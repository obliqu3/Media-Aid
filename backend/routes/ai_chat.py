"""
AI Chat Route — Gemini-powered symptom checker and health assistant
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
import google.generativeai as genai
import json
import os
from uuid import UUID, uuid4
from datetime import datetime

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction="""You are MediAid, a compassionate AI health assistant designed to help 
people in underserved communities access basic healthcare guidance.

Your role:
- Analyze symptoms described by users and provide initial guidance
- Triage urgency level: low / medium / high / emergency
- Ask clarifying questions about symptoms (duration, severity, location)
- Provide clear, simple, jargon-free health information
- Always recommend professional medical consultation for serious concerns
- For EMERGENCY situations, immediately instruct user to call emergency services

CRITICAL RULES:
- You are NOT a doctor and cannot diagnose conditions
- Always end serious symptom conversations with "Please consult a healthcare provider"
- Never prescribe specific medications
- For chest pain, difficulty breathing, stroke symptoms → always say CALL EMERGENCY NOW

Response format (always return valid JSON):
{
  "message": "Your response to the user",
  "urgency": "low|medium|high|emergency",
  "detected_symptoms": ["symptom1", "symptom2"],
  "follow_up_questions": ["question1"],
  "recommendations": ["recommendation1"],
  "should_seek_care": true|false
}"""
)


class ChatMessage(BaseModel):
    content: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    urgency: str
    detected_symptoms: List[str]
    recommendations: List[str]
    should_seek_care: bool
    session_id: str


class RiskAssessmentRequest(BaseModel):
    age: int
    gender: str
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    blood_glucose: Optional[float] = None
    bmi: Optional[float] = None
    smoker: bool = False
    family_history_diabetes: bool = False
    family_history_heart: bool = False
    physical_activity: str = "moderate"   # low, moderate, high


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    message: ChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Conversational AI symptom checker powered by Gemini."""
    try:
        # Build conversation history prompt
        user_context = f"""
User profile context:
- Age: {current_user.get('age', 'unknown')}
- Known conditions: {current_user.get('conditions', 'none reported')}

User message: {message.content}

Respond ONLY with valid JSON matching the specified format.
"""
        response = model.generate_content(user_context)
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        ai_data = json.loads(raw)

        session_id = message.session_id or str(uuid4())

        # Persist chat message to DB (async, non-blocking in production use background task)
        await _persist_chat(db, current_user["id"], session_id, message.content, ai_data)

        return ChatResponse(
            message=ai_data.get("message", "I'm here to help. Could you describe your symptoms?"),
            urgency=ai_data.get("urgency", "low"),
            detected_symptoms=ai_data.get("detected_symptoms", []),
            recommendations=ai_data.get("recommendations", []),
            should_seek_care=ai_data.get("should_seek_care", False),
            session_id=session_id,
        )

    except json.JSONDecodeError:
        # Fallback: return raw text if JSON parsing fails
        return ChatResponse(
            message=response.text if 'response' in dir() else "I'm here to help. Please describe your symptoms.",
            urgency="low",
            detected_symptoms=[],
            recommendations=["Please consult a healthcare provider for proper diagnosis."],
            should_seek_care=False,
            session_id=message.session_id or str(uuid4()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/risk-assessment")
async def risk_assessment(
    data: RiskAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI-powered health risk prediction using Gemini + rule-based heuristics."""

    # Rule-based risk scoring (interpretable, no black box for health)
    diabetes_risk = _calculate_diabetes_risk(data)
    hypertension_risk = _calculate_hypertension_risk(data)
    heart_risk = _calculate_heart_risk(data)

    overall_score = (diabetes_risk + hypertension_risk + heart_risk) / 3
    if overall_score < 0.25:
        overall = "low"
    elif overall_score < 0.5:
        overall = "moderate"
    elif overall_score < 0.75:
        overall = "high"
    else:
        overall = "critical"

    # Use Gemini to generate personalized recommendations
    prompt = f"""
Based on this health risk assessment, provide 5 personalized, actionable health recommendations.
Patient data: age={data.age}, gender={data.gender}, BMI={data.bmi}, 
smoker={data.smoker}, physical_activity={data.physical_activity}
Risk scores: diabetes={diabetes_risk:.2f}, hypertension={hypertension_risk:.2f}, heart={heart_risk:.2f}

Return JSON: {{"recommendations": ["rec1", "rec2", "rec3", "rec4", "rec5"]}}
"""
    rec_response = model.generate_content(prompt)
    try:
        raw = rec_response.text.strip().replace("```json", "").replace("```", "")
        recs = json.loads(raw).get("recommendations", [])
    except Exception:
        recs = [
            "Maintain a balanced diet rich in vegetables and whole grains",
            "Aim for 30 minutes of moderate exercise daily",
            "Monitor your blood pressure and glucose regularly",
            "Reduce salt and sugar intake",
            "Schedule a preventive health check-up",
        ]

    return {
        "diabetes_risk": round(diabetes_risk, 3),
        "hypertension_risk": round(hypertension_risk, 3),
        "heart_disease_risk": round(heart_risk, 3),
        "overall_risk": overall,
        "recommendations": recs,
        "assessed_at": datetime.utcnow().isoformat(),
    }


# ── HELPERS ────────────────────────────────────────────────────────────────────

def _calculate_diabetes_risk(data: RiskAssessmentRequest) -> float:
    score = 0.0
    if data.age > 45: score += 0.2
    if data.age > 60: score += 0.1
    if data.bmi and data.bmi > 25: score += 0.15
    if data.bmi and data.bmi > 30: score += 0.15
    if data.blood_glucose and data.blood_glucose > 100: score += 0.2
    if data.blood_glucose and data.blood_glucose > 126: score += 0.2
    if data.family_history_diabetes: score += 0.15
    if data.physical_activity == "low": score += 0.1
    return min(score, 1.0)


def _calculate_hypertension_risk(data: RiskAssessmentRequest) -> float:
    score = 0.0
    if data.systolic_bp and data.systolic_bp > 120: score += 0.15
    if data.systolic_bp and data.systolic_bp > 140: score += 0.25
    if data.age > 55: score += 0.15
    if data.smoker: score += 0.2
    if data.bmi and data.bmi > 30: score += 0.1
    if data.physical_activity == "low": score += 0.1
    return min(score, 1.0)


def _calculate_heart_risk(data: RiskAssessmentRequest) -> float:
    score = 0.0
    if data.age > 45: score += 0.15
    if data.smoker: score += 0.25
    if data.family_history_heart: score += 0.2
    if data.systolic_bp and data.systolic_bp > 140: score += 0.15
    if data.bmi and data.bmi > 30: score += 0.1
    if data.physical_activity == "low": score += 0.1
    if data.blood_glucose and data.blood_glucose > 126: score += 0.1
    return min(score, 1.0)


async def _persist_chat(db, user_id, session_id, user_message, ai_response):
    """Persist chat exchange to database."""
    from sqlalchemy import text
    try:
        await db.execute(
            text("""
                INSERT INTO chat_messages (id, session_id, role, content, metadata)
                VALUES (:id, :session_id, :role, :content, :metadata)
                ON CONFLICT DO NOTHING
            """),
            {
                "id": str(uuid4()),
                "session_id": session_id,
                "role": "user",
                "content": user_message,
                "metadata": json.dumps({}),
            },
        )
        await db.execute(
            text("""
                INSERT INTO chat_messages (id, session_id, role, content, metadata)
                VALUES (:id, :session_id, :role, :content, :metadata)
            """),
            {
                "id": str(uuid4()),
                "session_id": session_id,
                "role": "assistant",
                "content": ai_response.get("message", ""),
                "metadata": json.dumps({
                    "urgency": ai_response.get("urgency"),
                    "symptoms": ai_response.get("detected_symptoms"),
                }),
            },
        )
    except Exception:
        pass  # Don't fail request on logging error
