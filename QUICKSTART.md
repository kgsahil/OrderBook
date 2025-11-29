# 🚀 Quick Start Guide

Get the OrderBook trading system running in under 5 minutes!

## Prerequisites

- **Docker & Docker Compose** (Recommended) - [Install Docker](https://docs.docker.com/get-docker/)

OR

- **C++ Build Tools:** g++ 10+, CMake 3.20+
- **Python:** 3.11+
- **Linux:** Ubuntu 20.04+ or similar

## Option 1: Docker (Easiest) ⭐

### 1. Start All Components

```bash
# (Optional) enable LLM-powered agents
export ENABLE_LLM=true
export GOOGLE_API_KEY=your_api_key  # or OPENAI_API_KEY / ANTHROPIC_API_KEY

# Start all components
docker-compose up -d --build
```

This will:
- Build and start OrderBook (C++ backend + Python WebSocket server)
- Build and start Dashboard (Admin interface)
- Build and start Agents (they always run; LLM is only used if `ENABLE_LLM=true` and an API key is set)

### 2. Open Your Browser

Navigate to: **http://localhost:8080** (Dashboard)

Or access OrderBook API directly: **http://localhost:8000**

You should see the admin dashboard!

### 3. Try It Out

1. **Select "Buy"** or "Sell"
2. **Choose order type:** Limit (with price) or Market
3. **Enter quantity**
4. **Click the button** to place your order
5. **Watch the orderbook update** in real-time

### 4. Test Multi-Client

Open the same URL in multiple browser tabs - they all share the same orderbook!

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific component
docker-compose logs -f orderbook
docker-compose logs -f dashboard
docker-compose logs -f agents
```

### Stop the System

```bash
docker-compose down
```

### Rebuild After Changes

```bash
# Rebuild all
docker-compose up -d --build

# Rebuild specific component
docker-compose up -d --build orderbook
docker-compose up -d --build dashboard
docker-compose up -d --build agents
```

---

## Option 2: Manual Build

### 1. Build OrderBook Component

```bash
cd orderbook

# Build C++ backend
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# Start C++ server
./build/ob_server
```

Leave this terminal open - you should see:
```
[INFO] Order Book Server starting on port 9999...
[INFO] Server ready
```

### 2. Start OrderBook WebSocket Server

Open a **new terminal**:

```bash
cd orderbook/websocket_server

# Install dependencies (first time only)
pip install -r requirements.txt

# Start server
python server.py
```

You should see:
```
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 3. Start Dashboard (Optional)

Open a **new terminal**:

```bash
cd dashboard

# Install dependencies (first time only)
pip install -r requirements.txt

# Start server
python server.py
```

### 4. Start Agents (Optional)

Open a **new terminal**:

```bash
cd agents

# Install dependencies (first time only)
pip install -r requirements.txt

# (Optional) enable LLM-powered decisions
export ENABLE_LLM=true
export GOOGLE_API_KEY=your_api_key  # or OPENAI_API_KEY / ANTHROPIC_API_KEY

# Start agents (will use local ML + heuristic strategies if LLM is disabled or no key is set)
python run_agents.py config/agent_config.yaml
```

### 5. Open Browser

Navigate to: **http://localhost:8080** (Dashboard)

---

## 🎯 What's Happening?

```
┌──────────────┐
│   Dashboard  │  ← You interact here (Admin UI)
└──────┬───────┘
       │ WebSocket + REST API
       ▼
┌──────────────┐
│  OrderBook   │  ← Core trading engine
│  Component   │
│  ┌─────────┐ │
│  │ Python │ │  ← WebSocket Server
│  │ Server │ │
│  └───┬─────┘ │
│      │ TCP   │
│      ▼       │
│  ┌─────────┐ │
│  │ C++ OMS │ │  ← Matching Engine
│  └─────────┘ │
└──────┬───────┘
       │ WebSocket
       ▼
┌──────────────┐
│   Agents     │  ← AI Trading Agents
└──────────────┘
```

1. You manage the system via Dashboard
2. Dashboard proxies requests to OrderBook
3. OrderBook processes orders via C++ backend
4. Agents connect and trade automatically
5. Updates broadcast to all connected clients

---

## 🧪 Test Commands

### CLI Mode (Without WebSocket)

```bash
cd orderbook
# Build first
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# Run interactive CLI
./build/ob_cli
```

Commands:
- `buy 100.50 10` - Buy 10 @ $100.50
- `sell 101.00 5` - Sell 5 @ $101.00
- `market buy 10` - Market buy 10
- `snapshot` - View orderbook
- `help` - Show all commands
- `quit` - Exit

### TCP Test (Advanced)

```bash
# Connect directly to C++ backend
nc localhost 9999

# Try commands:
ADD B L 100.50 10
SNAPSHOT
```

---

## 📊 Example Trading Session

1. **Open browser** to http://localhost:8000
2. **Place a buy order:** Buy 10 @ $100.00 (limit)
3. **Place a sell order:** Sell 5 @ $100.00 (limit)
4. **Watch the trade execute!** 5 units match immediately
5. **Check orderbook:** Remaining 5 buy @ $100.00

---

## ❓ Troubleshooting

### Docker: "Cannot connect to Docker daemon"

```bash
# Start Docker Desktop (Windows/Mac) or
sudo systemctl start docker  # Linux
```

### Docker: "Port 8000 already in use"

```bash
# Find and kill process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

### Manual Build: "CMake version too old"

```bash
# Ubuntu/Debian
sudo apt-get install cmake

# Or download latest from cmake.org
```

### Manual Build: "Cannot connect to backend"

- Ensure `ob_server` is running (check Terminal 1)
- Verify no firewall blocking port 9999
- Try: `netstat -an | grep 9999`

### Browser: "Connection failed"

- Check OrderBook is running: `curl http://localhost:8000/health`
- Check Dashboard is running: `curl http://localhost:8080/health`
- Check browser console (F12) for WebSocket errors
- Try different browser (Chrome/Firefox recommended)

---

## 🎓 Next Steps

- **Read the docs:** [docs/](docs/) folder
  - [API_CONTRACT.md](docs/API_CONTRACT.md) - Component communication
  - [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
  - [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) - Detailed Docker guide
  - [INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) - Simplified implementation

- **Explore the code:**
  - `orderbook/apps/ob_server.cpp` - C++ TCP server
  - `orderbook/include/orderbook/` - C++ headers
  - `orderbook/websocket_server/server.py` - Python WebSocket server
  - `dashboard/server.py` - Dashboard server
  - `dashboard/static/index.html` - Admin UI
  - `agents/langraph_agent.py` - AI agent implementation

- **Contribute:** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 💡 Tips

- **Performance:** The system can handle 500K+ orders/sec
- **Concurrency:** Open 10+ browser tabs to test multi-client
- **Learning:** Check `interview_version/` for simplified 1-hour implementation
- **Extending:** Add new order types, cancel orders, or market data

---

**Need help?** Open an issue on GitHub!

**Enjoying the project?** ⭐ Star it on GitHub!

