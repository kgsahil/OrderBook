#pragma once

#include "orderbook/core/types.hpp"
#include "orderbook/core/instrument.hpp"
#include "orderbook/book/order_book.hpp"
#include "orderbook/events/event_types.hpp"
#include <string>
#include <vector>
#include <optional>
#include <functional>

namespace ob::oms {

/**
 * Abstract interface for OrderBook service operations.
 * 
 * This interface decouples the TCP server from the concrete InstrumentManager
 * implementation, enabling:
 * - Dependency injection
 * - Testability (mock implementations)
 * - Swappable implementations
 * - Follows Dependency Inversion Principle (SOLID)
 */
class IOrderBookService {
public:
    virtual ~IOrderBookService() = default;

    // Instrument management
    virtual std::uint32_t addInstrument(
        const std::string& ticker,
        const std::string& description,
        const std::string& industry,
        double initialPrice
    ) = 0;
    
    virtual bool removeInstrument(std::uint32_t symbolId) = 0;
    virtual bool hasInstrument(std::uint32_t symbolId) const = 0;
    virtual std::optional<core::Instrument> getInstrument(std::uint32_t symbolId) const = 0;
    virtual std::vector<core::Instrument> listInstruments() const = 0;

    // Order operations
    virtual bool submitOrder(const core::Order& order) = 0;
    virtual bool submitOrder(core::Order&& order) = 0;
    virtual bool cancelOrder(std::uint32_t symbolId, core::OrderId orderId) = 0;

    // Market data
    virtual std::optional<core::Price> getBestBid(std::uint32_t symbolId) const = 0;
    virtual std::optional<core::Price> getBestAsk(std::uint32_t symbolId) const = 0;
    virtual std::vector<book::LevelSummary> getBidsSnapshot(
        std::uint32_t symbolId, 
        std::size_t depth = 0
    ) const = 0;
    virtual std::vector<book::LevelSummary> getAsksSnapshot(
        std::uint32_t symbolId, 
        std::size_t depth = 0
    ) const = 0;

    // Event handling
    virtual void processEvents() = 0;
    virtual void setEventCallback(
        std::function<void(const events::Event&)> callback
    ) = 0;
    
    // Type alias for callback (matches handlers::OutputHandler::EventCallback)
    using EventCallback = std::function<void(const events::Event&)>;

    // Lifecycle
    virtual void start() = 0;
    virtual void stop() = 0;
    virtual bool isRunning() const noexcept = 0;
};

} // namespace ob::oms

