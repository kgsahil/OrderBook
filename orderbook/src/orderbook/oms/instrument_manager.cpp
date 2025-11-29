#include "orderbook/oms/instrument_manager.hpp"
#include <algorithm>

namespace ob::oms {

InstrumentManager::InstrumentManager() = default;

std::uint32_t InstrumentManager::addInstrument(const std::string& ticker,
                                               const std::string& description,
                                               const std::string& industry,
                                               double initialPrice) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::uint32_t symbolId = nextSymbolId_++;
    
    // Create new OMS instance for this instrument
    auto oms = std::make_unique<OrderManagementSystem>();
    oms->start();
    
    // Store instrument metadata
    instruments_[symbolId] = core::Instrument(symbolId, ticker, description, industry, initialPrice);
    orderBooks_[symbolId] = std::move(oms);
    
    return symbolId;
}

bool InstrumentManager::removeInstrument(std::uint32_t symbolId) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = orderBooks_.find(symbolId);
    if (it == orderBooks_.end()) {
        return false;
    }
    
    // Stop the OMS before removing
    it->second->stop();
    orderBooks_.erase(it);
    instruments_.erase(symbolId);
    
    return true;
}

bool InstrumentManager::hasInstrument(std::uint32_t symbolId) const {
    std::lock_guard<std::mutex> lock(mutex_);
    return orderBooks_.find(symbolId) != orderBooks_.end();
}

std::optional<core::Instrument> InstrumentManager::getInstrument(std::uint32_t symbolId) const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = instruments_.find(symbolId);
    if (it == instruments_.end()) {
        return std::nullopt;
    }
    
    return it->second;
}

std::vector<core::Instrument> InstrumentManager::listInstruments() const {
    std::lock_guard<std::mutex> lock(mutex_);
    
    std::vector<core::Instrument> result;
    result.reserve(instruments_.size());
    
    for (const auto& [id, instrument] : instruments_) {
        result.push_back(instrument);
    }
    
    return result;
}

bool InstrumentManager::submitOrder(const core::Order& order) {
    auto* oms = getOMS(order.symbolId);
    if (!oms) {
        return false;
    }
    return oms->submitOrder(order);
}

bool InstrumentManager::submitOrder(core::Order&& order) {
    auto* oms = getOMS(order.symbolId);
    if (!oms) {
        return false;
    }
    return oms->submitOrder(std::move(order));
}

bool InstrumentManager::cancelOrder(std::uint32_t symbolId, core::OrderId orderId) {
    auto* oms = getOMS(symbolId);
    if (!oms) {
        return false;
    }
    return oms->cancelOrder(orderId);
}

std::optional<core::Price> InstrumentManager::getBestBid(std::uint32_t symbolId) const {
    auto* oms = getOMS(symbolId);
    if (!oms) {
        return std::nullopt;
    }
    return oms->getBestBid();
}

std::optional<core::Price> InstrumentManager::getBestAsk(std::uint32_t symbolId) const {
    auto* oms = getOMS(symbolId);
    if (!oms) {
        return std::nullopt;
    }
    return oms->getBestAsk();
}

std::vector<book::LevelSummary> InstrumentManager::getBidsSnapshot(std::uint32_t symbolId, std::size_t depth) const {
    auto* oms = getOMS(symbolId);
    if (!oms) {
        return {};
    }
    return oms->getBidsSnapshot(depth);
}

std::vector<book::LevelSummary> InstrumentManager::getAsksSnapshot(std::uint32_t symbolId, std::size_t depth) const {
    auto* oms = getOMS(symbolId);
    if (!oms) {
        return {};
    }
    return oms->getAsksSnapshot(depth);
}

void InstrumentManager::processEvents() {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& [symbolId, oms] : orderBooks_) {
        oms->processEvents();
    }
}

void InstrumentManager::setEventCallback(handlers::OutputHandler::EventCallback callback) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& [symbolId, oms] : orderBooks_) {
        oms->setEventCallback(callback);
    }
}

void InstrumentManager::start() {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& [symbolId, oms] : orderBooks_) {
        oms->start();
    }
}

void InstrumentManager::stop() {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& [symbolId, oms] : orderBooks_) {
        oms->stop();
    }
}

bool InstrumentManager::isRunning() const noexcept {
    std::lock_guard<std::mutex> lock(mutex_);
    return !orderBooks_.empty();
}

OrderManagementSystem* InstrumentManager::getOMS(std::uint32_t symbolId) const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto it = orderBooks_.find(symbolId);
    if (it == orderBooks_.end()) {
        return nullptr;
    }
    return it->second.get();
}

} // namespace ob::oms

