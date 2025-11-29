# Running Services Independently

The trading simulation consists of three independent components that can be run separately or together.

## Component Overview

1. **OrderBook** - Core trading engine (C++ backend + Python WebSocket server)
2. **Dashboard** - Admin interface (Python FastAPI server)
3. **Agents** - AI trading agents (Python)

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# Start OrderBook
docker-compose up -d orderbook

# Start Dashboard (requires OrderBook)
docker-compose up -d dashboard

# Start Agents (requires OrderBook)
export GOOGLE_API_KEY=your_key
docker-compose up -d agents
```

See [DOCKER_SEPARATE.md](DOCKER_SEPARATE.md) for details.

### Option 2: Manual Start (Development)

#### 1. Start OrderBook Component

**Terminal 1: Build and run C++ backend**

```bash
cd orderbook

# Build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# Run
./build/ob_server
```

The C++ server listens on **port 9999** (TCP, internal).

**Terminal 2: Start Python WebSocket server**

```bash
cd orderbook/websocket_server

# Install dependencies (first time only)
pip install -r requirements.txt

# Run
python server.py
```

The WebSocket server listens on **port 8000** (HTTP/WebSocket).

**Environment Variables:**
- `BROADCAST_INTERVAL` - Orderbook broadcast interval in seconds (default: 0.2 = 200ms)

#### 2. Start Dashboard Component

**Terminal 3: Start Dashboard**

```bash
cd dashboard

# Install dependencies (first time only)
pip install -r requirements.txt

# Run
python server.py
```

The Dashboard listens on **port 8080** (HTTP).

**Environment Variables:**
- `ORDERBOOK_HOST` - OrderBook service hostname (default: `localhost`)
- `ORDERBOOK_PORT` - OrderBook service port (default: `8000`)

#### 3. Start Agents Component

**Terminal 4: Start AI Agents**

```bash
cd agents

# Install dependencies (first time only)
pip install -r requirements.txt

# Set API key
export GOOGLE_API_KEY=your_google_api_key

# Run agents
python run_agents.py config/agent_config.yaml
```

**Environment Variables:**
- `WS_URL` - OrderBook WebSocket URL (default: `ws://localhost:8000/ws`)
- `GOOGLE_API_KEY` - Google Gemini API key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `LLM_PROVIDER` - LLM provider (default: `gemini`)
- `LLM_MODEL` - Model name (default: `gemini-2.0-flash-exp`)

## Service Dependencies

```
┌─────────────────────┐
│  OrderBook          │  (Port 8000 - WebSocket + REST API)
│  Component          │  (Port 9999 - TCP, internal)
│  - C++ Backend      │
│  - WebSocket Server │
└──────────┬──────────┘
           │
           │ WebSocket + REST API
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌──────────┐  ┌──────────┐
│ Dashboard│  │  Agents  │
│ (Port    │  │ (No Port)│
│  8080)   │  │          │
└──────────┘  └──────────┘
```

**Dependency Chain:**
- OrderBook: No dependencies (can run standalone)
- Dashboard: Requires OrderBook
- Agents: Requires OrderBook

## Component Details

### OrderBook Component

**Files:**
- `orderbook/apps/ob_server.cpp` - C++ TCP server
- `orderbook/websocket_server/server.py` - Python WebSocket server

**Ports:**
- 8000: WebSocket + REST API (exposed)
- 9999: TCP (internal, C++ backend)

**Start Order:**
1. C++ backend first (`ob_server`)
2. Then Python WebSocket server

### Dashboard Component

**Files:**
- `dashboard/server.py` - FastAPI server
- `dashboard/static/index.html` - Admin UI

**Ports:**
- 8080: HTTP (exposed)

**Start Order:**
1. After OrderBook is running

### Agents Component

**Files:**
- `agents/run_agents.py` - Entry point
- `agents/langraph_agent.py` - LLM-based agent
- `agents/config/agent_config.yaml` - Configuration

**Ports:**
- None (connects to OrderBook)

**Start Order:**
1. After OrderBook is running

## Health Checks

### OrderBook

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "connections": 0,
  "agents": 0,
  "instruments": 0,
  "backend": "localhost:9999"
}
```

### Dashboard

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "ok",
  "orderbook": {
    "status": "ok",
    ...
  },
  "orderbook_url": "http://orderbook:8000/api"
}
```

## Troubleshooting

### OrderBook: "Cannot connect to backend"

- Ensure C++ backend (`ob_server`) is running
- Check port 9999 is not blocked
- Verify TCP connection: `nc localhost 9999`

### Dashboard: "Cannot connect to OrderBook"

- Ensure OrderBook is running: `curl http://localhost:8000/health`
- Check `ORDERBOOK_HOST` and `ORDERBOOK_PORT` environment variables
- Verify network connectivity

### Agents: "Connection failed"

- Ensure OrderBook is running: `curl http://localhost:8000/health`
- Check `WS_URL` environment variable
- Verify WebSocket endpoint: `ws://localhost:8000/ws`
- Check agent logs for connection errors

### Port Conflicts

```bash
# Find process using port
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

## Development Workflow

### Making Changes

1. **OrderBook C++ changes:**
   - Edit files in `orderbook/include/` or `orderbook/src/`
   - Rebuild: `cmake --build build`
   - Restart: `./build/ob_server`

2. **OrderBook Python changes:**
   - Edit `orderbook/websocket_server/server.py`
   - Restart: `python server.py`

3. **Dashboard changes:**
   - Edit `dashboard/server.py` or `dashboard/static/index.html`
   - Restart: `python server.py`

4. **Agents changes:**
   - Edit files in `agents/`
   - Restart: `python run_agents.py config/agent_config.yaml`

### Testing

```bash
# Test OrderBook API
curl http://localhost:8000/api/instruments

# Test Dashboard
curl http://localhost:8080/api/instruments

# Test WebSocket (using wscat)
wscat -c ws://localhost:8000/ws
```

## Production Deployment

For production, use Docker:

```bash
docker-compose up -d --build
```

This ensures:
- Proper process management
- Health checks
- Automatic restarts
- Network isolation
- Resource limits

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for details.

## Next Steps

- **Component Architecture:** [API_CONTRACT.md](API_CONTRACT.md)
- **Docker Setup:** [DOCKER_SETUP.md](DOCKER_SETUP.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
