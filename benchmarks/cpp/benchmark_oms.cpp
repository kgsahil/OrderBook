#include "orderbook/oms/order_management_system.hpp"
#include "orderbook/core/types.hpp"
#include <benchmark/benchmark.h>
#include <random>

using namespace ob::oms;
using namespace ob::core;

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

// Benchmark end-to-end order submission through OMS
static void BM_OMS_SubmitOrder(benchmark::State& state) {
    OrderManagementSystem oms;
    oms.start();
    
    std::mt19937 gen(42);
    OrderId orderId = 1;
    
    for (auto _ : state) {
        Order order = generateOrder(orderId++, 1, gen);
        bool submitted = oms.submitOrder(std::move(order));
        benchmark::DoNotOptimize(submitted);
        
        // Process events to simulate real usage
        oms.processEvents();
    }
    
    oms.stop();
    state.SetItemsProcessed(state.iterations());
}

// Benchmark order cancellation through OMS
static void BM_OMS_CancelOrder(benchmark::State& state) {
    OrderManagementSystem oms;
    oms.start();
    
    std::mt19937 gen(42);
    
    // Pre-submit orders
    constexpr std::size_t INITIAL_ORDERS = 1000;
    std::vector<OrderId> orderIds;
    orderIds.reserve(INITIAL_ORDERS);
    
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        oms.submitOrder(std::move(order));
        orderIds.push_back(id);
        oms.processEvents();
    }
    
    std::size_t cancelIndex = 0;
    for (auto _ : state) {
        if (cancelIndex >= orderIds.size()) {
            cancelIndex = 0;
        }
        bool cancelled = oms.cancelOrder(orderIds[cancelIndex++]);
        benchmark::DoNotOptimize(cancelled);
        oms.processEvents();
    }
    
    oms.stop();
    state.SetItemsProcessed(state.iterations());
}

// Benchmark getting market data
static void BM_OMS_GetMarketData(benchmark::State& state) {
    OrderManagementSystem oms;
    oms.start();
    
    std::mt19937 gen(42);
    
    // Pre-populate
    constexpr std::size_t INITIAL_ORDERS = 1000;
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        oms.submitOrder(std::move(order));
        oms.processEvents();
    }
    
    for (auto _ : state) {
        auto bestBid = oms.getBestBid();
        auto bestAsk = oms.getBestAsk();
        auto bids = oms.getBidsSnapshot(10);
        auto asks = oms.getAsksSnapshot(10);
        
        benchmark::DoNotOptimize(bestBid);
        benchmark::DoNotOptimize(bestAsk);
        benchmark::DoNotOptimize(bids);
        benchmark::DoNotOptimize(asks);
    }
    
    oms.stop();
    state.SetItemsProcessed(state.iterations());
}

// Register benchmarks
BENCHMARK(BM_OMS_SubmitOrder)
    ->Name("OMS_SubmitOrder")
    ->UseRealTime()
    ->Iterations(10000);

BENCHMARK(BM_OMS_CancelOrder)
    ->Name("OMS_CancelOrder")
    ->UseRealTime()
    ->Iterations(10000);

BENCHMARK(BM_OMS_GetMarketData)
    ->Name("OMS_GetMarketData")
    ->UseRealTime()
    ->Iterations(100000);

// BENCHMARK_MAIN(); // Defined in benchmark_orderbook.cpp

