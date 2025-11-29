# OrderBook Performance Benchmarks

This directory contains performance benchmarks for the OrderBook system. Benchmarks are kept separate from the main codebase to maintain clean separation.

## Overview

The benchmark suite measures:
- **C++ Core Operations**: Order insertion, cancellation, matching, queue operations
- **Python WebSocket Layer**: Message handling, connection pooling, TCP communication
- **End-to-End Latency**: Full order submission flow

## Prerequisites

### C++ Benchmarks
- CMake 3.20+
- C++20 compiler (GCC 10+, Clang 12+, MSVC 2019+)
- Google Benchmark library

### Python Benchmarks
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

## Building C++ Benchmarks

```bash
cd benchmarks
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --parallel
```

## Running Benchmarks

### Docker (Recommended - All Services Running)

```bash
# Start all services first
docker-compose up -d

# Run benchmarks with all services
docker-compose --profile benchmarks run --rm benchmarks

# Or use the helper script
./benchmarks/docker-run.sh
```

See [DOCKER.md](DOCKER.md) for detailed Docker instructions.

### Local C++ Benchmarks

```bash
cd benchmarks/build

# Run all benchmarks
./benchmarks

# Run specific benchmark
./benchmarks --benchmark_filter=OrderBook_AddOrder

# Run with custom iterations
./benchmarks --benchmark_min_time=2s

# Generate JSON report
./benchmarks --benchmark_format=json > results.json
```

### Local Python Benchmarks

```bash
cd benchmarks

# Run all Python benchmarks
python -m pytest python_benchmarks/ -v

# Run specific benchmark
python -m pytest python_benchmarks/benchmark_tcp_client.py -v

# Run with profiling
python -m pytest python_benchmarks/ --profile
```

## Benchmark Results

Results are saved to:
- `benchmarks/results/` - JSON and CSV reports
- `benchmarks/reports/` - HTML reports (if generated)

## Interpreting Results

### Latency Metrics

All critical benchmarks now include comprehensive latency tracking:

- **Mean**: Average operation time
- **P50 (Median)**: 50th percentile - typical performance
- **P95**: 95th percentile - 95% of operations complete within this time
- **P99**: 99th percentile - 99% of operations complete within this time (critical for SLAs)
- **P99.9**: 99.9th percentile - worst-case tail latency
- **Min/Max**: Best and worst case performance
- **StdDev**: Standard deviation (consistency indicator)

### Throughput Metrics
- **Ops/sec**: Operations per second
- **Throughput**: Total operations completed
- **Bytes/sec**: Data throughput (for queue operations)

### Current Performance Results

#### C++ Core Operations (Production-Grade)

| Operation | Mean | P99 | P999 | Throughput | Status |
|-----------|------|-----|------|------------|--------|
| **AddOrder** | 1.7 μs | 28.2 μs | 64.3 μs | 533k ops/sec | ✅ Excellent |
| **GetBestPrice** | 39.6 ns | 51 ns | 81 ns | 10.6M ops/sec | ✅ Excellent |
| **CancelOrder** | 51.7 ns | - | - | 19.4M ops/sec | ✅ Excellent |
| **MatchLimitOrder** | 192.7 ns | 561 ns | 5.26 μs | 3.6M ops/sec | ✅ Excellent |
| **MatchMarketOrder** | 77.4 ns | - | - | 12.9M ops/sec | ✅ Excellent |
| **SPSCQueue_Push** | 12.2 ns | - | - | 82.1M ops/sec | ✅ Excellent |
| **OMS_SubmitOrder** | 51.2 ns | - | - | 19.5M ops/sec | ✅ Excellent |

#### Python Network Layer

| Operation | Localhost | Real-World (Same DC) | Real-World (Remote) | Notes |
|-----------|-----------|---------------------|-------------------|-------|
| **TCP Client (pooled)** | 435 μs | 0.9-2.4 ms | 10.4-50.4 ms | Add network RTT |
| **TCP Client (no pool)** | 2.2 ms | 2.7-4.2 ms | 12.2-52.2 ms | Add network RTT |
| **Message Serialization** | 8.9 μs | 8.9 μs | 8.9 μs | No network impact |
| **Message Deserialization** | 17.1 μs | 17.1 μs | 17.1 μs | No network impact |

**Note:** Python TCP benchmarks run on localhost. Add network latency for real-world estimates:
- Same datacenter: +0.5-2 ms
- Cross-region: +10-50 ms
- Internet: +20-200 ms

## Network Impact on Benchmarks

### C++ Benchmarks (No Network Impact)
All C++ benchmarks test **in-memory operations** and are **not affected** by localhost vs remote:
- OrderBook operations (map/deque operations)
- Matching engine (algorithmic matching)
- SPSC Queue (lock-free data structure)
- OMS (in-process function calls)

**These results are production-realistic** and represent actual CPU/memory performance.

### Python Benchmarks (Network Impact Varies)

#### No Network Impact
- **Message Serialization/Deserialization**: Pure JSON operations, no network
- **Connection Pool Operations**: Socket management only

#### Network Impact (Localhost vs Remote)
- **TCP Client Benchmarks**: Test against localhost mock server
  - **Localhost**: ~0.1-0.5 ms RTT (current results)
  - **Same Datacenter**: Add +0.5-2 ms
  - **Cross-Region**: Add +10-50 ms
  - **Internet**: Add +20-200 ms

**To estimate real-world performance:**
```
Real-World Latency = Benchmark Result + Network RTT
```

Example:
- TCP Client (pooled) localhost: 435 μs
- Same datacenter estimate: 435 μs + 1000 μs = **1.4 ms**
- Cross-region estimate: 435 μs + 20000 μs = **20.4 ms**

## Hardware Requirements

For consistent results:
- Disable CPU frequency scaling: `sudo cpupower frequency-set -g performance`
- Close unnecessary applications
- Run on dedicated hardware (not in Docker for C++ benchmarks)
- Use Release builds (`-DCMAKE_BUILD_TYPE=Release`)

### Test Environment
Current benchmarks run on:
- **CPU**: 6 cores @ 2.37 GHz
- **Cache**: L1 32KB, L2 512KB, L3 4MB
- **OS**: Ubuntu 22.04 (Docker)
- **Build**: Release mode with -O3 optimizations

## Production-Grade Performance Assessment

### Grade: **A** (Production-Ready)

The OrderBook system demonstrates **production-grade performance** suitable for:
- ✅ Institutional trading platforms
- ✅ Crypto exchanges
- ✅ Algorithmic trading systems
- ✅ Market data distribution
- ✅ High-frequency trading (with optimizations)

### Key Strengths
1. **Sub-microsecond latency** on critical paths (GetBestPrice: 39.6 ns)
2. **High throughput** (533k orders/sec, 10.6M price lookups/sec)
3. **Excellent P99 latencies** (GetBestPrice P99: 51 ns)
4. **Lock-free operations** (SPSC queue: 12-14 ns)

### Performance Targets Met
- ✅ GetBestPrice: <100 ns (target: <100 ns) - **EXCEEDED**
- ✅ CancelOrder: <1 μs (target: <1 μs) - **MET**
- ✅ MatchMarketOrder: <1 μs (target: <1 μs) - **MET**
- ⚠️ AddOrder: 1.7 μs (target: <1 μs) - **Close, optimization ongoing**

## Contributing

When adding new benchmarks:
1. Follow the naming convention: `Component_Operation`
2. Include warmup iterations
3. Measure both latency and throughput
4. **Always include latency tracking** (P50, P95, P99, P999) for critical operations
5. Document expected results in comments
6. Update this README with new benchmark descriptions
7. Note network impact if applicable

