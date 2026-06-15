---
layout: default
title: "Proximos Projetos"
---

# Proximos Projetos — Livros Open-Source DevSecurity

> Diretrizes do projeto: livros tecnicos gratuitos em Markdown, linguagem PT-BR para texto, codigo em ingles (C++17 ou linguagem apropriada), minimo 800 linhas por capitulo, 17+ capitulos, com casos publicos documentados (CVEs).

---

## Livros Concluidos

### Livro 1: Security-Driven Development (CONCLUIDO)
- **17 capitulos** | ~48.500 linhas | **C++17**
- [Indice](docs/book/INDICE.md) | [Diretorio](docs/book/)
- Foco: SDD, Secure SDLC, Memory Safety, AuthN/AuthZ, Crypto, Network, DB, API, Concurrency, Testing, Compliance, Hardening
- 100+ CVEs documentados

### Livro 2: DevSecOps na Pratica (CONCLUIDO)
- **18 capitulos** | ~52.300 linhas | **Bash, Python, YAML, Docker, HCL, Go**
- [Indice](docs/devsecops/INDICE.md) | [Diretorio](docs/devsecops/)
- Foco: CI/CD Security, SAST/DAST/SCA, Containers, K8s, Cloud, GitOps, Supply Chain, Monitoring, Incident Response, Compliance
- 60+ casos de seguranca documentados

### Livro 3: Engenharia e Analise de Malware em C++ (CONCLUIDO)
- **18 capitulos** | ~55.600 linhas | **C++17 + Assembly**
- [Indice](docs/malware/INDICE.md) | [Diretorio](docs/malware/)
- Foco: Reverse Engineering, Static/Dynamic Analysis, Debugging, Ransomware, Rootkits, Exploits, YARA, Automation
- 100+ malwares documentados

### Livro 4: Concorrencia e Paralelismo Seguro em C++ (CONCLUIDO)
- **18 capitulos** | ~19.700 linhas | **C++17/20**
- [Indice](docs/concurrency/INDICE.md) | [Diretorio](docs/concurrency/)
- Foco: Modelo de memoria, Lock-Free, Deadlocks, Thread Pools, Paralelismo, Cache, Futures/Coroutines, Testes, Debugging, Performance, SIMD/GPU
- CVEs de concorrencia documentados

### Livro 5: Criptografia Engenheira em C++ (CONCLUIDO)
- **18 capitulos** | ~66.400 linhas | **C++17**
- [Indice](docs/cryptography/INDICE.md) | [Diretorio](docs/cryptography/)
- Foco: Constant-Time, Side-Channels, HSM, TLS 1.3, PQC, Key Management, FHE, ZKP, Formal Verification, Testing, Compliance
- 20+ CVEs documentados

### Livro 6: Desenvolvimento Seguro na Web (CONCLUIDO)
- **18 capitulos** | ~57.800 linhas | **JS/TS, Python, Go**
- [Indice](docs/web/INDICE.md) | [Diretorio](docs/web/)
- Foco: OWASP Top 10, XSS, SQLi, CSRF, Auth, API Security, Containers, DevSecOps, Pen Testing, Compliance
- 20+ CVEs documentados

### Livro 7: CMake Seguro e Build Systems (CONCLUIDO)
- **18 capitulos** | ~52.500 linhas | **CMake 3.20+, C++17/20**
- [Indice](docs/cmake-book/INDICE.md) | [Diretorio](docs/cmake-book/)
- Foco: Flags de seguranca, Sanitizers, Hardening, Analise Estatica, Reproducible Builds, Supply Chain, vcpkg/Conan, CI/CD
- 6+ CVEs documentados

---

## Backlog de Livros Planejados

### Tier 1 — Alta demanda e sinergia direta

| # | Titulo | Foco | Linguagem | Prioridade |
|---|--------|------|-----------|------------|
| 8 | **WebAssembly Seguro** | Wasm sandboxing, WASI, component model, memory safety, browser vs server | Rust, C++, Wat | Alta |
| 9 | **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++, corpus management, OSS-Fuzz, CI/CD | C++17 | Alta |
| 10 | **Security Code Review Handbook** | Checklists praticos, anti-patterns, revisao de PRs, automacao | C++17 | Media |
| 11 | **LGPD/GDPR para Engenheiros** | Privacy by Design, consentimento, criptografia, DPIA | Conceitual + codigo | Media |
| 12 | **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security | Conceitual | Media |

### Tier 2 — Nichos com pouca cobertura em PT-BR

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 13 | **Firmware & Embedded Security** | Bootloader security, secure boot, TPM, ARM TrustZone, IoT | C + C++17 |
| 14 | **Side-Channel Analysis & Mitigation** | Timing, cache, power, EM attacks, constant-time | C++17 + Assembly |
| 15 | **Binary Exploitation & Mitigation Bypass** | ROP/JOP, heap exploitation, CFG/ACG bypass, kernel exploitation | C++17 + Assembly |
| 16 | **Threat Hunting & DFIR** | Log analysis, memory forensics, network forensics, timeline | Python + C++ |

### Tier 3 — Ampliam o alcance do projeto

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 17 | **Security Testing Automation** | CI/CD security gates, mutation testing, contract testing | Multi |
| 18 | **Secure DevOps at Scale** | Monorepo security, multi-team pipelines, compliance automation | Bash/YAML/HCL |

### Tier 4 — Expansao de linguagem

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 19 | **Secure Coding in Rust** | Ownership/borrowing for security, unsafe patterns, FFI, crypto | Rust |
| 20 | **Python para Seguranca de Software** | Automacao, analise de dados, tooling, malware analysis | Python |
| 21 | **Go for Security Engineering** | Concurrent security tools, networking, cloud security | Go |

---

## Criterios de Selecao

- **Demanda**: livros com maior audiencia potencial primeiro
- **Sinergia**: livros que complementam os anteriores
- **Diferenciacao**: pouca cobertura gratuita em PT-BR
- **Viabilidade**: ferramentas e libs disponiveis para exemplos praticos
- **Manutenibilidade**: topicos que nao ficam obsoletos rapidamente

---

## Progresso Geral

```
Total planejado: 21 livros
Concluidos: 7 (33%)
Em andamento: 0
Planejados: 14

Linhas escritas: ~352.800
Linhas projetadas: ~900.000+
```

---

## Estrutura do Repositorio

```
DevSecurity/
├── README.md                    # Este arquivo
├── CONTRIBUTING.md               # Guia de contribuicao
├── PROXIMOS-PROJETOS.md         # Este arquivo
├── docs/                         # GitHub Pages
│   ├── index.md
│   ├── book/                     # Livro 1: SDD (C++17)
│   ├── devsecops/                # Livro 2: DevSecOps (Multi-lang)
│   ├── malware/                  # Livro 3: Malware (C++17 + asm)
│   ├── concurrency/              # Livro 4: Concorrencia (C++17/20)
│   ├── cryptography/             # Livro 5: Criptografia (C++17)
│   ├── web/                      # Livro 6: Web Security (JS/TS/Python/Go)
│   └── cmake-book/               # Livro 7: CMake (CMake + C/C++)
├── openspec/                     # SDD artifacts
├── scripts/                      # Scripts auxiliares
└── .mimocode/                    # Skills e commands
```

---

## Contribuicao

Se quiser sugerir um novo livro, melhorar um existente, ou reportar erro tecnico:
- Abra uma **Issue** no repositorio
- Para correcoes de codigo: PRs sao bem-vindos
- Para novos temas: abra Discussion primeiro
