"""
CrimePatrol — Daily Report Generator (AI Report Agent)
Generates a daily city-wide safety briefing using Gemini.
"""
import uuid
from datetime import datetime, timezone

from backend.core.config import get_settings
from backend.core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def generate_daily_report() -> dict:
    from backend.infrastructure.database.connection import get_session_factory
    from backend.infrastructure.database.models.all_models import PredictionModel, DailyBriefingModel, AreaModel
    from sqlalchemy import select, desc, func, and_

    session_factory = get_session_factory()
    today = datetime.now(timezone.utc).date()

    async with session_factory() as session:
        # Gather today's predictions
        stmt = (
            select(PredictionModel, AreaModel.name)
            .join(AreaModel, PredictionModel.area_id == AreaModel.id)
            .where(
                and_(
                    func.date(PredictionModel.predicted_for) == today,
                    AreaModel.city == settings.city_name,
                )
            )
            .order_by(desc(PredictionModel.risk_score))
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        logger.warning("daily_report_no_data", date=str(today))
        return {"success": False, "reason": "No predictions found for today."}

    predictions = [row[0] for row in rows]
    area_names = {str(row[0].area_id): row[1] for row in rows}

    highest = predictions[0]
    highest_area = area_names.get(str(highest.area_id), "Unknown")
    avg_score = round(sum(p.risk_score for p in predictions) / len(predictions), 2)
    avg_conf = round(sum(p.confidence for p in predictions) / len(predictions), 3)

    # Determine overall risk level
    high_count = sum(1 for p in predictions if p.risk_level in ("HIGH", "CRITICAL"))
    overall_level = "HIGH" if high_count > len(predictions) * 0.3 else "MEDIUM" if high_count > 0 else "LOW"

    # Generate summary with Gemini
    summary_text = await _generate_summary(highest, highest_area, avg_score, overall_level, len(predictions))

    # Top recommendations from highest-risk prediction
    top_recs = []
    # (in production, query recommendations table for highest prediction)

    async with session_factory() as session:
        briefing = DailyBriefingModel(
            id=uuid.uuid4(),
            city=settings.city_name,
            briefing_date=today,
            highest_risk_area=highest_area,
            highest_risk_score=highest.risk_score,
            primary_crime_type=highest.crime_type,
            overall_risk_level=overall_level,
            avg_risk_score=avg_score,
            avg_confidence=avg_conf,
            summary_text=summary_text,
            top_recommendations=top_recs,
            stats={"total_predictions": len(predictions), "high_risk_count": high_count},
        )
        session.add(briefing)
        await session.commit()

    logger.info("daily_report_generated", city=settings.city_name, date=str(today))
    return {
        "success": True,
        "city": settings.city_name,
        "date": str(today),
        "highest_risk_area": highest_area,
        "overall_risk_level": overall_level,
        "avg_risk_score": avg_score,
        "summary": summary_text,
    }


async def _generate_summary(prediction, area_name: str, avg_score: float, overall_level: str, count: int) -> str:
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage

        if not settings.gemini_api_key:
            return _fallback_summary(prediction, area_name, avg_score, overall_level)

        prompt = f"""Write a professional 4-sentence daily safety briefing for {settings.city_name} city officials.

Data:
- Overall City Risk: {overall_level} (avg score: {avg_score}/100)
- Highest Risk Area: {area_name} (score: {prediction.risk_score}/100, {prediction.risk_level})
- Primary Crime Type: {prediction.crime_type}
- Total Areas Analyzed: {count}

Include: risk level, highest risk area, primary threat type, and one key recommendation.
Professional tone. No bullet points. Under 80 words."""

        llm = ChatGoogleGenerativeAI(model=settings.gemini_model, google_api_key=settings.gemini_api_key)
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        return resp.content.strip()
    except Exception as exc:
        logger.warning("daily_report_llm_error", error=str(exc))
        return _fallback_summary(prediction, area_name, avg_score, overall_level)


def _fallback_summary(prediction, area_name: str, avg_score: float, overall_level: str) -> str:
    return (
        f"Today's city-wide risk level is {overall_level} with an average score of {avg_score}/100. "
        f"The highest risk area is {area_name} with a score of {prediction.risk_score}/100, "
        f"primarily driven by {prediction.crime_type} risk. "
        f"Increased patrol presence and CCTV monitoring in high-risk zones is recommended."
    )
