# Dashboard Component

Admin dashboard for managing the trading simulation. Connects to OrderBook service via WebSocket and REST API.

## Architecture

- **FastAPI Server**: Web server and API proxy
- **WebSocket Proxy**: Forwards WebSocket connections to OrderBook
- **REST API Proxy**: Proxies all `/api/*` requests to OrderBook
- **Real-time UI**: Alpine.js + Tailwind CSS with live orderbook visualization

## Features

- **Real-time Orderbook**: Live bid/ask updates with depth visualization
- **Price Chart**: Per-second candlestick chart using LightweightCharts
- **Agent Management**: View agents, create new agents, view portfolios
- **Instrument Management**: Add/remove trading instruments
- **News Publishing**: Publish market news that affects agent behavior
- **Performance Metrics**: Real-time system metrics (trades/sec, orders/sec, queue usage)
- **Connection Status**: Visual indicator with automatic reconnection
- **Toast Notifications**: Non-blocking user feedback
- **Agent Activity**: Real-time agent trading activity with visual feedback

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

## External Dependencies

Requires OrderBook service to be running and accessible.

## Browser Compatibility

- Modern browsers with WebSocket support
- Chrome/Edge 90+, Firefox 88+, Safari 14+
- JavaScript ES6+ required

