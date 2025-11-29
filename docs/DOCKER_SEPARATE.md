# Running Components Separately

The system consists of three independent components that can be run separately or together.

## Architecture

```
┌─────────────────────┐         ┌─────────────────────┐         ┌─────────────────────┐
│  OrderBook Container│         │  Dashboard Container│         │  Agents Container   │
│                     │         │                     │         │                     │
│  - C++ Backend      │         │  - Admin UI         │         │  - AI Agents        │
│  - WebSocket Server │◄────────┤  - API Proxy        │         │  (LangGraph)        │
│  Port 8000          │  API    │  Port 8080          │         │  No Port            │
└─────────────────────┘         └─────────────────────┘         └─────────────────────┘
```

## Quick Start

### 1. Start OrderBook Only

```bash
# Start OrderBook container
docker-compose up -d orderbook

# Check status
docker-compose ps

# View logs
docker-compose logs -f orderbook

# Access API
curl http://localhost:8000/health
```

### 2. Start Dashboard (Requires OrderBook)

```bash
# Start Dashboard container
docker-compose up -d dashboard

# View logs
docker-compose logs -f dashboard

# Access Dashboard
# Open http://localhost:8080 in browser
```

### 3. Start Agents (Requires OrderBook)

```bash
# Set API key
export GOOGLE_API_KEY=your_api_key

# Start agents container
docker-compose up -d agents

# View agent logs
docker-compose logs -f agents
```

### 4. Start All Together

```bash
# Set API key
export GOOGLE_API_KEY=your_api_key

# Start all components
docker-compose up -d --build
```

## Component Dependencies

- **OrderBook:** No dependencies (can run standalone)
- **Dashboard:** Requires OrderBook
- **Agents:** Requires OrderBook

## Service Discovery

Components communicate via Docker service names:
- OrderBook: `orderbook:8000`
- Dashboard: `dashboard:8080`
- Agents: Connects to `orderbook:8000`

## Health Checks

```bash
# Check OrderBook
curl http://localhost:8000/health

# Check Dashboard (includes OrderBook status)
curl http://localhost:8080/health
```

## Stopping Components

```bash
# Stop all
docker-compose down

# Stop specific component
docker-compose stop orderbook
docker-compose stop dashboard
docker-compose stop agents
```

## Rebuilding Components

```bash
# Rebuild all
docker-compose up -d --build

# Rebuild specific component
docker-compose up -d --build orderbook
docker-compose up -d --build dashboard
docker-compose up -d --build agents
```

## Component Isolation

Each component:
- Has its own Dockerfile
- Has its own dependencies
- Can be built independently
- Can be deployed independently
- Communicates only via network protocols

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for communication protocols.
