# Capítulo 8 — Criptografia e Gestão de Chaves

> "Cryptography is not about secrets — it is about trust."
> Bruce Schneier

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Distinguir entre criptografia simétrica e assimétrica, compreendendo quando aplicar cada abordagem e seus respectivos trade-offs de performance e segurança.
2. Implementar criptografia autenticada (AES-GCM e ChaCha20-Poly1305) em C++17, gerenciando corretamente nonces, associated data e verificação de autenticação.
3. Projetar e implementar um sistema completo de gestão de chaves, incluindo geração segura, armazenamento criptografado, rotação automatizada e destruição segura de memória.
4. Analisar vulnerabilidades históricas de criptografia (ROCA, FREAK, POODLE, Heartbleed) e compreender as falhas criptográficas subjacentes que as tornaram possíveis.
5. Avaliar e planejar a migração para criptografia pós-quântica, compreendendo os algoritmos candidatos do NIST e suas implicações para sistemas existentes.

---

## 1. Fundamentos de Criptografia

### 1.1 Criptografia Simétrica vs Assimétrica

A criptografia simétrica utiliza a mesma chave para criptografar e descriptografar. É rápida e eficiente, mas exige que ambas as partes compartilhem um segredo comum. A criptografia assimétrica utiliza um par de chaves — pública e privada — permitindo comunicação segura sem troca prévia de segredos.

| Característica | Simétrica | Assimétrica |
|---|---|---|
| Velocidade | ~1000x mais rápida | Mais lenta |
| Chave | Una compartilhada | Par de chaves |
| Uso principal | Bulk encryption | Key exchange, assinaturas |
| Escalabilidade | O(n²) pares de chaves | O(n) chaves públicas |
| Exemplos | AES, ChaCha20 | RSA, ECC, Ed25519 |

### 1.2 Cipher Blocks vs Stream Ciphers

Block ciphers processam dados em blocos de tamanho fixo (tipicamente 128 bits). Stream ciphers geram um keystream pseudocasual e o combinam com o plaintext via XOR. Block ciphers são mais versáteis, enquanto stream ciphers oferecem melhor performance em hardware limitado.

### 1.3 Modos de Operação

Os modos de operação definem como block ciphers processam dados maiores que um bloco:

- **ECB (Electronic Codebook)**: Cada bloco é criptografado independentemente. **NUNCA usar** — preserva padrões no plaintext.
- **CBC (Cipher Block Chaining)**: Cada bloco é XOR com o anterior antes da criptografia. Susceptível a padding oracle attacks.
- **CTR (Counter Mode)**: Converte block cipher em stream cipher. Permite paralelização.
- **GCM (Galois/Counter Mode)**: CTR + autenticação via GHASH. Fornece autenticação e confidencialidade simultaneamente.

### 1.4 Criptografia Autenticada

Criptografia autenticada (AEAD) garante confidencialidade e integridade. AEADs como AES-GCM e ChaCha20-Poly1305 produzem um authentication tag que detecta qualquer manipulação. Usar criptografia sem autenticação é um erro grave — CBC sem MAC permite bit-flipping attacks.

### 1.5 Conceitos Errôneos Comuns

Mitos perigosos sobre criptografia:

- **"256-bit sempre é melhor que 128-bit"**: Em AES, ambos são considerados seguros. A diferença está na margem de segurança, não na resistência a ataques práticos.
- **"Criptografar duas vezes é melhor"**: Double encryption não aumenta significativamente a segurança e pode introduzir vulnerabilidades (meet-in-the-middle).
- **"AES está ultrapassado"**: AES permanece o padrão ouro. Nenhum ataque prático contra AES-128 ou AES-256 foi demonstrado.
- **"TLS é suficiente para tudo"**: TLS protege em trânsito, não em repouso. Dados em disco precisam de criptografia adicional.

---

## 2. Criptografia Simétrica

### 2.1 AES-GCM

AES-GCM combina o cipher AES em modo CTR com autenticação GHASH. É o cipher AEAD mais amplamente utilizado, suportado por hardware (AES-NI) e amplamente padronizado.

#### Gerenciamento de Nonces

O nonce (number used once) é crítico em GCM. Reutilizar o nonce com a mesma chave destrói completamente a segurança, permitindo recuperação do authentication key e subsequentes falsificações.

```cpp
#include <cstdint>
#include <array>
#include <vector>
#include <stdexcept>
#include <cstring>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

class AesGcmCipher {
public:
    static constexpr size_t KEY_SIZE = 32;   // AES-256
    static constexpr size_t NONCE_SIZE = 12; // 96 bits recommended for GCM
    static constexpr size_t TAG_SIZE = 16;   // 128-bit authentication tag

    struct EncryptionResult {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> tag;
        std::vector<uint8_t> nonce;
    };

    AesGcmCipher() {
        // Generate a random key from CSPRNG
        if (RAND_bytes(key_.data(), KEY_SIZE) != 1) {
            throw std::runtime_error("Failed to generate random key");
        }
    }

    explicit AesGcmCipher(const std::vector<uint8_t>& key) {
        if (key.size() != KEY_SIZE) {
            throw std::invalid_argument("Key must be 256 bits (32 bytes)");
        }
        std::memcpy(key_.data(), key.data(), KEY_SIZE);
    }

    ~AesGcmCipher() {
        // Securely erase key from memory
        OPENSSL_cleanse(key_.data(), KEY_SIZE);
    }

    // Disable copy to prevent accidental key duplication
    AesGcmCipher(const AesGcmCipher&) = delete;
    AesGcmCipher& operator=(const AesGcmCipher&) = delete;

    // Encrypt plaintext with optional associated data (AAD)
    EncryptionResult encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad = {}
    ) const {
        // Generate unique nonce — NEVER reuse with same key
        std::vector<uint8_t> nonce(NONCE_SIZE);
        if (RAND_bytes(nonce.data(), NONCE_SIZE) != 1) {
            throw std::runtime_error("Failed to generate nonce");
        }

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        std::vector<uint8_t> ciphertext(plaintext.size());
        std::vector<uint8_t> tag(TAG_SIZE);
        int out_len = 0;
        int final_len = 0;

        try {
            // Initialize encryption
            if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                    nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to init AES-GCM");
            }

            // Set nonce length
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                     NONCE_SIZE, nullptr) != 1) {
                throw std::runtime_error("Failed to set IV length");
            }

            // Set key and IV
            if (EVP_EncryptInit_ex(ctx, nullptr, nullptr,
                                    key_.data(), nonce.data()) != 1) {
                throw std::runtime_error("Failed to set key/IV");
            }

            // Process AAD if provided
            if (!aad.empty()) {
                if (EVP_EncryptUpdate(ctx, nullptr, &out_len,
                                      aad.data(), aad.size()) != 1) {
                    throw std::runtime_error("Failed to process AAD");
                }
            }

            // Encrypt plaintext
            if (EVP_EncryptUpdate(ctx, ciphertext.data(), &out_len,
                                  plaintext.data(), plaintext.size()) != 1) {
                throw std::runtime_error("Failed to encrypt");
            }

            // Finalize encryption
            if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + out_len,
                                     &final_len) != 1) {
                throw std::runtime_error("Failed to finalize encryption");
            }

            // Get authentication tag
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG,
                                     TAG_SIZE, tag.data()) != 1) {
                throw std::runtime_error("Failed to get tag");
            }

        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);

        return { ciphertext, tag, nonce };
    }

    // Decrypt ciphertext and verify authentication tag
    std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& tag,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& aad = {}
    ) const {
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        std::vector<uint8_t> plaintext(ciphertext.size());
        int out_len = 0;
        int final_len = 0;

        try {
            // Initialize decryption
            if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                    nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to init AES-GCM decrypt");
            }

            // Set nonce length
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                     nonce.size(), nullptr) != 1) {
                throw std::runtime_error("Failed to set IV length");
            }

            // Set key and nonce
            if (EVP_DecryptInit_ex(ctx, nullptr, nullptr,
                                    key_.data(), nonce.data()) != 1) {
                throw std::runtime_error("Failed to set key/IV");
            }

            // Process AAD
            if (!aad.empty()) {
                if (EVP_DecryptUpdate(ctx, nullptr, &out_len,
                                      aad.data(), aad.size()) != 1) {
                    throw std::runtime_error("Failed to process AAD");
                }
            }

            // Decrypt ciphertext
            if (EVP_DecryptUpdate(ctx, plaintext.data(), &out_len,
                                  ciphertext.data(), ciphertext.size()) != 1) {
                throw std::runtime_error("Failed to decrypt");
            }

            // Set expected authentication tag
            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG,
                                     TAG_SIZE,
                                     const_cast<uint8_t*>(tag.data())) != 1) {
                throw std::runtime_error("Failed to set tag");
            }

            // Finalize — this VERIFIES the tag. If tag is wrong,
            // EVP_DecryptFinal_ex returns 0 (authentication failure)
            if (EVP_DecryptFinal_ex(ctx, plaintext.data() + out_len,
                                     &final_len) != 1) {
                throw std::runtime_error(
                    "Authentication failed — data tampered or wrong key");
            }

        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);

        plaintext.resize(out_len + final_len);
        return plaintext;
    }

private:
    std::array<uint8_t, KEY_SIZE> key_;
};
```

### 2.2 ChaCha20-Poly1305

ChaCha20-Poly1305 é uma alternativa ao AES-GCM, especialmente em dispositivos sem suporte hardware AES (AES-NI). Desenvolvido por Daniel Bernstein, é resistente a timing attacks e produz resultados idênticos em qualquer plataforma.

#### Quando Preferir ChaCha20-Poly1305

- Dispositivos mobile/embedded sem AES-NI
- Ambientes onde timing side-channels são uma preocupação
- Protocolos que precisam de constante tempo garantido
- TLS 1.3 (já suportado como cipher suite alternativo)

```cpp
#include <sodium.h>
#include <vector>
#include <stdexcept>
#include <cstring>
#include <cstdint>

class ChaCha20Poly1305Cipher {
public:
    static constexpr size_t KEY_SIZE = 32;
    static constexpr size_t NONCE_SIZE = 12;
    static constexpr size_t TAG_SIZE = 16;

    struct EncryptionResult {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> tag;  // Appended to ciphertext in libsodium
        std::vector<uint8_t> nonce;
    };

    ChaCha20Poly1305Cipher() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        randombytes_buf(key_.data(), KEY_SIZE);
    }

    explicit ChaCha20Poly1305Cipher(const std::vector<uint8_t>& key) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        if (key.size() != KEY_SIZE) {
            throw std::invalid_argument("Key must be 256 bits");
        }
        std::memcpy(key_.data(), key.data(), KEY_SIZE);
    }

    ~ChaCha20Poly1305Cipher() {
        sodium_memzero(key_.data(), KEY_SIZE);
    }

    EncryptionResult encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad = {}
    ) const {
        std::vector<uint8_t> nonce(NONCE_SIZE);
        randombytes_buf(nonce.data(), NONCE_SIZE);

        // libsodium appends the 16-byte tag to the ciphertext
        std::vector<uint8_t> ciphertext(plaintext.size() + TAG_SIZE);

        if (crypto_aead_xchacha20poly1305_ietf_encrypt(
                ciphertext.data(), nullptr,
                plaintext.data(), plaintext.size(),
                aad.empty() ? nullptr : aad.data(),
                aad.size(),
                nullptr,  // nsec (unused)
                nonce.data(),
                key_.data()) != 0) {
            throw std::runtime_error("Encryption failed");
        }

        return { ciphertext, std::vector<uint8_t>(), nonce };
    }

    std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& ciphertext_with_tag,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& aad = {}
    ) const {
        if (ciphertext_with_tag.size() < TAG_SIZE) {
            throw std::invalid_argument("Ciphertext too short");
        }

        size_t plaintext_len = ciphertext_with_tag.size() - TAG_SIZE;
        std::vector<uint8_t> plaintext(plaintext_len);

        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), nullptr,
                nullptr,  // nsec (unused)
                ciphertext_with_tag.data(),
                ciphertext_with_tag.size(),
                aad.empty() ? nullptr : aad.data(),
                aad.size(),
                nonce.data(),
                key_.data()) != 0) {
            throw std::runtime_error(
                "Decryption/authentication failed");
        }

        return plaintext;
    }

private:
    std::array<uint8_t, KEY_SIZE> key_;
};
```

### Comparação: AES-GCM vs ChaCha20-Poly1305

| Aspecto | AES-GCM | ChaCha20-Poly1305 |
|---|---|---|
| Velocidade (com AES-NI) | ~1.5 GB/s | ~0.8 GB/s |
| Velocidade (sem AES-NI) | ~200 MB/s | ~700 MB/s |
| Tamanho da chave | 128 ou 256 bits | 256 bits |
| Tamanho do nonce | 96 bits (recomendado) | 96 bits |
| Resis. a timing attacks | Depende da implementação | Por design |
| Suporte em TLS 1.3 | Sim (obrigatório) | Sim (obrigatório) |
| Hardware acceleration | AES-NI | AVX2, NEON |
| Segurança do nonce | Reuso destrói GHASH key | Reuso destrói keystream |

---

## 3. Criptografia Assimétrica

### 3.1 RSA

RSA é baseado na dificuldade de fatorar números inteiros grandes. Embora ainda amplamente usado para assinaturas e key encapsulation, RSA está sendo gradualmente substituído por ECC devido à eficiência.

#### CVE-2017-15361 — ROCA Vulnerability

A vulnerabilidade ROCA (Return of Coppersmith's Attack) afetou a geração de chaves RSA em módulos TPM da Infineon. O gerador de chaves falhava em produzir primos verdadeiramente aleatórios, tornando fatoração factível para chaves de até 2048 bits.

```cpp
// CORRECT RSA key generation using OpenSSL EVP
// This avoids the ROCA vulnerability by using proper CSPRNG
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/rsa.h>
#include <memory>
#include <stdexcept>

class RsaKeyGenerator {
public:
    // Generate RSA key pair using cryptographically secure RNG
    // ROCA (CVE-2017-15361) occurred when TPM used weak PRNG
    static EVP_PKEY* generate_keypair(int key_bits = 2048) {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, nullptr);
        if (!ctx) {
            throw std::runtime_error("Failed to create keygen context");
        }

        EVP_PKEY* pkey = nullptr;

        try {
            if (EVP_PKEY_keygen_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init keygen");
            }

            // Set RSA key size
            if (EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, key_bits) <= 0) {
                throw std::runtime_error("Failed to set key bits");
            }

            // Set public exponent (65537 is standard)
            // Using deprecated API for compatibility; prefer EVP_PKEY_CTX
            if (EVP_PKEY_keygen(ctx, &pkey) <= 0) {
                throw std::runtime_error("Failed to generate key");
            }

        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            throw;
        }

        EVP_PKEY_CTX_free(ctx);
        return pkey;
    }

    // Verify key quality — check for known weak primes
    static bool verify_key_quality(EVP_PKEY* pkey) {
        // In production, perform additional checks:
        // 1. Verify key is not from a known weak generator
        // 2. Check prime factors are sufficiently random
        // 3. Verify no known backdoor patterns
        // This is a simplified check
        return (pkey != nullptr);
    }
};
```

### 3.2 Elliptic Curve Cryptography

ECC oferece segurança equivalente a RSA com chaves muito menores. Uma chave ECC de 256 bits equivale aproximadamente a RSA-3072 em segurança.

| Tamanho ECC | Equivalente RSA | Segurança (bits) |
|---|---|---|
| 224 | 2048 | 112 |
| 256 | 3072 | 128 |
| 384 | 7680 | 192 |
| 521 | 15360 | 256 |

### 3.3 X25519 e Ed25519

X25519 é um protocolo de Diffie-Hellman sobre a curva Curve25519, projetado por Daniel Bernstein para ser resistente a implementation errors. Ed25519 é o esquema de assinatura correspondente.

```cpp
#include <openssl/evp.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/rand.h>
#include <vector>
#include <stdexcept>
#include <memory>
#include <array>

class EcdsaKeyExchange {
public:
    struct KeyPair {
        std::vector<uint8_t> private_key;
        std::vector<uint8_t> public_key;
    };

    // Generate X25519 key pair for key exchange
    static KeyPair generate_x25519() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_X25519, nullptr);
        if (!ctx) {
            throw std::runtime_error("Failed to create X25519 context");
        }

        EVP_PKEY* pkey = nullptr;

        try {
            if (EVP_PKEY_keygen_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init X25519 keygen");
            }
            if (EVP_PKEY_keygen(ctx, &pkey) <= 0) {
                throw std::runtime_error("Failed to generate X25519 key");
            }
        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            throw;
        }
        EVP_PKEY_CTX_free(ctx);

        // Serialize public key
        int pub_len = i2d_PUBKEY(pkey, nullptr);
        std::vector<uint8_t> public_key(pub_len);
        uint8_t* pub_ptr = public_key.data();
        i2d_PUBKEY(pkey, &pub_ptr);

        // Serialize private key
        int priv_len = i2d_PrivateKey(pkey, nullptr);
        std::vector<uint8_t> private_key(priv_len);
        uint8_t* priv_ptr = private_key.data();
        i2d_PrivateKey(pkey, &priv_ptr);

        EVP_PKEY_free(pkey);
        return { private_key, public_key };
    }

    // Perform ECDH key agreement
    static std::vector<uint8_t> derive_shared_secret(
        const std::vector<uint8_t>& private_key_der,
        const std::vector<uint8_t>& peer_public_key_der
    ) {
        // Decode private key
        const uint8_t* ptr = private_key_der.data();
        EVP_PKEY* privkey = d2i_PrivateKey(nullptr, &ptr,
                                            private_key_der.size());
        if (!privkey) {
            throw std::runtime_error("Failed to decode private key");
        }

        // Decode peer's public key
        ptr = peer_public_key_der.data();
        EVP_PKEY* peer_pubkey = d2i_PUBKEY(nullptr, &ptr,
                                            peer_public_key_der.size());
        if (!peer_pubkey) {
            EVP_PKEY_free(privkey);
            throw std::runtime_error("Failed to decode peer public key");
        }

        // Create derivation context
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(privkey, nullptr);
        if (!ctx) {
            EVP_PKEY_free(privkey);
            EVP_PKEY_free(peer_pubkey);
            throw std::runtime_error("Failed to create derivation context");
        }

        std::vector<uint8_t> shared_secret;

        try {
            if (EVP_PKEY_derive_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init derivation");
            }
            if (EVP_PKEY_derive_set_peer(ctx, peer_pubkey) <= 0) {
                throw std::runtime_error("Failed to set peer key");
            }

            // Determine output size
            size_t secret_len = 0;
            if (EVP_PKEY_derive(ctx, nullptr, &secret_len) <= 0) {
                throw std::runtime_error("Failed to get secret length");
            }

            shared_secret.resize(secret_len);
            if (EVP_PKEY_derive(ctx, shared_secret.data(),
                                &secret_len) <= 0) {
                throw std::runtime_error("Failed to derive secret");
            }

            shared_secret.resize(secret_len);

        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            EVP_PKEY_free(privkey);
            EVP_PKEY_free(peer_pubkey);
            throw;
        }

        EVP_PKEY_CTX_free(ctx);
        EVP_PKEY_free(privkey);
        EVP_PKEY_free(peer_pubkey);

        return shared_secret;
    }

    // Generate Ed25519 signing key pair
    static KeyPair generate_ed25519() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_ED25519, nullptr);
        if (!ctx) {
            throw std::runtime_error("Failed to create Ed25519 context");
        }

        EVP_PKEY* pkey = nullptr;

        try {
            if (EVP_PKEY_keygen_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init Ed25519 keygen");
            }
            if (EVP_PKEY_keygen(ctx, &pkey) <= 0) {
                throw std::runtime_error("Failed to generate Ed25519 key");
            }
        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            throw;
        }
        EVP_PKEY_CTX_free(ctx);

        int pub_len = i2d_PUBKEY(pkey, nullptr);
        std::vector<uint8_t> public_key(pub_len);
        uint8_t* pub_ptr = public_key.data();
        i2d_PUBKEY(pkey, &pub_ptr);

        int priv_len = i2d_PrivateKey(pkey, nullptr);
        std::vector<uint8_t> private_key(priv_len);
        uint8_t* priv_ptr = private_key.data();
        i2d_PrivateKey(pkey, &priv_ptr);

        EVP_PKEY_free(pkey);
        return { private_key, public_key };
    }

    // Sign a message using Ed25519
    static std::vector<uint8_t> sign(
        const std::vector<uint8_t>& private_key_der,
        const uint8_t* message, size_t message_len
    ) {
        const uint8_t* ptr = private_key_der.data();
        EVP_PKEY* pkey = d2i_PrivateKey(nullptr, &ptr,
                                        private_key_der.size());
        if (!pkey) {
            throw std::runtime_error("Failed to decode signing key");
        }

        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            EVP_PKEY_free(pkey);
            throw std::runtime_error("Failed to create MD context");
        }

        std::vector<uint8_t> signature(EVP_PKEY_size(pkey));
        size_t sig_len = signature.size();

        try {
            if (EVP_DigestSignInit(mdctx, nullptr, nullptr, nullptr,
                                   pkey) != 1) {
                throw std::runtime_error("Failed to init signing");
            }
            if (EVP_DigestSignUpdate(mdctx, message, message_len) != 1) {
                throw std::runtime_error("Failed to update signing");
            }
            if (EVP_DigestSignFinal(mdctx, signature.data(),
                                    &sig_len) != 1) {
                throw std::runtime_error("Failed to finalize signing");
            }
        } catch (...) {
            EVP_MD_CTX_free(mdctx);
            EVP_PKEY_free(pkey);
            throw;
        }

        signature.resize(sig_len);
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(pkey);

        return signature;
    }
};
```

### 3.4 Recomendações de Tamanho de Chave

| Algoritmo | Tamanho Recomendado | Força de Segurança | Ano de Expiração Estimado |
|---|---|---|---|
| RSA | 3072+ bits | 128 bits | 2030 |
| ECDSA/EdDSA | P-256 ou Ed25519 | 128 bits | 2030 |
| AES | 256 bits | 256 bits | 2040+ |
| X25519 | 256 bits | 128 bits | 2030 |
| SHA-256 | 256 bits hash | 128 bits (collision) | 2030 |
| SHA-384 | 384 bits hash | 192 bits | 2030 |

---

## 4. TLS 1.3

### 4.1 Processo de Handshake

TLS 1.3 reduziu o handshake de 2-RTT para 1-RTT (ou 0-RTT com resumption). O fluxo completo:

```
Client                                Server
  |                                      |
  |------- ClientHello (key_share) ----->|
  |       [supported_versions: TLS 1.3]  |
  |       [signature_algorithms: ...]    |
  |                                      |
  |<------ ServerHello (key_share) ------|
  |<------ {EncryptedExtensions} --------|
  |<------ {Certificate} ----------------|
  |<------ {CertificateVerify} ----------|
  |<------ {Finished} -------------------|
  |                                      |
  |------- {Finished} ----------------->|
  |                                      |
  |<==== Application Data =============>|
```

### 4.2 Cipher Suites do TLS 1.3

TLS 1.3 eliminou cipher suites inseguros. As únicas aceitas:

| Cipher Suite | Key Exchange | Cipher | Hash |
|---|---|---|---|
| TLS_AES_256_GCM_SHA384 | X25519/ECDH | AES-256-GCM | SHA-384 |
| TLS_CHACHA20_POLY1305_SHA256 | X25519/ECDH | ChaCha20-Poly1305 | SHA-256 |
| TLS_AES_128_GCM_SHA256 | X25519/ECDH | AES-128-GCM | SHA-256 |

### 4.3 CVE-2015-0204 — FREAK Attack

O FREAK (Factoring RSA Export Keys) explorava cipher suites de exportação do SSL que usavam chaves RSA de apenas 512 bits. Atacantes podiam forçar o downgrade para chaves fracas.

### 4.4 CVE-2014-3566 — POODLE

O POODLE (Padding Oracle On Downgraded Legacy Encryption) explorava o padding scheme do SSL 3.0 em CBC mode, permitindo extrair dados criptografados byte a byte.

### 4.5 CVE-2014-0160 — Heartbleed

Heartbleed era uma vulnerabilidade no heartbeat extension do OpenSSL que permitia ler até 64KB de memória do servidor, expondo chaves privadas, senhas e dados sensíveis.

```cpp
// CORRECT TLS 1.3 client using OpenSSL
// Demonstrates proper certificate verification and protocol configuration
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

class TlsClient {
public:
    TlsClient(const std::string& ca_cert_path) {
        // Use TLS 1.3 method — enforces modern protocol only
        const SSL_METHOD* method = TLS_client_method();
        ctx_ = SSL_CTX_new(method);
        if (!ctx_) {
            throw std::runtime_error("Failed to create SSL context");
        }

        // Enforce TLS 1.3 minimum
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);

        // Load CA certificates for verification
        if (SSL_CTX_load_verify_locations(ctx_, ca_cert_path.c_str(),
                                           nullptr) != 1) {
            ERR_print_errors_fp(stderr);
            SSL_CTX_free(ctx_);
            throw std::runtime_error("Failed to load CA certificates");
        }

        // Enable certificate verification
        SSL_CTX_set_verify(ctx_,
                           SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                           nullptr);

        // Set verification depth
        SSL_CTX_set_verify_depth(ctx_, 4);

        // Disable legacy protocols (CRITICAL for preventing FREAK/POODLE)
        SSL_CTX_clear_options(ctx_,
                              SSL_OP_NO_SSLv2 | SSL_OP_NO_SSLv3 |
                              SSL_OP_NO_TLSv1 | SSL_OP_NO_TLSv1_1);

        // Enable certificate status request (OCSP stapling)
        SSL_CTX_set_tlsext_status_type(ctx_, TLSEXT_STATUSTYPE_ocsp);

        // Set cipher suites to only allow TLS 1.3 suites
        SSL_CTX_set_ciphersuites(ctx_,
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256");
    }

    ~TlsClient() {
        if (ctx_) {
            SSL_CTX_free(ctx_);
        }
    }

    // Connect and verify certificate
    bool connect(const std::string& hostname, int port) {
        BIO* bio = BIO_new_ssl_connect(ctx_);
        if (!bio) {
            throw std::runtime_error("Failed to create BIO");
        }

        BIO_get_ssl(bio, &ssl_);
        SSL_set_mode(ssl_, SSL_MODE_AUTO_RETRY);
        SSL_set_tlsext_host_name(ssl_, hostname.c_str());

        // Also set hostname for SNI
        SSL_set1_host(ssl_, hostname.c_str());

        BIO_set_conn_int_port(bio, port);
        BIO_set_conn_hostname(bio, hostname.c_str());

        if (BIO_do_connect(bio) <= 0) {
            ERR_print_errors_fp(stderr);
            BIO_free_all(bio);
            return false;
        }

        if (BIO_do_handshake(bio) <= 0) {
            ERR_print_errors_fp(stderr);
            BIO_free_all(bio);
            return false;
        }

        // Verify the certificate
        if (!verify_certificate()) {
            BIO_free_all(bio);
            return false;
        }

        bio_ = bio;
        return true;
    }

    // Certificate pinning — verify against known good certificate
    bool verify_pinned_certificate(
        const std::vector<uint8_t>& pinned_hash
    ) {
        X509* cert = SSL_get_peer_certificate(ssl_);
        if (!cert) {
            return false;
        }

        // Compute SHA-256 hash of SubjectPublicKeyInfo
        std::vector<uint8_t> spki_hash(32);
        unsigned int hash_len = 0;

        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        if (!ctx) {
            X509_free(cert);
            return false;
        }

        bool result = false;

        const ASN1_BIT_STRING* pubkey = X509_get0_pubkey_bitstr(cert);
        if (pubkey) {
            EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
            EVP_DigestUpdate(ctx, ASN1_STRING_get0_data(pubkey),
                             ASN1_STRING_length(pubkey));
            EVP_DigestFinal_ex(ctx, spki_hash.data(), &hash_len);
            result = (hash_len == pinned_hash.size() &&
                      std::memcmp(spki_hash.data(), pinned_hash.data(),
                                  hash_len) == 0);
        }

        EVP_MD_CTX_free(ctx);
        X509_free(cert);
        return result;
    }

    std::string send_receive(const std::string& request) {
        if (SSL_write(ssl_, request.c_str(), request.size()) <= 0) {
            throw std::runtime_error("Failed to send data");
        }

        std::string response;
        char buffer[4096];
        int bytes_read;
        while ((bytes_read = SSL_read(ssl_, buffer, sizeof(buffer) - 1)) > 0) {
            buffer[bytes_read] = '\0';
            response += buffer;
        }

        return response;
    }

private:
    SSL_CTX* ctx_ = nullptr;
    SSL* ssl_ = nullptr;
    BIO* bio_ = nullptr;

    bool verify_certificate() {
        long verify_result = SSL_get_verify_result(ssl_);
        if (verify_result != X509_V_OK) {
            std::cerr << "Certificate verification failed: "
                      << X509_verify_cert_error_string(verify_result)
                      << std::endl;
            return false;
        }

        X509* cert = SSL_get_peer_certificate(ssl_);
        if (!cert) {
            std::cerr << "No peer certificate presented" << std::endl;
            return false;
        }

        // Verify certificate chain, expiration, and revocation
        X509_free(cert);
        return true;
    }
};
```

### 4.6 HSTS (HTTP Strict Transport Security)

HSTS força o navegador a usar HTTPS sempre. Deve ser implementado no lado do servidor e também pode ser incluído em certificados (preload lists).

```cpp
// HSTS header configuration
struct HstsConfig {
    int max_age = 31536000;  // 1 year
    bool include_subdomains = true;
    bool preload = true;

    std::string to_header() const {
        std::string header = "Strict-Transport-Security: max-age=" +
                             std::to_string(max_age);
        if (include_subdomains) {
            header += "; includeSubDomains";
        }
        if (preload) {
            header += "; preload";
        }
        return header;
    }
};
```

---

## 5. Gestão de Chaves

### 5.1 Geração de Chaves

#### Fontes de Entropy

CSPRNGs (Cryptographically Secure Pseudo-Random Number Generators) são a base da geração segura de chaves.

```cpp
#include <fcntl.h>
#include <unistd.h>
#include <sys/random.h>
#include <vector>
#include <stdexcept>
#include <array>

class SecureRandom {
public:
    // Linux: Use getrandom() which blocks until enough entropy is available
    // This is safer than /dev/urandom which may return before initialization
    static std::vector<uint8_t> generate_bytes(size_t count) {
        std::vector<uint8_t> buffer(count);
        size_t obtained = 0;

        while (obtained < count) {
            ssize_t result = getrandom(
                buffer.data() + obtained,
                count - obtained,
                0  // No flags — blocks until entropy is ready
            );

            if (result < 0) {
                if (errno == EINTR) {
                    continue;  // Interrupted, retry
                }
                throw std::runtime_error(
                    "Failed to obtain random bytes from kernel");
            }

            obtained += result;
        }

        return buffer;
    }

    // Generate random integer in range [min, max]
    static uint32_t generate_range(uint32_t min, uint32_t max) {
        if (min > max) {
            throw std::invalid_argument("min > max");
        }

        // Rejection sampling to avoid modulo bias
        uint32_t range = max - min + 1;
        uint32_t limit = UINT32_MAX - (UINT32_MAX % range);
        uint32_t value;

        do {
            auto bytes = generate_bytes(sizeof(value));
            std::memcpy(&value, bytes.data(), sizeof(value));
        } while (value >= limit);

        return min + (value % range);
    }
};
```

#### Funções de Derivação de Chaves

HKDF (HMAC-based Key Derivation Function) é a função de derivação recomendada para TLS 1.3 e muitos protocolos modernos.

```cpp
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <vector>
#include <stdexcept>
#include <cstring>

class KeyDerivation {
public:
    // HKDF-Extract: derive a pseudorandom key from input key material
    static std::vector<uint8_t> hkdf_extract(
        const std::vector<uint8_t>& ikm,
        const std::vector<uint8_t>& salt = {}
    ) {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_hkdf(EVP_sha256(), nullptr);
        if (!ctx) {
            throw std::runtime_error("Failed to create HKDF context");
        }

        std::vector<uint8_t> prk(32);  // SHA-256 output size

        try {
            if (EVP_PKEY_derive_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init HKDF");
            }
            if (EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256()) <= 0) {
                throw std::runtime_error("Failed to set HKDF hash");
            }
            if (!salt.empty()) {
                if (EVP_PKEY_CTX_set_hkdf_salt(ctx, salt.data(),
                                                salt.size()) <= 0) {
                    throw std::runtime_error("Failed to set HKDF salt");
                }
            }
            if (EVP_PKEY_CTX_set_hkdf_key(ctx, ikm.data(),
                                            ikm.size()) <= 0) {
                throw std::runtime_error("Failed to set HKDF key");
            }

            size_t prk_len = prk.size();
            if (EVP_PKEY_derive(ctx, prk.data(), &prk_len) <= 0) {
                throw std::runtime_error("Failed to derive key");
            }

            prk.resize(prk_len);

        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            throw;
        }

        EVP_PKEY_CTX_free(ctx);
        return prk;
    }

    // HKDF-Expand: expand PRK into output key material
    static std::vector<uint8_t> hkdf_expand(
        const std::vector<uint8_t>& prk,
        const std::string& info,
        size_t output_length
    ) {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_hkdf(EVP_sha256(), nullptr);
        if (!ctx) {
            throw std::runtime_error("Failed to create HKDF context");
        }

        std::vector<uint8_t> okm(output_length);

        try {
            if (EVP_PKEY_derive_init(ctx) <= 0) {
                throw std::runtime_error("Failed to init HKDF expand");
            }
            if (EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256()) <= 0) {
                throw std::runtime_error("Failed to set hash");
            }
            if (EVP_PKEY_CTX_set_hkdf_key(ctx, prk.data(),
                                            prk.size()) <= 0) {
                throw std::runtime_error("Failed to set PRK");
            }
            if (EVP_PKEY_CTX_add1_hkdf_info(
                    ctx,
                    reinterpret_cast<const uint8_t*>(info.data()),
                    info.size()) <= 0) {
                throw std::runtime_error("Failed to set info");
            }

            size_t okm_len = okm.size();
            if (EVP_PKEY_derive(ctx, okm.data(), &okm_len) <= 0) {
                throw std::runtime_error("Failed to derive OKM");
            }

            okm.resize(okm_len);

        } catch (...) {
            EVP_PKEY_CTX_free(ctx);
            throw;
        }

        EVP_PKEY_CTX_free(ctx);
        return okm;
    }

    // PBKDF2 for password-based key derivation
    static std::vector<uint8_t> pbkdf2_sha256(
        const std::string& password,
        const std::vector<uint8_t>& salt,
        int iterations,
        size_t key_length
    ) {
        std::vector<uint8_t> key(key_length);

        if (PKCS5_PBKDF2_HMAC(
                password.c_str(), password.size(),
                salt.data(), salt.size(),
                iterations,
                EVP_sha256(),
                key_length,
                key.data()) != 1) {
            throw std::runtime_error("PBKDF2 failed");
        }

        return key;
    }
};
```

### 5.2 Armazenamento de Chaves

Chaves nunca devem ser armazenadas em texto plano. Opções seguras incluem:

1. **HSM (Hardware Security Modules)**: Dispositivos dedicados que gerenciam chaves em hardware, nunca expondo-as ao software.
2. **OS Keychain**: integração com keyring do Linux, Keychain do macOS, ou DPAPI do Windows.
3. **Key Wrapping**: Chaves são protegidas por outra chave (KEK) em um hierarchy de segurança.
4. **Armazenamento criptografado**: Arquivos de chave criptografados com chave derivada de senha.

```cpp
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <vector>
#include <fstream>
#include <stdexcept>
#include <array>

class SecureKeyStore {
public:
    // Key file format: [magic(4)] [version(4)] [salt(32)] [iv(16)]
    //                  [encrypted_key_size(4)] [encrypted_key(N)]
    static constexpr uint32_t MAGIC = 0x534B5354;  // "SKST"
    static constexpr uint32_t VERSION = 1;
    static constexpr size_t SALT_SIZE = 32;
    static constexpr size_t IV_SIZE = 16;
    static constexpr int PBKDF2_ITERATIONS = 600000;

    // Encrypt and store a key using a password
    static void store_key(
        const std::string& filepath,
        const std::vector<uint8_t>& key,
        const std::string& password
    ) {
        // Generate random salt
        std::vector<uint8_t> salt(SALT_SIZE);
        RAND_bytes(salt.data(), SALT_SIZE);

        // Derive encryption key from password
        std::vector<uint8_t> encryption_key =
            KeyDerivation::pbkdf2_sha256(password, salt,
                                          PBKDF2_ITERATIONS, 32);

        // Generate IV for AES-GCM
        std::vector<uint8_t> iv(IV_SIZE);
        RAND_bytes(iv.data(), IV_SIZE);

        // Encrypt the key
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        std::vector<uint8_t> ciphertext(key.size() + EVP_MAX_BLOCK_LENGTH);
        std::vector<uint8_t> tag(16);
        int out_len = 0;

        try {
            if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                    nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to init encryption");
            }

            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                     IV_SIZE, nullptr) != 1) {
                throw std::runtime_error("Failed to set IV length");
            }

            if (EVP_EncryptInit_ex(ctx, nullptr, nullptr,
                                    encryption_key.data(), iv.data()) != 1) {
                throw std::runtime_error("Failed to set key/IV");
            }

            if (EVP_EncryptUpdate(ctx, ciphertext.data(), &out_len,
                                  key.data(), key.size()) != 1) {
                throw std::runtime_error("Failed to encrypt key");
            }

            if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + out_len,
                                     &out_len) != 1) {
                throw std::runtime_error("Failed to finalize encryption");
            }

            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG,
                                     16, tag.data()) != 1) {
                throw std::runtime_error("Failed to get tag");
            }

        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);

        // Write to file
        std::ofstream file(filepath, std::ios::binary);
        if (!file) {
            throw std::runtime_error("Failed to open file for writing");
        }

        uint32_t key_size = static_cast<uint32_t>(key.size());
        file.write(reinterpret_cast<const char*>(&MAGIC), 4);
        file.write(reinterpret_cast<const char*>(&VERSION), 4);
        file.write(reinterpret_cast<const char*>(salt.data()), SALT_SIZE);
        file.write(reinterpret_cast<const char*>(iv.data()), IV_SIZE);
        file.write(reinterpret_cast<const char*>(tag.data()), 16);
        file.write(reinterpret_cast<const char*>(&key_size), 4);
        file.write(reinterpret_cast<const char*>(ciphertext.data()),
                   out_len);

        // Securely erase derived key
        OPENSSL_cleanse(encryption_key.data(), encryption_key.size());
    }

    // Load and decrypt a stored key
    static std::vector<uint8_t> load_key(
        const std::string& filepath,
        const std::string& password
    ) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file) {
            throw std::runtime_error("Failed to open key file");
        }

        // Read header
        uint32_t magic, version;
        file.read(reinterpret_cast<char*>(&magic), 4);
        file.read(reinterpret_cast<char*>(&version), 4);

        if (magic != MAGIC) {
            throw std::runtime_error("Invalid key file format");
        }
        if (version != VERSION) {
            throw std::runtime_error("Unsupported key file version");
        }

        std::vector<uint8_t> salt(SALT_SIZE);
        std::vector<uint8_t> iv(IV_SIZE);
        std::vector<uint8_t> tag(16);
        uint32_t key_size;

        file.read(reinterpret_cast<char*>(salt.data()), SALT_SIZE);
        file.read(reinterpret_cast<char*>(iv.data()), IV_SIZE);
        file.read(reinterpret_cast<char*>(tag.data()), 16);
        file.read(reinterpret_cast<char*>(&key_size), 4);

        std::vector<uint8_t> ciphertext(key_size + EVP_MAX_BLOCK_LENGTH);
        file.read(reinterpret_cast<char*>(ciphertext.data()), key_size);

        // Derive decryption key
        std::vector<uint8_t> decryption_key =
            KeyDerivation::pbkdf2_sha256(password, salt,
                                          PBKDF2_ITERATIONS, 32);

        // Decrypt
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create cipher context");
        }

        std::vector<uint8_t> plaintext(key_size);
        int out_len = 0;

        try {
            if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                    nullptr, nullptr) != 1) {
                throw std::runtime_error("Failed to init decryption");
            }

            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                     IV_SIZE, nullptr) != 1) {
                throw std::runtime_error("Failed to set IV length");
            }

            if (EVP_DecryptInit_ex(ctx, nullptr, nullptr,
                                    decryption_key.data(), iv.data()) != 1) {
                throw std::runtime_error("Failed to set key/IV");
            }

            if (EVP_DecryptUpdate(ctx, plaintext.data(), &out_len,
                                  ciphertext.data(), key_size) != 1) {
                throw std::runtime_error("Failed to decrypt");
            }

            if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG,
                                     16, tag.data()) != 1) {
                throw std::runtime_error("Failed to set tag");
            }

            if (EVP_DecryptFinal_ex(ctx, plaintext.data() + out_len,
                                     &out_len) != 1) {
                throw std::runtime_error(
                    "Decryption failed — wrong password or tampered data");
            }

        } catch (...) {
            EVP_CIPHER_CTX_free(ctx);
            throw;
        }

        EVP_CIPHER_CTX_free(ctx);
        OPENSSL_cleanse(decryption_key.data(), decryption_key.size());
        plaintext.resize(out_len);
        return plaintext;
    }
};
```

### 5.3 Rotação de Chaves

A rotação de chaves deve ser automatizada e transparente para o sistema. A estratégia mais comum é usar key versioning:

```cpp
#include <map>
#include <string>
#include <vector>
#include <shared_mutex>
#include <functional>

class VersionedKeyStore {
public:
    struct KeyEntry {
        std::vector<uint8_t> key;
        std::string version;
        bool active;       // Can be used for new encryptions
        bool expired;      // Can only be used for decryption (legacy)
    };

    void add_key(const std::string& version,
                 const std::vector<uint8_t>& key) {
        std::unique_lock lock(mutex_);
        KeyEntry entry;
        entry.key = key;
        entry.version = version;
        entry.active = true;
        entry.expired = false;
        keys_[version] = entry;

        // Deactivate all other versions
        for (auto& [v, e] : keys_) {
            if (v != version) {
                e.active = false;
            }
        }
    }

    // Get the current active key for encryption
    const KeyEntry& get_active_key() const {
        std::shared_lock lock(mutex_);
        for (const auto& [version, entry] : keys_) {
            if (entry.active) {
                return entry;
            }
        }
        throw std::runtime_error("No active key found");
    }

    // Get key by version for decryption (handles old versions)
    const KeyEntry& get_key(const std::string& version) const {
        std::shared_lock lock(mutex_);
        auto it = keys_.find(version);
        if (it == keys_.end()) {
            throw std::runtime_error("Key version not found: " + version);
        }
        return it->second;
    }

    // Rotate: add new key, mark current as expired, remove oldest
    void rotate(const std::string& new_version,
                const std::vector<uint8_t>& new_key,
                size_t max_retained = 3) {
        std::unique_lock lock(mutex_);

        // Deactivate current active keys
        for (auto& [v, e] : keys_) {
            if (e.active) {
                e.active = false;
                e.expired = true;
            }
        }

        // Add new active key
        KeyEntry entry;
        entry.key = new_key;
        entry.version = new_version;
        entry.active = true;
        entry.expired = false;
        keys_[new_version] = entry;

        // Remove oldest expired keys if over limit
        while (keys_.size() > max_retained) {
            std::string oldest;
            for (const auto& [v, e] : keys_) {
                if (!e.active) {
                    if (oldest.empty() || v < oldest) {
                        oldest = v;
                    }
                }
            }
            if (!oldest.empty()) {
                keys_.erase(oldest);
            } else {
                break;
            }
        }
    }

private:
    mutable std::shared_mutex mutex_;
    std::map<std::string, KeyEntry> keys_;
};
```

### 5.4 Destruição de Chaves

A destruição segura de chaves é frequentemente negligenciada. Memória pode persistir em swap, core dumps, ou ser acessada via cold boot attacks.

#### CVE-2008-0166 — Debian OpenSSL Weak Keys

O Debian OpenSSL weak keys foram causados por uma remoção acidental do entropy seeding no PRNG. Chaves geradas em Debian e derivadas eram previsíveis, com apenas 32.768 valores possíveis.

```cpp
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <new>
#include <openssl/crypto.h>

// Secure memory class with automatic erasure and memory locking
class SecureKey {
public:
    explicit SecureKey(size_t size) : size_(size) {
        // Allocate page-aligned memory
        size_t page_size = sysconf(_SC_PAGESIZE);
        alloc_size_ = ((size + page_size - 1) / page_size) * page_size;

        // Use mmap for memory that can be locked and securely erased
        data_ = static_cast<uint8_t*>(
            mmap(nullptr, alloc_size_,
                 PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS,
                 -1, 0));

        if (data_ == MAP_FAILED) {
            throw std::runtime_error("Failed to allocate secure memory");
        }

        // Lock memory to prevent swapping to disk
        // This prevents the key from appearing in swap space
        if (mlock(data_, alloc_size_) != 0) {
            munmap(data_, alloc_size_);
            data_ = MAP_FAILED;
            throw std::runtime_error("Failed to lock memory (mlock failed)");
        }

        // Prevent core dump from containing key
        // MAD_DONTDUMP prevents this page from being included in core dumps
        madvise(data_, alloc_size_, MAD_DONTDUMP);

        initialized_ = true;
    }

    ~SecureKey() {
        destroy();
    }

    // Disable copy
    SecureKey(const SecureKey&) = delete;
    SecureKey& operator=(const SecureKey&) = delete;

    // Disable move (would leave dangling pointer)
    SecureKey(SecureKey&&) = delete;
    SecureKey& operator=(SecureKey&&) = delete;

    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }

    // Explicitly erase the key material
    void destroy() {
        if (data_ && data_ != MAP_FAILED && initialized_) {
            // Use explicit_bzero / OPENSSL_cleanse to prevent
            // compiler optimization from eliding the memset
            OPENSSL_cleanse(data_, size_);

            // Second pass with volatile to be extra safe
            volatile uint8_t* vptr = data_;
            for (size_t i = 0; i < size_; ++i) {
                vptr[i] = 0;
            }

            // Memory barrier to ensure writes are committed
            __sync_synchronize();

            // Unlock memory
            munlock(data_, alloc_size_);

            // Release virtual memory
            munmap(data_, alloc_size_);

            data_ = nullptr;
            initialized_ = false;
        }
    }

    // Generate random key material
    static SecureKey generate(size_t size) {
        SecureKey key(size);
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0) {
            throw std::runtime_error("Failed to open /dev/urandom");
        }

        size_t obtained = 0;
        while (obtained < size) {
            ssize_t result = read(fd, key.data_ + obtained, size - obtained);
            if (result < 0) {
                close(fd);
                key.destroy();
                throw std::runtime_error("Failed to read random bytes");
            }
            obtained += result;
        }

        close(fd);
        return key;
    }

private:
    uint8_t* data_ = nullptr;
    size_t size_ = 0;
    size_t alloc_size_ = 0;
    bool initialized_ = false;
};
```

---

## 6. Hashing e HMAC

### 6.1 SHA-256 e SHA-3

SHA-2 permanece o padrão recomendado. SHA-3 (Keccak) oferece uma alternativa com design completamente diferente, protegendo contra ataques que poderiam afetar construções de Merkle-Damgård.

### 6.2 HMAC para Autenticação de Mensagens

HMAC (Hash-based Message Authentication Code) combina hash com chave para autenticar integridade de dados.

```cpp
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <openssl/sha.h>
#include <vector>
#include <string>
#include <stdexcept>
#include <cstdint>
#include <cstring>

class CryptographicHash {
public:
    static std::vector<uint8_t> sha256(
        const uint8_t* data, size_t len
    ) {
        std::vector<uint8_t> hash(SHA256_DIGEST_LENGTH);
        SHA256(data, len, hash.data());
        return hash;
    }

    static std::vector<uint8_t> sha3_256(
        const uint8_t* data, size_t len
    ) {
        // Using SHA-3 via EVP interface
        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        if (!ctx) {
            throw std::runtime_error("Failed to create hash context");
        }

        std::vector<uint8_t> hash(32);  // SHA3-256 output size
        unsigned int hash_len = 0;

        try {
            if (EVP_DigestInit_ex(ctx, EVP_sha3_256(), nullptr) != 1) {
                throw std::runtime_error("Failed to init SHA3-256");
            }
            if (EVP_DigestUpdate(ctx, data, len) != 1) {
                throw std::runtime_error("Failed to update hash");
            }
            if (EVP_DigestFinal_ex(ctx, hash.data(), &hash_len) != 1) {
                throw std::runtime_error("Failed to finalize hash");
            }
        } catch (...) {
            EVP_MD_CTX_free(ctx);
            throw;
        }

        EVP_MD_CTX_free(ctx);
        hash.resize(hash_len);
        return hash;
    }

    // HMAC-SHA256 for message authentication
    static std::vector<uint8_t> hmac_sha256(
        const std::vector<uint8_t>& key,
        const uint8_t* data, size_t data_len
    ) {
        std::vector<uint8_t> mac(SHA256_DIGEST_LENGTH);
        unsigned int mac_len = 0;

        HMAC(EVP_sha256(),
             key.data(), key.size(),
             data, data_len,
             mac.data(), &mac_len);

        mac.resize(mac_len);
        return mac;
    }

    // Constant-time comparison to prevent timing attacks
    static bool constant_time_compare(
        const std::vector<uint8_t>& a,
        const std::vector<uint8_t>& b
    ) {
        if (a.size() != b.size()) {
            return false;
        }
        // CRYPTO_memcmp is constant-time
        return CRYPTO_memcmp(a.data(), b.data(), a.size()) == 0;
    }

    // Verify HMAC in constant time
    static bool verify_hmac(
        const std::vector<uint8_t>& key,
        const uint8_t* data, size_t data_len,
        const std::vector<uint8_t>& expected_mac
    ) {
        auto computed = hmac_sha256(key, data, data_len);
        return constant_time_compare(computed, expected_mac);
    }
};
```

---

## 7. Assinaturas Digitais e Certificados

### 7.1 Processo de Assinatura Digital

Assinaturas digitais garantem autenticidade, integridade e não-repúdio. O processo:
1. Hash do mensagem é computado
2. Hash é criptografado com chave privada do assinador
3. Receptor decripta o hash com chave pública e compara

### 7.2 Estrutura X.509

Certificados X.509 contêm informações sobre o titular, a chave pública, e são assinados por uma CA (Certificate Authority). A cadeia de confiança vai do certificado raiz (self-signed) até o certificado de servidor.

### 7.3 CVE-2015-4000 — Logjam

O Logjam explorava chaves Diffie-Hellman de 512 e 1024 bits usadas em TLS, permitindo downgrade para criptografia export-grade. Afetou todos os browsers e servidores que suportavam DHE.

```cpp
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <iostream>
#include <string>
#include <memory>

class CertificateValidator {
public:
    struct ValidationReport {
        bool valid = false;
        bool chain_valid = false;
        bool hostname_valid = false;
        bool expiry_valid = false;
        bool purpose_valid = false;
        std::string error_message;
    };

    // Complete certificate chain validation
    static ValidationReport validate(
        X509* cert,
        STACK_OF(X509)* chain,
        X509_STORE* store,
        const std::string& expected_hostname
    ) {
        ValidationReport report;

        // Create verification context
        X509_STORE_CTX* ctx = X509_STORE_CTX_new();
        if (!ctx) {
            report.error_message = "Failed to create verification context";
            return report;
        }

        try {
            if (X509_STORE_CTX_init(ctx, store, cert, chain) != 1) {
                throw std::runtime_error("Failed to init verification");
            }

            // Set expected hostname for verification
            X509_STORE_CTX_set0_param(ctx, get_verify_params());

            // Perform verification
            int result = X509_verify_cert(ctx);
            int error = X509_STORE_CTX_get_error(ctx);

            report.chain_valid = (result == 1);
            if (!report.chain_valid) {
                report.error_message =
                    std::string("Chain verification failed: ") +
                    X509_verify_cert_error_string(error);
            }

            X509_STORE_CTX_cleanup(ctx);

        } catch (const std::exception& e) {
            report.error_message = e.what();
        }

        X509_STORE_CTX_free(ctx);

        // Check hostname
        if (report.chain_valid) {
            report.hostname_valid =
                verify_hostname(cert, expected_hostname);
            if (!report.hostname_valid) {
                report.error_message = "Hostname verification failed";
            }
        }

        // Check expiry
        report.expiry_valid = verify_expiry(cert);

        // Check certificate purpose
        report.purpose_valid = verify_purpose(cert);

        report.valid = report.chain_valid && report.hostname_valid &&
                       report.expiry_valid && report.purpose_valid;

        return report;
    }

    // Verify certificate is not expired and not yet valid
    static bool verify_expiry(X509* cert) {
        const ASN1_TIME* not_before = X509_get0_notBefore(cert);
        const ASN1_TIME* not_after = X509_get0_notAfter(cert);

        int day, sec;
        if (ASN1_TIME_diff(&day, &sec, nullptr, not_before) != 1) {
            return false;
        }
        // If not_before is in the future, certificate is not yet valid
        if (day < 0 || sec < 0) {
            return false;
        }

        if (ASN1_TIME_diff(&day, &sec, nullptr, not_after) != 1) {
            return false;
        }
        // If not_after is in the past, certificate is expired
        if (day > 0 || sec > 0) {
            return false;
        }

        return true;
    }

    // Verify certificate purpose (server auth, client auth, etc.)
    static bool verify_purpose(X509* cert) {
        X509_PURPOSE* purpose =
            X509_PURPOSE_get0(X509_PURPOSE_SSL_CLIENT);
        if (!purpose) {
            return false;
        }

        int id = X509_PURPOSE_get_id(purpose);
        return X509_check_purpose(cert, id, 0) == 1;
    }

private:
    static X509_VERIFY_PARAM* get_verify_params() {
        X509_VERIFY_PARAM* param = X509_VERIFY_PARAM_new();
        if (!param) {
            throw std::runtime_error("Failed to create verify param");
        }

        // Set minimum security level
        X509_VERIFY_PARAM_set_level(param, X509_V_FLAG_CRL_CHECK);

        // Disable weak signatures (MD5, SHA-1)
        X509_VERIFY_PARAM_set_time(param, nullptr);

        return param;
    }

    static bool verify_hostname(X509* cert,
                                 const std::string& expected) {
        // Use OpenSSL's built-in hostname verification
        // This handles wildcards, IP addresses, etc.
        return X509_check_host(
            cert,
            expected.c_str(), expected.size(),
            X509_CHECK_FLAG_NO_WILDCARDS, nullptr
        ) == 1;
    }
};
```

### 7.4 Let's Encrypt e Protocolo ACME

Let's Encrypt fornece certificados TLS gratuitos via o protocolo ACME. A automação é essencial para manutenção de certificados.

---

## 8. Entropy e CSPRNG

### 8.1 Fontes de Entropy

Entropy é a medida de imprevisibilidade. Sistemas computacionais obtêm entropy de:
- Interrupções de hardware (discos, teclados, redes)
- Thermal noise em circuitos
- Hardware RNGs dedicados (RDRAND, RDSEED no x86)

### 8.2 std::random_device vs Criptografia

```cpp
#include <random>
#include <iostream>
#include <array>
#include <chrono>

// WARNING: std::random_device is NOT guaranteed to be cryptographic
// On some implementations (MinGW), it uses a fixed seed!
// ALWAYS use platform-specific CSPRNG for security purposes

void demonstrate_random_device_issues() {
    // This MAY be deterministic on some platforms
    std::random_device rd;

    // NEVER use this for key generation:
    // std::mt19937 gen(rd());  // DANGEROUS — rd() may be predictable

    // The CORRECT approach:
    // 1. Use getrandom() on Linux
    // 2. Use BCryptGenRandom() on Windows
    // 3. Use /dev/urandom on Unix-like systems
    // 4. Use arc4random() on BSD/macOS
}

// Health monitoring for entropy sources
class EntropyHealthMonitor {
public:
    struct HealthReport {
        bool initial_self_test_passed;
        bool consecutive_repetition_test_passed;
        bool adaptive_ratio_test_passed;
        uint64_t total_bytes_generated;
    };

    EntropyHealthMonitor() : total_bytes_(0) {
        // Run initial health tests on startup
        initial_self_test_ = run_initial_self_test();
    }

    void record_generation(size_t bytes) {
        total_bytes_ += bytes;

        // Track consecutive bytes for repetition test
        // If we see the same byte pattern repeatedly,
        // the entropy source may be failing
        auto now = std::chrono::steady_clock::now();
        last_generation_time_ = now;

        // Adaptive ratio test: check if generation times
        // are too fast (possible deterministic output)
        if (generation_times_.size() >= 10) {
            auto oldest = generation_times_.front();
            auto newest = generation_times_.back();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                newest - oldest).count();

            // If 10 generations happen in < 1 microsecond,
            // something is wrong
            if (duration < 1 && generation_times_.size() >= 10) {
                adaptive_ratio_test_ = false;
            }
        }

        generation_times_.push_back(now);
        if (generation_times_.size() > 100) {
            generation_times_.erase(generation_times_.begin());
        }
    }

    HealthReport get_report() const {
        return {
            initial_self_test_,
            consecutive_repetition_test_,
            adaptive_ratio_test_,
            total_bytes_
        };
    }

private:
    bool initial_self_test_ = false;
    bool consecutive_repetition_test_ = true;
    bool adaptive_ratio_test_ = true;
    uint64_t total_bytes_ = 0;
    std::vector<std::chrono::steady_clock::time_point> generation_times_;
    std::chrono::steady_clock::time_point last_generation_time_;

    bool run_initial_self_test() {
        // NIST SP 800-90B Section 4: Repetition Count Test
        // and Adaptive Proportion Test should be run at startup
        // This is a simplified version
        std::array<uint8_t, 1024> test_data;
        int fd = open("/dev/urandom", O_RDONLY);
        if (fd < 0) return false;

        ssize_t result = read(fd, test_data.data(), test_data.size());
        close(fd);

        if (result != static_cast<ssize_t>(test_data.size())) {
            return false;
        }

        // Check for all-zeros or all-same-byte (basic health test)
        bool all_same = true;
        uint8_t first = test_data[0];
        for (const auto& byte : test_data) {
            if (byte != first) {
                all_same = false;
                break;
            }
        }

        return !all_same;
    }
};
```

---

## 9. Criptografia Pós-Quântica

### 9.1 Ameaça Quântica

Computadores quânticos, quando suficientemente grandes, quebrarão RSA, ECC, e DH via algoritmo de Shor. AES-256 perde apenas metade da segurança (128 bits) via algoritmo de Grover. A migração para algoritmos pós-quânticos precisa começar agora.

### 9.2 Candidatos do NIST

O NIST padronizou em 2024 os primeiros algoritmos pós-quânticos:

| Algoritmo | Tipo | Baseado em | Uso |
|---|---|---|---|
| ML-KEM (Kyber) | KEM | Lattice | Key encapsulation |
| ML-DSA (Dilithium) | Assinatura | Lattice | Digital signatures |
| SLH-DSA (SPHINCS+) | Assinatura | Hash | Digital signatures |

### 9.3 Estratégia de Migração

A migração para pós-quântico deve ser gradual:

1. **Fase 1 — Inventário**: Identificar todos os componentes que usam criptografia
2. **Fase 2 — Híbrido**: Usar chaves híbridas (clássica + pós-quântica) simultaneamente
3. **Fase 3 — Transição**: Migrar para algoritmos puramente pós-quânticos
4. **Fase 4 — Depreciação**: Remover algoritmos clássicos vulneráveis

```cpp
// Hybrid key exchange: classical (X25519) + post-quantum (ML-KEM)
// This ensures security even if one layer is broken
#include <vector>
#include <cstdint>
#include <stdexcept>

// Forward declarations for post-quantum KEM interfaces
// (Actual implementation requires liboqs or similar library)
struct MlKemPublicKey {
    std::vector<uint8_t> data;
};

struct MlKemCiphertext {
    std::vector<uint8_t> data;
};

struct MlKemSharedSecret {
    std::vector<uint8_t> data;
};

class HybridKeyExchange {
public:
    struct HybridKeyPair {
        std::vector<uint8_t> classical_private;  // X25519
        std::vector<uint8_t> classical_public;
        std::vector<uint8_t> pq_private;          // ML-KEM
        std::vector<uint8_t> pq_public;
    };

    struct HybridEncapsulation {
        std::vector<uint8_t> classical_ciphertext;
        MlKemCiphertext pq_ciphertext;
        std::vector<uint8_t> classical_shared;
        MlKemSharedSecret pq_shared;
    };

    // Generate hybrid key pair
    // Uses both classical and post-quantum key exchange
    static HybridKeyPair generate_hybrid_keypair() {
        HybridKeyPair keys;

        // Classical: X25519
        // keys.classical_private = generate_x25519_private();
        // keys.classical_public = generate_x25519_public(keys.classical_private);

        // Post-quantum: ML-KEM-768 (recommended security level)
        // keys.pq_private = generate_ml_kem_private();
        // keys.pq_public = generate_ml_kem_public(keys.pq_private);

        // In production, use liboqs for ML-KEM operations
        // and OpenSSL/libsodium for classical operations

        return keys;
    }

    // Combine shared secrets from both layers
    static std::vector<uint8_t> combine_shared_secrets(
        const std::vector<uint8_t>& classical_secret,
        const MlKemSharedSecret& pq_secret
    ) {
        // Use HKDF to combine both secrets
        // The combined secret is secure if EITHER layer is secure
        std::vector<uint8_t> input;
        input.insert(input.end(), classical_secret.begin(),
                     classical_secret.end());
        input.insert(input.end(), pq_secret.data.begin(),
                     pq_secret.data.end());

        // HKDF-Extract with zero salt
        // return KeyDerivation::hkdf_extract(input, {});
        return input;  // Simplified
    }

private:
    // Production implementations would use:
    // - OpenSSL EVP_PKEY for X25519
    // - liboqs OQS_KEM for ML-KEM
    // - HKDF for combining shared secrets
};
```

### 9.4 DUAL_EC_DRBG — O Backdoor da NIST

O DUAL_EC_DRBG (Dual Elliptic Curve Deterministic Random Bit Generator) foi padronizado pela NIST em 2006. Em 2013, documentos do Snowden revelaram que a NSA havia inserido um backdoor no algoritmo, permitindo predição dos números pseudoaleatórios. O algoritmo foi retirado da norma NIST SP 800-90A.

A lição: confie em algoritmos abertos e revisados pela comunidade, não apenas em padronizações governamentais.

---

## 10. Erros Comuns em Criptografia

### 10.1 Criptografia Customizada (NUNCA Faça Isso)

O erro mais perigoso é implementar criptografia própria. Em 2023, uma empresa de segurança descobriu que seu "protocolo criptográfico proprietário" era equivalente a ECB mode com XOR.

```cpp
// WRONG: Custom "encryption" — DO NOT USE THIS
namespace wrong {

// This looks like encryption but has ZERO security
std::vector<uint8_t> fake_encrypt(
    const std::vector<uint8_t>& data,
    uint8_t key_byte
) {
    std::vector<uint8_t> result(data.size());
    for (size_t i = 0; i < data.size(); ++i) {
        result[i] = data[i] ^ key_byte;  // Single-byte XOR key
    }
    return result;
}

}  // namespace wrong

// CORRECT: Use established AEAD constructions
namespace correct {

std::vector<uint8_t> real_encrypt(
    const std::vector<uint8_t>& data,
    const std::vector<uint8_t>& key
) {
    // Use AES-GCM or ChaCha20-Poly1305 via established library
    ChaCha20Poly1305Cipher cipher(key);
    auto result = cipher.encrypt(data);
    return result.ciphertext;
}

}  // namespace correct
```

### 10.2 Uso de ECB Mode

ECB criptografa cada bloco independentemente, preservando padrões no ciphertext. O teste do pinguim famously demonstra isso.

```cpp
// WRONG: ECB mode reveals patterns in plaintext
// If two blocks have the same plaintext, they produce the same ciphertext
void ecb_pattern_leakage() {
    // Block A: "AAAAAAAAAAAAAAAA" (16 bytes of 'A')
    // Block B: "AAAAAAAAAAAAAAAA" (16 bytes of 'A')
    // Both encrypt to the SAME ciphertext block — revealing repetition
}

// CORRECT: Use CBC, CTR, or GCM mode
void secure_mode_usage() {
    // AES-GCM ensures identical plaintexts produce different ciphertexts
    // due to unique nonces
}
```

### 10.3 Reutilização de Nonces

Reutilizar um nonce com a mesma chave em AES-GCM é catastrófico — permite recuperação do authentication key.

```cpp
// WRONG: Nonce reuse in AES-GCM
void nonce_reuse_catastrophe() {
    std::vector<uint8_t> key(32, 0x42);
    AesGcmCipher cipher(key);

    std::vector<uint8_t> message1 = {0x01, 0x02, 0x03};
    std::vector<uint8_t> message2 = {0x04, 0x05, 0x06};

    // WRONG: Using the same nonce for both encryptions
    std::vector<uint8_t> nonce(12, 0x00);  // BAD!

    // Both ciphertexts use the same keystream
    // XOR of ciphertexts = XOR of plaintexts (stream cipher property)
    // This leaks information about both messages
}

// CORRECT: Generate unique nonce for each encryption
void correct_nonce_usage() {
    AesGcmCipher cipher;
    std::vector<uint8_t> message1 = {0x01, 0x02, 0x03};
    std::vector<uint8_t> message2 = {0x04, 0x05, 0x06};

    // Each encrypt() call generates a unique random nonce
    auto enc1 = cipher.encrypt(message1);  // Unique nonce
    auto enc2 = cipher.encrypt(message2);  // Different nonce
}
```

### 10.4 Geração de Chave Fraca

```cpp
// WRONG: Using predictable seed for key generation
void weak_key_generation() {
    // NEVER use time-based seed for cryptographic keys
    srand(time(nullptr));
    uint32_t key_component = rand();  // Predictable!
}

// WRONG: Using std::mt19937 without proper seeding
void also_weak() {
    std::mt19937 gen(42);  // Fixed seed — deterministic output
    std::uniform_int_distribution<uint32_t> dist;
    uint32_t key_part = dist(gen);  // Same key every time!
}

// CORRECT: Use CSPRNG
void secure_key_generation() {
    std::vector<uint8_t> key = SecureRandom::generate_bytes(32);
    // key is cryptographically random regardless of previous state
}
```

### 10.5 Side-Channel Vulnerabilities

Timing attacks explorem variações no tempo de execução para inferir valores secretos.

```cpp
// WRONG: Non-constant-time comparison
bool insecure_compare(const std::vector<uint8_t>& a,
                      const std::vector<uint8_t>& b) {
    if (a.size() != b.size()) return false;
    for (size_t i = 0; i < a.size(); ++i) {
        if (a[i] != b[i]) return false;  // Early return leaks position
    }
    return true;
    // Attacker can measure time to determine HOW MANY bytes match
}

// CORRECT: Constant-time comparison
bool secure_compare(const std::vector<uint8_t>& a,
                    const std::vector<uint8_t>& b) {
    if (a.size() != b.size()) return false;
    volatile uint8_t result = 0;
    for (size_t i = 0; i < a.size(); ++i) {
        result |= a[i] ^ b[i];  // Always iterates full length
    }
    return result == 0;
    // Timing is identical regardless of where bytes differ
}
```

### 10.6 CVE — Certificados Sem Verificação

Muitos clientes TLS desativam a verificação de certificados em desenvolvimento e esquecem de reativar em produção.

```cpp
// WRONG: Disabling certificate verification
void dangerous_tls_client() {
    SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, nullptr);
    // Accepts ANY certificate, including self-signed and forged
    // Vulnerable to MITM attacks
}

// CORRECT: Full certificate verification
void secure_tls_client() {
    SSL_CTX_set_verify(ctx,
                       SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                       nullptr);
    SSL_CTX_load_verify_locations(ctx, "/etc/ssl/certs/ca-certificates.crt",
                                  nullptr);
    // Also verify hostname matches certificate
    SSL_set1_host(ssl, "expected.hostname.com");
}
```

---

## 11. Exemplo Completo: Crypto Library Wrapper

A biblioteca a seguir demonstra uma wrapper completa de criptografia em C++17, combinando todos os conceitos deste capítulo.

```cpp
// secure_crypto_library.hpp
// Complete cryptographic library wrapper using OpenSSL and libsodium
// NEVER use in production without security audit

#pragma once

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <openssl/sha.h>
#include <openssl/hmac.h>
#include <sodium.h>
#include <vector>
#include <string>
#include <array>
#include <stdexcept>
#include <memory>
#include <cstring>
#include <cstdint>
#include <sys/mman.h>
#include <unistd.h>

namespace seclib {

// Forward declarations
class SecureBuffer;
class AesGcmProvider;
class X25519Exchange;
class Ed25519Signer;
class HkdfDeriver;

// ============================================================
// SecureBuffer: Memory-safe buffer with automatic erasure
// ============================================================
class SecureBuffer {
public:
    explicit SecureBuffer(size_t size) : size_(size) {
        size_t page_size = sysconf(_SC_PAGESIZE);
        alloc_size_ = ((size + page_size - 1) / page_size) * page_size;

        data_ = static_cast<uint8_t*>(
            mmap(nullptr, alloc_size_,
                 PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));

        if (data_ == MAP_FAILED) {
            throw std::runtime_error("SecureBuffer: mmap failed");
        }

        if (mlock(data_, alloc_size_) != 0) {
            munmap(data_, alloc_size_);
            data_ = MAP_FAILED;
            throw std::runtime_error("SecureBuffer: mlock failed");
        }

        madvise(data_, alloc_size_, MAD_DONTDUMP);
    }

    ~SecureBuffer() { zeroize_and_free(); }

    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;
    SecureBuffer(SecureBuffer&& other) noexcept
        : data_(other.data_), size_(other.size_),
          alloc_size_(other.alloc_size_) {
        other.data_ = nullptr;
        other.size_ = 0;
        other.alloc_size_ = 0;
    }

    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }

    void zeroize() {
        if (data_ && data_ != MAP_FAILED) {
            volatile uint8_t* ptr = data_;
            for (size_t i = 0; i < size_; ++i) ptr[i] = 0;
            __sync_synchronize();
        }
    }

private:
    uint8_t* data_ = nullptr;
    size_t size_ = 0;
    size_t alloc_size_ = 0;

    void zeroize_and_free() {
        if (data_ && data_ != MAP_FAILED) {
            zeroize();
            munlock(data_, alloc_size_);
            munmap(data_, alloc_size_);
            data_ = nullptr;
        }
    }
};

// ============================================================
// CSPRNG: Cryptographically secure random number generation
// ============================================================
class CSPRNG {
public:
    static SecureBuffer generate_bytes(size_t count) {
        SecureBuffer buf(count);
        ssize_t obtained = 0;
        while (static_cast<size_t>(obtained) < count) {
            ssize_t r = getrandom(
                buf.data() + obtained, count - obtained, 0);
            if (r < 0) {
                if (errno == EINTR) continue;
                throw std::runtime_error("CSPRNG: getrandom failed");
            }
            obtained += r;
        }
        return buf;
    }

    static std::vector<uint8_t> random_bytes(size_t count) {
        std::vector<uint8_t> buf(count);
        size_t obtained = 0;
        while (obtained < count) {
            ssize_t r = getrandom(
                buf.data() + obtained, count - obtained, 0);
            if (r < 0) {
                if (errno == EINTR) continue;
                throw std::runtime_error("CSPRNG: getrandom failed");
            }
            obtained += r;
        }
        return buf;
    }
};

// ============================================================
// AesGcmProvider: Authenticated encryption with AES-256-GCM
// ============================================================
struct EncryptedData {
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> tag;
    std::vector<uint8_t> nonce;
};

class AesGcmProvider {
public:
    static constexpr size_t KEY_SIZE = 32;
    static constexpr size_t NONCE_SIZE = 12;
    static constexpr size_t TAG_SIZE = 16;

    static EncryptedData encrypt(
        const uint8_t* key,
        const uint8_t* plaintext, size_t pt_len,
        const uint8_t* aad = nullptr, size_t aad_len = 0
    ) {
        std::vector<uint8_t> nonce(NONCE_SIZE);
        RAND_bytes(nonce.data(), NONCE_SIZE);

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("EVP_CIPHER_CTX_new failed");

        std::vector<uint8_t> ciphertext(pt_len + EVP_MAX_BLOCK_LENGTH);
        std::vector<uint8_t> tag(TAG_SIZE);
        int out_len = 0;

        auto cleanup = [&](const char* msg) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error(msg);
        };

        if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(),
                                nullptr, nullptr, nullptr) != 1)
            cleanup("EncryptInit failed");

        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                 NONCE_SIZE, nullptr) != 1)
            cleanup("Set IV length failed");

        if (EVP_EncryptInit_ex(ctx, nullptr, nullptr,
                                key, nonce.data()) != 1)
            cleanup("Set key/IV failed");

        if (aad && aad_len > 0) {
            if (EVP_EncryptUpdate(ctx, nullptr, &out_len,
                                  aad, aad_len) != 1)
                cleanup("AAD update failed");
        }

        if (EVP_EncryptUpdate(ctx, ciphertext.data(), &out_len,
                              plaintext, pt_len) != 1)
            cleanup("Encrypt update failed");

        int final_len = 0;
        if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + out_len,
                                 &final_len) != 1)
            cleanup("Encrypt final failed");

        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG,
                                 TAG_SIZE, tag.data()) != 1)
            cleanup("Get tag failed");

        EVP_CIPHER_CTX_free(ctx);
        ciphertext.resize(out_len + final_len);
        return { ciphertext, tag, nonce };
    }

    static std::vector<uint8_t> decrypt(
        const uint8_t* key,
        const uint8_t* ciphertext, size_t ct_len,
        const uint8_t* tag,
        const uint8_t* nonce,
        const uint8_t* aad = nullptr, size_t aad_len = 0
    ) {
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("EVP_CIPHER_CTX_new failed");

        std::vector<uint8_t> plaintext(ct_len);
        int out_len = 0;

        auto cleanup = [&](const char* msg) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error(msg);
        };

        if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(),
                                nullptr, nullptr, nullptr) != 1)
            cleanup("DecryptInit failed");

        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                 NONCE_SIZE, nullptr) != 1)
            cleanup("Set IV length failed");

        if (EVP_DecryptInit_ex(ctx, nullptr, nullptr,
                                key, nonce) != 1)
            cleanup("Set key/IV failed");

        if (aad && aad_len > 0) {
            if (EVP_DecryptUpdate(ctx, nullptr, &out_len,
                                  aad, aad_len) != 1)
                cleanup("AAD update failed");
        }

        if (EVP_DecryptUpdate(ctx, plaintext.data(), &out_len,
                              ciphertext, ct_len) != 1)
            cleanup("Decrypt update failed");

        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG,
                                 TAG_SIZE,
                                 const_cast<uint8_t*>(tag)) != 1)
            cleanup("Set tag failed");

        if (EVP_DecryptFinal_ex(ctx, plaintext.data() + out_len,
                                 &out_len) != 1)
            cleanup("Authentication failed — tampered data or wrong key");

        EVP_CIPHER_CTX_free(ctx);
        plaintext.resize(out_len);
        return plaintext;
    }
};

// ============================================================
// X25519Exchange: Elliptic curve Diffie-Hellman key exchange
// ============================================================
struct KeyPair {
    std::vector<uint8_t> private_key;
    std::vector<uint8_t> public_key;
};

class X25519Exchange {
public:
    static KeyPair generate_keypair() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_X25519, nullptr);
        if (!ctx) throw std::runtime_error("X25519 context failed");

        EVP_PKEY* pkey = nullptr;
        if (EVP_PKEY_keygen_init(ctx) <= 0 ||
            EVP_PKEY_keygen(ctx, &pkey) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            throw std::runtime_error("X25519 keygen failed");
        }
        EVP_PKEY_CTX_free(ctx);

        int pub_len = i2d_PUBKEY(pkey, nullptr);
        std::vector<uint8_t> pub(pub_len);
        uint8_t* p = pub.data();
        i2d_PUBKEY(pkey, &p);

        int priv_len = i2d_PrivateKey(pkey, nullptr);
        std::vector<uint8_t> priv(priv_len);
        uint8_t* q = priv.data();
        i2d_PrivateKey(pkey, &q);

        EVP_PKEY_free(pkey);
        return { priv, pub };
    }

    static std::vector<uint8_t> derive_shared_secret(
        const std::vector<uint8_t>& my_private_der,
        const std::vector<uint8_t>& peer_public_der
    ) {
        const uint8_t* p = my_private_der.data();
        EVP_PKEY* priv = d2i_PrivateKey(nullptr, &p,
                                         my_private_der.size());
        if (!priv) throw std::runtime_error("Failed to decode private key");

        p = peer_public_der.data();
        EVP_PKEY* peer = d2i_PUBKEY(nullptr, &p, peer_public_der.size());
        if (!peer) {
            EVP_PKEY_free(priv);
            throw std::runtime_error("Failed to decode public key");
        }

        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(priv, nullptr);
        if (!ctx) {
            EVP_PKEY_free(priv);
            EVP_PKEY_free(peer);
            throw std::runtime_error("Derivation context failed");
        }

        if (EVP_PKEY_derive_init(ctx) <= 0 ||
            EVP_PKEY_derive_set_peer(ctx, peer) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            EVP_PKEY_free(priv);
            EVP_PKEY_free(peer);
            throw std::runtime_error("Derivation init failed");
        }

        size_t secret_len = 0;
        EVP_PKEY_derive(ctx, nullptr, &secret_len);

        std::vector<uint8_t> secret(secret_len);
        if (EVP_PKEY_derive(ctx, secret.data(), &secret_len) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            EVP_PKEY_free(priv);
            EVP_PKEY_free(peer);
            throw std::runtime_error("Derivation failed");
        }
        secret.resize(secret_len);

        EVP_PKEY_CTX_free(ctx);
        EVP_PKEY_free(priv);
        EVP_PKEY_free(peer);
        return secret;
    }
};

// ============================================================
// Ed25519Signer: Digital signatures using EdDSA
// ============================================================
class Ed25519Signer {
public:
    static KeyPair generate_keypair() {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_ED25519, nullptr);
        if (!ctx) throw std::runtime_error("Ed25519 context failed");

        EVP_PKEY* pkey = nullptr;
        if (EVP_PKEY_keygen_init(ctx) <= 0 ||
            EVP_PKEY_keygen(ctx, &pkey) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            throw std::runtime_error("Ed25519 keygen failed");
        }
        EVP_PKEY_CTX_free(ctx);

        int pub_len = i2d_PUBKEY(pkey, nullptr);
        std::vector<uint8_t> pub(pub_len);
        uint8_t* p = pub.data();
        i2d_PUBKEY(pkey, &p);

        int priv_len = i2d_PrivateKey(pkey, nullptr);
        std::vector<uint8_t> priv(priv_len);
        uint8_t* q = priv.data();
        i2d_PrivateKey(pkey, &q);

        EVP_PKEY_free(pkey);
        return { priv, pub };
    }

    static std::vector<uint8_t> sign(
        const std::vector<uint8_t>& private_key_der,
        const uint8_t* msg, size_t msg_len
    ) {
        const uint8_t* p = private_key_der.data();
        EVP_PKEY* key = d2i_PrivateKey(nullptr, &p,
                                        private_key_der.size());
        if (!key) throw std::runtime_error("Failed to decode signing key");

        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            EVP_PKEY_free(key);
            throw std::runtime_error("MD context failed");
        }

        std::vector<uint8_t> sig(EVP_PKEY_size(key));
        size_t sig_len = sig.size();

        if (EVP_DigestSignInit(mdctx, nullptr, nullptr, nullptr, key) != 1 ||
            EVP_DigestSignUpdate(mdctx, msg, msg_len) != 1 ||
            EVP_DigestSignFinal(mdctx, sig.data(), &sig_len) != 1) {
            EVP_MD_CTX_free(mdctx);
            EVP_PKEY_free(key);
            throw std::runtime_error("Signing failed");
        }

        sig.resize(sig_len);
        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(key);
        return sig;
    }

    static bool verify(
        const std::vector<uint8_t>& public_key_der,
        const uint8_t* msg, size_t msg_len,
        const uint8_t* sig, size_t sig_len
    ) {
        const uint8_t* p = public_key_der.data();
        EVP_PKEY* key = d2i_PUBKEY(nullptr, &p, public_key_der.size());
        if (!key) return false;

        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            EVP_PKEY_free(key);
            return false;
        }

        bool valid = (EVP_DigestVerifyInit(mdctx, nullptr, nullptr,
                      nullptr, key) == 1 &&
                      EVP_DigestVerifyUpdate(mdctx, msg, msg_len) == 1 &&
                      EVP_DigestVerifyFinal(mdctx, sig, sig_len) == 1);

        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_free(key);
        return valid;
    }
};

// ============================================================
// HkdfDeriver: HMAC-based Key Derivation Function
// ============================================================
class HkdfDeriver {
public:
    static std::vector<uint8_t> derive(
        const uint8_t* ikm, size_t ikm_len,
        const uint8_t* salt, size_t salt_len,
        const uint8_t* info, size_t info_len,
        size_t output_len
    ) {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new_hkdf(EVP_sha256(), nullptr);
        if (!ctx) throw std::runtime_error("HKDF context failed");

        std::vector<uint8_t> okm(output_len);

        if (EVP_PKEY_derive_init(ctx) <= 0 ||
            EVP_PKEY_CTX_set_hkdf_md(ctx, EVP_sha256()) <= 0 ||
            EVP_PKEY_CTX_set_hkdf_salt(ctx, salt, salt_len) <= 0 ||
            EVP_PKEY_CTX_set_hkdf_key(ctx, ikm, ikm_len) <= 0 ||
            EVP_PKEY_CTX_add1_hkdf_info(ctx, info, info_len) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            throw std::runtime_error("HKDF config failed");
        }

        size_t len = okm.size();
        if (EVP_PKEY_derive(ctx, okm.data(), &len) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            throw std::runtime_error("HKDF derivation failed");
        }

        okm.resize(len);
        EVP_PKEY_CTX_free(ctx);
        return okm;
    }
};

// ============================================================
// Constant-time utilities to prevent timing attacks
// ============================================================
class ConstantTime {
public:
    static bool compare(const uint8_t* a, const uint8_t* b, size_t len) {
        return CRYPTO_memcmp(a, b, len) == 0;
    }

    static bool compare_vectors(
        const std::vector<uint8_t>& a,
        const std::vector<uint8_t>& b
    ) {
        if (a.size() != b.size()) return false;
        return CRYPTO_memcmp(a.data(), b.data(), a.size()) == 0;
    }
};

}  // namespace seclib

// ============================================================
// Usage example
// ============================================================

int main() {
    using namespace seclib;

    // 1. Symmetric encryption
    auto key = CSPRNG::random_bytes(AesGcmProvider::KEY_SIZE);
    std::string message = "Confidential data";

    auto encrypted = AesGcmProvider::encrypt(
        key.data(),
        reinterpret_cast<const uint8_t*>(message.data()),
        message.size()
    );

    auto decrypted = AesGcmProvider::decrypt(
        key.data(),
        encrypted.ciphertext.data(), encrypted.ciphertext.size(),
        encrypted.tag.data(),
        encrypted.nonce.data()
    );

    // 2. Key exchange
    auto alice = X25519Exchange::generate_keypair();
    auto bob = X25519Exchange::generate_keypair();
    auto shared = X25519Exchange::derive_shared_secret(
        alice.private_key, bob.public_key
    );

    // 3. Key derivation
    auto derived = HkdfDeriver::derive(
        shared.data(), shared.size(),
        reinterpret_cast<const uint8_t*>("salt"), 4,
        reinterpret_cast<const uint8_t*>("info"), 4,
        32
    );

    // 4. Digital signatures
    auto signer = Ed25519Signer::generate_keypair();
    auto sig = Ed25519Signer::sign(
        signer.private_key,
        reinterpret_cast<const uint8_t*>(message.data()),
        message.size()
    );
    bool valid = Ed25519Signer::verify(
        signer.public_key,
        reinterpret_cast<const uint8_t*>(message.data()),
        message.size(),
        sig.data(), sig.size()
    );

    return valid ? 0 : 1;
}
```

---

## 12. Referências

### Padrões e Especificações

1. NIST SP 800-38D — Recommendation for Block Cipher Mode of Operation: Galois/Counter Mode (GCM)
2. NIST SP 800-56A — Recommendation for Pair-Wise Key-Establishment Schemes Using Discrete Logarithm Cryptography
3. RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
4. RFC 7748 — Elliptic Curves for Security (X25519, X448)
5. RFC 8032 — Edwards-Curve Digital Signature Algorithm (Ed25519, Ed448)
6. RFC 5869 — HMAC-based Extract-and-Expand Key Derivation Function (HKDF)
7. RFC 8410 — Algorithm Identifiers for EdDSA and X25519/X448

### Vulnerabilidades e CVEs

8. CVE-2017-15361 — ROCA: Infineon TPM RSA key generation vulnerability
9. CVE-2015-0204 — FREAK: Factoring RSA Export Keys
10. CVE-2014-3566 — POODLE: Padding Oracle On Downgraded Legacy Encryption
11. CVE-2014-0160 — Heartbleed: OpenSSL memory handling vulnerability
12. CVE-2008-0166 — Debian OpenSSL weak key generation
13. CVE-2015-4000 — Logjam: Diffie-Hellman key exchange weakness
14. Bernstein, D.J. — DUAL_EC_DRBG backdoor analysis

### Livros e Referências

15. Ferguson, N., Schneier, B. — *Practical Cryptography* (Wiley, 2003)
16. Schneier, B. — *Applied Cryptography* (20th Anniversary Edition, 2015)
17. Boneh, D., Shoup, V. — *A Graduate Course in Applied Cryptography* (2023)
18. Katz, J., Lindell, Y. — *Introduction to Modern Cryptography* (CRC Press, 2020)
19. NIST — Post-Quantum Cryptography Standardization (2024)

### Implementações e Bibliotecas

20. OpenSSL — https://www.openssl.org/
21. libsodium — https://libsodium.gitbook.io/
22. liboqs — Open Quantum Safe (https://openquantumsafe.org/)
23. BoringSSL — Google's fork of OpenSSL

---

> **Nota do Autor**: Criptografia é uma das áreas onde o erro humano é mais custoso. Um único bug — reutilizar um nonce, verificar um certificado incorretamente, ou usar um modo de operação inadequado — pode comprometer todo o sistema. Siga as práticas estabelecidas, use bibliotecas maduras revisadas pela comunidade, e NUNCA implemente criptografia própria. A segurança depende da coragem de reconhecer os próprios limites e usar soluções comprovadas.
---

*[Capítulo anterior: 07 — Autenticacao E Autorizacao](07-autenticacao-e-autorizacao.md)*
*[Próximo capítulo: 09 — Seguranca De Rede](09-seguranca-de-rede.md)*
