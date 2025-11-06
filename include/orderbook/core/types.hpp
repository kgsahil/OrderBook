#pragma once

#include <cstdint>
#include <chrono>

namespace ob::core {

enum class Side : std::uint8_t { Buy = 0, Sell = 1 };
enum class OrderType : std::uint8_t { Limit = 0, Market = 1 };

using OrderId = std::uint64_t;
using Price = std::int64_t; // price in ticks
using Quantity = std::int64_t; // quantity in lots
using Timestamp = std::chrono::time_point<std::chrono::steady_clock, std::chrono::nanoseconds>;

struct alignas(64) Order final {
    OrderId     orderId{};
    Side        side{Side::Buy};
    OrderType   type{OrderType::Limit};
    Price       price{0};
    Quantity    quantity{0};
    Timestamp   ts{}; // arrival timestamp
    std::uint32_t symbolId{0};

    Order() = default;
    Order(OrderId id, std::uint32_t sym, Side s, OrderType t, Price p, Quantity q, Timestamp tstamp) noexcept
        : orderId(id), side(s), type(t), price(p), quantity(q), ts(tstamp), symbolId(sym) {}
};

struct Trade final {
    OrderId makerId{};
    OrderId takerId{};
    Price   price{0};
    Quantity quantity{0};
    Timestamp ts{};
};

} // namespace ob::core

