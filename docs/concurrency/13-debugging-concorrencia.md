---
layout: default
title: "13-debugging-concorrencia"
---

# Capítulo 13 — Debugging de Programas Concorrentes

## Objetivos de Aprendizado

1. Utilizar GDB para debugar programas multithreaded
2. Analisar core dumps com threads
3. Implementar logging thread-safe para diagnóstico
4. Aplicar determinism logging para reproduzir bugs
5. Usar ferramentas de replay para debugging determinístico

---

## 1. GDB para Multithreading

### 1.1 Setup e Comandos Essenciais

```bash
# Compilar com símbolos
g++ -std=c++20 -g -O0 -pthread code.cpp -o code_debug

# Executar no GDB
gdb ./code_debug
```

### 1.2 Comandos de Thread

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
        ++shared_counter;
        if (shared_counter == 500) {
            std::cout << "Thread " << id << " hit 500\n";
        }
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

```bash
# Comandos GDB essenciais:
(gdb) info threads                    # Lista todas as threads
(gdb) thread 2                        # Muda para thread 2
(gdb) thread apply all bt             # Backtrace de todas as threads
(gdb) thread apply all info locals    # Variáveis locais de todas
(gdb) break increment                 # Breakpoint em função
(gdb) thread 3 break increment        # Breakpoint só na thread 3
(gdb) watch shared_counter            # Watchpoint em variável
(gdb) set scheduler-locking on        # Bloqueia outras threads durante step
(gdb) thread find 0x7ffff7fc1700      # Encontra thread por endereço
(gdb) info threads 1-4                # Info de threads específicas
(gdb) thread 1 apply thread 2 call increment(99)  # Chama função em thread específica
```

---

## 2. Logging Thread-Safe

### 2.1 Logger com Níveis

```cpp
#include <mutex>
#include <iostream>
#include <thread>
#include <chrono>
#include <sstream>
#include <vector>
#include <iomanip>
#include <string>

enum class LogLevel { DEBUG, INFO, WARNING, ERROR, FATAL };

class ThreadSafeLogger {
    std::mutex mutex_;
    LogLevel min_level_;
    
    static const char* level_str(LogLevel level) {
        switch (level) {
            case LogLevel::DEBUG:   return "DEBUG";
            case LogLevel::INFO:    return "INFO ";
            case LogLevel::WARNING: return "WARN ";
            case LogLevel::ERROR:   return "ERROR";
            case LogLevel::FATAL:   return "FATAL";
        }
        return "?????";
    }
    
    static const char* level_color(LogLevel level) {
        switch (level) {
            case LogLevel::DEBUG:   return "\033[36m";
            case LogLevel::INFO:    return "\033[32m";
            case LogLevel::WARNING: return "\033[33m";
            case LogLevel::ERROR:   return "\033[31m";
            case LogLevel::FATAL:   return "\033[1;31m";
        }
        return "\033[0m";
    }
    
public:
    ThreadSafeLogger(LogLevel min = LogLevel::INFO) : min_level_(min) {}
    
    void log(LogLevel level, int thread_id, const std::string& msg) {
        if (level < min_level_) return;
        
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        
        std::ostringstream oss;
        oss << "\033[0m"
            << std::put_time(std::localtime(&time), "%H:%M:%S.")
            << std::setfill('0') << std::setw(3)
            << std::chrono::duration_cast<std::chrono::milliseconds>(
                now.time_since_epoch()).count() % 1000
            << " " << level_color(level) << level_str(level)
            << " \033[34m[T" << thread_id << "]\033[0m "
            << msg << "\n";
        
        std::cout << oss.str();
    }
    
    template<typename... Args>
    void debug(int tid, Args&&... args) {
        std::ostringstream oss;
        ((oss << std::forward<Args>(args)), ...);
        log(LogLevel::DEBUG, tid, oss.str());
    }
    
    template<typename... Args>
    void info(int tid, Args&&... args) {
        std::ostringstream oss;
        ((oss << std::forward<Args>(args)), ...);
        log(LogLevel::INFO, tid, oss.str());
    }
    
    template<typename... Args>
    void warn(int tid, Args&&... args) {
        std::ostringstream oss;
        ((oss << std::forward<Args>(args)), ...);
        log(LogLevel::WARNING, tid, oss.str());
    }
    
    template<typename... Args>
    void error(int tid, Args&&... args) {
        std::ostringstream oss;
        ((oss << std::forward<Args>(args)), ...);
        log(LogLevel::ERROR, tid, oss.str());
    }
};

void worker(ThreadSafeLogger& logger, int id) {
    logger.info(id, "Starting work");
    
    for (int i = 0; i < 5; ++i) {
        logger.debug(id, "Processing item ", i);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        
        if (i == 3) {
            logger.warn(id, "Item ", i, " took longer than expected");
        }
    }
    
    logger.info(id, "Work complete");
}

int main() {
    ThreadSafeLogger logger(LogLevel::DEBUG);
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(worker, std::ref(logger), i);
    }
    for (auto& t : threads) t.join();
    
    return 0;
}
```

### 2.2 Structured Logging

```cpp
#include <mutex>
#include <iostream>
#include <thread>
#include <chrono>
#include <sstream>
#include <map>
#include <string>

class StructuredLogger {
    std::mutex mutex_;
    
public:
    void log_event(const std::string& event_type,
                   const std::map<std::string, std::string>& fields) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto now = std::chrono::system_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()).count();
        
        std::ostringstream oss;
        oss << "{\"timestamp\":" << ms
            << ",\"event\":\"" << event_type << "\"";
        
        for (const auto& [key, value] : fields) {
            oss << ",\"" << key << "\":\"" << value << "\"";
        }
        
        oss << ",\"thread_id\":\"" << std::this_thread::get_id() << "\"}";
        
        std::cout << oss.str() << "\n";
    }
};

int main() {
    StructuredLogger logger;
    
    logger.log_event("user_login", {{"user", "alice"}, {"ip", "192.168.1.1"}});
    logger.log_event("data_access", {{"table", "users"}, {"action", "read"}});
    logger.log_event("error", {{"code", "401"}, {"message", "unauthorized"}});
    
    return 0;
}
```

---

## 3. Deadlock Detection

### 3.1 Detecção com GDB

```cpp
#include <mutex>
#include <thread>
#include <iostream>

std::mutex mutex_a, mutex_b;

void thread_1() {
    std::lock_guard<std::mutex> lock_a(mutex_a);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> lock_b(mutex_b);  // DEADLOCK potential
}

void thread_2() {
    std::lock_guard<std::mutex> lock_b(mutex_b);
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    std::lock_guard<std::mutex> lock_a(mutex_a);  // DEADLOCK potential
}

int main() {
    std::thread t1(thread_1);
    std::thread t2(thread_2);
    t1.join(); t2.join();
    return 0;
}
```

```bash
# Detectar deadlock no GDB:
(gdb) info threads
  Id   Target Id          Frame
* 1    Thread 0x7ffff7fc1700 (LWP 12345) futex_wait_cancelable
  2    Thread 0x7ffff7fc1700 (LWP 12346) futex_wait_cancelable

(gdb) thread 2
(gdb) bt
#0  __lll_lock_wait () at lowlevellock.c:135
#1  0x00007ffff7a12345 in __pthread_mutex_lock
#2  0x0000555555555123 in thread_2 ()
#3  0x0000555555555234 in std::thread::_M_invoke
```

### 3.2 Detecção com ThreadSanitizer

```bash
TSAN_OPTIONS="detect_deadlocks=1 deadlock_timeout_ms=5000" ./code_tsan
```

---

## 4. Core Dump Analysis

```bash
# Habilitar core dumps
ulimit -c unlimited
echo "/tmp/core.%e.%p.%t" | sudo tee /proc/sys/kernel/core_pattern

# Compilar com símbolos
g++ -std=c++20 -g -O0 -pthread code.cpp -o code_debug

# Rodar (vai gerar core dump no crash)
./code_debug

# Analisar core dump
gdb ./code_debug /tmp/core.code_debug.12345

# Comandos úteis:
(gdb) info threads
(gdb) thread apply all bt full
(gdb) thread 1
(gdb) info locals
(gdb) print shared_data
(gdb) list
```

### 4.2 Análise de Stack

```cpp
#include <execinfo.h>
#include <iostream>
#include <thread>

void print_stacktrace() {
    void* callstack[128];
    int frames = backtrace(callstack, 128);
    char** symbols = backtrace_symbols(callstack, frames);
    for (int i = 0; i < frames; ++i) {
        std::cout << symbols[i] << "\n";
    }
    free(symbols);
}

void function_c() {
    std::cout << "In function_c:\n";
    print_stacktrace();
}

void function_b() { function_c(); }
void function_a() { function_b(); }

int main() {
    std::thread t(function_a);
    t.join();
    return 0;
}
```

---

## 5. Deterministic Replay

### 5.1 rr (Record and Replay)

```bash
# Gravar execução
rr record ./program

# Replay determinístico
rr replay

# Replay de um ponto específico
rr replay --goto <time>

# Listar eventos
rr dump --ticks > events.txt

# Análise de race condition
rr record ./program_with_race
rr replay --cpu 0
```

### 5.2 Seed Fixa para RNG

```cpp
#include <thread>
#include <random>
#include <functional>

thread_local std::mt19937 rng;

void deterministic_worker(int thread_id, std::function<void(int)> func) {
    rng.seed(thread_id * 12345 + 67890);
    func(thread_id);
}

int main() {
    std::vector<std::thread> threads;
    
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(deterministic_worker, i, [](int id) {
            for (int j = 0; j < 100; ++j) {
                int val = rng() % 1000;
                if (val < 0 || val >= 1000) {
                    std::cout << "ERROR in thread " << id << "\n";
                }
            }
        });
    }
    
    for (auto& t : threads) t.join();
    std::cout << "Deterministic test completed\n";
    return 0;
}
```

---

## 6. Ferramentas de Debugging

| Ferramenta | Tipo | Uso Principal |
|------------|------|---------------|
| GDB | Debugger | Análise interativa, breakpoints, watchpoints |
| ThreadSanitizer | Dinâmico | Data races, deadlocks |
| rr | Record/Replay | Reprodução determinística |
| Valgrind/Memcheck | Dinâmico | Memory leaks, invalid access |
| ASan | Dinâmico | Buffer overflow, use-after-free |
| perf | Profiling | Lock contention, scheduling |
| core dump | Forense | Análise pós-crash |

### 6.2 Script de Análise Automatizada

```python
#!/usr/bin/env python3
import subprocess
import sys

def analyze_core(core_file, executable):
    commands = [
        f"file {executable}",
        "info threads",
        "thread apply all bt full",
        "info signals"
    ]
    gdb_script = "\n".join(commands)
    
    proc = subprocess.run(
        ["gdb", "-batch", "-ex", gdb_script, executable, core_file],
        capture_output=True, text=True
    )
    
    print("=== GDB Analysis ===")
    print(proc.stdout)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python analyze_crash.py <core_file> <executable>")
        sys.exit(1)
    analyze_core(sys.argv[1], sys.argv[2])
```

---

## 7. Referências

- **GDB Documentation** — sourceware.org/gdb/documentation/
- **rr Debugger** — rr-project.org
- **Valgrind** — valgrind.org
- **Google Sanitizers** — github.com/google/sanitizers
- **Brendan Gregg** — Systems Performance (Pearson)
---

*[Capítulo anterior: 12 — Testando Codigo Concorrente](12-testando-codigo-concorrente.md)*
*[Próximo capítulo: 14 — Performance E Escalabilidade](14-performance-e-escalabilidade.md)*
