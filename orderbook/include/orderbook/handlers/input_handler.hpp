#pragma once

#include "orderbook/core/types.hpp"
#include "orderbook/queue/spsc_queue.hpp"
#include "orderbook/core/constants.hpp"
#include <memory>
#include <atomic>

namespace ob::handlers {

// Input handler for submitting orders to the queue
// Single Responsibility: Handle order input
class InputHandler {
public:
    explicit InputHandler(std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue)
        : orderQueue_(std::move(orderQueue)) {}

    bool submitOrder(const core::Order& order) {
        return orderQueue_ && orderQueue_->tryPush(order);
    }

    bool submitOrder(core::Order&& order) {
        return orderQueue_ && orderQueue_->tryPush(std::move(order));
    }

    bool isQueueFull() const {
        return orderQueue_ && orderQueue_->full();
    }

private:
    std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue_;
};

} // namespace ob::handlers

