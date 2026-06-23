# Desenvolvimento Seguro na Web — Índice do Livro

> **OWASP Top 10, XSS, SQL Injection, Auth, API Security, DevSecOps**

---

## Sumário Rápido

| # | Capítulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefácio](00-prefacio.md) | Motivação, público-alvo, convenções |
| 01 | [Introdução à Segurança Web](01-introducao-seguranca-web.md) | HTTP, CORS, CSP, TLS, autenticação |
| 02 | [Protocolo HTTP Seguro](02-protocolo-http-seguro.md) | Headers, cookies, HSTS, CORS |
| 03 | [OWASP Top 10](03-owasp-top-10.md) | Todas as 10 categorias com CVEs |
| 04 | [SQL Injection](04-sql-injection.md) | Injection, NoSQL, parameterized queries |
| 05 | [Cross-Site Scripting (XSS)](05-cross-site-scripting.md) | Reflected, Stored, DOM-based, CSP |
| 06 | [CSRF, Clickjacking e Ataques Client-Side](06-csrf-clickjacking.md) | CSRF tokens, SameSite, frame protection |
| 07 | [Autenticação e Gerenciamento de Sessão](07-autenticacao-sessoes.md) | Passwords, MFA, OAuth 2.0, JWT |
| 08 | [Autorização e Controle de Acesso](08-autorizacao-controle-acesso.md) | RBAC, ABAC, IDOR, OPA |
| 09 | [Criptografia na Web](09-criptografia-na-web.md) | TLS, Web Crypto, SubtleCrypto |
| 10 | [Input Validation](10-validacao-sanitizacao.md) | Allowlists, schemas, sanitization |
| 11 | [Segurança de APIs](11-seguranca-api.md) | REST, GraphQL, gRPC, rate limiting |
| 12 | [JavaScript Seguro](12-javascript-seguro.md) | CSP, SRI, prototype pollution, Node.js |
| 13 | [Segurança Server-Side](13-seguranca-server-side.md) | Django, Flask, Express, Go |
| 14 | [Containers e Deployment](14-seguranca-container.md) | Docker, K8s, secrets, scanning |
| 15 | [DevSecOps para Aplicações Web](15-devsecops-web.md) | SAST/DAST/SCA, pipelines CI/CD |
| 16 | [Penetration Testing](16-pentesting-web.md) | Burp Suite, ZAP, methodology |
| 17 | [Compliance e Boas Práticas](17-compliance-boas-praticas.md) | OWASP ASVS, PCI DSS, LGPD |

---

## Diagrama de Dependências

```
            ┌──────┐
            │  00  │ Prefácio
            └──┬───┘
               │
            ┌──┴──┐
            │  01  │ ← Fundamento obrigatório
            └──┬──┘
               │
       ┌───────┼──────────────────────────────┐
       │       │                              │
   ┌───┴──┐ ┌──┴──┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
   │  02  │ │  03 │ │  04   │ │  05   │ │  06   │ │  07   │
   │ HTTP │ │OWASP│ │SQLi   │ │ XSS   │ │ CSRF  │ │ Auth  │
   └──┬───┘ └──┬──┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
      │        │        │         │         │         │
      │        │     ┌──┴─────────┴─────────┴─────────┘
      │        │     │
      │     ┌──┴─────┴──────────────────────────┐
      │     │  08  │  09  │ 10  │ 11  │ 12  │ 13 │
      │     │AuthZ │ Crypto│InVal│ API  │ JS  │SRV │
      │     └──┬───┴──┬───┴──┬──┴──┬──┴──┬──┴──┬─┘
      │        │      │      │     │     │     │
      │     ┌──┴──────┴──────┴─────┴─────┴─────┘
      │     │
      │  ┌──┴──────────────────────┐
      │  │  14  │  15  │ 16  │ 17  │
      │  │Docker│SecOps│PenT │Comp │
      │  └──────┴──────┴─────┴─────┘
```

---

## Caminhos de Leitura por Perfil

### Para Desenvolvedor Full-Stack
```
01 → 03 → 04 → 05 → 07 → 09 → 10 → 12 → 13
```

### Para DevOps/Platform Engineer
```
01 → 02 → 14 → 15 → 09 → 07
```

### Para Engenheiro de Segurança
```
01 → 03 → 04 → 05 → 06 → 07 → 08 → 11 → 16 → 17
```

### Para Penetration Tester
```
03 → 04 → 05 → 06 → 07 → 08 → 11 → 16
```

### Cobertura Completa
```
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17
```

---

## CVEs Documentados no Livro

| CVE | Título | Capítulo |
|-----|--------|----------|
| CVE-2021-44228 | Log4Shell | 03, 06 |
| CVE-2023-34362 | MOVEit SQL Injection | 04 |
| CVE-2019-9193 | PostgreSQL COPY command | 04 |
| CVE-2012-2122 | MySQL authentication bypass | 04 |
| CVE-2017-5638 | Apache Struts (Equifax) | 03 |
| CVE-2019-11510 | Pulse Secure VPN auth bypass | 07 |
| CVE-2020-1472 | Zerologon | 07 |
| CVE-2019-11091 | MDS (Microarchitectural Data Sampling) | 01 |
| CVE-2014-0160 | Heartbleed | 09 |
| CVE-2019-1547 | OpenSSL ECDSA timing | 09 |

---

## Linguagens e Frameworks Referenciados

| Linguagem | Frameworks | Capítulos |
|-----------|-----------|-----------|
| JavaScript/TypeScript | Express.js, Next.js, React, Vue | 05, 07, 11, 12, 13 |
| Python | Flask, Django, FastAPI | 07, 10, 11, 13 |
| Go | Gin, Echo, Chi | 07, 11, 13 |
| SQL | PostgreSQL, MySQL, SQLite | 04 |
| Docker/K8s | Docker, Kubernetes, Trivy | 14 |
| CI/CD | GitHub Actions, GitLab CI | 15 |
