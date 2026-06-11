"""Health Profile Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


class HealthProfileUpdate(BaseModel):
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    insurance_provider: Optional[str] = None


@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(
        text("SELECT * FROM health_profiles WHERE user_id = :uid"),
        {"uid": current_user["id"]},
    )
    row = result.fetchone()
    if not row:
        return {"message": "No health profile found. Please create one.", "data": None}
    return dict(row._mapping)


@router.put("/profile")
async def upsert_profile(
    body: HealthProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await db.execute(
        text("""
            INSERT INTO health_profiles (id, user_id, height_cm, weight_kg, blood_type,
                allergies, chronic_conditions, emergency_contact_name, emergency_contact_phone, insurance_provider)
            VALUES (:id, :uid, :h, :w, :bt, :al, :cc, :ecn, :ecp, :ins)
            ON CONFLICT (user_id) DO UPDATE SET
                height_cm = EXCLUDED.height_cm,
                weight_kg = EXCLUDED.weight_kg,
                blood_type = EXCLUDED.blood_type,
                allergies = EXCLUDED.allergies,
                chronic_conditions = EXCLUDED.chronic_conditions,
                emergency_contact_name = EXCLUDED.emergency_contact_name,
                emergency_contact_phone = EXCLUDED.emergency_contact_phone,
                insurance_provider = EXCLUDED.insurance_provider,
                updated_at = NOW()
        """),
        {
            "id": str(uuid4()), "uid": current_user["id"],
            "h": body.height_cm, "w": body.weight_kg, "bt": body.blood_type,
            "al": body.allergies, "cc": body.chronic_conditions,
            "ecn": body.emergency_contact_name, "ecp": body.emergency_contact_phone,
            "ins": body.insurance_provider,
        },
    )
    return {"message": "Health profile updated successfully"}
