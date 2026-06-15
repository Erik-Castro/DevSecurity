# Security-Driven Development — Índice do Livro

> **Desenvolvimento Seguro orientado à Segurança — C++17**
>
> 17 capítulos | ~44.700 linhas | 100+ CVEs documentados | 200+ exemplos em C++17

---

## Sumário Rápido

| # | Capítulo | Linhas |
|---|----------|--------|
| 00 | [Prefácio](00-prefacio.md) | 1.841 |
| 01 | [Introdução ao Security-Driven Development](01-introducao-ao-sdd.md) | 2.837 |
| 02 | [Ciclo de Vida Seguro de Software](02-ciclo-de-vida-seguro.md) | 3.203 |
| 03 | [Princípios de Codificação Segura](03-principios-de-codificacao-segura.md) | 2.178 |
| 04 | [Segurança de Memória em C++](04-seguranca-de-memoria-em-cpp.md) | 2.243 |
| 05 | [Tratamento de Erros e Exceções](05-tratamento-de-erros-e-excecoes.md) | 2.693 |
| 06 | [Validação de Entrada e Sanitização](06-validacao-de-entrada-e-sanitizacao.md) | 3.061 |
| 07 | [Autenticação e Autorização](07-autenticacao-e-autorizacao.md) | 3.741 |
| 08 | [Criptografia e Gestão de Chaves](08-cRIPTografia-e-chaves.md) | 2.881 |
| 09 | [Segurança de Rede](09-seguranca-de-rede.md) | 2.367 |
| 10 | [Segurança de Banco de Dados](10-seguranca-de-banco-de-dados.md) | 2.879 |
| 11 | [Segurança de API](11-seguranca-de-api.md) | 3.043 |
| 12 | [Concorrência e Segurança](12-concorrencia-e-seguranca.md) | 2.876 |
| 13 | [Testes de Segurança e Pentest](13-testes-de-seguranca-e-pentest.md) | 1.692 |
| 14 | [Compliance e Normas](14-compliance-e-normas.md) | 3.403 |
| 15 | [Resposta a Incidentes de Segurança](15-resposta-a-incidentes.md) | 2.547 |
| 16 | [Hardening e Deploy Seguro](16-hardening-e-deploy-seguro.md) | 2.496 |
| 17 | [Conclusão e Tendências](17-conclusao-e-tendencias.md) | 1.962 |
| **Total** | | **~44.756** |

---

## Índice Detalhado por Capítulo

---

### [Prefácio — Desenvolvimento Seguro orientado à Segurança](00-prefacio.md)

- **1. Por que este livro existe**
  - 1.1 A crise na segurança de software
  - 1.2 O impacto em C++
  - 1.3 Casos públicos documentados — Heartbleed, Shellshock, EternalBlue, Log4Shell, Spectre/Meltdown, SolarWinds, Qualcomm MSM (CVE-2023-33106), Android Kernel (CVE-2021-1048), Stuxnet, macOS Gatekeeper
  - 1.4 Filosofia deste livro
- **2. Obrigação Ética do Desenvolvedor**
  - 2.1 O contrato social do software
  - 2.2 Responsabilidade profissional
  - 2.3 LGPD e implicações para desenvolvedores
  - 2.4 Casos de responsabilização
  - 2.5 Casos públicos — Equifax, SolarWinds
- **3. Público-Alvo e Pré-Requisitos**
  - 3.1 Quem deve ler este livro
  - 3.2 Pré-requisitos técnicos
  - 3.3 Como usar este livro
- **4. Ambiente de Desenvolvimento**
  - 4.1 Configuração do toolchain (GCC, Clang, MSVC)
  - 4.2 Ferramentas de análise estática — clang-tidy, cppcheck, Facebook Infer
  - 4.3 Sanitizers — ASan, TSan, UBSan
  - 4.4 Fuzzing — libFuzzer, AFL++
  - 4.5 CMakeLists.txt completo com flags de segurança
  - 4.6 CMake Presets
  - 4.7 Git Hooks para segurança
  - 4.8 Exemplo completo de configuração de projeto seguro
- **5. Convenções do Livro**
  - 5.1 Blocos de código
  - 5.2 Padrão "vulnerável vs. seguro"
  - 5.3 Referências CWE/OWASP
  - 5.4 Convenções de formatação
- **6. Estrutura do Livro**

---

### [Cap 01 — Introdução ao Security-Driven Development](01-introducao-ao-sdd.md)

- **1. O que é Security-Driven Development**
  - 1.1 Definição e Princípios Fundamentais
  - 1.2 SDD versus o Modelo Tradicional
  - 1.3 A Mudança de Reativo para Proativo
  - 1.4 SDD versus DevSecOps versus Secure SDLC
  - 1.5 O Manifesto SDD
  - 1.6 Casos Públicos Documentados — Heartbleed, Shellshock, EternalBlue, Log4Shell, SolarWinds, Equifax, Target, Stuxnet, NotPetya, Samsung RKP (CVE-2024-49410), Qualcomm GPU (CVE-2023-33106), Android Binder (CVE-2023-26083)
  - 1.7 Lições Consolidadas dos Casos Documentados
- **2. Security by Design versus Security by Afterthought**
  - 2.1 Contexto Histórico
  - 2.2 O Multiplicador de Custo
  - 2.3 Decisões de Design que Eliminam Classes de Vulnerabilidades
  - 2.4 Exemplo: Hierarquia de Classes com e sem Segurança
- **3. Modelos de Ameaças**
  - 3.1 STRIDE — Spoofing, Tampering, Repudiation, Info Disclosure, DoS, EoP
  - 3.2 DREAD
  - 3.3 PASTA
- **4. OWASP Top 10 e CWE/SANS Top 25**
  - 4.1 OWASP Top 10 Mapeado para C++
  - 4.2 CWE/SANS Top 25 com Exemplos em C++
  - 4.3 Exemplos de Código Vulnerável — Command Injection, Buffer Overflow, Use-After-Free
  - 4.4 CVEs de Referência para Cada Categoria OWASP
  - 4.5 Tabela de Mapeamento Completa
- **5. Custos de Correção: Design versus Produção**
- **6. Estudo de Caso: Sistema de Login em C++**
- **7. Referências**

---

### [Cap 02 — Ciclo de Vida Seguro de Software](02-ciclo-de-vida-seguro.md)

- **1. Visão Geral do Ciclo de Vida Seguro**
  - 1.1 SDLC Tradicional vs Secure SDLC
  - 1.2 As Seis Fases do Secure SDLC
  - 1.3 Portas de Segurança em Cada Fase
  - 1.4 Papéis e Responsabilidades
  - 1.5 Estudo de Caso CVE: Portas de Segurança Ausentes
- **2. Fase de Requisitos de Segurança**
  - 2.1 Técnicas de Coleta de Requisitos
  - 2.2 User Stories de Segurança e Abuse Cases
  - 2.3 Integração com Avaliação de Risco
  - 2.4 Documento Completo: Sistema de Pagamentos em C++
  - 2.5 Requisitos Funcionais vs Não-Funcionais
  - 2.6 Elicitação Baseada em STRIDE
- **3. Fase de Design e Threat Modeling**
  - 3.1 Threat Modeling como Atividade de Design
  - 3.2 Diagramas de Fluxo de Dados (DFD)
  - 3.3 Árvores de Ataque e Superfícies de Ataque
  - 3.4 Identificação de Limites de Confiança
  - 3.5 Modelo Completo: Sistema de Processamento de Arquivos em C++
  - 3.6 Microsoft Threat Modeling Tool
- **4. Fase de Implementação Segura**
  - 4.1 Padrões de Codificação — CERT C++, MISRA
  - 4.2 Checklist de Revisão de Código
  - 4.3 Programação em Par para Código Crítico
  - 4.4 Integração de Análise Estática
  - 4.5 Hooks de Pre-commit
  - 4.6 Estudo de Caso: Heartbleed (CVE-2014-0160)
- **5. Fase de Teste de Segurança**
  - 5.1 Pirâmide de Testes de Segurança
  - 5.2 Testes Unitários para Funções de Segurança
  - 5.3 Testes de Integração
  - 5.4 Fuzzing como Estratégia de Teste
  - 5.5 Estudo de Caso: Shellshock
- **6. Fase de Deploy Seguro**
  - 6.1 Checklists de Deploy
  - 6.2 Hardening de Infraestrutura
  - 6.3 Gestão de Segredos
  - 6.4 Deploy Blue-Green e Canary
  - 6.5 Script de Deploy Seguro para C++
  - 6.6 Estudo de Caso: Equifax (CVE-2017-5638)
- **7. Fase de Monitoramento e Resposta**
  - 7.1 Monitoramento de Segurança e Logging
  - 7.2 Detecção de Intrusão
  - 7.3 Gestão de Vulnerabilidades Pós-Deploy
- **8. Shift-Left Security**
- **9. Code Review como Gate de Segurança**
- **10. Exemplo Completo: Pipeline SDD**
- **11. Referências**

---

### [Cap 03 — Princípios de Codificação Segura](03-principios-de-codificacao-segura.md)

- **1. Menor Privilégio (Least Privilege)**
  - RAII para Gerenciamento de Privilégios
  - File Descriptor Management
  - CVE: Log4Shell (CVE-2021-44228)
- **2. Defesa em Profundidade (Defense in Depth)**
  - Múltiplas Validações em C++
  - CVE: Equifax Breach (2017)
- **3. Padrões Seguros por Defeito (Fail-Safe Defaults)**
  - Controle de Acesso com Default-Deny
  - CVE: Heartbleed (CVE-2014-0160)
- **4. Separação de Deveres (Separation of Duties)**
  - Processamento de Pagamento com Separação
  - CVE: Stuxnet
- **5. Economia de Mecanismo (Economy of Mechanism)**
  - Autenticação: Complexa vs Simples
  - CVE: Shellshock (CVE-2014-6271)
- **6. Mediação Completa (Complete Mediation)**
  - TOCTOU em C++
  - CVE: EternalBlue (CVE-2017-0144)
- **7. Design Aberto (Open Design)**
  - Algoritmo Secreto vs Chave Secreta
- **8. Aceitação Psicológica (Psychological Acceptability)**
  - API Segura vs API Ruim para Criptografia
- **9. Zero Trust no Código**
- **10. Princípios Adicionais** — Work Factor, Compromise Recording, Least Astonishment
- **11. Tabela de Referência: Princípios x CWE x CVEs**
- **12. Referências**

---

### [Cap 04 — Segurança de Memória em C++](04-seguranca-de-memoria-em-cpp.md)

- **1. Fundamentos de Memória em C++**
  - Modelo de Memória do Processo
  - Alocação Dinâmica
  - Pools e Alocadores Customizados
- **2. Buffer Overflows**
  - Stack-Based, Heap-Based, Format String Attacks
  - Mitigações
- **3. Use-After-Free e Double-Free**
  - CVE-2023-33106 — Qualcomm GPU UAF
  - Heap Spray
- **4. Integer Overflows e Arithmetic**
- **5. Dangling Pointers e Reference Management**
- **6. Mitigações de Compilador e SO**
  - Stack Canaries, ASLR, DEP/NX, RELRO
  - CMake Completo, Verificação com checksec
- **7. Sanitizadores**
  - ASan, MSan, UBSan, TSan
  - Benchmarks de Sobrecarga
- **8. Smart Pointers e RAII**
  - unique_ptr, shared_ptr, weak_ptr
- **9. Safe Memory Patterns**
  - Arena Allocators
- **10. Hardening Memory Management**
  - Fortify Source, CMake Hardening
- **11. Exercício Prático** — 7 bugs para encontrar e corrigir
- **12. Referências**

---

### [Cap 05 — Tratamento de Erros e Exceções](05-tratamento-de-erros-e-excecoes.md)

- **1. Error Handling como Surface de Ataque**
  - Vazamento de Informações via Error Messages
  - Negação de Serviço via Exceções
  - CVE: Heartbleed (CVE-2014-0160)
  - CVE: Cloudbleed (CVE-2017-5882)
- **2. Leaks de Informação em Stack Traces**
  - O Que um Stack Trace Revela
  - Debug em Binários de Produção
  - Limitações do Symbol Stripping
- **3. No-Throw Guarantee e Exception Safety**
  - Quatro Níveis de Exception Safety
  - Strong Exception Safety para Operações Críticas
- **4. Error Codes vs Exceptions: Trade-offs de Segurança**
  - Falhas Silenciosas, Ataques de Exaustão
  - std::error_code e std::error_condition
- **5. Logging Seguro**
  - Sanitização de Entradas, Mascarando Dados Sensíveis
  - Logging Estruturado para Análise Forense
- **6. Tratamento de Erros em Operações Criptográficas**
- **7. Tratamento de Erros em Operações de Rede**
- **8. Assert e Debug em Produção**
  - Framework de Assertions Customizado
- **9. Estrutura de Error Handling Seguro** — Framework completo ~200 linhas
- **10. Padrões e Anti-Padrões**
  - Empty Catch, Catch-All, Throwing Sensitive Data, Object Slicing, Ignoring Error Codes, Resource Leaks, Exception in Destructor
- **11. Referências**

---

### [Cap 06 — Validação de Entrada e Sanitização](06-validacao-de-entrada-e-sanitizacao.md)

- **1. Tainted Data: O Conceito Fundamental**
  - Fluxo de Dados em C++, Classificação de Fontes
- **2. Whitelisting vs Blacklisting**
  - Biblioteca de Validação de Email e URL
- **3. Regular Expressions Seguras**
  - std::regex vs RE2 vs PCRE, ReDoS
  - Biblioteca de Validação com RE2
- **4. Validação de Tipos, Ranges e Formatos**
  - Parsing Seguro de Inteiros
- **5. Canonicalização e Path Traversal**
  - Symlink Traversal, Null Byte Injection
  - Biblioteca Segura de Caminhos em C++
- **6. SQL Injection e Parameterized Queries**
  - CVE: Heartland Payment Systems (2008)
  - SQL Injection de Segunda Ordem
- **7. Cross-Site Scripting (XSS) em Contexto C++**
  - CVE: Samy Worm MySpace (2005)
  - Output Encoding, CSP Generation
- **8. Command Injection**
  - CVE: Shellshock (CVE-2014-6271)
  - Execução Segura de Subprocessos
- **9. Injection em Formatos e Serialização**
  - Format String Vulnerabilities
  - CVE: Log4Shell (CVE-2021-44228)
  - CVE: ImageTragick (CVE-2016-3714)
  - JSON Parsing Seguro

---

### [Cap 07 — Autenticação e Autorização](07-autenticacao-e-autorizacao.md)

- **7.1 Autenticação: Fundamentos**
  - Fatores, Vulnerabilidades, Arquitetura
  - Estudo de Caso: Adobe Password Breach (2013)
- **7.2 Password Hashing Seguro**
  - Argon2id, bcrypt, Memória Segura para Senhas
  - Estudo de Caso: LinkedIn (2012), Yahoo (2013-2014)
- **7.3 Autenticação Multi-Fator (MFA/2FA)**
  - TOTP (RFC 6238), HOTP, Códigos de Backup
  - Estudo de Caso: Colonial Pipeline (2021)
- **7.4 Session Management**
  - Tokens, Cookies, Fixation Prevention
  - Estudo de Caso: Okta (2023)
- **7.5 JSON Web Tokens (JWT)**
  - Estrutura, Implementação Completa, Ataque 'none' Algorithm
- **7.6 OAuth 2.0 e OpenID Connect**
  - Fluxo com PKCE, Cliente Completo
- **7.7 Authorization: RBAC, ABAC, ACL, Capability-Based**
- **7.8 Gestão de Senhas e Segredos**
  - SecureString Completa
- **7.9 Autenticação em Protocolos de Rede**
  - mTLS, HMAC para APIs
  - Estudo de Caso: LastPass (2022)
- **7.10 Exemplo Completo: Servidor de Autenticação**
- **7.11 Referências**

---

### [Cap 08 — Criptografia e Gestão de Chaves](08-cRIPTografia-e-chaves.md)

- **1. Fundamentos de Criptografia** — Simétrica vs Assimétrica, Modos de Operação
- **2. Criptografia Simétrica**
  - AES-GCM (nonce management), ChaCha20-Poly1305
- **3. Criptografia Assimétrica**
  - RSA (CVE-2017-15361 ROCA), ECC, X25519/Ed25519
- **4. TLS 1.3**
  - Handshake, Cipher Suites
  - CVE-2015-0204 (FREAK), CVE-2014-3566 (POODLE), CVE-2014-0160 (Heartbleed)
  - HSTS
- **5. Gestão de Chaves**
  - Geração (Entropy, HKDF, PBKDF2), Armazenamento, Rotação, Destruição
  - CVE-2008-0166 (Debian Weak Keys)
- **6. Hashing e HMAC** — SHA-256, SHA-3
- **7. Assinaturas Digitais e Certificados** — X.509, Let's Encrypt
  - CVE-2015-4000 (Logjam)
- **8. Entropy e CSPRNG** — std::random_device vs Criptografia
- **9. Criptografia Pós-Quântica** — NIST candidates, DUAL_EC_DRBG backdoor

---

### [Cap 09 — Segurança de Rede](09-seguranca-de-rede.md)

- **1. Fundamentos** — Modelo OSI, Categorias de Ataques, Threat Modeling
- **2. Socket Programming Seguro** — Validação, Buffers, Timeouts
- **3. TLS/SSL Hardening** — BEAST/DROWN, Cipher Suites, OpenSSL Hardened
- **4. DNS Security** — DNS Spoofing, DNSSEC, DoH/DoT
- **5. Network Segmentation e Firewall** — Microsegmentação
- **6. DDoS Mitigation** — SYN Flood, Token Bucket, Sliding Window, Throttling
- **7. Protocol Design Seguro** — Wire Format, Replay Prevention
- **8. HTTP Security** — Headers, Middleware
- **9. Network Monitoring e Detection** — Anomalias
- **10. Exemplo Completo: HTTPS Client/Server Seguro**
- **11. Referências**

---

### [Cap 10 — Segurança de Banco de Dados](10-seguranca-de-banco-de-dados.md)

- **1. Fundamentos** — Arquitetura, Vetores de Ataque, Privilégios
- **2. Prepared Statements e Parameterized Queries**
  - SQLite, PostgreSQL libpq, Connection Strings
- **3. ORM Security** — CVE PostgreSQL (CVE-2014-0060), CVE MySQL (CVE-2012-2122)
- **4. Encryption em Repouso e em Trânsito** — TDE, Coluna, Chaves
- **5. Database Access Patterns** — Connection Pooling, Somente-Leitura
- **6. Audit Trails e Data Masking**
- **7. Backup Security** — Backup Criptografado
- **8. NoSQL Injection** — MongoDB, Redis, CouchDB
- **9. Database Migration Security**
- **10. Exemplo Completo: Database Layer Seguro**
- **11. Referências**

---

### [Cap 11 — Segurança de API](11-seguranca-de-api.md)

- **1. Fundamentos de Segurança de API**
- **2. Segurança de API REST** — Validação, Content-Type, CORS, Rate Limiting, Middleware
- **3. Rate Limiting e Throttling**
  - CVE Twitter (2020), CVE Parler (2020), CVE Facebook (2018)
  - Token Bucket, Sliding Window, Multidimensional
- **4. Segurança em GraphQL**
  - CVE GraphQL Introspection (2020), Log4Shell via API
  - Query Depth, Complexity Analysis
- **5. Segurança em gRPC** — mTLS, Interceptors, Deadlines
- **6. Padrões de API Gateway**
  - CVE Swagger/OpenAPI (2020), CVE Uber API Key (2019)
- **7. Versionamento e Deprecação Segura**
- **8. Gerenciamento de Chaves de API** — CSPRNG, Rotação
- **9. Segurança de Webhooks** — HMAC, Replay Prevention

---

### [Cap 12 — Concorrência e Segurança](12-concorrencia-e-seguranca.md)

- **1. Race Conditions como Vulnerabilidade** — TOCTOU, Bypass de Autenticação
- **2. TOCTOU Bugs e Mitigação** — CVE-2016-0728 (Keyring), File Locking
- **3. Operações Atômicas e Memory Ordering** — std::atomic, Data Races
- **4. Padrões Thread-Safe** — Mutexes, shared_mutex, Condition Variables
- **5. Lock-Free e Wait-Free Patterns** — CAS, Problema ABA
- **6. Deadlocks: Detecção e Prevenção** — Coffman, scoped_lock
- **7. Side-Channels por Tempo** — Timing Attacks, Cache-Timing, Spectre
- **8. Concorrência em Operações Criptográficas**
- **9. Segurança em Ambientes Multi-Core** — False Sharing, NUMA
- **10. Padrões de Concorrência Seguros** — Actor Model
- **11. Exercício Prático** — 5 bugs com ThreadSanitizer

---

### [Cap 13 — Testes de Segurança e Pentest](13-testes-de-seguranca-e-pentest.md)

- **Análise Estática (SAST)** — clang-tidy, cppcheck, Custom Checks, Infer
- **Análise Dinâmica (DAST)** — ASan, Valgrind, Dynamic Taint Analysis
- **Fuzzing Extensivo**
  - Heartbleed e o Poder do Fuzzing
  - AFL++, OSS-Fuzz, LibFuzzer Configuration
  - Gerenciamento de Corpus, Análise de Crashes
- **Testes de Segurança Unitários** — Boundary, Negative, Mock, Bypass
- **Penetration Testing** — Metodologia, Ferramentas C++, Checklist
- **Testes Baseados em STRIDE e OWASP Top 10**
- **Code Coverage para Segurança** — Branch/Line, Mutation Testing
- **Exemplo Completo: Fuzzer para Protocol Parser**

---

### [Cap 14 — Compliance e Normas](14-compliance-e-normas.md)

- **1. Panorama de Normas e Padrões** — Voluntário vs Obrigatório, Setor
- **2. OWASP ASVS** — Níveis V1-V14, Mapeamento C++, Checklist Completo
- **3. OWASP SAMM** — Estrutura, Maturidade, Template de Avaliação
- **4. CERT C++ Secure Coding Standard** — MEM51-CPP, STR50-CPP, INT32-CPP, CON50-CPP
- **5. MISRA C/C++** — Regras Obrigatórias, Conformidade C++17
- **6. ISO 27001 e SOC 2** — Controles, Auditoria
- **7. GDPR, LGPD e Privacidade** — Privacy by Design em C++
- **8. CWE Taxonomy e Mapping** — CWE Top 25, Oráculo de Teste
- **9. SBOM (Software Bill of Materials)** — SPDX, CycloneDX, Geração
- **10. Licenças e Dependências Seguras** — Varredura, Versionamento

---

### [Cap 15 — Resposta a Incidentes de Segurança](15-resposta-a-incidentes.md)

- **1. Planejamento de Resposta** — Plano, Comunicação, Escalação, Template
- **2. Classificação de Incidentes** — Severidade, CVSS Scoring, Implementação C++
- **3. Detecção e Análise** — Monitoramento, Análise de Log, Anomalias
- **4. Contenção** — Curto/Longo Prazo, Isolamento, Evidências
- **5. Erradicação** — Causa Raiz, Patching, Hardening, Scanner C++
- **6. Recuperação** — Restauração, Integridade, Monitoramento
- **7. Forensic Analysis de Binários** — Memória, Logs, Ferramentas C++
- **8. Disclosure Responsável** — CVE, Bug Bounty
- **9. Post-Mortem sem Culpa** — 5 Whys, Fishbone
- **10. Patching Strategies** — Hotfix, Rollback, Canary
- **11. Exemplo Completo: Runbook de Resposta a Incidente**

---

### [Cap 16 — Hardening e Deploy Seguro](16-hardening-e-deploy-seguro.md)

- **1. Compiler Hardening Flags** — fstack-protector, FORTIFY_SOURCE, PIE, RELRO, CFI
- **2. OS Hardening** — seccomp-bpf, AppArmor, Capabilities, Wrapper Completo
- **3. Container Security** — Dockerfile Hardened, K8s Security Context, CVE-2019-5736
- **4. Supply Chain Security** — SBOM, Sigstore, Reproducible Builds
  - SolarWinds (2020), Codecov (2021), xz-utils Backdoor (2024, CVE-2024-3094)
- **5. Secret Management** — Vault Patterns, Secure Memory Manager
- **6. Monitoring e Alerting** — Structured Logging, SIEM Integration
- **7. Binary Hardening** — Stripping, Anti-Debugging
- **8. Network Hardening** — mTLS, Firewall (nftables)
- **9. Exemplo Completo: Deploy Pipeline Seguro**

---

### [Cap 17 — Conclusão e Tendências](17-conclusao-e-tendencias.md)

- **1. Resumo dos Princípios Fundamentais** — Checklist do Desenvolvedor Seguro
- **2. O Desenvolvedor Seguro** — Habilidades, Certificações, Cultura
- **3. Segurança e Inteligência Artificial** — Copilot, LLMs, AI-assisted Testing
- **4. Memory-Safe Languages** — Rust, C++ Core Guidelines, Interoperabilidade
- **5. Criptografia Pós-Quântica** — NIST Standards, Migração
- **6. Computação Confidencial** — SGX, SEV, TrustZone
- **7. Zero Trust Architecture** — Microsserviços C++
- **8. WebAssembly e Segurança**
- **9. IoT e Edge Computing Security**
- **10. Formação Contínua** — CTF, Bug Bounty, Conferências
- **11. Roadmap de Estudos** — Beginner, Intermediate, Advanced
- **12. Recursos Finais** — Tools, Papers, Comunidades
- **13. Considerações Finais**

---

## Casos Públicos Documentados (CVEs) por Capítulo

| CVE | Incidente | Capítulo |
|-----|-----------|----------|
| CVE-2014-0160 | Heartbleed (OpenSSL) | 00, 01, 03, 04, 05, 08, 12, 13 |
| CVE-2014-6271 | Shellshock (Bash) | 00, 01, 03, 06, 13 |
| CVE-2017-0144 | EternalBlue/WannaCry | 00, 01, 03, 09 |
| CVE-2021-44228 | Log4Shell (Log4j) | 00, 01, 03, 06, 11 |
| CVE-2017-5753 | Spectre | 00, 04, 12 |
| CVE-2017-5715 | Meltdown | 00, 04 |
| CVE-2023-33106 | Qualcomm GPU UAF | 00, 01, 04 |
| CVE-2021-1048 | Android Kernel UAF | 00, 04 |
| CVE-2024-49410 | Samsung RKP | 01, 04 |
| CVE-2023-26083 | Android Binder | 01 |
| CVE-2017-15361 | ROCA (Infineon TPM) | 08 |
| CVE-2015-0204 | FREAK Attack | 08 |
| CVE-2014-3566 | POODLE | 08 |
| CVE-2015-4000 | Logjam | 08 |
| CVE-2008-0166 | Debian Weak Keys | 08 |
| CVE-2016-0728 | Keyring Race Condition | 12 |
| CVE-2019-5736 | Container Escape (runc) | 16 |
| CVE-2024-3094 | xz-utils Backdoor | 16 |
| CVE-2014-0060 | PostgreSQL Privilege Escalation | 10 |
| CVE-2012-2122 | MySQL Auth Bypass | 10 |
| CVE-2020-36547 | GraphQL Introspection Leak | 11 |
| CVE-2016-3714 | ImageTragick | 06 |
| CVE-2017-5882 | Cloudbleed | 05 |
| CVE-2020-36370 | Twitter API Token Leak | 11 |
| CVE-2020-36148 | Parler API Vulnerability | 11 |
| CVE-2019-11234 | Uber API Key Exposure | 11 |
| — | SolarWinds Supply Chain | 00, 02, 16 |
| — | Equifax Breach | 01, 03, 15 |
| — | Target Breach | 01, 15 |
| — | Stuxnet | 01, 03 |
| — | NotPetya | 01 |
| — | Colonial Pipeline | 07, 15 |
| — | LastPass | 07, 15 |
| — | LinkedIn/Yahoo Passwords | 07 |
| — | Adobe Password Breach | 07 |
| — | MOVEit Zero-Day | 15 |
| — | Samy Worm (MySpace) | 06 |
| — | Heartland Payment Systems | 06 |
| — | DUAL_EC_DRBG Backdoor | 08 |
