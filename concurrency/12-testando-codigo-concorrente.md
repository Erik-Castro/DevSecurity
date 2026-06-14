# Capítulo 12 — Testando Código Concorrente

## Objetivos de Aprendizado

1. Utilizar ThreadSanitizer (TSan) para detecção de data races
2. Aplicar stress testing para descobrir bugs intermitentes
3. Implementar model checking para verificação de atomics
4. Criar testes determinísticos para código concorrente

---

## 1. ThreadSanitizer (TSan)

```bash
# Compilação
g++ -std=c++20 -fsanitize=thread -g -O1 -pthread code.cpp -o code_tsan

# Execução
TSAN_OPTIONS="halt_on_error=1 history_size=7 log_path=tsan_report" ./code_tsan

# Suppress known issues
TSAN_OPTIONS="suppressions=tsan_suppressions.txt" ./code_tsan
```

### 1.1 Exemplo de Deteção

```cpp
#include <thread>
#include <atomic>
#include <iostream>

// TSAN detectará data race aqui
void data_race_example() {
    int shared_data = 0;  // NÃO é atômico!
    std::atomic<bool> ready{false};
    
    std::thread writer([&] {
        shared_data = 42;  // Data race: write
        ready.store(true, std::memory_order_release);
    });
    
    std::thread reader([&] {
        while (!ready.load(std::memory_order_acquire)) {}
        std::cout << shared_data << "\n";  // Data race: read
    });
    
    writer.join();
    reader.join();
}

// CORRETO: usar atomic
void no_data_race() {
    std::atomic<int> shared_data{0};
    std::atomic<bool> ready{false};
    
    std::thread writer([&] {
        shared_data.store(42, std::memory_order_release);
        ready.store(true, std::memory_order_release);
    });
    
    std::thread reader([&] {
        while (!ready.load(std::memory_order_acquire)) {}
        std::cout << shared_data.load(std::memory_order_acquire) << "\n";
    });
    
    writer.join();
    reader.join();
}
```

---

## 2. Stress Testing

```cpp
#include <thread>
#include <vector>
#include <atomic>
#include <iostream>
#include <functional>
#include <random>

template<typename Func>
void stress_test(Func test_func, int num_threads = 8, int iterations = 10000) {
    std::atomic<int> failures{0};
    
    for (int iter = 0; iter < iterations; ++iter) {
        std::vector<std::thread> threads;
        
        for (int i = 0; i < num_threads; ++i) {
            threads.emplace_back([&test_func, &failures] {
                if (!test_func()) {
                    failures.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }
        
        for (auto& t : threads) t.join();
        
        if (failures.load() > 0) {
            std::cout << "Found " << failures.load() << " failures in iteration " << iter << "\n";
            return;
        }
    }
    
    std::cout << "No failures found in " << iterations << " iterations\n";
}

// Exemplo: testar uma fila thread-safe
template<typename T>
class ThreadSafeQueue {
    std::queue<T> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    
public:
    void push(T value) {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(value));
        cv_.notify_one();
    }
    
    bool try_pop(T& value) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (queue_.empty()) return false;
        value = std::move(queue_.front());
        queue_.pop();
        return true;
    }
};

int main() {
    ThreadSafeQueue<int> queue;
    
    stress_test([&queue]() -> bool {
        // Producer-consumer stress test
        std::vector<std::thread> threads;
        
        // 4 producers
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&queue, i] {
                for (int j = 0; j < 100; ++j) {
                    queue.push(i * 100 + j);
                }
            });
        }
        
        // 4 consumers
        std::atomic<int> consumed{0};
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&queue, &consumed] {
                int val;
                for (int j = 0; j < 100; ++j) {
                    while (!queue.try_pop(val)) {
                        std::this_thread::yield();
                    }
                    consumed.fetch_add(1, std::memory_order_relaxed);
                }
            });
        }
        
        for (auto& t : threads) t.join();
        
        // Verify all items consumed
        return consumed.load() == 400;
    });
    
    return 0;
}
```

---

## 3. Model Checking

```cpp
// CDSChecker example (simplified)
// Compile with: g++ -std=c++20 -DCDSCHECKER code.cpp -o code

#ifdef CDSCHECKER
#include <cdschecker.h>
#endif

void atomic_example() {
    std::atomic<int> x{0};
    std::atomic<int> y{0};
    std::atomic<bool> flag{false};
    
    std::thread writer([&] {
        x.store(1, std::memory_order_relaxed);
        y.store(1, std::memory_order_release);
        flag.store(true, std::memory_order_release);
    });
    
    std::thread reader([&] {
        while (!flag.load(std::memory_order_acquire)) {}
        int x_val = x.load(std::memory_order_relaxed);
        int y_val = y.load(std::memory_order_acquire);
        // CDSChecker verifica se y_val==1 implica x_val==1
        (void)x_val;
        (void)y_val;
    });
    
    writer.join();
    reader.join();
}
```

---

## 4. Deterministic Replay

```cpp
// rr (record and replay) debugging
// Record: rr record ./program
// Replay: rr replay

// Para testes determinísticos, seed RNG por thread ID
#include <random>
#include <thread>

thread_local std::mt19937 rng;

void seeded_thread(int seed) {
    rng.seed(seed);  // Deterministic seed per thread
    // Now operations are reproducible
}

int main() {
    std::thread t1(seeded_thread, 42);
    std::thread t2(seeded_thread, 123);
    t1.join();
    t2.join();
    return 0;
}
```

---

## 5. Referências

- **ThreadSanitizer** — clang.llvm.org/docs/ThreadSanitizer.html
- **CDSChecker** — github.com/ucecserc/CDSChecker
- **Nidhugg** — github.com/nidhugg/nidhugg
- **rr** — rr-project.org
- **Google Sanitizers** — github.com/google/sanitizers
