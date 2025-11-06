#include "orderbook/processors/order_processor.hpp"
#include "orderbook/core/log.hpp"
#include <thread>

namespace ob::processors {

OrderProcessor::OrderProcessor(
    std::shared_ptr<queue::SpscRingBuffer<core::Order>> orderQueue,
    std::shared_ptr<engine::IMatchingEngine> matchingEngine
) : orderQueue_(std::move(orderQueue)), matchingEngine_(std::move(matchingEngine)) {}

OrderProcessor::~OrderProcessor() {
    stop();
}

void OrderProcessor::start() {
    if (running_.exchange(true)) {
        return; // Already running
    }
    processorThread_ = std::thread(&OrderProcessor::processLoop, this);
}

void OrderProcessor::stop() {
    if (!running_.exchange(false)) {
        return; // Already stopped
    }
    if (processorThread_.joinable()) {
        processorThread_.join();
    }
}

void OrderProcessor::processLoop() {
    core::Order order;
    while (running_.load()) {
        if (orderQueue_->tryPop(order)) {
            matchingEngine_->process(order);
        } else {
            // Queue is empty, yield to avoid busy-waiting
            std::this_thread::yield();
        }
    }
}

} // namespace ob::processors

