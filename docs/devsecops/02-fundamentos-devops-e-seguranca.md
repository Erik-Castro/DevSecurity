---
layout: default
title: "02-fundamentos-devops-e-seguranca"
---

# Capítulo 2 — Fundamentos de DevOps e Segurança

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Identificar e aplicar os pilares fundamentais do DevOps e como eles se conectam com práticas de segurança ao longo de todo o ciclo de vida do desenvolvimento de software.
2. Construir pipelines CI/CD seguras com portas de segurança em cada estágio, incluindo SAST, SCA, DAST, varredura de segredos e conformidade de licenças.
3. Implementar boas práticas de segurança em Docker, Kubernetes e Infrastructure as Code (IaC), reconhecendo os riscos específicos de cada tecnologia.
4. Analisar casos reais de incidentes de segurança em ferramentas de DevOps (Travis CI, GitHub Actions, Docker Hub, Terraform, Ansible) e extrair lições aplicáveis.
5. Configurar proteções de repositório Git — commits assinados, branch protection, CODEOWNERS e pre-commit hooks — para reduzir a superfície de ataque desde o primeiro commit.

---

## 1. DevOps: Conceitos Essenciais

DevOps é mais do que um conjunto de ferramentas — é uma cultura de colaboração entre desenvolvimento e operações que visa entregar valor de forma contínua e confiável. Quando incorporamos segurança desde o início, transformamos DevOps em DevSecOps.

### 1.1 Fundamentos de CI/CD

CI/CD (Integração Contínua / Entrega Contínua) é o coração do DevOps. Cada commit de código dispara automaticamente uma série de verificações que garantem que o software está funcionando, é performático e — quando adicionamos DevSecOps — seguro.

**O ciclo básico de CI/CD:**

```
Developer → Commit → Build → Test → Stage → Deploy → Monitor
    ↑                                                          |
    └──────────────── Feedback Loop ───────────────────────────┘
```

**Etapas típicas de um pipeline CI/CD moderno:**

| Etapa | Descrição | Ferramentas Comuns |
|-------|-----------|-------------------|
| Source | Controle de versão, branch strategy | Git, GitHub, GitLab |
| Build | Compilação, empacotamento | Maven, Gradle, npm, Docker |
| Test | Testes unitários, integração | JUnit, pytest, Jest |
| Security | Análise estática e dinâmica | SonarQube, Snyk, Trivy |
| Stage | Ambiente de homologação | Kubernetes, Terraform |
| Deploy | Entrega ao produção | ArgoCD, Helm, Ansible |
| Monitor | Observabilidade e alertas | Prometheus, Grafana, ELK |

### 1.2 Infrastructure as Code (IaC)

IaC permite gerenciar infraestrutura de forma declarativa e versionada. Em vez de configurar servidores manualmente, escrevemos código que descreve o estado desejado da infraestrutura.

**Exemplo básico de Terraform (IaC):**

```hcl
# main.tf - Provisions an EC2 instance
resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name        = "WebServer"
    Environment = "production"
  }

  vpc_security_group_ids = [aws_security_group.web_sg.id]
  subnet_id              = aws_subnet.public.id
}

resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Security group for web server"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

**Princípio da imutabilidade:** servidores devem ser descartáveis e recriados, nunca modificados in-place. Isso reduz drift de configuração e vulnerabilidades de estado.

### 1.3 Configuration Management

Configuration Management garante que todos os ambientes sejam idênticos e reproduzíveis. Ferramentas como Ansible, Chef e Puppet automatizam a configuração de servidores.

**Exemplo Ansible playbook:**

```yaml
# harden_server.yml
---
- name: Hardening do servidor web
  hosts: webservers
  become: yes
  vars:
    ssh_port: 2222
    allow_password_auth: no

  tasks:
    - name: Desabilitar login via senha SSH
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^#?PasswordAuthentication'
        line: 'PasswordAuthentication no'
      notify: restart sshd

    - name: Configurar porta SSH não padrão
      lineinfile:
        path: /etc/ssh/sshd_config
        regexp: '^#?Port'
        line: 'Port {{ ssh_port }}'
      notify: restart sshd

    - name: Instalar e configurar UFW
      ufw:
        state: enabled
        policy: deny
        rule: allow
        port: "{{ ssh_port }}"
        proto: tcp

    - name: Habilitar auto-updates de segurança
      apt:
        name: unattended-upgrades
        state: present

  handlers:
    - name: restart sshd
      service:
        name: sshd
        state: restarted
```

### 1.4 Containerização e Orquestramento

Containers empacotam aplicações com suas dependências, garantindo consistência entre ambientes. Docker é o padrão de mercado; Kubernetes orquestra milhares de containers em produção.

```bash
# Construção de imagem Docker
docker build -t meuapp:v1.0 .

# Execução com restrições de segurança
docker run --rm \
  --read-only \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --user 1000:1000 \
  -p 8080:8080 \
  meuapp:v1.0
```

### 1.5 Princípios do GitOps

GitOps usa o Git como a única fonte de verdade para infraestrutura e aplicações. Toda alteração passa por um pull request, revisão e aprovação antes de ser aplicada.

```
Git (Fonte da Verdade) → Controller (ArgoCD/Flux) → Cluster Kubernetes
         ↑                                                 |
         └──── Auto-sync / Drift Detection ────────────────┘
```

**Regras fundamentais do GitOps:**

- Todo o estado do sistema é declarativo (YAML, HCL, JSON).
- O versionamento é imutável — cada commit é um snapshot do estado.
- Mudanças são aprovadas via pull request, nunca manualmente.
- Agentes de reconciliação detectam e corrigem drift automaticamente.
- Rollback é trivial: basta reverter um commit.

### 1.6 Anatomia Completa de um Pipeline CI/CD

Um pipeline CI/CD maduro em DevSecOps inclui múltiplas camadas de verificação:

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE CI/CD SEGURO                     │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  SOURCE  │  BUILD   │   TEST   │  STAGE   │     DEPLOY      │
├──────────┼──────────┼──────────┼──────────┼─────────────────┤
│ • Commit │ • Compile│ • Unit   │ • Smoke  │ • Canary        │
│ • Lint   │ • SAST   │ • Integ  │ • DAST   │ • Blue/Green    │
│ • Secret │ • SCA    │ • E2E    │ • Fuzz   │ • Rolling       │
│   Scan   │ • Build  │ • Perf   │ • Manual │ • Approval      │
│ • Sign   │ • Image  │ • Sec    │   Gate   │   Gate          │
│   Check  │   Scan   │   Test   │          │ • Monitoring    │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

**Cada porta de segurança tem um propósito específico:**

1. **Secret Scanning**: impede que chaves, tokens e senhas entrem no repositório.
2. **SAST**: analisa o código-fonte procurando padrões vulneráveis sem executá-lo.
3. **SCA**: verifica dependências de terceiros contra bases de dados de CVEs.
4. **Container Scanning**: analisa imagens Docker para vulnerabilidades em camadas.
5. **DAST**: testa a aplicação em execução simulando ataques externos.
6. **Fuzz Testing**: envia entradas maliciosas e aleatórias para encontrar falhas.

---

## 2. Segurança em Cada Pilar do DevOps

DevSecOps significa incorporar segurança em todas as fases do ciclo de vida, não apenas no final. A seguir, exploramos como a segurança se manifesta em cada pilar do DevOps.

### 2.1 Plan — Threat Modeling no Planejamento

O threat modeling é o processo de identificar ameaças antes que o código seja escrito. Ferramentas como STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege) ajudam a sistematizar a análise.

**Exemplo de threat model simplificado:**

```markdown
## Threat Model: API de Pagamentos

| Ameaça | Ativo | STRIDE | Mitigação |
|--------|-------|--------|-----------|
| Injeção SQL na busca de pedidos | Database | Tampering | Prepared statements, ORM |
| Interceptação de dados de cartão | Rede | Info Disclosure | TLS 1.3, tokenização |
| Acesso não autorizado a pedidos | API | Spoofing | JWT + RBAC |
| DDoS na API pública | API | DoS | Rate limiting, WAF |
| Escalação de privilégio no admin | Admin Panel | Elevation | Validação server-side |
```

**Checklist de segurança no planejamento:**

- Quais dados sensíveis a aplicação manipula?
- Quais são os信任边界 (trust boundaries) do sistema?
- Quais APIs ficam expostas publicamente?
- Como o sistema falha? (fail-safe defaults)
- Quais são os requisitos de compliance (LGPD, PCI-DSS, SOC2)?

### 2.2 Code — Padrões de Código Seguro

A fase de codificação é onde vulnerabilidades são introduzidas — e onde são mais baratas de corrigir.

**Regras de codificação segura:**

1. Nunca concatene dados de entrada diretamente em consultas SQL.
2. Valide todas as entradas do usuário no lado do servidor.
3. Use bibliotecas criptográficas auditadas (não invente criptografia).
4. Implemente logging sem expor dados sensíveis.
5. Trate erros de forma que não revele informações internas.

**Exemplo de código vulnerável vs. seguro:**

```python
# VULNERAVEL — SQL Injection
def get_user_vulnerable(username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# SEGURO — Parameterized Query
def get_user_safe(username):
    query = "SELECT * FROM users WHERE username = %s"
    cursor.execute(query, (username,))
    return cursor.fetchone()

# VULNERAVEL — Sensitive data in logs
def process_payment(card_number, amount):
    logger.info(f"Processing payment for card {card_number} amount {amount}")
    # O número do cartão ficou registrado no log!

# SEGURO — Masked logging
def process_payment_safe(card_number, amount):
    masked = f"****-****-****-{card_number[-4:]}"
    logger.info(f"Processing payment for card {masked} amount {amount}")
```

### 2.3 Build — SAST e Dependency Scanning

Durante o build, ferramentas de análise estática (SAST) examinam o código sem executá-lo, procurando padrões conhecidos como vulneráveis.

**Configuração de SAST com SonarQube (sonar-project.properties):**

```properties
sonar.projectKey=myapp
sonar.sources=src
sonar.tests=tests
sonar.language=py
sonar.sourceEncoding=UTF-8

# Regras de qualidade de segurança
sonar.qualitygate.wait=true
sonar.qualitygate.timeout=300
```

**Dependency scanning com Snyk (exemplo CLI):**

```bash
# Verificar vulnerabilidades em dependências Node.js
snyk test --severity-threshold=high

# Monitorar o projeto continuamente
snyk monitor --file=package.json

# Verificar apenas dependências de produção
snyk test --production
```

### 2.4 Test — DAST e Penetration Testing

O DAST (Dynamic Application Security Testing) testa a aplicação em execução, simulando ataques externos.

**Configuração OWASP ZAP para DAST:**

```yaml
# zap-baseline.yml para GitHub Actions
name: OWASP ZAP Scan
on:
  schedule:
    - cron: '0 2 * * 1'  # Segunda-feira às 2h

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: 'https://staging.example.com'
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a'
```

**Estratégias de pentest em DevSecOps:**

- Pentest automatizado em staging antes de cada release.
- Bug bounty program para testes contínuos em produção.
- Red team exercises trimestrais para validar defesas.

### 2.5 Release — Approval Gates e Sign-off

A fase de release é a última barreira antes da produção. Deve exigir aprovação humana para mudanças críticas.

**Gate de aprovação exemplo (GitHub Actions):**

```yaml
deploy-production:
  needs: [security-scan, integration-tests]
  runs-on: ubuntu-latest
  environment:
    name: production
    url: https://app.example.com

  steps:
    - name: Checkout
      uses: actions/checkout@v4

    - name: Deploy to Production
      if: success()
      run: |
        echo "All security checks passed"
        echo "Deploying to production..."
        # deploy script here
```

**Critérios de aprovação para release:**

- Todos os testes automatizados passando (unitários, integração, E2E).
- Nenhuma vulnerabilidade crítica ou alta identificada.
- Scan de segredos limpo.
- License compliance verificado.
- Aprovação de pelo menos um membro da equipe de segurança.
- Change request aprovado (se aplicável).

### 2.6 Operate — Hardening e Configuração

Em operação, a segurança se concentra em hardening de sistemas, patch management e configuração segura.

**Checklist de hardening:**

- [ ] Sistema operacional atualizado com patches de segurança.
- [ ] Firewall configurado com regra padrão de negação.
- [ ] SSH configurado com chave pública apenas, sem senha.
- [ ] Fail2ban ativo para prevenir brute force.
- [ ] Auditoria de logs centralizada (SIEM).
- [ ] Backup criptografado e testado regularmente.
- [ ] Contas privilegiadas com MFA obrigatório.

### 2.7 Monitor — Feedback Loops

O monitoramento é o que fecha o ciclo de DevSecOps. Sem ele, não sabemos se as defesas estão funcionando.

**Componentes essenciais de observabilidade:**

- **Metrics**: Taxa de erros, latência, utilização de recursos, vulnerabilidades por severidade.
- **Logs**: Acesso, erros de aplicação, mudanças de configuração, tentativas de intrusão.
- **Traces**: Fluxo de requisições entre serviços para identificar gargalos e pontos de falha.

**Exemplo de dashboard de segurança (Prometheus + Grafana):**

{% raw %}
```yaml
# Métricas customizadas de segurança
groups:
  - name: security_metrics
    rules:
      - record: auth_failures_total
        expr: sum(rate(http_requests_total{status="401"}[5m])) by (source_ip)

      - alert: HighAuthFailureRate
        expr: auth_failures_total > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Alta taxa de falhas de autenticação"
          description: "IP {{ $labels.source_ip }} teve {{ $value }} falhas em 5 minutos"
```
{% endraw %}

---

## 3. Pipeline CI/CD: Anatomia Segura

### 3.1 Arquitetura de Pipeline Seguro

Uma pipeline segura não é apenas uma sequência de verificações — é uma arquitetura onde cada estágio protege o próximo.

```
┌─────────────────────────────────────────────────────────────────┐
│                   PIPELINE CI/CD SEGURO — FULL                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  COMMIT  │→ │  BUILD   │→ │  TEST    │→ │  DEPLOY  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │              │
│  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐       │
│  │ Pre-     │  │ SAST     │  │ DAST     │  │ Approval │       │
│  │ commit   │  │          │  │          │  │ Gate     │       │
│  │ hooks    │  │ SCA      │  │ Fuzz     │  │          │       │
│  │          │  │          │  │ Tests    │  │ Canary   │       │
│  │ Secret   │  │ Container│  │          │  │ Deploy   │       │
│  │ Scan     │  │ Scan     │  │ Pen Test │  │          │       │
│  │          │  │          │  │          │  │ Rollback │       │
│  │ Lint     │  │ License  │  │ Perf     │  │ Policy   │       │
│  │ Security │  │ Check    │  │ Tests    │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                  │
│  ═══════════════════════════════════════════════════════════════ │
│  │ FAIL = STOP │ QUALITY GATES │ AUDIT TRAIL │ ROLLBACK │     │
│  ═══════════════════════════════════════════════════════════════ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Portas de Segurança em Cada Estágio

**Regra fundamental: falha em qualquer verificação de segurança interrompe o pipeline.**

| Estágio | Verificação | Ferramenta | Ação em Falha |
|---------|------------|------------|---------------|
| Commit | Secret scanning | gitleaks, trufflehog | Bloquear commit |
| Commit | Lint de segurança | bandit, eslint-plugin-security | Bloquear commit |
| Build | SAST | SonarQube, Semgrep | Bloquear build |
| Build | SCA | Snyk, Dependabot | Bloquear se crítico |
| Build | Container scan | Trivy, Grype | Bloquear imagem |
| Build | License check | license-checker | Alerta (não bloqueia) |
| Test | DAST | OWASP ZAP | Bloquear release |
| Test | Fuzz testing | AFL, Jazzer | Alerta |
| Stage | Pen test | Nuclei, Nmap | Bloquear deploy |
| Deploy | Approval gate | GitHub Environments | Bloquear deploy |
| Operate | Runtime monitoring | Falco, Wazuh | Alerta + auto-response |

### 3.3 Políticas de Build com Falha

```yaml
# Exemplo de política de qualidade (quality-gate.json)
{
  "qualityGate": {
    "name": "Security Gate",
    "conditions": [
      {
        "metric": "new_security_hotspots",
        "operator": "LESS_THAN",
        "value": 0
      },
      {
        "metric": "new_vulnerabilities",
        "operator": "LESS_THAN",
        "value": 0
      },
      {
        "metric": "new_coverage",
        "operator": "GREATER_THAN",
        "value": 80
      }
    ]
  }
}
```

### 3.4 Pipeline Completa com GitHub Actions

A seguir, uma pipeline completa que incorpora todas as verificações de segurança:

{% raw %}
```yaml
# .github/workflows/security-pipeline.yml
name: Security Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write
  actions: read
  id-token: write

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─────────────────────────────────────────────
  # ESTÁGIO 1: Linting e Validação de Código
  # ─────────────────────────────────────────────
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install ruff bandit safety

      - name: Ruff lint
        run: ruff check src/

      - name: Bandit security lint
        run: bandit -r src/ -f json -o bandit-report.json || true

      - name: Check Bandit results
        run: |
          CRITICAL=$(python3 -c "
          import json
          with open('bandit-report.json') as f:
              data = json.load(f)
          issues = [r for r in data.get('results', []) if r['issue_severity'] == 'HIGH']
          print(len(issues))
          ")
          if [ "$CRITICAL" -gt 0 ]; then
            echo "ERROR: Found $CRITICAL high-severity security issues"
            cat bandit-report.json
            exit 1
          fi

  # ─────────────────────────────────────────────
  # ESTÁGIO 2: SAST (Static Application Security Testing)
  # ─────────────────────────────────────────────
  sast:
    name: SAST Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Semgrep Scan
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit p/python
          generateSarif: true
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: semgrep.sarif

  # ─────────────────────────────────────────────
  # ESTÁGIO 3: SCA (Software Composition Analysis)
  # ─────────────────────────────────────────────
  sca:
    name: Dependency Vulnerability Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Safety Check
        run: |
          pip install safety
          safety check --output json > safety-report.json || true
          CRITICAL=$(python3 -c "
          import json
          with open('safety-report.json') as f:
              data = json.load(f)
          vulns = [v for v in data if v.get('severity') == 'critical']
          print(len(vulns))
          ")
          if [ "$CRITICAL" -gt 0 ]; then
            echo "ERROR: Found $CRITICAL critical dependency vulnerabilities"
            exit 1
          fi

      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  # ─────────────────────────────────────────────
  # ESTÁGIO 4: Secret Scanning
  # ─────────────────────────────────────────────
  secret-scan:
    name: Secret Scanning
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: TruffleHog scan
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

  # ─────────────────────────────────────────────
  # ESTÁGIO 5: License Compliance
  # ─────────────────────────────────────────────
  license-check:
    name: License Compliance
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install pip-licenses
          pip install -r requirements.txt

      - name: Check licenses
        run: |
          pip-licenses --format=json --output-file=licenses.json
          FORBIDDEN=$(python3 -c "
          import json
          FORBIDDEN_LICENSES = ['GPL-3.0', 'AGPL-3.0', 'SSPL-1.0']
          with open('licenses.json') as f:
              licenses = json.load(f)
          violations = [l for l in licenses if l.get('License') in FORBIDDEN_LICENSES]
          for v in violations:
              print(f\"FORBIDDEN: {v['Name']} uses {v['License']}\")
          print(len(violations))
          " | tail -1)
          if [ "$FORBIDDEN" -gt 0 ]; then
            echo "ERROR: Found forbidden licenses"
            exit 1
          fi

  # ─────────────────────────────────────────────
  # ESTÁGIO 6: Container Build e Scan
  # ─────────────────────────────────────────────
  container-scan:
    name: Container Security Scan
    runs-on: ubuntu-latest
    needs: [lint, sast, sca, secret-scan]
    permissions:
      contents: read
      packages: write
      security-events: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Trivy image scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  # ─────────────────────────────────────────────
  # ESTÁGIO 7: Testes de Integração
  # ─────────────────────────────────────────────
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [lint, sast, sca, secret-scan]
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
        run: |
          pytest tests/integration/ \
            --cov=src \
            --cov-report=xml \
            --junitxml=results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: results.xml

  # ─────────────────────────────────────────────
  # ESTÁGIO 8: DAST (Dynamic Application Security Testing)
  # ─────────────────────────────────────────────
  dast:
    name: DAST Scan
    runs-on: ubuntu-latest
    needs: [integration-tests]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build and start application
        run: |
          docker compose -f docker-compose.staging.yml up -d
          sleep 30
          curl -f http://localhost:8000/health || exit 1

      - name: OWASP ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: 'http://localhost:8000'
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a -j'
          allow_issue_writing: false

      - name: Cleanup
        if: always()
        run: docker compose -f docker-compose.staging.yml down

  # ─────────────────────────────────────────────
  # ESTÁGIO 9: Deploy com Approval Gate
  # ─────────────────────────────────────────────
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [container-scan, integration-tests, dast]
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          echo "Deploying to staging environment"
          # Deploy script here

      - name: Smoke tests
        run: |
          curl -f https://staging.example.com/health
          curl -f https://staging.example.com/api/v1/status

  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    environment:
      name: production
      url: https://app.example.com
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          echo "Deploying to production environment"
          # Deploy script here

      - name: Post-deploy verification
        run: |
          curl -f https://app.example.com/health
          curl -f https://app.example.com/api/v1/status
```
{% endraw %}

---

## 4. Git: Segurança no Controle de Versão

O Git é a base de todo o fluxo de trabalho DevOps. Proteger o repositório Git é proteger a cadeia de confiança inteira.

### 4.1 Commits Assinados (GPG/SSH)

Commits assinados garantem que a pessoa que fez o commit é realmente quem diz ser. Isso previne impersonação e garante rastreabilidade.

```bash
# Configurar GPG key para commits
git config --global user.signingkey ABCDEF1234567890
git config --global commit.gpgsign true
git config --global gpg.program gpg2

# Verificar assinatura de um commit
git log --show-signature -1

# Criar commit assinado
git commit -S -m "feat: add authentication module"

# Assinar tags
git tag -s v1.0.0 -m "Release version 1.0.0"
git tag -v v1.0.0  # Verificar assinatura da tag
```

**Usando SSH para assinatura (Git 2.34+):**

```bash
# Configurar SSH como programa de assinatura
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub

# Adicionar chave de assinatura confiável
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

### 4.2 Branch Protection Rules

Branch protection impede que commits diretos na branch principal sem passar por revisão e verificações automáticas.

**Configuração via GitHub CLI:**

```bash
# Habilitar branch protection na branch main
gh api repos/{owner}/{repo}/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["lint","sast","sca","secret-scan","integration-tests"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  --field restrictions=null \
  --field allow_force_pushes=false \
  --field allow_deletions=false
```

**Configuração manual (GitHub UI):**

| Regra | Configuração Recomendada |
|-------|------------------------|
| Require pull request | Ativado, 2 approving reviews |
| Dismiss stale reviews | Ativado |
| Require review from code owners | Ativado |
| Require status checks | lint, sast, sca, secret-scan |
| Require branches to be up to date | Ativado |
| Require conversation resolution | Ativado |
| Require signed commits | Ativado |
| Require linear history | Ativado (merge/squash only) |
| Require force pushes | Desativado |
| Require admin compliance | Ativado |
| Include administrators | Ativado |

### 4.3 Arquivo CODEOWNERS

O arquivo CODEOWNERS define quem é responsável por revisar alterações em partes específicas do código.

```
# .github/CODEOWNERS
# Global
* @equipe-dev @equipe-seguranca

# Infraestrutura
/terraform/ @equipe-infra
/docker/ @equipe-infra
/kubernetes/ @equipe-infra

# Segurança
/.github/workflows/ @equipe-seguranca
/security/ @equipe-seguranca

# API
/src/api/ @equipe-api
/tests/api/ @equipe-api

# Documentação
/docs/ @equipe-docs

# Dependências
/package.json @equipe-dev @equipe-seguranca
/requirements.txt @equipe-dev @equipe-seguranca
```

### 4.4 Pre-commit Hooks para Segurança

Pre-commit hooks executam verificações automaticamente antes de cada commit, impedindo que código inseguro entre no repositório.

**.pre-commit-config.yaml completo:**

```yaml
# .pre-commit-config.yaml
repos:
  # ── Varredura de segredos ──
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  # ── Lint de segurança Python ──
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']
        additional_dependencies: ['bandit[toml]']

  # ── Lint geral ──
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: ['--fix']

  # ── Validação de arquivos de configuração ──
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 0.27.0
    hooks:
      - id: check-github-actions
      - id: check-github-workflows

  # ── Validação de Dockerfile ──
  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint

  # ── Verificação de arquivos sensíveis ──
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-merge-conflict
      - id: detect-private-key
      - id: check-yaml
      - id: check-toml
      - id: no-commit-to-branch
        args: ['--branch', 'main', '--branch', 'master']

  # ── Validação de Terraform ──
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.83.5
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_security
```

**Configuração do Bandit (pyproject.toml):**

```toml
# pyproject.toml - Bandit configuration
[tool.bandit]
exclude_dirs = ["tests", "venv"]
skips = ["B101"]  # Skip assert warnings
```

### 4.5 Configurações de Segurança do Repositório GitHub

Além das branch protection rules, configure estas opções de segurança no repositório:

**Configurações gerais:**

- Vulnerability alerts: Ativado
- Dependency graph: Ativado
- Dependabot alerts: Ativado
- Dependabot security updates: Ativado
- Code scanning: Ativado (CodeQL)
- Secret scanning: Ativado
- Push protection: Ativado

**Configurações de fork:**

- Allow fork pulling: Conforme necessidade
- Restrict who can push to forks: Ativado
- Code review required for co-authors: Ativado

```bash
# Habilitar secret scanning via CLI
gh api repos/{owner}/{repo}/private-vulnerability-reporting \
  --method PUT

# Habilitar Dependabot
gh api repos/{owner}/{repo}/vulnerability-alerts \
  --method PUT

# Habilitar auto-merge para PRs aprovados
gh api repos/{owner}/{repo}/auto-merge \
  --method PUT \
  --field enabled=true
```

---

## 5. Docker: Fundamentos de Segurança

### 5.1 Melhores Práticas de Dockerfile

O Dockerfile define como a imagem é construída. Cada decisão aqui afeta a superfície de ataque da aplicação.

**Regras de segurança para Dockerfile:**

1. Use imagens base minimalistas (Alpine, distroless).
2. Nunca execute como root.
3. Use multi-stage builds para reduzir tamanho e superfície de ataque.
4. Fixe versões de imagens base (não use `latest`).
5. Não inclua secrets no build.
6. Use `.dockerignore` para excluir arquivos sensíveis.

**Exemplo de Dockerfile inseguro vs. seguro:**

```dockerfile
# INSEGURO — Não faça isso
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8080
CMD ["python", "app.py"]

# Problemas:
# 1. Imagem base muito grande (milhares deMB)
# 2. Roda como root
# 3. Copia TUDO (incluindo .git, .env, etc)
# 4. Não usa multi-stage build
# 5. Não há healthcheck
```

### 5.2 Image Layering e Segurança

Cada instrução Dockerfile cria uma camada (layer). Camadas são cached e compartilhadas. Isso tem implicações de segurança:

- Secrets em uma camada podem ser recuperados de camadas anteriores.
- Camadas maiores significam imagens maiores e mais superfície de ataque.
- Reordenar instruções pode melhorar cache e reduzir tamanhos.

**Estratégia de layering segura:**

```dockerfile
# Primeiro: dependências do sistema (muda raramente)
FROM python:3.12-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Segundo: dependências Python (muda quando requirements.txt muda)
FROM base AS deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Terceiro: código da aplicação (muda frequentemente)
FROM deps AS runtime
COPY src/ ./src/
COPY config/ ./config/

# Criar usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "-m", "src.main"]
```

### 5.3 Containers Não-Root

Executar containers como root é o erro mais comum e mais perigoso. Um container root pode escalar privilégios para o host.

```dockerfile
# Criar usuário não-root
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -g appgroup -u 1001 -d /app -s /sbin/nologin appuser

# Transferir propriedade dos arquivos
COPY --chown=appuser:appgroup . /app/

WORKDIR /app
USER appuser

# Configurações adicionais de segurança
# Não usar capabilities perigosas
# Não montar volumes sensíveis
# Não expor portas desnecessárias
```

**Restrições de execução:**

```bash
# Executar com restrições mínimas de privilégio
docker run --rm \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --security-opt no-new-privileges \
  --security-opt seccomp=default \
  --pids-limit 100 \
  --memory 256m \
  --cpus 0.5 \
  meuapp:latest
```

### 5.4 Filesystem Somente Leitura

Containers com filesystem somente leitura previnem que atacantes escrevam malware ou modifiquem configurações.

```dockerfile
# Dockerfile com filesystem somente leitura
FROM python:3.12-slim AS runtime

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Criar diretório para dados temporários (writable)
RUN mkdir -p /tmp/app-data && \
    chown -R appuser:appuser /tmp/app-data

COPY --chown=appuser:appgroup . /app/

# Usuário não-root
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -g appgroup -u 1001 -d /app -s /sbin/nologin appuser

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "src.main"]
```

### 5.5 Dockerfile Hardened Completo para Aplicação Python

```dockerfile
# ============================================================
# STAGE 1: Builder
# ============================================================
FROM python:3.12-slim AS builder

# Instalar dependências de compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Instalar dependências em ambiente isolado
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# STAGE 2: Runtime
# ============================================================
FROM python:3.12-slim AS runtime

# Metadados da imagem
LABEL maintainer="equipe-seguranca@example.com"
LABEL security.scan="trivy"
LABEL version="1.0"

# Instalar apenas dependências de runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar dependências do builder
COPY --from=builder /install /usr/local

# Criar usuário não-root
RUN groupadd -r -g 1001 appgroup && \
    useradd -r -g appgroup -u 1001 -d /app -s /sbin/nologin appuser

# Criar diretórios necessários
RUN mkdir -p /app /tmp/app-data /var/log/app && \
    chown -R appuser:appgroup /app /tmp/app-data /var/log/app

WORKDIR /app

# Copiar código da aplicação
COPY --chown=appuser:appgroup src/ ./src/
COPY --chown=appuser:appgroup config/ ./config/

# Remover arquivos desnecessários
RUN find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null; \
    find /app -name "*.pyc" -delete 2>/dev/null; \
    true

# Configurar variáveis de ambiente seguras
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    APP_HOME=/app \
    APP_USER=appuser

# Trocar para usuário não-root
USER appuser

# Expôr porta não-privilegiada
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Usar tini como PID 1 para signal handling correto
ENTRYPOINT ["tini", "--"]

CMD ["python", "-m", "src.main"]
```

### 5.6 docker-compose.yml com Restrições de Segurança

```yaml
# docker-compose.yml — Produção segura
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    image: meuapp:latest
    container_name: meuapp
    restart: unless-stopped

    # ── Restrições de segurança ──
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=64m
    security_opt:
      - no-new-privileges:true
      - seccomp:default
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE

    # ── Limites de recursos ──
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M
    pids_limit: 200

    # ── Rede ──
    networks:
      - frontend
      - backend

    # ── Variáveis de ambiente (via secrets, não inline) ──
    environment:
      - APP_ENV=production
      - LOG_LEVEL=info
    secrets:
      - db_password
      - api_key

    # ── Healthcheck ──
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

    # ── Logs ──
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  db:
    image: postgres:16-alpine
    container_name: meuapp-db
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp:rw,noexec,nosuid,size=64m
      - /var/run/postgresql:rw,noexec,nosuid,size=64m
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
    networks:
      - backend
    secrets:
      - db_password
    environment:
      POSTGRES_DB: meuapp
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

# ── Rede ──
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # Sem acesso externo

# ── Volumes ──
volumes:
  pgdata:
    driver: local

# ── Secrets ──
secrets:
  db_password:
    file: ./secrets/db_password.txt
  api_key:
    file: ./secrets/api_key.txt
```

### 5.7 Image Scanning com Trivy

Trivy é uma ferramenta de扫描 de vulnerabilidades para imagens Docker, filesystems e repositórios Git.

```bash
# Instalar Trivy
sudo apt-get install trivy

# Escanear imagem local
trivy image meuapp:latest

# Escanear com severidade mínima
trivy image --severity HIGH,CRITICAL meuapp:latest

# Escanear com formato JSON para integração
trivy image --format json --output trivy-results.json meuapp:latest

# Escanear diretório (Dockerfile)
trivy config --severity HIGH,CRITICAL .

# Escanear IaC (Terraform, Kubernetes)
trivy config --severity HIGH,CRITICAL ./terraform/

# Modo CI — falha se encontrar vulnerabilidades CRITICAL
trivy image --exit-code 1 --severity CRITICAL meuapp:latest

# Ignorar CVEs conhecidos (com justificativa)
trivy image --ignorefile .trivyignore meuapp:latest
```

**Arquivo .trivyignore para ignorar CVEs aceitos:**

```
# CVE-2023-XXXXX — Vulnerabilidade mitigada via WAF
# Ajuste em: 2024-01-15
# Owner: @equipe-seguranca
# Review: 2024-07-15
CVE-2023-12345
```

---

## 6. Kubernetes: Fundamentos de Segurança

### 6.1 Pod Security Standards

Kubernetes define três níveis de segurança para Pods: Privileged, Baseline e Restricted.

```yaml
# Namespace com Pod Security Standards
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Níveis de segurança:**

| Nível | Descrição | Uso Recomendado |
|-------|-----------|-----------------|
| Privileged | Sem restrições | Sistema (monitoramento, logging) |
| Baseline | Restrições mínimas | Desenvolvimento |
| Restricted | Restrições máximas | Produção |

### 6.2 Network Policies

Network Policies controlam o tráfego entre Pods, implementando o princípio de menor privilégio na rede.

```yaml
# Negar todo tráfego por padrão no namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

---
# Permitir tráfego apenas entre Pods com labels específicas
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-backend
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: backend
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: frontend
      ports:
        - protocol: TCP
          port: 8080

---
# Permitir backend acessar banco de dados
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-to-db
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: database
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: backend
      ports:
        - protocol: TCP
          port: 5432
```

### 6.3 RBAC (Role-Based Access Control)

RBAC define quem pode fazer o quê no cluster Kubernetes.

```yaml
# Role com permissões mínimas
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: app-deployer
rules:
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods", "services"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["pods/log"]
    verbs: ["get"]

---
# ServiceAccount associado à Role
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-deployer
  namespace: production

---
# Binding
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-deployer-binding
  namespace: production
subjects:
  - kind: ServiceAccount
    name: app-deployer
    namespace: production
roleRef:
  kind: Role
  name: app-deployer
  apiGroup: rbac.authorization.k8s.io
```

### 6.4 Secret Management

Kubernetes Secrets são base64, NÃO criptografados por padrão. Para produção, useExternal Secrets Operator ou Vault.

```yaml
# Secret via External Secrets Operator
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-password
      remoteRef:
        key: secret/data/production/db
        property: password
    - secretKey: api-key
      remoteRef:
        key: secret/data/production/api
        property: key

---
# Usando os Secrets no Pod
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: app-deployer
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        runAsGroup: 1001
        fsGroup: 1001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: meuapp:latest
          ports:
            - containerPort: 8080
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: db-password
            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: api-key
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 128Mi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 20
```

### 6.5 Security Context Completo

```yaml
# Security Context completo para Pod e Container
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: production
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001
    fsGroupChangePolicy: OnRootMismatch
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: meuapp:latest
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        runAsNonRoot: true
        runAsUser: 1001
        capabilities:
          drop:
            - ALL
        procMount: Default
      volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: app-cache
          mountPath: /app/cache
  volumes:
    - name: tmp
      emptyDir:
        medium: Memory
        sizeLimit: 64Mi
    - name: app-cache
      emptyDir:
        sizeLimit: 100Mi
```

---

## 7. Infrastructure as Code Seguro

### 7.1 Fundamentos de Segurança Terraform

Terraform gerencia infraestrutura de forma declarativa. Erros de segurança no Terraform podem expor recursos inteiros na nuvem.

```hcl
# Segurança básica em Terraform

# 1. Usar variáveis para valores sensíveis (nunca hardcode)
variable "db_password" {
  type      = string
  sensitive = true
}

# 2. Usar remote state com criptografia
terraform {
  backend "s3" {
    bucket         = "my-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}

# 3. Versionar providers
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

### 7.2 Segurança de State Files

O state file do Terraform contém toda a infraestrutura, incluindo secrets. Protegê-lo é crítico.

```bash
# Habilitar versionamento no S3 bucket do state
aws s3api put-bucket-versioning \
  --bucket my-terraform-state \
  --versioning-configuration Status=Enabled

# Habilitar criptografia SSE-S3
aws s3api put-bucket-encryption \
  --bucket my-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "alias/terraform-state"
      }
    }]
  }'

# Bloquear acesso público
aws s3api put-public-access-block \
  --bucket my-terraform-state \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,\
    BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### 7.3 Segurança de Módulos

```hcl
# Módulo de VPC com segurança embutida
# modules/vpc/main.tf

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "enable_flow_logs" {
  type    = bool
  default = true
}

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "production-vpc"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# Flow Logs para auditoria
resource "aws_flow_log" "vpc_flow_log" {
  count                = var.enable_flow_logs ? 1 : 0
  vpc_id               = aws_vpc.main.id
  traffic_type         = "ALL"
  iam_role_arn         = aws_iam_role.flow_log_role[0].arn
  log_destination      = aws_cloudwatch_log_group.flow_log[0].arn
  log_destination_type = "cloud-watch-logs"
}

resource "aws_cloudwatch_log_group" "flow_log" {
  count             = var.enable_flow_logs ? 1 : 0
  name              = "/aws/vpc/flow-log/${aws_vpc.main.id}"
  retention_in_days = 90
  kms_key_id        = aws_kms_key.flow_log[0].arn
}

# Security Group com regras restritivas
resource "aws_security_group" "restricted" {
  name        = "restricted-sg"
  description = "Security group with minimal access"
  vpc_id      = aws_vpc.main.id

  # Sem regras de entrada por padrão (deny all)
  # Sem regras de saída por padrão

  tags = {
    Name = "restricted-sg"
  }
}
```

### 7.4 Terraform com Segurança Completa

```hcl
# main.tf — Configuração Terraform segura completa

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "company-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Security    = "enabled"
    }
  }
}

# ── Variáveis com validação ──

variable "aws_region" {
  type    = string
  default = "us-east-1"

  validation {
    condition     = can(regex("^us-east-1$", var.aws_region))
    error_message = "Apenas us-east-1 é permitido neste ambiente."
  }
}

variable "environment" {
  type    = string
  default = "production"

  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Ambiente deve ser production ou staging."
  }
}

variable "db_password" {
  type      = string
  sensitive = true

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "Senha do banco deve ter pelo menos 16 caracteres."
  }
}

# ── KMS Key para criptografia ──

resource "aws_kms_key" "main" {
  description             = "KMS key for encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "production-kms-key"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/production-key"
  target_key_id = aws_kms_key.main.key_id
}

# ── VPC Segura ──

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "production-vpc"
  }
}

# ── Security Group com regras mínimas ──

resource "aws_security_group" "app" {
  name        = "app-sg"
  description = "Security group for application"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "HTTPS from ALB only"
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound"
  }

  egress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.db.id]
    description     = "PostgreSQL to database"
  }

  tags = {
    Name = "app-sg"
  }
}

# ── RDS com criptografia ──

resource "aws_db_instance" "main" {
  identifier     = "production-db"
  engine         = "postgres"
  engine_version = "16.1"
  instance_class = "db.t3.medium"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  kms_key_id           = aws_kms_key.main.arn

  db_name  = "production"
  username = "dbadmin"
  password = var.db_password

  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  backup_retention_period = 30
  backup_window           = "03:00-04:00"
  maintenance_window      = "Mon:04:00-Mon:05:00"

  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "production-db-final"

  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.main.arn
  monitoring_interval             = 60
  monitoring_role_arn            = aws_iam_role.rds_monitoring.arn

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Name = "production-db"
  }
}
```

### 7.5 Checkov para Verificação de IaC

```bash
# Instalar Checkov
pip install checkov

# Escanear diretório Terraform
checkov -d ./terraform --framework terraform

# Escanear apenas verificações de alta severidade
checkov -d ./terraform --check HIGH

# Escanear com output em JSON
checkov -d ./terraform --output json --output-file checkov-results.json

# Escanear Dockerfile
checkov -f Dockerfile

# Ignorar check específico com justificativa
checkov -d ./terraform --skip-check CKV_AWS_18

# CI/CD — falhar se encontrar issues
checkov -d ./terraform --hard-fail-on HIGH,CRITICAL --compact
```

**Exemplo de Checkov bypass documentado:**

```hcl
# checkov:skip=CKV_AWS_145:Using KMS key for encryption is configured
# checkov:skip=CKV_AWS_119:RDS encryption handled at module level
resource "aws_db_instance" "main" {
  # ... configuração segura ...
}
```

---

## 8. Exercício Prático

### 8.1 Problema: Pipeline Insegura

Analise a pipeline abaixo e identifique TODOS os problemas de segurança:

```yaml
# .github/workflows/insecure-pipeline.yml
name: Insecure Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/

      - name: Build
        run: python setup.py sdist

      - name: Build Docker image
        run: docker build -t myapp:latest .

      - name: Push to Docker Hub
        run: |
          docker login -u ${{ secrets.DOCKER_USER }} -p ${{ secrets.DOCKER_PASS }}
          docker push myapp:latest

      - name: Deploy
        env:
          SSH_KEY: ${{ secrets.SSH_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          echo "$SSH_KEY" > /tmp/key
          chmod 600 /tmp/key
          scp -i /tmp/key dist/*.tar.gz user@server:/app/
          ssh -i /tmp/key user@server "cd /app && pip install *.tar.gz && systemctl restart app"
```

**Problemas identificados:**

| # | Problema | Risco | Solução |
|---|---------|-------|---------|
| 1 | Sem linting de código | Bugs e vulnerabilidades passam despercebidos | Adicionar ruff, bandit |
| 2 | Sem SAST | Vulnerabilidades no código não detectadas | Adicionar Semgrep/SonarQube |
| 3 | Sem SCA/dependency scan | Dependências vulneráveis em produção | Adicionar Snyk/safety |
| 4 | Sem secret scanning | Secrets podem vazar para o repositório | Adicionar gitleaks |
| 5 | Docker build sem scan | Imagens com vulnerabilidades em produção | Adicionar Trivy scan |
| 6 | Docker login inline | Credentials expostas em logs | Usar registry credentials configurado |
| 7 | Sem branch protection | Qualquer pessoa pode fazer push direto | Configurar branch protection |
| 8 | Deploy sem approval gate | Deploy automático sem revisão humana | Adicionar environment protection |
| 9 | SSH key no ambiente | Chave SSH exposta em logs do step | Usar SSH agent ou deploy key |
| 10 | Sem rollback strategy | Falha no deploy não tem recuperação | Implementar blue/green ou canary |
| 11 | actions/checkout@v3 desatualizado | Versão antiga pode ter vulnerabilidades | Usar actions/checkout@v4 |
| 12 | actions/setup-python@v4 desatualizado | Versão antiga pode ter vulnerabilidades | Usar actions/setup-python@v5 |

### 8.2 Solução: Pipeline Corrigida

```yaml
# .github/workflows/secure-pipeline.yml
name: Secure Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write
  packages: write

jobs:
  # ── ESTÁGIO 1: Validação e Linting ──
  validate:
    name: Validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install linting tools
        run: pip install ruff bandit safety

      - name: Ruff lint
        run: ruff check src/

      - name: Bandit security lint
        run: bandit -r src/ -f json

      - name: Safety dependency check
        run: safety check --output json

  # ── ESTÁGIO 2: SAST ──
  sast:
    name: Static Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: p/security-audit p/python

  # ── ESTÁGIO 3: Secret Scanning ──
  secrets:
    name: Secret Scanning
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # ── ESTÁGIO 4: Testes ──
  test:
    name: Tests
    runs-on: ubuntu-latest
    needs: [validate]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml

  # ── ESTÁGIO 5: Container Build + Scan ──
  container:
    name: Container Security
    runs-on: ubuntu-latest
    needs: [validate, sast, secrets, test]
    permissions:
      packages: write
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/setup-buildx-action@v3

      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Trivy image scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  # ── ESTÁGIO 6: Deploy Seguro ──
  deploy-staging:
    name: Deploy Staging
    runs-on: ubuntu-latest
    needs: [container]
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying to staging"

  deploy-production:
    name: Deploy Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    environment:
      name: production
      url: https://app.example.com
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying to production"
```

---

## 9. Referências

### 9.1 Documentação Oficial

- **OWASP DevSecOps Guideline**: https://owasp.org/www-project-devsecops-guideline/
- **NIST SP 800-218 (SSDF)**: https://csrc.nist.gov/publications/detail/sp/800-218/final
- **CIS Benchmarks**: https://www.cisecurity.org/cis-benchmarks
- **Docker Security Best Practices**: https://docs.docker.com/engine/security/
- **Kubernetes Security Checklist**: https://kubernetes.io/docs/concepts/security/
- **Terraform Security Best Practices**: https://developer.hashicorp.com/terraform/cloud-docs/recommended-practices/part3

### 9.2 Ferramentas

| Categoria | Ferramenta | Uso |
|-----------|-----------|-----|
| SAST | Semgrep, SonarQube, Bandit | Análise estática de código |
| SCA | Snyk, Dependabot, Safety | Análise de dependências |
| DAST | OWASP ZAP, Nuclei | Análise dinâmica |
| Secret Scanning | Gitleaks, TruffleHog | Detecção de segredos |
| Container Scan | Trivy, Grype, Snyk Container | Scan de imagens |
| IaC Scan | Checkov, tfsec, KICS | Scan de infraestrutura |
| Runtime | Falco, Wazuh | Monitoramento em runtime |
| RBAC | OPA/Gatekeeper, Kyverno | Políticas de segurança |

### 9.3 Casos Documentados de Incidentes

#### Travis CI — Exposure of Secrets (2021)

Em 2021, pesquisadores descobriram que o Travis CI expunha variáveis de ambiente (incluindo chaves de API, tokens de acesso e credenciais de deploy) para forks de repositórios públicos. O problema afetou milhares de projetos open source que usavam Travis CI.

**Lições aprendidas:**
- Nunca armazene secrets em variáveis de ambiente de ferramentas de CI sem restrição de acesso.
- Use ferramentas de CI que suportam proteção de secrets em forks (GitHub Actions com `pull_request_target` tem restrições semelhantes).
- Implemente secret scanning em todos os repositórios.
- Revogue e rotacione secrets regularmente.

**Como mitigar em GitHub Actions:**

```yaml
# NUNCA faça isso — expõe secrets para PRs de forks
on:
  pull_request_target

# Em vez disso, use:
on:
  pull_request
  # Pull requests de forks NÃO recebem secrets

# Se precisar de secrets em PRs, use workflow_run:
on:
  workflow_run:
    workflows: ["PR Validation"]
    types: [completed]
```

#### GitHub Actions — Workflow Injection Attacks

Vulnerabilidades de injeção em GitHub Actions permitem que atacantes manipulem workflows para executar código arbitrário. Um caso comum é o uso inseguro de `${{ github.event.pull_request.title }}` em run steps:

```yaml
# VULNERAVEL — Injeção via pull request title
- name: Process PR
  run: |
    echo "Processing: ${{ github.event.pull_request.title }}"
    # Um título como "test\nmalicious command" executa o comando

# SEGURO — Usar variável de ambiente
- name: Process PR
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  run: |
    echo "Processing: $PR_TITLE"
    # Variáveis de ambiente são sanitizadas
```

**Padrões de ataque documentados:**

- **Script injection**: Usar contextos do GitHub em `run` steps sem sanitização.
- **Poisoned pipeline execution (PPE)**: Atacantes modificam arquivos do repositório que o workflow usa.
- **Exfiltration**: Workflows que leem secrets e os enviam para servidores externos.

**Proteções:**

```yaml
# Usar permissões mínimas
permissions:
  contents: read
  # Não adicionar write desnecessário

# Usar GITHUB_TOKEN com escopo mínimo
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.GITHUB_TOKEN }}

# Evitar pull_request_target com checkout do PR
# Se necessário, usar:
on:
  pull_request_target
steps:
  - uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }}
      # NUNCA use ref: ${{ github.event.pull_request.head.ref }}
```

#### Docker Hub — Cryptographic Mining Images

Pesquisadores descobriram centenas de imagens no Docker Hub que continham software de mineração de criptomoedas oculto. Essas imagens eram oferecidas como "imagens oficiais" ou "imagens otimizadas" de software popular.

**Exemplos documentados:**
- Imagens "nginx" maliciosas que executavam mineros em background.
- Imagens "python" com código de mineração embutido nas camadas.
- Imagens que baixavam e executavam mineros após o container iniciar.

**Proteções:**

```bash
# 1. Use imagens oficiais verificadas
docker pull python:3.12-slim  # Oficial, verified
docker pull random-user/python-custom  # RISCO

# 2. Verifique assinaturas de imagens
docker trust inspect --pretty python:3.12-slim

# 3. Escaneie antes de usar
trivy image python:3.12-slim

# 4. Use Docker Content Trust
export DOCKER_CONTENT_TRUST=1
docker pull python:3.12-slim  # Só baixa imagens assinadas

# 5. Use .dockerignore para não expor secrets durante build
echo ".env\n*.key\n*.pem" > .dockerignore
```

#### Terraform State File Exposure

Diversos incidentes foram documentados onde state files do Terraform foram expostos publicamente em buckets S3, revelando secrets como senhas de banco de dados, chaves de API e credenciais de cloud providers.

**Causa raiz:** Buckets S3 sem bloqueio de acesso público + state files sem criptografia.

**Proteções:**

```hcl
# 1. Habilitar criptografia no state
terraform {
  backend "s3" {
    bucket  = "terraform-state"
    key     = "prod/terraform.tfstate"
    encrypt = true  # Obrigatório
  }
}

# 2. Bloquear acesso público no bucket
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 3. Habilitar versionamento para recovery
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 4. Configurar lifecycle para retenção
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}
```

#### Ansible — Misconfiguration Vulnerabilities

Playbooks do Ansible frequentemente contêm configurações inseguras que podem ser exploradas. Casos documentados incluem:

- Playbooks com `become: yes` sem restrições, executando comandos arbitrários como root.
- Variáveis de senha em texto plano em playbooks versionados.
- Módulos `command`/`shell` com variáveis não sanitizadas (injeção de comandos).
- Factories de vault sem rotação de chaves.

**Exemplo inseguro vs. seguro:**

```yaml
# INSEGURO — Senha em texto plano
- name: Configurar banco de dados
  hosts: databases
  tasks:
    - name: Criar usuário do banco
      mysql_user:
        name: appuser
        password: "minha_senha_secreta"  # NUNCA faça isso
        priv: "*.*:ALL"
        state: present

# SEGURO — Usando ansible-vault
# playbook.yml (cifrado com ansible-vault)
- name: Configurar banco de dados
  hosts: databases
  tasks:
    - name: Criar usuário do banco
      mysql_user:
        name: appuser
        password: "{{ vault_db_password }}"
        priv: "appdb.*:ALL"
        state: present
        login_unix_socket: /var/run/mysqld/mysqld.sock

# Criptografar o playbook:
# ansible-vault encrypt playbook.yml

# Executar:
# ansible-playbook --ask-vault-pass playbook.yml

# OU usar vault password file:
# ansible-playbook --vault-password-file=.vault_pass playbook.yml
```

{% raw %}
```yaml
# INSEGURO — Shell injection
- name: Processar arquivo
  shell: "echo {{ user_input }} > /tmp/output"
  # user_input pode conter: "foo; rm -rf /"

# SEGURO — Usar módulo argument
- name: Processar arquivo
  ansible.builtin.lineinfile:
    path: /tmp/output
    line: "{{ user_input }}"
    create: yes
    mode: '0644'
```
{% endraw %}

### 9.4 Frameworks e Padrões

- **SLSA (Supply-chain Levels for Software Artifacts)**: https://slsa.dev/
- **SSDF (Secure Software Development Framework)**: NIST SP 800-218
- **OpenSSF Scorecard**: https://securityscorecards.dev/
- **SCA (Software Composition Analysis)**: https://cyclonedx.org/

### 9.5 Comunidades e Certificações

- **DevSecOps Community**: https://www.devsecops.org/
- **Cloud Security Alliance (CSA)**: https://cloudsecurityalliance.org/
- **CompTIA Security+**: Certificação fundamental de segurança
- **CKS (Certified Kubernetes Security Specialist)**: Segurança em Kubernetes
- **AWS Security Specialty**: Segurança na AWS

---

**Próximo capítulo**: No Capítulo 3, vamos aprofundar em Segurança de Aplicações Web, explorando OWASP Top 10, autenticação e autorização, proteção contra ataques comuns, e como integrar testes de segurança de aplicações no pipeline de CI/CD.
---

*[Capítulo anterior: 01 — Introducao Ao Devsecops](01-introducao-ao-devsecops.md)*
*[Próximo capítulo: 03 — Shift Left Security](03-shift-left-security.md)*
