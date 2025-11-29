"""Pydantic models for websocket messages."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class InstrumentModel(BaseModel):
    symbol_id: int
    ticker: str
    description: str
    industry: str
    initial_price: Optional[float] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OrderBookMessage(BaseModel):
    type: Literal["orderbooks"] = "orderbooks"
    version: int = 1
    data: Dict[int, Dict[str, Any]]
    sequence: Optional[int] = None  # For tracking message order
    timestamp: Optional[str] = None  # ISO format timestamp


class InstrumentsMessage(BaseModel):
    type: Literal["instruments"] = "instruments"
    version: int = 1
    data: List[InstrumentModel]


class AgentsSnapshotMessage(BaseModel):
    type: Literal["agents_snapshot"] = "agents_snapshot"
    version: int = 1
    data: List[Dict[str, Any]]


class OrderPlacedPayload(BaseModel):
    agent_id: str
    agent_name: str
    symbol_id: int
    ticker: str
    side: str
    order_type: str
    price: float
    quantity: int
    timestamp: str


class OrderPlacedMessage(BaseModel):
    type: Literal["order_placed"] = "order_placed"
    version: int = 1
    data: OrderPlacedPayload


class NewsPayload(BaseModel):
    headline: Optional[str] = Field(default=None, alias="title")
    content: str
    created_at: str


class NewsMessage(BaseModel):
    type: Literal["news"] = "news"
    version: int = 1
    data: Dict[str, Any]


class NewsHistoryMessage(BaseModel):
    type: Literal["news_history"] = "news_history"
    version: int = 1
    data: List[Dict[str, Any]]

