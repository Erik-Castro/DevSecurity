# Spec: Book 5 — Cryptography Engineering in C++

**Change**: cryptography-engineering  
**Status**: Draft  
**Date**: 2026-06-15  
**Target**: 18 chapters, 2,800–3,900 lines each, PT-BR prose, English code

---

## Book Metadata

- **Title**: Engenharia Criptográfica em C++
- **Directory**: `/home/Projetos/DevSecurity/cryptography/`
- **Language**: PT-BR prose, English code identifiers
- **Code Standard**: C++17, OpenSSL 3.x, libsodium, liboqs, Botan, TPM2-TSS
- **Total CVEs**: 20+ unique CVEs across all chapters
- **Minimum Lines**: 800 per chapter (absolute floor)
- **Target Lines**: 2,800–3,900 per chapter
- **Total Target**: 50,400–70,200 lines

---

## Library Comparison Matrix

| Library | Version | Language | FIPS | PQC | HSM | Best For |
|---------|---------|----------|------|-----|-----|----------|
| OpenSSL 3.x | 3.0+ | C | Yes (FIPS provider) | No | PKCS#11 | TLS, general crypto, HSM integration |
| libsodium | 1.0.19+ | C | No | No | No | Modern crypto, easy API, constant-time |
| liboqs | 0.10+ | C | No | Yes (NIST PQC) | No | Post-quantum algorithms |
| Botan | 3.0+ | C++ | Yes (FIPS module) | Partial | No | C++ native, algorithm variety |
| TPM2-TSS | 4.0+ | C | Yes | No | TPM 2.0 | Hardware root of trust |
| Microsoft SEAL | 4.0+ | C++ | No | No | No | Homomorphic encryption |
| libsnark | 2.0+ | C++ | No | No | No | Zero-knowledge proofs |

## Algorithm Comparison Tables

### Symmetric Encryption

| Algorithm | Key Size | Block/Stream | Constant-Time | Libraries | Status |
|-----------|----------|--------------|---------------|-----------|--------|
| AES-GCM | 128/192/256 | 128-bit block | HW-accelerated | OpenSSL, libsodium, Botan | Recommended |
| ChaCha20-Poly1305 | 256 | Stream | Yes (software) | OpenSSL, libsodium | Recommended |
| XChaCha20-Poly1305 | 256 | Stream | Yes (software) | libsodium | Nonce-misuse resistant |
| AES-SIV | 256/512 | 128-bit block | Yes | libsodium | Nonce-misuse resistant |

### Key Exchange

| Algorithm | Type | PQC-Ready | Libraries | Security Level |
|-----------|------|-----------|-----------|----------------|
| X25519 | ECDH | No | OpenSSL, libsodium | 128-bit |
| X448 | ECDH | No | OpenSSL | 224-bit |
| ML-KEM-768 | Lattice | Yes | liboqs | 192-bit (NIST) |
| ML-KEM-1024 | Lattice | Yes | liboqs | 256-bit (NIST) |
| ECDH-P256 | ECDH | No | OpenSSL, Botan | 128-bit |

### Digital Signatures

| Algorithm | Signature Size | Speed | PQC-Ready | Libraries |
|-----------|---------------|-------|-----------|-----------|
| Ed25519 | 64 bytes | Fast | No | OpenSSL, libsodium |
| ECDSA-P256 | 64 bytes | Medium | No | OpenSSL, Botan |
| ML-DSA-65 | 3,293 bytes | Slow | Yes | liboqs |
| SLH-DSA-128s | 7,856 bytes | Very slow | Yes | liboqs |
| RSA-PSS | 256+ bytes | Slow | No | OpenSSL, Botan |

### Hash Functions

| Algorithm | Output | Speed | Security | Libraries |
|-----------|--------|-------|----------|-----------|
| SHA-256 | 256 bits | Fast | 128-bit | OpenSSL, libsodium, Botan |
| SHA-3-256 | 256 bits | Medium | 128-bit | OpenSSL, Botan |
| BLAKE2b | 256 bits | Very fast | 128-bit | libsodium |
| BLAKE3 | 256 bits | Fastest | 128-bit | External lib |

### Authenticated Encryption

| Scheme | Nonce Size | Max Message | Libraries | Use Case |
|--------|-----------|-------------|-----------|----------|
| AES-GCM | 96 bits | ~64 GB | OpenSSL, Botan | General purpose |
| ChaCha20-Poly1305 | 96 bits | ~256 GB | OpenSSL, libsodium | Mobile, embedded |
| AES-GCM-SIV | 96 bits | ~64 GB | libsodium | Nonce-misuse |
| XChaCha20-Poly1305 | 192 bits | ~256 GB | libsodium | Random nonces |

---

## Side-Channel Attack Comparison

| Attack Type | Vector | Complexity | Mitigation | Chapter |
|-------------|--------|------------|------------|---------|
| Timing | Execution time | Low | Constant-time code | Ch02 |
| Power Analysis (SPA) | Power consumption | Medium | Masking, shuffling | Ch03 |
| Power Analysis (DPA) | Statistical power | High | Higher-order masking | Ch03 |
| Cache-Timing | Cache behavior | Medium | Constant-time access | Ch03 |
| Branch Prediction | Branch predictor | High | Branchless code | Ch03 |
| Electromagnetic | EM emanations | High | Shielding, masking | Ch03 |
| Acoustic | Sound waves | Very high | Physical isolation | Ch03 |
| Fault Injection | Hardware faults | High | Redundancy, checks | Ch03 |

## Compliance Standards Matrix

| Standard | Region | Focus | Levels | Chapter |
|----------|--------|-------|--------|---------|
| FIPS 140-3 | USA/Canada | Crypto modules | 1-4 | Ch14 |
| Common Criteria | International | Security evaluation | EAL1-7 | Ch14 |
| LGPD | Brazil | Data protection | N/A | Ch14 |
| ICP-Brasil | Brazil | Digital certificates | N/A | Ch14 |
| eIDAS | EU | Electronic identification | Low/Medium/High | Ch14 |
| PCI DSS | International | Payment card data | 1-4 | Ch14 |
| HIPAA | USA | Healthcare data | N/A | Ch14 |

## Chapter 00 — Prefácio

**Slug**: `00-prefacio.md`  
**Target Lines**: 1,800  
**Dependencies**: None

### Learning Objectives
1. Compreender o escopo e a abordagem do livro
2. Identificar pré-requisitos e audiência-alvo
3. Entender como navegar entre capítulos

### Section Outline
| Section | Content | Est. Lines |
|---------|---------|------------|
| 0.1 Saudação e Motivação | Por que engenharia criptográfica é diferente de usar criptografia | 200 |
| 0.2 Audiência-Alvo | C++ devs, security engineers, DevSecOps | 150 |
| 0.3 Pré-requisitos | Conhecimento C++17, conceitos básicos de criptografia (Book 1) | 200 |
| 0.4 Estrutura do Livro | Como os 18 capítulos se conectam, caminhos de leitura | 300 |
| 0.5 Convenções do Código | OpenSS 3.x, libsodium, liboqs, Botan, TPM2-TSS | 200 |
| 0.6 Como Usar Este Livro | Exercícios, estudos de caso, laboratórios | 200 |
| 0.7 Agradecimentos | Créditos e referências | 150 |
| 0.8 Nota sobre CVEs | Como analisamos vulnerabilidades reais | 200 |
| 0.9 Segurança em Português | Preenchendo a lacuna na literatura técnica PT-BR | 200 |

### Code Examples
- None (introductory chapter)

### Exercises
1. Instalar OpenSSL 3.x, libsodium e liboqs e compilar um exemplo básico
2. Identificar 3 vulnerabilidades criptográficas recentes e suas implicações
3. Projetar um fluxograma de um sistema de criptografia completo

---

## Chapter 01 — Introdução à Engenharia Criptográfica

**Slug**: `01-introducao-engenharia-criptografica.md`  
**Target Lines**: 2,800  
**Dependencies**: Chapter 00

### Learning Objectives
1. Diferenciar "usar criptografia" de "construir sistemas criptográficos"
2. Identificar os principais desafios de engenharia em implementações criptográficas
3. Compreender o ciclo de vida de uma vulnerabilidade criptográfica
4. Analisar a arquitetura de um sistema criptográfico seguro

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2008-0166 | Debian OpenSSL predictable RNG | 2008 | 1.8 |
| CVE-2013-2099 | Android PRNG vulnerability | 2013 | 1.8 |
| CVE-2014-0160 | Heartbleed OpenSSL over-read | 2014 | 1.8 |

### Code Examples
- Basic OpenSSL 3.x context initialization (`OSSL_LIB_CTX`, `EVP_PROVIDER`)
- Secure random number generation comparison (`RAND_bytes` vs `std::random_device` vs `getrandom`)
- Key derivation function (PBKDF2) with `EVP_KDF` API
- Simple authenticated encryption with libsodium (`crypto_aead_xchacha20poly1305_ietf`)
- Provider pattern interface for crypto abstraction
- Entropy source detection and validation

### Exercises
1. Implementar um sistema de criptografia simples e identificar 3 pontos de falha
2. Analisar o Debian OpenSSL bug e reproduzir o problema em ambiente controlado
3. Projetar uma arquitetura de segurança para um sistema de pagamento
4. Implementar um provider pattern para abstrair provedores de criptografia

### Dependencies
- Chapter 00 (Prefácio)
- Book 1 Chapter 8 (Criptografia e Gestão de Chaves) — referência

---

## Chapter 02 — Fundamentos de Constant-Time Programming

**Slug**: `02-fundamentos-constant-time.md`  
**Target Lines**: 3,200  
**Dependencies**: Chapter 01

### Learning Objectives
1. Compreender como ataques de timing funcionam em implementações criptográficas
2. Implementar comparações constant-time em C++17
3. Identificar e eliminar branches dependentes de dados em código criptográfico
4. Utilizar técnicas de memória constante-time para operações sensíveis
5. Medir e validar o timing de implementações

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2013-0169 | Lucky13 CBC padding oracle timing | 2013 | 2.8 |
| CVE-2019-15809 | Minerva ECDSA timing attack | 2019 | 2.8 |
| CVE-2020-1968 | Raccoon DH key computation timing | 2020 | 2.8 |

### Code Examples
- Constant-time comparison function (OpenSSL `CRYPTO_memcmp` vs custom `secure_compare`)
- Branchless conditional move patterns (`cmov` emulation, ternary with masking)
- Timing measurement harness with `std::chrono::high_resolution_clock`
- Constant-time AES implementation wrapper (AES-NI vs software)
- Cache-timing attack demonstration (educational `flushreload.c`)
- Secure memory zeroing with compiler barrier (`explicit_bzero`, `OPENSSL_cleanse`)
- Timing test statistical analysis (chi-squared, t-test)

### Exercises
1. Implementar uma comparação constant-time e demonstrar timing attack vs vanilla comparison
2. Medir timing de operações de chave em diferentes cenários de cache
3. Converter um código com branches dependentes de dados para branchless
4. Criar um timing test que valide a constância de uma implementação

### Dependencies
- Chapter 01 (Introdução)
- Chapter 04 (Side-Channel Attacks) — cross-reference

---

## Chapter 03 — Ataques de Canal Lateral Avançados

**Slug**: `03-ataques-canal-lateral.md`  
**Target Lines**: 3,400  
**Dependencies**: Chapter 02

### Learning Objectives
1. Classificar ataques de canal lateral por vetor de ataque e complexidade
2. Implementar contramedidas para power analysis (SPA, DPA, CPA)
3. Compreender cache-timing attacks (Flush+Reload, Prime+Probe)
4. Projetar software resistente a side-channel para hardware específico

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2022-23935 | Hertzbleed frequency throttling side-channel | 2022 | 3.9 |
| CVE-2022-40982 | Downfall Gather data sampling | 2023 | 3.9 |
| CVE-2019-11090 | TPM-FAIL Intel TPM timing attack | 2019 | 3.9 |

### Code Examples
- Power analysis measurement setup (educational with `perf`)
- Flush+Reload cache-timing attack PoC (`clflush`, `rdtsc`)
- Prime+Probe demonstration (L3 cache occupancy)
- Masking countermeasure implementation (boolean masking, Ishai-Sahai-Wagner)
- Shuffling countermeasure for lookup tables (AES S-box)
- Memory access pattern obfuscation (ORAM simulation)
- Spectre v1 gadget detection and mitigation

### Exercises
1. Implementar um ataque Flush+Reload em uma S-box de AES
2. Projetar uma implementação masking para operações de chave
3. Criar um ataque DPA simplificado e demonstrar contramedidas
4. Analisar o impacto de Spectre mitigations em performance de criptografia

### Dependencies
- Chapter 02 (Constant-Time)
- Chapter 04 (Side-Channel Attacks) — cross-reference
- Chapter 14 (Testes) — para validação

---

## Chapter 04 — HSM e Tokens de Segurança

**Slug**: `04-hsm-tokens-seguranca.md`  
**Target Lines**: 3,000  
**Dependencies**: Chapter 01

### Learning Objectives
1. Integrar hardware security modules via PKCS#11 em C++
2. Configurar e usar cloud HSM services (AWS, Azure, GCP)
3. Implementar key ceremony procedures seguras
4. Projetar arquiteturas com HSM para alta disponibilidade

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2017-15361 | ROCA Infineon RSA key generation flaw | 2017 | 4.8 |

### Code Examples
- PKCS#11 initialization and token enumeration (`C_Initialize`, `C_GetSlotList`)
- Key generation via HSM (RSA, EC) using `C_GenerateKeyPair`
- Signing and verification with HSM keys (`C_Sign`, `C_Verify`)
- Connection pooling for HSM sessions (thread-safe wrapper)
- AWS CloudHSM integration example (`cloudhsm.hsm_client`)
- Key ceremony procedure automation (M-of-N approval workflow)
- HSM-backed TLS certificate storage

### Exercises
1. Configurar um SoftHSM para desenvolvimento e integrar via PKCS#11
2. Implementar key rotation com HSM
3. Projetar um sistema de key ceremony com multi-person control
4. Criar um benchmark de performance HSM vs software

### Dependencies
- Chapter 01 (Introdução)
- Chapter 08 (Gestão de Chaves Avançada) — cross-reference

---

## Chapter 05 — TLS 1.3: Internals e Implementação

**Slug**: `05-tls13-internals.md`  
**Target Lines**: 3,600  
**Dependencies**: Chapters 01, 02

### Learning Objectives
1. Entender o handshake TLS 1.3 byte-a-byte
2. Implementar um client TLS 1.3 mínimo em C++ com OpenSSL 3.x
3. Compreender o key schedule e key derivation
4. Analisar e mitigar vulnerabilidades TLS 1.3

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2013-0169 | Lucky13 CBC padding oracle | 2013 | 5.9 |
| CVE-2014-3566 | POODLE SSL 3.0 padding oracle | 2014 | 5.9 |
| CVE-2015-0204 | FREAK export cipher downgrade | 2015 | 5.9 |
| CVE-2014-3513 | Triple Handshake session resumption | 2014 | 5.9 |

### Code Examples
- TLS 1.3 client with OpenSSL 3.x (`SSL_CTX_set_min_proto_version`, `SSL_set_tlsext_host_name`)
- TLS 1.3 server implementation (`SSL_CTX_use_PrivateKey_file`, `SSL_accept`)
- 0-RTT early data handling (`SSL_CTX_set_max_early_data`, `SSL_get_early_data_status`)
- Certificate validation and pinning (`X509_STORE`, custom verify callback)
- Session ticket implementation (PSK resumption)
- TLS 1.3 handshake debugger/parser (WYSIWYT approach)
- Custom cipher suite configuration
- OCSP stapling implementation

### Exercises
1. Implementar um TLS 1.3 client completo e conectar a um servidor real
2. Capturar e analisar um handshake TLS 1.3 com Wireshark
3. Implementar certificate pinning para um servidor específico
4. Criar um TLS server com suporte a SNI e ALPN
5. Analisar o ataque POODLE e implementar contramedidas

### Dependencies
- Chapter 01 (Introdução)
- Chapter 02 (Constant-Time)
- Chapter 04 (HSM) — para key storage

---

## Chapter 06 — Criptografia Pós-Quântica: Migração Prática

**Slug**: `06-criptografia-pos-quantica.md`  
**Target Lines**: 3,200  
**Dependencies**: Chapters 01, 05

### Learning Objectives
1. Compreender os algoritmos NIST PQC (ML-KEM, ML-DSA, SLH-DSA)
2. Implementar hybrid cryptographic schemes em C++
3. Realizar inventário criptográfico de sistemas existentes
4. Planejar migração incremental para PQC

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2022-3676 | Liboqs side-channel in Kyber | 2022 | 6.9 |

### Code Examples
- liboqs basic usage (`OQS_KEM_keypair`, `OQS_KEM_encaps`, `OQS_KEM_decaps`)
- Hybrid key exchange (X25519 + ML-KEM-768)
- Cryptographic inventory scanner (binary analysis, dependency detection)
- Migration test harness (old vs new algorithm validation)
- Performance benchmarking suite (Google Benchmark + liboqs)
- PQC certificate chain handling (hybrid X.509)
- Algorithm agility pattern implementation
- Deprecation warning system for legacy algorithms

### Exercises
1. Implementar hybrid key exchange com X25519 + ML-KEM
2. Criar um scanner de inventário criptográfico para um projeto
3. Planejar migração PQC para um sistema TLS existente
4. Comparar performance de algoritmos PQC vs clássicos

### Dependencies
- Chapter 01 (Introdução)
- Chapter 05 (TLS 1.3)
- Chapter 08 (Gestão de Chaves Avançada)

---

## Chapter 07 — Gestão de Chaves Avançada

**Slug**: `07-gestao-chaves-avancada.md`  
**Target Lines**: 3,000  
**Dependencies**: Chapters 01, 04

### Learning Objectives
1. Projetar key lifecycle completo (geração, distribuição, rotação, destruição)
2. Implementar key wrapping e encapsulation em C++
3. Utilizar Shamir's Secret Sharing para distribuição de chaves
4. Implementar threshold cryptography para alta disponibilidade

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2008-0166 | Debian OpenSSL weak key generation | 2008 | 7.9 |

### Code Examples
- Key lifecycle state machine (generate → active → rotate → retire → destroy)
- AES key wrapping (RFC 3394) with `EVP_aes_256_wrap`
- Shamir's Secret Sharing implementation (GF(2^8) arithmetic)
- Threshold ECDSA signing (t-of-n party computation)
- Automated key rotation scheduler (time-based, usage-based)
- Secure memory zeroing utilities (`SecureString`, `SecureVector`)
- Key metadata management (creation date, usage count, expiry)
- Distributed key generation (DKG) protocol

### Exercises
1. Implementar Shamir's Secret Sharing com threshold (2-of-3)
2. Criar um sistema de key rotation automático
3. Implementar key wrapping com AES-KW e comparar com RSA-OAEP
4. Projetar um DKG protocol simplificado

### Dependencies
- Chapter 01 (Introdução)
- Chapter 04 (HSM e Tokens)

---

## Chapter 08 — Protocolos Criptográficos Modernos

**Slug**: `08-protocolos-criptograficos-modernos.md`  
**Target Lines**: 3,200  
**Dependencies**: Chapters 01, 02, 05

### Learning Objectives
1. Compreender o Noise Protocol Framework e suas construction patterns
2. Analisar a arquitetura criptográfica do Signal Protocol
3. Implementar WireGuard-like handshake em C++
4. Entender o Messaging Layer Security (MLS) protocol

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2015-4000 | Logjam DHE export cipher downgrade | 2015 | 8.8 |
| CVE-2016-2183 | SWEET32 birthday attack | 2016 | 8.8 |
| CVE-2021-3449 | OpenSSL NULL pointer dereference | 2021 | 8.8 |

### Code Examples
- Noise protocol handshake (Noise_IK pattern) with `noise-c-*` library
- Signal Protocol Double Ratchet implementation (X3DH + symmetric ratchet)
- WireGuard-like key exchange (Noise_IK, ChaCha20-Poly1305, Curve25519)
- MLS group key management (TreeKEM, group operations)
- Protocol state machine (formal state transitions)
- Security proof annotations (provable security comments)
- Message encryption/decryption with forward secrecy
- Group key agreement protocol

### Exercises
1. Implementar um Noise handshake pattern completo
2. Analisar o Signal Protocol e documentar cada passo criptográfico
3. Criar um protocolo de mensagem seguro usando Double Ratchet
4. Implementar group key agreement para 3 participantes

### Dependencies
- Chapter 01 (Introdução)
- Chapter 02 (Constant-Time)
- Chapter 05 (TLS 1.3)

---

## Chapter 09 — Hardware Security: TPM e Enclaves

**Slug**: `09-hardware-security-tpm-enclaves.md`  
**Target Lines**: 3,000  
**Dependencies**: Chapters 01, 04

### Learning Objectives
1. Integrar TPM 2.0 em aplicações C++ via TPM2-TSS
2. Utilizar Intel SGX enclaves para computação segura
3. Compreender ARM TrustZone para dispositivos móveis
4. Implementar remote attestation para verificação de integridade

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2019-11090 | TPM-FAIL Intel TPM timing attack | 2019 | 9.8 |
| CVE-2019-16863 | TPM-FAIL AMD fTPM timing attack | 2019 | 9.8 |

### Code Examples
- TPM2-TSS initialization and context management (`Tss2_TctiLdr_Initialize`)
- TPM key generation and storage (`TPMA_OBJECT`, `TPM2_CreatePrimary`)
- SGX enclave creation and initialization (`sgx_create_enclave`)
- Remote attestation quote generation and verification (`TPM2_Quote`)
- Sealed storage implementation (TPM sealing, SGX sealing)
- Measured boot chain verification (PCR validation)
- TPM-backed key storage with policy authorization
- SGX enclave ECALL/OCALL patterns

### Exercises
1. Configurar TPM2-TSS em ambiente de desenvolvimento
2. Criar um SGX enclave que realize operações de criptografia
3. Implementar remote attestation para verificar integridade de um enclaves
4. Comparar TPM vs SGX para armazenamento de chaves

### Dependencies
- Chapter 01 (Introdução)
- Chapter 04 (HSM e Tokens)

---

## Chapter 10 — Criptografia Homomórfica

**Slug**: `10-criptografia-homomorfica.md`  
**Target Lines**: 2,800  
**Dependencies**: Chapter 01

### Learning Objectives
1. Compreender os conceitos de criptografia homomórfica (FHE, PHE, SWHE)
2. Utilizar Microsoft SEAL para computação sobre dados criptografados
3. Identificar casos de uso reais para HE
4. Analisar trade-offs de performance e segurança

### Section Outline
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

### CVEs to Document
- N/A (emerging technology, focus on implementation pitfalls)

### Code Examples
- Microsoft SEAL setup and configuration (`SEALContext`, `EncryptionParameters`)
- BFV scheme: encrypted addition and multiplication (`Evaluator::add`, `Evaluator::multiply`)
- CKKS scheme: approximate arithmetic (complex numbers, encoding)
- TFHE: encrypted boolean circuits (gate-by-gate evaluation)
- Performance benchmarking suite (Google Benchmark + SEAL)
- Encrypted ML inference example (logistic regression on ciphertext)
- Noise budget management and bootstrapping
- Parameter selection guide (security vs performance trade-offs)

### Exercises
1. Implementar soma e multiplicação homomórfica com BFV
2. Criar um sistema de votação com HE
3. Otimizar parâmetros de CKKS para um caso de uso específico
4. Comparar performance de diferentes esquemas HE

### Dependencies
- Chapter 01 (Introdução)
- Chapter 02 (Constant-Time) — para operações sensíveis

---

## Chapter 11 — Zero-Knowledge Proofs em C++

**Slug**: `11-zero-knowledge-proofs.md`  
**Target Lines**: 3,000  
**Dependencies**: Chapter 01

### Learning Objectives
1. Compreender os conceitos fundamentais de ZKP (completeness, soundness, zero-knowledge)
2. Implementar ZKPs usando bibliotecas como libsnark ou circom
3. Aplicar ZKPs em casos de uso reais (autenticação, verificação)
4. Analisar trade-offs de performance e segurança

### Section Outline
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

### CVEs to Document
- N/A (academic focus, implementation pitfalls discussed)

### Code Examples
- Schnorr protocol implementation (interactive and non-interactive)
- Simple SNARK circuit (libsnark) for range proof
- ZK-authentication system (password-based ZKP)
- Verifiable computation example (outsource computation with proof)
- Proof verification server (REST API for proof validation)
- Performance benchmarking (proof generation vs verification time)
- Groth16 trusted setup ceremony
- Bulletproofs implementation (no trusted setup)

### Exercises
1. Implementar o protocolo Schnorr para autenticação
2. Criar um circuito SNARK para verificação de idade
3. Construir um sistema de verificação de conhecimento zero
4. Analisar o impacto do trusted setup na segurança

### Dependencies
- Chapter 01 (Introdução)
- Chapter 02 (Constant-Time) — para operações sensíveis

---

## Chapter 12 — Verificação Formal de Implementações

**Slug**: `12-verificacao-formal.md`  
**Target Lines**: 2,800  
**Dependencies**: Chapters 01, 02

### Learning Objectives
1. Utilizar ferramentas de formal verification para código criptográfico
2. Implementar property-based testing para algoritmos de criptografia
3. Aplicar fuzzing dirigido a implementações criptográficas
4. Compreender differential testing para validação cruzada

### Section Outline
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

### CVEs to Document
- N/A (verification methodology focus)

### Code Examples
- Property-based test for AES-GCM (Hypothesis/QuickCheck pattern)
- Differential testing across OpenSSL and libsodium (cross-validation)
- AFL++ fuzzing harness for crypto functions (custom mutators)
- Timecop integration for timing analysis (`timecop_freeze`, `timecop_sleep`)
- Cryptol specification for a hash function (reference implementation)
- CI/CD pipeline for crypto verification (GitHub Actions)
- SAW verification script for crypto primitive
- Abstract interpretation for constant-time verification

### Exercises
1. Criar uma property-based test para uma primitiva de hash
2. Configurar fuzzing para uma função de criptografia customizada
3. Implementar differential testing entre duas bibliotecas
4. Integrar verificação em um pipeline de CI/CD

### Dependencies
- Chapter 01 (Introdução)
- Chapter 02 (Constant-Time)
- Chapter 14 (Testes) — cross-reference

---

## Chapter 13 — Testes de Implementações Criptográficas

**Slug**: `13-testes-implementacoes-criptograficas.md`  
**Target Lines**: 3,000  
**Dependencies**: Chapter 01

### Learning Objectives
1. Projetar test vectors para primitivas criptográficas
2. Implementar known-answer tests (KATs) em C++
3. Aplicar testes estatísticos para RNGs
4. Criar suites de teste abrangentes para bibliotecas de criptografia

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2016-0773 | OpenSSL RSS key handling info leak | 2016 | 13.8 |

### Code Examples
- KAT implementation for AES-GCM (NIST test vectors)
- NIST statistical test suite for RNG (SP 800-90B)
- Wycheproof test vector parser (Google test vectors)
- Performance benchmarking suite (Google Benchmark)
- Regression test framework (catch2 integration)
- Test vector generation tool (automated KAT creation)
- Conformance testing for TLS implementations
- Side-channel test integration (timing, power)

### Exercises
1. Criar KATs para ChaCha20-Poly1305 usando vetores NIST
2. Implementar testes estatísticos para um PRNG
3. Criar uma suite de testes de regressão para uma biblioteca
4. Automatizar testes em CI/CD com Google Benchmark

### Dependencies
- Chapter 01 (Introdução)
- Chapter 12 (Verificação Formal) — cross-reference

---

## Chapter 14 — Compliance e Normas Criptográficas

**Slug**: `14-compliance-normas.md`  
**Target Lines**: 2,800  
**Dependencies**: Chapter 01

### Learning Objectives
1. Compreender FIPS 140-3 e seus níveis de segurança
2. Implementar Common Criteria para software criptográfico
3. Navegar LGPD e implicações criptográficas no Brasil
4. Projetar sistemas compliant com múltiplas normas

### Section Outline
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

### CVEs to Document
- N/A (compliance focus, historical context of regulatory failures)

### Code Examples
- FIPS 140-3 compliant crypto configuration (OpenSSL FIPS provider)
- LGPD data encryption implementation (data classification, encryption at rest)
- ICP-Brasil certificate handling (X.509 extensions, OID parsing)
- Compliance documentation template (security policy, procedures)
- Audit log implementation (tamper-evident logging)
- Crypto module boundary definition (module interface, self-tests)
- Key management policy enforcement (automated compliance checks)
- Evidence collection for auditors (automated reporting)

### Exercises
1. Configurar OpenSSL para FIPS 140-3 compliance
2. Criar documentação de compliance para um módulo criptográfico
3. Implementar LGPD-compliant data encryption
4. Projetar um sistema que atenda FIPS + Common Criteria + LGPD

### Dependencies
- Chapter 01 (Introdução)
- Chapter 04 (HSM) — para FIPS hardware requirements
- Chapter 07 (Gestão de Chaves) — para key management compliance

---

## Chapter 15 — Estudo de Caso: TLS Server Seguro

**Slug**: `15-estudo-caso-tls-server.md`  
**Target Lines**: 3,900  
**Dependencies**: Chapters 02, 04, 05, 07

### Learning Objectives
1. Projetar e implementar um TLS server de produção completo
2. Integrar HSM para armazenamento de chaves
3. Implementar certificate management automatizado
4. Configurar monitoring e logging de segurança

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2014-0160 | Heartbleed (context: server hardening) | 2014 | 15.8 |

### Code Examples
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

### Exercises
1. Implementar um TLS server completo com todas as features
2. Configurar certificate rotation automático com ACME
3. Integrar HSM para key storage e signing
4. Criar um monitoring dashboard para o server
5. Realizar load testing e otimizar performance

### Dependencies
- Chapter 02 (Constant-Time)
- Chapter 04 (HSM)
- Chapter 05 (TLS 1.3)
- Chapter 07 (Gestão de Chaves)

---

## Chapter 16 — Boas Práticas e Checklist de Produção

**Slug**: `16-boas-praticas-checklist.md`  
**Target Lines**: 2,800  
**Dependencies**: All previous chapters

### Learning Objectives
1. Criar checklists de segurança para deploy criptográfico
2. Implementar monitoring e alerting para sistemas criptográficos
3. Proceder incident response para vulnerabilidades criptográficas
4. Manter sistemas criptográficos atualizados

### Section Outline
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

### CVEs to Document
| CVE | Title | Year | Chapter Section |
|-----|-------|------|-----------------|
| CVE-2017-1000364 | Cloudbleed memory leak (context: monitoring) | 2017 | 16.3 |

### Code Examples
- Pre-deployment security checklist (automated validation script)
- Production configuration templates (cipher suites, key sizes)
- Monitoring dashboard implementation (Grafana + Prometheus)
- Incident response runbook (crypto-specific procedures)
- Key compromise response procedures (revocation, rotation)
- Update automation scripts (dependency scanning, patching)
- Security documentation generator (automated runbook creation)
- Compliance validation suite (pre-deploy checks)

### Exercises
1. Criar um checklist de segurança para um deploy criptográfico
2. Implementar monitoring para detectar anomalias criptográficas
3. Proceder um incidente de key compromise simulado
4. Criar um runbook de response para vulnerabilidades criptográficas

### Dependencies
- All previous chapters (comprehensive)

---

## Chapter 17 — Conclusão e Tendências Futuras

**Slug**: `17-conclusao-tendencias.md`  
**Target Lines**: 2,000  
**Dependencies**: All previous chapters

### Learning Objectives
1. Sintetizar os conhecimentos adquiridos ao longo do livro
2. Avaliar tendências emergentes em engenharia criptográfica
3. Planejar carreira em engenharia criptográfica

### Section Outline
| Section | Content | Est. Lines |
|---------|---------|------------|
| 17.1 Resumo do Livro | Recapitulação dos 17 capítulos | 400 |
| 17.2 Lições Aprendidas | Padrões, anti-padrões, insights | 300 |
| 17.3 Tendências Emergentes | PQC, FHE, ZKP, verificação formal | 400 |
| 17.4 Ameaças Futuras | Quantum computing, AI-assisted attacks | 300 |
| 17.5 Recursos para Continuar | Certificações, comunidades, conferências | 300 |
| 17.6 Agradecimentos Finais | Créditos e encerramento | 300 |

### CVEs to Document
- N/A (concluding chapter)

### Code Examples
- Summary of key code patterns from the book (consolidated reference)
- Future-looking code examples (PQC migration, FHE basics)
- Reference implementation of best practices (comprehensive example)
- Quick reference cheat sheet (common API calls)
- Migration checklist implementation

### Exercises
1. Criar um plano de estudos personalizado baseado nos capítulos
2. Identificar 3 áreas de estudo aprofundado
3. Projetar um projeto de código aberto usando técnicas do livro

### Dependencies
- All previous chapters

---

## Cross-Chapter CVE Summary

| # | CVE ID | Title | Year | Chapter |
|---|--------|-------|------|---------|
| 1 | CVE-2008-0166 | Debian OpenSSL predictable RNG | 2008 | 01, 07 |
| 2 | CVE-2013-0169 | Lucky13 CBC padding oracle timing | 2013 | 02, 05 |
| 3 | CVE-2013-2099 | Android PRNG vulnerability | 2013 | 01 |
| 4 | CVE-2014-0160 | Heartbleed OpenSSL over-read | 2014 | 01, 15 |
| 5 | CVE-2014-3513 | Triple Handshake session resumption | 2014 | 05 |
| 6 | CVE-2014-3566 | POODLE SSL 3.0 padding oracle | 2014 | 05 |
| 7 | CVE-2015-0204 | FREAK export cipher downgrade | 2015 | 05 |
| 8 | CVE-2015-4000 | Logjam DHE export cipher downgrade | 2015 | 08 |
| 9 | CVE-2016-0773 | OpenSSL RSS key handling info leak | 2016 | 13 |
| 10 | CVE-2016-2183 | SWEET32 birthday attack | 2016 | 08 |
| 11 | CVE-2017-15361 | ROCA Infineon RSA key generation flaw | 2017 | 04 |
| 12 | CVE-2017-1000364 | Cloudbleed memory leak | 2017 | 16 |
| 13 | CVE-2019-11090 | TPM-FAIL Intel TPM timing attack | 2019 | 03, 09 |
| 14 | CVE-2019-15809 | Minerva ECDSA timing attack | 2019 | 02 |
| 15 | CVE-2019-16863 | TPM-FAIL AMD fTPM timing attack | 2019 | 09 |
| 16 | CVE-2020-1968 | Raccoon DH key computation timing | 2020 | 02 |
| 17 | CVE-2021-3449 | OpenSSL NULL pointer dereference | 2021 | 08 |
| 18 | CVE-2022-23935 | Hertzbleed frequency throttling | 2022 | 03 |
| 19 | CVE-2022-3676 | Liboqs side-channel in Kyber | 2022 | 06 |
| 20 | CVE-2022-40982 | Downfall Gather data sampling | 2023 | 03 |

**Total unique CVEs**: 20

---

## Chapter Dependency Graph

```
Ch00 (Prefácio)
  └── Ch01 (Introdução)
        ├── Ch02 (Constant-Time) → Ch03 (Side-Channel)
        ├── Ch04 (HSM/Tokens) → Ch09 (TPM/Enclaves)
        ├── Ch05 (TLS 1.3) → Ch06 (PQC)
        ├── Ch07 (Key Management)
        ├── Ch08 (Modern Protocols)
        ├── Ch10 (Homomorphic)
        ├── Ch11 (ZKP)
        ├── Ch12 (Formal Verification)
        ├── Ch13 (Testing)
        ├── Ch14 (Compliance)
        └── Ch15 (Case Study) ← depends on Ch02, Ch04, Ch05, Ch07
              └── Ch16 (Best Practices)
                    └── Ch17 (Conclusion)
```

---

## Library Dependencies

| Library | Chapters | Purpose |
|---------|----------|---------|
| OpenSSL 3.x | 01, 02, 04, 05, 07, 08, 15 | TLS, crypto operations, PKCS#11 |
| libsodium | 01, 02, 06, 08 | Modern crypto, constant-time primitives |
| liboqs | 06, 08 | Post-quantum algorithms |
| Botan | 02, 05, 13 | Alternative crypto implementation |
| TPM2-TSS | 09 | TPM 2.0 integration |
| Microsoft SEAL | 10 | Homomorphic encryption |
| libsnark | 11 | Zero-knowledge proofs |
| Google Benchmark | 13, 15 | Performance testing |

---

## Code Quality Standards

- All code examples must compile with C++17 standard
- Use OpenSSL 3.x provider API (not deprecated 1.x API)
- Include proper error handling (exceptions or error codes)
- Use RAII for resource management
- Document memory management and cleanup
- Include compilation instructions for each example
- Test on Linux (primary), macOS (secondary)

---

## Next Recommended Step

**sdd-design**: Create detailed technical design for:
- Code example architecture and patterns
- CVE documentation structure
- Testing infrastructure
- Build system for code examples
- Quality gates and validation
