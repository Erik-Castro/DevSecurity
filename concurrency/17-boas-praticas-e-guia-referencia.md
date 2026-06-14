# Capítulo 17 — Boas Práticas e Guia de Referência

## Objetivos de Aprendizado

1. Consolidar os princípios fundamentais de concorrência segura em C++
2. Aplicar um checklist completo para revisão de código concorrente
3. Identificar e evitar anti-padrões comuns em código multithreaded
4. Construir uma cultura de qualidade em projetos com concorrência

---

## 1. Princípios Fundamentais

### Regra 1: Nunca confie em sua intuição sobre concorrência

```cpp
// ANTI-PADRÃO: "Isso provavelmente funciona"
int shared_counter = 0;

void increment() {
    shared_counter++;  // Não é atômico! Data race!
}
```

### Regra 2: Use ferramentas, não testing manual

```bash
# Sempre compile com TSan em desenvolvimento
g++ -std=c++20 -fsanitize=thread -g -O1 code.cpp -o code -pthread
```

### Regra 3: Se não pode provar que está correto, não está

Use model checking para código lock-free e atomics.

---

## 2. Checklist de Código Concorrente

### Design
- [ ] Identificar todos os dados compartilhados entre threads
- [ ] Definir estrutura de sincronização para cada dado compartilhado
- [ ] Documentar invariantes de cada estrutura thread-safe
- [ ] Verificar ausência de deadlocks (ordenação de locks)

### Implementação
- [ ] Usar RAII para todos os locks (lock_guard, scoped_lock)
- [ ] Usar atomic para flags e contadores simples
- [ ] Usar memory_order correto (não seq_cst por preguiça)
- [ ] Tratar exceções dentro de threads
- [ ] Garantir join/detach em todas as threads

### Testing
- [ ] Compilar com ThreadSanitizer
- [ ] Rodar stress test com múltiplas threads
- [ ] Testar cenários de race condition específicos
- [ ] Verificar com helgrind/DRD

### Performance
- [ ] Evitar false sharing (padding em contadores)
- [ ] Minimizar seções críticas
- [ ] Usar read-write locks quando apropriado
- [ ] Medir antes de otimizar

---

## 3. Anti-Padrões Comuns

### 3.1 Double-Checked Locking (Broken)

```cpp
// ANTI-PADRÃO — broken em C++11 sem atomic
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

// CORRETO — usar std::call_once ou static local
class SingletonCorrect {
public:
    static SingletonCorrect& get() {
        static SingletonCorrect instance;  // Thread-safe em C++11+
        return instance;
    }
};
```

### 3.2 Mutex During I/O

```cpp
// ANTI-PADRÃO
std::mutex mtx;
void log_slow(const std::string& msg) {
    std::lock_guard<std::mutex> lock(mtx);
    std::cout << msg << std::endl;  // I/O bloqueia todas as threads
}

// CORRETO
void log_fast(const std::string& msg) {
    thread_local std::ostringstream buffer;
    buffer << msg << "\n";
    
    if (buffer.tellp() > 4096) {
        std::lock_guard<std::mutex> lock(mtx);
        std::cout << buffer.str();
        buffer.str("");
        buffer.clear();
    }
}
```

### 3.3 Spurious Wakeup Ignorance

```cpp
// ANTI-PADRÃO
cv.wait(lock);  // Pode acordar sem motivo

// CORRETO
cv.wait(lock, [&]{ return ready; });  // Sempre com predicado
```

---

## 4. Tabela de Decisão: Qual Primitiva Usar?

| Cenário | Solução Recomendada |
|---------|---------------------|
| Contador simples entre threads | `std::atomic<int>` |
| Dados complexos com leituras frequentes | `std::shared_mutex` |
| Dados complexos com escritas frequentes | `std::mutex` |
| Sincronização de N threads | `std::latch` ou `std::barrier` |
| Limitar concorrência | `std::counting_semaphore` |
| Aguardar condição | `std::condition_variable` |
| Dados sem locking (read-mostly) | `std::atomic<std::shared_ptr<T>>` |
| Task scheduling | `std::async` ou thread pool |
| Cancellation | `std::stop_token` (C++20) |

---

## 5. Referências Rápidas

### Memory Orders

| Order | Uso | Garantia |
|-------|-----|----------|
| `seq_cst` | Padrão, mais forte | Ordem total |
| `acquire` | Ler dados escritos por release | Previne reordenação posterior |
| `release` | Publicar dados para leitores acquire | Previne reordenação anterior |
| `acq_rel` | Read-modify-write com sincronização | Combina acquire + release |
| `relaxed` | Contadores, estatísticas | Apenas atomicidade |
| `consume` | Dados dependentes | (Descontinuado, usar acquire) |

### Lock Performance

| Mutex | Uso | Throughput | Fairness |
|-------|-----|------------|----------|
| `std::mutex` | Uso geral | Médio |_fifo |
| `std::recursive_mutex` | Recursão | Baixo | FIFO |
| `std::shared_mutex` | Read-mostly | Alto | Depends |
| `std::timed_mutex` | Timeouts | Médio | FIFO |
| Spinlock | Baixa contenção | Muito alto | Não公平 |
| MCS lock | Alta contenção | Alto | Justo |

### Thread Sanitizer Quick Reference

```bash
# Compilar
clang++ -std=c++20 -fsanitize=thread -O1 -g code.cpp -o code -pthread

# Executar
TSAN_OPTIONS="halt_on_error=1 history_size=7" ./code

# Suppress known issues
TSAN_OPTIONS="suppressions=tsan_suppressions.txt" ./code

# Output example
# WARNING: ThreadSanitizer: data race
#   Write of size 4 at 0x...
#   Previous read of size 4 at 0x...
```
