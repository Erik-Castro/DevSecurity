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

A **consistência sequencial** (sequential consistency) é o modelo mental mais intuitivo para programadores: as operações de todas as threads parecem executar em uma única ordem global, respeitando a ordem do programa em cada thread individual. Em um sistema sequencialmente consistente, se a thread A escreve `x = 1` e depois `y = 1`, e a thread B lê `y == 1` e depois lê `x`, a thread B **deve** observar `x == 1`.

```cpp
// Expectativa de consistência sequencial
// Thread A                          // Thread B
x = 1;                              // while (y == 0) { /* spin */ }
y = 1;                              // assert(x == 1); // Sempre passa em SC
```

No entanto, hardware moderno **não** fornece consistência sequencial por padrão. Processadores usam caches, *store buffers*, execução fora de ordem (*out-of-order execution*) e previsão de ramificação (*speculative execution*) para maximizar desempenho. Essas otimizações quebram a ilusão de execução sequencial.

### 1.2 A Ilusão de Execução Sequencial

Considere este código simples:

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

Em x86 (arquitetura *Total Store Order* - TSO), o `assert` **nunca** falha porque x86 garante que stores não são reordenados com outros stores. Mas em ARM, POWER, RISC-V e outras arquiteturas *weakly-ordered*, o processador pode reordenar `x = 1` e `y = 1`, fazendo com que a thread B veja `y == 1` mas `x == 0`.

### 1.3 Realidade do Hardware: Caches, Store Buffers, Execução Fora de Ordem

#### Caches e Coerência de Cache

Cada núcleo possui caches privados (L1, L2). Quando a thread A escreve em `x`, o valor vai para o cache do núcleo A. Outros núcleos não veem essa escrita imediatamente — precisam do protocolo de coerência de cache (MESI, MOESI) para invalid</think>
<tool_call>
<function=bash>