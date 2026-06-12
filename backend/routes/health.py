"""Health Profile Routes"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4
import os
from datetime import datetime

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


class HealthProfileUpdate(BaseModel):
    # Personal Info (users table)
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None  # format YYYY-MM-DD
    gender: Optional[str] = None
    phone: Optional[str] = None

    # Health Info (health_profiles table)
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    chronic_conditions: Optional[List[str]] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    insurance_provider: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Join users and health_profiles to get the full profile info
    result = await db.execute(
        text("""
            SELECT u.email, u.full_name, u.phone, u.date_of_birth, u.gender, u.profile_picture,
                   hp.height_cm, hp.weight_kg, hp.blood_type, hp.allergies, hp.chronic_conditions,
                   hp.emergency_contact_name, hp.emergency_contact_phone, hp.insurance_provider,
                   hp.latitude, hp.longitude
            FROM users u
            LEFT JOIN health_profiles hp ON u.id = hp.user_id
            WHERE u.id = :uid
        """),
        {"uid": current_user["id"]},
    )
    row = result.fetchone()
    if not row:
        return {"message": "No profile found", "data": None}
    
    # Return mapped dictionary
    data = dict(row._mapping)
    
    # Convert date_of_birth to string if it is a date object
    if data.get("date_of_birth"):
        data["date_of_birth"] = data["date_of_birth"].strftime("%Y-%m-%d")
        
    # Convert decimal fields to float for JSON compatibility
    if data.get("latitude") is not None:
        data["latitude"] = float(data["latitude"])
    if data.get("longitude") is not None:
        data["longitude"] = float(data["longitude"])
        
    return {"message": "Profile retrieved successfully", "data": data}


@router.put("/profile")
async def upsert_profile(
    body: HealthProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # 1. Update users table if personal info is provided
    gender_val = body.gender.lower() if body.gender else None
    if gender_val and gender_val not in ('male', 'female', 'other'):
        gender_val = None
        
    dob_val = None
    if body.date_of_birth:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                dob_val = datetime.strptime(body.date_of_birth, fmt).date()
                break
            except ValueError:
                continue
            
    await db.execute(
        text("""
            UPDATE users
            SET full_name = COALESCE(:full_name, full_name),
                date_of_birth = COALESCE(:date_of_birth, date_of_birth),
                gender = COALESCE(:gender, gender),
                phone = COALESCE(:phone, phone),
                updated_at = NOW()
            WHERE id = :uid
        """),
        {
            "uid": current_user["id"],
            "full_name": body.full_name,
            "date_of_birth": dob_val,
            "gender": gender_val,
            "phone": body.phone,
        }
    )

    # 2. Upsert health_profiles table
    await db.execute(
        text("""
            INSERT INTO health_profiles (id, user_id, height_cm, weight_kg, blood_type,
                allergies, chronic_conditions, emergency_contact_name, emergency_contact_phone, insurance_provider,
                latitude, longitude)
            VALUES (:id, :uid, :h, :w, :bt, :al, :cc, :ecn, :ecp, :ins, :lat, :lon)
            ON CONFLICT (user_id) DO UPDATE SET
                height_cm = COALESCE(EXCLUDED.height_cm, health_profiles.height_cm),
                weight_kg = COALESCE(EXCLUDED.weight_kg, health_profiles.weight_kg),
                blood_type = COALESCE(EXCLUDED.blood_type, health_profiles.blood_type),
                allergies = COALESCE(EXCLUDED.allergies, health_profiles.allergies),
                chronic_conditions = COALESCE(EXCLUDED.chronic_conditions, health_profiles.chronic_conditions),
                emergency_contact_name = COALESCE(EXCLUDED.emergency_contact_name, health_profiles.emergency_contact_name),
                emergency_contact_phone = COALESCE(EXCLUDED.emergency_contact_phone, health_profiles.emergency_contact_phone),
                insurance_provider = COALESCE(EXCLUDED.insurance_provider, health_profiles.insurance_provider),
                latitude = COALESCE(EXCLUDED.latitude, health_profiles.latitude),
                longitude = COALESCE(EXCLUDED.longitude, health_profiles.longitude),
                updated_at = NOW()
        """),
        {
            "id": str(uuid4()), "uid": current_user["id"],
            "h": body.height_cm, "w": body.weight_kg, "bt": body.blood_type,
            "al": body.allergies, "cc": body.chronic_conditions,
            "ecn": body.emergency_contact_name, "ecp": body.emergency_contact_phone,
            "ins": body.insurance_provider,
            "lat": body.latitude, "lon": body.longitude,
        },
    )
    return {"message": "Profile updated successfully"}


ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}

@router.post("/profile/photo")
async def upload_profile_photo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PNG, JPG, and JPEG images are allowed.")
    
    # Path to local uploads directory
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    filename = f"profile_{current_user['id']}{ext}"
    file_path = os.path.join(uploads_dir, filename)
    
    # Save the uploaded file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # The URL to access the photo
    photo_url = f"http://localhost:8000/uploads/{filename}"
    
    # Save photo_url in users table
    await db.execute(
        text("UPDATE users SET profile_picture = :photo_url, updated_at = NOW() WHERE id = :uid"),
        {"uid": current_user["id"], "photo_url": photo_url}
    )
    
    return {"message": "Profile picture updated successfully", "profile_picture": photo_url}

