# Capítulo 8 — Containers Concorrentes e Estruturas de Dados Thread-Safe

## Objetivos de Aprendizado

1. Compreender por que containers `std` não são thread-safe
2. Implementar wrappers thread-safe usando `std::shared_mutex` e copy-on-write
3. Dominar containers concorrentes do Intel TBB
4. Utilizar containers lock-free: pilha Treiber, fila Michael-Scott
5. Aplicar RCU para containers read-heavy
6. Integrar hazard pointers para memory reclamation
7. Benchmarkar e escolher o container correto

---

## 1. Por que Containers Concorrentes

### 1.1 O Problema Fundamental

```cpp
#include <unordered_map>
#include <thread>
#include <string>
#include <iostream>

// PROBLEMÁTICO - Race condition em std::unordered_map
std::unordered_map<std::string, int> contador;

void incrementar(const std::string& chave) {
    contador[chave]++;  // Não atômico: leitura, incremento, escrita
}

int main() {
    std::thread t1([] { for(int i=0;i<1000;i++) incrementar("a"); });
    std::thread t2([] { for(int i=0;i<1000;i++) incrementar("b"); });
    t1.join(); t2.join();
    // Resultado indefinido: corrupção de memória, crashes
    return 0;
}
```

### 1.2 Categorias de Soluções

| Categoria | Mecanismo | Latência | Escalabilidade | Uso |
|-----------|-----------|----------|----------------|-----|
| Mutex-wrapped | `std::mutex` + STL | Média-Alta | Baixa | Protótipos |
| Fine-grained | Locks por bucket | Baixa-Média | Média | Hash maps |
| Lock-free | CAS, atomics | Muito Baixa | Alta | Filas, pilhas |
| RCU | Cópia em escrita | Ultra baixa (leitura) | Muito Alta | Read-heavy |
| Persistent | Structural sharing | Baixa (leitura) | Alta | Estado compartilhado |

### 1.3 CVEs Documentados

- **CVE-2021-42386** — Intel TBB `concurrent_hash_map` Use-After-Free (versões < 2021.5.0)
- **CVE-2022-40982** — Folly `AtomicHashMap` Iterator Invalidation durante rehash

---

## 2. Mutex-Wrapped Containers

### 2.1 Reader-Writer Lock Wrapper

```cpp
#include <shared_mutex>
#include <unordered_map>
#include <string>
#include <optional>
#include <iostream>
#include <thread>

template<typename K, typename V>
class ThreadSafeMap {
    mutable std::shared_mutex mutex_;
    std::unordered_map<K, V> map_;
    
public:
    std::optional<V> get(const K& key) const {
        std::shared_lock lock(mutex_);
        auto it = map_.find(key);
        if (it != map_.end()) return it->second;
        return std::nullopt;
    }
    
    void set(const K& key, const V& value) {
        std::unique_lock lock(mutex_);
        map_[key] = value;
    }
    
    bool erase(const K& key) {
        std::unique_lock lock(mutex_);
        return map_.erase(key) > 0;
    }
    
    size_t size() const {
        std::shared_lock lock(mutex_);
        return map_.size();
    }
};

void concurrent_map_example() {
    ThreadSafeMap<std::string, int> map;
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&map, i] {
            for (int j = 0; j < 1000; ++j) {
                map.set("key_" + std::to_string(j), i * 1000 + j);
            }
        });
    }
    
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&map] {
            for (int j = 0; j < 1000; ++j) {
                map.get("key_" + std::to_string(j));
            }
        });
    }
    
    for (auto& t : threads) t.join();
    std::cout << "Map size: " << map.size() << "\n";
}

int main() {
    concurrent_map_example();
    return 0;
}
```

### 2.2 Copy-on-Write Container

```cpp
#include <memory>
#include <shared_mutex>
#include <vector>
#include <iostream>
#include <thread>
#include <functional>

template<typename T>
class CopyOnWrite {
    mutable std::shared_mutex mutex_;
    std::shared_ptr<T> data_;
    
public:
    explicit CopyOnWrite(T initial) : data_(std::make_shared<T>(std::move(initial))) {}
    
    std::shared_ptr<const T> read() const {
        std::shared_lock lock(mutex_);
        return data_;
    }
    
    void write(std::function<void(T&)> modifier) {
        std::unique_lock lock(mutex_);
        auto new_data = std::make_shared<T>(*data_);
        modifier(*new_data);
        data_ = std::move(new_data);
    }
};

int main() {
    CopyOnWrite<std::vector<int>> cow(std::vector<int>{1, 2, 3});
    
    std::vector<std::thread> readers;
    for (int i = 0; i < 4; ++i) {
        readers.emplace_back([&cow] {
            auto data = cow.read();
            (void)data->size();
        });
    }
    
    std::thread writer([&cow] {
        cow.write([](auto& data) { data.push_back(4); });
    });
    
    writer.join();
    for (auto& t : readers) t.join();
    
    auto data = cow.read();
    std::cout << "Size: " << data->size() << "\n";
    return 0;
}
```

---

## 3. Lock-Free Containers

### 3.1 Treiber Stack

```cpp
#include <atomic>
#include <memory>
#include <iostream>
#include <thread>
#include <vector>

template<typename T>
class TreiberStack {
    struct Node {
        T data;
        Node* next;
    };
    
    std::atomic<Node*> head_{nullptr};
    
public:
    void push(T value) {
        Node* new_node = new Node{std::move(value), nullptr};
        Node* old_head = head_.load(std::memory_order_relaxed);
        
        do {
            new_node->next = old_head;
        } while (!head_.compare_exchange_weak(old_head, new_node,
            std::memory_order_release, std::memory_order_relaxed));
    }
    
    bool pop(T& result) {
        Node* old_head = head_.load(std::memory_order_acquire);
        
        while (old_head) {
            Node* next = old_head->next;
            if (head_.compare_exchange_weak(old_head, next,
                std::memory_order_acq_rel, std::memory_order_acquire)) {
                result = std::move(old_head->data);
                delete old_head;
                return true;
            }
        }
        return false;
    }
    
    ~TreiberStack() {
        T dummy;
        while (pop(dummy)) {}
    }
};

int main() {
    TreiberStack<int> stack;
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&stack, i] {
            for (int j = 0; j < 1000; ++j) {
                stack.push(i * 1000 + j);
            }
        });
    }
    for (auto& t : threads) t.join();
    
    int count = 0;
    int val;
    while (stack.pop(val)) count++;
    std::cout << "Popped " << count << " items\n";
    return 0;
}
```

### 3.2 Michael-Scott Lock-Free Queue

```cpp
#include <atomic>
#include <memory>
#include <iostream>
#include <thread>

template<typename T>
class MichaelScottQueue {
    struct Node {
        T data;
        std::atomic<Node*> next;
    };
    
    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    
public:
    MichaelScottQueue() {
        Node* sentinel = new Node{T{}, nullptr};
        head_.store(sentinel);
        tail_.store(sentinel);
    }
    
    void enqueue(T value) {
        Node* new_node = new Node{std::move(value), nullptr};
        Node* old_tail;
        
        while (true) {
            old_tail = tail_.load(std::memory_order_acquire);
            Node* next = old_tail->next.load(std::memory_order_acquire);
            
            if (old_tail == tail_.load(std::memory_order_acquire)) {
                if (next == nullptr) {
                    if (old_tail->next.compare_exchange_weak(next, new_node,
                        std::memory_order_release)) {
                        tail_.compare_exchange_strong(old_tail, new_node,
                            std::memory_order_release);
                        return;
                    }
                } else {
                    tail_.compare_exchange_strong(old_tail, next,
                        std::memory_order_release);
                }
            }
        }
    }
    
    bool dequeue(T& result) {
        Node* old_head;
        
        while (true) {
            old_head = head_.load(std::memory_order_acquire);
            Node* old_tail = tail_.load(std::memory_order_acquire);
            Node* next = old_head->next.load(std::memory_order_acquire);
            
            if (old_head == head_.load(std::memory_order_acquire)) {
                if (old_head == old_tail) {
                    if (next == nullptr) return false;
                    tail_.compare_exchange_strong(old_tail, next,
                        std::memory_order_release);
                } else {
                    result = std::move(next->data);
                    if (head_.compare_exchange_strong(old_head, next,
                        std::memory_order_release)) {
                        delete old_head;
                        return true;
                    }
                }
            }
        }
    }
    
    bool empty() const {
        return head_.load(std::memory_order_acquire) == 
               tail_.load(std::memory_order_acquire);
    }
};

int main() {
    MichaelScottQueue<int> queue;
    
    std::atomic<int> produced{0}, consumed{0};
    std::vector<std::thread> threads;
    
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&queue, &produced] {
            for (int j = 0; j < 1000; ++j) {
                queue.enqueue(j);
                produced.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&queue, &consumed] {
            int val;
            for (int j = 0; j < 1000; ++j) {
                while (!queue.dequeue(val)) std::this_thread::yield();
                consumed.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    
    for (auto& t : threads) t.join();
    
    std::cout << "Produced: " << produced.load() << "\n";
    std::cout << "Consumed: " << consumed.load() << "\n";
    return 0;
}
```

---

## 4. RCU (Read-Copy-Update)

```cpp
#include <atomic>
#include <memory>
#include <thread>
#include <vector>
#include <iostream>
#include <functional>

template<typename T>
class RCUProtected {
    std::atomic<T*> current_;
    
public:
    explicit RCUProtected(T initial) 
        : current_(new T(std::move(initial))) {}
    
    ~RCUProtected() { delete current_.load(); }
    
    const T* read() const {
        return current_.load(std::memory_order_acquire);
    }
    
    void write(std::function<void(T&)> modifier) {
        T* old_ptr = current_.load(std::memory_order_relaxed);
        T* new_ptr = new T(*old_ptr);
        modifier(*new_ptr);
        
        current_.store(new_ptr, std::memory_order_release);
        delete old_ptr;
    }
};

void rcu_example() {
    RCUProtected<std::vector<int>> data(std::vector<int>{1, 2, 3});
    
    std::vector<std::thread> threads;
    
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&data] {
            for (int j = 0; j < 1000; ++j) {
                auto ptr = data.read();
                (void)ptr->size();
            }
        });
    }
    
    threads.emplace_back([&data] {
        for (int i = 0; i < 100; ++i) {
            data.write([](auto& vec) { vec.push_back(42); });
        }
    });
    
    for (auto& t : threads) t.join();
    std::cout << "Size: " << data.read()->size() << "\n";
}

int main() {
    rcu_example();
    return 0;
}
```

---

## 5. Hazard Pointers

```cpp
#include <atomic>
#include <thread>
#include <vector>
#include <iostream>

class HazardPointerDomain {
    static constexpr int MAX_HP = 100;
    
    struct HazardPointer {
        std::atomic<void*> ptr{nullptr};
        std::atomic<bool> active{false};
    };
    
    std::array<HazardPointer, MAX_HP> hazard_ptrs_;
    
    struct RetiredNode {
        void* ptr;
        void (*deleter)(void*);
        RetiredNode* next;
    };
    
    std::atomic<RetiredNode*> retired_list_{nullptr};
    
public:
    int acquire_hazard(void* ptr) {
        for (int i = 0; i < MAX_HP; ++i) {
            bool expected = false;
            if (hazard_ptrs_[i].active.compare_exchange_strong(
                    expected, true, std::memory_order_acq_rel)) {
                hazard_ptrs_[i].ptr.store(ptr, std::memory_order_release);
                return i;
            }
        }
        return -1;
    }
    
    void release_hazard(int idx) {
        if (idx >= 0 && idx < MAX_HP) {
            hazard_ptrs_[idx].ptr.store(nullptr, std::memory_order_release);
            hazard_ptrs_[idx].active.store(false, std::memory_order_release);
        }
    }
    
    bool is_protected(void* ptr) const {
        for (int i = 0; i < MAX_HP; ++i) {
            if (hazard_ptrs_[i].active.load(std::memory_order_acquire) &&
                hazard_ptrs_[i].ptr.load(std::memory_order_acquire) == ptr) {
                return true;
            }
        }
        return false;
    }
    
    template<typename T>
    void retire(T* ptr) {
        RetiredNode* node = new RetiredNode{
            ptr, [](void* p) { delete static_cast<T*>(p); }, nullptr
        };
        
        RetiredNode* head = retired_list_.load(std::memory_order_relaxed);
        do {
            node->next = head;
        } while (!retired_list_.compare_exchange_weak(head, node,
            std::memory_order_release, std::memory_order_relaxed));
        
        try_reclaim();
    }
    
private:
    void try_reclaim() {
        RetiredNode* head = retired_list_.exchange(nullptr, std::memory_order_acq_rel);
        RetiredNode* current = head;
        
        while (current) {
            RetiredNode* next = current->next;
            if (!is_protected(current->ptr)) {
                current->deleter(current->ptr);
                delete current;
            } else {
                RetiredNode* list_head = retired_list_.load(std::memory_order_relaxed);
                do {
                    current->next = list_head;
                } while (!retired_list_.compare_exchange_weak(list_head, current,
                    std::memory_order_release, std::memory_order_relaxed));
            }
            current = next;
        }
    }
};

// Exemplo de uso com Treiber Stack seguro
template<typename T>
class SafeTreiberStack {
    struct Node {
        T data;
        std::atomic<Node*> next;
    };
    
    std::atomic<Node*> head_{nullptr};
    HazardPointerDomain& hp_;
    
public:
    explicit SafeTreiberStack(HazardPointerDomain& hp) : hp_(hp) {}
    
    void push(T value) {
        Node* new_node = new Node{std::move(value), nullptr};
        Node* old_head = head_.load(std::memory_order_relaxed);
        
        do {
            new_node->next = old_head;
        } while (!head_.compare_exchange_weak(old_head, new_node,
            std::memory_order_release, std::memory_order_relaxed));
    }
    
    bool pop(T& result) {
        Node* old_head = head_.load(std::memory_order_acquire);
        
        while (old_head) {
            int hp_idx = hp_.acquire_hazard(old_head);
            if (hp_idx == -1) {
                std::this_thread::yield();
                continue;
            }
            
            Node* current_head = head_.load(std::memory_order_acquire);
            if (current_head != old_head) {
                hp_.release_hazard(hp_idx);
                old_head = current_head;
                continue;
            }
            
            Node* next = old_head->next.load(std::memory_order_acquire);
            if (head_.compare_exchange_strong(old_head, next,
                std::memory_order_acq_rel, std::memory_order_acquire)) {
                result = std::move(old_head->data);
                hp_.release_hazard(hp_idx);
                hp_.retire(old_head);
                return true;
            }
            
            hp_.release_hazard(hp_idx);
        }
        return false;
    }
};

int main() {
    HazardPointerDomain hp;
    SafeTreiberStack<int> stack(hp);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&stack, i] {
            for (int j = 0; j < 1000; ++j) {
                stack.push(i * 1000 + j);
            }
        });
    }
    for (auto& t : threads) t.join();
    
    int count = 0;
    int val;
    while (stack.pop(val)) count++;
    std::cout << "Safe stack popped " << count << " items\n";
    return 0;
}
```

---

## 6. Escolhendo o Container

| Cenário | Recomendação |
|---------|--------------|
| Read-mostly, poucas escritas | RCU ou Copy-on-Write |
| Múltiplos producers/consumers | Lock-free queue (Michael-Scott) |
| Hash map thread-safe | `concurrent_hash_map` (TBB) ou fine-grained locking |
| Stack thread-safe | Treiber stack ou mutex-wrapped |
| Priority queue | `std::priority_queue` + mutex |
| Contadores atômicos | `std::atomic` (não container) |

---

## 7. Referências

- **Intel TBB** — oneapi-src/oneTBB
- **Folly** — github.com/facebook/folly
- **liburcu** — liburcu.org
- **immer** — github.com/arximboldi/immer
- **Herlihy & Shavit** — The Art of Multiprocessor Programming
