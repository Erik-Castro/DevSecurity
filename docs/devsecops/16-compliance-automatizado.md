---
layout: default
title: "16-compliance-automatizado"
---

# Capítulo 16 — Compliance Automatizado

## Sumario

1. [Compliance e DevSecOps](#1-compliance-e-devsecops)
2. [SOC 2 Type II](#2-soc-2-type-ii)
3. [PCI DSS](#3-pci-dss)
4. [GDPR/LGPD](#4-gdprlgpd)
5. [CIS Benchmarks](#5-cis-benchmarks)
6. [OpenSCAP](#6-openscap)
7. [Policy as Code](#7-policy-as-code)
8. [Audit Trail](#8-audit-trail)
9. [Evidence Automation](#9-evidence-automation)
10. [Exemplo Completo: Compliance Pipeline](#10-exemplo-completo-compliance-pipeline)
11. [Referencias](#11-referencias)

---

## 1. Compliance e DevSecOps

### 1.1 Compliance as Code

O compliance tradicional depende de auditorias periodicas, planilhas manuais e verificacoes pontuais. Esse modelo falha em ambientes modernos de DevOps, onde a velocidade de deploy excede a capacidade de revisao humana. Compliance as Code transforma requisitos regulatórios em implementações automatizaveis, executaveis e versionaveis.

O conceito central e expressar politicas de compliance como codigo executavel. Em vez de documentar que "todas as credenciais devem ser criptografadas", voce escreve uma verificacao automatizada que bloqueia qualquer deploy sem criptografia. O codigo se torna a fonte unica de verdade sobre o que e obrigatório.

```yaml
# compliance-policy.yaml
policies:
  credential_encryption:
    name: "Todas as credenciais devem ser criptografadas"
    severity: critical
    frameworks:
      - SOC2
      - PCI_DSS
      - LGPD
    check:
      type: automated
      command: "python scripts/check_credential_encryption.py"
      remediation: "Use AWS Secrets Manager ou HashiCorp Vault"
    enforcement: block  # block | warn | audit
    auto_remediate: false

  data_at_rest_encryption:
    name: "Dados em repouso devem ser criptografados AES-256"
    severity: critical
    frameworks:
      - SOC2
      - PCI_DSS
      - GDPR
      - LGPD
    check:
      type: automated
      command: "python scripts/check_at_rest_encryption.py"
      remediation: "Habilitar criptografia KMS nos buckets e bancos"
    enforcement: block
    auto_remediate: true

  access_logging:
    name: "Todos os acessos devem ser auditados"
    severity: high
    frameworks:
      - SOC2
      - PCI_DSS
      - HIPAA
    check:
      type: automated
      command: "python scripts/check_access_logging.py"
      remediation: "Habilitar CloudTrail/Audit Log em todos os servicos"
    enforcement: block
    auto_remediate: true

  data_retention:
    name: "Dados pessoais devem respeitar politica de retencao"
    severity: high
    frameworks:
      - GDPR
      - LGPD
    check:
      type: automated
      command: "python scripts/check_data_retention.py"
      remediation: "Configurar lifecycle policies no S3 e TTL no DynamoDB"
    enforcement: warn
    auto_remediate: false
```

### 1.2 Continuous Compliance

O compliance continuo monitora o estado de conformidade em tempo real, nao apenas no momento do deploy. Um sistema pode estar em conformidade hoje e violar amanha devido a uma mudanca de configuracao, atualizacao de dependencia ou falha de operacao.

```yaml
# continuous-compliance.yaml
continuous_compliance:
  scan_interval: "every 6 hours"
  triggers:
    - on_deploy: true
    - on_config_change: true
    - on_schedule: "0 */6 * * *"
    - on_incident: true

  scope:
    - infrastructure
    - application_code
    - dependencies
    - configurations
    - access_controls
    - data_stores

  alert_channels:
    - slack: "#compliance-alerts"
    - pagerduty: "compliance-critical"
    - email: "compliance@company.com"
    - jira: "COMP"

  auto_remediation:
    enabled: true
    max_auto_fixes_per_day: 10
    require_approval_above: medium
    rollback_on_failure: true
    notification_on_remediate: true
```

### 1.3 Audit Automation

A automatizacao de auditorias elimina o vies humano e garante consistencia. Sistemas automatizados podem verificar milhares de controles em minutos, enquanto uma equipe de auditoria levaria semanas.

```python
# audit_automation.py
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class ComplianceFramework(Enum):
    SOC2 = "SOC2"
    PCI_DSS = "PCI_DSS"
    GDPR = "GDPR"
    LGPD = "LGPD"
    HIPAA = "HIPAA"
    CIS = "CIS"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ControlStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    ERROR = "error"


@dataclass
class ComplianceControl:
    control_id: str
    name: str
    description: str
    framework: ComplianceFramework
    severity: Severity
    check_command: str
    remediation: str
    auto_remediate: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class ControlResult:
    control: ComplianceControl
    status: ControlStatus
    timestamp: datetime
    details: str
    evidence: str = ""
    remediation_applied: bool = False
    execution_time_ms: int = 0


@dataclass
class AuditReport:
    report_id: str
    timestamp: datetime
    framework: ComplianceFramework
    results: List[ControlResult] = field(default_factory=list)

    @property
    def total_controls(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.FAIL)

    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == ControlStatus.WARN)

    @property
    def compliance_score(self) -> float:
        if self.total_controls == 0:
            return 0.0
        return (self.passed / self.total_controls) * 100

    def to_json(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "framework": self.framework.value,
            "summary": {
                "total": self.total_controls,
                "passed": self.passed,
                "failed": self.failed,
                "warnings": self.warnings,
                "score": f"{self.compliance_score:.1f}%"
            },
            "results": [
                {
                    "control_id": r.control.control_id,
                    "name": r.control.name,
                    "status": r.status.value,
                    "details": r.details,
                    "evidence": r.evidence,
                    "severity": r.control.severity.value,
                    "framework": r.control.framework.value
                }
                for r in self.results
            ]
        }


class ComplianceAuditor:
    def __init__(self):
        self.controls: List[ComplianceControl] = []
        self.results: List[ControlResult] = []

    def register_control(self, control: ComplianceControl):
        self.controls.append(control)

    def run_control(self, control: ComplianceControl) -> ControlResult:
        import subprocess

        try:
            start_time = datetime.now()
            result = subprocess.run(
                control.check_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            if result.returncode == 0:
                status = ControlStatus.PASS
            elif result.returncode == 1:
                status = ControlStatus.FAIL
            else:
                status = ControlStatus.ERROR

            return ControlResult(
                control=control,
                status=status,
                timestamp=datetime.now(),
                details=result.stdout.strip() or result.stderr.strip(),
                execution_time_ms=elapsed_ms
            )
        except subprocess.TimeoutExpired:
            return ControlResult(
                control=control,
                status=ControlStatus.ERROR,
                timestamp=datetime.now(),
                details="Check timed out after 300 seconds"
            )

    def run_full_audit(self, framework: ComplianceFramework) -> AuditReport:
        report = AuditReport(
            report_id=f"audit-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            timestamp=datetime.now(),
            framework=framework
        )

        relevant_controls = [
            c for c in self.controls if c.framework == framework
        ]

        for control in relevant_controls:
            result = self.run_control(control)
            report.results.append(result)

            if (result.status == ControlStatus.FAIL
                    and control.auto_remediate):
                self._attempt_remediation(control)

        return report

    def _attempt_remediation(self, control: ComplianceControl):
        print(f"[REMEDIATION] Attempting auto-remediation for {control.control_id}")

    def export_evidence(self, report: AuditReport, output_dir: str):
        import os
        os.makedirs(output_dir, exist_ok=True)

        report_path = os.path.join(output_dir, f"{report.report_id}.json")
        with open(report_path, "w") as f:
            json.dump(report.to_json(), f, indent=2)

        evidence_path = os.path.join(output_dir, f"{report.report_id}-evidence.json")
        evidence_data = []
        for result in report.results:
            evidence_data.append({
                "control_id": result.control.control_id,
                "status": result.status.value,
                "evidence": result.evidence,
                "timestamp": result.timestamp.isoformat()
            })
        with open(evidence_path, "w") as f:
            json.dump(evidence_data, f, indent=2)

        print(f"[EVIDENCE] Report exported to {report_path}")
        print(f"[EVIDENCE] Evidence exported to {evidence_path}")
```

### 1.4 Evidence Collection

A coleta automatizada de evidencias e o coracao do compliance continuo. Auditorias exigem provas concretas de que controles estao funcionando. E mais do que dizer "sim, fazemos isso" — e mostrar logs, configuracoes e resultados de verificacoes automaticas.

```yaml
# evidence-collection.yaml
evidence_pipeline:
  collection:
    sources:
      - type: cloudtrail_logs
        aws_services:
          - s3
          - iam
          - ec2
          - rds
          - lambda
          - cloudwatch
        retention_days: 365

      - type: kubernetes_audit
        cluster: production
        log_path: /var/log/kubernetes/audit/
        retention_days: 365

      - type: git_audit
        repositories: all
        events:
          - push
          - pull_request
          - merge
          - force_push
          - branch_protection_override

      - type: iam_audit
        providers:
          - aws_iam
          - azure_ad
          - okta
        events:
          - login
          - privilege_escalation
          - role_assumption
          - policy_change

      - type: infrastructure_changes
        tools:
          - terraform
          - cloudformation
          - ansible
        events:
          - plan
          - apply
          - destroy

  storage:
    provider: s3
    bucket: compliance-evidence-${AWS_ACCOUNT_ID}
    encryption: AES-256
    versioning: enabled
    lifecycle:
      transition_to_ia: 90 days
      transition_to_glacier: 180 days
      expiration: 2555 days  # 7 years

  integrity:
    method: sha256_checksum
    blockchain_anchor: true
    anchor_service: aws_qldb

  access_control:
    write: compliance-service
    read:
      - compliance-team
      - auditors
      - security-team
    deny:
      - developers  # cannot delete or modify evidence
```

### 1.5 Casos Reais de Falha de Compliance

#### Google — Multa de 50 Milhoes de Euros (GDPR)

Em janeiro de 2019, a CNIL (Commission Nationale de l'Informatique et des Libertés) francesa aplicou uma multa recorde de 50 milhoes de euros ao Google por violacoes ao GDPR. Os problemas incluíam:

- Falta de transparencia no uso de dados pessoais para personalizacao de anuncios
- Ausencia de consentimento valido para anuncios personalizados
- Informacoes insuficientes sobre retencao de dados
- Dificuldade para usuarios exercerem seus direitos de exclusao

A decisao revelou que o Google tratava o consentimento como um checkbox padrao em vez de um mecanismo granular. O consentimento para anuncios personalizados vinha pre-marcado durante a criacao de conta, violando o principio de consentimento livre e especifico do GDPR.

A lição para DevSecOps e clara: consent management deve ser implementado como codigo, nao como um processo manual. Um pipeline de compliance automatizado teria detectado o opt-out padrao antes do deploy.

#### Amazon — Multa de 746 Milhoes de Euros (GDPR)

Em julho de 2021, o Luxembourg National Commission for Data Protection (CNPD) aplicou uma multa de 746 milhoes de euros a Amazon Europe — a maior multa ja aplicada sob o GDPR ate aquele momento. A investigacao durou mais de tres anos e focou em práticas de coleta e uso de dados pessoais para fins de publicidade direcionada.

O caso expôs problemas estruturais: o sistema de publicidade da Amazon coletava dados sem base legal adequada, e os mecanismos de consentimento nao atendiam aos requisitos de especificidade do GDPR. A decisao sublinhou que mesmo empresas com engenharia de ponta podem falhar em compliance quando o tratamento de dados nao e tratado como requisito de sistema.

#### SolarWinds — Gaps de Compliance em Cascata

O ataque ao SolarWinds em 2020 expôs uma falha sistemica de compliance. A empresa tinha certificacoes SOC 2 e atendia a FedRAMP, mas o comprometimento do pipeline de build passou despercebido por meses. A investigacao posterior revelou:

- Falta de verificacao de integridade no pipeline de build
- Ausencia de signed commits obrigatórios
- Monitoramento inadequado de acessos privilegiados
- Certificacoes auditadas apenas em pontos no tempo, nao continuamente

O SolarWinds ilustra por que compliance periodico (trimestral/anual) e insuficiente. Um pipeline de compliance continuo com verificacao de integridade de artefatos teria detectado a injecao maliciosa significativamente antes.

---

## 2. SOC 2 Type II

### 2.1 Trust Service Criteria

O SOC 2 e baseado em cinco Trust Service Criteria definidos pelo AICPA. Cada um representarea um dominio de controle que a organizacao deve demonstrar:

- **Seguranca (Security)**: Protecao contra acesso nao autorizado. Obrigatório para todos os relatorios SOC 2.
- **Disponibilidade (Availability)**: Operacao do sistema conforme o acordado contractualmente.
- **Integridade de Processamento (Processing Integrity)**: Processamento completo, preciso, oportuno e autorizado.
- **Confidencialidade (Confidentiality)**: Protecao de informacoes designadas como confidenciais.
- **Privacidade (Privacy)**: Coleta, uso, retencao, divulgacao e descarte de dados pessoais de acordo com asPoliticas de Privacidade.

### 2.2 Technical Controls

Cada Trust Service Criteria mapeia para controles tecnicos especificos. A automacao desses controles e o que permite evidenciar compliance continuo durante o periodo de auditoria (tipicamente 6-12 meses).

```yaml
# soc2-controls.yaml
soc2_controls:
  CC6.1:
    name: "Logical Access Controls"
    criteria: "Seguranca"
    description: "Controles logicos de acesso ao sistema"
    controls:
      - id: "CC6.1.1"
        name: "MFA obrigatorio"
        check: "python scripts/check_mfa.py"
        evidence: "Okta SSO logs com MFA enforced"
      - id: "CC6.1.2"
        name: "Least privilege IAM"
        check: "python scripts/check_iam_privilege.py"
        evidence: "IAM policy analysis report"
      - id: "CC6.1.3"
        name: "Access review trimestral"
        check: "python scripts/check_access_review.py"
        evidence: "Access review completion records"

  CC6.6:
    name: "Logical Access Security"
    criteria: "Seguranca"
    description: "Seguranca contra ameacas e vulnerabilidades"
    controls:
      - id: "CC6.6.1"
        name: "Vulnerability scanning"
        check: "python scripts/check_vuln_scan.py"
        evidence: "Nessus/Qualys scan reports"
      - id: "CC6.6.2"
        name: "Penetration testing"
        check: "python scripts/check_pentest.py"
        evidence: "Annual pentest report"
      - id: "CC6.6.3"
        name: "Patch management"
        check: "python scripts/check_patch_status.py"
        evidence: "Patch compliance dashboard"

  CC7.1:
    name: "Monitoring"
    criteria: "Seguranca"
    description: "Monitoramento continuo da infraestrutura"
    controls:
      - id: "CC7.1.1"
        name: "SIEM configurado"
        check: "python scripts/check_siem.py"
        evidence: "SIEM dashboard screenshots"
      - id: "CC7.1.2"
        name: "Alertas configurados"
        check: "python scripts/check_alerts.py"
        evidence: "Alert configuration exports"
      - id: "CC7.1.3"
        name: "Log retention"
        check: "python scripts/check_log_retention.py"
        evidence: "Log storage configuration"

  CC8.1:
    name: "Change Management"
    criteria: "Seguranca"
    description: "Controles de gestao de mudancas"
    controls:
      - id: "CC8.1.1"
        name: "Code review obrigatorio"
        check: "python scripts/check_code_review.py"
        evidence: "GitHub/GitLab PR merge logs"
      - id: "CC8.1.2"
        name: "Approval antes de deploy"
        check: "python scripts/check_deploy_approval.py"
        evidence: "Deployment approval records"
      - id: "CC8.1.3"
        name: "Rollback capability"
        check: "python scripts/check_rollback.py"
        evidence: "Deployment history with rollbacks"
```

### 2.3 Evidence Automation

Para SOC 2 Type II, voce precisa demonstrar que os controles estao funcionando continuamente durante o periodo de auditoria. A evidencia automatizada coleta provas de forma sistematica e consistente.

```python
# soc2_evidence_collector.py
import json
import hashlib
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EvidenceItem:
    control_id: str
    evidence_type: str
    collection_date: datetime
    content: Dict[str, Any]
    source_system: str
    collector: str
    integrity_hash: str = ""

    def __post_init__(self):
        content_str = json.dumps(self.content, sort_keys=True)
        self.integrity_hash = hashlib.sha256(content_str.encode()).hexdigest()


@dataclass
class EvidenceCollector:
    organization: str
    audit_period_start: datetime
    audit_period_end: datetime
    evidence_items: List[EvidenceItem] = field(default_factory=list)

    def collect_mfa_evidence(self) -> EvidenceItem:
        result = subprocess.run(
            ["aws", "iam", "get-credential-report", "--output", "json"],
            capture_output=True, text=True, timeout=60
        )

        content = {
            "mfa_enabled_users": self._parse_mfa_report(result.stdout),
            "total_users": self._count_users(result.stdout),
            "collection_timestamp": datetime.now().isoformat()
        }

        evidence = EvidenceItem(
            control_id="CC6.1.1",
            evidence_type="mfa_status",
            collection_date=datetime.now(),
            content=content,
            source_system="AWS IAM",
            collector="soc2_evidence_collector"
        )
        self.evidence_items.append(evidence)
        return evidence

    def collect_access_logs(self, days_back: int = 90) -> EvidenceItem:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        result = subprocess.run(
            [
                "aws", "logs", "filter-log-events",
                "--log-group-name", "/aws/cloudtrail",
                "--start-time", str(int(start_date.timestamp() * 1000)),
                "--end-time", str(int(end_date.timestamp() * 1000)),
                "--filter-pattern", "{ ($.eventName = ConsoleLogin) }",
                "--output", "json"
            ],
            capture_output=True, text=True, timeout=120
        )

        content = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "login_events": self._parse_cloudtrail(result.stdout),
            "unique_users": self._count_unique_users(result.stdout),
            "failed_attempts": self._count_failed_logins(result.stdout)
        }

        evidence = EvidenceItem(
            control_id="CC7.1.1",
            evidence_type="access_logs",
            collection_date=datetime.now(),
            content=content,
            source_system="AWS CloudTrail",
            collector="soc2_evidence_collector"
        )
        self.evidence_items.append(evidence)
        return evidence

    def collect_change_management(self, days_back: int = 90) -> EvidenceItem:
        result = subprocess.run(
            [
                "gh", "api", "repos/{owner}/{repo}/pulls",
                "--jq", "[.[] | {merged_at: .merged_at, user: .user.login, title: .title, reviews: .requested_reviewers}]"
            ],
            capture_output=True, text=True, timeout=60
        )

        content = {
            "period_days": days_back,
            "pull_requests": json.loads(result.stdout) if result.stdout else [],
            "collection_timestamp": datetime.now().isoformat()
        }

        evidence = EvidenceItem(
            control_id="CC8.1.1",
            evidence_type="change_management",
            collection_date=datetime.now(),
            content=content,
            source_system="GitHub",
            collector="soc2_evidence_collector"
        )
        self.evidence_items.append(evidence)
        return evidence

    def generate_report(self) -> Dict[str, Any]:
        return {
            "organization": self.organization,
            "audit_period": {
                "start": self.audit_period_start.isoformat(),
                "end": self.audit_period_end.isoformat()
            },
            "total_evidence_items": len(self.evidence_items),
            "controls_covered": list(set(e.control_id for e in self.evidence_items)),
            "evidence_integrity": all(e.integrity_hash for e in self.evidence_items),
            "collection_summary": [
                {
                    "control_id": e.control_id,
                    "type": e.evidence_type,
                    "collected_at": e.collection_date.isoformat(),
                    "hash": e.integrity_hash
                }
                for e in self.evidence_items
            ]
        }

    def _parse_mfa_report(self, raw: str) -> List[Dict]:
        return []

    def _count_users(self, raw: str) -> int:
        return 0

    def _parse_cloudtrail(self, raw: str) -> List[Dict]:
        return []

    def _count_unique_users(self, raw: str) -> int:
        return 0

    def _count_failed_logins(self, raw: str) -> int:
        return 0


if __name__ == "__main__":
    collector = EvidenceCollector(
        organization="Acme Corp",
        audit_period_start=datetime.now() - timedelta(days=365),
        audit_period_end=datetime.now()
    )

    print("[SOC2] Collecting MFA evidence...")
    collector.collect_mfa_evidence()

    print("[SOC2] Collecting access logs...")
    collector.collect_access_logs(days_back=90)

    print("[SOC2] Collecting change management evidence...")
    collector.collect_change_management(days_back=90)

    report = collector.generate_report()
    print(json.dumps(report, indent=2))
```

### 2.4 Complete SOC 2 Automation Pipeline

{% raw %}
```yaml
# .github/workflows/soc2-compliance.yml
name: SOC 2 Type II Compliance Pipeline

on:
  schedule:
    - cron: "0 6 * * *"  # Diario as 6h UTC
  push:
    branches: [main]
    paths:
      - "infrastructure/**"
      - "src/**"
  workflow_dispatch:
    inputs:
      audit_type:
        description: "Tipo de auditoria"
        required: true
        default: "continuous"
        type: choice
        options:
          - continuous
          - quarterly
          - annual

env:
  EVIDENCE_BUCKET: s3://compliance-evidence-${{ secrets.AWS_ACCOUNT_ID }}
  SOC2_REPORT_DIR: /tmp/soc2-reports

jobs:
  collect-evidence:
    name: "Coletar Evidencias SOC 2"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Instalar dependencias
        run: |
          pip install boto3 requests pyyaml

      - name: Coletar evidencias MFA
        run: python scripts/soc2/evidence_collector.py --control CC6.1.1

      - name: Coletar evidencias Access Controls
        run: python scripts/soc2/evidence_collector.py --control CC6.1

      - name: Coletar evidencias Change Management
        run: python scripts/soc2/evidence_collector.py --control CC8.1

      - name: Coletar evidencias Monitoring
        run: python scripts/soc2/evidence_collector.py --control CC7.1

      - name: Coletar evidencias Incident Response
        run: python scripts/soc2/evidence_collector.py --control CC7.3

      - name: Upload evidencias
        run: |
          aws s3 sync $SOC2_REPORT_DIR $EVIDENCE_BUCKET/soc2/ \
            --metadata '{"integrity":"sha256","collector":"github-actions"}'

  verify-controls:
    name: "Verificar Controles SOC 2"
    runs-on: ubuntu-latest
    needs: collect-evidence
    steps:
      - uses: actions/checkout@v4

      - name: Verificar controles automaticos
        run: |
          echo "=== Verificando CC6.1 - Logical Access ==="
          python scripts/soc2/verify_control.py --control CC6.1.1 --expect pass
          python scripts/soc2/verify_control.py --control CC6.1.2 --expect pass

          echo "=== Verificando CC7.1 - Monitoring ==="
          python scripts/soc2/verify_control.py --control CC7.1.1 --expect pass
          python scripts/soc2/verify_control.py --control CC7.1.2 --expect pass

          echo "=== Verificando CC8.1 - Change Management ==="
          python scripts/soc2/verify_control.py --control CC8.1.1 --expect pass
          python scripts/soc2/verify_control.py --control CC8.1.2 --expect pass

      - name: Gerar relatorio de compliance
        run: |
          python scripts/soc2/generate_report.py \
            --output $SOC2_REPORT_DIR/soc2-report-$(date +%Y%m%d).json

      - name: Upload relatorio
        run: |
          aws s3 cp $SOC2_REPORT_DIR/soc2-report-*.json \
            $EVIDENCE_BUCKET/reports/soc2/

  alert-on-failure:
    name: "Alertar em Caso de Falha"
    runs-on: ubuntu-latest
    needs: verify-controls
    if: failure()
    steps:
      - name: Notificar Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "ALERTA SOC 2: Controle falhou na verificacao diaria. Verificar relatorios em $EVIDENCE_BUCKET"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```
{% endraw %}

---

## 3. PCI DSS

### 3.1 Requirements Relevant to DevOps

O PCI DSS (Payment Card Industry Data Security Standard) e obrigatório para qualquer organizacao que processe, armazene ou transmita dados de cartao de credito. As 12 divisoes do PCI DSS impactam diretamente o ciclo de vida do desenvolvimento de software.

```yaml
# pci-dss-devops-mapping.yaml
pci_dss_devops_mapping:
  requirement_1:
    name: "Instalar e manter configuracao de controle de acesso"
    devops_controls:
      - "Firewall rules as Code (Terraform/Security Groups)"
      - "Network segmentation automation"
      - "Automated firewall rule review"
    implementation: "iptables rules generated from YAML config"

  requirement_2:
    name: "Nao usar senhas padrao do fornecedor"
    devops_controls:
      - "Container image scanning for default credentials"
      - "Infrastructure templates without hardcoded passwords"
      - "Secrets management (Vault/AWS Secrets Manager)"
    implementation: "Pre-commit hooks + CI pipeline checks"

  requirement_3:
    name: "Proteger dados do titular armazenados"
    devops_controls:
      - "Database encryption at rest (AES-256)"
      - "Tokenization of card data"
      - "Data masking in non-production environments"
    implementation: "Terraform KMS modules + application-level encryption"

  requirement_4:
    name: "Criptografar transmissao de dados em redes publicas"
    devops_controls:
      - "TLS 1.2+ enforcement"
      - "Certificate rotation automation"
      - "HSTS headers"
    implementation: "Cert-manager + NetworkPolicy"

  requirement_6:
    name: "Desenvolver e manter sistemas seguros"
    devops_controls:
      - "Secure SDLC pipeline"
      - "SAST/DAST in CI"
      - "Code review requirements"
      - "Dependency vulnerability scanning"
    implementation: "GitHub Actions with security gates"

  requirement_7:
    name: "Restringir acesso por necessidade de saber"
    devops_controls:
      - "RBAC enforcement"
      - "Just-in-time access provisioning"
      - "Access review automation"
    implementation: "Okta + Terraform IAM modules"

  requirement_8:
    name: "Identificar e autenticar acesso"
    devops_controls:
      - "MFA enforcement for all access"
      - "Service account rotation"
      - "SSH key management"
    implementation: "Vault SSH CA + Okta MFA"

  requirement_10:
    name: "Rastrear e monitorar todos os acessos"
    devops_controls:
      - "Centralized logging"
      - "Audit trail for all changes"
      - "Automated log review"
    implementation: "ELK Stack + Fluentd"

  requirement_11:
    name: "Testar regularmente seguranca dos sistemas"
    devops_controls:
      - "Automated vulnerability scanning"
      - "Penetration testing automation"
      - "Wireless access point detection"
    implementation: "Nessus + OWASP ZAP in CI"

  requirement_12:
    name: "Manter politica de seguranca"
    devops_controls:
      - "Security policy as Code"
      - "Incident response automation"
      - "Security awareness training tracking"
    implementation: "Policy engine + automated playbooks"
```

### 3.2 Automated Controls

```yaml
# pci-automated-controls.yaml
pci_controls:
  encryption_at_rest:
    requirement: "3.4"
    check: |
      for bucket in $(aws s3 ls --query 'Buckets[].Name' --output text); do
        encryption=$(aws s3api get-bucket-encryption --bucket $bucket 2>/dev/null)
        if [ $? -ne 0 ]; then
          echo "FAIL: Bucket $bucket has no encryption configured"
          exit 1
        fi
      done
      echo "PASS: All S3 buckets have encryption"
    auto_remediate: |
      for bucket in $(aws s3 ls --query 'Buckets[].Name' --output text); do
        aws s3api put-bucket-encryption --bucket $bucket \
          --server-side-encryption-configuration '{
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}}]
          }'
      done

  tls_enforcement:
    requirement: "4.1"
    check: |
      for endpoint in $(cat endpoints.txt); do
        protocol=$(echo | openssl s_client -connect $endpoint 2>/dev/null | grep Protocol)
        if echo "$protocol" | grep -q "TLSv1.2\|TLSv1.3"; then
          echo "PASS: $endpoint uses $protocol"
        else
          echo "FAIL: $endpoint uses weak protocol: $protocol"
          exit 1
        fi
      done

  access_review:
    requirement: "7.1.1"
    check: |
      python scripts/pci/check_iam_review.py \
        --max-days-without-review 90 \
        --require-justification

  log_retention:
    requirement: "10.7"
    check: |
      RETENTION_DAYS=$(python scripts/pci/get_log_retention.py)
      if [ "$RETENTION_DAYS" -lt 365 ]; then
        echo "FAIL: Log retention is $RETENTION_DAYS days, minimum is 365"
        exit 1
      fi
      echo "PASS: Log retention meets PCI DSS requirement"
```

### 3.3 Evidence Collection

```yaml
# pci-evidence.yaml
pci_evidence:
  controls:
    - id: "3.4"
      name: "Dados de cartao criptografados"
      evidence_sources:
        - type: automated
          command: "python scripts/pci/evidence_encryption.py"
          frequency: daily
        - type: config_export
          command: "aws s3api get-bucket-encryption --bucket card-data-bucket"
          frequency: daily
      retention: "3 years"

    - id: "6.5.1"
      name: "Vulnerabilidades de codigo identificadas e corrigidas"
      evidence_sources:
        - type: sast_report
          tool: "semgrep"
          command: "semgrep --config=pci-dss --json --output=pci-sast-report.json"
          frequency: every_merge
        - type: dependency_scan
          tool: "safety"
          command: "safety check --json --output=pci-dep-report.json"
          frequency: daily
      retention: "3 years"

    - id: "8.3"
      name: "MFA implementado"
      evidence_sources:
        - type: identity_provider
          command: "python scripts/pci/evidence_mfa.py --provider okta"
          frequency: daily
        - type: aws_iam
          command: "aws iam generate-credential-report && aws iam get-credential-report"
          frequency: daily
      retention: "3 years"

    - id: "10.2"
      name: "Logs de auditoria completos"
      evidence_sources:
        - type: log_config
          command: "python scripts/pci/evidence_log_config.py"
          frequency: daily
        - type: log_integrity
          command: "python scripts/pci/verify_log_integrity.py"
          frequency: daily
      retention: "3 years"

  storage:
    bucket: "pci-evidence-${AWS_ACCOUNT_ID}"
    encryption: "aws:kms"
    access_logging: true
    versioning: true
    object_lock: true  # WORM compliance
    retention_period: 1095 days  # 3 years
```

### 3.4 Complete PCI DSS Compliance Pipeline

```yaml
# .github/workflows/pci-compliance.yml
name: PCI DSS Compliance Pipeline

on:
  schedule:
    - cron: "0 5 * * *"
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PCI_EVIDENCE_BUCKET: s3://pci-evidence-${{ secrets.AWS_ACCOUNT_ID }}

jobs:
  pci-sast:
    name: "PCI SAST - Requisito 6"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Semgrep SAST
        uses: semgrep/semgrep-action@v1
        with:
          config: p/pci-dss
          generateSarif: true
      - name: Upload resultados
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: semgrep.sarif

  pci-dependencies:
    name: "PCI Dependency Check - Requisito 6"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Safety check
        run: |
          pip install safety
          safety check --json > pci-dependency-report.json
          if safety check 2>&1 | grep -q "vulnerabilities found"; then
            echo "::error::Vulnerabilidades de dependencia encontradas (PCI 6.5)"
            exit 1
          fi

  pci-infrastructure:
    name: "PCI Infrastructure Scan - Requisito 2"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Verificar configuracoes PCI
        run: |
          python scripts/pci/verify_all_controls.py \
            --requirements "2,3,4,7,8,10" \
            --output pci-infra-report.json \
            --fail-on critical,high
      - name: Upload resultado
        run: |
          aws s3 cp pci-infra-report.json \
            $PCI_EVIDENCE_BUCKET/reports/$(date +%Y%m%d)-infra.json

  pci-network:
    name: "PCI Network Security - Requisito 1"
    runs-on: ubuntu-latest
    steps:
      - name: Verificar segmentacao de rede
        run: |
          python scripts/pci/verify_network_segmentation.py \
            --expected-segments cardholder,data,public \
            --deny-cross-segment-traffic
      - name: Verificar firewall rules
        run: |
          python scripts/pci/verify_firewall_rules.py \
            --deny-default-inbound \
            --require-explicit-rules

  pci-report:
    name: "Gerar Relatorio PCI"
    runs-on: ubuntu-latest
    needs: [pci-sast, pci-dependencies, pci-infrastructure, pci-network]
    if: always()
    steps:
      - name: Consolidar resultados
        run: |
          python scripts/pci/generate_pci_report.py \
            --results-dir . \
            --output pci-compliance-report.json \
            --format aco
      - name: Upload relatorio
        run: |
          aws s3 cp pci-compliance-report.json \
            $PCI_EVIDENCE_BUCKET/reports/$(date +%Y%m%d)-pci-report.json
```

---

## 4. GDPR/LGPD

### 4.1 Data Protection by Design

O GDPR (Regulamento Geral de Protecao de Dados) e a LGPD (Lei Geral de Protecao de Dados) exigem que a protecao de dados seja incorporada desde o design dos sistemas. Isso nao e opcional — e uma obrigacao legal com multas que podem chegar a 4% do faturamento global.

```yaml
# privacy-by-design.yaml
privacy_engineering:
  data_classification:
    levels:
      - public: "Dados publicos, sem restricao"
      - internal: "Dados internos da organizacao"
      - confidential: "Dados confidenciais, acesso restrito"
      - restricted: "Dados pessoais sensiveis, acesso critico"

    detection_rules:
      - name: "CPF Detection"
        pattern: "\\d{3}\\.\\d{3}\\.\\d{3}-\\d{2}"
        classification: restricted
        frameworks: [LGPD, GDPR]
      - name: "CNPJ Detection"
        pattern: "\\d{2}\\.\\d{3}\\.\\d{3}/\\d{4}-\\d{2}"
        classification: confidential
        frameworks: [LGPD]
      - name: "Email Detection"
        pattern: "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"
        classification: internal
        frameworks: [LGPD, GDPR]
      - name: "Credit Card Detection"
        pattern: "\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}[\\s-]?\\d{4}"
        classification: restricted
        frameworks: [PCI_DSS, LGPD]

  data_minimization:
    principles:
      - "Coletar apenas dados necessarios para o proposito"
      - "Nao manter dados alem do necessario"
      - "Anonimizar dados quando possivel"
      - "Pseudonimizar dados sensiveis"
    automated_checks:
      - check: "Verificar se todos os campos de formulario tem justificativa de coleta"
        script: "python scripts/gdpr/check_data_collection_justification.py"
      - check: "Verificar se dados de teste estao anonimizados"
        script: "python scripts/gdpr/check_test_data_anonymization.py"
      - check: "Verificar politicas de retencao de dados"
        script: "python scripts/gdpr/check_data_retention_policies.py"

  right_to_erasure:
    implementation:
      - name: "Data Erasure API"
        endpoint: "POST /api/v1/data-subject/erasure"
        scope: "Todos os sistemas que processam dados pessoais"
        sla_hours: 72
        verification: "Confirmar exclusao em todos os sistemas"
      - name: "Backup Purge"
        process: "Excluir dados pessoais em backups dentro do ciclo de retencao"
        automation: "Script de busca e exclusao em backups criptografados"
```

### 4.2 Privacy Impact Assessment Automation

```yaml
# pia-automation.yaml
privacy_impact_assessment:
  trigger: "on_new_feature_or_data_flow"
  automated_checks:
    - name: "Data Flow Mapping"
      script: "python scripts/gdpr/map_data_flows.py"
      output: "data_flow_inventory.yaml"
      checks:
        - "Identificar todos os pontos de coleta de dados"
        - "Mapear fluxo de dados entre servicos"
        - "Identificar terceiros que recebem dados"
        - "Verificar base legal para cada processamento"

    - name: "Risk Assessment"
      script: "python scripts/gdpr/assess_privacy_risk.py"
      output: "privacy_risk_assessment.yaml"
      risk_factors:
        - "Volume de dados pessoais processados"
        - "Sensibilidade dos dados"
        - "Numero de titulares afetados"
        - "Tecnologias envolvidas"
        - "Medidas de seguranca existentes"

    - name: "Legal Basis Verification"
      script: "python scripts/gdpr/verify_legal_basis.py"
      output: "legal_basis_inventory.yaml"
      valid_bases:
        - consent
        - contract
        - legal_obligation
        - vital_interests
        - public_task
        - legitimate_interests

    - name: "DPIA Score Calculator"
      script: "python/scripts/gdpr/calculate_dpia_score.py"
      output: "dpia_score.yaml"
      thresholds:
        high_risk: "Score >= 15 or processing involves sensitive data"
        requires_dpia: "Score >= 10 or large-scale processing"
        notification_required: "Score >= 20 or cross-border transfer"

  approval_workflow:
    low_risk: "Security team review"
    medium_risk: "DPO + Security team review"
    high_risk: "DPO + Legal + Security + CTO approval"
    critical: "DPO + Legal + Security + CTO + Board notification"
```

### 4.3 Data Mapping

```python
# data_mapping.py
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DataField:
    name: str
    type: str
    classification: str
    legal_basis: str
    retention_days: int
    encrypted: bool = False
    pseudonymized: bool = False
    purpose: str = ""
    third_parties: List[str] = field(default_factory=list)


@dataclass
class DataAsset:
    asset_id: str
    name: str
    location: str
    data_fields: List[DataField] = field(default_factory=list)
    owner: str = ""
    last_audit: Optional[datetime] = None
    encryption_status: str = "unknown"

    @property
    def personal_data_fields(self) -> List[DataField]:
        return [
            f for f in self.data_fields
            if f.classification in ("restricted", "confidential")
        ]

    @property
    def requires_dpia(self) -> bool:
        return any(
            f.classification == "restricted" for f in self.data_fields
        )


@dataclass
class DataMappingInventory:
    organization: str
    assets: List[DataAsset] = field(default_factory=list)
    last_scan: Optional[datetime] = None

    def scan_all_assets(self):
        print("[DATA-MAP] Scanning all data assets...")
        self.last_scan = datetime.now()

    def generate_report(self) -> Dict[str, Any]:
        total_fields = sum(len(a.data_fields) for a in self.assets)
        personal_fields = sum(
            len(a.personal_data_fields) for a in self.assets
        )
        encrypted_fields = sum(
            sum(1 for f in a.data_fields if f.encrypted)
            for a in self.assets
        )

        return {
            "organization": self.organization,
            "scan_date": self.last_scan.isoformat() if self.last_scan else None,
            "summary": {
                "total_assets": len(self.assets),
                "total_fields": total_fields,
                "personal_data_fields": personal_fields,
                "encrypted_fields": encrypted_fields,
                "encryption_coverage": (
                    f"{(encrypted_fields / total_fields * 100):.1f}%"
                    if total_fields > 0 else "N/A"
                ),
                "assets_requiring_dpia": sum(
                    1 for a in self.assets if a.requires_dpia
                ),
            },
            "assets": [
                {
                    "id": a.asset_id,
                    "name": a.name,
                    "location": a.location,
                    "field_count": len(a.data_fields),
                    "personal_data_count": len(a.personal_data_fields),
                    "encryption_status": a.encryption_status,
                    "owner": a.owner,
                }
                for a in self.assets
            ],
            "compliance_gaps": self._identify_gaps()
        }

    def _identify_gaps(self) -> List[Dict[str, str]]:
        gaps = []
        for asset in self.assets:
            for field in asset.data_fields:
                if field.classification == "restricted" and not field.encrypted:
                    gaps.append({
                        "asset": asset.name,
                        "field": field.name,
                        "issue": "Dados sensiveis nao criptografados",
                        "severity": "critical",
                        "regulation": "LGPD Art. 46"
                    })
                if field.classification == "restricted" and not field.legal_basis:
                    gaps.append({
                        "asset": asset.name,
                        "field": field.name,
                        "issue": "Base legal nao definida",
                        "severity": "critical",
                        "regulation": "LGPD Art. 7"
                    })
                if (field.classification == "restricted"
                        and field.retention_days > 365 * 5):
                    gaps.append({
                        "asset": asset.name,
                        "field": field.name,
                        "issue": "Periodo de retencao excessivo",
                        "severity": "high",
                        "regulation": "LGPD Art. 15"
                    })
        return gaps
```

### 4.4 Consent Management in Code

```python
# consent_manager.py
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class ConsentPurpose(Enum):
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY_SHARING = "third_party_sharing"
    PROFILING = "profiling"
    NECESSARY = "necessary"  # always consent, cannot be withdrawn


@dataclass
class ConsentRecord:
    data_subject_id: str
    purpose: ConsentPurpose
    granted: bool
    timestamp: datetime
    method: str  # "web_form", "api", "mobile_app"
    ip_address: str = ""
    version: str = "1.0"
    expires_at: Optional[datetime] = None


@dataclass
class ConsentManager:
    records: List[ConsentRecord] = field(default_factory=list)

    def record_consent(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose,
        granted: bool,
        method: str,
        ip_address: str = "",
        validity_days: int = 365
    ) -> ConsentRecord:
        record = ConsentRecord(
            data_subject_id=data_subject_id,
            purpose=purpose,
            granted=granted,
            timestamp=datetime.now(),
            method=method,
            ip_address=ip_address,
            expires_at=datetime.now() + timedelta(days=validity_days)
        )
        self.records.append(record)
        return record

    def has_valid_consent(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose
    ) -> bool:
        relevant = [
            r for r in self.records
            if r.data_subject_id == data_subject_id and r.purpose == purpose
        ]
        if not relevant:
            return False

        latest = max(relevant, key=lambda r: r.timestamp)
        if not latest.granted:
            return False

        if latest.expires_at and datetime.now() > latest.expires_at:
            return False

        return True

    def withdraw_consent(
        self,
        data_subject_id: str,
        purpose: ConsentPurpose,
        method: str,
        ip_address: str = ""
    ) -> ConsentRecord:
        return self.record_consent(
            data_subject_id=data_subject_id,
            purpose=purpose,
            granted=False,
            method=method,
            ip_address=ip_address
        )

    def get_all_consents(self, data_subject_id: str) -> Dict[str, bool]:
        result = {}
        for purpose in ConsentPurpose:
            if purpose == ConsentPurpose.NECESSARY:
                result[purpose.value] = True
            else:
                result[purpose.value] = self.has_valid_consent(
                    data_subject_id, purpose
                )
        return result

    def export_for_subject(self, data_subject_id: str) -> List[Dict]:
        return [
            {
                "purpose": r.purpose.value,
                "granted": r.granted,
                "timestamp": r.timestamp.isoformat(),
                "method": r.method,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None
            }
            for r in self.records
            if r.data_subject_id == data_subject_id
        ]

    def audit_log(self) -> List[Dict]:
        return [
            {
                "data_subject": r.data_subject_id,
                "purpose": r.purpose.value,
                "action": "granted" if r.granted else "withdrawn",
                "timestamp": r.timestamp.isoformat(),
                "method": r.method,
                "valid": self.has_valid_consent(
                    r.data_subject_id, r.purpose
                )
            }
            for r in self.records
        ]
```

### 4.5 Complete LGPD Compliance Checklist

```yaml
# lgpd-compliance-checklist.yaml
lgpd_checklist:
  governance:
    - name: "DPO nomeado"
      requirement: "LGPD Art. 41"
      status: "automated_check"
      check: "python scripts/lgpd/check_dpo_appointed.py"
      evidence: "DPO appointment letter + registration"

    - name: "Relatorio de Impacto a Protecao de Dados (RIPD)"
      requirement: "LGPD Art. 38"
      status: "automated_check"
      check: "python scripts/lgpd/check_dpia_completed.py"
      frequency: "before_new_processing"
      evidence: "RIPD document with DPO sign-off"

  data_processing:
    - name: "Bases legais documentadas"
      requirement: "LGPD Art. 7"
      check: "python scripts/lgpd/check_legal_bases.py"
      evidence: "Legal basis mapping per processing activity"

    - name: "Consentimento granular"
      requirement: "LGPD Art. 8"
      check: "python scripts/lgpd/check_consent_mechanism.py"
      evidence: "Consent records with purpose specification"

    - name: "Dados minimizados"
      requirement: "LGPD Art. 6, III"
      check: "python scripts/lgpd/check_data_minimization.py"
      evidence: "Data collection form review + field justification"

  data_subject_rights:
    - name: "API de direitos do titular"
      requirement: "LGPD Art. 18"
      endpoints:
        - "GET /api/v1/data-subject/consent"
        - "POST /api/v1/data-subject/consent"
        - "GET /api/v1/data-subject/data-export"
        - "POST /api/v1/data-subject/erasure"
        - "POST /api/v1/data-subject/correction"
      sla: "15 dias uteis"
      check: "python scripts/lgpd/check_rights_api.py"

  security:
    - name: "Criptografia de dados pessoais"
      requirement: "LGPD Art. 46"
      check: "python scripts/lgpd/check_encryption.py"
      severity: critical

    - name: "Controle de acesso"
      requirement: "LGPD Art. 46"
      check: "python scripts/lgpd/check_access_control.py"
      severity: critical

    - name: "Registro de operacoes de tratamento"
      requirement: "LGPD Art. 37"
      check: "python scripts/lgpd/check_processing_records.py"

    - name: "Plano de resposta a incidentes"
      requirement: "LGPD Art. 48"
      check: "python scripts/lgpd/check_incident_plan.py"
      sla_notification: "72 horas para ANPD"

  international_transfer:
    - name: "Adequacao do pais receptor"
      requirement: "LGPD Art. 33"
      check: "python scripts/lgpd/check_transfer_adequacy.py"
      valid_countries_file: "lgpd_adequacy_list.yaml"

  retention:
    - name: "Politica de retencao de dados"
      requirement: "LGPD Art. 15, 16"
      check: "python scripts/lgpd/check_retention_policy.py"
      max_retention: "defined_per_purpose"
```

### 4.6 Caso Real: LGPD no Brasil

Em 2023, a ANPD (Autoridade Nacional de Protecao de Dados) iniciou operacoes de fiscalizacao ativa contra empresas brasileiras. O primeiro caso publico envolveu uma empresa de telecomunicacoes que:

- Manteve dados de clientes por tempo indefinido apos cancelamento do contrato
- Nao oferecia mecanismo eficaz para exercicio de direitos dos titulares
- Compartilhava dados com parceiros sem base legal adequada
- Falhou em notificar a ANPD dentro de 72 horas sobre um incidente de seguranca

A LGPD prevê multas de ate 2% do faturamento (limitadas a R$ 50 milhoes por infração). Alem das multas, a reputacao do mercado sofre impacto significativo. Empresas que implementam compliance automatizado para LGPD estao melhor posicionadas para demonstrar "due diligence" e mitigar penalidades.

---

## 5. CIS Benchmarks

### 5.1 Automated Benchmark Testing

Os CIS (Center for Internet Security) Benchmarks sao guias de configuracao segura para diversos sistemas operacionais, servicos e aplicacoes. A automacao de verificacao contra esses benchmarks e fundamental para manter a seguranca da infraestrutura.

```yaml
# cis-benchmark.yaml
cis_benchmarks:
  docker:
    benchmark_version: "1.6.0"
    profile: "level_1"
    checks:
      - id: "2.1"
        name: "Restrict network traffic between containers"
        command: "python scripts/cis/docker/check_network_policy.py"
        severity: high

      - id: "4.1"
        name: "Ensure images are scanned for vulnerabilities"
        command: "python scripts/cis/docker/check_image_scan.py"
        severity: critical

      - id: "4.6"
        name: "Ensure that privileged containers are not used"
        command: "python scripts/cis/docker/check_privileged.py"
        severity: critical

  kubernetes:
    benchmark_version: "1.8.0"
    profile: "level_1"
    checks:
      - id: "4.1.1"
        name: "Ensure that the API server endpoint is set"
        command: "python scripts/cis/k8s/check_api_server.py"
        severity: critical

      - id: "4.2.1"
        name: "Ensure that anonymous auth is disabled"
        command: "python scripts/cis/k8s/check_anonymous_auth.py"
        severity: critical

      - id: "4.2.3"
        name: "Ensure that certificate rotation is set"
        command: "python scripts/cis/k8s/check_cert_rotation.py"
        severity: high

  linux:
    benchmark_version: "3.0.0"
    profile: "level_1"
    checks:
      - id: "1.1.1.1"
        name: "Disable cramfs filesystem"
        command: "python scripts/cis/linux/check_filesystem.py cramfs"
        severity: medium

      - id: "3.1.1"
        name: "Disable IP forwarding"
        command: "python scripts/cis/linux/check_ip_forwarding.py"
        severity: high

      - id: "5.4.1.1"
        name: "Ensure password expiration is 90 days or less"
        command: "python scripts/cis/linux/check_password_expiration.py 90"
        severity: high
```

### 5.2 Docker CIS Benchmark

```yaml
# docker-cis.yaml
docker_cis:
  host_configuration:
    - rule: "1.1.1"
      name: "Create a separate partition for containers"
      check: |
        df -h /var/lib/docker | tail -1 | awk '{print $1}'
      remediation: |
        echo "Create separate partition for /var/lib/docker"

    - rule: "1.2.1"
      name: "Set the logging level"
      check: |
        cat /etc/docker/daemon.json | python3 -c "
        import json, sys
        config = json.load(sys.stdin)
        level = config.get('log-level', 'info')
        print(f'Current log level: {level}')
        if level in ('debug', 'info'):
            exit(1)
        exit(0)
        "

  docker_daemon:
    - rule: "2.1"
      name: "Restrict network traffic between containers"
      check: |
        docker network ls --format '{{.Name}}' | while read net; do
          docker network inspect $net --format '{{.Internal}}'
        done

    - rule: "2.4"
      name: "Do not use insecure registries"
      check: |
        docker info 2>/dev/null | grep -i "insecure registries"

  container_runtime:
    - rule: "5.1"
      name: "Do not disable AppArmor profile"
      check: |
        for container in $(docker ps -q); do
          security=$(docker inspect $container --format '{{.HostConfig.SecurityOpt}}')
          if echo "$security" | grep -q "apparmor=unconfined"; then
            echo "FAIL: Container $container has AppArmor disabled"
            exit 1
          fi
        done
        echo "PASS: All containers have AppArmor enabled"

    - rule: "5.3"
      name: "Restrict Linux kernel capabilities"
      check: |
        for container in $(docker ps -q); do
          caps=$(docker inspect $container --format '{{.HostConfig.CapAdd}}')
          if [ "$caps" != "[]" ] && [ "$caps" != "null" ]; then
            echo "WARNING: Container $container has additional capabilities: $caps"
          fi
        done

  image建设和:
    - rule: "4.1"
      name: "Ensure images are scanned for vulnerabilities before deployment"
      check: |
        for image in $(docker images --format '{{.Repository}}:{{.Tag}}'); do
          trivy image --severity HIGH,CRITICAL --exit-code 1 "$image"
        done

    - rule: "4.6"
      name: "Add HEALTHCHECK instruction to the container image"
      check: |
        for dockerfile in $(find . -name "Dockerfile"); do
          if ! grep -q "HEALTHCHECK" "$dockerfile"; then
            echo "FAIL: $dockerfile missing HEALTHCHECK"
            exit 1
          fi
        done
        echo "PASS: All Dockerfiles have HEALTHCHECK"
```

### 5.3 Kubernetes CIS Benchmark

```yaml
# kubernetes-cis.yaml
kubernetes_cis:
  master_components:
    api_server:
      - rule: "1.1.1"
        name: "Ensure that the API server audit logging is enabled"
        check: |
          kubectl -n kube-system get pod -l component=kube-apiserver -o yaml | \
            grep "audit-log-path"
        expected: "audit-log-path configured"

      - rule: "1.1.3"
        name: "Ensure that the admission control plugin AlwaysPullImages is set"
        check: |
          ps aux | grep kube-apiserver | grep AlwaysPullImages

    controller_manager:
      - rule: "1.2.1"
        name: "Ensure that the terminated pod garbage collector is enabled"
        check: |
          ps aux | grep kube-controller-manager | grep terminated-pod-gc-threshold

    scheduler:
      - rule: "1.3.1"
        name: "Ensure that the scheduler pod specification file permissions"
        check: |
          stat -c %a /etc/kubernetes/manifests/kube-scheduler.yaml
        expected: "644"

  worker_nodes:
    - rule: "4.2.1"
      name: "Ensure that the kubelet only uses strong cryptographic ciphers"
      check: |
        cat /var/lib/kubelet/config.yaml | grep tlsCipherSuites
        expected: "Strong cipher suites configured"

    - rule: "4.2.4"
      name: "Ensure that the kubelet only uses strong TLS ciphers"
      check: |
        curl -k https://localhost:10250/healthz -s -o /dev/null -w "%{http_code}"

  pod_security:
    - rule: "5.1.1"
      name: "Ensure that the cluster-admin role is only used where required"
      check: |
        kubectl get clusterrolebinding -o json | python3 -c "
        import json, sys
        data = json.load(sys.stdin)
        for binding in data['items']:
            if binding['roleRef']['name'] == 'cluster-admin':
                for subject in binding.get('subjects', []):
                    if subject['kind'] != 'User' or subject['name'] == 'system:admin':
                        print(f'WARNING: Cluster-admin bound to {subject[\"kind\"]}:{subject[\"name\"]}')
        "

    - rule: "5.2.1"
      name: "Ensure Pod Security Policies are enabled"
      check: |
        kubectl get psp
```

### 5.4 Linux CIS Benchmark

```yaml
# linux-cis.yaml
linux_cis:
  filesystem_configuration:
    - rule: "1.1.1"
      name: "Disable unused filesystems"
      check: |
        for fs in cramfs freevxfs jffs2 hfs hfsplus squashfs udf; do
          if lsmod | grep -q $fs; then
            echo "FAIL: $fs filesystem is loaded"
            exit 1
          fi
        done
        echo "PASS: No unused filesystems loaded"
      remediation: |
        echo "install $fs /bin/true" >> /etc/modprobe.d/CIS.conf

  network_configuration:
    - rule: "3.1.1"
      name: "Ensure IP forwarding is disabled"
      check: |
        value=$(cat /proc/sys/net/ipv4/ip_forward)
        if [ "$value" -eq 1 ]; then
          echo "FAIL: IP forwarding is enabled"
          exit 1
        fi
        echo "PASS: IP forwarding is disabled"
      remediation: |
        echo "net.ipv4.ip_forward = 0" >> /etc/sysctl.conf
        sysctl -w net.ipv4.ip_forward=0

    - rule: "3.2.1"
      name: "Ensure source routed packets are rejected"
      check: |
        value=$(cat /proc/sys/net/ipv4/conf/all/accept_source_route)
        if [ "$value" -eq 1 ]; then
          echo "FAIL: Source routed packets are accepted"
          exit 1
        fi

  access_control:
    - rule: "5.4.1"
      name: "Ensure password expiration is 90 days or less"
      check: |
        grep PASS_MAX_DAYS /etc/login.defs | awk '{print $2}'
        expected: "90"
      remediation: |
        sed -i 's/PASS_MAX_DAYS.*/PASS_MAX_DAYS 90/' /etc/login.defs

    - rule: "5.4.2"
      name: "Ensure minimum days between password changes is 7 or more"
      check: |
        grep PASS_MIN_DAYS /etc/login.defs | awk '{print $2}'
        expected: "7"

    - rule: "5.5"
      name: "Ensure default user umask is 027 or more restrictive"
      check: |
        grep -E "^umask" /etc/profile /etc/profile.d/*.sh
        expected: "umask 027"
```

---

## 6. OpenSCAP

### 6.1 Security Profiles

OpenSCAP fornece um framework para verificacao automatizada de conformidade com padroes de seguranca. Os perfis definem conjuntos de regras especificos para diferentes requisitos regulatórios.

```yaml
# openscap-profiles.yaml
openscap_profiles:
  compliance_frameworks:
    - name: "PCI-DSS"
      profile: "xccdf_org.ssgproject.content_profile_pci-dss"
      description: "Payment Card Industry Data Security Standard"
      applicable_to:
        - payment_processing
        - card_data_storage

    - name: "STIG"
      profile: "xccdf_org.ssgproject.content_profile_stig"
      description: "Security Technical Implementation Guide"
      applicable_to:
        - government_systems
        - defense_systems

    - name: "CIS"
      profile: "xccdf_org.ssgproject.content_profile_cis"
      description: "Center for Internet Security Benchmark"
      applicable_to:
        - general_purpose
        - enterprise_systems

    - name: "HIPAA"
      profile: "xccdf_org.ssgproject.content_profile_hipaa"
      description: "Health Insurance Portability and Accountability Act"
      applicable_to:
        - healthcare_systems
        - phi_processing

  scan_configuration:
    scan_type: "compliance"
    report_format: "html,xml,json"
    remediation: "auto"
    severity_threshold: "medium"

    scan_targets:
      - type: "os"
        profiles: ["PCI-DSS", "CIS"]
      - type: "docker"
        profiles: ["CIS"]
      - type: "kubernetes"
        profiles: ["CIS"]
```

### 6.2 Compliance Scanning

```bash
#!/bin/bash
# openscap_scan.sh - Automatiza scans OpenSCAP

set -euo pipefail

PROFILE="${1:-xccdf_org.ssgproject.content_profile_cis}"
REPORT_DIR="/var/log/openscap/reports/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$REPORT_DIR"

echo "[OpenSCAP] Iniciando scan com perfil: $PROFILE"
echo "[OpenSCAP] Diretorio de relatorios: $REPORT_DIR"

# Scan de sistema operacional
oscap xccdf eval \
  --profile "$PROFILE" \
  --results "$REPORT_DIR/results.xml" \
  --report "$REPORT_DIR/report.html" \
  --oval-results \
  /usr/share/xml/scap/ssg/content/ssg-rhel9-ds.xml 2>/dev/null || true

# Verificar resultados
PASS_COUNT=$(grep -c "pass" "$REPORT_DIR/results.xml" 2>/dev/null || echo "0")
FAIL_COUNT=$(grep -c "fail" "$REPORT_DIR/results.xml" 2>/dev/null || echo "0")
TOTAL=$((PASS_COUNT + FAIL_COUNT))

if [ "$TOTAL" -gt 0 ]; then
  SCORE=$((PASS_COUNT * 100 / TOTAL))
  echo "[OpenSCAP] Score: ${SCORE}% ($PASS_COUNT pass, $FAIL_COUNT fail)"
else
  echo "[OpenSCAP] Nenhum resultado encontrado"
  SCORE=0
fi

# Gerar JSON para integracao
python3 - <<EOF
import xml.etree.ElementTree as ET
import json

tree = ET.parse("$REPORT_DIR/results.xml")
root = tree.getroot()

results = []
for rule in root.iter("{http://checklists.nist.gov/xccdf/1.2}rule-result"):
    rule_id = rule.get("idref")
    result = rule.find("{http://checklists.nist.gov/xccdf/1.2}result").text
    results.append({"rule": rule_id, "status": result})

report = {
    "profile": "$PROFILE",
    "score": $SCORE,
    "pass_count": $PASS_COUNT,
    "fail_count": $FAIL_COUNT,
    "results": results
}

with open("$REPORT_DIR/summary.json", "w") as f:
    json.dump(report, f, indent=2)

print(f"[OpenSCAP] Relatorio JSON salvo em $REPORT_DIR/summary.json")
EOF

# Upload para evidencia
if [ -n "${EVIDENCE_BUCKET:-}" ]; then
  aws s3 sync "$REPORT_DIR" "$EVIDENCE_BUCKET/openscap/$(date +%Y%m%d)/"
  echo "[OpenSCAP] Relatorios enviados para $EVIDENCE_BUCKET"
fi
```

### 6.3 Reporting

```python
# openscap_reporter.py
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class OpenSCAPResult:
    rule_id: str
    status: str  # pass, fail, notchecked, error, unknown
    severity: str = ""
    description: str = ""
    remediation: str = ""


@dataclass
class OpenSCAPReport:
    scan_date: datetime
    profile: str
    target: str
    results: List[OpenSCAPResult] = field(default_factory=list)

    @property
    def total_rules(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "fail")

    @property
    def score(self) -> float:
        if self.total_rules == 0:
            return 0.0
        return (self.passed / self.total_rules) * 100

    def failed_by_severity(self) -> Dict[str, int]:
        counts = {}
        for r in self.results:
            if r.status == "fail":
                counts[r.severity] = counts.get(r.severity, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_date": self.scan_date.isoformat(),
            "profile": self.profile,
            "target": self.target,
            "summary": {
                "total_rules": self.total_rules,
                "passed": self.passed,
                "failed": self.failed,
                "score": f"{self.score:.1f}%",
                "failed_by_severity": self.failed_by_severity()
            },
            "failed_rules": [
                {
                    "rule_id": r.rule_id,
                    "severity": r.severity,
                    "description": r.description,
                    "remediation": r.remediation
                }
                for r in self.results if r.status == "fail"
            ]
        }


class OpenSCAPRunner:
    def __init__(self, content_path: str):
        self.content_path = content_path

    def run_scan(
        self,
        profile: str,
        output_dir: str,
        report_format: str = "xml"
    ) -> OpenSCAPReport:
        results_file = f"{output_dir}/results.{report_format}"
        report_file = f"{output_dir}/report.html"

        cmd = [
            "oscap", "xccdf", "eval",
            "--profile", profile,
            "--results", results_file,
            "--report", report_file,
            self.content_path
        ]

        subprocess.run(cmd, check=False, capture_output=True)

        report = OpenSCAPReport(
            scan_date=datetime.now(),
            profile=profile,
            target=subprocess.run(
                ["hostname"], capture_output=True, text=True
            ).stdout.strip()
        )

        try:
            tree = ET.parse(results_file)
            root = tree.getroot()
            ns = {"xccdf": "http://checklists.nist.gov/xccdf/1.2"}

            for rule_result in root.iter("{http://checklists.nist.gov/xccdf/1.2}rule-result"):
                result = OpenSCAPResult(
                    rule_id=rule_result.get("idref", ""),
                    status=rule_result.find(
                        "{http://checklists.nist.gov/xccdf/1.2}result"
                    ).text or "unknown"
                )
                report.results.append(result)
        except (ET.ParseError, FileNotFoundError):
            pass

        return report
```

### 6.4 Complete OpenSCAP Pipeline

```yaml
# .github/workflows/openscap-compliance.yml
name: OpenSCAP Compliance Pipeline

on:
  schedule:
    - cron: "0 3 * * 1"  # Toda segunda-feira as 3h UTC
  workflow_dispatch:
    inputs:
      profile:
        description: "Perfil OpenSCAP"
        required: true
        default: "PCI-DSS"
        type: choice
        options:
          - PCI-DSS
          - CIS
          - STIG
          - HIPAA

jobs:
  openscap-scan:
    name: "OpenSCAP Compliance Scan"
    runs-on: self-hosted
    strategy:
      matrix:
        target: [web-server, api-server, database-server]
    steps:
      - uses: actions/checkout@v4

      - name: Instalar OpenSCAP
        run: |
          sudo apt-get update
          sudo apt-get install -y libopenscap8 ssg-debian9

      - name: Executar scan
        run: |
          PROFILE="xccdf_org.ssgproject.content_profile_${{ github.event.inputs.profile || 'pci-dss' }}"
          bash scripts/openscap/openscap_scan.sh "$PROFILE"

      - name: Verificar score minimo
        run: |
          SCORE=$(cat /var/log/openscap/reports/*/summary.json | \
            python3 -c "import json,sys; print(json.load(sys.stdin)['score'])")
          MIN_SCORE=80
          if [ "$(echo "$SCORE < $MIN_SCORE" | bc)" -eq 1 ]; then
            echo "::error::Score $SCORE abaixo do minimo $MIN_SCORE%"
            exit 1
          fi

      - name: Upload relatorios
        run: |
          aws s3 sync /var/log/openscap/reports/ \
            s3://compliance-evidence/openscap/${{ matrix.target }}/$(date +%Y%m%d)/
```

---

## 7. Policy as Code

### 7.1 OPA/Rego for Compliance

Open Policy Agent (OPA) e o padrao para politicas como codigo. Com Rego, voce pode expressar regras de compliance de forma declarativa e verificavel.

```rego
# policy/iam.rego
package compliance.iam

import future.keywords.in
import future.keywords.if

default allow = false

# Regra: Usuarios nao devem ter acesso direto ao producao
deny[msg] {
    input.iam_user.policies[_].effect == "Allow"
    input.iam_user.policies[_].resource == "*"
    input.iam_user.policies[_].action == "*"
    msg := sprintf("Usuario %s tem acesso admin total - viola least privilege", [input.iam_user.name])
}

# Regra: MFA deve estar habilitado para todos os usuarios
deny[msg] {
    input.iam_user.mfa_enabled == false
    msg := sprintf("Usuario %s nao tem MFA habilitado - obrigatorio por compliance", [input.iam_user.name])
}

# Regra: Credenciais devem expirar em no maximo 90 dias
deny[msg] {
    days_since_rotation := time.now_ns() - input.iam_user.access_key_last_rotated
    days := days_since_rotation / (1000000000 * 86400)
    days > 90
    msg := sprintf("Credenciais do usuario %s tem %d dias sem rotacao - maximo 90 dias", [input.iam_user.name, days])
}

# Regra: Nao devem existir access keys para contas root
deny[msg] {
    input.iam_user.is_root == true
    input.iam_user.access_keys_count > 0
    msg := "Conta root nao deve ter access keys"
}

# Regra: Policies devem ser especificas, nao wildcard
deny[msg] {
    policy := input.iam_user.policies[_]
    policy.action == "*"
    policy.resource == "*"
    msg := sprintf("Policy %s usa wildcards em acao e recurso - deve ser especifica", [policy.name])
}

# Regra: Contas devem ser revisadas a cada 90 dias
deny[msg] {
    input.iam_user.last_reviewed == null
    msg := sprintf("Usuario %s nunca foi revisado", [input.iam_user.name])
}

deny[msg] {
    days_since_review := time.now_ns() - input.iam_user.last_reviewed
    days := days_since_review / (1000000000 * 86400)
    days > 90
    msg := sprintf("Usuario %s nao e revisado a %d dias - revisao trimestral obrigatoria", [input.iam_user.name, days])
}
```

```rego
# policy/deployment.rego
package compliance.deployment

default allow = false

# Regra: Containers nao devem rodar como root
deny[msg] {
    input.container.run_as_root == true
    msg := sprintf("Container %s roda como root - viola seguranca", [input.container.name])
}

# Regra: Imagens devem vir de registries aprovadas
deny[msg] {
    input.container.image_registry not in data.approved_registries
    msg := sprintf("Imagem %s vem de registry nao aprovado: %s", [
        input.container.image, input.container.image_registry
    ])
}

# Regra: Recursos devem ter limites definidos
deny[msg] {
    not input.container.resources.limits.cpu
    msg := sprintf("Container %s nao tem limite de CPU definido", [input.container.name])
}

deny[msg] {
    not input.container.resources.limits.memory
    msg := sprintf("Container %s nao tem limite de memoria definido", [input.container.name])
}

# Regra: Health check e obrigatorio
deny[msg] {
    not input.container.health_check
    msg := sprintf("Container %s nao tem health check configurado", [input.container.name])
}

# Regra: Variaveis de ambiente nao devem conter secrets
deny[msg] {
    env := input.container.env[_]
    contains(lower(env.name), "password") or
    contains(lower(env.name), "secret") or
    contains(lower(env.name), "token") or
    contains(lower(env.name), "api_key")
    msg := sprintf("Variavel de ambiente %s parece conter um segredo - use secret management", [env.name])
}

# Regra: Network policy deve ser definida
deny[msg] {
    not input.container.network_policy
    msg := sprintf("Container %s nao tem network policy - comunicao deve ser restrita", [input.container.name])
}

# Regra: ReadOnlyRootFilesystem deve ser verdadeiro
deny[msg] {
    input.container.security_context.read_only_root_filesystem != true
    msg := sprintf("Container %s nao tem filesystem read-only", [input.container.name])
}
```

### 7.2 Sentinel for Terraform

HashiCorp Sentinel fornece politicas para infraestrutura como codigo antes do apply.

```hcl
# policy/sentinel/s3-encryption.sentinel
import "tfplan/v2" as tfplan

# Regra: Todos os buckets S3 devem ter criptografia habilitada
s3_encryption_required = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_s3_bucket" or
        (
            resource.change.actions contains "create" or
            resource.change.actions contains "update"
        ) implies
        resource.change.after.server_side_encryption_configuration is not null
    }
}

# Regra: Versionamento deve estar habilitado
s3_versioning_required = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_s3_bucket" or
        resource.change.after.versioning is not null and
        resource.change.after.versioning[0].enabled is true
    }
}

# Regra: Block public access
s3_public_access_blocked = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_s3_bucket" or
        resource.change.after.block_public_acls is true
    }
}

# Regra: Lifecycle policies para dados antigos
s3_lifecycle_required = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_s3_bucket" or
        resource.change.after.lifecycle_rule is not null
    }
}

# Main policy
main = rule {
    s3_encryption_required and
    s3_versioning_required and
    s3_public_access_blocked and
    s3_lifecycle_required
}
```

```hcl
# policy/sentinel/encryption.sentinel
import "tfplan/v2" as tfplan

# Regra: Bancos de dados devem ter criptografia habilitada
rds_encryption_required = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_db_instance" or
        resource.change.after.storage_encrypted is true
    }
}

# Regra: RDS nao deve ser acessivel publicamente
rds_no_public_access = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_db_instance" or
        resource.change.after.publicly_accessible is not true
    }
}

# Regra: ElastiCache deve ter encryption at rest
elasticache_encryption = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_elasticache_cluster" or
        resource.change.after.at_rest_encryption_enabled is true
    }
}

# Regra: KMS keys devem ter rotacao automatica
kms_rotation_enabled = rule {
    all tfplan.resource_changes as _, resource {
        resource.type is not "aws_kms_key" or
        resource.change.after.enable_key_rotation is true
    }
}

main = rule {
    rds_encryption_required and
    rds_no_public_access and
    elasticache_encryption and
    kms_rotation_enabled
}
```

### 7.3 Kyverno for Kubernetes

Kyverno e o policy engine nativo para Kubernetes, escrito em YAML sem necessidade de linguagem de programacao separada.

```yaml
# kyverno-policies/require-labels.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-labels
  annotations:
    policies.kyverno.io/title: Require Labels
    policies.kyverno.io/category: Compliance
    policies.kyverno.io/severity: high
    policies.kyverno.io/subject: Pod, Deployment, StatefulSet, DaemonSet
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-required-labels
      match:
        any:
          - resources:
              kinds:
                - Pod
                - Deployment
                - StatefulSet
                - DaemonSet
      validate:
        message: "Labels obrigatórias ausentes: app, env, team, cost-center"
        pattern:
          metadata:
            labels:
              app: "?*"
              env: "?*"
              team: "?*"
              cost-center: "?*"

---
# kyverno-policies/restrict-image-registries.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
  annotations:
    policies.kyverno.io/title: Restrict Image Registries
    policies.kyverno.io/category: Security
    policies.kyverno.io/severity: critical
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: validate-registries
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Imagem deve vir de registry aprovado"
        pattern:
          spec:
            containers:
              - image: "registry.company.com/* | gcr.io/project-id/*"

---
# kyverno-policies/require-security-context.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-security-context
  annotations:
    policies.kyverno.io/title: Require Security Context
    policies.kyverno.io/category: Security
    policies.kyverno.io/severity: critical
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: require-run-as-nonroot
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Containers devem rodar como non-root"
        pattern:
          spec:
            securityContext:
              runAsNonRoot: true

    - name: require-read-only-rootfs
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Root filesystem deve ser read-only"
        pattern:
          spec:
            containers:
              - securityContext:
                  readOnlyRootFilesystem: true

    - name: drop-all-capabilities
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Capabilities devem ser dropped (exceto NET_BIND_SERVICE)"
        pattern:
          spec:
            containers:
              - securityContext:
                  capabilities:
                    drop:
                      - ALL
                    add:
                      - NET_BIND_SERVICE

---
# kyverno-policies/require-resource-limits.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
  annotations:
    policies.kyverno.io/title: Require Resource Limits
    policies.kyverno.io/category: Compliance
    policies.kyverno.io/severity: medium
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: check-resource-limits
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Todos os containers devem ter limites de recursos definidos"
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"
                    cpu: "?*"
                  requests:
                    memory: "?*"
                    cpu: "?*"

---
# kyverno-policies/disable-debug-tools.yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disable-debug-tools
  annotations:
    policies.kyverno.io/title: Disable Debug Tools
    policies.kyverno.io/category: Security
    policies.kyverno.io/severity: high
spec:
  validationFailureAction: Enforce
  background: true
  rules:
    - name: deny-nsenter
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Uso de nsenter e proibido"
        deny:
          conditions:
            any:
              - key: "{{ request.object.spec.containers[].command[] }}"
                operator: AnyIn
                value: ["nsenter"]

    - name: deny-strace
      match:
        any:
          - resources:
              kinds:
                - Pod
      validate:
        message: "Uso de strace e proibido"
        deny:
          conditions:
            any:
              - key: "{{ request.object.spec.containers[].command[] }}"
                operator: AnyIn
                value: ["strace"]
```

### 7.4 Complete Policy Examples

```yaml
# policy/comprehensive-compliance.yaml
compliance_policies:
  soc2:
    - policy: "Require MFA for all service accounts"
      engine: "opa"
      file: "policy/iam/mfa_requirement.rego"
      enforcement: "block"

    - policy: "Ensure audit logs are enabled"
      engine: "opa"
      file: "policy/logging/audit_enabled.rego"
      enforcement: "block"

    - policy: "Require encryption at rest"
      engine: "sentinel"
      file: "policy/terraform/encryption_at_rest.sentinel"
      enforcement: "block"

  pci_dss:
    - policy: "No card data in logs"
      engine: "opa"
      file: "policy/logging/no_card_data.rego"
      enforcement: "block"

    - policy: "Network segmentation enforcement"
      engine: "kyverno"
      file: "policy/kubernetes/network_segmentation.yaml"
      enforcement: "block"

    - policy: "TLS 1.2+ only"
      engine: "opa"
      file: "policy/tls/tls_version.rego"
      enforcement: "block"

  lgpd:
    - policy: "Data minimization"
      engine: "opa"
      file: "policy/data/minimization.rego"
      enforcement: "warn"

    - policy: "Consent verification"
      engine: "opa"
      file: "policy/data/consent_check.rego"
      enforcement: "block"

    - policy: "Right to erasure support"
      engine: "opa"
      file: "policy/data/erasure_support.rego"
      enforcement: "audit"
```

---

## 8. Audit Trail

### 8.1 Immutable Audit Logs

Um audit trail imutavel e essencial para demonstrar compliance. Logs que podem ser alterados ou excluidos nao servem como evidencia em auditorias.

```yaml
# audit-trail.yaml
audit_trail:
  log_sources:
    - name: "api_access"
      type: "structured"
      format: "json"
      fields:
        - timestamp
        - user_id
        - source_ip
        - action
        - resource
        - result
        - request_id
        - user_agent
        - geolocation

    - name: "infrastructure_changes"
      type: "structured"
      format: "json"
      fields:
        - timestamp
        - user_id
        - tool
        - resource_type
        - resource_id
        - action
        - before_state
        - after_state
        - approval_id

    - name: "security_events"
      type: "structured"
      format: "json"
      fields:
        - timestamp
        - event_type
        - severity
        - source
        - description
        - affected_resources
        - mitre_technique
        - response_actions

  immutability:
    method: "append_only"
    storage:
      primary: "AWS CloudWatch Logs"
      archive: "S3 with Object Lock (WORM)"
      blockchain_anchor: true
      anchor_service: "AWS QLDB"

    verification:
      frequency: "every_6_hours"
      method: "hash_chain_verification"
      alert_on_tamper: true
      alert_channel: "pagerduty"

  retention:
    hot: "90 days"
    warm: "365 days"
    cold: "2555 days"  # 7 years

  access_control:
    write: "audit-service-only"
    read: "compliance-team, auditors, legal"
    delete: "prohibited"

  integrity:
    checksum_algorithm: "SHA-256"
    chain_verification: true
    tamper_detection: "hash_chain_break_detection"
```

### 8.2 Log Integrity Verification

```python
# log_integrity.py
import hashlib
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    timestamp: datetime
    source: str
    event_type: str
    content: Dict[str, Any]
    previous_hash: str = ""
    entry_hash: str = ""

    def compute_hash(self) -> str:
        data = json.dumps({
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "event_type": self.event_type,
            "content": self.content,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        self.entry_hash = hashlib.sha256(data.encode()).hexdigest()
        return self.entry_hash


@dataclass
class AuditChain:
    entries: List[LogEntry] = field(default_factory=list)

    def append(
        self,
        source: str,
        event_type: str,
        content: Dict[str, Any]
    ) -> LogEntry:
        previous_hash = self.entries[-1].entry_hash if self.entries else "genesis"

        entry = LogEntry(
            timestamp=datetime.now(),
            source=source,
            event_type=event_type,
            content=content,
            previous_hash=previous_hash
        )
        entry.compute_hash()
        self.entries.append(entry)
        return entry

    def verify_integrity(self) -> List[Dict[str, Any]]:
        violations = []
        for i, entry in enumerate(self.entries):
            expected_prev = self.entries[i - 1].entry_hash if i > 0 else "genesis"
            if entry.previous_hash != expected_prev:
                violations.append({
                    "entry_index": i,
                    "timestamp": entry.timestamp.isoformat(),
                    "violation": "Chain broken",
                    "expected_prev": expected_prev,
                    "actual_prev": entry.previous_hash
                })

            computed_hash = entry.compute_hash()
            if computed_hash != entry.entry_hash:
                violations.append({
                    "entry_index": i,
                    "timestamp": entry.timestamp.isoformat(),
                    "violation": "Hash mismatch",
                    "expected_hash": computed_hash,
                    "actual_hash": entry.entry_hash
                })

        return violations

    def export(self, filepath: str):
        data = {
            "chain_length": len(self.entries),
            "last_hash": self.entries[-1].entry_hash if self.entries else None,
            "entries": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "source": e.source,
                    "event_type": e.event_type,
                    "content": e.content,
                    "previous_hash": e.previous_hash,
                    "entry_hash": e.entry_hash
                }
                for e in self.entries
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    chain = AuditChain()

    # Exemplo de uso
    chain.append(
        source="github",
        event_type="code_merge",
        content={
            "repository": "api-service",
            "branch": "main",
            "commit": "abc123",
            "author": "dev@company.com",
            "reviewers": ["lead@company.com"]
        }
    )

    chain.append(
        source="terraform",
        event_type="resource_created",
        content={
            "provider": "aws",
            "resource": "aws_instance",
            "id": "i-1234567890abcdef0",
            "user": "deployer@company.com",
            "approval": "JIRA-1234"
        }
    )

    violations = chain.verify_integrity()
    if violations:
        print(f"[ALERTA] {len(violations)} violacoes de integridade detectadas!")
        for v in violations:
            print(f"  - Entry {v['entry_index']}: {v['violation']}")
    else:
        print("[OK] Cadeia de audit trail verificada com sucesso")

    chain.export("/var/log/audit/audit_chain.json")
```

### 8.3 Complete Audit Pipeline

```yaml
# audit-pipeline.yaml
audit_pipeline:
  collection:
    sources:
      - name: "kubernetes_audit"
        type: "webhook"
        endpoint: "https://audit.internal:8443/k8s"
        events:
          - "create"
          - "update"
          - "delete"
          - "bind"
          - "impersonate"

      - name: "cloud_trail"
        type: "aws_cloudtrail"
        events: "all"
        regions: ["us-east-1", "us-west-2", "eu-west-1"]

      - name: "application_audit"
        type: "custom_api"
        endpoint: "https://api.company.com/audit"
        events:
          - "login_success"
          - "login_failure"
          - "permission_change"
          - "data_access"
          - "data_export"
          - "config_change"

  processing:
    deduplication:
      enabled: true
      window_seconds: 60
      strategy: "keep_latest"

    enrichment:
      enabled: true
      fields:
        - geoip_lookup
        - user_identity
        - asset_inventory
        - threat_intelligence

    classification:
      levels:
        - info: "Operational events"
        - warning: "Policy violations"
        - critical: "Security incidents"
        - emergency: "Active attacks"

  storage:
    hot:
      provider: "elasticsearch"
      retention_days: 30
      replicas: 3
      index_pattern: "audit-{yyyy.MM.dd}"

    warm:
      provider: "elasticsearch"
      retention_days: 365
      ilm_policy: "audit-warm"

    cold:
      provider: "s3"
      format: "parquet"
      retention_days: 2555
      encryption: "AES-256"
      object_lock: true

  integrity:
    verification_frequency: "hourly"
    method: "hash_chain"
    alert_on_tamper: true

  compliance_queries:
    - name: "Logins nas ultimas 24h"
      query: |
        SELECT user_id, COUNT(*) as login_count
        FROM audit_logs
        WHERE event_type = 'login_success'
        AND timestamp > NOW() - INTERVAL 24 HOUR
        GROUP BY user_id
        HAVING login_count > 50

    - name: "Acessos fora do horario"
      query: |
        SELECT user_id, source_ip, timestamp
        FROM audit_logs
        WHERE EXTRACT(HOUR FROM timestamp) NOT BETWEEN 8 AND 18
        AND event_type IN ('data_access', 'data_export')

    - name: "Falhas de login repetidas"
      query: |
        SELECT source_ip, COUNT(*) as failures
        FROM audit_logs
        WHERE event_type = 'login_failure'
        AND timestamp > NOW() - INTERVAL 1 HOUR
        GROUP BY source_ip
        HAVING failures > 5
```

---

## 9. Evidence Automation

### 9.1 Automated Evidence Collection

A coleta automatizada de evidencias garante que toda verificacao de compliance produza uma evidencia auditavel e rastreavel.

```yaml
# evidence-automation.yaml
evidence_automation:
  framework:
    collectors:
      - name: "SCA-Evidence-Collector"
        version: "2.0"
        description: "Coleta evidencias automaticas de todos os sistemas"

    templates:
      - name: "SOC2-evidence"
        controls:
          - CC6.1:
              type: "mfa_status"
              command: "python evidence/soc2_mfa.py"
              frequency: daily
          - CC6.6:
              type: "vulnerability_scan"
              command: "python evidence/vuln_scan.py"
              frequency: weekly
          - CC8.1:
              type: "change_management"
              command: "python evidence/change_management.py"
              frequency: on_event

      - name: "PCI-evidence"
        controls:
          - "3.4":
              type: "encryption_status"
              command: "python evidence/pci_encryption.py"
              frequency: daily
          - "8.3":
              type: "mfa_enforcement"
              command: "python evidence/pci_mfa.py"
              frequency: daily

      - name: "LGPD-evidence"
        controls:
          - "Art. 46":
              type: "security_measures"
              command: "python evidence/lgpd_security.py"
              frequency: weekly
          - "Art. 37":
              type: "processing_records"
              command: "python evidence/lgpd_processing.py"
              frequency: monthly

    storage:
      primary:
        type: "s3"
        bucket: "compliance-evidence-${AWS_ACCOUNT_ID}"
        encryption: "AES-256"
        versioning: true
        object_lock: true

      backup:
        type: "s3"
        bucket: "compliance-evidence-backup-${AWS_ACCOUNT_ID}"
        replication: "cross-region"
        region: "us-west-2"

    integrity:
      checksum: "SHA-256"
      blockchain: true
      verification_frequency: "every_6_hours"

    access_control:
      write: "evidence-collector-service"
      read:
        - "compliance-team"
        - "auditors"
        - "security-team"
        - "legal"
      deny:
        - "developers"  # Cannot modify evidence
        - "operations"  # Cannot delete evidence
```

### 9.2 Evidence Storage

```python
# evidence_storage.py
import hashlib
import json
import boto3
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EvidenceRecord:
    evidence_id: str
    control_id: str
    framework: str
    collection_date: datetime
    content: Dict[str, Any]
    collector: str
    source_system: str
    checksum: str = ""

    def __post_init__(self):
        content_str = json.dumps(self.content, sort_keys=True)
        self.checksum = hashlib.sha256(content_str.encode()).hexdigest()

    def to_s3_key(self) -> str:
        return (
            f"{self.framework}/{self.control_id}/"
            f"{self.collection_date.strftime('%Y/%m/%d')}/"
            f"{self.evidence_id}.json"
        )


class EvidenceStorage:
    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3 = boto3.client("s3", region_name=region)

    def store_evidence(self, evidence: EvidenceRecord) -> str:
        s3_key = evidence.to_s3_key()

        body = json.dumps({
            "evidence_id": evidence.evidence_id,
            "control_id": evidence.control_id,
            "framework": evidence.framework,
            "collection_date": evidence.collection_date.isoformat(),
            "content": evidence.content,
            "collector": evidence.collector,
            "source_system": evidence.source_system,
            "checksum": evidence.checksum
        }, indent=2)

        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="aws:kms",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=datetime(2031, 12, 31),
            Metadata={
                "control-id": evidence.control_id,
                "framework": evidence.framework,
                "checksum-sha256": evidence.checksum
            }
        )

        return f"s3://{self.bucket_name}/{s3_key}"

    def verify_evidence_integrity(
        self, evidence: EvidenceRecord
    ) -> bool:
        s3_key = evidence.to_s3_key()

        response = self.s3.get_object(
            Bucket=self.bucket_name,
            Key=s3_key
        )

        body = json.loads(response["Body"].read().decode("utf-8"))

        content_str = json.dumps(body["content"], sort_keys=True)
        current_checksum = hashlib.sha256(content_str.encode()).hexdigest()

        return current_checksum == evidence.checksum

    def list_evidence(
        self,
        framework: str,
        control_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        prefix = f"{framework}/"
        if control_id:
            prefix += f"{control_id}/"

        paginator = self.s3.get_paginator("list_objects_v2")
        evidence_list = []

        for page in paginator.paginate(
            Bucket=self.bucket_name, Prefix=prefix
        ):
            for obj in page.get("Contents", []):
                evidence_list.append({
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "etag": obj["ETag"]
                })

        return evidence_list
```

### 9.3 Evidence Reporting

```python
# evidence_reporter.py
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class FrameworkSummary:
    framework: str
    total_controls: int
    controls_with_evidence: int
    controls_missing_evidence: int
    evidence_freshness_days: int
    compliance_score: float

    @property
    def coverage(self) -> float:
        if self.total_controls == 0:
            return 0.0
        return (self.controls_with_evidence / self.total_controls) * 100


@dataclass
class EvidenceReport:
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    summaries: List[FrameworkSummary] = field(default_factory=list)
    gaps: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "frameworks": [
                {
                    "name": s.framework,
                    "total_controls": s.total_controls,
                    "with_evidence": s.controls_with_evidence,
                    "missing_evidence": s.controls_missing_evidence,
                    "coverage": f"{s.coverage:.1f}%",
                    "freshness_days": s.evidence_freshness_days,
                    "score": f"{s.compliance_score:.1f}%"
                }
                for s in self.summaries
            ],
            "gaps": self.gaps,
            "overall_score": self._overall_score()
        }

    def _overall_score(self) -> str:
        if not self.summaries:
            return "N/A"
        total = sum(s.total_controls for s in self.summaries)
        if total == 0:
            return "N/A"
        covered = sum(s.controls_with_evidence for s in self.summaries)
        return f"{(covered / total * 100):.1f}%"


class EvidenceReporter:
    def __init__(self):
        self.evidence_store: List[Dict[str, Any]] = []

    def load_evidence(self, filepath: str):
        with open(filepath) as f:
            self.evidence_store = json.load(f)

    def generate_report(
        self,
        frameworks: List[str],
        controls_per_framework: Dict[str, int]
    ) -> EvidenceReport:
        summaries = []
        gaps = []

        for framework in frameworks:
            framework_evidence = [
                e for e in self.evidence_store
                if e.get("framework") == framework
            ]

            controls_with_evidence = set(
                e["control_id"] for e in framework_evidence
            )
            total = controls_per_framework.get(framework, 0)
            missing = total - len(controls_with_evidence)

            for ctrl_id in range(1, total + 1):
                ctrl_str = f"{framework}-{ctrl_id:03d}"
                if ctrl_str not in controls_with_evidence:
                    gaps.append({
                        "framework": framework,
                        "control_id": ctrl_str,
                        "severity": "high",
                        "description": f"Missing evidence for {ctrl_str}"
                    })

            freshness = 0
            if framework_evidence:
                dates = [
                    datetime.fromisoformat(e["collection_date"])
                    for e in framework_evidence
                    if "collection_date" in e
                ]
                if dates:
                    latest = max(dates)
                    freshness = (datetime.now() - latest).days

            score = len(controls_with_evidence) / total * 100 if total > 0 else 0

            summaries.append(FrameworkSummary(
                framework=framework,
                total_controls=total,
                controls_with_evidence=len(controls_with_evidence),
                controls_missing_evidence=missing,
                evidence_freshness_days=freshness,
                compliance_score=score
            ))

        return EvidenceReport(
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(days=90),
            period_end=datetime.now(),
            summaries=summaries,
            gaps=gaps
        )
```

### 9.4 Complete Evidence Pipeline

{% raw %}
```yaml
# .github/workflows/evidence-pipeline.yml
name: Evidence Collection Pipeline

on:
  schedule:
    - cron: "0 2 * * *"  # Diario as 2h UTC
  workflow_dispatch:

jobs:
  collect-evidence:
    name: "Coletar Evidencias"
    runs-on: ubuntu-latest
    strategy:
      matrix:
        framework: [SOC2, PCI_DSS, LGPD]
    steps:
      - uses: actions/checkout@v4

      - name: Configurar AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Coletar evidencias ${{ matrix.framework }}
        run: |
          python scripts/evidence/collect.py \
            --framework ${{ matrix.framework }} \
            --output /tmp/evidence-${{ matrix.framework }}.json \
            --format json

      - name: Verificar integridade
        run: |
          python scripts/evidence/verify_integrity.py \
            --evidence-file /tmp/evidence-${{ matrix.framework }}.json

      - name: Armazenar evidencias
        run: |
          aws s3 cp /tmp/evidence-${{ matrix.framework }}.json \
            s3://compliance-evidence/${{ matrix.framework }}/$(date +%Y%m%d)/ \
            --metadata '{"checksum-sha256":"'$(sha256sum /tmp/evidence-${{ matrix.framework }}.json | cut -d' ' -f1)'"}'

  generate-report:
    name: "Gerar Relatorio de Evidencias"
    runs-on: ubuntu-latest
    needs: collect-evidence
    steps:
      - uses: actions/checkout@v4

      - name: Gerar relatorio consolidado
        run: |
          python scripts/evidence/generate_report.py \
            --period 30 \
            --output /tmp/evidence-report.json

      - name: Verificar gaps
        run: |
          GAPS=$(python scripts/evidence/check_gaps.py \
            --report /tmp/evidence-report.json \
            --min-coverage 95)
          if [ "$GAPS" -gt 0 ]; then
            echo "::warning::$GAPS controles sem evidencia completa"
          fi

      - name: Upload relatorio
        run: |
          aws s3 cp /tmp/evidence-report.json \
            s3://compliance-evidence/reports/$(date +%Y%m%d)-evidence-report.json

      - name: Notificar gaps
        if: failure()
        run: |
          python scripts/evidence/notify_gaps.py \
            --report /tmp/evidence-report.json \
            --slack-webhook ${{ secrets.SLACK_WEBHOOK_URL }}
```
{% endraw %}

---

## 10. Exemplo Completo: Compliance Pipeline

### 10.1 Continuous Compliance Scanning

Esta secao integra todos os componentes anteriores em uma pipeline completa de compliance continuo.

```yaml
# compliance-pipeline.yaml
# Pipeline completa de compliance automatizado

name: "Compliance Pipeline"

on:
  schedule:
    - cron: "0 */6 * * *"  # A cada 6 horas
  push:
    branches: [main, develop]
    paths:
      - "infrastructure/**"
      - "src/**"
      - "config/**"
      - "policy/**"
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      frameworks:
        description: "Frameworks para verificar"
        required: false
        default: "SOC2,PCI_DSS,LGPD,CIS"
        type: string

env:
  EVIDENCE_BUCKET: s3://compliance-evidence-${{ secrets.AWS_ACCOUNT_ID }}
  MIN_COMPLIANCE_SCORE: 80

jobs:
  compliance-scan:
    name: "Continuous Compliance Scan"
    runs-on: ubuntu-latest
    strategy:
      matrix:
        framework: [SOC2, PCI_DSS, LGPD, CIS]
    steps:
      - uses: actions/checkout@v4

      - name: Configurar ambiente
        run: |
          pip install boto3 requests pyyaml semgrep safety

      - name: Executar scan ${{ matrix.framework }}
        run: |
          python scripts/compliance/scan.py \
            --framework ${{ matrix.framework }} \
            --output /tmp/scan-${{ matrix.framework }}.json \
            --severity-threshold medium \
            --fail-on critical,high

      - name: Verificar score minimo
        run: |
          SCORE=$(python scripts/compliance/get_score.py \
            --scan-result /tmp/scan-${{ matrix.framework }}.json)
          echo "Score ${{ matrix.framework }}: ${SCORE}%"
          if [ "$(echo "$SCORE < $MIN_COMPLIANCE_SCORE" | bc)" -eq 1 ]; then
            echo "::error::${{ matrix.framework }} score $SCORE abaixo do minimo $MIN_COMPLIANCE_SCORE%"
            exit 1
          fi

      - name: Coletar evidencias
        run: |
          python scripts/evidence/collect_from_scan.py \
            --scan-result /tmp/scan-${{ matrix.framework }}.json \
            --framework ${{ matrix.framework }} \
            --output /tmp/evidence-${{ matrix.framework }}.json

      - name: Upload evidencias
        run: |
          aws s3 cp /tmp/evidence-${{ matrix.framework }}.json \
            $EVIDENCE_BUCKET/scan/$(date +%Y%m%d-%H%M)/${{ matrix.framework }}/

      - name: Upload resultado
        if: always()
        run: |
          aws s3 cp /tmp/scan-${{ matrix.framework }}.json \
            $EVIDENCE_BUCKET/scan-results/$(date +%Y%m%d-%H%M)/${{ matrix.framework }}/

  policy-validation:
    name: "Policy as Code Validation"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Instalar OPA
        run: |
          curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64
          chmod +x /usr/local/bin/opa

      - name: Validar politicas OPA
        run: |
          for policy in $(find policy/rego -name "*.rego"); do
            echo "Validating $policy..."
            opa eval --data "$policy" --input /dev/null "data"
          done

      - name: Validar politicas Kyverno
        run: |
          for policy in $(find policy/kyverno -name "*.yaml"); do
            echo "Validating $policy..."
            kubectl apply --dry-run=client -f "$policy"
          done

      - name: Validar politicas Sentinel
        run: |
          for policy in $(find policy/sentinel -name "*.sentinel"); do
            echo "Checking syntax: $policy"
            sentinel fmt "$policy"
          done

  remediation-tracking:
    name: "Remediation Tracking"
    runs-on: ubuntu-latest
    needs: [compliance-scan]
    if: always()
    steps:
      - uses: actions/checkout@v4

      - name: Analisar falhas
        run: |
          python scripts/remediation/analyze_failures.py \
            --scan-results /tmp/scan-*.json \
            --output /tmp/remediation-plan.json

      - name: Criar issues para remediation
        run: |
          python scripts/remediation/create_issues.py \
            --plan /tmp/remediation-plan.json \
            --github-token ${{ secrets.GITHUB_TOKEN }}

      - name: Verificar remediation pendentes
        run: |
          python scripts/remediation/check_overdue.py \
            --max-age-days 30 \
            --slack-webhook ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 10.2 Evidence Generation

```python
# evidence_generator.py
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class EvidencePackage:
    package_id: str
    generated_at: datetime
    framework: str
    scan_results: Dict[str, Any]
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_evidence(
        self,
        control_id: str,
        evidence_type: str,
        content: Dict[str, Any],
        source: str
    ):
        item = {
            "control_id": control_id,
            "type": evidence_type,
            "content": content,
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "checksum": hashlib.sha256(
                json.dumps(content, sort_keys=True).encode()
            ).hexdigest()
        }
        self.evidence_items.append(item)

    def generate_checksum(self) -> str:
        data = json.dumps({
            "package_id": self.package_id,
            "framework": self.framework,
            "items_count": len(self.evidence_items),
            "items_checksums": [
                item["checksum"] for item in self.evidence_items
            ]
        }, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "generated_at": self.generated_at.isoformat(),
            "framework": self.framework,
            "total_evidence_items": len(self.evidence_items),
            "integrity_checksum": self.generate_checksum(),
            "scan_results_summary": self.scan_results,
            "evidence_items": self.evidence_items,
            "metadata": self.metadata
        }


class ComplianceEvidenceGenerator:
    def __init__(self, organization: str):
        self.organization = organization

    def generate_soc2_package(
        self,
        scan_results: Dict[str, Any]
    ) -> EvidencePackage:
        package = EvidencePackage(
            package_id=f"soc2-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            generated_at=datetime.now(),
            framework="SOC2",
            scan_results=scan_results,
            metadata={
                "organization": self.organization,
                "audit_period": "annual",
                "auditor": "Internal Security Team"
            }
        )

        mfa_evidence = {
            "mfa_enforced_for_all_users": True,
            "mfa_provider": "Okta",
            "coverage_percentage": 100,
            "exceptions": [],
            "verification_date": datetime.now().isoformat()
        }
        package.add_evidence("CC6.1.1", "mfa_status", mfa_evidence, "okta")

        access_review_evidence = {
            "last_review_date": datetime.now().isoformat(),
            "total_users_reviewed": 150,
            "access_revoked": 12,
            "new_access_granted": 5,
            "review_completion_rate": 100
        }
        package.add_evidence(
            "CC6.1.3", "access_review", access_review_evidence, "okta"
        )

        vuln_scan_evidence = {
            "scanner": "Trivy + Semgrep",
            "last_scan": datetime.now().isoformat(),
            "critical_vulns": scan_results.get("critical", 0),
            "high_vulns": scan_results.get("high", 0),
            "medium_vulns": scan_results.get("medium", 0),
            "remediation_sla_days": {"critical": 1, "high": 7, "medium": 30}
        }
        package.add_evidence(
            "CC6.6.1", "vulnerability_scan", vuln_scan_evidence, "trivy"
        )

        return package

    def generate_lgpd_package(
        self,
        scan_results: Dict[str, Any]
    ) -> EvidencePackage:
        package = EvidencePackage(
            package_id=f"lgpd-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            generated_at=datetime.now(),
            framework="LGPD",
            scan_results=scan_results,
            metadata={
                "organization": self.organization,
                "dpo": "dpo@company.com",
                "authority": "ANPD"
            }
        )

        consent_evidence = {
            "consent_mechanism": "opt-in_granular",
            "purposes_documented": [
                "marketing", "analytics", "third_party_sharing"
            ],
            "withdrawal_available": True,
            "withdrawal_sla_hours": 72,
            "total_consents_active": 50000
        }
        package.add_evidence(
            "Art.8", "consent_management", consent_evidence, "consent_manager"
        )

        data_mapping_evidence = {
            "personal_data_assets": 15,
            "assets_with_encryption": 15,
            "encryption_coverage": "100%",
            "data_flows_documented": 25,
            "third_party_processors": 5,
            "dpia_completed": True
        }
        package.add_evidence(
            "Art.37", "data_mapping", data_mapping_evidence, "data_mapper"
        )

        return package

    def export_package(
        self,
        package: EvidencePackage,
        output_path: str
    ):
        with open(output_path, "w") as f:
            json.dump(package.to_dict(), f, indent=2)

        checksum_path = f"{output_path}.sha256"
        with open(checksum_path, "w") as f:
            f.write(package.generate_checksum())

        print(f"[EVIDENCE] Package exported to {output_path}")
        print(f"[EVIDENCE] Checksum: {package.generate_checksum()}")
```

### 10.3 Reporting

```python
# compliance_reporter.py
import json
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class ComplianceDashboard:
    generated_at: datetime
    organization: str
    frameworks: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def add_framework_result(
        self,
        framework: str,
        score: float,
        total_controls: int,
        passed: int,
        failed: int,
        critical_findings: int
    ):
        self.frameworks[framework] = {
            "score": score,
            "total_controls": total_controls,
            "passed": passed,
            "failed": failed,
            "critical_findings": critical_findings,
            "status": "compliant" if score >= 80 else "non_compliant"
        }

    def overall_score(self) -> float:
        if not self.frameworks:
            return 0.0
        scores = [f["score"] for f in self.frameworks.values()]
        return sum(scores) / len(scores)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "organization": self.organization,
            "overall_score": f"{self.overall_score():.1f}%",
            "frameworks": self.frameworks,
            "recommendations": self._generate_recommendations(),
            "trend": "improving"  # placeholder for historical comparison
        }

    def _generate_recommendations(self) -> List[Dict[str, str]]:
        recommendations = []
        for fw, data in self.frameworks.items():
            if data["score"] < 80:
                recommendations.append({
                    "framework": fw,
                    "priority": "high",
                    "recommendation": f"Aumentar score {fw} de {data['score']:.0f}% para >= 80%",
                    "impact": "compliance"
                })
            if data["critical_findings"] > 0:
                recommendations.append({
                    "framework": fw,
                    "priority": "critical",
                    "recommendation": f"Resolver {data['critical_findings']} findings criticos",
                    "impact": "security"
                })
        return recommendations


class ComplianceReporter:
    def __init__(self):
        self.dashboard = ComplianceDashboard(
            generated_at=datetime.now(),
            organization=""
        )

    def load_scan_results(self, results: List[Dict[str, Any]]):
        for result in results:
            self.dashboard.add_framework_result(
                framework=result["framework"],
                score=result["score"],
                total_controls=result["total"],
                passed=result["passed"],
                failed=result["failed"],
                critical_findings=result.get("critical", 0)
            )

    def generate_executive_summary(self) -> str:
        overall = self.dashboard.overall_score()
        lines = [
            "EXECUTIVE SUMMARY - Compliance Status",
            "=" * 50,
            f"Organization: {self.dashboard.organization}",
            f"Report Date: {self.dashboard.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"Overall Score: {overall:.1f}%",
            "",
            "Framework Scores:"
        ]

        for fw, data in self.dashboard.frameworks.items():
            status_icon = "PASS" if data["status"] == "compliant" else "FAIL"
            lines.append(
                f"  [{status_icon}] {fw}: {data['score']:.1f}% "
                f"({data['passed']}/{data['total_controls']} controls)"
            )

        lines.extend([
            "",
            "Recommendations:"
        ])
        for rec in self.dashboard._generate_recommendations():
            lines.append(
                f"  [{rec['priority'].upper()}] {rec['framework']}: "
                f"{rec['recommendation']}"
            )

        return "\n".join(lines)

    def export_dashboard(self, output_path: str):
        with open(output_path, "w") as f:
            json.dump(self.dashboard.to_dict(), f, indent=2)
```

### 10.4 Remediation Tracking

```python
# remediation_tracker.py
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class RemediationStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ACCEPTED_RISK = "accepted_risk"
    OVERDUE = "overdue"


@dataclass
class RemediationItem:
    item_id: str
    finding_id: str
    framework: str
    control_id: str
    severity: str
    description: str
    remediation_steps: List[str]
    created_at: datetime
    due_date: datetime
    assigned_to: str = ""
    status: RemediationStatus = RemediationStatus.OPEN
    resolved_at: Optional[datetime] = None
    resolution_notes: str = ""

    @property
    def is_overdue(self) -> bool:
        return (
            self.status not in (
                RemediationStatus.RESOLVED,
                RemediationStatus.ACCEPTED_RISK
            )
            and datetime.now() > self.due_date
        )

    @property
    def days_remaining(self) -> int:
        delta = self.due_date - datetime.now()
        return max(0, delta.days)


class RemediationTracker:
    def __init__(self):
        self.items: List[RemediationItem] = []

    def add_finding(
        self,
        finding_id: str,
        framework: str,
        control_id: str,
        severity: str,
        description: str,
        remediation_steps: List[str],
        assigned_to: str = ""
    ):
        sla_days = {
            "critical": 1,
            "high": 7,
            "medium": 30,
            "low": 90
        }

        item = RemediationItem(
            item_id=f"REM-{len(self.items) + 1:04d}",
            finding_id=finding_id,
            framework=framework,
            control_id=control_id,
            severity=severity,
            description=description,
            remediation_steps=remediation_steps,
            created_at=datetime.now(),
            due_date=datetime.now() + timedelta(
                days=sla_days.get(severity, 30)
            ),
            assigned_to=assigned_to
        )
        self.items.append(item)
        return item

    def get_overdue_items(self) -> List[RemediationItem]:
        return [item for item in self.items if item.is_overdue]

    def get_dashboard(self) -> Dict[str, Any]:
        status_counts = {}
        for item in self.items:
            status = item.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        severity_counts = {}
        for item in self.items:
            if item.status != RemediationStatus.RESOLVED:
                severity_counts[item.severity] = (
                    severity_counts.get(item.severity, 0) + 1
                )

        return {
            "total_findings": len(self.items),
            "by_status": status_counts,
            "open_by_severity": severity_counts,
            "overdue_count": len(self.get_overdue_items()),
            "average_resolution_days": self._avg_resolution_days(),
            "compliance_by_framework": self._by_framework()
        }

    def _avg_resolution_days(self) -> float:
        resolved = [
            item for item in self.items
            if item.resolved_at and item.status == RemediationStatus.RESOLVED
        ]
        if not resolved:
            return 0.0
        total_days = sum(
            (item.resolved_at - item.created_at).days
            for item in resolved
        )
        return total_days / len(resolved)

    def _by_framework(self) -> Dict[str, Dict[str, int]]:
        frameworks: Dict[str, Dict[str, int]] = {}
        for item in self.items:
            if item.framework not in frameworks:
                frameworks[item.framework] = {
                    "total": 0, "resolved": 0, "open": 0, "overdue": 0
                }
            frameworks[item.framework]["total"] += 1
            if item.status == RemediationStatus.RESOLVED:
                frameworks[item.framework]["resolved"] += 1
            elif item.is_overdue:
                frameworks[item.framework]["overdue"] += 1
            else:
                frameworks[item.framework]["open"] += 1
        return frameworks

    def export(self, filepath: str):
        data = {
            "generated_at": datetime.now().isoformat(),
            "dashboard": self.get_dashboard(),
            "items": [
                {
                    "item_id": item.item_id,
                    "finding_id": item.finding_id,
                    "framework": item.framework,
                    "control_id": item.control_id,
                    "severity": item.severity,
                    "status": item.status.value,
                    "assigned_to": item.assigned_to,
                    "created_at": item.created_at.isoformat(),
                    "due_date": item.due_date.isoformat(),
                    "is_overdue": item.is_overdue,
                    "description": item.description,
                    "remediation_steps": item.remediation_steps
                }
                for item in self.items
            ]
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
```

---

## 11. Referencias

### 11.1 Frameworks e Padroes

- **SOC 2 Type II**: AICPA Trust Service Criteria — https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2
- **PCI DSS v4.0**: PCI Security Standards Council — https://www.pcisecuritystandards.org/document_library/
- **GDPR**: European Commission — https://gdpr.eu/
- **LGPD (Lei 13.709/2018)**: Brasil — https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm
- **CIS Benchmarks**: Center for Internet Security — https://www.cisecurity.org/cis-benchmarks
- **OpenSCAP**: Open Source Compliance — https://www.open-scap.org/

### 11.2 Tools e Tecnologias

- **Open Policy Agent (OPA)**: https://www.openpolicyagent.org/
- **Kyverno**: https://kyverno.io/
- **HashiCorp Sentinel**: https://developer.hashicorp.com/sentinel
- **Trivy**: https://trivy.dev/
- **Semgrep**: https://semgrep.dev/
- **OpenSCAP**: https://www.open-scap.org/tools/

### 11.3 Casos de Estudo

- **GDPR Enforcement Cases**: European Data Protection Board — https://edpb.europa.eu/news/news_en
- **SolarWinds Incident Report**: CISA — https://www.cisa.gov/solarwinds
- **ANPD Decisions**: Autoridade Nacional de Protecao de Dados — https://www.gov.br/anpd/
- **Cloud Security Alliance**: https://cloudsecurityalliance.org/

### 11.4 Documentacao Adicional

- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework
- **ISO 27001**: https://www.iso.org/iso-27001-information-security.html
- **MITRE ATT&CK**: https://attack.mitre.org/
- **OWASP DevSecOps Guideline**: https://owasp.org/www-project-devsecops-guideline/
- **SLSA Framework**: https://slsa.dev/

---

*Compliance nao e opcional e nao e temporario. Automatize o que puder, audite o que nao puder automatizar, e nunca assuma que conformidade de ontem garante conformidade de amanha.*
