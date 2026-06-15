---
layout: default
title: "15-resposta-a-incidentes-em-producao"
---

# Capítulo 15 — Resposta a Incidentes em Produção

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Estruturar um processo de resposta a incidentes adaptado para ambientes DevOps e cloud-native, incluindo automação, infraestrutura imutável e deploy contínuo.
2. Criar runbooks e playbooks automatizados que aceleram a detecção, contenção e recuperação de incidentes em produção.
3. Implementar estratégias de rollback seguras incluindo rollbacks automáticos no CI/CD, feature flags e migrações de banco reversíveis.
4. Conduzir resposta a incidentes em containers e Kubernetes, incluindo forense de containers, evicção de pods e isolamento de nós.
5. Executar resposta a incidentes em ambientes cloud (AWS, Azure, GCP) com foco em automação e preservação de evidências.
6. conduzir post-mortems sem culpa (blameless) que transformam incidentes em aprendizados organizacionais duradouros.
7. Utilizar chaos engineering como ferramenta de preparação para incidentes reais.

---

## 1. Incident Response em Ambientes DevOps

### 1.1 Como o DevOps Muda a Resposta a Incidentes

A adoção de práticas DevOps transforma fundamentalmente a forma como organizações respondem a incidentes. Em ambientes tradicionais, a resposta era lenta e manual, dependendo de times separados de operações e segurança. Com DevOps, a velocidade de deploy e a automação exigem uma abordagem diferente de resposta.

**Princípios fundamentais de incident response em DevOps:**

| Princípio | Antes (Tradicional) | Depois (DevOps) |
|-----------|---------------------|-----------------|
| Velocidade de resposta | Horas ou dias | Minutos |
| Rollback | Manual e arriscado | Automatizado e seguro |
| Comunicação | E-mails e tickets | ChatOps e alertas integrados |
| Evidências | Logs manuais | Forense automatizada |
| Isolamento | Reboot do servidor | Containers efêmeros |
| Recuperação | Restore de backup | Re-deploy da última versão conhecida |
| Lições aprendidas | Documento esquecido | Ações integradas ao backlog |

A infraestrutura imutável é um dos pilares que mais impacta a resposta a incidentes. Quando containers são efêmeros e infraestrutura é descartável, a contenção se torna mais simples: basta destruir o container comprometido e redesenhar um novo a partir da imagem conhecida.

### 1.2 Implicações da Infraestrutura Imutável

A infraestrutura imutável elimina a necessidade de "consertar" servidores comprometidos. Em vez de aplicar patches ou limpar malware, você simplesmente recria o recurso a partir de uma imagem conhecida e segura.

```bash
#!/bin/bash
# deploy_rollback.sh - Rollback automatizado para infraestrutura imutável
# Uso: ./deploy_rollback.sh <service> <previous_version>

set -euo pipefail

SERVICE="${1:?Uso: $0 <service> <previous_version>}"
VERSION="${2:?Uso: $0 <service> <previous_version>}"
NAMESPACE="${NAMESPACE:-production}"
DEPLOYMENT_TIMEOUT=300

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "Iniciando rollback de ${SERVICE} para versão ${VERSION}"

# Verificar se a versão alvo existe no registry
if ! docker manifest inspect "registry.internal/${SERVICE}:${VERSION}" > /dev/null 2>&1; then
    log "ERRO: Versão ${VERSION} não encontrada no registry"
    exit 1
fi

# Criar snapshot do estado atual para análise posterior
kubectl get deployment "${SERVICE}" -n "${NAMESPACE}" -o yaml > "/tmp/${SERVICE}-pre-rollback-$(date +%s).yaml"

# Executar rollback
kubectl set image "deployment/${SERVICE}" \
    "${SERVICE}=registry.internal/${SERVICE}:${VERSION}" \
    -n "${NAMESPACE}"

# Aguardar rollouts completar
if kubectl rollout status "deployment/${SERVICE}" -n "${NAMESPACE}" --timeout="${DEPLOYMENT_TIMEOUT}s"; then
    log "Rollback de ${SERVICE} concluído com sucesso"
    
    # Verificar health check após rollback
    sleep 10
    if kubectl get pods -n "${NAMESPACE}" -l "app=${SERVICE}" -o json | \
       jq -e '.items[] | select(.status.phase != "Running")' > /dev/null 2>&1; then
        log "AVISO: Pods não estão todos em Running após rollback"
        kubectl get pods -n "${NAMESPACE}" -l "app=${SERVICE}"
    else
        log "Todos os pods estão saudáveis"
    fi
else
    log "ERRO: Rollback falhou ou excedeu timeout"
    kubectl rollout undo "deployment/${SERVICE}" -n "${NAMESPACE}"
    exit 1
fi
```

### 1.3 Rollback como Primeira Resposta

Em ambientes DevOps, o rollback é frequentemente a primeira ação de contenção. Antes de investigar a causa raiz, o prior é restaurar o serviço para uma versão conhecida e estável.

```python
#!/usr/bin/env python3
"""
automated_rollback.py - Sistema de rollback automatizado com verificação de saúde.
Implementa rollback gradual com verificação de integridade pós-deploy.
"""

import subprocess
import json
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any


class RollbackManager:
    """Gerencia rollback automatizado de serviços em Kubernetes."""
    
    def __init__(self, namespace: str = "production"):
        self.namespace = namespace
        self.history = []
    
    def get_current_version(self, service: str) -> Optional[str]:
        """Obtém a versão atual de um deployment."""
        cmd = [
            "kubectl", "get", "deployment", service,
            "-n", self.namespace,
            "-o", "jsonpath={.spec.template.spec.containers[0].image}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    
    def get_previous_version(self, service: str) -> Optional[str]:
        """Obtém a versão anterior do deployment."""
        cmd = [
            "kubectl", "rollout", "history", f"deployment/{service}",
            "-n", self.namespace
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 3:
            return None
        
        # A penúltima revisão é a anterior
        previous_revision = lines[-2].split()[0]
        
        cmd_detail = [
            "kubectl", "rollout", "history", f"deployment/{service}",
            "-n", self.namespace, f"--revision={previous_revision}"
        ]
        result = subprocess.run(cmd_detail, capture_output=True, text=True)
        return result.stdout
    
    def execute_rollback(self, service: str, 
                         target_revision: Optional[int] = None,
                         dry_run: bool = False) -> bool:
        """Executa rollback de um serviço."""
        
        current = self.get_current_version(service)
        timestamp = datetime.utcnow().isoformat()
        
        log_entry = {
            "service": service,
            "timestamp": timestamp,
            "current_version": current,
            "action": "rollback_start"
        }
        self.history.append(log_entry)
        
        if dry_run:
            print(f"[DRY-RUN] Rollback de {service}: {current}")
            return True
        
        # Executar rollback
        cmd = ["kubectl", "rollout", "undo", f"deployment/{service}",
               "-n", self.namespace]
        if target_revision:
            cmd.append(f"--to-revision={target_revision}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ERRO no rollback de {service}: {result.stderr}")
            return False
        
        # Aguardar conclusão
        cmd_wait = [
            "kubectl", "rollout", "status", f"deployment/{service}",
            "-n", self.namespace, "--timeout=300s"
        ]
        result = subprocess.run(cmd_wait, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"ERRO: Rollback não completou: {result.stderr}")
            return False
        
        # Verificar saúde pós-rollback
        if self.verify_health(service):
            log_entry["action"] = "rollback_success"
            self.history.append(log_entry)
            print(f"Rollback de {service} concluído com sucesso")
            return True
        else:
            log_entry["action"] = "rollback_health_check_failed"
            self.history.append(log_entry)
            print(f"AVISO: Health check falhou após rollback de {service}")
            return False
    
    def verify_health(self, service: str, 
                      retries: int = 3,
                      interval: int = 10) -> bool:
        """Verifica saúde de um serviço após rollback."""
        for attempt in range(retries):
            cmd = [
                "kubectl", "get", "pods",
                "-n", self.namespace,
                "-l", f"app={service}",
                "-o", "json"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                time.sleep(interval)
                continue
            
            pods = json.loads(result.stdout)
            all_ready = all(
                pod["status"]["phase"] == "Running" and
                any(
                    cs.get("ready", False)
                    for cs in pod.get("status", {}).get("containerStatuses", [])
                )
                for pod in pods.get("items", [])
            )
            
            if all_ready:
                return True
            
            print(f"Tentativa {attempt + 1}/{retries}: Pods ainda inicializando...")
            time.sleep(interval)
        
        return False
    
    def generate_report(self) -> str:
        """Gera relatório do rollback executado."""
        report_lines = ["=" * 60]
        report_lines.append("RELATÓRIO DE ROLLBACK")
        report_lines.append("=" * 60)
        
        for entry in self.history:
            report_lines.append(
                f"[{entry['timestamp']}] {entry['service']}: "
                f"{entry['action']}"
            )
        
        report_lines.append("=" * 60)
        return "\n".join(report_lines)


def main():
    """Função principal para execução via CLI."""
    if len(sys.argv) < 2:
        print("Uso: python automated_rollback.py <service> [--dry-run]")
        sys.exit(1)
    
    service = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    manager = RollbackManager(namespace="production")
    
    print(f"Rollback automatizado para {service}")
    print(f"Modo: {'DRY-RUN' if dry_run else 'EXECUÇÃO REAL'}")
    
    success = manager.execute_rollback(service, dry_run=dry_run)
    
    report = manager.generate_report()
    print(report)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

### 1.4 Remediação Automatizada

A remediação automática é o estágio mais avançado de incident response em DevOps. Quando um problema conhecido é detectado, o sistema pode corrigi-lo sem intervenção humana.

```yaml
# automated-remediation.yaml - Pipeline de remediação automática
# Executa quando um alerta específico é disparado

apiVersion: batch/v1
kind: Job
metadata:
  name: auto-remediation-${ALERT_TYPE}
  namespace: security
  labels:
    app: incident-response
    alert-type: "${ALERT_TYPE}"
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      serviceAccountName: remediation-bot
      containers:
      - name: remediation
        image: registry.internal/incident-bot:latest
        env:
        - name: ALERT_TYPE
          value: "${ALERT_TYPE}"
        - name: TARGET_SERVICE
          value: "${TARGET_SERVICE}"
        - name: INCIDENT_ID
          value: "${INCIDENT_ID}"
        - name: DRY_RUN
          value: "false"
        volumeMounts:
        - name: remediation-scripts
          mountPath: /scripts
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: remediation-scripts
        configMap:
          name: remediation-scripts
          defaultMode: 0755
      restartPolicy: Never
  activeDeadlineSeconds: 300
```

### 1.5 Ferramentas de Detecção Automatizada

```bash
#!/bin/bash
# detect_anomalies.sh - Detecção automatizada de anomalias em produção
# Monitora métricas críticas e dispara alertas

set -euo pipefail

METRICS_ENDPOINT="${METRICS_ENDPOINT:-http://prometheus:9090}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-http://alertmanager:9093/api/v1/alerts}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

check_error_rate() {
    local service="$1"
    local threshold="${2:-5}"
    
    query="rate(http_requests_total{service=\"${service}\",code=~\"5..\"}[5m]) / rate(http_requests_total{service=\"${service}\"}[5m]) * 100"
    
    result=$(curl -s "${METRICS_ENDPOINT}/api/v1/query" \
        --data-urlencode "query=${query}" | \
        jq -r '.data.result[0].value[1] // "0"')
    
    if (( $(echo "${result} > ${threshold}" | bc -l) )); then
        log "ALERTA: Taxa de erro de ${result}% em ${service} (threshold: ${threshold}%)"
        send_alert "high_error_rate" "${service}" "${result}"
        return 0
    fi
    return 1
}

check_latency() {
    local service="$1"
    local threshold="${2:-500}"
    
    query="histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{service=\"${service}\"}[5m])) * 1000"
    
    result=$(curl -s "${METRICS_ENDPOINT}/api/v1/query" \
        --data-urlencode "query=${query}" | \
        jq -r '.data.result[0].value[1] // "0"')
    
    if (( $(echo "${result} > ${threshold}" | bc -l) )); then
        log "ALERTA: Latência p99 de ${result}ms em ${service} (threshold: ${threshold}ms)"
        send_alert "high_latency" "${service}" "${result}"
        return 0
    fi
    return 1
}

check_memory_leak() {
    local service="$1"
    local threshold="${2:-90}"
    
    query="container_memory_usage_bytes{container=\"${service}\"} / container_spec_memory_limit_bytes * 100"
    
    result=$(curl -s "${METRICS_ENDPOINT}/api/v1/query" \
        --data-urlencode "query=${query}" | \
        jq -r '.data.result[0].value[1] // "0"')
    
    if (( $(echo "${result} > ${threshold}" | bc -l) )); then
        log "ALERTA: Uso de memória de ${result}% em ${service} (threshold: ${threshold}%)"
        send_alert "high_memory" "${service}" "${result}"
        return 0
    fi
    return 1
}

send_alert() {
    local alert_type="$1"
    local service="$2"
    local value="$3"
    
    payload=$(cat <<EOF
[{
    "labels": {
        "alertname": "${alert_type}",
        "severity": "critical",
        "service": "${service}",
        "namespace": "production"
    },
    "annotations": {
        "summary": "Anomalia detectada em ${service}",
        "description": "Tipo: ${alert_type}, Valor: ${value}",
        "runbook_url": "https://wiki.internal/runbooks/${alert_type}"
    },
    "startsAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "generatorURL": "https://grafana.internal/d/${service}"
}]
EOF
)
    
    curl -s -X POST "${ALERT_WEBHOOK}" \
        -H "Content-Type: application/json" \
        -d "${payload}" > /dev/null
    
    log "Alerta enviado: ${alert_type} para ${service}"
}

# Loop principal de monitoramento
log "Iniciando detecção de anomalias (intervalo: ${CHECK_INTERVAL}s)"

while true; do
    # Verificar serviços críticos
    for service in api-gateway auth-service payment-service; do
        check_error_rate "${service}" 5 || true
        check_latency "${service}" 500 || true
        check_memory_leak "${service}" 90 || true
    done
    
    sleep "${CHECK_INTERVAL}"
done
```

---

## 2. Runbooks e Playbooks

### 2.1 Criando Runbooks Efetivos

Um runbook efetivo é aquele que pode ser executado por qualquer membro da equipe, mesmo em situação de estresse. A chave é ser claro, específico e incluir comandos exatos.

**Estrutura de um runbook efetivo:**

1. **Nome e Propósito**: O que este runbook resolve
2. **Pré-requisitos**: O que é necessário antes de executar
3. **Sintomas**: Como identificar que este runbook se aplica
4. **Passo a passo**: Instruções numeradas com comandos exatos
5. **Verificação**: Como confirmar que o problema foi resolvido
6. **Rollback**: O que fazer se a solução piorar as coisas
7. **Escalation**: Quando e para quem escalar

### 2.2 Runbook: Container Comprometido

```yaml
# runbook-compromised-container.yaml
# Versão: 2.1
# Última atualização: 2024-01-15
# Dono: Equipe de Segurança

runbook:
  id: IR-CONTAINER-001
  name: "Container Comprometido"
  severity: critical
 平均_time: "30-60 minutos"
  
  triggers:
    - "Alerta de malware em container scan"
    - "Comportamento suspeito detectado (cryptominer, reverse shell)"
    - "Vulnerabilidade crítica não patcheada"
    - "Evidência de movimentação lateral"
  
  prerequisites:
    - "Acesso kubectl com permissão de delete pod"
    - "Acesso ao registry de imagens"
    - "Ferramenta de análise forense instalada"
  
  steps:
    - step: 1
      action: "Isolamento do Container"
      description: "Remover o pod da rede imediatamente"
      commands:
        - "kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o yaml > /tmp/pod-state.yaml"
        - "kubectl delete networkpolicy isolate-${POD_NAME} -n ${NAMESPACE} || true"
        - "cat <<EOF | kubectl apply -f -"
        - "apiVersion: networking.k8s.io/v1"
        - "kind: NetworkPolicy"
        - "metadata:"
        - "  name: isolate-${POD_NAME}"
        - "  namespace: ${NAMESPACE}"
        - "spec:"
        - "  podSelector:"
        - "    matchLabels:"
        - "      app: ${APP_NAME}"
        - "  policyTypes:"
        - "  - Egress"
        - "  - Ingress"
        - "  egress: []"
        - "  ingress: []"
        - "EOF"
      verification: "Confirmar que o pod não consegue se comunicar externamente"
    
    - step: 2
      action: "Preservação de Evidências"
      description: "Coletar dados forenses antes da destruição"
      commands:
        - "kubectl logs ${POD_NAME} -n ${NAMESPACE} --previous > /tmp/pod-logs-$(date +%s).txt"
        - "kubectl exec ${POD_NAME} -n ${NAMESPACE} -- cat /etc/passwd > /tmp/pod-users-$(date +%s).txt || true"
        - "kubectl exec ${POD_NAME} -n ${NAMESPACE} -- ps auxf > /tmp/pod-processes-$(date +%s).txt || true"
        - "kubectl exec ${POD_NAME} -n ${NAMESPACE} -- netstat -tlnp > /tmp/pod-network-$(date +%s).txt || true"
        - "kubectl describe pod ${POD_NAME} -n ${NAMESPACE} > /tmp/pod-describe-$(date +%s).txt"
      verification: "Arquivos de evidência salvos em /tmp/"
    
    - step: 3
      action: "Análise da Imagem"
      description: "Verificar a imagem do container para vulnerabilidades"
      commands:
        - "IMAGE=$(kubectl get pod ${POD_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.containers[0].image}')"
        - "trivy image --severity HIGH,CRITICAL ${IMAGE}"
        - "docker history ${IMAGE}"
        - "docker inspect ${IMAGE} | jq '.[0].Config.Env'"
      verification: "Lista de vulnerabilidades documentada"
    
    - step: 4
      action: "Remoção do Container"
      description: "Deletar o pod comprometido"
      commands:
        - "kubectl delete pod ${POD_NAME} -n ${NAMESPACE} --grace-period=0 --force"
      verification: "Pod removido e não reiniciado automaticamente"
    
    - step: 5
      action: "Redeploy com Imagem Limpa"
      description: "Recriar o serviço com imagem verificada"
      commands:
        - "kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}"
        - "kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=300s"
      verification: "Novos pods estão rodando com versão anterior"
    
    - step: 6
      action: "Verificação de Segurança"
      description: "Confirmar que o ambiente está limpo"
      commands:
        - "kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o wide"
        - "kubectl logs -l app=${APP_NAME} -n ${NAMESPACE} --tail=100 | grep -i 'error\\|warn\\|suspicious'"
      verification: "Nenhum comportamento suspeito detectado"
  
  escalation:
    condition: "Se o incidente envolver dados sensíveis ou múltiplos namespaces"
    action: "Notificar CISO e equipe de segurança"
    contact: "security-incidents@company.com"
  
  post_actions:
    - "Atualizar inventário de imagens"
    - "Revisar políticas de RBAC"
    - "Executar scan de segurança em todos os namespaces"
    - "Documentar no post-mortem"
```

### 2.3 Runbook: Vazamento de Segredos em Produção

```bash
#!/bin/bash
# runbook-secrets-leak.sh
# Resposta a vazamento de segredos em produção
# Executar SOMENTE quando confirmado vazamento

set -euo pipefail

# Configuração
VAULT_ADDR="${VAULT_ADDR:-https://vault.internal:8200}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/incident-${INCIDENT_ID}"
mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${INCIDENT_ID}] $*" | tee -a "${EVIDENCE_DIR}/incident.log"
}

alert_team() {
    local message="$1"
    if [[ -n "${SLACK_WEBHOOK}" ]]; then
        curl -s -X POST "${SLACK_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"[SECURITY INCIDENT ${INCIDENT_ID}] ${message}\"}"
    fi
}

log "=== INÍCIO DA RESPOSTA A INCIDENTE DE SEGREDO VAZADO ==="
alert_team "Incidente de vazamento de segredos detectado. Iniciando resposta."

# Passo 1: Identificar o segredo vazado
log "Passo 1: Identificando segredo vazado"

# Verificar em repositórios Git
if command -v gitleaks &> /dev/null; then
    log "Executando scan de repositórios Git..."
    gitleaks detect --source="${CODE_REPO:-.}" \
        --report-path="${EVIDENCE_DIR}/gitleaks-report.json" \
        --verbose || true
fi

# Verificar em logs de aplicação
log "Verificando logs de aplicação..."
for service in api-gateway auth-service payment-service; do
    kubectl logs -l "app=${service}" -n production --tail=10000 | \
        grep -iE "(password|secret|token|api.key|private.key)" \
        > "${EVIDENCE_DIR}/leaked-secrets-${service}.log" 2>/dev/null || true
done

# Passo 2: Rotação imediata do segredo
log "Passo 2: Rotação do segredo"

rotate_aws_secret() {
    local secret_name="$1"
    log "Rotacionando secret AWS: ${secret_name}"
    
    # Gerar novo valor
    new_value=$(openssl rand -base64 32)
    
    # Atualizar no Secrets Manager
    aws secretsmanager update-secret \
        --secret-id "${secret_name}" \
        --secret-string "${new_value}" \
        --region "${AWS_REGION}"
    
    # Invalidar cache do Secrets Manager
    aws secretsmanager get-secret-value \
        --secret-id "${secret_name}" \
        --region "${AWS_REGION}" > /dev/null
    
    log "Secret ${secret_name} rotacionado com sucesso"
}

rotate_vault_secret() {
    local secret_path="$1"
    log "Rotacionando secret Vault: ${secret_path}"
    
    vault kv put "${secret_path}" \
        password="$(openssl rand -base64 32)" > /dev/null
    
    log "Secret Vault ${secret_path} rotacionado"
}

# Rotação automática de segredos conhecidos
rotate_aws_secret "prod/database/password" || log "AVISO: Falha ao rotacionar DB password"
rotate_aws_secret "prod/api/stripe-key" || log "AVISO: Falha ao rotacionar Stripe key"
rotate_vault_secret "secret/data/prod/auth/jwt" || log "AVISO: Falha ao rotacionar JWT secret"

# Passo 3: Invalidar sessões e tokens
log "Passo 3: Invalidando sessões"

# Limpar cache de sessões
kubectl exec -n production redis-0 -- redis-cli FLUSHDB
log "Cache de sessões Redis limpo"

# Forçar rotação de tokens de API
kubectl get configmap -n production api-config -o yaml > "${EVIDENCE_DIR}/api-config-backup.yaml"
# Atualizar config com novo timestamp de invalidação
kubectl patch configmap api-config -n production -p \
    '{"data":{"token_invalidation_timestamp":"'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}}'

# Passo 4: Verificar exposição
log "Passo 4: Verificando exposição externa"

# Verificar se o segredo aparece em serviços de terceiros
check_github() {
    local secret_pattern="$1"
    log "Verificando GitHub para exposição: ${secret_pattern}"
    
    # Usar GitHub secret scanning API se disponível
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
            "https://api.github.com/search/code?q=${secret_pattern}" | \
            jq '.total_count' > "${EVIDENCE_DIR}/github-exposure.txt" 2>/dev/null || true
    fi
}

check_github "AKIA"  # AWS Access Key pattern
check_github "ghp_"  # GitHub PAT pattern
check_github "sk-"   # Stripe secret key pattern

# Passo 5: Notificar stakeholders
log "Passo 5: Notificando stakeholders"

cat > "${EVIDENCE_DIR}/incident-report.md" << EOF
# Relatório de Incidente: Vazamento de Segredo

**ID do Incidente:** ${INCIDENT_ID}
**Data/Hora:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Severidade:** CRÍTICA
**Status:** Em andamento

## Resumo
Vazamento de segredo detectado em produção. Rotação automática executada.

## Ações Executadas
1. Identificação do segredo vazado
2. Rotação automática do segredo
3. Invalidação de sessões e tokens
4. Verificação de exposição externa

## Próximos Passos
- Revisão completa de logs
- Auditoria de acesso ao segredo
- Atualização de políticas de secrets management
- Post-mortem agendado

## Evidências Coletadas
- Logs de scan: ${EVIDENCE_DIR}/
- Relatório Gitleaks: ${EVIDENCE_DIR}/gitleaks-report.json
- Logs de aplicação: ${EVIDENCE_DIR}/leaked-secrets-*.log
EOF

log "Relatório gerado: ${EVIDENCE_DIR}/incident-report.md"
alert_team "Resposta ao incidente concluída. Relatório: ${EVIDENCE_DIR}/incident-report.md"

log "=== RESPOSTA AO INCIDENTE CONCLUÍDA ==="
```

### 2.4 Runbook: Dependência Vulnerável em Produção

```yaml
# runbook-vulnerable-dependency.yaml
# Runbook para resposta a vulnerabilidades em dependências de produção
# Executar quando CVSS >= 7.0 ou quando exploração é confirmada

runbook:
  id: IR-DEPENDENCY-001
  name: "Dependência Vulnerável em Produção"
  severity: high
  average_time: "2-4 horas"
  
  triggers:
    - "Scan de dependência detectou vulnerabilidade CVSS >= 7.0"
    - "CVE publicado com exploit disponível"
    - "Alerta de parceiro ou CERT"
    - "Detecção de exploração em logs"
  
  assessment:
    - step: 1
      question: "A vulnerabilidade é explotável neste contexto?"
      tools:
        - "Verificar se o endpoint afetado está exposto"
        - "Verificar se as defesas (WAF, RASP) bloqueiam o vetor"
        - "Consultar CVSS e EPSS para probabilidade de exploração"
    
    - step: 2
      question: "Quais dados estão em risco?"
      tools:
        - "Mapear dados processados pelo componente vulnerável"
        - "Verificar classificação de dados (PII, financeiro, etc.)"
        - "Avaliar necessidade de notificação regulatória"
    
    - step: 3
      question: "Existe patch disponível?"
      tools:
        - "Verificar CVE database"
        - "Verificar changelog da dependência"
        - "Avaliar breaking changes"
  
  remediation_options:
    option_a_patch:
      name: "Aplicar patch direto"
      when: "Patch disponível sem breaking changes"
      risk: "Baixo"
      steps:
        - "Executar testes de regressão com a nova versão"
        - "Aplicar em staging primeiro"
        - "Deploy gradual em produção"
        - "Monitorar por 24 horas"
    
    option_b_upgrade:
      name: "Upgrade da dependência"
      when: "Versão patch não disponível, mas major sim"
      risk: "Médio"
      steps:
        - "Revisar changelog e breaking changes"
        - "Atualizar código afetado"
        - "Executar suite completa de testes"
        - "Deploy com feature flags"
    
    option_c_virtual_patch:
      name: "Patch virtual (WAF/RASP)"
      when: "Não é possível atualizar agora"
      risk: "Médio"
      steps:
        - "Criar regra WAF para bloquear vetor de ataque"
        - "Configurar RASP para detectar exploração"
        - "Documentar como fix temporário"
        - "Agendar fix permanente"
    
    option_d_mitigate:
      name: "Mitigação de risco"
      when: "Nenhuma correção possível no curto prazo"
      risk: "Alto"
      steps:
        - "Restringir acesso ao componente vulnerável"
        - "Aumentar monitoramento"
        - "Notificar time sobre risco aceito"
        - "Documentar decisão de negócio"
  
  verification:
    - "Executar scan de vulnerabilidade após correção"
    - "Verificar que o CVE não é mais reportado"
    - "Confirmar que testes de segurança passam"
    - "Revisar logs por sinais de exploração prévia"
  
  escalation:
    condition: "Se a vulnerabilidade foi explorada ou dados foram comprometidos"
    action: "Ativar plano de resposta a breach"
  
  post_actions:
    - "Atualizar SBOM do projeto"
    - "Adicionar dependência à lista de monitroamento"
    - "Revisar processo de dependency update"
    - "Documentar no post-mortem"
```

---

## 3. Estratégias de Rollback

### 3.1 Rollback Automatizado no CI/CD

```python
#!/usr/bin/env python3
"""
cicd_rollback.py - Pipeline de rollback automatizado para CI/CD.
Implementa rollback inteligente com verificação de saúde e notificação.
"""

import subprocess
import json
import sys
import os
from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime


class RollbackStrategy(Enum):
    """Estratégias de rollback disponíveis."""
    IMMEDIATE = "immediate"
    CANARY = "canary"
    LINEAR = "linear"
    BLUE_GREEN = "blue_green"


@dataclass
class RollbackConfig:
    """Configuração para execução de rollback."""
    service: str
    namespace: str
    strategy: RollbackStrategy
    target_version: Optional[str] = None
    health_check_url: Optional[str] = None
    health_check_retries: int = 10
    health_check_interval: int = 30
    notification_channel: Optional[str] = None
    dry_run: bool = False


class CICDRollback:
    """Implementa rollback automatizado para pipelines CI/CD."""
    
    def __init__(self, config: RollbackConfig):
        self.config = config
        self.events = []
        self.start_time = datetime.utcnow()
    
    def log_event(self, event_type: str, message: str, 
                  data: Optional[Dict] = None):
        """Registra evento de rollback."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": event_type,
            "message": message,
            "data": data or {}
        }
        self.events.append(event)
        print(f"[{event['timestamp']}] {event_type}: {message}")
    
    def get_current_version(self) -> Optional[str]:
        """Obtém a versão atual do deployment."""
        cmd = [
            "kubectl", "get", "deployment", self.config.service,
            "-n", self.config.namespace,
            "-o", "jsonpath={.spec.template.spec.containers[0].image}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    
    def get_target_version(self) -> str:
        """Determina a versão alvo para rollback."""
        if self.config.target_version:
            return self.config.target_version
        
        # Usar revisão anterior
        cmd = [
            "kubectl", "rollout", "history",
            f"deployment/{self.config.service}",
            "-n", self.config.namespace
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        if len(lines) >= 3:
            return lines[-2].split()[0]
        
        raise ValueError("Nenhuma versão anterior disponível para rollback")
    
    def execute_immediate_rollback(self) -> bool:
        """Executa rollback imediato."""
        self.log_event("ROLLBACK_START", "Iniciando rollback imediato")
        
        current = self.get_current_version()
        self.log_event("VERSION_INFO", f"Versão atual: {current}")
        
        cmd = [
            "kubectl", "rollout", "undo",
            f"deployment/{self.config.service}",
            "-n", self.config.namespace
        ]
        
        if self.config.dry_run:
            cmd.append("--dry-run=client")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log_event("ROLLBACK_ERROR", f"Falha: {result.stderr}")
            return False
        
        self.log_event("ROLLBACK_EXECUTED", "Rollback executado com sucesso")
        return True
    
    def execute_canary_rollback(self, 
                                 steps: List[int] = None) -> bool:
        """Executa rollback gradual (canary)."""
        if steps is None:
            steps = [10, 25, 50, 75, 100]
        
        self.log_event("CANARY_START", 
                      f"Iniciando rollback canary: {steps}")
        
        current = self.get_current_version()
        target = self.get_target_version()
        
        self.log_event("VERSION_INFO", 
                      f"Versão atual: {current}, Alvo: {target}")
        
        for step in steps:
            self.log_event("CANARY_STEP", 
                          f"Avançando para {step}% da versão anterior")
            
            # Atualizar percentage
            cmd = [
                "kubectl", "set", "image",
                f"deployment/{self.config.service}",
                f"{self.config.service}={target}",
                "-n", self.config.namespace
            ]
            
            if self.config.dry_run:
                cmd.append("--dry-run=client")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.log_event("CANARY_ERROR", 
                              f"Falha no step {step}%: {result.stderr}")
                return False
            
            # Aguardar propagação
            import time
            time.sleep(self.config.health_check_interval)
            
            # Verificar saúde
            if not self.verify_health():
                self.log_event("CANARY_FAILED", 
                              f"Saudade falhou no step {step}%. Revertendo...")
                # Reverter canary
                cmd_revert = [
                    "kubectl", "set", "image",
                    f"deployment/{self.config.service}",
                    f"{self.config.service}={current}",
                    "-n", self.config.namespace
                ]
                subprocess.run(cmd_revert, capture_output=True, text=True)
                return False
        
        self.log_event("CANARY_COMPLETE", 
                      "Rollback canary concluído com sucesso")
        return True
    
    def verify_health(self) -> bool:
        """Verifica saúde do serviço pós-rollback."""
        cmd = [
            "kubectl", "get", "pods",
            "-n", self.config.namespace,
            "-l", f"app={self.config.service}",
            "-o", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False
        
        pods = json.loads(result.stdout)
        
        for pod in pods.get("items", []):
            status = pod.get("status", {})
            
            # Verificar fase
            if status.get("phase") != "Running":
                return False
            
            # Verificar containers prontos
            containers = status.get("containerStatuses", [])
            for container in containers:
                if not container.get("ready", False):
                    return False
        
        return True
    
    def execute(self) -> bool:
        """Executa rollback com a estratégia configurada."""
        self.log_event("EXECUTE_START", 
                      f"Estratégia: {self.config.strategy.value}")
        
        if self.config.strategy == RollbackStrategy.IMMEDIATE:
            success = self.execute_immediate_rollback()
        elif self.config.strategy == RollbackStrategy.CANARY:
            success = self.execute_canary_rollback()
        else:
            self.log_event("UNSUPPORTED", 
                          f"Estratégia {self.config.strategy} não implementada")
            return False
        
        if success:
            # Aguardar estabilização
            import time
            time.sleep(60)
            
            # Verificação final de saúde
            if self.verify_health():
                self.log_event("EXECUTE_SUCCESS", 
                              "Rollback concluído e verificado")
                return True
            else:
                self.log_event("EXECUTE_WARNING", 
                              "Rollback executado, mas saúde não confirmada")
                return False
        else:
            self.log_event("EXECUTE_FAILED", "Rollback falhou")
            return False
    
    def generate_report(self) -> str:
        """Gera relatório de rollback."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        report = [
            "=" * 70,
            "RELATÓRIO DE ROLLBACK CI/CD",
            "=" * 70,
            f"Serviço: {self.config.service}",
            f"Namespace: {self.config.namespace}",
            f"Estratégia: {self.config.strategy.value}",
            f"Duração: {duration:.1f} segundos",
            f"Dry Run: {self.config.dry_run}",
            "",
            "EVENTOS:",
            "-" * 70,
        ]
        
        for event in self.events:
            report.append(
                f"  [{event['timestamp']}] {event['type']}: "
                f"{event['message']}"
            )
        
        report.append("=" * 70)
        return "\n".join(report)


def main():
    """Função principal para execução via CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Rollback automatizado CI/CD"
    )
    parser.add_argument("service", help="Nome do serviço")
    parser.add_argument("--namespace", default="production")
    parser.add_argument("--strategy", 
                       choices=["immediate", "canary", "linear"],
                       default="immediate")
    parser.add_argument("--target-version", help="Versão alvo")
    parser.add_argument("--dry-run", action="store_true")
    
    args = parser.parse_args()
    
    config = RollbackConfig(
        service=args.service,
        namespace=args.namespace,
        strategy=RollbackStrategy(args.strategy),
        target_version=args.target_version,
        dry_run=args.dry_run
    )
    
    rollback = CICDRollback(config)
    
    print(f"Rollback CI/CD para {config.service}")
    print(f"Modo: {'DRY-RUN' if config.dry_run else 'EXECUÇÃO REAL'}")
    print(f"Estratégia: {config.strategy.value}")
    
    success = rollback.execute()
    
    report = rollback.generate_report()
    print(report)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

### 3.2 Feature Flags para Rollback Instantâneo

```python
#!/usr/bin/env python3
"""
feature_flag_rollback.py - Sistema de rollback via feature flags.
Permite desabilitar funcionalidades específicas sem redeploy.
"""

import json
import requests
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class FeatureFlag:
    """Representa uma feature flag."""
    name: str
    enabled: bool
    description: str
    owner: str
    created_at: str
    updated_at: Optional[str] = None


class FeatureFlagRollback:
    """Gerencia rollback via feature flags."""
    
    def __init__(self, flag_service_url: str):
        self.flag_service_url = flag_service_url.rstrip('/')
        self.session = requests.Session()
    
    def get_flag(self, flag_name: str) -> Optional[FeatureFlag]:
        """Obtém o estado atual de uma feature flag."""
        response = self.session.get(
            f"{self.flag_service_url}/flags/{flag_name}"
        )
        if response.status_code == 200:
            data = response.json()
            return FeatureFlag(
                name=data['name'],
                enabled=data['enabled'],
                description=data.get('description', ''),
                owner=data.get('owner', ''),
                created_at=data.get('created_at', ''),
                updated_at=data.get('updated_at')
            )
        return None
    
    def disable_flag(self, flag_name: str, 
                     reason: str = "Rollback de segurança") -> bool:
        """Desabilita uma feature flag."""
        response = self.session.put(
            f"{self.flag_service_url}/flags/{flag_name}",
            json={
                "enabled": False,
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "rollback_reason": reason,
                    "rollback_time": datetime.utcnow().isoformat()
                }
            }
        )
        return response.status_code == 200
    
    def enable_flag(self, flag_name: str) -> bool:
        """Habilita uma feature flag."""
        response = self.session.put(
            f"{self.flag_service_url}/flags/{flag_name}",
            json={
                "enabled": True,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        return response.status_code == 200
    
    def bulk_disable(self, flags: List[str], 
                     reason: str) -> Dict[str, bool]:
        """Desabilita múltiplas flags de uma vez."""
        results = {}
        for flag_name in flags:
            results[flag_name] = self.disable_flag(flag_name, reason)
        return results
    
    def get_all_flags(self) -> List[FeatureFlag]:
        """Lista todas as feature flags."""
        response = self.session.get(
            f"{self.flag_service_url}/flags"
        )
        if response.status_code == 200:
            return [
                FeatureFlag(
                    name=f['name'],
                    enabled=f['enabled'],
                    description=f.get('description', ''),
                    owner=f.get('owner', ''),
                    created_at=f.get('created_at', ''),
                    updated_at=f.get('updated_at')
                )
                for f in response.json()
            ]
        return []
    
    def emergency_disable_all(self, 
                              exclude: List[str] = None) -> Dict[str, bool]:
        """Emergência: desabilita todas as flags exceto as excluídas."""
        if exclude is None:
            exclude = []
        
        flags = self.get_all_flags()
        active_flags = [
            f.name for f in flags 
            if f.enabled and f.name not in exclude
        ]
        
        return self.bulk_disable(
            active_flags, 
            "Emergency rollback: all features disabled"
        )


class FeatureFlagRollbackPlan:
    """Plano de rollback baseado em feature flags."""
    
    def __init__(self, flag_manager: FeatureFlagRollback):
        self.flag_manager = flag_manager
        self.plans = {}
    
    def create_plan(self, incident_type: str, 
                    flags_to_disable: List[str],
                    description: str = ""):
        """Cria um plano de rollback para um tipo de incidente."""
        self.plans[incident_type] = {
            "flags": flags_to_disable,
            "description": description,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def execute_plan(self, incident_type: str) -> bool:
        """Executa um plano de rollback."""
        if incident_type not in self.plans:
            print(f"Plano não encontrado: {incident_type}")
            return False
        
        plan = self.plans[incident_type]
        print(f"Executando plano: {incident_type}")
        print(f"Flags a desabilitar: {plan['flags']}")
        
        results = self.flag_manager.bulk_disable(
            plan['flags'],
            f"Rollback plan: {incident_type}"
        )
        
        all_success = all(results.values())
        
        for flag, success in results.items():
            status = "OK" if success else "FALHOU"
            print(f"  {flag}: {status}")
        
        return all_success


def main():
    """Demonstração do sistema de rollback via feature flags."""
    
    # Configurar gerenciador de flags
    flag_manager = FeatureFlagRollback(
        "https://flags.internal:8080/api/v1"
    )
    
    # Criar planos de rollback
    plan_manager = FeatureFlagRollbackPlan(flag_manager)
    
    # Plano para incidente de pagamento
    plan_manager.create_plan(
        incident_type="payment_system_failure",
        flags_to_disable=[
            "enable_new_checkout",
            "enable_dynamic_pricing",
            "enable_fraud_detection_v2"
        ],
        description="Rollback do sistema de pagamento"
    )
    
    # Plano para incidente de performance
    plan_manager.create_plan(
        incident_type="performance_degradation",
        flags_to_disable=[
            "enable_real_time_analytics",
            "enable_recommendation_engine",
            "enable_chat_widget"
        ],
        description="Rollback de funcionalidades pesadas"
    )
    
    # Executar plano (em caso real, seria chamado pelo runbook)
    # plan_manager.execute_plan("payment_system_failure")
    
    print("Planos de rollback configurados com sucesso")


if __name__ == "__main__":
    main()
```

### 3.3 Rollback de Migrações de Banco

```python
#!/usr/bin/env python3
"""
db_migration_rollback.py - Rollback seguro de migrações de banco de dados.
Implementa verificação pré-rollback e backup automático.
"""

import subprocess
import json
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path


@dataclass
class MigrationInfo:
    """Informações sobre uma migração."""
    version: str
    name: str
    applied_at: Optional[str] = None
    checksum: Optional[str] = None


class DatabaseMigrationRollback:
    """Gerencia rollback de migrações de banco de dados."""
    
    def __init__(self, db_type: str = "postgresql", 
                 db_name: str = "production"):
        self.db_type = db_type
        self.db_name = db_name
        self.backup_dir = Path("/tmp/db-backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str):
        """Registra mensagem com timestamp."""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def create_backup(self) -> str:
        """Cria backup do banco antes do rollback."""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"{self.db_name}_{timestamp}.sql"
        
        self.log(f"Criando backup: {backup_file}")
        
        if self.db_type == "postgresql":
            cmd = [
                "pg_dump",
                "-h", "localhost",
                "-U", "postgres",
                "-d", self.db_name,
                "-f", str(backup_file),
                "--no-owner",
                "--no-acl"
            ]
        elif self.db_type == "mysql":
            cmd = [
                "mysqldump",
                "-h", "localhost",
                "-u", "root",
                self.db_name,
                f"--result-file={backup_file}"
            ]
        else:
            raise ValueError(f"Tipo de banco não suportado: {self.db_type}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"ERRO no backup: {result.stderr}")
            raise Exception("Backup falhou")
        
        self.log(f"Backup criado com sucesso: {backup_file}")
        return str(backup_file)
    
    def get_applied_migrations(self) -> List[MigrationInfo]:
        """Obtém lista de migrações aplicadas."""
        if self.db_type == "postgresql":
            cmd = [
                "psql", "-h", "localhost", "-U", "postgres",
                "-d", self.db_name,
                "-c", "SELECT version, name, applied_at FROM schema_migrations ORDER BY version DESC"
            ]
        elif self.db_type == "mysql":
            cmd = [
                "mysql", "-h", "localhost", "-u", "root",
                self.db_name,
                "-e", "SELECT version, name, applied_at FROM schema_migrations ORDER BY version DESC"
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        migrations = []
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[1:]  # Pular header
            for line in lines:
                parts = line.split('|')
                if len(parts) >= 2:
                    migrations.append(MigrationInfo(
                        version=parts[0].strip(),
                        name=parts[1].strip(),
                        applied_at=parts[2].strip() if len(parts) > 2 else None
                    ))
        
        return migrations
    
    def rollback_migration(self, target_version: str) -> bool:
        """Executa rollback para uma versão específica."""
        migrations = self.get_applied_migrations()
        
        if not migrations:
            self.log("Nenhuma migração encontrada")
            return False
        
        self.log(f"Migração atual: {migrations[0].version}")
        self.log(f"Alvo de rollback: {target_version}")
        
        # Verificar se a versão alvo existe
        target_exists = any(
            m.version == target_version for m in migrations
        )
        
        if not target_exists:
            self.log(f"ERRO: Versão {target_version} não encontrada")
            return False
        
        # Criar backup
        backup_file = self.create_backup()
        
        # Executar rollback
        self.log("Executando rollback...")
        
        # Usar flyway ou alembic conforme o caso
        if self.db_type == "postgresql":
            cmd = [
                "flyway",
                "-url=jdbc:postgresql://localhost:5432/{self.db_name}",
                "-user=postgres",
                f"undo",
                f"-target={target_version}"
            ]
        else:
            # Para outros bancos, usar migration tool genérico
            cmd = [
                "migrate",
                "rollback",
                f"--to={target_version}",
                f"--database={self.db_name}"
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"ERRO no rollback: {result.stderr}")
            self.log("Restaurando backup...")
            self.restore_backup(backup_file)
            return False
        
        # Verificar integridade
        if self.verify_integrity():
            self.log("Rollback concluído com sucesso")
            return True
        else:
            self.log("AVISO: Verificação de integridade falhou")
            return False
    
    def verify_integrity(self) -> bool:
        """Verifica integridade do banco após rollback."""
        self.log("Verificando integridade do banco...")
        
        if self.db_type == "postgresql":
            cmd = [
                "psql", "-h", "localhost", "-U", "postgres",
                "-d", self.db_name,
                "-c", "SELECT COUNT(*) FROM schema_migrations"
            ]
        elif self.db_type == "mysql":
            cmd = [
                "mysql", "-h", "localhost", "-u", "root",
                self.db_name,
                "-e", "SELECT COUNT(*) as cnt FROM schema_migrations"
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        # Verificar se há erros de schema
        if self.db_type == "postgresql":
            check_cmd = [
                "psql", "-h", "localhost", "-U", "postgres",
                "-d", self.db_name,
                "-c", "SELECT * FROM information_schema.tables WHERE table_schema = 'public'"
            ]
        else:
            check_cmd = [
                "mysql", "-h", "localhost", "-u", "root",
                self.db_name,
                "-e", "SHOW TABLES"
            ]
        
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)
        return check_result.returncode == 0
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restaura backup do banco."""
        self.log(f"Restaurando backup: {backup_file}")
        
        if self.db_type == "postgresql":
            cmd = [
                "psql", "-h", "localhost", "-U", "postgres",
                "-d", self.db_name,
                "-f", backup_file
            ]
        elif self.db_type == "mysql":
            cmd = [
                "mysql", "-h", "localhost", "-u", "root",
                self.db_name,
                f"< {backup_file}"
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.log(f"ERRO na restauração: {result.stderr}")
            return False
        
        self.log("Restauração concluída com sucesso")
        return True
    
    def generate_rollback_script(self, 
                                  target_version: str) -> str:
        """Gera script de rollback para execução manual."""
        migrations = self.get_applied_migrations()
        
        rollback_migrations = [
            m for m in migrations 
            if m.version > target_version
        ]
        
        script_lines = [
            "#!/bin/bash",
            "# Script de rollback gerado automaticamente",
            f"# Alvo: versão {target_version}",
            f"# Data: {datetime.utcnow().isoformat()}",
            "",
            "set -euo pipefail",
            "",
            "# Criar backup antes de começar",
            f'pg_dump -h localhost -U postgres {self.db_name} > /tmp/pre-rollback-$(date +%s).sql',
            "",
        ]
        
        for migration in reversed(rollback_migrations):
            script_lines.extend([
                f"# Rollback: {migration.name}",
                f'echo "Executando rollback de {migration.name}..."',
                f'flyway -url=jdbc:postgresql://localhost:5432/{self.db_name} '
                f'-user=postgres undo -target={migration.version}',
                ""
            ])
        
        script_lines.extend([
            "# Verificação final",
            'echo "Verificando integridade..."',
            f'psql -h localhost -U postgres {self.db_name} -c "SELECT COUNT(*) FROM schema_migrations"',
            "",
            'echo "Rollback concluído!"'
        ])
        
        return "\n".join(script_lines)


def main():
    """Função principal para execução via CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Rollback de migrações de banco"
    )
    parser.add_argument("--db-type", 
                       choices=["postgresql", "mysql"],
                       default="postgresql")
    parser.add_argument("--db-name", default="production")
    parser.add_argument("--target-version", 
                       required=True,
                       help="Versão alvo para rollback")
    parser.add_argument("--generate-script", 
                       action="store_true",
                       help="Apenas gerar script, não executar")
    
    args = parser.parse_args()
    
    rollback = DatabaseMigrationRollback(
        db_type=args.db_type,
        db_name=args.db_name
    )
    
    if args.generate_script:
        script = rollback.generate_rollback_script(args.target_version)
        print(script)
    else:
        success = rollback.rollback_migration(args.target_version)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

---

## 4. Resposta a Incidentes em Containers

### 4.1 Identificando Containers Comprometidos

```bash
#!/bin/bash
# container_forensics.sh - Análise forense de containers
# Identifica containers comprometidos e coleta evidências

set -euo pipefail

EVIDENCE_DIR="/tmp/container-forensics-$(date +%Y%m%d-%H%M%S)"
mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${EVIDENCE_DIR}/forensics.log"
}

# Listar todos os containers rodando
log "=== INVENTÁRIO DE CONTAINERS ==="
docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" > "${EVIDENCE_DIR}/running-containers.txt"

# Verificar containers com recursos suspeitos
log "=== VERIFICAÇÃO DE RECURSOS SUSPEITOS ==="

# Containers com CPU alta
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | \
    awk '$2 ~ /[0-9]{2,}%/ {print "CPU ALTA:", $0}' > "${EVIDENCE_DIR}/high-cpu-containers.txt"

# Containers com processos suspeitos
for container in $(docker ps -q); do
    container_name=$(docker inspect --format '{{.Name}}' "$container" | sed 's/^\///')
    log "Verificando container: ${container_name}"
    
    # Listar processos
    docker exec "$container" ps auxf > "${EVIDENCE_DIR}/${container_name}-processes.txt" 2>/dev/null || true
    
    # Verificar conexões de rede
    docker exec "$container" netstat -tlnp > "${EVIDENCE_DIR}/${container_name}-network.txt" 2>/dev/null || true
    
    # Verificar arquivos modificados recentemente
    docker exec "$container" find / -type f -mmin -60 2>/dev/null | \
        head -100 > "${EVIDENCE_DIR}/${container_name}-recent-files.txt" 2>/dev/null || true
    
    # Verificar cron jobs suspeitos
    docker exec "$container" cat /etc/crontab > "${EVIDENCE_DIR}/${container_name}-crontab.txt" 2>/dev/null || true
    docker exec "$container" ls -la /var/spool/cron/ > "${EVIDENCE_DIR}/${container_name}-cron-spool.txt" 2>/dev/null || true
done

# Verificar imagens para vulnerabilidades
log "=== SCAN DE VULNERABILIDADES ==="
for image in $(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>"); do
    log "Scanando imagem: ${image}"
    trivy image --severity HIGH,CRITICAL "${image}" \
        --format json > "${EVIDENCE_DIR}/trivy-$(echo $image | tr ':' '-').json" 2>/dev/null || true
done

# Verificar volumes comprometidos
log "=== VERIFICAÇÃO DE VOLUMES ==="
docker volume ls > "${EVIDENCE_DIR}/volumes.txt"

for volume in $(docker volume ls -q); do
    mount_point=$(docker volume inspect "$volume" --format '{{.Mountpoint}}')
    log "Verificando volume: ${volume} em ${mount_point}"
    
    # Verificar arquivos modificados nos volumes
    find "${mount_point}" -type f -mmin -1440 -ls > \
        "${EVIDENCE_DIR}/volume-${volume}-recent.txt" 2>/dev/null || true
done

# Verificar network configurations
log "=== VERIFICAÇÃO DE REDES ==="
docker network ls > "${EVIDENCE_DIR}/networks.txt"
for network in $(docker network ls -q); do
    docker network inspect "$network" >> "${EVIDENCE_DIR}/network-details.json"
done

# Salvar logs de auditoria
log "=== LOGS DE AUDITORIA ==="
if command -v auditctl &> /dev/null; then
    auditctl -l > "${EVIDENCE_DIR}/audit-rules.txt"
    ausearch -k docker --start recent > "${EVIDENCE_DIR}/docker-audit.log" 2>/dev/null || true
fi

# Gerar resumo
log "=== GERANDO RESUMO ==="
cat > "${EVIDENCE_DIR}/summary.txt" << EOF
RELATÓRIO DE FORENSE DE CONTAINERS
Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Diretório de Evidências: ${EVIDENCE_DIR}

ARQUIVOS COLETADOS:
- running-containers.txt: Inventário de containers
- high-cpu-containers.txt: Containers com CPU alta
- *-processes.txt: Processos por container
- *-network.txt: Conexões de rede por container
- *-recent-files.txt: Arquivos modificados recentemente
- trivy-*.json: Resultados de scan de vulnerabilidades
- volumes.txt: Lista de volumes
- networks.txt: Configuração de redes

PRÓXIMOS PASSOS:
1. Revisar processos suspeitos
2. Verificar conexões de rede anômalas
3. Analisar vulnerabilidades encontradas
4. Isolar containers comprometidos
5. Coletar evidências adicionais se necessário
EOF

log "Forense concluída. Evidências em: ${EVIDENCE_DIR}"
log "Resumo: ${EVIDENCE_DIR}/summary.txt"
```

### 4.2 Análise de Diferenças em Containers

```python
#!/usr/bin/env python3
"""
container_diff.py - Análise de diferenças entre versões de container.
Compara estado atual com versão conhecida para detectar comprometimento.
"""

import subprocess
import json
import sys
from dataclasses import dataclass
from typing import List, Dict, Set
from pathlib import Path


@dataclass
class ContainerDiff:
    """Resultado da comparação entre containers."""
    container_id: str
    container_name: str
    image_current: str
    image_baseline: str
    files_added: List[str]
    files_removed: List[str]
    files_modified: List[str]
    processes_added: List[Dict]
    processes_removed: List[Dict]
    network_connections: List[Dict]
    anomalies: List[str]


class ContainerDiffAnalyzer:
    """Analisa diferenças entre versões de container."""
    
    def __init__(self, evidence_dir: str = "/tmp/container-diff"):
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
    
    def log(self, message: str):
        """Registra mensagem."""
        print(f"[CONTAINER-DIFF] {message}")
    
    def get_container_filesystem(self, 
                                  container_id: str) -> Set[str]:
        """Obtém lista de arquivos do container."""
        cmd = [
            "docker", "exec", container_id,
            "find", "/", "-type", "f", "-not", "-path", "/proc/*",
            "-not", "-path", "/sys/*", "-not", "-path", "/dev/*"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return set()
        
        return set(result.stdout.strip().split('\n'))
    
    def get_container_processes(self, 
                                 container_id: str) -> List[Dict]:
        """Obtém processos rodando no container."""
        cmd = [
            "docker", "exec", container_id,
            "ps", "aux", "--no-headers"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        processes = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    processes.append({
                        "user": parts[0],
                        "pid": parts[1],
                        "cpu": parts[2],
                        "mem": parts[3],
                        "command": parts[10]
                    })
        
        return processes
    
    def get_container_network(self, 
                               container_id: str) -> List[Dict]:
        """Obtém conexões de rede do container."""
        cmd = [
            "docker", "exec", container_id,
            "netstat", "-tlnp"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        connections = []
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n')[2:]:
                parts = line.split()
                if len(parts) >= 4:
                    connections.append({
                        "protocol": parts[0],
                        "local_address": parts[3],
                        "state": parts[3] if len(parts) > 4 else "LISTEN"
                    })
        
        return connections
    
    def get_file_hashes(self, container_id: str, 
                         files: List[str]) -> Dict[str, str]:
        """Obtém hashes de arquivos específicos."""
        hashes = {}
        for file_path in files:
            cmd = [
                "docker", "exec", container_id,
                "md5sum", file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                hash_value = result.stdout.split()[0]
                hashes[file_path] = hash_value
        return hashes
    
    def compare_containers(self, 
                           current_id: str,
                           baseline_id: str) -> ContainerDiff:
        """Compara dois containers e retorna diferenças."""
        self.log(f"Comparando container {current_id} com {baseline_id}")
        
        # Obter filesystems
        current_fs = self.get_container_filesystem(current_id)
        baseline_fs = self.get_container_filesystem(baseline_id)
        
        # Calcular diferenças
        files_added = list(current_fs - baseline_fs)
        files_removed = list(baseline_fs - current_fs)
        files_common = current_fs & baseline_fs
        
        # Verificar arquivos modificados
        files_modified = []
        for file_path in files_common:
            # Pular diretórios e arquivos de sistema
            if not file_path.startswith('/etc/') and \
               not file_path.startswith('/var/'):
                continue
            
            current_hashes = self.get_file_hashes(current_id, [file_path])
            baseline_hashes = self.get_file_hashes(baseline_id, [file_path])
            
            if current_hashes.get(file_path) != baseline_hashes.get(file_path):
                files_modified.append(file_path)
        
        # Obter processos
        current_processes = self.get_container_processes(current_id)
        baseline_processes = self.get_container_processes(baseline_id)
        
        current_cmds = {p['command'] for p in current_processes}
        baseline_cmds = {p['command'] for p in baseline_processes}
        
        processes_added = [
            p for p in current_processes 
            if p['command'] not in baseline_cmds
        ]
        processes_removed = [
            p for p in baseline_processes 
            if p['command'] not in current_cmds
        ]
        
        # Obter rede
        network_connections = self.get_container_network(current_id)
        
        # Detectar anomalias
        anomalies = []
        
        # Verificar processos de mineração
        mining_keywords = ['minerd', 'minergate', 'cryptonight', 'xmrig']
        for proc in current_processes:
            if any(keyword in proc['command'].lower() 
                   for keyword in mining_keywords):
                anomalies.append(
                    f"PROCESSO DE MINERAÇÃO DETECTADO: {proc['command']}"
                )
        
        # Verificar shells reversos
        for conn in network_connections:
            if conn['state'] == 'ESTABLISHED':
                anomalies.append(
                    f"CONEXÃO DE SAÍDA: {conn['local_address']}"
                )
        
        # Verificar arquivos suspeitos
        suspicious_paths = [
            '/tmp/.X11-unix', '/dev/shm', 
            '/var/tmp/.hidden', '/etc/ld.so.preload'
        ]
        for file_path in files_added:
            if any(suspicious in file_path for suspicious in suspicious_paths):
                anomalies.append(f"ARQUIVO SUSPEITO ADICIONADO: {file_path}")
        
        return ContainerDiff(
            container_id=current_id,
            container_name=current_id[:12],
            image_current=f"image:{current_id[:12]}",
            image_baseline=f"image:{baseline_id[:12]}",
            files_added=files_added[:100],  # Limitar para output
            files_removed=files_removed[:100],
            files_modified=files_modified[:100],
            processes_added=processes_added,
            processes_removed=processes_removed,
            network_connections=network_connections,
            anomalies=anomalies
        )
    
    def generate_report(self, diff: ContainerDiff) -> str:
        """Gera relatório de análise."""
        report_lines = [
            "=" * 70,
            "RELATÓRIO DE ANÁLISE DE DIFERENÇAS DE CONTAINER",
            "=" * 70,
            f"Container: {diff.container_name}",
            f"Data: {subprocess.run(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], 
                                    capture_output=True, text=True).stdout.strip()}",
            "",
            "RESUMO:",
            f"  Arquivos adicionados: {len(diff.files_added)}",
            f"  Arquivos removidos: {len(diff.files_removed)}",
            f"  Arquivos modificados: {len(diff.files_modified)}",
            f"  Processos adicionados: {len(diff.processes_added)}",
            f"  Processos removidos: {len(diff.processes_removed)}",
            f"  Conexões de rede: {len(diff.network_connections)}",
            "",
        ]
        
        if diff.anomalies:
            report_lines.append("ANOMALIAS DETECTADAS:")
            report_lines.append("-" * 70)
            for anomaly in diff.anomalies:
                report_lines.append(f"  [!] {anomaly}")
            report_lines.append("")
        
        if diff.processes_added:
            report_lines.append("PROCESSOS ADICIONADOS:")
            report_lines.append("-" * 70)
            for proc in diff.processes_added[:10]:
                report_lines.append(
                    f"  PID: {proc['pid']}, CMD: {proc['command']}"
                )
            report_lines.append("")
        
        if diff.files_added:
            report_lines.append("ARQUIVOS ADICIONADOS (primeiros 20):")
            report_lines.append("-" * 70)
            for file_path in diff.files_added[:20]:
                report_lines.append(f"  + {file_path}")
            report_lines.append("")
        
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
    
    def save_report(self, diff: ContainerDiff, 
                    filename: str = "container-diff-report.txt"):
        """Salva relatório em arquivo."""
        report = self.generate_report(diff)
        report_path = self.evidence_dir / filename
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        self.log(f"Relatório salvo: {report_path}")
        return str(report_path)


def main():
    """Função principal para execução via CLI."""
    if len(sys.argv) < 3:
        print("Uso: python container_diff.py <container_atual> <container_baseline>")
        sys.exit(1)
    
    current_id = sys.argv[1]
    baseline_id = sys.argv[2]
    
    analyzer = ContainerDiffAnalyzer()
    
    diff = analyzer.compare_containers(current_id, baseline_id)
    
    report_path = analyzer.save_report(diff)
    
    # Imprimir relatório
    print(analyzer.generate_report(diff))
    
    # Código de saída baseado em anomalias
    sys.exit(1 if diff.anomalies else 0)


if __name__ == "__main__":
    main()
```

---

## 5. Resposta a Incidentes em Kubernetes

### 5.1 Evicção e Isolamento de Pods

```yaml
# k8s-incident-response.yaml
# Configurações de resposta a incidentes em Kubernetes
# Inclui: NetworkPolicies, PodSecurityPolicies, e scripts de evicção

---
# NetworkPolicy para isolar pods comprometidos
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-compromised-pod
  namespace: security
  labels:
    app: incident-response
spec:
  podSelector:
    matchLabels:
      incident.io/status: compromised
  policyTypes:
  - Ingress
  - Egress
  # Negar todo tráfego
  ingress: []
  egress: []

---
# ConfigMap com scripts de resposta a incidentes
apiVersion: v1
kind: ConfigMap
metadata:
  name: incident-response-scripts
  namespace: security
data:
  isolate-pod.sh: |
    #!/bin/bash
    # Isola um pod comprometido aplicando NetworkPolicy
    
    POD_NAME="$1"
    NAMESPACE="${2:-default}"
    
    echo "Isolando pod: ${POD_NAME} no namespace: ${NAMESPACE}"
    
    # Criar NetworkPolicy para isolar o pod
    cat <<EOF | kubectl apply -f -
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: isolate-${POD_NAME}
      namespace: ${NAMESPACE}
    spec:
      podSelector:
        matchLabels:
          app: ${POD_NAME}
      policyTypes:
      - Ingress
      - Egress
      ingress: []
      egress: []
    EOF
    
    echo "Pod isolado. Nenhum tráfego de entrada/saída permitido."
  
  evict-pod.sh: |
    #!/bin/bash
    # Evicts a pod from a node for forensic analysis
    
    POD_NAME="$1"
    NAMESPACE="${2:-default}"
    
    echo "Evicting pod: ${POD_NAME} from namespace: ${NAMESPACE}"
    
    # Get pod node
    NODE=$(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.spec.nodeName}')
    echo "Pod running on node: ${NODE}"
    
    # Drain node (with force to handle PDB violations)
    kubectl drain "${NODE}" \
      --ignore-daemonsets \
      --delete-emptydir-data \
      --force \
      --grace-period=30
    
    echo "Node drained. Pod evicted for analysis."
  
  forensic-collect.sh: |
    #!/bin/bash
    # Collects forensic evidence from a pod
    
    POD_NAME="$1"
    NAMESPACE="${2:-default}"
    EVIDENCE_DIR="/tmp/forensics-${POD_NAME}-$(date +%s)"
    
    mkdir -p "${EVIDENCE_DIR}"
    
    echo "Collecting forensics from pod: ${POD_NAME}"
    
    # Save pod description
    kubectl describe pod "${POD_NAME}" -n "${NAMESPACE}" > "${EVIDENCE_DIR}/pod-description.txt"
    
    # Save pod logs
    kubectl logs "${POD_NAME}" -n "${NAMESPACE}" --all-containers > "${EVIDENCE_DIR}/pod-logs.txt" 2>/dev/null || true
    
    # Save container info
    for container in $(kubectl get pod "${POD_NAME}" -n "${NAMESPACE}" -o jsonpath='{.spec.containers[*].name}'); do
      echo "Container: ${container}" >> "${EVIDENCE_DIR}/containers.txt"
      kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -c "${container}" -- ps auxf > "${EVIDENCE_DIR}/${container}-processes.txt" 2>/dev/null || true
      kubectl exec "${POD_NAME}" -n "${NAMESPACE}" -c "${container}" -- netstat -tlnp > "${EVIDENCE_DIR}/${container}-network.txt" 2>/dev/null || true
    done
    
    # Save events
    kubectl get events -n "${NAMESPACE}" --field-selector involvedObject.name="${POD_NAME}" > "${EVIDENCE_DIR}/events.txt"
    
    echo "Evidence collected in: ${EVIDENCE_DIR}"
```

### 5.2 Script Completo de Resposta K8s

```bash
#!/bin/bash
# k8s-incident-response.sh
# Resposta automatizada a incidentes em Kubernetes
# Executar com cuidado - afeta pods e nodes em produção

set -euo pipefail

# Configuração
NAMESPACE="${NAMESPACE:-production}"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/k8s-incident-${INCIDENT_ID}"
LOG_FILE="${EVIDENCE_DIR}/response.log"

mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

# Função para isolar um pod
isolate_pod() {
    local pod_name="$1"
    local namespace="${2:-${NAMESPACE}}"
    
    log "Isolando pod: ${pod_name}"
    
    # Criar NetworkPolicy de isolamento
    cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: isolate-${pod_name}
  namespace: ${namespace}
spec:
  podSelector:
    matchLabels:
      app: ${pod_name}
  policyTypes:
  - Ingress
  - Egress
  ingress: []
  egress: []
EOF
    
    log "Pod ${pod_name} isolado - sem tráfego de rede"
}

# Função para coletar evidências de um pod
collect_evidence() {
    local pod_name="$1"
    local namespace="${2:-${NAMESPACE}}"
    local evidence_subdir="${EVIDENCE_DIR}/${pod_name}"
    
    mkdir -p "${evidence_subdir}"
    
    log "Coletando evidências do pod: ${pod_name}"
    
    # Descrição completa do pod
    kubectl describe pod "${pod_name}" -n "${namespace}" > "${evidence_subdir}/pod-description.txt"
    
    # Logs (incluindo anterior)
    kubectl logs "${pod_name}" -n "${namespace}" --all-containers > "${evidence_subdir}/pod-logs.txt" 2>/dev/null || true
    kubectl logs "${pod_name}" -n "${namespace}" --previous > "${evidence_subdir}/pod-logs-previous.txt" 2>/dev/null || true
    
    # Listar containers
    containers=$(kubectl get pod "${pod_name}" -n "${namespace}" -o jsonpath='{.spec.containers[*].name}')
    
    for container in ${containers}; do
        log "Coletando dados do container: ${container}"
        
        # Processos
        kubectl exec "${pod_name}" -n "${namespace}" -c "${container}" -- \
            ps auxf > "${evidence_subdir}/${container}-processes.txt" 2>/dev/null || true
        
        # Conexões de rede
        kubectl exec "${pod_name}" -n "${namespace}" -c "${container}" -- \
            netstat -tlnp > "${evidence_subdir}/${container}-network.txt" 2>/dev/null || true
        
        # Arquivos modificados recentemente
        kubectl exec "${pod_name}" -n "${namespace}" -c "${container}" -- \
            find / -type f -mmin -60 2>/dev/null | head -100 > "${evidence_subdir}/${container}-recent-files.txt" 2>/dev/null || true
    done
    
    # Events
    kubectl get events -n "${namespace}" \
        --field-selector involvedObject.name="${pod_name}" \
        > "${evidence_subdir}/events.txt" 2>/dev/null || true
    
    # Resource usage
    kubectl top pod "${pod_name}" -n "${namespace}" > "${evidence_subdir}/resource-usage.txt" 2>/dev/null || true
    
    log "Evidências coletadas em: ${evidence_subdir}"
}

# Função para evacuar node
evacuate_node() {
    local node_name="$1"
    local reason="$2"
    
    log "Evacuando node: ${node_name} (razão: ${reason})"
    
    # Verificar se o node está realmente comprometido
    kubectl describe node "${node_name}" > "${EVIDENCE_DIR}/${node_name}-describe.txt"
    
    # Drain com opções de segurança
    kubectl drain "${node_name}" \
        --ignore-daemonsets \
        --delete-emptydir-data \
        --force \
        --grace-period=60 \
        --timeout=300s
    
    # Marcar node como不可用
    kubectl cordon "${node_name}"
    
    log "Node ${node_name} evacuado e marcado como不可用"
}

# Função para restaurar serviço
restore_service() {
    local deployment_name="$1"
    local namespace="${2:-${NAMESPACE}}"
    local target_image="${3:-}"
    
    log "Restaurando deployment: ${deployment_name}"
    
    if [[ -n "${target_image}" ]]; then
        # Deploy para versão específica
        kubectl set image "deployment/${deployment_name}" \
            "${deployment_name}=${target_image}" \
            -n "${namespace}"
    else
        # Rollback para versão anterior
        kubectl rollout undo "deployment/${deployment_name}" -n "${namespace}"
    fi
    
    # Aguardar estabilização
    if kubectl rollout status "deployment/${deployment_name}" \
        -n "${namespace}" --timeout=300s; then
        log "Deployment ${deployment_name} restaurado com sucesso"
    else
        log "ERRO: Deployment ${deployment_name} não estabilizou"
        return 1
    fi
    
    # Verificar saúde dos pods
    sleep 10
    kubectl get pods -n "${namespace}" -l "app=${deployment_name}" -o wide
}

# Função para scan de segurança
security_scan() {
    local namespace="${1:-${NAMESPACE}}"
    
    log "Executando scan de segurança no namespace: ${namespace}"
    
    # Listar todas as imagens em uso
    kubectl get pods -n "${namespace}" -o json | \
        jq -r '.spec.containers[].image' | sort -u > "${EVIDENCE_DIR}/images-in-use.txt"
    
    # Scan cada imagem
    while IFS= read -r image; do
        log "Scanando: ${image}"
        trivy image --severity HIGH,CRITICAL "${image}" \
            --format json > "${EVIDENCE_DIR}/trivy-$(echo ${image} | tr ':' '-').json" 2>/dev/null || true
    done < "${EVIDENCE_DIR}/images-in-use.txt"
    
    log "Scan de segurança concluído"
}

# Função principal
main() {
    log "=== INÍCIO DA RESPOSTA A INCIDENTE KUBERNETES ==="
    log "Incident ID: ${INCIDENT_ID}"
    
    # Listar pods suspeitos
    log "Procurando pods com comportamento suspeito..."
    
    # Verificar pods com restarts altos
    kubectl get pods -n "${NAMESPACE}" -o json | \
        jq -r '.items[] | select(.status.containerStatuses[].restartCount > 5) | .metadata.name' | \
        while read pod; do
            log "Pod com muitos restarts detectado: ${pod}"
            collect_evidence "${pod}"
        done
    
    # Verificar pods com alta CPU
    kubectl top pods -n "${NAMESPACE}" --sort-by=cpu 2>/dev/null | \
        awk 'NR>1 && $3 ~ /[0-9]+m/ && int($3) > 800 {print $1}' | \
        while read pod; do
            log "Pod com alta CPU detectado: ${pod}"
            collect_evidence "${pod}"
        done
    
    # Executar scan de segurança
    security_scan
    
    log "=== RESPOSTA AO INCIDENTE CONCLUÍDA ==="
    log "Evidências em: ${EVIDENCE_DIR}"
    log "Próximos passos: revisar evidências, decidir ações corretivas"
}

# Executar
main "$@"
```

---

## 6. Resposta a Incidentes em Cloud

### 6.1 Resposta a Incidentes em AWS

```bash
#!/bin/bash
# aws-incident-response.sh
# Resposta a incidentes em AWS

set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/aws-incident-${INCIDENT_ID}"
mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${EVIDENCE_DIR}/response.log"
}

# Função para isolar instância EC2
isolate_ec2_instance() {
    local instance_id="$1"
    local reason="$2"
    
    log "Isolando instância EC2: ${instance_id}"
    
    # Criar Security Group de isolamento
    vpc_id=$(aws ec2 describe-instances --instance-ids "${instance_id}" \
        --query 'Reservations[0].Instances[0].VpcId' --output text --region "${AWS_REGION}")
    
    sg_id=$(aws ec2 create-security-group \
        --group-name "isolate-${instance_id}" \
        --description "Isolation SG for incident ${INCIDENT_ID}" \
        --vpc-id "${vpc_id}" \
        --region "${AWS_REGION}" \
        --query 'GroupId' --output text)
    
    # Reatribuar instância para SG de isolamento (sem regras)
    aws ec2 modify-instance-attribute \
        --instance-id "${instance_id}" \
        --groups "${sg_id}" \
        --region "${AWS_REGION}"
    
    log "Instância ${instance_id} isolada (SG: ${sg_id})"
    echo "${sg_id}" > "${EVIDENCE_DIR}/${instance_id}-isolation-sg.txt"
}

# Função para snapshot de EBS
snapshot_ebs() {
    local instance_id="$1"
    
    log "Criando snapshots de EBS para instância: ${instance_id}"
    
    # Obter volumes
    volumes=$(aws ec2 describe-instances --instance-ids "${instance_id}" \
        --query 'Reservations[0].Instances[0].BlockDeviceMappings[*].Ebs.VolumeId' \
        --output text --region "${AWS_REGION}")
    
    for volume in ${volumes}; do
        log "Criando snapshot do volume: ${volume}"
        snapshot_id=$(aws ec2 create-snapshot \
            --volume-id "${volume}" \
            --description "Incident ${INCIDENT_ID} - ${instance_id}" \
            --region "${AWS_REGION}" \
            --query 'SnapshotId' --output text)
        
        aws ec2 create-tags \
            --resources "${snapshot_id}" \
            --tags "Key=IncidentId,Value=${INCIDENT_ID}" \
            "Key=SourceInstanceId,Value=${instance_id}" \
            --region "${AWS_REGION}"
        
        log "Snapshot criado: ${snapshot_id}"
    done
}

# Função para habilitar CloudTrail logging
enable_forensic_logging() {
    log "Habilitando logging forense..."
    
    # Habilitar VPC Flow Logs
    vpc_id="${VPC_ID:-$(aws ec2 describe-vpcs --query 'Vpcs[0].VpcId' --output text --region "${AWS_REGION}")}"
    
    aws ec2 create-flow-logs \
        --resource-type VPC \
        --resource-ids "${vpc_id}" \
        --traffic-type ALL \
        --log-destination-type cloud-watch-logs \
        --log-group-name "/aws/vpc/flowlogs/${INCIDENT_ID}" \
        --deliver-logs-permission-arn "arn:aws:iam::role/VPCFlowLogsRole" \
        --region "${AWS_REGION}" 2>/dev/null || true
    
    log "VPC Flow Logs habilitados"
    
    # Habilitar GuardDuty se disponível
    aws guardduty enable-detector \
        --detector-id "${DETECTOR_ID:-}" \
        --region "${AWS_REGION}" 2>/dev/null || true
    
    log "Logging forense habilitado"
}

# Função para coletar evidências
collect_evidence() {
    local instance_id="$1"
    
    log "Coletando evidências da instância: ${instance_id}"
    
    # Descrição da instância
    aws ec2 describe-instances --instance-ids "${instance_id}" \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/${instance_id}-describe.json"
    
    # Security Groups
    sg_ids=$(cat "${EVIDENCE_DIR}/${instance_id}-describe.json" | \
        jq -r '.Reservations[0].Instances[0].SecurityGroups[*].GroupId')
    for sg in ${sg_ids}; do
        aws ec2 describe-security-groups --group-ids "${sg}" \
            --region "${AWS_REGION}" > "${EVIDENCE_DIR}/${instance_id}-sg-${sg}.json"
    done
    
    # CloudWatch Logs
    aws logs describe-log-groups \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/cloudwatch-log-groups.json"
    
    # Flow Logs
    aws ec2 describe-flow-logs \
        --filter "Name=resource-id,Values=${instance_id}" \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/${instance_id}-flow-logs.json"
    
    # Configuração de rede
    aws ec2 describe-network-interfaces \
        --filters "Name=attachment.instance-id,Values=${instance_id}" \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/${instance_id}-network-interfaces.json"
    
    log "Evidências coletadas"
}

# Função para verificar acessos suspeitos
check_suspicious_access() {
    log "Verificando acessos suspeitos via CloudTrail..."
    
    # CloudTrail - Últimas 24 horas
    aws cloudtrail lookup-events \
        --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
        --max-results 100 \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/cloudtrail-console-login.json"
    
    # IAM changes
    aws cloudtrail lookup-events \
        --lookup-attributes AttributeKey=EventName,AttributeValue=AttachUserPolicy \
        --max-results 100 \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/cloudtrail-iam-changes.json"
    
    # Security group changes
    aws cloudtrail lookup-events \
        --lookup-attributes AttributeKey=EventName,AttributeValue=AuthorizeSecurityGroupIngress \
        --max-results 100 \
        --region "${AWS_REGION}" > "${EVIDENCE_DIR}/cloudtrail-sg-changes.json"
    
    log "Verificação de acessos concluída"
}

# Função principal
main() {
    log "=== INÍCIO DA RESPOSTA A INCIDENTE AWS ==="
    log "Incident ID: ${INCIDENT_ID}"
    
    # Verificar se há instâncias comprometidas
    if [[ -n "${TARGET_INSTANCE:-}" ]]; then
        isolate_ec2_instance "${TARGET_INSTANCE}" "Suspected compromise"
        snapshot_ebs "${TARGET_INSTANCE}"
        collect_evidence "${TARGET_INSTANCE}"
    fi
    
    enable_forensic_logging
    check_suspicious_access
    
    log "=== RESPOSTA AO INCIDENTE CONCLUÍDA ==="
    log "Evidências em: ${EVIDENCE_DIR}"
}

main "$@"
```

### 6.2 Resposta a Incidentes em Azure

```bash
#!/bin/bash
# azure-incident-response.sh
# Resposta a incidentes em Azure

set -euo pipefail

AZURE_SUBSCRIPTION="${AZURE_SUBSCRIPTION:-}"
RESOURCE_GROUP="${RESOURCE_GROUP:-production-rg}"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/azure-incident-${INCIDENT_ID}"
mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${EVIDENCE_DIR}/response.log"
}

# Função para isolar VM
isolate_vm() {
    local vm_name="$1"
    
    log "Isolando VM: ${vm_name}"
    
    # Criar NSG para isolamento
    nsg_name="isolate-${vm_name}-${INCIDENT_ID}"
    
    az network nsg create \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${nsg_name}" \
        --location "$(az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" --query location --output tsv)" \
        > /dev/null
    
    # NSG sem regras = isolamento total
    
    # Associar NSG à subnet da VM
    nic_id=$(az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" \
        --query 'networkProfile.networkInterfaces[0].id' --output tsv)
    
    subnet_id=$(az network nic show --ids "${nic_id}" \
        --query 'ipConfigurations[0].subnet.id' --output tsv)
    
    az network vnet subnet update --ids "${subnet_id}" \
        --network-security-group "${nsg_name}" > /dev/null
    
    log "VM ${vm_name} isolada via NSG: ${nsg_name}"
}

# Função para snapshot de disco
snapshot_disk() {
    local vm_name="$1"
    
    log "Criando snapshot dos discos da VM: ${vm_name}"
    
    # Listar discos
    disks=$(az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" \
        --query 'storageProfile.dataDisks[*].name' --output tsv)
    
    # Adicionar disco do OS
    os_disk=$(az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" \
        --query 'storageProfile.osDisk.name' --output tsv)
    
    for disk in ${os_disk} ${disks}; do
        log "Criando snapshot do disco: ${disk}"
        snapshot_name="${disk}-snapshot-${INCIDENT_ID}"
        
        az snapshot create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${snapshot_name}" \
            --source "${disk}" \
            --incremental false \
            > /dev/null
        
        log "Snapshot criado: ${snapshot_name}"
    done
}

# Função para habilitar diagnósticos
enable_diagnostics() {
    local vm_name="$1"
    
    log "Habilitando diagnósticos na VM: ${vm_name}"
    
    # Habilitar boot diagnostics
    az vm boot-diagnostics enable \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${vm_name}" \
        > /dev/null 2>&1 || true
    
    # Habilitar VM insights
    az monitor diagnostic-settings create \
        --resource "/subscriptions/${AZURE_SUBSCRIPTION}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${vm_name}" \
        --name "incident-diagnostics-${INCIDENT_ID}" \
        --logs '[{"category":"AuditEvent","enabled":true},{"category":"Policy","enabled":true}]' \
        --metrics '[{"category":"AllMetrics","enabled":true}]' \
        > /dev/null 2>&1 || true
    
    log "Diagnósticos habilitados"
}

# Função para coletar evidências
collect_evidence() {
    local vm_name="$1"
    
    log "Coletando evidências da VM: ${vm_name}"
    
    # Informações da VM
    az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" \
        > "${EVIDENCE_DIR}/${vm_name}-describe.json"
    
    # NSGs associados
    az vm show --resource-group "${RESOURCE_GROUP}" --name "${vm_name}" \
        --query 'networkProfile.networkInterfaces[*].id' --output tsv | \
        while read nic; do
            az network nic show --ids "${nic}" \
                > "${EVIDENCE_DIR}/${vm_name}-nic-$(basename ${nic}).json"
        done
    
    # Activity Log
    az monitor activity-log list \
        --resource-group "${RESOURCE_GROUP}" \
        --query "[?contains(resourceId, '${vm_name}')]" \
        > "${EVIDENCE_DIR}/${vm_name}-activity-log.json"
    
    # Diagnostic logs
    az monitor diagnostic-settings list \
        --resource "/subscriptions/${AZURE_SUBSCRIPTION}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Compute/virtualMachines/${vm_name}" \
        > "${EVIDENCE_DIR}/${vm_name}-diagnostics.json" 2>/dev/null || true
    
    log "Evidências coletadas"
}

main() {
    log "=== INÍCIO DA RESPOSTA A INCIDENTE AZURE ==="
    log "Incident ID: ${INCIDENT_ID}"
    
    if [[ -n "${TARGET_VM:-}" ]]; then
        isolate_vm "${TARGET_VM}"
        snapshot_disk "${TARGET_VM}"
        enable_diagnostics "${TARGET_VM}"
        collect_evidence "${TARGET_VM}"
    fi
    
    log "=== RESPOSTA AO INCIDENTE CONCLUÍDA ==="
    log "Evidências em: ${EVIDENCE_DIR}"
}

main "$@"
```

### 6.3 Resposta a Incidentes em GCP

```bash
#!/bin/bash
# gcp-incident-response.sh
# Resposta a incidentes em Google Cloud Platform

set -euo pipefail

GCP_PROJECT="${GCP_PROJECT:-}"
GCP_REGION="${GCP_REGION:-us-central1}"
INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
EVIDENCE_DIR="/tmp/gcp-incident-${INCIDENT_ID}"
mkdir -p "${EVIDENCE_DIR}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "${EVIDENCE_DIR}/response.log"
}

# Função para isolar VM
isolate_vm() {
    local instance_name="$1"
    local zone="${2:-${GCP_REGION}-a}"
    
    log "Isolando instância GCE: ${instance_name}"
    
    # Criar regra de firewall para isolamento
    firewall_name="isolate-${instance_name}-${INCIDENT_ID}"
    
    gcloud compute firewall-rules create "${firewall_name}" \
        --project "${GCP_PROJECT}" \
        --network default \
        --direction INGRESS \
        --priority 1000 \
        --source-ranges 0.0.0.0/0 \
        --action DENY \
        --rules all \
        --target-tags "instance=${instance_name}" \
        > /dev/null
    
    # Tag a instância
    gcloud compute instances add-tags "${instance_name}" \
        --project "${GCP_PROJECT}" \
        --zone "${zone}" \
        --tags "incident-${INCIDENT_ID},isolated" \
        > /dev/null
    
    log "Instância ${instance_name} isolada via firewall rule"
}

# Função para snapshot
create_snapshot() {
    local instance_name="$1"
    local zone="${2:-${GCP_REGION}-a}"
    
    log "Criando snapshot da instância: ${instance_name}"
    
    # Listar discos
    disks=$(gcloud compute instances describe "${instance_name}" \
        --project "${GCP_PROJECT}" \
        --zone "${zone}" \
        --format='value(disks[].source.basename())')
    
    for disk in ${disks}; do
        snapshot_name="${disk}-snapshot-${INCIDENT_ID}"
        
        gcloud compute disks snapshot "${disk}" \
            --project "${GCP_PROJECT}" \
            --zone "${zone}" \
            --snapshot-names "${snapshot_name}" \
            --description "Incident ${INCIDENT_ID}" \
            > /dev/null
        
        log "Snapshot criado: ${snapshot_name}"
    done
}

# Função para habilitar logging
enable_logging() {
    log "Habilitando logging avançado..."
    
    # Data audit logs
    gcloud logging sinks create "incident-audit-${INCIDENT_ID}" \
        "storage.googleapis.com/${GCP_PROJECT}-incident-logs" \
        --project "${GCP_PROJECT}" \
        --log-filter='protoPayload.authenticationInfo.principalEmail!=""' \
        > /dev/null 2>&1 || true
    
    # VPC Flow Logs
    gcloud compute networks subnets update default \
        --project "${GCP_PROJECT}" \
        --region "${GCP_REGION}" \
        --enable-flow-logs \
        --logging-metadata include-all \
        > /dev/null 2>&1 || true
    
    log "Logging habilitado"
}

# Função para coletar evidências
collect_evidence() {
    local instance_name="$1"
    local zone="${2:-${GCP_REGION}-a}"
    
    log "Coletando evidências da instância: ${instance_name}"
    
    # Informações da instância
    gcloud compute instances describe "${instance_name}" \
        --project "${GCP_PROJECT}" \
        --zone "${zone}" > "${EVIDENCE_DIR}/${instance_name}-describe.json"
    
    # Firewall rules
    gcloud compute firewall-rules list \
        --project "${GCP_PROJECT}" \
        --format=json > "${EVIDENCE_DIR}/firewall-rules.json"
    
    # Logs de auditoria
    gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=${instance_name}" \
        --project "${GCP_PROJECT}" \
        --limit 1000 \
        --format=json > "${EVIDENCE_DIR}/${instance_name}-audit-logs.json" 2>/dev/null || true
    
    # Network endpoints
    gcloud compute network-endpoints list \
        --project "${GCP_PROJECT}" \
        --filter="instance=${instance_name}" \
        > "${EVIDENCE_DIR}/${instance_name}-network-endpoints.json" 2>/dev/null || true
    
    log "Evidências coletadas"
}

# Função principal
main() {
    log "=== INÍCIO DA RESPOSTA A INCIDENTE GCP ==="
    log "Incident ID: ${INCIDENT_ID}"
    
    if [[ -n "${TARGET_INSTANCE:-}" ]]; then
        isolate_vm "${TARGET_INSTANCE}"
        create_snapshot "${TARGET_INSTANCE}"
        collect_evidence "${TARGET_INSTANCE}"
    fi
    
    enable_logging
    
    log "=== RESPOSTA AO INCIDENTE CONCLUÍDA ==="
    log "Evidências em: ${EVIDENCE_DIR}"
}

main "$@"
```

---

## 7. Comunicação

### 7.1 Notificação de Stakeholders

```python
#!/usr/bin/env python3
"""
incident_communication.py - Sistema de comunicação durante incidentes.
Gerencia notificações para diferentes stakeholders.
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Severidade do incidente."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NotificationChannel(Enum):
    """Canais de notificação."""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    PHONE = "phone"
    PAGERDUTY = "pagerduty"


@dataclass
class Stakeholder:
    """Stakeholder para notificação."""
    name: str
    role: str
    email: str
    phone: Optional[str]
    channels: List[NotificationChannel]
    severity_threshold: Severity


@dataclass
class Incident:
    """Representação de um incidente."""
    id: str
    title: str
    severity: Severity
    status: str
    created_at: str
    updated_at: str
    summary: str
    impact: str
    next_update: str
    actions_taken: List[str]
    next_steps: List[str]


class IncidentCommunicator:
    """Gerencia comunicação durante incidentes."""
    
    def __init__(self):
        self.stakeholders = self._load_stakeholders()
        self.templates = self._load_templates()
    
    def _load_stakeholders(self) -> List[Stakeholder]:
        """Carrega lista de stakeholders."""
        return [
            Stakeholder(
                name="CEO",
                role="Executivo",
                email="ceo@company.com",
                phone="+5511999999999",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                severity_threshold=Severity.CRITICAL
            ),
            Stakeholder(
                name="CISO",
                role="Segurança",
                email="ciso@company.com",
                phone="+5511999999998",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.SMS],
                severity_threshold=Severity.HIGH
            ),
            Stakeholder(
                name="VP Engenharia",
                role="Engenharia",
                email="vp-eng@company.com",
                phone="+5511999999997",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                severity_threshold=Severity.HIGH
            ),
            Stakeholder(
                name="Time de Segurança",
                role="Operacional",
                email="security@company.com",
                phone=None,
                channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
                severity_threshold=Severity.MEDIUM
            ),
            Stakeholder(
                name="Time de Operações",
                role="Operacional",
                email="ops@company.com",
                phone=None,
                channels=[NotificationChannel.SLACK, NotificationChannel.EMAIL],
                severity_threshold=Severity.MEDIUM
            ),
        ]
    
    def _load_templates(self) -> Dict[str, str]:
        """Carrega templates de mensagem."""
        return {
            "initial_notification": """
=== NOTIFICAÇÃO DE INCIDENTE ===

ID: {incident_id}
Título: {title}
Severidade: {severity}
Status: {status}
Data/Hora: {timestamp}

RESUMO:
{summary}

IMPACTO:
{impact}

AÇÕES EM ANDAMENTO:
{actions}

PRÓXIMA ATUALIZAÇÃO: {next_update}
""",
            "status_update": """
=== ATUALIZAÇÃO DE INCIDENTE ===

ID: {incident_id}
Status: {status}
Data/Hora: {timestamp}

RESUMO ATUALIZADO:
{summary}

AÇÕES REALIZADAS:
{actions}

PRÓXIMOS PASSOS:
{next_steps}

PRÓXIMA ATUALIZAÇÃO: {next_update}
""",
            "resolution": """
=== RESOLUÇÃO DE INCIDENTE ===

ID: {incident_id}
Status: RESOLVIDO
Data/Hora: {timestamp}

DURAÇÃO TOTAL: {duration}

RESUMO FINAL:
{summary}

CAUSA RAIZ:
{root_cause}

AÇÕES CORRETIVAS:
{corrective_actions}

POST-MORTEM AGENDADO: {postmortem_date}
"""
        }
    
    def should_notify(self, stakeholder: Stakeholder, 
                      severity: Severity) -> bool:
        """Verifica se o stakeholder deve ser notificado."""
        severity_order = {
            Severity.LOW: 0,
            Severity.MEDIUM: 1,
            Severity.HIGH: 2,
            Severity.CRITICAL: 3
        }
        return severity_order[severity] >= severity_order[stakeholder.severity_threshold]
    
    def format_message(self, template_name: str, 
                       incident: Incident) -> str:
        """Formata mensagem usando template."""
        template = self.templates.get(template_name, "")
        
        return template.format(
            incident_id=incident.id,
            title=incident.title,
            severity=incident.severity.value.upper(),
            status=incident.status,
            timestamp=incident.updated_at,
            summary=incident.summary,
            impact=incident.impact,
            actions="\n".join(f"- {a}" for a in incident.actions_taken),
            next_steps="\n".join(f"- {s}" for s in incident.next_steps),
            next_update=incident.next_update,
            duration=self._calculate_duration(incident),
            root_cause="A ser determinado no post-mortem",
            corrective_actions="A ser definido",
            postmortem_date="A ser agendado"
        )
    
    def _calculate_duration(self, incident: Incident) -> str:
        """Calcula duração do incidente."""
        created = datetime.fromisoformat(incident.created_at)
        updated = datetime.fromisoformat(incident.updated_at)
        duration = updated - created
        
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        return f"{hours}h {minutes}m"
    
    def send_email(self, to_email: str, 
                   subject: str, body: str) -> bool:
        """Envia email de notificação."""
        msg = MIMEMultipart()
        msg['From'] = "incident-response@company.com"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP('smtp.company.com', 587) as server:
                server.starttls()
                server.login("incident@company.com", "password")
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
            return False
    
    def send_slack(self, webhook_url: str, message: str) -> bool:
        """Envia mensagem Slack."""
        import requests
        
        payload = {"text": message}
        
        try:
            response = requests.post(webhook_url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Erro ao enviar Slack: {e}")
            return False
    
    def notify_stakeholders(self, incident: Incident, 
                           template_name: str = "initial_notification"):
        """Notifica todos os stakeholders apropriados."""
        message = self.format_message(template_name, incident)
        subject = f"[{incident.severity.value.upper()}] Incidente {incident.id}: {incident.title}"
        
        for stakeholder in self.stakeholders:
            if not self.should_notify(stakeholder, incident.severity):
                continue
            
            print(f"Notificando {stakeholder.name} ({stakeholder.role})")
            
            for channel in stakeholder.channels:
                if channel == NotificationChannel.EMAIL:
                    self.send_email(stakeholder.email, subject, message)
                elif channel == NotificationChannel.SLACK:
                    # Em produção, usar webhook real
                    print(f"  [SLACK] Enviado para {stakeholder.name}")
                elif channel == NotificationChannel.SMS:
                    # Em produção, usar serviço de SMS
                    print(f"  [SMS] Enviado para {stakeholder.name}")
    
    def generate_status_page(self, incident: Incident) -> str:
        """Gera conteúdo para página de status."""
        return f"""
# Status do Sistema

## Incidente Ativo

**ID:** {incident.id}
**Título:** {incident.title}
**Status:** {incident.status}
**Severidade:** {incident.severity.value.upper()}
**Início:** {incident.created_at}
**Última atualização:** {incident.updated_at}

### Impacto
{incident.impact}

### Status Atual
{incident.summary}

### Serviços Afetados
- API Gateway: Degradado
- Serviço de Pagamento: Indisponível
- Dashboard: Funcional com dados atrasados

### Próxima Atualização
{incident.next_update}
"""


def main():
    """Demonstração do sistema de comunicação."""
    
    communicator = IncidentCommunicator()
    
    # Criar incidente de exemplo
    incident = Incident(
        id="INC-2024-001",
        title="Vazamento de dados detectado",
        severity=Severity.CRITICAL,
        status="Em andamento",
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        summary="Deteção de acesso não autorizado a dados de clientes.",
        impact="Dados de ~10.000 clientes potencialmente expostos",
        next_update="30 minutos",
        actions_taken=[
            "Containers comprometidos isolados",
            "Credenciais rotacionadas",
            "Forense iniciada"
        ],
        next_steps=[
            "Determinar escopo completo do vazamento",
            "Notificar autoridades regulatórias",
            "Preparar comunicação para clientes"
        ]
    )
    
    # Notificar stakeholders
    communicator.notify_stakeholders(incident)
    
    # Gerar status page
    status_page = communicator.generate_status_page(incident)
    print(status_page)


if __name__ == "__main__":
    main()
```

### 7.2 Templates de Comunicação

```markdown
# Templates de Comunicação para Incidentes

## Template: Notificação Inicial (Internos)

**Assunto:** [SEVERIDADE] Incidente Detectado - [TÍTULO]

**Corpo:**

Time,

Um incidente de segurança foi detectado e está sendo investigado.

**Detalhes:**
- ID do Incidente: [ID]
- Severidade: [SEVERIDADE]
- Hora da Detecção: [HORA]
- Serviços Afetados: [LISTA]
- Impacto Atual: [IMPACTO]

**Ações em Andamento:**
1. [AÇÃO 1]
2. [AÇÃO 2]
3. [AÇÃO 3]

**Próxima Atualização:** [HORA]

**Canal de Comunicação:** [SLACK/EMAIL]

---

## Template: Atualização de Status

**Assunto:** [ATUALIZAÇÃO] Incidente [ID] - Status [STATUS]

**Corpo:**

Time,

Atualização sobre o incidente [ID].

**Status Atual:** [STATUS]
**Duração:** [DURAÇÃO]

**O que aconteceu desde a última atualização:**
- [EVENTO 1]
- [EVENTO 2]

**Ações Tomadas:**
- [AÇÃO 1]
- [AÇÃO 2]

**Próximos Passos:**
- [PASSO 1]
- [PASSO 2]

**Próxima Atualização:** [HORA]

---

## Template: Resolução

**Assunto:** [RESOLVIDO] Incidente [ID] - Serviço Restaurado

**Corpo:**

Time,

O incidente [ID] foi resolvido.

**Resumo:**
- **Duração Total:** [DURAÇÃO]
- **Causa Raiz:** [CAUSA]
- **Impacto Final:** [IMPACTO]

**Ações Corretivas:**
- [AÇÃO 1]
- [AÇÃO 2]

**Próximos Passos:**
- Post-mortem agendado para [DATA]
- Documentação das lições aprendidas
- Implementação de melhorias

Obrigado pela paciência e pelo trabalho da equipe durante este incidente.

---

## Template: Comunicação para Clientes

**Assunto:** Notificação de Incidente de Segurança

**Corpo:**

Prezado(a) cliente,

Estamos escrevendo para informá-lo(a) sobre um incidente de segurança que afetou nossos sistemas.

**O que aconteceu:**
[DESCRIÇÃO SIMPLES DO INCIDENTE]

**Quando aconteceu:**
[PERÍODO]

**Dados afetados:**
[TIPOS DE DADOS AFETADOS]

**O que estamos fazendo:**
1. [AÇÃO 1]
2. [AÇÃO 2]
3. [AÇÃO 3]

**O que você pode fazer:**
- [RECOMENDAÇÃO 1]
- [RECOMENDAÇÃO 2]

**Mais informações:**
Estamos disponíveis para responder suas dúvidas através de [CANAL].

Pedimos desculpas pelo inconveniente e reafirmamos nosso compromisso com a segurança de seus dados.

Atenciosamente,
[EQUIPE DE SEGURANÇA]

---

## Template: Comunicação para Mídia

**Assunto:** Nota Oficial - Incidente de Segurança

**Corpo:**

[NOME DA EMPRESA] confirmou que identificou e está respondendo a um incidente de segurança que afeta [ESCPO].

**Resumo do Incidente:**
Em [DATA], nossa equipe de segurança identificou [DESCRIÇÃO BREVE].

**Ações Imediatas:**
1. Isolamos os sistemas afetados
2. Iniciamos investigação forense
3. Notificamos as autoridades competentes
4. Implementamos medidas de contenção

**Status Atual:**
O incidente está sob controle e nossos sistemas estão operando normalmente.

**Compromisso com a Segurança:**
[NOME DA EMPRESA] leva a segurança dos dados muito a sério. Estamos trabalhando para garantir que todos os sistemas estejam protegidos.

**Contato para Imprensa:**
[EMAIL]
[TELEFONE]
```

---

## 8. Revisão Pós-Incidente

### 8.1 Post-Mortem Sem Culpa (Blameless)

```python
#!/usr/bin/env python3
"""
postmortem.py - Sistema de post-mortem sem culpa.
Gerencia análise pós-incidente focada em melhorias, não punição.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class TimelineEvent:
    """Evento na linha do tempo do incidente."""
    timestamp: str
    event: str
    actor: str
    impact: str


@dataclass
class ActionItem:
    """Item de ação pós-incidente."""
    id: str
    description: str
    owner: str
    priority: str
    due_date: str
    status: str = "open"


@dataclass
class PostMortem:
    """Post-mortem de um incidente."""
    incident_id: str
    title: str
    date: str
    duration: str
    severity: str
    author: str
    
    # Resumo executivo
    executive_summary: str
    
    # Linha do tempo
    timeline: List[TimelineEvent]
    
    # Impacto
    impact_summary: str
    users_affected: int
    revenue_impact: str
    data_impact: str
    
    # Causa raiz
    root_cause: str
    contributing_factors: List[str]
    
    # O que deu certo
    what_went_well: List[str]
    
    # O que poderia ter sido melhor
    what_could_improve: List[str]
    
    # Lições aprendidas
    lessons_learned: List[str]
    
    # Ações corretivas
    action_items: List[ActionItem]
    
    # Métricas
    detection_time: str
    response_time: str
    resolution_time: str


class PostMortemGenerator:
    """Gera post-mortems estruturados."""
    
    def __init__(self):
        self.questions = self._load_questionnaire()
    
    def _load_questionnaire(self) -> Dict[str, List[str]]:
        """Carrega questionário para coleta de informações."""
        return {
            "detection": [
                "Como o incidente foi detectado?",
                "Quanto tempo levou para detectar?",
                "O alerta correto foi acionado?",
                "A severidade foi classificada corretamente?",
            ],
            "response": [
                "Quem foi notificado primeiro?",
                "O runbook foi seguido?",
                "Houve bloqueios na resposta?",
                "As ferramentas funcionaram conforme esperado?",
            ],
            "resolution": [
                "Qual foi a causa raiz?",
                "Havia preventivo disponível?",
                "A contenção foi efetiva?",
                "A recuperação foi completa?",
            ],
            "process": [
                "A comunicação foi efetiva?",
                "Os papéis estavam claros?",
                "Havia redundância na equipe?",
                "O escopo do incidente foi bem delimitado?",
            ],
        }
    
    def generate_template(self) -> PostMortem:
        """Gera template de post-mortem."""
        return PostMortem(
            incident_id="[ID]",
            title="[TÍTULO DO INCIDENTE]",
            date="[DATA]",
            duration="[DURAÇÃO]",
            severity="[SEVERIDADE]",
            author="[AUTOR]",
            executive_summary="[RESUMO EXECUTIVO - 2-3 parágrafos]",
            timeline=[],
            impact_summary="[RESUMO DO IMPACTO]",
            users_affected=0,
            revenue_impact="[IMPACTO FINANCEIRO]",
            data_impact="[IMPACTO EM DADOS]",
            root_cause="[CAUSA RAIZ]",
            contributing_factors=[],
            what_went_well=[],
            what_could_improve=[],
            lessons_learned=[],
            action_items=[],
            detection_time="[TEMPO DE DETECÇÃO]",
            response_time="[TEMPO DE RESPOSTA]",
            resolution_time="[TEMPO DE RESOLUÇÃO]",
        )
    
    def generate_report(self, postmortem: PostMortem) -> str:
        """Gera relatório de post-mortem formatado."""
        
        report = f"""
# Post-Mortem: {postmortem.title}

## Informações Gerais

| Campo | Valor |
|-------|-------|
| ID do Incidente | {postmortem.incident_id} |
| Data | {postmortem.date} |
| Duração | {postmortem.duration} |
| Severidade | {postmortem.severity} |
| Autor | {postmortem.author} |

## Resumo Executivo

{postmortem.executive_summary}

## Métricas de Resposta

| Métrica | Valor |
|---------|-------|
| Tempo de Detecção | {postmortem.detection_time} |
| Tempo de Resposta | {postmortem.response_time} |
| Tempo de Resolução | {postmortem.resolution_time} |

## Impacto

**Resumo:** {postmortem.impact_summary}

- Usuários Afetados: {postmortem.users_affected:,}
- Impacto Financeiro: {postmortem.revenue_impact}
- Impacto em Dados: {postmortem.data_impact}

## Linha do Tempo

| Hora | Evento | Responsável | Impacto |
|------|--------|-------------|---------|
"""
        
        for event in postmortem.timeline:
            report += f"| {event.timestamp} | {event.event} | {event.actor} | {event.impact} |\n"
        
        report += f"""

## Causa Raiz

{postmortem.root_cause}

### Fatores Contribuintes

"""
        for factor in postmortem.contributing_factors:
            report += f"- {factor}\n"
        
        report += "\n## O que Deu Certo\n\n"
        for item in postmortem.what_went_well:
            report += f"- {item}\n"
        
        report += "\n## O que Poderia Ter Sido Melhor\n\n"
        for item in postmortem.what_could_improve:
            report += f"- {item}\n"
        
        report += "\n## Lições Aprendidas\n\n"
        for lesson in postmortem.lessons_learned:
            report += f"- {lesson}\n"
        
        report += "\n## Itens de Ação\n\n"
        report += "| ID | Descrição | Responsável | Prioridade | Prazo | Status |\n"
        report += "|----|-----------|-------------|------------|-------|--------|\n"
        
        for action in postmortem.action_items:
            report += f"| {action.id} | {action.description} | {action.owner} | {action.priority} | {action.due_date} | {action.status} |\n"
        
        report += "\n---\n\n"
        report += "*Este post-mortem foi conduzido em um ambiente sem culpa, focado em melhorias de sistema e processo.*\n"
        
        return report
    
    def conduct_interview(self) -> Dict[str, List[str]]:
        """Conduz entrevista para coleta de informações."""
        responses = {}
        
        print("=== ENTREVISTA PÓS-INCIDENTE ===\n")
        print("Por favor, responda as perguntas abaixo.")
        print("Use 'fim' para terminar cada resposta.\n")
        
        for section, questions in self.questions.items():
            print(f"\n### {section.upper()}\n")
            responses[section] = []
            
            for question in questions:
                print(f"\nPergunta: {question}")
                response_lines = []
                
                while True:
                    line = input("> ")
                    if line.lower() == "fim":
                        break
                    response_lines.append(line)
                
                responses[section].append({
                    "question": question,
                    "response": "\n".join(response_lines)
                })
        
        return responses


def main():
    """Demonstração do sistema de post-mortem."""
    
    generator = PostMortemGenerator()
    
    # Criar post-mortem de exemplo
    postmortem = PostMortem(
        incident_id="INC-2024-001",
        title="Vazamento de Dados de Clientes",
        date="2024-01-15",
        duration="4 horas",
        severity="Crítico",
        author="Equipe de Segurança",
        executive_summary="Em 15 de janeiro de 2024, detectamos acesso não autorizado a dados de clientes através de uma vulnerabilidade na API. O incidente durou 4 horas e afetou aproximadamente 10.000 clientes. A resposta foi rápida e eficaz, contendo o incidente em 30 minutos após a detecção.",
        timeline=[
            TimelineEvent("14:00", "Vulnerabilidade explorada", "Atacante", "Alto"),
            TimelineEvent("14:15", "Alerta de segurança disparado", "Sistema", "Médio"),
            TimelineEvent("14:30", "Equipe mobilizada", "Incident Commander", "Médio"),
            TimelineEvent("15:00", "Containers isolados", "Security Lead", "Baixo"),
            TimelineEvent("16:00", "Credenciais rotacionadas", "DevOps", "Baixo"),
            TimelineEvent("18:00", "Incidente resolvido", "Time", "Nenhum"),
        ],
        impact_summary="Dados de clientes expostos por 2 horas. Nenhum dado financeiro comprometido.",
        users_affected=10000,
        revenue_impact="R$ 50.000 em custos de resposta",
        data_impact="Nomes, emails e telefones de clientes",
        root_cause="Validação de entrada insuficiente na API de pagamento",
        contributing_factors=[
            "Falta de rate limiting na API",
            "Monitoramento inadequado de endpoints sensíveis",
            "Ausência de WAF com regras específicas",
        ],
        what_went_well=[
            "Detecção rápida em 15 minutos",
            "Isolamento efetivo dos containers",
            "Comunicação clara entre as equipes",
            "Preservação de evidências forenses",
        ],
        what_could_improve=[
            "Rate limiting não estava configurado",
            "WAF não tinha regra para este vetor",
            "Runbooks precisavam de atualização",
            "Testes de segurança não cobriam este cenário",
        ],
        lessons_learned=[
            "Validação de entrada deve ser testada em todos os endpoints",
            "Rate limiting é essencial para APIs públicas",
            "WAF deve ter regras customizadas para cada aplicação",
            "Runbooks devem ser revisados trimestralmente",
        ],
        action_items=[
            ActionItem("AI-001", "Implementar rate limiting", "DevOps", "Alta", "2024-01-22", "em andamento"),
            ActionItem("AI-002", "Atualizar regras WAF", "Segurança", "Alta", "2024-01-20", "em andamento"),
            ActionItem("AI-003", "Revisar runbooks", "Segurança", "Média", "2024-02-01", "aberto"),
            ActionItem("AI-004", "Adicionar testes de segurança", "QA", "Média", "2024-02-15", "aberto"),
        ],
        detection_time="15 minutos",
        response_time="30 minutos",
        resolution_time="4 horas",
    )
    
    # Gerar relatório
    report = generator.generate_report(postmortem)
    print(report)
    
    # Salvar relatório
    with open("postmortem-INC-2024-001.md", "w") as f:
        f.write(report)
    
    print("\nRelatório salvo em: postmortem-INC-2024-001.md")


if __name__ == "__main__":
    main()
```

---

## 9. Chaos Engineering para Resposta a Incidentes

### 9.1 Conceitos do Chaos Monkey

```python
#!/usr/bin/env python3
"""
chaos_engineering.py - Framework de Chaos Engineering para preparação de incidentes.
Implementa injeções de falhas controladas para testar resiliência.
"""

import random
import time
import subprocess
import json
from dataclasses import dataclass
from typing import List, Callable, Dict
from enum import Enum


class FailureType(Enum):
    """Tipos de falha que podem ser injetados."""
    POD_KILL = "pod_kill"
    NETWORK_LATENCY = "network_latency"
    NETWORK_PARTITION = "network_partition"
    CPU_STRESS = "cpu_stress"
    MEMORY_STRESS = "memory_stress"
    DISK_FILL = "disk_fill"
    SERVICE_DEPENDENCY_FAILURE = "service_dependency_failure"


@dataclass
class ChaosExperiment:
    """Define um experimento de chaos."""
    name: str
    description: str
    failure_type: FailureType
    target: str
    duration: int  # segundos
    steady_state_hypothesis: str
    rollback_action: str


class ChaosEngine:
    """Executa experimentos de chaos engineering."""
    
    def __init__(self, namespace: str = "production"):
        self.namespace = namespace
        self.experiments_history = []
    
    def log(self, message: str):
        """Registra mensagem."""
        print(f"[CHAOS] {message}")
    
    def create_experiment_kill_pod(self, 
                                    app_name: str,
                                    duration: int = 300) -> ChaosExperiment:
        """Cria experimento para matar pods aleatoriamente."""
        return ChaosExperiment(
            name=f"kill-pod-{app_name}",
            description=f"Matar pods aleatórios de {app_name} por {duration}s",
            failure_type=FailureType.POD_KILL,
            target=app_name,
            duration=duration,
            steady_state_hypothesis=f"O serviço {app_name} continua respondendo com latência < 500ms",
            rollback_action="Remover label de chaos e aguardar pods reiniciarem"
        )
    
    def create_experiment_network_latency(self,
                                           app_name: str,
                                           latency_ms: int = 500,
                                           duration: int = 300) -> ChaosExperiment:
        """Cria experimento de latência de rede."""
        return ChaosExperiment(
            name=f"network-latency-{app_name}",
            description=f"Adicionar {latency_ms}ms de latência em {app_name}",
            failure_type=FailureType.NETWORK_LATENCY,
            target=app_name,
            duration=duration,
            steady_state_hypothesis=f"O serviço {app_name} continua funcionando com latência elevada",
            rollback_action="Remover regra de latência"
        )
    
    def create_experiment_dependency_failure(self,
                                              service: str,
                                              dependency: str,
                                              duration: int = 300) -> ChaosExperiment:
        """Cria experimento de falha de dependência."""
        return ChaosExperiment(
            name=f"dependency-failure-{service}-{dependency}",
            description=f"Simular falha de {dependency} para {service}",
            failure_type=FailureType.SERVICE_DEPENDENCY_FAILURE,
            target=service,
            duration=duration,
            steady_state_hypothesis=f"O serviço {service} degrada graciosamente quando {dependency} falha",
            rollback_action="Restaurar conectividade com a dependência"
        )
    
    def execute_kill_pod(self, experiment: ChaosExperiment) -> bool:
        """Executa experimento de kill pod."""
        self.log(f"Iniciando: {experiment.name}")
        
        # Encontrar pods alvo
        cmd = [
            "kubectl", "get", "pods",
            "-n", self.namespace,
            "-l", f"app={experiment.target}",
            "-o", "jsonpath={.items[*].metadata.name}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout.strip():
            self.log("Nenhum pod encontrado")
            return False
        
        pods = result.stdout.strip().split()
        target_pod = random.choice(pods)
        
        self.log(f"Matando pod: {target_pod}")
        
        cmd = ["kubectl", "delete", "pod", target_pod, 
               "-n", self.namespace, "--grace-period=0"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log(f"Pod {target_pod} deletado")
            
            # Aguardar pods reiniciarem
            time.sleep(30)
            
            # Verificar se o serviço está saudável
            return self.verify_service_health(experiment.target)
        
        return False
    
    def execute_network_latency(self, experiment: ChaosExperiment,
                                 latency_ms: int = 500) -> bool:
        """Executa experimento de latência de rede."""
        self.log(f"Iniciando latência de rede: {experiment.name}")
        
        # Criar NetworkPolicy com latência usando tc
        cmd = [
            "kubectl", "exec", "-n", self.namespace,
            f"deploy/{experiment.target}", "--",
            "tc", "qdisc", "add", "dev", "eth0", "root",
            "netem", "delay", f"{latency_ms}ms"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.log(f"Latência de {latency_ms}ms aplicada")
            
            # Aguardar duração do experimento
            time.sleep(experiment.duration)
            
            # Remover latência
            cmd_remove = [
                "kubectl", "exec", "-n", self.namespace,
                f"deploy/{experiment.target}", "--",
                "tc", "qdisc", "del", "dev", "eth0", "root"
            ]
            subprocess.run(cmd_remove, capture_output=True, text=True)
            
            self.log("Latência removida")
            return True
        
        return False
    
    def verify_service_health(self, service: str) -> bool:
        """Verifica saúde de um serviço."""
        cmd = [
            "kubectl", "get", "pods",
            "-n", self.namespace,
            "-l", f"app={service}",
            "-o", "json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False
        
        pods = json.loads(result.stdout)
        
        running_pods = sum(
            1 for pod in pods.get("items", [])
            if pod.get("status", {}).get("phase") == "Running"
        )
        
        return running_pods > 0
    
    def execute_experiment(self, experiment: ChaosExperiment) -> bool:
        """Executa um experimento de chaos."""
        self.log(f"=== EXECUTANDO: {experiment.name} ===")
        self.log(f"Descrição: {experiment.description}")
        self.log(f"Hipótese: {experiment.steady_state_hypothesis}")
        
        start_time = time.time()
        
        try:
            if experiment.failure_type == FailureType.POD_KILL:
                success = self.execute_kill_pod(experiment)
            elif experiment.failure_type == FailureType.NETWORK_LATENCY:
                success = self.execute_network_latency(experiment)
            else:
                self.log(f"Tipo de falha não implementado: {experiment.failure_type}")
                return False
        except Exception as e:
            self.log(f"Erro durante experimento: {e}")
            success = False
        
        duration = time.time() - start_time
        
        result = {
            "experiment": experiment.name,
            "success": success,
            "duration": duration,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        self.experiments_history.append(result)
        
        self.log(f"=== RESULTADO: {'PASSOU' if success else 'FALHOU'} ===")
        
        return success
    
    def generate_report(self) -> str:
        """Gera relatório dos experimentos."""
        report = [
            "=" * 70,
            "RELATÓRIO DE CHAOS ENGINEERING",
            "=" * 70,
            f"Data: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total de experimentos: {len(self.experiments_history)}",
            "",
        ]
        
        passed = sum(1 for r in self.experiments_history if r['success'])
        failed = len(self.experiments_history) - passed
        
        report.append(f"Passaram: {passed}")
        report.append(f"Falharam: {failed}")
        report.append("")
        report.append("DETALHES:")
        report.append("-" * 70)
        
        for result in self.experiments_history:
            status = "PASSOU" if result['success'] else "FALHOU"
            report.append(f"  {result['experiment']}: {status} ({result['duration']:.1f}s)")
        
        report.append("=" * 70)
        
        return "\n".join(report)


def main():
    """Demonstração do framework de chaos engineering."""
    
    engine = ChaosEngine(namespace="production")
    
    # Criar experimentos
    experiments = [
        engine.create_experiment_kill_pod("api-gateway", duration=60),
        engine.create_experiment_network_latency("auth-service", latency_ms=200, duration=120),
        engine.create_experiment_dependency_failure("payment-service", "database", duration=60),
    ]
    
    print("=== PLANO DE CHAOS ENGINEERING ===\n")
    for exp in experiments:
        print(f"- {exp.name}: {exp.description}")
        print(f"  Hipótese: {exp.steady_state_hypothesis}")
        print()
    
    # Em produção, descomente para executar:
    # for exp in experiments:
    #     engine.execute_experiment(exp)
    #     time.sleep(30)  # Pausa entre experimentos
    
    # print(engine.generate_report())
    
    print("Framework de Chaos Engineering pronto para uso")


if __name__ == "__main__":
    main()
```

### 9.2 Game Days e Drills de Resposta

```yaml
# game-day-plan.yaml
# Plano de Game Day para treinamento de resposta a incidentes

game_day:
  name: "Exercise Blackout 2024"
  date: "2024-02-15"
  duration: "4 horas"
  organizer: "Equipe de Segurança"
  
  objectives:
    - "Testar tempo de detecção de incidentes"
    - "Validar runbooks em cenários reais"
    - "Avaliar comunicação entre equipes"
    - "Identificar gaps no processo de resposta"
  
  scenarios:
    - name: "Cenário 1: Vazamento de Credenciais"
      type: "credentialexposure"
      difficulty: "média"
      expected_duration: "45 minutos"
      injected_failure:
        type: "secret_leak"
        target: "production-secrets"
        method: "Adicionar credencial falsa em repositório público"
      success_criteria:
        - "Detecção em até 15 minutos"
        - "Credencial rotacionada em até 30 minutos"
        - "Comunicação enviada em até 10 minutos"
    
    - name: "Cenário 2: Ataque DDoS"
      type: "availability"
      difficulty: "alta"
      expected_duration: "60 minutos"
      injected_failure:
        type: "traffic_spike"
        target: "api-gateway"
        method: "Simular tráfego 10x maior que o normal"
      success_criteria:
        - "Rate limiting ativado automaticamente"
        - "Serviço permaneceu disponível"
        - "Escalação automática funcionou"
    
    - name: "Cenário 3: Comprometimento de Container"
      type: "security"
      difficulty: "alta"
      expected_duration: "90 minutos"
      injected_failure:
        type: "container_compromise"
        target: "auth-service"
        method: "Inserir processo suspeito em container"
      success_criteria:
        - "Container isolado em até 10 minutos"
        - "Evidências coletadas corretamente"
        - "Rollback executado com sucesso"
  
  participants:
    - role: "Incident Commander"
      name: "[NOME]"
      responsibilities:
        - "Coordenar a resposta"
        - "Tomar decisões de escalação"
        - "Gerenciar comunicação"
    
    - role: "Security Lead"
      name: "[NOME]"
      responsibilities:
        - "Análise técnica do incidente"
        - "Contenção e erradicação"
        - "Coleta de evidências"
    
    - role: "DevOps Lead"
      name: "[NOME]"
      responsibilities:
        - "Executar ações técnicas"
        - "Rollback de serviços"
        - "Restauração de sistemas"
    
    - role: "Communications Lead"
      name: "[NOME]"
      responsibilities:
        - "Notificar stakeholders"
        - "Atualizar status page"
        - "Gerenciar comunicação externa"
  
  evaluation:
    metrics:
      - name: "Mean Time to Detect (MTTD)"
        target: "< 15 minutos"
        actual: "[A PREENCHER]"
      
      - name: "Mean Time to Respond (MTTR)"
        target: "< 30 minutos"
        actual: "[A PREENCHER]"
      
      - name: "Mean Time to Resolve"
        target: "< 2 horas"
        actual: "[A PREENCHER]"
    
    checklist:
      - "Todos os participantes foram notificados?"
      - "O Incident Commander assumiu controle rapidamente?"
      - "Os runbooks foram seguidos corretamente?"
      - "A comunicação fluiu sem gargalos?"
      - "As evidências foram preservadas?"
      - "O rollback foi executado com sucesso?"
  
  post_game_day:
    - action: "Retrospectiva"
      timeframe: "Imediatamente após o game day"
      participants: "Todos os participantes"
    
    - action: "Documentação de lições"
      timeframe: "24 horas"
      responsible: "Security Lead"
    
    - action: "Atualização de runbooks"
      timeframe: "1 semana"
      responsible: "Equipe de Segurança"
    
    - action: "Correção de gaps identificados"
      timeframe: "2 semanas"
      responsible: "DevOps Lead"
```

---

## 10. Exemplo Completo: Pipeline de Resposta a Incidentes

### 10.1 Pipeline Integrado

```yaml
# incident-response-pipeline.yaml
# Pipeline completa de resposta a incidentes
# Detecção → Triage → Contenção → Erradicação → Recuperação → Revisão

name: "Incident Response Pipeline"
on:
  repository_dispatch:
    types: [incident-detected]
  workflow_dispatch:
    inputs:
      incident_type:
        description: "Tipo de incidente"
        required: true
        type: choice
        options:
          - compromised_container
          - leaked_secret
          - vulnerability_production
          - ddos_attack
          - data_breach
      severity:
        description: "Severidade"
        required: true
        type: choice
        options:
          - critical
          - high
          - medium
          - low
      target_service:
        description: "Serviço afetado"
        required: true
        type: string

env:
  INCIDENT_ID: "INC-${{ github.run_number }}-$(date +%s)"
  EVIDENCE_DIR: "/tmp/incident-evidence"
  SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
  PAGERDUTY_KEY: ${{ secrets.PAGERDUTY_KEY }}

jobs:
  # Fase 1: Detecção e Triagem
  detection-triage:
    runs-on: ubuntu-latest
    outputs:
      incident_id: ${{ steps.create_incident.outputs.incident_id }}
      severity: ${{ github.event.inputs.severity }}
      requires_immediate_action: ${{ steps.assess.outputs.immediate_action }}
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Create Incident Record
        id: create_incident
        run: |
          INCIDENT_ID="INC-$(date +%Y%m%d-%H%M%S)"
          echo "incident_id=${INCIDENT_ID}" >> $GITHUB_OUTPUT
          
          # Criar registro do incidente
          mkdir -p ${EVIDENCE_DIR}
          
          cat > ${EVIDENCE_DIR}/incident-metadata.json << EOF
          {
            "id": "${INCIDENT_ID}",
            "type": "${{ github.event.inputs.incident_type }}",
            "severity": "${{ github.event.inputs.severity }}",
            "target": "${{ github.event.inputs.target_service }}",
            "detected_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "detected_by": "automated-pipeline",
            "status": "triaging"
          }
          EOF
      
      - name: Initial Assessment
        id: assess
        run: |
          # Avaliação inicial do incidente
          SEVERITY="${{ github.event.inputs.severity }}"
          
          if [[ "${SEVERITY}" == "critical" ]] || [[ "${SEVERITY}" == "high" ]]; then
            echo "immediate_action=true" >> $GITHUB_OUTPUT
          else
            echo "immediate_action=false" >> $GITHUB_OUTPUT
          fi
      
      - name: Notify Stakeholders
        if: steps.assess.outputs.immediate_action == 'true'
        run: |
          # Notificar stakeholders imediatamente
          curl -X POST "${SLACK_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d '{
              "text": "🚨 INCIDENTE DETECTADO\nID: ${{ steps.create_incident.outputs.incident_id }}\nTipo: ${{ github.event.inputs.incident_type }}\nSeveridade: ${{ github.event.inputs.severity }}\nServiço: ${{ github.event.inputs.target_service }}"
            }'
      
      - name: Create PagerDuty Alert
        if: steps.assess.outputs.immediate_action == 'true'
        run: |
          curl -X POST "https://events.pagerduty.com/v2/enqueue" \
            -H "Content-Type: application/json" \
            -d '{
              "routing_key": "${PAGERDUTY_KEY}",
              "event_action": "trigger",
              "payload": {
                "summary": "Incidente: ${{ github.event.inputs.incident_type }}",
                "severity": "${{ github.event.inputs.severity }}",
                "source": "github-actions",
                "component": "${{ github.event.inputs.target_service }}",
                "custom_details": {
                  "incident_id": "${{ steps.create_incident.outputs.incident_id }}"
                }
              }
            }'
      
      - name: Upload Evidence
        uses: actions/upload-artifact@v4
        with:
          name: incident-evidence-initial
          path: ${{ env.EVIDENCE_DIR }}

  # Fase 2: Containment
  containment:
    needs: detection-triage
    runs-on: ubuntu-latest
    if: needs.detection-triage.outputs.requires_immediate_action == 'true'
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Kubernetes
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      
      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Isolate Compromised Resources
        run: |
          SERVICE="${{ github.event.inputs.target_service }}"
          NAMESPACE="production"
          
          echo "Isolando recursos do serviço: ${SERVICE}"
          
          # Criar NetworkPolicy de isolamento
          cat <<EOF | kubectl apply -f -
          apiVersion: networking.k8s.io/v1
          kind: NetworkPolicy
          metadata:
            name: incident-isolate-${SERVICE}
            namespace: ${NAMESPACE}
          spec:
            podSelector:
              matchLabels:
                app: ${SERVICE}
            policyTypes:
            - Ingress
            - Egress
            ingress: []
            egress: []
          EOF
          
          echo "Servidor isolado da rede"
      
      - name: Collect Forensic Evidence
        run: |
          SERVICE="${{ github.event.inputs.target_service }}"
          NAMESPACE="production"
          EVIDENCE_DIR="${{ env.EVIDENCE_DIR }}/forensics"
          
          mkdir -p ${EVIDENCE_DIR}
          
          # Coletar evidências
          kubectl get pods -n ${NAMESPACE} -l app=${SERVICE} -o yaml > ${EVIDENCE_DIR}/pods.yaml
          kubectl logs -l app=${SERVICE} -n ${NAMESPACE} --all-containers > ${EVIDENCE_DIR}/logs.txt 2>/dev/null || true
          kubectl describe deployment ${SERVICE} -n ${NAMESPACE} > ${EVIDENCE_DIR}/deployment.txt
          
          # Verificar vulnerabilidades
          IMAGE=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}')
          trivy image --severity HIGH,CRITICAL ${IMAGE} > ${EVIDENCE_DIR}/vulnerabilities.txt 2>/dev/null || true
          
          echo "Evidências coletadas em: ${EVIDENCE_DIR}"
      
      - name: Upload Forensic Evidence
        uses: actions/upload-artifact@v4
        with:
          name: forensic-evidence
          path: ${{ env.EVIDENCE_DIR }}/forensics

  # Fase 3: Erradicação e Recuperação
  eradication-recovery:
    needs: containment
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Kubernetes
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.28.0'
      
      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Execute Rollback
        run: |
          SERVICE="${{ github.event.inputs.target_service }}"
          NAMESPACE="production"
          
          echo "Executando rollback de: ${SERVICE}"
          
          # Rollback para versão anterior
          kubectl rollout undo deployment/${SERVICE} -n ${NAMESPACE}
          
          # Aguardar estabilização
          kubectl rollout status deployment/${SERVICE} -n ${NAMESPACE} --timeout=300s
      
      - name: Remove Isolation
        run: |
          SERVICE="${{ github.event.inputs.target_service }}"
          NAMESPACE="production"
          
          # Remover NetworkPolicy de isolamento
          kubectl delete networkpolicy incident-isolate-${SERVICE} -n ${NAMESPACE} --ignore-not-found
      
      - name: Verify Recovery
        run: |
          SERVICE="${{ github.event.inputs.target_service }}"
          NAMESPACE="production"
          
          echo "Verificando recuperação do serviço..."
          
          # Aguardar pods ficarem prontos
          sleep 30
          
          # Verificar status
          READY=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} \
            -o jsonpath='{.status.readyReplicas}')
          DESIRED=$(kubectl get deployment ${SERVICE} -n ${NAMESPACE} \
            -o jsonpath='{.spec.replicas}')
          
          if [[ "${READY}" -ge "${DESIRED}" ]]; then
            echo "Serviço recuperado: ${READY}/${DESIRED} replicas prontas"
          else
            echo "AVISO: Serviço não recuperou completamente: ${READY}/${DESIRED}"
            exit 1
          fi
      
      - name: Rotate Secrets
        run: |
          echo "Verificando se rotação de segredos é necessária..."
          # Implementar rotação conforme necessário
          # aws secretsmanager rotate-secret --secret-id prod/db/password
      
      - name: Update Incident Status
        run: |
          curl -X PATCH "${{ github.api_url }}/repos/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
            -H "Authorization: token ${{ github.token }}" \
            -H "Accept: application/vnd.github.v3+json" \
            -d '{"conclusion": "success"}'

  # Fase 4: Revisão Pós-Incidente
  post-incident-review:
    needs: eradication-recovery
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Generate Post-Mortem Template
        run: |
          INCIDENT_ID="${{ needs.detection-triage.outputs.incident_id }}"
          
          cat > postmortem-${INCIDENT_ID}.md << EOF
          # Post-Mortem: ${INCIDENT_ID}
          
          ## Informações Gerais
          - **ID:** ${INCIDENT_ID}
          - **Data:** $(date -u +%Y-%m-%d)
          - **Tipo:** ${{ github.event.inputs.incident_type }}
          - **Severidade:** ${{ github.event.inputs.severity }}
          - **Serviço:** ${{ github.event.inputs.target_service }}
          
          ## Resumo Executivo
          [Preencher]
          
          ## Linha do Tempo
          [Preencher]
          
          ## Causa Raiz
          [Preencher]
          
          ## O que Deu Certo
          [Preencher]
          
          ## O que Poderia Melhorar
          [Preencher]
          
          ## Lições Aprendidas
          [Preencher]
          
          ## Ações Corretivas
          [Preencher]
          EOF
          
          echo "Template de post-mortem gerado: postmortem-${INCIDENT_ID}.md"
      
      - name: Schedule Post-Mortem Meeting
        run: |
          echo "Agendando reunião de post-mortem..."
          # Integrar com Google Calendar ou similar
          # Em produção, enviar convite via API
      
      - name: Create Follow-up Issues
        run: |
          echo "Criando issues de acompanhamento..."
          # Criar issues no GitHub para ações corretivas
          # gh issue create --title "Post-mortem action: [ACTION]" --label "incident-followup"
      
      - name: Send Final Notification
        run: |
          curl -X POST "${SLACK_WEBHOOK}" \
            -H "Content-Type: application/json" \
            -d '{
              "text": "✅ INCIDENTE RESOLVIDO\nID: ${{ needs.detection-triage.outputs.incident_id }}\nServiço: ${{ github.event.inputs.target_service }}\nDuração: $(($(date +%s) - START_TIME)) segundos"
            }'
      
      - name: Upload All Evidence
        uses: actions/upload-artifact@v4
        with:
          name: incident-evidence-complete
          path: |
            ${{ env.EVIDENCE_DIR }}
            postmortem-*.md
          retention-days: 90
```

---

## 11. Referências

### 11.1 Documentos e Frameworks

1. **NIST SP 800-61 Rev. 2** - Computer Security Incident Handling Guide
   - Framework fundamental para tratamento de incidentes
   - Disponível em: https://csrc.nist.gov/publications/detail/sp/800-61/rev-2/final

2. **SANS Incident Handler's Handbook**
   - Guia prático para equipes de resposta
   - Disponível em: https://www.sans.org/white-papers/incident-handlers-handbook/

3. **MITRE ATT&CK Framework**
   - Base de conhecimento de táticas e técnicas de adversários
   - Disponível em: https://attack.mitre.org/

4. **FIRST PSIRT Services Framework**
   - Framework para equipes de segurança de produto
   - Disponível em: https://www.first.org/standards/frameworks/psirt/

5. **ISO/IEC 27035**
   - Padrão internacional para gestão de incidentes de segurança
   - Cobertura completa de processo e gestão

### 11.2 Ferramentas de Resposta a Incidentes

| Ferramenta | Uso | Licença |
|-----------|-----|---------|
| Velociraptor | Forense endpoint | Open Source |
| TheHive | Orquestração de resposta | Open Source |
| Cortex | Análise de indicadores | Open Source |
| GRR | Forense de hosts | Open Source |
| OSSEC | IDS host-based | Open Source |
| Suricata | IDS/IPS de rede | Open Source |
| Wireshark | Análise de pacotes | Open Source |
| Volatility | Memory forensics | Open Source |

### 11.3 Cursos e Certificações

- **GCIH** - GIAC Certified Incident Handler
- **GCFE** - GIAC Certified Forensic Examiner
- **GNFA** - GIAC Network Forensic Analyst
- **eCDFP** - Certified Digital Forensics Professional
- **CHFI** - Computer Hacking Forensic Investigator

### 11.4 Casos Documentados de Incidentes

#### Target Breach (2013)

**Resumo:** Atacantes acessaram a rede da Target através de credenciais roubadas de um fornecedor de HVAC, comprometendo 40 milhões de cartões de crédito e 70 milhões de registros de clientes.

**Falhas de Detecção:**
- Alertas do FireEye foram ignorados por semanas
- Equipe de segurança não tinha processos claros de triagem
- Falta de segmentação de rede permitiu movimentação lateral
- Vendor management deficiente

**Lições Aprendidas:**
- Monitorar e responder a alertas de segurança rapidamente
- Implementar segmentação de rede robusta
- Revisar acessos de terceiros e fornecedores
- Não depender apenas de uma ferramenta de detecção

#### Equifax (2017)

**Resumo:** Vulnerabilidade Apache Struts (CVE-2017-5638) explorada, expondo dados pessoais de 147 milhões de pessoas. A resposta foi extremamente lenta e mal gerenciada.

**Falhas de Resposta:**
- Notificação atrasada de 76 dias após a detecção
- Website de notificação era confuso e não funcionava
- Comunicação inconsistente e contraditória
- Falta de plano de resposta adequado

**Lições Aprendidas:**
- Ter planos de resposta prontos e testados
- Comunicação clara e transparente é essencial
- Notificar afetados rapidamente
- Investir em gestão de vulnerabilidades

#### Colonial Pipeline (2021)

**Resumo:** Ataque de ransomware forçou o shutdown do maior oleoduto dos EUA, causando escassez de combustível no sudeste.

**Resposta:**
- Pipeline desligado preventivamente
- Pagamento de resgate de $4.4 milhões
- Restauração gradual ao longo de dias
- Investigação conjunta com FBI

**Lições Aprendidas:**
- Ter planos de continuidade para infraestrutura crítica
- Segregar redes corporativas e operacionais
- Testar恢复 de ransomware regularmente
- Avaliar riscos de pagamentos de resgate

#### SolarWinds (2020)

**Resumo:** Ataque de supply chain que comprometeu o software Orion, afetando múltiplas agências governamentais e empresas.

**Desafios de Resposta:**
- Comprometimento era difícil de detectar
- Atacantes tinham persistência avançada
- Múltiplos vetores de entrada
- Difícil determinar escopo completo

**Lições Aprendidas:**
- Implementar verificação de integridade de software
- Monitorar comportamento de aplicações
- Ter visibilidade completa da cadeia de suprimentos
- Resposta coordenada entre múltiplas organizações

#### Log4Shell (2021)

**Resumo:** Vulnerabilidade crítica no Log4j (CVE-2021-44228) que afetou milhões de aplicações Java em todo o mundo.

**Resposta Coordenada:**
- Divulgação coordenada com Apache
- Atualizações rápidas de bibliotecas
- Mitigação via configuração para quem não podia atualizar
- Scans massivos de identificação

**Lições Aprendidas:**
- Manter inventário completo de dependências
- Ter processo ágil de atualização de bibliotecas
- Comunicação clara durante incidentes de ampla escala
- Workarounds são essenciais quando patches não são imediatos

### 11.5 Leituras Recomendadas

1. **"Incident Response" por Antier Solutions** - Guia abrangente para equipes de segurança
2. **"The Art of Incident Response" por Daniel B. Corman** - Técnicas avançadas de resposta
3. **"Blue Team Handbook" por Don Murdoch** - Referência para equipes defensivas
4. **"Site Reliability Engineering" por Google** - Práticas de operação e resposta
5. **"The Phoenix Project" por Gene Kim** - Entendendo DevOps e gestão de incidentes

---

## Resumo do Capítulo

Neste capítulo, exploramos os fundamentos e práticas avançadas de resposta a incidentes em ambientes DevOps e cloud-native. Os pontos-chave incluem:

1. **Infraestrutura Imutável** - A base para resposta rápida e segura
2. **Runbooks Automatizados** - Documentação executável que acelera a resposta
3. **Rollback Inteligente** - Estratégias para restaurar serviços rapidamente
4. **Forense de Containers** - Técnicas para analisar e isolar containers comprometidos
5. **Resposta Kubernetes** - Gerenciamento de incidentes em ambientes orquestrados
6. **Cloud Response** - Especificidades de AWS, Azure e GCP
7. **Comunicação Efetiva** - Notificação de stakeholders e gestão de crise
8. **Post-Mortem Sem Culpa** - Aprendizado contínuo com cada incidente
9. **Chaos Engineering** - Preparação proativa para incidentes

A resposta a incidentes não é apenas uma questão técnica - é um processo organizacional que requer treinamento, planejamento e melhoria contínua. Cada incidente é uma oportunidade de aprendizado e fortalecimento dos controles de segurança.

---

*Fim do Capítulo 15*
