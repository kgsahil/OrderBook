# Docker Setup Guide

This guide explains how to run the complete OrderBook Trading System with three independent components using Docker.

## 🐳 Quick Start

### Prerequisites

- Docker installed (version 20.10+)
- Docker Compose (optional, but recommended)
- Google API Key (optional, for AI agents)

### Start All Components

```bash
# Set API key for agents (optional)
export GOOGLE_API_KEY=your_api_key

# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Access the Application

- **Dashboard (Admin UI):** http://localhost:8080
- **OrderBook API:** http://localhost:8000

## 📋 Architecture

The system consists of three independent Docker containers:

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│  OrderBook Container│         │  Dashboard Container│         │  Agents Container   │
│                     │         │                     │         │                     │
│  ┌──────────────┐   │         │  ┌──────────────┐   │         │  ┌──────────────┐   │
│  │  ob_server   │   │         │  │  FastAPI     │   │         │  │  AI Agents   │   │
│  │  (C++)       │   │         │  │  Server      │   │         │  │  (LangGraph) │   │
│  │  Port 9999   │←──┼─────────┼─▶│  Port 8080   │   │         │  │  No Port    │   │
│  │  (internal)  │   │  TCP    │  └──────┬───────┘   │         │  └──────┬──────┘   │
│  └──────┬───────┘   │         │         │           │         │         │          │
│         │            │         │         │ Proxy      │         │         │ WS       │
│         │            │         │         ▼            │         │         ▼          │
│  ┌──────▼───────┐   │         │  ┌──────────────┐   │         │  ┌──────────────┐   │
│  │  WebSocket   │   │         │  │  OrderBook  │   │         │  │  OrderBook   │   │
│  │  Server      │◄──┼─────────┼─▶│  API        │   │         │  │  WebSocket   │   │
│  │  Port 8000   │   │  WS/API │  └──────────────┘   │         │  └──────────────┘   │
│  └──────────────┘   │         │                     │         │                     │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
```

### Component Details

1. **OrderBook Container** (`orderbook-service`)
   - C++ backend (port 9999, internal)
   - Python WebSocket server (port 8000, exposed)
   - No external dependencies

2. **Dashboard Container** (`dashboard-service`)
   - FastAPI server (port 8080, exposed)
   - WebSocket proxy to OrderBook
   - REST API proxy to OrderBook
   - Requires OrderBook service

3. **Agents Container** (`agents-service`)
   - AI trading agents (no exposed ports)
   - Connects to OrderBook via WebSocket
   - Requires OrderBook service

## 🚀 Running Components Separately

### Start OrderBook Only

```bash
docker-compose up -d orderbook
```

Check health:
```bash
curl http://localhost:8000/health
```

### Start Dashboard (After OrderBook)

```bash
docker-compose up -d dashboard
```

Access: http://localhost:8080

### Start Agents (After OrderBook)

```bash
export GOOGLE_API_KEY=your_api_key
docker-compose up -d agents
```

## 📊 Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orderbook
docker-compose logs -f dashboard
docker-compose logs -f agents

# Follow specific log file (inside container)
docker exec orderbook-service tail -f /var/log/supervisor/ob_server.log
docker exec orderbook-service tail -f /var/log/supervisor/websocket_server.log
```

## 🔧 Configuration

### Environment Variables

**OrderBook:**
- `BROADCAST_INTERVAL` - Orderbook update interval (default: 0.2 seconds)

**Dashboard:**
- `ORDERBOOK_HOST` - OrderBook service hostname (default: `orderbook`)
- `ORDERBOOK_PORT` - OrderBook service port (default: `8000`)

**Agents:**
- `WS_URL` - OrderBook WebSocket URL (default: `ws://orderbook:8000/ws`)
- `GOOGLE_API_KEY` - Google Gemini API key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `LLM_PROVIDER` - LLM provider (default: `gemini`)
- `LLM_MODEL` - Model name (default: `gemini-2.0-flash-exp`)
- `MAX_RETRIES` - Connection retry attempts (default: `5`)
- `RETRY_DELAY` - Retry delay in seconds (default: `5`)

### Using .env File

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your_api_key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.0-flash-exp
```

Then run:
```bash
docker-compose up -d --build
```

## 🛠️ Building Components

### Build All

```bash
docker-compose build
```

### Build Specific Component

```bash
# OrderBook
docker-compose build orderbook

# Dashboard
docker-compose build dashboard

# Agents
docker-compose build agents
```

### Rebuild After Code Changes

```bash
# Rebuild all
docker-compose up -d --build

# Rebuild specific component
docker-compose up -d --build orderbook
```

## 🔍 Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

### Container Won't Start

```bash
# Check logs
docker-compose logs orderbook

# Check container status
docker-compose ps

# Restart
docker-compose restart orderbook
```

### Agents Can't Connect

```bash
# Check OrderBook is running
curl http://localhost:8000/health

# Check agent logs
docker-compose logs agents

# Verify network
docker network inspect orderbook_trading-network
```

### Dashboard Can't Connect to OrderBook

```bash
# Check OrderBook health
curl http://localhost:8000/health

# Check Dashboard logs
docker-compose logs dashboard

# Verify service names
docker-compose ps
```

## 🧹 Cleanup

### Stop All Containers

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

### Remove All Images

```bash
docker-compose down --rmi all
```

### Clean Docker System

```bash
# Remove unused containers, networks, images
docker system prune

# Remove everything (including volumes)
docker system prune -a --volumes
```

## 📚 Additional Resources

- **Component Architecture:** [docs/API_CONTRACT.md](API_CONTRACT.md)
- **Quick Start:** [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
- **Running Separately:** [DOCKER_SEPARATE.md](DOCKER_SEPARATE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 🎯 Next Steps

1. **Access Dashboard:** http://localhost:8080
2. **Add Instruments:** Use Dashboard to add trading instruments
3. **Start Agents:** Set API key and start agents
4. **Monitor Trading:** Watch agents trade in real-time
5. **View Leaderboard:** Check agent performance in Dashboard
