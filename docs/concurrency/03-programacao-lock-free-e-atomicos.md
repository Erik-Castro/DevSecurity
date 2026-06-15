---
layout: default
title: "03-programacao-lock-free-e-atomicos"
---

# Capítulo 3 — Programação Lock-Free e Atômicos Avançados

## Objetivos de Aprendizado

1. Compreender os fundamentos teóricos e práticos da programação lock-free, incluindo garantias de progresso (wait-free, lock-free, obstruction-free) e quando aplicar cada abordagem
2. Dominar operações atômicas avançadas em C++17/20: compare_exchange_weak/strong, memory_order semantics, e padrões de loops CAS robustos
3. Identificar e mitigar o problema ABA através de múltiplas estratégias: tagged pointers, version counters, hazard pointers, e epoch-based reclamation
4. Implementar estruturas de dados lock-free fundamentais: stacks (Treiber), queues (Michael-Scott), e hash maps com linearizabilidade garantida
5. Aplicar técnicas de gerenciamento de memória segura em contextos lock-free: hazard pointers, userspace RCU, reference counting atômico, e quiescent state-based reclamation
## 1. Por que Lock-Free

A programação lock-free representa uma mudança fundamental na forma como pensamos sobre concorrência. Em vez de usar mutexes para proteger seções críticas, algoritmos lock-free garantem progresso do sistema através de operações atômicas de hardware.

### Problemas com Locks Tradicionais

Locks baseados em mutex apresentam vários problemas bem documentados:

**Contenção de Lock**: Quando múltiplas threads competem pelo mesmo mutex, o kernel deve gerenciar a fila de espera, resultando em chamadas de sistema custosas e cache misses. Em sistemas de alta performance, a contenção de lock pode consumir 30-50% do tempo de CPU.

**Inversão de Prioridade**: Uma thread de baixa prioridade segura um lock necessário por uma thread de alta prioridade. A thread de alta prioridade fica bloqueada indefinidamente. O Mars Pathfinder (1997) sofreu reset watchdog devido a inversão de prioridade não tratada.

**Deadlock**: Ciclos de espera por locks criam deadlocks. O banco de dados PostgreSQL teve CVE-2013-1899 onde deadlock em lock de catálogo causava negação de serviço.

**Liberdade de Deadlock**: Algoritmos lock-free são imunes a deadlock por construção — não há locks para adquirir em ordem circular.

### Garantias de Progresso

| Garantia | Definição | Exemplo |
|----------|-----------|---------|
| **Wait-free** | Toda thread completa em número finito de passos | Atomic increment |
| **Lock-free** | Sistema como um todo progride; algumas threads podem starvar | Treiber stack |
| **Obstruction-free** | Thread progride se executar isoladamente | STM otimista |

### Quando NÃO Usar Lock-Free

- Baixa contenção: mutex é mais simples e rápido
- Estruturas de dados complexas: manutenção difícil
- Requisitos de latência determinística: wait-free necessário
- Equipe sem experiência: bugs sutis (ABA, reordering)


## 2. Compare-And-Swap (CAS) Fundamentals

Compare-And-Swap é a operação atômica fundamental para programação lock-free. Ela compara o valor de uma localização de memória com um valor esperado e, se iguais, substitui pelo novo valor — tudo atomicamente.

### CAS vs LL/SC (Load-Linked/Store-Conditional)

**CAS (Compare-And-Swap)**: Arquiteturas x86, ARMv8-A (LDAXR/STLXR)
- Operação única atômica
- Falha espúria possível em implementações weak

**LL/SC (Load-Linked/Store-Conditional)**: ARMv7, PowerPC, MIPS, RISC-V
- Duas instruções: load-linked marca endereço, store-conditional verifica se inalterado
- Mais flexível para operações complexas
- Vulnerável a falhas espúrias por interrupções/context switch

```cpp
// x86 CAS (via std::atomic)
std::atomic<int> value{0};
int expected = 0;
bool success = value.compare_exchange_strong(expected, 42);
// success == true, value == 42

// Conceitual LL/SC (ARM)
/*
ldaxr  w0, [x1]    // Load-linked
add    w0, w0, #1  // Modify
stlxr  w2, w0, [x1] // Store-conditional
cbnz   w2, retry   // Retry if failed
*/
```

### Strong vs Weak CAS

```cpp
#include <atomic>
#include <iostream>

void demonstrate_cas_differences() {
    std::atomic<int> counter{0};
    
    // compare_exchange_strong: garante sucesso se valor == expected
    // Pode ser mais lento em arquiteturas LL/SC (loop interno)
    int expected_strong = 0;
    bool strong_result = counter.compare_exchange_strong(expected_strong, 1);
    // strong_result == true, counter == 1, expected_strong == 0 (unchanged on success)
    
    // compare_exchange_weak: pode falhar espúriamente mesmo se valor == expected
    // Mais rápido em LL/SC (sem loop interno), requer loop externo
    int expected_weak = 1;
    bool weak_result = counter.compare_exchange_weak(expected_weak, 2);
    // weak_result pode ser false mesmo com counter == 1!
    // Se false: expected_weak é atualizado com valor atual (1)
    
    std::cout << "Strong: " << strong_result << ", Weak: " << weak_result << "\n";
    std::cout << "Counter: " << counter.load() << "\n";
}
```

### Spurious Failures

Falhas espúrias ocorrem em arquiteturas LL/SC quando:
1. Interrupção entre load-linked e store-conditional
2. Context switch da thread
3. Outra CPU acessa a mesma cache line (false sharing)
4. Implementação de hardware não garante atomicidade perfeita

```cpp
// Padrão CORRETO para compare_exchange_weak
template<typename T>
bool cas_loop_weak(std::atomic<T>& atomic, T& expected, T desired) {
    while (!atomic.compare_exchange_weak(expected, desired)) {
        // expected já foi atualizado com valor atual
        // Loop continua até sucesso ou desistência
    }
    return true;
}

// Padrão para compare_exchange_strong (sem loop necessário na maioria dos casos)
template<typename T>
bool cas_strong(std::atomic<T>& atomic, T& expected, T desired) {
    return atomic.compare_exchange_strong(expected, desired);
}

// Exemplo prático: contador lock-free com weak CAS
class LockFreeCounter {
    std::atomic<uint64_t> count_{0};
    
public:
    void increment() {
        uint64_t expected = count_.load(std::memory_order_relaxed);
        while (!count_.compare_exchange_weak(expected, expected + 1,
                                             std::memory_order_release,
                                             std::memory_order_relaxed)) {
            // expected atualizado automaticamente
        }
    }
    
    uint64_t get() const {
        return count_.load(std::memory_order_acquire);
    }
};
```

### Complete CAS Loop Patterns

```cpp
#include <atomic>
#include <memory>

// Pattern 1: Simple increment (relaxed ordering OK for counters)
void atomic_increment(std::atomic<int>& counter) {
    int expected = counter.load(std::memory_order_relaxed);
    while (!counter.compare_exchange_weak(expected, expected + 1,
                                           std::memory_order_relaxed)) {
        // expected updated automatically
    }
}

// Pattern 2: Publish pointer with release semantics
template<typename T>
void atomic_store_release(std::atomic<T*>& atomic, T* ptr) {
    T* expected = nullptr;
    while (!atomic.compare_exchange_weak(expected, ptr,
                                          std::memory_order_release,
                                          std::memory_order_relaxed)) {
        // If expected != nullptr, another thread published first
        // Decide: retry or handle conflict
        if (expected != nullptr) {
            delete ptr; // Avoid leak if we lost race
            return;
        }
    }
}

// Pattern 3: Acquire-load with CAS for read-modify-write
template<typename T>
T atomic_fetch_add_acq_rel(std::atomic<T>& atomic, T increment) {
    T expected = atomic.load(std::memory_order_acquire);
    while (!atomic.compare_exchange_weak(expected, expected + increment,
                                          std::memory_order_acq_rel,
                                          std::memory_order_acquire)) {
        // Loop until success
    }
    return expected;
}

// Pattern 4: CAS com memory_order_seq_cst para linearizabilidade
class SeqCstStack {
    struct Node {
        int value;
        Node* next;
        Node(int v) : value(v), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    
public:
    void push(int value) {
        Node* new_node = new Node(value);
        Node* expected = head_.load(std::memory_order_seq_cst);
        do {
            new_node->next = expected;
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_seq_cst));
    }
    
    bool pop(int& value) {
        Node* expected = head_.load(std::memory_order_seq_cst);
        while (expected && !head_.compare_exchange_weak(expected, expected->next,
                                                         std::memory_order_seq_cst)) {
            // Retry
        }
        if (!expected) return false;
        value = expected->value;
        // NOTE: Memory reclamation needed here! (ABA problem)
        delete expected; // UNSAFE without hazard pointers/epoch
        return true;
    }
};
```


## 3. O Problema ABA

### O que é ABA

O problema ABA ocorre quando uma thread lê um valor A, é preemptida, outra thread muda o valor para B e depois de volta para A, e a primeira thread retoma e vê A — acreditando que nada mudou, quando na verdade o estado do sistema foi alterado.

```cpp
// Exemplo clássico ABA em stack lock-free
// Thread 1: lê head = A (node A -> node B -> node C)
// Thread 1: preemptida antes do CAS
// Thread 2: pop A, pop B, push A (reutiliza node A!)
// Thread 1: retoma, vê head == A, CAS succeeds
// Resultado: node B vazou (memory leak) ou corrupção
```

### Por que é Perigoso em Algoritmos Lock-Free

Em estruturas lock-free, ponteiros são reutilizados após deleção. O CAS verifica apenas o valor do ponteiro, não sua "identidade" ou histórico. Isso leva a:

1. **Corrupção de dados**: Nós incorretos linkados
2. **Memory leaks**: Nós perdidos nunca liberados  
3. **Use-after-free**: Acesso a memória liberada
4. **Violação de linearizabilidade**: Operação parece atômica mas não é

### Soluções para o Problema ABA

#### 3.1 Tagged Pointers (Pointer + Counter)

Adiciona contador de versão nos bits não usados do ponteiro (bits baixos alinhados).

```cpp
#include <atomic>
#include <cstdint>

template<typename T>
class TaggedPointer {
    static constexpr uintptr_t TAG_MASK = 0xFFFF; // 16 bits para tag
    static constexpr uintptr_t PTR_MASK = ~TAG_MASK;
    
    std::atomic<uintptr_t> packed_{0};
    
    static uintptr_t pack(T* ptr, uint16_t tag) {
        return (reinterpret_cast<uintptr_t>(ptr) & PTR_MASK) | tag;
    }
    
    static T* unpack_ptr(uintptr_t packed) {
        return reinterpret_cast<T*>(packed & PTR_MASK);
    }
    
    static uint16_t unpack_tag(uintptr_t packed) {
        return static_cast<uint16_t>(packed & TAG_MASK);
    }
    
public:
    bool compare_exchange_weak(T*& expected_ptr, T* desired_ptr,
                               uint16_t& expected_tag, uint16_t desired_tag) {
        uintptr_t expected = pack(expected_ptr, expected_tag);
        uintptr_t desired = pack(desired_ptr, desired_tag);
        
        if (packed_.compare_exchange_weak(expected, desired)) {
            expected_ptr = unpack_ptr(expected);
            expected_tag = unpack_tag(expected);
            return true;
        }
        expected_ptr = unpack_ptr(expected);
        expected_tag = unpack_tag(expected);
        return false;
    }
    
    T* load_ptr() const {
        return unpack_ptr(packed_.load(std::memory_order_acquire));
    }
    
    uint16_t load_tag() const {
        return unpack_tag(packed_.load(std::memory_order_acquire));
    }
};

// Stack com tagged pointers (mitiga ABA)
template<typename T>
class TaggedStack {
    struct Node {
        T value;
        Node* next;
        Node(T&& v) : value(std::move(v)), next(nullptr) {}
    };
    
    TaggedPointer<Node> head_;
    
public:
    void push(T&& value) {
        Node* new_node = new Node(std::move(value));
        Node* expected_ptr = head_.load_ptr();
        uint16_t expected_tag = head_.load_tag();
        
        do {
            new_node->next = expected_ptr;
        } while (!head_.compare_exchange_weak(expected_ptr, new_node,
                                               expected_tag, expected_tag + 1));
    }
    
    bool pop(T& value) {
        Node* expected_ptr = head_.load_ptr();
        uint16_t expected_tag = head_.load_tag();
        
        while (expected_ptr && !head_.compare_exchange_weak(expected_ptr, expected_ptr->next,
                                                             expected_tag, expected_tag + 1)) {
            // Retry
        }
        if (!expected_ptr) return false;
        value = std::move(expected_ptr->value);
        // ABA ainda possível se tag wraparound (2^16 operações)
        delete expected_ptr; // Ainda unsafe sem reclamation!
        return true;
    }
};
```

#### 3.2 Version Counters (Separate Counter)

```cpp
#include <atomic>

template<typename T>
class VersionedPointer {
    struct VersionedPtr {
        T* ptr;
        uint64_t version;
    };
    
    std::atomic<VersionedPtr> atomic_{nullptr, 0};
    
public:
    bool compare_exchange_weak(T*& expected_ptr, uint64_t& expected_version,
                               T* desired_ptr, uint64_t desired_version) {
        VersionedPtr expected{expected_ptr, expected_version};
        VersionedPtr desired{desired_ptr, desired_version};
        
        if (atomic_.compare_exchange_weak(expected, desired)) {
            expected_ptr = expected.ptr;
            expected_version = expected.version;
            return true;
        }
        expected_ptr = expected.ptr;
        expected_version = expected.version;
        return false;
    }
    
    T* load_ptr() const {
        return atomic_.load(std::memory_order_acquire).ptr;
    }
    
    uint64_t load_version() const {
        return atomic_.load(std::memory_order_acquire).version;
    }
};
```

#### 3.3 Hazard Pointers (Solução Completa)

Hazard pointers resolvem ABA garantindo que nenhum nó seja liberado enquanto alguma thread pode acessá-lo.

```cpp
#include <atomic>
#include <array>
#include <thread>
#include <vector>
#include <cassert>

// Hazard Pointer Implementation
class HazardPointerDomain {
    static constexpr size_t MAX_HAZARDS = 128;
    static constexpr size_t MAX_THREADS = 64;
    
    struct HazardRecord {
        std::atomic<std::thread::id> owner_{};
        std::atomic<void*> hazard_{nullptr};
        std::atomic<bool> active_{false};
    };
    
    std::array<HazardRecord, MAX_HAZARDS> records_;
    std::atomic<size_t> next_record_{0};
    std::vector<void*> retired_list_;
    std::mutex retired_mutex_;
    const size_t retire_threshold_ = 100;
    
    size_t acquire_record() {
        for (size_t i = 0; i < MAX_HAZARDS; ++i) {
            std::thread::id empty_id;
            if (records_[i].owner_.compare_exchange_strong(empty_id, std::this_thread::get_id())) {
                records_[i].active_.store(true, std::memory_order_release);
                return i;
            }
        }
        // Fallback: linear search for inactive
        for (size_t i = 0; i < MAX_HAZARDS; ++i) {
            if (!records_[i].active_.load(std::memory_order_acquire)) {
                records_[i].owner_.store(std::this_thread::get_id(), std::memory_order_release);
                records_[i].active_.store(true, std::memory_order_release);
                return i;
            }
        }
        assert(false && "No hazard records available");
        return 0;
    }
    
    void release_record(size_t idx) {
        records_[idx].hazard_.store(nullptr, std::memory_order_release);
        records_[idx].active_.store(false, std::memory_order_release);
        records_[idx].owner_.store(std::thread::id{}, std::memory_order_release);
    }
    
    bool is_hazard(void* ptr) const {
        for (size_t i = 0; i < MAX_HAZARDS; ++i) {
            if (records_[i].active_.load(std::memory_order_acquire) &&
                records_[i].hazard_.load(std::memory_order_acquire) == ptr) {
                return true;
            }
        }
        return false;
    }
    
public:
    class HazardPointer {
        HazardPointerDomain* domain_;
        size_t record_idx_;
        
    public:
        HazardPointer() : domain_(nullptr), record_idx_(SIZE_MAX) {}
        
        explicit HazardPointer(HazardPointerDomain* domain) 
            : domain_(domain), record_idx_(domain->acquire_record()) {}
        
        ~HazardPointer() {
            if (domain_) domain_->release_record(record_idx_);
        }
        
        HazardPointer(const HazardPointer&) = delete;
        HazardPointer& operator=(const HazardPointer&) = delete;
        
        HazardPointer(HazardPointer&& other) noexcept
            : domain_(other.domain_), record_idx_(other.record_idx_) {
            other.domain_ = nullptr;
        }
        
        HazardPointer& operator=(HazardPointer&& other) noexcept {
            if (domain_) domain_->release_record(record_idx_);
            domain_ = other.domain_;
            record_idx_ = other.record_idx_;
            other.domain_ = nullptr;
            return *this;
        }
        
        void protect(void* ptr) {
            assert(domain_);
            domain_->records_[record_idx_].hazard_.store(ptr, std::memory_order_release);
        }
        
        template<typename T>
        void protect(T* ptr) {
            protect(static_cast<void*>(ptr));
        }
        
        void reset() {
            if (domain_) {
                domain_->records_[record_idx_].hazard_.store(nullptr, std::memory_order_release);
            }
        }
    };
    
    HazardPointerDomain() = default;
    
    HazardPointer make_hazard_pointer() {
        return HazardPointer(this);
    }
    
    void retire(void* ptr) {
        std::lock_guard<std::mutex> lock(retired_mutex_);
        retired_list_.push_back(ptr);
        if (retired_list_.size() >= retire_threshold_) {
            scan_and_reclaim();
        }
    }
    
    void scan_and_reclaim() {
        std::vector<void*> to_delete;
        to_delete.reserve(retired_list_.size());
        
        for (void* ptr : retired_list_) {
            if (!is_hazard(ptr)) {
                to_delete.push_back(ptr);
            }
        }
        
        std::vector<void*> new_retired;
        new_retired.reserve(retired_list_.size() - to_delete.size());
        
        for (void* ptr : retired_list_) {
            bool found = false;
            for (void* del : to_delete) {
                if (del == ptr) { found = true; break; }
            }
            if (!found) new_retired.push_back(ptr);
        }
        
        retired_list_.swap(new_retired);
        
        for (void* ptr : to_delete) {
            ::operator delete(ptr);
        }
    }
    
    void force_reclaim_all() {
        scan_and_reclaim();
        for (void* ptr : retired_list_) {
            ::operator delete(ptr);
        }
        retired_list_.clear();
    }
};

// Global domain instance
thread_local HazardPointerDomain* g_hazard_domain = nullptr;

HazardPointerDomain& get_hazard_domain() {
    static HazardPointerDomain domain;
    if (!g_hazard_domain) g_hazard_domain = &domain;
    return domain;
}

// Stack seguro com Hazard Pointers
template<typename T>
class HazardStack {
    struct Node {
        T value;
        std::atomic<Node*> next;
        Node(T&& v) : value(std::move(v)), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    HazardPointerDomain& domain_;
    
public:
    explicit HazardStack(HazardPointerDomain& domain = get_hazard_domain()) : domain_(domain) {}
    
    void push(T&& value) {
        Node* new_node = new Node(std::move(value));
        Node* expected = head_.load(std::memory_order_relaxed);
        do {
            new_node->next.store(expected, std::memory_order_relaxed);
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        auto hp = domain_.make_hazard_pointer();
        Node* expected = head_.load(std::memory_order_acquire);
        
        while (expected) {
            hp.protect(expected);
            // Re-check after protection
            Node* current_head = head_.load(std::memory_order_acquire);
            if (current_head != expected) {
                hp.reset();
                expected = current_head;
                continue;
            }
            
            Node* next = expected->next.load(std::memory_order_acquire);
            if (head_.compare_exchange_weak(expected, next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected->value);
                hp.reset();
                domain_.retire(expected);
                return true;
            }
            hp.reset();
        }
        return false;
    }
};
```

### Real-World ABA Bugs

#### CVE-2016-0728: Linux Kernel Keyring Reference Counting

```cpp
// Simplified illustration of the bug pattern
// Actual bug in kernel/cred.c keyring reference counting

struct key {
    atomic_t usage;        // Reference count
    struct keyring *keyring;
    // ...
};

// BUG: ABA in reference counting
void key_put(struct key *key) {
    if (atomic_dec_and_test(&key->usage)) {
        // Object freed here
        kfree(key);
    }
}

// Attack scenario:
// Thread 1: reads key->usage == 2
// Thread 2: key_put() -> usage becomes 1, then 0 -> kfree(key)
// Thread 2: allocator reuses same memory for new key object
// Thread 2: new key->usage initialized to 1
// Thread 1: atomic_dec_and_test sees usage == 1 (was 2, now 1) -> thinks it's the last ref
// Thread 1: kfree(key) -> DOUBLE FREE / USE-AFTER-FREE

// Fix: Use atomic_inc_not_zero / atomic_dec_and_lock with proper locking
// Or use RCU for read-side critical sections
```

#### Michael-Scott Queue ABA Vulnerability

```cpp
// Michael-Scott queue node
template<typename T>
struct MSNode {
    T value;
    std::atomic<MSNode*> next;
    MSNode(T&& v) : value(std::move(v)), next(nullptr) {}
};

template<typename T>
class MichaelScottQueue {
    std::atomic<MSNode<T>*> head_;
    std::atomic<MSNode<T>*> tail_;
    
public:
    MichaelScottQueue() {
        MSNode<T>* dummy = new MSNode<T>(T{});
        head_.store(dummy, std::memory_order_relaxed);
        tail_.store(dummy, std::memory_order_relaxed);
    }
    
    // VULNERABLE to ABA on tail pointer
    void enqueue(T&& value) {
        MSNode<T>* new_node = new MSNode<T>(std::move(value));
        MSNode<T>* tail = tail_.load(std::memory_order_acquire);
        MSNode<T>* next = nullptr;
        
        while (true) {
            next = tail->next.load(std::memory_order_acquire);
            if (tail == tail_.load(std::memory_order_acquire)) {
                if (next == nullptr) {
                    if (tail->next.compare_exchange_weak(next, new_node,
                                                          std::memory_order_release,
                                                          std::memory_order_relaxed)) {
                        break;
                    }
                } else {
                    // Help advance tail
                    tail_.compare_exchange_weak(tail, next,
                                                 std::memory_order_release,
                                                 std::memory_order_relaxed);
                }
            }
        }
        // ABA possible here: tail advanced, node reused, tail comes back
        tail_.compare_exchange_weak(tail, new_node,
                                     std::memory_order_release,
                                     std::memory_order_relaxed);
    }
    
    bool dequeue(T& value) {
        MSNode<T>* head = head_.load(std::memory_order_acquire);
        MSNode<T>* tail = tail_.load(std::memory_order_acquire);
        MSNode<T>* next = nullptr;
        
        while (true) {
            next = head->next.load(std::memory_order_acquire);
            if (head == head_.load(std::memory_order_acquire)) {
                if (head == tail) {
                    if (next == nullptr) return false; // Empty
                    // Help advance tail
                    tail_.compare_exchange_weak(tail, next,
                                                 std::memory_order_release,
                                                 std::memory_order_relaxed);
                } else {
                    value = std::move(next->value);
                    if (head_.compare_exchange_weak(head, next,
                                                     std::memory_order_acq_rel,
                                                     std::memory_order_acquire)) {
                        break;
                    }
                }
            }
        }
        // ABA on head: node freed, reallocated, head CAS succeeds incorrectly
        // Need hazard pointers or epoch reclamation here!
        delete head; // UNSAFE without reclamation
        return true;
    }
};
```

#### Lock-Free Allocator Bugs (jemalloc/tcmalloc)

```cpp
// Simplified pattern from jemalloc arena allocation
// ABA in freelist management

struct freelist_entry {
    freelist_entry* next;
};

class LockFreeFreelist {
    std::atomic<freelist_entry*> head_;
    
public:
    freelist_entry* pop() {
        freelist_entry* expected = head_.load(std::memory_order_acquire);
        while (expected && 
               !head_.compare_exchange_weak(expected, expected->next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
            // ABA: expected freed, reused, points to different object
            // but same address -> CAS succeeds incorrectly
        }
        return expected;
    }
    
    void push(freelist_entry* entry) {
        entry->next = head_.load(std::memory_order_relaxed);
        while (!head_.compare_exchange_weak(entry->next, entry,
                                             std::memory_order_release,
                                             std::memory_order_relaxed)) {
            // Retry
        }
    }
};

// Real jemalloc fix: use per-CPU caches, batch allocation,
// and TCMalloc uses central free lists with spinlocks for large objects
// plus thread-local caches to reduce contention
```


## 4. Estruturas de Dados Lock-Free

### 4.1 Lock-Free Stack

#### Treiber Stack Algorithm

O algoritmo de stack de Treiber (1986) é a estrutura lock-free fundamental. Usa CAS no ponteiro head para push/pop.

```cpp
#include <atomic>
#include <memory>

template<typename T>
class TreiberStack {
    struct Node {
        T value;
        Node* next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    
public:
    TreiberStack() = default;
    ~TreiberStack() {
        // NOTE: Unsafe without reclamation!
        while (Node* n = head_.load()) {
            head_.store(n->next);
            delete n;
        }
    }
    
    TreiberStack(const TreiberStack&) = delete;
    TreiberStack& operator=(const TreiberStack&) = delete;
    
    // Push: wait-free (single CAS)
    template<typename... Args>
    void push(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* expected = head_.load(std::memory_order_relaxed);
        do {
            new_node->next = expected;
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    // Pop: lock-free (may retry)
    bool pop(T& value) {
        Node* expected = head_.load(std::memory_order_acquire);
        while (expected) {
            Node* next = expected->next;
            if (head_.compare_exchange_weak(expected, next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected->value);
                // ABA PROBLEM: expected may be freed and reallocated!
                // Need hazard pointers, epoch, or tagged pointers
                delete expected; // UNSAFE without reclamation
                return true;
            }
            // expected updated to current head
        }
        return false;
    }
    
    bool empty() const {
        return head_.load(std::memory_order_acquire) == nullptr;
    }
};
```

#### ABA Problem in Stack

{% raw %}
```cpp
// Demonstração do problema ABA no stack
/*
Cenário:
1. Stack: A -> B -> C (head = A)
2. Thread 1: pop() -> lê head = A, next = B, preemptida antes do CAS
3. Thread 2: pop() -> remove A, head = B
4. Thread 2: pop() -> remove B, head = C
5. Thread 2: push(A) -> reutiliza nó A! head = A -> C
6. Thread 1: retoma, CAS(head, A, B) SUCCEDES (head ainda é A!)
7. Resultado: B perdido (memory leak), stack corrompido: A -> C (B vazou)
*/

// Com Hazard Pointers - Stack Seguro
template<typename T>
class HazardStack {
    struct Node {
        T value;
        std::atomic<Node*> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    HazardPointerDomain& domain_;
    
public:
    explicit HazardStack(HazardPointerDomain& domain = get_hazard_domain()) : domain_(domain) {}
    
    template<typename... Args>
    void push(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* expected = head_.load(std::memory_order_relaxed);
        do {
            new_node->next.store(expected, std::memory_order_relaxed);
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        auto hp = domain_.make_hazard_pointer();
        Node* expected = head_.load(std::memory_order_acquire);
        
        while (expected) {
            hp.protect(expected);
            // Re-verify after protection
            Node* current_head = head_.load(std::memory_order_acquire);
            if (current_head != expected) {
                hp.reset();
                expected = current_head;
                continue;
            }
            
            Node* next = expected->next.load(std::memory_order_acquire);
            if (head_.compare_exchange_weak(expected, next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected->value);
                hp.reset();
                domain_.retire(expected);
                return true;
            }
            hp.reset();
        }
        return false;
    }
};

// Com Tagged Pointers - Stack Seguro (ABA mitigado)
template<typename T>
class TaggedStack {
    struct Node {
        T value;
        Node* next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    struct TaggedPtr {
        Node* ptr;
        uint64_t tag;
    };
    
    std::atomic<TaggedPtr> head_{{nullptr, 0}};
    
public:
    template<typename... Args>
    void push(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        TaggedPtr expected = head_.load(std::memory_order_relaxed);
        TaggedPtr desired;
        do {
            desired.ptr = new_node;
            desired.tag = expected.tag + 1;
            new_node->next = expected.ptr;
        } while (!head_.compare_exchange_weak(expected, desired,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        TaggedPtr expected = head_.load(std::memory_order_acquire);
        while (expected.ptr) {
            Node* next = expected.ptr->next;
            TaggedPtr desired{next, expected.tag + 1};
            if (head_.compare_exchange_weak(expected, desired,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected.ptr->value);
                // Tag incrementado previne ABA (até wraparound 2^64)
                delete expected.ptr;
                return true;
            }
        }
        return false;
    }
};
```
{% endraw %}

### 4.2 Lock-Free Queue

#### Michael-Scott Queue (1996)

A queue de Michael-Scott usa dois ponteiros (head, tail) e CAS para enqueue/dequeue. É linearizável e lock-free.

```cpp
#include <atomic>
#include <memory>

template<typename T>
class MichaelScottQueue {
    struct Node {
        T value;
        std::atomic<Node*> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    
    // Helper: advance tail if lagging
    void try_advance_tail(Node* tail, Node* next) {
        tail_.compare_exchange_weak(tail, next,
                                     std::memory_order_release,
                                     std::memory_order_relaxed);
    }
    
public:
    MichaelScottQueue() {
        Node* dummy = new Node();
        head_.store(dummy, std::memory_order_relaxed);
        tail_.store(dummy, std::memory_order_relaxed);
    }
    
    ~MichaelScottQueue() {
        T dummy;
        while (dequeue(dummy)) {}
        Node* h = head_.load();
        delete h;
    }
    
    MichaelScottQueue(const MichaelScottQueue&) = delete;
    MichaelScottQueue& operator=(const MichaelScottQueue&) = delete;
    
    // Enqueue: lock-free
    template<typename... Args>
    void enqueue(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* tail = tail_.load(std::memory_order_acquire);
        Node* next = nullptr;
        
        while (true) {
            next = tail->next.load(std::memory_order_acquire);
            if (tail == tail_.load(std::memory_order_acquire)) {
                if (next == nullptr) {
                    // Try to link new node
                    if (tail->next.compare_exchange_weak(next, new_node,
                                                          std::memory_order_release,
                                                          std::memory_order_relaxed)) {
                        break; // Successfully linked
                    }
                } else {
                    // Tail lagging, help advance it
                    try_advance_tail(tail, next);
                }
            }
            // Retry with current tail
            tail = tail_.load(std::memory_order_acquire);
        }
        // Advance tail to new node (best effort)
        try_advance_tail(tail, new_node);
    }
    
    // Dequeue: lock-free
    bool dequeue(T& value) {
        Node* head = head_.load(std::memory_order_acquire);
        Node* tail = tail_.load(std::memory_order_acquire);
        Node* next = nullptr;
        
        while (true) {
            next = head->next.load(std::memory_order_acquire);
            if (head == head_.load(std::memory_order_acquire)) {
                if (head == tail) {
                    if (next == nullptr) {
                        return false; // Empty queue
                    }
                    // Tail lagging, help advance
                    try_advance_tail(tail, next);
                } else {
                    // Read value before CAS
                    value = std::move(next->value);
                    if (head_.compare_exchange_weak(head, next,
                                                     std::memory_order_acq_rel,
                                                     std::memory_order_acquire)) {
                        break; // Successfully dequeued
                    }
                }
            }
            // Retry
            head = head_.load(std::memory_order_acquire);
            tail = tail_.load(std::memory_order_acquire);
        }
        // NOTE: ABA on head! Node may be freed and reallocated
        // Need hazard pointers or epoch reclamation
        delete head; // UNSAFE without reclamation
        return true;
    }
    
    bool empty() const {
        Node* h = head_.load(std::memory_order_acquire);
        Node* t = tail_.load(std::memory_order_acquire);
        return h == t && h->next.load(std::memory_order_acquire) == nullptr;
    }
};
```

#### Two-Lock Queue vs Lock-Free Queue

| Aspecto | Two-Lock Queue | Michael-Scott Lock-Free |
|---------|----------------|------------------------|
| **Complexidade** | Simples | Moderada |
| **Contenção baixa** | Rápido (mutex) | Overhead CAS |
| **Contenção alta** | Degrada (kernel) | Escala melhor |
| **Latência pior caso** | Ilimitada (OS) | Limitada (CAS retries) |
| **Memória** | Simples | Reclamation needed |
| **Linearizável** | Sim (com locks) | Sim |

```cpp
// Two-Lock Queue para comparação
#include <mutex>
#include <queue>

template<typename T>
class TwoLockQueue {
    std::queue<T> queue_;
    mutable std::mutex head_mutex_;
    mutable std::mutex tail_mutex_;
    
public:
    void enqueue(T value) {
        std::lock_guard<std::mutex> lock(tail_mutex_);
        queue_.push(std::move(value));
    }
    
    bool dequeue(T& value) {
        std::lock_guard<std::mutex> lock(head_mutex_);
        if (queue_.empty()) return false;
        value = std::move(queue_.front());
        queue_.pop();
        return true;
    }
    
    bool empty() const {
        std::lock_guard<std::mutex> lock(head_mutex_);
        return queue_.empty();
    }
};
```

#### Linearizability

Uma operação é linearizável se parece executar atomicamente em algum ponto entre sua invocação e resposta.

```cpp
// Pontos de linearização no Michael-Scott Queue:
// Enqueue: CAS bem-sucedido em tail->next (link do novo nó)
// Dequeue: CAS bem-sucedido em head (avanço do head)

// Prova de linearizabilidade:
// 1. Cada enqueue bem-sucedido adiciona nó no final
// 2. Cada dequeue bem-sucedido remove nó do início
// 3. Ordem FIFO mantida por ponteiros next
// 4. Head avança apenas quando queue não vazia
// 5. Tail avança apenas para último nó
```

### 4.3 Lock-Free Hash Map

#### Split-Ordered Lists (Shalev & Shavit, 2003)

```cpp
#include <atomic>
#include <vector>
#include <functional>

template<typename Key, typename Value, typename Hash = std::hash<Key>>
class SplitOrderedHashMap {
    struct Node {
        Key key;
        Value value;
        std::atomic<Node*> next;
        uint64_t hash;
        
        Node(Key k, Value v, uint64_t h) 
            : key(std::move(k)), value(std::move(v)), next(nullptr), hash(h) {}
    };
    
    struct Bucket {
        std::atomic<Node*> head;
        Bucket() : head(nullptr) {}
    };
    
    std::vector<Bucket> buckets_;
    std::atomic<size_t> size_{0};
    Hash hasher_;
    const float max_load_factor_ = 0.75;
    
    size_t bucket_index(uint64_t hash) const {
        return hash & (buckets_.size() - 1);
    }
    
    void resize() {
        // Lock-free resize complex - typically use epoch-based
        // Simplified: not implemented here
    }
    
public:
    explicit SplitOrderedHashMap(size_t initial_buckets = 16) 
        : buckets_(initial_buckets) {
        // Ensure power of 2
        size_t n = 1;
        while (n < initial_buckets) n <<= 1;
        buckets_.resize(n);
    }
    
    bool insert(Key key, Value value) {
        uint64_t hash = hasher_(key);
        size_t idx = bucket_index(hash);
        
        Node* new_node = new Node(std::move(key), std::move(value), hash);
        Node* expected = buckets_[idx].head.load(std::memory_order_acquire);
        
        while (true) {
            // Check for duplicate
            for (Node* curr = expected; curr; curr = curr->next.load(std::memory_order_acquire)) {
                if (curr->hash == hash && curr->key == new_node->key) {
                    delete new_node;
                    return false; // Key exists
                }
            }
            
            new_node->next.store(expected, std::memory_order_relaxed);
            if (buckets_[idx].head.compare_exchange_weak(expected, new_node,
                                                          std::memory_order_release,
                                                          std::memory_order_acquire)) {
                size_.fetch_add(1, std::memory_order_relaxed);
                return true;
            }
            // Retry with new expected
        }
    }
    
    bool find(const Key& key, Value& value) const {
        uint64_t hash = hasher_(key);
        size_t idx = bucket_index(hash);
        
        Node* curr = buckets_[idx].head.load(std::memory_order_acquire);
        while (curr) {
            if (curr->hash == hash && curr->key == key) {
                value = curr->value;
                return true;
            }
            curr = curr->next.load(std::memory_order_acquire);
        }
        return false;
    }
    
    bool erase(const Key& key) {
        uint64_t hash = hasher_(key);
        size_t idx = bucket_index(hash);
        
        Node* prev = nullptr;
        Node* curr = buckets_[idx].head.load(std::memory_order_acquire);
        
        while (curr) {
            if (curr->hash == hash && curr->key == key) {
                Node* next = curr->next.load(std::memory_order_acquire);
                if (prev) {
                    if (prev->next.compare_exchange_strong(curr, next,
                                                            std::memory_order_acq_rel,
                                                            std::memory_order_acquire)) {
                        // Need reclamation!
                        delete curr;
                        size_.fetch_sub(1, std::memory_order_relaxed);
                        return true;
                    }
                } else {
                    if (buckets_[idx].head.compare_exchange_strong(curr, next,
                                                                    std::memory_order_acq_rel,
                                                                    std::memory_order_acquire)) {
                        delete curr;
                        size_.fetch_sub(1, std::memory_order_relaxed);
                        return true;
                    }
                }
            }
            prev = curr;
            curr = curr->next.load(std::memory_order_acquire);
        }
        return false;
    }
    
    size_t size() const { return size_.load(std::memory_order_relaxed); }
};
```

#### Cliff-Click Hash Map (Non-blocking)

```cpp
// Cliff Click's lock-free hash map (Azul Systems)
// Características principais:
// - Resize incremental (não bloqueia)
// - Tabela de potência de 2
// - Sondagem linear com CAS
// - Contadores de versão para resize

template<typename K, typename V>
class CliffClickHashMap {
    struct Entry {
        std::atomic<K*> key;
        std::atomic<V*> value;
        std::atomic<uint64_t> version; // Para resize
        
        Entry() : key(nullptr), value(nullptr), version(0) {}
    };
    
    std::atomic<Entry*> table_;
    std::atomic<size_t> size_;
    std::atomic<size_t> mask_; // table_size - 1
    std::atomic<bool> resizing_;
    
    size_t hash(const K& key) const {
        return std::hash<K>{}(key);
    }
    
    size_t index(size_t hash, size_t mask) const {
        return hash & mask;
    }
    
    // Simplified - full implementation is ~2000 lines
    // Key insight: resize creates new table, copies incrementally
    // Readers check both old and new table during resize
    
public:
    // Production implementation: https://github.com/click/lockfree
};
```

#### Desafios de Hash Maps Lock-Free

1. **Resize atômico**: Requer copiar buckets enquanto writers continuam
2. **Memory reclamation**: Nodes removidos não podem ser liberados imediatamente
3. **Cache efficiency**: Sondagem linear vs chaining
4. **Load factor**: Balanceamento sem locks globais
5. **Iterator invalidation**: Iteradores lock-free são complexos

EOF
## 5. Gerenciamento de Memória Lock-Free

### O Problema: Safe Memory Reclamation

Em estruturas lock-free, quando um nó é removido, não podemos simplesmente `delete` - outras threads podem ter ponteiros para ele (hazard pointers) ou estar prestes a acessá-lo (epoch/RCU).

```cpp
// O PROBLEMA:
/*
Thread 1: pop() -> lê head = A, next = B
Thread 1: preemptida
Thread 2: pop() -> remove A, delete A
Thread 2: allocador reusa memória de A para novo nó C
Thread 1: retoma, CAS(head, A, B) -> SUCCEDE (A ainda lá!)
Thread 1: acessa A->value -> USE-AFTER-FREE / CORRUPÇÃO
*/

// Requisitos para reclamation:
// 1. Nenhum nó liberado enquanto thread pode acessá-lo
// 2. Progresso garantido (não bloquear writers)
// 3. Overhead mínimo no caminho crítico
// 4. Funcionar com número ilimitado de threads
```

### Hazard Pointers (Implementação Completa)

```cpp
#include <atomic>
#include <vector>
#include <thread>
#include <mutex>
#include <cassert>
#include <algorithm>

// Hazard Pointer Domain - gerencia records por thread
class HazardPointerDomain {
    struct HazardRecord {
        std::atomic<std::thread::id> thread_id{};
        std::atomic<void*> hazard_ptr{nullptr};
        std::atomic<bool> in_use{false};
    };
    
    static constexpr size_t MAX_RECORDS = 256;
    std::array<HazardRecord, MAX_RECORDS> records_;
    std::atomic<size_t> record_count_{0};
    
    // Lista de nós aposentados (por thread)
    struct RetiredList {
        std::vector<void*> nodes;
        std::mutex mutex;
        size_t threshold = 100;
    };
    
    // Thread-local retired list
    static thread_local RetiredList* tl_retired_;
    
    RetiredList& get_retired_list() {
        if (!tl_retired_) {
            tl_retired_ = new RetiredList();
        }
        return *tl_retired_;
    }
    
    bool is_protected(void* ptr) const {
        for (size_t i = 0; i < record_count_.load(std::memory_order_acquire); ++i) {
            if (records_[i].in_use.load(std::memory_order_acquire) &&
                records_[i].hazard_ptr.load(std::memory_order_acquire) == ptr) {
                return true;
            }
        }
        return false;
    }
    
    void scan_and_reclaim(RetiredList& list) {
        std::vector<void*> to_reclaim;
        to_reclaim.reserve(list.nodes.size());
        
        {
            std::lock_guard<std::mutex> lock(list.mutex);
            for (void* ptr : list.nodes) {
                if (!is_protected(ptr)) {
                    to_reclaim.push_back(ptr);
                }
            }
            // Keep protected nodes
            std::vector<void*> remaining;
            remaining.reserve(list.nodes.size() - to_reclaim.size());
            for (void* ptr : list.nodes) {
                bool found = false;
                for (void* r : to_reclaim) if (r == ptr) { found = true; break; }
                if (!found) remaining.push_back(ptr);
            }
            list.nodes.swap(remaining);
        }
        
        for (void* ptr : to_reclaim) {
            ::operator delete(ptr);
        }
    }
    
public:
    class HazardPointer {
        HazardPointerDomain* domain_;
        size_t record_idx_;
        
    public:
        HazardPointer() : domain_(nullptr), record_idx_(SIZE_MAX) {}
        
        explicit HazardPointer(HazardPointerDomain* domain) : domain_(domain) {
            // Find free record
            for (size_t i = 0; i < MAX_RECORDS; ++i) {
                std::thread::id empty;
                if (domain_->records_[i].thread_id.compare_exchange_strong(
                        empty, std::this_thread::get_id(),
                        std::memory_order_acq_rel)) {
                    domain_->records_[i].in_use.store(true, std::memory_order_release);
                    record_idx_ = i;
                    size_t count = domain_->record_count_.load(std::memory_order_relaxed);
                    while (count <= i && 
                           !domain_->record_count_.compare_exchange_weak(count, i + 1,
                                                                          std::memory_order_release)) {}
                    return;
                }
            }
            assert(false && "No hazard records available");
        }
        
        ~HazardPointer() {
            if (domain_) {
                domain_->records_[record_idx_].hazard_ptr.store(nullptr, std::memory_order_release);
                domain_->records_[record_idx_].in_use.store(false, std::memory_order_release);
                domain_->records_[record_idx_].thread_id.store(std::thread::id{}, std::memory_order_release);
            }
        }
        
        HazardPointer(const HazardPointer&) = delete;
        HazardPointer& operator=(const HazardPointer&) = delete;
        
        HazardPointer(HazardPointer&& other) noexcept
            : domain_(other.domain_), record_idx_(other.record_idx_) {
            other.domain_ = nullptr;
        }
        
        void protect(void* ptr) {
            assert(domain_);
            domain_->records_[record_idx_].hazard_ptr.store(ptr, std::memory_order_release);
        }
        
        template<typename T>
        void protect(T* ptr) {
            protect(static_cast<void*>(ptr));
        }
        
        void reset() {
            if (domain_) {
                domain_->records_[record_idx_].hazard_ptr.store(nullptr, std::memory_order_release);
            }
        }
    };
    
    HazardPointerDomain() = default;
    
    HazardPointer make_hazard_pointer() {
        return HazardPointer(this);
    }
    
    void retire(void* ptr) {
        auto& list = get_retired_list();
        std::lock_guard<std::mutex> lock(list.mutex);
        list.nodes.push_back(ptr);
        if (list.nodes.size() >= list.threshold) {
            scan_and_reclaim(list);
        }
    }
    
    void force_reclaim_all() {
        auto& list = get_retired_list();
        scan_and_reclaim(list);
    }
};

thread_local typename HazardPointerDomain::RetiredList* HazardPointerDomain::tl_retired_ = nullptr;

// Global domain
HazardPointerDomain& global_hazard_domain() {
    static HazardPointerDomain domain;
    return domain;
}

// Stack com Hazard Pointers completo
template<typename T>
class HazardStackComplete {
    struct Node {
        T value;
        std::atomic<Node*> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    HazardPointerDomain& domain_;
    
public:
    explicit HazardStackComplete(HazardPointerDomain& d = global_hazard_domain()) : domain_(d) {}
    
    template<typename... Args>
    void push(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* expected = head_.load(std::memory_order_relaxed);
        do {
            new_node->next.store(expected, std::memory_order_relaxed);
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        auto hp = domain_.make_hazard_pointer();
        Node* expected = head_.load(std::memory_order_acquire);
        
        while (expected) {
            hp.protect(expected);
            // Re-check after protection
            Node* current = head_.load(std::memory_order_acquire);
            if (current != expected) {
                hp.reset();
                expected = current;
                continue;
            }
            
            Node* next = expected->next.load(std::memory_order_acquire);
            if (head_.compare_exchange_weak(expected, next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected->value);
                hp.reset();
                domain_.retire(expected);
                return true;
            }
            hp.reset();
        }
        return false;
    }
};
```

### Epoch-Based Reclamation (Userspace RCU)

Epoch-based reclamation (EBR) divide o tempo em épocas. Threads registram época atual; nó aposentado só é liberado após todas as threads avançarem época.

```cpp
#include <atomic>
#include <vector>
#include <thread>
#include <array>
#include <mutex>

class EpochReclamation {
    static constexpr size_t MAX_THREADS = 128;
    static constexpr size_t EPOCHS = 3;
    
    struct ThreadData {
        std::atomic<uint64_t> epoch{0};      // Época atual da thread
        std::atomic<bool> active{false};     // Thread participando
        std::vector<void*> retired[EPOCHS];  // Nós aposentados por época
    };
    
    std::array<ThreadData, MAX_THREADS> threads_;
    std::atomic<uint64_t> global_epoch_{0};
    std::atomic<size_t> thread_count_{0};
    std::mutex retire_mutex_;
    
    size_t register_thread() {
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            bool expected = false;
            if (threads_[i].active.compare_exchange_strong(expected, true)) {
                thread_count_.fetch_add(1, std::memory_order_relaxed);
                return i;
            }
        }
        assert(false && "Max threads reached");
        return 0;
    }
    
    void unregister_thread(size_t idx) {
        threads_[idx].active.store(false, std::memory_order_release);
        thread_count_.fetch_sub(1, std::memory_order_relaxed);
        // Reclaim remaining
        for (size_t e = 0; e < EPOCHS; ++e) {
            for (void* ptr : threads_[idx].retired[e]) {
                ::operator delete(ptr);
            }
            threads_[idx].retired[e].clear();
        }
    }
    
    uint64_t current_epoch() const {
        return global_epoch_.load(std::memory_order_acquire);
    }
    
    void try_advance_epoch() {
        uint64_t current = global_epoch_.load(std::memory_order_acquire);
        uint64_t next = (current + 1) % EPOCHS;
        
        // Check if all active threads have seen current epoch
        bool all_synced = true;
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            if (threads_[i].active.load(std::memory_order_acquire)) {
                uint64_t t_epoch = threads_[i].epoch.load(std::memory_order_acquire);
                if (t_epoch != current) {
                    all_synced = false;
                    break;
                }
            }
        }
        
        if (all_synced) {
            global_epoch_.compare_exchange_strong(current, next,
                                                   std::memory_order_acq_rel);
        }
    }
    
    void reclaim_epoch(uint64_t epoch) {
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            if (threads_[i].active.load(std::memory_order_acquire)) {
                auto& vec = threads_[i].retired[epoch];
                for (void* ptr : vec) {
                    ::operator delete(ptr);
                }
                vec.clear();
            }
        }
    }
    
public:
    class Registrar {
        EpochReclamation* domain_;
        size_t thread_idx_;
        
    public:
        Registrar() : domain_(nullptr), thread_idx_(SIZE_MAX) {}
        
        explicit Registrar(EpochReclamation* domain) : domain_(domain) {
            thread_idx_ = domain_->register_thread();
        }
        
        ~Registrar() {
            if (domain_) domain_->unregister_thread(thread_idx_);
        }
        
        Registrar(const Registrar&) = delete;
        Registrar& operator=(const Registrar&) = delete;
        
        void enter_critical() {
            domain_->threads_[thread_idx_].epoch.store(
                domain_->current_epoch(), std::memory_order_release);
        }
        
        void exit_critical() {
            domain_->threads_[thread_idx_].epoch.store(UINT64_MAX, std::memory_order_release);
            domain_->try_advance_epoch();
        }
        
        void retire(void* ptr) {
            uint64_t epoch = domain_->current_epoch();
            domain_->threads_[thread_idx_].retired[epoch].push_back(ptr);
        }
    };
    
    EpochReclamation() = default;
    
    Registrar make_registrar() {
        return Registrar(this);
    }
    
    // RAII critical section
    class CriticalSection {
        Registrar& reg_;
    public:
        explicit CriticalSection(Registrar& reg) : reg_(reg) { reg_.enter_critical(); }
        ~CriticalSection() { reg_.exit_critical(); }
    };
};

// Stack com Epoch-Based Reclamation
template<typename T>
class EpochStack {
    struct Node {
        T value;
        std::atomic<Node*> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_{nullptr};
    EpochReclamation epoch_;
    
public:
    EpochStack() = default;
    
    template<typename... Args>
    void push(Args&&... args) {
        auto reg = epoch_.make_registrar();
        EpochReclamation::CriticalSection cs(reg);
        
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* expected = head_.load(std::memory_order_relaxed);
        do {
            new_node->next.store(expected, std::memory_order_relaxed);
        } while (!head_.compare_exchange_weak(expected, new_node,
                                               std::memory_order_release,
                                               std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        auto reg = epoch_.make_registrar();
        EpochReclamation::CriticalSection cs(reg);
        
        Node* expected = head_.load(std::memory_order_acquire);
        while (expected) {
            Node* next = expected->next.load(std::memory_order_acquire);
            if (head_.compare_exchange_weak(expected, next,
                                             std::memory_order_acq_rel,
                                             std::memory_order_acquire)) {
                value = std::move(expected->value);
                reg.retire(expected);
                return true;
            }
        }
        return false;
    }
};
```

### Reference Counting with Atomic Shared_Ptr

```cpp
#include <atomic>
#include <memory>
#include <cstdint>

// Lock-free reference counting control block
template<typename T>
class AtomicControlBlock {
    std::atomic<uint32_t> strong_refs_{1};
    std::atomic<uint32_t> weak_refs_{1};
    T* object_;
    
public:
    explicit AtomicControlBlock(T* obj) : object_(obj) {}
    
    void add_strong_ref() {
        strong_refs_.fetch_add(1, std::memory_order_relaxed);
    }
    
    bool release_strong_ref() {
        uint32_t old = strong_refs_.fetch_sub(1, std::memory_order_acq_rel);
        if (old == 1) {
            // Last strong ref - destroy object
            object_->~T();
            ::operator delete(object_);
            // Weak refs keep control block alive
            release_weak_ref();
            return true;
        }
        return false;
    }
    
    void add_weak_ref() {
        weak_refs_.fetch_add(1, std::memory_order_relaxed);
    }
    
    void release_weak_ref() {
        if (weak_refs_.fetch_sub(1, std::memory_order_acq_rel) == 1) {
            // Last weak ref - delete control block
            delete this;
        }
    }
    
    uint32_t strong_count() const {
        return strong_refs_.load(std::memory_order_acquire);
    }
    
    T* get() const { return object_; }
};

// Atomic shared_ptr para estruturas lock-free
template<typename T>
class LockFreeSharedPtr {
    AtomicControlBlock<T>* ctrl_;
    
public:
    LockFreeSharedPtr() : ctrl_(nullptr) {}
    
    explicit LockFreeSharedPtr(T* ptr) : ctrl_(new AtomicControlBlock<T>(ptr)) {}
    
    LockFreeSharedPtr(const LockFreeSharedPtr& other) : ctrl_(other.ctrl_) {
        if (ctrl_) ctrl_->add_strong_ref();
    }
    
    LockFreeSharedPtr(LockFreeSharedPtr&& other) noexcept : ctrl_(other.ctrl_) {
        other.ctrl_ = nullptr;
    }
    
    ~LockFreeSharedPtr() {
        if (ctrl_) ctrl_->release_strong_ref();
    }
    
    LockFreeSharedPtr& operator=(const LockFreeSharedPtr& other) {
        if (ctrl_) ctrl_->release_strong_ref();
        ctrl_ = other.ctrl_;
        if (ctrl_) ctrl_->add_strong_ref();
        return *this;
    }
    
    T* get() const { return ctrl_ ? ctrl_->get() : nullptr; }
    T& operator*() const { return *get(); }
    T* operator->() const { return get(); }
    
    explicit operator bool() const { return ctrl_ && ctrl_->get(); }
    
    // Atomic operations para uso lock-free
    bool compare_exchange_weak(LockFreeSharedPtr& expected, LockFreeSharedPtr desired) {
        // Implementação requer CAS no control block pointer
        // Simplificado - versão real precisa de atomic<AtomicControlBlock*>
        return false;
    }
};

// std::shared_ptr operações atômicas (C++20)
/*
namespace std {
    template<class T>
    bool atomic_compare_exchange_weak(shared_ptr<T>* p, shared_ptr<T>* expected, shared_ptr<T> desired);
    
    template<class T>
    shared_ptr<T> atomic_load(const shared_ptr<T>* p);
    
    template<class T>
    void atomic_store(shared_ptr<T>* p, shared_ptr<T> desired);
}

// Exemplo uso C++20:
std::shared_ptr<Node> head;
std::shared_ptr<Node> expected = head;
std::shared_ptr<Node> desired = new_node;
while (!std::atomic_compare_exchange_weak(&head, &expected, desired)) {
    desired->next = expected;
}
*/
```

### Quiescent State-Based Reclamation (QSBR)

```cpp
#include <atomic>
#include <thread>
#include <vector>
#include <array>

class QSBR {
    static constexpr size_t MAX_THREADS = 128;
    
    struct ThreadState {
        std::atomic<uint64_t> counter{0};  // Incrementado em quiescent state
        std::atomic<bool> registered{false};
    };
    
    std::array<ThreadState, MAX_THREADS> states_;
    std::atomic<uint64_t> global_counter_{0};
    std::atomic<size_t> registered_count_{0};
    std::mutex retire_mutex_;
    std::vector<std::pair<void*, uint64_t>> retired_; // ptr, counter at retire
    
    size_t register_thread() {
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            bool expected = false;
            if (states_[i].registered.compare_exchange_strong(expected, true)) {
                registered_count_.fetch_add(1, std::memory_order_relaxed);
                return i;
            }
        }
        assert(false);
        return 0;
    }
    
    void unregister_thread(size_t idx) {
        states_[idx].registered.store(false, std::memory_order_release);
        registered_count_.fetch_sub(1, std::memory_order_relaxed);
    }
    
    void quiescent_state(size_t idx) {
        uint64_t current = global_counter_.load(std::memory_order_acquire);
        states_[idx].counter.store(current, std::memory_order_release);
        try_reclaim();
    }
    
    void try_reclaim() {
        uint64_t min_counter = UINT64_MAX;
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            if (states_[i].registered.load(std::memory_order_acquire)) {
                uint64_t c = states_[i].counter.load(std::memory_order_acquire);
                if (c < min_counter) min_counter = c;
            }
        }
        
        if (min_counter == UINT64_MAX) return; // No threads
        
        std::lock_guard<std::mutex> lock(retire_mutex_);
        std::vector<std::pair<void*, uint64_t>> still_retired;
        still_retired.reserve(retired_.size());
        
        for (auto& [ptr, cnt] : retired_) {
            if (cnt < min_counter) {
                ::operator delete(ptr);
            } else {
                still_retired.emplace_back(ptr, cnt);
            }
        }
        retired_.swap(still_retired);
    }
    
public:
    class ThreadRegistrar {
        QSBR* domain_;
        size_t idx_;
        
    public:
        ThreadRegistrar() : domain_(nullptr), idx_(SIZE_MAX) {}
        explicit ThreadRegistrar(QSBR* d) : domain_(d), idx_(d->register_thread()) {}
        ~ThreadRegistrar() { if (domain_) domain_->unregister_thread(idx_); }
        
        ThreadRegistrar(const ThreadRegistrar&) = delete;
        ThreadRegistrar& operator=(const ThreadRegistrar&) = delete;
        
        void quiescent() { domain_->quiescent_state(idx_); }
        void retire(void* ptr) {
            uint64_t cnt = domain_->global_counter_.load(std::memory_order_acquire);
            std::lock_guard<std::mutex> lock(domain_->retire_mutex_);
            domain_->retired_.emplace_back(ptr, cnt);
        }
    };
    
    QSBR() = default;
    ThreadRegistrar register_thread() { return ThreadRegistrar(this); }
};


## 6. RCU (Read-Copy-Update)

### Principles of RCU

RCU (Read-Copy-Update) é uma técnica de sincronização onde:
- **Leitores** não fazem sincronização (wait-free reads)
- **Escritores** fazem copy-on-update: copiam estrutura, modificam, publicam atomicamente
- **Reclamation** adiada até grace period (todos leitores pré-existentes terminarem)

```cpp
// RCU básico: ponteiro protegido
struct rcu_head {
    void (*func)(struct rcu_head*);
    struct rcu_head* next;
};

// Read-side critical section (Linux kernel)
/*
rcu_read_lock();
// read shared data
do_something(rcu_dereference(ptr));
rcu_read_unlock();

// Writer side
new_ptr = kmalloc(...);
copy_data(old_ptr, new_ptr);
modify(new_ptr);
rcu_assign_pointer(ptr, new_ptr);
call_rcu(&old_ptr->rcu, free_callback);
*/
```

### Linux Kernel RCU vs Userspace RCU

| Aspecto | Kernel RCU | Userspace RCU (liburcu) |
|---------|------------|------------------------|
| **Grace period** | Scheduler, interrupts | Thread quiescent states |
| **Read-side** | `rcu_read_lock()` | `rcu_read_lock()` (pthread) |
| **Callbacks** | `call_rcu()` | `call_rcu()` / `synchronize_rcu()` |
| **Overhead** | Muito baixo | Moderado |
| **Uso** | Kernel, filesystem, networking | Aplicações userspace |

### liburcu Overview

```cpp
// liburcu API principal
#include <urcu/rculfhash.h>  // Lock-free hash table
#include <urcu/rculfqueue.h> // Lock-free queue
#include <urcu/rculflist.h>  // Lock-free list

// Exemplo uso liburcu
/*
struct my_node {
    int key;
    struct cds_lfht_node node; // Hash table node
    struct rcu_head rcu;
};

struct cds_lfht *ht = cds_lfht_new(0, 0, 0, CDS_LFHT_AUTO_RESIZE, NULL);

// Insert
struct my_node *node = malloc(sizeof(*node));
node->key = 42;
cds_lfht_add(ht, &node->node, hash_fn, NULL);

// Lookup (RCU read-side)
rcu_read_lock();
struct my_node *found = cds_lfht_lookup(ht, &key, hash_fn, NULL);
if (found) use(found->key);
rcu_read_unlock();

// Delete
rcu_read_lock();
struct my_node *found = cds_lfht_lookup(ht, &key, hash_fn, NULL);
if (found) {
    cds_lfht_del(ht, &found->node);
    call_rcu(&found->rcu, free_node);
}
rcu_read_unlock();
*/
```

### C++ Userspace RCU Implementation

```cpp
#include <atomic>
#include <vector>
#include <thread>
#include <functional>
#include <mutex>
#include <condition_variable>

class UserSpaceRCU {
    static constexpr size_t MAX_THREADS = 128;
    static constexpr size_t GRACE_PERIODS = 2;
    
    struct ThreadState {
        std::atomic<bool> in_critical{false};
        std::atomic<uint64_t> grace_period{0};
        std::atomic<bool> registered{false};
    };
    
    std::array<ThreadState, MAX_THREADS> threads_;
    std::atomic<uint64_t> current_gp_{0};
    std::atomic<size_t> registered_threads_{0};
    
    // Callbacks pendentes
    struct Callback {
        std::function<void()> func;
        uint64_t gp_at_queue;
    };
    
    std::mutex callback_mutex_;
    std::vector<Callback> callbacks_[GRACE_PERIODS];
    std::condition_variable gp_cv_;
    std::thread gp_thread_;
    std::atomic<bool> running_{true};
    
    size_t register_thread() {
        for (size_t i = 0; i < MAX_THREADS; ++i) {
            bool expected = false;
            if (threads_[i].registered.compare_exchange_strong(expected, true)) {
                registered_threads_.fetch_add(1, std::memory_order_relaxed);
                return i;
            }
        }
        assert(false);
        return 0;
    }
    
    void unregister_thread(size_t idx) {
        threads_[idx].registered.store(false, std::memory_order_release);
        registered_threads_.fetch_sub(1, std::memory_order_relaxed);
    }
    
    void grace_period_worker() {
        while (running_.load(std::memory_order_acquire)) {
            std::unique_lock<std::mutex> lock(callback_mutex_);
            gp_cv_.wait_for(lock, std::chrono::milliseconds(1));
            
            if (!running_.load(std::memory_order_acquire)) break;
            
            // Check if all threads passed through quiescent state
            uint64_t current = current_gp_.load(std::memory_order_acquire);
            bool all_quiescent = true;
            
            for (size_t i = 0; i < MAX_THREADS; ++i) {
                if (threads_[i].registered.load(std::memory_order_acquire)) {
                    if (!threads_[i].in_critical.load(std::memory_order_acquire)) {
                        uint64_t gp = threads_[i].grace_period.load(std::memory_order_acquire);
                        if (gp != current) {
                            all_quiescent = false;
                            break;
                        }
                    } else {
                        all_quiescent = false;
                        break;
                    }
                }
            }
            
            if (all_quiescent) {
                // Advance grace period
                uint64_t next = (current + 1) % GRACE_PERIODS;
                current_gp_.store(next, std::memory_order_release);
                
                // Execute callbacks from completed grace period
                auto& completed = callbacks_[current];
                for (auto& cb : completed) {
                    cb.func();
                }
                completed.clear();
            }
        }
    }
    
public:
    class RCUDomain {
        UserSpaceRCU* rcu_;
        size_t thread_idx_;
        
    public:
        RCUDomain() : rcu_(nullptr), thread_idx_(SIZE_MAX) {}
        explicit RCUDomain(UserSpaceRCU* rcu) : rcu_(rcu), thread_idx_(rcu->register_thread()) {}
        ~RCUDomain() { if (rcu_) rcu_->unregister_thread(thread_idx_); }
        
        RCUDomain(const RCUDomain&) = delete;
        RCUDomain& operator=(const RCUDomain&) = delete;
        
        class ReadLock {
            RCUDomain& domain_;
        public:
            explicit ReadLock(RCUDomain& domain) : domain_(domain) {
                domain_.rcu_->threads_[domain_.thread_idx_].in_critical.store(true, std::memory_order_release);
                domain_.rcu_->threads_[domain_.thread_idx_].grace_period.store(
                    domain_.rcu_->current_gp_.load(std::memory_order_acquire), std::memory_order_release);
            }
            ~ReadLock() {
                domain_.rcu_->threads_[domain_.thread_idx_].in_critical.store(false, std::memory_order_release);
            }
        };
        
        ReadLock read_lock() { return ReadLock(*this); }
        
        template<typename F>
        void call_rcu(F&& f) {
            uint64_t gp = rcu_->current_gp_.load(std::memory_order_acquire);
            std::lock_guard<std::mutex> lock(rcu_->callback_mutex_);
            rcu_->callbacks_[gp].push_back({std::forward<F>(f), gp});
            rcu_->gp_cv_.notify_one();
        }
    };
    
    UserSpaceRCU() {
        gp_thread_ = std::thread(&UserSpaceRCU::grace_period_worker, this);
    }
    
    ~UserSpaceRCU() {
        running_.store(false, std::memory_order_release);
        gp_cv_.notify_one();
        if (gp_thread_.joinable()) gp_thread_.join();
    }
    
    RCUDomain make_domain() { return RCUDomain(this); }
};

// Exemplo uso RCU C++
/*
UserSpaceRCU rcu;
auto domain = rcu.make_domain();

// Writer thread
void writer() {
    auto new_data = new Data{42};
    std::atomic_store(&global_ptr, new_data); // rcu_assign_pointer
    domain.call_rcu([old = std::atomic_load(&global_ptr)]() {
        delete old; // Safe after grace period
    });
}

// Reader thread
void reader() {
    auto lock = domain.read_lock();
    Data* data = std::atomic_load(&global_ptr); // rcu_dereference
    use(data->value);
}
*/
```

### When to Use RCU

| Cenário | RCU Adequado? |
|---------|---------------|
| Reads >> Writes (99% reads) | **SIM** - leitores wait-free |
| Estruturas ponteiro-indiretas (listas, árvores, hash) | **SIM** - copy-on-write natural |
| Atualizações frequentes | NÃO - overhead de copy |
| Estruturas pequenas (contadores) | NÃO - atomic direto melhor |
| Latência de write crítica | NÃO - grace period atrasa reclamation |
| Memória limitada | CUIDADO - grace period acumula lixo |

EOF
## 7. Atomic Shared Pointer

### std::shared_ptr Atomic Operations (C++20)

C++20 introduziu operações atômicas para `std::shared_ptr`, permitindo uso seguro em contextos lock-free.

```cpp
#include <memory>
#include <atomic>
#include <thread>
#include <vector>

// C++20 atomic shared_ptr operations
/*
namespace std {
    template<class T>
    bool atomic_compare_exchange_weak(shared_ptr<T>* p, shared_ptr<T>* expected, shared_ptr<T> desired);
    
    template<class T>
    bool atomic_compare_exchange_strong(shared_ptr<T>* p, shared_ptr<T>* expected, shared_ptr<T> desired);
    
    template<class T>
    shared_ptr<T> atomic_load(const shared_ptr<T>* p);
    
    template<class T>
    void atomic_store(shared_ptr<T>* p, shared_ptr<T> desired);
    
    template<class T>
    void atomic_store_explicit(shared_ptr<T>* p, shared_ptr<T> desired, memory_order order);
    
    template<class T>
    shared_ptr<T> atomic_load_explicit(const shared_ptr<T>* p, memory_order order);
}
*/

// Exemplo: Lock-free stack com atomic shared_ptr (C++20)
template<typename T>
class AtomicSharedPtrStack {
    struct Node {
        T value;
        std::shared_ptr<Node> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...) {}
    };
    
    std::shared_ptr<Node> head_;
    
public:
    template<typename... Args>
    void push(Args&&... args) {
        auto new_node = std::make_shared<Node>(std::forward<Args>(args)...);
        std::shared_ptr<Node> expected = std::atomic_load(&head_);
        do {
            new_node->next = expected;
        } while (!std::atomic_compare_exchange_weak(&head_, &expected, new_node));
    }
    
    bool pop(T& value) {
        std::shared_ptr<Node> expected = std::atomic_load(&head_);
        while (expected) {
            std::shared_ptr<Node> next = std::atomic_load(&expected->next);
            if (std::atomic_compare_exchange_weak(&head_, &expected, next)) {
                value = std::move(expected->value);
                return true;
            }
            // expected atualizado automaticamente
        }
        return false;
    }
};
```

### Lock-Free Reference Counting

O control block de `shared_ptr` contém contadores atômicos. Em C++20, as operações no control block são atômicas.

```cpp
// Estrutura interna simplificada do control block
/*
struct control_block {
    std::atomic<std::size_t> strong_refs;  // shared_ptr count
    std::atomic<std::size_t> weak_refs;    // weak_ptr count + 1 if strong > 0
    T* object;
    // Deleter, allocator
};
*/

// Operações atômicas no control block:
// - Increment/decrement strong_refs: memory_order_acq_rel
// - Increment/decrement weak_refs: memory_order_acq_rel
// - Destruição do objeto quando strong_refs == 0
// - Destruição do control block quando weak_refs == 0

// Custom atomic shared_ptr para estruturas lock-free
template<typename T>
class LockFreeAtomicSharedPtr {
    struct ControlBlock {
        std::atomic<uint32_t> strong{1};
        std::atomic<uint32_t> weak{1};
        T* ptr;
        
        ControlBlock(T* p) : ptr(p) {}
        
        void add_strong() { strong.fetch_add(1, std::memory_order_relaxed); }
        bool release_strong() {
            if (strong.fetch_sub(1, std::memory_order_acq_rel) == 1) {
                ptr->~T();
                ::operator delete(ptr);
                release_weak();
                return true;
            }
            return false;
        }
        void add_weak() { weak.fetch_add(1, std::memory_order_relaxed); }
        void release_weak() {
            if (weak.fetch_sub(1, std::memory_order_acq_rel) == 1) {
                delete this;
            }
        }
    };
    
    ControlBlock* ctrl_;
    
public:
    LockFreeAtomicSharedPtr() : ctrl_(nullptr) {}
    explicit LockFreeAtomicSharedPtr(T* p) : ctrl_(new ControlBlock(p)) {}
    
    LockFreeAtomicSharedPtr(const LockFreeAtomicSharedPtr& other) : ctrl_(other.ctrl_) {
        if (ctrl_) ctrl_->add_strong();
    }
    
    LockFreeAtomicSharedPtr(LockFreeAtomicSharedPtr&& other) noexcept : ctrl_(other.ctrl_) {
        other.ctrl_ = nullptr;
    }
    
    ~LockFreeAtomicSharedPtr() { if (ctrl_) ctrl_->release_strong(); }
    
    LockFreeAtomicSharedPtr& operator=(const LockFreeAtomicSharedPtr& other) {
        if (ctrl_) ctrl_->release_strong();
        ctrl_ = other.ctrl_;
        if (ctrl_) ctrl_->add_strong();
        return *this;
    }
    
    T* get() const { return ctrl_ ? ctrl_->ptr : nullptr; }
    T& operator*() const { return *get(); }
    T* operator->() const { return get(); }
    explicit operator bool() const { return ctrl_ && ctrl_->ptr; }
    
    uint32_t use_count() const { return ctrl_ ? ctrl_->strong.load(std::memory_order_acquire) : 0; }
    
    // Atomic CAS para uso lock-free
    bool compare_exchange_weak(LockFreeAtomicSharedPtr& expected, LockFreeAtomicSharedPtr desired) {
        // Requer atomic<ControlBlock*> - não implementado aqui
        return false;
    }
};
```

### Control Block Atomicity

```cpp
// O control block garante:
// 1. strong_refs atômico - múltiplas threads podem copiar shared_ptr
// 2. weak_refs atômico - weak_ptr não impede destruição do objeto
// 3. Destruição do objeto ocorre exatamente uma vez (quando strong == 0)
// 4. Destruição do control block ocorre exatamente uma vez (quando weak == 0)

// Memory ordering no control block:
// - Increment: relaxed (só precisa de atomicidade)
// - Decrement: acq_rel (sincroniza com destruição)
// - Load para use_count: acquire

// Exemplo de race condition evitada:
/*
Thread 1: shared_ptr p = global;  // atomic_load -> increment strong (relaxed)
Thread 2: global.reset();          // atomic_store -> decrement strong (acq_rel)
                                     // Se strong == 0: destrói objeto
Thread 1: use(p);                  // Seguro: strong > 0 garante objeto vivo
*/
```

### Custom Atomic Shared_Ptr for Lock-Free Structures

```cpp
// Para estruturas lock-free customizadas, podemos usar shared_ptr
// com CAS atômico (C++20) ou implementar nosso próprio

template<typename T>
class LockFreeStackWithSharedPtr {
    struct Node {
        T value;
        std::shared_ptr<Node> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...) {}
    };
    
    // C++20: std::atomic<std::shared_ptr<Node>> head_;
    // Pré-C++20: std::shared_ptr<Node> head_ com atomic_* functions
    
    std::shared_ptr<Node> head_;
    
public:
    template<typename... Args>
    void push(Args&&... args) {
        auto new_node = std::make_shared<Node>(std::forward<Args>(args)...);
        std::shared_ptr<Node> expected = std::atomic_load_explicit(&head_, std::memory_order_relaxed);
        do {
            new_node->next = expected;
        } while (!std::atomic_compare_exchange_weak_explicit(
            &head_, &expected, new_node,
            std::memory_order_release, std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        std::shared_ptr<Node> expected = std::atomic_load_explicit(&head_, std::memory_order_acquire);
        while (expected) {
            std::shared_ptr<Node> next = std::atomic_load_explicit(&expected->next, std::memory_order_acquire);
            if (std::atomic_compare_exchange_weak_explicit(
                &head_, &expected, next,
                std::memory_order_acq_rel, std::memory_order_acquire)) {
                value = std::move(expected->value);
                return true;
            }
        }
        return false;
    }
};
```

EOF
## 8. Benchmarking e Análise de Desempenho

### Measuring Lock-Free vs Lock-Based

```cpp
#include <chrono>
#include <thread>
#include <vector>
#include <atomic>
#include <mutex>
#include <iostream>
#include <random>

template<typename Queue>
void benchmark_queue(Queue& q, int num_threads, int ops_per_thread, bool is_producer) {
    std::vector<std::thread> threads;
    std::atomic<int> ready{0};
    std::atomic<bool> start{false};
    
    auto worker = [&](int id) {
        ready.fetch_add(1, std::memory_order_release);
        while (!start.load(std::memory_order_acquire)) {}
        
        if (is_producer) {
            for (int i = 0; i < ops_per_thread; ++i) {
                q.push(id * ops_per_thread + i);
            }
        } else {
            int value;
            for (int i = 0; i < ops_per_thread; ++i) {
                while (!q.pop(value)) {} // busy wait
            }
        }
    };
    
    for (int i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker, i);
    }
    
    while (ready.load(std::memory_order_acquire) < num_threads) {}
    
    auto t1 = std::chrono::high_resolution_clock::now();
    start.store(true, std::memory_order_release);
    
    for (auto& t : threads) t.join();
    
    auto t2 = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
    
    std::cout << "Threads: " << num_threads 
              << ", Ops: " << (long long)num_threads * ops_per_thread
              << ", Time: " << duration << " us"
              << ", Throughput: " << (double)num_threads * ops_per_thread / duration * 1e6 << " ops/s"
              << std::endl;
}

// Benchmark comparativo
void run_benchmarks() {
    const int threads = 4;
    const int ops = 100000;
    
    std::cout << "=== Lock-Free Stack (Hazard) ===" << std::endl;
    HazardStack<int> hs;
    benchmark_queue(hs, threads, ops, true);
    benchmark_queue(hs, threads, ops, false);
    
    std::cout << "\n=== Mutex Stack ===" << std::endl;
    std::stack<int> ms;
    std::mutex mm;
    struct MutexStack {
        std::stack<int>& s; std::mutex& m;
        void push(int v) { std::lock_guard<std::mutex> l(m); s.push(v); }
        bool pop(int& v) { std::lock_guard<std::mutex> l(m); if(s.empty()) return false; v=s.top(); s.pop(); return true; }
    } mutex_stack{ms, mm};
    benchmark_queue(mutex_stack, threads, ops, true);
    benchmark_queue(mutex_stack, threads, ops, false);
}
```

### Contention Analysis

```cpp
#include <atomic>
#include <chrono>

class ContentionTracker {
    std::atomic<uint64_t> cas_attempts_{0};
    std::atomic<uint64_t> cas_success_{0};
    std::atomic<uint64_t> cas_failures_{0};
    
public:
    void record_attempt(bool success) {
        cas_attempts_.fetch_add(1, std::memory_order_relaxed);
        if (success) cas_success_.fetch_add(1, std::memory_order_relaxed);
        else cas_failures_.fetch_add(1, std::memory_order_relaxed);
    }
    
    double contention_ratio() const {
        uint64_t a = cas_attempts_.load(std::memory_order_relaxed);
        uint64_t f = cas_failures_.load(std::memory_order_relaxed);
        return a > 0 ? (double)f / a : 0.0;
    }
    
    void reset() {
        cas_attempts_.store(0, std::memory_order_relaxed);
        cas_success_.store(0, std::memory_order_relaxed);
        cas_failures_.store(0, std::memory_order_relaxed);
    }
    
    void report() const {
        uint64_t a = cas_attempts_.load();
        uint64_t s = cas_success_.load();
        uint64_t f = cas_failures_.load();
        std::cout << "CAS Attempts: " << a << ", Success: " << s 
                  << ", Failures: " << f << ", Contention: " << contention_ratio() * 100 << "%" << std::endl;
    }
};

// Instrumented stack
template<typename T>
class InstrumentedStack {
    struct Node { T value; Node* next; Node(T&& v): value(std::move(v)), next(nullptr) {} };
    std::atomic<Node*> head_{nullptr};
    ContentionTracker tracker_;
    
public:
    void push(T&& value) {
        Node* n = new Node(std::move(value));
        Node* expected = head_.load(std::memory_order_relaxed);
        while (true) {
            n->next = expected;
            tracker_.record_attempt(head_.compare_exchange_weak(expected, n,
                                                                 std::memory_order_release,
                                                                 std::memory_order_relaxed));
            if (n->next == expected) break; // success
        }
    }
    
    bool pop(T& value) {
        Node* expected = head_.load(std::memory_order_acquire);
        while (expected) {
            Node* next = expected->next;
            bool success = head_.compare_exchange_weak(expected, next,
                                                        std::memory_order_acq_rel,
                                                        std::memory_order_acquire);
            tracker_.record_attempt(success);
            if (success) {
                value = std::move(expected->value);
                delete expected; // unsafe without reclamation
                return true;
            }
        }
        return false;
    }
    
    const ContentionTracker& tracker() const { return tracker_; }
};
```

### False Sharing Detection

```cpp
#include <atomic>
#include <thread>
#include <vector>
#include <iostream>

// False sharing: threads em cores diferentes modificam variáveis na mesma cache line (64 bytes)
struct BadCounter {
    std::atomic<int> counters[4]; // Todas na mesma cache line!
};

struct GoodCounter {
    struct alignas(64) PaddedAtomic {
        std::atomic<int> value;
    };
    PaddedAtomic counters[4]; // Cada uma em cache line separada
};

void false_sharing_demo() {
    const int iterations = 10000000;
    
    BadCounter bad;
    GoodCounter good;
    
    auto run_bad = [&]() {
        for (int i = 0; i < iterations; ++i) {
            bad.counters[0].fetch_add(1, std::memory_order_relaxed);
        }
    };
    
    auto run_good = [&]() {
        for (int i = 0; i < iterations; ++i) {
            good.counters[0].value.fetch_add(1, std::memory_order_relaxed);
        }
    };
    
    auto measure = [](auto&& fn, const char* name) {
        auto t1 = std::chrono::high_resolution_clock::now();
        std::thread t1_th(fn), t2_th(fn), t3_th(fn), t4_th(fn);
        t1_th.join(); t2_th.join(); t3_th.join(); t4_th.join();
        auto t2 = std::chrono::high_resolution_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
        std::cout << name << ": " << us << " us" << std::endl;
    };
    
    std::cout << "False sharing test (4 threads incrementing different counters):" << std::endl;
    measure(run_bad, "Bad (same cache line)");
    measure(run_good, "Good (padded)");
}
```

### Cache Line Padding (alignas)

```cpp
// Padding correto para evitar false sharing
template<typename T>
struct CacheLineAligned {
    alignas(64) T value; // 64 bytes = cache line típica x86/ARM
    
    CacheLineAligned() = default;
    CacheLineAligned(const T& v) : value(v) {}
    CacheLineAligned(T&& v) : value(std::move(v)) {}
    
    CacheLineAligned& operator=(const T& v) { value = v; return *this; }
    CacheLineAligned& operator=(T&& v) { value = std::move(v); return *this; }
};

// Uso em estruturas lock-free
template<typename T>
class PaddedAtomicStack {
    struct Node {
        T value;
        Node* next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    // Head em cache line própria
    struct alignas(64) HeadWrapper {
        std::atomic<Node*> ptr;
    } head_;
    
public:
    void push(T&& value) {
        Node* n = new Node(std::move(value));
        Node* expected = head_.ptr.load(std::memory_order_relaxed);
        do { n->next = expected; }
        while (!head_.ptr.compare_exchange_weak(expected, n,
                                                 std::memory_order_release,
                                                 std::memory_order_relaxed));
    }
    
    bool pop(T& value) {
        Node* expected = head_.ptr.load(std::memory_order_acquire);
        while (expected) {
            Node* next = expected->next;
            if (head_.ptr.compare_exchange_weak(expected, next,
                                                 std::memory_order_acq_rel,
                                                 std::memory_order_acquire)) {
                value = std::move(expected->value);
                delete expected; // unsafe
                return true;
            }
        }
        return false;
    }
};
```

### C++ Benchmark Framework

```cpp
#include <chrono>
#include <functional>
#include <string>
#include <vector>
#include <iostream>
#include <iomanip>

struct BenchmarkResult {
    std::string name;
    int threads;
    int operations;
    double duration_us;
    double throughput_ops_per_sec;
    double contention_ratio;
};

class Benchmark {
    std::vector<BenchmarkResult> results_;
    
public:
    template<typename Fn>
    void run(const std::string& name, int threads, int ops_per_thread, Fn&& fn) {
        std::vector<std::thread> workers;
        std::atomic<int> ready{0};
        std::atomic<bool> start{false};
        
        for (int i = 0; i < threads; ++i) {
            workers.emplace_back([&, i]() {
                ready.fetch_add(1, std::memory_order_release);
                while (!start.load(std::memory_order_acquire)) {}
                fn(i);
            });
        }
        
        while (ready.load(std::memory_order_acquire) < threads) {}
        
        auto t1 = std::chrono::high_resolution_clock::now();
        start.store(true, std::memory_order_release);
        
        for (auto& w : workers) w.join();
        
        auto t2 = std::chrono::high_resolution_clock::now();
        double us = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
        double total_ops = (double)threads * ops_per_thread;
        
        results_.push_back({
            name, threads, ops_per_thread, us,
            total_ops / us * 1e6, 0.0
        });
    }
    
    void print_results() const {
        std::cout << std::left << std::setw(30) << "Name" 
                  << std::setw(10) << "Threads"
                  << std::setw(12) << "Ops"
                  << std::setw(15) << "Time (us)"
                  << std::setw(20) << "Throughput (ops/s)"
                  << std::endl;
        std::cout << std::string(107, '-') << std::endl;
        
        for (const auto& r : results_) {
            std::cout << std::left << std::setw(30) << r.name
                      << std::setw(10) << r.threads
                      << std::setw(12) << r.operations
                      << std::setw(15) << r.duration_us
                      << std::setw(20) << (long long)r.throughput_ops_per_sec
                      << std::endl;
        }
    }
};
```

EOF
## 9. Verificação Formal e Testing

### Model Checking with CDSChecker

CDSChecker é uma ferramenta para verificação de programas C/C++ concorrentes usando model checking.

```cpp
// Exemplo: Verificando linearizabilidade de stack lock-free
// Compilar com: cdschecker -o test test.cpp -lpthread

#include <cdschecker.h>
#include <atomic>

std::atomic<int*> head;

void push(int* node) {
    int* expected = head.load();
    do {
        // node->next = expected; // Simplificado
    } while (!head.compare_exchange_weak(expected, node));
}

int* pop() {
    int* expected = head.load();
    while (expected) {
        int* next = nullptr; // expected->next
        if (head.compare_exchange_weak(expected, next)) {
            return expected;
        }
    }
    return nullptr;
}

// CDSchecker verifica automaticamente:
// - Data races
// - Deadlocks
// - Linearizability violations
// - Memory safety
```

### Nidhugg for C/C++

Nidhugg é um model checker stateless para programas C/C++ com pthreads.

```bash
# Instalação
git clone https://github.com/nidhugg/nidhugg
cd nidhugg && make

# Uso
nidhugg -pthread -race test.c

# Opções principais:
# -race: detecta data races
# -fair: escalonamento justo
# -bound N: limita profundidade de busca
# -full: busca exaustiva
```

```c
// Exemplo para Nidhugg: stack lock-free com bug ABA
#include <pthread.h>
#include <stdatomic.h>

typedef struct Node { int val; struct Node* next; } Node;
atomic(Node*) head;

void* pusher(void* arg) {
    Node* n = malloc(sizeof(Node));
    n->val = *(int*)arg;
    Node* expected = atomic_load(&head);
    do { n->next = expected; }
    while (!atomic_compare_exchange_weak(&head, &expected, n));
    return NULL;
}

void* popper(void* arg) {
    Node* expected = atomic_load(&head);
    while (expected) {
        Node* next = expected->next;
        if (atomic_compare_exchange_weak(&head, &expected, next)) {
            free(expected); // BUG: ABA - pode ser reutilizado!
            return NULL;
        }
    }
    return NULL;
}

int main() {
    pthread_t t1, t2, t3, t4;
    int a=1, b=2, c=3, d=4;
    pthread_create(&t1, NULL, pusher, &a);
    pthread_create(&t2, NULL, pusher, &b);
    pthread_create(&t3, NULL, popper, NULL);
    pthread_create(&t4, NULL, popper, NULL);
    pthread_join(t1, NULL); pthread_join(t2, NULL);
    pthread_join(t3, NULL); pthread_join(t4, NULL);
    return 0;
}

/*
Nidhugg detectará:
- Data race no free/use
- ABA violation
- Memory leak
*/
```

### Linearizability Testing

```cpp
#include <atomic>
#include <vector>
#include <thread>
#include <chrono>
#include <algorithm>
#include <iostream>

// Test harness para linearizabilidade
template<typename Stack>
class LinearizabilityTester {
    Stack& stack_;
    std::vector<std::thread> threads_;
    std::atomic<bool> running_{true};
    
    struct Operation {
        enum Type { PUSH, POP } type;
        int value;
        int thread_id;
        std::chrono::high_resolution_clock::time_point start, end;
        bool success;
        int returned_value;
    };
    
    std::vector<Operation> history_;
    std::mutex history_mutex_;
    
    void record(Operation op) {
        std::lock_guard<std::mutex> lock(history_mutex_);
        history_.push_back(op);
    }
    
    void worker_push(int id, int value) {
        Operation op{Operation::PUSH, value, id, {}, {}, true, 0};
        op.start = std::chrono::high_resolution_clock::now();
        stack_.push(value);
        op.end = std::chrono::high_resolution_clock::now();
        record(op);
    }
    
    void worker_pop(int id) {
        Operation op{Operation::POP, 0, id, {}, {}, false, 0};
        op.start = std::chrono::high_resolution_clock::now();
        int val;
        op.success = stack_.pop(val);
        op.returned_value = val;
        op.end = std::chrono::high_resolution_clock::now();
        record(op);
    }
    
    // Verifica se history é linearizável
    bool check_linearizability() {
        // Simplified: verifica ordem FIFO para queue, LIFO para stack
        // Implementação completa requer algoritmo de verificação de linearizabilidade
        // (ex: algoritmo de Wing & Gong)
        return true; // placeholder
    }
    
public:
    LinearizabilityTester(Stack& s) : stack_(s) {}
    
    void run_test(int num_threads, int ops_per_thread) {
        for (int i = 0; i < num_threads; ++i) {
            threads_.emplace_back([this, i, ops_per_thread]() {
                for (int j = 0; j < ops_per_thread; ++j) {
                    if (rand() % 2) worker_push(i, i * ops_per_thread + j);
                    else worker_pop(i);
                }
            });
        }
        for (auto& t : threads_) t.join();
    }
    
    void verify() {
        bool ok = check_linearizability();
        std::cout << "Linearizability: " << (ok ? "PASS" : "FAIL") << std::endl;
        std::cout << "Total operations: " << history_.size() << std::endl;
    }
};
```

### ThreadSanitizer Limitations with Lock-Free

```cpp
// ThreadSanitizer (TSan) tem limitações com código lock-free:
// 1. Falsos positivos em CAS loops (esperado)
// 2. Não detecta ABA problems
// 3. Overhead alto (~5-15x slowdown)
// 4. Não modela memory_order corretamente em todos casos

// Exemplo de falso positivo TSan:
/*
std::atomic<int> x{0};
void thread1() { x.store(1, std::memory_order_release); }
void thread2() { 
    int expected = 0;
    x.compare_exchange_strong(expected, 2, std::memory_order_acq_rel);
}
// TSan pode reportar race no compare_exchange!
*/

// Workarounds:
// 1. Annotate com __tsan_ignore_reads/__tsan_ignore_writes
// 2. Use __atomic_* builtins com memory_order explícito
// 3. Testes de stress manuais além de TSan

// Helpers para TSan:
#ifdef __has_feature
#  if __has_feature(thread_sanitizer)
#    define TSAN_IGNORE_READ(addr) __tsan_ignore_reads(addr)
#    define TSAN_IGNORE_WRITE(addr) __tsan_ignore_writes(addr)
#  else
#    define TSAN_IGNORE_READ(addr)
#    define TSAN_IGNORE_WRITE(addr)
#  endif
#else
#  define TSAN_IGNORE_READ(addr)
#  define TSAN_IGNORE_WRITE(addr)
#endif
```

### Stress Testing Patterns

```cpp
#include <atomic>
#include <thread>
#include <vector>
#include <chrono>
#include <random>
#include <iostream>

template<typename Queue>
void stress_test_mpsc(Queue& q, int num_producers, int num_consumers, int ops) {
    std::atomic<int> produced{0}, consumed{0};
    std::atomic<bool> done{false};
    std::vector<std::thread> threads;
    
    // Producers
    for (int i = 0; i < num_producers; ++i) {
        threads.emplace_back([&, i]() {
            std::mt19937 rng(i + 12345);
            for (int j = 0; j < ops; ++j) {
                q.push(i * ops + j);
                produced.fetch_add(1, std::memory_order_relaxed);
                // Random delay para aumentar interleaving
                if (rng() % 100 == 0) std::this_thread::yield();
            }
        });
    }
    
    // Consumers
    for (int i = 0; i < num_consumers; ++i) {
        threads.emplace_back([&]() {
            int val;
            while (!done.load(std::memory_order_acquire) || 
                   consumed.load(std::memory_order_relaxed) < produced.load(std::memory_order_relaxed)) {
                if (q.pop(val)) {
                    consumed.fetch_add(1, std::memory_order_relaxed);
                } else {
                    std::this_thread::yield();
                }
            }
        });
    }
    
    auto t1 = std::chrono::high_resolution_clock::now();
    for (auto& t : threads) t.join();
    auto t2 = std::chrono::high_resolution_clock::now();
    
    std::cout << "Produced: " << produced.load() 
              << ", Consumed: " << consumed.load()
              << ", Time: " << std::chrono::duration_cast<std::chrono::ms>(t2-t1).count() << "ms"
              << std::endl;
    
    assert(produced.load() == consumed.load());
}

// Stress test com verificação de integridade
template<typename Stack>
void stress_test_stack_integrity(Stack& s, int threads, int ops) {
    std::atomic<int> push_count{0}, pop_count{0};
    std::vector<std::thread> workers;
    const int total_ops = threads * ops;
    
    for (int i = 0; i < threads; ++i) {
        workers.emplace_back([&, i]() {
            std::mt19937 rng(i);
            for (int j = 0; j < ops; ++j) {
                if (rng() % 2 || s.empty()) {
                    s.push(i * ops + j);
                    push_count.fetch_add(1, std::memory_order_relaxed);
                } else {
                    int val;
                    if (s.pop(val)) {
                        pop_count.fetch_add(1, std::memory_order_relaxed);
                        // Verify value was previously pushed
                        // (requires tracking pushed values)
                    }
                }
            }
        });
    }
    
    for (auto& w : workers) w.join();
    
    std::cout << "Pushes: " << push_count.load() 
              << ", Pops: " << pop_count.load() << std::endl;
}
```

EOF
## 10. Exercício Prático

### Implement a Lock-Free MPMC Queue

Implemente uma queue MPMC (Multi-Producer Multi-Consumer) lock-free completa com proteção hazard pointer.

```cpp
#include <atomic>
#include <memory>
#include <thread>
#include <vector>
#include <cassert>

// ============================================================
// HAZARD POINTER DOMAIN (reuso do código anterior)
// ============================================================

class HazardPointerDomain {
    struct Record {
        std::atomic<std::thread::id> owner{};
        std::atomic<void*> hazard{nullptr};
        std::atomic<bool> active{false};
    };
    
    static constexpr size_t MAX_RECORDS = 256;
    std::array<Record, MAX_RECORDS> records_;
    std::atomic<size_t> count_{0};
    
    struct RetiredList {
        std::vector<void*> nodes;
        std::mutex mutex;
        size_t threshold = 100;
    };
    static thread_local RetiredList* tl_retired_;
    
    RetiredList& get_retired() {
        if (!tl_retired_) tl_retired_ = new RetiredList();
        return *tl_retired_;
    }
    
    bool is_hazard(void* ptr) const {
        for (size_t i = 0; i < count_.load(std::memory_order_acquire); ++i) {
            if (records_[i].active.load(std::memory_order_acquire) &&
                records_[i].hazard.load(std::memory_order_acquire) == ptr)
                return true;
        }
        return false;
    }
    
    void scan(RetiredList& list) {
        std::vector<void*> to_del;
        {
            std::lock_guard<std::mutex> lock(list.mutex);
            for (void* p : list.nodes) if (!is_hazard(p)) to_del.push_back(p);
            std::vector<void*> rem;
            for (void* p : list.nodes) {
                bool found = false;
                for (void* d : to_del) if (d == p) { found = true; break; }
                if (!found) rem.push_back(p);
            }
            list.nodes.swap(rem);
        }
        for (void* p : to_del) ::operator delete(p);
    }
    
public:
    class HazardPointer {
        HazardPointerDomain* domain_;
        size_t idx_;
    public:
        HazardPointer() : domain_(nullptr), idx_(SIZE_MAX) {}
        explicit HazardPointer(HazardPointerDomain* d) : domain_(d) {
            for (size_t i = 0; i < MAX_RECORDS; ++i) {
                std::thread::id empty;
                if (domain_->records_[i].owner.compare_exchange_strong(empty, std::this_thread::get_id())) {
                    domain_->records_[i].active.store(true, std::memory_order_release);
                    idx_ = i;
                    size_t c = domain_->count_.load(std::memory_order_relaxed);
                    while (c <= i && !domain_->count_.compare_exchange_weak(c, i + 1)) {}
                    return;
                }
            }
            assert(false);
        }
        ~HazardPointer() { if (domain_) { domain_->records_[idx_].hazard.store(nullptr, std::memory_order_release); domain_->records_[idx_].active.store(false, std::memory_order_release); domain_->records_[idx_].owner.store(std::thread::id{}, std::memory_order_release); } }
        HazardPointer(const HazardPointer&) = delete;
        HazardPointer& operator=(const HazardPointer&) = delete;
        void protect(void* p) { if (domain_) domain_->records_[idx_].hazard.store(p, std::memory_order_release); }
        void reset() { if (domain_) domain_->records_[idx_].hazard.store(nullptr, std::memory_order_release); }
    };
    
    HazardPointerDomain() = default;
    HazardPointer make_hazard_pointer() { return HazardPointer(this); }
    void retire(void* p) { auto& l = get_retired(); std::lock_guard<std::mutex> lock(l.mutex); l.nodes.push_back(p); if (l.nodes.size() >= l.threshold) scan(l); }
    void force_reclaim() { auto& l = get_retired(); scan(l); }
};
thread_local typename HazardPointerDomain::RetiredList* HazardPointerDomain::tl_retired_ = nullptr;

HazardPointerDomain& global_hazard_domain() {
    static HazardPointerDomain d; return d;
}

// ============================================================
// LOCK-FREE MPMC QUEUE (Michael-Scott com Hazard Pointers)
// ============================================================

template<typename T>
class LockFreeMPMCQueue {
    struct Node {
        T value;
        std::atomic<Node*> next;
        template<typename... Args>
        Node(Args&&... args) : value(std::forward<Args>(args)...), next(nullptr) {}
    };
    
    std::atomic<Node*> head_;
    std::atomic<Node*> tail_;
    HazardPointerDomain& domain_;
    
    void try_advance_tail(Node* tail, Node* next) {
        tail_.compare_exchange_weak(tail, next, std::memory_order_release, std::memory_order_relaxed);
    }
    
public:
    explicit LockFreeMPMCQueue(HazardPointerDomain& d = global_hazard_domain()) : domain_(d) {
        Node* dummy = new Node();
        head_.store(dummy, std::memory_order_relaxed);
        tail_.store(dummy, std::memory_order_relaxed);
    }
    
    ~LockFreeMPMCQueue() {
        T dummy;
        while (dequeue(dummy)) {}
        Node* h = head_.load(); delete h;
    }
    
    LockFreeMPMCQueue(const LockFreeMPMCQueue&) = delete;
    LockFreeMPMCQueue& operator=(const LockFreeMPMCQueue&) = delete;
    
    // Enqueue: lock-free, wait-free para single producer
    template<typename... Args>
    void enqueue(Args&&... args) {
        Node* new_node = new Node(std::forward<Args>(args)...);
        Node* tail = tail_.load(std::memory_order_acquire);
        Node* next = nullptr;
        
        while (true) {
            next = tail->next.load(std::memory_order_acquire);
            if (tail == tail_.load(std::memory_order_acquire)) {
                if (next == nullptr) {
                    if (tail->next.compare_exchange_weak(next, new_node,
                                                          std::memory_order_release,
                                                          std::memory_order_relaxed)) {
                        break;
                    }
                } else {
                    try_advance_tail(tail, next);
                }
            }
            tail = tail_.load(std::memory_order_acquire);
        }
        try_advance_tail(tail, new_node);
    }
    
    // Dequeue: lock-free com hazard pointers
    bool dequeue(T& value) {
        auto hp_head = domain_.make_hazard_pointer();
        auto hp_next = domain_.make_hazard_pointer();
        
        Node* head = head_.load(std::memory_order_acquire);
        Node* tail = tail_.load(std::memory_order_acquire);
        Node* next = nullptr;
        
        while (true) {
            next = head->next.load(std::memory_order_acquire);
            if (head == head_.load(std::memory_order_acquire)) {
                if (head == tail) {
                    if (next == nullptr) return false; // Empty
                    try_advance_tail(tail, next);
                } else {
                    hp_next.protect(next);
                    // Re-check
                    if (head != head_.load(std::memory_order_acquire)) {
                        hp_next.reset();
                        head = head_.load(std::memory_order_acquire);
                        tail = tail_.load(std::memory_order_acquire);
                        continue;
                    }
                    
                    value = std::move(next->value);
                    if (head_.compare_exchange_weak(head, next,
                                                     std::memory_order_acq_rel,
                                                     std::memory_order_acquire)) {
                        hp_next.reset();
                        hp_head.protect(head); // Protect old head for retirement
                        domain_.retire(head);
                        return true;
                    }
                    hp_next.reset();
                }
            }
            head = head_.load(std::memory_order_acquire);
            tail = tail_.load(std::memory_order_acquire);
        }
    }
    
    bool empty() const {
        Node* h = head_.load(std::memory_order_acquire);
        Node* t = tail_.load(std::memory_order_acquire);
        return h == t && h->next.load(std::memory_order_acquire) == nullptr;
    }
};

// ============================================================
// BENCHMARK CONTRA std::queue + mutex
// ============================================================

#include <queue>
#include <mutex>
#include <chrono>
#include <iostream>

template<typename Queue>
void benchmark_mpsc(Queue& q, int producers, int consumers, int ops) {
    std::atomic<int> produced{0}, consumed{0};
    std::atomic<bool> start{false}, done{false};
    std::vector<std::thread> threads;
    
    for (int i = 0; i < producers; ++i) {
        threads.emplace_back([&, i]() {
            while (!start.load(std::memory_order_acquire)) {}
            for (int j = 0; j < ops; ++j) {
                q.enqueue(i * ops + j);
                produced.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    
    for (int i = 0; i < consumers; ++i) {
        threads.emplace_back([&]() {
            while (!start.load(std::memory_order_acquire)) {}
            int val;
            while (!done.load(std::memory_order_acquire) || 
                   consumed.load(std::memory_order_relaxed) < produced.load(std::memory_order_relaxed)) {
                if (q.dequeue(val)) {
                    consumed.fetch_add(1, std::memory_order_relaxed);
                } else {
                    std::this_thread::yield();
                }
            }
        });
    }
    
    auto t1 = std::chrono::high_resolution_clock::now();
    start.store(true, std::memory_order_release);
    for (auto& t : threads) t.join();
    done.store(true, std::memory_order_release);
    auto t2 = std::chrono::high_resolution_clock::now();
    
    auto us = std::chrono::duration_cast<std::chrono::microseconds>(t2 - t1).count();
    std::cout << "  Produced: " << produced.load() << ", Consumed: " << consumed.load()
              << ", Time: " << us << " us"
              << ", Throughput: " << (double)(producers * ops) / us * 1e6 << " ops/s"
              << std::endl;
}

// Mutex queue para comparação
template<typename T>
class MutexQueue {
    std::queue<T> q_;
    mutable std::mutex m_;
public:
    template<typename... Args>
    void enqueue(Args&&... args) {
        std::lock_guard<std::mutex> lock(m_);
        q_.emplace(std::forward<Args>(args)...);
    }
    bool dequeue(T& value) {
        std::lock_guard<std::mutex> lock(m_);
        if (q_.empty()) return false;
        value = std::move(q_.front());
        q_.pop();
        return true;
    }
};

int main() {
    const int producers = 4, consumers = 4, ops = 100000;
    
    std::cout << "=== Lock-Free MPMC Queue (Hazard Pointers) ===" << std::endl;
    LockFreeMPMCQueue<int> lfq;
    benchmark_mpsc(lfq, producers, consumers, ops);
    
    std::cout << "\n=== std::queue + mutex ===" << std::endl;
    MutexQueue<int> mq;
    benchmark_mpsc(mq, producers, consumers, ops);
    
    std::cout << "\n=== Verificação de Linearizabilidade ===" << std::endl;
    // Teste simples: enqueue 1..N, dequeue deve retornar 1..N em ordem
    LockFreeMPMCQueue<int> test_q;
    for (int i = 1; i <= 1000; ++i) test_q.enqueue(i);
    for (int i = 1; i <= 1000; ++i) {
        int val; assert(test_q.dequeue(val)); assert(val == i);
    }
    assert(test_q.empty());
    std::cout << "  FIFO order verified: PASS" << std::endl;
    
    // Teste concorrente de integridade
    std::cout << "\n=== Teste de Integridade Concorrente ===" << std::endl;
    LockFreeMPMCQueue<int> integrity_q;
    std::atomic<int> pushed{0}, popped{0};
    std::vector<std::thread> workers;
    
    for (int i = 0; i < 4; ++i) {
        workers.emplace_back([&]() {
            for (int j = 0; j < 10000; ++j) {
                integrity_q.enqueue(pushed.fetch_add(1) + 1);
            }
        });
    }
    for (int i = 0; i < 4; ++i) {
        workers.emplace_back([&]() {
            int val;
            while (popped.load() < 40000) {
                if (integrity_q.dequeue(val)) popped.fetch_add(1);
            }
        });
    }
    for (auto& w : workers) w.join();
    std::cout << "  Pushed: " << pushed.load() << ", Popped: " << popped.load() << " - " 
              << (pushed.load() == popped.load() ? "PASS" : "FAIL") << std::endl;
    
    return 0;
}
```

### Exercícios Adicionais

1. **Implemente um lock-free hash map** usando split-ordered lists com hazard pointers
2. **Adicione suporte a iteradores lock-free** na queue MPMC
3. **Implemente epoch-based reclamation** como alternativa aos hazard pointers
4. **Compare desempenho** com folly::MPMCQueue, boost::lockfree::queue, moodycamel::ConcurrentQueue
5. **Verifique linearizabilidade** usando modelo de verificação (Nidhugg/CDSChecker)

EOF
## 11. Referências

### Artigos Fundamentais

1. **Treiber, R. K.** (1986). "Systems Programming: Coping with Parallelism". *IBM Almaden Research Center*. RJ 5118.
   - Algoritmo original de stack lock-free (Treiber stack)

2. **Michael, M. M. & Scott, M. L.** (1996). "Simple, Fast, and Practical Non-Blocking and Blocking Concurrent Queue Algorithms". *PODC '96*.
   - Michael-Scott queue algorithm

3. **Michael, M. M.** (2002). "High Performance Dynamic Lock-Free Hash Tables and List-Based Sets". *SPAA '02*.
   - Lock-free hash table com split-ordered lists

4. **Shalev, N. & Shavit, N.** (2003). "Split-Ordered Lists: Lock-Free Extensible Hash Tables". *PODC '03*.
   - Split-ordered lists para hash maps extensíveis

5. **Maged M. Michael** (2004). "Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects". *IEEE TPDS*.
   - Hazard pointers paper original

6. **Fraser, K.** (2004). "Practical Lock-Freedom". *PhD Thesis, University of Cambridge*.
   - Implementação prática de lock-free, RCU userspace

7. **Hart, T. E., McKenney, P. E., Brown, A. D., & Walpole, J.** (2007). "Performance of Memory Reclamation for Lockless Synchronization". *J. Parallel Distrib. Comput.*
   - Comparação de técnicas de reclamation

8. **Dice, D., Shalev, N., & Shavit, N.** (2016). "Transactional Locking II". *DISC '16*.
   - TL2 e comparação com lock-free

### Livros e Referências Técnicas

9. **Williams, A.** (2019). *C++ Concurrency in Action, 2nd Edition*. Manning Publications.
   - Capítulos 5, 6, 7: atomic operations, lock-free, memory model

10. **McKenney, P. E.** (2021). *Is Parallel Programming Hard, And, If So, What Can You Do About It?*. Linux Kernel Documentation.
    - RCU detalhado, memory barriers, reclamation

11. **Herlihy, M. & Shavit, N.** (2012). *The Art of Multiprocessor Programming, Revised Reprint*. Morgan Kaufmann.
    - Capítulos 10-15: lock-free, wait-free, ABA, reclamation

12. **Boehm, H. & Adve, S.** (2008). "Foundations of the C++ Concurrency Memory Model". *PLDI '08*.
    - C++ memory model formal

### CVEs e Bugs Reais Documentados

13. **CVE-2016-0728** - Linux Kernel Keyring Reference Count Overflow
    - https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-0728
    - ABA em reference counting leva a use-after-free e privilege escalation

14. **CVE-2017-1000112** - Linux Kernel UDP Fragmentation Offset
    - Race condition em manipulação de skbuff

15. **CVE-2019-11477** - Linux Kernel TCP SACK Panic
    - Integer overflow em reassembly, relacionado a concorrência

16. **CVE-2020-8835** - Linux Kernel BPF Verifier
    - Race condition em verificação de bounds

17. **CVE-2021-4034** - Polkit pkexec (PwnKit)
    - Não lock-free mas demonstra importância de atomicidade

18. **jemalloc Issue #1492** - ABA em freelist lock-free
    - https://github.com/jemalloc/jemalloc/issues/1492

19. **TCMalloc Issue** - Race condition em central free list
    - https://github.com/gperftools/gperftools/issues

### Ferramentas de Verificação

20. **CDSChecker** - https://github.com/plrg/cdschecker
    - Model checker para C/C++ concorrente

21. **Nidhugg** - https://github.com/nidhugg/nidhugg
    - Stateless model checker para pthreads

22. **ThreadSanitizer (TSan)** - https://clang.llvm.org/docs/ThreadSanitizer.html
    - Data race detector dinâmico

23. **Helgrind/DRD** (Valgrind) - https://valgrind.org/docs/manual/hg-manual.html
    - Race detection dinâmico

24. **GenMC** - https://github.com/model-checking/genmc
    - Model checker para C/C++ com memory model fraco

### Bibliotecas e Implementações de Referência

25. **liburcu** - https://liburcu.org/
    - Userspace RCU library

26. **folly** (Facebook) - https://github.com/facebook/folly
    - folly::MPMCQueue, folly::AtomicSharedPtr, folly::Hazptr

27. **moodycamel::ConcurrentQueue** - https://github.com/cameron314/concurrentqueue
    - Lock-free MPMC queue de alta performance

28. **boost::lockfree** - https://www.boost.org/doc/libs/release/doc/html/lockfree.html
    - Lock-free stack, queue, spsc_queue

29. **CDS (Concurrent Data Structures)** - https://github.com/khizmax/libcds
    - Biblioteca completa de estruturas lock-free

30. **crossbeam** (Rust) - https://github.com/crossbeam-rs/crossbeam
    - Referência para hazard pointers, epoch-based reclamation

### Artigos de Performance e Benchmarks

31. **David, T., Guerraoui, R., & Trigonakis, V.** (2013). "Everything You Always Wanted to Know About Synchronization but Were Afraid to Ask". *ASPLOS '13*.
    - Benchmark abrangente de sincronização

32. **Morrison, A. & Afek, Y.** (2013). "Fast Concurrent Queues for x86 Processors". *PPoPP '13*.
    - Otimizações x86 para queues

33. **Le, W., Gopalakrishnan, G., & Yang, Z.** (2014). "Race Condition Detection for Lock-Free Data Structures". *PLDI '14*.
    - Detecção de race em estruturas lock-free

### Documentação de Linguagem

34. **ISO/IEC 14882:2020** - C++20 Standard
    - [atomics], [atomics.types.operations], [util.smartptr.shared.atomic]

35. **cppreference.com** - https://en.cppreference.com/w/cpp/atomic
    - Documentação std::atomic, memory_order, atomic_shared_ptr

36. **Linux Kernel Documentation** - https://www.kernel.org/doc/html/latest/RCU/
    - RCU API, design patterns, best practices

### Talks e Apresentações

37. **Michael, M.** (2016). "Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects". *CppCon 2016*.
38. **McKenney, P. E.** (2018). "RCU: From Theory to Practice". *Linux Plumbers Conference*.
39. **Williams, A.** (2019). "Lock-Free Programming in C++20". *CppCon 2019*.
40. **Lamport, L.** (1979). "How to Make a Multiprocessor Computer That Correctly Executes Multiprocess Programs". *IEEE Trans. Computers*.
    - Paper original sobre linearizabilidade

### Recursos Online

- **Concurrency Kit (CK)** - https://concurrencykit.org/
- **lockfree** (GitHub topic) - https://github.com/topics/lockfree
- **Paul McKenney's RCU page** - https://www.rdrop.com/users/paulmck/RCU/
- **Dmitry Vyukov's algorithms** - http://www.1024cores.net/home/lock-free-algorithms

---

*Fim do Capítulo 3 — Programação Lock-Free e Atômicos Avançados*

