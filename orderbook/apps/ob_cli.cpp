#include "orderbook/oms/order_management_system.hpp"
#include "orderbook/core/types.hpp"

#include <iostream>
#include <string>
#include <limits>
#include <chrono>

using namespace ob;

int main() {
    oms::OrderManagementSystem oms;

    // Set up event callback
    oms.setEventCallback([](const events::Event& event) {
        switch (event.type) {
            case events::EventType::Ack:
                std::cout << "ACK: orderId=" << event.orderId << "\n";
                break;
            case events::EventType::Trade:
                if (event.trade) {
                    std::cout << "TRADE: maker=" << event.trade->makerId 
                              << " taker=" << event.trade->takerId
                              << " price=" << event.trade->price
                              << " qty=" << event.trade->quantity << "\n";
                }
                break;
            case events::EventType::CancelAck:
                std::cout << "CANCEL_ACK: orderId=" << event.orderId << "\n";
                break;
            case events::EventType::CancelReject:
                std::cout << "CANCEL_REJECT: orderId=" << event.orderId << "\n";
                break;
            case events::EventType::Reject:
                std::cout << "REJECT: orderId=" << event.orderId << "\n";
                break;
        }
    });

    // Start the OMS
    oms.start();

    std::cout << "OrderBook CLI (q to quit)\n";
    std::string cmd;
    core::OrderId nextId = 1;
    
    while (std::cin >> cmd) {
        if (cmd == "q") {
            break;
        }
        
        // Process any pending events
        oms.processEvents();
        
        if (cmd == "add") {
            char sideChar, typeChar;
            long long price = 0;
            long long qty;
            std::cin >> sideChar >> typeChar;
            if (typeChar != 'M') {
                std::cin >> price;
            }
            std::cin >> qty;
            
            core::Side s = (sideChar == 'B' ? core::Side::Buy : core::Side::Sell);
            core::OrderType t = core::OrderType::Limit;
            if (typeChar == 'M') {
                t = core::OrderType::Market;
            }
            if (t == core::OrderType::Market) {
                price = (s == core::Side::Buy 
                    ? std::numeric_limits<long long>::max() 
                    : std::numeric_limits<long long>::min());
            }
            
            auto now = std::chrono::steady_clock::now();
            auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
            core::Order o{
                nextId++, 
                1u, 
                s, 
                t, 
                static_cast<core::Price>(price), 
                static_cast<core::Quantity>(qty),
                core::Timestamp{nowNs}
            };
            
            bool submitted = oms.submitOrder(std::move(o));
            std::cout << (submitted ? "SUBMITTED" : "QUEUE_FULL") << "\n";
        } else if (cmd == "cancel") {
            unsigned long long id;
            std::cin >> id;
            bool ok = oms.cancelOrder(id);
            std::cout << (ok ? "OK" : "NF") << "\n";
        } else if (cmd == "snap") {
            auto bids = oms.getBidsSnapshot();
            auto asks = oms.getAsksSnapshot();
            std::cout << "BIDS\n";
            for (auto& l : bids) {
                std::cout << l.price << " " << l.total << " (" << l.numOrders << ")\n";
            }
            std::cout << "ASKS\n";
            for (auto& l : asks) {
                std::cout << l.price << " " << l.total << " (" << l.numOrders << ")\n";
            }
        } else {
            std::cout << "unknown\n";
        }
    }

    oms.stop();
    return 0;
}
