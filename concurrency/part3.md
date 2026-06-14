## 2. CSP (Communicating Sequential Processes)

### 2.1 Canais para Comunicação

CSP (Communicating Sequential Processes), formalizado por Tony Hoare em 1978, baseia-se na ideia de processos sequenciais que comunicam-se através de **canais**. Diferente do Actor Model onde a identidade do receptor é explícita, em CSP a comunicação ocorre através de canais compartilhados.

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>
#include <optional>
#include <chrono>
#include <thread>

template<typename T>
class Channel {
private:
    std::queue<T> buffer_;
    std::mutex mutex_;
    std::condition_variable cv_not_empty_;
    std::condition_variable cv_not_full_;
    size_t capacity_;
    bool closed_ = false;
    
public:
    explicit Channel(size_t cap = 0) : capacity_(cap) {}
    
    bool send(T value) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (closed_) return false;
        
        if (capacity_ > 0) {
            cv_not_full_.wait(lock, [this] { 
                return buffer_.size() < capacity_ || closed_; 
            });
            if (closed_) return false;
        }
        
        buffer_.push(std::move(value));
        cv_not_empty_.notify_one();
        return true;
    }
    
    std::optional<T> receive() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_not_empty_.wait(lock, [this] { 
            return !buffer_.empty() || closed_; 
        });
        
        if (buffer_.empty() && closed_) return std::nullopt;
        
        T value = std::move(buffer_.front());
        buffer_.pop();
        cv_not_full_.notify_one();
        return value;
    }
    
    bool try_send(T value) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (closed_ || (capacity_ > 0 && buffer_.size() >= capacity_)) return false;
        buffer_.push(std::move(value));
        cv_not_empty_.notify_one();
        return true;
    }
    
    std::optional<T> try_receive() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (buffer_.empty()) return std::nullopt;
        T value = std::move(buffer_.front());
        buffer_.pop();
        cv_not_full_.notify_one();
        return value;
    }
    
    void close() {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
        cv_not_empty_.notify_all();
        cv_not_full_.notify_all();
    }
    
    bool is_closed() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return closed_;
    }
    
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return buffer_.size();
    }
};
```

### 2.2 Select / Multiplexação

O `select` permite aguardar múltiplos canais simultaneamente, processando o primeiro que estiver pronto. Isso é fundamental para implementar servidores concorrentes e timeouts.

```cpp
#include <vector>
#include <variant>
#include <memory>

template<typename... Channels>
class Select {
    using ChannelVariant = std::variant<Channels*...>;
    std::vector<ChannelVariant> channels_;
    
public:
    template<typename Channel>
    void add(Channel* ch) {
        channels_.push_back(ch);
    }
    
    template<typename Fn>
    bool wait(Fn&& handler) {
        while (true) {
            for (auto& ch_variant : channels_) {
                std::visit([&](auto* ch) {
                    using ChType = std::decay_t<decltype(*ch)>;
                    if (auto val = ch->try_receive(); val.has_value()) {
                        handler(std::move(*val));
                        return true;
                    }
                }, ch_variant);
            }
            std::this_thread::yield();
        }
        return false;
    }
    
    template<typename Fn, typename Rep, typename Period>
    bool wait_for(std::chrono::duration<Rep, Period> timeout, Fn&& handler) {
        auto deadline = std::chrono::steady_clock::now() + timeout;
        while (std::chrono::steady_clock::now() < deadline) {
            for (auto& ch_variant : channels_) {
                std::visit([&](auto* ch) {
                    if (auto val = ch->try_receive(); val.has_value()) {
                        handler(std::move(*val));
                        return true;
                    }
                }, ch_variant);
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        return false;
    }
};
```

### 2.3 Canais Estilo Go em C++

Implementação de canais com semântica similar ao Go, incluindo `select` com `default` case e canais direcionados.

```cpp
#include <coroutine>
#include <optional>

template<typename T>
class GoChannel {
private:
    struct Promise;
    using CoroHandle = std::coroutine_handle<Promise>;
    
    struct Promise {
        std::optional<T> value_;
        CoroHandle sender_ = nullptr;
        CoroHandle receiver_ = nullptr;
        bool closed_ = false;
        
        auto get_return_object() { return CoroHandle::from_promise(*this); }
        auto initial_suspend() { return std::suspend_always{}; }
        auto final_suspend() noexcept { return std::suspend_always{}; }
        void unhandled_exception() { std::terminate(); }
        void return_void() {}
        
        auto yield_value(T val) {
            value_ = std::move(val);
            if (receiver_) receiver_.resume();
            return std::suspend_always{};
        }
        
        auto await_transform(ChannelAwaiter<T> awaiter) {
            return awaiter;
        }
    };
    
    CoroHandle coro_;
    
public:
    GoChannel() : coro_(Promise::get_return_object()) {}
    ~GoChannel() { if (coro_) coro_.destroy(); }
    
    bool send(T value) {
        if (!coro_ || coro_.promise().closed_) return false;
        coro_.promise().value_ = std::move(value);
        coro_.resume();
        return true;
    }
    
    std::optional<T> receive() {
        if (!coro_ || coro_.promise().closed_) return std::nullopt;
        coro_.resume();
        auto val = std::move(coro_.promise().value_);
        coro_.promise().value_.reset();
        return val;
    }
    
    void close() { if (coro_) coro_.promise().closed_ = true; }
};

template<typename T>
struct ChannelAwaiter {
    GoChannel<T>* ch_;
    bool await_ready() const noexcept { return false; }
    void await_suspend(std::coroutine_handle<> h) noexcept {
        ch_->coro_.promise().receiver_ = h;
    }
    T await_resume() noexcept {
        return std::move(*ch_->coro_.promise().value_);
    }
};
```

### 2.4 Bibliotecas: libmill, libdill, cppcoro

**libmill** (C): Implementação de Go-style coroutines e canais em C puro.
```c
// libmill example
chan ch = chmake(sizeof(int), 0);
go(sender(ch));
go(receiver(ch));
```

**libdill** (C): Focado em concorrência estruturada e cancelamento.
```c
// libdill example
int ch = chmake(sizeof(int), 0);
bundle b = bundle_new();
bundle_go(b, sender(ch));
bundle_go(b, receiver(ch));
bundle_wait(b, -1);
```

**cppcoro** (C++20): Corrotinas nativas com canais, generators e sync primitives.
```cpp
#include <cppcoro/sync_wait.hpp>
#include <cppcoro/channel.hpp>
#include <cppcoro/task.hpp>

cppcoro::task<> sender(cppcoro::channel<int>& ch) {
    for (int i = 0; i < 10; ++i) {
        co_await ch.write(i);
    }
    ch.close();
}

cppcoro::task<> receiver(cppcoro::channel<int>& ch) {
    for (auto val : ch) {
        std::cout << "Received: " << val << std::endl;
    }
}

void cppcoro_example() {
    cppcoro::channel<int> ch(10);
    cppcoro::sync_wait(cppcoro::when_all(sender(ch), receiver(ch)));
}
```

### 2.5 CSP vs Actor Model

| Característica | Actor Model | CSP |
|----------------|-------------|-----|
| Identidade do receptor | Explícita (endereço do ator) | Implícita (canal compartilhado) |
| Tipagem de mensagens | Por ator (polimórfico) | Por canal (homogêneo) |
| Buffer | Mailbox por ator | Buffer no canal |
| Seleção | Pattern matching no ator | `select` em canais |
| Falha | Supervisão hierárquica | Cancelamento estruturado |
| Exemplos | Erlang, Akka, CAF | Go, Occam, libmill |

**Quando usar CSP**: Pipelines de dados, sistemas baseados em streams, quando a topologia de comunicação é dinâmica.

**Quando usar Actor Model**: Sistemas com estado encapsulado, hierarquias de supervisão claras, domínios orientados a objetos.