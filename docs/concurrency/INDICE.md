# Concorrência e Paralelismo Seguro em C++ — Índice do Livro

> **Modelo de Memória, Lock-Free, Padrões, Debugging, Performance, GPU**

---

## Sumário Rápido

| # | Capítulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefácio](00-prefacio.md) | Motivação, público-alvo, ambiente |
| 01 | [Modelo de Memória C++](01-modelo-memoria-cpp.md) | memory_order, happens-before, data races |
| 02 | [Threads, std::thread e Sincronização Básica](02-fundamentos-threads-sincronizacao.md) | std::thread, mutex, locks, C++20 primitives |
| 03 | [Programação Lock-Free](03-programacao-lock-free-e-atomicos.md) | CAS, ABA, hazard pointers, RCU |
| 04 | [Deadlocks, Livelocks e Starvation](04-deadlocks-e-livelocks.md) | Coffman, detecção, prevenção, starvation |
| 05 | [Thread Pools, std::async e Execução Assíncrona](05-thread-pools-tarefas-assincronas.md) | std::async, thread pools, executors |
| 06 | [Paralelismo](06-paralelismo-std-algorithms.md) | std::execution, par_unseq, OpenMP |
| 07 | [False Sharing, Cache Coherence e Otimização de Memória](07-false-sharing-e-otimizacao-cache.md) | Cache coherence, MESI, NUMA, pad |
| 08 | [Containers Concorrentes](08-containers-concorrentes.md) | Lock-free queues, hash maps, RCU |
| 09 | [Futures, Promises e Continuations em C++](09-futures-promises-continuacoes.md) | Async composition, when_all, pipelines |
| 10 | [Coroutines C++20](10-coroutines-cpp20.md) | co_await, generators, async tasks |
| 11 | [Primitivas de Sincronização Avançadas (C++20)](11-primitivas-sincronizacao-cpp20.md) | latch, barrier, semaphore, stop_token |
| 12 | [Testando Código Concorrente](12-testando-codigo-concorrente.md) | TSan, model checking, stress testing |
| 13 | [Debugging](13-debugging-concorrencia.md) | GDB, core dumps, logging, replay |
| 14 | [Performance e Escalabilidade](14-performance-e-escalabilidade.md) | Amdahl, profiling, NUMA tuning |
| 15 | [Padrões de Concorrência](15-padroes-concorrencia.md) | Actor, CSP, pipeline, fork-join |
| 16 | [SIMD, GPU e Computação Heterogênea](16-simd-gpu-e-heterogeneo.md) | AVX, CUDA, SYCL, OpenCL |
| 17 | [Boas Práticas](17-boas-praticas-e-guia-referencia.md) | Checklist, anti-padrões, referências |

---

## Diagrama de Dependências

```
         ┌─────┐
         │  00  │ Prefácio
         └──┬──┘
            │
         ┌──┴──┐
         │  01  │ ← Fundamento obrigatório
         └──┬──┘
            │
    ┌───────┼───────────────────────────┐
    │       │                           │
┌───┴──┐ ┌──┴──┐ ┌───┴───┐ ┌───┴───┐ ┌──┴──┐ ┌───┴───┐
│  02  │ │  03 │ │  04   │ │  05   │ │  06 │ │  07   │
│Threds│ │Lock │ │Deadlk │ │Pool   │ │Prall│ │Cache  │
└──┬───┘ │Free │ └───┬───┘ └───┬───┘ └──┬──┘ └───┬───┘
   │     └──┬──┘     │         │        │         │
   │        │     ┌──┴─────────┴────────┴─────────┘
   │        │     │
   │     ┌──┴─────┴──────────────────────────┐
   │     │  08  │  09  │ 10  │ 11  │ 15  │ 16 │
   │     │Contnr│Futures│Coro │Sync │Ptrn │SIMD│
   │     └──┬───┴──┬───┴──┬──┴──┬──┴──┬──┴──┬─┘
   │        │      │      │     │     │      │
   │     ┌──┴──────┴──────┴─────┴─────┴──────┘
   │     │
   │  ┌──┴──────────────────────┐
   │  │  12  │  13  │  14  │ 17 │
   │  │ Test │Debug │Perf  │Chkl│
   │  └──────┴──────┴──────┴────┘
   │
```

---

## Caminhos de Leitura por Perfil

### Para CORREÇÃO (eliminar bugs)
```
01 → 02 → 03 → 05 → 07 → 08 → 09 → 14 → 16
```

### Para PERFORMANCE (lock-free, scaling)
```
02 → 03 → 04 → 06 → 10 → 11 → 13 → 15
```

### Para SEGURANÇA (hardening, exploração)
```
01 → 02 → 07 → 08 → 09 → 14 → 16 → 17
```

### Para ARQUITETURA (design de sistemas)
```
04 → 10 → 11 → 12 → 13 → 17
```

---

## CVEs Documentados no Livro

| CVE | Título | Capítulo |
|-----|--------|----------|
| CVE-2016-0728 | Linux kernel keyring refcount | 03 |
| CVE-2017-18344 | Linux kernel timer race | 02 |
| CVE-2019-11135 | TSX Async Abort | 01 |
| CVE-2021-4034 | Polkit pkexec race | 01 |
| CVE-2014-0160 | Heartbleed | 01 |

---

## Ferramentas Recomendadas

| Ferramenta | Uso | Capítulos |
|------------|-----|-----------|
| ThreadSanitizer | Detecção de data races | 01, 03, 06, 12 |
| Helgrind/DRD | Race conditions (Valgrind) | 01, 12 |
| CDSChecker | Model checking atomics | 03, 12 |
| Nidhugg | Stateless model checking | 03, 12 |
| Intel VTune | Profiling threads/cache | 07, 14 |
| perf (Linux) | Profiling | 07, 14 |
| rr | Record/replay debugging | 13 |
| Google Benchmark | Microbenchmarking | 04, 14 |
