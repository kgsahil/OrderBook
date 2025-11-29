#pragma once

#include "orderbook/core/instrument.hpp"
#include "orderbook/core/types.hpp"
#include "orderbook/oms/order_management_system.hpp"
#include "orderbook/oms/i_order_book_service.hpp"
#include <memory>
#include <unordered_map>
#include <mutex>
#include <string>
#include <vector>

namespace ob::oms {

/**
 * InstrumentManager implements IOrderBookService interface.
 * 
 * This allows the TCP server to depend on the abstraction rather than
 * the concrete implementation, enabling dependency injection and testability.
 */
class InstrumentManager : public IOrderBookService {
public:
    InstrumentManager();
    ~InstrumentManager() = default;
    
    // Instrument management (IOrderBookService interface)
    std::uint32_t addInstrument(const std::string& ticker,
                                const std::string& description,
                                const std::string& industry,
                                double initialPrice) override;
    bool removeInstrument(std::uint32_t symbolId) override;
    bool hasInstrument(std::uint32_t symbolId) const override;
    std::optional<core::Instrument> getInstrument(std::uint32_t symbolId) const override;
    std::vector<core::Instrument> listInstruments() const override;

    // Order operations (IOrderBookService interface)
    bool submitOrder(const core::Order& order) override;
    bool submitOrder(core::Order&& order) override;
    bool cancelOrder(std::uint32_t symbolId, core::OrderId orderId) override;

    // Market data (IOrderBookService interface)
    std::optional<core::Price> getBestBid(std::uint32_t symbolId) const override;
    std::optional<core::Price> getBestAsk(std::uint32_t symbolId) const override;
    std::vector<book::LevelSummary> getBidsSnapshot(std::uint32_t symbolId, std::size_t depth = 0) const override;
    std::vector<book::LevelSummary> getAsksSnapshot(std::uint32_t symbolId, std::size_t depth = 0) const override;

    // Event handling (IOrderBookService interface)
    void processEvents() override;
    void setEventCallback(EventCallback callback) override;
    
    // Lifecycle (IOrderBookService interface)
    void start() override;
    void stop() override;
    bool isRunning() const noexcept override;
    
private:
    mutable std::mutex mutex_;
    std::unordered_map<std::uint32_t, std::unique_ptr<OrderManagementSystem>> orderBooks_;
    std::unordered_map<std::uint32_t, core::Instrument> instruments_;
    std::atomic<std::uint32_t> nextSymbolId_{1};
    
    OrderManagementSystem* getOMS(std::uint32_t symbolId) const;
};

} // namespace ob::oms

