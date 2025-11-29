# Docker Quick Start

## 🚀 Start All Components

```bash
# Set API key for agents
export GOOGLE_API_KEY=your_api_key

# Start all components
docker-compose up -d --build
```

This starts:
- **OrderBook** on port 8000 (WebSocket + REST API)
- **Dashboard** on port 8080 (Admin UI)
- **Agents** (connects to OrderBook)

## 📊 Access Services

- **Dashboard:** http://localhost:8080 (Admin interface)
- **OrderBook API:** http://localhost:8000 (WebSocket + REST API)

## 🚀 Start Components Individually

### OrderBook Only

```bash
docker-compose up -d orderbook
```

### Dashboard (requires OrderBook)

```bash
docker-compose up -d dashboard
```

### Agents (requires OrderBook)

```bash
export GOOGLE_API_KEY=your_api_key
docker-compose up -d agents
```

## 📊 View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orderbook
docker-compose logs -f dashboard
docker-compose logs -f agents
```

## 🛑 Stop

```bash
docker-compose down
```

## 🔧 Common Commands

```bash
# Rebuild after code changes
docker-compose up -d --build

# Rebuild specific component
docker-compose up -d --build orderbook
docker-compose up -d --build dashboard
docker-compose up -d --build agents

# Restart services
docker-compose restart

# Check status
docker-compose ps

# Shell into containers
docker exec -it orderbook-service bash    # OrderBook
docker exec -it dashboard-service bash    # Dashboard
docker exec -it agents-service bash      # Agents

# Health checks
curl http://localhost:8000/health  # OrderBook
curl http://localhost:8080/health  # Dashboard
```

## 📖 Full Documentation

- **Component Architecture:** [docs/API_CONTRACT.md](docs/API_CONTRACT.md)
- **Docker Setup:** [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md)
- **Troubleshooting:** [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

