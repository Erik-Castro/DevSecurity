# DevSecurity — Livros de Desenvolvimento Seguro

> **Seguranca nao e um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositorio

Este e o repositorio central da colecao **DevSecurity**: livros tecnicos de desenvolvimento de software seguro, escritos em portugues, com foco pratico em **C++ moderno (C++17/20)** e arquitetura de sistemas.

O objetivo e preencher a lacuna entre teoria de seguranca e pratica de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padroes de codigo seguro, verificavel e pronto para producao.

### Numeros da Colecao

| Metrica | Valor |
|---------|-------|
| Livros publicados | 5 |
| Total de capitulos | 89 |
| Total de linhas | ~300.000+ |
| CVEs documentados | 300+ |
| Linguagens | C++17/20, Python, Bash, YAML, Go, Assembly |
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
- **Operacao**: Compliance (ASVS, SAMM, CERT, MISRA, ISO 27001, LGPD), Incident Response, Hardening, Supply Chain (SBOM, Sigstore, Reproducible Builds)

**Casos reais documentados**: Heartbleed, Shellshock, EternalBlue, Log4Shell, Spectre/Meltdown, SolarWinds, xz-utils backdoor, Qualcomm GPU UAF, Android Kernel, Samsung RKP, Equifax, Target, Stuxnet, Colonial Pipeline, LastPass, e mais.

**Ferramentas configuradas**: CMake hardening (GCC/Clang/MSVC), Sanitizers (ASan/TSan/UBSan/MSan), clang-tidy, cppcheck, Facebook Infer, libFuzzer, AFL++, Google Test/Benchmark.

[Leia online](book/INDICE.md) — indice completo com links para todos os capitulos.

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

[Leia online](devsecops/INDICE.md) — indice completo com links para todos os capitulos.

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

[Leia online](malware/INDICE.md) — indice completo com links para todos os capitulos.

---

### 4. Concorrencia e Paralelismo Seguro em C++

> *Modelo de Memoria, Lock-Free, Padroes, Debugging, Performance, GPU — 18 capitulos | ~19.700 linhas | CVEs de concorrencia | C++17/20*

**Conteudo:**
- **Fundamentos**: Modelo de memoria C++ (memory_order, happens-before, data races), Threads e sincronizacao (std::thread, mutex, locks, C++20 primitives)
- **Avancado**: Programacao Lock-Free (CAS, ABA, hazard pointers, RCU), Deadlocks/Livelocks/Starvation (Coffman, deteccao, prevencao)
- **Paralelismo**: Thread pools, std::async, executors, std::execution (par_unseq), OpenMP
- **Otimizacao**: False sharing, cache coherence (MESI), NUMA, containers concorrentes, lock-free queues/hash maps
- **Async**: Futures, promises, continuations, when_all, coroutines C++20 (co_await, generators)
- **Primitivas C++20**: latch, barrier, semaphore, stop_token
- **Testes e Debugging**: ThreadSanitizer, model checking, stress testing, GDB, core dumps, replay debugging
- **Performance**: Amdahl's law, profiling, NUMA tuning, scalable patterns (Actor, CSP, pipeline, fork-join)
- **Heterogeneo**: SIMD (AVX), CUDA, SYCL, OpenCL
- **Boas Praticas**: Checklist, anti-padroes, referencias

**CVEs documentados**: CVE-2016-0728 (keyring refcount), CVE-2017-18344 (timer race), CVE-2019-11135 (TSX Async Abort), CVE-2021-4034 (Polkit pkexec race), CVE-2014-0160 (Heartbleed).

[Leia online](concurrency/INDICE.md) — indice completo com links para todos os capitulos.

---

### 5. Criptografia Engenheira em C++

> *Constant-Time, Side-Channels, HSM, TLS 1.3, PQC, Key Management — 18 capitulos | ~66.400 linhas | 20+ CVEs | C++17*

**Conteudo:**
- **Fundamentos**: Primitivas criptograficas, bibliotecas (OpenSSL 3.x, libsodium, Botan), selecao de algoritmos
- **Constant-Time**: Timing attacks, cache-timing, techniques C++17, assembly intrinsics, Valgrind ct-grind
- **Side-Channel Attacks**: Power analysis (SPA/DPA/CPA), EM emanation, cache attacks (Prime+Probe, Flush+Reload), Spectre/Meltdown, Hertzbleed, Downfall
- **HSM e Hardware Security**: PKCS#11, cloud HSMs (AWS/Azure/GCP), TPM 2.0, Intel SGX, ARM TrustZone, attestation
- **TLS 1.3**: Handshake protocol, key schedule, 0-RTT, OpenSSL 3.x implementation, TLS server completo em C++17
- **Pos-Quantico**: ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+), hybrid schemes, migration strategy
- **Key Management**: Key lifecycle, wrapping, threshold crypto, distributed generation, Vault/KMS integration
- **Protocolos Modernos**: Signal Protocol, OPAQUE, Noise Framework, WireGuard
- **Criptografia Avancada**: FHE (Microsoft SEAL), Zero-Knowledge Proofs (SNARKs, STARKs, Bulletproofs), Formal Verification (SAW, ProVerif)
- **Testes**: Differential testing, Cryptofuzz, constant-time verification, reproducible builds
- **Compliance**: FIPS 140-3, Common Criteria, LGPD, GDPR, ICP-Brasil, PCI DSS, HIPAA
- **Boas Praticas**: 20+ anti-patterns, checklists completos, decision trees, migration checklist

**CVEs documentados**: CVE-2014-0160 (Heartbleed), CVE-2008-0166 (Debian OpenSSL), CVE-2019-1547 (ECDSA timing), Lucky13, Minerva, CVE-2017-15274 (ROCA), CVE-2019-11091 (MDS), Spectre-BHB, CVE-2021-36260 (Hikvision), Raccoon Attack, ROBOT Attack, CVE-2022-36760 (KyberSlash), CVE-2016-0728 (keyring refcount), CVE-2022-4304 (OpenSSL RSA timing), e mais.

[Leia online](cryptography/INDICE.md) — indice completo com links para todos os capitulos.

---

## Proximas Publicacoes (Em Planejamento)

| Livro | Foco | Status |
|-------|------|--------|
| **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++ avancado, corpus management, OSS-Fuzz integration, CI/CD | Planejado |
| **Supply Chain Security & Reproducible Builds** | SBOM (SPDX/CycloneDX), SLSA, Sigstore, in-toto, reproducible builds, xz-utils post-mortem | Planejado |
| **Security Code Review Handbook** | Checklists praticos, anti-padroes, como revisar PRs de seguranca, automacao | Planejado |
| **LGPD/GDPR para Engenheiros** | Privacy by Design em codigo, consentimento, criptografia, DPIA, breach notification | Planejado |
| **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security, language-agnostic | Planejado |

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
```

Todos os exemplos compilam. Use o `CMakeLists.txt` do [Prefacio SDD](book/00-prefacio.md) como base para seus projetos.

---

## Estrutura do Repositorio

```
DevSecurity/
├── README.md                    # Este arquivo
├── PROXIMOS-PROJETOS.md         # Roadmap e backlog
├── book/                        # Livro 1: Security-Driven Development (C++17)
│   ├── INDICE.md                # 48.500+ linhas
│   └── 00-17 capitulos
├── devsecops/                   # Livro 2: DevSecOps na Pratica (Multi-lang)
│   ├── INDICE.md                # 52.300+ linhas
│   └── 00-17 capitulos
├── malware/                     # Livro 3: Engenharia e Analise de Malware (C++17 + asm)
│   ├── INDICE.md                # 55.600+ linhas
│   └── 00-17 capitulos
├── concurrency/                 # Livro 4: Concorrencia e Paralelismo Seguro (C++17/20)
│   ├── INDICE.md                # 19.700+ linhas
│   └── 00-17 capitulos
└── cryptography/                # Livro 5: Criptografia Engenheira em C++ (C++17)
    ├── INDICE.md                # 66.400+ linhas
    └── 00-17 capitulos
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

## Links Uteis

### Security-Driven Development
- **Indice completo**: [book/INDICE.md](book/INDICE.md)
- **Prefacio (comece aqui)**: [book/00-prefacio.md](book/00-prefacio.md)
- **CMake Hardening Reference**: [book/00-prefacio.md](book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguranca)
- **CVEs por capitulo**: [book/INDICE.md](book/INDICE.md#casos-publicos-documentados-cves-por-capitulo)

### DevSecOps na Pratica
- **Indice completo**: [devsecops/INDICE.md](devsecops/INDICE.md)
- **Prefacio**: [devsecops/00-prefacio.md](devsecops/00-prefacio.md)
- **Lab setup**: [devsecops/00-prefacio.md](devsecops/00-prefacio.md#4-ambiente-de-desenvolvimento)

### Engenharia e Analise de Malware
- **Indice completo**: [malware/INDICE.md](malware/INDICE.md)
- **Prefacio**: [malware/00-prefacio.md](malware/00-prefacio.md)
- **VM Setup**: [malware/00-prefacio.md](malware/00-prefacio.md#4-ambiente-de-analise)

### Concorrencia e Paralelismo Seguro em C++
- **Indice completo**: [concurrency/INDICE.md](concurrency/INDICE.md)
- **Prefacio**: [concurrency/00-prefacio.md](concurrency/00-prefacio.md)
- **CVEs documentados**: [concurrency/INDICE.md](concurrency/INDICE.md#cvcs-documentados-no-livro)

### Criptografia Engenheira em C++
- **Indice completo**: [cryptography/INDICE.md](cryptography/INDICE.md)
- **Prefacio**: [cryptography/00-prefacio.md](cryptography/00-prefacio.md)
- **CVEs documentados**: [cryptography/INDICE.md](cryptography/INDICE.md#cvcs-documentados-no-livro)
- **Bibliotecas referenciadas**: OpenSSL 3.x, libsodium, liboqs, Botan, TPM2-TSS, Microsoft SEAL, libsnark
- **Ferramentas de analise**: Valgrind, Cryptofuzz, libFuzzer, AFL++, testssl.sh

---

## Autor

Desenvolvedor de sistemas, foco em seguranca de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com seguranca de verdade."*

---

Se este material te ajudou, deixe uma estrela no repositorio — ajuda outros desenvolvedores a encontrarem conteudo de qualidade em portugues.
