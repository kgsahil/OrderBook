#pragma once

#include "orderbook/core/types.hpp"
#include "orderbook/events/event_types.hpp"
#include <vector>

namespace ob::engine {

// Interface for matching engine (Dependency Inversion Principle)
class IMatchingEngine {
public:
    virtual ~IMatchingEngine() = default;
    virtual std::vector<core::Trade> process(core::Order& order) = 0;
};

} // namespace ob::engine

