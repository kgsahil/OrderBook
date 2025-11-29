"""News REST endpoints."""

from fastapi import APIRouter, HTTPException

from broadcast import broadcast_news_update
from state import news_service

router = APIRouter(prefix="/api/news", tags=["News"])


@router.post("")
async def publish_news(data: dict):
    content = data.get("content")
    instrument_id = data.get("instrument_id")
    impact_type = data.get("impact_type")

    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    instrument_id = int(instrument_id) if instrument_id else None

    news = news_service.publish_news(content, instrument_id, impact_type)
    await broadcast_news_update(news.to_dict())
    return news.to_dict()


@router.get("")
async def get_news(limit: int | None = None):
    news_items = news_service.get_news(limit)
    return [news.to_dict() for news in news_items]

