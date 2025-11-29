#include "orderbook/queue/spsc_queue.hpp"
#include "orderbook/core/types.hpp"
#include <benchmark/benchmark.h>
#include <thread>
#include <atomic>
#include <vector>
#include <memory>

using namespace ob::queue;
using namespace ob::core;

// Benchmark SPSC queue push operations (circular to avoid queue full)
static void BM_SPSCQueue_Push(benchmark::State& state) {
    constexpr std::size_t QUEUE_SIZE = 1024;
    auto queue = std::make_shared<SpscRingBuffer<Order>>(QUEUE_SIZE);
    
    Order order{1, 1, Side::Buy, OrderType::Limit, 10000, 100, {}};
    Order dummy;
    
    // Pre-fill queue halfway to allow push/pop cycling
    for (std::size_t i = 0; i < QUEUE_SIZE / 2; ++i) {
        queue->tryPush(order);
    }
    
    for (auto _ : state) {
        // Push an order
        bool success = queue->tryPush(order);
        if (!success) {
            // If queue is full, pop one to make room
            queue->tryPop(dummy);
            queue->tryPush(order);
        }
        benchmark::DoNotOptimize(success);
    }
    
    state.SetItemsProcessed(state.iterations());
    state.SetBytesProcessed(state.iterations() * sizeof(Order));
}

// Benchmark SPSC queue pop operations (circular to avoid queue empty)
static void BM_SPSCQueue_Pop(benchmark::State& state) {
    constexpr std::size_t QUEUE_SIZE = 1024;
    auto queue = std::make_shared<SpscRingBuffer<Order>>(QUEUE_SIZE);
    
    // Pre-fill queue
    Order order{1, 1, Side::Buy, OrderType::Limit, 10000, 100, {}};
    for (std::size_t i = 0; i < QUEUE_SIZE - 1; ++i) {
        queue->tryPush(order);
    }
    
    Order out;
    for (auto _ : state) {
        bool success = queue->tryPop(out);
        if (!success) {
            // If queue is empty, push one to keep it going
            queue->tryPush(order);
            queue->tryPop(out);
        }
        benchmark::DoNotOptimize(out);
    }
    
    state.SetItemsProcessed(state.iterations());
    state.SetBytesProcessed(state.iterations() * sizeof(Order));
}

// Benchmark concurrent push/pop (producer-consumer pattern)
static void BM_SPSCQueue_Concurrent(benchmark::State& state) {
    constexpr std::size_t QUEUE_SIZE = 1024;
    auto queue = std::make_shared<SpscRingBuffer<Order>>(QUEUE_SIZE);
    
    std::atomic<bool> running{true};
    std::atomic<std::uint64_t> pushed{0};
    std::atomic<std::uint64_t> popped{0};
    
    // Producer thread
    std::thread producer([&]() {
        Order order{1, 1, Side::Buy, OrderType::Limit, 10000, 100, {}};
        while (running.load()) {
            if (queue->tryPush(order)) {
                pushed.fetch_add(1);
            }
            std::this_thread::yield();
        }
    });
    
    // Consumer thread
    std::thread consumer([&]() {
        Order out;
        while (running.load() || !queue->empty()) {
            if (queue->tryPop(out)) {
                popped.fetch_add(1);
            }
            std::this_thread::yield();
        }
    });
    
    // Run benchmark
    for (auto _ : state) {
        benchmark::DoNotOptimize(queue);
    }
    
    running.store(false);
    producer.join();
    consumer.join();
    
    state.SetItemsProcessed(pushed.load() + popped.load());
}

// Register benchmarks
BENCHMARK(BM_SPSCQueue_Push)
    ->Name("SPSCQueue_Push")
    ->UseRealTime()
    ->Threads(1)
    ->Iterations(1000000);

BENCHMARK(BM_SPSCQueue_Pop)
    ->Name("SPSCQueue_Pop")
    ->UseRealTime()
    ->Threads(1)
    ->Iterations(1000000);

BENCHMARK(BM_SPSCQueue_Concurrent)
    ->Name("SPSCQueue_Concurrent")
    ->UseRealTime()
    ->MinTime(2.0);  // Run for at least 2 seconds

// BENCHMARK_MAIN(); // Defined in benchmark_orderbook.cpp

