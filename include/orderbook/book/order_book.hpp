#pragma once

#include "orderbook/book/i_order_book.hpp"
#include "orderbook/core/types.hpp"
#include <map>
#include <deque>
#include <unordered_map>

namespace ob::book {

// Concrete implementation of order book
class OrderBook final : public IOrderBook {
public:
    OrderBook() = default;

    bool addOrder(core::Order order) override;
    bool cancelOrder(core::OrderId id) override;
    void eraseFrontAtLevel(core::Side side, core::Price price, core::OrderId expectedId);

    std::optional<core::Price> findBestBid() const noexcept override;
    std::optional<core::Price> findBestAsk() const noexcept override;
    std::vector<LevelSummary> snapshotBidsL2(std::size_t depth = 0) const override;
    std::vector<LevelSummary> snapshotAsksL2(std::size_t depth = 0) const override;

    // Internal helpers for MatchingEngine (not part of interface)
    std::deque<core::Order>& bestQueue(core::Side side);
    std::map<core::Price, std::deque<core::Order>, std::greater<core::Price>>& bids() { return bids_; }
    std::map<core::Price, std::deque<core::Order>, std::less<core::Price>>& asks() { return asks_; }
    const std::deque<core::Order>* getQueueAt(core::Side side, core::Price price) const;

private:
    using BidMap = std::map<core::Price, std::deque<core::Order>, std::greater<core::Price>>;
    using AskMap = std::map<core::Price, std::deque<core::Order>, std::less<core::Price>>;

    BidMap bids_{}; // highest price first
    AskMap asks_{}; // lowest price first

    struct OrderLocator {
        core::Side side{core::Side::Buy};
        core::Price price{0};
        std::deque<core::Order>::iterator it;
    };

    std::unordered_map<core::OrderId, OrderLocator> locators_;
};

} // namespace ob::book

