#include "orderbook/book/order_book.hpp"
#include "orderbook/engine/matching_engine.hpp"
#include "orderbook/oms/order_management_system.hpp"
#include "orderbook/core/types.hpp"
#include "orderbook/events/event_publisher.hpp"
#include "orderbook/events/event_types.hpp"
#include <benchmark/benchmark.h>
#include <random>
#include <vector>
#include <thread>
#include <atomic>
#include <chrono>

using namespace ob::book;
using namespace ob::core;
using namespace ob::engine;
using namespace ob::oms;
using namespace ob::events;

// Null event publisher for benchmarks
class NullEventPublisher : public IEventPublisher {
public:
    bool publish(const Event&) override { return true; }
    bool publish(Event&&) override { return true; }
};

// Generate random order
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

// Load test: High-frequency order submission
static void BM_LoadTest_HighFrequencyOrders(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    
    OrderId orderId = 1;
    constexpr std::size_t BATCH_SIZE = 10000;
    
    for (auto _ : state) {
        // Submit a batch of orders
        for (std::size_t i = 0; i < BATCH_SIZE; ++i) {
            Order order = generateOrder(orderId++, 1, gen);
            book.addOrder(std::move(order));
        }
        
        // Periodically cancel some orders to simulate real usage
        if (orderId % (BATCH_SIZE * 10) == 0) {
            for (OrderId cancelId = orderId - BATCH_SIZE; cancelId < orderId; cancelId += 100) {
                book.cancelOrder(cancelId);
            }
        }
        
        benchmark::DoNotOptimize(book);
    }
    
    state.SetItemsProcessed(state.iterations() * BATCH_SIZE);
}

// Load test: Sustained throughput
static void BM_LoadTest_SustainedThroughput(benchmark::State& state) {
    auto orderBook = std::make_shared<OrderBook>();
    auto eventPublisher = std::make_shared<NullEventPublisher>();
    MatchingEngine engine(orderBook, eventPublisher);
    std::mt19937 gen(42);
    
    OrderId orderId = 1;
    Price basePrice = 10000;
    
    // Pre-populate with depth
    for (OrderId id = 1; id <= 1000; ++id) {
        Order order = generateOrder(id, 1, gen);
        engine.process(order);
    }
    
    for (auto _ : state) {
        // Mix of operations: 70% new orders, 20% matches, 10% cancels
        int op = orderId % 10;
        
        if (op < 7) {
            // New order
            Order order = generateOrder(orderId++, 1, gen);
            engine.process(order);
        } else if (op < 9) {
            // Matching order (opposite side)
            Side side = (orderId % 2 == 0) ? Side::Buy : Side::Sell;
            auto now = std::chrono::steady_clock::now();
            auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
            Order matchOrder{orderId++, 1, side, OrderType::Limit, basePrice, 100, Timestamp{nowNs}};
            engine.process(matchOrder);
        } else {
            // Cancel
            OrderId cancelId = (orderId - 100 > 0) ? orderId - 100 : 1;
            orderBook->cancelOrder(cancelId);
            orderId++;
        }
        
        benchmark::DoNotOptimize(engine);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Load test: Large order book (10K+ orders)
static void BM_LoadTest_LargeOrderBook(benchmark::State& state) {
    OrderBook book;
    std::mt19937 gen(42);
    
    // Pre-populate with large number of orders
    constexpr std::size_t INITIAL_ORDERS = 10000;
    std::vector<OrderId> orderIds;
    orderIds.reserve(INITIAL_ORDERS);
    
    for (OrderId id = 1; id <= INITIAL_ORDERS; ++id) {
        Order order = generateOrder(id, 1, gen);
        book.addOrder(std::move(order));
        orderIds.push_back(id);
    }
    
    OrderId newOrderId = INITIAL_ORDERS + 1;
    std::size_t cancelIndex = 0;
    
    for (auto _ : state) {
        // Add new order
        Order order = generateOrder(newOrderId++, 1, gen);
        book.addOrder(std::move(order));
        
        // Cancel an old order
        if (cancelIndex < orderIds.size()) {
            book.cancelOrder(orderIds[cancelIndex++]);
        }
        
        // Query best price
        auto bestBid = book.findBestBid();
        auto bestAsk = book.findBestAsk();
        
        benchmark::DoNotOptimize(bestBid);
        benchmark::DoNotOptimize(bestAsk);
    }
    
    state.SetItemsProcessed(state.iterations());
}

// Register load test benchmarks
BENCHMARK(BM_LoadTest_HighFrequencyOrders)
    ->Name("LoadTest_HighFrequencyOrders")
    ->UseRealTime()
    ->MinTime(5.0);  // Run for at least 5 seconds

BENCHMARK(BM_LoadTest_SustainedThroughput)
    ->Name("LoadTest_SustainedThroughput")
    ->UseRealTime()
    ->MinTime(5.0);

BENCHMARK(BM_LoadTest_LargeOrderBook)
    ->Name("LoadTest_LargeOrderBook")
    ->UseRealTime()
    ->Iterations(10000);

// BENCHMARK_MAIN(); // Defined in benchmark_orderbook.cpp

