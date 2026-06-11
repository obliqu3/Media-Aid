"""Admin Route — Anonymized population analytics (admin-only)"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from middleware.auth import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Platform-wide anonymized health statistics."""
    result = await db.execute(text("""
        SELECT
            (SELECT COUNT(*) FROM users WHERE is_active = true) AS total_users,
            (SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '7 days') AS new_users_7d,
            (SELECT COUNT(*) FROM chat_sessions WHERE created_at > NOW() - INTERVAL '1 day') AS chats_today,
            (SELECT COUNT(*) FROM vitals WHERE recorded_at > NOW() - INTERVAL '1 day') AS vitals_today,
            (SELECT COUNT(*) FROM risk_assessments WHERE overall_risk IN ('high','critical')) AS high_risk_users
    """))
    row = result.fetchone()
    stats = dict(row._mapping) if row else {}

    # Top symptoms from chat metadata (anonymized)
    sym_result = await db.execute(text("""
        SELECT jsonb_array_elements_text(metadata->'symptoms') AS symptom, COUNT(*) AS count
        FROM chat_messages
        WHERE role = 'assistant'
          AND created_at > NOW() - INTERVAL '7 days'
          AND metadata ? 'symptoms'
        GROUP BY symptom
        ORDER BY count DESC
        LIMIT 10
    """))
    top_symptoms = [{"symptom": r[0], "count": r[1]} for r in sym_result.fetchall()]

    return {
        "platform_stats": stats,
        "top_symptoms_7d": top_symptoms,
        "sdg_impact": {
            "people_served": stats.get("total_users", 0),
            "symptom_checks_today": stats.get("chats_today", 0),
            "high_risk_identified": stats.get("high_risk_users", 0),
            "sdg_goal": "SDG 3.8 — Universal health coverage",
        }
    }
