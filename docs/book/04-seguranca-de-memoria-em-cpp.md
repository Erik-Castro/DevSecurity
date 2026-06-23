# Capítulo 4 — Segurança de Memória em C++

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Identificar e classificar** vulnerabilidades de memória em código C++, incluindo buffer overflows, use-after-free, integer overflows e dangling pointers.
2. **Compreender o modelo de memória** de um processo C++ no nível do sistema operacional, incluindo layout de segmentos, stack, heap e suas implicações de segurança.
3. **Aplicar mitigações de compilador e sistema operacional** — ASLR, stack canaries, DEP/NX, RELRO — e verificar sua eficácia com ferramentas como `readelf` e `checksec`.
4. **Utilizar sanitizadores** (AddressSanitizer, MemorySanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer) para detecção de erros de memória em tempo de execução.
5. **Projetar e implementar padrões seguros de gerenciamento de memória** utilizando smart pointers, RAII, arena allocators e classes de wrapper para recursos sensíveis.
6. **Analisar CVEs reais** — Heartbleed, EternalBlue, Spectre, Meltdown e outros — para entender como vulnerabilidades de memória são exploradas em produção e como preveni-las.

---

## 1. Fundamentos de Memória em C++

### 1.1 O Modelo de Memória do Processo

Quando um executável C++ é carregado pelo sistema operacional, o kernel mapeia seu conteúdo em um espaço de endereçamento virtual organizado em segmentos bem definidos. Cada segmento possui permissões de acesso distintas — leitura, escrita e execução — que são a primeira barreira de defesa contra exploração.

O layout típico de um processo C++ no Linux é o seguinte:

```
+-------------------------+ 0xFFFFFFFFFFFFFFFF (topo do espaço de endereçamento)
|        Kernel Space      |  (não acessível pelo usuário)
+-------------------------+ 0x7FFFFFFFFFFF
|         Stack            |  ← cresce para baixo (endereços menores)
|    (argumentos locais,   |
|     variáveis automátics,|
|     frames de retorno)   |
|            ↓              |
+-------------------------+
|         (gap)            |  ← proteção contra colisão
|            ↑              |
+-------------------------+
|          Heap            |  ← cresce para cima (endereços maiores)
|    (new, malloc,         |
|     alocações dinâmicas) |
+-------------------------+
|          BSS             |  ← variáveis globais não inicializadas
+-------------------------+
|         Data             |  ← variáveis globais inicializadas
+-------------------------+
|         Text             |  ← código executável (somente leitura)
+-------------------------+ 0x400000 (típico no x86-64 Linux)
```

### 1.2 Alocação Dinâmica de Memória

C++ oferece dois mecanismos principais para alocação dinâmica: `new`/`delete` para objetos individuais e `new[]`/`delete[]` para arrays. Ambos delegam ao alocador do sistema operacional para blocos grandes e utilizam pools internos para blocos pequenos.

```cpp
#include <iostream>
#include <cstring>
#include <new>

// Exemplo de alocação dinâmica com verificação de segurança
class SecureBuffer {
public:
    explicit SecureBuffer(size_t size) : size_(size), data_(nullptr) {
        // Verificação contra tamanho zero e overflow na multiplicação
        if (size == 0) {
            throw std::invalid_argument("Buffer size cannot be zero");
        }

        // Proteção contra integer overflow na alocação
        constexpr size_t max_alloc = 1ULL << 32; // 4 GB
        if (size > max_alloc) {
            throw std::overflow_error("Allocation size exceeds maximum");
        }

        data_ = new(std::nothrow) std::uint8_t[size];
        if (data_ == nullptr) {
            throw std::bad_alloc();
        }

        // Inicializa toda a memória com zero — evita dados residuais
        std::memset(data_, 0, size);
    }

    ~SecureBuffer() {
        if (data_ != nullptr) {
            // Zera a memória antes de liberar — evita dados residuais
            // Em sistemas de segurança, dados em memória liberada podem
            // ser recuperados por outro processo
            volatile std::uint8_t* vdata = data_;
            for (size_t i = 0; i < size_; ++i) {
                vdata[i] = 0;
            }
            delete[] data_;
            data_ = nullptr;
        }
    }

    // Impede cópia — evita double-free
    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;

    // Permite movimento — transferência segura de propriedade
    SecureBuffer(SecureBuffer&& other) noexcept
        : size_(other.size_), data_(other.data_) {
        other.size_ = 0;
        other.data_ = nullptr;
    }

    std::uint8_t* data() { return data_; }
    size_t size() const { return size_; }

    // Acesso seguro com bounds checking
    std::uint8_t& at(size_t index) {
        if (index >= size_) {
            throw std::out_of_range("Buffer index out of range");
        }
        return data_[index];
    }

private:
    size_t size_;
    std::uint8_t* data_;
};

int main() {
    try {
        SecureBuffer buf(256);
        buf.at(0) = 0x41;
        buf.at(255) = 0x42;
        std::cout << "Buffer created successfully, size: "
                  << buf.size() << "\n";

        // Isso lançaria std::out_of_range:
        // buf.at(256) = 0x43;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
    }
    return 0;
}
```

### 1.3 Pools de Memória e Alocadores Customizados

Em aplicações de segurança — servidores de rede, firewalls, sistemas de detecção de intrusão — a alocação dinâmica padrão pode ser um gargalo e uma superfície de ataque. Alocadores customizados com pools pré-alocados reduzem tanto a latência quanto o risco de heap corruption.

```cpp
#include <array>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <mutex>
#include <vector>

// Arena allocator com tamanho fixo por bloco
// Reduz fragmentação e previne heap spraying
class ArenaAllocator {
public:
    static constexpr size_t BLOCK_SIZE = 4096;
    static constexpr size_t MAX_BLOCKS = 256;

    ArenaAllocator() : current_block_(0), current_offset_(0) {
        for (auto& block : blocks_) {
            block.fill(0);
        }
    }

    // Alopca um objeto dentro do arena
    template <typename T, typename... Args>
    T* allocate(Args&&... args) {
        static_assert(sizeof(T) <= BLOCK_SIZE,
                      "Object exceeds block size");

        std::lock_guard<std::mutex> lock(mutex_);

        // Alinhamento para garantir acesso seguro
        constexpr size_t alignment = alignof(T);
        size_t aligned_offset = (current_offset_ + alignment - 1)
                                & ~(alignment - 1);

        // Se não cabe no bloco atual, avança para o próximo
        if (aligned_offset + sizeof(T) > BLOCK_SIZE) {
            ++current_block_;
            if (current_block_ >= MAX_BLOCKS) {
                return nullptr; // Arena esgotada
            }
            current_offset_ = 0;
            aligned_offset = 0;
        }

        void* mem = &blocks_[current_block_][aligned_offset];
        current_offset_ = aligned_offset + sizeof(T);

        // Constrói o objeto no memória alocada
        return new (mem) T(std::forward<Args>(args)...);
    }

    // Libera todos os objetos do arena de uma vez
    void reset() {
        std::lock_guard<std::mutex> lock(mutex_);
        current_block_ = 0;
        current_offset_ = 0;
        // Zera todos os blocos para limpar dados residuais
        for (auto& block : blocks_) {
            block.fill(0);
        }
    }

    size_t allocated() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return current_block_ * BLOCK_SIZE + current_offset_;
    }

private:
    std::array<std::array<std::uint8_t, BLOCK_SIZE>, MAX_BLOCKS> blocks_;
    size_t current_block_;
    size_t current_offset_;
    mutable std::mutex mutex_;
};

struct ConnectionRecord {
    uint32_t id;
    uint64_t timestamp;
    char hostname[64];

    ConnectionRecord(uint32_t id, uint64_t ts, const char* name)
        : id(id), timestamp(ts) {
        std::strncpy(hostname, name, sizeof(hostname) - 1);
        hostname[sizeof(hostname) - 1] = '\0';
    }
};

int main() {
    ArenaAllocator arena;

    for (uint32_t i = 0; i < 100; ++i) {
        auto* conn = arena.allocate<ConnectionRecord>(
            i, 1700000000ULL + i, "example.host"
        );
        if (conn == nullptr) {
            std::cerr << "Arena exhausted at record " << i << "\n";
            break;
        }
    }

    std::cout << "Allocated: " << arena.allocated() << " bytes\n";
    arena.reset(); // Libera tudo de uma vez — seguro e rápido
    std::cout << "After reset: " << arena.allocated() << " bytes\n";
    return 0;
}
```

---

## 2. Buffer Overflows

### 2.1 Visão Geral

Buffer overflows são a classe mais antiga e persistente de vulnerabilidades de memória. Um overflow ocorre quando dados são escritos além dos limites de um buffer alocado, corrompendo memória adjacente. Conforme documentado pela CWE (Common Weakness Enumeration), o CWE-120 é a entrada para todas as variantes de buffer overflow.

**Heartbleed (CVE-2014-0160)**: Uma das vulnerabilidades mais devastadoras da história, afetou o OpenSSL. O bug estava na implementação do heartbeat TLS/DTLS. O servidor retornava conteúdo de memória sem verificar se o comprimento declarado pelo cliente correspondia ao dado realmente enviado.

```cpp
// ============================================================
// Caso CVE-2014-0160 (Heartbleed) — Simulação em C++
// O servidor retorna dados sem validar o comprimento real
// ============================================================

#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>

// Simula o buffer interno do servidor
struct TlsContext {
    std::vector<std::uint8_t> internal_buffer;
    size_t buffer_len;

    TlsContext() : buffer_len(0) {
        // Preenche com dados sensíveis simulados (chaves, tokens)
        const char* secret = "SECRET_KEY_1234567890123456";
        internal_buffer.resize(1024, 0);
        std::memcpy(internal_buffer.data(), secret, std::strlen(secret));
        buffer_len = internal_buffer.size();
    }
};

// ============================================================
// CÓDIGO VULNERÁVEL — Heartbleed-style over-read
// ============================================================
// O atacante envia um heartbeat request com payload de N bytes
// e declara um comprimento M >> N.
// O servidor retorna M bytes a partir do payload, incluindo
// dados sensíveis que não fazem parte da requisição.
std::vector<std::uint8_t> vulnerable_heartbeat(
    const TlsContext& ctx,
    const std::uint8_t* payload,
    size_t payload_len,
    size_t declared_len     // comprimento declarado pelo cliente
) {
    // BUG FATAL: declared_len NÃO é validado contra payload_len
    // O servidor confia no valor declarado pelo cliente
    std::vector<std::uint8_t> response(declared_len);

    // Copia declared_len bytes a partir do payload
    // Se declared_len > payload_len, lê memória além do payload
    std::memcpy(response.data(), payload, declared_len);
    return response;
}

// ============================================================
// CÓDIGO SEGURO — Validação adequada do comprimento
// ============================================================
std::vector<std::uint8_t> secure_heartbeat(
    const TlsContext& ctx,
    const std::uint8_t* payload,
    size_t payload_len,
    size_t declared_len
) {
    // 1. Verifica que declared_len não excede o payload real
    if (declared_len > payload_len) {
        std::cerr << "[SECURITY] Heartbeat length mismatch\n";
        return {};
    }

    // 2. Verifica limite máximo de resposta
    constexpr size_t MAX_HEARTBEAT_RESPONSE = 65535;
    if (declared_len > MAX_HEARTBEAT_RESPONSE) {
        std::cerr << "[SECURITY] Heartbeat response too large\n";
        return {};
    }

    // 3. Copia apenas o tamanho válido
    std::vector<std::uint8_t> response(declared_len);
    std::memcpy(response.data(), payload, declared_len);
    return response;
}

void demonstrate_heartbleed() {
    std::cout << "=== Heartbleed (CVE-2014-0160) ===\n\n";

    TlsContext ctx;

    // Atacante envia apenas 4 bytes de payload
    // mas declara comprimento de 256
    std::uint8_t small_payload[4] = {0x01, 0x02, 0x03, 0x04};

    auto leaked = vulnerable_heartbeat(ctx, small_payload, 4, 256);

    std::cout << "[VULN] Server returned " << leaked.size()
              << " bytes (leaked sensitive data):\n  ";
    for (size_t i = 0; i < std::min(leaked.size(), size_t(32)); ++i) {
        printf("%02x ", leaked[i]);
    }
    std::cout << "\n\n";

    auto safe = secure_heartbeat(ctx, small_payload, 4, 256);
    std::cout << "[SAFE] Server returned " << safe.size()
              << " bytes (rejected oversized request)\n";
}

int main() {
    demonstrate_heartbleed();
    return 0;
}
```

### 2.2 Stack-Based Buffer Overflow

O overflow de stack é a forma clássica de exploração de memória. Quando uma função declara um buffer local na stack e escreve além de seus limites, ela sobrescreve o endereço de retorno armazenado no frame. Ao retornar, o processador pula para o endereço atacante.

```cpp
#include <cstdio>
#include <cstring>
#include <iostream>

// ============================================================
// CÓDIGO VULNERÁVEL — Stack buffer overflow clássico
// ============================================================
// Morris Worm (1988) utilizou overflow semelhante no fingerd
// do BSD Unix, onde um buffer de 512 bytes era preenchido
// sem validação de comprimento.
void vulnerable_login(const char* username) {
    char buffer[64]; // Buffer fixo na stack

    // Overflow: strcpy não valida o comprimento
    // Se username tem > 64 bytes, sobrescreve EBP e RET
    std::strcpy(buffer, username);

    printf("Login attempt: %s\n", buffer);
}

// ============================================================
// CÓDIGO SEGURO — Validação de comprimento
// ============================================================
void secure_login(const char* username) {
    char buffer[64];

    // Verifica o comprimento antes de copiar
    if (std::strlen(username) >= sizeof(buffer)) {
        std::cerr << "[SECURITY] Username too long, rejected\n";
        return;
    }

    // strncpy garante que no máximo sizeof(buffer)-1 bytes
    // são copiados, preservando o null terminator
    std::strncpy(buffer, username, sizeof(buffer) - 1);
    buffer[sizeof(buffer) - 1] = '\0';

    printf("Login attempt: %s\n", buffer);
}

// Versão moderna: usa std::string para evitar overflow completamente
void modern_login(const std::string& username) {
    if (username.size() >= 64) {
        std::cerr << "[SECURITY] Username too long\n";
        return;
    }
    // std::string gerencia a memória automaticamente
    std::string safe = username;
    printf("Login attempt: %s\n", safe.c_str());
}

int main() {
    // Demonstração do overflow
    std::cout << "=== Stack Buffer Overflow ===\n\n";

    // Isso causaria overflow em produção:
    // char long_input[128];
    // std::memset(long_input, 'A', 127);
    // long_input[127] = '\0';
    // vulnerable_login(long_input);

    // Versão segura:
    secure_login("admin");
    std::cout << "Secure login works correctly\n";
    return 0;
}
```

### 2.3 Heap-Based Buffer Overflow

Diferente do stack overflow, o heap overflow corrompe estruturas de controle do heap (malloc metadata, free lists). Isso permite manipular alocações e liberações subsequentes, potencialmente resultando em execução arbitrária de código.

### 2.4 Format String Attacks

Format string vulnerabilities ocorrem quando dados de entrada do usuário são passados diretamente como argumento de formato para funções como `printf`. Um atacante pode usar `%x` para ler da stack ou `%n` para escrever em endereços arbitrários.

```cpp
#include <cstdio>
#include <cstring>
#include <iostream>

// ============================================================
// CÓDIGO VULNERÁVEL — Format string attack
// ============================================================
void vulnerable_log(const char* user_input) {
    // Se user_input contém "%x.%x.%x.%x", expõe dados da stack
    // Se user_input contém "%n", escreve no endereço da stack
    printf(user_input);
    printf("\n");
}

// ============================================================
// CÓDIGO SEGURO — Formato como literal
// ============================================================
void secure_log(const char* user_input) {
    // O formato é literal — user_input é tratado como dado
    printf("%s\n", user_input);
}

int main() {
    std::cout << "=== Format String Attack ===\n\n";

    // Demonstração: format string pode ler da stack
    const char* malicious = "%08x.%08x.%08x";
    std::cout << "[VULN] Malicious input: " << malicious << "\n";
    vulnerable_log(malicious);

    std::cout << "\n[SAFE] Same input handled safely:\n";
    secure_log(malicious);
    return 0;
}
```

### 2.5 Mitigações de Buffer Overflow

| Mitigação | Mecanismo | Flag de Compilador |
|-----------|-----------|-------------------|
| Stack Canaries | Valor aleatório entre buffer e return address | `-fstack-protector-strong` |
| ASLR | Randomiza endereços de stack, heap e bibliotecas | `-fPIE -pie` |
| DEP/NX | Impede execução de código em regiões de dados | `-Wl,-z,noexecstack` |
| RELRO | Torna seções de GOT somente leitura | `-Wl,-z,relro -Wl,-z,now` |

---

## 3. Use-After-Free e Double-Free

### 3.1 Mecânica de Use-After-Free

Use-after-free (UAF) ocorre quando um ponteiro continua referenciando memória que foi liberada. Se o alocador reutilizar esse bloco para outro propósito, o ponteiro antigo passa a apontar para dados controlados pelo atacante.

### 3.2 CVE-2023-33106 — Qualcomm GPU Use-After-Free

Esta vulnerabilidade no driver GPU da Qualcomm permitiu execução arbitrária de código no kernel a partir de um app Android. O bug ocorria quando o driver liberava um buffer de framebuffer e permitia acesso a ele através de uma referência dangling.

```cpp
#include <iostream>
#include <memory>
#include <cstring>

// ============================================================
// Simulação de CVE-2023-33106 — Qualcomm GPU UAF
// ============================================================

struct GpuBuffer {
    uint32_t width;
    uint32_t height;
    void* data;
    bool freed;

    GpuBuffer(uint32_t w, uint32_t h)
        : width(w), height(h), freed(false) {
        data = new uint8_t[w * h * 4];
        std::memset(data, 0, w * h * 4);
        std::cout << "GPU buffer allocated: " << w << "x" << h << "\n";
    }

    ~GpuBuffer() {
        if (!freed) {
            delete[] static_cast<uint8_t*>(data);
        }
    }
};

// ============================================================
// CÓDIGO VULNERÁVEL — UAF via referência dangling
// ============================================================
void vulnerable_gpu_render(GpuBuffer* buffer) {
    // Passo 1: driver libera o buffer para reuso
    delete[] static_cast<uint8_t*>(buffer->data);
    buffer->data = nullptr;
    buffer->freed = true;
    std::cout << "[VULN] Buffer freed\n";

    // Passo 2: outro componente aloca memória no mesmo endereço
    // (simula heap spray do atacante)
    uint8_t* attacker_data = new uint8_t[buffer->width * buffer->height * 4];
    std::memset(attacker_data, 0x41, buffer->width * buffer->height * 4);
    std::cout << "[VULN] Attacker allocated overlapping buffer\n";

    // Passo 3: driver ainda tem referência ao buffer antigo
    // e tenta renderizar — acessa dados do atacante
    // Em código real, isto resulta em execução arbitrária
    auto* stale = reinterpret_cast<GpuBuffer*>(buffer);
    if (stale->data != nullptr) {
        // Este acesso é UAF — memória foi liberada e reutilizada
        std::cout << "[VULN] Rendering stale buffer data\n";
    }

    delete[] attacker_data;
}

// ============================================================
// CÓDIGO SEGURO — Smart pointers e invalidation
// ============================================================
class SecureGpuBuffer {
public:
    SecureGpuBuffer(uint32_t w, uint32_t h)
        : width_(w), height_(h),
          data_(std::make_unique<uint8_t[]>(w * h * 4)),
          valid_(true) {
        std::memset(data_.get(), 0, w * h * 4);
    }

    // Libera o buffer e invalida todas as referências
    void release() {
        if (data_) {
            std::memset(data_.get(), 0, width_ * height_ * 4);
            data_.reset();
        }
        valid_ = false;
    }

    // Verifica validade antes de acessar
    bool render() {
        if (!valid_ || !data_) {
            std::cerr << "[SECURITY] Attempted render on invalid buffer\n";
            return false;
        }
        // Render seguro com buffer válido
        std::cout << "[SAFE] Rendering valid buffer: "
                  << width_ << "x" << height_ << "\n";
        return true;
    }

    bool is_valid() const { return valid_; }

private:
    uint32_t width_;
    uint32_t height_;
    std::unique_ptr<uint8_t[]> data_;
    bool valid_;
};

// ============================================================
// CVE-2021-1048 — Android Binder UAF (CVE-2023-26083)
// ============================================================
// O binder do Android允许 referências a objetos IPC
// que foram liberados pelo processo remoto.
// O kernel retornava dados sensíveis de outros processos.

struct BinderNode {
    uint32_t id;
    void* data;
    bool alive;

    BinderNode(uint32_t id) : id(id), data(nullptr), alive(true) {
        data = new uint8_t[256];
        std::memset(data, 0, 256);
    }

    ~BinderNode() {
        if (alive && data) {
            delete[] static_cast<uint8_t*>(data);
        }
    }
};

void vulnerable_binder_release(BinderNode* node) {
    // Libera os dados mas não invalida a referência
    delete[] static_cast<uint8_t*>(node->data);
    node->data = nullptr;
    node->alive = false;
    // BUG: outro thread pode acessar node->data ainda
}

void secure_binder_release(std::shared_ptr<BinderNode>& node) {
    if (node) {
        // Zera a memória antes de liberar
        if (node->data) {
            volatile uint8_t* vdata =
                static_cast<volatile uint8_t*>(node->data);
            for (int i = 0; i < 256; ++i) vdata[i] = 0;
        }
        // shared_ptr gerencia a contagem de referências
        // O objeto é destruído quando a última referência é liberada
        node.reset();
    }
}

int main() {
    std::cout << "=== Use-After-Free ===\n\n";

    // Demonstração segura do SecureGpuBuffer
    SecureGpuBuffer buffer(64, 64);
    buffer.render();
    buffer.release();
    buffer.render(); // Rejeitado com segurança

    std::cout << "\n=== Double-Free Prevention ===\n\n";
    // unique_ptr previne double-free automaticamente
    auto node = std::make_shared<BinderNode>(42);
    secure_binder_release(node);
    // node agora é nullptr — double-free é impossível

    return 0;
}
```

### 3.3 Heap Spray

Heap spray é uma técnica onde o atacante preenche grandes porções do heap com dados controlados, aumentando a probabilidade de que uma UAF aponte para memória do atacante. O uso de arena allocators e randomização de heap (ASLR) mitiga parcialmente essa técnica.

---

## 4. Integer Overflows e Arithmetic

### 4.1 Signed vs Unsigned Integer Overflow

Em C++, integer overflow em tipos sem sinal (`unsigned`) é definido como wrap-around (módulo 2^N), mas overflow em tipos com sinal (`signed`) é **comportamento indefinido** (undefined behavior — UB). Compiladores podem otimizar código que depende de overflow de formas inesperadas.

```cpp
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>

// ============================================================
// CÓDIGO VULNERÁVEL — Integer overflow em cálculo de tamanho
// ============================================================
// Quando size = count * sizeof(int) faz overflow, o buffer
// alocado é menor que o esperado, e a iteração subsequente
// escreve além dos limites.
void* vulnerable_array_alloc(uint32_t count) {
    // Se count = 0x40000001, sizeof(int) = 4
    // count * sizeof(int) = 0x100000004 → truncado para 0x04
    // Aloca apenas 4 bytes em vez de ~1 GB
    uint32_t size = count * sizeof(int);
    int* arr = new int[size / sizeof(int)];
    for (uint32_t i = 0; i < count; ++i) {
        arr[i] = static_cast<int>(i); // HEAP OVERFLOW aqui
    }
    return arr;
}

// ============================================================
// CÓDIGO SEGURO — Verificação de overflow
// ============================================================
void* secure_array_alloc(uint32_t count) {
    // Verifica overflow antes da multiplicação
    constexpr uint32_t max_count =
        std::numeric_limits<uint32_t>::max() / sizeof(int);
    if (count > max_count) {
        std::cerr << "[SECURITY] Integer overflow detected\n";
        return nullptr;
    }

    size_t size = static_cast<size_t>(count) * sizeof(int);
    int* arr = new(std::nothrow) int[size / sizeof(int)];
    if (arr == nullptr) {
        return nullptr;
    }

    for (uint32_t i = 0; i < count; ++i) {
        arr[i] = static_cast<int>(i);
    }
    return arr;
}

// ============================================================
// Biblioteca de aritmética segura
// ============================================================
namespace safe_math {

// Soma segura com detecção de overflow
template <typename T>
bool add(T a, T b, T& result) {
    if (b > 0 && a > std::numeric_limits<T>::max() - b) {
        return false; // overflow positivo
    }
    if (b < 0 && a < std::numeric_limits<T>::min() - b) {
        return false; // overflow negativo
    }
    result = a + b;
    return true;
}

// Multiplicação segura com detecção de overflow
template <typename T>
bool multiply(T a, T b, T& result) {
    if (a == 0 || b == 0) {
        result = 0;
        return true;
    }

    T abs_a = (a < 0) ? -a : a;
    T abs_b = (b < 0) ? -b : b;

    if (abs_a > std::numeric_limits<T>::max() / abs_b) {
        return false;
    }

    result = a * b;
    return true;
}

} // namespace safe_math

// ============================================================
// Width conversion vulnerability
// ============================================================
void demonstrate_width_conversion() {
    std::cout << "\n=== Width Conversion Vulnerability ===\n\n";

    // Simula um tamanho de 64-bit truncado para 32-bit
    uint64_t large_size = 0x100000005ULL; // ~4 GB + 5 bytes
    uint32_t truncated = static_cast<uint32_t>(large_size);

    std::cout << "[VULN] 64-bit size: 0x" << std::hex << large_size
              << std::dec << "\n";
    std::cout << "[VULN] Truncated to 32-bit: " << truncated << "\n";
    std::cout << "[VULN] Buffer would be " << truncated
              << " bytes instead of " << large_size << "\n";
}

int main() {
    std::cout << "=== Integer Overflow ===\n\n";

    uint32_t result;
    if (!safe_math::multiply(uint32_t{0x40000001}, uint32_t{4}, result)) {
        std::cout << "[SAFE] Overflow detected in multiplication\n";
    }

    demonstrate_width_conversion();
    return 0;
}
```

---

## 5. Dangling Pointers e Reference Management

### 5.1 Problemas de Ponteiros Pendurados

Um dangling pointer existe quando um ponteiro referencia memória que foi liberada. Em C++, isso pode ocorrer de múltiplas formas:

```cpp
#include <iostream>
#include <memory>
#include <vector>

// ============================================================
// CÓDIGO VULNERÁVEL — Dangling pointer após free
// ============================================================
struct NetworkConnection {
    int id;
    char data[1024];
};

NetworkConnection* vulnerable_create_connection() {
    NetworkConnection* conn = new NetworkConnection();
    conn->id = 42;
    std::memset(conn->data, 0, sizeof(conn->data));
    return conn;
    // Se o chamador esquece de deletar, tem memory leak
    // Se deleta e continua usando, tem use-after-free
}

// ============================================================
// CÓDIGO SEGURO — Smart pointers
// ============================================================
std::unique_ptr<NetworkConnection> secure_create_connection() {
    auto conn = std::make_unique<NetworkConnection>();
    conn->id = 42;
    std::memset(conn->data, 0, sizeof(conn->data));
    return conn; // Propriedade transferida para o chamador
}

// ============================================================
// Problema de iteradores invalidados
// ============================================================
void vulnerable_iterator_invalidated() {
    std::vector<int> vec = {1, 2, 3, 4, 5};
    auto it = vec.begin();

    // push_back pode realocar o vector, invalidando todos os iteradores
    vec.push_back(6);

    // Dangling iterator — comportamento indefinido
    // int val = *it; // BUG: it não é mais válido
    (void)it;
}

void secure_iterator_usage() {
    std::vector<int> vec = {1, 2, 3, 4, 5};
    auto it = vec.begin();

    // Salva o índice em vez do iterador
    size_t index = it - vec.begin();

    vec.push_back(6);

    // Usa o índice — seguro mesmo após realocação
    if (index < vec.size()) {
        int val = vec[index];
        std::cout << "Value: " << val << "\n";
    }
}

// ============================================================
// Pool de objetos com contagem de referências
// ============================================================
template <typename T>
class ReferenceCountedPool {
public:
    struct Entry {
        std::unique_ptr<T> object;
        int ref_count;
        bool in_use;

        Entry() : ref_count(0), in_use(false) {}
    };

    explicit ReferenceCountedPool(size_t capacity)
        : entries_(capacity) {
        for (auto& entry : entries_) {
            entry.object = std::make_unique<T>();
        }
    }

    // Obtém um objeto do pool
    T* acquire() {
        for (auto& entry : entries_) {
            if (!entry.in_use) {
                entry.in_use = true;
                entry.ref_count = 1;
                return entry.object.get();
            }
        }
        return nullptr; // Pool esgotado
    }

    // Libera um objeto de volta ao pool
    void release(T* obj) {
        for (auto& entry : entries_) {
            if (entry.object.get() == obj && entry.in_use) {
                --entry.ref_count;
                if (entry.ref_count <= 0) {
                    entry.in_use = false;
                    entry.ref_count = 0;
                    // Zera a memória antes de reutilizar
                    std::memset(entry.object.get(), 0, sizeof(T));
                }
                return;
            }
        }
    }

private:
    std::vector<Entry> entries_;
};

int main() {
    std::cout << "=== Dangling Pointers ===\n\n";

    // Smart pointer previne dangling
    auto conn = secure_create_connection();
    std::cout << "Connection ID: " << conn->id << "\n";
    // conn é automaticamente deletado quando sai do escopo

    secure_iterator_usage();

    std::cout << "\n=== Reference Counted Pool ===\n\n";
    ReferenceCountedPool<NetworkConnection> pool(10);
    NetworkConnection* c1 = pool.acquire();
    NetworkConnection* c2 = pool.acquire();
    std::cout << "Acquired connections: "
              << (c1 != nullptr) << ", " << (c2 != nullptr) << "\n";
    pool.release(c1);
    pool.release(c2);

    return 0;
}
```

---

## 6. Mitigações de Compilador e Sistema Operacional

### 6.1 Stack Canaries

O GCC e Clang suportam a inserção de canaries (valores sentinelas) entre buffers locais e o endereço de retorno na stack. Quando um buffer overflow sobrescreve a canary, o valor é corrompido e o runtime detecta a tentativa antes de retornar.

```bash
# Habilita stack canaries fortes
# O compilador escolhe quais funções precisam de canary
# baseado na complexidade do buffer local
g++ -fstack-protector-strong -o secure_app main.cpp
```

### 6.2 ASLR (Address Space Layout Randomization)

```bash
# Compila como Position-Independent Executable (PIE)
# Isso permite que o kernel randomize o endereço base do executável
g++ -fPIE -pie -o secure_app main.cpp

# Verifica se ASLR está habilitado no sistema
cat /proc/sys/kernel/randomize_va_space
# 0 = desabilitado, 1 = parcial, 2 = completo (recomendado)
```

### 6.3 DEP/NX (Data Execution Prevention)

```bash
# Marca as seções de dados como não-executáveis
# Qualquer tentativa de executar código nestas seções causa SIGSEGV
g++ -Wl,-z,noexecstack -o secure_app main.cpp

# Verifica se a marcação NX está presente
readelf -l secure_app | grep GNU_STACK
# Se a flag não tem 'E' (exec), NX está ativo
```

### 6.4 RELRO (Relocation Read-Only)

```bash
# Torna a Global Offset Table (GOT) somente leitura após resolução
# Isso previne ataques que sobrescrevem ponteiros de função
g++ -Wl,-z,relro -Wl,-z,now -o secure_app main.cpp

# Full RELRO: toda a GOT é resolvida e marcada somente leitura
# na carga do programa
```

### 6.5 Configuração CMake Completa com Todas as Mitigações

```cmake
cmake_minimum_required(VERSION 3.15)
project(SecureApp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================================
# Hardening flags
# ============================================================

# Stack protector
add_compile_options(-fstack-protector-strong)

# Position-independent code
add_compile_options(-fPIE)
add_link_options(-pie)

# Non-executable stack
add_link_options(-Wl,-z,noexecstack)

# Full RELRO
add_link_options(-Wl,-z,relro -Wl,-z,now)

# Fortify source
add_compile_options(-D_FORTIFY_SOURCE=2)

# Warnings como erros
add_compile_options(-Wall -Wextra -Werror -Wpedantic)

# ============================================================
# Executável principal
# ============================================================
add_executable(secure_app main.cpp)

# ============================================================
# Configuração de build segura
# ============================================================
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Em debug, habilita sanitizadores
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_compile_options(secure_app PRIVATE
        -fsanitize=address,undefined,leak
        -fno-omit-frame-pointer
    )
    target_link_options(secure_app PRIVATE
        -fsanitize=address,undefined,leak
    )
endif()
```

### 6.6 Verificação de Mitigações

```bash
# Verifica todas as proteções em um binário
# Ferramenta checksec (disponível em many GDB distributions)

# Verificação manual com readelf/readobj:
echo "=== RELRO ==="
readelf -l secure_app | grep GNU_RELRO

echo "=== Stack Canary ==="
readelf -s secure_app | grep __stack_chk_fail

echo "=== NX (Non-Executable Stack) ==="
readelf -l secure_app | grep GNU_STACK

echo "=== PIE ==="
file secure_app
# Deve mostrar "shared object" em vez de "executable"

echo "=== FORTIFY ==="
readelf -s secure_app | grep _chk
# Presença de funções _chk indica FORTIFY ativo
```

---

## 7. Sanitizadores

### 7.1 AddressSanitizer (ASan)

ASan é o sanitizador mais abrangente, detectando buffer overflows, use-after-free, double-free, memory leaks e mais. A sobrecarga típica é de 2x-3x em tempo de execução e 10%-20% em uso de memória.

```cpp
#include <cstdio>
#include <cstdlib>
#include <cstring>

// ============================================================
// Código que dispara ASan: buffer overflow na stack
// ============================================================
void trigger_stack_overflow() {
    char buffer[32];
    // Escreve além do buffer — ASan detecta imediatamente
    std::memset(buffer, 'A', 64); // overflow: 64 > 32
    buffer[63] = '\0';
    printf("Buffer: %s\n", buffer);
}

// ============================================================
// Código que dispara ASan: use-after-free
// ============================================================
void trigger_uaf() {
    int* ptr = new int(42);
    delete ptr;
    // UAF: acessa memória já liberada
    printf("Value: %d\n", *ptr);
}

// ============================================================
// Compilação com sanitizadores
// ============================================================
// g++ -fsanitize=address -fno-omit-frame-pointer -g -o asan_test main.cpp
// ./asan_test
//
// Saída típica do ASan:
// ==12345==ERROR: AddressSanitizer: stack-buffer-overflow on address ...
// WRITE of size 64 at ...
// #0 0x... in trigger_stack_overflow ...
// Shadow memory map:
// ...
// allocated by thread T0 here:
//   #0 0x... in malloc ...

int main() {
    // Estas chamadas causariam erros detectáveis pelo ASan
    // trigger_stack_overflow();
    // trigger_uaf();

    std::cout << "ASan demo (uncomment triggers to test)\n";
    return 0;
}
```

### 7.2 MemorySanitizer (MSan)

MSan detecta leituras de memória não inicializada. É particularmente útil em código de parsing e protocol handling.

```cpp
#include <cstdint>
#include <iostream>
#include <vector>

// ============================================================
// Código que dispara MSan: variável não inicializada
// ============================================================
bool has_critical_flag(uint8_t* data, size_t len) {
    if (len < 4) return false;
    // Se data veio de socket/parsing incompleto,
    // data[3] pode não estar inicializado
    return (data[3] & 0x01) != 0;
}

// Versão segura: sempre inicializa
bool has_critical_flag_secure(uint8_t* data, size_t len) {
    if (len < 4) return false;
    // Garante que todos os bytes foram lidos inicializados
    uint8_t flags = data[3];
    return (flags & 0x01) != 0;
}

// Compilação:
// g++ -fsanitize=memory -fno-omit-frame-pointer -g -o msan_test main.cpp

int main() {
    // Demonstra com dados inicializados (seguro)
    std::vector<uint8_t> buf = {0x10, 0x20, 0x30, 0x01};
    bool result = has_critical_flag_secure(buf.data(), buf.size());
    std::cout << "Flag: " << result << "\n";
    return 0;
}
```

### 7.3 UndefinedBehaviorSanitizer (UBSan)

UBSan detecta comportamento indefinido em tempo de execução, incluindo overflow em tipos com sinal, divisão por zero, deslocamento negativo e ponteiros nulos.

```cpp
#include <iostream>
#include <limits>

// ============================================================
// Comportamentos indefinidos detectados pelo UBSan
// ============================================================

// Signed integer overflow
int add_signed(int a, int b) {
    return a + b; // UB se a+b > INT_MAX
}

// Division by zero
int divide(int a, int b) {
    return a / b; // UB se b == 0
}

// Null pointer dereference
int deref_null(int* p) {
    return *p; // UB se p == nullptr
}

// Shift by negative amount
int shift_amount(int val, int shift) {
    return val >> shift; // UB se shift < 0 ou shift >= 32
}

// Compilação:
// g++ -fsanitize=undefined -g -o ubsan_test main.cpp

int main() {
    std::cout << "UBSan demo\n";

    // Estas chamadas disparam UBSan:
    // add_signed(std::numeric_limits<int>::max(), 1);
    // divide(10, 0);
    // shift_amount(1, -1);

    // Versão segura
    int safe_add_result;
    bool ok = __builtin_add_overflow(
        std::numeric_limits<int>::max(), 1, &safe_add_result
    );
    if (ok) {
        std::cout << "Safe add: " << safe_add_result << "\n";
    } else {
        std::cout << "Overflow detected by __builtin_add_overflow\n";
    }

    return 0;
}
```

### 7.4 ThreadSanitizer (TSan)

TSan detecta data races — acessos concorrentes à mesma memória sem sincronização adequada.

```cpp
#include <iostream>
#include <thread>
#include <vector>
#include <atomic>

// ============================================================
// Código com data race (TSan detecta)
// ============================================================
// void data_race_example() {
//     int counter = 0;
//     std::vector<std::thread> threads;
//     for (int i = 0; i < 4; ++i) {
//         threads.emplace_back([&counter]() {
//             for (int j = 0; j < 100000; ++j) {
//                 counter++; // DATA RACE: sem sincronização
//             }
//         });
//     }
//     for (auto& t : threads) t.join();
//     // counter pode ter valor indefinido
// }

// Versão segura com atomic
void secure_counter() {
    std::atomic<int> counter{0};
    std::vector<std::thread> threads;
    for (int i = 0; i < 4; ++i) {
        threads.emplace_back([&counter]() {
            for (int j = 0; j < 100000; ++j) {
                counter.fetch_add(1, std::memory_order_relaxed);
            }
        });
    }
    for (auto& t : threads) t.join();
    std::cout << "Counter: " << counter.load() << "\n";
    // Resultado sempre = 400000
}

// Compilação:
// g++ -fsanitize=thread -g -o tsan_test main.cpp

int main() {
    secure_counter();
    return 0;
}
```

### 7.5 Sobrecarga dos Sanitizadores

| Sanitizador | Tempo | Memória | Uso Recomendado |
|-------------|-------|---------|-----------------|
| ASan | 2x | +20% | Debug/CI — detecção abrangente |
| MSan | 3x | +30% | Debug — memória não inicializada |
| UBSan | 1.5x | +10% | Sempre — overhead mínimo |
| TSan | 5x | +10x | Debug — concorrência |

---

## 8. Smart Pointers e RAII

### 8.1 unique_ptr — Propriedade Exclusiva

`unique_ptr` garante que apenas um ownership existe por objeto. Quando o `unique_ptr` sai do escopo, o objeto é automaticamente deletado. Isso elimina memory leaks e prevene double-free por design.

```cpp
#include <iostream>
#include <memory>
#include <cstring>

// ============================================================
// Wrapper RAII para material criptográfico
// Garante zeroing seguro na destruição
// ============================================================
class SecureCryptoKey {
public:
    SecureCryptoKey(const uint8_t* key_data, size_t len)
        : key_len_(len), key_(nullptr) {
        if (len == 0 || len > 64) {
            throw std::invalid_argument("Invalid key length");
        }

        key_ = new uint8_t[len];
        std::memcpy(key_, key_data, len);

        // Marca como válido
        valid_ = true;
    }

    ~SecureCryptoKey() {
        secure_zero();
    }

    // Impede cópia — chave criptográfica nunca deve ser copiada
    SecureCryptoKey(const SecureCryptoKey&) = delete;
    SecureCryptoKey& operator=(const SecureCryptoKey&) = delete;

    // Permite movimento
    SecureCryptoKey(SecureCryptoKey&& other) noexcept
        : key_(other.key_), key_len_(other.key_len_),
          valid_(other.valid_) {
        other.key_ = nullptr;
        other.key_len_ = 0;
        other.valid_ = false;
    }

    // Uso da chave (retorna ponteiro para operações criptográficas)
    const uint8_t* data() const {
        if (!valid_ || key_ == nullptr) {
            throw std::runtime_error("Key is invalid or zeroized");
        }
        return key_;
    }

    size_t length() const { return key_len_; }
    bool is_valid() const { return valid_ && key_ != nullptr; }

private:
    void secure_zero() {
        if (key_ != nullptr && key_len_ > 0) {
            // volatile impede que o compilador otimize o zeroing
            volatile uint8_t* vkey = key_;
            for (size_t i = 0; i < key_len_; ++i) {
                vkey[i] = 0;
            }

            // Barrier de memória para garantir que o zeroing
            // é visível antes da liberação
            __sync_synchronize();

            delete[] key_;
            key_ = nullptr;
            key_len_ = 0;
            valid_ = false;
        }
    }

    uint8_t* key_;
    size_t key_len_;
    bool valid_;
};

// ============================================================
// Gerenciador de chave RAII com unique_ptr
// ============================================================
void process_with_key(const uint8_t* raw_key, size_t key_len) {
    // unique_ptr gerencia a vida da chave automaticamente
    auto key = std::make_unique<SecureCryptoKey>(raw_key, key_len);

    if (key->is_valid()) {
        std::cout << "Key loaded, length: " << key->length() << "\n";
        // ... usar a chave para operações criptográficas ...
    }

    // Quando key sai do escopo:
    // 1. secure_zero() é chamado — memória é zerada
    // 2. delete[] libera a memória
    // 3. Nenhum ponteiro dangling permanece
}

// ============================================================
// Socket RAII wrapper — previne fd leaks
// ============================================================
class SecureSocket {
public:
    explicit SecureSocket(int fd) : fd_(fd) {
        if (fd_ < 0) {
            throw std::runtime_error("Invalid socket fd");
        }
    }

    ~SecureSocket() {
        if (fd_ >= 0) {
            close(fd_);
            fd_ = -1;
        }
    }

    // Impede cópia
    SecureSocket(const SecureSocket&) = delete;
    SecureSocket& operator=(const SecureSocket&) = delete;

    // Permite movimento
    SecureSocket(SecureSocket&& other) noexcept
        : fd_(other.fd_) {
        other.fd_ = -1;
    }

    int get() const { return fd_; }

    void close() {
        if (fd_ >= 0) {
            ::close(fd_);
            fd_ = -1;
        }
    }

private:
    int fd_;
};

// Mutex RAII wrapper
class SecureMutex {
public:
    explicit SecureMutex() {
        pthread_mutex_init(&mutex_, nullptr);
    }

    ~SecureMutex() {
        pthread_mutex_destroy(&mutex_);
    }

    SecureMutex(const SecureMutex&) = delete;
    SecureMutex& operator=(const SecureSocket&) = delete;

    void lock() { pthread_mutex_lock(&mutex_); }
    void unlock() { pthread_mutex_unlock(&mutex_); }

    pthread_mutex_t* native_handle() { return &mutex_; }

private:
    pthread_mutex_t mutex_;
};

// Scoped lock
class ScopedLock {
public:
    explicit ScopedLock(SecureMutex& m) : mutex_(m) {
        mutex_.lock();
    }

    ~ScopedLock() {
        mutex_.unlock();
    }

    ScopedLock(const ScopedLock&) = delete;
    ScopedLock& operator=(const ScopedLock&) = delete;

private:
    SecureMutex& mutex_;
};

int main() {
    std::cout << "=== Secure Crypto Key with RAII ===\n\n";

    uint8_t key_data[32] = {
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10,
        0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18,
        0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20
    };

    process_with_key(key_data, sizeof(key_data));
    std::cout << "Key was securely zeroed on destruction\n";

    return 0;
}
```

### 8.2 shared_ptr e weak_ptr

```cpp
#include <iostream>
#include <memory>
#include <string>

// ============================================================
// shared_ptr: contagem de referências thread-safe
// ============================================================
class SharedResource {
public:
    explicit SharedResource(const std::string& name)
        : name_(name), ref_count_(0) {
        std::cout << "Resource '" << name_ << "' created\n";
    }

    ~SharedResource() {
        std::cout << "Resource '" << name_ << "' destroyed\n";
    }

    const std::string& name() const { return name_; }

private:
    std::string name_;
    int ref_count_;
};

// ============================================================
// weak_ptr: quebra referências circulares
// ============================================================
struct TreeNode {
    std::string value;
    std::shared_ptr<TreeNode> parent;    // Referência forte ao pai
    std::weak_ptr<TreeNode> child;       // Referência fraca ao filho
    // Se child fosse shared_ptr, teríamos ciclo:
    //   pai → filho → pai → ...

    explicit TreeNode(const std::string& v) : value(v) {
        std::cout << "TreeNode '" << value << "' created\n";
    }

    ~TreeNode() {
        std::cout << "TreeNode '" << value << "' destroyed\n";
    }
};

// weak_ptr usage
void demonstrate_weak_ptr() {
    std::weak_ptr<TreeNode> weak;

    {
        auto root = std::make_shared<TreeNode>("root");
        auto child = std::make_shared<TreeNode>("child");
        child->parent = root;
        root->child = child;

        weak = child;
        std::cout << "Inside scope, weak expired: "
                  << weak.expired() << "\n";
    }
    // root e child destruídos — weak não mantém viva a memória
    std::cout << "Outside scope, weak expired: "
              << weak.expired() << "\n";

    // Tentar acessar memória liberada: segura com weak_ptr
    if (auto locked = weak.lock()) {
        std::cout << "Still alive: " << locked->value << "\n";
    } else {
        std::cout << "Object was safely destroyed\n";
    }
}

int main() {
    demonstrate_weak_ptr();
    return 0;
}
```

---

## 9. Safe Memory Patterns

### 9.1 Arena Allocator para Alocação com Limites

```cpp
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>

// ============================================================
// String segura com alocação em arena
// ============================================================
class SafeString {
public:
    static constexpr size_t MAX_LEN = 4096;

    SafeString() : len_(0) {
        data_[0] = '\0';
    }

    explicit SafeString(const char* str) {
        if (str == nullptr) {
            throw std::invalid_argument("Null string");
        }

        size_t input_len = std::strlen(str);
        if (input_len >= MAX_LEN) {
            throw std::overflow_error("String exceeds maximum length");
        }

        std::memcpy(data_, str, input_len + 1);
        len_ = input_len;
    }

    // Concatenação segura com verificação de overflow
    SafeString& operator+=(const SafeString& other) {
        if (len_ + other.len_ >= MAX_LEN) {
            throw std::overflow_error("Concatenation would exceed limit");
        }
        std::memcpy(data_ + len_, other.data_, other.len_ + 1);
        len_ += other.len_;
        return *this;
    }

    SafeString& operator+=(const char* str) {
        if (str == nullptr) return *this;
        size_t str_len = std::strlen(str);
        if (len_ + str_len >= MAX_LEN) {
            throw std::overflow_error("Concatenation would exceed limit");
        }
        std::memcpy(data_ + len_, str, str_len + 1);
        len_ += str_len;
        return *this;
    }

    // Acesso seguro com bounds checking
    char at(size_t index) const {
        if (index >= len_) {
            throw std::out_of_range("Index out of range");
        }
        return data_[index];
    }

    const char* c_str() const { return data_; }
    size_t length() const { return len_; }
    bool empty() const { return len_ == 0; }

    // Substring segura
    SafeString substr(size_t start, size_t count) const {
        if (start > len_) {
            throw std::out_of_range("Start index out of range");
        }
        size_t actual_count = std::min(count, len_ - start);
        char temp[MAX_LEN];
        std::memcpy(temp, data_ + start, actual_count);
        temp[actual_count] = '\0';
        return SafeString(temp);
    }

    // Zeroing seguro na destruição
    ~SafeString() {
        volatile char* vdata = data_;
        for (size_t i = 0; i < len_; ++i) {
            vdata[i] = '\0';
        }
        len_ = 0;
    }

private:
    char data_[MAX_LEN];
    size_t len_;
};

// ============================================================
// Fence-based bounds checking
// ============================================================
template <typename T, size_t Capacity>
class FenceArray {
public:
    FenceArray() : size_(0) {
        // Preenche fence com padrão mágico
        std::memset(fence_before_, 0xDE, sizeof(fence_before_));
        std::memset(fence_after_,  0xAD, sizeof(fence_after_));
    }

    void push(const T& value) {
        if (size_ >= Capacity) {
            throw std::overflow_error("FenceArray is full");
        }

        // Verifica integridade do fence antes de escrita
        verify_fence();

        data_[size_] = value;
        ++size_;

        // Verifica integridade do fence após escrita
        verify_fence();
    }

    T& at(size_t index) {
        if (index >= size_) {
            throw std::out_of_range("Index out of range");
        }
        verify_fence();
        return data_[index];
    }

    size_t size() const { return size_; }

    // Verifica se o fence foi corrompido
    bool verify_fence() const {
        bool ok = true;
        for (size_t i = 0; i < sizeof(fence_before_); ++i) {
            if (fence_before_[i] != 0xDE) {
                ok = false;
                std::cerr << "[SECURITY] Fence before corrupted at "
                          << i << "\n";
                break;
            }
        }
        for (size_t i = 0; i < sizeof(fence_after_); ++i) {
            if (fence_after_[i] != 0xAD) {
                ok = false;
                std::cerr << "[SECURITY] Fence after corrupted at "
                          << i << "\n";
                break;
            }
        }
        return ok;
    }

private:
    T data_[Capacity];
    size_t size_;
    std::uint8_t fence_before_[64];
    std::uint8_t fence_after_[64];
};

// ============================================================
// Copy-on-write pattern
// ============================================================
template <typename T>
class CowPtr {
public:
    explicit CowPtr(T* data) : data_(data), ref_count_(new size_t(1)) {}

    CowPtr(const CowPtr& other)
        : data_(other.data_), ref_count_(other.ref_count_) {
        ++(*ref_count_);
    }

    ~CowPtr() {
        if (--(*ref_count_) == 0) {
            delete data_;
            delete ref_count_;
        }
    }

    // Cópia sob demanda: só copia quando tenta modificar
    T& modify() {
        if (*ref_count_ > 1) {
            // Cria cópia privada antes de modificar
            T* new_data = new T(*data_);
            --(*ref_count_);
            data_ = new_data;
            ref_count_ = new size_t(1);
        }
        return *data_;
    }

    const T& read() const { return *data_; }

private:
    T* data_;
    size_t* ref_count_;
};

int main() {
    std::cout << "=== SafeString ===\n\n";
    SafeString s1("Hello");
    SafeString s2(" World");
    s1 += s2;
    std::cout << "Result: " << s1.c_str() << "\n";
    std::cout << "Length: " << s1.length() << "\n";

    std::cout << "\n=== FenceArray ===\n\n";
    FenceArray<int, 10> arr;
    for (int i = 0; i < 5; ++i) {
        arr.push(i * 10);
    }
    std::cout << "FenceArray size: " << arr.size() << "\n";
    std::cout << "Fence intact: " << arr.verify_fence() << "\n";

    return 0;
}
```

---

## 10. Hardening Memory Management

### 10.1 Fortify Source

`_FORTIFY_SOURCE` substitui funções de string e I/O por versões que verificam o tamanho do buffer em tempo de compilação ou execução. Deve ser habilitado com `-O1` ou superior.

```cpp
#define _FORTIFY_SOURCE 2

#include <cstdio>
#include <cstring>
#include <cstdlib>

// ============================================================
// Exemplos de funções fortificadas
// ============================================================
void demonstrate_fortify() {
    // strcpy → __strcpy_chk: verifica se o destino tem espaço
    // Se sizeof(dest) < strlen(src) + 1, aborta em tempo de execução
    char safe_dest[32];
    // strcpy(safe_dest, long_string); // __strcpy_chk detecta overflow

    // memcpy → __memcpy_chk: verifica tamanho do destino
    // snprintf → __snprintf_chk: limita escrita ao tamanho do buffer

    // Versão segura explícita (sem depender de FORTIFY)
    const char* src = "This is a safe string operation";
    std::strncpy(safe_dest, src, sizeof(safe_dest) - 1);
    safe_dest[sizeof(safe_dest) - 1] = '\0';
}

// ============================================================
// Exemplo: função com FORTIFY detectável
// ============================================================
void vulnerable_strcpy_example() {
    // Se _FORTIFY_SOURCE está ativo e -O1+:
    // Esta chamada aborta em tempo de execução
    char small_buf[16];
    const char* long_data = "This string is much longer than 16 bytes";

    // Em tempo de compilação (sizeof disponível):
    // strcpy(small_buf, long_data); // erro de compilação com FORTIFY

    // Em tempo de execução (strlen dinâmico):
    // snprintf(small_buf, sizeof(small_buf), "%s", long_data);
    // Se strlen > sizeof, truncamento ocorre (seguro)
    std::snprintf(small_buf, sizeof(small_buf), "%s", long_data);
    std::cout << "Truncated: " << small_buf << "\n";
}

int main() {
    demonstrate_fortify();
    vulnerable_strcpy_example();
    return 0;
}
```

### 10.2 Configuração CMake de Hardening Completa

```cmake
cmake_minimum_required(VERSION 3.15)
project(HardenedProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ============================================================
# Compile definitions para hardening
# ============================================================
target_compile_definitions(${PROJECT_NAME} PRIVATE
    _FORTIFY_SOURCE=2
    _GLIBCXX_ASSERTIONS
)

# ============================================================
# Compile options — warnings rigorosos
# ============================================================
target_compile_options(${PROJECT_NAME} PRIVATE
    -Wall -Wextra -Werror -Wpedantic
    -Wformat=2
    -Wformat-security
    -Wconversion
    -Wsign-conversion
    -Wnull-dereference
    -Wstack-protector
    -Wstrict-overflow=5
    -fstack-protector-strong
    -fPIE
    -ftrapv
)

# ============================================================
# Link options — hardening completo
# ============================================================
target_link_options(${PROJECT_NAME} PRIVATE
    -pie
    -Wl,-z,noexecstack
    -Wl,-z,relro
    -Wl,-z,now
    -Wl,-z,separate-code
    -Wl,--no-undefined
    -Wl,--as-needed
    -Wl,--hash-style=gnu
)

# ============================================================
# Sanitizers para debug
# ============================================================
option(ENABLE_SANITIZERS "Enable sanitizers" OFF)

if(ENABLE_SANITIZERS)
    target_compile_options(${PROJECT_NAME} PRIVATE
        -fsanitize=address,undefined,leak
        -fno-omit-frame-pointer
    )
    target_link_options(${PROJECT_NAME} PRIVATE
        -fsanitize=address,undefined,leak
    )
endif()

# ============================================================
# Verificação pós-build: verifica que todas as proteções
# estão ativas no binário final
# ============================================================
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
        COMMAND echo "=== Verifying hardening ==="
        COMMAND readelf -l $<TARGET_FILE:${PROJECT_NAME}>
                | grep -q GNU_STACK && echo "NX: OK" || echo "NX: MISSING"
        COMMAND readelf -l $<TARGET_FILE:${PROJECT_NAME}>
                | grep -q GNU_RELRO && echo "RELRO: OK" || echo "RELRO: MISSING"
        COMMAND readelf -s $<TARGET_FILE:${PROJECT_NAME}>
                | grep -q __stack_chk_fail && echo "Canary: OK" || echo "Canary: MISSING"
        COMMENT "Verifying binary hardening flags"
    )
endif()
```

### 10.3 Verificação Completa com checksec

```bash
#!/bin/bash
# check_hardening.sh — Verifica todas as proteções de segurança
# em um binário ELF compilado com hardening

BINARY="${1:-./myapp}"

echo "=== Hardening Check: $BINARY ==="

# 1. RELRO
echo -n "RELRO: "
if readelf -l "$BINARY" 2>/dev/null | grep -q "GNU_RELRO"; then
    if readelf -d "$BINARY" 2>/dev/null | grep -q "BIND_NOW"; then
        echo "Full RELRO"
    else
        echo "Partial RELRO"
    fi
else
    echo "No RELRO"
fi

# 2. Stack Canary
echo -n "Stack Canary: "
if readelf -s "$BINARY" 2>/dev/null | grep -q "__stack_chk_fail"; then
    echo "Enabled"
else
    echo "Disabled"
fi

# 3. NX (Non-Executable Stack)
echo -n "NX: "
if readelf -l "$BINARY" 2>/dev/null | grep "GNU_STACK" | grep -qv "E"; then
    echo "Enabled"
else
    echo "Disabled"
fi

# 4. PIE
echo -n "PIE: "
file_type=$(file "$BINARY" 2>/dev/null)
if echo "$file_type" | grep -q "shared object"; then
    echo "Enabled"
elif echo "$file_type" | grep -q "executable"; then
    echo "Disabled"
else
    echo "Unknown"
fi

# 5. FORTIFY
echo -n "FORTIFY: "
if readelf -s "$BINARY" 2>/dev/null | grep -q "_chk@"; then
    echo "Enabled"
else
    echo "Disabled"
fi

echo "=== Done ==="
```

---

## 11. Exercício Prático

### Enunciado

O programa abaixo contém **7 vulnerabilidades de memória** intencionais. Sua tarefa é:

1. Identificar cada vulnerabilidade.
2. Classificar o tipo (buffer overflow, UAF, integer overflow, format string, etc.).
3. Corrigir cada uma utilizando os padrões aprendidos neste capítulo.
4. Compilar com `-fsanitize=address,undefined -Wall -Wextra -Werror` e verificar que nenhum erro é reportado.

```cpp
// vulnerable_server.cpp — Programa com 7 vulnerabilidades
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cstdint>

struct UserRecord {
    uint32_t id;
    char username[32];
    char password[64];
    bool authenticated;
};

// Bug 1: Stack buffer overflow em parse_username
void parse_username(const char* input, char* output) {
    strcpy(output, input); // overflow se input > 31 chars
}

// Bug 2: Format string em log_message
void log_message(const char* user_msg) {
    printf(user_msg); // format string se user_msg contém %
}

// Bug 3: Integer overflow em allocate_users
UserRecord* allocate_users(uint32_t count) {
    uint32_t size = count * sizeof(UserRecord); // overflow
    UserRecord* users = (UserRecord*)malloc(size);
    return users;
}

// Bug 4: Use-after-free em process_request
char* process_request(const char* data) {
    char* buffer = (char*)malloc(256);
    strcpy(buffer, data);
    free(buffer);
    // Bug: retorna buffer já liberado
    return buffer;
}

// Bug 5: Double-free em cleanup
void cleanup(UserRecord* user) {
    if (user != NULL) {
        free(user); // se chamado duas vezes → double-free
    }
}

// Bug 6: Off-by-one em copy_field
void copy_field(const char* src, char* dst, int max_len) {
    for (int i = 0; i <= max_len; i++) { // <= em vez de <
        dst[i] = src[i];
    }
}

// Bug 7: Dangling pointer em connection_handler
struct Connection {
    void* data;
    int id;
};

Connection* create_connection() {
    Connection* conn = (Connection*)malloc(sizeof(Connection));
    conn->data = malloc(128);
    conn->id = 42;
    return conn;
}

// Fim do arquivo: falta free para conn->data e conn
```

### Soluções

```cpp
// ============================================================
// Solution 1: Stack buffer overflow → std::string ou bounds check
// ============================================================
void secure_parse_username(const char* input, char* output, size_t out_size) {
    if (std::strlen(input) >= out_size) {
        std::fprintf(stderr, "[SECURITY] Username too long\n");
        output[0] = '\0';
        return;
    }
    std::strncpy(output, input, out_size - 1);
    output[out_size - 1] = '\0';
}

// ============================================================
// Solution 2: Format string → literal format
// ============================================================
void secure_log_message(const char* user_msg) {
    std::printf("%s\n", user_msg);
}

// ============================================================
// Solution 3: Integer overflow → safe multiplication
// ============================================================
UserRecord* secure_allocate_users(uint32_t count) {
    constexpr uint32_t max_count =
        UINT32_MAX / sizeof(UserRecord);
    if (count > max_count || count == 0) {
        std::fprintf(stderr, "[SECURITY] Invalid count\n");
        return nullptr;
    }
    return new(std::nothrow) UserRecord[count];
}

// ============================================================
// Solution 4: UAF → don't return freed memory
// ============================================================
void secure_process_request(const char* data, char* output, size_t out_size) {
    // Processa e copia para output sem retornar memória temporária
    std::strncpy(output, data, out_size - 1);
    output[out_size - 1] = '\0';
}

// ============================================================
// Solution 5: Double-free → use smart pointer
// ============================================================
void secure_cleanup(std::unique_ptr<UserRecord>& user) {
    user.reset(); // Seguro: se já é nullptr, não faz nada
}

// ============================================================
// Solution 6: Off-by-one → correct loop bound
// ============================================================
void secure_copy_field(const char* src, char* dst, int max_len) {
    std::strncpy(dst, src, static_cast<size_t>(max_len));
    dst[max_len - 1] = '\0'; // Garante null terminator
}

// ============================================================
// Solution 7: Dangling pointer → RAII
// ============================================================
class SecureConnection {
public:
    SecureConnection() : id_(42) {
        data_ = std::make_unique<char[]>(128);
        std::memset(data_.get(), 0, 128);
    }

    ~SecureConnection() {
        // data_ é automaticamente liberado pelo unique_ptr
    }

private:
    std::unique_ptr<char[]> data_;
    int id_;
};

// ============================================================
// Main para testes
// ============================================================
int main() {
    // Teste 1
    char uname[32];
    secure_parse_username("admin", uname, sizeof(uname));
    std::printf("Username: %s\n", uname);

    // Teste 2
    secure_log_message("User logged in successfully");

    // Teste 3
    auto users = secure_allocate_users(10);
    if (users) {
        delete[] users;
    }

    // Teste 4
    char result[256];
    secure_process_request("test data", result, sizeof(result));
    std::printf("Result: %s\n", result);

    // Teste 5
    auto user = std::make_unique<UserRecord>();
    secure_cleanup(user);

    // Teste 6
    char field[16];
    secure_copy_field("hello world", field, sizeof(field));
    std::printf("Field: %s\n", field);

    // Teste 7
    {
        SecureConnection conn;
    } // conn destruído automaticamente aqui

    std::printf("All vulnerabilities fixed\n");
    return 0;
}
```

---

## 12. Referências

1. **OWASP Foundation.** "Buffer Overflow Vulnerabilities." OWASP Top Ten. https://owasp.org/www-community/vulnerabilities/Buffer_overflow

2. **MITRE Corporation.** "CWE-120: Buffer Copy without Checking Size of Input." Common Weakness Enumeration. https://cwe.mitre.org/data/definitions/120.html

3. **CVE-2014-0160.** "The (1) TLS and (2) DTLS implementations in OpenSSL 1.0.1 before 1.0.1g allow remote attackers to read memory from or send packets to invalid memory locations." MITRE CVE Database.

4. **CVE-2017-0144.** "The SMBv1 server in Microsoft Windows allows remote code execution." Microsoft Security Bulletin MS17-010.

5. **CVE-2017-5753.** "Bounds Check Bypass (Spectre Variant 1)." Project Zero, Google. https://googleprojectzero.blogspot.com/2018/01/reading-privileged-memory-with-side.html

6. **CVE-2017-5715.** "Branch Target Injection (Spectre Variant 2)." Project Zero, Google.

7. **CVE-2017-5754.** "Rogue Data Cache Load (Meltdown)." Project Zero, Google.

8. **CVE-2023-33106.** "Use-after-free vulnerability in the GPU driver." Qualcomm Product Security Bulletin, 2023.

9. **CVE-2023-26083.** "Memory mapping vulnerability in the Arm Mali GPU kernel driver." Arm Security Bulletin, 2023.

10. **CVE-2021-1048.** "Use-after-free vulnerability in the epoll subsystem of the Linux kernel." Android Security Bulletin, 2021.

11. **CVE-2024-49410.** "Vulnerability in Samsung Real-time Kernel Protection." Samsung Security Bulletin, 2024.

12. **Sploitfun.** "Understanding glibc malloc." https://sploitfun.wordpress.com/understanding-glibc-malloc/

13. **OWASP.** "Heap Overflow." OWASP Code Review Guide. https://owasp.org/www-project-code-review-guide/

14. **Dowd, M.; McDonald, J.; Schuh, J.** *The Art of Software Security Assessment.* Addison-Wesley, 2006.

15. **Lattner, C. & Adve, V.** "AddressSanitizer: A Fast Address Sanity Checker." USENIX ATC, 2012.

16. **GCC Documentation.** "Instrumentation Options: -fsanitize=address." https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html

17. **Clang Documentation.** "AddressSanitizer." https://clang.llvm.org/docs/AddressSanitizer.html

---

*Capítulo seguinte: [Capítulo 5 — Tratamento de Erros e Exceções](05-tratamento-de-erros-e-excecoes.md)*
---

*[Capítulo anterior: 03 — Principios De Codificacao Segura](03-principios-de-codificacao-segura.md)*
*[Próximo capítulo: 05 — Tratamento De Erros E Excecoes](05-tratamento-de-erros-e-excecoes.md)*
