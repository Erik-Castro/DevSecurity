# DevSecOps na Prática — Índice do Livro

> **Pipeline CI/CD Seguro, Ferramentas, Containers, Cloud, Kubernetes e Compliance**
>
> 18 capítulos | ~52.000 linhas | 60+ casos de segurança documentados | Bash, Python, YAML, Docker, HCL, Go

---

## Sumário Rápido

| # | Capítulo | Linhas |
|---|----------|--------|
| 00 | [Prefácio](00-prefacio.md) | 2.094 |
| 01 | [Introdução ao DevSecOps](01-introducao-ao-devsecops.md) | 2.283 |
| 02 | [Fundamentos de DevOps e Segurança](02-fundamentos-devops-e-seguranca.md) | 2.557 |
| 03 | [Shift-Left Security](03-shift-left-security.md) | 2.591 |
| 04 | [SAST: Análise Estática de Segurança](04-sast-analise-estatica.md) | 2.355 |
| 05 | [DAST: Análise Dinâmica de Segurança](05-dast-analise-dinamica.md) | 2.980 |
| 06 | [SCA: Análise de Composição de Software](06-sca-composicao-software.md) | 2.434 |
| 07 | [Segurança de Containers](07-seguranca-de-containers.md) | 2.159 |
| 08 | [Infrastructure as Code: Segurança](08-iac-seguranca.md) | 3.558 |
| 09 | [Segurança de Pipelines CI/CD](09-seguranca-cicd.md) | 2.573 |
| 10 | [Gestão de Segredos](10-gestao-de-segredos.md) | 2.521 |
| 11 | [Segurança em Cloud](11-seguranca-cloud.md) | 3.132 |
| 12 | [Segurança em Kubernetes](12-seguranca-kubernetes.md) | 2.203 |
| 13 | [GitOps e Segurança da Cadeia de Suprimentos](13-gitops-e-supply-chain.md) | 2.400 |
| 14 | [Monitoramento e Observabilidade de Segurança](14-monitoramento-e-observabilidade.md) | 3.339 |
| 15 | [Resposta a Incidentes em Produção](15-resposta-a-incidentes-em-producao.md) | 4.668 |
| 16 | [Compliance Automatizado](16-compliance-automatizado.md) | 4.080 |
| 17 | [Cultura DevSecOps e Métricas](17-cultura-devsecops-e-metricas.md) | 4.090 |
| **Total** | | **~52.017** |

---

## Índice Detalhado por Capítulo

---

### [Prefácio — DevSecOps na Prática](00-prefacio.md)

- **1. Por que DevSecOps na Prática**
  - 1.1 A crise de segurança em DevOps
  - 1.2 O caso para DevSecOps
  - 1.3 Casos públicos documentados — SolarWinds, Codecov, 3CX, xz-utils, Log4Shell
- **2. Obrigação Ética e Impacto**
- **3. Público-Alvo** — DevOps, Security Engineers, Developers, Architects
- **4. Pré-Requisitos e Ambiente**
  - Docker, Kubernetes, Git, Python 3.10+, Trivy, Snyk, Semgrep
  - docker-compose.yml completo para lab
  - Script de setup completo
- **5. Convenções do Livro**
- **6. Estrutura do Livro**
- **7. Como Acompanhar Atualizações**

---

### [Cap 01 — Introdução ao DevSecOps](01-introducao-ao-devsecops.md)

- **1. O que é DevSecOps** — Definição, evolução, manifesto, modelo de maturidade
- **2. Por que Segurança Falha em Ambientes Ágeis**
- **3. Princípios Fundamentais** — Automação, shift-left, verificação contínua, defense in depth
- **4. O Maturidade DevSecOps** — Níveis 0-5, checklist de avaliação
- **5. Ferramentas do Ecossistema** — SAST, DAST, SCA, secrets, containers, IaC
- **6. Estudo de Caso** — Pipeline antes vs depois de DevSecOps
- **7. Métricas** — MTTR, tempo de detecção, KPIs

---

### [Cap 02 — Fundamentos de DevOps e Segurança](02-fundamentos-devops-e-seguranca.md)

- **1. DevOps: Conceitos Essenciais** — CI/CD, IaC, containers, GitOps
- **2. Segurança em Cada Pilar do DevOps** — Plan → Code → Build → Test → Release → Deploy → Operate → Monitor
- **3. Pipeline CI/CD: Anatomia Segura** — Arquitetura, security gates, GitHub Actions completo
- **4. Git: Segurança no Controle de Versão** — Signed commits, branch protection, pre-commit hooks
- **5. Docker: Fundamentos de Segurança** — Dockerfile seguro, non-root, image scanning
- **6. Kubernetes: Fundamentos de Segurança** — Pod Security, Network Policies, RBAC
- **7. Infrastructure as Code Seguro** — Terraform security, state file security
- **8. Exercício Prático** — Pipeline inseguro para tornar seguro

---

### [Cap 03 — Shift-Left Security](03-shift-left-security.md)

- **1. O que é Shift-Left Security** — Definição, ROI, estatísticas
- **2. IDE Integration para Segurança** — Extensões VS Code/JetBrains, pre-commit hooks
- **3. Code Review Automatizado** — GitHub PR checks, CodeQL, Semgrep custom rules
- **4. Threat Modeling no Pipeline** — ThreatPlaybook, STRIDE automatizado
- **5. Secret Scanning** — GitLeaks, TruffleHog, GitHub secret scanning
- **6. License Compliance** — SPDX, CycloneDX, FOSSA
- **7. Exemplo Completo: Pipeline Shift-Left**

---

### [Cap 04 — SAST: Análise Estática de Segurança](04-sast-analise-estatica.md)

- **1. Fundamentos de Análise Estática** — AST parsing, taint analysis, false positives
- **2. Semgrep** — Regras customizadas, taint mode, CI/CD
- **3. SonarQube** — Setup Docker, quality gates, custom rules
- **4. CodeQL** — Consultas, databases, GitHub Advanced Security
- **5. Bandit** — Python security scanning
- **6. ESLint Security** — JavaScript/TypeScript
- **7. Comparação de Ferramentas** — Tabela de features, benchmarks
- **8. Pipeline SAST completo** — Multi-language

---

### [Cap 05 — DAST: Análise Dinâmica de Segurança](05-dast-analise-dinamica.md)

- **1. Fundamentos de DAST** — Black-box testing, crawling, autenticação
- **2. OWASP ZAP** — Docker, automated scan, API scan, CI/CD automation
- **3. Nikto** — Web server scanning
- **4. Nuclei** — Template-based scanning, custom templates
- **5. API Security Testing** — REST, GraphQL, gRPC
- **6. DAST em Pipelines CI/CD** — Staging, scan timing, false positives
- **7. Authenticated Scanning** — Session handling, OAuth flow
- **8. Exemplo Completo: Pipeline DAST**

---

### [Cap 06 — SCA: Análise de Composição de Software](06-sca-composicao-software.md)

- **1. O que é SCA** — Dependências, transitive dependencies, attack vectors
- **2. SBOM (Software Bill of Materials)** — SPDX, CycloneDX, geração, NTIA
- **3. Trivy** — Containers, filesystem, repos, policies
- **4. Snyk** — Monitoring, fix PRs, containers, IaC
- **5. OWASP Dependency-Check** — Maven/Gradle, standalone, CVE database
- **6. GitHub Dependabot** — Configuração, security alerts, automated PRs
- **7. Gerenciamento de Vulnerabilidades** — Triage, risk assessment, CVE prioritization
- **8. Políticas de Dependências** — Pinning, licenses, severity
- **9. Pipeline SCA completo** — Multi-tool + SBOM

---

### [Cap 07 — Segurança de Containers](07-seguranca-de-containers.md)

- **1. Fundamentos** — Containers vs VMs, attack surface, OCI runtime
- **2. Dockerfile Seguro** — Multi-stage, distroless, non-root, read-only
- **3. Scanning de Imagens** — Trivy, Grype, Docker Scout, Snyk
- **4. Runtime Security** — AppArmor, Seccomp, capabilities
- **5. Docker Bench Security** — CIS benchmark, auditoria automatizada
- **6. Registry Security** — Private registry, image signing (Cosign)
- **7. Docker Compose Seguro** — Security constraints, resource limits
- **8. Pipeline de Container Security** — Build → Scan → Sign → Push → Verify

---

### [Cap 08 — Infrastructure as Code: Segurança](08-iac-seguranca.md)

- **1. IaC e Segurança** — Attack surface, state file security
- **2. Terraform Seguro** — Checkov, tfsec, Sentinel, VPC/S3/RDS/IAM seguro
- **3. Checkov** — Custom policies em Python, CI/CD integration
- **4. tfsec** — Rule customization, severity filtering
- **5. Ansible Seguro** — ansible-lint, Vault, Galaxy scanning
- **6. CloudFormation Security** — cfn-nag, cfn-lint
- **7. Pulumi Security** — CrossGuard policies
- **8. Kubernetes IaC Security** — OPA/Gatekeeper, Kyverno
- **9. State File Security** — Remote state, encryption, locking
- **10. Pipeline IaC completo**

---

### [Cap 09 — Segurança de Pipelines CI/CD](09-seguranca-cicd.md)

- **1. Segurança de CI/CD** — Attack surface, trust boundaries, blast radius
- **2. GitHub Actions Security** — Permissions, third-party actions, OIDC
- **3. GitLab CI Security** — Variables, runners, job tokens
- **4. Jenkins Security** — Pipeline, credentials, plugins
- **5. Secret Management em Pipelines** — GitHub Secrets, Vault, AWS/Azure
- **6. Pipeline Isolation** — Ephemeral runners, container-based, network
- **7. Artifact Security** — Reproducibility, signing, SBOM, provenance
- **8. Deployment Security** — Approval gates, canary, blue-green

---

### [Cap 10 — Gestão de Segredos](10-gestao-de-segredos.md)

- **1. Por que Gestão de Segredos Importa** — Estatísticas, tipos, impacto
- **2. Detecção de Segredos** — GitLeaks, TruffleHog, detect-secrets
- **3. HashiCorp Vault** — Dynamic secrets, transit, PKI, setup completo
- **4. Cloud Secret Management** — AWS Secrets Manager, Azure Key Vault, GCP
- **5. Kubernetes Secrets** — Native, Sealed Secrets, External Secrets, CSI
- **6. Environment Variables Seguras** — .env management, dotenv-linter
- **7. Certificate Management** — Let's Encrypt, cert-manager, internal PKI
- **8. Key Rotation** — Automated rotation, zero-downtime

---

### [Cap 11 — Segurança em Cloud](11-seguranca-cloud.md)

- **1. Shared Responsibility Model** — IaaS/PaaS/SaaS, matrix de responsabilidade
- **2. AWS Security** — IAM, S3, EC2, Lambda, CloudTrail, GuardDuty
- **3. Azure Security** — Entra ID, Storage, Key Vault
- **4. GCP Security** — IAM, GCS, Cloud Functions
- **5. Cloud Security Posture Management** — AWS Config, Azure Policy, SCC
- **6. Cloud Workload Protection** — Containers, serverless, VM agents
- **7. Network Security in Cloud** — Security groups, VPC, WAF
- **8. Data Protection** — Encryption, key management, backups
- **9. Cloud Logging and Monitoring** — CloudTrail, SIEM integration

---

### [Cap 12 — Segurança em Kubernetes](12-seguranca-kubernetes.md)

- **1. Modelo de Segurança do Kubernetes** — Layers, CIA, attack surface
- **2. Pod Security Standards** — Privileged, Baseline, Restricted
- **3. RBAC** — Roles, Service Accounts, least privilege
- **4. Network Policies** — Default deny, namespace isolation
- **5. Secrets in Kubernetes** — Sealed Secrets, External Secrets, Vault
- **6. Image Security** — Scanning, pull secrets, Trivy operator
- **7. OPA/Gatekeeper** — Rego, constraint templates
- **8. Kyverno** — Validate, mutate, generate policies
- **9. Runtime Security** — Falco, audit logging, seccomp
- **10. Cluster Hardening** — API server, etcd, worker nodes, CIS benchmark

---

### [Cap 13 — GitOps e Segurança da Cadeia de Suprimentos](13-gitops-e-supply-chain.md)

- **1. GitOps Fundamentals** — Principles, pull-based, reconciliation
- **2. Supply Chain Security** — Attack vectors, SLSA framework
- **3. ArgoCD Security** — RBAC, credentials, SSO
- **4. Flux Security** — Image automation, policy enforcement
- **5. Artifact Signing** — Sigstore/Cosign, Notary v2, in-toto
- **6. Provenance and Attestation** — SLSA provenance, SBOM attestation
- **7. SLSA Framework** — Levels 0-4, implementation guide
- **8. Dependency Security** — Pinning, lock files, reproducible builds

---

### [Cap 14 — Monitoramento e Observabilidade de Segurança](14-monitoramento-e-observabilidade.md)

- **1. Observabilidade vs Monitoramento** — Logs, metrics, traces, OpenTelemetry
- **2. Security Logging** — What to log, structured logging, Fluentd
- **3. SIEM** — ELK Stack, Wazuh, dashboards de segurança
- **4. Falco para Runtime Security** — Rules, custom rules, alert management
- **5. Prometheus e Grafana para Segurança** — Metrics, alerts, dashboards
- **6. Cloud-Native Security Monitoring** — CloudTrail, Sentinel, Chronicle
- **7. Incident Detection** — Alert design, severity, escalation
- **8. Threat Hunting** — Methodology, queries, Jupyter notebooks
- **9. Metrics de Segurança** — MTTD, MTTR, KPIs

---

### [Cap 15 — Resposta a Incidentes em Produção](15-resposta-a-incidentes-em-producao.md)

- **1. Incident Response em Ambientes DevOps** — Immutable infrastructure, rollback
- **2. Runbooks e Playbooks** — Automated runbooks, examples
- **3. Rollback Strategies** — Automated rollback, feature flags
- **4. Container Incident Response** — Forensic analysis, diff analysis
- **5. Kubernetes Incident Response** — Pod eviction, node isolation
- **6. Cloud Incident Response** — AWS, Azure, GCP forensics
- **7. Communication** — Stakeholder notification, status page
- **8. Post-Incident Review** — Blameless post-mortem, root cause analysis
- **9. Chaos Engineering para Resposta** — Game days, drills

---

### [Cap 16 — Compliance Automatizado](16-compliance-automatizado.md)

- **1. Compliance e DevSecOps** — Compliance as code, continuous compliance
- **2. SOC 2 Type II** — Trust service criteria, evidence automation
- **3. PCI DSS** — Requirements, automated controls, evidence
- **4. GDPR/LGPD** — Data protection by design, PIA automation
- **5. CIS Benchmarks** — Docker, Kubernetes, Linux automated testing
- **6. OpenSCAP** — Security profiles, scanning, reporting
- **7. Policy as Code** — OPA/Rego, Sentinel, Kyverno
- **8. Audit Trail** — Immutable logs, integrity verification
- **9. Evidence Automation** — Collection, storage, reporting

---

### [Cap 17 — Cultura DevSecOps e Métricas](17-cultura-devsecops-e-metricas.md)

- **1. Cultura de Segurança** — Security champions, gamification, training
- **2. Organização e Pessoas** — Shared responsibility, RACI matrix
- **3. Métricas de DevSecOps** — MTTD, MTTR, vulnerability density, pipeline metrics
- **4. Dashboards de Segurança** — Executive, engineering, Grafana JSON
- **5. Programa de Bug Bounty** — Setup, scope, disclosure
- **6. Formação Contínua** — Training, CTF, learning paths
- **7. Tendências Futuras** — AI, policy as code, supply chain, post-quantum
- **8. Roadmap de Implementação** — 12-month phased plan

---

## Casos de Segurança Documentados por Capítulo

| Caso | Capítulos |
|------|-----------|
| SolarWinds Supply Chain (2020) | 00, 13, 15 |
| Codecov Bash Uploader (2021) | 00, 09, 13 |
| 3CX Supply Chain (2023) | 00, 13 |
| xz-utils Backdoor (2024, CVE-2024-3094) | 00, 13 |
| Log4Shell (CVE-2021-44228) | 00, 06, 13, 15 |
| Capital One Breach (2019) | 01, 08, 17 |
| Equifax Breach (2017) | 01, 14, 15 |
| Target Breach (2013) | 14, 15 |
| Travis CI Secrets Leak (2021) | 00, 01, 09 |
| Docker Hub Crypto Miners | 07 |
| CVE-2019-5736 runc Escape | 07 |
| Tesla K8s Breach (2018) | 12 |
| Shopify K8s Incident | 12 |
| event-stream npm (2018) | 06, 13 |
| ua-parser-js (2021) | 06, 13 |
| colors.js Sabotage (2022) | 06 |
| Uber API Key Leak (2019) | 10, 17 |
| GitHub Actions Injection | 09 |
| GitLab CI Vulnerabilities | 09 |
| Jenkins CVE-2024-23897 | 09 |
| AWS S3 Misconfigurations | 08, 11 |
| Google GDPR Fine 50M EUR | 16 |
| Amazon GDPR Fine 746M EUR | 16 |
