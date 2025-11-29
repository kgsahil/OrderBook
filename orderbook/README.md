# OrderBook Component

The core trading engine component providing orderbook functionality, WebSocket API, and REST API.

## Architecture

- **C++ Backend**: High-performance orderbook matching engine
- **Python WebSocket Server**: Real-time API for clients and agents
- **TCP Communication**: Internal communication between Python and C++

## Ports

- **8000**: WebSocket server and REST API

## Endpoints

See [API_CONTRACT.md](../docs/API_CONTRACT.md) for full API documentation.

## Building

```bash
docker build -t orderbook-service -f Dockerfile .
```

## Running

```bash
docker run -p 8000:8000 orderbook-service
```

Or via docker-compose:

```bash
docker-compose up orderbook
```

## Configuration

- `BROADCAST_INTERVAL`: Orderbook update interval in seconds (default: 0.2)

## Dependencies

- C++20 compiler
- Python 3.10+
- FastAPI, uvicorn, websockets

## No External Dependencies

This component does not depend on Dashboard or Agents. It can run independently.

