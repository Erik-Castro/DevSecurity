# Capítulo 14 — Monitoramento e Observabilidade de Segurança

> "Voce nao pode proteger o que nao consegue ver."
> — Bruce Schneier

## Introducao

Monitoramento e observabilidade sao os pilares que transformam seguranca de reativa em
proativa. Sem visibilidade adequada, uma equipe de seguranca esta essencialmente
trabalhando no escuro — reagindo a incidentes depois que ja causaram dano, em vez de
detectar e neutralizar ameacas antes que se materializem.

Este capitulo explora como construir uma estrutura completa de monitoramento de seguranca,
desde a coleta basica de logs ate caças ao ameacas automatizadas com Jupyter notebooks.

---

## 1. Observabilidade vs Monitoramento

### 1.1 Definicao Fundamental

**Monitoramento** e a coleta e analise de dados pre-definidos para verificar se um
sistema esta dentro de limites aceitaveis. Voce pergunta: "esta tudo funcionando como
esperado?"

**Observabilidade** e a capacidade de entender o estado interno de um sistema a partir
dos seus sinais externos. Voce pergunta: "o que esta acontecendo dentro do sistema e por
que?"

```
Monitoramento:   "O CPU esta em 95%."
Observabilidade: "O CPU esta em 95% porque um usuario executou uma query O(n^3) na tabela orders."
```

### 1.2 Os Tres Pilares

Os tres pilares da observabilidade formam a base para qualquer estrutura de seguranca
eficaz:

**Logs** — Registros discretos de eventos que aconteceram no sistema. Cada log e um
evento individual com timestamp, nivel e contexto.

```yaml
# Exemplo de log de seguranca estruturado
timestamp: "2025-01-15T14:32:01Z"
level: "WARNING"
service: "auth-api"
event: "login_failed"
user_id: "u-12345"
source_ip: "203.0.113.42"
user_agent: "Mozilla/5.0..."
failure_reason: "invalid_password"
attempt_count: 5
geo_country: "BR"
geo_city: "Sao Paulo"
```

**Metrics** — Numeros agregados ao longo do tempo que representam o comportamento do
sistema. Metrics sao ideais para dashboards e alertas.

```yaml
# Metricas de seguranca
login_failures_total: 1523
active_sessions: 847
blocked_ips: 23
api_requests_per_second: 1250
auth_latency_p99_ms: 45
security_alerts_open: 12
```

**Traces** — Um identificador unico que acompanha uma requisicao completa atraves de
multiplos servicos. Traces sao essenciais para entender ataques que percorrem varios
componentes.

```
Trace ID: abc-123-def-456
  [gateway]       POST /api/login          (12ms)
    [auth-api]    validate_credentials     (8ms)
      [redis]     check_rate_limit         (2ms)
      [postgres]  query_user               (5ms)
    [auth-api]    generate_token           (3ms)
    [audit-log]   record_login_attempt     (1ms)
```

### 1.3 Observabilidade de Seguranca

Observabilidade de seguranca vai alem da observabilidade tradicional ao focar
especificamente em sinais de ameaca. Enquanto a observabilidade de operacoes responde
"por que o sistema esta lento?", a observabilidade de seguranca responde:

- Quem esta acessando o sistema e de onde?
- O que esses usuarios estao fazendo?
- Essas acoes sao legitimas ou representam uma ameaca?
- Qual e o impacto potencial se essa ameaca se materializar?

```python
# Conceito de security observability layer
class SecurityObservability:
    """Camada de observabilidade que enriquece sinais com contexto de seguranca."""

    def __init__(self, threat_intel, geo_ip, user_behavior_db):
        self.threat_intel = threat_intel
        self.geo_ip = geo_ip
        self.user_behavior_db = user_behavior_db

    def enrich_event(self, raw_event):
        """Enriquece um evento com contexto de seguranca."""
        enriched = dict(raw_event)

        # Contexto geografico
        ip = raw_event.get("source_ip")
        geo = self.geo_ip.lookup(ip)
        enriched["geo_country"] = geo["country"]
        enriched["geo_city"] = geo["city"]
        enriched["is_tor_exit"] = self.threat_intel.is_tor_exit(ip)
        enriched["is_known_bad_ip"] = self.threat_intel.is_malicious(ip)

        # Contexto comportamental
        user_id = raw_event.get("user_id")
        if user_id:
            baseline = self.user_behavior_db.get_baseline(user_id)
            enriched["anomaly_score"] = self._calculate_anomaly(raw_event, baseline)
            enriched["is_impossible_travel"] = self._check_impossible_travel(
                user_id, raw_event
            )

        return enriched

    def _calculate_anomaly(self, event, baseline):
        score = 0.0
        if event.get("geo_country") not in baseline.get("usual_countries", []):
            score += 0.3
        if event.get("hour_local") not in baseline.get("usual_hours", []):
            score += 0.2
        if event.get("user_agent") not in baseline.get("known_devices", []):
            score += 0.2
        if event.get("failure_reason") == "invalid_password":
            score += 0.1 * min(event.get("attempt_count", 1), 5)
        return min(score, 1.0)

    def _check_impossible_travel(self, user_id, event):
        last_event = self.user_behavior_db.get_last_event(user_id)
        if not last_event:
            return False
        distance_km = self._haversine(
            last_event["lat"], last_event["lon"],
            event.get("lat", 0), event.get("lon", 0)
        )
        time_diff_hours = (
            event["timestamp"] - last_event["timestamp"]
        ).total_seconds() / 3600
        if time_diff_hours <= 0:
            return False
        speed_kmh = distance_km / time_diff_hours
        return speed_kmh > 900  # Mais rapido que um aviao comercial
```

### 1.4 OpenTelemetry para Seguranca

OpenTelemetry (OTel) fornece um framework padronizado para coleta de telemetria.
Para seguranca, ele permite criar um pipeline unificado que coleta logs, metrics e
traces com contexto de seguranca enriquecido.

```yaml
# Configuracao do OpenTelemetry Collector para seguranca
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Receber logs de seguranca diretamente
  filelog:
    include:
      - /var/log/security/*.log
      - /var/log/auth/*.log
    operators:
      - type: json_parser
        timestamp:
          parse_from: attributes.timestamp
          layout: "2006-01-02T15:04:05Z"
      - type: add_fields
        fields:
          security.classification: "unknown"
          security.severity: "low"

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000

  # Enriquecimento com contexto de seguranca
  transform:
    log_statements:
      - context: log
        statements:
          - set(attributes["security.classification"],
                 "critical") where body matches ".*privilege.escalation.*"
          - set(attributes["security.classification"],
                 "high") where body matches ".*failed.login.*"
          - set(attributes["security.severity"],
                 "critical") where attributes["security.classification"] == "critical"

  # Filtrar dados sensiveis
  filter/security:
    error_mode: ignore
    logs:
      log:
        - 'attributes["security.classification"] != "none"'

exporters:
  # Enviar logs de seguranca para o SIEM
  elasticsearch/security:
    endpoints: ["https://siem.internal:9200"]
    index: "security-logs-%{yyyy.MM.dd}"
    tls:
      ca_file: /etc/otel/certs/ca.crt

  # Enviar metricas de seguranca para Prometheus
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: "security"

  # Enviar traces para Jaeger
  jaeger:
    endpoint: "jaeger.internal:14250"
    tls:
      ca_file: /etc/otel/certs/ca.crt

service:
  pipelines:
    security_logs:
      receivers: [otlp, filelog]
      processors: [transform, filter/security, batch]
      exporters: [elasticsearch/security]
    security_metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]
    security_traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [jaeger]
```

---

## 2. Security Logging

### 2.1 O Que Registrar para Seguranca

Nem todo log e util para seguranca. O segredo esta em registrar exatamente o necessario
— suficiente para detectar ameacas e conduzir investigacoes, sem inundar o sistema com
ruido.

**Eventos criticos que SEMPRE devem ser logados:**

| Categoria | Eventos | Exemplo |
|-----------|---------|---------|
| Autenticacao | Login, logout, falha, lockout | `login_success`, `login_failed`, `account_locked` |
| Autorizacao | Acesso negado, elevacao de privilegio | `access_denied`, `privilege_escalated` |
| Dados | Leitura/escrita de dados sensiveis | `pii_accessed`, `data_exported` |
| Configuracao | Mudancas em politicas, usuarios | `policy_changed`, `user_created` |
| Rede | Conexoes incomuns, ports scan | `unusual_connection`, `port_scan_detected` |
| Sistema | Start/stop de servicos criticos | `service_started`, `service_stopped` |

**Eventos que NAO devem ser logados:**

- Senhas ou hashes (nunca)
- Tokens de sessao completos (logar apenas os ultimos 4 caracteres)
- Dados de cartao de credito completos (usar mascaramento)
- Dados de saude (PII sob HIPAA/GDPR)

### 2.2 Formato de Log Estruturado

Logs estruturados sao criticos para seguranca por permitem busca e analise automatizada.
Nunca use logs em texto livre para eventos de seguranca.

```json
{
  "timestamp": "2025-01-15T14:32:01.123Z",
  "level": "WARNING",
  "service": "auth-api",
  "version": "1.2.0",
  "environment": "production",
  "trace_id": "abc-123-def-456",
  "span_id": "789-ghi",
  "event": {
    "type": "authentication",
    "action": "login_failed",
    "outcome": "failure",
    "reason": "invalid_password"
  },
  "actor": {
    "user_id": "u-12345",
    "session_id": "sess-abc",
    "role": "user"
  },
  "source": {
    "ip": "203.0.113.42",
    "user_agent": "Mozilla/5.0 (X11; Linux x86_64)",
    "geo": {
      "country": "BR",
      "city": "Sao Paulo",
      "coordinates": { "lat": -23.55, "lon": -46.63 }
    }
  },
  "security": {
    "classification": "high",
    "risk_score": 0.75,
    "indicators": ["brute_force_attempt", "unusual_geo"],
    "correlation_id": "corr-xyz-789"
  },
  "metadata": {
    "attempt_number": 5,
    "time_since_last_attempt_sec": 12
  }
}
```

### 2.3 Niveis de Log para Eventos de Seguranca

```python
import logging
import json
from datetime import datetime, timezone
from enum import Enum


class SecurityLevel(Enum):
    """Niveis de severidade especificos para seguranca."""
    CRITICAL = "critical"    # Ameaca ativa, acao imediata necessaria
    HIGH = "high"            # Atividade suspeita, investigacao necessaria
    MEDIUM = "medium"        # Anomalia detectada, monitorar
    LOW = "low"              # Evento de interesse, registrar
    INFO = "info"            # Atividade normal de seguranca


class SecurityEvent:
    """Representa um evento de seguranca estruturado."""

    def __init__(self, event_type, action, source_ip, user_id=None,
                 outcome="success", reason=None, risk_score=0.0):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type
        self.action = action
        self.source_ip = source_ip
        self.user_id = user_id
        self.outcome = outcome
        self.reason = reason
        self.risk_score = risk_score
        self.classification = self._classify()

    def _classify(self):
        if self.risk_score >= 0.8:
            return SecurityLevel.CRITICAL.value
        elif self.risk_score >= 0.6:
            return SecurityLevel.HIGH.value
        elif self.risk_score >= 0.3:
            return SecurityLevel.MEDIUM.value
        elif self.risk_score > 0.0:
            return SecurityLevel.LOW.value
        return SecurityLevel.INFO.value

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "action": self.action,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "outcome": self.outcome,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "classification": self.classification,
        }


class SecurityLogger:
    """Logger especializado para eventos de seguranca."""

    def __init__(self, service_name, environment="production"):
        self.service_name = service_name
        self.environment = environment
        self.logger = logging.getLogger(f"security.{service_name}")
        self.logger.setLevel(logging.DEBUG)

        # Handler para logs de seguranca (JSON estruturado)
        handler = logging.StreamHandler()
        handler.setFormatter(SecurityFormatter())
        self.logger.addHandler(handler)

    def log_event(self, security_event, extra_context=None):
        log_entry = {
            "service": self.service_name,
            "environment": self.environment,
            "event": security_event.to_dict(),
        }
        if extra_context:
            log_entry["context"] = extra_context

        level = self._map_classification(security_event.classification)
        self.logger.log(level, json.dumps(log_entry))

    def log_login_success(self, user_id, source_ip, user_agent=""):
        event = SecurityEvent(
            event_type="authentication",
            action="login_success",
            source_ip=source_ip,
            user_id=user_id,
            outcome="success",
            risk_score=0.0,
        )
        self.log_event(event, {"user_agent": user_agent})

    def log_login_failure(self, user_id, source_ip, reason, attempt_count):
        risk = min(0.1 * attempt_count, 0.9)
        event = SecurityEvent(
            event_type="authentication",
            action="login_failed",
            source_ip=source_ip,
            user_id=user_id,
            outcome="failure",
            reason=reason,
            risk_score=risk,
        )
        self.log_event(event, {"attempt_count": attempt_count})

    def log_access_denied(self, user_id, source_ip, resource, permission_needed):
        event = SecurityEvent(
            event_type="authorization",
            action="access_denied",
            source_ip=source_ip,
            user_id=user_id,
            outcome="failure",
            reason=f"missing_permission:{permission_needed}",
            risk_score=0.4,
        )
        self.log_event(event, {"resource": resource, "permission": permission_needed})

    def log_data_access(self, user_id, source_ip, resource, data_classification):
        risk_map = {"public": 0.0, "internal": 0.1, "confidential": 0.3,
                     "restricted": 0.5, "pii": 0.6, "financial": 0.7}
        risk = risk_map.get(data_classification, 0.5)
        event = SecurityEvent(
            event_type="data_access",
            action="read",
            source_ip=source_ip,
            user_id=user_id,
            outcome="success",
            risk_score=risk,
        )
        self.log_event(event, {
            "resource": resource,
            "data_classification": data_classification,
        })

    def log_privilege_escalation(self, user_id, source_ip, old_role, new_role):
        event = SecurityEvent(
            event_type="authorization",
            action="privilege_escalation",
            source_ip=source_ip,
            user_id=user_id,
            outcome="success",
            risk_score=0.8,
        )
        self.log_event(event, {"old_role": old_role, "new_role": new_role})

    def log_suspicious_activity(self, user_id, source_ip, activity_type, details):
        event = SecurityEvent(
            event_type="threat",
            action="suspicious_activity",
            source_ip=source_ip,
            user_id=user_id,
            outcome="detected",
            reason=activity_type,
            risk_score=0.7,
        )
        self.log_event(event, {"details": details})

    def _map_classification(self, classification):
        level_map = {
            "critical": logging.CRITICAL,
            "high": logging.ERROR,
            "medium": logging.WARNING,
            "low": logging.INFO,
            "info": logging.DEBUG,
        }
        return level_map.get(classification, logging.INFO)


class SecurityFormatter(logging.Formatter):
    """Formatter que garante saida JSON estruturada."""

    def format(self, record):
        try:
            data = json.loads(record.getMessage())
        except json.JSONDecodeError:
            data = {"message": record.getMessage()}

        data["log_level"] = record.levelname
        data["logger"] = record.name
        return json.dumps(data, ensure_ascii=False)
```

### 2.4 Pipeline de Logging Completo com Fluentd

Fluentd atua como camada de coleta, enriquecimento e roteamento de logs de seguranca.

```yaml
# fluentd.conf — Pipeline de logs de seguranca
# Receber logs de aplicacoes
<source>
  @type forward
  port 24224
  bind 0.0.0.0
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

# Receber logs do sistema operacional
<source>
  @type tail
  path /var/log/auth.log,/var/log/syslog
  pos_file /var/log/fluentd/system.pos
  tag system.auth
  <parse>
    @type syslog
  </parse>
</source>

# Filtrar e classificar logs de seguranca
<filter security.**>
  @type record_transformer
  enable_ruby true
  <record>
    security_classification ${record.dig("security", "classification") || "unknown"}
    enriched_at ${Time.now.utc.iso8601}
  </record>
</filter>

# Detectar e enriquecer IPs maliciosos
<filter security.**>
  @type ruby_transform
  <ruby>
    require 'net/http'
    require 'json'

    def lookup_ip_reputation(ip)
      begin
        uri = URI("http://threat-intel.internal:8080/api/lookup/#{ip}")
        response = Net::HTTP.get_response(uri)
        JSON.parse(response.body)
      rescue => e
        {"malicious" => false, "error" => e.message}
      end
    end

    def transform(record)
      ip = record.dig("source", "ip")
      if ip
        reputation = lookup_ip_reputation(ip)
        record["threat_intel"] = {
          "malicious" => reputation["malicious"],
          "category" => reputation["category"],
          "confidence" => reputation["confidence"]
        }
      end
      record
    end
  </ruby>
</filter>

# Roteamento baseado em classificacao de seguranca
<match security.**>
  @type copy

  # Logs criticos vao para alerta imediato
  <store>
    @type elasticsearch
    host siem-internal
    port 9200
    index_name security-critical-${Time.now.strftime("%Y.%m.%d")}
    <buffer>
      @type file
      path /var/log/fluentd/buffer/security-critical
      flush_interval 1s
      retry_type exponential_backoff
      chunk_limit_size 8M
      total_limit_size 2G
    </buffer>
  </store>

  # Todos os logs de seguranca vao para o SIEM
  <store>
    @type elasticsearch
    host siem-internal
    port 9200
    index_name security-logs-${Time.now.strftime("%Y.%m.%d")}
    <buffer>
      @type file
      path /var/log/fluentd/buffer/security-all
      flush_interval 5s
      retry_type exponential_backoff
      chunk_limit_size 16M
      total_limit_size 8G
    </buffer>
  </store>

  # Backup em S3 para compliance
  <store>
    @type s3
    aws_key_id "#{ENV['AWS_ACCESS_KEY_ID']}"
    aws_sec_key "#{ENV['AWS_SECRET_ACCESS_KEY']}"
    s3_bucket security-logs-archive
    s3_region us-east-1
    path "security-logs/%Y/%m/%d/"
    buffer_type file
    buffer_path /var/log/fluentd/buffer/s3
    buffer_chunk_limit 256M
    buffer_total_limit_size 10G
    flush_interval 300s
    store_as gzip
    <format>
      @type json
    </format>
  </store>
</match>
```

---

## 3. SIEM (Security Information and Event Management)

### 3.1 ELK Stack para Seguranca

O ELK Stack (Elasticsearch, Logstash, Kibana) e uma das solucoes mais populares para
SIEM open-source. Cada componente tem um papel especifico na pipeline de seguranca.

**Arquitetura ELK para Seguranca:**

```
App Logs ──> Logstash ──> Elasticsearch ──> Kibana
OS Logs  ──> (parse,    (armazenamento   (dashboards,
Firewall ──>  enriquece,  e indexacao)     visualizacao,
IDS/IPS ──>  roteamento)                  alertas)
                    │
                    ├──> Alertas ──> Slack/PagerDuty
                    └──> Compliance ──> S3 Glacier
```

### 3.2 Wazuh como SIEM Open-Source

Wazuh e uma plataforma open-source que combina deteccao de intrusao, monitoramento de
integridade, analise de vulnerabilidades e resposta a incidentes.

**Funcionalidades principais do Wazuh:**

- Monitoramento de logs em tempo real
- Deteccao de intrusao baseada em assinaturas
- Monitoramento de integridade de arquivos
- Analise de vulnerabilidades
- Conformidade com regulamentacoes (PCI DSS, GDPR, HIPAA)
- Resposta a incidentes automatizada

```yaml
# /var/ossec/etc/ossec.conf — Configuracao basica do Wazuh
<ossec_config>
  <global>
    <email_notification>yes</email_notification>
    <email_to>security@example.com</email_to>
    <smtp_server>smtp.example.com</smtp_server>
    <email_from>wazuh@example.com</email_from>
    <email_maxperhour>12</email_maxperhour>
  </global>

  <!-- Monitoramento de logs do sistema -->
  <localfile>
    <log_format>syslog</log_format>
    <location>/var/log/auth.log</location>
  </localfile>

  <localfile>
    <log_format>syslog</log_format>
    <location>/var/log/syslog</location>
  </localfile>

  <!-- Monitoramento de logs de aplicacao -->
  <localfile>
    <log_format>json</log_format>
    <location>/var/log/app/security.log</location>
  </localfile>

  <!-- Monitoramento de integridade de arquivos criticos -->
  <syscheck>
    <frequency>3600</frequency>
    <scan_on_start>yes</scan_on_start>
    <alert_new_files>yes</alert_new_files>

    <directories check_all="yes" report_changes="yes" realtime="yes">
      /etc,/usr/bin,/usr/sbin
    </directories>

    <directories check_all="yes" report_changes="yes" realtime="yes">
      /bin,/sbin
    </directories>
  </syscheck>

  <!-- Regras de seguranca customizadas -->
  <rule>
    <rule id="100001" level="12">
      <if_sid>5712</if_sid>
      <field name="operation">rootkit</field>
      <description>Rootkit detection alert</description>
      <group>rootcheck,</group>
    </rule>
  </rule>

  <!-- Ativacao de resposta automatizada -->
  <active-response>
    <command>firewall-drop</command>
    <location>local</location>
    <rules_id>5712,100001</rules_id>
  </active-response>
</ossec_config>
```

### 3.3 Conceitos do Splunk

Splunk e uma plataforma comercial de SIEM amplamente utilizada em grandes empresas.
Embora nao seja open-source, seus conceitos influenciaram muitas solucoes da area.

**Conceitos fundamentais do Splunk para seguranca:**

- **Sourcetype**: Identifica o formato do dado de entrada (ex: `linux:syslog`, `cisco:ios`)
- **Search Processing Language (SPL)**: Linguagem de consulta para analise de logs
- **Dashboards**: Visualizacoes customizadas de dados de seguranca
- **Alerts**: Notificacoes automaticas baseadas em condicoes predefinidas
- **Notable Events**: Eventos que precisam de atencao humana
- **Adaptive Response**: Acoes automatizadas em resposta a ameacas

```spl
# Exemplos de consultas Splunk para seguranca

# Detectar brute force
index=security sourcetype=auth action=failure
| stats count as failure_count by src_ip, user
| where failure_count > 5
| sort -failure_count

# Detectar login fora do horario comercial
index=security sourcetype=auth action=success
| eval hour=strftime(_time, "%H")
| where hour < 7 OR hour > 19
| table _time, user, src_ip, hour

# Analise de geolocalizacao
index=security sourcetype=auth
| iplocation src_ip
| stats count by Country, City
| sort -count

# Deteccao de data exfiltration
index=network src_ip=INTERNAL*
| stats sum(bytes_out) as total_bytes by src_ip, dest_ip
| where total_bytes > 1000000000
| sort -total_bytes
```

### 3.4 Setup Completo do ELK com Docker

```yaml
# docker-compose.yml — ELK Stack para seguranca
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.http.ssl.enabled=true
      - xpack.security.transport.ssl.enabled=true
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - ELASTICSEARCH_CERTIFICATE_AUTHORITIES=/usr/share/elasticsearch/config/certs/ca.crt
      - ELASTICSEARCH_CERTIFICATE=/usr/share/elasticsearch/config/certs/elasticsearch.crt
      - ELASTICSEARCH_KEY=/usr/share/elasticsearch/config/certs/elasticsearch.key
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    volumes:
      - elasticsearch-data:/usr/share/elasticsearch/data
      - ./certs:/usr/share/elasticsearch/config/certs:ro
    ports:
      - "9200:9200"
    networks:
      - elk
    healthcheck:
      test: ["CMD-SHELL", "curl -k -u elastic:${ELASTIC_PASSWORD} https://localhost:9200/_cluster/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  logstash:
    image: docker.elastic.co/logstash/logstash:8.12.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml:ro
      - ./certs:/usr/share/logstash/config/certs:ro
    ports:
      - "5044:5044"
      - "5000:5000"
      - "9600:9600"
    environment:
      - LS_JAVA_OPTS=-Xms1g -Xmx1g
    networks:
      - elk
    depends_on:
      elasticsearch:
        condition: service_healthy

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    container_name: kibana
    volumes:
      - ./kibana/config/kibana.yml:/usr/share/kibana/config/kibana.yml:ro
      - ./certs:/usr/share/kibana/config/certs:ro
    ports:
      - "5601:5601"
    networks:
      - elk
    depends_on:
      elasticsearch:
        condition: service_healthy

volumes:
  elasticsearch-data:
    driver: local

networks:
  elk:
    driver: bridge
```

```yaml
# logstash/pipeline/security.conf — Pipeline de seguranca
input {
  beats {
    port => 5044
    ssl_enabled => true
    ssl_certificate => "/usr/share/logstash/config/certs/logstash.crt"
    ssl_key => "/usr/share/logstash/config/certs/logstash.key"
  }

  tcp {
    port => 5000
    codec => json_lines
    type => "security-logs"
  }
}

filter {
  # Parse de logs de autenticacao do Linux
  if [type] == "syslog" {
    grok {
      match => {
        "message" => "%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:hostname} %{DATA:program}(?:\[%{POSINT:pid}\])?: %{GREEDYDATA:syslog_message}"
      }
    }

    if [program] == "sshd" {
      grok {
        match => {
          "syslog_message" => "%{GREEDYDATA:action} for %{DATA:auth_method} from %{IP:src_ip} port %{INT:src_port}"
        }
      }

      if "_grokparsefailure" in [tags] {
        grok {
          match => {
            "syslog_message" => "Failed password for (?:invalid user )?%{USER:username} from %{IP:src_ip} port %{INT:src_port}"
          }
          tag_on_failure => []
        }
      }

      # Classificar evento
      mutate {
        add_field => { "event_category" => "authentication" }
        add_field => { "security_type" => "ssh" }
      }
    }
  }

  # Enriquecimento com GeoIP
  if [src_ip] {
    geoip {
      source => "src_ip"
      target => "geoip"
      fields => ["country_name", "region_name", "city_name", "latitude", "longitude"]
    }

    # Verificar se e IP privado
    cidr {
      address => [ "%{src_ip}" ]
      network => [ "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16" ]
      add_tag => [ "internal_ip" ]
    }
  }

  # Deteccao de brute force
  if [event_category] == "authentication" and [action] == "Failed" {
    aggregate {
      task_id => "%{src_ip}"
      code => "map['count'] ||= 0; map['count'] += 1; event.set('failed_attempts', map['count'])"
      push_previous_map_as_event => true
      timeout => 300
    }

    if [failed_attempts] and [failed_attempts] > 5 {
      mutate {
        add_field => { "alert_type" => "brute_force" }
        add_field => { "severity" => "high" }
      }
    }
  }

  # Adicionar timestamp normalizado
  ruby {
    code => "event.set('normalized_timestamp', Time.now.utc.iso8601)"
  }
}

output {
  elasticsearch {
    hosts => ["https://elasticsearch:9200"]
    user => "elastic"
    password => "${ELASTIC_PASSWORD}"
    ssl_enabled => true
    ssl_certificate_authorities => ["/usr/share/logstash/config/certs/ca.crt"]
    index => "security-logs-%{+YYYY.MM.dd}"
  }

  # Alertas criticos vao para canal separado
  if [severity] == "critical" or [severity] == "high" {
    http {
      url => "http://alerting-service:8080/api/alerts"
      http_method => "post"
      format => "json"
    }
  }
}
```

### 3.5 Dashboards de Seguranca

```yaml
# Kibana dashboard — Visao geral de seguranca
# kibana/dashboard/security-overview.json
{
  "dashboard": {
    "title": "Security Overview Dashboard",
    "description": "Visao geral de eventos de seguranca em tempo real",
    "panels": [
      {
        "title": "Eventos por Severidade",
        "type": "pie",
        "query": {
          "bool": {
            "must": [
              { "range": { "@timestamp": { "gte": "now-24h" } } },
              { "term": { "event_category": "security" } }
            ]
          }
        },
        "aggs": {
          "severity": {
            "terms": { "field": "severity.keyword", "size": 5 }
          }
        }
      },
      {
        "title": "Tentativas de Login Falhas por Hora",
        "type": "line",
        "query": {
          "bool": {
            "must": [
              { "term": { "event.action": "login_failed" } },
              { "range": { "@timestamp": { "gte": "now-7d" } } }
            ]
          }
        },
        "aggs": {
          "per_hour": {
            "date_histogram": {
              "field": "@timestamp",
              "calendar_interval": "1h"
            }
          }
        }
      },
      {
        "title": "Top 10 IPs com Mais Atividade Suspeita",
        "type": "horizontal_bar",
        "query": {
          "bool": {
            "must": [
              { "range": { "security.risk_score": { "gte": 0.5 } } }
            ]
          }
        },
        "aggs": {
          "top_ips": {
            "terms": { "field": "source.ip.keyword", "size": 10 }
          }
        }
      },
      {
        "title": "Mapa de Origem dos Ataques",
        "type": "map",
        "query": {
          "bool": {
            "must": [
              { "exists": { "field": "geoip.country_name" } },
              { "term": { "event.outcome": "failure" } }
            ]
          }
        },
        "aggs": {
          "by_country": {
            "terms": { "field": "geoip.country_name.keyword", "size": 50 }
          }
        }
      }
    ]
  }
}
```

---

## 4. Falco para Runtime Security

### 4.1 Introducao ao Falco

Falco e uma ferramenta open-source de seguranca em runtime desenvolvida originalmente
pela Sysdig e agora mantida pela CNCF. Ele monitora atividade do sistema em tempo real
usando chamadas de sistema e aplica regras para detectar comportamentos anomalous.

```
Kernel (syscall) ──> Falco Engine ──> Regras ──> Alertas
                            │
                            ├──> Logs de seguranca
                            └──> Integracao (Slack, PagerDuty, etc.)
```

### 4.2 Regras do Falco

```yaml
# /etc/falco/falco_rules.yaml — Regras de seguranca do Falco

# Detectar execucao de shell em containers
- rule: Terminal shell in container
  desc: >
    Detecta quando um usuario inicia um shell interativo dentro de um container.
    Isso pode indicar acesso nao autorizado ou activity de atacante.
  condition: >
    evt.type = execve and container and proc.tty != 0
    and not proc.name in (falco_allowed_shells)
  output: >
    Shell interativo executado em container
    (user=%user.name user_id=%user.uid command=%proc.cmdline
     container_id=%container.id container_name=%container.name
     image=%container.image.repository:%container.image.tag
     parent=%proc.pname terminal=%proc.tty)
  priority: WARNING
  tags: [container, shell, mitre_execution]

# Detectar acesso a /etc/shadow
- rule: Read sensitive file untrusted
  desc: Detecta processos nao confiaveis lendo arquivos sensiveis
  condition: >
    open_read and container and
    (fd.name = /etc/shadow or fd.name = /etc/passwd) and
    not proc.name in (falco_allowed_readers)
  output: >
    Arquivo sensivel lido por processo nao confiavel
    (file=%fd.name user=%user.name command=%proc.cmdline
     container_id=%container.id container_name=%container.name
     image=%container.image.repository:%container.image.tag)
  priority: CRITICAL
  tags: [filesystem, mitre_credential_access]

# Detectar conexao de rede incomum
- rule: Unexpected outbound connection
  desc: Detecta conexoes de rede de saida para IPs nao autorizados
  condition: >
    outbound and container and
    not (fd.rip in (falco_allowed_outbound_ips))
  output: >
    Conexao de rede nao autorizada detectada
    (connection=%fd.name user=%user.name command=%proc.cmdline
     container_id=%container.id container_name=%container.name
     image=%container.image.repository:%container.image.tag
     dest_ip=%fd.rip dest_port=%fd.rport)
  priority: WARNING
  tags: [network, mitre_command_and_control]

# Detectar criptomineracao
- rule: Possible cryptocurrency mining
  desc: Detecta processos que podem ser mineradores de criptomoeda
  condition: >
    spawned_process and container and
    (proc.name in (cryptominer_names) or
     proc.cmdline contains "stratum" or
     proc.cmdline contains "cryptonight" or
     proc.cmdline contains "-o pool")
  output: >
    Possivel minerador de criptomoeda detectado
    (process=%proc.name command=%proc.cmdline
     user=%user.name container_id=%container.id
     container_name=%container.name)
  priority: CRITICAL
  tags: [process, cryptomining, mitre_impact]

# Detectar montagem de filesystem
- rule: Container Drift Detected
  desc: Detecta execucao de binarios que nao existiam quando o container iniciou
  condition: >
    evt.type = execve and container and
    not proc.name in (falco_allowed_executables) and
    not proc.vpid in (falco_allowed_vpid)
  output: >
    Binario executado que nao estava presente na imagem do container
    (process=%proc.name command=%proc.cmdline
     container_id=%container.id container_name=%container.name
     image=%container.image.repository:%container.image.tag)
  priority: CRITICAL
  tags: [container, drift, mitre_execution]
```

### 4.3 Regras Customizadas

```yaml
# Regras customizadas para aplicacao especifica
# /etc/falco/rules.d/custom-rules.yaml

# Detectar acesso a API admin sem autenticacao adequada
- rule: Admin API access without proper auth
  desc: Detecta acessos a endpoints de administracao
  condition: >
    evt.type = connect and container and
    fd.rport = 8443 and
    container.name = "api-gateway"
  output: >
    Acesso detectado na API de administracao
    (source_ip=%fd.lip dest_port=%fd.rport
     container_name=%container.name process=%proc.name)
  priority: INFO
  tags: [api, admin, custom]

# Detectar manipulacao de arquivos de configuracao
- rule: Config file modification
  desc: Detecta modificacoes em arquivos de configuracao criticos
  condition: >
    modify and container and
    (fd.name endswith .conf or fd.name endswith .yaml or fd.name endswith .yml) and
    not proc.name in (falco_allowed_config_writers)
  output: >
    Arquivo de configuracao modificado
    (file=%fd.name user=%user.name command=%proc.cmdline
     container_id=%container.id container_name=%container.name)
  priority: WARNING
  tags: [filesystem, config, mitre_persistence]

# Detectar exfiltracao de dados
- rule: Large outbound data transfer
  desc: Detecta transferencias grandes de dados para fora do cluster
  condition: >
    outbound and container and
    fd.bytes > 104857600 and
    not (fd.rip in (falco_allowed_outbound_ips))
  output: >
    Possivel exfiltracao de dados detectada
    (bytes=%fd.bytes dest_ip=%fd.rip dest_port=%fd.rport
     process=%proc.name container_name=%container.name
     user=%user.name)
  priority: CRITICAL
  tags: [network, exfiltration, mitre_exfiltration]
```

### 4.4 Gestao de Alertas e Integracao

```yaml
# docker-compose.yml — Falco com integracoes
version: '3.8'

services:
  falco:
    image: falcosecurity/falco:latest
    container_name: falco
    privileged: true
    volumes:
      - /var/run/docker.sock:/host/var/run/docker.sock
      - /proc:/host/proc:ro
      - /etc:/host/etc:ro
      - ./falco_rules.yaml:/etc/falco/falco_rules.yaml:ro
      - ./custom-rules.yaml:/etc/falco/rules.d/custom-rules.yaml:ro
      - ./falco.yaml:/etc/falco/falco.yaml:ro
    environment:
      - FALCO_GRPC_ENABLED=true
      - FALCO_GRPC_BIND_ADDRESS=0.0.0.0:5060
    command:
      - /usr/bin/falco
      - --gvisor
      - --modern-bpf
      - --cri-enabled

  falcosidekick:
    image: falcosecurity/falcosidekick:latest
    container_name: falcosidekick
    ports:
      - "2801:2801"
    environment:
      - DEBUG=false
      # Slack
      - SLACK_WEBHOOKURL=https://hooks.slack.com/services/xxx/yyy/zzz
      - SLACK_CHANNEL=#security-alerts
      - SLACK_USERNAME=Falco
      - SLACK_FOOTER=Falco Security Alert
      # PagerDuty
      - PAGERDUTY_ENABLED=true
      - PAGERDUTY_ROUTINGKEY=your-routing-key
      # Elasticsearch
      - ELASTICSEARCH_ENABLED=true
      - ELASTICSEARCH_HOST=elasticsearch
      - ELASTICSEARCH_PORT=9200
      - ELASTICSEARCH_INDEX=falco-alerts
      # Webhook customizado
      - WEBHOOK_ENABLED=true
      - WEBHOOK_URL=http://incident-response:8080/api/alerts
      - WEBHOOK_METHOD=POST
    command:
      - /usr/bin/falcosidekick
      - -c
      - /etc/falcosidekick/config.yaml
    volumes:
      - ./falcosidekick-config.yaml:/etc/falcosidekick/config.yaml:ro

  falcosidekick-ui:
    image: falcosecurity/falcosidekick-ui:latest
    container_name: falcosidekick-ui
    ports:
      - "2802:2801"
    environment:
      - FALCOSIDEKICK_URL=http://falcosidekick:2801
```

```yaml
# falcosidekick-config.yaml — Configuracao de integracoes
slack:
  webhookurl: "https://hooks.slack.com/services/xxx/yyy/zzz"
  channel: "#security-alerts"
  username: "Falco"
  footer: "Falco Security Alert"
  icon: "https://falco.org/img/logo/falco-logo.png"
  outputformat: "all"
  minimumpriority: "warning"
  messageformat: "alert: {rule.output}"
  actions:
    - "slack:high:critical"

pagerduty:
  enabled: true
  routingKey: "your-routing-key"
  minimumpriority: "critical"

elasticsearch:
  enabled: true
  hostport: "http://elasticsearch:9200"
  index: "falco-alerts-%Y.%m.%d"
  minimumpriority: "warning"

webhook:
  enabled: true
  url: "http://incident-response:8080/api/alerts"
  method: POST
  headers:
    Authorization: "Bearer ${INCIDENT_RESPONSE_TOKEN}"
    Content-Type: "application/json"
  minimumpriority: "warning"
```

---

## 5. Prometheus e Grafana para Seguranca

### 5.1 Metricas de Seguranca

Prometheus e ideal para coleta de metricas de seguranca em tempo real. Com o Grafana,
e possivel criar dashboards visuais que fornecem visibilidade imediata.

```python
# security_metrics.py — Exposicao de metricas de seguranca para Prometheus
from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server
from prometheus_client.core import REGISTRY
import time
import random


# Contadores
login_attempts_total = Counter(
    'security_login_attempts_total',
    'Total de tentativas de login',
    ['method', 'outcome', 'source_type']
)

failed_logins_total = Counter(
    'security_failed_logins_total',
    'Total de logins falhos',
    ['reason', 'source_ip_country']
)

blocked_requests_total = Counter(
    'security_blocked_requests_total',
    'Total de requisicoes bloqueadas pelo WAF',
    ['rule_id', 'action']
)

security_incidents_total = Counter(
    'security_incidents_total',
    'Total de incidentes de seguranca detectados',
    ['severity', 'category', 'status']
)

data_access_total = Counter(
    'security_data_access_total',
    'Total de acessos a dados sensiveis',
    ['data_classification', 'operation', 'user_role']
)

# Gauges
active_sessions = Gauge(
    'security_active_sessions',
    'Numero ativo de sessoes de usuario'
)

blocked_ips_count = Gauge(
    'security_blocked_ips',
    'Numero de IPs bloqueados'
)

vulnerabilities_open = Gauge(
    'security_vulnerabilities_open',
    'Numero de vulnerabilidades abertas',
    ['severity']
)

mean_time_to_detect = Gauge(
    'security_mttd_seconds',
    'Tempo medio para detectar um incidente em segundos'
)

mean_time_to_respond = Gauge(
    'security_mttr_seconds',
    'Tempo medio para responder a um incidente em segundos'
)

# Histogramas
request_duration_seconds = Histogram(
    'security_request_duration_seconds',
    'Duracao das requisicoes de seguranca',
    ['endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

auth_latency_seconds = Histogram(
    'security_auth_latency_seconds',
    'Latencia de autenticacao',
    ['method'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Summary
risk_score_summary = Summary(
    'security_risk_score',
    'Distribuicao de risk scores calculados',
    ['category']
)


class SecurityMetricsCollector:
    """Coletor de metricas de seguranca."""

    def __init__(self):
        self.login_attempts = login_attempts_total
        self.failed_logins = failed_logins_total
        self.blocked_requests = blocked_requests_total
        self.incidents = security_incidents_total
        self.data_access = data_access_total

    def record_login_attempt(self, method, outcome, source_type):
        self.login_attempts.labels(
            method=method, outcome=outcome, source_type=source_type
        ).inc()

    def record_failed_login(self, reason, source_ip_country="unknown"):
        self.failed_logins.labels(
            reason=reason, source_ip_country=source_ip_country
        ).inc()

    def record_blocked_request(self, rule_id, action):
        self.blocked_requests.labels(rule_id=rule_id, action=action).inc()

    def record_incident(self, severity, category, status):
        self.incidents.labels(
            severity=severity, category=category, status=status
        ).inc()

    def record_data_access(self, classification, operation, user_role):
        self.data_access.labels(
            data_classification=classification,
            operation=operation,
            user_role=user_role,
        ).inc()

    def update_active_sessions(self, count):
        active_sessions.set(count)

    def update_blocked_ips(self, count):
        blocked_ips_count.set(count)

    def update_vulnerabilities(self, severity, count):
        vulnerabilities_open.labels(severity=severity).set(count)

    def update_mttd(self, seconds):
        mean_time_to_detect.set(seconds)

    def update_mttr(self, seconds):
        mean_time_to_respond.set(seconds)

    def record_auth_latency(self, method, duration):
        auth_latency_seconds.labels(method=method).observe(duration)

    def record_risk_score(self, category, score):
        risk_score_summary.labels(category=category).observe(score)
```

### 5.2 Regras de Alerta do Prometheus

```yaml
# prometheus/alert-rules/security-alerts.yaml
groups:
  - name: security_alerts
    interval: 30s
    rules:
      # Brute force detection
      - alert: BruteForceDetected
        expr: |
          rate(security_failed_logins_total[5m]) > 0.1
        for: 2m
        labels:
          severity: high
          category: authentication
        annotations:
          summary: "Possivel ataque de brute force detectado"
          description: >
            Taxa de tentativas de login falhas acima do normal nos ultimos 5 minutos.
            Atual: {{ $value }} tentativas/segundo.
          runbook_url: "https://wiki.internal/security/runbooks/brute-force"

      # High number of blocked requests
      - alert: HighBlockedRequestsRate
        expr: |
          rate(security_blocked_requests_total[5m]) > 10
        for: 5m
        labels:
          severity: medium
          category: waf
        annotations:
          summary: "Alta taxa de requisicoes bloqueadas pelo WAF"
          description: >
            A WAF esta bloqueando mais de 10 requisicoes por segundo.
            Isso pode indicar um ataque DDoS ou scanning de vulnerabilidades.

      # Critical vulnerability detected
      - alert: CriticalVulnerabilityDetected
        expr: |
          security_vulnerabilities_open{severity="critical"} > 0
        for: 1m
        labels:
          severity: critical
          category: vulnerability
        annotations:
          summary: "Vulnerabilidade critica aberta detectada"
          description: >
            Existe {{ $value }} vulnerabilidade(s) critica(s) aberta(s)
            que precisa(m) de atencao imediata.

      # Anomalous data access
      - alert: AnomalousDataAccess
        expr: |
          rate(security_data_access_total{data_classification="pii"}[1h]) > 100
        for: 30m
        labels:
          severity: high
          category: data_access
        annotations:
          summary: "Acesso anomalous a dados PII detectado"
          description: >
            Taxa de acesso a dados PII esta significativamente acima do normal.
            Verificar possivel exfiltracao de dados.

      # MTTR too high
      - alert: MTTRTooHigh
        expr: |
          security_mttr_seconds > 3600
        for: 5m
        labels:
          severity: medium
          category: operations
        annotations:
          summary: "Tempo medio de resposta a incidentes muito alto"
          description: >
            MTTR atual: {{ $value | humanizeDuration }}.
            O tempo medio para responder a incidentes esta acima de 1 hora.

      # Login from unusual geo
      - alert: UnusualGeoLogin
        expr: |
          sum by (source_ip_country) (
            rate(security_failed_logins_total{source_ip_country!="BR"}[1h])
          ) > 5
        for: 15m
        labels:
          severity: medium
          category: authentication
        annotations:
          summary: "Tentativas de login de localizacao incomum"
          description: >
            Detectadas {{ $value }} tentativas de login falhas por hora
            do pais {{ $labels.source_ip_country }}.

      # High risk score
      - alert: HighRiskScoreDetected
        expr: |
          security_risk_score{category="authentication"} > 0.8
        for: 1m
        labels:
          severity: critical
          category: risk
        annotations:
          summary: "Risk score de autenticacao criticamente alto"
          description: >
            O risk score de autenticacao atingiu {{ $value }}.
            Investigacao imediata necessaria.
```

### 5.3 Configuracao do Prometheus para Seguranca

```yaml
# prometheus.yml — Configuracao do Prometheus para seguranca
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: "production"
    team: "security"

rule_files:
  - "alert-rules/*.yaml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

scrape_configs:
  # Metricas de seguranca das aplicacoes
  - job_name: "security-metrics"
    static_configs:
      - targets:
          - "auth-api:8080"
          - "api-gateway:8081"
          - "waf:8082"
    metrics_path: "/metrics/security"
    scrape_interval: 10s

  # Metricas do Prometheus
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  # Metricas do node-exporter
  - job_name: "node"
    static_configs:
      - targets:
          - "node1:9100"
          - "node2:9100"
          - "node3:9100"
    relabel_configs:
      - source_labels: [__address__]
        regex: "(.*):9100"
        target_label: instance

  # Metricas do Falco
  - job_name: "falco"
    static_configs:
      - targets:
          - "falco:8765"
    metrics_path: "/metrics"

  # Metricas do Wazuh
  - job_name: "wazuh"
    static_configs:
      - targets:
          - "wazuh:9199"
    metrics_path: "/prometheus"

  # Metricas do Elasticsearch
  - job_name: "elasticsearch"
    static_configs:
      - targets:
          - "elasticsearch:9200"
    metrics_path: "/_nodes/stats/prometheus"
```

### 5.4 Dashboard de Seguranca no Grafana

```json
{
  "dashboard": {
    "title": "Security Operations Dashboard",
    "uid": "security-ops",
    "tags": ["security", "operations"],
    "timezone": "browser",
    "refresh": "30s",
    "panels": [
      {
        "title": "Incidentes Ativos",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "sum(security_incidents_total{status=\"open\"})",
            "legendFormat": "Incidentes Abertos"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 5 },
                { "color": "red", "value": 10 }
              ]
            }
          }
        }
      },
      {
        "title": "MTTD (Tempo Medio para Detectar)",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 6, "y": 0 },
        "targets": [
          {
            "expr": "security_mttd_seconds",
            "legendFormat": "MTTD"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 300 },
                { "color": "red", "value": 3600 }
              ]
            }
          }
        }
      },
      {
        "title": "MTTR (Tempo Medio para Responder)",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 12, "y": 0 },
        "targets": [
          {
            "expr": "security_mttr_seconds",
            "legendFormat": "MTTR"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 1800 },
                { "color": "red", "value": 3600 }
              ]
            }
          }
        }
      },
      {
        "title": "Vulnerabilidades Abertas",
        "type": "stat",
        "gridPos": { "h": 4, "w": 6, "x": 18, "y": 0 },
        "targets": [
          {
            "expr": "sum(security_vulnerabilities_open)",
            "legendFormat": "Total"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 10 },
                { "color": "red", "value": 25 }
              ]
            }
          }
        }
      },
      {
        "title": "Tentativas de Login (24h)",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 4 },
        "targets": [
          {
            "expr": "rate(security_login_attempts_total[5m])",
            "legendFormat": "{{ outcome }} - {{ method }}"
          }
        ]
      },
      {
        "title": "Requisicoes Bloqueadas",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 4 },
        "targets": [
          {
            "expr": "rate(security_blocked_requests_total[5m])",
            "legendFormat": "{{ rule_id }} - {{ action }}"
          }
        ]
      }
    ]
  }
}
```

---

## 6. Cloud-Native Security Monitoring

### 6.1 AWS CloudTrail + GuardDuty

AWS CloudTrail registra chamadas de API da AWS, enquanto GuardDuty usa machine learning
para detectar atividades maliciosas.

```yaml
# terraform/cloudtrail.tf — Configuracao do CloudTrail para seguranca
resource "aws_cloudtrail" "security_trail" {
  name                          = "security-audit-trail"
  s3_bucket_name                = aws_s3_bucket.security_logs.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                = true
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type = "AWS::S3::Object"
      values = ["${aws_s3_bucket.security_logs.arn}/"]
    }

    data_resource {
      type = "AWS::Lambda::Function"
      values = ["arn:aws:lambda"]
    }
  }

  cloud_watch_logs_group_arn = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn  = aws_iam_role.cloudtrail_cloudwatch.arn

  tags = {
    Environment = "production"
    Purpose     = "security-audit"
  }
}

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/security"
  retention_in_days = 365

  tags = {
    Environment = "production"
    Purpose     = "security-audit"
  }
}

# CloudWatch Alarm para CloudTrail
resource "aws_cloudwatch_metric_alarm" "root_login" {
  alarm_name          = "root-login-detected"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RootLoginEvents"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alarme quando root faz login na conta"
  alarm_actions       = [aws_sns_topic.security_alerts.arn]

  dimensions = {
    TrailName = aws_cloudtrail.security_trail.name
  }
}

# GuardDuty
resource "aws_guardduty_detector" "main" {
  enable = true

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    cloudtrail {
      enable = true
    }
  }

  finding_publishing_frequency = "FIFTEEN_MINUTES"
}

# EventBridge rule para incidentes do GuardDuty
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "guardduty-critical-findings"
  description = "Captura findings criticos do GuardDuty"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
    }
  })
}

resource "aws_cloudwatch_event_target" "guardduty_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.security_alerts.arn
}
```

### 6.2 Azure Sentinel

Azure Sentinel e o SIEM cloud-native da Microsoft, integrado nativamente com o ecossistema
Azure.

```yaml
# ARM template — Azure Sentinel workspace
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "resources": [
    {
      "type": "Microsoft.OperationalInsights/workspaces",
      "apiVersion": "2022-10-01",
      "name": "sentinel-security-workspace",
      "location": "brazilsouth",
      "properties": {
        "sku": {
          "name": "PerGB2018"
        },
        "retentionInDays": 90,
        "features": {
          "enableLogAccessUsingOnlyResourcePermissions": true
        }
      }
    },
    {
      "type": "Microsoft.SecurityInsights/onboardingStates",
      "apiVersion": "2023-12-01-preview",
      "name": "sentinel-security-workspace/onboardingState",
      "properties": {
        "customerManagedKey": false
      }
    }
  ]
}
```

### 6.3 GCP Chronicle (Security Operations)

```yaml
# Configuracao do Google Cloud para Chronicle
# gcp-security-monitoring.yaml
apiVersion: monitoring.googleapis.com/v3
kind: AlertPolicy
metadata:
  name: security-threat-detected
  labels:
    severity: critical
spec:
  displayName: "Threat Detected in GCP Logs"
  conditions:
    - displayName: "High severity audit log"
      conditionMatchedLog:
        filter: >
          resource.type="gce_instance"
          logName="projects/my-project/logs/cloudaudit.googleapis.com%2Factivity"
          severity>=ERROR
        aggregation:
          alignmentPeriod: 300s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_SUM
  combiner: OR
  notificationChannels:
    - "projects/my-project/notificationChannels/1234567890"
  alertStrategy:
    autoClose: 1800s
```

---

## 7. Incident Detection

### 7.1 Design de Alertas

Um sistema de alertas eficaz precisa equilibrar sensibilidade com especificidade. Alertas
muito sensativos geram fadiga de alertas (alert fatigue), enquanto alertas muito
especificos podem deixar ameacas passarem despercebidas.

**Principios de design de alertas:**

1. **Acaoabilidade**: Cada alerta deve indicar uma acao clara a ser tomada
2. **Contexto suficiente**: O operador deve entender o que aconteceu sem consultar
   outros sistemas
3. **Severidade correta**: Nao todos os alertas sao criticos — classifique adequadamente
4. **Supressao inteligente**: Evite alertas duplicados durante manutencao programada
5. **Escalacao progressiva**: Se nao atendido, o alerta deve escalar automaticamente

### 7.2 Classificacao de Severidade

```yaml
# severity-classification.yaml — Matriz de classificacao de severidade
severity_levels:
  P1_CRITICAL:
    description: "Ameaca ativa com impacto imediato nos dados ou servicos"
    response_time: "15 minutos"
    escalation: "Imediato para CISO e equipe de seguranca"
    examples:
      - "Ransomware detectado em producao"
      - "Exfiltracao de dados em andamento"
      - "Comprometimento de credenciais de administrador"
      - "Acesso nao autorizado a dados de clientes"

  P2_HIGH:
    description: "Atividade suspeita significativa que requer investigacao urgente"
    response_time: "1 hora"
    escalation: "Equipe de seguranca on-call"
    examples:
      - "Brute force bem-sucedido em conta de administrador"
      - "Deteccao de malware em endpoint critico"
      - "Vulnerabilidade critica sem patch disponivel"
      - "Configuracao de seguranca desabilitada"

  P3_MEDIUM:
    description: "Anomalia detectada que pode indicar problema de seguranca"
    response_time: "4 horas"
    escalation: "Equipe de seguranca durante horario comercial"
    examples:
      - "Tentativas de login falhas acima do normal"
      - "Acesso a recursos fora do padrao"
      - "Certificado de TLS proximo do vencimento"
      - "Mudanca nao autorizada em configuracao"

  P4_LOW:
    description: "Evento de interesse que nao requer acao imediata"
    response_time: "24 horas"
    escalation: "Revisao no proximo ciclo de seguranca"
    examples:
      - "Atualizacao de politica de seguranca"
      - "Acesso a recursos de desenvolvimento"
      - "Novo dispositivo conectado a rede"
      - "Relatorio de conformidade pendente"
```

### 7.3 Procedimentos de Escalacao

```yaml
# escalation-procedures.yaml
escalation_policies:
  security_incident:
    levels:
      - level: 1
        name: "Equipe de Seguranca On-Call"
        notify:
          - method: "pagerduty"
            service: "security-oncall"
            delay: "0m"
          - method: "slack"
            channel: "#security-incidents"
            delay: "0m"
        acknowledge_timeout: "15m"

      - level: 2
        name: "Lider de Seguranca"
        notify:
          - method: "phone_call"
            target: "security_lead_phone"
            delay: "15m"
          - method: "email"
            target: "security_lead_email"
            delay: "15m"
        acknowledge_timeout: "15m"

      - level: 3
        name: "CISO"
        notify:
          - method: "phone_call"
            target: "ciso_phone"
            delay: "30m"
          - method: "sms"
            target: "ciso_phone"
            delay: "30m"
        acknowledge_timeout: "15m"

      - level: 4
        name: "Diretoria Executiva"
        notify:
          - method: "email"
            target: "exec-team@company.com"
            delay: "45m"
          - method: "phone_call"
            target: "cto_phone"
            delay: "45m"
        acknowledge_timeout: "30m"

    repeat_interval: "1h"
    auto_resolve_after: "24h"
```

### 7.4 Pipeline de Alertas Completa

```yaml
# docker-compose.yml — Pipeline de alertas completa
version: '3.8'

services:
  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - ./templates:/etc/alertmanager/templates:ro
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
    volumes:
      - alertmanager-data:/alertmanager

  grafana-oncall:
    image: grafana/oncall:latest
    container_name: grafana-oncall
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgres://oncall:password@postgres:5432/oncall
      - REDIS_URL=redis://redis:6379/0
      - SLACK_CLIENT_ID=${SLACK_CLIENT_ID}
      - SLACK_CLIENT_SECRET=${SLACK_CLIENT_SECRET}
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    container_name: oncall-postgres
    environment:
      - POSTGRES_DB=oncall
      - POSTGRES_USER=oncall
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: oncall-redis

  # Webhook receiver para alertas customizados
  alert-webhook:
    build: ./alert-webhook
    container_name: alert-webhook
    ports:
      - "8081:8080"
    environment:
      - PAGERDUTY_TOKEN=${PAGERDUTY_TOKEN}
      - SLACK_WEBHOOK=${SLACK_WEBHOOK}
      - JIRA_URL=${JIRA_URL}
      - JIRA_TOKEN=${JIRA_TOKEN}

volumes:
  alertmanager-data:
  postgres-data:
```

```yaml
# alertmanager.yml — Configuracao do Alertmanager
global:
  resolve_timeout: 5m
  slack_api_url: "${SLACK_WEBHOOK_URL}"
  pagerduty_url: "https://events.pagerduty.com/v2/enqueue"

templates:
  - "/etc/alertmanager/templates/*.tmpl"

route:
  receiver: "default"
  group_by: ["alertname", "severity", "category"]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  routes:
    - match:
        severity: critical
      receiver: "critical-incidents"
      group_wait: 10s
      repeat_interval: 15m
    - match:
        severity: high
      receiver: "high-priority"
      group_wait: 30s
      repeat_interval: 1h
    - match:
        severity: medium
      receiver: "medium-priority"
      group_interval: 30m
      repeat_interval: 4h
    - match:
        category: compliance
      receiver: "compliance-team"
      repeat_interval: 24h

receivers:
  - name: "default"
    slack_configs:
      - channel: "#security-alerts"
        title: '{{ template "slack.default.title" . }}'
        text: '{{ template "slack.default.text" . }}'
        send_resolved: true

  - name: "critical-incidents"
    pagerduty_configs:
      - service_key: "${PAGERDUTY_CRITICAL_KEY}"
        severity: critical
        description: '{{ .GroupLabels.alertname }}'
        details:
          firing: '{{ .Alerts.Firing | len }}'
          resolved: '{{ .Alerts.Resolved | len }}'
          dashboard: "https://grafana.internal/d/security-ops"
    slack_configs:
      - channel: "#security-critical"
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'
        color: "#FF0000"

  - name: "high-priority"
    pagerduty_configs:
      - service_key: "${PAGERDUTY_HIGH_KEY}"
        severity: warning
    slack_configs:
      - channel: "#security-alerts"
        title: 'HIGH: {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'
        color: "#FF8800"

  - name: "medium-priority"
    slack_configs:
      - channel: "#security-monitoring"
        title: 'MEDIUM: {{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'
        color: "#FFCC00"

  - name: "compliance-team"
    email_configs:
      - to: "compliance@company.com"
        from: "alertmanager@company.com"
        smarthost: "smtp.company.com:587"
        subject: "Compliance Alert: {{ .GroupLabels.alertname }}"
        text: '{{ .CommonAnnotations.description }}'

inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: high
    equal: ["alertname", "category"]
  - source_match:
      severity: high
    target_match:
      severity: medium
    equal: ["alertname", "category"]
```

---

## 8. Threat Hunting

### 8.1 Metodologia de Caça ao Ameacas

Threat hunting e a pratica de buscar proativamente ameacas em uma rede, em vez de esperar
alertas automaticos. O caçador assume que o inimigo ja esta presente e busca evidencias
de sua atividade.

**Ciclo de Threat Hunting:**

```
1. Hipotese    → "O que poderia estar acontecendo?"
2. Coleta      → "Que dados precisamos para testar a hipotese?"
3. Analise     → "Os dados suportam ou refutam a hipotese?"
4. Descoberta  → "O que encontramos? E novidade?"
5. Melhoria    → "Como melhorar nossas deteccoes?"
```

### 8.2 Exemplos de Consultas

```python
# threat_hunting_queries.py — Consultas de threat hunting
"""
Exemplos de consultas para different SIEMs e ferramentas de analise.
Cada consulta testa uma hipotese especifica de ameaca.
"""


class ThreatHuntingQueries:
    """Colecao de consultas para threat hunting."""

    @staticmethod
    def hunting_lateral_movement_elk():
        """
        Hipotese: Um atacante esta se movendo lateralmente na rede
        apos comprometer uma maquina.
        """
        return {
            "name": "Lateral Movement Detection",
            "description": "Detecta sinais de movimento lateral na rede",
            "query": """
                {
                  "query": {
                    "bool": {
                      "must": [
                        { "term": { "event.category": "authentication" } },
                        { "terms": { "event.type": ["logon_success", "logon_type_3"] } }
                      ],
                      "should": [
                        { "range": { "source.geo.country_name": { "minimum_should_match": 1 } } },
                        { "term": { "winlog.event_data.LogonType": "3" } },
                        { "term": { "event.outcome": "success" } }
                      ]
                    }
                  },
                  "aggs": {
                    "by_source_user": {
                      "terms": { "field": "user.name.keyword", "size": 20 },
                      "aggs": {
                        "by_target_host": {
                          "terms": { "field": "destination.host.keyword", "size": 20 },
                          "aggs": {
                            "unique_sources": {
                              "cardinality": { "field": "source.host.keyword" }
                            }
                          }
                        }
                      }
                    },
                    "timeline": {
                      "date_histogram": {
                        "field": "@timestamp",
                        "fixed_interval": "1h"
                      }
                    }
                  }
                }
            """,
            "expected_findings": [
                "Um usuario autenticando em hosts incomuns",
                "Multiplos hosts de origem para o mesmo usuario",
                "Padrao de autenticacao em cascata (A->B->C->D)"
            ]
        }

    @staticmethod
    def hunting_data_exfiltration():
        """
        Hipotese: Dados estao sendo exfiltrados da rede
        atraves de conexões HTTPS para IPs externos.
        """
        return {
            "name": "Data Exfiltration Hunting",
            "description": "Detecta possivel exfiltracao de dados",
            "spl_query": """
                index=network dest_port=443 src_ip=INTERNAL*
                | where bytes_out > 10485760
                | stats sum(bytes_out) as total_bytes_out
                       values(dest_ip) as dest_ips
                       dc(dest_ip) as unique_dest_ips
                       by src_ip, user
                | where unique_dest_ips > 3 AND total_bytes_out > 104857600
                | sort -total_bytes_out
            """,
            "elasticsearch_query": """
                {
                  "query": {
                    "bool": {
                      "must": [
                        { "term": { "event.category": "network" } },
                        { "term": { "destination.port": 443 } },
                        { "range": { "destination.bytes": { "gte": 1048576 } } }
                      ],
                      "must_not": [
                        { "terms": { "destination.ip": ["10.0.0.0/8"] } }
                      ]
                    }
                  },
                  "aggs": {
                    "by_source": {
                      "terms": { "field": "source.ip.keyword", "size": 20 },
                      "aggs": {
                        "total_bytes": { "sum": { "field": "destination.bytes" } },
                        "unique_destinations": { "cardinality": { "field": "destination.ip.keyword" } },
                        "top_destinations": { "terms": { "field": "destination.ip.keyword", "size": 10 } }
                      }
                    }
                  }
                }
            """,
            "expected_findings": [
                "Uploads grandes para IPs externos",
                "Multiplos destinos externos a partir de uma mesma maquina",
                "Transferencias de dados em horarios incomuns"
            ]
        }

    @staticmethod
    def hunting_persistence():
        """
        Hipotese: Um atacante instalou mecanismos de persistencia
        no sistema.
        """
        return {
            "name": "Persistence Mechanism Hunting",
            "description": "Detecta mecanismos de persistencia de ameacas",
            "spl_query": """
                index=windows sourcetype=WinEventLog:Security
                EventCode IN (4688, 4697, 4698, 4702, 7045)
                | eval is_suspicious=case(
                    match(CommandLine, "(?i)(schtasks|taskschd)"), "scheduled_task",
                    match(CommandLine, "(?i)(reg add|regsvr32|mshta)"), "registry_modification",
                    match(CommandLine, "(?i)(wmic|powershell.*-enc)"), "wmi_abuse",
                    1=1, "normal"
                  )
                | where is_suspicious!="normal"
                | stats count by host, user, is_suspicious, CommandLine
                | sort -count
            """,
            "osquery_query": """
                SELECT
                    p.name as process_name,
                    p.cmdline as command_line,
                    u.username,
                    p.start_time,
                    t.name as parent_process
                FROM processes p
                JOIN users u ON p.uid = u.uid
                JOIN processes t ON p.parent = t.pid
                WHERE (
                    p.cmdline LIKE '%schtasks%' OR
                    p.cmdline LIKE '%reg add%' OR
                    p.cmdline LIKE '%powershell%-enc%' OR
                    p.cmdline LIKE '%wmic%' OR
                    p.cmdline LIKE '%mshta%'
                )
                AND p.start_time > datetime('now', '-24 hours')
                ORDER BY p.start_time DESC;
            """
        }

    @staticmethod
    def hunting_command_and_control():
        """
        Hipotese: Um malware esta se comunicando com servidores
        C2 atraves de DNS ou HTTPS.
        """
        return {
            "name": "C2 Communication Hunting",
            "description": "Detecta comunicacao com servidores de comando e controle",
            "query": """
                {
                  "query": {
                    "bool": {
                      "should": [
                        {
                          "bool": {
                            "must": [
                              { "term": { "event.category": "network" } },
                              { "range": { "dns.question.name.length": { "gte": 50 } } },
                              { "terms": { "dns.question.type": ["A", "AAAA"] } }
                            ]
                          }
                        },
                        {
                          "bool": {
                            "must": [
                              { "term": { "event.category": "network" } },
                              { "term": { "destination.port": 443 } },
                              { "range": { "network.packets": { "lte": 10 } } },
                              { "range": { "destination.bytes": { "gte": 1024 } } }
                            ]
                          }
                        }
                      ]
                    }
                  },
                  "aggs": {
                    "suspicious_domains": {
                      "terms": { "field": "dns.question.name.keyword", "size": 50 }
                    },
                    "long_dns_names": {
                      "histogram": {
                        "field": "dns.question.name.length",
                        "interval": 10
                      }
                    }
                  }
                }
            """
        }
```

### 8.3 Automacao com Jupyter Notebooks

```python
# threat_hunting.ipynb — Notebook de Threat Hunting
"""
Este notebook demonstra como automatizar threat hunting
usando Jupyter notebooks e Python.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta
import json

# Conexao ao Elasticsearch
es = Elasticsearch(
    ["https://siem-internal:9200"],
    basic_auth=("elastic", "password"),
    verify_certs=True,
    ca_certs="/etc/elk/certs/ca.crt"
)

# Funcao auxiliar para executar queries
def execute_query(index, query, size=10000):
    """Executa uma query no Elasticsearch e retorna um DataFrame."""
    result = es.search(index=index, body=query, size=size)
    hits = result["hits"]["hits"]
    if not hits:
        return pd.DataFrame()
    return pd.DataFrame([hit["_source"] for hit in hits])

# ============================================================
# CÉLULA 1: Analise de tentativas de login
# ============================================================

query_logins = {
    "query": {
        "bool": {
            "must": [
                {"term": {"event.category": "authentication"}},
                {"range": {"@timestamp": {"gte": "now-24h"}}}
            ]
        }
    },
    "aggs": {
        "login_timeline": {
            "date_histogram": {
                "field": "@timestamp",
                "calendar_interval": "1h"
            },
            "aggs": {
                "by_outcome": {
                    "terms": {"field": "event.outcome.keyword"}
                }
            }
        },
        "top_failing_ips": {
            "terms": {
                "field": "source.ip.keyword",
                "size": 20,
                "order": {"_count": "desc"}
            },
            "aggs": {
                "failure_rate": {
                    "bucket_script": {
                        "buckets_path": {"total": "_count"},
                        "script": "params.total"
                    }
                }
            }
        }
    }
}

df_logins = execute_query("security-logs-*", query_logins)

# Visualizacao
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Timeline de logins
if not df_logins.empty:
    timeline = es.search(index="security-logs-*", body=query_logins)["aggregations"]["login_timeline"]["buckets"]
    df_timeline = pd.DataFrame([{"hour": b["key_as_string"], "count": b["doc_count"],
                                  "failures": b["by_outcome"]["buckets"][1]["doc_count"]
                                  if len(b["by_outcome"]["buckets"]) > 1 else 0}
                                 for b in timeline])

    axes[0].plot(df_timeline["hour"], df_timeline["count"], label="Total", marker="o")
    axes[0].plot(df_timeline["hour"], df_timeline["failures"], label="Falhas", marker="x", color="red")
    axes[0].set_title("Tentativas de Login (24h)")
    axes[0].legend()
    axes[0].tick_params(axis='x', rotation=45)

# Top IPs com falhas
top_ips = es.search(index="security-logs-*", body=query_logins)["aggregations"]["top_failing_ips"]["buckets"]
df_ips = pd.DataFrame([{"ip": b["key"], "failures": b["doc_count"]} for b in top_ips[:10]])
axes[1].barh(df_ips["ip"], df_ips["failures"], color="coral")
axes[1].set_title("Top 10 IPs com Mais Falhas")
axes[1].set_xlabel("Numero de Tentativas")

plt.tight_layout()
plt.savefig("login_analysis.png", dpi=150, bbox_inches="tight")
plt.show()

# ============================================================
# CÉLULA 2: Deteccao de anomalias geograficas
# ============================================================

query_geo = {
    "query": {
        "bool": {
            "must": [
                {"term": {"event.outcome": "success"}},
                {"range": {"@timestamp": {"gte": "now-7d"}}}
            ]
        }
    },
    "aggs": {
        "by_country": {
            "terms": {"field": "source.geo.country_name.keyword", "size": 50},
            "aggs": {
                "by_user": {
                    "terms": {"field": "user.name.keyword", "size": 20},
                    "aggs": {
                        "countries": {
                            "cardinality": {"field": "source.geo.country_name.keyword"}
                        }
                    }
                }
            }
        }
    }
}

geo_result = es.search(index="security-logs-*", body=query_geo)
countries = geo_result["aggregations"]["by_country"]["buckets"]

# Identificar usuarios com logins de multiplos paises
print("=== Usuarios com Logins de Multiplos Paises ===")
for country in countries:
    for user in country["by_user"]["buckets"]:
        if user["countries"]["value"] > 1:
            print(f"  Usuario: {user['key']}")
            print(f"  Paises: {user['countries']['value']}")
            print(f"  Ultimo pais: {country['key']}")
            print()

# ============================================================
# CÉLULA 3: Analise de horarios de acesso
# ============================================================

query_hours = {
    "query": {
        "bool": {
            "must": [
                {"term": {"event.outcome": "success"}},
                {"range": {"@timestamp": {"gte": "now-30d"}}}
            ]
        }
    },
    "aggs": {
        "by_hour": {
            "histogram": {
                "field": "event.hour",
                "interval": 1
            }
        }
    }
}

hours_result = es.search(index="security-logs-*", body=query_hours)
hours_data = [{"hour": b["key"], "count": b["doc_count"]}
              for b in hours_result["aggregations"]["by_hour"]["buckets"]]
df_hours = pd.DataFrame(hours_data)

plt.figure(figsize=(12, 5))
plt.bar(df_hours["hour"], df_hours["count"], color="steelblue")
plt.axvspan(0, 7, alpha=0.2, color="red", label="Horario Incomum (0-7h)")
plt.axvspan(19, 24, alpha=0.2, color="red")
plt.title("Distribuicao de Acessos por Hora (Ultimos 30 dias)")
plt.xlabel("Hora do Dia")
plt.ylabel("Numero de Acessos")
plt.legend()
plt.savefig("access_hours_analysis.png", dpi=150, bbox_inches="tight")
plt.show()

# ============================================================
# CÉLULA 4: Relatorio de Threat Hunting
# ============================================================

report = {
    "period": f"{(datetime.now() - timedelta(days=7)).isoformat()} ate {datetime.now().isoformat()}",
    "findings": [],
    "recommendations": []
}

# Analise de IPs com atividade suspeita
suspicious_ips = df_ips[df_ips["failures"] > 100]
if not suspicious_ips.empty:
    report["findings"].append({
        "category": "Brute Force",
        "severity": "HIGH",
        "description": f"{len(suspicious_ips)} IPs com mais de 100 tentativas de login falhas",
        "ips": suspicious_ips["ip"].tolist()
    })
    report["recommendations"].append(
        "Bloquear IPs com mais de 200 tentativas e revisar regras de rate limiting"
    )

# Salvar relatorio
with open("threat_hunting_report.json", "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("Relatorio salvo em threat_hunting_report.json")
print(json.dumps(report, indent=2, ensure_ascii=False))
```

---

## 9. Metrics de Seguranca

### 9.1 MTTD, MTTR e Outras Metrics Essenciais

As metricas de seguranca permitem medir a eficacia do programa de seguranca e justificar
investimentos para a lideranca.

```python
# security_kpi_calculator.py — Calculadora de KPIs de seguranca
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional
import statistics


@dataclass
class Incident:
    """Representa um incidente de seguranca."""
    id: str
    title: str
    severity: str
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    contained_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    category: str = ""
    affected_systems: List[str] = field(default_factory=list)


class SecurityKPICalculator:
    """Calculador de KPIs de seguranca."""

    def __init__(self, incidents: List[Incident]):
        self.incidents = incidents

    def mttd(self) -> float:
        """
        Mean Time to Detect (MTTD) — Tempo medio para detectar um incidente.
        Mede a eficacia da deteccao.
        """
        detection_times = []
        for incident in self.incidents:
            if incident.detected_at and incident.acknowledged_at:
                delta = (incident.acknowledged_at - incident.detected_at).total_seconds()
                detection_times.append(delta)
        return statistics.mean(detection_times) if detection_times else 0

    def mttr(self) -> float:
        """
        Mean Time to Respond (MTTR) — Tempo medio para responder a um incidente.
        Mede a eficiencia da resposta.
        """
        response_times = []
        for incident in self.incidents:
            if incident.detected_at and incident.resolved_at:
                delta = (incident.resolved_at - incident.detected_at).total_seconds()
                response_times.append(delta)
        return statistics.mean(response_times) if response_times else 0

    def mttc(self) -> float:
        """
        Mean Time to Contain (MTTC) — Tempo medio para conter um incidente.
        Mede a velocidade de contensao.
        """
        containment_times = []
        for incident in self.incidents:
            if incident.detected_at and incident.contained_at:
                delta = (incident.contained_at - incident.detected_at).total_seconds()
                containment_times.append(delta)
        return statistics.mean(containment_times) if containment_times else 0

    def incidents_per_month(self) -> float:
        """Media de incidentes por mes."""
        if not self.incidents:
            return 0
        dates = [i.detected_at for i in self.incidents]
        if len(dates) < 2:
            return 0
        period_days = (max(dates) - min(dates)).days
        if period_days == 0:
            return len(self.incidents)
        return (len(self.incidents) / period_days) * 30

    def vulnerability_density(self, total_lines_of_code: int,
                               vulnerabilities_found: int) -> float:
        """
        Densidade de vulnerabilidades — Vulnerabilidades por 1000 linhas de codigo.
        """
        if total_lines_of_code == 0:
            return 0
        return (vulnerabilities_found / total_lines_of_code) * 1000

    def false_positive_rate(self) -> float:
        """
        Taxa de falsos positivos — Alertas que nao eram ameacas reais.
        """
        total_alerts = len(self.incidents)
        false_positives = len([i for i in self.incidents if i.severity == "false_positive"])
        if total_alerts == 0:
            return 0
        return (false_positives / total_alerts) * 100

    def coverage_percentage(self, total_assets: int, monitored_assets: int) -> float:
        """
        Cobertura de monitoramento — Percentual de ativos monitorados.
        """
        if total_assets == 0:
            return 0
        return (monitored_assets / total_assets) * 100

    def patch_compliance_rate(self, total_systems: int,
                               systems_with_critical_patches: int) -> float:
        """
        Taxa de conformidade de patches — Percentual de sistemas com patches criticos.
        """
        if total_systems == 0:
            return 0
        return (systems_with_critical_patches / total_systems) * 100

    def generate_dashboard_data(self) -> dict:
        """Gera dados para o dashboard de metricas de seguranca."""
        return {
            "mttd_seconds": self.mttd(),
            "mttr_seconds": self.mttr(),
            "mttc_seconds": self.mttc(),
            "incidents_per_month": self.incidents_per_month(),
            "false_positive_rate": self.false_positive_rate(),
            "severity_distribution": self._severity_distribution(),
            "category_distribution": self._category_distribution(),
            "trend_data": self._trend_data(),
        }

    def _severity_distribution(self) -> dict:
        """Distribuicao de incidentes por severidade."""
        dist = {}
        for incident in self.incidents:
            sev = incident.severity
            dist[sev] = dist.get(sev, 0) + 1
        return dist

    def _category_distribution(self) -> dict:
        """Distribuicao de incidentes por categoria."""
        dist = {}
        for incident in self.incidents:
            cat = incident.category
            dist[cat] = dist.get(cat, 0) + 1
        return dist

    def _trend_data(self) -> list:
        """Dados de tendencia de incidentes por mes."""
        monthly = {}
        for incident in self.incidents:
            month_key = incident.detected_at.strftime("%Y-%m")
            monthly[month_key] = monthly.get(month_key, 0) + 1
        return [{"month": k, "count": v} for k, v in sorted(monthly.items())]
```

### 9.2 Dashboard de Metricas

```yaml
# grafana/dashboard-security-kpis.json
# Dashboard de KPIs de Seguranca no Grafana
{
  "dashboard": {
    "title": "Security KPIs Dashboard",
    "uid": "security-kpis",
    "tags": ["security", "kpi", "metrics"],
    "panels": [
      {
        "title": "MTTD (Tempo Medio para Detectar)",
        "type": "gauge",
        "gridPos": { "h": 6, "w": 6, "x": 0, "y": 0 },
        "targets": [
          {
            "expr": "security_mttd_seconds",
            "legendFormat": "MTTD"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "min": 0,
            "max": 7200,
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 300 },
                { "color": "orange", "value": 1800 },
                { "color": "red", "value": 3600 }
              ]
            }
          }
        }
      },
      {
        "title": "MTTR (Tempo Medio para Responder)",
        "type": "gauge",
        "gridPos": { "h": 6, "w": 6, "x": 6, "y": 0 },
        "targets": [
          {
            "expr": "security_mttr_seconds",
            "legendFormat": "MTTR"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "s",
            "min": 0,
            "max": 14400,
            "thresholds": {
              "steps": [
                { "color": "green", "value": null },
                { "color": "yellow", "value": 1800 },
                { "color": "orange", "value": 7200 },
                { "color": "red", "value": 10800 }
              ]
            }
          }
        }
      },
      {
        "title": "Incidentes por Mes",
        "type": "timeseries",
        "gridPos": { "h": 8, "w": 12, "x": 0, "y": 6 },
        "targets": [
          {
            "expr": "increase(security_incidents_total[30d])",
            "legendFormat": "{{ severity }}"
          }
        ]
      },
      {
        "title": "Vulnerabilidades Abertas",
        "type": "bargauge",
        "gridPos": { "h": 8, "w": 12, "x": 12, "y": 6 },
        "targets": [
          {
            "expr": "security_vulnerabilities_open",
            "legendFormat": "{{ severity }}"
          }
        ]
      }
    ]
  }
}
```

### 9.3 Pipeline de Metricas Completa

```yaml
# docker-compose.yml — Pipeline de metricas de seguranca
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.49.0
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./alert-rules:/etc/prometheus/alert-rules:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.retention.time=90d
      - --storage.tsdb.retention.size=50GB

  grafana:
    image: grafana/grafana:10.3.1
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/datasources:/etc/grafana/provisioning/datasources:ro

  node-exporter:
    image: prom/node-exporter:v1.7.0
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - --path.procfs=/host/proc
      - --path.sysfs=/host/sys
      - --path.rootfs=/rootfs

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.49.1
    container_name: cadvisor
    ports:
      - "8080:8080"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro

volumes:
  prometheus-data:
  grafana-data:
```

---

## 10. Casos Reais de Seguranca

### 10.1 Target — O Breach que Ignorou Alertas (2013)

O ataque a Target em 2013 e um dos exemplos mais estudados de como alertas de seguranca
ignorados podem levar a catastrofes.

**O que aconteceu:**

Em novembro de 2013, atacantes roubaram dados de 40 milhoes de cartoes de credito e 70
milhoes de registros pessoais de clientes da Target, uma das maiores varejistas dos
Estados Unidos.

**O papel critico do monitoramento ignorado:**

O FireEye, um sistema de seguranca avancado (MDR) instalado nos data centers da Target
em Minneapolis, detectou o ataque e gerou alertas MULTIPLES vezes. O sistema classificou
os alertas como "graves" e os enviou para o Security Operations Center (SOC) em Bangalore,
na India.

Os operadores do SOC em Bangalore revisaram os alertas e os escalaram para a equipe de
seguranca em Minneapolis. No entanto, a equipe em Minneapolis nao tomou nenhuma acao.

**Linha do tempo detalhada:**

```
27 Nov 2013 — FireEye detecta malware (HammerDump/BlackPoison) e envia alerta
28 Nov 2013 — Target recebe outro alerta do FireEye. Sem acao.
30 Nov 2013 — Atacantes instalam malware em 1,800 caixas registradoras.
01 Dec 2013 — FireEye envia alerta CRITICO. Ainda sem resposta.
02 Dec 2013 — Atacantes comecam a roubar dados de cartoes de credito.
12 Dec 2013 — Target e notificada pelo Departamento de Justica.
15 Dec 2013 — Target confirma o breach publicamente.
```

**Causas raiz do fracasso de monitoramento:**

1. **Alert fatigue**: O SOC recebia centenas de alertas por dia e nao tinha processos
   claros para priorizar
2. **Falta de contexto**: Os alertas do FireEye nao foram integrados com outros sinais
   de seguranca
3. **Comunicacao fragmentada**: A equipe em Bangalore e a de Minneapolis nao tinham
   canais eficazes de comunicacao
4. **Ausencia de runbooks**: Nao havia procedimentos documentados para alertas criticos

**Licoes aprendidas:**

```
Licao 1: Ter um sistema de deteccao avancado e inutil sem
         processos de resposta eficazes.

Licao 2: Alertas que chegam ao SOC precisam de SLAs claros
         de resposta. Cada minuto de atraso aumenta o impacto.

Licao 3: A integracao entre ferramentas de seguranca e a
         comunicacao entre equipes e tao importante quanto
         a propria tecnologia.

Licao 4: Monitoramento 24/7 exige pessoas treinadas, nao
         apenas ferramentas rodando.
```

### 10.2 Equifax — O Fracasso do Monitoramento (2017)

O breach da Equifax em 2017 expôs os dados pessoais de 147 milhoes de pessoas e
ilustra como a falta de monitoramento adequado pode ter consequencias devastadoras.

**O que aconteceu:**

Em maio de 2017, atacantes exploraram uma vulnerabilidade no Apache Struts (CVE-2017-5638)
que nao foi corrigida pela Equifax. Os atacantes permaneceram na rede por 76 dias,
acessando bases de dados contendo numeros de seguranca social, datas de nascimento,
enderecos e outros dados sensiveis.

**Falhas de monitoramento:**

```
1. SSL/TLS Decryption Nao Configurada
   - O equipamento de inspecao de trafego (IDS/IPS) nao estava
     inspectando trafego criptografado
   - O trafego malicioso entre os atacantes e os sistemas internos
     passou completamente despercebido

2. Certificado SSL Expirado
   - Um dos certificados SSL usado pelo sistema de monitoramento
     de trafego expirou ha 19 meses
   - O sistema de monitoramento parou de inspecionar pacotes
   - Ninguem percebeu por quase 2 anos

3. Sistema de Monitoramento Desatualizado
   - O software de monitoramento de rede nao estava atualizado
   - As assinaturas de deteccao nao tinham as regras para
     detectar a exploracao do Struts

4. Falta de Segmentacao de Rede
   - Os sistemas de dados sensiveis nao estavam adequadamente
     segmentados da rede corporativa
   - Uma vez que os atacantes acessaram um sistema, podiam
     alcancar os dados sensiveis
```

**Impacto financeiro:**

```
- Multa do CFPB: USD 700 milhoes
- Acordo judicial: USD 425 milhoes (vítimas)
- Custo de remediation: USD 1.4 bilhoes
- Perda de market cap: USD 5 bilhoes (no dia seguinte)
- Custo total estimado: USD 4+ bilhoes
```

**Licoes aprendidas:**

```
Licao 1: Monitoramento de trafego criptografado e OBRIGATORIO.
         Se voce nao pode ver o trafego, nao pode protege-lo.

Licao 2: Certificados de seguranca precisam de gestao e alertas
         automaticos para expiracao.

Licao 3: Segmentacao de rede limita o impacto de um breach.
         Um sistema comprometido nao deve dar acesso a todos os dados.

Licao 4: Pessoal de seguranca precisa de supervisao e processos
         que garantam que alertas sao investigados.
```

### 10.3 Gaps de Deteccao em Grandes Breaches

Muitos dos maiores breaches da historia tiveram gaps de deteccao que poderiam ter sido
evitados com monitoramento adequado.

**Colonial Pipeline (2021):**

```
Problema: A empresa nao tinha monitoramento adequado em sistemas
          legados (VPN) que nao estavam protegidos por MFA.

Gap:       Nao havia correlacao entre logs de VPN e anomalias
          de comportamento. O atacante usou uma credencial
          comprometida sem MFA.

Deteccao:  O ransomware foi detectado apenas quando os sistemas
          comecaram a falhar.

Prevencao possivel: Monitoramento de login com MFA bypass detection,
                    alertas para logins de VPN sem MFA.
```

**SolarWinds (2020):**

```
Problema: Atacantes injetaram codigo malicioso no processo de build
          do SolarWinds Orion. O software comprometido foi distribuido
          para 18.000 organizacoes.

Gap:       A inserted backdoor (SUNBURST) se comunicava via DNS
          que parecia trafego normal.

Deteccao:  FireEye detectou o breach quando o atacante roubou as
          ferramentas internas de seguranca da FireEye.

Prevencao possivel: Monitoramento de DNS com analise de padroes,
                    verificacao de integridade de binarios distribuidos.
```

**Uber (2016/2022):**

```
Problema: Dados de 57 milhoes de usuarios e motoristas foram
          roubados. A empresa pagou USD 100.000 aos atacantes
          para deletarem os dados.

Gap:       Os dados estavam armazenados em texto plano no
          repositorio GitHub da empresa. Credenciais de acesso
          estavam no codigo.

Deteccao:  Nao houve deteccao interna. A empresa so descobriu
          porque um jornalista contactou a equipe de seguranca.

Prevencao possivel: SAST/DAST no pipeline de CI/CD, monitoramento
                    de repositorios, alertas para credenciais hardcoded.
```

### 10.4 Alert Fatigue — O Inimigo Silencioso

Alert fatigue e o fenomeno em que os operadores de seguranca se tornam sobrecarregados
pela quantidade de alertas, levando a ignorar ou responder lentamente a alertas reais.

**Estatisticas preocupantes:**

```
- 45% dos alertas de seguranca sao ignorados (Ponemon Institute)
- Tempo medio para investigar um alerta: 17 minutos
- 68% dos SOC analysts experimentam burnout
- Mediana de falsos positivos em ferramentas de seguranca: 40-60%
- 25% dos alertas criticos levam mais de 4 horas para serem atendidos
```

**Exemplo real de impacto de alert fatigue:**

```
Caso: Um hospital sofreu um ransomware que criptografou todos os
      sistemas clinicos.

Timeline:
  Dia 1 — Alerta de malware detectado pelo EDR. CLASSIFICADO
           COMO BAIXO PRIORIDADE. Nao investigado.
  Dia 2 — Alerta de atividade incomum no PowerShell. CLASSIFICADO
           COMO FALSO POSITIVO. Descartado.
  Dia 3 — Alerta de conexao C2 detectada. CLASSIFICADO COMO
           CRITICO mas NAO ATENDIDO (equipe sobrecarregada).
  Dia 4 — Ransomware detonado. Todos os sistemas clinicos
           ficam inacessiveis.

Raiz do problema: 340 alertas/dia para uma equipe de 3 pessoas.
Classificacao automatizada estava incorreta — o alerta de malware
foi classificado como baixo quando deveria ser critico.
```

**Estrategias de combate ao alert fatigue:**

```yaml
# Estrategias para reduzir alert fatigue
strategies:
  name: "Programa de Reducao de Alert Fatigue"

  phase_1_quick_wins:
    - action: "Corrigir classificacao de severidade"
      description: >
        Revisar todos os alertas existentes e garantir que
        a severidade reflita o risco real. Alertas de malware
        NUNCA devem ser classificados como baixo.
      impact: "Reducao de 30% em alertas ignorados"

    - action: "Implementar suppressao inteligente"
      description: >
        Suprimir alertas durante manutencao programada e
        em horarios de alto trafego legitimo.
      impact: "Reducao de 20% no volume total de alertas"

    - action: "Agregar alertas relacionados"
      description: >
        Agrupar multiplos alertas do mesmo evento em um
        unico alerta contextualizado.
      impact: "Reducao de 40% no numero de alertas"

  phase_2_automation:
    - action: "Implementar SOAR"
      description: >
        Usar ferramentas de orquestracao para automatizar
        investigacoes comuns e reduzir carga manual.
      tools: ["Demisto", "Swimlane", "Tines"]
      impact: "Reducao de 50% no tempo de resposta"

    - action: "Machine learning para falsos positivos"
      description: >
        Treinar modelos de ML para identificar automaticamente
        falsos positivos com base em historico.
      impact: "Reducao de 60% em falsos positivos"

  phase_3_culture:
    - action: "Treinamento continuo do SOC"
      description: >
        Sessoes regulares de treinamento sobre novas ameacas
        e como identificar falsos positivos.
      frequency: "Mensal"
      impact: "Melhoria de 25% na qualidade de investigacao"

    - action: "Metricas de qualidade, nao quantidade"
      description: >
        Medir o SOC por qualidade de deteccao (verdadeiros
        positivos), nao por numero de alertas processados.
      impact: "Mudanca de foco para resultados"
```

---

## 11. Resumo

Este capitulo demonstrou como construir uma estrutura completa de monitoramento e
observabilidade de seguranca:

1. **Observabilidade** vai alem do monitoramento tradicional ao fornecer contexto para
   entender por que algo esta acontecendo, nao apenas o que esta acontecendo
2. **Security logging** estruturado e a base de toda visibilidade de seguranca
3. **SIEMs** como ELK, Wazuh e Splunk agregam e correlacionam logs de multiplos fontes
4. **Falco** fornece monitoramento em runtime com deteccao baseada em regras
5. **Prometheus e Grafana** oferecem metricas de seguranca em tempo real com dashboards
   visuais
6. **Cloud-native monitoring** e essencial para ambientes na nuvem
7. **Incident detection** precisa de alertas bem projetados com escalacao adequada
8. **Threat hunting** proativo e necessario complementar deteccao automatizada
9. **Metricas de seguranca** permitem medir e melhorar continuamente o programa

**Casos reais** como Target e Equifax mostram que a tecnologia de monitoramento sem
processos e pessoas adequadas e inutil. Alert fatigue e uma ameaca real que pode
anular os investimentos mais sofisticados em seguranca.

A chave do sucesso nao e ter a ferramenta perfeita — e ter pessoas treinadas,
processos documentados e uma cultura que valorize a resposta rapida e eficaz a
incidentes.

---

## 12. Referencias

1. Schneier, B. (2015). "Data and Goliath: The Hidden Battles to Collect Your Data and
   Control Your World." W. W. Norton & Company.

2. Krebs, B. (2014). "Target Hackers Broke in Via HVAC Company." KrebsOnSecurity.

3. Ponemon Institute. (2023). "Cost of a Data Breach Report 2023." IBM Security.

4. CNCF. (2023). "Falco: Cloud Native Runtime Security." Cloud Native Computing Foundation.

5. Elastic. (2024). "Elastic Security Documentation." elastic.co.

6. Prometheus. (2024). "Prometheus: From Metrics to Insight." prometheus.io.

7. Grafana. (2024). "Grafana Documentation." grafana.com.

8. OpenTelemetry. (2024). "OpenTelemetry Documentation." opentelemetry.io.

9. NIST. (2012). "SP 800-92: Guide to Computer Security Log Management."

10. Mandiant. (2021). "M-Trends 2021: The Shift to Remote Work and Cloud Changes
    the Attack Landscape."

11. CISA. (2023). "Incident Response Playbooks." Cybersecurity and Infrastructure
    Security Agency.

12. SANS Institute. (2023). "Security Operations Center (SOC) Metrics and
    Measurement." SANS Reading Room.

13. OWASP. (2024). "OWASP Security Logging and Monitoring Cheat Sheet."
    owasp.org.

14. ISO/IEC 27001:2022. "Information Security Management Systems — Requirements."

15. AWS. (2024). "AWS Security Best Practices." Amazon Web Services Documentation.
