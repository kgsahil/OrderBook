#pragma once

#include <cstdint>
#include <string>
#include <chrono>

namespace ob::core {

struct Instrument {
    std::uint32_t symbolId{0};
    std::string ticker;
    std::string description;
    std::string industry;
    double initialPrice{0.0};
    std::chrono::system_clock::time_point createdAt;
    
    Instrument() = default;
    Instrument(std::uint32_t id, const std::string& t, const std::string& desc, const std::string& ind, double price)
        : symbolId(id),
          ticker(t),
          description(desc),
          industry(ind),
          initialPrice(price),
          createdAt(std::chrono::system_clock::now()) {}
};

} // namespace ob::core

