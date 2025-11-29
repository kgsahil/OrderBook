#!/usr/bin/env python3
"""
Admin Dashboard Server - Separate component for managing trading simulation.
Connects to OrderBook service via WebSocket and REST API.
"""

import asyncio
import json
import logging
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import httpx
import uvicorn

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Trading Dashboard")

# Serve static assets (CSS/JS) from /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OrderBook service connection
ORDERBOOK_HOST = os.getenv("ORDERBOOK_HOST", "orderbook")
ORDERBOOK_PORT = int(os.getenv("ORDERBOOK_PORT", "8000"))
ORDERBOOK_WS_URL = f"ws://{ORDERBOOK_HOST}:{ORDERBOOK_PORT}/ws"
ORDERBOOK_API_URL = f"http://{ORDERBOOK_HOST}:{ORDERBOOK_PORT}/api"

# HTTP client for REST API calls
http_client = httpx.AsyncClient(timeout=10.0)


@app.get("/")
async def get_index():
    """Serve the dashboard HTML page"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if OrderBook is accessible
        response = await http_client.get(f"{ORDERBOOK_API_URL.replace('/api', '')}/health")
        orderbook_status = response.json() if response.status_code == 200 else {"status": "unreachable"}
    except Exception as e:
        orderbook_status = {"status": "error", "error": str(e)}
    
    return {
        "status": "ok",
        "orderbook": orderbook_status,
        "orderbook_url": ORDERBOOK_API_URL
    }


# Proxy endpoints to OrderBook API
@app.get("/api/instruments")
async def list_instruments():
    """List all instruments"""
    try:
        response = await http_client.get(f"{ORDERBOOK_API_URL}/instruments")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/instruments")
async def add_instrument(request: Request):
    """Add a new instrument"""
    try:
        data = await request.json()
        response = await http_client.post(f"{ORDERBOOK_API_URL}/instruments", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error adding instrument: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/instruments/{symbol_id}")
async def remove_instrument(symbol_id: int):
    """Remove an instrument"""
    try:
        response = await http_client.delete(f"{ORDERBOOK_API_URL}/instruments/{symbol_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents")
async def list_agents():
    """List all agents"""
    try:
        response = await http_client.get(f"{ORDERBOOK_API_URL}/agents")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/agents")
async def create_agent(request: Request):
    """Create a new agent (metadata only - agent must connect via WebSocket to start trading)"""
    try:
        data = await request.json()
        response = await http_client.post(f"{ORDERBOOK_API_URL}/agents", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    try:
        response = await http_client.get(f"{ORDERBOOK_API_URL}/agents/{agent_id}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/portfolio")
async def get_agent_portfolio(agent_id: str):
    """Get agent portfolio"""
    try:
        response = await http_client.get(f"{ORDERBOOK_API_URL}/agents/{agent_id}/portfolio")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agents/{agent_id}/trades")
async def get_agent_trades(agent_id: str, limit: Optional[int] = None):
    """Get agent trade history"""
    try:
        params = {"limit": limit} if limit else {}
        response = await http_client.get(f"{ORDERBOOK_API_URL}/agents/{agent_id}/trades", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/leaderboard")
async def get_leaderboard():
    """Get leaderboard"""
    try:
        response = await http_client.get(f"{ORDERBOOK_API_URL}/leaderboard")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/news")
async def publish_news(request: Request):
    """Publish news"""
    try:
        data = await request.json()
        response = await http_client.post(f"{ORDERBOOK_API_URL}/news", json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error publishing news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/news")
async def get_news(limit: Optional[int] = None):
    """Get news history"""
    try:
        params = {"limit": limit} if limit else {}
        response = await http_client.get(f"{ORDERBOOK_API_URL}/news", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance")
async def get_performance_metrics():
    """Get orderbook performance metrics"""
    try:
        # ORDERBOOK_API_URL is "http://orderbook:8000/api"
        # Performance endpoint is at "/api/performance" on orderbook server
        # So we call "http://orderbook:8000/api/performance"
        url = f"{ORDERBOOK_API_URL}/performance"
        logger.info(f"Fetching performance metrics from: {url}")
        response = await http_client.get(url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Performance metrics fetched successfully")
        return data
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching performance metrics from {url}: {e.response.text}")
        return _get_default_metrics()
    except Exception as e:
        logger.error(f"Error fetching performance metrics from {url}: {e}")
        return _get_default_metrics()


def _get_default_metrics():
    """Return default performance metrics."""
    return {
        "trades_per_second": 0,
        "orders_per_second": 0,
        "total_volume": 0,
        "total_trades": 0,
        "total_orders": 0,
        "queue_full_count": 0,
        "queue_capacity": 1024,
        "queue_usage_pct": 0,
        "uptime_seconds": 0,
        "avg_trades_per_second": 0,
        "avg_orders_per_second": 0
    }


@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """Bidirectional proxy between dashboard and OrderBook WebSocket."""
    await websocket.accept()
    import websockets
    
    try:
        orderbook_ws = await websockets.connect(ORDERBOOK_WS_URL)
    except Exception as exc:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Failed to connect to OrderBook WebSocket: {exc}"
        }))
        await websocket.close()
        return
    
    async def forward_to_orderbook():
        try:
            while True:
                data = await websocket.receive_text()
                await orderbook_ws.send(data)
        except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
            pass
    
    async def forward_to_dashboard():
        try:
            async for data in orderbook_ws:
                await websocket.send_text(data)
        except (websockets.exceptions.ConnectionClosed, RuntimeError):
            pass
    
    tasks = [
        asyncio.create_task(forward_to_orderbook()),
        asyncio.create_task(forward_to_dashboard())
    ]
    
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
    
    try:
        await orderbook_ws.close()
    except Exception:
        pass
    try:
        await websocket.close()
    except Exception:
        pass


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await http_client.aclose()


if __name__ == "__main__":
    print("Starting Admin Dashboard Server...")
    print(f"OrderBook API: {ORDERBOOK_API_URL}")
    print(f"OrderBook WebSocket: {ORDERBOOK_WS_URL}")
    print("Dashboard: http://localhost:8080")
    
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

