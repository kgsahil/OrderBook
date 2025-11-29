#pragma once

#include "orderbook/core/instrument.hpp"
#include "orderbook/core/types.hpp"
#include "orderbook/oms/order_management_system.hpp"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <string>
#include <vector>

namespace ob::oms {

class InstrumentManager {
public:
    InstrumentManager();
    ~InstrumentManager() = default;
    
    // Instrument management
    std::uint32_t addInstrument(const std::string& ticker,
                                const std::string& description,
                                const std::string& industry,
                                double initialPrice);
    bool removeInstrument(std::uint32_t symbolId);
    bool hasInstrument(std::uint32_t symbolId) const;
    std::optional<core::Instrument> getInstrument(std::uint32_t symbolId) const;
    std::vector<core::Instrument> listInstruments() const;
    
    // Order operations (route to correct OrderBook)
    bool submitOrder(const core::Order& order);
    bool submitOrder(core::Order&& order);
    bool cancelOrder(std::uint32_t symbolId, core::OrderId orderId);
    
    // Market data (per instrument)
    std::optional<core::Price> getBestBid(std::uint32_t symbolId) const;
    std::optional<core::Price> getBestAsk(std::uint32_t symbolId) const;
    std::vector<book::LevelSummary> getBidsSnapshot(std::uint32_t symbolId, std::size_t depth = 0) const;
    std::vector<book::LevelSummary> getAsksSnapshot(std::uint32_t symbolId, std::size_t depth = 0) const;
    
    // Event handling (aggregate from all OrderBooks)
    void processEvents();
    void setEventCallback(handlers::OutputHandler::EventCallback callback);
    
    // Lifecycle
    void start();
    void stop();
    bool isRunning() const noexcept;
    
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::uint32_t, std::unique_ptr<OrderManagementSystem>> orderBooks_;
    std::unordered_map<std::uint32_t, core::Instrument> instruments_;
    std::atomic<std::uint32_t> nextSymbolId_{1};
    
    OrderManagementSystem* getOMS(std::uint32_t symbolId) const;
};

} // namespace ob::oms

