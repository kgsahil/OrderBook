# Interview Version - Simplified Orderbook

This is a **1-hour interview version** of the orderbook. It focuses on core functionality without the production features.

## What's Included

✅ Core OrderBook with matching  
✅ Limit and Market orders  
✅ Order cancellation  
✅ Snapshot functionality  
✅ Simple CLI  

## What's Not Included (Discuss Instead)

❌ SPSC queues (discuss design)  
❌ Threading/async (discuss approach)  
❌ Event system (mention if time)  
❌ SOLID interfaces (discuss design)  
❌ Error handling (mention)  

## Compile & Run

```bash
g++ -std=c++17 -O2 orderbook.cpp main.cpp -o orderbook
./orderbook
```

## Usage

```
add B L 100 10    # Buy Limit at 100, qty 10
add S M 0 5       # Sell Market, qty 5
cancel 1          # Cancel order ID 1
snap              # Show order book
q                 # Quit
```

## Time Estimate

- OrderBook: 20-25 min
- Matching Engine: 20-25 min  
- CLI: 10-15 min
- **Total: ~50-65 minutes**

## Key Points to Discuss

1. **Data Structures**: Why map + deque?
2. **Matching Logic**: Price-time priority
3. **Performance**: O(log N) add, O(1) cancel
4. **Extensions**: Threading, lock-free queues, events

