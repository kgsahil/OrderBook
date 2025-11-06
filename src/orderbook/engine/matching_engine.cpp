#include "orderbook/engine/matching_engine.hpp"
#include "orderbook/book/order_book.hpp"
#include "orderbook/core/log.hpp"
#include "orderbook/core/types.hpp"
#include "orderbook/events/event_types.hpp"

#include <algorithm>
#include <chrono>
#include <stdexcept>

namespace ob::engine {

MatchingEngine::MatchingEngine(
    std::shared_ptr<book::IOrderBook> orderBook,
    std::shared_ptr<events::IEventPublisher> eventPublisher
) : orderBook_(std::move(orderBook)), eventPublisher_(std::move(eventPublisher)) {}

bool MatchingEngine::canMatch(core::Side takerSide, core::Price takerPrice, core::Price makerPrice, core::OrderType type) noexcept {
    if (type == core::OrderType::Market) return true;
    if (takerSide == core::Side::Buy) return takerPrice >= makerPrice;
    return takerPrice <= makerPrice;
}

book::OrderBook* MatchingEngine::getConcreteBook() {
    // We know it's OrderBook, but we need to cast to access internal methods
    // In a production system, we might want to expose these methods through the interface
    // or use a different design pattern
    return static_cast<book::OrderBook*>(orderBook_.get());
}

std::vector<core::Trade> MatchingEngine::process(core::Order& order) {
    std::vector<core::Trade> trades;
    auto now = std::chrono::steady_clock::now();
    auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
    order.ts = core::Timestamp{nowNs};
    
    auto* concreteBook = getConcreteBook();
    if (!concreteBook) {
        // Publish reject event
        if (eventPublisher_) {
            events::Event rejectEvent;
            rejectEvent.type = events::EventType::Reject;
            rejectEvent.orderId = order.orderId;
            rejectEvent.ts = order.ts;
            eventPublisher_->publish(std::move(rejectEvent));
        }
        return trades;
    }

    // Publish acknowledgment
    if (eventPublisher_) {
        events::Event ackEvent;
        ackEvent.type = events::EventType::Ack;
        ackEvent.orderId = order.orderId;
        ackEvent.ts = order.ts;
        eventPublisher_->publish(std::move(ackEvent));
    }

    if (order.side == core::Side::Buy) {
        auto& contra = concreteBook->asks();
        while (order.quantity > 0 && !contra.empty()) {
            auto levelIt = contra.begin();
            core::Price makerPrice = levelIt->first;
            if (!canMatch(order.side, order.price, makerPrice, order.type)) break;
            auto& dq = levelIt->second;
            while (order.quantity > 0 && !dq.empty()) {
                core::Order& maker = dq.front();
                const core::Quantity tradeQty = std::min(order.quantity, maker.quantity);
                core::Trade t{maker.orderId, order.orderId, maker.price, tradeQty, order.ts};
                trades.push_back(t);
                
                // Publish trade event
                if (eventPublisher_) {
                    events::Event tradeEvent;
                    tradeEvent.type = events::EventType::Trade;
                    tradeEvent.orderId = order.orderId;
                    tradeEvent.trade = t;
                    tradeEvent.ts = order.ts;
                    eventPublisher_->publish(std::move(tradeEvent));
                }
                
                maker.quantity -= tradeQty;
                order.quantity -= tradeQty;
                OB_LOG("TRADE maker=" << t.makerId << " taker=" << t.takerId << " px=" << t.price << " qty=" << t.quantity);
                if (maker.quantity == 0) {
                    concreteBook->eraseFrontAtLevel(core::Side::Sell, maker.price, maker.orderId);
                }
            }
            if (dq.empty()) contra.erase(levelIt);
        }
    } else {
        auto& contra = concreteBook->bids();
        while (order.quantity > 0 && !contra.empty()) {
            auto levelIt = contra.begin();
            core::Price makerPrice = levelIt->first;
            if (!canMatch(order.side, order.price, makerPrice, order.type)) break;
            auto& dq = levelIt->second;
            while (order.quantity > 0 && !dq.empty()) {
                core::Order& maker = dq.front();
                const core::Quantity tradeQty = std::min(order.quantity, maker.quantity);
                core::Trade t{maker.orderId, order.orderId, maker.price, tradeQty, order.ts};
                trades.push_back(t);
                
                // Publish trade event
                if (eventPublisher_) {
                    events::Event tradeEvent;
                    tradeEvent.type = events::EventType::Trade;
                    tradeEvent.orderId = order.orderId;
                    tradeEvent.trade = t;
                    tradeEvent.ts = order.ts;
                    eventPublisher_->publish(std::move(tradeEvent));
                }
                
                maker.quantity -= tradeQty;
                order.quantity -= tradeQty;
                OB_LOG("TRADE maker=" << t.makerId << " taker=" << t.takerId << " px=" << t.price << " qty=" << t.quantity);
                if (maker.quantity == 0) {
                    concreteBook->eraseFrontAtLevel(core::Side::Buy, maker.price, maker.orderId);
                }
            }
            if (dq.empty()) contra.erase(levelIt);
        }
    }

    // Market orders do not rest
    if (order.type == core::OrderType::Market) {
        order.quantity = 0;
        return trades;
    }

    if (order.quantity > 0 && order.type == core::OrderType::Limit) {
        orderBook_->addOrder(std::move(order));
    }

    return trades;
}

} // namespace ob::engine

