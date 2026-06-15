# Capítulo 5 — Thread Pools, std::async e Execução Assíncrona

## Objetivos de Aprendizado

1. Entender por que thread pools são superiores à criação manual de threads
2. Implementar um thread pool production-ready com work stealing
3. Dominar std::async, std::future e std::shared_future
4. Aplicar padrões de execução assíncrona: fire-and-forget, continuations, when_all
5. Implementar cancellation e timeout em operações assíncronas

---

## 1. Por que Thread Pools

### 1.1 Overhead de Criação de Threads

```cpp
#include <thread>
#include <chrono>
#include <iostream>
#include <vector>

void measure_thread_creation() {
    const int N = 100;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    threads.reserve(N);
    
    for (int i = 0; i < N; ++i) {
        threads.emplace_back([]{ /* trivial work */ });
    }
    
    for (auto& t : threads) t.join();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    
    std::cout << "Created " << N << " threads in " << us << "µs\n";
    std::cout << "Average: " << us / N << "µs per thread\n";
}

int main() {
    measure_thread_creation();
    return 0;
}
```

### 1.2 Controle de Recursos

```cpp
#include <thread>
#include <atomic>
#include <iostream>

class ResourceMonitor {
    std::atomic<int> active_threads_{0};
    std::atomic<int> peak_threads_{0};
    int max_threads_;
    
public:
    explicit ResourceMonitor(int max) : max_threads_(max) {}
    
    bool try_acquire() {
        int current = active_threads_.fetch_add(1, std::memory_order_acq_rel) + 1;
        if (current > max_threads_) {
            active_threads_.fetch_sub(1, std::memory_order_release);
            return false;
        }
        
        int peak = peak_threads_.load(std::memory_order_relaxed);
        while (current > peak && !peak_threads_.compare_exchange_weak(
            peak, current, std::memory_order_relaxed)) {}
        
        return true;
    }
    
    void release() {
        active_threads_.fetch_sub(1, std::memory_order_release);
    }
    
    int active() const { return active_threads_.load(); }
    int peak() const { return peak_threads_.load(); }
};
```

---

## 2. std::async e std::future

### 2.1 launch::async vs launch::deferred

```cpp
#include <future>
#include <iostream>
#include <chrono>

int expensive_computation(int x) {
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    return x * x;
}

int main() {
    // launch::async — executa imediatamente em nova thread
    auto f1 = std::async(std::launch::async, expensive_computation, 5);
    
    // launch::deferred — executa apenas quando .get() é chamado
    auto f2 = std::async(std::launch::deferred, expensive_computation, 10);
    
    // Sem policy — implementação decide (PERIGOSO: pode ser deferred!)
    auto f3 = std::async(expensive_computation, 15);
    
    std::cout << "Result 1: " << f1.get() << "\n";
    std::cout << "Result 2: " << f2.get() << "\n";
    std::cout << "Result 3: " << f3.get() << "\n";
    
    return 0;
}
```

### 2.2 Exceções em Futures

```cpp
#include <future>
#include <stdexcept>
#include <iostream>

int might_throw(bool should_throw) {
    if (should_throw) throw std::runtime_error("Something went wrong!");
    return 42;
}

int main() {
    auto f = std::async(std::launch::async, might_throw, true);
    
    try {
        int result = f.get();
        std::cout << "Result: " << result << "\n";
    } catch (const std::exception& e) {
        std::cout << "Caught in main: " << e.what() << "\n";
    }
    
    return 0;
}
```

### 2.3 std::shared_future

```cpp
#include <future>
#include <vector>
#include <thread>
#include <iostream>

int main() {
    auto sf = std::async(std::launch::async, [] {
        return std::string("Data from computation");
    }).share();
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([sf, i] {
            std::cout << "Thread " << i << " got: " << sf.get() << "\n";
        });
    }
    
    for (auto& t : threads) t.join();
    
    return 0;
}
```

---

## 3. std::packaged_task

```cpp
#include <future>
#include <functional>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <iostream>

class SimpleThreadPool {
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex queue_mutex_;
    std::condition_variable condition_;
    bool stop_ = false;
    
public:
    explicit SimpleThreadPool(size_t num_threads = std::thread::hardware_concurrency()) {
        for (size_t i = 0; i < num_threads; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex_);
                        condition_.wait(lock, [this] {
                            return stop_ || !tasks_.empty();
                        });
                        
                        if (stop_ && tasks_.empty()) return;
                        
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }
    
    template<class F, class... Args>
    auto submit(F&& f, Args&&... args) -> std::future<typename std::invoke_result<F, Args...>::type> {
        using return_type = typename std::invoke_result<F, Args...>::type;
        
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        
        std::future<return_type> result = task->get_future();
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            if (stop_) throw std::runtime_error("submit on stopped pool");
            tasks_.emplace([task]() { (*task)(); });
        }
        condition_.notify_one();
        return result;
    }
    
    ~SimpleThreadPool() {
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            stop_ = true;
        }
        condition_.notify_all();
        for (auto& worker : workers_) {
            if (worker.joinable()) worker.join();
        }
    }
};

int main() {
    SimpleThreadPool pool(4);
    
    std::vector<std::future<int>> futures;
    
    for (int i = 0; i < 20; ++i) {
        futures.push_back(pool.submit([i] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return i * i;
        }));
    }
    
    for (auto& f : futures) {
        std::cout << f.get() << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

---

## 4. Thread Pool Avançado com Work Stealing

```cpp
#include <thread>
#include <vector>
#include <deque>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <random>
#include <functional>
#include <iostream>

class WorkStealingPool {
    struct alignas(64) WorkerData {
        std::deque<std::function<void()>> local_queue;
        std::mutex mutex;
    };
    
    std::vector<std::unique_ptr<WorkerData>> workers_;
    std::vector<std::thread> threads_;
    std::atomic<bool> stop_{false};
    std::atomic<int> active_tasks_{0};
    int num_workers_;
    
    std::mutex global_mutex_;
    std::condition_variable global_cv_;
    std::deque<std::function<void()>> global_queue_;
    
public:
    explicit WorkStealingPool(int num_workers = std::thread::hardware_concurrency())
        : num_workers_(num_workers) {
        workers_.resize(num_workers);
        for (int i = 0; i < num_workers; ++i) {
            workers_[i] = std::make_unique<WorkerData>();
        }
        
        threads_.reserve(num_workers);
        for (int i = 0; i < num_workers; ++i) {
            threads_.emplace_back(&WorkStealingPool::worker_loop, this, i);
        }
    }
    
    ~WorkStealingPool() {
        stop_.store(true, std::memory_order_release);
        global_cv_.notify_all();
        for (auto& t : threads_) {
            if (t.joinable()) t.join();
        }
    }
    
    template<class F>
    void submit(F&& task) {
        active_tasks_.fetch_add(1, std::memory_order_relaxed);
        int worker_id = get_random_worker();
        
        {
            std::lock_guard<std::mutex> lock(workers_[worker_id]->mutex);
            workers_[worker_id]->local_queue.emplace_back(std::forward<F>(task));
        }
        global_cv_.notify_one();
    }
    
    void wait_idle() {
        while (active_tasks_.load(std::memory_order_acquire) > 0) {
            std::this_thread::yield();
        }
    }
    
private:
    void worker_loop(int id) {
        while (!stop_.load(std::memory_order_acquire)) {
            std::function<void()> task;
            
            if (try_pop_local(id, task)) {
                execute_task(task);
                continue;
            }
            
            int victim = get_random_worker();
            if (victim != id && try_steal(victim, task)) {
                execute_task(task);
                continue;
            }
            
            if (try_pop_global(task)) {
                execute_task(task);
                continue;
            }
            
            std::unique_lock<std::mutex> lock(global_mutex_);
            global_cv_.wait_for(lock, std::chrono::microseconds(100),
                [this] { return stop_.load() || !global_queue_.empty(); });
        }
    }
    
    bool try_pop_local(int id, std::function<void()>& task) {
        std::lock_guard<std::mutex> lock(workers_[id]->mutex);
        if (!workers_[id]->local_queue.empty()) {
            task = std::move(workers_[id]->local_queue.front());
            workers_[id]->local_queue.pop_front();
            return true;
        }
        return false;
    }
    
    bool try_steal(int victim_id, std::function<void()>& task) {
        std::lock_guard<std::mutex> lock(workers_[victim_id]->mutex);
        auto& q = workers_[victim_id]->local_queue;
        if (!q.empty()) {
            task = std::move(q.back());
            q.pop_back();
            return true;
        }
        return false;
    }
    
    bool try_pop_global(std::function<void()>& task) {
        std::lock_guard<std::mutex> lock(global_mutex_);
        if (!global_queue_.empty()) {
            task = std::move(global_queue_.front());
            global_queue_.pop_front();
            return true;
        }
        return false;
    }
    
    void execute_task(std::function<void()>& task) {
        task();
        active_tasks_.fetch_sub(1, std::memory_order_release);
    }
    
    int get_random_worker() {
        thread_local std::mt19937 rng(std::hash<std::thread::id>{}(std::this_thread::get_id()));
        return std::uniform_int_distribution<>(0, num_workers_ - 1)(rng);
    }
};

int main() {
    WorkStealingPool pool(4);
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < 100000; ++i) {
        pool.submit([] {
            volatile int x = 0;
            for (int j = 0; j < 100; ++j) x += j;
        });
    }
    
    pool.wait_idle();
    auto end = std::chrono::high_resolution_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    std::cout << "Work-stealing pool: " << ms << "ms\n";
    return 0;
}
```

---

## 5. Padrões de Execução Assíncrona

### 5.1 Continuation Chaining

```cpp
#include <future>
#include <functional>
#include <iostream>
#include <string>

template<typename T>
class Task {
    std::future<T> future_;
    
public:
    explicit Task(std::future<T> f) : future_(std::move(f)) {}
    
    template<typename F>
    auto then(F&& func) -> Task<decltype(func(std::declval<T>()))> {
        using R = decltype(func(std::declval<T>()));
        auto next = std::async(std::launch::async, [f = std::move(future_),
                                                      func = std::forward<F>(func)]() mutable {
            return func(f.get());
        });
        return Task<R>(std::move(next));
    }
    
    T get() { return future_.get(); }
};

int main() {
    auto task = Task<int>(std::async(std::launch::async, [] {
        return 10;
    })).then([](int value) {
        return value * 2;
    }).then([](int value) {
        return std::to_string(value) + " is the result";
    });
    
    std::cout << task.get() << "\n";
    return 0;
}
```

### 5.2 When All / When Any

```cpp
#include <future>
#include <vector>
#include <iostream>

template<typename T>
std::future<std::vector<T>> when_all(std::vector<std::future<T>>& futures) {
    return std::async(std::launch::async, [&futures] {
        std::vector<T> results;
        results.reserve(futures.size());
        for (auto& f : futures) {
            results.push_back(f.get());
        }
        return results;
    });
}

int main() {
    std::vector<std::future<int>> futures;
    
    for (int i = 0; i < 5; ++i) {
        futures.push_back(std::async(std::launch::async, [i] {
            std::this_thread::sleep_for(std::chrono::milliseconds(100 * (5 - i)));
            return i * 10;
        }));
    }
    
    auto all_results = when_all(futures);
    auto results = all_results.get();
    
    for (int r : results) {
        std::cout << r << " ";
    }
    std::cout << "\n";
    
    return 0;
}
```

---

## 6. Cancellation e Timeout

```cpp
#include <atomic>
#include <future>
#include <chrono>
#include <iostream>
#include <thread>

class CancellationToken {
    std::atomic<bool> cancelled_{false};
public:
    void cancel() { cancelled_.store(true, std::memory_order_release); }
    bool is_cancelled() const { return cancelled_.load(std::memory_order_acquire); }
};

int long_computation(CancellationToken& token) {
    for (int i = 0; i < 1000000; ++i) {
        if (token.is_cancelled()) {
            throw std::runtime_error("Operation cancelled");
        }
        volatile int x = i * i;
        (void)x;
    }
    return 42;
}

int main() {
    CancellationToken token;
    
    auto future = std::async(std::launch::async, [&token] {
        return long_computation(token);
    });
    
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    token.cancel();
    
    try {
        int result = future.get();
        std::cout << "Result: " << result << "\n";
    } catch (const std::runtime_error& e) {
        std::cout << "Cancelled: " << e.what() << "\n";
    }
    
    return 0;
}
```

---

## 7. Benchmarking Thread Pools

```cpp
#include <chrono>
#include <iostream>
#include <vector>

template<typename Pool>
void benchmark_pool(Pool& pool, const std::string& name, int num_tasks) {
    std::vector<std::future<int>> futures;
    futures.reserve(num_tasks);
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < num_tasks; ++i) {
        futures.push_back(pool.submit([i] {
            volatile int x = 0;
            for (int j = 0; j < 1000; ++j) x += j;
            return i;
        }));
    }
    
    for (auto& f : futures) f.get();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count();
    
    std::cout << name << ": " << ms << "ms for " << num_tasks << " tasks\n";
}
```

---

## 8. Referências

- **Williams, A.** — C++ Concurrency in Action, 2nd Ed (Manning)
- **cppreference.com** — std::async, std::future, std::packaged_task
- **Herlihy & Shavit** — The Art of Multiprocessor Programming
- **Intel TBB** — Threading Building Blocks documentation
- **Folly** — Facebook's C++ library (folly::CPUThreadPoolExecutor)
