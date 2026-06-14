# Capítulo 11 — Primitivas de Sincronização Avançadas (C++20)

## Objetivos de Aprendizado

1. Utilizar std::latch para sincronização one-shot entre threads
2. Implementar barreiras reutilizáveis com std::barrier
3. Controlar concorrência com std::counting_semaphore
4. Implementar cooperative cancellation com std::stop_token

---

## 1. std::latch

```cpp
#include <latch>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>

void latch_example() {
    constexpr int NUM_THREADS = 4;
    std::latch start_latch(1);   // Main signals threads to start
    std::latch done_latch(NUM_THREADS);  // Threads signal main when done
    
    std::vector<std::thread> threads;
    
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back([&start_latch, &done_latch, i] {
            start_latch.wait();  // Wait for start signal
            
            std::cout << "Thread " << i << " started\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(100 * (i + 1)));
            std::cout << "Thread " << i << " finished\n";
            
            done_latch.count_down();  // Signal completion
        });
    }
    
    std::cout << "Main: signaling threads to start\n";
    start_latch.count_down();  // Release all threads
    
    done_latch.wait();  // Wait for all threads to finish
    std::cout << "Main: all threads completed\n";
    
    for (auto& t : threads) t.join();
}
```

---

## 2. std::barrier

```cpp
#include <barrier>
#include <thread>
#include <vector>
#include <iostream>
#include <string>

void barrier_example() {
    constexpr int NUM_THREADS = 4;
    std::atomic<int> phase{0};
    
    auto completion = [&phase]() noexcept {
        phase.fetch_add(1, std::memory_order_release);
    };
    
    std::barrier sync_point(NUM_THREADS, completion);
    
    std::vector<std::thread> threads;
    
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back([&sync_point, &phase, i] {
            for (int round = 0; round < 3; ++round) {
                std::cout << "Thread " << i << " round " << phase.load() << "\n";
                
                sync_point.arrive_and_wait();  // Wait for all threads
                
                // All threads proceed together
                std::cout << "Thread " << i << " proceeding in round " << phase.load() << "\n";
            }
        });
    }
    
    for (auto& t : threads) t.join();
}
```

---

## 3. std::counting_semaphore

```cpp
#include <semaphore>
#include <thread>
#include <vector>
#include <iostream>
#include <chrono>

class ConnectionPool {
    std::counting_semaphore<> sem_;
    std::vector<int> connections_;
    
public:
    explicit ConnectionPool(int max_connections) : sem_(max_connections) {
        for (int i = 0; i < max_connections; ++i) {
            connections_.push_back(i);
        }
    }
    
    int acquire() {
        sem_.acquire();  // Blocks if no connections available
        int conn;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            conn = connections_.back();
            connections_.pop_back();
        }
        return conn;
    }
    
    void release(int conn) {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            connections_.push_back(conn);
        }
        sem_.release();
    }
    
private:
    std::mutex mutex_;
};

int main() {
    ConnectionPool pool(3);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 10; ++i) {
        threads.emplace_back([&pool, i] {
            int conn = pool.acquire();
            std::cout << "Thread " << i << " got connection " << conn << "\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            pool.release(conn);
            std::cout << "Thread " << i << " released connection " << conn << "\n";
        });
    }
    
    for (auto& t : threads) t.join();
    return 0;
}
```

---

## 4. std::stop_token (C++20)

```cpp
#include <thread>
#include <stop_token>
#include <iostream>
#include <chrono>

void long_task(std::stop_token token) {
    int i = 0;
    while (!token.stop_requested()) {
        std::cout << "Working... " << i++ << "\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
    std::cout << "Stop requested, cleaning up\n";
}

int main() {
    std::jthread worker(long_task);
    
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    
    std::cout << "Requesting stop...\n";
    worker.request_stop();  // Signal the thread to stop
    
    worker.join();  // jthread automatically joins in destructor
    std::cout << "Worker thread joined\n";
    
    return 0;
}
```

### 4.1 stop_callback

```cpp
#include <thread>
#include <stop_token>
#include <iostream>
#include <functional>

void worker_with_callback(std::stop_token token) {
    std::stop_callback cb(token, [] {
        std::cout << "Cleanup callback invoked\n";
    });
    
    // Long running work...
    std::this_thread::sleep_for(std::chrono::seconds(2));
}

int main() {
    std::jthread worker(worker_with_callback);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    worker.request_stop();
    worker.join();
    return 0;
}
```

---

## 5. Referências

- **C++20 Standard** — §32.14 (latch), §32.15 (barrier), §32.16 (semaphore)
- **C++20 Standard** — §33.4.5 (jthread), §33.4.6 (stop_token)
- **ISO/IEC 14882:2020** — Thread support library additions
- **cppreference.com** — std::latch, std::barrier, std::counting_semaphore
