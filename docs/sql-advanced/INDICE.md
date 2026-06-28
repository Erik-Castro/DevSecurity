---
layout: default
title: "INDICE"
---

# SQL Avancado e Seguranca — Indice

---

| # | Capitulo | Tema Principal | Linhas |
|---|----------|----------------|--------|
| 00 | [Prefacio](00-prefacio.md) | Casos reais, publico-alvo | 72 |
| 01 | [Introducao ao SQL Avancado](01-introducao-sql-avancado.md) | SQL moderno, features, dialectos | 2799 |
| 02 | [Tipos de Dados e Esquemas](02-tipos-dados-esquemas.md) | Tipos nativos, CHECK, ENUM, JSON | 2813 |
| 03 | [Joins, CTEs e Subqueries](03-joins-ctes-subqueries.md) | JOINs avancados, CTE recursivos, window functions | 2806 |
| 04 | [SQL Injection - Fundamentos](04-sqli-fundamentos.md) | Como funciona, union-based, error-based | 3026 |
| 05 | [SQL Injection - Tecnicas Avancadas](05-sqli-avancado.md) | Blind, time-based, out-of-band, second-order | 2800 |
| 06 | [Blind SQL Injection em Detalhe](06-blind-sqli.md) | Boolean-based, time-based, techniques | 2829 |
| 07 | [NoSQL Injection](07-nosql-injection.md) | MongoDB, Redis, CouchDB |
| 08 | [Stored Procedures e Seguranca](08-stored-procedures.md) | Dynamic SQL, permission models |
| 09 | [Triggers e Auditing](09-triggers-auditing.md) | Audit tables, CDC, change tracking |
| 10 | [Transactions e Isolation](10-transactions-isolation.md) | ACID, isolation levels, deadlocks |
| 11 | [Indices e Performance](11-indices-performance.md) | B-tree, hash, partial, covering |
| 12 | [Partitioning e Sharding](12-partitioning-sharding.md) | Horizontal/vertical, strategies |
| 13 | [Query Optimization](13-query-optimization.md) | EXPLAIN, query plans, rewriting |
| 14 | [Database Hardening](14-database-hardening.md) | Config segura, encryption at rest |
| 15 | [Casos Reais de Ataques](15-casos-reais.md) | Equifax, MOVEit, Heartbleed | 2801 |
| 16 | [Compliance e Normas](16-compliance.md) | PCI DSS, LGPD, GDPR | 2892 |
| 17 | [Boas Praticas e Checklist](17-boas-praticas.md) | Anti-patterns, checklist | 2904 |

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
         12 -> 13 -> 14
                    |
              15 -> 16 -> 17
```
