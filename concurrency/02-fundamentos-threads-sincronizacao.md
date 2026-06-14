# Capítulo 2 — Threads, std::thread e Sincronização Básica

## Objetivos de Aprendizado

1. Dominar o ciclo de vida de threads em C++: criação, join, detach e RAII
2. Aplicar corretamente mutexes, locks e primitivas de sincronização básicas
3. Implementar padrões de sincronização seguros: producer-consumer, reader-writer
4. Evitar anti-padrões comuns em concorrência C++: deadlocks, lost wakeups, exception safety
5. Utilizar std::scoped_lock (C++17) para evitar deadlocks em múltiplos mutexes

---

## 1. std::thread em Profundidade

### 1.1 Criação e Move Semantics

```cpp
#include <thread>
#include <iostream>
#include <functional>

void worker_function(int id, const std::string& name) {
    std::cout << "Thread " << id << " (" << name << ") started\n";
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    std::cout << "Thread " << id << " (" << name << ") finished\n";
}

int main() {
    // Criação básica
    std::thread t1(worker_function, 1, "Worker A");
    
    // Move semantics — threads são move-only
    std::thread t2 = std::thread(worker_function, 2, "Worker B");
    
    // Lambda como Callable
    std::thread t3([id = 3]() {
        std::cout << "Lambda thread " << id << "\n";
    });
    
    // std::bind
    auto bound = std::bind(worker_function, 4, "Bound");
    std::thread t4(bound);
    
    // join() — bloqueia até a thread terminar
    t1.join();
    t2.join();
    t3.join();
    t4.join();
    
    return 0;
}
```

### 1.2 join() vs detach()

```cpp
#include <thread>
#include <iostream>

void long_running_task() {
    for (int i = 0; i < 10; ++i) {
        std::cout << "Working... " << i << "\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
}

int main() {
    // join() — bloqueia até completar
    {
        std::thread t(long_running_task);
        t.join();  //主线程 bloqueia aqui
        std::cout << "Thread joined successfully\n";
    }
    
    // detach() — thread roda independentemente
    {
        std::thread t(long_running_task);
        t.detach();  // Thread continua rodando em background
        // CUIDADO: objeto t é destruído, mas thread continua
        // Perigoso: acessar variáveis locais que podem ser destruídas
    }
    
    // Padrão seguro: RAII com join automático
    class ScopedThread {
        std::thread t_;
    public:
        template<typename F, typename... Args>
        explicit ScopedThread(F&& f, Args&&... args)
            : t_(std::forward<F>(f), std::forward<Args>(args)...) {}
        
        ~ScopedThread() {
            if (t_.joinable()) {
                t_.join();
            }
        }
        
        ScopedThread(const ScopedThread&) = delete;
        ScopedThread& operator=(const ScopedThread&) = delete;
        ScopedThread(ScopedThread&&) = default;
        ScopedThread& operator=(ScopedThread&&) = default;
    };
    
    {
        ScopedThread st(long_running_task);
        // Thread será joinada automaticamente no destructor
    }
    std::cout << "ScopedThread destroyed, thread joined\n";
    
    return 0;
}
```

### 1.3 Passagem de Argumentos

```cpp
#include <thread>
#include <string>
#include <vector>
#include <iostream>
#include <functional>

// PROBLEMA: reference argument pode causar dangling reference
void dangerous_ref(const std::string& s) {
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    std::cout << s << "\n";  // s pode não existir mais!
}

// SOLUÇÃO: std::ref para reference_wrapper
void safe_ref(std::reference_wrapper<std::string> sr) {
    std::string& s = sr.get();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    std::cout << s << "\n";  // Seguro: referência é válida
}

// SOLUÇÃO: mover para thread
void safe_move(std::string s) {  // Recebe por valor
    std::cout << s << "\n";
}

int main() {
    std::string data = "Hello, World!";
    
    // PERIGOSO: passar referência temporária
    // std::thread t1(dangerous_ref, data);  // COMPILE ERROR: cópia não funciona
    // std::thread t1(dangerous_ref, std::cref(data));  // PERIGOSO: data pode ser destruído
    
    // SEGURO: std::ref
    std::thread t2(safe_ref, std::ref(data));
    t2.join();
    
    // SEGURO: mover para thread
    std::thread t3(safe_move, std::move(data));
    t3.join();
    
    return 0;
}
```

---

## 2. Gerenciamento de Ciclo de Vida

### 2.1 Thread Guard Pattern (RAII)

```cpp
#include <thread>
#include <iostream>
#include <stdexcept>

class ThreadGuard {
    std::thread& thread_;
public:
    explicit ThreadGuard(std::thread& t) : thread_(t) {}
    
    ~ThreadGuard() {
        if (thread_.joinable()) {
            std::cout << "Joining thread in destructor\n";
            thread_.join();
        }
    }
    
    ThreadGuard(const ThreadGuard&) = delete;
    ThreadGuard& operator=(const ThreadGuard&) = delete;
};

void risky_function() {
    std::thread t([] {
        std::cout << "Worker thread running\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    });
    ThreadGuard guard(t);  // join automático se exceção lançada
    
    // Código que pode lançar exceção
    if (true) {
        throw std::runtime_error("Something went wrong!");
    }
    // Thread será joinada mesmo com exceção
}

int main() {
    try {
        risky_function();
    } catch (const std::exception& e) {
        std::cout << "Caught: " << e.what() << "\n";
    }
    return 0;
}
```

### 2.2 Exception Safety com Threads

```cpp
#include <thread>
#include <vector>
#include <numeric>
#include <iostream>
#include <stdexcept>

// EXCEPTION SAFE: uso de std::async que retorna future
std::vector<int> parallel_sum(const std::vector<int>& data, size_t num_threads) {
    if (data.empty()) return {};
    
    size_t chunk_size = (data.size() + num_threads - 1) / num_threads;
    std::vector<std::future<int>> futures;
    
    for (size_t t = 0; t < num_threads; ++t) {
        size_t start = t * chunk_size;
        size_t end = std::min(start + chunk_size, data.size());
        
        if (start >= data.size()) break;
        
        futures.push_back(std::async(std::launch::async, [&data, start, end]() {
            return std::accumulate(data.begin() + start, data.begin() + end, 0);
        }));
    }
    
    // Exceções são propagadas automaticamente via future
    std::vector<int> partial_sums;
    for (auto& f : futures) {
        partial_sums.push_back(f.get());  // rethrows exceptions
    }
    
    return partial_sums;
}

int main() {
    std::vector<int> data(1000000);
    std::iota(data.begin(), data.end(), 1);
    
    auto partial = parallel_sum(data, 4);
    int total = std::accumulate(partial.begin(), partial.end(), 0);
    std::cout << "Total: " << total << "\n";
    
    return 0;
}
```

---

## 3. Mutexes e Locks

### 3.1 std::mutex

```cpp
#include <mutex>
#include <thread>
#include <vector>
#include <iostream>

class ThreadSafeCounter {
    int count_ = 0;
    std::mutex mutex_;
public:
    void increment() {
        std::lock_guard<std::mutex> lock(mutex_);
        ++count_;
    }
    
    int get() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return count_;
    }
};

void increment_counter(ThreadSafeCounter& counter, int iterations) {
    for (int i = 0; i < iterations; ++i) {
        counter.increment();
    }
}

int main() {
    ThreadSafeCounter counter;
    constexpr int NUM_THREADS = 8;
    constexpr int ITERATIONS = 1000000;
    
    std::vector<std::thread> threads;
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back(increment_counter, std::ref(counter), ITERATIONS);
    }
    
    for (auto& t : threads) {
        t.join();
    }
    
    std::cout << "Counter: " << counter.get() << "\n";
    std::cout << "Expected: " << NUM_THREADS * ITERATIONS << "\n";
    
    return 0;
}
```

### 3.2 std::shared_mutex (C++17)

```cpp
#include <shared_mutex>
#include <thread>
#include <vector>
#include <string>
#include <iostream>
#include <map>

class ThreadSafeConfig {
    mutable std::shared_mutex mutex_;
    std::map<std::string, std::string> config_;
    
public:
    // Leitura: múltiplas threads simultâneas
    std::string get(const std::string& key) const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        auto it = config_.find(key);
        return (it != config_.end()) ? it->second : "";
    }
    
    // Escrita: exclusiva
    void set(const std::string& key, const std::string& value) {
        std::unique_lock<std::shared_mutex> lock(mutex_);
        config_[key] = value;
    }
    
    // Leitura: múltiplas threads simultâneas
    size_t size() const {
        std::shared_lock<std::shared_mutex> lock(mutex_);
        return config_.size();
    }
};

void reader_task(const ThreadSafeConfig& config, int id) {
    for (int i = 0; i < 100; ++i) {
        std::string val = config.get("key" + std::to_string(i % 10));
        (void)val;
    }
    std::cout << "Reader " << id << " finished\n";
}

void writer_task(ThreadSafeConfig& config, int id) {
    for (int i = 0; i < 100; ++i) {
        config.set("key" + std::to_string(i % 10), "value" + std::to_string(i));
    }
    std::cout << "Writer " << id << " finished\n";
}

int main() {
    ThreadSafeConfig config;
    
    // Inicializar
    for (int i = 0; i < 10; ++i) {
        config.set("key" + std::to_string(i), "initial" + std::to_string(i));
    }
    
    std::vector<std::thread> threads;
    
    // 4 readers concorrentes
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(reader_task, std::ref(config), i);
    }
    
    // 2 writers
    for (int i = 0; i < 2; ++i) {
        threads.emplace_back(writer_task, std::ref(config), i);
    }
    
    for (auto& t : threads) {
        t.join();
    }
    
    std::cout << "Config size: " << config.size() << "\n";
    return 0;
}
```

### 3.3 std::timed_mutex

```cpp
#include <mutex>
#include <thread>
#include <chrono>
#include <iostream>

class TimedLockExample {
    std::timed_mutex mutex_;
    int value_ = 0;
    
public:
    bool try_increment_for(int milliseconds) {
        std::unique_lock<std::timed_mutex> lock(mutex_,
            std::chrono::milliseconds(milliseconds));
        
        if (lock.owns_lock()) {
            ++value_;
            return true;
        }
        return false;  // Timeout — não conseguiu adquirir lock
    }
    
    int get_value() const {
        // Para leitura em timed_mutex, precisa de unique_lock
        std::unique_lock<std::timed_mutex> lock(
            const_cast<std::timed_mutex&>(mutex_),
            std::chrono::milliseconds(100));
        return (lock.owns_lock()) ? value_ : -1;
    }
};

int main() {
    TimedLockExample example;
    
    std::thread t1([&] {
        for (int i = 0; i < 10; ++i) {
            if (example.try_increment_for(10)) {
                std::cout << "T1 incremented\n";
            } else {
                std::cout << "T1 timed out\n";
            }
        }
    });
    
    std::thread t2([&] {
        for (int i = 0; i < 10; ++i) {
            if (example.try_increment_for(10)) {
                std::cout << "T2 incremented\n";
            } else {
                std::cout << "T2 timed out\n";
            }
        }
    });
    
    t1.join();
    t2.join();
    
    std::cout << "Final value: " << example.get_value() << "\n";
    return 0;
}
```

---

## 4. Lock Wrappers RAII

### 4.1 std::lock_guard

```cpp
#include <mutex>
#include <vector>
#include <iostream>

class ResourceManager {
    std::mutex resource_mutex_;
    std::vector<int> resources_;
    int allocations_ = 0;
    
public:
    int allocate() {
        std::lock_guard<std::mutex> lock(resource_mutex_);
        int id = allocations_++;
        resources_.push_back(id);
        return id;
    }
    
    void deallocate(int id) {
        std::lock_guard<std::mutex> lock(resource_mutex_);
        auto it = std::find(resources_.begin(), resources_.end(), id);
        if (it != resources_.end()) {
            resources_.erase(it);
        }
    }
    
    size_t count() const {
        std::lock_guard<std::mutex> lock(resource_mutex_);
        return resources_.size();
    }
};
```

### 4.2 std::unique_lock

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>
#include <thread>
#include <iostream>
#include <string>

class MessageQueue {
    std::queue<std::string> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    bool shutdown_ = false;
    
public:
    void push(std::string msg) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            queue_.push(std::move(msg));
        }
        cv_.notify_one();
    }
    
    bool try_pop_for(std::string& msg, std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        
        // Espera com timeout — unique_lock necessário para cv_.wait_for
        if (!cv_.wait_for(lock, timeout, [this] {
            return !queue_.empty() || shutdown_;
        })) {
            return false;  // Timeout
        }
        
        if (queue_.empty()) return false;  // Shutdown
        
        msg = std::move(queue_.front());
        queue_.pop();
        return true;
    }
    
    void shutdown() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            shutdown_ = true;
        }
        cv_.notify_all();
    }
};

int main() {
    MessageQueue mq;
    
    // Producer
    std::thread producer([&] {
        for (int i = 0; i < 5; ++i) {
            mq.push("Message " + std::to_string(i));
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }
        mq.shutdown();
    });
    
    // Consumer
    std::thread consumer([&] {
        std::string msg;
        while (mq.try_pop_for(msg, std::chrono::milliseconds(100))) {
            std::cout << "Received: " << msg << "\n";
        }
        std::cout << "Consumer finished\n";
    });
    
    producer.join();
    consumer.join();
    
    return 0;
}
```

### 4.3 std::scoped_lock (C++17)

```cpp
#include <mutex>
#include <thread>
#include <iostream>
#include <string>

class Account {
    std::mutex mutex_;
    std::string name_;
    int balance_;
    
public:
    Account(std::string name, int balance)
        : name_(std::move(name)), balance_(balance) {}
    
    // Transferência entre duas contas — deadlock-free com scoped_lock
    static void transfer(Account& from, Account& to, int amount) {
        // scoped_lock adquire AMBOS mutexes sem deadlock
        std::scoped_lock lock(from.mutex_, to.mutex_);
        
        if (from.balance_ >= amount) {
            from.balance_ -= amount;
            to.balance_ += amount;
            std::cout << from.name_ << " transferred " << amount
                      << " to " << to.name_ << "\n";
        } else {
            std::cout << "Insufficient funds in " << from.name_ << "\n";
        }
    }
    
    int balance() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return balance_;
    }
    
    const std::string& name() const { return name_; }
};

int main() {
    Account alice("Alice", 1000);
    Account bob("Bob", 500);
    
    // Transferências simultâneas — scoped_lock evita deadlock
    std::thread t1([&] {
        for (int i = 0; i < 10; ++i) {
            Account::transfer(alice, bob, 50);
        }
    });
    
    std::thread t2([&] {
        for (int i = 0; i < 10; ++i) {
            Account::transfer(bob, alice, 30);
        }
    });
    
    t1.join();
    t2.join();
    
    std::cout << "Alice: " << alice.balance() << "\n";
    std::cout << "Bob: " << bob.balance() << "\n";
    
    return 0;
}
```

---

## 5. Condicionais (Condition Variables)

### 5.1 Producer-Consumer com Condition Variable

```cpp
#include <condition_variable>
#include <mutex>
#include <queue>
#include <thread>
#include <iostream>
#include <chrono>

template<typename T>
class ThreadSafeQueue {
    std::queue<T> queue_;
    mutable std::mutex mutex_;
    std::condition_variable not_empty_;
    std::condition_variable not_full_;
    size_t max_size_;
    bool shutdown_ = false;
    
public:
    explicit ThreadSafeQueue(size_t max_size = 100) : max_size_(max_size) {}
    
    void push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);
        not_full_.wait(lock, [this] {
            return queue_.size() < max_size_ || shutdown_;
        });
        
        if (shutdown_) return;
        
        queue_.push(std::move(item));
        lock.unlock();
        not_empty_.notify_one();
    }
    
    bool pop(T& item) {
        std::unique_lock<std::mutex> lock(mutex_);
        not_empty_.wait(lock, [this] {
            return !queue_.empty() || shutdown_;
        });
        
        if (queue_.empty()) return false;
        
        item = std::move(queue_.front());
        queue_.pop();
        lock.unlock();
        not_full_.notify_one();
        return true;
    }
    
    void shutdown() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            shutdown_ = true;
        }
        not_empty_.notify_all();
        not_full_.notify_all();
    }
    
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }
};

int main() {
    ThreadSafeQueue<int> queue(10);
    
    // Producers
    std::vector<std::thread> producers;
    for (int p = 0; p < 3; ++p) {
        producers.emplace_back([&queue, p] {
            for (int i = 0; i < 5; ++i) {
                int item = p * 100 + i;
                queue.push(item);
                std::cout << "Produced: " << item << "\n";
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        });
    }
    
    // Consumers
    std::vector<std::thread> consumers;
    for (int c = 0; c < 2; ++c) {
        consumers.emplace_back([&queue, c] {
            int item;
            while (queue.pop(item)) {
                std::cout << "Consumer " << c << " got: " << item << "\n";
                std::this_thread::sleep_for(std::chrono::milliseconds(15));
            }
        });
    }
    
    for (auto& t : producers) t.join();
    queue.shutdown();
    for (auto& t : consumers) t.join();
    
    return 0;
}
```

### 5.2 Lost Wakeup Problem

```cpp
#include <condition_variable>
#include <mutex>
#include <thread>
#include <iostream>

// ANTI-PADRÃO: lost wakeup
class BrokenEvent {
    std::mutex mutex_;
    bool ready_ = false;
    
public:
    // PRODUCER
    void signal_broken() {
        std::lock_guard<std::mutex> lock(mutex_);
        ready_ = true;  // Pode acontecer ANTES do wait!
    }
    
    // CONSUMER — PERIGOSO: lost wakeup
    void wait_broken() {
        std::unique_lock<std::mutex> lock(mutex_);
        while (!ready_) {
            // Se signal aconteceu entre while check e wait:
            // ready_ = true, mas wait() bloqueia para sempre!
            mutex_.unlock();
            // ... race condition aqui ...
            mutex_.lock();
        }
    }
};

// CORRETO: predicate-based wait
class CorrectEvent {
    std::mutex mutex_;
    std::condition_variable cv_;
    bool ready_ = false;
    
public:
    void signal() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            ready_ = true;
        }
        cv_.notify_one();  // Fora do lock — OK pois cv não tem estado
    }
    
    void wait() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return ready_; });
        // Predicate-based wait não sofre lost wakeup
    }
    
    void wait_with_timeout(std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (!cv_.wait_for(lock, timeout, [this] { return ready_; })) {
            std::cout << "Timeout!\n";
        }
    }
};

int main() {
    CorrectEvent event;
    
    // Consumer espera
    std::thread consumer([&] {
        std::cout << "Consumer waiting...\n";
        event.wait();
        std::cout << "Consumer: event received!\n";
    });
    
    // Producer sinaliza
    std::thread producer([&] {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        std::cout << "Producer signaling...\n";
        event.signal();
    });
    
    consumer.join();
    producer.join();
    
    return 0;
}
```

---

## 6. Thread-Local Storage

### 6.1 thread_local Keyword

```cpp
#include <thread>
#include <iostream>
#include <vector>
#include <sstream>

// Thread-local counter — cada thread tem sua cópia
thread_local int thread_counter = 0;
thread_local std::string thread_name;

void increment_and_print(const std::string& name) {
    thread_name = name;
    for (int i = 0; i < 5; ++i) {
        ++thread_counter;
        std::ostringstream oss;
        oss << thread_name << " counter: " << thread_counter << "\n";
        std::cout << oss.str();
    }
}

int main() {
    std::thread t1(increment_and_print, "T1");
    std::thread t2(increment_and_print, "T2");
    std::thread t3(increment_and_print, "T3");
    
    t1.join();
    t2.join();
    t3.join();
    
    // Counter da thread principal é 0 — cada thread tem sua cópia
    std::cout << "Main thread counter: " << thread_counter << "\n";
    
    return 0;
}
```

### 6.2 Destruição Ordenada

```cpp
#include <thread>
#include <iostream>
#include <string>

// CUIDADO: thread_local destruído na ordem reversa de construção
// dentro de cada thread

struct Tracked {
    std::string name;
    Tracked(const std::string& n) : name(n) {
        std::cout << "Constructing " << name << "\n";
    }
    ~Tracked() {
        std::cout << "Destroying " << name << "\n";
    }
};

// thread_local objects — destruídos quando thread termina
thread_local Tracked a("A");
thread_local Tracked b("B");
thread_local Tracked c("C");

void thread_func() {
    // Construction: A, B, C
    // Destruction: C, B, A (reverse order)
    std::cout << "Thread running\n";
}

int main() {
    std::thread t(thread_func);
    t.join();
    std::cout << "Main: thread finished\n";
    return 0;
}
```

---

## 7. Primitivas de Sincronização C++20

### 7.1 std::latch

```cpp
#include <latch>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>

void run_with_latch(int num_threads) {
    std::latch ready(num_threads);  // Contador para N threads
    std::latch done(1);             // Contador para main thread
    
    std::vector<std::thread> threads;
    
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back([&ready, &done, i] {
            std::cout << "Thread " << i << " initialization...\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(50 * i));
            
            ready.count_down();  // Sinaliza que está pronta
            ready.wait();         // Espera TODAS as threads ficarem prontas
            
            std::cout << "Thread " << i << " working (all ready)...\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            
            if (i == 0) {
                done.count_down();  // Sinaliza que terminou
            }
        });
    }
    
    done.wait();  // Espera trabalho principal terminar
    for (auto& t : threads) t.join();
    
    std::cout << "All threads completed\n";
}

int main() {
    run_with_latch(4);
    return 0;
}
```

### 7.2 std::barrier

```cpp
#include <barrier>
#include <thread>
#include <vector>
#include <iostream>
#include <numeric>
#include <vector>

void parallel_computation(int num_threads, std::vector<double>& data) {
    std::barrier sync_point(num_threads);
    
    std::vector<std::thread> threads;
    
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&, t] {
            size_t chunk = (data.size() + num_threads - 1) / num_threads;
            size_t start = t * chunk;
            size_t end = std::min(start + chunk, data.size());
            
            // Fase 1: cada thread calcula sua parte
            for (size_t i = start; i < end; ++i) {
                data[i] = std::sin(data[i]) + std::cos(data[i]);
            }
            
            // Sincroniza — todas as threads completaram fase 1
            sync_point.arrive_and_wait();
            
            // Fase 2: cada thread normaliza usando o máximo
            // (simplificado — em realidade precisa de reduce)
            double max_val = *std::max_element(data.begin() + start,
                                                data.begin() + end);
            for (size_t i = start; i < end; ++i) {
                data[i] /= max_val;
            }
            
            sync_point.arrive_and_wait();
            
            // Fase 3: ...
        });
    }
    
    for (auto& t : threads) t.join();
}

int main() {
    std::vector<double> data(1000);
    std::iota(data.begin(), data.end(), 1.0);
    
    parallel_computation(4, data);
    
    std::cout << "First 5 values: ";
    for (int i = 0; i < 5; ++i) {
        std::cout << data[i] << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

### 7.3 std::counting_semaphore

```cpp
#include <semaphore>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>

// Semáforo para limitar concorrência
class ThreadPool {
    std::counting_semaphore<> slots_;  // Controla slots disponíveis
    std::vector<std::thread> workers_;
    
public:
    explicit ThreadPool(size_t max_concurrent)
        : slots_(max_concurrent) {}
    
    template<typename F>
    void submit(F&& task) {
        slots_.acquire();  // Espera slot disponível
        
        workers_.emplace_back([this, t = std::forward<F>(task)]() mutable {
            t();
            slots_.release();  // Libera slot
        });
    }
    
    void wait_all() {
        for (auto& t : workers_) {
            t.join();
        }
    }
};

int main() {
    ThreadPool pool(3);  // Máximo 3 threads simultâneas
    
    for (int i = 0; i < 10; ++i) {
        pool.submit([i] {
            std::cout << "Task " << i << " on thread "
                      << std::this_thread::get_id() << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        });
    }
    
    pool.wait_all();
    std::cout << "All tasks completed\n";
    
    return 0;
}
```

---

## 8. Erros Comuns e Anti-Padrões

### 8.1 Forgotten Join/Detach

```cpp
// PERIGOSO: std::thread destruído sem join/detach
void dangerous() {
    std::thread t([] { std::cout << "Work\n"; });
    // Se exception lançada aqui, t é destruído sem join
    // → std::terminate() é chamado!
}

// CORRETO: sempre join ou detach
void correct() {
    std::thread t([] { std::cout << "Work\n"; });
    try {
        do_risky_work();
        t.join();
    } catch (...) {
        t.join();  // Garantir join mesmo com exceção
        throw;
    }
}
```

### 8.2 Double Lock

```cpp
#include <mutex>
#include <iostream>

std::mutex mtx;

// PERIGOSO: deadlock — mutex não é recursivo
void dangerous_double_lock() {
    std::lock_guard<std::mutex> lock(mtx);
    // ... código que chama função que também locka mtx
    another_function_that_locks_mtx();  // DEADLOCK!
}

// CORRETO: usar recursive_mutex ou redesign
std::recursive_mutex rmtx;

void safe_recursive() {
    std::lock_guard<std::recursive_mutex> lock(rmtx);
    // OK: recursive_mutex permite múltiplos locks
    another_function_that_locks_rmtx();
}
```

### 8.3 Holding Lock During I/O

```cpp
#include <mutex>
#include <fstream>
#include <iostream>

std::mutex log_mutex;

// PERIGOSO: lock durante I/O lento
void slow_logging() {
    std::lock_guard<std::mutex> lock(log_mutex);
    // I/O é lento — outras threads bloqueiam
    std::ofstream file("log.txt", std::ios::app);
    file << "This is a slow log operation\n";
    file.flush();
}

// CORRETO: minimizar tempo com lock
void fast_logging() {
    std::string message = "This is a fast log operation\n";
    
    // I/O fora do lock
    {
        std::lock_guard<std::mutex> lock(log_mutex);
        // Apenas operação rápida
        // ... buffering, etc
    }
    
    // I/O sem lock
    std::ofstream file("log.txt", std::ios::app);
    file << message;
}
```

---

## 9. Exercício Prático

### Thread-Safe LRU Cache

```cpp
#include <unordered_map>
#include <list>
#include <shared_mutex>
#include <optional>
#include <iostream>

template<typename Key, typename Value>
class ThreadSafeLRUCache {
    using ListIterator = typename std::list<std::pair<Key, Value>>::iterator;
    
    mutable std::shared_mutex mutex_;
    std::list<std::pair<Key, Value>> order_;  // LRU order
    std::unordered_map<Key, ListIterator> cache_;
    size_t capacity_;
    
public:
    explicit ThreadSafeLRUCache(size_t capacity) : capacity_(capacity) {}
    
    std::optional<Value> get(const Key& key) {
        std::unique_lock lock(mutex_);
        auto it = cache_.find(key);
        if (it == cache_.end()) {
            return std::nullopt;
        }
        
        // Move to front (most recently used)
        order_.splice(order_.begin(), order_, it->second);
        return it->second->second;
    }
    
    void put(const Key& key, Value value) {
        std::unique_lock lock(mutex_);
        auto it = cache_.find(key);
        
        if (it != cache_.end()) {
            // Update existing
            it->second->second = std::move(value);
            order_.splice(order_.begin(), order_, it->second);
            return;
        }
        
        // Evict if at capacity
        if (cache_.size() >= capacity_) {
            auto last = std::prev(order_.end());
            cache_.erase(last->first);
            order_.erase(last);
        }
        
        // Insert new
        order_.emplace_front(key, std::move(value));
        cache_[key] = order_.begin();
    }
    
    size_t size() const {
        std::shared_lock lock(mutex_);
        return cache_.size();
    }
};

int main() {
    ThreadSafeLRUCache<int, std::string> cache(3);
    
    cache.put(1, "one");
    cache.put(2, "two");
    cache.put(3, "three");
    
    auto val = cache.get(1);
    if (val) std::cout << "Got: " << *val << "\n";
    
    cache.put(4, "four");  // Evicts key 2 (LRU)
    
    val = cache.get(2);
    std::cout << "Key 2 after eviction: " << (val ? *val : "not found") << "\n";
    
    std::cout << "Cache size: " << cache.size() << "\n";
    
    return 0;
}
```

---

## 10. Referências

- **C++17 Standard** — ISO/IEC 14882:2017, §30 (Thread support library)
- **C++20 Standard** — ISO/IEC 14882:2020, §32 (Thread support library)
- **Williams, A.** — C++ Concurrency in Action, 2nd Edition (Manning, 2019)
- **Becker, B.** — The C++ Standard Library: A Tutorial and Reference, 2nd Edition
- **cppreference.com** — std::thread, std::mutex, std::condition_variable
- **ISO/IEC 14882:2020** — §32.4.4 (std::scoped_lock), §32.10 (latch/barrier/semaphore)
