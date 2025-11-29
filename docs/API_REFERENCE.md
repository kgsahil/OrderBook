# OrderBook API Reference

Complete reference for interacting with the OrderBook system via WebSocket and TCP protocols.

## WebSocket API (Port 8000)

**Endpoint:** `ws://localhost:8000/ws`

Connect using standard WebSocket API. All messages are JSON strings.

### Message Types

#### 1. Order Submission

**Client → Server**

```json
{
    "type": "add_order",
    "symbol_id": 1,
    "side": "buy",
    "orderType": "LIMIT",
    "price": 100.50,
    "quantity": 10,
    "agent_id": "optional_agent_id"
}
```

**Fields:**
- `type` (string): "add_order"
- `symbol_id` (integer): Instrument ID (default 1)
- `side` (string): "buy" or "sell"
- `orderType` (string): "LIMIT" or "MARKET"
- `price` (number): Limit price (required for limit orders)
- `quantity` (number): Order quantity (positive integer)
- `agent_id` (string): Optional agent identifier

**Server Response:**

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

#### 2. OrderBook Snapshot

**Server → Client** (Broadcast)

```json
{
    "type": "orderbooks",
    "data": {
        "1": {
            "status": "success",
            "symbol_id": 1,
            "bids": [
                {"price": 100.50, "quantity": 150, "orders": 2}
            ],
            "asks": [
                {"price": 100.75, "quantity": 100, "orders": 1}
            ]
        }
    }
}
```

#### 3. Order Placed Notification

**Server → Client** (Broadcast to all clients)

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
        "price": 100.50,
        "quantity": 10,
        "timestamp": "2025-01-01T12:00:00"
    }
}
```

**Note:** This message is sent when an order is successfully placed and executed. The price in this message represents the execution price (for market orders) or limit price (for limit orders).

#### 4. Agent Created (Real-time Notification)

**Server → Client** (Broadcast to all clients, including agent runners)

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

**Note:** This message is broadcast when a new agent is created via the Dashboard UI. Agent runners listen for this message to automatically spawn and start the new agent.

#### 5. Agent Registration

**Client → Server**

```json
{
    "type": "agent_register",
    "agent_id": "agent_123",
    "name": "Trader Bot",
    "personality": "aggressive",
    "starting_capital": 100000.0
}
```

**Server Response:**

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

#### 6. Portfolio Update

**Server → Client** (To specific agent)

```json
{
    "type": "portfolio_update",
    "cash": 95000.0,
    "positions": {
        "1": {
            "instrument_id": 1,
            "quantity": 100,
            "avg_price": 150.00
        }
    },
    "total_value": 110000.0,
    "pnl": 10000.0
}
```

#### 7. News

**Server → Client** (Broadcast)

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

#### 8. Ping/Pong (Heartbeat)

**Client → Server**
```json
{
    "type": "ping"
}
```

**Server → Client**
```json
{
    "type": "pong"
}
```

**Note:** Used for connection health monitoring. Clients should send ping every 30 seconds. Server responds with pong. If no messages are received for 60 seconds, connection is considered stale.

## TCP Protocol (Port 9999)

Used internally by the WebSocket server to communicate with C++ backend.

### Message Format

Messages are newline-delimited JSON (`\n` terminated).

#### Submit Order

```
{"action":"add","order":{"type":"limit","side":"buy","price":10050,"qty":10}}\n
```
*Note: Price is in cents (integer)*

#### Get OrderBook

```
{"action":"get"}\n
```

## Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 1000 | Invalid order type | Type must be "LIMIT" or "MARKET" |
| 1001 | Invalid side | Side must be "buy" or "sell" |
| 1002 | Invalid price | Price must be positive for limit orders |
| 1003 | Invalid quantity | Quantity must be positive integer |
| 1004 | Order rejected | Order validation failed at orderbook level |

**Price Validation:**
- All LIMIT orders must have `price > 0`
- Price validation occurs at multiple levels:
  1. Client/Agent level (before sending)
  2. WebSocket server level
  3. C++ TCP server level
  4. Matching engine level
  5. Order book level

**Quantity Validation:**
- All orders must have `quantity > 0`
- Validated at all levels before processing

## Performance Metrics API

### GET /api/performance

Returns real-time system performance metrics.

**Response:**
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

**Fields:**
- `trades_per_second` - Current trades per second (rolling 1-second window)
- `orders_per_second` - Current orders per second (rolling 1-second window)
- `total_trades` - Total trades executed since startup
- `total_orders` - Total orders processed since startup
- `total_volume` - Total volume traded (quantity × price)
- `queue_full_count` - Number of times SPSC queue was full
- `queue_capacity` - SPSC queue capacity (default: 1024)
- `queue_usage_pct` - Queue usage percentage
- `uptime_seconds` - Server uptime in seconds
- `avg_trades_per_second` - Average trades per second since startup
- `avg_orders_per_second` - Average orders per second since startup

## Best Practices

### Client Implementation

**Reconnection:**
- Implement exponential backoff (3s → 4.5s → 6.75s, max 30s)
- Maximum 10 reconnection attempts
- Check connection state before creating new connections

**Heartbeat:**
- Send ping every 30 seconds: `{"type": "ping"}`
- Monitor for stale connections (no messages for 60 seconds)
- Server responds with `{"type": "pong"}`

**Error Handling:**
- Wrap JSON parsing in try-catch blocks
- Queue messages when disconnected, send on reconnect
- Handle WebSocket errors gracefully without breaking connection

## Support

For API questions or issues:
- Email: sahilgupta.17299@gmail.com
