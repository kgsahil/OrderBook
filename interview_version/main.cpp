#include "orderbook.h"
#include <iostream>
#include <string>
#include <limits>

int main() {
    OrderBook book;
    uint64_t nextOrderId = 1;
    
    std::cout << "OrderBook CLI (q to quit)\n";
    std::string cmd;
    
    while (std::cin >> cmd) {
        if (cmd == "q") break;
        
        if (cmd == "add") {
            char sideChar, typeChar;
            int64_t price = 0, qty;
            std::cin >> sideChar >> typeChar;
            if (typeChar != 'M') std::cin >> price;
            std::cin >> qty;
            
            Side side = (sideChar == 'B') ? Side::Buy : Side::Sell;
            OrderType type = (typeChar == 'M') ? OrderType::Market : OrderType::Limit;
            
            if (type == OrderType::Market) {
                price = (side == Side::Buy) 
                    ? std::numeric_limits<int64_t>::max() 
                    : std::numeric_limits<int64_t>::min();
            }
            
            Order order(nextOrderId++, side, type, price, qty);
            auto trades = book.addOrder(order);
            
            std::cout << "Trades: " << trades.size() << "\n";
            for (const auto& t : trades) {
                std::cout << "  Trade: maker=" << t.makerId 
                          << " taker=" << t.takerId
                          << " price=" << t.price
                          << " qty=" << t.quantity << "\n";
            }
        }
        else if (cmd == "cancel") {
            uint64_t id;
            std::cin >> id;
            bool ok = book.cancelOrder(id);
            std::cout << (ok ? "OK" : "NOT_FOUND") << "\n";
        }
        else if (cmd == "snap") {
            auto bids = book.getBidsSnapshot();
            auto asks = book.getAsksSnapshot();
            
            std::cout << "BIDS:\n";
            for (const auto& l : bids) {
                std::cout << "  " << l.price << " : " << l.totalQty 
                          << " (" << l.numOrders << " orders)\n";
            }
            
            std::cout << "ASKS:\n";
            for (const auto& l : asks) {
                std::cout << "  " << l.price << " : " << l.totalQty 
                          << " (" << l.numOrders << " orders)\n";
            }
        }
        else {
            std::cout << "Unknown command\n";
        }
    }
    
    return 0;
}

