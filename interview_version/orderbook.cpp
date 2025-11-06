#include "orderbook.h"
#include <algorithm>
#include <limits>

std::vector<Trade> OrderBook::addOrder(Order order) {
    // Try to match first
    auto trades = matchOrder(order);
    
    // If remaining quantity and limit order, add to book
    if (order.quantity > 0 && order.type == OrderType::Limit) {
        if (order.side == Side::Buy) {
            auto& queue = bids_[order.price];
            queue.push_back(order);
            auto it = std::prev(queue.end());
            locators_[order.orderId] = {Side::Buy, order.price, it};
        } else {
            auto& queue = asks_[order.price];
            queue.push_back(order);
            auto it = std::prev(queue.end());
            locators_[order.orderId] = {Side::Sell, order.price, it};
        }
    }
    
    return trades;
}

bool OrderBook::cancelOrder(uint64_t orderId) {
    auto it = locators_.find(orderId);
    if (it == locators_.end()) return false;
    
    auto& loc = it->second;
    removeOrder(orderId, loc.side, loc.price, loc.it);
    locators_.erase(it);
    return true;
}

std::optional<int64_t> OrderBook::getBestBid() const {
    if (bids_.empty()) return std::nullopt;
    return bids_.begin()->first;
}

std::optional<int64_t> OrderBook::getBestAsk() const {
    if (asks_.empty()) return std::nullopt;
    return asks_.begin()->first;
}

std::vector<Level> OrderBook::getBidsSnapshot(size_t depth) const {
    std::vector<Level> result;
    size_t count = 0;
    for (const auto& [price, orders] : bids_) {
        if (depth > 0 && count >= depth) break;
        int64_t total = 0;
        for (const auto& o : orders) total += o.quantity;
        result.push_back({price, total, orders.size()});
        ++count;
    }
    return result;
}

std::vector<Level> OrderBook::getAsksSnapshot(size_t depth) const {
    std::vector<Level> result;
    size_t count = 0;
    for (const auto& [price, orders] : asks_) {
        if (depth > 0 && count >= depth) break;
        int64_t total = 0;
        for (const auto& o : orders) total += o.quantity;
        result.push_back({price, total, orders.size()});
        ++count;
    }
    return result;
}

std::vector<Trade> OrderBook::matchOrder(Order& order) {
    std::vector<Trade> trades;
    
    // Set market order price
    if (order.type == OrderType::Market) {
        order.price = (order.side == Side::Buy) 
            ? std::numeric_limits<int64_t>::max() 
            : std::numeric_limits<int64_t>::min();
    }
    
    if (order.side == Side::Buy) {
        // Match against asks (sell orders)
        while (order.quantity > 0 && !asks_.empty()) {
            auto levelIt = asks_.begin();
            int64_t makerPrice = levelIt->first;
            
            if (!canMatch(order.side, order.price, makerPrice, order.type)) break;
            
            auto& queue = levelIt->second;
            while (order.quantity > 0 && !queue.empty()) {
                Order& maker = queue.front();
                int64_t tradeQty = std::min(order.quantity, maker.quantity);
                
                trades.push_back({maker.orderId, order.orderId, maker.price, tradeQty});
                
                maker.quantity -= tradeQty;
                order.quantity -= tradeQty;
                
                if (maker.quantity == 0) {
                    locators_.erase(maker.orderId);
                    queue.pop_front();
                }
            }
            
            if (queue.empty()) {
                asks_.erase(levelIt);
            }
        }
    } else {
        // Match against bids (buy orders)
        while (order.quantity > 0 && !bids_.empty()) {
            auto levelIt = bids_.begin();
            int64_t makerPrice = levelIt->first;
            
            if (!canMatch(order.side, order.price, makerPrice, order.type)) break;
            
            auto& queue = levelIt->second;
            while (order.quantity > 0 && !queue.empty()) {
                Order& maker = queue.front();
                int64_t tradeQty = std::min(order.quantity, maker.quantity);
                
                trades.push_back({maker.orderId, order.orderId, maker.price, tradeQty});
                
                maker.quantity -= tradeQty;
                order.quantity -= tradeQty;
                
                if (maker.quantity == 0) {
                    locators_.erase(maker.orderId);
                    queue.pop_front();
                }
            }
            
            if (queue.empty()) {
                bids_.erase(levelIt);
            }
        }
    }
    
    return trades;
}

bool OrderBook::canMatch(Side takerSide, int64_t takerPrice, int64_t makerPrice, OrderType type) {
    if (type == OrderType::Market) return true;
    if (takerSide == Side::Buy) return takerPrice >= makerPrice;
    return takerPrice <= makerPrice;
}

void OrderBook::removeOrder(uint64_t orderId, Side side, int64_t price, std::deque<Order>::iterator it) {
    if (side == Side::Buy) {
        auto levelIt = bids_.find(price);
        if (levelIt != bids_.end()) {
            levelIt->second.erase(it);
            if (levelIt->second.empty()) {
                bids_.erase(levelIt);
            }
        }
    } else {
        auto levelIt = asks_.find(price);
        if (levelIt != asks_.end()) {
            levelIt->second.erase(it);
            if (levelIt->second.empty()) {
                asks_.erase(levelIt);
            }
        }
    }
}

