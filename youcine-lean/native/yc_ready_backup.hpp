#pragma once
#include <atomic>
#include <cstdlib>
#include <utility>

namespace lsplant {
// The entry patch can become visible before inline_hooker returns its backup.
// No reader accesses the pointer/member-pointer until the release publication.
template<class T> class YCReadyBackup {
public:
    using ValueType = T;
    void publish(T value) {
        target_ = std::move(value);
        state_.store(1, std::memory_order_release);
        state_.notify_all();
    }
    void fail() {
        state_.store(2, std::memory_order_release);
        state_.notify_all();
    }
    template<class... Args> decltype(auto) operator()(Args&&... args) {
        int state = state_.load(std::memory_order_acquire);
        while (state == 0) {
            state_.wait(0, std::memory_order_acquire);
            state = state_.load(std::memory_order_acquire);
        }
        // A callback after a failed backend installation cannot safely invoke
        // an invented original or return an arbitrary application value.
        if (state != 1) std::abort();
        return target_(std::forward<Args>(args)...);
    }
    explicit operator bool() {
        return state_.load(std::memory_order_acquire) == 1 && static_cast<bool>(target_);
    }
private:
    T target_{};
    std::atomic<int> state_{0};
};
}
