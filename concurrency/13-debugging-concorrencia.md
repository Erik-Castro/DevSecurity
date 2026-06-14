# Capítulo 13 — Debugging de Programas Concorrentes

## Objetivos de Aprendizado

1. Utilizar GDB para debugar programas multithreaded
2. Analisar core dumps com threads
3. Implementar logging thread-safe para diagnóstico
4. Aplicar determinism logging para reproduzir bugs

---

## 1. GDB para Multithreading

```bash
# Compilar com símbolos de debug
g++ -std=c++20 -g -O0 -pthread code.cpp -o code_debug

# Executar no GDB
gdb ./code_debug
```

### 1.1 Comandos Essenciais

```bash
(gdb) info threads              # Lista todas as threads
(gdb) thread 2                  # Muda para thread 2
(gdb) thread apply all bt       # Backtrace de todas as threads
(gdb) thread apply all info locals  # Variáveis locais de todas as threads
(gdb) break main.cpp:42 thread 3  # Breakpoint só na thread 3
(gdb) watch shared_data         # Watchpoint em variável compartilhada
(gdb) set scheduler-locking on  # Impede otras threads durante step
(gdb) thread find 0x7ffff7fc1700  # Encontra thread por endereço
```

### 1.2 Exemplo Prático

```cpp
#include <thread>
#include <mutex>
#include <iostream>
#include <vector>

std::mutex mtx;
int shared_counter = 0;

void increment(int id) {
    for (int i = 0; i < 1000; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        ++shared_counter;  // Breakpoint aqui: "break increment"
    }
}

int main() {
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(increment, i);
    }
    for (auto& t : threads) t.join();
    std::cout << "Counter: " << shared_counter << "\n";
    return 0;
}
```

---

## 2. Logging Thread-Safe

```cpp
#include <mutex>
#include <iostream>
#include <thread>
#include <chrono>
#include <sstream>
#include <vector>

class ThreadSafeLogger {
    std::mutex mutex_;
    bool use_colors_;
    
    static const char* thread_color(int id) {
        static const char* colors[] = {
            "\033[31m", "\033[32m", "\033[33m", "\033[34m",
            "\033[35m", "\033[36m", "\033[1;31m", "\033[1;32m"
        };
        return colors[id % 8];
    }
    
public:
    ThreadSafeLogger(bool colors = false) : use_colors_(colors) {}
    
    template<typename... Args>
    void log(int thread_id, Args&&... args) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        
        std::ostringstream oss;
        oss << std::put_time(std::localtime(&time), "%H:%M:%S");
        
        if (use_colors_) {
            oss << " " << thread_color(thread_id) << "[T" << thread_id << "]\033[0m";
        } else {
            oss << " [T" << thread_id << "]";
        }
        
        ((oss << std::forward<Args>(args)), ...);
        oss << "\n";
        
        std::cout << oss.str();
    }
};

void worker(ThreadSafeLogger& logger, int id) {
    logger.log(id, "Starting work");
    std::this_thread::sleep_for(std::chrono::milliseconds(100 * id));
    logger.log(id, "Work complete");
}

int main() {
    ThreadSafeLogger logger(true);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(worker, std::ref(logger), i);
    }
    for (auto& t : threads) t.join();
    
    return 0;
}
```

---

## 3. Deadlock Detection com GDB

```bash
# Se programa travou (deadlock):
(gdb) info threads              # Ver threads bloqueadas
(gdb) thread apply all bt       # Backtrace completa
(gdb) print mutex               # Ver estado do mutex
(gdb) thread 1                  # Thread principal
(gdb) info args                 # Ver argumentos
(gdb) print *mutex.__data.__owner  # Dono do mutex (Linux)

# Usar ThreadSanitizer com deadlock detection:
export TSAN_OPTIONS="detect_deadlocks=1 deadlock_timeout_ms=5000"
```

---

## 4. Core Dump Analysis

```bash
# Habilitar core dumps
ulimit -c unlimited
echo "/tmp/core.%e.%p" | sudo tee /proc/sys/kernel/core_pattern

# Compilar
g++ -std=c++20 -g -O0 -pthread code.cpp -o code_debug

# Rodar (vai gerar core dump no crash)
./code_debug

# Analisar core dump
gdb ./code_debug /tmp/core.code_debug.12345
(gdb) info threads
(gdb) thread apply all bt full
(gdb) thread 1
(gdb) info locals
(gdb) print shared_data
```

---

## 5. Referências

- **GDB Documentation** — sourceware.org/gdb/documentation/
- **GDB Thread Debugging** — sourceware.org/gdb/onlinedocs/gdb/Threads.html
- **rr Debugger** — rr-project.org
- **Valgrind** — valgrind.org
- **Google Sanitizers** — github.com/google/sanitizers
