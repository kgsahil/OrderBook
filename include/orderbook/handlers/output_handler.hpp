#pragma once

#include "orderbook/events/event_types.hpp"
#include "orderbook/queue/spsc_queue.hpp"
#include <memory>
#include <functional>

namespace ob::handlers {

// Output handler for consuming events from the queue
// Single Responsibility: Handle event output
class OutputHandler {
public:
    using EventCallback = std::function<void(const events::Event&)>;

    explicit OutputHandler(
        std::shared_ptr<queue::SpscRingBuffer<events::Event>> eventQueue,
        EventCallback callback = nullptr
    ) : eventQueue_(std::move(eventQueue)), callback_(std::move(callback)) {}

    // Process available events (non-blocking)
    void processEvents() {
        if (!eventQueue_) return;
        
        events::Event event;
        while (eventQueue_->tryPop(event)) {
            if (callback_) {
                callback_(event);
            }
        }
    }

    bool hasEvents() const {
        return eventQueue_ && !eventQueue_->empty();
    }

    void setCallback(EventCallback callback) {
        callback_ = std::move(callback);
    }

private:
    std::shared_ptr<queue::SpscRingBuffer<events::Event>> eventQueue_;
    EventCallback callback_;
};

} // namespace ob::handlers

