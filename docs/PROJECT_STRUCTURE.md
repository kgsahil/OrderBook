# OrderBook Project Structure

This document provides a detailed overview of the three-component architecture.

## Component Architecture

The project is organized into three completely independent components:

```
Orderbook/
├── orderbook/              # OrderBook Component (Core Trading Engine)
├── dashboard/              # Dashboard Component (Admin Interface)
├── agents/                 # Agents Component (AI Trading Agents)
├── docs/                   # Documentation
├── interview_version/      # Simplified interview implementation
└── docker-compose.yml      # Service orchestration
```

## Component Details

### 1. OrderBook Component (`orderbook/`)

**Purpose:** Core trading engine with C++ backend and Python WebSocket server

**Structure:**
```
orderbook/
├── apps/                          # Application entry points
│   ├── ob_cli.cpp                # Command-line interface
│   └── ob_server.cpp             # TCP server for WebSocket bridge
│
├── include/orderbook/            # Public C++ header files
│   ├── book/                     # OrderBook implementation
│   ├── core/                     # Core types and utilities
│   ├── engine/                   # Matching engine
│   ├── events/                   # Event system
│   ├── handlers/                 # I/O handlers
│   ├── oms/                      # Order Management System
│   ├── processors/               # Order processing
│   └── queue/                    # Lock-free data structures
│
├── src/orderbook/                # C++ implementation files
│   ├── book/
│   ├── engine/
│   ├── oms/
│   └── processors/
│
├── websocket_server/             # Python WebSocket server
│   ├── server.py                # FastAPI WebSocket server
│   ├── requirements.txt         # Python dependencies
│   ├── models/                  # Data models
│   └── services/                # Business logic services
│
├── docker/                       # Docker configuration
│   └── supervisord.conf         # Process manager config
│
├── CMakeLists.txt                # CMake build configuration
├── Dockerfile                    # Component Dockerfile
└── README.md                     # Component documentation
```

**Ports:** 8000 (WebSocket + REST API)

**Dependencies:** None (can run independently)

### 2. Dashboard Component (`dashboard/`)

**Purpose:** Admin interface for managing the trading simulation

**Structure:**
```
dashboard/
├── static/                       # Static web assets
│   └── index.html               # Admin dashboard UI
├── server.py                    # FastAPI server (proxy)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Component Dockerfile
└── README.md                    # Component documentation
```

**Ports:** 8080 (Admin UI)

**Dependencies:** Requires OrderBook service

**Features:**
- WebSocket proxy to OrderBook
- REST API proxy to OrderBook
- Admin UI for managing instruments, agents, news

### 3. Agents Component (`agents/`)

**Purpose:** AI trading agents with optional LLM support, plus local ML and statistical heuristic strategies

**Structure:**
```
agents/
├── config/                       # Agent configuration
│   └── agent_config.yaml       # Agent settings
├── agent_base.py               # Base agent class
├── langraph_agent.py           # LLM-based agent
├── agent_runner.py             # Agent manager
├── run_agents.py               # Entry point
├── agent_entrypoint.sh         # Docker entrypoint
├── requirements.txt            # Python dependencies
├── Dockerfile                   # Component Dockerfile
└── README.md                   # Component documentation
```

**Ports:** None (connects to OrderBook via WebSocket)

**Dependencies:** Requires OrderBook service

**Features:**
- Multiple configurable agents with personalities
- Optional LLM-based decision making (Gemini, OpenAI, Anthropic) when `ENABLE_LLM=true` and an API key is provided
- Local ML strategy (RandomForest) controlled via `USE_ML_FALLBACK` / config
- Statistical heuristic strategies with personality-based behavior
- Real-time orderbook access
- Automatic connection management

## Documentation (`docs/`)

```
docs/
├── API_CONTRACT.md              # Inter-component communication protocols
├── API_REFERENCE.md             # WebSocket API documentation
├── ARCHITECTURE.md              # System architecture details
├── DOCKER_SETUP.md              # Docker deployment guide
├── INTERVIEW_GUIDE.md           # Interview preparation guide
├── REFACTORING_SUMMARY.md       # Component segregation details
├── RUNNING_SERVICES.md          # Service management guide
└── TROUBLESHOOTING.md           # Common issues and solutions
```

## Communication Flow

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Dashboard  │────────▶│  OrderBook  │◀────────│   Agents    │
│  (Port 8080)│         │  (Port 8000)│         │  (No Port)  │
└─────────────┘         └─────────────┘         └─────────────┘
      │                        │                        │
      │                        │                        │
      └────────────────────────┴────────────────────────┘
                    WebSocket + REST API
```

**Key Principles:**
- ✅ Complete component isolation
- ✅ Network-only communication
- ✅ No shared files
- ✅ Independent deployment

## File Naming Conventions

- **C++ Headers:** `snake_case.hpp`
- **C++ Sources:** `snake_case.cpp`
- **Python:** `snake_case.py`
- **HTML:** `lowercase.html`
- **Markdown:** `UPPERCASE.md` (root), `CAPITALIZED.md` (subdirs)
- **Config:** `lowercase.yml`, `lowercase.conf`

## Build Artifacts (Gitignored)

- `build/` - CMake build output
- `out/` - Alternative build output
- `*.o`, `*.a`, `*.so` - Compiled objects
- `*.exe` - Executables
- `__pycache__/` - Python bytecode
- `.vscode/`, `.idea/` - IDE settings

## Quick Navigation

| Want to... | Go to... |
|------------|----------|
| Understand the system | [README.md](README.md) |
| Get started quickly | [QUICKSTART.md](QUICKSTART.md) |
| Deploy with Docker | [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) |
| Learn the API | [docs/API_CONTRACT.md](docs/API_CONTRACT.md) |
| Understand architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Contribute code | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Prepare for interview | [docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) |
| Modify OrderBook | [orderbook/](orderbook/) |
| Modify Dashboard | [dashboard/](dashboard/) |
| Modify Agents | [agents/](agents/) |

## Development Workflow

### Making Changes to OrderBook

1. Edit C++ headers in `orderbook/include/orderbook/`
2. Edit C++ implementations in `orderbook/src/orderbook/`
3. Edit Python server in `orderbook/websocket_server/`
4. Rebuild: `cd orderbook && docker build -t orderbook-service -f Dockerfile .`
5. Or use docker-compose: `docker-compose up -d --build orderbook`

### Making Changes to Dashboard

1. Edit UI in `dashboard/static/index.html`
2. Edit server in `dashboard/server.py`
3. Rebuild: `cd dashboard && docker build -t dashboard-service -f Dockerfile .`
4. Or use docker-compose: `docker-compose up -d --build dashboard`

### Making Changes to Agents

1. Edit agent code in `agents/`
2. Edit config in `agents/config/agent_config.yaml`
3. Rebuild: `docker build -t agents-service -f agents/Dockerfile .`
4. Or use docker-compose: `docker-compose up -d --build agents`

## Component Independence

Each component:
- Has its own Dockerfile
- Has its own dependencies
- Can be built independently
- Can be deployed independently
- Communicates only via network protocols

## Adding New Features

### New Order Type (OrderBook)

1. Add type to `orderbook/include/orderbook/core/types.hpp`
2. Update matching logic in `orderbook/src/orderbook/engine/matching_engine.cpp`
3. Update TCP parser in `orderbook/apps/ob_server.cpp`
4. Update Python protocol in `orderbook/websocket_server/server.py`
5. Update Dashboard UI in `dashboard/static/index.html`

### New WebSocket Message Type

1. Define message in `docs/API_CONTRACT.md`
2. Add handler in `orderbook/websocket_server/server.py`
3. Update Dashboard to send/receive in `dashboard/static/index.html`
4. Update Agents to handle in `agents/langraph_agent.py`

### New Component

1. Create new directory (e.g., `newcomponent/`)
2. Add Dockerfile
3. Add to `docker-compose.yml`
4. Document in `docs/API_CONTRACT.md`
5. Update this file

## Maintenance

### Regular Updates

- Keep dependencies updated (requirements.txt, CMakeLists.txt)
- Update documentation when APIs change
- Add tests as functionality grows
- Profile performance periodically

### Code Quality

- Follow CONTRIBUTING.md guidelines
- Maintain SOLID principles
- Keep functions focused and small
- Document public APIs
- Use consistent naming

## License

All files in this project are licensed under MIT License. See [LICENSE](LICENSE) for details.
