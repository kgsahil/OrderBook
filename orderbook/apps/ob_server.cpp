#include "orderbook/oms/i_order_book_service.hpp"
#include "orderbook/oms/instrument_manager.hpp"
#include "orderbook/core/types.hpp"
#include <iostream>
#include <string>
#include <sstream>
#include <limits>
#include <chrono>
#include <thread>
#include <atomic>
#include <cstring>
#include <algorithm>
#include <vector>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

using namespace ob;

/**
 * TCP server for the orderbook.
 * 
 * Uses dependency injection via IOrderBookService interface, enabling:
 * - Testability (can inject mock service)
 * - Swappable implementations
 * - Follows Dependency Inversion Principle (SOLID)
 */
class OrderBookServer {
public:
    /**
     * Constructor with dependency injection.
     * 
     * @param port TCP port to listen on
     * @param service OrderBook service implementation (defaults to InstrumentManager)
     */
    explicit OrderBookServer(
        int port,
        std::unique_ptr<oms::IOrderBookService> service = nullptr
    ) : port_(port), running_(false) {
        // Use provided service or create default implementation
        if (service) {
            service_ = std::move(service);
        } else {
            service_ = std::make_unique<oms::InstrumentManager>();
        }
        
        // Set up event callback
        service_->setEventCallback([this](const events::Event& event) {
            handleEvent(event);
        });
        
        service_->start();
        nextOrderId_ = 1;
    }
    
    ~OrderBookServer() {
        stop();
        if (service_) {
            service_->stop();
        }
    }
    
    void start() {
        serverSocket_ = socket(AF_INET, SOCK_STREAM, 0);
        if (serverSocket_ < 0) {
            throw std::runtime_error("Failed to create socket");
        }
        
        int opt = 1;
        setsockopt(serverSocket_, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
        
        sockaddr_in serverAddr{};
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_addr.s_addr = INADDR_ANY;
        serverAddr.sin_port = htons(port_);
        
        if (bind(serverSocket_, (sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
            close(serverSocket_);
            throw std::runtime_error("Failed to bind socket");
        }
        
        if (listen(serverSocket_, 5) < 0) {
            close(serverSocket_);
            throw std::runtime_error("Failed to listen on socket");
        }
        
        running_ = true;
        std::cout << "OrderBook Server listening on port " << port_ << std::endl;
        
        while (running_) {
            sockaddr_in clientAddr{};
            socklen_t clientLen = sizeof(clientAddr);
            int clientSocket = accept(serverSocket_, (sockaddr*)&clientAddr, &clientLen);
            
            if (clientSocket < 0) {
                if (running_) {
                    std::cerr << "Failed to accept connection" << std::endl;
                }
                continue;
            }
            
            std::cout << "Client connected" << std::endl;
            std::thread(&OrderBookServer::handleClient, this, clientSocket).detach();
        }
    }
    
    void stop() {
        running_ = false;
        if (serverSocket_ >= 0) {
            close(serverSocket_);
            serverSocket_ = -1;
        }
    }
    
private:
    void handleClient(int clientSocket) {
        char buffer[4096];
        
        while (running_) {
            memset(buffer, 0, sizeof(buffer));
            int bytesRead = recv(clientSocket, buffer, sizeof(buffer) - 1, 0);
            
            if (bytesRead <= 0) {
                break;
            }
            
            std::string request(buffer, bytesRead);
            std::string response = processRequest(request);
            
            // Process any pending events
            if (service_) {
                service_->processEvents();
            }
            
            send(clientSocket, response.c_str(), response.length(), 0);
        }
        
        std::cout << "Client disconnected" << std::endl;
        close(clientSocket);
    }
    
    static std::string trim(const std::string& input) {
        const auto start = input.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) {
            return "";
        }
        const auto end = input.find_last_not_of(" \t\r\n");
        return input.substr(start, end - start + 1);
    }
    
    std::string processRequest(const std::string& request) {
        std::istringstream iss(request);
        std::string cmd;
        iss >> cmd;
        
        if (cmd == "ADD_INSTRUMENT") {
            std::string payload;
            std::getline(iss, payload);
            payload = trim(payload);
            
            std::vector<std::string> parts;
            std::stringstream payloadStream(payload);
            std::string part;
            while (std::getline(payloadStream, part, '|')) {
                parts.push_back(trim(part));
            }
            
            if (parts.size() < 4) {
                return "ERROR Invalid instrument payload\n";
            }
            
            const std::string& ticker = parts[0];
            const std::string& description = parts[1];
            const std::string& industry = parts[2];
            double initialPrice = 0.0;
            try {
                initialPrice = std::stod(parts[3]);
            } catch (...) {
                return "ERROR Invalid initial price\n";
            }
            
            if (ticker.empty() || initialPrice <= 0.0) {
                return "ERROR Invalid ticker\n";
            }
            
            std::uint32_t symbolId = service_->addInstrument(ticker, description, industry, initialPrice);
            return "OK " + std::to_string(symbolId) + "\n";
            
        } else if (cmd == "REMOVE_INSTRUMENT") {
            std::uint32_t symbolId;
            iss >> symbolId;
            bool ok = service_->removeInstrument(symbolId);
            return ok ? "OK\n" : "ERROR Instrument not found\n";
            
        } else if (cmd == "LIST_INSTRUMENTS") {
            std::ostringstream oss;
            auto instruments = service_->listInstruments();
            oss << "INSTRUMENTS " << instruments.size() << "\n";
            for (const auto& inst : instruments) {
                oss << inst.symbolId << "|" << inst.ticker << "|" 
                    << inst.description << "|" << inst.industry << "|" << inst.initialPrice << "\n";
            }
            oss << "END\n";
            return oss.str();
            
        } else if (cmd == "ADD") {
            std::uint32_t symbolId;
            char sideChar, typeChar;
            long long price = 0;
            long long qty;
            iss >> symbolId >> sideChar >> typeChar >> price >> qty;
            
            if (!service_->hasInstrument(symbolId)) {
                return "ERROR Instrument not found\n";
            }
            
            core::Side s = (sideChar == 'B' ? core::Side::Buy : core::Side::Sell);
            core::OrderType t = (typeChar == 'L' ? core::OrderType::Limit : core::OrderType::Market);
            
            // Validate LIMIT order price must be positive
            if (t == core::OrderType::Limit && price <= 0) {
                return "ERROR Invalid price for LIMIT order (must be > 0)\n";
            }
            
            // Validate quantity must be positive
            if (qty <= 0) {
                return "ERROR Invalid quantity (must be > 0)\n";
            }
            
            if (t == core::OrderType::Market) {
                price = (s == core::Side::Buy 
                    ? std::numeric_limits<long long>::max() 
                    : std::numeric_limits<long long>::min());
            }
            
            auto now = std::chrono::steady_clock::now();
            auto nowNs = std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch());
            
            core::OrderId orderId = nextOrderId_++;
            core::Order o{
                orderId, 
                symbolId, 
                s, 
                t, 
                static_cast<core::Price>(price), 
                static_cast<core::Quantity>(qty),
                core::Timestamp{nowNs}
            };
            
            bool submitted = service_->submitOrder(std::move(o));
            if (!submitted) {
                return "ERROR Failed to submit order (queue full or validation failed)\n";
            }
            return "OK " + std::to_string(orderId) + "\n";
            
        } else if (cmd == "CANCEL") {
            std::uint32_t symbolId;
            unsigned long long orderId;
            iss >> symbolId >> orderId;
            bool ok = service_->cancelOrder(symbolId, orderId);
            return ok ? "OK\n" : "NOTFOUND\n";
            
        } else if (cmd == "SNAPSHOT") {
            std::uint32_t symbolId;
            iss >> symbolId;
            
            if (!service_->hasInstrument(symbolId)) {
                return "ERROR Instrument not found\n";
            }
            
            std::ostringstream oss;
            auto bids = service_->getBidsSnapshot(symbolId, 10);
            auto asks = service_->getAsksSnapshot(symbolId, 10);
            
            oss << "SNAPSHOT " << symbolId << "\n";
            oss << "BIDS " << bids.size() << "\n";
            for (const auto& l : bids) {
                oss << l.price << " " << l.total << " " << l.numOrders << "\n";
            }
            oss << "ASKS " << asks.size() << "\n";
            for (const auto& l : asks) {
                oss << l.price << " " << l.total << " " << l.numOrders << "\n";
            }
            oss << "END\n";
            return oss.str();
            
        } else {
            return "ERROR Unknown command\n";
        }
    }
    
    void handleEvent(const events::Event& event) {
        // Events will be polled by clients via SNAPSHOT for now
        // Could extend to push events via separate connection
        switch (event.type) {
            case events::EventType::Ack:
                std::cout << "ACK: " << event.orderId << std::endl;
                break;
            case events::EventType::Trade:
                if (event.trade) {
                    std::cout << "TRADE: maker=" << event.trade->makerId 
                              << " taker=" << event.trade->takerId
                              << " price=" << event.trade->price
                              << " qty=" << event.trade->quantity << std::endl;
                }
                break;
            case events::EventType::CancelAck:
                std::cout << "CANCEL_ACK: " << event.orderId << std::endl;
                break;
            default:
                break;
        }
    }
    
    int port_;
    int serverSocket_{-1};
    std::atomic<bool> running_;
    std::unique_ptr<oms::IOrderBookService> service_;  // Dependency injection via interface
    std::atomic<core::OrderId> nextOrderId_{1};
};

int main() {
    try {
        OrderBookServer server(9999);
        std::cout << "Starting OrderBook TCP Server on port 9999..." << std::endl;
        server.start();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}

