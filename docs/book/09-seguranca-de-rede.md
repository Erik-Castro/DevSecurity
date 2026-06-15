# Capítulo 9 — Segurança de Rede

## Objetivos de Aprendizado

1. Compreender os fundamentos de segurança de rede e os vetores de ataque mais comuns em sistemas baseados em C++.
2. Implementar sockets seguros com gerenciamento RAII, validação de entrada e prevenção contra overflow de buffers.
3. Configurar TLS/SSL com hardening adequado, incluindo seleção de cipher suites, validação de cadeia de certificados e pinning.
4. Projetar protocolos de rede resistentes a replay attacks, com autenticação HMAC e controle de sequência.
5. Aplicar técnicas de mitigação de DDoS, incluindo SYN cookies, rate limiting com token bucket e sliding window.

---

## 1. Fundamentos de Segurança de Rede

### 1.1 Considerações de Segurança no Modelo OSI

Cada camada do modelo OSI apresenta vetores de ataque distintos. A segurança de rede deve ser tratada em todas as camadas simultaneamente — uma falha em qualquer nível pode comprometer todo o sistema.

| Camada | Nome            | Ameaças Principais                  | Controles Recomendados                    |
|--------|-----------------|--------------------------------------|-------------------------------------------|
| 7      | Aplicação       | Injeção, XSS, XSS SSRF              | Validação de entrada, CSP                 |
| 6      | Apresentação    | Ataques downgrade, compressão BREACH | TLS 1.3, compressão segura               |
| 5      | Sessão          | Fixação de sessão, hijacking         | Tokens aleatórios, binding IP             |
| 4      | Transporte      | SYN flood, seq prediction            | SYN cookies, sequence randomization      |
| 3      | Rede            | Spoofing, routing manipulation       | IPSec, validação de rotas                 |
| 2      | Enlace          | ARP spoofing, VLAN hopping           | 802.1X, dynamic ARP inspection            |
| 1      | Física          | Wiretapping, jamming                 | Conduits seguros, monitoramento           |

### 1.2 Categorias de Ataques de Rede

Ataques de rede podem ser classificados em três grandes categorias:

**Ataques Passivos:** Interceptação de tráfego sem alteração. Incluem sniffing de pacotes e análise de tráfego. O atacante observa sem ser detectado.

**Ataques Ativos — Off-path:** O atacante não está no caminho direto entre vítima e servidor. Exemplos incluem TCP sequence prediction e DNS spoofing.

**Ataques Ativos — On-path (Man-in-the-Middle):** O atacante se posiciona entre dois通信端点. SSLStrip (2009) e BEAST (CVE-2011-3389) são exemplos clássicos.

### 1.3 Threat Modeling para Aplicações C++

Ao modelar ameaças para aplicações C++ de rede, considere:

1. **Pontos de entrada:** Todo socket, pipe, ou interface de rede é um ponto de entrada potencial.
2. **Confiança entre componentes:** Microserviços confiam uns nos outros? Existe segmentação?
3. **Dados sensíveis em trânsito:** Credenciais, tokens, dados pessoais viajam em texto plano?
4. **Autenticação mútua:** O servidor autentica o cliente? O cliente autentica o servidor?

### 1.4 Limites de Confiança em Sistemas em Rede

Limites de confiança (trust boundaries) são pontos onde dados cruzam de uma zona de confiança para outra. Em C++, toda vez que um dado chega de rede, ele entra por uma trust boundary e deve ser tratado como não confiável.

```cpp
// Trust boundary crossing: network data enters the application
// Every byte from recv() is UNTRUSTED
void handle_client(int client_fd) {
    char buffer[4096];
    // Trust boundary: data crosses from network to application
    ssize_t n = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
    if (n <= 0) {
        close(client_fd);
        return;
    }
    buffer[n] = '\0';
    // DANGER: buffer now contains untrusted data
    // Must validate before use
    process_request(buffer, n);
}
```

---

## 2. Socket Programming Seguro

### 2.1 Criação e Configuração Segura de Sockets

Erros na criação de sockets são uma fonte comum de vulnerabilidades. Fechar file descriptors duplicados, configurar SO_REUSEADDR adequadamente e validar retornos de chamadas de sistema são práticas essenciais.

```cpp
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <stdexcept>
#include <string>
#include <chrono>
#include <thread>

// RAII wrapper for POSIX sockets
class SecureSocket {
public:
    SecureSocket() : fd_(-1) {}

    // Non-copyable, movable
    SecureSocket(const SecureSocket&) = delete;
    SecureSocket& operator=(const SecureSocket&) = delete;

    SecureSocket(SecureSocket&& other) noexcept : fd_(other.fd_) {
        other.fd_ = -1;
    }

    SecureSocket& operator=(SecureSocket&& other) noexcept {
        if (this != &other) {
            close();
            fd_ = other.fd_;
            other.fd_ = -1;
        }
        return *this;
    }

    ~SecureSocket() { close(); }

    void create_tcp() {
        fd_ = ::socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
        if (fd_ < 0) {
            throw std::runtime_error(
                "socket() failed: " + std::string(std::strerror(errno)));
        }
    }

    void set_reuse_addr(bool enable) {
        int val = enable ? 1 : 0;
        if (::setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val)) < 0) {
            throw std::runtime_error("setsockopt SO_REUSEADDR failed");
        }
    }

    void set_timeout(std::chrono::seconds sec) {
        struct timeval tv;
        tv.tv_sec = sec.count();
        tv.tv_usec = 0;
        if (::setsockopt(fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)) < 0) {
            throw std::runtime_error("setsockopt SO_RCVTIMEO failed");
        }
        if (::setsockopt(fd_, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv)) < 0) {
            throw std::runtime_error("setsockopt SO_SNDTIMEO failed");
        }
    }

    void bind(const std::string& addr, uint16_t port) {
        struct sockaddr_in sa{};
        sa.sin_family = AF_INET;
        sa.sin_port = htons(port);
        if (::inet_pton(AF_INET, addr.c_str(), &sa.sin_addr) != 1) {
            throw std::invalid_argument("Invalid bind address: " + addr);
        }
        if (::bind(fd_, reinterpret_cast<struct sockaddr*>(&sa), sizeof(sa)) < 0) {
            throw std::runtime_error(
                "bind() failed: " + std::string(std::strerror(errno)));
        }
    }

    void listen(int backlog) {
        if (::listen(fd_, backlog) < 0) {
            throw std::runtime_error(
                "listen() failed: " + std::string(std::strerror(errno)));
        }
    }

    int accept(struct sockaddr_in& client_addr) {
        socklen_t len = sizeof(client_addr);
        int client_fd = ::accept(
            fd_, reinterpret_cast<struct sockaddr*>(&client_addr), &len);
        if (client_fd < 0) {
            throw std::runtime_error(
                "accept() failed: " + std::string(std::strerror(errno)));
        }
        return client_fd;
    }

    void close() {
        if (fd_ >= 0) {
            ::close(fd_);
            fd_ = -1;
        }
    }

    int fd() const { return fd_; }
    bool is_valid() const { return fd_ >= 0; }

private:
    int fd_;
};
```

### 2.2 Validação de Entrada em Dados de Rede

Dados vindos da rede nunca devem ser confiados. Toda entrada deve ser validada quanto a tamanho, formato e conteúdo antes do processamento.

```cpp
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <vector>

// Protocol message structure
#pragma pack(push, 1)
struct MessageHeader {
    uint32_t magic;       // Expected: 0xDEADBEEF
    uint32_t version;     // Protocol version
    uint32_t msg_type;    // Message type
    uint32_t payload_len; // Length of payload
};
#pragma pack(pop)

static constexpr uint32_t MSG_MAGIC = 0xDEADBEEF;
static constexpr uint32_t MAX_PAYLOAD_SIZE = 1024 * 1024; // 1 MB
static constexpr uint32_t MIN_PAYLOAD_SIZE = 1;
static constexpr uint32_t PROTOCOL_VERSION = 2;

enum class ParseError {
    OK,
    INVALID_MAGIC,
    UNSUPPORTED_VERSION,
    PAYLOAD_TOO_LARGE,
    PAYLOAD_TOO_SMALL,
    TRUNCATED_HEADER,
    TRUNCATED_PAYLOAD,
    NETWORK_ERROR
};

// Secure message parsing with full validation
ParseError parse_message(int fd, MessageHeader& header, std::vector<uint8_t>& payload) {
    // Step 1: Read header with exact count check
    ssize_t total_read = 0;
    ssize_t header_size = sizeof(MessageHeader);
    char header_buf[sizeof(MessageHeader)];

    while (total_read < header_size) {
        ssize_t n = ::recv(fd, header_buf + total_read,
                          header_size - total_read, 0);
        if (n <= 0) {
            return ParseError::TRUNCATED_HEADER;
        }
        total_read += n;
    }

    std::memcpy(&header, header_buf, sizeof(header));

    // Step 2: Validate magic number
    if (header.magic != MSG_MAGIC) {
        return ParseError::INVALID_MAGIC;
    }

    // Step 3: Validate protocol version
    if (header.version != PROTOCOL_VERSION) {
        return ParseError::UNSUPPORTED_VERSION;
    }

    // Step 4: Validate payload size bounds
    if (header.payload_len < MIN_PAYLOAD_SIZE) {
        return ParseError::PAYLOAD_TOO_SMALL;
    }
    if (header.payload_len > MAX_PAYLOAD_SIZE) {
        return ParseError::PAYLOAD_TOO_LARGE;
    }

    // Step 5: Read payload with pre-allocated buffer
    payload.resize(header.payload_len);
    total_read = 0;
    while (total_read < static_cast<ssize_t>(header.payload_len)) {
        ssize_t n = ::recv(fd, reinterpret_cast<char*>(payload.data()) + total_read,
                          header.payload_len - total_read, 0);
        if (n <= 0) {
            return ParseError::TRUNCATED_PAYLOAD;
        }
        total_read += n;
    }

    return ParseError::OK;
}
```

### 2.3 Gerenciamento de Buffers para E/S de Rede

O gerenciamento inadequado de buffers em operações de rede é uma das vulnerabilidades mais perigosas em C++. Ocaso de buffers estáticos, off-by-one errors e falta de terminação nula são vetores comuns de exploração.

```cpp
// Secure buffer management for network I/O
class NetworkBuffer {
public:
    explicit NetworkBuffer(size_t capacity)
        : data_(capacity), read_pos_(0), write_pos_(0), full_(false) {}

    // Append data from network recv
    bool append(const uint8_t* data, size_t len) {
        size_t available = capacity() - size();
        if (len > available) {
            // Buffer would overflow — reject data
            return false;
        }
        for (size_t i = 0; i < len; ++i) {
            data_[write_pos_] = data[i];
            write_pos_ = (write_pos_ + 1) % capacity();
        }
        full_ = (write_pos_ == read_pos_);
        return true;
    }

    // Extract data from buffer
    size_t extract(uint8_t* dest, size_t max_len) {
        size_t avail = size();
        size_t to_read = std::min(avail, max_len);
        for (size_t i = 0; i < to_read; ++i) {
            dest[i] = data_[read_pos_];
            read_pos_ = (read_pos_ + 1) % capacity();
        }
        full_ = false;
        return to_read;
    }

    size_t size() const {
        if (full_) return capacity();
        if (write_pos_ >= read_pos_) {
            return write_pos_ - read_pos_;
        }
        return capacity() - read_pos_ + write_pos_;
    }

    size_t capacity() const { return data_.size(); }
    bool empty() const { return !full_ && (read_pos_ == write_pos_); }

    void clear() {
        read_pos_ = 0;
        write_pos_ = 0;
        full_ = false;
    }

private:
    std::vector<uint8_t> data_;
    size_t read_pos_;
    size_t write_pos_;
    bool full_;
};
```

### 2.4 Tratamento de Timeouts

Timeouts adequadamente configurados previnem que sockets bloqueiem indefinidamente, protegendo contra ataques de exaustão de recursos (slowloris, slow POST).

```cpp
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <stdexcept>

// Recv with timeout and full error handling
ssize_t recv_with_timeout(int fd, void* buf, size_t len,
                         int flags, std::chrono::milliseconds timeout) {
    struct pollfd pfd{};
    pfd.fd = fd;
    pfd.events = POLLIN;

    int poll_result = ::poll(&pfd, 1, static_cast<int>(timeout.count()));
    if (poll_result < 0) {
        if (errno == EINTR) {
            return 0; // Interrupted, caller can retry
        }
        throw std::runtime_error(
            "poll() failed: " + std::string(std::strerror(errno)));
    }
    if (poll_result == 0) {
        // Timeout expired
        return -2; // Special return value for timeout
    }
    if (pfd.revents & (POLLERR | POLLHUP)) {
        return -1; // Connection error or hangup
    }
    return ::recv(fd, buf, len, flags);
}

// Send with timeout
ssize_t send_with_timeout(int fd, const void* buf, size_t len,
                         int flags, std::chrono::milliseconds timeout) {
    struct pollfd pfd{};
    pfd.fd = fd;
    pfd.events = POLLOUT;

    int poll_result = ::poll(&pfd, 1, static_cast<int>(timeout.count()));
    if (poll_result < 0) {
        if (errno == EINTR) {
            return 0;
        }
        throw std::runtime_error(
            "poll() failed: " + std::string(std::strerror(errno)));
    }
    if (poll_result == 0) {
        return -2;
    }
    if (pfd.revents & POLLERR) {
        return -1;
    }
    return ::send(fd, buf, len, flags);
}

// Send all bytes with timeout (handles partial sends)
bool send_all(int fd, const uint8_t* data, size_t len,
              std::chrono::milliseconds timeout) {
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = send_with_timeout(
            fd, data + sent, len - sent, 0, timeout);
        if (n <= 0) {
            return false;
        }
        sent += static_cast<size_t>(n);
    }
    return true;
}
```

---

## 3. TLS/SSL Hardening

### 3.1 O Problema: BEAST e DROWN

**BEAST (CVE-2011-3389):** Ataque que explora o modo CBC (Cipher Block Chaining) no TLS 1.0. O atacante pode recuperar dados cifrados manipulando vetores de inicialização.

**DROWN (CVE-2016-0800):** Explora servidores que suportam SSLv2, mesmo que o cliente não o utilize. Um atacante pode descifrar sessões TLS 1.0/1.1 enviando request ao servidor via SSLv2.

### 3.2 Seleção de Cipher Suites

Cipher suites determinam os algoritmos usados para cada fase da conexão TLS. A seleção inadequada pode comprometer toda a segurança.

```
# FORTE (TLS 1.3 — usar preferencialmente):
TLS_AES_256_GCM_SHA384
TLS_CHACHA20_POLY1305_SHA256
TLS_AES_128_GCM_SHA256

# ACEITÁVEL (TLS 1.2 — se necessário por compatibilidade):
ECDHE-RSA-AES256-GCM-SHA384
ECDHE-RSA-AES128-GCM-SHA256
ECDHE-RSA-CHACHA20-POLY1305

# PROIBIDO (descontinuados e vulneráveis):
DES-CBC3-SHA
RC4-SHA
RC4-MD5
AES128-SHA (TLS 1.0 CBC — ataque BEAST)
```

### 3.3 Configuração OpenSSL Hardened para C++

```cpp
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#include <stdexcept>
#include <string>
#include <vector>

class TLSContext {
public:
    explicit TLSContext(bool is_server) {
        ctx_ = SSL_CTX_new(is_server ? TLS_server_method() : TLS_client_method());
        if (!ctx_) {
            throw std::runtime_error("SSL_CTX_new failed");
        }
        configure();
    }

    ~TLSContext() {
        if (ctx_) SSL_CTX_free(ctx_);
    }

    TLSContext(const TLSContext&) = delete;
    TLSContext& operator=(const TLSContext&) = delete;

    SSL_CTX* get() const { return ctx_; }

    void load_certificate_chain(const std::string& cert_file,
                                const std::string& key_file) {
        if (SSL_CTX_use_certificate_chain_file(ctx_, cert_file.c_str()) != 1) {
            throw std::runtime_error("Failed to load certificate chain");
        }
        if (SSL_CTX_use_PrivateKey_file(ctx_, key_file.c_str(),
                                        SSL_FILETYPE_PEM) != 1) {
            throw std::runtime_error("Failed to load private key");
        }
        if (SSL_CTX_check_private_key(ctx_) != 1) {
            throw std::runtime_error("Private key does not match certificate");
        }
    }

    void load_ca_bundle(const std::string& ca_file) {
        if (SSL_CTX_load_verify_locations(ctx_, ca_file.c_str(), nullptr) != 1) {
            throw std::runtime_error("Failed to load CA bundle");
        }
        SSL_CTX_set_verify(ctx_,
                          SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                          nullptr);
    }

private:
    void configure() {
        // Force TLS 1.3 and TLS 1.2 only
        SSL_CTX_set_min_proto_version(ctx_, TLS1_2_VERSION);

        // Explicitly disable old protocols
        SSL_CTX_set_options(ctx_,
            SSL_OP_NO_SSLv2 |      // CVE-2016-0800 (DROWN)
            SSL_OP_NO_SSLv3 |      // POODLE attack
            SSL_OP_NO_TLSv1 |      // BEAST (CVE-2011-3389)
            SSL_OP_NO_TLSv1_1);    // Deprecated

        // Hardened cipher suite list
        const char* cipher_list =
            "ECDHE-ECDSA-AES256-GCM-SHA384:"
            "ECDHE-RSA-AES256-GCM-SHA384:"
            "ECDHE-ECDSA-AES128-GCM-SHA256:"
            "ECDHE-RSA-AES128-GCM-SHA256:"
            "ECDHE-ECDSA-CHACHA20-POLY1305:"
            "ECDHE-RSA-CHACHA20-POLY1305";

        if (SSL_CTX_set_cipher_list(ctx_, cipher_list) != 1) {
            throw std::runtime_error("Failed to set cipher list");
        }

        // Prefer server cipher order
        SSL_CTX_set_options(ctx_, SSL_OP_CIPHER_SERVER_PREFERENCE);

        // Enable ECDHE key exchange
        SSL_CTX_set_ecdh_auto(ctx_, 1);

        // Session cache settings
        SSL_CTX_set_session_cache_mode(ctx_, SSL_SESS_CACHE_SERVER);
        SSL_CTX_sess_set_cache_size(ctx_, 1024);
    }

    SSL_CTX* ctx_;
};

// Certificate pinning implementation
class CertificatePinning {
public:
    // SHA-256 hash of Subject Public Key Info (SPKI)
    struct PinnedHash {
        std::vector<uint8_t> sha256;
        std::string label; // Human-readable label
    };

    bool verify_certificate(X509* cert) const {
        if (!cert || pinned_hashes_.empty()) return false;

        // Get the SPKI from the certificate
        EVP_PKEY* pubkey = X509_get_pubkey(cert);
        if (!pubkey) return false;

        // Encode SPKI to DER
        int len = i2d_PublicKey(pubkey, nullptr);
        if (len <= 0) {
            EVP_PKEY_free(pubkey);
            return false;
        }

        std::vector<unsigned char> spki_der(static_cast<size_t>(len));
        unsigned char* ptr = spki_der.data();
        i2d_PublicKey(pubkey, &ptr);
        EVP_PKEY_free(pubkey);

        // Compute SHA-256 of SPKI
        std::vector<uint8_t> hash(SHA256_DIGEST_LENGTH);
        SHA256(spki_der.data(), spki_der.size(), hash.data());

        // Check against pinned hashes
        for (const auto& pinned : pinned_hashes_) {
            if (hash == pinned.sha256) {
                return true; // Match found
            }
        }

        return false; // No pin matched
    }

    void add_pin(const std::string& base64_sha256, const std::string& label) {
        PinnedHash pin;
        pin.label = label;
        // Decode base64 to bytes
        pin.sha256 = base64_decode(base64_sha256);
        pinned_hashes_.push_back(std::move(pin));
    }

private:
    std::vector<PinnedHash> pinned_hashes_;

    static std::vector<uint8_t> base64_decode(const std::string& input) {
        BIO* b64 = BIO_new(BIO_f_base64());
        BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
        BIO* bmem = BIO_new_mem_buf(input.data(), static_cast<int>(input.size()));
        bmem = BIO_push(b64, bmem);

        std::vector<uint8_t> output(input.size());
        int len = BIO_read(bmem, output.data(), static_cast<int>(output.size()));
        BIO_free_all(bmem);

        if (len > 0) {
            output.resize(static_cast<size_t>(len));
        } else {
            output.clear();
        }
        return output;
    }
};
```

### 3.4 OCSP Stapling

OCSP stapling permite que o servidor forneça o status do certificado diretamente, eliminando que o cliente consulte a CA. Isso melhora privacidade e performance.

```cpp
// Enable OCSP stapling on server context
void enable_ocsp_stapling(SSL_CTX* ctx) {
    // Server side: load OCSP response
    SSL_CTX_set_tlsext_status_type(ctx, TLSEXT_STATUSTYPE_ocsp);
}

// Client side: verify OCSP stapled response
bool verify_ocsp_response(SSL* ssl, X509* cert, X509* issuer) {
    const unsigned char* resp_data = nullptr;
    int resp_len = SSL_get_tlsext_status_ocsp_resp(ssl, &resp_data);

    if (!resp_data || resp_len <= 0) {
        // No stapled response — could fall back to direct OCSP check
        return false;
    }

    OCSP_RESPONSE* resp = d2i_OCSP_RESPONSE(nullptr, &resp_data, resp_len);
    if (!resp) {
        return false;
    }

    OCSP_BASICRESP* basic = OCSP_response_get1_basic(resp);
    OCSP_RESPONSE_free(resp);
    if (!basic) {
        return false;
    }

    X509_STORE* store = X509_STORE_new();
    X509_STORE_add_cert(store, issuer);

    int status = OCSP_basic_verify(basic, cert, store, OCSP_NOCHAIN);
    OCSP_BASICRESP_free(basic);
    X509_STORE_free(store);

    return (status == 1);
}
```

---

## 4. DNS Security

### 4.1 Ataques de DNS Spoofing

DNS spoofing (ou DNS cache poisoning) ocorre quando um atacante injeta registros DNS falsos, redirecionando tráfego legítimo para servidores maliciosos.

O ataque DYN de 2016 explorou dispositivos IoT com credenciais padrão para criar um botnet massivo, gerando tráfego DDoS de mais de 1.2 Tbps contra servidores DNS, afetando Twitter, Netflix, Reddit e outros serviços.

**Mecânica do ataque:** O atacante envia respostas DNS falsificadas antes da resposta legítima, usando IDs de transação previsíveis ou explorando implementações fracas de randomização de porta.

### 4.2 DNSSEC

DNSSEC adiciona assinaturas criptográficas aos registros DNS, permitindo verificação de autenticidade e integridade. Cada zona é assinada com uma chave privada e verificada com a chave pública da zona pai.

### 4.3 DNS over HTTPS (DoH) e DNS over TLS (DoT)

DoH e DoT protegem consultas DNS contra espionagem e manipulação em trânsito. DoH usa HTTPS na porta 443 (mais difícil de bloquear), DoT usa a porta 853.

```cpp
// Secure DNS resolver using HTTPS (DoH)
#include <curl/curl.h>
#include <nlohmann/json.hpp>
#include <string>
#include <vector>

struct DNSRecord {
    std::string name;
    std::string type;
    uint32_t ttl;
    std::string data;
};

class DoHResolver {
public:
    explicit DoHResolver(const std::string& doh_server)
        : doh_server_(doh_server) {
        curl_global_init(CURL_GLOBAL_DEFAULT);
    }

    ~DoHResolver() {
        curl_global_cleanup();
    }

    std::vector<DNSRecord> resolve(const std::string& domain,
                                   const std::string& record_type = "A") {
        std::string url = doh_server_ + "?dns=" + base64url_encode(
            build_dns_query(domain, record_type));

        CURL* curl = curl_easy_init();
        if (!curl) {
            throw std::runtime_error("curl_easy_init failed");
        }

        std::string response;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);

        // TLS verification
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYPEER, 1L);
        curl_easy_setopt(curl, CURLOPT_SSL_VERIFYHOST, 2L);

        CURLcode res = curl_easy_perform(curl);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            throw std::runtime_error(
                std::string("DoH request failed: ") +
                curl_easy_strerror(res));
        }

        return parse_doh_response(response);
    }

private:
    std::string doh_server_;

    static size_t write_callback(char* ptr, size_t size,
                                 size_t nmemb, void* userdata) {
        auto* response = static_cast<std::string*>(userdata);
        response->append(ptr, size * nmemb);
        return size * nmemb;
    }

    // Build raw DNS query wire format
    std::vector<uint8_t> build_dns_query(const std::string& domain,
                                          const std::string& type) {
        std::vector<uint8_t> query;

        // Header
        uint16_t id = generate_random_id();
        query.push_back(static_cast<uint8_t>(id >> 8));
        query.push_back(static_cast<uint8_t>(id & 0xFF));
        query.push_back(0x01); // Standard query
        query.push_back(0x00);
        query.push_back(0x00); // Questions: 1
        query.push_back(0x01);
        query.push_back(0x00); // Answer RRs: 0
        query.push_back(0x00);
        query.push_back(0x00); // Authority RRs: 0
        query.push_back(0x00);
        query.push_back(0x00); // Additional RRs: 0
        query.push_back(0x00);

        // Question section: domain name
        size_t start = 0;
        for (size_t i = 0; i <= domain.size(); ++i) {
            if (i == domain.size() || domain[i] == '.') {
                size_t label_len = i - start;
                if (label_len == 0 || label_len > 63) {
                    throw std::invalid_argument("Invalid DNS label length");
                }
                query.push_back(static_cast<uint8_t>(label_len));
                for (size_t j = start; j < i; ++j) {
                    query.push_back(static_cast<uint8_t>(domain[j]));
                }
                start = i + 1;
            }
        }
        query.push_back(0x00); // Root label terminator

        // QTYPE
        uint16_t qtype = dns_type_from_string(type);
        query.push_back(static_cast<uint8_t>(qtype >> 8));
        query.push_back(static_cast<uint8_t>(qtype & 0xFF));

        // QCLASS: IN (1)
        query.push_back(0x00);
        query.push_back(0x01);

        return query;
    }

    uint16_t dns_type_from_string(const std::string& type) {
        if (type == "A")     return 1;
        if (type == "AAAA")  return 28;
        if (type == "CNAME") return 5;
        if (type == "MX")    return 15;
        if (type == "TXT")   return 16;
        if (type == "HTTPS") return 65;
        throw std::invalid_argument("Unknown DNS type: " + type);
    }

    uint16_t generate_random_id() {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<uint16_t> dist(0, 65535);
        return dist(gen);
    }

    static std::string base64url_encode(const std::vector<uint8_t>& data) {
        const char table[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        std::string result;
        result.reserve(((data.size() + 2) / 3) * 4);

        for (size_t i = 0; i < data.size(); i += 3) {
            uint32_t n = static_cast<uint32_t>(data[i]) << 16;
            if (i + 1 < data.size()) n |= static_cast<uint32_t>(data[i + 1]) << 8;
            if (i + 2 < data.size()) n |= static_cast<uint32_t>(data[i + 2]);

            result.push_back(table[(n >> 18) & 0x3F]);
            result.push_back(table[(n >> 12) & 0x3F]);
            if (i + 1 < data.size()) result.push_back(table[(n >> 6) & 0x3F]);
            else result.push_back('=');
            if (i + 2 < data.size()) result.push_back(table[n & 0x3F]);
            else result.push_back('=');
        }

        // Replace base64 chars with URL-safe variants
        std::replace(result.begin(), result.end(), '+', '-');
        std::replace(result.begin(), result.end(), '/', '_');
        return result;
    }

    std::vector<DNSRecord> parse_doh_response(const std::string& json_str) {
        auto json = nlohmann::json::parse(json_str);
        std::vector<DNSRecord> records;

        for (const auto& answer : json["Answer"]) {
            DNSRecord rec;
            rec.name = answer["name"].get<std::string>();
            rec.type = std::to_string(answer["type"].get<int>());
            rec.ttl = answer["TTL"].get<uint32_t>();
            rec.data = answer["data"].get<std::string>();
            records.push_back(std::move(rec));
        }

        return records;
    }
};
```

---

## 5. Network Segmentation e Firewall

### 5.1 Padrões de Segmentação de Rede

Segmentação limita o impacto de comprometimentos ao restringir comunicação entre zonas de rede. Tipos principais:

- **Segmentação por VLAN:** Separação em camada 2, controlada por switches.
- **Segmentação por sub-rede:** Separação em camada 3, com routing entre segmentos.
- **Microsegmentação:** Controle granular em nível de workload, permitindo apenas comunicações explícitas.

### 5.2 Microsegmentação no Código

```cpp
#include <unordered_set>
#include <string>
#include <vector>
#include <cstdint>

struct FirewallRule {
    enum class Action { ALLOW, DENY, LOG_AND_DENY };

    std::string source_subnet;    // CIDR notation
    uint16_t port;
    std::string protocol;         // "TCP" or "UDP"
    Action action;
    std::string description;
};

class FirewallRuleEngine {
public:
    void add_rule(const FirewallRule& rule) {
        rules_.push_back(rule);
    }

    // Evaluate whether a connection should be allowed
    FirewallRule::Action evaluate(const std::string& source_ip,
                                  uint16_t dest_port,
                                  const std::string& protocol) const {
        for (const auto& rule : rules_) {
            if (rule.protocol != protocol) continue;
            if (rule.port != 0 && rule.port != dest_port) continue;
            if (!ip_matches_cidr(source_ip, rule.source_subnet)) continue;

            // First matching rule wins
            return rule.action;
        }

        // Default: deny (whitelist approach)
        return FirewallRule::Action::DENY;
    }

    // Validate rule configuration
    bool validate_rule(const FirewallRule& rule) const {
        if (rule.source_subnet.empty()) return false;
        if (rule.protocol != "TCP" && rule.protocol != "UDP") return false;
        if (rule.port > 1024 && rule.port != 0) {
            // Privileged ports should be explicitly noted
        }
        // Validate CIDR format
        auto slash_pos = rule.source_subnet.find('/');
        if (slash_pos == std::string::npos) return false;
        std::string ip_part = rule.source_subnet.substr(0, slash_pos);
        std::string cidr_part = rule.source_subnet.substr(slash_pos + 1);

        try {
            int prefix = std::stoi(cidr_part);
            if (prefix < 0 || prefix > 32) return false;
        } catch (...) {
            return false;
        }

        // Validate IP parts
        struct in_addr addr;
        if (::inet_pton(AF_INET, ip_part.c_str(), &addr) != 1) {
            return false;
        }

        return true;
    }

    const std::vector<FirewallRule>& rules() const { return rules_; }

private:
    std::vector<FirewallRule> rules_;

    static bool ip_matches_cidr(const std::string& ip,
                                const std::string& cidr) {
        auto slash_pos = cidr.find('/');
        std::string network = cidr.substr(0, slash_pos);
        int prefix = std::stoi(cidr.substr(slash_pos + 1));

        struct in_addr ip_addr, net_addr;
        if (::inet_pton(AF_INET, ip.c_str(), &ip_addr) != 1) return false;
        if (::inet_pton(AF_INET, network.c_str(), &net_addr) != 1) return false;

        uint32_t ip_n = ntohl(ip_addr.s_addr);
        uint32_t net_n = ntohl(net_addr.s_addr);
        uint32_t mask = prefix == 0 ? 0 : (~0u) << (32 - prefix);

        return (ip_n & mask) == (net_n & mask);
    }
};
```

---

## 6. DDoS Mitigation

### 6.1 Prevenção contra SYN Flood — SYN Cookies

O ataque SYN flood explora o handshake TCP de três vias, inundando o servidor com pacotes SYN sem completar a conexão. SYN cookies evitam a exaustão de state ao codificar informações na sequência inicial.

```cpp
#include <cstdint>
#include <chrono>
#include <arpa/inet.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>

class SYNCookieManager {
public:
    SYNCookieManager() {
        // Generate a random secret for cookie computation
        std::random_device rd;
        secret_ = rd();
    }

    // Generate SYN cookie (sequence number for SYN-ACK)
    uint32_t generate_cookie(const struct in_addr& client_ip,
                             uint16_t client_port,
                             uint32_t server_ip,
                             uint16_t server_port) const {
        uint32_t timestamp = current_timestamp_16();
        uint32_t mss_option = 1; // MSS option indicator

        // Hash the 4-tuple with secret
        uint32_t cookie = hash_tuple(client_ip, client_port,
                                     server_ip, server_port);
        cookie ^= (secret_ ^ timestamp);
        cookie = (cookie & 0x000000FF) | (timestamp << 8);
        cookie |= (mss_option << 28);

        return cookie;
    }

    // Validate SYN cookie from ACK
    bool validate_cookie(const struct in_addr& client_ip,
                         uint16_t client_port,
                         uint32_t server_ip,
                         uint16_t server_port,
                         uint32_t seq_num) const {
        uint32_t timestamp_from_seq = (seq_num >> 8) & 0x0000FFFF;
        uint32_t mss_from_seq = (seq_num >> 28) & 0x01;
        uint32_t current_ts = current_timestamp_16();

        // Check if cookie is within acceptable window (16 seconds)
        uint32_t diff;
        if (current_ts >= timestamp_from_seq) {
            diff = current_ts - timestamp_from_seq;
        } else {
            diff = timestamp_from_seq - current_ts;
        }

        if (diff > 16) {
            return false; // Cookie expired
        }

        // Recompute expected cookie
        uint32_t expected = generate_cookie(client_ip, client_port,
                                            server_ip, server_port);
        expected = (seq_num & 0xFF000000) | (expected & 0x00FFFFFF);

        return seq_num == expected;
    }

    // Get MSS from validated cookie
    uint32_t get_mss(uint32_t seq_num) const {
        return (seq_num >> 28) & 0x01;
    }

private:
    uint32_t secret_;

    uint32_t current_timestamp_16() const {
        auto now = std::chrono::steady_clock::now();
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()).count();
        return static_cast<uint32_t>(ms / 1000) & 0xFFFF;
    }

    uint32_t hash_tuple(const struct in_addr& cip, uint16_t cport,
                        uint32_t sip, uint16_t sport) const {
        uint32_t h = secret_;
        h ^= static_cast<uint32_t>(cip.s_addr);
        h ^= static_cast<uint32_t>(cport) << 16;
        h ^= sip;
        h ^= static_cast<uint32_t>(sport) << 16;
        // Simple mixing function
        h ^= (h >> 16);
        h *= 0x85EBCA6B;
        h ^= (h >> 13);
        h *= 0xC2B2AE35;
        h ^= (h >> 16);
        return h;
    }
};
```

### 6.2 Rate Limiting com Token Bucket

O algoritmo Token Bucket é amplamente utilizado para controle de taxa. Cada "bucket" mantém tokens que são consumidos por cada requisição e repostos periodicamente.

```cpp
#include <chrono>
#include <mutex>
#include <unordered_map>
#include <string>
#include <atomic>

class TokenBucketRateLimiter {
public:
    struct BucketConfig {
        size_t capacity;          // Max tokens (burst size)
        size_t refill_rate;       // Tokens per second
        std::chrono::seconds refill_interval{1};
    };

    explicit TokenBucketRateLimiter(BucketConfig config)
        : config_(std::move(config)) {}

    // Try to consume tokens from bucket identified by key
    bool try_acquire(const std::string& key, size_t tokens = 1) {
        std::lock_guard<std::mutex> lock(mu_);

        auto now = std::chrono::steady_clock::now();
        auto& entry = buckets_[key];

        if (entry.last_refill.time_since_epoch().count() == 0) {
            // First access: initialize bucket
            entry.tokens = config_.capacity;
            entry.last_refill = now;
        } else {
            // Refill tokens based on elapsed time
            auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
                now - entry.last_refill).count();
            size_t new_tokens = static_cast<size_t>(
                elapsed * config_.refill_rate / 1000);
            if (new_tokens > 0) {
                entry.tokens = std::min(entry.tokens + new_tokens,
                                        config_.capacity);
                entry.last_refill = now;
            }
        }

        if (entry.tokens >= tokens) {
            entry.tokens -= tokens;
            total_allowed_++;
            return true;
        }

        total_rejected_++;
        return false;
    }

    // Get current stats
    struct Stats {
        size_t total_allowed;
        size_t total_rejected;
        size_t active_buckets;
    };

    Stats stats() const {
        std::lock_guard<std::mutex> lock(mu_);
        return Stats{
            total_allowed_.load(),
            total_rejected_.load(),
            buckets_.size()
        };
    }

    // Remove expired buckets (call periodically)
    void cleanup(std::chrono::seconds max_idle = std::chrono::seconds(300)) {
        std::lock_guard<std::mutex> lock(mu_);
        auto now = std::chrono::steady_clock::now();

        for (auto it = buckets_.begin(); it != buckets_.end(); ) {
            auto idle = std::chrono::duration_cast<std::chrono::seconds>(
                now - it->second.last_refill);
            if (idle > max_idle) {
                it = buckets_.erase(it);
            } else {
                ++it;
            }
        }
    }

private:
    BucketConfig config_;
    mutable std::mutex mu_;

    struct BucketEntry {
        size_t tokens = 0;
        std::chrono::steady_clock::time_point last_refill{};
    };

    std::unordered_map<std::string, BucketEntry> buckets_;
    std::atomic<size_t> total_allowed_{0};
    std::atomic<size_t> total_rejected_{0};
};
```

### 6.3 Sliding Window Counter

O Sliding Window Counter oferece controle de taxa mais preciso que a janela fixa, ao ponderar contagens parciais entre janelas.

```cpp
#include <chrono>
#include <mutex>
#include <unordered_map>

class SlidingWindowCounter {
public:
    struct WindowConfig {
        std::chrono::seconds window_size{60};
        size_t max_requests{100};
    };

    explicit SlidingWindowCounter(WindowConfig config)
        : config_(std::move(config)) {}

    bool allow_request(const std::string& key) {
        std::lock_guard<std::mutex> lock(mu_);

        auto now = std::chrono::steady_clock::now();
        auto& entry = counters_[key];

        auto window_start = now - config_.window_size;
        auto elapsed = now - entry.window_end;

        if (entry.window_start <= window_start) {
            // Current window has ended or is the first
            entry.prev_count = entry.curr_count;
            entry.curr_count = 0;
            entry.window_start = window_start;
            entry.window_end = now;
        } else {
            // Within current window — compute overlap with previous
            double overlap = 1.0 - static_cast<double>(
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    now - entry.window_start).count()) /
                std::chrono::duration_cast<std::chrono::milliseconds>(
                    config_.window_size).count();
            entry.effective_count = static_cast<size_t>(
                entry.prev_count * overlap + entry.curr_count);
        }

        if (entry.effective_count >= config_.max_requests) {
            return false;
        }

        entry.curr_count++;
        entry.effective_count = entry.prev_count + entry.curr_count;
        return true;
    }

private:
    WindowConfig config_;
    mutable std::mutex mu_;

    struct WindowEntry {
        size_t prev_count = 0;
        size_t curr_count = 0;
        size_t effective_count = 0;
        std::chrono::steady_clock::time_point window_start{};
        std::chrono::steady_clock::time_point window_end{};
    };

    std::unordered_map<std::string, WindowEntry> counters_;
};
```

### 6.4 Throttling por IP e Limites de Pool de Conexões

```cpp
#include <unordered_map>
#include <atomic>
#include <mutex>

class ConnectionThrottler {
public:
    struct ThrottleConfig {
        size_t max_connections_per_ip;
        size_t max_total_connections;
        size_t max_connection_rate_per_sec;
    };

    explicit ConnectionThrottler(ThrottleConfig config)
        : config_(std::move(config)) {}

    bool allow_connection(const std::string& client_ip) {
        std::lock_guard<std::mutex> lock(mu_);

        if (total_connections_.load() >= config_.max_total_connections) {
            return false;
        }

        auto& entry = per_ip_[client_ip];
        if (entry.count >= config_.max_connections_per_ip) {
            return false;
        }

        entry.count++;
        total_connections_++;
        return true;
    }

    void release_connection(const std::string& client_ip) {
        std::lock_guard<std::mutex> lock(mu_);

        auto it = per_ip_.find(client_ip);
        if (it != per_ip_.end() && it->second.count > 0) {
            it->second.count--;
            total_connections_--;

            if (it->second.count == 0) {
                per_ip_.erase(it);
            }
        }
    }

    size_t current_connections() const { return total_connections_.load(); }

private:
    ThrottleConfig config_;
    mutable std::mutex mu_;

    struct IPEntry {
        size_t count = 0;
    };

    std::unordered_map<std::string, IPEntry> per_ip_;
    std::atomic<size_t> total_connections_{0};
};
```

---

## 7. Protocol Design Seguro

### 7.1 Validação de Wire Format

Um protocolo seguro deve definir claramente o formato binário, com validação rigorosa em cada campo. O Mirai botnet (2016) explorou dispositivos IoT que aceitavam comandos sem validação de formato.

### 7.2 Prevenção contra Replay Attacks

Replay attacks ocorrem quando um atacante intercepta e reenvia mensagens válidas. A prevenção requer nonces, timestamps e números de sequência.

### 7.3 Implementação Completa de Protocolo Seguro

```cpp
#include <cstdint>
#include <cstring>
#include <vector>
#include <array>
#include <chrono>
#include <random>
#include <stdexcept>
#include <algorithm>
#include <map>
#include <optional>

#include <openssl/hmac.h>
#include <openssl/rand.h>

#pragma pack(push, 1)
struct SecureMessageHeader {
    uint32_t magic;           // 0x53454352 ("SECR")
    uint32_t version;         // Protocol version
    uint32_t msg_type;        // Message type
    uint64_t sequence;        // Monotonic sequence number
    uint64_t timestamp;       // Unix timestamp (seconds)
    uint32_t payload_len;     // Payload length
    uint8_t  nonce[16];       // Random nonce
    uint8_t  hmac[32];        // HMAC-SHA256
};
#pragma pack(pop)

static constexpr uint32_t PROTO_MAGIC = 0x53454352;
static constexpr uint32_t PROTO_VERSION = 1;
static constexpr size_t MAX_MSG_SIZE = 16 * 1024 * 1024; // 16 MB
static constexpr int64_t MAX_TIMESTAMP_DRIFT = 300; // 5 minutes

enum class MessageType : uint32_t {
    HANDSHAKE     = 0x01,
    HANDSHAKE_ACK = 0x02,
    DATA          = 0x10,
    DATA_ACK      = 0x11,
    HEARTBEAT     = 0x20,
    DISCONNECT    = 0xFF
};

class SecureProtocolHandler {
public:
    SecureProtocolHandler() {
        // Generate unique session key
        session_key_.resize(32);
        if (RAND_bytes(session_key_.data(), 32) != 1) {
            throw std::runtime_error("RAND_bytes failed for session key");
        }
    }

    // Create a protocol message
    std::vector<uint8_t> create_message(
        MessageType type,
        const uint8_t* payload,
        size_t payload_len,
        uint64_t sequence) {

        if (payload_len > MAX_MSG_SIZE) {
            throw std::invalid_argument("Payload too large");
        }

        std::vector<uint8_t> message(sizeof(SecureMessageHeader) + payload_len);
        auto* hdr = reinterpret_cast<SecureMessageHeader*>(message.data());

        hdr->magic = PROTO_MAGIC;
        hdr->version = PROTO_VERSION;
        hdr->msg_type = static_cast<uint32_t>(type);
        hdr->sequence = sequence;
        hdr->timestamp = current_timestamp();
        hdr->payload_len = static_cast<uint32_t>(payload_len);

        // Generate random nonce
        if (RAND_bytes(hdr->nonce, sizeof(hdr->nonce)) != 1) {
            throw std::runtime_error("RAND_bytes failed for nonce");
        }

        // Copy payload
        if (payload_len > 0) {
            std::memcpy(message.data() + sizeof(SecureMessageHeader),
                       payload, payload_len);
        }

        // Compute HMAC over header (excluding HMAC field) + payload
        compute_hmac(message.data(), message.size(), hdr->hmac);

        return message;
    }

    // Validate and parse a received message
    struct ParsedMessage {
        MessageType type;
        uint64_t sequence;
        std::vector<uint8_t> payload;
    };

    std::optional<ParsedMessage> parse_message(const uint8_t* data, size_t len) {
        if (len < sizeof(SecureMessageHeader)) {
            return std::nullopt; // Too short for header
        }

        const auto* hdr = reinterpret_cast<const SecureMessageHeader*>(data);

        // Validate magic
        if (hdr->magic != PROTO_MAGIC) {
            return std::nullopt;
        }

        // Validate version
        if (hdr->version != PROTO_VERSION) {
            return std::nullopt;
        }

        // Validate payload length consistency
        size_t expected_total = sizeof(SecureMessageHeader) + hdr->payload_len;
        if (len < expected_total) {
            return std::nullopt; // Truncated message
        }

        // Validate timestamp (anti-replay)
        int64_t now = current_timestamp();
        int64_t msg_time = static_cast<int64_t>(hdr->timestamp);
        if (std::abs(now - msg_time) > MAX_TIMESTAMP_DRIFT) {
            return std::nullopt; // Message too old or too far in future
        }

        // Validate HMAC
        uint8_t computed_hmac[32];
        compute_hmac(data, len, computed_hmac);
        if (CRYPTO_memcmp(computed_hmac, hdr->hmac, 32) != 0) {
            return std::nullopt; // HMAC mismatch — tampered message
        }

        // Check sequence number (anti-replay)
        if (!validate_sequence(hdr->sequence)) {
            return std::nullopt; // Replayed or out-of-order message
        }

        // Extract payload
        ParsedMessage result;
        result.type = static_cast<MessageType>(hdr->msg_type);
        result.sequence = hdr->sequence;
        if (hdr->payload_len > 0) {
            result.payload.assign(
                data + sizeof(SecureMessageHeader),
                data + sizeof(SecureMessageHeader) + hdr->payload_len);
        }

        return result;
    }

private:
    std::vector<uint8_t> session_key_;
    std::map<uint64_t, bool> seen_sequences_;
    mutable std::mutex seq_mutex_;

    void compute_hmac(const uint8_t* data, size_t len, uint8_t* out) {
        unsigned int hmac_len = 32;
        HMAC(EVP_sha256(),
             session_key_.data(), static_cast<int>(session_key_.size()),
             data, len,
             out, &hmac_len);
    }

    bool validate_sequence(uint64_t seq) {
        std::lock_guard<std::mutex> lock(seq_mutex_);
        if (seen_sequences_.count(seq) > 0) {
            return false; // Replay detected
        }
        seen_sequences_[seq] = true;

        // Cleanup old entries (keep last 10000)
        if (seen_sequences_.size() > 10000) {
            auto it = seen_sequences_.begin();
            seen_sequences_.erase(it, 
                std::next(it, 
                    static_cast<std::ptrdiff_t>(seen_sequences_.size() - 5000)));
        }

        return true;
    }

    static int64_t current_timestamp() {
        return std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }
};
```

---

## 8. HTTP Security

### 8.1 Headers de Segurança HTTP

Headers de segurança adicionam camadas de proteção contra ataques comuns como clickjacking, MIME sniffing e XSS.

| Header | Valor Recomendado | Proteção |
|--------|-------------------|----------|
| Strict-Transport-Security | max-age=63072000; includeSubDomains; preload | Previne downgrade para HTTP |
| Content-Security-Policy | default-src 'self' | Previne XSS e inject |
| X-Content-Type-Options | nosniff | Previne MIME sniffing |
| X-Frame-Options | DENY | Previne clickjacking |
| Referrer-Policy | no-referrer | Previne leak de URLs |
| Permissions-Policy | camera=(), microphone=() | Restringe features |

### 8.2 HTTP Security Middleware em C++

```cpp
#include <string>
#include <unordered_map>
#include <sstream>
#include <algorithm>
#include <cctype>

class HTTPSecurityHeaders {
public:
    struct Config {
        bool enable_hsts = true;
        bool enable_csp = true;
        bool enable_xfo = true;
        bool enable_xcto = true;
        std::string csp_policy;
    };

    explicit HTTPSecurityHeaders(Config config = {})
        : config_(std::move(config)) {
        if (config_.csp_policy.empty()) {
            config_.csp_policy =
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'";
        }
    }

    // Generate security headers for HTTP response
    std::string generate_headers() const {
        std::ostringstream ss;

        if (config_.enable_hsts) {
            ss << "Strict-Transport-Security: "
               << "max-age=63072000; includeSubDomains; preload\r\n";
        }

        if (config_.enable_csp) {
            ss << "Content-Security-Policy: " << config_.csp_policy << "\r\n";
        }

        if (config_.enable_xfo) {
            ss << "X-Frame-Options: DENY\r\n";
        }

        if (config_.enable_xcto) {
            ss << "X-Content-Type-Options: nosniff\r\n";
        }

        ss << "Referrer-Policy: no-referrer\r\n";
        ss << "Permissions-Policy: camera=(), microphone=(), geolocation=()\r\n";
        ss << "X-XSS-Protection: 1; mode=block\r\n";
        ss << "Cache-Control: no-store, no-cache, must-revalidate\r\n";
        ss << "Pragma: no-cache\r\n";

        return ss.str();
    }

    // Validate incoming request headers
    struct ValidationResult {
        bool valid;
        std::string error;
    };

    ValidationResult validate_request(
        const std::unordered_map<std::string, std::string>& headers) const {

        // Check Content-Length bounds
        auto cl = headers.find("content-length");
        if (cl != headers.end()) {
            try {
                size_t len = std::stoull(cl->second);
                if (len > MAX_REQUEST_BODY_SIZE) {
                    return {false, "Request body too large"};
                }
            } catch (...) {
                return {false, "Invalid Content-Length"};
            }
        }

        // Check for suspicious headers
        for (const auto& [key, value] : headers) {
            std::string lower_key = key;
            std::transform(lower_key.begin(), lower_key.end(),
                          lower_key.begin(), ::tolower);

            // Reject Transfer-Encoding variations (chunked smuggling)
            if (lower_key == "transfer-encoding") {
                std::string lower_val = value;
                std::transform(lower_val.begin(), lower_val.end(),
                              lower_val.begin(), ::tolower);
                if (lower_val.find("chunked") != std::string::npos &&
                    headers.count("content-length")) {
                    return {false, "Conflicting Transfer-Encoding and Content-Length"};
                }
            }

            // Reject excessively large header values
            if (value.size() > MAX_HEADER_VALUE_SIZE) {
                return {false, "Header value too large: " + key};
            }
        }

        // Validate Host header
        if (headers.find("host") == headers.end()) {
            return {false, "Missing Host header"};
        }

        return {true, ""};
    }

private:
    Config config_;
    static constexpr size_t MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024; // 10 MB
    static constexpr size_t MAX_HEADER_VALUE_SIZE = 8192;
};

// WebSocket security validation
class WebSocketSecurity {
public:
    struct ValidationResult {
        bool valid;
        std::string error;
    };

    ValidationResult validate_upgrade(
        const std::unordered_map<std::string, std::string>& headers,
        const std::string& allowed_origins) {

        // Must have Upgrade: websocket
        auto upgrade = headers.find("upgrade");
        if (upgrade == headers.end() ||
            to_lower(upgrade->second) != "websocket") {
            return {false, "Missing or invalid Upgrade header"};
        }

        // Must have Connection: Upgrade
        auto connection = headers.find("connection");
        if (connection == headers.end() ||
            to_lower(connection->second).find("upgrade") == std::string::npos) {
            return {false, "Missing or invalid Connection header"};
        }

        // Must have Sec-WebSocket-Key
        if (headers.find("sec-websocket-key") == headers.end()) {
            return {false, "Missing Sec-WebSocket-Key"};
        }

        // Must have Sec-WebSocket-Version: 13
        auto version = headers.find("sec-websocket-version");
        if (version == headers.end() || version->second != "13") {
            return {false, "Invalid WebSocket version"};
        }

        // Validate Origin against whitelist
        auto origin = headers.find("origin");
        if (origin == headers.end()) {
            return {false, "Missing Origin header"};
        }

        if (!is_origin_allowed(origin->second, allowed_origins)) {
            return {false, "Origin not in whitelist"};
        }

        return {true, ""};
    }

private:
    static std::string to_lower(const std::string& s) {
        std::string result = s;
        std::transform(result.begin(), result.end(),
                      result.begin(), ::tolower);
        return result;
    }

    static bool is_origin_allowed(const std::string& origin,
                                  const std::string& allowed) {
        // Simple comma-separated origin whitelist check
        std::istringstream ss(allowed);
        std::string allowed_origin;
        while (std::getline(ss, allowed_origin, ',')) {
            // Trim whitespace
            size_t start = allowed_origin.find_first_not_of(" \t");
            size_t end = allowed_origin.find_last_not_of(" \t");
            if (start != std::string::npos) {
                allowed_origin = allowed_origin.substr(start, end - start + 1);
            }
            if (origin == allowed_origin) {
                return true;
            }
        }
        return false;
    }
};
```

---

## 9. Network Monitoring e Detection

### 9.1 Detecção de Anomalias

Detecção de anomalias em rede envolve identificar padrões que se desviam do comportamento normal. Abordagens incluem análise estatística, assinaturas de ataques e análise de fluxo.

### 9.2 Monitor de Rede em C++

```cpp
#include <unordered_map>
#include <vector>
#include <chrono>
#include <mutex>
#include <atomic>
#include <functional>

struct ConnectionEvent {
    std::string source_ip;
    uint16_t source_port;
    std::string dest_ip;
    uint16_t dest_port;
    std::string protocol;
    size_t bytes_sent;
    size_t bytes_received;
    std::chrono::steady_clock::time_point timestamp;
};

class NetworkMonitor {
public:
    struct DetectionRule {
        std::string name;
        std::function<bool(const ConnectionStats&)> detector;
        enum class Severity { LOW, MEDIUM, HIGH, CRITICAL };
        Severity severity;
    };

    struct ConnectionStats {
        size_t total_connections = 0;
        size_t failed_connections = 0;
        size_t bytes_sent = 0;
        size_t bytes_received = 0;
        std::chrono::steady_clock::time_point first_seen{};
        std::chrono::steady_clock::time_point last_seen{};
    };

    struct Alert {
        std::string rule_name;
        DetectionRule::Severity severity;
        std::string source_ip;
        std::string details;
        std::chrono::steady_clock::time_point timestamp;
    };

    NetworkMonitor() {
        // Default detection rules
        add_rule("high_connection_rate",
            [](const ConnectionStats& s) {
                auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                    s.last_seen - s.first_seen).count();
                return elapsed > 0 &&
                       (s.total_connections / static_cast<size_t>(elapsed)) > 1000;
            },
            DetectionRule::Severity::HIGH);

        add_rule("high_failure_rate",
            [](const ConnectionStats& s) {
                if (s.total_connections < 10) return false;
                double fail_rate = static_cast<double>(s.failed_connections) /
                                   s.total_connections;
                return fail_rate > 0.8;
            },
            DetectionRule::Severity::MEDIUM);

        add_rule("data_exfiltration",
            [](const ConnectionStats& s) {
                return s.bytes_sent > 100 * 1024 * 1024; // > 100 MB sent
            },
            DetectionRule::Severity::CRITICAL);
    }

    void add_rule(const std::string& name,
                  std::function<bool(const ConnectionStats&)> detector,
                  DetectionRule::Severity severity) {
        std::lock_guard<std::mutex> lock(rule_mutex_);
        rules_.push_back({name, std::move(detector), severity});
    }

    void record_event(const ConnectionEvent& event) {
        std::lock_guard<std::mutex> lock(stats_mutex_);

        auto& stats = ip_stats_[event.source_ip];
        stats.total_connections++;
        stats.bytes_sent += event.bytes_sent;
        stats.bytes_received += event.bytes_received;

        auto now = std::chrono::steady_clock::now();
        if (stats.first_seen.time_since_epoch().count() == 0) {
            stats.first_seen = now;
        }
        stats.last_seen = now;

        // Run detection rules
        std::lock_guard<std::mutex> rlock(rule_mutex_);
        for (const auto& rule : rules_) {
            if (rule.detector(stats)) {
                Alert alert;
                alert.rule_name = rule.name;
                alert.severity = rule.severity;
                alert.source_ip = event.source_ip;
                alert.details = "Rule triggered for IP " + event.source_ip;
                alert.timestamp = now;

                std::lock_guard<std::mutex> alock(alert_mutex_);
                alerts_.push_back(std::move(alert));
                alerts_triggered_++;
            }
        }
    }

    std::vector<Alert> get_alerts() const {
        std::lock_guard<std::mutex> lock(alert_mutex_);
        return alerts_;
    }

    size_t alerts_triggered() const { return alerts_triggered_.load(); }

    const std::unordered_map<std::string, ConnectionStats>&
    get_stats() const {
        return ip_stats_;
    }

private:
    mutable std::mutex stats_mutex_;
    mutable std::mutex rule_mutex_;
    mutable std::mutex alert_mutex_;

    std::unordered_map<std::string, ConnectionStats> ip_stats_;
    std::vector<DetectionRule> rules_;
    std::vector<Alert> alerts_;
    std::atomic<size_t> alerts_triggered_{0};
};

// Simple intrusion detection system (IDS) with signature matching
class SignatureBasedIDS {
public:
    struct Signature {
        std::string name;
        std::vector<uint8_t> pattern;
        std::vector<uint8_t> mask;  // 0xFF = must match, 0x00 = wildcard
        NetworkMonitor::DetectionRule::Severity severity;
    };

    void add_signature(const Signature& sig) {
        std::lock_guard<std::mutex> lock(mu_);
        signatures_.push_back(sig);
    }

    std::vector<std::string> inspect(const uint8_t* packet_data,
                                      size_t packet_len) {
        std::lock_guard<std::mutex> lock(mu_);
        std::vector<std::string> matches;

        for (const auto& sig : signatures_) {
            if (sig.pattern.size() > packet_len) continue;

            for (size_t i = 0; i <= packet_len - sig.pattern.size(); ++i) {
                bool found = true;
                for (size_t j = 0; j < sig.pattern.size(); ++j) {
                    uint8_t masked = packet_data[i + j] & sig.mask[j];
                    if (masked != (sig.pattern[j] & sig.mask[j])) {
                        found = false;
                        break;
                    }
                }
                if (found) {
                    matches.push_back(sig.name);
                    break;
                }
            }
        }

        return matches;
    }

private:
    mutable std::mutex mu_;
    std::vector<Signature> signatures_;
};
```

---

## 10. Exemplo Completo: HTTPS Client/Server Seguro

O exemplo a seguir demonstra um servidor HTTPS completo com todas as técnicas de segurança discutidas neste capítulo, incluindo TLS 1.3 forçado, cipher suites fortes, validação de certificados, parsing de requests com bounds checking, headers de segurança, rate limiting e tratamento de erros sem vazamento de informação.

```cpp
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include <chrono>
#include <thread>
#include <mutex>
#include <unordered_map>
#include <sstream>
#include <algorithm>
#include <stdexcept>

// ======================== Rate Limiter ========================

class SimpleRateLimiter {
public:
    struct Config {
        size_t max_requests_per_minute = 60;
        size_t burst_size = 10;
    };

    explicit SimpleRateLimiter(Config cfg = {}) : cfg_(cfg) {}

    bool allow(const std::string& key) {
        std::lock_guard<std::mutex> lock(mu_);
        auto now = std::chrono::steady_clock::now();
        auto& entry = buckets_[key];

        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - entry.window_start).count();
        if (elapsed >= 60) {
            entry.count = 0;
            entry.window_start = now;
        }

        if (entry.count >= cfg_.max_requests_per_minute) {
            return false;
        }
        entry.count++;
        return true;
    }

private:
    Config cfg_;
    mutable std::mutex mu_;
    struct Bucket { size_t count = 0; std::chrono::steady_clock::time_point window_start{}; };
    std::unordered_map<std::string, Bucket> buckets_;
};

// ======================== TLS Context ========================

class ServerTLSContext {
public:
    ServerTLSContext(const std::string& cert, const std::string& key,
                     const std::string& ca) {
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) throw std::runtime_error("SSL_CTX_new failed");

        // TLS 1.3 only (falls back to TLS 1.2 if needed)
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);

        // Disable old protocols
        SSL_CTX_set_options(ctx_,
            SSL_OP_NO_SSLv2 | SSL_OP_NO_SSLv3 |
            SSL_OP_NO_TLSv1 | SSL_OP_NO_TLSv1_1);

        // Strong cipher suites only
        SSL_CTX_set_cipher_list(ctx_,
            "TLS_AES_256_GCM_SHA384:"
            "TLS_CHACHA20_POLY1305_SHA256:"
            "TLS_AES_128_GCM_SHA256");

        // Load certificate
        if (SSL_CTX_use_certificate_chain_file(ctx_, cert.c_str()) != 1) {
            throw std::runtime_error("Failed to load certificate");
        }
        if (SSL_CTX_use_PrivateKey_file(ctx_, key.c_str(),
                                        SSL_FILETYPE_PEM) != 1) {
            throw std::runtime_error("Failed to load private key");
        }
        if (SSL_CTX_check_private_key(ctx_) != 1) {
            throw std::runtime_error("Private key mismatch");
        }

        // Load CA for client verification
        if (SSL_CTX_load_verify_locations(ctx_, ca.c_str(), nullptr) == 1) {
            SSL_CTX_set_verify(ctx_,
                SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                nullptr);
        }
    }

    ~ServerTLSContext() { if (ctx_) SSL_CTX_free(ctx_); }

    SSL_CTX* get() const { return ctx_; }

    ServerTLSContext(const ServerTLSContext&) = delete;
    ServerTLSContext& operator=(const ServerTLSContext&) = delete;

private:
    SSL_CTX* ctx_ = nullptr;
};

// ======================== HTTP Parser ========================

struct HttpRequest {
    std::string method;
    std::string path;
    std::string version;
    std::unordered_map<std::string, std::string> headers;
    std::string body;
    bool valid = false;
};

HttpRequest parse_http_request(const std::string& raw) {
    HttpRequest req;
    size_t header_end = raw.find("\r\n\r\n");
    if (header_end == std::string::npos) {
        return req; // No header terminator found
    }

    std::string headers_part = raw.substr(0, header_end);
    std::istringstream stream(headers_part);
    std::string line;

    // Parse request line
    if (!std::getline(stream, line)) return req;
    if (!line.empty() && line.back() == '\r') line.pop_back();

    std::istringstream req_line(line);
    if (!(req_line >> req.method >> req.path >> req.version)) return req;

    // Validate method
    static const std::vector<std::string> valid_methods = {
        "GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"
    };
    if (std::find(valid_methods.begin(), valid_methods.end(), req.method)
        == valid_methods.end()) {
        return req;
    }

    // Validate path
    if (req.path.empty() || req.path[0] != '/') return req;
    if (req.path.size() > 2048) return req; // Path too long

    // Parse headers
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        if (line.empty()) break;

        auto colon = line.find(':');
        if (colon == std::string::npos) continue;

        std::string key = line.substr(0, colon);
        std::string value = line.substr(colon + 1);
        // Trim whitespace
        size_t start = value.find_first_not_of(" \t");
        if (start != std::string::npos) {
            value = value.substr(start);
        }

        // Case-insensitive key for HTTP
        std::string lower_key = key;
        std::transform(lower_key.begin(), lower_key.end(),
                      lower_key.begin(), ::tolower);
        req.headers[lower_key] = value;
    }

    // Extract body
    size_t body_start = header_end + 4;
    if (body_start < raw.size()) {
        // Enforce body size limit
        size_t max_body = 10 * 1024 * 1024; // 10 MB
        size_t body_len = raw.size() - body_start;
        if (body_len > max_body) return req; // Reject oversized body
        req.body = raw.substr(body_start, body_len);
    }

    req.valid = true;
    return req;
}

// ======================== Security Headers ========================

std::string security_headers() {
    return
        "Strict-Transport-Security: max-age=63072000; includeSubDomains; preload\r\n"
        "Content-Security-Policy: default-src 'self'; script-src 'self'; "
        "style-src 'self'; frame-ancestors 'none'\r\n"
        "X-Content-Type-Options: nosniff\r\n"
        "X-Frame-Options: DENY\r\n"
        "Referrer-Policy: no-referrer\r\n"
        "Permissions-Policy: camera=(), microphone=(), geolocation=()\r\n"
        "Cache-Control: no-store\r\n";
}

// ======================== Response Generator ========================

std::string make_response(int status_code, const std::string& status_text,
                           const std::string& body,
                           const std::string& extra_headers = "") {
    std::ostringstream resp;
    resp << "HTTP/1.1 " << status_code << " " << status_text << "\r\n";
    resp << "Content-Type: text/plain; charset=utf-8\r\n";
    resp << "Content-Length: " << body.size() << "\r\n";
    resp << "Connection: close\r\n";
    resp << security_headers();
    if (!extra_headers.empty()) {
        resp << extra_headers;
    }
    resp << "\r\n";
    resp << body;
    return resp.str();
}

std::string error_response(int code, const std::string& text) {
    return make_response(code, text, text + "\n");
}

// ======================== Client Handler ========================

void handle_client(SSL* ssl, const std::string& client_ip,
                   SimpleRateLimiter& limiter) {
    // Rate limiting
    if (!limiter.allow(client_ip)) {
        std::string resp = error_response(429, "Too Many Requests");
        SSL_write(ssl, resp.data(), static_cast<int>(resp.size()));
        SSL_shutdown(ssl);
        SSL_free(ssl);
        return;
    }

    // Read request with timeout
    std::string raw_request;
    char buffer[4096];
    int total_read = 0;
    constexpr int MAX_REQUEST_SIZE = 1024 * 1024; // 1 MB

    while (total_read < MAX_REQUEST_SIZE) {
        int n = SSL_read(ssl, buffer, sizeof(buffer) - 1);
        if (n <= 0) break;
        buffer[n] = '\0';
        raw_request.append(buffer, static_cast<size_t>(n));
        total_read += n;

        // Check if we have complete headers
        if (raw_request.find("\r\n\r\n") != std::string::npos) {
            break;
        }
    }

    if (raw_request.empty()) {
        SSL_shutdown(ssl);
        SSL_free(ssl);
        return;
    }

    // Parse HTTP request
    HttpRequest req = parse_http_request(raw_request);
    if (!req.valid) {
        std::string resp = error_response(400, "Bad Request");
        SSL_write(ssl, resp.data(), static_cast<int>(resp.size()));
        SSL_shutdown(ssl);
        SSL_free(ssl);
        return;
    }

    // Validate Host header
    if (req.headers.find("host") == req.headers.end()) {
        std::string resp = error_response(400, "Missing Host Header");
        SSL_write(ssl, resp.data(), static_cast<int>(resp.size()));
        SSL_shutdown(ssl);
        SSL_free(ssl);
        return;
    }

    // Route request
    std::string body;
    int status = 200;
    std::string status_text = "OK";

    if (req.method == "GET" && req.path == "/") {
        body = "Secure HTTPS Server - OK\n";
    } else if (req.method == "GET" && req.path == "/health") {
        body = "{\"status\":\"healthy\"}\n";
    } else if (req.method == "POST" && req.path == "/api/data") {
        // Validate Content-Type
        auto ct = req.headers.find("content-type");
        if (ct == req.headers.end() ||
            ct->second.find("application/json") == std::string::npos) {
            status = 415;
            status_text = "Unsupported Media Type";
            body = "Content-Type must be application/json\n";
        } else {
            body = "{\"received\":true}\n";
        }
    } else {
        status = 404;
        status_text = "Not Found";
        body = "Not Found\n";
    }

    std::string resp = make_response(status, status_text, body);
    SSL_write(ssl, resp.data(), static_cast<int>(resp.size()));

    SSL_shutdown(ssl);
    SSL_free(ssl);
}

// ======================== Main Server ========================

int main(int argc, char* argv[]) {
    uint16_t port = 8443;
    if (argc > 1) {
        port = static_cast<uint16_t>(std::atoi(argv[1]));
    }

    // Initialize OpenSSL
    SSL_library_init();
    SSL_load_error_strings();
    OpenSSL_add_all_algorithms();

    // Create TLS context
    ServerTLSContext tls_ctx("server.crt", "server.key", "ca.crt");

    // Create listening socket
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        std::perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if (bind(server_fd, reinterpret_cast<struct sockaddr*>(&addr),
             sizeof(addr)) < 0) {
        std::perror("bind");
        return 1;
    }

    if (listen(server_fd, 128) < 0) {
        std::perror("listen");
        return 1;
    }

    std::printf("HTTPS server listening on port %d\n", port);

    SimpleRateLimiter limiter;

    while (true) {
        struct sockaddr_in client_addr{};
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(server_fd,
            reinterpret_cast<struct sockaddr*>(&client_addr), &client_len);

        if (client_fd < 0) {
            std::perror("accept");
            continue;
        }

        char ip_str[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, ip_str, sizeof(ip_str));
        std::string client_ip(ip_str);

        // Create SSL object
        SSL* ssl = SSL_new(tls_ctx.get());
        SSL_set_fd(ssl, client_fd);

        // Accept TLS handshake
        if (SSL_accept(ssl) <= 0) {
            std::fprintf(stderr, "TLS handshake failed for %s\n", client_ip.c_str());
            SSL_free(ssl);
            close(client_fd);
            continue;
        }

        // Handle client in thread
        std::thread(handle_client, ssl, client_ip,
                    std::ref(limiter)).detach();
    }

    close(server_fd);
    EVP_cleanup();
    return 0;
}
```

---

## 11. Referências

### Documentação e RFCs

- RFC 8446 — The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 7525 — Recommendations for Secure Use of TLS and DTLS
- RFC 5246 — The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 5386 — Better-Than-Nothing Security: An Unauthenticated Mode of IPsec
- RFC 7919 — Negotiated Finite Diffie-Hellman Ephemeral Parameters for TLS
- RFC 8484 — DNS Queries over HTTPS (DoH)
- RFC 7858 — Specification for DNS over TLS (DoT)
- RFC 4033/4034/4035 — DNS Security Extensions (DNSSEC)
- RFC 4987 — TCP SYN Flooding Attacks and Common Mitigations
- RFC 6520 — Transport Layer Security (TLS) and Datagram TLS (DTLS) Heartbeat Extension

### CVEs e Casos Documentados

- CVE-2016-0800 — DROWN: Cross-protocol attack on TLS using SSLv2
- CVE-2011-3389 — BEAST: Browser Exploit Against SSL/TLS
- CVE-2017-13077/13078/13087/13088 — KRACK: Key Reinstallation Attacks on WPA2
- CVE-2020-24588 — FragAttacks: Fragmentation and Aggregation attacks on WiFi
- CVE-2015-0235 — Ghost: Buffer overflow in glibc __nss_hostname_digits_dots
- Mirai Botnet (2016) — Insecure IoT devices with default credentials
- DYN DDoS Attack (2016) — DNS infrastructure exploitation via IoT botnet
- BGP Hijacking (2008) — Pakistan YouTube incident: AS7007 route announcement
- SSLStrip (2009) — HTTPS downgrade via MITM proxy (Moxie Marlinspike)
- TCP Sequence Prediction — Morris (1985) initial sequence number attacks

### Ferramentas e Bibliotecas

- OpenSSL — Biblioteca TLS/SSL de referência
- wolfSSL — Alternativa leve para embedded/IoT
- libcurl — Cliente HTTP com suporte TLS completo
- nlohmann/json — Parsing JSON moderno em C++
- gperftools — Profiling de memória e CPU para detecção de leaks

### Leituras Adicionais

- "Network Security with OpenSSL" — Viega, Messier, Chandra (O'Reilly)
- "TCP/IP Illustrated, Volume 1" — W. Richard Stevens
- "The Tangled Web" — Michal Zalewski (No Starch Press)
- "Bulletproof SSL and TLS" — Ivan Ristic (Feisty Duck)
- OWASP Testing Guide — Testing for Transport Layer Security
- MITRE ATT&CK Framework — Network-based attack techniques
