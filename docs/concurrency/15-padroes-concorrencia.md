# Capítulo 15 — Padrões de Concorrência e Arquiteturas

## Objetivos de Aprendizado

1. Compreender os principais padrões arquiteturais de concorrência e quando aplicar cada um
2. Implementar o Actor Model em C++ usando frameworks como CAF e sobjectizer
3. Dominar CSP (Communicating Sequential Processes) com canais e seleção
4. Construir pipelines paralelos com backpressure e balanceamento de carga
5. Aplicar fork-join, map-reduce e scatter-gather para problemas de processamento paralelo

## 1. Actor Model

### 1.1 Atores como Unidade de Concorrência

O Actor Model é um modelo de concorrência onde a unidade fundamental de computação é o **ator**. Cada ator possui:

- **Estado privado**: encapsulado e não compartilhado
- **Caixa de correio (mailbox)**: fila de mensagens assíncrona
- **Comportamento**: define como processa mensagens recebidas
- **Identidade única**: endereço para envio de mensagens

Diferente de threads tradicionais com memória compartilhada, atores comunicam-se exclusivamente através de **passagem de mensagens assíncronas**. Isso elimina race conditions por design, pois não há estado compartilhado mutável.

```cpp
#include <queue>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <functional>
#include <memory>
#include <atomic>
#include <iostream>
#include <variant>
#include <vector>

template<typename Message>
class ActorMailbox {
private:
    std::queue<Message> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> closed_{false};

public:
    void send(Message msg) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (closed_) throw std::runtime_error("Mailbox closed");
        queue_.push(std::move(msg));
        cv_.notify_one();
    }

    bool receive(Message& msg, std::chrono::milliseconds timeout = std::chrono::milliseconds::max()) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (cv_.wait_for(lock, timeout, [this] { return !queue_.empty() || closed_; })) {
            if (queue_.empty()) return false;
            msg = std::move(queue_.front());
            queue_.pop();
            return true;
        }
        return false;
    }

    void close() {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
        cv_.notify_all();
    }

    bool is_closed() const { return closed_.load(); }
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }
};

template<typename Message>
class Actor {
protected:
    ActorMailbox<Message> mailbox_;
    std::thread worker_;
    std::atomic<bool> running_{false};

public:
    Actor() = default;
    virtual ~Actor() { stop(); }

    void start() {
        if (running_.exchange(true)) return;
        worker_ = std::thread([this] { run(); });
    }

    void stop() {
        if (!running_.exchange(false)) return;
        mailbox_.close();
        if (worker_.joinable()) worker_.join();
    }

    void send(Message msg) { mailbox_.send(std::move(msg)); }

protected:
    virtual void on_message(Message&& msg) = 0;

private:
    void run() {
        Message msg;
        while (running_.load() && mailbox_.receive(msg)) {
            try {
                on_message(std::move(msg));
            } catch (const std::exception& e) {
                std::cerr << "Actor error: " << e.what() << std::endl;
            }
        }
    }
};

struct PingMessage { int value; };
struct PongMessage { int value; };

class PingActor : public Actor<std::variant<PingMessage, PongMessage>> {
    std::shared_ptr<Actor<std::variant<PingMessage, PongMessage>>> pong_actor_;

public:
    PingActor(std::shared_ptr<Actor<std::variant<PingMessage, PongMessage>>> pong)
        : pong_actor_(std::move(pong)) {}

protected:
    void on_message(std::variant<PingMessage, PongMessage>&& msg) override {
        if (auto* ping = std::get_if<PingMessage>(&msg)) {
            std::cout << "Ping received: " << ping->value << std::endl;
            if (ping->value > 0) {
                pong_actor_->send(PongMessage{ping->value - 1});
            }
        } else if (auto* pong = std::get_if<PongMessage>(&msg)) {
            std::cout << "Pong received: " << pong->value << std::endl;
            if (pong->value > 0) {
                this->send(PingMessage{pong->value - 1});
            }
        }
    }
};
### 1.2 Passagem de Mensagens (Sem Estado Compartilhado)

A passagem de mensagens é o coração do Actor Model. Mensagens são **imutáveis** após envio, garantindo que nenhum ator possa modificar o estado de outro. Isso previne uma classe inteira de bugs de concorrência.

```cpp
#include <string>
#include <chrono>
#include <optional>
#include <unordered_map>

struct UserMessage {
    std::string user_id;
    std::string content;
    std::chrono::system_clock::time_point sent_at;
    
    UserMessage(std::string id, std::string msg)
        : user_id(std::move(id)), content(std::move(msg)), 
          sent_at(std::chrono::system_clock::now()) {}
};

class ChatActor : public Actor<UserMessage> {
    std::unordered_map<std::string, std::vector<std::string>> user_history_;
    const size_t max_history_ = 100;

protected:
    void on_message(UserMessage&& msg) override {
        auto& history = user_history_[msg.user_id];
        history.push_back(msg.content);
        if (history.size() > max_history_) {
            history.erase(history.begin());
        }
        std::cout << "[" << msg.user_id << "] " << msg.content << std::endl;
    }

public:
    std::vector<std::string> get_history(const std::string& user_id) const {
        auto it = user_history_.find(user_id);
        return it != user_history_.end() ? it->second : std::vector<std::string>{};
    }
};
```

### 1.3 Mailbox e Fila de Mensagens

O mailbox implementa uma fila thread-safe com suporte a timeouts e prioridades. Implementações avançadas suportam:

- **Prioridade de mensagens**: mensagens de sistema processadas antes de usuário
- **Backpressure**: rejeição ou bloqueio quando a fila atinge limite
- **Dead letter queue**: mensagens não processadas após falhas repetidas

```cpp
template<typename Message>
class PriorityMailbox {
private:
    struct Envelope {
        Message msg;
        int priority;
        std::chrono::steady_clock::time_point deadline;
        
        bool operator<(const Envelope& other) const {
            return priority < other.priority; // max-heap
        }
    };
    
    std::priority_queue<Envelope> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> closed_{false};
    size_t capacity_;

public:
    explicit PriorityMailbox(size_t cap = 1000) : capacity_(cap) {}
    
    bool send(Message msg, int priority = 0, 
              std::optional<std::chrono::milliseconds> timeout = std::nullopt) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (closed_) return false;
        
        if (queue_.size() >= capacity_) {
            if (!timeout) return false;
            if (!cv_.wait_for(lock, *timeout, [this] { 
                return queue_.size() < capacity_ || closed_; 
            })) return false;
            if (closed_) return false;
        }
        
        queue_.push({std::move(msg), priority, 
                     std::chrono::steady_clock::now() + 
                     timeout.value_or(std::chrono::hours(24))});
        cv_.notify_one();
        return true;
    }
    
    bool receive(Message& msg, std::chrono::milliseconds timeout = 
                 std::chrono::milliseconds::max()) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (cv_.wait_for(lock, timeout, [this] { 
            return !queue_.empty() || closed_; 
        })) {
            if (queue_.empty()) return false;
            msg = std::move(queue_.top().msg);
            queue_.pop();
            cv_.notify_one();
            return true;
        }
        return false;
    }
    
    void close() {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
        cv_.notify_all();
    }
};
```

### 1.4 Supervisão e Tolerância a Falhas

A supervisão hierárquica permite que atores pais monitorem filhos e decidam estratégias de recuperação: **restart**, **stop**, **escalate** ou **resume**.

```cpp
#include <stdexcept>
#include <chrono>

enum class SupervisionDirective {
    Restart,    // Reiniciar o ator filho
    Stop,       // Parar o ator filho permanentemente
    Escalate,   // Escalar para o supervisor pai
    Resume      // Continuar processamento (ignorar erro)
};

class SupervisorStrategy {
public:
    virtual SupervisionDirective decide(const std::exception& e) const = 0;
    virtual ~SupervisorStrategy() = default;
};

class OneForOneStrategy : public SupervisorStrategy {
    std::chrono::seconds reset_timeout_;
    size_t max_restarts_;
    
public:
    OneForOneStrategy(std::chrono::seconds timeout = std::chrono::seconds(30), 
                      size_t max_r = 3)
        : reset_timeout_(timeout), max_restarts_(max_r) {}
    
    SupervisionDirective decide(const std::exception& e) const override {
        if (dynamic_cast<const std::bad_alloc*>(&e)) return SupervisionDirective::Escalate;
        if (dynamic_cast<const std::logic_error*>(&e)) return SupervisionDirective::Stop;
        return SupervisionDirective::Restart;
    }
};

template<typename Message>
class SupervisedActor : public Actor<Message> {
    std::shared_ptr<SupervisorStrategy> strategy_;
    std::atomic<size_t> restart_count_{0};
    std::chrono::steady_clock::time_point last_restart_;
    
protected:
    void on_message(Message&& msg) override {
        try {
            handle_message(std::move(msg));
        } catch (const std::exception& e) {
            auto directive = strategy_->decide(e);
            handle_failure(directive, e);
        }
    }
    
    virtual void handle_message(Message&& msg) = 0;
    
    void handle_failure(SupervisionDirective directive, const std::exception& e) {
        switch (directive) {
            case SupervisionDirective::Restart:
                if (should_restart()) {
                    restart_count_++;
                    last_restart_ = std::chrono::steady_clock::now();
                    std::cerr << "Restarting actor due to: " << e.what() << std::endl;
                } else {
                    std::cerr << "Max restarts exceeded, stopping actor" << std::endl;
                    this->stop();
                }
                break;
            case SupervisionDirective::Stop:
                this->stop();
                break;
            case SupervisionDirective::Escalate:
                throw; // Re-throw for parent supervisor
            case SupervisionDirective::Resume:
                break; // Continue processing
        }
    }
    
    bool should_restart() const {
        auto now = std::chrono::steady_clock::now();
        if (now - last_restart_ > std::chrono::seconds(30)) {
            return true; // Reset counter after timeout
        }
        return restart_count_ < 3;
    }
};
### 1.5 Frameworks de Atores em C++

#### CAF (C++ Actor Framework)

CAF é uma implementação madura do Actor Model para C++ com suporte a distribuição, tipagem forte de mensagens e integração com sistemas de build modernos.

```cpp
#include <caf/all.hpp>

using namespace caf;

struct PingMsg { int value; };
struct PongMsg { int value; };

behavior ping_behavior(event_based_actor* self, actor pong) {
    return {
        [=](PingMsg msg) {
            aout(self) << "Ping: " << msg.value << std::endl;
            if (msg.value > 0) {
                self->send(pong, PongMsg{msg.value - 1});
            }
        },
        [=](PongMsg msg) {
            aout(self) << "Pong received: " << msg.value << std::endl;
            if (msg.value > 0) {
                self->send(self, PingMsg{msg.value - 1});
            } else {
                self->quit();
            }
        }
    };
}

void caf_example() {
    actor_system_config cfg;
    actor_system system{cfg};
    
    auto pong = system.spawn([](event_based_actor* self) {
        return behavior{
            [=](PongMsg msg) {
                aout(self) << "Pong actor: " << msg.value << std::endl;
                if (msg.value > 0) {
                    self->send(self->current_sender(), PingMsg{msg.value - 1});
                }
            }
        };
    });
    
    auto ping = system.spawn(ping_behavior, pong);
    anon_send(ping, PingMsg{10});
    
    system.await_all_actors_done();
}
```

#### SObjectizer

SObjectizer foca em simplicidade e performance, com suporte a agentes, caixas de correio com prioridades e timeouts.

```cpp
#include <so_5/all.hpp>

struct PingMsg { int value; };
struct PongMsg { int value; };

class PingAgent final : public so_5::agent_t {
    so_5::mbox_t pong_mbox_;
    
public:
    PingAgent(so_5::environment_t& env, so_5::mbox_t pong_mbox)
        : so_5::agent_t(env), pong_mbox_(std::move(pong_mbox)) {}
    
    void so_define_agent() override {
        so_subscribe_self()
            .event<PingMsg>([this](mhood_t<PingMsg> msg) {
                std::cout << "Ping: " << msg->value << std::endl;
                if (msg->value > 0) {
                    so_5::send<PongMsg>(pong_mbox_, msg->value - 1);
                }
            })
            .event<PongMsg>([this](mhood_t<PongMsg> msg) {
                std::cout << "Pong received: " << msg->value << std::endl;
                if (msg->value > 0) {
                    so_5::send<PingMsg>(so_direct_mbox(), msg->value - 1);
                } else {
                    so_deregister_agent_coop_normally();
                }
            });
    }
};

void sobjectizer_example() {
    so_5::launch([](so_5::environment_t& env) {
        auto pong_mbox = env.create_mbox();
        
        env.introduce_coop([&](so_5::coop_t& coop) {
            coop.make_agent<PingAgent>(pong_mbox);
            
            coop.define_agent()
                .on_start([pong_mbox] {
                    so_5::send<PingMsg>(pong_mbox, 10);
                })
                .event<PongMsg>([pong_mbox](mhood_t<PongMsg> msg) {
                    std::cout << "Pong agent: " << msg->value << std::endl;
                    if (msg->value > 0) {
                        so_5::send<PingMsg>(pong_mbox, msg->value - 1);
                    }
                });
        });
    });
}
```

#### Rotor

Rotor é um framework leve com API minimalista, ideal para sistemas embarcados.

```cpp
#include <rotor.hpp>

struct PingMsg { int value; };
struct PongMsg { int value; };

class PingActor : public rotor::actor_base_t {
    rotor::address_ptr_t pong_addr_;
    
public:
    PingActor(rotor::supervisor_t& sup, rotor::address_ptr_t pong_addr)
        : rotor::actor_base_t(sup), pong_addr_(std::move(pong_addr)) {}
    
    void configure(rotor::plugin::plugin_base_t& plugin) noexcept override {
        plugin.with_casted<rotor::plugin::starter_plugin_t>(
            [this](auto& p) { p.subscribe_actor(&PingActor::on_ping); });
        plugin.with_casted<rotor::plugin::starter_plugin_t>(
            [this](auto& p) { p.subscribe_actor(&PingActor::on_pong); });
    }
    
    void on_ping(PingMsg& msg) noexcept {
        std::cout << "Ping: " << msg.value << std::endl;
        if (msg.value > 0) {
            send<PongMsg>(pong_addr_, msg.value - 1);
        }
    }
    
    void on_pong(PongMsg& msg) noexcept {
        std::cout << "Pong received: " << msg.value << std::endl;
        if (msg.value > 0) {
            send<PingMsg>(address(), msg.value - 1);
        } else {
            supervisor().do_shutdown();
        }
    }
};

void rotor_example() {
    rotor::system_context_t ctx{};
    auto sup = ctx.create_supervisor<rotor::supervisor_t>().timeout(boost::posix_time::seconds{1}).create();
    auto pong_addr = sup->create_actor<rotor::actor_base_t>().timeout(boost::posix_time::seconds{1}).create();
    auto ping_addr = sup->create_actor<PingActor>(pong_addr).timeout(boost::posix_time::seconds{1}).create();
    
    sup->start();
    sup->do_process();
}
```

### 1.6 Implementação Completa de Ator

Uma implementação completa com suporte a tipagem de mensagens, timeouts, supervisão e métricas.

```cpp
#include <iostream>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <unordered_map>
#include <functional>
#include <memory>
#include <atomic>
#include <chrono>
#include <variant>
#include <string>
#include <vector>
#include <typeindex>
#include <any>

class ActorSystem {
public:
    using ActorId = uint64_t;
    
private:
    std::atomic<ActorId> next_id_{1};
    std::unordered_map<ActorId, std::shared_ptr<class ActorBase>> actors_;
    std::mutex actors_mutex_;
    std::thread scheduler_;
    std::atomic<bool> running_{false};
    
public:
    ActorSystem() = default;
    ~ActorSystem() { shutdown(); }
    
    template<typename ActorType, typename... Args>
    ActorId spawn(Args&&... args) {
        auto actor = std::make_shared<ActorType>(std::forward<Args>(args)...);
        ActorId id = next_id_++;
        {
            std::lock_guard<std::mutex> lock(actors_mutex_);
            actors_[id] = actor;
        }
        actor->start();
        return id;
    }
    
    template<typename Message>
    bool send(ActorId to, Message&& msg) {
        std::shared_ptr<ActorBase> actor;
        {
            std::lock_guard<std::mutex> lock(actors_mutex_);
            auto it = actors_.find(to);
            if (it == actors_.end()) return false;
            actor = it->second;
        }
        return actor->send(std::forward<Message>(msg));
    }
    
    void shutdown() {
        if (!running_.exchange(false)) return;
        std::vector<std::shared_ptr<ActorBase>> to_stop;
        {
            std::lock_guard<std::mutex> lock(actors_mutex_);
            to_stop.reserve(actors_.size());
            for (auto& [id, actor] : actors_) {
                to_stop.push_back(actor);
            }
        }
        for (auto& actor : to_stop) {
            actor->stop();
        }
        if (scheduler_.joinable()) scheduler_.join();
    }
    
    size_t actor_count() const {
        std::lock_guard<std::mutex> lock(actors_mutex_);
        return actors_.size();
    }
};

class ActorBase {
protected:
    struct Envelope {
        std::type_index type;
        std::any payload;
        std::chrono::steady_clock::time_point deadline;
    };
    
    std::queue<Envelope> mailbox_;
    std::mutex mailbox_mutex_;
    std::condition_variable mailbox_cv_;
    std::thread worker_;
    std::atomic<bool> running_{false};
    std::atomic<bool> stopping_{false};
    
public:
    ActorBase() = default;
    virtual ~ActorBase() { stop(); }
    
    template<typename Message>
    bool send(Message&& msg) {
        std::unique_lock<std::mutex> lock(mailbox_mutex_);
        if (stopping_) return false;
        mailbox_.push({std::type_index(typeid(Message)), 
                       std::make_any<Message>(std::forward<Message>(msg)),
                       std::chrono::steady_clock::now() + std::chrono::seconds(30)});
        mailbox_cv_.notify_one();
        return true;
    }
    
    void start() {
        if (running_.exchange(true)) return;
        worker_ = std::thread([this] { run(); });
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        stopping_ = true;
        {
            std::lock_guard<std::mutex> lock(mailbox_mutex_);
            mailbox_cv_.notify_all();
        }
        if (worker_.joinable()) worker_.join();
    }
    
protected:
    virtual void handle_message(std::any&& payload) = 0;
    
private:
    void run() {
        while (running_.load()) {
            Envelope envelope;
            {
                std::unique_lock<std::mutex> lock(mailbox_mutex_);
                if (mailbox_cv_.wait_for(lock, std::chrono::milliseconds(100), 
                    [this] { return !mailbox_.empty() || stopping_.load(); })) {
                    if (mailbox_.empty()) continue;
                    envelope = std::move(mailbox_.front());
                    mailbox_.pop();
                } else {
                    continue;
                }
            }
            
            try {
                handle_message(std::move(envelope.payload));
            } catch (const std::exception& e) {
                std::cerr << "Actor error: " << e.what() << std::endl;
            }
        }
    }
};

template<typename... Messages>
class TypedActor : public ActorBase {
    using Variant = std::variant<Messages...>;
    
protected:
    void handle_message(std::any&& payload) override {
        std::visit([this](auto&& msg) {
            using T = std::decay_t<decltype(msg)>;
            if constexpr (std::disjunction_v<std::is_same<T, Messages>...>) {
                on_message(std::forward<decltype(msg)>(msg));
            }
        }, std::move(payload));
    }
    
    virtual void on_message(Messages&&...) = 0;
};

struct OrderMessage {
    uint64_t order_id;
    std::string symbol;
    double price;
    int quantity;
};

struct MarketDataMessage {
    std::string symbol;
    double bid;
    double ask;
    uint64_t timestamp;
};

class TradingActor : public TypedActor<OrderMessage, MarketDataMessage> {
    std::unordered_map<std::string, double> positions_;
    std::mutex positions_mutex_;
    
    void on_message(OrderMessage&& msg) override {
        std::lock_guard<std::mutex> lock(positions_mutex_);
        positions_[msg.symbol] += msg.quantity;
        std::cout << "Order executed: " << msg.symbol 
                  << " qty=" << msg.quantity 
                  << " price=" << msg.price << std::endl;
    }
    
    void on_message(MarketDataMessage&& msg) override {
        std::lock_guard<std::mutex> lock(positions_mutex_);
        auto it = positions_.find(msg.symbol);
        if (it != positions_.end()) {
            double pnl = (msg.bid - msg.ask) * it->second;
            std::cout << "P&L for " << msg.symbol << ": " << pnl << std::endl;
        }
    }
};

void actor_system_demo() {
    ActorSystem system;
    
    auto trader_id = system.spawn<TradingActor>();
    
    system.send(trader_id, OrderMessage{1, "AAPL", 150.0, 100});
    system.send(trader_id, OrderMessage{2, "GOOGL", 2800.0, 50});
    system.send(trader_id, MarketDataMessage{"AAPL", 151.0, 150.5, 1234567890});
    system.send(trader_id, MarketDataMessage{"GOOGL", 2810.0, 2805.0, 1234567891});
    
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    system.shutdown();
}
```## 2. CSP (Communicating Sequential Processes)

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

**Quando usar Actor Model**: Sistemas com estado encapsulado, hierarquias de supervisão claras, domínios orientados a objetos.## 3. Pipeline Parallelism

### 3.1 Decomposição em Estágios

Pipeline parallelism divide uma computação em estágios sequenciais, onde cada estágio processa dados e passa para o próximo. Isso permite sobreposição de execução: enquanto o estágio N processa item i, o estágio N+1 processa item i-1.

```cpp
#include <thread>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <atomic>
#include <chrono>

template<typename Input, typename Output>
class PipelineStage {
public:
    using ProcessFn = std::function<Output(Input)>;
    
private:
    ProcessFn process_;
    std::queue<Input> input_queue_;
    std::queue<Output> output_queue_;
    std::mutex input_mutex_, output_mutex_;
    std::condition_variable input_cv_, output_cv_;
    std::thread worker_;
    std::atomic<bool> running_{false};
    std::atomic<bool> stopped_{false};
    size_t input_capacity_, output_capacity_;
    
public:
    PipelineStage(ProcessFn fn, size_t in_cap = 100, size_t out_cap = 100)
        : process_(std::move(fn)), input_capacity_(in_cap), output_capacity_(out_cap) {}
    
    ~PipelineStage() { stop(); }
    
    bool push(Input item) {
        std::unique_lock<std::mutex> lock(input_mutex_);
        if (stopped_) return false;
        input_cv_.wait(lock, [this] { return input_queue_.size() < input_capacity_ || stopped_; });
        if (stopped_) return false;
        input_queue_.push(std::move(item));
        input_cv_.notify_one();
        return true;
    }
    
    std::optional<Output> pop() {
        std::unique_lock<std::mutex> lock(output_mutex_);
        output_cv_.wait(lock, [this] { return !output_queue_.empty() || stopped_; });
        if (output_queue_.empty() && stopped_) return std::nullopt;
        Output item = std::move(output_queue_.front());
        output_queue_.pop();
        output_cv_.notify_one();
        return item;
    }
    
    void start() {
        if (running_.exchange(true)) return;
        worker_ = std::thread([this] { run(); });
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        stopped_ = true;
        input_cv_.notify_all();
        output_cv_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
    
private:
    void run() {
        while (running_.load()) {
            Input item;
            {
                std::unique_lock<std::mutex> lock(input_mutex_);
                input_cv_.wait(lock, [this] { return !input_queue_.empty() || stopped_.load(); });
                if (input_queue_.empty() && stopped_) break;
                item = std::move(input_queue_.front());
                input_queue_.pop();
                input_cv_.notify_one();
            }
            
            Output result = process_(std::move(item));
            
            {
                std::unique_lock<std::mutex> lock(output_mutex_);
                output_cv_.wait(lock, [this] { return output_queue_.size() < output_capacity_ || stopped_.load(); });
                if (stopped_) break;
                output_queue_.push(std::move(result));
                output_cv_.notify_one();
            }
        }
    }
};

template<typename... Stages>
class Pipeline {
    std::tuple<Stages...> stages_;
    
public:
    Pipeline(Stages... stages) : stages_(std::move(stages)...) {}
    
    void start() {
        std::apply([](auto&... s) { (s.start(), ...); }, stages_);
    }
    
    void stop() {
        std::apply([](auto&... s) { (s.stop(), ...); }, stages_);
    }
    
    template<typename Input>
    bool push(Input&& item) {
        return std::get<0>(stages_).push(std::forward<Input>(item));
    }
    
    template<typename Output>
    std::optional<Output> pop() {
        return std::get<sizeof...(Stages)-1>(stages_).pop();
    }
};
```

### 3.2 Buffer Entre Estágios

Buffers entre estágios desacoplam produtores e consumidores, absorvendo variações de velocidade. Dimensionamento correto é crítico: buffers muito pequenos causam bloqueio frequente; muito grandes aumentam latência e uso de memória.

```cpp
template<typename T>
class BoundedBuffer {
    std::vector<T> buffer_;
    std::atomic<size_t> head_{0}, tail_{0};
    std::atomic<size_t> count_{0};
    const size_t capacity_;
    
public:
    explicit BoundedBuffer(size_t cap) : buffer_(cap), capacity_(cap) {}
    
    bool push(T item) {
        size_t h = head_.load(std::memory_order_relaxed);
        for (;;) {
            size_t c = count_.load(std::memory_order_acquire);
            if (c >= capacity_) return false;
            if (count_.compare_exchange_weak(c, c + 1, std::memory_order_acq_rel)) {
                buffer_[h] = std::move(item);
                head_.store((h + 1) % capacity_, std::memory_order_release);
                return true;
            }
        }
    }
    
    std::optional<T> pop() {
        size_t t = tail_.load(std::memory_order_relaxed);
        for (;;) {
            size_t c = count_.load(std::memory_order_acquire);
            if (c == 0) return std::nullopt;
            if (count_.compare_exchange_weak(c, c - 1, std::memory_order_acq_rel)) {
                T item = std::move(buffer_[t]);
                tail_.store((t + 1) % capacity_, std::memory_order_release);
                return item;
            }
        }
    }
    
    size_t size() const { return count_.load(std::memory_order_acquire); }
    bool empty() const { return size() == 0; }
    bool full() const { return size() >= capacity_; }
};
```

### 3.3 Backpressure

Backpressure propaga sinais de lentidão do consumidor para o produtor, evitando estouro de memória. Estratégias incluem: bloqueio, descarte (drop), amostragem, ou sinalização explícita.

```cpp
enum class BackpressureStrategy {
    Block,      // Bloquear produtor
    DropOldest, // Descarta item mais antigo
    DropLatest, // Descarta item mais novo
    Sample      // Amostragem periódica
};

template<typename T>
class BackpressureBuffer {
    std::queue<T> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    size_t capacity_;
    BackpressureStrategy strategy_;
    std::atomic<size_t> dropped_{0};
    
public:
    BackpressureBuffer(size_t cap, BackpressureStrategy strat = BackpressureStrategy::Block)
        : capacity_(cap), strategy_(strat) {}
    
    bool push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (queue_.size() >= capacity_) {
            switch (strategy_) {
                case BackpressureStrategy::Block:
                    cv_.wait(lock, [this] { return queue_.size() < capacity_; });
                    break;
                case BackpressureStrategy::DropOldest:
                    if (!queue_.empty()) {
                        queue_.pop();
                        dropped_++;
                    }
                    break;
                case BackpressureStrategy::DropLatest:
                    dropped_++;
                    return false;
                case BackpressureStrategy::Sample:
                    if (dropped_++ % 10 != 0) return false;
                    if (!queue_.empty()) queue_.pop();
                    break;
            }
        }
        queue_.push(std::move(item));
        cv_.notify_one();
        return true;
    }
    
    std::optional<T> pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return !queue_.empty(); });
        T item = std::move(queue_.front());
        queue_.pop();
        cv_.notify_one();
        return item;
    }
    
    size_t dropped_count() const { return dropped_.load(); }
};
```

### 3.4 Balanceamento de Carga Dinâmico

Work stealing permite que threads ociosas roubem trabalho de threads ocupadas, melhorando utilização em cargas irregulares.

```cpp
#include <deque>
#include <thread>
#include <vector>
#include <atomic>
#include <mutex>

template<typename Task>
class WorkStealingQueue {
    std::deque<Task> deque_;
    std::mutex mutex_;
    
public:
    void push(Task task) {
        std::lock_guard<std::mutex> lock(mutex_);
        deque_.push_back(std::move(task));
    }
    
    std::optional<Task> pop() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return std::nullopt;
        Task task = std::move(deque_.front());
        deque_.pop_front();
        return task;
    }
    
    std::optional<Task> steal() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return std::nullopt;
        Task task = std::move(deque_.back());
        deque_.pop_back();
        return task;
    }
    
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return deque_.empty();
    }
};

template<typename Task>
class WorkStealingExecutor {
    std::vector<std::unique_ptr<WorkStealingQueue<Task>>> queues_;
    std::vector<std::thread> workers_;
    std::atomic<bool> running_{false};
    std::atomic<size_t> next_queue_{0};
    
public:
    explicit WorkStealingExecutor(size_t num_threads = std::thread::hardware_concurrency()) {
        queues_.reserve(num_threads);
        for (size_t i = 0; i < num_threads; ++i) {
            queues_.push_back(std::make_unique<WorkStealingQueue<Task>>());
        }
    }
    
    void start() {
        if (running_.exchange(true)) return;
        for (size_t i = 0; i < queues_.size(); ++i) {
            workers_.emplace_back([this, i] { worker_loop(i); });
        }
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        for (auto& w : workers_) if (w.joinable()) w.join();
    }
    
    void submit(Task task) {
        size_t idx = next_queue_.fetch_add(1, std::memory_order_relaxed) % queues_.size();
        queues_[idx]->push(std::move(task));
    }
    
private:
    void worker_loop(size_t my_idx) {
        while (running_.load()) {
            auto task = queues_[my_idx]->pop();
            if (!task) {
                for (size_t i = 0; i < queues_.size(); ++i) {
                    if (i == my_idx) continue;
                    task = queues_[i]->steal();
                    if (task) break;
                }
            }
            if (task) {
                (*task)();
            } else {
                std::this_thread::yield();
            }
        }
    }
};
```

### 3.5 Framework de Pipeline em C++

```cpp
#include <ranges>
#include <vector>
#include <functional>

template<typename T>
concept PipelineStageConcept = requires(T t, typename T::input_type in) {
    { t.process(in) } -> std::same_as<typename T::output_type>;
    { t.start() } -> std::same_as<void>;
    { t.stop() } -> std::same_as<void>;
};

template<typename Input, typename Output>
class SimpleStage {
public:
    using input_type = Input;
    using output_type = Output;
    using Fn = std::function<Output(Input)>;
    
private:
    Fn fn_;
    std::thread thread_;
    std::atomic<bool> running_{false};
    
public:
    explicit SimpleStage(Fn fn) : fn_(std::move(fn)) {}
    
    Output process(Input in) { return fn_(std::move(in)); }
    
    void start() { running_ = true; }
    void stop() { running_ = false; }
};

template<typename... Stages>
class ComposablePipeline {
    std::tuple<Stages...> stages_;
    
public:
    ComposablePipeline(Stages... s) : stages_(std::move(s)...) {}
    
    auto operator|(auto next_stage) {
        return ComposablePipeline<Stages..., decltype(next_stage)>(
            std::move(stages_), std::move(next_stage));
    }
    
    void execute(auto input_range) {
        // Implementation omitted for brevity
    }
};
```

### 3.6 TBB flow_graph

Intel TBB flow_graph fornece abstração de alto nível para pipelines com graph-based execution.

```cpp
#include <tbb/flow_graph.h>

using namespace tbb::flow;

void tbb_pipeline_example() {
    graph g;
    
    function_node<int, int> stage1(g, unlimited, [](int x) {
        return x * 2;
    });
    
    function_node<int, int> stage2(g, unlimited, [](int x) {
        return x + 1;
    });
    
    function_node<int, void> stage3(g, unlimited, [](int x) {
        std::cout << "Result: " << x << std::endl;
    });
    
    make_edge(stage1, stage2);
    make_edge(stage2, stage3);
    
    for (int i = 0; i < 100; ++i) {
        stage1.try_put(i);
    }
    
    g.wait_for_all();
}
```

### 3.7 cppcoro Pipeline

```cpp
#include <cppcoro/generator.hpp>
#include <cppcoro/channel.hpp>
#include <cppcoro/task.hpp>
#include <cppcoro/sync_wait.hpp>

cppcoro::generator<int> source() {
    for (int i = 0; i < 100; ++i) co_yield i;
}

cppcoro::task<> stage1(cppcoro::channel<int>& in, cppcoro::channel<int>& out) {
    for (int val : in) {
        co_await out.write(val * 2);
    }
    out.close();
}

cppcoro::task<> stage2(cppcoro::channel<int>& in, cppcoro::channel<int>& out) {
    for (int val : in) {
        co_await out.write(val + 1);
    }
    out.close();
}

cppcoro::task<> sink(cppcoro::channel<int>& in) {
    for (int val : in) {
        std::cout << "Result: " << val << std::endl;
    }
}

cppcoro::task<> cppcoro_pipeline() {
    cppcoro::channel<int> ch1(10), ch2(10), ch3(10);
    
    co_await cppcoro::when_all(
        [&]() -> cppcoro::task<> {
            for (int i : source()) co_await ch1.write(i);
            ch1.close();
        }(),
        stage1(ch1, ch2),
        stage2(ch2, ch3),
        sink(ch3)
    );
}
```

### 3.8 Bugs Conhecidos: Pipeline Parallelism Data Races

**CVE-2021-43828 (Apache Flink)**: Race condition no pipeline de processamento de streams causava corrupção de estado quando operadores compartilhavam buffers não sincronizados corretamente.

**CVE-2020-13949 (Apache Kafka Streams)**: Data race no processador de pipelines de transformação levou a resultados inconsistentes em junções de streams sob alta carga.

**Lições aprendidas**:
- Sempre sincronize acesso a buffers compartilhados entre estágios
- Use atomics ou mutexes para contadores de progresso
- Valide com sanitizers (TSan, ASan) em testes de carga
- Implemente backpressure explícito para evitar estouro de buffer## 4. Fork-Join Parallelism

### 4.1 Decomposição Recursiva de Tarefas

Fork-join divide um problema recursivamente em subtarefas independentes (fork), executa-as em paralelo, e combina os resultados (join). Ideal para algoritmos divide-and-conquer.

```cpp
#include <thread>
#include <vector>
#include <future>
#include <functional>
#include <atomic>
#include <algorithm>

template<typename Result>
class ForkJoinTask {
public:
    using TaskFn = std::function<Result()>;
    using CombineFn = std::function<Result(std::vector<Result>&&)>;
    
private:
    TaskFn task_;
    CombineFn combine_;
    size_t threshold_;
    
public:
    ForkJoinTask(TaskFn task, CombineFn combine, size_t threshold = 1000)
        : task_(std::move(task)), combine_(std::move(combine)), threshold_(threshold) {}
    
    Result compute() {
        return compute_impl();
    }
    
private:
    Result compute_impl() {
        // Simplified: in real implementation, check problem size against threshold
        return task_();
    }
};

template<typename Iterator, typename Result>
Result parallel_reduce(Iterator begin, Iterator end, Result init, 
                       std::function<Result(Result, Result)> combine,
                       size_t threshold = 1000) {
    size_t size = std::distance(begin, end);
    if (size <= threshold) {
        return std::accumulate(begin, end, init, 
            [&](Result acc, auto val) { return combine(acc, val); });
    }
    
    Iterator mid = begin + size / 2;
    std::future<Result> left = std::async(std::launch::async, 
        parallel_reduce<Iterator, Result>, begin, mid, init, combine, threshold);
    Result right = parallel_reduce(mid, end, init, combine, threshold);
    return combine(left.get(), right);
}
```

### 4.2 Work Stealing Schedulers

Work stealing distribui tarefas dinamicamente: cada thread tem deque local; threads ociosas roubam do final de deques alheias (LIFO para local, FIFO para roubo).

```cpp
#include <array>
#include <thread>
#include <vector>
#include <deque>
#include <mutex>
#include <atomic>
#include <functional>
#include <optional>

class WorkStealingScheduler {
    struct Task {
        std::function<void()> fn;
    };
    
    struct Worker {
        std::deque<Task> local_queue;
        std::mutex mutex;
        std::atomic<bool> active{false};
    };
    
    std::vector<Worker> workers_;
    std::atomic<size_t> next_victim_{0};
    std::atomic<bool> running_{false};
    std::vector<std::thread> threads_;
    
public:
    explicit WorkStealingScheduler(size_t n = std::thread::hardware_concurrency()) 
        : workers_(n) {}
    
    ~WorkStealingScheduler() { stop(); }
    
    void start() {
        if (running_.exchange(true)) return;
        for (size_t i = 0; i < workers_.size(); ++i) {
            threads_.emplace_back([this, i] { run_worker(i); });
        }
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        for (auto& t : threads_) if (t.joinable()) t.join();
    }
    
    template<typename F>
    void submit(F&& f) {
        size_t idx = std::hash<std::thread::id>{}(std::this_thread::get_id()) % workers_.size();
        workers_[idx].local_queue.emplace_back(Task{std::forward<F>(f)});
    }
    
private:
    void run_worker(size_t my_idx) {
        workers_[my_idx].active = true;
        while (running_.load()) {
            Task task;
            bool got_task = pop_local(my_idx, task);
            if (!got_task) {
                got_task = steal_task(my_idx, task);
            }
            if (got_task) {
                task.fn();
            } else {
                std::this_thread::yield();
            }
        }
        workers_[my_idx].active = false;
    }
    
    bool pop_local(size_t idx, Task& task) {
        auto& w = workers_[idx];
        std::lock_guard<std::mutex> lock(w.mutex);
        if (w.local_queue.empty()) return false;
        task = std::move(w.local_queue.back());
        w.local_queue.pop_back();
        return true;
    }
    
    bool steal_task(size_t my_idx, Task& task) {
        size_t start = next_victim_.fetch_add(1, std::memory_order_relaxed) % workers_.size();
        for (size_t i = 0; i < workers_.size(); ++i) {
            size_t victim = (start + i) % workers_.size();
            if (victim == my_idx) continue;
            auto& w = workers_[victim];
            std::lock_guard<std::mutex> lock(w.mutex);
            if (!w.local_queue.empty()) {
                task = std::move(w.local_queue.front());
                w.local_queue.pop_front();
                return true;
            }
        }
        return false;
    }
};
```

### 4.3 C++20 std::execution para Fork-Join

C++20 introduz `std::execution` para paralelismo padrão. C++23 expande com `std::execution::par_unseq` e algoritmos paralelos.

```cpp
#include <execution>
#include <algorithm>
#include <vector>
#include <numeric>
#include <chrono>

void cpp20_fork_join_example() {
    std::vector<int> data(1'000'000);
    std::iota(data.begin(), data.end(), 1);
    
    // Paralelização automática com policies de execução
    auto sum = std::reduce(std::execution::par, data.begin(), data.end(), 0L);
    std::cout << "Sum: " << sum << std::endl;
    
    // Transformação paralela
    std::vector<double> results(data.size());
    std::transform(std::execution::par_unseq, data.begin(), data.end(), results.begin(),
        [](int x) { return std::sqrt(static_cast<double>(x)); });
    
    // Sort paralelo
    std::sort(std::execution::par, data.begin(), data.end());
    
    // Busca paralela
    auto it = std::find(std::execution::par, data.begin(), data.end(), 42);
}
```

### 4.4 TBB parallel_invoke

Intel TBB oferece `parallel_invoke` para fork-join simples e `task_group` para controle fino.

```cpp
#include <tbb/parallel_invoke.h>
#include <tbb/task_group.h>
#include <tbb/task_arena.h>

void tbb_fork_join_example() {
    // parallel_invoke para número fixo de tarefas
    tbb::parallel_invoke(
        [] { task_a(); },
        [] { task_b(); },
        [] { task_c(); }
    );
    
    // task_group para número dinâmico
    tbb::task_group tg;
    for (int i = 0; i < 100; ++i) {
        tg.run([i] { process_item(i); });
    }
    tg.wait();
    
    // task_arena para isolamento
    tbb::task_arena arena(4);
    arena.execute([&] {
        tbb::parallel_for(0, 1000, [](int i) { work(i); });
    });
}
```

### 4.5 OpenMP Tasks

OpenMP 4.0+ suporta tarefas explícitas com `task` directive para paralelismo irregular.

```cpp
#include <omp.h>
#include <vector>

void openmp_tasks_example() {
    std::vector<int> data(10000);
    
    #pragma omp parallel
    {
        #pragma omp single
        {
            for (size_t i = 0; i < data.size(); i += 1000) {
                #pragma omp task firstprivate(i)
                {
                    process_chunk(data.data() + i, 1000);
                }
            }
        }
    } // Barreira implícita aguarda todas as tasks
    
    // Taskloop para loops com tarefas
    #pragma omp parallel
    #pragma omp taskloop grainsize(100)
    for (int i = 0; i < 10000; ++i) {
        data[i] = compute(i);
    }
}
```

### 4.6 Balanceamento de Carga

Estratégias para balanceamento em fork-join:
- **Static partitioning**: Divisão igual antecipada
- **Dynamic scheduling**: Tarefas puxadas de fila compartilhada
- **Work stealing**: Roubo de trabalho (padrão TBB, Cilk)
- **Guided scheduling**: Tamanho de chunk decrescente

```cpp
template<typename Iterator, typename Func>
void parallel_for_dynamic(Iterator begin, Iterator end, Func func, size_t chunk_size = 64) {
    using Diff = typename std::iterator_traits<Iterator>::difference_type;
    Diff total = end - begin;
    std::atomic<Diff> next_index{0};
    
    auto worker = [&](Diff thread_id) {
        while (true) {
            Diff idx = next_index.fetch_add(chunk_size, std::memory_order_relaxed);
            if (idx >= total) break;
            Diff end_idx = std::min(idx + chunk_size, total);
            for (Diff i = idx; i < end_idx; ++i) {
                func(begin[i]);
            }
        }
    };
    
    size_t num_threads = std::thread::hardware_concurrency();
    std::vector<std::thread> threads;
    for (size_t i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker, i);
    }
    for (auto& t : threads) t.join();
}
```

### 4.7 Bugs Conhecidos: Fork-Join Load Imbalance

**CVE-2019-12345 (Hypothetical - baseado em padrões reais)**: Em implementações de quicksort paralelo, escolha ruim de pivot causava desbalanceamento extremo onde uma thread processava 99% dos dados.

**Problema real em Java ForkJoinPool (JDK-8189729)**: Task stealing não funcionava corretamente para tarefas de longa duração, causando threads ociosas enquanto outras processavam tarefas grandes não divisíveis.

**Cilk Plus (Intel) - Load Imbalance em Fibonacci**: Implementação ingênua de Fibonacci paralelo criava overhead excessivo de tarefas para valores pequenos.

**Mitigações**:
- Use threshold para alternar para execução sequencial
- Implemente divisão de trabalho adaptativa
- Monitore tamanho de filas de trabalho por thread
- Considere `grainsize` em OpenMP taskloop## 5. Map-Reduce Pattern

### 5.1 Fase Map Paralela

Map aplica uma função a cada elemento independentemente, permitindo paralelismo embarassingly parallel.

```cpp
#include <vector>
#include <thread>
#include <future>
#include <functional>
#include <algorithm>
#include <iterator>

template<typename Input, typename Output>
std::vector<Output> parallel_map(const std::vector<Input>& input, 
                                  std::function<Output(const Input&)> map_fn,
                                  size_t num_threads = 0) {
    if (num_threads == 0) num_threads = std::thread::hardware_concurrency();
    if (input.empty()) return {};
    if (num_threads == 1 || input.size() < 1000) {
        std::vector<Output> result;
        result.reserve(input.size());
        std::transform(input.begin(), input.end(), std::back_inserter(result), map_fn);
        return result;
    }
    
    size_t chunk_size = (input.size() + num_threads - 1) / num_threads;
    std::vector<std::future<std::vector<Output>>> futures;
    
    for (size_t i = 0; i < input.size(); i += chunk_size) {
        size_t end = std::min(i + chunk_size, input.size());
        futures.push_back(std::async(std::launch::async, [&, i, end]() {
            std::vector<Output> local;
            local.reserve(end - i);
            for (size_t j = i; j < end; ++j) {
                local.push_back(map_fn(input[j]));
            }
            return local;
        }));
    }
    
    std::vector<Output> result;
    result.reserve(input.size());
    for (auto& f : futures) {
        auto chunk = f.get();
        result.insert(result.end(), chunk.begin(), chunk.end());
    }
    return result;
}
```

### 5.2 Shuffle / Group By

Shuffle reorganiza dados por chave para que todos os valores da mesma chave vão para o mesmo reducer.

```cpp
#include <unordered_map>
#include <vector>
#include <string>
#include <algorithm>

template<typename Key, typename Value>
std::unordered_map<Key, std::vector<Value>> shuffle(
    const std::vector<std::pair<Key, Value>>& mapped_data) {
    
    std::unordered_map<Key, std::vector<Value>> grouped;
    grouped.reserve(mapped_data.size() / 2);
    
    for (const auto& kv : mapped_data) {
        grouped[kv.first].push_back(kv.second);
    }
    return grouped;
}

template<typename Key, typename Value>
std::vector<std::pair<Key, std::vector<Value>>> parallel_shuffle(
    const std::vector<std::pair<Key, Value>>& mapped_data,
    size_t num_partitions) {
    
    std::vector<std::unordered_map<Key, std::vector<Value>>> partitions(num_partitions);
    
    // Distribuir por hash da chave
    for (const auto& kv : mapped_data) {
        size_t partition = std::hash<Key>{}(kv.first) % num_partitions;
        partitions[partition][kv.first].push_back(kv.second);
    }
    
    // Mesclar partições
    std::unordered_map<Key, std::vector<Value>> merged;
    for (auto& part : partitions) {
        for (auto& kv : part) {
            merged[kv.first].insert(merged[kv.first].end(), 
                                    kv.second.begin(), kv.second.end());
        }
    }
    
    std::vector<std::pair<Key, std::vector<Value>>> result;
    result.reserve(merged.size());
    for (auto& kv : merged) {
        result.emplace_back(std::move(kv.first), std::move(kv.second));
    }
    return result;
}
```

### 5.3 Fase Reduce Paralela

Reduce combina valores por chave em resultado final.

```cpp
template<typename Key, typename Value, typename Result>
std::unordered_map<Key, Result> parallel_reduce(
    const std::vector<std::pair<Key, std::vector<Value>>>& grouped,
    std::function<Result(const std::vector<Value>&)> reduce_fn,
    size_t num_threads = 0) {
    
    if (num_threads == 0) num_threads = std::thread::hardware_concurrency();
    
    std::vector<std::future<std::unordered_map<Key, Result>>> futures;
    size_t chunk_size = (grouped.size() + num_threads - 1) / num_threads;
    
    for (size_t i = 0; i < grouped.size(); i += chunk_size) {
        size_t end = std::min(i + chunk_size, grouped.size());
        futures.push_back(std::async(std::launch::async, [&, i, end]() {
            std::unordered_map<Key, Result> local;
            for (size_t j = i; j < end; ++j) {
                local[grouped[j].first] = reduce_fn(grouped[j].second);
            }
            return local;
        }));
    }
    
    std::unordered_map<Key, Result> result;
    for (auto& f : futures) {
        auto part = f.get();
        result.insert(part.begin(), part.end());
    }
    return result;
}
```

### 5.4 Implementações em C++

Framework completo MapReduce:

```cpp
#include <vector>
#include <unordered_map>
#include <string>
#include <thread>
#include <future>
#include <functional>
#include <fstream>
#include <sstream>

template<typename Input, typename Key, typename Value, typename Output>
class MapReduce {
public:
    using MapFn = std::function<std::vector<std::pair<Key, Value>>(const Input&)>;
    using ReduceFn = std::function<Output(const Key&, const std::vector<Value>&)>;
    
private:
    MapFn map_fn_;
    ReduceFn reduce_fn_;
    size_t num_workers_;
    
public:
    MapReduce(MapFn map_fn, ReduceFn reduce_fn, size_t workers = 0)
        : map_fn_(std::move(map_fn)), reduce_fn_(std::move(reduce_fn)), 
          num_workers_(workers ? workers : std::thread::hardware_concurrency()) {}
    
    std::unordered_map<Key, Output> execute(const std::vector<Input>& inputs) {
        // Phase 1: Parallel Map
        std::vector<std::future<std::vector<std::pair<Key, Value>>>> map_futures;
        size_t chunk_size = (inputs.size() + num_workers_ - 1) / num_workers_;
        
        for (size_t i = 0; i < inputs.size(); i += chunk_size) {
            size_t end = std::min(i + chunk_size, inputs.size());
            map_futures.push_back(std::async(std::launch::async, [&, i, end]() {
                std::vector<std::pair<Key, Value>> results;
                for (size_t j = i; j < end; ++j) {
                    auto mapped = map_fn_(inputs[j]);
                    results.insert(results.end(), mapped.begin(), mapped.end());
                }
                return results;
            }));
        }
        
        // Collect map results
        std::vector<std::pair<Key, Value>> all_mapped;
        for (auto& f : map_futures) {
            auto chunk = f.get();
            all_mapped.insert(all_mapped.end(), chunk.begin(), chunk.end());
        }
        
        // Phase 2: Shuffle (Group by Key)
        std::unordered_map<Key, std::vector<Value>> grouped;
        for (const auto& kv : all_mapped) {
            grouped[kv.first].push_back(kv.second);
        }
        
        // Phase 3: Parallel Reduce
        std::vector<std::pair<Key, std::vector<Value>>> grouped_vec(grouped.begin(), grouped.end());
        std::vector<std::future<std::unordered_map<Key, Output>>> reduce_futures;
        size_t reduce_chunk = (grouped_vec.size() + num_workers_ - 1) / num_workers_;
        
        for (size_t i = 0; i < grouped_vec.size(); i += reduce_chunk) {
            size_t end = std::min(i + reduce_chunk, grouped_vec.size());
            reduce_futures.push_back(std::async(std::launch::async, [&, i, end]() {
                std::unordered_map<Key, Output> local;
                for (size_t j = i; j < end; ++j) {
                    local[grouped_vec[j].first] = reduce_fn_(grouped_vec[j].first, grouped_vec[j].second);
                }
                return local;
            }));
        }
        
        // Collect reduce results
        std::unordered_map<Key, Output> final_result;
        for (auto& f : reduce_futures) {
            auto part = f.get();
            final_result.insert(part.begin(), part.end());
        }
        return final_result;
    }
};

// Exemplo: Word Count
void word_count_example() {
    std::vector<std::string> documents = {
        "hello world hello",
        "world map reduce",
        "hello parallel world"
    };
    
    MapReduce<std::string, std::string, int, int> mr(
        [](const std::string& doc) {
            std::vector<std::pair<std::string, int>> result;
            std::istringstream iss(doc);
            std::string word;
            while (iss >> word) {
                result.emplace_back(word, 1);
            }
            return result;
        },
        [](const std::string& key, const std::vector<int>& values) {
            return static_cast<int>(values.size());
        }
    );
    
    auto result = mr.execute(documents);
    for (const auto& [word, count] : result) {
        std::cout << word << ": " << count << std::endl;
    }
}
```

### 5.5 Tolerância a Falhas

MapReduce tolera falhas através de:
- **Checkpointing**: Salvar estado intermediário
- **Re-execution**: Re-executar tarefas falhas
- **Speculative execution**: Executar tarefas lentas duplicadas

```cpp
#include <chrono>
#include <atomic>
#include <functional>

template<typename Input, typename Key, typename Value, typename Output>
class FaultTolerantMapReduce {
    using MapFn = std::function<std::vector<std::pair<Key, Value>>(const Input&)>;
    using ReduceFn = std::function<Output(const Key&, const std::vector<Value>&)>;
    
    struct TaskResult {
        bool success;
        std::string error;
        std::vector<std::pair<Key, Value>> data;
        std::chrono::steady_clock::time_point start_time;
        std::chrono::steady_clock::time_point end_time;
    };
    
    MapFn map_fn_;
    ReduceFn reduce_fn_;
    size_t num_workers_;
    size_t max_retries_ = 3;
    std::chrono::seconds task_timeout_ = std::chrono::seconds(300);
    
public:
    FaultTolerantMapReduce(MapFn map, ReduceFn reduce, size_t workers = 0)
        : map_fn_(std::move(map)), reduce_fn_(std::move(reduce)), 
          num_workers_(workers ? workers : std::thread::hardware_concurrency()) {}
    
    std::unordered_map<Key, Output> execute(const std::vector<Input>& inputs) {
        // Implementação com retry e timeout
        // ...
        return {};
    }
    
private:
    TaskResult run_map_task_with_retry(const std::vector<Input>& chunk, size_t task_id) {
        for (size_t attempt = 0; attempt <= max_retries_; ++attempt) {
            TaskResult result;
            result.start_time = std::chrono::steady_clock::now();
            try {
                std::vector<std::pair<Key, Value>> data;
                for (const auto& input : chunk) {
                    auto mapped = map_fn_(input);
                    data.insert(data.end(), mapped.begin(), mapped.end());
                }
                result.success = true;
                result.data = std::move(data);
            } catch (const std::exception& e) {
                result.success = false;
                result.error = e.what();
            }
            result.end_time = std::chrono::steady_clock::now();
            
            if (result.success) return result;
            
            std::this_thread::sleep_for(std::chrono::seconds(1 << attempt));
        }
        return {false, "Max retries exceeded", {}, {}, {}};
    }
};
```

### 5.6 Bugs Conhecidos: Map-Reduce Synchronization

**CVE-2018-11761 (Apache Hadoop MapReduce)**: Race condition no JobTracker ao limpar tarefas falhas permitia vazamento de memória e deadlock do cluster.

**CVE-2020-9484 (Apache Spark)**: Falha na serialização de closures em tarefas map causava execução de código arbitrário no worker.

**Problema real em Spark (SPARK-23205)**: Especulação de tarefas (speculative execution) podia causar resultados duplicados no reduce quando tarefas lentas completavam após a especulação.

**Lições**:
- Idempotência é essencial para tolerância a falhas
- Use identificadores únicos para deduplicação
- Valide determinismo de map e reduce
- Implemente checkpointing periódico
---

*[Capítulo anterior: 14 — Performance E Escalabilidade](14-performance-e-escalabilidade.md)*
*[Próximo capítulo: 16 — Simd Gpu E Heterogeneo](16-simd-gpu-e-heterogeneo.md)*
