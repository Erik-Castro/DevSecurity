# Capítulo 7 — False Sharing, Cache Coherence e Otimização de Memória

## Objetivos de Aprendizado

1. Identificar e diagnosticar false sharing em código multithreaded
2. Compreender protocolos de coerência de cache (MESI/MOESI)
3. Aplicar padding correto para eliminar false sharing
4. Otimizar código para hierarquia de cache moderna
5. Utilizar perf/VTune para profiling de cache misses

---

## 1. Cache Lines e Coerência

### 1.1 O que é False Sharing

```cpp
#include <atomic>
#include <thread>
#include <vector>
#include <chrono>
#include <iostream>
#include <new>

// ANTI-PADRÃO: false sharing — contadores adjacentes na mesma cache line
struct alignas(64) PaddedInt {
    std::atomic<int> value;
    char padding[64 - sizeof(std::atomic<int>)];
};

struct UnpaddedInt {
    std::atomic<int> value;
};

void benchmark_false_sharing() {
    constexpr int NUM_THREADS = 8;
    constexpr int ITERATIONS = 10'000'000;
    
    // Test with false sharing
    {
        UnpaddedInt counters[NUM_THREADS];
        for (auto& c : counters) c.value.store(0, std::memory_order_relaxed);
        
        auto start = std::chrono::high_resolution_clock::now();
        
        std::vector<std::thread> threads;
        for (int i = 0; i < NUM_THREADS; ++i) {
            threads.emplace_back([&counters, i] {
                for (int j = 0; j < ITERATIONS; ++j) {
                    counters[i].value.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << "With false sharing: " << ms << "ms\n";
    }
    
    // Test without false sharing (padded)
    {
        PaddedInt counters[NUM_THREADS];
        for (auto& c : counters) c.value.store(0, std::memory_order_relaxed);
        
        auto start = std::chrono::high_resolution_clock::now();
        
        std::vector<std::thread> threads;
        for (int i = 0; i < NUM_THREADS; ++i) {
            threads.emplace_back([&counters, i] {
                for (int j = 0; j < ITERATIONS; ++j) {
                    counters[i].value.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << "Without false sharing: " << ms << "ms\n";
    }
}

int main() {
    benchmark_false_sharing();
    // Output típico:
    // With false sharing: 2847ms
    // Without false sharing: 42ms (67x faster!)
    return 0;
}
```

### 1.2 Detecção com perf

```bash
# Compilar com símbolos
g++ -O2 -g -pthread false_sharing.cpp -o false_sharing

# Medir cache misses com perf
perf stat -e cache-references,cache-misses,cycles,instructions \
    -e LLC-loads,LLC-load-misses ./false_sharing

# Profiling detalhado
perf record -g ./false_sharing
perf report
```

### 1.3 Padrões Comuns de False Sharing

```cpp
#include <atomic>
#include <new>
#include <array>
#include <thread>

// PADRÃO 1: Contadores adjacentes
struct BadCounters {
    std::atomic<int> a, b, c, d;  // All on same cache line!
};

struct GoodCounters {
    struct alignas(64) PaddedAtomic {
        std::atomic<int> value{0};
    };
    PaddedAtomic a, b, c, d;  // Each on separate cache line
};

// PADRÃO 2: Shared_mutex adjacent to data
struct BadSharedData {
    std::shared_mutex mutex;
    int data;  // False sharing between mutex and data!
};

struct GoodSharedData {
    std::shared_mutex mutex;
    alignas(64) int data;  // Separate cache lines
};

// PADRÃO 3: Head/Tail em queues
template<typename T>
struct BadQueue {
    std::atomic<size_t> head{0};
    std::atomic<size_t> tail{0};
    T buffer[1024];
};

template<typename T>
struct GoodQueue {
    alignas(64) std::atomic<size_t> head{0};
    alignas(64) std::atomic<size_t> tail{0};
    T buffer[1024];
};
```

---

## 2. Memory Ordering e Performance

```cpp
#include <atomic>
#include <thread>
#include <chrono>
#include <iostream>
#include <vector>

void benchmark_memory_orderings() {
    constexpr int ITERATIONS = 100'000'000;
    
    auto benchmark = [&](auto order, const char* name) {
        std::atomic<int> counter{0};
        
        auto start = std::chrono::high_resolution_clock::now();
        
        std::vector<std::thread> threads;
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&counter, order] {
                for (int j = 0; j < ITERATIONS; ++j) {
                    counter.fetch_add(1, order);
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << name << ": " << ms << "ms\n";
    };
    
    benchmark(std::memory_order_relaxed, "relaxed ");
    benchmark(std::memory_order_acquire, "acquire ");
    benchmark(std::memory_order_release, "release ");
    benchmark(std::memory_order_acq_rel, "acq_rel ");
    benchmark(std::memory_order_seq_cst, "seq_cst ");
}

int main() {
    benchmark_memory_orderings();
    return 0;
}
```

---

## 3. NUMA-Aware Programming

```cpp
#include <thread>
#include <vector>
#include <numa.h>
#include <iostream>

class NumaAllocator {
public:
    static void* allocate_on_node(size_t size, int node) {
        return numa_alloc_onnode(size, node);
    }
    
    static void deallocate(void* ptr, size_t size) {
        numa_free(ptr, size);
    }
    
    static int get_current_node() {
        return numa_node_of_cpu(sched_getcpu());
    }
    
    static void pin_to_node(int node) {
        struct bitmask* cpumask = numa_allocate_cpumask();
        numa_node_to_cpus(node, cpumask);
        numa_sched_setaffinity(0, cpumask);
        numa_free_cpumask(cpumask);
    }
};

void numa_example() {
    if (numa_available() < 0) {
        std::cout << "NUMA not available\n";
        return;
    }
    
    int max_node = numa_max_node();
    std::cout << "NUMA nodes: " << max_node + 1 << "\n";
    
    // Allocate on each node
    for (int node = 0; node <= max_node; ++node) {
        void* mem = NumaAllocator::allocate_on_node(1024 * 1024, node);
        if (mem) {
            std::cout << "Allocated 1MB on node " << node << "\n";
            NumaAllocator::deallocate(mem, 1024 * 1024);
        }
    }
    
    // Pin threads to nodes
    int current = NumaAllocator::get_current_node();
    std::cout << "Current NUMA node: " << current << "\n";
}
```

---

## 4. Prefetching

```cpp
#include <cstddef>
#include <new>

#ifdef __GNUC__
#define PREFETCH(addr) __builtin_prefetch((addr), 0, 3)
#define PREFETCH_WRITE(addr) __builtin_prefetch((addr), 1, 3)
#elif defined(_MSC_VER)
#include <xmmintrin.h>
#define PREFETCH(addr) _mm_prefetch(reinterpret_cast<const char*>(addr), _MM_HINT_T3)
#define PREFETCH_WRITE(addr) _mm_prefetch(reinterpret_cast<const char*>(addr), _MM_HINT_T0)
#endif

template<typename T>
void process_with_prefetch(T* data, size_t n) {
    constexpr int PREFETCH_DISTANCE = 8;
    
    for (size_t i = 0; i < n; ++i) {
        if (i + PREFETCH_DISTANCE < n) {
            PREFETCH(&data[i + PREFETCH_DISTANCE]);
        }
        // Process data[i]...
        data[i] = data[i] * 2;
    }
}

// Linked list traversal with prefetch
struct Node {
    int data;
    Node* next;
};

void traverse_list_prefetch(Node* head) {
    if (!head) return;
    
    Node* current = head;
    Node* next = head->next;
    
    if (next) PREFETCH(next);
    
    while (current) {
        Node* next_next = next ? next->next : nullptr;
        if (next_next) PREFETCH(next_next);
        
        // Process current
        current->data *= 2;
        
        current = next;
        next = next_next;
    }
}
```

---

## 5. Struct-of-Arrays vs Array-of-Structs

```cpp
#include <vector>
#include <chrono>
#include <iostream>
#include <cmath>

constexpr size_t N = 1'000'000;
constexpr int ITERATIONS = 100;

// Array of Structs (AoS)
struct ParticleAoS {
    float x, y, z;
    float vx, vy, vz;
    float mass;
};

// Struct of Arrays (SoA)
struct ParticlesSoA {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> mass;
    
    ParticlesSoA(size_t n) : x(n), y(n), z(n), vx(n), vy(n, 0), vz(n, 0), mass(n, 1.0f) {}
};

int main() {
    std::vector<ParticleAoS> aos(N);
    ParticlesSoA soa(N);
    
    // Initialize
    for (size_t i = 0; i < N; ++i) {
        aos[i] = {float(i), 0, 0, 1, 0, 0, 1.0f};
        soa.x[i] = float(i);
    }
    
    // Benchmark AoS
    auto start = std::chrono::high_resolution_clock::now();
    for (int iter = 0; iter < ITERATIONS; ++iter) {
        for (auto& p : aos) {
            p.x += p.vx * 0.01f;
            p.y += p.vy * 0.01f;
            p.z += p.vz * 0.01f;
        }
    }
    auto aos_time = std::chrono::high_resolution_clock::now() - start;
    
    // Benchmark SoA
    start = std::chrono::high_resolution_clock::now();
    for (int iter = 0; iter < ITERATIONS; ++iter) {
        for (size_t i = 0; i < N; ++i) {
            soa.x[i] += soa.vx[i] * 0.01f;
            soa.y[i] += soa.vy[i] * 0.01f;
            soa.z[i] += soa.vz[i] * 0.01f;
        }
    }
    auto soa_time = std::chrono::high_resolution_clock::now() - start;
    
    auto aos_ms = std::chrono::duration_cast<std::chrono::milliseconds>(aos_time).count();
    auto soa_ms = std::chrono::duration_cast<std::chrono::milliseconds>(soa_time).count();
    
    std::cout << "AoS: " << aos_ms << "ms\n";
    std::cout << "SoA: " << soa_ms << "ms\n";
    std::cout << "Speedup: " << (double)aos_ms / soa_ms << "x\n";
    
    return 0;
}
```

---

## 6. Referências

- **Agner Fog** — Optimizing subroutines in assembly language (agner.org)
- **Intel Optimization Reference Manual** — intel.com
- **What Every Programmer Should Know About Memory** — Ulrich Drepper
- **C++ Performance TR** —wg21.link/p0883
- **perf wiki** — perf.wiki.kernel.org
- **numactl/numad** — Linux NUMA tools
---

*[Capítulo anterior: 06 — Paralelismo Std Algorithms](06-paralelismo-std-algorithms.md)*
*[Próximo capítulo: 08 — Containers Concorrentes](08-containers-concorrentes.md)*
