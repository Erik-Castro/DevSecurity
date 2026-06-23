# Capítulo 1 — Modelo de Memória C++ e Fundamentos de Concorrência

## Objetivos de Aprendizado

1. Compreender por que o modelo de memória C++ é fundamental para programas concorrentes corretos
2. Dominar as relações *sequenced-before*, *happens-before* e *synchronizes-with*
3. Aplicar corretamente os seis modos de ordenação de memória (`memory_order`)
4. Identificar e eliminar *data races* usando `std::atomic` e ferramentas de análise
5. Analisar vulnerabilidades reais causadas por falhas de ordenação de memória

---

## 1. Por que Modelo de Memória Importa

### 1.1 Consistência Sequencial vs Memória Relaxada

A **consistência sequencial** (sequential consistency) é o modelo mental mais intuitivo para programadores: as operações de todas as threads parecem executar em uma única ordem global, respeitando a ordem do programa em cada thread individual.

```cpp
// Expectativa de consistência sequencial
// Thread A                          // Thread B
x = 1;                              // while (y == 0) { /* spin */ }
y = 1;                              // assert(x == 1); // Sempre passa em SC
```

No entanto, hardware moderno **não** fornece consistência sequencial por padrão. Processadores usam caches, *store buffers*, execução fora de ordem e previsão de ramificação para maximizar desempenho.

### 1.2 A Ilusão de Execução Sequencial

```cpp
int x = 0, y = 0;

void thread_a() {
    x = 1;
    y = 1;
}

void thread_b() {
    while (y == 0) { /* spin */ }
    assert(x == 1); // Pode falhar!
}
```

Em x86 (arquitetura *Total Store Order* - TSO), o `assert` **nunca** falha porque x86 garante que stores não são reordenados com outros stores. Mas em ARM, POWER, RISC-V e outras arquiteturas *weakly-ordered*, o processador pode reordenar `x = 1` e `y = 1`.

### 1.3 Realidade do Hardware

#### Caches e Coerência de Cache

Cada núcleo possui caches privados (L1, L2). Quando a thread A escreve em `x`, o valor vai para o cache do núcleo A. Outros núcleos não veem essa escrita imediatamente — precisam do protocolo de coerência de cache (MESI, MOESI) para invalidar e sincronizar.

```
Cenário de Cache:
  Core 0: cache[x] = 1  ← Escrita visível apenas localmente
  Core 1: cache[x] = 0  ← Ainda vê valor antigo até invalidação
```

#### Store Buffers

Store buffers permitem que o processador continue executando após uma escrita, sem esperar a propagação completa. Isso cria uma janela onde outras threads podem ver valores desatualizados.

```
Thread A: Store x=1 → Store Buffer → Cache L1 → Coerência → Outros cores
                ↑
        Thread B pode ler x=0 neste ínterim
```

#### Execução Fora de Ordem

Compiladores e processadores reordenam instruções para maximizar ILP (Instruction-Level Parallelism). Sem barreiras de memória, reordenações podem quebrar invariantes de concorrência.

---

## 2. Modelo de Memória C++11/14/17/20

### 2.1 Relações Fundamentais

```cpp
// 1. Sequenced-before: ordem dentro de uma thread
// 2. Happens-before: ordem entre threads (transitiva)
// 3. Synchronizes-with: sincronização entre threads
```

### 2.2 Data Race: Definição Formal

Um **data race** ocorre quando duas threads acessam a mesma memória concorrentemente, pelo menos uma é uma escrita, e não há sincronização entre elas. Data races em C++ causam **comportamento indefinido (UB)**.

```cpp
// DATA RACE — comportamento indefinido!
int shared = 0;
void thread_a() { shared = 42; }
void thread_b() { shared = 43; }
```

**CVE-2017-18344**: O kernel Linux tinha um data race no timer subsystem que permitia acesso a memória não inicializada, resultando em vazamento de informações kernel para user space.

### 2.3 volatile NÃO é para Concorrência

```cpp
volatile int flag = 0;
int data = 0;
// Thread A
data = 42;
flag = 1;  // volatile garante visibilidade NÃO garante atomicidade
// Thread B
while (flag == 0) {}
// data pode ainda ser 0!
```

`volatile` em C++ previne otimizações do compilador mas **não** fornece barreiras de memória nem atomicidade. Use `std::atomic` para concorrência.

---

## 3. std::atomic em Profundidade

### 3.1 Operações Atômicas

```cpp
#include <atomic>
#include <thread>
#include <iostream>
#include <cassert>

void atomic_basics() {
    std::atomic<int> counter{0};
    
    counter.store(10, std::memory_order_relaxed);
    int val = counter.load(std::memory_order_acquire);
    
    int old = counter.fetch_add(1, std::memory_order_acq_rel);
    assert(old == 10);
    
    int expected = 11;
    bool success = counter.compare_exchange_strong(expected, 42, std::memory_order_acq_rel);
    assert(success);
    
    int prev = counter.exchange(0, std::memory_order_acq_rel);
    assert(prev == 42);
}

int main() {
    atomic_basics();
    std::cout << "All atomic operations passed\n";
    return 0;
}
```

### 3.2 compare_exchange_weak vs compare_exchange_strong

```cpp
#include <atomic>
#include <iostream>

void cas_comparison() {
    std::atomic<int> value{0};
    
    int expected = 0;
    bool success = value.compare_exchange_strong(expected, 1);
    // success = true, value = 1
    
    expected = 1;
    success = value.compare_exchange_weak(expected, 2);
    // Pode ser false MESMO SE value == 1
    
    int desired = 100;
    do {
        expected = value.load(std::memory_order_acquire);
    } while (!value.compare_exchange_weak(expected, desired,
        std::memory_order_release, std::memory_order_acquire));
    
    std::cout << "Value: " << value.load() << "\n";
}

int main() {
    cas_comparison();
    return 0;
}
```

---

## 4. Memory Orders em Detalhe

### 4.1 memory_order_relaxed

```cpp
#include <atomic>
#include <thread>
#include <vector>

std::atomic<int> counter{0};

void increment_relaxed() {
    for (int i = 0; i < 1000000; ++i) {
        counter.fetch_add(1, std::memory_order_relaxed);
    }
}

int main() {
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) threads.emplace_back(increment_relaxed);
    for (auto& t : threads) t.join();
    std::cout << "Counter: " << counter.load() << "\n";
    return 0;
}
```

### 4.2 memory_order_acquire/release

```cpp
#include <atomic>
#include <thread>
#include <iostream>

std::atomic<int> data{0};
std::atomic<bool> ready{false};

void producer() {
    data.store(42, std::memory_order_relaxed);
    ready.store(true, std::memory_order_release);
}

void consumer() {
    while (!ready.load(std::memory_order_acquire)) {}
    std::cout << "Data: " << data.load(std::memory_order_relaxed) << "\n";
}

int main() {
    std::thread t1(producer);
    std::thread t2(consumer);
    t1.join(); t2.join();
    return 0;
}
```

---

## 5. Casos Reais de Vulnerabilidades

### CVE-2019-11135 — TSX Async Abort
### CVE-2014-0160 — Heartbleed
### CVE-2016-0728 — Linux Kernel Keyring
### CVE-2017-18344 — Linux Kernel Timer Race

---

## 6. Referências

- **C++ Standard** — ISO/IEC 14882:2020
- **cppreference.com** — std::atomic, memory_order
- **Williams, A.** — C++ Concurrency in Action, 2nd Ed
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Fundamentos Threads Sincronizacao](02-fundamentos-threads-sincronizacao.md)*
