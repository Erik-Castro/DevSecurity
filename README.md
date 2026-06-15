---
layout: default
title: "DevSecurity"
---

# DevSecurity — Livros de Desenvolvimento Seguro

> **Seguranca nao e um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositorio

Este e o repositorio central da colecao **DevSecurity**: livros tecnicos de desenvolvimento de software seguro, escritos em portugues, com foco pratico em **C++ moderno (C++17/20)** e arquitetura de sistemas.

O objetivo e preencher a lacuna entre teoria de seguranca e pratica de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padroes de codigo seguro, verificavel e pronto para producao.

### Numeros da Colecao

| Metrica | Valor |
|---------|-------|
| Livros publicados | 7 |
| Livros na fila | 1 |
| Total de capitulos | 126 |
| Total de linhas | ~350.000+ |
| CVEs documentados | 350+ |
| Linguagens | C++17/20, Python, Bash, YAML, Go, Assembly, JS/TS, CMake |
| Idioma | Portugues (PT-BR) para texto, Ingles para codigo |

---

## Livros Publicados

### 1. Security-Driven Development com C++17

> *Desenvolvimento Seguro orientado a Seguranca — 17 capitulos | ~48.500 linhas | 100+ CVEs | 200+ exemplos*

**Conteudo:**
- **Fundamentos**: SDD, Secure SDLC, Threat Modeling (STRIDE/PASTA/DREAD), OWASP Top 10 + CWE Top 25 mapeados para C++
- **Codificacao Segura**: Principios (Saltzer & Schroeder), Memory Safety, Error Handling, Input Validation
- **Dominios Criticos**: AuthN/AuthZ, Criptografia (AES-GCM, ChaCha20-Poly1305, X25519, TLS 1.3, PQC), Rede, Database, API, Concorrencia
- **Verificacao**: SAST/DAST, Fuzzing (libFuzzer/AFL++), Penetration Testing, Mutation Testing
- **Operacao**: Compliance (ASVS, SAMM, CERT, MISRA, ISO 27001, LGPD), Incident Response, Hardening, Supply Chain (SBOM, Sigstore, Reproducive Builds)

**Casos reais documentados**: Heartbleed, Shellshock, EternalBlue, Log4Shell, Spectre/Meltdown, SolarWinds, xz-utils backdoor, Qualcomm GPU UAF, Android Kernel, Samsung RKP, Equifax, Target, Stuxnet, Colonial Pipeline, LastPass, e mais.

[Leia online](docs/book/INDICE.md) — indice completo com links para todos os capitulos.

---

### 2. DevSecOps na Pratica

> *Pipeline CI/CD Seguro, Ferramentas, Containers, Cloud, Kubernetes e Compliance — 18 capitulos | ~52.300 linhas | 60+ CVEs | Bash, Python, YAML, Docker, HCL, Go*

**Conteudo:**
- **Pipeline Seguro**: GitHub Actions, GitLab CI, Jenkins hardening, OIDC, secret management, artifact signing
- **Shift-Left**: IDE integration, pre-commit hooks, CodeQL, Semgrep, SAST/DAST/SCA integrados
- **Container & Cloud**: Docker hardening, Kubernetes (Pod Security, RBAC, Network Policies, OPA/Gatekeeper, Falco), AWS/Azure/GCP security
- **Supply Chain**: GitOps (ArgoCD/Flux), SLSA, Sigstore/Cosign, SBOM (SPDX/CycloneDX), xz-utils post-mortem
- **Observabilidade**: ELK/Wazuh, Prometheus/Grafana, Falco, threat hunting, MTTD/MTTR
- **Operacao**: Incident response runbooks, rollback, chaos engineering, compliance as code (SOC 2, PCI DSS, LGPD/GDPR, CIS Benchmarks)

**Casos reais**: SolarWinds, Codecov, 3CX, xz-utils, Travis CI, Log4Shell, Capital One, Equifax, Target, Colonial Pipeline, Uber, Tesla K8s, Docker Hub crypto-miners.

[Leia online](docs/devsecops/INDICE.md) — indice completo com links para todos os capitulos.

---

### 3. Engenharia e Analise de Malware em C++

> *Reverse Engineering, Analise Estatica/Dinamica, Debugging, Ransomware, Rootkits, Exploits — 18 capitulos | ~55.600 linhas | 100+ malwares documentados | C++17 + Assembly*

**Conteudo:**
- **Fundamentos**: PE/ELF/Mach-O parsing, x86/x64 assembly, calling conventions, syscalls, compiler artifacts
- **Ferramentas**: IDA Pro (IDAPython), Ghidra (scripts), Radare2/Cutter, GDB/GEF/PEDA, x64dbg, WinDbg
- **Analise Estatica**: Strings (XOR/RC4), imports/exports, packer detection (UPX/Themida/VMProtect), entropy, YARA rules, IOC extraction
- **Analise Dinamica**: API monitoring, C2 traffic analysis, sandbox automation (Cuckoo/CAPE), anti-sandbox evasion
- **Debugging**: Breakpoints, memory dumping, anti-debug bypass, scripting (GDB Python, x64dbg)
- **Malware por Categoria**: Ransomware (WannaCry, NotPetya, Conti, LockBit, BlackCat), Rootkits/Bootkits (UEFI MoonBounce, BlackLotus), Exploits/Shellcode (EternalBlue, ROP chains), Network (C2, DGA)
- **Automacao**: Custom sandbox framework, batch analysis, MISP/STIX integration
- **Ferramentas C++**: LIEF, entropy, compiler/packer detection, CFG, signature matching

**Casos documentados**: Stuxnet, WannaCry, NotPetya, Emotet, TrickBot, Cobalt Strike, Mirai, SolarWinds SUNBURST, BlackCat/ALPHV, LockBit, Conti, REvil, Ryuk, Cl0p, MoonBounce, BlackLotus, EternalBlue, Log4Shell, ProxyLogon, PrintNightmare, BlueKeep, Conficker, GameOver Zeus.

[Leia online](docs/malware/INDICE.md) — indice completo com links para todos os capitulos.

---

### 4. Concorrencia e Paralelismo Seguro em C++

> *Modelo de Memoria, Lock-Free, Padroes, Debugging, Performance, GPU — 18 capitulos | ~19.700 linhas | CVEs de concorrencia | C++17/20*

**Conteudo:**
- **Fundamentos**: Modelo de memoria C++ (memory_order, happens-before, data races), Threads e sincronizacao
- **Avancado**: Programacao Lock-Free (CAS, ABA, hazard pointers, RCU), Deadlocks/Livelocks/Starvation
- **Paralelismo**: Thread pools, std::async, executors, std::execution (par_unseq), OpenMP
- **Otimizacao**: False sharing, cache coherence (MESI), NUMA, containers concorrentes
- **Async**: Futures, promises, continuations, when_all, coroutines C++20
- **Testes e Debugging**: ThreadSanitizer, model checking, stress testing, GDB, replay debugging
- **Heterogeneo**: SIMD (AVX), CUDA, SYCL, OpenCL

**CVEs documentados**: CVE-2016-0728, CVE-2019-11135, CVE-2021-4034, CVE-2014-0160 (Heartbleed).

[Leia online](docs/concurrency/INDICE.md) — indice completo com links para todos os capitulos.

---

### 5. Criptografia Engenheira em C++

> *Constant-Time, Side-Channels, HSM, TLS 1.3, PQC, Key Management — 18 capitulos | ~66.400 linhas | 20+ CVEs | C++17*

**Conteudo:**
- **Fundamentos**: Primitivas criptograficas, bibliotecas (OpenSSL 3.x, libsodium, Botan)
- **Constant-Time**: Timing attacks, cache-timing, techniques C++17, assembly intrinsics
- **Side-Channel Attacks**: Power analysis, EM emanation, cache attacks, Spectre/Meltdown, Hertzbleed, Downfall
- **HSM e Hardware Security**: PKCS#11, cloud HSMs, TPM 2.0, Intel SGX, ARM TrustZone
- **TLS 1.3**: Handshake protocol, key schedule, 0-RTT, OpenSSL 3.x implementation
- **Pos-Quantico**: ML-KEM, ML-DSA, SLH-DSA, hybrid schemes, migration strategy
- **Key Management**: Key lifecycle, wrapping, threshold crypto, Vault/KMS integration
- **Criptografia Avancada**: FHE, Zero-Knowledge Proofs, Formal Verification
- **Compliance**: FIPS 140-3, Common Criteria, LGPD, GDPR, ICP-Brasil, PCI DSS

**CVEs documentados**: Heartbleed, CVE-2008-0166, CVE-2019-1547, Lucky13, Minerva, ROCA, CVE-2019-11091, Spectre-BHB, Raccoon Attack, ROBOT Attack, CVE-2022-36760, CVE-2022-4304.

[Leia online](docs/cryptography/INDICE.md) — indice completo com links para todos os capitulos.

---

### 6. Desenvolvimento Seguro na Web

> *OWASP Top 10, XSS, SQLi, CSRF, Auth, API Security, Containers, DevSecOps — 18 capitulos | ~57.800 linhas | 20+ CVEs | JS/TS, Python, Go*

**Conteudo:**
- **Fundamentos**: HTTP security, CORS, CSP, Same-Origin Policy, TLS/HTTPS
- **OWASP Top 10**: Todas as 10 categorias com CVEs e codigo corrigido
- **Injection**: SQL Injection, NoSQL, Command Injection, LDAP Injection
- **Client-Side**: XSS (Reflected, Stored, DOM-based), CSRF, Clickjacking
- **Authentication**: Password storage (bcrypt, Argon2id), MFA, OAuth 2.0, JWT, WebAuthn
- **API Security**: REST, GraphQL, gRPC, rate limiting, OWASP API Security Top 10
- **JavaScript Security**: CSP, Trusted Types, SRI, prototype pollution, Node.js security
- **Server-Side**: Django, Flask, Express.js, Go security patterns
- **Containers & DevSecOps**: Docker security, Kubernetes, CI/CD pipelines, SAST/DAST
- **Testing**: Penetration testing methodology, Burp Suite, OWASP ZAP
- **Compliance**: OWASP ASVS, PCI DSS, LGPD/GDPR, SOC 2

**CVEs documentados**: Log4Shell, MOVEit, Equifax (Apache Struts), Zerologon, Heartbleed, Spring4Shell, XZ Utils backdoor.

[Leia online](docs/web/INDICE.md) — indice completo com links para todos os capitulos.

---

### 7. CMake Seguro e Build Systems

> *Compiler Flags, Sanitizers, Hardening, Reproducible Builds, Supply Chain — 18 capitulos | ~52.500 linhas | 6+ CVEs | CMake 3.20+, C++17/20*

**Conteudo:**
- **Fundamentos do CMake**: Target model, properties, generator expressions, funcoes
- **Flags de Seguranca**: Stack protector, FORTIFY_SOURCE, PIE, RELRO, format strings
- **Sanitizers**: ASan, TSan, UBSan, MSan — configuracao e uso em CI/CD
- **Hardening de Binarios**: RELRO, ASLR, strip, code signing, RPATH
- **Analise Estatica**: clang-tidy, cppcheck, Facebook Infer integration
- **Builds Reproduziveis**: Deterministic builds, SOURCE_DATE_EPOCH, Docker
- **Dependencias**: find_package seguro, FetchContent, vcpkg, Conan, lock files
- **Supply Chain**: SBOM (SPDX/CycloneDX), Sigstore, Cosign, SLSA
- **Cross-Compilation**: Toolchains, sysroots, secure cross-builds
- **Testing**: CTest, GoogleTest, Catch2, fuzzing, coverage, benchmarking
- **CI/CD**: GitHub Actions, GitLab CI, security gates, code signing
- **Boas Praticas**: 30+ anti-patterns, checklists, decision trees, templates

**CVEs documentados**: CVE-2024-3094 (XZ Utils backdoor), CVE-2021-44228 (Log4Shell), CVE-2019-11091 (MDS).

[Leia online](docs/cmake-book/INDICE.md) — indice completo com links para todos os capitulos.

---

## Proxima Publicacao

| Livro | Foco | Status |
|-------|------|--------|
| **WebAssembly Seguro** | Wasm sandboxing, WASI, component model, memory safety, browser vs server security | Na fila |

---

## Para Quem Escrevo

- **Desenvolvedores C++** (intermediario a avancado) que querem codigo seguro por design
- **Engenheiros de Seguranca** que auditam/revisam codigo nativo
- **Arquitetos & Tech Leads** que definem padroes e processos de seguranca
- **Analistas de Malware / Threat Researchers** que fazem engenharia reversa
- **DevOps / Platform Engineers** que constroem pipelines seguros
- **Estudantes avancados** de ciencia da computacao / engenharia de software

**Pre-requisitos**: C++17 (templates, RAII, smart pointers, atomics), Linux/WSL2, CMake, compilador moderno (GCC 12+, Clang 16+, MSVC 2022+).

---

## Como Usar os Livros

Cada livro e **autocontido**, mas a sequencia recomendada por perfil:

```
Desenvolvedor:  SDD (1-5) -> SDD (6-12) -> DevSecOps (1-4) -> DevSecOps (5-9)
Eng. Seguranca: Malware (1-4) -> Malware (5-10) -> SDD (13-17) -> DevSecOps (10-17)
DevOps/Platform: DevSecOps (1-9) -> DevSecOps (10-17) -> Malware (14-15)
Arquiteto:      SDD (1-3) -> DevSecOps (1-3) -> Malware (17) -> Todos os Cap 17
Concorrencia:   SDD (1-3) -> Concorrencia (01-03) -> Concorrencia (04-10) -> Concorrencia (11-17)
Criptografia:   SDD (1-3) -> Criptografia (01-03) -> Criptografia (04-09) -> Criptografia (10-17)
CMake:          CMake (01-03) -> CMake (04-08) -> CMake (09-12) -> CMake (13-17)
Web:            SDD (1-3) -> Web (01-03) -> Web (04-10) -> Web (11-17)
```

---

## Estrutura do Repositorio

```
DevSecurity/
├── README.md                    # Este arquivo
├── CONTRIBUTING.md               # Guia de contribuicao
├── PROXIMOS-PROJETOS.md         # Roadmap e backlog
├── docs/                         # GitHub Pages
│   ├── index.md                  # Pagina inicial do site
│   ├── book/                     # Livro 1: Security-Driven Development (C++17)
│   ├── devsecops/                # Livro 2: DevSecOps na Pratica (Multi-lang)
│   ├── malware/                  # Livro 3: Engenharia e Analise de Malware (C++17 + asm)
│   ├── concurrency/              # Livro 4: Concorrencia e Paralelismo Seguro (C++17/20)
│   ├── cryptography/             # Livro 5: Criptografia Engenheira em C++ (C++17)
│   ├── web/                      # Livro 6: Desenvolvimento Seguro na Web (JS/TS/Python/Go)
│   ├── cmake-book/               # Livro 7: CMake Seguro e Build Systems (CMake + C/C++)
│   ├── javascripts/              # Assets do site
│   └── stylesheets/              # Assets do site
├── openspec/                     # SDD artifacts
├── scripts/                      # Scripts auxiliares
└── .mimocode/                    # Skills e commands
```

---

## Contribuicoes

Este e um projeto de autoria individual, mas **feedback e bem-vindo**:

- **Issues**: Erros tecnicos, CVEs faltando, exemplos que nao compilam
- **Discussoes**: Sugestoes de temas, capitulos, formatos
- **Traducoes**: Se quiser traduzir para ingles/espanhol, abra issue primeiro

---

## Licenca

**CC BY-NC-SA 4.0** — Compartilhe, adapte, cite a fonte. Uso comercial requer autorizacao.

---

## Autor

Desenvolvedor de sistemas, foco em seguranca de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com seguranca de verdade."*

---

Se este material te ajudou, deixe uma estrela no repositorio — ajuda outros desenvolvedores a encontrarem conteudo de qualidade em portugues.
