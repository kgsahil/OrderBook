"""Shared application state and services."""

from typing import Set

from fastapi import WebSocket

import settings
from services import (
    InstrumentService,
    AgentManager,
    PortfolioTracker,
    NewsService,
    MarketMakerService,
    OrderBookClient,
)

# Core service instances
ob_client = OrderBookClient(settings.settings.cpp_host, settings.settings.cpp_port)
instrument_service = InstrumentService(ob_client)
agent_manager = AgentManager()
portfolio_tracker = PortfolioTracker(agent_manager)
news_service = NewsService()
market_maker_service = MarketMakerService(ob_client)

# Active dashboard websocket connections
regular_connections: Set[WebSocket] = set()

# Default instrument bootstrap configuration
DEFAULT_INSTRUMENT = settings.settings.default_instrument

