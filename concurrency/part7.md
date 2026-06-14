## 6. Scatter-Gather

### 6.1 Broadcast para Múltiplos Workers

Scatter-Gather envia uma requisição para múltiplos workers em paralelo (scatter) e agrega os resultados (gather). Útil para consultas paralelas, ensemble learning, busca distribuída.

```cpp
#include <vector>
#include <thread>
#include <future>
#include <functional>
#include <chrono>
#include <optional>
#include <atomic>

template<typename Request, typename Response>
class ScatterGather {
public:
    using WorkerFn = std::function<Response(const Request&)>;
    using AggregatorFn = std::function<Response(const std::vector<Response>&)>;
    
private:
    std::vector<WorkerFn> workers_;
    AggregatorFn aggregator_;
    std::chrono::milliseconds timeout_;
    size_t min_responses_;
    
public:
    ScatterGather(std::vector<WorkerFn> workers, AggregatorFn agg, 
                  std::chrono::milliseconds timeout = std::chrono::seconds(5),
                  size_t min_resp = 1)
        : workers_(std::move(workers)), aggregator_(std::move(agg)),
          timeout_(timeout), min_responses_(min_resp) {}
    
    Response execute(const Request& request) {
        std::vector<std::future<Response>> futures;
        futures.reserve(workers_.size());
        
        for (const auto& worker : workers_) {
            futures.push_back(std::async(std::launch::async, worker, std::cref(request)));
        }
        
        std::vector<Response> responses;
        responses.reserve(workers_.size());
        
        auto deadline = std::chrono::steady_clock::now() + timeout_;
        
        for (auto& future : futures) {
            auto remaining = deadline - std::chrono::steady_clock::now();
            if (remaining <= std::chrono::milliseconds(0)) break;
            
            auto status = future.wait_for(remaining);
            if (status == std::future_status::ready) {
                try {
                    responses.push_back(future.get());
                } catch (...) {
                    // Ignorar falhas individuais
                }
            }
        }
        
        if (responses.size() < min_responses_) {
            throw std::runtime_error("Insufficient responses: " + 
                std::to_string(responses.size()) + " < " + 
                std::to_string(min_responses_));
        }
        
        return aggregator_(std::move(responses));
    }
};
```

### 6.2 Agregação de Resultados

Estratégias de agregação comuns:

```cpp
// Maioria (voting)
template<typename T>
T majority_vote(const std::vector<T>& responses) {
    std::unordered_map<T, int> counts;
    for (const auto& r : responses) counts[r]++;
    return std::max_element(counts.begin(), counts.end(),
        [](const auto& a, const auto& b) { return a.second < b.second; })->first;
}

// Média (para valores numéricos)
template<typename T>
T average(const std::vector<T>& responses) {
    T sum = std::accumulate(responses.begin(), responses.end(), T{0});
    return sum / static_cast<T>(responses.size());
}

// Primeiro sucesso (first success)
template<typename T>
std::optional<T> first_success(const std::vector<std::optional<T>>& responses) {
    for (const auto& r : responses) {
        if (r.has_value()) return r;
    }
    return std::nullopt;
}

// Melhor resultado (best result com scoring)
template<typename T>
T best_result(const std::vector<T>& responses, std::function<double(const T&)> score_fn) {
    return *std::max_element(responses.begin(), responses.end(),
        [&](const T& a, const T& b) { return score_fn(a) < score_fn(b); });
}

// Quorum (exige N concordâncias)
template<typename T>
std::optional<T> quorum(const std::vector<T>& responses, size_t required) {
    std::unordered_map<T, int> counts;
    for (const auto& r : responses) {
        if (++counts[r] >= static_cast<int>(required)) return r;
    }
    return std::nullopt;
}
```

### 6.3 Tratamento de Timeout

Timeouts individuais e globais com cancelamento cooperativo.

```cpp
#include <atomic>
#include <chrono>

template<typename Request, typename Response>
class TimedScatterGather {
    using WorkerFn = std::function<Response(const Request&, std::atomic<bool>&)>;
    using AggregatorFn = std::function<Response(const std::vector<Response>&)>;
    
    std::vector<WorkerFn> workers_;
    AggregatorFn aggregator_;
    std::chrono::milliseconds global_timeout_;
    std::chrono::milliseconds per_worker_timeout_;
    
public:
    TimedScatterGather(std::vector<WorkerFn> w, AggregatorFn agg,
                       std::chrono::milliseconds global_to,
                       std::chrono::milliseconds per_worker_to)
        : workers_(std::move(w)), aggregator_(std::move(agg)),
          global_timeout_(global_to), per_worker_timeout_(per_worker_to) {}
    
    Response execute(const Request& request) {
        std::atomic<bool> cancelled{false};
        std::vector<std::future<Response>> futures;
        std::vector<std::thread> timeout_threads;
        
        auto global_deadline = std::chrono::steady_clock::now() + global_timeout_;
        
        for (auto& worker : workers_) {
            futures.push_back(std::async(std::launch::async, [&, worker = std::move(worker)]() {
                return worker(request, cancelled);
            }));
        }
        
        // Thread de timeout global
        std::thread global_timer([&] {
            std::this_thread::sleep_until(global_deadline);
            cancelled = true;
        });
        
        std::vector<Response> responses;
        for (auto& future : futures) {
            if (future.wait_for(std::chrono::milliseconds(100)) == std::future_status::ready) {
                try {
                    responses.push_back(future.get());
                } catch (...) {}
            }
        }
        
        cancelled = true;
        if (global_timer.joinable()) global_timer.join();
        
        return aggregator_(std::move(responses));
    }
};
```

### 6.4 Resultados Parciais

Retornar resultados mesmo com falhas parciais, com metadados de qualidade.

```cpp
#include <variant>
#include <string>

template<typename T>
struct PartialResult {
    std::vector<T> successful;
    std::vector<std::pair<size_t, std::string>> failed; // worker_id, error
    std::chrono::milliseconds elapsed;
    bool timed_out;
    double completeness_ratio() const {
        return successful.empty() ? 0.0 : 
            static_cast<double>(successful.size()) / (successful.size() + failed.size());
    }
};

template<typename Request, typename Response>
class PartialScatterGather {
    using WorkerFn = std::function<Response(const Request&)>;
    using AggregatorFn = std::function<Response(const PartialResult<Response>&)>;
    
    std::vector<WorkerFn> workers_;
    AggregatorFn aggregator_;
    std::chrono::milliseconds timeout_;
    
public:
    PartialScatterGather(std::vector<WorkerFn> w, AggregatorFn agg, 
                         std::chrono::milliseconds to)
        : workers_(std::move(w)), aggregator_(std::move(agg)), timeout_(to) {}
    
    PartialResult<Response> execute_partial(const Request& request) {
        PartialResult<Response> result;
        auto start = std::chrono::steady_clock::now();
        auto deadline = start + timeout_;
        
        std::vector<std::future<Response>> futures;
        for (size_t i = 0; i < workers_.size(); ++i) {
            futures.push_back(std::async(std::launch::async, [&, i]() {
                return std::make_pair(i, workers_[i](request));
            }));
        }
        
        for (auto& future : futures) {
            auto remaining = deadline - std::chrono::steady_clock::now();
            if (remaining <= std::chrono::milliseconds(0)) {
                result.timed_out = true;
                break;
            }
            
            auto status = future.wait_for(remaining);
            if (status == std::future_status::ready) {
                try {
                    auto [worker_id, response] = future.get();
                    result.successful.push_back(std::move(response));
                } catch (const std::exception& e) {
                    result.failed.emplace_back(0, e.what());
                }
            }
        }
        
        result.elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - start);
        return result;
    }
};
```

### 6.5 Implementação em C++

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <thread>
#include <future>
#include <chrono>
#include <algorithm>

struct SearchQuery { std::string term; int max_results; };
struct SearchResult { std::string source; std::vector<std::string> items; double score; };

SearchResult aggregate_search(const PartialResult<SearchResult>& partial) {
    SearchResult best;
    best.score = -1.0;
    
    for (const auto& r : partial.successful) {
        if (r.score > best.score) {
            best = r;
        }
    }
    return best;
}

void scatter_gather_demo() {
    std::vector<std::function<SearchResult(const SearchQuery&)>> search_engines = {
        [](const SearchQuery& q) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            return SearchResult{"Google", {"result1", "result2"}, 0.9}; 
        },
        [](const SearchQuery& q) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(150));
            return SearchResult{"Bing", {"result3", "result4"}, 0.85}; 
        },
        [](const SearchQuery& q) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(200));
            return SearchResult{"DuckDuckGo", {"result5"}, 0.8}; 
        }
    };
    
    PartialScatterGather<SearchQuery, SearchResult> sg(
        std::move(search_engines), aggregate_search, std::chrono::milliseconds(300));
    
    auto result = sg.execute_partial({"C++ concurrency", 10});
    
    std::cout << "Best source: " << result.successful[0].source << std::endl;
    std::cout << "Completeness: " << result.completeness_ratio() * 100 << "%" << std::endl;
    std::cout << "Elapsed: " << result.elapsed.count() << "ms" << std::endl;
}
```

### 6.6 Bugs Conhecidos: Scatter-Gather

**Problema real em sistemas de busca distribuída**: Timeout global muito curto causava cancelamento de workers lentos mas precisos, degradando qualidade dos resultados.

**Race condition em agregação**: Múltiplas threads escrevendo no mesmo acumulador sem sincronização causava perda de resultados.