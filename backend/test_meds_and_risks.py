import httpx
import asyncio
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_lab_report():
    pdf_path = "mock_kidney_liver_report.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        spaceAfter=15
    )
    normal_style = styles['Normal']
    
    story.append(Paragraph("Aravind Clinic Health Assessment & Lab Report", title_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Patient Name: Arjun Rao", normal_style))
    story.append(Paragraph("Date: June 12, 2026", normal_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Renal/Kidney Panel:</b>", styles['Heading2']))
    story.append(Paragraph("- eGFR: 55 mL/min/1.73m2 (Moderate impairment, High risk of Chronic Kidney Disease)", normal_style))
    story.append(Paragraph("- Creatinine: 1.6 mg/dL (High, normal range: 0.7 - 1.3)", normal_style))
    
    story.append(Paragraph("<b>Hepatic/Liver Panel:</b>", styles['Heading2']))
    story.append(Paragraph("- Alanine Aminotransferase (ALT): 95 U/L (High, normal: 7 - 56)", normal_style))
    story.append(Paragraph("- Aspartate Aminotransferase (AST): 85 U/L (High, normal: 10 - 40)", normal_style))
    
    story.append(Paragraph("<b>Prescribed Medications:</b>", styles['Heading2']))
    story.append(Paragraph("- Lisinopril 10mg - 1 tablet once daily (for hypertension and renal protection)", normal_style))
    story.append(Paragraph("- Metformin 500mg - 1 tablet twice daily", normal_style))
    
    doc.build(story)
    print("Mock kidney/liver PDF generated.")

async def run_test():
    generate_lab_report()
    
    upload_url = "http://localhost:8000/reports/upload"
    meds_url = "http://localhost:8000/medications/"
    
    print("\n--- 1. Uploading PDF and waiting for AI analysis ---")
    async with httpx.AsyncClient(timeout=40.0) as client:
        with open("mock_kidney_liver_report.pdf", "rb") as f:
            files = {"file": ("mock_kidney_liver_report.pdf", f, "application/pdf")}
            response = await client.post(upload_url, files=files)
            
        print("Upload Status Code:", response.status_code)
        resp_data = response.json()
        print("AI Risks detected:", resp_data.get("report", {}).get("ai_insights", {}).get("risks"))
        print("Detected meds:", resp_data.get("report", {}).get("ai_insights", {}).get("detected_medications"))
        
        print("\n--- 2. Fetching medications list ---")
        meds_response = await client.get(meds_url)
        print("Meds list Status:", meds_response.status_code)
        meds_data = meds_response.json()
        med_names = [m.get("name") for m in meds_data.get("medications", [])]
        print("Active Medications in Database:", med_names)

if __name__ == "__main__":
    asyncio.run(run_test())
