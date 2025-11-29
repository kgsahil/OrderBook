# System Architecture & Data Flow

This document provides a comprehensive visual and textual representation of the OrderBook system architecture, data flows, and component interactions. It is designed to complement the high-level [ARCHITECTURE.md](ARCHITECTURE.md) by focusing on the dynamic behavior of the system.

## 1. High-Level Architecture

The OrderBook system follows a segregated, multi-tier architecture designed for high performance, isolation, and scalability.

```mermaid
graph TD
    subgraph "Presentation Layer"
        Dashboard[Dashboard UI]
        Traders[Trading Clients]
    end

    subgraph "Application Layer"
        WS_Server[Python WebSocket Server]
        API[REST API]
    end

    subgraph "Business Logic Layer"
        TCP_Server[C++ TCP Server<br/>Uses IOrderBookService Interface]
        OMS[Order Management System<br/>Implements IOrderBookService]
        ME[Matching Engine]
        OB[OrderBook]
    end

    subgraph "Agent Layer"
        Agents[AI Trading Agents]
    end

    Dashboard <-->|WebSocket JSON| WS_Server
    Traders <-->|WebSocket JSON| WS_Server
    Agents <-->|WebSocket JSON| WS_Server
    
    WS_Server <-->|TCP JSON<br/>Connection Pool| TCP_Server
    
    TCP_Server -->|SPSC Queue| OMS
    OMS -->|Order Object| ME
    ME -->|Match/Add| OB
    OB -->|Events| OMS
    OMS -->|Response JSON| TCP_Server
```

### Component Responsibilities

*   **Presentation Layer**: Handles user interaction and visualization. It communicates exclusively via WebSockets.
*   **Application Layer (Python)**: Acts as the gateway. It manages WebSocket connections, performs initial validation, and bridges the external JSON protocol to the internal TCP protocol. Uses connection pooling for efficient TCP communication with the C++ backend.
*   **Business Logic Layer (C++)**: The core engine. It executes orders with low latency using lock-free data structures. It is isolated from the network handling of the application layer. The TCP server uses dependency injection via `IOrderBookService` interface for testability and flexibility.
*   **Agent Layer**: Autonomous trading bots (LLM-enabled when configured, otherwise ML + heuristic strategies) that interact with the system exactly like human traders.

---

## 2. Core Workflows

### 2.1 Order Submission Lifecycle

The path of an order from creation to execution is the most critical flow in the system.

```mermaid
sequenceDiagram
    participant Agent as Client (Agent/UI)
    participant WS as WebSocket Server (Py)
    participant TCP as TCP Server (C++)
    participant OMS as Order Processor
    participant ME as Matching Engine
    participant DB as Dashboard UI

    Note over Agent, DB: 1. Submission & Validation
    Agent->>WS: {type: "add_order", side: "buy", ...}
    WS->>WS: Validate JSON Schema
    alt Invalid Schema
        WS-->>Agent: {type: "error", msg: "Invalid format"}
    else Valid Schema
        WS->>TCP: {"action": "add", "order": {...}}
    end
    
    Note over TCP, ME: 2. High-Performance Processing
    TCP->>OMS: Push to Lock-Free SPSC Queue
    OMS->>OMS: Pop Order & Business Validation
    OMS->>ME: Submit to Matching Engine
    
    alt Match Found (Immediate Execution)
        ME->>ME: Match with Best Ask
        ME-->>OMS: TradeEvent (Filled)
    else No Match (Passive Order)
        ME->>ME: Insert into OrderBook
        ME-->>OMS: OrderAcceptedEvent
    end
    
    Note over OMS, DB: 3. Broadcast & Notification
    OMS-->>TCP: Serialize Event to JSON
    TCP-->>WS: Forward Response
    
    par Broadcast Updates
        WS-->>Agent: {type: "order_response", status: "success"}
        WS-->>DB: {type: "order_placed", data: {...}}
        WS-->>DB: {type: "orderbooks", data: {...}}
    end
```

### 2.2 Agent Registration & State Sync

How agents and dashboards initialize and stay in sync.

```mermaid
sequenceDiagram
    participant Client as New Client
    participant WS as WebSocket Server
    participant State as State Managers

    Client->>WS: Connect /ws
    WS-->>Client: Accept Connection
    
    par Initial State Push
        State->>WS: Get Instruments
        WS-->>Client: {type: "instruments", data: [...]}
        
        State->>WS: Get OrderBooks
        WS-->>Client: {type: "orderbooks", data: {...}}
        
        State->>WS: Get News History
        WS-->>Client: {type: "news_history", data: [...]}
        
        State->>WS: Get Agents List
        WS-->>Client: {type: "agents_snapshot", data: [...]}
    end
    
    opt Agent Registration
        Client->>WS: {type: "agent_register", name: "Bot1", ...}
        WS->>State: Register Agent
        WS-->>Client: {type: "agent_registered", agent_id: "..."}
        WS-->>Client: {type: "portfolio_update", ...}
    end
```

### 2.3 Market Data Broadcast

Efficiently propagating state changes to thousands of clients.

```mermaid
graph LR
    ME[Matching Engine] -->|State Change| EB[Event Publisher]
    EB -->|1. Internal Event| TCP[TCP Server]
    TCP -->|2. JSON Serialization| WS[WebSocket Server]
    
    subgraph "Fan-Out"
        WS -->|3. Broadcast| C1[Client 1]
        WS -->|3. Broadcast| C2[Client 2]
        WS -->|3. Broadcast| C3[Dashboard]
        WS -->|3. Broadcast| C4[Agent]
    end
```

### 2.4 Dashboard WebSocket Proxy Flow

End-to-end flow for a dashboard browser client connecting via the dashboard WebSocket proxy to the OrderBook server and C++ backend.

```mermaid
sequenceDiagram
    participant UI as Browser (Dashboard UI)
    participant DWS as Dashboard /ws
    participant OBWS as OrderBook /ws
    participant State as State & Services
    participant TCP as C++ TCP Server
    participant OMS as Order Processor
    participant ME as Matching Engine
    participant OB as OrderBook

    Note over UI,DWS: 1. Connect WebSocket
    UI->>DWS: WebSocket handshake /ws
    DWS->>OBWS: WebSocket handshake /ws
    OBWS-->>DWS: Accept
    DWS-->>UI: Accept

    Note over OBWS,UI: 2. Initial State Push
    OBWS->>State: Load instruments, orderbooks, news, agents
    State-->>OBWS: Instruments + snapshots + news + agents
    OBWS-->>DWS: {type: \"instruments\" | \"orderbooks\" | \"news_history\" | \"agents_snapshot\"}
    DWS-->>UI: Forward messages unchanged

    Note over UI,OB: 3. Place Order via WebSocket
    UI->>DWS: {\"type\":\"add_order\", ...}
    DWS->>OBWS: Forward JSON
    OBWS->>TCP: add_order(symbol_id, side, type, price, qty)
    TCP->>OMS: Push to SPSC queue
    OMS->>ME: Submit order
    ME->>OB: Match / add
    OB-->>ME: Events (trade / accepted)
    ME-->>OMS: Events
    OMS-->>TCP: JSON result
    TCP-->>OBWS: Result JSON
    OBWS-->>DWS: {\"type\":\"order_response\", data:{...}}
    DWS-->>UI: Forward response

    Note over OBWS,UI: 4. Broadcast Updates
    OBWS->>State: Refresh snapshots + portfolios
    State-->>OBWS: Updated books + agent stats
    OBWS-->>DWS: {\"type\":\"orderbooks\"} / {\"type\":\"agents_snapshot\"} / {\"type\":\"order_placed\"}
    DWS-->>UI: Forward to browser
```

### 2.5 Dashboard REST Proxy Flow

Flow for REST calls from the dashboard UI to the OrderBook API (used for instruments, agents, news, performance).

```mermaid
sequenceDiagram
    participant UI as Browser (Dashboard UI)
    participant DAPI as Dashboard /api/*
    participant OBAPI as OrderBook /api/*
    participant Svc as Services (Instrument/Agent/News/Performance)
    participant TCP as C++ TCP Server
    participant OMS as Order Processor
    participant ME as Matching Engine
    participant OB as OrderBook

    Note over UI,DAPI: 1. REST Request (e.g. create instrument)
    UI->>DAPI: POST /api/instruments {ticker, initial_price, ...}
    DAPI->>OBAPI: POST /api/instruments {...}

    Note over OBAPI,OB: 2. Business Logic
    OBAPI->>Svc: validate + create instrument
    Svc->>TCP: ensure instrument in C++ backend (if needed)
    TCP->>OMS: Control / config command
    OMS->>ME: update routing
    ME->>OB: adjust internal state
    OB-->>ME: ack
    ME-->>OMS: ack
    OMS-->>TCP: ack
    TCP-->>Svc: success

    Note over Svc,UI: 3. Broadcast & Response
    Svc-->>OBAPI: instrument created
    OBAPI-->>DAPI: 201 {instrument...}
    DAPI-->>UI: JSON response
    Svc->>OBWS: trigger broadcast_instruments_update()
```

### 2.6 Agents Service Lifecycle & Auto-Spawning

How the separate Agents service (agent runner) interacts with OrderBook and Dashboard to create and run agents.

```mermaid
sequenceDiagram
    participant UI as Dashboard UI
    participant DAPI as Dashboard /api/agents
    participant OBAPI as OrderBook /api/agents
    participant OBWS as OrderBook /ws
    participant Runner as Agents Service (AgentRunner)
    participant Agent as LangGraphAgent (single agent)

    Note over UI,OBAPI: 1. Create Agent Metadata (via REST)
    UI->>DAPI: POST /api/agents {name, personality, starting_capital}
    DAPI->>OBAPI: POST /api/agents {...}
    OBAPI->>OBAPI: Validate & create Agent model
    OBAPI-->>DAPI: 201 {agent_id, ...}
    DAPI-->>UI: Agent created (metadata only)

    Note over OBWS,Runner: 2. Broadcast agent_created & spawn in Agents service
    OBAPI->>OBWS: broadcast_agent_created(agent)
    OBWS-->>Runner: {type:"agent_created", data:{agent_id,...}}
    Runner->>Runner: _create_agent_from_data() → build LangGraphAgent

    Note over Agent,OBWS: 3. Agent connects & registers via WebSocket
    Agent->>OBWS: Connect /ws
    OBWS-->>Agent: instruments + orderbooks + news_history
    Agent->>OBWS: {type:"agent_register", agent_id, name, personality, starting_capital}
    OBWS->>OBWS: register_agent(...) in AgentManager
    OBWS-->>Agent: {type:"agent_registered", agent_id, agent:{...}}
    OBWS-->>Agent: {type:"portfolio_update", ...}

    Note over Agent,OBWS: 4. Trading loop
    OBWS-->>Agent: {type:"orderbooks"} / {type:"news"} (stream)
    Agent->>Agent: Decide using LLM (optional) → ML → heuristic
    Agent->>OBWS: {type:"add_order", ...}
    OBWS->>...: Order submission flow (see 2.1)
    OBWS-->>Agent: {type:"order_response", ...}
    OBWS-->>Agent: {type:"portfolio_update", ...}
```

### 2.7 News & Broadcast Flow

How news is published from the dashboard and propagated to agents and dashboards.

```mermaid
sequenceDiagram
    participant UI as Dashboard UI
    participant DAPI as Dashboard /api/news
    participant OBAPI as OrderBook /api/news
    participant NewsSvc as NewsService
    participant OBWS as OrderBook /ws
    participant Agent as Agents
    participant DB as Dashboards

    Note over UI,OBAPI: 1. Publish news via REST
    UI->>DAPI: POST /api/news {content, instrument_id?, impact_type?}
    DAPI->>OBAPI: POST /api/news {...}
    OBAPI->>NewsSvc: publish_news(...)
    NewsSvc-->>OBAPI: news object

    Note over OBWS,DB: 2. Broadcast to all WebSocket clients
    OBAPI->>OBWS: broadcast_news_update(news)
    OBWS-->>Agent: {type:"news", data:{...}}
    OBWS-->>DB: {type:"news", data:{...}}

    Note over Agent,DB: 3. Consumption
    Agent->>Agent: Incorporate news into strategy (LLM/ML/heuristic)
    DB->>DB: Update UI (news feed, visual cues)
```

### 2.8 Performance Metrics Flow

How performance metrics are collected inside OrderBook and exposed to the Dashboard.

```mermaid
sequenceDiagram
    participant OBWS as OrderBook /ws
    participant Metrics as performance_metrics
    participant DAPI as Dashboard /api/performance
    participant OBAPI as OrderBook /api/performance
    participant UI as Dashboard UI

    Note over OBWS,Metrics: 1. Metrics collection
    OBWS->>Metrics: record_order(qty) on successful add_order
    OBWS->>Metrics: record_trade(qty) when trades inferred/recorded
    OBWS->>Metrics: record_queue_full() on queue full events

    Note over UI,OBAPI: 2. Metrics request from dashboard
    UI->>DAPI: GET /api/performance
    DAPI->>OBAPI: GET /api/performance
    OBAPI->>Metrics: get_stats()
    Metrics-->>OBAPI: JSON metrics
    OBAPI-->>DAPI: metrics JSON
    DAPI-->>UI: metrics JSON (charts, stats)
```

### 2.9 Event Triggers Overview

Summary of key events and what they trigger across services:

- **`agent_created` (WebSocket, from OrderBook)**:
  - Emitted when a new agent is created via REST (`POST /api/agents`).
  - **Consumers**: Agents service (`AgentRunner`) listens and spawns matching `LangGraphAgent` instances.
- **`agent_register` / `agent_registered` (WebSocket)**:
  - `agent_register` sent by agents when they connect.
  - `agent_registered` + initial `portfolio_update` sent by OrderBook to confirm registration and seed state.
- **`add_order` (WebSocket)**:
  - Sent by agents and dashboards to place trades.
  - Triggers full order processing path: WebSocket → TCP → OMS → Matching Engine → OrderBook → events → broadcasts (`orderbooks`, `order_placed`, `portfolio_update`, metrics).
- **`news` / `news_history` (WebSocket)**:
  - Emitted after REST `POST /api/news` and on initial connection.
  - Used by agents as an input signal for strategies; used by dashboards to show market news.
- **`orderbooks` / `agents_snapshot` (WebSocket)**:
  - Emitted on initial connection, on periodic sync, and after key events (orders, price moves, portfolio updates).
  - Keep dashboards and agents in sync with current market and agent state.

---

## 3. Data Structures & Models

### 3.1 OrderBook Internal Design

The C++ core uses specialized data structures for O(1) and O(log N) performance.

```mermaid
classDiagram
    class OrderBook {
        -map~Price, Level, Greater~ m_bids
        -map~Price, Level, Less~ m_asks
        -unordered_map~OrderId, OrderPtr~ m_orders
        +addOrder(OrderPtr)
        +cancelOrder(OrderId)
        +match(OrderPtr)
    }

    class Level {
        +Price price
        +Quantity totalQuantity
        +deque~OrderPtr~ orders
    }

    class Order {
        +OrderId id
        +Price price
        +Quantity quantity
        +Quantity filledQuantity
        +Side side
        +Timestamp timestamp
    }

    OrderBook "1" *-- "many" Level : contains
    Level "1" *-- "many" Order : FIFO Queue
    OrderBook ..> Order : Fast Lookup
```

---

## 4. Protocol Messages

### 4.1 WebSocket Messages (Client <-> Server)

#### Client Requests

| Type | Description | Payload Example |
|------|-------------|-----------------|
| `agent_register` | Register a new trading agent | `{"type": "agent_register", "name": "Alpha", "starting_capital": 100000}` |
| `add_order` | Place a new limit/market order | `{"type": "add_order", "symbol_id": 1, "side": "buy", "price": 100, "quantity": 10}` |
| `cancel_order` | Cancel an active order | `{"type": "cancel_order", "symbol_id": 1, "orderId": 12345}` |
| `get_portfolio` | Request current portfolio state | `{"type": "get_portfolio", "agent_id": "..."}` |

#### Server Broadcasts & Responses

| Type | Description | Payload Example |
|------|-------------|-----------------|
| `instruments` | List of tradable instruments | `{"type": "instruments", "data": [{"ticker": "AAPL", ...}]}` |
| `orderbooks` | Full orderbook snapshots | `{"type": "orderbooks", "data": {1: {"bids": [], "asks": []}}}` |
| `order_response` | Ack/Nack for `add_order` | `{"type": "order_response", "data": {"status": "success", "order_id": 123}}` |
| `cancel_response` | Ack/Nack for `cancel_order` | `{"type": "cancel_response", "data": {"status": "success"}}` |
| `order_placed` | Notification of new order (for UI) | `{"type": "order_placed", "data": {"ticker": "AAPL", "price": 100, ...}}` |
| `portfolio_update` | Agent cash/position update | `{"type": "portfolio_update", "cash": 50000, "positions": {...}}` |
| `agents_snapshot` | List of all active agents | `{"type": "agents_snapshot", "data": [...]}` |
| `news` | Real-time news event | `{"type": "news", "data": {"headline": "...", "sentiment": 0.5}}` |
| `news_history` | Historical news items | `{"type": "news_history", "data": [...]}` |

### 4.2 TCP Messages (Internal Python <-> C++)

**Command (Python -> C++):**
```json
{
  "action": "add",
  "order": {
    "id": 12345,
    "price": 10050,
    "qty": 10,
    "side": 1
  }
}
```

---

## 5. Error Handling Flows

How the system manages failures.

```mermaid
stateDiagram-v2
    [*] --> Validation
    
    state "Python Validation" as PyVal
    state "C++ Validation" as CppVal
    state "Execution" as Exec
    
    Validation --> PyVal
    PyVal --> ErrorResponse: Invalid JSON/Types
    PyVal --> CppVal: Valid
    
    CppVal --> ErrorResponse: Invalid Logic (e.g. Price < 0)
    CppVal --> Exec: Valid
    
    Exec --> [*]: Success
    
    state ErrorResponse {
        [*] --> LogError
        LogError --> SendErrorToClient
        SendErrorToClient --> [*]
    }
```

---

## 6. Design Improvements

### 6.1 Dependency Injection via IOrderBookService Interface

The TCP server has been refactored to use dependency injection, following the Dependency Inversion Principle (SOLID).

**Architecture:**
```mermaid
classDiagram
    class IOrderBookService {
        <<interface>>
        +submitOrder(Order) bool
        +cancelOrder(symbolId, orderId) bool
        +getBidsSnapshot(symbolId, depth) vector
        +getAsksSnapshot(symbolId, depth) vector
        +processEvents() void
        +setEventCallback(callback) void
    }
    
    class InstrumentManager {
        +submitOrder(Order) bool
        +cancelOrder(symbolId, orderId) bool
        +getBidsSnapshot(symbolId, depth) vector
        +getAsksSnapshot(symbolId, depth) vector
        +processEvents() void
        +setEventCallback(callback) void
    }
    
    class OrderBookServer {
        -service_ IOrderBookService*
        +OrderBookServer(port, service)
        +processRequest(request) string
    }
    
    IOrderBookService <|.. InstrumentManager
    OrderBookServer --> IOrderBookService : depends on abstraction
```

**Benefits:**
- ✅ **Testability**: Can inject mock services for unit testing
- ✅ **Swappable Implementations**: Easy to swap different OMS implementations
- ✅ **SOLID Compliance**: Follows Dependency Inversion Principle
- ✅ **Maintainability**: Changes to InstrumentManager don't require TCP server changes

**Implementation:**
- Interface defined in `orderbook/include/orderbook/oms/i_order_book_service.hpp`
- `InstrumentManager` implements `IOrderBookService`
- `OrderBookServer` accepts optional `IOrderBookService` in constructor (defaults to `InstrumentManager`)

### 6.2 Connection Pooling for Python TCP Client

The Python WebSocket server now uses connection pooling for efficient TCP communication with the C++ backend.

**Architecture:**
```mermaid
sequenceDiagram
    participant WS as WebSocket Server
    participant Pool as Connection Pool
    participant TCP as TCP Server
    
    Note over WS,Pool: Connection Pool Lifecycle
    
    WS->>Pool: get_connection()
    alt Pool has available connection
        Pool-->>WS: Return existing socket
    else Pool empty or all busy
        Pool->>TCP: Create new connection
        TCP-->>Pool: Socket
        Pool-->>WS: Return socket
    end
    
    WS->>TCP: Send command via pooled socket
    TCP-->>WS: Response
    
    WS->>Pool: return_connection(socket)
    Pool->>Pool: Validate & store in pool
    
    Note over Pool: Idle timeout cleanup
    Pool->>Pool: Close idle connections (>30s)
```

**Features:**
- **Thread-Safe**: Multiple WebSocket clients can share the pool safely
- **Configurable Pool Size**: Default 5 connections, adjustable
- **Idle Timeout**: Connections idle >30s are closed automatically
- **Health Checking**: Invalid connections are detected and replaced
- **Retry Logic**: Exponential backoff on connection failures
- **Graceful Degradation**: Falls back to new connections if pool exhausted

**Performance Benefits:**
- Reduced connection overhead (reuse vs. create per request)
- Lower latency for subsequent requests (no TCP handshake)
- Better resource management (bounded pool size)
- Improved throughput under load

**Configuration:**
```python
# Default (pooling enabled)
client = OrderBookClient(host="localhost", port=9999)

# Custom pool settings
client = OrderBookClient(
    host="localhost",
    port=9999,
    use_pooling=True,
    max_connections=10,
    connection_timeout=5.0
)
```

**Files:**
- `orderbook/websocket_server/services/orderbook_client.py` - Connection pool implementation
