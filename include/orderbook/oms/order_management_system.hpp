#pragma once

#include "orderbook/core/types.hpp"
#include "orderbook/core/constants.hpp"
#include "orderbook/queue/spsc_queue.hpp"
#include "orderbook/book/order_book.hpp"
#include "orderbook/engine/matching_engine.hpp"
#include "orderbook/events/event_publisher.hpp"
#include "orderbook/processors/order_processor.hpp"
#include "orderbook/handlers/input_handler.hpp"
#include "orderbook/handlers/output_handler.hpp"
#include <memory>

namespace ob::oms {

// Main OMS class that orchestrates all components
// Facade pattern: Provides simple interface to complex subsystem
class OrderManagementSystem {
public:
    explicit OrderManagementSystem(std::size_t queueSize = core::DEFAULT_QUEUE_SIZE);

    // Order operations
    bool submitOrder(const core::Order& order);
    bool submitOrder(core::Order&& order);
    bool cancelOrder(core::OrderId orderId);

    // Market data
    std::optional<core::Price> getBestBid() const;
    std::optional<core::Price> getBestAsk() const;
    std::vector<book::LevelSummary> getBidsSnapshot(std::size_t depth = 0) const;
    std::vector<book::LevelSummary> getAsksSnapshot(std::size_t depth = 0) const;

    // Event handling
    void processEvents();
    void setEventCallback(handlers::OutputHandler::EventCallback callback);

    // Lifecycle
    void start();
    void stop();
    bool isRunning() const noexcept;

private:
    // SPSC Queues (lock-free communication)
    std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue_;
    std::shared_ptr<queue::SpscRingBuffer<events::Event>> eventQueue_;

    // Core components
    std::shared_ptr<book::OrderBook> orderBook_;
    std::shared_ptr<events::SpscEventPublisher> eventPublisher_;
    std::shared_ptr<engine::MatchingEngine> matchingEngine_;
    
    // Processors and handlers
    std::unique_ptr<processors::OrderProcessor> orderProcessor_;
    std::unique_ptr<handlers::InputHandler> inputHandler_;
    std::unique_ptr<handlers::OutputHandler> outputHandler_;
};

} // namespace ob::oms

