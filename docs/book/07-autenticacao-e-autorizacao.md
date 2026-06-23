---
layout: default
title: "07-autenticacao-e-autorizacao"
---

# Capítulo 7 — Autenticação e Autorização

> "A cadeia de segurança do seu sistema é tão forte quanto seu elo mais fraco. E frequentemente, esse elo é a autenticação."

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Implementar hashing de senhas robusto** usando Argon2id, bcrypt e scrypt em C++17, compreendendo por que algoritmos como MD5, SHA-1 e SHA-256 são inadequados para proteger senhas.
2. **Projetar e implementar autenticação multi-fator (MFA/2FA)** incluindo TOTP (RFC 6238), HOTP e integração com FIDO2/WebAuthn.
3. **Gerenciar sessões e tokens JWT** com segurança, incluindo proteção contra ataques de confusão de algoritmo ('none' algorithm), rotação de chaves e revogação de tokens.
4. **Implementar modelos de autorização** como RBAC e ABAC em C++17, com motor de avaliação de permissões e logging de auditoria.
5. **Projetar um servidor de autenticação completo** que integre registro de usuários, login com verificação, MFA, sessões JWT e middleware de autorização.

---

## 7.1 Autenticação: Fundamentos

Autenticação é o processo de verificar a identidade de um indivíduo, dispositivo ou entidade. É a primeira linha de defesa em qualquer sistema de segurança. Antes de autorizar qualquer ação, o sistema deve confirmar: **quem está pedindo?**

### 7.1.1 Fatores de Autenticação

Tradicionalmente, os fatores de autenticação são divididos em três categorias:

| Fator | Descrição | Exemplos |
|-------|-----------|----------|
| **Algo que você sabe** | Conhecimento secreto compartilhado | Senhas, PINs, respostas a perguntas secretas |
| **Algo que você possui** | Objeto físico ou digital | Token de hardware, smartphone, smart card, chave USB |
| **Algo que você é** | Característica biométrica digital | Impressão digital, reconhecimento facial, íris |

A autenticação de dois fatores (2FA) combina dois desses fatores, significativamente aumentando a dificuldade para um atacante comprometer uma conta.

### 7.1.2 Autenticação vs. Autorização

É comum confundir os dois conceitos, mas são processos distintos:

- **Autenticação** responde: "Quem é você?" — Verificação de identidade.
- **Autorização** responde: "O que você pode fazer?" — Controle de acesso baseado na identidade já estabelecida.

Um sistema pode ter uma autenticação perfeita mas uma autorização falha, permitindo que um usuário autenticado acesse recursos além do seu escopo.

### 7.1.3 Vulnerabilidades Comuns em Autenticação

As falhas de autenticação estão consistentemente no top 10 do OWASP:

1. **Força bruta** — Tentativas automatizadas de adivinhar senhas.
2. **Credential stuffing** — Uso de credenciais vazadas de outros serviços.
3. **Session fixation** — Atacante define um ID de sessão antes do login.
4. **Credential leakage** — Senhas em logs, URLs, ou memória não protegida.
5. **Weak password policies** — Senhas curtas ou sem complexidade.
6. **Missing MFA** — Contas protegidas apenas por senha.

### 7.1.4 Padrões de Arquitetura de Autenticação

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Cliente    │────▶│  Gateway/    │────▶│  Serviço de    │
│              │     │  Proxy       │     │  Autenticação  │
└─────────────┘     └──────────────┘     └───────┬────────┘
                                                  │
                                    ┌─────────────┴─────────────┐
                                    │                           │
                              ┌─────▼─────┐             ┌───────▼───────┐
                              │  Banco de  │             │  Serviço de   │
                              │  Dados     │             │  Autorização  │
                              │  (senhas)  │             │  (permissões) │
                              └───────────┘             └───────────────┘
```

### 7.1.5 Estudo de Caso: Adobe Password Breach (2013)

Em 2013, a Adobe sofreu um vazamento de dados que expôs **153 milhões de contas** de usuários. O dado mais alarmante não foi apenas a escala, mas a **forma como as senhas foram armazenadas**.

**O que deu errado:** A Adobe usou **3DES em modo ECB (Electronic Codebook)** para criptografar senhas. ECB é um modo de operação que não usa IV (Initialization Vector) e processa cada bloco de 64 bits independentemente. Isso significa que senhas idênticas produzem o mesmo texto cifrado, permitindo ataques de rainbow table e análise de frequência.

```cpp
// VULNERÁVEL: Padrão Adobe 2013 - 3DES em modo ECB
// NÃO USE ESTE CÓDIGO
#include <openssl/des.h>
#include <openssl/rand.h>
#include <string>
#include <vector>

class AdobePasswordHasher {
public:
    std::vector<unsigned char> hashPassword(const std::string& password) {
        // Problema 1: 3DES não é um algoritmo de hashing de senhas
        // Problema 2: ECB não usa IV — senhas iguais produzem saídas iguais
        // Problema 3: Sem salt — rainbow tables são eficazes
        
        DES_cblock key1, key2, key3;
        DES_key_schedule ks1, ks2, ks3;
        
        // Chaves fixas (outro problema enorme)
        unsigned char fixedKey1[8] = {0xC0,0x16,0x12,0xEC,0x22,0xAB,0xBC,0x11};
        unsigned char fixedKey2[8] = {0x32,0x45,0x67,0x89,0xAB,0xCD,0xEF,0x01};
        unsigned char fixedKey3[8] = {0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88};
        
        memcpy(key1, fixedKey1, 8);
        memcpy(key2, fixedKey2, 8);
        memcpy(key3, fixedKey3, 8);
        
        DES_set_key(&key1, &ks1);
        DES_set_key(&key2, &ks2);
        DES_set_key(&key3, &ks3);
        
        std::vector<unsigned char> padded(8 * ((password.size() / 8) + 1), 0);
        memcpy(padded.data(), password.data(), password.size());
        
        std::vector<unsigned char> ciphertext(padded.size());
        
        for (size_t i = 0; i < padded.size(); i += 8) {
            DES_ecb3_encrypt(
                reinterpret_cast<DES_cblock*>(padded.data() + i),
                reinterpret_cast<DES_cblock*>(ciphertext.data() + i),
                &ks1, &ks2, &ks3, DES_ENCRYPT
            );
        }
        
        return ciphertext;
    }
};
```

**A lição:** Criptografia NÃO é hashing de senhas. 3DES com chave fixa e modo ECB é uma combinação devastadoramente insegura. O correto é usar algoritmos de hashing de senhas como Argon2id, bcrypt ou scrypt — que veremos na próxima seção.

---

## 7.2 Password Hashing Seguro

### 7.2.1 Por que MD5/SHA-1/SHA-256 NÃO são hashes de senhas

Algoritmos como MD5, SHA-1 e SHA-256 são **funções de hash criptográficas**, não **funções de hashing de senhas**. A distinção é fundamental:

| Característica | Hash Criptográfico | Hash de Senha |
|----------------|-------------------|---------------|
| Velocidade | O mais rápido possível | Intencionalmente lento |
| Resistência a GPU | Baixa (GPU acelera massivamente) | Alta (memória intencionalmente usada) |
| Salt incorporado | Não | Sim |
| Parâmetros ajustáveis | Não | Sim |
| Propósito | Verificação de integridade | Proteção contra força bruta |

SHA-256 pode calcular **bilhões** de hashes por segundo em uma GPU moderna. Isso permite que um atacante teste centenas de bilhões de senhas comuns por dia.

```cpp
// VULNERÁVEL: SHA-256 para hashing de senhas
// Um atacante pode testar ~10 bilhões de senhas/s em uma RTX 4090
#include <openssl/sha.h>
#include <string>
#include <array>

class VulnerablePasswordHasher {
public:
    std::string hash(const std::string& password) {
        // Problema 1: SHA-256 é rápido demais
        // Problema 2: Sem salt — rainbow tables eficazes
        // Problema 3: Sem work factor — impossível ajustar ao hardware
        
        unsigned char hash[SHA256_DIGEST_LENGTH];
        SHA256(reinterpret_cast<const unsigned char*>(password.data()),
               password.size(), hash);
        
        // Conversão para hexadecimal
        std::string result;
        result.reserve(SHA256_DIGEST_LENGTH * 2);
        for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", hash[i]);
            result += buf;
        }
        return result;
    }
};
```

### 7.2.2 Argon2id: O Padrão Recomendado

Argon2id é o vencedor do Password Hashing Competition (2015) e é atualmente o algoritmo recomendado para hashing de senhas. Ele combina as melhores características de Argon2i (resistente a ataques de canal lateral) e Argon2d (resistente a ataques GPU/ASIC).

Parâmetros principais:
- **Memory cost (m)** — Quantidade de memória usada em KB.
- **Time cost (t)** — Número de iterações.
- **Parallelism (p)** — Número de threads paralelas.

### 7.2.3 Implementação Completa com libsodium

```cpp
// Seguro: Argon2id via libsodium para hashing de senhas
#include <sodium.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstring>
#include <array>
#include <sys/mman.h>

class SecurePasswordHasher {
public:
    static constexpr size_t SALT_BYTES = crypto_pwhash_SALTBYTES;
    static constexpr size_t STRBYTES = crypto_pwhash_STRBYTES;

    SecurePasswordHasher() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    // Gera salt aleatório criptograficamente seguro
    std::array<unsigned char, SALT_BYTES> generateSalt() {
        std::array<unsigned char, SALT_BYTES> salt;
        randombytes_buf(salt.data(), SALT_BYTES);
        return salt;
    }

    // Hash de senha com Argon2id
    // Retorna string codificada que inclui algoritmo, parâmetros, salt e hash
    std::string hashPassword(const std::string& password,
                             unsigned long long opslimit = crypto_pwhash_OPSLIMIT_SENSITIVE,
                             size_t memlimit = crypto_pwhash_MEMLIMIT_SENSITIVE) {
        std::array<char, STRBYTES> encoded;
        
        if (crypto_pwhash_str_encoded(
                encoded.data(),
                password.c_str(),
                password.size(),
                opslimit,
                memlimit) != 0) {
            throw std::runtime_error("Password hashing failed");
        }
        
        return std::string(encoded.data());
    }

    // Verificação de senha com comparação de tempo constante
    bool verifyPassword(const std::string& password,
                        const std::string& storedHash) {
        // crypto_pwhash_str_verify internamente usa comparação de tempo constante
        return crypto_pwhash_str_verify(
            storedHash.c_str(),
            password.c_str(),
            password.size()) == 0;
    }

    // Hash com salt explícito (para controle manual dos parâmetros)
    std::vector<unsigned char> hashWithSalt(
            const std::string& password,
            const unsigned char* salt,
            size_t hashBytes = crypto_pwhash_BYTES,
            unsigned long long opslimit = crypto_pwhash_OPSLIMIT_SENSITIVE,
            size_t memlimit = crypto_pwhash_MEMLIMIT_SENSITIVE) {
        
        std::vector<unsigned char> hash(hashBytes);
        
        if (crypto_pwhash(
                hash.data(),
                hashBytes,
                password.c_str(),
                password.size(),
                salt,
                opslimit,
                memlimit,
                crypto_pwhash_ALG_ARGON2ID13) != 0) {
            throw std::runtime_error("Password hashing failed");
        }
        
        return hash;
    }
};

// Exemplo de uso
void example_password_hashing() {
    SecurePasswordHasher hasher;
    
    std::string password = "MyStr0ng!P@ssw0rd#2024";
    
    // Hash da senha
    std::string hashed = hasher.hashPassword(password);
    std::cout << "Hashed password: " << hashed << std::endl;
    
    // Verificação
    bool valid = hasher.verifyPassword(password, hashed);
    std::cout << "Password valid: " << (valid ? "yes" : "no") << std::endl;
    
    // Senha incorreta
    bool invalid = hasher.verifyPassword("wrongpassword", hashed);
    std::cout << "Wrong password valid: " << (invalid ? "yes" : "no") << std::endl;
}
```

### 7.2.4 bcrypt: O Clássico Confiável

```cpp
#include <sodium.h>
#include <string>
#include <stdexcept>
#include <cstring>

class BcryptHasher {
public:
    static constexpr size_t SALTBYTES = 16;
    static constexpr size_t HASHBYTES = 32;

    std::string hashPassword(const std::string& password, int logRounds = 12) {
        std::array<unsigned char, SALTBYTES> salt;
        randombytes_buf(salt.data(), SALTBYTES);
        
        // libsodium oferece crypto_pwhash via argon2
        // Para bcrypt real, use biblioteca específica ou implemente manualmente
        // Aqui demonstramos o padrão de uso
        
        std::vector<unsigned char> hash(crypto_pwhash_BYTES);
        
        if (crypto_pwhash(
                hash.data(), hash.size(),
                password.c_str(), password.size(),
                salt.data(),
                static_cast<unsigned long long>(1) << logRounds,  // 2^logRounds ops
                128 * 1024,  // 128 MB de memória
                crypto_pwhash_ALG_ARGON2ID13) != 0) {
            throw std::runtime_error("Hashing failed");
        }
        
        // Formatação: $argon2id$v=19$m=131072,t=4096,p=1$salt$hash
        return formatEncoded(salt.data(), hash.data(), logRounds);
    }

    bool verifyPassword(const std::string& password, const std::string& stored) {
        // Decodificar stored, extrair salt e parâmetros
        // Recalcular hash com mesmos parâmetros
        // Comparar em tempo constante
        
        // Simplificação para demonstração:
        auto decoded = parseStored(stored);
        auto computed = hashWithParams(password, decoded.salt, decoded.rounds);
        
        return sodium_memcmp(computed.data(), decoded.hash.data(),
                            computed.size()) == 0;
    }

private:
    struct DecodedHash {
        std::vector<unsigned char> salt;
        std::vector<unsigned char> hash;
        int rounds;
    };

    std::string formatEncoded(const unsigned char* salt,
                               const unsigned char* hash,
                               int rounds) {
        // Formato simplificado — produção deve seguir formato bcrypt completo
        std::string result = "$2b$";
        result += std::to_string(rounds) + "$";
        
        // Codificar salt e hash em base64
        char saltB64[32];
        char hashB64[48];
        size_t saltB64Len, hashB64Len;
        
        sodium_bin2base64(saltB64, sizeof(saltB64),
                         salt, 16, sodium_base64_VARIANT_ORIGINAL);
        sodium_bin2base64(hashB64, sizeof(hashB64),
                         hash, 32, sodium_base64_VARIANT_ORIGINAL);
        
        result += saltB64;
        result += "$";
        result += hashB64;
        
        return result;
    }

    std::vector<unsigned char> hashWithParams(const std::string& password,
                                               const unsigned char* salt,
                                               int rounds) {
        std::vector<unsigned char> hash(32);
        crypto_pwhash(
            hash.data(), hash.size(),
            password.c_str(), password.size(),
            salt,
            static_cast<unsigned long long>(1) << rounds,
            128 * 1024,
            crypto_pwhash_ALG_ARGON2ID13);
        return hash;
    }

    DecodedHash parseStored(const std::string& stored) {
        DecodedHash decoded;
        // Parse do formato armazenado (simplificado)
        decoded.rounds = 12;
        decoded.salt.resize(16);
        decoded.hash.resize(32);
        randombytes_buf(decoded.salt.data(), 16);
        return decoded;
    }
};
```

### 7.2.5 Aparência de Memória Segura para Senhas

Quando senhas estão em memória, elas devem ser protegidas contra swap e dumps de memória:

```cpp
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
#include <string>
#include <stdexcept>
#include <vector>

class SecurePasswordMemory {
public:
    SecurePasswordMemory(size_t capacity) 
        : capacity_(capacity), locked_(true) {
        
        // Alocar memória não-swapável
        buffer_ = static_cast<char*>(mmap(
            nullptr, capacity_,
            PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS,
            -1, 0));
        
        if (buffer_ == MAP_FAILED) {
            throw std::runtime_error("mmap failed");
        }
        
        // Travar na memória física (impede swap para disco)
        if (mlock(buffer_, capacity_) != 0) {
            munmap(buffer_, capacity_);
            throw std::runtime_error("mlock failed");
        }
        
        // Mascarar da leitura de /proc/self/maps
        madvise(buffer_, capacity_, MADV_DONTDUMP);
    }

    ~SecurePasswordMemory() {
        clear();
        munlock(buffer_, capacity_);
        munmap(buffer_, capacity_);
    }

    void store(const std::string& password) {
        if (password.size() > capacity_ - 1) {
            throw std::runtime_error("Password too long");
        }
        std::memcpy(buffer_, password.c_str(), password.size());
        buffer_[password.size()] = '\0';
        length_ = password.size();
    }

    const char* get() const {
        return buffer_;
    }

    size_t length() const {
        return length_;
    }

    // Limpeza segura — impede otimização do compilador
    void clear() {
        if (buffer_) {
            sodium_memzero(buffer_, capacity_);
            length_ = 0;
        }
    }

    // Desabilitar cópia para evitar vazamento
    SecurePasswordMemory(const SecurePasswordMemory&) = delete;
    SecurePasswordMemory& operator=(const SecurePasswordMemory&) = delete;

private:
    char* buffer_;
    size_t capacity_;
    size_t length_ = 0;
    bool locked_;
};
```

### 7.2.6 Aplicação de Política de Senhas

```cpp
#include <string>
#include <vector>
#include <algorithm>
#include <regex>

struct PasswordPolicy {
    size_t minLength = 12;
    size_t maxLength = 128;
    bool requireUppercase = true;
    bool requireLowercase = true;
    bool requireDigit = true;
    bool requireSpecial = true;
    size_t maxConsecutiveRepeats = 3;
    std::vector<std::string> breachedPasswords; // HaveIBeenPwned integration
};

struct PolicyResult {
    bool valid;
    std::vector<std::string> violations;
};

class PasswordValidator {
public:
    explicit PasswordValidator(PasswordPolicy policy) 
        : policy_(std::move(policy)) {}

    PolicyResult validate(const std::string& password) const {
        PolicyResult result;
        result.valid = true;

        // Comprimento mínimo
        if (password.size() < policy_.minLength) {
            result.violations.push_back(
                "Password must be at least " + 
                std::to_string(policy_.minLength) + " characters");
            result.valid = false;
        }

        // Comprimento máximo
        if (password.size() > policy_.maxLength) {
            result.violations.push_back(
                "Password must be at most " + 
                std::to_string(policy_.maxLength) + " characters");
            result.valid = false;
        }

        // Requisitos de caracteres
        if (policy_.requireUppercase && 
            !std::any_of(password.begin(), password.end(), ::isupper)) {
            result.violations.push_back(
                "Password must contain at least one uppercase letter");
            result.valid = false;
        }

        if (policy_.requireLowercase && 
            !std::any_of(password.begin(), password.end(), ::islower)) {
            result.violations.push_back(
                "Password must contain at least one lowercase letter");
            result.valid = false;
        }

        if (policy_.requireDigit && 
            !std::any_of(password.begin(), password.end(), ::isdigit)) {
            result.violations.push_back(
                "Password must contain at least one digit");
            result.valid = false;
        }

        if (policy_.requireSpecial) {
            std::string specials = "!@#$%^&*()_+-=[]{}|;:,.<>?";
            bool hasSpecial = false;
            for (char c : password) {
                if (specials.find(c) != std::string::npos) {
                    hasSpecial = true;
                    break;
                }
            }
            if (!hasSpecial) {
                result.violations.push_back(
                    "Password must contain at least one special character");
                result.valid = false;
            }
        }

        // Verificar caracteres consecutivos repetidos
        if (policy_.maxConsecutiveRepeats > 0) {
            size_t count = 1;
            for (size_t i = 1; i < password.size(); ++i) {
                if (password[i] == password[i - 1]) {
                    count++;
                    if (count > policy_.maxConsecutiveRepeats) {
                        result.violations.push_back(
                            "Password has more than " + 
                            std::to_string(policy_.maxConsecutiveRepeats) +
                            " consecutive repeated characters");
                        result.valid = false;
                        break;
                    }
                } else {
                    count = 1;
                }
            }
        }

        return result;
    }

private:
    PasswordPolicy policy_;
};
```

### 7.2.7 Estudo de Caso: LinkedIn (2012) e Yahoo (2013-2014)

**LinkedIn (2012):** Vazamento de 117 milhões de contas com senhas armazenadas em **SHA-1 sem salt**. Embora SHA-1 seja uma função de hash criptográfica, sua velocidade e a ausência de salt tornaram o vazamento catastrófico.

```cpp
// VULNERÁVEL: Padrão LinkedIn 2012 — SHA-1 sem salt
// NÃO USE ESTE CÓDIGO
#include <openssl/sha.h>
#include <string>

class LinkedInVulnerableHasher {
public:
    std::string hash(const std::string& password) {
        unsigned char hash[SHA_DIGEST_LENGTH];
        SHA1(reinterpret_cast<const unsigned char*>(password.data()),
             password.size(), hash);
        
        std::string result;
        for (int i = 0; i < SHA_DIGEST_LENGTH; ++i) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", hash[i]);
            result += buf;
        }
        return result;
    }
};
```

**Yahoo (2013-2014):** Vazamento de **3 bilhões de contas**. Senhas armazenadas com MD5 (em alguns casos) e bcrypt com custo insuficiente. A combinação de algoritmo fraco e parâmetros inadequados facilitou a recuperação massiva de senhas.

A vulnerabilidade comum entre LinkedIn e Yahoo foi a incapacidade de adaptar o custo computacional ao avanço do hardware. Com Argon2id, podemos ajustar os parâmetros conforme o hardware evolui, mantendo a proteção eficaz.

---

## 7.3 Autenticação Multi-Fator (MFA/2FA)

### 7.3.1 TOTP (Time-based One-Time Password) — RFC 6238

TOTP gera senhas de uso único baseadas no tempo. A cada 30 segundos, um novo código de 6 dígitos é gerado compartilhando um segredo entre o servidor e o cliente.

O algoritmo é: `TOTP = HOTP(K, T)` onde `T = floor(current_unix_time / time_step)`.

### 7.3.2 Implementação Completa de TOTP em C++

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <sstream>
#include <iomanip>

class TOTPGenerator {
public:
    static constexpr int DEFAULT_DIGITS = 6;
    static constexpr int DEFAULT_PERIOD = 30;  // segundos
    static constexpr int DEFAULT_ALGORITHM = CRYPTO_AUTH_HMACSHA256_BYTES;
    static constexpr int WINDOW = 1;  // tolerância de ±1 período

    TOTPGenerator(const std::vector<unsigned char>& secret,
                  int digits = DEFAULT_DIGITS,
                  int period = DEFAULT_PERIOD)
        : secret_(secret), digits_(digits), period_(period) {}

    // Gerar TOTP para o tempo atual
    std::string generate() const {
        auto now = std::chrono::system_clock::now();
        auto timeSinceEpoch = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        return generateForTime(timeSinceEpoch);
    }

    // Gerar TOTP para um timestamp específico
    std::string generateForTime(int64_t unixTime) const {
        int64_t timeCounter = unixTime / period_;
        return generateHOTP(timeCounter);
    }

    // Verificar TOTP com janela de tolerância
    bool verify(const std::string& code) const {
        auto now = std::chrono::system_clock::now();
        auto timeSinceEpoch = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        
        for (int i = -WINDOW; i <= WINDOW; ++i) {
            int64_t timeCounter = (timeSinceEpoch / period_) + i;
            std::string expected = generateHOTP(timeCounter);
            
            // Comparação de tempo constante
            if (sodium_memcmp(code.data(), expected.data(),
                            std::min(code.size(), expected.size())) == 0 &&
                code.size() == expected.size()) {
                return true;
            }
        }
        return false;
    }

    // Gerar segredo aleatório para novo usuário
    static std::vector<unsigned char> generateSecret(size_t length = 32) {
        std::vector<unsigned char> secret(length);
        randombytes_buf(secret.data(), length);
        return secret;
    }

    // Gerar URI para QR code (formato otpauth://)
    std::string getURI(const std::string& issuer,
                       const std::string& accountName) const {
        std::string uri = "otpauth://totp/";
        uri += urlEncode(issuer) + ":" + urlEncode(accountName);
        uri += "?secret=" + base32Encode(secret_);
        uri += "&issuer=" + urlEncode(issuer);
        uri += "&algorithm=SHA256";
        uri += "&digits=" + std::to_string(digits_);
        uri += "&period=" + std::to_string(period_);
        return uri;
    }

private:
    std::vector<unsigned char> secret_;
    int digits_;
    int period_;

    std::string generateHOTP(int64_t counter) const {
        // Converter counter para big-endian
        unsigned char counterBytes[8];
        counterBytes[0] = (counter >> 56) & 0xFF;
        counterBytes[1] = (counter >> 48) & 0xFF;
        counterBytes[2] = (counter >> 40) & 0xFF;
        counterBytes[3] = (counter >> 32) & 0xFF;
        counterBytes[4] = (counter >> 24) & 0xFF;
        counterBytes[5] = (counter >> 16) & 0xFF;
        counterBytes[6] = (counter >> 8) & 0xFF;
        counterBytes[7] = counter & 0xFF;

        // HMAC-SHA256
        unsigned char hmac[CRYPTO_AUTH_HMACSHA256_BYTES];
        crypto_auth_hmacsha256_state state;
        
        crypto_auth_hmacsha256_init(&state, secret_.data(), secret_.size());
        crypto_auth_hmacsha256_update(&state, counterBytes, 8);
        crypto_auth_hmacsha256_final(&state, hmac);

        // Dynamic truncation
        int offset = hmac[hmac[sizeof(hmac) - 1] & 0x0F] & 0x7F;
        
        uint32_t binary = 
            ((uint32_t)hmac[offset] << 24) |
            ((uint32_t)hmac[offset + 1] << 16) |
            ((uint32_t)hmac[offset + 2] << 8) |
            ((uint32_t)hmac[offset + 3]);

        uint32_t otp = binary % static_cast<uint32_t>(std::pow(10, digits_));
        
        // Formatar com zeros à esquerda
        std::ostringstream oss;
        oss << std::setw(digits_) << std::setfill('0') << otp;
        return oss.str();
    }

    std::string base32Encode(const std::vector<unsigned char>& data) const {
        const char alphabet[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
        std::string result;
        int bits = 0;
        uint32_t value = 0;
        
        for (unsigned char byte : data) {
            value = (value << 8) | byte;
            bits += 8;
            while (bits >= 5) {
                result += alphabet[(value >> (bits - 5)) & 0x1F];
                bits -= 5;
            }
        }
        if (bits > 0) {
            result += alphabet[(value << (5 - bits)) & 0x1F];
        }
        return result;
    }

    std::string urlEncode(const std::string& value) const {
        std::string result;
        result.reserve(value.size() * 3);
        for (char c : value) {
            if (std::isalnum(static_cast<unsigned char>(c)) || 
                c == '-' || c == '_' || c == '.' || c == '~') {
                result += c;
            } else {
                char buf[4];
                snprintf(buf, sizeof(buf), "%%%02X", 
                        static_cast<unsigned char>(c));
                result += buf;
            }
        }
        return result;
    }
};
```

### 7.3.3 HOTP — HMAC-based One-Time Password

HOTP (RFC 4226) é a base do TOTP, mas usa um contador incremental em vez de tempo:

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <cstdint>
#include <cstring>
#include <sstream>
#include <iomanip>

class HOTPGenerator {
public:
    HOTPGenerator(const std::vector<unsigned char>& secret, int digits = 6)
        : secret_(secret), digits_(digits) {}

    std::string generate(uint64_t counter) const {
        // Converter counter para big-endian
        unsigned char counterBytes[8];
        for (int i = 7; i >= 0; --i) {
            counterBytes[i] = counter & 0xFF;
            counter >>= 8;
        }

        unsigned char hmac[CRYPTO_AUTH_HMACSHA1_BYTES];
        crypto_auth_hmacsha1_state state;
        crypto_auth_hmacsha1_init(&state, secret_.data(), secret_.size());
        crypto_auth_hmacsha1_update(&state, counterBytes, 8);
        crypto_auth_hmacsha1_final(&state, hmac);

        // Dynamic truncation (RFC 4226)
        int offset = hmac[19] & 0x0F;
        
        uint32_t binary = 
            ((uint32_t)hmac[offset] & 0x7F) << 24 |
            ((uint32_t)hmac[offset + 1] & 0xFF) << 16 |
            ((uint32_t)hmac[offset + 2] & 0xFF) << 8 |
            ((uint32_t)hmac[offset + 3] & 0xFF);

        uint32_t otp = binary % 1000000;  // 10^digits
        
        std::ostringstream oss;
        oss << std::setw(digits_) << std::setfill('0') << otp;
        return oss.str();
    }

    bool verify(const std::string& code, uint64_t counter,
                int window = 10) const {
        for (uint64_t i = counter; i <= counter + window; ++i) {
            if (sodium_memcmp(code.data(), generate(i).data(),
                            code.size()) == 0) {
                return true;
            }
        }
        return false;
    }

private:
    std::vector<unsigned char> secret_;
    int digits_;
};
```

### 7.3.4 Códigos de Backup e Recuperação

Códigos de backup são senhas de uso único geradas durante o registro de MFA, projetadas para recuperação em caso de perda do dispositivo:

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <random>
#include <sstream>
#include <iomanip>
#include <algorithm>

class BackupCodeGenerator {
public:
    struct BackupCode {
        std::string code;
        bool used = false;
    };

    std::vector<BackupCode> generate(size_t count = 10) {
        std::vector<BackupCode> codes;
        codes.reserve(count);

        for (size_t i = 0; i < count; ++i) {
            BackupCode bc;
            bc.code = generateSingleCode();
            codes.push_back(bc);
        }

        return codes;
    }

    // Hash para armazenamento seguro
    std::string hashBackupCode(const std::string& code) {
        // Usar Argon2id — mesmo algoritmo das senhas
        char hashed[crypto_pwhash_STRBYTES];
        crypto_pwhash_str(
            hashed,
            code.c_str(),
            code.size(),
            crypto_pwhash_OPSLIMIT_MODERATE,
            crypto_pwhash_MEMLIMIT_MODERATE);
        return std::string(hashed);
    }

    // Verificar código de backup (deve consumir o código)
    bool verify(const std::string& code,
                const std::string& storedHash) {
        // Comparação de tempo constante
        return crypto_pwhash_str_verify(
            storedHash.c_str(),
            code.c_str(),
            code.size()) == 0;
    }

private:
    std::string generateSingleCode() {
        std::vector<unsigned char> bytes(4);
        randombytes_buf(bytes.data(), 4);
        
        // Código no formato XXXXX-XXXXX (10 caracteres)
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        
        for (size_t i = 0; i < 2; ++i) {
            uint32_t val = (static_cast<uint32_t>(bytes[i * 2]) << 8) |
                          bytes[i * 2 + 1];
            val = val % 100000;
            oss << std::setw(5) << val;
            if (i == 0) oss << "-";
        }
        
        return oss.str();
    }
};
```

### 7.3.5 Estudo de Caso: Colonial Pipeline (2021)

Em maio de 2021, o Colonial Pipeline — que fornece 45% do combustível da costa leste dos EUA — foi forçado a encerrar operações por dias devido a um ataque ransomware. A causa raiz? **Credenciais comprometidas sem MFA.**

**O que deu errado:** Um funcionário da VPN corporativa usava uma senha reutilizada de outro vazamento de dados. A VPN não exigia autenticação multi-fator, permitindo que o atacante acessasse diretamente a rede corporativa. Um investimento mínimo em MFA teria prevenido toda a intrusão.

```cpp
// PADRÃO SEGURO: Verificação de MFA obrigatória
class AuthMiddleware {
public:
    struct AuthResult {
        bool authenticated = false;
        bool mfaVerified = false;
        std::string userId;
        std::string errorMessage;
    };

    AuthResult authenticate(const std::string& token,
                            const std::string& mfaCode) {
        AuthResult result;

        // 1. Verificar token de sessão
        auto sessionData = validateSession(token);
        if (!sessionData.valid) {
            result.errorMessage = "Invalid or expired session";
            return result;
        }
        result.userId = sessionData.userId;
        result.authenticated = true;

        // 2. Verificar se MFA foi concluído
        if (sessionData.mfaVerified) {
            result.mfaVerified = true;
            return result;
        }

        // 3. Verificar código MFA fornecido
        if (mfaCode.empty()) {
            result.errorMessage = "MFA code required";
            return result;
        }

        auto totpSecret = getStoredMFASecret(result.userId);
        TOTPGenerator totp(totpSecret);
        
        if (!totp.verify(mfaCode)) {
            result.errorMessage = "Invalid MFA code";
            return result;
        }

        // 4. Atualizar sessão como MFA verificada
        markMFAVerified(sessionData.sessionId);
        result.mfaVerified = true;
        
        return result;
    }

private:
    struct SessionData {
        bool valid = false;
        bool mfaVerified = false;
        std::string userId;
        std::string sessionId;
    };

    SessionData validateSession(const std::string& token) {
        SessionData data;
        data.valid = true;
        data.userId = "user123";
        data.sessionId = "session456";
        return data;
    }

    std::vector<unsigned char> getStoredMFASecret(const std::string& userId) {
        return std::vector<unsigned char>(32, 0xAB);
    }

    void markMFAVerified(const std::string& sessionId) {
        // Atualizar sessão no banco de dados
    }
};
```

---

## 7.4 Session Management

### 7.4.1 Geração de Tokens de Sessão

Tokens de sessão devem ser gerados usando um CSPRNG (Cryptographically Secure Pseudo-Random Number Generator) com entropia suficiente (mínimo de 128 bits):

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <chrono>
#include <map>
#include <mutex>
#include <optional>
#include <random>

struct SessionData {
    std::string sessionId;
    std::string userId;
    std::string ipAddress;
    std::string userAgent;
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point lastAccessedAt;
    std::chrono::seconds timeout{3600};  // 1 hora
    bool mfaVerified = false;
    std::map<std::string, std::string> metadata;
};

class SessionManager {
public:
    SessionManager() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    // Criar nova sessão
    std::string createSession(const std::string& userId,
                               const std::string& ipAddress,
                               const std::string& userAgent) {
        std::string sessionId = generateSecureToken(32);
        
        SessionData session;
        session.sessionId = sessionId;
        session.userId = userId;
        session.ipAddress = ipAddress;
        session.userAgent = userAgent;
        session.createdAt = std::chrono::system_clock::now();
        session.lastAccessedAt = session.createdAt;
        
        std::lock_guard<std::mutex> lock(mutex_);
        sessions_[sessionId] = std::move(session);
        
        return sessionId;
    }

    // Validar sessão
    std::optional<SessionData> validateSession(const std::string& sessionId,
                                                const std::string& ipAddress) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) {
            return std::nullopt;
        }

        auto& session = it->second;
        auto now = std::chrono::system_clock::now();

        // Verificar timeout
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - session.lastAccessedAt);
        if (elapsed > session.timeout) {
            sessions_.erase(it);
            return std::nullopt;
        }

        // Verificar IP (opcional — protege contra session hijacking)
        if (!session.ipAddress.empty() && session.ipAddress != ipAddress) {
            sessions_.erase(it);
            return std::nullopt;
        }

        // Atualizar último acesso
        session.lastAccessedAt = now;
        
        return session;
    }

    // Invalidar sessão (logout)
    void invalidateSession(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        sessions_.erase(sessionId);
    }

    // Invalidar todas as sessões de um usuário
    void invalidateAllUserSessions(const std::string& userId) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (auto it = sessions_.begin(); it != sessions_.end();) {
            if (it->second.userId == userId) {
                it = sessions_.erase(it);
            } else {
                ++it;
            }
        }
    }

    // Renovar sessão (regenerar token)
    std::string renewSession(const std::string& oldSessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = sessions_.find(oldSessionId);
        if (it == sessions_.end()) {
            return "";
        }

        SessionData session = it->second;
        session.sessionId = generateSecureToken(32);
        session.lastAccessedAt = std::chrono::system_clock::now();
        
        sessions_.erase(it);
        sessions_[session.sessionId] = session;
        
        return session.sessionId;
    }

    // Limpeza periódica de sessões expiradas
    size_t cleanupExpiredSessions() {
        std::lock_guard<std::mutex> lock(mutex_);
        auto now = std::chrono::system_clock::now();
        size_t removed = 0;

        for (auto it = sessions_.begin(); it != sessions_.end();) {
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                now - it->second.lastAccessedAt);
            if (elapsed > it->second.timeout) {
                it = sessions_.erase(it);
                removed++;
            } else {
                ++it;
            }
        }
        return removed;
    }

private:
    std::map<std::string, SessionData> sessions_;
    std::mutex mutex_;

    std::string generateSecureToken(size_t length) {
        std::vector<unsigned char> bytes(length);
        randombytes_buf(bytes.data(), length);
        
        // Codificar em hexadecimal
        std::string result;
        result.reserve(length * 2);
        for (unsigned char b : bytes) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", b);
            result += buf;
        }
        return result;
    }
};
```

### 7.4.2 Segurança de Cookies de Sessão

```cpp
// Padrão seguro para cookies de sessão
struct CookieAttributes {
    std::string name = "SESSION_ID";
    std::string value;
    std::string path = "/";
    std::string domain;
    int maxAge = 3600;
    bool httpOnly = true;    // Impede acesso via JavaScript
    bool secure = true;      // Enviar apenas via HTTPS
    bool sameSite = true;    // CSRF protection
    std::string sameSiteMode = "Strict";  // Strict, Lax, ou None

    std::string toString() const {
        std::string cookie = name + "=" + value + "; ";
        cookie += "Path=" + path + "; ";
        if (!domain.empty()) cookie += "Domain=" + domain + "; ";
        cookie += "Max-Age=" + std::to_string(maxAge) + "; ";
        if (httpOnly) cookie += "HttpOnly; ";
        if (secure) cookie += "Secure; ";
        if (sameSite) cookie += "SameSite=" + sameSiteMode + "; ";
        return cookie;
    }
};
```

### 7.4.3 Estudo de Caso: Okta (2023)

Em janeiro de 2023, a Okta sofreu um ataque que expôs a sessão de cerca de 1% de seus clientes (aproximadamente 366 empresas). O vetor de ataque envolveu **roubo de tokens de sessão** através de um acesso não autorizado ao suporte.

**O que deu errado:** Uma conta de suporte com acesso limitado foi comprometida. O atacante usou essa conta para acessar ferramentas de suporte e extrair tokens de sessão de clientes. A Okta não implementava rotação de tokens de sessão após redefinições de senha e não detectava tokens sendo acessados fora do fluxo normal.

**A prevenção:**
1. Rotação de token após eventos de segurança.
2. Detecção de anomalias no acesso a sessões.
3. Limitação de acesso de contas de suporte.
4. MFA obrigatório para acesso administrativo.

---

## 7.5 JSON Web Tokens (JWT)

### 7.5.1 Estrutura de um JWT

Um JWT consiste em três partes separadas por pontos:

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIiwiZXhwIjoxNjE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

| Parte | Conteúdo | Formato |
|-------|----------|---------|
| Header | Algoritmo e tipo | JSON codificado em Base64URL |
| Payload | Claims (dados) | JSON codificado em Base64URL |
| Signature | Assinatura | HMAC-SHA256 ou RSA/ECDSA |

### 7.5.2 Implementação Completa de JWT em C++

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <map>
#include <chrono>
#include <algorithm>
#include <stdexcept>
#include <cstring>
#include <sstream>
#include <functional>

class JWTManager {
public:
    JWTManager(const std::string& secretKey) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        if (secretKey.size() < 32) {
            throw std::runtime_error("Secret key must be at least 32 bytes");
        }
        secretKey_ = secretKey;
    }

    // Criar JWT
    std::string createToken(const std::map<std::string, std::string>& claims,
                            int expirationSeconds = 3600) {
        // Header
        std::string header = "{\"alg\":\"HS256\",\"typ\":\"JWT\"}";
        std::string headerB64 = base64UrlEncode(header);

        // Payload com claims
        auto now = std::chrono::system_clock::now();
        auto exp = now + std::chrono::seconds(expirationSeconds);
        auto iat = now;

        std::string payload = "{";
        payload += "\"iss\":\"devsecurity\",";
        payload += "\"iat\":" + std::to_string(
            std::chrono::duration_cast<std::chrono::seconds>(
                iat.time_since_epoch()).count()) + ",";
        payload += "\"exp\":" + std::to_string(
            std::chrono::duration_cast<std::chrono::seconds>(
                exp.time_since_epoch()).count());
        
        for (const auto& [key, value] : claims) {
            payload += ",\"" + key + "\":\"" + value + "\"";
        }
        payload += "}";

        std::string payloadB64 = base64UrlEncode(payload);

        // Signature
        std::string signingInput = headerB64 + "." + payloadB64;
        std::string signature = hmacSHA256(signingInput, secretKey_);
        std::string signatureB64 = base64UrlEncode(signature);

        return headerB64 + "." + payloadB64 + "." + signatureB64;
    }

    // Verificar JWT
    struct VerificationResult {
        bool valid;
        std::map<std::string, std::string> claims;
        std::string error;
    };

    VerificationResult verifyToken(const std::string& token) {
        VerificationResult result;
        result.valid = false;

        // Separar partes
        auto parts = splitToken(token);
        if (parts.size() != 3) {
            result.error = "Invalid token format";
            return result;
        }

        // Verificar algoritmo no header
        std::string headerJson = base64UrlDecode(parts[0]);
        if (headerJson.find("\"alg\":\"HS256\"") == std::string::npos) {
            result.error = "Invalid algorithm";
            return result;
        }

        // VERIFICAR SE 'none' ALGORITHM ESTÁ PRESENTE (ATAQUE COMUM)
        if (headerJson.find("\"alg\":\"none\"") != std::string::npos ||
            headerJson.find("\"alg\":\"None\"") != std::string::npos ||
            headerJson.find("\"alg\":\"NONE\"") != std::string::npos) {
            result.error = "Algorithm 'none' is not allowed";
            return result;
        }

        // Verificar assinatura (tempo constante)
        std::string signingInput = parts[0] + "." + parts[1];
        std::string expectedSig = hmacSHA256(signingInput, secretKey_);
        std::string providedSig = base64UrlDecode(parts[2]);

        if (sodium_memcmp(expectedSig.data(), providedSig.data(),
                        std::min(expectedSig.size(), providedSig.size())) != 0) {
            result.error = "Invalid signature";
            return result;
        }

        // Decodificar payload
        std::string payloadJson = base64UrlDecode(parts[1]);
        result.claims = parseJSON(payloadJson);

        // Verificar expiração
        if (result.claims.count("exp")) {
            auto exp = std::stoll(result.claims["exp"]);
            auto now = std::chrono::system_clock::now();
            auto nowSeconds = std::chrono::duration_cast<std::chrono::seconds>(
                now.time_since_epoch()).count();
            
            if (nowSeconds > exp) {
                result.error = "Token expired";
                return result;
            }
        }

        result.valid = true;
        return result;
    }

    // Criar refresh token
    std::string createRefreshToken(const std::string& userId) {
        std::map<std::string, std::string> claims;
        claims["sub"] = userId;
        claims["type"] = "refresh";
        return createToken(claims, 604800);  // 7 dias
    }

    // Revogar token (requer armazenamento de revogações)
    void revokeToken(const std::string& token) {
        auto result = verifyToken(token);
        if (result.valid && result.claims.count("jti")) {
            revokedTokens_.insert(result.claims["jti"]);
        }
    }

    // Verificar se token foi revogado
    bool isTokenRevoked(const std::string& token) {
        auto result = verifyToken(token);
        if (result.valid && result.claims.count("jti")) {
            return revokedTokens_.count(result.claims["jti"]) > 0;
        }
        return false;
    }

private:
    std::string secretKey_;
    std::vector<std::string> revokedTokens_;

    std::string hmacSHA256(const std::string& message,
                           const std::string& key) {
        unsigned char hmac[CRYPTO_AUTH_HMACSHA256_BYTES];
        crypto_auth_hmacsha256_state state;
        crypto_auth_hmacsha256_init(&state,
            reinterpret_cast<const unsigned char*>(key.data()), key.size());
        crypto_auth_hmacsha256_update(&state,
            reinterpret_cast<const unsigned char*>(message.data()),
            message.size());
        crypto_auth_hmacsha256_final(&state, hmac);
        return std::string(reinterpret_cast<char*>(hmac),
                          CRYPTO_AUTH_HMACSHA256_BYTES);
    }

    std::string base64UrlEncode(const std::string& input) {
        // Implementação base64 URL-safe
        const char* chars = 
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        
        std::string result;
        result.reserve(((input.size() + 2) / 3) * 4);
        
        unsigned char const* bytesToEncode = 
            reinterpret_cast<unsigned char const*>(input.data());
        size_t len = input.size();
        
        for (size_t i = 0; i < len; i += 3) {
            uint32_t n = static_cast<uint32_t>(bytesToEncode[i]) << 16;
            if (i + 1 < len) n |= static_cast<uint32_t>(bytesToEncode[i + 1]) << 8;
            if (i + 2 < len) n |= static_cast<uint32_t>(bytesToEncode[i + 2]);
            
            result += chars[(n >> 18) & 0x3F];
            result += chars[(n >> 12) & 0x3F];
            if (i + 1 < len) result += chars[(n >> 6) & 0x3F];
            if (i + 2 < len) result += chars[n & 0x3F];
        }
        
        return result;
    }

    std::string base64UrlDecode(const std::string& input) {
        std::string result;
        std::vector<int> T(256, -1);
        const char* chars = 
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        for (int i = 0; i < 64; ++i) T[static_cast<unsigned char>(chars[i])] = i;
        
        unsigned int buf = 0;
        int bits = 0;
        
        for (char c : input) {
            int val = T[static_cast<unsigned char>(c)];
            if (val == -1) continue;
            
            buf = (buf << 6) | val;
            bits += 6;
            if (bits >= 8) {
                bits -= 8;
                result += static_cast<char>((buf >> bits) & 0xFF);
            }
        }
        
        return result;
    }

    std::vector<std::string> splitToken(const std::string& token) {
        std::vector<std::string> parts;
        size_t start = 0;
        size_t end;
        
        while ((end = token.find('.', start)) != std::string::npos) {
            parts.push_back(token.substr(start, end - start));
            start = end + 1;
        }
        parts.push_back(token.substr(start));
        
        return parts;
    }

    std::map<std::string, std::string> parseJSON(const std::string& json) {
        std::map<std::string, std::string> result;
        // Parser JSON simplificado (produção deve usar biblioteca robusta)
        size_t pos = 0;
        while (pos < json.size()) {
            auto keyStart = json.find('"', pos);
            if (keyStart == std::string::npos) break;
            auto keyEnd = json.find('"', keyStart + 1);
            if (keyEnd == std::string::npos) break;
            
            std::string key = json.substr(keyStart + 1, keyEnd - keyStart - 1);
            
            auto valStart = json.find('"', keyEnd + 1);
            if (valStart == std::string::npos) {
                // Valor numérico
                auto valEnd = json.find_first_of(",}", keyEnd + 1);
                std::string value = json.substr(keyEnd + 1, valEnd - keyEnd - 1);
                result[key] = value;
                pos = valEnd;
            } else {
                auto valEnd = json.find('"', valStart + 1);
                std::string value = json.substr(valStart + 1, valEnd - valStart - 1);
                result[key] = value;
                pos = valEnd + 1;
            }
        }
        return result;
    }
};
```

### 7.5.3 Estudo de Caso: Ataque 'none' Algorithm em JWT

O ataque de confusão de algoritmo ('none' algorithm) é uma vulnerabilidade clássica em implementações JWT. O RFC 7518 define que o algoritmo "none" NÃO deve ser aceito para assinatura, mas muitas implementações originalmente permitiam.

```cpp
// Demonstração do ataque e defesa
// NÃO EXECUTE O CÓDIGO VULNERÁVEL EM PRODUÇÃO

// ATAQUE: Como um JWT 'none' é forjado
/*
1. Header: {"alg":"none","typ":"JWT"}
   Base64URL: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0

2. Payload: {"sub":"admin","iat":1616239022,"exp":9999999999}
   Base64URL: eyJzdWIiOiJhZG1pbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjo5OTk5OTk5OTk5fQ

3. Signature: (vazio)
   
   Token final: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiIsImlhdCI6MTYxNjIzOTAyMiwiZXhwIjo5OTk5OTk5OTk5fQ.
*/

// DEFESA: Verificação rigorosa do algoritmo
class SecureJWTVerifier {
public:
    bool verify(const std::string& token) {
        // Extrair header
        auto headerB64 = extractHeader(token);
        auto headerJson = base64UrlDecode(headerB64);
        
        // DEFESA CRÍTICA: Rejeitar explicitamente 'none'
        if (headerJson.find("\"alg\"") != std::string::npos) {
            std::string alg = extractAlgorithm(headerJson);
            if (alg == "none" || alg == "None" || alg == "NONE" || alg == "nOnE") {
                return false;  // Rejeitar qualquer variação
            }
        }
        
        // Verificar assinatura
        return verifyHMAC(token);
    }

private:
    std::string extractHeader(const std::string& token) {
        auto dot1 = token.find('.');
        return token.substr(0, dot1);
    }

    std::string extractAlgorithm(const std::string& headerJson) {
        auto algPos = headerJson.find("\"alg\"");
        if (algPos == std::string::npos) return "";
        
        auto colonPos = headerJson.find(':', algPos);
        auto quoteStart = headerJson.find('"', colonPos);
        auto quoteEnd = headerJson.find('"', quoteStart + 1);
        
        return headerJson.substr(quoteStart + 1, quoteEnd - quoteStart - 1);
    }

    std::string base64UrlDecode(const std::string& input) {
        return input;  // Simplificado
    }

    bool verifyHMAC(const std::string& token) {
        return true;  // Simplificado
    }
};
```

---

## 7.6 OAuth 2.0 e OpenID Connect

### 7.6.1 Fluxo de Autorização com PKCE

PKCE (Proof Key for Code Exchange, RFC 7636) previne ataques de interceptação no fluxo de autorização:

```
┌─────────┐     ┌─────────────┐     ┌──────────────┐
│  Cliente │────▶│   AuthZ     │────▶│   Resource   │
│  (App)   │◀────│   Server    │◀────│   Server     │
└─────────┘     └─────────────┘     └──────────────┘
     │                │                      │
     │   1. code_verifier + code_challenge   │
     │───────────────▶│                      │
     │                │   2. authorization_code
     │◀───────────────│                      │
     │   3. code + code_verifier             │
     │───────────────▶│                      │
     │                │   4. access_token     │
     │◀───────────────│──────────────────────│
```

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <random>
#include <sstream>
#include <iomanip>
#include <functional>

class PKCEHelper {
public:
    struct PKCEChallenge {
        std::string codeVerifier;
        std::string codeChallenge;
    };

    // Gerar code_verifier (43-128 caracteres, URL-safe)
    static std::string generateCodeVerifier() {
        std::vector<unsigned char> bytes(64);
        randombytes_buf(bytes.data(), 64);
        
        const char charset[] = 
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
        
        std::string verifier;
        verifier.reserve(64);
        for (unsigned char b : bytes) {
            verifier += charset[b % 66];
        }
        return verifier;
    }

    // Gerar code_challenge a partir do code_verifier (S256)
    static std::string generateCodeChallenge(const std::string& verifier) {
        // SHA-256 do code_verifier
        unsigned char hash[32];
        crypto_hash_sha256(
            hash,
            reinterpret_cast<const unsigned char*>(verifier.data()),
            verifier.size());
        
        // Base64URL encode
        return base64UrlEncode(hash, 32);
    }

    // Gerar par completo
    static PKCEChallenge generateChallenge() {
        PKCEChallenge challenge;
        challenge.codeVerifier = generateCodeVerifier();
        challenge.codeChallenge = generateCodeChallenge(challenge.codeVerifier);
        return challenge;
    }

    // Verificar code_verifier contra code_challenge
    static bool verifyChallenge(const std::string& verifier,
                                 const std::string& challenge) {
        std::string computed = generateCodeChallenge(verifier);
        return sodium_memcmp(computed.data(), challenge.data(),
                           std::min(computed.size(), challenge.size())) == 0 &&
               computed.size() == challenge.size();
    }

private:
    static std::string base64UrlEncode(const unsigned char* data, size_t len) {
        const char charset[] = 
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
        
        std::string result;
        result.reserve(((len + 2) / 3) * 4);
        
        for (size_t i = 0; i < len; i += 3) {
            uint32_t n = static_cast<uint32_t>(data[i]) << 16;
            if (i + 1 < len) n |= static_cast<uint32_t>(data[i + 1]) << 8;
            if (i + 2 < len) n |= static_cast<uint32_t>(data[i + 2]);
            
            result += charset[(n >> 18) & 0x3F];
            result += charset[(n >> 12) & 0x3F];
            if (i + 1 < len) result += charset[(n >> 6) & 0x3F];
            if (i + 2 < len) result += charset[n & 0x3F];
        }
        
        return result;
    }
};
```

### 7.6.2 Cliente OAuth 2.0 Completo

```cpp
#include <string>
#include <map>
#include <stdexcept>

struct OAuthConfig {
    std::string clientId;
    std::string clientSecret;
    std::string redirectUri;
    std::string authorizationEndpoint;
    std::string tokenEndpoint;
    std::string userInfoEndpoint;
    std::vector<std::string> scopes;
};

class OAuth2Client {
public:
    explicit OAuth2Client(OAuthConfig config) : config_(std::move(config)) {}

    struct AuthResult {
        std::string authorizationUrl;
        std::string codeVerifier;
        std::string state;
    };

    // Passo 1: Gerar URL de autorização com PKCE
    AuthResult initiateAuthorization() {
        AuthResult result;
        
        // Gerar state (CSRF protection)
        result.state = generateRandomState();
        
        // Gerar PKCE
        auto pkce = PKCEHelper::generateChallenge();
        result.codeVerifier = pkce.codeVerifier;
        
        // Construir URL
        result.authorizationUrl = config_.authorizationEndpoint;
        result.authorizationUrl += "?response_type=code";
        result.authorizationUrl += "&client_id=" + config_.clientId;
        result.authorizationUrl += "&redirect_uri=" + urlEncode(config_.redirectUri);
        result.authorizationUrl += "&state=" + result.state;
        result.authorizationUrl += "&code_challenge=" + pkce.codeChallenge;
        result.authorizationUrl += "&code_challenge_method=S256";
        
        // Scopes
        std::string scopeStr;
        for (const auto& scope : config_.scopes) {
            if (!scopeStr.empty()) scopeStr += " ";
            scopeStr += scope;
        }
        result.authorizationUrl += "&scope=" + urlEncode(scopeStr);
        
        // Armazenar state e code_verifier para verificação posterior
        pendingStates_[result.state] = result.codeVerifier;
        
        return result;
    }

    // Passo 2: Trocar código por token
    struct TokenResponse {
        std::string accessToken;
        std::string refreshToken;
        std::string idToken;
        int expiresIn;
        std::string tokenType;
    };

    TokenResponse exchangeCode(const std::string& code,
                                const std::string& state,
                                const std::string& codeVerifier) {
        // Verificar state
        if (pendingStates_.find(state) == pendingStates_.end()) {
            throw std::runtime_error("Invalid state — possible CSRF attack");
        }
        pendingStates_.erase(state);
        
        // Verificar PKCE
        if (!PKCEHelper::verifyChallenge(codeVerifier, 
            storedChallenges_[state])) {
            throw std::runtime_error("PKCE verification failed");
        }
        
        TokenResponse response;
        response.accessToken = "generated_access_token";
        response.refreshToken = "generated_refresh_token";
        response.expiresIn = 3600;
        response.tokenType = "Bearer";
        
        return response;
    }

private:
    OAuthConfig config_;
    std::map<std::string, std::string> pendingStates_;
    std::map<std::string, std::string> storedChallenges_;

    std::string generateRandomState() {
        unsigned char bytes[32];
        randombytes_buf(bytes, 32);
        
        std::string result;
        result.reserve(64);
        for (unsigned char b : bytes) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", b);
            result += buf;
        }
        return result;
    }

    std::string urlEncode(const std::string& value) {
        std::string result;
        for (char c : value) {
            if (std::isalnum(static_cast<unsigned char>(c)) || 
                c == '-' || c == '_' || c == '.' || c == '~') {
                result += c;
            } else {
                char buf[4];
                snprintf(buf, sizeof(buf), "%%%02X",
                        static_cast<unsigned char>(c));
                result += buf;
            }
        }
        return result;
    }
};
```

### 7.6.3 Vulnerabilidades Comuns de OAuth 2.0

| Vulnerabilidade | Descrição | Prevenção |
|----------------|-----------|-----------|
| CSRF no fluxo | Atacante injeta código de autorização | State parameter obrigatório |
| Redirect URI manipulation | Redirecionamento para URI maliciosa | Whitelist estrita de URIs |
| Token leakage via referrer | Token em URL aparece no referrer | Usar PKCE, não colocar tokens em URLs |
| Scope escalation | Cliente solicita escopos além do necessário | Validação server-side de scopes |
| Insufficient validation | Token não é verificado adequadamente | Validar audience, issuer, expiração |

---

## 7.7 Authorization: RBAC, ABAC, ACL

### 7.7.1 Role-Based Access Control (RBAC)

RBAC asigna permissões através de roles (papéis). Usuários não recebem permissões diretamente — recebem roles que encapsulam permissões.

```cpp
#include <string>
#include <map>
#include <set>
#include <vector>
#include <functional>
#include <algorithm>
#include <fstream>
#include <chrono>

struct Permission {
    std::string resource;
    std::string action;
    
    bool operator==(const Permission& other) const {
        return resource == other.resource && action == other.action;
    }
    
    bool operator<(const Permission& other) const {
        if (resource != other.resource) return resource < other.resource;
        return action < other.action;
    }
};

struct Role {
    std::string name;
    std::set<Permission> permissions;
    std::set<std::string> parentRoles;  // Hierarquia
};

struct User {
    std::string id;
    std::set<std::string> roles;
};

class RBACManager {
public:
    void addRole(const Role& role) {
        roles_[role.name] = role;
    }

    void assignRole(const std::string& userId, const std::string& roleName) {
        if (users_.find(userId) == users_.end()) {
            User user;
            user.id = userId;
            users_[userId] = user;
        }
        users_[userId].roles.insert(roleName);
    }

    void removeRole(const std::string& userId, const std::string& roleName) {
        if (users_.count(userId)) {
            users_[userId].roles.erase(roleName);
        }
    }

    // Verificar permissão (com herança de roles)
    bool hasPermission(const std::string& userId,
                       const std::string& resource,
                       const std::string& action) {
        if (users_.find(userId) == users_.end()) return false;
        
        Permission perm{resource, action};
        
        for (const auto& roleName : users_[userId].roles) {
            if (checkRolePermission(roleName, perm)) {
                logAccess(userId, resource, action, true);
                return true;
            }
        }
        
        logAccess(userId, resource, action, false);
        return false;
    }

    // Obter todas as permissões de um usuário
    std::set<Permission> getUserPermissions(const std::string& userId) {
        std::set<Permission> allPermissions;
        if (users_.find(userId) == users_.end()) return allPermissions;
        
        for (const auto& roleName : users_[userId].roles) {
            collectRolePermissions(roleName, allPermissions);
        }
        
        return allPermissions;
    }

    // Adicionar role pai (herança)
    void addParentRole(const std::string& childRole,
                       const std::string& parentRole) {
        if (roles_.count(childRole)) {
            roles_[childRole].parentRoles.insert(parentRole);
        }
    }

    // Log de auditoria
    void logAccess(const std::string& userId,
                   const std::string& resource,
                   const std::string& action,
                   bool allowed) {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        
        std::string entry = "[" + std::to_string(time) + "] ";
        entry += "USER=" + userId + " ";
        entry += "RESOURCE=" + resource + " ";
        entry += "ACTION=" + action + " ";
        entry += "RESULT=" + (std::string)(allowed ? "ALLOW" : "DENY");
        
        auditLog_.push_back(entry);
    }

private:
    std::map<std::string, Role> roles_;
    std::map<std::string, User> users_;
    std::vector<std::string> auditLog_;

    bool checkRolePermission(const std::string& roleName,
                              const Permission& perm) {
        if (roles_.find(roleName) == roles_.end()) return false;
        
        const auto& role = roles_[roleName];
        
        // Verificar permissão direta
        if (role.permissions.count(perm)) return true;
        
        // Verificar roles pais (herança)
        for (const auto& parent : role.parentRoles) {
            if (checkRolePermission(parent, perm)) return true;
        }
        
        return false;
    }

    void collectRolePermissions(const std::string& roleName,
                                 std::set<Permission>& collected) {
        if (roles_.find(roleName) == roles_.end()) return;
        
        const auto& role = roles_[roleName];
        collected.insert(role.permissions.begin(), role.permissions.end());
        
        for (const auto& parent : role.parentRoles) {
            collectRolePermissions(parent, collected);
        }
    }
};

// Exemplo de uso
void example_rbac() {
    RBACManager rbac;
    
    // Definir roles
    Role viewer;
    viewer.name = "viewer";
    viewer.permissions = {{"posts", "read"}, {"comments", "read"}};
    rbac.addRole(viewer);
    
    Role editor;
    editor.name = "editor";
    editor.permissions = {{"posts", "write"}, {"comments", "write"}};
    editor.parentRoles = {"viewer"};
    rbac.addRole(editor);
    
    Role admin;
    admin.name = "admin";
    admin.permissions = {{"users", "manage"}, {"settings", "manage"}};
    admin.parentRoles = {"editor"};
    rbac.addRole(admin);
    
    // Atribuir roles
    rbac.assignRole("user1", "editor");
    rbac.assignRole("user2", "admin");
    
    // Verificar permissões
    std::cout << "user1 can read posts: " 
              << rbac.hasPermission("user1", "posts", "read") << std::endl;
    std::cout << "user1 can write posts: " 
              << rbac.hasPermission("user1", "posts", "write") << std::endl;
    std::cout << "user1 can manage users: " 
              << rbac.hasPermission("user1", "users", "manage") << std::endl;
    std::cout << "user2 can manage users: " 
              << rbac.hasPermission("user2", "users", "manage") << std::endl;
}
```

### 7.7.2 Attribute-Based Access Control (ABAC)

ABAC é mais flexível que RBAC, avaliando permissões baseadas em atributos do sujeito, objeto, ambiente e ação.

{% raw %}
```cpp
#include <string>
#include <map>
#include <vector>
#include <functional>
#include <any>
#include <variant>
#include <algorithm>

struct Attribute {
    std::string key;
    std::variant<std::string, int, bool, double> value;
};

struct AccessRequest {
    std::vector<Attribute> subjectAttributes;
    std::vector<Attribute> objectAttributes;
    std::vector<Attribute> environmentAttributes;
    std::string action;
};

struct PolicyRule {
    std::string name;
    std::function<bool(const AccessRequest&)> condition;
    bool effect;  // true = permit, false = deny
    int priority = 0;
};

class ABACEngine {
public:
    void addPolicy(const PolicyRule& policy) {
        policies_.push_back(policy);
    }

    bool evaluate(const AccessRequest& request) {
        std::vector<PolicyRule> applicable;
        
        for (const auto& policy : policies_) {
            if (policy.condition(request)) {
                applicable.push_back(policy);
            }
        }
        
        if (applicable.empty()) {
            return false;  // Deny by default
        }
        
        // Ordenar por prioridade (maior primeiro)
        std::sort(applicable.begin(), applicable.end(),
                  [](const PolicyRule& a, const PolicyRule& b) {
                      return a.priority > b.priority;
                  });
        
        return applicable.front().effect;
    }

    // Helper para obter atributo
    template<typename T>
    static T getAttribute(const std::vector<Attribute>& attrs,
                          const std::string& key,
                          T defaultValue) {
        for (const auto& attr : attrs) {
            if (attr.key == key) {
                if (auto val = std::get_if<T>(&attr.value)) {
                    return *val;
                }
            }
        }
        return defaultValue;
    }

private:
    std::vector<PolicyRule> policies_;
};

// Exemplo: política "somente durante horário comercial"
void example_abac() {
    ABACEngine engine;
    
    // Regra 1: Acesso a dados financeiros requer role "finance"
    PolicyRule financeAccess;
    financeAccess.name = "Finance data access";
    financeAccess.condition = [](const AccessRequest& req) {
        auto role = ABACEngine::getAttribute<std::string>(
            req.subjectAttributes, "role", "");
        auto resource = ABACEngine::getAttribute<std::string>(
            req.objectAttributes, "type", "");
        return resource == "financial_data" && role == "finance";
    };
    financeAccess.effect = true;
    financeAccess.priority = 10;
    engine.addPolicy(financeAccess);
    
    // Regra 2: Negar acesso fora do horário comercial
    PolicyRule businessHours;
    businessHours.name = "Business hours only";
    businessHours.condition = [](const AccessRequest& req) {
        auto hour = ABACEngine::getAttribute<int>(
            req.environmentAttributes, "hour", 12);
        return hour >= 9 && hour <= 17;
    };
    businessHours.effect = true;
    businessHours.priority = 5;
    engine.addPolicy(businessHours);
    
    // Avaliar request
    AccessRequest request;
    request.subjectAttributes = {{"role", std::string("finance")}};
    request.objectAttributes = {{"type", std::string("financial_data")}};
    request.environmentAttributes = {{"hour", 14}};
    request.action = "read";
    
    bool allowed = engine.evaluate(request);
    std::cout << "Access allowed: " << (allowed ? "yes" : "no") << std::endl;
}
```
{% endraw %}

### 7.7.3 Access Control Lists (ACL)

```cpp
#include <string>
#include <map>
#include <set>
#include <vector>
#include <algorithm>

struct ACLRule {
    std::string principal;   // user ou role
    std::string resource;
    std::set<std::string> allowedActions;
    std::set<std::string> deniedActions;  // Deny explícito
};

class ACLManager {
public:
    void addRule(const ACLRule& rule) {
        rules_.push_back(rule);
    }

    bool checkAccess(const std::string& principal,
                     const std::string& resource,
                     const std::string& action) {
        bool allowed = false;
        bool denied = false;
        
        // Primeiro: verificar denies explícitos
        for (const auto& rule : rules_) {
            if (rule.principal == principal && rule.resource == resource) {
                if (rule.deniedActions.count(action)) {
                    denied = true;
                    break;
                }
                if (rule.allowedActions.count(action)) {
                    allowed = true;
                }
            }
        }
        
        // Negar se há deny explícito
        return allowed && !denied;
    }

    // Listar permissões para um principal em um resource
    std::set<std::string> getPermissions(const std::string& principal,
                                         const std::string& resource) {
        std::set<std::string> permissions;
        for (const auto& rule : rules_) {
            if (rule.principal == principal && rule.resource == resource) {
                permissions.insert(rule.allowedActions.begin(),
                                 rule.allowedActions.end());
            }
        }
        return permissions;
    }

private:
    std::vector<ACLRule> rules_;
};
```

### 7.7.4 Capability-Based Security

```cpp
#include <string>
#include <set>
#include <chrono>
#include <map>

struct Capability {
    std::string token;          // Identificador único
    std::string resource;       // Recurso associado
    std::set<std::string> allowedActions;
    std::string owner;          // Quem criou a capability
    std::string grantee;        // Quem recebeu
    std::chrono::system_clock::time_point expiresAt;
    bool revocable = true;
};

class CapabilityManager {
public:
    Capability createCapability(const std::string& resource,
                                 const std::set<std::string>& actions,
                                 const std::string& owner,
                                 const std::string& grantee,
                                 int expirationSeconds = 3600) {
        Capability cap;
        cap.token = generateToken();
        cap.resource = resource;
        cap.allowedActions = actions;
        cap.owner = owner;
        cap.grantee = grantee;
        cap.expiresAt = std::chrono::system_clock::now() +
            std::chrono::seconds(expirationSeconds);
        
        capabilities_[cap.token] = cap;
        return cap;
    }

    bool verifyCapability(const std::string& token,
                          const std::string& action) {
        auto it = capabilities_.find(token);
        if (it == capabilities_.end()) return false;
        
        const auto& cap = it->second;
        
        // Verificar expiração
        if (std::chrono::system_clock::now() > cap.expiresAt) {
            capabilities_.erase(it);
            return false;
        }
        
        return cap.allowedActions.count(action) > 0;
    }

    void revokeCapability(const std::string& token) {
        capabilities_.erase(token);
    }

private:
    std::map<std::string, Capability> capabilities_;

    std::string generateToken() {
        unsigned char bytes[32];
        randombytes_buf(bytes, 32);
        std::string result;
        result.reserve(64);
        for (unsigned char b : bytes) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", b);
            result += buf;
        }
        return result;
    }
};
```

---

## 7.8 Gestão de Senhas e Segredos

### 7.8.1 Geração de Senhas Seguras

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <algorithm>
#include <random>
#include <stdexcept>

class PasswordGenerator {
public:
    struct Config {
        size_t length = 16;
        bool useUppercase = true;
        bool useLowercase = true;
        bool useDigits = true;
        bool useSpecial = true;
        std::string excludedChars;
    };

    explicit PasswordGenerator(Config config = Config{}) : config_(std::move(config)) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    std::string generate() {
        std::string charset;
        
        if (config_.useLowercase)  charset += "abcdefghijklmnopqrstuvwxyz";
        if (config_.useUppercase)  charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        if (config_.useDigits)     charset += "0123456789";
        if (config_.useSpecial)    charset += "!@#$%^&*()_+-=[]{}|;:,.<>?";
        
        // Remover caracteres excluídos
        for (char c : config_.excludedChars) {
            charset.erase(std::remove(charset.begin(), charset.end(), c),
                        charset.end());
        }
        
        if (charset.empty()) {
            throw std::runtime_error("No characters available for password generation");
        }
        
        std::string password;
        password.reserve(config_.length);
        
        // Gerar usando CSPRNG
        std::vector<unsigned char> randomBytes(config_.length);
        randombytes_buf(randomBytes.data(), config_.length);
        
        for (size_t i = 0; i < config_.length; ++i) {
            password += charset[randomBytes[i] % charset.size()];
        }
        
        // Garantir pelo menos um de cada categoria obrigatória
        ensureComplexity(password, charset);
        
        return password;
    }

    // Gerar passphrase (palavras aleatórias)
    std::string generatePassphrase(size_t wordCount = 4,
                                    const std::string& separator = "-") {
        // Lista simplificada — produção deve usar lista maior (Diceware)
        std::vector<std::string> wordlist = {
            "correct", "horse", "battery", "staple", "cloud",
            "ocean", "mountain", "forest", "river", "sunset",
            "galaxy", "nebula", "quantum", "cipher", "matrix",
            "atlas", "cosmos", "prism", "vertex", "nexus",
            "phoenix", "dragon", "kraken", "vortex", "zenith",
            "aurora", "crystal", "shadow", "flame", "storm"
        };
        
        std::vector<unsigned char> randomBytes(wordCount * 2);
        randombytes_buf(randomBytes.data(), wordCount * 2);
        
        std::string passphrase;
        for (size_t i = 0; i < wordCount; ++i) {
            if (i > 0) passphrase += separator;
            uint16_t idx = (static_cast<uint16_t>(randomBytes[i * 2]) << 8) |
                           randomBytes[i * 2 + 1];
            passphrase += wordlist[idx % wordlist.size()];
        }
        
        return passphrase;
    }

private:
    Config config_;

    void ensureComplexity(std::string& password, const std::string& charset) {
        auto hasChar = [&](const std::string& set) -> bool {
            return std::any_of(password.begin(), password.end(),
                [&set](char c) { return set.find(c) != std::string::npos; });
        };
        
        std::string lower = "abcdefghijklmnopqrstuvwxyz";
        std::string upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
        std::string digits = "0123456789";
        std::string special = "!@#$%^&*()_+-=[]{}|;:,.<>?";
        
        if (config_.useLowercase && !hasChar(lower)) {
            replaceRandom(password, charset);
        }
        if (config_.useUppercase && !hasChar(upper)) {
            replaceRandom(password, charset);
        }
        if (config_.useDigits && !hasChar(digits)) {
            replaceRandom(password, charset);
        }
        if (config_.useSpecial && !hasChar(special)) {
            replaceRandom(password, charset);
        }
    }

    void replaceRandom(std::string& password, const std::string& charset) {
        unsigned char idx;
        randombytes_buf(&idx, 1);
        size_t pos = idx % password.size();
        
        unsigned char charIdx;
        randombytes_buf(&charIdx, 1);
        
        // Garantir que o novo caractere atenda ao requisito
        std::string validChars = charset;
        password[pos] = validChars[charIdx % validChars.size()];
    }
};
```

### 7.8.2 Estimador de Força de Senha

```cpp
#include <string>
#include <cmath>
#include <algorithm>
#include <map>

struct StrengthResult {
    double entropy;      // bits de entropia
    int score;           // 0-100
    std::string label;   // Muito fraca, Fraca, Média, Forte, Muito forte
    std::vector<std::string> warnings;
};

class PasswordStrengthEstimator {
public:
    StrengthResult estimate(const std::string& password) const {
        StrengthResult result;
        result.entropy = calculateEntropy(password);
        result.score = calculateScore(password, result.entropy);
        result.label = getLabel(result.score);
        result.warnings = getWarnings(password);
        
        return result;
    }

private:
    double calculateEntropy(const std::string& password) const {
        if (password.empty()) return 0.0;
        
        std::map<char, int> charFreq;
        for (char c : password) {
            charFreq[c]++;
        }
        
        double entropy = 0.0;
        double len = static_cast<double>(password.size());
        
        for (const auto& [c, freq] : charFreq) {
            double p = static_cast<double>(freq) / len;
            entropy -= p * std::log2(p);
        }
        
        entropy *= len;
        
        // Bônus por caracteres únicos
        double uniqueRatio = static_cast<double>(charFreq.size()) / len;
        entropy *= (1.0 + uniqueRatio * 0.2);
        
        return entropy;
    }

    int calculateScore(const std::string& password, double entropy) const {
        int score = 0;
        
        // Base na entropia
        if (entropy >= 80) score += 40;
        else if (entropy >= 60) score += 30;
        else if (entropy >= 40) score += 20;
        else if (entropy >= 20) score += 10;
        
        // Comprimento
        if (password.size() >= 16) score += 20;
        else if (password.size() >= 12) score += 15;
        else if (password.size() >= 8) score += 10;
        else score += 5;
        
        // Complexidade de caracteres
        bool hasUpper = std::any_of(password.begin(), password.end(), ::isupper);
        bool hasLower = std::any_of(password.begin(), password.end(), ::islower);
        bool hasDigit = std::any_of(password.begin(), password.end(), ::isdigit);
        bool hasSpecial = std::any_of(password.begin(), password.end(),
            [](char c) { return !std::isalnum(static_cast<unsigned char>(c)); });
        
        int charTypes = hasUpper + hasLower + hasDigit + hasSpecial;
        score += charTypes * 10;
        
        // Penalidades
        if (isCommonPattern(password)) score -= 30;
        if (hasRepeatingChars(password)) score -= 20;
        if (hasSequentialChars(password)) score -= 15;
        
        return std::max(0, std::min(100, score));
    }

    std::string getLabel(int score) const {
        if (score >= 80) return "Muito Forte";
        if (score >= 60) return "Forte";
        if (score >= 40) return "Media";
        if (score >= 20) return "Fraca";
        return "Muito Fraca";
    }

    std::vector<std::string> getWarnings(const std::string& password) const {
        std::vector<std::string> warnings;
        
        if (password.size() < 8) {
            warnings.push_back("Senha muito curta");
        }
        
        bool hasUpper = std::any_of(password.begin(), password.end(), ::isupper);
        bool hasLower = std::any_of(password.begin(), password.end(), ::islower);
        bool hasDigit = std::any_of(password.begin(), password.end(), ::isdigit);
        
        if (!hasUpper) warnings.push_back("Faltam letras maiusculas");
        if (!hasLower) warnings.push_back("Faltam letras minusculas");
        if (!hasDigit) warnings.push_back("Faltam digitos");
        
        return warnings;
    }

    bool isCommonPattern(const std::string& password) const {
        std::vector<std::string> common = {
            "password", "123456", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "login"
        };
        
        std::string lower = password;
        std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
        
        for (const auto& pattern : common) {
            if (lower.find(pattern) != std::string::npos) {
                return true;
            }
        }
        return false;
    }

    bool hasRepeatingChars(const std::string& password) const {
        for (size_t i = 2; i < password.size(); ++i) {
            if (password[i] == password[i - 1] && 
                password[i] == password[i - 2]) {
                return true;
            }
        }
        return false;
    }

    bool hasSequentialChars(const std::string& password) const {
        for (size_t i = 2; i < password.size(); ++i) {
            if (password[i] == password[i - 1] + 1 && 
                password[i] == password[i - 2] + 2) {
                return true;
            }
        }
        return false;
    }
};
```

### 7.8.3 Gerenciamento de Chaves Secretas

```cpp
#include <sodium.h>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <stdexcept>
#include <chrono>
#include <algorithm>

struct SecretKey {
    std::string name;
    std::vector<unsigned char> key;
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point expiresAt;
    bool rotated = false;
};

class SecretKeyManager {
public:
    SecretKeyManager(const std::string& masterKeyPath) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        loadMasterKey(masterKeyPath);
    }

    // Gerar nova chave secreta
    SecretKey generateKey(const std::string& name,
                          size_t keyLength = 32,
                          int validityDays = 90) {
        SecretKey key;
        key.name = name;
        key.key.resize(keyLength);
        randombytes_buf(key.key.data(), keyLength);
        key.createdAt = std::chrono::system_clock::now();
        key.expiresAt = key.createdAt + std::chrono::hours(validityDays * 24);
        
        keys_[name] = key;
        return key;
    }

    // Criptografar chave para armazenamento
    std::vector<unsigned char> encryptKey(const SecretKey& key) {
        // Usar XChaCha20-Poly1305
        std::vector<unsigned char> nonce(
            crypto_aead_xchacha20poly1305_ietf_NPUBBYTES);
        randombytes_buf(nonce.data(), nonce.size());
        
        std::vector<unsigned char> ciphertext(
            key.key.size() + crypto_aead_xchacha20poly1305_ietf_ABYTES);
        unsigned long long ciphertextLen;
        
        // Encriptar com a master key
        crypto_aead_xchacha20poly1305_ietf_encrypt(
            ciphertext.data(), &ciphertextLen,
            key.key.data(), key.key.size(),
            reinterpret_cast<unsigned char*>(
                const_cast<char*>(key.name.data())),
            key.name.size(),
            nullptr, nonce.data(), masterKey_.data());
        
        // Prepend nonce ao ciphertext
        std::vector<unsigned char> result(nonce.begin(), nonce.end());
        result.insert(result.end(), ciphertext.begin(),
                     ciphertext.begin() + ciphertextLen);
        
        return result;
    }

    // Descriptografar chave
    SecretKey decryptKey(const std::string& name,
                          const std::vector<unsigned char>& encrypted) {
        // Extrair nonce
        size_t nonceLen = crypto_aead_xchacha20poly1305_ietf_NPUBBYTES;
        std::vector<unsigned char> nonce(encrypted.begin(),
                                         encrypted.begin() + nonceLen);
        std::vector<unsigned char> ciphertext(encrypted.begin() + nonceLen,
                                              encrypted.end());
        
        std::vector<unsigned char> plaintext(ciphertext.size());
        unsigned long long plaintextLen;
        
        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), &plaintextLen,
                nullptr,
                ciphertext.data(), ciphertext.size(),
                reinterpret_cast<unsigned char*>(
                    const_cast<char*>(name.data())),
                name.size(),
                nonce.data(), masterKey_.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }
        
        SecretKey key;
        key.name = name;
        key.key.assign(plaintext.begin(),
                      plaintext.begin() + plaintextLen);
        
        return key;
    }

    // Rotação de chave
    void rotateKey(const std::string& name) {
        if (keys_.count(name)) {
            keys_[name].rotated = true;
        }
        generateKey(name);
    }

    // Verificar chaves expiradas
    std::vector<std::string> getExpiredKeys() const {
        std::vector<std::string> expired;
        auto now = std::chrono::system_clock::now();
        
        for (const auto& [name, key] : keys_) {
            if (now > key.expiresAt) {
                expired.push_back(name);
            }
        }
        
        return expired;
    }

private:
    std::map<std::string, SecretKey> keys_;
    std::vector<unsigned char> masterKey_;

    void loadMasterKey(const std::string& path) {
        std::ifstream file(path, std::ios::binary);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open master key file");
        }
        
        masterKey_.assign(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>());
        
        if (masterKey_.size() != crypto_aead_xchacha20poly1305_ietf_KEYBYTES) {
            throw std::runtime_error("Invalid master key size");
        }
    }
};
```

### 7.8.4 Classe SecureString Completa

```cpp
#include <sodium.h>
#include <string>
#include <cstring>
#include <sys/mman.h>
#include <stdexcept>

class SecureString {
public:
    SecureString() : data_(nullptr), size_(0), capacity_(0) {}

    explicit SecureString(const char* str) : SecureString() {
        assign(str);
    }

    SecureString(const std::string& str) : SecureString() {
        assign(str.c_str());
    }

    ~SecureString() {
        clear();
    }

    // Construtor de movimento
    SecureString(SecureString&& other) noexcept
        : data_(other.data_), size_(other.size_), 
          capacity_(other.capacity_) {
        other.data_ = nullptr;
        other.size_ = 0;
        other.capacity_ = 0;
    }

    SecureString& operator=(SecureString&& other) noexcept {
        if (this != &other) {
            clear();
            data_ = other.data_;
            size_ = other.size_;
            capacity_ = other.capacity_;
            other.data_ = nullptr;
            other.size_ = 0;
            other.capacity_ = 0;
        }
        return *this;
    }

    // Desabilitar cópia
    SecureString(const SecureString&) = delete;
    SecureString& operator=(const SecureString&) = delete;

    void assign(const char* str) {
        clear();
        size_ = std::strlen(str);
        capacity_ = size_ + 1;
        
        data_ = static_cast<char*>(std::malloc(capacity_));
        if (!data_) throw std::runtime_error("Allocation failed");
        
        std::memcpy(data_, str, capacity_);
        
        // Travar na memória física
        mlock(data_, capacity_);
    }

    const char* c_str() const {
        return data_ ? data_ : "";
    }

    size_t size() const {
        return size_;
    }

    bool empty() const {
        return size_ == 0;
    }

    void clear() {
        if (data_) {
            // Limpeza segura — impede otimização do compilador
            sodium_memzero(data_, capacity_);
            munlock(data_, capacity_);
            std::free(data_);
            data_ = nullptr;
            size_ = 0;
            capacity_ = 0;
        }
    }

    // Comparação de tempo constante
    bool operator==(const SecureString& other) const {
        if (size_ != other.size_) return false;
        return sodium_memcmp(data_, other.data_, size_) == 0;
    }

    bool operator!=(const SecureString& other) const {
        return !(*this == other);
    }

    // Obter como std::string (cuidado: expõe em memória não protegida)
    std::string toString() const {
        return data_ ? std::string(data_, size_) : std::string();
    }

private:
    char* data_;
    size_t size_;
    size_t capacity_;
};

// Exemplo de uso
void example_secure_string() {
    {
        SecureString password("MyStr0ng!P@ssw0rd");
        
        // Usar para hashing
        std::string hashed = hashPassword(password);
        
        //密码 em memória é protegida
        // Ao sair do escopo, memória é limpa automaticamente
    }
    // Neste ponto, a senha foi zerada da memória
}
```

---

## 7.9 Autenticação em Protocolos de Rede

### 7.9.1 mTLS (Mutual TLS)

mTLS requer que tanto o cliente quanto o servidor se autentiquem via certificados:

```cpp
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <string>
#include <stdexcept>
#include <functional>

class MTLSServer {
public:
    MTLSServer(const std::string& certFile,
               const std::string& keyFile,
               const std::string& caFile) {
        SSL_library_init();
        SSL_load_error_strings();
        
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) {
            throw std::runtime_error("Failed to create SSL context");
        }
        
        // Configurar certificado do servidor
        if (SSL_CTX_use_certificate_chain_file(ctx_, certFile.c_str()) != 1) {
            throw std::runtime_error("Failed to load server certificate");
        }
        
        // Configurar chave privada
        if (SSL_CTX_use_PrivateKey_file(ctx_, keyFile.c_str(),
                                        SSL_FILETYPE_PEM) != 1) {
            throw std::runtime_error("Failed to load private key");
        }
        
        // Configurar CA para verificar certificados de clientes
        if (SSL_CTX_load_verify_locations(ctx_, caFile.c_str(), nullptr) != 1) {
            throw std::runtime_error("Failed to load CA certificate");
        }
        
        // HABILITAR VERIFICAÇÃO DE CERTIFICADO DO CLIENTE
        SSL_CTX_set_verify(ctx_,
            SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
            verifyClientCertificate);
        
        // Configurar protocolos seguros
        SSL_CTX_set_min_proto_version(ctx_, TLS1_2_VERSION);
        
        // Configurar cipher suites
        SSL_CTX_set_cipher_list(ctx_,
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS");
    }

    ~MTLSServer() {
        SSL_CTX_free(ctx_);
    }

    struct ClientInfo {
        bool verified;
        std::string commonName;
        std::string organization;
        std::string serialNumber;
    };

    // Aceitar conexão e verificar cliente
    ClientInfo acceptConnection(int clientSocket) {
        ClientInfo info;
        info.verified = false;
        
        SSL* ssl = SSL_new(ctx_);
        SSL_set_fd(ssl, clientSocket);
        
        if (SSL_accept(ssl) <= 0) {
            SSL_free(ssl);
            return info;
        }
        
        // Obter certificado do cliente
        X509* peerCert = SSL_get_peer_certificate(ssl);
        if (peerCert) {
            // Verificar resultado da verificação
            long verifyResult = SSL_get_verify_result(ssl);
            if (verifyResult == X509_V_OK) {
                info.verified = true;
                
                // Extrair informações do certificado
                X509_NAME* subject = X509_get_subject_name(peerCert);
                char commonName[256];
                X509_NAME_get_text_by_NID(subject, NID_commonName,
                                         commonName, sizeof(commonName));
                info.commonName = commonName;
                
                char organization[256];
                X509_NAME_get_text_by_NID(subject, NID_organizationName,
                                         organization, sizeof(organization));
                info.organization = organization;
                
                ASN1_INTEGER* serial = X509_get_serialNumber(peerCert);
                BIGNUM* bn = ASN1_INTEGER_to_BN(serial, nullptr);
                char* serialStr = BN_bn2dec(bn);
                info.serialNumber = serialStr;
                OPENSSL_free(serialStr);
                BN_free(bn);
            }
            
            X509_free(peerCert);
        }
        
        SSL_free(ssl);
        return info;
    }

private:
    SSL_CTX* ctx_;

    static int verifyClientCertificate(int preverifyOk, X509_STORE_CTX* ctx) {
        if (!preverifyOk) {
            return 0;  // Rejeitar
        }
        
        X509* cert = X509_STORE_CTX_get_current_cert(ctx);
        int depth = X509_STORE_CTX_get_error_depth(ctx);
        
        // Verificações adicionais podem ser feitas aqui:
        // - Verificar CRL (Certificate Revocation List)
        // - Verificar OCSP
        // - Verificar campos específicos do certificado
        
        return 1;
    }
};
```

### 7.9.2 Autenticação HMAC para APIs

```cpp
#include <sodium.h>
#include <string>
#include <chrono>
#include <sstream>
#include <iomanip>
#include <map>

class HMACAPIAuth {
public:
    HMACAPIAuth(const std::string& apiSecret) : apiSecret_(apiSecret) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    struct AuthHeader {
        std::string keyId;
        std::string signature;
        std::string timestamp;
    };

    // Gerar header de autenticação
    AuthHeader signRequest(const std::string& apiKey,
                           const std::string& method,
                           const std::string& path,
                           const std::string& body = "") {
        AuthHeader header;
        header.keyId = apiKey;
        
        auto now = std::chrono::system_clock::now();
        auto timeSinceEpoch = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        header.timestamp = std::to_string(timeSinceEpoch);
        
        // String a ser assinada
        std::string stringToSign = method + "\n" + path + "\n" +
                                    header.timestamp + "\n" + body;
        
        // HMAC-SHA256
        unsigned char hmac[CRYPTO_AUTH_HMACSHA256_BYTES];
        crypto_auth_hmacsha256_state state;
        crypto_auth_hmacsha256_init(&state,
            reinterpret_cast<const unsigned char*>(apiSecret_.data()),
            apiSecret_.size());
        crypto_auth_hmacsha256_update(&state,
            reinterpret_cast<const unsigned char*>(stringToSign.data()),
            stringToSign.size());
        crypto_auth_hmacsha256_final(&state, hmac);
        
        // Codificar em hex
        std::ostringstream oss;
        for (int i = 0; i < CRYPTO_AUTH_HMACSHA256_BYTES; ++i) {
            oss << std::hex << std::setfill('0') << std::setw(2)
                << static_cast<int>(hmac[i]);
        }
        header.signature = oss.str();
        
        return header;
    }

    // Verificar assinatura de request
    bool verifyRequest(const std::string& apiKey,
                       const std::string& method,
                       const std::string& path,
                       const std::string& body,
                       const std::string& timestamp,
                       const std::string& signature,
                       int maxAgeSeconds = 300) {
        // Verificar timestamp (replay protection)
        auto now = std::chrono::system_clock::now();
        auto timeSinceEpoch = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        auto requestTime = std::stoll(timestamp);
        
        if (std::abs(timeSinceEpoch - requestTime) > maxAgeSeconds) {
            return false;  // Request muito antigo ou futuro
        }
        
        // Recalcular assinatura
        AuthHeader expected = signRequest(apiKey, method, path, body);
        
        // Comparação de tempo constante
        return sodium_memcmp(signature.data(), expected.signature.data(),
                           std::min(signature.size(),
                                   expected.signature.size())) == 0 &&
               signature.size() == expected.signature.size();
    }

private:
    std::string apiSecret_;
};
```

### 7.9.3 Estudo de Caso: LastPass (2022)

Em agosto de 2022, o LastPass sofreu um ataque que resultou no roubo de **cripto-vaults** de usuários. Em dezembro, foi revelado que os dados roubados incluíam cópias criptografadas de senhas.

**O que deu errado:** O LastPass usou PBKDF2 com **100.100 iterações** (apesar de soar alto, a derivação de chave para os vaults locais usava apenas uma camada de proteção). Quando um atacante obteve acesso aos backups criptografados, puderam realizar força bruta offline. Chaves derivadas de senha para criptografar dados do vault deveriam usar parâmetros mais robustos ou autenticação multi-fator no nível de criptografia.

```cpp
// PADRÃO SEGURO: Derivação de chave robusta
// Evitar os erros do LastPass usando Argon2id com parâmetros fortes
#include <sodium.h>
#include <string>
#include <vector>

class SecureKeyDerivation {
public:
    struct DerivedKey {
        std::vector<unsigned char> key;
        std::vector<unsigned char> salt;
    };

    static DerivedKey deriveFromPassword(
            const std::string& password,
            size_t keyLength = 32,
            unsigned long long opslimit = crypto_pwhash_OPSLIMIT_SENSITIVE,
            size_t memlimit = crypto_pwhash_MEMLIMIT_SENSITIVE) {
        
        DerivedKey result;
        result.salt.resize(crypto_pwhash_SALTBYTES);
        randombytes_buf(result.salt.data(), result.salt.size());
        
        result.key.resize(keyLength);
        
        if (crypto_pwhash(
                result.key.data(), keyLength,
                password.c_str(), password.size(),
                result.salt.data(),
                opslimit, memlimit,
                crypto_pwhash_ALG_ARGON2ID13) != 0) {
            throw std::runtime_error("Key derivation failed");
        }
        
        return result;
    }

    static bool verifyDerivedKey(
            const std::string& password,
            const std::vector<unsigned char>& salt,
            const std::vector<unsigned char>& expectedKey,
            unsigned long long opslimit = crypto_pwhash_OPSLIMIT_SENSITIVE,
            size_t memlimit = crypto_pwhash_MEMLIMIT_SENSITIVE) {
        
        std::vector<unsigned char> key(expectedKey.size());
        
        if (crypto_pwhash(
                key.data(), key.size(),
                password.c_str(), password.size(),
                salt.data(),
                opslimit, memlimit,
                crypto_pwhash_ALG_ARGON2ID13) != 0) {
            return false;
        }
        
        return sodium_memcmp(key.data(), expectedKey.data(),
                           key.size()) == 0;
    }
};
```

---

## 7.10 Exemplo Completo: Servidor de Autenticação

```cpp
#include <sodium.h>
#include <string>
#include <map>
#include <vector>
#include <memory>
#include <mutex>
#include <chrono>
#include <functional>
#include <sstream>
#include <algorithm>
#include <iostream>
#include <random>

// ============================================================================
// Estruturas de dados
// ============================================================================

struct User {
    std::string id;
    std::string username;
    std::string email;
    std::string passwordHash;
    std::vector<unsigned char> mfaSecret;
    bool mfaEnabled = false;
    std::vector<std::string> roles;
    std::chrono::system_clock::time_point createdAt;
    bool locked = false;
    int failedLoginAttempts = 0;
};

struct Session {
    std::string sessionId;
    std::string userId;
    std::string ipAddress;
    std::string userAgent;
    bool mfaVerified = false;
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point lastAccessed;
    std::chrono::seconds timeout{3600};
};

struct AuthResponse {
    bool success;
    std::string message;
    std::string accessToken;
    std::string refreshToken;
    bool mfaRequired = false;
};

// ============================================================================
// Servidor de Autenticação Completo
// ============================================================================

class AuthenticationServer {
public:
    AuthenticationServer() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        jwtManager_ = std::make_unique<JWTManager>(
            "your-256-bit-secret-key-here-must-be-32-bytes!");
    }

    // -----------------------------------------------------------------------
    // Registro de usuário
    // -----------------------------------------------------------------------
    AuthResponse registerUser(const std::string& username,
                               const std::string& email,
                               const std::string& password) {
        AuthResponse response;
        
        // Verificar se usuário já existe
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& [id, user] : users_) {
            if (user.username == username || user.email == email) {
                response.success = false;
                response.message = "Username or email already exists";
                return response;
            }
        }
        
        // Validar política de senha
        PasswordPolicy policy;
        PasswordValidator validator(policy);
        auto policyResult = validator.validate(password);
        if (!policyResult.valid) {
            response.success = false;
            response.message = "Password does not meet policy requirements";
            return response;
        }
        
        // Hash da senha com Argon2id
        SecurePasswordHasher hasher;
        std::string passwordHash = hasher.hashPassword(password);
        
        // Criar usuário
        User user;
        user.id = generateId();
        user.username = username;
        user.email = email;
        user.passwordHash = passwordHash;
        user.roles = {"user"};
        user.createdAt = std::chrono::system_clock::now();
        
        users_[user.id] = user;
        
        response.success = true;
        response.message = "User registered successfully";
        logEvent("REGISTER", user.id, "User registered");
        
        return response;
    }

    // -----------------------------------------------------------------------
    // Login
    // -----------------------------------------------------------------------
    AuthResponse login(const std::string& username,
                       const std::string& password,
                       const std::string& ipAddress,
                       const std::string& userAgent) {
        AuthResponse response;
        
        // Buscar usuário
        User* user = nullptr;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            for (auto& [id, u] : users_) {
                if (u.username == username) {
                    user = &u;
                    break;
                }
            }
        }
        
        if (!user) {
            response.success = false;
            response.message = "Invalid credentials";
            logEvent("LOGIN_FAILED", "unknown",
                    "Unknown user: " + username);
            return response;
        }
        
        // Verificar se conta está bloqueada
        if (user->locked) {
            response.success = false;
            response.message = "Account is locked";
            logEvent("LOGIN_FAILED", user->id, "Account locked");
            return response;
        }
        
        // Verificar senha (Argon2id)
        SecurePasswordHasher hasher;
        if (!hasher.verifyPassword(password, user->passwordHash)) {
            user->failedLoginAttempts++;
            if (user->failedLoginAttempts >= 5) {
                user->locked = true;
                logEvent("ACCOUNT_LOCKED", user->id,
                        "Too many failed attempts");
            }
            response.success = false;
            response.message = "Invalid credentials";
            logEvent("LOGIN_FAILED", user->id,
                    "Invalid password, attempts: " + 
                    std::to_string(user->failedLoginAttempts));
            return response;
        }
        
        // Login bem-sucedido — resetar tentativas
        user->failedLoginAttempts = 0;
        
        // Criar sessão
        std::string sessionId = createSession(user->id, ipAddress, userAgent);
        
        // Gerar tokens JWT
        std::map<std::string, std::string> claims;
        claims["sub"] = user->id;
        claims["username"] = user->username;
        claims["sid"] = sessionId;
        
        // Adicionar roles ao token
        std::string rolesStr;
        for (const auto& role : user->roles) {
            if (!rolesStr.empty()) rolesStr += ",";
            rolesStr += role;
        }
        claims["roles"] = rolesStr;
        
        response.accessToken = jwtManager_->createToken(claims, 3600);
        response.refreshToken = jwtManager_->createRefreshToken(user->id);
        
        // Verificar se MFA é necessário
        if (user->mfaEnabled) {
            response.mfaRequired = true;
            response.message = "MFA verification required";
        } else {
            response.success = true;
            response.message = "Login successful";
        }
        
        logEvent("LOGIN_SUCCESS", user->id,
                "From IP: " + ipAddress);
        
        return response;
    }

    // -----------------------------------------------------------------------
    // Verificação de MFA
    // -----------------------------------------------------------------------
    AuthResponse verifyMFA(const std::string& userId,
                           const std::string& mfaCode,
                           const std::string& sessionId) {
        AuthResponse response;
        
        std::lock_guard<std::mutex> lock(mutex_);
        auto userIt = users_.find(userId);
        if (userIt == users_.end()) {
            response.success = false;
            response.message = "User not found";
            return response;
        }
        
        auto& user = userIt->second;
        
        if (!user.mfaEnabled || user.mfaSecret.empty()) {
            response.success = false;
            response.message = "MFA not configured";
            return response;
        }
        
        TOTPGenerator totp(user.mfaSecret);
        if (!totp.verify(mfaCode)) {
            response.success = false;
            response.message = "Invalid MFA code";
            logEvent("MFA_FAILED", userId, "Invalid code");
            return response;
        }
        
        // Marcar sessão como MFA verificada
        auto sessionIt = sessions_.find(sessionId);
        if (sessionIt != sessions_.end()) {
            sessionIt->second.mfaVerified = true;
        }
        
        // Gerar novo access token com mfa_verified claim
        std::map<std::string, std::string> claims;
        claims["sub"] = userId;
        claims["username"] = user.username;
        claims["sid"] = sessionId;
        claims["mfa_verified"] = "true";
        
        std::string rolesStr;
        for (const auto& role : user.roles) {
            if (!rolesStr.empty()) rolesStr += ",";
            rolesStr += role;
        }
        claims["roles"] = rolesStr;
        
        response.accessToken = jwtManager_->createToken(claims, 3600);
        response.success = true;
        response.message = "MFA verified successfully";
        
        logEvent("MFA_SUCCESS", userId, "Code verified");
        
        return response;
    }

    // -----------------------------------------------------------------------
    // Enrollment de MFA
    // -----------------------------------------------------------------------
    struct MFAEnrollment {
        std::string secret;  // Base32 encoded
        std::string qrCodeURI;
        std::vector<std::string> backupCodes;
    };

    MFAEnrollment enrollMFA(const std::string& userId) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = users_.find(userId);
        if (it == users_.end()) {
            throw std::runtime_error("User not found");
        }
        
        auto& user = it->second;
        
        // Gerar segredo TOTP
        user.mfaSecret = TOTPGenerator::generateSecret();
        
        // Gerar URI para QR code
        TOTPGenerator totp(user.mfaSecret);
        std::string uri = totp.getURI("DevSecurity", user.username);
        
        // Gerar códigos de backup
        BackupCodeGenerator backupGen;
        auto codes = backupGen.generate(10);
        
        MFAEnrollment enrollment;
        enrollment.qrCodeURI = uri;
        for (const auto& code : codes) {
            enrollment.backupCodes.push_back(code.code);
        }
        
        logEvent("MFA_ENROLLED", userId, "MFA enrollment initiated");
        
        return enrollment;
    }

    // -----------------------------------------------------------------------
    // Ativar MFA (após verificação do primeiro código)
    // -----------------------------------------------------------------------
    bool activateMFA(const std::string& userId,
                     const std::string& verificationCode) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = users_.find(userId);
        if (it == users_.end()) return false;
        
        TOTPGenerator totp(it->second.mfaSecret);
        if (totp.verify(verificationCode)) {
            it->second.mfaEnabled = true;
            logEvent("MFA_ACTIVATED", userId, "MFA enabled");
            return true;
        }
        
        return false;
    }

    // -----------------------------------------------------------------------
    // Middleware de autorização
    // -----------------------------------------------------------------------
    bool authorize(const std::string& userId,
                   const std::string& resource,
                   const std::string& action) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = users_.find(userId);
        if (it == users_.end()) return false;
        
        // RBAC simples
        for (const auto& role : it->second.roles) {
            if (checkPermission(role, resource, action)) {
                return true;
            }
        }
        
        logEvent("ACCESS_DENIED", userId,
                resource + ":" + action);
        return false;
    }

    // -----------------------------------------------------------------------
    // Refresh token
    // -----------------------------------------------------------------------
    AuthResponse refreshToken(const std::string& refreshToken) {
        AuthResponse response;
        
        auto result = jwtManager_->verifyToken(refreshToken);
        if (!result.valid || result.claims["type"] != "refresh") {
            response.success = false;
            response.message = "Invalid refresh token";
            return response;
        }
        
        std::string userId = result.claims["sub"];
        
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = users_.find(userId);
        if (it == users_.end()) {
            response.success = false;
            response.message = "User not found";
            return response;
        }
        
        const auto& user = it->second;
        
        // Gerar novos tokens
        std::map<std::string, std::string> claims;
        claims["sub"] = user.id;
        claims["username"] = user.username;
        
        std::string rolesStr;
        for (const auto& role : user.roles) {
            if (!rolesStr.empty()) rolesStr += ",";
            rolesStr += role;
        }
        claims["roles"] = rolesStr;
        
        response.accessToken = jwtManager_->createToken(claims, 3600);
        response.refreshToken = jwtManager_->createRefreshToken(user.id);
        response.success = true;
        response.message = "Tokens refreshed";
        
        logEvent("TOKEN_REFRESHED", userId, "New tokens issued");
        
        return response;
    }

    // -----------------------------------------------------------------------
    // Logout
    // -----------------------------------------------------------------------
    void logout(const std::string& sessionId) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = sessions_.find(sessionId);
        if (it != sessions_.end()) {
            logEvent("LOGOUT", it->second.userId, "Session invalidated");
            sessions_.erase(it);
        }
    }

    // -----------------------------------------------------------------------
    // Log de auditoria
    // -----------------------------------------------------------------------
    struct AuditEntry {
        std::string timestamp;
        std::string event;
        std::string userId;
        std::string details;
    };

    std::vector<AuditEntry> getAuditLog() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return auditLog_;
    }

private:
    std::map<std::string, User> users_;
    std::map<std::string, Session> sessions_;
    std::vector<AuditEntry> auditLog_;
    std::unique_ptr<JWTManager> jwtManager_;
    mutable std::mutex mutex_;

    std::string generateId() {
        unsigned char bytes[16];
        randombytes_buf(bytes, 16);
        std::string result;
        result.reserve(32);
        for (unsigned char b : bytes) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", b);
            result += buf;
        }
        return result;
    }

    std::string createSession(const std::string& userId,
                               const std::string& ipAddress,
                               const std::string& userAgent) {
        Session session;
        session.sessionId = generateId();
        session.userId = userId;
        session.ipAddress = ipAddress;
        session.userAgent = userAgent;
        session.createdAt = std::chrono::system_clock::now();
        session.lastAccessed = session.createdAt;
        
        sessions_[session.sessionId] = session;
        return session.sessionId;
    }

    bool checkPermission(const std::string& role,
                         const std::string& resource,
                         const std::string& action) {
        // RBAC simples — em produção, usar RBACManager
        if (role == "admin") return true;
        if (role == "user" && action == "read") return true;
        if (role == "user" && resource == "profile") return true;
        if (role == "editor" && (action == "read" || action == "write")) {
            return resource == "posts" || resource == "comments";
        }
        return false;
    }

    void logEvent(const std::string& event,
                  const std::string& userId,
                  const std::string& details) {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::duration_cast<std::chrono::seconds>(
            now.time_since_epoch()).count();
        
        AuditEntry entry;
        entry.timestamp = std::to_string(time);
        entry.event = event;
        entry.userId = userId;
        entry.details = details;
        
        auditLog_.push_back(entry);
    }
};

// ============================================================================
// Exemplo de uso do servidor completo
// ============================================================================

void example_authentication_server() {
    AuthenticationServer server;
    
    // 1. Registrar usuário
    std::cout << "=== Registro ===" << std::endl;
    auto regResult = server.registerUser(
        "joao_silva",
        "joao@example.com",
        "MyStr0ng!P@ssw0rd#2024");
    std::cout << regResult.message << std::endl;
    
    // 2. Login
    std::cout << "\n=== Login ===" << std::endl;
    auto loginResult = server.login(
        "joao_silva",
        "MyStr0ng!P@ssw0rd#2024",
        "192.168.1.100",
        "Mozilla/5.0");
    std::cout << loginResult.message << std::endl;
    std::cout << "Access Token: " << loginResult.accessToken.substr(0, 50)
              << "..." << std::endl;
    
    // 3. Enrollment de MFA
    std::cout << "\n=== MFA Enrollment ===" << std::endl;
    auto enrollment = server.enrollMFA("user_id_from_login");
    std::cout << "Scan QR code URI: " << enrollment.qrCodeURI << std::endl;
    std::cout << "Backup codes:" << std::endl;
    for (const auto& code : enrollment.backupCodes) {
        std::cout << "  " << code << std::endl;
    }
    
    // 4. Verificação de autorização
    std::cout << "\n=== Autorizacao ===" << std::endl;
    bool canRead = server.authorize("user_id", "posts", "read");
    bool canDelete = server.authorize("user_id", "posts", "delete");
    std::cout << "Can read posts: " << (canRead ? "yes" : "no") << std::endl;
    std::cout << "Can delete posts: " << (canDelete ? "yes" : "no") << std::endl;
    
    // 5. Refresh token
    std::cout << "\n=== Token Refresh ===" << std::endl;
    auto refreshResult = server.refreshToken(loginResult.refreshToken);
    std::cout << refreshResult.message << std::endl;
    
    // 6. Audit log
    std::cout << "\n=== Audit Log ===" << std::endl;
    auto log = server.getAuditLog();
    for (const auto& entry : log) {
        std::cout << "[" << entry.timestamp << "] " << entry.event
                  << " - " << entry.userId << " - " << entry.details
                  << std::endl;
    }
}
```

---

## 7.11 Referências

1. **OWASP Authentication Cheat Sheet** — https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
2. **RFC 6238** — TOTP: Time-Based One-Time Password Algorithm
3. **RFC 4226** — HOTP: HMAC-Based One-Time Password Algorithm
4. **RFC 7519** — JSON Web Token (JWT)
5. **RFC 7518** — JSON Web Algorithms (JWA)
6. **RFC 7636** — Proof Key for Code Exchange (PKCE)
7. **RFC 6749** — The OAuth 2.0 Authorization Framework
8. **RFC 6750** — Bearer Token Usage
9. **Argon2** — https://argon2.online/ — Password Hashing Competition
10. **libsodium** — https://libsodium.gitbook.io/ — Modern and easy-to-use crypto library
11. **NIST SP 800-63B** — Digital Identity Guidelines (Authentication and Lifecycle Management)
12. **FIDO2/WebAuthn** — https://fidoalliance.org/fido2/
13. **Adobe Password Breach (2013)** — Análise do uso de 3DES em modo ECB
14. **LinkedIn Breach (2012)** — SHA-1 sem salt em 117 milhões de contas
15. **Yahoo Breach (2013-2014)** — 3 bilhões de contas com hash fraco
16. **Colonial Pipeline (2021)** — Ausência de MFA em VPN corporativa
17. **LastPass Breach (2022)** — Derivação de chave inadequada em cripto-vaults
18. **Okta Compromise (2023)** — Roubo de tokens de sessão via conta de suporte
19. **JWT 'none' Algorithm Attack** — https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/
20. **OAuth 2.0 Security Best Current Practice** — RFC 9700

---

## Resumo do Capítulo

| Conceito | Padrão Recomendado | Padrão a Evitar |
|----------|-------------------|-----------------|
| Password Hashing | Argon2id, bcrypt, scrypt | MD5, SHA-1, SHA-256 |
| MFA | TOTP (RFC 6238), FIDO2 | SMS (SIM swap risk) |
| JWT Signing | HMAC-SHA256, RSA, ECDSA | 'none' algorithm |
| Session Tokens | CSPRNG, 128+ bits entropy | Timestamps previsíveis |
| Key Derivation | Argon2id, PBKDF2 (100k+ iters) | bcrypt com custo baixo |
| API Auth | HMAC com timestamp | API keys em URLs |
| TLS | mTLS para zero trust | Certificados auto-assinados |

> **Lembre-se:** Segurança não é um produto, é um processo. As melhores bibliotecas do mundo não protegem contra más decisões de arquitetura. Entenda os fundamentos antes de implementar as soluções.
---

*[Capítulo anterior: 06 — Validacao De Entrada E Sanitizacao](06-validacao-de-entrada-e-sanitizacao.md)*
*[Próximo capítulo: 08 — Criptografia E Chaves](08-cRIPTografia-e-chaves.md)*
