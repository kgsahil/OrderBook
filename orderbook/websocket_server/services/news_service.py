"""Service for managing and broadcasting news."""

from typing import List, Optional
from datetime import datetime

from models.news import News


class NewsService:
    """Manages news items and broadcasts them to agents."""
    
    def __init__(self):
        self.news_items: List[News] = []
        self.next_news_id = 1
    
    def publish_news(self, content: str, 
                    instrument_id: Optional[int] = None,
                    impact_type: Optional[str] = None) -> News:
        """Publish a news item. News is independent - agents interpret which instruments are affected."""
        news = News(
            news_id=self.next_news_id,
            content=content,
            published_at=datetime.now(),
            instrument_id=instrument_id,
            impact_type=impact_type
        )
        self.next_news_id += 1
        self.news_items.append(news)
        return news
    
    def get_news(self, limit: Optional[int] = None) -> List[News]:
        """Get recent news items."""
        news = self.news_items.copy()
        if limit:
            return news[-limit:]
        return news
    
    def get_news_by_instrument(self, instrument_id: int, 
                               limit: Optional[int] = None) -> List[News]:
        """Get news that may be related to a specific instrument (includes general news)."""
        # Return news that is either tagged with this instrument or is general (no instrument_id)
        news = [n for n in self.news_items if n.instrument_id is None or n.instrument_id == instrument_id]
        if limit:
            return news[-limit:]
        return news
    
    def get_latest_news(self, count: int = 10) -> List[News]:
        """Get latest news items."""
        return self.news_items[-count:] if len(self.news_items) > count else self.news_items

