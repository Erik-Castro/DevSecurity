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
```