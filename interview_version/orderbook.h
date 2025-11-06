#pragma once

#include <cstdint>
#include <map>
#include <deque>
#include <unordered_map>
#include <optional>
#include <vector>

// Simplified interview version - all in one header for speed

enum class Side { Buy, Sell };
enum class OrderType { Limit, Market };

struct Order {
    uint64_t orderId;
    Side side;
    OrderType type;
    int64_t price;  // For market orders, use max/min
    int64_t quantity;
    
    Order(uint64_t id, Side s, OrderType t, int64_t p, int64_t qty)
        : orderId(id), side(s), type(t), price(p), quantity(qty) {}
};

struct Trade {
    uint64_t makerId;
    uint64_t takerId;
    int64_t price;
    int64_t quantity;
};

struct Level {
    int64_t price;
    int64_t totalQty;
    size_t numOrders;
};

class OrderBook {
public:
    // Add order to book (returns trades if matched)
    std::vector<Trade> addOrder(Order order);
    
    // Cancel order by ID
    bool cancelOrder(uint64_t orderId);
    
    // Get best bid/ask
    std::optional<int64_t> getBestBid() const;
    std::optional<int64_t> getBestAsk() const;
    
    // Get snapshot
    std::vector<Level> getBidsSnapshot(size_t depth = 0) const;
    std::vector<Level> getAsksSnapshot(size_t depth = 0) const;

private:
    // Price level -> orders (FIFO)
    std::map<int64_t, std::deque<Order>, std::greater<int64_t>> bids_;  // Highest first
    std::map<int64_t, std::deque<Order>, std::less<int64_t>> asks_;     // Lowest first
    
    // Fast cancel lookup: orderId -> (side, price, iterator)
    struct OrderLocation {
        Side side;
        int64_t price;
        std::deque<Order>::iterator it;
    };
    std::unordered_map<uint64_t, OrderLocation> locators_;
    
    // Matching logic
    std::vector<Trade> matchOrder(Order& order);
    bool canMatch(Side takerSide, int64_t takerPrice, int64_t makerPrice, OrderType type);
    void removeOrder(uint64_t orderId, Side side, int64_t price, std::deque<Order>::iterator it);
};

