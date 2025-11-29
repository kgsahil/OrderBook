#include "orderbook/book/order_book.hpp"
#include "orderbook/core/types.hpp"
#include <benchmark/benchmark.h>
#include <random>
#include <vector>
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace ob::book;
using namespace ob::core;

// Latency tracking helper (shared across benchmarks)
struct LatencyStats {
    std::vector<double> latencies;
    
    void record(double latency_ns) {
        latencies.push_back(latency_ns);
    }
    
    void report(benchmark::State& state, const std::string& name) {
        if (latencies.empty()) return;
        
        std::sort(latencies.begin(), latencies.end());
        
        auto p50 = latencies[latencies.size() * 0.50];
        auto p95 = latencies[latencies.size() * 0.95];
        auto p99 = latencies[latencies.size() * 0.99];
        auto p999 = latencies.size() >= 1000 ? latencies[latencies.size() * 0.999] : latencies.back();
        auto max = latencies.back();
        auto min = latencies.front();
        
        double sum = 0.0;
        for (auto l : latencies) sum += l;
        double mean = sum / latencies.size();
        
        double variance = 0.0;
        for (auto l : latencies) {
            variance += (l - mean) * (l - mean);
        }
        double stddev = std::sqrt(variance / latencies.size());
        
        state.counters[name + "_P50_ns"] = p50;
        state.counters[name + "_P95_ns"] = p95;
        state.counters[name + "_P99_ns"] = p99;
        state.counters[name + "_P999_ns"] = p999;
        state.counters[name + "_Mean_ns"] = mean;
        state.counters[name + "_StdDev_ns"] = stddev;
        state.counters[name + "_Min_ns"] = min;
        state.counters[name + "_Max_ns"] = max;
    }
};

// Generate random order (static to avoid multiple definition)
static Order generateOrder(OrderId id, std::uint32_t symbolId, std::mt19937& gen) {
    std::uniform_int_distribution<Price> priceDist(10000, 20000);
    std::uniform_int_distribution<Quantity> qtyDist(1, 1000);
    std::uniform_int_distribution<int> sideDist(0, 1);
    
    Side side = (sideDist(gen) == 0) ? Side::Buy : Side::Sell;
    Price price = priceDist(gen);
    Quantity qty = qtyDist(gen);
    
    auto now = std::chrono::steady_clock::now();
    auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
    
    return Order{id, symbolId, side, OrderType::Limit, price, qty, Timestamp{nowNs}};
}

// Benchmark adding orders to empty book (with latency tracking)
static void BM_OrderBook_AddOrder(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);  // Fixed seed for reproducibility
    LatencyStats stats;
    
    OrderId orderId = 1;
    for (auto _ : state) {
        Order order = generateOrder(orderId++, 1, gen);
        
        auto start = std::chrono::steady_clock::now();
        book.addOrder(std::move(order));
        auto end = std::chrono::steady_clock::now();
        
        auto latency = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        stats.record(static_cast<double>(latency));
        
        benchmark::DoNotOptimize(book);
    }
    
    stats.report(state, "AddOrder");
    state.SetItemsProcessed(state.iterations());
}

// Benchmark adding orders to book with existing orders
static void BM_OrderBook_AddOrder_WithDepth(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    
    // Pre-populate book
    constexpr std::size_t INITIAL_ORDERS = 1000;
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        book.addOrder(std::move(order));
    }
    
    OrderId orderId = INITIAL_ORDERS + 1;
    for (auto _ : state) {
        Order order = generateOrder(orderId++, 1, gen);
        book.addOrder(std::move(order));
        benchmark::DoNotOptimize(book);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Benchmark canceling orders
static void BM_OrderBook_CancelOrder(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    
    // Pre-populate book
    constexpr std::size_t INITIAL_ORDERS = 10000;
    std::vector<OrderId> orderIds;
    orderIds.reserve(INITIAL_ORDERS);
    
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        book.addOrder(std::move(order));
        orderIds.push_back(id);
    }
    
    std::size_t cancelIndex = 0;
    for (auto _ : state) {
        if (cancelIndex >= orderIds.size()) {
            cancelIndex = 0;
        }
        bool cancelled = book.cancelOrder(orderIds[cancelIndex++]);
        benchmark::DoNotOptimize(cancelled);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Benchmark getting best bid/ask (with latency tracking)
static void BM_OrderBook_GetBestPrice(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    LatencyStats stats;
    
    // Pre-populate book
    constexpr std::size_t INITIAL_ORDERS = 1000;
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        book.addOrder(std::move(order));
    }
    
    for (auto _ : state) {
        auto start = std::chrono::steady_clock::now();
        auto bestBid = book.findBestBid();
        auto bestAsk = book.findBestAsk();
        auto end = std::chrono::steady_clock::now();
        
        auto latency = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        stats.record(static_cast<double>(latency));
        
        benchmark::DoNotOptimize(bestBid);
        benchmark::DoNotOptimize(bestAsk);
    }
    
    stats.report(state, "GetBestPrice");
    state.SetItemsProcessed(state.iterations());
}

// Benchmark getting snapshot
static void BM_OrderBook_GetSnapshot(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    
    // Pre-populate book
    constexpr std::size_t INITIAL_ORDERS = 1000;
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        book.addOrder(std::move(order));
    }
    
    for (auto _ : state) {
        auto bids = book.snapshotBidsL2(10);
        auto asks = book.snapshotAsksL2(10);
        benchmark::DoNotOptimize(bids);
        benchmark::DoNotOptimize(asks);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Register benchmarks
BENCHMARK(BM_OrderBook_AddOrder)
    ->Name("OrderBook_AddOrder")
    ->UseRealTime()
    ->Iterations(100000);

BENCHMARK(BM_OrderBook_AddOrder_WithDepth)
    ->Name("OrderBook_AddOrder_WithDepth")
    ->UseRealTime()
    ->Iterations(100000);

BENCHMARK(BM_OrderBook_CancelOrder)
    ->Name("OrderBook_CancelOrder")
    ->UseRealTime()
    ->Iterations(100000);

BENCHMARK(BM_OrderBook_GetBestPrice)
    ->Name("OrderBook_GetBestPrice")
    ->UseRealTime()
    ->Iterations(1000000);

BENCHMARK(BM_OrderBook_GetSnapshot)
    ->Name("OrderBook_GetSnapshot")
    ->UseRealTime()
    ->Iterations(10000);

BENCHMARK_MAIN();

