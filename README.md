# Orderbook: High-Performance Limit Order Book and Matching Engine (C++20)

## Overview

Single-instrument, price-time priority limit order book and matching engine designed for very low latency and high throughput. Built with SOLID principles, lock-free SPSC queues, and clean architecture with no third-party runtime dependencies.

## Features

- ✅ **Lock-free operations**: SPSC (Single Producer Single Consumer) queues using relaxed atomics
- ✅ **SOLID principles**: Clean architecture with proper separation of concerns
- ✅ **Event-driven**: Asynchronous event publishing via lock-free queues
- ✅ **Thread-safe**: Lock-free communication between threads
- ✅ **High performance**: O(log N) order operations, O(1) cancel

## Build

```bash
cmake -S . -B build
cmake --build build --parallel
```

## Usage

```bash
./build/ob_cli
```

Commands:
- `add B|S L|M <price> <qty>` - Add order (Buy/Sell, Limit/Market)
- `cancel <order_id>` - Cancel order
- `snap` - Show order book snapshot
- `q` - Quit

Example:
```
add B L 100 10
add S L 101 5
snap
```

## Architecture

### System Architecture

```
┌─────────────────┐
│  Input Thread   │
│  (CLI/Network)  │
└────────┬────────┘
         │
         │ submitOrder()
         ▼
┌─────────────────────────┐
│   SPSC Order Queue      │  ← Lock-free (relaxed atomics)
│  (Single Producer)      │
└────────┬────────────────┘
         │
         │ tryPop()
         ▼
┌─────────────────────────┐
│   Order Processor       │  ← Consumer thread
│   (Processing Loop)     │
└────────┬────────────────┘
         │
         │ process()
         ▼
┌─────────────────────────┐
│   Matching Engine       │
└────────┬────────────────┘
         │
         ├─► OrderBook (add/cancel)
         │
         └─► Event Publisher
                 │
                 ▼
         ┌─────────────────────────┐
         │   SPSC Event Queue      │  ← Lock-free
         │  (Single Producer)      │
         └────────┬────────────────┘
                  │
                  │ tryPop()
                  ▼
         ┌─────────────────────────┐
         │   Output Handler        │  ← Consumer (main thread)
         │   (Event Callback)      │
         └─────────────────────────┘
```

### Class Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      OrderManagementSystem                   │
│                         (Facade Pattern)                     │
├─────────────────────────────────────────────────────────────┤
│ + submitOrder(Order) : bool                                 │
│ + cancelOrder(OrderId) : bool                               │
│ + getBestBid() : Price                                      │
│ + getBestAsk() : Price                                      │
│ + processEvents() : void                                    │
│ + start() : void                                            │
│ + stop() : void                                             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ├──────────────────────────────────────────────┐
               │                                              │
               ▼                                              ▼
┌──────────────────────────┐              ┌──────────────────────────┐
│    InputHandler          │              │   OrderProcessor         │
│  (Single Responsibility) │              │  (Single Responsibility) │
├──────────────────────────┤              ├──────────────────────────┤
│ + submitOrder() : bool   │              │ + start() : void         │
│ + isQueueFull() : bool   │              │ + stop() : void          │
└──────────┬───────────────┘              └──────────┬───────────────┘
           │                                          │
           │ uses                                     │ uses
           ▼                                          ▼
┌──────────────────────────┐              ┌──────────────────────────┐
│  SpscRingBuffer<Order>   │              │  IMatchingEngine         │
│   (Lock-free Queue)      │              │   (Interface)            │
├──────────────────────────┤              ├──────────────────────────┤
│ + tryPush() : bool       │              │ + process() : Trades     │
│ + tryPop() : bool        │              └──────────┬───────────────┘
│ + empty() : bool         │                         │
│ + full() : bool          │                         │ implements
└──────────────────────────┘                         ▼
                                           ┌──────────────────────────┐
                                           │   MatchingEngine         │
                                           │  (Dependency Injection)  │
                                           ├──────────────────────────┤
                                           │ - orderBook_             │
                                           │ - eventPublisher_        │
                                           └──────────┬───────────────┘
                                                      │
                                                      ├──────────────┐
                                                      │              │
                                                      ▼              ▼
                                    ┌──────────────────────┐  ┌──────────────────────┐
                                    │   IOrderBook         │  │  IEventPublisher     │
                                    │   (Interface)        │  │  (Interface)         │
                                    ├──────────────────────┤  ├──────────────────────┤
                                    │ + addOrder()         │  │ + publish()          │
                                    │ + cancelOrder()      │  └──────────┬───────────┘
                                    │ + findBestBid()      │             │
                                    │ + findBestAsk()      │             │ implements
                                    └──────────┬───────────┘             ▼
                                               │          ┌──────────────────────────┐
                                               │          │  SpscEventPublisher      │
                                               │          │  (Lock-free Publisher)   │
                                               │          ├──────────────────────────┤
                                               │          │ - eventQueue_            │
                                               │          └──────────┬───────────────┘
                                               │                     │
                                               │ implements          │ uses
                                               ▼                     ▼
                                    ┌──────────────────────┐  ┌──────────────────────┐
                                    │   OrderBook          │  │ SpscRingBuffer<Event>│
                                    │  (Concrete Class)    │  │  (Lock-free Queue)   │
                                    ├──────────────────────┤  └──────────────────────┘
                                    │ - bids_ : BidMap     │
                                    │ - asks_ : AskMap     │
                                    │ - locators_ : Map    │
                                    └──────────────────────┘
```

### Sequence Diagram: Order Processing

```
Client          InputHandler    OrderQueue    OrderProcessor    MatchingEngine    OrderBook    EventQueue    OutputHandler
  │                  │              │              │                  │              │              │              │
  │ submitOrder()    │              │              │                  │              │              │              │
  ├─────────────────►│              │              │                  │              │              │              │
  │                  │ tryPush()    │              │                  │              │              │              │
  │                  ├─────────────►│              │                  │              │              │              │
  │                  │◄─────────────┤ (success)    │                  │              │              │              │
  │◄─────────────────┤              │              │                  │              │              │              │
  │                  │              │              │                  │              │              │              │
  │                  │              │              │ tryPop()         │              │              │              │
  │                  │              │◄─────────────┤                  │              │              │              │
  │                  │              ├─────────────►│                  │              │              │              │
  │                  │              │              │ process()        │              │              │              │
  │                  │              │              ├─────────────────►│              │              │              │
  │                  │              │              │                  │ publish(Ack) │              │              │
  │                  │              │              │                  ├──────────────┼─────────────►│              │
  │                  │              │              │                  │ addOrder()   │              │              │
  │                  │              │              │                  ├─────────────►│              │              │
  │                  │              │              │                  │◄─────────────┤              │              │
  │                  │              │              │◄─────────────────┤              │              │              │
  │                  │              │              │                  │              │              │              │
  │                  │              │              │                  │              │              │ processEvents()
  │                  │              │              │                  │              │              │◄─────────────┤
  │                  │              │              │                  │              │              │ tryPop()     │
  │                  │              │              │                  │              │              │◄─────────────┤
  │                  │              │              │                  │              │              ├─────────────►│
  │                  │              │              │                  │              │              │ callback()   │
  │                  │              │              │                  │              │              ├─────────────►│
  │◄──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
```

## Lock-Free Operations

### SPSC Queue Implementation

The system uses **lock-free SPSC (Single Producer Single Consumer) queues** for thread-safe communication:

1. **Memory Ordering**: Uses `memory_order_relaxed`, `memory_order_acquire`, and `memory_order_release`
2. **Cache Line Alignment**: Head and tail pointers are 64-byte aligned to prevent false sharing
3. **Power-of-Two Capacity**: Enables fast modulo operation using bitwise AND
4. **Lock-Free Guarantees**:
   - No mutexes or locks
   - Wait-free for producer (when not full)
   - Wait-free for consumer (when not empty)
   - No blocking operations

### Lock-Free Flow

```
Producer Thread (Input)          Consumer Thread (Processor)
─────────────────────────         ─────────────────────────
head_.load(relaxed)              tail_.load(relaxed)
  │                                 │
  │ (head + 1) & mask               │ tail == head? (acquire)
  │                                 │   │
  │ next == tail? (acquire)         │   └─► empty
  │   │                              │
  │   └─► full                      │
  │                                 │
  │ construct(value)                │ move(buffer[tail])
  │                                 │ destroy(buffer[tail])
  │ head_.store(next, release)      │ tail_.store(next, release)
```

## SOLID Principles

### 1. Single Responsibility Principle (SRP)
- **OrderBook**: Manages order storage and retrieval
- **MatchingEngine**: Handles order matching logic
- **OrderProcessor**: Processes orders from queue
- **InputHandler**: Handles order submission
- **OutputHandler**: Handles event output

### 2. Open/Closed Principle (OCP)
- Interfaces (`IOrderBook`, `IMatchingEngine`, `IEventPublisher`) allow extension without modification
- New implementations can be added without changing existing code

### 3. Liskov Substitution Principle (LSP)
- All concrete implementations can be substituted for their interfaces
- `OrderBook` implements `IOrderBook`
- `MatchingEngine` implements `IMatchingEngine`

### 4. Interface Segregation Principle (ISP)
- Small, focused interfaces
- `IOrderBook` only contains order book operations
- `IEventPublisher` only contains publishing operations

### 5. Dependency Inversion Principle (DIP)
- High-level modules depend on abstractions (interfaces)
- `MatchingEngine` depends on `IOrderBook` and `IEventPublisher`, not concrete classes
- Dependency injection via constructor

## Design Patterns

1. **Facade Pattern**: `OrderManagementSystem` provides simple interface to complex subsystem
2. **Strategy Pattern**: Matching logic can be swapped via `IMatchingEngine` interface
3. **Observer Pattern**: Event callbacks for event handling
4. **Dependency Injection**: Components receive dependencies via constructor

## Directory Structure

```
Orderbook/
├── include/orderbook/
│   ├── core/              # Core types and constants
│   │   ├── types.hpp
│   │   ├── constants.hpp
│   │   └── log.hpp
│   ├── queue/             # Lock-free SPSC queue
│   │   └── spsc_queue.hpp
│   ├── book/              # Order book
│   │   ├── i_order_book.hpp
│   │   └── order_book.hpp
│   ├── engine/            # Matching engine
│   │   ├── i_matching_engine.hpp
│   │   └── matching_engine.hpp
│   ├── events/            # Event system
│   │   ├── event_types.hpp
│   │   └── event_publisher.hpp
│   ├── processors/        # Order processor
│   │   └── order_processor.hpp
│   ├── handlers/          # Input/output handlers
│   │   ├── input_handler.hpp
│   │   └── output_handler.hpp
│   └── oms/               # Main OMS facade
│       └── order_management_system.hpp
├── src/orderbook/         # Implementation files (same structure)
└── apps/
    └── ob_cli.cpp         # CLI application
```

## Data Structures

- **Bids**: `std::map<Price, std::deque<Order>, std::greater<Price>>` (highest first)
- **Asks**: `std::map<Price, std::deque<Order>, std::less<Price>>` (lowest first)
- **Fast Cancel**: `std::unordered_map<OrderId, OrderLocator>` (O(1) lookup)
- **SPSC Queues**: Lock-free ring buffers with power-of-two capacity

## Performance Characteristics

- **Order Add**: O(log N) - map insertion
- **Order Cancel**: O(1) - hash map lookup + deque erase
- **Order Match**: O(log N) per price level
- **Queue Operations**: O(1) - lock-free, wait-free when not full/empty
- **Memory**: 64-byte aligned structures for cache efficiency

## Notes

- All operations are O(log N) per level; cancel is O(1)
- Hot structs are 64B-aligned; SPSC uses relaxed atomics
- Prefer steady_clock for monotonic timestamps
- Lock-free queues enable high-throughput, low-latency processing
- Thread-safe communication without mutexes or locks

## Extensibility

- **Multiple instruments**: Shard books by symbolId with one engine per shard
- **Advanced order types**: Extend `OrderType` enum and engine logic
- **Persistence**: Attach sinks to event/trade stream
- **Custom publishers**: Implement `IEventPublisher` interface
- **Custom matching**: Implement `IMatchingEngine` interface
