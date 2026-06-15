# Próximos Projetos — Livros Open-Source DevSecurity

> Diretrizes do projeto: livros técnicos gratuitos em Markdown, linguagem PT-BR para texto, código em inglês (C++17 ou linguagem apropriada), mínimo 800 linhas por capítulo, 17+ capítulos, com casos públicos documentados (CVEs).

---

## ✅ Livros Concluídos

### Livro 1: Security-Driven Development (CONCLUÍDO)
- **17 capítulos** | ~48.500 linhas | **C++17**
- [Índice](book/INDICE.md) | [Diretório](book/)
- Foco: SDD, Secure SDLC, Memory Safety, AuthN/AuthZ, Crypto, Network, DB, API, Concurrency, Testing, Compliance, Hardening
- 100+ CVEs documentados

### Livro 2: DevSecOps na Prática (CONCLUÍDO)
- **18 capítulos** | ~52.300 linhas | **Bash, Python, YAML, Docker, HCL, Go**
- [Índice](devsecops/INDICE.md) | [Diretório](devsecops/)
- Foco: CI/CD Security, SAST/DAST/SCA, Containers, K8s, Cloud, GitOps, Supply Chain, Monitoring, Incident Response, Compliance
- 60+ casos de segurança documentados

### Livro 3: Engenharia e Análise de Malware em C++ (CONCLUÍDO)
- **18 capítulos** | ~55.600 linhas | **C++17 + Assembly**
- [Índice](malware/INDICE.md) | [Diretório](malware/)
- Foco: Reverse Engineering, Static/Dynamic Analysis, Debugging, Ransomware, Rootkits, Exploits, YARA, Automation
- 100+ malwares documentados

### Livro 4: Concorrência e Paralelismo Seguro em C++ (CONCLUÍDO)
- **18 capítulos** | ~19.700 linhas | **C++17/20**
- [Índice](concurrency/INDICE.md) | [Diretório](concurrency/)
- Foco: Modelo de memória, Lock-Free, Deadlocks, Thread Pools, Paralelismo, Cache, Containers concorrentes, Futures/Coroutines, Testes, Debugging, Performance, SIMD/GPU, Boas Práticas
- CVEs de concorrência documentados (CVE-2016-0728, CVE-2019-11135, CVE-2021-4034, Heartbleed)

### Livro 5: Criptografia Engenheira em C++ (CONCLUÍDO)
- **18 capítulos** | ~66.400 linhas | **C++17**
- [Índice](cryptography/INDICE.md) | [Diretório](cryptography/)
- Foco: Constant-Time, Side-Channels, HSM, TLS 1.3, PQC (ML-KEM/ML-DSA), Key Management, FHE, ZKP, Formal Verification, Testing, Compliance
- 20+ CVEs documentados (Heartbleed, ROCA, Minerva, Spectre, Lucky13, etc.)

---

## 📋 Backlog de Livros Planejados

### Tier 1 — Alta demanda e sinergia direta

| # | Título | Foco | Linguagem | Prioridade |
|---|--------|------|-----------|------------|
| 6 | **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++ avançado, corpus management, OSS-Fuzz integration, CI/CD | C++17 | Alta |
| 7 | **Supply Chain Security & Reproducible Builds** | SBOM (SPDX/CycloneDX), SLSA, Sigstore, in-toto, reproducible builds, xz-utils post-mortem | C++17 + Bash/YAML | Alta |
| 8 | **Desenvolvimento Seguro na Web** | XSS, CSRF, SQL Injection, OWASP Top 10, secure APIs, auth, session management, input validation | JS/TS, Python, Go | Alta |
| 9 | **CMake Seguro e Build Systems** | CMake hardening, reproducible builds, supply chain para builds, sanitizers, cross-compilation, CI/CD | CMake + C/C++ | Alta |
| 10 | **WebAssembly Seguro** | Wasm sandboxing, WASI, component model, security model, browser vs server, memory safety | Rust, C++, Wat | Alta |
| 11 | **Security Code Review Handbook** | Checklists práticos, anti-patterns, como revisar PRs de segurança, automação | C++17 | Média |
| 12 | **LGPD/GDPR para Engenheiros** | Privacy by Design em código, consentimento, criptografia, DPIA, breach notification | Conceitual + código | Média |
| 13 | **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security, language-agnostic | Conceitual | Média |

### Tier 2 — Nichos com pouca cobertura em PT-BR

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 14 | **Reverse Engineering e Análise de Malware Avançado** | VM-based obfuscation, deobfuscation, VMProtect/Themida analysis, custom VM | C++17 + Assembly |
| 15 | **Criptografia Pós-Quântica em C++** | ML-KEM, ML-DSA, SLH-DSA, hybrid schemes, migration strategies, liboqs integration | C++17 |
| 16 | **Firmware & Embedded Security** | Bootloader security, secure boot, TPM, ARM TrustZone, IoT device security | C + C++17 |
| 17 | **Side-Channel Analysis & Mitigation** | Timing, cache, power, EM attacks, constant-time programming, leakage detection | C++17 + Assembly |

### Tier 3 — Ampliam o alcance do projeto

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 18 | **Binary Exploitation & Mitigation Bypass** | Advanced ROP/JOP, heap exploitation, CFG/ACG bypass, kernel exploitation | C++17 + Assembly |
| 19 | **Threat Hunting & DFIR** | Log analysis, memory forensics (Volatility), network forensics, timeline analysis | Python + C++ |
| 20 | **Security Testing Automation** | CI/CD security gates, mutation testing, contract testing, chaos engineering | Multi |
| 21 | **Secure DevOps at Scale** | Monorepo security, multi-team pipelines, policy as code, compliance automation | Bash/YAML/HCL |

### Tier 4 — Expansão de linguagem

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 22 | **Secure Coding in Rust** | Ownership/borrowing for security, unsafe patterns, FFI, crypto in Rust | Rust |
| 23 | **Python para Segurança de Software** | Automação, análise de dados, tooling, malware analysis scripting | Python |
| 24 | **Go for Security Engineering** | Concurrent security tools, networking, cloud security, CLI tools | Go |

---

## Critérios de Seleção

- **Demanda**: livros com maior audiência potencial primeiro
- **Sinergia**: livros que complementam os anteriores
- **Diferenciação**: pouca cobertura gratuita em PT-BR
- **Viabilidade**: ferramentas e libs disponíveis para exemplos práticos
- **Manutenibilidade**: tópicos que não ficam obsoletos rapidamente

---

## Progresso Geral

```
Total planejado: 24 livros
Concluídos: 5 (21%)
Em andamento: 0
Planejados: 19

Linhas escritas: ~242.500
Linhas projetadas: ~1.200.000+
```

---

## Próximos 3 Livros na Fila

| # | Livro | Diretório | Foco Principal |
|---|-------|-----------|----------------|
| 6 | **Desenvolvimento Seguro na Web** | `web/` | OWASP Top 10, XSS/CSRF/SQLi, secure APIs, auth, session management, input validation |
| 7 | **CMake Seguro e Build Systems** | `cmake-book/` | CMake hardening, reproducible builds, supply chain para builds, sanitizers, cross-compilation |
| 8 | **WebAssembly Seguro** | `wasm/` | Wasm sandboxing, WASI, component model, memory safety, browser vs server security |

---

## Estrutura do Repositório

```
DevSecurity/
├── README.md                    # Este arquivo atualizado
├── PROXIMOS-PROJETOS.md         # Este arquivo
├── book/                        # Security-Driven Development (C++17)
│   ├── INDICE.md
│   └── 00-17 chapters
├── devsecops/                   # DevSecOps na Prática (Multi-lang)
│   ├── INDICE.md
│   └── 00-17 chapters
├── malware/                     # Engenharia e Análise de Malware (C++17 + asm)
│   ├── INDICE.md
│   └── 00-17 chapters
├── concurrency/                 # Concorrência e Paralelismo Seguro (C++17/20)
│   ├── INDICE.md
│   └── 00-17 chapters
├── cryptography/                # Criptografia Engenheira em C++ (C++17)
│   ├── INDICE.md
│   └── 00-17 chapters
├── web/                         # Desenvolvimento Seguro na Web (JS/TS/Python/Go)
│   └── (próximo)
├── cmake-book/                  # CMake Seguro e Build Systems
│   └── (próximo)
├── wasm/                        # WebAssembly Seguro (Rust/C++/Wat)
│   └── (próximo)
└── openspec/                    # SDD artifacts
```

---

## Contribuição

Se quiser sugerir um novo livro, melhorar um existente, ou reportar erro técnico:
- Abra uma **Issue** no repositório
- Para correções de código: PRs são bem-vindos
- Para novos temas: abra Discussion primeiro