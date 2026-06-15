# Tasks: Book 5 — Cryptography Engineering in C++

**Change**: cryptography-engineering  
**Status**: Draft  
**Date**: 2026-06-15  
**Spec Reference**: `/home/Projetos/DevSecurity/openspec/changes/sdd/cryptography-engineering/spec.md`  
**Design Reference**: `/home/Projetos/DevSecurity/openspec/changes/sdd/cryptography-engineering/design.md`

---

## Review Workload Forecast

| Metric | Value |
|--------|-------|
| **Total Chapters** | 18 (00-17) |
| **Estimated Total Lines** | ~56,100 |
| **Per-Chapter Range** | 1,800-3,900 lines |
| **Unique CVEs** | 20 |
| **Chained PRs Recommended** | No (single repo, sequential writing) |
| **Decision Needed Before Apply** | No |
| **Estimated Total Effort** | ~804 hours |

### Per-Chapter Line Breakdown

| Chapter | Target Lines | Prose (PT-BR) | Code (EN) | Tables | Exercises | CVE Analysis |
|---------|--------------|---------------|-----------|--------|-----------|--------------|
| 00 Prefácio | 1,800 | 1,000 | 200 | 200 | 200 | 200 |
| 01 Introdução | 2,800 | 1,200 | 800 | 200 | 300 | 300 |
| 02 Constant-Time | 3,200 | 1,400 | 900 | 250 | 350 | 300 |
| 03 Side-Channel | 3,400 | 1,500 | 950 | 280 | 320 | 350 |
| 04 HSM/Tokens | 3,000 | 1,300 | 850 | 250 | 300 | 300 |
| 05 TLS 1.3 | 3,600 | 1,600 | 1,000 | 300 | 350 | 350 |
| 06 PQC | 3,200 | 1,400 | 900 | 280 | 320 | 300 |
| 07 Key Management | 3,000 | 1,300 | 850 | 250 | 300 | 300 |
| 08 Modern Protocols | 3,200 | 1,400 | 900 | 280 | 320 | 300 |
| 09 Hardware Security | 3,000 | 1,300 | 850 | 250 | 300 | 300 |
| 10 Homomorphic | 2,800 | 1,200 | 800 | 250 | 300 | 250 |
| 11 ZKP | 3,000 | 1,300 | 850 | 250 | 300 | 300 |
| 12 Formal Verification | 2,800 | 1,200 | 800 | 250 | 300 | 250 |
| 13 Testing | 3,000 | 1,300 | 850 | 250 | 300 | 300 |
| 14 Compliance | 2,800 | 1,200 | 800 | 250 | 300 | 250 |
| 15 Case Study | 3,900 | 1,700 | 1,100 | 350 | 350 | 400 |
| 16 Best Practices | 2,800 | 1,200 | 800 | 250 | 300 | 250 |
| 17 Conclusion | 2,000 | 1,000 | 400 | 200 | 200 | 200 |

---

## Task Dependency Graph

```
Ch00 (Prefácio) ─────────────────────────────────────────────────────────────────┐
  └── Ch01 (Introdução) ──────────────────────────────────────────────────────┐  │
        ├── Ch02 (Constant-Time) ──→ Ch03 (Side-Channel) ──→ Ch12 (Formal) ──┼──┤
        ├── Ch04 (HSM/Tokens) ──→ Ch09 (TPM/Enclaves) ──→ Ch15 (Case Study) ─┤  │
        ├── Ch05 (TLS 1.3) ──→ Ch06 (PQC) ──→ Ch08 (Modern Protocols) ──────┤  │
        ├── Ch07 (Key Management) ──→ Ch14 (Compliance) ──→ Ch15 (Case Study)─┤  │
        ├── Ch10 (Homomorphic) ──→ Ch11 (ZKP) ──→ Ch13 (Testing) ────────────┤  │
        └── Ch15 (Case Study) ← Ch02 + Ch04 + Ch05 + Ch07 ──→ Ch16 (Best) ──┘  │
              └── Ch16 (Best Practices) ──→ Ch17 (Conclusion) ─────────────────┘
```

### Independent vs Dependent Chapters

| Category | Chapters | Can Start Immediately |
|----------|----------|----------------------|
| **Independent** | Ch00, Ch01 | Yes (no dependencies) |
| **Semi-Independent** | Ch02, Ch04, Ch05, Ch07, Ch10 | After Ch01 |
| **Dependent** | Ch03, Ch06, Ch08, Ch09, Ch11, Ch12, Ch13, Ch14 | After prerequisites |
| **Highly Dependent** | Ch15 | After Ch02, Ch04, Ch05, Ch07 |
| **Terminal** | Ch16, Ch17 | After Ch15 or all previous |

### Optimal Parallel Execution Order

**Wave 1** (Start immediately):
- Ch00 (Prefácio) — no dependencies

**Wave 2** (After Ch00):
- Ch01 (Introdução) — depends on Ch00

**Wave 3** (After Ch01, parallel):
- Ch02 (Constant-Time) — depends on Ch01
- Ch04 (HSM/Tokens) — depends on Ch01
- Ch05 (TLS 1.3) — depends on Ch01
- Ch07 (Key Management) — depends on Ch01
- Ch10 (Homomorphic) — depends on Ch01

**Wave 4** (After Wave 3, parallel):
- Ch03 (Side-Channel) — depends on Ch02
- Ch06 (PQC) — depends on Ch05
- Ch08 (Modern Protocols) — depends on Ch05
- Ch09 (Hardware Security) — depends on Ch04
- Ch11 (ZKP) — depends on Ch01 (can start with Wave 3)

**Wave 5** (After Wave 4, parallel):
- Ch12 (Formal Verification) — depends on Ch02
- Ch13 (Testing) — depends on Ch01
- Ch14 (Compliance) — depends on Ch07

**Wave 6** (After Wave 5):
- Ch15 (Case Study) — depends on Ch02, Ch04, Ch05, Ch07

**Wave 7** (After Wave 6):
- Ch16 (Best Practices) — depends on all previous

**Wave 8** (After Wave 7):
- Ch17 (Conclusion) — depends on all previous

---

## Task List

### Task T00: Prefácio

| Field | Value |
|-------|-------|
| **ID** | T00 |
| **Title** | Prefácio |
| **Slug** | `00-prefacio.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 1,800 |
| **Dependencies** | None |
| **Priority** | High |
| **Phase** | Foundation |
| **Estimated Hours** | 8 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 0.1 Saudação e Motivação | Por que engenharia criptográfica é diferente de usar criptografia | 200 |
| 0.2 Audiência-Alvo | C++ devs, security engineers, DevSecOps | 150 |
| 0.3 Pré-requisitos | Conhecimento C++17, conceitos básicos de criptografia (Book 1) | 200 |
| 0.4 Estrutura do Livro | Como os 18 capítulos se conectam, caminhos de leitura | 300 |
| 0.5 Convenções do Código | OpenSSL 3.x, libsodium, liboqs, Botan, TPM2-TSS | 200 |
| 0.6 Como Usar Este Livro | Exercícios, estudos de caso, laboratórios | 200 |
| 0.7 Agradecimentos | Créditos e referências | 150 |
| 0.8 Nota sobre CVEs | Como analisamos vulnerabilidades reais | 200 |
| 0.9 Segurança em Português | Preenchendo a lacuna na literatura técnica PT-BR | 200 |

#### CVEs to Include
- None (introductory chapter)

#### Key Code Examples
- None (introductory chapter)

#### Acceptance Criteria
- [ ] Total lines within 1,700-1,900 range
- [ ] All 9 sections present and complete
- [ ] Learning objectives clear and measurable
- [ ] Book structure explained with dependency graph
- [ ] Library conventions documented
- [ ] PT-BR prose is natural and professional
- [ ] No code examples (as per spec)

---

### Task T01: Introdução à Engenharia Criptográfica

| Field | Value |
|-------|-------|
| **ID** | T01 |
| **Title** | Introdução à Engenharia Criptográfica |
| **Slug** | `01-introducao-engenharia-criptografica.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,800 |
| **Dependencies** | T00 (Prefácio) |
| **Priority** | High |
| **Phase** | Foundation |
| **Estimated Hours** | 40 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 1.1 O Abismo entre Teoria e Prática | Por que algoritmos seguros geram sistemas inseguros | 250 |
| 1.2 Princípios da Engenharia Criptográfica | Fail-safe defaults, complete mediation, economy of mechanism | 300 |
| 1.3 Camadas de Segurança | Defense in depth para sistemas criptográficos | 250 |
| 1.4 Modelos de Ameaça | STRIDE, DREAD aplicados a criptografia | 300 |
| 1.5 Padrões de Arquitetura | Crypto abstraction layers, provider patterns | 350 |
| 1.6 Erros Comuns em Implementações | Nonce reuse, key reuse, RNG failures, timing leaks | 400 |
| 1.7 Ferramentas de Análise | SAST, DAST, fuzzing para código criptográfico | 300 |
| 1.8 CVEs Históricas | Debian OpenSSL bug, Android PRNG, Heartbleed analysis | 400 |
| 1.9 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2008-0166 | Debian OpenSSL predictable RNG | 2008 | 1.8 |
| CVE-2013-2099 | Android PRNG vulnerability | 2013 | 1.8 |
| CVE-2014-0160 | Heartbleed OpenSSL over-read | 2014 | 1.8 |

#### Key Code Examples
- Basic OpenSSL 3.x context initialization (`OSSL_LIB_CTX`, `EVP_PROVIDER`)
- Secure random number generation comparison (`RAND_bytes` vs `std::random_device` vs `getrandom`)
- Key derivation function (PBKDF2) with `EVP_KDF` API
- Simple authenticated encryption with libsodium (`crypto_aead_xchacha20poly1305_ietf`)
- Provider pattern interface for crypto abstraction
- Entropy source detection and validation

#### Acceptance Criteria
- [ ] Total lines within 2,600-3,000 range
- [ ] All 9 sections present and complete
- [ ] 3 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] Provider pattern interface defined
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Book 1 Chapter 8
- [ ] PT-BR prose is natural and professional
- [ ] English code identifiers consistent

---

### Task T02: Fundamentos de Constant-Time Programming

| Field | Value |
|-------|-------|
| **ID** | T02 |
| **Title** | Fundamentos de Constant-Time Programming |
| **Slug** | `02-fundamentos-constant-time.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,200 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | High |
| **Phase** | Foundation |
| **Estimated Hours** | 48 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 2.1 Introdução a Timing Attacks | Como medições de tempo revelam segredos | 300 |
| 2.2 Análise de Timing em C++ | Compiladores, otimizações, hardware | 350 |
| 2.3 Comparações Constant-Time | Verificação segura de segredos (secrets comparison) | 400 |
| 2.4 Branchless Programming | Ternário, bit masking, select patterns | 400 |
| 2.5 Acesso à Memória Constant-Time | Cache-timing, DRAM, DRAM row-buffer attacks | 350 |
| 2.6 Validação de Timing | Medição estatística, testes de timing | 300 |
| 2.7 Compiladores e Optimizações | volatile, asm volatile, compiler barriers | 350 |
| 2.8 CVEs de Timing | Lucky13, Minerva, Raccoon | 400 |
| 2.9 Exercícios e Referências | Práticas e bibliografia | 350 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2013-0169 | Lucky13 CBC padding oracle timing | 2013 | 2.8 |
| CVE-2019-15809 | Minerva ECDSA timing attack | 2019 | 2.8 |
| CVE-2020-1968 | Raccoon DH key computation timing | 2020 | 2.8 |

#### Key Code Examples
- Constant-time comparison function (OpenSSL `CRYPTO_memcmp` vs custom `secure_compare`)
- Branchless conditional move patterns (`cmov` emulation, ternary with masking)
- Timing measurement harness with `std::chrono::high_resolution_clock`
- Constant-time AES implementation wrapper (AES-NI vs software)
- Cache-timing attack demonstration (educational `flushreload.c`)
- Secure memory zeroing with compiler barrier (`explicit_bzero`, `OPENSSL_cleanse`)
- Timing test statistical analysis (chi-squared, t-test)

#### Acceptance Criteria
- [ ] Total lines within 3,000-3,400 range
- [ ] All 9 sections present and complete
- [ ] 3 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] Constant-time comparison implemented and tested
- [ ] Branchless patterns demonstrated
- [ ] Timing measurement harness functional
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch04 (Side-Channel)
- [ ] PT-BR prose is natural and professional

---

### Task T03: Ataques de Canal Lateral Avançados

| Field | Value |
|-------|-------|
| **ID** | T03 |
| **Title** | Ataques de Canal Lateral Avançados |
| **Slug** | `03-ataques-canal-lateral.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,400 |
| **Dependencies** | T02 (Constant-Time) |
| **Priority** | Medium |
| **Phase** | Foundation |
| **Estimated Hours** | 52 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 3.1 Taxonomia de Side-Channels | Classificação por canal (tempo, potência, EM, acústico) | 300 |
| 3.2 Power Analysis | SPA, DPA, CPA: teoria e implementação | 450 |
| 3.3 Emanação Eletromagnética | Ataques EM, contramedidas | 350 |
| 3.4 Cache-Timing Attacks | Flush+Reload, Prime+Probe, Evict+Time | 450 |
| 3.5 Branch Prediction Attacks | Spectre v1, v2, mitigações | 400 |
| 3.6 Memory Access Patterns | Oblivious RAM, padded pointers | 350 |
| 3.7 Ataques Acústicos | Acoustic cryptanalysis, contramedidas | 250 |
| 3.8 Contramedidas de Software | Constant-time, masking, shuffling | 400 |
| 3.9 CVEs de Side-Channel | Hertzbleed, Downfall, TPM-FAIL | 350 |
| 3.10 Exercícios e Referências | Práticas e bibliografia | 100 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2022-23935 | Hertzbleed frequency throttling side-channel | 2022 | 3.9 |
| CVE-2022-40982 | Downfall Gather data sampling | 2023 | 3.9 |
| CVE-2019-11090 | TPM-FAIL Intel TPM timing attack | 2019 | 3.9 |

#### Key Code Examples
- Power analysis measurement setup (educational with `perf`)
- Flush+Reload cache-timing attack PoC (`clflush`, `rdtsc`)
- Prime+Probe demonstration (L3 cache occupancy)
- Masking countermeasure implementation (boolean masking, Ishai-Sahai-Wagner)
- Shuffling countermeasure for lookup tables (AES S-box)
- Memory access pattern obfuscation (ORAM simulation)
- Spectre v1 gadget detection and mitigation

#### Acceptance Criteria
- [ ] Total lines within 3,200-3,600 range
- [ ] All 10 sections present and complete
- [ ] 3 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] Cache-timing attacks demonstrated
- [ ] Masking countermeasures implemented
- [ ] Spectre mitigations shown
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch02, Ch14
- [ ] PT-BR prose is natural and professional

---

### Task T04: HSM e Tokens de Segurança

| Field | Value |
|-------|-------|
| **ID** | T04 |
| **Title** | HSM e Tokens de Segurança |
| **Slug** | `04-hsm-tokens-seguranca.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,000 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | High |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 44 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 4.1 Fundamentos de HSM | O que é e quando usar | 250 |
| 4.2 PKCS#11 Interface | Programação com tokens físicos | 400 |
| 4.3 Cloud HSM Services | AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM | 350 |
| 4.4 Key Ceremony | Procedimentos de ceremony, multi-person control | 300 |
| 4.5 High Availability | Connection pooling, failover, load balancing | 350 |
| 4.6 Performance Considerations | Latency, throughput, caching strategies | 300 |
| 4.7 Compliance | FIPS 140-3 levels, Common Criteria | 300 |
| 4.8 CVEs de HSM | ROCA, hardware token vulnerabilities | 300 |
| 4.9 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2017-15361 | ROCA Infineon RSA key generation flaw | 2017 | 4.8 |

#### Key Code Examples
- PKCS#11 initialization and token enumeration (`C_Initialize`, `C_GetSlotList`)
- Key generation via HSM (RSA, EC) using `C_GenerateKeyPair`
- Signing and verification with HSM keys (`C_Sign`, `C_Verify`)
- Connection pooling for HSM sessions (thread-safe wrapper)
- AWS CloudHSM integration example (`cloudhsm.hsm_client`)
- Key ceremony procedure automation (M-of-N approval workflow)
- HSM-backed TLS certificate storage

#### Acceptance Criteria
- [ ] Total lines within 2,800-3,200 range
- [ ] All 9 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] PKCS#11 interface demonstrated
- [ ] Cloud HSM integration shown
- [ ] Key ceremony procedure documented
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch08
- [ ] PT-BR prose is natural and professional

---

### Task T05: TLS 1.3: Internals e Implementação

| Field | Value |
|-------|-------|
| **ID** | T05 |
| **Title** | TLS 1.3: Internals e Implementação |
| **Slug** | `05-tls13-internals.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,600 |
| **Dependencies** | T01 (Introdução), T02 (Constant-Time) |
| **Priority** | High |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 56 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 5.1 TLS 1.3 vs TLS 1.2 | Mudanças fundamentais, handshake simplificado | 300 |
| 5.2 Handshake Protocol | ServerHello, EncryptedExtensions, CertificateVerify | 450 |
| 5.3 Key Schedule | HKDF, key derivation, traffic keys | 400 |
| 5.4 0-RTT Resumption | Early data, replay attacks, security implications | 350 |
| 5.5 Certificate Handling | Validation, chain building, OCSP stapling | 350 |
| 5.6 Session Tickets | PSK, resumption, security considerations | 300 |
| 5.7 Implementation in C++ | OpenSSL 3.x TLS client, error handling | 400 |
| 5.8 TLS Server Implementation | Minimal TLS server, SNI, ALPN | 400 |
| 5.9 CVEs TLS | Lucky13, POODLE, FREAK, Triple Handshake | 400 |
| 5.10 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2013-0169 | Lucky13 CBC padding oracle | 2013 | 5.9 |
| CVE-2014-3566 | POODLE SSL 3.0 padding oracle | 2014 | 5.9 |
| CVE-2015-0204 | FREAK export cipher downgrade | 2015 | 5.9 |
| CVE-2014-3513 | Triple Handshake session resumption | 2014 | 5.9 |

#### Key Code Examples
- TLS 1.3 client with OpenSSL 3.x (`SSL_CTX_set_min_proto_version`, `SSL_set_tlsext_host_name`)
- TLS 1.3 server implementation (`SSL_CTX_use_PrivateKey_file`, `SSL_accept`)
- 0-RTT early data handling (`SSL_CTX_set_max_early_data`, `SSL_get_early_data_status`)
- Certificate validation and pinning (`X509_STORE`, custom verify callback)
- Session ticket implementation (PSK resumption)
- TLS 1.3 handshake debugger/parser (WYSIWYT approach)
- Custom cipher suite configuration
- OCSP stapling implementation

#### Acceptance Criteria
- [ ] Total lines within 3,400-3,800 range
- [ ] All 10 sections present and complete
- [ ] 4 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] TLS 1.3 client implemented
- [ ] TLS 1.3 server implemented
- [ ] 0-RTT handling shown
- [ ] Certificate validation demonstrated
- [ ] Exercises include 5 practical tasks
- [ ] Cross-references to Ch04
- [ ] PT-BR prose is natural and professional

---

### Task T06: Criptografia Pós-Quântica: Migração Prática

| Field | Value |
|-------|-------|
| **ID** | T06 |
| **Title** | Criptografia Pós-Quântica: Migração Prática |
| **Slug** | `06-criptografia-pos-quantica.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,200 |
| **Dependencies** | T01 (Introdução), T05 (TLS 1.3) |
| **Priority** | High |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 48 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 6.1 Ameaça Quântica | Shor's, Grover's, harvest now decrypt later | 300 |
| 6.2 Padrões NIST PQC | ML-KEM (Kyber), ML-DSA (Dilithium), SLH-DSA (SPHINCS+) | 400 |
| 6.3 Hybrid Schemes | Combinação clássica + PQC, rationale | 350 |
| 6.4 Cryptographic Inventory | Mapeamento de algoritmos em sistemas | 300 |
| 6.5 Migration Strategies | Big bang vs incremental, rollback plans | 350 |
| 6.6 Performance Implications | Benchmarks, overhead analysis | 300 |
| 6.7 TLS and PQC | Hybrid key exchange, certificate chains | 350 |
| 6.8 liboqs Integration | Open Quantum Safe library usage | 300 |
| 6.9 CVEs PQC | Relacionados a implementações PQC | 200 |
| 6.10 Exercícios e Referências | Práticas e bibliografia | 200 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2022-3676 | Liboqs side-channel in Kyber | 2022 | 6.9 |

#### Key Code Examples
- liboqs basic usage (`OQS_KEM_keypair`, `OQS_KEM_encaps`, `OQS_KEM_decaps`)
- Hybrid key exchange (X25519 + ML-KEM-768)
- Cryptographic inventory scanner (binary analysis, dependency detection)
- Migration test harness (old vs new algorithm validation)
- Performance benchmarking suite (Google Benchmark + liboqs)
- PQC certificate chain handling (hybrid X.509)
- Algorithm agility pattern implementation
- Deprecation warning system for legacy algorithms

#### Acceptance Criteria
- [ ] Total lines within 3,000-3,400 range
- [ ] All 10 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] liboqs integration demonstrated
- [ ] Hybrid key exchange implemented
- [ ] Migration strategy documented
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch08
- [ ] PT-BR prose is natural and professional

---

### Task T07: Gestão de Chaves Avançada

| Field | Value |
|-------|-------|
| **ID** | T07 |
| **Title** | Gestão de Chaves Avançada |
| **Slug** | `07-gestao-chaves-avancada.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,000 |
| **Dependencies** | T01 (Introdução), T04 (HSM/Tokens) |
| **Priority** | Medium |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 44 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 7.1 Key Lifecycle | Estados de chave, transições, políticas | 300 |
| 7.2 Key Generation | CSPRNG, entropy sources, key quality | 300 |
| 7.3 Key Wrapping | AES-KW, AES-KWP, RSA-OAEP wrapping | 350 |
| 7.4 Secret Sharing | Shamir's scheme, verifiable secret sharing | 350 |
| 7.5 Threshold Cryptography | Shamir's secret sharing + crypto operations | 350 |
| 7.6 Key Rotation | Automated rotation, backward compatibility | 300 |
| 7.7 Secure Destruction | Memory zeroing, key material handling | 250 |
| 7.8 Distributed Key Generation | DKG protocols, dealerless schemes | 300 |
| 7.9 CVEs de Key Management | Weak key generation, key leakage | 200 |
| 7.10 Exercícios e Referências | Práticas e bibliografia | 300 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2008-0166 | Debian OpenSSL weak key generation | 2008 | 7.9 |

#### Key Code Examples
- Key lifecycle state machine (generate → active → rotate → retire → destroy)
- AES key wrapping (RFC 3394) with `EVP_aes_256_wrap`
- Shamir's Secret Sharing implementation (GF(2^8) arithmetic)
- Threshold ECDSA signing (t-of-n party computation)
- Automated key rotation scheduler (time-based, usage-based)
- Secure memory zeroing utilities (`SecureString`, `SecureVector`)
- Key metadata management (creation date, usage count, expiry)
- Distributed key generation (DKG) protocol

#### Acceptance Criteria
- [ ] Total lines within 2,800-3,200 range
- [ ] All 10 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] Key lifecycle implemented
- [ ] Shamir's Secret Sharing working
- [ ] Key rotation automated
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch14
- [ ] PT-BR prose is natural and professional

---

### Task T08: Protocolos Criptográficos Modernos

| Field | Value |
|-------|-------|
| **ID** | T08 |
| **Title** | Protocolos Criptográficos Modernos |
| **Slug** | `08-protocolos-criptograficos-modernos.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,200 |
| **Dependencies** | T01 (Introdução), T02 (Constant-Time), T05 (TLS 1.3) |
| **Priority** | Medium |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 48 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 8.1 Noise Protocol Framework | Pattern libraries, handshake patterns, crypto binding | 400 |
| 8.2 Signal Protocol | X3DH, Double Ratchet, Sender Keys | 450 |
| 8.3 WireGuard Cryptography | Noise_IK, ChaCha20-Poly1305, Curve25519 | 400 |
| 8.4 Messaging Layer Security | MLS protocol, tree KEM, group operations | 350 |
| 8.5 Protocol Analysis | Formal methods, security proofs | 300 |
| 8.6 Implementation Patterns | State machines, error handling | 350 |
| 8.7 Performance Considerations | Benchmarking, optimization | 250 |
| 8.8 CVEs de Protocolos | Logjam, SWEET32, Null Pointer Deref | 400 |
| 8.9 Exercícios e Referências | Práticas e bibliografia | 300 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2015-4000 | Logjam DHE export cipher downgrade | 2015 | 8.8 |
| CVE-2016-2183 | SWEET32 birthday attack | 2016 | 8.8 |
| CVE-2021-3449 | OpenSSL NULL pointer dereference | 2021 | 8.8 |

#### Key Code Examples
- Noise protocol handshake (Noise_IK pattern) with `noise-c-*` library
- Signal Protocol Double Ratchet implementation (X3DH + symmetric ratchet)
- WireGuard-like key exchange (Noise_IK, ChaCha20-Poly1305, Curve25519)
- MLS group key management (TreeKEM, group operations)
- Protocol state machine (formal state transitions)
- Security proof annotations (provable security comments)
- Message encryption/decryption with forward secrecy
- Group key agreement protocol

#### Acceptance Criteria
- [ ] Total lines within 3,000-3,400 range
- [ ] All 9 sections present and complete
- [ ] 3 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] Noise handshake implemented
- [ ] Signal Protocol shown
- [ ] WireGuard cryptography demonstrated
- [ ] Exercises include 4 practical tasks
- [ ] PT-BR prose is natural and professional

---

### Task T09: Hardware Security: TPM e Enclaves

| Field | Value |
|-------|-------|
| **ID** | T09 |
| **Title** | Hardware Security: TPM e Enclaves |
| **Slug** | `09-hardware-security-tpm-enclaves.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,000 |
| **Dependencies** | T01 (Introdução), T04 (HSM/Tokens) |
| **Priority** | Medium |
| **Phase** | Hardware & Protocols |
| **Estimated Hours** | 44 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 9.1 Trusted Platform Modules | TPM 2.0 architecture, PCR, attestation | 350 |
| 9.2 TPM2-TSS Integration | Software stack, ESAPI, FAPI | 400 |
| 9.3 Intel SGX | Enclave creation, sealing, attestation | 400 |
| 9.4 ARM TrustZone | Secure world, Trusted Applications | 300 |
| 9.5 Remote Attestation | Quote verification, endorsement keys | 350 |
| 9.6 Secure Boot | Measured boot, chain of trust | 300 |
| 9.7 Key Storage | Sealed storage, wrapped keys | 250 |
| 9.8 CVEs de Hardware | TPM-FAIL, side-channel enclaves | 350 |
| 9.9 Exercícios e Referências | Práticas e bibliografia | 300 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2019-11090 | TPM-FAIL Intel TPM timing attack | 2019 | 9.8 |
| CVE-2019-16863 | TPM-FAIL AMD fTPM timing attack | 2019 | 9.8 |

#### Key Code Examples
- TPM2-TSS initialization and context management (`Tss2_TctiLdr_Initialize`)
- TPM key generation and storage (`TPMA_OBJECT`, `TPM2_CreatePrimary`)
- SGX enclave creation and initialization (`sgx_create_enclave`)
- Remote attestation quote generation and verification (`TPM2_Quote`)
- Sealed storage implementation (TPM sealing, SGX sealing)
- Measured boot chain verification (PCR validation)
- TPM-backed key storage with policy authorization
- SGX enclave ECALL/OCALL patterns

#### Acceptance Criteria
- [ ] Total lines within 2,800-3,200 range
- [ ] All 9 sections present and complete
- [ ] 2 CVEs documented with full template
- [ ] Code examples compile with C++17
- [ ] TPM2-TSS integration shown
- [ ] SGX enclave demonstrated
- [ ] Remote attestation implemented
- [ ] Exercises include 4 practical tasks
- [ ] PT-BR prose is natural and professional

---

### Task T10: Criptografia Homomórfica

| Field | Value |
|-------|-------|
| **ID** | T10 |
| **Title** | Criptografia Homomórfica |
| **Slug** | `10-criptografia-homomorfica.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,800 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | Medium |
| **Phase** | Advanced Topics |
| **Estimated Hours** | 40 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 10.1 Fundamentos de HE | FHE, PHE, SWHE, comparação | 350 |
| 10.2 Esquemas HE | BFV, BGV, CKKS, TFHE | 400 |
| 10.3 Microsoft SEAL | Instalação, configuração, operações | 400 |
| 10.4 Operações sobre Dados Criptografados | Soma, multiplicação, rotação | 350 |
| 10.5 Casos de Uso | ML federado, análise de dados sensíveis, votação | 350 |
| 10.6 Performance | Benchmarks, otimização, bootstrapping | 300 |
| 10.7 Limitações e Riscos | Noise management, ciphertext expansion | 300 |
| 10.8 Exercícios e Referências | Práticas e bibliografia | 200 |

#### CVEs to Include
- N/A (emerging technology, focus on implementation pitfalls)

#### Key Code Examples
- Microsoft SEAL setup and configuration (`SEALContext`, `EncryptionParameters`)
- BFV scheme: encrypted addition and multiplication (`Evaluator::add`, `Evaluator::multiply`)
- CKKS scheme: approximate arithmetic (complex numbers, encoding)
- TFHE: encrypted boolean circuits (gate-by-gate evaluation)
- Performance benchmarking suite (Google Benchmark + SEAL)
- Encrypted ML inference example (logistic regression on ciphertext)
- Noise budget management and bootstrapping
- Parameter selection guide (security vs performance trade-offs)

#### Acceptance Criteria
- [ ] Total lines within 2,600-3,000 range
- [ ] All 8 sections present and complete
- [ ] No CVEs (as per spec)
- [ ] Code examples compile with C++17
- [ ] Microsoft SEAL integration demonstrated
- [ ] BFV and CKKS schemes shown
- [ ] Performance benchmarks included
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch02
- [ ] PT-BR prose is natural and professional

---

### Task T11: Zero-Knowledge Proofs em C++

| Field | Value |
|-------|-------|
| **ID** | T11 |
| **Title** | Zero-Knowledge Proofs em C++ |
| **Slug** | `11-zero-knowledge-proofs.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,000 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | Medium |
| **Phase** | Advanced Topics |
| **Estimated Hours** | 44 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 11.1 Fundamentos de ZKP | Definições, propriedades, classificação | 350 |
| 11.2 Tipos de ZKP | Schnorr, Sigma protocols, SNARKs, STARKs | 400 |
| 11.3 Circuitos de Computação | R1CS, aritméticos circuits, constraints | 350 |
| 11.4 libsnark Integration | Setup, proof generation, verification | 400 |
| 11.5 Casos de Uso | ZK-authentication, verifiable computation, blockchain | 350 |
| 11.6 Performance | Proof size, verification time, trusted setup | 300 |
| 11.7 Limitações | Trusted setup, quantum resistance, complexity | 300 |
| 11.8 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
- N/A (academic focus, implementation pitfalls discussed)

#### Key Code Examples
- Schnorr protocol implementation (interactive and non-interactive)
- Simple SNARK circuit (libsnark) for range proof
- ZK-authentication system (password-based ZKP)
- Verifiable computation example (outsource computation with proof)
- Proof verification server (REST API for proof validation)
- Performance benchmarking (proof generation vs verification time)
- Groth16 trusted setup ceremony
- Bulletproofs implementation (no trusted setup)

#### Acceptance Criteria
- [ ] Total lines within 2,800-3,200 range
- [ ] All 8 sections present and complete
- [ ] No CVEs (as per spec)
- [ ] Code examples compile with C++17
- [ ] libsnark integration demonstrated
- [ ] Schnorr protocol implemented
- [ ] ZK-authentication shown
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch02
- [ ] PT-BR prose is natural and professional

---

### Task T12: Verificação Formal de Implementações

| Field | Value |
|-------|-------|
| **ID** | T12 |
| **Title** | Verificação Formal de Implementações |
| **Slug** | `12-verificacao-formal.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,800 |
| **Dependencies** | T01 (Introdução), T02 (Constant-Time) |
| **Priority** | Medium |
| **Phase** | Advanced Topics |
| **Estimated Hours** | 40 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 12.1 Formal Verification Basics | Model checking, theorem proving, abstract interpretation | 350 |
| 12.2 Cryptol and SAW | Specifying crypto in Cryptol, verifying with SAW | 400 |
| 12.3 Property-Based Testing | Hypothesis, QuickCheck patterns for crypto | 350 |
| 12.4 Fuzzing Cryptographic Code | AFL++, LibFuzzer, crypto-aware fuzzing | 400 |
| 12.5 Differential Testing | Cross-implementation validation | 350 |
| 12.6 Side-Channel Analysis Tools | Timecop, ct-grind, memcheck | 300 |
| 12.7 CI/CD Integration | Automating verification in pipelines | 300 |
| 12.8 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
- N/A (verification methodology focus)

#### Key Code Examples
- Property-based test for AES-GCM (Hypothesis/QuickCheck pattern)
- Differential testing across OpenSSL and libsodium (cross-validation)
- AFL++ fuzzing harness for crypto functions (custom mutators)
- Timecop integration for timing analysis (`timecop_freeze`, `timecop_sleep`)
- Cryptol specification for a hash function (reference implementation)
- CI/CD pipeline for crypto verification (GitHub Actions)
- SAW verification script for crypto primitive
- Abstract interpretation for constant-time verification

#### Acceptance Criteria
- [ ] Total lines within 2,600-3,000 range
- [ ] All 8 sections present and complete
- [ ] No CVEs (as per spec)
- [ ] Code examples compile with C++17
- [ ] Property-based testing shown
- [ ] Fuzzing harness demonstrated
- [ ] Differential testing implemented
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch14
- [ ] PT-BR prose is natural and professional

---

### Task T13: Testes de Implementações Criptográficas

| Field | Value |
|-------|-------|
| **ID** | T13 |
| **Title** | Testes de Implementações Criptográficas |
| **Slug** | `13-testes-implementacoes-criptograficas.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,000 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | Medium |
| **Phase** | Advanced Topics |
| **Estimated Hours** | 44 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 13.1 Tipos de Testes | KAT, statistical, fuzzing, conformance | 300 |
| 13.2 Test Vectors | NIST vectors, Wycheproof, test vector sources | 350 |
| 13.3 Known-Answer Tests | Implementação de KATs para AES, SHA, RSA | 400 |
| 13.4 Statistical Tests for RNG | NIST SP 800-90B, Dieharder, TestU01 | 400 |
| 13.5 Conformance Testing | RFC compliance, standards compliance | 350 |
| 13.6 Performance Benchmarking | Google Benchmark, crypto benchmarks | 300 |
| 13.7 Test Automation | CI/CD integration, regression testing | 300 |
| 13.8 CVEs de Testes | Bugs found through testing | 250 |
| 13.9 Exercícios e Referências | Práticas e bibliografia | 250 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2016-0773 | OpenSSL RSS key handling info leak | 2016 | 13.8 |

#### Key Code Examples
- KAT implementation for AES-GCM (NIST test vectors)
- NIST statistical test suite for RNG (SP 800-90B)
- Wycheproof test vector parser (Google test vectors)
- Performance benchmarking suite (Google Benchmark)
- Regression test framework (catch2 integration)
- Test vector generation tool (automated KAT creation)
- Conformance testing for TLS implementations
- Side-channel test integration (timing, power)

#### Acceptance Criteria
- [ ] Total lines within 2,800-3,200 range
- [ ] All 9 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] KAT implementation shown
- [ ] Statistical tests demonstrated
- [ ] Benchmarking suite included
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch12
- [ ] PT-BR prose is natural and professional

---

### Task T14: Compliance e Normas Criptográficas

| Field | Value |
|-------|-------|
| **ID** | T14 |
| **Title** | Compliance e Normas Criptográficas |
| **Slug** | `14-compliance-normas.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,800 |
| **Dependencies** | T01 (Introdução) |
| **Priority** | Medium |
| **Phase** | Advanced Topics |
| **Estimated Hours** | 40 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 14.1 Landscape de Compliance | Visão geral das normas criptográficas | 300 |
| 14.2 FIPS 140-3 | Levels, modules, CAVP, CMVP | 400 |
| 14.3 Common Criteria | Evaluation assurance levels, targets | 350 |
| 14.4 LGPD no Brasil | Criptografia como medida de segurança, DPO | 350 |
| 14.5 ICP-Brasil | Certificados digitais, PKI brasileira | 300 |
| 14.6 eIDAS | Assinatura eletrônica, identificação | 300 |
| 14.7 Auditoria Criptográfica | Procedures, documentation, evidence | 300 |
| 14.8 Exercícios e Referências | Práticas e bibliografia | 300 |

#### CVEs to Include
- N/A (compliance focus, historical context of regulatory failures)

#### Key Code Examples
- FIPS 140-3 compliant crypto configuration (OpenSSL FIPS provider)
- LGPD data encryption implementation (data classification, encryption at rest)
- ICP-Brasil certificate handling (X.509 extensions, OID parsing)
- Compliance documentation template (security policy, procedures)
- Audit log implementation (tamper-evident logging)
- Crypto module boundary definition (module interface, self-tests)
- Key management policy enforcement (automated compliance checks)
- Evidence collection for auditors (automated reporting)

#### Acceptance Criteria
- [ ] Total lines within 2,600-3,000 range
- [ ] All 8 sections present and complete
- [ ] No CVEs (as per spec)
- [ ] Code examples compile with C++17
- [ ] FIPS 140-3 configuration shown
- [ ] LGPD implementation demonstrated
- [ ] ICP-Brasil handling included
- [ ] Exercises include 4 practical tasks
- [ ] Cross-references to Ch04, Ch07
- [ ] PT-BR prose is natural and professional

---

### Task T15: Estudo de Caso: TLS Server Seguro

| Field | Value |
|-------|-------|
| **ID** | T15 |
| **Title** | Estudo de Caso: TLS Server Seguro |
| **Slug** | `15-estudo-caso-tls-server.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 3,900 |
| **Dependencies** | T02 (Constant-Time), T04 (HSM), T05 (TLS 1.3), T07 (Key Management) |
| **Priority** | High |
| **Phase** | Integration |
| **Estimated Hours** | 60 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 15.1 Requisitos do Sistema | Threat model, performance targets, compliance | 300 |
| 15.2 Arquitetura | Component diagram, data flow, deployment | 350 |
| 15.3 TLS Server Core | OpenSSL 3.x server, SNI, ALPN, session tickets | 450 |
| 15.4 Certificate Management | ACME, Let's Encrypt, certificate rotation | 400 |
| 15.5 HSM Integration | Key storage, signing operations | 400 |
| 15.6 Security Monitoring | Logging, alerting, anomaly detection | 350 |
| 15.7 Performance Tuning | Benchmarks, optimization, connection pooling | 350 |
| 15.8 Hardening | Security headers, cipher suites, OCSP stapling | 350 |
| 15.9 Deployment | Container, Kubernetes, load balancing | 300 |
| 15.10 Lessons Learned | Common pitfalls, post-mortem analysis | 250 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2014-0160 | Heartbleed (context: server hardening) | 2014 | 15.8 |

#### Key Code Examples
- Complete TLS server with OpenSSL 3.x (production-ready)
- ACME client integration (Let's Encrypt automation)
- Certificate rotation mechanism (zero-downtime rotation)
- HSM-backed key management (CloudHSM integration)
- Security monitoring dashboard (Prometheus metrics)
- Load balancer configuration (nginx with TLS termination)
- Health check endpoints (liveness, readiness probes)
- Performance benchmarking (connections/sec, latency)
- Security headers implementation (HSTS, CSP, etc.)
- OCSP stapling and certificate transparency

#### Acceptance Criteria
- [ ] Total lines within 3,700-4,100 range
- [ ] All 10 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] Complete TLS server implemented
- [ ] ACME integration shown
- [ ] HSM integration demonstrated
- [ ] Monitoring dashboard included
- [ ] Exercises include 5 practical tasks
- [ ] PT-BR prose is natural and professional

---

### Task T16: Boas Práticas e Checklist de Produção

| Field | Value |
|-------|-------|
| **ID** | T16 |
| **Title** | Boas Práticas e Checklist de Produção |
| **Slug** | `16-boas-praticas-checklist.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,800 |
| **Dependencies** | All previous chapters |
| **Priority** | High |
| **Phase** | Integration |
| **Estimated Hours** | 40 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 16.1 Pre-Deployment Checklist | Security review, code audit, penetration testing | 350 |
| 16.2 Production Configuration | Cipher suites, key sizes, protocols | 350 |
| 16.3 Monitoring and Alerting | Metrics, logging, anomaly detection | 350 |
| 16.4 Incident Response | Crypto-specific response procedures | 350 |
| 16.5 Key Compromise Procedures | Revocation, rotation, notification | 300 |
| 16.6 Update and Patch Management | Crypto library updates, deprecation | 300 |
| 16.7 Documentation | Security documentation, runbooks | 300 |
| 16.8 Exercícios e Referências | Práticas e bibliografia | 300 |

#### CVEs to Include
| CVE ID | Title | Year | Section |
|--------|-------|------|---------|
| CVE-2017-1000364 | Cloudbleed memory leak (context: monitoring) | 2017 | 16.3 |

#### Key Code Examples
- Pre-deployment security checklist (automated validation script)
- Production configuration templates (cipher suites, key sizes)
- Monitoring dashboard implementation (Grafana + Prometheus)
- Incident response runbook (crypto-specific procedures)
- Key compromise response procedures (revocation, rotation)
- Update automation scripts (dependency scanning, patching)
- Security documentation generator (automated runbook creation)
- Compliance validation suite (pre-deploy checks)

#### Acceptance Criteria
- [ ] Total lines within 2,600-3,000 range
- [ ] All 8 sections present and complete
- [ ] 1 CVE documented with full template
- [ ] Code examples compile with C++17
- [ ] Checklists comprehensive
- [ ] Monitoring shown
- [ ] Incident response documented
- [ ] Exercises include 4 practical tasks
- [ ] PT-BR prose is natural and professional

---

### Task T17: Conclusão e Tendências Futuras

| Field | Value |
|-------|-------|
| **ID** | T17 |
| **Title** | Conclusão e Tendências Futuras |
| **Slug** | `17-conclusao-tendencias.md` |
| **Directory** | `/home/Projetos/DevSecurity/cryptography/` |
| **Target Lines** | 2,000 |
| **Dependencies** | All previous chapters |
| **Priority** | Low |
| **Phase** | Integration |
| **Estimated Hours** | 24 |

#### Section Breakdown
| Section | Content | Est. Lines |
|---------|---------|------------|
| 17.1 Resumo do Livro | Recapitulação dos 17 capítulos | 400 |
| 17.2 Lições Aprendidas | Padrões, anti-padrões, insights | 300 |
| 17.3 Tendências Emergentes | PQC, FHE, ZKP, verificação formal | 400 |
| 17.4 Ameaças Futuras | Quantum computing, AI-assisted attacks | 300 |
| 17.5 Recursos para Continuar | Certificações, comunidades, conferências | 300 |
| 17.6 Agradecimentos Finais | Créditos e encerramento | 300 |

#### CVEs to Include
- N/A (concluding chapter)

#### Key Code Examples
- Summary of key code patterns from the book (consolidated reference)
- Future-looking code examples (PQC migration, FHE basics)
- Reference implementation of best practices (comprehensive example)
- Quick reference cheat sheet (common API calls)
- Migration checklist implementation

#### Acceptance Criteria
- [ ] Total lines within 1,800-2,200 range
- [ ] All 6 sections present and complete
- [ ] No CVEs (as per spec)
- [ ] Code examples compile with C++17
- [ ] Book summary comprehensive
- [ ] Future trends documented
- [ ] Exercises include 3 practical tasks
- [ ] PT-BR prose is natural and professional

---

## Critical Path Analysis

### Critical Path (Longest Dependency Chain)

```
T00 (0h) → T01 (40h) → T02 (48h) → T03 (52h) → T12 (40h) → T15 (60h) → T16 (40h) → T17 (24h)
```

**Total Critical Path Duration**: 304 hours

### Parallel Execution Opportunities

| Wave | Tasks | Max Parallel | Estimated Duration |
|------|-------|--------------|-------------------|
| Wave 1 | T00 | 1 | 8h |
| Wave 2 | T01 | 1 | 40h |
| Wave 3 | T02, T04, T05, T07, T10 | 5 | 56h (T05 longest) |
| Wave 4 | T03, T06, T08, T09, T11 | 5 | 52h (T03 longest) |
| Wave 5 | T12, T13, T14 | 3 | 44h (T13 longest) |
| Wave 6 | T15 | 1 | 60h |
| Wave 7 | T16 | 1 | 40h |
| Wave 8 | T17 | 1 | 24h |

**Optimal Parallel Duration**: ~324 hours (with 5 parallel writers)

### Resource Requirements

| Resource | Quantity | Purpose |
|----------|----------|---------|
| Technical Writers | 5 | Parallel chapter writing |
| C++ Developers | 2 | Code example validation |
| Security Reviewers | 1 | CVE accuracy verification |
| PT-BR Editors | 1 | Language quality assurance |

---

## Effort Summary

| Phase | Chapters | Hours | Lines | Writers |
|-------|----------|-------|-------|---------|
| Foundation | T00, T01, T02, T03 | 148 | 11,200 | 2 |
| Hardware & Protocols | T04, T05, T06, T07, T08, T09 | 284 | 19,200 | 5 |
| Advanced Topics | T10, T11, T12, T13, T14 | 208 | 14,400 | 3 |
| Integration | T15, T16, T17 | 124 | 8,700 | 2 |
| **Total** | **18** | **764** | **53,500** | — |

---

## Acceptance Criteria Summary

### Global Acceptance Criteria

- [ ] All 18 chapters completed
- [ ] Total lines: 53,500 ± 3,000
- [ ] 20 unique CVEs documented
- [ ] All code examples compile with C++17
- [ ] PT-BR prose is natural and professional
- [ ] English code identifiers consistent
- [ ] Cross-references validated
- [ ] Library versions documented
- [ ] Exercises include practical tasks
- [ ] CVE templates complete

### Per-Chapter Acceptance Criteria

Each chapter must:
- [ ] Meet target line count (±200 lines)
- [ ] Include all sections from outline
- [ ] Document assigned CVEs with full template
- [ ] Include compilable code examples
- [ ] Include 3-5 practical exercises
- [ ] Maintain PT-BR prose quality
- [ ] Use English code identifiers
- [ ] Include cross-references to related chapters

---

## Next Recommended Step

**sdd-apply**: Begin implementation with Wave 1 (T00) and Wave 2 (T01), then proceed with parallel execution of Wave 3.

**Priority Order**:
1. T00 (Prefácio) — foundation, no dependencies
2. T01 (Introdução) — core chapter, enables all others
3. T02, T04, T05, T07, T10 — parallel execution after T01
4. Continue with dependent chapters as prerequisites complete

**Resource Allocation**:
- Assign 1 writer to T00 + T01 (sequential)
- Assign 5 writers to Wave 3 (parallel)
- Coordinate CVE accuracy with security reviewer
- Validate PT-BR prose with editor
