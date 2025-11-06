#pragma once

#include "orderbook/engine/i_matching_engine.hpp"
#include "orderbook/book/i_order_book.hpp"
#include "orderbook/events/event_publisher.hpp"
#include "orderbook/core/types.hpp"
#include <memory>
#include <vector>
#include <stdexcept>

namespace ob::engine {

// Concrete matching engine implementation
class MatchingEngine final : public IMatchingEngine {
public:
    MatchingEngine(
        std::shared_ptr<book::IOrderBook> orderBook,
        std::shared_ptr<events::IEventPublisher> eventPublisher
    );

    std::vector<core::Trade> process(core::Order& order) override;

private:
    static bool canMatch(core::Side takerSide, core::Price takerPrice, core::Price makerPrice, core::OrderType type) noexcept;
    
    std::shared_ptr<book::IOrderBook> orderBook_;
    std::shared_ptr<events::IEventPublisher> eventPublisher_;
    
    // Need access to internal methods for matching
    book::OrderBook* getConcreteBook();
};

} // namespace ob::engine

