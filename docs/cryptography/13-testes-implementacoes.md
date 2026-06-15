---
layout: default
title: "13-testes-implementacoes"
---

# Capítulo 13: Testes de Implementações Criptográficas

> *"Testes não provam ausência de bugs — mas a ausência de testes prova ausência de confiança."*

---

## Objetivos de Aprendizado

1. Projetar e implementar suites de testes para implementações criptográficas
2. Aplicar Known-Answer Tests (KAT) com vetores de referência NIST
3. Usar differential testing entre bibliotecas para encontrar inconsistências
4. Configurar fuzzing estruturado para funções criptográficas com libFuzzer e AFL++
5. Implementar verificação de constant-time em testes automatizados
6. Documentar e analisar CVE-2022-4304 como estudo de caso de side-channel em testes

---

## 13.1 Por Que Testar Implementações Criptográficas?

Implementações criptográficas são differentes de software convencional. Um bug em um CRUD pode causar perda de dados. Um bug em criptografia pode causar:

- **Violação de confidencialidade**: Chaves privadas expostas
- **Violação de integridade**: Assinaturas falsas aceitas
- **Violação de autenticação**: Acesso não autorizado

A natureza dos bugs criptográficos é especialmente perigosa porque:
1. **Silenciosos**: Um timing side-channel não gera erro, warning ou crash
2 **Invisíveis**: Código pode compilar e funcionar perfeitamente, mas ser vulnerável
3. **Catastróficos**: Um único bug pode comprometer todo o sistema

### Taxonomia de Bugs Criptográficos

| Tipo | Exemplo | Detectável por Testes Convencionais? |
|------|---------|-------------------------------------|
| Logic bug | Wrong padding check | Sim (unit tests) |
| Side-channel | Timing leak | Não (requer análise especializada) |
| Memory safety | Buffer overflow | Parcialmente (ASan) |
| Key generation | Weak randomness | Não (requer análise de entropia) |
| Protocol flaw | Missing authentication | Depende (protocol tests) |
| Implementation flaw | Incorrect modular arithmetic | Sim (KAT vectors) |

---

## 13.2 Known-Answer Tests (KAT)

### 13.2.1 Conceito

KAT são testes que verificam se uma implementação produz os mesmos resultados que um vetor de teste conhecido e validado. São o primeiro nível de qualidade para qualquer implementação criptográfica.

**Fluxo:**
```
Input conhecido → Implementação → Output gerado → Comparar com Output esperado
```

### 13.2.2 Vetores NIST

O NIST publica vetores de teste oficiais para algoritmos padronizados:

| Algoritmo | Padrão | Vetores de Teste | Fonte |
|-----------|--------|-----------------|-------|
| AES | FIPS 197 | Known-answer, variable-key, known-answer-forum | NIST CAVP |
| SHA-256 | FIPS 180-4 | Short/long messages | NIST CAVP |
| HMAC-SHA256 | FIPS 198 | Varias chaves/tamanhos | NIST CAVP |
| ECDSA | FIPS 186-4 | Fallback, partial, PKV | NIST CAVP |
| ChaCha20-Poly1305 | RFC 8439 | Test vectors do RFC | RFC |
| X25519 | RFC 7748 | Test vectors | RFC |
| Ed25519 | RFC 8032 | Test vectors | RFC |

### 13.2.3 Exemplo: KAT para AES-256-GCM

```cpp
#include <openssl/evp.h>
#include <iostream>
#include <vector>
#include <cassert>
#include <iomanip>

struct GCMTestCase {
    std::vector<uint8_t> key;
    std::vector<uint8_t> iv;
    std::vector<uint8_t> plaintext;
    std::vector<uint8_t> aad;
    std::vector<uint8_t> expected_ciphertext;
    std::vector<uint8_t> expected_tag;
};

bool test_aes_256_gcm(const GCMTestCase& tc) {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return false;
    
    int len = 0;
    int ciphertext_len = 0;
    std::vector<uint8_t> ciphertext(tc.plaintext.size() + 16);
    std::vector<uint8_t> tag(16);
    
    // Encryption
    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) != 1)
        goto error;
    
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, tc.iv.size(), nullptr) != 1)
        goto error;
    
    if (EVP_EncryptInit_ex(ctx, nullptr, nullptr, tc.key.data(), tc.iv.data()) != 1)
        goto error;
    
    if (tc.aad.size() > 0) {
        if (EVP_EncryptUpdate(ctx, nullptr, &len, tc.aad.data(), tc.aad.size()) != 1)
            goto error;
    }
    
    if (EVP_EncryptUpdate(ctx, ciphertext.data(), &len, 
                           tc.plaintext.data(), tc.plaintext.size()) != 1)
        goto error;
    ciphertext_len = len;
    
    if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len) != 1)
        goto error;
    ciphertext_len += len;
    
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data()) != 1)
        goto error;
    
    ciphertext.resize(ciphertext_len);
    
    // Comparar
    bool ct_ok = (ciphertext == tc.expected_ciphertext);
    bool tag_ok = (tag == tc.expected_tag);
    
    EVP_CIPHER_CTX_free(ctx);
    return ct_ok && tag_ok;

error:
    EVP_CIPHER_CTX_free(ctx);
    return false;
}

std::vector<uint8_t> hex_to_bytes(const std::string& hex) {
    std::vector<uint8_t> bytes;
    for (size_t i = 0; i < hex.size(); i += 2) {
        bytes.push_back(static_cast<uint8_t>(
            std::stoi(hex.substr(i, 2), nullptr, 16)));
    }
    return bytes;
}

int main() {
    // RFC 5288 Test Vector #1 — AES-256-GCM
    GCMTestCase tc1{
        .key = hex_to_bytes("00000000000000000000000000000000"
                            "00000000000000000000000000000000"),
        .iv = hex_to_bytes("000000000000000000000000"),
        .plaintext = hex_to_bytes("00000000000000000000000000000000"),
        .aad = {},
        .expected_ciphertext = hex_to_bytes("cea7403d4d606b6e074ec5d3baf39d18"),
        .expected_tag = hex_to_bytes("d0d1c8a799996bf00275b9cdfd77b70a")
    };
    
    bool result = test_aes_256_gcm(tc1);
    std::cout << "AES-256-GCM KAT Test #1: " 
              << (result ? "PASS" : "FAIL") << std::endl;
    assert(result);
    
    // RFC 5288 Test Vector #2 — AES-256-GCM com AAD
    GCMTestCase tc2{
        .key = hex_to_bytes("00000000000000000000000000000000"
                            "00000000000000000000000000000000"),
        .iv = hex_to_bytes("000000000000000000000000"),
        .plaintext = hex_to_bytes("d9313225f88406e5a55909c5aff5269a"
                                  "86a7a9531534f7da2e4c303d8a318a72"
                                  "1c3c0c95956809532fcf0e2449a6b525"
                                  "b16aedf5aa0de657ba637b391afd255"),
        .aad = hex_to_bytes("feedfacedeadbeeffeedfacedeadbeefabaddad2"),
        .expected_ciphertext = hex_to_bytes("42831ec2217774244b7221b784d0d49c"
                                  "e3aa212f2c02a4e035c17e2329aca12e"
                                  "21d514b25466931c7d8f6a5aac84aa05"
                                  "1ba30b396a0aac973d58e091473f5985"),
        .expected_tag = hex_to_bytes("4d5c2af327cd64a62cf3817593a0c8e3")
    };
    
    result = test_aes_256_gcm(tc2);
    std::cout << "AES-256-GCM KAT Test #2: " 
              << (result ? "PASS" : "FAIL") << std::endl;
    assert(result);
    
    std::cout << "Todos os testes KAT passaram!" << std::endl;
    return 0;
}
```

### 13.2.4 Vetores Wycheproof

O projeto Google Wycheproof fornece vetores de teste que cobrem casos extremos e edge cases:

| Categoria | Tipo de Teste | Exemplo |
|-----------|---------------|---------|
| Good | Input válido, output esperado | Teste normal |
| Bad | Input inválido, deve rejeitar | Tag incorreta, padding errado |
| NoSharing | Chaves diferentes geram outputs diferentes | Verificar randomização |
| Truncated | Dados truncados, deve rejeitar | Ciphertext incompleto |

**Uso:**
```cpp
// Carregar vetores Wycheproof do JSON
// Cada entry tem: type, key, iv, aad, msg, ct, tag, result
for (const auto& tc : wycheproof_test_vectors) {
    bool outcome = encrypt_or_decrypt(tc);
    if (tc.result == "VALID") {
        assert(outcome == true);
    } else {
        assert(outcome == false);
    }
}
```

---

## 13.3 Differential Testing

### 13.3.1 Conceito

Differential testing compara duas ou mais implementações do mesmo algoritmo e verifica que produzem os mesmos resultados. Se OpenSSL e libsodium implementam AES-256-GCM corretamente, ambos devem produzir o mesmo ciphertext para o mesmo input.

**Princípio:**
```
Para todo input X:
    OpenSSL(X) == libsodium(X) == Botan(X)
```

Se alguma implementação produz resultado diferente, pelo menos uma está incorreta.

### 13.3.2 Implementação em C++

```cpp
#include <openssl/evp.h>
#include <sodium.h>
#include <iostream>
#include <random>
#include <vector>
#include <cassert>

struct CryptoResult {
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> tag;
};

CryptoResult test_openssl_aes_gcm(
    const std::vector<uint8_t>& key,
    const std::vector<uint8_t>& iv,
    const std::vector<uint8_t>& plaintext,
    const std::vector<uint8_t>& aad
) {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    int len;
    std::vector<uint8_t> ct(plaintext.size() + 16);
    std::vector<uint8_t> tag(16);
    
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, iv.size(), nullptr);
    EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), iv.data());
    
    if (!aad.empty())
        EVP_EncryptUpdate(ctx, nullptr, &len, aad.data(), aad.size());
    
    EVP_EncryptUpdate(ctx, ct.data(), &len, plaintext.data(), plaintext.size());
    EVP_EncryptFinal_ex(ctx, ct.data() + len, &len);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data());
    
    EVP_CIPHER_CTX_free(ctx);
    
    ct.resize(plaintext.size());
    return {ct, tag};
}

// libsodium não implementa AES-GCM diretamente, mas usa 
// ChaCha20-Poly1305 como AEAD primário
// Para differential testing real, usar a mesma primitiva
// em ambas as bibliotecas

bool differential_test_chacha20_poly1305(
    size_t key_size,
    size_t plaintext_size,
    size_t aad_size,
    int num_iterations
) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dist_key(0, 255);
    std::uniform_int_distribution<> dist_len(0, 255);
    
    int mismatches = 0;
    
    for (int i = 0; i < num_iterations; i++) {
        // Gerar dados aleatórios
        std::vector<uint8_t> key(key_size);
        std::vector<uint8_t> nonce(12);
        std::vector<uint8_t> plaintext(plaintext_size);
        std::vector<uint8_t> aad(aad_size);
        
        for (auto& b : key) b = dist_key(gen);
        for (auto& b : nonce) b = dist_key(gen);
        for (auto& b : plaintext) b = dist_key(gen);
        for (auto& b : aad) b = dist_key(gen);
        
        // Implementação 1: libsodium
        std::vector<uint8_t> ct1(plaintext.size() + 16);
        unsigned long long ct1_len;
        
        crypto_aead_chacha20poly1305_ietf_encrypt(
            ct1.data(), &ct1_len,
            plaintext.data(), plaintext.size(),
            aad.data(), aad_size,
            nullptr, nonce.data(), key.data());
        
        // Implementação 2: OpenSSL ChaCha20-Poly1305
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        int len;
        std::vector<uint8_t> ct2(plaintext.size() + 16);
        std::vector<uint8_t> tag2(16);
        
        EVP_EncryptInit_ex(ctx, EVP_chacha20_poly1305(), nullptr, nullptr, nullptr);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_SET_IVLEN, 12, nullptr);
        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), nonce.data());
        
        if (!aad.empty())
            EVP_EncryptUpdate(ctx, nullptr, &len, aad.data(), aad.size());
        
        EVP_EncryptUpdate(ctx, ct2.data(), &len, plaintext.data(), plaintext.size());
        EVP_EncryptFinal_ex(ctx, ct2.data() + len, &len);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_AEAD_GET_TAG, 16, tag2.data());
        
        EVP_CIPHER_CTX_free(ctx);
        
        // Comparar ciphertexts
        ct1.resize(plaintext.size());
        ct2.resize(plaintext.size());
        
        if (ct1 != ct2) {
            std::cerr << "MISMATCH no teste " << i << std::endl;
            mismatches++;
        }
        
        // Comparar tags
        std::vector<uint8_t> tag1(ct1.end() - 16, ct1.end());
        if (tag1 != tag2) {
            std::cerr << "TAG MISMATCH no teste " << i << std::endl;
            mismatches++;
        }
    }
    
    std::cout << "Differential test: " << num_iterations << " iterações, "
              << mismatches << " mismatches" << std::endl;
    
    return mismatches == 0;
}

int main() {
    if (sodium_init() < 0) {
        std::cerr << "Falha ao inicializar libsodium" << std::endl;
        return 1;
    }
    
    // Testes progressivos de complexidade
    bool all_pass = true;
    
    all_pass &= differential_test_chacha20_poly1305(32, 0, 0, 1000);
    all_pass &= differential_test_chacha20_poly1305(32, 16, 0, 1000);
    all_pass &= differential_test_chacha20_poly1305(32, 64, 12, 1000);
    all_pass &= differential_test_chacha20_poly1305(32, 4096, 256, 1000);
    all_pass &= differential_test_chacha20_poly1305(32, 65536, 1024, 100);
    
    std::cout << "\nResultado final: " 
              << (all_pass ? "TODOS PASSARAM" : "FALHA DETECTADA") 
              << std::endl;
    
    return all_pass ? 0 : 1;
}
```

---

## 13.4 Fuzzing de Código Criptográfico

### 13.4.1 Por Que Fuzzing?

Fuzzing é especialmente eficaz para código criptográfico porque:

1. **Inputs complexos**: Chaves, IVs, AAD, ciphertexts — muitos campos interdependentes
2. **Edge cases críticos**: Tamanhos específicos, zeros, valores máximos
3. **Código rarely exercised**: Error paths, unusual input combinations
4. **Side-channels em error paths**: Tratamento de erros pode vazar informações

### 13.4.2 Structure-Aware Fuzzing com libFuzzer

```cpp
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <openssl/evp.h>

// libFuzzer entry point
extern "C" int LLVMFuzzerTestOneInput(
    const uint8_t* data, size_t size
) {
    if (size < 48) return 0;  // mínimo: 32 key + 12 nonce + 4 len
    
    const uint8_t* key = data;
    const uint8_t* nonce = data + 32;
    const uint8_t* aad_len_bytes = data + 44;
    size_t aad_len = (aad_len_bytes[0] << 8) | aad_len_bytes[1];
    size_t ct_start = 46;
    
    if (ct_start + aad_len >= size) return 0;
    
    const uint8_t* aad = data + ct_start;
    const uint8_t* ct = data + ct_start + aad_len;
    size_t ct_len = size - ct_start - aad_len;
    
    // Tentar decrypt com dados fuzzed
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return 0;
    
    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr) == 1) {
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
        EVP_DecryptInit_ex(ctx, nullptr, nullptr, key, nonce);
        
        if (aad_len > 0) {
            EVP_DecryptUpdate(ctx, nullptr, nullptr, aad, aad_len);
        }
        
        // Tentar decrypt — deve tratar dados inválidos sem crash
        std::vector<uint8_t> pt(ct_len + 16);
        int len = 0;
        EVP_DecryptUpdate(ctx, pt.data(), &len, ct, ct_len);
        
        // Se tag não foi fornecida, verificar que final falha graciosamente
        EVP_DecryptFinal_ex(ctx, pt.data() + len, &len);
        // Não importa se falha — o importante é não crashar
    }
    
    EVP_CIPHER_CTX_free(ctx);
    return 0;
}

// Fuzzer para hash functions
extern "C" int LLVMFuzzerTestOneInputHash(
    const uint8_t* data, size_t size
) {
    unsigned char hash[SHA256_DIGEST_LENGTH];
    
    EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
    if (!mdctx) return 0;
    
    EVP_DigestInit_ex(mdctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(mdctx, data, size);
    EVP_DigestFinal_ex(mdctx, hash, nullptr);
    
    EVP_MD_CTX_free(mdctx);
    return 0;
}
```

### 13.4.3 Cryptofuzz

Cryptofuzz é um framework especializado em differential fuzzing de bibliotecas criptográficas:

```bash
# Setup do Cryptofuzz
git clone https://github.com/guidovranken/cryptofuzz.git
cd cryptofuzz
mkdir corpus

# Construir com OpenSSL e libsodium
./gen_repository.py
mkdir modules/openssl-module
echo "OPENSSL=1" > modules/openssl-module/configuration.txt
mkdir modules/libsodium-module
echo "LIBSODIUM=1" > modules/libsodium-module/configuration.txt

# Compilar
./gn.py configure --libfuzzer --enable-openssl --enable-libsodium
ninja -C build

# Rodar fuzzing
./build/src/cryptofuzz corpus/ -max_total_time=3600
```

**O que Cryptofuzz detecta automaticamente:**
- Diferenças entre implementações (AES-GCM OpenSSL vs Botan vs NSS)
- Crashes em inputs extremos
- Tempo anormal de execução (side-channels potenciais)
- Outputs que violam propriedades (ciphertext == plaintext, tag == zeros)

### 13.4.4 Fuzzing com AFL++

```bash
# Compilar com AFL++ instrumentation
export AFL_USE_ASAN=1
afl-clang-fast++ -fsanitize=fuzzer,address -O2 \
    -o crypto_fuzzer crypto_fuzzer.cpp \
    -lssl -lcrypto -lsodium

# Preparar corpus inicial
mkdir input/
echo -n "AES-256-GCM" > input/aes_gcm_seed
echo -n "ChaCha20-Poly1305" > input/chacha_seed

# Rodar
afl-fuzz -i input/ -o output/ -- ./crypto_fuzzer

# Monitorar
afl-whatsup output/
```

---

## 13.5 Property-Based Testing

### 13.5.1 Propriedades Universais de Criptografia

Toda implementação criptográfica correta deve satisfazer propriedades fundamentais:

| Propriedade | Descrição | Exemplo |
|-------------|-----------|---------|
| **Correctness** | Decrypt(Encrypt(m)) == m | Para qualquer mensagem |
| **Key uniqueness** | Chaves diferentes geram ciphertexts diferentes | Sem collision |
| **Semantic security** | Mensagens diferentes geram ciphertexts diferentes | Sem pattern |
| **Non-malleability** | Modificar ciphertext produce output aleatório | Sem bit-flipping |
| **Constant-time** | Tempo não depende do secret | Sem timing leak |

### 13.5.2 Implementação com QuickCheck-style

```cpp
#include <random>
#include <functional>
#include <vector>
#include <iostream>
#include <openssl/evp.h>
#include <sodium.h>

// Property: Encrypt then Decrypt retorna o plaintext original
template<typename EncryptFunc, typename DecryptFunc>
bool property_correctness(
    EncryptFunc encrypt, 
    DecryptFunc decrypt,
    size_t num_trials = 10000
) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> len_dist(0, 4096);
    std::uniform_int_distribution<> byte_dist(0, 255);
    
    for (int i = 0; i < num_trials; i++) {
        // Gerar plaintext aleatório
        size_t pt_len = len_dist(gen);
        std::vector<uint8_t> plaintext(pt_len);
        for (auto& b : plaintext) b = byte_dist(gen);
        
        // Encrypt
        auto ciphertext = encrypt(plaintext);
        
        // Decrypt
        auto recovered = decrypt(ciphertext);
        
        // Verificar
        if (recovered != plaintext) {
            std::cerr << "Property violation: correctness failed "
                      << "no trial " << i << std::endl;
            return false;
        }
    }
    return true;
}

// Property: Chaves diferentes → ciphertexts diferentes
bool property_key_uniqueness(size_t num_trials = 1000) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> byte_dist(0, 255);
    
    std::vector<uint8_t> plaintext(32);
    for (auto& b : plaintext) b = byte_dist(gen);
    
    std::vector<std::vector<uint8_t>> ciphertexts;
    
    for (int i = 0; i < num_trials; i++) {
        // Chave aleatória
        std::vector<uint8_t> key(32);
        for (auto& b : key) b = byte_dist(gen);
        
        // Nonce aleatório
        std::vector<uint8_t> nonce(12);
        for (auto& b : nonce) b = byte_dist(gen);
        
        // Encrypt com libsodium
        std::vector<uint8_t> ct(plaintext.size() + 16);
        unsigned long long ct_len;
        
        crypto_aead_chacha20poly1305_ietf_encrypt(
            ct.data(), &ct_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0,
            nullptr, nonce.data(), key.data());
        
        ct.resize(ct_len);
        
        // Verificar que é único
        for (size_t j = 0; j < ciphertexts.size(); j++) {
            if (ciphertexts[j] == ct) {
                std::cerr << "Key uniqueness violated at trial " << i 
                          << " (same as trial " << j << ")" << std::endl;
                return false;
            }
        }
        
        ciphertexts.push_back(ct);
    }
    return true;
}

// Property: Nonce diferente → ciphertext diferente
bool property_nonce_uniqueness(size_t num_trials = 1000) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> byte_dist(0, 255);
    
    std::vector<uint8_t> key(32);
    for (auto& b : key) b = byte_dist(gen);
    
    std::vector<uint8_t> plaintext(32);
    for (auto& b : plaintext) b = byte_dist(gen);
    
    std::vector<std::vector<uint8_t>> ciphertexts;
    
    for (int i = 0; i < num_trials; i++) {
        std::vector<uint8_t> nonce(12);
        for (auto& b : nonce) b = byte_dist(gen);
        
        std::vector<uint8_t> ct(plaintext.size() + 16);
        unsigned long long ct_len;
        
        crypto_aead_chacha20poly1305_ietf_encrypt(
            ct.data(), &ct_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0,
            nullptr, nonce.data(), key.data());
        
        ct.resize(ct_len);
        
        for (size_t j = 0; j < ciphertexts.size(); j++) {
            if (ciphertexts[j] == ct) {
                std::cerr << "Nonce uniqueness violated at trial " << i << std::endl;
                return false;
            }
        }
        ciphertexts.push_back(ct);
    }
    return true;
}

int main() {
    if (sodium_init() < 0) return 1;
    
    std::cout << "Property: Correctness... ";
    // ... encrypt/decrypt lambdas using libsodium
    std::cout << "PASS" << std::endl;
    
    std::cout << "Property: Key uniqueness... ";
    bool ku = property_key_uniqueness();
    std::cout << (ku ? "PASS" : "FAIL") << std::endl;
    
    std::cout << "Property: Nonce uniqueness... ";
    bool nu = property_nonce_uniqueness();
    std::cout << (nu ? "PASS" : "FAIL") << std::endl;
    
    return 0;
}
```

---

## 13.6 Verificação de Constant-Time em Testes

### 13.6.1 Abordagem com Valgrind/ctgrind

A abordagem mais prática é marcar dados secretos com `VALGRIND_MAKE_MEM_UNDEFINED` e verificar que nenhum branch ou memória é acessado condicionalmente baseado nesses dados:

```cpp
#include <valgrind/memcheck.h>
#include <openssl/crypto.h>
#include <iostream>

// Teste: verificar que CRYPTO_memcmp é constant-time
bool test_constant_time_comparison() {
    uint8_t secret[32] = {0};  // chave secreta
    uint8_t known[32] = {0};   // valor conhecido
    
    // Marcar secret como "não inicializado" para Valgrind
    VALGRIND_MAKE_MEM_UNDEFINED(secret, 32);
    
    // CRYPTO_memcmp deve ser constant-time
    int result = CRYPTO_memcmp(secret, known, 32);
    
    // Se CRYPTO_memcmp não for constant-time, Valgrind detectará
    // conditional jump baseado em valor não inicializado
    
    return true;  // Se chegou aqui sem warning, passou
}

// Teste: verificar que comparação customizada NÃO é constant-time (anti-pattern)
bool test_non_constant_time_comparison(uint8_t* a, uint8_t* b, size_t len) {
    // Esta comparação NÃO é constant-time — early return
    for (size_t i = 0; i < len; i++) {
        if (a[i] != b[i]) return false;  // BUG: timing leak!
    }
    return true;
}
```

### 13.6.2 Abordagem com Performance Counters

```cpp
#include <linux/perf_event.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <iostream>
#include <vector>
#include <numeric>

class TimingAnalyzer {
    int fd;
    
public:
    TimingAnalyzer() {
        struct perf_event_attr pe{};
        pe.type = PERF_TYPE_HARDWARE;
        pe.size = sizeof(pe);
        pe.config = PERF_COUNT_HW_CPU_CYCLES;
        pe.disabled = 1;
        pe.exclude_kernel = 1;
        pe.exclude_hv = 1;
        
        fd = perf_event_open(&pe, 0, -1, -1, 0);
    }
    
    uint64_t measure(std::function<void()> fn, int iterations = 100000) {
        std::vector<uint64_t> times;
        
        for (int i = 0; i < iterations; i++) {
            ioctl(fd, PERF_EVENT_IOC_RESET, 0);
            ioctl(fd, PERF_EVENT_IOC_ENABLE, 0);
            
            fn();
            
            ioctl(fd, PERF_EVENT_IOC_DISABLE, 0);
            
            uint64_t cycles = 0;
            read(fd, &cycles, sizeof(cycles));
            times.push_back(cycles);
        }
        
        // Analisar variância
        double mean = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
        double variance = 0;
        for (auto t : times) {
            variance += (t - mean) * (t - mean);
        }
        variance /= times.size();
        double stddev = std::sqrt(variance);
        
        // Coeficiente de variação (CV)
        double cv = stddev / mean;
        
        std::cout << "Mean: " << mean << " cycles, "
                  << "StdDev: " << stddev << ", "
                  << "CV: " << cv << std::endl;
        
        // Se CV > 0.1, provavelmente há timing variation
        return static_cast<uint64_t>(cv * 1000);
    }
};
```

---

## 13.7 CVE-2022-4304: Estudo de Caso

### 13.7.1 Descrição

CVE-2022-4304 é um timing side-channel em implementações RSA do OpenSSL que permite recuperação parcial da chave privada.

**Resumo:**
- **Produto**: OpenSSL 1.0.2 - 1.1.1
- **Severidade**: Medium (CVSS 5.9)
- **Tipo**: Timing side-channel
- **Vetor**: Decryption de ciphertexts RSA com chaves CRT

### 13.7.2 Análise Técnica

O bug estava na implementação de RSA decryption com CRT (Chinese Remainder Theorem):

```cpp
// Código VULNERÁVEL (simplificação)
int RSA_private_decrypt(int flen, const unsigned char* from,
                        unsigned char* to, RSA* rsa, int padding) {
    // ...
    
    // CRT-based decryption
    BIGNUM *m1 = BN_new(), *m2 = BN_new();
    
    // m1 = c^dmp1 mod p
    BN_mod_exp_montgomery(m1, c, rsa->dmp1, rsa->p, ctx);
    
    // m2 = c^dmq1 mod q  
    BN_mod_exp_montgomery(m2, c, rsa->dmq1, rsa->q, ctx);
    
    // BUG: Se m1 < m2, há um branch que leva mais tempo
    if (BN_cmp(m1, m2) < 0) {
        // Adicionar q para garantir que m1 > m2
        BN_add(m1, m1, rsa->q);
    }
    
    // h = (m1 - m2) * iqmp mod p
    // ...
}
```

**O problema:** A comparação `BN_cmp(m1, m2)` e o branch condicional levam tempo diferente dependendo do resultado. Um atacante pode medir o tempo de decryption para deduzir bits da chave privada.

### 13.7.3 Código de Teste

```cpp
// Teste para detectar o timing side-channel
#include <chrono>
#include <vector>
#include <openssl/rsa.h>
#include <openssl/bn.h>

bool detect_timing_leak() {
    RSA* rsa = RSA_new();
    BIGNUM* e = BN_new();
    BN_set_word(e, 65537);
    RSA_generate_key_ex(rsa, 2048, e, nullptr);
    
    // Medir tempo de decryption com diferentes ciphertexts
    std::vector<double> times;
    
    for (int i = 0; i < 10000; i++) {
        // Gerar ciphertext aleatório (não precisa ser válido)
        unsigned char msg[256];
        for (auto& b : msg) b = rand() % 256;
        
        unsigned char encrypted[256];
        unsigned char decrypted[256];
        int enc_len = RSA_public_encrypt(256, msg, encrypted, rsa, RSA_NO_PADDING);
        
        auto start = std::chrono::high_resolution_clock::now();
        int dec_len = RSA_private_decrypt(enc_len, encrypted, decrypted, rsa, RSA_NO_PADDING);
        auto end = std::chrono::high_resolution_clock::now();
        
        auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
        times.push_back(duration.count());
    }
    
    // Analisar variância
    double mean = std::accumulate(times.begin(), times.end(), 0.0) / times.size();
    double variance = 0;
    for (auto t : times) {
        variance += (t - mean) * (t - mean);
    }
    variance /= times.size();
    double cv = std::sqrt(variance) / mean;
    
    std::cout << "Timing CV: " << cv << std::endl;
    
    RSA_free(rsa);
    BN_free(e);
    
    // CV > 0.05 sugere timing variation suspeita
    return cv > 0.05;
}

int main() {
    bool leak_detected = detect_timing_leak();
    std::cout << "Timing leak: " 
              << (leak_detected ? "DETECTADO" : "NAO DETECTADO") << std::endl;
    return leak_detected ? 1 : 0;
}
```

### 13.7.4 Correção e Lição

**Correção (OpenSSL 1.1.1n):** Usar operações constant-time para comparação:

```cpp
// Código CORRIGIDO
if (BN_cmp(m1, m2) < 0) {
    // Trocar por: constant-time conditional add
    // m1 = m1 + q (sempre, mas com seletor const-time)
    BIGNUM* selector = BN_new();
    BN_consttime_swap(BN_cmp(m1, m2) < 0, m1, m2, BN_num_bits(rsa->q));
    BN_free(selector);
}
```

**Lição:** Timing side-channels em operações criptográficas são extremamente difíceis de detectar com testes convencionais. É necessário:
1. Testes de constant-time como parte do pipeline de CI
2. Análise estática com ferramentas como ct-verif
3. Code review específico para branches baseados em dados secretos

---

## 13.8 Reproducible Builds

### 13.8.1 Por Que?

Reproducible builds garantem que o binário compilado corresponde exatamente ao código-fonte. Isso é crítico para criptografia porque:

- Binários podem ser backdoorados na distribuição
- Compiladores podem introduzir side-channels
- A confiança deve vir do código, não do binário

### 13.8.2 Como Verificar

```bash
# 1. Compilar em ambiente isolado
docker run --rm -v $(pwd):/src ubuntu:22.04 bash -c \
    "apt-get update && apt-get install -y build-essential cmake libssl-dev && \
     cd /src && mkdir build && cd build && \
     cmake -DCMAKE_BUILD_TYPE=Release .. && make"

# 2. Calcular hash do binário
sha256sum build/crypto_server

# 3. Comparar com hash publicado
cat published_hash.txt
# Os hashes devem ser idênticos

# 4. Ou usar diffoscope para comparação detalhada
diffoscope --exclude .git build/crypto_server published_binary
```

### 13.8.3 CI/CD para Reproducible Builds

```yaml
# .github/workflows/reproducible.yml
name: Reproducible Build Verification
on: [push, pull_request]

jobs:
  verify-build:
    runs-on: ubuntu-22.04
    container: ubuntu:22.04
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          apt-get update
          apt-get install -y build-essential cmake libssl-dev libsodium-dev
      
      - name: Build
        run: |
          mkdir build && cd build
          cmake -DCMAKE_BUILD_TYPE=Release \
                -DCMAKE_C_COMPILER=gcc-12 \
                -DREPRODUCIBLE_BUILD=ON ..
          make -j$(nproc)
      
      - name: Verify hash
        run: |
          EXPECTED_HASH=$(cat .build-hash)
          ACTUAL_HASH=$(sha256sum build/crypto_server | cut -d' ' -f1)
          if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
            echo "BUILD NOT REPRODUCIBLE!"
            echo "Expected: $EXPECTED_HASH"
            echo "Actual: $ACTUAL_HASH"
            exit 1
          fi
```

---

## 13.9 CI/CD Pipeline Completo

### 13.9.1 GitHub Actions para Crypto Testing

```yaml
name: Crypto Implementation Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ libssl-dev libsodium-dev valgrind
      
      - name: Build
        run: |
          mkdir build && cd build
          cmake -DCMAKE_BUILD_TYPE=Debug -DENABLE_SANITIZERS=ON ..
          make -j$(nproc)
      
      - name: KAT Tests
        run: cd build && ctest -R "KAT" --output-on-failure
      
      - name: Differential Tests
        run: cd build && ctest -R "DIFF" --output-on-failure
      
      - name: Property Tests
        run: cd build && ctest -R "PROPERTY" --output-on-failure
      
      - name: Memory Safety (ASan)
        run: |
          cd build
          ASAN_OPTIONS=detect_leaks=1 ./crypto_tests
      
      - name: Constant-Time Check (Valgrind)
        run: |
          cd build
          valgrind --tool=exp-sgcheck --error-exitcode=1 \
            ./crypto_tests --gtest_filter="*ConstantTime*"
  
  fuzzing:
    runs-on: ubuntu-22.04
    strategy:
      matrix:
        fuzzer: [chacha, aes_gcm, ecdsa, sha256]
    steps:
      - uses: actions/checkout@v4
      
      - name: Build fuzzer
        run: |
          clang++ -fsanitize=fuzzer,address,undefined -O2 \
            -o fuzz_${{ matrix.fuzzer }} \
            fuzzing/fuzz_${{ matrix.fuzzer }}.cpp \
            -lssl -lcrypto -lsodium
      
      - name: Run fuzzing (10 minutes)
        run: |
          mkdir corpus_${{ matrix.fuzzer }}
          ./fuzz_${{ matrix.fuzzer }} corpus_${{ matrix.fuzzer }}/ \
            -max_total_time=600
      
      - name: Upload artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: fuzzer-${{ matrix.fuzzer }}-crash
          path: crash-*
```

---

## 13.10 Exemplo Completo: Suite de Testes para AES-GCM

```cpp
#include <gtest/gtest.h>
#include <openssl/evp.h>
#include <sodium.h>
#include <vector>
#include <random>

class AESGCMTestSuite : public ::testing::Test {
protected:
    void SetUp() override {
        // Setup OpenSSL
        ctx = EVP_CIPHER_CTX_new();
    }
    
    void TearDown() override {
        EVP_CIPHER_CTX_free(ctx);
    }
    
    EVP_CIPHER_CTX* ctx;
    
    std::vector<uint8_t> encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& iv,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad,
        std::vector<uint8_t>& tag
    ) {
        int len;
        std::vector<uint8_t> ct(plaintext.size() + 16);
        tag.resize(16);
        
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, iv.size(), nullptr);
        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), iv.data());
        
        if (!aad.empty())
            EVP_EncryptUpdate(ctx, nullptr, &len, aad.data(), aad.size());
        
        EVP_EncryptUpdate(ctx, ct.data(), &len, plaintext.data(), plaintext.size());
        EVP_EncryptFinal_ex(ctx, ct.data() + len, &len);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag.data());
        
        ct.resize(plaintext.size());
        return ct;
    }
    
    std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& iv,
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& aad,
        const std::vector<uint8_t>& tag,
        bool& success
    ) {
        int len;
        std::vector<uint8_t> pt(ciphertext.size() + 16);
        
        EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, iv.size(), nullptr);
        EVP_DecryptInit_ex(ctx, nullptr, nullptr, key.data(), iv.data());
        
        if (!aad.empty())
            EVP_DecryptUpdate(ctx, nullptr, &len, aad.data(), aad.size());
        
        EVP_DecryptUpdate(ctx, pt.data(), &len, ciphertext.data(), ciphertext.size());
        
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, 
                            const_cast<uint8_t*>(tag.data()));
        
        int ret = EVP_DecryptFinal_ex(ctx, pt.data() + len, &len);
        success = (ret > 0);
        
        pt.resize(ciphertext.size());
        return pt;
    }
};

// Teste de correctness básico
TEST_F(AESGCMTestSuite, CorrectnessEmptyPlaintext) {
    std::vector<uint8_t> key(32, 0x42);
    std::vector<uint8_t> iv(12, 0x24);
    std::vector<uint8_t> plaintext = {};
    std::vector<uint8_t> aad = {};
    std::vector<uint8_t> tag;
    
    auto ct = encrypt(key, iv, plaintext, aad, tag);
    bool ok;
    auto pt = decrypt(key, iv, ct, aad, tag, ok);
    
    EXPECT_TRUE(ok);
    EXPECT_EQ(pt, plaintext);
}

TEST_F(AESGCMTestSuite, CorrectnessShortPlaintext) {
    std::vector<uint8_t> key(32, 0x00);
    std::vector<uint8_t> iv(12, 0x01);
    std::vector<uint8_t> plaintext = {0x48, 0x65, 0x6c, 0x6c, 0x6f}; // "Hello"
    std::vector<uint8_t> aad = {};
    std::vector<uint8_t> tag;
    
    auto ct = encrypt(key, iv, plaintext, aad, tag);
    bool ok;
    auto pt = decrypt(key, iv, ct, aad, tag, ok);
    
    EXPECT_TRUE(ok);
    EXPECT_EQ(pt, plaintext);
}

// Teste: tag incorreta deve falhar
TEST_F(AESGCMTestSuite, WrongTagRejects) {
    std::vector<uint8_t> key(32, 0x42);
    std::vector<uint8_t> iv(12, 0x24);
    std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03};
    std::vector<uint8_t> aad = {};
    std::vector<uint8_t> tag;
    
    auto ct = encrypt(key, iv, plaintext, aad, tag);
    
    // Corromper tag
    tag[0] ^= 0xFF;
    
    bool ok;
    auto pt = decrypt(key, iv, ct, aad, tag, ok);
    EXPECT_FALSE(ok);
}

// Teste: chave incorreta deve falhar
TEST_F(AESGCMTestSuite, WrongKeyRejects) {
    std::vector<uint8_t> key(32, 0x42);
    std::vector<uint8_t> wrong_key(32, 0x99);
    std::vector<uint8_t> iv(12, 0x24);
    std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03};
    std::vector<uint8_t> aad = {};
    std::vector<uint8_t> tag;
    
    auto ct = encrypt(key, iv, plaintext, aad, tag);
    
    bool ok;
    auto pt = decrypt(wrong_key, iv, ct, aad, tag, ok);
    EXPECT_FALSE(ok);
}

// Teste: AAD correto deve ser verificado
TEST_F(AESGCMTestSuite, WrongAADRejects) {
    std::vector<uint8_t> key(32, 0x42);
    std::vector<uint8_t> iv(12, 0x24);
    std::vector<uint8_t> plaintext = {0x01, 0x02, 0x03};
    std::vector<uint8_t> aad = {0xAA, 0xBB, 0xCC};
    std::vector<uint8_t> tag;
    
    auto ct = encrypt(key, iv, plaintext, aad, tag);
    
    std::vector<uint8_t> wrong_aad = {0xDD, 0xEE, 0xFF};
    bool ok;
    auto pt = decrypt(key, iv, ct, wrong_aad, tag, ok);
    EXPECT_FALSE(ok);
}

// Teste fuzzing: muitos inputs aleatórios
TEST_F(AESGCMTestSuite, RandomizedCorrectness) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> len_dist(0, 1024);
    std::uniform_int_distribution<> byte_dist(0, 255);
    
    for (int i = 0; i < 10000; i++) {
        std::vector<uint8_t> key(32);
        std::vector<uint8_t> iv(12);
        std::vector<uint8_t> plaintext(len_dist(gen));
        std::vector<uint8_t> aad(len_dist(gen) % 128);
        std::vector<uint8_t> tag;
        
        for (auto& b : key) b = byte_dist(gen);
        for (auto& b : iv) b = byte_dist(gen);
        for (auto& b : plaintext) b = byte_dist(gen);
        for (auto& b : aad) b = byte_dist(gen);
        
        auto ct = encrypt(key, iv, plaintext, aad, tag);
        bool ok;
        auto pt = decrypt(key, iv, ct, aad, tag, ok);
        
        EXPECT_TRUE(ok) << "Failed at iteration " << i;
        EXPECT_EQ(pt, plaintext) << "Data mismatch at iteration " << i;
    }
}

// Teste: performance
TEST_F(AESGCMTestSuite, PerformanceBenchmark) {
    std::vector<uint8_t> key(32, 0x42);
    std::vector<uint8_t> iv(12, 0x24);
    std::vector<uint8_t> plaintext(4096, 0x55);
    std::vector<uint8_t> aad(128, 0xAA);
    std::vector<uint8_t> tag;
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < 100000; i++) {
        auto ct = encrypt(key, iv, plaintext, aad, tag);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    double ops_per_sec = 100000.0 / (duration.count() / 1000.0);
    double throughput_mbps = (4096.0 * ops_per_sec) / (1024.0 * 1024.0);
    
    std::cout << "Throughput: " << throughput_mbps << " MB/s" << std::endl;
    EXPECT_GT(throughput_mbps, 100.0);  // Mínimo 100 MB/s
}
```

---

## 13.11 Test Coverage

### 13.11.1 O Que Medir

| Métrica | Target | Como Medir |
|---------|--------|------------|
| Line coverage | > 80% | gcov/lcov |
| Branch coverage | > 70% | gcov/lcov |
| Error path coverage | 100% | Manual + fuzzing |
| KAT coverage | 100% NIST vectors | Automated |
| Edge case coverage | Key sizes, IV sizes, empty input | Property tests |

### 13.11.2 Coverage Report

```bash
# Compilar com coverage instrumentation
cmake -DCMAKE_CXX_FLAGS="--coverage" -DCMAKE_BUILD_TYPE=Debug ..
make

# Rodar testes
ctest

# Gerar relatório
lcov --capture --directory . --output-file coverage.info
lcov --remove coverage.info '/usr/*' --output-file coverage_filtered.info
genhtml coverage_filtered.info --output-directory coverage_report

# Abrir no browser
xdg-open coverage_report/index.html
```

---

## 13.12 Exercícios

### Exercício 1: KAT Suite
Implemente uma suite de KAT para AES-128/192/256-GCM usando vetores do NIST CAVP. Inclua testes de encrypt e decrypt com todos os tamanhos de plaintext.

### Exercício 2: Differential Testing
Implemente differential testing entre OpenSSL e libsodium para ChaCha20-Poly1305. Execute 100,000 iterações com inputs aleatórios e reporte qualquer mismatch.

### Exercício 3: Fuzzer Estruturado
Implemente um libFuzzer para ECDSA signature verification que cubra:
- Assinaturas com point-on-curve inválido
- R value fora da ordem
- Hash truncation incorreta
- Nonce reuse

### Exercício 4: Constant-Time Test
Implemente um teste que compara timing de `CRYPTO_memcmp` vs comparação regular (`memcmp`) com 100,000 iterações. Meça e reporte o coeficiente de variação.

### Exercício 5: Property-Based Test Suite
Implemente property-based tests para Ed25519:
- Correctness: sign + verify
- Determinism: mesmo input → mesma assinatura
- Non-reusability: assinaturas diferentes para mensagens diferentes
- Batch verification: verificação em lote é mais rápida

### Exercício 6: CI Pipeline
Crie um GitHub Actions workflow que execute todas as categorias de teste (KAT, differential, fuzzing, timing) e falhe se qualquer uma encontrar problemas.

---

## 13.13 Referências

1. NIST CAVP: https://csrc.nist.gov/projects/cryptographic-algorithm-validation-program
2. Wycheproof: https://github.com/google/wycheproof
3. Cryptofuzz: https://github.com/guidovranken/cryptofuzz
4. libFuzzer: https://llvm.org/docs/LibFuzzer.html
5. AFL++: https://github.com/AFLplusplus/AFLplusplus
6. OpenSSL CVE-2022-4304: https://www.openssl.org/news/secadv/20230207.txt
7. Valgrind ct-grind: https://valgrind.org/docs/manual/faq.html
8. Reproducible Builds: https://reproducible-builds.org/
9. Google Project Wycheproof: https://github.com/google/wycheproof/blob/master/doc/wycheproof_design.md
10. Boneh, D. (2016). "Twenty Years of Attacks on the RSA Cryptosystem." Notices of the AMS
11. Bernstein, D.J. (2005). "Cache-timing attacks on AES." 
12. Brumley, B.B., Boneh, D. (2003). "Remote timing attacks are practical." *Computer Networks*
13. Clulow, J. (2003). "On the Security of Pseudo-Random Number Generators." *ICISC*
14. Heninger, N. et al. (2012). "Mining Your Ps and Qs: Detection of Widespread Weak Keys in Network Devices." *USENIX Security*
15. NIST SP 800-90A: "Recommendation for Random Number Generation Using Deterministic Random Bit Generators"

---

*[Capítulo 12 — Verificação Formal de Implementações Criptográficas](12-verificacao-formal.md)*
*[Capítulo 14 — Compliance e Normas Criptográficas](14-compliance-normas.md)*
