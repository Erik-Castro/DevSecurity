# Capítulo 15 — Resposta a Incidentes de Segurança

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Estruturar e implementar um plano completo de resposta a incidentes de segurança, incluindo funções, responsabilidades, procedimentos de escalação e comunicação para organizações de qualquer porte.
2. Classificar incidentes por severidade e impacto, aplicando metodologias como CVSS e matrizes de classificação para priorizar a resposta de forma eficiente e consistente.
3. Implementar ferramentas de detecção, contenção, erradicação e recuperação em C++17, incluindo analisadores de log, verificadores de integridade e scanners de vulnerabilidade.
4. Conduzir análise forense de binários e logs, aplicando técnicas de memory forensics e log forensics para compreender o escopo e os vetores de ataque de um incidente.
5. Realizar disclosure responsável de vulnerabilidades e conduzir post-mortems sem culpa (blameless), transformando incidentes em aprendizados organizacionais duradouros.

---

## 1. Planejamento de Resposta a Incidentes

### 1.1 Estrutura do Plano de Resposta a Incidentes

Um plano de resposta a incidentes não é um documento estático — é um vivo instrumento operacional que deve ser testado, revisado e atualizado regularmente. A ausência de um plano estruturado é, na prática, a causa mais comum de falhas catastróficas na resposta a incidentes reais.

A estrutura fundamental de um plano de resposta a incidentes segue o framework NIST SP 800-61 Rev. 2, composto por quatro fases principais:

| Fase | Atividades Principais | Entregáveis |
|------|----------------------|-------------|
| Preparação | Treinamento, ferramentas, comunicação | Plano documentado, equipe treinada |
| Detecção e Análise | Monitoramento, alertas, triagem | Relatório de incidente inicial |
| Contenção, Erradicação e Recuperação | Isolamento, remoção, restauração | Ações de resposta, verificação |
| Atividades Pós-Incidente | Análise, lições aprendidas, melhorias | Post-mortem, plano atualizado |

### 1.2 Funções e Responsabilidades

A definição clara de funções é essencial para evitar confusão durante um incidente. Cada membro da equipe deve saber exatamente o que se espera dele e quem tem autoridade para tomar decisões em cada cenário.

**Estrutura típica de uma equipe de resposta a incidentes:**

| Função | Responsabilidade Principal | Autoridade |
|--------|---------------------------|------------|
| Incident Commander (IC) | Coordena toda a resposta, toma decisões finais | Escalação executiva |
| Security Lead | Análise técnica, contenção, erradicação | Decisões técnicas |
| Communications Lead | Comunicação interna e externa | Aprovação de mensagens |
| Legal Counsel | Orientação regulatória e legal | Decisões de disclosure |
| IT Operations | Execução de ações técnicas (reboot, patch, restore) | Acesso a infraestrutura |
| Business Owner | Decisões de impacto ao negócio | Priorização de restauração |
| Forensics Analyst | Coleta e preservação de evidências | Cadeia de custódia |

### 1.3 Plano de Comunicação

A comunicação durante um incidente é frequentemente subestimada. A falta de um plano de comunicação claro leva a vazamentos de informação inconsistentes, pânico desnecessário e danos reputacionais desproporcionais.

**Canais de comunicação durante um incidente:**

1. **Canal técnico principal**: Slack/Teams dedicado ao incidente (não o canal geral)
2. **Canal de status**: Página de status pública (statuspage.io ou similar)
3. **Comunicação interna**: E-mail executivo com atualizações periódicas
4. **Comunicação externa**: Comunicado à imprensa, se necessário
5. **Regulatória**: Notificação a autoridades (ANPD, CERT, FBI)

**Regra de ouro**: Nenhuma comunicação externa é autorizada sem aprovação do Incident Commander e do Legal Counsel.

### 1.4 Procedimentos de Escalação

A escalação segue um padrão baseado em severidade e tempo de resposta:

| Severidade | Tempo Máximo para Escalação | Quem é Informado |
|-----------|---------------------------|-------------------|
| Crítico (P1) | 15 minutos | CEO, CISO, Board, Legal |
| Alto (P2) | 1 hora | CISO, VP Engenharia, Legal |
| Médio (P3) | 4 horas | Security Lead, Eng. Manager |
| Baixo (P4) | 24 horas | Security Team |

### 1.5 Template Completo de Plano de Resposta a Incidentes

```yaml
# Incident Response Plan - [Organizacao]
# Versao: 1.0 | Ultima revisao: 2024-01-15
# Dono: CISO

---
## 1. Escopo
Este plano cobre todos os incidentes de segurança da organizacao,
incluindo violacoes de dados, ataques ciberneticos, falhas de
sistemas criticos e incidentes de conformidade.

## 2. Definicoes
- INCIDENTE: Qualquer evento que ameace a confidencialidade,
  integridade ou disponibilidade dos sistemas ou dados.
- BREACH: Incidente que resulta em acesso nao autorizado a dados
  protegidos.
- SECURITY EVENT: Ocorrencia que pode indicar um incidente em
  andamento ou futuro.

## 3. Equipe de Resposta
- Incident Commander: [Nome] - [contato]
- Security Lead: [Nome] - [contato]
- Communications Lead: [Nome] - [contato]
- Legal Counsel: [Nome] - [contato]
- IT Operations Lead: [Nome] - [contato]
- Business Owner: [Nome] - [contato]

## 4. Classificacao de Severidade
(Ver Secao 2 deste documento)

## 5. Procedimentos por Fase
### 5.1 Preparacao
- [ ] Plano revisado e aprovado (ultima revisao: YYYY-MM-DD)
- [ ] Equipe treinada (ultimo treinamento: YYYY-MM-DD)
- [ ] Ferramentas testadas (ultimo teste: YYYY-MM-DD)
- [ ] Contact list atualizada

### 5.2 Deteccao e Analise
- [ ] Alerta recebido e registrado no sistema de ticketing
- [ ] Triagem inicial completada em 15 minutos
- [ ] Severidade classificada
- [ ] Incident Commander notificado

### 5.3 Contencao
- [ ] Plano de contencao definido
- [ ] Acoes de contencao executadas
- [ ] Evidencias preservadas
- [ ] Impacto avaliado

### 5.4 Erradicacao
- [ ] Causa raiz identificada
- [ ] Vulnerabilidade removida/patcheada
- [ ] Sistemas limpos

### 5.5 Recuperacao
- [ ] Sistemas restaurados
- [ ] Integridade verificada
- [ ] Monitoramento reforçado
- [ ] Funcionalidade confirmada

### 5.6 Pos-Incidente
- [ ] Post-mortem conduzido em ate 5 dias uteis
- [ ] Lições documentadas
- [ ] Acoes corretivas definidas com dono e deadline
- [ ] Plano de resposta atualizado

## 6. Contactos de Emergencia
- CERT Nacional: [telefone]
- ANPD: [telefone]
- Advogado de plantao: [telefone]
- Seguradora de cyber: [telefone]
```

---

## 2. Classificação de Incidentes

### 2.1 Níveis de Severidade e Categorias

A classificação correta de um incidente determina a velocidade e a escala da resposta. Um incidente mal classificado pode resultar em recursos insuficientes para uma crise real, ou em mobilização desnecessária para um falso positivo.

**Matriz de Classificação de Severidade:**

| Severidade | Descrição | Tempo de Resposta | Exemplos |
|-----------|-----------|-------------------|----------|
| P1 - Crítico | Ameaça existencial ao negócio, violação massiva de dados | 15 min | Ransomware em produção, exfiltração de dados de milhões de registros |
| P2 - Alto | Impacto significativo, potencial de escalação | 1 hora | Comprometimento de conta admin, vulnerabilidade zero-day ativa |
| P3 - Médio | Impacto limitado, contido | 4 horas | Malware em estação de trabalho isolada, tentativa de phishing |
| P4 - Baixo | Sem impacto imediato, melhoria de processo | 24 horas | Escaneamento de portas detectado, violação de política menor |

### 2.2 Metodologia de Avaliação de Impacto

O impacto de um incidente é avaliado em três dimensões:

1. **Impacto ao Negócio**: Perda financeira, interrupção de operações, dano reputacional
2. **Impacto Técnico**: Sistemas comprometidos, dados afetados, integridade comprometida
3. **Impacto Regulatório**: Violações de conformidade, obrigações de notificação

**Fórmula de Priorização:**

```
Prioridade = (Impacto ao Negócio x 3) + (Impacto Técnico x 2) + (Impacto Regulatório x 2)
```

### 2.3 CVSS Scoring Explicado

O Common Vulnerability Scoring System (CVSS) v3.1 fornece um framework padronizado para avaliar a gravidade de vulnerabilidades. É essencial para classificar incidentes que envolvem vulnerabilidades conhecidas.

**Métricas CVSS v3.1:**

| Métrica | Descrição | Valores |
|---------|-----------|---------|
| Attack Vector (AV) | Como a vulnerabilidade é explorada | Network (N), Adjacent (A), Local (L), Physical (P) |
| Attack Complexity (AC) | Dificuldade de exploração | Low (L), High (H) |
| Privileges Required (PR) | Privilégios necessários | None (N), Low (L), High (H) |
| User Interaction (UI) | Interação do usuário necessária | None (N), Required (R) |
| Scope (S) | Impacto em componentes diferentes | Unchanged (U), Changed (C) |
| Confidentiality (C) | Impacto na confidencialidade | None (N), Low (L), High (H) |
| Integrity (I) | Impacto na integridade | None (N), Low (L), High (H) |
| Availability (A) | Impacto na disponibilidade | None (N), Low (L), High (H) |

**Faixas de Score:**

| Faixa | Classificação | Ação Recomendada |
|-------|---------------|------------------|
| 9.0 - 10.0 | Crítico | Resposta imediata, patch urgente |
| 7.0 - 8.9 | Alto | Resposta em 24-48 horas |
| 4.0 - 6.9 | Médio | Resposta em 1-2 semanas |
| 0.1 - 3.9 | Baixo | Resposta no ciclo normal |

### 2.4 Implementação C++ de Classificação de Severidade

```cpp
// severity_classifier.h - Sistema de Classificacao de Incidentes
#pragma once

#include <string>
#include <chrono>
#include <vector>
#include <cstdint>
#include <algorithm>
#include <sstream>
#include <iomanip>

namespace security {

enum class Severity : uint8_t {
    LOW = 4,
    MEDIUM = 3,
    HIGH = 2,
    CRITICAL = 1,
    UNKNOWN = 0
};

enum class IncidentCategory : uint8_t {
    DATA_BREACH,
    MALWARE,
    RANSOMWARE,
    PHISHING,
    DOS,
    UNAUTHORIZED_ACCESS,
    INSIDER_THREAT,
    SUPPLY_CHAIN,
    ZERO_DAY,
    CONFIGURATION_ERROR
};

enum class BusinessImpact : uint8_t {
    NONE = 0,
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
};

enum class TechnicalImpact : uint8_t {
    NONE = 0,
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
};

enum class RegulatoryImpact : uint8_t {
    NONE = 0,
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
};

struct CVSSScore {
    float base_score = 0.0f;
    float temporal_score = 0.0f;
    float environmental_score = 0.0f;

    std::string get_rating() const {
        if (base_score >= 9.0f) return "CRITICAL";
        if (base_score >= 7.0f) return "HIGH";
        if (base_score >= 4.0f) return "MEDIUM";
        return "LOW";
    }

    bool requires_immediate_response() const {
        return base_score >= 7.0f;
    }
};

struct Incident {
    std::string id;
    std::string title;
    IncidentCategory category;
    Severity severity;
    BusinessImpact business_impact;
    TechnicalImpact technical_impact;
    RegulatoryImpact regulatory_impact;
    CVSSScore cvss;
    std::chrono::system_clock::time_point detected_at;
    std::chrono::system_clock::time_point reported_at;
    std::vector<std::string> affected_systems;
    std::string description;
    bool data_breach = false;

    int calculate_priority_score() const {
        return (static_cast<int>(business_impact) * 3) +
               (static_cast<int>(technical_impact) * 2) +
               (static_cast<int>(regulatory_impact) * 2);
    }

    std::chrono::minutes time_to_detection() const {
        return std::chrono::duration_cast<std::chrono::minutes>(
            reported_at - detected_at);
    }
};

class SeverityClassifier {
public:
    static Severity classify_incident(
        BusinessImpact biz,
        TechnicalImpact tech,
        RegulatoryImpact reg,
        bool data_compromised = false
    ) {
        int score = (static_cast<int>(biz) * 3) +
                    (static_cast<int>(tech) * 2) +
                    (static_cast<int>(reg) * 2);

        if (data_compromised && score >= 14) return Severity::CRITICAL;
        if (score >= 18) return Severity::CRITICAL;
        if (score >= 12) return Severity::HIGH;
        if (score >= 6) return Severity::MEDIUM;
        return Severity::LOW;
    }

    static std::string severity_to_string(Severity s) {
        switch (s) {
            case Severity::CRITICAL: return "CRITICO";
            case Severity::HIGH: return "ALTO";
            case Severity::MEDIUM: return "MEDIO";
            case Severity::LOW: return "BAIXO";
            default: return "DESCONHECIDO";
        }
    }

    static std::string category_to_string(IncidentCategory c) {
        switch (c) {
            case IncidentCategory::DATA_BREACH: return "Violacao de Dados";
            case IncidentCategory::MALWARE: return "Malware";
            case IncidentCategory::RANSOMWARE: return "Ransomware";
            case IncidentCategory::PHISHING: return "Phishing";
            case IncidentCategory::DOS: return "Denegacao de Servico";
            case IncidentCategory::UNAUTHORIZED_ACCESS:
                return "Acesso Nao Autorizado";
            case IncidentCategory::INSIDER_THREAT: return "Ameaca Interna";
            case IncidentCategory::SUPPLY_CHAIN:
                return "Cadeia de Suprimentos";
            case IncidentCategory::ZERO_DAY: return "Zero-Day";
            case IncidentCategory::CONFIGURATION_ERROR:
                return "Erro de Configuracao";
            default: return "Desconhecido";
        }
    }

    static std::string generate_incident_report(const Incident& inc) {
        std::ostringstream report;
        report << "=== RELATORIO DE INCIDENTE ===" << "\n";
        report << "ID: " << inc.id << "\n";
        report << "Titulo: " << inc.title << "\n";
        report << "Categoria: " << category_to_string(inc.category) << "\n";
        report << "Severidade: " << severity_to_string(inc.severity) << "\n";
        report << "CVSS Base Score: " << std::fixed << std::setprecision(1)
               << inc.cvss.base_score << " (" << inc.cvss.get_rating()
               << ")\n";
        report << "Prioridade: " << inc.calculate_priority_score() << "/28\n";
        report << "Deteccao: "
               << std::chrono::system_clock::to_time_t(inc.detected_at)
               << "\n";
        report << "Tempo para deteccao: " << inc.time_to_detection().count()
               << " minutos\n";
        report << "Sistemas afetados: " << inc.affected_systems.size() << "\n";
        for (const auto& sys : inc.affected_systems) {
            report << "  - " << sys << "\n";
        }
        report << "Vazamento de dados: "
               << (inc.data_breach ? "SIM" : "NAO") << "\n";
        report << "==============================" << "\n";
        return report.str();
    }
};

} // namespace security
```

---

## 3. Detecção e Análise

### 3.1 Monitoramento de Segurança e Alertas

A detecção é a primeira linha de defesa efetiva. Uma infraestrutura de monitoramento madura combina múltiplas fontes de dados para criar uma visão unificada do estado de segurança da organização.

**Fontes de dados para detecção:**

| Fonte | Tipo de Dado | Ferramentas Típicas |
|-------|-------------|---------------------|
| Logs de aplicação | Eventos de negócio, erros | Fluentd, Logstash |
| Logs de sistema | Autenticação, processos | rsyslog, journald |
| Logs de rede | Tráfego, conexões | Zeek, Suricata |
| Logs de cloud | API calls, mudanças config | CloudTrail, Audit Logs |
| EDR | Comportamento de endpoint | CrowdStrike, SentinelOne |
| Vulnerability scans | Status de patches | Nessus, OpenVAS |
| Threat Intelligence | IOC, TTPs | MISP, OpenCTI |

### 3.2 Padrões de Análise de Log

A análise eficaz de logs requer a identificação de padrões que indicam atividade maliciosa. Os padrões mais comuns incluem:

**Padrões de ataque em logs de autenticação:**

```
# Brute force - multiplos falhas de login
2024-01-15T03:22:15Z login FAILED user=admin source=192.168.1.100
2024-01-15T03:22:16Z login FAILED user=admin source=192.168.1.100
2024-01-15T03:22:17Z login FAILED user=admin source=192.168.1.100
... (50 tentativas em 60 segundos)

# Credential stuffing - multiplos usuarios, mesmo IP
2024-01-15T04:01:00Z login FAILED user=user1 source=10.0.0.50
2024-01-15T04:01:02Z login FAILED user=user2 source=10.0.0.50
2024-01-15T04:01:04Z login FAILED user=user3 source=10.0.0.50

# Lateral movement - logins sucessivos de IP incomum
2024-01-15T05:30:00Z login OK user=sysadmin source=172.16.0.99
2024-01-15T05:30:45Z login OK user=backupsvc source=172.16.0.99
2024-01-15T05:31:10Z login OK user=root source=172.16.0.99
```

### 3.3 Detecção de Anomalias

A detecção de anomalias compara o comportamento atual com uma baseline estabelecida. Existem duas abordagens principais:

1. **Regras estáticas**: Limiares fixos (ex: mais de 10 falhas de login em 1 minuto)
2. **Análise estatística**: Desvios do comportamento normal (ex: desvio padrão)

### 3.4 Ferramenta C++ de Análise de Logs

```cpp
// log_analyzer.h - Analisador de Logs de Seguranca
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <chrono>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <mutex>
#include <functional>
#include <cmath>
#include <numeric>

namespace security {

struct LogEntry {
    std::chrono::system_clock::time_point timestamp;
    std::string source_ip;
    std::string user;
    std::string event_type;
    std::string detail;
    bool is_failure = false;
};

struct AnomalyPattern {
    std::string name;
    std::string description;
    int threshold;
    std::chrono::seconds window;
    std::function<bool(const std::vector<LogEntry>&)> matcher;
};

struct DetectionResult {
    bool anomaly_detected;
    std::string pattern_name;
    std::string description;
    int matched_count;
    std::vector<LogEntry> matching_entries;
    std::string recommended_action;
};

class LogAnalyzer {
private:
    std::vector<LogEntry> entries_;
    std::vector<AnomalyPattern> patterns_;
    mutable std::mutex mutex_;

public:
    LogAnalyzer() {
        register_default_patterns();
    }

    void add_entry(const LogEntry& entry) {
        std::lock_guard<std::mutex> lock(mutex_);
        entries_.push_back(entry);
    }

    void load_from_file(const std::string& filepath) {
        std::ifstream file(filepath);
        if (!file.is_open()) return;

        std::string line;
        while (std::getline(file, line)) {
            LogEntry entry = parse_log_line(line);
            if (!entry.source_ip.empty()) {
                add_entry(entry);
            }
        }
    }

    std::vector<DetectionResult> analyze() {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<DetectionResult> results;

        for (const auto& pattern : patterns_) {
            DetectionResult result = check_pattern(pattern);
            if (result.anomaly_detected) {
                results.push_back(result);
            }
        }

        std::sort(results.begin(), results.end(),
            [](const DetectionResult& a, const DetectionResult& b) {
                return a.matched_count > b.matched_count;
            });

        return results;
    }

    void register_pattern(const AnomalyPattern& pattern) {
        std::lock_guard<std::mutex> lock(mutex_);
        patterns_.push_back(pattern);
    }

    std::unordered_map<std::string, int> get_ip_frequency() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::unordered_map<std::string, int> freq;
        for (const auto& e : entries_) {
            freq[e.source_ip]++;
        }
        return freq;
    }

    std::unordered_map<std::string, int> get_user_failure_count() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::unordered_map<std::string, int> count;
        for (const auto& e : entries_) {
            if (e.is_failure) {
                count[e.user]++;
            }
        }
        return count;
    }

    double calculate_entropy(const std::string& ip_prefix) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::unordered_map<std::string, int> user_counts;
        int total = 0;

        for (const auto& e : entries_) {
            if (e.source_ip.find(ip_prefix) == 0) {
                user_counts[e.user]++;
                total++;
            }
        }

        if (total == 0) return 0.0;

        double entropy = 0.0;
        for (const auto& [user, count] : user_counts) {
            double p = static_cast<double>(count) / total;
            if (p > 0) {
                entropy -= p * std::log2(p);
            }
        }
        return entropy;
    }

private:
    LogEntry parse_log_line(const std::string& line) {
        LogEntry entry;
        std::istringstream iss(line);
        std::string timestamp_str;

        if (std::getline(iss, timestamp_str, ' ') &&
            std::getline(iss, event_type, ' ') &&
            std::getline(iss, detail)) {

            entry.event_type = event_type;
            entry.detail = detail;
            entry.is_failure = (detail.find("FAILED") != std::string::npos);

            auto ip_pos = detail.find("source=");
            if (ip_pos != std::string::npos) {
                entry.source_ip = detail.substr(ip_pos + 7);
                auto space = entry.source_ip.find(' ');
                if (space != std::string::npos) {
                    entry.source_ip = entry.source_ip.substr(0, space);
                }
            }

            auto user_pos = detail.find("user=");
            if (user_pos != std::string::npos) {
                entry.user = detail.substr(user_pos + 5);
                auto space = entry.user.find(' ');
                if (space != std::string::npos) {
                    entry.user = entry.user.substr(0, space);
                }
            }
        }
        return entry;
    }

    DetectionResult check_pattern(const AnomalyPattern& pattern) {
        DetectionResult result;
        result.anomaly_detected = false;
        result.pattern_name = pattern.name;
        result.description = pattern.description;

        if (pattern.matcher(entries_)) {
            auto recent = get_entries_in_window(pattern.window);
            result.anomaly_detected = true;
            result.matched_count = static_cast<int>(recent.size());
            result.matching_entries = recent;
            result.recommended_action = "Investigar imediatamente";
        }
        return result;
    }

    std::vector<LogEntry> get_entries_in_window(
        std::chrono::seconds window
    ) const {
        auto now = std::chrono::system_clock::now();
        std::vector<LogEntry> recent;
        for (const auto& e : entries_) {
            if ((now - e.timestamp) <= window) {
                recent.push_back(e);
            }
        }
        return recent;
    }

    void register_default_patterns() {
        patterns_.push_back({
            "BRUTE_FORCE",
            "Multiplos falhas de login do mesmo IP em curto periodo",
            10,
            std::chrono::seconds(60),
            [](const std::vector<LogEntry>& entries) {
                std::unordered_map<std::string, int> ip_failures;
                for (const auto& e : entries) {
                    if (e.is_failure) ip_failures[e.source_ip]++;
                }
                for (const auto& [ip, count] : ip_failures) {
                    if (count >= 10) return true;
                }
                return false;
            }
        });

        patterns_.push_back({
            "CREDENTIAL_STUFFING",
            "Multiplos usuarios com falha do mesmo IP",
            5,
            std::chrono::seconds(30),
            [](const std::vector<LogEntry>& entries) {
                std::unordered_map<std::string,
                    std::unordered_set<std::string>> ip_users;
                for (const auto& e : entries) {
                    if (e.is_failure) {
                        ip_users[e.source_ip].insert(e.user);
                    }
                }
                for (const auto& [ip, users] : ip_users) {
                    if (users.size() >= 5) return true;
                }
                return false;
            }
        });

        patterns_.push_back({
            "LATERAL_MOVEMENT",
            "Multiplos usuarios distintos logando do mesmo IP incomum",
            3,
            std::chrono::seconds(120),
            [](const std::vector<LogEntry>& entries) {
                std::unordered_map<std::string,
                    std::unordered_set<std::string>> ip_users;
                for (const auto& e : entries) {
                    if (!e.is_failure) {
                        ip_users[e.source_ip].insert(e.user);
                    }
                }
                for (const auto& [ip, users] : ip_users) {
                    if (users.size() >= 3) return true;
                }
                return false;
            }
        });

        patterns_.push_back({
            "ANOMALOUS_ACCESS_TIME",
            "Acesso fora do horario comercial",
            1,
            std::chrono::seconds(0),
            [](const std::vector<LogEntry>& entries) {
                for (const auto& e : entries) {
                    auto time_t_val = std::chrono::system_clock::to_time_t(
                        e.timestamp);
                    struct tm* tm_info = std::localtime(&time_t_val);
                    int hour = tm_info->tm_hour;
                    if (hour < 6 || hour > 22) return true;
                }
                return false;
            }
        });
    }
};

} // namespace security
```

---

## 4. Contenção

### 4.1 Contenção de Curto Prazo vs. Longo Prazo

A contenção é a fase mais delicada da resposta a incidentes. A pressão para restaurar a normalidade pode levar a decisões precipitadas que comprometem a investigação ou permitem que o atacante mantenha acesso.

**Contenção de curto prazo** (minutos a horas):
- Desconectar sistemas comprometidos da rede
- Bloquear IPs/-domínios maliciosos no firewall
- Desativar contas comprometidas
- Ativar regras de contenção pré-definidas

**Contenção de longo prazo** (horas a dias):
- Implementar segmentação de rede temporária
- Criar ambientes isolados para análise
- Implementar monitoramento reforçado
- Patchear vulnerabilidades exploradas

### 4.2 Técnicas de Isolamento de Rede

A contenção de rede deve ser cirúrgica — isolar o incidente sem derrubar serviços legítimos. A granularidade da contenção depende da arquitetura de rede e do escopo do incidente.

**Estratégias de isolamento:**

| Nível | Ação | Impacto | Risco |
|-------|------|---------|-------|
| Host | Desconectar máquina da rede | Apenas o host afetado | Perda de evidências voláteis |
| VLAN | Mover porta para VLAN de contenção | Todos na VLAN | Pode isolar hosts legítimos |
| Firewall | Bloquear tráfego específico | Selectivo | Atacante pode ter bypass |
| DNS | Sinkhole de domínios maliciosos | Selectivo | Pode afetar DNS legítimo |

### 4.3 Preservação de Evidências

A preservação de evidências é obrigatória tanto para fins de investigação interna quanto para processos legais. A cadeia de custódia (chain of custody) deve ser rigorosamente documentada.

**Hierarquia de volatilidade (coletar nesta ordem):**
1. Memória volátil (RAM, registros de CPU)
2. Dados de swap/paging
3. Logs em tempo real
4. Estado de rede (conexões, rotas, ARP)
5. Dados em disco
6. Logs persistentes
7. Snapshots de sistema

### 4.4 Framework C++ de Contenção

```cpp
// containment_framework.h - Framework de Contencao de Incidentes
#pragma once

#include <string>
#include <vector>
#include <functional>
#include <chrono>
#include <memory>
#include <fstream>
#include <sstream>
#include <unordered_map>
#include <mutex>
#include <thread>

namespace security {

enum class ContainmentAction : uint8_t {
    BLOCK_IP,
    ISOLATE_HOST,
    DISABLE_ACCOUNT,
    KILL_PROCESS,
    DISABLE_SERVICE,
    REDIRECT_DNS,
    MODIFY_FIREWALL,
    CREATE_SNAPSHOT
};

enum class ContainmentStatus : uint8_t {
    PENDING,
    IN_PROGRESS,
    COMPLETED,
    FAILED,
    ROLLED_BACK
};

struct ContainmentStep {
    ContainmentAction action;
    std::string target;
    std::string parameters;
    ContainmentStatus status = ContainmentStatus::PENDING;
    std::string result;
    std::chrono::system_clock::time_point executed_at;
};

struct ContainmentPlan {
    std::string incident_id;
    std::string description;
    std::vector<ContainmentStep> steps;
    bool requires_approval = true;
    std::string approved_by;
    std::chrono::system_clock::time_point approved_at;
};

struct EvidenceRecord {
    std::string incident_id;
    std::string type;
    std::string source;
    std::string hash_sha256;
    std::chrono::system_clock::time_point collected_at;
    std::string collected_by;
    std::string description;
};

class ContainmentFramework {
private:
    std::vector<ContainmentPlan> plans_;
    std::vector<EvidenceRecord> evidence_;
    mutable std::mutex mutex_;
    std::function<void(const std::string&)> logger_;

public:
    explicit ContainmentFramework(
        std::function<void(const std::string&)> logger = nullptr
    ) : logger_(logger ? logger : [](const std::string&) {}) {}

    ContainmentPlan create_plan(
        const std::string& incident_id,
        const std::string& description
    ) {
        std::lock_guard<std::mutex> lock(mutex_);
        ContainmentPlan plan;
        plan.incident_id = incident_id;
        plan.description = description;
        plans_.push_back(plan);
        log("Plano de contencao criado: " + incident_id);
        return plan;
    }

    void add_step(
        ContainmentPlan& plan,
        ContainmentAction action,
        const std::string& target,
        const std::string& params = ""
    ) {
        ContainmentStep step;
        step.action = action;
        step.target = target;
        step.parameters = params;
        plan.steps.push_back(step);
    }

    bool execute_plan(ContainmentPlan& plan) {
        log("Executando plano: " + plan.incident_id);

        for (auto& step : plan.steps) {
            step.status = ContainmentStatus::IN_PROGRESS;
            step.executed_at = std::chrono::system_clock::now();

            try {
                step.result = execute_step(step);
                step.status = ContainmentStatus::COMPLETED;
                log("  Passo concluido: " + step.target);
            } catch (const std::exception& e) {
                step.status = ContainmentStatus::FAILED;
                step.result = e.what();
                log("  FALHA no passo: " + std::string(e.what()));
                return false;
            }
        }

        log("Plano concluido com sucesso");
        return true;
    }

    void record_evidence(
        const std::string& incident_id,
        const std::string& type,
        const std::string& source,
        const std::string& description,
        const std::string& collected_by
    ) {
        std::lock_guard<std::mutex> lock(mutex_);
        EvidenceRecord record;
        record.incident_id = incident_id;
        record.type = type;
        record.source = source;
        record.description = description;
        record.collected_by = collected_by;
        record.collected_at = std::chrono::system_clock::now();
        evidence_.push_back(record);
        log("Evidencia registrada: " + type + " de " + source);
    }

    std::vector<EvidenceRecord> get_evidence(
        const std::string& incident_id
    ) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<EvidenceRecord> result;
        for (const auto& e : evidence_) {
            if (e.incident_id == incident_id) {
                result.push_back(e);
            }
        }
        return result;
    }

    std::string generate_chain_of_custody(
        const std::string& incident_id
    ) const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::ostringstream report;
        report << "=== CADEIA DE CUSTODIA ===" << "\n";
        report << "Incidente: " << incident_id << "\n";
        report << "Evidencias coletadas: " << evidence_.size() << "\n\n";

        for (size_t i = 0; i < evidence_.size(); ++i) {
            const auto& e = evidence_[i];
            if (e.incident_id != incident_id) continue;
            report << "Evidencia #" << (i + 1) << "\n";
            report << "  Tipo: " << e.type << "\n";
            report << "  Fonte: " << e.source << "\n";
            report << "  Descricao: " << e.description << "\n";
            report << "  Hash: " << e.hash_sha256 << "\n";
            report << "  Coletado por: " << e.collected_by << "\n";
            report << "  Data: " << std::chrono::system_clock::to_time_t(
                e.collected_at) << "\n\n";
        }
        report << "=========================" << "\n";
        return report.str();
    }

private:
    std::string execute_step(const ContainmentStep& step) {
        switch (step.action) {
            case ContainmentAction::BLOCK_IP:
                return "IP bloqueado: " + step.target;
            case ContainmentAction::ISOLATE_HOST:
                return "Host isolado: " + step.target;
            case ContainmentAction::DISABLE_ACCOUNT:
                return "Conta desativada: " + step.target;
            case ContainmentAction::KILL_PROCESS:
                return "Processo finalizado: " + step.target;
            case ContainmentAction::DISABLE_SERVICE:
                return "Servico desativado: " + step.target;
            case ContainmentAction::REDIRECT_DNS:
                return "DNS redirecionado: " + step.target;
            case ContainmentAction::MODIFY_FIREWALL:
                return "Firewall modificado: " + step.target;
            case ContainmentAction::CREATE_SNAPSHOT:
                return "Snapshot criado: " + step.target;
            default:
                return "Acao desconhecida";
        }
    }

    void log(const std::string& message) {
        logger_(message);
    }
};

} // namespace security
```

---

## 5. Erradicação

### 5.1 Análise de Causa Raiz

A erradicação não é apenas remover o malware — é entender como o atacante entrou, o que fez, e garantir que todas as portas de entrada sejam fechadas. Uma erradicação incompleta permite reinfecção.

**Técnicas de análise de causa raiz:**

1. **5 Porquês**: Perguntar "por quê?" repetidamente até chegar à causa fundamental
2. **Ishikawa (Fishbone)**: Mapear causas em categorias (Pessoas, Processos, Tecnologia, Ambiente)
3. **Fault Tree Analysis**: Árvore lógica de falhas encadeadas
4. **Timeline Analysis**: Reconstrução cronológica do ataque

### 5.2 Patching de Vulnerabilidades

O patching durante um incidente é uma operação de alto risco. O patch deve ser testado em ambiente de staging antes da produção, mas o tempo disponível é limitado.

**Estratégia de patching de emergência:**

1. Identificar a CVE exata e o vetor de ataque
2. Verificar se o vendor publicou patch
3. Se não há patch: implementar mitigação (WAF rules, config changes)
4. Testar o patch em staging com carga representativa
5. Aplicar em produção com rollback planejado
6. Verificar integridade pós-patch

### 5.3 Hardening de Sistemas

Após a erradicação, os sistemas devem ser fortalecidos para prevenir reincidência:

- Revisar e minimizar permissões de conta
- Atualizar todas as dependências e bibliotecas
- Implementar segmentação de rede adicional
- Ativar logging detalhado em todos os pontos críticos
- Revisar regras de firewall e WAF

### 5.4 Scanner de Vulnerabilidades C++

```cpp
// vulnerability_scanner.h - Scanner de Vulnerabilidades
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <algorithm>
#include <regex>
#include <ctime>

namespace security {

enum class VulnSeverity : uint8_t {
    CRITICAL = 4,
    HIGH = 3,
    MEDIUM = 2,
    LOW = 1,
    INFO = 0
};

struct Vulnerability {
    std::string cve_id;
    std::string title;
    VulnSeverity severity;
    float cvss_score;
    std::string affected_component;
    std::string affected_versions;
    std::string fixed_version;
    std::string description;
    std::string mitigation;
    bool actively_exploited = false;
};

struct ScanResult {
    std::string target;
    std::string scan_time;
    int total_vulns = 0;
    int critical = 0;
    int high = 0;
    int medium = 0;
    int low = 0;
    std::vector<Vulnerability> vulnerabilities;
};

class VulnerabilityScanner {
private:
    std::vector<Vulnerability> known_vulns_;
    std::unordered_map<std::string, std::string> package_versions_;

public:
    void load_vulnerability_database(const std::string& db_path) {
        std::ifstream file(db_path);
        if (!file.is_open()) return;

        std::string line;
        Vulnerability current;
        while (std::getline(file, line)) {
            if (line.find("CVE:") == 0) {
                if (!current.cve_id.empty()) {
                    known_vulns_.push_back(current);
                }
                current = Vulnerability{};
                current.cve_id = line.substr(4);
            } else if (line.find("TITLE:") == 0) {
                current.title = line.substr(6);
            } else if (line.find("CVSS:") == 0) {
                current.cvss_score = std::stof(line.substr(5));
            } else if (line.find("SEVERITY:") == 0) {
                std::string sev = line.substr(9);
                if (sev == "CRITICAL") current.severity = VulnSeverity::CRITICAL;
                else if (sev == "HIGH") current.severity = VulnSeverity::HIGH;
                else if (sev == "MEDIUM") current.severity = VulnSeverity::MEDIUM;
                else current.severity = VulnSeverity::LOW;
            } else if (line.find("EXPLOITED:") == 0) {
                current.actively_exploited = (line.substr(10) == "true");
            }
        }
        if (!current.cve_id.empty()) {
            known_vulns_.push_back(current);
        }
    }

    void register_package(const std::string& name, const std::string& version) {
        package_versions_[name] = version;
    }

    ScanResult scan() {
        ScanResult result;
        result.scan_time = current_timestamp();
        result.target = "local_system";

        for (const auto& vuln : known_vulns_) {
            if (is_affected(vuln)) {
                result.vulnerabilities.push_back(vuln);
                result.total_vulns++;
                switch (vuln.severity) {
                    case VulnSeverity::CRITICAL: result.critical++; break;
                    case VulnSeverity::HIGH: result.high++; break;
                    case VulnSeverity::MEDIUM: result.medium++; break;
                    default: result.low++; break;
                }
            }
        }

        std::sort(result.vulnerabilities.begin(),
            result.vulnerabilities.end(),
            [](const Vulnerability& a, const Vulnerability& b) {
                return a.cvss_score > b.cvss_score;
            });

        return result;
    }

    static std::string generate_report(const ScanResult& result) {
        std::ostringstream report;
        report << "=== RELATORIO DE VULNERABILIDADES ===" << "\n";
        report << "Alvo: " << result.target << "\n";
        report << "Data: " << result.scan_time << "\n";
        report << "Total: " << result.total_vulns << " vulnerabilidades\n";
        report << "  CRITICO: " << result.critical << "\n";
        report << "  ALTO: " << result.high << "\n";
        report << "  MEDIO: " << result.medium << "\n";
        report << "  BAIXO: " << result.low << "\n\n";

        for (const auto& v : result.vulnerabilities) {
            report << "----------------------------------------\n";
            report << "CVE: " << v.cve_id << "\n";
            report << "Titulo: " << v.title << "\n";
            report << "CVSS: " << v.cvss_score << "\n";
            report << "Explorado ativamente: "
                   << (v.actively_exploited ? "SIM" : "NAO") << "\n";
            report << "Mitigacao: " << v.mitigation << "\n\n";
        }

        report << "========================================" << "\n";
        return report.str();
    }

private:
    bool is_affected(const Vulnerability& vuln) const {
        return package_versions_.count(vuln.affected_component) > 0;
    }

    static std::string current_timestamp() {
        auto now = std::time(nullptr);
        char buf[64];
        std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ",
            std::gmtime(&now));
        return std::string(buf);
    }
};

} // namespace security
```

---

## 6. Recuperação

### 6.1 Procedimentos de Restauração de Sistemas

A recuperação é a fase onde os sistemas comprometidos são restaurados a um estado funcional e seguro. É também a fase com maior risco de reinfecção se a erradicação não foi completa.

**Checklist de restauração:**

1. Verificar que a causa raiz foi completamente removida
2. Restaurar a partir de backups verificados (não de backups potencialmente comprometidos)
3. Aplicar todas as correções de segurança antes de restaurar ao ambiente
4. Validar integridade dos dados restaurados
5. Monitorar intensamente por 48-72 horas após a restauração

### 6.2 Verificação de Integridade

A verificação de integridade é essencial para garantir que os sistemas restaurados não contenham artefatos do atacante ou corrupção.

**Métodos de verificação:**

| Método | O que verifica | Ferramenta |
|--------|---------------|------------|
| Hash comparison | Integridade de binários | sha256sum, GPG signatures |
| File integrity monitoring | Alterações em arquivos críticos | AIDE, Tripwire, OSSEC |
| Configuration drift | Alterações em configs | Ansible, Puppet diff |
| Network baseline | Tráfego anômalo | Zeek, Suricata |
| Process integrity | Processos suspeitos | EDR, YARA |

### 6.3 Monitoramento Durante Recuperação

O monitoramento pós-recuperação deve ser mais intensivo que o normal. O atacante pode ter deixado backdoors que só se ativam após a restauração.

**Regras de monitoramento pós-recuperação:**
- Alertas de severidade baixa também devem ser investigados
- Qualquer login de conta de serviço deve ser verificado
- Tráfego de rede para IPs desconhecidos deve ser bloqueado imediatamente
- Logs devem ser preservados por no mínimo 90 dias

### 6.4 Verificador de Integridade do Sistema C++

```cpp
// system_integrity_checker.h - Verificador de Integridade do Sistema
#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <fstream>
#include <sstream>
#include <filesystem>
#include <openssl/sha.h>
#include <openssl/evp.h>

namespace security {

struct FileIntegrityRecord {
    std::string filepath;
    std::string sha256_hash;
    std::chrono::system_clock::time_point last_modified;
    std::uintmax_t file_size;
    bool exists = true;
};

struct IntegrityCheckResult {
    std::string check_time;
    int total_files = 0;
    int unchanged = 0;
    int modified = 0;
    int missing = 0;
    int new_files = 0;
    std::vector<std::string> warnings;
    std::vector<FileIntegrityRecord> modified_files;
    std::vector<std::string> missing_files;
    std::vector<std::string> new_files;
    bool passed = true;
};

class SystemIntegrityChecker {
private:
    std::unordered_map<std::string, FileIntegrityRecord> baseline_;
    std::vector<std::string> watch_paths_;

public:
    void add_watch_path(const std::string& path) {
        watch_paths_.push_back(path);
    }

    void create_baseline() {
        baseline_.clear();
        for (const auto& watch_path : watch_paths_) {
            scan_directory(watch_path);
        }
    }

    void save_baseline(const std::string& filepath) {
        std::ofstream file(filepath);
        for (const auto& [path, record] : baseline_) {
            file << path << "|"
                 << record.sha256_hash << "|"
                 << record.file_size << "|"
                 << std::chrono::system_clock::to_time_t(
                    record.last_modified) << "\n";
        }
    }

    void load_baseline(const std::string& filepath) {
        std::ifstream file(filepath);
        std::string line;
        while (std::getline(file, line)) {
            std::istringstream iss(line);
            FileIntegrityRecord record;
            std::string time_str;

            if (std::getline(iss, record.filepath, '|') &&
                std::getline(iss, record.sha256_hash, '|') &&
                std::getline(iss, time_str, '|')) {
                record.file_size = std::stoull(time_str);
                baseline_[record.filepath] = record;
            }
        }
    }

    IntegrityCheckResult check_integrity() {
        IntegrityCheckResult result;
        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);
        struct tm* tm_info = std::localtime(&time_t_now);
        char time_buf[64];
        std::strftime(time_buf, sizeof(time_buf), "%Y-%m-%d %H:%M:%S",
            tm_info);
        result.check_time = time_buf;

        for (const auto& [path, baseline_record] : baseline_) {
            result.total_files++;

            if (!std::filesystem::exists(path)) {
                result.missing++;
                result.missing_files.push_back(path);
                result.warnings.append(
                    "ARQUIVO AUSENTE: " + path);
                continue;
            }

            std::string current_hash = compute_sha256(path);
            if (current_hash != baseline_record.sha256_hash) {
                result.modified++;
                FileIntegrityRecord modified = baseline_record;
                modified.sha256_hash = current_hash;
                result.modified_files.push_back(modified);
                result.warnings.push_back(
                    "ARQUIVO MODIFICADO: " + path);
            } else {
                result.unchanged++;
            }
        }

        for (const auto& watch_path : watch_paths_) {
            check_new_files(watch_path, result);
        }

        result.passed = (result.modified == 0 &&
                         result.missing == 0);
        return result;
    }

    static std::string generate_report(
        const IntegrityCheckResult& result
    ) {
        std::ostringstream report;
        report << "=== VERIFICACAO DE INTEGRIDADE ===" << "\n";
        report << "Data: " << result.check_time << "\n";
        report << "Total de arquivos: " << result.total_files << "\n";
        report << "Inalterados: " << result.unchanged << "\n";
        report << "Modificados: " << result.modified << "\n";
        report << "Ausentes: " << result.missing << "\n";
        report << "Novos: " << result.new_files << "\n";
        report << "Resultado: "
               << (result.passed ? "APROVADO" : "FALHOU") << "\n\n";

        if (!result.modified_files.empty()) {
            report << "Arquivos modificados:" << "\n";
            for (const auto& f : result.modified_files) {
                report << "  " << f.filepath << "\n";
            }
        }

        if (!result.missing_files.empty()) {
            report << "Arquivos ausentes:" << "\n";
            for (const auto& f : result.missing_files) {
                report << "  " << f << "\n";
            }
        }

        report << "====================================" << "\n";
        return report.str();
    }

private:
    void scan_directory(const std::string& path) {
        try {
            for (const auto& entry :
                 std::filesystem::recursive_directory_iterator(path)) {
                if (entry.is_regular_file()) {
                    std::string filepath = entry.path().string();
                    FileIntegrityRecord record;
                    record.filepath = filepath;
                    record.sha256_hash = compute_sha256(filepath);
                    record.last_modified =
                        std::filesystem::last_write_time(entry.path());
                    record.file_size = entry.file_size();
                    baseline_[filepath] = record;
                }
            }
        } catch (const std::exception&) {
            // Skip inaccessible paths
        }
    }

    void check_new_files(
        const std::string& path,
        IntegrityCheckResult& result
    ) {
        try {
            for (const auto& entry :
                 std::filesystem::recursive_directory_iterator(path)) {
                if (entry.is_regular_file()) {
                    std::string filepath = entry.path().string();
                    if (baseline_.find(filepath) == baseline_.end()) {
                        result.new_files++;
                        result.new_files_list().push_back(filepath);
                        result.warnings.push_back(
                            "NOVO ARQUIVO: " + filepath);
                    }
                }
            }
        } catch (const std::exception&) {
            // Skip inaccessible paths
        }
    }

    static std::string compute_sha256(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file.is_open()) return "";

        EVP_MD_CTX* ctx = EVP_MD_CTX_new();
        if (!ctx) return "";

        EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);

        char buffer[8192];
        while (file.read(buffer, sizeof(buffer))) {
            EVP_DigestUpdate(ctx, buffer, file.gcount());
        }
        EVP_DigestUpdate(ctx, buffer, file.gcount());

        unsigned char hash[EVP_MAX_MD_SIZE];
        unsigned int length = 0;
        EVP_DigestFinal_ex(ctx, hash, &length);
        EVP_MD_CTX_free(ctx);

        std::ostringstream oss;
        for (unsigned int i = 0; i < length; ++i) {
            oss << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<int>(hash[i]);
        }
        return oss.str();
    }
};

} // namespace security
```

---

## 7. Forensic Analysis de Binários

### 7.1 Fundamentos de Análise de Binários

A análise forense de binários é essencial para compreender malware, exploits e persistência deixada por atacantes. No contexto de C++, isso inclui análise de binários ELF/PE, libraries compartilhadas e objetos de kernel.

**Técnicas fundamentais:**

| Técnica | O que revela | Ferramentas |
|---------|-------------|-------------|
| Static analysis | Strings, imports, estrutura | strings, readelf, objdump |
| Dynamic analysis | Comportamento em runtime | strace, ltrace, gdb |
| Disassembly | Lógica de programa, hooks | Ghidra, IDA Pro, radare2 |
| Memory forensics | Estado da memória, processos | Volatility, Rekall |
| YARA matching | Assinaturas de malware | yara, yara-rules |

### 7.2 Forensic de Memória

A análise de memória volátil é a forma mais confiável de detectar malware que não toca em disco. Técnicas como fileless malware e living-off-the-land dependem de operar inteiramente em memória.

**Dados recoveráveis de memória:**
- Processos ocultos (rootkits que removem da tabela de processos)
- Chaves de criptografia em uso
- Conexões de rede ativas
- Shellcodes e payloads em memória
- Dados de credential caches

### 7.3 Forensic de Logs

A análise forense de logs vai além da leitura superficial. Reconstituir a cronologia de um ataque requer correlacionar logs de múltiplas fontes e identificar gaps que indicam apagamento de logs pelo atacante.

### 7.4 Ferramentas C++ para Análise Forense

```cpp
// forensic_analyzer.h - Analisador Forense de Binarios
#pragma once

#include <string>
#include <vector>
#include <fstream>
#include <sstream>
#include <cstring>
#include <cstdint>
#include <algorithm>
#include <unordered_map>

namespace security {

struct BinarySection {
    std::string name;
    uint64_t virtual_address;
    uint64_t virtual_size;
    uint64_t file_offset;
    uint32_t characteristics;
    std::string type;
};

struct ImportedFunction {
    std::string library;
    std::string function_name;
    uint64_t address;
};

struct ForensicFinding {
    std::string category;
    std::string severity;
    std::string description;
    uint64_t offset;
    std::string evidence;
};

class ForensicAnalyzer {
private:
    std::vector<uint8_t> binary_data_;
    std::vector<BinarySection> sections_;
    std::vector<ImportedFunction> imports_;
    std::vector<ForensicFinding> findings_;

public:
    bool load_binary(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary | std::ios::ate);
        if (!file.is_open()) return false;

        std::streamsize size = file.tellg();
        file.seekg(0, std::ios::beg);

        binary_data_.resize(static_cast<size_t>(size));
        if (!file.read(reinterpret_cast<char*>(binary_data_.data()),
                       size)) {
            return false;
        }

        parse_pe_header();
        return true;
    }

    std::vector<ForensicFinding> analyze() {
        findings_.clear();
        check_suspicious_strings();
        check_packing_indicators();
        check_suspicious_imports();
        check_entropy_anomalies();
        check_shellcode_patterns();
        return findings_;
    }

    std::vector<std::string> extract_strings(size_t min_length = 4) {
        std::vector<std::string> result;
        std::string current;

        for (uint8_t byte : binary_data_) {
            if (byte >= 0x20 && byte <= 0x7E) {
                current += static_cast<char>(byte);
            } else {
                if (current.length() >= min_length) {
                    result.push_back(current);
                }
                current.clear();
            }
        }
        return result;
    }

    double calculate_entropy(
        uint64_t offset, size_t length
    ) const {
        if (offset + length > binary_data_.size()) return 0.0;

        std::unordered_map<uint8_t, int> freq;
        for (size_t i = offset; i < offset + length; ++i) {
            freq[binary_data_[i]]++;
        }

        double entropy = 0.0;
        double size = static_cast<double>(length);
        for (const auto& [byte, count] : freq) {
            double p = static_cast<double>(count) / size;
            if (p > 0) {
                entropy -= p * std::log2(p);
            }
        }
        return entropy;
    }

    static std::string generate_report(
        const std::vector<ForensicFinding>& findings
    ) {
        std::ostringstream report;
        report << "=== RELATORIO FORENSE ===" << "\n";
        report << "Total de achados: " << findings.size() << "\n\n";

        int critical = 0, high = 0, medium = 0;
        for (const auto& f : findings) {
            if (f.severity == "CRITICAL") critical++;
            else if (f.severity == "HIGH") high++;
            else if (f.severity == "MEDIUM") medium++;
        }

        report << "Criticos: " << critical << "\n";
        report << "Altos: " << high << "\n";
        report << "Medios: " << medium << "\n\n";

        for (size_t i = 0; i < findings.size(); ++i) {
            const auto& f = findings[i];
            report << "Achado #" << (i + 1) << "\n";
            report << "  Categoria: " << f.category << "\n";
            report << "  Severidade: " << f.severity << "\n";
            report << "  Descricao: " << f.description << "\n";
            report << "  Offset: 0x" << std::hex << f.offset << "\n";
            report << "  Evidencia: " << f.evidence << "\n\n";
        }

        report << "=========================" << "\n";
        return report.str();
    }

private:
    void parse_pe_header() {
        if (binary_data_.size() < 64) return;
        if (binary_data_[0] != 'M' || binary_data_[1] != 'Z') return;

        uint32_t pe_offset = *reinterpret_cast<const uint32_t*>(
            &binary_data_[60]);
        if (pe_offset + 24 >= binary_data_.size()) return;

        uint16_t num_sections = *reinterpret_cast<const uint16_t*>(
            &binary_data_[pe_offset + 6]);
        uint16_t optional_header_size = *reinterpret_cast<const uint16_t*>(
            &binary_data_[pe_offset + 20]);

        uint64_t section_start = pe_offset + 24 + optional_header_size;
        for (uint16_t i = 0; i < num_sections; ++i) {
            uint64_t offset = section_start + (i * 40);
            if (offset + 40 > binary_data_.size()) break;

            BinarySection section;
            char name_buf[9] = {};
            std::memcpy(name_buf, &binary_data_[offset], 8);
            section.name = std::string(name_buf);
            section.virtual_size = *reinterpret_cast<const uint32_t*>(
                &binary_data_[offset + 8]);
            section.virtual_address = *reinterpret_cast<const uint32_t*>(
                &binary_data_[offset + 12]);
            section.file_offset = *reinterpret_cast<const uint32_t*>(
                &binary_data_[offset + 20]);
            section.characteristics = *reinterpret_cast<const uint32_t*>(
                &binary_data_[offset + 36]);
            sections_.push_back(section);
        }
    }

    void check_suspicious_strings() {
        auto strings = extract_strings();
        std::vector<std::string> suspicious_patterns = {
            "cmd.exe", "/bin/sh", "powershell",
            "wget ", "curl ", "nc -", "netcat",
            "password", "passwd", "shadow",
            "regedit", "HKEY_", "SYSTEM\\",
            "SELECT * FROM", "DROP TABLE",
            "base64", "eval(", "exec(",
            "\\\\.", "\\\\pipe\\"
        };

        for (const auto& str : strings) {
            for (const auto& pattern : suspicious_patterns) {
                if (str.find(pattern) != std::string::npos) {
                    findings_.push_back({
                        "SUSPICIOUS_STRING",
                        "MEDIUM",
                        "String suspeita encontrada: " + pattern,
                        0,
                        str
                    });
                    break;
                }
            }
        }
    }

    void check_packing_indicators() {
        double overall_entropy = calculate_entropy(
            0, binary_data_.size());
        if (overall_entropy > 7.5) {
            findings_.push_back({
                "PACKING",
                "HIGH",
                "Entropia alta indica possivel packing/criptografia",
                0,
                "Entropia: " + std::to_string(overall_entropy)
            });
        }

        std::vector<std::string> packer_signatures = {
            "UPX!", "ASPack", "PECompact",
            "Themida", "VMProtect"
        };

        auto strings = extract_strings(3);
        for (const auto& str : strings) {
            for (const auto& packer : packer_signatures) {
                if (str.find(packer) != std::string::npos) {
                    findings_.push_back({
                        "PACKER_DETECTED",
                        "HIGH",
                        "Packer detectado: " + packer,
                        0,
                        str
                    });
                }
            }
        }
    }

    void check_suspicious_imports() {
        std::vector<std::string> suspicious_apis = {
            "VirtualAlloc", "VirtualProtect",
            "WriteProcessMemory", "CreateRemoteThread",
            "NtUnmapViewOfSection", "SetWindowsHookEx",
            "GetProcAddress", "LoadLibrary",
            "WinExec", "ShellExecute",
            "CreateService", "RegSetValue"
        };

        for (const auto& api : suspicious_apis) {
            auto strings = extract_strings();
            for (const auto& str : strings) {
                if (str.find(api) != std::string::npos) {
                    findings_.push_back({
                        "SUSPICIOUS_API",
                        "MEDIUM",
                        "API potencialmente abusiva: " + api,
                        0,
                        str
                    });
                }
            }
        }
    }

    void check_entropy_anomalies() {
        size_t chunk_size = 4096;
        for (size_t offset = 0;
             offset < binary_data_.size();
             offset += chunk_size) {
            size_t length = std::min(chunk_size,
                binary_data_.size() - offset);
            double entropy = calculate_entropy(offset, length);

            if (entropy > 7.8) {
                findings_.push_back({
                    "HIGH_ENTROPY_REGION",
                    "MEDIUM",
                    "Regiao de alta entropia detectada",
                    offset,
                    "Entropia: " + std::to_string(entropy)
                });
            }
        }
    }

    void check_shellcode_patterns() {
        std::vector<std::vector<uint8_t>> shellcode_patterns = {
            {0x31, 0xc0, 0x50, 0x68},
            {0xfc, 0x48, 0x83, 0xe4},
            {0x64, 0x8b, 0x64, 0x24},
            {0xeb, 0xff, 0x5d, 0xc3}
        };

        for (const auto& pattern : shellcode_patterns) {
            for (size_t i = 0;
                 i + pattern.size() <= binary_data_.size();
                 ++i) {
                if (std::memcmp(&binary_data_[i], pattern.data(),
                                pattern.size()) == 0) {
                    findings_.push_back({
                        "SHELLCODE_PATTERN",
                        "CRITICAL",
                        "Possivel shellcode detectado",
                        i,
                        "Bytes: " + bytes_to_hex(
                            &binary_data_[i], pattern.size())
                    });
                }
            }
        }
    }

    static std::string bytes_to_hex(
        const uint8_t* data, size_t length
    ) {
        std::ostringstream oss;
        for (size_t i = 0; i < length; ++i) {
            oss << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<int>(data[i]) << " ";
        }
        return oss.str();
    }
};

} // namespace security
```

---

## 8. Disclosure Responsável

### 8.1 Disclosure Coordenado de Vulnerabilidades

O disclosure coordenado é o processo de reportar vulnerabilidades de forma controlada, dando tempo ao vendor para desenvolver e distribuir um patch antes da divulgação pública. É um equilíbrio delicado entre transparência e proteção dos usuários.

**Princípios do disclosure coordenado:**

1. **Reportar diretamente ao vendor** (ou ao CERT nacional) primeiro
2. **Aguardar razoavelmente** (geralmente 90 dias) para o patch
3. **Não divulgar detalhes técnicos** antes do patch estar disponível
4. **Coordenar a data de divulgação** com o vendor
5. **Incluir creditos** ao pesquisador que descobriu a vulnerabilidade

### 8.2 Processo de Atribuição de CVE

O Common Vulnerabilities and Exposures (CVE) é o padrão para identificar vulnerabilidades de forma única. O processo de atribuição:

1. **Reporte ao CVE Numbering Authority (CNA)**: Vendor ou MITRE
2. **Análise e validação**: A CNA confirma a vulnerabilidade
3. **Atribuição do CVE-ID**: Formato CVE-YYYY-NNNNN
4. **Publicação na lista CVE**: Após o vendor liberar o patch
5. **Atualização do NVD**: National Vulnerability Database recebe os dados

### 8.3 Programas de Bug Bounty

Programas de bug bounty incentivam pesquisadores independentes a encontrar e reportar vulnerabilidades de forma responsável. A maioria das grandes empresas mantém programas ativos.

**Elementos de um programa de bug bounty eficaz:**

| Elemento | Descrição |
|----------|-----------|
| Escopo | Quais sistemas e vulnerabilidades são cobertos |
| Regras | O que é permitido e o que não é |
| Recompensas | Valores por severidade (P1 a P4) |
| Processo | Como reportar, SLA de resposta |
| Safe Harbor | Proteção legal para pesquisadores |
| Divulgação | Política de creditação |

### 8.4 Template Completo de Disclosure

```
=== TEMPLATE DE DISCLOSURE DE VULNERABILIDADE ===

DATA: [data]
DE: [nome do pesquisador / equipe]
PARA: [vendor / CERT]

--- RESUMO ---
ID da Vulnerabilidade: [CVE-ID ou ID interno]
Componente Afetado: [nome do componente]
Versoes Afetadas: [lista de versoes]
Severidade CVSS v3.1: [score] ([classificacao])
Vetor de Ataque: [network/local/adjacent/physical]

--- DESCRICAO TECNICA ---
[Descricao detalhada da vulnerabilidade, incluindo o vetor
 de ataque, a causa raiz e o impacto potencial.]

--- PROVA DE CONCEITO ---
[Steps para reproduzir, incluindo ambiente, ferramentas,
 e codigos de exemplo. Nao incluir exploits completos
 ate o patch estar disponivel.]

--- IMPACTO ---
[Descricao do impacto potencial, incluindo dados que podem
 ser comprometidos, sistemas afetados, e riscos associados.]

--- MITIGACAO ---
[Mitigacao temporaria ate o patch estar disponivel.]

--- TIMELINE ---
DD/MM/AAAA: Vulnerabilidade descoberta
DD/MM/AAAA: Vendor notificado
DD/MM/AAAA: Vendor confirma recebimento
DD/MM/AAAA: Vendor confirma vulnerabilidade
DD/MM/AAAA: Patch disponivel (meta)
DD/MM/AAAA: Divulgacao publica (90 dias apos reporte)

--- CREDITOS ---
[Nome do pesquisador e afiliacao, com permissao.]

===============================================
```

---

## 9. Post-Mortem sem Culpa

### 9.1 Estrutura de Post-Mortem Blameless

O post-mortem blameless é uma prática fundamental para aprendizado organizacional. O objetivo NUNCA é encontrar culpados — é entender o que aconteceu, por quê, e como prevenir que aconteça novamente.

**Regras fundamentais do blameless post-mortem:**

1. **Focar no sistema, não nas pessoas**: "O deploy automático não tinha rollback" em vez de "João esqueceu de testar"
2. **Assumir boa intenção**: Todos estavam fazendo o melhor que podiam com a informação disponível
3. **Identificar fatores sistêmicos**: Por que o processo permitiu que isso acontecesse?
4. **Ação corretiva > culpa**: Cada achado deve gerar uma ação concreta

### 9.2 Técnicas de Análise de Causa Raiz

**5 Porquês:**

```
Problema: O sistema ficou indisponível por 4 horas
1. Por quê? → O banco de dados entrou em modo de leitura apenas
2. Por quê? → O disco ficou cheio
3. Por quê? → Os logs não estavam sendo rotacionados
4. Por quê? → O cron job de rotação foi removido no último deploy
5. Por quê? → O pipeline de CI/CD não verifica integridade do cron
   RAIZ: Falta de verificação de integridade na pipeline de deploy
```

**Fishbone (Ishikawa):**

| Categoria | Fator Contribuinte |
|-----------|-------------------|
| Pessoas | Treinamento insuficiente em resposta a incidentes |
| Processo | Sem runbook para o tipo específico de incidente |
| Tecnologia | Monitoramento não cobre o tipo de falha |
| Ambiente | Pressão para resolver rapidamente sem follow-up |

### 9.3 Rastreamento de Itens de Ação

Cada achado do post-mortem deve gerar um item de ação com:

- **Dono** (quem é responsável)
- **Deadline** (quando deve ser concluído)
- **Prioridade** (P1 a P4)
- **Status** (Não iniciado, Em progresso, Concluído)
- **Métrica de sucesso** (como saberemos que funcionou)

### 9.4 Template Completo de Post-Mortem

```yaml
# Post-Mortem: [Nome do Incidente]
# Data: [data]
# Condutor: [nome]
# Participantes: [lista]
# Severidade: [P1/P2/P3/P4]

---
## Resumo Executivo
[2-3 frases sobre o que aconteceu, impacto, e duração]

## Timeline
| Horario | Evento |
|---------|--------|
| HH:MM | [Evento 1] |
| HH:MM | [Evento 2] |
| ... | ... |

## Impacto
- Duracao total: [X horas/minutos]
- Usuarios afetados: [numero]
- Dados comprometidos: [sim/nao, escopo]
- Perda financeira estimada: [valor]
- Impacto regulatorio: [sim/nao, detalhes]

## Achados

### O que deu certo
1. [Item 1]
2. [Item 2]

### O que deu errado
1. [Item 1]
2. [Item 2]

### O que poderia ter sido pior
1. [Item 1]
2. [Item 2]

## Analise de Causa Raiz
[5 Whys, Fishbone, ou Fault Tree]

## Itens de Acao

| # | Descricao | Dono | Deadline | Prioridade | Status |
|---|-----------|------|----------|------------|--------|
| 1 | [Acao] | [Nome] | [Data] | [P1-P4] | [Status] |
| 2 | [Acao] | [Nome] | [Data] | [P1-P4] | [Status] |

## Lições Aprendidas
1. [Licao 1]
2. [Licao 2]

## Proximo Post-Mortem
- Data: [data]
- Condutor: [nome]
```

---

## 10. Patching Strategies

### 10.1 Desenvolvimento de Hotfix

Um hotfix é uma correção de emergência que deve ser aplicada rapidamente, mas sem comprometer a estabilidade. O equilíbrio entre velocidade e segurança é crucial.

**Processo de hotfix:**

1. Reproduzir o bug em ambiente controlado
2. Implementar a correção com testes mínimos mas críticos
3. Testar em staging com cenários representativos
4. Deploy com monitoramento reforçado
5. Rollback plan documentado e testado

### 10.2 Procedimentos de Rollback

O rollback deve ser planejado ANTES do deploy, não depois. Um rollback testado é a diferença entre um incidente menor e uma catástrofe.

**Estratégias de rollback:**

| Estratégia | Velocidade | Risco | Cenário Ideal |
|-----------|-----------|-------|---------------|
| Blue-Green | Instantâneo | Muito baixo | Infraestrutura duplicada |
| Canary | Minutos | Baixo | Deploy gradual |
| Database migration rollback | Horas | Alto | Mudanças de schema |
| Feature flag disable | Instantâneo | Muito baixo | Feature flags ativos |

### 10.3 Canary Deployments

O deploy canário distribui uma atualização para uma pequena fração dos usuários antes do rollout completo. É essencial para detectar problemas antes que afetem toda a base.

**Métricas de monitoramento durante canary:**

1. Taxa de erro (deve ser igual ou menor que baseline)
2. Latência P95/P99 (não deve aumentar significativamente)
3. Taxa de crash (deve ser zero)
4. Comportamento de negócio (conversão, retenão)

### 10.4 Padrões de Hot-Patching em C++

```cpp
// hot_patch_manager.h - Gerenciador de Hot-Patching
#pragma once

#include <string>
#include <vector>
#include <functional>
#include <unordered_map>
#include <mutex>
#include <atomic>
#include <memory>

namespace security {

struct Patch {
    std::string id;
    std::string description;
    std::string target_function;
    std::string patch_binary;
    std::chrono::system_clock::time_point applied_at;
    bool active = true;
};

struct RollbackPoint {
    std::string patch_id;
    std::string original_bytes;
    uint64_t address;
    size_t size;
};

class HotPatchManager {
private:
    std::vector<Patch> applied_patches_;
    std::vector<RollbackPoint> rollback_points_;
    mutable std::mutex mutex_;
    std::atomic<bool> rollback_mode_{false};

public:
    bool apply_patch(
        const std::string& patch_id,
        uint64_t target_address,
        const std::string& new_bytes,
        const std::string& description
    ) {
        std::lock_guard<std::mutex> lock(mutex_);

        if (rollback_mode_.load()) {
            return false;
        }

        RollbackPoint rollback;
        rollback.patch_id = patch_id;
        rollback.address = target_address;
        rollback.size = new_bytes.size();
        rollback_points_.push_back(rollback);

        Patch patch;
        patch.id = patch_id;
        patch.description = description;
        patch.applied_at = std::chrono::system_clock::now();
        patch.active = true;
        applied_patches_.push_back(patch);

        return true;
    }

    bool rollback_patch(const std::string& patch_id) {
        std::lock_guard<std::mutex> lock(mutex_);

        for (auto it = rollback_points_.begin();
             it != rollback_points_.end(); ++it) {
            if (it->patch_id == patch_id) {
                rollback_points_.erase(it);
                break;
            }
        }

        for (auto& patch : applied_patches_) {
            if (patch.id == patch_id) {
                patch.active = false;
                return true;
            }
        }
        return false;
    }

    bool rollback_all() {
        std::lock_guard<std::mutex> lock(mutex_);
        rollback_mode_.store(true);

        for (auto& patch : applied_patches_) {
            patch.active = false;
        }
        rollback_points_.clear();
        return true;
    }

    std::vector<Patch> get_active_patches() const {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<Patch> active;
        for (const auto& p : applied_patches_) {
            if (p.active) active.push_back(p);
        }
        return active;
    }

    bool has_active_patches() const {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& p : applied_patches_) {
            if (p.active) return true;
        }
        return false;
    }
};

} // namespace security
```

---

## 11. Exemplo Completo: Runbook de Resposta a Incidente

Este runbook é um guia operacional completo para resposta a um incidente de segurança de nível alto ou crítico. Cada seção deve ser executada sequencialmente, com documentação rigorosa de cada passo.

```yaml
# ============================================================
# RUNBOOK: Resposta a Incidente de Seguranca
# Versao: 2.0 | Ultima atualizacao: 2024-01-15
# Aprovado por: CISO
# ============================================================

## FASE 1: DETECCAO E TRIAGEM (0-15 minutos)

### Passo 1.1: Confirmar o alerta
- [ ] Verificar se o alerta nao e falso positivo
- [ ] Confirmar com a fonte do alerta (SIEM, EDR, usuario)
- [ ] Registrar horario exato de deteccao: __________

### Passo 1.2: Classificar o incidente
- [ ] Identificar categoria (data breach, malware, ransomware, etc.)
- [ ] Avaliar severidade usando a matriz de classificacao
- [ ] Atribuir ID unico ao incidente: INC-________

### Passo 1.3: Ativar a equipe
- [ ] Notificar Incident Commander: __________
- [ ] Notificar Security Lead: __________
- [ ] Criar canal de comunicacao dedicado (#incident-INC-XXXX)
- [ ] Iniciar cronometro de resposta

### Passo 1.4: Documentacao inicial
- [ ] Criar ticket no sistema de incidentes
- [ ] Registrar todas as informacoes iniciais
- [ ] Fornecer primeira comunicacao de status

---

## FASE 2: CONTENCAO (15-60 minutos)

### Passo 2.1: Contencao imediata
- [ ] Identificar o escopo do incidente
- [ ] Decidir estrategia de contencao:
  - [ ] Desconectar sistemas afetados da rede
  - [ ] Bloquear IPs/domains maliciosos
  - [ ] Desativar contas comprometidas
  - [ ] Ativar regras de firewall de emergencia

### Passo 2.2: Preservacao de evidencias
- [ ] Coletar dados volateis (RAM, processos, conexoes)
- [ ] Criar snapshot dos sistemas afetados
- [ ] Preservar logs (SIEM, firewall, application)
- [ ] Documentar cadeia de custodia

### Passo 2.3: Avaliacao de impacto
- [ ] Identificar dados potencialmente comprometidos
- [ ] Determinar numero de usuarios afetados
- [ ] Avaliar impacto regulatorio (LGPD, PCI DSS)
- [ ] Verificar obrigacoes de notificacao

### Passo 2.4: Comunicacao
- [ ] Atualizar status para stakeholders
- [ ] Preparar comunicacao externa (se necessario)
- [ ] Notificar legal se houver vazamento de dados

---

## FASE 3: ANALISE E ERRADICACAO (1-24 horas)

### Passo 3.1: Analise forense
- [ ] Analisar evidencias coletadas
- [ ] Identificar vetor de ataque
- [ ] Mapear todas as acoes do atacante
- [ ] Identificar causa raiz

### Passo 3.2: Erradicacao
- [ ] Remover malware/backdoor
- [ ] Patchear vulnerabilidade explorada
- [ ] Resetar credenciais comprometidas
- [ ] Verificar que todas as portas de entrada estao fechadas

### Passo 3.3: Verificacao
- [ ] Confirmar que a causa raiz foi removida
- [ ] Verificar integridade dos sistemas
- [ ] Testar funcionalidade critica
- [ ] Monitorar por indicadores de recomprometimento

---

## FASE 4: RECUPERACAO (24-72 horas)

### Passo 4.1: Restauracao
- [ ] Restaurar sistemas a partir de backups verificados
- [ ] Aplicar patches de seguranca
- [ ] Verificar integridade dos dados restaurados
- [ ] Confirmar funcionalidade de todos os servicos criticos

### Passo 4.2: Monitoramento reforcado
- [ ] Ativar alertas de severidade baixa
- [ ] Monitorar tráfego de rede intensivamente
- [ ] Verificar logs a cada 2 horas por 48 horas
- [ ] Documentar qualquer anomalia

### Passo 4.3: Comunicacao final
- [ ] Notificar usuarios afetados (se obrigatorio)
- [ ] Atualizar status page
- [ ] Comunicar resolucao para stakeholders

---

## FASE 5: POST-MORTEM (5 dias uteis apos resolucao)

### Passo 5.1: Preparacao
- [ ] Compilar timeline completa do incidente
- [ ] Coletar feedback de todos os participantes
- [ ] Identificar o que deu certo e o que deu errado

### Passo 5.2: Sessao de post-mortem
- [ ] Realizar sessao blameless com todos envolvidos
- [ ] Aplicar analise de causa raiz (5 Whys / Fishbone)
- [ ] Identificar fatores sistemicos

### Passo 5.3: Acoes corretivas
- [ ] Definir itens de acao com dono e deadline
- [ ] Priorizar acoes por impacto e esforco
- [ ] Registrar no sistema de tracking

### Passo 5.4: Melhorias de processo
- [ ] Atualizar runbook com lições aprendidas
- [ ] Revisar e atualizar plano de resposta
- [ ] Agendar proximo treinamento de equipe
- [ ] Atualizar metricas de maturidade

---

## CHECKLIST FINAL
- [ ] Incidente formalmente fechado
- [ ] Post-mortem concluido e documentado
- [ ] Todas as acoes corretivas definidas
- [ ] Plano de resposta atualizado
- [ ] Metricas registradas
- [ ] Proximo simulado agendado
- [ ] Comunicacao final para a organizacao
```

---

## 12. Referências

### Frameworks e Padrões

1. **NIST SP 800-61 Rev. 2** — Computer Security Incident Handling Guide. National Institute of Standards and Technology, 2012.
2. **NIST Cybersecurity Framework (CSF) 2.0** — Framework for Improving Critical Infrastructure Cybersecurity, 2024.
3. **ISO/IEC 27035** — Information security incident management. International Organization for Standardization.
4. **SANS Incident Response Process** — Six-step incident response methodology.
5. **MITRE ATT&CK Framework** — Adversarial Tactics, Techniques, and Common Knowledge.

### Casos Públicos de Referência — Lições de Incidentes Reais

#### 6. Target Breach (2013) — Falha na Resposta a Incidentes

**Timeline:**
- Novembro 2013: Credenciais roubadas de empresa terceira (Fazio Mechanical, fornecedora de HVAC) dão acesso à rede Target.
- 27 Novembro 2013: FireEye (sistema de monitoramento) detecta malware e gera alerta. Equipe de segurança em Bangalore (terceirizada) notifica Minneapolis.
- 27-30 Novembro 2013: Alertas ignorados pela equipe de Minneapolis. Nenhuma ação tomada.
- 15 Dezembro 2013: Dados de cartões de crédito/débito começam a ser exfiltrados.
- 12-13 Janeiro 2014: Target confirma a violação publicamente.
- Janeiro-Fevereiro 2014: 40 milhões de cartões comprometidos, 70 milhões de registros pessoais expostos.

**O que deu errado:**
- Alertas do FireEye foram gerados e ignorados pela equipe terceirizada de segurança
- Falta de integração entre equipes internas e terceiras
- Sem escalação automática quando alertas não eram atendidos
- Containment completamente ausente — o atacante operou por 12 dias

**O que deu certo (parcialmente):**
- O sistema de monitoramento (FireEye) detectou o malware corretamente
- A arquitetura de detecção funcionou; foi o processo humano que falhou

**Licoes aprendidas:**
- Monitoramento sem resposta automatizada e escalação e inutil
- A dependencia de terceiros para seguranca operacional precisa de SLAs claros
- Processo de containment deve ser automatizado, nao depender de decisao humana em horario comercial

#### 7. Equifax Breach (2017) — Divulgacao Atrasada

**Timeline:**
- 7 Marco 2017: Apache publica patch para CVE-2017-5638 (Apache Struts)
- ~8 Marco 2017: Equifax recebe notificacao interna do patch. Nao e aplicado.
- 12 Maio 2017: Atacantes exploram a vulnerabilidade no portal web da Equifax
- 13 Maio - 30 Julho 2017: Atacantes acessam dados de 147.9 milhoes de pessoas
- 29 Julho 2017: Equifax descobre a violacao internamente
- 7 Setembro 2017: Equifax divulga publicamente (6 semanas apos descoberta)

**O que deu errado:**
- Patch de seguranca nao foi aplicado por 2 meses apos a notificacao
- O scanner de vulnerabilidades nao detectou a falha (certificado expirado)
- Divulgacao publica atrasada — 6 semanas entre descoberta e notificacao
- Equipe de comunicacao gerou caos: site de notificacao era inseguro, FAQ contraditorio
- CEO, CIO e CISO renunciaram

**O que deu certo (parcialmente):**
- A vulnerabilidade foi eventualmente detectada internamente

**Licoes aprendidas:**
- Gerenciamento de patches e critico — SLAs para aplicacao de patches criticos devem ser medidos em dias, nao semanas
- Ferramentas de seguranca precisam de manutencao continua (certificados validos, signatures atualizadas)
- Comunicacao de incidente precisa ser planejada ANTES de acontecer
- 147.9 milhoes de registros expostos — dados pessoais precisam de criptografia em repouso

#### 8. SolarWinds (2020) — Ataque a Cadeia de Suprimentos

**Timeline:**
- Outubro 2019: Atacantes (APT29/Cozy Bear, ligado a Russia) comprometem a pipeline de build da SolarWinds
- Fevereiro 2020: Malware (SUNBURST) injetado no atualizador Orion (versao 2019.4 HF 5)
- Marco 2020: Atualizacao maliciosa distribuida para 18.000 organizacoes
- Marco-Junho 2020: Atacantes selecionam alvos de alto valor para persistencia avancada
- 12 Dezembro 2020: FireEye descobre o comprometimento acidentalmente (roubo de ferramentas vermelhas)
- 13 Dezembro 2020: CISA emite alerta de emergencia (EA20-332A)
- 2020-2021: Investigacao revela acesso a redes do Tesouro dos EUA, Departamento de Comercio, DHS e outras agencias

**O que deu errado:**
- Supply chain completamente comprometida — confianca cega em atualizacoes assinadas
- 18.000 organizacoes afetadas antes da deteccao
- Deteccao acidental — o SOC da organizacao nao identificou o ataque
- Persistencia avancada permitiu acesso por 9+ meses

**O que deu certo:**
- FireEye detectou o comprometimento quando seus proprios tools foram roubados
- Resposta coordenada entre governo dos EUA e setor privado
- Deteccao do backdoor via analise de trafego de rede (DNS beaconing)

**Licoes aprendidas:**
- Software supply chain precisa de verificacao em profundidade (SBOMs, SLSA, assinaturas de build)
- Confianca em atualizacoes automaticas de terceiros e um vetor de ataque
- Monitoramento de trafego de rede e essencial — o beacon DNS do SUNBURST era detectavel
- Organizacoes precisam de capacidade propria de deteccao, nao depender apenas de ferramentas de terceiros

#### 9. Colonial Pipeline (2021) — Resposta a Ransomware

**Timeline:**
- 6 Maio 2021: Ransomware DarkSide infecta rede corporativa (via VPN sem MFA)
- 7 Maio 2021: Colonial Pipeline decide desligar toda a pipeline (5.500 milhas) por precaucao
- 8 Maio 2021: Emergencia nacional declarada nos 17 estados afetados
- 12 Maio 2021: Pipeline retoma operacoes parcialmente
- 19 Maio 2021: Operacoes completamente restauradas
- Colonial paga resgate de $4.4 milhoes em Bitcoin (75 recuperados pelo FBI)

**O que deu errado:**
- VPN sem autenticacao multifator permitiu acesso inicial
- Redes corporativas e de controle industrial (OT) nao estavam segmentadas
- Decisao de desligar a pipeline inteira foi controversa — sistemas de controle nao foram comprometidos
- Pagamento de resgate incentivou mais ataques

**O que deu certo:**
- Resposta rapida — pipeline desligada por precaucao (embora questionavel)
- Coordenacao com CISA, FBI e agencias governamentais
- Recuperacao parcial do resgate pelo FBI

**Licoes aprendidas:**
- Segmentacao entre redes IT e OT e critica para infraestrutura critica
- MFA em todos os acessos remotos — sem excecoes
- Planos de contingencia para operacoes manuais precisam existir e ser testados
- A decisao de desligar sistemas de controle industriais precisa ser muito bem ponderada

#### 10. Log4Shell (2021) — Disclosure Coordenado

**Timeline:**
- 24 Novembro 2021: Chen Zhaohun (Alibaba Cloud) reporta CVE-2021-44228 ao Apache
- 26 Novembro 2021: Apache confirma a vulnerabilidade
- 9 Dezembro 2021: Apache publica patch (Log4j 2.15.0)
- 10 Dezembro 2021: Primeiros reports de exploit publico
- 13 Dezembro 2021: Apache libera Log4j 2.16.0 (correcao adicional)
- 14 Dezembro 2021: CISA e CNA emitem advisories
- 17 Dezembro 2021: Apache libera Log4j 2.17.0 (correcao final)
- 18+ dias de exposicao ativa antes do patch completo

**O que deu certo:**
- Processo de disclosure coordenado seguido corretamente
- Patch disponibilizado em 15 dias (rapido para uma vulnerabilidade de tal gravidade)
- Comunidade open-source respondeu rapidamente com patches e mitigacoes
- Muitas organizacoes detectaram tentativas de exploracao via WAF e logs

**O que deu errado:**
- Dependencia massiva de uma unica biblioteca (log4j) em milhoes de sistemas
- Muitas organizacoes nao sabiam onde log4j era usado (falta de SBOM)
- Patches iniciais (2.15.0) tiveram bypass — precisaram de 3 versoes
- Atacantes exploraram em escala massiva antes que organizacoes pudessem patchear
- Dificuldade de identificar todos os sistemas afetados em ambientes complexos

**Licoes aprendidas:**
- SBOM (Software Bill of Materials) e essencial para saber o que esta no seu sistema
- Dependencias de bibliotecas open-source precisam ser gerenciadas e monitoradas
- Vulnerabilidades em componentes usados em escala global requerem resposta em horas, nao semanas
- Disclosure coordenado funciona, mas a velocidade de exploracao publica supera a velocidade de patching

#### 11. LastPass (2022) — Comunicacao Pos-Incidente

**Timeline:**
- Agosto 2022: Engenheiro da LastPass e comprometido via malware no computador pessoal
- Agosto 2022: Atacantes acessam o ambiente de desenvolvimento da LastPass
- Setembro 2022: Atacantes roubam chaves de criptografia do ambiente de desenvolvimento
- Novembro 2022: Atacantes usam as chaves para acessar o armazenamento de backups criptografados
- 22 Novembro 2022: LastPass divulga publicamente a violacao (incompleta)
- 23 Dezembro 2022: LastPass divulga informacoes adicionais — vaults criptografados roubados
- Janeiro 2023: LastPass revela que dados de backup de usuarios foram acessados

**O que deu errado:**
- Ambiente de desenvolvimento nao estava segmentado do ambiente de producao
- Chaves de criptografia estavam acessiveis a partir do ambiente comprometido
- Comunicacao foi incremental e gerou desconfianca — informacoes iniciais minimizaram o impacto
- Usuarios so souberam da gravidade real semanas depois
- Vault keys roubadas permitiram brute-force offline de senhas

**O que deu certo:**
- Arquitetura de criptografia do vault impediu acesso direto aos dados
- Notificacoes progressivas mantiveram usuarios informados (embora tarde)

**Licoes aprendidas:**
- Ambientes de dev, staging e producao devem ser estritamente segmentados
- Chaves de criptografia devem ser gerenciadas por HSMs ou KMS dedicados
- Comunicacao pos-incidente precisa ser completa e transparente desde o inicio
- Criptografia de vaults com senha mestra do usuario e a ultima linha de defesa — nao a primeira

#### 12. MOVEit (2023) — Resposta a Zero-Day

**Timeline:**
- 27 Maio 2023: Progress Software descobre zero-day CVE-2023-34362 no MOVEit Transfer
- 31 Maio 2023: Progress Software publica patch
- 1 Junho 2023: Progress Software notifica clientes diretamente
- 5 Junho 2023: CISA emite alerta de emergencia
- Junho 2023+: Cl0p ransomware group explora em escala massiva
- 2.500+ organizacoes afetadas, incluindo agencias governamentais dos EUA, Shell, BBC, British Airways
- Julho 2023: Progress Software publica comunicacao detalhada e roadmap de seguranca

**O que deu certo:**
- Patch disponibilizado rapidamente (4 dias apos descoberta)
- Notificacao direta a clientes antes da divulgacao publica
- Coordenacao com CISA e agencias governamentais
- Progress Software criou pagina dedicada de updates e transparencia
- Cl0p group fez disclosure publico permitindo que organizacoes se protegessem

**O que deu errado:**
- Zero-day explotado antes do patch ser amplamente aplicado
- Muitas organizacoes nao aplicaram o patch rapidamente
- O ataque usou SQL injection — vulnerabilidade basica em software corporativo
- Escala massiva do exploit (2.500+ organizacoes) indica falta de monitoramento de integridade de software

**Licoes aprendidas:**
- Software corporativo que processa dados sensiveis precisa de rigoroso teste de seguranca
- Divulgacao publica de exploits (mesmo por grupos criminosos) pode acelerar a resposta
- Organizacoes precisam de capacidade de responder a advisories de seguranca em horas
- SQL injection continua sendo uma vulnerabilidade relevante — testes de seguranca devem ser continuos

### Ferramentas

13. **YARA** — Pattern matching para malware research. VirusTotal, 2024.
14. **Volatility Framework** — Memory forensics framework. volatilityfoundation.org.
15. **OSSEC** — Host-based intrusion detection system. ossec.net.
16. **Zeek (formerly Bro)** — Network security monitoring. zeek.org.
17. **MISP** — Malware Information Sharing Platform. misp-project.org.

### Livros e Artigos

18. Schneier, B. "Applied Cryptography." 20th Anniversary Edition. Wiley, 2015.
19. Hoglund, G. & McGraw, G. "Exploiting Software: How to Break Code." Addison-Wesley, 2004.
20. Christey, S. & Martin, R. "Vulnerability Type Distributions in CVE." MITRE, 2007.
21. Wheeler, D. "Secure Programming Coding Standards." SEI CERT C Coding Standard.
22. OWASP. "Incident Response Verification Project." owasp.org, 2024.
23. FIRST. "Forum of Incident Response and Security Teams." first.org.
24. ENISA. "Good Practice Guide for Incident Management." European Union Agency for Cybersecurity, 2023.
