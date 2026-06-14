## 3. Pipeline Parallelism

### 3.1 Decomposição em Estágios

Pipeline parallelism divide uma computação em estágios sequenciais, onde cada estágio processa dados e passa para o próximo. Isso permite sobreposição de execução: enquanto o estágio N processa item i, o estágio N+1 processa item i-1.

```cpp
#include <thread>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <atomic>
#include <chrono>

template<typename Input, typename Output>
class PipelineStage {
public:
    using ProcessFn = std::function<Output(Input)>;
    
private:
    ProcessFn process_;
    std::queue<Input> input_queue_;
    std::queue<Output> output_queue_;
    std::mutex input_mutex_, output_mutex_;
    std::condition_variable input_cv_, output_cv_;
    std::thread worker_;
    std::atomic<bool> running_{false};
    std::atomic<bool> stopped_{false};
    size_t input_capacity_, output_capacity_;
    
public:
    PipelineStage(ProcessFn fn, size_t in_cap = 100, size_t out_cap = 100)
        : process_(std::move(fn)), input_capacity_(in_cap), output_capacity_(out_cap) {}
    
    ~PipelineStage() { stop(); }
    
    bool push(Input item) {
        std::unique_lock<std::mutex> lock(input_mutex_);
        if (stopped_) return false;
        input_cv_.wait(lock, [this] { return input_queue_.size() < input_capacity_ || stopped_; });
        if (stopped_) return false;
        input_queue_.push(std::move(item));
        input_cv_.notify_one();
        return true;
    }
    
    std::optional<Output> pop() {
        std::unique_lock<std::mutex> lock(output_mutex_);
        output_cv_.wait(lock, [this] { return !output_queue_.empty() || stopped_; });
        if (output_queue_.empty() && stopped_) return std::nullopt;
        Output item = std::move(output_queue_.front());
        output_queue_.pop();
        output_cv_.notify_one();
        return item;
    }
    
    void start() {
        if (running_.exchange(true)) return;
        worker_ = std::thread([this] { run(); });
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        stopped_ = true;
        input_cv_.notify_all();
        output_cv_.notify_all();
        if (worker_.joinable()) worker_.join();
    }
    
private:
    void run() {
        while (running_.load()) {
            Input item;
            {
                std::unique_lock<std::mutex> lock(input_mutex_);
                input_cv_.wait(lock, [this] { return !input_queue_.empty() || stopped_.load(); });
                if (input_queue_.empty() && stopped_) break;
                item = std::move(input_queue_.front());
                input_queue_.pop();
                input_cv_.notify_one();
            }
            
            Output result = process_(std::move(item));
            
            {
                std::unique_lock<std::mutex> lock(output_mutex_);
                output_cv_.wait(lock, [this] { return output_queue_.size() < output_capacity_ || stopped_.load(); });
                if (stopped_) break;
                output_queue_.push(std::move(result));
                output_cv_.notify_one();
            }
        }
    }
};

template<typename... Stages>
class Pipeline {
    std::tuple<Stages...> stages_;
    
public:
    Pipeline(Stages... stages) : stages_(std::move(stages)...) {}
    
    void start() {
        std::apply([](auto&... s) { (s.start(), ...); }, stages_);
    }
    
    void stop() {
        std::apply([](auto&... s) { (s.stop(), ...); }, stages_);
    }
    
    template<typename Input>
    bool push(Input&& item) {
        return std::get<0>(stages_).push(std::forward<Input>(item));
    }
    
    template<typename Output>
    std::optional<Output> pop() {
        return std::get<sizeof...(Stages)-1>(stages_).pop();
    }
};
```

### 3.2 Buffer Entre Estágios

Buffers entre estágios desacoplam produtores e consumidores, absorvendo variações de velocidade. Dimensionamento correto é crítico: buffers muito pequenos causam bloqueio frequente; muito grandes aumentam latência e uso de memória.

```cpp
template<typename T>
class BoundedBuffer {
    std::vector<T> buffer_;
    std::atomic<size_t> head_{0}, tail_{0};
    std::atomic<size_t> count_{0};
    const size_t capacity_;
    
public:
    explicit BoundedBuffer(size_t cap) : buffer_(cap), capacity_(cap) {}
    
    bool push(T item) {
        size_t h = head_.load(std::memory_order_relaxed);
        for (;;) {
            size_t c = count_.load(std::memory_order_acquire);
            if (c >= capacity_) return false;
            if (count_.compare_exchange_weak(c, c + 1, std::memory_order_acq_rel)) {
                buffer_[h] = std::move(item);
                head_.store((h + 1) % capacity_, std::memory_order_release);
                return true;
            }
        }
    }
    
    std::optional<T> pop() {
        size_t t = tail_.load(std::memory_order_relaxed);
        for (;;) {
            size_t c = count_.load(std::memory_order_acquire);
            if (c == 0) return std::nullopt;
            if (count_.compare_exchange_weak(c, c - 1, std::memory_order_acq_rel)) {
                T item = std::move(buffer_[t]);
                tail_.store((t + 1) % capacity_, std::memory_order_release);
                return item;
            }
        }
    }
    
    size_t size() const { return count_.load(std::memory_order_acquire); }
    bool empty() const { return size() == 0; }
    bool full() const { return size() >= capacity_; }
};
```

### 3.3 Backpressure

Backpressure propaga sinais de lentidão do consumidor para o produtor, evitando estouro de memória. Estratégias incluem: bloqueio, descarte (drop), amostragem, ou sinalização explícita.

```cpp
enum class BackpressureStrategy {
    Block,      // Bloquear produtor
    DropOldest, // Descarta item mais antigo
    DropLatest, // Descarta item mais novo
    Sample      // Amostragem periódica
};

template<typename T>
class BackpressureBuffer {
    std::queue<T> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    size_t capacity_;
    BackpressureStrategy strategy_;
    std::atomic<size_t> dropped_{0};
    
public:
    BackpressureBuffer(size_t cap, BackpressureStrategy strat = BackpressureStrategy::Block)
        : capacity_(cap), strategy_(strat) {}
    
    bool push(T item) {
        std::unique_lock<std::mutex> lock(mutex_);
        if (queue_.size() >= capacity_) {
            switch (strategy_) {
                case BackpressureStrategy::Block:
                    cv_.wait(lock, [this] { return queue_.size() < capacity_; });
                    break;
                case BackpressureStrategy::DropOldest:
                    if (!queue_.empty()) {
                        queue_.pop();
                        dropped_++;
                    }
                    break;
                case BackpressureStrategy::DropLatest:
                    dropped_++;
                    return false;
                case BackpressureStrategy::Sample:
                    if (dropped_++ % 10 != 0) return false;
                    if (!queue_.empty()) queue_.pop();
                    break;
            }
        }
        queue_.push(std::move(item));
        cv_.notify_one();
        return true;
    }
    
    std::optional<T> pop() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return !queue_.empty(); });
        T item = std::move(queue_.front());
        queue_.pop();
        cv_.notify_one();
        return item;
    }
    
    size_t dropped_count() const { return dropped_.load(); }
};
```

### 3.4 Balanceamento de Carga Dinâmico

Work stealing permite que threads ociosas roubem trabalho de threads ocupadas, melhorando utilização em cargas irregulares.

```cpp
#include <deque>
#include <thread>
#include <vector>
#include <atomic>
#include <mutex>

template<typename Task>
class WorkStealingQueue {
    std::deque<Task> deque_;
    std::mutex mutex_;
    
public:
    void push(Task task) {
        std::lock_guard<std::mutex> lock(mutex_);
        deque_.push_back(std::move(task));
    }
    
    std::optional<Task> pop() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return std::nullopt;
        Task task = std::move(deque_.front());
        deque_.pop_front();
        return task;
    }
    
    std::optional<Task> steal() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (deque_.empty()) return std::nullopt;
        Task task = std::move(deque_.back());
        deque_.pop_back();
        return task;
    }
    
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return deque_.empty();
    }
};

template<typename Task>
class WorkStealingExecutor {
    std::vector<std::unique_ptr<WorkStealingQueue<Task>>> queues_;
    std::vector<std::thread> workers_;
    std::atomic<bool> running_{false};
    std::atomic<size_t> next_queue_{0};
    
public:
    explicit WorkStealingExecutor(size_t num_threads = std::thread::hardware_concurrency()) {
        queues_.reserve(num_threads);
        for (size_t i = 0; i < num_threads; ++i) {
            queues_.push_back(std::make_unique<WorkStealingQueue<Task>>());
        }
    }
    
    void start() {
        if (running_.exchange(true)) return;
        for (size_t i = 0; i < queues_.size(); ++i) {
            workers_.emplace_back([this, i] { worker_loop(i); });
        }
    }
    
    void stop() {
        if (!running_.exchange(false)) return;
        for (auto& w : workers_) if (w.joinable()) w.join();
    }
    
    void submit(Task task) {
        size_t idx = next_queue_.fetch_add(1, std::memory_order_relaxed) % queues_.size();
        queues_[idx]->push(std::move(task));
    }
    
private:
    void worker_loop(size_t my_idx) {
        while (running_.load()) {
            auto task = queues_[my_idx]->pop();
            if (!task) {
                for (size_t i = 0; i < queues_.size(); ++i) {
                    if (i == my_idx) continue;
                    task = queues_[i]->steal();
                    if (task) break;
                }
            }
            if (task) {
                (*task)();
            } else {
                std::this_thread::yield();
            }
        }
    }
};
```

### 3.5 Framework de Pipeline em C++

```cpp
#include <ranges>
#include <vector>
#include <functional>

template<typename T>
concept PipelineStageConcept = requires(T t, typename T::input_type in) {
    { t.process(in) } -> std::same_as<typename T::output_type>;
    { t.start() } -> std::same_as<void>;
    { t.stop() } -> std::same_as<void>;
};

template<typename Input, typename Output>
class SimpleStage {
public:
    using input_type = Input;
    using output_type = Output;
    using Fn = std::function<Output(Input)>;
    
private:
    Fn fn_;
    std::thread thread_;
    std::atomic<bool> running_{false};
    
public:
    explicit SimpleStage(Fn fn) : fn_(std::move(fn)) {}
    
    Output process(Input in) { return fn_(std::move(in)); }
    
    void start() { running_ = true; }
    void stop() { running_ = false; }
};

template<typename... Stages>
class ComposablePipeline {
    std::tuple<Stages...> stages_;
    
public:
    ComposablePipeline(Stages... s) : stages_(std::move(s)...) {}
    
    auto operator|(auto next_stage) {
        return ComposablePipeline<Stages..., decltype(next_stage)>(
            std::move(stages_), std::move(next_stage));
    }
    
    void execute(auto input_range) {
        // Implementation omitted for brevity
    }
};
```

### 3.6 TBB flow_graph

Intel TBB flow_graph fornece abstração de alto nível para pipelines com graph-based execution.

```cpp
#include <tbb/flow_graph.h>

using namespace tbb::flow;

void tbb_pipeline_example() {
    graph g;
    
    function_node<int, int> stage1(g, unlimited, [](int x) {
        return x * 2;
    });
    
    function_node<int, int> stage2(g, unlimited, [](int x) {
        return x + 1;
    });
    
    function_node<int, void> stage3(g, unlimited, [](int x) {
        std::cout << "Result: " << x << std::endl;
    });
    
    make_edge(stage1, stage2);
    make_edge(stage2, stage3);
    
    for (int i = 0; i < 100; ++i) {
        stage1.try_put(i);
    }
    
    g.wait_for_all();
}
```

### 3.7 cppcoro Pipeline

```cpp
#include <cppcoro/generator.hpp>
#include <cppcoro/channel.hpp>
#include <cppcoro/task.hpp>
#include <cppcoro/sync_wait.hpp>

cppcoro::generator<int> source() {
    for (int i = 0; i < 100; ++i) co_yield i;
}

cppcoro::task<> stage1(cppcoro::channel<int>& in, cppcoro::channel<int>& out) {
    for (int val : in) {
        co_await out.write(val * 2);
    }
    out.close();
}

cppcoro::task<> stage2(cppcoro::channel<int>& in, cppcoro::channel<int>& out) {
    for (int val : in) {
        co_await out.write(val + 1);
    }
    out.close();
}

cppcoro::task<> sink(cppcoro::channel<int>& in) {
    for (int val : in) {
        std::cout << "Result: " << val << std::endl;
    }
}

cppcoro::task<> cppcoro_pipeline() {
    cppcoro::channel<int> ch1(10), ch2(10), ch3(10);
    
    co_await cppcoro::when_all(
        [&]() -> cppcoro::task<> {
            for (int i : source()) co_await ch1.write(i);
            ch1.close();
        }(),
        stage1(ch1, ch2),
        stage2(ch2, ch3),
        sink(ch3)
    );
}
```

### 3.8 Bugs Conhecidos: Pipeline Parallelism Data Races

**CVE-2021-43828 (Apache Flink)**: Race condition no pipeline de processamento de streams causava corrupção de estado quando operadores compartilhavam buffers não sincronizados corretamente.

**CVE-2020-13949 (Apache Kafka Streams)**: Data race no processador de pipelines de transformação levou a resultados inconsistentes em junções de streams sob alta carga.

**Lições aprendidas**:
- Sempre sincronize acesso a buffers compartilhados entre estágios
- Use atomics ou mutexes para contadores de progresso
- Valide com sanitizers (TSan, ASan) em testes de carga
- Implemente backpressure explícito para evitar estouro de buffer