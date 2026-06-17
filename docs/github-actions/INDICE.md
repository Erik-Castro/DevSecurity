---
layout: default
title: "INDICE"
---

# GitHub Actions: Pipelines Seguros e Eficientes — Indice

---

| # | Capitulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefacio](00-prefacio.md) | Motivacao, publico-alvo |
| 01 | [Introducao ao GitHub Actions](01-introducao-github-actions.md) | Conceitos, arquitetura, ecossistema |
| 02 | [Syntax e Estrutura de Workflows](02-syntax-workflows.md) | YAML, triggers, jobs, steps |
| 03 | [Triggers e Eventos](03-triggers-eventos.md) | push, PR, schedule, workflow_dispatch |
| 04 | [Build e Test Automatizados](04-build-test.md) | Matrix builds, testes, coverage |
| 05 | [Deploy e Releases](05-deploy-releases.md) | GitHub Pages, Docker, cloud deploy |
| 06 | [Matrix Builds e Multi-Plataforma](06-matrix-builds.md) | Linux/macOS/Windows, multi-compiler |
| 07 | [Caching e Performance](07-caching-performance.md) | actions/cache, dependabot, re-approval |
| 08 | [Artifacts e Outputs](08-artifacts-outputs.md) | Upload/download, sharing between jobs |
| 09 | [Secrets e Variaveis Seguras](09-secrets-variaveis.md) | Environment secrets, OIDC, masking |
| 10 | [Permissions e least-privilege](10-permissions.md) | GITHUB_TOKEN, scopes, conditional |
| 11 | [Supply Chain Security](11-supply-chain.md) | Pin actions, hash verification, dependabot |
| 12 | [Harden Runners](12-harden-runners.md) | Self-hosted security, ephemeral runners |
| 13 | [Reusable Workflows](13-reusable-workflows.md) | workflow_call, composites, org-level |
| 14 | [Monorepos com GitHub Actions](14-monorepos.md) | path filters, turborepo, nx |
| 15 | [Debugging e Troubleshooting](15-debugging.md) | Act, debug logs, rerun strategies |
| 16 | [Monitoramento e Metricas](16-monitoramento.md) | Workflow runs, billing, optimization |
| 17 | [Boas Praticas e Checklist](17-boas-praticas.md) | Anti-patterns, decision trees, checklist |

---

## Dependencias

```
00 -> 01 -> 02 -> 03
                 |
         +-------+-------+
         |       |       |
         04      05      06
         |       |       |
         +---+---+---+---+
             |       |
             07      08
             |       |
         +---+---+---+---+
         |       |       |
         09      10      11
         |       |       |
         +---+---+---+---+
             |
             12
             |
         +---+---+---+---+
         |       |       |
         13      14      15
         |       |       |
         +---+---+---+---+
             |
         16 -> 17
```

---

## CVEs e Incidentes Documentados

| Incidente | Titulo | Capitulos |
|-----------|--------|-----------|
| actions/checkout v2 compromise | Supply chain attack | 11 |
| Codecov bash uploader | Secret exfiltration | 09, 11 |
| eventname injection | Workflow injection | 10, 12 |
| ReDoS em patterns | Performance attack | 15 |
| Actions marketplace typosquatting | Supply chain | 11 |

---

## Ferramentas Referenciadas

| Ferramenta | Uso | Capitulos |
|------------|-----|-----------|
| GitHub Actions | CI/CD | Todos |
| Docker | Container builds | 04, 05, 06 |
| Dependabot | Dependency updates | 07, 11 |
| Act | Local testing | 15 |
| actionlint | YAML linting | 17 |
| scorecard | Security analysis | 11, 17 |
