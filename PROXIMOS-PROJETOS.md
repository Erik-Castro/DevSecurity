---
layout: default
title: "Proximos Projetos"
---

# Proximos Projetos — Livros Open-Source DevSecurity

> Diretrizes do projeto: livros tecnicos gratuitos em Markdown, linguagem PT-BR para texto, codigo em ingles, minimo 800 linhas por capitulo, 17+ capitulos, com casos publicos documentados (CVEs).

---

## Livros Concluidos

### Livro 1: Security-Driven Development (CONCLUIDO)
- **17 capitulos** | ~48.500 linhas | **C++17**
- [Indice](docs/book/INDICE.md)

### Livro 2: DevSecOps na Pratica (CONCLUIDO)
- **18 capitulos** | ~52.300 linhas | **Bash, Python, YAML, Docker, HCL, Go**
- [Indice](docs/devsecops/INDICE.md)

### Livro 3: Engenharia e Analise de Malware em C++ (CONCLUIDO)
- **18 capitulos** | ~55.600 linhas | **C++17 + Assembly**
- [Indice](docs/malware/INDICE.md)

### Livro 4: Concorrencia e Paralelismo Seguro em C++ (CONCLUIDO)
- **18 capitulos** | ~19.700 linhas | **C++17/20**
- [Indice](docs/concurrency/INDICE.md)

### Livro 5: Criptografia Engenheira em C++ (CONCLUIDO)
- **18 capitulos** | ~66.400 linhas | **C++17**
- [Indice](docs/cryptography/INDICE.md)

### Livro 6: Desenvolvimento Seguro na Web (CONCLUIDO)
- **18 capitulos** | ~57.800 linhas | **JS/TS, Python, Go**
- [Indice](docs/web/INDICE.md)

### Livro 7: CMake Seguro e Build Systems (CONCLUIDO)
- **18 capitulos** | ~52.500 linhas | **CMake 3.20+, C++17/20**
- [Indice](docs/cmake-book/INDICE.md)

### Livro 8: GitHub Actions Pipelines Seguros (CONCLUIDO)
- **18 capitulos** | ~49.000 linhas | **YAML, Bash**
- [Indice](docs/github-actions/INDICE.md)

---

## Backlog de Livros Planejados

### Tier 1 — Alta demanda

| # | Titulo | Foco | Linguagem | Prioridade |
|---|--------|------|-----------|------------|
| 9 | **WebAssembly Seguro** | Wasm sandboxing, WASI, memory safety | Rust, C++, Wat | Alta |
| 10 | **Fuzzing & Property-Based Testing** | libFuzzer/AFL++, OSS-Fuzz, CI/CD | C++17 | Alta |
| 11 | **Security Code Review Handbook** | Checklists, anti-patterns, automacao | C++17 | Media |
| 12 | **LGPD/GDPR para Engenheiros** | Privacy by Design, DPIA, breach notification | Conceitual + codigo | Media |
| 13 | **Secure Architecture Patterns** | Zero Trust, threat modeling, capability-based | Conceitual | Media |

### Tier 2 — Nichos

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 14 | **Firmware & Embedded Security** | Bootloader, secure boot, TPM, IoT | C + C++17 |
| 15 | **Side-Channel Analysis & Mitigation** | Timing, cache, power, EM attacks | C++17 + Assembly |
| 16 | **Binary Exploitation** | ROP/JOP, heap exploitation, kernel | C++17 + Assembly |
| 17 | **Threat Hunting & DFIR** | Forensics, memory analysis, timeline | Python + C++ |

### Tier 3 — Alcance

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 18 | **Security Testing Automation** | CI/CD gates, mutation testing | Multi |
| 19 | **Secure DevOps at Scale** | Monorepo security, compliance automation | Bash/YAML/HCL |

### Tier 4 — Linguagens

| # | Titulo | Foco | Linguagem |
|---|--------|------|-----------|
| 20 | **Secure Coding in Rust** | Ownership, unsafe, FFI, crypto | Rust |
| 21 | **Python para Seguranca** | Automacao, tooling, analysis | Python |
| 22 | **Go for Security Engineering** | Concurrency, networking, cloud | Go |

---

## Progresso Geral

```
Total planejado: 22 livros
Concluidos: 8 (36%)
Em andamento: 0
Planejados: 14

Linhas escritas: ~401.900
```

---

## Estrutura do Repositorio

```
DevSecurity/
├── README.md
├── CONTRIBUTING.md
├── PROXIMOS-PROJETOS.md
├── docs/
│   ├── book/           # Livro 1: SDD
│   ├── devsecops/      # Livro 2: DevSecOps
│   ├── malware/        # Livro 3: Malware
│   ├── concurrency/    # Livro 4: Concorrencia
│   ├── cryptography/   # Livro 5: Criptografia
│   ├── web/            # Livro 6: Web Security
│   ├── cmake-book/     # Livro 7: CMake
│   └── github-actions/ # Livro 8: GitHub Actions
├── epub/               # Versoes EPUB
├── openspec/           # SDD artifacts
└── scripts/            # Scripts auxiliares
```
