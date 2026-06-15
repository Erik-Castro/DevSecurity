# Capítulo 12 — Testando Código Concorrente

## Objetivos de Aprendizado

1. Utilizar ThreadSanitizer (TSan) para detecção de data races
2. Aplicar stress testing para descobrir bugs intermitentes
3. Implementar model checking para verificação de atomics
4. Criar testes determinísticos para código concorrente
5. Integrar testes de concorrência em pipelines CI/CD

---

## 1. ThreadSanitizer (TSan)

### 1.1 Configuração e Uso

```bash
# Compilação com TSan
g++ -std=c++20 -fsanitize=thread -g -O1 -pthread code.cpp -o code_tsan

# Opções de runtime
export TSAN_OPTIONS="
    halt_on_error=0           # Continuar após primeiro erro
    history_size=7            # Histórico de acessos por thread
    report_signal_unsafe=1    # Detectar handlers de sinal inseguros
    detect_deadlocks=1        # Detectar deadlocks
    log_path=tsan_report      # Salvar relatório em arquivo
"

# Supressões para bugs conhecidos
cat > tsan_suppressions.txt << EOF
deadlock:thread_pool.cpp
race:third_party_library
EOF

TSAN_OPTIONS="suppressions=tsan_suppressions.txt" ./code_tsan
```

### 1.2 Exemplo de Detecção

```cpp
#include <thread>
#include <vector>
#include <iostream>
#include <atomic>

// BUG: Data race em variável não atômica
class UnsafeCounter {
    int count_ = 0;  // NÃO é atômico!
    
public:
    void increment() { ++count_; }  // Data race
    int get() const { return count_; }
};

// CORRETO: Usar atomic
class SafeCounter {
    std::atomic<int> count_{0};
    
public:
    void increment() { count_.fetch_add(1, std::memory_order_relaxed); }
    int get() const { return count_.load(std::memory_order_relaxed); }
};

// BUG: Race condition em inicialização
class Singleton {
    static Singleton* instance_;
    static std::mutex mutex_;
    
public:
    static Singleton* get() {
        if (!instance_) {                    // Check 1 (sem lock)
            std::lock_guard<std::mutex> lock(mutex_);
            if (!instance_) {                // Check 2 (com lock)
                instance_ = new Singleton();  // Publicação incompleta!
            }
        }
        return instance_;
    }
};

// CORRETO: Usar std::call_once
class SafeSingleton {
    static SafeSingleton* instance_;
    static std::once_flag init_flag_;
    
public:
    static SafeSingleton* get() {
        std::call_once(init_flag_, [] {
            instance_ = new SafeSingleton();
        });
        return instance_;
    }
};

int main() {
    // Teste de UnsafeCounter (TSan detecta data race)
    {
        UnsafeCounter counter;
        std::vector<std::thread> threads;
        
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&counter] {
                for (int j = 0; j < 100000; ++j) {
                    counter.increment();
                }
            });
        }
        
        for (auto& t : threads) t.join();
        // TSan: WARNING: ThreadSanitizer: data race
    }
    
    // Teste de SafeCounter (sem data race)
    {
        SafeCounter counter;
        std::vector<std::thread> threads;
        
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&counter] {
                for (int j = 0; j < 100000; ++j) {
                    counter.increment();
                }
            });
        }
        
        for (auto& t : threads) t.join();
        std::cout << "Safe counter: " << counter.get() << "\n";
    }
    
    return 0;
}
```

### 1.3 TSAN com Mutex

```cpp
#include <thread>
#include <mutex>
#include <vector>
#include <iostream>

// BUG: Mutex não está protegendo todos os acessos
class PartiallyProtected {
    std::mutex mutex_;
    int data_ = 0;
    
public:
    void safe_increment() {
        std::lock_guard<std::mutex> lock(mutex_);
        ++data_;
    }
    
    int unsafe_get() const {
        return data_;  // Acesso sem lock!
    }
};

// CORRETO: Todos os acessos protegidos
class FullyProtected {
    mutable std::mutex mutex_;
    int data_ = 0;
    
public:
    void increment() {
        std::lock_guard<std::mutex> lock(mutex_);
        ++data_;
    }
    
    int get() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return data_;
    }
};

int main() {
    // TSan detecta race no unsafe_get
    {
        PartiallyProtected pp;
        std::vector<std::thread> threads;
        
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&pp] {
                pp.safe_increment();
                volatile int v = pp.unsafe_get();  // Race!
                (void)v;
            });
        }
        for (auto& t : threads) t.join();
    }
    
    // TSan não detecta race no FullyProtected
    {
        FullyProtected fp;
        std::vector<std::thread> threads;
        
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&fp] {
                fp.increment();
                volatile int v = fp.get();
                (void)v;
            });
        }
        for (auto& t : threads) t.join();
    }
    
    return 0;
}
```

---

## 2. Stress Testing

### 2.1 Framework de Stress Test

```cpp
#include <thread>
#include <vector>
#include <atomic>
#include <functional>
#include <random>
#include <iostream>
#include <chrono>

template<typename Func>
class StressTestRunner {
    Func test_func_;
    int num_threads_;
    int iterations_;
    std::atomic<int> failures_{0};
    std::atomic<int> total_runs_{0};
    
public:
    StressTestRunner(Func func, int threads = 8, int iterations = 1000)
        : test_func_(func), num_threads_(threads), iterations_(iterations) {}
    
    bool run() {
        auto start = std::chrono::high_resolution_clock::now();
        
        for (int iter = 0; iter < iterations_; ++iter) {
            std::vector<std::thread> threads;
            
            for (int i = 0; i < num_threads_; ++i) {
                threads.emplace_back([this] {
                    if (!test_func_()) {
                        failures_.fetch_add(1, std::memory_order_relaxed);
                    }
                });
            }
            
            for (auto& t : threads) t.join();
            total_runs_.fetch_add(1, std::memory_order_relaxed);
            
            if (failures_.load() > 0) {
                std::cout << "FAILURE at iteration " << iter << "\n";
                return false;
            }
        }
        
        auto end = std::chrono::high_resolution_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
        
        std::cout << "All " << iterations_ << " iterations passed (" << ms << "ms)\n";
        return true;
    }
    
    int failures() const { return failures_.load(); }
    int total_runs() const { return total_runs_.load(); }
};

// Exemplo: testar fila thread-safe
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
    
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }
};

int main() {
    ThreadSafeQueue<int> queue;
    
    StressTestRunner test([&queue]() -> bool {
        std::vector<std::thread> threads;
        
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back([&queue, i] {
                for (int j = 0; j < 100; ++j) {
                    queue.push(i * 100 + j);
                }
            });
        }
        
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
        return consumed.load() == 400;
    });
    
    bool passed = test.run();
    std::cout << "Result: " << (passed ? "PASSED" : "FAILED") << "\n";
    return passed ? 0 : 1;
}
```

### 2.2 Randomized Scheduling

```cpp
#include <thread>
#include <random>
#include <vector>
#include <iostream>
#include <functional>

template<typename Func>
void randomized_stress(Func test, int num_iterations = 10000) {
    std::mt19937 rng(42);
    
    for (int iter = 0; iter < num_iterations; ++iter) {
        int num_threads = std::uniform_int_distribution<>(1, 8)(rng);
        int yield_probability = std::uniform_int_distribution<>(0, 100)(rng);
        
        std::vector<std::thread> threads;
        for (int i = 0; i < num_threads; ++i) {
            threads.emplace_back([&test, yield_probability] {
                if (std::uniform_int_distribution<>(0, 100)(std::mt19937(
                    std::hash<std::thread::id>{}(std::this_thread::get_id()))) < yield_probability) {
                    std::this_thread::yield();
                }
                test();
            });
        }
        
        for (auto& t : threads) t.join();
    }
    
    std::cout << "Randomized stress test completed: " << num_iterations << " iterations\n";
}

int main() {
    std::atomic<int> counter{0};
    
    randomized_stress([&counter] {
        for (int i = 0; i < 100; ++i) {
            counter.fetch_add(1, std::memory_order_relaxed);
        }
    });
    
    std::cout << "Counter: " << counter.load() << "\n";
    return 0;
}
```

---

## 3. Model Checking

### 3.1 CDSChecker

```cpp
// CDSChecker verifica todas as interleavings possíveis
#ifdef CDSCHECKER
#include <cdschecker.h>
#endif

void atomic_example() {
    std::atomic<int> x{0}, y{0};
    
    std::thread writer([] {
        x.store(1, std::memory_order_relaxed);
        y.store(1, std::memory_order_release);
    });
    
    std::thread reader([] {
        while (y.load(std::memory_order_acquire) == 0) {}
        int xv = x.load(std::memory_order_relaxed);
        (void)xv;
    });
    
    writer.join();
    reader.join();
}
```

### 3.2 Nidhugg

```bash
# Compilar para Nidhugg
clang -DNIDHUGG -c -emit-llvm -o code.bc code.c

# Executar model checking
nidhugg code.bc

# Nidhugg verifica:
# - Data races
# - Violations de memory model
# - Deadlocks
# - ABA problems
```

---

## 4. Testes Determinísticos

### 4.1 Seed Fixa para RNG

```cpp
#include <thread>
#include <random>
#include <vector>
#include <iostream>

thread_local std::mt19937 rng;

void deterministic_test(int thread_id) {
    rng.seed(thread_id * 12345 + 67890);
    
    for (int i = 0; i < 1000; ++i) {
        int value = rng() % 100;
        if (value < 0 || value >= 100) {
            std::cout << "ERROR: invalid value " << value << "\n";
        }
    }
}

int main() {
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(deterministic_test, i);
    }
    for (auto& t : threads) t.join();
    std::cout << "Deterministic test passed\n";
    return 0;
}
```

### 4.2 Deterministic Replay com rr

```bash
# Gravar execução
rr record ./program

# Replays idênticos
rr replay
rr replay  # Mesmo resultado

# Debugar race conditions
rr replay -a  # Replay com todos os eventos
```

---

## 5. CI/CD para Testes de Concorrência

```yaml
# .github/workflows/concurrency-tests.yml
name: Concurrency Tests

on: [push, pull_request]

jobs:
  tsan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build with TSan
        run: |
          g++ -std=c++20 -fsanitize=thread -g -O1 -pthread \
            -o test_tsan test.cpp
      
      - name: Run tests with TSan
        run: |
          TSAN_OPTIONS="halt_on_error=1 history_size=7" \
            ./test_tsan
      
      - name: Build with ASan + UBSan
        run: |
          g++ -std=c++20 -fsanitize=address,undefined -g -O1 -pthread \
            -o test_asan test.cpp
      
      - name: Run tests with sanitizers
        run: ./test_asan
```

---

## 6. Métricas de Qualidade

| Métrica | Como Medir | Meta |
|---------|------------|------|
| Data race detection rate | TSan runs | 100% coverage |
| Deadlock detection rate | Static analysis + TSan | 0 false negatives |
| Stress test pass rate | Consecutive runs without failure | >10000 iterations |
| Thread safety code review | Manual + automated | All shared data covered |
| Memory leak rate | ASan/Valgrind | 0 leaks |

---

## 7. Referências

- **ThreadSanitizer** — clang.llvm.org/docs/ThreadSanitizer.html
- **Google Sanitizers** — github.com/google/sanitizers
- **CDSChecker** — github.com/ucecserc/CDSChecker
- **Nidhugg** — github.com/nidhugg/nidhugg
- **rr** — rr-project.org
