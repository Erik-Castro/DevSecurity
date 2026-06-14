# Capítulo 14 — Performance e Escalabilidade em Concorrência

## Objetivos de Aprendizado

1. Medir throughput e latência de código concorrente
2. Identificar gargalos com profiling tools
3. Aplicar Amdahl's Law para prever escalabilidade
4. Otimizar para NUMA e cache hierarchy

---

## 1. Métricas de Performance

### 1.1 Throughput vs Latência

```cpp
#include <chrono>
#include <thread>
#include <vector>
#include <atomic>
#include <iostream>
#include <numeric>

class ThroughputLatencyBenchmark {
    std::atomic<long long> total_ops_{0};
    
public:
    void worker(int ops) {
        for (int i = 0; i < ops; ++i) {
            total_ops_.fetch_add(1, std::memory_order_relaxed);
        }
    }
    
    void run(int num_threads, int ops_per_thread) {
        total_ops_.store(0);
        
        auto start = std::chrono::high_resolution_clock::now();
        
        std::vector<std::thread> threads;
        for (int i = 0; i < num_threads; ++i) {
            threads.emplace_back(&ThroughputLatencyBenchmark::worker, this, ops_per_thread);
        }
        for (auto& t : threads) t.join();
        
        auto end = std::chrono::high_resolution_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
        
        double throughput = (double)total_ops_.load() / (us / 1e6);
        double latency = (double)us / total_ops_.load();
        
        std::cout << "Threads: " << num_threads 
                  << ", Throughput: " << throughput / 1e6 << " Mops/s"
                  << ", Latency: " << latency << " ns/op\n";
    }
};

int main() {
    ThroughputLatencyBenchmark bench;
    for (int t = 1; t <= 16; t *= 2) {
        bench.run(t, 10000000);
    }
    return 0;
}
```

---

## 2. Amdahl's Law

```cpp
#include <iostream>
#include <cmath>

// Amdahl's Law: Speedup = 1 / ((1-P) + P/N)
// P = parallel fraction, N = number of processors

double amdahl_speedup(double parallel_fraction, int num_threads) {
    return 1.0 / ((1.0 - parallel_fraction) + parallel_fraction / num_threads);
}

void amdahl_analysis() {
    std::cout << "Amdahl's Law Speedup Analysis:\n";
    std::cout << "P=50%: ";
    for (int n = 1; n <= 32; n *= 2) {
        std::cout << "N=" << n << ":" << amdahl_speedup(0.5, n) << "x ";
    }
    std::cout << "\n";
    
    std::cout << "P=90%: ";
    for (int n = 1; n <= 32; n *= 2) {
        std::cout << "N=" << n << ":" << amdahl_speedup(0.9, n) << "x ";
    }
    std::cout << "\n";
    
    std::cout << "P=99%: ";
    for (int n = 1; n <= 32; n *= 2) {
        std::cout << "N=" << n << ":" << amdahl_speedup(0.99, n) << "x ";
    }
    std::cout << "\n";
}

int main() {
    amdahl_analysis();
    // Output mostra que com 99% paralelo, speedup máximo é 100x
    // Com 50% paralelo, speedup máximo é apenas 2x
    return 0;
}
```

---

## 3. Profiling com perf

```bash
# Compilar com símbolos
g++ -O2 -g -pthread code.cpp -o code

# CPU profiling
perf record -g ./code
perf report

# Métricas de cache
perf stat -e cache-references,cache-misses,LLC-loads,LLC-load-misses \
    -e cycles,instructions,branch-misses ./code

# Lock contention
perf lock record ./code
perf lock report
```

### 3.1 Exemplo de Análise

```bash
# Resultado típico:
# 5,234,567,890  cycles
# 8,123,456,789  instructions    # IPC: 1.55
#     12,345,678  cache-references
#      3,456,789  cache-misses    # 28% miss rate (alto!)
```

---

## 4. Memory Bandwidth

```cpp
#include <vector>
#include <thread>
#include <chrono>
#include <iostream>

void bandwidth_test(size_t array_size, int num_threads) {
    std::vector<double> data(array_size, 1.0);
    
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    size_t chunk = array_size / num_threads;
    
    for (int t = 0; t < num_threads; ++t) {
        size_t begin = t * chunk;
        size_t end = (t == num_threads - 1) ? array_size : begin + chunk;
        
        threads.emplace_back([&data, begin, end] {
            double sum = 0;
            for (size_t i = begin; i < end; ++i) {
                sum += data[i];
            }
            volatile double sink = sum;
            (void)sink;
        });
    }
    
    for (auto& t : threads) t.join();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    
    double gb = (double)array_size * sizeof(double) / 1e9;
    double bandwidth = gb / (us / 1e6);
    
    std::cout << "Threads: " << num_threads
              << ", Size: " << gb << "GB"
              << ", Time: " << us << "µs"
              << ", Bandwidth: " << bandwidth << " GB/s\n";
}

int main() {
    size_t size = 100 * 1024 * 1024 / sizeof(double);  // 100MB
    for (int t = 1; t <= 8; t *= 2) {
        bandwidth_test(size, t);
    }
    return 0;
}
```

---

## 5. Referências

- **Amdahl, G.** — "Validity of the Single Processor Approach" (1967)
- **Hennessy & Patterson** — Computer Architecture: A Quantitative Approach
- **Brendan Gregg** — Systems Performance (Pearson)
- **Intel VTune** — software.intel.com/vtune
- **perf** — perf.wiki.kernel.org
