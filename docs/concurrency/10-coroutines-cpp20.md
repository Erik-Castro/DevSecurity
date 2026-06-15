# Capítulo 10 — Coroutines C++20 para Concorrência

## Objetivos de Aprendizado

1. Compreender os fundamentos das coroutines C++20 e como elas diferem de threads
2. Implementar tipos básicos de coroutine: Generator, Task e Awaitable
3. Criar awaitables personalizados para operações assíncronas
4. Aplicar padrões de concorrência estruturada com coroutines
5. Diagnosticar e prevenir bugs comuns de lifetime em coroutines

---

## 1. Fundamentos das Coroutines

### 1.1 O que são Coroutines

Coroutines são funções que podem suspender sua execução e retomar posteriormente, mantendo seu estado local entre suspensões. Diferente de threads, coroutines são **stackless** — o estado é armazenado em um *coroutine frame* alocado no heap.

```cpp
#include <coroutine>
#include <iostream>
#include <vector>

struct Generator {
    struct promise_type {
        int current_value;
        
        Generator get_return_object() {
            return Generator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        
        std::suspend_always yield_value(int value) {
            current_value = value;
            return {};
        }
        
        void return_void() {}
        void unhandled_exception() { std::terminate(); }
    };
    
    std::coroutine_handle<promise_type> handle;
    
    bool move_next() {
        if (handle.done()) return false;
        handle.resume();
        return !handle.done();
    }
    
    int current_value() const { return handle.promise().current_value; }
    
    ~Generator() { if (handle) handle.destroy(); }
    
    Generator(Generator&& other) noexcept : handle(other.handle) { other.handle = nullptr; }
    Generator& operator=(Generator&& other) noexcept {
        if (this != &other) {
            if (handle) handle.destroy();
            handle = other.handle;
            other.handle = nullptr;
        }
        return *this;
    }
    Generator(const Generator&) = delete;
    Generator& operator=(const Generator&) = delete;
};

Generator fibonacci() {
    int a = 0, b = 1;
    while (true) {
        co_yield a;
        auto temp = a + b;
        a = b;
        b = temp;
    }
}

int main() {
    auto gen = fibonacci();
    for (int i = 0; i < 10; ++i) {
        gen.move_next();
        std::cout << gen.current_value() << " ";
    }
    std::cout << "\n";  // 0 1 1 2 3 5 8 13 21 34
    return 0;
}
```

### 1.2 co_await, co_yield, co_return

```cpp
#include <coroutine>
#include <iostream>
#include <string>

struct AlwaysSuspend {
    bool await_ready() noexcept { return false; }
    void await_suspend(std::coroutine_handle<>) noexcept {}
    void await_resume() noexcept {}
};

struct Task {
    struct promise_type {
        std::string result;
        
        Task get_return_object() {
            return Task{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        
        void return_value(std::string value) { result = std::move(value); }
        void unhandled_exception() { std::terminate(); }
    };
    
    std::coroutine_handle<promise_type> handle;
    
    std::string get() {
        if (!handle.done()) handle.resume();
        return std::move(handle.promise().result);
    }
    
    ~Task() { if (handle) handle.destroy(); }
};

Task compute() {
    co_return "Hello from coroutine";
}

int main() {
    auto task = compute();
    std::cout << task.get() << "\n";
    return 0;
}
```

---

## 2. Generator com Range-Based For

```cpp
#include <coroutine>
#include <iostream>
#include <optional>

template<typename T>
struct AsyncGenerator {
    struct promise_type {
        std::optional<T> current_value;
        std::exception_ptr exception;
        
        AsyncGenerator get_return_object() {
            return AsyncGenerator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        
        std::suspend_always yield_value(T value) {
            current_value = std::move(value);
            return {};
        }
        
        void return_void() {}
        void unhandled_exception() { exception = std::current_exception(); }
    };
    
    std::coroutine_handle<promise_type> handle;
    
    struct Iterator {
        std::coroutine_handle<promise_type> handle;
        void operator++() { handle.resume(); }
        const T& operator*() const { return *handle.promise().current_value; }
        bool operator!=(const Iterator& other) const { return handle != other.handle; }
    };
    
    Iterator begin() { handle.resume(); return {handle}; }
    Iterator end() { return {nullptr}; }
    
    ~AsyncGenerator() { if (handle) handle.destroy(); }
};

AsyncGenerator<int> range(int start, int end) {
    for (int i = start; i < end; ++i) co_yield i;
}

int main() {
    for (auto n : range(0, 10)) std::cout << n << " ";
    std::cout << "\n";
    return 0;
}
```

---

## 3. Task com Continuations

```cpp
#include <coroutine>
#include <functional>
#include <optional>
#include <exception>

template<typename T = void>
class Task {
public:
    struct promise_type {
        std::optional<T> result;
        std::exception_ptr exception;
        std::coroutine_handle<> continuation = nullptr;
        
        Task get_return_object() {
            return Task{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        
        struct FinalAwaiter {
            bool await_ready() noexcept { return false; }
            void await_suspend(std::coroutine_handle<promise_type> h) noexcept {
                if (h.promise().continuation) h.promise().continuation.resume();
            }
            void await_resume() noexcept {}
        };
        
        FinalAwaiter final_suspend() noexcept { return {}; }
        void return_value(T value) { result = std::move(value); }
        void unhandled_exception() { exception = std::current_exception(); }
    };
    
    std::coroutine_handle<promise_type> handle;
    
    Task(std::coroutine_handle<promise_type> h) : handle(h) {}
    ~Task() { if (handle) handle.destroy(); }
    Task(Task&& other) noexcept : handle(other.handle) { other.handle = nullptr; }
    
    bool await_ready() const noexcept { return !handle || handle.done(); }
    
    void await_suspend(std::coroutine_handle<> caller) noexcept {
        handle.promise().continuation = caller;
        handle.resume();
    }
    
    T await_resume() {
        if (handle.promise().exception) std::rethrow_exception(handle.promise().exception);
        return std::move(*handle.promise().result);
    }
    
    T get() {
        if (!handle.done()) handle.resume();
        if (handle.promise().exception) std::rethrow_exception(handle.promise().exception);
        return std::move(*handle.promise().result);
    }
};

Task<int> async_add(int a, int b) { co_return a + b; }

Task<int> async_compose() {
    int x = co_await async_add(10, 20);
    int y = co_await async_add(x, 5);
    co_return y;
}

int main() {
    std::cout << async_compose().get() << "\n";  // 35
    return 0;
}
```

---

## 4. Cancellation com Coroutines

```cpp
#include <coroutine>
#include <atomic>
#include <stdexcept>

class CancellationToken {
    std::atomic<bool> cancelled_{false};
public:
    void cancel() { cancelled_.store(true, std::memory_order_release); }
    bool is_cancelled() const { return cancelled_.load(std::memory_order_acquire); }
};

struct CancelledException : std::runtime_error {
    using std::runtime_error::runtime_error;
};

#define CHECK_CANCEL(token) \
    if ((token).is_cancelled()) throw CancelledException("Cancelled")

Task<int> cancellable_task(CancellationToken& token) {
    for (int i = 0; i < 1000000; ++i) {
        CHECK_CANCEL(token);
        volatile int x = i * i;
        (void)x;
        if (i % 1000 == 0) co_await std::suspend_always{};
    }
    co_return 42;
}

int main() {
    CancellationToken token;
    auto task = cancellable_task(token);
    for (int i = 0; i < 100; ++i) { if (task.await_ready()) break; }
    token.cancel();
    try {
        int result = task.get();
        std::cout << "Result: " << result << "\n";
    } catch (const CancelledException& e) {
        std::cout << "Cancelled: " << e.what() << "\n";
    }
    return 0;
}
```

---

## 5. Async Generator

```cpp
#include <coroutine>
#include <optional>
#include <iostream>

template<typename T>
class AsyncGenerator {
    struct promise_type {
        std::optional<T> current_value;
        std::coroutine_handle<> waiter = nullptr;
        
        AsyncGenerator get_return_object() {
            return AsyncGenerator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        std::suspend_always yield_value(T value) { current_value = std::move(value); return {}; }
        void return_void() {}
    };
    
    std::coroutine_handle<promise_type> handle;
    
public:
    AsyncGenerator(std::coroutine_handle<promise_type> h) : handle(h) {}
    ~AsyncGenerator() { if (handle) handle.destroy(); }
    
    bool next() {
        if (!handle || handle.done()) return false;
        handle.resume();
        return !handle.done();
    }
    
    T value() const { return *handle.promise().current_value; }
};

AsyncGenerator<int> async_range(int start, int end) {
    for (int i = start; i < end; ++i) co_yield i;
}

int main() {
    auto gen = async_range(0, 5);
    while (gen.next()) std::cout << gen.value() << " ";
    std::cout << "\n";
    return 0;
}
```

---

## 6. Referências

- **Lewis Baker** — "Coroutines C++" (lewissbaker.github.io)
- **Gor Nishanov** — C++ Coroutines proposal (wg21.link/p0057)
- **cppcoro library** — github.com/lewissbaker/cppcoro
- **C++20 Standard** — §9.5.4 (Coroutines)
