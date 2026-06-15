# Criptografia Engenheira em C++ — Índice do Livro

> **Constant-Time, Side-Channels, HSM, TLS 1.3, PQC, Key Management**

---

## Sumário Rápido

| # | Capítulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefácio](00-prefacio.md) | Motivação, público-alvo, convenções |
| 01 | [- Introducao a Engenharia Criptografica](01-introducao-engenharia-cRIPTOGRAFICA.md) | Primitivas, bibliotecas, CVEs fundamentais |
| 02 | [Fundamentos de Constant-Time](02-fundamentos-constant-time.md) | Timing attacks, cache-timing, C++17 techniques |
| 03 | [Ataques de Canal Lateral](03-ataques-canal-lateral.md) | Power analysis, EM, cache attacks, Spectre/Meltdown |
| 04 | [HSM e Tokens de Segurança](04-hsm-tokens-seguranca.md) | PKCS#11, cloud HSMs, key ceremonies |
| 05 | [TLS 1.3 — Internals e Implementação](05-tls-13-internals.md) | Handshake, key schedule, 0-RTT, OpenSSL 3.x |
| 06 | [Criptografia Pós-Quântica](06-criptografia-pos-quantica.md) | ML-KEM, ML-DSA, hybrid schemes, migration |
| 07 | [Gestão de Chaves Avançada](07-gestao-chaves-avancada.md) | Lifecycle, wrapping, threshold, distributed |
| 08 | [Protocolos Criptográficos Modernos](08-protocolos-criptograficos.md) | Signal, OPAQUE, Noise, WireGuard |
| 09 | [Hardware Security — TPM e Enclaves](09-hardware-security-tpm.md) | TPM 2.0, SGX, TrustZone, attestation |
| 10 | [Criptografia Homomórfica](10-criptografia-homomorfica.md) | FHE, BFV, CKKS, Microsoft SEAL |
| 11 | [Zero-Knowledge Proofs em C++](11-zero-knowledge-proofs.md) | zk-SNARKs, zk-STARKs, libsnark |
| 12 | [Verificação Formal](12-verificacao-formal.md) | Cryptol, SAW, ProVerif, model checking |
| 13 | [Testes de Implementações](13-testes-implementacoes.md) | Differential testing, fuzzing, Cryptofuzz |
| 14 | [Compliance e Normas](14-compliance-normas.md) | FIPS 140-3, LGPD, PCI DSS, ICP-Brasil |
| 15 | [Estudo de Caso — TLS Server Seguro em C++](15-estudo-caso-tls-server.md) | Implementação completa do zero |
| 16 | [Boas Práticas e Checklist](16-boas-praticas-checklist.md) | Anti-padrões, decisões de design, referência |
| 17 | [Conclusão e Tendências](17-conclusao-tendencias.md) | Estado atual, pesquisa futura, recursos |

---

## Diagrama de Dependências

```
            ┌──────┐
            │  00  │ Prefácio
            └──┬───┘
               │
            ┌──┴──┐
            │  01  │ ← Fundamento obrigatório
            └──┬──┘
               │
       ┌───────┼──────────────────────────────┐
       │       │                              │
   ┌───┴──┐ ┌──┴──┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴───┐
   │  02  │ │  03 │ │  04   │ │  05   │ │  06   │ │  07   │
   │ CstT │ │ Side│ │  HSM  │ │ TLS13 │ │  PQC  │ │ KeyMg │
   └──┬───┘ └──┬──┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
      │        │        │         │         │         │
      │        │     ┌──┴─────────┴─────────┴─────────┘
      │        │     │
      │     ┌──┴─────┴──────────────────────────┐
      │     │  08  │  09  │ 10  │ 11  │ 12  │ 13 │ 14 │
      │     │Proto │ TPM  │FHE  │ ZKP  │Forml│Test│Comp│
      │     └──┬───┴──┬───┴──┬──┴──┬──┴──┬──┴──┬─┴──┬─┘
      │        │      │      │     │     │     │    │
      │     ┌──┴──────┴──────┴─────┴─────┴─────┴────┘
      │     │
      │  ┌──┴──────────────────────┐
      │  │  15  │  16  │  17     │
      │  │ Case │ Chkl │ Trends  │
      │  └──────┴──────┴─────────┘
      │
```

---

## Caminhos de Leitura por Perfil

### Para Implementação TLS
```
01 → 02 → 03 → 05 → 13 → 15 → 16
```

### Para Key Management
```
01 → 04 → 07 → 08 → 14 → 16
```

### Para Migração Pós-Quântica
```
01 → 06 → 07 → 14 → 15 → 16
```

### Para Auditoria de Código Criptográfico
```
01 → 02 → 03 → 12 → 13 → 16
```

### Para Pesquisa Aplicada
```
01 → 10 → 11 → 12 → 13 → 17
```

### Cobertura Completa
```
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17
```

---

## CVEs Documentados no Livro

| CVE | Título | Capítulo |
|-----|--------|----------|
| CVE-2014-0160 | Heartbleed (buffer over-read OpenSSL) | 01, 05 |
| CVE-2008-0166 | Debian OpenSSL weak PRNG | 01 |
| CVE-2019-1547 | OpenSSL ECDSA timing | 02 |
| Lucky13 | Padding oracle TLS timing | 02 |
| Minerva | ECDSA timing side-channel | 02 |
| CVE-2017-15274 | ROCA (weak key generation) | 03 |
| CVE-2019-11091 | MDS / Microarchitectural Data Sampling | 03, 09 |
| Spectre-BHB | Branch History Buffer | 03 |
| CVE-2021-36260 | Hikvision weak crypto | 04 |
| CVE-2016-0773 | OpenSSL key recovery | 05 |
| Raccoon Attack | DH timing attack | 05 |
| ROBOT Attack | Bleichenbacher oracle | 05 |
| CVE-2022-36760 | KyberSlash (PQC timing) | 06 |
| CVE-2016-0728 | Linux keyring refcount | 07 |
| CVE-2020-26139 | IPSec implementation flaw | 08 |
| CVE-2023-0286 | X.400 type confusion | 08 |
| CVE-2021-3449 | OpenSSL NULL dereference | 08 |
| CVE-2020-0543 | L1TF / Foreshadow | 09 |
| CVE-2022-4304 | OpenSSL RSA timing | 13 |
| CVE-2021-44228 | Log4Shell (dependency management) | 16 |

---

## Bibliotecas Referenciadas

| Biblioteca | Versão | Capítulos | Uso |
|------------|--------|-----------|-----|
| OpenSSL | 3.x | 01, 02, 04, 05, 07, 15 | TLS, key management, provider API |
| libsodium | 1.0.18+ | 01, 02, 08 | AEAD, key exchange, high-level API |
| liboqs | 0.7+ | 06 | Post-quantum algorithms |
| Botan | 3.x | 01 | Alternative crypto library |
| TPM2-TSS | 4.x | 04, 09 | Hardware security modules |
| Microsoft SEAL | 4.x | 10 | Fully homomorphic encryption |
| libsnark | — | 11 | Zero-knowledge proofs |
| Cryptol | — | 12 | Formal specification |
| SAW | — | 12 | Software verification |
| ProVerif | — | 12 | Protocol verification |
| Cryptofuzz | — | 13 | Differential fuzzing |

---

## Ferramentas de Análise

| Ferramenta | Uso | Capítulos |
|------------|-----|-----------|
| Valgrind (Cachegrind/Massif) | Cache/timing analysis | 02, 03 |
| ChipWhisperer | Power analysis | 03 |
| Intel VTune | Performance profiling | 02, 03 |
| testssl.sh | TLS configuration testing | 05 |
| sslyze | TLS scanning | 05 |
| libFuzzer/AFL++ | Crypto fuzzing | 13 |
| AddressSanitizer | Memory safety | 13 |
| ThreadSanitizer | Concurrency bugs | 13 |
