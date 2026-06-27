"""Reports router — daily briefings."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.infrastructure.database.connection import get_session
from backend.infrastructure.database.models.all_models import DailyBriefingModel
from backend.api.v1.controllers.all_controllers import get_current_user, ok

router = APIRouter(prefix="/reports")


@router.get("/daily")
async def get_daily_briefings(
    limit: int = 7,
    current_user: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(DailyBriefingModel).order_by(desc(DailyBriefingModel.briefing_date)).limit(limit)
    result = await session.execute(stmt)
    briefings = result.scalars().all()
    return ok([{
        "city": b.city,
        "briefing_date": b.briefing_date.isoformat() if b.briefing_date else None,
        "highest_risk_area": b.highest_risk_area,
        "highest_risk_score": b.highest_risk_score,
        "primary_crime_type": b.primary_crime_type,
        "overall_risk_level": b.overall_risk_level,
        "avg_risk_score": b.avg_risk_score,
        "summary_text": b.summary_text,
        "top_recommendations": b.top_recommendations,
    } for b in briefings])


@router.post("/generate")
async def generate_report(current_user: str = Depends(get_current_user)):
    from backend.application.generate_report import generate_daily_report
    result = await generate_daily_report()
    return ok(result)
