---
layout: default
title: "00-prefacio"
---

# Prefacio — GitHub Actions: Pipelines Seguros e Eficientes

> *"Automacao nao e opcional — e uma necessidade de seguranca."*

---

## Por Que Este Livro Existe

GitHub Actions se tornou o sistema de CI/CD mais usado do mundo, com mais de 20 milhoes de desenvolvedores ativos. Mas a maioria dos workflows e copiada de templates sem entender as implicacoes de seguranca, performance ou manutenibilidade.

Um workflow inseguro pode:
- Expor tokens e secrets em logs publicos
- Executar codigo arbitrario via pull requests
- Comprometer a supply chain do projeto
- Gerar builds nao-reproduziveis
- Custo excessivo em minutos de execucao
- Falhar silenciosamente em producao

Este livro transforma GitHub Actions de "copiar e colar" em uma ferramenta profissional de CI/CD.

---

## Publico-Alvo

- **Desenvolvedores** que usam GitHub e querem CI/CD robusto
- **DevOps/Platform Engineers** que constroem e mantem pipelines
- **Security Engineers** que auditam workflows de CI/CD
- **Tech Leads** que definem padroes de build e deploy

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| Git/GitHub | Basico | Repos, branches, PRs |
| YAML | Basico | Workflow syntax |
| Linux/Shell | Basico | Commands no runner |
| Docker | Basico | Containers no CI/CD |

---

## Estrutura do Livro

### Parte I: Fundamentos (00-03)
- Prefacio, GitHub Actions intro, syntax basica, triggers

### Parte II: Workflows Praticos (04-08)
- Build/test, deploy, matrix builds, caching, artifacts

### Parte III: Seguranca (09-12)
- Secrets, permissions, OIDC, supply chain, hardening

### Parte IV: Avancado (13-17)
- Self-hosted runners, reusable workflows, monorepos, performance, boas praticas

---

## Convencoes

- **Texto**: Portugues brasileiro (PT-BR)
- **Codigo**: Identificadores em ingles
- **Exemplos**: GitHub Actions YAML, scripts Bash
- **Plataforma**: GitHub.com e GitHub Enterprise

---

*[Proximo capitulo: 01 — Introducao ao GitHub Actions](01-introducao-github-actions.md)*
