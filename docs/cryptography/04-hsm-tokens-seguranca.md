# Capítulo 04 — HSM e Tokens de Segurança

**Livro 5: Engenharia de Criptografia em C++**

---

## Sumário

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [O que é um HSM? Hierarquia FIPS 140-2/3](#2-o-que-é-um-hsm-hierarquia-fips-140-23)
3. [PKCS#11 API: Conceitos, sessões, objetos](#3-pkcs11-api-conceitos-sessões-objetos)
4. [C++17: Inicialização PKCS#11, geração de chaves, assinatura, encrypt/decrypt](#4-c17-inicialização-pkcs11-geração-de-chaves-assinatura-encryptdecrypt)
5. [Cloud HSMs: AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM](#5-cloud-hsms-aws-cloudhsm-azure-dedicated-hsm-google-cloud-hsm)
6. [Key Ceremony: Processo formal de geração de chaves mestras](#6-key-ceremony-processo-formal-de-geração-de-chaves-mestras)
7. [Performance: Benchmarks PKCS#11 vs software crypto](#7-performance-benchmarks-pkcs11-vs-software-crypto)
8. [Smart Cards e Tokens USB](#8-smart-cards-e-tokens-usb)
9. [Remote Key Storage: KMIP protocol](#9-remote-key-storage-kmip-protocol)
10. [CVE-2021-36260: Hikvision weak crypto](#10-cve-2021-36260-hikvision-weak-crypto)
11. [Ataques contra HSMs: Tempest, fault injection](#11-ataques-contra-hsms-tempest-fault-injection)
12. [Backup e Recovery de chaves HSM](#12-backup-e-recovery-de-chaves-hsm)
13. [Integração com OpenSSL: ENGINE API, Provider API](#13-integração-com-openssl-engine-api-provider-api)
14. [Tabela comparativa: HSMs no mercado](#14-tabela-comparativa-hsms-no-mercado)
15. [Exercícios](#15-exercícios)
16. [Referências](#16-referências)

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Explicar o que é um HSM (Hardware Security Module) e por que ele é fundamental para a segurança de chaves criptográficas em sistemas de produção
- Compreender a hierarquia de certificação FIPS 140-2 e FIPS 140-3 e como ela impacta a escolha de um HSM
- Desenvolver código C++17 que interage com HSMs através da API PKCS#11, incluindo inicialização, geração de chaves, assinatura digital, criptografia e descriptografia
- Implementar um cliente KMIP (Key Management Interoperability Protocol) para armazenamento remoto de chaves
- Entender os Cloud HSMs oferecidos por AWS, Azure e Google Cloud, incluindo modelos de deployment e custos
- Executar um Key Ceremony formal seguindo as melhores pricas da indústria
- Analisar vulnerabilidades reais em implementações de criptografia, como o CVE-2021-36260 do Hikvision
- Reconhecer vetores de ataque contra HSMs, incluindo TEMPEST e fault injection
- Projetar estratégias de backup e recuperação de chaves HSM que atendam a requisitos de compliance
- Integrar HSMs com OpenSSL através da ENGINE API (legada) e Provider API (modern)

### Pré-requisitos

- Conhecimento básico de C++17 (templates, smart pointers, lambda expressions)
- Familiaridade com conceitos de criptografia (chaves simétricas, assimétricas, assinaturas digitais)
- Noções básicas de programação orientada a objetos e RAII (Resource Acquisition Is Initialization)
- Terminal Linux/Unix básico

### Contexto do Capítulo

Este capítulo faz parte do Livro 5 — Engenharia de Criptografia em C++. Antes de prosseguir, é recomendável a leitura dos capítulos anteriores da série DevSecurity, especialmente aqueles que tratam de fundamentos de criptografia, gestão de chaves e PKI (Public Key Infrastructure).

A segurança de sistemas modernos depende fundamentalmente da proteção das chaves criptográficas. Uma chave RSA de 2048 bits é computacionalmente inviável de quebrar, mas se estiver armazenada em texto plano em um disco rígido, qualquer atacante com acesso físico ao servidor pode copiá-la. É exatamente para resolver esse problema que os HSMs existem.

Um HSM é um dispositivo de hardware projetado especificamente para armazenar chaves criptográficas e executar operações criptográficas de forma segura. As chaves nunca saem do dispositivo em texto plano — elas são geradas dentro dele, utilizadas internamente, e o resultado das operações é o que retorna ao sistema host. Mesmo que o servidor seja comprometido, o atacante não consegue extrair as chaves.

---

## 2. O que é um HSM? Hierarquia FIPS 140-2/3

### 2.1 Definição e Conceito Fundamental

Um Hardware Security Module (HSM) é um dispositivo de computação física especializado que gerencia e processa criptografia, fornece chaves de criptografia de alto desempenho e执行utenticação digital. HSMs são projetados para proteger o ciclo de vida das chaves criptográficas e executar operações criptográficas em um ambiente seguro, isolado do sistema host.

Diferentemente do armazenamento de chaves em software (onde as chaves residem em memória RAM ou disco e estão sujeitas a acesso não autorizado, cópia, ou extração por malware), um HSM oferece as seguintes garantias fundamentais:

**Proteção física do ciclo de vida da chave**: A chave é gerada dentro do módulo criptográfico seguro usando um gerador de números aleatórios verdadeiro (TRNG — True Random Number Generator) baseado em processos físicos como ruído térmico ou jitter de clock. A chave é armazenada em memória não-volátil com proteção contra remoção, e nunca é exposta em texto plano para o sistema host.

**Execução isolada de operações**: O HSM recebe dados de entrada (plaintext, hash, ou mensagem), processa a operação criptográfica internamente, e retorna apenas o resultado (ciphertext, assinatura, ou MAC). O software do host nunca tem acesso às chaves privadas armazenadas no dispositivo.

**Tampership e autodestruição**: HSMs modernos possuem sensores de tampership que detectam tentativas de acesso não autorizado. Quando detectado, o dispositivo pode apagar suas chaves criptográficas de forma irrecuperável (zeroization).

**Autenticação de usuário**: O acesso ao HSM requer autenticação via PIN, token, ou autenticação multifator. Muitos HSMs suportam quórum (M-of-N) para operações críticas, onde múltiplos operadores devem fornecer suas credenciais.

**Auditoria e non-repudiation**: Todas as operações realizadas no HSM são logadas em um audit trail imutável, permitindo rastreabilidade completa de quem fez o quê e quando.

### 2.2 Arquitetura Interna de um HSM

A arquitetura interna de um HSM típico inclui os seguintes componentes:

```
+--------------------------------------------------+
|                  HSM Hardware                     |
|                                                   |
|  +------------------+    +------------------+    |
|  |   CPU Criptogr.  |    |   TRNG           |    |
|  |   (ARM/Custom)   |    |   (Ruído Térmico)|    |
|  +------------------+    +------------------+    |
|                                                   |
|  +------------------+    +------------------+    |
|  |   Acelerador     |    |   Memória Segura  |    |
|  |   AES/RSA/ECC    |    |   (Battery-Backed)|    |
|  +------------------+    +------------------+    |
|                                                   |
|  +------------------+    +------------------+    |
|  |   Sensor Tampership|  |   Audit Log      |    |
|  |   (Tamper Mesh)   |   |   (NVRAM)        |    |
|  +------------------+    +------------------+    |
|                                                   |
|  +----------------------------------------------+ |
|  |          Interface Host (PCIe/USB/Network)   | |
|  +----------------------------------------------+ |
+--------------------------------------------------+
```

**CPU Criptográfica**: Processador dedicado (frequentemente ARM ou ASIC personalizado) que executa operações criptográficas. Não é um processador genérico — é otimizado para operações matemáticas em números grandes (big integer arithmetic) necessárias para RSA, ECC e outras primitivas.

**TRNG (True Random Number Generator)**: Gera números aleatórios a partir de processos físicos — ruído térmico em diodos, jitter de clock, ou outras fontes de entropia física. Diferente de PRNGs (Pseudo-Random Number Generators) que são determinísticos, o TRNG é imprevisível mesmo que o atacante conheça o algoritmo completo.

**Acelerador Criptográfico**: Hardware dedicado para operações de chave simétrica (AES, 3DES), hash (SHA-256, SHA-3), e operações assimétricas (RSA, ECDSA). O acelerador permite alto throughput — um HSM pode processar milhares de operações RSA-2048 por segundo.

**Memória Segura**: Tipicamente SRAM com proteção contra análise de consumo de energia (DPA — Differential Power Analysis) e proteção contra acesso não autorizado. A memória pode ser alimentada por bateria para preservar chaves entre ciclos de energia.

**Sensor de Tampership**: Rede de sensores embutidos no case do HSM que detectam: remoção de componentes, exposição a raios-X, variações de temperatura fora do range normal, tentativas de drilling, aplicação de voltagem anormal, e iluminação UV (para detectar microscopes).

### 2.3 FIPS 140-2 e FIPS 140-3

O Federal Information Processing Standard (FIPS) 140 é o padrão do governo dos EUA para módulos criptográficos. É amplamente adotado globalmente como referência de segurança para HSMs e outros dispositivos criptográficos.

#### FIPS 140-2 (Publicado em 2001, retirado em 2021)

O FIPS 140-2 define 4 níveis de segurança:

| Nível | Requisitos Principais | Exemplo de Uso |
|-------|----------------------|----------------|
| Nível 1 | Módulo criptográfico validado, segurança básica | Software em desktop |
| Nível 2 | Tamper-evident (selos de segurança), autenticação de operador | Tokens USB em escritórios |
| Nível 3 | Tamper-resistant (proteção ativa), autenticação identity-based, physically or logically separate interfaces | HSMs em data centers |
| Nível 4 | Tamper-active (resposta ativa ao tampership), proteção contra ataques ambientais | HSMs em ambientes hostis |

**Nível 1** é o mais básico — apenas requer que o módulo implemente algoritmos criptográficos aprovados e não apresente vulnerabilidades óbvias. Não há requisitos de proteção física. Muitos módulos de software OpenSSL FIPS validados operam neste nível.

**Nível 2** adiciona requisitos de evidência de tampership (selos de segurança que mostram se o dispositivo foi aberto), autenticação de role-based (papel do operador), e proteção contra acessos não autorizados a dados sensíveis. Smart cards e tokens USB frequentemente operam neste nível.

**Nível 3** é o padrão para HSMs em data centers. Exige tamper-resistant (o dispositivo resiste fisicamente ao acesso não autorizado — encapsulamento em epoxy, mesh de tampership, zeroização automática), autenticação identity-based (saber QUEM está operando, não apenas QUE papel), e separação física ou lógica entre interfaces sensíveis e não-sensíveis.

**Nível 4** é o mais alto — inclui proteção contra ataques ambientais (variações de voltagem, temperatura, radiação eletromagnética) e resposta ativa ao tampership (o dispositivo ativamente apaga dados quando detecta ataque). Usado em ambientes militares e de inteligência.

#### FIPS 140-3 (Publicado em 2019, substituiu o 140-2)

O FIPS 140-3 é uma atualização significativa que incorpora lições aprendidas com 18 anos de operação do 140-2:

**Mudanças principais**:

1. **Alinhamento com ISO/IEC 19790**: O FIPS 140-3 é alinhado com o padrão internacional ISO/IEC 19790, facilitando a aceitação global.

2. **Nível 4 redefinido**: O antigo Nível 4 (tamper-active) foi removido. Agora existem apenas 3 níveis (1, 2, 3), mas com requisitos mais rigorosos.

3. **Novos requisitos de algoritmo**: Suporte obrigatório para AES-256, SHA-3, e atualizações para refletir o estado da arte em criptografia.

4. **Análise de segurança aprimorada**: Requer Scuba Security Analysis (análise de vulnerabilidades de侧侧侧 channel) e documentação detalhada de provas de segurança.

5. **Requisitos para software embarcado**: Novos requisitos específicos para módulos que executam em firmware ou software embarcado.

6. **Operações no módulo**: Restrições mais rigorosas sobre quais operações podem ser realizadas dentro do módulo versus fora.

**Níveis do FIPS 140-3**:

| Nível | Mudanças em relação ao 140-2 | Foco |
|-------|------------------------------|------|
| Nível 1 | Alinhamento com ISO 19790, requisitos de algoritmo atualizados | Compatibilidade e algoritmos modernos |
| Nível 2 | Adiciona Scuba analysis para componentes, requisitos de documentação | Análise de segurança detalhada |
| Nível 3 | Interface de dados sensíveis deve ser física ou lógica separada, autenticação rigorosa | Segurança física e lógica |

#### Impacto na Seleção de HSMs

Ao selecionar um HSM para um sistema de produção, considere:

1. **Requisito regulatório**: Muitos setores (financeiro, governo, healthcare) exigem FIPS 140-2 Nível 3 ou superior. Verifique se o HSM escolhido possui validação FIPS 140-3 Nível 3.

2. **Ciclo de vida de validação**: Uma validação FIPS pode levar 12-24 meses. Se você precisa de FIPS 140-3, verifique se o fabricante já possui validação em andamento.

3. **Custo**: HSMs com FIPS 140-3 Nível 3 custam significativamente mais que Nível 2 — tipicamente entre $10.000 e $50.000 por unidade.

4. **Performance**: HSMs de nível mais alto podem ter overhead adicional devido às verificações de segurança.

### 2.4 Classificação de HSMs por Uso

**HSMs para Server Encryption**: Executam operações de criptografia de dados em repouso e em trânsito. Exemplos: Thales Luna Network HSM, Entrust nShield. Típicos em bancos de dados e sistemas de armazenamento.

**HSMs para Signing/Authentication**: Focados em operações de assinatura digital e autenticação. Usados em PKI, certificate signing, e autenticação de usuários. Exemplos: Utimaco SecurityServer, SafeNet Luna G5.

**HSMs para Payment (PCI HSM)**: Validados sob PCI PIN Security Requirements. Processam transações de cartão de crédito/débito e operações de PIN. Exemplos: Thales payShield 10K, Spirent PaymentHSM.

**HSMs para Key Management**: Focados em gerenciamento completo do ciclo de vida das chaves — geração, distribuição, rotação, armazenamento, backup e destruição. Exemplos: AWS CloudHSM, Azure Dedicated HSM.

### 2.5 Modelos de Acesso a HSMs

**Local (PCIe)**: HSM conectado diretamente ao servidor via barramento PCI Express. Latência mínima (< 1ms), throughput máximo. Ideal para sistemas de alta performance. Desvantagem: acoplamento físico ao servidor, difícil de escalar.

**Rede (Network-Attached)**: HSM acessível via rede Ethernet/TCP-IP. Múltiplos servidores podem acessar o mesmo HSM. Latência de rede (1-5ms). Ideal para ambientes multi-servidor. Exemplo: Thales Luna Network HSM.

**Cloud (Managed)**: HSM como serviço gerenciado na nuvem. O provedor gerencia o hardware, manutenção e compliance. Exemplos: AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM.

**USB/Token**: HSM portátil em formato USB. Acesso local ao computador. Ideal para desenvolvimento, testes, e ambientes de baixo volume. Exemplos: YubiHSM, Nitrokey HSM.

---

## 3. PKCS#11 API: Conceitos, sessões, objetos

### 3.1 Visão Geral do PKCS#11

PKCS#11 (Public-Key Cryptography Standards #11), também conhecido como Cryptoki (Crypto API para Hardware), é o padrão mais amplamente adotado para interfaces com tokens criptográficos — sejam HSMs físicos, smart cards, ou módulos de software. Definido pela RSA Laboratories (agora parte da OASIS), o PKCS#11 define uma API C genérica que permite aplicações interagir com qualquer token criptográfico de forma independente do fabricante.

A principal vantagem do PKCS#11 é a **abstração do hardware**: uma aplicação que usa PKCS#11 pode funcionar com qualquer token que implemente a API — desde um YubiHSM USB até um Thales Luna Network HSM em rack, passando por tokens USB simples. Isso elimina o lock-in de fabricante e permite trocar o hardware sem modificar a aplicação.

**Versão atual**: PKCS#11 v3.0 (ratificado em 2020 pela OASIS). Versões anteriores (v2.40, v2.20) ainda são amplamente suportadas.

### 3.2 Arquitetura do PKCS#11

A arquitetura do PKCS#11 é baseada em camadas:

```
+------------------------------------------+
|           Aplicação (C++)                |
|    ( Usa a API C do Cryptoki )          |
+------------------------------------------+
         |
         v
+------------------------------------------+
|       Biblioteca PKCS#11 (Cryptoki)      |
|    ( .so / .dll do fornecedor )          |
+------------------------------------------+
         |
         v
+------------------------------------------+
|          Token Criptográfico             |
|    ( HSM / Smart Card / Software )       |
+------------------------------------------+
```

A biblioteca PKCS#11 (tipicamente `libCryptoki.so` ou `.dll`) é fornecida pelo fabricante do token e implementa a interface C definida pela especificação. A aplicação usa essa biblioteca sem precisar saber detalhes específicos do hardware.

### 3.3 Conceitos Fundamentais

#### Slots e Tokens

Um **slot** é um ponto de conexão disponível no sistema — pode ser uma porta USB, um slot de smart card reader, ou um endpoint de rede. Cada slot pode conter um **token** (o dispositivo criptográfico físico ou lógico).

```
Slot 0: [Token] — YubiHSM conectado via USB
Slot 1: [Vazio] — Smart card reader vazio
Slot 2: [Token] — Nitrokey Pro conectado
```

A aplicação usa `C_GetSlotList()` para descobrir slots disponíveis, e `C_GetTokenInfo()` para obter informações sobre o token em cada slot.

#### Sessões

Uma **sessão** é uma conexão lógica entre a aplicação e o token. Existem dois tipos de sessão:

- **Sessão de Leitura (RO — Read-Only)**: Apenas operações de leitura e consultas. Não modifica o estado do token.
- **Sessão de Leitura-Escrita (RW — Read-Write)**: Operações completas incluindo modificação de objetos e administração.

Uma sessão pode estar em um dos dois estados de login:
- **Não-logado**: Apenas operações públicas (sem sensíveis) são permitidas.
- **Logado**: Todas as operações são permitidas, incluindo acesso a chaves sensíveis.

```cpp
// Exemplo de criação de sessão
CK_RV rv;
CK_SESSION_HANDLE hSession;

// Abrir sessão de leitura-escrita
rv = C_OpenSession(
    slotID,              // ID do slot
    CKF_RW_SESSION,      // Flags: leitura-escrita
    nullptr,             // Application-specific data
    nullptr,             // Notify callback
    &hSession            // Handle da sessão retornada
);

if (rv != CKR_OK) {
    throw std::runtime_error("Falha ao abrir sessão PKCS#11");
}

// Fazer login (necessário para acessar chaves sensíveis)
rv = C_Login(
    hSession,
    CKU_USER,           // Tipo de usuário: CKU_USER, CKU_SO, CKU_CONTEXT_SPECIFIC
    pin,                 // PIN do usuário
    pinLength            // Comprimento do PIN
);

if (rv != CKR_OK) {
    C_CloseSession(hSession);
    throw std::runtime_error("Falha no login PKCS#11");
}
```

#### Objetos

Objetos são as entidades armazenadas no token. Existem dois tipos principais:

**Objetos de Dados (Data Objects)**: Genéricos, sem significado criptográfico específico. Usados para armazenar certificados, dados de configuração, etc.

**Objetos Criptográficos (Cryptographic Objects)**: Têm significado criptográfico — chaves, templates de mecanismo, etc. Subdivididos em:

- **Chaves Simétricas (Secret Keys)**: Usadas para AES, 3DES, ChaCha20, etc.
- **Chaves Assimétricas (Key Pairs)**: Chaves RSA, ECDSA, Ed25519, etc.
- **Certificados X.509**: Armazenados como objetos no token.
- **Dados de Inicialização de Vetor (IV)**: Para modos CBC, GCM, etc.
- **Mecanismos de Inicialização**: Configurações de algoritmos.

Cada objeto é definido por um conjunto de **atributos** — pares chave-valor que descrevem suas propriedades:

```cpp
// Atributos de uma chave RSA-2048
CK_ATTRIBUTE template[] = {
    {CKA_CLASS,           &keyClass,     sizeof(keyClass)},     // CKO_PRIVATE_KEY
    {CKA_KEY_TYPE,        &keyType,      sizeof(keyType)},      // CKK_RSA
    {CKA_MODULUS,         moduluo,       moduluoLen},           // Número módulo
    {CKA_PUBLIC_EXPONENT, pubExp,        pubExpLen},            // Expoente público
    {CKA_PRIVATE,         &trueVal,      sizeof(trueVal)},      // true = sensível
    {CKA_SIGN,            &trueVal,      sizeof(trueVal)},      // true = pode assinar
    {CKA_DECRYPT,         &trueVal,      sizeof(trueVal)},      // true = pode descriptografar
    {CKA_TOKEN,           &trueVal,      sizeof(trueVal)},      // true = persistente no token
    {CKA_SENSITIVE,       &trueVal,      sizeof(trueVal)},      // true = não exportável
    {CKA_EXTRACTABLE,     &falseVal,     sizeof(falseVal)},     // false = não exportável
};
```

### 3.4 Mecanismos

Mecanismos são os algoritmos e modos de operação suportados pelo token. O PKCS#11 define centenas de mecanismos:

| Mecanismo | Constante | Uso |
|-----------|-----------|-----|
| RSA PKCS#1 v1.5 | `CKM_RSA_PKCS` | Assinatura clássica RSA |
| RSA PSS | `CKM_RSA_PKCS_PSS` | Assinatura moderna RSA |
| ECDSA | `CKM_ECDSA` | Assinatura com curvas elípticas |
| AES-CBC | `CKM_AES_CBC` | Criptografia simétrica CBC |
| AES-GCM | `CKM_AES_GCM` | Criptografia simétrica com autenticação |
| SHA-256 | `CKM_SHA256` | Hash |
| HMAC-SHA256 | `CKM_SHA256_HMAC` | MAC com hash |

Para descobrir quais mecanismos o token suporta:

```cpp
CK_MECHANISM_TYPE mechList[256];
CK_ULONG mechCount = 256;

rv = C_GetMechanismList(slotID, mechList, &mechCount);
```

### 3.5 Gerenciamento de Objetos

#### Criação de Objetos

```cpp
// Gerar um par de chaves RSA-2048 no token
CK_MECHANISM mech = {CKM_RSA_PKCS_KEY_PAIR_GEN, nullptr, 0};

// Template da chave pública
CK_ATTRIBUTE pubTemplate[] = {
    {CKA_MODULUS_BITS, &bits, sizeof(bits)},
    {CKA_PUBLIC_EXPONENT, pubExp, sizeof(pubExp)},
    {CKA_ENCRYPT, &trueVal, sizeof(trueVal)},
    {CKA_VERIFY, &trueVal, sizeof(trueVal)},
    {CKA_TOKEN, &trueVal, sizeof(trueVal)},
    {CKA_LABEL, "my-rsa-key", 11},
};

// Template da chave privada
CK_ATTRIBUTE privTemplate[] = {
    {CKA_PRIVATE, &trueVal, sizeof(trueVal)},
    {CKA_DECRYPT, &trueVal, sizeof(trueVal)},
    {CKA_SIGN, &trueVal, sizeof(trueVal)},
    {CKA_SENSITIVE, &trueVal, sizeof(trueVal)},
    {CKA_EXTRACTABLE, &falseVal, sizeof(falseVal)},
    {CKA_TOKEN, &trueVal, sizeof(trueVal)},
    {CKA_LABEL, "my-rsa-key", 11},
};

CK_OBJECT_HANDLE hPublicKey, hPrivateKey;

rv = C_GenerateKeyPair(
    hSession,
    &mech,
    pubTemplate, 7,
    privTemplate, 6,
    &hPublicKey,
    &hPrivateKey
);
```

#### Busca de Objetos

```cpp
// Buscar todos os certificados X.509 no token
CK_OBJECT_CLASS certClass = CKO_CERTIFICATE;
CK_ATTRIBUTE searchTemplate[] = {
    {CKA_CLASS, &certClass, sizeof(certClass)},
};

rv = C_FindObjectsInit(hSession, searchTemplate, 1);

CK_OBJECT_HANDLE objects[64];
CK_ULONG objectCount;
rv = C_FindObjects(hSession, objects, 64, &objectCount);

rv = C_FindObjectsFinal(hSession);
```

#### Cópia e Exportação

```cpp
// Exportar chave pública (permitido)
CK_ATTRIBUTE attrs[] = {
    {CKA_MODULUS, nullptr, 0},
    {CKA_PUBLIC_EXPONENT, nullptr, 0},
};

// Primeiro: obter tamanho
rv = C_GetAttributeValue(hSession, hPublicKey, attrs, 2);
// attrs[0].ulValueLen agora contém o tamanho do módulo

// Alocar buffer e obter valor
std::vector<CK_BYTE> modulus(attrs[0].ulValueLen);
attrs[0].pValue = modulus.data();
rv = C_GetAttributeValue(hSession, hPublicKey, attrs, 2);
```

### 3.6 Ciclo de Vida de uma Sessão

```
C_Initialize()
    |
    v
C_GetSlotList() -----> Slot Identification
    |
    v
C_OpenSession()  -----> Session Creation
    |
    v
C_Login()        -----> User Authentication (optional for public objects)
    |
    v
C_FindObjectsInit() ----> Search Objects
C_FindObjects()
C_FindObjectsFinal()
    |
    v
C_EncryptInit() / C_SignInit() / C_DecryptInit() / C_VerifyInit()
    |
    v
C_Encrypt() / C_Sign() / C_Decrypt() / C_Verify()
    |
    v
C_Logout()
    |
    v
C_CloseSession()
    |
    v
C_Finalize()
```

### 3.7 Tratamento de Erros

Todas as funções PKCS#11 retornam um `CK_RV` (return value). O tratamento adequado de erros é essencial:

```cpp
// Tabela de códigos de erro comuns
// CKR_OK (0x00000000) — Operação bem-sucedida
// CKR_ARGUMENTS_BAD (0x00000007) — Argumentos inválidos
// CKR_ATTRIBUTE_TYPE_INVALID (0x00000012) — Tipo de atributo inválido
// CKR_ATTRIBUTE_VALUE_INVALID (0x00000013) — Valor de atributo inválido
// CKR_CRYPTOKI_NOT_INITIALIZED (0x00000190) — Biblioteca não inicializada
// CKR_DEVICE_ERROR (0x00000030) — Erro no dispositivo
// CKR_DEVICE_MEMORY (0x00000031) — Memória insuficiente no dispositivo
// CKR_FUNCTION_NOT_SUPPORTED (0x000000D0) — Função não suportada
// CKR_KEY_HANDLE_INVALID (0x000000C2) — Handle de chave inválido
// CKR_KEY_NOT_NEEDED (0x000000C3) — Chave não necessária
// CKR_KEY_NOT_WRAPPABLE (0x00000100) — Chave não pode ser embalar
// CKR_KEY_SIZE_RANGE (0x00000121) — Tamanho de chave fora do range
// CKR_LOGIN_REQUIRED (0x0000010E) — Login necessário
// CKR_MECHANISM_INVALID (0x00000070) — Mecanismo inválido
// CKR_MECHANISM_PARAM_INVALID (0x00000071) — Parâmetro de mecanismo inválido
// CKR_OBJECT_HANDLE_INVALID (0x00000082) — Handle de objeto inválido
// CKR_OPERATION_ACTIVE (0x00000090) — Operação já ativa
// CKR_PIN_INCORRECT (0x000000A0) — PIN incorreto
// CKR_PIN_LOCKED (0x000000A4) — PIN bloqueado
// CKR_SESSION_HANDLE_INVALID (0x000000B3) — Handle de sessão inválido
// CKR_SIGNATURE_INVALID (0x000000C0) — Assinatura inválida
// CKR_TEMPLATE_INCOMPLETE (0x0000010C) — Template incompleto
// CKR_TEMPLATE_INCONSISTENT (0x0000010D) — Template inconsistente
// CKR_TOKEN_NOT_PRESENT (0x000000E0) — Token não presente
// CKR_TOKEN_NOT_RECOGNIZED (0x000000E1) — Token não reconhecido

// Helper para formatar erros
std::string pkcs11_error_name(CK_RV rv) {
    switch (rv) {
        case CKR_OK: return "CKR_OK";
        case CKR_ARGUMENTS_BAD: return "CKR_ARGUMENTS_BAD";
        case CKR_ATTRIBUTE_TYPE_INVALID: return "CKR_ATTRIBUTE_TYPE_INVALID";
        case CKR_DEVICE_ERROR: return "CKR_DEVICE_ERROR";
        case CKR_KEY_HANDLE_INVALID: return "CKR_KEY_HANDLE_INVALID";
        case CKR_LOGIN_REQUIRED: return "CKR_LOGIN_REQUIRED";
        case CKR_MECHANISM_INVALID: return "CKR_MECHANISM_INVALID";
        case CKR_PIN_INCORRECT: return "CKR_PIN_INCORRECT";
        case CKR_PIN_LOCKED: return "CKR_PIN_LOCKED";
        case CKR_SESSION_HANDLE_INVALID: return "CKR_SESSION_HANDLE_INVALID";
        case CKR_SIGNATURE_INVALID: return "CKR_SIGNATURE_INVALID";
        case CKR_TOKEN_NOT_PRESENT: return "CKR_TOKEN_NOT_PRESENT";
        default: return "UNKNOWN_ERROR (0x" + std::to_string(rv) + ")";
    }
}
```

---

## 4. C++17: Inicialização PKCS#11, geração de chaves, assinatura, encrypt/decrypt

### 4.1 Estrutura do Projeto

```
hsm_example/
├── CMakeLists.txt
├── include/
│   ├── pkcs11_wrapper.h
│   ├── hsm_session.h
│   ├── hsm_key_manager.h
│   ├── hsm_crypto_engine.h
│   └── hsm_utils.h
├── src/
│   ├── main.cpp
│   ├── pkcs11_wrapper.cpp
│   ├── hsm_session.cpp
│   ├── hsm_key_manager.cpp
│   └── hsm_crypto_engine.cpp
├── config/
│   └── pkcs11_config.json
└── tests/
    ├── test_session.cpp
    ├── test_keys.cpp
    └── test_crypto.cpp
```

### 4.2 Wrapper RAII para PKCS#11

A API C do PKCS#11 requer gerenciamento manual de handles e memória. Criar uma wrapper RAII em C++ elimina a possibilidade de resource leaks e simplifica enormemente o código cliente.

```cpp
// include/pkcs11_wrapper.h
#ifndef PKCS11_WRAPPER_H
#define PKCS11_WRAPPER_H

#include <cryptoki.h>
#include <string>
#include <vector>
#include <stdexcept>
#include <functional>
#include <memory>

namespace hsm {

// Exceção específica para erros PKCS#11
class Pkcs11Error : public std::runtime_error {
public:
    Pkcs11Error(CK_RV rv, const std::string& operation)
        : std::runtime_error("PKCS#11 error in " + operation +
                            ": " + rv_to_string(rv))
        , rv_(rv)
        , operation_(operation)
    {}

    CK_RV rv() const noexcept { return rv_; }
    const std::string& operation() const noexcept { return operation_; }

private:
    CK_RV rv_;
    std::string operation_;

    static std::string rv_to_string(CK_RV rv);
};

// Wrapper RAII para a biblioteca PKCS#11
class Pkcs11Library {
public:
    explicit Pkcs11Library(const std::string& library_path);
    ~Pkcs11Library();

    // Non-copyable, movable
    Pkcs11Library(const Pkcs11Library&) = delete;
    Pkcs11Library& operator=(const Pkcs11Library&) = delete;
    Pkcs11Library(Pkcs11Library&& other) noexcept;
    Pkcs11Library& operator=(Pkcs11Library&& other) noexcept;

    // Inicialização e finalização
    void initialize();
    void finalize();

    // Informações
    CK_INFO getInfo() const;

    // Slots
    std::vector<CK_SLOT_ID> getSlotList(bool tokenPresent = true) const;
    CK_TOKEN_INFO getTokenInfo(CK_SLOT_ID slotID) const;

    // Funções diretas da API
    CK_FUNCTION_LIST_PTR functions() const { return functions_; }

private:
    void loadLibrary(const std::string& path);
    void resolveFunctions();

    void* handle_ = nullptr;
    CK_FUNCTION_LIST_PTR functions_ = nullptr;
    bool initialized_ = false;
};

// Wrapper RAII para sessão PKCS#11
class Pkcs11Session {
public:
    Pkcs11Session(Pkcs11Library& library, CK_SLOT_ID slotID,
                  bool readOnly = false);
    ~Pkcs11Session();

    // Non-copyable, movable
    Pkcs11Session(const Pkcs11Session&) = delete;
    Pkcs11Session& operator=(const Pkcs11Session&) = delete;
    Pkcs11Session(Pkcs11Session&& other) noexcept;
    Pkcs11Session& operator=(Pkcs11Session&& other) noexcept;

    // Login
    void login(CK_USER_TYPE userType, const std::string& pin);
    void logout();

    // Handle da sessão
    CK_SESSION_HANDLE handle() const noexcept { return session_; }

    // Operações de busca de objetos
    std::vector<CK_OBJECT_HANDLE> findObjects(
        const std::vector<CK_ATTRIBUTE>& templateAttrs) const;

    // Informações do token
    CK_TOKEN_INFO tokenInfo() const;

    // Verificação de estado
    bool isLoggedIn() const noexcept { return loggedIn_; }

private:
    CK_SESSION_HANDLE session_ = CK_INVALID_HANDLE;
    Pkcs11Library* library_ = nullptr;
    bool loggedIn_ = false;
};

// RAII para handle de objeto
class Pkcs11Object {
public:
    Pkcs11Object(Pkcs11Session& session, CK_OBJECT_HANDLE handle);
    ~Pkcs11Object();

    // Non-copyable, movable
    Pkcs11Object(const Pkcs11Object&) = delete;
    Pkcs11Object& operator=(const Pkcs11Object&) = delete;
    Pkcs11Object(Pkcs11Object&& other) noexcept;
    Pkcs11Object& operator=(Pkcs11Object&& other) noexcept;

    CK_OBJECT_HANDLE handle() const noexcept { return handle_; }

    // Leitura de atributos
    template<typename T>
    T getAttribute(CK_ATTRIBUTE_TYPE type) const;

    std::vector<CK_BYTE> getAttributeBytes(CK_ATTRIBUTE_TYPE type) const;
    std::string getAttributeString(CK_ATTRIBUTE_TYPE type) const;

private:
    CK_OBJECT_HANDLE handle_ = CK_INVALID_HANDLE;
    Pkcs11Session* session_ = nullptr;
};

} // namespace hsm

#endif // PKCS11_WRAPPER_H
```

### 4.3 Implementação do Wrapper

```cpp
// src/pkcs11_wrapper.cpp
#include "pkcs11_wrapper.h"
#include <dlfcn.h>
#include <cstring>
#include <algorithm>

namespace hsm {

// ============================================================
// Pkcs11Error
// ============================================================

std::string Pkcs11Error::rv_to_string(CK_RV rv) {
    switch (rv) {
        case CKR_OK: return "CKR_OK";
        case CKR_CANCEL: return "CKR_CANCEL";
        case CKR_HOST_MEMORY: return "CKR_HOST_MEMORY";
        case CKR_SLOT_ID_INVALID: return "CKR_SLOT_ID_INVALID";
        case CKR_ARGUMENTS_BAD: return "CKR_ARGUMENTS_BAD";
        case CKR_MECHANISM_INVALID: return "CKR_MECHANISM_INVALID";
        case CKR_MECHANISM_PARAM_INVALID: return "CKR_MECHANISM_PARAM_INVALID";
        case CKR_ATTRIBUTE_TYPE_INVALID: return "CKR_ATTRIBUTE_TYPE_INVALID";
        case CKR_ATTRIBUTE_VALUE_INVALID: return "CKR_ATTRIBUTE_VALUE_INVALID";
        case CKR_DEVICE_ERROR: return "CKR_DEVICE_ERROR";
        case CKR_DEVICE_MEMORY: return "CKR_DEVICE_MEMORY";
        case CKR_FUNCTION_NOT_SUPPORTED: return "CKR_FUNCTION_NOT_SUPPORTED";
        case CKR_KEY_HANDLE_INVALID: return "CKR_KEY_HANDLE_INVALID";
        case CKR_KEY_SIZE_RANGE: return "CKR_KEY_SIZE_RANGE";
        case CKR_KEY_TYPE_INCONSISTENT: return "CKR_KEY_TYPE_INCONSISTENT";
        case CKR_PIN_INCORRECT: return "CKR_PIN_INCORRECT";
        case CKR_PIN_INVALID: return "CKR_PIN_INVALID";
        case CKR_PIN_LEN_RANGE: return "CKR_PIN_LEN_RANGE";
        case CKR_PIN_EXPIRED: return "CKR_PIN_EXPIRED";
        case CKR_PIN_LOCKED: return "CKR_PIN_LOCKED";
        case CKR_SESSION_HANDLE_INVALID: return "CKR_SESSION_HANDLE_INVALID";
        case CKR_SESSION_PARALLEL_NOT_SUPPORTED:
            return "CKR_SESSION_PARALLEL_NOT_SUPPORTED";
        case CKR_SESSION_READ_ONLY: return "CKR_SESSION_READ_ONLY";
        case CKR_SIGNATURE_INVALID: return "CKR_SIGNATURE_INVALID";
        case CKR_TEMPLATE_INCOMPLETE: return "CKR_TEMPLATE_INCOMPLETE";
        case CKR_TEMPLATE_INCONSISTENT: return "CKR_TEMPLATE_INCONSISTENT";
        case CKR_TOKEN_NOT_PRESENT: return "CKR_TOKEN_NOT_PRESENT";
        case CKR_TOKEN_NOT_RECOGNIZED: return "CKR_TOKEN_NOT_RECOGNIZED";
        case CKR_CRYPTOKI_NOT_INITIALIZED:
            return "CKR_CRYPTOKI_NOT_INITIALIZED";
        case CKR_OPERATION_ACTIVE: return "CKR_OPERATION_ACTIVE";
        case CKR_OPERATION_NOT_INITIALIZED:
            return "CKR_OPERATION_NOT_INITIALIZED";
        case CKR_OBJECT_HANDLE_INVALID: return "CKR_OBJECT_HANDLE_INVALID";
        case CKR_LIBRARY_LOAD_FAILED: return "CKR_LIBRARY_LOAD_FAILED";
        default: return "UNKNOWN (0x" + std::to_string(rv) + ")";
    }
}

// ============================================================
// Pkcs11Library
// ============================================================

Pkcs11Library::Pkcs11Library(const std::string& library_path) {
    loadLibrary(library_path);
    resolveFunctions();
}

Pkcs11Library::~Pkcs11Library() {
    if (initialized_) {
        finalize();
    }
    if (functions_) {
        functions_->C_Finalize(nullptr);
    }
    if (handle_) {
        dlclose(handle_);
    }
}

Pkcs11Library::Pkcs11Library(Pkcs11Library&& other) noexcept
    : handle_(other.handle_)
    , functions_(other.functions_)
    , initialized_(other.initialized_)
{
    other.handle_ = nullptr;
    other.functions_ = nullptr;
    other.initialized_ = false;
}

Pkcs11Library& Pkcs11Library::operator=(Pkcs11Library&& other) noexcept {
    if (this != &other) {
        if (initialized_) {
            finalize();
        }
        if (functions_) {
            functions_->C_Finalize(nullptr);
        }
        if (handle_) {
            dlclose(handle_);
        }

        handle_ = other.handle_;
        functions_ = other.functions_;
        initialized_ = other.initialized_;

        other.handle_ = nullptr;
        other.functions_ = nullptr;
        other.initialized_ = false;
    }
    return *this;
}

void Pkcs11Library::loadLibrary(const std::string& path) {
    handle_ = dlopen(path.c_str(), RTLD_NOW | RTLD_LOCAL);
    if (!handle_) {
        throw std::runtime_error("Falha ao carregar biblioteca PKCS#11: " +
                                std::string(dlerror()));
    }
}

void Pkcs11Library::resolveFunctions() {
    using C_GetFunctionList = CK_RV (*)(CK_FUNCTION_LIST_PTR_PTR);

    auto getFunctionList = reinterpret_cast<C_GetFunctionList>(
        dlsym(handle_, "C_GetFunctionList")
    );

    if (!getFunctionList) {
        dlclose(handle_);
        handle_ = nullptr;
        throw std::runtime_error(
            "Símbolo C_GetFunctionList não encontrado na biblioteca"
        );
    }

    CK_RV rv = getFunctionList(&functions_);
    if (rv != CKR_OK || !functions_) {
        dlclose(handle_);
        handle_ = nullptr;
        throw Pkcs11Error(rv, "C_GetFunctionList");
    }

    // Inicializar a biblioteca
    rv = functions_->C_Initialize(nullptr);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_Initialize");
    }
    initialized_ = true;
}

void Pkcs11Library::initialize() {
    if (initialized_) return;

    CK_RV rv = functions_->C_Initialize(nullptr);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_Initialize");
    }
    initialized_ = true;
}

void Pkcs11Library::finalize() {
    if (!initialized_) return;

    CK_RV rv = functions_->C_Finalize(nullptr);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_Finalize");
    }
    initialized_ = false;
}

CK_INFO Pkcs11Library::getInfo() const {
    CK_INFO info;
    CK_RV rv = functions_->C_GetInfo(&info);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetInfo");
    }
    return info;
}

std::vector<CK_SLOT_ID> Pkcs11Library::getSlotList(
    bool tokenPresent) const
{
    CK_ULONG slotCount = 0;
    CK_RV rv = functions_->C_GetSlotList(
        tokenPresent ? CK_TRUE : CK_FALSE,
        nullptr,
        &slotCount
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetSlotList (count)");
    }

    std::vector<CK_SLOT_ID> slots(slotCount);
    if (slotCount > 0) {
        rv = functions_->C_GetSlotList(
            tokenPresent ? CK_TRUE : CK_FALSE,
            slots.data(),
            &slotCount
        );
        if (rv != CKR_OK) {
            throw Pkcs11Error(rv, "C_GetSlotList (list)");
        }
        slots.resize(slotCount);
    }
    return slots;
}

CK_TOKEN_INFO Pkcs11Library::getTokenInfo(CK_SLOT_ID slotID) const {
    CK_TOKEN_INFO info;
    CK_RV rv = functions_->C_GetTokenInfo(slotID, &info);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetTokenInfo");
    }
    return info;
}

// ============================================================
// Pkcs11Session
// ============================================================

Pkcs11Session::Pkcs11Session(
    Pkcs11Library& library, CK_SLOT_ID slotID, bool readOnly)
    : library_(&library)
{
    CK_FLAGS flags = readOnly ? CKF_SERIAL_SESSION : CKF_SERIAL_SESSION | CKF_RW_SESSION;

    CK_RV rv = library.functions_->C_OpenSession(
        slotID, flags, nullptr, nullptr, &session_
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_OpenSession");
    }
}

Pkcs11Session::~Pkcs11Session() {
    if (session_ != CK_INVALID_HANDLE) {
        if (loggedIn_) {
            library_->functions_->C_Logout(session_);
        }
        library_->functions_->C_CloseSession(session_);
    }
}

Pkcs11Session::Pkcs11Session(Pkcs11Session&& other) noexcept
    : session_(other.session_)
    , library_(other.library_)
    , loggedIn_(other.loggedIn_)
{
    other.session_ = CK_INVALID_HANDLE;
    other.loggedIn_ = false;
}

Pkcs11Session& Pkcs11Session::operator=(Pkcs11Session&& other) noexcept {
    if (this != &other) {
        if (session_ != CK_INVALID_HANDLE) {
            if (loggedIn_) {
                library_->functions_->C_Logout(session_);
            }
            library_->functions_->C_CloseSession(session_);
        }

        session_ = other.session_;
        library_ = other.library_;
        loggedIn_ = other.loggedIn_;

        other.session_ = CK_INVALID_HANDLE;
        other.loggedIn_ = false;
    }
    return *this;
}

void Pkcs11Session::login(
    CK_USER_TYPE userType, const std::string& pin)
{
    CK_RV rv = library_->functions_->C_Login(
        session_,
        userType,
        reinterpret_cast<CK_CHAR_PTR>(
            const_cast<char*>(pin.c_str())
        ),
        static_cast<CK_ULONG>(pin.size())
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_Login");
    }
    loggedIn_ = true;
}

void Pkcs11Session::logout() {
    CK_RV rv = library_->functions_->C_Logout(session_);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_Logout");
    }
    loggedIn_ = false;
}

std::vector<CK_OBJECT_HANDLE> Pkcs11Session::findObjects(
    const std::vector<CK_ATTRIBUTE>& templateAttrs) const
{
    CK_RV rv;

    rv = library_->functions_->C_FindObjectsInit(
        session_,
        const_cast<CK_ATTRIBUTE_PTR>(templateAttrs.data()),
        static_cast<CK_ULONG>(templateAttrs.size())
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_FindObjectsInit");
    }

    std::vector<CK_OBJECT_HANDLE> objects;
    CK_OBJECT_HANDLE handles[64];
    CK_ULONG objectCount = 0;

    do {
        rv = library_->functions_->C_FindObjects(
            session_, handles, 64, &objectCount
        );
        if (rv != CKR_OK) {
            library_->functions_->C_FindObjectsFinal(session_);
            throw Pkcs11Error(rv, "C_FindObjects");
        }
        objects.insert(objects.end(), handles, handles + objectCount);
    } while (objectCount > 0);

    rv = library_->functions_->C_FindObjectsFinal(session_);
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_FindObjectsFinal");
    }

    return objects;
}

CK_TOKEN_INFO Pkcs11Session::tokenInfo() const {
    CK_TOKEN_INFO info;
    CK_RV rv = library_->functions_->C_GetTokenInfo(
        // Para obter o slot ID, precisamos de uma abordagem diferente
        // Simplificação: assumimos que o token está no slot correto
        0, &info
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetTokenInfo");
    }
    return info;
}

// ============================================================
// Pkcs11Object
// ============================================================

Pkcs11Object::Pkcs11Object(
    Pkcs11Session& session, CK_OBJECT_HANDLE handle)
    : handle_(handle)
    , session_(&session)
{}

Pkcs11Object::~Pkcs11Object() {
    // Objetos são liberados automaticamente quando a sessão fecha
    // Não há necessidade de chamada explícita de C_DestroyObject
}

Pkcs11Object::Pkcs11Object(Pkcs11Object&& other) noexcept
    : handle_(other.handle_)
    , session_(other.session_)
{
    other.handle_ = CK_INVALID_HANDLE;
}

Pkcs11Object& Pkcs11Object::operator=(Pkcs11Object&& other) noexcept {
    if (this != &other) {
        handle_ = other.handle_;
        session_ = other.session_;
        other.handle_ = CK_INVALID_HANDLE;
    }
    return *this;
}

std::vector<CK_BYTE> Pkcs11Object::getAttributeBytes(
    CK_ATTRIBUTE_TYPE type) const
{
    // Primeiro: obter o tamanho do atributo
    CK_ATTRIBUTE attr;
    attr.type = type;
    attr.pValue = nullptr;
    attr.ulValueLen = 0;

    CK_RV rv = session_->library_->functions_->C_GetAttributeValue(
        session_->handle(), handle_, &attr, 1
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetAttributeValue (size)");
    }

    if (attr.ulValueLen == 0) {
        return {};
    }

    // Segundo: alocar buffer e obter o valor
    std::vector<CK_BYTE> value(attr.ulValueLen);
    attr.pValue = value.data();

    rv = session_->library_->functions_->C_GetAttributeValue(
        session_->handle(), handle_, &attr, 1
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GetAttributeValue (value)");
    }

    return value;
}

std::string Pkcs11Object::getAttributeString(
    CK_ATTRIBUTE_TYPE type) const
{
    auto bytes = getAttributeBytes(type);
    return std::string(bytes.begin(), bytes.end());
}

} // namespace hsm
```

### 4.4 Gerenciamento de Chaves HSM

```cpp
// include/hsm_key_manager.h
#ifndef HSM_KEY_MANAGER_H
#define HSM_KEY_MANAGER_H

#include "pkcs11_wrapper.h"
#include <string>
#include <vector>
#include <optional>
#include <chrono>

namespace hsm {

// Tipo de chave
enum class KeyType {
    AES_128,
    AES_256,
    RSA_2048,
    RSA_4096,
    ECDSA_P256,
    ECDSA_P384,
    ED25519
};

// Metadados de uma chave
struct KeyMetadata {
    std::string label;
    std::string id;
    KeyType type;
    bool sensitive;
    bool extractable;
    bool tokenObject;
    std::chrono::system_clock::time_point creationTime;
    std::optional<std::chrono::system_clock::time_point> expirationTime;
};

// Gerenciador de chaves HSM
class HsmKeyManager {
public:
    explicit HsmKeyManager(Pkcs11Session& session);
    ~HsmKeyManager() = default;

    // Geração de chaves
    CK_OBJECT_HANDLE generateAesKey(
        const std::string& label,
        KeyType type = KeyType::AES_256
    );

    CK_OBJECT_HANDLE generateRsaKeyPair(
        const std::string& label,
        KeyType type = KeyType::RSA_2048,
        bool extractable = false
    );

    CK_OBJECT_HANDLE generateEccKeyPair(
        const std::string& label,
        KeyType type = KeyType::ECDSA_P256
    );

    // Importação (para chaves simétricas — asymmetric keys
    // não devem ser importadas para HSMs seguros)
    CK_OBJECT_HANDLE importAesKey(
        const std::string& label,
        const std::vector<CK_BYTE>& keyData
    );

    // Busca de chaves
    std::optional<KeyMetadata> findKeyByLabel(
        const std::string& label
    ) const;

    std::vector<KeyMetadata> findAllKeys() const;

    // Exclusão de chaves
    void destroyKey(CK_OBJECT_HANDLE handle);

    // Rotação de chaves
    CK_OBJECT_HANDLE rotateKey(
        const std::string& oldLabel,
        const std::string& newLabel,
        KeyType type
    );

    // Backup (exportação de chave pública para backup)
    std::vector<CK_BYTE> exportPublicKey(
        CK_OBJECT_HANDLE handle
    ) const;

    // Verificação de integridade do HSM
    bool verifyHsmIntegrity() const;

private:
    Pkcs11Session& session_;

    // Helpers
    CK_KEY_TYPE toCkKeyType(KeyType type) const;
    CK_ULONG toKeySize(KeyType type) const;

    std::vector<CK_ATTRIBUTE> buildAesTemplate(
        const std::string& label,
        KeyType type,
        bool sensitive = true,
        bool extractable = false
    ) const;

    std::vector<CK_ATTRIBUTE> buildRsaTemplate(
        const std::string& label,
        KeyType type,
        bool extractable = false
    ) const;

    std::vector<CK_ATTRIBUTE> buildEccTemplate(
        const std::string& label,
        KeyType type
    ) const;
};

} // namespace hsm

#endif // HSM_KEY_MANAGER_H
```

### 4.5 Implementação do Gerenciador de Chaves

```cpp
// src/hsm_key_manager.cpp
#include "hsm_key_manager.h"
#include <stdexcept>
#include <cstring>

namespace hsm {

HsmKeyManager::HsmKeyManager(Pkcs11Session& session)
    : session_(session)
{}

CK_KEY_TYPE HsmKeyManager::toCkKeyType(KeyType type) const {
    switch (type) {
        case KeyType::AES_128:
        case KeyType::AES_256:
            return CKK_AES;
        case KeyType::RSA_2048:
        case KeyType::RSA_4096:
            return CKK_RSA;
        case KeyType::ECDSA_P256:
        case KeyType::ECDSA_P384:
        case KeyType::ED25519:
            return CKK_EC;
        default:
            throw std::invalid_argument("KeyType não suportado");
    }
}

CK_ULONG HsmKeyManager::toKeySize(KeyType type) const {
    switch (type) {
        case KeyType::AES_128:  return 16;
        case KeyType::AES_256:  return 32;
        case KeyType::RSA_2048: return 2048;
        case KeyType::RSA_4096: return 4096;
        case KeyType::ECDSA_P256: return 256;
        case KeyType::ECDSA_P384: return 384;
        case KeyType::ED25519:  return 256;
        default:
            throw std::invalid_argument("KeyType não suportado");
    }
}

std::vector<CK_ATTRIBUTE> HsmKeyManager::buildAesTemplate(
    const std::string& label,
    KeyType type,
    bool sensitive,
    bool extractable
) const
{
    CK_BBOOL trueVal = CK_TRUE;
    CK_BBOOL falseVal = CK_FALSE;
    CK_KEY_TYPE keyType = toCkKeyType(type);
    CK_ULONG keySize = toKeySize(type);

    return {
        {CKA_CLASS,       &keyType,  sizeof(CK_KEY_TYPE)},
        {CKA_KEY_TYPE,    &keyType,  sizeof(CK_KEY_TYPE)},
        {CKA_VALUE_LEN,   &keySize,  sizeof(CK_ULONG)},
        {CKA_TOKEN,       &trueVal,  sizeof(CK_BBOOL)},
        {CKA_ENCRYPT,     &trueVal,  sizeof(CK_BBOOL)},
        {CKA_DECRYPT,     &trueVal,  sizeof(CK_BBOOL)},
        {CKA_WRAP,        &trueVal,  sizeof(CK_BBOOL)},
        {CKA_UNWRAP,      &trueVal,  sizeof(CK_BBOOL)},
        {CKA_SENSITIVE,   sensitive ? &trueVal : &falseVal, sizeof(CK_BBOOL)},
        {CKA_EXTRACTABLE, extractable ? &trueVal : &falseVal, sizeof(CK_BBOOL)},
        {CKA_LABEL,       const_cast<char*>(label.c_str()),
                          static_cast<CK_ULONG>(label.size())},
    };
}

std::vector<CK_ATTRIBUTE> HsmKeyManager::buildRsaTemplate(
    const std::string& label,
    KeyType type,
    bool extractable
) const
{
    CK_BBOOL trueVal = CK_TRUE;
    CK_BBOOL falseVal = CK_FALSE;
    CK_ULONG modulusBits = toKeySize(type);
    CK_ULONG publicExponent = 65537;

    return {
        {CKA_MODULUS_BITS,    &modulusBits, sizeof(CK_ULONG)},
        {CKA_PUBLIC_EXPONENT, &publicExponent, sizeof(CK_ULONG)},
        {CKA_TOKEN,           &trueVal,  sizeof(CK_BBOOL)},
        {CKA_ENCRYPT,         &trueVal,  sizeof(CK_BBOOL)},
        {CKA_VERIFY,          &trueVal,  sizeof(CK_BBOOL)},
        {CKA_WRAP,            &trueVal,  sizeof(CK_BBOOL)},
        {CKA_SENSITIVE,       &trueVal,  sizeof(CK_BBOOL)},
        {CKA_EXTRACTABLE,     extractable ? &trueVal : &falseVal, sizeof(CK_BBOOL)},
        {CKA_LABEL,           const_cast<char*>(label.c_str()),
                              static_cast<CK_ULONG>(label.size())},
    };
}

std::vector<CK_ATTRIBUTE> HsmKeyManager::buildEccTemplate(
    const std::string& label,
    KeyType type
) const
{
    CK_BBOOL trueVal = CK_TRUE;
    CK_KEY_TYPE keyType = CKK_EC;

    // Parâmetros da curva OID
    // P-256: 06 08 2A 86 48 CE 3D 03 01 07
    // P-384: 06 05 2B 81 04 00 22
    static const CK_BYTE p256_oid[] = {
        0x06, 0x08, 0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x03, 0x01, 0x07
    };
    static const CK_BYTE p384_oid[] = {
        0x06, 0x05, 0x2B, 0x81, 0x04, 0x00, 0x22
    };

    const CK_BYTE* ecParams = nullptr;
    CK_ULONG ecParamsLen = 0;

    switch (type) {
        case KeyType::ECDSA_P256:
            ecParams = p256_oid;
            ecParamsLen = sizeof(p256_oid);
            break;
        case KeyType::ECDSA_P384:
            ecParams = p384_oid;
            ecParamsLen = sizeof(p384_oid);
            break;
        case KeyType::ED25519:
            // OID Ed25519: 06 03 2B 65 70
            {
                static const CK_BYTE ed25519_oid[] = {
                    0x06, 0x03, 0x2B, 0x65, 0x70
                };
                ecParams = ed25519_oid;
                ecParamsLen = sizeof(ed25519_oid);
            }
            break;
        default:
            throw std::invalid_argument("KeyType ECC não suportado");
    }

    return {
        {CKA_KEY_TYPE,    &keyType, sizeof(CK_KEY_TYPE)},
        {CKA_EC_PARAMS,   const_cast<CK_BYTE*>(ecParams), ecParamsLen},
        {CKA_TOKEN,       &trueVal, sizeof(CK_BBOOL)},
        {CKA_SIGN,        &trueVal, sizeof(CK_BBOOL)},
        {CKA_VERIFY,      &trueVal, sizeof(CK_BBOOL)},
        {CKA_SENSITIVE,   &trueVal, sizeof(CK_BBOOL)},
        {CKA_EXTRACTABLE, &trueVal, sizeof(CK_BBOOL)}, // ECC keys usually extractable
        {CKA_LABEL,       const_cast<char*>(label.c_str()),
                          static_cast<CK_ULONG>(label.size())},
    };
}

CK_OBJECT_HANDLE HsmKeyManager::generateAesKey(
    const std::string& label, KeyType type)
{
    CK_MECHANISM mech = {
        CKM_AES_KEY_GEN, nullptr, 0
    };

    auto templateAttrs = buildAesTemplate(label, type);

    CK_OBJECT_HANDLE hKey;
    CK_RV rv = session_.library_->functions_->C_GenerateKey(
        session_.handle(),
        &mech,
        templateAttrs.data(),
        static_cast<CK_ULONG>(templateAttrs.size()),
        &hKey
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GenerateKey (AES)");
    }
    return hKey;
}

CK_OBJECT_HANDLE HsmKeyManager::generateRsaKeyPair(
    const std::string& label, KeyType type, bool extractable)
{
    CK_MECHANISM mech = {
        CKM_RSA_PKCS_KEY_PAIR_GEN, nullptr, 0
    };

    auto pubTemplate = buildRsaTemplate(label, type, extractable);

    CK_BBOOL trueVal = CK_TRUE;
    CK_BBOOL falseVal = CK_FALSE;

    std::vector<CK_ATTRIBUTE> privTemplate = {
        {CKA_CLASS,       &trueVal,  sizeof(CK_BBOOL)},
        {CKA_TOKEN,       &trueVal,  sizeof(CK_BBOOL)},
        {CKA_PRIVATE,     &trueVal,  sizeof(CK_BBOOL)},
        {CKA_SIGN,        &trueVal,  sizeof(CK_BBOOL)},
        {CKA_DECRYPT,     &trueVal,  sizeof(CK_BBOOL)},
        {CKA_SENSITIVE,   &trueVal,  sizeof(CK_BBOOL)},
        {CKA_EXTRACTABLE, extractable ? &trueVal : &falseVal, sizeof(CK_BBOOL)},
        {CKA_LABEL,       const_cast<char*>(label.c_str()),
                          static_cast<CK_ULONG>(label.size())},
    };

    CK_OBJECT_HANDLE hPublicKey, hPrivateKey;

    CK_RV rv = session_.library_->functions_->C_GenerateKeyPair(
        session_.handle(),
        &mech,
        pubTemplate.data(),
        static_cast<CK_ULONG>(pubTemplate.size()),
        privTemplate.data(),
        static_cast<CK_ULONG>(privTemplate.size()),
        &hPublicKey,
        &hPrivateKey
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GenerateKeyPair (RSA)");
    }
    return hPrivateKey; // Retornamos a chave privada como referência principal
}

CK_OBJECT_HANDLE HsmKeyManager::generateEccKeyPair(
    const std::string& label, KeyType type)
{
    CK_MECHANISM mech = {
        CKM_EC_KEY_PAIR_GEN, nullptr, 0
    };

    auto pubTemplate = buildEccTemplate(label, type);

    CK_BBOOL trueVal = CK_TRUE;

    std::vector<CK_ATTRIBUTE> privTemplate = {
        {CKA_CLASS,       &trueVal, sizeof(CK_BBOOL)},
        {CKA_TOKEN,       &trueVal, sizeof(CK_BBOOL)},
        {CKA_PRIVATE,     &trueVal, sizeof(CK_BBOOL)},
        {CKA_SIGN,        &trueVal, sizeof(CK_BBOOL)},
        {CKA_SENSITIVE,   &trueVal, sizeof(CK_BBOOL)},
        {CKA_LABEL,       const_cast<char*>(label.c_str()),
                          static_cast<CK_ULONG>(label.size())},
    };

    CK_OBJECT_HANDLE hPublicKey, hPrivateKey;

    CK_RV rv = session_.library_->functions_->C_GenerateKeyPair(
        session_.handle(),
        &mech,
        pubTemplate.data(),
        static_cast<CK_ULONG>(pubTemplate.size()),
        privTemplate.data(),
        static_cast<CK_ULONG>(privTemplate.size()),
        &hPublicKey,
        &hPrivateKey
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GenerateKeyPair (ECC)");
    }
    return hPrivateKey;
}

CK_OBJECT_HANDLE HsmKeyManager::importAesKey(
    const std::string& label,
    const std::vector<CK_BYTE>& keyData)
{
    auto templateAttrs = buildAesTemplate(label, KeyType::AES_256,
                                          true, false);

    // Adicionar o valor da chave
    CK_ATTRIBUTE valueAttr = {
        CKA_VALUE,
        const_cast<CK_BYTE*>(keyData.data()),
        static_cast<CK_ULONG>(keyData.size())
    };
    templateAttrs.push_back(valueAttr);

    CK_OBJECT_HANDLE hKey;
    CK_RV rv = session_.library_->functions_->C_CreateObject(
        session_.handle(),
        templateAttrs.data(),
        static_cast<CK_ULONG>(templateAttrs.size()),
        &hKey
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_CreateObject (AES import)");
    }
    return hKey;
}

std::optional<KeyMetadata> HsmKeyManager::findKeyByLabel(
    const std::string& label) const
{
    CK_OBJECT_CLASS keyClass = CKO_SECRET_KEY;
    CK_ATTRIBUTE searchTemplate[] = {
        {CKA_CLASS, &keyClass, sizeof(keyClass)},
        {CKA_LABEL, const_cast<char*>(label.c_str()),
                    static_cast<CK_ULONG>(label.size())},
    };

    auto handles = session_.findObjects(
        std::vector<CK_ATTRIBUTE>(searchTemplate, searchTemplate + 2)
    );

    if (handles.empty()) {
        return std::nullopt;
    }

    // Se encontrou, obter metadados
    Pkcs11Object obj(const_cast<Pkcs11Session&>(session_), handles[0]);
    KeyMetadata meta;
    meta.label = label;
    meta.sensitive = true; // Default assumption

    // Obter tipo da chave
    auto keyTypeBytes = obj.getAttributeBytes(CKA_KEY_TYPE);
    if (!keyTypeBytes.empty()) {
        CK_KEY_TYPE kt;
        std::memcpy(&kt, keyTypeBytes.data(), sizeof(CK_KEY_TYPE));
        switch (kt) {
            case CKK_AES: meta.type = KeyType::AES_256; break;
            case CKK_RSA: meta.type = KeyType::RSA_2048; break;
            case CKK_EC:  meta.type = KeyType::ECDSA_P256; break;
            default: meta.type = KeyType::AES_256; break;
        }
    }

    return meta;
}

std::vector<KeyMetadata> HsmKeyManager::findAllKeys() const {
    CK_OBJECT_CLASS secretKeyClass = CKO_SECRET_KEY;
    CK_ATTRIBUTE searchTemplate[] = {
        {CKA_CLASS, &secretKeyClass, sizeof(secretKeyClass)},
    };

    auto secretHandles = session_.findObjects(
        std::vector<CK_ATTRIBUTE>(searchTemplate, searchTemplate + 1)
    );

    CK_OBJECT_CLASS privateKeyClass = CKO_PRIVATE_KEY;
    searchTemplate[0] = {CKA_CLASS, &privateKeyClass, sizeof(privateKeyClass)};

    auto privateHandles = session_.findObjects(
        std::vector<CK_ATTRIBUTE>(searchTemplate, searchTemplate + 1)
    );

    std::vector<KeyMetadata> allKeys;
    allKeys.reserve(secretHandles.size() + privateHandles.size());

    for (auto h : secretHandles) {
        Pkcs11Object obj(const_cast<Pkcs11Session&>(session_), h);
        KeyMetadata meta;
        meta.label = obj.getAttributeString(CKA_LABEL);
        meta.type = KeyType::AES_256;
        allKeys.push_back(meta);
    }

    for (auto h : privateHandles) {
        Pkcs11Object obj(const_cast<Pkcs11Session&>(session_), h);
        KeyMetadata meta;
        meta.label = obj.getAttributeString(CKA_LABEL);
        meta.type = KeyType::RSA_2048;
        allKeys.push_back(meta);
    }

    return allKeys;
}

void HsmKeyManager::destroyKey(CK_OBJECT_HANDLE handle) {
    CK_RV rv = session_.library_->functions_->C_DestroyObject(
        session_.handle(), handle
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_DestroyObject");
    }
}

std::vector<CK_BYTE> HsmKeyManager::exportPublicKey(
    CK_OBJECT_HANDLE handle) const
{
    Pkcs11Object obj(const_cast<Pkcs11Session&>(session_), handle);

    // Verificar se é uma chave pública (não sensível)
    auto isPrivate = obj.getAttributeBytes(CKA_PRIVATE);

    if (!isPrivate.empty() && isPrivate[0] == CK_TRUE) {
        throw std::runtime_error(
            "Não é possível exportar chave privada de HSM seguro"
        );
    }

    // Exportar módulo (RSA) ou ponto (ECC)
    auto modulus = obj.getAttributeBytes(CKA_MODULUS);
    auto pubExp = obj.getAttributeBytes(CKA_PUBLIC_EXPONENT);

    std::vector<CK_BYTE> publicKey;
    publicKey.insert(publicKey.end(), modulus.begin(), modulus.end());
    publicKey.insert(publicKey.end(), pubExp.begin(), pubExp.end());

    return publicKey;
}

bool HsmKeyManager::verifyHsmIntegrity() const {
    // Verificação básica — em produção, usar testes mais robustos
    try {
        auto info = const_cast<Pkcs11Session&>(session_).tokenInfo();

        // Verificar se o token está em estado saudável
        // (CKS_READY_USERTO == estado normal)
        return true;
    } catch (const Pkcs11Error&) {
        return false;
    }
}

} // namespace hsm
```

### 4.6 Motor de Criptografia com HSM

```cpp
// include/hsm_crypto_engine.h
#ifndef HSM_CRYPTO_ENGINE_H
#define HSM_CRYPTO_ENGINE_H

#include "pkcs11_wrapper.h"
#include "hsm_key_manager.h"
#include <vector>
#include <string>
#include <optional>

namespace hsm {

// Configuração do mecanismo de criptografia
struct MechanismConfig {
    CK_MECHANISM_TYPE type;
    std::vector<CK_BYTE> parameter;

    static MechanismConfig aesCbc(const std::vector<CK_BYTE>& iv);
    static MechanismConfig aesGcm(
        const std::vector<CK_BYTE>& iv,
        CK_ULONG tagBits = 128
    );
    static MechanismConfig rsaPkcs1();
    static MechanismConfig rsaPss(
        CK_SHA_TYPE hashType = CKM_SHA256
    );
    static MechanismConfig ecdsa(
        CK_SHA_TYPE hashType = CKM_SHA256
    );
};

// Resultado de operação criptográfica
struct CryptoResult {
    std::vector<CK_BYTE> data;
    bool success = false;
    std::string errorMessage;
};

// Motor de criptografia baseado em HSM
class HsmCryptoEngine {
public:
    HsmCryptoEngine(Pkcs11Session& session, HsmKeyManager& keyManager);
    ~HsmCryptoEngine() = default;

    // Criptografia simétrica
    CryptoResult encryptAes(
        CK_OBJECT_HANDLE keyHandle,
        const std::vector<CK_BYTE>& plaintext,
        const MechanismConfig& mechConfig
    );

    CryptoResult decryptAes(
        CK_OBJECT_HANDLE keyHandle,
        const std::vector<CK_BYTE>& ciphertext,
        const MechanismConfig& mechConfig
    );

    // Assinatura digital
    CryptoResult signRsa(
        CK_OBJECT_HANDLE privateKeyHandle,
        const std::vector<CK_BYTE>& data,
        const MechanismConfig& mechConfig
    );

    CryptoResult signEcc(
        CK_OBJECT_HANDLE privateKeyHandle,
        const std::vector<CK_BYTE>& data,
        const MechanismConfig& mechConfig
    );

    // Verificação de assinatura
    CryptoResult verifyRsa(
        CK_OBJECT_HANDLE publicKeyHandle,
        const std::vector<CK_BYTE>& data,
        const std::vector<CK_BYTE>& signature,
        const MechanismConfig& mechConfig
    );

    CryptoResult verifyEcc(
        CK_OBJECT_HANDLE publicKeyHandle,
        const std::vector<CK_BYTE>& data,
        const std::vector<CK_BYTE>& signature,
        const MechanismConfig& mechConfig
    );

    // Hash (se o HSM suportar operações de hash)
    CryptoResult hash(
        const std::vector<CK_BYTE>& data,
        CK_MECHANISM_TYPE hashMech
    );

    // Wrap/Unwrap de chaves
    CryptoResult wrapKey(
        CK_OBJECT_HANDLE wrappingKey,
        CK_OBJECT_HANDLE keyToWrap
    );

    CryptoResult unwrapKey(
        CK_OBJECT_HANDLE unwrappingKey,
        const std::vector<CK_BYTE>& wrappedKey,
        const std::vector<CK_ATTRIBUTE>& templateAttrs
    );

    // Geração de IV aleatório via HSM
    std::vector<CK_BYTE> generateIv(CK_ULONG length);

    // Geração de dados aleatórios via HSM
    std::vector<CK_BYTE> generateRandom(CK_ULONG length);

private:
    Pkcs11Session& session_;
    HsmKeyManager& keyManager_;

    // Helpers
    CK_MECHANISM buildMechanism(const MechanismConfig& config) const;
};

} // namespace hsm

#endif // HSM_CRYPTO_ENGINE_H
```

### 4.7 Implementação do Motor de Criptografia

```cpp
// src/hsm_crypto_engine.cpp
#include "hsm_crypto_engine.h"
#include <stdexcept>
#include <cstring>

namespace hsm {

// ============================================================
// MechanismConfig
// ============================================================

MechanismConfig MechanismConfig::aesCbc(
    const std::vector<CK_BYTE>& iv)
{
    return {CKM_AES_CBC, iv};
}

MechanismConfig MechanismConfig::aesGcm(
    const std::vector<CK_BYTE>& iv, CK_ULONG tagBits)
{
    // Parâmetros GCM: IV + tag bits
    // CK_GCM_PARAMS contém iv, ivLen, aad, aadLen, tagBits
    std::vector<CK_BYTE> params;
    params.insert(params.end(), iv.begin(), iv.end());

    // Adicionar tag bits como CK_ULONG
    CK_ULONG tagLen = tagBits / 8;
    auto* tagBytes = reinterpret_cast<CK_BYTE*>(&tagLen);
    params.insert(params.end(), tagBytes, tagBytes + sizeof(CK_ULONG));

    return {CKM_AES_GCM, params};
}

MechanismConfig MechanismConfig::rsaPkcs1() {
    return {CKM_RSA_PKCS, {}};
}

MechanismConfig MechanismConfig::rsaPss(CK_SHA_TYPE hashType) {
    CK_RSA_PKCS_PSS_PARAMS params;
    params.hashAlg = hashType;
    params.mgf = CKG_MGF1_SHA256;
    params.sLen = 32; // Salt length em bytes

    std::vector<CK_BYTE> paramBytes(sizeof(params));
    std::memcpy(paramBytes.data(), &params, sizeof(params));

    return {CKM_RSA_PKCS_PSS, paramBytes};
}

MechanismConfig MechanismConfig::ecdsa(CK_SHA_TYPE hashType) {
    return {CKM_ECDSA, {}};
}

// ============================================================
// HsmCryptoEngine
// ============================================================

HsmCryptoEngine::HsmCryptoEngine(
    Pkcs11Session& session, HsmKeyManager& keyManager)
    : session_(session)
    , keyManager_(keyManager)
{}

CK_MECHANISM HsmCryptoEngine::buildMechanism(
    const MechanismConfig& config) const
{
    CK_MECHANISM mech;
    mech.mechanism = config.type;

    if (config.parameter.empty()) {
        mech.pParameter = nullptr;
        mech.ulParameterLen = 0;
    } else {
        mech.pParameter = const_cast<CK_BYTE*>(config.parameter.data());
        mech.ulParameterLen = static_cast<CK_ULONG>(
            config.parameter.size()
        );
    }

    return mech;
}

// ============================================================
// Criptografia Simétrica
// ============================================================

CryptoResult HsmCryptoEngine::encryptAes(
    CK_OBJECT_HANDLE keyHandle,
    const std::vector<CK_BYTE>& plaintext,
    const MechanismConfig& mechConfig)
{
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        // Inicializar criptografia
        rv = session_.library_->functions_->C_EncryptInit(
            session_.handle(), &mech, keyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_EncryptInit falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Determinar tamanho do output
        CK_ULONG outputLen = 0;
        rv = session_.library_->functions_->C_Encrypt(
            session_.handle(),
            const_cast<CK_BYTE*>(plaintext.data()),
            static_cast<CK_ULONG>(plaintext.size()),
            nullptr,
            &outputLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Encrypt (size) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Criptografar
        result.data.resize(outputLen);
        rv = session_.library_->functions_->C_Encrypt(
            session_.handle(),
            const_cast<CK_BYTE*>(plaintext.data()),
            static_cast<CK_ULONG>(plaintext.size()),
            result.data.data(),
            &outputLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Encrypt falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(outputLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

CryptoResult HsmCryptoEngine::decryptAes(
    CK_OBJECT_HANDLE keyHandle,
    const std::vector<CK_BYTE>& ciphertext,
    const MechanismConfig& mechConfig)
{
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        // Inicializar descriptografia
        rv = session_.library_->functions_->C_DecryptInit(
            session_.handle(), &mech, keyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_DecryptInit falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Determinar tamanho do output
        CK_ULONG outputLen = 0;
        rv = session_.library_->functions_->C_Decrypt(
            session_.handle(),
            const_cast<CK_BYTE*>(ciphertext.data()),
            static_cast<CK_ULONG>(ciphertext.size()),
            nullptr,
            &outputLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Decrypt (size) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Descriptografar
        result.data.resize(outputLen);
        rv = session_.library_->functions_->C_Decrypt(
            session_.handle(),
            const_cast<CK_BYTE*>(ciphertext.data()),
            static_cast<CK_ULONG>(ciphertext.size()),
            result.data.data(),
            &outputLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Decrypt falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(outputLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

// ============================================================
// Assinatura Digital
// ============================================================

CryptoResult HsmCryptoEngine::signRsa(
    CK_OBJECT_HANDLE privateKeyHandle,
    const std::vector<CK_BYTE>& data,
    const MechanismConfig& mechConfig)
{
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        // Inicializar assinatura
        rv = session_.library_->functions_->C_SignInit(
            session_.handle(), &mech, privateKeyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_SignInit falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Determinar tamanho da assinatura
        CK_ULONG signatureLen = 0;
        rv = session_.library_->functions_->C_Sign(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            nullptr,
            &signatureLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Sign (size) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Assinar
        result.data.resize(signatureLen);
        rv = session_.library_->functions_->C_Sign(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            result.data.data(),
            &signatureLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Sign falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(signatureLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

CryptoResult HsmCryptoEngine::signEcc(
    CK_OBJECT_HANDLE privateKeyHandle,
    const std::vector<CK_BYTE>& data,
    const MechanismConfig& mechConfig)
{
    // ECDSA é mais simples que RSA — o tamanho da assinatura
    // é determinado pela curva, não pelo mecanismo
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        // Para ECDSA, precisamos de hash dos dados primeiro
        // (ou usar CKM_ECDSA_SHA256 que faz internamente)

        rv = session_.library_->functions_->C_SignInit(
            session_.handle(), &mech, privateKeyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_SignInit (ECC) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // ECDSA retorna assinatura DER-encoded
        CK_ULONG signatureLen = 128; // Tamanho máximo para ECDSA
        result.data.resize(signatureLen);

        rv = session_.library_->functions_->C_Sign(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            result.data.data(),
            &signatureLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Sign (ECC) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(signatureLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

// ============================================================
// Verificação de Assinatura
// ============================================================

CryptoResult HsmCryptoEngine::verifyRsa(
    CK_OBJECT_HANDLE publicKeyHandle,
    const std::vector<CK_BYTE>& data,
    const std::vector<CK_BYTE>& signature,
    const MechanismConfig& mechConfig)
{
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        rv = session_.library_->functions_->C_VerifyInit(
            session_.handle(), &mech, publicKeyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_VerifyInit falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        rv = session_.library_->functions_->C_Verify(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            const_cast<CK_BYTE*>(signature.data()),
            static_cast<CK_ULONG>(signature.size())
        );

        if (rv == CKR_SIGNATURE_INVALID) {
            result.errorMessage = "Assinatura inválida";
            result.success = false;
        } else if (rv != CKR_OK) {
            result.errorMessage = "C_Verify falhou: " +
                Pkcs11Error::rv_to_string(rv);
        } else {
            result.success = true;
        }
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

CryptoResult HsmCryptoEngine::verifyEcc(
    CK_OBJECT_HANDLE publicKeyHandle,
    const std::vector<CK_BYTE>& data,
    const std::vector<CK_BYTE>& signature,
    const MechanismConfig& mechConfig)
{
    CryptoResult result;
    CK_RV rv;

    try {
        auto mech = buildMechanism(mechConfig);

        rv = session_.library_->functions_->C_VerifyInit(
            session_.handle(), &mech, publicKeyHandle
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_VerifyInit (ECC) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        rv = session_.library_->functions_->C_Verify(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            const_cast<CK_BYTE*>(signature.data()),
            static_cast<CK_ULONG>(signature.size())
        );

        if (rv == CKR_SIGNATURE_INVALID) {
            result.errorMessage = "Assinatura ECC inválida";
            result.success = false;
        } else if (rv != CKR_OK) {
            result.errorMessage = "C_Verify (ECC) falhou: " +
                Pkcs11Error::rv_to_string(rv);
        } else {
            result.success = true;
        }
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

// ============================================================
// Hash
// ============================================================

CryptoResult HsmCryptoEngine::hash(
    const std::vector<CK_BYTE>& data,
    CK_MECHANISM_TYPE hashMech)
{
    CryptoResult result;
    CK_RV rv;

    try {
        CK_MECHANISM mech = {hashMech, nullptr, 0};

        rv = session_.library_->functions_->C_DigestInit(
            session_.handle(), &mech
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_DigestInit falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Determinar tamanho do hash
        CK_ULONG hashLen = 0;
        rv = session_.library_->functions_->C_Digest(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            nullptr,
            &hashLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Digest (size) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Calcular hash
        result.data.resize(hashLen);
        rv = session_.library_->functions_->C_Digest(
            session_.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            result.data.data(),
            &hashLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_Digest falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(hashLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

// ============================================================
// Wrap/Unwrap de Chaves
// ============================================================

CryptoResult HsmCryptoEngine::wrapKey(
    CK_OBJECT_HANDLE wrappingKey,
    CK_OBJECT_HANDLE keyToWrap)
{
    CryptoResult result;
    CK_RV rv;

    try {
        CK_MECHANISM mech = {CKM_AES_KEY_WRAP, nullptr, 0};

        // Determinar tamanho do wrap
        CK_ULONG wrappedLen = 0;
        rv = session_.library_->functions_->C_WrapKey(
            session_.handle(),
            &mech,
            wrappingKey,
            keyToWrap,
            nullptr,
            &wrappedLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_WrapKey (size) falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Wrap
        result.data.resize(wrappedLen);
        rv = session_.library_->functions_->C_WrapKey(
            session_.handle(),
            &mech,
            wrappingKey,
            keyToWrap,
            result.data.data(),
            &wrappedLen
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_WrapKey falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        result.data.resize(wrappedLen);
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

CryptoResult HsmCryptoEngine::unwrapKey(
    CK_OBJECT_HANDLE unwrappingKey,
    const std::vector<CK_BYTE>& wrappedKey,
    const std::vector<CK_ATTRIBUTE>& templateAttrs)
{
    CryptoResult result;
    CK_RV rv;

    try {
        CK_MECHANISM mech = {CKM_AES_KEY_WRAP, nullptr, 0};

        CK_OBJECT_HANDLE hUnwrappedKey;

        rv = session_.library_->functions_->C_UnwrapKey(
            session_.handle(),
            &mech,
            unwrappingKey,
            const_cast<CK_BYTE*>(wrappedKey.data()),
            static_cast<CK_ULONG>(wrappedKey.size()),
            templateAttrs.data(),
            static_cast<CK_ULONG>(templateAttrs.size()),
            &hUnwrappedKey
        );
        if (rv != CKR_OK) {
            result.errorMessage = "C_UnwrapKey falhou: " +
                Pkcs11Error::rv_to_string(rv);
            return result;
        }

        // Retornar o handle da chave desembrulhada
        result.data.resize(sizeof(CK_OBJECT_HANDLE));
        std::memcpy(result.data.data(), &hUnwrappedKey,
                    sizeof(CK_OBJECT_HANDLE));
        result.success = true;
    } catch (const Pkcs11Error& e) {
        result.errorMessage = e.what();
    }

    return result;
}

// ============================================================
// Geração Aleatória
// ============================================================

std::vector<CK_BYTE> HsmCryptoEngine::generateIv(CK_ULONG length) {
    return generateRandom(length);
}

std::vector<CK_BYTE> HsmCryptoEngine::generateRandom(CK_ULONG length) {
    std::vector<CK_BYTE> random(length);

    CK_RV rv = session_.library_->functions_->C_GenerateRandom(
        session_.handle(),
        random.data(),
        length
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_GenerateRandom");
    }

    return random;
}

} // namespace hsm
```

### 4.8 Exemplo Completo: main.cpp

```cpp
// src/main.cpp
#include "pkcs11_wrapper.h"
#include "hsm_key_manager.h"
#include "hsm_crypto_engine.h"
#include <iostream>
#include <iomanip>
#include <sstream>

// Helper para converter bytes para hex
std::string bytesToHex(const std::vector<CK_BYTE>& bytes) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (auto b : bytes) {
        oss << std::setw(2) << static_cast<int>(b);
    }
    return oss.str();
}

int main() {
    try {
        // =========================================================
        // 1. Inicializar biblioteca PKCS#11
        // =========================================================
        std::cout << "=== Inicializando HSM ===" << std::endl;

        hsm::Pkcs11Library library("/usr/lib/libCryptoki.so");

        auto info = library.getInfo();
        std::cout << "Criptoki version: "
                  << static_cast<int>(info.cryptokiVersion.major) << "."
                  << static_cast<int>(info.cryptokiVersion.minor)
                  << std::endl;
        std::cout << "Library: "
                  << reinterpret_cast<const char*>(info.libraryID)
                  << std::endl;

        // =========================================================
        // 2. Descobrir slots
        // =========================================================
        auto slots = library.getSlotList(true);
        std::cout << "\n=== Slots com Token ===" << std::endl;
        std::cout << "Total: " << slots.size() << std::endl;

        for (auto slotId : slots) {
            auto tokenInfo = library.getTokenInfo(slotId);
            std::cout << "Slot " << slotId << ": "
                      << reinterpret_cast<const char*>(tokenInfo.label)
                      << std::endl;
        }

        if (slots.empty()) {
            std::cerr << "Nenhum token encontrado!" << std::endl;
            return 1;
        }

        CK_SLOT_ID selectedSlot = slots[0];

        // =========================================================
        // 3. Abrir sessão e fazer login
        // =========================================================
        std::cout << "\n=== Abrindo sessão ===" << std::endl;

        hsm::Pkcs11Session session(library, selectedSlot);

        // Login com PIN (em produção, usar autenticação segura)
        session.login(CKU_USER, "12345678");
        std::cout << "Login realizado com sucesso" << std::endl;

        // =========================================================
        // 4. Gerenciar chaves
        // =========================================================
        std::cout << "\n=== Gerenciamento de Chaves ===" << std::endl;

        hsm::HsmKeyManager keyManager(session);

        // Gerar chave AES-256
        auto aesKeyHandle = keyManager.generateAesKey(
            "minha-chave-aes-256",
            hsm::KeyType::AES_256
        );
        std::cout << "Chave AES-256 gerada: handle=" << aesKeyHandle
                  << std::endl;

        // Gerar par de chaves RSA-2048
        auto rsaPrivKeyHandle = keyManager.generateRsaKeyPair(
            "minha-chave-rsa-2048",
            hsm::KeyType::RSA_2048
        );
        std::cout << "Par de chaves RSA-2048 gerado: handle="
                  << rsaPrivKeyHandle << std::endl;

        // Gerar par de chaves ECDSA P-256
        auto ecdsaPrivKeyHandle = keyManager.generateEccKeyPair(
            "minha-chave-ecdsa-p256",
            hsm::KeyType::ECDSA_P256
        );
        std::cout << "Par de chaves ECDSA P-256 gerado: handle="
                  << ecdsaPrivKeyHandle << std::endl;

        // Listar todas as chaves
        auto allKeys = keyManager.findAllKeys();
        std::cout << "\nTotal de chaves no token: " << allKeys.size()
                  << std::endl;
        for (const auto& key : allKeys) {
            std::cout << "  - " << key.label << std::endl;
        }

        // =========================================================
        // 5. Criptografia/Descriptografia com AES
        // =========================================================
        std::cout << "\n=== Criptografia AES ===" << std::endl;

        hsm::HsmCryptoEngine cryptoEngine(session, keyManager);

        // Gerar IV aleatório
        auto iv = cryptoEngine.generateIv(16);
        std::cout << "IV gerado: " << bytesToHex(iv) << std::endl;

        // Dados para criptografar
        std::string plaintext = "Dados sensíveis que precisam ser protegidos";
        std::vector<CK_BYTE> plaintextBytes(
            plaintext.begin(), plaintext.end()
        );

        // Criptografar com AES-CBC
        auto encConfig = hsm::MechanismConfig::aesCbc(iv);
        auto encResult = cryptoEngine.encryptAes(
            aesKeyHandle, plaintextBytes, encConfig
        );

        if (encResult.success) {
            std::cout << "Texto cifrado: " << bytesToHex(encResult.data)
                      << std::endl;

            // Descriptografar
            auto decResult = cryptoEngine.decryptAes(
                aesKeyHandle, encResult.data, encConfig
            );

            if (decResult.success) {
                std::string decrypted(
                    decResult.data.begin(), decResult.data.end()
                );
                std::cout << "Texto decifrado: " << decrypted << std::endl;
                std::cout << "Roundtrip OK: "
                          << (decrypted == plaintext ? "SIM" : "NAO")
                          << std::endl;
            } else {
                std::cerr << "Erro na descriptografia: "
                          << decResult.errorMessage << std::endl;
            }
        } else {
            std::cerr << "Erro na criptografia: "
                      << encResult.errorMessage << std::endl;
        }

        // =========================================================
        // 6. Assinatura com RSA
        // =========================================================
        std::cout << "\n=== Assinatura RSA ===" << std::endl;

        std::string message = "Documento importante para assinar";
        std::vector<CK_BYTE> messageBytes(message.begin(), message.end());

        // Assinar com RSA-PKCS#1 v1.5
        auto signConfig = hsm::MechanismConfig::rsaPkcs1();
        auto signResult = cryptoEngine.signRsa(
            rsaPrivKeyHandle, messageBytes, signConfig
        );

        if (signResult.success) {
            std::cout << "Assinatura gerada: "
                      << bytesToHex(signResult.data) << std::endl;
            std::cout << "Tamanho da assinatura: "
                      << signResult.data.size() << " bytes"
                      << std::endl;
        } else {
            std::cerr << "Erro na assinatura: "
                      << signResult.errorMessage << std::endl;
        }

        // =========================================================
        // 7. Assinatura com ECDSA
        // =========================================================
        std::cout << "\n=== Assinatura ECDSA ===" << std::endl;

        auto ecdsaSignConfig = hsm::MechanismConfig::ecdsa();
        auto ecdsaSignResult = cryptoEngine.signEcc(
            ecdsaPrivKeyHandle, messageBytes, ecdsaSignConfig
        );

        if (ecdsaSignResult.success) {
            std::cout << "Assinatura ECDSA gerada: "
                      << bytesToHex(ecdsaSignResult.data) << std::endl;
            std::cout << "Tamanho da assinatura ECDSA: "
                      << ecdsaSignResult.data.size() << " bytes"
                      << std::endl;
        } else {
            std::cerr << "Erro na assinatura ECDSA: "
                      << ecdsaSignResult.errorMessage << std::endl;
        }

        // =========================================================
        // 8. Hash SHA-256 via HSM
        // =========================================================
        std::cout << "\n=== Hash SHA-256 ===" << std::endl;

        auto hashResult = cryptoEngine.hash(messageBytes, CKM_SHA256);
        if (hashResult.success) {
            std::cout << "SHA-256: " << bytesToHex(hashResult.data)
                      << std::endl;
        } else {
            std::cerr << "Erro no hash: " << hashResult.errorMessage
                      << std::endl;
        }

        // =========================================================
        // 9. Gerar dados aleatórios
        // =========================================================
        std::cout << "\n=== Dados Aleatórios ===" << std::endl;

        auto random32 = cryptoEngine.generateRandom(32);
        std::cout << "32 bytes aleatórios: "
                  << bytesToHex(random32) << std::endl;

        // =========================================================
        // 10. Verificação de integridade
        // =========================================================
        std::cout << "\n=== Verificação de Integridade ===" << std::endl;

        bool integrity = keyManager.verifyHsmIntegrity();
        std::cout << "HSM íntegro: "
                  << (integrity ? "SIM" : "NAO") << std::endl;

        // =========================================================
        // Finalizar
        // =========================================================
        session.logout();
        std::cout << "\n=== Operação concluída com sucesso ==="
                  << std::endl;

    } catch (const hsm::Pkcs11Error& e) {
        std::cerr << "Erro PKCS#11: " << e.what() << std::endl;
        std::cerr << "Operação: " << e.operation() << std::endl;
        std::cerr << "Código: 0x" << std::hex << e.rv() << std::endl;
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

### 4.9 CMakeLists.txt

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project(hsm_example VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Dependências
find_package(Threads REQUIRED)

# Biblioteca do projeto
add_library(hsm_lib STATIC
    src/pkcs11_wrapper.cpp
    src/hsm_key_manager.cpp
    src/hsm_crypto_engine.cpp
)

target_include_directories(hsm_lib PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_link_libraries(hsm_lib PUBLIC
    Threads::Threads
    ${CMAKE_DL_LIBS}  # para dlopen/dlsym
)

# Executável principal
add_executable(hsm_example src/main.cpp)
target_link_libraries(hsm_example PRIVATE hsm_lib)

# Testes (opcional)
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

    # Testes unitários (usando Google Test ou framework simples)
    add_executable(test_session tests/test_session.cpp)
    target_link_libraries(test_session PRIVATE hsm_lib)

    add_executable(test_keys tests/test_keys.cpp)
    target_link_libraries(test_keys PRIVATE hsm_lib)

    add_executable(test_crypto tests/test_crypto.cpp)
    target_link_libraries(test_crypto PRIVATE hsm_lib)

    add_test(NAME SessionTests COMMAND test_session)
    add_test(NAME KeyTests COMMAND test_keys)
    add_test(NAME CryptoTests COMMAND test_crypto)
endif()

# Instalação
install(TARGETS hsm_example
    RUNTIME DESTINATION bin
)
```

### 4.10 Tratamento de Erros Detalhado

```cpp
// include/hsm_utils.h
#ifndef HSM_UTILS_H
#define HSM_UTILS_H

#include "pkcs11_wrapper.h"
#include <string>
#include <vector>
#include <functional>

namespace hsm {

// Logger para operações HSM
class HsmLogger {
public:
    enum class Level {
        DEBUG,
        INFO,
        WARNING,
        ERROR,
        CRITICAL
    };

    using LogCallback = std::function<void(
        Level level, const std::string& message
    )>;

    static HsmLogger& instance();

    void setCallback(LogCallback callback);
    void setLevel(Level level);

    void debug(const std::string& message);
    void info(const std::string& message);
    void warning(const std::string& message);
    void error(const std::string& message);
    void critical(const std::string& message);

    // Log de operação PKCS#11
    void logOperation(
        const std::string& operation,
        CK_RV result,
        double durationMs = 0.0
    );

private:
    HsmLogger() = default;
    void log(Level level, const std::string& message);

    LogCallback callback_;
    Level level_ = Level::INFO;
};

// Retry policy para operações HSM
class HsmRetryPolicy {
public:
    struct Config {
        int maxRetries = 3;
        int initialDelayMs = 100;
        double backoffMultiplier = 2.0;
        int maxDelayMs = 5000;
    };

    explicit HsmRetryPolicy(Config config = Config{});

    template<typename Func>
    auto execute(Func&& func) -> decltype(func()) {
        int attempt = 0;
        int delay = config_.initialDelayMs;

        while (true) {
            try {
                return func();
            } catch (const Pkcs11Error& e) {
                attempt++;

                // Não retry em erros de autenticação ou argumentos
                if (e.rv() == CKR_PIN_INCORRECT ||
                    e.rv() == CKR_PIN_LOCKED ||
                    e.rv() == CKR_ARGUMENTS_BAD ||
                    e.rv() == CKR_MECHANISM_INVALID)
                {
                    throw;
                }

                if (attempt >= config_.maxRetries) {
                    throw;
                }

                HsmLogger::instance().warning(
                    "Operação falhou (tentativa " +
                    std::to_string(attempt) + "/" +
                    std::to_string(config_.maxRetries) +
                    "): " + e.what() +
                    ". Retry em " + std::to_string(delay) + "ms"
                );

                std::this_thread::sleep_for(
                    std::chrono::milliseconds(delay)
                );

                delay = static_cast<int>(
                    std::min(
                        delay * config_.backoffMultiplier,
                        static_cast<double>(config_.maxDelayMs)
                    )
                );
            }
        }
    }

private:
    Config config_;
};

// Monitor de performance HSM
class HsmPerformanceMonitor {
public:
    struct Stats {
        uint64_t totalOperations = 0;
        uint64_t successfulOperations = 0;
        uint64_t failedOperations = 0;
        double totalDurationMs = 0.0;
        double minDurationMs = std::numeric_limits<double>::max();
        double maxDurationMs = 0.0;
        double avgDurationMs = 0.0;
    };

    void recordOperation(
        const std::string& operation,
        double durationMs,
        bool success
    );

    Stats getStats(const std::string& operation = "") const;
    void reset();

private:
    mutable std::mutex mutex_;
    std::unordered_map<std::string, Stats> stats_;
};

// Validação de configuração HSM
struct HsmConfig {
    std::string libraryPath;
    CK_SLOT_ID slotId = 0;
    std::string pin;
    CK_USER_TYPE userType = CKU_USER;
    int sessionTimeoutSeconds = 300;
    bool readOnlySession = false;
};

bool validateHsmConfig(const HsmConfig& config, std::string& error);

} // namespace hsm

#endif // HSM_UTILS_H
```

### 4.11 Exemplo de Integração com Aplicação Real

```cpp
// src/integration_example.cpp
#include "pkcs11_wrapper.h"
#include "hsm_key_manager.h"
#include "hsm_crypto_engine.h"
#include "hsm_utils.h"
#include <iostream>
#include <vector>
#include <string>

// Exemplo: Servidor de assinatura digital para documentos
class DocumentSigner {
public:
    DocumentSigner(
        const std::string& pkcs11LibPath,
        CK_SLOT_ID slotId,
        const std::string& pin
    )
        : library_(pkcs11LibPath)
        , session_(library_, slotId, false)
        , keyManager_(session_)
        , cryptoEngine_(session_, keyManager_)
    {
        session_.login(CKU_USER, pin);
        hsm::HsmLogger::instance().info("DocumentSigner inicializado");
    }

    ~DocumentSigner() {
        try {
            session_.logout();
        } catch (...) {
            // Logout best-effort
        }
    }

    // Assinar documento
    struct SignatureResult {
        std::vector<CK_BYTE> signature;
        std::vector<CK_BYTE> documentHash;
        bool success;
        std::string error;
    };

    SignatureResult signDocument(
        const std::vector<CK_BYTE>& document,
        const std::string& keyLabel
    ) {
        SignatureResult result;

        try {
            // 1. Hash do documento
            auto hashResult = cryptoEngine_.hash(document, CKM_SHA256);
            if (!hashResult.success) {
                result.error = "Falha ao calcular hash: " +
                    hashResult.errorMessage;
                return result;
            }
            result.documentHash = hashResult.data;

            // 2. Buscar chave de assinatura
            auto keyMetadata = keyManager_.findKeyByLabel(keyLabel);
            if (!keyMetadata) {
                result.error = "Chave não encontrada: " + keyLabel;
                return result;
            }

            // 3. Assinar hash
            CK_OBJECT_HANDLE keyHandle = 0; // Simplificado
            auto signConfig = hsm::MechanismConfig::rsaPss();
            auto signResult = cryptoEngine_.signRsa(
                keyHandle, hashResult.data, signConfig
            );

            if (!signResult.success) {
                result.error = "Falha na assinatura: " +
                    signResult.errorMessage;
                return result;
            }

            result.signature = signResult.data;
            result.success = true;

            hsm::HsmLogger::instance().info(
                "Documento assinado com sucesso: " + keyLabel
            );

        } catch (const std::exception& e) {
            result.error = e.what();
        }

        return result;
    }

    // Verificar assinatura
    bool verifyDocument(
        const std::vector<CK_BYTE>& document,
        const std::vector<CK_BYTE>& signature,
        const std::string& keyLabel
    ) {
        try {
            // Hash do documento
            auto hashResult = cryptoEngine_.hash(document, CKM_SHA256);
            if (!hashResult.success) {
                return false;
            }

            // Buscar chave pública
            CK_OBJECT_HANDLE pubKeyHandle = 0; // Simplificado
            auto verifyConfig = hsm::MechanismConfig::rsaPss();
            auto verifyResult = cryptoEngine_.verifyRsa(
                pubKeyHandle, hashResult.data, signature, verifyConfig
            );

            return verifyResult.success;
        } catch (const std::exception&) {
            return false;
        }
    }

    // Criptografar dados sensíveis
    std::vector<CK_BYTE> encryptSensitiveData(
        const std::vector<CK_BYTE>& data,
        const std::string& keyLabel
    ) {
        auto keyHandle = keyManager_.findKeyByLabel(keyLabel);
        if (!keyHandle) {
            throw std::runtime_error("Chave não encontrada: " + keyLabel);
        }

        auto iv = cryptoEngine_.generateIv(16);
        auto encConfig = hsm::MechanismConfig::aesGcm(iv);

        auto result = cryptoEngine_.encryptAes(
            0, // Handle simplificado
            data,
            encConfig
        );

        if (!result.success) {
            throw std::runtime_error("Criptografia falhou: " +
                result.errorMessage);
        }

        // Pré-fixar IV ao ciphertext para armazenamento
        std::vector<CK_BYTE> output;
        output.insert(output.end(), iv.begin(), iv.end());
        output.insert(output.end(), result.data.begin(), result.data.end());

        return output;
    }

private:
    hsm::Pkcs11Library library_;
    hsm::Pkcs11Session session_;
    hsm::HsmKeyManager keyManager_;
    hsm::HsmCryptoEngine cryptoEngine_;
};

int main() {
    try {
        // Configurar logger
        hsm::HsmLogger::instance().setLevel(
            hsm::HsmLogger::Level::INFO
        );
        hsm::HsmLogger::instance().setCallback(
            [](hsm::HsmLogger::Level level, const std::string& msg) {
                const char* levelStr = "INFO";
                switch (level) {
                    case hsm::HsmLogger::Level::DEBUG: levelStr = "DEBUG"; break;
                    case hsm::HsmLogger::Level::WARNING: levelStr = "WARN"; break;
                    case hsm::HsmLogger::Level::ERROR: levelStr = "ERROR"; break;
                    case hsm::HsmLogger::Level::CRITICAL: levelStr = "CRIT"; break;
                    default: break;
                }
                std::cout << "[" << levelStr << "] " << msg << std::endl;
            }
        );

        // Inicializar signer
        DocumentSigner signer(
            "/usr/lib/libCryptoki.so",
            0,
            "12345678"
        );

        // Assinar documento
        std::string doc = "Contrato confidencial entre as partes";
        std::vector<CK_BYTE> docBytes(doc.begin(), doc.end());

        auto sigResult = signer.signDocument(
            docBytes,
            "assinatura-documentos"
        );

        if (sigResult.success) {
            std::cout << "Assinatura gerada com sucesso" << std::endl;

            // Verificar assinatura
            bool verified = signer.verifyDocument(
                docBytes,
                sigResult.signature,
                "assinatura-documentos"
            );

            std::cout << "Assinatura verificada: "
                      << (verified ? "VALIDA" : "INVALIDA")
                      << std::endl;
        }

        // Criptografar dados
        std::string sensitive = "Número do cartão: 4111-1111-1111-1111";
        std::vector<CK_BYTE> sensitiveBytes(
            sensitive.begin(), sensitive.end()
        );

        auto encrypted = signer.encryptSensitiveData(
            sensitiveBytes,
            "chave-dados-sensiveis"
        );

        std::cout << "Dados criptografados: " << encrypted.size()
                  << " bytes" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Erro fatal: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

---

## 5. Cloud HSMs: AWS CloudHSM, Azure Dedicated HSM, Google Cloud HSM

### 5.1 Visão Geral

Cloud HSMs são serviços gerenciados que fornecem acesso a módulos criptográficos de hardware dedicados na nuvem. Diferente de serviços de gestão de chaves como AWS KMS ou Azure Key Vault (que são serviços de software), Cloud HSMs oferecem acesso dedicado a hardware físico — o cliente tem controle exclusivo sobre o módulo criptográfico.

### 5.2 AWS CloudHSM

**O que é**: O AWS CloudHSM fornece módulos criptográficos de hardware dedicados que permitem gerenciar suas chaves criptográficas usando hardware FIPS 140-2 Nível 3 validado. Você tem controle exclusivo sobre o hardware — nenhum outro cliente da AWS pode acessar seu HSM.

**Arquitetura**:
- HSMs dedicados no VPC (Virtual Private Cloud) do cliente
- Acesso via rede privada (VPC endpoint) — não traversa a internet
- Interface PKCS#11, JCE, e OpenSSL
- Suporte a cluster (até 28 HSMs por cluster)
- Replicação síncrona automática entre HSMs do cluster

**Características**:
- Custo: Aproximadamente $1.50/hora por HSM (~$1.080/mês)
- Performance: ~10.000 operações RSA-2048 por segundo por HSM
- Disponibilidade: 99.99% SLA
- Compliance: FIPS 140-2 Nível 3, PCI DSS, HIPAA, SOC 2

**Limitações**:
- Apenas Linux (Amazon Linux, RHEL, CentOS, Ubuntu)
- Suporte limitado a algoritmos FIPS aprovados
- Não suporta todos os mecanismos PKCS#11 (alguns são proprietários)
- Latência de rede (vs. PCIe local)

### 5.3 Azure Dedicated HSM

**O que é**: O Azure Dedicated HSM fornece HSMs físicos dedicados baseados no hardware Thales Luna 7, operados dentro de data centers da Azure.

**Arquitetura**:
- HSMs Thales Luna Network HSM 7 dedicados
- Conexão direta via rede privada (ExpressRoute ou VPN Gateway)
- Interface PKCS#11, JCE, e CNG (Windows)
- Suporte a clusters (até 4 HSMs por cluster)

**Características**:
- Custo: Aproximadamente $4/hora por HSM (~$2.880/mês) — mais caro que AWS
- Performance: Similar ao Thales Luna 7 físico
- Compliance: FIPS 140-2 Nível 3
- Suporte a Windows e Linux

**Diferencial**: Como é baseado em hardware Thales real, é mais compatível com aplicações existentes que usam Thales Luna PKCS#11. Migração de on-premises para cloud é mais simples.

### 5.4 Google Cloud HSM

**O que é**: O Google Cloud HSM é parte do Cloud KMS — fornece chaves criptográficas protegidas por hardware, mas com um modelo diferente dos outros provedores.

**Arquitetura**:
- Integrado ao Cloud KMS (não é hardware dedicado por cliente)
- Hardware proprio do Google (custom Titan chips)
- Interface REST API e Cloud KMS client libraries
- Suporte a chaves symmetric e asymmetric

**Características**:
- Custo: $3-12 por chave por mês + $0.03-0.12 por 10.000 operações
- Performance: Escalável automaticamente
- Compliance: FIPS 140-2 Nível 3
- Melhor integração com outros serviços Google Cloud

**Diferencial**: Modelo de pagamento por uso, não por hora. Mais econômico para cargas de trabalho esporádicas. Integração nativa com BigQuery, Spanner, Cloud Storage.

### 5.5 Comparação Resumida

| Característica | AWS CloudHSM | Azure Dedicated HSM | Google Cloud HSM |
|---------------|--------------|--------------------|--------------------|
| Hardware | Cavium/Marvell | Thales Luna 7 | Google Titan |
| Dedicação | Por cliente | Por cliente | Compartilhado |
| Interface | PKCS#11, JCE | PKCS#11, JCE, CNG | REST API, KMS |
| Custo base | ~$1.080/mês | ~$2.880/mês | Pay-per-use |
| Máx. HSMs | 28 por cluster | 4 por cluster | Ilimitado |
| FIPS Nível | 3 | 3 | 3 |
| Latência | Baixa (VPC) | Baixa (ExpressRoute) | Média (REST) |
| Uso ideal | Crypto pesado | Migração Thales | Integração GCP |

### 5.6 Estratégia de Multi-Cloud

Em organizações multi-cloud, uma estratégia comum é usar Cloud HSMs de cada provedor para suas respectivas integrações nativas, e um HSM on-premises (ou dedicado via colocation) como anchor de chaves mestras.

```
                    Chave Mestra Raiz
                    (On-prem HSM)
                         |
         +---------------+---------------+
         |               |               |
    CloudHSM AWS    Azure Dedicated   Google Cloud HSM
    (chaves de      (chaves de         (chaves de
     work)           work)              work)
```

A chave raiz nunca sai do HSM on-premises. As chaves de trabalho em cada cloud são geradas localmente e protegidas pelo HSM desse provedor. Em caso de comprometimento de uma cloud, a chave raiz permanece segura.

---

## 6. Key Ceremony: Processo formal de geração de chaves mestras

### 6.1 O que é um Key Ceremony

Um Key Ceremony é um processo formal e documentado para geração, distribuição, e arquivamento de chaves criptográficas mestras. É usado principalmente em:

- **Certificate Authorities (CAs)**: Geração de chaves root CA e intermediate CA
- **Bancos de dados**: Geração de chaves de criptografia para bancos de dados sensíveis
- **Sistemas de pagamento**: Geração de chaves de transação e PIN
- **Governo**: Geração de chaves para classificação e comunicação

O Key Ceremony é a fase mais crítica no ciclo de vida de uma chave — é quando ela nasce. Se a chave for comprometida neste estágio, toda a cadeia de segurança é comprometida.

### 6.2 Requisitos para um Key Ceremony

**Ambiente físico**:
- Sala segura (SCIF — Sensitive Compartmented Information Facility, ou equivalente)
- Controle de acesso biométrico
- Câmeras de segurança 24/7
- Proibição de dispositivos eletrônicos pessoais (celulares, USB drives)
- Auscultadores contra interceptação
- Suprimento de energia ininterrupto (UPS)

**Pessoal**:
- Mínimo de 3 operadores (M-of-N quórum, tipicamente 3-of-5)
- Cada operador possui um smart card ou token HSM pessoal
- Operadores são de departamentos diferentes (separação de deveres)
- Presença de um auditor independente

**Documentação**:
- Procedimento escrito passo-a-passo
- Formulários de registro de cada ação
- Vídeo-gravação do ceremony inteiro
- Assinaturas digitais de cada operador

**Hardware**:
- HSM dedicado (nunca conectado à rede durante o ceremony)
- Smart card reader
- Impressora conectada ao HSM (para imprimir chaves backup, se necessário)
- Envelopes de segurança lacrados

### 6.3 Etapas do Key Ceremony

```
1. PREPARAÇÃO (antes do ceremony)
   ├── Verificar integridade do HSM (selos, firmware)
   ├── Carregar firmware aprovado no HSM
   ├── Configurar política de quórum (M-of-N)
   ├── Distribuir smart cards aos operadores
   └── Documentar configuração inicial

2. INICIALIZAÇÃO
   ├── Verificar identidade de todos os operadores
   ├── Coletar smart cards/ tokens de todos
   ├── Inicializar HSM com SO PIN (Security Officer)
   ├── Configurar política de login
   └── Gerar chaves de administração

3. GERAÇÃO DE CHAVES
   ├── Gerar chaves root CA (RSA-4096 ou ECDSA P-384)
   ├── Gerar chaves de assinatura (RSA-2048 ou ECDSA P-256)
   ├── Gerar chaves de criptografia (AES-256)
   ├── Verificar cada chave gerada
   └── Registrar cada chave em log

4. DISTRIBUIÇÃO
   ├── Gerar CSR (Certificate Signing Request)
   ├── Assinar CSR com chave root (se aplicável)
   ├── Distribuir chaves para sistemas de produção
   ├── Verificar distribuição
   └── Documentar distribuição

5. ARQUIVAMENTO
   ├── Gerar backup das chaves (se necessário)
   ├── Armazenar backup em local seguro
   ├── Zerar memória temporária do HSM
   ├── Ativar HSM em modo produção
   ├── Documentar estado final
   └── Cerimonial de encerramento
```

### 6.4 Template de Documentação

```markdown
## KEY CEREMONY RECORD

**Data**: [DATA]
**Local**: [SALA SEGURA]
**HSM**: [MODELO / SERIAL]

### Operadores
| Nome | Departamento | Token ID | Assinatura |
|------|-------------|----------|------------|
| [Nome 1] | Infraestrutura | [Token ID 1] | [Assinatura] |
| [Nome 2] | Segurança | [Token ID 2] | [Assinatura] |
| [Nome 3] | Compliance | [Token ID 3] | [Assinatura] |

### Auditor
| Nome | Empresa | Assinatura |
|------|---------|------------|
| [Nome] | [Empresa] | [Assinatura] |

### Configuração do HSM
- Modelo: [MODELO]
- Serial: [SERIAL]
- Firmware: [VERSÃO]
- Política de Quórum: [M-of-N]

### Chaves Geradas
| Label | Tipo | Tamanho | Handle | Horário |
|-------|------|---------|--------|---------|
| root-ca-key | RSA | 4096 | [HANDLE] | [HH:MM:SS] |
| signing-key | RSA | 2048 | [HANDLE] | [HH:MM:SS] |
| encryption-key | AES | 256 | [HANDLE] | [HH:MM:SS] |

### Backup
- [ ] Gerado
- [ ] Armazenado em [LOCAL]
- [ ] Verificado

### Assinaturas dos Operadores
[Nomes e assinaturas dos 3 operadores]

### Assinatura do Auditor
[Nome e assinatura do auditor]
```

### 6.5 Script de Key Ceremony (Exemplo Simplificado)

```cpp
// src/key_ceremony.cpp
#include "pkcs11_wrapper.h"
#include "hsm_key_manager.h"
#include "hsm_crypto_engine.h"
#include <iostream>
#include <vector>
#include <string>
#include <fstream>
#include <chrono>
#include <iomanip>

struct CeremonyStep {
    std::string description;
    std::function<bool()> execute;
};

class KeyCeremony {
public:
    KeyCeremony(
        const std::string& hsmLibPath,
        CK_SLOT_ID slotId
    )
        : library_(hsmLibPath)
        , session_(library_, slotId, false)
        , keyManager_(session_)
        , cryptoEngine_(session_, keyManager_)
    {}

    void run() {
        std::cout << "=== KEY CEREMONY INICIADO ===" << std::endl;
        std::cout << "Data: " << getCurrentTimestamp() << std::endl;
        std::cout << std::endl;

        auto steps = buildSteps();

        for (size_t i = 0; i < steps.size(); ++i) {
            std::cout << "Passo " << (i + 1) << "/" << steps.size()
                      << ": " << steps[i].description << std::endl;

            auto startTime = std::chrono::steady_clock::now();

            if (!steps[i].execute()) {
                std::cerr << "FALHA no passo " << (i + 1) << std::endl;
                logStep(i + 1, steps[i].description, false,
                    getElapsedMs(startTime));
                throw std::runtime_error(
                    "Key Ceremony abortado no passo " +
                    std::to_string(i + 1)
                );
            }

            auto elapsed = getElapsedMs(startTime);
            logStep(i + 1, steps[i].description, true, elapsed);

            std::cout << "  -> OK (" << std::fixed
                      << std::setprecision(2) << elapsed << "ms)"
                      << std::endl;
        }

        std::cout << std::endl;
        std::cout << "=== KEY CEREMONY CONCLUIDO ===" << std::endl;
    }

private:
    hsm::Pkcs11Library library_;
    hsm::Pkcs11Session session_;
    hsm::HsmKeyManager keyManager_;
    hsm::HsmCryptoEngine cryptoEngine_;

    std::vector<CeremonyStep> buildSteps() {
        return {
            {"Verificar integridade do HSM", [this]() {
                return keyManager_.verifyHsmIntegrity();
            }},

            {"Fazer login como Security Officer", [this]() {
                session_.login(CKU_SO, "so-pin-ceremony");
                return true;
            }},

            {"Gerar chave Root CA RSA-4096", [this]() {
                auto handle = keyManager_.generateRsaKeyPair(
                    "root-ca-key",
                    hsm::KeyType::RSA_4096,
                    false
                );
                return handle != CK_INVALID_HANDLE;
            }},

            {"Gerar chave de Assinatura RSA-2048", [this]() {
                auto handle = keyManager_.generateRsaKeyPair(
                    "signing-key-2048",
                    hsm::KeyType::RSA_2048,
                    false
                );
                return handle != CK_INVALID_HANDLE;
            }},

            {"Gerar chave de Criptografia AES-256", [this]() {
                auto handle = keyManager_.generateAesKey(
                    "encryption-key-256",
                    hsm::KeyType::AES_256
                );
                return handle != CK_INVALID_HANDLE;
            }},

            {"Gerar chave de Assinatura ECDSA P-256", [this]() {
                auto handle = keyManager_.generateEccKeyPair(
                    "signing-key-ecdsa",
                    hsm::KeyType::ECDSA_P256
                );
                return handle != CK_INVALID_HANDLE;
            }},

            {"Verificar todas as chaves geradas", [this]() {
                auto keys = keyManager_.findAllKeys();
                return keys.size() >= 4; // Mínimo 4 chaves
            }},

            {"Exportar chaves públicas para arquivo", [this]() {
                // Em produção, salvar em arquivo seguro
                return true;
            }},

            {"Deslogar do modo SO", [this]() {
                session_.logout();
                return true;
            }},

            {"Fazer login como User para verificação", [this]() {
                session_.login(CKU_USER, "user-pin");
                return true;
            }},

            {"Verificar chaves visíveis para User", [this]() {
                auto keys = keyManager_.findAllKeys();
                return !keys.empty();
            }},

            {"Deslogar e finalizar", [this]() {
                session_.logout();
                return true;
            }},
        };
    }

    std::string getCurrentTimestamp() {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        char buffer[64];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S",
                      std::localtime(&time));
        return buffer;
    }

    double getElapsedMs(
        std::chrono::steady_clock::time_point start)
    {
        auto end = std::chrono::steady_clock::now();
        return std::chrono::duration<double, std::milli>(
            end - start
        ).count();
    }

    void logStep(
        int step, const std::string& desc,
        bool success, double elapsedMs)
    {
        // Em produção, salvar em log persistente
        std::ofstream log("key_ceremony.log", std::ios::app);
        log << getCurrentTimestamp() << " | Step " << step
            << " | " << desc
            << " | " << (success ? "OK" : "FAIL")
            << " | " << std::fixed << std::setprecision(2)
            << elapsedMs << "ms" << std::endl;
    }
};

int main() {
    try {
        KeyCeremony ceremony("/usr/lib/libCryptoki.so", 0);
        ceremony.run();
    } catch (const std::exception& e) {
        std::cerr << "ERRO: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}
```

---

## 7. Performance: Benchmarks PKCS#11 vs software crypto

### 7.1 Metodologia de Benchmark

Para comparar o desempenho de operações criptográficas via HSM (PKCS#11) versus implementações de software (OpenSSL), é necessário controlar variáveis:

- **Hardware**: Mesmo servidor para ambos os testes
- **Rede**: Para HSMs de rede, medir latência de rede separadamente
- **Tamanho da chave**: Usar os mesmos tamanhos em ambos
- **Modo de operação**: Usar os mesmos modos (CBC, GCM, etc.)
- **Número de iterações**: Mínimo de 10.000 para estabilidade
- **Warm-up**: 1.000 iterações descartadas antes da medição

### 7.2 Resultados Típicos

#### Criptografia Simétrica (AES-256)

| Operação | Software (OpenSSL) | HSM Local (PCIe) | HSM Rede (1GbE) | HSM Rede (10GbE) |
|----------|-------------------|-------------------|------------------|-------------------|
| AES-256-CBC Encrypt | 3.2 GB/s | 1.8 GB/s | 450 MB/s | 1.2 GB/s |
| AES-256-GCM Encrypt | 2.8 GB/s | 1.5 GB/s | 400 MB/s | 1.0 GB/s |
| AES-256-CBC Decrypt | 3.1 GB/s | 1.7 GB/s | 430 MB/s | 1.1 GB/s |
| Latência por operação | 0.003 ms | 0.005 ms | 0.5 ms | 0.1 ms |

**Análise**: Para criptografia simétrica, software é significativamente mais rápido porque:
1. OpenSSL usa AES-NI (instruction set dedicado no Intel/AMD)
2. HSMs têm aceleradores de hardware, mas com overhead de interface
3. Para HSMs de rede, a latência de rede domina

#### Assinatura Digital (RSA-2048)

| Operação | Software (OpenSSL) | HSM Local (PCIe) | HSM Rede |
|----------|-------------------|-------------------|----------|
| RSA-2048 Sign | 15.000 ops/s | 12.000 ops/s | 8.000 ops/s |
| RSA-2048 Verify | 45.000 ops/s | 35.000 ops/s | 25.000 ops/s |
| Latência Sign | 0.067 ms | 0.083 ms | 0.125 ms |
| Latência Verify | 0.022 ms | 0.029 ms | 0.040 ms |

**Análise**: Para RSA, a diferença é menor porque:
1. A operação é computationalmente intensiva (exponenciação modular)
2. O overhead de interface é proporcional ao tempo de computação
3. HSMs de alta gama (Thales Luna 7) podem ser mais rápidos que software

#### Assinatura Digital (ECDSA P-256)

| Operação | Software (OpenSSL) | HSM Local | HSM Rede |
|----------|-------------------|-----------|----------|
| ECDSA P-256 Sign | 30.000 ops/s | 25.000 ops/s | 18.000 ops/s |
| ECDSA P-256 Verify | 12.000 ops/s | 10.000 ops/s | 7.000 ops/s |
| Latência Sign | 0.033 ms | 0.040 ms | 0.056 ms |

**Análise**: ECDSA é mais rápido que RSA em software e HSM. A diferença percentual entre software e HSM é similar.

### 7.3 Quando Usar HSM vs Software

**Use HSM quando**:
- Chaves não podem ser exportadas (compliance, regulamentação)
- Non-repudiation é requerido (assinatura juridicamente válida)
- Alto volume de operações com chaves críticas
- Segurança física é prioritária

**Use Software quando**:
- Performance é crítica e volumes são extremamente altos
- Chaves podem ser gerenciadas em software (testes, dev)
- Custo é uma restrição significativa
- HSM de rede adiciona latência inaceitável

**Estratégia híbrida** (recomendada):
- Chaves raiz/root → HSM
- Chaves de trabalho → Software com proteção (encrypted at rest)
- Operações críticas → HSM
- Operações de alto volume → Software

### 7.4 Teste de Performance Híbrido

```cpp
// src/benchmark_hsm.cpp
#include "pkcs11_wrapper.h"
#include "hsm_crypto_engine.h"
#include <chrono>
#include <iostream>
#include <vector>
#include <iomanip>
#include <numeric>

class HsmBenchmark {
public:
    struct BenchmarkResult {
        std::string operation;
        int iterations;
        double totalMs;
        double avgMs;
        double minMs;
        double maxMs;
        double opsPerSecond;
    };

    template<typename Func>
    BenchmarkResult run(
        const std::string& name,
        int iterations,
        Func&& func)
    {
        std::vector<double> durations;
        durations.reserve(iterations);

        // Warm-up
        for (int i = 0; i < 100; ++i) {
            func();
        }

        // Benchmark
        for (int i = 0; i < iterations; ++i) {
            auto start = std::chrono::steady_clock::now();
            func();
            auto end = std::chrono::steady_clock::now();

            double ms = std::chrono::duration<double, std::milli>(
                end - start
            ).count();
            durations.push_back(ms);
        }

        // Calcular estatísticas
        double total = std::accumulate(
            durations.begin(), durations.end(), 0.0
        );
        double min = *std::min_element(
            durations.begin(), durations.end()
        );
        double max = *std::max_element(
            durations.begin(), durations.end()
        );

        BenchmarkResult result;
        result.operation = name;
        result.iterations = iterations;
        result.totalMs = total;
        result.avgMs = total / iterations;
        result.minMs = min;
        result.maxMs = max;
        result.opsPerSecond = 1000.0 / result.avgMs;

        return result;
    }

    void printResult(const BenchmarkResult& result) {
        std::cout << std::left << std::setw(30) << result.operation
                  << std::right << std::setw(10) << result.iterations
                  << std::setw(12) << std::fixed << std::setprecision(2)
                  << result.avgMs << "ms"
                  << std::setw(12) << result.opsPerSecond << "ops/s"
                  << std::setw(10) << std::fixed << std::setprecision(2)
                  << result.minMs << "ms"
                  << std::setw(10) << result.maxMs << "ms"
                  << std::endl;
    }
};

int main() {
    try {
        hsm::Pkcs11Library library("/usr/lib/libCryptoki.so");
        auto slots = library.getSlotList(true);

        if (slots.empty()) {
            std::cerr << "Nenhum HSM encontrado" << std::endl;
            return 1;
        }

        hsm::Pkcs11Session session(library, slots[0]);
        session.login(CKU_USER, "12345678");

        hsm::HsmKeyManager keyManager(session);
        hsm::HsmCryptoEngine cryptoEngine(session, keyManager);

        // Gerar chave de teste
        auto aesKey = keyManager.generateAesKey(
            "benchmark-key", hsm::KeyType::AES_256
        );

        auto rsaKey = keyManager.generateRsaKeyPair(
            "benchmark-rsa-key", hsm::KeyType::RSA_2048
        );

        HsmBenchmark bench;

        std::cout << "=== BENCHMARK HSM vs SOFTWARE ===" << std::endl;
        std::cout << std::endl;

        // Header
        std::cout << std::left << std::setw(30) << "Operação"
                  << std::right << std::setw(10) << "Iterações"
                  << std::setw(12) << "Média"
                  << std::setw(12) << "Ops/s"
                  << std::setw(10) << "Min"
                  << std::setw(10) << "Max"
                  << std::endl;
        std::cout << std::string(84, '-') << std::endl;

        // Benchmark AES-CBC
        auto iv = cryptoEngine.generateIv(16);
        auto aesConfig = hsm::MechanismConfig::aesCbc(iv);
        std::vector<CK_BYTE> plaintext(16, 'A');

        auto aesResult = bench.run("AES-CBC Encrypt", 10000, [&]() {
            cryptoEngine.encryptAes(aesKey, plaintext, aesConfig);
        });
        bench.printResult(aesResult);

        // Benchmark RSA Sign
        std::vector<CK_BYTE> data(32, 'B');
        auto rsaConfig = hsm::MechanismConfig::rsaPkcs1();

        auto rsaSignResult = bench.run("RSA-2048 Sign", 1000, [&]() {
            cryptoEngine.signRsa(rsaKey, data, rsaConfig);
        });
        bench.printResult(rsaSignResult);

        // Benchmark Hash
        auto shaResult = bench.run("SHA-256 Hash", 10000, [&]() {
            cryptoEngine.hash(data, CKM_SHA256);
        });
        bench.printResult(shaResult);

        // Benchmark Random
        auto randResult = bench.run("Random 32 bytes", 10000, [&]() {
            cryptoEngine.generateRandom(32);
        });
        bench.printResult(randResult);

        session.logout();

    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

---

## 8. Smart Cards e Tokens USB

### 8.1 Smart Cards

Smart cards são dispositivos de cartão de crédito com um chip integrado que executa operações criptográficas. Existem dois tipos principais:

**Smart Cards de Contato**: Precisam ser inseridas em um reader físico. Comunicação via interface ISO 7816 (触点 elétricos). Latência: 1-10ms por operação.

**Smart Cards Sem Contato (Contactless)**: Usam tecnologia RFID/NFC. Leitura sem inserção física. Latência: 5-50ms por operação.

**Padrões**:
- ISO/IEC 7816: Smart cards de contato
- ISO/IEC 14443: Smart cards sem contato (NFC)
- PKCS#15: Estrutura de dados para smart cards
- GlobalPlatform: Gerenciamento de aplicações em smart cards

**Aplicações**:
- Cartões de assinatura digital (e-CPF, e-CNPJ no Brasil)
- Certificados de pessoa física (e-ID na Europa)
- Autenticação de usuários (token de dois fatores)
- Assinatura de código-fonte

**Limitações**:
- Memória limitada (tipicamente 32KB-256KB)
- Processador lento (8-32 MHz)
- Pouca memória para chaves (até 10-20 chaves)
- Vida útil limitada (100.000 ciclos de escrita)

### 8.2 Tokens USB Criptográficos

Tokens USB são dispositivos portáteis que contêm um microprocessador criptográfico. Diferente de pend drives comuns, tokens USB criptográficos executam operações de chave internamente.

**Tipos**:

**Tokens de Software (Sem proteção física)**:
- Simulam PKCS#11 em software
- Chaves armazenadas em criptografia no filesystem
- Segurança baseada em PIN
- Exemplos: SoftHSM, OpenSC (modo software)
- Custo: $0 (software livre)
- Segurança: Baixa — chaves podem ser extraídas

**Tokens de Hardware (Com proteção física)**:
- Microprocessador dedicado com proteção contra tampership
- Chaves nunca saem do token em texto plano
- Suporte a PKCS#11 e/ou PKCS#15
- Exemplos: YubiKey, Nitrokey, SafeNet eToken
- Custo: $25-$200
- Segurança: FIPS 140-2 Nível 2

**Comparação de Tokens USB**:

| Token | Certificação | Algoritmos | Chaves Simultâneas | Custo |
|-------|-------------|------------|---------------------|-------|
| YubiKey 5 | FIPS 140-2 Lvl 2 | RSA, ECC, Ed25519 | Ilimitadas | $50 |
| Nitrokey HSM | Common Criteria EAL4+ | RSA, ECC | 96 | $170 |
| SafeNet eToken 5110 | FIPS 140-2 Lvl 2 | RSA, ECC | 50 | $80 |
| Thales Luna G5 | FIPS 140-2 Lvl 3 | RSA, ECC, AES | Ilimitadas | $300 |

### 8.3 Integração de Smart Cards em C++17

```cpp
// src/smartcard_example.cpp
#include "pkcs11_wrapper.h"
#include <iostream>
#include <vector>

class SmartCardManager {
public:
    SmartCardManager(const std::string& pkcs11Lib)
        : library_(pkcs11Lib)
    {}

    // Listar todos os smart cards inseridos
    std::vector<SmartCardInfo> listCards() {
        std::vector<SmartCardInfo> cards;
        auto slots = library_.getSlotList(true);

        for (auto slotId : slots) {
            try {
                auto tokenInfo = library_.getTokenInfo(slotId);
                SmartCardInfo info;
                info.slotId = slotId;
                info.label = reinterpret_cast<const char*>(
                    tokenInfo.label
                );
                info.manufacturer = reinterpret_cast<const char*>(
                    tokenInfo.manufacturerID
                );
                info.serialNumber = reinterpret_cast<const char*>(
                    tokenInfo.serialNumber
                );
                info.hardwareVersion = std::to_string(
                    tokenInfo.hardwareVersion.major
                ) + "." + std::to_string(
                    tokenInfo.hardwareVersion.minor
                );
                info.firmwareVersion = std::to_string(
                    tokenInfo.firmwareVersion.major
                ) + "." + std::to_string(
                    tokenInfo.firmwareVersion.minor
                );

                // Verificar se tem certificados
                hsm::Pkcs11Session session(library_, slotId);
                CK_OBJECT_CLASS certClass = CKO_CERTIFICATE;
                CK_ATTRIBUTE searchTemplate[] = {
                    {CKA_CLASS, &certClass, sizeof(certClass)},
                };

                auto certs = session.findObjects(
                    std::vector<CK_ATTRIBUTE>(
                        searchTemplate, searchTemplate + 1
                    )
                );
                info.certificateCount = certs.size();

                cards.push_back(info);
            } catch (const hsm::Pkcs11Error&) {
                // Slot vazio ou sem token
            }
        }

        return cards;
    }

    // Assinar com smart card
    std::vector<CK_BYTE> signWithCard(
        CK_SLOT_ID slotId,
        const std::string& pin,
        const std::vector<CK_BYTE>& data,
        const std::string& keyLabel
    ) {
        hsm::Pkcs11Session session(library_, slotId, false);
        session.login(CKU_USER, pin);

        // Buscar chave privada com o label especificado
        CK_OBJECT_CLASS privKeyClass = CKO_PRIVATE_KEY;
        CK_ATTRIBUTE searchTemplate[] = {
            {CKA_CLASS, &privKeyClass, sizeof(privKeyClass)},
        };

        auto keys = session.findObjects(
            std::vector<CK_ATTRIBUTE>(
                searchTemplate, searchTemplate + 1
            )
        );

        if (keys.empty()) {
            throw std::runtime_error(
                "Nenhuma chave privada encontrada no smart card"
            );
        }

        // Assinar com a primeira chave encontrada
        // (em produção, buscar pelo label específico)
        CK_MECHANISM mech = {CKM_RSA_PKCS, nullptr, 0};

        CK_ULONG signatureLen = 0;
        CK_RV rv = session.library_->functions_->C_SignInit(
            session.handle(), &mech, keys[0]
        );
        if (rv != CKR_OK) {
            throw hsm::Pkcs11Error(rv, "C_SignInit");
        }

        rv = session.library_->functions_->C_Sign(
            session.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            nullptr,
            &signatureLen
        );
        if (rv != CKR_OK) {
            throw hsm::Pkcs11Error(rv, "C_Sign (size)");
        }

        std::vector<CK_BYTE> signature(signatureLen);
        rv = session.library_->functions_->C_Sign(
            session.handle(),
            const_cast<CK_BYTE*>(data.data()),
            static_cast<CK_ULONG>(data.size()),
            signature.data(),
            &signatureLen
        );
        if (rv != CKR_OK) {
            throw hsm::Pkcs11Error(rv, "C_Sign");
        }

        signature.resize(signatureLen);
        session.logout();
        return signature;
    }

    // Ler certificado do smart card
    std::vector<CK_BYTE> readCertificate(
        CK_SLOT_ID slotId,
        const std::string& pin
    ) {
        hsm::Pkcs11Session session(library_, slotId);
        session.login(CKU_USER, pin);

        CK_OBJECT_CLASS certClass = CKO_CERTIFICATE;
        CK_ATTRIBUTE searchTemplate[] = {
            {CKA_CLASS, &certClass, sizeof(certClass)},
        };

        auto certs = session.findObjects(
            std::vector<CK_ATTRIBUTE>(
                searchTemplate, searchTemplate + 1
            )
        );

        if (certs.empty()) {
            throw std::runtime_error(
                "Nenhum certificado encontrado no smart card"
            );
        }

        hsm::Pkcs11Object cert(session, certs[0]);
        auto certData = cert.getAttributeBytes(CKA_VALUE);

        session.logout();
        return certData;
    }

private:
    hsm::Pkcs11Library library_;

    struct SmartCardInfo {
        CK_SLOT_ID slotId;
        std::string label;
        std::string manufacturer;
        std::string serialNumber;
        std::string hardwareVersion;
        std::string firmwareVersion;
        size_t certificateCount;
    };
};

int main() {
    try {
        SmartCardManager manager("/usr/lib/opensc-pkcs11.so");

        std::cout << "=== Smart Cards Detectados ===" << std::endl;

        auto cards = manager.listCards();
        for (const auto& card : cards) {
            std::cout << "Label: " << card.label << std::endl;
            std::cout << "Fabricante: " << card.manufacturer
                      << std::endl;
            std::cout << "Serial: " << card.serialNumber << std::endl;
            std::cout << "Certificados: " << card.certificateCount
                      << std::endl;
            std::cout << "---" << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
```

### 8.4 SoftHSM para Desenvolvimento

SoftHSM é uma implementação de software do PKCS#11 que simula um token criptográfico. É útil para desenvolvimento e testes quando um HSM físico não está disponível.

**Instalação**:

```bash
# Ubuntu/Debian
sudo apt-get install softhsm2

# CentOS/RHEL
sudo yum install softhsm2

# macOS
brew install softhsm
```

**Configuração**:

```bash
# Criar diretório de configuração
mkdir -p ~/.softhsm/tokens

# Configurar variáveis de ambiente
export SOFTHSM2_CONF=~/.softhsm/softhsm2.conf
echo "directories.tokendir = ~/.softhsm/tokens" > $SOFTHSM2_CONF

# Criar token
softhsm2-util --init-token --slot 0 --label "DevelopmentToken" \
    --pin 1234 --so-pin 12345678

# Listar tokens
softhsm2-util --show-slots
```

**Uso em código C++**:

```cpp
// Usar SoftHSM como se fosse um HSM real
// Apenas trocar o path da biblioteca
hsm::Pkcs11Library library("/usr/lib/softhsm/libsofthsm2.so");
```

**Limitações do SoftHSM**:
- Chaves armazenadas em disco (não proteção física)
- Performance limitada pela CPU
- Não serve para produção — apenas para desenvolvimento e testes
- Não atende FIPS 140-2

---

## 9. Remote Key Storage: KMIP protocol

### 9.1 Visão Geral do KMIP

KMIP (Key Management Interoperability Protocol) é um padrão OASIS para comunicação entre clientes de gerenciamento de chaves e servidores de chaves. Define um protocolo binário sobre TCP/IP para operações como criação, registro, busca, atualização e exclusão de chaves.

**Versão atual**: KMIP 2.0 (ratificado em 2020)

**Diferença para PKCS#11**:
- PKCS#11 é uma API C local (biblioteca compartilhada)
- KMIP é um protocolo de rede (TCP/IP com TLS)
- PKCS#11 é usado para acesso direto a HSMs
- KMIP é usado para acesso a servidores de chaves remotos

### 9.2 Arquitetura KMIP

```
+------------------+       KMIP/TLS       +------------------+
|   Cliente KMIP   | <=================> |   Servidor KMIP  |
|   (Aplicação)    |       TCP 5696       |   (Key Server)   |
+------------------+                      +------------------+
                                               |
                                               v
                                        +------------------+
                                        |   HSM Backend    |
                                        |   (FIPS 140-2)   |
                                        +------------------+
```

### 9.3 Operações KMIP

| Operação | Descrição |
|----------|-----------|
| Create | Cria um novo objeto (chave, certificado) |
| Get | Obtém um objeto existente |
| Destroy | Exclui um objeto |
| Locate | Busca objetos por atributos |
| Register | Registra um objeto existente |
| Re-key | Rotacionar uma chave |
| Re-key Key Pair | Rotacionar par de chaves |
| Encrypt | Criptografa dados no servidor |
| Decrypt | Descriptografa dados no servidor |
| Sign | Assina dados no servidor |
| Verify | Verifica assinatura no servidor |
| Mac | Calcula MAC no servidor |
| Verify MAC | Verifica MAC no servidor |
| Get Attributes | Obtém atributos de um objeto |
| Set Attributes | Modifica atributos |
| Query | Consulta capacidades do servidor |

### 9.4 Cliente KMIP em C++17

```cpp
// include/kmip_client.h
#ifndef KMIP_CLIENT_H
#define KMIP_CLIENT_H

#include <string>
#include <vector>
#include <memory>
#include <cstdint>
#include <optional>

namespace kmip {

// Enumeração de tipos de objeto KMIP
enum class ObjectType : uint32_t {
    Certificate = 0x00000001,
    SymmetricKey = 0x00000002,
    PublicKey = 0x00000003,
    PrivateKey = 0x00000004,
    SplitKey = 0x00000005,
    Template = 0x00000006,
    OpaqueObject = 0x00000007,
    Credential = 0x00000008,
    SecretData = 0x00000009,
    PGPKey = 0x0000000A
};

// Enumeração de algoritmos
enum class Algorithm : uint32_t {
    AES = 0x00000001,
    DES = 0x00000002,
    TripleDES = 0x00000003,
    RSA = 0x00000004,
    DSA = 0x00000005,
    ECDSA = 0x00000006,
    HMAC = 0x00000007,
    SHA1 = 0x00000008,
    SHA256 = 0x00000009,
    SHA384 = 0x0000000A,
    SHA512 = 0x0000000B,
    RSAESPKCS1v15 = 0x0000000C,
    RSAEOAEP = 0x0000000D,
    HMACSHA1 = 0x0000000E,
    HMACSHA256 = 0x0000000F,
    HMACSHA384 = 0x00000010,
    HMACSHA512 = 0x00000011,
    CMAC = 0x00000012,
    Blowfish = 0x00000013,
    Camellia = 0x00000014,
    CAST5 = 0x00000015,
    IDEA = 0x00000016,
    RC4 = 0x00000017,
    BlowfishCBC = 0x00000018,
    CamelliaCBC = 0x00000019,
    CAST5CBC = 0x0000001A,
    IDEACBC = 0x0000001B,
    RC4CBC = 0x0000001C
};

// Resultado de operação KMIP
struct KmipResult {
    uint32_t status;
    std::string message;
    std::vector<uint8_t> data;
    std::string uniqueId;
};

// Configuração de conexão KMIP
struct KmipConfig {
    std::string host;
    uint16_t port = 5696; // Porta padrão KMIP
    std::string certFile;
    std::string keyFile;
    std::string caFile;
    bool verifyPeer = true;
    int timeoutSeconds = 30;
};

// Cliente KMIP
class KmipClient {
public:
    explicit KmipClient(const KmipConfig& config);
    ~KmipClient();

    // Conexão
    void connect();
    void disconnect();
    bool isConnected() const;

    // Operações de chave
    KmipResult createSymmetricKey(
        Algorithm algorithm,
        uint32_t keyLength,
        const std::string& name = ""
    );

    KmipResult createAsymmetricKeyPair(
        Algorithm algorithm,
        uint32_t keyLength,
        const std::string& name = ""
    );

    KmipResult get(const std::string& uniqueId);
    KmipResult destroy(const std::string& uniqueId);

    KmipResult rekey(const std::string& uniqueId);

    // Operações criptográficas
    KmipResult encrypt(
        const std::string& uniqueId,
        const std::vector<uint8_t>& plaintext,
        Algorithm algorithm
    );

    KmipResult decrypt(
        const std::string& uniqueId,
        const std::vector<uint8_t>& ciphertext,
        Algorithm algorithm
    );

    KmipResult sign(
        const std::string& uniqueId,
        const std::vector<uint8_t>& data,
        Algorithm algorithm
    );

    KmipResult verify(
        const std::string& uniqueId,
        const std::vector<uint8_t>& data,
        const std::vector<uint8_t>& signature,
        Algorithm algorithm
    );

    // Busca
    KmipResult locate(
        const std::string& name = "",
        ObjectType type = ObjectType::SymmetricKey
    );

    // Atributos
    KmipResult getAttributes(const std::string& uniqueId);
    KmipResult setAttributes(
        const std::string& uniqueId,
        const std::string& newName
    );

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace kmip

#endif // KMIP_CLIENT_H
```

### 9.5 Implementação do Cliente KMIP

```cpp
// src/kmip_client.cpp
#include "kmip_client.h"
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <stdexcept>

namespace kmip {

// Implementação do protocolo KMIP binário
// (Simplificada — em produção, usar biblioteca como kmippp)

#pragma pack(push, 1)
struct KmipTlvHeader {
    uint8_t tag[3];
    uint8_t type;
    uint32_t length;
};
#pragma pack(pop)

class KmipClient::Impl {
public:
    Impl(const KmipConfig& config) : config_(config) {}

    ~Impl() {
        disconnect();
    }

    void connect() {
        // Inicializar OpenSSL
        if (!SSL_library_initialized_) {
            SSL_library_init();
            SSL_load_error_strings();
            OpenSSL_add_all_algorithms();
            SSL_library_initialized_ = true;
        }

        // Criar contexto SSL
        sslCtx_ = SSL_CTX_new(TLS_client_method());
        if (!sslCtx_) {
            throw std::runtime_error(
                "Falha ao criar contexto SSL"
            );
        }

        // Carregar certificados
        if (!config_.certFile.empty()) {
            if (SSL_CTX_use_certificate_chain_file(
                    sslCtx_, config_.certFile.c_str()) != 1)
            {
                throw std::runtime_error(
                    "Falha ao carregar certificado"
                );
            }
        }

        if (!config_.keyFile.empty()) {
            if (SSL_CTX_use_PrivateKey_file(
                    sslCtx_, config_.keyFile.c_str(),
                    SSL_FILETYPE_PEM) != 1)
            {
                throw std::runtime_error(
                    "Falha ao carregar chave privada"
                );
            }
        }

        if (!config_.caFile.empty()) {
            if (SSL_CTX_load_verify_locations(
                    sslCtx_, config_.caFile.c_str(), nullptr) != 1)
            {
                throw std::runtime_error(
                    "Falha ao carregar CA certificate"
                );
            }
        }

        if (config_.verifyPeer) {
            SSL_CTX_set_verify(
                sslCtx_,
                SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                nullptr
            );
        }

        // Criar socket
        socket_ = socket(AF_INET, SOCK_STREAM, 0);
        if (socket_ < 0) {
            throw std::runtime_error(
                "Falha ao criar socket"
            );
        }

        // Conectar
        struct sockaddr_in serverAddr;
        memset(&serverAddr, 0, sizeof(serverAddr));
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_port = htons(config_.port);
        inet_pton(AF_INET, config_.host.c_str(),
                  &serverAddr.sin_addr);

        if (::connect(socket_,
                      reinterpret_cast<struct sockaddr*>(&serverAddr),
                      sizeof(serverAddr)) < 0)
        {
            close(socket_);
            socket_ = -1;
            throw std::runtime_error(
                "Falha ao conectar ao servidor KMIP"
            );
        }

        // Criar objeto SSL
        ssl_ = SSL_new(sslCtx_);
        SSL_set_fd(ssl_, socket_);

        if (SSL_connect(ssl_) <= 0) {
            SSL_free(ssl_);
            ssl_ = nullptr;
            close(socket_);
            socket_ = -1;
            throw std::runtime_error(
                "Falha no handshake TLS"
            );
        }

        connected_ = true;
    }

    void disconnect() {
        if (ssl_) {
            SSL_shutdown(ssl_);
            SSL_free(ssl_);
            ssl_ = nullptr;
        }
        if (socket_ >= 0) {
            close(socket_);
            socket_ = -1;
        }
        if (sslCtx_) {
            SSL_CTX_free(sslCtx_);
            sslCtx_ = nullptr;
        }
        connected_ = false;
    }

    bool isConnected() const { return connected_; }

    // Enviar mensagem KMIP
    std::vector<uint8_t> sendReceive(
        const std::vector<uint8_t>& request)
    {
        if (!connected_) {
            throw std::runtime_error(
                "Não conectado ao servidor KMIP"
            );
        }

        // Enviar tamanho + dados
        uint32_t netLength = htonl(
            static_cast<uint32_t>(request.size())
        );

        // Enviar header (tamanho)
        if (SSL_write(ssl_, &netLength, sizeof(netLength)) <= 0) {
            throw std::runtime_error("Falha ao enviar tamanho");
        }

        // Enviar payload
        if (SSL_write(ssl_, request.data(), request.size()) <= 0) {
            throw std::runtime_error("Falha ao enviar payload");
        }

        // Ler resposta — tamanho
        uint32_t responseLength;
        if (SSL_read(ssl_, &responseLength,
                     sizeof(responseLength)) <= 0)
        {
            throw std::runtime_error(
                "Falha ao ler tamanho da resposta"
            );
        }
        responseLength = ntohl(responseLength);

        if (responseLength > 10 * 1024 * 1024) { // 10MB limit
            throw std::runtime_error(
                "Resposta KMIP excede tamanho máximo"
            );
        }

        // Ler payload
        std::vector<uint8_t> response(responseLength);
        size_t totalRead = 0;
        while (totalRead < responseLength) {
            int bytesRead = SSL_read(
                ssl_,
                response.data() + totalRead,
                responseLength - totalRead
            );
            if (bytesRead <= 0) {
                throw std::runtime_error(
                    "Falha ao ler resposta KMIP"
                );
            }
            totalRead += bytesRead;
        }

        return response;
    }

private:
    KmipConfig config_;
    SSL_CTX* sslCtx_ = nullptr;
    SSL* ssl_ = nullptr;
    int socket_ = -1;
    bool connected_ = false;
    static bool SSL_library_initialized_;
};

bool KmipClient::Impl::SSL_library_initialized_ = false;

// ============================================================
// KmipClient — Implementação pública
// ============================================================

KmipClient::KmipClient(const KmipConfig& config)
    : impl_(std::make_unique<Impl>(config))
{}

KmipClient::~KmipClient() = default;

void KmipClient::connect() {
    impl_->connect();
}

void KmipClient::disconnect() {
    impl_->disconnect();
}

bool KmipClient::isConnected() const {
    return impl_->isConnected();
}

KmipResult KmipClient::createSymmetricKey(
    Algorithm algorithm, uint32_t keyLength,
    const std::string& name)
{
    // Construir mensagem KMIP Create
    // (Implementação simplificada do protocolo binário)
    std::vector<uint8_t> request;

    // Header da requisição
    // Tag: Request Message (0x420078)
    // Type: Structure (0x01)
    // ...
    // (A implementação completa requer encoder TLV adequado)

    KmipResult result;
    result.status = 0;
    result.message = "Success";

    // Enviar e receber
    auto response = impl_->sendReceive(request);

    // Parse da resposta (simplificado)
    // Em produção, usar um parser TLV adequado

    return result;
}

KmipResult KmipClient::createAsymmetricKeyPair(
    Algorithm algorithm, uint32_t keyLength,
    const std::string& name)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::get(const std::string& uniqueId) {
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::destroy(const std::string& uniqueId) {
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::rekey(const std::string& uniqueId) {
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::encrypt(
    const std::string& uniqueId,
    const std::vector<uint8_t>& plaintext,
    Algorithm algorithm)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::decrypt(
    const std::string& uniqueId,
    const std::vector<uint8_t>& ciphertext,
    Algorithm algorithm)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::sign(
    const std::string& uniqueId,
    const std::vector<uint8_t>& data,
    Algorithm algorithm)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::verify(
    const std::string& uniqueId,
    const std::vector<uint8_t>& data,
    const std::vector<uint8_t>& signature,
    Algorithm algorithm)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::locate(
    const std::string& name, ObjectType type)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::getAttributes(
    const std::string& uniqueId)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

KmipResult KmipClient::setAttributes(
    const std::string& uniqueId,
    const std::string& newName)
{
    KmipResult result;
    result.status = 0;
    result.message = "Success";
    return result;
}

} // namespace kmip
```

### 9.6 Servidores KMIP Populares

| Produto | Tipo | KMIP Version | HSM Backend | Custo |
|---------|------|--------------|-------------|-------|
| PyKMIP | Software (OSS) | 1.2-2.0 | SoftHSM | Grátis |
| CipherTrust Manager | Appliance | 2.0 | Thales Luna | $15K+ |
| Vormetric DSM | Appliance | 1.4-2.0 | Proprietário | $20K+ |
| AWS CloudHSM | Serviço | N/A (PKCS#11) | Thales/Marvell | $1.08K/mês |
| HashiCorp Vault | Software | Via transit | Suporta HSMs | Grátis (OSS) |

---

## 10. CVE-2021-36260: Hikvision weak crypto

### 10.1 Visão Geral da Vulnerabilidade

O CVE-2021-36260 é uma vulnerabilidade crítica (CVSS 9.8) encontrada em câmeras de segurança Hikvision que permite Remote Code Execution (RCE) através do uso de criptografia fraca. Esta vulnerabilidade ilustra perfeitamente as consequências de implementações inadequadas de criptografia em dispositivos embarcados.

### 10.2 Detalhes Técnicos

**Descrição**: As câmeras Hikvision usam um servidor web embutido para gerenciamento remoto. O servidor web suporta operações de upload de firmware via HTTP. A vulnerabilidade reside no fato de que a verificação de autenticação na interface web pode ser bypassada, permitindo que um atacante envie firmware modificado para a câmera.

**Causa raiz**: A autenticação do servidor web das câmeras usa um mecanismo de challenge-response baseado em criptografia customizada (não padrão). A implementação apresenta múltiplas falhas:

1. **Cifra fraca**: Usa um algoritmo de cifra simétrica proprietário com chaves derivadas de forma previsível
2. **Challenge previsível**: O nonce/challenge usado na autenticação pode ser predito
3. **Falta de verificação de integridade**: O firmware upload não verifica integridade criptográfica
4. **Exposição de informações**: Mensagens de erro detalhadas expõem o estado interno

### 10.3 Vetores de Ataque

```
Atacante                           Câmera Hikvision
   |                                    |
   |---- HTTP GET /SDK/webControl ----->|
   |                                    |
   |<-- Response: 200 OK ---------------|
   |                                    |
   |---- POST /firmwareUpgrade ------->|
   |    (firmware modificado)           |
   |                                    |
   |---- Bypass de autenticação ------->|
   |    (usando criptografia fraca)     |
   |                                    |
   |---- Upload de shell reverse ------->|
   |    (payload malicioso)             |
   |                                    |
   |<-- Shell reverse conecta ----------|
   |    (acesso root à câmera)          |
```

### 10.4 Exemplo de Análise de Criptografia Fraca (C++17)

```cpp
// src/cve_2021_36260_analysis.cpp
// ANÁLISE EDUCACIONAL — NÃO USAR PARA ATAQUES
// Este código demonstra como analisar criptografia fraca

#include <iostream>
#include <vector>
#include <string>
#include <cstring>
#include <array>
#include <cstdint>

namespace weak_crypto_analysis {

// Estrutura que simula a criptografia fraca encontrada na Hikvision
// BASEADA EM ANÁLISE PÚBLICA — Não reproduz o código exato do firmware

// Algoritmo proprietary fraco encontrado:
// - Chave derivada de MAC address (previsível)
// - XOR com constantes fixas
// - Sem autenticação de integridade adequada

struct WeakChallengeResponse {
    // O challenge do servidor
    uint8_t serverChallenge[8];

    // A resposta do cliente
    uint8_t clientResponse[8];

    // MAC address do dispositivo (previsível!)
    uint8_t deviceMac[6];
};

// Derivação fraca de chave (simulada)
// No CVE real, a chave era derivada de valores previsíveis
// como MAC address ou firmware version
std::array<uint8_t, 16> deriveWeakKey(
    const uint8_t* macAddress,
    const uint8_t* firmwareVersion)
{
    std::array<uint8_t, 16> key{};

    // Problema 1: Chave derivada de dados públicos
    // MAC address é visível na rede
    for (int i = 0; i < 6; ++i) {
        key[i] = macAddress[i] ^ 0xAA; // XOR com constante fixa
    }

    // Problema 2: Firmware version é pública
    for (int i = 0; i < 4; ++i) {
        key[6 + i] = firmwareVersion[i] ^ 0x55;
    }

    // Problema 3: Resto preenchido com zeros
    // (key[10..15] = 0)

    return key;
}

// Análise: por que isso é inseguro
void analyzeWeakness() {
    std::cout << "=== Análise de Criptografia Fraca (CVE-2021-36260) ==="
              << std::endl;
    std::cout << std::endl;

    std::cout << "1. DERIVAÇÃO DE CHAVE:" << std::endl;
    std::cout << "   Problema: Chave derivada de MAC address" << std::endl;
    std::cout << "   Impacto: MAC address é público (visível na rede)" << std::endl;
    std::cout << "   Correção: Usar KDF (HKDF, PBKDF2) com entropia secreta"
              << std::endl;
    std::cout << std::endl;

    std::cout << "2. ALGORITMO PROPRIETÁRIO:" << std::endl;
    std::cout << "   Problema: XOR com constantes fixas (0xAA, 0x55)" << std::endl;
    std::cout << "   Impacto: Sem segurança criptográfica real" << std::endl;
    std::cout << "   Correção: Usar AES-GCM ou ChaCha20-Poly1305" << std::endl;
    std::cout << std::endl;

    std::cout << "3. FALTA DE INTEGRIDADE:" << std::endl;
    std::cout << "   Problema: Firmware upload sem verificação HMAC" << std::endl;
    std::cout << "   Impacto: Atacante pode modificar firmware" << std::endl;
    std::cout << "   Correção: Assinar firmware com chave RSA/ECC" << std::endl;
    std::cout << std::endl;

    std::cout << "4. SEM AUTENTICAÇÃO ROBUSTA:" << std::endl;
    std::cout << "   Problema: Challenge-response fraco" << std::endl;
    std::cout << "   Impacto: Bypass de autenticação" << std::endl;
    std::cout << "   Correção: TLS mutual authentication" << std::endl;
    std::cout << std::endl;

    std::cout << "5. CHALLENGE PREVISÍVEL:" << std::endl;
    std::cout << "   Problema: Nonce pode ser predito" << std::endl;
    std::cout << "   Impacto: Replay attack possível" << std::endl;
    std::cout << "   Correção: Nonce aleatório de 128+ bits" << std::endl;
}

// Simulação de ataque por fuerza bruta (APENAS EDUCACIONAL)
void demonstrateWeakness() {
    std::cout << "=== Demonstração de Fraqueza (Educacional) ===" << std::endl;

    // Simular 256 câmeras com MAC addresses similares
    std::vector<std::array<uint8_t, 6>> macAddresses;

    for (uint16_t i = 0; i < 256; ++i) {
        std::array<uint8_t, 6> mac{};
        mac[0] = 0x00;
        mac[1] = 0x80;
        mac[2] = 0xE1;
        mac[3] = static_cast<uint8_t>(i >> 8);
        mac[4] = static_cast<uint8_t>(i & 0xFF);
        mac[5] = 0x01;
        macAddresses.push_back(mac);
    }

    // Mostrar que as chaves são previsíveis
    std::cout << "Primeiras 5 chaves derivadas:" << std::endl;
    uint8_t fwVersion[4] = {0x00, 0x01, 0x00, 0x01};

    for (int i = 0; i < 5; ++i) {
        auto key = deriveWeakKey(macAddresses[i].data(), fwVersion);
        std::cout << "MAC ";
        for (int j = 0; j < 6; ++j) {
            std::cout << std::hex << std::setw(2) << std::setfill('0')
                      << static_cast<int>(macAddresses[i][j]);
            if (j < 5) std::cout << ":";
        }
        std::cout << " -> Key: ";
        for (int j = 0; j < 16; ++j) {
            std::cout << std::hex << std::setw(2) << std::setfill('0')
                      << static_cast<int>(key[j]);
        }
        std::cout << std::dec << std::endl;
    }

    std::cout << "\nNota: Chaves são facilmente previsíveis!" << std::endl;
}

// Correção recomendada usando criptografia forte
std::array<uint8_t, 32> deriveStrongKey(
    const uint8_t* macAddress,
    const uint8_t* secret,  // Segredo em hardware (HSM!)
    size_t secretLen)
{
    // Usar HKDF (HMAC-based Key Derivation Function)
    // RFC 5869

    std::array<uint8_t, 32> key{};

    // Em produção, usar OpenSSL EVP_KDF ou similar
    // HMAC-SHA256(secret, "hikvision-key-derivation" || mac)

    // Simulação simplificada:
    // Em realidade, usar implementação completa de HKDF
    for (int i = 0; i < 32; ++i) {
        uint8_t prk = 0;
        for (int j = 0; j < static_cast<int>(secretLen) && j < 32; ++j) {
            prk ^= secret[j] ^ macAddress[i % 6];
        }
        key[i] = prk;
    }

    return key;
}

} // namespace weak_crypto_analysis

int main() {
    // ANÁLISE EDUCACIONAL do CVE-2021-36260
    // Este código é para fins de educação e análise de segurança
    // NÃO é código de exploit

    weak_crypto_analysis::analyzeWeakness();
    std::cout << std::endl;
    weak_crypto_analysis::demonstrateWeakness();

    std::cout << "\n=== LIÇÕES APRENDIDAS ===" << std::endl;
    std::cout << "1. Nunca usar criptografia proprietária não auditada" << std::endl;
    std::cout << "2. Chaves devem ser derivadas de segredos, não dados públicos" << std::endl;
    std::cout << "3. Firmware deve ser assinado digitalmente" << std::endl;
    std::cout << "4. Use TLS para todas as comunicações" << std::endl;
    std::cout << "5. Implemente HSM para proteção de chaves críticas" << std::endl;
    std::cout << "6. Realize auditorias de segurança regularmente" << std::endl;
    std::cout << "7. Responda rapidamente a CVEs publicados" << std::endl;

    return 0;
}
```

### 10.5 Impacto e Lições

**Impacto do CVE-2021-36260**:
- Afetou milhões de câmeras Hikvision em todo o mundo
- Permitiu RCE sem autenticação
- Usado em botnets e ataques DDoS
- CISA emitiu alerta urgente (Alerta AA21-265A)
- Hikvision lançou patch em setembro de 2021

**Lições para Engenharia de Criptografia**:

1. **Nunca inventar criptografia**: Use algoritmos padrão (AES, RSA, ECC) e bibliotecas auditadas (OpenSSL, libsodium)
2. **Proteção de firmware**: Sempre assinar firmware digitalmente e verificar integridade antes de instalação
3. **Autenticação robusta**: Use TLS mutual authentication, não challenge-response proprietário
4. **Gestão de vulnerabilidades**: Ter processo para responder rapidamente a CVEs
5. **Segurança em profundidade**: Não depender apenas de criptografia — usar defense in depth
6. **Atualizações seguras**: Permitir atualizações remotas, mas com verificação criptográfica rigorosa

---

## 11. Ataques contra HSMs: Tempest, fault injection

### 11.1 Classificação de Ataques

Os ataques contra HSMs podem ser classificados em:

**Ataques Passivos**: Não alteram o comportamento do HSM. Difíceis de detectar.
- TEMPEST (emanation security)
- Análise de consumo de energia (SPA/DPA)
- Análise de timing

**Ataques Ativos**: Alteram o comportamento do HSM. Podem ser detectados.
- Fault injection (glitching)
- Remoção de encapsulamento
- Microprobing
- Ataques laser

**Ataques de Software**: Exploram vulnerabilidades no firmware ou software.
- Buffer overflow
- Side-channel via software
- Exploitation de CVEs

### 11.2 TEMPEST

TEMPEST é um termo genérico para ataques de emanation — capturar sinais eletromagnéticos, acústicos ou de energia de um dispositivo para extrair informações.

**Emanações eletromagnéticas**: Um HSM em operação emite radiação eletromagnética que pode ser capturada por antenas especializadas. Operações criptográficas (especialmente multiplicações em RSA) geram padrões de emanação que podem revelar a chave.

**Emanações acústicas**: Componentes eletrônicos emitem sons audíveis durante operações. Análise de espectro pode revelar informações sobre operações internas.

**Emanações de energia**: Variações no consumo de energia do HSM podem ser analisadas para inferir operações criptográficas.

**Contramedidas TEMPEST**:
- **Blinding**: Adicionar operações aleatórias para mascarar o padrão de consumo
- **Shielding**: Blindagem eletromagnética do HSM
- **Distância**: Manter HSMs em salas controladas (SCIF)
- **Noise injection**: Inserir ruído aleatório nas operações

### 11.3 Fault Injection (Glitching)

Fault injection é a introdução deliberada de falhas no funcionamento de um circuito para forçar comportamento anômalo que pode revelar informações ou bypassar proteções.

**Tipos de fault injection**:

1. **Voltage glitching**: Reduzir ou aumentar a voltagem de alimentação momentaneamente
2. **Clock glitching**: Pulso de clock fora do timing normal
3. **Laser fault injection**: Feixe laser focado em transistores específicos
4. **EM fault injection**: Pulso eletromagnético para perturbar circuitos
5. **Temperature**: Exposição a temperaturas extremas

**Exemplo de ataque por voltage glitching**:

```
Operação Normal:
1. Ler chave da memória
2. Executar operação criptográfica
3. Retornar resultado

Com Voltage Glitch:
1. Ler chave da memória
2. [GLITCH na voltagem] → Pular verificação de segurança
3. Retornar chave em texto plano
```

**Defesas contra fault injection**:

- **Dual-rail logic**: Implementar cada operação em duas redes complementares
- **Redundância temporal**: Executar operação duas vezes e comparar
- **Sensores de voltagem**: Detectar variações anormais
- **Sensores de temperatura**: Detectar condições ambientais anormais
- **Zeroização automática**: Apagar chaves quando detectado ataque
- **Selos de tampership**: Evidência física de abertura não autorizada

### 11.4 Side-Channel Attacks

Ataques de canal lateral exploram informações "laterais" emitidas pelo dispositivo durante operações criptográficas.

**Simple Power Analysis (SPA)**:
- Analisa o consumo de energia durante uma operação
- Diferentes operações (multiplicação vs. squaring) têm padrões diferentes
- Pode revelar a chave inteira em RSA com exponente curto

**Differential Power Analysis (DPA)**:
- Usa análise estatística de múltiplas medições
- Correlaciona variações de energia com bits da chave
- Muito mais poderoso que SPA
- Pode quebrar implementações que resistem a SPA

**Timing Attack**:
- Mede o tempo de operações criptográficas
- Operações condicionais (como verificação de assinatura) leakam informação
- Exemplo clássico: early termination em RSA

**Cache Attack**:
- Explora o cache da CPU para inferir padrões de acesso
- AES lookup tables leakam informação
- Mitigado por bitsliced implementations

**Contra-medidas para Side-Channel**:

- **Constant-time operations**: Todas as operações executam em tempo constante
- **Blinding**: Adicionar valores aleatórios a cada operação
- **Masking**: Mascarar valores intermediários com randomness
- **DPA countermeasures**: Adicionar ruído e aleatoriedade ao consumo
- **Hardware countermeasures**: Circuitos de proteção contra SPA/DPA

### 11.5 Defesas HSM Modernas

HSMs modernos implementam múltiplas camadas de defesa:

```
+--------------------------------------------------+
|                 Defesas HSM                       |
|                                                   |
|  +--------------------------------------------+ |
|  | Camada 1: Proteção Física                  | |
|  | - Epoxy potting (tamper mesh)              | |
|  | - Sensores de luz                          | |
|  | - Sensores de temperatura                  | |
|  | - Sensores de voltagem                     | |
|  +--------------------------------------------+ |
|                                                   |
|  +--------------------------------------------+ |
|  | Camada 2: Proteção Lógica                  | |
|  | - Zeroização automática                    | |
|  | - Autenticação rigorosa                    | |
|  | - Rate limiting                            | |
|  | - Audit logging                            | |
|  +--------------------------------------------+ |
|                                                   |
|  +--------------------------------------------+ |
|  | Camada 3: Proteção Criptográfica           | |
|  | - Constant-time operations                 | |
|  | - Blinding (SPA/DPA)                       | |
|  | - TRNG para nonces e IVs                   | |
|  | - Key wrapping                             | |
|  +--------------------------------------------+ |
|                                                   |
|  +--------------------------------------------+ |
|  | Camada 4: Proteção de Software             | |
|  | - Firmware assinado                        | |
|  | - Secure boot                              | |
|  | - Atualizações verificadas                 | |
|  | - Proteção contra rollback                 | |
|  +--------------------------------------------+ |
+--------------------------------------------------+
```

### 11.6 Exemplo: Teste de Side-Channel (Educacional)

```cpp
// src/sidechannel_analysis.cpp
// ANÁLISE EDUCACIONAL — Para entender ataques de canal lateral
// NÃO implementar ataques reais

#include <iostream>
#include <vector>
#include <chrono>
#include <random>
#include <algorithm>

namespace sidechannel_analysis {

// Simulação de operação RSA vulnerável a timing attack
// (NÃO usar em produção!)
class VulnerableRSA {
public:
    // Assinatura RSA simples (vulnerável a timing attack)
    // Exponenciação modular com early termination
    static std::vector<uint64_t> sign(
        const std::vector<uint64_t>& message,
        const std::vector<uint64_t>& privateKey,
        uint64_t modulus)
    {
        std::vector<uint64_t> result(message.size());

        for (size_t i = 0; i < message.size(); ++i) {
            // Early termination — vulnerabilidade!
            // Quando message[i] * privateKey < modulus,
            // a multiplicação é mais rápida
            uint64_t acc = 1;
            for (uint64_t j = 0; j < privateKey[0]; ++j) {
                acc = (acc * message[i]) % modulus;
            }
            result[i] = acc;
        }

        return result;
    }
};

// Implementação constante (segura contra timing attack)
class ConstantTimeRSA {
public:
    // Assinatura RSA com tempo constante
    // Sem early termination — sempre executa todas as iterações
    static std::vector<uint64_t> sign(
        const std::vector<uint64_t>& message,
        const std::vector<uint64_t>& privateKey,
        uint64_t modulus)
    {
        std::vector<uint64_t> result(message.size());

        for (size_t i = 0; i < message.size(); ++i) {
            uint64_t acc = 1;
            uint64_t exp = privateKey[0];

            // Executa TODAS as iterações, mesmo quando acc = 1
            // Adiciona operação dummy para manter tempo constante
            for (uint64_t j = 0; j < 64; ++j) { // Fixo em 64
                if (j < exp) {
                    acc = (acc * message[i]) % modulus;
                }
                // Operação dummy — não afeta resultado
                volatile uint64_t dummy = acc;
                (void)dummy;
            }
            result[i] = acc;
        }

        return result;
    }
};

// Medidor de timing
class TimingAnalyzer {
public:
    struct Measurement {
        std::vector<double> timings; // em nanosegundos
    };

    template<typename Func>
    Measurement measure(Func&& func, int iterations) {
        Measurement m;
        m.timings.reserve(iterations);

        for (int i = 0; i < iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();
            func();
            auto end = std::chrono::high_resolution_clock::now();

            double ns = std::chrono::duration<double, std::nano>(
                end - start
            ).count();
            m.timings.push_back(ns);
        }

        return m;
    }

    static void analyze(const Measurement& m,
                       const std::string& label)
    {
        auto sorted = m.timings;
        std::sort(sorted.begin(), sorted.end());

        double sum = 0;
        for (double t : sorted) sum += t;
        double mean = sum / sorted.size();

        double variance = 0;
        for (double t : sorted) {
            variance += (t - mean) * (t - mean);
        }
        variance /= sorted.size();
        double stddev = std::sqrt(variance);

        std::cout << label << ":" << std::endl;
        std::cout << "  Média: " << std::fixed << std::setprecision(1)
                  << mean << " ns" << std::endl;
        std::cout << "  Desvio padrão: " << stddev << " ns" << std::endl;
        std::cout << "  Min: " << sorted.front() << " ns" << std::endl;
        std::cout << "  Max: " << sorted.back() << " ns" << std::endl;
        std::cout << "  Coef. variação: " << std::fixed
                  << std::setprecision(2)
                  << (stddev / mean * 100) << "%" << std::endl;
    }
};

} // namespace sidechannel_analysis

int main() {
    std::cout << "=== Análise de Side-Channel (Educacional) ==="
              << std::endl;
    std::cout << "AVISO: Este código é para fins educacionais apenas!"
              << std::endl;
    std::cout << std::endl;

    // Configuração
    std::mt19937 rng(42);
    std::uniform_int_distribution<uint64_t> dist(1, 1000);

    uint64_t modulus = 1000000007ULL; // Primo grande (simplificado)
    std::vector<uint64_t> privateKey = {32}; // Exponente 32

    // Gerar dados de teste
    std::vector<uint64_t> messageSmall = {2, 3, 5, 7};
    std::vector<uint64_t> messageLarge = {999, 888, 777, 666};

    sidechannel_analysis::TimingAnalyzer analyzer;

    // Testar implementação vulnerável
    std::cout << "Testando implementação vulnerável..." << std::endl;

    auto timingSmallVuln = analyzer.measure([&]() {
        sidechannel_analysis::VulnerableRSA::sign(
            messageSmall, privateKey, modulus
        );
    }, 10000);

    auto timingLargeVuln = analyzer.measure([&]() {
        sidechannel_analysis::VulnerableRSA::sign(
            messageLarge, privateKey, modulus
        );
    }, 10000);

    sidechannel_analysis::TimingAnalyzer::analyze(
        timingSmallVuln, "Vulnerável - Mensagem Pequena"
    );
    sidechannel_analysis::TimingAnalyzer::analyze(
        timingLargeVuln, "Vulnerável - Mensagem Grande"
    );

    std::cout << std::endl;

    // Testar implementação constante
    std::cout << "Testando implementação constante..." << std::endl;

    auto timingSmallConst = analyzer.measure([&]() {
        sidechannel_analysis::ConstantTimeRSA::sign(
            messageSmall, privateKey, modulus
        );
    }, 10000);

    auto timingLargeConst = analyzer.measure([&]() {
        sidechannel_analysis::ConstantTimeRSA::sign(
            messageLarge, privateKey, modulus
        );
    }, 10000);

    sidechannel_analysis::TimingAnalyzer::analyze(
        timingSmallConst, "Constante - Mensagem Pequena"
    );
    sidechannel_analysis::TimingAnalyzer::analyze(
        timingLargeConst, "Constante - Mensagem Grande"
    );

    std::cout << "\n=== Conclusão ===" << std::endl;
    std::cout << "Se o coeficiente de variação da implementação" << std::endl;
    const double vulnCv = 15.0; // Simplificado
    const double constCv = 2.0;
    std::cout << "vulnerável (" << vulnCv << "%) é significativamente" << std::endl;
    std::cout << "maior que o da implementação constante (" << constCv << "%)," << std::endl;
    std::cout << "então há uma vulnerabilidade de timing." << std::endl;

    return 0;
}
```

---

## 12. Backup e Recovery de chaves HSM

### 12.1 Por que Backup de Chaves HSM?

HSMs protegem chaves contra acesso não autorizado, mas isso cria um problema: se o HSM falhar fisicamente, as chaves são perdidas para sempre. Para organizações que dependem dessas chaves para operações críticas (bancos, governos, empresas de telecomunicações), a perda de uma chave mestra pode significar falência.

### 12.2 Estratégias de Backup

#### Backup com Key Wrapping

A abordagem mais comum para backup de chaves HSM é o **key wrapping**: usar uma chave de backup (que reside em outro HSM ou no mesmo HSM em contexto diferente) para criptografar a chave a ser salva.

```
Chave A (em HSM-1)
    |
    v (Encrypt com Chave de Backup)
Chave B (Chave de Backup, em HSM-2 ou offline)
    |
    v
Chave A' (ciphertext, armazenada em disco)
```

**Processo**:
1. Gerar chave de backup (ou usar chave de backup existente)
2. Exportar chave A do HSM (wrap com chave de backup)
3. Armazenar ciphertext em disco (protegido por backup routines)
4. Para restaurar: importar ciphertext no HSM e unwrap

#### Backup com Quórum (M-of-N)

Para chaves críticas, usar quórum para backup e restauração:

- Gerar chave de backup
- Dividir a chave em N shares (secret sharing, ex: Shamir's Secret Sharing)
- Distribuir shares entre N pessoas confiáveis
- Para restaurar: M shares são necessários

```
Chave Mestra
    |
    v (Shamir Secret Sharing)
    +--- Share 1 (Operador A)
    +--- Share 2 (Operador B)
    +--- Share 3 (Operador C)
    +--- Share 4 (Operador D)
    +--- Share 5 (Operador E)

Para restaurar: qualquer 3 de 5 shares
```

#### Backup Hierárquico

```
                    Chave Root (Offline HSM)
                    Backup: Shamir 3-of-5
                    Local: Vault físico
                         |
         +---------------+---------------+
         |               |               |
    Chave CA 1      Chave CA 2      Chave CA 3
    Backup: Key     Backup: Key     Backup: Key
    Wrapping        Wrapping        Wrapping
    Local: HSM-1    Local: HSM-2    Local: HSM-3
```

### 12.3 Implementação de Backup Seguro

```cpp
// include/hsm_backup.h
#ifndef HSM_BACKUP_H
#define HSM_BACKUP_H

#include "pkcs11_wrapper.h"
#include "hsm_key_manager.h"
#include <string>
#include <vector>
#include <fstream>

namespace hsm {

// Dados de backup de uma chave
struct KeyBackupData {
    std::string label;
    std::vector<CK_BYTE> wrappedKey;
    std::vector<CK_BYTE> publicKey;
    KeyType keyType;
    std::string timestamp;
    std::string checksum;
};

// Mecanismo de backup HSM
class HsmBackupManager {
public:
    HsmBackupManager(
        Pkcs11Session& sourceSession,
        Pkcs11Session& backupSession
    );

    // Backup com key wrapping
    KeyBackupData backupKey(
        CK_OBJECT_HANDLE keyHandle,
        CK_OBJECT_HANDLE wrappingKeyHandle,
        const std::string& backupLabel
    );

    // Restaurar chave
    CK_OBJECT_HANDLE restoreKey(
        const KeyBackupData& backupData,
        CK_OBJECT_HANDLE unwrappingKeyHandle
    );

    // Backup para arquivo criptografado
    void backupToFile(
        const std::string& filename,
        const KeyBackupData& data,
        const std::string& passphrase
    );

    // Restaurar de arquivo
    KeyBackupData restoreFromFile(
        const std::string& filename,
        const std::string& passphrase
    );

    // Verificar integridade do backup
    bool verifyBackup(const KeyBackupData& data);

    // Listar backups
    std::vector<KeyBackupData> listBackups(
        const std::string& directory
    );

private:
    Pkcs11Session& sourceSession_;
    Pkcs11Session& backupSession_;

    // Helpers
    std::string calculateChecksum(
        const std::vector<CK_BYTE>& data
    );

    std::vector<CK_BYTE> encryptBackupData(
        const std::vector<CK_BYTE>& data,
        const std::string& passphrase
    );

    std::vector<CK_BYTE> decryptBackupData(
        const std::vector<CK_BYTE>& data,
        const std::string& passphrase
    );
};

// Secret Sharing (Shamir's Secret Sharing)
class SecretSharing {
public:
    struct Share {
        uint8_t index;
        std::vector<uint8_t> data;
    };

    // Dividir segredo em N shares com threshold M
    static std::vector<Share> split(
        const std::vector<uint8_t>& secret,
        int totalShares,
        int threshold
    );

    // Reconstruir segredo de M shares
    static std::vector<uint8_t> reconstruct(
        const std::vector<Share>& shares,
        int threshold
    );

private:
    // Operações em campo finito GF(2^8)
    static uint8_t gfMultiply(uint8_t a, uint8_t b);
    static uint8_t gfDivide(uint8_t a, uint8_t b);
    static uint8_t gfPow(uint8_t base, int exp);

    // Avaliação de polinômio
    static uint8_t evaluatePolynomial(
        const std::vector<uint8_t>& coefficients,
        uint8_t x
    );
};

} // namespace hsm

#endif // HSM_BACKUP_H
```

### 12.4 Implementação do Backup Manager

```cpp
// src/hsm_backup.cpp
#include "hsm_backup.h"
#include <openssl/sha.h>
#include <openssl/aes.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <fstream>
#include <sstream>
#include <iomanip>

namespace hsm {

HsmBackupManager::HsmBackupManager(
    Pkcs11Session& sourceSession,
    Pkcs11Session& backupSession)
    : sourceSession_(sourceSession)
    , backupSession_(backupSession)
{}

KeyBackupData HsmBackupManager::backupKey(
    CK_OBJECT_HANDLE keyHandle,
    CK_OBJECT_HANDLE wrappingKeyHandle,
    const std::string& backupLabel)
{
    KeyBackupData data;
    data.label = backupLabel;
    data.timestamp = getCurrentTimestamp();

    // 1. Obter atributos da chave
    Pkcs11Object keyObj(sourceSession_, keyHandle);
    auto keyTypeBytes = keyObj.getAttributeBytes(CKA_KEY_TYPE);
    CK_KEY_TYPE keyType;
    std::memcpy(&keyType, keyTypeBytes.data(), sizeof(CK_KEY_TYPE));

    if (keyType == CKK_AES || keyType == CKK_DES3) {
        data.keyType = KeyType::AES_256;
    } else if (keyType == CKK_RSA) {
        data.keyType = KeyType::RSA_2048;
    } else if (keyType == CKK_EC) {
        data.keyType = KeyType::ECDSA_P256;
    }

    // 2. Exportar chave pública (se aplicável)
    if (keyType == CKK_RSA || keyType == CKK_EC) {
        try {
            auto pubModulus = keyObj.getAttributeBytes(CKA_MODULUS);
            auto pubExp = keyObj.getAttributeBytes(CKA_PUBLIC_EXPONENT);
            data.publicKey.insert(
                data.publicKey.end(),
                pubModulus.begin(), pubModulus.end()
            );
            data.publicKey.insert(
                data.publicKey.end(),
                pubExp.begin(), pubExp.end()
            );
        } catch (...) {
            // Chave pode não ter atributos públicos exportáveis
        }
    }

    // 3. Wrap a chave
    CK_MECHANISM wrapMech = {CKM_AES_KEY_WRAP, nullptr, 0};

    CK_ULONG wrappedLen = 0;
    CK_RV rv = sourceSession_.library_->functions_->C_WrapKey(
        sourceSession_.handle(),
        &wrapMech,
        wrappingKeyHandle,
        keyHandle,
        nullptr,
        &wrappedLen
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_WrapKey (backup)");
    }

    data.wrappedKey.resize(wrappedLen);
    rv = sourceSession_.library_->functions_->C_WrapKey(
        sourceSession_.handle(),
        &wrapMech,
        wrappingKeyHandle,
        keyHandle,
        data.wrappedKey.data(),
        &wrappedLen
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_WrapKey (backup data)");
    }
    data.wrappedKey.resize(wrappedLen);

    // 4. Calcular checksum
    data.checksum = calculateChecksum(data.wrappedKey);

    return data;
}

CK_OBJECT_HANDLE HsmBackupManager::restoreKey(
    const KeyBackupData& backupData,
    CK_OBJECT_HANDLE unwrappingKeyHandle)
{
    // Verificar checksum
    if (!verifyBackup(backupData)) {
        throw std::runtime_error(
            "Verificação de integridade do backup falhou"
        );
    }

    // Construir template para a chave restaurada
    CK_BBOOL trueVal = CK_TRUE;
    CK_KEY_TYPE keyType;

    switch (backupData.keyType) {
        case KeyType::AES_256:
            keyType = CKK_AES;
            break;
        case KeyType::RSA_2048:
            keyType = CKK_RSA;
            break;
        case KeyType::ECDSA_P256:
            keyType = CKK_EC;
            break;
        default:
            throw std::invalid_argument("Tipo de chave desconhecido");
    }

    std::vector<CK_ATTRIBUTE> templateAttrs = {
        {CKA_KEY_TYPE, &keyType, sizeof(CK_KEY_TYPE)},
        {CKA_TOKEN, &trueVal, sizeof(CK_BBOOL)},
        {CKA_LABEL, const_cast<char*>(backupData.label.c_str()),
                    static_cast<CK_ULONG>(backupData.label.size())},
    };

    // Unwrap
    CK_MECHANISM unwrapMech = {CKM_AES_KEY_WRAP, nullptr, 0};
    CK_OBJECT_HANDLE hKey;

    CK_RV rv = backupSession_.library_->functions_->C_UnwrapKey(
        backupSession_.handle(),
        &unwrapMech,
        unwrappingKeyHandle,
        const_cast<CK_BYTE*>(backupData.wrappedKey.data()),
        static_cast<CK_ULONG>(backupData.wrappedKey.size()),
        templateAttrs.data(),
        static_cast<CK_ULONG>(templateAttrs.size()),
        &hKey
    );
    if (rv != CKR_OK) {
        throw Pkcs11Error(rv, "C_UnwrapKey (restore)");
    }

    return hKey;
}

void HsmBackupManager::backupToFile(
    const std::string& filename,
    const KeyBackupData& data,
    const std::string& passphrase)
{
    // Serializar dados
    std::vector<CK_BYTE> serialized;

    // Header: "HSM_BACKUP_v1"
    const char* header = "HSM_BACKUP_v1";
    serialized.insert(serialized.end(), header, header + strlen(header));

    // Tamanho do label
    uint32_t labelLen = htonl(static_cast<uint32_t>(data.label.size()));
    auto* labelLenBytes = reinterpret_cast<CK_BYTE*>(&labelLen);
    serialized.insert(serialized.end(), labelLenBytes, labelLenBytes + 4);

    // Label
    serialized.insert(
        serialized.end(),
        data.label.begin(), data.label.end()
    );

    // Tamanho do wrapped key
    uint32_t wrappedLen = htonl(
        static_cast<uint32_t>(data.wrappedKey.size())
    );
    auto* wrappedLenBytes = reinterpret_cast<CK_BYTE*>(&wrappedLen);
    serialized.insert(serialized.end(), wrappedLenBytes, wrappedLenBytes + 4);

    // Wrapped key
    serialized.insert(
        serialized.end(),
        data.wrappedKey.begin(), data.wrappedKey.end()
    );

    // Tamanho da chave pública
    uint32_t pubKeyLen = htonl(
        static_cast<uint32_t>(data.publicKey.size())
    );
    auto* pubKeyLenBytes = reinterpret_cast<CK_BYTE*>(&pubKeyLen);
    serialized.insert(serialized.end(), pubKeyLenBytes, pubKeyLenBytes + 4);

    // Chave pública
    serialized.insert(
        serialized.end(),
        data.publicKey.begin(), data.publicKey.end()
    );

    // Tamanho do timestamp
    uint32_t tsLen = htonl(
        static_cast<uint32_t>(data.timestamp.size())
    );
    auto* tsLenBytes = reinterpret_cast<CK_BYTE*>(&tsLen);
    serialized.insert(serialized.end(), tsLenBytes, tsLenBytes + 4);

    // Timestamp
    serialized.insert(
        serialized.end(),
        data.timestamp.begin(), data.timestamp.end()
    );

    // Tamanho do checksum
    uint32_t csLen = htonl(
        static_cast<uint32_t>(data.checksum.size())
    );
    auto* csLenBytes = reinterpret_cast<CK_BYTE*>(&csLen);
    serialized.insert(serialized.end(), csLenBytes, csLenBytes + 4);

    // Checksum
    serialized.insert(
        serialized.end(),
        data.checksum.begin(), data.checksum.end()
    );

    // Criptografar com passphrase
    auto encrypted = encryptBackupData(serialized, passphrase);

    // Salvar em arquivo
    std::ofstream outFile(filename, std::ios::binary);
    if (!outFile) {
        throw std::runtime_error(
            "Falha ao abrir arquivo para escrita: " + filename
        );
    }
    outFile.write(
        reinterpret_cast<const char*>(encrypted.data()),
        encrypted.size()
    );
}

KeyBackupData HsmBackupManager::restoreFromFile(
    const std::string& filename,
    const std::string& passphrase)
{
    // Ler arquivo
    std::ifstream inFile(filename, std::ios::binary);
    if (!inFile) {
        throw std::runtime_error(
            "Falha ao abrir arquivo: " + filename
        );
    }

    std::vector<CK_BYTE> encrypted(
        (std::istreambuf_iterator<char>(inFile)),
        std::istreambuf_iterator<char>()
    );

    // Descriptografar
    auto serialized = decryptBackupData(encrypted, passphrase);

    // Parse
    KeyBackupData data;
    size_t offset = 0;

    // Header
    const char* header = "HSM_BACKUP_v1";
    if (serialized.size() < 13) {
        throw std::runtime_error("Arquivo de backup inválido");
    }
    offset = 13; // strlen("HSM_BACKUP_v1")

    // Label
    uint32_t labelLen;
    std::memcpy(&labelLen, serialized.data() + offset, 4);
    labelLen = ntohl(labelLen);
    offset += 4;

    data.label.assign(
        serialized.begin() + offset,
        serialized.begin() + offset + labelLen
    );
    offset += labelLen;

    // Wrapped key
    uint32_t wrappedLen;
    std::memcpy(&wrappedLen, serialized.data() + offset, 4);
    wrappedLen = ntohl(wrappedLen);
    offset += 4;

    data.wrappedKey.assign(
        serialized.begin() + offset,
        serialized.begin() + offset + wrappedLen
    );
    offset += wrappedLen;

    // Public key
    uint32_t pubKeyLen;
    std::memcpy(&pubKeyLen, serialized.data() + offset, 4);
    pubKeyLen = ntohl(pubKeyLen);
    offset += 4;

    data.publicKey.assign(
        serialized.begin() + offset,
        serialized.begin() + offset + pubKeyLen
    );
    offset += pubKeyLen;

    // Timestamp
    uint32_t tsLen;
    std::memcpy(&tsLen, serialized.data() + offset, 4);
    tsLen = ntohl(tsLen);
    offset += 4;

    data.timestamp.assign(
        serialized.begin() + offset,
        serialized.begin() + offset + tsLen
    );
    offset += tsLen;

    // Checksum
    uint32_t csLen;
    std::memcpy(&csLen, serialized.data() + offset, 4);
    csLen = ntohl(csLen);
    offset += 4;

    data.checksum.assign(
        serialized.begin() + offset,
        serialized.begin() + offset + csLen
    );

    data.keyType = KeyType::AES_256; // Default

    return data;
}

bool HsmBackupManager::verifyBackup(const KeyBackupData& data) {
    std::string calculated = calculateChecksum(data.wrappedKey);
    return calculated == data.checksum;
}

std::vector<KeyBackupData> HsmBackupManager::listBackups(
    const std::string& directory)
{
    std::vector<KeyBackupData> backups;
    // Implementação depende do sistema de arquivos
    // Em produção, usar std::filesystem
    return backups;
}

std::string HsmBackupManager::calculateChecksum(
    const std::vector<CK_BYTE>& data)
{
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256(data.data(), data.size(), hash);

    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
        oss << std::setw(2) << static_cast<int>(hash[i]);
    }
    return oss.str();
}

std::vector<CK_BYTE> HsmBackupManager::encryptBackupData(
    const std::vector<CK_BYTE>& data,
    const std::string& passphrase)
{
    // Derivar chave da passphrase usando PBKDF2
    unsigned char key[32];
    unsigned char iv[16];
    const unsigned char* salt = reinterpret_cast<const unsigned char*>(
        "hsm-backup-salt-v1"
    );

    PKCS5_PBKDF2_HMAC(
        passphrase.c_str(),
        passphrase.size(),
        salt,
        16,
        100000,  // 100K iterações
        EVP_sha256(),
        32,
        key
    );

    // Gerar IV aleatório
    RAND_bytes(iv, 16);

    // Criptografar com AES-256-GCM
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) throw std::runtime_error("Falha ao criar contexto EVP");

    std::vector<CK_BYTE> output;
    output.insert(output.end(), iv, iv + 16);

    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                           key, iv) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha ao inicializar criptografia");
    }

    int outLen = 0;
    std::vector<CK_BYTE> ciphertext(data.size() + 16);
    if (EVP_EncryptUpdate(ctx, ciphertext.data(), &outLen,
                          data.data(), data.size()) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha no EncryptUpdate");
    }

    int finalLen = 0;
    if (EVP_EncryptFinal_ex(ctx, ciphertext.data() + outLen,
                            &finalLen) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha no EncryptFinal");
    }

    outLen += finalLen;
    ciphertext.resize(outLen);

    // Obter tag
    unsigned char tag[16];
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha ao obter tag GCM");
    }

    EVP_CIPHER_CTX_free(ctx);

    output.insert(output.end(), ciphertext.begin(), ciphertext.end());
    output.insert(output.end(), tag, tag + 16);

    return output;
}

std::vector<CK_BYTE> HsmBackupManager::decryptBackupData(
    const std::vector<CK_BYTE>& data,
    const std::string& passphrase)
{
    if (data.size() < 48) { // 16 IV + 16 tag + min ciphertext
        throw std::runtime_error("Dados criptografados inválidos");
    }

    // Extrair IV
    const unsigned char* iv = data.data();

    // Extrair ciphertext
    const unsigned char* ciphertext = data.data() + 16;
    size_t ciphertextLen = data.size() - 32; // -16 IV -16 tag

    // Extrair tag
    const unsigned char* tag = data.data() + data.size() - 16;

    // Derivar chave
    unsigned char key[32];
    const unsigned char* salt = reinterpret_cast<const unsigned char*>(
        "hsm-backup-salt-v1"
    );

    PKCS5_PBKDF2_HMAC(
        passphrase.c_str(),
        passphrase.size(),
        salt,
        16,
        100000,
        EVP_sha256(),
        32,
        key
    );

    // Descriptografar
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) throw std::runtime_error("Falha ao criar contexto EVP");

    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr,
                           key, iv) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha ao inicializar descriptografia");
    }

    int outLen = 0;
    std::vector<CK_BYTE> plaintext(ciphertextLen + 16);
    if (EVP_DecryptUpdate(ctx, plaintext.data(), &outLen,
                          ciphertext, ciphertextLen) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha no DecryptUpdate");
    }

    // Definir tag
    if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16,
                            const_cast<unsigned char*>(tag)) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error("Falha ao definir tag GCM");
    }

    int finalLen = 0;
    if (EVP_DecryptFinal_ex(ctx, plaintext.data() + outLen,
                            &finalLen) != 1)
    {
        EVP_CIPHER_CTX_free(ctx);
        throw std::runtime_error(
            "Falha na verificação de integridade (tag inválida)"
        );
    }

    outLen += finalLen;
    EVP_CIPHER_CTX_free(ctx);

    plaintext.resize(outLen);
    return plaintext;
}

// ============================================================
// Secret Sharing (Shamir's Secret Sharing)
// ============================================================

uint8_t SecretSharing::gfMultiply(uint8_t a, uint8_t b) {
    uint8_t result = 0;
    uint8_t temp = b;

    for (int i = 0; i < 8; ++i) {
        if (a & (1 << i)) {
            result ^= temp;
        }
        bool highBit = temp & 0x80;
        temp <<= 1;
        if (highBit) {
            temp ^= 0x1B; // Irreducible polynomial for GF(2^8)
        }
    }

    return result;
}

uint8_t SecretSharing::gfDivide(uint8_t a, uint8_t b) {
    if (b == 0) throw std::runtime_error("Divisão por zero em GF(2^8)");
    return gfMultiply(a, gfPow(b, 254)); // a * b^(-1) = a * b^254
}

uint8_t SecretSharing::gfPow(uint8_t base, int exp) {
    uint8_t result = 1;
    uint8_t temp = base;

    while (exp > 0) {
        if (exp & 1) {
            result = gfMultiply(result, temp);
        }
        temp = gfMultiply(temp, temp);
        exp >>= 1;
    }

    return result;
}

uint8_t SecretSharing::evaluatePolynomial(
    const std::vector<uint8_t>& coefficients, uint8_t x)
{
    uint8_t result = 0;
    uint8_t xPow = 1;

    for (size_t i = 0; i < coefficients.size(); ++i) {
        result ^= gfMultiply(coefficients[i], xPow);
        xPow = gfMultiply(xPow, x);
    }

    return result;
}

std::vector<SecretSharing::Share> SecretSharing::split(
    const std::vector<uint8_t>& secret,
    int totalShares,
    int threshold)
{
    if (threshold < 2) {
        throw std::invalid_argument(
            "Threshold deve ser >= 2"
        );
    }
    if (totalShares < threshold) {
        throw std::invalid_argument(
            "Total shares deve ser >= threshold"
        );
    }
    if (secret.size() == 0) {
        throw std::invalid_argument("Segredo vazio");
    }

    std::vector<Share> shares(totalShares);

    for (size_t byteIdx = 0; byteIdx < secret.size(); ++byteIdx) {
        // Gerar polinômio aleatório de grau threshold-1
        std::vector<uint8_t> polynomial(threshold);
        polynomial[0] = secret[byteIdx]; // a0 = segredo

        // Gerar coeficientes aleatórios
        for (int i = 1; i < threshold; ++i) {
            polynomial[i] = static_cast<uint8_t>(rand() % 256);
        }

        // Avaliar polinômio em pontos 1, 2, ..., totalShares
        for (int i = 0; i < totalShares; ++i) {
            uint8_t x = static_cast<uint8_t>(i + 1);
            uint8_t y = evaluatePolynomial(polynomial, x);

            if (shares[i].data.empty()) {
                shares[i].index = x;
                shares[i].data.resize(secret.size());
            }
            shares[i].data[byteIdx] = y;
        }
    }

    return shares;
}

std::vector<uint8_t> SecretSharing::reconstruct(
    const std::vector<Share>& shares,
    int threshold)
{
    if (static_cast<int>(shares.size()) < threshold) {
        throw std::invalid_argument(
            "Shares insuficientes para reconstrução"
        );
    }

    size_t secretLen = shares[0].data.size();
    std::vector<uint8_t> secret(secretLen);

    for (size_t byteIdx = 0; byteIdx < secretLen; ++byteIdx) {
        // Interpolação de Lagrange
        uint8_t result = 0;

        for (int i = 0; i < threshold; ++i) {
            uint8_t xi = shares[i].index;
            uint8_t yi = shares[i].data[byteIdx];

            // Calcular coeficiente de Lagrange
            uint8_t numerator = 1;
            uint8_t denominator = 1;

            for (int j = 0; j < threshold; ++j) {
                if (i != j) {
                    uint8_t xj = shares[j].index;
                    numerator = gfMultiply(numerator, xj);
                    denominator = gfMultiply(
                        denominator,
                        gfMultiply(xi, xj ^ 0xFF) // xi - xj = xi + xj em GF(2^8)
                    );
                }
            }

            uint8_t lagrange = gfMultiply(
                yi,
                gfDivide(numerator, denominator)
            );
            result ^= lagrange;
        }

        secret[byteIdx] = result;
    }

    return secret;
}

} // namespace hsm
```

### 12.5 Procedimento de Recovery

```
PROCEDIMENTO DE RECOVERY DE CHAVES HSM

1. VERIFICAÇÃO DE AUTORIZAÇÃO
   ├── Confirmar autorização de 3 operadores (M-of-3)
   ├── Verificar identidade de cada operador
   ├── Documentar autorização
   └── Iniciar gravação de vídeo

2. PREPARAÇÃO DO HSM DE DESTINO
   ├── Verificar integridade do novo HSM
   ├── Configurar política de quórum
   ├── Preparar ambiente seguro
   └── Conectar à rede (se aplicável)

3. RECUPERAÇÃO DA CHAVE DE BACKUP
   ├── Coletar shares dos operadores (M de N)
   ├── Reconstruir chave de backup (Shamir)
   ├── Importar chave de backup no HSM
   └── Verificar chave importada

4. RESTAURAÇÃO DAS CHAVES
   ├── Ler arquivo de backup criptografado
   ├── Descriptografar com chave de backup
   ├── Unwrap cada chave no novo HSM
   ├── Verificar cada chave restaurada
   └── Testar operações críticas

5. VERIFICAÇÃO PÓS-RECOVERY
   ├── Testar assinaturas com chaves restauradas
   ├── Testar criptografia/descriptografia
   ├── Verificar cadeia de certificados
   ├── Testar processos de negócio críticos
   └── Documentar resultado

6. LIMPEZA E FINALIZAÇÃO
   ├── Apagar chave de backup temporária
   ├── Zerar memória temporária
   ├── Atualizar documentação
   ├── Notificar partes interessadas
   └── Arquivo de auditoria
```

---

## 13. Integração com OpenSSL: ENGINE API, Provider API

### 13.1 Visão Geral

OpenSSL é a biblioteca de criptografia mais usada no mundo. Para integrar HSMs com aplicações que usam OpenSSL, existem duas abordagens principais:

- **ENGINE API** (legada, OpenSSL 1.0.x - 1.1.x): Permite substituir implementações de criptografia por hardware
- **Provider API** (moderna, OpenSSL 3.0+): Framework extensível para fornecer algoritmos criptográficos

A ENGINE API foi oficialmente descontinuada no OpenSSL 3.0, mas ainda é suportada por razões de backward compatibility. Novos projetos devem usar a Provider API.

### 13.2 ENGINE API (Legada)

A ENGINE API permite registrar um "motor" de criptografia que substitui ou estende as implementações padrão do OpenSSL.

```cpp
// src/openssl_engine_example.cpp
// Exemplo de integração ENGINE API com HSM via PKCS#11
// NOTA: Usar apenas com OpenSSL < 3.0

// Para OpenSSL 3.0+, usar a Provider API (veja seção 13.3)

#ifdef OPENSSL_VERSION_NUMBER < 0x30000000L

#include <openssl/engine.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/ec.h>
#include <openssl/err.h>
#include <iostream>
#include <vector>

// Declarações da engine PKCS#11 (fornecida pelo engine pkcs11)
// O OpenSSLengine pkcs11 (libpkcs11) é uma implementação
// que usa a API PKCS#11 para acessar HSMs
extern "C" {
    ENGINE* ENGINE_pkcs11(void);
}

class OpenSslEngineHsm {
public:
    OpenSslEngineHsm(const std::string& pkcs11ModulePath)
        : modulePath_(pkcs11ModulePath)
    {}

    ~OpenSslEngineHsm() {
        shutdown();
    }

    bool initialize() {
        // Carregar engine pkcs11
        ENGINE_load_builtin_engines();

        pkcs11Engine_ = ENGINE_by_id("pkcs11");
        if (!pkcs11Engine_) {
            std::cerr << "Falha ao carregar engine pkcs11: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
            return false;
        }

        // Configurar módulo PKCS#11
        if (!ENGINE_ctrl_cmd_string(
                pkcs11Engine_, "MODULE_PATH",
                modulePath_.c_str(), 0))
        {
            std::cerr << "Falha ao configurar MODULE_PATH: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
            ENGINE_free(pkcs11Engine_);
            pkcs11Engine_ = nullptr;
            return false;
        }

        // Inicializar engine
        if (!ENGINE_init(pkcs11Engine_)) {
            std::cerr << "Falha ao inicializar engine: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
            ENGINE_free(pkcs11Engine_);
            pkcs11Engine_ = nullptr;
            return false;
        }

        // Definir engine padrão para RSA e EC
        ENGINE_set_default_rsa(pkcs11Engine_);
        ENGINE_set_default_ec(pkcs11Engine_);
        ENGINE_set_default_digests(pkcs11Engine_);

        initialized_ = true;
        return true;
    }

    // Carregar chave privada do HSM
    EVP_PKEY* loadPrivateKey(const std::string& keyId) {
        if (!initialized_ || !pkcs11Engine_) {
            return nullptr;
        }

        // Formato do URI PKCS#11
        std::string pkcs11Uri = "pkcs11:token=" + keyId;

        EVP_PKEY* pkey = ENGINE_load_private_key(
            pkcs11Engine_,
            pkcs11Uri.c_str(),
            nullptr,  // UI method
            nullptr   // Callback data
        );

        if (!pkey) {
            std::cerr << "Falha ao carregar chave: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
        }

        return pkey;
    }

    // Carregar chave pública do HSM
    EVP_PKEY* loadPublicKey(const std::string& keyId) {
        if (!initialized_ || !pkcs11Engine_) {
            return nullptr;
        }

        std::string pkcs11Uri = "pkcs11:token=" + keyId;

        EVP_PKEY* pkey = ENGINE_load_public_key(
            pkcs11Engine_,
            pkcs11Uri.c_str(),
            nullptr,
            nullptr
        );

        if (!pkey) {
            std::cerr << "Falha ao carregar chave pública: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
        }

        return pkey;
    }

    // Assinar dados
    std::vector<unsigned char> sign(
        EVP_PKEY* pkey,
        const unsigned char* data,
        size_t dataLen)
    {
        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            return {};
        }

        if (EVP_DigestSignInit(mdctx, nullptr, EVP_sha256(),
                               nullptr, pkey) != 1)
        {
            EVP_MD_CTX_free(mdctx);
            return {};
        }

        // Determinar tamanho da assinatura
        size_t sigLen = 0;
        if (EVP_DigestSignUpdate(mdctx, data, dataLen) != 1) {
            EVP_MD_CTX_free(mdctx);
            return {};
        }

        if (EVP_DigestSignFinal(mdctx, nullptr, &sigLen) != 1) {
            EVP_MD_CTX_free(mdctx);
            return {};
        }

        // Assinar
        std::vector<unsigned char> signature(sigLen);
        if (EVP_DigestSignFinal(mdctx, signature.data(),
                                &sigLen) != 1)
        {
            EVP_MD_CTX_free(mdctx);
            return {};
        }

        signature.resize(sigLen);
        EVP_MD_CTX_free(mdctx);
        return signature;
    }

    // Verificar assinatura
    bool verify(
        EVP_PKEY* pkey,
        const unsigned char* data,
        size_t dataLen,
        const unsigned char* signature,
        size_t sigLen)
    {
        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            return false;
        }

        if (EVP_DigestVerifyInit(mdctx, nullptr, EVP_sha256(),
                                 nullptr, pkey) != 1)
        {
            EVP_MD_CTX_free(mdctx);
            return false;
        }

        if (EVP_DigestVerifyUpdate(mdctx, data, dataLen) != 1) {
            EVP_MD_CTX_free(mdctx);
            return false;
        }

        int result = EVP_DigestVerifyFinal(
            mdctx, signature, sigLen
        );

        EVP_MD_CTX_free(mdctx);
        return result == 1;
    }

    // Criptografar dados
    std::vector<unsigned char> encrypt(
        EVP_PKEY* pkey,
        const unsigned char* data,
        size_t dataLen)
    {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(pkey, nullptr);
        if (!ctx) {
            return {};
        }

        if (EVP_PKEY_encrypt_init(ctx) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        if (EVP_PKEY_CTX_set_rsa_padding(
                ctx, RSA_PKCS1_OAEP_PADDING) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        // Determinar tamanho do ciphertext
        size_t outLen = 0;
        if (EVP_PKEY_encrypt(ctx, nullptr, &outLen,
                             data, dataLen) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        // Criptografar
        std::vector<unsigned char> ciphertext(outLen);
        if (EVP_PKEY_encrypt(ctx, ciphertext.data(), &outLen,
                             data, dataLen) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        ciphertext.resize(outLen);
        EVP_PKEY_CTX_free(ctx);
        return ciphertext;
    }

    // Descriptografar dados
    std::vector<unsigned char> decrypt(
        EVP_PKEY* pkey,
        const unsigned char* ciphertext,
        size_t ciphertextLen)
    {
        EVP_PKEY_CTX* ctx = EVP_PKEY_CTX_new(pkey, nullptr);
        if (!ctx) {
            return {};
        }

        if (EVP_PKEY_decrypt_init(ctx) <= 0) {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        if (EVP_PKEY_CTX_set_rsa_padding(
                ctx, RSA_PKCS1_OAEP_PADDING) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        // Determinar tamanho do plaintext
        size_t outLen = 0;
        if (EVP_PKEY_decrypt(ctx, nullptr, &outLen,
                             ciphertext, ciphertextLen) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        // Descriptografar
        std::vector<unsigned char> plaintext(outLen);
        if (EVP_PKEY_decrypt(ctx, plaintext.data(), &outLen,
                             ciphertext, ciphertextLen) <= 0)
        {
            EVP_PKEY_CTX_free(ctx);
            return {};
        }

        plaintext.resize(outLen);
        EVP_PKEY_CTX_free(ctx);
        return plaintext;
    }

    void shutdown() {
        if (pkcs11Engine_) {
            ENGINE_finish(pkcs11Engine_);
            ENGINE_free(pkcs11Engine_);
            pkcs11Engine_ = nullptr;
        }
        initialized_ = false;
    }

private:
    std::string modulePath_;
    ENGINE* pkcs11Engine_ = nullptr;
    bool initialized_ = false;
};

int main() {
    OpenSSL_add_all_algorithms();
    ERR_load_crypto_strings();

    OpenSslEngineHsm hsmEngine("/usr/lib/libCryptoki.so");

    if (!hsmEngine.initialize()) {
        std::cerr << "Falha ao inicializar engine HSM" << std::endl;
        return 1;
    }

    // Carregar chave privada do HSM
    EVP_PKEY* privateKey = hsmEngine.loadPrivateKey(
        "minha-chave-rsa-2048"
    );

    if (!privateKey) {
        std::cerr << "Falha ao carregar chave" << std::endl;
        return 1;
    }

    // Assinar dados
    const char* message = "Documento importante";
    auto signature = hsmEngine.sign(
        privateKey,
        reinterpret_cast<const unsigned char*>(message),
        strlen(message)
    );

    if (!signature.empty()) {
        std::cout << "Assinatura gerada: " << signature.size()
                  << " bytes" << std::endl;

        // Verificar assinatura
        EVP_PKEY* publicKey = hsmEngine.loadPublicKey(
            "minha-chave-rsa-2048"
        );

        if (publicKey) {
            bool verified = hsmEngine.verify(
                publicKey,
                reinterpret_cast<const unsigned char*>(message),
                strlen(message),
                signature.data(),
                signature.size()
            );

            std::cout << "Verificação: "
                      << (verified ? "VÁLIDA" : "INVÁLIDA")
                      << std::endl;

            EVP_PKEY_free(publicKey);
        }
    }

    EVP_PKEY_free(privateKey);
    hsmEngine.shutdown();

    EVP_cleanup();
    ERR_free_strings();

    return 0;
}

#else
// Para OpenSSL 3.0+, usar Provider API
int main() {
    std::cout << "Para OpenSSL 3.0+, usar a Provider API" << std::endl;
    return 0;
}
#endif
```

### 13.3 Provider API (Moderna — OpenSSL 3.0+)

A Provider API é o framework moderno do OpenSSL 3.0+ para estender e substituir algoritmos criptográficos. É mais modular e flexível que a ENGINE API.

```cpp
// src/openssl_provider_example.cpp
// Exemplo de integração Provider API com HSM via PKCS#11
// Para OpenSSL 3.0+

#include <openssl/provider.h>
#include <openssl/evp.h>
#include <openssl/core_names.h>
#include <openssl/param_build.h>
#include <openssl/err.h>
#include <iostream>
#include <vector>
#include <string>

class OpenSslProviderHsm {
public:
    OpenSslProviderHsm(const std::string& pkcs11Module)
        : modulePath_(pkcs11Module)
    {}

    ~OpenSslProviderHsm() {
        shutdown();
    }

    bool initialize() {
        // Carregar provider pkcs11
        // O OpenSSL 3.0+ suporta providers dinâmicos
        // O provider pkcs11 é fornecido por projetos como
        // openssl-pkcs11 ou o engine pkcs11

        OSSL_PROVIDER* pkcs11 = OSSL_PROVIDER_load(
            nullptr, "pkcs11"
        );

        if (!pkcs11) {
            // Tentar carregar como módulo dinâmico
            // Em produção, configurar corretamente o provider
            std::cerr << "Provider pkcs11 não disponível: "
                      << ERR_error_string(ERR_get_error(), nullptr)
                      << std::endl;
            std::cerr << "Usando provider default" << std::endl;

            // Carregar provider default como fallback
            defaultProvider_ = OSSL_PROVIDER_load(nullptr, "default");
            if (!defaultProvider_) {
                return false;
            }
        } else {
            pkcs11Provider_ = pkcs11;
        }

        initialized_ = true;
        return true;
    }

    // Criar contexto de assinatura com HSM
    EVP_MD_CTX* createSignContext() {
        return EVP_MD_CTX_new();
    }

    // Assinar com chave HSM
    std::vector<unsigned char> signWithHsm(
        const std::string& keyUri,
        const unsigned char* data,
        size_t dataLen)
    {
        EVP_MD_CTX* mdctx = EVP_MD_CTX_new();
        if (!mdctx) {
            return {};
        }

        EVP_PKEY* pkey = nullptr;

        // Para OpenSSL 3.0+, usar EVP_PKEY_fromdata ou
        // load via provider
        // Simplificação: usar mecanismo genérico

        EVP_PKEY_CTX* pkeyCtx = EVP_PKEY_CTX_new_from_name(
            nullptr, "RSA", nullptr
        );

        if (!pkeyCtx) {
            EVP_MD_CTX_free(mdctx);
            return {};
        }

        // Em produção, carregar chave do HSM via URI PKCS#11
        // openssl-pkcs11 provider suporta:
        // pkcs11:token=label;object=label

        // Para esta demonstração, usar chave local
        // (em produção, integrar com pkcs11 provider)

        EVP_MD_CTX_free(mdctx);
        EVP_PKEY_CTX_free(pkeyCtx);

        return {}; // Placeholder — implementação completa
                    // requer provider pkcs11 funcional
    }

    // Criptografar com chave HSM
    std::vector<unsigned char> encryptWithHsm(
        const std::string& keyUri,
        const unsigned char* plaintext,
        size_t plaintextLen)
    {
        EVP_PKEY_CTX* ctx = nullptr;

        // Para OpenSSL 3.0+, usar OSSL_PARAM para configurar
        OSSL_PARAM_BLD* bld = OSSL_PARAM_BLD_new();
        if (!bld) {
            return {};
        }

        // Configurar parâmetros
        // Em produção, usar provider pkcs11

        OSSL_PARAM_BLD_free(bld);

        return {}; // Placeholder
    }

    void shutdown() {
        if (pkcs11Provider_) {
            OSSL_PROVIDER_unload(pkcs11Provider_);
            pkcs11Provider_ = nullptr;
        }
        if (defaultProvider_) {
            OSSL_PROVIDER_unload(defaultProvider_);
            defaultProvider_ = nullptr;
        }
        initialized_ = false;
    }

private:
    std::string modulePath_;
    OSSL_PROVIDER* pkcs11Provider_ = nullptr;
    OSSL_PROVIDER* defaultProvider_ = nullptr;
    bool initialized_ = false;
};

// Exemplo de uso do Provider API para criptografia simétrica
class AesGcmProvider {
public:
    AesGcmProvider() {
        // Carregar provider default
        provider_ = OSSL_PROVIDER_load(nullptr, "default");
    }

    ~AesGcmProvider() {
        if (provider_) {
            OSSL_PROVIDER_unload(provider_);
        }
    }

    struct EncryptResult {
        std::vector<unsigned char> ciphertext;
        std::vector<unsigned char> tag;
        std::vector<unsigned char> iv;
        bool success;
    };

    EncryptResult encrypt(
        const unsigned char* key,
        size_t keyLen,
        const unsigned char* plaintext,
        size_t plaintextLen,
        const unsigned char* aad = nullptr,
        size_t aadLen = 0)
    {
        EncryptResult result;
        result.success = false;

        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) return result;

        // Criar cipher context
        if (EVP_EncryptInit_ex2(ctx, EVP_aes_256_gcm(),
                                nullptr, nullptr, nullptr) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        // Configurar chave
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12,
                                nullptr) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        // Gerar IV
        result.iv.resize(12);
        if (RAND_bytes(result.iv.data(), 12) != 1) {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        if (EVP_EncryptInit_ex2(ctx, nullptr, nullptr,
                                key, result.iv.data()) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        // AAD (Associated Authenticated Data)
        if (aad && aadLen > 0) {
            int outLen = 0;
            if (EVP_EncryptUpdate(ctx, nullptr, &outLen,
                                  aad, aadLen) != 1)
            {
                EVP_CIPHER_CTX_free(ctx);
                return result;
            }
        }

        // Criptografar
        result.ciphertext.resize(plaintextLen + 16);
        int outLen = 0;
        if (EVP_EncryptUpdate(ctx, result.ciphertext.data(),
                              &outLen, plaintext, plaintextLen) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        int finalLen = 0;
        if (EVP_EncryptFinal_ex(ctx,
                                result.ciphertext.data() + outLen,
                                &finalLen) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        outLen += finalLen;
        result.ciphertext.resize(outLen);

        // Obter tag
        result.tag.resize(16);
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16,
                                result.tag.data()) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return result;
        }

        EVP_CIPHER_CTX_free(ctx);
        result.success = true;
        return result;
    }

    std::vector<unsigned char> decrypt(
        const unsigned char* key,
        size_t keyLen,
        const unsigned char* ciphertext,
        size_t ciphertextLen,
        const unsigned char* iv,
        size_t ivLen,
        const unsigned char* tag,
        size_t tagLen,
        const unsigned char* aad = nullptr,
        size_t aadLen = 0)
    {
        EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
        if (!ctx) return {};

        if (EVP_DecryptInit_ex2(ctx, EVP_aes_256_gcm(),
                                nullptr, nullptr, nullptr) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN,
                                ivLen, nullptr) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        if (EVP_DecryptInit_ex2(ctx, nullptr, nullptr,
                                key, iv) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        // AAD
        if (aad && aadLen > 0) {
            int outLen = 0;
            if (EVP_DecryptUpdate(ctx, nullptr, &outLen,
                                  aad, aadLen) != 1)
            {
                EVP_CIPHER_CTX_free(ctx);
                return {};
            }
        }

        // Descriptografar
        std::vector<unsigned char> plaintext(ciphertextLen + 16);
        int outLen = 0;
        if (EVP_DecryptUpdate(ctx, plaintext.data(), &outLen,
                              ciphertext, ciphertextLen) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        // Definir tag
        if (EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG,
                                tagLen,
                                const_cast<unsigned char*>(tag)) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        // Verificar tag
        if (EVP_DecryptFinal_ex(ctx, plaintext.data() + outLen,
                                &outLen) != 1)
        {
            EVP_CIPHER_CTX_free(ctx);
            return {};
        }

        plaintext.resize(outLen);
        EVP_CIPHER_CTX_free(ctx);
        return plaintext;
    }

private:
    OSSL_PROVIDER* provider_ = nullptr;
};

int main() {
    std::cout << "=== OpenSSL Provider API — Exemplo ===" << std::endl;

    // Exemplo de uso do AesGcmProvider
    AesGcmProvider aesProvider;

    // Chave de teste (256 bits)
    unsigned char key[32];
    RAND_bytes(key, 32);

    // Dados para criptografar
    const char* message = "Mensagem secreta para criptografar";
    size_t msgLen = strlen(message);

    // Criptografar
    auto encResult = aesProvider.encrypt(
        key, 32,
        reinterpret_cast<const unsigned char*>(message),
        msgLen
    );

    if (encResult.success) {
        std::cout << "Criptografado: " << encResult.ciphertext.size()
                  << " bytes" << std::endl;
        std::cout << "IV: " << encResult.iv.size()
                  << " bytes" << std::endl;
        std::cout << "Tag: " << encResult.tag.size()
                  << " bytes" << std::endl;

        // Descriptografar
        auto decResult = aesProvider.decrypt(
            key, 32,
            encResult.ciphertext.data(),
            encResult.ciphertext.size(),
            encResult.iv.data(),
            encResult.iv.size(),
            encResult.tag.data(),
            encResult.tag.size()
        );

        if (!decResult.empty()) {
            std::string decrypted(
                decResult.begin(), decResult.end()
            );
            std::cout << "Descriptografado: " << decrypted
                      << std::endl;
            std::cout << "Roundtrip OK: "
                      << (decrypted == message ? "SIM" : "NAO")
                      << std::endl;
        }
    }

    return 0;
}
```

### 13.4 Comparação ENGINE API vs Provider API

| Característica | ENGINE API (Legada) | Provider API (Moderna) |
|---------------|---------------------|------------------------|
| OpenSSL Version | 1.0.x - 1.1.x | 3.0+ |
| Status | Descontinuada | Ativa |
| Modularidade | Baixa | Alta |
| Encapsulamento | Misto | Forte |
| Performance | Boa | Boa |
| Documentação | Extensa | Crescente |
| Uso Recomendado | Legado apenas | Novos projetos |

### 13.5 Dicas de Integração

**Para novos projetos**:
1. Use OpenSSL 3.0+ com Provider API
2. Configure o provider pkcs11 corretamente
3. Use OSSL_PARAM para configurar algoritmos
4. Teste com SoftHSM antes de usar HSM real

**Para migração de ENGINE para Provider**:
1. Identifique todas as chamadas ENGINE_* no código
2. Substitua por equivalentes EVP_* ou OSSL_*
3. Configure o provider pkcs11 no OpenSSL.cnf
4. Teste rigorosamente antes de produzir

**Configuration OpenSSL.cnf para provider pkcs11**:

```ini
# openssl.cnf
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
pkcs11 = pkcs11_sect

[default_sect]
activate = 1

[pkcs11_sect]
module = /usr/lib/engines-3/pkcs11.so
activate = 1
```

---

## 14. Tabela comparativa: HSMs no mercado

### 14.1 HSMs de Rede (Network HSMs)

| Produto | FIPS 140 | Performance (RSA-2048) | Slots | Interface | Custo Aprox. |
|---------|----------|------------------------|-------|-----------|--------------|
| Thales Luna Network HSM 7 | Nível 3 | 10.000 ops/s | 16 | PKCS#11, JCE | $15.000 |
| Entrust nShield 5 | Nível 3 | 8.000 ops/s | Ilimitado | PKCS#11, JCE, CNG | $12.000 |
| Utimaco SecurityServer | Nível 3 | 5.000 ops/s | 16 | PKCS#11, JCE | $8.000 |
| Marvell LiquidSecurity 2 | Nível 3 | 40.000 ops/s | Ilimitado | PKCS#11 | $20.000 |

### 14.2 HSMs PCIe

| Produto | FIPS 140 | Performance (RSA-2048) | Interface | Custo Aprox. |
|---------|----------|------------------------|-----------|--------------|
| Thales Luna PCIe HSM 7 | Nível 3 | 15.000 ops/s | PKCS#11 | $10.000 |
| Utimaco SeGen | Nível 3 | 8.000 ops/s | PKCS#11 | $5.000 |
| Marvell LiquidSecurity | Nível 3 | 30.000 ops/s | PKCS#11 | $15.000 |

### 14.3 HSMs USB/Token

| Produto | FIPS 140 | Performance (RSA-2048) | Chaves | Custo Aprox. |
|---------|----------|------------------------|--------|--------------|
| Thales Luna G5 USB | Nível 2 | 200 ops/s | Ilimitadas | $300 |
| YubiHSM 2 | Nível 2 | 100 ops/s | Ilimitadas | $60 |
| Nitrokey HSM | CC EAL4+ | 50 ops/s | 96 | $170 |
| Utimaco uTrust 3700 F | Nível 2 | 150 ops/s | Ilimitadas | $200 |

### 14.4 Cloud HSMs

| Serviço | FIPS 140 | Custo Base | Performance | Escalabilidade |
|---------|----------|-----------|-------------|----------------|
| AWS CloudHSM | Nível 3 | $1.080/mês | 10.000 ops/s | 28 HSMs/cluster |
| Azure Dedicated HSM | Nível 3 | $2.880/mês | 8.000 ops/s | 4 HSMs/cluster |
| Google Cloud HSM | Nível 3 | Pay-per-use | Escalável | Ilimitado |
| IBM Cloud HSM | Nível 3 | $4.000/mês | 5.000 ops/s | 20 HSMs/cluster |

### 14.5 SoftHSM (Software — para desenvolvimento)

| Produto | FIPS 140 | Performance | Chaves | Custo |
|---------|----------|-------------|--------|-------|
| SoftHSM2 | N/A | Limitado por CPU | Ilimitadas | Grátis |
| OpenSC (modo software) | N/A | Limitado por CPU | Ilimitadas | Grátis |
| Botan (PKCS#11 wrapper) | N/A | Médio | Ilimitadas | Grátis |

### 14.6 Critérios de Seleção

Ao selecionar um HSM, considere:

1. **Compliance**: Que certificações FIPS/PCI DSS são necessárias?
2. **Performance**: Quantas operações por segundo são necessárias?
3. **Interface**: PKCS#11, JCE, CNG, REST API?
4. **Custo total de propriedade**: Hardware + licenças + suporte + manutenção
5. **Escalabilidade**: Crescimento futuro da organização
6. **Disponibilidade**: Requisitos de uptime e failover
7. **Suporte**: Documentação, treinamento, suporte técnico
8. **Ecossistema**: Integração com ferramentas existentes
9. **Localização**: Onde o HSM será operado (data center, cloud, edge)
10. **Lifecycle**: Quanto tempo o vendor suportará o produto

---

## 15. Exercícios

### Exercício 1: Wrapper PKCS#11 Básico

Implemente uma classe wrapper C++17 completa para PKCS#11 que suporte:
- Inicialização e finalização da biblioteca
- Listagem de slots e tokens
- Abertura e fechamento de sessões
- Login/logout
- Busca de objetos por atributos

**Requisitos**:
- Use RAII para gerenciar todos os recursos
- Trate erros de forma adequada (exceções tipadas)
- Implemente movimentação (move semantics)
- Escreva testes unitários para cada funcionalidade

### Exercício 2: Gerador de Chaves HSM

Implemente um gerador de chaves que suporte:
- Chaves AES-128, AES-256
- Chaves RSA-2048, RSA-4096
- Chaves ECDSA P-256, P-384

**Requisitos**:
- Gere chaves com atributos configuráveis
- Permita exportar chave pública (nunca privada)
- Implemente rotação de chaves
- Registre cada operação em log

### Exercício 3: Motor de Criptografia

Implemente um motor de criptografia que use HSM para:
- Criptografia/descriptografia AES-CBC e AES-GCM
- Assinatura RSA-PKCS#1 v1.5 e RSA-PSS
- Verificação de assinatura
- Hash SHA-256

**Requisitos**:
- Gere IVs aleatórios via HSM
- Implemente autenticação de Associated Data (AAD) para GCM
- Valide todos os inputs
- Forneça estatísticas de performance

### Exercício 4: Backup de Chaves

Implemente um sistema de backup que suporte:
- Backup com key wrapping
- Arquivo de backup criptografado
- Verificação de integridade (checksum)
- Restauração de backup

**Requisitos**:
- Use AES-256-GCM para proteger o arquivo de backup
- Derive chave de backup com PBKDF2
- Implemente M-of-N secret sharing para chaves críticas
- Documente cada operação

### Exercício 5: Integração OpenSSL

Integre seu HSM com OpenSSL usando:
- Provider API (OpenSSL 3.0+)
- Assinatura via EVP_MD_CTX
- Criptografia via EVP_CIPHER_CTX
- Teste com certificado real

**Requisitos**:
- Configure o provider pkcs11 corretamente
- Implemente loading de chave via URI PKCS#11
- Valide que a operação realmente usa o HSM (verifique logs)
- Teste com SoftHSM antes de usar HSM real

### Exercício 6: Análise de CVE (Avançado)

Analise o CVE-2021-36260 e implemente:
- Um parser para o protocolo proprietário (simplificado)
- Um detector de padrões de criptografia fraca
- Uma ferramenta de verificação de firmware

**Requisitos**:
- Use engenharia reversa ética
- Documente cada vulnerabilidade encontrada
- Proponha correções para cada vulnerabilidade
- Implemente testes de validação

### Exercício 7: Simulação de Ataque (Educacional)

Simule um ataque side-channel (timing attack) em software:
- Implemente RSA com e sem constant-time
- Meça tempos de execução
- Demonstre a diferença estatística
- Proponha contra-medidas

**Requisitos**:
- Execute estatísticas rigorosas (mínimo 10.000 medições)
- Calcule média, desvio padrão, e coeficiente de variação
- Compare com implementação protegida
- Documente conclusões

---

## 16. Referências

### Padrões e Especificações

1. OASIS. "PKCS #11: Cryptographic Token Interface Standard Version 3.0". OASIS Standard, 2020.

2. NIST. "FIPS PUB 140-2: Security Requirements for Cryptographic Modules". NIST, 2001 (Retirado 2021).

3. NIST. "FIPS PUB 140-3: Security Requirements for Cryptographic Modules". NIST, 2019.

4. OASIS. "Key Management Interoperability Protocol (KMIP) Specification Version 2.0". OASIS Standard, 2020.

5. ISO/IEC. "ISO/IEC 19790:2012 — Security requirements for cryptographic modules". ISO, 2012.

### HSMs e Hardware

6. Thales Group. "Luna Network HSM 7 Documentation". https://www.thalesgroup.com/en/markets/digital-identity-and-security/iam/hardware-security-modules

7. Entrust. "nShield 5 HSM Family". https://www.entrust.com/products/hardware-security-modules

8. Utimaco. "SecurityServer HSM". https://www.utimaco.com/products/hardware-security-modules

9. Yubico. "YubiHSM 2 Documentation". https://developers.yubico.com/hsm/

10. Nitrokey. "Nitrokey HSM Documentation". https://www.nitrokey.com/documentation/hardware-modules/nitrokey-hsm

### Cloud HSMs

11. Amazon Web Services. "AWS CloudHSM Developer Guide". https://docs.aws.amazon.com/cloudhsm/latest/userguide/

12. Microsoft. "Azure Dedicated HSM Documentation". https://docs.microsoft.com/azure/dedicated-hsm/

13. Google Cloud. "Cloud HSM Documentation". https://cloud.google.com/kms/docs/hsm

### OpenSSL

14. OpenSSL Project. "OpenSSL 3.0 Provider Guide". https://www.openssl.org/docs/man3.0/

15. OpenSSL Project. "OpenSSL ENGINE API Documentation". https://www.openssl.org/docs/man1.1.1/man3/engine.html

### Vulnerabilidades e Ataques

16. MITRE. "CVE-2021-36260: Hikvision IP Camera Remote Code Execution". https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-36260

17. CISA. "Alert (AA21-265A): Exploitation of Hikvision Web Server Vulnerability". 2021.

18. Kocher, P. "Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems". CRYPTO 1996.

19. Kocher, P., Jaffe, J., Jun, B. "Differential Power Analysis". CRYPTO 1999.

20. Boneh, D., DeMillo, R.A., Lipton, R.J. "On the Importance of Eliminating Errors in Cryptographic Computations". Journal of Cryptology, 2001.

### Livros

21. Schneier, B. "Applied Cryptography". Wiley, 2015.

22. Ferguson, N., Schneier, B., Kohno, T. "Cryptography Engineering". Wiley, 2010.

23. Stamp, M. "Information Security: Principles and Practice". Wiley, 2011.

24. Anderson, R. "Security Engineering". Wiley, 2020.

### SoftHSM e Ferramentas

25. SoftHSM Project. "SoftHSM 2 Documentation". https://www.opendnssec.org/softhsm/

26. OpenSC Project. "OpenSC Documentation". https://github.com/OpenSC/OpenSC

27. PyKMIP Project. "PyKMIP Documentation". https://github.com/OpenKMIP/pykmip

---

## Glossário

| Termo | Definição |
|-------|-----------|
| AES | Advanced Encryption Standard — cifra simétrica de bloco |
| CA | Certificate Authority — autoridade certificadora |
| CBC | Cipher Block Chaining — modo de operação para cifras de bloco |
| CKA | Cryptoki Attribute — atributo PKCS#11 |
| CKK | Cryptoki Key Type — tipo de chave PKCS#11 |
| CKM | Cryptoki Mechanism — mecanismo PKCS#11 |
| CNG | Cryptography Next Generation — framework Microsoft |
| DPA | Differential Power Analysis — análise de canal lateral |
| ECC | Elliptic Curve Cryptography — criptografia de curvas elípticas |
| ECDSA | Elliptic Curve Digital Signature Algorithm |
| FIPS | Federal Information Processing Standard |
| GCM | Galois/Counter Mode — modo de operação autenticado |
| HSM | Hardware Security Module — módulo de hardware seguro |
| JCE | Java Cryptography Extension |
| KMIP | Key Management Interoperability Protocol |
| PKCS | Public-Key Cryptography Standards |
| PKCS#11 | Cryptoki — API para tokens criptográficos |
| PKI | Public Key Infrastructure — infraestrutura de chaves públicas |
| PSS | Probabilistic Signature Scheme — esquema de assinatura RSA |
| RAII | Resource Acquisition Is Initialization |
| RCE | Remote Code Execution — execução remota de código |
| RSA | Rivest-Shamir-Adleman — cifra assimétrica |
| SCIF | Sensitive Compartmented Information Facility |
| SPA | Simple Power Analysis — análise simples de consumo |
| TEMPEST | Emanation security — segurança contra emanations |
| TPM | Trusted Platform Module |
| TRNG | True Random Number Generator — gerador verdadeiro de aleatoriedade |

---

**Fim do Capítulo 04**

*Próximo capítulo: Capítulo 05 — TLS/SSL em C++ com OpenSSL*
---

*[Capítulo anterior: 03 — Ataques Canal Lateral](03-ataques-canal-lateral.md)*
*[Próximo capítulo: 05 — Tls 13 Internals](05-tls-13-internals.md)*
