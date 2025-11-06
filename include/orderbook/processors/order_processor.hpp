#pragma once

#include "orderbook/core/types.hpp"
#include "orderbook/queue/spsc_queue.hpp"
#include "orderbook/engine/i_matching_engine.hpp"
#include "orderbook/book/i_order_book.hpp"
#include "orderbook/events/event_publisher.hpp"
#include "orderbook/core/constants.hpp"
#include <memory>
#include <thread>
#include <atomic>

namespace ob::processors {

// Order processor that consumes from SPSC queue and processes orders
// Single Responsibility: Process orders from queue
class OrderProcessor {
public:
    OrderProcessor(
        std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue,
        std::shared_ptr<engine::IMatchingEngine> matchingEngine
    );

    ~OrderProcessor();

    // Start processing orders (runs in separate thread)
    void start();
    void stop();
    bool isRunning() const noexcept { return running_.load(); }

private:
    void processLoop();

    std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue_;
    std::shared_ptr<engine::IMatchingEngine> matchingEngine_;
    std::thread processorThread_;
    std::atomic<bool> running_{false};
};

} // namespace ob::processors

