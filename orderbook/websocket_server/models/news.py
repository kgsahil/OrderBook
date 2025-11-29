"""News data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class News:
    """Represents a news item. News is independent of instruments - agents interpret which instruments are affected."""
    news_id: int
    content: str
    published_at: datetime
    instrument_id: Optional[int] = None  # Optional: agents decide which instruments are affected
    impact_type: Optional[str] = None  # "positive", "negative", "neutral"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'news_id': self.news_id,
            'content': self.content,
            'published_at': self.published_at.isoformat(),
            'instrument_id': self.instrument_id,
            'impact_type': self.impact_type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'News':
        """Create from dictionary."""
        return cls(
            news_id=data['news_id'],
            content=data['content'],
            published_at=datetime.fromisoformat(data['published_at']) if isinstance(data['published_at'], str) else data['published_at'],
            instrument_id=data.get('instrument_id'),
            impact_type=data.get('impact_type')
        )

