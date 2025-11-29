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
        TCP_Server[C++ TCP Server]
        OMS[Order Management System]
        ME[Matching Engine]
        OB[OrderBook]
    end

    subgraph "Agent Layer"
        Agents[AI Trading Agents]
    end

    Dashboard <-->|WebSocket JSON| WS_Server
    Traders <-->|WebSocket JSON| WS_Server
    Agents <-->|WebSocket JSON| WS_Server
    
    WS_Server <-->|TCP JSON| TCP_Server
    
    TCP_Server -->|SPSC Queue| OMS
    OMS -->|Order Object| ME
    ME -->|Match/Add| OB
    OB -->|Events| OMS
    OMS -->|Response JSON| TCP_Server
```

### Component Responsibilities

*   **Presentation Layer**: Handles user interaction and visualization. It communicates exclusively via WebSockets.
*   **Application Layer (Python)**: Acts as the gateway. It manages WebSocket connections, performs initial validation, and bridges the external JSON protocol to the internal TCP protocol.
*   **Business Logic Layer (C++)**: The core engine. It executes orders with low latency using lock-free data structures. It is isolated from the network handling of the application layer.
*   **Agent Layer**: Autonomous trading bots that interact with the system exactly like human traders.

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
