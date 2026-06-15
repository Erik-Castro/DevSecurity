# Capítulo 14 — Compliance e Normas

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Compreender o panorama de normas e padrões de segurança aplicáveis ao desenvolvimento de software, incluindo a diferença entre conformidade (compliance) e segurança efetiva.
2. Aplicar os padrões OWASP ASVS e SAMM em projetos C++17, mapeando requisitos de verificação para práticas de codificação segura.
3. Implementar código C++17 que atenda aos padrões SEI CERT C++ e MISRA C/C++, utilizando ferramentas de análise estática para garantia de conformidade.
4. Projetar e implementar soluções de software que atendam a regulamentações de privacidade como GDPR e LGPD, incluindo padrões de tratamento de dados sensíveis em C++.
5. Gerenciar Software Bill of Materials (SBOM), dependências e licenças em projetos C++, garantindo conformidade legal e segurança da cadeia de suprimentos.

---

## 1. Panorama de Normas e Padrões

### 1.1 Visão Geral dos Principais Padrões de Segurança

O desenvolvimento seguro de software é orientado por um ecossistema complexo de normas, padrões e regulamentações. Cada um atende a um contexto específico — segurança de aplicação, proteção de dados, segurança industrial ou conformidade organizacional.

**Principais categorias:**

| Categoria | Padrões/Normas | Escopo |
|-----------|----------------|--------|
| Segurança de Aplicação | OWASP ASVS, OWASP SAMM, CERT C++ | Código, arquitetura, processos |
| Segurança Industrial | IEC 62443, NIST SP 800-82 | Sistemas industriais, SCADA |
| Gestão de Segurança | ISO 27001, SOC 2, NIST CSF | Organizações inteiras |
| Privacidade | GDPR, LGPD, CCPA | Tratamento de dados pessoais |
| Conformidade Setorial | PCI DSS, HIPAA, FDA Guidance | Setores específicos |
| Segurança Automotiva | ISO/SAE 21434, UNECE WP.29 | Veículos conectados |
| Cadeia de Suprimentos | SBOM (SPDX, CycloneDX), SLSA | Dependências e componentes |

### 1.2 Compliance vs. Segurança

Uma distinção crítica que todo profissional deve compreender:

**Compliance (Conformidade)** é o ato de atender aos requisitos mínimos estabelecidos por uma norma ou regulamentação. É um piso, não um teto.

**Segurança** é o estado real de proteção contra ameaças. Uma organização pode ser 100% compliance e ainda assim completamente vulnerável.

```
Exemplo: Uma empresa pode ter todos os checkboxes de compliance marcados,
mas se não testa vulnerabilidades, não monitora intrusões e não treina
funcionários, ela NÃO é segura — apenas é conformista.
```

> "Compliance is not security. Compliance is doing what you're told.
> Security is doing what works." — Bruce Schneier

### 1.3 Compliance Voluntário vs. Obrigatório

**Obrigatório (Mandatory):**
- LGPD (Lei Geral de Proteção de Dados) — Brasil
- GDPR (General Data Protection Regulation) — União Europeia
- PCI DSS — para quem processa cartões de pagamento
- HIPAA — dados de saúde nos EUA
- FDA Guidance — dispositivos médicos

**Voluntário (mas recomendado):**
- ISO 27001 — certificação de gestão de segurança
- SOC 2 — relatório de controle organizacional
- OWASP ASVS — verificação de segurança de aplicação
- CERT C++ — codificação segura

### 1.4 Requisitos Específicos por Setor

Cada setor impõe requisitos únicos que impactam diretamente o design e a implementação de software em C++:

**Setor Financeiro:**
- PCI DSS: criptografia de dados em repouso e em trânsito
- SOX: integridade de dados financeiros
- Basel III: modelos de risco computacionais

**Setor de Saúde:**
- HIPAA: proteção de informações de saúde
- FDA: segurança de dispositivos médicos
- IEC 62304: ciclo de vida de software médico

**Setor Automotivo:**
- ISO/SAE 21434: segurança cibernética veicular
- UNECE WP.29: regulamentação de segurança
- AUTOSAR: arquitetura de software automotivo

**Setor de Telecomunicações:**
- 3GPP: padrões de segurança em redes
- NIST: frameworks de segurança cibernética

---

## 2. OWASP ASVS (Application Security Verification Standard)

### 2.1 Níveis de Verificação (V1-V14)

O OWASP ASVS define 14 categorias de requisitos com três níveis de verificação:

| Nível | Descrição | Criticidade |
|-------|-----------|-------------|
| Nível 1 | Verificação básica (mínimo para qualquer aplicação) | Baixa |
| Nível 2 | Verificação intermediária (aplicação com dados sensíveis) | Média |
| Nível 3 | Verificação avançada (aplicação de alta segurança) | Alta |

**Categorias ASVS:**

| ID | Categoria | Descrição |
|----|-----------|-----------|
| V1 | Arquitetura | Requisitos de arquitetura e design de segurança |
| V2 | Autenticação | Verificação de identidade e autenticação |
| V3 | Gerenciamento de Sessão | Controle de sessões e tokens |
| V4 | Controle de Acesso | Autorização e controle de acesso |
| V5 | Validação, Sanitização e Codificação | Entrada de dados e codificação |
| V6 | Criptografia | Armazenamento e transmissão de dados sensíveis |
| V7 | Erros, Logs e Auditoria | Tratamento de erros e logging seguro |
| V8 | Proteção de Dados | Privacidade e proteção de dados |
| V9 | Comunicação | Segurança em comunicações |
| V10 | Segurança de APIs | APIs RESTful e SOAP |
| V11 | Segurança de Componentes | Bibliotecas e componentes de terceiros |
| V12 | Fluxo de Trabalho de Negócios | Controles de processo de negócio |
| V13 | Configuração de Segurança | Hardening e configuração |
| V14 | Segurança de Mobilidade | Aplicações mobile |

### 2.2 Mapeamento ASVS para Práticas C++

```cpp
// ASVS V1.2.3 — Arquitetura de Segurança: Separação de componentes
// Implementação de arquitetura hexagonal em C++17

#include <memory>
#include <string>
#include <unordered_map>
#include <functional>
#include <variant>
#include <optional>
#include <stdexcept>

// Domain layer — sem dependências de infraestrutura
namespace domain {

struct UserId {
    std::string value;
    bool is_valid() const { return !value.empty(); }
};

struct Transaction {
    UserId sender;
    UserId receiver;
    double amount;
    std::string currency;
    
    bool is_valid() const {
        return sender.is_valid() && 
               receiver.is_valid() && 
               amount > 0.0 && 
               !currency.empty();
    }
};

// Port (interface) — contrato de domínio
class TransactionPort {
public:
    virtual ~TransactionPort() = default;
    virtual bool process(const Transaction& tx) = 0;
    virtual std::optional<Transaction> find_by_id(const std::string& id) = 0;
};

// Port de autenticação
class AuthenticationPort {
public:
    virtual ~AuthenticationPort() = default;
    virtual bool authenticate(const std::string& token) = 0;
    virtual UserId get_user_from_token(const std::string& token) = 0;
};

} // namespace domain

// Application layer — orquestra use cases
namespace application {

class TransactionUseCase {
private:
    domain::TransactionPort& transaction_port_;
    domain::AuthenticationPort& auth_port_;

public:
    TransactionUseCase(domain::TransactionPort& tx_port,
                       domain::AuthenticationPort& auth_port)
        : transaction_port_(tx_port), auth_port_(auth_port) {}

    bool execute(const std::string& auth_token,
                 const domain::Transaction& tx) {
        // ASVS V2.1: Autenticação antes de processar
        if (!auth_port_.authenticate(auth_token)) {
            throw std::runtime_error("Authentication failed");
        }

        auto user = auth_port_.get_user_from_token(auth_token);
        
        // ASVS V4.1: Verificação de autorização
        if (tx.sender.value != user.value) {
            throw std::runtime_error("Unauthorized: sender mismatch");
        }

        // Validação de entrada
        if (!tx.is_valid()) {
            throw std::invalid_argument("Invalid transaction");
        }

        return transaction_port_.process(tx);
    }
};

} // namespace application

// Infrastructure layer — adaptações concretas
namespace infrastructure {

// Adapter para banco de dados (exemplo simplificado)
class SqlTransactionAdapter : public domain::TransactionPort {
public:
    bool process(const domain::Transaction& tx) override {
        // Implementação concreta com banco de dados
        return true;
    }
    
    std::optional<domain::Transaction> find_by_id(
        const std::string& id) override {
        return std::nullopt;
    }
};

} // namespace infrastructure
```

### 2.3 Checklist ASVS Completo para Aplicações C++

**V1 — Arquitetura e Design:**

| Requisito | Descrição | Implementação C++ |
|-----------|-----------|-------------------|
| V1.1.1 | Documentação de controles de segurança | Arquitetura hexagonal, portas documentadas |
| V1.2.3 | Separação de componentes | Camadas de domínio, aplicação, infraestrutura |
| V1.4.1 | Análise de ameaças | Threat modeling integrado ao ciclo de vida |

**V2 — Autenticação:**

| Requisito | Descrição | Implementação C++ |
|-----------|-----------|-------------------|
| V2.1.1 | Autenticação mínima | Tokens JWT com verificação criptográfica |
| V2.2.1 | Gerenciamento de senhas | Argon2/bcrypt com salt aleatório |
| V2.7.1 | Autenticação multifator | TOTP/HOTP com clock sync |

```cpp
// ASVS V2.2.1 — Gerenciamento seguro de senhas
// Implementação com Argon2id (OWASP recomendado)

#include <string>
#include <array>
#include <random>
#include <cstring>

// Nota: Em produção, usar biblioteca como argon2-cpp ou libsodium
// Este é um exemplo didático da estrutura

class PasswordHasher {
private:
    struct HashConfig {
        uint32_t memory_cost = 65536;   // 64 MB
        uint32_t time_cost = 3;         // 3 iterações
        uint32_t parallelism = 4;       // 4 threads
        uint32_t hash_length = 32;      // 32 bytes
        uint32_t salt_length = 16;      // 16 bytes
    };

    HashConfig config_;

    std::string generate_salt() const {
        std::array<uint8_t, 16> salt{};
        // Usar fonte criptograficamente segura
        // Em produção: /dev/urandom ou BCryptGenRandom
        std::random_device rd;
        for (auto& byte : salt) {
            byte = static_cast<uint8_t>(rd());
        }
        return std::string(salt.begin(), salt.end());
    }

public:
    explicit PasswordHasher(HashConfig config = {}) 
        : config_(config) {}

    struct HashResult {
        std::string hash;
        std::string salt;
        HashConfig config;
    };

    HashResult hash_password(const std::string& password) const {
        auto salt = generate_salt();
        
        // Simulação — em produção, usar argon2id_hash_raw()
        std::string hash(config_.hash_length, '\0');
        
        // Aqui estaria a chamada real ao Argon2:
        // argon2id_hash_raw(
        //     config_.time_cost,
        //     config_.memory_cost,
        //     config_.parallelism,
        //     password.data(), password.size(),
        //     reinterpret_cast<const uint8_t*>(salt.data()),
        //     salt.size(),
        //     reinterpret_cast<uint8_t*>(hash.data()),
        //     config_.hash_length
        // );

        return HashResult{hash, salt, config_};
    }

    bool verify_password(const std::string& password,
                         const HashResult& stored) const {
        auto computed = hash_password_with_salt(password, stored.salt);
        return constant_time_compare(computed.hash, stored.hash);
    }

private:
    HashResult hash_password_with_salt(const std::string& password,
                                       const std::string& salt) const {
        std::string hash(config_.hash_length, '\0');
        // Chamada real ao Argon2 com salt fornecido
        return HashResult{hash, salt, config_};
    }

    // ASVS V2.2.1: Comparação em tempo constante
    // Prevenção contra timing attacks
    static bool constant_time_compare(const std::string& a,
                                      const std::string& b) {
        if (a.size() != b.size()) {
            return false;
        }
        
        volatile uint8_t result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= static_cast<uint8_t>(a[i]) ^ 
                      static_cast<uint8_t>(b[i]);
        }
        return result == 0;
    }
};
```

### 2.4 Exemplos de Código para Requisitos Principais

```cpp
// ASVS V5.1 — Validação de Entrada
// Padrão de validação com sanitização

#include <string>
#include <string_view>
#include <regex>
#include <algorithm>
#include <cctype>
#include <stdexcept>
#include <optional>

class InputValidator {
public:
    // Validação de email (ASVS V5.1.2)
    static bool is_valid_email(std::string_view email) {
        if (email.empty() || email.size() > 254) {
            return false;
        }

        // RFC 5322 simplificado
        static const std::regex email_regex(
            R"(^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$)"
        );
        return std::regex_match(email.begin(), email.end(), email_regex);
    }

    // Sanitização de entrada para SQL (ASVS V5.3.1)
    // Nunca usar string diretamente — usar prepared statements
    static std::string sanitize_sql_identifier(std::string_view input) {
        std::string result;
        result.reserve(input.size());

        for (char c : input) {
            if (std::isalnum(static_cast<unsigned char>(c)) || c == '_') {
                result += c;
            } else {
                throw std::invalid_argument(
                    "Invalid character in SQL identifier");
            }
        }

        if (result.empty()) {
            throw std::invalid_argument("Empty SQL identifier");
        }

        return result;
    }

    // Validação de número com limites (ASVS V5.1.4)
    static int32_t validate_range(std::string_view input,
                                  int32_t min_val,
                                  int32_t max_val) {
        try {
            size_t pos;
            int32_t value = std::stoi(std::string(input), &pos);
            
            if (pos != input.size()) {
                throw std::invalid_argument("Invalid number format");
            }
            
            if (value < min_val || value > max_val) {
                throw std::out_of_range("Value out of allowed range");
            }
            
            return value;
        } catch (const std::exception&) {
            throw std::invalid_argument("Invalid numeric input");
        }
    }

    // Validação de path (ASVS V5.1.7 — prevenção de path traversal)
    static std::string validate_file_path(std::string_view input) {
        std::string path(input);
        
        // Detectar path traversal
        if (path.find("..") != std::string::npos) {
            throw std::invalid_argument("Path traversal detected");
        }

        // Normalizar separadores
        std::replace(path.begin(), path.end(), '\\', '/');
        
        // Remover duplas barras
        auto new_end = std::unique(path.begin(), path.end(),
            [](char a, char b) { return a == '/' && b == '/'; });
        path.erase(new_end, path.end());

        return path;
    }
};
```

---

## 3. OWASP SAMM (Software Assurance Maturity Model)

### 3.1 Estrutura do SAMM

O SAMM organiza a maturidade de segurança em cinco funções de negócio, cada uma com três práticas:

| Função | Prática 1 | Prática 2 | Prática 3 |
|--------|-----------|-----------|-----------|
| Governança | Estratégia e Métricas | Política e Compliência | Educação e Orientação |
| Design | Requisitos de Segurança | Ameaças e Defesas | Segurança de Arquitetura |
| Implementação | Desenvolvimento Seguro | Verificação de Segurança | Arquitetura de Segurança |
| Verificação | Teste de Requisitos | Teste de Segurança | Verificação de Arquitetura |
| Operações | Monitoramento e Resposta | Gestão de Incidentes | Gerenciamento de Ambientes |

### 3.2 Níveis de Maturidade

| Nível | Descrição | Características |
|-------|-----------|-----------------|
| 0 | Inexistente | Processos não documentados |
| 1 | Inicial | Processos básicos, ad-hoc |
| 2 | Conforme | Processos documentados e repeatáveis |
| 3 | Otimizado | Processos medidos e melhorados continuamente |

### 3.3 Template de Avaliação de Maturidade para Projetos C++

```cpp
// Modelo C++ para avaliação SAMM de um projeto
// Utilizado para medir e acompanhar maturidade de segurança

#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <numeric>

enum class SAMMPractice {
    // Governança
    StrategyMetrics,
    PolicyCompliance,
    EducationGuidance,
    
    // Design
    SecurityRequirements,
    ThreatDefense,
    SecurityArchitecture,
    
    // Implementação
    SecureDevelopment,
    SecurityVerification,
    ArchitectureSecurity,
    
    // Verificação
    RequirementsTesting,
    SecurityTesting,
    ArchitectureVerification,
    
    // Operações
    MonitoringResponse,
    IncidentManagement,
    EnvironmentManagement
};

enum class MaturityLevel {
    None = 0,
    Initial = 1,
    Compliant = 2,
    Optimized = 3
};

struct PracticeAssessment {
    SAMMPractice practice;
    MaturityLevel current_level;
    MaturityLevel target_level;
    std::vector<std::string> evidence;
    std::vector<std::string> gaps;
};

class SAMMAssessment {
private:
    std::string project_name_;
    std::vector<PracticeAssessment> assessments_;

public:
    explicit SAMMAssessment(const std::string& project_name)
        : project_name_(project_name) {}

    void assess(SAMMPractice practice,
                MaturityLevel current,
                MaturityLevel target,
                std::vector<std::string> evidence,
                std::vector<std::string> gaps) {
        assessments_.push_back(PracticeAssessment{
            practice, current, target, 
            std::move(evidence), std::move(gaps)
        });
    }

    double overall_maturity() const {
        if (assessments_.empty()) return 0.0;
        
        int total = std::accumulate(assessments_.begin(), 
            assessments_.end(), 0,
            [](int sum, const PracticeAssessment& a) {
                return sum + static_cast<int>(a.current_level);
            });
        
        return static_cast<double>(total) / 
               static_cast<double>(assessments_.size());
    }

    std::vector<PracticeAssessment> get_gaps() const {
        std::vector<PracticeAssessment> gaps;
        std::copy_if(assessments_.begin(), assessments_.end(),
            std::back_inserter(gaps),
            [](const PracticeAssessment& a) {
                return a.current_level < a.target_level;
            });
        return gaps;
    }

    void generate_report(const std::string& output_path) const {
        std::ofstream file(output_path);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open report file");
        }

        file << "# SAMM Maturity Assessment Report\n\n";
        file << "Project: " << project_name_ << "\n";
        file << "Overall Maturity: " << overall_maturity() << "/3.0\n\n";

        auto gaps = get_gaps();
        if (gaps.empty()) {
            file << "## Status: All practices at target level\n";
        } else {
            file << "## Gaps to Address\n\n";
            for (const auto& gap : gaps) {
                file << "- Practice " 
                     << static_cast<int>(gap.practice)
                     << ": Current=" 
                     << static_cast<int>(gap.current_level)
                     << ", Target=" 
                     << static_cast<int>(gap.target_level)
                     << "\n";
                
                for (const auto& g : gap.gaps) {
                    file << "  - " << g << "\n";
                }
            }
        }
    }
};

// Exemplo de uso
void assess_cpp_project() {
    SAMMAssessment assessment("SecureCppProject");

    // Avaliação de Governança
    assessment.assess(
        SAMMPractice::StrategyMetrics,
        MaturityLevel::Compliant,
        MaturityLevel::Optimized,
        {"Security metrics defined", "Quarterly reviews"},
        {"Automated metric collection needed"}
    );

    // Avaliação de Implementação
    assessment.assess(
        SAMMPractice::SecureDevelopment,
        MaturityLevel::Initial,
        MaturityLevel::Compliant,
        {"Code review process exists"},
        {"Static analysis not integrated",
         "Security training incomplete"}
    );

    assessment.generate_report("samm_report.md");
}
```

---

## 4. CERT C++ Secure Coding Standard

### 4.1 Regras Mais Importantes para Segurança

O CERT C++ Secure Coding Standard define regras para evitar vulnerabilidades comuns em código C++. As regras são organizadas por categorias:

| ID | Categoria | Descrição |
|----|-----------|-----------|
| MEM | Gerenciamento de Memória | Alocação, desalocação, uso de ponteiros |
| STR | Strings e Entrada | Manipulação segura de strings |
| INT | Integridade | Operações que preservam integridade |
| MSC | Diversos | Regras diversas de segurança |
| CON | Concorrência | Problemas de race conditions |
| ERR | Tratamento de Erros | Exceções e códigos de erro |
| OOP | Programação Orientada a Objetos | Padrões OOP seguros |
| CTR | Contêineres | Uso seguro de contêineres |

### 4.2 Regras SEI CERT C++ com Exemplos C++17

#### Regra MEM51-CPP: Gerenciamento de Memória com Smart Pointers

```cpp
// CERT MEM51-CPP: Gerenciar memória com smart pointers
// EVITAR: new/delete manual,造成 memory leaks e dangling pointers

#include <memory>
#include <vector>
#include <iostream>

// RUIM: Memória gerenciada manualmente
class BadResourceManager {
private:
    int* data_;
    size_t size_;

public:
    BadResourceManager(size_t size) 
        : data_(new int[size]), size_(size) {}
    
    // BUG: Destrutor pode ser esquecido
    ~BadResourceManager() { delete[] data_; }
    
    // PROBLEMA: Copy pode causar double-free
    // BadResourceManager(const BadResourceManager&) = default;
};

// BOM: Smart pointers C++17
class GoodResourceManager {
private:
    std::vector<std::unique_ptr<int[]>> buffers_;
    std::shared_ptr<int> shared_counter_;

public:
    explicit GoodResourceManager(size_t size) 
        : shared_counter_(std::make_shared<int>(0)) {
        buffers_.push_back(
            std::make_unique<int[]>(size));
    }

    // Move seguro
    GoodResourceManager(GoodResourceManager&& other) noexcept = default;
    GoodResourceManager& operator=(GoodResourceManager&& other) noexcept = default;

    // Cópia explícita quando necessário
    GoodResourceManager clone() const {
        GoodResourceManager copy(0);
        copy.buffers_.clear();
        
        for (const auto& buf : buffers_) {
            if (buf) {
                // Deep copy do buffer
                copy.buffers_.push_back(
                    std::make_unique<int[]>(1));
                copy.buffers_.back()[0] = buf[0];
            }
        }
        
        copy.shared_counter_ = std::make_shared<int>(
            *shared_counter_);
        return copy;
    }

    void increment() {
        ++(*shared_counter_);
    }

    int counter() const {
        return *shared_counter_;
    }
};
```

#### Regra STR50-CPP: Usar std::string em vez de C-style strings

```cpp
// CERT STR50-CPP: Usar strings seguras
// EVITAR: char[], strcpy, strcat — vulnerabilidades de buffer overflow

#include <string>
#include <string_view>
#include <array>
#include <charconv>
#include <stdexcept>

// RUIM: Uso de C-style strings
void bad_string_handling(const char* input) {
    char buffer[64];
    // PROBLEMA: Buffer overflow se input > 63 caracteres
    strcpy(buffer, input);  // CERT VIOLATION
    // ...
}

// BOM: std::string com verificação de tamanho
class SecureStringBuffer {
private:
    std::string buffer_;
    size_t max_size_;

public:
    explicit SecureStringBuffer(size_t max_size = 1024)
        : max_size_(max_size) {}

    bool append(std::string_view data) {
        if (buffer_.size() + data.size() > max_size_) {
            return false;  // Rejeitar overflow
        }
        buffer_.append(data);
        return true;
    }

    std::string_view view() const {
        return buffer_;
    }

    void clear() {
        buffer_.clear();
    }
};

// Conversão segura de números (C++17 std::from_chars)
template<typename T>
std::optional<T> safe_stoi(std::string_view input) {
    T value{};
    auto [ptr, ec] = std::from_chars(
        input.data(), 
        input.data() + input.size(), 
        value);
    
    if (ec != std::errc() || ptr != input.data() + input.size()) {
        return std::nullopt;
    }
    return value;
}

// Validação de input com sanitização
std::string sanitize_for_display(std::string_view input) {
    std::string result;
    result.reserve(input.size());

    for (char c : input) {
        switch (c) {
            case '<': result += "&lt;"; break;
            case '>': result += "&gt;"; break;
            case '&': result += "&amp;"; break;
            case '"': result += "&quot;"; break;
            case '\'': result += "&#x27;"; break;
            default:
                if (std::isprint(static_cast<unsigned char>(c))) {
                    result += c;
                }
                break;
        }
    }

    return result;
}
```

#### Regra INT32-CPP: Verificar overflow em operações inteiras

```cpp
// CERT INT32-CPP: Verificar overflow em operações inteiras
// EVITAR: Overflow silencioso que pode causar vulnerabilidades

#include <limits>
#include <optional>
#include <cstdint>
#include <stdexcept>

class SafeInteger {
public:
    // Soma segura com verificação de overflow
    static std::optional<int64_t> safe_add(int64_t a, int64_t b) {
        if (b > 0 && a > std::numeric_limits<int64_t>::max() - b) {
            return std::nullopt;  // Overflow
        }
        if (b < 0 && a < std::numeric_limits<int64_t>::min() - b) {
            return std::nullopt;  // Underflow
        }
        return a + b;
    }

    // Subtração segura
    static std::optional<int64_t> safe_sub(int64_t a, int64_t b) {
        if (b > 0 && a < std::numeric_limits<int64_t>::min() + b) {
            return std::nullopt;
        }
        if (b < 0 && a > std::numeric_limits<int64_t>::max() + b) {
            return std::nullopt;
        }
        return a - b;
    }

    // Multiplicação segura
    static std::optional<int64_t> safe_mul(int64_t a, int64_t b) {
        if (a > 0) {
            if (b > 0 && a > std::numeric_limits<int64_t>::max() / b) {
                return std::nullopt;
            }
            if (b < 0 && b < std::numeric_limits<int64_t>::min() / a) {
                return std::nullopt;
            }
        } else if (a < 0) {
            if (b > 0 && a < std::numeric_limits<int64_t>::min() / b) {
                return std::nullopt;
            }
            if (b < 0 && a < std::numeric_limits<int64_t>::max() / b) {
                return std::nullopt;
            }
        }
        return a * b;
    }

    // Divisão segura
    static std::optional<int64_t> safe_div(int64_t a, int64_t b) {
        if (b == 0) {
            return std::nullopt;  // Divisão por zero
        }
        if (a == std::numeric_limits<int64_t>::min() && b == -1) {
            return std::nullopt;  // Overflow
        }
        return a / b;
    }
};

// Exemplo de uso em cálculo de preço
std::optional<int64_t> calculate_total(
    int64_t price_cents, 
    int64_t quantity,
    int64_t discount_cents) {
    
    auto subtotal = SafeInteger::safe_mul(price_cents, quantity);
    if (!subtotal) return std::nullopt;
    
    auto total = SafeInteger::safe_sub(*subtotal, discount_cents);
    if (!total) return std::nullopt;
    
    return total;
}
```

#### Regra CON50-CPP: Evitar Race Conditions

```cpp
// CERT CON50-CPP: Prevenir race conditions
// EVITAR: Acesso compartilhado sem sincronização adequada

#include <mutex>
#include <shared_mutex>
#include <thread>
#include <vector>
#include <atomic>
#include <condition_variable>
#include <functional>

// RUIM: Race condition em contador compartilhado
class BadCounter {
    int count_ = 0;  // Sem proteção!

public:
    void increment() {
        // PROBLEMA: Operação não atômica
        count_++;  // Race condition!
    }

    int get() const { return count_; }
};

// BOM: Contador atômico
class SafeCounter {
    std::atomic<int> count_{0};

public:
    void increment() {
        count_.fetch_add(1, std::memory_order_relaxed);
    }

    int get() const {
        return count_.load(std::memory_order_relaxed);
    }
};

// Padrão Reader-Writer com std::shared_mutex
template<typename T>
class ThreadSafeContainer {
private:
    mutable std::shared_mutex mutex_;
    std::vector<T> data_;
    std::condition_variable_any cv_;

public:
    void add(const T& item) {
        std::unique_lock lock(mutex_);
        data_.push_back(item);
        cv_.notify_all();
    }

    // Leitura concorrente — múltiplos leitores permitidos
    std::vector<T> read_all() const {
        std::shared_lock lock(mutex_);
        return data_;
    }

    // Leitura condicional
    template<typename Pred>
    std::optional<T> find_if(Pred pred) const {
        std::shared_lock lock(mutex_);
        auto it = std::find_if(data_.begin(), data_.end(), pred);
        if (it != data_.end()) {
            return *it;
        }
        return std::nullopt;
    }

    // Espera com timeout
    template<typename Pred>
    std::optional<T> wait_for(Pred pred, 
                               std::chrono::milliseconds timeout) {
        std::unique_lock lock(mutex_);
        if (!cv_.wait_for(lock, timeout, 
            [&]{ return std::any_of(data_.begin(), data_.end(), pred); })) {
            return std::nullopt;
        }
        auto it = std::find_if(data_.begin(), data_.end(), pred);
        return *it;
    }

    size_t size() const {
        std::shared_lock lock(mutex_);
        return data_.size();
    }
};
```

### 4.3 Mapeamento CERT Rules para CWE Entries

| CERT Rule | CWE | Descrição |
|-----------|-----|-----------|
| MEM51-CPP | CWE-401 | Memory Leak |
| MEM52-CPP | CWE-416 | Use After Free |
| STR50-CPP | CWE-120 | Buffer Copy without Checking Size |
| INT32-CPP | CWE-190 | Integer Overflow |
| CON50-CPP | CWE-362 | Race Condition |
| ERR50-CPP | CWE-391 | Unchecked Error Condition |
| OOP50-CPP | CWE-476 | NULL Pointer Dereference |
| CTR50-CPP | CWE-787 | Out-of-bounds Write |

### 4.4 Verificação Automatizada com clang-tidy

```yaml
# .clang-tidy — Configuração para verificação CERT C++
---
Checks: >
  -*,
  cert-*,
  bugprone-*,
  cppcoreguidelines-*,
  misc-*,
  modernize-*,
  performance-*,
  readability-*,
  -modernize-use-trailing-return-type,
  -readability-magic-numbers

WarningsAsErrors: >
  cert-*,
  bugprone-use-after-move,
  bugprone-dangling-handle,
  cppcoreguidelines-avoid-c-arrays,
  cppcoreguidelines-pro-type-member-init

HeaderFilterRegex: 'src/.*\.hpp$'

CheckOptions:
  - key: cert-dcl50-cpp.WarnOnStringFormatFunctions
    value: true
  - key: cert-err58-cpp.WarnOnStatics
    value: true
  - key: cert-oop54-cpp.WarnOnBitwiseOpPrecedence
    value: true
  - key: cert-str34-cpp.WarnOnCharPtr
    value: true
  - key: modernize-use-nullptr.NullMacros
    value: 'NULL'
```

---

## 5. MISRA C/C++

### 5.1 Diretrizes de Codificação para Software Crítico em Segurança

MISRA (Motor Industry Software Reliability Association) é o padrão predominante para software crítico em segurança, originalmente desenvolvido para o setor automotivo mas amplamente adotado em medicina, aviação e defesa.

### 5.2 Regras Obrigatórias, Requeridas e Consultivas

| Categoria | Descrição | Exemplo |
|-----------|-----------|---------|
| Obrigatória (Mandatory) | Deve ser cumprida, sem exceções | Regra 1.3: Não usar recursão |
| Requerida (Required) | Deve ser cumprida, com justificativa documentada para desvio | Regra 17.3: Não usar implícito int |
| Consultiva (Advisory) | Recomendada, pode ser desviada com justificativa | Regra 2.7: Não usar comentários em código |

### 5.3 Regras MISRA de Segurança

```cpp
// MISRA C++ 2023 — Regras de Segurança Relevantes
// Exemplos de conformidade em C++17

#include <cstdint>
#include <array>
#include <optional>
#include <type_traits>
#include <limits>

// Regra 3.1: Usar tipos fixos de largura em vez de int/long
// RUIM:
// int x = 42;  // Tamanho indefinido por plataforma

// BOM:
std::int32_t safe_value = 42;        // Sempre 32 bits
std::uint64_t identifier = 12345ULL; // Sempre 64 bits

// Regra 10.3: Não usar typedef
// RUIM:
// typedef unsigned int uint32_misra;

// BOM:
using uint32_misra = std::uint32_t;  // C++ style

// Regra 14.4: Condições com expressões booleanas
void process_flag(bool is_active) {
    // RUIM:
    // if (is_active == true) { }

    // BOM:
    if (is_active) {
        // Processamento
    }
}

// Regra 15.6: Usar chaves para todos os blocos
void safe_branch(int value) {
    if (value > 0) {
        process_positive(value);
    } else {
        process_non_positive(value);
    }
}

// Regra 18.4: Não usar aritmética de ponteiros
void safe_array_access(const std::array<int, 10>& arr, 
                        std::size_t index) {
    // RUIM:
    // int* ptr = arr.data() + index;  // Pointer arithmetic

    // BOM:
    if (index < arr.size()) {
        int value = arr[index];  // Acesso seguro via índice
    }
}

// Regra 22.10: Não usar recursão
// RUIM:
// int factorial(int n) {
//     if (n <= 1) return 1;
//     return n * factorial(n - 1);  // Recursão proibida
// }

// BOM:
std::int32_t factorial(std::int32_t n) {
    std::int32_t result = 1;
    for (std::int32_t i = 2; i <= n; ++i) {
        result *= i;
    }
    return result;
}
```

### 5.4 Conformidade MISRA em Projetos C++17

```cmake
# CMakeLists.txt — Configuração de conformidade MISRA
cmake_minimum_required(VERSION 3.16)

project(SecureCppProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Habilitar verificações de conformidade
option(ENABLE_MISRA_CHECK "Enable MISRA C++ compliance checks" ON)
option(ENABLE_CERT_CHECK "Enable CERT C++ compliance checks" ON)
option(ENABLE_CPPCHECK "Enable cppcheck static analysis" ON)

if(ENABLE_MISRA_CHECK)
    # Polyspace ou similar (exemplo com flags de compilação)
    add_compile_options(
        -Wall -Wextra -Wpedantic
        -Werror
        -Wshadow
        -Wconversion
        -Wsign-conversion
        -Wnon-virtual-dtor
        -Woverloaded-virtual
        -Wold-style-cast
        -Wcast-align
        -Wunused
        -Woverloaded-virtual
        -Wdouble-promotion
        -Wformat=2
        -Wimplicit-fallthrough
        -Wmisleading-indentation
        -Wduplicated-cond
        -Wduplicated-branches
        -Wlogical-op
        -Wnull-dereference
        -Wuseless-cast
        -Wlifetime
    )
endif()

if(ENABLE_CERT_CHECK)
    add_compile_options(
        -Werror=return-type
        -Werror=init-self
        -Werror=uninitialized
    )
endif()

# Alvo principal
add_library(secure_lib STATIC
    src/input_validator.cpp
    src/safe_integer.cpp
    src/secure_string.cpp
)

target_include_directories(secure_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Análise estática com cppcheck
if(ENABLE_CPPCHECK)
    find_program(CPPCHECK cppcheck)
    if(CPPCHECK)
        set(CMAKE_CXX_CPPCHECK 
            ${CPPCHECK}
            --enable=all
            --std=c++17
            --suppress=missingIncludeSystem
            --error-exitcode=1
            --inline-suppr
            --check-level=exhaustive
        )
    endif()
endif()

# Análise estática com clang-tidy
find_program(CLANG_TIDY clang-tidy)
if(CLANG_TIDY)
    set(CMAKE_CXX_CLANG_TIDY
        ${CLANG_TIDY}
        --checks=cert-*,bugprone-*,cppcoreguidelines-*
        --warnings-as-errors=cert-*
    )
endif()
```

---

## 6. ISO 27001 e SOC 2

### 6.1 Gestão de Segurança da Informação

**ISO 27001** é o padrão internacional para sistemas de gestão de segurança da informação (ISMS). Para desenvolvimento de software, os controles relevantes incluem:

**Controles de Desenvolvimento (Anexo A, controle 14):**

| Controle | Descrição | Implementação C++ |
|----------|-----------|-------------------|
| A.14.1 | Processos seguros de desenvolvimento | Code review, static analysis |
| A.14.2 | Segurança em ambientes de desenvolvimento | CI/CD com verificações de segurança |
| A.14.3 | Dados de teste | Dados sintéticos, não produção |
| A.14.4 | Auditoria durante desenvolvimento | Logs de auditoria no código |

### 6.2 Controles de Segurança para Desenvolvimento de Software

```cpp
// ISO 27001 — Controle A.14.2.5: Engenharia de Segurança na Revisão
// Sistema de code review automatizado com verificações de segurança

#include <string>
#include <vector>
#include <functional>
#include <iostream>
#include <sstream>
#include <algorithm>

struct SecurityCheck {
    std::string name;
    std::string severity;  // "critical", "high", "medium", "low"
    std::function<bool(const std::string&)> check;
    std::string description;
    std::string remediation;
};

class SecurityCodeReviewer {
private:
    std::vector<SecurityCheck> checks_;

public:
    SecurityCodeReviewer() {
        // A.14.2.5: Verificações obrigatórias de segurança
        checks_.push_back({
            "No hardcoded secrets",
            "critical",
            [](const std::string& code) {
                // Verificar por secrets hardcoded
                std::vector<std::string> patterns = {
                    "password", "secret", "api_key", "token",
                    "private_key", "credential"
                };
                for (const auto& pattern : patterns) {
                    if (code.find(pattern) != std::string::npos) {
                        return false;  // Violação encontrada
                    }
                }
                return true;
            },
            "Hardcoded secrets detected in source code",
            "Use environment variables or secret management service"
        });

        checks_.push_back({
            "No unsafe functions",
            "high",
            [](const std::string& code) {
                // Verificar por funções inseguras C
                std::vector<std::string> unsafe = {
                    "sprintf", "strcpy", "strcat", "gets",
                    "scanf", "atoi", "atof"
                };
                for (const auto& func : unsafe) {
                    if (code.find(func) != std::string::npos) {
                        return false;
                    }
                }
                return true;
            },
            "Unsafe C functions detected",
            "Use C++ alternatives: std::string, std::stoi, etc."
        });

        checks_.push_back({
            "Input validation present",
            "medium",
            [](const std::string& code) {
                // Verificar se há validação de entrada
                return code.find("validate") != std::string::npos ||
                       code.find("sanitize") != std::string::npos ||
                       code.find("check") != std::string::npos;
            },
            "No input validation patterns detected",
            "Add input validation for all external data"
        });

        checks_.push_back({
            "RAII for resource management",
            "medium",
            [](const std::string& code) {
                // Verificar uso de smart pointers
                bool has_new = code.find("new ") != std::string::npos;
                bool has_delete = code.find("delete ") != std::string::npos;
                bool has_unique = code.find("unique_ptr") != std::string::npos;
                bool has_shared = code.find("shared_ptr") != std::string::npos;
                
                // Se usa new, deve usar smart pointers
                if (has_new && !has_unique && !has_shared) {
                    return false;
                }
                // Se usa delete, é suspeito
                if (has_delete) {
                    return false;
                }
                return true;
            },
            "Manual memory management detected",
            "Use smart pointers (std::unique_ptr, std::shared_ptr)"
        });
    }

    struct ReviewResult {
        std::string check_name;
        std::string severity;
        bool passed;
        std::string description;
        std::string remediation;
    };

    std::vector<ReviewResult> review(const std::string& code) {
        std::vector<ReviewResult> results;
        
        for (const auto& check : checks_) {
            results.push_back({
                check.name,
                check.severity,
                check.check(code),
                check.description,
                check.remediation
            });
        }
        
        return results;
    }

    void print_report(const std::vector<ReviewResult>& results) {
        std::cout << "\n=== Security Code Review Report ===\n\n";
        
        int passed = 0;
        int failed = 0;

        for (const auto& r : results) {
            if (r.passed) {
                std::cout << "[PASS] " << r.check_name << "\n";
                ++passed;
            } else {
                std::cout << "[FAIL] " << r.check_name 
                          << " (" << r.severity << ")\n";
                std::cout << "  Description: " << r.description << "\n";
                std::cout << "  Remediation: " << r.remediation << "\n\n";
                ++failed;
            }
        }

        std::cout << "\n=== Summary: " << passed << " passed, " 
                  << failed << " failed ===\n";
    }
};
```

### 6.3 Preparação para Auditoria

```cpp
// ISO 27001 — A.12.4: Logging e Auditoria
// Sistema de logging seguro para conformidade

#include <string>
#include <chrono>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <memory>
#include <mutex>
#include <format>

enum class AuditLevel {
    INFO,
    WARNING,
    ERROR,
    CRITICAL
};

class AuditLogger {
private:
    std::ofstream log_file_;
    mutable std::mutex mutex_;
    std::string component_name_;

    std::string level_to_string(AuditLevel level) const {
        switch (level) {
            case AuditLevel::INFO:     return "INFO";
            case AuditLevel::WARNING:  return "WARNING";
            case AuditLevel::ERROR:    return "ERROR";
            case AuditLevel::CRITICAL: return "CRITICAL";
        }
        return "UNKNOWN";
    }

    std::string get_timestamp() const {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
            now.time_since_epoch()) % 1000;

        std::ostringstream oss;
        oss << std::put_time(std::localtime(&time), "%Y-%m-%dT%H:%M:%S");
        oss << '.' << std::setfill('0') << std::setw(3) << ms.count();
        oss << "Z";
        return oss.str();
    }

public:
    AuditLogger(const std::string& filename,
                const std::string& component)
        : component_name_(component) {
        log_file_.open(filename, std::ios::app);
        if (!log_file_.is_open()) {
            throw std::runtime_error("Cannot open audit log file");
        }
    }

    void log(AuditLevel level,
             const std::string& event_type,
             const std::string& user,
             const std::string& details) {
        std::lock_guard lock(mutex_);
        
        // ISO 27001 A.12.4.1: Event logging
        std::ostringstream entry;
        entry << "{\"timestamp\":\"" << get_timestamp()
              << "\",\"level\":\"" << level_to_string(level)
              << "\",\"component\":\"" << component_name_
              << "\",\"event\":\"" << event_type
              << "\",\"user\":\"" << user
              << "\",\"details\":\"" << details
              << "\"}";
        
        log_file_ << entry.str() << "\n";
        log_file_.flush();
    }

    // Log de acesso (A.12.4.1)
    void log_access(const std::string& user,
                    const std::string& resource,
                    bool granted) {
        log(granted ? AuditLevel::INFO : AuditLevel::WARNING,
            "ACCESS", user,
            std::string("Resource: ") + resource + 
            ", Granted: " + (granted ? "true" : "false"));
    }

    // Log de mudança de dados (A.12.4.1)
    void log_data_change(const std::string& user,
                         const std::string& table,
                         const std::string& operation,
                         const std::string& record_id) {
        log(AuditLevel::INFO,
            "DATA_CHANGE", user,
            "Table: " + table + 
            ", Operation: " + operation + 
            ", Record: " + record_id);
    }

    // Log de falha de segurança (A.12.4.1)
    void log_security_event(const std::string& event_type,
                           const std::string& user,
                           const std::string& details) {
        log(AuditLevel::CRITICAL,
            "SECURITY:" + event_type, user, details);
    }
};
```

---

## 7. GDPR, LGPD e Privacidade

### 7.1 Princípios de Proteção de Dados

Tanto o GDPR quanto a LGPD compartilham princípios fundamentais:

| Princípio | GDPR | LGPD | Implementação C++ |
|-----------|------|------|-------------------|
| Finalidade | Art. 5(1)(b) | Art. 6º, I | Controle de uso por finalidade |
| Adequação | Art. 5(1)(b) | Art. 6º, II | Validação de compatibilidade |
| Necessidade | Art. 5(1)(c) | Art. 6º, III | Minimização de dados |
| Qualidade | Art. 5(1)(d) | Art. 6º, IV | Validação e sanitização |
| Segurança | Art. 5(1)(f) | Art. 6º, VII | Criptografia e controle |
| Responsabilização | Art. 5(2) | Art. 6º, X | Auditoria e logging |

### 7.2 Privacy by Design em Código C++

```cpp
// LGPD/GDPR — Privacy by Design
// Implementação de tratamento de dados pessoais com privacidade

#include <string>
#include <vector>
#include <unordered_map>
#include <optional>
#include <memory>
#include <chrono>
#include <algorithm>
#include <functional>
#include <variant>

// Princípio de necessidade: apenas dados necessários
enum class DataCategory {
    Personal,       // Dados pessoais (nome, email)
    Sensitive,      // Dados sensíveis (saúde, biometria)
    Financial,      // Dados financeiros
    Behavioral      // Dados de comportamento
};

enum class LegalBasis {
    Consent,
    Contract,
    LegalObligation,
    VitalInterests,
    PublicTask,
    LegitimateInterests
};

struct DataRecord {
    std::string id;
    DataCategory category;
    LegalBasis legal_basis;
    std::chrono::system_clock::time_point collected_at;
    std::chrono::system_clock::time_point expires_at;
    bool consent_withdrawn = false;
    std::string purpose;
};

// Minimização de dados: reter apenas o necessário
template<typename T>
class PrivacyAwareStorage {
private:
    struct StoredRecord {
        T data;
        DataRecord metadata;
        std::vector<std::string> purposes;
    };

    std::unordered_map<std::string, StoredRecord> records_;
    mutable std::mutex mutex_;

public:
    // Coleta com finalidade específica (LGPD Art. 7º)
    void collect(const std::string& id,
                 const T& data,
                 DataCategory category,
                 LegalBasis basis,
                 const std::string& purpose,
                 std::chrono::hours retention_hours = 720) {
        std::lock_guard lock(mutex_);

        auto now = std::chrono::system_clock::now();
        
        DataRecord metadata{
            id,
            category,
            basis,
            now,
            now + std::chrono::duration_cast<
                std::chrono::system_clock::duration>(retention_hours),
            false,
            purpose
        };

        records_[id] = StoredRecord{data, metadata, {purpose}};
    }

    // Acesso com verificação de finalidade (GDPR Art. 5(1)(b))
    std::optional<T> access(const std::string& id,
                            const std::string& purpose) const {
        std::lock_guard lock(mutex_);

        auto it = records_.find(id);
        if (it == records_.end()) {
            return std::nullopt;
        }

        const auto& record = it->second;

        // Verificar consentimento
        if (record.metadata.consent_withdrawn) {
            return std::nullopt;
        }

        // Verificar expiração
        if (std::chrono::system_clock::now() > record.metadata.expires_at) {
            return std::nullopt;
        }

        // Verificar finalidade (princípio da finalidade)
        auto purpose_it = std::find(
            record.purposes.begin(), 
            record.purposes.end(), 
            purpose);
        
        if (purpose_it == record.purposes.end()) {
            return std::nullopt;  // Finalidade não autorizada
        }

        return record.data;
    }

    // Direito ao esquecimento (LGPD Art. 18, VI)
    void erase(const std::string& id) {
        std::lock_guard lock(mutex_);
        records_.erase(id);
    }

    // Retirada de consentimento (LGPD Art. 8º, §5º)
    void withdraw_consent(const std::string& id) {
        std::lock_guard lock(mutex_);
        auto it = records_.find(id);
        if (it != records_.end()) {
            it->second.metadata.consent_withdrawn = true;
        }
    }

    // Portabilidade de dados (LGPD Art. 18, II)
    std::vector<std::pair<std::string, T>> export_data(
        const std::string& purpose) const {
        std::lock_guard lock(mutex_);
        
        std::vector<std::pair<std::string, T>> result;
        
        for (const auto& [id, record] : records_) {
            if (record.metadata.consent_withdrawn) continue;
            if (std::chrono::system_clock::now() > 
                record.metadata.expires_at) continue;
            
            auto purpose_it = std::find(
                record.purposes.begin(),
                record.purposes.end(),
                purpose);
            
            if (purpose_it != record.purposes.end()) {
                result.emplace_back(id, record.data);
            }
        }
        
        return result;
    }

    // Limpeza de dados expirados
    size_t cleanup_expired() {
        std::lock_guard lock(mutex_);
        
        size_t count = 0;
        auto now = std::chrono::system_clock::now();
        
        for (auto it = records_.begin(); it != records_.end(); ) {
            if (now > it->second.metadata.expires_at) {
                it = records_.erase(it);
                ++count;
            } else {
                ++it;
            }
        }
        
        return count;
    }

    // Relatório de dados para auditoria (LGPD Art. 37)
    struct DataReport {
        std::string id;
        DataCategory category;
        LegalBasis basis;
        std::string purpose;
        bool is_expired;
        bool consent_withdrawn;
    };

    std::vector<DataReport> generate_report() const {
        std::lock_guard lock(mutex_);
        
        std::vector<DataReport> report;
        auto now = std::chrono::system_clock::now();
        
        for (const auto& [id, record] : records_) {
            report.push_back(DataReport{
                id,
                record.metadata.category,
                record.metadata.legal_basis,
                record.metadata.purpose,
                now > record.metadata.expires_at,
                record.metadata.consent_withdrawn
            });
        }
        
        return report;
    }
};
```

### 7.3 Criptografia de Dados Pessoais

```cpp
// LGPD/GDPR — Criptografia de dados pessoais em repouso
// Art. 46: Medidas de segurança para proteção de dados

#include <string>
#include <vector>
#include <array>
#include <memory>
#include <stdexcept>
#include <cstring>

// Interface abstrata para criptografia (HSM/KMS ready)
class EncryptionProvider {
public:
    virtual ~EncryptionProvider() = default;
    
    virtual std::vector<uint8_t> encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& key) = 0;
    
    virtual std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& key) = 0;
    
    virtual std::vector<uint8_t> generate_key(size_t bits) = 0;
    
    virtual std::vector<uint8_t> generate_iv(size_t size) = 0;
};

// Wrapper para dados pessoais criptografados
template<typename T>
class EncryptedPersonalData {
private:
    std::vector<uint8_t> encrypted_data_;
    std::vector<uint8_t> iv_;
    std::string data_id_;
    EncryptionProvider& provider_;

public:
    EncryptedPersonalData(const T& data,
                          const std::vector<uint8_t>& key,
                          EncryptionProvider& provider,
                          const std::string& id)
        : provider_(provider), data_id_(id) {
        // Serializar dados
        std::vector<uint8_t> plaintext(
            reinterpret_cast<const uint8_t*>(&data),
            reinterpret_cast<const uint8_t*>(&data) + sizeof(T));
        
        // Gerar IV aleatório
        iv_ = provider_.generate_iv(16);
        
        // Criptografar
        encrypted_data_ = provider_.encrypt(plaintext, key);
    }

    T decrypt(const std::vector<uint8_t>& key) const {
        auto plaintext = provider_.decrypt(encrypted_data_, key);
        
        if (plaintext.size() != sizeof(T)) {
            throw std::runtime_error("Decrypted data size mismatch");
        }
        
        T result;
        std::memcpy(&result, plaintext.data(), sizeof(T));
        return result;
    }

    const std::string& id() const { return data_id_; }
    bool is_encrypted() const { return !encrypted_data_.empty(); }
};
```

### 7.4 Requisitos Específicos da LGPD para Empresas Brasileiras

| Artigo | Requisito | Implementação Técnica |
|--------|-----------|----------------------|
| Art. 37 | Registro de operações de tratamento | AuditLogger, DataReport |
| Art. 38 | Relatório de impacto | Métricas de coleta e uso |
| Art. 41 | Encarregado de dados | API de contato documentada |
| Art. 46 | Segurança e sigilo | Criptografia, controle de acesso |
| Art. 48 | Comunicação de incidentes | Sistema de alertas automatizado |
| Art. 49 | Privacy by design | PrivacyAwareStorage |
| Art. 50 | Certificação e selo | Frameworks de conformidade |

---

## 8. CWE Taxonomy e Mapping

### 8.1 CWE Top 25 (2023/2024)

| Rank | CWE | Descrição | Score |
|------|-----|-----------|-------|
| 1 | CWE-787 | Out-of-bounds Write | 66.03 |
| 2 | CWE-79 | Improper Neutralization of Input During Web Page Generation | 49.98 |
| 3 | CWE-89 | Improper Neutralization of Special Elements used in an SQL Command | 45.17 |
| 4 | CWE-416 | Use After Free | 27.75 |
| 5 | CWE-78 | Improper Neutralization of Special Elements used in an OS Command | 26.01 |
| 6 | CWE-20 | Improper Input Validation | 24.15 |
| 7 | CWE-125 | Out-of-bounds Read | 18.52 |
| 8 | CWE-22 | Improper Limitation of a Pathname to a Restricted Directory | 17.93 |
| 9 | CWE-352 | Cross-Site Request Forgery | 16.34 |
| 10 | CWE-434 | Unrestricted Upload of File with Dangerous Type | 15.77 |
| 11 | CWE-862 | Missing Authorization | 14.89 |
| 12 | CWE-863 | Incorrect Authorization | 14.24 |
| 13 | CWE-798 | Use of Hard-coded Credentials | 13.95 |
| 14 | CWE-306 | Missing Authentication for Critical Function | 13.54 |
| 15 | CWE-190 | Integer Overflow or Wraparound | 12.93 |
| 16 | CWE-502 | Deserialization of Untrusted Data | 12.62 |
| 17 | CWE-287 | Improper Authentication | 12.13 |
| 18 | CWE-476 | NULL Pointer Dereference | 11.89 |
| 19 | CWE-22 | Improper Limitation of a Pathname | 11.77 |
| 20 | CWE-732 | Incorrect Permission Assignment for Critical Resource | 11.65 |
| 21 | CWE-94 | Improper Control of Generation of Code | 11.49 |
| 22 | CWE-611 | Improper Restriction of XML External Entity Reference | 11.21 |
| 23 | CWE-918 | Server-Side Request Forgery | 10.68 |
| 24 | CWE-77 | Improper Neutralization of Special Elements used in a Command | 10.34 |
| 25 | CWE-306 | Missing Authentication for Critical Function | 10.08 |

### 8.2 Mapeamento CWE para Padrões de Código C++

```cpp
// CWE Top 25 — Mapeamento para padrões de código C++
// Exemplos de mitigação para as vulnerabilidades mais comuns

#include <string>
#include <vector>
#include <memory>
#include <array>
#include <optional>
#include <algorithm>
#include <span>
#include <cstring>

// CWE-787: Out-of-bounds Write
// Mitigação: bounds checking, span, std::array
class SafeBuffer {
private:
    std::array<uint8_t, 1024> buffer_{};
    size_t size_ = 0;

public:
    // USO DE std::span para acesso seguro
    std::span<uint8_t> data() {
        return std::span(buffer_.data(), size_);
    }

    std::span<const uint8_t> data() const {
        return std::span(buffer_.data(), size_);
    }

    bool write(std::span<const uint8_t> input) {
        if (input.size() > buffer_.size() - size_) {
            return false;  // Prevent overflow
        }
        std::copy(input.begin(), input.end(), 
                  buffer_.begin() + size_);
        size_ += input.size();
        return true;
    }

    size_t size() const { return size_; }
    size_t capacity() const { return buffer_.size(); }
};

// CWE-416: Use After Free
// Mitigação: smart pointers, ownership semantics
class SafeResource {
private:
    struct ResourceData {
        std::string name;
        std::vector<uint8_t> data;
        
        ~ResourceData() {
            // Secure cleanup
            std::fill(data.begin(), data.end(), 0);
        }
    };

    std::shared_ptr<ResourceData> data_;

public:
    SafeResource() : data_(std::make_shared<ResourceData>()) {}
    
    // Cópia segura via shared_ptr
    SafeResource(const SafeResource&) = default;
    SafeResource& operator=(const SafeResource&) = default;

    // Move seguro
    SafeResource(SafeResource&&) noexcept = default;
    SafeResource& operator=(SafeResource&&) noexcept = default;

    void set_name(const std::string& name) {
        if (data_) {
            data_->name = name;
        }
    }

    std::optional<std::string> get_name() const {
        if (data_) {
            return data_->name;
        }
        return std::nullopt;
    }
};

// CWE-190: Integer Overflow
// Mitigação: checked arithmetic
class CheckedArithmetic {
public:
    static std::optional<int64_t> add(int64_t a, int64_t b) {
        if (b > 0 && a > INT64_MAX - b) return std::nullopt;
        if (b < 0 && a < INT64_MIN - b) return std::nullopt;
        return a + b;
    }

    static std::optional<int64_t> multiply(int64_t a, int64_t b) {
        if (a > 0) {
            if (b > 0 && a > INT64_MAX / b) return std::nullopt;
            if (b < 0 && b < INT64_MIN / a) return std::nullopt;
        } else if (a < 0) {
            if (b > 0 && a < INT64_MIN / b) return std::nullopt;
            if (b < 0 && a < INT64_MAX / b) return std::nullopt;
        }
        return a * b;
    }

    static std::optional<size_t> to_size_t(int64_t value) {
        if (value < 0) return std::nullopt;
        if (static_cast<uint64_t>(value) > SIZE_MAX) return std::nullopt;
        return static_cast<size_t>(value);
    }
};

// CWE-798: Use of Hard-coded Credentials
// Mitigação: externalized configuration
class CredentialManager {
private:
    struct Credential {
        std::string username;
        std::string encrypted_password;
        std::chrono::system_clock::time_point last_rotated;
    };

    std::unordered_map<std::string, Credential> credentials_;

public:
    // Carregar de vault externo (HashiCorp Vault, AWS Secrets Manager)
    bool load_from_vault(const std::string& vault_addr,
                        const std::string& token) {
        // Em produção: conectar ao vault e obter credentials
        // NUNCA armazenar em código fonte
        return true;
    }

    std::optional<Credential> get_credential(
        const std::string& service) const {
        auto it = credentials_.find(service);
        if (it != credentials_.end()) {
            return it->second;
        }
        return std::nullopt;
    }

    // Rotação automática de credenciais
    void rotate_credentials(const std::string& service) {
        auto it = credentials_.find(service);
        if (it != credentials_.end()) {
            // Gerar novas credenciais
            it->second.last_rotated = 
                std::chrono::system_clock::now();
        }
    }
};
```

### 8.3 CWE como Oráculo de Teste

```cpp
// CWE — Testes baseados em CWE para verificação de segurança
// Cada teste verifica uma vulnerabilidade CWE específica

#include <gtest/gtest.h>
#include <string>
#include <vector>
#include <array>

// CWE-787: Teste de buffer overflow
class CweBufferOverflowTest : public ::testing::Test {
protected:
    SafeBuffer buffer;
};

TEST_F(CweBufferOverflowTest, NormalWrite) {
    // Escrita dentro do limite
    std::vector<uint8_t> data = {1, 2, 3, 4, 5};
    EXPECT_TRUE(buffer.write(std::span(data)));
    EXPECT_EQ(buffer.size(), 5u);
}

TEST_F(CweBufferOverflowTest, OverflowPrevented) {
    // Tentativa de overflow deve ser prevenida
    std::vector<uint8_t> large_data(2048, 0xFF);
    EXPECT_FALSE(buffer.write(std::span(large_data)));
    EXPECT_EQ(buffer.size(), 0u);
}

// CWE-416: Teste de use-after-free
class CweUseAfterFreeTest : public ::testing::Test {
protected:
};

TEST_F(CweUseAfterFreeTest, SharedOwnershipSafe) {
    SafeResource r1;
    r1.set_name("test");
    
    SafeResource r2 = r1;  // Cópia compartilhada
    
    EXPECT_EQ(r1.get_name(), "test");
    EXPECT_EQ(r2.get_name(), "test");
    
    r1 = SafeResource();  // r1 resetado, r2 ainda válido
    
    // r2 ainda funciona — não há use-after-free
    EXPECT_EQ(r2.get_name(), "test");
}

// CWE-190: Teste de integer overflow
class CweIntegerOverflowTest : public ::testing::Test {
protected:
};

TEST_F(CweIntegerOverflowTest, SafeAddition) {
    auto result = CheckedArithmetic::add(100, 200);
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(*result, 300);
}

TEST_F(CweIntegerOverflowTest, OverflowDetected) {
    auto result = CheckedArithmetic::add(
        INT64_MAX, 1);
    EXPECT_FALSE(result.has_value());
}

// CWE-798: Teste de credenciais hardcoded
class CweHardcodedCredentialsTest : public ::testing::Test {
protected:
};

TEST_F(CweHardcodedCredentialsTest, NoHardcodedCredentials) {
    // Verificar que o código fonte não contém credenciais hardcoded
    // Este teste é executado como estática analysis
    CredentialManager mgr;
    
    // Em produção: carregar de vault
    // EXPECT_TRUE(mgr.load_from_vault("https://vault:8200", token));
}
```

---

## 9. SBOM (Software Bill of Materials)

### 9.1 O que é SBOM e por que Importa

Um SBOM é um inventário formal de todos os componentes, bibliotecas e dependências em um software. É essencial para:

- **Vulnerabilidade**: identificar componentes afetados por CVEs
- **Licenciamento**: garantir conformidade legal
- **Segurança da cadeia de suprimentos**: rastrear origem dos componentes
- **Compliance**: atender a requisitos regulatórios

### 9.2 Formatos SPDX e CycloneDX

| Formato | Organização | Uso Principal |
|---------|-------------|---------------|
| SPDX | Linux Foundation | Licenciamento, compliance |
| CycloneDX | OWASP | Segurança, vulnerabilidades |

### 9.3 Geração de SBOM para Projetos C++

```cpp
// SBOM — Geração de Software Bill of Materials
// Formato CycloneDX para projetos C++/CMake

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <iostream>
#include <filesystem>
#include <algorithm>
#include <optional>
#include <json/json.h>  // JsonCpp ou nlohmann/json

struct Component {
    std::string name;
    std::string version;
    std::string supplier;
    std::string license;
    std::string purl;     // Package URL
    std::string cpe;      // Common Platform Enumeration
    std::vector<std::string> hashes;
    std::string description;
};

struct Vulnerability {
    std::string id;          // CVE ID
    std::string severity;
    std::string description;
    std::string reference_url;
    std::string match_version;
};

class SBOMGenerator {
private:
    std::vector<Component> components_;
    std::vector<Vulnerability> vulnerabilities_;
    std::string project_name_;
    std::string project_version_;

public:
    SBOMGenerator(const std::string& name, 
                  const std::string& version)
        : project_name_(name), project_version_(version) {}

    void add_component(const Component& comp) {
        components_.push_back(comp);
    }

    void add_vulnerability(const Vulnerability& vuln) {
        vulnerabilities_.push_back(vuln);
    }

    // Gerar SBOM em formato CycloneDX JSON
    std::string generate_cyclonedx() const {
        Json::Value root;
        root["bomFormat"] = "CycloneDX";
        root["specVersion"] = "1.4";
        root["version"] = 1;

        // Metadata
        auto& metadata = root["metadata"];
        auto& tool = metadata["tool"];
        tool["vendor"] = "DevSecurity";
        tool["name"] = "cpp-sbom-generator";
        tool["version"] = "1.0.0";

        auto& timestamp = metadata["timestamp"];
        timestamp = get_timestamp();

        auto& component = metadata["component"];
        component["name"] = project_name_;
        component["version"] = project_version_;
        component["type"] = "application";

        // Componentes
        auto& components = root["components"];
        for (const auto& comp : components_) {
            Json::Value comp_json;
            comp_json["type"] = "library";
            comp_json["name"] = comp.name;
            comp_json["version"] = comp.version;
            comp_json["supplier"]["name"] = comp.supplier;
            comp_json["description"] = comp.description;

            // Licença
            auto& licenses = comp_json["licenses"];
            auto& license = licenses[0];
            license["license"]["name"] = comp.license;

            // Package URL
            comp_json["purl"] = comp.purl;

            // CPE
            if (!comp.cpe.empty()) {
                comp_json["cpe"] = comp.cpe;
            }

            components.append(comp_json);
        }

        // Vulnerabilidades
        auto& vulns = root["vulnerabilities"];
        for (const auto& vuln : vulnerabilities_) {
            Json::Value vuln_json;
            vuln_json["id"] = vuln.id;
            vuln_json["description"] = vuln.description;
            vuln_json["severity"] = vuln.severity;
            vuln_json["references"][0]["url"] = vuln.reference_url;

            auto& affects = vuln_json["affects"];
            auto& target = affects[0];
            target["ref"] = vuln.match_version;

            vulns.append(vuln_json);
        }

        // Serializar para JSON
        Json::StreamWriterBuilder writer;
        writer["indentation"] = "  ";
        return Json::writeString(writer, root);
    }

    // Gerar SBOM em formato SPDX
    std::string generate_spdx() const {
        std::ostringstream spdx;
        
        spdx << "SPDXVersion: SPDX-2.3\n";
        spdx << "DataLicense: CC0-1.0\n";
        spdx << "SPDXID: SPDXRef-DOCUMENT\n";
        spdx << "DocumentName: " << project_name_ << "\n";
        spdx << "DocumentNamespace: https://devsecurity.io/"
             << project_name_ << "\n";
        spdx << "Creator: Tool: cpp-sbom-generator\n";
        spdx << "Created: " << get_timestamp() << "\n\n";

        spdx << "PackageName: " << project_name_ << "\n";
        spdx << "SPDXID: SPDXRef-Package\n";
        spdx << "PackageVersion: " << project_version_ << "\n";
        spdx << "PackageDownloadLocation: NOASSERTION\n";
        spdx << "FilesAnalyzed: false\n\n";

        for (size_t i = 0; i < components_.size(); ++i) {
            const auto& comp = components_[i];
            spdx << "PackageName: " << comp.name << "\n";
            spdx << "SPDXID: SPDXRef-Package-" << i << "\n";
            spdx << "PackageVersion: " << comp.version << "\n";
            spdx << "PackageDownloadLocation: NOASSERTION\n";
            spdx << "LicenseConcluded: " << comp.license << "\n";
            spdx << "LicenseDeclared: " << comp.license << "\n";
            spdx << "PackageSupplier: " << comp.supplier << "\n\n";
        }

        return spdx.str();
    }

    // Salvar SBOM em arquivo
    void save(const std::string& filename, 
              const std::string& format = "cyclonedx") {
        std::string content;
        if (format == "spdx") {
            content = generate_spdx();
        } else {
            content = generate_cyclonedx();
        }

        std::ofstream file(filename);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open SBOM file: " + filename);
        }
        file << content;
    }

private:
    std::string get_timestamp() const {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::ostringstream oss;
        oss << std::put_time(std::gmtime(&time), "%Y-%m-%dT%H:%M:%SZ");
        return oss.str();
    }
};

// Exemplo de uso com projeto CMake
void generate_project_sbom() {
    SBOMGenerator sbom("SecureCppApp", "1.0.0");

    // Adicionar dependências do CMake
    sbom.add_component({
        "nlohmann-json",
        "3.11.2",
        "Niels Lohmann",
        "MIT",
        "pkg:github/nlohmann/json@3.11.2",
        "cpe:2.3:a:nlohmann:json:3.11.2:*:*:*:*:*:*:*",
        {},
        "JSON for Modern C++"
    });

    sbom.add_component({
        "OpenSSL",
        "3.1.4",
        "OpenSSL Project",
        "Apache-2.0",
        "pkg:github/openssl/openssl@3.1.4",
        "cpe:2.3:a:openssl:openssl:3.1.4:*:*:*:*:*:*:*",
        {},
        "Cryptography and SSL/TLS Toolkit"
    });

    // Adicionar vulnerabilidade conhecida
    sbom.add_vulnerability({
        "CVE-2023-5678",
        "high",
        "Buffer overflow in OpenSSL X.509 certificate verification",
        "https://nvd.nist.gov/vuln/detail/CVE-2023-5678",
        "OpenSSL < 3.1.5"
    });

    sbom.save("sbom_cyclonedx.json");
    sbom.save("sbom_spdx.txt", "spdx");
}
```

---

## 10. Licenças e Dependências Seguras

### 10.1 Implicações de Segurança de Licenças Open Source

| Licença | Copyleft | Distribuição | Commercial Use | Security Implications |
|---------|----------|--------------|----------------|----------------------|
| MIT | No | Yes | Yes | Baixa — permisiva |
| Apache-2.0 | No | Yes | Yes | Baixa — inclui patentes |
| GPL-3.0 | Yes | Yes | Yes | Média — pode exigir revelação |
| LGPL-3.0 | Partial | Yes | Yes | Média — dynamic linking |
| AGPL-3.0 | Yes (network) | Yes | Yes | Alta — SaaS deve liberar código |
| BSD-3 | No | Yes | Yes | Baixa — permisiva |
| MPL-2.0 | File-level | Yes | Yes | Baixa — arquivo específico |

### 10.2 Varredura de Vulnerabilidades em Dependências

```cpp
// Dependências Seguras — Varredura e auditoria
// Sistema de verificação de dependências para projetos C++

#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <regex>

struct Dependency {
    std::string name;
    std::string version;
    std::string license;
    std::string source;  // vcpkg, conan, conda, manual
    bool transitive = false;
};

struct VulnerabilityReport {
    std::string dependency;
    std::string cve_id;
    std::string severity;
    std::string fixed_version;
    std::string description;
};

class DependencyAuditor {
private:
    std::vector<Dependency> dependencies_;
    std::unordered_map<std::string, std::vector<VulnerabilityReport>> 
        known_vulnerabilities_;

    // Licenças incompatíveis com uso comercial
    std::vector<std::string> restrictive_licenses_ = {
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
        "SSPL-1.0"
    };

public:
    void add_dependency(const Dependency& dep) {
        dependencies_.push_back(dep);
    }

    void load_known_vulnerabilities(
        const std::string& vuln_db_path) {
        // Em produção: consultar NVD, GitHub Advisories, etc.
        // Aqui exemplificamos com um repositório local
    }

    // Verificar licenças
    std::vector<std::string> check_license_compliance() const {
        std::vector<std::string> issues;

        for (const auto& dep : dependencies_) {
            for (const auto& restrictive : restrictive_licenses_) {
                if (dep.license.find(restrictive) != std::string::npos) {
                    issues.push_back(
                        "WARNING: " + dep.name + " uses " + dep.license +
                        " — may require source code disclosure");
                }
            }
        }

        return issues;
    }

    // Verificar vulnerabilidades conhecidas
    std::vector<VulnerabilityReport> check_vulnerabilities() const {
        std::vector<VulnerabilityReport> found;

        for (const auto& dep : dependencies_) {
            auto it = known_vulnerabilities_.find(dep.name);
            if (it != known_vulnerabilities_.end()) {
                for (const auto& vuln : it->second) {
                    if (is_version_affected(dep.version, 
                                           vuln.fixed_version)) {
                        found.push_back(vuln);
                    }
                }
            }
        }

        return found;
    }

    // Verificar dependências não atualizadas
    std::vector<std::string> check_outdated() const {
        std::vector<std::string> outdated;

        // Em produção: comparar com repositórios upstream
        // Aqui exemplificamos a estrutura

        return outdated;
    }

    // Gerar relatório completo
    void generate_report(const std::string& output_path) const {
        std::ofstream file(output_path);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open report file");
        }

        file << "# Dependency Security Audit Report\n\n";
        file << "Total dependencies: " << dependencies_.size() << "\n\n";

        // Licenças
        auto license_issues = check_license_compliance();
        file << "## License Issues\n\n";
        if (license_issues.empty()) {
            file << "No license issues found.\n\n";
        } else {
            for (const auto& issue : license_issues) {
                file << "- " << issue << "\n";
            }
            file << "\n";
        }

        // Vulnerabilidades
        auto vulns = check_vulnerabilities();
        file << "## Vulnerabilities\n\n";
        if (vulns.empty()) {
            file << "No known vulnerabilities found.\n\n";
        } else {
            for (const auto& v : vulns) {
                file << "### " << v.cve_id << "\n";
                file << "- Dependency: " << v.dependency << "\n";
                file << "- Severity: " << v.severity << "\n";
                file << "- Fixed in: " << v.fixed_version << "\n";
                file << "- Description: " << v.description << "\n\n";
            }
        }

        // Resumo
        file << "## Summary\n\n";
        file << "- Total dependencies: " << dependencies_.size() << "\n";
        file << "- License issues: " << license_issues.size() << "\n";
        file << "- Vulnerabilities: " << vulns.size() << "\n";
    }

private:
    bool is_version_affected(const std::string& current,
                             const std::string& fixed) const {
        // Simplificado — em produção, usar semver comparison
        return current < fixed;
    }
};
```

### 10.3 Estratégias de Versionamento

```cpp
// Versionamento Seguro — Estratégias para dependências C++

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <regex>
#include <optional>
#include <algorithm>

struct VersionPin {
    std::string package;
    std::string exact_version;
    std::string hash;  // SHA256 do pacote
    bool required = true;
};

class DependencyPinning {
private:
    std::vector<VersionPin> pins_;
    std::string lockfile_path_;

public:
    explicit DependencyPinning(const std::string& lockfile)
        : lockfile_path_(lockfile) {}

    // Pin para versão exata (mais seguro)
    void pin_exact(const std::string& package,
                   const std::string& version,
                   const std::string& hash) {
        pins_.push_back(VersionPin{package, version, hash, true});
    }

    // Carregar pins de lockfile
    void load_lockfile() {
        std::ifstream file(lockfile_path_);
        if (!file.is_open()) {
            return;  // Lockfile não existe
        }

        std::string line;
        while (std::getline(file, line)) {
            auto pin = parse_lockfile_line(line);
            if (pin) {
                pins_.push_back(*pin);
            }
        }
    }

    // Salvar lockfile
    void save_lockfile() const {
        std::ofstream file(lockfile_path_);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot save lockfile");
        }

        for (const auto& pin : pins_) {
            file << pin.package << "=" << pin.exact_version 
                 << ":" << pin.hash << "\n";
        }
    }

    // Verificar integridade
    bool verify_integrity(const std::string& package,
                          const std::string& version,
                          const std::string& hash) const {
        for (const auto& pin : pins_) {
            if (pin.package == package && 
                pin.exact_version == version) {
                return pin.hash == hash;
            }
        }
        return false;  // Pacote não está no lockfile
    }

private:
    std::optional<VersionPin> parse_lockfile_line(
        const std::string& line) const {
        // Formato: package=version:hash
        static const std::regex pattern(
            R"(^([^=]+)=([^:]+):([a-fA-F0-9]+)$)");
        
        std::smatch match;
        if (std::regex_match(line, match, pattern)) {
            return VersionPin{
                match[1].str(),
                match[2].str(),
                match[3].str(),
                true
            };
        }
        return std::nullopt;
    }
};
```

### 10.4 Fluxo de Auditoria

```cpp
// Fluxo de Auditoria — Workflow completo de segurança de dependências

class DependencyAuditWorkflow {
public:
    struct AuditResult {
        bool passed;
        std::vector<std::string> critical_issues;
        std::vector<std::string> warnings;
        std::vector<std::string> info;
    };

    static AuditResult run_full_audit(
        const DependencyAuditor& auditor) {
        
        AuditResult result;
        result.passed = true;

        // 1. Verificar vulnerabilidades
        auto vulns = auditor.check_vulnerabilities();
        for (const auto& v : vulns) {
            if (v.severity == "critical" || v.severity == "high") {
                result.critical_issues.push_back(
                    v.cve_id + " in " + v.dependency);
                result.passed = false;
            } else {
                result.warnings.push_back(
                    v.cve_id + " in " + v.dependency);
            }
        }

        // 2. Verificar licenças
        auto license_issues = auditor.check_license_compliance();
        for (const auto& issue : license_issues) {
            result.warnings.push_back(issue);
        }

        // 3. Verificar dependências desatualizadas
        auto outdated = auditor.check_outdated();
        for (const auto& dep : outdated) {
            result.info.push_back("Outdated: " + dep);
        }

        return result;
    }

    static void print_result(const AuditResult& result) {
        std::cout << "\n=== Dependency Audit Result ===\n\n";
        
        if (result.passed) {
            std::cout << "STATUS: PASSED\n\n";
        } else {
            std::cout << "STATUS: FAILED\n\n";
        }

        if (!result.critical_issues.empty()) {
            std::cout << "CRITICAL ISSUES:\n";
            for (const auto& issue : result.critical_issues) {
                std::cout << "  [!] " << issue << "\n";
            }
            std::cout << "\n";
        }

        if (!result.warnings.empty()) {
            std::cout << "WARNINGS:\n";
            for (const auto& warning : result.warnings) {
                std::cout << "  [*] " << warning << "\n";
            }
            std::cout << "\n";
        }

        if (!result.info.empty()) {
            std::cout << "INFO:\n";
            for (const auto& i : result.info) {
                std::cout << "  [i] " << i << "\n";
            }
        }
    }
};
```

---

## 11. Exemplo Completo: Compliance Checklist Automático

```cpp
// Compliance Checker — Sistema completo de verificação de conformidade
// Verifica CERT C++, MISRA, SBOM, licenças e controles de segurança

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>
#include <functional>
#include <memory>
#include <chrono>
#include <regex>
#include <unordered_map>
#include <filesystem>
#include <numeric>
#include <iomanip>
#include <set>

// ============================================================================
// Resultados de verificação
// ============================================================================

enum class Severity {
    Info,
    Low,
    Medium,
    High,
    Critical
};

enum class ComplianceStatus {
    Pass,
    Fail,
    Warning,
    NotChecked
};

struct CheckResult {
    std::string rule_id;
    std::string rule_name;
    Severity severity;
    ComplianceStatus status;
    std::string file;
    int line;
    std::string message;
    std::string remediation;
};

struct ComplianceReport {
    std::string project_name;
    std::string timestamp;
    std::vector<CheckResult> results;
    
    int pass_count() const {
        return static_cast<int>(std::count_if(
            results.begin(), results.end(),
            [](const CheckResult& r) { 
                return r.status == ComplianceStatus::Pass; 
            }));
    }
    
    int fail_count() const {
        return static_cast<int>(std::count_if(
            results.begin(), results.end(),
            [](const CheckResult& r) { 
                return r.status == ComplianceStatus::Fail; 
            }));
    }
    
    int warning_count() const {
        return static_cast<int>(std::count_if(
            results.begin(), results.end(),
            [](const CheckResult& r) { 
                return r.status == ComplianceStatus::Warning; 
            }));
    }

    bool is_compliant() const {
        return std::none_of(results.begin(), results.end(),
            [](const CheckResult& r) { 
                return r.status == ComplianceStatus::Fail && 
                       (r.severity == Severity::Critical || 
                        r.severity == Severity::High); 
            });
    }
};

// ============================================================================
// Verificador CERT C++
// ============================================================================

class CERTCppChecker {
private:
    std::vector<std::pair<std::string, std::regex>> forbidden_patterns_;

public:
    CERTCppChecker() {
        // MEM51-CPP: Usar smart pointers em vez de new/delete
        forbidden_patterns_.emplace_back(
            "MEM51-CPP",
            std::regex(R"(\bnew\s+\w+[\[\(])"));

        // STR50-CPP: Não usar funções C inseguras
        forbidden_patterns_.emplace_back(
            "STR50-CPP",
            std::regex(R"(\b(sprintf|strcpy|strcat|gets|scanf)\s*\()"));

        // INT32-CPP: Verificar overflow
        forbidden_patterns_.emplace_back(
            "INT32-CPP",
            std::regex(R"(\b\w+\s*\+\s*\w+\s*=\s*\w+)"));

        // ERR50-CPP: Verificar retorno de funções
        forbidden_patterns_.emplace_back(
            "ERR50-CPP",
            std::regex(R"(\b(fopen|malloc|calloc|realloc)\s*\()"));

        // CON50-CPP: Não usar threads sem sincronização
        forbidden_patterns_.emplace_back(
            "CON50-CPP",
            std::regex(R"(\bstd::thread\b)"));
    }

    std::vector<CheckResult> check_file(const std::string& filepath) {
        std::vector<CheckResult> results;

        std::ifstream file(filepath);
        if (!file.is_open()) {
            results.push_back({
                "GEN", "File Access", Severity::Medium,
                ComplianceStatus::Fail, filepath, 0,
                "Cannot open file for review", "Check file path"
            });
            return results;
        }

        std::string line;
        int line_num = 0;

        while (std::getline(file, line)) {
            ++line_num;

            for (const auto& [rule_id, pattern] : forbidden_patterns_) {
                if (std::regex_search(line, pattern)) {
                    results.push_back({
                        rule_id, get_rule_name(rule_id),
                        Severity::High,
                        ComplianceStatus::Fail,
                        filepath, line_num,
                        "Violation of " + rule_id + " detected",
                        get_remediation(rule_id)
                    });
                }
            }

            // Verificar nullptr explícito
            if (line.find("NULL") != std::string::npos &&
                line.find("nullptr") == std::string::npos) {
                results.push_back({
                    "OOP50-CPP", "Use nullptr",
                    Severity::Medium,
                    ComplianceStatus::Fail,
                    filepath, line_num,
                    "Use nullptr instead of NULL",
                    "Replace NULL with nullptr"
                });
            }
        }

        // Adicionar resultado pass se nenhuma violação
        if (results.empty() || 
            std::none_of(results.begin(), results.end(),
                [](const CheckResult& r) { 
                    return r.status == ComplianceStatus::Fail; 
                })) {
            results.push_back({
                "CERT-ALL", "CERT C++ Compliance",
                Severity::Info,
                ComplianceStatus::Pass,
                filepath, 0,
                "No CERT C++ violations detected", ""
            });
        }

        return results;
    }

private:
    std::string get_rule_name(const std::string& rule_id) const {
        static const std::unordered_map<std::string, std::string> names = {
            {"MEM51-CPP", "Smart Pointer Usage"},
            {"STR50-CPP", "Safe String Handling"},
            {"INT32-CPP", "Integer Overflow Check"},
            {"ERR50-CPP", "Error Handling"},
            {"CON50-CPP", "Thread Safety"}
        };
        auto it = names.find(rule_id);
        return it != names.end() ? it->second : "Unknown Rule";
    }

    std::string get_remediation(const std::string& rule_id) const {
        static const std::unordered_map<std::string, std::string> remediations = {
            {"MEM51-CPP", "Use std::unique_ptr or std::shared_ptr"},
            {"STR50-CPP", "Use std::string and std::stoi/printf alternatives"},
            {"INT32-CPP", "Use SafeInteger::safe_add() with overflow checking"},
            {"ERR50-CPP", "Check return values and use RAII"},
            {"CON50-CPP", "Use std::mutex, std::shared_mutex, or std::atomic"}
        };
        auto it = remediations.find(rule_id);
        return it != remediations.end() ? it->second : "Review documentation";
    }
};

// ============================================================================
// Verificador MISRA
// ============================================================================

class MISRA_CPPChecker {
public:
    std::vector<CheckResult> check_file(const std::string& filepath) {
        std::vector<CheckResult> results;

        std::ifstream file(filepath);
        if (!file.is_open()) return results;

        std::string line;
        int line_num = 0;

        while (std::getline(file, line)) {
            ++line_num;

            // Regra 2.7: Não usar comentários em blocos de código
            if (line.find("/*") != std::string::npos) {
                results.push_back({
                    "MISRA-2.7", "No Block Comments",
                    Severity::Low,
                    ComplianceStatus::Warning,
                    filepath, line_num,
                    "Block comment detected (MISRA advisory)",
                    "Use // comments instead"
                });
            }

            // Regra 14.4: Condições booleanas
            if (std::regex_search(line, 
                std::regex(R"(\bif\s*\([^)]*==\s*(true|false))"))) {
                results.push_back({
                    "MISRA-14.4", "Boolean Condition",
                    Severity::Medium,
                    ComplianceStatus::Fail,
                    filepath, line_num,
                    "Direct boolean comparison in condition",
                    "Use if (condition) instead of if (condition == true)"
                });
            }

            // Regra 17.3: Não usar implícito int
            if (std::regex_search(line,
                std::regex(R"(^\s*(int|long|short|char)\s+\w+\s*[=(])"))) {
                // Verificar se há tipo explícito
                if (line.find("explicit") == std::string::npos &&
                    line.find("static") == std::string::npos) {
                    // Advertência apenas
                }
            }

            // Regra 18.4: Não usar aritmética de ponteiros
            if (line.find("++") != std::string::npos ||
                line.find("--") != std::string::npos) {
                if (line.find("*") != std::string::npos ||
                    line.find("ptr") != std::string::npos) {
                    results.push_back({
                        "MISRA-18.4", "No Pointer Arithmetic",
                        Severity::High,
                        ComplianceStatus::Warning,
                        filepath, line_num,
                        "Possible pointer arithmetic detected",
                        "Use array indexing instead"
                    });
                }
            }

            // Regra 22.10: Não usar recursão
            // (Verificação simplificada)
        }

        return results;
    }
};

// ============================================================================
// Verificador de SBOM
// ============================================================================

class SBOMChecker {
public:
    struct SBOMEntry {
        std::string name;
        std::string version;
        std::string license;
    };

    std::vector<CheckResult> check_sbom(
        const std::vector<SBOMEntry>& entries) {
        std::vector<CheckResult> results;

        for (const auto& entry : entries) {
            // Verificar se há versão especificada
            if (entry.version.empty()) {
                results.push_back({
                    "SBOM-001", "Version Specified",
                    Severity::Medium,
                    ComplianceStatus::Fail,
                    entry.name, 0,
                    "No version specified for " + entry.name,
                    "Pin exact version in dependency manifest"
                });
            }

            // Verificar licença
            if (entry.license.empty()) {
                results.push_back({
                    "SBOM-002", "License Documented",
                    Severity::Low,
                    ComplianceStatus::Warning,
                    entry.name, 0,
                    "No license documented for " + entry.name,
                    "Add license information to SBOM"
                });
            }

            // Verificar licenças restritivas
            if (entry.license.find("AGPL") != std::string::npos ||
                entry.license.find("SSPL") != std::string::npos) {
                results.push_back({
                    "SBOM-003", "Restrictive License",
                    Severity::High,
                    ComplianceStatus::Fail,
                    entry.name, 0,
                    "Restrictive license: " + entry.license,
                    "Evaluate license compatibility or find alternative"
                });
            }
        }

        if (results.empty()) {
            results.push_back({
                "SBOM-ALL", "SBOM Compliance",
                Severity::Info,
                ComplianceStatus::Pass,
                "SBOM", 0,
                "All SBOM checks passed", ""
            });
        }

        return results;
    }
};

// ============================================================================
// Verificador de Controles de Segurança
// ============================================================================

class SecurityControlsChecker {
public:
    std::vector<CheckResult> check_coding_practices(
        const std::string& filepath) {
        std::vector<CheckResult> results;

        std::ifstream file(filepath);
        if (!file.is_open()) return results;

        std::string content(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>());

        // Controle: Criptografia adequada
        if (content.find("MD5") != std::string::npos ||
            content.find("SHA1") != std::string::npos) {
            results.push_back({
                "SEC-001", "Weak Cryptography",
                Severity::High,
                ComplianceStatus::Fail,
                filepath, 0,
                "Weak cryptographic algorithm detected",
                "Use SHA-256 or stronger algorithms"
            });
        }

        // Controle: Logging seguro
        if (content.find("password") != std::string::npos &&
            content.find("log") != std::string::npos) {
            results.push_back({
                "SEC-002", "Sensitive Data in Logs",
                Severity::Critical,
                ComplianceStatus::Fail,
                filepath, 0,
                "Potential sensitive data in log output",
                "Sanitize sensitive data before logging"
            });
        }

        // Controle: Validação de entrada
        if (content.find("cin") != std::string::npos ||
            content.find("getline") != std::string::npos) {
            if (content.find("validate") == std::string::npos &&
                content.find("sanitize") == std::string::npos) {
                results.push_back({
                    "SEC-003", "Input Validation",
                    Severity::Medium,
                    ComplianceStatus::Warning,
                    filepath, 0,
                    "Input handling without explicit validation",
                    "Add input validation for all external data"
                });
            }
        }

        // Controle: Gerenciamento de memória
        if (content.find("delete ") != std::string::npos) {
            results.push_back({
                "SEC-004", "Manual Memory Management",
                Severity::Medium,
                ComplianceStatus::Fail,
                filepath, 0,
                "Manual memory deletion detected",
                "Use smart pointers (std::unique_ptr, std::shared_ptr)"
            });
        }

        return results;
    }
};

// ============================================================================
// Gerador de Relatório
// ============================================================================

class ComplianceReportGenerator {
public:
    static void generate(const ComplianceReport& report,
                         const std::string& output_path) {
        std::ofstream file(output_path);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open report file");
        }

        file << "# Compliance Report\n\n";
        file << "Project: " << report.project_name << "\n";
        file << "Generated: " << report.timestamp << "\n";
        file << "Overall Status: " 
             << (report.is_compliant() ? "COMPLIANT" : "NON-COMPLIANT") 
             << "\n\n";

        file << "## Summary\n\n";
        file << "| Status | Count |\n";
        file << "|--------|-------|\n";
        file << "| Pass | " << report.pass_count() << " |\n";
        file << "| Fail | " << report.fail_count() << " |\n";
        file << "| Warning | " << report.warning_count() << " |\n\n";

        // Agrupar por severidade
        auto crit = filter_by_severity(report.results, Severity::Critical);
        auto high = filter_by_severity(report.results, Severity::High);
        auto med = filter_by_severity(report.results, Severity::Medium);
        auto low = filter_by_severity(report.results, Severity::Low);

        if (!crit.empty()) {
            file << "## Critical Issues\n\n";
            print_section(file, crit);
        }

        if (!high.empty()) {
            file << "## High Issues\n\n";
            print_section(file, high);
        }

        if (!med.empty()) {
            file << "## Medium Issues\n\n";
            print_section(file, med);
        }

        if (!low.empty()) {
            file << "## Low Issues\n\n";
            print_section(file, low);
        }

        // Detalhes por arquivo
        file << "## Details by File\n\n";
        auto by_file = group_by_file(report.results);
        for (const auto& [filepath, results] : by_file) {
            file << "### " << filepath << "\n\n";
            for (const auto& r : results) {
                file << "- [" << status_to_string(r.status) << "] "
                     << r.rule_id << " (Line " << r.line << "): "
                     << r.message << "\n";
                if (!r.remediation.empty()) {
                    file << "  - Remediation: " << r.remediation << "\n";
                }
            }
            file << "\n";
        }
    }

private:
    static std::vector<CheckResult> filter_by_severity(
        const std::vector<CheckResult>& results,
        Severity severity) {
        std::vector<CheckResult> filtered;
        std::copy_if(results.begin(), results.end(),
            std::back_inserter(filtered),
            [severity](const CheckResult& r) { 
                return r.severity == severity; 
            });
        return filtered;
    }

    static std::unordered_map<std::string, std::vector<CheckResult>>
    group_by_file(const std::vector<CheckResult>& results) {
        std::unordered_map<std::string, std::vector<CheckResult>> grouped;
        for (const auto& r : results) {
            grouped[r.file].push_back(r);
        }
        return grouped;
    }

    static std::string status_to_string(ComplianceStatus status) {
        switch (status) {
            case ComplianceStatus::Pass: return "PASS";
            case ComplianceStatus::Fail: return "FAIL";
            case ComplianceStatus::Warning: return "WARN";
            case ComplianceStatus::NotChecked: return "N/C";
        }
        return "?";
    }

    static void print_section(std::ofstream& file,
                               const std::vector<CheckResult>& results) {
        for (const auto& r : results) {
            file << "- **" << r.rule_name << "** (" << r.rule_id << ")\n";
            file << "  - File: " << r.file << ":" << r.line << "\n";
            file << "  - Message: " << r.message << "\n";
            if (!r.remediation.empty()) {
                file << "  - Remediation: " << r.remediation << "\n";
            }
        }
        file << "\n";
    }
};

// ============================================================================
// Orquestrador Principal
// ============================================================================

class ComplianceChecker {
private:
    CERTCppChecker cert_checker_;
    MISRA_CPPChecker misra_checker_;
    SBOMChecker sbom_checker_;
    SecurityControlsChecker security_checker_;
    std::string project_name_;

public:
    explicit ComplianceChecker(const std::string& project_name)
        : project_name_(project_name) {}

    ComplianceReport run_full_check(
        const std::vector<std::string>& source_files,
        const std::vector<SBOMChecker::SBOMEntry>& sbom_entries) {
        
        ComplianceReport report;
        report.project_name = project_name_;
        
        // Timestamp
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        std::ostringstream oss;
        oss << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
        report.timestamp = oss.str();

        // 1. CERT C++ checks
        for (const auto& file : source_files) {
            auto results = cert_checker_.check_file(file);
            report.results.insert(report.results.end(),
                results.begin(), results.end());
        }

        // 2. MISRA checks
        for (const auto& file : source_files) {
            auto results = misra_checker_.check_file(file);
            report.results.insert(report.results.end(),
                results.begin(), results.end());
        }

        // 3. SBOM checks
        auto sbom_results = sbom_checker_.check_sbom(sbom_entries);
        report.results.insert(report.results.end(),
            sbom_results.begin(), sbom_results.end());

        // 4. Security controls checks
        for (const auto& file : source_files) {
            auto results = security_checker_.check_coding_practices(file);
            report.results.insert(report.results.end(),
                results.begin(), results.end());
        }

        return report;
    }

    void save_report(const ComplianceReport& report,
                     const std::string& output_path) {
        ComplianceReportGenerator::generate(report, output_path);
        
        std::cout << "\n=== Compliance Check Complete ===\n";
        std::cout << "Project: " << report.project_name << "\n";
        std::cout << "Status: " 
                  << (report.is_compliant() ? "COMPLIANT" : "NON-COMPLIANT")
                  << "\n";
        std::cout << "Pass: " << report.pass_count() 
                  << " | Fail: " << report.fail_count()
                  << " | Warning: " << report.warning_count() << "\n";
        std::cout << "Report saved to: " << output_path << "\n";
    }
};

// ============================================================================
// Exemplo de uso
// ============================================================================

int main() {
    ComplianceChecker checker("DevSecurityCpp");

    std::vector<std::string> source_files = {
        "src/main.cpp",
        "src/auth.cpp",
        "src/crypto.cpp",
        "src/database.cpp"
    };

    std::vector<SBOMChecker::SBOMEntry> sbom = {
        {"nlohmann-json", "3.11.2", "MIT"},
        {"OpenSSL", "3.1.4", "Apache-2.0"},
        {"fmt", "10.1.1", "MIT"},
        {"spdlog", "1.12.0", "MIT"},
        {"boost", "1.83.0", "BSL-1.0"},
        {"some-gpl-lib", "2.0.0", "GPL-3.0-only"}
    };

    auto report = checker.run_full_check(source_files, sbom);
    checker.save_report(report, "compliance_report.md");

    return report.is_compliant() ? 0 : 1;
}
```

---

## 12. Referências

### Padrões e Normas

1. **OWASP ASVS** — Application Security Verification Standard. https://owasp.org/www-project-application-security-verification-standard/
2. **OWASP SAMM** — Software Assurance Maturity Model. https://owasp.org/www-project-samm/
3. **SEI CERT C++** — Secure Coding Standard. https://wiki.sei.cmu.edu/confluence/display/cplusplus/
4. **MISRA C++ 2023** — Guidelines for the Use of the C++14 Language in Critical Systems. MISRA Consortium.
5. **ISO/IEC 27001** — Information Security Management Systems. International Organization for Standardization.
6. **SOC 2** — Service Organization Control 2. American Institute of Certified Public Accountants.

### Regulamentações

7. **GDPR** — General Data Protection Regulation (EU) 2016/679.
8. **LGPD** — Lei Geral de Proteção de Dados (Lei nº 13.709/2018).
9. **PCI DSS** — Payment Card Industry Data Security Standard v4.0.
10. **HIPAA** — Health Insurance Portability and Accountability Act.
11. **FDA Cybersecurity Guidance** — Premarket Cybersecurity Guidance for Medical Devices. FDA, 2023.
12. **ISO/SAE 21434** — Road Vehicles — Cybersecurity Engineering.

### CWE e Vulnerabilidades

13. **CWE** — Common Weakness Enumeration. MITRE. https://cwe.mitre.org/
14. **CWE Top 25** — Most Dangerous Software Weaknesses. MITRE, 2024.
15. **NVD** — National Vulnerability Database. NIST. https://nvd.nist.gov/

### SBOM e Licenciamentos

16. **SPDX** — Software Package Data Exchange. Linux Foundation. https://spdx.org/
17. **CycloneDX** — Software Bill of Materials Standard. OWASP. https://owasp.org/www-project-cyclonedx/
18. **SLSA** — Supply-chain Levels for Software Artifacts. Google. https://slsa.dev/

### Casos Documentados

19. **Equifax Breach** — Failure to patch Apache Struts vulnerability (CVE-2017-5638). Congressional Report, 2018.
20. **GDPR Fines** — Google €50M (CNIL, 2019), Amazon €746M (DPA Luxembourg, 2021).
21. **Facebook FTC Settlement** — $5B USD settlement for privacy violations. FTC, 2019.
22. **SolarWinds** — Supply chain compromise via Orion Platform. CISA Advisory, 2020.

### Ferramentas

23. **clang-tidy** — C++ linter with CERT, MISRA, and other checks. LLVM Project.
24. **cppcheck** — Static analysis for C/C++. https://cppcheck.sourceforge.io/
25. **Polyspace** — MISRA and CERT compliance verification. MathWorks.
26. **SonarQube** — Continuous code quality and security analysis. SonarSource.

---

**Fim do Capítulo 14**

> Compliance é o início, não o fim. O verdadeiro desafio é construir software que
> seja seguro POR DESIGN, não apenas conformista por acidente. Domine as normas,
> mas nunca pare de questionar se elas são suficientes para o seu contexto.
