# DevSecurity — Livros de Desenvolvimento Seguro

> **Segurança não é um produto, mas um processo.** — Bruce Schneier

---

## Sobre este Repositório

Este é o repositório central da coleção **DevSecurity**: livros técnicos de desenvolvimento de software seguro, escritos em português, com foco prático em **C++ moderno (C++17/20/23)** e arquitetura de sistemas.

O objetivo é preencher a lacuna entre teoria de segurança e prática de desenvolvimento — transformando vulnerabilidades reais (CVEs documentados) em padrões de código seguro, verificável e pronto para produção.

---

## 📚 Publicação Atual

### **Security-Driven Development com C++17**
> *Desenvolvimento Seguro orientado à Segurança — 17 capítulos | ~44.700 linhas | 100+ CVEs | 200+ exemplos*

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

## 🚀 Próximas Publicações (Em Escrita)

| Livro | Foco | Previsão |
|-------|------|----------|
| **Secure C++ Concurrency & Parallelism** | Data races, lock-free, actor model, TSan, false sharing, side-channels | 2025 |
| **Cryptography Engineering in C++** | Constant-time, side-channels, HSM, TLS 1.3 internals, PQC migration, key management | 2025 |
| **Fuzzing & Property-Based Testing for C++** | libFuzzer/AFL++ avançado, corpus management, OSS-Fuzz integration, CI/CD | 2025 |
| **Supply Chain Security & Reproducible Builds** | SBOM (SPDX/CycloneDX), SLSA, Sigstore, in-toto, reproducible builds, xz-utils post-mortem | 2025 |
| **Security Code Review Handbook** | Checklists práticos, anti-patterns, como revisar PRs de segurança, automação | 2026 |
| **LGPD/GDPR para Engenheiros** | Privacy by Design em código, consentimento, criptografia, DPIA, breach notification | 2026 |
| **Secure Architecture Patterns** | Zero Trust, threat modeling at scale, capability-based security, language-agnostic | 2026 |

---

## 🎯 Para Quem Escrevo

- **Desenvolvedores C++** (intermediário a avançado) que querem código seguro por design
- **Engenheiros de Segurança** que auditam/revisam código nativo
- **Arquitetos & Tech Leads** que definem padrões e processos de segurança
- **Estudantes avançados** de ciência da computação / engenharia de software

**Pré-requisitos**: C++17 (templates, RAII, smart pointers, atomics), Linux/WSL2, CMake, compilador moderno (GCC 12+, Clang 16+, MSVC 2022+).

---

## 📖 Como Usar os Livros

Cada livro é **autocontido**, mas a sequência recomendada:

```
Iniciante:     Cap 1-5 → Cap 6-8 → Cap 9-12 → Cap 13-16
Experiente:    Cap 1-2 → Capítulos por necessidade → Cap 17 (referências)
Arquiteto:     Cap 1-3 → Cap 13-16 → Cap 17
```

Todos os exemplos compilam. Use o `CMakeLists.txt` do [Prefácio](book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a) como base para seus projetos.

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

- **Índice completo**: [`book/INDICE.md`](book/INDICE.md)
- **Prefácio (comece aqui)**: [`book/00-prefacio.md`](book/00-prefacio.md)
- **CMake Hardening Reference**: [`book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a`](book/00-prefacio.md#45-cmakeliststxt-completo-com-flags-de-seguran%C3%A7a)
- **CVEs por capítulo**: [`book/INDICE.md#casos-p%C3%BAblicos-documentados-cves-por-cap%C3%ADtulo`](book/INDICE.md#casos-p%C3%BAblicos-documentados-cves-por-cap%C3%ADtulo)

---

## ✍️ Autor

Desenvolvedor de sistemas, foco em segurança de software nativo, arquitetura e engenharia de confiabilidade.

> *"Escrevo o livro que gostaria de ter lido quando comecei a me importar com segurança de verdade."*

---

⭐ **Se este material te ajudou, deixe uma estrela no repositório** — ajuda outros desenvolvedores a encontrarem conteúdo de qualidade em português.