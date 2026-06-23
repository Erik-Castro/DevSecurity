# Capítulo 14 — Performance e Escalabilidade em Concorrência

## Objetivos de Aprendizado

1. Medir throughput e latência de código concorrente com precisão
2. Identificar gargalos de performance com profiling tools (perf, VTune)
3. Aplicar Amdahl's Law e Gustafson's Law para prever escalabilidade
4. Otimizar para hierarquia de cache e arquiteturas NUMA
5. Reduzir lock contention e false sharing em código production

---

## 1. Métricas de Performance Concorrente

### 1.1 Throughput vs Latência

```cpp
#include <chrono>
#include <thread>
#include <vector>
#include <atomic>
#include <iostream>
#include <numeric>

class PerformanceMetrics {
    std::atomic<long long> total_ops_{0};
    std::atomic<long long> total_ns_{0};
    
public:
    void record_operation(long long ns) {
        total_ops_.fetch_add(1, std::memory_order_relaxed);
        total_ns_.fetch_add(ns, std::memory_order_relaxed);
    }
    
    double throughput() const {
        long long ops = total_ops_.load();
        long long ns = total_ns_.load();
        return (ns > 0) ? static_cast<double>(ops) / (ns / 1e9) : 0;
    }
    
    double avg_latency_ns() const {
        long long ops = total_ops_.load();
        long long ns = total_ns_.load();
        return (ops > 0) ? static_cast<double>(ns) / ops : 0;
    }
    
    void reset() {
        total_ops_.store(0);
        total_ns_.store(0);
    }
};

void benchmark_atomic_ops() {
    PerformanceMetrics metrics;
    constexpr int NUM_THREADS = 8;
    constexpr int OPS_PER_THREAD = 1'000'000;
    
    std::atomic<int> counter{0};
    
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([&] {
            for (int i = 0; i < OPS_PER_THREAD; ++i) {
                auto op_start = std::chrono::high_resolution_clock::now();
                counter.fetch_add(1, std::memory_order_relaxed);
                auto op_end = std::chrono::high_resolution_clock::now();
                metrics.record_operation(
                    std::chrono::duration_cast<std::chrono::nanoseconds>(op_end - op_start).count());
            }
        });
    }
    
    for (auto& t : threads) t.join();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto wall_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    
    std::cout << "=== Atomic Performance ===\n";
    std::cout << "Threads: " << NUM_THREADS << "\n";
    std::cout << "Total ops: " << counter.load() << "\n";
    std::cout << "Wall time: " << wall_ns / 1e6 << " ms\n";
    std::cout << "Throughput: " << metrics.throughput() / 1e6 << " Mops/s\n";
    std::cout << "Avg latency: " << metrics.avg_latency_ns() << " ns/op\n";
    std::cout << "Ops per thread: " << counter.load() / NUM_THREADS << "\n";
}

int main() {
    benchmark_atomic_ops();
    return 0;
}
```

### 1.2 Contention Metrics

```cpp
#include <atomic>
#include <chrono>
#include <thread>
#include <vector>
#include <iostream>
#include <mutex>

class ContentionAnalyzer {
    std::atomic<int> cas_attempts_{0};
    std::atomic<int> cas_failures_{0};
    std::atomic<long long> total_spins_{0};
    std::atomic<int> lock_waits_{0};
    std::atomic<long long> lock_wait_ns_{0};
    
public:
    void record_cas_attempt() {
        cas_attempts_.fetch_add(1, std::memory_order_relaxed);
    }
    
    void record_cas_failure() {
        cas_failures_.fetch_add(1, std::memory_order_relaxed);
    }
    
    void record_spin() {
        total_spins_.fetch_add(1, std::memory_order_relaxed);
    }
    
    void record_lock_wait(long long ns) {
        lock_waits_.fetch_add(1, std::memory_order_relaxed);
        lock_wait_ns_.fetch_add(ns, std::memory_order_relaxed);
    }
    
    void report() const {
        int attempts = cas_attempts_.load();
        int failures = cas_failures_.load();
        long long spins = total_spins_.load();
        int waits = lock_waits_.load();
        long long wait_ns = lock_wait_ns_.load();
        
        std::cout << "\n=== Contention Analysis ===\n";
        std::cout << "CAS attempts: " << attempts << "\n";
        std::cout << "CAS failures: " << failures << "\n";
        std::cout << "CAS failure rate: " << (attempts > 0 ? 100.0 * failures / attempts : 0) << "%\n";
        std::cout << "Total spins: " << spins << "\n";
        std::cout << "Lock waits: " << waits << "\n";
        std::cout << "Avg lock wait: " << (waits > 0 ? wait_ns / waits : 0) << " ns\n";
    }
    
    void reset() {
        cas_attempts_.store(0);
        cas_failures_.store(0);
        total_spins_.store(0);
        lock_waits_.store(0);
        lock_wait_ns_.store(0);
    }
};

int main() {
    ContentionAnalyzer analyzer;
    
    std::atomic<int> shared{0};
    std::vector<std::thread> threads;
    
    for (int i = 0; i < 8; ++i) {
        threads.emplace_back([&] {
            for (int j = 0; j < 100000; ++j) {
                analyzer.record_cas_attempt();
                int expected = shared.load(std::memory_order_relaxed);
                while (!shared.compare_exchange_weak(expected, expected + 1,
                    std::memory_order_relaxed)) {
                    analyzer.record_cas_failure();
                    analyzer.record_spin();
                }
            }
        });
    }
    
    for (auto& t : threads) t.join();
    analyzer.report();
    
    return 0;
}
```

---

## 2. Amdahl's Law e Gustafson's Law

### 2.1 Amdahl's Law

```cpp
#include <iostream>
#include <cmath>
#include <vector>
#include <thread>
#include <chrono>

double amdahl_speedup(double parallel_fraction, int num_threads) {
    if (num_threads <= 0) return 1.0;
    return 1.0 / ((1.0 - parallel_fraction) + parallel_fraction / num_threads);
}

void amdahl_analysis() {
    std::cout << "=== Amdahl's Law Analysis ===\n\n";
    
    std::vector<double> parallel_fractions = {0.50, 0.75, 0.90, 0.95, 0.99, 0.999};
    std::vector<int> thread_counts = {1, 2, 4, 8, 16, 32, 64};
    
    std::cout << "P\\N\t";
    for (int n : thread_counts) std::cout << n << "\t";
    std::cout << "\n";
    
    for (double p : parallel_fractions) {
        std::cout << (p * 100) << "%\t";
        for (int n : thread_counts) {
            std::cout << std::fixed << std::setprecision(1)
                      << amdahl_speedup(p, n) << "x\t";
        }
        std::cout << "\n";
    }
    
    std::cout << "\nLimites teóricos:\n";
    std::cout << "P=50%  → max speedup: " << 1.0/(1.0-0.50) << "x\n";
    std::cout << "P=90%  → max speedup: " << 1.0/(1.0-0.90) << "x\n";
    std::cout << "P=99%  → max speedup: " << 1.0/(1.0-0.99) << "x\n";
    std::cout << "P=99.9% → max speedup: " << 1.0/(1.0-0.999) << "x\n";
}

// Prático: medir P empiricamente
void measure_parallel_fraction() {
    const size_t N = 10'000'000;
    std::vector<double> data(N, 1.0);
    
    auto seq_start = std::chrono::high_resolution_clock::now();
    double sum = 0;
    for (size_t i = 0; i < N; ++i) sum += std::sin(data[i]);
    auto seq_end = std::chrono::high_resolution_clock::now();
    auto seq_ms = std::chrono::duration_cast<std::chrono::milliseconds>(seq_end - seq_start).count();
    
    auto par_start = std::chrono::high_resolution_clock::now();
    std::atomic<double> par_sum{0.0};
    std::vector<std::thread> threads;
    int num_threads = 8;
    size_t chunk = N / num_threads;
    
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&data, &par_sum, t, chunk, N] {
            double local = 0;
            size_t start = t * chunk;
            size_t end = (t == num_threads - 1) ? N : start + chunk;
            for (size_t i = start; i < end; ++i) local += std::sin(data[i]);
            par_sum.fetch_add(local, std::memory_order_relaxed);
        });
    }
    for (auto& t : threads) t.join();
    
    auto par_end = std::chrono::high_resolution_clock::now();
    auto par_ms = std::chrono::duration_cast<std::chrono::milliseconds>(par_end - par_start).count();
    
    double speedup = static_cast<double>(seq_ms) / par_ms;
    double P = 1.0 - (1.0 / speedup - 1.0) / (num_threads - 1);
    
    std::cout << "\n=== Empirical Parallel Fraction ===\n";
    std::cout << "Sequential: " << seq_ms << "ms\n";
    std::cout << "Parallel (" << num_threads << "): " << par_ms << "ms\n";
    std::cout << "Speedup: " << speedup << "x\n";
    std::cout << "Estimated P: " << P * 100 << "%\n";
}

int main() {
    amdahl_analysis();
    measure_parallel_fraction();
    return 0;
}
```

### 2.2 Gustafson's Law

```cpp
double gustafson_speedup(double parallel_fraction, int num_threads) {
    return num_threads - (1.0 - parallel_fraction) * (num_threads - 1);
}

void gustafson_analysis() {
    std::cout << "\n=== Gustafson's Law ===\n";
    std::cout << "P=90%, N=64: " << gustafson_speedup(0.90, 64) << "x\n";
    std::cout << "P=95%, N=64: " << gustafson_speedup(0.95, 64) << "x\n";
    std::cout << "P=99%, N=64: " << gustafson_speedup(0.99, 64) << "x\n";
}
```

---

## 3. Profiling com perf

### 3.1 Setup e Comandos

```bash
# Compilar com símbolos
g++ -O2 -g -pthread code.cpp -o code

# CPU profiling
perf record -g ./code
perf report

# Métricas de cache
perf stat -e cycles,instructions,cache-references,cache-misses \
    -e LLC-loads,LLC-load-misses,branch-misses ./code

# Lock contention
perf lock record ./code
perf lock report

# Scheduling analysis
perf sched record ./code
perf sched latency
perf sched map
```

### 3.2 Interpretação de Resultados

```
// Métricas importantes:
// IPC (Instructions Per Cycle) = instructions / cycles
// > 1.0 = good (superescalar)
// < 0.5 = problemas de memory stalls ou branch misses

// Cache miss rates:
// L1 miss rate < 5% = good
// LLC miss rate < 1% = good
// LLC miss rate > 10% = problema de localidade

// Branch prediction:
// branch-misses < 5% = good
// > 10% = code layout issues

// Lock contention indicators:
// high cycles-per-lock-acquire
// high context switches
// high wait time in futex
```

### 3.3 Flame Graphs

```bash
# Gerar flamegraph
perf record -g ./code
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Procurar por:
# - Large blocks = hot functions
# - Wide stacks = deep call chains
# - Deep stacks = recursion or complex call patterns
```

---

## 4. NUMA Optimization

### 4.1 NUMA Topology

```cpp
#include <thread>
#include <vector>
#include <iostream>
#include <numa.h>
#include <sched.h>

class NumaTopology {
    int num_nodes_;
    std::vector<int> cpus_per_node_;
    
public:
    NumaTopology() {
        if (numa_available() < 0) {
            num_nodes_ = 1;
            cpus_per_node_.push_back(std::thread::hardware_concurrency());
            return;
        }
        
        num_nodes_ = numa_max_node() + 1;
        cpus_per_node_.resize(num_nodes_);
        
        for (int node = 0; node < num_nodes_; ++node) {
            struct bitmask* cpumask = numa_allocate_cpumask();
            numa_node_to_cpus(node, cpumask);
            
            int count = 0;
            for (int cpu = 0; cpu < numa_num_configured_cpus(); ++cpu) {
                if (numa_bitmask_isbitset(cpumask, cpu)) count++;
            }
            cpus_per_node_[node] = count;
            numa_free_cpumask(cpumask);
        }
    }
    
    void print() const {
        std::cout << "NUMA Topology: " << num_nodes_ << " nodes\n";
        for (int i = 0; i < num_nodes_; ++i) {
            std::cout << "  Node " << i << ": " << cpus_per_node_[i] << " CPUs\n";
        }
    }
    
    int num_nodes() const { return num_nodes_; }
    int cpus_on_node(int node) const { return cpus_per_node_[node]; }
};

void numa_aware_thread_placement() {
    NumaTopology topo;
    topo.print();
    
    int num_threads = std::thread::hardware_concurrency();
    std::vector<std::thread> threads;
    
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([t] {
            cpu_set_t cpuset;
            CPU_ZERO(&cpuset);
            CPU_SET(t, &cpuset);
            sched_setaffinity(0, sizeof(cpuset), &cpuset);
            
            volatile int x = 0;
            for (int i = 0; i < 1000000; ++i) x += i;
        });
    }
    
    for (auto& t : threads) t.join();
}

int main() {
    numa_aware_thread_placement();
    return 0;
}
```

---

## 5. Reducing Lock Contention

### 5.1 Lock Striping

```cpp
#include <mutex>
#include <vector>
#include <thread>
#include <iostream>
#include <shared_mutex>
#include <array>
#include <unordered_map>
#include <functional>
#include <optional>

template<typename K, typename V, size_t NUM_STRIPES = 16>
class StripedMap {
    struct Bucket {
        std::shared_mutex mutex;
        std::unordered_map<K, V> data;
    };
    
    std::array<Bucket, NUM_STRIPES> stripes_;
    
    size_t get_stripe(const K& key) const {
        return std::hash<K>{}(key) % NUM_STRIPES;
    }
    
public:
    void put(const K& key, const V& value) {
        auto& bucket = stripes_[get_stripe(key)];
        std::unique_lock lock(bucket.mutex);
        bucket.data[key] = value;
    }
    
    std::optional<V> get(const K& key) const {
        auto& bucket = stripes_[get_stripe(key)];
        std::shared_lock lock(bucket.mutex);
        auto it = bucket.data.find(key);
        if (it != bucket.data.end()) return it->second;
        return std::nullopt;
    }
    
    bool remove(const K& key) {
        auto& bucket = stripes_[get_stripe(key)];
        std::unique_lock lock(bucket.mutex);
        return bucket.data.erase(key) > 0;
    }
};

void benchmark_lock_contention() {
    constexpr int NUM_THREADS = 8;
    constexpr int OPS_PER_THREAD = 100'000;
    
    // Single lock
    {
        std::shared_mutex mutex;
        std::unordered_map<int, int> map;
        
        auto start = std::chrono::high_resolution_clock::now();
        std::vector<std::thread> threads;
        
        for (int t = 0; t < NUM_THREADS; ++t) {
            threads.emplace_back([&] {
                for (int i = 0; i < OPS_PER_THREAD; ++i) {
                    if (i % 2 == 0) {
                        std::unique_lock lock(mutex);
                        map[i] = i;
                    } else {
                        std::shared_lock lock(mutex);
                        map.find(i);
                    }
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << "Single lock: " << ms << "ms\n";
    }
    
    // Striped locks
    {
        StripedMap<int, int, 16> map;
        
        auto start = std::chrono::high_resolution_clock::now();
        std::vector<std::thread> threads;
        
        for (int t = 0; t < NUM_THREADS; ++t) {
            threads.emplace_back([&] {
                for (int i = 0; i < OPS_PER_THREAD; ++i) {
                    if (i % 2 == 0) map.put(i, i);
                    else map.get(i);
                }
            });
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        std::cout << "Striped locks: " << ms << "ms\n";
    }
}

int main() {
    benchmark_lock_contention();
    return 0;
}
```

---

## 6. Memory Bandwidth Analysis

```cpp
#include <vector>
#include <thread>
#include <chrono>
#include <iostream>

void memory_bandwidth_test() {
    const size_t SIZE = 100 * 1024 * 1024 / sizeof(double);
    std::vector<double> data(SIZE, 1.0);
    
    auto start = std::chrono::high_resolution_clock::now();
    double sum = 0;
    for (size_t i = 0; i < SIZE; ++i) sum += data[i];
    auto end = std::chrono::high_resolution_clock::now();
    auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    double bandwidth = (SIZE * sizeof(double)) / static_cast<double>(ns);
    
    std::cout << "Single-thread read bandwidth: " << bandwidth << " GB/s\n";
    
    int num_threads = 4;
    start = std::chrono::high_resolution_clock::now();
    std::vector<std::thread> threads;
    
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&data, t, num_threads] {
            size_t chunk = data.size() / num_threads;
            size_t start_idx = t * chunk;
            size_t end_idx = (t == num_threads - 1) ? data.size() : start_idx + chunk;
            double local_sum = 0;
            for (size_t i = start_idx; i < end_idx; ++i) local_sum += data[i];
            volatile double sink = local_sum;
            (void)sink;
        });
    }
    for (auto& t : threads) t.join();
    
    end = std::chrono::high_resolution_clock::now();
    ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    bandwidth = (SIZE * sizeof(double) * num_threads) / static_cast<double>(ns);
    
    std::cout << "Multi-thread read bandwidth (" << num_threads << " threads): "
              << bandwidth << " GB/s\n";
}

int main() {
    memory_bandwidth_test();
    return 0;
}
```

---

## 7. Referências

- **Amdahl, G.** — "Validity of the Single Processor Approach" (1967)
- **Gustafson, J.** — "Reevaluating Amdahl's Law" (1988)
- **Hennessy & Patterson** — Computer Architecture: A Quantitative Approach
- **Brendan Gregg** — Systems Performance (Pearson)
- **Intel VTune** — software.intel.com/vtune
- **perf** — perf.wiki.kernel.org
- **numactl** — man numactl
- **likwid** — github.com/RRZE-HPC/likwid
---

*[Capítulo anterior: 13 — Debugging Concorrencia](13-debugging-concorrencia.md)*
*[Próximo capítulo: 15 — Padroes Concorrencia](15-padroes-concorrencia.md)*
