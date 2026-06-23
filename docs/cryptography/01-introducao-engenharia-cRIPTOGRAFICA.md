# Capitulo 01 -- Introducao a Engenharia Criptografica

> **Livro 5: Engenharia Criptografica em C++**
> **Projeto: DevSecurity**

---

## Sumario

1. Objetivos de Aprendizado
2. O que e Engenharia Criptografica
3. Modelo de Ameaca para Sistemas Criptograficos
4. Primitivas Criptograficas: Confidencialidade, Integridade, Autenticidade
5. Algoritmos Simetricos: AES, ChaCha20, Modos de Operacao
6. Algoritmos Assimetricos: RSA, ECDSA, Ed25519, X25519
7. Funcoes Hash: SHA-256, SHA-3, BLAKE2, BLAKE3
8. KDF e HKDF: Derivacao de Chaves
9. Authenticated Encryption: AES-GCM vs ChaCha20-Poly1305
10. Geradores de Numeros Aleatorios
11. CVE-2014-0160: Heartbleed -- Deep Dive
12. CVE-2008-0166: Debian OpenSSL -- O Bug que Destruiu Milhoes de Chaves
13. Android PRNG Vulnerability: Entropy Depletion apos Fork
14. Selecionando Bibliotecas Criptograficas
15. Tabela Comparativa de Bibliotecas
16. Exercicios
17. Referencias e Leituras Adicionais

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce ser capaz de:

1. **Distinguir** engenharia criptografica de criptografia teorica, compreendendo por que a implementacao correta de primitivas criptograficas e tao critica quanto a escolha do algoritmo certo.

2. **Classificar** primitivas criptograficas por propriedade de seguranca (confidencialidade, integridade, autenticidade) e selecionar o algoritmo apropriado para cada caso de uso em sistemas C++ modernos.

3. **Analisar** falhas historicas reais -- CVE-2014-0160 (Heartbleed), CVE-2008-0166 (Debian OpenSSL), e a vulnerabilidade PRNG do Android -- identificando raiz causal, impacto e contramedidas.

4. **Implementar** operacoes criptograficas basicas em C++17 utilizando pelo menos duas bibliotecas diferentes (OpenSSL e libsodium), incluindo cifragem simetrica, assinatura digital e derivacao de chaves.

5. **Avaliar** bibliotecas criptograficas por criterios de seguranca, performance, API design e manutencao, aplicando frameworks de decisao para escolhas tecnologicas fundamentadas.

---

## 2. O que e Engenharia Criptografica

### 2.1 Distincao Fundamental

Existe uma distincao critica que muitos desenvolvedores negligenciam: **criptografia teorica** e **engenharia criptografica** sao disciplinas distintas com requisitos, habilidades e modos de falha completamente diferentes.

A **criptografia teorica** e uma disciplina matematica que estuda propriedades abstratas de algoritmos: seguranca semantica, resistencia a chosen-plaintext attacks, reducoes entre problemas computacionais. Os pesquisadores nesta area demonstram que um esquema e seguro *assumindo* que algum problema matematico e dificil.

A **engenharia criptografica** e a disciplina de construir sistemas que usam primitivas criptograficas de forma correta. Um engenheiro criptografico deve resolver problemas como:

- Como gerar numeros aleatorios verdadeiramente aleatorios em uma maquina virtual?
- Como armazenar chaves em memoria sem que sejam despejadas em core dumps?
- Como transmitir uma chave entre processos sem expoe-la em `/proc`?
- O que acontece com o estado do gerador de numeros aleatorios apos um `fork()`?
- Como implementar a derivacao de chaves de forma que um ataque em uma chave derivada nao comprometa a chave mestra?

A historia esta repleta de sistemas que usaram algoritmos criptograficamente seguros de forma catastroficamente incorreta. O SSL/TLS, por exemplo, usou RSA e AES durante decadas -- algoritmos robustos -- mas foi constantemente derrotado por implementacoes defeituosas.

### 2.2 O Gap entre Teoria e Pratica

Considere o seguinte cenario. Um sistema precisa autenticar mensagens. O engenheiro pesquisa e escolhe HMAC-SHA256, um esquema teoricamente seguro. Mas a implementacao tem uma falha:

```cpp
// CODIGO VULNERAVEL -- NUNCA FACO ISSO
class MessageAuthenticator {
private:
    std::vector<uint8_t> key_;

public:
    // Erro 1: Chave herdada de configuracao, nao derivada
    explicit MessageAuthenticator(const std::string& static_key)
        : key_(static_key.begin(), static_key.end()) {}

    // Erro 2: Comparacao de MAC com operador == (timing side-channel)
    bool verify(const std::vector<uint8_t>& message,
                const std::vector<uint8_t>& received_mac) {
        auto computed_mac = compute_hmac(message);
        return computed_mac == received_mac;  // VULNERAVEL: timing attack
    }

    // Erro 3: Mensagem e MAC sao copiados por valor (persistem em memoria)
    std::vector<uint8_t> process(const std::vector<uint8_t>& message) {
        auto mac = compute_hmac(message);
        std::vector<uint8_t> result(message);
        result.insert(result.end(), mac.begin(), mac.end());
        return result;  // Cadeia completa fica na heap
    }
};
```

Este codigo usa um algoritmo correto (HMAC-SHA256) mas e fundamentalmente inseguro por tres razoes:

1. **Chave estatica** derivada diretamente de uma string de configuracao, sem KDF
2. **Comparacao timing-aware ausente**: o operador `==` retorna falso no primeiro byte divergente, mas leva um tempo proporcional a posicao do primeiro byte diferente -- um atacante pode medir tempo e inferir a chave byte a byte
3. **Residuo em memoria**: o vetor result persiste na heap apos o return, podendo ser lido por outro processo com acesso ao espaco de endereco do processo

A solucao correta utiliza constant-time comparison, derivação de chaves via KDF, e limpeza segura de memoria:

```cpp
#include <sodium.h>
#include <sodium/crypto_kdf.h>
#include <vector>
#include <array>

class SecureMessageAuthenticator {
private:
    static constexpr size_t KEY_SIZE = 32;
    static constexpr size_t MAC_SIZE = 32;
    std::array<uint8_t, KEY_SIZE> key_;

public:
    explicit SecureMessageAuthenticator(
        const std::array<uint8_t, KEY_SIZE>& master_key,
        uint64_t context
    ) {
        // Deriva subchave usando HKDF-like construto do libsodium
        crypto_kdf_keygen(key_.data());
        static const char subkey_id[] = "MsgAuth";
        crypto_kdf_derive_from_key(
            key_.data(), KEY_SIZE,
            0, reinterpret_cast<const uint8_t*>(subkey_id),
            master_key.data()
        );
    }

    ~SecureMessageAuthenticator() {
        // Limpeza segura: sobrescreve memoria antes de liberar
        sodium_memzero(key_.data(), KEY_SIZE);
    }

    std::vector<uint8_t> compute_mac(
        const uint8_t* data, size_t data_len
    ) const {
        std::vector<uint8_t> mac(MAC_SIZE);
        crypto_generichash(
            mac.data(), MAC_SIZE,
            data, data_len,
            key_.data(), KEY_SIZE
        );
        return mac;
    }

    bool verify(
        const uint8_t* data, size_t data_len,
        const uint8_t* received_mac, size_t mac_len
    ) const {
        if (mac_len != MAC_SIZE) return false;
        auto computed = compute_mac(data, data_len);
        // Constant-time comparison via libsodium
        return sodium_memcmp(computed.data(), received_mac, MAC_SIZE) == 0;
    }
};
```

### 2.3 Principios da Engenharia Criptografica

Os principios fundamentais que orientam a engenharia criptografica sao:

**Nao reinvente a roda criptografica.** Nunca implemente algoritmos criptograficos do zero. Use bibliotecas auditadas e amplamente testadas. Mesmo implementacoes de AES aparentemente simples podem conter vulnerabilidades de timing side-channel.

**Chaves nunca em texto claro.** Chaves devem ser armazenadas em memoria protegida, derivadas de KDFs, e limpas imediatamente apos uso. Em sistemas operacionais modernos, use `mlock()` para evitar swapping e `sodium_memzero()` para limpeza segura.

**Gere aleatoriedade de verdade.** Use `/dev/urandom`, `getrandom()`, ou `BCryptGenRandom()` -- nunca `rand()`, `std::mt19937`, ou outros PRNGs nao criptograficos.

**Autenticacao antes de confidencialidade.** Sempre autentique mensagens antes de decifra-las. O padrao moderno e authenticated encryption (AEAD) que combina cifragem e autenticacao em uma unica primitiva.

**Defina o que esta fora do escopo.** Criptografia protege dados contra atacantes com recursos limitados. Nenhum esquema criptografico protege contra quem ja tem acesso fisico ao dispositivo, ou contra um atacante com poder computacional ilimitado.

---

## 3. Modelo de Ameaca para Sistemas Criptograficos

### 3.1 O que e um Modelo de Ameaca

Um modelo de ameaca e uma descricao estruturada de quem pode atacar o sistema, quais assets eles podem querer comprometer, e quais vetores de ataque estao disponiveis. Sem um modelo de ameaca, voce esta apenas adivinhando quais controles de seguranca implementar.

### 3.2 Componentes do Modelo

```
+-----------------------------------------------+
|              MODELO DE AMEACA                 |
+-----------------------------------------------+
|  1. ATOR DE AMEACA                            |
|     - Interno vs Externo                      |
|     - Motivacao (financeira, espionagem)      |
|     - Recursos (script kiddie vs APT)         |
+-----------------------------------------------+
|  2. ASSETS                                    |
|     - Dados em repouso                        |
|     - Dados em transito                       |
|     - Metadados                               |
|     - Disponibilidade do sistema              |
+-----------------------------------------------+
|  3. VETORES DE ATAQUE                         |
|     - Interceptacao de rede                   |
|     - Acesso a disco fisico                   |
|     - Engenharia social                       |
|     - Vulnerabilidades de implementacao       |
+-----------------------------------------------+
|  4. CONTROLES                                 |
|     - Cifragem em transito (TLS 1.3)         |
|     - Cifragem em repouso (AES-256-GCM)      |
|     - Gerenciamento de chaves                 |
|     - Autenticacao multifator                 |
+-----------------------------------------------+
```

### 3.3 Niveis de Atacante

A biblioteca de seguranca define niveis de atacante que influenciam diretamente as decisoes criptograficas:

| Nivel | Descricao | Exemplo | Impacto na Criptografia |
|-------|-----------|---------|------------------------|
| L1 | Atacante casual | Explorador de portas | Senhas fortes, HTTPS basico |
| L2 | Atacante motivado | Criminal organizado | AEAD, gerenciamento de chaves |
| L3 | Atacante com recursos | Empresa concorrente | HSMs, perfeita forward secrecy |
| L4 | Atacante estatal | Agencia de inteligencia | Pos-quantum, air gaps |

### 3.4 Propriedades de Seguranca

As propriedades que um sistema criptografico deve garantir:

**Confidencialidade**: Apenas as partes autorizadas podem ler os dados. Implementada via cifragem simetrica (AES, ChaCha20) ou assimetrica (RSA, ECDH).

**Integridade**: Os dados nao foram modificados entre remetente e receptor. Implementada via HMAC, MACs, ou assinaturas digitais.

**Autenticidade**: As partes podem verificar a identidade uma da outra. Implementada via certificados, chaves publicas pre-compartilhadas, ou autenticacao por senha.

**Nao-repudio**: O remetente nao pode negar ter enviado a mensagem. Implementada via assinaturas digitais com certificados PKI.

**Forward Secrecy**: Comprometimento de uma chave passada nao revela comunicacoes passadas. Implementada via Diffie-Hellman efemero (DHE ou ECDHE).

---

## 4. Primitivas Criptograficas: Confidencialidade, Integridade, Autenticidade

### 4.1 Confidencialidade -- Cifragem Simetrica

A cifragem simetrica usa a mesma chave para cifrar e decifrar. E rapida e eficiente para grandes volumes de dados.

**Caracteristicas fundamentais:**

- Chave secreta compartilhada entre remetente e receptor
- Algoritmos: AES-128/256, ChaCha20, XChaCha20
- Modos de operacao: GCM, CTR, CBC (descontinuado), Poly1305
- Tamanho de bloco: 128 bits (AES), stream cipher (ChaCha20)

**Por que CBC e descontinuado:**

O modo CBC e vulneravel a padding oracle attacks. Em 2011, o ataque BEAST (Browser Exploit Against SSL/TLS) demonstrou que o CBC no TLS 1.0 permitia deciframento seletivo. Apesar de mitigacoes (1/n-1 record splitting), o padrao moderno prefere AEAD.

### 4.2 Integridade -- MACs e HMAC

**HMAC (Hash-based Message Authentication Code):**

HMAC usa uma funcao hash criptografica combinada com uma chave secreta para gerar um tag de autenticidade. A seguranca do HMAC depende tanto da resistencia a colisoes da hash quanto da preservacao da chave.

```
HMAC(K, m) = H((K' XOR opad) || H((K' XOR ipad) || m))
```

Onde:
- K' e a chave ajustada ao tamanho do bloco da hash
- opad = 0x5c repetido
- ipad = 0x36 repetido

**Poly1305:**

Poly1305 e um authenticador de uso unico baseado em aritmetica modular. Usado com ChaCha20, forma o construto ChaCha20-Poly1305 que e o padrao IETF para authenticated encryption.

### 4.3 Autenticidade -- Assinaturas Digitais

Assinaturas digitais ligam uma identidade (chave publica) a uma mensagem, garantindo autenticidade e nao-repudio.

**Propriedades:**
- So quem tem a chave privada pode gerar a assinatura
- Qualquer um com a chave publica pode verificar
- A assinatura e especifica para aquela mensagem
- Nao-repudio: o assinante nao pode negar ter assinado

---

## 5. Algoritmos Simetricos: AES, ChaCha20, Modos de Operacao

### 5.1 AES (Advanced Encryption Standard)

AES e o algoritmo de cifragem simetrica mais utilizado no mundo. Foi selecionado pelo NIST em 2001 apos um processo de competicao publica.

**Caracteristicas do AES:**

| Propriedade | Valor |
|-------------|-------|
| Bloco | 128 bits |
| Chaves | 128, 192 ou 256 bits |
| Rounds | 10, 12 ou 14 respectivamente |
| Estrutura | Substitution-Permutation Network |
| Seguranca | Resistente a ataques conhecidos (linear, diferencial) |

**Implementacao AES-GCM em C++ com OpenSSL:**

```cpp
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <vector>
#include <array>
#include <stdexcept>
#include <cstring>

struct AesGcmResult {
    std::vector<uint8_t> ciphertext;
    std::array<uint8_t, 16> tag;
    std::array<uint8_t, 12> iv;
};

class AesGcmCipher {
private:
    std::array<uint8_t, 32> key_;

public:
    AesGcmCipher() {
        if (RAND_bytes(key_.data(), key_.size()) != 1) {
            throw std::runtime_error("Failed to generate random key");
        }
    }

    explicit AesGcmCipher(const std::array<uint8_t, 32>& key)
        : key_(key) {}

    AesGcmResult encrypt(
        const uint8_t* plaintext, size_t plaintext_len,
        const uint8_t* aad, size_t aad_len
    ) {
        AesGcmResult result;

        // Gera IV aleatorio de 96 bits (recomendado para GCM)
        if (RAND_bytes(result.iv.data(), result.iv.size()) != 1) {
            throw std::runtime_error("Failed to generate IV");
        }

        result.ciphertext.resize(plaintext_len);

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("Failed to create cipher context");

        // Configura AES-256-GCM
        if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                nullptr, nullptr) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to init cipher");
        }

        // Define tamanho da chave
        if (EVP_CIPHER_CTX_set_key_length(ctx, key_.size()) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to set key length");
        }

        // Inicializa com chave e IV
        if (EVP_EncryptInit_ex(ctx, nullptr, nullptr,
                                key_.data(), result.iv.data()) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to set key and IV");
        }

        // Processa AAD (Additional Authenticated Data)
        int outlen;
        if (aad && aad_len > 0) {
            if (EVP_EncryptUpdate(ctx, nullptr, &outlen, aad, aad_len) != 1) {
                EVP_CIPHER_CTX_free(ctx);
                throw std::runtime_error("Failed to process AAD");
            }
        }

        // Cifra o plaintext
        if (EVP_EncryptUpdate(ctx, result.ciphertext.data(), &outlen,
                              plaintext, plaintext_len) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to encrypt");
        }

        // Finaliza a cifragem
        if (EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + outlen,
                                &outlen) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to finalize encryption");
        }

        // Obtem o tag de autenticacao
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16,
                                result.tag.data()) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to get tag");
        }

        EVP_CIPHER_CTX_free(ctx);
        return result;
    }

    std::vector<uint8_t> decrypt(
        const uint8_t* ciphertext, size_t ciphertext_len,
        const uint8_t* aad, size_t aad_len,
        const std::array<uint8_t, 16>& tag,
        const std::array<uint8_t, 12>& iv
    ) {
        std::vector<uint8_t> plaintext(ciphertext_len);
        int outlen;

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("Failed to create cipher context");

        if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                                nullptr, nullptr) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to init cipher");
        }

        if (EVP_CIPHER_CTX_set_key_length(ctx, key_.size()) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to set key length");
        }

        if (EVP_DecryptInit_ex(ctx, nullptr, nullptr,
                                key_.data(), iv.data()) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to set key and IV");
        }

        // Processa AAD
        if (aad && aad_len > 0) {
            if (EVP_DecryptUpdate(ctx, nullptr, &outlen, aad, aad_len) != 1) {
                EVP_CIPHER_CTX_free(ctx);
                throw std::runtime_error("Failed to process AAD");
            }
        }

        // Decifra
        if (EVP_DecryptUpdate(ctx, plaintext.data(), &outlen,
                              ciphertext, ciphertext_len) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to decrypt");
        }

        // Define o tag esperado
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16,
                                const_cast<uint8_t*>(tag.data())) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Failed to set tag");
        }

        // Verifica autenticacao (deve ser chamado DEPOIS de definir o tag)
        if (EVP_DecryptFinal_ex(ctx, plaintext.data() + outlen,
                                &outlen) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            throw std::runtime_error("Authentication failed");
        }

        EVP_CIPHER_CTX_free(ctx);
        return plaintext;
    }
};
```

### 5.2 ChaCha20

ChaCha20 e um stream cipher projetado por Daniel J. Bernstein como uma melhoria do Salsa20. Usa operacoes de 32 bits (add, rotate, XOR) que sao nativas em processadores modernos, oferecendo performance excellent mesmo sem AES-NI.

**Vantagens do ChaCha20 sobre AES:**

| Aspecto | AES | ChaCha20 |
|---------|-----|----------|
| Hardware acceleration | AES-NI (x86) | Nao requer |
| Side-channels | T-tables vulneraveis | Resistente por design |
| Tamanho de chave | 128/192/256 bits | 256 bits |
| Nonce | 96 bits (GCM) | 96 bits |
| Performance (sem HW) | Lento | Rapido |
| Performance (com HW) | Muito rapido | Rapido |

**Implementacao ChaCha20-Poly1305 em C++ com libsodium:**

```cpp
#include <sodium.h>
#include <vector>
#include <array>
#include <stdexcept>
#include <cstring>

struct ChaCha20Poly1305Result {
    std::vector<uint8_t> ciphertext;
    std::array<uint8_t, 24> nonce;
};

class ChaCha20Poly1305Cipher {
private:
    std::array<uint8_t, 32> key_;

public:
    ChaCha20Poly1305Cipher() {
        crypto_aead_xchacha20poly1305_ietf_keygen(key_.data());
    }

    explicit ChaCha20Poly1305Cipher(const std::array<uint8_t, 32>& key)
        : key_(key) {}

    ~ChaCha20Poly1305Cipher() {
        sodium_memzero(key_.data(), key_.size());
    }

    ChaCha20Poly1305Result encrypt(
        const uint8_t* plaintext, size_t plaintext_len,
        const uint8_t* aad, size_t aad_len
    ) {
        ChaCha20Poly1305Result result;

        // Gera nonce aleatorio (XChaCha20 usa 24 bytes)
        randombytes_buf(result.nonce.data(), result.nonce.size());

        result.ciphertext.resize(plaintext_len);
        unsigned long long actual_len;

        if (crypto_aead_xchacha20poly1305_ietf_encrypt(
                result.ciphertext.data(), &actual_len,
                plaintext, plaintext_len,
                aad, aad_len,
                nullptr,  // nsec (nao usado)
                result.nonce.data(),
                key_.data()) != 0) {
            throw std::runtime_error("Encryption failed");
        }

        result.ciphertext.resize(actual_len);
        return result;
    }

    std::vector<uint8_t> decrypt(
        const uint8_t* ciphertext, size_t ciphertext_len,
        const uint8_t* aad, size_t aad_len,
        const std::array<uint8_t, 24>& nonce
    ) {
        std::vector<uint8_t> plaintext(ciphertext_len);
        unsigned long long actual_len;

        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), &actual_len,
                nullptr,  // nsec (nao usado)
                ciphertext, ciphertext_len,
                aad, aad_len,
                nonce.data(),
                key_.data()) != 0) {
            throw std::runtime_error("Decryption or authentication failed");
        }

        plaintext.resize(actual_len);
        return plaintext;
    }
};
```

### 5.3 Modos de Operacao

**GCM (Galois/Counter Mode):**

GCM e o modo AEAD mais utilizado, combinando CTR mode para confidencialidade com GHASH para autenticacao.

```
Ciphertext = AES-CTR(K, IV, Plaintext)
Tag = GHASH(K, AAD, Ciphertext) XOR AES-CTR(K, IV, 0^128)
```

**Regras criticas para GCM:**
- NUNCA reutilize um par (key, nonce) -- isto destruiu a seguranca completamente
- Nonce deve ser de 96 bits para GCM
- Tag deve ser de 128 bits para seguranca completa
- Para nonces maiores que 96 bits, GHASH e usado como hash para gerar nonce efetivo

**Poly1305:**

Poly1305 e um authenticador de uso unico baseado em aritmetica modular modulo p = 2^130 - 5. O nonce e usado apenas uma vez, e a chave Poly1305 e derivada do nonce e da chave ChaCha20.

```
r = CHACHA20(K, nonce, 0)[0..31] mod p
s = CHACHA20(K, nonce, 1)[0..31]
tag = ((m1*r^n + m2*r^(n-1) + ... + mn*r^1) mod p) + s
```

**Comparacao GCM vs Poly1305:**

| Aspecto | AES-GCM | ChaCha20-Poly1305 |
|---------|---------|-------------------|
| Base de seguranca | AES (blocos) | ChaCha20 (stream) |
| Autenticacao | GHASH (GF(2^128)) | Poly1305 (GF(2^130-5)) |
| Nonce length | 96 bits | 96/192 bits (IETF/XChaCha20) |
| Performance com AES-NI | Muito alta | Alta |
| Performance sem AES-NI | Media | Muito alta |
| Uso recomendado | Servidores com AES-NI | Mobile, IoT, dispositivos sem AES-NI |

---

## 6. Algoritmos Assimetricos: RSA, ECDSA, Ed25519, X25519

### 6.1 RSA (Rivest-Shamir-Adleman)

RSA e baseado na dificuldade de fatorar produtos de dois numeros primos grandes. Foi inventado em 1977 e ainda e amplamente utilizado para troca de chaves e assinaturas.

**Parametros recomendados:**

| Tamanho de chave | Seguranca equivalente | Uso |
|-----------------|----------------------|-----|
| 2048 bits | ~112 bits | Minimo aceitavel |
| 3072 bits | ~128 bits | Recomendado |
| 4096 bits | ~140 bits | Para dados de longo prazo |

**Limitacoes do RSA:**
- Chaves grandes (3072+ bits) sao lentas para gerar
- Assinaturas sao lentas comparadas com ECDSA/Ed25519
- Nao suporta forward secrecy nativo
- Vulneravel a ataques de quantum computing (fatoracao)

### 6.2 ECDSA (Elliptic Curve Digital Signature Algorithm)

ECDSA usa curvas elipticas sobre corpos finitos para gerar assinaturas compactas e rapidas.

**Curvas recomendadas:**

| Curva | Tamanho | Seguranca | Observacoes |
|-------|---------|-----------|-------------|
| P-256 (secp256r1) | 32 bytes | 128 bits | Padrao NIST, amplamente suportado |
| P-384 (secp384r1) | 48 bytes | 192 bits | Para dados de longo prazo |
| secp256k1 | 32 bytes | 128 bits | Usado no Bitcoin |

**Implementacao ECDSA-P256 em C++ com OpenSSL:**

```cpp
#include <openssl/ec.h>
#include <openssl/ecdsa.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/pem.h>
#include <vector>
#include <stdexcept>

class EcdsaP256Signer {
private:
    EVP_PKEY* key_;

public:
    EcdsaP256Signer() {
        EC_KEY* ec_key = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
        if (!ec_key) throw std::runtime_error("Failed to create EC key");

        if (EC_KEY_generate_key(ec_key) != 1) {
            EC_KEY_free(ec_key);
            throw std::runtime_error("Failed to generate EC key");
        }

        key_ = EVP_PKEY_new();
        if (!key_ || EVP_PKEY_assign_EC_KEY(key_, ec_key) != 1) {
            EC_KEY_free(ec_key);
            EVP_PKEY_free(key_);
            throw std::runtime_error("Failed to assign EC key");
        }
    }

    ~EcdsaP256Signer() {
        if (key_) EVP_PKEY_free(key_);
    }

    std::vector<uint8_t> sign(
        const uint8_t* data, size_t data_len
    ) {
        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) throw std::runtime_error("Failed to create digest context");

        size_t sig_len = 0;

        if (EVP_DigestSignInit(mdctx, nullptr, EVP_sha256(), nullptr, key_) != 1) {
            EVP_MD_CTX_free(mdctx);
            throw std::runtime_error("Failed to init signing");
        }

        // Obtem tamanho necessario para a assinatura
        if (EVP_DigestSignUpdate(mdctx, data, data_len) != 1) {
            EVP_MD_CTX_free(mdctx);
            throw std::runtime_error("Failed to update digest");
        }

        if (EVP_DigestSignFinal(mdctx, nullptr, &sig_len) != 1) {
            EVP_MD_CTX_free(mdctx);
            throw std::runtime_error("Failed to get signature size");
        }

        std::vector<uint8_t> signature(sig_len);

        if (EVP_DigestSignFinal(mdctx, signature.data(), &sig_len) != 1) {
            EVP_MD_CTX_free(mdctx);
            throw std::runtime_error("Failed to sign");
        }

        signature.resize(sig_len);
        EVP_MD_CTX_free(mdctx);
        return signature;
    }

    bool verify(
        const uint8_t* data, size_t data_len,
        const uint8_t* signature, size_t sig_len
    ) {
        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) throw std::runtime_error("Failed to create digest context");

        int result = 0;

        if (EVP_DigestVerifyInit(mdctx, nullptr, EVP_sha256(),
                                 nullptr, key_) != 1) {
            EVP_MD_CTX_free(mdctx);
            return false;
        }

        if (EVP_DigestVerifyUpdate(mdctx, data, data_len) != 1) {
            EVP_MD_CTX_free(mdctx);
            return false;
        }

        result = EVP_DigestVerifyFinal(mdctx, signature, sig_len);

        EVP_MD_CTX_free(mdctx);
        return result == 1;
    }
};
```

### 6.3 Ed25519

Ed25519 e uma schema de assinatura baseada em curvas elipticas projetada por Daniel J. Bernstein e colaboradores. Usa a curva Ed25519 (Curve25519 no grupo aditivo de Edwards).

**Vantagens do Ed25519:**

| Aspecto | ECDSA-P256 | Ed25519 |
|---------|-----------|---------|
| Tamanho da chave publica | 64 bytes | 32 bytes |
| Tamanho da assinatura | 72 bytes | 64 bytes |
| Velocidade de assinatura | ~10K/s | ~30K/s |
| Velocidade de verificacao | ~8K/s | ~12K/s |
| Resistencia a nonce reuse | VULNERAVEL | Resistente |
| Complexidade de implementacao | Alta | Baixa |

**Por que Ed25519 e resistente a nonce reuse:**

A chave privada de Ed25519 e derivada de um hash SHA-512 do seed, e o nonce e parte da chave derivada. Portanto, assinar duas vezes com a mesma chave privada e a mesma mensagem gera o mesmo nonce, mas assinar com o mesmo seed e mensagens diferentes gera nonces diferentes -- eliminando o risco catastrofico de nonce reuse que afeta ECDSA.

### 6.4 X25519 -- Troca de Chaves Ephemeral

X25519 implementa Diffie-Hellman sobre Curve25519, fornecendo key agreement ephemeral que garante forward secrecy.

**Implementacao X25519 com libsodium:**

```cpp
#include <sodium.h>
#include <array>
#include <stdexcept>

class X25519KeyExchange {
private:
    std::array<uint8_t, 32> private_key_;
    std::array<uint8_t, 32> public_key_;

public:
    X25519KeyExchange() {
        // Gera par de chaves
        if (crypto_kx_keypair(public_key_.data(), private_key_.data()) != 0) {
            throw std::runtime_error("Failed to generate keypair");
        }
    }

    const std::array<uint8_t, 32>& public_key() const {
        return public_key_;
    }

    std::array<uint8_t, 32> compute_shared_secret(
        const std::array<uint8_t, 32>& other_public
    ) const {
        std::array<uint8_t, 32> shared_key;
        std::array<uint8_t, 32> client_pk, server_pk;

        // crypto_kx_seed_keypair para gerar chaves de sessao
        if (crypto_kx_seed_keypair(
                client_pk.data(), server_pk.data(),
                private_key_.data()) != 0) {
            throw std::runtime_error("Failed to compute shared secret");
        }

        // X25519 DH
        if (crypto_scalarmult(shared_key.data(),
                               private_key_.data(),
                               other_public.data()) != 0) {
            throw std::runtime_error("Invalid public key");
        }

        return shared_key;
    }
};
```

---

## 7. Funcoes Hash: SHA-256, SHA-3, BLAKE2, BLAKE3

### 7.1 SHA-256

SHA-256 e uma funcao hash da familia SHA-2, produzindo uma saida de 256 bits. E amplamente utilizada para assinaturas digitais, verificacao de integridade, e proof-of-work.

**Propriedades:**
- Tamanho de saida: 256 bits (32 bytes)
- Tamanho de bloco: 512 bits (64 bytes)
- Rounds: 64
- Resistencia a colisao: 2^128 (forca bruta)
- Resistencia a pre-imagem: 2^256

**Implementacao SHA-256 em C++:**

```cpp
#include <openssl/sha.h>
#include <vector>
#include <array>
#include <cstring>

class SHA256Hash {
public:
    static constexpr size_t DIGEST_SIZE = 32;

    static std::array<uint8_t, DIGEST_SIZE> hash(
        const uint8_t* data, size_t len
    ) {
        std::array<uint8_t, DIGEST_SIZE> digest;
        SHA256(data, len, digest.data());
        return digest;
    }

    static std::array<uint8_t, DIGEST_SIZE> hash(
        const std::vector<uint8_t>& data
    ) {
        return hash(data.data(), data.size());
    }

    // HMAC-SHA256
    static std::array<uint8_t, DIGEST_SIZE> hmac(
        const uint8_t* key, size_t key_len,
        const uint8_t* data, size_t data_len
    ) {
        std::array<uint8_t, DIGEST_SIZE> result;
        unsigned int result_len;
        HMAC(EVP_sha256(), key, key_len, data, data_len,
             result.data(), &result_len);
        return result;
    }
};
```

### 7.2 SHA-3 (Keccak)

SHA-3 e a familia de funcoes hash selecionada pelo NIST em 2015, baseada no construto Keccak. Apesar de SHA-2 nao ter falhas conhecidas, SHA-3 foi projetado como backup em caso de falhas futuras.

**Variantes de SHA-3:**

| Variante | Tamanho de saida | Uso recomendado |
|----------|-----------------|-----------------|
| SHA3-256 | 256 bits | Substituto direto do SHA-256 |
| SHA3-512 | 512 bits | Para dados muito longos |
| SHAKE128 | Variavel | XOF (extensible-output function) |
| SHAKE256 | Variavel | XOF para derivacao de chaves |

**Keccak sponge construction:**

```
s = f(k || p || pad)

onde:
- f e a funcao de permutacao Keccak-f[1600]
- k e o dominio de separacao (01 para SHA-3, 11 para SHAKE)
- p e o padding pad10*1
- s e o estado interno de 1600 bits
```

### 7.3 BLAKE2

BLAKE2 e uma evolucao do BLAKE (finalista do SHA-3), projetado para ser mais rapido que MD5 e SHA-1, mantendo a seguranca de SHA-3.

**Variantes:**
- **BLAKE2b**: Otimizado para 64-bit, saida ate 512 bits
- **BLAKE2s**: Otimizado para 32-bit, saida ate 256 bits
- **BLAKE2bp/BLAKE2sp**: Versiones paralelas

**Performance comparativa (hash de 1 MB):**

| Algoritmo | Throughput | |
|-----------|-----------|---|
| MD5 | ~700 MB/s | Nao seguro |
| SHA-1 | ~600 MB/s | Nao seguro |
| SHA-256 | ~300 MB/s | Seguro |
| SHA-3-256 | ~200 MB/s | Seguro |
| BLAKE2b | ~900 MB/s | Seguro |
| BLAKE3 | ~2000 MB/s | Seguro |

### 7.4 BLAKE3

BLAKE3 e a evolucao de BLAKE2, projetado para ser massivamente paralelizavel. Suporta hashing incremental, tree hashing, e XOF.

**Caracteristicas unicas:**
- **Tree hashing**: divide dados em blocos e hash paralelmente
- **Infinite output**: pode gerar quantos bytes precisar (XOF)
- **Keyed hashing**: suporta MAC via chave
- **Key derivation**: suporta KDF via contexto

```cpp
#include <blake3.h>
#include <vector>
#include <string>

class BLAKE3Hasher {
private:
    blake3_hasher hasher_;

public:
    BLAKE3Hasher() {
        blake3_hasher_init(&hasher_);
    }

    explicit BLAKE3Hasher(const uint8_t* key, size_t key_len) {
        blake3_hasher_init_keyed(&hasher_, key);
    }

    void update(const uint8_t* data, size_t len) {
        blake3_hasher_update(&hasher_, data, len);
    }

    void finalize(uint8_t* out, size_t out_len) {
        blake3_hasher_finalize(&hasher_, out, out_len);
    }

    // Hash conveniencia
    static std::vector<uint8_t> hash(
        const uint8_t* data, size_t data_len, size_t out_len
    ) {
        std::vector<uint8_t> out(out_len);
        blake3_hasher hasher;
        blake3_hasher_init(&hasher);
        blake3_hasher_update(&hasher, data, data_len);
        blake3_hasher_finalize(&hasher, out.data(), out_len);
        return out;
    }
};
```

---

## 8. KDF e HKDF: Derivacao de Chaves

### 8.1 Por que Derivar Chaves

A derivacao de chaves (KDF) resolve um problema fundamental: como obter multipas chaves seguras a partir de uma unica chave mestra ou segredo compartilhado.

**Motivacoes:**
- Uma chave mestra nao deve ser usada diretamente para multipas operacoes
- Cada operacao deve usar uma chave unica (principio de least privilege)
- Chaves devem ter formato e tamanho adequados ao algoritmo destino
- Previne cross-protocol attacks (a mesma chave usada em protocolos diferentes)

### 8.2 HKDF (HMAC-based Key Derivation Function)

HKDF e definido no RFC 5869 e e o padrao moderno para derivacao de chaves. Composto por duas etapas:

**Extracao:**
```
PRK = HMAC-Hash(salt, IKM)
```
Onde:
- PRK = Pseudo-Random Key (tamanho do bloco da hash)
- salt = valor aleatorio (se nao disponivel, usa zeros)
- IKM = Input Keying Material (segredo compartilhado)

**Expansao:**
```
T(0) = ""
T(i) = HMAC-Hash(PRK, T(i-1) || info || i)
OKM = T(1) || T(2) || ... || T(n)
```
Onde:
- info = contexto da aplicacao
- n = ceil(L / HashLen), onde L e o comprimento desejado

**Implementacao HKDF em C++:**

```cpp
#include <openssl/hmac.h>
#include <openssl/evp.h>
#include <vector>
#include <stdexcept>
#include <cstring>

class HKDF {
public:
    // Extracao
    static std::vector<uint8_t> extract(
        const uint8_t* salt, size_t salt_len,
        const uint8_t* ikm, size_t ikm_len,
        size_t hash_len = 32
    ) {
        std::vector<uint8_t> prk(hash_len);
        unsigned int prk_len;

        // Se salt for nulo, usa zeros do tamanho do bloco da hash
        uint8_t default_salt[32] = {0};
        const uint8_t* effective_salt = salt ? salt : default_salt;
        size_t effective_salt_len = salt ? salt_len : hash_len;

        HMAC(EVP_sha256(), effective_salt, effective_salt_len,
             ikm, ikm_len, prk.data(), &prk_len);

        prk.resize(prk_len);
        return prk;
    }

    // Expansao
    static std::vector<uint8_t> expand(
        const uint8_t* prk, size_t prk_len,
        const uint8_t* info, size_t info_len,
        size_t okm_len,
        size_t hash_len = 32
    ) {
        size_t n = (okm_len + hash_len - 1) / hash_len;
        std::vector<uint8_t> okm;
        okm.reserve(okm_len);

        std::vector<uint8_t> t(hash_len);
        unsigned int t_len;

        for (size_t i = 1; i <= n; i++) {
            // Concatena T(i-1) || info || i
            std::vector<uint8_t> hmac_input;
            hmac_input.reserve(t.size() + info_len + 1);

            if (i > 1) {
                hmac_input.insert(hmac_input.end(), t.begin(), t.end());
            }
            hmac_input.insert(hmac_input.end(), info, info + info_len);
            hmac_input.push_back(static_cast<uint8_t>(i));

            HMAC(EVP_sha256(), prk, prk_len,
                 hmac_input.data(), hmac_input.size(),
                 t.data(), &t_len);

            size_t to_copy = std::min(hash_len, okm_len - okm.size());
            okm.insert(okm.end(), t.begin(), t.begin() + to_copy);
        }

        return okm;
    }

    // Derivacao conveniencia
    static std::vector<uint8_t> derive(
        const uint8_t* ikm, size_t ikm_len,
        size_t okm_len,
        const uint8_t* salt = nullptr, size_t salt_len = 0,
        const uint8_t* info = nullptr, size_t info_len = 0
    ) {
        auto prk = extract(salt, salt_len, ikm, ikm_len);
        return expand(prk.data(), prk.size(),
                      info, info_len, okm_len);
    }
};
```

---

## 9. Authenticated Encryption: AES-GCM vs ChaCha20-Poly1305

### 9.1 Por que Authenticated Encryption

O authenticated encryption (AEAD) combina confidencialidade (cifragem) e integridade (autenticacao) em uma unica primitiva. A alternativa -- construir "encrypt-then-MAC" manualmente -- e propensa a erros:

**Erros comuns em encrypt-then-MAC manual:**
- MAC aplicado antes da cifragem (MAC-then-encrypt) -- vulneravel
- MAC aplicado a dados incompletos
- Verificacao do MAC com timing comparison
- Reuso de nonce com MAC diferente

AEAD elimina estas armadilhas fornecendo uma interface unica onde o nonce, chave, e dados sao processados atomicamente.

### 9.2 AES-GCM -- Profundidade

**Estrutura interna:**

```
Ciphertext = AES-CTR(K, IV || counter, Plaintext)
GHASH = GHASH_H(AAD || Ciphertext || len(AAD) || len(Ciphertext))
Tag = GHASH XOR AES-CTR(K, IV || counter=0, 0^128)
```

Onde H = AES-CTR(K, IV, 0^128) e a chave de GHASH.

**Vulnerabilidades conhecidas:**
- Reuso de nonce destruiu completamente a seguranca
- Forca bruta no tag de 32 bits e viavel (~2^32 operacoes)
- GHASH tem weakness quando o adendo e longo demais
- Side-channel em implementacoes de tabelas delookup

### 9.3 ChaCha20-Poly1305 -- Profundidade

**Estrutura interna:**

```
Poly1305_K = CHACHA20(K, nonce, 0)[0..31]
Poly1305_K = Poly1305_K AND 0xffffffc0ffffffc0ffffffc0fffffff
Ciphertext = CHACHA20(K, nonce, counter=1, Plaintext)
Tag = Poly1305(Poly1305_K, AAD || Ciphertext || padding || len(AAD) || len(Ciphertext))
```

**Vantagens sobre AES-GCM:**
- Nonce de 192 bits (XChaCha20) vs 96 bits (GCM) -- muito mais espaco
- Nao requer hardware AES-NI
- Resistente a timing side-channels por design
- Autenticacao baseada em aritmetica modular (Poly1305) vs GHASH

### 9.4 Decision Matrix

| Criterio | AES-GCM | ChaCha20-Poly1305 | Recomendacao |
|----------|---------|-------------------|--------------|
| Servidor com AES-NI | Muito rapido | Rapido | AES-GCM |
| Mobile/IoT | Lento | Muito rapido | ChaCha20-Poly1305 |
| TLS 1.3 | Suportado | Suportado | Ambos |
| Nonce space | 2^96 | 2^192 (XChaCha20) | ChaCha20 |
| Resistencia a nonce reuse | Nenhuma | Nenhuma | Nenhum (regenerar nonce) |
| NIST compliance | Sim | Nao | AES-GCM |

---

## 10. Geradores de Numeros Aleatorios

### 10.1 O Problema fundamental

A seguranca criptografica depende fundamentalmente da qualidade dos numeros aleatorios. Se um atacante pode prever os numeros aleatorios, ele pode:
- Prever chaves de sessao
- Prever salts de hashing
- Prever IVs de cifragem
- Prever nonces de authenticated encryption

### 10.2 Fontes de Entropy no Linux

**/dev/urandom:**
- Disponivel em todos os sistemas POSIX
- Nunca bloqueia (ao contrario de /dev/random)
- Alimentado por interrupcoes de hardware, timing de IO, e outros eventos
- RECOMENDADO para uso criptografico

**getrandom():**
- Disponivel no Linux 3.17+
- Chamada de sistema direta (nao requer fd)
- Suporta flag GRND_NONBLOCK para nao bloquear
- Suporta flag GRND_RANDOM para usar /dev/random
- RECOMENDADO (melhor que /dev/urandom por nao depender de file descriptors)

**/dev/random:**
- Pode bloquear apos o boot ate acumular suficiente entropy
- Historico controverso: versoes antigas "depletavam" entropy
- Apos Linux 4.8, usa o mesmo crng que /dev/urandom
- NAO RECOMENDADO para uso geral (use /dev/urandom ou getrandom)

### 10.3 Geracao de Chaves Criptograficas

```cpp
#include <sys/random.h>
#include <array>
#include <stdexcept>

class SecureRandom {
public:
    static std::array<uint8_t, 32> get_random_bytes() {
        std::array<uint8_t, 32> buffer;
        ssize_t result = getrandom(buffer.data(), buffer.size(), 0);
        if (result != static_cast<ssize_t>(buffer.size())) {
            throw std::runtime_error("Failed to get random bytes");
        }
        return buffer;
    }

    static uint64_t get_random_u64() {
        uint64_t value;
        ssize_t result = getrandom(&value, sizeof(value), 0);
        if (result != sizeof(value)) {
            throw std::runtime_error("Failed to get random u64");
        }
        return value;
    }

    // Para gerar chave de sessao TLS
    static std::array<uint8_t, 32> generate_session_key() {
        return get_random_bytes();
    }

    // Para gerar nonce/IV
    static std::array<uint8_t, 12> generate_iv() {
        std::array<uint8_t, 12> iv;
        ssize_t result = getrandom(iv.data(), iv.size(), 0);
        if (result != static_cast<ssize_t>(iv.size())) {
            throw std::runtime_error("Failed to generate IV");
        }
        return iv;
    }

    // Para gerar salt
    static std::array<uint8_t, 16> generate_salt() {
        std::array<uint8_t, 16> salt;
        ssize_t result = getrandom(salt.data(), salt.size(), 0);
        if (result != static_cast<ssize_t>(salt.size())) {
            throw std::runtime_error("Failed to generate salt");
        }
        return salt;
    }
};
```

### 10.4 CRNG (Cryptographic Random Number Generator) do Linux

O CRNG do Linux e o subsistema responsavel por fornecer numeros aleatorios criptograficos. Apos o boot, ele acumula entropy de:

- Interrupcoes de hardware (teclado, mouse, disco)
- Timing de interrupcoes de rede
- Timing de interrupcoes de timer
- Eventos de dispositivos USB
- Ruido de outros dispositivos

**O estado do CRNG:**
```
+-------------------------------------------+
|            CRNG State                     |
+-------------------------------------------+
|  Input Pool (entropy pool)                |
|  - Recebe eventos do sistema             |
|  - Mistura via SHA-1 / BLAKE2            |
+-------------------------------------------+
|  Blocking Pool                            |
|  - Gera numeros para /dev/random          |
|  - Bloqueia quando sem entropy            |
+-------------------------------------------+
|  Non-blocking Pool                        |
|  - Gera numeros para /dev/urandom         |
|  - Nunca bloqueia                         |
|  - Mesmo RNG do blocking pool (pos 4.8)   |
+-------------------------------------------+
```

---

## 11. CVE-2014-0160: Heartbleed -- Deep Dive

### 11.1 Visao Geral

Heartbleed e uma vulnerabilidade de buffer over-read no heartbeat extension do TLS/SSL, afetando a biblioteca OpenSSL (versoes 1.0.1 ate 1.0.1f). Publicada em 7 de abril de 2014, e uma das vulnerabilidades mais severas ja descobertas em software de seguranca.

| Propriedade | Valor |
|-------------|-------|
| CVE | CVE-2014-0160 |
| CVSS | 7.5 (critico) |
| Data de divulgacao | 7 de abril de 2014 |
| Impacto | Leitura de memoria do servidor |
| Alcance | ~17% dos servidores HTTPS na epoca |
| Biblioteca | OpenSSL 1.0.1 ate 1.0.1f |
| Correcao | OpenSSL 1.0.1g |

### 11.2 Como Funcionava o Heartbeat

O heartbeat e uma extensao do TLS que permite manter uma conexao ativa sem re-handshake. O protocolo funciona assim:

1. Cliente envia "heartbeat request" com dados (ex: "HELLO")
2. Servidor deve retornar os mesmos dados
3. Se o servidor nao suportar heartbeat, ele envia "heartbeat failure"

**Formato do heartbeat:**

```
+--------+--------+--------+--------+--------+--------+
|  Type  |        Payload       |     Payload         |
| (1B)   |    Length (2B)       |    (Variavel)       |
+--------+--------+--------+--------+--------+--------+
```

### 11.3 O Bug Vulneravel

A vulnerabilidade estava na verificacao do campo `payload_length`. O atacante podia enviar um heartbeat com `payload_length` maior que o tamanho real do payload:

```cpp
// CODIGO VULNERAVEL (simplificado do OpenSSL 1.0.1f)
int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int padding = 16;  // Heartbeat padding

    // Leitura do type
    hbtype = *p++;

    // Leitura do payload length (SEM VERIFICACAO!)
    n2s(p, payload);  // payload = campo de 2 bytes

    // AQUI ESTA O BUG: payload nao e validado contra o tamanho real
    // Envia de volta payload bytes a partir do ponteiro p
    // Se payload > tamanho real, le memoria adjacente!
    pl = p;

    // ... envia heartbeat response com payload bytes
    // Leitura de memoria alem do buffer designado
    return dtls1_heartbeat(s, hbtype, payload, pl);
}
```

### 11.4 Exploit Demonstrativo

```cpp
// DEMONSTRACAO DO CONCEITO (NAO USE PARA ATAQUES REAIS)
//
// Este codigo demonstra o conceito do bug Heartbleed.
// Em um ambiente real, o atacante enviaria isto via rede.

#include <cstdint>
#include <cstring>
#include <vector>
#include <iostream>

struct HeartbeatRequest {
    uint8_t type;
    uint16_t payload_length;
    // payload real aqui
};

// Simulacao do que acontece quando payload_length > payload real
std::vector<uint8_t> simulate_heartbleed(
    const uint8_t* legitimate_data, size_t legitimate_len,
    uint16_t claimed_length
) {
    std::vector<uint8_t> leaked_data;

    // O servidor copia 'claimed_length' bytes a partir do inicio dos dados
    // Se claimed_length > legitimate_len, le memoria adjacente
    for (size_t i = 0; i < claimed_length && i < legitimate_len + 1024; ++i) {
        if (i < legitimate_len) {
            leaked_data.push_back(legitimate_data[i]);
        } else {
            // Em um servidor real, isto leria memoria do processo
            // Aqui simulamos com dados ficticios
            leaked_data.push_back(0x41);  // 'A'
        }
    }

    return leaked_data;
}

int main() {
    // Dados legitimos do cliente (ex: "HELLO")
    uint8_t legitimate_data[] = "HELLO";
    size_t legitimate_len = strlen(reinterpret_cast<char*>(legitimate_data));

    // Atacante envia payload_length = 65535 (maximo de uint16_t)
    uint16_t malicious_length = 65535;

    auto leaked = simulate_heartbleed(
        legitimate_data, legitimate_len, malicious_length
    );

    std::cout << "Dados legitimos: " << legitimate_len << " bytes" << std::endl;
    std::cout << "Dados retornados: " << leaked.size() << " bytes" << std::endl;
    std::cout << "Leak: " << (leaked.size() - legitimate_len)
              << " bytes de memoria adjacente" << std::endl;

    return 0;
}
```

### 11.5 O Que Podia Ser Lido

Atraves do Heartbleed, um atacante podia ler:

1. **Chaves privadas do servidor** -- se estivesse em memoria no momento do ataque
2. **Cookies de sessao** -- permitindo session hijacking
3. **Dados de clientes** -- incluindo senhas e dados sensiveis
4. **Chaves de sessao TLS** -- permitindo descriptar comunicacoes gravadas

### 11.6 A Correcao

A correcao foi simples e elegante: adicionar validacao do campo payload_length:

```cpp
// CODIGO CORRIGIDO (OpenSSL 1.0.1g)
int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int padding = 16;

    // Verificacao basica de tamanho minimo
    if (s->s3->rrec.length < 1 + 2 + 16)
        return 0;  // packet too short

    hbtype = *p++;
    n2s(p, payload);

    // VALIDACAO CRITICA: verifica se o tamanho declarado e consistente
    if (1 + 2 + payload + 16 > s->s3->rrec.length)
        return 0;  // silently discard per RFC 6520

    pl = p;

    // Agora e seguro: payload esta dentro dos limites do buffer
    return dtls1_heartbeat(s, hbtype, payload, pl);
}
```

### 11.7 Lições e Prevencao

**Lições do Heartbleed:**

1. **Fuzzing estruturado** poderia ter encontrado o bug antes do lancamento
2. **Validacao de entrada** e critica mesmo em codigos "confiaveis"
3. **Auditorias de seguranca** devem ser rotineiras, nao apenas reativas
4. **Distribuicao de correcoes** deve ser rapida (OpenSSL levou 2 dias para corrigir)
5. **Transparencia** e essencial (os mantenedores foram transparentes na divulgacao)

**Prevencao em C++17:**

```cpp
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <vector>

// Verificacao robusta de tamanho
class SafeBuffer {
private:
    std::vector<uint8_t> data_;

public:
    explicit SafeBuffer(size_t capacity) : data_(capacity, 0) {}

    // Leitura segura com verificacao de limites
    uint16_t read_uint16(size_t offset) const {
        if (offset + sizeof(uint16_t) > data_.size()) {
            throw std::out_of_range("Buffer overflow in read_uint16");
        }
        uint16_t value;
        std::memcpy(&value, data_.data() + offset, sizeof(uint16_t));
        return value;
    }

    // Leitura de payload com verificacao completa
    std::vector<uint8_t> read_payload(
        size_t offset, uint16_t declared_length
    ) const {
        size_t end = offset + declared_length;

        // Verificacao dupla: offset nao ultrapassa e declared_length e valido
        if (offset > data_.size() || declared_length == 0) {
            throw std::invalid_argument("Invalid offset or length");
        }

        if (end > data_.size()) {
            throw std::out_of_range(
                "Payload length exceeds buffer size");
        }

        return std::vector<uint8_t>(
            data_.begin() + offset,
            data_.begin() + end
        );
    }

    // Getter para dados brutos
    const uint8_t* raw_data() const { return data_.data(); }
    size_t size() const { return data_.size(); }
};
```

---

## 12. CVE-2008-0166: Debian OpenSSL -- O Bug que Destruiu Milhoes de Chaves

### 12.1 Visao Geral

Em 2008, um desenvolvedor do Debian removeu acidentalmente o codigo de geracao de entropy do OpenSSL para silenciar um warning do Valgrind. Esta mudanca afetou todas as chaves geradas no Debian e derivados (Ubuntu, etc.) durante mais de 2 anos.

| Propriedade | Valor |
|-------------|-------|
| CVE | CVE-2008-0166 |
| CVSS | 7.5 (critico) |
| Data de divulgacao | 13 de maio de 2008 |
| Impacto | Chaves previsiveis |
| Alcance | Debian Lenny (testing) e todas as derivacoes |
| Duracao da vulnerabilidade | De setembro 2006 a maio 2008 |
| Chaves afetadas | ~32.000 chaves SSL publicas |

### 12.2 O Bug

O bug estava no arquivo `md_rand.c` do OpenSSL. O desenvolvedor removeu linhas que usavam `MD_Update` com dados de entropia do sistema operacional porque o Valgrind reportava warning de uso de dados nao inicializados:

```cpp
// CODIGO ORIGINAL (pre-bug)
int RAND_pseudo_bytes(unsigned char *buf, int num) {
    static int ssl3_seed_idx = 0;
    int i;

    // ... codigo anterior ...

    // ESTAS LINHAS FORAM REMOVIDAS:
    MD_Update(&m, &(md_c[0]), sizeof(md_c));  // entropy do sistema
    MD_Update(&m, buf, i);                      // dados do buffer
    // ...

    // CODIGO DEPOIS DA MUDANCA:
    // As linhas acima foram substituidas por:
    // (nenhuma adicao de entropia!)

    // Isto torna a saida deterministica!
    // Apenas 4 bits de entropia possiveis (pipe_len)
}
```

### 12.3 Impacto

**Chaves afetadas:**

- Chaves RSA geradas em Debian entre setembro 2006 e maio 2008
- Chaves DSA geradas no mesmo periodo
- Chaves ECDSA geradas no mesmo periodo
- Chaves SSH, SSL/TLS, e criptografia de disco

**Espaco de chaves reduzido:**

O espaco de chaves RSA foi reduzido de 2^128 (para 1024 bits) para apenas 32.768 chaves possiveis. Um atacante podia:

1. Gerar todas as 32.768 chaves possiveis
2. Testar cada uma contra a chave publica do servidor
3. Encontrar a chave privada em minutos

### 12.4 Como Foi Descoberto

Kees Cook, um desenvolvedor do Ubuntu, notou que chaves geradas em maquinas diferentes continham padroes suspeitos. Ele investigou e descobriu que as chaves eram previsiveis.

**Padrao suspeito:**

```
Chave 1: 0x... 7a3f 1b2c ...
Chave 2: 0x... 7a3f 1b2c ...
Chave 3: 0x... 7a3f 1b2c ...
// Mesmo prefixo em chaves geradas em momentos diferentes!
```

### 12.5 A Correcao

A correcao foi publicada como DSA-1571-1 e incluia:

1. Reverter a mudanca removida
2. Adicionar melhorias na geracao de entropy
3. Notificar usuarios para regerar chaves

**Porem, a correcao veio tarde demais.** Muitas chaves continuaram em uso por anos apos a divulgacao.

### 12.6 Lições

**Prevencoes contra este tipo de bug:**

1. **Testes de entropia** devem ser parte da suite de testes do projeto
2. **Validacao de saida** de geradores de numeros aleatorios deve ser continua
3. **Mudancas em codigos de seguranca** devem ser revisadas por multiplos revisores
4. **Distribuicao de correcoes** deve incluir roteiro de mitigacao (regenerar chaves)
5. **Dependencias de seguranca** devem ser monitoradas ativamente

**Teste de entropia para detectar regressoes:**

```cpp
#include <random>
#include <array>
#include <bitset>
#include <iostream>
#include <cmath>

class EntropyTester {
public:
    static double estimate_entropy(const std::vector<uint8_t>& data) {
        if (data.empty()) return 0.0;

        // Conta frequencia de cada byte
        std::array<size_t, 256> freq{};
        for (uint8_t byte : data) {
            freq[byte]++;
        }

        // Calcula entropia de Shannon
        double entropy = 0.0;
        size_t n = data.size();
        for (size_t f : freq) {
            if (f > 0) {
                double p = static_cast<double>(f) / n;
                entropy -= p * std::log2(p);
            }
        }

        return entropy;
    }

    static bool is_acceptable_entropy(
        const std::vector<uint8_t>& data,
        double min_entropy_per_byte = 7.5
    ) {
        double entropy = estimate_entropy(data);
        // Entropia maxima de 8 bits por byte
        return entropy >= min_entropy_per_byte;
    }

    // Testa se duas chaves geradas sao diferentes
    static bool are_keys_unique(
        const std::vector<uint8_t>& key1,
        const std::vector<uint8_t>& key2
    ) {
        return key1 != key2;
    }
};
```

---

## 13. Android PRNG Vulnerability: Entropy Depletion apos Fork

### 13.1 Visao Geral

Em 2013, pesquisadores da Universidade de Radboud descobriram que dispositivos Android (pre-4.2) usavam um PRNG fraco para gerar chaves criptograficas. O bug era causado por dois fatores:

1. PRNG inadequado (java.util.Random)
2. Estado do PRNG nao era bifurcado corretamente apos fork()

| Propriedade | Valor |
|-------------|-------|
| CVE | CVE-2013-4788 |
| CVSS | 7.5 (critico) |
| Data de divulgacao | 31 de julho de 2013 |
| Impacto | Chaves criptograficas previsiveis |
| Plataforma | Android 4.1 e anteriores |
| Correcao | Android 4.2 (SecureRandom) |

### 13.2 O Problema do PRNG

O Java `java.util.Random` nao e um PRNG criptografico seguro. Ele usa um LCG (Linear Congruential Generator) que e previsivel:

```java
// java.util.Random (VULNERAVEL para uso criptografico)
protected int next(int bits) {
    long oldseed = seed;
    long nextseed = (oldseed * 0x5DEECE66DL + 0xBL) & ((1L << 48) - 1);
    seed = nextseed;
    return (int)(nextseed >>> (48 - bits));
}
```

**Por que LCG e inseguro:**
- O proximo valor e deterministico a partir do estado atual
- Conhecendo 629 outputs consecutivos, e possivel prever todos os proximos
- Nao possui resistencia a ataques de retrocesso (backtracking resistance)

### 13.3 O Problema do Fork

Quando um processo Android faz fork (via `Runtime.exec()` ou `ProcessBuilder`), ambos os processos herdam o mesmo estado do PRNG. Se ambos gerarem numeros na mesma sequencia, os numeros serao identicos:

```
Processo Pai:  seed = 12345
                |
            fork()
                |
    +-----------+-----------+
    |                       |
Filho                    Pai
    |                       |
    | next()               | next()
    | resultado = X        | resultado = X (IDENTICO!)
```

### 13.4 O Ataque

O ataque funciona da seguinte forma:

1. Atacante força o aplicativo Android a fazer fork (ex: via Intent)
2. Ambos os processos herdam o mesmo estado do PRNG
3. Processo filho gera chaves RSA/ECDSA
4. Processo pai gera numeros aleatorios
5. Atacante compara os outputs e reconstrói o estado do PRNG
6. Com o estado reconstruido, preve todas as chaves futuras

### 13.5 A Correcao (Android 4.2+)

A correcao usou `SecureRandom` que:
- Usa `/dev/urandom` como fonte de entropia
- Re-seeda periodicamente
- Bifurca o estado corretamente apos fork

```java
// Android 4.2+ - CORRETO
import java.security.SecureRandom;

// Correto para uso criptografico
SecureRandom sr = new SecureRandom();
byte[] key = new byte[32];
sr.nextBytes(key);

// Correto apos fork - Android 4.2+ re-seeda automaticamente
```

### 13.6 Prevencao em C++

```cpp
#include <sys/random.h>
#include <unistd.h>
#include <fcntl.h>
#include <array>
#include <stdexcept>

class ForkSafeRandom {
public:
    static std::array<uint8_t, 32> generate_key() {
        std::array<uint8_t, 32> key;

        // getrandom() e fork-safe no Linux 3.17+
        // Ele detecta fork e re-seeda automaticamente
        ssize_t result = getrandom(key.data(), key.size(), 0);
        if (result != static_cast<ssize_t>(key.size())) {
            throw std::runtime_error("Failed to generate fork-safe key");
        }

        return key;
    }

    // Alternativa: gerar chave apos fork explícito
    static std::array<uint8_t, 32> generate_key_after_fork() {
        pid_t pid = fork();

        if (pid < 0) {
            throw std::runtime_error("fork failed");
        } else if (pid == 0) {
            // Processo filho - gera chave
            std::array<uint8_t, 32> key;
            ssize_t result = getrandom(key.data(), key.size(), 0);
            if (result != static_cast<ssize_t>(key.size())) {
                _exit(1);
            }

            // Envia chave de volta ao pai via pipe
            // (implementacao omitida)
            _exit(0);
        } else {
            // Processo pai - espera o filho
            int status;
            waitpid(pid, &status, 0);
            // Recupera chave do pipe
        }

        return {};
    }
};
```

---

## 14. Selecionando Bibliotecas Criptograficas

### 14.1 Criterios de Avaliacao

A escolha de uma biblioteca criptografica nao e trivial. Os criterios principais sao:

1. **Seguranca**: Historico de vulnerabilidades, tempo de resposta a CVEs, profundidade de auditorias
2. **API Design**: Facilidade de uso correto, dificuldade de uso incorreto, constant-time by default
3. **Performance**: Throughput, latencia, suporte a hardware acceleration
4. **Manutencao**: Atividade de desenvolvimento, tempo de vida util, estabilidade de API
5. **Portabilidade**: Suporte a SO, compiladores, arquiteturas
6. **Compliance**: FIPS 140-2/3, Common Criteria, conformidade NIST
7. **Tamanho**: Footprint em binario, dependencias

### 14.2 OpenSSL

OpenSSL e a biblioteca criptografica mais utilizada no mundo. Apesar de sua complexidade, fornece a cobertura mais completa de protocolos e algoritmos.

**Vantagens:**
- Cobertura completa: TLS, X.509, PKCS, CMS, OCSP, CRL
- Suporte a todos os algoritmos principais
- Grande ecossistema de ferramentas (openssl CLI)
- Compatibilidade retroativa
- Suporte a FIPS

**Desvantagens:**
- API complexa e propensa a erros (BIO, EVP, etc.)
- Historico de vulnerabilidades (Heartbleed, Poodle, etc.)
- Documentacao dispersa
- Grandes superficies de ataque
- Configuracao complexa

**Quando usar OpenSSL:**
- Servidores que precisam de TLS 1.3
- Sistemas que precisam de X.509/PKI
- Integracao com ferramentas de seguranca existentes

### 14.3 libsodium

libsodium e uma fork do NaCl (Networking and Cryptography library) de Daniel J. Bernstein. Projetado para ser facil de usar de forma correta.

**Vantagens:**
- API simples e segura por design
- Resiste a side-channels por design
- NaCl primitives (XSalsa20, X25519, Ed25519)
- Fornce AEAD, KDF, hashing, assinaturas
- Constant-time por padrao

**Desvantagens:**
- Nao suporta TLS (usar libouetils ou mbedTLS)
- Nao suporta X.509/PKI
- Algoritmos limitados aos do NaCl
- Nao suporta FIPS

**Quando usar libsodium:**
- Aplicacoes que precisam de crypto basico (cifrar, assinar, hash)
- Sistemas que valorizam facilidade de uso
- Projetos que preferem modernidade sobre compatibilidade
- Mobile e embedded

### 14.4 BoringSSL

BoringSSL e o fork do OpenSSL mantido pelo Google. Usado em Chromium, Android, e servicos Google.

**Vantagens:**
- API simplificada do OpenSSL
- Remocao de codigo morto e features nao usadas
- Foco em TLS 1.3 e CT (Certificate Transparency)
- Melhorias de seguranca sobre OpenSSL
- Usado em um dos ecossistemas maiores do mundo

**Desvantagens:**
- Nao e projetado para uso publico
- API instavel (pode mudar entre versoes)
- Menos documentacao que OpenSSL
- Nao suporta todos os protocolos do OpenSSL
- Difil de encontrar binarios prontos

**Quando usar BoringSSL:**
- Projetos que precisam de TLS moderno e seguro
- Integracao com ecossistema Google
- Quando OpenSSL e complexo demais mas libsodium nao cobre

### 14.5 Botan

Botan e uma biblioteca C++ pura com foco em design moderno e seguranca.

**Vantagens:**
- API moderna C++ (RAII, exceptions, strong types)
- Suporte a criptografia post-quantum
- Boa documentacao e testes
- Modular: so linka o que usa
- Suporte a FIPS

**Desvantagens:**
- Performance inferior ao OpenSSL em TLS
- Menor adocao que OpenSSL
- Nao e o padrao da industria
- Menor ecossistema de ferramentas

**Quando usar Botan:**
- Projetos C++ que valorizam design moderno
- Quando precisam de post-quantum crypto
- Para bibliotecas onde modularidade e importante

---

## 15. Tabela Comparativa de Bibliotecas

| Criterio | OpenSSL | libsodium | BoringSSL | Botan |
|----------|---------|-----------|-----------|-------|
| **Idioma** | C | C | C | C++ |
| **API complexity** | Alta | Baixa | Media | Media |
| **TLS** | Sim | Nao | Sim | Sim |
| **X.509/PKI** | Sim | Nao | Sim | Sim |
| **FIPS 140** | Sim | Nao | Parcial | Sim |
| **AEAD** | AES-GCM, ChaCha20 | XChaCha20, AES-GCM | AES-GCM, ChaCha20 | AES-GCM, ChaCha20 |
| **Assinaturas** | RSA, ECDSA | Ed25519, EdDSA | RSA, ECDSA | RSA, ECDSA, EdDSA |
| **KDF** | HKDF, PBKDF2 | Argon2, HKDF | HKDF, PBKDF2 | HKDF, Argon2 |
| **Hash** | SHA-2/3, BLAKE2 | BLAKE2b, SHA-2/3 | SHA-2/3, BLAKE2 | SHA-2/3, BLAKE2/3 |
| **Auditorias** | Multiplas | Multiplas | Google interna | Multiplas |
| **Pos-quantum** | Parcial | Nao | Parcial | Sim |
| **Manutencao** | Ativa | Ativa | Ativa | Ativa |
| **Tamanho** | ~5 MB | ~200 KB | ~3 MB | ~2 MB |

### 15.1 Matriz de Decisao

```
Voce precisa de:
    |
    +-- TLS/X.509/PKI? ----> OpenSSL ou Botan
    |       |
    |       +-- API simples? --> Botan
    |       +-- Maximo suporte? --> OpenSSL
    |
    +-- Crypto basico? ----> libsodium
    |       |
    |       +-- AEAD + KDF + Hash --> libsodium
    |       +-- Precisa de TLS? --> Usar com mbedTLS
    |
    +-- Post-quantum? ----> Botan
    |
    +-- Ecossistema Google? --> BoringSSL
```

### 15.2 Exemplo: Usando libsodium para Todas as Operacoes

```cpp
#include <sodium.h>
#include <vector>
#include <array>
#include <string>
#include <stdexcept>
#include <cstring>

class CryptoSuite {
public:
    CryptoSuite() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    // 1. Geração de chaves
    std::array<uint8_t, 32> generate_key() {
        std::array<uint8_t, 32> key;
        crypto_aead_xchacha20poly1305_ietf_keygen(key.data());
        return key;
    }

    // 2. Cifragem AEAD
    struct EncryptedData {
        std::vector<uint8_t> ciphertext;
        std::array<uint8_t, 24> nonce;
    };

    EncryptedData encrypt(
        const uint8_t* plaintext, size_t len,
        const uint8_t* key,
        const uint8_t* aad = nullptr, size_t aad_len = 0
    ) {
        EncryptedData result;
        result.ciphertext.resize(len);

        randombytes_buf(result.nonce.data(), result.nonce.size());

        unsigned long long actual_len;
        if (crypto_aead_xchacha20poly1305_ietf_encrypt(
                result.ciphertext.data(), &actual_len,
                plaintext, len,
                aad, aad_len,
                nullptr,
                result.nonce.data(), key) != 0) {
            throw std::runtime_error("Encryption failed");
        }

        result.ciphertext.resize(actual_len);
        return result;
    }

    // 3. Decifragem
    std::vector<uint8_t> decrypt(
        const uint8_t* ciphertext, size_t len,
        const uint8_t* key,
        const std::array<uint8_t, 24>& nonce,
        const uint8_t* aad = nullptr, size_t aad_len = 0
    ) {
        std::vector<uint8_t> plaintext(len);
        unsigned long long actual_len;

        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), &actual_len,
                nullptr,
                ciphertext, len,
                aad, aad_len,
                nonce.data(), key) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(actual_len);
        return plaintext;
    }

    // 4. Hashing
    std::array<uint8_t, 32> hash(const uint8_t* data, size_t len) {
        std::array<uint8_t, 32> out;
        crypto_generichash(out.data(), out.size(), data, len, nullptr, 0);
        return out;
    }

    // 5. HMAC
    std::array<uint8_t, 32> hmac(
        const uint8_t* key, size_t key_len,
        const uint8_t* data, size_t data_len
    ) {
        std::array<uint8_t, 32> out;
        crypto_auth_hmacsha256_state state;
        crypto_auth_hmacsha256_init(&state, key, key_len);
        crypto_auth_hmacsha256_update(&state, data, data_len);
        crypto_auth_hmacsha256_final(&state, out.data());
        sodium_memzero(&state, sizeof(state));
        return out;
    }

    // 6. Assinatura digital
    struct KeyPair {
        std::array<uint8_t, 32> public_key;
        std::array<uint8_t, 64> secret_key;
    };

    KeyPair generate_signing_keypair() {
        KeyPair kp;
        crypto_sign_ed25519_keypair(kp.public_key.data(),
                                    kp.secret_key.data());
        return kp;
    }

    std::array<uint8_t, 64> sign(
        const uint8_t* message, size_t msg_len,
        const uint8_t* secret_key
    ) {
        std::array<uint8_t, 64> sig;
        unsigned long long sig_len;
        crypto_sign_ed25519_detached(
            sig.data(), &sig_len,
            message, msg_len,
            secret_key
        );
        return sig;
    }

    bool verify(
        const uint8_t* message, size_t msg_len,
        const std::array<uint8_t, 64>& sig,
        const uint8_t* public_key
    ) {
        return crypto_sign_ed25519_verify_detached(
            sig.data(), message, msg_len, public_key
        ) == 0;
    }

    // 7. Key exchange
    struct KeyExchangeResult {
        std::array<uint8_t, 32> shared_secret;
        std::array<uint8_t, 32> public_key;
    };

    KeyExchangeResult key_exchange() {
        KeyExchangeResult result;
        crypto_kx_keypair(result.public_key.data(),
                          result.shared_secret.data());
        return result;
    }
};
```

---

## 16. Exercicios

### Exercicio 1: Timing Attack em Comparacao de MAC (Nivel: Facil)

Implemente um ataque de timing para demonstrar por que `operator==` e inseguro para comparacao de MACs:

```cpp
// Implemente a funcao vulnerable_time_compare
// que retorna o tempo que leva para comparar dois MACs
double vulnerable_time_compare(
    const std::array<uint8_t, 32>& mac1,
    const std::array<uint8_t, 32>& mac2
);

// Implemente a funcao secure_time_compare
// que usa comparacao constant-time
bool secure_time_compare(
    const std::array<uint8_t, 32>& mac1,
    const std::array<uint8_t, 32>& mac2
);
```

**Requisitos:**
- Demonstre que a funcao vulnerable retorna tempos diferentes dependendo do numero de bytes corretos
- Demonstre que a funcao secure retorna tempos constantes

### Exercicio 2: Implementacao de AES-GCM com OpenSSL (Nivel: Medio)

Implemente uma classe completa de authenticated encryption usando AES-256-GCM:

```cpp
class AeadCipher {
public:
    // Gera chave aleatoria
    virtual std::vector<uint8_t> generate_key() = 0;

    // Cifra com AEAD
    virtual struct {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> nonce;
        std::vector<uint8_t> tag;
    } encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad,
        const std::vector<uint8_t>& key
    ) = 0;

    // Decifra com AEAD
    virtual std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& aad,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& tag,
        const std::vector<uint8_t>& key
    ) = 0;
};
```

**Requisitos:**
- Implemente usando OpenSSL (EVP interface)
- Valide todos os parametros de entrada
- Use exception handling adequado
- Escreva testes unitarios que verifiquem:
  - Cifragem e decifragem corretas
  - Autenticacao (decifrar com tag alterado deve falhar)
  - Reuso de nonce (deve ser detectado/prevenido)

### Exercicio 3: HKDF Completo (Nivel: Medio)

Implemente HKDF-RFC5869 completo e demonstre a derivacao de chaves:

```cpp
class HKDF_RFC5869 {
public:
    // Extracao
    std::vector<uint8_t> extract(
        const std::vector<uint8_t>& ikm,
        const std::vector<uint8_t>& salt = {}
    );

    // Expansao
    std::vector<uint8_t> expand(
        const std::vector<uint8_t>& prk,
        const std::vector<uint8_t>& info,
        size_t length
    );
};
```

**Testes:**
- Use os vetores de teste do RFC 5869 Appendix A
- Verifique que a saida e deterministica para mesma entrada
- Verifique que salt vazio e tratado corretamente

### Exercicio 4: Deteccao de PRNG Fraco (Nivel: Dificil)

Implemente um teste estatistico para detectar se um PRNG e adequado para uso criptografico:

```cpp
class PRNGTester {
public:
    // Gera N amostras do PRNG e retorna o vetor
    std::vector<uint8_t> generate_samples(
        std::function<uint8_t()> prng, size_t n
    );

    // Teste de entropia de Shannon
    double shannon_entropy(const std::vector<uint8_t>& samples);

    // Teste de frequencia (Chi-squared)
    double chi_squared_test(const std::vector<uint8_t>& samples);

    // Teste de runs (sequencias de bits)
    double runs_test(const std::vector<uint8_t>& samples);

    // Avaliacao completa
    struct PRNGReport {
        double entropy_per_byte;
        double chi_squared_p_value;
        double runs_p_value;
        bool suitable_for_crypto;
    };

    PRNGReport evaluate(std::function<uint8_t()> prng, size_t samples = 100000);
};
```

**Cenarios de teste:**
- Teste com `std::rand()` (deve falhar)
- Teste com `std::mt19937` (deve falhar)
- Teste com `/dev/urandom` (deve passar)
- Teste com `getrandom()` (deve passar)

### Exercicio 5: Heartbleed Exploit Demo (Nivel: Dificil)

Implemente um servidor e cliente TCP simples que demonstre o conceito do Heartbleed:

```cpp
// Servidor: processa heartbeat requests
class HeartbleedServer {
public:
    void start(uint16_t port);
    void handle_heartbeat(const uint8_t* request, size_t len);
};

// Cliente: envia heartbeat com payload_length > payload real
class HeartbleedClient {
public:
    std::vector<uint8_t> exploit(
        const std::string& host, uint16_t port,
        uint16_t malicious_length
    );
};
```

**Requisitos:**
- O servidor deve simular a behavior do OpenSSL vulneravel
- O cliente deve enviar heartbeat com payload_length > 255
- O servidor deve retornar bytes alem do payload legitimo
- Documente os bytes "vazados" e explique como um atacante real os usaria

---

## 17. Referencias e Leituras Adicionais

### 17.1 Livros

1. **"Cryptography Engineering"** -- Niels Ferguson, Bruce Schneier, Tadayoshi Kohno
   - O livro fundamental de engenharia criptografica. Cobertura completa de design, implementacao, e testes.

2. **"Serious Cryptography"** -- Jean-Philippe Aumasson
   - Visao moderna de criptografia com foco em implementacao. Excelente para C++.

3. **"Applied Cryptography"** -- Bruce Schneier
   - Referencia classica. Apesar de datado, conceitos fundamentais permanecem validos.

4. **"The Cryptoparty Handbook"** -- Schuyler Earle (ed.)
   - Pratico e acessivel. Bom para aprender o basico antes de se aprofundar.

5. **"Bulletproofs, Ristretto, and Decaf"** -- Mike Hamburg
   - Avancado. Para quem quer entender o estado da arte em construcao de primitivas.

### 17.2 Paper Academicos

6. **"The TLS Protocol Version 1.0"** -- K. Hickman et al. (RFC 2246)
   - O paper original do TLS. Entender a evolucao e critico para evitar erros historicos.

7. **"A Provably Secure Strong Diffie-Hellman Protocol"** -- M. Bellare, P. Rogaway
   - Fundamento teorico de key exchange seguro.

8. **"The Galois/Counter Mode of Operation"** -- D. McGrew, J. Viega (NIST SP 800-38D)
   - Especificacao padrao de GCM. Leitura obrigatoria para uso correto.

9. **"ChaCha20 and Poly1305 for IETF Protocols"** -- Y. Nir, A. Langley (RFC 8439)
   - Especificacao de ChaCha20-Poly1305. Deve ser seguida rigorosamente.

10. **"Edwards-curve Digital Signature Algorithm (EdDSA)"** -- S. Josefsson, I. Liusvaara (RFC 8032)
    - Especificacao de Ed25519 e Ed448.

### 17.3 Artigos de Seguranca

11. **"Heartbleed: Anatomy of a catastrophic bug"** -- Alex Horn
    - Analise detalhada do bug CVE-2014-0160.

12. **"Mining Your Ps and Qs: Detection of Widespread Weak Keys in Network Devices"** -- Heninger et al.
    - O paper que revelou CVE-2008-0166 e seu impacto em escala.

13. **"Android Security: Broken PRNG"** -- Universidade de Radboud
    - Documentacao completa da vulnerabilidade PRNG do Android.

14. **"NIST SP 800-57: Recommendation for Key Management"**
    - Guia do NIST para gerenciamento de chaves. Fundamental para decisoes de tamanhos e ciclos de vida.

15. **"CRIME: Compression Ratio Info-leak Made Easy"** -- Rizzo, Duong
    - Vulnerabilidade de side-channel em TLS que motivou mudancas no TLS 1.3.

### 17.4 RFCs Essenciais

| RFC | Titulo | Relevancia |
|-----|--------|------------|
| RFC 5246 | TLS 1.2 | Basico para entender TLS |
| RFC 8446 | TLS 1.3 | Padrao moderno de TLS |
| RFC 8439 | ChaCha20-Poly1305 | AEAD moderno |
| RFC 8032 | EdDSA | Assinaturas modernas |
| RFC 5869 | HKDF | Derivacao de chaves |
| RFC 7748 | X25519/X448 | Key exchange moderno |
| RFC 8017 | PKCS#1 RSA | RSA padrao |
| RFC 7539 | ChaCha20-Poly1305 | Versao IETF |
| RFC 6979 | Deterministic ECDSA | Previne nonce reuse |

### 17.5 Ferramentas e Recursos

| Recurso | URL | Descricao |
|---------|-----|-----------|
| OpenSSL | openssl.org | Biblioteca criptografica principal |
| libsodium | doc.libsodium.org | Biblioteca facil e segura |
| BoringSSL | boringssl.googlesource.com | Fork OpenSSL do Google |
| Botan | botan.randombit.net | Biblioteca C++ moderna |
| NIST Crypto Guidelines | csrc.nist.gov | Documentacao NIST |
| Cryptopals | cryptopals.com | Exercicios praticos |

### 17.6 Cursos e Treinamentos

- **"Applied Cryptography"** -- Coursera (Universidade de Maryland)
- **"Cryptography I"** -- Coursera (Stanford, Dan Boneh)
- **"Security Tube Linux Encryption Expert"** -- SecurityTube
- **"SANS SEC575"** -- Network Security Monitoring
- **"Cryptopals Challenges"** -- cryptopals.com (exercicios praticos)

### 17.7 Comunidades

- **IETF Crypto Forum Research Group (CFRG)** -- criptografia moderna
- **NIST Post-Quantum Cryptography** -- criptografia post-quantum
- **OpenSSL-dev mailing list** -- desenvolvimento OpenSSL
- **libsodium mailing list** -- discussao de libsodium
- **crypto.stackexchange.com** -- perguntas e respostas sobre criptografia

---

## Resumo do Capitulo

Neste capitulo, estabelecemos as bases da engenharia criptografica:

1. **Diferenca entre teoria e pratica**: Criptografia teorica estuda propriedades abstratas; engenharia criptografica lida com implementacoes corretas em sistemas reais.

2. **Modelo de ameaca**: Antes de escolher algoritmos, devemos entender quem esta atacando, o que querem, e como podem atacar.

3. **Primitivas fundamentais**: Cifragem simetrica (AES, ChaCha20), MACs (HMAC, Poly1305), assinaturas (ECDSA, Ed25519), e hash (SHA-256, SHA-3, BLAKE2/3).

4. **Authenticated Encryption**: AEAD (AES-GCM, ChaCha20-Poly1305) e o padrao moderno, eliminando erros comuns de construcao manual.

5. **Geracao de numeros aleatorios**: `/dev/urandom`, `getrandom()`, e CRNG do Linux sao as fontes seguras. Nunca use PRNGs nao criptograficos.

6. **Falhas historicas**: Heartbleed, Debian OpenSSL, e Android PRNG demonstram por que implementacao correta e critica.

7. **Escolha de bibliotecas**: OpenSSL (completo), libsodium (facil), BoringSSL (Google), Botan (C++ moderno) -- cada um com tradeoffs distintos.

O proximo capitulo explorara o gerenciamento de chaves em profundidade, incluindo HSMs, key wrapping, e lifecycle management.

---

## Apendice A: Padroes de Codificacao Criptografica em C++

### A.1 Convencoes de Nomenclatura

A nomenclatura inconsistente e uma fonte comum de bugs em codigo criptografico. Defina padroes claros e os aplique rigorosamente:

```cpp
// PADRAO CORRETO: Nomes descritivos e semanticos
namespace crypto {

// Tipos fortes para chaves -- previne mistura acidental
struct symmetric_key {
    std::array<uint8_t, 32> data;

    explicit symmetric_key(const std::array<uint8_t, 32>& raw)
        : data(raw) {}

    // Proibe copia (chaves nao devem ser copiadas sem intencao)
    symmetric_key(const symmetric_key&) = delete;
    symmetric_key& operator=(const symmetric_key&) = delete;

    // Permite movimento
    symmetric_key(symmetric_key&&) = default;
    symmetric_key& operator=(symmetric_key&&) = default;

    // Limpeza segura no destruidor
    ~symmetric_key() {
        sodium_memzero(data.data(), data.size());
    }
};

// Tipo para nonce -- previne reuso acidental
struct nonce_96bit {
    std::array<uint8_t, 12> data;

    static nonce_96bit generate() {
        nonce_96bit n;
        randombytes_buf(n.data.data(), n.data.size());
        return n;
    }
};

// Tipo para nonce de 192 bits (XChaCha20)
struct nonce_192bit {
    std::array<uint8_t, 24> data;

    static nonce_192bit generate() {
        nonce_192bit n;
        randombytes_buf(n.data.data(), n.data.size());
        return n;
    }
};

}  // namespace crypto
```

### A.2 Gerenciamento de Memoria Segura

A memoria que contem chaves e dados sensiveis deve ser tratada com cuidado especial:

```cpp
#include <sodium.h>
#include <vector>
#include <cstddef>

class SecureBuffer {
private:
    uint8_t* data_;
    size_t size_;
    bool locked_;

public:
    explicit SecureBuffer(size_t size)
        : data_(nullptr), size_(size), locked_(false)
    {
        // Aloca memoria
        data_ = static_cast<uint8_t*>(std::malloc(size));
        if (!data_) throw std::bad_alloc();

        // Bloqueia na memoria fisica (previne swapping)
        if (mlock(data_, size) == 0) {
            locked_ = true;
        }
        // mlock pode falhar em containers -- nao e erro fatal

        // Garante que a memoria esta zerada
        sodium_memzero(data_, size);
    }

    ~SecureBuffer() {
        if (data_) {
            // Limpa antes de liberar
            sodium_memzero(data_, size_);

            // Desbloqueia da memoria fisica
            if (locked_) {
                munlock(data_, size_);
            }

            std::free(data_);
            data_ = nullptr;
        }
    }

    // Proibe copia
    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;

    // Permite movimento
    SecureBuffer(SecureBuffer&& other) noexcept
        : data_(other.data_), size_(other.size_), locked_(other.locked_)
    {
        other.data_ = nullptr;
        other.size_ = 0;
        other.locked_ = false;
    }

    SecureBuffer& operator=(SecureBuffer&& other) noexcept {
        if (this != &other) {
            // Libera memoria atual
            if (data_) {
                sodium_memzero(data_, size_);
                if (locked_) munlock(data_, size_);
                std::free(data_);
            }

            data_ = other.data_;
            size_ = other.size_;
            locked_ = other.locked_;

            other.data_ = nullptr;
            other.size_ = 0;
            other.locked_ = false;
        }
        return *this;
    }

    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }
};
```

### A.3 Tratamento de Erros

O tratamento de erros em criptografica e critico. Erros silenciados podem levar a vulnerabilidades graves:

```cpp
// PADRAO INCORRETO: Erros silenciados
void bad_example() {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    // Se ctx for null, o proximo chamada vai crashar
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    // Se a inicializacao falhar, continuamos com estado inconsistente
    EVP_EncryptUpdate(ctx, nullptr, nullptr, nullptr, 0);
    // ...
    EVP_CIPHER_CTX_free(ctx);
}

// PADRAO CORRETO: Erros tratados com RAII
class CipherContext {
private:
    EVP_CIPHER_CTX* ctx_;

public:
    CipherContext() : ctx_(EVP_CIPHER_CTX_new()) {
        if (!ctx_) {
            throw std::runtime_error("Failed to create cipher context");
        }
    }

    ~CipherContext() {
        if (ctx_) EVP_CIPHER_CTX_free(ctx_);
    }

    // Proibe copia
    CipherContext(const CipherContext&) = delete;
    CipherContext& operator=(const CipherContext&) = delete;

    // Conversao para o ponteiro bruto
    EVP_CIPHER_CTX* get() { return ctx_; }
    const EVP_CIPHER_CTX* get() const { return ctx_; }

    // Liberacao explicita
    void release() {
        if (ctx_) {
            EVP_CIPHER_CTX_free(ctx_);
            ctx_ = nullptr;
        }
    }
};

// Uso correto com RAII
void good_example() {
    CipherContext ctx;

    if (EVP_EncryptInit_ex(ctx.get(), EVP_aes_256_gcm(),
                            nullptr, nullptr, nullptr) != 1) {
        throw std::runtime_error("Cipher init failed");
    }

    // ... operacoes ...

    // Cleanup automatico no destruidor
}
```

### A.4 Constant-Time Operations

Operacoes de comparacao e verificacao de assinatura devem ser constant-time:

```cpp
#include <sodium.h>
#include <cstring>

namespace crypto {

// Comparacao constant-time de dois buffers
bool constant_time_compare(
    const uint8_t* a, const uint8_t* b, size_t len
) {
    // libsodium fornece comparacao constant-time
    return sodium_memcmp(a, b, len) == 0;
}

// Verificacao de assinatura Ed25519 (ja e constant-time)
bool verify_signature(
    const uint8_t* signature, size_t sig_len,
    const uint8_t* message, size_t msg_len,
    const uint8_t* public_key
) {
    if (sig_len != 64) return false;

    // crypto_sign_ed25519_verify_detached e constant-time
    return crypto_sign_ed25519_verify_detached(
        signature, message, msg_len, public_key
    ) == 0;
}

// Verificacao de tag HMAC (constant-time via libsodium)
bool verify_hmac(
    const uint8_t* expected_tag, size_t tag_len,
    const uint8_t* key, size_t key_len,
    const uint8_t* message, size_t msg_len
) {
    if (tag_len != 32) return false;

    std::array<uint8_t, 32> computed_tag;
    crypto_auth_hmacsha256_state state;

    crypto_auth_hmacsha256_init(&state, key, key_len);
    crypto_auth_hmacsha256_update(&state, message, msg_len);
    crypto_auth_hmacsha256_final(&state, computed_tag.data());

    // Comparacao constant-time
    bool result = sodium_memcmp(
        computed_tag.data(), expected_tag, tag_len
    ) == 0;

    sodium_memzero(&state, sizeof(state));
    sodium_memzero(computed_tag.data(), computed_tag.size());

    return result;
}

}  // namespace crypto
```

---

## Apendice B: Matrizes de Decisao Detalhadas

### B.1 Escolha de Algoritmo por Caso de Uso

| Caso de Uso | Algoritmo | Tamanho Chave | Observacoes |
|-------------|-----------|---------------|-------------|
| Cifrar dados em repouso | AES-256-GCM | 256 bits | Com IV unico por arquivo |
| Cifrar dados em transito | ChaCha20-Poly1305 ou AES-GCM | 256 bits | TLS 1.3 |
| Hash de senhas | Argon2id | N/A | Com salt unico |
| Assinatura de dados | Ed25519 | 32 bits | Mais rapido que ECDSA |
| Key exchange | X25519 | 256 bits | Forward secrecy |
| HMAC | HMAC-SHA256 | 256 bits | Para verificacao de integridade |
| KDF | HKDF-SHA256 | Variavel | Para derivar subchaves |
| Password hashing | Argon2id | N/A | Com salt e memoria |
| Token generation | CSPRNG | 128+ bits | Via getrandom() |

### B.2 Tamanhos de Chaves e Seguranca

| Tamanho | Seguranca (bits) | Tempo para quebrar (anos*) | Uso |
|---------|-----------------|---------------------------|-----|
| AES-128 | 128 | ~10^38 | Minimo aceitavel |
| AES-192 | 192 | ~10^45 | Para dados de longo prazo |
| AES-256 | 256 | ~10^52 | Para dados muito sensiveis |
| RSA-2048 | ~112 | ~10^17 | Minimo aceitavel |
| RSA-3072 | ~128 | ~10^24 | Recomendado |
| RSA-4096 | ~140 | ~10^35 | Para dados de longo prazo |
| Ed25519 | 128 | ~10^38 | Recomendado |
| X25519 | 128 | ~10^38 | Recomendado |

*Baseado em 2^128 operacoes por segundo (estimativa conservadora com hardware atual)

### B.3 Escolha de Hash

| Requisito | Algoritmo | Saida | Performance |
|-----------|-----------|-------|-------------|
| Integridade basica | SHA-256 | 256 bits | ~300 MB/s |
| Alta performance | BLAKE2b | 256-512 bits | ~900 MB/s |
| Massivamente paralelo | BLAKE3 | Variavel | ~2 GB/s |
| NIST compliance | SHA-256 ou SHA-3 | 256 bits | ~300/200 MB/s |
| Password hashing | Argon2id | Variavel | ~100 ms |
| Key derivation | HKDF-SHA256 | Variavel | ~300 MB/s |

---

## Apendice C: Cheklist de Seguranca Criptografica

Use este checklist antes de lancar qualquer codigo criptografico:

### C.1 Geracao de Chaves

- [ ] Chaves geradas via CSPRNG (`/dev/urandom`, `getrandom()`, `BCryptGenRandom`)
- [ ] Chaves de 256 bits para simetricos, 3072+ bits para RSA, 256 bits para curvas
- [ ] Chaves armazenadas em memoria protegida (`mlock`, `VirtualLock`)
- [ ] Chaves limpas apos uso (`sodium_memzero`)
- [ ] Chaves nunca em logs, core dumps, ou debug output

### C.2 Cifragem

- [ ] Usando AEAD (AES-GCM ou ChaCha20-Poly1305)
- [ ] Nonce gerado aleatoriamente (nao reutilizado)
- [ ] IV/Nonce de tamanho correto (96 bits para GCM, 96/192 bits para ChaCha20)
- [ ] Tag de autenticacao verificado ANTES de decifrar
- [ ] AAD inclui dados de contexto quando necessario

### C.3 Hashing

- [ ] SHA-256 ou superior para uso geral
- [ ] Argon2id para password hashing
- [ ] Salt unico por hash (gerado via CSPRNG)
- [ ] Iteracoes de work factor adequadas
- [ ] Resultado do hash em variavel de tamanho fixo

### C.4 Assinaturas

- [ ] Ed25519 ou ECDSA-P256 para assinaturas
- [ ] Nonce deterministic (RFC 6979) para ECDSA
- [ ] Verificacao de assinatura em contexto seguro
- [ ] Certificados X.509 validados contra chain of trust
- [ ] Chaves de assinatura rotacionadas periodicamente

### C.5 Transporte

- [ ] TLS 1.3 (ou 1.2 com ECDHE + AES-GCM)
- [ ] Forward secrecy habilitado
- [ ] Certificados validados (hostname, CA, data de validade)
- [ ] OCSP stapling quando possivel
- [ ] HSTS habilitado

### C.6 Armazenamento

- [ ] Dados sensiveis cifrados em repouso
- [ ] Chaves de cifragem nao armazenadas junto aos dados
- [ ] Backup de chaves em HSM ou vault dedicado
- [ ] Key rotation policy definida e implementada
- [ ] Logs sanitizados (sem dados sensiveis)

---

## Apendice D: Glossario de Termos

| Termo | Definicao |
|-------|-----------|
| AEAD | Authenticated Encryption with Associated Data -- cifragem que autentica dados e metadados |
| ASN.1 | Abstract Syntax Notation One -- formato para estruturas de dados em PKI |
| CBC | Cipher Block Chaining -- modo de operacao simetrico (descontinuado) |
| CTR | Counter Mode -- modo de operacao que transforma bloque cipher em stream cipher |
| CSPRNG | Cryptographically Secure Pseudo-Random Number Generator |
| DER | Distinguished Encoding Rules -- formato binario para certificados X.509 |
| DH | Diffie-Hellman -- protocolo de key exchange |
| DHE | Ephemeral Diffie-Hellman -- DH com chaves temporarias |
| ECDH | Elliptic Curve Diffie-Hellman -- DH sobre curvas elipticas |
| ECDHE | Ephemeral ECDH -- ECDH com chaves temporarias |
| ECDSA | Elliptic Curve Digital Signature Algorithm |
| EdDSA | Edwards-curve Digital Signature Algorithm |
| GCM | Galois/Counter Mode -- modo AEAD baseado em CTR e GHASH |
| GHASH | Funcao hash usada internamente pelo GCM |
| HKDF | HMAC-based Key Derivation Function (RFC 5869) |
| HMAC | Hash-based Message Authentication Code |
| HSM | Hardware Security Module -- dispositivo fisico para protecao de chaves |
| IV | Initialization Vector -- valor aleatorio usado na inicializacao de cifragem |
| KDF | Key Derivation Function -- funcao para derivar chaves a partir de material de segredo |
| Nonce | Numero usado uma vez -- valor aleatorio unico por mensagem |
| OID | Object Identifier -- identificador unico em ASN.1 |
| PEM | Privacy Enhanced Mail -- formato ASCII para chaves e certificados |
| PKI | Public Key Infrastructure -- infraestrutura de chaves publicas |
| Poly1305 | Authenticador baseado em aritmetica modular |
| PRNG | Pseudo-Random Number Generator |
| RSA | Rivest-Shamir-Adleman -- algoritmo de cifraga/assinatura baseado em fatoracao |
| X.509 | Padrao para certificados digitais |
| XChaCha20 | ChaCha20 com nonce de 192 bits (mais seguro contra reuso) |

---

## Apendice E: Padroes de Commit e Codigo

### E.1 Mensagens de Commit

Para mudancas em codigo criptografico, siga o formato:

```
tipo(escopo): descricao curta

- Detalhe 1
- Detalhe 2

Refs: CVE-XXXX-XXXX (se aplicavel)
```

Exemplos:
```
fix(crypto): corrige timing attack em verificacao de MAC

- Substituiu operator== por sodium_memcmp em verify()
- Adiciona testes de timing para validar constant-time

Refs: CWE-208
```

```
feat(crypto): adiciona suporte a XChaCha20-Poly1305

- Implementa cipher com nonce de 192 bits
- Adiciona testes com vetores do RFC 8439
```

### E.2 Nomes de Variaveis

```cpp
// BOM: Nomes semanticos
std::array<uint8_t, 32> encryption_key;
std::array<uint8_t, 12> initialization_vector;
std::vector<uint8_t> authenticated_ciphertext;
uint64_t message_counter;

// RUIM: Nomes genericos
std::array<uint8_t, 32> key;      // Que tipo de chave?
std::array<uint8_t, 12> iv;       // Para que algoritmo?
std::vector<uint8_t> data;        // Plaintext? Ciphertext?
uint64_t counter;                 // Contador de que?
```

### E.3 Comentarios Obrigatorios

```cpp
// Em operacoes criptograficas, comente:
// 1. POR QUE algo e feito (razao de seguranca)
// 2. O QUE e nao obvio (por que este tamanho? por que este algoritmo?)
// 3. REFERENCIAS a padroes (RFC, NIST SP)

// Exemplo de comentario util:
// Gera nonce de 192 bits para XChaCha20.
// O nonce de 96 bits do ChaCha20 padrao (RFC 8439) e
// insuficiente para alto volume de mensagens por chave.
// XChaCha20 (draft-arciszewski-xchacha20) expande para 192 bits,
// permitindo ~2^96 nonce antes de colisao.
std::array<uint8_t, 24> nonce;
randombytes_buf(nonce.data(), nonce.size());
```

---

> **Nota**: Este capitulo e parte do Livro 5 (Engenharia Criptografica em C++) do projeto DevSecurity. Para exercicios praticos e solucoes, consulte o repositorio do projeto.
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Fundamentos Constant Time](02-fundamentos-constant-time.md)*
