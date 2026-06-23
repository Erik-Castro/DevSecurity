---
layout: default
title: "14-compliance-normas"
---

# Capítulo 14 — Compliance e Normas Criptográficas

> **Livro 5 — Engenharia de Criptografia em C++**
> Projeto DevSecurity

---

## Sumário

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Panorama de compliance criptográfico](#2-panorama-de-compliance-criptográfico)
3. [FIPS 140-3: Módulos criptográficos, CMVP, certificação](#3-fips-140-3)
4. [Common Criteria (CC/ISO 15408): EAL levels](#4-common-criteria)
5. [LGPD (Brasil): Criptografia como medida de proteção](#5-lgpd)
6. [GDPR (Europa): Artigo 32 e criptografia](#6-gdpr)
7. [ICP-Brasil: Certificados digitais, PBI](#7-icp-brasil)
8. [eIDAS: Assinatura eletrônica, selo eletrônico](#8-eidas)
9. [PCI DSS: Requisitos de criptografia para pagamentos](#9-pci-dss)
10. [HIPAA: Criptografia para dados de saúde](#10-hipaa)
11. [CIS Benchmarks: Configurações seguras](#11-cis-benchmarks)
12. [NIST Cybersecurity Framework e criptografia](#12-nist-csf)
13. [Mapeamento: Standards x Algoritmos permitidos](#13-mapeamento)
14. [Tabela comparativa completa de standards](#14-tabela-comparativa)
15. [Implementação de compliance em código C++](#15-implementação-em-código)
16. [Audit preparation checklist](#16-audit-preparation-checklist)
17. [Exercícios](#17-exercícios)
18. [Referências](#18-referências)

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, o engenheiro de software será capaz de:

- Identificar os principais marcos regulatórios e normas técnicas que exigem ou
  recomendam o uso de criptografia em sistemas de software.
- Distinguir entre requisitos obrigatórios (FIPS 140-3, PCI DSS, HIPAA) e
  recomendações de melhores práticas (CIS Benchmarks, NIST CSF).
- Mapear algoritmos criptográficos a cada standard e determinar quais são
  permitidos, proibidos ou descontinuados em cada contexto normativo.
- Implementar controles de compliance criptográfico em código C++ que atendam
  simultaneamente a múltiplos marcos regulatórios.
- Estruturar documentação e evidências para auditorias de compliance.
- Compreender o ciclo de vida de certificação de módulos criptográficos
  (CMVP, Common Criteria) e como eles afetam decisões de arquitetura.
- Avaliar o impacto da LGPD, GDPR, eIDAS e ICP-Brasil em projetos de
  software que processam dados pessoais ou realizam transações digitais.
- Projetar sistemas criptográficos que sejam "compliant by design" em vez
  de "compliant by retrofit".

### 1.1 Por que compliance importa

O compliance criptográfico não é burocracia — é garantia jurídica e técnica de
que o software protege adequadamente os dados sob sua custódia. Um sistema que
viola FIPS 140-3 pode perder contratos governamentais. Um sistema que não atende
LGPD pode gerar multas de até 2% do faturamento. Um sistema que descumpre PCI DSS
pode perder a capacidade de processar pagamentos.

Para o engenheiro de C++, compliance se traduz em:

- **Escolha de algoritmos**: usar AES-256-GCM em vez de RC4, SHA-256 em vez de MD5.
- **Gerenciamento de chaves**: HSMs, key wrapping, rotação periódica.
- **Logging e auditoria**: registrar quem acessou quais dados criptografados e quando.
- **Proteção de memória**: zeroing de chaves em RAM, proteção contra side channels.
- **Validação de implementação**: testes de conformidade, Known Answer Tests (KAT).

### 1.2 Público-alvo

Este capítulo é voltado para engenheiros que:

- Desenvolvem sistemas que processam dados sensíveis (saúde, financeiros, pessoais).
- Trabalham em produtos que vendem para governos ou grandes corporações.
- Precisam demonstrar compliance em auditorias externas.
- Mantêm bibliotecas criptográficas que são consumidas por terceiros.

### 1.3 Pré-requisitos

- Conhecimento dos capítulos anteriores do Livro 5 (algoritmos, key management,
  side channels).
- Familiaridade com C++17 ou superior.
- Noções básicas de direito digital e proteção de dados.

---

## 2. Panorama de compliance criptográfico

### 2.1 O ecossistema normativo

O compliance criptográfico opera em múltiplas camadas, cada uma com escopo,
jurisdição e severidade diferentes:

```
┌─────────────────────────────────────────────────────┐
│              CAMADAS DE COMPLIANCE                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Internacionais          Regionais    Locais        │
│  ┌──────────────┐   ┌────────────┐  ┌───────────┐  │
│  │ FIPS 140-3   │   │ GDPR       │  │ LGPD      │  │
│  │ CC/ISO 15408 │   │ eIDAS      │  │ ICP-Brasil│  │
│  │ NIST CSF     │   │            │  │           │  │
│  │ PCI DSS      │   │            │  │           │  │
│  │ HIPAA        │   │            │  │           │  │
│  │ CIS          │   │            │  │           │  │
│  └──────────────┘   └────────────┘  └───────────┘  │
│                                                     │
│  Setoriais (Industria)                              │
│  ┌──────────────────────────────────────────────┐   │
│  │ SWIFT CSP, FFIEC, SOX, Basel III             │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### 2.2 Classificação dos standards

| Tipo | Exemplos | Natureza | Penalidade de descumprimento |
|------|----------|----------|------------------------------|
| Certificatório | FIPS 140-3, CC | Módulo deve ser certificado | Impossibilidade de venda |
| Regulatório | LGPD, GDPR, HIPAA, PCI DSS | Obrigação legal/setorial | Multas, proibição de operar |
| Diretriz | NIST CSF, CIS Benchmarks | Recomendação de boas práticas | Perda de seguro, reputação |
| Contratual | CLP, SLA com criptografia | Acordo entre partes | Rescisão contratual |

### 2.3 O princípio da defesa em profundidade normativa

Um sistema bem projetado não atende apenas UMA norma. Ele implementa uma
camada de controles que satisfaz múltiplos standards simultaneamente:

```
Requisito Comum: "Dados em trânsito devem ser protegidos"
│
├── FIPS 140-3: TLS 1.2+ com cifras aprovadas (AES-GCM, ECDHE)
├── PCI DSS 4.0: Req 4 — criptografia de dados em trânsito via TLS 1.2+
├── LGPD Art. 46: medidas técnicas adequadas
├── GDPR Art. 32: criptografia como medida de segurança
├── HIPAA: HIPAA Security Rule §164.312(e)(1)
└── CIS Benchmark: TLS 1.2+ habilitado, cifras de alta segurança
```

### 2.4 Ciclo de vida do compliance criptográfico

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  DESIGN  │───>│ IMPL.    │───>│ VALID.   │───>│ AUDITORIA│
│          │    │          │    │          │    │          │
│ Escolha  │    │ Código   │    │ KATs     │    │ Evidências│
│ Algoritmos│    │ Certific.│    │ Testes   │    │ Relatórios│
│ Key Mgmt │    │ Logging  │    │ Pentests │    │ Certidões │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │                                              │
      │         ┌──────────┐    ┌──────────┐         │
      └────────>│ MONITOR. │───>│ REMEDIAÇÃO│<────────┘
                │          │    │          │
                │ Alertas  │    │ Correções│
                │ Anomalias│    │ Rotações │
                └──────────┘    └──────────┘
```

### 2.5 Multijurisdição: um desafio real

Muitos sistemas operam em múltiplos países simultaneamente. O desafio é atender
o stricto sensu de CADA jurisdição:

- **Dados de um paciente brasileiro** processados em servidor nos EUA: LGPD + HIPAA.
- **Pagamento europeu** processado no Brasil: PCI DSS + GDPR + LGPD + eIDAS.
- **Software vendido para governo americano**: FIPS 140-3 é mandatório.
- **Software vendido para governo brasileiro**: ICP-Brasil pode ser exigido.

### 2.6 Algoritmos proibidos e descontinuados

Uma das primeiras verificações de compliance é eliminar algoritmos inseguros:

| Algoritmo | Status | Motivo | Onde é proibido |
|-----------|--------|--------|-----------------|
| MD5 | Proibido | Colisões práticas | FIPS, PCI DSS, NIST |
| SHA-1 | Descontinuado | Colisões demonstradas | FIPS, NIST, Google/Mozilla |
| DES | Proibido | Chave de 56 bits trivial | FIPS, PCI DSS, todos |
| 3DES | Descontinuado (2023) | Sweet32, limite de 64 bits | FIPS, NIST, PCI DSS |
| RC4 | Proibido | Bias estatístico | FIPS, TLS, IETF |
| RSA-1024 | Proibido | Fatoração viável | FIPS, NIST |
| Blowfish | Descontinuado | Bloco de 64 bits | NIST |
| IDEA | Descontinuado | Sem suporte atual | PCI DSS |

---

## 3. FIPS 140-3

### 3.1 Visão geral

O Federal Information Processing Standard (FIPS) 140-3 é o padrão da NIST para
validação de módulos criptográficos. Publicado em 2019 e efetivo desde 2020, ele
substituiu o FIPS 140-2 e introduz requisitos mais rigorosos alinhados com
internacionais (ISO/IEC 19790).

**Quem precisa**: qualquer fornecedor que vende software/hardware criptográfico
para agências federais dos EUA, e indiretamente para qualquer organização que
aceite o padrão como garantia de qualidade.

### 3.2 CMVP: Cryptographic Module Validation Program

O CMVP é o programa que testifica que um módulo criptográfico atende FIPS 140-3.
O processo é:

1. **Desenvolvimento**: implementar o módulo seguindo as diretrizes NIST.
2. **Testes internos**: laboratório interno ou terceiro realiza testes de conformidade.
3. **Submissão ao CMVP**: enviar documentação e código para avaliação.
4. **Laboratório Acreditado (CST)**: laboratório independente (ex: Leidos, Acumen)
   testa o módulo contra os requisitos do standard.
5. **Publicação**: se aprovado, o módulo entra na "Cryptographic Module Validation
   List" (CMVL) do NIST.

### 3.3 Níveis de segurança

FIPS 140-3 define quatro níveis, cada um com requisitos crescentes:

| Nível | Requisitos principais | Exemplo de uso |
|-------|----------------------|----------------|
| 1 | Criptografia básica, autenticação de usuário | Software de uso geral |
| 2 | Tamper-evident coating, login individual | Dispositivos de médio risco |
| 3 | Tamper-resistance, auth multifator, segregação física | HSMs, módulos de alto risco |
| 4 | Completamente envolvido, proteção contra intrusão | Fisicamente inviolável |

### 3.4 Requisitos por área funcional

FIPS 140-3 avalia o módulo em 11 áreas:

**Área 1 — Especificação de criptografia**
- O módulo deve declarar exatamente quais algoritmos implementa.
- Parâmetros de operação (tamanhos de chave, modos de operação) devem ser
  documentados.

**Área 2 — Interfaces do módulo**
- Interfaces de dados, controle, erro e status.
- Entradas e saídas devem ser autenticadas.

**Área 3 — Gerenciamento de chaves**
- Geração, distribuição, armazenamento e destruição de chaves.
- Zeroing seguro de memória após uso.
- Suporte a key wrapping conforme NIST SP 800-57.

**Área 4 — Mechanisms de segurança auto-testados**
- Power-Up Self Test (POST): algoritmos e condicionamento de RNG.
- Conditional Self Test: testes periódicos durante operação.

**Área 5 — Áreas de dados sensíveis**
- Dados sensíveis incluem: chaves secretas, PINs, chaves de antissubstituição.
- Devem ser segregadas de dados não-sensíveis.

**Área 6 — Operação física**
- Controle de acesso físico (para módulos com proteção física).
- Indicações visuais de estado do módulo.

**Área 7 — Segurança operacional**
- Roles e auth de operadores (User, Crypto Officer, Security Officer).
- Procedimentos de setup e shutdown.

**Área 8 — Auto-teste e falha**
- Testes de integridade (integrity tests).
- Testes de algoritmo (algorithm tests com KATs).
- RNG tests (entropy source tests).

**Área 9 — Design aberto**
- Documentação pública do design.
- Análise de vulnerabilidades.

**Área 10 — Mitigações de força física**
- Nível 3+: tampas, switches de intrusão, blindagem.

**Área 11 — Mitigações de ataque de canal lateral**
- Proteção contra SPA, DPA, fault injection.
- Execução constante (constant-time).

### 3.5 Algoritmos aprovados pelo FIPS 140-3

| Algoritmo | Finalidade | Referência NIST |
|-----------|-----------|-----------------|
| AES (128, 192, 256) | Criptografia simétrica | FIPS 197 |
| SHA-224, SHA-256, SHA-384, SHA-512 | Hash | FIPS 180-4 |
| SHA-3 (224, 256, 384, 512) | Hash | FIPS 202 |
| HMAC-SHA-256 | Autenticação | FIPS 198-1 |
| CMAC-AES | Autenticação | SP 800-38B |
| ECDH, ECDSA | Troca/assinatura de chaves | SP 800-56A |
| RSA (2048+) | Assinatura, troca de chaves | SP 800-56B |
| DRBG (HMAC, Hash, CTR) | Geração de números aleatórios | SP 800-90A |
| HKDF | Derivação de chaves | SP 800-56C |
| PBKDF2 | Derivação de chave de senha | SP 800-132 |
| SHAKE (128, 256) | XOF (extendable output) | FIPS 202 |
| CCM, GCM | Modos autenticados | SP 800-38C, SP 800-38D |

### 3.6 Impacto em código C++

Em C++, a escolha de biblioteca criptográfica é crítica para FIPS 140-3:

```cpp
// Opção 1: OpenSSL com provider FIPS
// Precisa de OpenSSL 3.0+ com FIPS provider habilitado
#include <openssl/evp.h>
#include <openssl/provider.h>

bool initialize_fips_provider() {
    OSSL_PROVIDER *fips = OSSL_PROVIDER_load(nullptr, "fips");
    if (!fips) {
        return false;  // FIPS provider não disponível
    }
    // Garantir que o módulo default NÃO seja carregado
    // para forçar uso exclusivo de algoritmos FIPS
    return true;
}

bool fips_aes_encrypt(
    const unsigned char* key, size_t key_len,
    const unsigned char* iv, size_t iv_len,
    const unsigned char* plaintext, size_t pt_len,
    unsigned char* ciphertext, size_t* ct_len,
    unsigned char* tag, size_t tag_len
) {
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return false;

    // AES-256-GCM é aprovado pelo FIPS 140-3
    int ret = EVP_EncryptInit_ex2(
        ctx,
        EVP_aes_256_gcm(),
        nullptr, nullptr, nullptr
    );
    if (!ret) { EVP_CIPHER_CTX_free(ctx); return false; }

    ret = EVP_EncryptInit_ex2(ctx, nullptr, key, iv, nullptr);
    if (!ret) { EVP_CIPHER_CTX_free(ctx); return false; }

    int written = 0;
    ret = EVP_EncryptUpdate(ctx, ciphertext, &written, plaintext, pt_len);
    if (!ret) { EVP_CIPHER_CTX_free(ctx); return false; }

    int final_len = 0;
    ret = EVP_EncryptFinal_ex(ctx, ciphertext + written, &final_len);
    if (!ret) { EVP_CIPHER_CTX_free(ctx); return false; }

    *ct_len = static_cast<size_t>(written + final_len);

    ret = EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, tag_len, tag);
    EVP_CIPHER_CTX_free(ctx);
    return ret == 1;
}

// Opção 2: Usar cryptopp com módulo FIPS-compliant
// Crypto++ tem um módulo FIPS 140-2 validado (Level 1)
// Para FIPS 140-3, usar OpenSSL 3.0+ ou BoringSSL

// Opção 3: Usar platform-specific APIs
// Windows: BCrypt API (Bcrypt.lib) — módulo certificado pelo CMVP
// Linux: pkcs11 com HSM certificado
```

### 3.7 Power-Up Self Test em C++

FIPS 140-3 exige que o módulo realize testes antes de operar:

```cpp
#include <iostream>
#include <vector>
#include <cstring>
#include <functional>

// KAT (Known Answer Test) para AES-256-GCM
struct KATVector {
    std::vector<unsigned char> key;
    std::vector<unsigned char> iv;
    std::vector<unsigned char> plaintext;
    std::vector<unsigned char> expected_ciphertext;
    std::vector<unsigned char> expected_tag;
};

class FIPSModule {
public:
    bool power_up_self_test() {
        // 1. Teste de integridade do módulo
        if (!test_module_integrity()) {
            last_error_ = "Falha no teste de integridade do modulo";
            return false;
        }

        // 2. KAT para AES-256-GCM
        if (!test_aes_256_gcm()) {
            last_error_ = "Falha no KAT de AES-256-GCM";
            return false;
        }

        // 3. KAT para SHA-256
        if (!test_sha256()) {
            last_error_ = "Falha no KAT de SHA-256";
            return false;
        }

        // 4. RNG health test
        if (!test_rng_health()) {
            last_error_ = "Falha no health test do RNG";
            return false;
        }

        // 5. DRBG test
        if (!test_drbg()) {
            last_error_ = "Falha no teste do DRBG";
            return false;
        }

        module_ready_ = true;
        return true;
    }

    const char* last_error() const { return last_error_; }
    bool is_ready() const { return module_ready_; }

private:
    bool module_ready_ = false;
    const char* last_error_ = nullptr;

    bool test_module_integrity() {
        // Verificar hash do código do módulo
        // Comparar com valor armazenado em local seguro
        return true;  // Implementação real requer hash do binário
    }

    bool test_aes_256_gcm() {
        // KAT vetores do NIST CAVP
        KATVector kat;
        kat.key = {
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        };
        kat.iv = {
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00
        };
        kat.plaintext = {};  // plaintext vazio
        kat.expected_ciphertext = {};
        kat.expected_tag = {
            0xCE, 0xA7, 0x37, 0x32, 0x0F, 0x76, 0x5B, 0x1A,
            0xF8, 0xE7, 0x9B, 0x9E, 0xA7, 0xE5, 0x52, 0x5A
        };

        // Executar criptografia com o módulo
        std::vector<unsigned char> computed_ct(kat.plaintext.size());
        std::vector<unsigned char> computed_tag(16);

        bool result = encrypt_aes_256_gcm(
            kat.key.data(), kat.key.size(),
            kat.iv.data(), kat.iv.size(),
            kat.plaintext.data(), kat.plaintext.size(),
            computed_ct.data(), computed_ct.size(),
            computed_tag.data(), computed_tag.size()
        );

        if (!result) return false;
        return computed_tag == kat.expected_tag;
    }

    bool test_sha256() {
        // SHA-256("abc") = ba7816bf8f01cfea414140de5dae2223
        //                   b00361a396177a9cb410ff61f20015ad
        const unsigned char input[] = "abc";
        unsigned char hash[32];

        bool result = compute_sha256(input, 3, hash);
        if (!result) return false;

        const unsigned char expected[] = {
            0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea,
            0x41, 0x41, 0x40, 0xde, 0x5d, 0xae, 0x22, 0x23,
            0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c,
            0xb4, 0x10, 0xff, 0x61, 0xf2, 0x00, 0x15, 0xad
        };

        return std::memcmp(hash, expected, 32) == 0;
    }

    bool test_rng_health() {
        // NIST SP 800-90B: Repetition Count Test
        // Se o mesmo valor é gerado muitas vezes seguidas, o RNG falhou
        std::vector<unsigned char> samples(1024);
        for (auto& s : samples) {
            if (!generate_random(&s, 1)) return false;
        }

        // Contar repetições consecutivas
        int max_repeat = 1;
        int current_repeat = 1;
        for (size_t i = 1; i < samples.size(); ++i) {
            if (samples[i] == samples[i - 1]) {
                current_repeat++;
                if (current_repeat > 10) return false;  // Limite de repetição
                max_repeat = std::max(max_repeat, current_repeat);
            } else {
                current_repeat = 1;
            }
        }
        return true;
    }

    bool test_drbg() {
        // Usar DRBG com seed conhecida, verificar saída
        return true;  // Implementação completa requer NIST SP 800-90A
    }

    // Stub functions (implementadas com biblioteca real)
    bool encrypt_aes_256_gcm(
        const unsigned char*, size_t,
        const unsigned char*, size_t,
        const unsigned char*, size_t,
        unsigned char*, size_t,
        unsigned char*, size_t
    ) { return true; }

    bool compute_sha256(const unsigned char*, size_t, unsigned char*) {
        return true;
    }

    bool generate_random(unsigned char*, size_t) { return true; }
};
```

### 3.8 Constant-time operations

FIPS 140-3 requer mitigação de side channels. Operações criptográficas em
C++ devem ser executadas em tempo constante:

```cpp
#include <cstdint>
#include <cstring>

// Comparações em tempo constante para valores sensíveis
// Evita timing attacks em comparações de MAC, tag, hash

// ABORDAGEM INCORRETA (timing vulnerable):
bool insecure_compare(const unsigned char* a, const unsigned char* b, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        if (a[i] != b[i]) return false;  // Retorna na primeira diferença
    }
    return true;
}

// ABORDAGEM CORRETA (constant-time):
bool constant_time_compare(const unsigned char* a, const unsigned char* b, size_t len) {
    volatile unsigned char diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= a[i] ^ b[i];  // Acumula todas as diferenças
    }
    return diff == 0;  // Sempre percorre todo o buffer
}

// Constant-time selection: seleciona um de dois valores sem branch
// Retorna a se选择 (选择 = c), b caso contrário
uint64_t ct_select(uint64_t select, uint64_t a, uint64_t b) {
    // select é 0 ou 1
    uint64_t mask = static_cast<uint64_t>(-static_cast<int64_t>(select));
    return (a & mask) | (b & ~mask);
}

// Constant-time base64-like encoding para tokens
// Evita que o padrão de padding revele o comprimento real
void ct_pad(unsigned char* buffer, size_t data_len, size_t total_len) {
    // Preenche com padrão consistente, não com zeros óbvios
    unsigned char pad_value = 0xFF;
    for (size_t i = data_len; i < total_len; ++i) {
        buffer[i] = pad_value;
    }
}

// Zeroing seguro de memória em tempo constante
// Compilador NÃO pode otimizar este memset para fora
void secure_zero(void* ptr, size_t len) {
    volatile unsigned char* p = static_cast<volatile unsigned char*>(ptr);
    while (len--) {
        *p++ = 0;
    }
}

// Padrão RAII para garantir zeroing automático
class SecureBuffer {
public:
    explicit SecureBuffer(size_t size) : size_(size) {
        data_ = new unsigned char[size]();
    }

    ~SecureBuffer() {
        secure_zero(data_, size_);
        delete[] data_;
    }

    // Sem cópia (evita dangling pointer com zeroing)
    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;

    // Move é permitido
    SecureBuffer(SecureBuffer&& other) noexcept
        : data_(other.data_), size_(other.size_) {
        other.data_ = nullptr;
        other.size_ = 0;
    }

    unsigned char* data() { return data_; }
    const unsigned char* data() const { return data_; }
    size_t size() const { return size_; }

private:
    unsigned char* data_;
    size_t size_;
};
```

### 3.9 Documentação para CMVP

O processo de submissão ao CMVP requer documentação extensiva:

```
┌─────────────────────────────────────────────────┐
│ PACOTE DE CERTIFICAÇÃO FIPS 140-3               │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. Security Policy Document (SPD)              │
│     - Descrição do módulo                       │
│     - Modos de operação                         │
│     - Interfaces de segurança                   │
│     - Roles e autenticação                      │
│     - Gerenciamento de chaves                   │
│     - Self-tests implementados                  │
│                                                 │
│  2. Finite State Model                          │
│     - Estados do módulo                         │
│     - Transições de estado                      │
│     - Requisitos por estado                     │
│                                                 │
│  3. Module Specification                        │
│     - Especificações funcionais                 │
│     - Algoritmos implementados                  │
│     - Parâmetros de operação                    │
│                                                 │
│  4. Interface Specification                     │
│     - APIs públicas                             │
│     - Parâmetros de entrada/saída               │
│     - Códigos de retorno                        │
│                                                 │
│  5. Operational Environment                     │
│     - SO suportado                              │
│     - Dependências                              │
│     - Configuração mínima                       │
│                                                 │
│  6. Finite State Analysis                       │
│     - Análise formal de estados                 │
│     - Provas de segurança                       │
│                                                 │
│  7. Physical Security (níveis 2-4)              │
│     - Descrição da encapsulação                 │
│     - Mecanismos de tamper                      │
│                                                 │
│  8. Source Code                                 │
│     - Código completo                           │
│     - Makefiles                                 │
│     - Scripts de build                          │
│                                                 │
│  9. Build Procedures                            │
│     - Como compilar o módulo                    │
│     - Dependências verificadas                  │
│                                                 │
│ 10. Test Results                                │
│     - KATs passados                             │
│     - Testes de performance                     │
│     - Testes de integração                      │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 3.10 Transição FIPS 140-2 para 140-3

| Aspecto | FIPS 140-2 | FIPS 140-3 |
|---------|-----------|-----------|
| Publicação | 2001 | 2019 (efetivo 2020) |
| Referência internacional | ISO 19772 | ISO 19790 |
| Automação de testes | Manual | AEM (Automated Entropy Measuring) |
| Testes de RNG | Basic | SP 800-90B (health tests) |
| Side channels | Recomendado | Obrigatório (níveis 3-4) |
| Integração com ISO | Separado | Unificado |
| Algoritmos | Lista fixa | Atualizada dinamicamente |

---

## 4. Common Criteria (CC/ISO 15408)

### 4.1 Visão geral

Common Criteria (CC) é o padrão internacional (ISO/IEC 15408) para avaliação
de segurança de produtos de tecnologia da informação. Diferente do FIPS que
foca em módulos criptográficos, CC avalia o produto COMPLETO.

### 4.2 Evaluation Assurance Levels (EAL)

CC define sete níveis crescentes de garantia de avaliação:

| EAL | Nome | Descrição | Aplicação típica |
|-----|------|-----------|-----------------|
| EAL1 | Functionally tested | Testes básicos de função | Software de baixo risco |
| EAL2 | Structurally tested | Análise de design superficial | Software comercial |
| EAL3 | Methodically tested and checked | Metodologia de teste documentada | Produtos com requerimentos de segurança |
| EAL4 | Methodically designed, tested, and reviewed | Design metódico e revisão | Software de segurança de mercado |
| EAL5 | Semi-formally designed and tested | Análise semi-formal | Sistemas militares |
| EAL6 | Semi-formally verified design and tested | Verificação semi-formal | Sistemas de alta segurança |
| EAL7 | Formally verified design and tested | Verificação formal | Sistemas críticos (aviação, nuclear) |

### 4.3 Protection Profiles (PP) e Security Targets (ST)

- **Protection Profile (PP)**: documento que define requisitos de segurança
  para uma classe de produtos. Ex: PP for firewalls, PP for smart cards.
- **Security Target (ST)**: documento específico do produto que mapeia seus
  mecanismos de segurança para um ou mais PPs.

### 4.4 Componentes de segurança

CC organiza requisitos emClasses, Famílias e Componentes:

```
Classe: Criptografia (FCS)
  ├── Família: Geração de chaves (FCS_CKM)
  │     ├── Componente: Geração de chaves simétricas
  │     │     └── Componente: Geração de chaves assimétricas
  │     └── ...
  ├── Família: Gerenciamento de chaves (FCS_CKM)
  │     ├── Componente: Distribuição de chaves
  │     ├── Componente: Armazenamento de chaves
  │     └── Componente: Destrução de chaves
  ├── Família: Uso de chaves (FCS_COP)
  │     ├── Componente: Uso de chaves simétricas
  │     └── Componente: Uso de chaves assimétricas
  └── Família: Zeroização (FCS_CKM.1.1)
        └── Componente: Eliminação segura de chaves
```

### 4.5 Impacto em arquitetura C++

Para um produto CC-certified, a arquitetura C++ deve demonstrar:

1. **Isolamento de domínio**: separar código de segurança do código de
   aplicação.
2. **Audit trail**: logs imutáveis de operações criptográficas.
3. **Controle de acesso**: RBAC implementado em código.
4. **Teste de conformidade**: suite de testes automatizados documentada.

```cpp
// Exemplo de design para compliance CC EAL4+

// Interface de domínio de segurança
class SecurityDomain {
public:
    virtual ~SecurityDomain() = default;

    // Operações que o domínio permite
    virtual bool encrypt(
        const SecurityLabel& label,
        const void* plaintext, size_t pt_len,
        void* ciphertext, size_t* ct_len
    ) = 0;

    virtual bool decrypt(
        const SecurityLabel& label,
        const void* ciphertext, size_t ct_len,
        void* plaintext, size_t* pt_len
    ) = 0;

    // Controle de acesso
    virtual bool authorize(
        const SecurityIdentity& identity,
        OperationType op
    ) const = 0;

    // Auditoria
    virtual void audit_log(
        const AuditEvent& event
    ) = 0;
};

// Rótulo de segurança para segregação de dados
struct SecurityLabel {
    enum class Classification {
        PUBLIC,
        INTERNAL,
        CONFIDENTIAL,
        SECRET,
        TOP_SECRET
    };

    Classification level;
    std::string compartment;  // Ex: "FINANCE", "HEALTH", "PII"
    uint64_t expiry_timestamp;
};

// Evento de auditoria imutável
struct AuditEvent {
    uint64_t timestamp;
    std::string actor_id;
    OperationType operation;
    std::string target_resource;
    bool success;
    std::string details;
    std::vector<unsigned char> integrity_hash;
};
```

---

## 5. LGPD (Brasil)

### 5.1 Visão geral

A Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018) é o marco
regulatório brasileiro para proteção de dados pessoais. A criptografia é
mencionada como uma das medidas técnicas adequadas para proteção de dados.

### 5.2 Artigos relevantes à criptografia

**Art. 46 — Segurança e sigilo dos dados**

> "Os agentes de tratamento devem adotar medidas de segurança, técnicas e
> administrativas aptas a proteger os dados pessoais de acessos não
> autorizados e de situações acidentais ou ilícitas de destruição, perda,
> alteração, comunicação ou qualquer forma de tratamento inadequado ou
> ilícito."

A criptografia é a principal medida técnica para atender este artigo.

**Art. 47 — Forma de tratamento**

> "Os dados pessoais devem ser tratados de forma a lhes garantir a
> segurança, o sigilo e a integridade, inclusive quanto aos dados armazenados
> em bases de dados que não atendam aos padrões técnicos mínimos."

**Art. 48 — Comunicação de incidentes**

> "O controlador deverá comunicar à autoridade nacional e ao titular a
> ocorrência de incidente de segurança que possa acarretar risco ou dano
> relevante aos titulares."

**Art. 46, §2º (projetos que dependem de regulamentação)**

> "A autoridade nacional poderá dispor sobre padrões técnicos mínimos para
> tornar aplicável o disposto no caput deste artigo, considerados os
> padrões internacionais de segurança da informação."

### 5.3 Criptografia como "medida técnica adequada"

A ANPD (Autoridade Nacional de Proteção de Dados) reconhece criptografia como
medida técnica adequada em múltiplos contextos:

| Dado | Medida criptográfica | Base legal |
|------|---------------------|------------|
| CPF, RG, Passaporte | AES-256 em repouso, TLS 1.2+ em trânsito | Art. 46 |
| Dados de saúde | Criptografia com acesso restrito | Art. 11, II, "f" |
| Dados financeiros | Criptografia ponta-a-ponta | Art. 46 |
| Dados de geolocalização | Criptografia + minimização | Art. 46 |
| Dados biométricos | Criptografia com chave separada | Art. 11, II, "e" |

### 5.4 Impacto em arquitetura C++

```cpp
// Framework de criptografia LGPD-compliant

#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <functional>

enum class DataCategory {
    PERSONAL,        // Dados pessoais (nome, email, CPF)
    SENSITIVE,       // Dados sensíveis (saúde, biometria, religião)
    FINANCIAL,       // Dados financeiros
    MINOR,           // Dados de menores
    ANONYMIZED       // Dados anonimizados (não é LGPD)
};

// Políticas de criptografia por categoria
struct EncryptionPolicy {
    DataCategory category;
    std::string algorithm;           // "AES-256-GCM"
    size_t key_size_bits;            // 256
    std::string key_management;      // "HSM_BACKED"
    size_t key_rotation_days;        // 90
    bool requires_field_level;       // true para dados sensíveis
    std::string transit_protection;  // "TLS_1_3"
    std::string backup_encryption;   // "AES-256-CBC"
};

class LGPDComplianceEngine {
public:
    LGPDComplianceEngine() {
        // Definir políticas por categoria
        policies_[DataCategory::PERSONAL] = {
            .category = DataCategory::PERSONAL,
            .algorithm = "AES-256-GCM",
            .key_size_bits = 256,
            .key_management = "SOFTWARE_KMS",
            .key_rotation_days = 180,
            .requires_field_level = false,
            .transit_protection = "TLS_1_2",
            .backup_encryption = "AES-256-CBC"
        };

        policies_[DataCategory::SENSITIVE] = {
            .category = DataCategory::SENSITIVE,
            .algorithm = "AES-256-GCM",
            .key_size_bits = 256,
            .key_management = "HSM_BACKED",
            .key_rotation_days = 90,
            .requires_field_level = true,
            .transit_protection = "TLS_1_3",
            .backup_encryption = "AES-256-GCM"
        };

        policies_[DataCategory::FINANCIAL] = {
            .category = DataCategory::FINANCIAL,
            .algorithm = "AES-256-GCM",
            .key_size_bits = 256,
            .key_management = "HSM_BACKED",
            .key_rotation_days = 60,
            .requires_field_level = true,
            .transit_protection = "TLS_1_3",
            .backup_encryption = "AES-256-GCM"
        };
    }

    // Encriptografar dados com a política apropriada
    EncryptionResult encrypt(
        const std::vector<unsigned char>& plaintext,
        DataCategory category,
        const std::string& field_name
    ) {
        auto it = policies_.find(category);
        if (it == policies_.end()) {
            return {false, "Categoria de dados desconhecida", {}};
        }

        const auto& policy = it->second;

        // Verificar se a chave está dentro do prazo de validade
        if (is_key_expired(policy)) {
            return {false, "Chave expirada - necessaria rotacao", {}};
        }

        // Registrar acesso para auditoria LGPD
        log_access(field_name, "ENCRYPT", category);

        // Executar criptografia
        EncryptionResult result;
        result.success = perform_encryption(
            plaintext, policy, result.ciphertext, result.metadata
        );

        if (!result.success) {
            result.error = "Falha na criptografia";
        }

        return result;
    }

    // Descriptografar com verificação de autorização
    DecryptionResult decrypt(
        const std::vector<unsigned char>& ciphertext,
        const std::string& field_name,
        const std::string& accessor_id
    ) {
        // Verificar autorização
        if (!is_authorized(accessor_id, field_name)) {
            log_unauthorized_access(accessor_id, field_name);
            return {false, "Acesso nao autorizado", {}};
        }

        // Registrar acesso
        log_access(field_name, "DECRYPT", accessor_id);

        DecryptionResult result;
        result.success = perform_decryption(ciphertext, result.plaintext);
        return result;
    }

    // Verificar se dados atendem políticas LGPD
    ComplianceStatus audit(const std::string& dataset_id) {
        ComplianceStatus status;
        status.dataset_id = dataset_id;

        // 1. Verificar algoritmos em uso
        status.algorithm_issues = check_algorithms();
        if (!status.algorithm_issues.empty()) {
            status.compliant = false;
        }

        // 2. Verificar idades das chaves
        status.key_issues = check_key_ages();
        if (!status.key_issues.empty()) {
            status.compliant = false;
        }

        // 3. Verificar se dados sensíveis têm field-level encryption
        status.field_level_issues = check_field_level_encryption();
        if (!status.field_level_issues.empty()) {
            status.compliant = false;
        }

        // 4. Verificar logs de acesso
        status.audit_log_issues = check_audit_logs();
        if (!status.audit_log_issues.empty()) {
            status.compliant = false;
        }

        // 5. Verificar política de backup
        status.backup_issues = check_backup_encryption();
        if (!status.backup_issues.empty()) {
            status.compliant = false;
        }

        return status;
    }

private:
    std::unordered_map<DataCategory, EncryptionPolicy> policies_;

    struct EncryptionResult {
        bool success = false;
        std::string error;
        std::vector<unsigned char> ciphertext;
        std::unordered_map<std::string, std::string> metadata;
    };

    struct DecryptionResult {
        bool success = false;
        std::string error;
        std::vector<unsigned char> plaintext;
    };

    struct ComplianceStatus {
        std::string dataset_id;
        bool compliant = true;
        std::vector<std::string> algorithm_issues;
        std::vector<std::string> key_issues;
        std::vector<std::string> field_level_issues;
        std::vector<std::string> audit_log_issues;
        std::vector<std::string> backup_issues;
    };

    bool is_key_expired(const EncryptionPolicy& policy) {
        // Implementação real consulta timestamp da última rotação
        return false;
    }

    void log_access(const std::string& field, const std::string& op,
                    const std::string& category) {
        // Registrar em log imutável para auditoria
    }

    void log_unauthorized_access(const std::string& accessor,
                                  const std::string& field) {
        // Alerta de segurança
    }

    bool is_authorized(const std::string& accessor_id,
                       const std::string& field_name) {
        return false;  // Implementação real consulta IAM
    }

    bool perform_encryption(
        const std::vector<unsigned char>&, const EncryptionPolicy&,
        std::vector<unsigned char>&,
        std::unordered_map<std::string, std::string>&
    ) { return true; }

    bool perform_decryption(const std::vector<unsigned char>&,
                            std::vector<unsigned char>&) { return true; }

    std::vector<std::string> check_algorithms() { return {}; }
    std::vector<std::string> check_key_ages() { return {}; }
    std::vector<std::string> check_field_level_encryption() { return {}; }
    std::vector<std::string> check_audit_logs() { return {}; }
    std::vector<std::string> check_backup_encryption() { return {}; }
};
```

### 5.5 Criptografia de dados pessoais sensíveis

Para dados sensíveis sob LGPD (Art. 11), a criptografia deve ser reforçada:

```cpp
// Encriptografia de campo para dados pessoais sensíveis
// Cada dado sensível é criptografado com chave separada

class SensitiveDataVault {
public:
    // Armazenar dado sensível com criptografia de campo
    FieldEncryptedData store_sensitive(
        const std::string& field_type,     // "cpf", "biometric", "health"
        const std::vector<unsigned char>& plaintext,
        const DataSubject& subject        // Titular dos dados
    ) {
        // Gerar chave de campo específica
        SecureBuffer field_key = generate_field_key(field_type);

        // Adicionar metadata ao plaintext
        std::vector<unsigned char> enriched = add_metadata(
            plaintext, field_type, subject.id
        );

        // Encriptografar com AES-256-GCM
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> iv(12);
        std::vector<unsigned char> tag(16);

        generate_random(iv.data(), iv.size());

        bool ok = aes_256_gcm_encrypt(
            field_key.data(), iv.data(),
            enriched.data(), enriched.size(),
            ciphertext, tag
        );

        if (!ok) {
            return {{}, "Falha na criptografia"};
        }

        // Gerar key ID para rastreio
        std::string key_id = compute_key_id(field_key.data(), field_key.size());

        // Registrar para auditoria
        log_field_encryption(field_type, subject.id, key_id);

        return {
            {
                .key_id = key_id,
                .ciphertext = ciphertext,
                .iv = iv,
                .tag = tag,
                .algorithm = "AES-256-GCM",
                .encrypted_at = current_timestamp()
            },
            ""
        };
    }

    // Descriptografar dado sensível
    DecryptedSensitive retrieve_sensitive(
        const FieldEncryptedData& encrypted,
        const std::string& accessor_id,
        const std::string& purpose
    ) {
        // 1. Verificar finalidade (purpose limitation)
        if (!is_purpose_valid(encrypted.key_id, purpose)) {
            return {{}, "Finalidade nao autorizada"};
        }

        // 2. Verificar autorização do accessor
        if (!is_accessor_authorized(accessor_id, encrypted.key_id)) {
            log_unauthorized_retrieval(accessor_id, encrypted.key_id);
            return {{}, "Acesso nao autorizado"};
        }

        // 3. Recuperar chave de campo
        SecureBuffer field_key = retrieve_field_key(encrypted.key_id);
        if (!field_key.data()) {
            return {{}, "Chave nao encontrada"};
        }

        // 4. Descriptografar
        std::vector<unsigned char> plaintext;
        bool ok = aes_256_gcm_decrypt(
            field_key.data(), encrypted.iv.data(),
            encrypted.ciphertext.data(), encrypted.ciphertext.size(),
            encrypted.tag.data(),
            plaintext
        );

        if (!ok) {
            return {{}, "Descriptografia falhou"};
        }

        // 5. Verificar e remover metadata
        auto [data, meta] = extract_metadata(plaintext);

        // 6. Log de acesso
        log_field_access(encrypted.key_id, accessor_id, purpose, "DECRYPT");

        return {{data, meta}, ""};
    }

private:
    struct FieldEncryptedData {
        std::string key_id;
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> iv;
        std::vector<unsigned char> tag;
        std::string algorithm;
        uint64_t encrypted_at;
    };

    struct DecryptedSensitive {
        std::vector<unsigned char> data;
        std::unordered_map<std::string, std::string> metadata;
    };

    struct DataSubject {
        std::string id;
    };

    SecureBuffer generate_field_key(const std::string& field_type) {
        return SecureBuffer(32);  // 256 bits
    }

    std::string compute_key_id(const unsigned char*, size_t) {
        return "key_001";
    }

    uint64_t current_timestamp() {
        return static_cast<uint64_t>(
            std::chrono::system_clock::now().time_since_epoch().count()
        );
    }

    void generate_random(unsigned char* buf, size_t len) {}
    bool aes_256_gcm_encrypt(
        const unsigned char*, const unsigned char*,
        const unsigned char*, size_t,
        std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) { return true; }

    bool aes_256_gcm_decrypt(
        const unsigned char*, const unsigned char*,
        const unsigned char*, size_t,
        const unsigned char*,
        std::vector<unsigned char>&
    ) { return true; }

    std::vector<unsigned char> add_metadata(
        const std::vector<unsigned char>& d, const std::string& t,
        const std::string& id
    ) { return d; }

    std::pair<std::vector<unsigned char>, std::unordered_map<std::string, std::string>>
    extract_metadata(const std::vector<unsigned char>& d) {
        return {d, {}};
    }

    bool is_purpose_valid(const std::string&, const std::string&) { return true; }
    bool is_accessor_authorized(const std::string&, const std::string&) { return true; }
    SecureBuffer retrieve_field_key(const std::string&) { return SecureBuffer(32); }
    void log_field_encryption(const std::string&, const std::string&, const std::string&) {}
    void log_field_access(const std::string&, const std::string&, const std::string&, const std::string&) {}
    void log_unauthorized_retrieval(const std::string&, const std::string&) {}
};
```

### 5.6 LGPD vs. GDPR: semelhanças e diferenças

| Aspecto | LGPD | GDPR |
|---------|------|------|
| Jurisdição | Brasil | União Europeia |
| Autoridade | ANPD | DPO + autoridades nacionais |
| Consentimento | Base legal, pode ser dispensado | Base legal, pode ser dispensado |
| Criptografia | Medida técnica adequada | Medida de segurança apropriada |
| Notificação de incidente | "Risco ou dano relevante" | "Risco alto para direitos" |
| Prazo de notificação | "Sem prejuízo" (sem prazo fixo) | 72 horas |
| DPO | Obrigatório para controlador público | Obrigatório em certos casos |
| Multas | Até 2% (teto R$ 50M/benefício) | Até 4% ou EUR 20M |
| Transferência internacional | Adequação ou std contratuais | Adequação ou std contratuais |

---

## 6. GDPR (Europa)

### 6.1 Artigo 32 — Segurança do tratamento

O Artigo 32 do GDPR é a seção central que trata de medidas técnicas de
segurança, incluindo criptografia:

> "O responsável pelo tratamento e o operador devem implementar medidas
> técnicas e organizacionais adequadas ao nível de risco, incluindo entre
> outras, conforme aplicável:
>
> a) a pseudonimização e a criptografia de dados pessoais;
>
> b) a capacidade de garantir a confidencialidade, integridade, disponibilidade
> e resiliência constantes dos sistemas e serviços de tratamento;
>
> c) a capacidade de restaurar a disponibilidade e o acesso aos dados
> pessoais em tempo oportuno em caso de incidente físico ou técnico;
>
> d) um processo para testar, avaliar e medir regularmente a eficácia das
> medidas técnicas e organizacionais."

### 6.2 Criptografia como "state of the art"

O GDPR usa o conceito de "state of the art" — as medidas devem refletir o
melhor disponível na data de implementação. Isso significa:

- **Em 2024+**: AES-256-GCM é state of the art para simétrica.
- **Em 2024+**: RSA-2048+ ou ECC (P-256, P-384) para assimétrica.
- **Em 2024+**: TLS 1.3 é state of the art para transmissão.
- **Em 2024+**: ChaCha20-Poly1305 é alternativa aceitável.

### 6.3 Direito ao esquecimento e criptografia

O Artigo 17 (direito ao apagamento) interage com criptografia:

```cpp
// Implementação de "crypto-shredding" para GDPR Art. 17
// Em vez de apagar dados, destruir a chave de criptografia

class CryptoShreddingService {
public:
    // Cada titular de dados tem uma chave dedicada
    struct DataKeyBundle {
        std::string subject_id;
        SecureBuffer encryption_key;
        std::string key_version;
        uint64_t created_at;
        bool destroyed = false;
    };

    // Criptografar dados vinculados a um titular
    EncryptedRecord encrypt_for_subject(
        const std::string& subject_id,
        const std::vector<unsigned char>& data,
        const std::string& purpose
    ) {
        // Obter ou criar chave para este titular
        DataKeyBundle key = get_or_create_key(subject_id);

        // Encriptografar dados
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> iv(12);
        std::vector<unsigned char> tag(16);

        bool ok = aes_gcm_encrypt(
            key.encryption_key.data(), iv.data(),
            data.data(), data.size(),
            ciphertext, tag
        );

        return {
            .subject_id = subject_id,
            .key_version = key.key_version,
            .ciphertext = ciphertext,
            .iv = iv,
            .tag = tag,
            .purpose = purpose,
            .encrypted_at = now()
        };
    }

    // "Apagar" dados destruindo a chave (crypto-shredding)
    // Em vez de sobrescrever dados em disco (lento e não garantido
    // em SSDs), destruir a chave torna os dados irrecuperáveis
    ShredResult shred_subject_data(const std::string& subject_id) {
        // 1. Localizar todas as chaves do titular
        auto keys = find_keys_for_subject(subject_id);
        if (keys.empty()) {
            return {false, "Nenhuma chave encontrada"};
        }

        // 2. Marcar chaves como destruídas
        for (auto& key : keys) {
            key.destroyed = true;
            secure_zero(key.encryption_key.data(),
                       key.encryption_key.size());
            log_key_destruction(key.subject_id, key.key_version);
        }

        // 3. Atualizar registro de destruição
        update_destruction_log(subject_id, keys.size());

        // 4. Os dados criptografados permanecem no disco
        // mas são IRRECUPERÁVEIS sem as chaves
        // Em SSDs com TRIM, os blocos eventualmente
        // serão liberados pelo controlador

        return {true, std::to_string(keys.size()) + " chaves destruidas"};
    }

    // Verificar se dados de um titular foram "apagados"
    bool verify_subject_deleted(const std::string& subject_id) {
        auto keys = find_keys_for_subject(subject_id);
        for (const auto& key : keys) {
            if (!key.destroyed) return false;
        }
        return true;
    }

private:
    struct EncryptedRecord {
        std::string subject_id;
        std::string key_version;
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> iv;
        std::vector<unsigned char> tag;
        std::string purpose;
        uint64_t encrypted_at;
    };

    struct ShredResult {
        bool success;
        std::string details;
    };

    DataKeyBundle get_or_create_key(const std::string& subject_id) {
        return {subject_id, SecureBuffer(32), "v1", now(), false};
    }

    std::vector<DataKeyBundle> find_keys_for_subject(const std::string&) {
        return {};
    }

    bool aes_gcm_encrypt(
        const unsigned char*, const unsigned char*,
        const unsigned char*, size_t,
        std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) { return true; }

    uint64_t now() {
        return static_cast<uint64_t>(
            std::chrono::system_clock::now().time_since_epoch().count()
        );
    }

    void secure_zero(unsigned char* ptr, size_t len) {
        volatile unsigned char* p = ptr;
        while (len--) *p++ = 0;
    }

    void log_key_destruction(const std::string&, const std::string&) {}
    void update_destruction_log(const std::string&, size_t) {}
};
```

### 6.4 Transferência internacional e criptografia

GDPR restringe transferências de dados para fora do EEA. Criptografia pode
facilitar a conformidade:

```cpp
// Padrão para transferência internacional de dados GDPR-compliant
// Dados são encriptografados ANTES da transferência
// Chave fica no EEA (Key Management Outside Transfer)

struct CrossBorderTransfer {
    std::string transfer_id;
    std::string source_jurisdiction;      // "EU"
    std::string destination_jurisdiction;  // "BR", "US", etc.
    std::string legal_basis;              // "SCCs", "adequacy", "BCR"
    std::string encryption_algorithm;     // "AES-256-GCM"
    bool key_in_eu = true;
    uint64_t transfer_timestamp;
    bool data_encrypted_at_rest = true;
    bool data_encrypted_in_transit = true;
};

class CrossBorderTransferManager {
public:
    TransferResult initiate_transfer(
        const std::vector<unsigned char>& data,
        const std::string& destination,
        const std::string& legal_basis
    ) {
        // 1. Verificar se há base legal adequada
        if (!has_valid_legal_basis(destination, legal_basis)) {
            return {false, "Base legal insuficiente para transferencia"};
        }

        // 2. Encriptografar dados com chave gerada no EEA
        std::vector<unsigned char> encrypted_data;
        SecureBuffer transfer_key(32);
        generate_transfer_key(transfer_key);

        bool ok = encrypt_for_transfer(
            data, transfer_key, encrypted_data
        );

        if (!ok) {
            return {false, "Falha na criptografia para transferencia"};
        }

        // 3. Criptografar a chave de transferência
        // (envelope encryption)
        std::vector<unsigned char> wrapped_key;
        wrap_key_for_destination(
            transfer_key, destination, wrapped_key
        );

        // 4. Registrar transferência
        CrossBorderTransfer record;
        record.transfer_id = generate_id();
        record.destination_jurisdiction = destination;
        record.legal_basis = legal_basis;
        record.encryption_algorithm = "AES-256-GCM";
        record.key_in_eu = true;
        record.transfer_timestamp = now();

        log_transfer(record);

        return {
            true,
            "Transferencia preparada: " + record.transfer_id
        };
    }

private:
    struct TransferResult {
        bool success;
        std::string details;
    };

    bool has_valid_legal_basis(const std::string&, const std::string&) {
        return true;
    }

    void generate_transfer_key(SecureBuffer& key) {}
    bool encrypt_for_transfer(
        const std::vector<unsigned char>&, SecureBuffer&,
        std::vector<unsigned char>&
    ) { return true; }

    void wrap_key_for_destination(
        SecureBuffer&, const std::string&,
        std::vector<unsigned char>&
    ) {}

    std::string generate_id() { return "transfer_001"; }
    uint64_t now() {
        return static_cast<uint64_t>(
            std::chrono::system_clock::now().time_since_epoch().count()
        );
    }

    void log_transfer(const CrossBorderTransfer&) {}
};
```

### 6.5 Data Protection Impact Assessment (DPIA)

O Artigo 35 do GDPR exige DPIA para tratamentos de alto risco. A criptografia
é um controle que reduz o risco avaliado:

```
┌──────────────────────────────────────────────────────────┐
│ DPIA SIMPLIFICADA — Criptografia como Controle           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  DESCRICAO DO TRATAMENTO                                 │
│  - Dados: CPF, email, historico medico                   │
│  - Finalidade: prestacao de servico de saude             │
│  - Base legal: Art. 11, II, "f" (saude)                 │
│                                                          │
│  RISCOS IDENTIFICADOS                                    │
│  ┌────────────────────┬──────────┬──────────┐            │
│  │ Risco              │ Impacto  │ Control  │            │
│  ├────────────────────┼──────────┼──────────┤            │
│  │ Vazamento de dados │ Alto     │ Cript.   │            │
│  │ Acesso nao autoriz.│ Alto     │ Cript.   │            │
│  │ Perda de dados     │ Medio    │ Backup   │            │
│  │ Transferencia ilic.│ Alto     │ TLS+E2E  │            │
│  └────────────────────┴──────────┴──────────┘            │
│                                                          │
│  MEDIDAS DE MITIGACAO                                    │
│  - AES-256-GCM para dados em repouso                     │
│  - TLS 1.3 para dados em transito                        │
│  - Field-level encryption para dados sensiveis           │
│  - HSM para gerenciamento de chaves                      │
│  - Crypto-shredding para direito ao esquecimento         │
│  - Key rotation a cada 90 dias                           │
│  - Logging de todos os acessos                           │
│                                                          │
│  RISCO RESIDUAL                                          │
│  Com as medias acima, o risco residual e avaliado        │
│  como BAIXO, aceitavel para o tratamento proposto.       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 7. ICP-Brasil

### 7.1 Visão geral

A Infraestrutura de Chaves Públicas Brasileira (ICP-Brasil) é o sistema
nacional de certificação digital, gerenciado pelo ITI (Instituto Nacional de
Tecnologia da Informação). É uma PKI hierárquica com raiz de confiança
governamental.

### 7.2 Hierarquia da ICP-Brasil

```
                    ┌─────────────────┐
                    │   AC Raiz       │
                    │   ICP-Brasil    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────┴───┐  ┌──────┴──────┐  ┌───┴────────┐
     │ AC S       │  │ AC A1       │  │ AC G4      │
     │ (Sede)     │  │ (Apenas     │  │ (Geral     │
     │            │  │  Assinatura)│  │  Nivel 4)  │
     └────────┬───┘  └──────┬──────┘  └───┬────────┘
              │              │              │
     ┌────────┴────────┐    │         ┌────┴────────┐
     │                 │    │         │             │
  ┌──┴───────┐  ┌─────┴──┐ │    ┌────┴───┐  ┌─────┴──┐
  │ AC A1    │  │ AC A3  │ │    │ AC G4  │  │ AC G4  │
  │ (Sede)   │  │ (4a.)  │ │    │ (Sub)  │  │ (Sub)  │
  └──┬───────┘  └───┬────┘ │    └────┬───┘  └────┬───┘
     │              │       │         │           │
  ┌──┴───┐     ┌───┴──┐    │      ┌──┴──┐    ┌──┴──┐
  │ e-   │     │ e-   │    │      │ e-  │    │ e-  │
  │CPF   │     │CNPJ  │    │      │CPF  │    │CNPJ │
  └──────┘     └──────┘    │      └─────┘    └─────┘
                           │
                    ┌──────┴──────┐
                    │  Selo       │
                    │  tempo      │
                    └─────────────┘
```

### 7.3 Tipos de certificado

| Tipo | Finalidade | Algoritmo | Validade |
|------|-----------|-----------|----------|
| e-CPF A1 | Assinatura de pessoa física | RSA 2048 / ECC P-256 | 1 ano |
| e-CPF A3 | Assinatura (smartcard/token) | RSA 2048-4096 / ECC | Até 3 anos |
| e-CNPJ A1 | Assinatura de pessoa jurídica | RSA 2048 | 1 ano |
| e-CNPJ A3 | Assinatura de pessoa jurídica | RSA 2048-4096 | Até 3 anos |
| e-CPF e-CNPJ A3 | Assinatura + criptografia | RSA 2048-4096 | Até 3 anos |
| AC Sede | Certificados de instituição | RSA 2048-4096 | Até 5 anos |
| Selo de Tempo | Comprovação de tempo | RSA 2048 | Variável |

### 7.4 Padrão de Bibliotecas (PBI)

O PBI define bibliotecas de assinatura digital para padronizar o uso de
certificados ICP-Brasil em softwares:

```cpp
// Padrão de Bibliotecas de Assinatura (PBI)
// Interface para uso de certificados ICP-Brasil em C++

#include <string>
#include <vector>
#include <functional>

// Estrutura representando um certificado ICP-Brasil
struct ICPCertificate {
    std::string subject_name;         // CN do titular
    std::string issuer_name;          // AC emissor
    std::string serial_number;        // Número de série
    std::string valid_from;           // Data de início (ISO 8601)
    std::string valid_to;             // Data de término
    std::string cpf_cnpj;             // CPF ou CNPJ do titular
    std::string policy_oid;           // OID da política de certificação
    std::string public_key_algorithm; // "RSA" ou "ECDSA"
    int key_size_bits;                // Tamanho da chave pública
    std::vector<unsigned char> thumbprint;  // SHA-256 do certificado
};

// Interface PBI para assinatura
class PBISignature {
public:
    virtual ~PBISignature() = default;

    // Carregar certificado do repositório do sistema
    virtual bool load_certificate(
        const std::string& cpf_cnpj,
        const std::string& pin
    ) = 0;

    // Assinar dados (CMS/PKCS#7)
    virtual std::vector<unsigned char> sign(
        const std::vector<unsigned char>& data,
        bool detached = false
    ) = 0;

    // Verificar assinatura
    virtual bool verify(
        const std::vector<unsigned char>& data,
        const std::vector<unsigned char>& signature,
        ICPCertificate& signer_cert
    ) = 0;

    // Obter informações do certificado carregado
    virtual ICPCertificate get_certificate_info() const = 0;

    // Obter CRL para revogação
    virtual bool check_revocation() = 0;

    // Selo de tempo
    virtual std::vector<unsigned char> timestamp(
        const std::vector<unsigned char>& data
    ) = 0;
};

// Implementação concreta (exemplo simplificado)
class PBISignatureImpl : public PBISignature {
public:
    bool load_certificate(
        const std::string& cpf_cnpj,
        const std::string& pin
    ) override {
        // 1. Buscar certificado no repositório do sistema
        // Windows: cert store (MY)
        // Linux: NSS ou diretório ICP-Brasil

        // 2. Validar PIN do token/smartcard (A3)
        if (!validate_pin(pin)) {
            return false;
        }

        // 3. Carregar chave privada
        if (!load_private_key(cpf_cnpj, pin)) {
            return false;
        }

        // 4. Verificar cadeia de certificação
        if (!verify_certificate_chain()) {
            return false;
        }

        // 5. Verificar revogação (CRL/OCSP)
        if (check_revocation()) {
            last_error_ = "Certificado revogado";
            return false;
        }

        cert_loaded_ = true;
        return true;
    }

    std::vector<unsigned char> sign(
        const std::vector<unsigned char>& data,
        bool detached = false
    ) override {
        if (!cert_loaded_) {
            return {};  // Erro: certificado não carregado
        }

        // 1. Calcular hash dos dados
        std::vector<unsigned char> hash = compute_sha256(data);

        // 2. Assinar o hash com a chave privada
        std::vector<unsigned char> signature = sign_hash(hash);

        // 3. Embalar em CMS/PKCS#7
        std::vector<unsigned char> cms = build_cms(
            data, signature, detached
        );

        // 4. Registrar assinatura para auditoria
        log_signature(certificate_info_.serial_number, data.size());

        return cms;
    }

    bool verify(
        const std::vector<unsigned char>& data,
        const std::vector<unsigned char>& signature,
        ICPCertificate& signer_cert
    ) override {
        // 1. Parse CMS/PKCS#7
        auto parsed = parse_cms(signature);
        if (!parsed.valid) return false;

        // 2. Extrair certificado do signatário
        signer_cert = parsed.signer_certificate;

        // 3. Verificar cadeia até a AC Raiz ICP-Brasil
        if (!verify_chain_to_root(signer_cert)) {
            return false;
        }

        // 4. Verificar revogação
        if (is_revoked(signer_cert.serial_number)) {
            return false;
        }

        // 5. Verificar assinatura
        return verify_signature(
            data, parsed.hash, parsed.signature_value
        );
    }

    ICPCertificate get_certificate_info() const override {
        return certificate_info_;
    }

    bool check_revocation() override {
        // Consultar CRL da AC emissor
        // Ou consultar OCSP responder
        return false;  // false = não revogado
    }

    std::vector<unsigned char> timestamp(
        const std::vector<unsigned char>& data
    ) override {
        // Requerer selo de tempo do ICP-Brasil (TSA)
        // O selo prova que os dados existiam em determinado momento
        // e que a assinatura era válida naquela data
        return {};
    }

private:
    bool cert_loaded_ = false;
    ICPCertificate certificate_info_;
    std::string last_error_;

    bool validate_pin(const std::string&) { return true; }
    bool load_private_key(const std::string&, const std::string&) { return true; }
    bool verify_certificate_chain() { return true; }
    std::vector<unsigned char> compute_sha256(
        const std::vector<unsigned char>&
    ) { return {}; }

    std::vector<unsigned char> sign_hash(
        const std::vector<unsigned char>&
    ) { return {}; }

    std::vector<unsigned char> build_cms(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&, bool
    ) { return {}; }

    struct ParsedCMS {
        bool valid = false;
        ICPCertificate signer_certificate;
        std::vector<unsigned char> hash;
        std::vector<unsigned char> signature_value;
    };

    ParsedCMS parse_cms(const std::vector<unsigned char>&) { return {}; }
    bool verify_chain_to_root(const ICPCertificate&) { return true; }
    bool is_revoked(const std::string&) { return false; }
    bool verify_signature(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&
    ) { return true; }

    void log_signature(const std::string&, size_t) {}
};
```

### 7.5 Requisitos técnicos ICP-Brasil

| Componente | Requisito | Referência |
|-----------|-----------|-----------|
| Chave simétrica | AES-128+ ou 3DES (legado) | ICP-04.001 |
| Chave assimétrica | RSA 2048+ ou ECC P-256/P-384 | ICP-04.001 |
| Hash | SHA-256+ | ICP-04.001 |
| Assinatura | RSA PKCS#1 v1.5 ou PSS, ECDSA | ICP-04.002 |
| Transporte | TLS 1.2+ com cifras ICP | ICP-04.004 |
| Protocolo OCSP | IETF RFC 6960 | ICP-04.001 |
| Protocolo CRL | IETF RFC 5280 | ICP-04.001 |
| Selo de tempo | RFC 3161 / ICP-04.005 | ICP-04.005 |

---

## 8. eIDAS

### 8.1 Visão geral

eIDAS (Electronic Identification, Authentication and Trust Services) é o
regulamento europeu (UE Nº 910/2014) que estabelece o quadro para serviços
de confiança na União Europeia. Ele reconhece assinaturas eletrônicas,
selos eletrônicos e carimbos temporais como legalmente equivalentes a
assinaturas manuscritas.

### 8.2 Níveis de assinatura eletrônica

| Nível | Descrição | Valor jurídico | Requisitos |
|-------|-----------|---------------|-----------|
| Simples (eIDAS) | Dados eletrônicos anexados ou associados | Não pode ser recusado por ser eletrônico | Qualquer método |
| Avançada (QES) | Identificação exclusiva do signatário | Equivalente a assinatura manuscrita | Certificado qualificado + dispositivo seguro |
| Qualificada (Seal) | Selo de pessoa jurídica | Presumido autêntico | Certificado qualificado |

### 8.3 Selo eletrônico qualificado

```cpp
// Implementação de selo eletrônico qualificado (eIDAS)
// Usado por entidades jurídicas para autenticar documentos

class QualifiedElectronicSeal {
public:
    // Criar selo eletrônico qualificado
    SealResult create_seal(
        const std::vector<unsigned char>& document,
        const std::string& legal_entity_id
    ) {
        // 1. Verificar certificado qualificado
        if (!has_valid_qualified_certificate(legal_entity_id)) {
            return {false, "Certificado qualificado nao encontrado"};
        }

        // 2. Hash do documento
        std::vector<unsigned char> doc_hash = hash_document(document);

        // 3. Assinar o hash com chave do certificado
        std::vector<unsigned char> seal_signature =
            sign_with_qualified_key(doc_hash, legal_entity_id);

        // 4. Embalar em estrutura CAdES (CMS Advanced Electronic Signatures)
        std::vector<unsigned char> cades_seal = build_cades(
            document, seal_signature, legal_entity_id
        );

        // 5. Adicionar carimbo temporal qualificado (TSA)
        std::vector<unsigned char> timestamp_token =
            request_qualified_timestamp(cades_seal);

        // 6. Construir selo final
        std::vector<unsigned char> final_seal =
            build_qualified_seal(cades_seal, timestamp_token);

        // 7. Registrar para auditoria
        log_seal_creation(legal_entity_id, document.size());

        return {
            true,
            "Selo criado com sucesso",
            final_seal
        };
    }

    // Verificar selo eletrônico qualificado
    VerificationResult verify_seal(
        const std::vector<unsigned char>& document,
        const std::vector<unsigned char>& seal
    ) {
        VerificationResult result;

        // 1. Parse da estrutura CAdES
        auto parsed = parse_cades_seal(seal);
        if (!parsed.valid) {
            result.status = "INVALID";
            result.detail = "Estrutura CAdES invalida";
            return result;
        }

        // 2. Verificar cadeia de certificação
        if (!verify_qualified_certificate_chain(parsed.signer_cert)) {
            result.status = "INVALID";
            result.detail = "Cadeia de certificacao invalida";
            return result;
        }

        // 3. Verificar se certificado é qualificado
        if (!is_qualified_certificate(parsed.signer_cert)) {
            result.status = "ADVANCED_NOT_QUALIFIED";
            result.detail = "Certificado nao e qualificado";
            return result;
        }

        // 4. Verificar revogação
        if (is_certificate_revoked(parsed.signer_cert)) {
            result.status = "INVALID";
            result.detail = "Certificado revogado";
            return result;
        }

        // 5. Verificar assinatura
        if (!verify_signature_value(
                parsed.document_hash, parsed.signature)) {
            result.status = "INVALID";
            result.detail = "Assinatura invalida";
            return result;
        }

        // 6. Verificar integridade do documento
        std::vector<unsigned char> current_hash = hash_document(document);
        if (current_hash != parsed.document_hash) {
            result.status = "INVALID";
            result.detail = "Documento foi alterado apos selagem";
            return result;
        }

        // 7. Verificar carimbo temporal
        if (!verify_timestamp(parsed.timestamp_token)) {
            result.status = "VALID_NO_TIMESTAMP";
            result.detail = "Selo valido, mas sem carimbo temporal";
            return result;
        }

        result.status = "QUALIFIED_VALID";
        result.detail = "Selo eletronico qualificado VALIDO";
        result.signer_info = parsed.signer_info;
        result.timestamp = parsed.timestamp_value;

        return result;
    }

private:
    struct SealResult {
        bool success;
        std::string message;
        std::vector<unsigned char> seal_data;
    };

    struct VerificationResult {
        std::string status;
        std::string detail;
        std::string signer_info;
        std::string timestamp;
    };

    struct ParsedSeal {
        bool valid = false;
        ICPCertificate signer_cert;
        std::vector<unsigned char> document_hash;
        std::vector<unsigned char> signature;
        std::vector<unsigned char> timestamp_token;
        std::string signer_info;
        std::string timestamp_value;
    };

    bool has_valid_qualified_certificate(const std::string&) { return true; }
    std::vector<unsigned char> hash_document(
        const std::vector<unsigned char>&
    ) { return {}; }

    std::vector<unsigned char> sign_with_qualified_key(
        const std::vector<unsigned char>&, const std::string&
    ) { return {}; }

    std::vector<unsigned char> build_cades(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&,
        const std::string&
    ) { return {}; }

    std::vector<unsigned char> request_qualified_timestamp(
        const std::vector<unsigned char>&
    ) { return {}; }

    std::vector<unsigned char> build_qualified_seal(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&
    ) { return {}; }

    ParsedSeal parse_cades_seal(const std::vector<unsigned char>&) { return {}; }
    bool verify_qualified_certificate_chain(const ICPCertificate&) { return true; }
    bool is_qualified_certificate(const ICPCertificate&) { return true; }
    bool is_certificate_revoked(const ICPCertificate&) { return false; }
    bool verify_signature_value(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&
    ) { return true; }

    bool verify_timestamp(const std::vector<unsigned char>&) { return true; }
    void log_seal_creation(const std::string&, size_t) {}
};
```

### 8.4 eIDAS e ICP-Brasil

A partir de 2023, o ICP-Brasil foi reconhecido como equivalente aos padrões
eIDAS pela Comissão Europeia. Isso significa:

- Assinaturas com certificados ICP-Brasil tipo A3 são reconhecidas na UE.
- A verificação cruzada requer mapeamento de OIDs de política.
- Selo temporal ICP-Brasil é reconhecido como TSA qualificado.

### 8.5 Algoritmos eIDAS

| Uso | Algoritmo permitido | Nível mínimo |
|-----|-------------------|--------------|
| Assinatura | RSA 2048+, ECDSA P-256+ | Qualificado |
| Hash | SHA-256+ | Qualificado |
| Criptografia | AES-128+ | Transporte |
| TLS | TLS 1.2+ com ECDHE | Qualificado |
| Carimbo temporal | RFC 3161 | Qualificado |

---

## 9. PCI DSS

### 9.1 Visão geral

PCI DSS (Payment Card Industry Data Security Standard) é o padrão de segurança
para organizações que processam, armazenam ou transmitem dados de cartões de
crédito. Versão 4.0 (2022) com implementação obrigatória a partir de março de 2025.

### 9.2 Requisitos de criptografia no PCI DSS 4.0

PCI DSS 4.0 define 12 requisitos. Os diretamente ligados a criptografia:

| Requisito | Descrição | Criptografia envolvida |
|-----------|-----------|----------------------|
| Req 3 | Proteger dados de conta armazenados | AES-256, key management |
| Req 4 | Proteger dados em trânsito em redes abertas | TLS 1.2+ |
| Req 8 | Autenticar acesso ao sistema | Cryptographic tokens |
| Req 10 | Rastrear e monitorar acesso | Integrity hashing |
| Req 12.3 | Análise de risco incluindo criptografia | Crypto assessment |

### 9.3 Requisito 3 — Dados armazenados

```cpp
// PCI DSS Req 3: Proteção de dados de conta armazenados

// Regras PCI DSS 4.0 para dados armazenados:
// - NUNCA armazenar dados de autenticação (CVV, PIN) após autorização
// - Dados de conta (PAN) devem ser criptografados com algoritmo forte
// - Chaves de criptografia devem ser gerenciadas de forma segura
// - Usar key-splitting ou key-management system

class PCIStorageEncryption {
public:
    // Regras de quais dados podem ser armazenados
    enum class StoredDataRule {
        NEVER_STORE,           // CVV, PIN, dados de autenticação
        ENCRYPT_IF_NEEDED,     // PAN (número do cartão)
        MAY_STORE_MASKED,      // Últimos 4 dígitos, sem criptografia
        TOKEN_ALLOWED,         // Substituição por token
        HASH_ALLOWED           // Hash unidirecional (sem reversão)
    };

    // Determinar regra para um tipo de dado
    StoredDataRule get_storage_rule(const std::string& data_type) {
        if (data_type == "CVV" || data_type == "CVV2" ||
            data_type == "CVC" || data_type == "PIN") {
            return StoredDataRule::NEVER_STORE;
        }
        if (data_type == "PAN" || data_type == "TRACK_DATA") {
            return StoredDataRule::ENCRYPT_IF_NEEDED;
        }
        if (data_type == "PAN_MASKED" || data_type == "LAST_4") {
            return StoredDataRule::MAY_STORE_MASKED;
        }
        if (data_type == "ACCOUNT_TOKEN") {
            return StoredDataRule::TOKEN_ALLOWED;
        }
        return StoredDataRule::HASH_ALLOWED;
    }

    // Armazenar PAN com criptografia PCI DSS-compliant
    StorageResult store_pan(
        const std::string& pan,
        const StorageEncryptionKey& key
    ) {
        // 1. Validar formato do PAN
        if (!validate_pan_format(pan)) {
            return {false, "Formato de PAN invalido"};
        }

        // 2. Verificar regra de armazenamento
        StoredDataRule rule = get_storage_rule("PAN");
        if (rule != StoredDataRule::ENCRYPT_IF_NEEDED) {
            return {false, "Regra de armazenamento nao permite"};
        }

        // 3. NUNCA armazenar dados de autenticação
        // (seria verificado nos dados de entrada)

        // 4. Encriptografar PAN com AES-256-GCM
        std::vector<unsigned char> pan_bytes(pan.begin(), pan.end());
        std::vector<unsigned char> encrypted_pan;
        std::vector<unsigned char> iv(12);
        std::vector<unsigned char> tag(16);

        generate_random(iv.data(), iv.size());

        bool ok = aes_256_gcm_encrypt(
            key.data(), iv.data(),
            pan_bytes.data(), pan_bytes.size(),
            encrypted_pan, tag
        );

        if (!ok) {
            return {false, "Falha na criptografia"};
        }

        // 5. Armazenar dados criptografados + IV + tag
        EncryptedPANRecord record;
        record.encrypted_pan = encrypted_pan;
        record.iv = iv;
        record.tag = tag;
        record.key_id = key.id();
        record.encrypted_at = now();
        record.algorithm = "AES-256-GCM";

        // 6. Log de auditoria PCI DSS
        log_storage_event("PAN_ENCRYPTED", key.id());

        return {true, "PAN armazenado com criptografia"};
    }

    // Descriptografar PAN apenas para uso autorizado
    DecryptionResult decrypt_pan(
        const EncryptedPANRecord& record,
        const StorageEncryptionKey& key,
        const std::string& purpose
    ) {
        // 1. Verificar se finalização é permitida
        if (!is_pan_access_allowed(purpose)) {
            return {false, "Acesso ao PAN nao autorizado"};
        }

        // 2. Descriptografar
        std::vector<unsigned char> decrypted;
        bool ok = aes_256_gcm_decrypt(
            key.data(), record.iv.data(),
            record.encrypted_pan.data(), record.encrypted_pan.size(),
            record.tag.data(),
            decrypted
        );

        if (!ok) {
            return {false, "Falha na descriptografia"};
        }

        // 3. Log de auditoria
        log_storage_event("PAN_DECRYPTED", purpose);

        return {
            true,
            std::string(decrypted.begin(), decrypted.end())
        };
    }

private:
    struct StorageResult {
        bool success;
        std::string message;
    };

    struct DecryptionResult {
        bool success;
        std::string message;
    };

    struct EncryptedPANRecord {
        std::vector<unsigned char> encrypted_pan;
        std::vector<unsigned char> iv;
        std::vector<unsigned char> tag;
        std::string key_id;
        uint64_t encrypted_at;
        std::string algorithm;
    };

    struct StorageEncryptionKey {
        virtual ~StorageEncryptionKey() = default;
        virtual const unsigned char* data() const = 0;
        virtual std::string id() const = 0;
    };

    bool validate_pan_format(const std::string& pan) {
        if (pan.size() < 13 || pan.size() > 19) return false;
        for (char c : pan) {
            if (!std::isdigit(c)) return false;
        }
        return luhn_check(pan);
    }

    bool luhn_check(const std::string& pan) {
        int sum = 0;
        bool alternate = false;
        for (int i = static_cast<int>(pan.size()) - 1; i >= 0; --i) {
            int n = pan[i] - '0';
            if (alternate) {
                n *= 2;
                if (n > 9) n -= 9;
            }
            sum += n;
            alternate = !alternate;
        }
        return sum % 10 == 0;
    }

    void generate_random(unsigned char*, size_t) {}
    bool aes_256_gcm_encrypt(
        const unsigned char*, const unsigned char*,
        const unsigned char*, size_t,
        std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) { return true; }

    bool aes_256_gcm_decrypt(
        const unsigned char*, const unsigned char*,
        const unsigned char*, size_t,
        const unsigned char*,
        std::vector<unsigned char>&
    ) { return true; }

    bool is_pan_access_allowed(const std::string&) { return true; }
    uint64_t now() {
        return static_cast<uint64_t>(
            std::chrono::system_clock::now().time_since_epoch().count()
        );
    }

    void log_storage_event(const std::string&, const std::string&) {}
};
```

### 9.4 Requisito 4 — Dados em trânsito

```cpp
// PCI DSS Req 4: Criptografia de dados em trânsito

// Requisitos:
// - TLS 1.2 ou superior para todas as transmissões de dados de conta
// - Certificados devem ser válidos e confiáveis
// - Protocolos e cifras inseguros devem ser desabilitados

struct TLSPolicyPCI {
    // Mínimo TLS 1.2
    int min_tls_version = 12;  // TLS 1.2

    // Cifras permitidas (PCI DSS 4.0)
    std::vector<std::string> allowed_ciphers = {
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES128-GCM-SHA256"
    };

    // Cifras PROIBIDAS (PCI DSS 4.0)
    std::vector<std::string> prohibited_ciphers = {
        "RC4", "DES", "3DES", "MD5",
        "NULL", "EXPORT", "anon"
    };

    // Requisitos de certificate
    bool require_valid_certificate = true;
    bool require_private_key_2048_plus = true;
    bool check_certificate_transparency = true;
    bool require_ocsp_stapling = true;

    // Configuração OpenSSL
    std::string get_openssl_cipher_string() const {
        return "ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!RC4:!DES:!3DES";
    }
};

// Configuração TLS para servidor PCI DSS-compliant
// /etc/nginx/conf.d/ssl-params.conf (referência)
// 
// ssl_protocols TLSv1.2 TLSv1.3;
// ssl_ciphers ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!RC4:!DES:!3DES;
// ssl_prefer_server_ciphers on;
// ssl_session_timeout 1d;
// ssl_session_cache shared:PCI_SSL:10m;
// ssl_stapling on;
// ssl_stapling_verify on;
// ssl_certificate /path/to/cert.pem;
// ssl_certificate_key /path/to/key.pem;

// Em C++, configurar o contexto TLS:
#include <openssl/ssl.h>
#include <openssl/err.h>

class PCICompliantTLS {
public:
    bool configure_server_context(SSL_CTX* ctx) {
        // 1. Forçar TLS 1.2+
        SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

        // 2. Configurar cifras PCI DSS-compliant
        const char* cipher_list =
            "ECDHE+AESGCM:ECDHE+CHACHA20:!aNULL:!MD5:!RC4:!DES:!3DES";

        if (SSL_CTX_set_cipher_list(ctx, cipher_list) != 1) {
            return false;
        }

        // 3. Habilitar OCSP stapling
        SSL_CTX_set_tlsext_status_type(ctx, TLSEXT_STATUSTYPE_ocsp);

        // 4. Configurar session resumption com limite
        SSL_CTX_set_session_cache_mode(
            ctx, SSL_SESS_CACHE_SERVER | SSL_SESS_CACHE_NO_INTERNAL
        );
        SSL_CTX_sess_set_cache_size(ctx, 10000);

        // 5. Configurar curves
        SSL_CTX_set1_curves_list(ctx, "P-256:P-384:X25519");

        // 6. Habilitar ALPN para HTTP/2
        const unsigned char alpn[] = {2, 'h', '2'};
        SSL_CTX_set_alpn_protos(ctx, alpn, sizeof(alpn));

        return true;
    }

    bool configure_client_context(SSL_CTX* ctx) {
        // Cliente também deve forçar TLS 1.2+
        SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

        // Verificar certificado do servidor
        SSL_CTX_set_verify(
            ctx,
            SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
            nullptr
        );

        // Carregar certificados CA confiáveis
        if (SSL_CTX_load_verify_locations(
                ctx, "/etc/ssl/certs/ca-certificates.crt", nullptr
            ) != 1) {
            return false;
        }

        return true;
    }

private:
    SSL_CTX* create_context() {
        const SSL_METHOD* method = TLS_server_method();
        return SSL_CTX_new(method);
    }
};
```

### 9.5 PCI DSS 4.0: mudanças em criptografia

| Aspecto | PCI DSS 3.2.1 | PCI DSS 4.0 |
|---------|--------------|-------------|
| TLS mínimo | TLS 1.2 | TLS 1.2 (mantido) |
| TLS 1.3 | Não mencionado | Suportado e recomendado |
| MFA | Exigido para acessos administrativos | Exigido para todos os acessos ao CDE |
| Criptografia de chaves | Obrigatório | Obrigatório + key lifecycle |
| Tokenização | Alternativa à criptografia | Alternativa, mas com requisitos adicionais |
| Algoritmos | Não especifica | Especifica algoritmos aprovados |
| Testes | Anual | Contínuo (novas exigências) |

---

## 10. HIPAA

### 10.1 Visão geral

HIPAA (Health Insurance Portability and Accountability Act) é a lei americana
de 1996 que protege dados de saúde (PHI - Protected Health Information).
O Security Rule (§164.302-318) exige medidas técnicas para proteção de PHI.

### 10.2 Requisitos relevantes

| Seção | Requisito | Criptografia |
|-------|-----------|-------------|
| §164.312(a)(2)(iv) | Criptografia e decriptografia de ePHI | Obrigatória para ePHI |
| §164.312(e)(1) | Proteção de ePHI em trânsito | Criptografia de transmissão |
| §164.312(e)(2)(ii) | Criptografia de ePHI em trânsito | Mecanismo de criptografia |
| §164.312(c)(1) | Integridade de ePHI | Controles de integridade |
| §164.312(d) | Autenticação de pessoas/entidades | Controles de autenticação |

### 10.3 ePHI e criptografia

ePHI (electronic Protected Health Information) inclui qualquer informação
de saúde que seja eletronicamente armazenada ou transmitida:

```cpp
// Framework de criptografia HIPAA-compliant para dados de saúde

class HIPAAEncryptionFramework {
public:
    // Verificar se um dado é ePHI
    bool is_ePHI(const std::string& data_type) {
        // PHI inclui:
        // - Identificadores pessoais (nome, SSN, data de nascimento)
        // - Informações de saúde (diagnósticos, tratamentos)
        // - Números de seguro saúde
        // - Dados biométricos
        // - Fotos faciais identificáveis

        static const std::vector<std::string> phi_types = {
            "patient_name", "ssn", "date_of_birth",
            "medical_record_number", "diagnosis",
            "treatment", "medication", "insurance_id",
            "biometric", "facial_photo", "genetic_data"
        };

        for (const auto& phi_type : phi_types) {
            if (data_type.find(phi_type) != std::string::npos) {
                return true;
            }
        }
        return false;
    }

    // Criptografar ePHI para armazenamento
    StorageResult encrypt_ePHI_for_storage(
        const std::vector<unsigned char>& ephi_data,
        const std::string& data_type,
        const HSMKey& encryption_key
    ) {
        // 1. Verificar se é ePHI
        if (!is_ePHI(data_type)) {
            return {false, "Dado nao e ePHI"};
        }

        // 2. Usar AES-256-GCM (NIST aprovado)
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> iv(12);
        std::vector<unsigned char> tag(16);

        generate_random(iv.data(), iv.size());

        bool ok = encrypt_aes_gcm(
            encryption_key, iv.data(),
            ephi_data.data(), ephi_data.size(),
            ciphertext, tag
        );

        if (!ok) {
            return {false, "Falha na criptografia"};
        }

        // 3. Verificar se criptografia é "adequada" (§164.312(a)(2)(iv))
        // NIST reconhece: AES-128+ é adequada
        if (ephi_data.size() > 0 && ciphertext.size() == 0) {
            return {false, "Criptografia inadequada"};
        }

        // 4. Registrar em log de auditoria HIPAA
        log_ePHI_access(data_type, "ENCRYPT", "STORAGE");

        return {true, "ePHI encriptografado para armazenamento"};
    }

    // Criptografar ePHI para transmissão
    TransmissionResult encrypt_ePHI_for_transmission(
        const std::vector<unsigned char>& ephi_data,
        const std::string& data_type,
        const std::string& destination
    ) {
        if (!is_ePHI(data_type)) {
            return {false, "Dado nao e ePHI"};
        }

        // HIPAA §164.312(e)(1): mecanismo de criptografia
        // para ePHI transmitido pela rede
        //
        // Opções aceitas:
        // - TLS 1.2+ (para comunicação client-server)
        // - IPsec (para VPN)
        // - Criptografia ponta-a-ponta (para email)
        // - SFTP/SCP (para transferência de arquivos)

        TransmissionConfig config;
        config.protocol = select_transmission_protocol(destination);
        config.min_tls_version = "1.2";
        config.cipher_preference = "AES-256-GCM";

        if (!validate_transmission_config(config)) {
            return {false, "Configuracao de transmissao invalida"};
        }

        log_ePHI_access(data_type, "ENCRYPT", "TRANSMISSION");

        return {true, "ePHI pronto para transmissao segura"};
    }

    // Verificar conformidade HIPAA
    ComplianceCheckResult verify_hipaa_compliance(
        const std::string& dataset_id
    ) {
        ComplianceCheckResult result;
        result.dataset_id = dataset_id;

        // 1. Verificar se todos os ePHI estão criptografados
        result.encryption_status = check_encryption_status(dataset_id);

        // 2. Verificar algoritmos em uso
        result.algorithm_check = check_algorithms();

        // 3. Verificar gerenciamento de chaves
        result.key_management = check_key_management();

        // 4. Verificar logs de auditoria
        result.audit_logs = check_audit_logs();

        // 5. Verificar política de retenção
        result.retention_policy = check_retention_policy();

        // HIPAA exige "reasonable and appropriate" measures
        result.compliant =
            result.encryption_status.compliant &&
            result.algorithm_check.compliant &&
            result.key_management.compliant;

        return result;
    }

private:
    struct StorageResult {
        bool success;
        std::string message;
    };

    struct TransmissionResult {
        bool success;
        std::string message;
    };

    struct TransmissionConfig {
        std::string protocol;
        std::string min_tls_version;
        std::string cipher_preference;
    };

    struct ComplianceStatus {
        bool compliant = true;
        std::vector<std::string> issues;
    };

    struct ComplianceCheckResult {
        std::string dataset_id;
        bool compliant = true;
        ComplianceStatus encryption_status;
        ComplianceStatus algorithm_check;
        ComplianceStatus key_management;
        ComplianceStatus audit_logs;
        ComplianceStatus retention_policy;
    };

    struct HSMKey {
        virtual const unsigned char* data() const = 0;
        virtual size_t size() const = 0;
    };

    void generate_random(unsigned char*, size_t) {}
    bool encrypt_aes_gcm(
        const HSMKey&, const unsigned char*,
        const unsigned char*, size_t,
        std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) { return true; }

    std::string select_transmission_protocol(const std::string&) {
        return "TLS_1_2";
    }

    bool validate_transmission_config(const TransmissionConfig&) {
        return true;
    }

    void log_ePHI_access(const std::string&, const std::string&,
                          const std::string&) {}

    ComplianceStatus check_encryption_status(const std::string&) { return {}; }
    ComplianceStatus check_algorithms() { return {}; }
    ComplianceStatus check_key_management() { return {}; }
    ComplianceStatus check_audit_logs() { return {}; }
    ComplianceStatus check_retention_policy() { return {}; }
};
```

### 10.4 HIPAA Safe Harbor

O §164.532(c)(2) oferece "Safe Harbor" para dados de saúde criptografados:
se os dados são criptografados de acordo com NIST standards, eles NÃO são
considerados PHI para fins de notificação de violação.

Isso significa que AES-256-GCM (NIST aprovado) fornece Safe Harbor, enquanto
algoritmos proprietários ou obsoletos NÃO fornecem.

---

## 11. CIS Benchmarks

### 11.1 Visão geral

CIS (Center for Internet Security) Benchmarks são diretrizes de configuração
segura para sistemas operacionais, softwares e dispositivos de rede. Eles
incluem configurações específicas de criptografia.

### 11.2 Configurações de criptografia CIS

| Sistema | Configuração CIS | Valor recomendado |
|---------|-----------------|-------------------|
| Linux | TLS protocolo mínimo | TLS 1.2+ |
| Linux | Cipher suites | TLS_AES_256_GCM_SHA384, ECDHE+AESGCM |
| OpenSSL | Versão mínima | 3.0+ |
| Docker | TLS para daemon | TLS 1.2+ com certificados |
| MySQL | Criptografia em repouso | AES-256 |
| PostgreSQL | Criptografia de conexão | SSL/TLS 1.2+ |
| Nginx | SSL configuração | TLS 1.2+, ECDHE+AESGCM |
| Apache | SSL configuração | TLS 1.2+, ECDHE+AESGCM |
| SSH | Protocolo | SSHv2, Ed25519/RSA 4096 |
| Windows | CredSSP | NLA obrigatório |

### 11.3 Verificação automatizada

```cpp
// Verificador de conformidade CIS Benchmarks para criptografia

class CISBenchmarkChecker {
public:
    struct CheckResult {
        std::string check_id;
        std::string description;
        bool compliant;
        std::string current_value;
        std::string recommended_value;
        std::string remediation;
    };

    std::vector<CheckResult> run_cryptographic_checks() {
        std::vector<CheckResult> results;

        // CIS-1: Versão mínima TLS
        results.push_back(check_tls_version());

        // CIS-2: Cipher suites
        results.push_back(check_cipher_suites());

        // CIS-3: Certificados
        results.push_back(check_certificate_validity());

        // CIS-4: Chaves SSH
        results.push_back(check_ssh_key_strength());

        // CIS-5: Criptografia de disco
        results.push_back(check_disk_encryption());

        // CIS-6: Gerenciamento de chaves
        results.push_back(check_key_management());

        return results;
    }

private:
    CheckResult check_tls_version() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-001";
        result.description = "TLS minimo deve ser 1.2";
        result.recommended_value = "TLS 1.2 ou superior";

        // Verificar configuração TLS do sistema
        int min_version = get_system_tls_version();
        result.current_value = "TLS " + std::to_string(min_version / 10) + "."
                              + std::to_string(min_version % 10);

        result.compliant = (min_version >= 12);
        result.remediation = "Configurar TLS 1.2+ no servidor";

        return result;
    }

    CheckResult check_cipher_suites() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-002";
        result.description = "Cipher suites devem ser seguras";
        result.recommended_value = "ECDHE+AESGCM, CHACHA20";

        auto ciphers = get_enabled_ciphers();

        // Verificar se há cifras proibidas
        std::vector<std::string> prohibited = {
            "RC4", "DES", "3DES", "NULL", "EXPORT", "MD5"
        };

        bool has_prohibited = false;
        for (const auto& cipher : ciphers) {
            for (const auto& p : prohibited) {
                if (cipher.find(p) != std::string::npos) {
                    has_prohibited = true;
                    break;
                }
            }
        }

        result.compliant = !has_prohibited;
        result.current_value = has_prohibited ? "Cifras proibidas detectadas" : "OK";
        result.remediation = "Remover cifras RC4, DES, 3DES, NULL, EXPORT";

        return result;
    }

    CheckResult check_certificate_validity() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-003";
        result.description = "Certificados devem ser validos e nao expirados";

        // Verificar certificado do servidor
        auto cert_info = get_server_certificate_info();
        bool valid = !cert_info.expired && cert_info.key_size >= 2048;

        result.compliant = valid;
        result.current_value = valid ? "Valido" : "Invalido ou expirado";
        result.recommended_value = "Certificado valido com chave 2048+";
        result.remediation = "Renovar certificado com chave RSA 2048+ ou ECC P-256+";

        return result;
    }

    CheckResult check_ssh_key_strength() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-004";
        result.description = "Chaves SSH devem ter pelo menos 4096 bits (RSA) ou 256 bits (Ed25519)";

        auto ssh_config = get_ssh_config();
        bool strong_keys = ssh_config.min_key_size >= 4096 ||
                          ssh_config.allow_ed25519;

        result.compliant = strong_keys;
        result.current_value = "Min key: " + std::to_string(ssh_config.min_key_size);
        result.recommended_value = "RSA 4096+ ou Ed25519";
        result.remediation = "Configurar HostKeyMinimumKeySize e desabilitar RSA < 4096";

        return result;
    }

    CheckResult check_disk_encryption() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-005";
        result.description = "Disco deve ter criptografia habilitada (LUKS/dm-crypt)";

        bool encrypted = is_disk_encrypted("/");

        result.compliant = encrypted;
        result.current_value = encrypted ? "Criptografado" : "Nao criptografado";
        result.recommended_value = "LUKS2 com AES-256-XTS";
        result.remediation = "Habilitar LUKS2 no volume raiz";

        return result;
    }

    CheckResult check_key_management() {
        CheckResult result;
        result.check_id = "CIS-CRYPTO-006";
        result.description = "Chaves devem ser gerenciadas adequadamente";

        bool ok = verify_key_management_practices();
        result.compliant = ok;
        result.current_value = ok ? "Conforme" : "Nao conforme";
        result.recommended_value = "Key rotation, HSM, access control";
        result.remediation = "Implementar key management com rotação periodica";

        return result;
    }

    // Stub functions
    int get_system_tls_version() { return 12; }
    std::vector<std::string> get_enabled_ciphers() {
        return {"TLS_AES_256_GCM_SHA384", "ECDHE-RSA-AES256-GCM-SHA384"};
    }

    struct CertificateInfo {
        bool expired = false;
        int key_size = 2048;
    };

    CertificateInfo get_server_certificate_info() { return {}; }

    struct SSHConfig {
        int min_key_size = 4096;
        bool allow_ed25519 = true;
    };

    SSHConfig get_ssh_config() { return {}; }
    bool is_disk_encrypted(const std::string&) { return true; }
    bool verify_key_management_practices() { return true; }
};
```

---

## 12. NIST Cybersecurity Framework e criptografia

### 12.1 Visão geral

O NIST Cybersecurity Framework (CSF) é um framework voluntary para gerenciar
risgos de cibersegurança. Versão 2.0 (2024) expande o escopo para além de
infraestrutura crítica.

### 12.2 Funções do CSF e criptografia

| Função | Subfunção | Relevância criptográfica |
|--------|-----------|------------------------|
| GOVERN (GV) | GV.OC-07 | Identificar requisitos legais de criptografia |
| GOVERN (GV) | GV.RR-06 | Política de criptografia organizacional |
| IDENTIFY (ID) | ID.AM-05 | Inventariar recursos criptográficos |
| PROTECT (PR) | PR.DS-01 | Criptografia de dados em repouso |
| PROTECT (PR) | PR.DS-02 | Criptografia de dados em trânsito |
| PROTECT (PR) | PR.AA-01 | Gerenciamento de identidade e acesso |
| PROTECT (PR) | PR.AA-03 | Autenticação multifator com criptografia |
| DETECT (DE) | DE.CM-09 | Monitoramento de uso de criptografia |
| RESPOND (RS) | RS.AN-06 | Resposta a incidentes de criptografia |
| RECOVER (RC) | RC.RP-01 | Recuperação de chaves e dados |

### 12.3 Implementação CSF 2.0 em C++

```cpp
// Implementação de controles CSF 2.0 para criptografia

class CSFCryptographyControls {
public:
    // PROTECT: PR.DS-01 — Criptografia em repouso
    struct AtRestPolicy {
        std::string algorithm = "AES-256-GCM";
        std::string key_management = "HSM_or_KMS";
        int key_rotation_days = 90;
        bool field_level_for_pii = true;
        bool field_level_for_phi = true;
        bool field_level_for_pci = true;
    };

    // PROTECT: PR.DS-02 — Criptografia em trânsito
    struct InTransitPolicy {
        std::string min_tls_version = "1.2";
        bool require_mutual_tls = false;
        std::string cipher_suites = "ECDHE+AESGCM:ECDHE+CHACHA20";
        bool certificate_pinning = true;
        bool ocsp_stapling = true;
    };

    // GOVERN: GV.RR-06 — Política organizacional
    struct CryptoGovernancePolicy {
        std::string policy_version = "2.0";
        std::string approved_algorithms[5] = {
            "AES-256-GCM", "AES-128-GCM",
            "ChaCha20-Poly1305",
            "SHA-256", "SHA-384"
        };
        std::string prohibited_algorithms[5] = {
            "MD5", "SHA-1", "DES", "3DES", "RC4"
        };
        bool require_key_rotation = true;
        bool require_audit_logging = true;
        bool require_incident_response_plan = true;
    };

    // Avaliação de maturidade CSF para criptografia
    struct MaturityAssessment {
        int govern_level = 0;      // 0-4 (Partial, Risk Informed, Repeatable, Adaptive)
        int protect_level = 0;
        int detect_level = 0;
        int respond_level = 0;
        int recover_level = 0;

        int overall_score() const {
            return (govern_level + protect_level + detect_level +
                    respond_level + recover_level) / 5;
        }

        std::string maturity_label() const {
            int score = overall_score();
            if (score == 0) return "Nenhum";
            if (score == 1) return "Parcial";
            if (score == 2) return "Informado por Risco";
            if (score == 3) return "Repetivel";
            if (score == 4) return "Adaptativo";
            return "Desconhecido";
        }
    };

    // Executar avaliação de maturidade
    MaturityAssessment assess_maturity() {
        MaturityAssessment assessment;

        // GOVERN
        assessment.govern_level = assess_govern_maturity();

        // PROTECT
        assessment.protect_level = assess_protect_maturity();

        // DETECT
        assessment.detect_level = assess_detect_maturity();

        // RESPOND
        assessment.respond_level = assess_respond_maturity();

        // RECOVER
        assessment.recover_level = assess_recover_maturity();

        return assessment;
    }

private:
    int assess_govern_maturity() {
        // Nível 0: Sem política formal
        // Nível 1: Política existe mas inconsistente
        // Nível 2: Política documentada e comunicada
        // Nível 3: Política revisada regularmente e automatizada
        // Nível 4: Política adaptativa baseada em ameaças
        return 2;
    }

    int assess_protect_maturity() {
        return 2;
    }

    int assess_detect_maturity() {
        return 1;
    }

    int assess_respond_maturity() {
        return 1;
    }

    int assess_recover_maturity() {
        return 1;
    }
};
```

### 12.4 NIST SP 800-57: Recomendações de Key Management

O NIST SP 800-57 é a referência para gerenciamento de chaves criptográficas:

| Parâmetro | Recomendação |
|-----------|-------------|
| Chave simétrica (confidencialidade) | AES-128+ (recomendado: AES-256) |
| Chave simétrica (integridade) | HMAC-SHA-256+ |
| Chave assimétrica (assinatura) | RSA 2048+ ou ECC P-256+ |
| Chave assimétrica (troca) | ECDH P-256+ ou X25519 |
| Derivação de chaves | HKDF-SHA-256+ ou SP 800-108 |
| Rotação de chaves | Conforme política organizacional |
| Validade de chave | Máximo 2 anos (recomendado) |
| Destruction | Zeroing + verificação |

---

## 13. Mapeamento: Standards x Algoritmos permitidos

### 13.1 Tabela de mapeamento algoritmo-standard

```
┌──────────────────┬───────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ Algoritmo        │ FIPS  │ CC   │ PCI  │ HIPAA│ LGPD │ GDPR │ NIST │
│                  │ 140-3 │      │ DSS  │      │      │      │ CSF  │
├──────────────────┼───────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ AES-256-GCM      │  OK   │  OK  │  OK  │  OK  │ Rec. │ Rec. │ Rec. │
│ AES-128-GCM      │  OK   │  OK  │  OK  │  OK  │ Rec. │ Rec. │ Rec. │
│ AES-256-CBC      │  OK   │  OK  │  OK  │  OK  │ Rec. │ Rec. │ Rec. │
│ ChaCha20-Poly    │  -    │  -   │  -   │  -   │  -   │  -   │ Rec. │
│ RSA-2048         │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ RSA-4096         │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ ECDSA P-256      │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ Ed25519          │  -    │  -   │  -   │  -   │  -   │  -   │ Rec. │
│ X25519           │  -    │  -   │  -   │  -   │  -   │  -   │ Rec. │
│ SHA-256          │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ SHA-384          │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ SHA-3-256        │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ HMAC-SHA-256     │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ HKDF-SHA-256     │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ PBKDF2           │  OK   │  OK  │  OK  │  OK  │ OK   │ OK   │ Rec. │
│ scrypt           │  -    │  -   │  -   │  -   │ OK   │ OK   │  -   │
│ Argon2           │  -    │  -   │  -   │  -   │ OK   │ OK   │  -   │
│ MD5              │  PRO  │  PRO │  PRO │  PRO │  -   │  -   │  -   │
│ SHA-1            │  PRO  │  PRO │  PRO │  PRO │  -   │  -   │  -   │
│ DES              │  PRO  │  PRO │  PRO │  PRO │  -   │  -   │  -   │
│ 3DES             │  PRO  │  DES │  PRO │  DES │  -   │  -   │  -   │
│ RC4              │  PRO  │  PRO │  PRO │  PRO │  -   │  -   │  -   │
│ Blowfish         │  PRO  │  DES │  DES │  DES │  -   │  -   │  -   │
└──────────────────┴───────┴──────┴──────┴──────┴──────┴──────┴──────┘

Legenda: OK = Aprovado, Rec. = Recomendado, PRO = Proibido,
         DES = Descontinuado, - = Não mencionado
```

### 13.2 Matriz de decisões

```
DADO A SER PROTEGIDO → QUAL STANDARD SE APLICA?
│
├── Número de cartão (PAN)
│   └── PCI DSS Req 3 + 4
│       └── Algoritmo: AES-256-GCM
│
├── CPF / RG / Passaporte
│   └── LGPD Art. 46 + GDPR Art. 32
│       └── Algoritmo: AES-256-GCM
│
├── Diagnóstico médico (PHI)
│   └── HIPAA §164.312 + LGPD Art. 11
│       └── Algoritmo: AES-256-GCM + field-level
│
├── Dados biométricos
│   └── LGPD Art. 11 + GDPR Art. 9
│       └── Algoritmo: AES-256-GCM + HSM
│
├── Documento assinado digitalmente
│   └── ICP-Brasil + eIDAS
│       └── Algoritmo: RSA 2048+ ou ECDSA P-256+
│
├── Software para governo (EUA)
│   └── FIPS 140-3 (obrigatório)
│       └── Módulo deve ser certificado CMVP
│
├── Software de alta segurança
│   └── Common Criteria EAL4+ (recomendado)
│       └── Design documentado e verificado
│
└── Qualquer dado em rede
    └── CIS Benchmarks + NIST CSF + TLS 1.2+
        └── ECDHE+AESGCM
```

### 13.3 Algoritmos futuros: PQC (Post-Quantum Cryptography)

O NIST finalizou os primeiros padrões PQC em 2024:

| Algoritmo | Tipo | Uso | Status NIST |
|-----------|------|-----|-------------|
| ML-KEM (CRYSTALS-Kyber) | KEM | Troca de chaves | FIPS 203 |
| ML-DSA (CRYSTALS-Dilithium) | Assinatura | Assinatura digital | FIPS 204 |
| SLH-DSA (SPHINCS+) | Assinatura | Assinatura hash-based | FIPS 205 |
| FN-DSA (FALCON) | Assinatura | Assinatura compacta | Em revisão |

Impacto em compliance:

- **Curto prazo (2024-2026)**: híbridos (clássico + PQC) são recomendados.
- **Médio prazo (2027-2030)**: PQC tornará obrigatório em novas certificações.
- **FIPS 140-3**: atualizações incluirão PQC em breve.

```cpp
// Exemplo de suporte híbrido clássico + PQC

class HybridKeyExchange {
public:
    // Troca de chaves híbrida: ECDH + ML-KEM
    struct HybridKeyPair {
        // Clássico
        std::vector<unsigned char> ecdh_private;
        std::vector<unsigned char> ecdh_public;

        // PQC (ML-KEM-768)
        std::vector<unsigned char> mlkem_private;
        std::vector<unsigned char> mlkem_public;
    };

    struct HybridSharedSecret {
        std::vector<unsigned char> ecdh_shared;
        std::vector<unsigned char> mlkem_shared;
        std::vector<unsigned char> combined;  // Concatenar e derivar
    };

    HybridKeyPair generate_hybrid_keypair() {
        HybridKeyPair kp;

        // Gerar par ECDH (P-256)
        generate_ecdh_keypair(kp.ecdh_private, kp.ecdh_public);

        // Gerar par ML-KEM-768
        generate_mlkem_keypair(kp.mlkem_private, kp.mlkem_public);

        return kp;
    }

    HybridSharedSecret compute_hybrid_shared(
        const HybridKeyPair& local,
        const std::vector<unsigned char>& remote_ecdh,
        const std::vector<unsigned char>& remote_mlkem
    ) {
        HybridSharedSecret secret;

        // ECDH shared
        compute_ecdh_shared(local.ecdh_private, remote_ecdh, secret.ecdh_shared);

        // ML-KEM decapsulate
        mlkem_decapsulate(local.mlkem_private, remote_mlkem, secret.mlkem_shared);

        // Combinar: HKDF(ECDH_shared || MLKEM_shared)
        std::vector<unsigned char> combined_input;
        combined_input.insert(combined_input.end(),
                              secret.ecdh_shared.begin(), secret.ecdh_shared.end());
        combined_input.insert(combined_input.end(),
                              secret.mlkem_shared.begin(), secret.mlkem_shared.end());

        hkdf_sha256(combined_input, "hybrid-key-exchange", 32, secret.combined);

        // Zeroing intermediários
        secure_zero(secret.ecdh_shared.data(), secret.ecdh_shared.size());
        secure_zero(secret.mlkem_shared.data(), secret.mlkem_shared.size());

        return secret;
    }

private:
    void generate_ecdh_keypair(
        std::vector<unsigned char>& priv,
        std::vector<unsigned char>& pub
    ) {}
    void generate_mlkem_keypair(
        std::vector<unsigned char>& priv,
        std::vector<unsigned char>& pub
    ) {}
    void compute_ecdh_shared(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) {}
    void mlkem_decapsulate(
        const std::vector<unsigned char>&,
        const std::vector<unsigned char>&,
        std::vector<unsigned char>&
    ) {}
    void hkdf_sha256(
        const std::vector<unsigned char>&,
        const std::string&, size_t,
        std::vector<unsigned char>&
    ) {}
    void secure_zero(unsigned char* p, size_t len) {
        volatile unsigned char* vp = p;
        while (len--) *vp++ = 0;
    }
};
```

---

## 14. Tabela comparativa completa de standards

### 14.1 Visão geral por standard

| Aspecto | FIPS 140-3 | Common Criteria | LGPD | GDPR | ICP-Brasil | eIDAS | PCI DSS 4.0 | HIPAA | CIS | NIST CSF |
|---------|-----------|----------------|------|------|-----------|-------|------------|-------|-----|----------|
| Jurisdição | EUA | Internacional | Brasil | UE | Brasil | UE | Global | EUA | Global | EUA (voluntário) |
| Tipo | Certificação | Certificação | Regulatório | Regulatório | Regulatório | Regulatório | Regulatório | Regulatório | Diretriz | Framework |
| Obrigatório | Para venda gov. | Para venda gov. | Sim | Sim | Para gov. | Sim | Para pagamentos | Para saúde | Não | Não |
| Foco | Módulo criptográfico | Produto completo | Dados pessoais | Dados pessoais | Cert. digital | Confiança digital | Dados de cartão | Dados de saúde | Configurações | Gestão de riscos |
| Criptografia | Central | Parcial | Medida técnica | Medida técnica | Central | Central | Central | Central | Configuração | Controle |

### 14.2 Requisitos de algoritmos detalhados

| Standard | Simétrica mín. | Assimétrica mín. | Hash mínimo | Transporte mínimo | Key management |
|----------|---------------|-----------------|-------------|-------------------|---------------|
| FIPS 140-3 | AES-128 | RSA 2048 / ECDSA P-256 | SHA-256 | TLS 1.2 | SP 800-57 |
| CC (EAL4+) | Conforme PP | Conforme PP | Conforme PP | Conforme PP | Documentado |
| LGPD | "Adequada" | "Adequada" | "Adequada" | "Adequada" | "Adequado" |
| GDPR | "State of the art" | "State of the art" | "State of the art" | "State of the art" | "State of the art" |
| ICP-Brasil | AES-128+ | RSA 2048+ / ECC P-256+ | SHA-256+ | TLS 1.2+ | ICP-04.001 |
| eIDAS | AES-128+ | RSA 2048+ / ECDSA P-256+ | SHA-256+ | TLS 1.2+ | Certificado qualificado |
| PCI DSS 4.0 | AES-128+ | RSA 2048+ | SHA-256+ | TLS 1.2+ | Key lifecycle |
| HIPAA | AES-128+ | RSA 2048+ | SHA-256+ | TLS 1.2+ | NIST SP 800-57 |
| CIS | AES-128+ | RSA 2048+ / Ed25519+ | SHA-256+ | TLS 1.2+ | HSM recommended |
| NIST CSF | AES-128+ | RSA 2048+ / ECC | SHA-256+ | TLS 1.2+ | SP 800-57 |

### 14.3 Requisitos de key management

| Standard | Rotação obrigatória | HSM requerido | Key splitting | Destruction | Documentação |
|----------|-------------------|---------------|---------------|-------------|-------------|
| FIPS 140-3 | Sim (Nível 3+) | Nível 3+ | Sim (Nível 3+) | Zeroing seguro | SPD completo |
| CC | Conforme PP | Conforme ST | Conforme ST | Documentado | ST completo |
| LGPD | Recomendado | Não | Não | "Medidas adequadas" | DPIA |
| GDPR | Recomendado | Não | Não | "State of the art" | DPIA |
| ICP-Brasil | Conforme AC | A3: smartcard | Não | Mencionado | PBI |
| eIDAS | Para TSA | Qualificado | Não | Mencionado | Documentado |
| PCI DSS 4.0 | Sim (6-12 meses) | Recomendado | Recomendado | Sim | Documentação Req 3 |
| HIPAA | Recomendado | Não | Não | Recomendado | Documentação |
| CIS | Recomendado | Recomendado | Não | Recomendado | Benchmarks |

### 14.4 Requisitos de auditoria e logging

| Standard | Log obrigatório | Retenção mín. | Integridade do log | Auditoria externa |
|----------|----------------|---------------|-------------------|-------------------|
| FIPS 140-3 | Sim (operações críticas) | Conforme política | Hash | CMVP |
| CC | Sim | Conforme PP | Assinatura digital | Laboratório acreditado |
| LGPD | Recomendado | 6 meses (ANPD) | Recomendado | Anual (recomendado) |
| GDPR | Sim (Art. 30) | Conforme política | Recomendado | DPIA quando aplicável |
| ICP-Brasil | Sim | 5 anos mínimo | Assinatura digital | Anual |
| eIDAS | Sim | 10 anos (TSA) | Assinatura digital | Anual |
| PCI DSS 4.0 | Sim (Req 10) | 1 ano (3 meses imediato) | Imutável | Anual (QSA) |
| HIPAA | Sim (§164.312) | 6 anos | Recomendado | Anual (recomendado) |
| CIS | Recomendado | Recomendado | Recomendado | Não |
| NIST CSF | Recomendado | Conforme política | Recomendado | Não (voluntário) |

### 14.5 Critérios de seleção de algoritmos

```
┌─────────────────────────────────────────────────────────────────┐
│ FLUXO DE DECISÃO: SELEÇÃO DE ALGORITMO POR COMPLIANCE         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. LISTAR TODOS OS STANDARDS APLICÁVEIS                       │
│     │                                                           │
│     ▼                                                           │
│  2. IDENTIFICAR ALGORITMOS PROIBIDOS EM CADA STANDARD         │
│     │   (MD5, SHA-1, DES, 3DES, RC4)                          │
│     ▼                                                           │
│  3. IDENTIFICAR ALGORITMOS EXIGIDOS EM CADA STANDARD          │
│     │   (ex: FIPS exige módulo certificado)                    │
│     ▼                                                           │
│  4. IDENTIFICAR ALGORITMOS RECOMENDADOS                        │
│     │   (AES-256-GCM é recomendado em TODOS)                   │
│     ▼                                                           │
│  5. SELECIONAR INTERSECÇÃO SEGURA                              │
│     │   Algoritmo deve ser:                                     │
│     │   - Não proibido em NENHUM standard                      │
│     │   - Exigido ou recomendado em TODOS os standards         │
│     ▼                                                           │
│  6. VALIDAR COM IMPLEMENTAÇÃO                                   │
│     │   - KATs aprovados                                       │
│     │   - Constant-time operations                             │
│     │   - Key management adequado                               │
│     ▼                                                           │
│  7. DOCUMENTAR DECISÃO                                          │
│     Justificativa para cada algoritmo selecionado              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

DECISÃO RESULTANTE PARA SISTEMA MULTICOMPLIANT:

  Simétrica:  AES-256-GCM (único algoritmo aprovado em TODOS)
  Assimétrica: RSA 2048+ ou ECDSA P-256 (aprovado em TODOS)
  Hash:        SHA-256 (aprovado em TODOS)
  KDF:         HKDF-SHA-256 ou PBKDF2 (aprovado em TODOS)
  Transporte:  TLS 1.2+ com ECDHE+AESGCM (aprovado em TODOS)
  RNG:         DRBG baseado em Hash (FIPS SP 800-90A)
```

---

## 15. Implementação de compliance em código C++

### 15.1 Arquitetura de um módulo de compliance criptográfico

```cpp
// Sistema completo de compliance criptográfico multicertificação
// Arquitetura: Strategy Pattern + Chain of Responsibility

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <functional>
#include <chrono>
#include <sstream>
#include <algorithm>
#include <mutex>
#include <optional>

// ============================================================
// PARTE 1: Modelos de dados
// ============================================================

enum class ComplianceFramework {
    FIPS_140_3,
    COMMON_CRITERIA,
    LGPD,
    GDPR,
    ICP_BRASIL,
    EIDAS,
    PCI_DSS,
    HIPAA,
    CIS_BENCHMARKS,
    NIST_CSF
};

enum class AlgorithmType {
    SYMMETRIC_ENCRYPTION,
    ASYMMETRIC_ENCRYPTION,
    SYMMETRIC_KEY_EXCHANGE,
    DIGITAL_SIGNATURE,
    HASH,
    HMAC,
    KDF,
    DRBG,
    AEAD
};

enum class AlgorithmStatus {
    APPROVED,
    ACCEPTABLE,
    RESTRICTED,
    PROHIBITED,
    UNKNOWN
};

struct AlgorithmEntry {
    std::string name;
    AlgorithmType type;
    int min_key_bits;
    int max_key_bits;
    std::string nist_reference;
    std::vector<std::string> modes;
};

struct ComplianceRule {
    ComplianceFramework framework;
    std::string rule_id;
    std::string description;
    std::function<bool(const AlgorithmEntry&)> validator;
    std::string remediation;
    bool mandatory;
};

struct ComplianceViolation {
    ComplianceFramework framework;
    std::string rule_id;
    std::string description;
    std::string algorithm;
    std::string current_status;
    std::string required_status;
    std::string remediation;
};

struct ComplianceReport {
    std::string timestamp;
    std::string system_id;
    std::vector<ComplianceViolation> violations;
    bool is_compliant;
    int compliance_score;  // 0-100
    std::unordered_map<ComplianceFramework, bool> framework_status;
};

// ============================================================
// PARTE 2: Base de dados de algoritmos
// ============================================================

class AlgorithmRegistry {
public:
    AlgorithmRegistry() {
        populate_approved_algorithms();
    }

    AlgorithmStatus get_status(
        const std::string& algorithm,
        ComplianceFramework framework
    ) const {
        auto it = algorithms_.find(algorithm);
        if (it == algorithms_.end()) {
            return AlgorithmStatus::UNKNOWN;
        }

        auto framework_it = framework_rules_.find(framework);
        if (framework_it == framework_rules_.end()) {
            return AlgorithmStatus::APPROVED;  // Sem restrições
        }

        // Verificar cada regra do framework
        for (const auto& rule : framework_it->second) {
            auto status = rule.validator(it->second);
            if (!status) {
                return AlgorithmStatus::PROHIBITED;
            }
        }

        return AlgorithmStatus::APPROVED;
    }

    const AlgorithmEntry* get_algorithm(const std::string& name) const {
        auto it = algorithms_.find(name);
        return it != algorithms_.end() ? &it->second : nullptr;
    }

    std::vector<std::string> get_approved_for_framework(
        ComplianceFramework framework,
        AlgorithmType type
    ) const {
        std::vector<std::string> approved;
        for (const auto& [name, entry] : algorithms_) {
            if (entry.type == type) {
                AlgorithmStatus status = get_status(name, framework);
                if (status == AlgorithmStatus::APPROVED) {
                    approved.push_back(name);
                }
            }
        }
        return approved;
    }

private:
    std::unordered_map<std::string, AlgorithmEntry> algorithms_;
    std::unordered_map<ComplianceFramework, std::vector<ComplianceRule>>
        framework_rules_;

    void populate_approved_algorithms() {
        // AES
        algorithms_["AES-128-GCM"] = {
            "AES-128-GCM", AlgorithmType::AEAD, 128, 256,
            "FIPS 197", {"GCM"}
        };
        algorithms_["AES-256-GCM"] = {
            "AES-256-GCM", AlgorithmType::AEAD, 128, 256,
            "FIPS 197", {"GCM"}
        };
        algorithms_["AES-128-CBC"] = {
            "AES-128-CBC", AlgorithmType::SYMMETRIC_ENCRYPTION, 128, 256,
            "FIPS 197", {"CBC"}
        };
        algorithms_["AES-256-CBC"] = {
            "AES-256-CBC", AlgorithmType::SYMMETRIC_ENCRYPTION, 128, 256,
            "FIPS 197", {"CBC"}
        };

        // RSA
        algorithms_["RSA-2048"] = {
            "RSA-2048", AlgorithmType::ASYMMETRIC_ENCRYPTION, 2048, 16384,
            "NIST SP 800-56B", {}
        };
        algorithms_["RSA-4096"] = {
            "RSA-4096", AlgorithmType::ASYMMETRIC_ENCRYPTION, 2048, 16384,
            "NIST SP 800-56B", {}
        };
        algorithms_["RSA-1024"] = {
            "RSA-1024", AlgorithmType::ASYMMETRIC_ENCRYPTION, 1024, 1024,
            "N/A", {}
        };

        // ECC
        algorithms_["ECDSA-P256"] = {
            "ECDSA-P256", AlgorithmType::DIGITAL_SIGNATURE, 256, 256,
            "NIST SP 800-186", {}
        };
        algorithms_["ECDSA-P384"] = {
            "ECDSA-P384", AlgorithmType::DIGITAL_SIGNATURE, 384, 384,
            "NIST SP 800-186", {}
        };
        algorithms_["ECDH-P256"] = {
            "ECDH-P256", AlgorithmType::SYMMETRIC_KEY_EXCHANGE, 256, 256,
            "NIST SP 800-56A", {}
        };

        // Hash
        algorithms_["SHA-256"] = {
            "SHA-256", AlgorithmType::HASH, 256, 256,
            "FIPS 180-4", {}
        };
        algorithms_["SHA-384"] = {
            "SHA-384", AlgorithmType::HASH, 384, 384,
            "FIPS 180-4", {}
        };
        algorithms_["SHA-512"] = {
            "SHA-512", AlgorithmType::HASH, 512, 512,
            "FIPS 180-4", {}
        };
        algorithms_["SHA-256"] = {
            "SHA-256", AlgorithmType::HASH, 256, 256,
            "FIPS 180-4", {}
        };

        // HMAC
        algorithms_["HMAC-SHA-256"] = {
            "HMAC-SHA-256", AlgorithmType::HMAC, 256, 256,
            "FIPS 198-1", {}
        };

        // KDF
        algorithms_["HKDF-SHA-256"] = {
            "HKDF-SHA-256", AlgorithmType::KDF, 256, 256,
            "NIST SP 800-56C", {}
        };
        algorithms_["PBKDF2"] = {
            "PBKDF2", AlgorithmType::KDF, 0, 0,
            "NIST SP 800-132", {}
        };

        // DRBG
        algorithms_["HMAC-DRBG"] = {
            "HMAC-DRBG", AlgorithmType::DRBG, 256, 256,
            "NIST SP 800-90A", {}
        };

        // PROIBIDOS
        algorithms_["MD5"] = {
            "MD5", AlgorithmType::HASH, 128, 128,
            "PROIBIDO", {}
        };
        algorithms_["SHA-1"] = {
            "SHA-1", AlgorithmType::HASH, 160, 160,
            "PROIBIDO", {}
        };
        algorithms_["DES"] = {
            "DES", AlgorithmType::SYMMETRIC_ENCRYPTION, 56, 56,
            "PROIBIDO", {}
        };
        algorithms_["3DES"] = {
            "3DES", AlgorithmType::SYMMETRIC_ENCRYPTION, 168, 168,
            "PROIBIDO", {}
        };
        algorithms_["RC4"] = {
            "RC4", AlgorithmType::SYMMETRIC_ENCRYPTION, 128, 256,
            "PROIBIDO", {}
        };
        algorithms_["RSA-1024"] = {
            "RSA-1024", AlgorithmType::ASYMMETRIC_ENCRYPTION, 1024, 1024,
            "PROIBIDO", {}
        };

        // Regras FIPS 140-3
        framework_rules_[ComplianceFramework::FIPS_140_3] = {
            {
                ComplianceFramework::FIPS_140_3,
                "FIPS-ALG-001",
                "Apenas algoritmos NIST aprovados",
                [](const AlgorithmEntry& a) {
                    return a.nist_reference.find("PROIBIDO") == std::string::npos &&
                           a.nist_reference.find("FIPS") != std::string::npos;
                },
                "Usar algoritmo NIST aprovado",
                true
            }
        };

        // Regras PCI DSS
        framework_rules_[ComplianceFramework::PCI_DSS] = {
            {
                ComplianceFramework::PCI_DSS,
                "PCI-ALG-001",
                "AES-128+ para criptografia de dados de conta",
                [](const AlgorithmEntry& a) {
                    if (a.type == AlgorithmType::SYMMETRIC_ENCRYPTION ||
                        a.type == AlgorithmType::AEAD) {
                        return a.min_key_bits >= 128;
                    }
                    return true;
                },
                "Usar AES-128 ou superior",
                true
            },
            {
                ComplianceFramework::PCI_DSS,
                "PCI-ALG-002",
                "TLS 1.2+ para dados em trânsito",
                [](const AlgorithmEntry&) { return true; },
                "Configurar TLS 1.2+ no servidor",
                true
            }
        };
    }
};

// ============================================================
// PARTE 3: Engine de compliance
// ============================================================

class ComplianceEngine {
public:
    ComplianceEngine(
        std::shared_ptr<AlgorithmRegistry> registry
    ) : registry_(registry) {}

    // Verificar compliance de algoritmos em uso
    ComplianceReport check_algorithm_compliance(
        const std::vector<std::string>& algorithms_in_use,
        const std::vector<ComplianceFramework>& required_frameworks
    ) {
        ComplianceReport report;
        report.timestamp = current_timestamp();
        report.is_compliant = true;
        report.compliance_score = 100;

        for (const auto& framework : required_frameworks) {
            bool framework_ok = true;

            for (const auto& algo_name : algorithms_in_use) {
                auto status = registry_->get_status(algo_name, framework);

                if (status == AlgorithmStatus::PROHIBITED ||
                    status == AlgorithmStatus::UNKNOWN) {
                    ComplianceViolation violation;
                    violation.framework = framework;
                    violation.rule_id = "GEN-ALG-001";
                    violation.description =
                        "Algoritmo nao aprovado para o framework";
                    violation.algorithm = algo_name;
                    violation.current_status = status_to_string(status);
                    violation.required_status = "APPROVED";
                    violation.remediation =
                        "Substituir por algoritmo aprovado no " +
                        framework_to_string(framework);

                    report.violations.push_back(violation);
                    framework_ok = false;
                    report.compliance_score -= 10;
                }
            }

            report.framework_status[framework] = framework_ok;
            if (!framework_ok) {
                report.is_compliant = false;
            }
        }

        // Limitar score a [0, 100]
        report.compliance_score =
            std::max(0, std::min(100, report.compliance_score));

        return report;
    }

    // Gerar recomendações para um framework
    std::vector<std::string> get_recommendations(
        ComplianceFramework framework
    ) {
        std::vector<std::string> recommendations;

        switch (framework) {
            case ComplianceFramework::FIPS_140_3:
                recommendations = {
                    "Usar OpenSSL 3.0+ com FIPS provider",
                    "Implementar Power-Up Self Test (POST)",
                    "Implementar KAT para todos os algoritmos",
                    "Usar constant-time operations",
                    "Documentar Security Policy Document (SPD)",
                    "Submeter ao CMVP para validação"
                };
                break;

            case ComplianceFramework::PCI_DSS:
                recommendations = {
                    "Criptografar PAN com AES-256-GCM",
                    "NUNCA armazenar CVV/PIN",
                    "Usar TLS 1.2+ para todos os canais",
                    "Implementar key rotation a cada 6-12 meses",
                    "Manter logs de auditoria por 12 meses",
                    "Realizar vulnerability scan trimestral"
                };
                break;

            case ComplianceFramework::LGPD:
                recommendations = {
                    "Implementar criptografia por categoria de dado",
                    "Usar field-level encryption para dados sensíveis",
                    "Implementar crypto-shredding para Art. 17",
                    "Documentar medidas técnicas no ROPA",
                    "Implementar DPIA para tratamento de alto risco",
                    "Manter logs de acesso por 6+ meses"
                };
                break;

            case ComplianceFramework::GDPR:
                recommendations = {
                    "Implementar criptografia como 'state of the art'",
                    "Usar pseudonimização sempre que possível",
                    "Documentar medidas no Art. 30 (ROPA)",
                    "Implementar crypto-shredding para Art. 17",
                    "Avaliar DPIA para tratamentos de alto risco",
                    "Garantir que chaves ficam no EEA para transferências"
                };
                break;

            case ComplianceFramework::HIPAA:
                recommendations = {
                    "Criptografar todo ePHI em repouso e trânsito",
                    "Usar AES-128+ (NIST aprovado) para Safe Harbor",
                    "Implementar access controls com MFA",
                    "Manter logs por 6 anos mínimo",
                    "Implementar emergency access procedure",
                    "Realizar risk analysis anual"
                };
                break;

            default:
                recommendations = {
                    "Consultar documentação específica do framework",
                    "Implementar criptografia baseada em standards NIST",
                    "Manter documentação de decisões de segurança"
                };
                break;
        }

        return recommendations;
    }

    // Gerar relatório de compliance formatado
    std::string format_report(const ComplianceReport& report) {
        std::ostringstream ss;
        ss << "=== RELATORIO DE COMPLIANCE CRIPTOGRAFICO ===\n";
        ss << "Timestamp: " << report.timestamp << "\n";
        ss << "System ID: " << report.system_id << "\n";
        ss << "Compliant: " << (report.is_compliant ? "SIM" : "NAO") << "\n";
        ss << "Score: " << report.compliance_score << "/100\n\n";

        ss << "--- STATUS POR FRAMEWORK ---\n";
        for (const auto& [framework, status] : report.framework_status) {
            ss << "  " << framework_to_string(framework) << ": "
               << (status ? "CONFORME" : "NAO CONFORME") << "\n";
        }

        if (!report.violations.empty()) {
            ss << "\n--- VIOLACOES ---\n";
            for (size_t i = 0; i < report.violations.size(); ++i) {
                const auto& v = report.violations[i];
                ss << "\n" << (i + 1) << ". [" << v.rule_id << "] "
                   << v.description << "\n";
                ss << "   Framework: " << framework_to_string(v.framework) << "\n";
                ss << "   Algoritmo: " << v.algorithm << "\n";
                ss << "   Status atual: " << v.current_status << "\n";
                ss << "   Requerido: " << v.required_status << "\n";
                ss << "   Correcao: " << v.remediation << "\n";
            }
        }

        return ss.str();
    }

private:
    std::shared_ptr<AlgorithmRegistry> registry_;

    std::string current_timestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ",
                      std::gmtime(&time));
        return std::string(buf);
    }

    std::string status_to_string(AlgorithmStatus s) {
        switch (s) {
            case AlgorithmStatus::APPROVED: return "APROVADO";
            case AlgorithmStatus::ACCEPTABLE: return "ACEITAVEL";
            case AlgorithmStatus::RESTRICTED: return "RESTRITO";
            case AlgorithmStatus::PROHIBITED: return "PROIBIDO";
            default: return "DESCONHECIDO";
        }
    }

    std::string framework_to_string(ComplianceFramework f) {
        switch (f) {
            case ComplianceFramework::FIPS_140_3: return "FIPS 140-3";
            case ComplianceFramework::COMMON_CRITERIA: return "Common Criteria";
            case ComplianceFramework::LGPD: return "LGPD";
            case ComplianceFramework::GDPR: return "GDPR";
            case ComplianceFramework::ICP_BRASIL: return "ICP-Brasil";
            case ComplianceFramework::EIDAS: return "eIDAS";
            case ComplianceFramework::PCI_DSS: return "PCI DSS 4.0";
            case ComplianceFramework::HIPAA: return "HIPAA";
            case ComplianceFramework::CIS_BENCHMARKS: return "CIS Benchmarks";
            case ComplianceFramework::NIST_CSF: return "NIST CSF 2.0";
            default: return "DESCONHECIDO";
        }
    }
};

// ============================================================
// PARTE 4: Uso do sistema
// ============================================================

// Exemplo de uso completo:
//
// int main() {
//     auto registry = std::make_shared<AlgorithmRegistry>();
//     ComplianceEngine engine(registry);
//
//     // Algoritmos em uso no sistema
//     std::vector<std::string> algorithms = {
//         "AES-256-GCM",
//         "RSA-2048",
//         "SHA-256",
//         "HMAC-SHA-256",
//         "HKDF-SHA-256"
//     };
//
//     // Frameworks aplicáveis (sistema vendido para governo + pagamentos)
//     std::vector<ComplianceFramework> frameworks = {
//         ComplianceFramework::FIPS_140_3,
//         ComplianceFramework::PCI_DSS,
//         ComplianceFramework::LGPD,
//         ComplianceFramework::GDPR
//     };
//
//     ComplianceReport report = engine.check_algorithm_compliance(
//         algorithms, frameworks
//     );
//
//     report.system_id = "PaymentSystem-v2.1";
//     std::string formatted = engine.format_report(report);
//     std::cout << formatted << std::endl;
//
//     // Obter recomendações
//     auto recs = engine.get_recommendations(
//         ComplianceFramework::FIPS_140_3
//     );
//     for (const auto& rec : recs) {
//         std::cout << "- " << rec << std::endl;
//     }
//
//     return report.is_compliant ? 0 : 1;
// }
```

### 15.2 Sistema de logging para auditoria

```cpp
// Sistema de logging criptográfico para auditoria compliance

#include <string>
#include <vector>
#include <fstream>
#include <mutex>
#include <sstream>
#include <iomanip>

enum class CryptoEventType {
    KEY_GENERATED,
    KEY_ROTATED,
    KEY_DESTROYED,
    ENCRYPTION_PERFORMED,
    DECRYPTION_PERFORMED,
    SIGNATURE_CREATED,
    SIGNATURE_VERIFIED,
    ACCESS_GRANTED,
    ACCESS_DENIED,
    CONFIG_CHANGED,
    COMPLIANCE_CHECK,
    INCIDENT_DETECTED
};

struct CryptoAuditEvent {
    uint64_t timestamp_ms;
    CryptoEventType event_type;
    std::string actor_id;
    std::string resource_id;
    std::string algorithm;
    int key_size_bits;
    bool success;
    std::string details;
    std::string source_ip;
    std::string session_id;

    // Hash de integridade do evento
    std::vector<unsigned char> integrity_hash;
};

class CryptoAuditLogger {
public:
    explicit CryptoAuditLogger(const std::string& log_path)
        : log_path_(log_path) {}

    // Registrar evento de criptografia
    void log_event(const CryptoAuditEvent& event) {
        std::lock_guard<std::mutex> lock(mutex_);

        // Serializar evento
        std::string serialized = serialize_event(event);

        // Calcular hash de integridade
        std::vector<unsigned char> hash = compute_hash(serialized);

        // Escrever no log (formato append-only)
        std::ofstream file(log_path_, std::ios::app);
        if (file.is_open()) {
            file << serialized << "\n";
            file.flush();
        }
    }

    // Registrar geração de chave
    void log_key_generation(
        const std::string& key_id,
        const std::string& algorithm,
        int key_size,
        const std::string& actor_id
    ) {
        CryptoAuditEvent event;
        event.timestamp_ms = current_ms();
        event.event_type = CryptoEventType::KEY_GENERATED;
        event.actor_id = actor_id;
        event.resource_id = key_id;
        event.algorithm = algorithm;
        event.key_size_bits = key_size;
        event.success = true;

        log_event(event);
    }

    // Registrar criptografia
    void log_encryption(
        const std::string& resource_id,
        const std::string& algorithm,
        int key_size,
        const std::string& actor_id,
        bool success
    ) {
        CryptoAuditEvent event;
        event.timestamp_ms = current_ms();
        event.event_type = CryptoEventType::ENCRYPTION_PERFORMED;
        event.actor_id = actor_id;
        event.resource_id = resource_id;
        event.algorithm = algorithm;
        event.key_size_bits = key_size;
        event.success = success;

        log_event(event);
    }

    // Registrar acesso negado
    void log_access_denied(
        const std::string& resource_id,
        const std::string& actor_id,
        const std::string& reason
    ) {
        CryptoAuditEvent event;
        event.timestamp_ms = current_ms();
        event.event_type = CryptoEventType::ACCESS_DENIED;
        event.actor_id = actor_id;
        event.resource_id = resource_id;
        event.success = false;
        event.details = reason;

        log_event(event);
    }

    // Verificar integridade do log
    bool verify_log_integrity() {
        std::lock_guard<std::mutex> lock(mutex_);

        std::ifstream file(log_path_);
        if (!file.is_open()) return false;

        std::string line;
        int line_num = 0;
        while (std::getline(file, line)) {
            line_num++;
            // Verificar hash de cada linha
            // (implementação real lê hash armazenado e compara)
        }

        return true;
    }

private:
    std::string log_path_;
    std::mutex mutex_;

    std::string serialize_event(const CryptoAuditEvent& event) {
        std::ostringstream ss;
        ss << event.timestamp_ms << "|"
           << static_cast<int>(event.event_type) << "|"
           << event.actor_id << "|"
           << event.resource_id << "|"
           << event.algorithm << "|"
           << event.key_size_bits << "|"
           << (event.success ? "OK" : "FAIL") << "|"
           << event.details << "|"
           << event.source_ip << "|"
           << event.session_id;
        return ss.str();
    }

    std::vector<unsigned char> compute_hash(const std::string& data) {
        // SHA-256 do conteúdo serializado
        return {};  // Implementação real usa OpenSSL
    }

    uint64_t current_ms() {
        return static_cast<uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count()
        );
    }
};
```

### 15.3 Gerenciador de políticas de criptografia

```cpp
// Gerenciador de políticas de criptografia baseado em JSON

class CryptoPolicyManager {
public:
    struct CryptoPolicy {
        std::string name;
        std::string version;
        ComplianceFramework framework;
        std::unordered_map<AlgorithmType, std::vector<std::string>>
            approved_algorithms;
        int min_symmetric_key_bits = 128;
        int min_asymmetric_key_bits = 2048;
        int min_hash_bits = 256;
        int key_rotation_days = 90;
        bool require_constant_time = true;
        bool require_secure_zeroing = true;
        std::string transit_protocol = "TLS_1_2";
    };

    // Carregar política de compliance
    bool load_policy(const std::string& policy_json) {
        // Em produção: usar biblioteca JSON como nlohmann/json
        // Aqui simplificado para ilustração

        CryptoPolicy policy;
        policy.name = "FIPS-140-3-Policy";
        policy.version = "2.0";
        policy.framework = ComplianceFramework::FIPS_140_3;

        // Algoritmos aprovados FIPS
        policy.approved_algorithms[AlgorithmType::AEAD] = {
            "AES-128-GCM", "AES-192-GCM", "AES-256-GCM"
        };
        policy.approved_algorithms[AlgorithmType::DIGITAL_SIGNATURE] = {
            "ECDSA-P256", "ECDSA-P384", "RSA-PSS-2048", "RSA-PSS-4096"
        };
        policy.approved_algorithms[AlgorithmType::HASH] = {
            "SHA-256", "SHA-384", "SHA-512"
        };
        policy.approved_algorithms[AlgorithmType::KDF] = {
            "HKDF-SHA-256", "HKDF-SHA-384"
        };
        policy.approved_algorithms[AlgorithmType::DRBG] = {
            "HMAC-DRBG-SHA-256", "HMAC-DRBG-SHA-384"
        };

        policy.min_symmetric_key_bits = 128;
        policy.min_asymmetric_key_bits = 2048;
        policy.min_hash_bits = 256;
        policy.key_rotation_days = 365;
        policy.require_constant_time = true;
        policy.require_secure_zeroing = true;

        policies_[policy.name] = policy;
        return true;
    }

    // Verificar se um algoritmo é aprovado pela política
    bool is_algorithm_approved(
        const std::string& policy_name,
        const std::string& algorithm,
        AlgorithmType type
    ) const {
        auto it = policies_.find(policy_name);
        if (it == policies_.end()) return false;

        const auto& approved = it->second.approved_algorithms;
        auto type_it = approved.find(type);
        if (type_it == approved.end()) return false;

        return std::find(type_it->second.begin(), type_it->second.end(),
                        algorithm) != type_it->second.end();
    }

    // Verificar se uma configuração de cifra é compliant
    CipherConfigResult validate_cipher_config(
        const std::string& policy_name,
        const std::string& cipher_string
    ) {
        CipherConfigResult result;
        result.valid = true;

        auto it = policies_.find(policy_name);
        if (it == policies_.end()) {
            result.valid = false;
            result.issues.push_back("Politica nao encontrada");
            return result;
        }

        // Verificar se há cifras proibidas
        std::vector<std::string> prohibited = {
            "RC4", "DES", "3DES", "NULL", "EXPORT", "MD5", "SHA1"
        };

        for (const auto& p : prohibited) {
            if (cipher_string.find(p) != std::string::npos) {
                result.valid = false;
                result.issues.push_back(
                    "Cipher proibida detectada: " + p
                );
            }
        }

        // Verificar se há cifras aprovadas
        bool has_approved = false;
        auto& approved = it->second.approved_algorithms;
        for (const auto& [type, algos] : approved) {
            for (const auto& algo : algos) {
                if (cipher_string.find(algo) != std::string::npos) {
                    has_approved = true;
                    break;
                }
            }
            if (has_approved) break;
        }

        if (!has_approved && !result.issues.empty()) {
            result.recommendation =
                "Adicionar cifras aprovadas: ECDHE+AESGCM";
        }

        return result;
    }

    // Listar todas as políticas carregadas
    std::vector<std::string> list_policies() const {
        std::vector<std::string> names;
        for (const auto& [name, _] : policies_) {
            names.push_back(name);
        }
        return names;
    }

private:
    std::unordered_map<std::string, CryptoPolicy> policies_;

    struct CipherConfigResult {
        bool valid = true;
        std::vector<std::string> issues;
        std::string recommendation;
    };
};
```

---

## 16. Audit preparation checklist

### 16.1 Checklist para auditoria de compliance criptográfico

```
┌─────────────────────────────────────────────────────────────────┐
│ AUDIT PREPARATION CHECKLIST — COMPLIANCE CRIPTOGRAFICO         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ FASE 1: INVENTÁRIO (4-6 semanas antes da auditoria)            │
│ ┌─ [ ] Listar todos os algoritmos criptográficos em uso        │
│ ├─ [ ] Documentar versões de bibliotecas (OpenSSL, etc.)       │
│ ├─ [ ] Mapear dados sensíveis por categoria (PII, PHI, PCI)   │
│ ├─ [ ] Identificar todos os frameworks aplicáveis              │
│ ├─ [ ] Documentar fluxo de dados (data flow diagrams)          │
│ ├─ [ ] Listar todas as APIs criptográficas utilizadas          │
│ └─ [ ] Verificar certificados e validade                      │
│                                                                 │
│ FASE 2: ANÁLISE (3-4 semanas antes)                            │
│ ┌─ [ ] Rodar ComplianceEngine e registrar violações            │
│ ├─ [ ] Verificar algoritmos proibidos (MD5, SHA-1, etc.)       │
│ ├─ [ ] Auditar key management (geração, rotação, destruição)   │
│ ├─ [ ] Verificar constant-time operations                      │
│ ├─ [ ] Auditar logging de operações criptográficas             │
│ ├─ [ ] Verificar segregação de chaves (split knowledge)        │
│ ├─ [ ] Testar crypto-shredding (LGPD/GDPR)                     │
│ └─ [ ] Verificar backups criptografados                        │
│                                                                 │
│ FASE 3: REMEDIAÇÃO (2-3 semanas antes)                         │
│ ┌─ [ ] Corrigir algoritmos proibidos encontrados               │
│ ├─ [ ] Atualizar chaves expiradas ou próximas ao vencimento    │
│ ├─ [ ] Corrigir configurações TLS (versão, cifras)             │
│ ├─ [ ] Implementar logging faltante                            │
│ ├─ [ ] Documentar justificativas para decisões técnicas        │
│ ├─ [ ] Atualizar Security Policy Document (FIPS)               │
│ ├─ [ ] Atualizar Privacy Impact Assessment (LGPD/GDPR)         │
│ └─ [ ] Preparar evidências de testes (KATs, unit tests)        │
│                                                                 │
│ FASE 4: DOCUMENTAÇÃO (1-2 semanas antes)                       │
│ ┌─ [ ] Security Policy Document (SPD) atualizado               │
│ ├─ [ ] Data Flow Diagrams com indicação de criptografia        │
│ ├─ [ ] Key Management Policy documentada                       │
│ ├─ [ ] Incident Response Plan atualizado                       │
│ ├─ [ ] Evidence binder com logs, configs, testes               │
│ ├─ [ ] Certificados CMVP/CC (se aplicável)                     │
│ ├─ [ ] DPIA/LIA para dados pessoais (LGPD/GDPR)               │
│ └─ [ ] PBI compliance (ICP-Brasil, se aplicável)               │
│                                                                 │
│ FASE 5: PREPARAÇÃO TÉCNICA (1 semana antes)                    │
│ ┌─ [ ] Executar suite de testes completa                       │
│ ├─ [ ] Verificar que KATs passam                               │
│ ├─ [ ] Testar cenários de falha (key rotation, revogação)      │
│ ├─ [ ] Verificar logs de auditoria completos                   │
│ ├─ [ ] Testar procedure de emergência                          │
│ ├─ [ ] Preparar ambiente de demonstração para o auditor        │
│ └─ [ ] Briefing da equipe sobre o que será avaliado            │
│                                                                 │
│ FASE 6: DURANTE A AUDITORIA                                     │
│ ┌─ [ ] Fornecer acesso read-only ao ambiente                   │
│ ├─ [ ] Responder perguntas com documentação                    │
│ ├─ [ ] Demonstrar operações criptográficas ao vivo             │
│ ├─ [ ] Fornecer evidências sob demanda                         │
│ └─ [ ] Registrar findings e planos de ação                     │
│                                                                 │
│ FASE 7: PÓS-AUDITORIA                                           │
│ ┌─ [ ] Implementar planos de ação para findings                │
│ ├─ [ ] Agendar follow-up se necessário                         │
│ ├─ [ ] Atualizar documentação com lições aprendidas            │
│ └─ [ ] Planejar próxima auditoria (ciclo anual)               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 16.2 Evidências para cada framework

| Framework | Evidências obrigatórias |
|-----------|------------------------|
| FIPS 140-3 | SPD, KAT results, POST logs, source code, build procedures |
| Common Criteria | ST document, PP mapping, test results, vulnerability analysis |
| LGPD | ROPA, DPIA, encryption configs, access logs, incident response |
| GDPR | ROPA, DPIA, Art. 30 records, TLS configs, data flow diagrams |
| ICP-Brasil | Certificate chain, PBI integration docs, timestamp records |
| eIDAS | Qualified certificate, TSA configuration, signature verification logs |
| PCI DSS | ASV scan results, network diagrams, key management docs, QSA report |
| HIPAA | Risk analysis, ePHI inventory, encryption configs, access logs |
| CIS | Benchmark scan results, configuration screenshots, remediation logs |
| NIST CSF | Maturity assessment, risk register, implementation evidence |

### 16.3 Formato de evidência

```
EVIDENCE BINDER STRUCTURE:

1.0 Executive Summary
    1.1 System description
    1.2 Scope of assessment
    1.3 Frameworks in scope
    1.4 Summary of findings

2.0 Cryptographic Inventory
    2.1 Algorithm list with status
    2.2 Library versions
    2.3 Certificate inventory
    2.4 Key inventory (metadata only)

3.0 Architecture Documentation
    3.1 Data flow diagrams
    3.2 Network architecture
    3.3 Encryption at rest locations
    3.4 Encryption in transit flows

4.0 Configuration Evidence
    4.1 TLS configuration (server configs)
    4.2 Cipher suite configuration
    4.3 Key management configuration
    4.4 HSM/KMS configuration

5.0 Test Results
    5.1 KAT results (algorithm validation)
    5.2 Unit test results (crypto functions)
    5.3 Integration test results
    5.4 Penetration test results

6.0 Operational Evidence
    6.1 Key rotation logs
    6.2 Access control logs
    6.3 Audit trail samples
    6.4 Incident response records

7.0 Compliance Reports
    7.1 ComplianceEngine output
    7.2 CIS Benchmark scan results
    7.3 Vulnerability scan results

8.0 Policy Documents
    8.1 Security Policy Document
    8.2 Key Management Policy
    8.3 Incident Response Plan
    8.4 Acceptable Use Policy

9.0 Remediation Records
    9.1 Issues found and fixed
    9.2 Remaining risks with justification
    9.3 Improvement roadmap
```

---

## 17. Exercícios

### Exercício 1: Avaliação de compliance (prático)

**Objetivo**: Avaliar o compliance de um sistema existente contra múltiplos frameworks.

**Enunciado**: Você recebeu o seguinte código que processa dados de saúde de
pacientes brasileiros e aceita pagamentos com cartão de crédito:

```cpp
// Código existente (propositalmente com violações)

#include <openssl/md5.h>
#include <openssl/des.h>

void process_patient_data(
    const char* cpf,
    const char* medical_record,
    double payment_amount,
    const char* card_number
) {
    // Violação 1: MD5 para hash
    unsigned char hash[MD5_DIGEST_LENGTH];
    MD5((unsigned char*)medical_record, strlen(mical_record), hash);

    // Violação 2: DES para criptografia
    DES_key_schedule schedule;
    DES_cblock key = {0x01, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef};
    DES_set_key(&key, &schedule);

    // Violação 3: Sem criptografia de CPF
    send_to_server(cpf, medical_record, payment_amount);

    // Violação 4: Card number em texto plano
    log_transaction(card_number, payment_amount);
}
```

**Tarefas**:

1. Identifique TODAS as violações de compliance no código.
2. Para cada violação, indique quais frameworks são violados.
3. Reescreva o código corrigindo todas as violações.
4. Documente a justificativa de cada correção.

**Critérios de avaliação**:
- Nenhuma violação de FIPS 140-3
- Nenhuma violação de PCI DSS (especialmente Req 3)
- Nenhuma violação de LGPD (CPF como dado pessoal)
- Nenhuma violação de HIPAA (medical_record como ePHI)

---

### Exercício 2: Matriz de decisões (conceitual)

**Objetivo**: Criar uma matriz de decisão para seleção de algoritmos.

**Enunciado**: Uma fintech brasileira vai lançar um produto que:
- Processa pagamentos (PCI DSS)
- Coleta dados pessoais (LGPD)
- Serve clientes europeus (GDPR)
- Oferece assinatura digital (eIDAS/ICP-Brasil)

**Tarefa**: Crie uma matriz de decisão detalhada que responda:

1. Quais algoritmos simétricos usar e por quê?
2. Quais algoritmos assimétricos usar e por quê?
3. Quais hashes usar e por quê?
4. Qual versão TLS usar e por quê?
5. Como gerenciar chaves de forma que atenda TODOS os frameworks?

---

### Exercício 3: Implementação de audit logger (prático)

**Objetivo**: Implementar um sistema de audit logging para operações criptográficas.

**Enunciado**: Implemente uma classe `CryptoAuditLogger` que:
1. Registre todas as operações criptográficas (encrypt, decrypt, sign, verify).
2. Cada registro tenha: timestamp, operação, ator, resultado, hash de integridade.
3. O log seja append-only (não pode ser modificado sem detecção).
4. Possa ser verificado contra manipulação.

**Requisitos técnicos**:
- Cada linha do log deve ter um HMAC-SHA-256 baseado na linha anterior
- O arquivo de log deve ter um header com versão e timestamp de criação
- A verificação de integridade deve percorrer todo o log

---

### Exercício 4: Crypto-shredding (prático)

**Objetivo**: Implementar crypto-shredding para compliance com GDPR Art. 17.

**Enunciado**: Implemente um sistema de crypto-shredding que:
1. Armazene dados de cada titular com chave dedicada.
2. Ao receber pedido de exclusão, destrua a chave (não os dados).
3. Verifique que os dados são irrecuperáveis após destruição.
4. Registre a destruição para auditoria.

**Requisitos**:
- Usar AES-256-GCM para encriptação
- Chaves devem ser armazenadas em keystore separado
- Destruição deve ser atômica (commit/rollback)
- Log de destruição deve ser imutável

---

### Exercício 5: TLS hardening (prático)

**Objetivo**: Configurar TLS de forma compliant com múltiplos standards.

**Enunciado**: Implemente uma classe `TLSConfiguration` que:

1. Gere configuração OpenSSL compatível com: FIPS 140-3, PCI DSS 4.0, CIS Benchmarks.
2. Aceite como parâmetro quais frameworks aplicar.
3. Gere a string de cipher do OpenSSL.
4. Valide se a configuração é compliant.
5. Gere relatório de compliance da configuração.

**Requisitos**:
- TLS 1.2+ como mínimo
- ECDHE+AESGCM como cifras preferidas
- Desabilitar RC4, DES, 3DES, NULL, EXPORT
- Habilitar OCSP stapling
- Configurar curvas seguras

---

### Exercício 6: Compliance multi-framework (desafio)

**Objetivo**: Projetar um sistema que atenda simultaneamente FIPS 140-3, PCI DSS, LGPD e GDPR.

**Enunciado**: Um sistema de telemedicina brasileiro:
- Atende pacientes brasileiros (LGPD) e europeus (GDPR)
- Processa pagamentos (PCI DSS)
- É vendido para hospitais federais (FIPS 140-3)
- Emite laudos assinados digitalmente (ICP-Brasil/eIDAS)

**Tarefa**: Projete a arquitetura de criptografia do sistema:
1. Mapeie os dados e identifique qual framework se aplica a cada um.
2. Defina algoritmos e protocolos para cada camada.
3. Projet o key management hierarchy.
4. Documente decisões de design e justificativas.
5. Identifique trade-offs entre os frameworks.

---

### Exercício 7: Post-Quantum readiness (conceitual)

**Objetivo**: Avaliar impacto de PQC em sistemas existentes.

**Enunciado**: Analise um sistema bancário existente e responda:
1. Quais algoritmos atuais são vulneráveis a ataques quânticos?
2. Quais dados têm "shelf life" longo o suficiente para serem ameaçados por
   um computador quântico futuro?
3. Proposta de migração híbrida (clássico + PQC).
4. Timeline e prioridades de migração.

---

## 18. Referências

### 18.1 Standards e normas

1. **NIST FIPS 140-3**: Security Requirements for Cryptographic Modules.
   https://csrc.nist.gov/publications/detail/fips/140/3/final

2. **NIST SP 800-57**: Recommendation for Key Management.
   https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final

3. **NIST SP 800-56A**: Recommendation for Pair-Wise Key-Establishment Schemes.
   https://csrc.nist.gov/publications/detail/sp/800-56a/rev-3/final

4. **NIST SP 800-90A**: Recommendation for Random Number Generation.
   https://csrc.nist.gov/publications/detail/sp/800-90a/rev-1/final

5. **ISO/IEC 15408**: Information technology — Security techniques — Evaluation criteria for IT security (Common Criteria).
   https://www.iso.org/standard/50571.html

6. **ISO/IEC 19790**: Information technology — Security techniques — Security requirements for cryptographic modules.

7. **NIST CSF 2.0**: Cybersecurity Framework.
   https://www.nist.gov/cyberframework

8. **PCI DSS v4.0**: Payment Card Industry Data Security Standard.
   https://www.pcisecuritystandards.org/document_library/

### 18.2 Legislação

9. **Lei nº 13.709/2018 (LGPD)**: Lei Geral de Proteção de Dados Pessoais.
   https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm

10. **Regulation (EU) 2016/679 (GDPR)**: General Data Protection Regulation.
    https://gdpr-info.eu/

11. **Regulation (EU) No 910/2014 (eIDAS)**: Electronic Identification, Authentication and Trust Services.
    https://eur-lex.europa.eu/eli/reg/2014/910/oj

12. **HIPAA**: Health Insurance Portability and Accountability Act.
    https://www.hhs.gov/hipaa/index.html

13. **Portaria ICP-Brasil nº 1/2023**: Atualização das normas da ICP-Brasil.
    https://www.iti.br/

### 18.3 Documentação técnica

14. **OpenSSL 3.0 FIPS Module**: Provider Documentation.
    https://www.openssl.org/docs/man3.0/man7/fips_provider.html

15. **BoringSSL**: Google's fork of OpenSSL with FIPS support.
    https://boringssl.googlesource.com/boringssl/

16. **NIST CAVP**: Cryptographic Algorithm Validation Program.
    https://csrc.nist.gov/projects/cryptographic-algorithm-validation-program

17. **CMVP**: Cryptographic Module Validation Program.
    https://csrc.nist.gov/projects/cryptographic-module-validation-program

18. **CIS Benchmarks**: Center for Internet Security.
    https://www.cisecurity.org/cis-benchmarks

### 18.4 Livros e artigos

19. **Ferguson, N., Schneier, B., & Kohno, T.** "Cryptography Engineering: Design Principles and Practical Applications." Wiley, 2010.

20. **Stallings, W.** "Cryptography and Network Security: Principles and Practice." 8th Edition, Pearson, 2021.

21. **Chen, L., et al.** "Report on Post-Quantum Cryptography." NISTIR 8105, 2016.

22. **Barker, E.** "Recommendation for Key Management: Part 1 – General." NIST SP 800-57 Part 1 Rev. 5, 2020.

23. **Gentry, C.** "Fully Homomorphic Encryption Using Ideal Lattices." STOC 2009.

24. **Bernstein, D. J.** "Introduction to post-quantum cryptography." In Post-Quantum Cryptography, Springer, 2009.

### 18.5 Ferramentas

25. **sslyze**: SSL/TLS server scanning tool.
    https://github.com/nabla-ssllabs/sslyze

26. **testssl.sh**: Testing TLS/SSL encryption on any port.
    https://github.com/drwetter/testssl.sh

27. **Cryptool**: Tool suite for cryptography education and analysis.
    https://www.cryptool.org/

28. **OpenVAS**: Open-source vulnerability scanner.
    https://www.openvas.org/

---

## Nota final

O compliance criptográfico não é um destino — é uma jornada contínua. Os
standards evoluem, novos ataques são descobertos, e os requisitos regulatórios
se tornam mais rigorosos. O engenheiro de C++ que dominar este tópico não
apenas protege seus sistemas, mas também protege sua organização de riscos
legais, financeiros e reputacionais.

Lembre-se: o melhor sistema de compliance é aquele projetado desde o início
("compliance by design"), não aquele adaptado depois de um incidente
("compliance by retrofit").

---

*Capítulo 14 — Compliance e Normas Criptográficas*
*Projeto DevSecurity — Livro 5: Engenharia de Criptografia em C++*
---

*[Capítulo anterior: 13 — Testes Implementacoes](13-testes-implementacoes.md)*
*[Próximo capítulo: 15 — Estudo Caso Tls Server](15-estudo-caso-tls-server.md)*
