# Capítulo 17 — Boas Práticas e Guia de Referência

## Objetivos de Aprendizado

1. Consolidar os princípios fundamentais de concorrência segura em C++
2. Aplicar um checklist completo para revisão de código concorrente
3. Identificar e evitar anti-padrões comuns em código multithreaded
4. Construir uma cultura de qualidade em projetos com concorrência
5. Referenciar rapidamente primitivas e padrões para uso diário

---

## 1. Princípios Fundamentais

### 1.1 Princípio 1: Nunca Confie em sua Intuição

```cpp
// ANTI-PADRÃO: "Isso provavelmente funciona"
int shared_counter = 0;

void increment() {
    shared_counter++;  // Não é atômico! Data race!
}
```

A intuição humana é terrível para prever comportamento concorrente. O compilador pode reordenar, o hardware pode reordenar, e o scheduling de threads é não-determinístico.

**Regra de ouro**: Se você não pode provar formalmente que o código está correto, ele não está.

### 1.2 Princípio 2: Use Ferramentas, Não Testing Manual

```bash
# Sempre compile com TSan em desenvolvimento
g++ -std=c++20 -fsanitize=thread -g -O1 code.cpp -o code -pthread

# Teste com múltiplos sanitizers
g++ -std=c++20 -fsanitize=thread,address,undefined -g -O1 code.cpp -o code_all -pthread

# Fuzzing para encontrar race conditions
clang++ -std=c++20 -fsanitize=fuzzer,thread -g code.cpp -o fuzz_target
```

### 1.3 Princípio 3: Favor Imutabilidade

```cpp
#include <memory>
#include <string>
#include <thread>
#include <iostream>

// MUTÁVEL: requer sincronização complexa
class MutableConfig {
    mutable std::mutex mutex_;
    std::string data_;
public:
    void set(std::string d) { std::lock_guard lock(mutex_); data_ = std::move(d); }
    std::string get() const { std::lock_guard lock(mutex_); return data_; }
};

// IMUTÁVEL: seguro por construção
class ImmutableConfig {
    const std::shared_ptr<const std::string> data_;
public:
    explicit ImmutableConfig(std::string d) : data_(std::make_shared<const std::string>(std::move(d))) {}
    ImmutableConfig update(std::string new_data) const {
        return ImmutableConfig(std::move(new_data));
    }
    std::string get() const { return *data_; }
};

int main() {
    ImmutableConfig config("initial");
    auto updated = config.update("new value");  // Nova cópia, sem locks
    
    // Múltiplas threads podem ler simultaneamente
    std::thread t1([&config] { std::cout << config.get() << "\n"; });
    std::thread t2([&updated] { std::cout << updated.get() << "\n"; });
    t1.join(); t2.join();
    return 0;
}
```

---

## 2. Checklist de Código Concorrente

### 2.1 Design Checklist

```markdown
### Design
- [ ] Identificar TODOS os dados compartilhados entre threads
- [ ] Definir estrutura de sincronização para cada dado compartilhado
- [ ] Documentar invariantes de cada estrutura thread-safe
- [ ] Verificar ausência de deadlocks (ordenação de locks)
- [ ] Definir estratégia de memory ordering para cada atomic
- [ ] Planejar cleanup e shutdown seguro
- [ ] Avaliar se lock-free é realmente necessário
```

### 2.2 Implementação Checklist

```markdown
### Implementação
- [ ] Usar RAII para todos os locks (lock_guard, scoped_lock)
- [ ] Usar atomic para flags e contadores simples
- [ ] Usar memory_order correto (não seq_cst por preguiça)
- [ ] Tratar exceções dentro de threads
- [ ] Garantir join/detach em todas as threads
- [ ] Usar std::scoped_lock para múltiplos mutexes
- [ ] Evitar locks durante I/O
- [ ] Usar predicados com condition_variable
- [ ] Verificar se código é reentrant
```

### 2.3 Testing Checklist

```markdown
### Testing
- [ ] Compilar com ThreadSanitizer
- [ ] Rodar stress test com múltiplas threads
- [ ] Testar cenários de race condition específicos
- [ ] Verificar com helgrind/DRD
- [ ] Fuzzing com threads
- [ ] Testar cenários de erro e exceção
- [ ] Testar cleanup e shutdown
```

### 2.4 Performance Checklist

```markdown
### Performance
- [ ] Evitar false sharing (padding em contadores)
- [ ] Minimizar seções críticas
- [ ] Usar read-write locks quando apropriado
- [ ] Medir antes de otimizar
- [ ] Verificar escalabilidade com mais threads
- [ ] Profile lock contention
- [ ] Considerar NUMA para aplicações high-performance
```

---

## 3. Anti-Padrões e Suas Correções

### 3.1 Double-Checked Locking (Broken)

```cpp
#include <memory>
#include <mutex>
#include <iostream>

// ANTI-PADRÃO — broken em C++11 sem atomic
class BrokenSingleton {
    static BrokenSingleton* instance_;
    static std::mutex mutex_;
public:
    static BrokenSingleton* get() {
        if (!instance_) {                    // Check 1 (sem lock)
            std::lock_guard<std::mutex> lock(mutex_);
            if (!instance_) {                // Check 2 (com lock)
                instance_ = new BrokenSingleton();  // Publicação incompleta!
            }
        }
        return instance_;
    }
};

// CORRETO — usar std::call_once ou static local
class CorrectSingleton {
public:
    static CorrectSingleton& get() {
        static CorrectSingleton instance;  // Thread-safe em C++11+
        return instance;
    }
};
```

### 3.2 Mutex Durante I/O

```cpp
#include <mutex>
#include <fstream>
#include <iostream>

std::mutex log_mutex;

// ANTI-PADRÃO
void slow_logging(const std::string& msg) {
    std::lock_guard<std::mutex> lock(log_mutex);
    std::ofstream file("log.txt", std::ios::app);
    file << msg << "\n";  // I/O bloqueia todas as threads!
    file.close();
}

// CORRETO — buffer thread-local + batch write
void fast_logging(const std::string& msg) {
    thread_local std::string buffer;
    buffer += msg + "\n";
    
    if (buffer.size() > 4096) {
        std::lock_guard<std::mutex> lock(log_mutex);
        std::ofstream file("log.txt", std::ios::app);
        file << buffer;
        buffer.clear();
    }
}
```

### 3.3 Spurious Wakeup Ignorance

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>

std::mutex mtx;
std::condition_variable cv;
std::queue<int> data_queue;
bool shutdown = false;

// ANTI-PADRÃO
void wait_wrong() {
    std::unique_lock lock(mtx);
    cv.wait(lock);  // Pode acordar sem motivo!
}

// CORRETO — sempre com predicado
void wait_correct() {
    std::unique_lock lock(mtx);
    cv.wait(lock, [] { return !data_queue.empty() || shutdown; });
}
```

### 3.4 Holding Lock During Long Operations

```cpp
#include <mutex>
#include <vector>
#include <algorithm>
#include <numeric>

std::mutex mtx;
std::vector<int> shared_data(1000000);

// ANTI-PADRÃO — lock durante operação custosa
void process_wrong() {
    std::lock_guard<std::mutex> lock(mtx);
    // Operação O(n²) com lock!
    for (size_t i = 0; i < shared_data.size(); ++i) {
        for (size_t j = i + 1; j < shared_data.size(); ++j) {
            if (shared_data[i] > shared_data[j]) {
                std::swap(shared_data[i], shared_data[j]);
            }
        }
    }
}

// CORRETO — trabalho pesado fora do lock
void process_correct() {
    std::vector<int> local_copy;
    {
        std::lock_guard<std::mutex> lock(mtx);
        local_copy = shared_data;  // Cópia rápida
    }
    
    // Trabalho pesado sem lock
    std::sort(local_copy.begin(), local_copy.end());
    
    {
        std::lock_guard<std::mutex> lock(mtx);
        shared_data = local_copy;  // Atualização rápida
    }
}
```

### 3.5 Forgetting to Notify

```cpp
#include <mutex>
#include <condition_variable>
#include <queue>
#include <string>

std::mutex mtx;
std::condition_variable cv;
std::queue<std::string> tasks;

// ANTI-PADRÃO — esquecer de notificar
void submit_wrong(std::string task) {
    {
        std::lock_guard<std::mutex> lock(mtx);
        tasks.push(std::move(task));
    }
    // cv.notify_one() esquecido! Worker pode dormir para sempre
}

// CORRETO
void submit_correct(std::string task) {
    {
        std::lock_guard<std::mutex> lock(mtx);
        tasks.push(std::move(task));
    }
    cv.notify_one();  // Sempre notificar após modificar estado
}
```

---

## 4. Tabela de Decisão: Qual Primitiva Usar?

| Cenário | Solução Recomendada | Alternativa |
|---------|---------------------|-------------|
| Contador simples entre threads | `std::atomic<int>` | `std::atomic<long long>` |
| Flag de sinalização | `std::atomic<bool>` + `wait/notify` | `std::condition_variable` |
| Dados complexos com leituras frequentes | `std::shared_mutex` | Copy-on-Write |
| Dados complexos com escritas frequentes | `std::mutex` | Lock-free se performance crítica |
| Sincronização de N threads (one-shot) | `std::latch` | `std::barrier` com N iterações |
| Sincronização de N threads (reutilizável) | `std::barrier` | `std::condition_variable` |
| Limitar concorrência | `std::counting_semaphore` | Thread pool |
| Aguardar condição | `std::condition_variable` | `std::atomic::wait` |
| Dados sem locking (read-mostly) | `std::atomic<std::shared_ptr<T>>` | RCU |
| Task scheduling | `std::async` ou thread pool | `std::jthread` |
| Cancellation | `std::stop_token` | Flag atômica |
| Producer-consumer simples | `std::condition_variable` | `std::counting_semaphore` |
| Producer-consumer high-throughput | Lock-free queue | Bounded queue |

---

## 5. Memory Order Reference

| Order | Semântica | Uso Típico | Custo x86 |
|-------|-----------|------------|-----------|
| `relaxed` | Apenas atomicidade | Contadores, estatísticas | Zero |
| `acquire` | Previne reordenação posterior | Ler dados publicados | Leve |
| `release` | Previne reordenação anterior | Publicar dados | Leve |
| `acq_rel` | Combine acquire + release | RMW operations | Médio |
| `seq_cst` | Ordem total global | Padrão quando não sabe | Maior |
| `consume` | Dependência de dados | Descontinuado | N/A |

### Quando usar cada memory order:

```cpp
// relaxed: contadores sem dependência
std::atomic<int> hits{0};
hits.fetch_add(1, std::memory_order_relaxed);

// acquire/release: message passing
std::atomic<bool> ready{false};
int data = 0;

// Producer
data = 42;
ready.store(true, std::memory_order_release);

// Consumer
while (!ready.load(std::memory_order_acquire)) {}
// data é garantidamente 42

// acq_rel: read-modify-write com sincronização
std::atomic<int> counter{0};
counter.fetch_add(1, std::memory_order_acq_rel);

// seq_cst: quando não tem certeza
std::atomic<int> x{0};
x.store(1);  // default seq_cst
```

---

## 6. Referências Rápidas

### Compiladores e Flags

```bash
# GCC/Clang — build seguro
g++ -std=c++20 -pthread -O2 -g -Wall -Wextra -Wpedantic

# Com sanitizers
g++ -std=c++20 -pthread -fsanitize=thread,address,undefined -g

# Release com otimizações
g++ -std=c++20 -pthread -O3 -DNDEBUG -march=native
```

### Ferramentas Essenciais

| Ferramenta | Uso | Instalação |
|------------|-----|------------|
| ThreadSanitizer | Data races | `-fsanitize=thread` |
| Helgrind | Race conditions | `valgrind --tool=helgrind` |
| CDSChecker | Model checking | github.com/ucecserc/CDSChecker |
| rr | Record/replay | `apt install rr` |
| perf | Profiling | `apt install linux-tools-common` |
| GDB | Debugging | `apt install gdb` |

### Links Úteis

- **cppreference.com** — std::thread, std::atomic, std::mutex
- **C++ Core Guidelines** — Concurrency and Locking
- **ISO/IEC 14882:2020** — Thread support library
- **Herlihy & Shavit** — The Art of Multiprocessor Programming
- **Williams, A.** — C++ Concurrency in Action, 2nd Ed
---

*[Capítulo anterior: 16 — Simd Gpu E Heterogeneo](16-simd-gpu-e-heterogeneo.md)*

