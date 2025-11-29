# OrderBook - High-Performance Trading System

[![C++20](https://img.shields.io/badge/C%2B%2B-20-blue.svg)](https://en.cppreference.com/w/cpp/20)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A production-grade limit order book and matching engine with real-time WebSocket trading interface. Built with modern C++20, featuring lock-free SPSC queues, SOLID design principles, and a segregated three-component architecture.

## 🏗️ Architecture

The system consists of three completely independent components:

1. **OrderBook** (`orderbook/`) - Core trading engine (C++ backend + Python WebSocket server)
2. **Agents** (`agents/`) - AI trading agents using LLMs
3. **Dashboard** (`dashboard/`) - Admin interface for managing the simulation

Components communicate only via network protocols (WebSocket/REST API). No file sharing between components.

## 🚀 Quick Start

### Docker (Recommended)

**Start all components:**
```bash
# Default: Agents use heuristic fallback strategy (no LLM required)
docker-compose up -d --build

# To enable LLM for agents (requires API key):
export ENABLE_LLM=true
export GOOGLE_API_KEY=your_api_key  # or OPENAI_API_KEY or ANTHROPIC_API_KEY
docker-compose up -d --build
```

**Or start individually:**
```bash
# Start OrderBook
docker-compose up -d orderbook

# Start Dashboard (requires OrderBook)
docker-compose up -d dashboard

# Start Agents (requires OrderBook)
# Default: Uses heuristic fallback strategy (no API key needed)
docker-compose up -d agents

# To enable LLM for agents:
export ENABLE_LLM=true
export GOOGLE_API_KEY=your_api_key
docker-compose up -d agents
```

**Access:**
- **Dashboard:** [http://localhost:8080](http://localhost:8080) - Admin interface
- **OrderBook API:** [http://localhost:8000](http://localhost:8000) - WebSocket + REST API

**Note:** 
- **Agents use heuristic fallback strategy by default** (no LLM/API key required)
- Set `ENABLE_LLM=true` to use LLM-based decision making (requires API key)
- Agents will automatically connect to OrderBook on startup
- If OrderBook connection fails, agents will terminate
- Dashboard proxies all requests to OrderBook

**API Documentation:** See [docs/API_CONTRACT.md](docs/API_CONTRACT.md)

### Manual Build

**OrderBook Component:**
```bash
cd orderbook
# Build C++ backend
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel

# Run TCP server + WebSocket interface
cd orderbook
./build/ob_server  # Terminal 1
cd websocket_server && python server.py  # Terminal 2
```

**Dashboard Component:**
```bash
cd dashboard
pip install -r requirements.txt
python server.py
```

**Agents Component:**
```bash
cd agents
pip install -r requirements.txt
python run_agents.py config/agent_config.yaml
```

## ✨ Features

### Core Engine
- ⚡ **Lock-Free Operations** - SPSC queues with relaxed atomics
- 🎯 **Price-Time Priority** - Standard FIFO matching algorithm
- 🏗️ **SOLID Architecture** - Clean, maintainable, extensible code
- 🔥 **High Performance** - O(log N) order operations, O(1) cancel
- 🧵 **Thread-Safe** - Lock-free communication between threads

### Trading Interface
- 🌐 **Real-Time WebSocket** - Sub-second orderbook updates
- 💻 **Modern Web UI** - Tailwind CSS + Alpine.js
- 👥 **Multi-Client Support** - Concurrent traders
- 📊 **Live OrderBook** - Bids and asks with depth
- 🎨 **Beautiful Design** - Professional trading interface

## 📊 Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard Component                       │
│                    (Port 8080)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Admin UI (HTML/JS)                                     │ │
│  │  FastAPI Server                                         │ │
│  │  WebSocket Proxy → OrderBook                            │ │
│  │  REST API Proxy → OrderBook                             │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket + REST API
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    OrderBook Component                       │
│                    (Port 8000)                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Python WebSocket Server (FastAPI)                    │ │
│  │  REST API + WebSocket API                              │ │
│  └──────────────┬─────────────────────────────────────────┘ │
│                 │ TCP (internal)                            │
│                 ▼                                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  C++ OrderBook Backend (OMS)                           │ │
│  │  Lock-Free SPSC Queues                                 │ │
│  │  Order Processor → Matching Engine                     │ │
│  │  OrderBook (Price-Time Priority)                       │ │
│  └────────────────────────────────────────────────────────┘ │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebSocket
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agents Component                          │
│                    (No exposed ports)                        │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  AI Trading Agents (LangGraph + LLM)                    │ │
│  │  WebSocket Client → OrderBook                           │ │
│  │  Real-time decision making                              │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Principles:**
- ✅ Complete component isolation
- ✅ Network-only communication
- ✅ No shared files
- ✅ Independent deployment

## 📁 Project Structure

```
Orderbook/
├── orderbook/              # OrderBook component (independent)
│   ├── apps/               # C++ applications
│   ├── include/            # C++ headers
│   ├── src/                # C++ sources
│   ├── websocket_server/   # Python WebSocket server
│   ├── docker/             # Supervisor config
│   ├── CMakeLists.txt      # C++ build config
│   └── Dockerfile          # OrderBook Dockerfile
│
├── dashboard/              # Dashboard component (independent)
│   ├── static/             # HTML/JS dashboard UI
│   ├── server.py           # FastAPI server
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Dashboard Dockerfile
│
├── agents/                 # Agents component (independent)
│   ├── config/             # Agent configuration
│   ├── agent_base.py       # Base agent class
│   ├── langraph_agent.py   # LLM-based agent
│   ├── agent_runner.py     # Agent manager
│   ├── run_agents.py       # Entry point
│   ├── requirements.txt    # Python dependencies
│   ├── agent_entrypoint.sh # Docker entrypoint
│   └── Dockerfile          # Agents Dockerfile
│
├── docs/                   # Documentation
│   ├── API_CONTRACT.md     # Inter-component API contract
│   └── ...
│
└── docker-compose.yml      # Orchestration for all components
```

**Component Independence:**
- Each component has its own directory
- Each component has its own Dockerfile
- No shared files between components
- Communication only via network protocols

```
Orderbook/
├── orderbook/              # OrderBook component (independent)
│   ├── apps/               # C++ applications
│   ├── include/            # C++ headers
│   ├── src/                # C++ sources
│   ├── websocket_server/   # Python WebSocket server
│   ├── docker/             # Supervisor config
│   ├── CMakeLists.txt      # C++ build config
│   └── Dockerfile          # OrderBook Dockerfile
│
├── dashboard/              # Dashboard component (independent)
│   ├── static/             # HTML/JS dashboard UI
│   ├── server.py           # FastAPI server
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Dashboard Dockerfile
│
├── agents/                 # Agents component (independent)
│   ├── config/             # Agent configuration
│   ├── agent_base.py       # Base agent class
│   ├── langraph_agent.py   # LLM-based agent
│   ├── agent_runner.py     # Agent manager
│   ├── run_agents.py       # Entry point
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Agents Dockerfile
│
├── docs/                   # Documentation
│   ├── API_CONTRACT.md     # Inter-component API contract
│   └── ...
│
└── docker-compose.yml      # Orchestration for all components
```

## 🎯 Use Cases

- **Learning**: Understand market microstructure and matching algorithms
- **Trading Systems**: Foundation for building trading infrastructure
- **Interviews**: Demonstrate system design and C++ expertise
- **Research**: Experiment with order matching strategies
- **Algorithmic Trading**: Base for building trading bots

## 🛠️ Technology Stack

**Backend (C++20)**
- STL containers (map, deque, unordered_map)
- Lock-free SPSC queues with memory ordering
- Multi-threading with std::thread
- TCP sockets (POSIX)

**Frontend (Python/JavaScript)**
- FastAPI - Modern web framework
- Uvicorn - ASGI server
- WebSockets - Real-time communication
- Tailwind CSS - UI styling
- Alpine.js - Reactive framework

**Infrastructure**
- Docker - Containerization
- Supervisor - Process management
- CMake - Build system

## 📈 Performance

| Operation | Complexity | Latency |
|-----------|-----------|---------|
| Add Order | O(log N) | ~1-5μs |
| Cancel Order | O(1) | ~0.5μs |
| Match Order | O(log N) per level | ~2-10μs |
| Queue Operations | O(1) | ~100ns |

*Measured on Intel i7, Ubuntu 22.04*

## 📚 Documentation

**Quick Start:**
- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[Docker Quick Start](docs/DOCKER_QUICKSTART.md)** - Docker-specific guide

**Architecture & Setup:**
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Complete project organization
- **[Docker Setup Guide](docs/DOCKER_SETUP.md)** - Complete Docker deployment guide
- **[API Contract](docs/API_CONTRACT.md)** - Inter-component communication protocols
- **[Architecture](docs/ARCHITECTURE.md)** - System design and patterns

**Reference:**
- **[API Reference](docs/API_REFERENCE.md)** - WebSocket and REST API
- **[Running Services](docs/RUNNING_SERVICES.md)** - Manual service management
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Interview Guide](docs/INTERVIEW_GUIDE.md)** - Simplified 1-hour implementation

**See [docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md) for complete documentation index.**

## 🎓 Key Concepts

### Lock-Free SPSC Queue
Single-producer, single-consumer ring buffer using:
- `memory_order_relaxed` for local reads
- `memory_order_acquire` for shared reads
- `memory_order_release` for shared writes
- 64-byte cache line alignment to prevent false sharing

### Price-Time Priority
- Orders at better prices execute first
- Orders at same price execute FIFO (first-in, first-out)
- Partial fills supported
- Market orders execute at best available price

### SOLID Principles
- **S**ingle Responsibility - Each class has one job
- **O**pen/Closed - Extensible without modification
- **L**iskov Substitution - Interfaces properly implemented
- **I**nterface Segregation - Small, focused interfaces
- **D**ependency Inversion - Depend on abstractions

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Docker Hub**: (Coming soon)
- **Documentation**: [./docs](./docs)
- **Issue Tracker**: GitHub Issues
- **Discussions**: GitHub Discussions

## ⚠️ Disclaimer

This is an educational project. Not suitable for production trading without extensive testing, risk management, and regulatory compliance.

## 🙏 Acknowledgments

- Inspired by modern exchange architectures
- Built for learning and demonstration purposes
- Community contributions and feedback

---

**Made with ❤️ for the trading technology community**
