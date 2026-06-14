## 4. Fork-Join Parallelism

### 4.1 Decomposição Recursiva de Tarefas

Fork-join divide um problema recursivamente em subtarefas independentes (fork), executa-as em paralelo, e combina os resultados (join). Ideal para algoritmos divide-and-conquer.

```cpp
#include <thread>
#include <vector>
#include <future>
#include <functional>
#include <atomic>
#include <algorithm>

template<typename Result>
class ForkJoinTask {
public:
    using TaskFn = std::function<Result()>;
    using CombineFn = std::function<Result(std::vector<Result>&&)>;
    
private:
    TaskFn task_;
    CombineFn combine_;
    size_t threshold_;
    
public:
    ForkJoinTask(TaskFn task, CombineFn combine, size_t threshold = 1000)
        : task_(std::move(task)), combine_(std::move(combine)), threshold_(threshold) {}
    
    Result compute() {
        return compute_impl();
    }
    
private:
    Result compute_impl() {
        // Simplified: in real implementation, check problem size against threshold
        return task_();
    }
};

template<typename Iterator, typename Result>
Result parallel_reduce(Iterator begin, Iterator end, Result init, 
                       std::function<Result(Result, Result)> combine,
                       size_t threshold = 1000) {
    size_t size = std::distance(begin, end);
    if (size <= threshold) {
        return std::accumulate(begin, end, init, 
            [&](Result acc, auto val) { return combine(acc, val); });
    }
    
    Iterator mid = begin + size / 2;
    std::future<Result> left = std::async(std::launch::async, 
        parallel_reduce<Iterator, Result>, begin, mid, init, combine, threshold);
    Result right = parallel_reduce(mid, end, init, combine, threshold);
    return combine(left.get(), right);
}
```

### 4.2 Work Stealing Schedulers

Work stealing distribui tarefas dinamicamente: cada thread tem deque local; threads ociosas roubam do final de deques alheias (LIFO para local, FIFO para roubo).

```cpp
#include <array>
#include <thread>
#include <vector>
#include <deque>
#include <mutex>
#include <atomic>
#include <functional>
#include <optional>

class WorkStealingScheduler {
    struct Task {
        std::function<void()> fn;
    };
    
    struct Worker {
        std::deque<Task> local_queue;
        std::mutex mutex;
        std::atomic<bool> active{false};
    };
    
    std::vector<Worker> workers_;
    std::atomic<size_t> next_victim_{0};
    std::atomic<bool> running_{false};
    std::vector<std::thread> threads_;
    
public:
    explicit WorkStealingScheduler(size_t n = std::thread::hardware_concurrency()) 
        : workers_(n) {}
    
    ~WorkStealingScheduler() { stop(); }
    
    void start() {
        if (running_.exchange(true)) return;
        for (size_t i = 0; i < workers_.size(); ++i) {
            threads_.emplace_back([this, i] { run_worker(i); });
        }
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        for (auto& t : threads_) if (t.joinable()) t.join();
    }
    
    template<typename F>
    void submit(F&& f) {
        size_t idx = std::hash<std::thread::id>{}(std::this_thread::get_id()) % workers_.size();
        workers_[idx].local_queue.emplace_back(Task{std::forward<F>(f)});
    }
    
private:
    void run_worker(size_t my_idx) {
        workers_[my_idx].active = true;
        while (running_.load()) {
            Task task;
            bool got_task = pop_local(my_idx, task);
            if (!got_task) {
                got_task = steal_task(my_idx, task);
            }
            if (got_task) {
                task.fn();
            } else {
                std::this_thread::yield();
            }
        }
        workers_[my_idx].active = false;
    }
    
    bool pop_local(size_t idx, Task& task) {
        auto& w = workers_[idx];
        std::lock_guard<std::mutex> lock(w.mutex);
        if (w.local_queue.empty()) return false;
        task = std::move(w.local_queue.back());
        w.local_queue.pop_back();
        return true;
    }
    
    bool steal_task(size_t my_idx, Task& task) {
        size_t start = next_victim_.fetch_add(1, std::memory_order_relaxed) % workers_.size();
        for (size_t i = 0; i < workers_.size(); ++i) {
            size_t victim = (start + i) % workers_.size();
            if (victim == my_idx) continue;
            auto& w = workers_[victim];
            std::lock_guard<std::mutex> lock(w.mutex);
            if (!w.local_queue.empty()) {
                task = std::move(w.local_queue.front());
                w.local_queue.pop_front();
                return true;
            }
        }
        return false;
    }
};
```

### 4.3 C++20 std::execution para Fork-Join

C++20 introduz `std::execution` para paralelismo padrão. C++23 expande com `std::execution::par_unseq` e algoritmos paralelos.

```cpp
#include <execution>
#include <algorithm>
#include <vector>
#include <numeric>
#include <chrono>

void cpp20_fork_join_example() {
    std::vector<int> data(1'000'000);
    std::iota(data.begin(), data.end(), 1);
    
    // Paralelização automática com policies de execução
    auto sum = std::reduce(std::execution::par, data.begin(), data.end(), 0L);
    std::cout << "Sum: " << sum << std::endl;
    
    // Transformação paralela
    std::vector<double> results(data.size());
    std::transform(std::execution::par_unseq, data.begin(), data.end(), results.begin(),
        [](int x) { return std::sqrt(static_cast<double>(x)); });
    
    // Sort paralelo
    std::sort(std::execution::par, data.begin(), data.end());
    
    // Busca paralela
    auto it = std::find(std::execution::par, data.begin(), data.end(), 42);
}
```

### 4.4 TBB parallel_invoke

Intel TBB oferece `parallel_invoke` para fork-join simples e `task_group` para controle fino.

```cpp
#include <tbb/parallel_invoke.h>
#include <tbb/task_group.h>
#include <tbb/task_arena.h>

void tbb_fork_join_example() {
    // parallel_invoke para número fixo de tarefas
    tbb::parallel_invoke(
        [] { task_a(); },
        [] { task_b(); },
        [] { task_c(); }
    );
    
    // task_group para número dinâmico
    tbb::task_group tg;
    for (int i = 0; i < 100; ++i) {
        tg.run([i] { process_item(i); });
    }
    tg.wait();
    
    // task_arena para isolamento
    tbb::task_arena arena(4);
    arena.execute([&] {
        tbb::parallel_for(0, 1000, [](int i) { work(i); });
    });
}
```

### 4.5 OpenMP Tasks

OpenMP 4.0+ suporta tarefas explícitas com `task` directive para paralelismo irregular.

```cpp
#include <omp.h>
#include <vector>

void openmp_tasks_example() {
    std::vector<int> data(10000);
    
    #pragma omp parallel
    {
        #pragma omp single
        {
            for (size_t i = 0; i < data.size(); i += 1000) {
                #pragma omp task firstprivate(i)
                {
                    process_chunk(data.data() + i, 1000);
                }
            }
        }
    } // Barreira implícita aguarda todas as tasks
    
    // Taskloop para loops com tarefas
    #pragma omp parallel
    #pragma omp taskloop grainsize(100)
    for (int i = 0; i < 10000; ++i) {
        data[i] = compute(i);
    }
}
```

### 4.6 Balanceamento de Carga

Estratégias para balanceamento em fork-join:
- **Static partitioning**: Divisão igual antecipada
- **Dynamic scheduling**: Tarefas puxadas de fila compartilhada
- **Work stealing**: Roubo de trabalho (padrão TBB, Cilk)
- **Guided scheduling**: Tamanho de chunk decrescente

```cpp
template<typename Iterator, typename Func>
void parallel_for_dynamic(Iterator begin, Iterator end, Func func, size_t chunk_size = 64) {
    using Diff = typename std::iterator_traits<Iterator>::difference_type;
    Diff total = end - begin;
    std::atomic<Diff> next_index{0};
    
    auto worker = [&](Diff thread_id) {
        while (true) {
            Diff idx = next_index.fetch_add(chunk_size, std::memory_order_relaxed);
            if (idx >= total) break;
            Diff end_idx = std::min(idx + chunk_size, total);
            for (Diff i = idx; i < end_idx; ++i) {
                func(begin[i]);
            }
        }
    };
    
    size_t num_threads = std::thread::hardware_concurrency();
    std::vector<std::thread> threads;
    for (size_t i = 0; i < num_threads; ++i) {
        threads.emplace_back(worker, i);
    }
    for (auto& t : threads) t.join();
}
```

### 4.7 Bugs Conhecidos: Fork-Join Load Imbalance

**CVE-2019-12345 (Hypothetical - baseado em padrões reais)**: Em implementações de quicksort paralelo, escolha ruim de pivot causava desbalanceamento extremo onde uma thread processava 99% dos dados.

**Problema real em Java ForkJoinPool (JDK-8189729)**: Task stealing não funcionava corretamente para tarefas de longa duração, causando threads ociosas enquanto outras processavam tarefas grandes não divisíveis.

**Cilk Plus (Intel) - Load Imbalance em Fibonacci**: Implementação ingênua de Fibonacci paralelo criava overhead excessivo de tarefas para valores pequenos.

**Mitigações**:
- Use threshold para alternar para execução sequencial
- Implemente divisão de trabalho adaptativa
- Monitore tamanho de filas de trabalho por thread
- Considere `grainsize` em OpenMP taskloop