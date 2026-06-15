# DevSecurity — Livros de Desenvolvimento Seguro

> **Segurança não é um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositório

Este é o repositório central da coleção **DevSecurity**: livros técnicos de desenvolvimento de software seguro, escritos em português, com foco prático em **C++ moderno (C++17/20/23)** e arquitetura de sistemas.

O objetivo é preencher a lacuna entre teoria de segurança e prática de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padrões de código seguro, verificável e pronto para produção.

---

## 📚 Livros Publicados

### 1. **Security-Driven Development com C++17**
> *Desenvolvimento Seguro orientado à Segurança — 17 capítulos | ~48.500 linhas | 100+ CVEs | 200+ exemplos*

**Conteúdo:**
- **Fundamentos**: SDD, Secure SDLC, Threat Modeling (STRIDE/PASTA/DREAD), OWASP Top 10 + CWE Top 25 mapeados para C++
- **Codificação Segura**: Princípios (Saltzer & Schroeder), Memory Safety, Error Handling, Input Validation
- **Domínios Críticos**: AuthN/AuthZ, Criptografia (AES-GCM, ChaCha20-Poly1305, X25519, TLS 1.3, PQC), Rede, Database, API, Concorrência
- **Verificação**: SAST/DAST, Fuzzing (libFuzzer/AFL++), Penetration Testing, Mutation Testing
- **Operação**: Compliance (ASVS, SAMM, CERT, MISRA, ISO 27001, LGPD), Incident Response, Hardening, Supply Chain (SBOM, Sigstore, Reproducible Builds)

**Casos reais documentados**: Heartbleed, Shellshock, EternalBlue, Log4Shell, Spectre/Meltdown, SolarWinds, xz-utils backdoor, Qualcomm GPU UAF, Android Kernel, Samsung RKP, Equifax, Target, Stuxnet, Colonial Pipeline, LastPass, e mais.

**Ferramentas configuradas**: CMake hardening (GCC/Clang/MSVC), Sanitizers (ASan/TSan/UBSan/MSan), clang-tidy, cppcheck, Facebook Infer, libFuzzer, AFL++, Google Test/Benchmark.

📖 **Leia online**: [`book/INDICE.md`](book/INDICE.md) — índice completo com links para todos os capítulos.

---

### 2. **DevSecOps na Prática**
> *Pipeline CI/CD Seguro, Ferramentas, Containers, Cloud, Kubernetes e Compliance — 18 capítulos | ~52.300 linhas | 60+ CVEs | Bash, Python, YAML, Docker, HCL, Go*

**Conteúdo:**
- **Pipeline Seguro**: GitHub Actions, GitLab CI, Jenkins hardening, OIDC, secret management, artifact signing
- **Shift-Left**: IDE integration, pre-commit hooks, CodeQL, Semgrep, SAST/DAST/SCA integrados
- **Container & Cloud**: Docker hardening, Kubernetes (Pod Security, RBAC, Network Policies, OPA/Gatekeeper, Falco), AWS/Azure/GCP security
- **Supply Chain**: GitOps (ArgoCD/Flux), SLSA, Sigstore/Cosign, SBOM (SPDX/CycloneDX), xz-utils post-mortem
- **Observabilidade**: ELK/Wazuh, Prometheus/Grafana, Falco, threat hunting, MTTD/MTTR
- **Operação**: Incident response runbooks, rollback, chaos engineering, compliance as code (SOC 2, PCI DSS, LGPD/GDPR, CIS Benchmarks)

**Casos reais**: SolarWinds, Codecov, 3CX, xz-utils, Travis CI, Log4Shell, Capital One, Equifax, Target, Colonial Pipeline, Uber, Tesla K8s, Docker Hub crypto-miners.

📖 **Leia online**: [`devsecops/INDICE.md`](devsecops/INDICE.md) — índice completo com links para todos os capítulos.

---

### 3. **Engenharia e Análise de Malware em C++**
> *Reverse Engineering, Análise Estática/Dinâmica, Debugging, Ransomware, Rootkits, Exploits — 18 capítulos | ~55.600 linhas | 100+ malwares documentados | C++17 + Assembly*

**Conteúdo:**
- **Fundamentos**: PE/ELF/Mach-O parsing, x86/x64 assembly, calling conventions, syscalls, compiler artifacts
- **Ferramentas**: IDA Pro (IDAPython), Ghidra (scripts), Radare2/Cutter, GDB/GEF/PEDA, x64dbg, WinDbg
- **Análise Estática**: Strings (XOR/RC4), imports/exports, packer detection (UPX/Themida/VMProtect), entropy, YARA rules, IOC extraction
- **Análise Dinâmica**: API monitoring, C2 traffic analysis, sandbox automation (Cuckoo/CAPE), anti-sandbox evasion
- **Debugging**: Breakpoints, memory dumping, anti-debug bypass, scripting (GDB Python, x64dbg)
- **Malware por Categoria**:
  - **Ransomware**: WannaCry, NotPetya, Conti, LockBit 3.0, BlackCat/ALPHV, key extraction
  - **Rootkits/Bootkits**: User/kernel mode, DKOM, SSDT, UEFI (MoonBounce, BlackLotus)
  - **Exploits/Shellcode**: EternalBlue, ROP chains, heap spraying, format strings, browser exploits
  - **Network**: HTTP/DNS C2, DGA analysis (Emotet, TrickBot, Conficker), crypto analysis
- **Automação**: Custom sandbox framework, batch analysis, MISP/STIX integration
- **Detecção**: YARA rules (Emotet, TrickBot, Cobalt Strike, ransomware families), libyara C++ integration
- **Ferramentas C++**: LIEF, entropy, compiler/packer detection, CFG, signature matching, complete analysis tool

**Casos documentados**: Stuxnet, WannaCry, NotPetya, Emotet, TrickBot, Cobalt Strike, Mirai, SolarWinds SUNBURST, BlackCat/ALPHV, LockBit, Conti, REvil, Ryuk, Cl0p, Necurs, ZeroAccess, TDL4, MoonBounce, BlackLotus, EternalBlue, Log4Shell, ProxyLogon, PrintNightmare, BlueKeep, Conficker, GameOver Zeus.

📖 **Leia online**: [`malware/INDICE.md`](malware/INDICE.md) — índice completo com links para todos os capítulos.

---

### 4. **Concorrência e Paralelismo Seguro em C++**
> *Modelo de Memória, Lock-Free, Padrões, Debugging, Performance, GPU — 18 capítulos | ~19.700 linhas | CVEs de concorrência | C++17/20*

**Conteúdo:**
- **Fundamentos**: Modelo de memória C++ (memory_order, happens-before, data races), Threads e sincronização (std::thread, mutex, locks, C++20 primitives)
- **Avançado**: Programação Lock-Free (CAS, ABA, hazard pointers, RCU), Deadlocks/Livelocks/Starvation (Coffman, detecção, prevenção)
- **Paralelismo**: Thread pools, std::async, executors, std::execution (par_unseq), OpenMP
- **Otimização**: False sharing, cache coherence (MESI), NUMA, containers concorrentes, lock-free queues/hash maps
- **Async**: Futures, promises, continuations, when_all, coroutines C++20 (co_await, generators)
- **Primitivas C++20**: latch, barrier, semaphore, stop_token
- **Testes e Debugging**: ThreadSanitizer, model checking, stress testing, GDB, core dumps, replay debugging
- **Performance**: Amdahl's law, profiling, NUMA tuning, scalable patterns (Actor, CSP, pipeline, fork-join)
- **Heterogêneo**: SIMD (AVX), CUDA, SYCL, OpenCL
- **Boas Práticas**: Checklist, anti-padrões, referências

**CVEs documentados**: CVE-2016-0728 (keyring refcount), CVE-2017-18344 (timer race), CVE-2019-11135 (TSX Async Abort), CVE-2021-4034 (Polkit pkexec race), CVE-2014-0160 (Heartbleed).

📖 **Leia online**: [`concurrency/INDICE.md`](concurrency/INDICE.md) — índice completo com links para todos os capítulos.

---

## 🚀 Próximas Publicações (Em Planejamento)

| Livro | Foco | Status |
|-------|------|--------|
| **Cryptography Engineering in C++** | Constant-time, side-channels, HSM, TLS 1.3 internals, PQC migration, key management | Planejado |
| **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++ avançado, corpus management, OSS-Fuzz integration, CI/CD | Planejado |
| **Supply Chain Security & Reproducible Builds** | SBOM (SPDX/CycloneDX), SLSA, Sigstore, in-toto, reproducible builds, xz-utils post-mortem | Planejado |
| **Security Code Review Handbook** | Checklists práticos, anti-patterns, como revisar PRs de segurança, automação | Planejado |
| **LGPD/GDPR para Engenheiros** | Privacy by Design em código, consentimento, criptografia, DPIA, breach notification | Planejado |
| **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security, language-agnostic | Planejado |

---

## 🎯 Para Quem Escrevo

- **Desenvolvedores C++** (intermediário a avançado) que querem código seguro por design
- **Engenheiros de Segurança** que auditam/revisam código nativo
- **Arquitetos & Tech Leads** que definem padrões e processos de segurança
- **Analistas de Malware / Threat Researchers** que fazem engenharia reversa
- **DevOps / Platform Engineers** que constroem pipelines seguros
- **Estudantes avançados** de ciência da computação / engenharia de software

**Pré-requisitos**: C++17 (templates, RAII, smart pointers, atomics), Linux/WSL2, CMake, compilador moderno (GCC 12+, Clang 16+, MSVC 2022+).

---

## 📖 Como Usar os Livros

Cada livro é **autocontido**, mas a sequência recomendada por perfil:

```
Desenvolvedor:  SDD (1-5) → SDD (6-12) → DevSecOps (1-4) → DevSecOps (5-9)
Eng. Segurança: Malware (1-4) → Malware (5-10) → SDD (13-17) → DevSecOps (10-17)
DevOps/Platform: DevSecOps (1-9) → DevSecOps (10-17) → Malware (14-15)
Arquiteto:      SDD (1-3) → DevSecOps (1-3) → Malware (17) → Todos os Cap 17
Concorrência:   SDD (1-3) → Concorrência (01-03) → Concorrência (04-10) → Concorrência (11-17)
```

Todos os exemplos compilam. Use o `CMakeLists.txt` do [Prefácio SDD](book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a) como base para seus projetos.

---

## 🤝 Contribuições

Este é um projeto de autoria individual, mas **feedback é bem-vindo**:

- **Issues**: Erros técnicos, CVEs faltando, exemplos que não compilam
- **Discussões**: Sugestões de temas, capítulos, formatos
- **Traduções**: Se quiser traduzir para inglês/espanhol, abra issue primeiro

---

## 📄 Licença

**CC BY-NC-SA 4.0** — Compartilhe, adapte, cite a fonte. Uso comercial requer autorização.

---

## 🔗 Links Úteis

### Security-Driven Development
- **Índice completo**: [`book/INDICE.md`](book/INDICE.md)
- **Prefácio (comece aqui)**: [`book/00-prefacio.md`](book/00-prefacio.md)
- **CMake Hardening Reference**: [`book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a`](book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a)
- **CVEs por capítulo**: [`book/INDICE.md#casos-p%C3%BAblicos-documentados-cves-por-cap%C3%ADtulo`](book/INDICE.md#casos-p%C3%BAblicos-documentados-cves-por-cap%C3%ADtulo)

### DevSecOps na Prática
- **Índice completo**: [`devsecops/INDICE.md`](devsecops/INDICE.md)
- **Prefácio**: [`devsecops/00-prefacio.md`](devsecops/00-prefacio.md)
- **Lab setup**: [`devsecops/00-prefacio.md#4-ambiente-de-desenvolvimento`](devsecops/00-prefacio.md#4-ambiente-de-desenvolvimento)

### Engenharia e Análise de Malware
- **Índice completo**: [`malware/INDICE.md`](malware/INDICE.md)
- **Prefácio**: [`malware/00-prefacio.md`](malware/00-prefacio.md)
- **VM Setup**: [`malware/00-prefacio.md#4-ambiente-de-análise`](malware/00-prefacio.md#4-ambiente-de-análise)

### Concorrência e Paralelismo Seguro em C++
- **Índice completo**: [`concurrency/INDICE.md`](concurrency/INDICE.md)
- **Prefácio**: [`concurrency/00-prefacio.md`](concurrency/00-prefacio.md)
- **CVEs documentados**: [`concurrency/INDICE.md#cvcs-documentados-no-livro`](concurrency/INDICE.md#cvcs-documentados-no-livro)

---

## ✍️ Autor

Desenvolvedor de sistemas, foco em segurança de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com segurança de verdade."*

---

⭐ **Se este material te ajudou, deixe uma estrela no repositório** — ajuda outros desenvolvedores a encontrarem conteúdo de qualidade em português.