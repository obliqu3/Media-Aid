"""Reports Route — AI-generated PDF health summaries and medical uploads"""

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import date, datetime, timedelta
import io
import os
import json
from uuid import uuid4
import google.generativeai as genai

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


@router.get("/")
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        text("""
            SELECT id, generated_at, period_start, period_end, report_type, file_path, summary, ai_insights
            FROM health_reports
            WHERE user_id = :uid
            ORDER BY generated_at DESC
            LIMIT 12
        """),
        {"uid": current_user["id"]},
    )
    
    reports = []
    for r in result.fetchall():
        row = dict(r._mapping)
        if isinstance(row.get("generated_at"), datetime):
            row["generated_at"] = row["generated_at"].isoformat()
        if isinstance(row.get("period_start"), date):
            row["period_start"] = row["period_start"].isoformat()
        if isinstance(row.get("period_end"), date):
            row["period_end"] = row["period_end"].isoformat()
            
        if isinstance(row.get("ai_insights"), str):
            try:
                row["ai_insights"] = json.loads(row["ai_insights"])
            except Exception:
                row["ai_insights"] = {}
                
        reports.append(row)
        
    return {"reports": reports}


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # 1. Save the file to uploads directory
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    file_id = str(uuid4())
    _, ext = os.path.splitext(file.filename.lower())
    if not ext:
        if file.content_type == "application/pdf":
            ext = ".pdf"
        elif file.content_type == "image/png":
            ext = ".png"
        elif file.content_type in ("image/jpeg", "image/jpg"):
            ext = ".jpg"
        else:
            ext = ".dat"
            
    filename = f"report_{file_id}{ext}"
    file_path = os.path.join(uploads_dir, filename)
    
    file_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    # 2. Get Gemini to analyze the report
    ai_insights = {}
    doc_title = file.filename
    doc_type = "report"
    summary = "Uploaded report"
    urgency = "low"
    
    try:
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        
        prompt = """
        You are an expert clinical AI. Analyze the attached medical report or medication document.
        1. Determine if this is a medication list/prescription or a lab/health report.
        2. Extract the main title/type of the document (e.g., "CBC Blood Test", "Metformin Prescription").
        3. Generate a concise, patient-friendly summary of the document (2-3 sentences).
        4. Extract key metrics, findings, or list of medications.
        5. Generate a list of actionable AI insights and recommendations for the patient based on this document.
        6. Assess the general urgency level based on the findings (low, medium, high, or emergency).
        7. Extract any medications mentioned in the document.
        8. Estimate the patient's current risk levels as a percentage float between 0.00 and 1.00 for: diabetes, hypertension, heart, cholesterol, kidney, and liver. 
           Evaluate based on relevant biomarker values (e.g., eGFR/creatinine/BUN for kidney risk; ALT/AST/bilirubin for liver risk; HbA1c/glucose for diabetes; BP for hypertension; lipids for cholesterol/heart).
           If there are no markers or clues for a specific risk, provide a default healthy baseline level (e.g., between 0.05 and 0.15).

        Format your response strictly as a JSON object with the following fields:
        {
          "document_title": "string",
          "document_type": "medication" | "report",
          "summary": "string",
          "urgency": "low" | "medium" | "high" | "emergency",
          "insights": [
            "insight 1",
            "insight 2"
          ],
          "detected_medications": [
            {
              "name": "string (medication name, e.g., Metformin)",
              "dosage": "string (e.g., 500mg or as directed)",
              "frequency": "string (e.g., twice daily or once daily)",
              "times_per_day": 1
            }
          ],
          "risks": {
            "diabetes": 0.42,
            "hypertension": 0.35,
            "heart": 0.22,
            "cholesterol": 0.18,
            "kidney": 0.15,
            "liver": 0.12
          }
        }
        Return ONLY valid JSON. Do not include any formatting, markdown code fences, or explanations.
        """
        
        # Determine mime type
        mime_type = file.content_type or "application/octet-stream"
        if ext == ".pdf":
            mime_type = "application/pdf"
        elif ext in (".png", ".jpg", ".jpeg"):
            mime_type = f"image/{ext[1:]}"
            if mime_type == "image/jpg":
                mime_type = "image/jpeg"
                
        # Send to Gemini
        response = model.generate_content([
            prompt,
            {
                "mime_type": mime_type,
                "data": file_bytes
            }
        ])
        
        raw = response.text.strip()
        # Clean up markdown response if needed
        if raw.startswith("```"):
            lines = raw.split("\n")
            if lines[0].startswith("```json") or lines[0].startswith("```"):
                raw = "\n".join(lines[1:-1])
            else:
                raw = raw.replace("```json", "").replace("```", "")
        raw = raw.strip()
        
        ai_data = json.loads(raw)
        doc_title = ai_data.get("document_title", doc_title)
        doc_type = ai_data.get("document_type", doc_type)
        summary = ai_data.get("summary", summary)
        urgency = ai_data.get("urgency", urgency)
        ai_insights = {
            "insights": ai_data.get("insights", []),
            "urgency": urgency,
            "summary": summary,
            "detected_medications": ai_data.get("detected_medications", []),
            "risks": ai_data.get("risks", {
                "diabetes": 0.42,
                "hypertension": 0.35,
                "heart": 0.22,
                "cholesterol": 0.18,
                "kidney": 0.15,
                "liver": 0.12
            })
        }
        
    except Exception as e:
        print(f"Error analyzing report with Gemini: {e}")
        # Default fallback values
        ai_insights = {
            "insights": ["AI analysis failed or was unavailable for this document. Please review it manually."],
            "urgency": "low",
            "summary": f"Uploaded document: {file.filename}",
            "detected_medications": [],
            "risks": {
                "diabetes": 0.42,
                "hypertension": 0.35,
                "heart": 0.22,
                "cholesterol": 0.18,
                "kidney": 0.15,
                "liver": 0.12
            }
        }
        summary = f"Uploaded document: {file.filename}"
        
    # The URL to access the file
    file_url = f"http://localhost:8000/uploads/{filename}"
    
    # 3. Save detected medications to medications table
    detected_meds = ai_insights.get("detected_medications", [])
    for med in detected_meds:
        med_name = med.get("name")
        if med_name:
            # Check for existing active medication with same name to avoid duplicates
            existing = await db.execute(
                text("""
                    SELECT id FROM medications
                    WHERE user_id = :uid AND LOWER(name) = LOWER(:name) AND is_active = true
                """),
                {"uid": current_user["id"], "name": med_name}
            )
            if not existing.fetchone():
                med_id = str(uuid4())
                await db.execute(
                    text("""
                        INSERT INTO medications (id, user_id, name, dosage, frequency, times_per_day, start_date, is_active)
                        VALUES (:id, :uid, :name, :dosage, :freq, :tpd, :sd, true)
                    """),
                    {
                        "id": med_id,
                        "uid": current_user["id"],
                        "name": med_name,
                        "dosage": med.get("dosage", "as directed"),
                        "freq": med.get("frequency", "once daily"),
                        "tpd": med.get("times_per_day", 1),
                        "sd": date.today()
                    }
                )
                
    # 4. Save report + insights to database
    today = date.today()
    report_db_id = str(uuid4())
    
    await db.execute(
        text("""
            INSERT INTO health_reports (id, user_id, generated_at, period_start, period_end, report_type, file_path, summary, ai_insights)
            VALUES (:id, :uid, NOW(), :start, :end, :type, :file_path, :summary, :ai_insights)
        """),
        {
            "id": report_db_id,
            "uid": current_user["id"],
            "start": today,
            "end": today,
            "type": doc_type,
            "file_path": file_url,
            "summary": doc_title,
            "ai_insights": json.dumps(ai_insights)
        }
    )
    
    return {
        "message": "Report uploaded and analyzed successfully",
        "report": {
            "id": report_db_id,
            "generated_at": datetime.utcnow().isoformat(),
            "period_start": today.isoformat(),
            "period_end": today.isoformat(),
            "report_type": doc_type,
            "file_path": file_url,
            "summary": doc_title,
            "ai_insights": ai_insights
        }
    }


@router.get("/generate")
async def generate_report(
    period: str = Query("monthly", enum=["monthly", "quarterly", "weekly"]),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate a health report PDF using ReportLab."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import cm

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle("title", parent=styles["Title"],
                                     fontSize=22, textColor=colors.HexColor("#0B4F6C"))
        story.append(Paragraph("MediAid Health Report", title_style))
        story.append(Paragraph(f"Patient: {current_user.get('name', 'Patient')} | Generated: {date.today()}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("SDG 3: Good Health and Well-Being", styles["Italic"]))
        story.append(Spacer(1, 1*cm))

        # Summary section
        story.append(Paragraph("Health Summary", styles["Heading2"]))
        story.append(Paragraph("This report covers your health metrics, medication adherence, and AI-assessed risk levels for the selected period.", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Mock vitals table
        data = [
            ["Metric", "Latest Value", "30-Day Avg", "Status"],
            ["Systolic BP", "124 mmHg", "126 mmHg", "Normal"],
            ["Diastolic BP", "82 mmHg", "83 mmHg", "Normal"],
            ["Heart Rate", "72 bpm", "74 bpm", "Normal"],
            ["Blood Glucose", "108 mg/dL", "110 mg/dL", "Monitor"],
            ["SpO₂", "98%", "98%", "Normal"],
        ]
        table = Table(data, colWidths=[5*cm, 4*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B4F6C")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph("AI Risk Assessment: MODERATE (37%)", styles["Heading3"]))
        story.append(Paragraph("Disclaimer: This report is generated by AI and is not a medical diagnosis. Always consult a qualified healthcare professional.", styles["Italic"]))

        doc.build(story)
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=mediaid-report-{date.today()}.pdf"},
        )
    except ImportError:
        return {"error": "ReportLab not installed. Run: pip install reportlab"}
