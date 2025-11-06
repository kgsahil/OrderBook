#pragma once

#include <iostream>
#include <chrono>
#include <cstdint>

namespace ob::core {

inline std::uint64_t nowNs() {
    using clock = std::chrono::steady_clock;
    return std::chrono::duration_cast<std::chrono::nanoseconds>(clock::now().time_since_epoch()).count();
}

#ifdef ORDERBOOK_VERBOSE_LOG
#define OB_LOG(msg) do { std::cout << nowNs() << " | " << msg << std::endl; } while(0)
#else
#define OB_LOG(msg) do {} while(0)
#endif

} // namespace ob::core

