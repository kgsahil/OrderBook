#pragma once

#include "orderbook/core/types.hpp"
#include <optional>
#include <cstdint>
#include <chrono>

namespace ob::events {

enum class EventType : std::uint8_t { 
    Ack,           // Order acknowledged
    Trade,         // Trade executed
    CancelAck,     // Cancel acknowledged
    CancelReject,  // Cancel rejected
    Reject         // Order rejected
};

struct Event final {
    EventType type{EventType::Ack};
    core::OrderId orderId{};
    std::optional<core::Trade> trade; // present for Trade events
    core::Timestamp ts{}; // event timestamp
};

} // namespace ob::events

