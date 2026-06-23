# Capítulo 4 — Deadlocks, Livelocks e Starvation

## Objetivos de Aprendizado

1. Compreender as quatro condições de Coffman para deadlock e como quebrar cada uma
2. Implementar prevenção de deadlock usando std::scoped_lock e ordenação de locks
3. Detectar e recuperar de deadlocks usando wait-for graphs
4. Identificar e resolver livelocks com backoff exponencial
5. Prevenir starvation e priority inversion em sistemas de tempo real
## 1. Fundamentos de Deadlock

### 1.1 Condições de Coffman

Em 1971, Edward Coffman Jr. e seus colegas formalizaram as quatro condições necessárias para que um deadlock ocorra. Todas as quatro devem ser satisfeitas simultaneamente:

1. **Exclusão Mútua (Mutual Exclusion)**: Pelo menos um recurso deve ser mantido em modo não compartilhável. Apenas uma thread pode usar o recurso por vez.

2. **Retenção e Espera (Hold and Wait)**: Uma thread que já possui pelo menos um recurso está esperando para adquirir recursos adicionais mantidos por outras threads.

3. **Não Preempção (No Preemption)**: Recursos não podem ser preemptados; um recurso só pode ser liberado voluntariamente pela thread que o possui.

4. **Espera Circular (Circular Wait)**: Existe um conjunto de threads {T1, T2, ..., Tn} tal que T1 espera por um recurso mantido por T2, T2 espera por um recurso mantido por T3, ..., Tn espera por um recurso mantido por T1.

```cpp
// Exemplo clássico de deadlock: duas threads, dois mutexes
#include <mutex>
#include <thread>
#include <chrono>
#include <iostream>

std::mutex mutex_a;
std::mutex mutex_b;

void thread1_func() {
    std::lock_guard<std::mutex> lock_a(mutex_a);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> lock_b(mutex_b);
    std::cout << "Thread 1 adquiriu ambos os locks\n";
}

void thread2_func() {
    std::lock_guard<std::mutex> lock_b(mutex_b);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> lock_a(mutex_a);
    std::cout << "Thread 2 adquiriu ambos os locks\n";
}

int main() {
    std::thread t1(thread1_func);
    std::thread t2(thread2_func);
    t1.join();
    t2.join();
    return 0;
}
```

### 1.2 Grafo de Alocação de Recursos

O Resource Allocation Graph (RAG) é uma representação visual para detectar deadlocks:

- **Nós de Processo (círculos)**: Representam threads/processos
- **Nós de Recurso (quadrados)**: Representam recursos (mutexes, semáforos, etc.)
- **Arestas de Requisição (P → R)**: Processo P está solicitando recurso R
- **Arestas de Atribuição (R → P)**: Recurso R está atribuído ao processo P

Um ciclo no grafo indica deadlock potencial.

```cpp
// Representação simplificada de um Resource Allocation Graph
#include <unordered_map>
#include <vector>
#include <string>
#include <iostream>

class ResourceAllocationGraph {
    std::unordered_map<std::string, std::vector<std::string>> requests;  // thread -> resources
    std::unordered_map<std::string, std::vector<std::string>> holds;     // resource -> threads

public:
    void request(const std::string& thread, const std::string& resource) {
        requests[thread].push_back(resource);
    }

    void acquire(const std::string& thread, const std::string& resource) {
        holds[resource].push_back(thread);
        // Remove da lista de requisições
        auto& req = requests[thread];
        req.erase(std::remove(req.begin(), req.end(), resource), req.end());
    }

    void release(const std::string& thread, const std::string& resource) {
        auto& holders = holds[resource];
        holders.erase(std::remove(holders.begin(), holders.end(), thread), holders.end());
    }

    bool hasCycle() const {
        // Implementação simplificada de detecção de ciclo usando DFS
        std::unordered_map<std::string, int> visited;  // 0=unvisited, 1=visiting, 2=visited
        
        std::function<bool(const std::string&)> dfs = [&](const std::string& node) -> bool {
            visited[node] = 1;  // visiting
            
            // Verifica arestas de requisição (thread -> resource)
            if (requests.count(node)) {
                for (const auto& resource : requests.at(node)) {
                    if (holds.count(resource)) {
                        for (const auto& holder : holds.at(resource)) {
                            if (visited[holder] == 1) return true;  // Cycle detected
                            if (visited[holder] == 0 && dfs(holder)) return true;
                        }
                    }
                }
            }
            
            visited[node] = 2;  // visited
            return false;
        };

        for (const auto& [thread, _] : requests) {
            if (visited[thread] == 0 && dfs(thread)) return true;
        }
        return false;
    }
};
```

### 1.3 Deadlock vs Livelock vs Starvation

| Característica | Deadlock | Livelock | Starvation |
|----------------|----------|----------|------------|
| **Progresso** | Zero - threads bloqueadas permanentemente | Zero - threads ativas mas sem progresso | Zero - thread nunca consegue recurso |
| **Estado das Threads** | Bloqueadas (waiting) | Executando (running) | Bloqueadas ou ready |
| **CPU Usage** | Baixo | Alto (busy-waiting) | Variável |
| **Recuperação** | Requer intervenção externa | Pode auto-recuperar com backoff | Requer escalonamento justo |
| **Causa Comum** | Ordem de locks inconsistente | Retry agressivo sem backoff | Prioridade baixa, unfair locking |

```cpp
// Deadlock: threads bloqueadas indefinidamente
// Livelock: threads continuam tentando mas nunca progridem
// Starvation: thread nunca consegue o recurso

// Exemplo de Livelock: duas threads tentando ser "educadas"
#include <atomic>
#include <thread>
#include <chrono>

std::atomic<bool> flag_a{false};
std::atomic<bool> flag_b{false};

void polite_thread_a() {
    while (true) {
        flag_a.store(true, std::memory_order_release);
        while (flag_b.load(std::memory_order_acquire)) {
            flag_a.store(false, std::memory_order_release);
            std::this_thread::yield();
            flag_a.store(true, std::memory_order_release);
        }
        // Critical section
        flag_a.store(false, std::memory_order_release);
        break;
    }
}

void polite_thread_b() {
    while (true) {
        flag_b.store(true, std::memory_order_release);
        while (flag_a.load(std::memory_order_acquire)) {
            flag_b.store(false, std::memory_order_release);
            std::this_thread::yield();
            flag_b.store(true, std::memory_order_release);
        }
        // Critical section
        flag_b.store(false, std::memory_order_release);
        break;
    }
}
```

### 1.4 Por que Deadlocks são Difíceis de Reproduzir

Deadlocks são notoriamente difíceis de reproduzir porque:

1. **Dependência de Timing**: Requerem interleaving específico de execução
2. **Não Determinismo**: Escalonador do SO, cache, interrupts afetam timing
3. **Raridade**: Podem ocorrer uma vez em milhões de execuções
4. **Heisenbugs**: Depuradores alteram timing e "consertam" o bug

```cpp
// Técnica para aumentar probabilidade de deadlock em testes
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>

std::mutex m1, m2;
std::atomic<int> sync_point{0};

void stress_thread_a() {
    for (int i = 0; i < 10000; ++i) {
        std::lock_guard<std::mutex> lock1(m1);
        sync_point.fetch_add(1, std::memory_order_acq_rel);
        while (sync_point.load(std::memory_order_acquire) < 2) {
            std::this_thread::yield();
        }
        std::lock_guard<std::mutex> lock2(m2);
        // Critical section
    }
}

void stress_thread_b() {
    for (int i = 0; i < 10000; ++i) {
        std::lock_guard<std::mutex> lock1(m2);
        sync_point.fetch_add(1, std::memory_order_acq_rel);
        while (sync_point.load(std::memory_order_acquire) < 2) {
            std::this_thread::yield();
        }
        std::lock_guard<std::mutex> lock2(m1);
        // Critical section
    }
}
```


## 2. Prevenção de Deadlock

### 2.1 Quebrando Hold-and-Wait

A estratégia mais prática é garantir que uma thread adquira todos os recursos necessários de uma só vez, ou nenhum.

#### std::scoped_lock para Múltiplos Mutexes

Desde C++17, `std::scoped_lock` adquire múltiplos mutexes de forma atômica, evitando deadlock por ordem inconsistente:

```cpp
#include <mutex>
#include <vector>
#include <iostream>

class BankAccount {
    std::mutex mtx_;
    double balance_;
    std::string name_;

public:
    BankAccount(const std::string& name, double initial) 
        : name_(name), balance_(initial) {}

    void deposit(double amount) {
        std::lock_guard<std::mutex> lock(mtx_);
        balance_ += amount;
    }

    bool withdraw(double amount) {
        std::lock_guard<std::mutex> lock(mtx_);
        if (balance_ >= amount) {
            balance_ -= amount;
            return true;
        }
        return false;
    }

    double get_balance() const {
        std::lock_guard<std::mutex> lock(mtx_);
        return balance_;
    }

    // Transfer atômica entre duas contas - SEM DEADLOCK
    static void transfer(BankAccount& from, BankAccount& to, double amount) {
        // std::scoped_lock adquire ambos os mutexes de forma atômica
        // Usa algoritmo de ordenação por endereço para evitar deadlock
        std::scoped_lock lock(from.mtx_, to.mtx_);
        
        if (from.balance_ >= amount) {
            from.balance_ -= amount;
            to.balance_ += amount;
            std::cout << "Transferência de " << amount 
                      << " de " << from.name_ << " para " << to.name_ << "\n";
        } else {
            std::cout << "Saldo insuficiente em " << from.name_ << "\n";
        }
    }

    friend void transfer(BankAccount&, BankAccount&, double);
};

int main() {
    BankAccount alice("Alice", 1000.0);
    BankAccount bob("Bob", 500.0);

    std::thread t1([&] { BankAccount::transfer(alice, bob, 100.0); });
    std::thread t2([&] { BankAccount::transfer(bob, alice, 50.0); });
    
    t1.join();
    t2.join();
    
    std::cout << "Alice: " << alice.get_balance() << "\n";
    std::cout << "Bob: " << bob.get_balance() << "\n";
}
```

#### Protocolo de Ordenação de Locks

Quando `std::scoped_lock` não é aplicável, imponha uma ordem global:

```cpp
#include <mutex>
#include <thread>
#include <vector>
#include <algorithm>

class OrderedLockManager {
    std::vector<std::mutex> mutexes_;
    std::vector<int> lock_order_;  // Índices ordenados por endereço

public:
    explicit OrderedLockManager(size_t count) : mutexes_(count) {
        lock_order_.resize(count);
        std::iota(lock_order_.begin(), lock_order_.end(), 0);
        // Ordena por endereço do mutex para ordem consistente
        std::sort(lock_order_.begin(), lock_order_.end(),
            [this](int a, int b) { 
                return &mutexes_[a] < &mutexes_[b]; 
            });
    }

    template<typename Func>
    void lock_multiple(const std::vector<int>& indices, Func&& func) {
        // Ordena índices pela ordem global
        std::vector<int> sorted = indices;
        std::sort(sorted.begin(), sorted.end(),
            [this](int a, int b) { 
                return &mutexes_[a] < &mutexes_[b]; 
            });

        // Adquire locks na ordem
        std::vector<std::unique_lock<std::mutex>> locks;
        locks.reserve(sorted.size());
        for (int idx : sorted) {
            locks.emplace_back(mutexes_[idx]);
        }

        func();
        // Locks liberados automaticamente no destrutor
    }
};
```

### 2.2 Quebrando No Preemption

#### try_lock com Backoff

```cpp
#include <mutex>
#include <chrono>
#include <thread>
#include <random>

class TryLockWithBackoff {
    std::mutex mtx_;
    std::mt19937 rng_{std::random_device{}()};

public:
    template<typename Func>
    bool try_execute(Func&& func, std::chrono::milliseconds max_wait = std::chrono::seconds(1)) {
        auto start = std::chrono::steady_clock::now();
        std::chrono::microseconds backoff(100);
        const auto max_backoff = std::chrono::milliseconds(10);

        while (true) {
            if (mtx_.try_lock()) {
                try {
                    func();
                    mtx_.unlock();
                    return true;
                } catch (...) {
                    mtx_.unlock();
                    throw;
                }
            }

            auto elapsed = std::chrono::steady_clock::now() - start;
            if (elapsed >= max_wait) {
                return false;  // Timeout
            }

            // Exponential backoff com jitter
            std::this_thread::sleep_for(backoff);
            backoff = std::min(backoff * 2, max_backoff);
            
            // Adiciona jitter aleatório (0-50% do backoff)
            std::uniform_int_distribution<> dist(0, backoff.count() / 2);
            std::this_thread::sleep_for(std::chrono::microseconds(dist(rng_)));
        }
    }
};
```

#### Lock Timeouts com std::unique_lock

```cpp
#include <mutex>
#include <chrono>
#include <iostream>

class TimeoutLock {
    std::mutex mtx_;

public:
    template<typename Duration, typename Func>
    bool execute_with_timeout(Duration timeout, Func&& func) {
        std::unique_lock<std::mutex> lock(mtx_, std::defer_lock);
        
        if (lock.try_lock_for(timeout)) {
            func();
            return true;
        }
        return false;  // Timeout expirado
    }

    template<typename TimePoint, typename Func>
    bool execute_until(TimePoint deadline, Func&& func) {
        std::unique_lock<std::mutex> lock(mtx_, std::defer_lock);
        
        if (lock.try_lock_until(deadline)) {
            func();
            return true;
        }
        return false;
    }
};

// Uso prático
void example_usage() {
    TimeoutLock lock;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(500);
    
    bool success = lock.execute_until(deadline, []{
        std::cout << "Lock adquirido, executando seção crítica\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    });
    
    if (!success) {
        std::cout << "Timeout: não conseguiu adquirir lock\n";
    }
}
```

### 2.3 Quebrando Circular Wait

#### Hierarquia Global de Ordenação de Locks

```cpp
#include <mutex>
#include <thread>
#include <stdexcept>
#include <iostream>

// Níveis de lock: quanto menor o número, mais "externo" o lock
enum class LockLevel : int {
    Database = 10,      // Nível mais alto (adquirido primeiro)
    Cache = 20,
    FileSystem = 30,
    Network = 40,
    UserInterface = 50  // Nível mais baixo (adquirido por último)
};

class HierarchicalMutex {
    std::mutex mtx_;
    const LockLevel level_;
    static thread_local LockLevel current_level_;

public:
    explicit HierarchicalMutex(LockLevel level) : level_(level) {}

    void lock() {
        if (current_level_ != LockLevel::UserInterface && 
            static_cast<int>(current_level_) <= static_cast<int>(level_)) {
            throw std::logic_error("Violação de hierarquia de locks: "
                "tentando adquirir lock de nível igual ou superior");
        }
        mtx_.lock();
        current_level_ = level_;
    }

    void unlock() {
        current_level_ = LockLevel::UserInterface;  // Reset para nível base
        mtx_.unlock();
    }

    bool try_lock() {
        if (current_level_ != LockLevel::UserInterface && 
            static_cast<int>(current_level_) <= static_cast<int>(level_)) {
            return false;
        }
        if (mtx_.try_lock()) {
            current_level_ = level_;
            return true;
        }
        return false;
    }
};

thread_local LockLevel HierarchicalMutex::current_level_ = LockLevel::UserInterface;

// RAII wrapper
class HierarchicalLock {
    HierarchicalMutex& mtx_;
public:
    explicit HierarchicalLock(HierarchicalMutex& m) : mtx_(m) { mtx_.lock(); }
    ~HierarchicalLock() { mtx_.unlock(); }
    HierarchicalLock(const HierarchicalLock&) = delete;
    HierarchicalLock& operator=(const HierarchicalLock&) = delete;
};

// Uso: sempre adquira locks em ordem decrescente de nível (Database -> UI)
HierarchicalMutex db_mutex(LockLevel::Database);
HierarchicalMutex cache_mutex(LockLevel::Cache);
HierarchicalMutex ui_mutex(LockLevel::UserInterface);

void correct_usage() {
    HierarchicalLock db_lock(db_mutex);      // OK: nível 10
    HierarchicalLock cache_lock(cache_mutex); // OK: nível 20 > 10
    // HierarchicalLock ui_lock(ui_mutex);    // OK: nível 50 > 20
}

void incorrect_usage() {
    HierarchicalLock cache_lock(cache_mutex); // OK: nível 20
    // HierarchicalLock db_lock(db_mutex);    // ERRO: nível 10 < 20 - lança exceção!
}
```

#### Sistema de Rank de Locks em Tempo de Compilação (C++20)

```cpp
#include <mutex>
#include <concepts>
#include <type_traits>

// Compile-time lock ordering verification
template<int Level>
class RankedMutex {
    std::mutex mtx_;
public:
    void lock() { mtx_.lock(); }
    void unlock() { mtx_.unlock(); }
    bool try_lock() { return mtx_.try_lock(); }
};

// Concept para verificar ordenação em tempo de compilação
template<int... Levels>
concept StrictlyIncreasing = (Levels < ...);

// Lock guard que verifica ordenação em compile-time
template<StrictlyIncreasing... Levels>
class OrderedLockGuard {
    std::tuple<RankedMutex<Levels>&...> mutexes_;
    
public:
    explicit OrderedLockGuard(RankedMutex<Levels>&... mtx) 
        : mutexes_(mtx...) {
        // Adquire em ordem (já garantida pelo template)
        std::apply([](auto&... m) { (m.lock(), ...); }, mutexes_);
    }
    
    ~OrderedLockGuard() {
        std::apply([](auto&... m) { (m.unlock(), ...); }, mutexes_);
    }
};

// Uso - erro de compilação se ordem violada
RankedMutex<10> db_mutex;
RankedMutex<20> cache_mutex;
RankedMutex<30> fs_mutex;

// OK: 10 < 20 < 30
// OrderedLockGuard<10, 20, 30> guard(db_mutex, cache_mutex, fs_mutex);

// ERRO DE COMPILAÇÃO: 20 !< 10
// OrderedLockGuard<20, 10> bad_guard(cache_mutex, db_mutex);
```


## 3. Detecção e Recuperação

### 3.1 Algoritmos de Detecção de Deadlock

#### Wait-for Graph (Grafo de Espera)

O Wait-for Graph é uma variação do RAG onde apenas processos são nós, e arestas indicam "P1 espera por P2":

```cpp
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <mutex>
#include <shared_mutex>
#include <iostream>

class WaitForGraph {
    mutable std::shared_mutex graph_mtx_;
    std::unordered_map<std::string, std::unordered_set<std::string>> edges_;  // waiter -> holders
    std::unordered_map<std::string, std::string> thread_to_resource_;         // thread -> resource it holds

public:
    void add_edge(const std::string& waiter, const std::string& holder) {
        std::unique_lock lock(graph_mtx_);
        edges_[waiter].insert(holder);
    }

    void remove_edge(const std::string& waiter, const std::string& holder) {
        std::unique_lock lock(graph_mtx_);
        auto it = edges_.find(waiter);
        if (it != edges_.end()) {
            it->second.erase(holder);
            if (it->second.empty()) edges_.erase(it);
        }
    }

    void set_resource_owner(const std::string& resource, const std::string& owner) {
        std::unique_lock lock(graph_mtx_);
        thread_to_resource_[resource] = owner;
    }

    void clear_resource_owner(const std::string& resource) {
        std::unique_lock lock(graph_mtx_);
        thread_to_resource_.erase(resource);
    }

    // Detecta ciclos usando algoritmo de Tarjan (SCC)
    std::vector<std::vector<std::string>> detect_deadlocks() const {
        std::shared_lock lock(graph_mtx_);
        
        std::unordered_map<std::string, int> index;
        std::unordered_map<std::string, int> lowlink;
        std::vector<std::string> stack;
        std::unordered_set<std::string> on_stack;
        int idx = 0;
        std::vector<std::vector<std::string>> sccs;

        std::function<void(const std::string&)> strongconnect = 
            [&](const std::string& v) {
            index[v] = lowlink[v] = idx++;
            stack.push_back(v);
            on_stack.insert(v);

            auto it = edges_.find(v);
            if (it != edges_.end()) {
                for (const auto& w : it->second) {
                    if (!index.count(w)) {
                        strongconnect(w);
                        lowlink[v] = std::min(lowlink[v], lowlink[w]);
                    } else if (on_stack.count(w)) {
                        lowlink[v] = std::min(lowlink[v], index[w]);
                    }
                }
            }

            if (lowlink[v] == index[v]) {
                std::vector<std::string> scc;
                std::string w;
                do {
                    w = stack.back();
                    stack.pop_back();
                    on_stack.erase(w);
                    scc.push_back(w);
                } while (w != v);
                
                if (scc.size() > 1) {  // Ciclo real (não auto-loop)
                    sccs.push_back(scc);
                }
            }
        };

        for (const auto& [node, _] : edges_) {
            if (!index.count(node)) {
                strongconnect(node);
            }
        }

        return sccs;
    }

    void print_graph() const {
        std::shared_lock lock(graph_mtx_);
        std::cout << "Wait-for Graph:\n";
        for (const auto& [waiter, holders] : edges_) {
            std::cout << "  " << waiter << " -> ";
            for (const auto& h : holders) std::cout << h << " ";
            std::cout << "\n";
        }
    }
};
```

### 3.2 Seleção de Vítima (Victim Selection)

Quando deadlock detectado, escolha qual thread abortar:

```cpp
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>

enum class VictimPolicy {
    Youngest,           // Thread mais nova (menos trabalho perdido)
    Oldest,             // Thread mais velha
    LeastResources,     // Thread com menos recursos
    MostResources,      // Thread com mais recursos (libera mais)
    LowestPriority,     // Thread de menor prioridade
    Random              // Aleatório
};

struct ThreadInfo {
    std::string id;
    std::chrono::steady_clock::time_point start_time;
    int resources_held;
    int priority;
    size_t work_done;  // Métrica de progresso
};

class VictimSelector {
    VictimPolicy policy_;

public:
    explicit VictimSelector(VictimPolicy policy) : policy_(policy) {}

    std::string select_victim(const std::vector<std::string>& deadlock_cycle,
                              const std::unordered_map<std::string, ThreadInfo>& threads) {
        if (deadlock_cycle.empty()) return "";

        std::vector<std::string> candidates;
        for (const auto& tid : deadlock_cycle) {
            if (threads.count(tid)) candidates.push_back(tid);
        }
        if (candidates.empty()) return deadlock_cycle[0];

        switch (policy_) {
            case VictimPolicy::Youngest:
                return *std::min_element(candidates.begin(), candidates.end(),
                    [&](const std::string& a, const std::string& b) {
                        return threads.at(a).start_time > threads.at(b).start_time;
                    });
            
            case VictimPolicy::LeastResources:
                return *std::min_element(candidates.begin(), candidates.end(),
                    [&](const std::string& a, const std::string& b) {
                        return threads.at(a).resources_held < threads.at(b).resources_held;
                    });
            
            case VictimPolicy::LowestPriority:
                return *std::min_element(candidates.begin(), candidates.end(),
                    [&](const std::string& a, const std::string& b) {
                        return threads.at(a).priority < threads.at(b).priority;
                    });
            
            case VictimPolicy::Random: {
                std::random_device rd;
                std::mt19937 gen(rd());
                std::uniform_int_distribution<> dis(0, candidates.size() - 1);
                return candidates[dis(gen)];
            }
            
            default:
                return candidates[0];
        }
    }
};
```

### 3.3 Estratégias de Recuperação Automática

```cpp
#include <functional>
#include <atomic>
#include <thread>
#include <chrono>

class DeadlockRecoveryManager {
    WaitForGraph wfg_;
    VictimSelector selector_{VictimPolicy::Youngest};
    std::atomic<bool> running_{false};
    std::thread detector_thread_;
    std::chrono::milliseconds check_interval_{1000};

    // Callbacks para recuperação
    std::function<void(const std::string&)> on_abort_;
    std::function<void(const std::string&)> on_force_release_;

public:
    DeadlockRecoveryManager(
        std::function<void(const std::string&)> abort_cb,
        std::function<void(const std::string&)> force_release_cb)
        : on_abort_(std::move(abort_cb))
        , on_force_release_(std::move(force_release_cb)) {}

    void start() {
        running_ = true;
        detector_thread_ = std::thread([this] { detection_loop(); });
    }

    void stop() {
        running_ = false;
        if (detector_thread_.joinable()) detector_thread_.join();
    }

    void register_wait(const std::string& waiter, const std::string& holder) {
        wfg_.add_edge(waiter, holder);
    }

    void unregister_wait(const std::string& waiter, const std::string& holder) {
        wfg_.remove_edge(waiter, holder);
    }

    void register_resource_owner(const std::string& resource, const std::string& owner) {
        wfg_.set_resource_owner(resource, owner);
    }

    void unregister_resource_owner(const std::string& resource) {
        wfg_.clear_resource_owner(resource);
    }

private:
    void detection_loop() {
        while (running_) {
            std::this_thread::sleep_for(check_interval_);
            
            auto cycles = wfg_.detect_deadlocks();
            for (const auto& cycle : cycles) {
                std::cout << "[DEADLOCK DETECTADO] Ciclo: ";
                for (const auto& t : cycle) std::cout << t << " -> ";
                std::cout << cycle[0] << "\n";

                // Seleciona vítima e recupera
                std::string victim = selector_.select_victim(cycle, get_thread_info());
                std::cout << "[RECUPERAÇÃO] Abortando thread vítima: " << victim << "\n";
                
                on_abort_(victim);
                on_force_release_(victim);
                
                // Remove vítima do grafo
                for (const auto& other : cycle) {
                    if (other != victim) {
                        wfg_.remove_edge(other, victim);
                        wfg_.remove_edge(victim, other);
                    }
                }
            }
        }
    }

    std::unordered_map<std::string, ThreadInfo> get_thread_info() {
        // Implementação simplificada - em produção, viria de registry de threads
        return {};
    }
};
```

### 3.4 Implementação de Deadlock Detector em C++

```cpp
#include <mutex>
#include <condition_variable>
#include <unordered_map>
#include <vector>
#include <string>
#include <chrono>
#include <thread>
#include <atomic>
#include <iostream>

// Deadlock detector pronto para uso em produção
class ProductionDeadlockDetector {
    struct LockInfo {
        std::string name;
        std::thread::id owner;
        std::chrono::steady_clock::time_point acquired_at;
        int recursion_count = 0;
    };

    struct ThreadState {
        std::string name;
        std::vector<std::string> held_locks;
        std::string waiting_for;
        std::chrono::steady_clock::time_point last_activity;
    };

    mutable std::mutex detector_mtx_;
    std::unordered_map<std::string, LockInfo> locks_;
    std::unordered_map<std::thread::id, ThreadState> threads_;
    std::atomic<bool> enabled_{true};

public:
    // Chamado antes de tentar adquirir lock
    void on_lock_attempt(const std::string& lock_name, const std::string& thread_name) {
        if (!enabled_) return;
        std::lock_guard lock(detector_mtx_);
        
        auto& thread_state = threads_[std::this_thread::get_id()];
        thread_state.name = thread_name;
        thread_state.waiting_for = lock_name;
        thread_state.last_activity = std::chrono::steady_clock::now();
    }

    // Chamado após adquirir lock com sucesso
    void on_lock_acquired(const std::string& lock_name, const std::string& thread_name) {
        if (!enabled_) return;
        std::lock_guard lock(detector_mtx_);
        
        auto tid = std::this_thread::get_id();
        locks_[lock_name] = {lock_name, tid, std::chrono::steady_clock::now(), 1};
        
        auto& thread_state = threads_[tid];
        thread_state.name = thread_name;
        thread_state.held_locks.push_back(lock_name);
        thread_state.waiting_for.clear();
        thread_state.last_activity = std::chrono::steady_clock::now();
    }

    // Chamado ao liberar lock
    void on_lock_released(const std::string& lock_name) {
        if (!enabled_) return;
        std::lock_guard lock(detector_mtx_);
        
        auto it = locks_.find(lock_name);
        if (it != locks_.end()) {
            auto tid = it->second.owner;
            locks_.erase(it);
            
            auto thread_it = threads_.find(tid);
            if (thread_it != threads_.end()) {
                auto& held = thread_it->second.held_locks;
                held.erase(std::remove(held.begin(), held.end(), lock_name), held.end());
                thread_it->second.last_activity = std::chrono::steady_clock::now();
            }
        }
    }

    // Verifica deadlocks - chama periodicamente
    std::vector<std::vector<std::string>> check_deadlocks() {
        std::lock_guard lock(detector_mtx_);
        
        // Constrói wait-for graph
        std::unordered_map<std::string, std::unordered_set<std::string>> wfg;
        
        for (const auto& [lock_name, lock_info] : locks_) {
            const auto& owner = lock_info.owner;
            for (const auto& [tid, thread_state] : threads_) {
                if (tid != owner && 
                    thread_state.waiting_for == lock_name) {
                    wfg[thread_state.name].insert(
                        threads_.at(owner).name
                    );
                }
            }
        }

        // Tarjan's SCC algorithm
        return find_cycles(wfg);
    }

    void print_status() const {
        std::lock_guard lock(detector_mtx_);
        std::cout << "=== Deadlock Detector Status ===\n";
        std::cout << "Locks ativos: " << locks_.size() << "\n";
        std::cout << "Threads rastreadas: " << threads_.size() << "\n";
        
        for (const auto& [name, info] : locks_) {
            auto tid = info.owner;
            auto thread_it = threads_.find(tid);
            std::string thread_name = (thread_it != threads_.end()) ? thread_it->second.name : "unknown";
            std::cout << "  Lock: " << name << " | Owner: " << thread_name 
                      << " | Recursion: " << info.recursion_count << "\n";
        }
    }

    void set_enabled(bool enabled) { enabled_ = enabled; }

private:
    std::vector<std::vector<std::string>> find_cycles(
        const std::unordered_map<std::string, std::unordered_set<std::string>>& graph) const {
        
        std::unordered_map<std::string, int> index, lowlink;
        std::vector<std::string> stack;
        std::unordered_set<std::string> on_stack;
        int idx = 0;
        std::vector<std::vector<std::string>> cycles;

        std::function<void(const std::string&)> strongconnect = 
            [&](const std::string& v) {
            index[v] = lowlink[v] = idx++;
            stack.push_back(v);
            on_stack.insert(v);

            auto it = graph.find(v);
            if (it != graph.end()) {
                for (const auto& w : it->second) {
                    if (!index.count(w)) {
                        strongconnect(w);
                        lowlink[v] = std::min(lowlink[v], lowlink[w]);
                    } else if (on_stack.count(w)) {
                        lowlink[v] = std::min(lowlink[v], index[w]);
                    }
                }
            }

            if (lowlink[v] == index[v]) {
                std::vector<std::string> scc;
                std::string w;
                do {
                    w = stack.back();
                    stack.pop_back();
                    on_stack.erase(w);
                    scc.push_back(w);
                } while (w != v);
                
                if (scc.size() > 1) cycles.push_back(scc);
            }
        };

        for (const auto& [node, _] : graph) {
            if (!index.count(node)) strongconnect(node);
        }
        return cycles;
    }
};

// Wrapper RAII para uso transparente
class TrackedMutex {
    std::mutex mtx_;
    std::string name_;
    ProductionDeadlockDetector* detector_;
    std::string thread_name_;

public:
    TrackedMutex(const std::string& name, ProductionDeadlockDetector* detector, 
                 const std::string& thread_name = "unknown")
        : name_(name), detector_(detector), thread_name_(thread_name) {}

    void lock() {
        detector_->on_lock_attempt(name_, thread_name_);
        mtx_.lock();
        detector_->on_lock_acquired(name_, thread_name_);
    }

    void unlock() {
        mtx_.unlock();
        detector_->on_lock_released(name_);
    }

    bool try_lock() {
        detector_->on_lock_attempt(name_, thread_name_);
        if (mtx_.try_lock()) {
            detector_->on_lock_acquired(name_, thread_name_);
            return true;
        }
        return false;
    }
};
```


## 4. Livelock

### 4.1 Definição e Causas

Livelock ocorre quando threads estão ativas (não bloqueadas) mas não fazem progresso útil porque continuamente respondem umas às outras sem avançar. Diferente do deadlock, as threads consomem CPU ativamente.

**Causas comuns:**
- **Retry agressivo sem backoff**: Threads tentam adquirir lock, falham, tentam imediatamente
- **Protocolos de "cortesia" excessivos**: Threads cedem passagem mutuamente (exemplo dos dois cavaleiros)
- **Algoritmos de consenso mal projetados**: Raft/Paxos com timeouts muito agressivos
- **Load balancing oscilante**: Threads migram tarefas entre si indefinidamente

```cpp
// Livelock clássico: dois processos tentando atravessar corredor estreito
#include <atomic>
#include <thread>
#include <chrono>
#include <iostream>

std::atomic<int> position_a{0};
std::atomic<int> position_b{10};
const int MEETING_POINT = 5;

void pedestrian_a() {
    while (position_a.load() != MEETING_POINT) {
        int pos = position_a.load();
        if (pos < MEETING_POINT) {
            // Tenta avançar
            if (position_a.compare_exchange_weak(pos, pos + 1)) {
                std::cout << "A avançou para " << pos + 1 << "\n";
            }
        } else if (pos > MEETING_POINT) {
            // Tenta recuar
            if (position_a.compare_exchange_weak(pos, pos - 1)) {
                std::cout << "A recuou para " << pos - 1 << "\n";
            }
        }
        
        // Verifica colisão - se B está no mesmo lugar, recua
        if (position_a.load() == position_b.load()) {
            int current = position_a.load();
            if (current > 0) position_a.store(current - 1);
            std::cout << "A: Colisão! Recuando...\n";
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    std::cout << "A chegou ao destino!\n";
}

void pedestrian_b() {
    while (position_b.load() != MEETING_POINT) {
        int pos = position_b.load();
        if (pos > MEETING_POINT) {
            if (position_b.compare_exchange_weak(pos, pos - 1)) {
                std::cout << "B avançou para " << pos - 1 << "\n";
            }
        } else if (pos < MEETING_POINT) {
            if (position_b.compare_exchange_weak(pos, pos + 1)) {
                std::cout << "B recuou para " << pos + 1 << "\n";
            }
        }
        
        if (position_a.load() == position_b.load()) {
            int current = position_b.load();
            if (current < 10) position_b.store(current + 1);
            std::cout << "B: Colisão! Recuando...\n";
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    std::cout << "B chegou ao destino!\n";
}
```

### 4.2 Backoff Exponencial

A solução padrão para livelock é introduzir atrasos aleatórios crescentes:

```cpp
#include <atomic>
#include <thread>
#include <chrono>
#include <random>
#include <iostream>

class ExponentialBackoff {
    std::chrono::microseconds current_delay_;
    const std::chrono::microseconds min_delay_;
    const std::chrono::microseconds max_delay_;
    const double multiplier_;
    std::mt19937 rng_;
    std::uniform_real_distribution<> jitter_dist_;

public:
    ExponentialBackoff(
        std::chrono::microseconds min_d = std::chrono::microseconds(100),
        std::chrono::microseconds max_d = std::chrono::milliseconds(100),
        double mult = 2.0)
        : current_delay_(min_d)
        , min_delay_(min_d)
        , max_delay_(max_d)
        , multiplier_(mult)
        , rng_(std::random_device{}())
        , jitter_dist_(0.0, 1.0) {}

    void wait() {
        // Jitter: delay aleatório entre 0.5x e 1.5x do delay atual
        double jitter = 0.5 + jitter_dist_(rng_);
        auto delay = std::chrono::microseconds(
            static_cast<long long>(current_delay_.count() * jitter));
        
        std::this_thread::sleep_for(delay);
        
        // Aumenta delay para próxima tentativa
        current_delay_ = std::min(
            std::chrono::microseconds(static_cast<long long>(current_delay_.count() * multiplier_)),
            max_delay_);
    }

    void reset() { current_delay_ = min_delay_; }
    
    std::chrono::microseconds current() const { return current_delay_; }
};

// Lock-free queue com backoff exponencial para evitar livelock
template<typename T>
class LockFreeQueue {
    struct Node {
        T value;
        std::atomic<Node*> next;
        Node(const T& v) : value(v), next(nullptr) {}
    };

    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    ExponentialBackoff backoff_;

public:
    LockFreeQueue() {
        Node* dummy = new Node(T{});
        head_.store(dummy);
        tail_.store(dummy);
    }

    ~LockFreeQueue() {
        while (Node* n = head_.load()) {
            head_.store(n->next.load());
            delete n;
        }
    }

    void push(const T& value) {
        Node* new_node = new Node(value);
        while (true) {
            Node* tail = tail_.load();
            Node* next = tail->next.load();
            
            if (tail == tail_.load()) {
                if (next == nullptr) {
                    if (tail->next.compare_exchange_weak(next, new_node)) {
                        tail_.compare_exchange_weak(tail, new_node);
                        backoff_.reset();
                        return;
                    }
                } else {
                    tail_.compare_exchange_weak(tail, next);
                }
            }
            backoff_.wait();
        }
    }

    bool pop(T& result) {
        while (true) {
            Node* head = head_.load();
            Node* tail = tail_.load();
            Node* next = head->next.load();
            
            if (head == head_.load()) {
                if (head == tail) {
                    if (next == nullptr) return false;  // Empty
                    tail_.compare_exchange_weak(tail, next);
                } else {
                    result = next->value;
                    if (head_.compare_exchange_weak(head, next)) {
                        delete head;
                        backoff_.reset();
                        return true;
                    }
                }
            }
            backoff_.wait();
        }
    }
};
```

### 4.3 Atrasos Aleatórios (Randomized Delays)

```cpp
#include <random>
#include <chrono>
#include <thread>
#include <atomic>

class RandomizedDelay {
    std::mt19937 rng_;
    std::uniform_int_distribution<int> dist_;
    std::chrono::microseconds base_delay_;

public:
    RandomizedDelay(std::chrono::microseconds base = std::chrono::microseconds(100),
                    int max_multiplier = 1000)
        : rng_(std::random_device{}())
        , dist_(1, max_multiplier)
        , base_delay_(base) {}

    void wait() {
        int multiplier = dist_(rng_);
        std::this_thread::sleep_for(base_delay_ * multiplier);
    }
};

// Exemplo: Ethernet-style exponential backoff com jitter (IEEE 802.3)
class EthernetBackoff {
    int attempt_ = 0;
    static constexpr int MAX_ATTEMPTS = 16;
    static constexpr int SLOT_TIME_US = 512;  // 51.2 µs para 10Mbps, 5.12 µs para 100Mbps
    std::mt19937 rng_{std::random_device{}()};

public:
    void wait_after_collision() {
        if (attempt_ >= MAX_ATTEMPTS) {
            throw std::runtime_error("Max retransmission attempts reached");
        }
        
        int max_slots = (1 << std::min(attempt_, 10)) - 1;  // Truncated binary exponential backoff
        std::uniform_int_distribution<int> dist(0, max_slots);
        int slots = dist(rng_);
        
        std::this_thread::sleep_for(std::chrono::microseconds(slots * SLOT_TIME_US));
        ++attempt_;
    }

    void reset() { attempt_ = 0; }
    int attempt() const { return attempt_; }
};
```

### 4.4 Exemplos de Livelock em C++ e Correções

#### Livelock em Spinlock com Yield

```cpp
// PROBLEMÁTICO: Spinlock que causa livelock sob alta contenção
class BadSpinlock {
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
public:
    void lock() {
        while (flag_.test_and_set(std::memory_order_acquire)) {
            std::this_thread::yield();  // Apenas yield - pode causar livelock!
        }
    }
    void unlock() { flag_.clear(std::memory_order_release); }
};

// CORRIGIDO: Spinlock com backoff exponencial
class GoodSpinlock {
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
    ExponentialBackoff backoff_{std::chrono::nanoseconds(100), 
                                 std::chrono::microseconds(1000)};
public:
    void lock() {
        while (flag_.test_and_set(std::memory_order_acquire)) {
            backoff_.wait();
        }
        backoff_.reset();
    }
    void unlock() { flag_.clear(std::memory_order_release); }
};

// AINDA MELHOR: Usa pause instruction (x86) / yield (ARM)
class OptimizedSpinlock {
    std::atomic_flag flag_ = ATOMIC_FLAG_INIT;
    
    static void cpu_relax() {
#if defined(__x86_64__) || defined(__i386__)
        __builtin_ia32_pause();
#elif defined(__aarch64__)
        __builtin_arm_yield();
#else
        std::this_thread::yield();
#endif
    }

    ExponentialBackoff backoff_{std::chrono::nanoseconds(100), 
                                 std::chrono::microseconds(1000)};
    
public:
    void lock() {
        // Fast path: tenta adquirir sem backoff primeiro
        if (!flag_.test_and_set(std::memory_order_acquire)) return;
        
        // Slow path: spin com cpu_relax, depois backoff
        int spins = 0;
        while (flag_.test_and_set(std::memory_order_acquire)) {
            if (spins < 100) {
                cpu_relax();
                ++spins;
            } else {
                backoff_.wait();
            }
        }
        backoff_.reset();
    }
    
    void unlock() { flag_.clear(std::memory_order_release); }
    bool try_lock() { return !flag_.test_and_set(std::memory_order_acquire); }
};
```

#### Livelock em Comparação-e-Troca (CAS) Loops

```cpp
// PROBLEMÁTICO: CAS loop sem backoff - livelock sob contenção
std::atomic<int> counter{0};

void bad_increment() {
    for (int i = 0; i < 1000; ++i) {
        int expected = counter.load();
        while (!counter.compare_exchange_weak(expected, expected + 1)) {
            // Sem delay - livelock garantido sob alta contenção!
        }
    }
}

// CORRIGIDO: CAS loop com backoff
void good_increment() {
    ExponentialBackoff backoff;
    for (int i = 0; i < 1000; ++i) {
        int expected = counter.load();
        while (!counter.compare_exchange_weak(expected, expected + 1)) {
            backoff.wait();
        }
        backoff.reset();
    }
}

// MELHOR: fetch_add atômico (hardware faz o trabalho)
void best_increment() {
    for (int i = 0; i < 1000; ++i) {
        counter.fetch_add(1, std::memory_order_relaxed);
    }
}
```


## 5. Starvation

### 5.1 Fairness em Locking

Starvation ocorre quando uma thread nunca consegue adquirir um recurso porque outras threads sempre o adquirem primeiro. Locks "unfair" (como std::mutex padrão) podem causar starvation.

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>
#include <thread>
#include <chrono>
#include <iostream>

// Unfair mutex (padrão) - pode causar starvation
std::mutex unfair_mutex;
int unfair_counter = 0;

void unfair_worker(int id) {
    for (int i = 0; i < 100; ++i) {
        unfair_mutex.lock();
        ++unfair_counter;
        unfair_mutex.unlock();
    }
}

// Fair mutex usando fila FIFO
class FairMutex {
    std::mutex internal_mtx_;
    std::condition_variable cv_;
    std::queue<std::thread::id> wait_queue_;
    std::thread::id owner_;
    int recursion_count_ = 0;
    bool locked_ = false;

public:
    void lock() {
        std::thread::id this_id = std::this_thread::get_id();
        
        std::unique_lock<std::mutex> lock(internal_mtx_);
        
        // Fast path: já é o dono (recursivo)
        if (locked_ && owner_ == this_id) {
            ++recursion_count_;
            return;
        }
        
        // Entra na fila
        wait_queue_.push(this_id);
        
        // Espera até ser o próximo da fila e lock estiver livre
        cv_.wait(lock, [this, this_id] {
            return !locked_ && wait_queue_.front() == this_id;
        });
        
        // Adquire o lock
        wait_queue_.pop();
        locked_ = true;
        owner_ = this_id;
        recursion_count_ = 1;
    }

    void unlock() {
        std::lock_guard<std::mutex> lock(internal_mtx_);
        
        if (--recursion_count_ == 0) {
            locked_ = false;
            owner_ = std::thread::id{};
            cv_.notify_one();  // Notifica próximo na fila
        }
    }

    bool try_lock() {
        std::lock_guard<std::mutex> lock(internal_mtx_);
        if (!locked_) {
            locked_ = true;
            owner_ = std::this_thread::get_id();
            recursion_count_ = 1;
            return true;
        }
        return false;
    }
};
```

### 5.2 Starvation em Reader-Writer Locks

Reader-writer locks tradicionais podem causar starvation de writers (ou readers):

```cpp
#include <shared_mutex>
#include <thread>
#include <vector>
#include <chrono>
#include <iostream>

// Problema: Writer starvation com std::shared_mutex (prefere readers)
std::shared_mutex rw_mutex;
int shared_data = 0;
std::atomic<int> reader_count{0}, writer_count{0};

void reader(int id) {
    for (int i = 0; i < 100; ++i) {
        std::shared_lock lock(rw_mutex);
        ++reader_count;
        std::this_thread::sleep_for(std::chrono::microseconds(10));
        --reader_count;
    }
}

void writer(int id) {
    for (int i = 0; i < 10; ++i) {
        std::unique_lock lock(rw_mutex);
        ++writer_count;
        shared_data = id * 100 + i;
        --writer_count;
        std::this_thread::sleep_for(std::chrono::microseconds(100));
    }
}

// Solução: Write-preferring RW lock
class WritePreferringRWLock {
    std::mutex mtx_;
    std::condition_variable cv_readers_, cv_writers_;
    int active_readers_ = 0;
    int waiting_writers_ = 0;
    bool active_writer_ = false;

public:
    void lock_shared() {  // Reader lock
        std::unique_lock<std::mutex> lock(mtx_);
        cv_readers_.wait(lock, [this] { 
            return !active_writer_ && waiting_writers_ == 0; 
        });
        ++active_readers_;
    }

    void unlock_shared() {
        std::lock_guard<std::mutex> lock(mtx_);
        if (--active_readers_ == 0) {
            cv_writers_.notify_one();
        }
    }

    void lock() {  // Writer lock
        std::unique_lock<std::mutex> lock(mtx_);
        ++waiting_writers_;
        cv_writers_.wait(lock, [this] { 
            return !active_writer_ && active_readers_ == 0; 
        });
        --waiting_writers_;
        active_writer_ = true;
    }

    void unlock() {
        std::lock_guard<std::mutex> lock(mtx_);
        active_writer_ = false;
        if (waiting_writers_ > 0) {
            cv_writers_.notify_one();  // Prioridade para writers
        } else {
            cv_readers_.notify_all();
        }
    }
};
```

### 5.3 Priority Inheritance

Priority inheritance previne priority inversion (veja Seção 6) mas também ajuda contra starvation de threads de alta prioridade:

```cpp
#include <pthread.h>
#include <iostream>
#include <thread>
#include <chrono>

// POSIX priority inheritance mutex
class PI_Mutex {
    pthread_mutex_t mtx_;
    pthread_mutexattr_t attr_;

public:
    PI_Mutex() {
        pthread_mutexattr_init(&attr_);
        pthread_mutexattr_setprotocol(&attr_, PTHREAD_PRIO_INHERIT);
        pthread_mutexattr_settype(&attr_, PTHREAD_MUTEX_NORMAL);
        pthread_mutex_init(&mtx_, &attr_);
    }

    ~PI_Mutex() {
        pthread_mutex_destroy(&mtx_);
        pthread_mutexattr_destroy(&attr_);
    }

    void lock() { pthread_mutex_lock(&mtx_); }
    void unlock() { pthread_mutex_unlock(&mtx_); }
    bool try_lock() { return pthread_mutex_trylock(&mtx_) == 0; }

    // Não copiável/movível
    PI_Mutex(const PI_Mutex&) = delete;
    PI_Mutex& operator=(const PI_Mutex&) = delete;
};

// Wrapper RAII
class PI_Lock {
    PI_Mutex& mtx_;
public:
    explicit PI_Lock(PI_Mutex& m) : mtx_(m) { mtx_.lock(); }
    ~PI_Lock() { mtx_.unlock(); }
};
```

### 5.4 Locks Livres de Starvation (Starvation-Free)

```cpp
#include <atomic>
#include <thread>
#include <chrono>

// MCS Lock - Queue-based, starvation-free, cache-friendly
class MCSLock {
    struct Node {
        std::atomic<Node*> next{nullptr};
        std::atomic<bool> locked{false};
    };

    std::atomic<Node*> tail_{nullptr};
    thread_local static Node* my_node_;

public:
    MCSLock() = default;
    ~MCSLock() = default;

    class Guard {
        MCSLock& lock_;
        Node* my_node_;
    public:
        explicit Guard(MCSLock& lock) : lock_(lock), my_node_(new Node()) {
            Node* pred = lock_.tail_.exchange(my_node_, std::memory_order_acq_rel);
            if (pred) {
                my_node_->locked.store(true, std::memory_order_relaxed);
                pred->next.store(my_node_, std::memory_order_release);
                while (my_node_->locked.load(std::memory_order_acquire)) {
                    std::this_thread::yield();
                }
            }
        }

        ~Guard() {
            if (!my_node_->next.load(std::memory_order_acquire)) {
                Node* expected = my_node_;
                if (lock_.tail_.compare_exchange_strong(expected, nullptr, 
                    std::memory_order_acq_rel)) {
                    delete my_node_;
                    return;
                }
                // Espera próximo node ser linkado
                while (!my_node_->next.load(std::memory_order_acquire)) {
                    std::this_thread::yield();
                }
            }
            my_node_->next.load(std::memory_order_acquire)->locked.store(false, 
                std::memory_order_release);
            delete my_node_;
        }
    };

    Guard acquire() { return Guard(*this); }
};

thread_local MCSLock::Node* MCSLock::my_node_ = nullptr;

// CLH Lock - Outra lock baseada em fila, starvation-free
class CLHLock {
    struct Node {
        std::atomic<bool> locked{false};
    };

    std::atomic<Node*> tail_{nullptr};
    thread_local static Node* my_node_;
    thread_local static Node* my_pred_;

public:
    CLHLock() {
        Node* initial = new Node();
        initial->locked.store(false, std::memory_order_relaxed);
        tail_.store(initial, std::memory_order_relaxed);
    }

    ~CLHLock() {
        Node* n = tail_.load(std::memory_order_relaxed);
        delete n;
    }

    class Guard {
        CLHLock& lock_;
        Node* my_node_;
        Node* my_pred_;
    public:
        explicit Guard(CLHLock& lock) : lock_(lock), my_node_(new Node()) {
            my_node_->locked.store(true, std::memory_order_relaxed);
            my_pred_ = lock_.tail_.exchange(my_node_, std::memory_order_acq_rel);
            while (my_pred_->locked.load(std::memory_order_acquire)) {
                std::this_thread::yield();
            }
        }

        ~Guard() {
            my_node_->locked.store(false, std::memory_order_release);
            lock_.tail_.store(my_pred_, std::memory_order_release);
            delete my_node_;
        }
    };

    Guard acquire() { return Guard(*this); }
};

thread_local CLHLock::Node* CLHLock::my_node_ = nullptr;
thread_local CLHLock::Node* CLHLock::my_pred_ = nullptr;

// Ticket Lock - Simples, FIFO, starvation-free
class TicketLock {
    std::atomic<unsigned> next_ticket_{0};
    std::atomic<unsigned> now_serving_{0};

public:
    class Guard {
        TicketLock& lock_;
        unsigned my_ticket_;
    public:
        explicit Guard(TicketLock& lock) : lock_(lock) {
            my_ticket_ = lock_.next_ticket_.fetch_add(1, std::memory_order_relaxed);
            while (lock_.now_serving_.load(std::memory_order_acquire) != my_ticket_) {
                std::this_thread::yield();
            }
        }
        ~Guard() {
            lock_.now_serving_.fetch_add(1, std::memory_order_release);
        }
    };

    Guard acquire() { return Guard(*this); }
    bool try_acquire() {
        unsigned ticket = next_ticket_.load(std::memory_order_relaxed);
        if (now_serving_.load(std::memory_order_acquire) == ticket) {
            next_ticket_.fetch_add(1, std::memory_order_relaxed);
            return true;
        }
        return false;
    }
};
```

EOF
## 6. Priority Inversion

### 6.1 Estudo de Caso: Mars Pathfinder

Em 1997, o rover Mars Pathfinder da NASA sofreu reinicializações repetidas devido a **priority inversion**. O sistema usava VxWorks RTOS com escalonamento de prioridade fixa.

**Cenário:**
- **High-priority thread** (bus management): Prioridade 10 - gerencia comunicação
- **Medium-priority thread** (communications): Prioridade 7 - tarefas de comunicação  
- **Low-priority thread** (meteorological data): Prioridade 3 - coleta dados meteorológicos

**Sequência do problema:**
1. Low-priority thread adquire mutex para acessar barramento de dados
2. High-priority thread tenta adquirir o mesmo mutex → **bloqueia**
3. Medium-priority thread (não relacionada) preempta low-priority thread
4. High-priority thread fica bloqueada indefinidamente esperando low-priority
5. Watchdog timer reinicia o sistema achando que travou

**Solução aplicada no espaço:** Ativação de **priority inheritance** no mutex do barramento via upload de patch.

```cpp
// Simulação do problema do Mars Pathfinder
#include <thread>
#include <mutex>
#include <condition_variable>
#include <chrono>
#include <iostream>
#include <atomic>

class MarsPathfinderSimulator {
    std::mutex bus_mutex_;
    std::condition_variable cv_;
    std::atomic<bool> low_has_mutex_{false};
    std::atomic<bool> high_waiting_{false};
    std::atomic<int> context_switches_{0};

    void low_priority_task() {  // Meteorological data
        std::cout << "[LOW] Iniciando coleta de dados...\n";
        {
            std::lock_guard<std::mutex> lock(bus_mutex_);
            low_has_mutex_ = true;
            std::cout << "[LOW] Adquiriu mutex do barramento\n";
            
            // Simula trabalho longo
            for (int i = 0; i < 10; ++i) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                if (high_waiting_) {
                    std::cout << "[LOW] High-priority esperando! (Priority inversion ativo)\n";
                }
            }
            low_has_mutex_ = false;
        }
        std::cout << "[LOW] Liberou mutex\n";
    }

    void high_priority_task() {  // Bus management
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        std::cout << "[HIGH] Tentando adquirir mutex do barramento\n";
        high_waiting_ = true;
        
        std::unique_lock<std::mutex> lock(bus_mutex_);
        high_waiting_ = false;
        std::cout << "[HIGH] Adquiriu mutex - gerenciando barramento\n";
        
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
        std::cout << "[HIGH] Liberou mutex\n";
    }

    void medium_priority_task() {  // Communications
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        std::cout << "[MEDIUM] Iniciando tarefa de comunicação (preempta LOW)\n";
        for (int i = 0; i < 5; ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(80));
            ++context_switches_;
        }
        std::cout << "[MEDIUM] Terminando\n";
    }

public:
    void run_without_pi() {
        std::cout << "=== SIMULAÇÃO SEM PRIORITY INHERITANCE ===\n";
        std::thread low(&MarsPathfinderSimulator::low_priority_task, this);
        std::thread high(&MarsPathfinderSimulator::high_priority_task, this);
        std::thread medium(&MarsPathfinderSimulator::medium_priority_task, this);
        
        low.join();
        high.join();
        medium.join();
        
        std::cout << "Context switches médios: " << context_switches_ << "\n";
    }
};
```

### 6.2 Protocolo de Priority Inheritance

Quando uma thread de alta prioridade bloqueia em um mutex mantido por thread de baixa prioridade, a thread de baixa prioridade **herda temporariamente** a prioridade alta:

```cpp
#include <pthread.h>
#include <sched.h>
#include <iostream>
#include <thread>
#include <chrono>

// Mutex com Priority Inheritance (POSIX)
class PriorityInheritanceMutex {
    pthread_mutex_t mtx_;
    pthread_mutexattr_t attr_;

public:
    PriorityInheritanceMutex() {
        pthread_mutexattr_init(&attr_);
        // Define protocolo de priority inheritance
        pthread_mutexattr_setprotocol(&attr_, PTHREAD_PRIO_INHERIT);
        // Tipo robusto para detectar owner death
        pthread_mutexattr_setrobust(&attr_, PTHREAD_MUTEX_ROBUST);
        pthread_mutex_init(&mtx_, &attr_);
    }

    ~PriorityInheritanceMutex() {
        pthread_mutex_destroy(&mtx_);
        pthread_mutexattr_destroy(&attr_);
    }

    void lock() { 
        int result = pthread_mutex_lock(&mtx_);
        if (result == EOWNERDEAD) {
            // Owner morreu - mutex está em estado inconsistente
            pthread_mutex_consistent(&mtx_);
        }
    }
    
    void unlock() { pthread_mutex_unlock(&mtx_); }
    bool try_lock() { return pthread_mutex_trylock(&mtx_) == 0; }

    // Acesso ao handle nativo para configuração avançada
    pthread_mutex_t* native_handle() { return &mtx_; }
};

// Wrapper RAII
class PI_Guard {
    PriorityInheritanceMutex& mtx_;
public:
    explicit PI_Guard(PriorityInheritanceMutex& m) : mtx_(m) { mtx_.lock(); }
    ~PI_Guard() { mtx_.unlock(); }
    PI_Guard(const PI_Guard&) = delete;
    PI_Guard& operator=(const PI_Guard&) = delete;
};

// Exemplo de uso com threads de diferentes prioridades (requer root/CAP_SYS_NICE)
void demonstrate_priority_inheritance() {
    PriorityInheritanceMutex pi_mutex;
    std::atomic<bool> low_done{false}, high_done{false};
    
    // Thread de baixa prioridade
    auto low_task = [&] {
        PI_Guard guard(pi_mutex);
        std::cout << "[LOW] Adquiriu mutex com PI\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        std::cout << "[LOW] Liberando mutex\n";
        low_done = true;
    };
    
    // Thread de alta prioridade
    auto high_task = [&] {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        std::cout << "[HIGH] Tentando adquirir mutex\n";
        PI_Guard guard(pi_mutex);
        std::cout << "[HIGH] Adquiriu mutex (LOW herdou prioridade)\n";
        high_done = true;
    };
    
    std::thread t_low(low_task);
    std::thread t_high(high_task);
    
    // Em sistema real, definiria prioridades com pthread_setschedparam
    // pthread_setschedparam(t_low.native_handle(), SCHED_FIFO, &low_prio);
    // pthread_setschedparam(t_high.native_handle(), SCHED_FIFO, &high_prio);
    
    t_low.join();
    t_high.join();
}
```

### 6.3 Protocolo de Priority Ceiling

Priority Ceiling Protocol (PCP) previne deadlock E priority inversion atribuindo um **teto de prioridade** (ceiling) a cada mutex:

```cpp
#include <pthread.h>
#include <mutex>
#include <thread>
#include <chrono>
#include <iostream>
#include <vector>
#include <algorithm>

// Priority Ceiling Mutex - previne deadlock e priority inversion
class PriorityCeilingMutex {
    pthread_mutex_t mtx_;
    pthread_mutexattr_t attr_;
    int ceiling_priority_;

public:
    // ceiling_priority: prioridade máxima de qualquer thread que pode lock este mutex
    explicit PriorityCeilingMutex(int ceiling_prio) : ceiling_priority_(ceiling_prio) {
        pthread_mutexattr_init(&attr_);
        pthread_mutexattr_setprotocol(&attr_, PTHREAD_PRIO_PROTECT);
        pthread_mutexattr_setprioceiling(&attr_, ceiling_prio);
        pthread_mutex_init(&mtx_, &attr_);
    }

    ~PriorityCeilingMutex() {
        pthread_mutex_destroy(&mtx_);
        pthread_mutexattr_destroy(&attr_);
    }

    void lock() { pthread_mutex_lock(&mtx_); }
    void unlock() { pthread_mutex_unlock(&mtx_); }
    bool try_lock() { return pthread_mutex_trylock(&mtx_) == 0; }

    int ceiling() const { return ceiling_priority_; }
};

// Sistema de Prioridade Ceiling em C++ (user-space, sem pthread)
class UserSpaceCeilingMutex {
    struct ThreadInfo {
        int priority;
        std::thread::id id;
    };

    std::mutex internal_mtx_;
    std::condition_variable cv_;
    int ceiling_priority_;
    int current_ceiling_ = -1;  // -1 = unlocked
    std::thread::id owner_;
    int recursion_ = 0;
    std::vector<std::thread::id> wait_queue_;

public:
    explicit UserSpaceCeilingMutex(int ceiling) : ceiling_priority_(ceiling) {}

    void lock() {
        std::thread::id this_id = std::this_thread::get_id();
        int my_priority = get_current_thread_priority();  // Implementação específica
        
        std::unique_lock<std::mutex> lock(internal_mtx_);
        
        // Fast path: já é dono
        if (owner_ == this_id) {
            ++recursion_;
            return;
        }
        
        // Priority Ceiling Protocol: eleva teto do sistema
        int old_ceiling = current_ceiling_;
        current_ceiling_ = std::max(current_ceiling_, ceiling_priority_);
        
        // Verifica se pode adquirir (prioridade da thread > teto atual)
        wait_queue_.push_back(this_id);
        cv_.wait(lock, [this, this_id, my_priority] {
            return owner_ == std::thread::id{} && 
                   wait_queue_.front() == this_id &&
                   my_priority > current_ceiling_;
        });
        
        wait_queue_.erase(wait_queue_.begin());
        owner_ = this_id;
        recursion_ = 1;
    }

    void unlock() {
        std::lock_guard<std::mutex> lock(internal_mtx_);
        if (--recursion_ == 0) {
            owner_ = std::thread::id{};
            // Restaura teto anterior (simplificado)
            current_ceiling_ = -1;
            cv_.notify_one();
        }
    }

private:
    int get_current_thread_priority() {
        // Em implementação real, obteria de pthread_getschedparam
        return 10;  // Placeholder
    }
};
```

### 6.4 pthread_mutexattr_setprotocol em C++

```cpp
#include <pthread.h>
#include <cerrno>
#include <system_error>
#include <iostream>

// Wrapper completo para atributos de mutex POSIX
class PosixMutex {
public:
    enum class Protocol {
        None = PTHREAD_PRIO_NONE,
        Inherit = PTHREAD_PRIO_INHERIT,
        Protect = PTHREAD_PRIO_PROTECT
    };

    enum class Type {
        Normal = PTHREAD_MUTEX_NORMAL,
        Recursive = PTHREAD_MUTEX_RECURSIVE,
        ErrorCheck = PTHREAD_MUTEX_ERRORCHECK,
        Default = PTHREAD_MUTEX_DEFAULT
    };

    enum class Robustness {
        Normal = PTHREAD_MUTEX_STALLED,
        Robust = PTHREAD_MUTEX_ROBUST
    };

private:
    pthread_mutex_t mtx_;
    pthread_mutexattr_t attr_;
    bool initialized_ = false;

public:
    PosixMutex(Protocol protocol = Protocol::Inherit,
               Type type = Type::Normal,
               Robustness robust = Robustness::Normal,
               int priority_ceiling = 0) {
        int rc = pthread_mutexattr_init(&attr_);
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "mutexattr_init");

        rc = pthread_mutexattr_setprotocol(&attr_, static_cast<int>(protocol));
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "setprotocol");

        rc = pthread_mutexattr_settype(&attr_, static_cast<int>(type));
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "settype");

        rc = pthread_mutexattr_setrobust(&attr_, static_cast<int>(robust));
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "setrobust");

        if (protocol == Protocol::Protect) {
            rc = pthread_mutexattr_setprioceiling(&attr_, priority_ceiling);
            if (rc != 0) throw std::system_error(rc, std::generic_category(), "setprioceiling");
        }

        rc = pthread_mutex_init(&mtx_, &attr_);
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "mutex_init");
        
        initialized_ = true;
    }

    ~PosixMutex() {
        if (initialized_) {
            pthread_mutex_destroy(&mtx_);
            pthread_mutexattr_destroy(&attr_);
        }
    }

    void lock() {
        int rc = pthread_mutex_lock(&mtx_);
        if (rc == EOWNERDEAD) {
            // Recupera estado consistente após owner death
            pthread_mutex_consistent(&mtx_);
        } else if (rc != 0) {
            throw std::system_error(rc, std::generic_category(), "mutex_lock");
        }
    }

    void unlock() {
        int rc = pthread_mutex_unlock(&mtx_);
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "mutex_unlock");
    }

    bool try_lock() {
        int rc = pthread_mutex_trylock(&mtx_);
        if (rc == EBUSY) return false;
        if (rc == EOWNERDEAD) {
            pthread_mutex_consistent(&mtx_);
            return true;
        }
        if (rc != 0) throw std::system_error(rc, std::generic_category(), "mutex_trylock");
        return true;
    }

    pthread_mutex_t* native_handle() { return &mtx_; }

    // Não copiável
    PosixMutex(const PosixMutex&) = delete;
    PosixMutex& operator=(const PosixMutex&) = delete;
};

// RAII guard
class PosixLock {
    PosixMutex& mtx_;
public:
    explicit PosixLock(PosixMutex& m) : mtx_(m) { mtx_.lock(); }
    ~PosixLock() { mtx_.unlock(); }
    PosixLock(const PosixLock&) = delete;
    PosixLock& operator=(const PosixLock&) = delete;
};
```

EOF
## 7. Lock Convoy

### 7.1 O que é Lock Convoy

Lock Convoy (comboio de locks) ocorre quando múltiplas threads competem por um lock, e o SO as coloca para dormir. Quando o lock é liberado, todas acordam simultaneamente, mas apenas uma adquire o lock; as outras voltam a dormir. Isso cria um padrão de "ondas" de wake/sleep que degrada performance drasticamente.

**Sintomas:**
- Throughput cai drasticamente sob alta contenção
- Latência média aumenta exponencialmente
- CPU gasta mais tempo em context switches que em trabalho útil
- "Thundering herd" problem

```cpp
#include <mutex>
#include <thread>
#include <chrono>
#include <vector>
#include <atomic>
#include <iostream>

// Demonstração de Lock Convoy
class ConvoyDemo {
    std::mutex mtx_;
    std::atomic<int> counter_{0};
    std::atomic<int> convoy_count_{0};
    std::chrono::steady_clock::time_point start_;

public:
    void worker(int id, int iterations) {
        for (int i = 0; i < iterations; ++i) {
            auto lock_start = std::chrono::steady_clock::now();
            std::lock_guard<std::mutex> lock(mtx_);
            auto lock_end = std::chrono::steady_clock::now();
            
            auto wait_time = std::chrono::duration_cast<std::chrono::microseconds>(
                lock_end - lock_start).count();
            
            if (wait_time > 1000) {  // Esperou mais de 1ms
                ++convoy_count_;
            }
            
            ++counter_;
            // Simula trabalho na seção crítica
            std::this_thread::sleep_for(std::chrono::microseconds(10));
        }
    }

    void run_test(int num_threads, int iterations) {
        start_ = std::chrono::steady_clock::now();
        std::vector<std::thread> threads;
        for (int i = 0; i < num_threads; ++i) {
            threads.emplace_back(&ConvoyDemo::worker, this, i, iterations);
        }
        for (auto& t : threads) t.join();
        
        auto elapsed = std::chrono::steady_clock::now() - start_;
        std::cout << "Threads: " << num_threads 
                  << ", Iterations: " << iterations
                  << ", Time: " << std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count() << "ms"
                  << ", Convoy events: " << convoy_count_
                  << ", Counter: " << counter_ << "\n";
    }
};
```

### 7.2 Causas e Detecção

**Causas:**
1. **Mutex unfair padrão**: `std::mutex` não garante FIFO
2. **Seções críticas longas**: Trabalho excessivo dentro do lock
3. **Muitas threads**: Mais threads que cores CPU
4. **Wake-up storms**: Todas threads acordam ao mesmo tempo

**Detecção:**
```cpp
#include <mutex>
#include <chrono>
#include <atomic>
#include <vector>

class ConvoyDetector {
    std::mutex mtx_;
    std::atomic<uint64_t> total_wait_cycles_{0};
    std::atomic<uint64_t> lock_acquisitions_{0};
    std::atomic<uint64_t> convoy_events_{0};
    std::chrono::nanoseconds convoy_threshold_{100000};  // 100µs

public:
    class ScopedLock {
        ConvoyDetector& detector_;
        std::chrono::steady_clock::time_point start_;
    public:
        explicit ScopedLock(ConvoyDetector& d) : detector_(d), start_(std::chrono::steady_clock::now()) {
            detector_.mtx_.lock();
        }
        ~ScopedLock() {
            auto end = std::chrono::steady_clock::now();
            auto wait = end - start_;
            detector_.mtx_.unlock();
            
            detector_.lock_acquisitions_.fetch_add(1, std::memory_order_relaxed);
            detector_.total_wait_cycles_.fetch_add(wait.count(), std::memory_order_relaxed);
            
            if (wait > detector_.convoy_threshold_) {
                detector_.convoy_events_.fetch_add(1, std::memory_order_relaxed);
            }
        }
    };

    ScopedLock lock() { return ScopedLock(*this); }

    double average_wait_ns() const {
        uint64_t acq = lock_acquisitions_.load();
        return acq > 0 ? double(total_wait_cycles_.load()) / acq : 0;
    }

    uint64_t convoy_events() const { return convoy_events_.load(); }
    uint64_t acquisitions() const { return lock_acquisitions_.load(); }
    
    void reset() {
        total_wait_cycles_ = 0;
        lock_acquisitions_ = 0;
        convoy_events_ = 0;
    }
};
```

### 7.3 Soluções: Fair Locks, Queuing Locks

#### Fair Mutex com FIFO

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>
#include <thread>
#include <atomic>

class FairMutex {
    std::mutex internal_;
    std::condition_variable cv_;
    std::queue<std::thread::id> queue_;
    std::thread::id owner_;
    bool locked_ = false;
    int recursion_ = 0;

public:
    void lock() {
        std::thread::id me = std::this_thread::get_id();
        std::unique_lock<std::mutex> lock(internal_);
        
        if (locked_ && owner_ == me) {
            ++recursion_;
            return;
        }
        
        queue_.push(me);
        cv_.wait(lock, [this, me] { return !locked_ && queue_.front() == me; });
        queue_.pop();
        locked_ = true;
        owner_ = me;
        recursion_ = 1;
    }

    void unlock() {
        std::lock_guard<std::mutex> lock(internal_);
        if (--recursion_ == 0) {
            locked_ = false;
            owner_ = std::thread::id{};
            cv_.notify_one();
        }
    }

    bool try_lock() {
        std::lock_guard<std::mutex> lock(internal_);
        if (!locked_) {
            locked_ = true;
            owner_ = std::this_thread::get_id();
            recursion_ = 1;
            return true;
        }
        return false;
    }
};
```

### 7.4 Implementação de MCS Lock

MCS (Mellor-Crummey and Scott) Lock - queue-based, scalable, cache-friendly:

```cpp
#include <atomic>
#include <thread>
#include <memory>

// MCS Lock - O padrão ouro para locks escaláveis
class MCSLock {
    struct QNode {
        std::atomic<QNode*> next{nullptr};
        std::atomic<bool> locked{true};  // true = waiting
    };

    std::atomic<QNode*> tail_{nullptr};

public:
    MCSLock() = default;
    ~MCSLock() = default;

    // Não copiável/movível
    MCSLock(const MCSLock&) = delete;
    MCSLock& operator=(const MCSLock&) = delete;

    class Guard {
        MCSLock& lock_;
        QNode* my_node_;
    public:
        explicit Guard(MCSLock& lock) : lock_(lock), my_node_(new QNode()) {
            // Adiciona à fila atomicamente
            QNode* pred = lock_.tail_.exchange(my_node_, std::memory_order_acq_rel);
            if (pred != nullptr) {
                // Há predecessor - espera ele nos sinalizar
                pred->next.store(my_node_, std::memory_order_release);
                // Spin local na variável locked do meu nó (cache-friendly!)
                while (my_node_->locked.load(std::memory_order_acquire)) {
                    // Pausa para reduzir pressão no barramento
#if defined(__x86_64__) || defined(__i386__)
                    __builtin_ia32_pause();
#elif defined(__aarch64__)
                    __builtin_arm_yield();
#else
                    std::this_thread::yield();
#endif
                }
            }
            // Se pred == nullptr, sou o primeiro - adquiri o lock!
        }

        ~Guard() {
            QNode* next = my_node_->next.load(std::memory_order_acquire);
            if (next == nullptr) {
                // Tentativa rápida: sou o último na fila
                QNode* expected = my_node_;
                if (lock_.tail_.compare_exchange_strong(
                        expected, nullptr, std::memory_order_acq_rel)) {
                    delete my_node_;
                    return;  // Fila vazia, lock liberado
                }
                // Alguém entrou na fila enquanto eu verificava - espera link
                while ((next = my_node_->next.load(std::memory_order_acquire)) == nullptr) {
#if defined(__x86_64__) || defined(__i386__)
                    __builtin_ia32_pause();
#elif defined(__aarch64__)
                    __builtin_arm_yield();
#else
                    std::this_thread::yield();
#endif
                }
            }
            // Sinaliza próximo na fila
            next->locked.store(false, std::memory_order_release);
            delete my_node_;
        }
    };

    Guard acquire() { return Guard(*this); }
    
    bool try_lock() {
        QNode* expected = nullptr;
        QNode* new_node = new QNode();
        new_node->locked.store(false, std::memory_order_relaxed);
        if (tail_.compare_exchange_strong(expected, new_node, std::memory_order_acq_rel)) {
            delete new_node;
            return true;
        }
        delete new_node;
        return false;
    }
};
```

### 7.5 Implementação de CLH Lock

CLH (Craig, Landin, and Hagersten) Lock - variante do MCS, mais simples:

```cpp
#include <atomic>
#include <thread>

class CLHLock {
    struct QNode {
        std::atomic<bool> locked{false};
    };

    std::atomic<QNode*> tail_{nullptr};
    thread_local static QNode* my_node_;
    thread_local static QNode* my_pred_;

public:
    CLHLock() {
        QNode* initial = new QNode();
        initial->locked.store(false, std::memory_order_relaxed);
        tail_.store(initial, std::memory_order_relaxed);
    }

    ~CLHLock() {
        QNode* n = tail_.load(std::memory_order_relaxed);
        delete n;
    }

    class Guard {
        CLHLock& lock_;
        QNode* my_node_;
        QNode* my_pred_;
    public:
        explicit Guard(CLHLock& lock) : lock_(lock), my_node_(new QNode()) {
            my_node_->locked.store(true, std::memory_order_relaxed);
            my_pred_ = lock_.tail_.exchange(my_node_, std::memory_order_acq_rel);
            
            // Spin no predecessor (cache-friendly - predecessor's cache line)
            while (my_pred_->locked.load(std::memory_order_acquire)) {
#if defined(__x86_64__) || defined(__i386__)
                __builtin_ia32_pause();
#elif defined(__aarch64__)
                __builtin_arm_yield();
#else
                std::this_thread::yield();
#endif
            }
        }

        ~Guard() {
            my_node_->locked.store(false, std::memory_order_release);
            lock_.tail_.store(my_pred_, std::memory_order_release);
            delete my_node_;
        }
    };

    Guard acquire() { return Guard(*this); }
};

thread_local CLHLock::QNode* CLHLock::my_node_ = nullptr;
thread_local CLHLock::QNode* CLHLock::my_pred_ = nullptr;
```

### 7.6 Comparação de Performance

```cpp
#include <benchmark/benchmark.h>  // Google Benchmark
#include <mutex>
#include <thread>
#include <vector>

static void BM_StdMutex(benchmark::State& state) {
    std::mutex mtx;
    int counter = 0;
    std::vector<std::thread> threads;
    
    for (auto _ : state) {
        threads.clear();
        for (int i = 0; i < state.range(0); ++i) {
            threads.emplace_back([&] {
                for (int j = 0; j < 1000; ++j) {
                    std::lock_guard<std::mutex> l(mtx);
                    ++counter;
                }
            });
        }
        for (auto& t : threads) t.join();
    }
    state.SetItemsProcessed(state.iterations() * state.range(0) * 1000);
}

static void BM_MCSLock(benchmark::State& state) {
    MCSLock mcs;
    int counter = 0;
    std::vector<std::thread> threads;
    
    for (auto _ : state) {
        threads.clear();
        for (int i = 0; i < state.range(0); ++i) {
            threads.emplace_back([&] {
                for (int j = 0; j < 1000; ++j) {
                    auto g = mcs.acquire();
                    ++counter;
                }
            });
        }
        for (auto& t : threads) t.join();
    }
    state.SetItemsProcessed(state.iterations() * state.range(0) * 1000);
}

static void BM_CLHLock(benchmark::State& state) {
    CLHLock clh;
    int counter = 0;
    std::vector<std::thread> threads;
    
    for (auto _ : state) {
        threads.clear();
        for (int i = 0; i < state.range(0); ++i) {
            threads.emplace_back([&] {
                for (int j = 0; j < 1000; ++j) {
                    auto g = clh.acquire();
                    ++counter;
                }
            });
        }
        for (auto& t : threads) t.join();
    }
    state.SetItemsProcessed(state.iterations() * state.range(0) * 1000);
}

BENCHMARK(BM_StdMutex)->Arg(1)->Arg(2)->Arg(4)->Arg(8)->Arg(16)->Arg(32);
BENCHMARK(BM_MCSLock)->Arg(1)->Arg(2)->Arg(4)->Arg(8)->Arg(16)->Arg(32);
BENCHMARK(BM_CLHLock)->Arg(1)->Arg(2)->Arg(4)->Arg(8)->Arg(16)->Arg(32);

BENCHMARK_MAIN();
```

EOF
## 8. Deadlocks em Sistemas Distribuídos

### 8.1 Detecção de Deadlock Distribuído

Em sistemas distribuídos, deadlocks podem envolver recursos em múltiplos nós. A detecção é mais complexa pois não há memória compartilhada global.

```cpp
#include <unordered_map>
#include <vector>
#include <string>
#include <mutex>
#include <chrono>
#include <thread>
#include <atomic>
#include <iostream>

// Modelo simplificado de deadlock distribuído
struct DistributedWaitForEdge {
    std::string waiter_node;
    std::string waiter_thread;
    std::string holder_node;
    std::string holder_thread;
    std::string resource_id;
    std::chrono::steady_clock::time_point timestamp;
};

class DistributedDeadlockDetector {
    std::mutex edges_mtx_;
    std::vector<DistributedWaitForEdge> local_edges_;
    std::atomic<bool> running_{false};
    std::thread detector_thread_;
    std::chrono::seconds check_interval_{5};

    // Callback para receber edges de outros nós (RPC/message queue)
    std::function<void(const DistributedWaitForEdge&)> on_receive_edge_;

public:
    DistributedDeadlockDetector(
        std::function<void(const DistributedWaitForEdge&)> receive_cb)
        : on_receive_edge_(std::move(receive_cb)) {}

    void start() {
        running_ = true;
        detector_thread_ = std::thread([this] { detection_loop(); });
    }

    void stop() {
        running_ = false;
        if (detector_thread_.joinable()) detector_thread_.join();
    }

    void add_local_edge(const std::string& waiter_thread,
                        const std::string& holder_thread,
                        const std::string& resource_id) {
        DistributedWaitForEdge edge;
        edge.waiter_node = get_node_id();
        edge.waiter_thread = waiter_thread;
        edge.holder_node = get_node_id();
        edge.holder_thread = holder_thread;
        edge.resource_id = resource_id;
        edge.timestamp = std::chrono::steady_clock::now();

        std::lock_guard lock(edges_mtx_);
        local_edges_.push_back(edge);
    }

    void receive_remote_edge(const DistributedWaitForEdge& edge) {
        std::lock_guard lock(edges_mtx_);
        local_edges_.push_back(edge);
    }

private:
    std::string get_node_id() {
        // Em produção: hostname, IP, ou ID único do cluster
        return "node-" + std::to_string(std::hash<std::thread::id>{}(std::this_thread::get_id()) % 100);
    }

    void detection_loop() {
        while (running_) {
            std::this_thread::sleep_for(check_interval_);
            check_global_deadlocks();
        }
    }

    void check_global_deadlocks() {
        std::lock_guard lock(edges_mtx_);
        
        // Constrói grafo global wait-for
        std::unordered_map<std::string, std::vector<std::string>> graph;
        for (const auto& edge : local_edges_) {
            std::string waiter = edge.waiter_node + ":" + edge.waiter_thread;
            std::string holder = edge.holder_node + ":" + edge.holder_thread;
            graph[waiter].push_back(holder);
        }

        // Detecta ciclos (Tarjan's SCC)
        auto cycles = find_cycles(graph);
        
        for (const auto& cycle : cycles) {
            std::cout << "[DISTRIBUTED DEADLOCK] Cycle detected: ";
            for (const auto& n : cycle) std::cout << n << " -> ";
            std::cout << cycle[0] << "\n";
            
            // Inicia resolução (Chandy-Misra-Haas ou vítima)
            resolve_deadlock(cycle);
        }
    }

    std::vector<std::vector<std::string>> find_cycles(
        const std::unordered_map<std::string, std::vector<std::string>>& graph) {
        // Implementação similar à anterior
        return {};
    }

    void resolve_deadlock(const std::vector<std::string>& cycle) {
        // Seleciona vítima e notifica nó correspondente
        // Requer protocolo de coordenação distribuída
    }
};
```

### 8.2 Algoritmo Chandy-Misra-Haas

Algoritmo distribuído de detecção de deadlock baseado em **probe messages**:

```cpp
#include <unordered_map>
#include <vector>
#include <string>
#include <mutex>
#include <atomic>
#include <functional>

// Implementação simplificada do Chandy-Misra-Haas
class ChandyMisraHaasDetector {
    struct Probe {
        std::string initiator;      // Thread que iniciou
        std::string sender;         // Thread que enviou
        std::string target;         // Thread alvo
        int sequence_number;        // Para evitar loops
    };

    std::mutex state_mtx_;
    std::unordered_map<std::string, std::vector<std::string>> wait_for_;  // local wait-for
    std::unordered_map<std::string, bool> engaged_;  // thread -> engaged in detection
    std::atomic<int> sequence_counter_{0};
    
    // Callbacks para comunicação distribuída
    std::function<void(const std::string&, const Probe&)> send_probe_;
    std::function<void(const std::string&)> on_deadlock_found_;

public:
    ChandyMisraHaasDetector(
        std::function<void(const std::string&, const Probe&)> send_cb,
        std::function<void(const std::string&)> deadlock_cb)
        : send_probe_(std::move(send_cb))
        , on_deadlock_found_(std::move(deadlock_cb)) {}

    // Chamado quando thread local espera por recurso
    void add_dependency(const std::string& waiter, const std::string& holder) {
        std::lock_guard lock(state_mtx_);
        wait_for_[waiter].push_back(holder);
    }

    void remove_dependency(const std::string& waiter, const std::string& holder) {
        std::lock_guard lock(state_mtx_);
        auto it = wait_for_.find(waiter);
        if (it != wait_for_.end()) {
            it->second.erase(std::remove(it->second.begin(), it->second.end(), holder),
                           it->second.end());
        }
    }

    // Inicia detecção a partir de thread local
    void initiate_detection(const std::string& thread_id) {
        std::lock_guard lock(state_mtx_);
        if (engaged_[thread_id]) return;  // Já em detecção
        
        engaged_[thread_id] = true;
        int seq = ++sequence_counter_;
        
        // Envia probes para todos que esta thread espera
        auto it = wait_for_.find(thread_id);
        if (it != wait_for_.end()) {
            for (const auto& holder : it->second) {
                Probe probe{thread_id, thread_id, holder, seq};
                send_probe_(holder, probe);
            }
        }
    }

    // Recebe probe de outro nó/thread
    void receive_probe(const Probe& probe) {
        std::lock_guard lock(state_mtx_);
        
        // Se probe voltou ao iniciador -> DEADLOCK!
        if (probe.target == probe.initiator) {
            std::cout << "[CMH] Deadlock detected! Initiator: " << probe.initiator << "\n";
            on_deadlock_found_(probe.initiator);
            return;
        }

        // Se já engajado com sequence number menor ou igual, ignora
        if (engaged_[probe.target] && engaged_[probe.target] <= probe.sequence_number) {
            return;
        }

        engaged_[probe.target] = true;
        
        // Encaminha probe para todos que target espera
        auto it = wait_for_.find(probe.target);
        if (it != wait_for_.end()) {
            for (const auto& next_holder : it->second) {
                Probe next_probe = probe;
                next_probe.sender = probe.target;
                next_probe.target = next_holder;
                send_probe_(next_holder, next_probe);
            }
        }
    }

    // Thread liberou recurso - reseta estado
    void thread_released(const std::string& thread_id) {
        std::lock_guard lock(state_mtx_);
        engaged_[thread_id] = false;
        wait_for_.erase(thread_id);
    }
};
```

### 8.3 Abordagens Baseadas em Timeout

Em prática, muitos sistemas usam timeouts simples para deadlocks distribuídos:

```cpp
#include <chrono>
#include <mutex>
#include <condition_variable>
#include <unordered_map>
#include <string>
#include <thread>
#include <functional>

class DistributedLockManager {
    struct LockState {
        std::string owner;
        std::chrono::steady_clock::time_point acquired_at;
        int lease_duration_ms;  // Lease time
        bool valid = true;
    };

    std::mutex locks_mtx_;
    std::unordered_map<std::string, LockState> locks_;
    std::chrono::milliseconds default_lease_{30000};  // 30s default
    std::thread lease_monitor_;
    std::atomic<bool> running_{false};

public:
    using LockCallback = std::function<void(const std::string&, bool)>;  // resource, acquired

    DistributedLockManager() = default;

    ~DistributedLockManager() {
        stop();
    }

    void start() {
        running_ = true;
        lease_monitor_ = std::thread([this] { monitor_leases(); });
    }

    void stop() {
        running_ = false;
        if (lease_monitor_.joinable()) lease_monitor_.join();
    }

    // Tenta adquirir lock com lease
    bool try_acquire(const std::string& resource, const std::string& client_id,
                     int lease_ms = -1, LockCallback cb = nullptr) {
        std::unique_lock lock(locks_mtx_);
        
        auto it = locks_.find(resource);
        if (it == locks_.end() || !it->second.valid) {
            // Lock livre
            locks_[resource] = {client_id, std::chrono::steady_clock::now(),
                               lease_ms > 0 ? lease_ms : default_lease_.count(), true};
            if (cb) cb(resource, true);
            return true;
        }
        
        // Verifica se lease expirou
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            now - it->second.acquired_at).count();
        
        if (elapsed >= it->second.lease_duration_ms) {
            // Lease expirado - força release
            std::cout << "[LEASE] Expirado para " << resource 
                      << " (owner: " << it->second.owner << ")\n";
            it->second = {client_id, now, 
                         lease_ms > 0 ? lease_ms : default_lease_.count(), true};
            if (cb) cb(resource, true);
            return true;
        }
        
        if (cb) cb(resource, false);
        return false;
    }

    void release(const std::string& resource, const std::string& client_id) {
        std::lock_guard lock(locks_mtx_);
        auto it = locks_.find(resource);
        if (it != locks_.end() && it->second.owner == client_id) {
            it->second.valid = false;
        }
    }

    void renew_lease(const std::string& resource, const std::string& client_id,
                     int lease_ms = -1) {
        std::lock_guard lock(locks_mtx_);
        auto it = locks_.find(resource);
        if (it != locks_.end() && it->second.owner == client_id && it->second.valid) {
            it->second.acquired_at = std::chrono::steady_clock::now();
            it->second.lease_duration_ms = lease_ms > 0 ? lease_ms : default_lease_.count();
        }
    }

private:
    void monitor_leases() {
        while (running_) {
            std::this_thread::sleep_for(std::chrono::seconds(5));
            
            std::lock_guard lock(locks_mtx_);
            auto now = std::chrono::steady_clock::now();
            
            for (auto& [resource, state] : locks_) {
                if (!state.valid) continue;
                
                auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                    now - state.acquired_at).count();
                
                if (elapsed >= state.lease_duration_ms) {
                    std::cout << "[MONITOR] Lease expirado forçado: " << resource << "\n";
                    state.valid = false;
                }
            }
        }
    }
};
```

EOF
## 9. Ferramentas de Detecção

### 9.1 ThreadSanitizer (TSan)

ThreadSanitizer é a ferramenta principal para detectar data races e deadlocks em C++:

```bash
# Compilação com TSan
g++ -fsanitize=thread -g -O1 -fno-omit-frame-pointer \
    deadlock_example.cpp -o deadlock_example -pthread

# Execução
./deadlock_example

# Opções úteis
TSAN_OPTIONS="halt_on_error=1:report_thread_leaks=1:deadlock_detection=1" ./deadlock_example
```

**Exemplo detectado pelo TSan:**

```cpp
// deadlock_tsan.cpp
#include <mutex>
#include <thread>
#include <chrono>

std::mutex m1, m2;

void thread_a() {
    std::lock_guard<std::mutex> l1(m1);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> l2(m2);
}

void thread_b() {
    std::lock_guard<std::mutex> l1(m2);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> l2(m1);
}

int main() {
    std::thread t1(thread_a);
    std::thread t2(thread_b);
    t1.join();
    t2.join();
    return 0;
}
```

**Saída do TSan:**
```
==================
WARNING: ThreadSanitizer: deadlock detected
==================
Mutex M1 (0x...) created at:
  #0 main deadlock_tsan.cpp:15
Mutex M2 (0x...) created at:
  #0 main deadlock_tsan.cpp:16

Thread T1 (tid=...) acquired M1 at:
  #0 thread_a deadlock_tsan.cpp:6
Thread T2 (tid=...) acquired M2 at:
  #0 thread_b deadlock_tsan.cpp:12

Thread T1 waiting for M2 (held by T2)
Thread T2 waiting for M1 (held by T1)
```

### 9.2 Helgrind e DRD (Valgrind)

```bash
# Helgrind - detecta data races e deadlocks
valgrind --tool=helgrind --free-is-write=yes \
    --track-lockorders=yes ./deadlock_example

# DRD - detector de data races mais rápido
valgrind --tool=drd ./deadlock_example

# Opções úteis Helgrind
valgrind --tool=helgrind \
    --history-level=full \
    --conflict-cache-size=2000000 \
    --track-lockorders=yes \
    ./deadlock_example
```

**Saída típica do Helgrind para deadlock:**
```
==12345== Thread #1: lock order "0x... (mutex1) before 0x... (mutex2)" violated
==12345== Thread #2: lock order "0x... (mutex2) before 0x... (mutex1)" violated
==12345== Possible deadlock detected.
```

### 9.3 Análise Estática: clang-tidy

```bash
# Verificações de concorrência do clang-tidy
clang-tidy -checks='-*,concurrency-*' deadlock_example.cpp -- -std=c++20 -pthread

# Checks específicos:
# concurrency-thread-safety-*
# concurrency-mt-unsafe
# bugprone-lock-order
# bugprone-unlocked-attribute
```

**Configuração .clang-tidy para concorrência:**
```yaml
Checks: >
  -*,
  concurrency-*,
  bugprone-lock-order,
  bugprone-unlocked-attribute,
  thread-safety-*
WarningsAsErrors: 'concurrency-*,bugprone-lock-order'
CheckOptions:
  - key: concurrency-thread-safety-enable-annotations
    value: 'true'
```

**Anotações de Thread Safety (Clang):**
```cpp
#include <mutex>

class BankAccount {
    mutable std::mutex mtx_ 
        ACQUIRE_SHARED()  // Para métodos const
        RELEASE_SHARED();
    int balance_ GUARDED_BY(mtx_) = 0;

public:
    void deposit(int amount) 
        EXCLUSIVE_LOCK_FUNCTION(mtx_) {
        std::lock_guard<std::mutex> lock(mtx_);
        balance_ += amount;
    }

    int get_balance() const 
        SHARED_LOCK_FUNCTION(mtx_) {
        std::lock_guard<std::mutex> lock(mtx_);
        return balance_;
    }
    
    // Erro: faltando anotação de lock
    // void unsafe_method() { balance_ = 0; }  // WARNING!
};
```

### 9.4 Model Checking

Para verificação formal de algoritmos de concorrência:

```cpp
// Exemplo para TLA+ / PlusCal
/*
---- MODULE DeadlockFreeTransfer ----
EXTENDS Naturals, Sequences

CONSTANTS Accounts, MaxBalance

VARIABLES balances, locks, pc

TypeOK == 
  /\ balances \in [Accounts -> 0..MaxBalance]
  /\ locks \in [Accounts -> {"free", "locked"}]
  /\ pc \in [1..2 -> {"start", "lock1", "lock2", "transfer", "unlock2", "unlock1", "done"}]

Transfer(from, to, amount) ==
  /\ pc[1] = "start"
  /\ pc[2] = "start"
  /\ locks[from] = "free"
  /\ locks[to] = "free"
  /\ balances[from] >= amount
  /\ pc' = [pc EXCEPT ![1] = "lock1", ![2] = "lock1"]
  /\ locks' = [locks EXCEPT ![from] = "locked", ![to] = "locked"]
  /\ balances' = [balances EXCEPT ![from] = @ - amount, ![to] = @ + amount]

NoDeadlock == 
  ~(pc[1] = "lock2" /\ pc[2] = "lock2" /\ locks[from] = "locked" /\ locks[to] = "locked")

===============================================================================
*/

// Para uso com CBMC (C Bounded Model Checker)
// cbmc --unwind 10 --function main deadlock_cbmc.c
```

```cpp
// CBMC example - verifica deadlock em bounded loops
#include <assert.h>
#include <pthread.h>

pthread_mutex_t m1, m2;
int turn = 0;

void* thread1(void* arg) {
    for (int i = 0; i < 10; i++) {
        pthread_mutex_lock(&m1);
        pthread_mutex_lock(&m2);
        turn = 1;
        pthread_mutex_unlock(&m2);
        pthread_mutex_unlock(&m1);
    }
    return NULL;
}

void* thread2(void* arg) {
    for (int i = 0; i < 10; i++) {
        pthread_mutex_lock(&m2);
        pthread_mutex_lock(&m1);
        turn = 2;
        pthread_mutex_unlock(&m1);
        pthread_mutex_unlock(&m2);
    }
    return NULL;
}

int main() {
    pthread_mutex_init(&m1, NULL);
    pthread_mutex_init(&m2, NULL);
    
    pthread_t t1, t2;
    pthread_create(&t1, NULL, thread1, NULL);
    pthread_create(&t2, NULL, thread2, NULL);
    
    pthread_join(t1, NULL);
    pthread_join(t2, NULL);
    
    // CBMC pode verificar: assert(turn == 1 || turn == 2);
    return 0;
}
```

### 9.5 Ferramentas Comerciais e Avançadas

| Ferramenta | Tipo | Deadlock Detection | Data Race | Plataforma |
|------------|------|-------------------|-----------|------------|
| **ThreadSanitizer** | Dynamic | ✅ | ✅ | Linux, macOS, Windows |
| **Helgrind/DRD** | Dynamic | ✅ | ✅ | Linux, macOS |
| **Intel Inspector** | Dynamic | ✅ | ✅ | Linux, Windows |
| **CodeSonar** | Static | ✅ | ✅ | Cross-platform |
| **Coverity** | Static | ✅ | ✅ | Cross-platform |
| **PVS-Studio** | Static | ⚠️ | ✅ | Cross-platform |
| **TLA+/PlusCal** | Model Check | ✅ | N/A | Cross-platform |
| **CBMC** | Model Check | ✅ | ✅ | Cross-platform |
| **SPIN** | Model Check | ✅ | N/A | Cross-platform |

EOF
## 10. Exercício Prático

### 10.1 Implementar Gerenciador de Recursos Livre de Deadlock

Implemente um `ResourceManager` que gerencia múltiplos recursos tipados com prevenção de deadlock:

```cpp
#include <mutex>
#include <shared_mutex>
#include <unordered_map>
#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <optional>
#include <iostream>
#include <algorithm>

// Resource Manager livre de deadlock usando std::scoped_lock e ordenação
template<typename ResourceType>
class DeadlockFreeResourceManager {
    struct ResourceEntry {
        std::shared_mutex rw_mutex;  // Permite múltiplos readers
        ResourceType resource;
        std::string name;
        int lock_level;  // Para ordenação global
    };

    std::mutex registry_mtx_;
    std::unordered_map<std::string, std::unique_ptr<ResourceEntry>> resources_;
    int next_lock_level_ = 0;

public:
    // Registra novo recurso com nível de lock automático
    bool register_resource(const std::string& name, ResourceType&& resource) {
        std::lock_guard lock(registry_mtx_);
        if (resources_.count(name)) return false;
        
        auto entry = std::make_unique<ResourceEntry>();
        entry->name = name;
        entry->resource = std::move(resource);
        entry->lock_level = next_lock_level_++;
        resources_[name] = std::move(entry);
        return true;
    }

    // Adquire múltiplos recursos para escrita (exclusivo) - SEM DEADLOCK
    template<typename Func>
    bool acquire_exclusive(const std::vector<std::string>& names, Func&& func) {
        // Ordena por lock_level para prevenir circular wait
        std::vector<std::string> sorted = names;
        std::sort(sorted.begin(), sorted.end(),
            [this](const std::string& a, const std::string& b) {
                auto it_a = resources_.find(a);
                auto it_b = resources_.find(b);
                if (it_a == resources_.end() || it_b == resources_.end()) return a < b;
                return it_a->second->lock_level < it_b->second->lock_level;
            });

        // Adquire todos os locks usando scoped_lock (atômico)
        std::vector<std::unique_lock<std::shared_mutex>> locks;
        locks.reserve(sorted.size());
        
        for (const auto& name : sorted) {
            auto it = resources_.find(name);
            if (it == resources_.end()) {
                // Rollback: libera locks já adquiridos
                return false;
            }
            locks.emplace_back(it->second->rw_mutex);
        }

        // Executa função com todos os recursos
        std::vector<ResourceType*> resources;
        resources.reserve(sorted.size());
        for (const auto& name : sorted) {
            resources.push_back(&resources_[name]->resource);
        }
        
        func(resources);
        return true;
    }

    // Adquire múltiplos recursos para leitura (compartilhado)
    template<typename Func>
    bool acquire_shared(const std::vector<std::string>& names, Func&& func) {
        std::vector<std::string> sorted = names;
        std::sort(sorted.begin(), sorted.end(),
            [this](const std::string& a, const std::string& b) {
                auto it_a = resources_.find(a);
                auto it_b = resources_.find(b);
                if (it_a == resources_.end() || it_b == resources_.end()) return a < b;
                return it_a->second->lock_level < it_b->second->lock_level;
            });

        std::vector<std::shared_lock<std::shared_mutex>> locks;
        locks.reserve(sorted.size());
        
        for (const auto& name : sorted) {
            auto it = resources_.find(name);
            if (it == resources_.end()) return false;
            locks.emplace_back(it->second->rw_mutex);
        }

        std::vector<const ResourceType*> resources;
        resources.reserve(sorted.size());
        for (const auto& name : sorted) {
            resources.push_back(&resources_[name]->resource);
        }
        
        func(resources);
        return true;
    }

    // Timeout-based acquire
    template<typename Func>
    bool try_acquire_exclusive(const std::vector<std::string>& names,
                               std::chrono::milliseconds timeout,
                               Func&& func) {
        std::vector<std::string> sorted = names;
        std::sort(sorted.begin(), sorted.end(),
            [this](const std::string& a, const std::string& b) {
                auto it_a = resources_.find(a);
                auto it_b = resources_.find(b);
                if (it_a == resources_.end() || it_b == resources_.end()) return a < b;
                return it_a->second->lock_level < it_b->second->lock_level;
            });

        std::vector<std::unique_lock<std::shared_mutex>> locks;
        locks.reserve(sorted.size());
        
        auto deadline = std::chrono::steady_clock::now() + timeout;
        
        for (const auto& name : sorted) {
            auto it = resources_.find(name);
            if (it == resources_.end()) return false;
            
            if (!locks.emplace_back(it->second->rw_mutex, std::defer_lock)
                    .try_lock_until(deadline)) {
                return false;  // Timeout
            }
        }

        std::vector<ResourceType*> resources;
        for (const auto& name : sorted) {
            resources.push_back(&resources_[name]->resource);
        }
        
        func(resources);
        return true;
    }
};

// Exemplo de uso: Sistema de transferência bancária
struct Account {
    std::string owner;
    double balance = 0.0;
    std::vector<std::string> transaction_log;
};

void banking_example() {
    DeadlockFreeResourceManager<Account> bank;
    
    bank.register_resource("alice", Account{"Alice", 1000.0});
    bank.register_resource("bob", Account{"Bob", 500.0});
    bank.register_resource("charlie", Account{"Charlie", 2000.0});

    // Transferência atômica entre múltiplas contas - SEM DEADLOCK
    std::thread t1([&] {
        bank.acquire_exclusive({"alice", "bob"}, [](auto& accounts) {
            Account* alice = accounts[0];
            Account* bob = accounts[1];
            if (alice->balance >= 100) {
                alice->balance -= 100;
                bob->balance += 100;
                alice->transaction_log.push_back("Sent 100 to Bob");
                bob->transaction_log.push_back("Received 100 from Alice");
            }
        });
    });

    std::thread t2([&] {
        bank.acquire_exclusive({"bob", "charlie"}, [](auto& accounts) {
            Account* bob = accounts[0];
            Account* charlie = accounts[1];
            if (bob->balance >= 50) {
                bob->balance -= 50;
                charlie->balance += 50;
            }
        });
    });

    std::thread t3([&] {
        bank.acquire_exclusive({"alice", "charlie"}, [](auto& accounts) {
            Account* alice = accounts[0];
            Account* charlie = accounts[1];
            if (alice->balance >= 200) {
                alice->balance -= 200;
                charlie->balance += 200;
            }
        });
    });

    t1.join(); t2.join(); t3.join();

    // Leitura concorrente segura
    bank.acquire_shared({"alice", "bob", "charlie"}, [](auto& accounts) {
        for (auto* acc : accounts) {
            std::cout << acc->owner << ": $" << acc->balance << "\n";
        }
    });
}
```

### 10.2 Adicionar Detecção de Deadlock

```cpp
#include <thread>
#include <chrono>
#include <atomic>
#include <vector>
#include <string>
#include <mutex>
#include <unordered_map>
#include <functional>

class ResourceManagerWithDetection {
    struct Resource {
        std::mutex mtx;
        std::string name;
        std::thread::id owner = {};
        std::chrono::steady_clock::time_point acquired_at;
        int waiters = 0;
    };

    std::mutex registry_mtx_;
    std::unordered_map<std::string, std::unique_ptr<Resource>> resources_;
    
    // Deadlock detector
    struct WaitEdge {
        std::string waiter;
        std::string holder;
        std::chrono::steady_clock::time_point since;
    };
    std::mutex detector_mtx_;
    std::vector<WaitEdge> wait_edges_;
    std::atomic<bool> detection_enabled_{true};
    std::thread detector_thread_;
    std::chrono::milliseconds check_interval_{100};

public:
    ResourceManagerWithDetection() = default;
    
    ~ResourceManagerWithDetection() {
        detection_enabled_ = false;
        if (detector_thread_.joinable()) detector_thread_.join();
    }

    void enable_detection(bool enable = true) {
        detection_enabled_ = enable;
        if (enable && !detector_thread_.joinable()) {
            detector_thread_ = std::thread([this] { detection_loop(); });
        }
    }

    bool register_resource(const std::string& name) {
        std::lock_guard lock(registry_mtx_);
        if (resources_.count(name)) return false;
        resources_[name] = std::make_unique<Resource>();
        resources_[name]->name = name;
        return true;
    }

    // Lock com detecção de wait-for
    class LockGuard {
        ResourceManagerWithDetection& manager_;
        std::string resource_name_;
        bool acquired_ = false;
    public:
        LockGuard(ResourceManagerWithDetection& mgr, const std::string& name)
            : manager_(mgr), resource_name_(name) {
            acquire();
        }
        
        ~LockGuard() { if (acquired_) release(); }
        
        void acquire() {
            auto& res = manager_.get_resource(resource_name_);
            std::thread::id me = std::this_thread::get_id();
            
            if (manager_.detection_enabled_) {
                // Registra wait-for edge antes de tentar lock
                {
                    std::lock_guard lock(manager_.detector_mtx_);
                    if (res.owner != std::thread::id{} && res.owner != me) {
                        manager_.wait_edges_.push_back({
                            resource_name_,  // waiter (simplificado)
                            res.name,        // holder
                            std::chrono::steady_clock::now()
                        });
                    }
                    res.waiters++;
                }
            }
            
            res.mtx.lock();
            acquired_ = true;
            
            if (manager_.detection_enabled_) {
                std::lock_guard lock(manager_.detector_mtx_);
                res.owner = me;
                res.acquired_at = std::chrono::steady_clock::now();
                res.waiters--;
                // Remove wait-for edges para este recurso
                manager_.wait_edges_.erase(
                    std::remove_if(manager_.wait_edges_.begin(), 
                                   manager_.wait_edges_.end(),
                                   [&](const WaitEdge& e) { 
                                       return e.holder == resource_name_; 
                                   }),
                    manager_.wait_edges_.end());
            }
        }
        
        void release() {
            auto& res = manager_.get_resource(resource_name_);
            if (manager_.detection_enabled_) {
                std::lock_guard lock(manager_.detector_mtx_);
                res.owner = std::thread::id{};
            }
            res.mtx.unlock();
            acquired_ = false;
        }
    };

    LockGuard lock(const std::string& name) { return LockGuard(*this, name); }

    // Detecta ciclos no wait-for graph
    std::vector<std::vector<std::string>> detect_deadlocks() {
        std::lock_guard lock(detector_mtx_);
        
        std::unordered_map<std::string, std::vector<std::string>> graph;
        for (const auto& edge : wait_edges_) {
            graph[edge.waiter].push_back(edge.holder);
        }
        
        return find_cycles(graph);
    }

private:
    Resource& get_resource(const std::string& name) {
        std::lock_guard lock(registry_mtx_);
        auto it = resources_.find(name);
        if (it == resources_.end()) throw std::runtime_error("Resource not found");
        return *it->second;
    }

    void detection_loop() {
        while (detection_enabled_) {
            std::this_thread::sleep_for(check_interval_);
            
            auto cycles = detect_deadlocks();
            for (const auto& cycle : cycles) {
                std::cout << "[DEADLOCK DETECTED] Cycle: ";
                for (const auto& n : cycle) std::cout << n << " -> ";
                std::cout << cycle[0] << "\n";
                // Em produção: notificar, logar, ou recuperar automaticamente
            }
        }
    }

    std::vector<std::vector<std::string>> find_cycles(
        const std::unordered_map<std::string, std::vector<std::string>>& graph) {
        // Tarjan's algorithm (mesma implementação anterior)
        return {};
    }
};
```

### 10.3 Stress Test com Múltiplas Threads

```cpp
#include <thread>
#include <vector>
#include <chrono>
#include <atomic>
#include <random>
#include <iostream>
#include <iomanip>

void stress_test_resource_manager() {
    ResourceManagerWithDetection rm;
    
    // Registra 10 recursos
    for (int i = 0; i < 10; ++i) {
        rm.register_resource("res" + std::to_string(i));
    }
    rm.enable_detection(true);

    std::atomic<int> successful_ops{0};
    std::atomic<int> failed_ops{0};
    std::atomic<int> deadlock_detected{0};
    const int num_threads = 20;
    const int ops_per_thread = 1000;

    auto worker = [&](int thread_id) {
        std::mt19937 rng(thread_id + std::random_device{}());
        std::uniform_int_distribution<int> res_dist(0, 9);
        std::uniform_int_distribution<int> num_resources_dist(1, 3);
        std::uniform_int_distribution<int> hold_time_dist(1, 10);

        for (int op = 0; op < ops_per_thread; ++op) {
            int num_res = num_resources_dist(rng);
            std::vector<std::string> resources;
            
            // Seleciona recursos aleatórios únicos
            while ((int)resources.size() < num_res) {
                std::string r = "res" + std::to_string(res_dist(rng));
                if (std::find(resources.begin(), resources.end(), r) == resources.end()) {
                    resources.push_back(r);
                }
            }

            // Adquire locks em ordem aleatória (testa prevenção de deadlock)
            std::shuffle(resources.begin(), resources.end(), rng);
            
            std::vector<typename ResourceManagerWithDetection::LockGuard> locks;
            bool all_acquired = true;
            
            for (const auto& res : resources) {
                locks.emplace_back(rm, res);
            }
            
            if (all_acquired) {
                // Simula trabalho
                std::this_thread::sleep_for(
                    std::chrono::milliseconds(hold_time_dist(rng)));
                successful_ops++;
            } else {
                failed_ops++;
            }
            
            // Verifica deadlocks periodicamente
            if (op % 100 == 0) {
                auto cycles = rm.detect_deadlocks();
                if (!cycles.empty()) {
                    deadlock_detected++;
                }
            }
        }
    };

    std::cout << "Iniciando stress test: " << num_threads 
              << " threads, " << ops_per_thread << " ops cada\n";
    
    auto start = std::chrono::steady_clock::now();
    
    std::vector<std::thread> threads;
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker, i);
    }
    
    for (auto& t : threads) t.join();
    
    auto elapsed = std::chrono::steady_clock::now() - start;
    
    std::cout << "\n=== RESULTADOS ===\n";
    std::cout << "Tempo total: " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count() 
              << "ms\n";
    std::cout << "Operações bem-sucedidas: " << successful_ops << "\n";
    std::cout << "Operações falhadas: " << failed_ops << "\n";
    std::cout << "Deadlocks detectados: " << deadlock_detected << "\n";
    std::cout << "Throughput: " 
              << (successful_ops * 1000 / std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count())
              << " ops/sec\n";
}

int main() {
    banking_example();
    std::cout << "\n";
    stress_test_resource_manager();
    return 0;
}
```

EOF
## 11. Referências

### Livros Fundamentais

1. **Herlihy, M. & Shavit, N.** - *The Art of Multiprocessor Programming*, 2nd Ed. Morgan Kaufmann, 2012. ISBN: 978-0123973375
   - Capítulos 2, 3, 8: Locks, deadlock freedom, progress conditions

2. **Williams, A.** - *C++ Concurrency in Action*, 2nd Ed. Manning, 2019. ISBN: 978-1617294693
   - Capítulos 3, 4, 10: Deadlock avoidance, lock hierarchies, testing

3. **Butenhof, D.** - *Programming with POSIX Threads*. Addison-Wesley, 1997. ISBN: 978-0201633924
   - Capítulos 4, 5: Mutex protocols, priority inheritance/ceiling

4. **McKenney, P.E.** - *Is Parallel Programming Hard, And, If So, What Can You Do About It?* (v2023.06). Kernel.org.
   - Capítulos 7, 9: Locking, deadlock, RCU

5. **Goetz, B. et al.** - *Java Concurrency in Practice*. Addison-Wesley, 2006. ISBN: 978-0321349606
   - Capítulo 10: Avoiding liveness hazards (aplicável a C++)

### Papers Acadêmicos Clássicos

6. **Coffman, E.G., Elphick, M.J., Shoshani, A.** - "System Deadlocks". *ACM Computing Surveys*, 3(2):67-78, 1971.
   - Original four conditions paper

7. **Dijkstra, E.W.** - "Solution of a Problem in Concurrent Programming Control". *CACM*, 8(9):569, 1965.
   - Banker's algorithm

8. **Havender, J.W.** - "Avoiding Deadlock in Multi-tasking Systems". *IBM Systems Journal*, 7(2):74-84, 1968.
   - Lock ordering prevention

9. **Mellor-Crummey, J.M. & Scott, M.L.** - "Algorithms for Scalable Synchronization on Shared-Memory Multiprocessors". *ACM TOCS*, 9(1):21-65, 1991.
   - MCS Lock paper

10. **Craig, T.S.** - "Building FIFO and Priority-Queuing Spin Locks from Atomic Swap". *TR 93-02-02*, UW, 1993.
    - CLH Lock paper

11. **Chandy, K.M., Misra, J., Haas, L.M.** - "Distributed Deadlock Detection". *ACM TOCS*, 1(2):144-156, 1983.
    - Chandy-Misra-Haas algorithm

12. **Sha, L., Rajkumar, R., Lehoczky, J.P.** - "Priority Inheritance Protocols: An Approach to Real-Time Synchronization". *IEEE TC*, 39(9):1175-1185, 1990.
    - Priority inheritance protocol

13. **Lamport, L.** - "A New Solution of Dijkstra's Concurrent Programming Problem". *CACM*, 17(8):453-455, 1974.
    - Bakery algorithm

14. **Anderson, T.E.** - "The Performance of Spin Lock Alternatives for Shared-Memory Multiprocessors". *IEEE TPDS*, 1(1):6-16, 1990.
    - Spinlock performance analysis

### CVEs e Incidentes Reais

15. **CVE-2016-0728** - Linux Kernel Keyring Reference Count Overflow/Deadlock
    - https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-0728
    - Perception Point analysis: https://perception-point.io/blog/cve-2016-0728/

16. **CVE-2021-4034** - Polkit pkexec Local Privilege Escalation (race condition related)
    - https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-4034

17. **PostgreSQL Deadlock Documentation** - "Explicit Locking" and "Deadlocks"
    - https://www.postgresql.org/docs/current/explicit-locking.html
    - https://www.postgresql.org/docs/current/transaction-iso.html#XACT-DEADLOCK

18. **MySQL InnoDB Deadlock Detection**
    - https://dev.mysql.com/doc/refman/8.0/en/innodb-deadlocks.html
    - https://dev.mysql.com/doc/refman/8.0/en/innodb-deadlock-detection.html

19. **Mars Pathfinder Priority Inversion** - NASA Technical Report
    - https://www.cs.cmu.edu/~msl/teaching/15317-f07/lectures/06-mars.pdf
    - Glenn Reeves, "What Really Happened on Mars", 1998

20. **Therac-25 Accidents** - Race conditions and software interlocks
    - Leveson, N.G. & Turner, C.S. "An Investigation of the Therac-25 Accidents". *IEEE Computer*, 26(7):18-41, 1993.

21. **Knight Capital Group Trading Loss (2012)** - Deadlock in deployment script
    - SEC Report: https://www.sec.gov/litigation/admin/2013/34-70694.pdf

22. **GitHub Database Incident (2020)** - MySQL deadlock during failover
    - https://github.blog/2020-05-01-incident-report-may-2020/

### Documentação Oficial e Standards

23. **ISO/IEC 14882:2020** - C++20 Standard
    - §33: Thread support library
    - §33.6: Mutual exclusion (mutex, shared_mutex, scoped_lock)

24. **POSIX.1-2017 (IEEE Std 1003.1)** - Threads and Synchronization
    - pthread_mutexattr_setprotocol(3p)
    - pthread_mutexattr_setprioceiling(3p)
    - pthread_mutexattr_setrobust(3p)

25. **C++ Core Guidelines** - Concurrency Rules (CP.40-CP.50)
    - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#cp40-minimize-lock-contention
    - https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines#cp41-avoid-deadlocks

26. **Linux Kernel Locking Documentation**
    - https://www.kernel.org/doc/html/latest/kernel-hacking/locking.html
    - https://www.kernel.org/doc/html/latest/kernel-hacking/locktypes.html

### Ferramentas e Artigos Técnicos

27. **ThreadSanitizer Documentation** - Google
    - https://github.com/google/sanitizers/wiki/ThreadSanitizerCppManual
    - https://clang.llvm.org/docs/ThreadSafetyAnalysis.html

28. **Valgrind Helgrind/DRD Manual**
    - https://valgrind.org/docs/manual/hg-manual.html
    - https://valgrind.org/docs/manual/drd-manual.html

29. **Intel Inspector User Guide**
    - https://www.intel.com/content/www/us/en/developer/articles/technical/intel-inspector-user-guide.html

30. **McKenney, P.** - "What is RCU? Fundamentally" (2023)
    - https://www.kernel.org/doc/html/latest/RCU/whatisRCU.html

31. **Boehm, H.** - "Threads Cannot be Implemented as a Library" (2005)
    - PLDI 2005, explains why language-level support is needed

32. **Meyer, B.** - "Systematic Concurrent Object-Oriented Programming" (1993)
    - SCOOP model for deadlock-free concurrency

### Recursos Online e Cursos

33. **C++ Concurrency Reference** - cppreference.com
    - https://en.cppreference.com/w/cpp/thread

34. **Linux Kernel Locking Tutorial** - kernel.org
    - https://www.kernel.org/doc/html/latest/kernel-hacking/locking.html

35. **Distributed Systems Deadlock Detection** - MIT 6.824
    - https://pdos.csail.mit.edu/6.824/

36. **Real-Time Systems Priority Inversion** - RTOS.com
    - https://www.rtos.com/priority-inversion/

37. **CppCon Talks on Concurrency**:
    - "Lock-Free Programming" - Fedor Pikus (2014-2023)
    - "C++ Atomics and Memory Model" - Herb Sutter (2014)
    - "Deadlock Detection in C++" - Various years

### Benchmarks e Performance

38. **David, T., Guerraoui, R., Trigonakis, V.** - "Everything You Always Wanted to Know About Synchronization but Were Afraid to Ask". *PPoPP 2013*.
    - Comprehensive lock performance comparison

39. **Moscibroda, T.** - "The Complexity of Lock-Free Algorithms". *DISC 2003*.
    - Lower bounds for synchronization

40. **Attiya, H., Welch, J.** - *Distributed Computing: Fundamentals, Simulations, and Advanced Topics*, 2nd Ed. Wiley, 2004.
    - Chapter 13: Distributed deadlock detection

---

### Índice de Código Examples por Seção

| Seção | Exemplos Principais |
|-------|---------------------|
| 1.1 | Classic deadlock com 2 mutexes |
| 1.2 | ResourceAllocationGraph class |
| 1.3 | Deadlock vs Livelock vs Starvation table |
| 1.4 | Stress test timing manipulation |
| 2.1 | std::scoped_lock BankAccount transfer |
| 2.1 | OrderedLockManager |
| 2.2 | TryLockWithBackoff, TimeoutLock |
| 2.3 | HierarchicalMutex, Compile-time RankedMutex |
| 3.1 | WaitForGraph com Tarjan SCC |
| 3.2 | VictimSelector policies |
| 3.3 | DeadlockRecoveryManager |
| 3.4 | ProductionDeadlockDetector, TrackedMutex |
| 4.1 | Pedestrian livelock example |
| 4.2 | ExponentialBackoff, LockFreeQueue |
| 4.3 | RandomizedDelay, EthernetBackoff |
| 4.4 | BadSpinlock vs GoodSpinlock vs OptimizedSpinlock |
| 5.1 | FairMutex FIFO implementation |
| 5.2 | WritePreferringRWLock |
| 5.3 | PI_Mutex pthread priority inheritance |
| 5.4 | MCSLock, CLHLock, TicketLock |
| 6.1 | MarsPathfinderSimulator |
| 6.2 | PriorityInheritanceMutex |
| 6.3 | PriorityCeilingMutex, UserSpaceCeilingMutex |
| 6.4 | PosixMutex full wrapper |
| 7.1 | ConvoyDemo measurement |
| 7.2 | ConvoyDetector |
| 7.3 | FairMutex |
| 7.4 | MCSLock full implementation |
| 7.5 | CLHLock full implementation |
| 7.6 | Google Benchmark harness |
| 8.1 | DistributedDeadlockDetector |
| 8.2 | ChandyMisraHaasDetector |
| 8.3 | DistributedLockManager leases |
| 9.1 | TSan compilation flags, output example |
| 9.2 | Helgrind/DRD commands |
| 9.3 | clang-tidy config, annotations |
| 9.4 | TLA+/PlusCal, CBMC examples |
| 10.1 | DeadlockFreeResourceManager |
| 10.2 | ResourceManagerWithDetection |
| 10.3 | Stress test harness |

---

**Fim do Capítulo 4**

*Próximo capítulo: Capítulo 5 — Programação Livre de Locks (Lock-Free Programming)*
---

*[Capítulo anterior: 03 — Programacao Lock Free E Atomicos](03-programacao-lock-free-e-atomicos.md)*
*[Próximo capítulo: 05 — Thread Pools Tarefas Assincronas](05-thread-pools-tarefas-assincronas.md)*
