# Capítulo 02: Fundamentos de Constant-Time Programming

## Livro 5: Engenharia de Criptografia em C++

---

## Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

1. **Definir** programação constant-time com precisão formal e prática
2. **Identificar** como compiladores (GCC, Clang, MSVC) otimizam código constant-time de forma indesejada
3. **Classificar** os principais tipos de ataques de timing (local, remoto, cache-based)
4. **Implementar** comparações constant-time seguras em C++17
5. **Utilizar** técnicas de manipulação de bits para evitar branches secret-dependent
6. **Empregar** assembly intrinsics para x86-64 e ARM64 quando necessário
7. **Analisar** código usando Valgrind (Cachegrind, Massif) e perf counters
8. **Reconhecer** anti-patterns comuns que quebram constant-time
9. **Aplicar** o checklist de constant-time programming em projetos reais
10. **Compreender** CVEs reais (CVE-2019-1547, Lucky13, Minerva) e como teriam sido prevenidos

---

## 2.1 O que é Constant-Time? Definição Formal vs Prática

### 2.1.1 Definição Formal

Programação constant-time é uma **disciplina de implementação** que garante que o tempo de execução, consumo de memória e padrões de acesso a memória de um algoritmo criptográfico **não dependam de dados secretos** (chaves, textos cifrados em processamento, segredos de protocolo).

Definição formal (Costello, 2005):

> Um programa P executando sobre input `(d, s)`, onde `d` é dado público e `s` é segredo, é **constant-time** se e somente se:
> 1. Todo branch executado depende apenas de `d`, não de `s`
> 2. Todo índice de array acessado depende apenas de `d`, não de `s`
> 3. O número de iterações de loops depende apenas de `d`, não de `s`
> 4. O padrão de acesso a memória (sequencial vs aleatório) depende apenas de `d`, não de `s`

### 2.1.2 Definição Prática

Na prática, a definição se estende para incluir:

- **Constant-time em relação ao algoritmo completo**: não apenas operações atômicas, mas todo o fluxo de execução
- **Resistência a ataques de canal lateral**: incluindo power analysis, EM emanations, e timing
- **Independência de cache**: o padrão de cache hits/misses não deve revelar informação sobre dados secretos

### 2.1.3 O que NÃO é Constant-Time

Muitos programadores confundem "rápido" com "constant-time". Veja a tabela:

| Conceito | Definido por | Exemplo |
|----------|--------------|---------|
| Tempo médio baixo | Complexidade amortizada | HashMap lookup O(1) amortizado |
| Tempo fixo por iteração | Complexidade por iteração | Loop com corpo constante |
| **Constant-time criptográfico** | **Independência de input secreto** | **Todos os caminhos executados são idênticos** |

```cpp
// ESTE CÓDIGO NÃO É CONSTANT-TIME!
// Embora seja O(1) em média, revela informação via timing
bool naive_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        if (a[i] != b[i]) {
            return false;  // Early return revela posição do primeiro byte diferente
        }
    }
    return true;
}

// ESTE CÓDIGO É CONSTANT-TIME
// Sempre percorre todos os bytes, sem branches
bool constant_time_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t result = 0;
    for (size_t = 0; i < len; ++i) {
        result |= a[i] ^ b[i];
    }
    return result == 0;
}
```

### 2.1.4 Modelo de Amenaça

Programação constant-time pressupõe um **modelo de amenaça** específico:

```
Modelo de Amenação:
- Atacante pode medir tempo de execução com precisão (nanoseconds)
- Atacante pode executar o algoritmo muchas vezes com inputs diferentes
- Atacante não pode acessar memória diretamente (não é cold boot attack)
- Atacante pode compartilhar hardware (cache, branch predictor)
- Atacante pode escolher inputs público e observar output
```

---

## 2.2 Por que o Compilador é seu Inimigo

### 2.2.1 Otimizações que Quebram Constant-Time

Compiladores C/C++ tratam constant-time como um **efeito colateral**, não como objetivo. Eles aplicam otimizações legítimas que destroem invariantes de timing:

#### 2.2.1.1 Dead Code Elimination (DCE)

```cpp
// O compilador pode eliminar branches mortos
// Se só um caminho é possível, o outro some
void process_secret(uint8_t secret, uint8_t* output) {
    // Compilador com -O2 pode eliminar este branch
    if (secret & 0x01) {
        output[0] = 0xFF;
    } else {
        output[0] = 0x00;
    }
}
```

#### 2.2.1.2 Constant Folding e Propagation

```cpp
// O compilador resolve constantes em tempo de compilação
uint8_t key[] = {0x42, 0x73, 0x9A, 0xE1};
uint8_t derived = (key[0] ^ 0x42) & (key[1] ^ 0x73);
// Compilador resolve: (0x42 ^ 0x42) & (0x73 ^ 0x73) = 0x00
// O valor derived é constante - branch pode ser eliminado
if (derived) {
    // Este código pode ser eliminado como dead code
}
```

#### 2.2.1.3 Loop Unrolling

```cpp
// Compilador pode unroll o loop, alterando timing
void xor_block(uint8_t* out, const uint8_t* a, const uint8_t* b, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        out[i] = a[i] ^ b[i];
    }
    // Com -funroll-loops, o compilador pode:
    // 1. Processar 4/8 bytes por iteração
    // 2. Usar SIMD implicitamente
    // 3. Criar branches de alinhamento
}
```

#### 2.2.1.4 Vectorização (Auto-vectorization)

```cpp
// Compilador pode vectorizar, usando SSE/AVX
void constant_time_select(uint8_t* out, const uint8_t* a, 
                          const uint8_t* b, uint8_t selector, size_t len) {
    // Compilador pode transformar em:
    // if (selector) memcpy(out, a, len); else memcpy(out, b, len);
    // O que NÃO é constant-time!
    for (size_t i = 0; i < len; ++i) {
        out[i] = (selector & a[i]) | (~selector & b[i]);
    }
}
```

#### 2.2.1.5 Branch Prediction hints

```cpp
// Compilador pode adicionar hints ao branch predictor
void critical_path(bool condition) {
    if (__builtin_expect(condition, 1)) {  // likely
        // Branch predictor aprende este padrão
        // Timing fica diferente quando condition = false
    }
}
```

### 2.2.2 Mitigações do Compilador

#### 2.2.2.1 Volatile

```cpp
// volatile impede otimização mas NÃO garante constant-time
// Compilador pode gerar code que depende de cache
volatile uint8_t secret = 0x42;
volatile uint8_t result = 0;

// Este código NÃO é constant-time mesmo com volatile
result = (secret == 0x42) ? 1 : 0;
```

#### 2.2.2.2 Compiler Barriers

```cpp
// Compiler barrier impede reordering de instruções
#define COMPILER_BARRIER() asm volatile("" ::: "memory")

void constant_time_function(uint8_t secret) {
    uint8_t result = 0;
    
    result = secret ^ 0xFF;
    COMPILER_BARRIER();  // Impede que o compilador reordene
    
    result |= secret & 0x0F;
    COMPILER_BARRIER();
    
    // result é usado aqui
}
```

#### 2.2.2.3 Inline Assembly

```cpp
// Inline assembly garante instrução específica
uint8_t constant_time_select_asm(uint8_t a, uint8_t b, uint8_t selector) {
    uint8_t result;
    __asm__ __volatile__ (
        "movb %1, %0\n\t"
        "andb %2, %0\n\t"
        "movb %3, %%al\n\t"
        "andb %4, %%al\n\t"
        "orb %%al, %0\n\t"
        : "=&q"(result)
        : "q"(a), "q"(selector), "q"(b), "q"((uint8_t)~selector)
        : "rax"
    );
    return result;
}
```

#### 2.2.2.4 `__attribute__((noinline))` e `__attribute__((optimize("O0")))`

```cpp
// Força que a função não seja inlined e sem otimizações
__attribute__((noinline, optimize("O0")))
void sensitive_function(uint8_t* key, size_t key_len) {
    // O compilador não otimizará este código
    // Mas isso tem overhead significativo
}
```

### 2.2.3 Pragma de Compilador

```cpp
// Para GCC/Clang, desabilitar otimizações específicas
#ifdef __GNUC__
#pragma GCC optimize ("no-tree-loop-distribute-patterns")
#pragma GCC optimize ("no-loop-convert")
#endif

// Garantir que loops não sejam vectorizados
void constant_time_loop(uint8_t* data, size_t len) {
    #pragma GCC ivdep  // Impede vectorização
    for (size_t i = 0; i < len; ++i) {
        data[i] = data[i] ^ 0xFF;
    }
}
```

### 2.2.4 Tabela: O que cada otimização faz

| Otimização | Flag GCC | Efeito em Constant-Time | Risco |
|------------|----------|------------------------|-------|
| Dead Code Elimination | `-O1` | Elimina branches mortos | Alto |
| Constant Folding | `-O1` | Resolve constantes | Alto |
| Loop Unrolling | `-funroll-loops` | Muda padrão de execução | Médio |
| Auto-vectorization | `-ftree-vectorize` | Usa SIMD implicitamente | Alto |
| Inline Expansion | `-O2` | Remove overhead de chamada | Baixo |
| Tail Call Optimization | `-O2` | Transforma recursão em loop | Médio |
| Branch Prediction | `-fprofile-use` | Adapta padrão de branch | Alto |

---

## 2.3 Timing Attacks: Conceitos Fundamentais

### 2.3.1 Histórico

Ataques de timing foram descobertos por Paul Kocher em 1996. O conceito fundamental:

> Se o tempo de execução de um algoritmo criptográfico varia dependendo de dados secretos, um atacante pode extrair esses dados medindo o tempo de execução.

### 2.3.2 Tipos de Timing Attacks

#### 2.3.2.1 Ataques Locais

O atacante tem acesso ao sistema e pode medir tempo com precisão:

```cpp
// Exemplo de código vulnerável a timing attack local
bool verify_mac_local(const uint8_t* mac, const uint8_t* computed_mac, size_t len) {
    // Timing depende de onde os bytes diferem
    for (size_t i = 0; i < len; ++i) {
        if (mac[i] != computed_mac[i]) {
            return false;  // Retorna mais cedo se bytes diferem cedo
        }
    }
    return true;
}

// Medição de timing local
#include <chrono>
#include <vector>

std::vector<double> measure_local_timing(const uint8_t* target_mac, 
                                         size_t iterations) {
    std::vector<double> timings;
    timings.reserve(iterations);
    
    uint8_t test_mac[32];
    memset(test_mac, 0, 32);
    
    for (size_t i = 0; i < iterations; ++i) {
        // Variar o primeiro byte para forçar diferentes timings
        test_mac[0] = static_cast<uint8_t>(i);
        
        auto start = std::chrono::high_resolution_clock::now();
        verify_mac_local(target_mac, test_mac, 32);
        auto end = std::chrono::high_resolution_clock::now();
        
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
            end - start
        ).count();
        timings.push_back(static_cast<double>(duration));
    }
    
    return timings;
}
```

#### 2.3.2.2 Ataques Remotos (Network-based)

```cpp
// Timing attack via rede - protocolo TCP
// O atacante mede round-trip time (RTT) em cada tentativa
//
// Cenário: servidor verifica HMAC em cada requisição
// Atacante envia guesses do HMAC byte-a-byte
// RTT maior = byte correto (servidor processou mais)

#include <sys/socket.h>
#include <arpa/inet.h>
#include <chrono>

class RemoteTimingAttacker {
private:
    int socket_fd_;
    
    double measure_rtt(const uint8_t* guess, size_t guess_len) {
        auto send_time = std::chrono::high_resolution_clock::now();
        
        send(socket_fd_, guess, guess_len, 0);
        
        uint8_t response[1];
        recv(socket_fd_, response, 1, 0);
        
        auto recv_time = std::chrono::high_resolution_clock::now();
        
        return std::chrono::duration_cast<std::chrono::microseconds>(
            recv_time - send_time
        ).count();
    }
    
public:
    void attack(const uint8_t* partial_mac, size_t mac_len) {
        uint8_t guess[32] = {0};
        memcpy(guess, partial_mac, mac_len);
        
        // Para cada byte do MAC, testar todos os 256 valores
        for (size_t pos = mac_len; pos < 32; ++pos) {
            double best_time = 0;
            uint8_t best_byte = 0;
            
            for (int b = 0; b < 256; ++b) {
                guess[pos] = static_cast<uint8_t>(b);
                
                // Múltiplas medições para reduzir ruído
                std::vector<double> samples;
                for (int trial = 0; trial < 1000; ++trial) {
                    samples.push_back(measure_rtt(guess, pos + 1));
                }
                
                // Média das medições
                double avg_time = 0;
                for (double t : samples) avg_time += t;
                avg_time /= samples.size();
                
                if (avg_time > best_time) {
                    best_time = avg_time;
                    best_byte = static_cast<uint8_t>(b);
                }
            }
            
            guess[pos] = best_byte;
            // Byte encontrado com maior tempo = byte correto
        }
    }
};
```

### 2.3.3 Técnicas de Medição de Timing

#### 2.3.3.1 Clock do Processador (RDTSC/RDTSCP)

```cpp
#include <cstdint>
#include <vector>
#include <algorithm>
#include <numeric>

// Para x86-64
#ifdef __x86_64__
#include <immintrin.h>

inline uint64_t read_tsc() {
    _mm_mfence();           // Memory fence
    _mm_lfence();           // Load fence
    uint64_t tsc = __rdtsc();
    _mm_lfence();
    return tsc;
}

inline uint64_t read_tscp() {
    uint32_t aux;
    uint64_t tsc = __rdtscp(&aux);
    _mm_lfence();
    return tsc;
}
#endif

// Para ARM64
#ifdef __aarch64__
inline uint64_t read_cycle_counter() {
    uint64_t val;
    asm volatile("mrs %0, CNTVCT_EL0" : "=r"(val));
    return val;
}
#endif

class TimingMeasurement {
public:
    // Medição com calibração de overhead
    struct TimingResult {
        double mean_ns;
        double stddev_ns;
        double min_ns;
        double max_ns;
        uint64_t median_ns;
    };
    
    template<typename Func>
    static TimingResult measure(Func f, size_t iterations = 10000) {
        std::vector<uint64_t> measurements;
        measurements.reserve(iterations);
        
        for (size_t i = 0; i < iterations; ++i) {
            uint64_t start = read_tsc();
            f();
            uint64_t end = read_tsc();
            
            measurements.push_back(end - start);
        }
        
        // Ordenar para mediana e percentis
        std::sort(measurements.begin(), measurements.end());
        
        // Calcular média e stddev
        uint64_t sum = std::accumulate(measurements.begin(), 
                                        measurements.end(), 0ULL);
        double mean = static_cast<double>(sum) / measurements.size();
        
        double variance = 0;
        for (uint64_t m : measurements) {
            double diff = static_cast<double>(m) - mean;
            variance += diff * diff;
        }
        variance /= measurements.size();
        double stddev = std::sqrt(variance);
        
        TimingResult result;
        result.mean_ns = mean;
        result.stddev_ns = stddev;
        result.min_ns = static_cast<double>(measurements.front());
        result.max_ns = static_cast<double>(measurements.back());
        result.median_ns = measurements[measurements.size() / 2];
        
        return result;
    }
    
    // Calibração de overhead da medição
    static uint64_t calibrate_overhead() {
        auto result = measure([]() {}, 100000);
        return static_cast<uint64_t>(result.mean_ns);
    }
};
```

#### 2.3.3.2 Medição via `clock_gettime`

```cpp
#include <time.h>
#include <cstdint>

class ClockMeasurement {
public:
    static int64_t measure_ns(auto&& func) {
        struct timespec start, end;
        clock_gettime(CLOCK_MONOTONIC, &start);
        func();
        clock_gettime(CLOCK_MONOTONIC, &end);
        
        return (end.tv_sec - start.tv_sec) * 1000000000LL + 
               (end.tv_nsec - start.tv_nsec);
    }
};
```

### 2.3.4 Análise Estatística para Timing Attacks

```cpp
#include <vector>
#include <cmath>
#include <algorithm>

class TimingAnalyzer {
public:
    // Teste T de Student para comparar duas distribuições de timing
    static double t_test(const std::vector<double>& group1, 
                        const std::vector<double>& group2) {
        double n1 = group1.size();
        double n2 = group2.size();
        
        double mean1 = std::accumulate(group1.begin(), group1.end(), 0.0) / n1;
        double mean2 = std::accumulate(group2.begin(), group2.end(), 0.0) / n2;
        
        double var1 = 0, var2 = 0;
        for (double v : group1) var1 += (v - mean1) * (v - mean1);
        for (double v : group2) var2 += (v - mean2) * (v - mean2);
        var1 /= (n1 - 1);
        var2 /= (n2 - 1);
        
        double se = std::sqrt(var1/n1 + var2/n2);
        if (se == 0) return 0;
        
        return (mean1 - mean2) / se;
    }
    
    // Correlação de Pearson entre timing e guessed byte
    static double pearson_correlation(const std::vector<double>& x,
                                     const std::vector<double>& y) {
        size_t n = x.size();
        double sum_x = 0, sum_y = 0;
        for (size_t i = 0; i < n; ++i) {
            sum_x += x[i];
            sum_y += y[i];
        }
        double mean_x = sum_x / n;
        double mean_y = sum_y / n;
        
        double cov_xy = 0, var_x = 0, var_y = 0;
        for (size_t i = 0; i < n; ++i) {
            double dx = x[i] - mean_x;
            double dy = y[i] - mean_y;
            cov_xy += dx * dy;
            var_x += dx * dx;
            var_y += dy * dy;
        }
        
        double denom = std::sqrt(var_x * var_y);
        if (denom == 0) return 0;
        
        return cov_xy / denom;
    }
};
```

---

## 2.4 Cache-Timing Attacks

### 2.4.1 Hierarquia de Cache

```
┌─────────────────────────────────────┐
│           Registers                 │  ~0.3 ns
├─────────────────────────────────────┤
│           L1 Cache (32-64 KB)       │  ~1 ns
├─────────────────────────────────────┤
│           L2 Cache (256 KB-1 MB)    │  ~5 ns
├─────────────────────────────────────┤
│           L3 Cache (8-64 MB)        │  ~20 ns
├─────────────────────────────────────┤
│           Main Memory (GB)          │  ~100 ns
├─────────────────────────────────────┤
│           Disk (SSD/HDD)            │  ~10 us - 10 ms
└─────────────────────────────────────┘
```

Timing de cache access depende de:
1. Se o dado está em cache (hit) ou não (miss)
2. Nível do cache onde o dado está
3. Estado do cache (tempos de acesso variam)

### 2.4.2 Prime+Probe

Técnica onde o atacante:
1. **Prime**: Preenche um conjunto de cache com dados conhecidos
2. **Vitima executa**: Executa operação que acessa cache
3. **Probe**: Acessa os mesmos endereços e mede tempo

```cpp
// Implementação básica de Prime+Probe (simplificada)
// Requer acesso ao mesmo cache set que a vítima

#include <cstdint>
#include <vector>
#include <chrono>

class PrimeProbeAttack {
private:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t NUM_CACHE_SETS = 64;  // Assumindo 64 conjuntos
    
    // Buffer para mapear cache sets
    // Assumindo 8-way associative cache de 32KB L1
    uint8_t* probe_buffer_;
    size_t buffer_size_;
    
    void prime_cache_set(size_t set_index) {
        // Acessa todas as vias do conjunto
        volatile uint8_t* ptr = reinterpret_cast<volatile uint8_t*>(
            probe_buffer_ + set_index * CACHE_LINE_SIZE * 8
        );
        
        for (size_t i = 0; i < 8; ++i) {
            *ptr;  // Força o dado para cache
            ptr += CACHE_LINE_SIZE;
        }
    }
    
    bool probe_cache_set(size_t set_index) {
        uint64_t start = __rdtsc();
        
        volatile uint8_t* ptr = reinterpret_cast<volatile uint8_t*>(
            probe_buffer_ + set_index * CACHE_LINE_SIZE * 8
        );
        
        for (size_t i = 0; i < 8; ++i) {
            *ptr;
            ptr += CACHE_LINE_SIZE;
        }
        
        uint64_t end = __rdtsc();
        
        // Se houve cache miss, tempo será maior
        return (end - start) > THRESHOLD;
    }
    
    static constexpr uint64_t THRESHOLD = 100;  // Ciclos
    
public:
    PrimeProbeAttack() {
        buffer_size_ = NUM_CACHE_SETS * CACHE_LINE_SIZE * 8;
        posix_memalign(reinterpret_cast<void**>(&probe_buffer_), 
                       CACHE_LINE_SIZE, buffer_size_);
    }
    
    // Revela quais cache sets foram acessados pela vítima
    std::vector<bool> observe_victim_access(size_t victim_duration_ms) {
        // 1. Prime todos os conjuntos
        for (size_t set = 0; set < NUM_CACHE_SETS; ++set) {
            prime_cache_set(set);
        }
        
        // 2. Esperar a vítima executar
        // (em cenário real, a vítima executaria em paralelo)
        
        // 3. Probe e medir tempo
        std::vector<bool> evicted(NUM_CACHE_SETS, false);
        for (size_t set = 0; set < NUM_CACHE_SETS; ++set) {
            evicted[set] = probe_cache_set(set);
        }
        
        return evicted;
    }
};
```

### 2.4.3 Flush+Reload

Técnica que explora shared memory (ex: shared libraries):

```cpp
// Flush+Reload explora memória compartilhada
// Atacante e vítima compartilham o mesmo código/data
// via bibliotecas compartilhadas

#include <cstdint>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>

class FlushReloadAttack {
private:
    uint8_t* shared_memory_;
    size_t shared_size_;
    int shm_fd_;
    
public:
    // Inicializar memória compartilhada
    void init(const char* shm_name, size_t size) {
        shared_size_ = size;
        
        shm_fd_ = shm_open(shm_name, O_CREAT | O_RDWR, 0666);
        ftruncate(shm_fd_, shared_size_);
        
        shared_memory_ = static_cast<uint8_t*>(
            mmap(nullptr, shared_size_, PROT_READ | PROT_WRITE, 
                 MAP_SHARED, shm_fd_, 0)
        );
    }
    
    // Flush: remover linha de cache do conjunto específico
    void flush(size_t offset) {
        uint8_t* addr = shared_memory_ + offset;
        __asm__ __volatile__("clflush (%0)" : : "r"(addr) : "memory");
    }
    
    // Flush completo
    void flush_all() {
        for (size_t i = 0; i < shared_size_; i += 64) {
            flush(i);
        }
    }
    
    // Reload: medir tempo de acesso
    bool reload(size_t offset) {
        uint64_t start = __rdtsc();
        volatile uint8_t val = shared_memory_[offset];
        uint64_t end = __rdtsc();
        
        (void)val;  // Evitar warning
        
        // Cache hit < 100 ciclos, miss > 200 ciclos (tipicamente)
        return (end - start) < 100;
    }
    
    // Padrão de ataque completo
    struct AttackResult {
        size_t total_probes;
        size_t cache_hits;
        std::vector<size_t> hit_offsets;
    };
    
    AttackResult attack(size_t num_iterations) {
        AttackResult result;
        result.total_probes = 0;
        result.cache_hits = 0;
        
        std::vector<size_t> hit_counts(shared_size_ / 64, 0);
        
        for (size_t iter = 0; iter < num_iterations; ++iter) {
            // Flush todas as linhas
            flush_all();
            
            // Vítima executa (em paralelo)
            // victim_function();
            
            // Reload e medir
            for (size_t offset = 0; offset < shared_size_; offset += 64) {
                if (reload(offset)) {
                    hit_counts[offset / 64]++;
                    result.cache_hits++;
                }
                result.total_probes++;
            }
        }
        
        // Encontrar offsets com alta taxa de hits
        for (size_t i = 0; i < hit_counts.size(); ++i) {
            if (hit_counts[i] > num_iterations / 2) {
                result.hit_offsets.push_back(i * 64);
            }
        }
        
        return result;
    }
};
```

### 2.4.4 Evict+Time

Técnica que combina evição de cache com medição de tempo:

```cpp
// Evict+Time: evict cache lines e medir tempo de operação
class EvictTimeAttack {
private:
    uint8_t* evictor_buffer_;
    size_t evictor_size_;
    
    static constexpr size_t CACHE_SET_SIZE = 8;  // 8-way
    static constexpr size_t CACHE_LINE = 64;
    
public:
    EvictTimeAttack() {
        evictor_size_ = CACHE_SET_SIZE * CACHE_LINE * 1024;
        posix_memalign(reinterpret_cast<void**>(&evictor_buffer_),
                       CACHE_LINE, evictor_size_);
    }
    
    // Evict um conjunto de cache específico
    void evict_cache_set(size_t set_index) {
        for (size_t way = 0; way < CACHE_SET_SIZE; ++way) {
            volatile uint8_t* addr = reinterpret_cast<volatile uint8_t*>(
                evictor_buffer_ + (set_index + way * 1024) * CACHE_LINE
            );
            *addr;
        }
    }
    
    // Medir tempo de operação da vítima após evição
    double measure_victim_time(size_t set_to_evict, 
                               size_t iterations = 10000) {
        std::vector<double> timings;
        
        for (size_t i = 0; i < iterations; ++i) {
            // Evict o conjunto-alvo
            evict_cache_set(set_to_evict);
            
            // Medir tempo da vítima
            uint64_t start = __rdtsc();
            // victim_function();
            uint64_t end = __rdtsc();
            
            timings.push_back(static_cast<double>(end - start));
        }
        
        double sum = std::accumulate(timings.begin(), timings.end(), 0.0);
        return sum / timings.size();
    }
};
```

### 2.4.5 Tabela Comparativa: Ataques de Cache

| Ataque | Requisitos | Precisão | Custo | Mitigação |
|--------|-----------|----------|-------|-----------|
| Prime+Probe | Acesso ao mesmo core | Alta | Baixo | Prefetching, padronização |
| Flush+Reload | Shared memory | Muito Alta | Médio | clflush, disable SMT |
| Evict+Time | Shared cache (LLC) | Média | Baixo | Cache partitioning |
| Flush+Flush | clflush disponível | Alta | Médio | Restringir clflush |

---

## 2.5 Técnicas C++17 para Constant-Time

### 2.5.1 Constant-Time Comparison

#### 2.5.1.1 CRYPTO_memcmp (OpenSSL)

```cpp
#include <openssl/crypto.h>
#include <cstdint>
#include <cstddef>

// OpenSSL fornece comparação constante
bool verify_hmac_openssl(const uint8_t* expected, 
                          const uint8_t* computed, 
                          size_t len) {
    // CRYPTO_memcmp: O(n) sempre, sem branches
    int result = CRYPTO_memcmp(expected, computed, len);
    return result == 0;
}

// Implementação interna do OpenSSL (simplificada)
// Referência: crypto/cryptlib.c no OpenSSL
int crypto_memcmp_internal(const void* a, const void* b, size_t len) {
    const uint8_t* pa = static_cast<const uint8_t*>(a);
    const uint8_t* pb = static_cast<const uint8_t*>(b);
    uint8_t result = 0;
    
    for (size_t i = 0; i < len; ++i) {
        result |= pa[i] ^ pb[i];
    }
    
    return static_cast<int>(result);
}
```

#### 2.5.1.2 Implementação Manual com XOR

```cpp
#include <cstdint>
#include <cstddef>

// Implementação manual de comparação constante
bool constant_time_memcmp(const void* a, const void* b, size_t len) {
    const volatile uint8_t* pa = reinterpret_cast<const volatile uint8_t*>(a);
    const volatile uint8_t* pb = reinterpret_cast<const volatile uint8_t*>(b);
    uint8_t result = 0;
    
    for (size_t i = 0; i < len; ++i) {
        result |= pa[i] ^ pb[i];
    }
    
    // Garantir que o compilador não otimize esta comparação
    return result == 0;
}

// Versão otimizada usando uint64_t (8 bytes por iteração)
bool constant_time_memcmp_64(const void* a, const void* b, size_t len) {
    const uint64_t* pa = reinterpret_cast<const uint64_t*>(a);
    const uint64_t* pb = reinterpret_cast<const uint64_t*>(b);
    uint64_t result = 0;
    
    // Processar 8 bytes por iteração
    size_t i = 0;
    for (; i + 8 <= len; i += 8) {
        result |= pa[i/8] ^ pb[i/8];
    }
    
    // Processar bytes restantes
    const uint8_t* remaining_a = reinterpret_cast<const uint8_t*>(pa + i/8);
    const uint8_t* remaining_b = reinterpret_cast<const uint8_t*>(pb + i/8);
    uint8_t result_byte = 0;
    for (; i < len; ++i) {
        result_byte |= remaining_a[i] ^ remaining_b[i];
    }
    
    return (result | result_byte) == 0;
}

// Versão usando std::array (C++17)
#include <array>

template<size_t N>
bool constant_time_array_compare(const std::array<uint8_t, N>& a, 
                                  const std::array<uint8_t, N>& b) {
    uint8_t result = 0;
    for (size_t i = 0; i < N; ++i) {
        result |= a[i] ^ b[i];
    }
    return result == 0;
}
```

#### 2.5.1.3 Constant-Time Comparison com Memória Segura

```cpp
#include <cstdint>
#include <cstring>
#include <new>

// Comparação constante que não deixa resíduos em memória
class SecureConstantTimeCompare {
public:
    // Comparação com zeroing após uso
    static bool compare(const void* a, const void* b, size_t len) {
        // Alocar em memória não-swappable
        volatile uint8_t* result = new (std::nothrow) volatile uint8_t[1];
        if (!result) return false;
        
        *result = 0;
        
        const volatile uint8_t* pa = reinterpret_cast<const volatile uint8_t*>(a);
        const volatile uint8_t* pb = reinterpret_cast<const volatile uint8_t*>(b);
        
        for (size_t i = 0; i < len; ++i) {
            *result |= pa[i] ^ pb[i];
        }
        
        bool match = (*result == 0);
        
        // Zeroing seguro
        *result = 0;
        
        // Compiler barrier
        __asm__ __volatile__("" ::: "memory");
        
        delete[] result;
        return match;
    }
    
    // Comparação de strings constant-time
    static bool compare_strings(const std::string& a, const std::string& b) {
        if (a.size() != b.size()) {
            // TAMANHO diferente NÃO é constante-time
            // Em muitos protocolos, isso é aceitável
            // pois o tamanho não é secreto
            return false;
        }
        return compare(a.data(), b.data(), a.size());
    }
};
```

### 2.5.2 Constant-Time Conditional Select

```cpp
#include <cstdint>

// Seleção condicional constante-time
// Retorna a se selector != 0, b se selector == 0
// SEM branches, SEM data-dependent memory access

// Para uint8_t
inline uint8_t ct_select_u8(uint8_t selector, uint8_t a, uint8_t b) {
    // Máscara: 0xFF se selector != 0, 0x00 se selector == 0
    uint8_t mask = static_cast<uint8_t>(-static_cast<int64_t>(selector != 0));
    return (a & mask) | (b & ~mask);
}

// Para uint32_t
inline uint32_t ct_select_u32(uint32_t selector, uint32_t a, uint32_t b) {
    uint32_t mask = -static_cast<uint32_t>(selector != 0);
    return (a & mask) | (b & ~mask);
}

// Para uint64_t
inline uint64_t ct_select_u64(uint64_t selector, uint64_t a, uint64_t b) {
    uint64_t mask = -static_cast<uint64_t>(selector != 0);
    return (a & mask) | (b & ~mask);
}

// Para vetores (constante-time memcpy condicional)
void ct_select_bytes(uint8_t* dest, const uint8_t* a, const uint8_t* b,
                     uint8_t selector, size_t len) {
    uint8_t mask = static_cast<uint8_t>(-static_cast<int64_t>(selector != 0));
    
    for (size_t i = 0; i < len; ++i) {
        dest[i] = (a[i] & mask) | (b[i] & ~mask);
    }
}

// Template version
template<typename T>
T ct_select(bool condition, T true_val, T false_val) {
    // Usar -static_cast para gerar máscara sem branch
    T mask = -static_cast<T>(condition);
    return (true_val & mask) | (false_val & ~mask);
}

// Exemplo de uso: constant-time absolute value
int32_t ct_abs(int32_t x) {
    int32_t mask = x >> 31;  // Arithmetic shift: -1 se negativo, 0 se positivo
    return (x ^ mask) - mask;
}

// Exemplo: constant-time min/max
int32_t ct_min(int32_t a, int32_t b) {
    int32_t diff = a - b;
    int32_t mask = diff >> 31;  // -1 se a < b
    return b + (diff & mask);   // b + (a - b) se a < b, senão b
}

int32_t ct_max(int32_t a, int32_t b) {
    int32_t diff = a - b;
    int32_t mask = diff >> 31;
    return a - (diff & mask);
}
```

### 2.5.3 Constant-Time Arithmetic Without Branches

```cpp
#include <cstdint>
#include <limits>

// Constant-time addition (sem carry-out)
uint32_t ct_add(uint32_t a, uint32_t b) {
    return a + b;  // Soma é inerentemente constante-time em CPUs modernas
    // MAS overflow pode ser detectado via carry flag
    // Para truly constant-time, usar:
    return static_cast<uint32_t>(static_cast<uint64_t>(a) + b);
}

// Constant-time subtraction
uint32_t ct_sub(uint32_t a, uint32_t b) {
    return a - b;
}

// Constant-time multiplication (sem usar MUL/IMUL)
// Algoritmo de peasant multiplication
uint32_t ct_mul(uint32_t a, uint32_t b) {
    uint32_t result = 0;
    uint32_t temp_a = a;
    uint32_t temp_b = b;
    
    for (int i = 0; i < 32; ++i) {
        // Se bit i de b é 1, adicionar a << i
        uint32_t mask = -(temp_b & 1);
        result += (temp_a & mask);
        
        temp_a <<= 1;
        temp_b >>= 1;
    }
    
    return result;
}

// Constant-time division (binary long division)
// Retorna quociente
uint32_t ct_div(uint32_t dividend, uint32_t divisor) {
    uint32_t quotient = 0;
    uint32_t current = 0;
    
    for (int i = 31; i >= 0; --i) {
        current = (current << 1) | ((dividend >> i) & 1);
        
        // Se current >= divisor, subtrair e set bit do quociente
        uint32_t diff = current - divisor;
        uint32_t mask = -(~(diff >> 31));  // mask = 0xFFFFFFFF se diff >= 0
        
        current = (current & ~mask) | (diff & mask);
        quotient |= (static_cast<uint32_t>(1) << i) & mask;
    }
    
    return quotient;
}

// Constant-time modulo
uint32_t ct_mod(uint32_t dividend, uint32_t divisor) {
    uint32_t current = 0;
    
    for (int i = 31; i >= 0; --i) {
        current = (current << 1) | ((dividend >> i) & 1);
        
        uint32_t diff = current - divisor;
        uint32_t mask = -(~(diff >> 31));
        
        current = (current & ~mask) | (diff & mask);
    }
    
    return current;
}

// Constant-time square root (inteiro)
uint32_t ct_sqrt(uint32_t n) {
    if (n == 0) return 0;
    
    uint32_t result = 0;
    uint32_t bit = 1u << 30;  // Maior potência de 4 <= n
    
    while (bit > n) {
        bit >>= 2;
    }
    
    while (bit != 0) {
        if (n >= result + bit) {
            n -= result + bit;
            result = (result >> 1) + bit;
        } else {
            result >>= 1;
        }
        bit >>= 2;
    }
    
    return result;
}
```

### 2.5.4 Bit Manipulation Tricks

```cpp
#include <cstdint>

// Constant-time bit operations úteis em criptografia

// Verificar se um inteiro é zero (constante-time)
bool ct_is_zero(uint64_t x) {
    // De Morgan: x | -x terá MSB setado se x != 0
    // Isso funciona porque -x = ~x + 1
    return ((x | (-x)) >> 63) == 0;
}

// Verificar se dois valores são iguais (constante-time)
bool ct_eq(uint64_t a, uint64_t b) {
    // a ^ b = 0 se a == b
    return ct_is_zero(a ^ b);
}

// Verificar se a < b (constante-time, unsigned)
bool ct_lt(uint64_t a, uint64_t b) {
    // Se a < b, então a - b terá borrow
    return (a - b) >> 63;
}

// Verificar se a <= b (constante-time, unsigned)
bool ct_leq(uint64_t a, uint64_t b) {
    return ct_lt(a, b + 1);
}

// Constant-time conditional negate
// Retorna -x se condition é true, x se false
int64_t ct_negate(int64_t x, bool condition) {
    int64_t mask = -static_cast<int64_t>(condition);
    return (x ^ mask) + (mask & 1);
}

// Constant-time conditional swap
void ct_swap(uint64_t* a, uint64_t* b, bool condition) {
    uint64_t mask = -static_cast<uint64_t>(condition);
    uint64_t diff = (*a ^ *b) & mask;
    *a ^= diff;
    *b ^= diff;
}

// Contar bits setados (Hamming weight) constante-time
// Algoritmo de Brian Kernighan
uint8_t ct_popcount(uint64_t x) {
    uint64_t count = 0;
    for (int i = 0; i < 64; ++i) {
        count += (x >> i) & 1;
    }
    return static_cast<uint8_t>(count);
}

// Versão mais eficiente com bit manipulation
uint8_t ct_popcount_optimized(uint64_t x) {
    x = x - ((x >> 1) & 0x5555555555555555ULL);
    x = (x & 0x3333333333333333ULL) + ((x >> 2) & 0x3333333333333333ULL);
    x = (x + (x >> 4)) & 0x0F0F0F0F0F0F0F0FULL;
    return static_cast<uint8_t>((x * 0x0101010101010101ULL) >> 56);
}

// Constant-time leading zeros
uint8_t ct_clz(uint64_t x) {
    uint8_t count = 0;
    for (int i = 63; i >= 0; --i) {
        count += static_cast<uint8_t>((x >> i) & 1) ^ 1;
        if ((x >> i) & 1) break;
    }
    return count;
}

// Constant-time trailing zeros
uint8_t ct_ctz(uint64_t x) {
    uint8_t count = 0;
    for (int i = 0; i < 64; ++i) {
        count += static_cast<uint8_t>((x >> i) & 1) ^ 1;
        if ((x >> i) & 1) break;
    }
    return count;
}

// Constant-time rotate left
uint32_t ct_rotl32(uint32_t x, uint8_t shift) {
    shift &= 31;
    return (x << shift) | (x >> (32 - shift));
}

// Constant-time rotate right
uint32_t ct_rotr32(uint32_t x, uint8_t shift) {
    shift &= 31;
    return (x >> shift) | (x << (32 - shift));
}
```

### 2.5.5 Evitando Secret-Dependent Memory Access

```cpp
#include <cstdint>
#include <vector>
#include <array>

// PROBLEMA: Acesso a array com índice secreto
// Se secret_idx é secreto, o padrão de cache revela informação
void bad_secret_access(const uint8_t* table, size_t table_size, 
                       uint8_t secret_idx) {
    // Pattern de cache depende de secret_idx!
    uint8_t value = table[secret_idx];  // NON-CONSTANT-TIME
}

// SOLUÇÃO 1: Percorrer toda a tabela
void constant_time_table_lookup(const uint8_t* table, size_t table_size,
                                 uint8_t secret_idx, uint8_t* result) {
    uint8_t dummy = 0;
    *result = 0;
    
    for (size_t i = 0; i < table_size; ++i) {
        // Sempre acessa table[i], independente de secret_idx
        // Usa ct_select para条件选择
        uint8_t match = ct_eq_u8(static_cast<uint8_t>(i), secret_idx);
        *result = ct_select_u8(match, table[i], *result);
    }
}

// SOLUÇÃO 2: Lookup table constante-time (Feistel network)
class ConstantTimeLookupTable {
private:
    // Tamanho da tabela deve ser potência de 2
    static constexpr size_t TABLE_SIZE = 256;
    
    // Tabelas de Feistel
    std::array<uint8_t, TABLE_SIZE> f_table_;
    std::array<uint8_t, TABLE_SIZE> f_inv_table_;
    
    // Feistel: permutação constante-time
    uint8_t feistel_permute(uint8_t input, bool invert) {
        const auto& table = invert ? f_inv_table_ : f_table_;
        
        uint8_t left = input >> 4;
        uint8_t right = input & 0x0F;
        
        for (int i = 0; i < 4; ++i) {
            uint8_t new_right = left ^ table[right];
            left = right;
            right = new_right;
        }
        
        return (left << 4) | right;
    }
    
public:
    ConstantTimeLookupTable() {
        // Inicializar tabelas de Feistel com valores pseudo-aleatórios
        // Na prática, usar seed fixa ou chave
        for (size_t i = 0; i < TABLE_SIZE; ++i) {
            f_table_[i] = static_cast<uint8_t>(i);
        }
        // Embaralhar usando Feistel
        // (implementação omitida por brevidade)
    }
    
    // Lookup constante-time
    uint8_t lookup(uint8_t index) const {
        return f_table_[index];
    }
    
    // Lookup com valor secreto
    uint8_t secure_lookup(uint8_t secret_index) const {
        // Percorrer a tabela inteira
        uint8_t result = 0;
        for (uint8_t i = 0; i < TABLE_SIZE; ++i) {
            uint8_t match = ct_eq_u8(i, secret_index);
            result = ct_select_u8(match, f_table_[i], result);
        }
        return result;
    }
};

// Helper: equality check para uint8_t
uint8_t ct_eq_u8(uint8_t a, uint8_t b) {
    uint16_t diff = static_cast<uint16_t>(a) ^ static_cast<uint16_t>(b);
    // diff == 0 se a == b
    return static_cast<uint8_t>((-(static_cast<int>(diff == 0))) & 0xFF);
}

// SOLUÇÃO 3: Usar SIMD para lookup constante-time
#ifdef __SSE2__
#include <emmintrin.h>

class SIMDConstantTimeLookup {
public:
    static __m128i ct_select_bytes_simd(__m128i selector, 
                                         __m128i true_val,
                                         __m128i false_val) {
        // selector deve ser 0x00 ou 0xFF em cada byte
        __m128i mask = selector;
        return _mm_or_si128(_mm_and_si128(mask, true_val),
                           _mm_andnot_si128(mask, false_val));
    }
    
    // Lookup de 16 bytes simultaneamente
    static void ct_lookup_16(const uint8_t* table, size_t table_size,
                              const uint8_t* indices, uint8_t* results) {
        for (size_t i = 0; i < table_size; i += 16) {
            __m128i table_vec = _mm_loadu_si128(
                reinterpret_cast<const __m128i*>(table + i)
            );
            
            for (size_t j = 0; j < 16; ++j) {
                __m128i idx_vec = _mm_set1_epi8(indices[j]);
                __m128i match = _mm_cmpeq_epi8(idx_vec, 
                    _mm_set1_epi8(static_cast<char>(i + j)));
                
                __m128i result_vec = _mm_loadu_si128(
                    reinterpret_cast<const __m128i*>(results)
                );
                result_vec = ct_select_bytes_simd(match, table_vec, result_vec);
                _mm_storeu_si128(reinterpret_cast<__m128i*>(results), result_vec);
            }
        }
    }
};
#endif
```

### 2.5.6 Evitando Secret-Dependent Branches

```cpp
#include <cstdint>

// PROBLEMA: Branch baseado em dado secreto
void bad_secret_branch(uint8_t secret, uint8_t* output) {
    if (secret & 0x80) {      // Branch secret-dependent!
        output[0] = 0xFF;
    } else {
        output[0] = 0x00;
    }
}

// SOLUÇÃO: Usar operações bitwise
void good_constant_time(uint8_t secret, uint8_t* output) {
    // Máscara: 0xFF se bit 7 setado, 0x00 caso contrário
    uint8_t mask = -(secret >> 7);
    output[0] = mask;  // Constant-time!
}

// Exemplo avançado: constante-time sorting network
// Sort de 4 elementos usando sorting network
void ct_sort_4(int32_t values[4]) {
    // Comparação e swap constante-time
    #define CT_COMPARE_SWAP(a, b) do { \
        int32_t diff = (a) - (b); \
        int32_t mask = diff >> 31; \
        int32_t min_val = (b) + (diff & mask); \
        int32_t max_val = (a) - (diff & mask); \
        (a) = min_val; \
        (b) = max_val; \
    } while(0)
    
    // Bitonic sorting network para 4 elementos
    CT_COMPARE_SWAP(values[0], values[1]);
    CT_COMPARE_SWAP(values[2], values[3]);
    CT_COMPARE_SWAP(values[0], values[2]);
    CT_COMPARE_SWAP(values[1], values[3]);
    CT_COMPARE_SWAP(values[1], values[2]);
    
    #undef CT_COMPARE_SWAP
}

// Exemplo: constante-time binary search
// Retorna 1 se found, 0 se not found
// Pos do match está em *result_pos
int ct_binary_search(const int32_t* sorted_array, size_t len,
                     int32_t target, size_t* result_pos) {
    int32_t lo = 0;
    int32_t hi = static_cast<int32_t>(len) - 1;
    int32_t found = 0;
    size_t pos = 0;
    
    for (int i = 0; i < 32; ++i) {  // Max 32 iterações para 32-bit int
        int32_t mid = lo + ((hi - lo) >> 1);
        uint64_t mask_lo = static_cast<uint64_t>(lo <= hi);
        
        // Se lo > hi, mid é inválido, mas continuamos
        int32_t mid_val = sorted_array[mid & (static_cast<int32_t>(len) - 1)];
        
        int32_t cmp = target - mid_val;
        uint64_t match = static_cast<uint64_t>(cmp == 0);
        uint64_t less = static_cast<uint64_t>(cmp > 0);
        
        found |= static_cast<int32_t>(match);
        pos = static_cast<size_t>(mid) & (-static_cast<size_t>(match));
        
        lo = lo + ((mid + 1 - lo) & less);
        hi = hi - ((hi - (mid - 1)) & (1 - less));
        lo = lo & (-static_cast<int32_t>(mask_lo));
        hi = hi & (-static_cast<int32_t>(mask_lo));
    }
    
    *result_pos = pos;
    return static_cast<int>(found);
}
```

---

## 2.6 Assembly Intrinsics para Constant-Time

### 2.6.1 x86-64: Instruções Essenciais

```cpp
#include <cstdint>
#include <immintrin.h>

// CMOV: Conditional Move (constante-time select)
uint64_t ct_select_x64(uint64_t condition, uint64_t true_val, uint64_t false_val) {
    uint64_t result;
    __asm__ __volatile__(
        "movq %1, %0\n\t"
        "testq %2, %2\n\t"
        "cmovnz %3, %0\n\t"
        : "=&r"(result)
        : "r"(false_val), "r"(condition), "r"(true_val)
        : "cc"
    );
    return result;
}

// Constant-time multiplication 64x64 -> 128 bits
void ct_mul128(uint64_t a, uint64_t b, uint64_t* hi, uint64_t* lo) {
    __asm__ __volatile__(
        "mulq %3"
        : "=a"(*lo), "=d"(*hi)
        : "a"(a), "r"(b)
        : "cc"
    );
    // NOTA: mulq pode ter timing variável em CPUs antigas
    // Em CPUs modernos (post-2010), mulq é constante-time
}

// Constant-time division (usando divq)
// NOTA: divq NÃO é constante-time em todas as CPUs!
// Usar apenas quando CPU suporta (post-Haswell)
bool ct_div64(uint64_t dividend, uint64_t divisor, 
              uint64_t* quotient, uint64_t* remainder) {
    if (divisor == 0) return false;
    
    uint64_t q, r;
    __asm__ __volatile__(
        "divq %4"
        : "=a"(q), "=d"(r)
        : "a"(dividend), "d"(0), "r"(divisor)
        : "cc"
    );
    
    *quotient = q;
    *remainder = r;
    return true;
}

// PSHUFB: Constant-time byte shuffle (AES-NI)
#ifdef __SSSE3__
#include <tmmintrin.h>

// Constant-time byte permutation
__m128i ct_shuffle_bytes(__m128i input, __m128i indices) {
    return _mm_shuffle_epi8(input, indices);
}
#endif

// AES-NI: Constant-time AES operations
#ifdef __AES__
#include <wmmintrin.h>

// Constant-time AES encryption round
__m128i ct_aes_encrypt(__m128i state, __m128i round_key) {
    return _mm_aesenc_si128(state, round_key);
}

// Constant-time AES decryption round
__m128i ct_aes_decrypt(__m128i state, __m128i round_key) {
    return _mm_aesdec_si128(state, round_key);
}

// Constant-time AES key expansion
__m128i ct_aes_keygen(__m128i key, __m128i keygen) {
    return _mm_aeskeygenassist_si128(key, keygen);
}

// Constant-time AES-NI based comparison
bool ct_aes_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    __m128i result = _mm_setzero_si128();
    
    for (size_t i = 0; i < len; i += 16) {
        __m128i va = _mm_loadu_si128(reinterpret_cast<const __m128i*>(a + i));
        __m128i vb = _mm_loadu_si128(reinterpret_cast<const __m128i*>(b + i));
        __m128i diff = _mm_xor_si128(va, vb);
        result = _mm_or_si128(result, diff);
    }
    
    // Verificar se result é zero
    __m128i cmp = _mm_cmpeq_epi8(result, _mm_setzero_si128());
    int mask = _mm_movemask_epi8(cmp);
    return mask == 0xFFFF;
}
#endif
```

### 2.6.2 ARM64: Instruções Essenciais

```cpp
#include <cstdint>

#ifdef __aarch64__

// ARM64: CSEL (Conditional Select)
uint64_t ct_select_arm64(uint64_t condition, uint64_t true_val, uint64_t false_val) {
    uint64_t result;
    __asm__ __volatile__(
        "cmp %2, #0\n\t"
        "csel %0, %1, %3, ne\n\t"
        : "=r"(result)
        : "r"(true_val), "r"(condition), "r"(false_val)
        : "cc"
    );
    return result;
}

// ARM64: Bit manipulation instructions

// CLZ (Count Leading Zeros) - constante-time
uint8_t ct_clz_arm64(uint64_t x) {
    uint64_t result;
    __asm__ __volatile__("clz %0, %1" : "=r"(result) : "r"(x));
    return static_cast<uint8_t>(result);
}

// REV (Reverse bytes) - constante-time
uint64_t ct_bswap64_arm64(uint64_t x) {
    uint64_t result;
    __asm__ __volatile__("rev %0, %1" : "=r"(result) : "r"(x));
    return result;
}

// EXTR (Extract) - para constant-time bit field extraction
uint64_t ct_bfi_arm64(uint64_t val, uint64_t bits, 
                       uint8_t lsb, uint8_t width) {
    uint64_t result;
    __asm__ __volatile__(
        "bfi %0, %1, %2, %3"
        : "=r"(result)
        : "r"(val), "r"(lsb), "r"(width)
    );
    return result;
}

// ARM64: SIMD (NEON) para constant-time operations
#ifdef __ARM_NEON
#include <arm_neon.h>

// Constant-time byte selection using NEON
uint8x16_t ct_select_neon(uint8x16_t selector, 
                           uint8x16_t true_val,
                           uint8x16_t false_val) {
    // selector deve ser 0x00 ou 0xFF em cada byte
    return vbslq_u8(selector, true_val, false_val);
}

// Constant-time AES using ARMv8 Crypto Extensions
#ifdef __ARM_FEATURE_CRYPTO
// ARMv8 hardware AES - constante-time por hardware
uint8x16_t ct_aes_arm64(uint8x16_t data, uint8x16_t key) {
    return vaeseq_u8(data, key);
}

uint8x16_t ct_aes_inv_arm64(uint8x16_t data, uint8x16_t key) {
    return vaesdq_u8(data, key);
}
#endif
#endif

#endif // __aarch64__
```

---

## 2.7 Constant-Time em OpenSSL

### 2.7.1 CRYPTO_memcmp

```cpp
// OpenSSL CRYPTO_memcmp - referência em crypto/cryptlib.c
// Fonte: OpenSSL 1.1.1+
//
// Esta função é usada internamente pelo OpenSSL para
// comparações de MAC, assinaturas, e outros dados sensíveis

#include <openssl/crypto.h>
#include <cstdint>
#include <cstddef>

// Implementação interna simplificada do OpenSSL
int CRYPTO_memcmp_internal(const void* in_a, const void* in_b, size_t len) {
    size_t i;
    uint8_t result;
    const volatile uint8_t *a = in_a, *b = in_b;
    
    result = 0;
    for (i = 0; i < len; i++) {
        result |= a[i] ^ b[i];
    }
    
    return result;
}

// USO CORRETO no OpenSSL:
// 1. Para verificar MAC
bool verify_hmac_with_openssl(const uint8_t* mac, 
                               const uint8_t* computed,
                               size_t mac_len) {
    return CRYPTO_memcmp(mac, computed, mac_len) == 0;
}

// 2. Para verificar assinatura
bool verify_signature_with_openssl(const uint8_t* sig,
                                    const uint8_t* expected,
                                    size_t sig_len) {
    return CRYPTO_memcmp(sig, expected, sig_len) == 0;
}
```

### 2.7.2 OPENSSL_cleanse

```cpp
#include <openssl/crypto.h>
#include <cstdint>
#include <cstddef>

// OPENSSL_cleanse: secure memory clearing
// Previne que compilador optimize away o memset

// O problema com memset:
void insecure_clear(uint8_t* buffer, size_t len) {
    memset(buffer, 0, len);  // Compilador pode eliminar!
    // Após memset, buffer pode conter dados antigos
    // se compiler decide que buffer não é usado depois
}

// A solução do OpenSSL:
void secure_clear_openssl(uint8_t* buffer, size_t len) {
    OPENSSL_cleanse(buffer, len);  // Não pode ser otimizado
}

// Implementação interna do OPENSSL_cleanse (simplificada)
// Referência: crypto/o_init.c
void OPENSSL_cleanse_internal(void* ptr, size_t len) {
    uint8_t* p = static_cast<uint8_t*>(ptr);
    volatile uint8_t* vp = p;
    
    while (len--) {
        *vp++ = 0;
    }
    
    // Compiler barrier adicional
    __asm__ __volatile__("" ::: "memory");
}

// Usando OPENSSL_cleanse em contexto real
class SecureBuffer {
private:
    uint8_t* data_;
    size_t size_;
    
public:
    SecureBuffer(size_t size) : size_(size) {
        data_ = new uint8_t[size];
    }
    
    ~SecureBuffer() {
        if (data_) {
            // Usar OPENSSL_cleanse em vez de memset
            OPENSSL_cleanse(data_, size_);
            delete[] data_;
        }
    }
    
    // Disable copy, enable move
    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;
    
    SecureBuffer(SecureBuffer&& other) noexcept 
        : data_(other.data_), size_(other.size_) {
        other.data_ = nullptr;
        other.size_ = 0;
    }
    
    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }
};
```

### 2.7.3 Padrões do OpenSSL para Constant-Time

```cpp
// OpenSSL usa vários padrões para garantir constant-time

// 1. O padrão "masked operations"
uint64_t openssl_ct_mask(uint64_t a, uint64_t b) {
    // Retorna 0xFF..F se a == b, 0 senão
    uint64_t diff = a ^ b;
    return -((diff | (-diff)) >> 63);
}

// 2. O padrão "conditional move"
uint64_t openssl_ct_select(uint64_t mask, uint64_t a, uint64_t b) {
    // mask deve ser 0 ou 0xFF..F
    return (a & mask) | (b & ~mask);
}

// 3. Evitar tabelas indexadas por dado secreto
// O OpenSSL usa Feistel networks ou bit-sliced implementations

// 4. Usar funções de comparação seguras
// Nunca usar memcmp() para dados sensíveis

// 5. Limpeza segura de memória
// Sempre usar OPENSSL_cleanse() ou sodium_memzero()
```

---

## 2.8 Constant-Time em libsodium

### 2.8.1 sodium_memcmp

```cpp
#include <sodium.h>
#include <cstdint>
#include <cstddef>

// libsodium fornece primitives constant-time robustas

// Comparação constante-time
bool compare_with_sodium(const uint8_t* a, const uint8_t* b, size_t len) {
    // sodium_memcmp retorna 0 se iguais, -1 caso contrário
    // SEMPRE percorre todo o buffer
    return sodium_memcmp(a, b, len) == 0;
}

// Inicializar libsodium (deve ser chamado antes de usar)
void init_sodium() {
    if (sodium_init() < 0) {
        // Tratar erro
    }
}
```

### 2.8.2 sodium_memzero

```cpp
#include <sodium.h>

// sodium_memzero: limpeza segura de memória
// Garante que o compilador NÃO otimize away

class SecureKey {
private:
    uint8_t key_[32];
    
public:
    SecureKey() {
        // Gerar chave aleatória
        randombytes_buf(key_, sizeof(key_));
    }
    
    ~SecureKey() {
        // Limpeza segura
        sodium_memzero(key_, sizeof(key_));
    }
    
    // Comparação segura
    bool operator==(const SecureKey& other) const {
        return sodium_memcmp(key_, other.key_, sizeof(key_)) == 0;
    }
};
```

### 2.8.3 Padrões do libsodium

```cpp
// libsodium é mais rigoroso que OpenSSL em constant-time

// 1. Todas as operações de chave usam crypto_scalarmult
//    que é constant-time por design

// 2. Comparações de MAC sempre usam sodium_memcmp
//    NUNCA memcmp

// 3. Limpeza sempre usa sodium_memzero
//    NUNCA memset

// 4. Validações de formato NÃO são constant-time
//    (tamanho, formato, etc. são públicos)

// Exemplo correto: verificar chave pública
bool verify_public_key(const uint8_t* key, size_t key_len) {
    // Verificação de formato NÃO precisa ser constante-time
    // pois formato é público
    if (key_len != crypto_sign_PUBLICKEYBYTES) {
        return false;
    }
    
    // Verificação de valor NÃO é necessária aqui
    // (chave pública é... pública)
    return true;
}

// Exemplo: verificar assinatura
bool verify_signature(const uint8_t* sig, size_t sig_len,
                       const uint8_t* msg, size_t msg_len,
                       const uint8_t* pk) {
    // Verificar tamanho da assinatura (público, não const-time)
    if (sig_len != crypto_sign_BYTES) {
        return false;
    }
    
    // Verificar assinatura (const-time)
    return crypto_sign_verify_detached(sig, msg, msg_len, pk) == 0;
}
```

---

## 2.9 Validação: Como Testar se Código é Realmente Constant-Time

### 2.9.1 Abordagem 1: Análise Manual

```cpp
// Checklist de código para análise manual
// [ ] Todos os branches são independentes de dados secretos
// [ ] Todos os acessos a array são independentes de dados secretos
// [ ] Nenhuma operação de divisão/módulo com dados secretos
// [ ] Nenhuma tabela lookup com índice secreto
// [ ] Memória sensível é limpa com OPENSSL_cleanse ou similar
// [ ] Não há early returns baseados em dados secretos
// [ ] Não há exceptions baseadas em dados secretos
```

### 2.9.2 Abordagem 2: Instrumentação com Valgrind

```cpp
// Valgrind (com Cachegrind) pode ser usado para detectar
// branches e acessos a memória dependentes de dados

// Compilar com debug info:
// g++ -O0 -g -o program program.cpp

// Rodar com Cachegrind:
// valgrind --tool=cachegrind ./program

// Analisar output:
// cg_annotate cachegrind.out.<pid>

// IMPORTANTE: Valgrind NÃO detecta constant-time diretamente
// Mas pode ser usado para verificar padrões de cache
```

### 2.9.3 Abordagem 3: Código de Verificação

```cpp
#include <cstdint>
#include <vector>
#include <cmath>
#include <random>
#include <chrono>

class ConstantTimeVerifier {
private:
    // Medir tempo de execução com diferentes inputs
    struct TimingSample {
        uint64_t time_ns;
        std::vector<uint8_t> input;
    };
    
    // Testar se função é constante-time
    // Retorna true se timing é constante (dentro de threshold)
    template<typename Func>
    static bool verify_constant_time(Func func, 
                                     size_t input_size,
                                     size_t num_samples = 10000) {
        std::vector<TimingSample> samples;
        std::mt19937 rng(42);
        
        // Gerar samples com inputs diferentes
        for (size_t i = 0; i < num_samples; ++i) {
            TimingSample sample;
            sample.input.resize(input_size);
            
            // Gerar input pseudo-aleatório
            for (auto& byte : sample.input) {
                byte = static_cast<uint8_t>(rng());
            }
            
            // Medir tempo
            auto start = std::chrono::high_resolution_clock::now();
            func(sample.input.data(), input_size);
            auto end = std::chrono::high_resolution_clock::now();
            
            sample.time_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
                end - start
            ).count();
            
            samples.push_back(sample);
        }
        
        // Analisar variação de timing
        double mean = 0;
        for (const auto& s : samples) {
            mean += s.time_ns;
        }
        mean /= samples.size();
        
        double variance = 0;
        for (const auto& s : samples) {
            double diff = s.time_ns - mean;
            variance += diff * diff;
        }
        variance /= samples.size();
        
        double stddev = std::sqrt(variance);
        
        // Threshold: stddev deve ser menor que 10% da média
        // (ajustar conforme necessário)
        double threshold = mean * 0.1;
        
        return stddev < threshold;
    }
    
public:
    // Testar comparação constante-time
    static bool verify_comparison() {
        auto func = [](const uint8_t* data, size_t len) {
            volatile uint8_t result = 0;
            for (size_t i = 0; i < len; ++i) {
                result |= data[i];
            }
        };
        
        return verify_constant_time(func, 32);
    }
    
    // Testar tabela lookup constante-time
    static bool verify_table_lookup() {
        static const uint8_t table[256] = { /* ... */ };
        
        auto func = [](const uint8_t* data, size_t) {
            volatile uint8_t result = table[data[0]];
            (void)result;
        };
        
        return verify_constant_time(func, 1);
    }
};
```

---

## 2.10 Perf Counters e Cache Line Analysis

### 2.10.1 Linux perf

```bash
# Medir ciclos e instructions
perf stat -e cycles,instructions,cache-misses,cache-references ./program

# Medir branches e branch misses
perf stat -e branches,branch-misses ./program

# Gravar perf data para análise
perf record -e cycles -g ./program
perf report

# Medir cache misses específicos
perf stat -e L1-dcache-load-misses,L1-dcache-loads ./program
```

### 2.10.2 Código com perf counters

```cpp
#include <cstdint>
#include <sys/ioctl.h>
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <unistd.h>

class PerfCounter {
private:
    int fd_;
    
    long perf_event_open(struct perf_event_attr* hw_event, pid_t pid,
                         int cpu, int group_fd, unsigned long flags) {
        return syscall(__NR_perf_event_open, hw_event, pid, cpu, 
                       group_fd, flags);
    }
    
public:
    PerfCounter(uint32_t type, uint64_t config) {
        struct perf_event_attr pe;
        memset(&pe, 0, sizeof(pe));
        pe.type = type;
        pe.size = sizeof(pe);
        pe.config = config;
        pe.disabled = 1;
        pe.exclude_kernel = 1;
        pe.exclude_hv = 1;
        
        fd_ = perf_event_open(&pe, 0, -1, -1, 0);
        if (fd_ == -1) {
            // Erro
        }
    }
    
    ~PerfCounter() {
        if (fd_ != -1) close(fd_);
    }
    
    void start() {
        ioctl(fd_, PERF_EVENT_IOC_RESET, 0);
        ioctl(fd_, PERF_EVENT_IOC_ENABLE, 0);
    }
    
    uint64_t stop() {
        ioctl(fd_, PERF_EVENT_IOC_DISABLE, 0);
        uint64_t count = 0;
        read(fd_, &count, sizeof(count));
        return count;
    }
};

// Uso
void measure_with_perf() {
    PerfCounter cycles(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES);
    PerfCounter instructions(PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS);
    PerfCounter cache_misses(PERF_TYPE_HARDWARE, PERF_COUNT_HW_CACHE_MISSES);
    
    cycles.start();
    instructions.start();
    cache_misses.start();
    
    // Função a medir
    // constant_time_function(...);
    
    uint64_t c = cycles.stop();
    uint64_t i = instructions.stop();
    uint64_t cm = cache_misses.stop();
    
    printf("Cycles: %lu, Instructions: %lu, Cache Misses: %lu\n", c, i, cm);
    printf("CPI: %.2f\n", static_cast<double>(c) / i);
}
```

### 2.10.3 Cache Line Analysis

```cpp
#include <cstdint>
#include <vector>
#include <chrono>

class CacheLineAnalyzer {
public:
    struct CacheLineInfo {
        size_t line_size;
        size_t associativity;
        size_t total_cache_size;
        size_t num_sets;
    };
    
    // Detectar tamanho da cache line
    static size_t detect_cache_line_size() {
        // Testar com stride crescente
        const size_t buffer_size = 1024 * 1024;  // 1MB
        uint8_t* buffer = new uint8_t[buffer_size];
        
        // Preencher buffer
        for (size_t i = 0; i < buffer_size; ++i) {
            buffer[i] = static_cast<uint8_t>(i);
        }
        
        // Medir tempo com diferentes strides
        size_t best_stride = 64;  // Default
        
        for (size_t stride = 16; stride <= 256; stride *= 2) {
            volatile uint8_t dummy;
            auto start = std::chrono::high_resolution_clock::now();
            
            for (size_t i = 0; i < buffer_size; i += stride) {
                dummy = buffer[i];
            }
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
                end - start
            ).count();
            
            // Stride que causa mais cache misses revela line size
            if (duration > 1000000) {  // > 1ms
                best_stride = stride;
                break;
            }
        }
        
        delete[] buffer;
        return best_stride;
    }
    
    // Medir latência de acesso a diferentes níveis de cache
    struct LatencyProfile {
        double l1_latency_ns;
        double l2_latency_ns;
        double l3_latency_ns;
        double memory_latency_ns;
    };
    
    static LatencyProfile measure_latency_profile() {
        LatencyProfile profile;
        
        // Tamanhos típicos de cache
        constexpr size_t L1_SIZE = 32 * 1024;      // 32KB
        constexpr size_t L2_SIZE = 256 * 1024;     // 256KB
        constexpr size_t L3_SIZE = 8 * 1024 * 1024; // 8MB
        constexpr size_t MEM_SIZE = 64 * 1024 * 1024; // 64MB
        
        // Medir para cada tamanho
        auto measure_size = [](size_t size) -> double {
            uint8_t* buffer = new uint8_t[size];
            constexpr size_t STRIDE = 64;
            constexpr size_t ITERATIONS = 100;
            
            volatile uint8_t dummy;
            auto start = std::chrono::high_resolution_clock::now();
            
            for (size_t iter = 0; iter < ITERATIONS; ++iter) {
                for (size_t i = 0; i < size; i += STRIDE) {
                    dummy = buffer[i];
                }
            }
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
                end - start
            ).count();
            
            delete[] buffer;
            return static_cast<double>(duration) / (ITERATIONS * (size / STRIDE));
        };
        
        profile.l1_latency_ns = measure_size(L1_SIZE);
        profile.l2_latency_ns = measure_size(L2_SIZE);
        profile.l3_latency_ns = measure_size(L3_SIZE);
        profile.memory_latency_ns = measure_size(MEM_SIZE);
        
        return profile;
    }
};
```

---

## 2.11 Valgrind Massif e Cachegrind para Timing Analysis

### 2.11.1 Cachegrind

```bash
# Compilar com debug info
g++ -O0 -g -o program program.cpp

# Rodar com Cachegrind
valgrind --tool=cachegrind --D1=32768,8,64 \
         --L2=262144,8,64 \
         --LL=8388608,16,64 \
         ./program

# Analisar output
cg_annotate cachegrind.out.12345

# Gerar relatório visual
cg_annotate --auto=yes cachegrind.out.12345 > report.txt

# Usar KCachegrind para visualização gráfica
kcachegrind cachegrind.out.12345
```

### 2.11.2 Massif (Memory Profiler)

```bash
# Rodar com Massif
valgrind --tool=massif --pages-as-heap=no ./program

# Analisar output
ms_print massif.out.12345

# Script de análise
valgrind --tool=massif \
         --massif-out-file=massif.out \
         --pages-as-heap=no \
         ./program

# Converter para formato visual
ms_print massif.out > massif_visual.txt
```

### 2.11.3 Código com Valgrind Annotations

```cpp
#include <valgrind/memcheck.h>
#include <cstdint>

// Valgrind annotations podem ajudar a detectar
// uso incorreto de memória em constant-time code

class ConstantTimeWithValgrind {
public:
    static bool secure_compare(const uint8_t* a, const uint8_t* b, 
                                size_t len) {
        uint8_t result = 0;
        
        for (size_t i = 0; i < len; ++i) {
            // Marcar resultado como "undefined" para Valgrind
            // Isso ajuda a detectar se resultado é usado incorretamente
            VALGRIND_MAKE_MEM_UNDEFINED(&result, sizeof(result));
            
            result |= a[i] ^ b[i];
            
            VALGRIND_MAKE_MEM_DEFINED(&result, sizeof(result));
        }
        
        return result == 0;
    }
    
    // Usar VALGRIND_CHECK_MEM_IS_DEFINED para verificar
    // se dados são definidos antes de usar
    static void verify_defined(const uint8_t* data, size_t len) {
        VALGRIND_CHECK_MEM_IS_DEFINED(data, len);
    }
    
    // Usar VALGRIND_MAKE_MEM_NOACCESS para proteger
    // dados sensíveis após uso
    static void secure_clear(uint8_t* data, size_t len) {
        // Limpar
        for (size_t i = 0; i < len; ++i) {
            data[i] = 0;
        }
        
        // Marcar como inacessível
        VALGRIND_MAKE_MEM_NOACCESS(data, len);
    }
};
```

---

## 2.12 CVE-2019-1547: OpenSSL ECDSA Timing Side-Channel

### 2.12.1 Descrição da Vulnerabilidade

**CVE**: CVE-2019-1547
**Severidade**: Medium (5.3)
**Produto afetado**: OpenSSL 1.0.2 - 1.0.2o
**Tipo**: Timing Side-Channel Attack

#### O que aconteceu?

A implementação de ECDSA (Elliptic Curve Digital Signature Algorithm) no OpenSSL 1.0.2k e anteriores tinha um timing side-channel que permitia a um atacante recuperar a chave privada.

O problema estava na função de assinatura ECDSA, especificamente na geração do número aleatório `k` (nonce). O OpenSSL 1.0.2 usava um PRNG (Pseudo-Random Number Generator) que:

1. **Gerava k com timing variável**: O tempo para gerar o nonce dependia do valor gerado
2. **Não verificava uniformidade**: O nonce não era uniformemente distribuído
3. **Revealava bits via timing**: Cada bit de k podia ser deduzido medindo o tempo

### 2.12.2 Análise Técnica

```cpp
// Código vulnerável (simplificado do OpenSSL 1.0.2k)
// Referência: crypto/ec/ecdsa_ossl.c

// NOVO: Implementação VULNERÁVEL (NÃO USAR)
namespace vulnerable {

// PRNG com timing variável
struct ECDSA_CTX {
    uint8_t private_key[32];
    uint8_t nonce[32];
};

// Função de geração de nonce VULNERÁVEL
// O tempo depende do valor gerado
void generate_nonce_bad(uint8_t* nonce, size_t len) {
    // Em OpenSSL 1.0.2k, isto era feito via BN_rand()
    // que tinha timing dependente do valor gerado
    
    // SIMULAÇÃO do bug:
    for (size_t i = 0; i < len; ++i) {
        nonce[i] = 0;
        
        // Bug: gera bytes até encontrar valor não-zero
        // Se nonce[i] == 0, continua gerando
        // Isso revela timing!
        while (nonce[i] == 0) {
            // Em OpenSSL real, isto chamava RAND_bytes()
            // que tinha timing variável
            nonce[i] = rand() % 256;  // Simplificado
        }
    }
}

// Assinatura VULNERÁVEL
// k é gerado com timing variável
bool sign_message_bad(const uint8_t* private_key,
                       const uint8_t* message, size_t msg_len,
                       uint8_t* signature) {
    uint8_t k[32];
    
    // BUG: generate_nonce_bad tem timing dependente de k
    generate_nonce_bad(k, sizeof(k));
    
    // Assinatura ECDSA: s = k^{-1} * (hash + private_key * r) mod n
    // Se k é conhecido via timing, privada pode ser recuperada
    
    // ... (código de assinatura omitted)
    
    return true;
}

}  // namespace vulnerable

// CORREÇÃO (OpenSSL 1.1.0+)
namespace fixed {

// Nonce generation constante-time
void generate_nonce_ct(uint8_t* nonce, size_t len) {
    // Usar DRBG (Deterministic Random Bit Generator)
    // que é constante-time
    
    // OpenSSL 1.1.0+ usa DRBGs que:
    // 1. Sempre geram blocos de tamanho fixo
    // 2. Não têm timing variável
    // 3. Usam AES-CTR ou Hash-DRBG
    
    // Em código real:
    // RAND_bytes(nonce, len);
    
    // Simulação constante-time:
    // Preencher com zeros primeiro (constante-time)
    for (size_t i = 0; i < len; ++i) {
        nonce[i] = 0;
    }
    
    // Em seguida, preencher com dados pseudo-aleatórios
    // SEM loop de retry
    // Em OpenSSL 1.1.0+, isto é feito internamente
}

// Assinatura segura
bool sign_message_fixed(const uint8_t* private_key,
                         const uint8_t* message, size_t msg_len,
                         uint8_t* signature) {
    uint8_t k[32];
    
    // Usar geração constante-time
    generate_nonce_ct(k, sizeof(k));
    
    // Verificar se k está no range válido
    // Isso é público (k < curve_order), não timing-sensitive
    
    // ... (código de assinatura)
    
    return true;
}

}  // namespace fixed
```

### 2.12.3 Tabela: CVE-2019-1547

| Campo | Valor |
|-------|-------|
| CVE | CVE-2019-1547 |
| Produto | OpenSSL 1.0.2 - 1.0.2o |
| Severidade | Medium (5.3) |
| CVSS | CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N |
| Tipo | Timing Side-Channel |
| Componente | ECDSA nonce generation |
| Ano | 2019 |
| Impacto | Recuperação de chave privada ECDSA |
| Fix | OpenSSL 1.1.1c, 1.0.2s |
| Mitigation | Atualizar para OpenSSL 1.1.1+ |

### 2.12.3.1 Como teria sido prevenido

```cpp
// Prevenção: usar geração de nonce constante-time
// 1. Usar DRBGs aprovados (NIST SP 800-90A)
// 2. Usar deterministic ECDSA (RFC 6979)
// 3. Verificar que nonce é uniformemente distribuído

// Exemplo: RFC 6979 - Deterministic ECDSA
// Gera k de forma determinística a partir da chave e mensagem
// Eliminando a necessidade de RNG constante-time

namespace rfc6979 {

// Deterministic nonce generation (simplificado)
void generate_deterministic_nonce(
    const uint8_t* private_key,
    const uint8_t* message, size_t msg_len,
    uint8_t* k_out)
{
    // 1. h1 = HMAC-SHA256(private_key, message)
    uint8_t h1[32];
    // hmac_sha256(private_key, 32, message, msg_len, h1);
    
    // 2. Inicializar DRBG com h1 como seed
    // 3. Gerar k do DRBG
    
    // Este processo é:
    // - Determinístico (mesmo input = mesmo k)
    // - Constant-time (DRBG é constante-time)
    // - Seguro (não depende de RNG externo)
}

}  // namespace rfc6979
```

---

## 2.13 Lucky13: Padding Oracle via Timing Difference

### 2.13.1 Descrição da Vulnerabilidade

**CVE**: CVE-2013-0169
**Severidade**: Medium (4.3)
**Produto afetado**: TLS/SSL implementations (OpenSSL, NSS, GnuTLS)
**Tipo**: Padding Oracle Attack via Timing

#### O que aconteceu?

Lucky13 é um ataque de padding oracle que explora diferenças de timing na verificação de padding de mensagens TLS CBC (Cipher Block Chaining).

O ataque funciona porque:
1. O servidor verifica padding **antes** de verificar MAC
2. O tempo para remover padding varia dependendo do padding correto
3. O atacante pode distinguir "padding correto" vs "padding incorreto" medindo timing
4. Com milhares de requests, o atacante pode decriptar qualquer mensagem

### 2.13.2 Análise Técnica

```cpp
// Código VULNERÁVEL (simplificado de implementações TLS)
// Referência: AlFardan, Bernstein, Paterson, Poettering, Schuldt (2013)

namespace vulnerable {

// Verificação de padding VULNERÁVEL
bool check_padding_vulnerable(const uint8_t* decrypted, size_t len) {
    // O último byte indica o valor do padding
    uint8_t padding_len = decrypted[len - 1];
    
    // Verificar se padding_len é válido
    if (padding_len > len - 1 || padding_len == 0) {
        return false;  // Padding inválido
    }
    
    // Verificar se todos os bytes de padding são iguais
    // BUG: este loop tem timing variável!
    for (size_t i = 0; i < padding_len; ++i) {
        if (decrypted[len - 1 - i] != padding_len) {
            return false;  // Early return revela posição do erro
        }
    }
    
    return true;
}

// MAC verification VULNERÁVEL
bool verify_mac_vulnerable(const uint8_t* key,
                            const uint8_t* data, size_t data_len,
                            const uint8_t* received_mac, size_t mac_len) {
    // Se padding está correto, verificar MAC
    // Mas tempo depende de onde padding falha
    
    // ... (verificação de MAC omitted)
    
    return true;
}

// Processamento TLS VULNERÁVEL
bool process_tls_record_vulnerable(const uint8_t* record, size_t record_len,
                                    const uint8_t* mac_key,
                                    const uint8_t* enc_key) {
    // 1. Decriptar
    uint8_t decrypted[16384];
    // aes_cbc_decrypt(enc_key, record, record_len, decrypted);
    
    // 2. Verificar padding (VULNERÁVEL!)
    if (!check_padding_vulnerable(decrypted, record_len)) {
        // Enviar alert "bad_record_mac"
        return false;  // Timing diferente aqui!
    }
    
    // 3. Verificar MAC
    // ... (MAC verification)
    
    return true;
}

}  // namespace vulnerable

// CORREÇÃO: Constant-time padding verification
namespace fixed {

// Constant-time padding check
bool check_padding_ct(const uint8_t* decrypted, size_t len) {
    uint8_t padding_len = decrypted[len - 1];
    uint8_t valid = 0;
    
    // Verificar se padding_len está no range válido
    uint8_t range_check = static_cast<uint8_t>(
        (padding_len > 0) & (padding_len <= len - 1)
    );
    
    // Verificar TODOS os bytes de padding
    // SEM early return!
    for (size_t i = 0; i < padding_len; ++i) {
        uint8_t match = static_cast<uint8_t>(
            decrypted[len - 1 - i] == padding_len
        );
        valid |= match;
    }
    
    // Resultado final
    return (range_check & valid) != 0;
}

// Constant-time MAC verification
bool verify_mac_ct(const uint8_t* key,
                    const uint8_t* data, size_t data_len,
                    const uint8_t* received_mac, size_t mac_len) {
    // Calcular MAC
    uint8_t computed_mac[32];
    // hmac_sha256(key, ..., data, data_len, computed_mac);
    
    // Comparação constante-time
    uint8_t result = 0;
    for (size_t i = 0; i < mac_len; ++i) {
        result |= computed_mac[i] ^ received_mac[i];
    }
    
    return result == 0;
}

// Processamento TLS CORRIGIDO
bool process_tls_record_ct(const uint8_t* record, size_t record_len,
                            const uint8_t* mac_key,
                            const uint8_t* enc_key) {
    // 1. Decriptar
    uint8_t decrypted[16384];
    // aes_cbc_decrypt(enc_key, record, record_len, decrypted);
    
    // 2. Verificar padding (CONSTANT-TIME!)
    if (!check_padding_ct(decrypted, record_len)) {
        return false;
    }
    
    // 3. Verificar MAC (CONSTANT-TIME!)
    // Mesmo se padding está incorreto, sempre verificar MAC
    // Isso torna o timing constante
    // ... (MAC verification)
    
    return true;
}

}  // namespace fixed
```

### 2.13.3 Tabela: Lucky13

| Campo | Valor |
|-------|-------|
| CVE | CVE-2013-0169 |
| Produto | TLS/SSL (OpenSSL, NSS, GnuTLS) |
| Severidade | Medium (4.3) |
| CVSS | CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N |
| Tipo | Padding Oracle via Timing |
| Componente | TLS CBC padding verification |
| Ano | 2013 |
| Impacto | Decriptação de mensagens TLS |
| Mitigation | Constant-time padding check, encrypt-then-MAC |
| Fix | OpenSSL 1.0.1g, NSS 3.14.5 |

### 2.13.3.1 Mitigação detalhada

```cpp
// Mitigação completa para Lucky13

// 1. Constant-time padding check (já mostrado acima)

// 2. Encrypt-then-MAC (RFC 7366)
// Em vez de MAC-then-Encrypt (TLS 1.0-1.2):
// - MAC é calculado sobre texto cifrado
// - MAC é verificado ANTES de decriptar
// - Timing não revela informação sobre padding

// 3. TLS 1.3 elimina completamente o problema:
// - Usa AEAD (AES-GCM, ChaCha20-Poly1305)
// - Não há padding oracle possible
// - GCM/ChaCha20 são inerentemente constant-time

// Exemplo: Encrypt-then-MAC (simplificado)
bool encrypt_then_mac_process(const uint8_t* record, size_t record_len,
                               const uint8_t* mac_key,
                               const uint8_t* enc_key) {
    // 1. Separar MAC e ciphertext
    size_t mac_len = 32;  // SHA-256
    const uint8_t* received_mac = record + record_len - mac_len;
    const uint8_t* ciphertext = record;
    size_t ciphertext_len = record_len - mac_len;
    
    // 2. Verificar MAC sobre ciphertext (CONSTANT-TIME)
    // Mesmo se MAC falhar, NÃO revelar onde falhou
    uint8_t computed_mac[32];
    // hmac_sha256(mac_key, ..., ciphertext, ciphertext_len, computed_mac);
    
    uint8_t mac_result = 0;
    for (size_t i = 0; i < mac_len; ++i) {
        mac_result |= computed_mac[i] ^ received_mac[i];
    }
    
    if (mac_result != 0) {
        // MAC inválido
        // NÃO retornar aqui (ou retornar timing constante)
        // Em TLS 1.3, sempre processar até o final
        return false;
    }
    
    // 3. Decriptar
    // aes_gcm_decrypt(enc_key, ciphertext, ciphertext_len, ...);
    
    return true;
}
```

---

## 2.14 Minerva: Timing Attack em Smart Cards

### 2.14.1 Descrição da Vulnerabilidade

**CVE**: N/A (vulnerabilidade de implementação)
**Severidade**: High (7.6)
**Produto afetado**: Smart cards com ECDSA/P-256
**Tipo**: Timing Side-Channel em implementação de curva elíptica

#### O que aconteceu?

Minerva é um ataque de timing que explora diferenças no tempo de computação de operações de curva elíptica (escalar multiplication) em smart cards.

O ataque descobriu que:
1. A operação de multiplicação escalar ECDSA varia em tempo dependendo do **número de bits significativos** do nonce `k`
2. Smart cards usam otimizações que pulam zeros leading em k
3. Isso revela informação sobre k, permitindo recuperação da chave privada

### 2.14.2 Análise Técnica

```cpp
// Código VULNERÁVEL (simulação de smart card)
// Referência: Jancar et al., "Minerva: The curse of ECDSA nonces" (2020)

namespace minerva_vulnerable {

// Multiplicação escalar em curva elíptica VULNERÁVEL
// Smart cards frequentemente otimizam para zeros leading
struct Point {
    uint8_t x[32];
    uint8_t y[32];
};

// Tabela pre-computada para acelerar
Point precomputed_table[64];

// Multiplicação escalar VULNERÁVEL
// Tempo depende do número de leading zeros em scalar
Point scalar_mul_vulnerable(const uint8_t* scalar, size_t scalar_len) {
    Point result;
    // Ponto infinito (identidade aditiva)
    memset(result.x, 0, 32);
    memset(result.y, 0, 32);
    
    Point temp;
    memset(temp.x, 0, 32);
    memset(temp.y, 0, 32);
    
    bool started = false;
    
    // BUG: este loop tem timing dependente de scalar!
    for (int i = 0; i < scalar_len * 8; ++i) {
        int byte_idx = i / 8;
        int bit_idx = 7 - (i % 8);
        
        uint8_t bit = (scalar[byte_idx] >> bit_idx) & 1;
        
        // Otimização: não processar leading zeros
        if (bit == 0 && !started) {
            continue;  // Pula leading zeros!
            // Isso revela timing!
        }
        
        started = true;
        
        // Double
        // point_double(&result);
        
        // Add se bit == 1
        if (bit == 1) {
            // point_add(&result, &precomputed_table[byte_idx]);
        }
    }
    
    return result;
}

// Assinatura ECDSA VULNERÁVEL
bool sign_vulnerable(const uint8_t* private_key,
                      const uint8_t* message_hash,
                      uint8_t* signature) {
    // 1. Gerar nonce k (pode ter leading zeros)
    uint8_t k[32];
    // random_bytes(k, 32);
    
    // 2. Calcular R = k * G (VULNERÁVEL!)
    Point R = scalar_mul_vulnerable(k, 32);
    
    // 3. r = R.x mod n
    // 4. s = k^{-1} * (hash + private_key * r) mod n
    
    // ... (rest of signing)
    
    return true;
}

}  // namespace minerva_vulnerable

// CORREÇÃO: Multiplicação escalar constante-time
namespace minerva_fixed {

// Multiplicação escalar constante-time
// Usa Montgomery ladder - SEMPRE executa o mesmo número de iterações
Point scalar_mul_ct(const uint8_t* scalar, size_t scalar_len) {
    Point r0, r1;
    
    // Inicializar r0 = ponto infinito, r1 = G
    memset(r0.x, 0, 32);
    memset(r0.y, 0, 32);
    // r1 = G (ponto gerador da curva)
    
    Point temp;
    
    // Montgomery ladder: SEMPRE itera sobre TODOS os bits
    for (int i = scalar_len * 8 - 1; i >= 0; --i) {
        int byte_idx = i / 8;
        int bit_idx = i % 8;
        
        uint8_t bit = (scalar[byte_idx] >> bit_idx) & 1;
        
        // SEMPRE executar double e add
        // bit determina QUAL dos dois resultados usar
        
        // Se bit == 0: r0 = 2*r0, r1 = r0 + r1
        // Se bit == 1: r0 = r0 + r1, r1 = 2*r1
        
        // Constant-time select
        uint8_t mask = -bit;
        
        // Sempre calcular ambos os resultados
        Point temp_r0 = r0;  // double(r0)
        Point temp_r1 = r0;  // add(r0, r1)
        
        // point_double(&temp_r0);
        // point_add(&temp_r1, &r1);
        
        Point temp2_r0 = r1;  // add(r1, r0)
        Point temp2_r1 = r1;  // double(r1)
        
        // point_add(&temp2_r0, &r0);
        // point_double(&temp2_r1);
        
        // Selecionar baseado em bit (constante-time)
        for (int j = 0; j < 32; ++j) {
            r0.x[j] = (temp_r0.x[j] & mask) | (temp2_r0.x[j] & ~mask);
            r0.y[j] = (temp_r0.y[j] & mask) | (temp2_r0.y[j] & ~mask);
            r1.x[j] = (temp_r1.x[j] & mask) | (temp2_r1.x[j] & ~mask);
            r1.y[j] = (temp_r1.y[j] & mask) | (temp2_r1.y[j] & ~mask);
        }
    }
    
    return r0;
}

// Assinatura segura
bool sign_ct(const uint8_t* private_key,
             const uint8_t* message_hash,
             uint8_t* signature) {
    // 1. Gerar nonce k (constante-time)
    uint8_t k[32];
    // Deterministic nonce (RFC 6979) ou DRBG constante-time
    
    // 2. Calcular R = k * G (CONSTANT-TIME!)
    Point R = scalar_mul_ct(k, 32);
    
    // 3. Continuar com constant-time operations
    
    return true;
}

}  // namespace minerva_fixed
```

### 2.14.3 Tabela: Minerva

| Campo | Valor |
|-------|-------|
| CVE | N/A (vulnerabilidade de implementação) |
| Produto | Smart cards (múltiplos fabricantes) |
| Severidade | High (7.6) |
| CVSS | CVSS:3.1/AV:P/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H |
| Tipo | Timing Side-Channel em ECDSA |
| Componente | Scalar multiplication em curva elíptica |
| Ano | 2020 |
| Impacto | Recuperação de chave privada ECDSA |
| Mitigation | Montgomery ladder, constant-time scalar mul |

### 2.14.4 Lições Aprendidas

```cpp
// Lições do Minerva para implementadores:

// 1. NUNCA pule leading zeros em operações criptográficas
//    Otimização "innocente" cria timing side-channel

// 2. Use Montgomery ladder para scalar multiplication
//    Sempre executa o mesmo número de iterações

// 3. Teste com diferentes valores de nonce
//    Verifique se timing é constante independentemente do nonce

// 4. Smart cards são especialmente vulneráveis
//    Hardware pode ter otimizações secretas

// 5. Use implementações auditadas
//    Não implemente criptografia básica do zero

// Implementação correta: Montgomery ladder
struct MontgomeryLadder {
    Point r0, r1;  // Dois pontos para ladder
    
    MontgomeryLadder(const Point& G) {
        memset(r0.x, 0, 32);
        memset(r0.y, 0, 32);
        r1 = G;
    }
    
    void process_bit(uint8_t bit) {
        Point temp_r0 = r0;
        Point temp_r1 = r0;
        
        Point temp2_r0 = r1;
        Point temp2_r1 = r1;
        
        // Sempre calcular double e add para AMBOS
        // point_double(&temp_r0);      // 2*r0
        // point_add(&temp_r1, &r1);    // r0 + r1
        // point_add(&temp2_r0, &r0);   // r1 + r0
        // point_double(&temp2_r1);     // 2*r1
        
        // Selecionar baseado em bit (constante-time)
        uint8_t mask = -static_cast<uint8_t>(bit);
        
        for (int j = 0; j < 32; ++j) {
            r0.x[j] = (temp_r0.x[j] & mask) | (temp2_r0.x[j] & ~mask);
            r0.y[j] = (temp_r0.y[j] & mask) | (temp2_r0.y[j] & ~mask);
            r1.x[j] = (temp_r1.x[j] & mask) | (temp2_r1.x[j] & ~mask);
            r1.y[j] = (temp_r1.y[j] & mask) | (temp2_r1.y[j] & ~mask);
        }
    }
    
    Point result() const {
        return r0;
    }
};
```

---

## 2.15 Anti-patterns: Código que Parece Constant-Time mas Não é

### 2.15.1 Anti-pattern 1: Conditional Return

```cpp
// ANTI-PATTERN: return condicional
// Parece constante-time mas o compilador pode otimizar

// ERRADO
bool bad_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t result = 0;
    for (size_t i = 0; i < len; ++i) {
        result |= a[i] ^ b[i];
    }
    return result == 0;  // Compilador pode branch aqui!
}

// CORRETO: Usar bitwise operations
bool good_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t result = 0;
    for (size_t i = 0; i < len; ++i) {
        result |= a[i] ^ b[i];
    }
    // Usar操作 para evitar branch
    return ((result - 1) >> 8) & 1;  // 1 se result == 0, 0 caso contrário
}
```

### 2.15.2 Anti-pattern 2: Early Return em Funções

```cpp
// ANTI-PATTERN: Early return baseado em dados secretos

// ERRADO
void process_secret_data(const uint8_t* data, size_t len, 
                          uint8_t* output) {
    if (len == 0) return;  // OK: len não é secreto
    
    // Mas se len depende de dados secretos, é vulnerável!
    for (size_t i = 0; i < len; ++i) {
        output[i] = data[i] ^ 0xFF;
    }
}

// CORRETO: Processar sempre tamanho fixo
void process_secret_data_ct(const uint8_t* data, size_t max_len,
                             uint8_t* output, size_t actual_len) {
    // Sempre processar max_len bytes
    for (size_t i = 0; i < max_len; ++i) {
        // Usar conditional select para output
        uint8_t valid = static_cast<uint8_t>(i < actual_len);
        uint8_t mask = -valid;
        output[i] = (data[i] ^ 0xFF) & mask;
    }
}
```

### 2.15.3 Anti-pattern 3: Switch-Case com Dados Secretos

```cpp
// ANTI-PATTERN: Switch-case baseado em dados secretos

// ERRADO
uint8_t lookup_table_bad(uint8_t secret_index) {
    switch (secret_index) {
        case 0: return 0xAA;
        case 1: return 0xBB;
        // ...
        default: return 0x00;
    }
    // Compilador gera jump table baseado em secret_index
    // Padrão de cache revela informação!
}

// CORRETO: Percorrer tabela inteira
uint8_t lookup_table_ct(const uint8_t* table, size_t table_size,
                         uint8_t secret_index) {
    uint8_t result = 0;
    for (size_t i = 0; i < table_size; ++i) {
        uint8_t match = static_cast<uint8_t>(
            (static_cast<int>(i == secret_index)) * 0xFF
        );
        result = (table[i] & match) | (result & ~match);
    }
    return result;
}
```

### 2.15.4 Anti-pattern 4: Uso de strlen em Dados Secretos

```cpp
// ANTI-PATTERN: strlen() em dados secretos

// ERRADO
void process_string(const char* secret_string) {
    size_t len = strlen(secret_string);  // NÃO é constante-time!
    // strlen para no primeiro \0
    // Timing revela posição do primeiro \0
    
    for (size_t i = 0; i < len; ++i) {
        // ...
    }
}

// CORRETO: Usar tamanho fixo ou comparar com tamanho conhecido
void process_fixed_string(const char* secret_string, size_t known_len) {
    // Usar known_len em vez de strlen
    for (size_t i = 0; i < known_len; ++i) {
        // ...
    }
}
```

### 2.15.5 Anti-pattern 5: Memcpy com Tamanho Secreto

```cpp
// ANTI-PATTERN: memcpy com tamanho secreto

// ERRADO
void copy_secret(void* dest, const void* src, size_t secret_len) {
    memcpy(dest, src, secret_len);  // NÃO é constante-time!
    // Padrão de acesso a memória depende de secret_len
}

// CORRETO: Copiar sempre tamanho máximo
void copy_secret_ct(void* dest, const void* src, 
                     size_t secret_len, size_t max_len) {
    const uint8_t* src_bytes = static_cast<const uint8_t*>(src);
    uint8_t* dest_bytes = static_cast<uint8_t*>(dest);
    
    for (size_t i = 0; i < max_len; ++i) {
        // Sempre acessar src[i] e dest[i]
        uint8_t valid = static_cast<uint8_t>(i < secret_len);
        uint8_t mask = -valid;
        dest_bytes[i] = (src_bytes[i] & mask) | (dest_bytes[i] & ~mask);
    }
}
```

### 2.15.6 Anti-pattern 6: Exceptions Baseadas em Dados Secretos

```cpp
// ANTI-PATTERN: Throwing exception baseada em dados secretos

// ERRADO
void process_data(const uint8_t* data, size_t len) {
    if (data[0] == 0xFF) {  // Branch secret-dependent
        throw std::runtime_error("Invalid data");  // Exception timing
    }
    // ...
}

// CORRETO: Sempre executar o mesmo caminho
void process_data_ct(const uint8_t* data, size_t len) {
    // Calcular resultado independentemente
    uint8_t error_mask = static_cast<uint8_t>(data[0] == 0xFF);
    
    // Usar error_mask para decidir resultado
    // Mas SEM throw/return baseado em dado secreto
    uint8_t result = 0;
    for (size_t i = 0; i < len; ++i) {
        result |= data[i] & ~error_mask;
    }
    
    // Se precisar indicar erro, retornar código de erro
    // (não throw)
}
```

### 2.15.7 Anti-pattern 7: Vector Size Secreto

```cpp
// ANTI-PATTERN: vector::size() como dado secreto

// ERRADO
void process_vector(const std::vector<uint8_t>& secret_data) {
    // Otimizações do vector podem revelar tamanho
    for (size_t i = 0; i < secret_data.size(); ++i) {
        // ...
    }
}

// CORRETO: Usar tamanho fixo
void process_fixed_vector(const uint8_t* data, size_t max_len,
                           size_t actual_len) {
    for (size_t i = 0; i < max_len; ++i) {
        uint8_t valid = static_cast<uint8_t>(i < actual_len);
        uint8_t mask = -valid;
        // Processar independentemente de valid
    }
}
```

### 2.15.8 Anti-pattern 8: String Comparison Secret-Dependent

```cpp
// ANTI-PATTERN: Comparação de string com early exit

// ERRADO
bool verify_password(const char* input, const char* correct) {
    size_t len = strlen(correct);
    for (size_t i = 0; i < len; ++i) {
        if (input[i] != correct[i]) {
            return false;  // Early exit!
        }
    }
    return input[len] == '\0';
}

// CORRETO: Comparação constante-time
bool verify_password_ct(const char* input, const char* correct,
                         size_t max_len) {
    uint8_t result = 0;
    size_t correct_len = strlen(correct);
    
    for (size_t i = 0; i < max_len; ++i) {
        // Comparar sempre max_len bytes
        uint8_t input_byte = (i < strlen(input)) ? input[i] : 0;
        uint8_t correct_byte = (i < correct_len) ? correct[i] : 0;
        
        result |= input_byte ^ correct_byte;
    }
    
    // Verificar também se tamanhos são iguais
    uint8_t len_diff = static_cast<uint8_t>(strlen(input) ^ correct_len);
    
    return (result | len_diff) == 0;
}
```

---

## 2.16 Checklist de Constant-Time Programming

### 2.16.1 Princípios Fundamentais

```
CHECKLIST DE CONSTANT-TIME PROGRAMMING
========================================

1. DADOS SECRETOS
   [ ] Chaves privadas
   [ ] Tokens de autenticação
   [ ] Segredos de protocolo
   [ ] Nonces (quando secretos)
   [ ] Dados de usuário sensíveis

2. OPERAÇÕES CRÍTICAS
   [ ] Comparações de MAC/assinatura
   [ ] Verificação de passwords
   [ ] Decriptação com dados sensíveis
   [ ] Geração de chaves
   [ ] Operações de curva elíptica

3. CODING STANDARDS
   [ ] Usar CRYPTO_memcmp/sodium_memcmp para comparações
   [ ] Usar OPENSSL_cleanse/sodium_memzero para limpeza
   [ ] NUNCA usar memcmp para dados sensíveis
   [ ] NUNCA usar memset para limpeza segura
   [ ] Usar ct_select em vez de ternary operator

4. BRANCHES
   [ ] Nenhum branch depende de dados secretos
   [ ] Nenhum early return baseado em dados secretos
   [ ] Nenhum throw/exception baseado em dados secretos
   [ ] Usar bitwise operations em vez de if/else
   [ ] Usar CMOV (x86) ou CSEL (ARM) quando possível

5. MEMORY ACCESS
   [ ] Nenhum acesso a array com índice secreto
   [ ] Usar lookup tables constante-time
   [ ] Evitar table lookups com índices variáveis
   [ ] Usar Montgomery ladder para curva elíptica
   [ ] Evitar access patterns dependentes de dados secretos

6. COMPILER
   [ ] Usar compiler barriers quando necessário
   [ ] Usar volatile para dados sensíveis
   [ ] Verificar assembly gerado (objdump)
   [ ] Usar -O0 para debugging (não produção)
   [ ] Testar com múltiplas versões de compilador

7. VALIDATION
   [ ] Testar com diferentes valores de input
   [ ] Usar Valgrind/Cachegrind para análise
   [ ] Verificar perf counters
   [ ] Testar em hardware alvo (x86-64, ARM64)
   [ ] Auditoria de código por especialista

8. DOCUMENTATION
   [ ] Documentar dados sensíveis
   [ ] Documentar operações constant-time
   [ ] Documentar dependências de bibliotecas
   [ ] Documentar limitações conhecidas
   [ ] Documentar testes realizados
```

### 2.16.2 Checklist por Tipo de Operação

```cpp
// CHECKLIST PARA CADA OPERAÇÃO CRIPTOGRÁFICA

// 1. COMPARAÇÃO DE MAC
// [ ] Usar CRYPTO_memcmp ou sodium_memcmp
// [ ] SEMPRE comparar todos os bytes
// [ ] NÃO retornar na primeira diferença
// [ ] Verificar tamanho ANTES (se público)

// 2. VERIFICAÇÃO DE ASSINATURA
// [ ] Usar implementação constante-time
// [ ] Não revelar qual parte da assinatura é inválida
// [ ] Usar bibliotecas auditadas

// 3. OPERAÇÕES EM CURVA ELÍPTICA
// [ ] Usar Montgomery ladder
// [ ] Não pular leading zeros
// [ ] Usar constant-time point operations
// [ ] Verificar implementação do hardware

// 4. AES/Block Cipher
// [ ] Usar AES-NI quando disponível
// [ ] Não usar tabelas lookup software-based
// [ ] Verificar padding é constante-time

// 5. RSA
// [ ] Usar CRT constante-time
// [ ] Verificar blinding está habilitado
// [ ] Usar implementação de biblioteca auditada

// 6. PASSWORD HASHING
// [ ] Usar bcrypt/scrypt/argon2
// [ ] NUNCA comparar hashes com memcmp
// [ ] Usar comparador constante-time para hash

// 7. TLS/SSL
// [ ] Usar TLS 1.3 (AEAD)
// [ ] Evitar CBC em TLS 1.2
// [ ] Verificar padding constante-time
// [ ] Usar encrypt-then-MAC
```

---

## 2.17 Exercícios

### Exercício 1: Implementação de Constant-Time Comparison

**Objetivo**: Implementar e testar comparação constante-time.

```cpp
// Exercício 1: Implementar as seguintes funções
// e verificar que são constante-time

#include <cstdint>
#include <cstddef>

// 1a. Implementar comparação constante-time para uint8_t arrays
// Deve retornar 1 se iguais, 0 caso contrário
// Deve percorrer TODOS os bytes, SEM early return
int constant_time_compare(const uint8_t* a, const uint8_t* b, size_t len);

// 1b. Implementar variação que também compara tamanhos
// len_a e len_b são públicos (não precisam ser constante-time)
// mas a comparação dos dados deve ser constante-time
int constant_time_compare_with_length(const uint8_t* a, size_t len_a,
                                       const uint8_t* b, size_t len_b);

// 1c. Implementar versão usando uint64_t para eficiência
// Processar 8 bytes por iteração
int constant_time_compare_64(const uint8_t* a, const uint8_t* b, size_t len);

// 1d. Testar sua implementação
// Criar testes que medem timing com diferentes inputs
// Verificar que timing é constante (stddev < threshold)
```

### Exercício 2: Constant-Time Conditional Select

**Objetivo**: Implementar seleção condicional constante-time.

```cpp
// Exercício 2: Implementar seleção condicional

// 2a. Implementar para uint32_t
uint32_t constant_time_select_u32(uint32_t selector, 
                                   uint32_t true_val, 
                                   uint32_t false_val);

// 2b. Implementar para arrays de uint8_t
void constant_time_select_bytes(uint8_t* dest, 
                                 const uint8_t* true_src,
                                 const uint8_t* false_src,
                                 uint8_t selector, 
                                 size_t len);

// 2c. Implementar constant-time absolute value
int32_t constant_time_abs(int32_t x);

// 2d. Implementar constant-time min/max
int32_t constant_time_min(int32_t a, int32_t b);
int32_t constant_time_max(int32_t a, int32_t b);

// 2e. Usar suas implementações em um cenário real:
// - Receber mensagem com flag secreta
// - Retornar resultado diferente baseado na flag
// - Verificar que timing é constante
```

### Exercício 3: Constant-Time Table Lookup

**Objetivo**: Implementar lookup table constante-time.

```cpp
// Exercício 3: Lookup table seguro

// 3a. Implementar lookup constante-time para tabela de 256 bytes
// O índice pode ser secreto
uint8_t constant_time_lookup(const uint8_t* table, 
                              size_t table_size,
                              uint8_t secret_index);

// 3b. Implementar lookup para tabela de uint32_t
uint32_t constant_time_lookup_u32(const uint32_t* table,
                                   size_t table_size,
                                   uint8_t secret_index);

// 3c. Implementar lookup com múltiplos índices secretos
// Receber array de índices, retornar array de valores
void constant_time_multi_lookup(const uint8_t* table,
                                 size_t table_size,
                                 const uint8_t* secret_indices,
                                 uint8_t* results,
                                 size_t num_lookups);

// 3d. Medir e comparar timing:
// - Tabela normal: acesso com índice variável
// - Tabela constante-time: acesso constante-time
// - Verificar diferença de timing
```

### Exercício 4: Timing Measurement

**Objetivo**: Criar framework de medição de timing.

```cpp
// Exercício 4: Criar framework de medição

// 4a. Implementar classe TimingBenchmark
class TimingBenchmark {
    // Métodos:
    // - medir tempo de execução de função
    // - rodar múltiplas iterações
    // - calcular média, stddev, min, max
    // - gerar relatório
};

// 4b. Testar com código NÃO constante-time
void test_non_constant_time() {
    // Implementar comparação com early return
    // Medir timing
    // Verificar que timing VARIA com input
}

// 4c. Testar com código constante-time
void test_constant_time() {
    // Implementar comparação constante-time
    // Medir timing
    // Verificar que timing é CONSTANTE
}

// 4d. Usar perf counters para análise detalhada
// Medir: cycles, instructions, cache-misses
// Comparar entre constant-time e non-constant-time
```

### Exercício 5: Constant-Time Sorting Network

**Objetivo**: Implementar sorting network constante-time.

```cpp
// Exercício 5: Sorting network

// 5a. Implementar sorting network para 4 elementos
// Usar compare-and-swap constante-time
void sort_4_constant_time(int32_t values[4]);

// 5b. Implementar sorting network para 8 elementos
// Usar rede de Bitonic sort
void sort_8_constant_time(int32_t values[8]);

// 5c. Generalizar para potências de 2
template<size_t N>
void sort_n_constant_time(int32_t values[N]);

// 5d. Testar que sorting é constante-time
// - Medir timing para diferentes inputs
// - Verificar que timing não depende de valores
// - Verificar que timing não depende de ordenação
```

### Exercício 6: Constant-Time Bit Operations

**Objetivo**: Implementar operações de bits constante-time.

```cpp
// Exercício 6: Bit operations

// 6a. Implementar contagem de bits (popcount) constante-time
uint8_t constant_time_popcount(uint64_t x);

// 6b. Implementar leading zeros constante-time
uint8_t constant_time_clz(uint64_t x);

// 6c. Implementar trailing zeros constante-time
uint8_t constant_time_ctz(uint64_t x);

// 6d. Implementar rotação constante-time
uint32_t constant_time_rotl(uint32_t x, uint8_t shift);
uint32_t constant_time_rotr(uint32_t x, uint8_t shift);

// 6e. Implementar verificação de potência de 2
int constant_time_is_power_of_two(uint64_t x);

// 6f. Implementar next potência de 2
uint64_t constant_time_next_power_of_two(uint64_t x);
```

### Exercício 7: Análise com Valgrind

**Objetivo**: Usar ferramentas para validar constant-time.

```cpp
// Exercício 7: Validação com ferramentas

// 7a. Criar programa com código vulnerável
// (comparação com early return)

// 7b. Rodar com Cachegrind
// valgrind --tool=cachegrind ./vulnerable_program

// 7c. Analisar cache misses
// cg_annotate cachegrind.out.*

// 7d. Criar versão constante-time
// Rodar novamente com Cachegrind
// Comparar resultados

// 7e. Criar relatório comparativo
// - Diferenças em cache misses
// - Diferenças em branch misses
// - Conclusão sobre constant-time
```

### Exercício 8: Proteção de Password Hash

**Objetivo**: Implementar verificação de password constante-time.

```cpp
// Exercício 8: Password verification

// 8a. Implementar hash simples (para exercício)
// (NÃO usar em produção!)

// 8b. Implementar comparação de hash constante-time
bool verify_password_constant_time(const char* input, 
                                    const char* stored_hash);

// 8c. Medir timing de:
// - Password correto
// - Password incorreto (primeiro caractere)
// - Password incorreto (último caractere)
// - Password incorreto (tamanho diferente)

// 8d. Verificar que timing é constante
// independentemente de onde o password difere
```

---

## 2.18 Referências

### Referências Primárias

1. **Kocher, P.** (1996). "Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems." *Advances in Cryptology — CRYPTO '96*. LNCS 1109, pp. 104-113.

2. **Bernstein, D. J.** (2005). "Cache-timing attacks on AES." *Technical Report*.

3. **Osvik, D. A., Shamir, A., & Tromer, E.** (2006). "Cache Attacks and Countermeasures: the Case of AES." *CT-RSA 2006*. LNCS 3860, pp. 1-20.

4. **Brumley, B. B., & Boneh, D.** (2003). "Remote Timing Attacks are Practical." *Computer Networks*, 43(4), pp. 525-541.

5. **AlFardan, N. J., Bernstein, D. J., Paterson, K. G., Poettering, B., & Schuldt, J. C. N.** (2013). "On the Security of RC4 in TLS." *USENIX Security Symposium*.

### Referências sobre CVEs

6. **CVE-2019-1547**: OpenSSL ECDSA Timing Side-Channel. https://nvd.nist.gov/vuln/detail/CVE-2019-1547

7. **CVE-2013-0169**: Lucky13 Padding Oracle Attack. https://nvd.nist.gov/vuln/detail/CVE-2013-0169

8. **Jancar, J., Faltsetas, V., Kuli, M., Kvašš, M., & Sys, M.** (2020). "Minerva: The curse of ECDSA nonces." *IACR ePrint Archive*.

### Referências sobre Constant-Time Programming

9. **Costello, C.** (2005). "Constant-Time Programming." *Technical Report*.

10. **Schwabe, P.** (2014). "Never trust a AVR Studio simulation: AVRCrypto library." *CHES 2014*.

11. **Bernstein, D. J.** (2014). "How to make constant-time code really constant-time." *Talk at Real World Crypto*.

12. **Lipp, B., Blanchoult, D., Helden, D., & Moss, A.** (2016). "Modding the Mach-O file format for constant-time computations." *Technical Report*.

### Referências sobre Validação

13. **Nccgroup** (2018). "Understanding and exploiting the power of the DDR4 DRAM rowhammer bug." *Technical Report*.

14. **Valgrind Documentation**. https://valgrind.org/docs/manual/manual.html

15. **Linux perf Documentation**. https://perf.wiki.kernel.org/index.php/Main_Page

### Referências sobre Bibliotecas

16. **OpenSSL Documentation**. https://www.openssl.org/docs/

17. **libsodium Documentation**. https://doc.libsodium.org/

18. **BoringSSL Documentation**. https://boringssl.googlesource.com/boringssl/

### Livros Recomendados

19. **Stallings, W.** (2017). *Cryptography and Network Security: Principles and Practice*. 7th Edition. Pearson.

20. **Schneier, B.** (2015). *Applied Cryptography: Protocols, Algorithms, and Source Code in C*. 20th Anniversary Edition. Wiley.

21. **Menezes, A. J., van Oorschot, P. C., & Vanstone, S. A.** (2001). *Handbook of Applied Cryptography*. CRC Press.

22. **Boneh, D., & Shoup, V.** (2020). *A Graduate Course in Applied Cryptography*. Version 0.5.

### RFCs Relevantes

23. **RFC 6979** - Deterministic Usage of the Digital Signature Algorithm (DSA) and Elliptic Curve Digital Signature Algorithm (ECDSA).

24. **RFC 7366** - Encrypt-then-MAC for Transport Layer Security (TLS) and Datagram Transport Layer Security (DTLS).

25. **RFC 8446** - The Transport Layer Security (TLS) Protocol Version 1.3.

---

## Resumo do Capítulo

Neste capítulo, exploramos os fundamentos de programação constant-time, uma disciplina essencial para implementações criptográficas seguras. Cobrimos:

1. **Definição formal e prática** de constant-time programming
2. **Otimizações de compilador** que podem quebrar invariantes de timing
3. **Ataques de timing** (local, remoto, cache-based)
4. **Técnicas C++17** para implementar operações constante-time
5. **Assembly intrinsics** para x86-64 e ARM64
6. **Bibliotecas** OpenSSL e libsodium
7. **Validação** usando Valgrind e perf counters
8. **CVEs reais** que demonstram a importância de constant-time

O capítulo enfatiza que constant-time programming não é apenas uma técnica, mas uma **mentalidade** que deve permeiar toda a implementação criptográfica. Cada decisão de implementação deve considerar seu impacto em timing side-channels.

No próximo capítulo, veremos como aplicar esses fundamentos em algoritmos criptográficos específicos.

---

*Fim do Capítulo 02*
