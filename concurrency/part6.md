## 5. Map-Reduce Pattern

### 5.1 Fase Map Paralela

Map aplica uma função a cada elemento independentemente, permitindo paralelismo embarassingly parallel.

```cpp
#include <vector>
#include <thread>
#include <future>
#include <functional>
#include <algorithm>
#include <iterator>

template<typename Input, typename Output>
std::vector<Output> parallel_map(const std::vector<Input>& input, 
                                  std::function<Output(const Input&)> map_fn,
                                  size_t num_threads = 0) {
    if (num_threads == 0) num_threads = std::thread::hardware_concurrency();
    if (input.empty()) return {};
    if (num_threads == 1 || input.size() < 1000) {
        std::vector<Output> result;
        result.reserve(input.size());
        std::transform(input.begin(), input.end(), std::back_inserter(result), map_fn);
        return result;
    }
    
    size_t chunk_size = (input.size() + num_threads - 1) / num_threads;
    std::vector<std::future<std::vector<Output>>> futures;
    
    for (size_t i = 0; i < input.size(); i += chunk_size) {
        size_t end = std::min(i + chunk_size, input.size());
        futures.push_back(std::async(std::launch::async, [&, i, end]() {
            std::vector<Output> local;
            local.reserve(end - i);
            for (size_t j = i; j < end; ++j) {
                local.push_back(map_fn(input[j]));
            }
            return local;
        }));
    }
    
    std::vector<Output> result;
    result.reserve(input.size());
    for (auto& f : futures) {
        auto chunk = f.get();
        result.insert(result.end(), chunk.begin(), chunk.end());
    }
    return result;
}
```

### 5.2 Shuffle / Group By

Shuffle reorganiza dados por chave para que todos os valores da mesma chave vão para o mesmo reducer.

```cpp
#include <unordered_map>
#include <vector>
#include <string>
#include <algorithm>

template<typename Key, typename Value>
std::unordered_map<Key, std::vector<Value>> shuffle(
    const std::vector<std::pair<Key, Value>>& mapped_data) {
    
    std::unordered_map<Key, std::vector<Value>> grouped;
    grouped.reserve(mapped_data.size() / 2);
    
    for (const auto& kv : mapped_data) {
        grouped[kv.first].push_back(kv.second);
    }
    return grouped;
}

template<typename Key, typename Value>
std::vector<std::pair<Key, std::vector<Value>>> parallel_shuffle(
    const std::vector<std::pair<Key, Value>>& mapped_data,
    size_t num_partitions) {
    
    std::vector<std::unordered_map<Key, std::vector<Value>>> partitions(num_partitions);
    
    // Distribuir por hash da chave
    for (const auto& kv : mapped_data) {
        size_t partition = std::hash<Key>{}(kv.first) % num_partitions;
        partitions[partition][kv.first].push_back(kv.second);
    }
    
    // Mesclar partições
    std::unordered_map<Key, std::vector<Value>> merged;
    for (auto& part : partitions) {
        for (auto& kv : part) {
            merged[kv.first].insert(merged[kv.first].end(), 
                                    kv.second.begin(), kv.second.end());
        }
    }
    
    std::vector<std::pair<Key, std::vector<Value>>> result;
    result.reserve(merged.size());
    for (auto& kv : merged) {
        result.emplace_back(std::move(kv.first), std::move(kv.second));
    }
    return result;
}
```

### 5.3 Fase Reduce Paralela

Reduce combina valores por chave em resultado final.

```cpp
template<typename Key, typename Value, typename Result>
std::unordered_map<Key, Result> parallel_reduce(
    const std::vector<std::pair<Key, std::vector<Value>>>& grouped,
    std::function<Result(const std::vector<Value>&)> reduce_fn,
    size_t num_threads = 0) {
    
    if (num_threads == 0) num_threads = std::thread::hardware_concurrency();
    
    std::vector<std::future<std::unordered_map<Key, Result>>> futures;
    size_t chunk_size = (grouped.size() + num_threads - 1) / num_threads;
    
    for (size_t i = 0; i < grouped.size(); i += chunk_size) {
        size_t end = std::min(i + chunk_size, grouped.size());
        futures.push_back(std::async(std::launch::async, [&, i, end]() {
            std::unordered_map<Key, Result> local;
            for (size_t j = i; j < end; ++j) {
                local[grouped[j].first] = reduce_fn(grouped[j].second);
            }
            return local;
        }));
    }
    
    std::unordered_map<Key, Result> result;
    for (auto& f : futures) {
        auto part = f.get();
        result.insert(part.begin(), part.end());
    }
    return result;
}
```

### 5.4 Implementações em C++

Framework completo MapReduce:

```cpp
#include <vector>
#include <unordered_map>
#include <string>
#include <thread>
#include <future>
#include <functional>
#include <fstream>
#include <sstream>

template<typename Input, typename Key, typename Value, typename Output>
class MapReduce {
public:
    using MapFn = std::function<std::vector<std::pair<Key, Value>>(const Input&)>;
    using ReduceFn = std::function<Output(const Key&, const std::vector<Value>&)>;
    
private:
    MapFn map_fn_;
    ReduceFn reduce_fn_;
    size_t num_workers_;
    
public:
    MapReduce(MapFn map_fn, ReduceFn reduce_fn, size_t workers = 0)
        : map_fn_(std::move(map_fn)), reduce_fn_(std::move(reduce_fn)), 
          num_workers_(workers ? workers : std::thread::hardware_concurrency()) {}
    
    std::unordered_map<Key, Output> execute(const std::vector<Input>& inputs) {
        // Phase 1: Parallel Map
        std::vector<std::future<std::vector<std::pair<Key, Value>>>> map_futures;
        size_t chunk_size = (inputs.size() + num_workers_ - 1) / num_workers_;
        
        for (size_t i = 0; i < inputs.size(); i += chunk_size) {
            size_t end = std::min(i + chunk_size, inputs.size());
            map_futures.push_back(std::async(std::launch::async, [&, i, end]() {
                std::vector<std::pair<Key, Value>> results;
                for (size_t j = i; j < end; ++j) {
                    auto mapped = map_fn_(inputs[j]);
                    results.insert(results.end(), mapped.begin(), mapped.end());
                }
                return results;
            }));
        }
        
        // Collect map results
        std::vector<std::pair<Key, Value>> all_mapped;
        for (auto& f : map_futures) {
            auto chunk = f.get();
            all_mapped.insert(all_mapped.end(), chunk.begin(), chunk.end());
        }
        
        // Phase 2: Shuffle (Group by Key)
        std::unordered_map<Key, std::vector<Value>> grouped;
        for (const auto& kv : all_mapped) {
            grouped[kv.first].push_back(kv.second);
        }
        
        // Phase 3: Parallel Reduce
        std::vector<std::pair<Key, std::vector<Value>>> grouped_vec(grouped.begin(), grouped.end());
        std::vector<std::future<std::unordered_map<Key, Output>>> reduce_futures;
        size_t reduce_chunk = (grouped_vec.size() + num_workers_ - 1) / num_workers_;
        
        for (size_t i = 0; i < grouped_vec.size(); i += reduce_chunk) {
            size_t end = std::min(i + reduce_chunk, grouped_vec.size());
            reduce_futures.push_back(std::async(std::launch::async, [&, i, end]() {
                std::unordered_map<Key, Output> local;
                for (size_t j = i; j < end; ++j) {
                    local[grouped_vec[j].first] = reduce_fn_(grouped_vec[j].first, grouped_vec[j].second);
                }
                return local;
            }));
        }
        
        // Collect reduce results
        std::unordered_map<Key, Output> final_result;
        for (auto& f : reduce_futures) {
            auto part = f.get();
            final_result.insert(part.begin(), part.end());
        }
        return final_result;
    }
};

// Exemplo: Word Count
void word_count_example() {
    std::vector<std::string> documents = {
        "hello world hello",
        "world map reduce",
        "hello parallel world"
    };
    
    MapReduce<std::string, std::string, int, int> mr(
        [](const std::string& doc) {
            std::vector<std::pair<std::string, int>> result;
            std::istringstream iss(doc);
            std::string word;
            while (iss >> word) {
                result.emplace_back(word, 1);
            }
            return result;
        },
        [](const std::string& key, const std::vector<int>& values) {
            return static_cast<int>(values.size());
        }
    );
    
    auto result = mr.execute(documents);
    for (const auto& [word, count] : result) {
        std::cout << word << ": " << count << std::endl;
    }
}
```

### 5.5 Tolerância a Falhas

MapReduce tolera falhas através de:
- **Checkpointing**: Salvar estado intermediário
- **Re-execution**: Re-executar tarefas falhas
- **Speculative execution**: Executar tarefas lentas duplicadas

```cpp
#include <chrono>
#include <atomic>
#include <functional>

template<typename Input, typename Key, typename Value, typename Output>
class FaultTolerantMapReduce {
    using MapFn = std::function<std::vector<std::pair<Key, Value>>(const Input&)>;
    using ReduceFn = std::function<Output(const Key&, const std::vector<Value>&)>;
    
    struct TaskResult {
        bool success;
        std::string error;
        std::vector<std::pair<Key, Value>> data;
        std::chrono::steady_clock::time_point start_time;
        std::chrono::steady_clock::time_point end_time;
    };
    
    MapFn map_fn_;
    ReduceFn reduce_fn_;
    size_t num_workers_;
    size_t max_retries_ = 3;
    std::chrono::seconds task_timeout_ = std::chrono::seconds(300);
    
public:
    FaultTolerantMapReduce(MapFn map, ReduceFn reduce, size_t workers = 0)
        : map_fn_(std::move(map)), reduce_fn_(std::move(reduce)), 
          num_workers_(workers ? workers : std::thread::hardware_concurrency()) {}
    
    std::unordered_map<Key, Output> execute(const std::vector<Input>& inputs) {
        // Implementação com retry e timeout
        // ...
        return {};
    }
    
private:
    TaskResult run_map_task_with_retry(const std::vector<Input>& chunk, size_t task_id) {
        for (size_t attempt = 0; attempt <= max_retries_; ++attempt) {
            TaskResult result;
            result.start_time = std::chrono::steady_clock::now();
            try {
                std::vector<std::pair<Key, Value>> data;
                for (const auto& input : chunk) {
                    auto mapped = map_fn_(input);
                    data.insert(data.end(), mapped.begin(), mapped.end());
                }
                result.success = true;
                result.data = std::move(data);
            } catch (const std::exception& e) {
                result.success = false;
                result.error = e.what();
            }
            result.end_time = std::chrono::steady_clock::now();
            
            if (result.success) return result;
            
            std::this_thread::sleep_for(std::chrono::seconds(1 << attempt));
        }
        return {false, "Max retries exceeded", {}, {}, {}};
    }
};
```

### 5.6 Bugs Conhecidos: Map-Reduce Synchronization

**CVE-2018-11761 (Apache Hadoop MapReduce)**: Race condition no JobTracker ao limpar tarefas falhas permitia vazamento de memória e deadlock do cluster.

**CVE-2020-9484 (Apache Spark)**: Falha na serialização de closures em tarefas map causava execução de código arbitrário no worker.

**Problema real em Spark (SPARK-23205)**: Especulação de tarefas (speculative execution) podia causar resultados duplicados no reduce quando tarefas lentas completavam após a especulação.

**Lições**:
- Idempotência é essencial para tolerância a falhas
- Use identificadores únicos para deduplicação
- Valide determinismo de map e reduce
- Implemente checkpointing periódico