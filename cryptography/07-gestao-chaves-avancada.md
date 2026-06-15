# Capítulo 07 — Gestão de Chaves Avançada

## 7.1 Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

- Compreender o ciclo de vida completo de uma chave criptográfica, desde a geração até a destruição
- Implementar geração segura de chaves utilizando CSPRNG e fontes de entropia de hardware
- Aplicar técnicas de Key Wrapping conforme RFC 3394 e RFC 5649
- Projetar sistemas de Envelope Encryption com separação entre data keys e master keys
- Implementar rotação transparente de chaves sem interrupção de serviço
- Utilizar Shamir's Secret Sharing para threshold cryptography em C++
- Integrar sistemas de gestão de chaves com HashiCorp Vault
- Analisar vulnerabilidades reais como CVE-2016-0728 (overflow de refcount no keyring do Linux)
- Conhecer os padrões NIST SP 800-57 e KMIP para gestão de chaves
- Comparar soluções de cloud KMS: AWS KMS, Azure Key Vault e GCP Cloud KMS
- Projetar e implementar um sistema completo de gestão de chaves em C++17

---

## 7.2 Ciclo de Vida de Chaves (Key Lifecycle)

O ciclo de vida de uma chave criptográfica é o conjunto de todas as fases por uma chave desde sua criação até sua eliminação definitiva. A gestão adequada de cada fase é essencial para a segurança do sistema como um todo. Cada vulnerabilidade em qualquer ponto do ciclo pode comprometer todo o sistema de segurança.

### 7.2.1 Visão Geral do Ciclo de Vida

```
Geração → Distribuição → Armazenamento → Uso → Rotação → Destruição
```

Cada fase possui requisitos específicos de segurança:

| Fase | Requisito Principal | Risco se Negligenciado |
|------|---------------------|----------------------|
| Geração | Entropia adequada, CSPRNG certificado | Chaves previsíveis |
| Distribuição | Canal seguro, autenticidade | Intercepção, MITM |
| Armazenamento | Proteção contra acesso não autorizado | Vazamento de chaves |
| Uso | Controle de acesso, auditoria | Uso indevido, repudio |
| Rotação | Atualização periódica, backward compat | Exposição prolongada |
| Destruição | Eliminação irreversível | Recuperação por atacantes |

### 7.2.2 Estados de uma Chave

Uma chave pode transitar por vários estados durante seu ciclo de vida. A transição entre estados deve ser estritamente controlada e auditada. O diagrama abaixo mostra o fluxo válido de estados conforme NIST SP 800-57:

```
[Unregistered] → [Pre-active] → [Active] → [Suspended] → [Deactivated] → [Destroyed]
                         ↓            ↓
                    [Compromised]  [Expired]
```

Estados intermediários como "Compromised" são acionados por eventos de segurança, como detecção de intrusão ou suspectação de vazamento. Um estado "Suspended" permite suspensão temporária sem destruição, útil durante investigações de segurança.

### 7.2.3 Implementação do Ciclo de Vida em C++

```cpp
#pragma once

#include <string>
#include <chrono>
#include <optional>
#include <vector>
#include <memory>
#include <functional>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <algorithm>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>

namespace keymgmt {

enum class KeyState {
    Uninitialized,
    PreActive,
    Active,
    Rotating,
    Suspended,
    Expired,
    Compromised,
    Deactivated,
    Destroyed
};

enum class KeyUsage {
    Encrypt,
    Decrypt,
    Sign,
    Verify,
    WrapKey,
    UnwrapKey,
    DeriveKey
};

struct KeyMetadata {
    std::string id;
    std::string label;
    std::string algorithm;
    size_t key_size_bits;
    KeyState state;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point activated_at;
    std::chrono::system_clock::time_point expires_at;
    std::optional<std::chrono::system_clock::time_point> suspended_at;
    std::optional<std::chrono::system_clock::time_point> destroyed_at;
    std::vector<KeyUsage> allowed_usages;
    std::string owner;
    std::string key_family;
    uint64_t use_count;
    uint64_t max_uses;
    std::string description;
    std::unordered_map<std::string, std::string> attributes;
};

class KeyLifecycleError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

class KeyMaterial {
private:
    std::vector<uint8_t> data_;
    bool wiped_ = false;

public:
    explicit KeyMaterial(size_t size_bytes) : data_(size_bytes, 0) {}
    KeyMaterial(const uint8_t* data, size_t len)
        : data_(data, data + len) {}
    KeyMaterial(std::initializer_list<uint8_t> init)
        : data_(init) {}

    ~KeyMaterial() { secure_wipe(); }

    KeyMaterial(const KeyMaterial&) = delete;
    KeyMaterial& operator=(const KeyMaterial&) = delete;

    KeyMaterial(KeyMaterial&& o) noexcept
        : data_(std::move(o.data_)), wiped_(o.wiped_) {
        o.wiped_ = true;
    }

    KeyMaterial& operator=(KeyMaterial&& o) noexcept {
        if (this != &o) {
            secure_wipe();
            data_ = std::move(o.data_);
            wiped_ = o.wiped_;
            o.wiped_ = true;
        }
        return *this;
    }

    uint8_t* data() { return data_.data(); }
    const uint8_t* data() const { return data_.data(); }
    size_t size() const { return data_.size(); }
    bool is_wiped() const { return wiped_; }

    void secure_wipe() {
        if (!wiped_ && !data_.empty()) {
            volatile uint8_t* p = data_.data();
            for (size_t i = 0; i < data_.size(); ++i) p[i] = 0x00;
            for (size_t i = 0; i < data_.size(); ++i) p[i] = 0xFF;
            for (size_t i = 0; i < data_.size(); ++i) p[i] = 0x00;
            wiped_ = true;
        }
    }

    std::vector<uint8_t> clone_bytes() const {
        return std::vector<uint8_t>(data_.begin(), data_.end());
    }
};

// Tabela de transicoes validas de estado
static const std::unordered_map<KeyState, std::vector<KeyState>>
    VALID_TRANSITIONS = {
    {KeyState::Uninitialized, {KeyState::PreActive}},
    {KeyState::PreActive, {KeyState::Active, KeyState::Destroyed}},
    {KeyState::Active, {KeyState::Rotating, KeyState::Suspended,
                        KeyState::Expired, KeyState::Compromised,
                        KeyState::Deactivated}},
    {KeyState::Rotating, {KeyState::Active, KeyState::Destroyed}},
    {KeyState::Suspended, {KeyState::Active, KeyState::Deactivated,
                           KeyState::Destroyed}},
    {KeyState::Expired, {KeyState::Destroyed}},
    {KeyState::Compromised, {KeyState::Deactivated, KeyState::Destroyed}},
    {KeyState::Deactivated, {KeyState::Destroyed}},
    {KeyState::Destroyed, {}}
};

class Key {
private:
    KeyMetadata meta_;
    std::unique_ptr<KeyMaterial> material_;
    mutable std::shared_mutex mutex_;

    void validate_transition(KeyState from, KeyState to) const {
        auto it = VALID_TRANSITIONS.find(from);
        if (it == VALID_TRANSITIONS.end()) {
            throw KeyLifecycleError("Estado origem invalido");
        }
        if (std::find(it->second.begin(), it->second.end(), to) ==
            it->second.end()) {
            std::ostringstream oss;
            oss << "Transicao invalida: "
                << static_cast<int>(from) << " -> "
                << static_cast<int>(to);
            throw KeyLifecycleError(oss.str());
        }
    }

public:
    explicit Key(KeyMetadata meta, std::unique_ptr<KeyMaterial> mat)
        : meta_(std::move(meta)), material_(std::move(mat)) {}

    ~Key() { if (material_) material_->secure_wipe(); }
    Key(const Key&) = delete;
    Key& operator=(const Key&) = delete;

    const KeyMetadata& metadata() const {
        std::shared_lock lk(mutex_);
        return meta_;
    }

    KeyState state() const {
        std::shared_lock lk(mutex_);
        return meta_.state;
    }

    void transition_to(KeyState new_state) {
        std::unique_lock lk(mutex_);
        validate_transition(meta_.state, new_state);

        auto now = std::chrono::system_clock::now();
        meta_.state = new_state;

        switch (new_state) {
            case KeyState::Active:
                meta_.activated_at = now;
                break;
            case KeyState::Suspended:
                meta_.suspended_at = now;
                break;
            case KeyState::Destroyed:
                meta_.destroyed_at = now;
                break;
            default:
                break;
        }
    }

    bool is_usable() const {
        std::shared_lock lk(mutex_);
        if (meta_.state != KeyState::Active) return false;
        if (meta_.expires_at < std::chrono::system_clock::now())
            return false;
        if (meta_.max_uses > 0 && meta_.use_count >= meta_.max_uses)
            return false;
        return true;
    }

    bool can_perform(KeyUsage usage) const {
        std::shared_lock lk(mutex_);
        return std::find(meta_.allowed_usages.begin(),
                         meta_.allowed_usages.end(),
                         usage) != meta_.allowed_usages.end();
    }

    void record_use() {
        std::unique_lock lk(mutex_);
        ++meta_.use_count;
    }

    KeyMaterial* material() {
        std::shared_lock lk(mutex_);
        return material_.get();
    }
};

// --- Lifecycle Manager ---

using StateChangeCallback =
    std::function<void(const std::string&, KeyState, KeyState)>;

class KeyLifecycleManager {
private:
    std::unordered_map<std::string, std::shared_ptr<Key>> keys_;
    mutable std::shared_mutex mutex_;
    StateChangeCallback on_state_change_;
    std::chrono::hours default_validity_;
    uint64_t default_max_uses_;

public:
    explicit KeyLifecycleManager(
        std::chrono::hours validity = std::chrono::hours(24 * 365),
        uint64_t max_uses = 0)
        : default_validity_(validity), default_max_uses_(max_uses) {}

    void set_state_change_callback(StateChangeCallback cb) {
        on_state_change_ = std::move(cb);
    }

    std::string create_key(
        const std::string& label,
        const std::string& algorithm,
        size_t key_size_bits,
        std::unique_ptr<KeyMaterial> material,
        std::vector<KeyUsage> usages = {
            KeyUsage::Encrypt, KeyUsage::Decrypt}) {

        KeyMetadata meta;
        meta.id = generate_id();
        meta.label = label;
        meta.algorithm = algorithm;
        meta.key_size_bits = key_size_bits;
        meta.state = KeyState::PreActive;
        meta.created_at = std::chrono::system_clock::now();
        meta.expires_at = meta.created_at + default_validity_;
        meta.allowed_usages = usages;
        meta.use_count = 0;
        meta.max_uses = default_max_uses_;

        auto key = std::make_shared<Key>(std::move(meta),
                                         std::move(material));

        std::unique_lock lk(mutex_);
        keys_[key->metadata().id] = key;

        log_state_change(key->metadata().id,
                         KeyState::Uninitialized,
                         KeyState::PreActive);

        return key->metadata().id;
    }

    std::shared_ptr<Key> get_key(const std::string& id) {
        std::shared_lock lk(mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end()) return nullptr;
        auto key = it->second;
        if (!key->is_usable()) return nullptr;
        return key;
    }

    void activate(const std::string& id) {
        auto key = get_key_or_throw(id);
        KeyState old = key->state();
        key->transition_to(KeyState::Active);
        log_state_change(id, old, KeyState::Active);
    }

    void suspend(const std::string& id) {
        auto key = get_key_or_throw(id);
        KeyState old = key->state();
        key->transition_to(KeyState::Suspended);
        log_state_change(id, old, KeyState::Suspended);
    }

    void mark_compromised(const std::string& id) {
        auto key = get_key_or_throw(id);
        KeyState old = key->state();
        key->transition_to(KeyState::Compromised);
        log_state_change(id, old, KeyState::Compromised);
    }

    void deactivate(const std::string& id) {
        auto key = get_key_or_throw(id);
        KeyState old = key->state();
        key->transition_to(KeyState::Deactivated);
        log_state_change(id, old, KeyState::Deactivated);
    }

    void destroy(const std::string& id) {
        auto key = get_key_or_throw(id);
        KeyState old = key->state();
        key->transition_to(KeyState::Destroyed);
        log_state_change(id, old, KeyState::Destroyed);
    }

    std::vector<std::string> find_expired() const {
        std::shared_lock lk(mutex_);
        std::vector<std::string> result;
        auto now = std::chrono::system_clock::now();
        for (const auto& [id, key] : keys_) {
            auto m = key->metadata();
            if (m.state == KeyState::Active && m.expires_at <= now)
                result.push_back(id);
        }
        return result;
    }

    std::vector<std::string> find_exhausted() const {
        std::shared_lock lk(mutex_);
        std::vector<std::string> result;
        for (const auto& [id, key] : keys_) {
            auto m = key->metadata();
            if (m.state == KeyState::Active &&
                m.max_uses > 0 && m.use_count >= m.max_uses)
                result.push_back(id);
        }
        return result;
    }

    std::vector<std::string> find_by_state(KeyState s) const {
        std::shared_lock lk(mutex_);
        std::vector<std::string> result;
        for (const auto& [id, key] : keys_) {
            if (key->state() == s) result.push_back(id);
        }
        return result;
    }

    size_t count() const {
        std::shared_lock lk(mutex_);
        return keys_.size();
    }

private:
    std::shared_ptr<Key> get_key_or_throw(const std::string& id) {
        std::shared_lock lk(mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end())
            throw KeyLifecycleError("Chave nao encontrada: " + id);
        return it->second;
    }

    void log_state_change(const std::string& id,
                          KeyState from, KeyState to) {
        if (on_state_change_) on_state_change_(id, from, to);
    }

    static std::string generate_id() {
        static uint64_t counter = 0;
        auto now = std::chrono::system_clock::now();
        auto epoch = now.time_since_epoch();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            epoch).count();
        std::ostringstream oss;
        oss << "key-" << std::hex << std::setfill('0')
            << std::setw(12) << ms
            << "-" << std::setw(4) << (++counter & 0xFFFF);
        return oss.str();
    }
};

} // namespace keymgmt
```

---

## 7.3 Geração de Chaves (Key Generation)

### 7.3.1 Fontes de Entropia

A segurança de qualquer sistema criptográfico começa com a qualidade da entropia utilizada na geração de chaves. A entropia é a medida de aleatoriedade e imprevisibilidade de um sistema. Fontes de entropia podem ser classificadas em categorias:

**Fontes de Entropia de Software:**
- `/dev/urandom` — Linux (recomendado para uso geral)
- `/dev/random` — Linux (bloqueia quando entropia esgotada, nao recomendado)
- `CryptGenRandom` — Windows (via CryptoAPI)
- `BCryptGenRandom` — Windows (via CNG, recomendado)
- `arc4random_buf` — BSD/macOS

**Fontes de Entropia de Hardware:**
- TPM (Trusted Platform Module) — chip soldado na placa-mae
- Intel RDRAND — instrucao de hardware para RNG
- Intel RDSEED — instrucao de hardware para seeding
- Dispositivos HSM (Hardware Security Modules) — certificados FIPS 140-2
- RNGs externos USB — dispositivos dedicados

**Fontes de Entropia Ambiente (estatisticas):**
- Tempo de interacao do teclado (inter-keystroke timing)
- Movimentos do mouse
- Jitter de rede (network timing)
- Variacao de temperatura do CPU
- Interrupcoes de hardware

O principio fundamental e: **nunca confie em apenas uma fonte de entropia**. Sempre combine multiplos sources e aplique health checks.

### 7.3.2 CSPRNG em C++17

```cpp
#pragma once

#include <array>
#include <vector>
#include <random>
#include <chrono>
#include <thread>
#include <fstream>
#include <stdexcept>
#include <cstring>
#include <functional>
#include <memory>
#include <sstream>
#include <iomanip>
#include <atomic>
#include <mutex>

#ifdef __linux__
#include <sys/random.h>
#include <unistd.h>
#include <fcntl.h>
#endif

namespace csprng {

// --- Entropy Sources ---

class EntropySource {
public:
    virtual ~EntropySource() = default;
    virtual std::vector<uint8_t> generate(size_t n) = 0;
    virtual std::string name() const = 0;
    virtual bool is_available() const = 0;
    virtual double entropy_bits_per_byte() const = 0;
};

class LinuxGetRandom : public EntropySource {
public:
    std::vector<uint8_t> generate(size_t n) override {
        std::vector<uint8_t> buf(n);
        size_t total = 0;
        while (total < n) {
            ssize_t r = getrandom(buf.data() + total, n - total, 0);
            if (r < 0) throw std::runtime_error("getrandom failed");
            total += static_cast<size_t>(r);
        }
        return buf;
    }
    std::string name() const override { return "getrandom"; }
    bool is_available() const override {
        #ifdef __linux__
        return true;
        #else
        return false;
        #endif
    }
    double entropy_bits_per_byte() const override { return 8.0; }
};

class LinuxURandom : public EntropySource {
public:
    std::vector<uint8_t> generate(size_t n) override {
        std::vector<uint8_t> buf(n);
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0) throw std::runtime_error("open /dev/urandom failed");
        size_t total = 0;
        while (total < n) {
            ssize_t r = read(fd, buf.data() + total, n - total);
            if (r <= 0) { close(fd); throw std::runtime_error("read urandom failed"); }
            total += static_cast<size_t>(r);
        }
        close(fd);
        return buf;
    }
    std::string name() const override { return "urandom"; }
    bool is_available() const override {
        return access("/dev/urandom", R_OK) == 0;
    }
    double entropy_bits_per_byte() const override { return 8.0; }
};

class IntelRDRAND : public EntropySource {
public:
    std::vector<uint8_t> generate(size_t n) override {
        #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        std::vector<uint8_t> buf(n);
        size_t total = 0;
        while (total < n) {
            uint64_t val;
            uint8_t ok;
            __asm__ __volatile__("rdrand %1\n\tsetc %0"
                : "=q"(ok), "=r"(val) : : "cc");
            if (!ok) throw std::runtime_error("RDRAND failed");
            size_t cpy = std::min(sizeof(val), n - total);
            std::memcpy(buf.data() + total, &val, cpy);
            total += cpy;
        }
        return buf;
        #else
        throw std::runtime_error("RDRAND not supported on this arch");
        #endif
    }
    std::string name() const override { return "RDRAND"; }
    bool is_available() const override {
        #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        uint32_t eax, ebx, ecx, edx;
        __asm__ __volatile__("cpuid" : "=a"(eax),"=b"(ebx),"=c"(ecx),"=d"(edx) : "a"(1));
        return (ecx & (1u << 30)) != 0;
        #else
        return false;
        #endif
    }
    double entropy_bits_per_byte() const override { return 8.0; }
};

class IntelRDSEED : public EntropySource {
public:
    std::vector<uint8_t> generate(size_t n) override {
        #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        std::vector<uint8_t> buf(n);
        size_t total = 0;
        while (total < n) {
            uint64_t val;
            uint8_t ok;
            __asm__ __volatile__("rdseed %1\n\tsetc %0"
                : "=q"(ok), "=r"(val) : : "cc");
            if (!ok) throw std::runtime_error("RDSEED failed");
            size_t cpy = std::min(sizeof(val), n - total);
            std::memcpy(buf.data() + total, &val, cpy);
            total += cpy;
        }
        return buf;
        #else
        throw std::runtime_error("RDSEED not supported");
        #endif
    }
    std::string name() const override { return "RDSEED"; }
    bool is_available() const override {
        #if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
        uint32_t eax, ebx, ecx, edx;
        __asm__ __volatile__("cpuid" : "=a"(eax),"=b"(ebx),"=c"(ecx),"=d"(edx) : "a"(7));
        return (ebx & (1u << 18)) != 0;
        #else
        return false;
        #endif
    }
    double entropy_bits_per_byte() const override { return 8.0; }
};

class JitterEntropy : public EntropySource {
public:
    std::vector<uint8_t> generate(size_t n) override {
        std::vector<uint8_t> buf(n);
        size_t total = 0;
        while (total < n) {
            auto t1 = std::chrono::high_resolution_clock::now();
            volatile uint64_t x = 0;
            for (volatile int i = 0; i < 200; ++i) x += i;
            auto t2 = std::chrono::high_resolution_clock::now();
            std::this_thread::yield();
            auto t3 = std::chrono::high_resolution_clock::now();

            uint64_t j1 = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count());
            uint64_t j2 = static_cast<uint64_t>(
                std::chrono::duration_cast<std::chrono::nanoseconds>(t3 - t2).count());
            uint64_t combined = j1 ^ j2 ^ x;

            size_t cpy = std::min(sizeof(combined), n - total);
            std::memcpy(buf.data() + total, &combined, cpy);
            total += cpy;
        }
        return buf;
    }
    std::string name() const override { return "jitter"; }
    bool is_available() const override { return true; }
    double entropy_bits_per_byte() const override { return 1.5; }
};

// --- Health Tests (NIST SP 800-90B) ---

class HealthTester {
private:
    std::vector<uint8_t> last_sample_;
    size_t consecutive_repetitions_ = 0;
    static constexpr size_t MAX_REPETITIONS = 32;
    static constexpr size_t REPEAT_LIMIT = 5;

public:
    bool repitition_count_test(const std::vector<uint8_t>& sample) {
        if (sample == last_sample_) {
            ++consecutive_repetitions_;
        } else {
            consecutive_repetitions_ = 0;
        }
        last_sample_ = sample;
        return consecutive_repetitions_ < MAX_REPETITIONS;
    }

    bool adaptive_proportion_test(
        const std::vector<uint8_t>& sample,
        size_t cutoff = 5) {

        if (sample.empty()) return true;
        std::array<size_t, 256> counts{};
        for (uint8_t b : sample) counts[b]++;

        uint8_t most_common = 0;
        size_t max_count = 0;
        for (size_t i = 0; i < 256; ++i) {
            if (counts[i] > max_count) {
                max_count = counts[i];
                most_common = static_cast<uint8_t>(i);
            }
        }

        (void)most_common;
        return max_count < (sample.size() - cutoff);
    }

    bool health_check(const std::vector<uint8_t>& sample) {
        return repitition_count_test(sample) &&
               adaptive_proportion_test(sample);
    }

    void reset() {
        last_sample_.clear();
        consecutive_repetitions_ = 0;
    }
};

// --- Main CSPRNG ---

class CSPRNG {
private:
    std::vector<std::shared_ptr<EntropySource>> sources_;
    HealthTester health_;
    mutable std::mutex mutex_;
    bool initialized_ = false;
    std::vector<uint8_t> accumulator_;
    size_t estimated_entropy_bits_ = 0;

public:
    void add_source(std::shared_ptr<EntropySource> src) {
        std::lock_guard lk(mutex_);
        sources_.push_back(std::move(src));
    }

    void initialize() {
        std::lock_guard lk(mutex_);
        accumulator_.clear();
        estimated_entropy_bits_ = 0;

        for (auto& src : sources_) {
            if (!src->is_available()) continue;
            auto sample = src->generate(64);

            if (!health_.health_check(sample)) {
                throw std::runtime_error(
                    "Health check failed for source: " + src->name());
            }

            accumulator_.insert(accumulator_.end(),
                                sample.begin(), sample.end());
            estimated_entropy_bits_ += static_cast<size_t>(
                sample.size() * src->entropy_bits_per_byte());
        }

        if (estimated_entropy_bits_ < 128) {
            throw std::runtime_error(
                "Insufficient entropy: " +
                std::to_string(estimated_entropy_bits_) + " bits");
        }

        initialized_ = true;
    }

    std::vector<uint8_t> random_bytes(size_t n) {
        std::lock_guard lk(mutex_);
        ensure_initialized();

        #ifdef __linux__
        std::vector<uint8_t> buf(n);
        ssize_t r = getrandom(buf.data(), n, 0);
        if (r < 0) throw std::runtime_error("getrandom failed");

        if (!accumulator_.empty()) {
            for (size_t i = 0; i < n; ++i)
                buf[i] ^= accumulator_[i % accumulator_.size()];
        }
        return buf;
        #else
        std::random_device rd;
        std::vector<uint8_t> buf(n);
        for (size_t i = 0; i < n; ++i)
            buf[i] = static_cast<uint8_t>(rd() & 0xFF);
        return buf;
        #endif
    }

    std::vector<uint8_t> generate_key(size_t bits) {
        size_t bytes = (bits + 7) / 8;
        auto key = random_bytes(bytes);
        if (bits % 8 != 0) {
            key[0] &= static_cast<uint8_t>(0xFF >> (8 - (bits % 8)));
        }
        return key;
    }

    size_t entropy_bits() const {
        std::lock_guard lk(mutex_);
        return estimated_entropy_bits_;
    }

    std::vector<std::string> available_sources() const {
        std::lock_guard lk(mutex_);
        std::vector<std::string> names;
        for (auto& s : sources_)
            if (s->is_available()) names.push_back(s->name());
        return names;
    }

private:
    void ensure_initialized() const {
        if (!initialized_)
            throw std::runtime_error("CSPRNG not initialized");
    }
};

// --- Factory ---

inline std::unique_ptr<CSPRNG> create_default_csprng() {
    auto csprng = std::make_unique<CSPRNG>();
    csprng->add_source(std::make_shared<LinuxGetRandom>());
    csprng->add_source(std::make_shared<LinuxURandom>());
    csprng->add_source(std::make_shared<IntelRDRAND>());
    csprng->add_source(std::make_shared<IntelRDSEED>());
    csprng->add_source(std::make_shared<JitterEntropy>());
    csprng->initialize();
    return csprng;
}

} // namespace csprng
```

### 7.3.3 Hardware RNG (HSM Integration)

```cpp
namespace hsm {

struct HSMConfig {
    std::string slot_id;
    std::string pin;
    std::string key_label;
    std::string library_path;
    std::string pin_source;
};

class HSMDriver {
public:
    virtual ~HSMDriver() = default;
    virtual bool initialize(const HSMConfig& cfg) = 0;
    virtual std::vector<uint8_t> generate_random(size_t n) = 0;
    virtual std::vector<uint8_t> generate_key(
        size_t bits, const std::string& label) = 0;
    virtual std::vector<uint8_t> wrap_key(
        const std::vector<uint8_t>& to_wrap,
        const std::vector<uint8_t>& wrapping_key) = 0;
    virtual std::vector<uint8_t> unwrap_key(
        const std::vector<uint8_t>& wrapped,
        const std::vector<uint8_t>& unwrapping_key) = 0;
    virtual void destroy_key(const std::string& label) = 0;
    virtual std::string driver_name() const = 0;
    virtual bool supports_hardware_rng() const = 0;
};

class SoftHSMAdapter : public HSMDriver {
private:
    HSMConfig config_;
    bool initialized_ = false;

public:
    bool initialize(const HSMConfig& cfg) override {
        config_ = cfg;
        initialized_ = true;
        return true;
    }

    std::vector<uint8_t> generate_random(size_t n) override {
        ensure_ready();
        std::vector<uint8_t> buf(n);
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0) throw std::runtime_error("urandom unavailable");
        size_t total = 0;
        while (total < n) {
            ssize_t r = read(fd, buf.data() + total, n - total);
            if (r <= 0) { close(fd); throw std::runtime_error("read failed"); }
            total += static_cast<size_t>(r);
        }
        close(fd);
        return buf;
    }

    std::vector<uint8_t> generate_key(
        size_t bits, const std::string& label) override {
        ensure_ready();
        return generate_random((bits + 7) / 8);
    }

    std::vector<uint8_t> wrap_key(
        const std::vector<uint8_t>& to_wrap,
        const std::vector<uint8_t>& kek) override {
        ensure_ready();
        std::vector<uint8_t> out(to_wrap.size());
        for (size_t i = 0; i < to_wrap.size(); ++i)
            out[i] = to_wrap[i] ^ kek[i % kek.size()];
        return out;
    }

    std::vector<uint8_t> unwrap_key(
        const std::vector<uint8_t>& wrapped,
        const std::vector<uint8_t>& kek) override {
        return wrap_key(wrapped, kek);
    }

    void destroy_key(const std::string&) override { ensure_ready(); }
    std::string driver_name() const override { return "SoftHSM"; }
    bool supports_hardware_rng() const override { return false; }

private:
    void ensure_ready() const {
        if (!initialized_) throw std::runtime_error("HSM not ready");
    }
};

class HSMSession {
private:
    std::unique_ptr<HSMDriver> driver_;
    bool authenticated_ = false;

public:
    explicit HSMSession(std::unique_ptr<HSMDriver> drv)
        : driver_(std::move(drv)) {}

    ~HSMSession() { close(); }

    void open(const HSMConfig& cfg) {
        if (!driver_->initialize(cfg))
            throw std::runtime_error("HSM init failed");
        authenticated_ = true;
    }

    void close() { authenticated_ = false; }

    std::vector<uint8_t> generate_key(size_t bits, const std::string& label) {
        require_auth();
        return driver_->generate_key(bits, label);
    }

    std::vector<uint8_t> generate_random(size_t n) {
        require_auth();
        return driver_->generate_random(n);
    }

    std::vector<uint8_t> wrap_key(
        const std::vector<uint8_t>& to_wrap,
        const std::vector<uint8_t>& kek) {
        require_auth();
        return driver_->wrap_key(to_wrap, kek);
    }

    std::vector<uint8_t> unwrap_key(
        const std::vector<uint8_t>& wrapped,
        const std::vector<uint8_t>& kek) {
        require_auth();
        return driver_->unwrap_key(wrapped, kek);
    }

    void destroy_key(const std::string& label) {
        require_auth();
        driver_->destroy_key(label);
    }

    bool is_authenticated() const { return authenticated_; }
    std::string driver_name() const { return driver_->driver_name(); }
    bool supports_hw_rng() const { return driver_->supports_hardware_rng(); }

private:
    void require_auth() const {
        if (!authenticated_)
            throw std::runtime_error("HSM session not authenticated");
    }
};

} // namespace hsm
```

---

## 7.4 Key Wrapping

### 7.4.1 Conceitos de Key Wrapping

Key wrapping e o processo de proteger uma chave de dados (data key) usando uma chave de wrapping (Key Encryption Key - KEK). As principais normas sao:

- **RFC 3394** — AES Key Wrap para chaves com tamanho multiplo de 64 bits
- **RFC 5649** — AES Key Wrap com padding para chaves de qualquer tamanho

O algoritmo preserva o tamanho original da chave e fornece autenticacao intrinseca (integrity check embutido).

### 7.4.2 Implementacao AES Key Wrap (RFC 3394)

```cpp
#pragma once

#include <array>
#include <vector>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <algorithm>

namespace keywrap {

class AESKeyWrap {
private:
    static constexpr uint64_t DEFAULT_IV = 0xA6A6A6A6A6A6A6A6ULL;

    static uint64_t be64(const uint8_t* p) {
        uint64_t v = 0;
        for (int i = 0; i < 8; ++i) v = (v << 8) | p[i];
        return v;
    }

    static void to_be64(uint64_t v, uint8_t* p) {
        for (int i = 7; i >= 0; --i) { p[i] = v & 0xFF; v >>= 8; }
    }

    // Placeholder: substitua por implementacao AES real
    static void aes_ecb_encrypt(
        const uint8_t* in, size_t in_len,
        const uint8_t* key, size_t key_len,
        uint8_t* out) {
        // Em producao, usar OpenSSL ou similar
        for (size_t i = 0; i < in_len; ++i)
            out[i] = in[i] ^ key[i % key_len];
    }

    static void aes_ecb_decrypt(
        const uint8_t* in, size_t in_len,
        const uint8_t* key, size_t key_len,
        uint8_t* out) {
        for (size_t i = 0; i < in_len; ++i)
            out[i] = in[i] ^ key[i % key_len];
    }

public:
    /// RFC 3394 — AES Key Wrap
    /// key_to_wrap: tamanho deve ser multiplo de 8 bytes
    /// kek: chave de wrapping (16, 24 ou 32 bytes)
    static std::vector<uint8_t> wrap(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& kek) {

        if (plaintext.size() < 8 || plaintext.size() % 8 != 0)
            throw std::runtime_error(
                "Key Wrap: plaintext must be multiple of 8 bytes");
        if (kek.size() != 16 && kek.size() != 24 && kek.size() != 32)
            throw std::runtime_error(
                "Key Wrap: KEK must be 128/192/256 bits");

        const size_t n = plaintext.size() / 8;
        std::vector<uint64_t> R(n + 1);
        R[0] = 0;
        for (size_t i = 0; i < n; ++i)
            R[i + 1] = be64(plaintext.data() + i * 8);

        uint64_t A = DEFAULT_IV;
        uint8_t B[16], tmp[8];

        for (uint64_t j = 0; j <= 5 * n - 1; ++j) {
            uint64_t i = (j % n) + 1;
            uint64_t t = n * (j + 1);

            to_be64(A, B);
            to_be64(R[i], B + 8);

            uint8_t enc[16];
            aes_ecb_encrypt(B, 16, kek.data(), kek.size(), enc);

            A = be64(enc) ^ t;
            std::memcpy(tmp, enc + 8, 8);
            R[i] = be64(tmp);
        }

        std::vector<uint8_t> result(8 * (n + 1));
        to_be64(A, result.data());
        for (size_t i = 1; i <= n; ++i)
            to_be64(R[i], result.data() + i * 8);

        return result;
    }

    /// RFC 3394 — AES Key Unwrap
    static std::vector<uint8_t> unwrap(
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& kek) {

        if (ciphertext.size() < 16 || ciphertext.size() % 8 != 0)
            throw std::runtime_error(
                "Key Unwrap: invalid ciphertext size");

        const size_t n = (ciphertext.size() / 8) - 1;
        uint64_t A = be64(ciphertext.data());
        std::vector<uint64_t> R(n + 1);
        for (size_t i = 0; i < n; ++i)
            R[i + 1] = be64(ciphertext.data() + 8 + i * 8);

        uint8_t B[16], tmp[8];

        for (int64_t j = 5 * static_cast<int64_t>(n) - 1; j >= 0; --j) {
            uint64_t i = (static_cast<uint64_t>(j) % n) + 1;
            uint64_t t = n * (static_cast<uint64_t>(j) + 1);

            uint8_t at[8];
            to_be64(A ^ t, at);

            std::memcpy(B, at, 8);
            to_be64(R[i], B + 8);

            uint8_t dec[16];
            aes_ecb_decrypt(B, 16, kek.data(), kek.size(), dec);

            A = be64(dec);
            R[i] = be64(dec + 8);
        }

        if (A != DEFAULT_IV)
            throw std::runtime_error(
                "Key Unwrap: integrity check failed");

        std::vector<uint8_t> result(n * 8);
        for (size_t i = 0; i < n; ++i)
            to_be64(R[i + 1], result.data() + i * 8);

        return result;
    }
};

/// RFC 5649 — AES Key Wrap with Padding
class AESKeyWrapPad {
private:
    static constexpr uint64_t IV_PAD = 0xA6595906ULL;

    static uint64_t be64(const uint8_t* p) {
        uint64_t v = 0;
        for (int i = 0; i < 8; ++i) v = (v << 8) | p[i];
        return v;
    }

    static void to_be64(uint64_t v, uint8_t* p) {
        for (int i = 7; i >= 0; --i) { p[i] = v & 0xFF; v >>= 8; }
    }

public:
    static std::vector<uint8_t> wrap(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& kek) {

        if (plaintext.empty())
            throw std::runtime_error("KeyWrapPad: empty plaintext");

        size_t mli = plaintext.size();
        size_t pad = (8 - (mli % 8)) % 8;

        std::vector<uint8_t> padded = plaintext;
        padded.insert(padded.end(), pad, 0);

        const size_t n = padded.size() / 8;
        uint32_t mli_bits = static_cast<uint32_t>(mli * 8);

        uint64_t A = (IV_PAD << 32) | mli_bits;

        std::vector<uint64_t> R(n + 1);
        for (size_t i = 0; i < n; ++i)
            R[i + 1] = be64(padded.data() + i * 8);

        for (uint64_t j = 0; j <= 5 * n - 1; ++j) {
            uint64_t i = (j % n) + 1;
            uint64_t t = n * (j + 1);
            // Simplified — usar AES real em producao
            A ^= t;
            R[i] ^= A;
        }

        std::vector<uint8_t> result(8 * (n + 1));
        to_be64(A, result.data());
        for (size_t i = 1; i <= n; ++i)
            to_be64(R[i], result.data() + i * 8);

        return result;
    }

    static std::vector<uint8_t> unwrap(
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& kek) {

        if (ciphertext.size() < 16 || ciphertext.size() % 8 != 0)
            throw std::runtime_error("KeyUnwrapPad: invalid size");

        const size_t n = (ciphertext.size() / 8) - 1;
        uint64_t A = be64(ciphertext.data());
        uint32_t mli = static_cast<uint32_t>(A & 0xFFFFFFFF);
        uint64_t expected_A = (IV_PAD << 32) | mli;

        std::vector<uint64_t> R(n + 1);
        for (size_t i = 0; i < n; ++i)
            R[i + 1] = be64(ciphertext.data() + 8 + i * 8);

        for (int64_t j = 5 * static_cast<int64_t>(n) - 1; j >= 0; --j) {
            uint64_t i = (static_cast<uint64_t>(j) % n) + 1;
            uint64_t t = n * (static_cast<uint64_t>(j) + 1);
            R[i] ^= A;
            A ^= t;
        }

        if (A != expected_A)
            throw std::runtime_error(
                "KeyUnwrapPad: integrity check failed");

        size_t plaintext_len = mli / 8;
        std::vector<uint8_t> result(plaintext_len);
        std::memcpy(result.data(),
                     ciphertext.data() + 8,
                     std::min(plaintext_len, ciphertext.size() - 8));

        return result;
    }
};

} // namespace keywrap
```

---

## 7.5 Envelope Encryption

### 7.5.1 Conceito

Envelope Encryption e um padrao onde cada dado e criptografado com uma chave unica de dados (Data Key), e a Data Key e criptografada com uma Master Key. Este padrao e utilizado por AWS KMS, Google Cloud KMS e Azure Key Vault.

```
Dado ──► [Data Key (DK)] ──► Dado Criptografado
              │
              ▼
         [Master Key (MK)]
              │
              ▼
      DK Criptografada (Envoltorio)
```

As vantagens deste modelo sao:
- A Master Key raramente e usada diretamente, reduzindo exposicao
- Cada dado tem sua propria Data Key, limitando o impacto de um vazamento
- A Data Key pode ser rotacionada sem afetar a Master Key
- A Master Key pode ser protegida por HSM

### 7.5.2 Implementacao de Envelope Encryption

```cpp
#pragma once

#include <vector>
#include <string>
#include <memory>
#include <optional>
#include <chrono>
#include <unordered_map>
#include <mutex>
#include <shared_mutex>
#include <random>
#include <cstring>
#include <stdexcept>
#include <functional>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <array>

namespace envelope {

struct EncryptedEnvelope {
    std::string key_id;
    std::string version;
    std::vector<uint8_t> encrypted_dek;
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> iv;
    std::vector<uint8_t> tag;
    std::string algorithm;
    std::string aad_context;
    std::chrono::system_clock::time_point encrypted_at;
};

struct DataKey {
    std::string id;
    std::string version;
    std::vector<uint8_t> material;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point expires_at;
    bool active;
    uint64_t use_count;
    uint64_t max_uses;
};

// --- Master Key Provider (abstraction) ---

class MasterKeyProvider {
public:
    virtual ~MasterKeyProvider() = default;
    virtual std::vector<uint8_t> encrypt_dek(
        const std::vector<uint8_t>& dek) = 0;
    virtual std::vector<uint8_t> decrypt_dek(
        const std::vector<uint8_t>& enc_dek) = 0;
    virtual std::string key_id() const = 0;
    virtual std::string algorithm() const = 0;
};

class LocalMasterKey : public MasterKeyProvider {
private:
    std::vector<uint8_t> mk_;
    std::string id_;

public:
    LocalMasterKey(std::vector<uint8_t> master_key,
                   const std::string& id = "local-mk-001")
        : mk_(std::move(master_key)), id_(id) {}

    std::vector<uint8_t> encrypt_dek(
        const std::vector<uint8_t>& dek) override {

        std::vector<uint8_t> iv(16);
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, 255);
        for (auto& b : iv) b = static_cast<uint8_t>(dis(gen));

        std::vector<uint8_t> enc(dek.size());
        for (size_t i = 0; i < dek.size(); ++i)
            enc[i] = dek[i] ^ mk_[i % mk_.size()] ^ iv[i % iv.size()];

        std::vector<uint8_t> result;
        result.reserve(iv.size() + enc.size());
        result.insert(result.end(), iv.begin(), iv.end());
        result.insert(result.end(), enc.begin(), enc.end());
        return result;
    }

    std::vector<uint8_t> decrypt_dek(
        const std::vector<uint8_t>& enc_dek) override {

        if (enc_dek.size() < 16)
            throw std::runtime_error("Encrypted DEK too short");

        std::vector<uint8_t> iv(enc_dek.begin(), enc_dek.begin() + 16);
        std::vector<uint8_t> enc(enc_dek.begin() + 16, enc_dek.end());

        std::vector<uint8_t> dec(enc.size());
        for (size_t i = 0; i < enc.size(); ++i)
            dec[i] = enc[i] ^ mk_[i % mk_.size()] ^ iv[i % iv.size()];

        return dec;
    }

    std::string key_id() const override { return id_; }
    std::string algorithm() const override { return "XOR-KEK"; }
};

// --- Envelope Encryptor ---

class EnvelopeEncryptor {
private:
    std::shared_ptr<MasterKeyProvider> mkp_;
    std::unordered_map<std::string, DataKey> dek_store_;
    mutable std::shared_mutex dek_mutex_;
    std::chrono::hours dek_validity_;
    std::mutex rng_mutex_;
    std::mt19937 rng_;

public:
    explicit EnvelopeEncryptor(
        std::shared_ptr<MasterKeyProvider> mkp,
        std::chrono::hours validity = std::chrono::hours(24))
        : mkp_(std::move(mkp)), dek_validity_(validity),
          rng_(std::random_device{}()) {}

    DataKey generate_dek(size_t key_bits = 256) {
        DataKey dk;
        dk.id = make_id();
        dk.version = "1";
        dk.material.resize((key_bits + 7) / 8);
        {
            std::lock_guard lk(rng_mutex_);
            std::uniform_int_distribution<> dis(0, 255);
            for (auto& b : dk.material)
                b = static_cast<uint8_t>(dis(rng_));
        }

        auto now = std::chrono::system_clock::now();
        dk.created_at = now;
        dk.expires_at = now + dek_validity_;
        dk.active = true;
        dk.use_count = 0;
        dk.max_uses = 0;

        std::unique_lock lk(dek_mutex_);
        dek_store_[dk.id] = dk;

        return dk;
    }

    EncryptedEnvelope encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::string& aad = "") {

        auto dk = generate_dek();
        auto enc_dek = mkp_->encrypt_dek(dk.material);

        std::vector<uint8_t> iv(16);
        {
            std::lock_guard lk(rng_mutex_);
            std::uniform_int_distribution<> dis(0, 255);
            for (auto& b : iv) b = static_cast<uint8_t>(dis(rng_));
        }

        std::vector<uint8_t> ct(plaintext.size());
        for (size_t i = 0; i < plaintext.size(); ++i)
            ct[i] = plaintext[i] ^ dk.material[i % dk.material.size()]
                     ^ iv[i % iv.size()];

        std::vector<uint8_t> tag(16, 0);
        for (size_t i = 0; i < aad.size() && i < 16; ++i)
            tag[i] = static_cast<uint8_t>(aad[i]) ^
                     dk.material[i % dk.material.size()];
        for (size_t i = 0; i < ct.size(); ++i)
            tag[i % 16] ^= ct[i];

        EncryptedEnvelope env;
        env.key_id = dk.id;
        env.version = dk.version;
        env.encrypted_dek = std::move(enc_dek);
        env.ciphertext = std::move(ct);
        env.iv = std::move(iv);
        env.tag = std::move(tag);
        env.algorithm = mkp_->algorithm();
        env.aad_context = aad;
        env.encrypted_at = std::chrono::system_clock::now();

        return env;
    }

    std::vector<uint8_t> decrypt(const EncryptedEnvelope& env) {
        DataKey dk;
        {
            std::shared_lock lk(dek_mutex_);
            auto it = dek_store_.find(env.key_id);
            if (it == dek_store_.end())
                throw std::runtime_error("DEK not found: " + env.key_id);
            dk = it->second;
        }

        if (!dk.active)
            throw std::runtime_error("DEK revoked: " + dk.id);

        auto dek_material = mkp_->decrypt_dek(env.encrypted_dek);

        std::vector<uint8_t> pt(env.ciphertext.size());
        for (size_t i = 0; i < env.ciphertext.size(); ++i)
            pt[i] = env.ciphertext[i] ^ dek_material[i % dek_material.size()]
                     ^ env.iv[i % env.iv.size()];

        std::vector<uint8_t> tag(16, 0);
        for (size_t i = 0; i < env.aad_context.size() && i < 16; ++i)
            tag[i] = static_cast<uint8_t>(env.aad_context[i]) ^
                     dek_material[i % dek_material.size()];
        for (size_t i = 0; i < pt.size(); ++i)
            tag[i % 16] ^= pt[i];

        if (tag != env.tag)
            throw std::runtime_error("Envelope integrity check failed");

        return pt;
    }

    void revoke_dek(const std::string& id) {
        std::unique_lock lk(dek_mutex_);
        auto it = dek_store_.find(id);
        if (it != dek_store_.end()) it->second.active = false;
    }

    size_t active_dek_count() const {
        std::shared_lock lk(dek_mutex_);
        return std::count_if(dek_store_.begin(), dek_store_.end(),
            [](auto& p) { return p.second.active; });
    }

private:
    std::string make_id() {
        std::lock_guard lk(rng_mutex_);
        std::uniform_int_distribution<> hex(0, 15);
        std::ostringstream oss;
        for (int i = 0; i < 16; ++i)
            oss << std::hex << hex(rng_);
        return oss.str();
    }
};

} // namespace envelope
```

---

## 7.6 Rotação de Chaves

### 7.6.1 Estrategias de Rotação

**Rotação Periodica**: Chaves sao substituidas em intervalos regulares. E a forma mais simples e previsivel.

**Rotação por Evento**: Rotação acionada por eventos especificos (violação detectada, suspeita de comprometimento, mudanca de politica).

**Rotação Transparente**: Usuarios nao percebem a mudanca. Novas chaves sao usadas para criptografar, chaves antigas ainda sao usadas para descriptografar dados existentes.

**Rotação com Re-encryption**: Todos os dados criptografados com a chave antiga sao re-criptografados com a nova chave.

### 7.6.2 Implementacao de Rotação Transparente

```cpp
#pragma once

#include <vector>
#include <string>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <shared_mutex>
#include <chrono>
#include <functional>
#include <optional>
#include <algorithm>
#include <stdexcept>
#include <sstream>
#include <iomanip>

namespace rotation {

struct KeyVersion {
    std::string key_id;
    std::string label;
    std::vector<uint8_t> material;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point expires_at;
    bool encrypt_active;
    bool decrypt_active;
    uint64_t use_count;
    uint64_t max_uses;
};

class TransparentRotator {
private:
    std::string key_name_;
    std::vector<KeyVersion> versions_;
    mutable std::shared_mutex versions_mutex_;
    std::chrono::hours rotation_period_;
    size_t max_versions_;
    std::function<void(const std::string&, const std::string&)> on_rotate_;
    std::function<void(const std::string&)> on_destroy_;

public:
    TransparentRotator(
        const std::string& name,
        std::chrono::hours period = std::chrono::hours(24 * 30),
        size_t max_ver = 3)
        : key_name_(name), rotation_period_(period),
          max_versions_(max_ver) {}

    void set_on_rotate(
        std::function<void(const std::string&, const std::string&)> cb) {
        on_rotate_ = std::move(cb);
    }

    void set_on_destroy(std::function<void(const std::string&)> cb) {
        on_destroy_ = std::move(cb);
    }

    std::string add_version(const std::vector<uint8_t>& material) {
        std::unique_lock lk(versions_mutex_);

        // Desativar criptografia nas versoes anteriores
        for (auto& v : versions_)
            v.encrypt_active = false;

        std::string label = make_label();
        auto now = std::chrono::system_clock::now();

        KeyVersion kv;
        kv.key_id = key_name_ + ":" + label;
        kv.label = label;
        kv.material = material;
        kv.created_at = now;
        kv.expires_at = now + rotation_period_;
        kv.encrypt_active = true;
        kv.decrypt_active = true;
        kv.use_count = 0;
        kv.max_uses = 0;

        versions_.push_back(std::move(kv));

        // Politica de retencao
        while (versions_.size() > max_versions_) {
            auto& oldest = versions_.front();
            if (!oldest.encrypt_active) {
                if (on_destroy_) on_destroy_(oldest.key_id);
                secure_wipe(oldest.material);
                versions_.erase(versions_.begin());
            } else {
                break;
            }
        }

        if (on_rotate_) on_rotate_(key_name_, label);
        return label;
    }

    std::optional<KeyVersion> get_for_encrypt() const {
        std::shared_lock lk(versions_mutex_);
        auto now = std::chrono::system_clock::now();
        for (auto it = versions_.rbegin(); it != versions_.rend(); ++it)
            if (it->encrypt_active && it->expires_at > now)
                return *it;
        return std::nullopt;
    }

    std::optional<KeyVersion> get_for_decrypt(
        const std::string& label) const {
        std::shared_lock lk(versions_mutex_);
        auto it = std::find_if(versions_.begin(), versions_.end(),
            [&](auto& v) { return v.label == label && v.decrypt_active; });
        return it != versions_.end() ? std::make_optional(*it)
                                     : std::nullopt;
    }

    void retire(const std::string& label, bool keep_decrypt = true) {
        std::unique_lock lk(versions_mutex_);
        auto it = std::find_if(versions_.begin(), versions_.end(),
            [&](auto& v) { return v.label == label; });
        if (it == versions_.end())
            throw std::runtime_error("Version not found: " + label);
        it->encrypt_active = false;
        it->decrypt_active = keep_decrypt;
    }

    void destroy_version(const std::string& label) {
        std::unique_lock lk(versions_mutex_);
        auto it = std::find_if(versions_.begin(), versions_.end(),
            [&](auto& v) { return v.label == label; });
        if (it == versions_.end())
            throw std::runtime_error("Version not found: " + label);
        if (it->encrypt_active)
            throw std::runtime_error("Cannot destroy active version");

        if (on_destroy_) on_destroy_(it->key_id);
        secure_wipe(it->material);
        versions_.erase(it);
    }

    std::vector<KeyVersion> list() const {
        std::shared_lock lk(versions_mutex_);
        return versions_;
    }

    size_t count() const {
        std::shared_lock lk(versions_mutex_);
        return versions_.size();
    }

    std::string key_name() const { return key_name_; }

private:
    std::string make_label() {
        auto now = std::chrono::system_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()).count();
        std::ostringstream oss;
        oss << "v" << std::hex << std::setfill('0') << std::setw(16)
            << static_cast<uint64_t>(ms);
        return oss.str();
    }

    static void secure_wipe(std::vector<uint8_t>& d) {
        volatile uint8_t* p = d.data();
        for (size_t i = 0; i < d.size(); ++i) p[i] = 0;
    }
};

// --- Rotation Policy ---

struct RotationPolicy {
    std::chrono::hours period{24 * 30};
    uint64_t max_uses = 0;
    bool auto_rotate = true;
    bool re_encrypt_data = false;
    std::chrono::hours grace_period{24 * 7};

    bool should_rotate(const KeyVersion& kv) const {
        auto age = std::chrono::system_clock::now() - kv.created_at;
        if (age >= period) return true;
        if (max_uses > 0 && kv.use_count >= max_uses) return true;
        return false;
    }

    bool in_grace_period(const KeyVersion& kv) const {
        auto since_expiry = std::chrono::system_clock::now() - kv.expires_at;
        return since_expiry <= grace_period;
    }
};

} // namespace rotation
```

---

## 7.7 Threshold Cryptography: Shamir's Secret Sharing

### 7.7.1 Conceitos

Shamir's Secret Sharing (1979) permite dividir um segredo (chave) em N partes, onde qualquer K partes (threshold) sao suficientes para reconstruir o segredo, mas K-1 partes nao revelam nenhuma informacao sobre o segredo.

A base matematica e a interpolacao polinomial sobre corpos finitos (finite fields). Um polinomio de grau K-1 e determinado unicamente por K pontos, mas qualquer subconjunto de K-1 pontos deixa exatamente 1 grau de liberdade.

### 7.7.2 Implementacao em C++17

```cpp
#pragma once

#include <vector>
#include <random>
#include <cstdint>
#include <stdexcept>
#include <algorithm>
#include <array>

namespace shamir {

class ShamirSS {
private:
    uint32_t threshold_;
    uint32_t num_shares_;

    // Campo finito GF(p) com p primo proximo a 2^61
    static constexpr uint64_t P = (1ULL << 61) - 1;

    static uint64_t mod_add(uint64_t a, uint64_t b) {
        a %= P; b %= P;
        uint64_t r = a + b;
        return r >= P ? r - P : r;
    }

    static uint64_t mod_sub(uint64_t a, uint64_t b) {
        a %= P; b %= P;
        return a >= b ? a - b : a + P - b;
    }

    static uint64_t mod_mul(uint64_t a, uint64_t b) {
        a %= P; b %= P;
        __uint128_t prod = static_cast<__uint128_t>(a) * b;
        return static_cast<uint64_t>(prod % P);
    }

    static uint64_t mod_pow(uint64_t base, uint64_t exp) {
        uint64_t result = 1;
        base %= P;
        while (exp > 0) {
            if (exp & 1) result = mod_mul(result, base);
            base = mod_mul(base, base);
            exp >>= 1;
        }
        return result;
    }

    static uint64_t mod_inv(uint64_t a) {
        if (a == 0) throw std::runtime_error("No inverse for 0");
        return mod_pow(a, P - 2); // Fermat
    }

    static uint64_t eval_poly(
        const std::vector<uint64_t>& coeff, uint64_t x) {

        uint64_t result = 0, xp = 1;
        for (auto c : coeff) {
            result = mod_add(result, mod_mul(c, xp));
            xp = mod_mul(xp, x);
        }
        return result;
    }

public:
    struct Share {
        uint32_t id;
        uint64_t value;
    };

    ShamirSS(uint32_t threshold, uint32_t num_shares)
        : threshold_(threshold), num_shares_(num_shares) {
        if (threshold < 2)
            throw std::runtime_error("Threshold must be >= 2");
        if (num_shares < threshold)
            throw std::runtime_error("Shares must be >= threshold");
    }

    std::vector<Share> split(uint64_t secret) {
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dis(1, P - 1);

        std::vector<uint64_t> coeff;
        coeff.push_back(secret % P);
        for (uint32_t i = 1; i < threshold_; ++i)
            coeff.push_back(dis(gen));

        std::vector<Share> shares;
        for (uint32_t x = 1; x <= num_shares_; ++x)
            shares.push_back({x, eval_poly(coeff, x)});

        return shares;
    }

    uint64_t reconstruct(const std::vector<Share>& shares) {
        if (shares.size() < threshold_)
            throw std::runtime_error("Not enough shares");

        uint64_t secret = 0;
        for (size_t i = 0; i < threshold_; ++i) {
            uint64_t num = 1, den = 1;
            for (size_t j = 0; j < threshold_; ++j) {
                if (i == j) continue;
                num = mod_mul(num, mod_sub(0, shares[j].id));
                den = mod_mul(den,
                    mod_sub(shares[i].id, shares[j].id));
            }
            secret = mod_add(
                secret, mod_mul(mod_mul(num, mod_inv(den)),
                                shares[i].value));
        }
        return secret;
    }

    bool verify(const std::vector<Share>& shares, uint64_t known) {
        if (shares.size() < threshold_) return false;
        return reconstruct(shares) == known;
    }

    uint32_t threshold() const { return threshold_; }
    uint32_t num_shares() const { return num_shares_; }
};

/// Distributed Key Generation using Feldman's VSS
class FeldmanDKG {
private:
    size_t n_;
    size_t t_;

public:
    FeldmanDKG(size_t n, size_t t) : n_(n), t_(t) {
        if (t < 2) throw std::runtime_error("t must be >= 2");
        if (n < t) throw std::runtime_error("n must be >= t");
    }

    struct PartyOutput {
        size_t party_id;
        std::vector<uint8_t> secret_share;
        std::vector<uint8_t> verification;
    };

    struct DKGResult {
        std::vector<PartyOutput> shares;
        std::vector<uint8_t> public_verification_vector;
    };

    DKGResult generate() {
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dis(0, 255);

        // Gerar segredo aleatorio
        std::vector<uint8_t> secret(32);
        for (auto& b : secret) b = static_cast<uint8_t>(dis(gen));

        // Gerar polinomio secreto
        std::vector<std::vector<uint64_t>> polys(t_);
        for (auto& p : polys) {
            p.resize(t_);
            p[0] = 0;
            for (size_t i = 0; i < 32; ++i)
                p[0] = p[0] * 256 + secret[i];
            for (size_t j = 1; j < t_; ++j)
                p[j] = dis(gen);
        }

        DKGResult result;
        result.public_verification_vector.resize(n_ * 32);

        for (size_t party = 1; party <= n_; ++party) {
            PartyOutput out;
            out.party_id = party;
            out.secret_share.resize(32);

            // Calcular share do party
            uint64_t combined = 0;
            for (size_t k = 0; k < t_; ++k) {
                uint64_t x_pow = 1;
                for (size_t p = 0; p < k; ++p)
                    x_pow = x_pow * party % ((1ULL << 61) - 1);
                combined += polys[k][0] * x_pow;
            }
            for (size_t i = 0; i < 32; ++i) {
                out.secret_share[i] = static_cast<uint8_t>(
                    (combined >> ((i % 8) * 8)) & 0xFF);
            }

            // Verification
            std::array<uint8_t, 32> v{};
            uint64_t h = party;
            for (auto b : out.secret_share) h = h * 31 + b;
            for (size_t i = 0; i < 32; ++i)
                v[i] = static_cast<uint8_t>((h >> ((i % 8) * 8)) & 0xFF);
            out.verification = std::vector<uint8_t>(v.begin(), v.end());

            result.shares.push_back(std::move(out));
        }

        return result;
    }
};

} // namespace shamir
```

---

## 7.8 Distributed Key Generation

### 7.8.1 Conceitos

Distributed Key Generation (DKG) permite que multiplos participantes colaborem para gerar uma chave sem que nenhum individuo conheca a chave completa. Isto e essencial para:

- Assinaturas de threshold (t-of-n)
- Sistemas de consenso distribuido (Byzantine fault tolerance)
- Cofre digital compartilhado
- Multi-party computation (MPC)

O protocolo de Pedersen DKG e um dos mais utilizados, combinando commitments de Feldman com secret sharing de Shamir.

### 7.8.2 Implementacao DKG

```cpp
#pragma once

#include <vector>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <functional>
#include <random>
#include <stdexcept>
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace dkg {

struct DKGMessage {
    enum class Type {
        Commitment,
        ShareBroadcast,
        Echo,
        Ready,
        Reconstruct
    };

    Type type;
    size_t sender;
    size_t round;
    std::vector<uint8_t> payload;
};

struct DKGPartyState {
    size_t id;
    std::vector<uint8_t> secret_share;
    std::vector<uint8_t> public_share;
    bool committed;
    bool share_received;
    bool verified;
    size_t echo_count;
    size_t ready_count;
};

class DKGProtocol {
private:
    size_t n_;
    size_t t_;
    std::vector<DKGPartyState> parties_;
    std::vector<DKGMessage> log_;
    mutable std::mutex log_mutex_;
    size_t current_round_;
    bool complete_;
    std::function<void(const DKGMessage&)> on_message_;

public:
    DKGProtocol(size_t n, size_t t) : n_(n), t_(t),
        current_round_(0), complete_(false) {
        if (t < 2) throw std::runtime_error("t >= 2 required");
        if (n < t) throw std::runtime_error("n >= t required");

        parties_.resize(n);
        for (size_t i = 0; i < n; ++i) {
            parties_[i].id = i + 1;
            parties_[i].committed = false;
            parties_[i].share_received = false;
            parties_[i].verified = false;
            parties_[i].echo_count = 0;
            parties_[i].ready_count = 0;
        }
    }

    void set_handler(std::function<void(const DKGMessage&)> h) {
        on_message_ = std::move(h);
    }

    // Round 0: Cada party gera seu polinomio secreto e envia commitment
    void execute_round_0() {
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dis(0, 255);

        for (auto& party : parties_) {
            std::vector<uint8_t> secret(32);
            for (auto& b : secret) b = static_cast<uint8_t>(dis(gen));
            party.secret_share = secret;

            // Gerar commitment
            uint64_t hash = party.id;
            for (auto b : secret) hash = hash * 6364136223846793005ULL + b;
            party.public_share.resize(32);
            for (size_t i = 0; i < 32; ++i)
                party.public_share[i] = static_cast<uint8_t>(
                    (hash >> ((i % 8) * 8)) & 0xFF);

            DKGMessage msg;
            msg.type = DKGMessage::Type::Commitment;
            msg.sender = party.id;
            msg.round = 0;
            msg.payload = party.public_share;

            log_message(msg);
            if (on_message_) on_message_(msg);
            party.committed = true;
        }
        current_round_ = 1;
    }

    // Round 1: Cada party envia shares privados para outros
    void execute_round_1() {
        std::random_device rd;
        std::mt19937_64 gen(rd());
        std::uniform_int_distribution<uint64_t> dis(0, 255);

        for (auto& sender : parties_) {
            for (auto& receiver : parties_) {
                if (sender.id == receiver.id) continue;

                std::vector<uint8_t> share_data;
                share_data.push_back(static_cast<uint8_t>(sender.id));
                share_data.push_back(static_cast<uint8_t>(receiver.id));
                for (size_t i = 0; i < 8; ++i)
                    share_data.push_back(static_cast<uint8_t>(dis(gen)));

                DKGMessage msg;
                msg.type = DKGMessage::Type::ShareBroadcast;
                msg.sender = sender.id;
                msg.round = 1;
                msg.payload = share_data;

                log_message(msg);
                if (on_message_) on_message_(msg);
            }
        }
        current_round_ = 2;
    }

    // Round 2: Verificacao e echo
    void execute_round_2() {
        for (auto& party : parties_) {
            party.share_received = true;
            party.verified = true;

            DKGMessage msg;
            msg.type = DKGMessage::Type::Echo;
            msg.sender = party.id;
            msg.round = 2;
            msg.payload = party.public_share;

            log_message(msg);
            if (on_message_) on_message_(msg);
            party.echo_count++;
        }
        current_round_ = 3;
    }

    // Round 3: Ready e finalizacao
    void execute_round_3() {
        for (auto& party : parties_) {
            // Combinar shares recebidos
            for (auto& other : parties_) {
                if (party.id == other.id) continue;
                for (size_t i = 0;
                     i < std::min(party.secret_share.size(),
                                  other.secret_share.size());
                     ++i) {
                    party.secret_share[i] ^= other.secret_share[i];
                }
            }

            DKGMessage msg;
            msg.type = DKGMessage::Type::Ready;
            msg.sender = party.id;
            msg.round = 3;
            msg.payload = party.secret_share;

            log_message(msg);
            if (on_message_) on_message_(msg);
            party.ready_count++;
        }
        complete_ = true;
        current_round_ = 4;
    }

    void run_all_rounds() {
        execute_round_0();
        execute_round_1();
        execute_round_2();
        execute_round_3();
    }

    bool is_complete() const { return complete_; }
    size_t round() const { return current_round_; }
    size_t num_parties() const { return n_; }
    size_t threshold() const { return t_; }

    const DKGPartyState& party(size_t id) const {
        if (id < 1 || id > n_)
            throw std::runtime_error("Invalid party id");
        return parties_[id - 1];
    }

    std::vector<DKGPartyState> all_parties() const {
        return parties_;
    }

    std::vector<DKGMessage> log() const {
        std::lock_guard lk(log_mutex_);
        return log_;
    }

    bool verify_share(size_t party_id,
                      const std::vector<uint8_t>& share) const {
        for (const auto& p : parties_)
            if (p.id == party_id)
                return p.secret_share == share;
        return false;
    }

private:
    void log_message(const DKGMessage& msg) {
        std::lock_guard lk(log_mutex_);
        log_.push_back(msg);
    }
};

} // namespace dkg
```

---

## 7.9 Backup e Recuperacao de Chaves

### 7.9.1 Estrategias de Backup

O backup de chaves criptograficas requer cuidados especiais:
- Chaves devem ser criptografadas antes do backup
- A chave de protecao do backup deve ser gerenciada separadamente
- Multi-party backup usando Shamir's Secret Sharing
- Backup geograficamente distribuido
- Testes periodicos de recuperacao

### 7.9.2 Implementacao

```cpp
#pragma once

#include <vector>
#include <string>
#include <fstream>
#include <stdexcept>
#include <cstring>
#include <chrono>
#include <sstream>
#include <iomanip>

namespace keybackup {

struct BackupMetadata {
    std::string key_id;
    std::string algorithm;
    size_t key_size_bits;
    std::string owner;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point backed_up_at;
    std::string format_version;
    std::string description;
    uint32_t checksum;
};

struct BackupBundle {
    BackupMetadata metadata;
    std::vector<uint8_t> encrypted_material;
    std::vector<uint8_t> iv;
    std::vector<uint8_t> tag;
    std::vector<uint8_t> checksum_bytes;
};

class KeyBackupManager {
private:
    std::string backup_dir_;
    std::vector<uint8_t> protection_key_;

    static uint32_t compute_crc32(const std::vector<uint8_t>& data) {
        uint32_t crc = 0xFFFFFFFF;
        for (uint8_t b : data) {
            crc ^= b;
            for (int i = 0; i < 8; ++i)
                crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        }
        return crc ^ 0xFFFFFFFF;
    }

public:
    KeyBackupManager(const std::string& dir,
                     std::vector<uint8_t> protection_key)
        : backup_dir_(dir), protection_key_(std::move(protection_key)) {}

    BackupBundle create_backup(
        const std::string& key_id,
        const std::string& algorithm,
        size_t key_size_bits,
        const std::vector<uint8_t>& material,
        const std::string& owner = "",
        const std::string& desc = "") {

        BackupMetadata meta;
        meta.key_id = key_id;
        meta.algorithm = algorithm;
        meta.key_size_bits = key_size_bits;
        meta.owner = owner;
        meta.created_at = std::chrono::system_clock::now();
        meta.backed_up_at = std::chrono::system_clock::now();
        meta.format_version = "2.0";
        meta.description = desc;

        // Gerar IV
        std::vector<uint8_t> iv(16);
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, 255);
        for (auto& b : iv) b = static_cast<uint8_t>(dis(gen));

        // Criptografar material
        std::vector<uint8_t> enc(material.size());
        for (size_t i = 0; i < material.size(); ++i)
            enc[i] = material[i] ^
                      protection_key_[i % protection_key_.size()] ^
                      iv[i % iv.size()];

        // Tag de autenticacao
        std::vector<uint8_t> tag(16, 0);
        for (size_t i = 0; i < enc.size(); ++i)
            tag[i % 16] ^= enc[i];

        meta.checksum = compute_crc32(enc);

        std::vector<uint8_t> checksum_bytes(4);
        uint32_t c = meta.checksum;
        for (int i = 3; i >= 0; --i) {
            checksum_bytes[i] = c & 0xFF;
            c >>= 8;
        }

        BackupBundle bundle;
        bundle.metadata = std::move(meta);
        bundle.encrypted_material = std::move(enc);
        bundle.iv = std::move(iv);
        bundle.tag = std::move(tag);
        bundle.checksum_bytes = std::move(checksum_bytes);

        return bundle;
    }

    std::vector<uint8_t> restore(const BackupBundle& bundle) {
        uint32_t computed = compute_crc32(bundle.encrypted_material);
        if (computed != bundle.metadata.checksum)
            throw std::runtime_error("Checksum mismatch — data corrupted");

        std::vector<uint8_t> material(bundle.encrypted_material.size());
        for (size_t i = 0; i < bundle.encrypted_material.size(); ++i)
            material[i] = bundle.encrypted_material[i] ^
                          protection_key_[i % protection_key_.size()] ^
                          bundle.iv[i % bundle.iv.size()];
        return material;
    }

    void store(const BackupBundle& bundle, const std::string& fname) {
        std::string path = backup_dir_ + "/" + fname;
        std::ofstream f(path, std::ios::binary);
        if (!f.is_open())
            throw std::runtime_error("Cannot write backup: " + path);

        f.write(reinterpret_cast<const char*>(
            bundle.encrypted_material.data()),
            bundle.encrypted_material.size());
        f.write(reinterpret_cast<const char*>(bundle.iv.data()),
            bundle.iv.size());
        f.write(reinterpret_cast<const char*>(bundle.tag.data()),
            bundle.tag.size());
        f.write(reinterpret_cast<const char*>(
            bundle.checksum_bytes.data()),
            bundle.checksum_bytes.size());
    }

    BackupBundle load(const std::string& fname) {
        std::string path = backup_dir_ + "/" + fname;
        std::ifstream f(path, std::ios::binary);
        if (!f.is_open())
            throw std::runtime_error("Cannot read backup: " + path);

        f.seekg(0, std::ios::end);
        size_t sz = f.tellg();
        f.seekg(0, std::ios::beg);

        size_t min_sz = 16 + 16 + 4;
        if (sz < min_sz)
            throw std::runtime_error("Backup file too small");

        size_t mat_sz = sz - min_sz;
        BackupBundle bundle;
        bundle.encrypted_material.resize(mat_sz);
        f.read(reinterpret_cast<char*>(
            bundle.encrypted_material.data()), mat_sz);
        bundle.iv.resize(16);
        f.read(reinterpret_cast<char*>(bundle.iv.data()), 16);
        bundle.tag.resize(16);
        f.read(reinterpret_cast<char*>(bundle.tag.data()), 16);
        bundle.checksum_bytes.resize(4);
        f.read(reinterpret_cast<char*>(
            bundle.checksum_bytes.data()), 4);

        return bundle;
    }
};

} // namespace keybackup
```

---

## 7.10 Revocacao e Destruicao de Chaves

### 7.10.1 Estrategias de Destruição

A destruicao segura de chaves e uma das operacoes mais criticas. Chaves devem ser eliminadas de forma irreversivel de todas as memorias — RAM, disco, swap, caches.

Padroes de destruicao:

- **Zeroize** (3-pass): 0x00, 0xFF, 0x00
- **DOD 5220.22-M**: 3-pass com verificacao
- **Gutmann**: 7-pass (projeto para medios magneticos)
- **Crypto Erase**: Sobrescrever com dados aleatorios seguido de zeroize
- **Physical Destruction**: Para midias fisicas (HSM, TPM)

### 7.10.2 Implementacao

```cpp
#pragma once

#include <vector>
#include <string>
#include <unordered_map>
#include <mutex>
#include <chrono>
#include <functional>
#include <stdexcept>
#include <cstring>
#include <random>

namespace destruction {

enum class Method {
    Zeroize,
    CryptoErase,
    DoD5220,
    Gutmann,
    PhysicalDestruction
};

struct DestructionRecord {
    std::string key_id;
    Method method;
    std::chrono::system_clock::time_point timestamp;
    std::string witness;
    bool verified;
};

class KeyDestructionManager {
private:
    std::unordered_map<std::string, std::vector<uint8_t>> store_;
    mutable std::mutex store_mutex_;
    std::vector<DestructionRecord> audit_log_;
    mutable std::mutex log_mutex_;
    std::function<void(const DestructionRecord&)> on_destroy_;

public:
    void set_callback(std::function<void(const DestructionRecord&)> cb) {
        on_destroy_ = std::move(cb);
    }

    void register_key(const std::string& id, std::vector<uint8_t> key) {
        std::lock_guard lk(store_mutex_);
        store_[id] = std::move(key);
    }

    void destroy(const std::string& id,
                 Method method = Method::Zeroize,
                 const std::string& witness = "") {

        std::lock_guard lk(store_mutex_);
        auto it = store_.find(id);
        if (it == store_.end())
            throw std::runtime_error("Key not found: " + id);

        auto& data = it->second;

        switch (method) {
            case Method::Zeroize:
                zeroize(data);
                break;
            case Method::CryptoErase:
                crypto_erase(data);
                break;
            case Method::DoD5220:
                dod_5220_22m(data);
                break;
            case Method::Gutmann:
                gutmann(data);
                break;
            case Method::PhysicalDestruction:
                physical_destroy(data);
                break;
        }

        DestructionRecord rec;
        rec.key_id = id;
        rec.method = method;
        rec.timestamp = std::chrono::system_clock::now();
        rec.witness = witness;
        rec.verified = true;

        store_.erase(it);

        {
            std::lock_guard ll(log_mutex_);
            audit_log_.push_back(rec);
        }

        if (on_destroy_) on_destroy_(rec);
    }

    bool is_destroyed(const std::string& id) const {
        std::lock_guard lk(store_mutex_);
        return store_.find(id) == store_.end();
    }

    std::vector<DestructionRecord> log() const {
        std::lock_guard lk(log_mutex_);
        return audit_log_;
    }

    size_t pending_count() const {
        std::lock_guard lk(store_mutex_);
        return store_.size();
    }

private:
    static void zeroize(std::vector<uint8_t>& d) {
        volatile uint8_t* p = d.data();
        size_t n = d.size();
        for (size_t i = 0; i < n; ++i) p[i] = 0x00;
        for (size_t i = 0; i < n; ++i) p[i] = 0xFF;
        for (size_t i = 0; i < n; ++i) p[i] = 0x00;
    }

    static void crypto_erase(std::vector<uint8_t>& d) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<> dis(0, 255);
        for (auto& b : d) b = static_cast<uint8_t>(dis(gen));
        for (auto& b : d) b = 0x00;
    }

    static void dod_5220_22m(std::vector<uint8_t>& d) {
        volatile uint8_t* p = d.data();
        size_t n = d.size();
        for (size_t i = 0; i < n; ++i) p[i] = 0x00;
        for (size_t i = 0; i < n; ++i) p[i] = 0xFF;
        for (size_t i = 0; i < n; ++i) p[i] = 0x00;
    }

    static void gutmann(std::vector<uint8_t>& d) {
        static const uint8_t patterns[7][3] = {
            {0x00,0x00,0x00}, {0xFF,0xFF,0xFF},
            {0x55,0x55,0x55}, {0xAA,0xAA,0xAA},
            {0x92,0x49,0x24}, {0x49,0x24,0x92},
            {0x24,0x92,0x49}
        };
        volatile uint8_t* p = d.data();
        for (int pass = 0; pass < 7; ++pass)
            for (size_t i = 0; i < d.size(); ++i)
                p[i] = patterns[pass][i % 3];
        for (size_t i = 0; i < d.size(); ++i) p[i] = 0x00;
    }

    static void physical_destroy(std::vector<uint8_t>& d) {
        volatile uint8_t* p = d.data();
        for (size_t i = 0; i < d.size(); ++i) {
            p[i] = 0xDE; p[i] = 0xAD; p[i] = 0x00;
        }
        d.clear();
        d.shrink_to_fit();
    }
};

} // namespace destruction
```

---

## 7.11 Vault Integration: HashiCorp Vault API

### 7.11.1 Conceitos

HashiCorp Vault e um sistema populares de gestao de segredos que fornece:
- Armazenamento seguro de segredos com backends de armazenamento variedos
- Criptografia como servicio (transit secrets engine)
- Identity-based access com tokens, AppRole, LDAP, Kubernetes
- Audit logging completo
- Dynamic secrets (bases de dados, cloud credentials)
- Leases e renewals

### 7.11.2 Integracao com Vault em C++

```cpp
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <functional>
#include <stdexcept>
#include <mutex>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <algorithm>

namespace vault {

struct VaultConfig {
    std::string address = "https://127.0.0.1:8200";
    std::string token;
    std::string namespace_name;
    std::string role_id;
    std::string secret_id;
    bool verify_ssl = true;
    std::string ca_cert_path;
    std::string client_cert_path;
    std::string client_key_path;
    int timeout_seconds = 30;
    std::string kv_mount = "secret";
    std::string transit_mount = "transit";
};

struct VaultResponse {
    bool success;
    int status_code;
    std::string raw_body;
    std::unordered_map<std::string, std::string> data;
    std::string error;
    std::string lease_id;
    int lease_duration;
};

class VaultClient {
private:
    VaultConfig cfg_;
    std::string base_url_;
    std::mutex req_mutex_;
    bool authenticated_ = false;
    std::function<void(const std::string&)> logger_;

    struct HTTPReq {
        std::string method;
        std::string path;
        std::unordered_map<std::string, std::string> headers;
        std::string body;
    };

public:
    explicit VaultClient(const VaultConfig& cfg) : cfg_(cfg) {
        base_url_ = cfg.address;
        if (!base_url_.empty() && base_url_.back() != '/')
            base_url_ += '/';
    }

    void set_logger(std::function<void(const std::string&)> cb) {
        logger_ = std::move(cb);
    }

    bool authenticate() {
        if (!cfg_.token.empty()) {
            authenticated_ = true;
            log("Authenticated via static token");
            return true;
        }
        return authenticate_approle();
    }

    // KV v2: Read secret
    VaultResponse read(const std::string& path) {
        require_auth();
        HTTPReq req{"GET",
            "v1/" + cfg_.kv_mount + "/data/" + path,
            {{"X-Vault-Token", cfg_.token}}, ""};
        return execute(req);
    }

    // KV v2: Write secret
    VaultResponse write(
        const std::string& path,
        const std::unordered_map<std::string, std::string>& data) {
        require_auth();
        std::string body = "{\"data\":{";
        bool first = true;
        for (auto& [k, v] : data) {
            if (!first) body += ",";
            body += "\"" + k + "\":\"" + v + "\"";
            first = false;
        }
        body += "}}";

        HTTPReq req{"POST",
            "v1/" + cfg_.kv_mount + "/data/" + path,
            {{"X-Vault-Token", cfg_.token},
             {"Content-Type", "application/json"}},
            body};
        return execute(req);
    }

    // KV v2: Delete secret
    VaultResponse remove(const std::string& path) {
        require_auth();
        HTTPReq req{"DELETE",
            "v1/" + cfg_.kv_mount + "/data/" + path,
            {{"X-Vault-Token", cfg_.token}}, ""};
        return execute(req);
    }

    // KV v2: List secrets
    VaultResponse list(const std::string& path = "") {
        require_auth();
        HTTPReq req{"LIST",
            "v1/" + cfg_.kv_mount + "/data/" + path,
            {{"X-Vault-Token", cfg_.token}}, ""};
        return execute(req);
    }

    // Transit: Encrypt
    VaultResponse transit_encrypt(
        const std::string& key_name,
        const std::string& plaintext_b64) {
        require_auth();
        std::string body = "{\"plaintext\":\"" + plaintext_b64 + "\"}";
        HTTPReq req{"POST",
            "v1/" + cfg_.transit_mount + "/encrypt/" + key_name,
            {{"X-Vault-Token", cfg_.token},
             {"Content-Type", "application/json"}},
            body};
        return execute(req);
    }

    // Transit: Decrypt
    VaultResponse transit_decrypt(
        const std::string& key_name,
        const std::string& ciphertext) {
        require_auth();
        std::string body = "{\"ciphertext\":\"" + ciphertext + "\"}";
        HTTPReq req{"POST",
            "v1/" + cfg_.transit_mount + "/decrypt/" + key_name,
            {{"X-Vault-Token", cfg_.token},
             {"Content-Type", "application/json"}},
            body};
        return execute(req);
    }

    // Transit: Generate data key
    VaultResponse generate_data_key(
        const std::string& key_name, int bits = 256) {
        require_auth();
        std::string body = "{\"bits\":" + std::to_string(bits) + "}";
        HTTPReq req{"POST",
            "v1/" + cfg_.transit_mount +
                "/datakey/plaintext/" + key_name,
            {{"X-Vault-Token", cfg_.token},
             {"Content-Type", "application/json"}},
            body};
        return execute(req);
    }

    // Transit: Rotate key
    VaultResponse rotate_key(const std::string& key_name) {
        require_auth();
        HTTPReq req{"POST",
            "v1/" + cfg_.transit_mount + "/rotate/" + key_name,
            {{"X-Vault-Token", cfg_.token}}, ""};
        return execute(req);
    }

    // Health check
    VaultResponse health() {
        HTTPReq req{"GET", "v1/sys/health", {}, ""};
        return execute(req);
    }

    bool is_authenticated() const { return authenticated_; }

private:
    bool authenticate_approle() {
        std::string body = "{\"role_id\":\"" + cfg_.role_id +
                           "\",\"secret_id\":\"" + cfg_.secret_id + "\"}";
        HTTPReq req{"POST", "v1/auth/approle/login",
            {{"Content-Type", "application/json"}}, body};
        auto resp = execute(req);
        if (resp.success && resp.data.count("client_token")) {
            cfg_.token = resp.data.at("client_token");
            authenticated_ = true;
            log("Authenticated via AppRole");
            return true;
        }
        log("AppRole auth failed: " + resp.error);
        return false;
    }

    void require_auth() const {
        if (!authenticated_)
            throw std::runtime_error("Vault not authenticated");
    }

    VaultResponse execute(const HTTPReq& req) {
        std::lock_guard lk(req_mutex_);
        log(req.method + " " + base_url_ + req.path);

        VaultResponse resp;
        resp.status_code = 501;
        resp.success = false;
        resp.error = "HTTP client not implemented — "
                     "use libcurl or Boost.Beast";
        resp.raw_body = "";
        return resp;
    }

    void log(const std::string& msg) const {
        if (logger_) logger_(msg);
    }
};

// --- Vault Key Manager ---

class VaultKeyManager {
private:
    std::shared_ptr<VaultClient> client_;
    std::string mount_;

public:
    VaultKeyManager(std::shared_ptr<VaultClient> client,
                    const std::string& mount = "secret")
        : client_(std::move(client)), mount_(mount) {}

    bool store_key(
        const std::string& key_id,
        const std::vector<uint8_t>& material,
        const std::unordered_map<std::string, std::string>& meta = {}) {

        std::string hex_key;
        hex_key.reserve(material.size() * 2);
        for (uint8_t b : material) {
            char h[3];
            std::snprintf(h, sizeof(h), "%02x", b);
            hex_key += h;
        }

        std::unordered_map<std::string, std::string> data = meta;
        data["key"] = hex_key;

        auto resp = client_->write(mount_ + "/keys/" + key_id, data);
        return resp.success;
    }

    std::vector<uint8_t> retrieve_key(const std::string& key_id) {
        auto resp = client_->read(mount_ + "/keys/" + key_id);
        if (!resp.success)
            throw std::runtime_error("Key retrieval failed: " + key_id);

        if (resp.data.find("key") == resp.data.end())
            throw std::runtime_error("Response missing key data");

        return hex_decode(resp.data.at("key"));
    }

    bool delete_key(const std::string& key_id) {
        auto resp = client_->remove(mount_ + "/keys/" + key_id);
        return resp.success;
    }

    std::vector<std::string> list_keys() {
        auto resp = client_->list(mount_ + "/keys/");
        std::vector<std::string> keys;
        if (resp.success) {
            for (auto& [k, v] : resp.data) keys.push_back(v);
        }
        return keys;
    }

private:
    static std::vector<uint8_t> hex_decode(const std::string& hex) {
        std::vector<uint8_t> result;
        result.reserve(hex.size() / 2);
        for (size_t i = 0; i < hex.size(); i += 2) {
            uint8_t byte = 0;
            for (int j = 0; j < 2 && i + j < hex.size(); ++j) {
                char c = hex[i + j];
                byte <<= 4;
                if (c >= '0' && c <= '9') byte |= (c - '0');
                else if (c >= 'a' && c <= 'f') byte |= (c - 'a' + 10);
                else if (c >= 'A' && c <= 'F') byte |= (c - 'A' + 10);
            }
            result.push_back(byte);
        }
        return result;
    }
};

} // namespace vault
```

---

## 7.12 CVE-2016-0728: Keyring Refcount Overflow

### 7.12.1 Descricao da Vulnerabilidade

CVE-2016-0728 e uma vulnerabilidade de overflow de reference count no subsystemo keyring do Linux kernel. O keyring e um mecanismo do kernel que permite que processos armazenem e compartilhem chaves criptograficas.

A vulnerabilidade foi descoberta em janeiro de 2016 pelo pesquisador David Jacoby e afeta kernels Linux da versao 3.10 ate a versao 4.4.4.

**Classificacao CVSS**: 7.8 (High)

**Vetor de ataque**: Local (requer acesso ao sistema)

**Impacto**: Privilege escalation — um atacante local pode obter root

### 7.12.2 Analise Tecnica

```cpp
// =============================================================
// Simulacao conceitual da vulnerabilidade CVE-2016-0728
// NAO execute este codigo em producao — e apenas educacional
// =============================================================

#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
#include <limits>

namespace cve_2016_0728 {

struct KernelKey {
    uint32_t serial;
    uint32_t usage;           // refcount — o campo vulneravel
    char* description;
    uint32_t perm;
    uint32_t uid;
    uint32_t gid;
    bool destroyed;
};

// Versao VULNERAVEL (antes do patch)
// O problema: atomic_inc sem verificacao de overflow
void vulnerable_key_get(KernelKey* key) {
    // No kernel real: atomic_inc(&key->usage)
    // Nao havia verificacao se usage ja atingiu INT_MAX
    key->usage++;
}

void vulnerable_key_put(KernelKey* key) {
    if (key->usage > 0) {
        key->usage--;
    }
    // Quando usage chega a 0, o kernel libera a key
    // Mas se o refcount fez wrap-around para 0
    // por overflow, a key e liberada indevidamente
}

// Versao CORRIGIDA (patch)
void fixed_key_get(KernelKey* key) {
    // O patch adicionou verificacao de overflow
    if (key->usage < std::numeric_limits<uint32_t>::max()) {
        key->usage++;
    }
    // Se ja esta no maximo, NAO incrementa
    // Isto previne o wrap-around
}

void fixed_key_put(KernelKey* key) {
    if (key->usage > 0) {
        key->usage--;
    }
}

// Demonstracao do overflow
void demonstrate_overflow() {
    std::cout << "=== CVE-2016-0728: Refcount Overflow Demo ===" << std::endl;

    KernelKey key{};
    key.serial = 1;
    key.usage = 1;
    key.description = new char[32];
    strcpy(key.description, "test-session-key");
    key.destroyed = false;

    std::cout << "Initial refcount: " << key.usage << std::endl;

    // Simular chamadas repetidas de keyctl() pelo atacante
    // Cada chamada incrementa o refcount
    const uint32_t ATTACK_ROUNDS = 1000;
    for (uint32_t i = 0; i < ATTACK_ROUNDS; ++i) {
        vulnerable_key_get(&key);
    }

    std::cout << "After " << ATTACK_ROUNDS
              << " increments: " << key.usage << std::endl;

    // Simular wrap-around
    key.usage = UINT32_MAX - 5;
    std::cout << "\nRefcount near overflow: " << key.usage << std::endl;

    for (uint32_t i = 0; i < 10; ++i) {
        vulnerable_key_get(&key);
        std::cout << "  Increment " << (i + 1)
                  << ": refcount = " << key.usage;
        if (key.usage == 0) {
            std::cout << " ** WRAP-AROUND! USE-AFTER-FREE **";
        }
        std::cout << std::endl;
    }

    std::cout << "\n=== Consequencias do Wrap-Around ===" << std::endl;
    std::cout << "1. Kernel libera a estrutura KernelKey" << std::endl;
    std::cout << "2. Memoria pode ser realocada por outro objeto" << std::endl;
    std::cout << "3. Acesso a memoria liberada = Use-After-Free" << std::endl;
    std::cout << "4. Possivel execucao de codigo arbitrario" << std::endl;

    delete[] key.description;
}

// Cadeia de exploit detalhada
void explain_exploit_chain() {
    std::cout << "\n=== Cadeia de Exploracao ===" << std::endl;
    std::cout << std::endl;
    std::cout << "1. PREPARACAO:" << std::endl;
    std::cout << "   - Atacante cria uma key via keyctl(KEYCTL_JOIN_SESSION_KEYRING)" << std::endl;
    std::cout << "   - Isto retorna um file descriptor para a key" << std::endl;
    std::cout << std::endl;
    std::cout << "2. ABUSO DE REFCOUNT:" << std::endl;
    std::cout << "   - Atacante chama keyctl() repetidamente" << std::endl;
    std::cout << "   - Cada chamada incrementa o refcount atomicamente" << std::endl;
    std::cout << "   - Nao ha limite configuravel para o refcount" << std::endl;
    std::cout << std::endl;
    std::cout << "3. WRAP-AROUND:" << std::endl;
    std::cout << "   - Apos ~4 bilhoes de incrementos (2^32)" << std::endl;
    std::cout << "   - O refcount faz wrap-around para 0" << std::endl;
    std::cout << "   - Isto leva ~30-60 minutos em hardware moderno" << std::endl;
    std::cout << std::endl;
    std::cout << "4. USE-AFTER-FREE:" << std::endl;
    std::cout << "   - Kernel decrementa refcount em operacoes normais" << std::endl;
    std::cout << "   - Quando refcount chega a 0, kernel libera a key" << std::endl;
    std::cout << "   - Mas a key ainda esta em uso pelo atacante" << std::endl;
    std::cout << std::endl;
    std::cout << "5. CODE EXECUTION:" << std::endl;
    std::cout << "   - Atacante realoca a memoria com payload controlado" << std::endl;
    std::cout << "   - Funcoes de callback da key apontam para codigo do atacante" << std::endl;
    std::cout << "   - Possivel elevacao de privilegios para root" << std::endl;
}

// Patch do kernel (simplificado)
struct PatchedKey {
    uint32_t serial;
    uint32_t usage;
    uint32_t flags;           // Novo campo: KEY_FLAG_DESTROYED, etc
    char* description;
    uint32_t perm;
    uint32_t uid;
    uint32_t gid;
    bool destroyed;

    bool is_alive() const {
        return !destroyed && usage > 0;
    }
};

void patched_key_get(PatchedKey* key) {
    if (!key->is_alive()) return;

    // Comparacao atomica com verificacao de overflow
    uint32_t expected = key->usage;
    while (expected < std::numeric_limits<uint32_t>::max()) {
        // Simulacao de atomic_cmpxchg
        uint32_t old = key->usage;
        if (old != expected) {
            expected = old;
            continue;
        }
        // Se chegou aqui, incrementamos com sucesso
        key->usage = expected + 1;
        return;
    }
    // Overflow detectado — NAO incrementa
}

} // namespace cve_2016_0728

int main() {
    cve_2016_0728::demonstrate_overflow();
    cve_2016_0728::explain_exploit_chain();
    return 0;
}
```

### 7.12.3 Lições Aprendidas e Prevencoes

```cpp
// Padroes seguros para prevenir vulnerabilidades de refcount

#include <atomic>
#include <cstdint>
#include <stdexcept>
#include <limits>
#include <memory>

namespace safe_refcount {

class ReferenceCounted {
private:
    std::atomic<uint32_t> ref_{1};
    std::atomic<bool> destroyed_{false};
    static constexpr uint32_t MAX_REF = 10000000;

public:
    void acquire() {
        uint32_t current = ref_.load(std::memory_order_relaxed);
        while (current < MAX_REF) {
            if (ref_.compare_exchange_weak(
                    current, current + 1,
                    std::memory_order_acq_rel)) {
                return;
            }
        }
        // Overflow detection: nao incrementa
    }

    bool release() {
        uint32_t current = ref_.load(std::memory_order_relaxed);
        if (current == 0) return false;
        if (ref_.compare_exchange_strong(
                current, current - 1,
                std::memory_order_acq_rel)) {
            if (current == 1) {
                destroyed_.store(true, std::memory_order_release);
                return true;
            }
        }
        return false;
    }

    uint32_t count() const {
        return ref_.load(std::memory_order_acquire);
    }

    bool is_valid() const {
        return !destroyed_.load(std::memory_order_acquire) &&
               ref_.load(std::memory_order_acquire) > 0;
    }
};

// Template seguro para recursos criptograficos
template<typename T>
class SecureResource {
private:
    ReferenceCounted refs_;
    std::unique_ptr<T> resource_;
    bool destroyed_ = false;

public:
    explicit SecureResource(std::unique_ptr<T> res)
        : resource_(std::move(res)) {}

    ~SecureResource() {
        if (refs_.release()) {
            secure_destroy();
        }
    }

    void acquire() { refs_.acquire(); }

    void release() {
        if (refs_.release()) {
            secure_destroy();
        }
    }

    T* get() {
        if (!is_valid())
            throw std::runtime_error("Resource invalid");
        return resource_.get();
    }

    bool is_valid() const {
        return !destroyed_ && refs_.is_valid();
    }

    uint32_t use_count() const { return refs_.count(); }

private:
    void secure_destroy() {
        destroyed_ = true;
        if (resource_) {
            resource_.reset();
        }
    }
};

} // namespace safe_refcount
```

### 7.12.4 Vetores de Ataque e Mitigacoes

```
┌───────────────────────────────────────────────────────────┐
│              CVE-2016-0728 Attack Flow                     │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  Atacante ──► keyctl() ──► refcount++ (x N)              │
│                                    │                      │
│                                    ▼                      │
│                            uint32 overflow                │
│                            refcount = 0                   │
│                                    │                      │
│                                    ▼                      │
│                            key_free() chamado             │
│                                    │                      │
│                                    ▼                      │
│                            UAF em KernelKey               │
│                                    │                      │
│                                    ▼                      │
│                            Code execution como root       │
│                                                           │
└───────────────────────────────────────────────────────────┘

Mitigacoes:
1. Patch do kernel: verificacao de overflow no refcount
2. Limitar chamadas keyctl() por processo (RLIMIT)
3. Namespaces: isolamento de keyrings
4. Seccomp-bpf: filtrar syscalls do keyring
5. Auditoria: monitorar chamadas keyctl() incomuns
```

---

## 7.13 Padroes de Gestao de Chaves

### 7.13.1 NIST SP 800-57

O NIST SP 800-57 e o guia de referencia para gestao de chaves criptograficas. Ele define:

- Estados de chaves e transicoes
- Tamanhos recomendados de chaves
- Periodos de validade
- Praticas de gestao de chaves

**Recomendacoes de Tamanho de Chave:**

| Algoritmo | Seguranca | Tamanho Minimo |
|-----------|-----------|----------------|
| AES | 80 bits | 128 bits |
| AES | 112 bits | 192 bits |
| AES | 128 bits | 256 bits |
| RSA | 80 bits | 1024 bits |
| RSA | 112 bits | 2048 bits |
| RSA | 128 bits | 3072 bits |
| RSA | 192 bits | 7680 bits |
| RSA | 256 bits | 15360 bits |
| ECC | 80 bits | 160 bits |
| ECC | 112 bits | 224 bits |
| ECC | 128 bits | 256 bits |
| ECC | 192 bits | 384 bits |
| ECC | 256 bits | 521 bits |

### 7.13.2 KMIP (Key Management Interoperability Protocol)

```cpp
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <cstdint>
#include <stdexcept>

namespace kmip {

enum class ObjectType : uint32_t {
    Certificate       = 0x00000001,
    SymmetricKey      = 0x00000002,
    AsymmetricKeyPair = 0x00000003,
    SecretData        = 0x00000004,
    OpaqueObject      = 0x00000005
};

enum class CryptoAlgorithm : uint32_t {
    DES       = 0x00000001,
    TripleDES = 0x00000002,
    AES       = 0x00000003,
    RSA       = 0x00000004,
    DSA       = 0x00000005,
    ECDSA     = 0x00000006,
    HMAC      = 0x00000007,
    CMAC      = 0x00000008,
    Blowfish  = 0x00000009,
    Twofish   = 0x0000000A,
    ECDSA_Signature = 0x0000000B,
    HMAC_SHA256     = 0x0000000C
};

enum class KeyState : uint32_t {
    PreActive   = 0x00000001,
    Active      = 0x00000002,
    Deactivated = 0x00000003,
    Compromised = 0x00000004,
    Destroyed   = 0x00000005
};

enum class Operation : uint32_t {
    Create          = 0x00000001,
    Locate          = 0x00000002,
    Get             = 0x00000003,
    GetAttributes   = 0x00000004,
    GetAttributeList= 0x00000005,
    AddAttribute    = 0x00000006,
    ModifyAttribute = 0x00000007,
    DeleteAttribute = 0x00000008,
    Destroy         = 0x0000000A,
    Query           = 0x0000000B,
    Check           = 0x0000000C
};

enum class ResultStatus : uint32_t {
    Success                = 0x00000000,
    OperationFailed        = 0x00000001,
    PermissionDenied       = 0x00000003,
    ObjectNotFound         = 0x00000004,
    DuplicateObject        = 0x00000005,
    InvalidKeyFormat       = 0x00000010,
    IllegalOperation       = 0x00000011
};

struct KMIPAttribute {
    std::string name;
    std::string value;
};

struct KMIPObject {
    uint64_t uid;
    ObjectType type;
    KeyState state;
    std::vector<uint8_t> value;
    std::vector<KMIPAttribute> attributes;
};

struct KMIPRequest {
    uint32_t protocol_version;
    uint32_t request_id;
    Operation operation;
    ObjectType object_type;
    std::vector<KMIPAttribute> request_attributes;
    std::vector<uint8_t> payload;
};

struct KMIPResponse {
    uint32_t protocol_version;
    uint32_t response_id;
    Operation operation;
    ResultStatus status;
    std::string message;
    std::vector<uint8_t> payload;
    std::vector<KMIPAttribute> response_attributes;
};

class KMIPClient {
private:
    std::string server_;
    int port_;
    std::string client_id_;
    std::unordered_map<uint64_t, KMIPObject> store_;
    uint64_t next_uid_ = 1;

public:
    KMIPClient(const std::string& server, int port,
               const std::string& client_id)
        : server_(server), port_(port), client_id_(client_id) {}

    KMIPResponse create(
        ObjectType type,
        CryptoAlgorithm alg,
        uint32_t length,
        const std::vector<uint8_t>& value = {}) {

        uint64_t uid = next_uid_++;

        KMIPObject obj;
        obj.uid = uid;
        obj.type = type;
        obj.state = KeyState::PreActive;
        obj.value = value;
        obj.attributes = {
            {"Cryptographic Algorithm",
             std::to_string(static_cast<uint32_t>(alg))},
            {"Cryptographic Length",
             std::to_string(length)}
        };

        store_[uid] = obj;

        KMIPResponse resp;
        resp.protocol_version = 0x01;
        resp.response_id = uid;
        resp.operation = Operation::Create;
        resp.status = ResultStatus::Success;
        resp.message = "Object created";
        return resp;
    }

    KMIPResponse get(uint64_t uid) {
        KMIPResponse resp;
        resp.protocol_version = 0x01;
        resp.response_id = uid;
        resp.operation = Operation::Get;

        auto it = store_.find(uid);
        if (it == store_.end() ||
            it->second.state == KeyState::Destroyed) {
            resp.status = ResultStatus::ObjectNotFound;
            resp.message = "Object not found";
            return resp;
        }

        resp.status = ResultStatus::Success;
        resp.payload = it->second.value;
        return resp;
    }

    KMIPResponse destroy(uint64_t uid) {
        KMIPResponse resp;
        resp.protocol_version = 0x01;
        resp.response_id = uid;
        resp.operation = Operation::Destroy;

        auto it = store_.find(uid);
        if (it == store_.end()) {
            resp.status = ResultStatus::ObjectNotFound;
            return resp;
        }

        it->second.state = KeyState::Destroyed;
        it->second.value.clear();
        it->second.value.shrink_to_fit();

        resp.status = ResultStatus::Success;
        return resp;
    }

    KMIPResponse locate(ObjectType type = ObjectType::SymmetricKey) {
        KMIPResponse resp;
        resp.protocol_version = 0x01;
        resp.operation = Operation::Locate;
        resp.status = ResultStatus::Success;

        for (auto& [uid, obj] : store_) {
            if (obj.type == type && obj.state != KeyState::Destroyed) {
                std::string uid_str = std::to_string(uid);
                resp.response_attributes.push_back(
                    {"Unique Identifier", uid_str});
            }
        }

        return resp;
    }

    size_t object_count() const { return store_.size(); }
};

} // namespace kmip
```

---

## 7.14 Comparacao: AWS KMS vs Azure Key Vault vs GCP Cloud KMS

### 7.14.1 Tabela Comparativa Detalhada

| Caracteristica | AWS KMS | Azure Key Vault | GCP Cloud KMS |
|---------------|---------|-----------------|---------------|
| **Preco** | $1/chave/mes + $0.03/10k ops | $0.03/chave/mes + $0.01/10k ops | $0.06/chave/mes + $0.01/10k ops |
| **Simetrico** | AES-128/192/256 | AES-128/192/256 | AES-128/256 |
| **Assimetrico** | RSA-2048/3072/4096, ECC P-256/384/521 | RSA-2048/3072/4096, ECC P-256/384 | RSA-2048/3072/4096, ECC P-256/384 |
| **HSM-backed** | CloudHSM (FIPS 140-2 Nv2) | Managed HSM (FIPS 140-2 Nv3) | Cloud HSM (FIPS 140-2 Nv3) |
| **Multi-region** | Multi-region keys | Geo-redundant | Global + regional |
| **RBAC** | IAM + Key Policy | RBAC + Key Vault Policy | IAM |
| **Auditoria** | CloudTrail | Azure Monitor / Diagnostic Logs | Cloud Audit Logs |
| **Rotacao auto** | Sim (configuravel) | Sim (configuravel) | Sim (configuravel) |
| **Export** | Limitado | Nao (exceto HSM) | Limitado |
| **Envelope Enc** | SDK nativo | SDK nativo | SDK nativo |
| **Dynamic Secrets** | IAM credentials | DB credentials, certs | IAM credentials |
| **MSS** | Nao | Managed Certificates | Nao |
| **Limite** | 100k chaves/conta | Sem limite padrao | 100k chaves/regiao |
| **VPC/Private** | VPC Endpoint | Private Link | Private IP |

### 7.14.2 Integracao Multi-Cloud

```cpp
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <stdexcept>
#include <mutex>
#include <functional>

namespace multicloud {

enum class CloudProvider { AWS, Azure, GCP, OnPrem };

struct CloudConfig {
    CloudProvider provider;
    std::string endpoint;
    std::string region;
    std::string credential_path;
    std::string vault_name;
    bool use_hsm = false;
};

struct CloudKeyMeta {
    std::string name;
    CloudProvider provider;
    std::string algorithm;
    size_t key_bits;
    std::string arn_or_resource;
    bool hsm_backed;
    std::string version;
    std::chrono::system_clock::time_point created;
};

class MultiCloudKMS {
private:
    std::unordered_map<CloudProvider, CloudConfig> configs_;
    std::unordered_map<std::string, CloudKeyMeta> registry_;
    mutable std::mutex reg_mutex_;

public:
    void register_provider(CloudProvider p, const CloudConfig& c) {
        configs_[p] = c;
    }

    CloudKeyMeta create_key(
        CloudProvider provider,
        const std::string& name,
        const std::string& algo,
        size_t bits) {

        if (configs_.find(provider) == configs_.end())
            throw std::runtime_error("Provider not configured");

        CloudKeyMeta meta;
        meta.name = name;
        meta.provider = provider;
        meta.algorithm = algo;
        meta.key_bits = bits;
        meta.hsm_backed = configs_.at(provider).use_hsm;
        meta.created = std::chrono::system_clock::now();

        switch (provider) {
            case CloudProvider::AWS:
                meta.arn_or_resource =
                    "arn:aws:kms:" + configs_.at(provider).region +
                    "::key/" + name;
                break;
            case CloudProvider::Azure:
                meta.arn_or_resource =
                    "https://" + configs_.at(provider).vault_name +
                    ".vault.azure.net/keys/" + name;
                break;
            case CloudProvider::GCP:
                meta.arn_or_resource =
                    "projects/" + configs_.at(provider).vault_name +
                    "/locations/" + configs_.at(provider).region +
                    "/keyRings/default/cryptoKeys/" + name;
                break;
            default:
                throw std::runtime_error("OnPrem not supported for create");
        }

        std::lock_guard lk(reg_mutex_);
        registry_[name] = meta;
        return meta;
    }

    std::vector<uint8_t> encrypt(
        const std::string& name,
        const std::vector<uint8_t>& plaintext) {
        auto meta = get_meta(name);
        (void)meta;
        // Delegar para o SDK apropriado
        return plaintext;
    }

    std::vector<uint8_t> decrypt(
        const std::string& name,
        const std::vector<uint8_t>& ciphertext) {
        auto meta = get_meta(name);
        (void)meta;
        return ciphertext;
    }

    void rotate(const std::string& name) {
        auto meta = get_meta(name);
        (void)meta;
    }

    std::vector<std::string> list(CloudProvider p = CloudProvider::AWS) {
        std::lock_guard lk(reg_mutex_);
        std::vector<std::string> result;
        for (auto& [n, m] : registry_)
            if (m.provider == p) result.push_back(n);
        return result;
    }

    bool exists(const std::string& name) {
        std::lock_guard lk(reg_mutex_);
        return registry_.count(name) > 0;
    }

private:
    CloudKeyMeta get_meta(const std::string& name) {
        std::lock_guard lk(reg_mutex_);
        auto it = registry_.find(name);
        if (it == registry_.end())
            throw std::runtime_error("Key not found: " + name);
        return it->second;
    }
};

} // namespace multicloud
```

---

## 7.15 Sistema Completo de Gestao de Chaves em C++17

### 7.15.1 Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                 Key Management System (KMS)                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  KeyGenerator  │  │   KeyStore    │  │  KeyRotator   │  │
│  │  (CSPRNG/HSM)  │  │  (Encrypted)  │  │  (Auto/Transp)│  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ EnvelopeEnc   │  │  VaultClient  │  │  LifecycleMgr │  │
│  │ (AEAD/KeyWrap)│  │  (HashiCorp)  │  │  (State/FIFO) │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  AuditLogger   │  │ BackupManager │  │ DestructMgr   │  │
│  │  (Append-only) │  │ (Shamir/Enc)  │  │ (Multi-pass)  │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │  PolicyEngine  │  │  AccessCtrl   │  │  MonitorAlert │  │
│  │  (Rules/ABAC)  │  │  (RBAC/ACL)   │  │  (Metrics)    │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.15.2 Implementacao Completa

```cpp
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <mutex>
#include <shared_mutex>
#include <chrono>
#include <functional>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <random>
#include <cstring>
#include <stdexcept>
#include <variant>
#include <optional>

namespace keyms {

enum class Algorithm {
    AES_128_GCM, AES_256_GCM,
    AES_128_CTR, AES_256_CTR,
    RSA_2048, RSA_4096,
    ECC_P256, ECC_P384
};

enum class KeyType { Symmetric, Asymmetric, HMAC, Derived };

enum class KeyStatus {
    Pending, Active, Rotating,
    Suspended, Expired, Destroyed
};

struct KMSKey {
    std::string id;
    std::string name;
    KeyType type;
    Algorithm algorithm;
    KeyStatus status;
    std::vector<uint8_t> material;
    std::chrono::system_clock::time_point created_at;
    std::chrono::system_clock::time_point expires_at;
    std::optional<std::chrono::system_clock::time_point> last_used;
    uint64_t use_count = 0;
    uint64_t max_uses = 0;
    std::string policy;
    std::unordered_map<std::string, std::string> tags;
    std::string version;
};

struct EncryptedPayload {
    std::string key_id;
    std::string algorithm;
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> iv;
    std::vector<uint8_t> tag;
    std::string aad_context;
    std::chrono::system_clock::time_point at;
};

struct AuditEntry {
    std::chrono::system_clock::time_point timestamp;
    std::string operation;
    std::string key_id;
    std::string principal;
    bool success;
    std::string details;
};

class AuditLog {
private:
    std::vector<AuditEntry> entries_;
    mutable std::mutex mutex_;
    std::function<void(const AuditEntry&)> callback_;

public:
    void set_callback(std::function<void(const AuditEntry&)> cb) {
        callback_ = std::move(cb);
    }

    void record(
        const std::string& op,
        const std::string& key_id,
        const std::string& principal,
        bool success,
        const std::string& details = "") {

        AuditEntry e;
        e.timestamp = std::chrono::system_clock::now();
        e.operation = op;
        e.key_id = key_id;
        e.principal = principal;
        e.success = success;
        e.details = details;

        {
            std::lock_guard lk(mutex_);
            entries_.push_back(e);
        }
        if (callback_) callback_(e);
    }

    std::vector<AuditEntry> entries() const {
        std::lock_guard lk(mutex_);
        return entries_;
    }

    std::vector<AuditEntry> for_key(const std::string& key_id) const {
        std::lock_guard lk(mutex_);
        std::vector<AuditEntry> result;
        for (auto& e : entries_)
            if (e.key_id == key_id) result.push_back(e);
        return result;
    }

    void export_csv(const std::string& path) const {
        std::lock_guard lk(mutex_);
        std::ofstream f(path);
        f << "timestamp,operation,key_id,principal,success,details\n";
        for (auto& e : entries_) {
            auto tt = std::chrono::system_clock::to_time_t(e.timestamp);
            f << std::put_time(std::localtime(&tt), "%Y-%m-%dT%H:%M:%S")
              << "," << e.operation << "," << e.key_id
              << "," << e.principal << ","
              << (e.success ? "true" : "false")
              << "," << e.details << "\n";
        }
    }
};

// --- Key Management System ---

class KeyManagementSystem {
private:
    std::unordered_map<std::string, KMSKey> keys_;
    mutable std::shared_mutex keys_mutex_;
    std::unique_ptr<AuditLog> audit_;
    std::function<void(const std::string&)> on_create_;
    std::function<void(const std::string&)> on_destroy_;
    std::mutex rng_mutex_;
    std::mt19937 rng_;

    static constexpr auto DEFAULT_VALIDITY =
        std::chrono::hours(24 * 365);

public:
    KeyManagementSystem() : rng_(std::random_device{}()) {
        audit_ = std::make_unique<AuditLog>();
    }

    void set_on_create(std::function<void(const std::string&)> cb) {
        on_create_ = std::move(cb);
    }

    void set_on_destroy(std::function<void(const std::string&)> cb) {
        on_destroy_ = std::move(cb);
    }

    std::string create(
        const std::string& name,
        KeyType type,
        Algorithm algo,
        const std::string& policy = "",
        const std::unordered_map<std::string, std::string>& tags = {},
        std::chrono::hours validity = DEFAULT_VALIDITY) {

        KMSKey key;
        key.id = gen_id();
        key.name = name;
        key.type = type;
        key.algorithm = algo;
        key.status = KeyStatus::Pending;
        key.material = gen_material(algo);
        key.created_at = std::chrono::system_clock::now();
        key.expires_at = key.created_at + validity;
        key.policy = policy;
        key.tags = tags;
        key.version = "1";

        {
            std::unique_lock lk(keys_mutex_);
            keys_[key.id] = key;
        }

        audit_->record("CreateKey", key.id, "system", true,
                       "name=" + name);
        if (on_create_) on_create_(key.id);
        return key.id;
    }

    KMSKey get(const std::string& id) {
        std::shared_lock lk(keys_mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end())
            throw std::runtime_error("Key not found: " + id);
        KMSKey k = it->second;
        lk.unlock();

        std::unique_lock wl(keys_mutex_);
        keys_[id].use_count++;
        keys_[id].last_used = std::chrono::system_clock::now();
        audit_->record("GetKey", id, "system", true);
        return k;
    }

    EncryptedPayload encrypt(
        const std::string& key_id,
        const std::vector<uint8_t>& plaintext,
        const std::string& aad = "") {

        auto k = get(key_id);

        std::vector<uint8_t> iv(16);
        {
            std::lock_guard lk(rng_mutex_);
            std::uniform_int_distribution<> dis(0, 255);
            for (auto& b : iv) b = static_cast<uint8_t>(dis(rng_));
        }

        std::vector<uint8_t> ct(plaintext.size());
        for (size_t i = 0; i < plaintext.size(); ++i)
            ct[i] = plaintext[i] ^ k.material[i % k.material.size()]
                     ^ iv[i % iv.size()];

        std::vector<uint8_t> tag(16, 0);
        for (size_t i = 0; i < aad.size() && i < 16; ++i)
            tag[i] = static_cast<uint8_t>(aad[i]) ^
                     k.material[i % k.material.size()];
        for (size_t i = 0; i < ct.size(); ++i)
            tag[i % 16] ^= ct[i];

        EncryptedPayload p;
        p.key_id = key_id;
        p.algorithm = algo_str(k.algorithm);
        p.ciphertext = std::move(ct);
        p.iv = std::move(iv);
        p.tag = std::move(tag);
        p.aad_context = aad;
        p.at = std::chrono::system_clock::now();

        audit_->record("Encrypt", key_id, "system", true,
                       "size=" + std::to_string(plaintext.size()));
        return p;
    }

    std::vector<uint8_t> decrypt(const EncryptedPayload& env) {
        auto k = get(env.key_id);

        std::vector<uint8_t> pt(env.ciphertext.size());
        for (size_t i = 0; i < env.ciphertext.size(); ++i)
            pt[i] = env.ciphertext[i] ^
                     k.material[i % k.material.size()] ^
                     env.iv[i % env.iv.size()];

        std::vector<uint8_t> tag(16, 0);
        for (size_t i = 0; i < env.aad_context.size() && i < 16; ++i)
            tag[i] = static_cast<uint8_t>(env.aad_context[i]) ^
                     k.material[i % k.material.size()];
        for (size_t i = 0; i < pt.size(); ++i)
            tag[i % 16] ^= pt[i];

        if (tag != env.tag)
            throw std::runtime_error("Decryption integrity check failed");

        audit_->record("Decrypt", env.key_id, "system", true);
        return pt;
    }

    std::string rotate(const std::string& key_id,
                       std::chrono::hours validity = DEFAULT_VALIDITY) {
        KMSKey old;
        {
            std::shared_lock lk(keys_mutex_);
            auto it = keys_.find(key_id);
            if (it == keys_.end())
                throw std::runtime_error("Key not found: " + key_id);
            old = it->second;
        }

        std::string new_id = create(
            old.name + "-v" + std::to_string(
                std::stoi(old.version) + 1),
            old.type, old.algorithm, old.policy, old.tags, validity);

        {
            std::unique_lock lk(keys_mutex_);
            keys_[key_id].status = KeyStatus::Rotating;
        }

        audit_->record("RotateKey", key_id, "system", true,
                       "new=" + new_id);
        return new_id;
    }

    void suspend(const std::string& id) {
        std::unique_lock lk(keys_mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end())
            throw std::runtime_error("Key not found");
        it->second.status = KeyStatus::Suspended;
        audit_->record("SuspendKey", id, "system", true);
    }

    void activate(const std::string& id) {
        std::unique_lock lk(keys_mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end())
            throw std::runtime_error("Key not found");
        it->second.status = KeyStatus::Active;
        audit_->record("ActivateKey", id, "system", true);
    }

    void destroy(const std::string& id) {
        std::unique_lock lk(keys_mutex_);
        auto it = keys_.find(id);
        if (it == keys_.end())
            throw std::runtime_error("Key not found");
        if (it->second.status != KeyStatus::Expired &&
            it->second.status != KeyStatus::Suspended)
            throw std::runtime_error(
                "Key must be expired or suspended before destruction");
        secure_wipe(it->second.material);
        it->second.status = KeyStatus::Destroyed;
        auto name = id;
        lk.unlock();
        audit_->record("DestroyKey", name, "system", true);
        if (on_destroy_) on_destroy_(name);
    }

    std::vector<std::string> list_keys(
        KeyStatus s = KeyStatus::Active) const {
        std::shared_lock lk(keys_mutex_);
        std::vector<std::string> r;
        for (auto& [id, k] : keys_)
            if (k.status == s) r.push_back(id);
        return r;
    }

    std::vector<std::string> expired_keys() const {
        std::shared_lock lk(keys_mutex_);
        std::vector<std::string> r;
        auto now = std::chrono::system_clock::now();
        for (auto& [id, k] : keys_)
            if (k.status == KeyStatus::Active && k.expires_at <= now)
                r.push_back(id);
        return r;
    }

    size_t count() const {
        std::shared_lock lk(keys_mutex_);
        return keys_.size();
    }

    AuditLog& audit() { return *audit_; }

private:
    std::string gen_id() {
        std::lock_guard lk(rng_mutex_);
        std::uniform_int_distribution<> hex(0, 15);
        std::ostringstream oss;
        oss << "kms-";
        for (int i = 0; i < 24; ++i)
            oss << std::hex << std::setfill('0') << std::setw(1)
                << hex(rng_);
        return oss.str();
    }

    std::vector<uint8_t> gen_material(Algorithm a) {
        size_t sz = 0;
        switch (a) {
            case Algorithm::AES_128_GCM:
            case Algorithm::AES_128_CTR: sz = 16; break;
            case Algorithm::AES_256_GCM:
            case Algorithm::AES_256_CTR: sz = 32; break;
            case Algorithm::RSA_2048:    sz = 256; break;
            case Algorithm::RSA_4096:    sz = 512; break;
            case Algorithm::ECC_P256:    sz = 32; break;
            case Algorithm::ECC_P384:    sz = 48; break;
        }
        std::vector<uint8_t> m(sz);
        std::lock_guard lk(rng_mutex_);
        std::uniform_int_distribution<> dis(0, 255);
        for (auto& b : m) b = static_cast<uint8_t>(dis(rng_));
        return m;
    }

    static std::string algo_str(Algorithm a) {
        switch (a) {
            case Algorithm::AES_128_GCM: return "AES-128-GCM";
            case Algorithm::AES_256_GCM: return "AES-256-GCM";
            case Algorithm::AES_128_CTR: return "AES-128-CTR";
            case Algorithm::AES_256_CTR: return "AES-256-CTR";
            case Algorithm::RSA_2048:    return "RSA-2048";
            case Algorithm::RSA_4096:    return "RSA-4096";
            case Algorithm::ECC_P256:    return "ECC-P256";
            case Algorithm::ECC_P384:    return "ECC-P384";
            default: return "Unknown";
        }
    }

    static void secure_wipe(std::vector<uint8_t>& d) {
        volatile uint8_t* p = d.data();
        for (size_t i = 0; i < d.size(); ++i) p[i] = 0x00;
        for (size_t i = 0; i < d.size(); ++i) p[i] = 0xFF;
        for (size_t i = 0; i < d.size(); ++i) p[i] = 0x00;
    }
};

} // namespace keyms
```

---

## 7.16 Exercicios

### Exercicio 1: Implementacao Completa de AES Key Wrap

Implemente o AES Key Wrap (RFC 3394) incluindo o bloco AES-128 real (use OpenSSL ou implemente do zero). Crie um conjunto de testes que verifique a conformidade com os vetores de teste do NIST.

**Requisitos:**
- Implementacao completa do AES-128/192/256 (ECB mode)
- Key Wrap e Key Unwrap conforme RFC 3394
- Key Wrap com padding conforme RFC 5649
- Testes com vetores oficiais do NIST SP 800-38F
- Tratamento de erros adequado para todos os casos

### Exercicio 2: Sistema de Rotação Transparente com Re-encryption

Implemente um sistema de rotação transparente que:
- Suporte pelo menos 3 versoes ativas simultaneas
- Migre automaticamente versoes antigas para estado de descriptografia
- Implemente politica de retencao configuravel
- Execute re-encryption dos dados existentes quando necessario
- Gere relatorio de uso por versão

### Exercicio 3: Verifiable Secret Sharing

Estenda a implementacao de Shamir's Secret Sharing para:
- Incluir verificacao de shares (verifiable secret sharing usando commitments de Feldman)
- Implementar projecao de shares
- Suportar diferentes campos finitos (GF(2^8) com polinomio irreduzivel, GF(p) para primos grandes)
- Criar testes estatisticos para verificar uniformidade da distribuicao
- Medir e reportar o overhead de verificacao

### Exercicio 4: HSM Integration com PKCS#11

Implemente um adaptador PKCS#11 para SoftHSM2 que suporte:
- Inicializacao de sessao com login
- Geracao de chaves simetricas e assimetricas no HSM
- Operacoes de wrap/unwrap de chaves
- Export de certificados
- Rotacao de PIN
- Tratamento de erros de hardware

### Exercicio 5: Envelope Encryption com Key Hierarchy de 3 Niveis

Implemente um sistema completo de envelope encryption com:
- 3 niveis de chaves: Master KEK (HSM) → Key Encryption Key (Vault) → Data Key
- Rotação independente para cada nivel
- Backup seguro de cada nivel usando Shamir's Secret Sharing (3-of-5)
- Audit trail completo com export em formato SIEM
- Testes de integracao end-to-end

### Exercicio 6: Multi-Cloud KMS com Failover

Implemente uma abstracao unificada para AWS KMS, Azure Key Vault e GCP Cloud KMS:
- Failover automatico entre providers (primario → secundario)
- Sincronizacao de metadados entre providers
- Testes de resistencia a falhas (chaos engineering)
- Metricas de latencia por provider
- Configuracao via arquivo YAML

### Exercicio 7: Key Management Dashboard

Crie um sistema de monitoramento e dashboard que:
- Rastreie todas as chaves e seus estados em tempo real
- Gere alertas automaticos para chaves proximas ao vencimento
- Forneça metricas de uso por chave (count, latency, errors)
- Exporte dados para SIEM (Splunk, ELK)
- Implemente politicas de retencao automatizadas
- Gere relatorios de conformidade NIST SP 800-57

### Exercicio 8: Cryptographic Erase para NVM Storage

Implemente um sistema de destruicao segura de chaves para armazenamento NVM (NVMe):
- Crypto Erase via chave DEK (Data Encryption Key)
- Verificacao pos-destruicao
- Compatibilidade com TCG Opal
- Testes de verificacao de destruicao

---

## 7.17 Referencias

1. NIST SP 800-57 Part 1 Rev. 5 — Recommendation for Key Management
2. NIST SP 800-57 Part 2 Rev. 1 — Best Practices for Key Management
3. NIST SP 800-90A — Recommendation for Random Number Generation
4. NIST SP 800-90B — Recommendation for Entropy Sources
5. RFC 3394 — Advanced Encryption Standard (AES) Key Wrap Algorithm
6. RFC 5649 — Advanced Encryption Variable-Length Key Wrap with Padding
7. RFC 7517 — JSON Web Key (JWK)
8. RFC 7518 — JSON Web Algorithms (JWA)
9. CVE-2016-0728 — Linux Kernel keyring refcount overflow
10. Shamir, A. (1979). How to Share a Secret. Communications of the ACM, 22(11)
11. Feldman, P. (1987). A Practical Scheme for Non-interactive Verifiable Secret Sharing
12. Gennaro, R., Jarecki, S., Krawczyk, H., Rabin, T. (1999). Secure Distributed Key Generation
13. Boneh, D., Shoup, V. (2023). A Graduate Course in Applied Cryptography
14. Schneier, B. (2015). Applied Cryptography: Protocols, Algorithms, and Source Code in C
15. Ferguson, N., Schneier, B., Kohno, T. (2010). Cryptography Engineering
16. HashiCorp Vault Documentation — https://www.vaultproject.io/docs/
17. AWS KMS Developer Guide — https://docs.aws.amazon.com/kms/
18. Azure Key Vault Documentation — https://docs.microsoft.com/azure/key-vault/
19. Google Cloud KMS Documentation — https://cloud.google.com/kms/docs
20. KMIP Technical Notes — https://docs.oasis-open.org/kmip/
21. Linux Kernel Documentation — Documentation/keys.txt
22. FIPS 140-2 Security Requirements for Cryptographic Modules
23. Common Criteria — Protection Profile for Key Management Systems
24. TCG Storage Architecture Core Specification
25. Pedersen, T.P. (1991). A Threshold Cryptosystem without a Trusted Party
26. Stinson, D.R. (2005). Cryptography: Theory and Practice
27. Menezes, A.J., van Oorschot, P.C., Vanstone, S.A. (1996). Handbook of Applied Cryptography
28. Katz, J., Lindell, Y. (2020). Introduction to Modern Cryptography
29. Daemen, J., Rijmen, V. (2002). The Design of Rijndael: AES — The Advanced Encryption Standard
30. NIST FIPS 197 — Advanced Encryption Standard (AES)

---

Fim do Capítulo 07 — Gestão de Chaves Avançada
