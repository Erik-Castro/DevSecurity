# Capítulo 11 — Primitivas de Sincronização Avançadas (C++20)

## Objetivos de Aprendizado

1. Utilizar std::latch para sincronização one-shot entre threads
2. Implementar barreiras reutilizáveis com std::barrier
3. Controlar concorrência com std::counting_semaphore e std::binary_semaphore
4. Implementar cooperative cancellation com std::stop_token e std::jthread
5. Comparar primitivas C++20 com soluções prévias e identificar casos de uso ideais

---

## 1. std::latch — Sincronização One-Shot

### 1.1 Conceito e Uso Básico

```cpp
#include <latch>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>
#include <string>

class ParallelInitializer {
    std::vector<std::string> data_;
    std::latch ready_latch_;
    std::latch done_latch_;
    
public:
    explicit ParallelInitializer(size_t num_threads)
        : ready_latch_(1), done_latch_(num_threads) {}
    
    void initialize(size_t total_items) {
        data_.resize(total_items);
        
        std::vector<std::thread> threads;
        size_t chunk = total_items / 4;
        
        for (int i = 0; i < 4; ++i) {
            size_t start = i * chunk;
            size_t end = (i == 3) ? total_items : start + chunk;
            
            threads.emplace_back([this, start, end, i] {
                ready_latch_.wait();
                
                for (size_t j = start; j < end; ++j) {
                    data_[j] = "item_" + std::to_string(j);
                }
                
                done_latch_.count_down();
            });
        }
        
        std::cout << "Initializing " << total_items << " items...\n";
        ready_latch_.count_down();
        
        done_latch_.wait();
        std::cout << "Initialization complete. First item: " << data_[0] << "\n";
        
        for (auto& t : threads) t.join();
    }
};

int main() {
    ParallelInitializer init(4);
    init.initialize(1000);
    return 0;
}
```

### 1.2 Padrões de Uso

```cpp
#include <latch>
#include <thread>
#include <vector>
#include <iostream>

// Padrão 1: Barrier one-shot para fase de computação
void computation_phase() {
    constexpr int N = 8;
    std::latch phase_complete(N);
    std::vector<int> results(N, 0);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < N; ++i) {
        threads.emplace_back([&phase_complete, &results, i] {
            results[i] = i * i;
            phase_complete.count_down();
        });
    }
    
    phase_complete.wait();
    
    int total = 0;
    for (int r : results) total += r;
    std::cout << "Phase 1 total: " << total << "\n";
    
    for (auto& t : threads) t.join();
}

// Padrão 2: Multiphasas com latches diferentes
void multi_phase() {
    constexpr int N = 4;
    std::latch phase1(N), phase2(N);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < N; ++i) {
        threads.emplace_back([&phase1, &phase2, i] {
            std::cout << "Thread " << i << " phase 1\n";
            phase1.count_down();
            phase1.wait();
            
            std::cout << "Thread " << i << " phase 2\n";
            phase2.count_down();
        });
    }
    
    for (auto& t : threads) t.join();
}

int main() {
    computation_phase();
    multi_phase();
    return 0;
}
```

---

## 2. std::barrier — Sincronização Reutilizável

### 2.1 Conceito e Uso

```cpp
#include <barrier>
#include <thread>
#include <vector>
#include <iostream>
#include <cmath>

void iterative_solver() {
    constexpr int NUM_THREADS = 4;
    constexpr int MAX_ITERATIONS = 100;
    constexpr double TOLERANCE = 1e-6;
    
    std::vector<double> data(1000, 1.0);
    std::atomic<bool> converged{false};
    std::atomic<int> iteration{0};
    
    auto on_completion = [&]() noexcept {
        iteration.fetch_add(1, std::memory_order_relaxed);
    };
    
    std::barrier sync_point(NUM_THREADS, on_completion);
    
    std::vector<std::thread> threads;
    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([&] {
            size_t chunk = data.size() / NUM_THREADS;
            size_t start = t * chunk;
            size_t end = (t == NUM_THREADS - 1) ? data.size() : start + chunk;
            
            while (!converged.load(std::memory_order_acquire)) {
                for (size_t i = start; i < end; ++i) {
                    data[i] = std::sin(data[i]) * 0.9 + 0.1;
                }
                
                sync_point.arrive_and_wait();
                
                if (t == 0) {
                    double max_diff = 0;
                    for (size_t i = 1; i < data.size(); ++i) {
                        max_diff = std::max(max_diff, std::abs(data[i] - data[i-1]));
                    }
                    if (max_diff < TOLERANCE || iteration.load() >= MAX_ITERATIONS) {
                        converged.store(true, std::memory_order_release);
                    }
                }
                
                sync_point.arrive_and_wait();
            }
        });
    }
    
    for (auto& t : threads) t.join();
    std::cout << "Converged after " << iteration.load() << " iterations\n";
}

int main() {
    iterative_solver();
    return 0;
}
```

### 2.2 flex_barrier

```cpp
#include <barrier>
#include <thread>
#include <vector>
#include <iostream>

void flex_barrier_example() {
    constexpr int NUM_THREADS = 4;
    std::atomic<int> phase{0};
    
    auto completion_fn = [&phase]() noexcept {
        phase.fetch_add(1, std::memory_order_release);
    };
    
    std::barrier sync(NUM_THREADS, completion_fn);
    
    std::vector<std::thread> threads;
    for (int t = 0; t < NUM_THREADS; ++t) {
        threads.emplace_back([&sync, &phase, t] {
            for (int iter = 0; iter < 3; ++iter) {
                std::cout << "Thread " << t << " iter " << phase.load() << "\n";
                sync.arrive_and_wait();
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                sync.arrive_and_wait();
            }
        });
    }
    
    for (auto& t : threads) t.join();
}

int main() {
    flex_barrier_example();
    return 0;
}
```

---

## 3. std::counting_semaphore e std::binary_semaphore

### 3.1 Controle de Concorrência

```cpp
#include <semaphore>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>

class ConnectionPool {
    std::counting_semaphore<> sem_;
    std::vector<int> available_;
    std::mutex mutex_;
    
public:
    explicit ConnectionPool(int max_size) : sem_(max_size) {
        for (int i = 0; i < max_size; ++i) {
            available_.push_back(i);
        }
    }
    
    int acquire() {
        sem_.acquire();
        std::lock_guard<std::mutex> lock(mutex_);
        int conn = available_.back();
        available_.pop_back();
        return conn;
    }
    
    void release(int conn) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            available_.push_back(conn);
        }
        sem_.release();
    }
    
    int available_count() const {
        return sem_.available();
    }
};

void client_task(ConnectionPool& pool, int id) {
    int conn = pool.acquire();
    std::cout << "Client " << id << " acquired connection " << conn << "\n";
    
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    pool.release(conn);
    std::cout << "Client " << id << " released connection " << conn << "\n";
}

int main() {
    ConnectionPool pool(3);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 10; ++i) {
        threads.emplace_back(client_task, std::ref(pool), i);
    }
    
    for (auto& t : threads) t.join();
    return 0;
}
```

### 3.2 binary_semaphore

```cpp
#include <semaphore>
#include <thread>
#include <iostream>

std::binary_semaphore data_ready{0};
std::binary_semaphore space_available{1};
int shared_data = 0;

void producer() {
    for (int i = 0; i < 5; ++i) {
        space_available.acquire();
        shared_data = i * 10;
        std::cout << "Produced: " << shared_data << "\n";
        data_ready.release();
    }
}

void consumer() {
    for (int i = 0; i < 5; ++i) {
        data_ready.acquire();
        std::cout << "Consumed: " << shared_data << "\n";
        space_available.release();
    }
}

int main() {
    std::thread t1(producer);
    std::thread t2(consumer);
    t1.join(); t2.join();
    return 0;
}
```

---

## 4. std::stop_token e std::jthread

### 4.1 Cooperative Cancellation

```cpp
#include <thread>
#include <stop_token>
#include <iostream>
#include <chrono>

void long_running_task(std::stop_token token, int id) {
    int iterations = 0;
    
    while (!token.stop_requested()) {
        volatile int x = 0;
        for (int i = 0; i < 1000; ++i) x += i;
        
        iterations++;
        if (iterations % 100 == 0) {
            std::cout << "Thread " << id << ": " << iterations << " iterations\n";
        }
    }
    
    std::cout << "Thread " << id << " stopped after " << iterations << " iterations\n";
}

int main() {
    std::jthread t1(long_running_task, 1);
    std::jthread t2(long_running_task, 2);
    
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    std::cout << "Requesting stop...\n";
    t1.request_stop();
    t2.request_stop();
    
    return 0;
}
```

### 4.2 stop_callback

```cpp
#include <thread>
#include <stop_token>
#include <iostream>
#include <vector>

void worker_with_cleanup(std::stop_token token) {
    std::vector<int> results;
    
    std::stop_callback cleanup(token, [&results] {
        std::cout << "Cleanup: saving " << results.size() << " results\n";
    });
    
    for (int i = 0; i < 100; ++i) {
        if (token.stop_requested()) break;
        results.push_back(i * i);
    }
    
    std::cout << "Worker finished with " << results.size() << " results\n";
}

int main() {
    std::jthread worker(worker_with_cleanup);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    worker.request_stop();
    return 0;
}
```

### 4.3 Stop Token com Múltiplas Threads

```cpp
#include <thread>
#include <stop_token>
#include <iostream>
#include <vector>
#include <chrono>

void worker(std::stop_token token, int id) {
    while (!token.stop_requested()) {
        std::cout << "Worker " << id << " running\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    std::cout << "Worker " << id << " stopped\n";
}

int main() {
    std::stop_source source;
    std::stop_token token = source.get_token();
    
    std::vector<std::jthread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(worker, token, i);
    }
    
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
    source.request_stop();
    
    return 0;
}
```

---

## 5. Comparação com Soluções Prévias

| Solução | C++ Versão | Reutilizável | Cancelável | Complexidade |
|---------|-----------|--------------|------------|--------------|
| `std::condition_variable` | C++11 | Sim | Manual | Média |
| `std::atomic::wait/notify` | C++20 | Sim | Manual | Baixa |
| `std::latch` | C++20 | Não | Não | Muito Baixa |
| `std::barrier` | C++20 | Sim | Não | Média |
| `std::counting_semaphore` | C++20 | Sim | Não | Baixa |
| `std::jthread + stop_token` | C++20 | N/A | Sim | Baixa |
| `std::future::wait_for` | C++11 | Sim | Parcial | Baixa |

---

## 6. Padrões de Sincronização Avançados

### 6.1 Pipeline com Barreiras

```cpp
#include <barrier>
#include <thread>
#include <vector>
#include <iostream>
#include <functional>

class Pipeline {
    std::barrier sync_;
    std::vector<std::function<void()>> stages_;
    
public:
    explicit Pipeline(int num_stages) : sync_(num_stages) {
        stages_.resize(num_stages);
    }
    
    void set_stage(int idx, std::function<void()> fn) {
        stages_[idx] = std::move(fn);
    }
    
    void run() {
        std::vector<std::thread> threads;
        for (size_t i = 0; i < stages_.size(); ++i) {
            threads.emplace_back([this, i] {
                for (int iter = 0; iter < 5; ++iter) {
                    stages_[i]();
                    sync_.arrive_and_wait();
                }
            });
        }
        for (auto& t : threads) t.join();
    }
};

int main() {
    Pipeline pipeline(3);
    
    pipeline.set_stage(0, [] { std::cout << "Stage 1: read\n"; });
    pipeline.set_stage(1, [] { std::cout << "Stage 2: process\n"; });
    pipeline.set_stage(2, [] { std::cout << "Stage 3: write\n"; });
    
    pipeline.run();
    return 0;
}
```

---

## 7. Referências

- **C++20 Standard** — §32.14 (latch), §32.15 (barrier), §32.16 (semaphore)
- **C++20 Standard** — §33.4.5 (jthread), §33.4.6 (stop_token)
- **cppreference.com** — std::latch, std::barrier, std::counting_semaphore
- **Anthony Williams** — C++ Concurrency in Action, 2nd Ed
- **GOTW #92** — LRWF, Simple Concurrency in C++
---

*[Capítulo anterior: 10 — Coroutines Cpp20](10-coroutines-cpp20.md)*
*[Próximo capítulo: 12 — Testando Codigo Concorrente](12-testando-codigo-concorrente.md)*
