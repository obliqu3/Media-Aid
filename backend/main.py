"""
MediAid — AI Health Assistant Backend
SDG 3: Good Health and Well-Being
FastAPI + PostgreSQL + Gemini AI
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager

from routes import auth, health, vitals, medications, ai_chat, reports, clinics, admin
from database import engine, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 MediAid API starting up...")
    # Create tables on startup (use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        # Seed the mock user 'Arjun Rao' for local development testing
        from sqlalchemy import text
        await conn.execute(
            text("""
                INSERT INTO users (id, firebase_uid, email, full_name, role)
                VALUES ('00000000-0000-0000-0000-000000000000', 'mock-user-123', 'arjun.rao@email.com', 'Arjun Rao', 'patient')
                ON CONFLICT (firebase_uid) DO NOTHING
            """)
        )
    logger.info("✅ Database tables ready")
    yield
    logger.info("🛑 MediAid API shutting down...")


app = FastAPI(
    title="MediAid API",
    description="AI-powered health assistant — SDG 3: Good Health and Well-Being",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── ROUTERS ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/auth",        tags=["Authentication"])
app.include_router(health.router,      prefix="/health",      tags=["Health Profile"])
app.include_router(vitals.router,      prefix="/vitals",      tags=["Vitals Tracking"])
app.include_router(medications.router, prefix="/medications", tags=["Medications"])
app.include_router(ai_chat.router,     prefix="/ai",          tags=["AI Assistant"])
app.include_router(reports.router,     prefix="/reports",     tags=["Reports"])
app.include_router(clinics.router,     prefix="/clinics",     tags=["Clinics"])
app.include_router(admin.router,       prefix="/admin",       tags=["Admin"])


# ── GLOBAL EXCEPTION HANDLER ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/", tags=["Root"])
async def root():
    return {
        "app": "MediAid API",
        "version": "1.0.0",
        "sdg": "SDG 3 — Good Health and Well-Being",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health-check", tags=["Root"])
async def health_check():
    return {"status": "ok"}  # trigger reload 2
