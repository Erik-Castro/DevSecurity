# DevSecurity

> **Segurança não é um produto, mas um processo.** — Bruce Schneier

---

## Sobre esta Coleção

O **DevSecurity** é uma coleção de livros técnicos de desenvolvimento de software seguro, escritos em português, com foco prático em **C++ moderno (C++17/20)** e arquitetura de sistemas.

O objetivo é preencher a lacuna entre teoria de segurança e prática de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padrões de código seguro, verificável e pronto para produção.

---

## Números da Coleção

| Métrica | Valor |
|---------|-------|
| Livros publicados | 10 |
| Total de capítulos | 180 |
| Total de linhas | ~527.000+ |
| CVEs documentados | 420+ |
| Linguagens | C++17/20, Python, Bash, YAML, Go, Assembly, Rust, JS/TS, CMake, WebAssembly |
| Idioma | Português (PT-BR) para texto, Inglês para código |

---

## Livros Publicados

### 1. [Security-Driven Development com C++17](book/00-prefacio.md)
> *Desenvolvimento Seguro orientado à Segurança — 17 capítulos | ~48.500 linhas | 100+ CVEs | 200+ exemplos*

**Conteúdo:**
- **Fundamentos**: SDD, Secure SDLC, Threat Modeling (STRIDE/PASTA/DREAD), OWASP Top 10 + CWE Top 25 mapeados para C++
- **Codificação Segura**: Princípios (Saltzer & Schroeder), Memory Safety, Error Handling, Input Validation
- **Domínios Críticos**: AuthN/AuthZ, Criptografia (AES-GCM, ChaCha20-Poly1305, X25519, TLS 1.3, PQC), Rede, Database, API, Concorrência
- **Verificação**: SAST/DAST, Fuzzing (libFuzzer/AFL++), Penetration Testing, Mutation Testing
- **Operação**: Compliance (ASVS, SAMM, CERT, MISRA, ISO 27001, LGPD), Incident Response, Hardening, Supply Chain (SBOM, Sigstore, Reproducible Builds)

**Casos reais**: Heartbleed, Shellshock, EternalBlue, Log4Shell, Spectre/Meltdown, SolarWinds, xz-utils backdoor, Qualcomm GPU UAF, Android Kernel, Samsung RKP, Equifax, Target, Stuxnet, Colonial Pipeline, LastPass.

---

### 2. [DevSecOps na Prática](devsecops/00-prefacio.md)
> *Pipeline CI/CD Seguro, Ferramentas, Containers, Cloud, Kubernetes e Compliance — 18 capítulos | ~52.300 linhas | 60+ CVEs*

**Conteúdo:**
- **Pipeline Seguro**: GitHub Actions, GitLab CI, Jenkins hardening, OIDC, secret management, artifact signing
- **Shift-Left**: IDE integration, pre-commit hooks, CodeQL, Semgrep, SAST/DAST/SCA integrados
- **Container & Cloud**: Docker hardening, Kubernetes (Pod Security, RBAC, Network Policies, OPA/Gatekeeper, Falco), AWS/Azure/GCP security
- **Supply Chain**: GitOps (ArgoCD/Flux), SLSA, Sigstore/Cosign, SBOM (SPDX/CycloneDX), xz-utils post-mortem
- **Observabilidade**: ELK/Wazuh, Prometheus/Grafana, Falco, threat hunting, MTTD/MTTR

---

### 3. [Engenharia e Análise de Malware em C++](malware/00-prefacio.md)
> *Reverse Engineering, Análise Estática/Dinâmica, Debugging, Ransomware, Rootkits, Exploits — 18 capítulos | ~55.600 linhas | 100+ malwares documentados*

**Conteúdo:**
- **Fundamentos**: PE/ELF/Mach-O parsing, x86/x64 assembly, calling conventions, syscalls, compiler artifacts
- **Ferramentas**: IDA Pro (IDAPython), Ghidra (scripts), Radare2/Cutter, GDB/GEF/PEDA, x64dbg, WinDbg
- **Análise Estática**: Strings (XOR/RC4), imports/exports, packer detection (UPX/Themida/VMProtect), entropy, YARA rules
- **Análise Dinâmica**: API monitoring, C2 traffic analysis, sandbox automation (Cuckoo/CAPE), anti-sandbox evasion
- **Malware por Categoria**: Ransomware (WannaCry, NotPetya, Conti, LockBit, BlackCat), Rootkits/Bootkits (UEFI MoonBounce, BlackLotus), Exploits/Shellcode (EternalBlue, ROP chains)

---

### 4. [Concorrência e Paralelismo Seguro em C++](concurrency/00-prefacio.md)
> *Modelo de Memória, Lock-Free, Padrões, Debugging, Performance, GPU — 18 capítulos | ~19.700 linhas*

**Conteúdo:**
- **Fundamentos**: Modelo de memória C++ (memory_order, happens-before, data races), Threads e sincronização
- **Avançado**: Programação Lock-Free (CAS, ABA, hazard pointers, RCU), Deadlocks/Livelocks/Starvation
- **Paralelismo**: Thread pools, std::async, executors, std::execution (par_unseq), OpenMP
- **Otimização**: False sharing, cache coherence (MESI), NUMA, containers concorrentes
- **Async**: Futures, promises, continuations, when_all, coroutines C++20

---

### 5. [Criptografia Engenheira em C++](cryptography/00-prefacio.md)
> *Constant-Time, Side-Channels, HSM, TLS 1.3, PQC, Key Management — 18 capítulos | ~66.400 linhas | 20+ CVEs*

**Conteúdo:**
- **Fundamentos**: Primitivas criptográficas, bibliotecas (OpenSSL 3.x, libsodium, Botan), seleção de algoritmos
- **Constant-Time**: Timing attacks, cache-timing, techniques C++17, assembly intrinsics, Valgrind ct-grind
- **Side-Channel Attacks**: Power analysis (SPA/DPA/CPA), EM emanation, cache attacks (Prime+Probe, Flush+Reload)
- **HSM e Hardware Security**: PKCS#11, cloud HSMs, TPM 2.0, Intel SGX, ARM TrustZone, attestation
- **TLS 1.3**: Handshake protocol, key schedule, 0-RTT, OpenSSL 3.x implementation
- **Pós-Quântico**: ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+), hybrid schemes

---

### 6. [Desenvolvimento Seguro na Web](web/00-prefacio.md)
> *OWASP Top 10, XSS, SQL Injection, Auth, API Security — 18 capítulos | ~57.800 linhas | 20+ CVEs*

---

### 7. [CMake Seguro e Build Systems](cmake-book/00-prefacio.md)
> *Build Systems, Hardening, Supply Chain, Reproducibility — 18 capítulos | ~52.500 linhas*

---

### 8. [GitHub Actions Pipelines Seguros](github-actions/00-prefacio.md)
> *Triggers, Secrets, OIDC, Reusable Workflows, Supply Chain — 18 capítulos | ~49.000 linhas*

---

### 9. [WebAssembly Seguro](wasm/00-prefacio.md)
> *Wasm Architecture, WASI, Sandboxing, Plugins, Edge, Blockchain — 18 capítulos | ~76.300 linhas*

---

### 10. [Autenticação, Autorização e Controle de Acesso](authz/00-prefacio.md)
> *OAuth, OIDC, SSO, RBAC, ABAC, WebAuthn, Caso Misantropi4 — 18 capítulos | ~49.500 linhas*

---

## Para Quem Escrevo

- **Desenvolvedores C++** (intermediário a avançado) que querem código seguro por design
- **Engenheiros de Segurança** que auditam/revisam código nativo
- **Arquitetos & Tech Leads** que definem padrões e processos de segurança
- **Analistas de Malware / Threat Researchers** que fazem engenharia reversa
- **DevOps / Platform Engineers** que constroem pipelines seguros
- **Estudantes avançados** de ciência da computação / engenharia de software

**Pré-requisitos**: C++17 (templates, RAII, smart pointers, atomics), Linux/WSL2, CMake, compilador moderno (GCC 12+, Clang 16+, MSVC 2022+).

---

## Como Navegar

Use o menu superior para selecionar um livro. Cada livro possui sua própria estrutura de capítulos navegável na barra lateral.

### Caminhos de Leitura Recomendados

=== "Desenvolvedor C++"
    ```
    SDD (1-5) → SDD (6-12) → DevSecOps (1-4) → DevSecOps (5-9)
    ```

=== "Engenheiro de Segurança"
    ```
    Malware (1-4) → Malware (5-10) → SDD (13-17) → DevSecOps (10-17)
    ```

=== "DevOps/Platform Engineer"
    ```
    DevSecOps (1-9) → DevSecOps (10-17) → Malware (14-15)
    ```

=== "Arquiteto"
    ```
    SDD (1-3) → DevSecOps (1-3) → Malware (17) → Todos os Cap 17
    ```

---

## Licença

**CC BY-NC-SA 4.0** — Compartilhe, adapte, cite a fonte. Uso comercial requer autorização.

---

## Links Úteis

- [Repositório GitHub](https://github.com/username/DevSecurity)
- [Issues](https://github.com/username/DevSecurity/issues) — Erros técnicos, CVEs faltando, exemplos que não compilam
- [Discussões](https://github.com/username/DevSecurity/discussions) — Sugestões de temas, capítulos, formatos

---

## Autor

Desenvolvedor de sistemas, foco em segurança de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com segurança de verdade."*
