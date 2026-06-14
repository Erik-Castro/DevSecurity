# Capítulo 6 — Paralelismo com std::execution e Algoritmos Paralelos

## Objetivos de Aprendizado

1. Utilizar std::execution::par e par_unseq para paralelizar algoritmos padrão
2. Compreender os requisitos de segurança para execução paralela
3. Integrar OpenMP e Intel TBB em projetos C++
4. Implementar padrões de paralelismo seguros: map-reduce, divide-and-conquer

---

## 1. C++17 Parallel Algorithms

```cpp
#include <algorithm>
#include <execution>
#include <vector>
#include <numeric>
#include <iostream>
#include <chrono>

int main() {
    std::vector<double> data(10'000'000);
    std::iota(data.begin(), data.end(), 1.0);
    
    // Sequential
    auto start = std::chrono::high_resolution_clock::now();
    std::sort(data.begin(), data.end(), std::greater<double>());
    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "sort seq: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    std::iota(data.begin(), data.end(), 1.0);
    
    // Parallel
    start = std::chrono::high_resolution_clock::now();
    std::sort(std::execution::par, data.begin(), data.end(), std::greater<double>());
    end = std::chrono::high_resolution_clock::now();
    std::cout << "sort par: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    // Parallel + Unsequenced (allows vectorization)
    std::iota(data.begin(), data.end(), 1.0);
    start = std::chrono::high_resolution_clock::now();
    std::sort(std::execution::par_unseq, data.begin(), data.end(), std::greater<double>());
    end = std::chrono::high_resolution_clock::now();
    std::cout << "sort par_unseq: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    return 0;
}
```

---

## 2. Algoritmos Paralelos Comuns

```cpp
#include <algorithm>
#include <execution>
#include <numeric>
#include <vector>
#include <iostream>
#include <functional>

void parallel_algorithms_demo() {
    std::vector<int> v(1'000'000);
    std::iota(v.begin(), v.end(), 1);
    
    // std::for_each — parallel element processing
    std::for_each(std::execution::par, v.begin(), v.end(), [](int& x) {
        x = x * x + x;
    });
    
    // std::reduce — parallel reduction (C++17)
    long long sum = std::reduce(std::execution::par, v.begin(), v.end(), 0LL);
    std::cout << "Sum: " << sum << "\n";
    
    // std::transform — parallel transform
    std::vector<double> result(v.size());
    std::transform(std::execution::par, v.begin(), v.end(), result.begin(),
                   [](int x) { return std::sqrt(static_cast<double>(x)); });
    
    // std::inclusive_scan — parallel prefix sum
    std::vector<long long> scanned(v.size());
    std::inclusive_scan(std::execution::par, v.begin(), v.end(), scanned.begin());
    
    // std::count_if — parallel counting
    auto evens = std::count_if(std::execution::par, v.begin(), v.end(),
                                [](int x) { return x % 2 == 0; });
    std::cout << "Even count: " << evens << "\n";
    
    // std::find — parallel search
    auto it = std::find(std::execution::par, v.begin(), v.end(), 500'000);
    if (it != v.end()) std::cout << "Found at index: " << std::distance(v.begin(), it) << "\n";
    
    // std::copy_if — parallel filtering
    std::vector<int> filtered;
    std::copy_if(std::execution::par, v.begin(), v.end(), std::back_inserter(filtered),
                 [](int x) { return x > 500'000 && x < 500'100; });
    std::cout << "Filtered: " << filtered.size() << " elements\n";
}
```

---

## 3. Requisitos de Segurança

```cpp
#include <algorithm>
#include <execution>
#include <atomic>
#include <vector>
#include <iostream>

// ANTI-PADRÃO: data race em par_unseq
void dangerous_parallel() {
    std::vector<int> v(1000, 0);
    int counter = 0;  // NÃO thread-safe!
    
    // RACE CONDITION!
    std::for_each(std::execution::par_unseq, v.begin(), v.end(), [&counter](int& x) {
        x = counter++;  // Data race!
    });
}

// CORRETO: usar atomic ou accumulator separado
void safe_parallel() {
    std::vector<int> v(1000, 0);
    std::atomic<int> counter{0};
    
    std::for_each(std::execution::par_unseq, v.begin(), v.end(), [&counter](int& x) {
        x = counter.fetch_add(1, std::memory_order_relaxed);
    });
    
    // Melhor ainda: cada thread processa seu range sem compartilhamento
    std::for_each(std::execution::par_unseq, v.begin(), v.end(), [](int& x) {
        x = &x - &(*v.begin());  // Calculate index without sharing
    });
}

// CORRETO: função pura sem efeitos colaterais
float pure_function(float x) {
    return std::sin(x) * std::cos(x) + 1.0f;
}

// ANTI-PADRÃO: efeito colateral em par_unseq
std::atomic<int> bad_counter{0};
float bad_function(float x) {
    return x + bad_counter.fetch_add(1);  // Serializes execution!
}
```

---

## 4. Execution Policies em Detalhes

| Policy | Parallelism | Vectorization | Reentrant | Thread-safe |
|--------|-------------|---------------|-----------|-------------|
| `seq` | No | No | No | N/A |
| `par` | Yes | No | Yes | Required |
| `par_unseq` | Yes | Yes | Yes | Required |

---

## 5. OpenMP Integração

```cpp
#include <vector>
#include <numeric>
#include <iostream>
#include <cmath>

// Compile: g++ -fopenmp -O2 example.cpp -o example
void openmp_example() {
    const int N = 10'000'000;
    std::vector<double> data(N);
    std::iota(data.begin(), data.end(), 1.0);
    
    // Parallel for with OpenMP
    #pragma omp parallel for reduction(+:sum)
    double sum = 0;
    for (int i = 0; i < N; ++i) {
        sum += std::sin(data[i]);
    }
    
    std::cout << "OpenMP sum: " << sum << "\n";
    
    // Parallel sections
    #pragma omp parallel sections
    {
        #pragma omp section
        { /* Task 1 */ }
        #pragma omp section
        { /* Task 2 */ }
    }
    
    // Thread affinity
    #pragma omp parallel
    {
        #pragma omp single
        std::cout << "Threads: " << omp_get_num_threads() << "\n";
    }
}
```

---

## 6. Intel TBB Parallel Algorithms

```cpp
// Compile: g++ -ltbb -O2 example.cpp -o example
#include <tbb/parallel_for.h>
#include <tbb/parallel_reduce.h>
#include <tbb/parallel_sort.h>
#include <vector>
#include <numeric>
#include <iostream>

void tbb_example() {
    std::vector<double> data(10'000'000);
    std::iota(data.begin(), data.end(), 1.0);
    
    // parallel_for
    tbb::parallel_for(size_t(0), data.size(), [&data](size_t i) {
        data[i] = std::sin(data[i]) * data[i];
    });
    
    // parallel_reduce
    double sum = tbb::parallel_reduce(
        tbb::blocked_range<size_t>(0, data.size()),
        0.0,
        [&](const tbb::blocked_range<size_t>& r, double init) {
            double local_sum = init;
            for (size_t i = r.begin(); i < r.end(); ++i) {
                local_sum += data[i];
            }
            return local_sum;
        },
        std::plus<double>()
    );
    
    std::cout << "TBB sum: " << sum << "\n";
    
    // parallel_sort
    tbb::parallel_sort(data.begin(), data.end(), std::greater<double>());
}
```

---

## 7. Padrões de Paralelismo Seguro

### Map-Reduce

```cpp
#include <vector>
#include <thread>
#include <numeric>
#include <iostream>
#include <algorithm>

template<typename MapFunc, typename ReduceFunc>
auto map_reduce(const std::vector<int>& input, MapFunc map_fn, ReduceFunc reduce_fn, 
                decltype(map_fn(input[0])) initial) {
    auto result = initial;
    
    std::vector<std::thread> threads;
    std::mutex result_mutex;
    size_t num_threads = std::thread::hardware_concurrency();
    size_t chunk = (input.size() + num_threads - 1) / num_threads;
    
    for (size_t t = 0; t < num_threads; ++t) {
        size_t start = t * chunk;
        size_t end = std::min(start + chunk, input.size());
        
        threads.emplace_back([&input, &result, &result_mutex, map_fn, reduce_fn, start, end] {
            auto local = map_fn(input[start]);
            for (size_t i = start + 1; i < end; ++i) {
                local = reduce_fn(local, map_fn(input[i]));
            }
            std::lock_guard<std::mutex> lock(result_mutex);
            result = reduce_fn(result, local);
        });
    }
    
    for (auto& t : threads) t.join();
    return result;
}

int main() {
    std::vector<int> data(1'000'000);
    std::iota(data.begin(), data.end(), 1);
    
    auto sum = map_reduce(data,
        [](int x) { return static_cast<long long>(x) * x; },  // Map: square
        [](long long a, long long b) { return a + b; },        // Reduce: sum
        0LL);
    
    std::cout << "Sum of squares: " << sum << "\n";
    return 0;
}
```

---

## 8. Referências

- **C++17 Standard** — §28.3 (Execution policies)
- **C++20 Standard** — §28.6 (Parallel algorithms)
- **ISO/IEC 14882:2020** — §28.3.2 (execution policy)
- **Intel TBB** — oneapi-src/oneTBB documentation
- **OpenMP 5.2** — openmp.org
- **McCaffrey** — "Practical Parallel Programming with OpenMP"
