#include "orderbook/oms/order_management_system.hpp"

namespace ob::oms {

OrderManagementSystem::OrderManagementSystem(std::size_t queueSize) {
    // Create SPSC queues
    orderQueue_ = std::make_shared<queue::SpscRingBuffer<core::Order>>(queueSize);
    eventQueue_ = std::make_shared<queue::SpscRingBuffer<events::Event>>(queueSize);

    // Create core components
    orderBook_ = std::make_shared<book::OrderBook>();
    eventPublisher_ = std::make_shared<events::SpscEventPublisher>(eventQueue_);
    matchingEngine_ = std::make_shared<engine::MatchingEngine>(orderBook_, eventPublisher_);

    // Create processors and handlers
    orderProcessor_ = std::make_unique<processors::OrderProcessor>(orderQueue_, matchingEngine_);
    inputHandler_ = std::make_unique<handlers::InputHandler>(orderQueue_);
    outputHandler_ = std::make_unique<handlers::OutputHandler>(eventQueue_);
}

bool OrderManagementSystem::submitOrder(const core::Order& order) {
    return inputHandler_->submitOrder(order);
}

bool OrderManagementSystem::submitOrder(core::Order&& order) {
    return inputHandler_->submitOrder(std::move(order));
}

bool OrderManagementSystem::cancelOrder(core::OrderId orderId) {
    // Cancel is synchronous for now (could be queued as well)
    return orderBook_->cancelOrder(orderId);
}

std::optional<core::Price> OrderManagementSystem::getBestBid() const {
    return orderBook_->findBestBid();
}

std::optional<core::Price> OrderManagementSystem::getBestAsk() const {
    return orderBook_->findBestAsk();
}

std::vector<book::LevelSummary> OrderManagementSystem::getBidsSnapshot(std::size_t depth) const {
    return orderBook_->snapshotBidsL2(depth);
}

std::vector<book::LevelSummary> OrderManagementSystem::getAsksSnapshot(std::size_t depth) const {
    return orderBook_->snapshotAsksL2(depth);
}

void OrderManagementSystem::processEvents() {
    outputHandler_->processEvents();
}

void OrderManagementSystem::setEventCallback(handlers::OutputHandler::EventCallback callback) {
    outputHandler_->setCallback(std::move(callback));
}

void OrderManagementSystem::start() {
    orderProcessor_->start();
}

void OrderManagementSystem::stop() {
    orderProcessor_->stop();
}

bool OrderManagementSystem::isRunning() const noexcept {
    return orderProcessor_->isRunning();
}

} // namespace ob::oms

