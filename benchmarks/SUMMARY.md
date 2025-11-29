# Benchmark Suite Summary

## Overview

This benchmark suite provides comprehensive performance measurements for the OrderBook system. All benchmarks are kept separate from the main codebase.

## Benchmark Categories

### 1. C++ Core Benchmarks

#### Queue Operations (`benchmark_queue.cpp`)
- **SPSCQueue_Push**: Measures lock-free queue push operations
- **SPSCQueue_Pop**: Measures lock-free queue pop operations  
- **SPSCQueue_Concurrent**: Measures concurrent producer-consumer throughput

**Expected Results:**
- Push/Pop: ~100ns per operation
- Concurrent: 10M+ ops/sec combined throughput

#### OrderBook Operations (`benchmark_orderbook.cpp`)
- **OrderBook_AddOrder**: Adding orders to empty book
- **OrderBook_AddOrder_WithDepth**: Adding orders to book with existing depth
- **OrderBook_CancelOrder**: O(1) order cancellation
- **OrderBook_GetBestPrice**: Best bid/ask retrieval
- **OrderBook_GetSnapshot**: Depth snapshot generation

**Actual Results (Latest):**
- Add Order: **1.7 μs** (P99: 28.2 μs, P999: 64.3 μs) - 533k ops/sec
- Cancel Order: **51.7 ns** - 19.4M ops/sec
- Get Best Price: **39.6 ns** (P99: 51 ns, P999: 81 ns) - 10.6M ops/sec
- Get Snapshot: **140 ns** - 7.2M ops/sec

**Performance Grade:** ✅ Excellent - Production-ready

#### Matching Engine (`benchmark_matching.cpp`)
- **MatchingEngine_MatchLimitOrder**: Limit order matching
- **MatchingEngine_MatchMarketOrder**: Market order matching
- **MatchingEngine_PartialFill**: Partial fill scenarios

**Actual Results (Latest):**
- Limit Match: **192.7 ns** (P99: 561 ns, P999: 5.26 μs) - 3.6M ops/sec
- Market Match: **77.4 ns** - 12.9M ops/sec
- Partial Fill: **185 ns** - 5.4M ops/sec

**Performance Grade:** ✅ Excellent - Sub-microsecond matching

#### OMS End-to-End (`benchmark_oms.cpp`)
- **OMS_SubmitOrder**: Full order submission through OMS
- **OMS_CancelOrder**: Order cancellation through OMS
- **OMS_GetMarketData**: Market data retrieval

**Actual Results (Latest):**
- Submit Order: **51.2 ns** - 19.5M ops/sec
- Cancel Order: See OrderBook_CancelOrder above
- Get Market Data: See GetBestPrice/GetSnapshot above

**Performance Grade:** ✅ Excellent - Minimal OMS overhead

### 2. Python Benchmarks

#### TCP Client (`benchmark_tcp_client.py`)
- **Connection Pool Operations**: Get/return connection performance
- **With Pooling**: TCP client with connection pooling
- **Without Pooling**: TCP client without pooling (baseline)
- **Concurrent Requests**: Multi-threaded request handling

**Actual Results (Latest - Localhost):**
- Pool Get/Return: **5.3 μs** - 189k ops/sec
- With Pooling: **435 μs** - 2.3k ops/sec
- Without Pooling: **2.2 ms** - 448 ops/sec
- Concurrent: **104.5 ms** - 9.6 ops/sec (100 concurrent requests)

**Network Impact Note:** These results are from localhost. Add network RTT for real-world:
- Same datacenter: +0.5-2 ms
- Cross-region: +10-50 ms
- Internet: +20-200 ms

#### WebSocket Message Handling (`benchmark_websocket.py`)
- **Order Message Serialization**: JSON serialization performance
- **Order Message Deserialization**: JSON parsing performance
- **Order Response Serialization**: Response message creation
- **Large Message Handling**: Orderbook snapshot processing

**Actual Results (Latest):**
- Serialization: **8.9 μs** - 112k ops/sec
- Deserialization: **17.1 μs** - 58k ops/sec
- Orderbook Message Serialization: **14.4 μs** - 70k ops/sec
- Large Messages: **193 μs** - 5.2k ops/sec

**Performance Grade:** ✅ Excellent - No network impact (pure CPU)

## Running Benchmarks

### Quick Start

```bash
cd benchmarks
./run_benchmarks.sh  # Linux/Mac
```

### Manual Execution

**C++ Benchmarks:**
```bash
cd benchmarks
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
./benchmarks
```

**Python Benchmarks:**
```bash
cd benchmarks/python_benchmarks
pip install -r requirements.txt
pytest . -v --benchmark-only
```

## Interpreting Results

### Latency Metrics
- **Mean/Median**: Average operation time
- **P95/P99/P99.9**: Percentile latencies (important for trading systems)
- **Min/Max**: Best and worst case performance

### Throughput Metrics
- **Items/Second**: Operations per second
- **Bytes/Second**: Data throughput
- **Throughput**: Total operations completed

### Key Performance Indicators

For trading systems, focus on:
1. **P99 Latency**: 99th percentile ensures 99% of orders process within threshold
2. **Throughput**: Sustained operations per second under load
3. **Consistency**: Low variance in latency (predictable performance)

## Hardware Considerations

Benchmark results vary significantly based on:
- **CPU**: Clock speed, cache size, architecture
- **Memory**: Speed, latency, bandwidth
- **OS**: Kernel version, scheduler, CPU governor
- **System Load**: Background processes, thermal throttling

For consistent results:
- Use Release builds (`-DCMAKE_BUILD_TYPE=Release`)
- Disable CPU frequency scaling
- Close unnecessary applications
- Run on dedicated hardware
- Document hardware specifications

## Updating Benchmarks

When adding new benchmarks:
1. Follow naming convention: `Component_Operation`
2. Include warmup iterations
3. Measure both latency and throughput
4. Document expected results
5. Update this summary

## Contributing

See [README.md](README.md) for contribution guidelines.

