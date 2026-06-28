---
layout: default
title: "00-prefacio"
---

# Prefacio — SQL Avancado e Seguranca

> *"O banco de dados e onde seus dados vivem. Proteja-o como protege sua casa."*

---

## Por Que Este Livro Existe

SQL e a lingua universal dos dados. Mais de 95% dos dados do mundo sao acessados via SQL em algum ponto. E, paradoxalmente, SQL injection continua sendo a vulnerabilidade mais explorada do mundo — ha mais de 20 anos.

Mas SQL vai muito alem de SELECT e INSERT. Este livro explora o SQL avancado — CTEs, window functions, query optimization, partitioning — e cruza cada topico com a perspectiva de seguranca. Cada funcionalidade e ensinada com codigo funcional E com as vulnerabilidades correspondentes.

### Casos Reais Documentados

- **Equifax (2017)**: SQL injection em Apache Struts expôs dados de 147M pessoas
- **MOVEit (2023)**: SQL injection em CVE-2023-34362 afetou 2.500+ organizacoes
- **Heartbleed (2014)**: Embora nao seja SQL, mostra como crypto e database security se entrelacam
- **Log4Shell (2021)**: Impactou sistemas de logging que alimentam bancos de dados
- **SolarWinds (2020)**: Supply chain que comprometeu acesso a databases corporativos

---

## Publico-Alvo

- **Desenvolvedores** que trabalham com bancos de dados diariamente
- **DBAs** que gerenciam producao e precisam de seguranca
- **Engenheiros de Seguranca** que auditan apoiucacoes com database
- **Data Engineers** que constroem pipelines de dados
- **Arquitetos** que projetam sistemas de dados

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| SQL | Intermediario | Consultas, joins, subqueries |
| Alguma linguagem de backend | Basico | Python, Node.js ou Go |
| Conceitos de rede | Basico | HTTP, APIs |

---

## Estrutura do Livro

### Parte I: Fundamentos SQL (00-03)
- Prefacio, SQL avancado, tipos de dados, joins

### Parte II: SQL Injection (04-08)
- Fundamentos, tecnicas avancadas, blind injection, NoSQL, stored procedures

### Parte III: Performance e Arquitetura (09-12)
- Indices, partitioning, query optimization, transactions

### Parte IV: Operacao e Seguranca (13-17)
- Database hardening, auditing, casos reais, compliance, boas praticas

---

## Convencoes

- **Texto**: Portugues brasileiro (PT-BR)
- **Codigo**: SQL padrao + specificidades (PostgreSQL, MySQL, SQLite)
- **Exemplos**: Tabelas虚构 com dados realistas

---

*[Proximo capitulo: 01 — Introducao ao SQL Avancado](01-introducao-sql-avancado.md)*
