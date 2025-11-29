#include "orderbook/book/order_book.hpp"
#include "orderbook/core/log.hpp"
#include "orderbook/core/types.hpp"

#include <algorithm>

namespace ob::book {

bool OrderBook::addOrder(core::Order order) {
    // Validate LIMIT order price must be positive
    // Note: Market orders should not reach here (they're consumed immediately)
    if (order.type == core::OrderType::Limit && order.price <= 0) {
        OB_LOG("REJECT id=" << order.orderId << " invalid price=" << order.price);
        return false;
    }
    
    // Validate quantity
    if (order.quantity <= 0) {
        OB_LOG("REJECT id=" << order.orderId << " invalid quantity=" << order.quantity);
        return false;
    }
    
    // Optimized: Cache price and side to avoid repeated access, use emplace for locators
    const auto price = order.price;
    const auto side = order.side;
    const auto orderId = order.orderId;
    
    if (side == core::Side::Buy) {
        // Get or create deque for this price level
        auto& q = bids_[price];
        
        // Emplace order and capture iterator efficiently
        q.emplace_back(std::move(order));
        auto orderIt = std::prev(q.end());
        
        // Use emplace (no hint needed for small maps) - more efficient than operator[]
        locators_.emplace(orderId, OrderLocator{side, price, orderIt});
        OB_LOG("ADD id=" << orderId << " side=B price=" << price << " qty=" << orderIt->quantity);
    } else {
        auto& q = asks_[price];
        
        q.emplace_back(std::move(order));
        auto orderIt = std::prev(q.end());
        
        locators_.emplace(orderId, OrderLocator{side, price, orderIt});
        OB_LOG("ADD id=" << orderId << " side=S price=" << price << " qty=" << orderIt->quantity);
    }
    return true;
}

bool OrderBook::cancelOrder(core::OrderId id) {
    auto locIt = locators_.find(id);
    if (locIt == locators_.end()) return false;
    
    // Copy the locator before erasing from map to avoid iterator invalidation issues
    auto loc = locIt->second;
    
    // Erase from locators map first to avoid dangling references
    locators_.erase(locIt);
    
    if (loc.side == core::Side::Buy) {
        auto it = bids_.find(loc.price);
        if (it == bids_.end()) return false;
        auto& dq = it->second;
        OB_LOG("CANCEL id=" << id);
        dq.erase(loc.it);
        if (dq.empty()) bids_.erase(it);
    } else {
        auto it = asks_.find(loc.price);
        if (it == asks_.end()) return false;
        auto& dq = it->second;
        OB_LOG("CANCEL id=" << id);
        dq.erase(loc.it);
        if (dq.empty()) asks_.erase(it);
    }
    return true;
}

void OrderBook::eraseFrontAtLevel(core::Side side, core::Price price, core::OrderId expectedId) {
    if (side == core::Side::Buy) {
        auto it = bids_.find(price);
        if (it == bids_.end()) return;
        auto& dq = it->second;
        if (!dq.empty() && dq.front().orderId == expectedId) {
            locators_.erase(expectedId);
            dq.pop_front();
            OB_LOG("ERASE_FRONT id=" << expectedId << " price=" << price);
        }
    } else {
        auto it = asks_.find(price);
        if (it == asks_.end()) return;
        auto& dq = it->second;
        if (!dq.empty() && dq.front().orderId == expectedId) {
            locators_.erase(expectedId);
            dq.pop_front();
            OB_LOG("ERASE_FRONT id=" << expectedId << " price=" << price);
        }
    }
}

std::optional<core::Price> OrderBook::findBestBid() const noexcept {
    if (bids_.empty()) return std::nullopt;
    return bids_.begin()->first;
}

std::optional<core::Price> OrderBook::findBestAsk() const noexcept {
    if (asks_.empty()) return std::nullopt;
    return asks_.begin()->first;
}

std::vector<LevelSummary> OrderBook::snapshotBidsL2(std::size_t depth) const {
    std::vector<LevelSummary> out;
    out.reserve(depth == 0 ? bids_.size() : std::min(depth, bids_.size()));
    std::size_t i = 0;
    for (const auto& [price, dq] : bids_) {
        core::Quantity total = 0;
        for (const auto& o : dq) total += o.quantity;
        out.push_back(LevelSummary{price, total, dq.size()});
        if (depth && ++i >= depth) break;
    }
    return out;
}

std::vector<LevelSummary> OrderBook::snapshotAsksL2(std::size_t depth) const {
    std::vector<LevelSummary> out;
    out.reserve(depth == 0 ? asks_.size() : std::min(depth, asks_.size()));
    std::size_t i = 0;
    for (const auto& [price, dq] : asks_) {
        core::Quantity total = 0;
        for (const auto& o : dq) total += o.quantity;
        out.push_back(LevelSummary{price, total, dq.size()});
        if (depth && ++i >= depth) break;
    }
    return out;
}

std::deque<core::Order>& OrderBook::bestQueue(core::Side side) {
    if (side == core::Side::Buy) {
        auto it = bids_.begin();
        if (it == bids_.end()) throw std::out_of_range("no bid levels");
        return it->second;
    } else {
        auto it = asks_.begin();
        if (it == asks_.end()) throw std::out_of_range("no ask levels");
        return it->second;
    }
}

const std::deque<core::Order>* OrderBook::getQueueAt(core::Side side, core::Price price) const {
    if (side == core::Side::Buy) {
        auto it = bids_.find(price);
        if (it == bids_.end()) return nullptr;
        return &it->second;
    } else {
        auto it = asks_.find(price);
        if (it == asks_.end()) return nullptr;
        return &it->second;
    }
}

} // namespace ob::book

