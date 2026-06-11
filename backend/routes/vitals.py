"""Vitals Tracking Routes"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


class VitalsEntry(BaseModel):
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    blood_glucose: Optional[float] = None
    temperature: Optional[float] = None
    spo2: Optional[float] = None
    weight_kg: Optional[float] = None
    notes: Optional[str] = None
    recorded_at: Optional[datetime] = None


@router.post("/")
async def log_vitals(
    entry: VitalsEntry,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Log a new vitals reading."""
    vital_id = str(uuid4())
    recorded_at = entry.recorded_at or datetime.utcnow()

    await db.execute(
        text("""
            INSERT INTO vitals (
                id, user_id, recorded_at, systolic_bp, diastolic_bp,
                heart_rate, blood_glucose, temperature, spo2, weight_kg, notes
            ) VALUES (
                :id, :user_id, :recorded_at, :systolic_bp, :diastolic_bp,
                :heart_rate, :blood_glucose, :temperature, :spo2, :weight_kg, :notes
            )
        """),
        {
            "id": vital_id,
            "user_id": current_user["id"],
            "recorded_at": recorded_at,
            **entry.model_dump(exclude={"recorded_at"}),
        },
    )

    # Check for alert conditions
    alerts = _check_vitals_alerts(entry)

    return {
        "id": vital_id,
        "recorded_at": recorded_at.isoformat(),
        "alerts": alerts,
        "message": "Vitals recorded successfully",
    }


@router.get("/")
async def get_vitals(
    limit: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get vitals history for the authenticated user."""
    result = await db.execute(
        text("""
            SELECT id, recorded_at, systolic_bp, diastolic_bp, heart_rate,
                   blood_glucose, temperature, spo2, weight_kg, notes
            FROM vitals
            WHERE user_id = :user_id
            ORDER BY recorded_at DESC
            LIMIT :limit
        """),
        {"user_id": current_user["id"], "limit": limit},
    )
    rows = result.fetchall()
    
    return {
        "vitals": [dict(row._mapping) for row in rows],
        "count": len(rows),
    }


@router.get("/latest")
async def get_latest_vitals(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the most recent vitals entry."""
    result = await db.execute(
        text("""
            SELECT * FROM vitals
            WHERE user_id = :user_id
            ORDER BY recorded_at DESC
            LIMIT 1
        """),
        {"user_id": current_user["id"]},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No vitals recorded yet.")
    return dict(row._mapping)


@router.get("/summary")
async def get_vitals_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get 7-day and 30-day averages for all vitals."""
    result = await db.execute(
        text("""
            SELECT
                AVG(systolic_bp) FILTER (WHERE recorded_at > NOW() - INTERVAL '7 days') AS avg_systolic_7d,
                AVG(diastolic_bp) FILTER (WHERE recorded_at > NOW() - INTERVAL '7 days') AS avg_diastolic_7d,
                AVG(heart_rate) FILTER (WHERE recorded_at > NOW() - INTERVAL '7 days') AS avg_hr_7d,
                AVG(blood_glucose) FILTER (WHERE recorded_at > NOW() - INTERVAL '7 days') AS avg_glucose_7d,
                AVG(systolic_bp) FILTER (WHERE recorded_at > NOW() - INTERVAL '30 days') AS avg_systolic_30d,
                AVG(diastolic_bp) FILTER (WHERE recorded_at > NOW() - INTERVAL '30 days') AS avg_diastolic_30d,
                COUNT(*) AS total_readings
            FROM vitals
            WHERE user_id = :user_id
        """),
        {"user_id": current_user["id"]},
    )
    row = result.fetchone()
    return dict(row._mapping) if row else {}


def _check_vitals_alerts(entry: VitalsEntry) -> List[dict]:
    alerts = []
    if entry.systolic_bp and entry.systolic_bp >= 180:
        alerts.append({"type": "critical", "message": "Critically high blood pressure. Seek immediate care."})
    elif entry.systolic_bp and entry.systolic_bp >= 140:
        alerts.append({"type": "warning", "message": "High blood pressure detected. Monitor closely."})

    if entry.blood_glucose and entry.blood_glucose >= 250:
        alerts.append({"type": "critical", "message": "Very high blood glucose. Contact your doctor."})
    elif entry.blood_glucose and entry.blood_glucose >= 126:
        alerts.append({"type": "warning", "message": "Elevated blood glucose. Consider consulting a doctor."})

    if entry.heart_rate and (entry.heart_rate > 130 or entry.heart_rate < 40):
        alerts.append({"type": "warning", "message": "Abnormal heart rate detected."})

    if entry.spo2 and entry.spo2 < 90:
        alerts.append({"type": "critical", "message": "Low oxygen saturation. Seek immediate medical attention."})

    return alerts
