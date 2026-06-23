# Capítulo 6 — Paralelismo com std::execution e Algoritmos Paralelos

## Objetivos de Aprendizado

1. Utilizar std::execution::par e par_unseq para paralelizar algoritmos padrão
2. Compreender os requisitos de segurança para execução paralela
3. Integrar OpenMP e Intel TBB em projetos C++
4. Implementar padrões de paralelismo seguros: map-reduce, divide-and-conquer
5. Medir e comparar performance entre sequential, parallel e parallel+vectorized

---

## 1. C++17 Parallel Algorithms

### 1.1 Execution Policies

```cpp
#include <algorithm>
#include <execution>
#include <vector>
#include <numeric>
#include <iostream>
#include <chrono>

int main() {
    const size_t N = 10'000'000;
    std::vector<double> data(N);
    std::iota(data.begin(), data.end(), 1.0);
    
    // Sequential
    auto start = std::chrono::high_resolution_clock::now();
    std::sort(data.begin(), data.end(), std::greater<double>());
    auto end = std::chrono::high_resolution_clock::now();
    std::cout << "sort seq: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    // Parallel
    std::iota(data.begin(), data.end(), 1.0);
    start = std::chrono::high_resolution_clock::now();
    std::sort(std::execution::par, data.begin(), data.end(), std::greater<double>());
    end = std::chrono::high_resolution_clock::now();
    std::cout << "sort par: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    // Parallel + Unsequenced
    std::iota(data.begin(), data.end(), 1.0);
    start = std::chrono::high_resolution_clock::now();
    std::sort(std::execution::par_unseq, data.begin(), data.end(), std::greater<double>());
    end = std::chrono::high_resolution_clock::now();
    std::cout << "sort par_unseq: " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count() << "ms\n";
    
    return 0;
}
```

### 1.2 Requisitos de Segurança

```cpp
#include <execution>
#include <vector>
#include <iostream>

// ANTI-PADRÃO: data race em par_unseq
void dangerous() {
    std::vector<int> v(1000, 0);
    int counter = 0;
    // RACE CONDITION!
    std::for_each(std::execution::par_unseq, v.begin(), v.end(), [&counter](int& x) {
        x = counter++;
    });
}

// CORRETO: função pura, sem efeitos colaterais
float safe_transform(float x) {
    return std::sin(x) * std::cos(x) + 1.0f;
}

// CORRETO: usar atomic para contadores
void safe_counter() {
    std::vector<int> v(1000, 0);
    std::atomic<int> counter{0};
    std::for_each(std::execution::par_unseq, v.begin(), v.end(), [&counter](int& x) {
        x = counter.fetch_add(1, std::memory_order_relaxed);
    });
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
#include <chrono>

void parallel_algorithms_demo() {
    const size_t N = 1'000'000;
    std::vector<int> v(N);
    std::iota(v.begin(), v.end(), 1);
    
    // std::for_each — parallel element processing
    std::for_each(std::execution::par, v.begin(), v.end(), [](int& x) {
        x = x * x + x;
    });
    
    // std::reduce — parallel reduction
    long long sum = std::reduce(std::execution::par, v.begin(), v.end(), 0LL);
    std::cout << "Sum: " << sum << "\n";
    
    // std::transform — parallel transform
    std::vector<double> result(N);
    std::transform(std::execution::par, v.begin(), v.end(), result.begin(),
                   [](int x) { return std::sqrt(static_cast<double>(x)); });
    
    // std::inclusive_scan — parallel prefix sum
    std::vector<long long> scanned(N);
    std::inclusive_scan(std::execution::par, v.begin(), v.end(), scanned.begin());
    
    // std::count_if — parallel counting
    auto evens = std::count_if(std::execution::par, v.begin(), v.end(),
                                [](int x) { return x % 2 == 0; });
    std::cout << "Even count: " << evens << "\n";
    
    // std::find — parallel search
    auto it = std::find(std::execution::par, v.begin(), v.end(), 500'000);
    if (it != v.end()) std::cout << "Found at: " << std::distance(v.begin(), it) << "\n";
    
    // std::copy_if — parallel filtering
    std::vector<int> filtered;
    std::copy_if(std::execution::par, v.begin(), v.end(), std::back_inserter(filtered),
                 [](int x) { return x > 500'000 && x < 500'100; });
    std::cout << "Filtered: " << filtered.size() << " elements\n";
}

int main() {
    parallel_algorithms_demo();
    return 0;
}
```

---

## 3. OpenMP Integração

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
    
    double sum = 0;
    #pragma omp parallel for reduction(+:sum)
    for (int i = 0; i < N; ++i) {
        sum += std::sin(data[i]);
    }
    
    std::cout << "OpenMP sum: " << sum << "\n";
    
    // Parallel sections
    #pragma omp parallel sections
    {
        #pragma omp section
        { std::cout << "Section 1: " << omp_get_thread_num() << "\n"; }
        #pragma omp section
        { std::cout << "Section 2: " << omp_get_thread_num() << "\n"; }
    }
}

int main() {
    openmp_example();
    return 0;
}
```

---

## 4. Intel TBB

```cpp
#include <tbb/parallel_for.h>
#include <tbb/parallel_reduce.h>
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
            double local = init;
            for (size_t i = r.begin(); i < r.end(); ++i) local += data[i];
            return local;
        },
        std::plus<double>()
    );
    
    std::cout << "TBB sum: " << sum << "\n";
}

int main() {
    tbb_example();
    return 0;
}
```

---

## 5. Padrões de Paralelismo Seguro

### 5.1 Map-Reduce

```cpp
#include <thread>
#include <vector>
#include <numeric>
#include <mutex>
#include <iostream>

template<typename MapFn, typename ReduceFn>
auto map_reduce(const std::vector<int>& input, MapFn map_fn, ReduceFn reduce_fn, 
                decltype(map_fn(input[0])) initial) {
    auto result = initial;
    std::mutex result_mutex;
    
    std::vector<std::thread> threads;
    size_t num_threads = std::thread::hardware_concurrency();
    size_t chunk = (input.size() + num_threads - 1) / num_threads;
    
    for (size_t t = 0; t < num_threads; ++t) {
        size_t start = t * chunk;
        size_t end = std::min(start + chunk, input.size());
        if (start >= input.size()) break;
        
        threads.emplace_back([&] {
            auto local = map_fn(input[start]);
            for (size_t i = start + 1; i < end; ++i) {
                local = reduce_fn(local, map_fn(input[i]));
            }
            std::lock_guard lock(result_mutex);
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
        [](int x) { return static_cast<long long>(x) * x; },
        [](long long a, long long b) { return a + b; },
        0LL);
    
    std::cout << "Sum of squares: " << sum << "\n";
    return 0;
}
```

### 5.2 Divide and Conquer

```cpp
#include <thread>
#include <vector>
#include <algorithm>
#include <numeric>
#include <iostream>
#include <future>

void parallel_sort(std::vector<int>& data, int depth = 0) {
    if (data.size() <= 1000 || depth >= 4) {
        std::sort(data.begin(), data.end());
        return;
    }
    
    auto mid = data.begin() + data.size() / 2;
    std::vector<int> left(data.begin(), mid);
    std::vector<int> right(mid, data.end());
    
    auto left_future = std::async(std::launch::async, parallel_sort, std::ref(left), depth + 1);
    parallel_sort(right, depth + 1);
    left_future.get();
    
    std::merge(left.begin(), left.end(), right.begin(), right.end(), data.begin());
}

int main() {
    std::vector<int> data(1'000'000);
    std::iota(data.begin(), data.end(), 0);
    std::reverse(data.begin(), data.end());
    
    parallel_sort(data);
    
    bool sorted = std::is_sorted(data.begin(), data.end());
    std::cout << "Sorted: " << (sorted ? "yes" : "NO") << "\n";
    return 0;
}
```

---

## 6. Referências

- **C++17 Standard** — §28.3 (Execution policies)
- **C++20 Standard** — §28.6 (Parallel algorithms)
- **Intel TBB** — oneapi-src/oneTBB
- **OpenMP 5.2** — openmp.org
- **McCaffrey** — Practical Parallel Programming with OpenMP
---

*[Capítulo anterior: 05 — Thread Pools Tarefas Assincronas](05-thread-pools-tarefas-assincronas.md)*
*[Próximo capítulo: 07 — False Sharing E Otimizacao Cache](07-false-sharing-e-otimizacao-cache.md)*
