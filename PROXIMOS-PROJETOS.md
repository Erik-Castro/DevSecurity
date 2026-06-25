---
layout: default
title: "Próximos Projetos"
---

# Próximos Projetos — Livros Open-Source DevSecurity

> Diretrizes do projeto: livros técnicos gratuitos em Markdown, linguagem PT-BR para texto, código em inglês, mínimo 800 linhas por capítulo, 17+ capítulos, com casos públicos documentados (CVEs).

---

## Livros Concluídos

### Livro 1: Security-Driven Development (CONCLUÍDO)
- **17 capítulos** | ~48.500 linhas | **C++17**
- [Índice](docs/book/INDICE.md)

### Livro 2: DevSecOps na Prática (CONCLUÍDO)
- **18 capítulos** | ~52.300 linhas | **Bash, Python, YAML, Docker, HCL, Go**
- [Índice](docs/devsecops/INDICE.md)

### Livro 3: Engenharia e Análise de Malware em C++ (CONCLUÍDO)
- **18 capítulos** | ~55.600 linhas | **C++17 + Assembly**
- [Índice](docs/malware/INDICE.md)

### Livro 4: Concorrência e Paralelismo Seguro em C++ (CONCLUÍDO)
- **18 capítulos** | ~19.700 linhas | **C++17/20**
- [Índice](docs/concurrency/INDICE.md)

### Livro 5: Criptografia Engenheira em C++ (CONCLUÍDO)
- **18 capítulos** | ~66.400 linhas | **C++17**
- [Índice](docs/cryptography/INDICE.md)

### Livro 6: Desenvolvimento Seguro na Web (CONCLUÍDO)
- **18 capítulos** | ~57.800 linhas | **JS/TS, Python, Go**
- [Índice](docs/web/INDICE.md)

### Livro 7: CMake Seguro e Build Systems (CONCLUÍDO)
- **18 capítulos** | ~52.500 linhas | **CMake 3.20+, C++17/20**
- [Índice](docs/cmake-book/INDICE.md)

### Livro 8: GitHub Actions Pipelines Seguros (CONCLUÍDO)
- **18 capítulos** | ~49.000 linhas | **YAML, Bash**
- [Índice](docs/github-actions/INDICE.md)

### Livro 9: WebAssembly Seguro (CONCLUÍDO)
- **18 capítulos** | ~76.300 linhas | **Rust, C++, WAT**
- [Índice](docs/wasm/INDICE.md)

### Livro 10: Autenticação, Autorização e Controle de Acesso (CONCLUÍDO)
- **18 capítulos** | ~49.500 linhas | **Python, JavaScript, Go**
- [Índice](docs/authz/INDICE.md)

### Livro 11: IA do Zero: ML em C++, Fortran e Rust (CONCLUÍDO)
- **18 capítulos** | ~52.000 linhas | **C++17, Rust, Fortran**
- [Índice](docs/ai-from-scratch/INDICE.md)

---

## Backlog de Livros Planejados

### Tier 1 — Alta demanda

| # | Título | Foco | Linguagem | Prioridade |
|---|--------|------|-----------|------------|
| 10 | **Fuzzing & Property-Based Testing** | libFuzzer/AFL++, OSS-Fuzz, CI/CD | C++17 | Alta |
| 11 | **Security Code Review Handbook** | Checklists, anti-patterns, automação | C++17 | Média |
| 12 | **LGPD/GDPR para Engenheiros** | Privacy by Design, DPIA, breach notification | Conceitual + código | Média |
| 13 | **Secure Architecture Patterns** | Zero Trust, threat modeling, capability-based | Conceitual | Média |

### Tier 2 — Nichos

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 14 | **Firmware & Embedded Security** | Bootloader, secure boot, TPM, IoT | C + C++17 |
| 15 | **Side-Channel Analysis & Mitigation** | Timing, cache, power, EM attacks | C++17 + Assembly |
| 16 | **Binary Exploitation** | ROP/JOP, heap exploitation, kernel | C++17 + Assembly |
| 17 | **Threat Hunting & DFIR** | Forensics, memory analysis, timeline | Python + C++ |

### Tier 3 — Alcance

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 18 | **Security Testing Automation** | CI/CD gates, mutation testing | Multi |
| 19 | **Secure DevOps at Scale** | Monorepo security, compliance automation | Bash/YAML/HCL |

### Tier 4 — Linguagens

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 20 | **Secure Coding in Rust** | Ownership, unsafe, FFI, crypto | Rust |
| 21 | **Python para Segurança** | Automação, tooling, analysis | Python |
| 22 | **Go for Security Engineering** | Concurrency, networking, cloud | Go |

---

## Progresso Geral

```
Total planejado: 22 livros
Concluidos: 11 (50%)
Em andamento: 0
Planejados: 11

Linhas escritas: ~579.700
```

---

## Estrutura do Repositório

```
DevSecurity/
├── README.md
├── CONTRIBUTING.md
├── PROXIMOS-PROJETOS.md
├── docs/
│   ├── book/           # Livro 1: SDD
│   ├── devsecops/      # Livro 2: DevSecOps
│   ├── malware/        # Livro 3: Malware
│   ├── concurrency/    # Livro 4: Concorrência
│   ├── cryptography/   # Livro 5: Criptografia
│   ├── web/            # Livro 6: Web Security
│   ├── cmake-book/     # Livro 7: CMake
│   ├── github-actions/ # Livro 8: GitHub Actions
│   ├── wasm/           # Livro 9: WebAssembly
│   └── authz/       # Livro 10: Auth/AuthZ
│   └── ai-from-scratch/ # Livro 11: IA do Zero (C++/Rust/Fortran)
├── epub/               # Versões EPUB
├── openspec/           # SDD artifacts
└── scripts/            # Scripts auxiliares
```
