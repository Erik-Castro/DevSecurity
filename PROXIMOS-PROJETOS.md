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

---

## 📋 Backlog de Livros Planejados

### Tier 1 — Alta demanda e sinergia direta

| # | Título | Foco | Linguagem | Prioridade |
|---|--------|------|-----------|------------|
| 4 | **Secure C++ Concurrency & Parallelism** | Data races, lock-free, actor model, TSan, false sharing, side-channels | C++17/20 | Alta |
| 5 | **Cryptography Engineering in C++** | Constant-time, side-channels, HSM, TLS 1.3 internals, PQC migration, key management | C++17 | Alta |
| 6 | **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++ avançado, corpus management, OSS-Fuzz integration, CI/CD | C++17 | Alta |
| 7 | **Supply Chain Security & Reproducible Builds** | SBOM (SPDX/CycloneDX), SLSA, Sigstore, in-toto, reproducible builds, xz-utils post-mortem | C++17 + Bash/YAML | Alta |
| 8 | **Security Code Review Handbook** | Checklists práticos, anti-patterns, como revisar PRs de segurança, automação | C++17 | Média |
| 9 | **LGPD/GDPR para Engenheiros** | Privacy by Design em código, consentimento, criptografia, DPIA, breach notification | Conceitual + código | Média |
| 10 | **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security, language-agnostic | Conceitual | Média |

### Tier 2 — Nichos com pouca cobertura em PT-BR

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 11 | **Reverse Engineering e Análise de Malware Avançado** | VM-based obfuscation, deobfuscation, VMProtect/Themida analysis, custom VM | C++17 + Assembly |
| 12 | **Criptografia Pós-Quântica em C++** | ML-KEM, ML-DSA, SLH-DSA, hybrid schemes, migration strategies, liboqs integration | C++17 |
| 13 | **Firmware & Embedded Security** | Bootloader security, secure boot, TPM, ARM TrustZone, IoT device security | C + C++17 |
| 14 | **Side-Channel Analysis & Mitigation** | Timing, cache, power, EM attacks, constant-time programming, leakage detection | C++17 + Assembly |

### Tier 3 — Ampliam o alcance do projeto

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 15 | **Binary Exploitation & Mitigation Bypass** | Advanced ROP/JOP, heap exploitation, CFG/ACG bypass, kernel exploitation | C++17 + Assembly |
| 16 | **Threat Hunting & DFIR** | Log analysis, memory forensics (Volatility), network forensics, timeline analysis | Python + C++ |
| 17 | **Security Testing Automation** | CI/CD security gates, mutation testing, contract testing, chaos engineering | Multi |
| 18 | **Secure DevOps at Scale** | Monorepo security, multi-team pipelines, policy as code, compliance automation | Bash/YAML/HCL |

### Tier 4 — Expansão de linguagem

| # | Título | Foco | Linguagem |
|---|--------|------|-----------|
| 19 | **Secure Coding in Rust** | Ownership/borrowing for security, unsafe patterns, FFI, crypto in Rust | Rust |
| 20 | **Python para Segurança de Software** | Automação, análise de dados, tooling, malware analysis scripting | Python |
| 21 | **Go for Security Engineering** | Concurrent security tools, networking, cloud security, CLI tools | Go |

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
Total planejado: 21 livros
Concluídos: 3 (14%)
Em andamento: 0
Planejados: 18

Linhas escritas: ~156.400
Linhas projetadas: ~1.000.000+
```

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
└── (futuros diretórios...)
```

---

## Contribuição

Se quiser sugerir um novo livro, melhorar um existente, ou reportar erro técnico:
- Abra uma **Issue** no repositório
- Para correções de código: PRs são bem-vindos
- Para novos temas: abra Discussion primeiro