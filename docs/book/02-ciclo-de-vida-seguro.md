---
layout: default
title: "02-ciclo-de-vida-seguro"
---

# Capítulo 2 — Ciclo de Vida Seguro de Software

---

## Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

1. Compreender e aplicar as fases do Secure Software Development Lifecycle (SSDL) em projetos C++ de produção, identificando onde as portas de segurança devem ser inseridas.
2. Elaborar requisitos de segurança using técnicas como STRIDE, abuse cases e user stories de segurança, traduzindo-os em especificações testáveis para sistemas C++.
3. Construir modelos de ameaças para sistemas complexos, mapeando fluxos de dados, limites de confiança e superfícies de ataque em aplicações de alto desempenho.
4. Integrar ferramentas de análise estática, fuzzing, sanitizers e revisão de código no pipeline de desenvolvimento, detectando vulnerabilidades antes do deploy.
5. Desenvolver e manter processos de resposta a incidentes, monitoramento contínuo e gestão de vulnerabilidades que sustentem a segurança operacional de software C++.

---

## 1. Visão Geral do Ciclo de Vida Seguro

### 1.1 SDLC Tradicional vs Secure SDLC

O ciclo de vida tradicional de desenvolvimento de software (SDLC) concentra-se na funcionalidade, no prazo e no custo. Segurança, quando presente, tende a aparecer apenas nas fases finais — testes ou deploy — quando o custo de correção é exponencialmente maior.

Um **Secure SDLC** (S-SDLC) integra segurança em **todas** as fases do ciclo, desde a concepção até a operação. A premissa fundamental é que vulnerabilidades descobertas na fase de requisitos custam ordens de magnitude menos para corrigir do que as encontradas em produção.

| Aspecto | SDLC Tradicional | Secure SDLC |
|---|---|---|
| Momento da segurança | Finais (teste) | Contínuo (todas as fases) |
| Custo de correção | Alto (pós-deploy) | Baixo (durante design) |
| Responsabilidade | Equipe de QA/Segurança | Toda a equipe |
| Ferramentas | Testes funcionais | Análise estática, fuzzing, threat modeling |
| Resultado | Software funcional | Software funcional E seguro |
| Conhecimento requerido | Desenvolvimento | Desenvolvimento + Segurança |

### 1.2 As Seis Fases do Secure SDLC

O Secure SDLC estrutura-se em seis fases principais, cada uma com portas de segurança específicas:

```
+=====================================================================+
|                   SECURE SOFTWARE DEVELOPMENT LIFECYCLE             |
+=====================================================================+
|                                                                     |
|  [1. REQUISITOS] --> [2. DESIGN] --> [3. IMPLEMENTAÇÃO]             |
|        |                  |                  |                       |
|        v                  v                  v                       |
|   +----------+     +-----------+     +---------------+              |
|   | Porta 1  |     |  Porta 2  |     |    Porta 3   |              |
|   | Req.Seg  |     | Threat    |     | Secure Code  |              |
|   | Checklist|     | Model OK  |     | Review Pass  |              |
|   +----------+     +-----------+     +---------------+              |
|        |                  |                  |                       |
|        +------------------+------------------+                       |
|                           |                                         |
|                           v                                         |
|  [4. TESTE] --> [5. DEPLOY] --> [6. MONITORAMENTO]                  |
|        |              |                |                             |
|        v              v                v                             |
|   +-----------+  +-----------+  +---------------+                   |
|   |  Porta 4  |  |  Porta 5  |  |    Porta 6   |                   |
|   | Security  |  | Config    |  |  Vulnerability|                   |
|   | Test Pass |  | Audit OK  |  |  Scan Clean   |                   |
|   +-----------+  +-----------+  +---------------+                   |
|        |              |                |                             |
|        +------+-------+-------+--------+                             |
|               |                                                       |
|               v                                                       |
|       +--------------+                                                |
|       |   Feed-back  |  (monitoramento alimenta requisitos)          |
|       +--------------+                                                |
+=====================================================================+
```

### 1.3 Portas de Segurança em Cada Fase

Uma **porta de segurança** (security gate) é um ponto de verificação obrigatório que impede a progressão de um artefato de desenvolvimento para a próxima fase, a menos que critérios de segurança específicos sejam atendidos.

**Fase 1 — Requisitos:**
- Requisitos de segurança documentados e revisados
- Classificação de dados concluída
- Requisitos regulatórios identificados (LGPD, PCI-DSS, etc.)

**Fase 2 — Design:**
- Modelo de ameaças revisado e aprovado
- Limites de confiança definidos
- Criptografia e autenticação especificadas

**Fase 3 — Implementação:**
- Análise estática sem alertas críticos
- Revisão de código de segurança concluída
- Dependências verificadas contra CVEs conhecidos

**Fase 4 — Teste:**
- Testes de segurança executados e aprovados
- Fuzzing sem crashes
- Cobertura de testes de segurança >= 80%

**Fase 5 — Deploy:**
- Configurações auditadas
- Segredos externalizados
- Hardening do infrastructure verificado

**Fase 6 — Monitoramento:**
- Logging de segurança ativo
- Varreduras de vulnerabilidade periódicas
- Plano de resposta a incidentes atualizado

### 1.4 Papéis e Responsabilidades

| Papel | Responsabilidades de Segurança |
|---|---|
| Product Owner | Incluir requisitos de segurança nas user stories |
| Arquiteto | Conduzir threat modeling, definir limites de confiança |
| Desenvolvedor | Codificação segura, revisão de código, correção de vulnerabilidades |
| QA de Segurança | Testes de segurança, fuzzing, penetração |
| DevOps/Infra | Hardening, gestão de segredos, monitoramento |
| Líder de Segurança | Definir padrões, conduzir auditorias, resposta a incidentes |

### 1.5 Estudo de Caso CVE: Portas de Segurança Ausentes

O ataque à **Equifax (2017)** é um exemplo clássico de como a ausência de portas de segurança em todas as fases leva a violações massivas. A vulnerabilidade CVE-2017-5638 no Apache Struts estava disponível para correção meses antes do ataque. A Equifax falhou em:

- **Requisitos**: Não mantinha inventário atualizado de dependências
- **Implementação**: Não aplicava patches de segurança regularmente
- **Monitoramento**: Não detectou o tráfego anômalo por meses
- **Deploy**: Não tinha processos de atualização de emergência

O resultado: 147 milhões de registros pessoais expostos, multa de US$ 700 milhões e perda irreparável de confiança. Uma única porta de segurança — gestão de dependências — poderia ter impedido a violação.

---

## 2. Fase de Requisitos de Segurança

### 2.1 Técnicas de Coleta de Requisitos de Segurança

A coleta de requisitos de segurança deve iniciar no momento da concepção do projeto. As principais técnicas incluem:

**Entrevistas com stakeholders:**
- Perguntar explicitamente sobre dados sensíveis tratados
- Identificar requisitos regulatórios aplicáveis
- Documentar expectativas de privacidade

**Análise de ameaças preliminar:**
- Identificar atores de ameaça prováveis
- Mapear ativos de valor
- Classificar dados por sensibilidade

**Benchmarking regulatório:**
- Mapear requisitos de normas aplicáveis
- Documentar requisitos legais (LGPD, GDPR)
- Identificar requisitos de conformidade do setor

### 2.2 User Stories de Segurança e Abuse Cases

User stories de segurança seguem o mesmo formato das funcionais, mas expresam necessidades de proteção:

```
[STORY] Como administrador do sistema, quero que todas as operações 
de escrita no banco de dados sejam autenticadas e autorizadas, para 
que apenas usuários legitimem possam modificar dados.

[Critérios de Aceite]
- Autenticação via JWT com validade de 15 minutos
- Refresh token com rotação automática
- Logs de todas as operações de escrita
- Rejeição de tokens expirados ou manipulados
```

**Abuse cases** invertem a perspectiva — descrevem como um atacante poderia abusar do sistema:

```
[ABUSE CASE] Como atacante, tentaria injetar código malicioso através 
de campos de entrada de texto para executar comandos arbitrários no 
servidor.

[Contra-medida] Validação e sanitização de todas as entradas com 
whitelist de caracteres permitidos. Rejeição de padrões suspeitos.
```

### 2.3 Integração com Avaliação de Risco

Cada requisito de segurança deve ser vinculado a uma avaliação de risco:

```cpp
// security_requirements.h
#pragma once
#include <string>
#include <vector>
#include <cstdint>

enum class RiskLevel : uint8_t {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
};

enum class DataClassification : uint8_t {
    PUBLIC,
    INTERNAL,
    CONFIDENTIAL,
    RESTRICTED
};

struct SecurityRequirement {
    std::string id;
    std::string description;
    RiskLevel riskLevel;
    DataClassification dataClass;
    bool regulatoryMandatory;
    std::string regulation;      // e.g., "LGPD", "PCI-DSS 3.4"
    std::string mitigation;
    std::string testCriteria;
};

class SecurityRequirementsRegistry {
public:
    void addRequirement(const SecurityRequirement& req) {
        requirements_.push_back(req);
    }

    std::vector<SecurityRequirement> getByRiskLevel(RiskLevel minLevel) const {
        std::vector<SecurityRequirement> result;
        for (const auto& req : requirements_) {
            if (req.riskLevel >= minLevel) {
                result.push_back(req);
            }
        }
        return result;
    }

    std::vector<SecurityRequirement> getMandatory() const {
        std::vector<SecurityRequirement> result;
        for (const auto& req : requirements_) {
            if (req.regulatoryMandatory) {
                result.push_back(req);
            }
        }
        return result;
    }

    [[nodiscard]] bool allMandatoryAddressed() const {
        for (const auto& req : requirements_) {
            if (req.regulatoryMandatory && req.mitigation.empty()) {
                return false;
            }
        }
        return true;
    }

private:
    std::vector<SecurityRequirement> requirements_;
};
```

### 2.4 Documento Completo de Requisitos de Segurança: Sistema de Pagamentos em C++

```cpp
// payment_security_requirements.cpp
#include "security_requirements.h"
#include <iostream>

SecurityRequirementsRegistry buildPaymentSystemRequirements() {
    SecurityRequirementsRegistry registry;

    // REQ-001: Autenticação de transações
    registry.addRequirement({
        .id = "REQ-001",
        .description = "Todas as transações financeiras devem ser autenticadas com MFA",
        .riskLevel = RiskLevel::CRITICAL,
        .dataClass = DataClassification::RESTRICTED,
        .regulatoryMandatory = true,
        .regulation = "PCI-DSS 8.3",
        .mitigation = "Implementar autenticação de dois fatores com TOTP/HOTP",
        .testCriteria = "Transações sem MFA devem ser rejeitadas com erro 403"
    });

    // REQ-002: Criptografia em repouso
    registry.addRequirement({
        .id = "REQ-002",
        .description = "Dados de cartão de crédito devem ser criptografados em repouso",
        .riskLevel = RiskLevel::CRITICAL,
        .dataClass = DataClassification::RESTRICTED,
        .regulatoryMandatory = true,
        .regulation = "PCI-DSS 3.4",
        .mitigation = "AES-256-GCM com keys em HSM",
        .testCriteria = "Verificar que dados em disco são ilegíveis sem chave"
    });

    // REQ-003: Proteção contra injeção SQL
    registry.addRequirement({
        .id = "REQ-003",
        .description = "Todas as consultas SQL devem usar prepared statements",
        .riskLevel = RiskLevel::HIGH,
        .dataClass = DataClassification::CONFIDENTIAL,
        .regulatoryMandatory = true,
        .regulation = "OWASP Top 10 A03:2021",
        .mitigation = "Prepared statements com parâmetros vinculados",
        .testCriteria = "Análise estática não deve encontrar concatenação de SQL"
    });

    // REQ-004: Validação de entrada
    registry.addRequirement({
        .id = "REQ-004",
        .description = "Todos os dados de entrada devem ser validados contra schema",
        .riskLevel = RiskLevel::HIGH,
        .dataClass = DataClassification::INTERNAL,
        .regulatoryMandatory = false,
        .regulation = "",
        .mitigation = "Whelist validation com max length e charset restrictions",
        .testCriteria = "Fuzzing com 100k inputs não deve causar crashes"
    });

    // REQ-005: Rate limiting
    registry.addRequirement({
        .id = "REQ-005",
        .description = "Endpoints de pagamento devem ter rate limiting",
        .riskLevel = RiskLevel::MEDIUM,
        .dataClass = DataClassification::INTERNAL,
        .regulatoryMandatory = false,
        .regulation = "",
        .mitigation = "Token bucket algorithm, 10 req/s por IP",
        .testCriteria = "Requisições acima do limite retornam 429"
    });

    // REQ-006: Auditoria de transações
    registry.addRequirement({
        .id = "REQ-006",
        .description = "Todas as transações devem ter log imutável de auditoria",
        .riskLevel = RiskLevel::HIGH,
        .dataClass = DataClassification::CONFIDENTIAL,
        .regulatoryMandatory = true,
        .regulation = "PCI-DSS 10.2",
        .mitigation = "Append-only log com hash de integridade",
        .testCriteria = "Logs devem conter: timestamp, user_id, action, IP, resultado"
    });

    // REQ-007: Proteção contra replay
    registry.addRequirement({
        .id = "REQ-007",
        .description = "Requisições de pagamento devem ser idempotentes com nonce",
        .riskLevel = RiskLevel::HIGH,
        .dataClass = DataClassification::CONFIDENTIAL,
        .regulatoryMandatory = false,
        .regulation = "",
        .mitigation = "Nonce único por transação com TTL de 5 minutos",
        .testCriteria = "Reenvio da mesma requisição deve ser rejeitado"
    });

    // REQ-008: Segredos em memória
    registry.addRequirement({
        .id = "REQ-008",
        .description = "Dados sensíveis em memória devem ser zerados após uso",
        .riskLevel = RiskLevel::HIGH,
        .dataClass = DataClassification::RESTRICTED,
        .regulatoryMandatory = false,
        .regulation = "",
        .mitigation = "Secure zeroization via explicit_bzero ou volatile write",
        .testCriteria = "Valgrind deve confirmar zeroização após uso"
    });

    return registry;
}

int main() {
    auto registry = buildPaymentSystemRequirements();

    auto critical = registry.getByRiskLevel(RiskLevel::CRITICAL);
    auto mandatory = registry.getMandatory();

    std::cout << "Total de requisitos criticos: " << critical.size() << "\n";
    std::cout << "Total de obrigatorios: " << mandatory.size() << "\n";
    std::cout << "Todos obrigatorios enderecados: "
              << (registry.allMandatoryAddressed() ? "SIM" : "NAO") << "\n";

    return 0;
}
```

### 2.5 Requisitos Funcionais vs Não-Funcionais de Segurança

**Requisitos funcionais de segurança** definem *o que* o sistema deve fazer:
- O sistema deve autenticar usuários antes de acessar dados
- O sistema deve criptografar senhas com bcrypt
- O sistema deve validar formato de e-mail

**Requisitos não-funcionais de segurança** definem *o quão bem* o sistema deve fazer:
- Autenticação deve completar em < 200ms
- Criptografia deve usar chaves de no mínimo 256 bits
- O sistema deve suportar 10.000 autenticações simultâneas

### 2.6 Elicitação de Requisitos Baseada em STRIDE

STRIDE é uma técnica sistemática para identificar ameaças, cada uma mapeando para um tipo de requisito:

| STRIDE Category | Ameaça | Tipo de Requisito | Exemplo |
|---|---|---|---|
| **S**poofing | Falsificação de identidade | Autenticação forte | MFA obrigatório |
| **T**ampering | Alteração de dados | Integridade | Assinaturas digitais |
| **R**epudiation | Negação de ação | Auditoria | Logs imutáveis |
| **I**nformation Disclosure | Vazamento de dados | Confidencialidade | Criptografia em repouso |
| **D**enial of Service | Indisponibilidade | Disponibilidade | Rate limiting, redundância |
| **E**levation of Privilege | Escalação de privilégio | Autorização | Least privilege, RBAC |

---

## 3. Fase de Design e Threat Modeling

### 3.1 Threat Modeling como Atividade de Design

Threat modeling não é uma atividade isolada — é parte integrante do design do sistema. Deve ocorrer antes do código ser escrito, quando mudanças arquiteturais são baratas.

O processo segue quatro passos:

1. **Decompor o sistema**: Mapear componentes, fluxos de dados e limites de confiança
2. **Identificar ameaças**: Usar metodologia estruturada (STRIDE, PASTA, Attack Trees)
3. **Mitigar ameaças**: Projetar contramedidas para cada ameaça identificada
4. **Validar**: Verificar que as contramedidas são eficazes e completas

### 3.2 Diagramas de Fluxo de Dados (DFD) para Análise de Segurança

Um DFD para análise de segurança identifica quatro tipos de elementos:

- **Entidades externas**: Fontes e destinos de dados fora do sistema
- **Processos**: Componentes que processam dados
- **Armazenamentos de dados**: Bancos de dados, arquivos, caches
- **Fluxos de dados**: Movimentação de dados entre elementos
- **Limites de confiança**: Bordas onde o nível de confiança muda

```
    +-------------------+
    |  Cliente (Ext.)   |
    +--------+----------+
             |
             | HTTPS (TLS 1.3)
             |
    +--------v----------+       +-------------------+
    | [Load Balancer]   |------>| (WAF / Firewall)  |
    |  Trust Boundary 1 |       +-------------------+
    +--------+----------+
             |
             | HTTP interno
             |
    +--------v----------+       +-------------------+
    | [API Gateway]     |------>| {Rate Limiter}    |
    |  Trust Boundary 2 |       +-------------------+
    +--------+----------+
             |
             | JWT validation
             |
    +--------v----------+       +-------------------+
    | [Payment Service] |------>| (Payment DB)      |
    |  Trust Boundary 3 |       |  Criptografado    |
    +--------+----------+       +-------------------+
             |
             | Queue (encrypted)
             |
    +--------v----------+       +-------------------+
    | [Notification Svc]|------>| (Email/SMS API)   |
    +-------------------+       +-------------------+
```

### 3.3 Árvores de Ataque e Superfícies de Ataque

Uma árvore de ataque descreve sistematicamente como um atacante pode alcançar um objetivo:

```
                        [Objetivo: Roubar dados de pagamento]
                                      |
                    +-----------------+-----------------+
                    |                                   |
            [Comprometer API]                   [Comprometer DB]
                    |                                   |
          +--------+--------+                 +--------+--------+
          |        |        |                 |        |        |
     [Injeção] [Bypass] [RCE]          [SQLi]  [Backup] [Disk]
      [SQL]    [Auth]   [via            [via    [Theft]  [Direct]
               [via     [deserial-      [API
               [JWT     [ization]       params]
               [forgery]
```

### 3.4 Identificação de Limites de Confiança

Limites de confiança são as bordas mais críticas em um sistema. Dados que cruzam um limite de confiança devem ser validados e protegidos:

```cpp
// trust_boundary.h
#pragma once
#include <string>
#include <functional>
#include <stdexcept>
#include <optional>

enum class TrustZone : uint8_t {
    EXTERNAL,      // Internet pública, clientes
    DMZ,           // Demilitarized zone, load balancers
    APPLICATION,   // Serviços internos
    DATA,          // Bancos de dados, armazenamento
    MANAGEMENT     // Painéis administrativos
};

template <typename T>
class TrustBoundaryValidator {
public:
    using ValidationFunc = std::function<bool(const T&)>;

    TrustBoundaryValidator(TrustZone source, TrustZone destination)
        : source_(source), destination_(destination) {}

    void addValidation(ValidationFunc func, const std::string& desc) {
        validations_.push_back({std::move(func), desc});
    }

    bool validate(const T& data, std::string& errorOut) const {
        if (source_ == destination_) {
            return true; // Same trust zone, no validation needed
        }

        for (const auto& [func, desc] : validations_) {
            if (!func(data)) {
                errorOut = "Trust boundary validation failed: " + desc +
                          " (zone " + zoneName(source_) + " -> " + zoneName(destination_) + ")";
                return false;
            }
        }
        return true;
    }

private:
    TrustZone source_;
    TrustZone destination_;
    struct ValidationEntry {
        ValidationFunc func;
        std::string description;
    };
    std::vector<ValidationEntry> validations_;

    static const char* zoneName(TrustZone zone) {
        switch (zone) {
            case TrustZone::EXTERNAL:    return "EXTERNAL";
            case TrustZone::DMZ:         return "DMZ";
            case TrustZone::APPLICATION: return "APPLICATION";
            case TrustZone::DATA:        return "DATA";
            case TrustZone::MANAGEMENT:  return "MANAGEMENT";
        }
        return "UNKNOWN";
    }
};

// Usage example
class PaymentInput {
public:
    std::string cardNumber;
    std::string cvv;
    double amount;
    std::string currency;
};

void configurePaymentValidation(
    TrustBoundaryValidator<PaymentInput>& validator) {

    // External -> Application boundary: strict validation required
    validator.addValidation(
        [](const PaymentInput& input) {
            // Validate card number format (Luhn algorithm)
            return input.cardNumber.size() >= 13 &&
                   input.cardNumber.size() <= 19;
        },
        "Card number must be 13-19 digits");

    validator.addValidation(
        [](const PaymentInput& input) {
            return input.cvv.size() >= 3 && input.cvv.size() <= 4;
        },
        "CVV must be 3-4 digits");

    validator.addValidation(
        [](const PaymentInput& input) {
            return input.amount > 0.0 && input.amount <= 999999.99;
        },
        "Amount must be positive and within limits");

    validator.addValidation(
        [](const PaymentInput& input) {
            return input.currency == "BRL" ||
                   input.currency == "USD" ||
                   input.currency == "EUR";
        },
        "Currency must be BRL, USD, or EUR");
}
```

### 3.5 Modelo de Ameaças Completo: Sistema de Processamento de Arquivos em C++

```cpp
// file_processor_threat_model.h
#pragma once
#include <string>
#include <vector>
#include <cstdint>

struct ThreatModelEntry {
    std::string threatId;
    std::string description;
    std::string strideCategory;
    std::string affectedComponent;
    std::string impact;       // Low, Medium, High, Critical
    std::string likelihood;   // Low, Medium, High
    std::string mitigation;
    std::string residualRisk;
    std::string status;       // Open, Mitigated, Accepted
};

class FileProcessorThreatModel {
public:
    FileProcessorThreatModel() {
        populateThreats();
    }

    std::vector<ThreatModelEntry> getOpenThreats() const {
        std::vector<ThreatModelEntry> open;
        for (const auto& t : threats_) {
            if (t.status == "Open") {
                open.push_back(t);
            }
        }
        return open;
    }

    std::vector<ThreatModelEntry> getThreatsBySeverity(const std::string& severity) const {
        std::vector<ThreatModelEntry> filtered;
        for (const auto& t : threats_) {
            if (t.impact == severity) {
                filtered.push_back(t);
            }
        }
        return filtered;
    }

    bool hasUnmitigatedCriticals() const {
        for (const auto& t : threats_) {
            if (t.impact == "Critical" && t.status == "Open") {
                return true;
            }
        }
        return false;
    }

    const std::vector<ThreatModelEntry>& getAllThreats() const {
        return threats_;
    }

private:
    std::vector<ThreatModelEntry> threats_;

    void populateThreats() {
        threats_ = {
            {
                "TM-FP-001",
                "Path traversal via crafted filename",
                "Tampering",
                "FileReader component",
                "Critical",
                "High",
                "Whitelist validation of file paths, chroot jail",
                "Low",
                "Mitigated"
            },
            {
                "TM-FP-002",
                "Zip bomb causing denial of service",
                "Denial of Service",
                "ArchiveExtractor component",
                "High",
                "Medium",
                "Size limits on decompressed output, ratio limits",
                "Low",
                "Mitigated"
            },
            {
                "TM-FP-003",
                "Malicious polyglot file executing code",
                "Elevation of Privilege",
                "FileProcessor core",
                "Critical",
                "Medium",
                "Magic byte validation, sandboxed processing",
                "Medium",
                "Open"
            },
            {
                "TM-FP-004",
                "Symlink following to sensitive files",
                "Information Disclosure",
                "FileReader component",
                "High",
                "High",
                "O_NOFOLLOW flag, symlink detection before processing",
                "Low",
                "Mitigated"
            },
            {
                "TM-FP-005",
                "Race condition in temp file creation",
                "Elevation of Privilege",
                "TempFileManager",
                "High",
                "Low",
                "Use mkstemp, O_EXCL, atomic rename",
                "Low",
                "Mitigated"
            },
            {
                "TM-FP-006",
                "Log injection via crafted filenames",
                "Tampering",
                "AuditLogger",
                "Medium",
                "Medium",
                "Sanitize log output, structured logging format",
                "Low",
                "Open"
            },
            {
                "TM-FP-007",
                "XML bomb (billion laughs attack)",
                "Denial of Service",
                "XMLParser component",
                "High",
                "High",
                "Entity expansion limits, disable DTD processing",
                "Low",
                "Mitigated"
            },
            {
                "TM-FP-008",
                "File metadata leak in error messages",
                "Information Disclosure",
                "ErrorHandler",
                "Medium",
                "Medium",
                "Generic error messages, log full details separately",
                "Low",
                "Open"
            }
        };
    }
};
```

### 3.6 Abordagem Microsoft Threat Modeling Tool

O Microsoft Threat Modeling Tool segue a abordagem "Design First, Attack Later":

1. **Desenhe o sistema** usando stencils de componentes
2. **Gere automaticamente** as ameaças STRIDE por componente
3. **Revise e classifique** cada ameaça por severidade
4. **Aplique mitigações** e documente decisões de aceitação de risco

Para sistemas C++, o tool gera automaticamente verificações como:
- Entradas que cruzam limites de confiança e precisam de validação
- Dados sensíveis que passam por componentes sem criptografia
- Pontos onde autenticação/autorização são necessárias

---

## 4. Fase de Implementação Segura

### 4.1 Padrões de Codificação Segura (CERT C++, MISRA)

O **CERT C++ Coding Standard** e o **MISRA C++** fornecem regras específicas para prevenir vulnerabilidades comuns. Exemplos críticos:

```cpp
// secure_coding_examples.cpp
#include <cstring>
#include <cstdlib>
#include <memory>
#include <array>
#include <string_view>
#include <charconv>
#include <system_error>
#include <fstream>
#include <filesystem>

// BAD: Stack buffer overflow
void unsafe_copy(const char* source) {
    char buffer[64];
    strcpy(buffer, source); // CERT C++ STR50-CPP: no bounds checking
}

// GOOD: Safe bounded copy
void safe_copy(const char* source, size_t sourceLen) {
    constexpr size_t BUFFER_SIZE = 64;
    char buffer[BUFFER_SIZE];

    if (sourceLen >= BUFFER_SIZE) {
        sourceLen = BUFFER_SIZE - 1;
    }

    std::memcpy(buffer, source, sourceLen);
    buffer[sourceLen] = '\0';
}

// BAD: Use after free
void unsafe_use_after_free() {
    int* ptr = new int(42);
    delete ptr;
    int value = *ptr; // UB: use after free
    (void)value;
}

// GOOD: Smart pointer usage
void safe_memory_management() {
    auto ptr = std::make_unique<int>(42);
    int value = *ptr;
    (void)value;
    // Automatic cleanup when ptr goes out of scope
}

// BAD: Integer overflow leading to buffer overflow
void unsafe_allocation(size_t count) {
    int* arr = new int[count * sizeof(int)]; // Overflow possible
    (void)arr;
    delete[] arr;
}

// GOOD: Overflow-checked allocation
bool safe_allocation(size_t count) {
    constexpr size_t MAX_COUNT = 1024 * 1024;

    if (count > MAX_COUNT) {
        return false;
    }

    // Use safe multiplication check
    if (count != 0 && MAX_COUNT / count < sizeof(int)) {
        return false;
    }

    auto arr = std::make_unique<int[]>(count);
    return true;
}

// BAD: Format string vulnerability
void unsafe_format(const char* userInput) {
    printf(userUserInput); // CERT C++ STR51-CPP
}

// GOOD: Format string safety
void safe_format(const char* userInput) {
    printf("%s", userInput);
}

// CERT C++ STR54-CPP: Use of random values
#include <random>
#include <chrono>

class SecureRandomGenerator {
public:
    SecureRandomGenerator() {
        std::random_device rd;
        generator_.seed(rd());
    }

    uint32_t generateNonce() {
        std::uniform_int_distribution<uint32_t> dist;
        return dist(generator_);
    }

    std::string generateToken(size_t length) {
        static constexpr char charset[] =
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789";

        std::string token;
        token.reserve(length);

        std::uniform_int_distribution<size_t> dist(0, sizeof(charset) - 2);

        for (size_t i = 0; i < length; ++i) {
            token += charset[dist(generator_)];
        }

        return token;
    }

private:
    std::mt19937 generator_;
};

// CERT C++ ERR55-CPP: Handle all errors
std::optional<std::string> readFileSafe(const std::string& path) {
    std::error_code ec;
    auto fileSize = std::filesystem::file_size(path, ec);

    if (ec) {
        return std::nullopt;
    }

    constexpr uintmax_t MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB limit
    if (fileSize > MAX_FILE_SIZE) {
        return std::nullopt;
    }

    std::ifstream file(path, std::ios::binary);
    if (!file.is_open()) {
        return std::nullopt;
    }

    std::string content(fileSize, '\0');
    if (!file.read(content.data(), static_cast<std::streamsize>(fileSize))) {
        return std::nullopt;
    }

    return content;
}
```

### 4.2 Checklist de Revisão de Código para Segurança

| ID | Verificação | Severidade | Ferramenta |
|---|---|---|---|
| CR-01 | Validação de entrada em todas as fronteiras | Alta | Manual + ASan |
| CR-02 | Uso correto de smart pointers | Alta | clang-tidy |
| CR-03 | Ausência de format strings com input | Crítica | cppcheck |
| CR-04 | Uso de bounded APIs (strncpy vs strcpy) | Alta | clang-tidy |
| CR-05 | Tratamento correto de erros | Média | Manual |
| CR-06 | Não-vazamento de recursos RAII | Alta | Valgrind |
| CR-07 | Criptografia com algoritmos aprovados | Crítica | Manual |
| CR-08 | Zeroização de dados sensíveis | Alta | Valgrind |
| CR-09 | Ausência de race conditions | Alta | TSan |
| CR-10 | Validação de todas as divisões por zero | Média | UBSan |

### 4.3 Programação em Par para Código Crítico de Segurança

Para componentes de segurança — autenticação, criptografia, validação — a programação em par é especialmente valiosa:

- Um desenvolvedor foca na funcionalidade
- O outro foca exclusivamente em segurança
- Pontos de atenção: validação de entrada, tratamento de erros, gerenciamento de memória

### 4.4 Integração de Análise Estática no Desenvolvimento

```cmake
# CMakeLists.txt with security-focused build pipeline
cmake_minimum_required(VERSION 3.20)
project(SecureCppProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ============================================================
# SECURITY FLAGS
# ============================================================

# Compiler security flags
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Werror=format-security
    -Werror=implicit-function-declaration
    -Wformat=2
    -Wformat-overflow=2
    -Wformat-truncation=2
    -Wnull-dereference
    -Wimplicit-fallthrough
    -Wswitch-enum
    -Wconversion
    -Wsign-conversion
    -Wdouble-promotion
    -Wstrict-overflow=5
    -fstack-protector-strong
    -fstack-clash-protection
    -fcf-protection=full
    -D_FORTIFY_SOURCE=2
    -fPIE
)

add_link_options(
    -Wl,-z,relro,-z,now
    -Wl,-z,noexecstack
    -Wl,-z,separate-code
)

# ============================================================
# SECURITY SANITIZERS (Debug builds)
# ============================================================

option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
option(ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)
option(ENABLE_TSAN "Enable ThreadSanitizer" OFF)
option(ENABLE_MSAN "Enable MemorySanitizer" OFF)

if(ENABLE_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()

if(ENABLE_UBSAN)
    add_compile_options(-fsanitize=undefined -fno-omit-frame-pointer)
    add_link_options(-fsanitize=undefined)
endif()

if(ENABLE_TSAN)
    add_compile_options(-fsanitize=thread -fno-omit-frame-pointer)
    add_link_options(-fsanitize=thread)
endif()

# ============================================================
# MAIN LIBRARY
# ============================================================

add_library(secure_core STATIC
    src/crypto_utils.cpp
    src/input_validator.cpp
    src/audit_logger.cpp
    src/secret_manager.cpp
    src/secure_allocator.cpp
)

target_include_directories(secure_core PUBLIC include/)

# ============================================================
# STATIC ANALYSIS TARGETS
# ============================================================

# clang-tidy
find_program(CLANG_TIDY clang-tidy)
if(CLANG_TIDY)
    set(CMAKE_CXX_CLANG_TIDY
        ${CLANG_TIDY}
        --checks=*
        --warnings-as-errors=*
        --header-filter=include/.*
    )
endif()

# cppcheck
find_program(CPPCHECK cppcheck)
if(CPPCHECK)
    add_custom_target(cppcheck
        COMMAND ${CPPCHECK}
            --enable=all
            --std=c++17
            --error-exitcode=1
            --inline-suppr
            --suppress=missingIncludeSystem
            -I include/
            src/
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    )
endif()

# ============================================================
# TESTING
# ============================================================

enable_testing()
find_package(GTest QUIET)

if(GTest)
    add_executable(security_tests
        tests/test_input_validator.cpp
        tests/test_crypto_utils.cpp
        tests/test_audit_logger.cpp
        tests/test_secret_manager.cpp
    )

    target_link_libraries(security_tests
        GTest::gtest
        GTest::gtest_main
        secure_core
    )

    # Run sanitizers on test builds
    if(ENABLE_ASAN OR ENABLE_UBSAN)
        target_compile_options(security_tests PRIVATE
            -fno-omit-frame-pointer
        )
    endif()

    add_test(NAME SecurityTests COMMAND security_tests)
endif()

# ============================================================
# FUZZ TESTING
# ============================================================

find_program(CLANG_FUZZ clang++)
if(CLANG_FUZZ)
    add_executable(fuzz_input_validator
        fuzz/fuzz_input_validator.cpp
    )
    target_link_libraries(fuzz_input_validator secure_core)

    set_target_properties(fuzz_input_validator PROPERTIES
        LINK_FLAGS "-fsanitize=fuzzer,address,undefined"
        COMPILE_FLAGS "-fsanitize=fuzzer,address,undefined -fno-omit-frame-pointer"
    )
endif()

# ============================================================
# CODE COVERAGE
# ============================================================

option(ENABLE_COVERAGE "Enable code coverage" OFF)
if(ENABLE_COVERAGE)
    add_compile_options(--coverage -fprofile-arcs -ftest-coverage)
    add_link_options(--coverage)
endif()
```

### 4.5 Hooks de Pre-commit para Verificações de Segurança

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Security checks before allowing commits

set -e

echo "=== Running Security Pre-Commit Checks ==="

# Check for secrets in staged files
echo "[1/5] Checking for secrets..."
if git diff --cached --name-only | xargs grep -lE \
    '(password|secret|api_key|token)\s*=\s*["\x27][^"\x27]+' 2>/dev/null; then
    echo "ERROR: Potential secrets found in staged files!"
    echo "Review the files above and remove any hardcoded secrets."
    exit 1
fi

# Check for dangerous functions
echo "[2/5] Checking for dangerous C/C++ functions..."
DANGEROUS_FUNCTIONS=(
    "gets("
    "strcpy("
    "strcat("
    "sprintf("
    "vsprintf("
    "scanf("
    "gets_s("
    "realpath("
)

for func in "${DANGEROUS_FUNCTIONS[@]}"; do
    if git diff --cached --diff-filter=ACM -- '*.cpp' '*.c' '*.h' |
       grep -q "$func"; then
        echo "WARNING: Dangerous function found: $func"
        echo "Consider using bounded alternatives."
        exit 1
    fi
done

# Run clang-tidy if available
echo "[3/5] Running clang-tidy..."
if command -v clang-tidy &> /dev/null; then
    STAGED_CPP=$(git diff --cached --name-only -- '*.cpp' '*.h')
    for file in $STAGED_CPP; do
        if [ -f "$file" ]; then
            clang-tidy "$file" -- -std=c++17 -Iinclude/ 2>/dev/null || true
        fi
    done
fi

# Run cppcheck if available
echo "[4/5] Running cppcheck..."
if command -v cppcheck &> /dev/null; then
    cppcheck --enable=all --error-exitcode=1 \
        --suppress=missingIncludeSystem \
        $(git diff --cached --name-only -- '*.cpp' '*.h') 2>/dev/null || true
fi

# Check for TODO/FIXME security items
echo "[5/5] Checking for security TODOs..."
if git diff --cached | grep -i "TODO.*security\|FIXME.*security\|HACK.*security"; then
    echo "WARNING: Security-related TODO/FIXME found in diff."
    echo "Please review and address before committing."
    exit 1
fi

echo "=== All Security Checks Passed ==="
```

### 4.6 Estudo de Caso CVE: Heartbleed (CVE-2014-0160)

O **Heartbleed** (CVE-2014-0160) foi uma vulnerabilidade no OpenSSL que permitia a leitura de memória do servidor, expondo chaves privadas, senhas e dados sensíveis. A vulnerabilidade existia por dois anos antes de ser descoberta.

**Causa raiz:** O bug estava na implementação da extensão Heartbeat do TLS. A função de validação de comprimento não verificava se o comprimento declarado pelo cliente correspondia ao payload real:

```cpp
// Simplified illustration of the Heartbleed vulnerability
// This is NOT production code - for educational purposes only

// VULNERABLE CODE (what OpenSSL had):
void handle_heartbeat_vulnerable(const uint8_t* payload, size_t payload_len) {
    uint8_t* buffer;
    // Read the claimed payload length from user input
    uint16_t heartbeat_length = *reinterpret_cast<const uint16_t*>(payload);

    // BUG: No validation that heartbeat_length <= actual payload_len
    // An attacker could claim 65535 bytes but only send 1 byte
    buffer = new uint8_t[1 + 2 + heartbeat_length];

    // This reads beyond payload, into server memory!
    std::memcpy(buffer, payload, 1 + heartbeat_length);

    // Sends server memory contents back to attacker
    send_response(buffer, 1 + 2 + heartbeat_length);
    delete[] buffer;
}

// SECURE CODE (what it should have been):
void handle_heartbeat_secure(const uint8_t* payload, size_t payload_len) {
    if (payload_len < 3) {  // Minimum: type(1) + length(2)
        return;  // Reject incomplete heartbeat
    }

    uint16_t heartbeat_length = *reinterpret_cast<const uint16_t*>(payload + 1);

    // CRITICAL: Validate declared length against actual payload
    if (heartbeat_length > payload_len - 3) {
        return;  // Reject if claimed length exceeds actual data
    }

    uint8_t* buffer = new uint8_t[1 + 2 + heartbeat_length];
    std::memcpy(buffer, payload, 1 + 2 + heartbeat_length);

    send_response(buffer, 1 + 2 + heartbeat_length);
    delete[] buffer;
}
```

**Como as fases teriam prevenido:**

- **Requisitos**: A especificação RFC 6520 defines que o heartbeat deve validar o comprimento. Requisitos de segurança claros teriam exigido essa validação.
- **Design**: O threat modeling identificaria que dados de entrada do usuário controlam alocação de memória — um padrão de alto risco.
- **Implementação**: Code review focado em segurança teria captado a validação ausente. Análise estática com Valgrind teria detectado o buffer over-read.
- **Teste**: Fuzzing do endpoint Heartbeat com entradas variadas teria revelado crash/leak imediatamente.

---

## 5. Fase de Teste de Segurança

### 5.1 Pirâmide de Testes de Segurança

```
                  /\
                 /  \        Testes de Penetração
                /    \       (Poucos, profundos)
               /------\
              /        \     Fuzzing & Manual Testing
             /          \    (Médio volume)
            /------------\
           /              \   Testes de Integração de Segurança
          /                \  (Muitos, automatizados)
         /------------------\
        /                    \  Testes Unitários de Segurança
       /                      \ (Vastos, executados em cada build)
      /------------------------\
```

### 5.2 Testes Unitários para Funções de Segurança

```cpp
// test_security_functions.cpp
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <string>
#include <vector>
#include <cstring>
#include <memory>
#include <array>

// ============================================================
// Input Validator Tests
// ============================================================

class InputValidator {
public:
    enum class ValidationError {
        NONE,
        EMPTY_INPUT,
        TOO_LONG,
        INVALID_CHARACTERS,
        SQL_INJECTION_ATTEMPT,
        PATH_TRAVERSAL_ATTEMPT,
        XSS_ATTEMPT
    };

    ValidationError validateUsername(const std::string& input) const {
        if (input.empty()) return ValidationError::EMPTY_INPUT;
        if (input.length() > 64) return ValidationError::TOO_LONG;

        for (char c : input) {
            if (!std::isalnum(c) && c != '_' && c != '-') {
                return ValidationError::INVALID_CHARACTERS;
            }
        }
        return ValidationError::NONE;
    }

    ValidationError validateSQL(const std::string& input) const {
        static const std::vector<std::string> sqlPatterns = {
            "'", "\"", ";", "--", "/*", "*/",
            "UNION", "SELECT", "INSERT", "UPDATE", "DELETE",
            "DROP", "ALTER", "CREATE", "EXEC", "EXECUTE"
        };

        std::string upper = input;
        std::transform(upper.begin(), upper.end(), upper.begin(), ::toupper);

        for (const auto& pattern : sqlPatterns) {
            if (upper.find(pattern) != std::string::npos) {
                return ValidationError::SQL_INJECTION_ATTEMPT;
            }
        }
        return ValidationError::NONE;
    }

    ValidationError validatePath(const std::string& input) const {
        if (input.find("..") != std::string::npos) {
            return ValidationError::PATH_TRAVERSAL_ATTEMPT;
        }
        if (input.find('\0') != std::string::npos) {
            return ValidationError::INVALID_CHARACTERS;
        }
        if (input.length() > 260) {
            return ValidationError::TOO_LONG;
        }
        return ValidationError::NONE;
    }

    ValidationError validateHTML(const std::string& input) const {
        if (input.find("<script") != std::string::npos) return ValidationError::XSS_ATTEMPT;
        if (input.find("javascript:") != std::string::npos) return ValidationError::XSS_ATTEMPT;
        if (input.find("onerror=") != std::string::npos) return ValidationError::XSS_ATTEMPT;
        if (input.find("onload=") != std::string::npos) return ValidationError::XSS_ATTEMPT;
        return ValidationError::NONE;
    }
};

class InputValidatorTest : public ::testing::Test {
protected:
    InputValidator validator;
};

TEST_F(InputValidatorTest, Username_EmptyInput_ReturnsEmptyError) {
    EXPECT_EQ(validator.validateUsername(""), InputValidator::ValidationError::EMPTY_INPUT);
}

TEST_F(InputValidatorTest, Username_ValidChars_ReturnsNone) {
    EXPECT_EQ(validator.validateUsername("user_123"), InputValidator::ValidationError::NONE);
}

TEST_F(InputValidatorTest, Username_TooLong_ReturnsTooLong) {
    std::string longUsername(100, 'a');
    EXPECT_EQ(validator.validateUsername(longUsername), InputValidator::ValidationError::TOO_LONG);
}

TEST_F(InputValidatorTest, Username_InvalidChars_ReturnsInvalid) {
    EXPECT_EQ(validator.validateUsername("user@name!"), InputValidator::ValidationError::INVALID_CHARACTERS);
    EXPECT_EQ(validator.validateUsername("user name"), InputValidator::ValidationError::INVALID_CHARACTERS);
    EXPECT_EQ(validator.validateUsername("admin;DROP TABLE"), InputValidator::ValidationError::INVALID_CHARACTERS);
}

TEST_F(InputValidatorTest, SQL_InjectionDetection) {
    EXPECT_EQ(validator.validateSQL("1; DROP TABLE users--"),
              InputValidator::ValidationError::SQL_INJECTION_ATTEMPT);
    EXPECT_EQ(validator.validateSQL("1' OR '1'='1"),
              InputValidator::ValidationError::SQL_INJECTION_ATTEMPT);
    EXPECT_EQ(validator.validateSQL("UNION SELECT * FROM passwords"),
              InputValidator::ValidationError::SQL_INJECTION_ATTEMPT);
    EXPECT_EQ(validator.validateSQL("normal text"),
              InputValidator::ValidationError::NONE);
}

TEST_F(InputValidatorTest, Path_TraversalDetection) {
    EXPECT_EQ(validator.validatePath("../../etc/passwd"),
              InputValidator::ValidationError::PATH_TRAVERSAL_ATTEMPT);
    EXPECT_EQ(validator.validatePath("../../../windows/system32"),
              InputValidator::ValidationError::PATH_TRAVERSAL_ATTEMPT);
    EXPECT_EQ(validator.validatePath("safe/file.txt"),
              InputValidator::ValidationError::NONE);
}

TEST_F(InputValidatorTest, HTML_XSSDetection) {
    EXPECT_EQ(validator.validateHTML("<script>alert('xss')</script>"),
              InputValidator::ValidationError::XSS_ATTEMPT);
    EXPECT_EQ(validator.validateHTML("<img onerror=alert(1)>"),
              InputValidator::ValidationError::XSS_ATTEMPT);
    EXPECT_EQ(validator.validateHTML("javascript:void(0)"),
              InputValidator::ValidationError::XSS_ATTEMPT);
    EXPECT_EQ(validator.validateHTML("Hello World"),
              InputValidator::ValidationError::NONE);
}

// ============================================================
// Cryptographic Utility Tests
// ============================================================

class CryptoUtils {
public:
    static bool constantTimeCompare(const std::vector<uint8_t>& a,
                                     const std::vector<uint8_t>& b) {
        if (a.size() != b.size()) return false;

        volatile uint8_t result = 0;
        for (size_t i = 0; i < a.size(); ++i) {
            result |= a[i] ^ b[i];
        }
        return result == 0;
    }

    static std::vector<uint8_t> deriveKey(const std::string& password,
                                            const std::vector<uint8_t>& salt,
                                            int iterations = 100000) {
        // Simplified PBKDF2-like derivation for demonstration
        std::vector<uint8_t> key(32, 0);
        const auto* passData = reinterpret_cast<const uint8_t*>(password.data());

        for (size_t i = 0; i < 32; ++i) {
            uint8_t current = passData[i % password.size()];
            for (int j = 0; j < iterations; ++j) {
                current = static_cast<uint8_t>(
                    (current * 31 + salt[i % salt.size()] + j) & 0xFF
                );
            }
            key[i] = current;
        }
        return key;
    }

    static std::string hashPassword(const std::string& password) {
        // Simplified for demonstration - real code would use Argon2
        auto salt = std::vector<uint8_t>{0x41, 0x42, 0x43, 0x44};
        auto key = deriveKey(password, salt);

        std::string result = "$argon2id$v=19$m=65536,t=3,p=4$";
        for (uint8_t byte : key) {
            char hex[3];
            std::snprintf(hex, sizeof(hex), "%02x", byte);
            result += hex;
        }
        return result;
    }
};

class CryptoUtilsTest : public ::testing::Test {};

TEST_F(CryptoUtilsTest, ConstantTimeCompare_EqualVectors_ReturnsTrue) {
    std::vector<uint8_t> a = {0x01, 0x02, 0x03};
    std::vector<uint8_t> b = {0x01, 0x02, 0x03};
    EXPECT_TRUE(CryptoUtils::constantTimeCompare(a, b));
}

TEST_F(CryptoUtilsTest, ConstantTimeCompare_DifferentVectors_ReturnsFalse) {
    std::vector<uint8_t> a = {0x01, 0x02, 0x03};
    std::vector<uint8_t> b = {0x01, 0x02, 0x04};
    EXPECT_FALSE(CryptoUtils::constantTimeCompare(a, b));
}

TEST_F(CryptoUtilsTest, ConstantTimeCompare_DifferentLengths_ReturnsFalse) {
    std::vector<uint8_t> a = {0x01, 0x02};
    std::vector<uint8_t> b = {0x01, 0x02, 0x03};
    EXPECT_FALSE(CryptoUtils::constantTimeCompare(a, b));
}

TEST_F(CryptoUtilsTest, ConstantTimeCompare_EmptyVectors_ReturnsTrue) {
    std::vector<uint8_t> a;
    std::vector<uint8_t> b;
    EXPECT_TRUE(CryptoUtils::constantTimeCompare(a, b));
}

TEST_F(CryptoUtilsTest, DeriveKey_SamePasswordSameSalt_SameKey) {
    std::vector<uint8_t> salt = {0x01, 0x02, 0x03, 0x04};
    auto key1 = CryptoUtils::deriveKey("password", salt);
    auto key2 = CryptoUtils::deriveKey("password", salt);
    EXPECT_EQ(key1, key2);
}

TEST_F(CryptoUtilsTest, DeriveKey_DifferentSalt_DifferentKey) {
    std::vector<uint8_t> salt1 = {0x01, 0x02, 0x03, 0x04};
    std::vector<uint8_t> salt2 = {0x05, 0x06, 0x07, 0x08};
    auto key1 = CryptoUtils::deriveKey("password", salt1);
    auto key2 = CryptoUtils::deriveKey("password", salt2);
    EXPECT_NE(key1, key2);
}

TEST_F(CryptoUtilsTest, HashPassword_ReturnsFormattedHash) {
    auto hash = CryptoUtils::hashPassword("test123");
    EXPECT_TRUE(hash.starts_with("$argon2id$"));
    EXPECT_GT(hash.size(), 20u);
}

// ============================================================
// Secure Memory Zeroization Tests
// ============================================================

class SecureMemory {
public:
    static void secureZero(void* ptr, size_t len) {
        volatile unsigned char* p = static_cast<volatile unsigned char*>(ptr);
        while (len--) {
            *p++ = 0;
        }
    }

    static bool isZeroed(const void* ptr, size_t len) {
        const unsigned char* p = static_cast<const unsigned char*>(ptr);
        for (size_t i = 0; i < len; ++i) {
            if (p[i] != 0) return false;
        }
        return true;
    }
};

class SecureMemoryTest : public ::testing::Test {};

TEST_F(SecureMemoryTest, SecureZero_ZerosBuffer) {
    std::array<uint8_t, 64> buffer;
    std::fill(buffer.begin(), buffer.end(), 0xFF);

    SecureMemory::secureZero(buffer.data(), buffer.size());

    EXPECT_TRUE(SecureMemory::isZeroed(buffer.data(), buffer.size()));
}

TEST_F(SecureMemoryTest, SecureZero_PartialZero) {
    std::array<uint8_t, 64> buffer;
    std::fill(buffer.begin(), buffer.end(), 0xFF);

    SecureMemory::secureZero(buffer.data(), 32);

    // First half should be zeroed
    EXPECT_TRUE(SecureMemory::isZeroed(buffer.data(), 32));
    // Second half should still be 0xFF
    EXPECT_FALSE(SecureMemory::isZeroed(buffer.data() + 32, 32));
}

TEST_F(SecureMemoryTest, SecureZero_ZeroLength_NoOp) {
    std::array<uint8_t, 64> buffer;
    std::fill(buffer.begin(), buffer.end(), 0xAA);

    SecureMemory::secureZero(buffer.data(), 0);

    // Nothing should have changed
    EXPECT_FALSE(SecureMemory::isZeroed(buffer.data(), buffer.size()));
}
```

### 5.3 Testes de Integração para Mecanismos de Segurança

```cpp
// test_security_integration.cpp
#include <gtest/gtest.h>
#include <string>
#include <memory>
#include <thread>
#include <vector>
#include <mutex>
#include <chrono>
#include <atomic>

// Simulated authentication system for integration testing
class AuthenticationService {
public:
    struct AuthResult {
        bool success;
        std::string token;
        std::string error;
    };

    AuthResult authenticate(const std::string& username, const std::string& password) {
        std::lock_guard<std::mutex> lock(mutex_);
        attempts_[username]++;

        if (attempts_[username] > MAX_ATTEMPTS) {
            return {false, "", "Account locked: too many failed attempts"};
        }

        if (username == "admin" && password == "correct_password") {
            attempts_[username] = 0;
            return {true, generateToken(), ""};
        }

        return {false, "", "Invalid credentials"};
    }

    bool validateToken(const std::string& token) const {
        std::lock_guard<std::mutex> lock(mutex_);
        return validTokens_.count(token) > 0;
    }

    size_t getAttemptCount(const std::string& username) const {
        std::lock_guard<std::mutex> lock(mutex_);
        auto it = attempts_.find(username);
        return it != attempts_.end() ? it->second : 0;
    }

    void resetAccount(const std::string& username) {
        std::lock_guard<std::mutex> lock(mutex_);
        attempts_[username] = 0;
    }

private:
    static constexpr size_t MAX_ATTEMPTS = 5;

    std::string generateToken() {
        std::string token;
        for (int i = 0; i < 32; ++i) {
            token += "abcdef0123456789"[static_cast<size_t>(rand()) % 16];
        }
        validTokens_.insert(token);
        return token;
    }

    mutable std::mutex mutex_;
    std::unordered_map<std::string, size_t> attempts_;
    std::unordered_set<std::string> validTokens_;
};

class AuthIntegrationTest : public ::testing::Test {
protected:
    AuthenticationService auth;
};

TEST_F(AuthIntegrationTest, SuccessfulAuthentication) {
    auto result = auth.authenticate("admin", "correct_password");
    EXPECT_TRUE(result.success);
    EXPECT_FALSE(result.token.empty());
    EXPECT_TRUE(result.error.empty());
}

TEST_F(AuthIntegrationTest, FailedAuthentication) {
    auto result = auth.authenticate("admin", "wrong_password");
    EXPECT_FALSE(result.success);
    EXPECT_TRUE(result.token.empty());
    EXPECT_FALSE(result.error.empty());
}

TEST_F(AuthIntegrationTest, AccountLockout) {
    for (size_t i = 0; i < 6; ++i) {
        auth.authenticate("admin", "wrong_password");
    }

    auto result = auth.authenticate("admin", "correct_password");
    EXPECT_FALSE(result.success);
    EXPECT_THAT(result.error, ::testing::HasSubstr("locked"));
}

TEST_F(AuthIntegrationTest, TokenValidation) {
    auto result = auth.authenticate("admin", "correct_password");
    EXPECT_TRUE(result.success);

    EXPECT_TRUE(auth.validateToken(result.token));
}

TEST_F(AuthIntegrationTest, InvalidTokenRejected) {
    EXPECT_FALSE(auth.validateToken("nonexistent_token"));
}

TEST_F(AuthIntegrationTest, ConcurrentAuthentication) {
    constexpr int NUM_THREADS = 10;
    std::vector<std::thread> threads;
    std::atomic<size_t> successCount{0};

    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back([this, &successCount]() {
            auto result = auth.authenticate("admin", "correct_password");
            if (result.success) {
                successCount++;
            }
        });
    }

    for (auto& t : threads) {
        t.join();
    }

    // At least some should succeed
    EXPECT_GT(successCount.load(), 0u);
}
```

### 5.4 Fuzzing como Estratégia de Teste

Fuzzing é uma técnica poderosa para descobrir vulnerabilidades que testes convencionais não captam. O libFuzzer, integrado ao compilador Clang, é uma escolha excelente para C++:

```cpp
// fuzz/fuzz_input_validator.cpp
#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <algorithm>
#include <cctype>

// Simplified validator for fuzzing demonstration
bool validatePaymentInput(const uint8_t* data, size_t size) {
    if (size < 10) return false;

    // Parse amount (first 8 bytes as double)
    double amount = *reinterpret_cast<const double*>(data);
    if (amount < 0.0 || amount > 1000000.0) return false;

    // Parse currency code (next 3 bytes)
    if (size < 11) return false;
    char currency[4] = {
        static_cast<char>(data[8]),
        static_cast<char>(data[9]),
        static_cast<char>(data[10]),
        '\0'
    };

    // Validate currency code
    std::string curr(currency);
    std::transform(curr.begin(), curr.end(), curr.begin(), ::toupper);

    if (curr != "BRL" && curr != "USD" && curr != "EUR") return false;

    // Parse card number (remaining bytes)
    for (size_t i = 11; i < size; ++i) {
        if (!std::isdigit(data[i])) return false;
    }

    return true;
}

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
    // Fuzz the payment validator
    validatePaymentInput(data, size);

    return 0;
}
```

Para executar o fuzzing:

```bash
# Compile with fuzzer
clang++ -std=c++17 -fsanitize=fuzzer,address,undefined \
    -g -O1 fuzz/fuzz_input_validator.cpp \
    -o fuzz_input_validator

# Run fuzzing
./fuzz_input_validator -max_total_time=300 -max_len=1024

# Run with specific corpus
./fuzz_input_validator corpus/ -max_total_time=600
```

### 5.5 Estudo de Caso CVE: Shellshock

O **Shellshock** (CVE-2014-6271) foi uma vulnerabilidade no bash que permitia execução remota de comandos através de variáveis de ambiente. Foi descoberto em 2014, mas existia desde 1989.

**Causa raiz:** O bash processava definições de funções em variáveis de ambiente de forma insegura, executando código após o fim da definição da função.

**Como teria sido prevenido:**

- **Teste**: Shellshock poderia ter sido descoberto com fuzzing de shells, testando variáveis de ambiente com conteúdo malicioso. Testes de integração que verificam o comportamento esperado do bash em contextos CGI teriam exposto a falha.
- **Monitoramento**: Intrusão baseada em comportamento teria detectado o padrão de execução de comandos remotos via HTTP headers.

---

## 6. Fase de Deploy Seguro

### 6.1 Checklists de Deploy Seguro

| Item | Verificação | Status |
|---|---|---|
| 1 | Binário compilado com -fstack-protector-strong | [ ] |
| 2 | PIE habilitado (-fPIE -pie) | [ ] |
| 3 | RELRO completo (-Wl,-z,relro,-z,now) | [ ] |
| 4 | Sem strings de debug em produção | [ ] |
| 5 | Versões de dependências atualizadas | [ ] |
| 6 | Configurações de TLS 1.3 habilitadas | [ ] |
| 7 | Segredos externalizados (Vault/KMS) | [ ] |
| 8 | Rate limiting configurado | [ ] |
| 9 | Logging de segurança habilitado | [ ] |
| 10 | Health checks e alertas configurados | [ ] |
| 11 | Backup testado e verificado | [ ] |
| 12 | Rollback procedure documentado | [ ] |

### 6.2 Hardening de Infraestrutura

```cpp
// secure_config.h
#pragma once
#include <string>
#include <map>
#include <stdexcept>

struct ServerConfig {
    // TLS Configuration
    std::string tlsMinVersion = "1.3";
    std::vector<std::string> tlsCipherSuites = {
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "TLS_AES_128_GCM_SHA256"
    };
    bool requireClientCert = false;

    // Rate Limiting
    uint32_t maxRequestsPerSecond = 100;
    uint32_t maxConcurrentConnections = 1000;
    uint32_t connectionTimeoutSeconds = 30;

    // Security Headers
    bool enableHSTS = true;
    uint32_t hstsMaxAge = 31536000;  // 1 year
    bool enableCSP = true;
    std::string cspPolicy = "default-src 'self'; script-src 'self'";

    // Logging
    bool enableSecurityLogging = true;
    std::string logLevel = "INFO";
    bool logSensitiveData = false;
};

class ConfigValidator {
public:
    static std::vector<std::string> validate(const ServerConfig& config) {
        std::vector<std::string> errors;

        if (config.tlsMinVersion < "1.2") {
            errors.push_back("TLS minimum version must be >= 1.2");
        }

        if (config.maxRequestsPerSecond > 10000) {
            errors.push_back("Rate limit too high for production");
        }

        if (config.enableHSTS && config.hstsMaxAge < 31536000) {
            errors.push_back("HSTS max-age should be at least 1 year");
        }

        if (config.logSensitiveData) {
            errors.push_back("Sensitive data logging must be disabled in production");
        }

        if (config.tlsCipherSuites.empty()) {
            errors.push_back("No TLS cipher suites configured");
        }

        return errors;
    }
};
```

### 6.3 Gestão de Segredos no Deploy

```cpp
// secret_manager.h
#pragma once
#include <string>
#include <memory>
#include <map>
#include <mutex>
#include <optional>
#include <functional>
#include <chrono>

class SecretManager {
public:
    struct Secret {
        std::string key;
        std::string value;
        std::chrono::system_clock::time_point expiresAt;
        int version;
    };

    using SecretLoader = std::function<std::optional<Secret>(const std::string&)>;

    explicit SecretManager(SecretLoader loader)
        : loader_(std::move(loader)) {}

    std::optional<std::string> getSecret(const std::string& key) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = cache_.find(key);
        if (it != cache_.end()) {
            if (std::chrono::system_clock::now() < it->second.expiresAt) {
                return it->second.value;
            }
            cache_.erase(it);
        }

        auto secret = loader_(key);
        if (secret) {
            cache_[key] = *secret;
            return secret->value;
        }
        return std::nullopt;
    }

    void invalidate(const std::string& key) {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.erase(key);
    }

    void invalidateAll() {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.clear();
    }

    // Secure cleanup
    ~SecretManager() {
        invalidateAll();
    }

private:
    SecretLoader loader_;
    std::mutex mutex_;
    std::map<std::string, Secret> cache_;
};
```

### 6.4 Deploy Blue-Green e Canary

**Blue-Green Deployment** mantém duas cópias idênticas do sistema em produção. O tráfego é alternado entre elas, permitindo rollback instantâneo:

```
                  +-----------+
                  |   Router  |
                  +-----+-----+
                        |
          +-------------+-------------+
          |                           |
    +-----v-----+             +-----v-----+
    |   BLUE     |             |   GREEN   |
    | (current)  |             | (new ver) |
    +-----+------+             +-----+-----+
          |                           |
    +-----v------+             +-----v-----+
    |   DB       |             |   DB       |
    | (primary)  |             | (replica)  |
    +------------+             +------------+
```

**Canary Deployment** libera a nova versão para um subconjunto pequeno de usuários primeiro:

```
                  +-----------+
                  |   Router  |
                  +-----+-----+
                        |
          +-------------+-------------+
          |                           |
    (95% tráfego)              (5% tráfego)
          |                           |
    +-----v-----+             +-----v-----+
    |   v1.0    |             |   v2.0    |
    | (stable)  |             | (canary)  |
    +-----------+             +-----------+
```

### 6.5 Script de Deploy Seguro para Aplicação C++

```bash
#!/bin/bash
# deploy_secure.sh - Secure deployment script for C++ application

set -euo pipefail

APP_NAME="secure_cpp_app"
VERSION="${1:?Version required}"
DEPLOY_DIR="/opt/${APP_NAME}"
BACKUP_DIR="/opt/${APP_NAME}_backup"
LOG_FILE="/var/log/${APP_NAME}/deploy.log"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG_FILE"
}

# Pre-deployment security checks
run_security_checks() {
    log "Running pre-deployment security checks..."

    # Check binary integrity
    if ! sha256sum -c "${APP_NAME}-${VERSION}.sha256"; then
        log "ERROR: Binary integrity check failed!"
        exit 1
    fi

    # Check for known CVEs in dependencies
    if command -v grype &> /dev/null; then
        if ! grype dir:${DEPLOY_DIR} --fail-on high; then
            log "ERROR: High/Critical vulnerabilities found in dependencies!"
            exit 1
        fi
    fi

    # Verify binary security features
    local binary="${DEPLOY_DIR}/bin/${APP_NAME}"

    # Check for stack canary
    if ! readelf -s "$binary" | grep -q __stack_chk_fail; then
        log "WARNING: Binary lacks stack canary protection"
    fi

    # Check for PIE
    if ! file "$binary" | grep -q "shared object"; then
        log "WARNING: Binary is not PIE"
    fi

    log "Security checks passed"
}

# Deploy with blue-green strategy
deploy_blue_green() {
    log "Starting blue-green deployment of version ${VERSION}"

    # Determine current active slot
    local active_slot
    active_slot=$(cat "${DEPLOY_DIR}/active_slot" 2>/dev/null || echo "blue")

    local new_slot
    if [ "$active_slot" = "blue" ]; then
        new_slot="green"
    else
        new_slot="blue"
    fi

    log "Active slot: ${active_slot}, deploying to: ${new_slot}"

    # Stop new slot
    systemctl stop "${APP_NAME}-${new_slot}" 2>/dev/null || true

    # Deploy to new slot
    cp -a "${DEPLOY_DIR}/releases/${VERSION}/." "${DEPLOY_DIR}/slots/${new_slot}/"

    # Start new slot
    systemctl start "${APP_NAME}-${new_slot}"

    # Health check
    local retries=30
    local healthy=false
    for i in $(seq 1 $retries); do
        if curl -sf "http://localhost:808${new_slot:0:1}/health" > /dev/null 2>&1; then
            healthy=true
            break
        fi
        sleep 2
    done

    if [ "$healthy" = false ]; then
        log "ERROR: New slot failed health check, rolling back"
        systemctl stop "${APP_NAME}-${new_slot}"
        exit 1
    fi

    # Switch traffic
    echo "$new_slot" > "${DEPLOY_DIR}/active_slot"

    # Update load balancer config
    update_load_balancer "$new_slot"

    log "Deployment complete. Active slot: ${new_slot}"
    log "Previous version can be restored by switching active slot back to ${active_slot}"
}

update_load_balancer() {
    local slot="$1"
    local port
    if [ "$slot" = "blue" ]; then
        port=8080
    else
        port=8081
    fi

    # Update upstream configuration
    cat > /etc/nginx/conf.d/upstream.conf << EOF
upstream ${APP_NAME} {
    server 127.0.0.1:${port};
}
EOF

    nginx -s reload
}

# Main
log "=== Deployment started for ${APP_NAME} v${VERSION} ==="
run_security_checks
deploy_blue_green
log "=== Deployment completed successfully ==="
```

### 6.6 Estudo de Caso CVE: Equifax (CVE-2017-5638)

O breach da **Equifax (2017)** expôs dados de 147 milhões de pessoas. A vulnerabilidade era no Apache Struts (CVE-2017-5638), que tinha patch disponível desde março de 2017 — o ataque ocorreu em maio.

**Falhas de deploy:**

- **Ausência de inventário de dependências**: A Equifax não sabia que usava a versão vulnerável do Struts
- **Sem processo de patch de emergência**: Meses se passaram sem aplicação do patch
- **Monitoramento inadequado**: O tráfego anômalo não foi detectado por meses
- **Segredos hardcoded**: Credenciais de banco de dados foram encontradas em texto plano

**Como o deploy seguro teria prevenido:**

- **Gestão de dependências automatizada**: Software Composition Analysis (SCA) teria alertado imediatamente sobre a CVE
- **Pipeline de deploy com verificação**: O pipeline teria impedido o deploy sem patch de segurança
- **Monitoramento contínuo**: Análise de comportamento de rede teria detectado o acesso não autorizado

---

## 7. Fase de Monitoramento e Resposta

### 7.1 Monitoramento de Segurança e Logging

```cpp
// secure_logger.h
#pragma once
#include <string>
#include <memory>
#include <mutex>
#include <fstream>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <functional>
#include <map>
#include <vector>
#include <iostream>

enum class LogLevel : uint8_t {
    TRACE = 0,
    DEBUG = 1,
    INFO = 2,
    WARNING = 3,
    ERROR = 4,
    CRITICAL = 5
};

enum class SecurityEventType : uint8_t {
    AUTH_SUCCESS,
    AUTH_FAILURE,
    AUTH_LOCKOUT,
    AUTHORIZATION_DENIED,
    INPUT_VALIDATION_FAILURE,
    RATE_LIMIT_EXCEEDED,
    SUSPICIOUS_ACTIVITY,
    DATA_ACCESS,
    DATA_MODIFICATION,
    CONFIG_CHANGE,
    PRIVILEGE_ESCALATION,
    INTEGRITY_VIOLATION
};

class SecurityLogger {
public:
    static SecurityLogger& instance() {
        static SecurityLogger logger;
        return logger;
    }

    void setLogFile(const std::string& path) {
        std::lock_guard<std::mutex> lock(mutex_);
        fileStream_.open(path, std::ios::app);
    }

    void setMinLevel(LogLevel level) {
        minLevel_ = level;
    }

    void logSecurityEvent(
        SecurityEventType type,
        const std::string& message,
        const std::string& userId = "",
        const std::string& sourceIp = "",
        const std::map<std::string, std::string>& metadata = {}) {

        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);

        std::stringstream ss;
        ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");

        nlohmann::json entry;
        entry["timestamp"] = ss.str();
        entry["level"] = "SECURITY";
        entry["event_type"] = securityEventTypeToString(type);
        entry["message"] = message;

        if (!userId.empty()) entry["user_id"] = userId;
        if (!sourceIp.empty()) entry["source_ip"] = sourceIp;
        if (!metadata.empty()) entry["metadata"] = metadata;

        writeLog(entry.dump());
    }

    void logAccess(
        const std::string& method,
        const std::string& path,
        int statusCode,
        const std::string& sourceIp,
        const std::string& userId = "") {

        nlohmann::json entry;
        entry["timestamp"] = currentTimestamp();
        entry["level"] = "INFO";
        entry["type"] = "access";
        entry["method"] = method;
        entry["path"] = path;
        entry["status"] = statusCode;
        entry["source_ip"] = sourceIp;
        if (!userId.empty()) entry["user_id"] = userId;

        writeLog(entry.dump());
    }

    void logError(const std::string& message, const std::string& details = "") {
        if (LogLevel::ERROR < minLevel_) return;

        nlohmann::json entry;
        entry["timestamp"] = currentTimestamp();
        entry["level"] = "ERROR";
        entry["message"] = message;
        if (!details.empty()) entry["details"] = details;

        writeLog(entry.dump());
    }

    std::vector<std::string> getRecentLogs(size_t count = 100) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<std::string> result(logBuffer_.end() -
            static_cast<std::ptrdiff_t>(std::min(count, logBuffer_.size())),
            logBuffer_.end());
        return result;
    }

private:
    SecurityLogger() = default;

    static std::string currentTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");
        return ss.str();
    }

    static const char* securityEventTypeToString(SecurityEventType type) {
        switch (type) {
            case SecurityEventType::AUTH_SUCCESS:         return "auth_success";
            case SecurityEventType::AUTH_FAILURE:         return "auth_failure";
            case SecurityEventType::AUTH_LOCKOUT:         return "auth_lockout";
            case SecurityEventType::AUTHORIZATION_DENIED: return "authorization_denied";
            case SecurityEventType::INPUT_VALIDATION_FAILURE: return "input_validation_failure";
            case SecurityEventType::RATE_LIMIT_EXCEEDED:  return "rate_limit_exceeded";
            case SecurityEventType::SUSPICIOUS_ACTIVITY:  return "suspicious_activity";
            case SecurityEventType::DATA_ACCESS:          return "data_access";
            case SecurityEventType::DATA_MODIFICATION:    return "data_modification";
            case SecurityEventType::CONFIG_CHANGE:        return "config_change";
            case SecurityEventType::PRIVILEGE_ESCALATION: return "privilege_escalation";
            case SecurityEventType::INTEGRITY_VIOLATION:  return "integrity_violation";
        }
        return "unknown";
    }

    void writeLog(const std::string& logEntry) {
        std::lock_guard<std::mutex> lock(mutex_);

        logBuffer_.push_back(logEntry);
        if (logBuffer_.size() > MAX_BUFFER_SIZE) {
            logBuffer_.erase(logBuffer_.begin());
        }

        if (fileStream_.is_open()) {
            fileStream_ << logEntry << "\n";
            fileStream_.flush();
        }
    }

    std::mutex mutex_;
    LogLevel minLevel_ = LogLevel::INFO;
    std::ofstream fileStream_;
    std::vector<std::string> logBuffer_;
    static constexpr size_t MAX_BUFFER_SIZE = 10000;
};
```

### 7.2 Detecção de Intrusão

```cpp
// intrusion_detector.h
#pragma once
#include <string>
#include <map>
#include <mutex>
#include <chrono>
#include <vector>
#include <algorithm>
#include <cmath>

class IntrusionDetector {
public:
    struct Alert {
        std::string type;
        std::string sourceIp;
        std::string description;
        std::chrono::system_clock::time_point timestamp;
        int severity; // 1-10
    };

    void recordRequest(const std::string& sourceIp, const std::string& path) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto now = std::chrono::system_clock::now();
        requestLog_[sourceIp].push_back({path, now});

        // Clean old entries (sliding window of 60 seconds)
        auto cutoff = now - std::chrono::seconds(60);
        auto& entries = requestLog_[sourceIp];
        entries.erase(
            std::remove_if(entries.begin(), entries.end(),
                [cutoff](const auto& e) { return e.timestamp < cutoff; }),
            entries.end()
        );
    }

    std::vector<Alert> detectAnomalies() {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<Alert> alerts;

        for (const auto& [ip, entries] : requestLog_) {
            // Check request rate
            if (entries.size() > RATE_THRESHOLD) {
                alerts.push_back({
                    "RATE_LIMIT",
                    ip,
                    "Request rate exceeded threshold: " + std::to_string(entries.size()) + " req/min",
                    std::chrono::system_clock::now(),
                    7
                });
            }

            // Check for path traversal attempts
            for (const auto& entry : entries) {
                if (entry.path.find("..") != std::string::npos) {
                    alerts.push_back({
                        "PATH_TRAVERSAL",
                        ip,
                        "Path traversal attempt detected: " + entry.path,
                        entry.timestamp,
                        8
                    });
                }

                // Check for SQL injection patterns
                if (hasSQLInjectionPattern(entry.path)) {
                    alerts.push_back({
                        "SQL_INJECTION",
                        ip,
                        "Possible SQL injection: " + entry.path,
                        entry.timestamp,
                        9
                    });
                }
            }
        }

        return alerts;
    }

private:
    struct RequestEntry {
        std::string path;
        std::chrono::system_clock::time_point timestamp;
    };

    static constexpr size_t RATE_THRESHOLD = 100;

    static bool hasSQLInjectionPattern(const std::string& input) {
        static const std::vector<std::string> patterns = {
            "UNION", "SELECT", "INSERT", "UPDATE", "DELETE",
            "DROP", "'", "--", ";"
        };

        for (const auto& pattern : patterns) {
            if (input.find(pattern) != std::string::npos) {
                return true;
            }
        }
        return false;
    }

    std::mutex mutex_;
    std::map<std::string, std::vector<RequestEntry>> requestLog_;
};
```

### 7.3 Gestão de Vulnerabilidades Pós-Deploy

Após o deploy, a gestão de vulnerabilidades continua:

1. **Varreduras periódicas**: Executar scan de vulnerabilidades semanalmente
2. **Monitoramento de CVE**: Acompanhar novas CVEs que afetam dependências
3. **Correções de emergência**: Processo para aplicar patches críticos rapidamente
4. **Verificação de integridade**: Monitorar integridade de binários e configurações
5. **Testes de penetração**: Realizar pentests periódicos em produção

---

## 8. Shift-Left Security

### 8.1 O que Shift-Left Significa para Segurança

"Shift-left" significa mover a detecção e correção de vulnerabilidades para estágios anteriores do desenvolvimento. Em vez de发现 problemas durante testes finais ou em produção, buscam-se durante o design, codificação e revisão.

**Impacto do timing na correção:**

| Fase de Descoberta | Custo Relativo |
|---|---|
| Requisitos | 1x |
| Design | 5x |
| Implementação | 10x |
| Teste | 50x |
| Deploy | 100x |
| Produção | 1000x+ |

### 8.2 Ferramentas e Práticas

| Ferramenta | Quando | O que detecta |
|---|---|---|
| Linters (clang-tidy) | Durante escrita | Code smells, padrões inseguros |
| Análise estática (cppcheck) | Build | Memory leaks, bugs, vulnerabilities |
| SAST (SonarQube) | CI pipeline | Vulnerabilidades de segurança |
| DAST (OWASP ZAP) | Deploy staging | Vulnerabilidades runtime |
| SCA (Snyk/Dependabot) | Build + diário | Dependências vulneráveis |
| Fuzzing (libFuzzer) | CI pipeline | Crashes, buffer overflows |
| Secret scanning | Pre-commit | Segredos hardcoded |
| Container scanning | Build | Vulnerabilities na imagem |

### 8.3 Fluxo de Trabalho do Desenvolvedor com Segurança Integrada

```
+-------+     +---------+     +--------+     +--------+
| Editar| --> | Salvar  | --> | Lint   | --> | Testar |
| codigo|     |         |     | auto   |     |        |
+-------+     +---------+     +--------+     +--------+
                                                |
                                                v
+-------+     +---------+     +--------+     +--------+
| Merge | <-- | Review  | <-- | Análise| <-- | Build  |
|       |     | seguranca|    | estática|    | seguro |
+-------+     +---------+     +--------+     +--------+
     |
     v
+-------+     +---------+     +--------+
| Deploy| --> | Monitor | --> | Responder|
| seguro|     |         |     | incidente|
+-------+     +---------+     +--------+
```

### 8.4 Medindo Postura de Segurança

Métricas essenciais para medir a postura de segurança:

```cpp
// security_metrics.h
#pragma once
#include <string>
#include <map>
#include <vector>
#include <chrono>
#include <numeric>

struct SecurityMetrics {
    // Vulnerability metrics
    size_t openCriticalVulns = 0;
    size_t openHighVulns = 0;
    size_t openMediumVulns = 0;
    size_t meanTimeToRemediate_hours = 0;
    float vulnDensity_perKLOC = 0.0f;

    // Code quality metrics
    float staticAnalysisAlertRate = 0.0f;
    float securityTestCoverage = 0.0f;
    size_t securityHotspots = 0;

    // Process metrics
    float threatModelCoverage = 0.0f;
    float securityGatePassRate = 0.0f;
    size_t securityTrainingHours = 0;

    // Incident metrics
    size_t securityIncidents = 0;
    float meanTimeToDetect_hours = 0.0f;
    float meanTimeToRespond_hours = 0.0f;

    float calculateOverallScore() const {
        float score = 0.0f;

        // Vuln score (lower is better)
        float vulnScore = 100.0f;
        vulnScore -= openCriticalVulns * 10.0f;
        vulnScore -= openHighVulns * 5.0f;
        vulnScore -= openMediumVulns * 2.0f;
        vulnScore = std::max(0.0f, std::min(100.0f, vulnScore));

        // Test coverage score
        float testScore = securityTestCoverage;

        // Process score
        float processScore = (threatModelCoverage + securityGatePassRate) / 2.0f;

        // Weighted average
        score = vulnScore * 0.4f + testScore * 0.3f + processScore * 0.3f;

        return score;
    }

    std::string getRating() const {
        float score = calculateOverallScore();
        if (score >= 90.0f) return "A";
        if (score >= 80.0f) return "B";
        if (score >= 70.0f) return "C";
        if (score >= 60.0f) return "D";
        return "F";
    }
};

class SecurityMetricsCollector {
public:
    void recordVulnerability(const std::string& severity) {
        std::lock_guard<std::mutex> lock(mutex_);
        vulnCounts_[severity]++;
    }

    SecurityMetrics calculateMetrics(size_t linesOfCode) const {
        std::lock_guard<std::mutex> lock(mutex_);
        SecurityMetrics metrics;

        metrics.openCriticalVulns = vulnCounts_.at("critical");
        metrics.openHighVulns = vulnCounts_.at("high");
        metrics.openMediumVulns = vulnCounts_.at("medium");

        size_t totalVulns = metrics.openCriticalVulns +
                           metrics.openHighVulns +
                           metrics.openMediumVulns;

        if (linesOfCode > 0) {
            metrics.vulnDensity_perKLOC =
                static_cast<float>(totalVulns) /
                static_cast<float>(linesOfCode / 1000);
        }

        return metrics;
    }

private:
    mutable std::mutex mutex_;
    std::map<std::string, size_t> vulnCounts_ = {
        {"critical", 0}, {"high", 0}, {"medium", 0}, {"low", 0}
    };
};
```

### 8.5 Pipeline CI/CD Completa com Portas de Segurança

{% raw %}
```yaml
# .github/workflows/security-pipeline.yml
name: Security-First CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  BUILD_TYPE: Release
  CXX_STANDARD: 17

jobs:
  # ============================================================
  # STAGE 1: Build with Security Flags
  # ============================================================
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ clang-tidy cppcheck

      - name: Configure CMake with security flags
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=${{ env.BUILD_TYPE }} \
            -DCMAKE_CXX_STANDARD=${{ env.CXX_STANDARD }} \
            -DENABLE_ASAN=ON \
            -DENABLE_UBSAN=ON

      - name: Build
        run: cmake --build build --parallel $(nproc)

  # ============================================================
  # STAGE 2: Static Analysis
  # ============================================================
  static-analysis:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run cppcheck
        run: |
          cppcheck --enable=all \
            --std=c++17 \
            --error-exitcode=1 \
            --inline-suppr \
            --suppress=missingIncludeSystem \
            -I include/ \
            src/ tests/

      - name: Run clang-tidy
        run: |
          find src/ -name "*.cpp" | xargs \
            clang-tidy -- -std=c++17 -Iinclude/

      - name: Run MISRA checks (if applicable)
        run: |
          echo "MISRA C++ compliance check placeholder"

  # ============================================================
  # STAGE 3: Security Testing with Sanitizers
  # ============================================================
  security-tests:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build with sanitizers
        run: |
          cmake -B build-debug \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_ASAN=ON \
            -DENABLE_UBSAN=ON \
            -DENABLE_TSAN=ON
          cmake --build build-debug

      - name: Run unit tests with sanitizers
        run: |
          cd build-debug
          ctest --output-on-failure

      - name: Run AddressSanitizer standalone
        run: |
          ./build-debug/bin/security_tests 2>&1 || \
            (echo "Sanitizer detected issues!" && exit 1)

  # ============================================================
  # STAGE 4: Fuzz Testing
  # ============================================================
  fuzz-testing:
    runs-on: ubuntu-latest
    needs: security-tests
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build fuzzer
        run: |
          clang++ -std=c++17 \
            -fsanitize=fuzzer,address,undefined \
            -g -O1 \
            fuzz/fuzz_input_validator.cpp \
            -I include/ \
            -o fuzz_input_validator

      - name: Run fuzzing (5 minutes)
        run: |
          mkdir -p corpus
          ./fuzz_input_validator \
            corpus/ \
            -max_total_time=300 \
            -max_len=1024 \
            -timeout=10

  # ============================================================
  # STAGE 5: Code Coverage
  # ============================================================
  code-coverage:
    runs-on: ubuntu-latest
    needs: security-tests
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build with coverage
        run: |
          cmake -B build-cov \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_COVERAGE=ON
          cmake --build build-cov

      - name: Run tests with coverage
        run: |
          cd build-cov
          ctest --output-on-failure

      - name: Generate coverage report
        run: |
          gcovr --root .. \
            --filter src/ \
            --print-summary \
            --fail-under-line 80

  # ============================================================
  # STAGE 6: Dependency Vulnerability Scan
  # ============================================================
  dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  # ============================================================
  # STAGE 7: Secret Scanning
  # ============================================================
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # ============================================================
  # STAGE 8: Security Gate
  # ============================================================
  security-gate:
    runs-on: ubuntu-latest
    needs: [build, static-analysis, security-tests, fuzz-testing,
            code-coverage, dependency-scan, secret-scan]
    steps:
      - name: Verify all security stages passed
        run: |
          echo "All security gates passed successfully"
          echo "Build: ${{ needs.build.result }}"
          echo "Static Analysis: ${{ needs.static-analysis.result }}"
          echo "Security Tests: ${{ needs.security-tests.result }}"
          echo "Fuzz Testing: ${{ needs.fuzz-testing.result }}"
          echo "Code Coverage: ${{ needs.code-coverage.result }}"
          echo "Dependency Scan: ${{ needs.dependency-scan.result }}"
          echo "Secret Scan: ${{ needs.secret-scan.result }}"

          if [ "${{ needs.build.result }}" != "success" ] || \
             [ "${{ needs.static-analysis.result }}" != "success" ] || \
             [ "${{ needs.security-tests.result }}" != "success" ] || \
             [ "${{ needs.fuzz-testing.result }}" != "success" ] || \
             [ "${{ needs.code-coverage.result }}" != "success" ] || \
             [ "${{ needs.dependency-scan.result }}" != "success" ] || \
             [ "${{ needs.secret-scan.result }}" != "success" ]; then
            echo "SECURITY GATE FAILED: One or more security stages failed"
            exit 1
          fi

  # ============================================================
  # STAGE 9: Deploy (only after all gates pass)
  # ============================================================
  deploy:
    runs-on: ubuntu-latest
    needs: security-gate
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy with security checks
        run: |
          echo "Deploying secure build..."
          bash deploy_secure.sh ${{ github.sha }}
```
{% endraw %}

---

## 9. Code Review como Gate de Segurança

### 9.1 Processo de Revisão de Código Focado em Segurança

A revisão de código de segurança vai além da revisão funcional. O revisor assume explicitamente a perspectiva de um atacante, buscando formas de abusar o código.

**Etapas do processo:**

1. **Preparação**: Revisar o threat model do componente sendo alterado
2. **Análise de superfície de ataque**: Identificar todas as entradas externas
3. **Rastreamento de dados**: Seguir dados de entrada até seus efeitos
4. **Verificação de边界**: Validar limites de confiança e tratamento de erros
5. **Busca por padrões inseguros**: Usar checklists de segurança

### 9.2 Checklist para Revisão de Segurança em C++

| # | Área | Verificação | Critérios |
|---|---|---|---|
| 1 | Entrada | Todos os inputs validados? | Whitelist, length, charset |
| 2 | Buffer | Uso seguro de memória? | Smart pointers, bounds checking |
| 3 | Injeção | Proteção contra injeção? | Prepared statements, escaping |
| 4 | Autenticação | Auth robusta? | MFA, token validation |
| 5 | Autorização | Least privilege? | RBAC, deny by default |
| 6 | Criptografia | Algoritmos aprovados? | AES-256, RSA-2048+, TLS 1.3 |
| 7 | Segredos | Hardcoded secrets? | Vault, env vars |
| 8 | Erros | Tratamento seguro? | No info leak, proper cleanup |
| 9 | Logs | Logging adequado? | Security events, no sensitive data |
| 10 | Concorrência | Race conditions? | Proper locking, atomic ops |

### 9.3 Anotações e Comentários de Revisão de Segurança

```cpp
// security_review_annotations.h
#pragma once
// SECURITY REVIEW ANNOTATIONS
//
// Use these macros and comment patterns to flag security-relevant code
// during review. They serve as documentation and can be grepped.

// Mark code that requires security review
#define SECURITY_REVIEW_REQUIRED \
    // SECURITY: This code handles sensitive data or trust boundary crossing

// Mark code that has been reviewed
#define SECURITY_REVIEWED \
    // SECURITY-REVIEWED: This code has been reviewed by [name] on [date]

// Mark code that is a known security risk (accepted risk)
#define SECURITY_ACCEPTED_RISK \
    // SECURITY-RISK-ACCEPTED: [reason] - approved by [name] on [date]

// ============================================================
// Example: Security annotations in practice
// ============================================================

// SECURITY: This function validates user input at trust boundary
// SECURITY-REVIEWED: John Doe, 2024-01-15
// REVIEW NOTES: Verified all paths return error on invalid input
void validateUserInput(const std::string& input) {
    // SECURITY: Length validation prevents DoS via large input
    if (input.length() > MAX_INPUT_LENGTH) {
        throw SecurityError("Input exceeds maximum length");
    }

    // SECURITY: Charset validation prevents injection attacks
    for (char c : input) {
        if (!isAllowedCharacter(c)) {
            throw SecurityError("Invalid character in input");
        }
    }

    // SECURITY-RISK-ACCEPTED: Performance optimization for trusted internal
    // callers. Risk: caller must guarantee non-null pointer.
    // Approved by: Jane Smith, 2024-01-20
    processInputInternal(input.c_str());
}

// SECURITY: This function handles cryptographic operations
// SECURITY-REVIEWED: John Doe, 2024-01-15
// REVIEW NOTES: Verified key derivation, IV generation, and tag validation
class EncryptionHandler {
public:
    // SECURITY: Uses AES-256-GCM (approved algorithm)
    std::vector<uint8_t> encrypt(
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& iv) {

        // SECURITY: Key length validation
        if (key.size() != 32) {
            throw SecurityError("Invalid key length for AES-256");
        }

        // SECURITY: IV must be unique per encryption operation
        if (iv.size() != 12) {
            throw SecurityError("Invalid IV length for GCM");
        }

        // ... encryption implementation
        return {};
    }
};
```

### 9.4 Estudo de Caso CVE: Heartbleed Descoberto por Code Review

O Heartbleed foi finalmente descoberto quando um revisor humano analisou o código do OpenSSL. A revisão manual do código, após uma auditoria de segurança solicitada, identificou a validação ausente no heartbeat handler.

**Pontos-chave:**

- O bug estava em apenas **duas linhas de código** — uma alocação de buffer baseada em input do usuário sem validação
- Code review automatizado (análise estática) poderia ter detectado o padrão de over-read
- Revisão humana focada em segurança identificou o problema quando aplicada
- O bug existia por **dois anos** — nenhum review anterior havia focado naquele componente

**Lições:**
- Code review de segurança deve ser específico e estruturado
- Ferramentas de análise estática devem ser executadas em todo commit
- Componentes críticos de segurança precisam de reviewers especializados

---

## 10. Exemplo Completo: Pipeline SDD

### 10.1 Pipeline Completo com Todas as Portas de Segurança

```yaml
# .gitlab-ci.yml - Complete Security Pipeline
stages:
  - build
  - analyze
  - test
  - fuzz
  - security-gate
  - deploy

variables:
  CMAKE_BUILD_TYPE: "Release"
  CXX_STANDARD: "17"
  COVERAGE_THRESHOLD: "80"

# ============================================================
# STAGE 1: Build with Security Flags
# ============================================================
build:
  stage: build
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y cmake g++ git
  script:
    - |
      cmake -B build \
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE} \
        -DCMAKE_CXX_STANDARD=${CXX_STANDARD} \
        -DCMAKE_CXX_FLAGS="-Wall -Wextra -Wpedantic -Werror" \
        -DENABLE_ASAN=ON \
        -DENABLE_UBSAN=ON
    - cmake --build build --parallel $(nproc)
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

# ============================================================
# STAGE 2: Static Analysis
# ============================================================
clang-tidy:
  stage: analyze
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y clang-tidy
  script:
    - |
      find src/ -name "*.cpp" -o -name "*.h" | while read file; do
        echo "Analyzing: $file"
        clang-tidy "$file" \
          --checks='*,-llvmlibc-*,-altera-*,-modernize-use-trailing-return-type' \
          --warnings-as-errors='*' \
          -- -std=c++17 -Iinclude/
      done
  allow_failure: false

cppcheck:
  stage: analyze
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y cppcheck
  script:
    - |
      cppcheck \
        --enable=all \
        --std=c++17 \
        --error-exitcode=1 \
        --inline-suppr \
        --suppress=missingIncludeSystem \
        --suppress=unmatchedSuppression \
        --check-level=exhaustive \
        -I include/ \
        --output-file=cppcheck-report.txt \
        src/
      cat cppcheck-report.txt
  artifacts:
    paths:
      - cppcheck-report.txt

# ============================================================
# STAGE 3: Security Testing with Sanitizers
# ============================================================
sanitize-tests:
  stage: test
  image: ubuntu:22.04
  needs: [build]
  before_script:
    - apt-get update && apt-get install -y cmake g++ libgtest-dev
  script:
    - |
      cmake -B build-test \
        -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_CXX_STANDARD=17 \
        -DENABLE_ASAN=ON \
        -DENABLE_UBSAN=ON \
        -DENABLE_COVERAGE=ON
      cmake --build build-test --parallel $(nproc)
      cd build-test && ctest --output-on-failure --verbose
  artifacts:
    when: always
    paths:
      - build-test/

coverage:
  stage: test
  image: ubuntu:22.04
  needs: [sanitize-tests]
  before_script:
    - apt-get update && apt-get install -y gcovr
  script:
    - |
      gcovr --root .. \
        --filter src/ \
        --exclude-throw-lines \
        --print-summary \
        --fail-under-line ${COVERAGE_THRESHOLD}
  artifacts:
    paths:
      - coverage-report/

# ============================================================
# STAGE 4: Fuzz Testing
# ============================================================
fuzz:
  stage: fuzz
  image: ubuntu:22.04
  needs: [build]
  before_script:
    - apt-get update && apt-get install -y clang
  script:
    - |
      # Build fuzzer
      clang++ -std=c++17 \
        -fsanitize=fuzzer,address,undefined \
        -g -O1 \
        fuzz/fuzz_input_validator.cpp \
        -I include/ \
        src/*.cpp \
        -o fuzz_target

      # Create corpus directory
      mkdir -p corpus

      # Run fuzzing for limited time
      timeout 300 ./fuzz_target \
        corpus/ \
        -max_total_time=240 \
        -max_len=1024 \
        -timeout=10 \
        -dict=fuzz/dictionary.txt \
        || true

      # Check for crashes
      if [ -d "crash-*" ] || ls crash-* 2>/dev/null; then
        echo "FUZZING FAILED: Crashes detected!"
        ls -la crash-*
        exit 1
      fi

      echo "Fuzzing completed without crashes"

# ============================================================
# STAGE 5: Security Gate
# ============================================================
security-gate:
  stage: security-gate
  needs:
    - clang-tidy
    - cppcheck
    - sanitize-tests
    - coverage
    - fuzz
  script:
    - |
      echo "=== SECURITY GATE CHECK ==="
      echo "All security stages must pass before deploy"

      # Verify no critical issues
      if [ -f cppcheck-report.txt ]; then
        if grep -q "error:" cppcheck-report.txt; then
          echo "FAILED: cppcheck errors found"
          exit 1
        fi
      fi

      echo "SECURITY GATE: PASSED"
      echo "All security checks completed successfully"

# ============================================================
# STAGE 6: Deploy
# ============================================================
deploy-production:
  stage: deploy
  needs: [security-gate]
  only:
    - main
  script:
    - |
      echo "Deploying with verified security posture"
      bash deploy_secure.sh "${CI_COMMIT_SHA}"
  environment:
    name: production
```

### 10.2 Explicação de Cada Estágio

**Build**: Compila o código com todas as flags de segurança habilitadas. `-fstack-protector-strong` detecta buffer overflows na stack. `-D_FORTIFY_SOURCE=2` adiciona verificações em runtime. PIE e RELRO protegem contra exploits de memória.

**Static Analysis**: clang-tidy e cppcheck verificam o código contra padrões conhecidos de vulnerabilidade. clang-tidy detecta code smells e padrões inseguros. cppcheck busca memory leaks, use-after-free e outros bugs de memória.

**Sanitizers**: AddressSanitizer (ASan) detecta buffer overflows, use-after-free, memory leaks. UndefinedBehaviorSanitizer (UBSan) detecta integer overflow, null pointer dereference, alignment issues. Code coverage mede a efetividade dos testes.

**Fuzzing**: libFuzzer gera milhares de entradas aleatórias buscando crashes e comportamentos inesperados. É especialmente eficaz para encontrar bugs em parsers, validadores e processadores de input.

**Security Gate**: Ponto de verificação final que impede deploy se qualquer verificação de segurança falhar. É a última defesa antes da produção.

**Deploy**: Script que aplica hardening, verifica integridade, configura monitoring e executa health checks.

---

## 11. Referências

1. Microsoft. *Security Development Lifecycle (SDL)*. Microsoft Security Documentation, 2023.

2. Howard, M.; Lipner, S. *The Security Development Lifecycle*. Microsoft Press, 2006.

3. OWASP Foundation. *OWASP Software Assurance Maturity Model (SAMM)*. OWASP, 2023.

4. CERT. *SEI CERT C++ Coding Standard*. Software Engineering Institute, Carnegie Mellon University, 2023.

5. MISRA. *MISRA C++:2023 — Guidelines for the Use of the C++17 Language in Critical Systems*. MISRA, 2023.

6. NIST. *Secure Software Development Framework (SSDF) Version 1.1*. NIST SP 800-218, 2022.

7. Heartbleed. *CVE-2014-0160: OpenSSL Heartbeat Extension Memory Disclosure*. National Vulnerability Database, 2014.

8. Shellshock. *CVE-2014-6271: GNU Bash Remote Code Execution*. National Vulnerability Database, 2014.

9. Equifax. *Equifax Data Breach 2017: Technical Report*. Federal Trade Commission, 2018.

10. SolarWinds. *SolarWinds Orion Supply Chain Attack Analysis*. CISA Advisory, 2021.

11. Log4Shell. *CVE-2021-44228: Apache Log4j Remote Code Execution*. Apache Software Foundation, 2021.

12. Microsoft. *Threat Modeling Tool*. Microsoft Security Development, 2023.

13. libFuzzer. *LibFuzzer — A library for coverage-guided fuzz testing*. LLVM Project, 2023.

14. Google. *AddressSanitizer: A Fast Memory Error Detector*. Google Security, 2023.

15. SonarSource. *SonarQube: Continuous Code Quality and Security*. SonarSource, 2023.

16. OWASP. *OWASP Top Ten Web Application Security Risks*. OWASP Foundation, 2021.

17. CWE. *Common Weakness Enumeration*. MITRE, 2023.

18. ISO/IEC. *ISO/IEC 27001:2022 — Information Security Management*. International Organization for Standardization, 2022.

19. NIST. *Framework for Improving Critical Infrastructure Cybersecurity (CSF) Version 2.0*. NIST, 2024.

20. Linux Foundation. *OpenSSF Best Practices*. Open Source Security Foundation, 2023.

---

## Exercícios

**Exercício 1**: Escreva um threat model completo para um sistema de chat em tempo real em C++, identificando pelo menos 10 ameaças STRIDE e propondo mitigações para cada uma.

**Exercício 2**: Implemente um pipeline CI/CD para um projeto C++ existente que inclua pelo menos 4 portas de segurança diferentes. Documente cada porta e seu critério de aprovação.

**Exercício 3**: Escreva um conjunto de pelo menos 20 testes unitários de segurança para uma função de parsing de JSON, cobrindo边界 cases como entradas vazias, strings extremamente longas, caracteres especiais e tentativas de injeção.

**Exercício 4**: Analise o caso Heartbleed (CVE-2014-0160) e documente como cada fase do Secure SDLC teria prevenido ou detectado a vulnerabilidade. Inclua ferramentas específicas que poderiam ter sido usadas.

**Exercício 5**: Implemente um sistema de logging de segurança em C++ que atenda aos requisitos PCI-DSS 10.2 para auditoria de transações. Inclua proteção contra log injection e integrity verification.

---

*Este capítulo estabelece as bases para o Secure Software Development Lifecycle. Nos capítulos seguintes, aprofundaremos cada fase com técnicas avançadas e implementações práticas em C++.*
---

*[Capítulo anterior: 01 — Introducao Ao Sdd](01-introducao-ao-sdd.md)*
*[Próximo capítulo: 03 — Principios De Codificacao Segura](03-principios-de-codificacao-segura.md)*
