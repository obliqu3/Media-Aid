"""Auth Routes — Firebase-backed registration and profile sync"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import uuid4

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


class RegisterRequest(BaseModel):
    firebase_uid: str
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    language: Optional[str] = "en"


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Create user record after Firebase sign-up."""
    user_id = str(uuid4())
    try:
        await db.execute(
            text("""
                INSERT INTO users (id, firebase_uid, email, full_name, phone, language)
                VALUES (:id, :uid, :email, :name, :phone, :lang)
                ON CONFLICT (firebase_uid) DO UPDATE
                  SET email = EXCLUDED.email, full_name = EXCLUDED.full_name
            """),
            {"id": user_id, "uid": body.firebase_uid, "email": body.email,
             "name": body.full_name, "phone": body.phone, "lang": body.language},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": user_id, "message": "User registered successfully"}


@router.get("/me")
async def get_me(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Return current authenticated user's profile."""
    result = await db.execute(
        text("SELECT id, email, full_name, role, language, created_at FROM users WHERE firebase_uid = :uid"),
        {"uid": current_user["firebase_uid"]},
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found. Please register.")
    return dict(row._mapping)
