# Prefácio — Criptografia Engenheira em C++

> *"Os crackers não atacam a criptografia. Eles atacam as implementações."*
> — Bruce Schneier

---

## Sumário

1. [Por Que Este Livro Existe](#por-que-este-livro-existe)
2. [Público-Alvo](#público-alvo)
3. [Pré-Requisitos](#pré-requisitos)
4. [Estrutura do Livro](#estrutura-do-livro)
5. [Como Usar Este Livro](#como-usar-este-livro)
6. [Convenções do Livro](#convenções-do-livro)
7. [Casos Reais Documentados](#casos-reais-documentados)
8. [Bibliotecas Utilizadas](#bibliotecas-utilizadas)
9. [O Panorama da Criptografia Aplicada](#o-panorama-da-criptografia-aplicada)
10. [A Lição dos Grandes Falhos](#a-lição-dos-grandes-falhos)
11. [Engenharia vs Teoria](#engenharia-vs-teoria)
12. [Segurança é um Processo](#segurança-é-um-processo)
13. [Agradecimentos](#agradecimentos)
14. [Código-Fonte e Recursos](#código-fonte-e-recursos)
15. [Nota sobre Segurança](#nota-sobre-segurança)
16. [Edições e Atualizações](#edições-e-atualizações)
17. [Comece Agora](#comece-agora)

---

## Por Que Este Livro Existe

Criptografia é uma das áreas mais bem fundamentadas da ciência da computação. Os algoritmos são sólidos. Os protocolos são provados. As provas formais existem há décadas. E, ainda assim, aplicações que usam criptografia continuam sendo comprometidas com uma regularidade perturbadora.

Heartbleed não foi um ataque contra o TLS. Foi um buffer over-read em um código que supostamente "usava TLS corretamente". ROCA não quebrou RSA — quebrou a forma como uma smart card gerava chaves. Minerva não atacou ECDSA — explorou uma variação temporal na assinatura.

O padrão é claro: **os ataques não acontecem contra a matemática. Acontecem contra o código.**

### O Paradoxo da Criptografia

Existe um paradoxo fundamental na criptografia aplicada. Os algoritmos que usamos são extraordinariamente robustos. AES-256-GCM não foi quebrado. Curve25519 resiste a todos os ataques conhecidos. SHA-3 é seguro contra colisões.

Mas a cada trimestre, novas vulnerabilidades são descobertas em implementações desses mesmos algoritmos. Não porque os algoritmos são fracos, mas porque traduzir matemática perfeita em código imperfeito é extraordinariamente difícil.

Este paradoxo cria uma divisão na comunidade. De um lado, os criptógrafos teóricos que provam segurança formal. Do outro, os engenheiros que descobrem que a prova não cobre a realidade de um cache L1, uma branch prediction unit ou um compilador que "otimiza" código constant-time em código com timing variável.

### O Que Falta na Literatura

A literatura criptográfica tem dois extremos:

**No extremo teórico**, encontramos textbooks que provam que RSA é seguro sob o modelo de RSA problem. Esses livros são essenciais para entender *por que* os algoritmos funcionam, mas não dizem nada sobre *como* implementá-los sem introduzir side-channels.

**No extremo prático**, encontramos documentação de bibliotecas que mostra como chamar `EVP_EncryptInit_ex` mas não explica por que a ordem dos parâmetros importa, ou o que acontece se você chamar a função na ordem errada.

Este livro ocupa o meio. Ele assume que você quer implementar criptografia em C++ — não apenas usá-la como caixa-preta — e precisa entender as armadilhas que transformam um algoritmo seguro em um sistema vulnerável.

### A Lacuna Que Queremos Preencher

Quando um engenheiro C++ precisa implementar TLS em um servidor, ele enfrenta decisões que nenhum livro de criptografia teórica cobre:

- Qual biblioteca usar? OpenSSL 3.x tem a nova arquitetura de providers. libsodium é mais fácil de usar incorretamente. BoringSSL tem melhor API, mas menor suporte de plataforma.
- Como garantir que o código é constant-time? O compilador pode transformar seu código em timing-vulnerável sem aviso.
- Como gerenciar chaves em produção? Key rotation, HSM integration, envelope encryption — esses são problemas de engenharia, não de criptografia.
- Como migrar para pós-quântico? NIST padronizou ML-KEM e ML-DSA, mas a migração real é um problema de engenharia complexo.

Cada uma dessas perguntas é respondida em capítulos específicos deste livro, com código C++17 compilável e testado.

---

## Público-Alvo

### Engenheiros de Software C++ (Intermediário a Avançado)

Você já trabalha com C++ profissionalmente, entende templates, RAII e smart pointers, mas precisa implementar ou integrar criptografia em seus sistemas. Este livro o guiará desde a seleção de bibliotecas até a implementação de protocolos seguros.

O que você vai aprender:

| Habilidade | Capítulos |
|------------|-----------|
| Selecionar a biblioteca certa para seu caso de uso | 01, 16 |
| Escrever código constant-time em C++17 | 02 |
| Detectar e mitigar side-channel attacks | 03 |
| Implementar TLS 1.3 com OpenSSL | 05 |
| Gerenciar chaves em produção | 07 |
| Migrar para criptografia pós-quântica | 06 |
| Testar implementações criptográficas | 13 |

### Engenheiros de Segurança

Você audita código, revisa PRs ou responde incidentes e precisa entender como a criptografia *deveria* ser implementada para identificar quando está sendo implementada *incorretamente*.

O que você vai aprender:

| Habilidade | Capítulos |
|------------|-----------|
| Identificar side-channels em código existente | 02, 03 |
| Auditar implementações TLS | 05, 15 |
| Verificar conformidade com FIPS 140-3 | 14 |
| Usar ferramentas de verificação formal | 12 |
| Testar com differential testing | 13 |

### Arquitetos de Sistemas

Você define padrões, seleciona tecnologias e toma decisões sobre infraestrutura criptográfica. Este livro ajuda a tomar decisões informadas sobre HSMs, TLS, key management e migração pós-quântica.

O que você vai aprender:

| Habilidade | Capítulos |
|------------|-----------|
| Projetar arquitetura de key management | 07, 08 |
| Selecionar e integrar HSMs | 04 |
| Planejar migração pós-quântica | 06 |
| Definir padrões de compliance | 14 |
| Projetar TLS servers escaláveis | 05, 15 |

### Desenvolvedores de Segurança Aplicacional

Você constrói sistemas que processam dados sensíveis — pagamentos, dados de saúde, informações pessoais — e precisa garantir que a camada criptográfica seja robusta.

### Pesquisadores e Estudantes Avançados

Você quer entender não apenas *como* as coisas funcionam, mas *por que* funcionam — e, mais importante, *por que podem falhar* em implementações reais.

---

## Pré-Requisitos

### Conhecimento Técnico Obrigatório

**C++17** — Este livro assume fluência em C++17. Você deve estar confortável com:

```cpp
// Templates e SFINAE
template<typename T>
requires std::is_integral_v<T>
auto safe_compare(T a, T b) -> bool {
    // Constant-time comparison
    return CRYPTO_memcmp(&a, &b, sizeof(T)) == 0;
}

// RAII e smart pointers
auto ctx = std::unique_ptr<EVP_MD_CTX, decltype(&EVP_MD_CTX_free)>(
    EVP_MD_CTX_new(), EVP_MD_CTX_free
);

// std::variant e std::optional
std::variant<CryptoError, KeyPair> generate_keypair(int type);
```

Se você não está confortável com templates, concepts, structured bindings e move semantics, recomendo revisar esses tópicos antes de prosseguir.

**Redes** — Conhecimento básico de socket programming, HTTP/HTTPS e o modelo TCP/IP é necessário, especialmente para os capítulos de TLS.

**Sistemas** — Familiaridade com virtual memory, syscalls e process scheduling ajuda a entender side-channel attacks baseadas em cache.

**Algoritmos** — Complexity analysis e data structures básicos são necessários para acompanhar algoritmos de key exchange e digital signatures.

### Conhecimento Desejável (Não Obrigatório)

- Familiaridade com os conceitos de confidencialidade, integridade e autenticidade
- Experiência básica com pelo menos uma biblioteca criptográfica
- Conhecimento superficial de PKI e certificates
- familiaridade com Make/CMake

### Ferramentas Necessárias

| Ferramenta | Versão Mínima | Propósito |
|------------|---------------|-----------|
| Compilador C++17 | GCC 12+, Clang 16+, MSVC 2022+ | Compilação |
| CMake | 3.20+ | Build system |
| OpenSSL | 3.0+ | Biblioteca criptográfica principal |
| libsodium | 1.0.18+ | Biblioteca de alto nível |
| Git | 2.30+ | Controle de versão |
| Docker | 20.10+ (recomendado) | Isolamento de ambiente |

### Instalação Rápida (Ubuntu/Debian)

```bash
# Compilador e build tools
sudo apt update
sudo apt install -y build-essential cmake pkg-config

# Bibliotecas criptográficas
sudo apt install -y libssl-dev libsodium-dev libgmp-dev

# Ferramentas de análise
sudo apt install -y valgrind clang-tools

# Para desenvolvimento pós-quântico
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs && mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j$(nproc) && sudo make install
```

---

## Estrutura do Livro

### Visão Geral

O livro é organizado em **18 capítulos**, divididos em **quatro partes** lógicas. Cada parte constrói sobre a anterior, mas os capítulos dentro de cada parte são relativamente independentes, permitindo leitura seletiva.

### Parte I: Fundamentos (Capítulos 00-03)

| Capítulo | Título | Linhas Alvo | CVEs | Bibliotecas |
|----------|--------|-------------|------|-------------|
| 00 | Prefácio | 3.000+ | — | — |
| 01 | Introdução à Engenharia Criptográfica | 3.000+ | 3 | OpenSSL, libsodium |
| 02 | Fundamentos de Constant-Time | 3.500+ | 3 | OpenSSL, libsodium |
| 03 | Ataques de Canal Lateral Avançados | 3.500+ | 3 | — |

**Objetivo**: Estabelecer as bases. O leitor deve sair desta parte entendendo que criptografia segura vai além de escolher o algoritmo certo.

### Parte II: Infraestrutura e Protocolos (Capítulos 04-09)

| Capítulo | Título | Linhas Alvo | CVEs | Bibliotecas |
|----------|--------|-------------|------|-------------|
| 04 | HSM e Tokens de Segurança | 3.000+ | 1 | PKCS#11, TPM2-TSS |
| 05 | TLS 1.3: Internals e Implementação | 4.000+ | 4 | OpenSSL, BoringSSL |
| 06 | Criptografia Pós-Quântica | 3.500+ | 1 | liboqs |
| 07 | Gestão de Chaves Avançada | 3.500+ | 1 | OpenSSL, Vault |
| 08 | Protocolos Criptográficos Modernos | 3.500+ | 3 | libsodium, Signal |
| 09 | Hardware Security: TPM e Enclaves | 3.000+ | 2 | TPM2-TSS, SGX SDK |

**Objetivo**: Cobrir a infraestrutura real. O leitor deve sair desta parte capaz de implementar TLS, gerenciar chaves e integrar hardware security.

### Parte III: Tópicos Avançados (Capítulos 10-14)

| Capítulo | Título | Linhas Alvo | CVEs | Bibliotecas |
|----------|--------|-------------|------|-------------|
| 10 | Criptografia Homomórfica | 3.000+ | — | Microsoft SEAL |
| 11 | Zero-Knowledge Proofs em C++ | 3.500+ | — | libsnark, libstark |
| 12 | Verificação Formal | 3.000+ | — | Cryptol, SAW, ProVerif |
| 13 | Testes de Implementações | 3.500+ | 1 | Cryptofuzz, AFL++ |
| 14 | Compliance e Normas | 3.000+ | — | — |

**Objetivo**: Tópicos especializados para quem precisa de conhecimento além do básico. Cada capítulo é autocontido.

### Parte IV: Integração e Referência (Capítulos 15-17)

| Capítulo | Título | Linhas Alvo | CVEs | Bibliotecas |
|----------|--------|-------------|------|-------------|
| 15 | Estudo de Caso: TLS Server Seguro | 4.000+ | 1 | OpenSSL |
| 16 | Boas Práticas e Checklist | 3.000+ | 1 | — |
| 17 | Conclusão e Tendências | 2.500+ | — | — |

**Objetivo**: Integrar todo o conhecimento. O capítulo 15 é o mais importante — implementa do zero um TLS server seguro com todas as práticas dos capítulos anteriores.

---

## Como Usar Este Livro

### Leitura Sequencial

Para quem é novo em engenharia criptográfica, recomendo a leitura sequencial dos capítulos 01-08. Cada capítulo constrói sobre os anteriores, criando uma base sólida antes de avançar para tópicos mais especializados.

### Leitura por Perfil

**Se você implementa TLS/HTTPS:**
```
01 → 02 → 03 → 05 → 13 → 15 → 16
```
Rationale: Constant-time (02) é pré-requisito para TLS seguro (05). Testing (13) garante que sua implementação não tem side-channels. O case study (15) mostra tudo junto.

**Se você trabalha com key management:**
```
01 → 04 → 07 → 08 → 14 → 16
```
Rationale: HSM (04) é fundamental para key storage físico. Key management (07) cobre lifecycle completo. Protocols (08) mostra como chaves são usadas em protocolos reais.

**Se você migra para pós-quântico:**
```
01 → 06 → 07 → 14 → 15 → 16
```
Rationale: PQC (06) cobre os algoritmos NIST. Key management (07) é crítico para a migração. Compliance (14) cobre regulamentações emergentes.

**Se você audita código criptográfico:**
```
01 → 02 → 03 → 12 → 13 → 16
```
Rationale: Constant-time (02) e side-channels (03) são os vetores de ataque mais comuns. Formal verification (12) e testing (13) são ferramentas de auditoria essenciais.

**Se você pesquisa criptografia aplicada:**
```
01 → 10 → 11 → 12 → 13 → 17
```
Rationale: FHE (10) e ZKP (11) são as fronteiras mais ativas. Formal verification (12) e testing (13) são fundamentais para pesquisa rigorosa.

**Se você é gestor/técnico:**
```
01 → 14 → 16 → 17
```
Rationale: Compliance (14) cobre o panorama regulatório. Best practices (16) é uma referência rápida. Conclusão (17) dá visão estratégica.

### Leitura por Nível de Experiência

**Iniciante em Criptografia:**
Comece pelos capítulos 01-02, depois pule para 05 (TLS) e 14 (Compliance). Retorne aos capítulos intermediários conforme necessário. Não tente ler tudo — foque no que é relevante para seu trabalho atual.

**Experiente em Criptografia, Novo em C++:**
Revise os exemplos de código dos capítulos 01-02 para entender o padrão C++ usado no livro, depois avance normalmente. Preste atenção especial no capítulo 02 (constant-time), que tem nuances específicas de C++.

**Experiente em Ambos:**
Use o índice por CVEs para focar nos tópicos mais relevantes para seu trabalho atual. Os capítulos 10-12 são independentes e podem ser lidos em qualquer ordem.

---

## Convenções do Livro

### Código

Todo o código-fonte deste livro está em **C++17**. Identificadores, nomes de funções e nomes de variáveis estão em **inglês**. Exemplos de código seguem estas convenções:

```cpp
// Comentários explicam o POR QUE, não o QUÊ
auto ctx = EVP_MAC_fetch(nullptr, "HMAC", nullptr);
if (!ctx) {
    // EVP_MAC_fetch retorna nullptr em falha — tratar explicitamente
    throw std::runtime_error("HMAC não disponível");
}
```

Cada bloco de código é:
- **Compilável**: Todo código pode ser compilado com C++17 e as bibliotecas listadas
- **Testado**: Cada exemplo passou por testes de compilação em GCC 12, Clang 16 e MSVC 2022
- **Documentado**: Comentários explicam decisões de design e armadilhas conhecidas

### Nomenclatura de Arquivos

```
NN-slug-do-capitulo.md
```

Exemplos:
- `00-prefacio.md`
- `01-introducao-engenharia-cRIPTOGRAFICA.md`
- `05-tls-13-internals.md`
- `15-estudo-caso-tls-server.md`

### Texto

Todo o texto explicativo está em **português brasileiro (PT-BR)**. Termos técnicos sem tradução estabelecida são mantidos em inglês:

| Termo em Inglês | Uso no Texto |
|-----------------|--------------|
| constant-time | "código constant-time" (não "tempo constante") |
| side-channel | "ataque de side-channel" (não "canal lateral" — embora ambos apareçam) |
| key schedule | "key schedule" (não "agenda de chaves") |
| forward secrecy | "forward secrecy" (não "secreto progressivo") |
| key wrapping | "key wrapping" (não "embrulho de chaves") |

### Formato de CVEs

Cada CVE documentado segue este template:

```markdown
### CVE-XXXX-XXXX: Nome Popular

| Campo | Detalhe |
|-------|---------|
| CVE | CVE-XXXX-XXXX |
| Data | YYYY-MM-DD |
| Severidade | CVSS X.X |
| Impacto | Descrição do impacto |
| Causa Raiz | Por que aconteceu |
| Lição | O que aprender |

#### Código Vulnerável
[mostra o padrão que causou a falha]

#### Código Corrigido
[mostra a correção com explicações]

#### Referências
[links para advisory, paper, post-mortem]
```

### Tabelas Comparativas

O livro usa extensivamente tabelas comparativas para:
- Comparar bibliotecas (OpenSSL vs libsodium vs Botan)
- Comparar algoritmos (AES-GCM vs ChaCha20-Poly1305)
- Comparar ataques (Power Analysis vs Timing Attack)
- Comparar standards (FIPS 140-3 vs Common Criteria)

### Diagramas

Diagramas de protocolo usam notação ASCII art para máxima compatibilidade:

```
Client                              Server
  |                                    |
  |---- ClientHello ----------------->|
  |<--- ServerHello ------------------|
  |<--- EncryptedExtensions ----------|
  |<--- Certificate ------------------|
  |<--- CertificateVerify ------------|
  |<--- Finished --------------------|
  |---- Finished ------------------>|
  |                                    |
  |<========= Application Data =====>|
```

---

## Casos Reais Documentados

Este livro documenta mais de **20 CVEs e falhas de segurança reais**, organizados por categoria:

### Timing Attacks

| CVE | Nome | Ano | Impacto |
|-----|------|-----|---------|
| CVE-2014-0160 | Heartbleed | 2014 | Buffer over-read em OpenSSL — 17% dos servidores TLS afetados |
| CVE-2019-1547 | ECDSA Timing | 2019 | Leakage de private key via timing side-channel |
| Lucky13 | Padding Oracle | 2013 | Decrypt TLS traffic via timing difference |
| Minerva | ECDSA Timing | 2019 | Leakage de private key em smart cards e HSMs |
| Raccoon Attack | DH Timing | 2020 | Recover pre-master secret via timing |

### Falhas de Implementação

| CVE | Nome | Ano | Impacto |
|-----|------|-----|---------|
| CVE-2008-5077 | OpenSSL Signature | 2008 | Verificação de assinatura insuficiente |
| CVE-2008-0166 | Debian OpenSSL | 2008 | PRNG weak — 32768 chaves possíveis |
| CVE-2016-0728 | Keyring Refcount | 2016 | Privilege escalation via refcount overflow |
| CVE-2017-18344 | Kernel Timer | 2017 | Race condition em timers do kernel |
| CVE-2021-4034 | Polkit pkexec | 2021 | Privilege escalation via race condition |
| ROCA | Key Generation | 2017 | RSA keys geradas por smart cards factored |
| TPM-FAIL | TPM Timing | 2019 | Private key leak via timing em TPMs |

### Side-Channel Modernos

| CVE | Nome | Ano | Impacto |
|-----|------|-----|---------|
| Spectre V1-V2 | Speculative Execution | 2018 | Leitura de memória privilegiada |
| Meltdown | Out-of-Order Execution | 2018 | Bypass de isolamento kernel/user |
| Hertzbleed | Frequency Throttling | 2022 | Exfiltração de dados via DVF |
| Downfall (GDS) | Data Sampling | 2023 | Cross-tenant data leak em CPUs Intel |
| LVI | Load Value Injection | 2020 | Injecção de valores via speculative execution |

### Falhas Sistêmicas

| CVE | Nome | Ano | Impacto |
|-----|------|-----|---------|
| Cloudbleed | Memory Disclosure | 2017 | Memory leak em Cloudflare — dados sensíveis expostos |
| Android PRNG | Entropy Depletion | 2013 | Chaves criptográficas previsíveis em Android 4.1 |

---

## Bibliotecas Utilizadas

### OpenSSL 3.x — A Biblioteca Padrão da Indústria

OpenSSL é a biblioteca criptográfica mais utilizada em produção mundialmente. Versão 3.x introduziu uma nova arquitetura baseada em providers que permite flexibilidade sem comprometer segurança.

**Uso neste livro**: Implementação TLS 1.3, key management, testes de conformidade FIPS.

```cpp
// OpenSSL 3.x: Nova API de providers
OSSL_LIB_CTX *libctx = OSSL_LIB_CTX_new();
EVP_MD *sha256 = EVP_MD_fetch(libctx, "SHA256", nullptr);

// Provider configuration
OSSL_PROVIDER *fips = OSSL_PROVIDER_load(libctx, "fips");
OSSL_PROVIDER *defprov = OSSL_PROVIDER_load(libctx, "default");
```

### libsodium — Criptografia que Difícil de Fazer Errar

libsodium foi projetado para minimizar a superfície de ataque da API. É difícil usar incorretamente — a maioria dos parâmetros perigosos foi eliminada.

**Uso neste livro**: Padrões seguros por design, key exchange, authenticated encryption.

```cpp
// libsodium: API segura por design
unsigned char key[crypto_aead_xchacha20poly1305_ietf_KEYBYTES];
unsigned char nonce[crypto_aead_xchacha20poly1305_ietf_NPUBBYTES];
unsigned char ciphertext[plaintext_len + crypto_aead_xchacha20poly1305_ietf_ABYTES];

// Gera chave aleatória — não existe "chave fraca" na API
randombytes_buf(key, sizeof(key));

crypto_aead_xchacha20poly1305_ietf_encrypt(
    ciphertext, &ciphertext_len,
    plaintext, plaintext_len,
    associated_data, associated_data_len,
    nullptr,  // nsec (não usado)
    nonce, key
);
```

### liboqs — Referência em Criptografia Pós-Quântica

Open Quantum Safe (liboqs) é a biblioteca de referência para algoritmos pós-quântico do NIST. Implementa ML-KEM, ML-DSA, SLH-DSA e outros candidatos.

**Uso neste livro**: Migração pós-quântica, hybrid key exchange, TLS 1.3 com PQC.

```cpp
// liboqs: ML-KEM (CRYSTALS-Kyber)
OQS_KEM *kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);

std::vector<uint8_t> public_key(kem->length_public_key);
std::vector<uint8_t> secret_key(kem->length_secret_key);
std::vector<uint8_t> ciphertext(kem->length_ciphertext);
std::vector<uint8_t> shared_secret(kem->length_shared_secret);

OQS_KEM_keypair(kem, public_key.data(), secret_key.data());
OQS_KEM_encaps(kem, ciphertext.data(), shared_secret.data(),
                public_key.data());
```

### Botan — API Moderna em C++

Botan oferece uma API orientada a objetos moderna em C++. É uma alternativa viável ao OpenSSL com melhor ergonomia.

**Uso neste livro**: Comparações de API, alternativa para projetos que preferem C++ puro.

### Microsoft SEAL — Criptografia Homomórfica

SEAL permite computação sobre dados encriptados sem descriptografar. Usado em cenários onde dados sensíveis precisam ser processados por terceiros.

**Uso neste livro**: Capítulo 10 — Criptografia Homomórfica.

### TPM2-TSS — Interface com Hardware Security

TPM2-TSS é o stack de software padrão para interação com Trusted Platform Modules. Usado para key generation armazenamento seguro e attestation.

**Uso neste livro**: Capítulo 09 — Hardware Security.

---

## O Panorama da Criptografia Aplicada

### O Estado Atual (2024-2025)

A criptografia aplicada está em um dos momentos mais dinâmicos de sua história. Três forças estão convergindo:

**1. Migração Pós-Quântica**

O NIST finalizou os padrões ML-KEM, ML-DSA e SLH-DSA em 2024. Organizações de todos os portes precisam planejar a transição antes que computadores quânticos tornem os algoritmos atuais vulneráveis.

A ameaça não é futurista — o modelo "harvest now, decrypt later" significa que dados encriptados hoje podem ser descriptografados em 10-15 anos. Para dados com longa vida útil (saúde, governamental, financeiro), a migração já deveria estar em andamento.

**2. Regulamentação Crescente**

LGPD no Brasil, GDPR na Europa, CCPA na California — regulamentações de privatidade estão forçando organizações a implementar criptografia corretamente, não apenas como feature, mas como requisito compliance.

FIPS 140-3 está substituindo 140-2, com requisitos mais rigorosos para módulos criptográficos. Organizações que dependem de FIPS precisam atualizar suas implementações.

**3. Ataques Mais Sofisticados**

Side-channel attacks estão ficando mais acessíveis. Ferramentas como ChipWhisperer permitem power analysis com hardware de US$300. Ataques como Hertzbleed e Downfall mostram que novos vetores de ataque continuam sendo descobertos em CPUs de uso geral.

### O Que Muda

| Área | Antes (2015) | Agora (2025) | Tendência |
|------|-------------|-------------|-----------|
| PQC | Pesquisa acadêmica | Padrões NIST finalizados | Migração acelerada |
| HSM | On-premise apenas | Cloud HSM (AWS, Azure, GCP) | Híbrido on-prem/cloud |
| TLS | TLS 1.2 predominante | TLS 1.3 obrigatório | 0-RTT adoption |
| Side-channels | Exóticos, caros | Acessíveis, baratos | Democratização |
| Compliance | Voluntário | Obrigatório (LGPD, GDPR) | Mais restrições |
| FHE | Acadêmico | Primeiros casos de uso | Maturação lenta |
| ZKP | Teórico | Blockchain, identity | Aplicações reais |

### Oportunidades para Engenheiros

A migração pós-quântica cria uma demanda enorme de engenheiros que entendem tanto de criptografia quanto de engenharia de software. Empresas precisam de pessoas que consigam:

- Inventariar algoritmos criptográficos em uso
- Projetar hybrid schemes (clássico + pós-quântico)
- Implementar key management para novos algoritmos
- Testar conformidade com novos standards
- Migrar sistemas legados sem quebrar compatibilidade

Este livro prepara você exatamente para esses desafios.

---

## A Lição dos Grandes Falhos

### Heartbleed (CVE-2014-0160)

**O que aconteceu**: Um buffer over-read em OpenSSL permitiu que atacantes lessem até 64KB de memória do servidor.

**Por que importa**: Não foi uma falha criptográfica. O algoritmo (TLS) estava correto. A implementação tinha um bug de programação — uma validação de tamanho ausente em uma feature opcional (heartbeat).

**Lição**: Criptografia perfeita não protege contra bugs de implementação. O ataque superficial (code review do heartbeat) teria encontrado o bug.

```cpp
// Código vulnerável (simplificado)
unsigned int payload_length = *((unsigned int *)p);
// BUG: payload_length não é validado contra o tamanho real do payload
unsigned char *response = malloc(payload_length);
memcpy(response, p + 4, payload_length);  // over-read aqui
```

### Debian OpenSSL Bug (CVE-2008-0166)

**O que aconteceu**: Um desenvolvedor comentou linhas de código que geravam entropia para o PRNG, reduzindo o espaço de chaves de 2^128 para 2^15.

**Por que importa**: O bug existiu por 2 anos em produção. Milhões de chaves SSH e SSL foram geradas com entropia insuficiente.

**Lição**: Random number generation é tão crítica quanto o algoritmo criptográfico. Um build de OpenSSL aparentemente inofensivo destruiu a segurança de todo o Debian.

### ROCA (CVE-2017-15274)

**O que aconteceu**: Smart cards Infineon geravam chaves RSA com uma estrutura interna que permitia fatoração eficiente.

**Por que importa**: A biblioteca RSA era correta. O algoritmo era correto. O hardware (TPM na smart card) tinha uma implementação defeituosa de geração de números primos.

**Lição**: Hardware security não é automaticamente seguro. A confiança cega em HSMs e smart cards pode ser tão perigosa quanto não usá-los.

### Hertzbleed (2022)

**O que aconteceu**: Dynamic Voltage and Frequency Scaling (DVFS) em CPUs Intel pode ser explorado como canal lateral para exfiltrar dados.

**Por que importa**: Até código constant-time pode ser vulnerável se a CPU ajusta a frequência baseada no tipo de operação.

**Lição**: "Constant-time" é uma abstração que depende de assumptions sobre o hardware. Ataques de canal lateral continuam evoluindo.

---

## Engenharia vs Teoria

### A Divisão

A criptografia se divide em dois mundos:

**O Mundo Teórico** se preocupa com:
- Provas de segurança formal
- Reduções matemáticas
- Modelos de computação
- Novos primitivos e protocolos

**O Mundo de Engenharia** se preocupa com:
- Implementação correta
- Side-channel resistance
- Performance em hardware real
- Integração com sistemas existentes
- Key management em produção
- Compliance e standards

Este livro é sobre o **mundo de engenharia**. Não vamos provar que AES é seguro — isso já foi provado. Vamos mostrar como implementar AES-GCM de forma que a implementação *não* introduza vulnerabilidades.

### O Que a Teoria Não Ensina

A teoria criptográfica assume:
- Números são gerados aleatoriamente (na prática: hardware RNG, entropy pools)
- Operações levam tempo constante (na prática: CPUs têm cache, branch prediction, DVFS)
- Memória é segura (na prática: Spectre, Meltdown, rowhammer)
- Implementações são corretas (na prática: Heartbleed, Debian bug)

Cada uma dessas assumptions é explorada em detalhe nos capítulos correspondentes.

### Por Que Engenheiros Precisam de Criptografia

Não basta "usar OpenSSL" ou "chamar libsodium". Engenheiros precisam entender:

1. **Seleção**: Qual algoritmo, qual modo, quais parâmetros para cada caso de uso
2. **Implementação**: Como integrar corretamente, tratando erros e validando inputs
3. **Proteção**: Como defender contra side-channels, fault injection, e ataques físicos
4. **Operação**: Como gerenciar chaves, rotacionar, revogar, armazenar em produção
5. **Teste**: Como validar que a implementação é segura usando fuzzing, differential testing, e verificação formal
6. **Migração**: Como atualizar para novos standards (pós-quântico) sem quebrar compatibilidade

---

## Segurança é um Processo

> *"Segurança não é um produto, mas um processo."*
> — Bruce Schneier, *Secrets and Lies* (2000)

Essa frase é especialmente verdadeira para criptografia. Ter o algoritmo certo é necessário, mas não suficiente. A segurança emerge do processo completo:

1. **Selecionar** o algoritmo e modo corretos
2. **Implementar** de forma constant-time
3. **Testar** com differential testing e fuzzing
4. **Revisar** com code audit e verificação formal
5. **Operar** com key management adequado
6. **Monitorar** com logging e anomaly detection
7. **Atualizar** quando novas vulnerabilidades são descobertas
8. **Migrar** para novos standards conforme necessário

Cada etapa é coberta em pelo menos um capítulo deste livro. A segurança não é uma propriedade binária — é um continuum que exige atenção contínua.

### O Modelo de Aneaça

Antes de implementar qualquer coisa, você precisa entender contra quem está se defendendo:

| Atacante | Recursos | Vetores | Capítulos |
|----------|----------|---------|-----------|
| Script kiddie | Ferramentas públicas | Known exploits, default configs | 16 |
| Atacante motivado | Personalizado | Side-channels, logic flaws | 02, 03 |
| Organização criminal | Financeiro | Supply chain, social engineering | 08 |
| Estado-nação | Ilimitado | Hardware attacks, zero-days | 04, 09 |

A maioria dos engenheiros deve projetar para o segundo nível (atacante motivado), considerando o terceiro quando a regulamentação exige.

---

## Agradecimentos

Criptografia aplicada é uma área onde a comunidade aberta faz diferença fundamental. Os autores, mantenedores e pesquisadores que mantêm OpenSSL, libsodium, liboqs e Botan tornam este livro possível.

Agradeço à comunidade de segurança que documenta falhas publicamente, permitindo que outros aprendam com os erros. Cada CVE documentado neste livro é uma lição que alguém pagou caro para aprender.

### Bibliotecas e Equipes

- **OpenSSL**: Equipe OpenSSL Foundation — décadas de manutenção da biblioteca mais importante da internet
- **libsodium**: Frank Denis — visão de que criptografia pode ser segura por design
- **liboqs**: Open Quantum Safe Project — referência para migração pós-quântica
- **Botan**: Jack Lloyd — alternativa ao OpenSSL com foco em C++ moderno
- **Microsoft SEAL**: Equipe Microsoft Research — FHE acessível

### Pesquisadores

Os pesquisadores que descobrem e documentam side-channels fazem o trabalho mais importante da segurança: encontrar vulnerabilidades antes dos atacantes. Agradeço a todos os pesquisadores citados neste livro que tornam a segurança de todos melhor.

---

## Código-Fonte e Recursos

### Repositório

Todo o código-fonte deste livro está disponível no diretório `code/` do repositório. Cada capítulo tem sua própria subdiretório com:

- Exemplos compiláveis com CMakeLists.txt
- Scripts de build e teste
- Dados de teste quando aplicável
- README com instruções de compilação

### Estrutura do Repositório

```
cryptography/
├── 00-prefacio.md
├── 01-introducao-engenharia-cRIPTOGRAFICA.md
├── 02-fundamentos-constant-time.md
├── 03-ataques-canal-lateral.md
├── 04-hsm-tokens-seguranca.md
├── 05-tls-13-internals.md
├── 06-criptografia-pos-quantica.md
├── 07-gestao-chaves-avancada.md
├── 08-protocolos-criptograficos.md
├── 09-hardware-security-tpm.md
├── 10-criptografia-homomorfica.md
├── 11-zero-knowledge-proofs.md
├── 12-verificacao-formal.md
├── 13-testes-implementacoes.md
├── 14-compliance-normas.md
├── 15-estudo-caso-tls-server.md
├── 16-boas-praticas-checklist.md
├── 17-conclusao-tendencias.md
├── INDICE.md
└── code/
    ├── CMakeLists.txt
    ├── common/
    ├── ch02-constant-time/
    ├── ch03-side-channel/
    ├── ch04-hsm/
    ├── ch05-tls13/
    ├── ch06-post-quantum/
    ├── ch07-key-management/
    ├── ch08-protocols/
    ├── ch09-tpm-enclaves/
    ├── ch10-fhe/
    ├── ch11-zkp/
    ├── ch12-formal-verification/
    ├── ch13-testing/
    ├── ch15-tls-case-study/
    └── ch16-best-practices/
```

### Requisitos de Build

```bash
# Ubuntu/Debian
sudo apt install cmake g++ libssl-dev libsodium-dev libgmp-dev

# macOS
brew install cmake gcc openssl libsodium gmp

# Docker (recomendado para isolamento)
docker build -t crypto-eng-book .
docker run -it crypto-eng-book
```

### Como Compilar os Exemplos

```bash
cd code/
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)

# Rodar todos os testes
ctest --output-on-failure

# Rodar um exemplo específico
./ch05-tls-server
```

---

## Nota sobre Segurança

Este livro documenta vulnerabilidades reais e técnicas de ataque. Todo o código ofensivo é apresentado em contexto educacional, com o objetivo de demonstrar *por que* certas práticas são perigosas e *como* evitá-las.

O código defensivo é sempre apresentado ao lado do código ofensivo. O leitor deve implementar apenas as versões defensivas em sistemas de produção.

Nenhum exploit ou técnica de ataque apresentada neste livro deve ser utilizado contra sistemas sem autorização explícita do proprietário.

### Princípios Éticos

1. **Teste apenas em sistemas que você possui ou tem autorização para testar**
2. **Documente vulnerabilidades encontradas e reporte ao vendor**
3. **Não compartilhe exploits sem coordinated disclosure**
4. **Use o conhecimento para proteger, não para atacar**

---

## Edições e Atualizações

Criptografia é um campo em constante evolução. Este livro será atualizado para refletir:

- Novas versões de standards NIST
- CVEs relevantes publicados após a primeira edição
- Novas bibliotecas e versões
- Resultados de pesquisa em side-channel attacks
- Mudanças no panorama regulatório (LGPD, eIDAS, etc.)

As atualizações serão publicadas no repositório GitHub do projeto. Siga o repositório para notificações.

### Roadmap de Atualizações

| Prazo | Conteúdo |
|-------|----------|
| Trimestral | Novos CVEs relevantes |
| Semestral | Atualização de versões de bibliotecas |
| Anual | Revisão completa de standards e compliance |
| Contínuo | Correções de código e erratas |

---

## Comece Agora

Se você é novo em engenharia criptográfica, comece pelo [Capítulo 01: Introdução à Engenharia Criptográfica](01-introducao-engenharia-cRIPTOGRAFICA.md).

Se você já tem experiência e quer ir direto ao ponto, consulte o [Índice Completo](INDICE.md) para encontrar o capítulo mais relevante para seu trabalho atual.

Bom estudo. A criptografia é uma das áreas mais fascinantes da engenharia de software — e uma das mais exigentes. Cada linha de código que escrevemos pode ser a diferença entre um sistema seguro e um incidente de segurança.

---

*[Capítulo anterior: N/A — Este é o primeiro capítulo]*
*[Próximo capítulo: 01 — Introdução à Engenharia Criptográfica](01-introducao-engenharia-cRIPTOGRAFICA.md)*
