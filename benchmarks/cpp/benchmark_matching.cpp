#include "orderbook/engine/matching_engine.hpp"
#include "orderbook/book/order_book.hpp"
#include "orderbook/core/types.hpp"
#include "orderbook/events/event_publisher.hpp"
#include "orderbook/events/event_types.hpp"
#include <benchmark/benchmark.h>
#include <random>
#include <vector>
#include <memory>
#include <algorithm>
#include <chrono>
#include <cmath>

using namespace ob::engine;
using namespace ob::core;
using namespace ob::book;
using namespace ob::events;

// Latency tracking helper
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

// Generate order that will match (static to avoid multiple definition)
static Order generateMatchingOrder(OrderId id, std::uint32_t symbolId, Side side, Price price, std::mt19937& gen) {
    std::uniform_int_distribution<Quantity> qtyDist(1, 1000);
    Quantity qty = qtyDist(gen);
    
    auto now = std::chrono::steady_clock::now();
    auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
    
    return Order{id, symbolId, side, OrderType::Limit, price, qty, Timestamp{nowNs}};
}

// Null event publisher for benchmarks
class NullEventPublisher : public IEventPublisher {
public:
    bool publish(const Event&) override { return true; }
    bool publish(Event&&) override { return true; }
};

// Benchmark matching limit orders (with latency tracking)
static void BM_MatchingEngine_MatchLimitOrder(benchmark::State& state) {
    auto orderBook = std::make_shared<OrderBook>();
    auto eventPublisher = std::make_shared<NullEventPublisher>();
    MatchingEngine engine(orderBook, eventPublisher);
    std::mt19937 gen(42);
    LatencyStats stats;
    
    // Pre-populate book with opposite side orders
    constexpr std::size_t INITIAL_ORDERS = 100;
    Price basePrice = 10000;
    
    // Add buy orders
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateMatchingOrder(id, 1, Side::Buy, basePrice + id, gen);
        engine.process(order);
    }
    
    // Match with sell orders
    OrderId sellOrderId = INITIAL_ORDERS + 1;
    for (auto _ : state) {
        Order sellOrder = generateMatchingOrder(sellOrderId++, 1, Side::Sell, basePrice, gen);
        
        auto start = std::chrono::steady_clock::now();
        engine.process(sellOrder);
        auto end = std::chrono::steady_clock::now();
        
        auto latency = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
        stats.record(static_cast<double>(latency));
        
        benchmark::DoNotOptimize(engine);
    }
    
    stats.report(state, "MatchLimitOrder");
    state.SetItemsProcessed(state.iterations());
}

// Benchmark matching market orders
static void BM_MatchingEngine_MatchMarketOrder(benchmark::State& state) {
    auto orderBook = std::make_shared<OrderBook>();
    auto eventPublisher = std::make_shared<NullEventPublisher>();
    MatchingEngine engine(orderBook, eventPublisher);
    std::mt19937 gen(42);
    
    // Pre-populate book
    constexpr std::size_t INITIAL_ORDERS = 100;
    Price basePrice = 10000;
    
    // Add limit orders
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateMatchingOrder(id, 1, Side::Buy, basePrice + id, gen);
        engine.process(order);
    }
    
    // Match with market sell orders
    OrderId marketOrderId = INITIAL_ORDERS + 1;
    for (auto _ : state) {
        auto now = std::chrono::steady_clock::now();
        auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
        
        std::uniform_int_distribution<Quantity> qtyDist(1, 100);
        Quantity qty = qtyDist(gen);
        
        Order marketOrder{marketOrderId++, 1, Side::Sell, OrderType::Market, 0, qty, Timestamp{nowNs}};
        engine.process(marketOrder);
        benchmark::DoNotOptimize(engine);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Benchmark partial fills
static void BM_MatchingEngine_PartialFill(benchmark::State& state) {
    auto orderBook = std::make_shared<OrderBook>();
    auto eventPublisher = std::make_shared<NullEventPublisher>();
    MatchingEngine engine(orderBook, eventPublisher);
    std::mt19937 gen(42);
    
    Price basePrice = 10000;
    
    for (auto _ : state) {
        // Add a large limit order
        auto now = std::chrono::steady_clock::now();
        auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
        
        Order largeOrder{1, 1, Side::Buy, OrderType::Limit, basePrice, 10000, Timestamp{nowNs}};
        engine.process(largeOrder);
        
        // Partially fill it
        Order smallOrder{2, 1, Side::Sell, OrderType::Limit, basePrice, 100, Timestamp{nowNs}};
        engine.process(smallOrder);
        
        benchmark::DoNotOptimize(engine);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Register benchmarks
BENCHMARK(BM_MatchingEngine_MatchLimitOrder)
    ->Name("MatchingEngine_MatchLimitOrder")
    ->UseRealTime()
    ->Iterations(10000);

BENCHMARK(BM_MatchingEngine_MatchMarketOrder)
    ->Name("MatchingEngine_MatchMarketOrder")
    ->UseRealTime()
    ->Iterations(10000);

BENCHMARK(BM_MatchingEngine_PartialFill)
    ->Name("MatchingEngine_PartialFill")
    ->UseRealTime()
    ->Iterations(10000);

// BENCHMARK_MAIN(); // Defined in benchmark_orderbook.cpp

