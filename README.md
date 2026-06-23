---
layout: default
title: "DevSecurity"
---

# DevSecurity — Livros de Desenvolvimento Seguro

> **Segurança não é um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositório

Este é o repositório central da coleção **DevSecurity**: livros técnicos de desenvolvimento de software seguro, escritos em português, com foco prático em **C++ moderno (C++17/20)** e arquitetura de sistemas.

O objetivo é preencher a lacuna entre teoria de segurança e prática de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padrões de código seguro, verificável e pronto para produção.

### Números da Coleção

| Métrica | Valor |
|---------|-------|
| Livros publicados | 10 |
| Total de capítulos | 180 |
| Total de linhas | ~527.000+ |
| CVEs documentados | 420+ |
| Linguagens | C++17/20, Python, Bash, YAML, Go, Assembly, JS/TS, CMake, GitHub Actions, Rust, WAT |
| Idioma | Português (PT-BR) para texto, Inglês para código |

---

## Livros Publicados

### 1. Security-Driven Development com C++17

> *Desenvolvimento Seguro orientado à Segurança — 17 capítulos | ~48.500 linhas | 100+ CVEs*

[Leia online](docs/book/INDICE.md)

---

### 2. DevSecOps na Prática

> *Pipeline CI/CD Seguro, Containers, Cloud, Kubernetes — 18 capítulos | ~52.300 linhas | 60+ CVEs*

[Leia online](docs/devsecops/INDICE.md)

---

### 3. Engenharia e Análise de Malware em C++

> *Reverse Engineering, Debugging, Ransomware, Rootkits — 18 capítulos | ~55.600 linhas | 100+ malwares*

[Leia online](docs/malware/INDICE.md)

---

### 4. Concorrência e Paralelismo Seguro em C++

> *Lock-Free, Deadlocks, Thread Pools, Coroutines — 18 capítulos | ~19.700 linhas*

[Leia online](docs/concurrency/INDICE.md)

---

### 5. Criptografia Engenheira em C++

> *Constant-Time, Side-Channels, TLS 1.3, PQC, FHE — 18 capítulos | ~66.400 linhas | 20+ CVEs*

[Leia online](docs/cryptography/INDICE.md)

---

### 6. Desenvolvimento Seguro na Web

> *OWASP Top 10, XSS, SQLi, Auth, API Security — 18 capítulos | ~57.800 linhas | 20+ CVEs*

[Leia online](docs/web/INDICE.md)

---

### 7. CMake Seguro e Build Systems

> *Flags de Segurança, Sanitizers, Hardening, Supply Chain — 18 capítulos | ~52.500 linhas*

[Leia online](docs/cmake-book/INDICE.md)

---

### 8. GitHub Actions Pipelines Seguros

> *Triggers, Secrets, OIDC, Reusable Workflows, Supply Chain — 18 capítulos | ~49.000 linhas*

[Leia online](docs/github-actions/INDICE.md)

---

### 9. WebAssembly Seguro

> *Wasm Architecture, WASI, Sandboxing, Plugins, Edge, Blockchain — 18 capítulos | ~76.300 linhas*

[Leia online](docs/wasm/INDICE.md)

---

### 10. Autenticação, Autorização e Controle de Acesso

> *OAuth, OIDC, SSO, RBAC, ABAC, WebAuthn, Caso Misantropi4 — 18 capítulos | ~49.500 linhas*

**Conteúdo:**
- **Autenticação Moderna**: OAuth 2.0, OpenID Connect, SSO, Magic Links, WebAuthn/FIDO2
- **Controle de Acesso**: RBAC, ABAC, ReBAC, MAC/DAC, Policy Engines (OPA, Cedar)
- **Segurança**: Credential stuffing, brute force, session hijacking, MFA fatigue
- **Caso Real**: Análise completa do ataque Misantropi4 ao sistema IDAP brasileiro (junho 2026)
- **Compliance**: OWASP ASVS, NIST SP 800-63, LGPD, GDPR, PCI DSS

**CVEs e incidentes**: Misantropi4/IDAP, Log4Shell, SolarWinds, Colonial Pipeline, LastPass, Uber/Lapsus$, Okta.

[Leia online](docs/authz/INDICE.md)

---

## Para Quem Escrevo

- **Desenvolvedores C++** que querem código seguro por design
- **Engenheiros de Segurança** que auditam e revisam código
- **DevOps / Platform Engineers** que constroem pipelines seguros
- **Tech Leads** que definem padrões de build e deploy
- **Estudantes avançados** de ciência da computação

---

## Como Usar os Livros

Cada livro é **autocontido**, mas a sequência recomendada por perfil:

```
Desenvolvedor:   SDD (1-5) -> SDD (6-12) -> DevSecOps (1-4) -> DevSecOps (5-9)
Eng. Segurança:  Malware (1-4) -> Malware (5-10) -> SDD (13-17) -> DevSecOps (10-17)
DevOps/Platform: DevSecOps (1-9) -> DevSecOps (10-17) -> GitHub Actions (1-9)
Arquiteto:       SDD (1-3) -> DevSecOps (1-3) -> CMake (1-8) -> GitHub Actions (1-8)
Criptografia:    SDD (1-3) -> Criptografia (01-03) -> Criptografia (04-09) -> Criptografia (10-17)
```

---

## Estrutura do Repositório

```
DevSecurity/
├── README.md
├── CONTRIBUTING.md
├── PROXIMOS-PROJETOS.md
├── docs/
│   ├── index.md
│   ├── book/           # Livro 1: SDD (C++17)
│   ├── devsecops/      # Livro 2: DevSecOps (Multi-lang)
│   ├── malware/        # Livro 3: Malware (C++17 + asm)
│   ├── concurrency/    # Livro 4: Concorrência (C++17/20)
│   ├── cryptography/   # Livro 5: Criptografia (C++17)
│   ├── web/            # Livro 6: Web Security (JS/TS/Python/Go)
│   ├── cmake-book/     # Livro 7: CMake (CMake + C/C++)
│   ├── github-actions/ # Livro 8: GitHub Actions (YAML/Bash)
│   ├── wasm/           # Livro 9: WebAssembly (Rust/C++/WAT)
│   └── authz/          # Livro 10: Auth/AuthZ
├── epub/               # Versões EPUB dos livros
├── openspec/           # SDD artifacts
└── scripts/            # Scripts auxiliares
```

---

## Contribuições

Este é um projeto de autoria individual, mas **feedback é bem-vindo**:

- **Issues**: Erros técnicos, CVEs faltando, exemplos que não compilam
- **Discussões**: Sugestões de temas, capítulos, formatos
- **Traduções**: Se quiser traduzir para inglês/espanhol, abra issue primeiro

---

## Licença

**CC BY-NC-SA 4.0** — Compartilhe, adapte, cite a fonte. Uso comercial requer autorização.

---

## Autor

Desenvolvedor de sistemas, foco em segurança de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com segurança de verdade."*
