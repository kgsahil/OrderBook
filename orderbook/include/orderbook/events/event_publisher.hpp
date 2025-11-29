#pragma once

#include "orderbook/events/event_types.hpp"
#include "orderbook/queue/spsc_queue.hpp"
#include <memory>

namespace ob::events {

// Interface for event publishing (Dependency Inversion Principle)
class IEventPublisher {
public:
    virtual ~IEventPublisher() = default;
    virtual bool publish(const Event& event) = 0;
    virtual bool publish(Event&& event) = 0;
};

// SPSC-based event publisher (lock-free)
class SpscEventPublisher final : public IEventPublisher {
public:
    explicit SpscEventPublisher(std::shared_ptr<queue::SpscRingBuffer<Event>> eventQueue)
        : eventQueue_(std::move(eventQueue)) {}

    bool publish(const Event& event) override {
        return eventQueue_ && eventQueue_->tryPush(event);
    }

    bool publish(Event&& event) override {
        return eventQueue_ && eventQueue_->tryPush(std::move(event));
    }

private:
    std::shared_ptr<queue::SpscRingBuffer<Event>> eventQueue_;
};

} // namespace ob::events

