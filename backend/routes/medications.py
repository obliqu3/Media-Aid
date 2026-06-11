"""Medications Routes — CRUD + dose logging"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time
from uuid import uuid4

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


class MedicationCreate(BaseModel):
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    times_per_day: int = 1
    reminder_times: Optional[List[str]] = None   # ["08:00", "20:00"]
    start_date: date
    end_date: Optional[date] = None
    instructions: Optional[str] = None
    prescribing_doctor: Optional[str] = None


class DoseLog(BaseModel):
    status: str   # taken | missed | skipped
    notes: Optional[str] = None


@router.get("/")
async def list_medications(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        text("""
            SELECT * FROM medications
            WHERE user_id = :uid AND (:active_only = false OR is_active = true)
            ORDER BY created_at DESC
        """),
        {"uid": current_user["id"], "active_only": active_only},
    )
    return {"medications": [dict(r._mapping) for r in result.fetchall()]}


@router.post("/", status_code=201)
async def add_medication(
    body: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    med_id = str(uuid4())
    await db.execute(
        text("""
            INSERT INTO medications (id, user_id, name, dosage, frequency, times_per_day,
                reminder_times, start_date, end_date, instructions, prescribing_doctor)
            VALUES (:id, :uid, :name, :dosage, :freq, :tpd, :rt, :sd, :ed, :inst, :doc)
        """),
        {
            "id": med_id, "uid": current_user["id"],
            "name": body.name, "dosage": body.dosage, "freq": body.frequency,
            "tpd": body.times_per_day, "rt": body.reminder_times,
            "sd": body.start_date, "ed": body.end_date,
            "inst": body.instructions, "doc": body.prescribing_doctor,
        },
    )
    return {"id": med_id, "message": "Medication added"}


@router.delete("/{med_id}")
async def delete_medication(
    med_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await db.execute(
        text("UPDATE medications SET is_active = false WHERE id = :id AND user_id = :uid"),
        {"id": med_id, "uid": current_user["id"]},
    )
    return {"message": "Medication deactivated"}


@router.get("/adherence")
async def get_adherence(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Calculate medication adherence rate for the last 30 days."""
    result = await db.execute(
        text("""
            SELECT
                m.name,
                COUNT(*) AS total_doses,
                COUNT(*) FILTER (WHERE ml.status = 'taken') AS taken_doses,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE ml.status = 'taken') / NULLIF(COUNT(*), 0), 1
                ) AS adherence_pct
            FROM medication_logs ml
            JOIN medications m ON ml.medication_id = m.id
            WHERE ml.user_id = :uid
              AND ml.scheduled_time > NOW() - INTERVAL '30 days'
            GROUP BY m.name
        """),
        {"uid": current_user["id"]},
    )
    rows = result.fetchall()
    return {"adherence": [dict(r._mapping) for r in rows]}
