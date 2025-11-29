# API Contract Documentation

This document defines the communication protocols between the three components:
1. **OrderBook** - Core trading engine
2. **Agents** - AI trading agents
3. **Dashboard** - Admin interface

## Component Communication

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

## OrderBook Service

### Endpoints

**Base URL:** `http://orderbook:8000` (internal) or `http://localhost:8000` (external)

#### REST API

- `GET /health` - Health check
- `GET /api/instruments` - List all instruments
- `POST /api/instruments` - Add new instrument
  ```json
  {
    "ticker": "AAPL",
    "description": "Apple Inc.",
    "industry": "Technology",
    "initial_price": 150.0
  }
  ```
- `DELETE /api/instruments/{symbol_id}` - Remove instrument
- `GET /api/agents` - List all agents
- `GET /api/agents/{agent_id}` - Get agent details
- `GET /api/agents/{agent_id}/portfolio` - Get agent portfolio
- `GET /api/agents/{agent_id}/trades` - Get agent trades
- `GET /api/leaderboard` - Get leaderboard
- `POST /api/news` - Publish news
  ```json
  {
    "headline": "Market Rally",
    "content": "Stocks are up...",
    "sentiment": 0.8,
    "source": "Bloomberg"
  }
  ```
- `GET /api/news` - Get news history
- `GET /api/performance` - Get system performance metrics
  ```json
  {
    "trades_per_second": 12.5,
    "orders_per_second": 45.2,
    "total_trades": 1250,
    "total_orders": 4520,
    "total_volume": 125000.50,
    "queue_full_count": 0,
    "queue_capacity": 1024,
    "queue_usage_pct": 0.0,
    "uptime_seconds": 3600.5,
    "avg_trades_per_second": 0.35,
    "avg_orders_per_second": 1.26
  }
  ```

#### WebSocket

**Endpoint:** `ws://orderbook:8000/ws`

**Client Messages (to OrderBook):**

1. **Agent Registration**
   ```json
   {
     "type": "agent_register",
     "agent_id": "agent_123",
     "name": "Trader Bot",
     "personality": "aggressive",
     "starting_capital": 100000.0
   }
   ```

2. **Place Order**
   ```json
   {
     "type": "add_order",
     "symbol_id": 1,
     "side": "buy",
     "orderType": "LIMIT",
     "price": 150.50,
     "quantity": 100,
     "agent_id": "agent_123"
   }
   ```

3. **Cancel Order**
   ```json
   {
     "type": "cancel_order",
     "symbol_id": 1,
     "orderId": 12345
   }
   ```

4. **Get Portfolio**
   ```json
   {
     "type": "get_portfolio",
     "agent_id": "agent_123"
   }
   ```

**Server Messages (from OrderBook):**

1. **Orderbooks Update**
   ```json
   {
     "type": "orderbooks",
     "data": {
       "1": {
         "status": "success",
         "symbol_id": 1,
         "bids": [{"price": 150.00, "quantity": 100, "orders": 2}],
         "asks": [{"price": 150.50, "quantity": 200, "orders": 1}]
       }
     }
   }
   ```

2. **Instruments List**
   ```json
   {
     "type": "instruments",
     "data": [
       {
         "symbol_id": 1,
         "ticker": "AAPL",
         "description": "Apple Inc.",
         "industry": "Technology",
         "initial_price": 150.0
       }
     ]
   }
   ```

3. **Portfolio Update**
   ```json
   {
     "type": "portfolio_update",
     "cash": 95000.0,
     "positions": {
       "1": {
         "instrument_id": 1,
         "quantity": 100,
         "avg_price": 150.00,
         "current_price": 155.00,
         "market_value": 15500.00,
         "unrealized_pnl": 500.00
       }
     },
     "total_value": 110000.0,
     "pnl": 10000.0
   }
   ```

4. **News**
   ```json
   {
     "type": "news",
     "data": {
       "id": "uuid",
       "headline": "Breaking news...",
       "content": "Details...",
       "sentiment": 0.5,
       "source": "System",
       "created_at": "2025-01-01T12:00:00"
     }
   }
   ```

5. **News History**
   ```json
   {
     "type": "news_history",
     "data": [ ... ]
   }
   ```

6. **Order Response**
   ```json
   {
     "type": "order_response",
     "data": {
       "status": "success",
       "order_id": 12345,
       "message": "Order added"
     }
   }
   ```

7. **Cancel Response**
   ```json
   {
     "type": "cancel_response",
     "data": {
       "status": "success",
       "message": "Order cancelled"
     }
   }
   ```

8. **Order Placed (Notification)**
   ```json
   {
     "type": "order_placed",
     "data": {
       "agent_id": "agent_123",
       "agent_name": "Trader Bot",
       "symbol_id": 1,
       "ticker": "AAPL",
       "side": "buy",
       "order_type": "LIMIT",
       "price": 150.50,
       "quantity": 100,
       "timestamp": "2025-01-01T12:00:00"
     }
   }
   ```

9. **Agent Registered**
   ```json
   {
     "type": "agent_registered",
     "agent_id": "agent_123",
     "agent": {
       "agent_id": "agent_123",
       "name": "Trader Bot",
       "personality": "aggressive",
       "cash": 100000.0,
       "positions": {},
       "total_value": 100000.0,
       "pnl": 0.0
     }
   }
   ```

10. **Agents Snapshot**
    ```json
    {
      "type": "agents_snapshot",
      "data": [ ... ]
    }
    ```

11. **Agent Created (Real-time)**
    ```json
    {
      "type": "agent_created",
      "data": {
        "agent_id": "agent_123",
        "name": "New Trader",
        "personality": "aggressive",
        "starting_capital": 100000.0,
        "created_at": "2025-01-01T12:00:00"
      }
    }
    ```
    **Note:** Broadcast when agent is created via Dashboard. Agent runners listen for this to auto-spawn agents.

12. **Ping/Pong (Heartbeat)**
    ```json
    {
      "type": "ping"
    }
    ```
    ```json
    {
      "type": "pong"
    }
    ```
    **Note:** Used for connection health monitoring. Clients should send ping every 30 seconds.

## Dashboard Service

### Endpoints

**Base URL:** `http://dashboard:8080` (internal) or `http://localhost:8080` (external)

- `GET /` - Dashboard UI
- `GET /health` - Health check (includes OrderBook status)
- `GET /ws` - WebSocket proxy to OrderBook

All `/api/*` endpoints are proxied to OrderBook service.

## Agents Service

### Configuration

Agents connect to OrderBook via WebSocket at `ws://orderbook:8000/ws`.

**Environment Variables:**
- `WS_URL` - WebSocket URL (default: `ws://orderbook:8000/ws`)
- `GOOGLE_API_KEY` - Google Gemini API key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `LLM_PROVIDER` - LLM provider (default: `gemini`)
- `LLM_MODEL` - Model name (default: `gemini-2.0-flash-exp`)

**Behavior:**
- Agents must register via `agent_register` message
- Agents receive orderbook updates and news via WebSocket
- Agents place orders via `add_order` message
- If OrderBook connection fails, agents terminate

## Network Configuration

All services communicate via Docker bridge network `trading-network`.

**Service Discovery:**
- OrderBook: `orderbook:8000`
- Dashboard: `dashboard:8080`
- Agents: No exposed ports (connects to OrderBook only)

## Port Mapping

- **OrderBook:** `8000:8000` (WebSocket + REST API)
- **Dashboard:** `8080:8080` (Admin UI)
- **Agents:** No exposed ports

## Message Format

All WebSocket messages are JSON strings.

**Common Fields:**
- `type` - Message type (required)
- `data` - Message payload (optional)
- `agent_id` - Agent identifier (for agent-specific messages)

## Error Handling

**Connection Failures:**
- Agents: Terminate after `MAX_RETRIES` failed connection attempts
- Dashboard: 
  - Automatic reconnection with exponential backoff (3s → 4.5s → 6.75s, max 30s)
  - Connection status indicator in UI (Connected/Connecting/Error/Disconnected)
  - Heartbeat monitoring (detects stale connections after 60s of no messages)
  - Manual reconnect button available
  - Shows error in health check, continues running
- OrderBook: Logs errors, continues serving other clients

**Message Errors:**
- Invalid messages are logged and ignored (with error handling to prevent crashes)
- Order rejections are sent via `order_response` with `status: "error"`
- JSON parsing errors are caught and logged without breaking the connection
- Unknown message types are logged but don't cause errors

**Price/Quantity Validation:**
- Multi-layer validation ensures no orders with price ≤ 0 or quantity ≤ 0 are processed
- Validation occurs at: Agent → WebSocket Server → TCP Server → Matching Engine → Order Book
- Invalid orders are rejected with appropriate error messages

