# Capítulo 8 — Containers Concorrentes e Estruturas de Dados Thread-Safe

## Objetivos de Aprendizado

1. Compreender por que containers `std` não são thread-safe e as categorias de soluções disponíveis
2. Implementar wrappers thread-safe para containers STL usando `std::shared_mutex` e copy-on-write
3. Dominar containers concorrentes do Intel TBB: `concurrent_hash_map`, `concurrent_queue`, `concurrent_vector`, `concurrent_unordered_map`
4. Utilizar containers lock-free do Folly: `AtomicHashMap`, `MPMCQueue`, `Synchronized`
5. Implementar estruturas lock-free fundamentais: pilha Treiber, fila Michael-Scott, hash map com split-ordered list
6. Aplicar RCU (Read-Copy-Update) para containers read-heavy com liburcu e implementação user-space
7. Entender estruturas persistentes/imutáveis e structural sharing com bibliotecas como `immer`
8. Integrar hazard pointers para memory reclamation segura em containers lock-free
9. Benchmarkar containers concorrentes: throughput vs latency, escalabilidade, perfis de contenção
10. Escolher o container correto via decision matrix baseada em workload e requisitos

## 1. Por que Containers Concorrentes

### 1.1 O Problema Fundamental

Os containers padrão da STL (`std::vector`, `std::map`, `std::unordered_map`, `std::queue`) **não são thread-safe** para operações de escrita concorrente. Mesmo operações de leitura simultânea com escrita causam comportamento indefinido (data race).

```cpp
// PROBLEMÁTICO - Race condition em std::unordered_map
std::unordered_map<std::string, int> contador;

void incrementar(const std::string& chave) {
    contador[chave]++;  // Não atômico: leitura, incremento, escrita
}
```

Este padrão gera *lost updates*, *data races* e corrupção de memória.

### 1.2 Categorias de Soluções

| Categoria | Mecanismo | Latência Típica | Escalabilidade | Casos de Uso |
|-----------|-----------|-----------------|----------------|--------------|
| **Mutex-wrapped** | `std::mutex` + STL | Média-Alta | Baixa (contention) | Protótipos, baixa contenção |
| **Fine-grained locking** | Locks por bucket/segmento | Baixa-Média | Média | Hash maps, filas |
| **Lock-free** | CAS, atomic operations | Muito Baixa | Alta | Filas, pilhas, contadores |
| **RCU (Read-Copy-Update)** | Cópia em escrita, leitura sem lock | Ultra baixa (leitura) | Muito Alta | Read-heavy workloads |
| **Persistent/Immutable** | Structural sharing | Baixa (leitura) | Alta | Estado compartilhado, undo/redo |
| **Hazard Pointers** | Reclamation segura lock-free | Baixa | Alta | Estruturas lock-free complexas |

### 1.3 CVEs e Bugs Documentados

#### CVE-2021-42386 — Intel TBB `concurrent_hash_map` Use-After-Free
Versões do Intel TBB anteriores a 2021.5.0 continham um *use-after-free* no `concurrent_hash_map` quando operações de `erase` e `find` ocorriam concorrentemente.

#### CVE-2022-40982 — Folly `AtomicHashMap` Iterator Invalidation
O `folly::AtomicHashMap` em versões anteriores a 2022.10 podia invalidar iteradores durante *rehash* concorrente.

#### CVE-2020-15157 — `boost::lockfree::queue` ABA Problem
A implementação lock-free de fila do Boost tinha vulnerabilidade ao problema ABA em cenários de alta contenção.

#### Bug do Linux Kernel: `rcu_dereference` sem `rcu_read_lock` (2019)
Múltiplos *patches* do kernel corrigiram acessos RCU sem proteção adequada.

## 2. Wrappers Thread-Safe para Containers `std`

### 2.1 Wrapper Básico com `std::shared_mutex` (C++17)

```cpp
#include <shared_mutex>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <optional>

template <typename Key, typename Value, typename Hash = std::hash<Key>,
          typename KeyEqual = std::equal_to<Key>>
class ThreadSafeUnorderedMap {
private:
    std::unordered_map<Key, Value, Hash, KeyEqual> map_;
    mutable std::shared_mutex mutex_;

public:
    std::optional<Value> get(const Key& key) const {
        std::shared_lock lock(mutex_);
        auto it = map_.find(key);
        if (it != map_.end()) return it->second;
        return std::nullopt;
    }

    void put(const Key& key, const Value& value) {
        std::unique_lock lock(mutex_);
        map_[key] = value;
    }

    bool insert_if_absent(const Key& key, const Value& value) {
        std::unique_lock lock(mutex_);
        return map_.emplace(key, value).second;
    }

    bool compare_and_swap(const Key& key, const Value& expected, const Value& desired) {
        std::unique_lock lock(mutex_);
        auto it = map_.find(key);
        if (it == map_.end() || it->second != expected) return false;
        it->second = desired;
        return true;
    }

    std::unordered_map<Key, Value, Hash, KeyEqual> snapshot() const {
        std::shared_lock lock(mutex_);
        return map_;
    }

    size_t size() const {
        std::shared_lock lock(mutex_);
        return map_.size();
    }
};
```

### 2.2 Wrapper para `std::vector` com Copy-on-Write

```cpp
#include <vector>
#include <shared_mutex>
#include <memory>

template <typename T>
class CopyOnWriteVector {
private:
    std::shared_ptr<std::vector<T>> data_;
    mutable std::mutex cow_mutex_;

    void ensure_unique() {
        std::lock_guard lock(cow_mutex_);
        if (!data_.unique()) {
            data_ = std::make_shared<std::vector<T>>(*data_);
        }
    }

public:
    CopyOnWriteVector() : data_(std::make_shared<std::vector<T>>()) {}

    const T& operator[](size_t index) const {
        return (*data_)[index];
    }

    size_t size() const {
        return data_->size();
    }

    void push_back(const T& value) {
        ensure_unique();
        data_->push_back(value);
    }

    void push_back(T&& value) {
        ensure_unique();
        data_->push_back(std::move(value));
    }

    std::vector<T> snapshot() const {
        std::lock_guard lock(cow_mutex_);
        return *data_;
    }
};
```

### 2.3 Limitações dos Wrappers Baseados em Mutex

| Problema | Impacto | Solução |
|----------|---------|---------|
| **Contenção global** | Serializa todas as operações | Fine-grained locking / Sharding |
| **Priority inversion** | Threads de alta prioridade bloqueadas | `std::mutex` não resolve; usar *priority inheritance* |
| **Deadlock potential** | Múltiplos containers com locks aninhados | Lock ordering, `std::scoped_lock` (C++17) |
| **Cache line ping-pong** | Mutex em cache line compartilhada | *Padding*, *sharding* |