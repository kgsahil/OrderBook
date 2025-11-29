#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <type_traits>
#include <new>
#include <cassert>

namespace ob::queue {

// A bounded SPSC ring buffer with power-of-two capacity.
// Lock-free for single producer and single consumer with relaxed atomics.
template <typename T>
class alignas(64) SpscRingBuffer final {
public:
    explicit SpscRingBuffer(std::size_t capacityPowerOfTwo)
        : capacity_(normalizeCapacity(capacityPowerOfTwo)), mask_(capacity_ - 1), buffer_(nullptr)
    {
        buffer_ = static_cast<Node*>(::operator new[](sizeof(Node) * capacity_, std::align_val_t{alignof(Node)}));
        for (std::size_t i = 0; i < capacity_; ++i) {
            ::new (&buffer_[i]) Node();
        }
    }

    SpscRingBuffer(const SpscRingBuffer&) = delete;
    SpscRingBuffer& operator=(const SpscRingBuffer&) = delete;

    ~SpscRingBuffer() noexcept {
        // Destroy any constructed elements
        // Producer/consumer must be stopped before destruction
        for (std::size_t i = head_.load(std::memory_order_relaxed); i != tail_.load(std::memory_order_relaxed); i = (i + 1) & mask_) {
            buffer_[i].destroy();
        }
        for (std::size_t i = 0; i < capacity_; ++i) {
            buffer_[i].~Node();
        }
        ::operator delete[](buffer_, std::align_val_t{alignof(Node)});
    }

    [[nodiscard]] bool tryPush(const T& value) noexcept(std::is_nothrow_copy_constructible_v<T>) {
        const std::size_t head = head_.load(std::memory_order_relaxed);
        const std::size_t next = (head + 1) & mask_;
        if (next == tail_.load(std::memory_order_acquire)) return false; // full
        buffer_[head].construct(value);
        head_.store(next, std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool tryPush(T&& value) noexcept(std::is_nothrow_move_constructible_v<T>) {
        const std::size_t head = head_.load(std::memory_order_relaxed);
        const std::size_t next = (head + 1) & mask_;
        if (next == tail_.load(std::memory_order_acquire)) return false;
        buffer_[head].construct(std::move(value));
        head_.store(next, std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool tryPop(T& out) noexcept(std::is_nothrow_move_assignable_v<T>) {
        const std::size_t tail = tail_.load(std::memory_order_relaxed);
        if (tail == head_.load(std::memory_order_acquire)) return false; // empty
        out = std::move(buffer_[tail].value);
        buffer_[tail].destroy();
        tail_.store((tail + 1) & mask_, std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool empty() const noexcept { return head_.load(std::memory_order_acquire) == tail_.load(std::memory_order_acquire); }
    [[nodiscard]] bool full() const noexcept { return ((head_.load(std::memory_order_acquire) + 1) & mask_) == tail_.load(std::memory_order_acquire); }
    [[nodiscard]] std::size_t capacity() const noexcept { return capacity_ - 1; }

private:
    struct Node {
        alignas(T) unsigned char storage[sizeof(T)];
        bool constructed{false};
        T& value = *reinterpret_cast<T*>(storage);
        template <typename... Args>
        void construct(Args&&... args) noexcept(std::is_nothrow_constructible_v<T, Args...>) {
            assert(!constructed);
            ::new (storage) T(std::forward<Args>(args)...);
            constructed = true;
        }
        void destroy() noexcept {
            if (constructed) {
                value.~T();
                constructed = false;
            }
        }
    };

    static std::size_t normalizeCapacity(std::size_t n) noexcept {
        if (n < 2) n = 2;
        // round up to power of two
        std::size_t p = 1;
        while (p < n) p <<= 1;
        return p;
    }

    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
    const std::size_t capacity_;
    const std::size_t mask_;
    Node* buffer_;
};

} // namespace ob::queue

