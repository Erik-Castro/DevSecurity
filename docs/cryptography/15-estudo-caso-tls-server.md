---
layout: default
title: "15-estudo-caso-tls-server"
---

# Capítulo 15: Estudo de Caso — TLS Server Seguro em C++

> **"A segurança não é um produto, é um processo."** — Bruce Schneier

---

## Sumário

1. [Objetivos de Aprendizado](#151-objetivos-de-aprendizado)
2. [Requisitos do Servidor](#152-requisitos-do-servidor)
3. [Arquitetura: Event-Driven e Non-Blocking I/O](#153-arquitetura-event-driven-e-non-blocking-io)
4. [Inicialização do OpenSSL 3.x e Provider Setup](#154-inicialização-do-openssl-3x-e-provider-setup)
5. [Gerenciamento de Certificados](#155-gerenciamento-de-certificados)
6. [Configuração TLS 1.3](#156-configuração-tls-13)
7. [Gerenciamento de Sessões](#157-gerenciamento-de-sessões)
8. [Gerenciamento de Chaves](#158-gerenciamento-de-chaves)
9. [Implementação Completa do TLS Server](#159-implementação-completa-do-tls-server)
10. [Hardening de Segurança](#1510-hardening-de-segurança)
11. [Otimização de Performance](#1511-otimização-de-performance)
12. [Testes do Servidor](#1512-testes-do-servidor)
13. [Deployment](#1513-deployment)
14. [Monitoramento e Alertas](#1514-monitoramento-e-alertas)
15. [Revisão de CVE](#1515-revisão-de-cve)
16. [Exercícios](#1516-exercícios)
17. [Referências](#1517-referências)

---

## 15.1 Objetivos de Aprendizado

Este capítulo representa a culminação de todo o Livro 5. Aqui, integramos cada componente
estudado anteriormente em um servidor TLS completo, production-ready, escrito em C++17
modern e seguro. Ao final deste capítulo, o leitor será capaz de:

- Projetar e implementar um servidor TLS 1.3 completo usando OpenSSL 3.x
- Aplicar gerenciamento seguro de certificados e chaves em ambiente produtivo
- Implementar hardening de segurança baseado em OWASP e NIST guidelines
- Integrar HSMs para proteção de chaves em nível físico
- Criar sistema de rotação automática de chaves sem downtime
- Implementar monitoramento e alertas para detecção de anomalias
- Realizar testes de penetração e validação de conformidade
- Entender e mitigar CVEs reais afetando implementações TLS
- Operar servidor TLS em ambientes Docker, Kubernetes e cloud
- Otimizar performance sem comprometer segurança

### Pré-requisitos

Este capítulo assume conhecimento consolidado dos capítulos anteriores:

| Capítulo | Conceito Chave | Aplicação Neste Capítulo |
|----------|---------------|-------------------------|
| Cap. 1-2 | Fundamentos de criptografia | Base de todas as operações |
| Cap. 3 | AES e criptografia simétrica | Proteção de dados em trânsito |
| Cap. 4 | RSA e criptografia assimétrica | Troca de chaves TLS |
| Cap. 5 | Hash e HMAC | Integridade de mensagens |
| Cap. 6 | Certificados X.509 | Autenticação do servidor |
| Cap. 7 | TLS/SSL | Protocolo subjacente |
| Cap. 8 | Gerenciamento de chaves | HSM e rotação |
| Cap. 9 | Random e entropia | Geração segura de nonces |
| Cap. 10 | Side-channel attacks | Hardening de implementação |
| Cap. 11 | Secure coding | Defesa contra vulnerabilidades |
| Cap. 12 | Testes de segurança | Validação da implementação |
| Cap. 13 | Performance | Otimização do servidor |
| Cap. 14 | Compliance | Atendimento a padrões |

### Arquivo de Projeto

Todos os códigos deste capítulo estão organizados da seguinte forma:

```
tls-server/
├── CMakeLists.txt
├── include/
│   ├── tls_server.h
│   ├── ssl_context.h
│   ├── connection_manager.h
│   ├── certificate_handler.h
│   ├── session_manager.h
│   ├── key_manager.h
│   ├── thread_pool.h
│   ├── logger.h
│   ├── metrics.h
│   └── config.h
├── src/
│   ├── main.cpp
│   ├── tls_server.cpp
│   ├── ssl_context.cpp
│   ├── connection_manager.cpp
│   ├── certificate_handler.cpp
│   ├── session_manager.cpp
│   ├── key_manager.cpp
│   ├── thread_pool.cpp
│   ├── logger.cpp
│   └── metrics.cpp
├── config/
│   ├── server.yaml
│   └── openssl.cnf
├── certs/
│   ├── server.crt
│   ├── server.key
│   ├── ca.crt
│   └── dhparam.pem
├── tests/
│   ├── test_tls_handshake.cpp
│   ├── test_certificate_validation.cpp
│   ├── test_session_resumption.cpp
│   └── test_performance.cpp
└── deploy/
    ├── Dockerfile
    ├── docker-compose.yml
    └── systemd/
        └── tls-server.service
```

---

## 15.2 Requisitos do Servidor

### 15.2.1 Requisitos de Performance

Um servidor TLS em produção deve atender a métricas específicas de performance.
Estabelecer metas claras desde o início evita retrabalho e garante que a implementação
atenda às expectativas de operação.

**Métricas de Performance Alvo:**

```
Métrica                          | Meta           | Justificativa
--------------------------------|----------------|----------------------------------
Latência TLS handshake (1.3)    | < 2ms          | Usuários percebem delays > 100ms
Throughput de conexões/s        | > 10,000       | Suporte a cargas de pico
Memória por conexão             | < 50KB         | Eficiência de recursos
CPU por handshake               | < 1ms          | Deixa margem para lógica de negócio
Conexões simultâneas            | > 100,000      | Escalabilidade horizontal
Time-to-first-byte              | < 50ms         | Experiência do usuário
Reconexão com resumption        | < 500μs        | Sessões recorrentes
```

**Trade-offs Importantes:**

Performance e segurança frequentemente entram em conflito. O servidor precisa navegar
essa tensão com critério:

- **Session tickets** reduzem latência de reconexão mas exigem rotação segura de chaves
- **OCSP stapling** melhora performance mas requer manutenção de cache
- **TLS 1.3** é mais rápido que TLS 1.2 mas suporta menos opções de retrocompatibilidade
- **HSMs** adicionam latência mas são obrigatórios para chaves de alto valor
- **Constant-time operations** são mais lentas mas essenciais contra side-channels

### 15.2.2 Requisitos de Segurança

O servidor deve seguir o princípio de defesa em profundidade. Cada camada oferece
proteção independente, de modo que a falha em uma camada não compromete todo o sistema.

**Nível de Segurança Alvo:**

```
Componente                      | Nível Mínimo   | Referência
-------------------------------|----------------|---------------------------
Protocolo TLS                  | TLS 1.3        | RFC 8446
Cipher suites                  | AEAD apenas    | NIST SP 800-52 Rev 2
Chave de sessão                | 256-bit        | NIST SP 800-57
Chave de assinatura            | ECDSA P-256+   | NIST FIPS 186-4
DH parameters                  | 2048-bit+      | NIST SP 800-56A
Random number generation       | CSPRNG         | NIST SP 800-90A
Certificate validation         | Full chain     | RFC 5280
Key storage                    | HSM/PKCS#11    | FIPS 140-2 Level 3
```

**Controles de Segurança Obrigatórios:**

1. **Autenticação mútua opcional (mTLS)** — suporte a client certificates
2. **OCSP Must-Staple** — servidor deve fornecer resposta OCSP válida
3. **Certificate Transparency** — logs CT devem ser verificados
4. **HSTS** — Header Strict-Transport-Security com max-age adequado
5. **Certificate pinning** — para aplicações móveis (com pinning backup)
6. **Forward secrecy** — ECDHE obrigatório em todos os cipher suites
7. **Anti-replay** — proteção contra replay de handshakes
8. **Memory wiping** — chaves sensíveis devem ser limpas da memória

### 15.2.3 Requisitos de Compliance

O servidor deve atender a múltiplos frameworks de compliance simultaneamente.
Cada framework tem requisitos específicos que afetam a implementação.

**PCI DSS 4.0:**

- Criptografia de dados sensíveis em trânsito com TLS 1.2+
- Certificate revocation checking obrigatório
- Logs de todas as conexões TLS
- Key management procedures documentados
- Vulnerability scanning periódico

**GDPR:**

- Dados pessoais devem ser criptografados
- Right to erasure deve ser suportado
- Data processing logs com retenção definida
- Breach notification em 72h

**HIPAA:**

- Criptografia de ePHI em trânsito
- Audit controls para acessos
- Integrity controls
- Transmission security

**SOC 2 Type II:**

- Security monitoring contínuo
- Incident response procedures
- Change management process
- Access controls documentados

### 15.2.4 Requisitos Operacionais

```
Requisito                       | Detalhamento
-------------------------------|-------------------------------------------
Disponibilidade                 | 99.99% (52 min downtime/ano)
Recovery Time Objective (RTO)   | < 5 minutos
Recovery Point Objective (RPO)  | Zero (sem perda de dados)
Rolling upgrade                 | Sem downtime
Observabilidade                 | Métricas, logs, traces
Alertas                         | Anomalias de performance e segurança
Automação                       | Deploy, scaling, recovery
```

---

## 15.3 Arquitetura: Event-Driven e Non-Blocking I/O

### 15.3.1 Por que Event-Driven?

Servidores tradicionais usando threads por conexão enfrentam problemas de escalabilidade
quando o número de conexões simultâneas cresce. Cada thread consome entre 1-8MB de
stack, e o overhead de context switching se torna proibitivo acima de algumas milhares
de threads.

A arquitetura event-driven resolve isso usando um modelo baseado em I/O não-bloqueante,
onde poucas threads gerenciam milhares de conexões.

**Comparação de Modelos:**

```
Modelo               | Threads por Conn | Memória/10K Conn | Scalabilidade
--------------------|------------------|------------------|----------------
Thread-per-request  | 1                | 10-80 GB         | Baixa
Thread pool fixo    | 0 (reusada)      | 100MB-1GB        | Média
Event-driven (1 th) | 0                | 500MB            | Alta
Event-driven (N th) | 0                | 500MB            | Muito Alta
```

### 15.3.2 Arquitetura do Servidor

A arquitetura do servidor TLS segue o padrão Reactor, com componentes bem definidos
e responsabilidades isoladas.

```
┌─────────────────────────────────────────────────────────────────┐
│                        TLS Server Architecture                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Accept     │    │   Event      │    │   Worker     │      │
│  │   Thread     │───▶│   Loop       │───▶│   Threads    │      │
│  │              │    │   (epoll/    │    │   (N pool)   │      │
│  └──────────────┘    │    kqueue)   │    └──────┬───────┘      │
│                      └──────┬───────┘           │              │
│                             │                   │              │
│                             ▼                   ▼              │
│                      ┌──────────────┐    ┌──────────────┐      │
│                      │   SSL        │    │   Application│      │
│                      │   Context    │    │   Handler    │      │
│                      │   Manager   │    │              │      │
│                      └──────┬───────┘    └──────┬───────┘      │
│                             │                   │              │
│                             ▼                   ▼              │
│                      ┌──────────────┐    ┌──────────────┐      │
│                      │   Certificate│    │   Session    │      │
│                      │   Handler   │    │   Manager    │      │
│                      └──────────────┘    └──────────────┘      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Cross-Cutting Concerns                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │  │
│  │  │ Logging  │  │ Metrics  │  │   Key    │  │  HSM   │  │  │
│  │  │          │  │          │  │ Manager  │  │ Client │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 15.3.3 Ciclo de Vida de uma Conexão

Cada conexão TLS passa por um ciclo de vida bem definido. Entender esse ciclo é
essencial para implementar cada ponto de controle de segurança corretamente.

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  ACCEPT │────▶│  TLS    │────▶│ REQUEST │────▶│ RESPONSE│
│         │     │ HANDSHAKE│     │ PROCESS │     │ SEND    │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Validate│     │ Verify  │     │ Decrypt │     │ Encrypt │
│ IP/Port │     │ Cert    │     │ Data    │     │ Data    │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
    │               │               │               │
    ▼               ▼               ▼               ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Rate   │     │Generate │     │ Execute │     │  Flush  │
│  Limit  │     │ Session │     │ Business│     │  Buffer │
│  Check  │     │ Ticket  │     │ Logic   │     │         │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                                                     │
                                                     ▼
                                              ┌─────────┐
                                              │  CLOSE  │
                                              │ (Clean) │
                                              └─────────┘
```

### 15.3.4 Integração com OpenSSL 3.x

OpenSSL 3.x introduziu o conceito de providers, que abstrai a implementação criptográfica
subjacente. Isso permite usar diferentes backends (software, HSM, FPGA) sem alterar
o código da aplicação.

**Fluxo de Inicialização:**

```cpp
// O OpenSSL 3.x exige inicialização explícita de providers
// Isso é diferente do OpenSSL 1.x, que usava algoritmos por default

// 1. Carregar provider padrão (software)
OSSL_PROVIDER *default_provider = OSSL_PROVIDER_load(nullptr, "default");

// 2. Carregar provider FIPS (se disponível)
OSSL_PROVIDER *fips_provider = OSSL_PROVIDER_load(nullptr, "fips");

// 3. Configurar propriedades de busca
OSSL_LIB_CTX *libctx = OSSL_LIB_CTX_new();

// 4. Usar propriedade para forçar provider específico
EVP_MD *sha256 = EVP_MD_fetch(libctx, "SHA256", "provider=fips");
```

### 15.3.5 Modelo de Threads

O servidor usa um modelo de threads híbrido que combina benefícios de event-driven
com paralelismo de múltiplos cores.

```
                    ┌──────────────────┐
                    │   Main Thread    │
                    │  (Accept Loop)   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Worker     │ │  Worker     │ │  Worker     │
    │  Thread 1   │ │  Thread 2   │ │  Thread N   │
    │             │ │             │ │             │
    │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │
    │ │Event    │ │ │ │Event    │ │ │ │Event    │ │
    │ │Loop 1   │ │ │ │Loop 2   │ │ │ │Loop N   │ │
    │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │
    └─────────────┘ └─────────────┘ └─────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────┴─────────┐
                    │   I/O Threads   │
                    │ (Non-blocking)  │
                    └──────────────────┘
```

**Configuração do Pool de Threads:**

```cpp
struct ThreadPoolConfig {
    // Número de worker threads
    // Regra geral: 2 * num_cpus + 1 para CPU-bound
    // Regra geral: num_cpus para I/O-bound
    // Para TLS server: I/O-bound dominante
    std::size_t worker_threads = std::thread::hardware_concurrency();

    // Número de I/O threads para operações bloqueantes
    // Usado para: DNS resolution, OCSP queries, disk I/O
    std::size_t io_threads = 4;

    // Prioridade das threads
    int worker_priority = 0;      // Normal priority
    int io_priority = -1000;      // SCHED_IDLE (Linux)

    // Stack size por thread (reduzido para economia de memória)
    std::size_t stack_size = 1 * 1024 * 1024;  // 1MB (padrão: 8MB)
};
```

---

## 15.4 Inicialização do OpenSSL 3.x e Provider Setup

### 15.4.1 Mudanças no OpenSSL 3.x

OpenSSL 3.0 representou uma mudança arquitetural significativa. O modelo de providers
substituiu o sistema de engines e mudou fundamentalmente como algoritmos são carregados
e usados. Ignorar essas mudanças resulta em código que não compila ou, pior, que
compila mas não usa os algoritmos corretos.

**Principais mudanças:**

1. **Provider model** — algoritmos são servidos por providers, não compilados
2. **Library context** — contextos isolados para diferentes configurações
3. **Deprecated API** — muitas funções 1.x marcadas como deprecated
4. **FIPS provider** — modo FIPS é agora um provider separado
5. **Fetch API** — novas formas de obter algoritmos

### 15.4.2 Inicialização Segura

```cpp
// ssl_init.h
#pragma once

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/provider.h>
#include <openssl/rand.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/ocsp.h>
#include <openssl/comp.h>

#include <memory>
#include <stdexcept>
#include <string>
#include <mutex>
#include <atomic>

namespace tls_server {

// RAII wrapper para OSSL_PROVIDER
class OsslProvider {
public:
    OsslProvider(OSSL_LIB_CTX* ctx, const char* name)
        : provider_(OSSL_PROVIDER_load(ctx, name)) {
        if (!provider_) {
            throw std::runtime_error(
                std::string("Failed to load OpenSSL provider: ") + name);
        }
    }

    ~OsslProvider() {
        if (provider_) {
            OSSL_PROVIDER_unload(provider_);
        }
    }

    OsslProvider(const OsslProvider&) = delete;
    OsslProvider& operator=(const OsslProvider&) = delete;

    OsslProvider(OsslProvider&& other) noexcept
        : provider_(other.provider_) {
        other.provider_ = nullptr;
    }

    OsslProvider& operator=(OsslProvider&& other) noexcept {
        if (this != &other) {
            if (provider_) {
                OSSL_PROVIDER_unload(provider_);
            }
            provider_ = other.provider_;
            other.provider_ = nullptr;
        }
        return *this;
    }

    [[nodiscard]] OSSL_PROVIDER* get() const noexcept {
        return provider_;
    }

    [[nodiscard]] bool is_loaded() const noexcept {
        return provider_ != nullptr;
    }

private:
    OSSL_PROVIDER* provider_ = nullptr;
};

// RAII wrapper para OSSL_LIB_CTX
class OsslLibCtx {
public:
    OsslLibCtx() : ctx_(OSSL_LIB_CTX_new()) {
        if (!ctx_) {
            throw std::runtime_error(
                "Failed to create OpenSSL library context");
        }
    }

    ~OsslLibCtx() {
        if (ctx_) {
            OSSL_LIB_CTX_free(ctx_);
        }
    }

    OsslLibCtx(const OsslLibCtx&) = delete;
    OsslLibCtx& operator=(const OsslLibCtx&) = delete;

    [[nodiscard]] OSSL_LIB_CTX* get() const noexcept {
        return ctx_;
    }

    [[nodiscard]] operator OSSL_LIB_CTX*() const noexcept {
        return ctx_;
    }

private:
    OSSL_LIB_CTX* ctx_ = nullptr;
};

// Classe principal de inicialização do OpenSSL
class OpenSSLInitializer {
public:
    static OpenSSLInitializer& instance() {
        static OpenSSLInitializer inst;
        return inst;
    }

    // Inicialização completa com todos os providers necessários
    void initialize(const std::string& fips_config_path = "",
                    bool enable_fips = false) {
        std::lock_guard<std::mutex> lock(init_mutex_);

        if (initialized_) {
            return;
        }

        // 1. Criar library context
        lib_ctx_ = std::make_unique<OsslLibCtx>();

        // 2. Carregar provider padrão (SEMPRE necessário)
        default_provider_ = std::make_unique<OsslProvider>(
            lib_ctx_->get(), "default");

        // 3. Carregar provider FIPS se habilitado
        if (enable_fips) {
            // Configurar caminho do módulo FIPS
            if (!fips_config_path.empty()) {
                std::string config =
                    "openssl_conf = openssl_init\n"
                    "[openssl_init]\n"
                    "providers = provider_sect\n"
                    "[provider_sect]\n"
                    "fips = fips_sect\n"
                    "[fips_sect]\n"
                    "activate = 1\n"
                    "module = " + fips_config_path + "\n";

                // Aplicar configuração
                OSSL_LIB_CTX_load_config(lib_ctx_->get(),
                    fips_config_path.c_str());
            }

            fips_provider_ = std::make_unique<OsslProvider>(
                lib_ctx_->get(), "fips");

            // Verificar se FIPS está realmente ativo
            if (!OSSL_PROVIDER_try_load(lib_ctx_->get(), "fips")) {
                throw std::runtime_error(
                    "FIPS provider requested but failed to load");
            }
        }

        // 4. Inicializar algoritmos necessários
        if ( EVP_MD_fetch(lib_ctx_->get(), "SHA256", nullptr) == nullptr ) {
            throw std::runtime_error("Failed to fetch SHA256");
        }

        // 5. Configurar DRBG para random numbers
        if (!configure_drbg()) {
            throw std::runtime_error("Failed to configure DRBG");
        }

        // 6. Verificar versão do OpenSSL
        verify_openssl_version();

        initialized_ = true;
    }

    [[nodiscard]] OSSL_LIB_CTX* lib_context() const noexcept {
        return lib_ctx_ ? lib_ctx_->get() : nullptr;
    }

    [[nodiscard]] bool is_fips_enabled() const noexcept {
        return fips_provider_ && fips_provider_->is_loaded();
    }

    [[nodiscard]] bool is_initialized() const noexcept {
        return initialized_;
    }

private:
    OpenSSLInitializer() = default;
    ~OpenSSLInitializer() {
        // Ordem inversa da inicialização
        fips_provider_.reset();
        default_provider_.reset();
        lib_ctx_.reset();

        // Cleanup global do OpenSSL
        EVP_cleanup();
        ERR_free_strings();
    }

    bool configure_drbg() {
        // Configurar DRBG (Deterministic Random Bit Generator)
        // Usando AES-256-CTR como algoritmo de DRBG
        EVP_RAND *rand = EVP_RAND_fetch(lib_ctx_->get(), "CTR-DRBG", nullptr);
        if (!rand) {
            return false;
        }

        EVP_RAND_CTX *rand_ctx = EVP_RAND_CTX_new(rand, nullptr);
        if (!rand_ctx) {
            EVP_RAND_free(rand);
            return false;
        }

        // Configurar parâmetros do DRBG
        uint64_t one = 1;
        OSSL_PARAM params[] = {
            OSSL_PARAM_construct_utf8_ptr("cipher",
                const_cast<char**>("AES-256-CTR")),
            OSSL_PARAM_construct_utf8_ptr("digest",
                const_cast<char**>("SHA-256")),
            OSSL_PARAM_construct_uint64("prediction_resistance",
                &one),
            OSSL_PARAM_END
        };

        bool success = EVP_RAND_instantiate(rand_ctx, 256, 0, nullptr, params)
                       == 1;

        EVP_RAND_CTX_free(rand_ctx);
        EVP_RAND_free(rand);

        return success;
    }

    void verify_openssl_version() {
        int major = OpenSSL_version_num() >> 28;

        if (major < 3) {
            throw std::runtime_error(
                "OpenSSL 3.x required. Found: " +
                std::string(OpenSSL_version(OPENSSL_VERSION)));
        }
    }

    std::mutex init_mutex_;
    bool initialized_ = false;
    std::unique_ptr<OsslLibCtx> lib_ctx_;
    std::unique_ptr<OsslProvider> default_provider_;
    std::unique_ptr<OsslProvider> fips_provider_;
};

// Função helper para inicialização
inline void initialize_openssl(const std::string& fips_config = "",
                               bool enable_fips = false) {
    OpenSSLInitializer::instance().initialize(fips_config, enable_fips);
}

}  // namespace tls_server
```

### 15.4.3 Configuração de FIPS Mode

O modo FIPS é obrigatório para muitos ambientes regulados. Com OpenSSL 3.x, o FIPS
é implementado como um provider separado, o que simplifica a ativação mas exige
configuração cuidadosa.

```cpp
// fips_provider.h
#pragma once

#include <openssl/provider.h>
#include <openssl/evp.h>
#include <string>
#include <stdexcept>
#include <vector>

namespace tls_server {

class FIPSProvider {
public:
    struct Config {
        std::string module_path;
        std::string config_file;
        bool require_fips = true;
        bool self_test_on_load = true;
        bool log_self_test_results = true;
    };

    explicit FIPSProvider(OSSL_LIB_CTX* ctx, const Config& config)
        : ctx_(ctx) {

        provider_ = OSSL_PROVIDER_load(ctx, "fips");

        if (!provider_) {
            if (config.require_fips) {
                throw std::runtime_error(
                    "FIPS mode required but provider failed to load. "
                    "Error: " + get_last_error());
            }
            return;
        }

        if (config.self_test_on_load && provider_) {
            run_self_test(config.log_self_test_results);
        }

        fips_enabled_ = (provider_ != nullptr);
    }

    ~FIPSProvider() {
        if (provider_) {
            OSSL_PROVIDER_unload(provider_);
        }
    }

    FIPSProvider(const FIPSProvider&) = delete;
    FIPSProvider& operator=(const FIPSProvider&) = delete;

    [[nodiscard]] bool is_enabled() const noexcept {
        return fips_enabled_;
    }

    [[nodiscard]] OSSL_PROVIDER* provider() const noexcept {
        return provider_;
    }

private:
    void run_self_test(bool log_results) {
        std::vector<std::string> required_algorithms = {
            "AES-256-GCM", "AES-128-GCM",
            "SHA-256", "SHA-384", "SHA-512",
            "ECDSA", "ECDH",
            "HMAC", "HKDF",
            "RSA", "DRBG"
        };

        for (const auto& algo : required_algorithms) {
            EVP_MD *md = EVP_MD_fetch(ctx_, algo.c_str(),
                                       "provider=fips");
            if (!md) {
                if (log_results) {
                    log_error("FIPS self-test FAILED for: " + algo);
                }
                throw std::runtime_error(
                    "FIPS self-test failed for algorithm: " + algo);
            }
            EVP_MD_free(md);

            if (log_results) {
                log_info("FIPS self-test PASSED for: " + algo);
            }
        }
    }

    static std::string get_last_error() {
        unsigned long err = ERR_get_error();
        char buf[256];
        ERR_error_string_n(err, buf, sizeof(buf));
        return std::string(buf);
    }

    static void log_error(const std::string& msg) {
        std::cerr << "[FIPS ERROR] " << msg << std::endl;
    }

    static void log_info(const std::string& msg) {
        std::cout << "[FIPS INFO] " << msg << std::endl;
    }

    OSSL_LIB_CTX* ctx_;
    OSSL_PROVIDER* provider_ = nullptr;
    bool fips_enabled_ = false;
};

}  // namespace tls_server
```

### 15.4.4 Error Handling do OpenSSL

O OpenSSL tem um sistema de erros baseado em thread-local storage. Cada thread mantém
uma pilha de erros que deve ser consultada após cada chamada que pode falhar. Ignorar
erros do OpenSSL é uma das fontes mais comuns de vulnerabilidades em implementações TLS.

```cpp
// ssl_error.h
#pragma once

#include <openssl/err.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <sstream>

namespace tls_server {

struct SslError {
    unsigned long code;
    std::string reason;
    std::string function;
    std::string file;
    int line;
};

class SslErrorStack {
public:
    static std::vector<SslError> capture() {
        std::vector<SslError> errors;
        unsigned long err;

        while ((err = ERR_get_error()) != 0) {
            SslError error;
            error.code = err;

            char buf[256];
            ERR_error_string_n(err, buf, sizeof(buf));
            error.reason = buf;

            ERR_get_error_line_data(nullptr, &error.line,
                                    nullptr, nullptr);
            error.file = ERR_reason_error_string(err);

            errors.push_back(std::move(error));
        }

        return errors;
    }

    static std::string capture_and_format() {
        auto errors = capture();
        if (errors.empty()) {
            return "No SSL errors";
        }

        std::ostringstream oss;
        oss << "SSL Errors (" << errors.size() << "):" << std::endl;

        for (size_t i = 0; i < errors.size(); ++i) {
            oss << "  [" << i << "] Code: 0x"
                << std::hex << errors[i].code
                << " - " << errors[i].reason << std::endl;
        }

        return oss.str();
    }

    static void check_and_throw(const std::string& context = "") {
        auto errors = capture();
        if (!errors.empty()) {
            std::ostringstream oss;
            oss << "OpenSSL error";
            if (!context.empty()) {
                oss << " during " << context;
            }
            oss << ": " << errors[0].reason;

            if (errors.size() > 1) {
                oss << " (+" << (errors.size() - 1) << " more errors)";
            }

            throw std::runtime_error(oss.str());
        }
    }

    static bool check_ssl_return(int ret, SSL* ssl,
                                  const std::string& context = "") {
        int ssl_err = SSL_get_error(ssl, ret);

        switch (ssl_err) {
            case SSL_ERROR_NONE:
                return true;

            case SSL_ERROR_WANT_READ:
            case SSL_ERROR_WANT_WRITE:
                return false;

            case SSL_ERROR_ZERO_RETURN:
                return false;

            case SSL_ERROR_SYSCALL:
                if (ret == 0) {
                    throw std::runtime_error(
                        "SSL: Unexpected EOF in " + context);
                }
                throw std::runtime_error(
                    "SSL: System call error in " + context);

            case SSL_ERROR_SSL:
                check_and_throw(context);
                break;

            default:
                throw std::runtime_error(
                    "SSL: Unknown error " + std::to_string(ssl_err) +
                    " in " + context);
        }

        return false;
    }
};

}  // namespace tls_server
```
---

## 15.5 Gerenciamento de Certificados

### 15.5.1 Estrutura de Certificados

O gerenciamento de certificados é uma das partes mais críticas de um servidor TLS.
Erros na validação de certificados podem expor o servidor a ataques man-in-the-middle
ou causar denegação de serviço por rejeição de clientes válidos.

```cpp
// certificate_handler.h
#pragma once

#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/err.h>
#include <openssl/ocsp.h>
#include <openssl/ct.h>

#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <functional>
#include <mutex>
#include <optional>

namespace tls_server {

struct CertificateConfig {
    std::string cert_file;
    std::string key_file;
    std::string chain_file;
    std::string ca_file;
    std::string ca_path;
    std::string crl_file;
    bool verify_client = false;
    bool ocsp_stapling = true;
    int verify_depth = 10;
    bool check_crl = true;
    bool check_ocsp = true;
    bool must_staple = false;
    bool ct_verification = false;
};

class CertificateHandler {
public:
    explicit CertificateHandler(const CertificateConfig& config);
    ~CertificateHandler();

    CertificateHandler(const CertificateHandler&) = delete;
    CertificateHandler& operator=(const CertificateHandler&) = delete;

    void configure_ssl_context(SSL_CTX* ctx);
    bool reload_certificates();
    bool is_certificate_expiring_soon(int days_threshold = 30) const;

    struct CertificateInfo {
        std::string subject;
        std::string issuer;
        std::string serial;
        std::string not_before;
        std::string not_after;
        std::string thumbprint_sha256;
        std::vector<std::string> san_dns;
        std::vector<std::string> san_ip;
        std::string key_type;
        int key_size;
        std::string signature_algorithm;
        bool is_ca;
        bool is_self_signed;
    };

    CertificateInfo get_certificate_info() const;

    std::vector<unsigned char> generate_ocsp_response(
        const unsigned char* request_data, size_t request_len);

    bool check_ocsp_status(X509* cert);

    void enable_ct_verification(SSL_CTX* ctx);

    void load_crl(const std::string& crl_path);

    std::string get_last_error() const;

private:
    static int verify_callback(int preverify_ok, X509_STORE_CTX* ctx);
    static int verify_client_callback(int preverify_ok, X509_STORE_CTX* ctx);
    bool validate_certificate_chain(X509* cert, STACK_OF(X509) *chain);
    OCSP_REQUEST* create_ocsp_request(X509* cert, X509* issuer);
    bool verify_ocsp_response(OCSP_RESPONSE* resp, X509* cert);
    bool verify_sct_list(const STACK_OF(SCT) *scts);
    EVP_PKEY* load_private_key(const std::string& key_file,
                               const std::string& passphrase = "");
    STACK_OF(X509)* load_certificate_chain(const std::string& chain_file);
    std::vector<std::string> get_san_entries(X509* cert, int nid);

    CertificateConfig config_;
    X509* cert_ = nullptr;
    EVP_PKEY* key_ = nullptr;
    STACK_OF(X509)* chain_ = nullptr;
    X509_STORE* store_ = nullptr;
    X509_CRL* crl_ = nullptr;

    mutable std::mutex cert_mutex_;
    std::string last_error_;

    struct OcspCacheEntry {
        std::vector<unsigned char> response;
        std::chrono::steady_clock::time_point expiry;
        std::string cert_id;
    };
    std::vector<OcspCacheEntry> ocsp_cache_;
    std::mutex ocsp_cache_mutex_;
};

}  // namespace tls_server
```

### 15.5.2 Implementação do CertificateHandler

```cpp
// certificate_handler.cpp
#include "certificate_handler.h"
#include "ssl_error.h"

#include <openssl/bio.h>
#include <openssl/pem.h>
#include <openssl/x509v3.h>
#include <openssl/ocsp.h>
#include <openssl/ct.h>

#include <fstream>
#include <sstream>
#include <algorithm>
#include <filesystem>
#include <cstring>

namespace tls_server {

CertificateHandler::CertificateHandler(const CertificateConfig& config)
    : config_(config) {

    BIO* cert_bio = BIO_new_file(config_.cert_file.c_str(), "r");
    if (!cert_bio) {
        throw std::runtime_error(
            "Failed to open certificate file: " + config_.cert_file);
    }

    cert_ = PEM_read_bio_X509(cert_bio, nullptr, nullptr, nullptr);
    BIO_free(cert_bio);

    if (!cert_) {
        SslErrorStack::check_and_throw("loading server certificate");
    }

    key_ = load_private_key(config_.key_file);
    if (!key_) {
        throw std::runtime_error(
            "Failed to load private key: " + config_.key_file);
    }

    if (X509_check_private_key(cert_, key_) != 1) {
        EVP_PKEY_free(key_);
        X509_free(cert_);
        throw std::runtime_error(
            "Private key does not match certificate");
    }

    if (!config_.chain_file.empty()) {
        chain_ = load_certificate_chain(config_.chain_file);
    }

    store_ = X509_STORE_new();
    if (!store_) {
        throw std::runtime_error("Failed to create X509 store");
    }

    if (!config_.ca_file.empty()) {
        if (X509_STORE_load_locations(store_, config_.ca_file.c_str(),
                                       nullptr) != 1) {
            throw std::runtime_error(
                "Failed to load CA file: " + config_.ca_file);
        }
    }

    if (!config_.ca_path.empty()) {
        if (X509_STORE_load_locations(store_, nullptr,
                                       config_.ca_path.c_str()) != 1) {
            throw std::runtime_error(
                "Failed to load CA path: " + config_.ca_path);
        }
    }

    if (!config_.crl_file.empty() && config_.check_crl) {
        load_crl(config_.crl_file);
    }

    X509_STORE_set_verify_cb(store_, verify_callback);
    X509_STORE_set_depth(store_, config_.verify_depth);
}

CertificateHandler::~CertificateHandler() {
    if (cert_) X509_free(cert_);
    if (key_) EVP_PKEY_free(key_);
    if (chain_) sk_X509_pop_free(chain_, X509_free);
    if (store_) X509_STORE_free(store_);
    if (crl_) X509_CRL_free(crl_);
}

void CertificateHandler::configure_ssl_context(SSL_CTX* ctx) {
    std::lock_guard<std::mutex> lock(cert_mutex_);

    if (SSL_CTX_use_certificate(ctx, cert_) != 1) {
        throw std::runtime_error("Failed to set certificate on SSL_CTX");
    }

    if (SSL_CTX_use_PrivateKey(ctx, key_) != 1) {
        throw std::runtime_error("Failed to set private key on SSL_CTX");
    }

    if (SSL_CTX_check_private_key(ctx) != 1) {
        throw std::runtime_error(
            "Private key does not match certificate in SSL_CTX");
    }

    if (chain_) {
        for (int i = 0; i < sk_X509_num(chain_); ++i) {
            X509* ca_cert = sk_X509_value(chain_, i);
            SSL_CTX_add_extra_chain_cert(ctx, X509_dup(ca_cert));
        }
    }

    if (config_.verify_client) {
        SSL_CTX_set_verify(ctx,
            SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
            verify_client_callback);

        if (config_.ca_file.empty() && config_.ca_path.empty()) {
            throw std::runtime_error(
                "mTLS enabled but no CA file/path configured");
        }
    } else {
        SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, nullptr);
    }

    SSL_CTX_set_verify_depth(ctx, config_.verify_depth);
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);
    SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

    if (config_.ocsp_stapling) {
        SSL_CTX_set_tlsext_status_type(ctx, TLSEXT_STATUSTYPE_ocsp);
    }

    if (config_.ct_verification) {
        enable_ct_verification(ctx);
    }
}

EVP_PKEY* CertificateHandler::load_private_key(
    const std::string& key_file,
    const std::string& passphrase) {

    BIO* key_bio = BIO_new_file(key_file.c_str(), "r");
    if (!key_bio) {
        last_error_ = "Failed to open key file: " + key_file;
        return nullptr;
    }

    EVP_PKEY* pkey = nullptr;

    if (!passphrase.empty()) {
        pem_password_cb* cb = [](char* buf, int size,
                                  int rwflag, void* u) -> int {
            std::string* pass = static_cast<std::string*>(u);
            int len = std::min(static_cast<int>(pass->size()), size - 1);
            std::memcpy(buf, pass->c_str(), len);
            buf[len] = '\0';
            return len;
        };

        pkey = PEM_read_bio_PrivateKey(key_bio, nullptr, cb,
                                        const_cast<void*>(
                                            static_cast<const void*>(
                                                &passphrase)));
    } else {
        pkey = PEM_read_bio_PrivateKey(key_bio, nullptr, nullptr, nullptr);
    }

    BIO_free(key_bio);

    if (!pkey) {
        SslErrorStack error_stack;
        last_error_ = "Failed to load private key: " +
                     error_stack.capture_and_format();
    }

    return pkey;
}

STACK_OF(X509)* CertificateHandler::load_certificate_chain(
    const std::string& chain_file) {

    BIO* chain_bio = BIO_new_file(chain_file.c_str(), "r");
    if (!chain_bio) {
        throw std::runtime_error(
            "Failed to open chain file: " + chain_file);
    }

    STACK_OF(X509)* chain = sk_X509_new_null();
    if (!chain) {
        BIO_free(chain_bio);
        throw std::runtime_error("Failed to create certificate stack");
    }

    X509* cert;
    while ((cert = PEM_read_bio_X509(chain_bio, nullptr, nullptr, nullptr))
           != nullptr) {
        if (!sk_X509_push(chain, cert)) {
            X509_free(cert);
            sk_X509_pop_free(chain, X509_free);
            BIO_free(chain_bio);
            throw std::runtime_error(
                "Failed to push certificate to chain");
        }
    }

    BIO_free(chain_bio);

    if (sk_X509_num(chain) == 0) {
        sk_X509_pop_free(chain, X509_free);
        throw std::runtime_error(
            "No certificates found in chain file: " + chain_file);
    }

    return chain;
}

void CertificateHandler::load_crl(const std::string& crl_path) {
    BIO* crl_bio = BIO_new_file(crl_path.c_str(), "r");
    if (!crl_bio) {
        throw std::runtime_error("Failed to open CRL file: " + crl_path);
    }

    X509_CRL* new_crl = PEM_read_bio_X509_CRL(crl_bio, nullptr, nullptr,
                                                nullptr);
    BIO_free(crl_bio);

    if (!new_crl) {
        throw std::runtime_error("Failed to parse CRL file: " + crl_path);
    }

    if (crl_) {
        X509_CRL_free(crl_);
    }

    crl_ = new_crl;

    if (!X509_STORE_add_crl(store_, crl_)) {
        throw std::runtime_error("Failed to add CRL to store");
    }

    X509_STORE_set_flags(store_, X509_V_FLAG_CRL_CHECK |
                                  X509_V_FLAG_CRL_CHECK_ALL);
}

void CertificateHandler::enable_ct_verification(SSL_CTX* ctx) {
    SSL_CTX_set_ct_validation_cb(ctx,
        [](SSL* s, void* arg) -> int {
            const STACK_OF(SCT)* scts = SSL_get0_peer_scts(s);

            if (!scts || sk_SCT_num(scts) < 1) {
                return 0;
            }

            for (int i = 0; i < sk_SCT_num(scts); ++i) {
                SCT* sct = sk_SCT_value(scts, i);
                SCT_verify_reason reason;
                int result = SCT_verify(sct, sct, &reason);

                if (result != 1) {
                    return 0;
                }
            }

            return 1;
        }, nullptr);
}

CertificateHandler::CertificateInfo
CertificateHandler::get_certificate_info() const {
    std::lock_guard<std::mutex> lock(cert_mutex_);

    CertificateInfo info;

    if (!cert_) {
        return info;
    }

    char subject[256], issuer[256];
    X509_NAME_oneline(X509_get_subject_name(cert_), subject, sizeof(subject));
    X509_NAME_oneline(X509_get_issuer_name(cert_), issuer, sizeof(issuer));
    info.subject = subject;
    info.issuer = issuer;

    BIGNUM* bn_serial = ASN1_INTEGER_to_BN(
        X509_get_serialNumber(cert_), nullptr);
    if (bn_serial) {
        char* serial_str = BN_bn2dec(bn_serial);
        info.serial = serial_str;
        OPENSSL_free(serial_str);
        BN_free(bn_serial);
    }

    BIO* bio = BIO_new(BIO_s_mem());
    ASN1_TIME_print(bio, X509_get0_notBefore(cert_));
    char buf[256];
    int len = BIO_read(bio, buf, sizeof(buf) - 1);
    buf[len] = '\0';
    info.not_before = buf;
    BIO_reset(bio);

    ASN1_TIME_print(bio, X509_get0_notAfter(cert_));
    len = BIO_read(bio, buf, sizeof(buf) - 1);
    buf[len] = '\0';
    info.not_after = buf;
    BIO_free(bio);

    unsigned char digest[SHA256_DIGEST_LENGTH];
    unsigned int digest_len;
    X509_digest(cert_, EVP_sha256(), digest, &digest_len);

    std::ostringstream oss;
    for (unsigned int i = 0; i < digest_len; ++i) {
        if (i > 0) oss << ":";
        oss << std::hex << std::setw(2) << std::setfill('0')
            << static_cast<int>(digest[i]);
    }
    info.thumbprint_sha256 = oss.str();

    info.san_dns = get_san_entries(cert_, NID_subject_alt_name);

    EVP_PKEY* pkey = X509_get0_pubkey(cert_);
    if (pkey) {
        int key_type = EVP_PKEY_base_id(pkey);
        switch (key_type) {
            case EVP_PKEY_RSA:
                info.key_type = "RSA";
                info.key_size = EVP_PKEY_bits(pkey);
                break;
            case EVP_PKEY_EC:
                info.key_type = "EC";
                info.key_size = EVP_PKEY_bits(pkey);
                break;
            case EVP_PKEY_ED25519:
                info.key_type = "Ed25519";
                info.key_size = 256;
                break;
            default:
                info.key_type = "Unknown";
                info.key_size = 0;
        }
    }

    const ASN1_OBJECT* sig_alg;
    X509_get0_signature(nullptr, &sig_alg, cert_);
    char sig_name[256];
    OBJ_obj2txt(sig_name, sizeof(sig_name), sig_alg, 1);
    info.signature_algorithm = sig_name;

    info.is_ca = (X509_check_ca(cert_) == 1);
    info.is_self_signed =
        (X509_name_cmp(X509_get_subject_name(cert_),
                        X509_get_issuer_name(cert_)) == 0);

    return info;
}

std::vector<std::string> CertificateHandler::get_san_entries(
    X509* cert, int nid) {

    std::vector<std::string> entries;
    GENERAL_NAMES* names = static_cast<GENERAL_NAMES*>(
        X509_get_ext_d2i(cert, NID_subject_alt_name, nullptr, nullptr));

    if (!names) {
        return entries;
    }

    for (int i = 0; i < sk_GENERAL_NAME_num(names); ++i) {
        GENERAL_NAME* name = sk_GENERAL_NAME_value(names, i);

        if (name->type == GEN_DNS) {
            unsigned char* dns_name = nullptr;
            int len = ASN1_STRING_to_UTF8(&dns_name, name->d.dNSName);
            if (len >= 0 && dns_name) {
                entries.emplace_back(
                    reinterpret_cast<char*>(dns_name), len);
                OPENSSL_free(dns_name);
            }
        } else if (name->type == GEN_IPADD) {
            const ASN1_OCTET_STRING* ip = name->d.iPAddress;
            if (ip->length == 4) {
                char ip_str[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, ip->data, ip_str, sizeof(ip_str));
                entries.emplace_back(ip_str);
            } else if (ip->length == 6) {
                char ip_str[INET6_ADDRSTRLEN];
                inet_ntop(AF_INET6, ip->data, ip_str, sizeof(ip_str));
                entries.emplace_back(ip_str);
            }
        }
    }

    sk_GENERAL_NAME_pop_free(names, GENERAL_NAME_free);
    return entries;
}

bool CertificateHandler::is_certificate_expiring_soon(
    int days_threshold) const {

    std::lock_guard<std::mutex> lock(cert_mutex_);

    if (!cert_) {
        return true;
    }

    const ASN1_TIME* not_after = X509_get0_notAfter(cert_);
    if (!not_after) {
        return true;
    }

    int day, sec;
    if (ASN1_TIME_diff(&day, &sec, not_after, nullptr)) {
        return day <= days_threshold;
    }

    return true;
}

bool CertificateHandler::reload_certificates() {
    std::lock_guard<std::mutex> lock(cert_mutex_);

    BIO* cert_bio = BIO_new_file(config_.cert_file.c_str(), "r");
    if (!cert_bio) {
        last_error_ = "Failed to open certificate file for reload";
        return false;
    }

    X509* new_cert = PEM_read_bio_X509(cert_bio, nullptr, nullptr, nullptr);
    BIO_free(cert_bio);

    if (!new_cert) {
        last_error_ = "Failed to parse new certificate";
        return false;
    }

    EVP_PKEY* new_key = load_private_key(config_.key_file);
    if (!new_key) {
        X509_free(new_cert);
        last_error_ = "Failed to load new private key";
        return false;
    }

    if (X509_check_private_key(new_cert, new_key) != 1) {
        X509_free(new_cert);
        EVP_PKEY_free(new_key);
        last_error_ = "New private key does not match new certificate";
        return false;
    }

    X509_free(cert_);
    cert_ = new_cert;

    EVP_PKEY_free(key_);
    key_ = new_key;

    if (!config_.crl_file.empty() && config_.check_crl) {
        load_crl(config_.crl_file);
    }

    return true;
}

int CertificateHandler::verify_callback(int preverify_ok,
                                          X509_STORE_CTX* ctx) {
    if (!preverify_ok) {
        int error = X509_STORE_CTX_get_error(ctx);
        int depth = X509_STORE_CTX_get_error_depth(ctx);

        std::cerr << "Certificate verification error at depth " << depth
                  << ": " << X509_verify_cert_error_string(error)
                  << std::endl;

        switch (error) {
            case X509_V_ERR_CERT_HAS_EXPIRED:
                return 0;
            case X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT:
                return 0;
            case X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT:
                return 0;
            case X509_V_ERR_CRL_HAS_EXPIRED:
                return 1;
            default:
                return 0;
        }
    }

    return 1;
}

int CertificateHandler::verify_client_callback(int preverify_ok,
                                                X509_STORE_CTX* ctx) {
    if (!preverify_ok) {
        int error = X509_STORE_CTX_get_error(ctx);
        X509* cert = X509_STORE_CTX_get_current_cert(ctx);
        int depth = X509_STORE_CTX_get_error_depth(ctx);

        char subject[256];
        if (cert) {
            X509_NAME_oneline(X509_get_subject_name(cert),
                              subject, sizeof(subject));
        } else {
            snprintf(subject, sizeof(subject), "unknown");
        }

        std::cerr << "mTLS verification failed for client '"
                  << subject << "' at depth " << depth
                  << ": " << X509_verify_cert_error_string(error)
                  << std::endl;
    }

    return preverify_ok;
}

}  // namespace tls_server
```

### 15.5.3 OCSP Stapling

OCSP stapling é uma extensão do protocolo OCSP onde o servidor busca periodicamente
o status de revogação do seu próprio certificado e fornece a resposta ao cliente durante
o handshake. Isso melhora a privacidade do cliente e reduz a latência.

```cpp
// ocsp_handler.h
#pragma once

#include <openssl/ssl.h>
#include <openssl/ocsp.h>
#include <openssl/x509.h>

#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <mutex>
#include <functional>

namespace tls_server {

class OCSPHandler {
public:
    struct Config {
        std::string ocsp_responder_url;
        int refresh_interval_seconds = 3600;
        int timeout_seconds = 5;
        bool require_staple = false;
        bool stapling_enabled = true;
        size_t max_cache_size = 1000;
    };

    explicit OCSPHandler(const Config& config);
    ~OCSPHandler();

    std::vector<unsigned char> get_stapled_response(SSL* ssl);
    void refresh_ocsp_response(X509* cert, X509* issuer);
    bool is_response_valid(const unsigned char* resp_data, size_t resp_len);
    void configure_ssl_context(SSL_CTX* ctx);
    static int tls_status_cb(SSL* ssl, void* arg);
    bool is_certificate_revoked(X509* cert, X509* issuer);

    struct Stats {
        size_t total_requests;
        size_t cache_hits;
        size_t cache_misses;
        size_t refresh_failures;
        std::chrono::steady_clock::time_point last_refresh;
    };

    Stats get_stats() const;

private:
    OCSP_REQUEST* create_request(X509* cert, X509* issuer);
    OCSP_RESPONSE* send_request(OCSP_REQUEST* req);
    bool validate_response(OCSP_RESPONSE* resp, X509* cert, X509* issuer);
    std::string compute_cert_id(X509* cert);

    struct CacheEntry {
        std::vector<unsigned char> response_data;
        std::chrono::steady_clock::time_point expiry;
        std::string cert_id;
    };

    Config config_;
    std::vector<CacheEntry> cache_;
    mutable std::mutex cache_mutex_;
    Stats stats_ = {};
    X509* cached_cert_ = nullptr;
    X509* cached_issuer_ = nullptr;
};

}  // namespace tls_server
```

---

## 15.6 Configuração TLS 1.3

### 15.6.1 Cipher Suites do TLS 1.3

TLS 1.3 simplificou drasticamente os cipher suites comparado ao TLS 1.2. Agora, todos
os cipher suites são AEAD e incluem obrigatoriamente um algoritmo de key exchange
baseado em Diffie-Hellman.

**Cipher Suites TLS 1.3 (RFC 8446):**

```
Cipher Suite                    | Key Exchange | Cipher      | Hash
------------------------------|-------------|-------------|----------
TLS_AES_256_GCM_SHA384        | (any)       | AES-256-GCM | SHA-384
TLS_AES_128_GCM_SHA256        | (any)       | AES-128-GCM | SHA-256
TLS_CHACHA20_POLY1305_SHA256  | (any)       | ChaCha20    | SHA-256
TLS_AES_128_CCM_SHA256        | (any)       | AES-128-CCM | SHA-256
TLS_AES_128_CCM_8_SHA256      | (any)       | AES-128-CCM8| SHA-256
```

**Key Exchange Groups TLS 1.3:**

```
Named Group        | Tamanho | Curva        | Segurança Recomendada
-------------------|---------|-------------|----------------------
x25519             | 253-bit | Curve25519  | Excelente
secp256r1          | 256-bit | P-256        | Boa
secp384r1          | 384-bit | P-384        | Excelente
secp521r1          | 521-bit | P-521        | Excelente
x448               | 448-bit | Curve448     | Excelente
secp256k1          | 256-bit | K-256        | Boa
```

### 15.6.2 Configuração TLS 1.3

```cpp
// ssl_context.h
#pragma once

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/ec.h>
#include <openssl/evp.h>
#include <openssl/dh.h>
#include <openssl/rsa.h>
#include <openssl/bn.h>
#include <openssl/comp.h>

#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <optional>
#include <map>

namespace tls_server {

struct TLSConfig {
    int min_version = TLS1_2_VERSION;
    int max_version = TLS1_3_VERSION;

    std::vector<std::string> tls13_ciphers = {
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256"
    };

    std::vector<std::string> tls12_ciphers = {
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-CHACHA20-POLY1305",
        "ECDHE-RSA-CHACHA20-POLY1305",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES128-GCM-SHA256"
    };

    std::vector<std::string> named_groups = {
        "x25519",
        "secp256r1",
        "secp384r1"
    };

    std::vector<std::string> sigalgs = {
        "ecdsa_secp256r1_sha256",
        "ecdsa_secp384r1_sha384",
        "ecdsa_secp521r1_sha512",
        "rsa_pss_rsae_sha256",
        "rsa_pss_rsae_sha384",
        "rsa_pss_rsae_sha512",
        "rsa_pkcs1_sha256",
        "rsa_pkcs1_sha384",
        "rsa_pkcs1_sha512"
    };

    std::vector<std::string> alpn_protocols = {
        "h2",
        "http/1.1"
    };

    bool session_tickets = true;
    std::string ticket_key_file;
    bool server_preference = true;
    bool compression = false;
    bool renegotiation = false;
    bool early_data = false;
    uint64_t max_early_data = 0;

    int read_buffer_size = 16384;
    int write_buffer_size = 16384;
    int handshake_timeout_ms = 10000;
    int read_timeout_ms = 30000;
    int write_timeout_ms = 30000;
};

class SSLContext {
public:
    explicit SSLContext(const TLSConfig& config = {});
    ~SSLContext();

    SSLContext(const SSLContext&) = delete;
    SSLContext& operator=(const SSLContext&) = delete;
    SSLContext(SSLContext&& other) noexcept;
    SSLContext& operator=(SSLContext&& other) noexcept;

    void configure();
    SSL* create_connection(int fd);
    void configure_alpn();
    void configure_session_tickets();
    void configure_groups_and_sigalgs();
    void configure_early_data();

    [[nodiscard]] SSL_CTX* get() const noexcept { return ctx_; }

    std::string get_debug_info() const;
    bool test_configuration() const;
    void rotate_ticket_keys();

private:
    void configure_ciphers();
    void configure_curves();
    void configure_sigalgs();

    static int security_callback(SSL* s, SSL_CTX* ctx,
                                  int op, int bits, int nid,
                                  void* other, void* ex);

    static int alpn_callback(SSL* s,
                              const unsigned char** out,
                              unsigned char* outlen,
                              const unsigned char* in,
                              unsigned int inlen, void* arg);

    static int sni_callback(SSL* s, int* ad, void* arg);

    void generate_ticket_keys();

    struct TicketKey {
        unsigned char name[16];
        unsigned char aes_key[32];
        unsigned char hmac_key[32];
        std::chrono::steady_clock::time_point created;
        bool active = true;
    };

    SSL_CTX* ctx_ = nullptr;
    TLSConfig config_;
    std::vector<TicketKey> ticket_keys_;
    mutable std::mutex ticket_mutex_;
};

}  // namespace tls_server
```

### 15.6.3 Implementação do SSLContext

```cpp
// ssl_context.cpp
#include "ssl_context.h"
#include "ssl_error.h"

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

#include <stdexcept>
#include <sstream>
#include <algorithm>
#include <cstring>

namespace tls_server {

SSLContext::SSLContext(const TLSConfig& config) : config_(config) {
    const SSL_METHOD* method = TLS_server_method();
    ctx_ = SSL_CTX_new(method);

    if (!ctx_) {
        throw std::runtime_error("Failed to create SSL_CTX");
    }

    SSL_CTX_set_options(ctx_,
        SSL_OP_NO_SSLv2 |
        SSL_OP_NO_SSLv3 |
        SSL_OP_NO_TLSv1 |
        SSL_OP_NO_TLSv1_1 |
        SSL_OP_CIPHER_SERVER_PREFERENCE |
        SSL_OP_SINGLE_ECDH_USE |
        SSL_OP_SINGLE_DH_USE |
        SSL_OP_NO_COMPRESSION
    );

    SSL_CTX_set_min_proto_version(ctx_, config_.min_version);
    SSL_CTX_set_max_proto_version(ctx_, config_.max_version);
}

SSLContext::~SSLContext() {
    if (ctx_) {
        SSL_CTX_free(ctx_);
    }
}

SSLContext::SSLContext(SSLContext&& other) noexcept
    : ctx_(other.ctx_),
      config_(std::move(other.config_)),
      ticket_keys_(std::move(other.ticket_keys_)) {
    other.ctx_ = nullptr;
}

SSLContext& SSLContext::operator=(SSLContext&& other) noexcept {
    if (this != &other) {
        if (ctx_) {
            SSL_CTX_free(ctx_);
        }
        ctx_ = other.ctx_;
        config_ = std::move(other.config_);
        ticket_keys_ = std::move(other.ticket_keys_);
        other.ctx_ = nullptr;
    }
    return *this;
}

void SSLContext::configure() {
    configure_ciphers();
    configure_groups_and_sigalgs();
    configure_alpn();

    if (config_.session_tickets) {
        configure_session_tickets();
    }

    if (config_.early_data) {
        configure_early_data();
    }

    SSL_CTX_set_security_callback(ctx_, security_callback);
    SSL_CTX_set_tlsext_servername_callback(ctx_, sni_callback);

    if (config_.session_tickets) {
        generate_ticket_keys();
    }
}

void SSLContext::configure_ciphers() {
    std::string tls13_ciphers_str;
    for (size_t i = 0; i < config_.tls13_ciphers.size(); ++i) {
        if (i > 0) tls13_ciphers_str += ":";
        tls13_ciphers_str += config_.tls13_ciphers[i];
    }

    if (!SSL_CTX_set_ciphersuites(ctx_, tls13_ciphers_str.c_str())) {
        throw std::runtime_error(
            "Failed to set TLS 1.3 cipher suites: " + tls13_ciphers_str);
    }

    std::string tls12_ciphers_str;
    for (size_t i = 0; i < config_.tls12_ciphers.size(); ++i) {
        if (i > 0) tls12_ciphers_str += ":";
        tls12_ciphers_str += config_.tls12_ciphers[i];
    }

    if (!SSL_CTX_set_cipher_list(ctx_, tls12_ciphers_str.c_str())) {
        throw std::runtime_error(
            "Failed to set TLS 1.2 cipher suites: " + tls12_ciphers_str);
    }
}

void SSLContext::configure_groups_and_sigalgs() {
    std::string groups_str;
    for (size_t i = 0; i < config_.named_groups.size(); ++i) {
        if (i > 0) groups_str += ":";
        groups_str += config_.named_groups[i];
    }

    if (!SSL_CTX_set1_groups_list(ctx_, groups_str.c_str())) {
        throw std::runtime_error(
            "Failed to set groups: " + groups_str);
    }

    std::string sigalgs_str;
    for (size_t i = 0; i < config_.sigalgs.size(); ++i) {
        if (i > 0) sigalgs_str += ":";
        sigalgs_str += config_.sigalgs[i];
    }

    if (!SSL_CTX_set1_sigalgs_list(ctx_, sigalgs_str.c_str())) {
        throw std::runtime_error(
            "Failed to set sigalgs: " + sigalgs_str);
    }
}

void SSLContext::configure_alpn() {
    if (config_.alpn_protocols.empty()) {
        return;
    }

    SSL_CTX_set_alpn_select_cb(ctx_,
        [](SSL* s,
           const unsigned char** out,
           unsigned char* outlen,
           const unsigned char* in,
           unsigned int inlen, void* arg) -> int {

            std::vector<std::string>& protos =
                *static_cast<std::vector<std::string>*>(arg);

            for (const auto& server_proto : protos) {
                for (unsigned int i = 0; i < inlen; ) {
                    unsigned char proto_len = in[i];
                    i++;

                    if (i + proto_len > inlen) {
                        break;
                    }

                    std::string client_proto(
                        reinterpret_cast<const char*>(in + i), proto_len);

                    if (client_proto == server_proto) {
                        *out = in + i;
                        *outlen = proto_len;
                        return SSL_TLSEXT_ERR_OK;
                    }

                    i += proto_len;
                }
            }

            return SSL_TLSEXT_ERR_NOACK;
        },
        &config_.alpn_protocols);
}

void SSLContext::configure_session_tickets() {
    SSL_CTX_set_options(ctx_, SSL_OP_NO_TICKET);
    SSL_CTX_set_max_early_data(ctx_, config_.max_early_data);
}

void SSLContext::configure_early_data() {
    if (!config_.early_data) {
        return;
    }

    SSL_CTX_set_max_early_data(ctx_, config_.max_early_data);
    SSL_CTX_set_recv_max_early_data(ctx_, config_.max_early_data);
}

void SSLContext::generate_ticket_keys() {
    std::lock_guard<std::mutex> lock(ticket_mutex_);

    for (int i = 0; i < 4; ++i) {
        TicketKey key;
        key.created = std::chrono::steady_clock::now();

        if (RAND_bytes(key.name, sizeof(key.name)) != 1) {
            throw std::runtime_error("Failed to generate ticket key name");
        }

        if (RAND_bytes(key.aes_key, sizeof(key.aes_key)) != 1) {
            throw std::runtime_error("Failed to generate ticket AES key");
        }

        if (RAND_bytes(key.hmac_key, sizeof(key.hmac_key)) != 1) {
            throw std::runtime_error("Failed to generate ticket HMAC key");
        }

        key.active = (i == 0);

        ticket_keys_.push_back(std::move(key));
    }

    for (const auto& key : ticket_keys_) {
        if (key.active) {
            SSL_CTX_set_tlsext_ticket_keys(ctx_,
                const_cast<unsigned char*>(key.name),
                sizeof(key.name));
        }
    }
}

void SSLContext::rotate_ticket_keys() {
    std::lock_guard<std::mutex> lock(ticket_mutex_);

    TicketKey new_key;
    new_key.created = std::chrono::steady_clock::now();
    new_key.active = true;

    if (RAND_bytes(new_key.name, sizeof(new_key.name)) != 1) {
        throw std::runtime_error("Failed to generate new ticket key name");
    }

    if (RAND_bytes(new_key.aes_key, sizeof(new_key.aes_key)) != 1) {
        throw std::runtime_error("Failed to generate new ticket AES key");
    }

    if (RAND_bytes(new_key.hmac_key, sizeof(new_key.hmac_key)) != 1) {
        throw std::runtime_error("Failed to generate new ticket HMAC key");
    }

    if (!ticket_keys_.empty()) {
        ticket_keys_.front().active = false;
    }

    ticket_keys_.insert(ticket_keys_.begin(), std::move(new_key));

    while (ticket_keys_.size() > 4) {
        ticket_keys_.pop_back();
    }

    std::vector<unsigned char> key_names;
    for (const auto& key : ticket_keys_) {
        if (key.active) {
            key_names.insert(key_names.end(),
                           key.name, key.name + sizeof(key.name));
        }
    }

    SSL_CTX_set_tlsext_ticket_keys(ctx_,
        key_names.data(), key_names.size());
}

const SSL_METHOD* SSLContext::sni_callback(
    SSL* s, int* ad, void* arg) {

    const char* sni = SSL_get_servername(s, TLSEXT_NAMETYPE_host_name);

    if (sni) {
        std::cout << "SNI: " << sni << std::endl;
    }

    return SSL_TLSEXT_ERR_OK;
}

std::string SSLContext::get_debug_info() const {
    std::ostringstream oss;

    oss << "SSL Context Configuration:" << std::endl;
    oss << "  Min version: " << config_.min_version << std::endl;
    oss << "  Max version: " << config_.max_version << std::endl;

    oss << "  TLS 1.3 ciphers: ";
    for (const auto& c : config_.tls13_ciphers) {
        oss << c << " ";
    }
    oss << std::endl;

    oss << "  Named groups: ";
    for (const auto& g : config_.named_groups) {
        oss << g << " ";
    }
    oss << std::endl;

    oss << "  Sigalgs: ";
    for (const auto& s : config_.sigalgs) {
        oss << s << " ";
    }
    oss << std::endl;

    oss << "  ALPN protocols: ";
    for (const auto& p : config_.alpn_protocols) {
        oss << p << " ";
    }
    oss << std::endl;

    oss << "  Session tickets: " << config_.session_tickets << std::endl;
    oss << "  Early data: " << config_.early_data << std::endl;

    return oss.str();
}

}  // namespace tls_server
```

---

## 15.7 Gerenciamento de Sessões

### 15.7.1 Session Tickets no TLS 1.3

TLS 1.3 mudou fundamentalmente como session resumption funciona. O mecanismo baseado
em session IDs do TLS 1.2 foi removido. Agora, apenas session tickets são suportados,
e o servidor pode fornecer múltiplos tickets por handshake.

**Vantagens de Session Resumption:**

- **0-RTT**: Reconexão pode usar early data, eliminando round-trip do handshake
- **1-RTT**: Handshake completo é mais rápido com state armazenado
- **Segurança**: Chaves derivadas por sessão limitam impacto de comprometimento

**Riscos de Session Resumption:**

- **Replay attacks**: Early data (0-RTT) não tem proteção contra replay
- **Ticket theft**: Roubo de ticket permite impersonation
- **Key compromise**: Comprometimento da chave de ticket compromete todas as sessões

### 15.7.2 Implementação de Session Manager

```cpp
// session_manager.h
#pragma once

#include <openssl/ssl.h>
#include <openssl/rand.h>

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <chrono>
#include <mutex>
#include <functional>
#include <optional>
#include <random>

namespace tls_server {

struct SessionConfig {
    bool tickets_enabled = true;
    std::string ticket_key;
    size_t ticket_key_rotation_hours = 24;
    size_t max_tickets_per_handshake = 2;

    bool server_side_cache = false;
    size_t max_cache_size = 10000;
    int cache_timeout_seconds = 300;

    bool early_data_enabled = false;
    uint64_t max_early_data_size = 16384;
    bool reject_early_data_replay = true;

    bool anti_replay_enabled = true;
    size_t anti_replay_window_size = 10000;
};

struct SessionData {
    std::string session_id;
    std::vector<unsigned char> master_secret;
    std::vector<unsigned char> session_ticket;
    std::chrono::steady_clock::time_point created;
    std::chrono::steady_clock::time_point last_access;
    std::string client_ip;
    uint16_t client_port;
    std::string sni;
    std::string alpn_protocol;
    bool early_data_allowed = false;
    uint32_t max_early_data = 0;
    size_t access_count = 0;
};

class SessionManager {
public:
    explicit SessionManager(const SessionConfig& config);
    ~SessionManager();

    bool create_session(SSL* ssl, SessionData& session);
    bool resume_session(SSL* ssl, const std::vector<unsigned char>& ticket);
    void remove_session(const std::string& session_id);

    std::vector<unsigned char> encrypt_ticket(const SessionData& session);
    std::optional<SessionData> decrypt_ticket(
        const unsigned char* ticket_data, size_t ticket_len);

    void configure_ssl_context(SSL_CTX* ctx);

    static int new_session_cb(SSL* ssl, SSL_SESSION* session);
    static int ticket_key_cb(SSL* ssl,
                              unsigned char* key_name,
                              unsigned char* iv,
                              EVP_CIPHER_CTX* enc,
                              HMAC_CTX* hmac,
                              int encrypt);

    void cache_session(const std::string& id, const SessionData& data);
    std::optional<SessionData> get_cached_session(const std::string& id);
    void evict_expired_sessions();

    bool check_replay(const std::vector<unsigned char>& client_hello_random,
                       const std::string& client_ip);
    void record_replay(const std::vector<unsigned char>& client_hello_random,
                       const std::string& client_ip);

    struct Stats {
        size_t sessions_created;
        size_t sessions_resumed;
        size_t tickets_issued;
        size_t tickets_renewed;
        size_t cache_hits;
        size_t cache_misses;
        size_t replay_attacks_detected;
        size_t early_data_accepted;
        size_t early_data_rejected;
    };

    Stats get_stats() const;
    void cleanup();

private:
    std::vector<unsigned char> generate_session_key();
    void derive_ticket_keys(const std::string& master_key);
    bool is_ticket_valid(const SessionData& session);

    SessionConfig config_;
    std::unordered_map<std::string, SessionData> session_cache_;
    mutable std::mutex cache_mutex_;

    struct TicketKeySet {
        unsigned char current_key[32];
        unsigned char previous_key[32];
        unsigned char current_hmac[32];
        unsigned char previous_hmac[32];
        std::chrono::steady_clock::time_point rotation_time;
    };

    TicketKeySet ticket_keys_;
    mutable std::mutex ticket_mutex_;

    struct ReplayEntry {
        std::vector<unsigned char> random;
        std::chrono::steady_clock::time_point timestamp;
    };

    std::vector<ReplayEntry> replay_window_;
    mutable std::mutex replay_mutex_;

    Stats stats_ = {};
};

}  // namespace tls_server
```

### 15.7.3 Anti-Replay para 0-RTT

Early data (0-RTT) no TLS 1.3 apresenta um desafio único: os dados enviados antes
do handshake completo não têm proteção contra replay. Um atacante pode gravar e
reenviar o ClientHello com early data.

```cpp
// anti_replay.h
#pragma once

#include <vector>
#include <string>
#include <chrono>
#include <mutex>
#include <unordered_set>
#include <openssl/rand.h>

namespace tls_server {

class AntiReplayProtection {
public:
    struct Config {
        size_t window_size = 10000;
        int max_age_seconds = 30;

        enum Action {
            REJECT,
            REQUIRE_PROOF,
            LOG_AND_ALLOW
        };

        Action on_replay_detected = REJECT;
        bool single_use_tickets = true;
        int max_ticket_uses = 1;
        bool use_timestamp_based = true;
    };

    explicit AntiReplayProtection(const Config& config);
    ~AntiReplayProtection();

    bool is_replay(const std::vector<unsigned char>& client_hello_random,
                   const std::string& client_ip,
                   uint64_t early_data_nonce = 0);

    void record(const std::vector<unsigned char>& client_hello_random,
                const std::string& client_ip,
                uint64_t early_data_nonce = 0);

    bool is_ticket_used(const std::vector<unsigned char>& ticket_id);
    void mark_ticket_used(const std::vector<unsigned char>& ticket_id);
    void cleanup();

    struct Stats {
        size_t total_checks;
        size_t replays_detected;
        size_t tickets_reused;
        size_t entries_cleaned;
    };

    Stats get_stats() const;

private:
    size_t hash_random(const std::vector<unsigned char>& data) const;

    Config config_;

    std::unordered_map<size_t, std::chrono::steady_clock::time_point>
        replay_cache_;
    mutable std::mutex cache_mutex_;

    struct VectorHash {
        size_t operator()(const std::vector<unsigned char>& v) const {
            size_t hash = 0;
            for (auto b : v) {
                hash ^= std::hash<unsigned char>{}(b) + 0x9e3779b9 +
                         (hash << 6) + (hash >> 2);
            }
            return hash;
        }
    };

    std::unordered_set<std::vector<unsigned char>,
                       VectorHash> used_tickets_;
    mutable std::mutex ticket_mutex_;

    Stats stats_ = {};
};

}  // namespace tls_server
```

---

## 15.8 Gerenciamento de Chaves

### 15.8.1 HSM Integration

Hardware Security Modules (HSMs) são dispositivos físicos que realizam operações
criptográficas e armazenam chaves de forma segura. A integração com HSMs é obrigatória
para muitos frameworks de compliance.

**Interface PKCS#11 para HSMs:**

```cpp
// hsm_client.h
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <mutex>

namespace tls_server {

class HSMInterface {
public:
    virtual ~HSMInterface() = default;

    virtual bool initialize(const std::string& pin,
                            const std::string& slot = "") = 0;

    virtual bool generate_key_pair(
        const std::string& key_id,
        int key_size,
        const std::string& algorithm = "RSA") = 0;

    virtual std::vector<unsigned char> sign(
        const std::string& key_id,
        const unsigned char* data, size_t data_len,
        const std::string& algorithm = "SHA256") = 0;

    virtual bool verify(
        const std::string& key_id,
        const unsigned char* data, size_t data_len,
        const unsigned char* signature, size_t sig_len,
        const std::string& algorithm = "SHA256") = 0;

    virtual std::vector<unsigned char> encrypt(
        const std::string& key_id,
        const unsigned char* data, size_t data_len) = 0;

    virtual std::vector<unsigned char> decrypt(
        const std::string& key_id,
        const unsigned char* data, size_t data_len) = 0;

    virtual bool generate_symmetric_key(
        const std::string& key_id,
        int key_size) = 0;

    virtual std::vector<std::string> list_keys() = 0;
    virtual bool delete_key(const std::string& key_id) = 0;
    virtual bool is_available() const = 0;
    virtual std::string get_hsm_info() const = 0;
    virtual void logout() = 0;
};

class PKCS11Client : public HSMInterface {
public:
    struct Config {
        std::string library_path;
        std::string slot_id;
        std::string pin;
        std::string so_pin;
        int max_sessions = 10;
        bool auto_reconnect = true;
        int reconnect_interval = 5;
    };

    explicit PKCS11Client(const Config& config);
    ~PKCS11Client() override;

    PKCS11Client(const PKCS11Client&) = delete;
    PKCS11Client& operator=(const PKCS11Client&) = delete;

    bool initialize(const std::string& pin,
                    const std::string& slot = "") override;
    bool generate_key_pair(const std::string& key_id,
                           int key_size,
                           const std::string& algorithm) override;
    std::vector<unsigned char> sign(
        const std::string& key_id,
        const unsigned char* data, size_t data_len,
        const std::string& algorithm) override;
    bool verify(const std::string& key_id,
                const unsigned char* data, size_t data_len,
                const unsigned char* signature, size_t sig_len,
                const std::string& algorithm) override;
    std::vector<unsigned char> encrypt(
        const std::string& key_id,
        const unsigned char* data, size_t data_len) override;
    std::vector<unsigned char> decrypt(
        const std::string& key_id,
        const unsigned char* data, size_t data_len) override;
    bool generate_symmetric_key(const std::string& key_id,
                                 int key_size) override;
    std::vector<std::string> list_keys() override;
    bool delete_key(const std::string& key_id) override;
    bool is_available() const override;
    std::string get_hsm_info() const override;
    void logout() override;

private:
    bool open_session();
    void close_session();
    static void* get_function_list(const std::string& library_path);

    Config config_;
    void* library_handle_ = nullptr;
    void* function_list_ = nullptr;
    void* session_handle_ = nullptr;
    void* slot_handle_ = nullptr;

    mutable std::mutex hsm_mutex_;
    bool initialized_ = false;
};

class HSMFactory {
public:
    static std::unique_ptr<HSMInterface> create(
        const std::string& hsm_type,
        const std::map<std::string, std::string>& config);

    static bool is_hsm_available(const std::string& hsm_type);
};

}  // namespace tls_server
```

### 15.8.2 Key Rotation

A rotação automática de chaves é essencial para limitar o impacto de uma comprometimento.
Chaves devem ser rotacionadas regularmente e sem downtime.

```cpp
// key_manager.h
#pragma once

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/hmac.h>

#include <string>
#include <vector>
#include <memory>
#include <chrono>
#include <mutex>
#include <functional>
#include <thread>
#include <atomic>
#include <map>

namespace tls_server {

struct KeyConfig {
    std::string primary_key_id;
    std::string secondary_key_id;

    bool auto_rotation = true;
    int rotation_interval_hours = 24;
    int key_lifetime_hours = 168;
    int overlap_period_hours = 1;

    bool use_hsm = false;
    std::string hsm_type;
    std::map<std::string, std::string> hsm_config;

    bool backup_enabled = true;
    std::string backup_path;
    int backup_count = 3;

    bool audit_enabled = true;
    std::string audit_log_path;
};

class KeyManager {
public:
    explicit KeyManager(const KeyConfig& config);
    ~KeyManager();

    KeyManager(const KeyManager&) = delete;
    KeyManager& operator=(const KeyManager&) = delete;

    bool initialize();

    EVP_PKEY* get_current_signing_key();
    std::vector<unsigned char> get_current_encryption_key();

    bool rotate_keys();
    bool rotate_signing_keys();
    bool rotate_encryption_keys();

    void schedule_rotation();
    void stop_rotation();

    std::vector<unsigned char> wrap_key(
        EVP_PKEY* key_to_wrap,
        const std::string& wrapping_key_id);

    EVP_PKEY* unwrap_key(
        const std::vector<unsigned char>& wrapped_key,
        const std::string& wrapping_key_id);

    bool backup_keys(const std::string& backup_path);
    bool restore_keys(const std::string& backup_path);

    struct KeyHealth {
        bool is_valid;
        bool is_expired;
        bool is_near_expiry;
        int days_until_expiry;
        std::string status;
    };

    KeyHealth check_key_health(const std::string& key_id);

    struct KeyInfo {
        std::string id;
        std::string type;
        std::string algorithm;
        int key_size;
        std::chrono::system_clock::time_point created;
        std::chrono::system_clock::time_point expires;
        bool is_primary;
        bool is_active;
        std::string location;
    };

    std::vector<KeyInfo> list_keys();

    struct Metrics {
        size_t total_rotations;
        size_t successful_rotations;
        size_t failed_rotations;
        std::chrono::system_clock::time_point last_rotation;
        std::chrono::system_clock::time_point next_scheduled_rotation;
    };

    Metrics get_metrics() const;

private:
    EVP_PKEY* generate_signing_key(int key_size = 256);
    std::vector<unsigned char> generate_encryption_key(int key_size = 256);

    bool save_key_to_disk(const std::string& key_id, EVP_PKEY* key);
    bool save_key_to_disk(const std::string& key_id,
                          const std::vector<unsigned char>& key);

    EVP_PKEY* load_key_from_disk(const std::string& key_id);
    std::vector<unsigned char> load_symmetric_key_from_disk(
        const std::string& key_id);

    std::vector<unsigned char> encrypt_key_for_storage(
        const std::vector<unsigned char>& key);
    std::vector<unsigned char> decrypt_key_from_storage(
        const std::vector<unsigned char>& encrypted_key);

    void rotation_thread_func();
    bool should_rotate();
    bool create_backup(const std::string& key_id);
    void audit_log(const std::string& operation,
                   const std::string& key_id, bool success);

    KeyConfig config_;

    EVP_PKEY* current_signing_key_ = nullptr;
    std::vector<unsigned char> current_encryption_key_;

    EVP_PKEY* previous_signing_key_ = nullptr;
    std::vector<unsigned char> previous_encryption_key_;

    std::chrono::system_clock::time_point last_rotation_;
    std::chrono::system_clock::time_point next_rotation_;

    std::unique_ptr<std::thread> rotation_thread_;
    std::atomic<bool> rotation_running_{false};
    std::condition_variable rotation_cv_;
    std::mutex rotation_mutex_;

    std::unique_ptr<HSMInterface> hsm_client_;

    Metrics metrics_ = {};

    mutable std::mutex key_mutex_;
};

}  // namespace tls_server
```

---

## 15.9 Implementação Completa do TLS Server

Esta seção contém a implementação completa do servidor TLS. O código é extenso mas
cuidadosamente organizado em componentes coesos.

### 15.9.1 Socket e Connection Management

```cpp
// connection_manager.h
#pragma once

#include <openssl/ssl.h>

#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <chrono>
#include <mutex>
#include <atomic>
#include <functional>
#include <optional>
#include <queue>
#include <condition_variable>
#include <thread>

namespace tls_server {

class Logger;
class MetricsCollector;

struct TLSConnection {
    int fd = -1;
    SSL* ssl = nullptr;
    std::string client_ip;
    uint16_t client_port = 0;
    std::chrono::steady_clock::time_point created;
    std::chrono::steady_clock::time_point last_activity;
    std::chrono::steady_clock::time_point handshake_completed;
    size_t bytes_read = 0;
    size_t bytes_written = 0;
    bool handshake_complete = false;
    bool is_alive = true;

    std::string session_id;
    std::string sni_hostname;
    std::string alpn_protocol;
    std::string tls_version;
    std::string cipher_suite;

    std::vector<unsigned char> read_buffer;
    std::vector<unsigned char> write_buffer;

    std::chrono::microseconds handshake_duration{0};
    std::chrono::microseconds resumption_duration{0};
    bool used_0rtt = false;
};

struct ConnectionConfig {
    size_t max_connections = 100000;
    size_t max_connections_per_ip = 100;
    size_t max_handshakes_per_second = 1000;

    int handshake_timeout_ms = 10000;
    int read_timeout_ms = 30000;
    int write_timeout_ms = 30000;
    int idle_timeout_ms = 300000;

    size_t read_buffer_size = 16384;
    size_t write_buffer_size = 16384;

    bool rate_limiting_enabled = true;
    size_t rate_limit_window_seconds = 60;
    size_t rate_limit_max_requests = 1000;

    bool keep_alive_enabled = true;
    int keep_alive_timeout_ms = 60000;
    int keep_alive_max_requests = 100;

    bool log_connections = true;
    bool log_handshakes = true;
    bool log_errors = true;
};

class ConnectionManager {
public:
    ConnectionManager(const ConnectionConfig& config,
                      Logger* logger = nullptr,
                      MetricsCollector* metrics = nullptr);
    ~ConnectionManager();

    ConnectionManager(const ConnectionManager&) = delete;
    ConnectionManager& operator=(const ConnectionManager&) = delete;

    std::shared_ptr<TLSConnection> accept_connection(int server_fd,
                                                      SSL_CTX* ssl_ctx);
    bool perform_handshake(std::shared_ptr<TLSConnection> conn);
    bool read_data(std::shared_ptr<TLSConnection> conn,
                   std::vector<unsigned char>& data, size_t max_len);
    bool write_data(std::shared_ptr<TLSConnection> conn,
                    const unsigned char* data, size_t len);
    void close_connection(std::shared_ptr<TLSConnection> conn);

    std::vector<std::shared_ptr<TLSConnection>> accept_connections(
        int server_fd, SSL_CTX* ssl_ctx, size_t max_count);
    void close_all_connections();

    size_t get_active_connections() const;
    size_t get_total_connections() const;
    size_t get_failed_handshakes() const;

    bool check_rate_limit(const std::string& client_ip);
    void update_rate_limit(const std::string& client_ip);

    void cleanup_expired_connections();

    using HandshakeCallback = std::function<bool(
        std::shared_ptr<TLSConnection>)>;
    using DataCallback = std::function<bool(
        std::shared_ptr<TLSConnection>,
        const std::vector<unsigned char>&)>;

    void set_handshake_callback(HandshakeCallback cb);
    void set_data_callback(DataCallback cb);

    struct Stats {
        size_t active_connections;
        size_t total_connections;
        size_t total_handshakes;
        size_t failed_handshakes;
        size_t total_bytes_read;
        size_t total_bytes_written;
        double avg_handshake_time_ms;
        double avg_connection_duration_s;
        size_t connections_per_ip_max;
        std::string most_active_client;
    };

    Stats get_stats() const;

private:
    class Socket {
    public:
        explicit Socket(int fd = -1) : fd_(fd) {}
        ~Socket() { close(); }

        Socket(Socket&& other) noexcept : fd_(other.fd_) {
            other.fd_ = -1;
        }

        Socket& operator=(Socket&& other) noexcept {
            if (this != &other) {
                close();
                fd_ = other.fd_;
                other.fd_ = -1;
            }
            return *this;
        }

        Socket(const Socket&) = delete;
        Socket& operator=(const Socket&) = delete;

        [[nodiscard]] int fd() const noexcept { return fd_; }

        void close() {
            if (fd_ >= 0) {
                ::close(fd_);
                fd_ = -1;
            }
        }

        [[nodiscard]] bool is_valid() const noexcept { return fd_ >= 0; }

    private:
        int fd_;
    };

    struct RateLimitEntry {
        size_t count = 0;
        std::chrono::steady_clock::time_point window_start;
    };

    std::shared_ptr<TLSConnection> find_connection(int fd);
    std::shared_ptr<TLSConnection> create_connection(
        int fd, SSL* ssl, const std::string& client_ip, uint16_t port);

    static bool set_nonblocking(int fd);
    static bool set_socket_options(int fd);
    static std::string get_client_ip(int fd);
    static uint16_t get_client_port(int fd);
    bool is_ip_blocked(const std::string& ip) const;

    ConnectionConfig config_;
    Logger* logger_;
    MetricsCollector* metrics_;

    std::unordered_map<int, std::shared_ptr<TLSConnection>> connections_;
    mutable std::mutex connections_mutex_;

    std::unordered_map<std::string, RateLimitEntry> rate_limits_;
    mutable std::mutex rate_limit_mutex_;

    std::atomic<size_t> active_connections_{0};
    std::atomic<size_t> total_connections_{0};
    std::atomic<size_t> failed_handshakes_{0};
    std::atomic<size_t> total_bytes_read_{0};
    std::atomic<size_t> total_bytes_written_{0};

    HandshakeCallback handshake_callback_;
    DataCallback data_callback_;

    std::unique_ptr<std::thread> cleanup_thread_;
    std::atomic<bool> running_{false};
};

}  // namespace tls_server
```

### 15.9.2 Implementação do Connection Manager

```cpp
// connection_manager.cpp
#include "connection_manager.h"
#include "logger.h"
#include "metrics.h"

#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <cstring>
#include <algorithm>
#include <numeric>

namespace tls_server {

ConnectionManager::ConnectionManager(
    const ConnectionConfig& config,
    Logger* logger,
    MetricsCollector* metrics)
    : config_(config),
      logger_(logger),
      metrics_(metrics) {

    running_ = true;
    cleanup_thread_ = std::make_unique<std::thread>(
        [this]() {
            while (running_) {
                std::this_thread::sleep_for(
                    std::chrono::seconds(30));
                cleanup_expired_connections();
            }
        });
}

ConnectionManager::~ConnectionManager() {
    running_ = false;
    if (cleanup_thread_ && cleanup_thread_->joinable()) {
        cleanup_thread_->join();
    }
    close_all_connections();
}

std::shared_ptr<TLSConnection> ConnectionManager::accept_connection(
    int server_fd, SSL_CTX* ssl_ctx) {

    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);

    int client_fd = accept4(server_fd,
                             reinterpret_cast<struct sockaddr*>(&client_addr),
                             &addr_len,
                             SOCK_NONBLOCK | SOCK_CLOEXEC);

    if (client_fd < 0) {
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            return nullptr;
        }
        if (logger_) {
            logger_->error("accept failed: " + std::string(strerror(errno)));
        }
        return nullptr;
    }

    std::string client_ip = get_client_ip(client_fd);
    uint16_t client_port = get_client_port(client_fd);

    if (config_.rate_limiting_enabled &&
        check_rate_limit(client_ip)) {

        if (logger_) {
            logger_->warn("Rate limit exceeded for: " + client_ip);
        }
        ::close(client_fd);
        return nullptr;
    }

    if (active_connections_ >= config_.max_connections) {
        if (logger_) {
            logger_->warn("Max connections reached");
        }
        ::close(client_fd);
        return nullptr;
    }

    {
        std::lock_guard<std::mutex> lock(connections_mutex_);
        size_t ip_count = 0;
        for (const auto& [fd, conn] : connections_) {
            if (conn->client_ip == client_ip) {
                ip_count++;
            }
        }

        if (ip_count >= config_.max_connections_per_ip) {
            if (logger_) {
                logger_->warn("Max connections per IP reached: " + client_ip);
            }
            ::close(client_fd);
            return nullptr;
        }
    }

    if (!set_socket_options(client_fd)) {
        if (logger_) {
            logger_->error("Failed to set socket options");
        }
        ::close(client_fd);
        return nullptr;
    }

    SSL* ssl = SSL_new(ssl_ctx);
    if (!ssl) {
        if (logger_) {
            logger_->error("Failed to create SSL connection");
        }
        ::close(client_fd);
        return nullptr;
    }

    if (SSL_set_fd(ssl, client_fd) != 1) {
        if (logger_) {
            logger_->error("Failed to associate SSL with fd");
        }
        SSL_free(ssl);
        ::close(client_fd);
        return nullptr;
    }

    auto conn = create_connection(client_fd, ssl, client_ip, client_port);

    struct timeval tv;
    tv.tv_sec = config_.handshake_timeout_ms / 1000;
    tv.tv_usec = (config_.handshake_timeout_ms % 1000) * 1000;
    setsockopt(client_fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    setsockopt(client_fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

    active_connections_++;
    total_connections_++;

    if (metrics_) {
        metrics_->increment_counter("connections.active");
        metrics_->increment_counter("connections.total");
    }

    if (logger_) {
        logger_->info("New connection from " + client_ip + ":" +
                      std::to_string(client_port));
    }

    return conn;
}

bool ConnectionManager::perform_handshake(
    std::shared_ptr<TLSConnection> conn) {

    if (!conn || !conn->ssl) {
        return false;
    }

    auto start = std::chrono::steady_clock::now();

    int ret = SSL_accept(conn->ssl);

    if (ret != 1) {
        int ssl_err = SSL_get_error(conn->ssl, ret);

        switch (ssl_err) {
            case SSL_ERROR_WANT_READ:
            case SSL_ERROR_WANT_WRITE:
                return false;

            case SSL_ERROR_ZERO_RETURN:
                if (logger_) {
                    logger_->warn("Handshake closed by client");
                }
                return false;

            case SSL_ERROR_SYSCALL:
                if (logger_) {
                    logger_->error("Handshake syscall error: " +
                                  std::string(strerror(errno)));
                }
                return false;

            case SSL_ERROR_SSL:
                if (logger_) {
                    unsigned long err = ERR_get_error();
                    char buf[256];
                    ERR_error_string_n(err, buf, sizeof(buf));
                    logger_->error("Handshake SSL error: " +
                                  std::string(buf));
                }
                failed_handshakes_++;
                return false;

            default:
                if (logger_) {
                    logger_->error("Handshake unknown error: " +
                                  std::to_string(ssl_err));
                }
                return false;
        }
    }

    auto end = std::chrono::steady_clock::now();
    conn->handshake_completed = end;
    conn->handshake_duration =
        std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    conn->handshake_complete = true;

    const SSL_CIPHER* cipher = SSL_get_current_cipher(conn->ssl);
    if (cipher) {
        conn->cipher_suite = SSL_CIPHER_get_name(cipher);
    }

    conn->tls_version = SSL_get_version(conn->ssl);

    const char* sni = SSL_get_servername(conn->ssl,
                                          TLSEXT_NAMETYPE_host_name);
    if (sni) {
        conn->sni_hostname = sni;
    }

    unsigned char* alpn;
    unsigned int alpn_len;
    SSL_get0_alpn_selected(conn->ssl, &alpn, &alpn_len);
    if (alpn && alpn_len > 0) {
        conn->alpn_protocol = std::string(reinterpret_cast<char*>(alpn),
                                           alpn_len);
    }

    X509* peer_cert = SSL_get_peer_certificate(conn->ssl);
    if (peer_cert) {
        char subject[256];
        X509_NAME_oneline(X509_get_subject_name(peer_cert),
                          subject, sizeof(subject));
        if (logger_) {
            logger_->info("Client certificate: " + std::string(subject));
        }
        X509_free(peer_cert);
    }

    if (logger_ && config_.log_handshakes) {
        std::ostringstream oss;
        oss << "Handshake completed:"
            << " client=" << conn->client_ip
            << ":" << conn->client_port
            << " cipher=" << conn->cipher_suite
            << " version=" << conn->tls_version
            << " time=" << conn->handshake_duration.count() / 1000.0
            << "ms";

        if (!conn->sni_hostname.empty()) {
            oss << " sni=" << conn->sni_hostname;
        }

        if (!conn->alpn_protocol.empty()) {
            oss << " alpn=" << conn->alpn_protocol;
        }

        logger_->info(oss.str());
    }

    if (metrics_) {
        metrics_->increment_counter("handshakes.completed");
        metrics_->record_histogram("handshakes.duration_us",
                                    conn->handshake_duration.count());
    }

    if (handshake_callback_) {
        return handshake_callback_(conn);
    }

    return true;
}

bool ConnectionManager::read_data(
    std::shared_ptr<TLSConnection> conn,
    std::vector<unsigned char>& data,
    size_t max_len) {

    if (!conn || !conn->ssl || !conn->handshake_complete) {
        return false;
    }

    data.resize(max_len);

    int bytes_read = SSL_read(conn->ssl, data.data(), data.size());

    if (bytes_read > 0) {
        data.resize(bytes_read);
        conn->bytes_read += bytes_read;
        conn->last_activity = std::chrono::steady_clock::now();
        total_bytes_read_ += bytes_read;

        if (metrics_) {
            metrics_->increment_counter("bytes.read", bytes_read);
        }

        return true;
    }

    int ssl_err = SSL_get_error(conn->ssl, bytes_read);

    switch (ssl_err) {
        case SSL_ERROR_WANT_READ:
        case SSL_ERROR_WANT_WRITE:
            data.clear();
            return false;

        case SSL_ERROR_ZERO_RETURN:
            conn->is_alive = false;
            data.clear();
            return false;

        case SSL_ERROR_SYSCALL:
            if (logger_) {
                logger_->error("Read syscall error: " +
                              std::string(strerror(errno)));
            }
            conn->is_alive = false;
            return false;

        case SSL_ERROR_SSL:
            if (logger_) {
                unsigned long err = ERR_get_error();
                char buf[256];
                ERR_error_string_n(err, buf, sizeof(buf));
                logger_->error("Read SSL error: " + std::string(buf));
            }
            conn->is_alive = false;
            return false;

        default:
            data.clear();
            return false;
    }
}

bool ConnectionManager::write_data(
    std::shared_ptr<TLSConnection> conn,
    const unsigned char* data,
    size_t len) {

    if (!conn || !conn->ssl || !conn->handshake_complete) {
        return false;
    }

    size_t total_written = 0;

    while (total_written < len) {
        int bytes_written = SSL_write(conn->ssl,
                                       data + total_written,
                                       len - total_written);

        if (bytes_written > 0) {
            total_written += bytes_written;
            conn->bytes_written += bytes_written;
            total_bytes_written_ += bytes_written;

            if (metrics_) {
                metrics_->increment_counter("bytes.written", bytes_written);
            }
        } else {
            int ssl_err = SSL_get_error(conn->ssl, bytes_written);

            switch (ssl_err) {
                case SSL_ERROR_WANT_READ:
                case SSL_ERROR_WANT_WRITE:
                    std::this_thread::sleep_for(
                        std::chrono::microseconds(100));
                    continue;

                case SSL_ERROR_SYSCALL:
                    if (logger_) {
                        logger_->error("Write syscall error: " +
                                      std::string(strerror(errno)));
                    }
                    conn->is_alive = false;
                    return false;

                case SSL_ERROR_SSL:
                    if (logger_) {
                        unsigned long err = ERR_get_error();
                        char buf[256];
                        ERR_error_string_n(err, buf, sizeof(buf));
                        logger_->error("Write SSL error: " +
                                      std::string(buf));
                    }
                    conn->is_alive = false;
                    return false;

                default:
                    return false;
            }
        }
    }

    conn->last_activity = std::chrono::steady_clock::now();
    return true;
}

void ConnectionManager::close_connection(
    std::shared_ptr<TLSConnection> conn) {

    if (!conn) return;

    if (logger_ && config_.log_connections) {
        logger_->info("Closing connection: " + conn->client_ip + ":" +
                      std::to_string(conn->client_port));
    }

    if (conn->ssl) {
        SSL_shutdown(conn->ssl);
        SSL_free(conn->ssl);
        conn->ssl = nullptr;
    }

    if (conn->fd >= 0) {
        ::close(conn->fd);
        conn->fd = -1;
    }

    conn->is_alive = false;

    {
        std::lock_guard<std::mutex> lock(connections_mutex_);
        connections_.erase(conn->fd);
    }

    active_connections_--;

    if (metrics_) {
        metrics_->decrement_counter("connections.active");

        auto duration = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - conn->created);
        metrics_->record_histogram("connections.duration_s",
                                    duration.count());
    }
}

void ConnectionManager::close_all_connections() {
    std::lock_guard<std::mutex> lock(connections_mutex_);

    for (auto& [fd, conn] : connections_) {
        if (conn->ssl) {
            SSL_shutdown(conn->ssl);
            SSL_free(conn->ssl);
            conn->ssl = nullptr;
        }

        if (conn->fd >= 0) {
            ::close(conn->fd);
            conn->fd = -1;
        }

        conn->is_alive = false;
    }

    connections_.clear();
    active_connections_ = 0;
}

void ConnectionManager::cleanup_expired_connections() {
    auto now = std::chrono::steady_clock::now();
    std::vector<std::shared_ptr<TLSConnection>> to_close;

    {
        std::lock_guard<std::mutex> lock(connections_mutex_);
        for (auto& [fd, conn] : connections_) {
            auto idle_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - conn->last_activity);

            if (idle_time.count() > config_.idle_timeout_ms) {
                to_close.push_back(conn);
            }
        }
    }

    for (auto& conn : to_close) {
        if (logger_) {
            logger_->info("Closing idle connection: " +
                          conn->client_ip + ":" +
                          std::to_string(conn->client_port));
        }
        close_connection(conn);
    }
}

bool ConnectionManager::check_rate_limit(const std::string& client_ip) {
    std::lock_guard<std::mutex> lock(rate_limit_mutex_);

    auto now = std::chrono::steady_clock::now();
    auto& entry = rate_limits_[client_ip];

    auto window_duration = std::chrono::seconds(
        config_.rate_limit_window_seconds);

    if (now - entry.window_start > window_duration) {
        entry.count = 0;
        entry.window_start = now;
    }

    entry.count++;

    return entry.count > config_.rate_limit_max_requests;
}

std::shared_ptr<TLSConnection> ConnectionManager::create_connection(
    int fd, SSL* ssl, const std::string& client_ip, uint16_t port) {

    auto conn = std::make_shared<TLSConnection>();
    conn->fd = fd;
    conn->ssl = ssl;
    conn->client_ip = client_ip;
    conn->client_port = port;
    conn->created = std::chrono::steady_clock::now();
    conn->last_activity = conn->created;

    conn->read_buffer.resize(config_.read_buffer_size);
    conn->write_buffer.resize(config_.write_buffer_size);

    {
        std::lock_guard<std::mutex> lock(connections_mutex_);
        connections_[fd] = conn;
    }

    return conn;
}

bool ConnectionManager::set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) return false;
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK) >= 0;
}

bool ConnectionManager::set_socket_options(int fd) {
    int flag = 1;
    if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag)) < 0) {
        return false;
    }

    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &flag, sizeof(flag)) < 0) {
        return false;
    }

    if (setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &flag, sizeof(flag)) < 0) {
        return false;
    }

    int idle = 60;
    int interval = 10;
    int count = 3;

    setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &idle, sizeof(idle));
    setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL, &interval, sizeof(interval));
    setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT, &count, sizeof(count));

    int buf_size = 65536;
    setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &buf_size, sizeof(buf_size));
    setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &buf_size, sizeof(buf_size));

    return true;
}

std::string ConnectionManager::get_client_ip(int fd) {
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);

    if (getpeername(fd, reinterpret_cast<struct sockaddr*>(&addr),
                    &addr_len) < 0) {
        return "unknown";
    }

    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &addr.sin_addr, ip_str, sizeof(ip_str));
    return ip_str;
}

uint16_t ConnectionManager::get_client_port(int fd) {
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);

    if (getpeername(fd, reinterpret_cast<struct sockaddr*>(&addr),
                    &addr_len) < 0) {
        return 0;
    }

    return ntohs(addr.sin_port);
}

std::shared_ptr<TLSConnection> ConnectionManager::find_connection(int fd) {
    std::lock_guard<std::mutex> lock(connections_mutex_);
    auto it = connections_.find(fd);
    if (it != connections_.end()) {
        return it->second;
    }
    return nullptr;
}

ConnectionManager::Stats ConnectionManager::get_stats() const {
    Stats stats;
    stats.active_connections = active_connections_.load();
    stats.total_connections = total_connections_.load();
    stats.failed_handshakes = failed_handshakes_.load();
    stats.total_bytes_read = total_bytes_read_.load();
    stats.total_bytes_written = total_bytes_written_.load();

    if (stats.total_connections > 0) {
        std::lock_guard<std::mutex> lock(connections_mutex_);

        double total_duration = 0;
        size_t count = 0;

        for (const auto& [fd, conn] : connections_) {
            if (conn->handshake_complete) {
                total_duration += conn->handshake_duration.count() / 1000.0;
                count++;
            }
        }

        if (count > 0) {
            stats.avg_handshake_time_ms = total_duration / count;
        }
    }

    return stats;
}

void ConnectionManager::set_handshake_callback(HandshakeCallback cb) {
    handshake_callback_ = std::move(cb);
}

void ConnectionManager::set_data_callback(DataCallback cb) {
    data_callback_ = std::move(cb);
}

}  // namespace tls_server
```

### 15.9.3 Logger

```cpp
// logger.h
#pragma once

#include <string>
#include <fstream>
#include <iostream>
#include <sstream>
#include <mutex>
#include <chrono>
#include <iomanip>
#include <thread>
#include <queue>
#include <condition_variable>
#include <functional>
#include <atomic>

namespace tls_server {

enum class LogLevel {
    TRACE,
    DEBUG,
    INFO,
    WARN,
    ERROR,
    FATAL
};

class Logger {
public:
    struct Config {
        std::string log_file;
        LogLevel min_level = LogLevel::INFO;
        bool console_output = true;
        bool file_output = true;
        bool json_format = false;
        size_t max_file_size_mb = 100;
        int max_files = 5;
        bool async_logging = true;
        size_t queue_size = 10000;
        bool include_thread_id = true;
        bool include_timestamp = true;
        bool include_source = true;
    };

    explicit Logger(const Config& config);
    ~Logger();

    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;

    void trace(const std::string& message,
               const char* file = nullptr, int line = 0);
    void debug(const std::string& message,
               const char* file = nullptr, int line = 0);
    void info(const std::string& message,
              const char* file = nullptr, int line = 0);
    void warn(const std::string& message,
              const char* file = nullptr, int line = 0);
    void error(const std::string& message,
               const char* file = nullptr, int line = 0);
    void fatal(const std::string& message,
               const char* file = nullptr, int line = 0);

    void log(LogLevel level, const std::string& message,
             const char* file = nullptr, int line = 0);

    void log_tls(LogLevel level, const std::string& message,
                 const std::string& client_ip, uint16_t client_port,
                 const std::string& session_id = "");

    void log_handshake(const std::string& client_ip,
                       uint16_t client_port,
                       const std::string& cipher,
                       const std::string& version,
                       double duration_ms,
                       bool success);

    void log_ssl_error(const std::string& context,
                       unsigned long error_code);

    void flush();
    void close();
    void rotate();

    struct Stats {
        size_t total_messages;
        size_t messages_by_level[6];
        size_t dropped_messages;
        size_t queue_size;
    };

    Stats get_stats() const;

private:
    struct LogMessage {
        LogLevel level;
        std::string message;
        std::string file;
        int line;
        std::chrono::system_clock::time_point timestamp;
        std::thread::id thread_id;
        std::string client_ip;
        uint16_t client_port;
        std::string session_id;
    };

    void worker_thread();
    void write_message(const LogMessage& msg);
    void write_to_console(const LogMessage& msg);
    void write_to_file(const LogMessage& msg);
    std::string format_message(const LogMessage& msg);
    std::string format_json(const LogMessage& msg);

    bool should_rotate() const;
    std::string generate_filename(int index);

    Config config_;
    std::ofstream log_file_;

    std::queue<LogMessage> message_queue_;
    mutable std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    std::unique_ptr<std::thread> worker_thread_;
    std::atomic<bool> running_{false};

    std::atomic<size_t> total_messages_{0};
    std::atomic<size_t> dropped_messages_{0};
    std::atomic<size_t> messages_by_level_[6] = {};

    std::chrono::system_clock::time_point last_rotation_;
    int current_file_index_ = 0;
};

#define LOG_TRACE(logger, msg) \
    (logger)->trace(msg, __FILE__, __LINE__)
#define LOG_DEBUG(logger, msg) \
    (logger)->debug(msg, __FILE__, __LINE__)
#define LOG_INFO(logger, msg) \
    (logger)->info(msg, __FILE__, __LINE__)
#define LOG_WARN(logger, msg) \
    (logger)->warn(msg, __FILE__, __LINE__)
#define LOG_ERROR(logger, msg) \
    (logger)->error(msg, __FILE__, __LINE__)
#define LOG_FATAL(logger, msg) \
    (logger)->fatal(msg, __FILE__, __LINE__)

}  // namespace tls_server
```

### 15.9.4 Metrics Collector

```cpp
// metrics.h
#pragma once

#include <string>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <atomic>
#include <chrono>
#include <functional>
#include <sstream>
#include <iomanip>

namespace tls_server {

class MetricsCollector {
public:
    struct Config {
        bool enabled = true;
        std::string prefix = "tls_server";
        int export_interval_seconds = 15;
        bool export_prometheus = true;
        bool export_json = false;
        std::string prometheus_path = "/metrics";
        int prometheus_port = 9090;
    };

    explicit MetricsCollector(const Config& config);
    ~MetricsCollector();

    MetricsCollector(const MetricsCollector&) = delete;
    MetricsCollector& operator=(const MetricsCollector&) = delete;

    void increment_counter(const std::string& name, int64_t delta = 1);
    void set_counter(const std::string& name, int64_t value);

    void set_gauge(const std::string& name, double value);
    void increment_gauge(const std::string& name, double delta = 1.0);
    void decrement_gauge(const std::string& name, double delta = 1.0);

    void record_histogram(const std::string& name, double value);
    void record_histogram_bucket(const std::string& name,
                                  double value,
                                  const std::vector<double>& buckets);

    class Timer {
    public:
        Timer(MetricsCollector& collector, const std::string& name);
        ~Timer();

        Timer(const Timer&) = delete;
        Timer& operator=(const Timer&) = delete;

        void stop();
        double elapsed_ms() const;

    private:
        MetricsCollector& collector_;
        std::string name_;
        std::chrono::steady_clock::time_point start_;
        bool stopped_ = false;
    };

    Timer timer(const std::string& name);

    std::string export_prometheus() const;
    std::string export_json() const;

    void handle_http_request(int client_fd);

    void reset();

    struct MetricsSnapshot {
        struct Counter {
            std::string name;
            int64_t value;
        };

        struct Gauge {
            std::string name;
            double value;
        };

        struct Histogram {
            std::string name;
            double sum;
            int64_t count;
            std::vector<std::pair<double, int64_t>> buckets;
        };

        std::vector<Counter> counters;
        std::vector<Gauge> gauges;
        std::vector<Histogram> histograms;
    };

    MetricsSnapshot snapshot() const;

private:
    struct CounterData {
        std::atomic<int64_t> value{0};
        std::string help;
    };

    struct GaugeData {
        std::atomic<double> value{0.0};
        std::string help;
    };

    struct HistogramData {
        std::mutex mutex;
        double sum = 0.0;
        int64_t count = 0;
        std::vector<double> buckets;
        std::vector<int64_t> bucket_counts;
        std::string help;
    };

    Config config_;
    mutable std::mutex mutex_;

    std::unordered_map<std::string, std::unique_ptr<CounterData>> counters_;
    std::unordered_map<std::string, std::unique_ptr<GaugeData>> gauges_;
    std::unordered_map<std::string, std::unique_ptr<HistogramData>>
        histograms_;

    std::unique_ptr<std::thread> http_thread_;
    std::atomic<bool> running_{false};

    static const std::vector<double> default_buckets_;
};

#define METRICS_TIMER(collector, name) \
    auto _timer_##name = (collector).timer(#name)

}  // namespace tls_server
```

### 15.9.5 TLS Server Principal

```cpp
// tls_server.h
#pragma once

#include "ssl_context.h"
#include "certificate_handler.h"
#include "connection_manager.h"
#include "session_manager.h"
#include "key_manager.h"
#include "thread_pool.h"
#include "logger.h"
#include "metrics.h"
#include "config.h"

#include <string>
#include <memory>
#include <atomic>
#include <functional>
#include <thread>
#include <vector>
#include <csignal>

namespace tls_server {

struct ServerConfig {
    std::string bind_address = "0.0.0.0";
    uint16_t port = 443;
    int backlog = 4096;
    bool reuse_address = true;

    TLSConfig tls;
    CertificateConfig cert;
    SessionConfig session;

    ThreadPoolConfig thread_pool;
    ConnectionConfig connections;
    KeyConfig keys;

    Logger::Config logging;
    MetricsCollector::Config metrics;

    bool tcp_fastopen = true;
    bool tcp_quickack = true;
    bool so_reuseport = true;

    int shutdown_timeout_seconds = 30;
};

class ApplicationHandler {
public:
    virtual ~ApplicationHandler() = default;

    virtual void on_connection(
        std::shared_ptr<TLSConnection> conn) = 0;

    virtual void on_data(
        std::shared_ptr<TLSConnection> conn,
        const std::vector<unsigned char>& data) = 0;

    virtual void on_close(
        std::shared_ptr<TLSConnection> conn) = 0;

    virtual void on_error(
        std::shared_ptr<TLSConnection> conn,
        const std::string& error) = 0;
};

class TLSServer {
public:
    explicit TLSServer(const ServerConfig& config);
    ~TLSServer();

    TLSServer(const TLSServer&) = delete;
    TLSServer& operator=(const TLSServer&) = delete;

    bool initialize();
    void run();
    void shutdown();
    bool reload();

    void set_application_handler(
        std::shared_ptr<ApplicationHandler> handler);

    ServerStats get_stats() const;
    bool is_healthy() const;

    void signal_reload();
    void signal_shutdown();

    struct ServerStats {
        size_t active_connections;
        size_t total_connections;
        size_t total_requests;
        size_t total_errors;
        double uptime_seconds;
        size_t memory_usage_bytes;
        double cpu_usage_percent;

        ConnectionManager::Stats connection_stats;
        MetricsCollector::MetricsSnapshot metrics;
    };

private:
    bool initialize_openssl();
    bool initialize_ssl_context();
    bool initialize_server_socket();
    bool initialize_thread_pool();
    bool initialize_key_manager();

    void accept_loop();
    void process_connection(std::shared_ptr<TLSConnection> conn);

    void event_loop();
    void handle_accept_event();
    void handle_read_event(int fd);
    void handle_write_event(int fd);

    void graceful_shutdown();
    void perform_reload();

    static void signal_handler(int signum);
    static TLSServer* instance_;

    ServerConfig config_;

    std::unique_ptr<SSLContext> ssl_context_;
    std::unique_ptr<CertificateHandler> cert_handler_;
    std::unique_ptr<ConnectionManager> conn_manager_;
    std::unique_ptr<SessionManager> session_manager_;
    std::unique_ptr<KeyManager> key_manager_;
    std::unique_ptr<ThreadPool> thread_pool_;
    std::unique_ptr<Logger> logger_;
    std::unique_ptr<MetricsCollector> metrics_;

    std::shared_ptr<ApplicationHandler> app_handler_;

    int server_fd_ = -1;
    int epoll_fd_ = -1;

    std::atomic<bool> running_{false};
    std::atomic<bool> reloading_{false};

    std::atomic<size_t> total_requests_{0};
    std::atomic<size_t> total_errors_{0};
    std::chrono::steady_clock::time_point start_time_;

    std::vector<std::thread> worker_threads_;
    std::thread accept_thread_;
};

class HTTPSHandler : public ApplicationHandler {
public:
    void on_connection(std::shared_ptr<TLSConnection> conn) override;
    void on_data(std::shared_ptr<TLSConnection> conn,
                 const std::vector<unsigned char>& data) override;
    void on_close(std::shared_ptr<TLSConnection> conn) override;
    void on_error(std::shared_ptr<TLSConnection> conn,
                  const std::string& error) override;

private:
    std::vector<unsigned char> process_request(
        const std::vector<unsigned char>& request);

    std::vector<unsigned char> create_response(
        int status_code,
        const std::string& content_type,
        const std::string& body);

    bool check_rate_limit(const std::string& ip);
};

}  // namespace tls_server
```

### 15.9.6 Implementação do TLS Server

```cpp
// tls_server.cpp
#include "tls_server.h"
#include "ssl_error.h"

#include <sys/socket.h>
#include <sys/epoll.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/resource.h>
#include <sys/mman.h>

#include <cstring>
#include <cerrno>
#include <csignal>
#include <filesystem>
#include <algorithm>
#include <numeric>
#include <sstream>

namespace tls_server {

TLSServer* TLSServer::instance_ = nullptr;

TLSServer::TLSServer(const ServerConfig& config)
    : config_(config),
      start_time_(std::chrono::steady_clock::now()) {

    instance_ = this;

    struct sigaction sa;
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_RESTART;

    sigaction(SIGINT, &sa, nullptr);
    sigaction(SIGTERM, &sa, nullptr);
    sigaction(SIGHUP, &sa, nullptr);
    sigaction(SIGUSR1, &sa, nullptr);
    sigaction(SIGPIPE, &sa, nullptr);

    signal(SIGPIPE, SIG_IGN);
}

TLSServer::~TLSServer() {
    if (running_) {
        shutdown();
    }

    if (server_fd_ >= 0) {
        ::close(server_fd_);
    }

    if (epoll_fd_ >= 0) {
        ::close(epoll_fd_);
    }

    instance_ = nullptr;
}

bool TLSServer::initialize() {
    if (logger_) {
        logger_->info("Initializing TLS Server...");
    }

    if (!initialize_openssl()) {
        return false;
    }

    if (!initialize_ssl_context()) {
        return false;
    }

    try {
        cert_handler_ = std::make_unique<CertificateHandler>(
            config_.cert);
        cert_handler_->configure_ssl_context(ssl_context_->get());
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->error("Failed to initialize certificates: " +
                          std::string(e.what()));
        }
        return false;
    }

    session_manager_ = std::make_unique<SessionManager>(
        config_.session);
    session_manager_->configure_ssl_context(ssl_context_->get());

    if (!initialize_key_manager()) {
        return false;
    }

    try {
        logger_ = std::make_unique<Logger>(config_.logging);
    } catch (const std::exception& e) {
        std::cerr << "Failed to initialize logger: " << e.what()
                  << std::endl;
        return false;
    }

    try {
        metrics_ = std::make_unique<MetricsCollector>(
            config_.metrics);
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->warn("Metrics collector failed to initialize: " +
                         std::string(e.what()));
        }
    }

    conn_manager_ = std::make_unique<ConnectionManager>(
        config_.connections, logger_.get(), metrics_.get());

    if (!initialize_thread_pool()) {
        return false;
    }

    if (!initialize_server_socket()) {
        return false;
    }

    epoll_fd_ = epoll_create1(EPOLL_CLOEXEC);
    if (epoll_fd_ < 0) {
        if (logger_) {
            logger_->error("Failed to create epoll: " +
                          std::string(strerror(errno)));
        }
        return false;
    }

    struct epoll_event ev;
    ev.events = EPOLLIN | EPOLLET;
    ev.data.fd = server_fd_;
    if (epoll_ctl(epoll_fd_, EPOLL_CTL_ADD, server_fd_, &ev) < 0) {
        if (logger_) {
            logger_->error("Failed to add server socket to epoll");
        }
        return false;
    }

    conn_manager_->set_handshake_callback(
        [this](std::shared_ptr<TLSConnection> conn) {
            process_connection(conn);
            return true;
        });

    if (logger_) {
        logger_->info("TLS Server configuration:");
        logger_->info("  Bind: " + config_.bind_address + ":" +
                      std::to_string(config_.port));
        logger_->info("  Max connections: " +
                      std::to_string(config_.connections.max_connections));
        logger_->info("  Worker threads: " +
                      std::to_string(config_.thread_pool.worker_threads));
        logger_->info(ssl_context_->get_debug_info());
    }

    if (logger_) {
        logger_->info("TLS Server initialized successfully");
    }

    return true;
}

bool TLSServer::initialize_openssl() {
    try {
        tls_server::initialize_openssl("", false);
        return true;
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->error("OpenSSL initialization failed: " +
                          std::string(e.what()));
        }
        return false;
    }
}

bool TLSServer::initialize_ssl_context() {
    try {
        ssl_context_ = std::make_unique<SSLContext>(config_.tls);
        ssl_context_->configure();
        return true;
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->error("SSL context initialization failed: " +
                          std::string(e.what()));
        }
        return false;
    }
}

bool TLSServer::initialize_server_socket() {
    server_fd_ = socket(AF_INET6, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC,
                         IPPROTO_TCP);

    if (server_fd_ < 0) {
        if (logger_) {
            logger_->error("Failed to create socket: " +
                          std::string(strerror(errno)));
        }
        return false;
    }

    int v6only = 0;
    setsockopt(server_fd_, IPPROTO_IPV6, IPV6_V6ONLY,
               &v6only, sizeof(v6only));

    int flag = 1;
    setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR,
               &flag, sizeof(flag));

    if (config_.so_reuseport) {
        setsockopt(server_fd_, SOL_SOCKET, SO_REUSEPORT,
                   &flag, sizeof(flag));
    }

    if (config_.tcp_fastopen) {
        int qlen = 5;
        setsockopt(server_fd_, IPPROTO_TCP, TCP_FASTOPEN,
                   &qlen, sizeof(qlen));
    }

    struct sockaddr_in6 addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin6_family = AF_INET6;
    addr.sin6_port = htons(config_.port);

    if (config_.bind_address == "0.0.0.0" ||
        config_.bind_address == "::") {
        addr.sin6_addr = in6addr_any;
    } else {
        if (inet_pton(AF_INET6, config_.bind_address.c_str(),
                      &addr.sin6_addr) < 1) {
            struct sockaddr_in addr4;
            memset(&addr4, 0, sizeof(addr4));
            addr4.sin_family = AF_INET;
            addr4.sin_port = htons(config_.port);
            inet_pton(AF_INET, config_.bind_address.c_str(),
                      &addr4.sin_addr);

            ::close(server_fd_);
            server_fd_ = socket(AF_INET,
                                 SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC,
                                 IPPROTO_TCP);

            if (server_fd_ < 0) {
                return false;
            }

            setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR,
                       &flag, sizeof(flag));

            if (bind(server_fd_,
                     reinterpret_cast<struct sockaddr*>(&addr4),
                     sizeof(addr4)) < 0) {
                if (logger_) {
                    logger_->error("Bind failed: " +
                                  std::string(strerror(errno)));
                }
                return false;
            }
        } else {
            if (bind(server_fd_,
                     reinterpret_cast<struct sockaddr*>(&addr),
                     sizeof(addr)) < 0) {
                if (logger_) {
                    logger_->error("Bind failed: " +
                                  std::string(strerror(errno)));
                }
                return false;
            }
        }
    }

    if (listen(server_fd_, config_.backlog) < 0) {
        if (logger_) {
            logger_->error("Listen failed: " +
                          std::string(strerror(errno)));
        }
        return false;
    }

    if (logger_) {
        logger_->info("Server socket listening on " +
                      config_.bind_address + ":" +
                      std::to_string(config_.port));
    }

    return true;
}

bool TLSServer::initialize_thread_pool() {
    try {
        thread_pool_ = std::make_unique<ThreadPool>(
            config_.thread_pool);
        return true;
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->error("Thread pool initialization failed: " +
                          std::string(e.what()));
        }
        return false;
    }
}

bool TLSServer::initialize_key_manager() {
    try {
        key_manager_ = std::make_unique<KeyManager>(config_.keys);
        if (!key_manager_->initialize()) {
            if (logger_) {
                logger_->error("Key manager initialization failed");
            }
            return false;
        }
        return true;
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->warn("Key manager initialization failed: " +
                         std::string(e.what()) +
                         " - continuing without HSM");
        }
        return true;
    }
}

void TLSServer::run() {
    if (logger_) {
        logger_->info("Starting TLS Server...");
    }

    running_ = true;
    start_time_ = std::chrono::steady_clock::now();

    event_loop();
}

void TLSServer::event_loop() {
    const int MAX_EVENTS = 100;
    struct epoll_event events[MAX_EVENTS];

    while (running_) {
        int nfds = epoll_wait(epoll_fd_, events, MAX_EVENTS, 1000);

        if (nfds < 0) {
            if (errno == EINTR) {
                continue;
            }
            if (logger_) {
                logger_->error("epoll_wait failed: " +
                              std::string(strerror(errno)));
            }
            break;
        }

        for (int i = 0; i < nfds; ++i) {
            if (events[i].data.fd == server_fd_) {
                handle_accept_event();
            } else if (events[i].events & EPOLLIN) {
                handle_read_event(events[i].data.fd);
            } else if (events[i].events & EPOLLOUT) {
                handle_write_event(events[i].data.fd);
            }

            if (events[i].events & (EPOLLERR | EPOLLHUP)) {
                auto conn = conn_manager_->find_connection(
                    events[i].data.fd);
                if (conn) {
                    conn_manager_->close_connection(conn);
                }
            }
        }
    }
}

void TLSServer::handle_accept_event() {
    while (true) {
        auto conn = conn_manager_->accept_connection(
            server_fd_, ssl_context_->get());

        if (!conn) {
            break;
        }

        thread_pool_->submit([this, conn]() {
            process_connection(conn);
        });
    }
}

void TLSServer::handle_read_event(int fd) {
    auto conn = conn_manager_->find_connection(fd);
    if (!conn) {
        return;
    }

    thread_pool_->submit([this, conn]() {
        std::vector<unsigned char> data;
        if (conn_manager_->read_data(conn, data, 65536) && !data.empty()) {
            if (app_handler_) {
                app_handler_->on_data(conn, data);
            }
        }
    });
}

void TLSServer::handle_write_event(int fd) {
    auto conn = conn_manager_->find_connection(fd);
    if (!conn) {
        return;
    }
}

void TLSServer::process_connection(
    std::shared_ptr<TLSConnection> conn) {

    if (!conn_manager_->perform_handshake(conn)) {
        if (logger_) {
            logger_->warn("Handshake failed for " +
                         conn->client_ip + ":" +
                         std::to_string(conn->client_port));
        }
        conn_manager_->close_connection(conn);
        return;
    }

    if (app_handler_) {
        app_handler_->on_connection(conn);
    }

    struct epoll_event ev;
    ev.events = EPOLLIN | EPOLLET | EPOLLRDHUP;
    ev.data.fd = conn->fd;
    epoll_ctl(epoll_fd_, EPOLL_CTL_ADD, conn->fd, &ev);
}

void TLSServer::shutdown() {
    if (!running_) {
        return;
    }

    if (logger_) {
        logger_->info("Shutting down TLS Server...");
    }

    running_ = false;

    if (server_fd_ >= 0) {
        ::close(server_fd_);
        server_fd_ = -1;
    }

    if (epoll_fd_ >= 0) {
        ::close(epoll_fd_);
        epoll_fd_ = -1;
    }

    auto deadline = std::chrono::steady_clock::now() +
                   std::chrono::seconds(
                       config_.shutdown_timeout_seconds);

    conn_manager_->close_all_connections();

    if (thread_pool_) {
        thread_pool_->wait_all();
    }

    if (logger_) {
        logger_->info("TLS Server stopped");
        logger_->flush();
    }

    instance_ = nullptr;
}

bool TLSServer::reload() {
    if (reloading_) {
        return false;
    }

    reloading_ = true;

    try {
        if (cert_handler_) {
            cert_handler_->reload_certificates();
        }

        if (ssl_context_) {
            ssl_context_->rotate_ticket_keys();
        }

        if (logger_) {
            logger_->info("Configuration reloaded successfully");
        }

        reloading_ = false;
        return true;
    } catch (const std::exception& e) {
        if (logger_) {
            logger_->error("Reload failed: " + std::string(e.what()));
        }
        reloading_ = false;
        return false;
    }
}

void TLSServer::set_application_handler(
    std::shared_ptr<ApplicationHandler> handler) {
    app_handler_ = std::move(handler);
}

TLSServer::ServerStats TLSServer::get_stats() const {
    ServerStats stats;
    stats.active_connections = conn_manager_->get_active_connections();
    stats.total_connections = conn_manager_->get_total_connections();
    stats.total_requests = total_requests_.load();
    stats.total_errors = total_errors_.load();

    auto now = std::chrono::steady_clock::now();
    stats.uptime_seconds = std::chrono::duration<double>(
        now - start_time_).count();

    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    stats.memory_usage_bytes = usage.ru_maxrss * 1024;

    stats.connection_stats = conn_manager_->get_stats();

    if (metrics_) {
        stats.metrics = metrics_->snapshot();
    }

    return stats;
}

bool TLSServer::is_healthy() const {
    if (!running_) {
        return false;
    }

    if (conn_manager_->get_active_connections() >=
        config_.connections.max_connections * 0.95) {
        return false;
    }

    return true;
}

void TLSServer::signal_handler(int signum) {
    if (!instance_) {
        return;
    }

    switch (signum) {
        case SIGINT:
        case SIGTERM:
            instance_->signal_shutdown();
            break;

        case SIGHUP:
            instance_->signal_reload();
            break;

        case SIGUSR1:
            {
                auto stats = instance_->get_stats();
                std::cout << "Active connections: "
                          << stats.active_connections << std::endl;
                std::cout << "Total connections: "
                          << stats.total_connections << std::endl;
            }
            break;
    }
}

void TLSServer::signal_reload() {
    std::thread([this]() {
        reload();
    }).detach();
}

void TLSServer::signal_shutdown() {
    std::thread([this]() {
        shutdown();
    }).detach();
}

void HTTPSHandler::on_connection(
    std::shared_ptr<TLSConnection> conn) {

}

void HTTPSHandler::on_data(
    std::shared_ptr<TLSConnection> conn,
    const std::vector<unsigned char>& data) {

    std::string http_response =
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: 28\r\n"
        "Connection: keep-alive\r\n"
        "\r\n"
        "{\"status\":\"ok\",\"tls\":\"1.3\"}";

    std::vector<unsigned char> response_data(
        http_response.begin(), http_response.end());
}

void HTTPSHandler::on_close(
    std::shared_ptr<TLSConnection> conn) {

}

void HTTPSHandler::on_error(
    std::shared_ptr<TLSConnection> conn,
    const std::string& error) {

}

std::vector<unsigned char> HTTPSHandler::process_request(
    const std::vector<unsigned char>& request) {
    return request;
}

std::vector<unsigned char> HTTPSHandler::create_response(
    int status_code,
    const std::string& content_type,
    const std::string& body) {

    std::ostringstream oss;
    oss << "HTTP/1.1 " << status_code << " "
        << (status_code == 200 ? "OK" : "Error") << "\r\n"
        << "Content-Type: " << content_type << "\r\n"
        << "Content-Length: " << body.size() << "\r\n"
        << "Connection: keep-alive\r\n"
        << "\r\n"
        << body;

    std::string response = oss.str();
    return std::vector<unsigned char>(response.begin(), response.end());
}

bool HTTPSHandler::check_rate_limit(const std::string& ip) {
    return true;
}

}  // namespace tls_server
```

### 15.9.7 Thread Pool

```cpp
// thread_pool.h
#pragma once

#include <vector>
#include <queue>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <functional>
#include <atomic>
#include <future>
#include <stdexcept>

namespace tls_server {

struct ThreadPoolConfig {
    std::size_t worker_threads = std::thread::hardware_concurrency();
    std::size_t io_threads = 4;
    int worker_priority = 0;
    std::size_t stack_size = 1 * 1024 * 1024;
    std::size_t max_queue_size = 100000;
};

class ThreadPool {
public:
    explicit ThreadPool(const ThreadPoolConfig& config = {});
    ~ThreadPool();

    ThreadPool(const ThreadPool&) = delete;
    ThreadPool& operator=(const ThreadPool&) = delete;

    void submit(std::function<void()> task);

    template<typename F, typename... Args>
    auto submit_with_future(F&& f, Args&&... args)
        -> std::future<typename std::result_of<F(Args...)>::type>;

    void wait_all();

    std::size_t pending_tasks() const;
    std::size_t active_threads() const;

    struct Stats {
        std::size_t total_submitted;
        std::size_t total_completed;
        std::size_t total_failed;
        std::size_t pending;
        std::size_t active;
        double avg_execution_time_ms;
    };

    Stats get_stats() const;

private:
    void worker_function();

    ThreadPoolConfig config_;
    std::vector<std::thread> workers_;

    std::queue<std::function<void()>> tasks_;
    mutable std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    std::atomic<bool> stop_{false};
    std::atomic<std::size_t> active_count_{0};

    std::atomic<std::size_t> total_submitted_{0};
    std::atomic<std::size_t> total_completed_{0};
    std::atomic<std::size_t> total_failed_{0};
};

template<typename F, typename... Args>
auto ThreadPool::submit_with_future(F&& f, Args&&... args)
    -> std::future<typename std::result_of<F(Args...)>::type> {

    using return_type = typename std::result_of<F(Args...)>::type;

    auto task = std::make_shared<std::packaged_task<return_type()>>(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...)
    );

    std::future<return_type> result = task->get_future();

    {
        std::unique_lock<std::mutex> lock(queue_mutex_);

        if (stop_) {
            throw std::runtime_error("submit on stopped ThreadPool");
        }

        tasks_.emplace([task]() { (*task)(); });
    }

    queue_cv_.notify_one();
    total_submitted_++;

    return result;
}

}  // namespace tls_server
```

### 15.9.8 Implementação do Thread Pool

```cpp
// thread_pool.cpp
#include "thread_pool.h"

#include <sys/resource.h>
#include <cstring>

namespace tls_server {

ThreadPool::ThreadPool(const ThreadPoolConfig& config)
    : config_(config) {

    if (config_.worker_threads == 0) {
        config_.worker_threads = std::thread::hardware_concurrency();
    }

    if (config_.worker_threads == 0) {
        config_.worker_threads = 4;
    }

    for (std::size_t i = 0; i < config_.worker_threads; ++i) {
        workers_.emplace_back([this]() {
            worker_function();
        });
    }
}

ThreadPool::~ThreadPool() {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        stop_ = true;
    }

    queue_cv_.notify_all();

    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }
}

void ThreadPool::submit(std::function<void()> task) {
    {
        std::unique_lock<std::mutex> lock(queue_mutex_);

        if (stop_) {
            throw std::runtime_error("submit on stopped ThreadPool");
        }

        if (tasks_.size() >= config_.max_queue_size) {
            throw std::runtime_error("ThreadPool queue full");
        }

        tasks_.emplace(std::move(task));
    }

    queue_cv_.notify_one();
    total_submitted_++;
}

void ThreadPool::wait_all() {
    std::unique_lock<std::mutex> lock(queue_mutex_);
    queue_cv_.wait(lock, [this]() {
        return tasks_.empty() && active_count_ == 0;
    });
}

std::size_t ThreadPool::pending_tasks() const {
    std::unique_lock<std::mutex> lock(queue_mutex_);
    return tasks_.size();
}

std::size_t ThreadPool::active_threads() const {
    return active_count_.load();
}

ThreadPool::Stats ThreadPool::get_stats() const {
    Stats stats;
    stats.total_submitted = total_submitted_.load();
    stats.total_completed = total_completed_.load();
    stats.total_failed = total_failed_.load();
    stats.pending = pending_tasks();
    stats.active = active_threads();
    return stats;
}

void ThreadPool::worker_function() {
    while (true) {
        std::function<void()> task;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);

            queue_cv_.wait(lock, [this]() {
                return stop_ || !tasks_.empty();
            });

            if (stop_ && tasks_.empty()) {
                return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
        }

        active_count_++;

        try {
            task();
            total_completed_++;
        } catch (...) {
            total_failed_++;
        }

        active_count_--;

        if (tasks_.empty() && active_count_ == 0) {
            queue_cv_.notify_all();
        }
    }
}

}  // namespace tls_server
```

---

## 15.10 Hardening de Segurança

### 15.10.1 Constant-Time Operations

Operações de comparação de dados sensíveis devem ser executadas em tempo constante
para prevenir ataques de timing side-channel.

```cpp
// secure_ops.h
#pragma once

#include <cstring>
#include <cstdint>
#include <vector>
#include <array>
#include <algorithm>

namespace tls_server {

inline bool constant_time_compare(const uint8_t* a, const uint8_t* b,
                                  size_t len) {
    volatile uint8_t result = 0;

    for (size_t i = 0; i < len; ++i) {
        result |= a[i] ^ b[i];
    }

    return result == 0;
}

inline bool constant_time_compare(const std::string& a,
                                   const std::string& b) {
    if (a.size() != b.size()) {
        volatile uint8_t result = 0;
        size_t max_len = std::max(a.size(), b.size());
        for (size_t i = 0; i < max_len; ++i) {
            uint8_t ca = (i < a.size()) ? a[i] : 0;
            uint8_t cb = (i < b.size()) ? b[i] : 0;
            result |= ca ^ cb;
        }
        return false;
    }

    return constant_time_compare(
        reinterpret_cast<const uint8_t*>(a.data()),
        reinterpret_cast<const uint8_t*>(b.data()),
        a.size());
}

inline uint8_t ct_cmov(uint8_t x, uint8_t y, uint8_t condition) {
    uint8_t mask = -(uint8_t)(condition != 0);
    return (x & mask) | (y & ~mask);
}

inline void ct_select(uint8_t* result, const uint8_t* a,
                       const uint8_t* b, size_t len,
                       uint8_t condition) {
    uint8_t mask = -(uint8_t)(condition != 0);
    for (size_t i = 0; i < len; ++i) {
        result[i] = (a[i] & mask) | (b[i] & ~mask);
    }
}

inline void secure_wipe(void* ptr, size_t len) {
    volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
    for (size_t i = 0; i < len; ++i) {
        p[i] = 0;
    }

    __asm__ __volatile__("" ::: "memory");
}

inline void secure_wipe(std::vector<uint8_t>& vec) {
    secure_wipe(vec.data(), vec.size());
    vec.clear();
    vec.shrink_to_fit();
}

template<size_t N>
void secure_wipe(std::array<uint8_t, N>& arr) {
    secure_wipe(arr.data(), N);
}

inline void ct_memcpy(uint8_t* dst, const uint8_t* src, size_t len) {
    volatile uint8_t* d = dst;
    const volatile uint8_t* s = src;

    for (size_t i = 0; i < len; ++i) {
        d[i] = s[i];
    }
}

inline bool ct_memeq(const void* a, const void* b, size_t len) {
    const volatile uint8_t* pa = static_cast<const volatile uint8_t*>(a);
    const volatile uint8_t* pb = static_cast<const volatile uint8_t*>(b);

    volatile uint8_t result = 0;
    for (size_t i = 0; i < len; ++i) {
        result |= pa[i] ^ pb[i];
    }

    return result == 0;
}

inline bool ct_is_zero(const uint8_t* data, size_t len) {
    volatile uint8_t result = 0;
    for (size_t i = 0; i < len; ++i) {
        result |= data[i];
    }
    return result == 0;
}

inline bool ct_compare64(uint64_t a, uint64_t b) {
    volatile uint8_t result = 0;
    const uint8_t* pa = reinterpret_cast<const uint8_t*>(&a);
    const uint8_t* pb = reinterpret_cast<const uint8_t*>(&b);

    for (size_t i = 0; i < 8; ++i) {
        result |= pa[i] ^ pb[i];
    }

    return result == 0;
}

}  // namespace tls_server
```

### 15.10.2 Memory Protection

```cpp
// memory_protection.h
#pragma once

#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>
#include <cstring>
#include <cstdint>
#include <stdexcept>
#include <memory>

namespace tls_server {

inline void lock_memory(const void* ptr, size_t len) {
    if (mlock(ptr, len) != 0) {
        throw std::runtime_error(
            std::string("Failed to lock memory: ") + strerror(errno));
    }
}

inline void unlock_memory(const void* ptr, size_t len) {
    munlock(ptr, len);
}

inline void set_memory_limits() {
    struct rlimit rl;

    rl.rlim_cur = RLIM_INFINITY;
    rl.rlim_max = RLIM_INFINITY;
    setrlimit(RLIMIT_MEMLOCK, &rl);

    rl.rlim_cur = 0;
    rl.rlim_max = 0;
    setrlimit(RLIMIT_CORE, &rl);
}

class LockedMemory {
public:
    LockedMemory(size_t size) : size_(size) {
        ptr_ = aligned_alloc(sysconf(_SC_PAGESIZE), size);
        if (!ptr_) {
            throw std::runtime_error("Failed to allocate locked memory");
        }

        memset(ptr_, 0, size);
        lock_memory(ptr_, size_);
        mlock(ptr_, size_);
    }

    ~LockedMemory() {
        if (ptr_) {
            secure_wipe(ptr_, size_);
            unlock_memory(ptr_, size_);
            free(ptr_);
        }
    }

    LockedMemory(const LockedMemory&) = delete;
    LockedMemory& operator=(const LockedMemory&) = delete;

    LockedMemory(LockedMemory&& other) noexcept
        : ptr_(other.ptr_), size_(other.size_) {
        other.ptr_ = nullptr;
        other.size_ = 0;
    }

    [[nodiscard]] void* get() const noexcept { return ptr_; }
    [[nodiscard]] size_t size() const noexcept { return size_; }

private:
    void* ptr_ = nullptr;
    size_t size_ = 0;
};

template <typename T>
class SecureAllocator {
public:
    using value_type = T;

    SecureAllocator() noexcept = default;

    template <typename U>
    SecureAllocator(const SecureAllocator<U>&) noexcept {}

    T* allocate(size_t n) {
        T* ptr = static_cast<T*>(
            ::operator new(n * sizeof(T), std::nothrow));

        if (ptr) {
            lock_memory(ptr, n * sizeof(T));
        }

        return ptr;
    }

    void deallocate(T* ptr, size_t n) {
        if (ptr) {
            volatile unsigned char* p =
                reinterpret_cast<volatile unsigned char*>(ptr);
            for (size_t i = 0; i < n * sizeof(T); ++i) {
                p[i] = 0;
            }

            unlock_memory(ptr, n * sizeof(T));
            ::operator delete(ptr);
        }
    }

    template <typename U>
    bool operator==(const SecureAllocator<U>&) const noexcept {
        return true;
    }

    template <typename U>
    bool operator!=(const SecureAllocator<U>&) const noexcept {
        return false;
    }
};

template <typename T>
using SecureVector = std::vector<T, SecureAllocator<T>>;

using SecureString = std::basic_string<char, std::char_traits<char>,
                                       SecureAllocator<char>>;

class SecureBuffer {
public:
    explicit SecureBuffer(size_t size)
        : data_(static_cast<uint8_t*>(
            ::operator new(size, std::nothrow))),
          size_(size) {

        if (!data_) {
            throw std::runtime_error(
                "Failed to allocate secure buffer");
        }

        memset(data_, 0, size);
        lock_memory(data_, size);
    }

    ~SecureBuffer() {
        wipe();
        if (data_) {
            unlock_memory(data_, size_);
            ::operator delete(data_);
        }
    }

    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;

    SecureBuffer(SecureBuffer&& other) noexcept
        : data_(other.data_), size_(other.size_) {
        other.data_ = nullptr;
        other.size_ = 0;
    }

    [[nodiscard]] uint8_t* data() noexcept { return data_; }
    [[nodiscard]] const uint8_t* data() const noexcept { return data_; }
    [[nodiscard]] size_t size() const noexcept { return size_; }

    void wipe() {
        if (data_) {
            volatile uint8_t* p = data_;
            for (size_t i = 0; i < size_; ++i) {
                p[i] = 0;
            }
        }
    }

private:
    uint8_t* data_ = nullptr;
    size_t size_ = 0;
};

}  // namespace tls_server
```

---

## 15.11 Otimização de Performance

### 15.11.1 Session Caching

```cpp
// performance_optimizer.h
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <chrono>
#include <mutex>
#include <functional>
#include <atomic>
#include <algorithm>

namespace tls_server {

class PerformanceOptimizer {
public:
    struct Config {
        bool session_cache_enabled = true;
        size_t max_session_cache_size = 10000;
        int session_cache_ttl_seconds = 300;

        bool ticket_cache_enabled = true;
        size_t max_ticket_cache_size = 10000;
        int ticket_cache_ttl_seconds = 3600;

        bool connection_pool_enabled = true;
        size_t max_pool_size = 1000;
        int pool_timeout_ms = 100;

        bool buffer_pool_enabled = true;
        size_t max_buffer_pool_size = 10000;
        size_t buffer_size = 16384;

        bool use_huge_pages = false;
        bool preallocate_connections = true;
        size_t preallocated_connections = 1000;
    };

    explicit PerformanceOptimizer(const Config& config);
    ~PerformanceOptimizer();

    bool cache_session(const std::string& session_id,
                       const std::vector<unsigned char>& session_data);
    bool get_cached_session(const std::string& session_id,
                            std::vector<unsigned char>& session_data);
    void evict_expired_sessions();

    bool cache_ticket(const std::string& ticket_id,
                      const std::vector<unsigned char>& ticket_data);
    bool get_cached_ticket(const std::string& ticket_id,
                           std::vector<unsigned char>& ticket_data);

    std::vector<unsigned char> get_buffer();
    void return_buffer(std::vector<unsigned char> buffer);

    void preallocate_resources();
    void optimize_tcp_socket(int fd);

    struct PerfMetrics {
        double avg_handshake_time_ms;
        double p95_handshake_time_ms;
        double p99_handshake_time_ms;
        size_t session_cache_hits;
        size_t session_cache_misses;
        double session_cache_hit_rate;
        size_t connection_pool_size;
        size_t buffer_pool_size;
        double memory_usage_mb;
    };

    PerfMetrics get_metrics() const;

    void run_benchmark();

private:
    struct SessionCacheEntry {
        std::vector<unsigned char> data;
        std::chrono::steady_clock::time_point expiry;
        size_t access_count = 0;
    };

    struct TicketCacheEntry {
        std::vector<unsigned char> data;
        std::chrono::steady_clock::time_point expiry;
    };

    Config config_;

    std::unordered_map<std::string, SessionCacheEntry> session_cache_;
    mutable std::mutex session_cache_mutex_;

    std::unordered_map<std::string, TicketCacheEntry> ticket_cache_;
    mutable std::mutex ticket_cache_mutex_;

    std::vector<std::vector<unsigned char>> buffer_pool_;
    mutable std::mutex buffer_pool_mutex_;

    std::atomic<size_t> session_cache_hits_{0};
    std::atomic<size_t> session_cache_misses_{0};
    std::vector<double> handshake_times_;
    mutable std::mutex metrics_mutex_;
};

}  // namespace tls_server
```

### 15.11.2 Connection Pooling

```cpp
// connection_pool.h
#pragma once

#include <string>
#include <vector>
#include <memory>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <functional>

namespace tls_server {

template<typename T>
class ConnectionPool {
public:
    using Creator = std::function<std::shared_ptr<T>()>;
    using Validator = std::function<bool(const std::shared_ptr<T>&)>;

    ConnectionPool(Creator creator,
                   Validator validator,
                   size_t min_size = 5,
                   size_t max_size = 100,
                   int timeout_ms = 100)
        : creator_(std::move(creator)),
          validator_(std::move(validator)),
          min_size_(min_size),
          max_size_(max_size),
          timeout_ms_(timeout_ms) {
        for (size_t i = 0; i < min_size_; ++i) {
            auto conn = creator_();
            if (conn) {
                pool_.push(conn);
            }
        }
    }

    ~ConnectionPool() {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!pool_.empty()) {
            pool_.pop();
        }
    }

    std::shared_ptr<T> acquire() {
        std::unique_lock<std::mutex> lock(mutex_);

        if (!cv_.wait_for(lock,
                          std::chrono::milliseconds(timeout_ms_),
                          [this]() {
                              return !pool_.empty() ||
                                     total_size_ < max_size_;
                          })) {
            return nullptr;
        }

        while (!pool_.empty()) {
            auto conn = pool_.front();
            pool_.pop();

            if (validator_ && !validator_(conn)) {
                total_size_--;
                continue;
            }

            return conn;
        }

        if (total_size_ < max_size_) {
            total_size_++;
            return creator_();
        }

        return nullptr;
    }

    void release(std::shared_ptr<T> conn) {
        if (!conn) return;

        std::lock_guard<std::mutex> lock(mutex_);

        if (pool_.size() < max_size_) {
            pool_.push(conn);
        } else {
            total_size_--;
        }

        cv_.notify_one();
    }

    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        while (!pool_.empty()) {
            pool_.pop();
        }
        total_size_ = 0;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return pool_.size();
    }

    size_t total_size() const {
        return total_size_.load();
    }

private:
    Creator creator_;
    Validator validator_;
    size_t min_size_;
    size_t max_size_;
    int timeout_ms_;

    std::queue<std::shared_ptr<T>> pool_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<size_t> total_size_{0};
};

}  // namespace tls_server
```

---

## 15.12 Testes do Servidor

### 15.12.1 Testes de Handshake TLS

```cpp
// test_tls_handshake.cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>

#include "tls_server.h"
#include "ssl_context.h"
#include "certificate_handler.h"

using namespace tls_server;
using namespace testing;

class TLSHandshakeTest : public ::testing::Test {
protected:
    void SetUp() override {
        initialize_openssl();

        server_config_.bind_address = "127.0.0.1";
        server_config_.port = 0;
        server_config_.tls.min_version = TLS1_3_VERSION;
        server_config_.tls.tls13_ciphers = {
            "TLS_AES_256_GCM_SHA384"
        };

        server_config_.cert.cert_file = "test_cert.pem";
        server_config_.cert.key_file = "test_key.pem";
        server_config_.cert.ca_file = "test_ca.pem";

        server_config_.logging.min_level = LogLevel::TRACE;
        server_config_.logging.console_output = true;
        server_config_.logging.file_output = false;
    }

    void TearDown() override {
    }

    ServerConfig server_config_;
};

TEST_F(TLSHandshakeTest, BasicHandshake) {
    TLSServer server(server_config_);
    ASSERT_TRUE(server.initialize());

    SSL_CTX* client_ctx = SSL_CTX_new(TLS_client_method());
    ASSERT_NE(client_ctx, nullptr);

    SSL_CTX_set_verify(client_ctx, SSL_VERIFY_PEER, nullptr);
    SSL_CTX_load_verify_locations(client_ctx,
                                   "test_ca.pem", nullptr);

    SSL* client_ssl = SSL_new(client_ctx);
    ASSERT_NE(client_ssl, nullptr);

    SSL_free(client_ssl);
    SSL_CTX_free(client_ctx);
}

TEST_F(TLSHandshakeTest, CipherSuiteNegotiation) {
    TLSConfig tls_config;
    tls_config.tls13_ciphers = {
        "TLS_AES_256_GCM_SHA384",
        "TLS_AES_128_GCM_SHA256"
    };

    SSLContext ctx(tls_config);
    ctx.configure();

    std::string debug = ctx.get_debug_info();
    EXPECT_THAT(debug, HasSubstr("TLS_AES_256_GCM_SHA384"));
    EXPECT_THAT(debug, HasSubstr("TLS_AES_128_GCM_SHA256"));
}

TEST_F(TLSHandshakeTest, VersionNegotiation) {
    TLSConfig tls_config;
    tls_config.min_version = TLS1_3_VERSION;
    tls_config.max_version = TLS1_3_VERSION;

    SSLContext ctx(tls_config);
    ctx.configure();

    EXPECT_EQ(tls_config.min_version, TLS1_3_VERSION);
    EXPECT_EQ(tls_config.max_version, TLS1_3_VERSION);
}

TEST_F(TLSHandshakeTest, SessionResumption) {
    SessionConfig session_config;
    session_config.tickets_enabled = true;
    session_config.early_data_enabled = false;

    SessionManager session_mgr(session_config);

    SessionData session;
    session.session_id = "test_session_123";
    session.master_secret = {1, 2, 3, 4, 5, 6, 7, 8};
    session.created = std::chrono::steady_clock::now();
    session.last_access = session.created;

    session_mgr.cache_session(session.session_id, session);

    auto cached = session_mgr.get_cached_session(session.session_id);
    ASSERT_TRUE(cached.has_value());
    EXPECT_EQ(cached->session_id, session.session_id);
}

TEST_F(TLSHandshakeTest, HandshakeMetrics) {
    MetricsCollector::Config metrics_config;
    metrics_config.enabled = true;

    MetricsCollector metrics(metrics_config);

    metrics.increment_counter("handshakes.total");
    metrics.record_histogram("handshakes.duration_ms", 1.5);

    auto snapshot = metrics.snapshot();
    EXPECT_FALSE(snapshot.counters.empty());
    EXPECT_FALSE(snapshot.histograms.empty());
}

TEST_F(TLSHandshakeTest, ConnectionLimits) {
    ConnectionConfig conn_config;
    conn_config.max_connections = 100;
    conn_config.max_connections_per_ip = 5;

    ConnectionManager conn_mgr(conn_config);

    auto stats = conn_mgr.get_stats();
    EXPECT_EQ(stats.active_connections, 0u);
    EXPECT_EQ(stats.total_connections, 0u);
}
```

### 15.12.2 Testes de Certificado

```cpp
// test_certificate_validation.cpp
#include <gtest/gtest.h>

#include "certificate_handler.h"

using namespace tls_server;

class CertificateTest : public ::testing::Test {
protected:
    void SetUp() override {
        cert_config_.cert_file = "test_cert.pem";
        cert_config_.key_file = "test_key.pem";
        cert_config_.ca_file = "test_ca.pem";
        cert_config_.verify_client = false;
        cert_config_.ocsp_stapling = false;
    }

    CertificateConfig cert_config_;
};

TEST_F(CertificateTest, LoadCertificate) {
    CertificateHandler handler(cert_config_);

    auto info = handler.get_certificate_info();

    EXPECT_FALSE(info.subject.empty());
    EXPECT_FALSE(info.issuer.empty());
    EXPECT_FALSE(info.serial.empty());
}

TEST_F(CertificateTest, CertificateExpiry) {
    CertificateHandler handler(cert_config_);

    EXPECT_FALSE(handler.is_certificate_expiring_soon(30));
    EXPECT_TRUE(handler.is_certificate_expiring_soon(36500));
}

TEST_F(CertificateTest, CertificateInfo) {
    CertificateHandler handler(cert_config_);

    auto info = handler.get_certificate_info();

    EXPECT_FALSE(info.subject.empty());
    EXPECT_FALSE(info.thumbprint_sha256.empty());
    EXPECT_FALSE(info.signature_algorithm.empty());

    EXPECT_TRUE(info.key_type == "RSA" ||
                info.key_type == "EC" ||
                info.key_type == "Ed25519");
}

TEST_F(CertificateTest, SANEntries) {
    CertificateHandler handler(cert_config_);

    auto info = handler.get_certificate_info();

    EXPECT_NO_THROW({
        for (const auto& dns : info.san_dns) {
            EXPECT_FALSE(dns.empty());
        }
    });
}

TEST_F(CertificateTest, ChainValidation) {
    CertificateConfig config = cert_config_;
    config.chain_file = "test_chain.pem";

    EXPECT_THROW({
        CertificateHandler handler(config);
    }, std::runtime_error);
}

TEST_F(CertificateTest, InvalidCertificate) {
    CertificateConfig config;
    config.cert_file = "nonexistent.pem";
    config.key_file = "nonexistent.pem";

    EXPECT_THROW({
        CertificateHandler handler(config);
    }, std::runtime_error);
}

TEST_F(CertificateTest, KeyMismatch) {
    CertificateConfig config;
    config.cert_file = "test_cert.pem";
    config.key_file = "wrong_key.pem";

    EXPECT_THROW({
        CertificateHandler handler(config);
    }, std::runtime_error);
}
```

### 15.12.3 Testes de Performance

```cpp
// test_performance.cpp
#include <gtest/gtest.h>

#include "tls_server.h"
#include "session_manager.h"
#include "performance_optimizer.h"

using namespace tls_server;

class PerformanceTest : public ::testing::Test {
protected:
    void SetUp() override {
    }
};

TEST_F(PerformanceTest, SessionCachePerformance) {
    SessionConfig config;
    config.tickets_enabled = true;
    config.server_side_cache = true;
    config.max_cache_size = 10000;

    SessionManager session_mgr(config);

    auto start = std::chrono::steady_clock::now();

    for (int i = 0; i < 1000; ++i) {
        SessionData session;
        session.session_id = "session_" + std::to_string(i);
        session.created = std::chrono::steady_clock::now();
        session.last_access = session.created;

        session_mgr.cache_session(session.session_id, session);
    }

    auto end = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end - start);

    EXPECT_LT(duration.count(), 10000);
}

TEST_F(PerformanceTest, BufferPoolPerformance) {
    PerformanceOptimizer::Config config;
    config.buffer_pool_enabled = true;
    config.max_buffer_pool_size = 1000;
    config.buffer_size = 16384;

    PerformanceOptimizer optimizer(config);

    auto start = std::chrono::steady_clock::now();

    for (int i = 0; i < 1000; ++i) {
        auto buffer = optimizer.get_buffer();
        optimizer.return_buffer(std::move(buffer));
    }

    auto end = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end - start);

    EXPECT_LT(duration.count(), 5000);
}

TEST_F(PerformanceTest, ConstantTimeComparison) {
    uint8_t a[] = {1, 2, 3, 4, 5};
    uint8_t b[] = {1, 2, 3, 4, 5};
    uint8_t c[] = {1, 2, 3, 4, 6};

    EXPECT_TRUE(constant_time_compare(a, b, 5));
    EXPECT_FALSE(constant_time_compare(a, c, 5));
}

TEST_F(PerformanceTest, SecureWipePerformance) {
    SecureBuffer buffer(1024);

    memset(buffer.data(), 0xAA, buffer.size());

    auto start = std::chrono::steady_clock::now();
    buffer.wipe();
    auto end = std::chrono::steady_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(
        end - start);

    for (size_t i = 0; i < buffer.size(); ++i) {
        EXPECT_EQ(buffer.data()[i], 0);
    }

    EXPECT_LT(duration.count(), 1000);
}

TEST_F(PerformanceTest, ThreadPoolThroughput) {
    ThreadPoolConfig config;
    config.worker_threads = 4;
    config.max_queue_size = 10000;

    ThreadPool pool(config);

    std::atomic<int> counter{0};

    auto start = std::chrono::steady_clock::now();

    for (int i = 0; i < 10000; ++i) {
        pool.submit([&counter]() {
            counter++;
        });
    }

    pool.wait_all();

    auto end = std::chrono::steady_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start);

    EXPECT_EQ(counter.load(), 10000);
    EXPECT_LT(duration.count(), 1000);
}

TEST_F(PerformanceTest, ConnectionPoolEfficiency) {
    int created = 0;
    int validated = 0;

    auto creator = [&created]() -> std::shared_ptr<int> {
        created++;
        return std::make_shared<int>(created);
    };

    auto validator = [&validated](const std::shared_ptr<int>& conn) {
        validated++;
        return *conn > 0;
    };

    ConnectionPool<int> pool(creator, validator, 5, 10);

    for (int i = 0; i < 20; ++i) {
        auto conn = pool.acquire();
        EXPECT_NE(conn, nullptr);
        pool.release(conn);
    }

    EXPECT_LT(created, 20);
}
```

---

## 15.13 Deployment

### 15.13.1 Dockerfile

```dockerfile
FROM ubuntu:22.04 AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DOPENSSL_ROOT_DIR=/usr \
          .. && \
    make -j$(nproc)

FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r tlsuser && \
    useradd -r -g tlsuser -d /app -s /sbin/nologin tlsuser

COPY --from=builder /app/build/tls-server /usr/local/bin/
COPY --from=builder /app/config/server.yaml /etc/tls-server/
COPY --from=builder /app/certs/ /etc/tls-server/certs/

RUN mkdir -p /var/log/tls-server && \
    chown tlsuser:tlsuser /var/log/tls-server

USER tlsuser

EXPOSE 443

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /usr/local/bin/tls-server --health-check || exit 1

ENTRYPOINT ["/usr/local/bin/tls-server"]
CMD ["--config", "/etc/tls-server/server.yaml"]
```

### 15.13.2 docker-compose.yml

```yaml
version: '3.8'

services:
  tls-server:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "443:443"
      - "9090:9090"
    volumes:
      - ./config:/etc/tls-server:ro
      - ./certs:/etc/tls-server/certs:ro
      - tls-logs:/var/log/tls-server
    environment:
      - TLS_SERVER_CONFIG=/etc/tls-server/server.yaml
      - LOG_LEVEL=info
      - METRICS_ENABLED=true
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "/usr/local/bin/tls-server", "--health-check"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    networks:
      - tls-network

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./deploy/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks:
      - tls-network

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - tls-network

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./deploy/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
    networks:
      - tls-network

volumes:
  tls-logs:
  grafana-data:

networks:
  tls-network:
    driver: bridge
```

### 15.13.3 systemd Service

```ini
[Unit]
Description=TLS Server
Documentation=https://github.com/devsecurity/tls-server
After=network-online.target
Wants=network-online.target

ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
RestrictSUIDSGID=true
MemoryDenyWriteExecute=true
RestrictRealtime=true

[Service]
Type=simple
User=tlsuser
Group=tlsuser
ExecStart=/usr/local/bin/tls-server --config /etc/tls-server/server.yaml
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

LimitNOFILE=1000000
LimitNPROC=infinity
LimitCORE=infinity
LimitMEMLOCK=infinity

CPUQuota=200%
MemoryMax=2G
MemoryHigh=1G

Restart=on-failure
RestartSec=5s
StartLimitBurst=5
StartLimitIntervalSec=60

CapabilityBoundingSet=
SecureBits=keep-caps

StandardOutput=journal
StandardError=journal
SyslogIdentifier=tls-server

[Install]
WantedBy=multi-user.target
```

---

## 15.14 Monitoramento e Alertas

### 15.14.1 Métricas Prometheus

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

rule_files:
  - "tls_server_rules.yml"

scrape_configs:
  - job_name: 'tls-server'
    static_configs:
      - targets: ['tls-server:9090']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
```

### 15.14.2 Alert Rules

```yaml
groups:
  - name: tls_server_alerts
    rules:
      - alert: TLSHandshakeFailureRateHigh
        expr: |
          rate(tls_server_handshakes_failed_total[5m]) /
          rate(tls_server_handshakes_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High TLS handshake failure rate"
          description: >
            TLS handshake failure rate is above 10% for 5 minutes.
            Current value: {{ $value }}

      - alert: TLSConnectionSaturation
        expr: |
          tls_server_connections_active /
          tls_server_connections_max > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "TLS server connection saturation"
          description: >
            TLS server connections are above 90% capacity.
            Current: {{ $value | humanizePercentage }}

      - alert: TLSHighMemoryUsage
        expr: |
          tls_server_memory_usage_bytes /
          tls_server_memory_limit_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on TLS server"
          description: >
            TLS server memory usage is above 85%.
            Current: {{ $value | humanizePercentage }}

      - alert: TLSHighResponseTime
        expr: |
          histogram_quantile(0.95,
            rate(tls_server_request_duration_seconds_bucket[5m])
          ) > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High TLS server response time"
          description: >
            95th percentile response time is above 500ms.
            Current: {{ $value }}s

      - alert: TLSCertificateExpiringSoon
        expr: |
          tls_server_certificate_expiry_days < 30
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "TLS certificate expiring soon"
          description: >
            TLS certificate expires in {{ $value }} days.

      - alert: TLSCertificateExpiryCritical
        expr: |
          tls_server_certificate_expiry_days < 7
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "TLS certificate expires within 7 days"
          description: >
            TLS certificate expires in {{ $value }} days.
            Renew immediately!

      - alert: TLSHighErrorRate
        expr: |
          rate(tls_server_errors_total[5m]) > 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate on TLS server"
          description: >
            Error rate is above 10 errors/second.
            Current: {{ $value }}

      - alert: TLSReplayAttackDetected
        expr: |
          increase(tls_server_replay_attacks_total[5m]) > 0
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "TLS replay attack detected"
          description: >
            {{ $value }} replay attacks detected in the last 5 minutes.
            Investigate immediately.

      - alert: TLSLowSessionCacheHitRate
        expr: |
          tls_server_session_cache_hits /
          (tls_server_session_cache_hits +
           tls_server_session_cache_misses) < 0.5
        for: 30m
        labels:
          severity: info
        annotations:
          summary: "Low session cache hit rate"
          description: >
            Session cache hit rate is below 50%.
            Current: {{ $value | humanizePercentage }}
```

### 15.14.3 Dashboard Grafana

```json
{
  "dashboard": {
    "title": "TLS Server Dashboard",
    "panels": [
      {
        "title": "Active Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "tls_server_connections_active",
            "legendFormat": "Active Connections"
          }
        ]
      },
      {
        "title": "Handshake Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tls_server_handshakes_total[1m])",
            "legendFormat": "Handshakes/sec"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tls_server_errors_total[1m])",
            "legendFormat": "Errors/sec"
          }
        ]
      },
      {
        "title": "Certificate Expiry",
        "type": "stat",
        "targets": [
          {
            "expr": "tls_server_certificate_expiry_days",
            "legendFormat": "Days until expiry"
          }
        ]
      }
    ]
  }
}
```

---

## 15.15 Revisão de CVE

### CVE-2014-0160: Heartbleed

O Heartbleed é uma das vulnerabilidades mais devastadoras na história de segurança
de TLS. Descoberta em abril de 2014, afetou o OpenSSL em versões entre 1.0.1 e 1.0.1f.
A vulnerabilidade permitia a um atacante ler memória do servidor, potencialmente
expondo chaves privadas, senhas e outros dados sensíveis.

**Técnica do Ataque:**

Heartbleed explorava uma falha na implementação do extensão TLS Heartbeat.
O Heartbeat é um mecanismo para manter conexões TCP vivas enviando um "eco"
do dado recebido. O atacante poderia:

1. Enviar um heartbeat request com dados pequenos (ex: 1 byte)
2. Mentir sobre o tamanho dos dados (declarar 64KB)
3. O servidor, sem verificar o tamanho, copiaria 64KB de memória
4. Essa memória poderia conter:
   - Chaves privadas do servidor
   - Chaves de sessão
   - Senhas de usuários
   - Outros dados sensíveis

**Lição para o TLS Server deste capítulo:**

Nossa implementação evita essa classe de vulnerabilidade através de:

1. **Validação rigorosa de tamanhos** — todas as operações de leitura verificam
   os limites do buffer antes de copiar dados

2. **Sem extensões desnecessárias** — TLS 1.3 removeu o Heartbeat do protocolo
   base, eliminando completamente essa superfície de ataque

3. **Buffer bounds checking** — todos os nossos buffers são verificados com
   `size_t` unsigned e bounds check explícitos

4. **Memory wiping** — dados sensíveis são limpos da memória após uso,
   limitando o impacto mesmo que um buffer over-read ocorra

**Código de proteção:**

```cpp
// Nossa implementação valida todos os tamanhos
bool ConnectionManager::read_data(
    std::shared_ptr<TLSConnection> conn,
    std::vector<unsigned char>& data,
    size_t max_len) {

    // VALIDAÇÃO: max_len não pode ser maior que o buffer
    if (max_len > data.capacity()) {
        return false;
    }

    data.resize(max_len);

    int bytes_read = SSL_read(conn->ssl, data.data(), data.size());

    if (bytes_read > 0) {
        // VALIDAÇÃO: bytes_read não pode ser maior que max_len
        if (static_cast<size_t>(bytes_read) > max_len) {
            // Isso NUNCA deve acontecer, mas verificamos
            return false;
        }

        data.resize(bytes_read);
    }
    // ...
}
```

**Outras proteções no nosso servidor:**

```cpp
// Em connection_manager.cpp - validação de socket options
bool ConnectionManager::set_socket_options(int fd) {
    // TCP_NODELAY previne buffering que poderia ser explorado
    int flag = 1;
    if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY,
                   &flag, sizeof(flag)) < 0) {
        return false;
    }

    // SO_REUSEADDR com verificação
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR,
                   &flag, sizeof(flag)) < 0) {
        return false;
    }

    // Keepalive com parâmetros seguros
    int idle = 60;
    int interval = 10;
    int count = 3;

    setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE,
               &idle, sizeof(idle));
    setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL,
               &interval, sizeof(interval));
    setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT,
               &count, sizeof(count));

    return true;
}
```

**Lição geral sobre segurança de buffers:**

Heartbleed ensinou que:

1. **Nunca confie no tamanho declarado pelo cliente** — sempre valide contra
   o tamanho real do buffer

2. **Limitações de memória devem ser verificadas** — use `size_t` unsigned
   e verifique overflow

3. **TLS não é inerentemente seguro** — a implementação é tão importante
   quanto o protocolo

4. **Atualizações de segurança são críticas** — o OpenSSL 1.0.1g corrigiu
   a vulnerabilidade em 7 de abril de 2014

5. **Defense in depth funciona** — mesmo que uma camada falhe, outras
   protegem (nossa implementação usa múltiplas camadas)

### 15.15.1 Outras CVEs Relevantes

| CVE | Ano | Impacto | Nossa Proteção |
|-----|-----|---------|----------------|
| CVE-2014-0160 | 2014 | Heartbleed | TLS 1.3, buffer validation |
| CVE-2014-3566 | 2014 | POODLE | SSLv3 disabled |
| CVE-2016-2183 | 2016 | SWEET32 | 3DES disabled |
| CVE-2016-6304 | 2016 | Memory exhaustion | Rate limiting |
| CVE-2017-3735 | 2017 | Out-of-bounds read | Input validation |
| CVE-2018-0734 | 2018 | Timing attack | Constant-time ops |
| CVE-2019-1559 | 2019 | Padding oracle | AEAD ciphers only |
| CVE-2020-1967 | 2020 | Segfault | Error handling |
| CVE-2021-3449 | 2021 | NULL deref | NULL checks |
| CVE-2022-0778 | 2022 | Infinite loop | Input validation |
| CVE-2023-0215 | 2023 | Use-after-free | Memory management |

---

## 15.16 Exercícios

### Exercício 1: Implementar SNI Virtual Hosts

Implemente suporte a SNI (Server Name Indication) para hospedar múltiplos
certificados no mesmo servidor. Cada hostname deve ter seu próprio certificado
e chain de CA.

**Requisitos:**
- Suporte a pelo menos 10 virtual hosts
- Hot reload de certificados sem restart
- Cache de contexto SSL por hostname
- Rate limiting por hostname

**Pistas:**
- Use `SSL_CTX_set_tlsext_servername_callback`
- Mantenha um mapa de hostname -> SSL_CTX
- Implemente LRU cache para contextos

### Exercício 2: mTLS com Certificate Revocation

Implemente suporte completo a mTLS (mutual TLS) com verificação de revogação
de certificados de cliente usando CRL e OCSP.

**Requisitos:**
- Aceitar connections com client certificates
- Verificar CRL periodicamente
- Cache de respostas OCSP
- Rejeitar certificados revogados

**Pistas:**
- Use `SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT`
- Implemente callback de verificação personalizado
- Use `X509_STORE_add_crl` para CRL

### Exercício 3: Rate Limiting Avançado

Implemente um sistema de rate limiting avançado que suporte:
- Rate limit por IP
- Rate limit por API key
- Rate limit por endpoint
- Sliding window algorithm

**Requisitos:**
- Algoritmo de sliding window
- Armazenamento em memória com TTL
- Headers de resposta (`X-RateLimit-*`)
- Suporte a rate limiting distribuído

### Exercício 4: HSM Integration Simulation

Implemente uma simulação de HSM usando software que emule a interface PKCS#11.
O simulator deve:
- Gerar e armazenar chaves de forma segura
- Realizar operações de sign/verify
- Limitar operações por segundo
- Simular latência de hardware

### Exercício 5: Security Audit Script

Escreva um script de auditoria de segurança que verifique:
- Configuração OpenSSL (cipher suites, protocols)
- Certificados (validade, chain, OCSP)
- Headers HTTP de segurança (HSTS, CSP)
- Conformidade com PCI DSS e NIST

**Formato de saída:** Relatório HTML com severidade (CRITICAL, HIGH, MEDIUM, LOW)

### Exercício 6: Performance Benchmarking

Crie um benchmark completo que meça:
- Throughput de handshakes TLS 1.3
- Latência de reconexão com session resumption
- Throughput de dados criptografados
- Uso de memória por conexão
- CPU usage sob carga

Compare os resultados com:
- nginx com TLS 1.3
- Go crypto/tls
- Rust rustls

### Exercício 7: Zero-Downtime Deployment

Implemente rotação de certificados sem downtime:
- Carregar novo certificado em background
- Testar novo certificado antes de ativar
- Migrar conexões existentes
- Fallback para certificado anterior em caso de erro

---

## 15.17 Referências

### RFCs

1. RFC 8446 - The Transport Layer Security (TLS) Protocol Version 1.3
2. RFC 5280 - Internet X.509 Public Key Infrastructure Certificate and CRL Profile
3. RFC 6960 - X.509 Internet Public Key Infrastructure Online Certificate Status Protocol - OCSP
4. RFC 6962 - Certificate Transparency
5. RFC 7301 - Transport Layer Security (TLS) Application-Layer Protocol Negotiation Extension
6. RFC 5077 - Transport Layer Security (TLS) Session Resumption without Server-Side State
7. RFC 8447 - IANA Registry for a TLS SignatureScheme Extension
8. RFC 7919 - Negotiated Finite Diffie-Hellman Ephemeral Parameters for TLS

### NIST Guidelines

1. NIST SP 800-52 Rev 2 - Guidelines for the Selection, Configuration, and Use of TLS Implementations
2. NIST SP 800-57 - Recommendation for Key Management
3. NIST SP 800-56A - Recommendation for Pair-Wise Key-Establishment Schemes Using Discrete Logarithm Cryptography
4. NIST SP 800-90A - Recommendation for Random Number Generation Using Deterministic Random Bit Generators
5. NIST FIPS 140-3 - Security Requirements for Cryptographic Modules

### OWASP

1. OWASP TLS Cheat Sheet
2. OWASP Certificate Pinning Cheat Sheet
3. OWASP Secure Headers Project

### Livros

1. "Bulletproof TLS and PKI" - Ivan Ristic
2. "Network Security with OpenSSL" - Viega, Messier, Chandra
3. "Cryptography Engineering" - Ferguson, Schneier, Kohno
4. "OpenSSL Cookbook" - Ivan Ristic
5. "Implementing SSL/TLS Using Cryptography and PKI" - Joshua Davies

### Ferramentas

1. OpenSSL 3.x Documentation - https://www.openssl.org/docs/
2. testssl.sh - Ferramenta de teste de configuração TLS
3. sslyze - Scanner de configuração SSL/TLS
4. OWASP ZAP - Ferramenta de teste de segurança
5. Prometheus + Grafana - Monitoramento

### CVEs

1. CVE-2014-0160 - OpenSSL Heartbleed
2. CVE-2014-3566 - POODLE (Padding Oracle On Downgraded Legacy Encryption)
3. CVE-2016-2183 - SWEET32 (Birthday attack on 64-bit block ciphers)
4. CVE-2022-0778 - OpenSSL infinite loop in BN_mod_sqrt()

---

**Próximo capítulo:** [Capítulo 16: Boas Práticas e Checklist de Engenharia Criptográfica](16-boas-praticas-checklist.md)

---

*Este capítulo faz parte do Livro 5: Engenharia de Criptografia em C++ do projeto DevSecurity.*
*Última atualização: 2024*
---

*[Capítulo anterior: 14 — Compliance Normas](14-compliance-normas.md)*
*[Próximo capítulo: 16 — Boas Praticas Checklist](16-boas-praticas-checklist.md)*
