# Dashboard Component

Admin dashboard for managing the trading simulation. Connects to the OrderBook service via WebSocket and REST API and provides real-time visibility into agents and their strategies (heuristic, ML, and optional LLM-powered).*** End Patch```}"`

## Architecture

- **FastAPI Server**: Web server and API proxy
- **WebSocket Proxy**: Forwards WebSocket connections to OrderBook
- **REST API Proxy**: Proxies all `/api/*` requests to OrderBook
- **Real-time UI**: Alpine.js + Tailwind CSS with live orderbook and agent visualization

# Features

- **Real-time Orderbook**: Live bid/ask updates with depth visualization
- **Price Chart**: Per-second candlestick chart using LightweightCharts
- **Agent Management**: View agents, create new agents, view portfolios
- **Instrument Management**: Add/remove trading instruments
- **News Publishing**: Publish market news that affects agent behavior and LLM/ML strategies
- **Performance Metrics**: Real-time system metrics (trades/sec, orders/sec, queue usage)
- **Connection Status**: Visual indicator with automatic reconnection
- **Toast Notifications**: Non-blocking user feedback
- **Agent Activity**: Real-time agent trading activity with visual feedback (works for heuristic, ML, and LLM-driven agents)

## Ports

- **8080**: Admin dashboard web interface

## Endpoints

- `GET /` - Dashboard UI
- `GET /health` - Health check (includes OrderBook status)
- `GET /ws` - WebSocket proxy to OrderBook
- `GET /api/*` - Proxied to OrderBook REST API
- `GET /api/performance` - Performance metrics (proxied to OrderBook)

## Building

```bash
docker build -t dashboard-service -f Dockerfile .
```

## Running

```bash
docker run -p 8080:8080 \
  -e ORDERBOOK_HOST=orderbook \
  -e ORDERBOOK_PORT=8000 \
  dashboard-service
```

Or via docker-compose:

```bash
docker-compose up dashboard
```

## Configuration

- `ORDERBOOK_HOST`: OrderBook service hostname (default: `orderbook`)
- `ORDERBOOK_PORT`: OrderBook service port (default: `8000`)

## Dependencies

- Python 3.10+
- FastAPI, uvicorn, websockets, httpx

## WebSocket Connection Features

The dashboard implements robust WebSocket connection handling:

- **Automatic Reconnection**: Exponential backoff (3s → 4.5s → 6.75s, max 30s)
- **Heartbeat Monitoring**: Sends ping every 30 seconds, detects stale connections
- **Connection Status**: Visual indicator showing connection state
- **Error Recovery**: Graceful error handling with JSON parsing protection
- **Message Queuing**: Queues messages when disconnected, sends on reconnect

## UI Features

- **Connection Status Indicator**: Shows Connected/Connecting/Error/Disconnected with retry count
- **Real-time Chart**: Per-second candlestick chart from executed trades
- **Orderbook Depth Visualization**: Visual depth chart showing cumulative volumes
- **Agent Card Flashing**: Visual feedback when agents place orders
- **Toast Notifications**: Non-blocking notifications for user actions
- **Performance Metrics Display**: Real-time system performance metrics

## Agent & Strategy Awareness

The dashboard is strategy-agnostic but **agent-aware**:

- Displays the actions of all agents, regardless of whether they use heuristic, ML, or LLM strategies
- Surfaces portfolio and performance metrics that let you compare different strategies side-by-side
- Works out-of-the-box with the agents described in `agents/README.md` and `agents/strategies/README.md`

## External Dependencies

Requires OrderBook service to be running and accessible.

## Browser Compatibility

- Modern browsers with WebSocket support
- Chrome/Edge 90+, Firefox 88+, Safari 14+
- JavaScript ES6+ required

