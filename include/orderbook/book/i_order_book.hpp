#pragma once

#include "orderbook/core/types.hpp"
#include <optional>
#include <vector>

namespace ob::book {

struct LevelSummary {
    core::Price price{0};
    core::Quantity total{0};
    std::size_t numOrders{0};
};

// Interface for order book operations (Interface Segregation Principle)
class IOrderBook {
public:
    virtual ~IOrderBook() = default;
    
    // Order management
    virtual bool addOrder(core::Order order) = 0;
    virtual bool cancelOrder(core::OrderId id) = 0;
    
    // Market data queries
    virtual std::optional<core::Price> findBestBid() const noexcept = 0;
    virtual std::optional<core::Price> findBestAsk() const noexcept = 0;
    virtual std::vector<LevelSummary> snapshotBidsL2(std::size_t depth = 0) const = 0;
    virtual std::vector<LevelSummary> snapshotAsksL2(std::size_t depth = 0) const = 0;
};

} // namespace ob::book

