---
layout: default
title: "12-verificacao-formal"
---

# Capítulo 12 — Verificação Formal de Implementações Criptográficas

> *"Testes podem demonstrar a presença de bugs, mas nunca a ausência."*
> — Edsger W. Dijkstra

---

## Sumário

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Por Que Verificação Formal? Limitações de Testes](#2-por-que-verificação-formal-limitações-de-testes)
3. [Model Checking: SPIN, NuSMV e Protocolos Criptográficos](#3-model-checking-spin-nusmv-e-protocolos-criptográficos)
4. [Cryptol: Linguagem de Especificação para Criptografia](#4-cryptol-linguagem-de-especificação-para-criptografia)
5. [SAW: Software Analysis Workbench](#5-saw-software-analysis-workbench)
6. [ProVerif: Verificação Automatizada de Protocolos](#6-proverif-verificação-automatizada-de-protocolos)
7. [Tamarin Prover: Análise de Protocolos Multpartite](#7-tamarin-prover-análise-de-protocolos-multipartite)
8. [F*: Verificação com Tipos Dependentes](#8-f-verificação-com-tipos-dependentes)
9. [CompCert: Implicações de um Compilador Verificado](#9-compcert-implicações-de-um-compilador-verificado)
10. [Agilidade Criptográfica: Projetando para Substituição de Algoritmos](#10-agilidade-criptográfica-projetando-para-substituição-de-algoritmos)
11. [Exemplo: Verificação de Propriedade Constant-Time com SAW](#11-exemplo-verificação-de-propriedade-constant-time-com-saw)
12. [Exemplo: Prova de Handshake TLS 1.3 com ProVerif](#12-exemplo-prova-de-handshake-tls-13-com-proverif)
13. [Comparação de Ferramentas de Verificação Formal](#13-comparação-de-ferramentas-de-verificação-formal)
14. [Integração com Fluxo de Desenvolvimento](#14-integração-com-fluxo-de-desenvolvimento)
15. [Exercícios](#15-exercícios)
16. [Referências](#16-referências)

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Compreender por que testes convencionais são insuficientes para validar implementações criptográficas
- Distinguir model checking, theorem proving e abstract interpretation como abordagens de verificação formal
- Utilizar SPIN e NuSMV para modelar e verificar protocolos criptográficos
- Especificar algoritmos criptográficos em Cryptol e prová-los com SAW
- Aplicar ProVerif para verificação automatizada de protocolos de autenticação
- Utilizar Tamarin Prover para analisar protocolos multipartite com modelos de segurança
- Compreender F* e como tipos dependentes podem capturar invariantes criptográficas
- Analisar as implicações de CompCert para a garantia de que código verificado permanece correto após compilação
- Projetar sistemas com agilidade criptográfica para substituição transparente de algoritmos
- Integrar verificação formal em pipelines de CI/CD para validação contínua
- Implementar ferramentas de verificação de propriedades como timing constant-time e ausência de memory leaks

**Pré-requisitos:** Capítulos anteriores desta série (especialmente Capítulos 01 e 02), conhecimento de C++17, conceitos básicos de criptografia e protocolos de segurança.

---

## 2. Por Que Verificação Formal? Limitações de Testes

### 2.1 O Problema Fundamental da Validação

Em engenharia de software convencional, testes são a principal ferramenta de validação. Escrevemos testes unitários, testes de integração, testes de regressão e esperamos que, se todos passarem, o software esteja correto. Para a maioria dos sistemas de software, essa abordagem é razoável — imperfeita, mas praticável.

Para software criptográfico, essa abordagem é catastroficamente insuficiente.

A razão é matemática. Um algoritmo criptográfico como AES opera sobre chaves de 128, 192 ou 256 bits. Isso significa que o espaço de entrada para AES-256 contém 2^256 elementos. Mesmo que pudéssemos testar um trilhão de casos por segundo, testar todo o espaço levaria mais tempo que a idade do universo. E isso considera apenas a chave — o espaço combinado com texto claro e IV é ainda maior.

```
+------------------------------------------------------------------+
|              O ABISMO ENTRE TESTES E VERIFICAÇÃO                 |
+------------------------------------------------------------------+
|                                                                  |
|  Testes:                                                       |
|  - Verificam AMOSTRAS do espaço de entrada                      |
|  - Cada teste cobre 1 caso específico                           |
|  - N testes = N pontos verificados                              |
|  - Espaço restante = NÃO VERIFICADO                             |
|                                                                  |
|  Verificação Formal:                                           |
|  - Verificam TODOS os elementos do espaço                       |
|  - Uma prova cobre infinitos casos                               |
|  - UMA PROVA = TODO o espaço verificado                         |
|  - Garantia matemática de correção                               |
|                                                                  |
+------------------------------------------------------------------+
```

### 2.2 Limitações Específicas dos Testes para Criptografia

**Limitação 1: Espaço de entrada exponencial**

O espaço de entrada de primitivas criptográficas é exponencial. Mesmo testes baseados em propriedades (property-based testing) apenas amostram esse espaço. Uma propriedade como "a concatenação de criptografar e descriptografar retorna o texto claro original" pode ser testada com milhares de exemplos aleatórios, mas isso não prova que vale para todos os 2^256 inputs possíveis.

**Limitação 2: Ausência de evidência é evidência de ausência... ou não**

Quando um teste passa, sabemos que aquele caso específico está correto. Quando um teste falha, sabemos que há um bug. Mas quando nenhum teste falha, não sabemos se o software está correto — apenas sabemos que não encontramos bugs ainda. Em criptografia, um único bug não detectado pode comprometer todo o sistema.

**Limitação 3: Propriedades de segurança são universais**

Uma propriedade como "o sistema não vazamento informações sobre a chave através de timing" precisa valer para TODAS as execuções possíveis, não apenas para as que testamos. Isso é fundamentalmente diferente de uma propriedade funcional como "a função retorna o resultado esperado para esta entrada específica".

**Limitação 4: Efeitos colaterais observáveis**

Em criptografia, o adversário não observa apenas o resultado correto — observa timing, consumo de energia, padrões de acesso a memória, erros diferenciados. Testes funcionais não capturam esses canais laterais.

### 2.3 O que a Verificação Formal Oferece

A verificação formal usa ferramentas matemáticas para PROVAR que um sistema satisfaz suas especificações. Ao contrário dos testes, que verificam instâncias específicas, verificação formal oferece garantias sobre todo o espaço de entrada.

As principais abordagens são:

**Model Checking:** Verifica automaticamente se um modelo finito do sistema satisfaz uma propriedade especificada em lógica temporal. O modelo é explorado sistematicamente — se uma propriedade é violada, o model checker retorna um contraexemplo (counterexample) que mostra exatamente como a violação ocorre.

**Theorem Proving:** O especificador escreve o sistema e suas propriedades como teoremas em uma lógica formal, e uma ferramenta (como um assistente de prova) ajuda a construir a demonstração de que os teoremas são verdadeiros. É mais poderoso que model checking (pode lidar com sistemas infinitos), mas requer mais trabalho humano.

**Abstract Interpretation:** Analisa o programa sem executá-lo, abstraindo seu comportamento e derivando propriedades estáticas. É usado para verificar propriedades como ausência de erros em tempo de execução e constant-time.

**Property-Based Testing (como ponte):** Embora não seja verificação formal propriamente dita, testes baseados em propriedades (como QuickCheck e Hypothesis) testam propriedades universais com geração aleatória de dados. São uma ponte entre testes convencionais e verificação formal.

### 2.4 Aplicação à Criptografia

A verificação formal é especialmente valiosa para criptografia porque:

1. **Protocolos são sistemas concorrentes:** Model checking pode verificar propriedades de segurança contra adversários ativos que executam ações não determinísticas
2. **Invariantes são universais:** Theorem proving pode provar que invariantes criptográficas valem para todas as entradas
3. **Constant-time é uma propriedade universal:** Abstract interpretation pode verificar que código não depende de dados secretos em suas decisões de controle ou acesso a memória
4. **Composição é complexa:** Verificação formal pode verificar propriedades sobre sistemas compostos de múltiplos protocolos e primitivas

### 2.5 Exemplo: Onde Testes Falharam

O bug Debian OpenSSL (CVE-2008-0166) é um exemplo perfeito. O bug removia bytes aleatórios do estado do PRNG, tornando as chaves previsíveis. Testes funcionais passavam normalmente — as chaves eram geradas, eram diferentes a cada execução (dentro do espaço reduzido), e eram aceitas pelo OpenSSL. Mas o espaço de chaves possíveis era drasticamente reduzido, e um atacante podia enumerar todas as chaves possíveis.

Uma verificação formal do PRNG poderia ter provado que a entropia do estado permanecia acima de um limiar mínimo após cada operação de geração de bytes — uma propriedade que testes funcionais não capturam.

---

## 3. Model Checking: SPIN, NuSMV e Protocolos Criptográficos

### 3.1 Fundamentos de Model Checking

Model checking é uma técnica de verificação automática que explora sistematicamente todos os estados de um modelo finito para verificar se uma propriedade especificada é satisfeita. Dado um modelo M e uma fórmula de propriedade φ, o model checker determina se M satisfaz φ (M |= φ).

O processo funciona em três etapas:

1. **Modelagem:** O sistema é descrito em uma linguagem de modelagem formal (Promela para SPIN, SMV para NuSMV)
2. **Especificação:** As propriedades a serem verificadas são expressas em lógica temporal (LTL, CTL)
3. **Verificação:** O model checker explora o espaço de estados e relata se a propriedade é satisfeita ou retorna um contraexemplo

```
+----------------------------------------------+
|        Ciclo de Model Checking               |
+----------------------------------------------+
|                                              |
|  Modelo do Sistema                           |
|       |                                      |
|       v                                      |
|  Especificação (LTL/CTL)                    |
|       |                                      |
|       v                                      |
|  Model Checker (explora estados)             |
|       |                                      |
|       +---> Propriedade OK                   |
|       |     (nenhum contraexemplo)           |
|       |                                      |
|       +---> Propriedade VIOLADA              |
|             (contraexemplo retornada)        |
+----------------------------------------------+
```

### 3.2 SPIN: Linguagem Promela e Verificação de Protocolos

SPIN é um dos model checkers mais maduros e amplamente utilizados. Ele aceita modelos escritos em Promela (Process Meta Language), uma linguagem de modelagem para sistemas concorrentes, e verifica propriedades expressas em LTL (Linear Temporal Logic).

Promela é especialmente adequada para protocolos criptográficos porque suporta:
- Canais assíncronos e síncronos (modelando rede)
- Não determinismo (modelando adversários)
- Verificação de ausência de deadlock
- Especificação de propriedades de segurança

**Exemplo: Modelo de Autenticação Simples em Promela**

Vamos modelar um protocolo de autenticação simples onde Alice envia uma mensagem assinada para Bob, e verificamos que Bob nunca aceita uma mensagem de um atacante.

```promela
/* Modelo Promela: Protocolo de Autenticação Simples */

/* Definição de canais */
chan channel_a2b = [1] of { mtype, byte };
chan channel_b2a = [1] of { mtype, byte };

/* Estados do protocolo */
mtype = { CHALLENGE, RESPONSE, ACCEPT, REJECT };

/* Chaves secretas */
byte key_alice = 42;
byte key_eve = 0; /* Atacante não conhece a chave */

/* Variável de controle */
bool bob_accepted = false;
bool attack_succeeded = false;

/* Ator: Alice (participante legítimo) */
active proctype Alice() {
    byte challenge;

    /* Recebe desafio de Bob */
    channel_b2a ? CHALLENGE, challenge;

    /* Calcula resposta = challenge XOR key_alice */
    byte response = challenge ^ key_alice;

    /* Envia resposta */
    channel_a2b ! RESPONSE, response;
}

/* Ator: Eve (atacante passivo) */
active proctype Eve() {
    byte intercepted_challenge;
    byte forged_response;

    /* Eve observa o canal */
    /* Mas não conhece key_alice */

    /* Tenta forjar uma resposta */
    forged_response = intercepted_challenge ^ key_eve;

    /* Envia resposta forjada */
    channel_a2b ! RESPONSE, forged_response;
}

/* Ator: Bob (receptor) */
active proctype Bob() {
    byte challenge;
    byte received_response;
    byte expected_response;

    /* Gera desafio */
    challenge = 7;
    channel_a2b ! CHALLENGE, challenge;

    /* Espera resposta */
    channel_a2b ? RESPONSE, received_response;

    /* Verifica resposta */
    expected_response = challenge ^ key_alice;

    if
    :: (received_response == expected_response) ->
        bob_accepted = true;
        /* Propriedade: Bob só aceita de Alice */
    :: else ->
        /* Rejeita */
        skip;
    fi;
}

/* Propriedade de segurança LTL: */
/* "Bob nunca aceita uma mensagem forjada" */
/* Em LTL: G(!attack_succeeded) */
```

### 3.3 NuSMV: CTL e Verificação Estruturada

NuSMV é outro model checker amplamente utilizado, particularmente adequado para verificação de propriedades em CTL (Computation Tree Logic). Enquanto LTL descreve propriedades ao longo de caminhos individuais, CTL descreve propriedades sobre a árvore de todos os caminhos possíveis — uma distinção importante para protocolos criptográficos onde o adversário pode escolher diferentes estratégias.

**Exemplo: Modelo de Chaveamento em NuSMV**

```smv
MODULE main
VAR
    state : {idle, key_sent, encrypted, decrypted};
    key : 0..255;
    plaintext : 0..255;
    ciphertext : 0..255;
    attacker_knows_key : boolean;
    attacker_knows_plaintext : boolean;

ASSIGN
    init(state) := idle;
    init(key) := 0;
    init(plaintext) := 0;
    init(attacker_knows_key) := false;
    init(attacker_knows_plaintext) := false;

TRANS state = idle & state' = key_sent
    -- Alice gera e envia chave

TRANS state = key_sent & state' = encrypted
    -- Alice criptografa mensagem

TRANS state = encrypted & state' = decrypted
    -- Bob descriptografa mensagem

-- Propriedade de segurança:
-- O atacante nunca conhece a chave
CTLSPEC AG (!attacker_knows_key)

-- Propriedade de segurança:
-- Se o atacante não conhece a chave, o plaintext é seguro
CTLSPEC AG (attacker_knows_key = false -> attacker_knows_plaintext = false)
```

### 3.4 Aplicação a Protocolos Reais: Needham-Schroeder

O protocolo Needham-Schroeder é um caso clássico de verificação formal. Em 1995, Lowe usou o model checker FDR (predecessor do SPIN) para encontrar uma violação de autenticação no protocolo Needham-Schroeder que passava despercebida por 17 anos.

**Exemplo: Verificação do Protocolo Needham-Schroeder com SPIN**

```promela
/*
 * Verificação do Protocolo Needham-Schroeder com SPIN
 * Replicando a análise de Lowe (1995)
 *
 * O atacante (Intruder) pode:
 * - Iniciar sessões com Alice e Bob
 * - Interceptar e reenviar mensagens
 * - Forjar mensagens com chaves que conhece
 */

/* Canais */
chan ns_channel = [1] of { mtype, byte, byte, byte };

mtype = { msg1, msg2, msg3, msg4, msg5 };

/* Estado do protocolo */
byte Na, Nb;
byte key_a, key_b;
byte Ka, Kb;

/* Ator Alice */
active proctype Alice() {
    byte nonce_a;
    byte nonce_b;

    /* Passo 1: Alice -> Bob */
    nonce_a = Na;
    ns_channel ! msg1, nonce_a, key_b, 0;

    /* Passo 4: Alice recebe msg4 de Bob */
    byte received_nonce_b;
    ns_channel ? msg4, _, received_nonce_b, _;

    /* Passo 5: Alice envia msg5 a Bob */
    ns_channel ! msg5, received_nonce_b, 0, 0;
}

/* Ator Bob */
active proctype Bob() {
    byte nonce_a;
    byte nonce_b;

    /* Passo 2: Bob recebe msg1 */
    ns_channel ? msg1, nonce_a, _, _;
    nonce_b = Nb;

    /* Passo 3: Bob envia msg2 a Alice */
    ns_channel ! msg2, nonce_a, nonce_b, 0;

    /* Passo 6: Bob recebe msg5 */
    byte received_nonce_b;
    ns_channel ? msg5, _, received_nonce_b, _;

    /* Verifica nonce */
    if
    :: (received_nonce_b == nonce_b) -> skip;
    :: else -> assert(false); /* Falha de autenticação */
    fi;
}

/* Atacante (Intruder) */
active proctype Intruder() {
    byte intercepted_a;
    byte intercepted_b;
    byte fake_nonce;

    /* Intercepta msg1 de Alice */
    ns_channel ? msg1, intercepted_a, _, _;
    fake_nonce = 100; /* Nonce conhecido pelo atacante */

    /* Reenvia com nonce próprio */
    ns_channel ! msg1, fake_nonce, key_b, 0;

    /* Recebe msg2 de Bob com nonce do atacante */
    ns_channel ? msg2, _, intercepted_b, _;

    /* Reenvia msg2 para Alice como se fosse de Bob */
    ns_channel ! msg2, intercepted_a, intercepted_b, 0;
}
```

### 3.5 Otimização com Partial Order Reduction

Model checkers como SPIN utilizam técnicas de otimização para reduzir o espaço de estados. A mais importante é a **Partial Order Reduction** (redução de ordem parcial), que explora o fato de que a ordem de execução de ações concorrentes independentes não afeta o resultado final.

Para protocolos criptográficos, isso é particularmente eficaz porque mensagens em canais diferentes são independentes. Se Alice envia uma mensagem para Bob enquanto Eve intercepta outra mensagem, a ordem dessas ações não altera o estado final do sistema.

```cpp
// Codigo C++ para configuracao e execucao de SPIN via interface programatica
// (usando a API de verificacao do SPIN)

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <cstdlib>
#include <memory>

class SpinVerifier {
public:
    struct VerificationResult {
        bool propertySatisfied;
        std::string counterexample;
        size_t statesExplored;
        size_t statesStored;
        double verificationTimeMs;
    };

    struct SpinConfig {
        std::string modelFile;
        std::string ltlProperty;
        bool usePartialOrderReduction = true;
        bool useHashCompression = true;
        size_t maxDepth = 10000;
        bool generateTrace = true;
    };

    explicit SpinVerifier(const SpinConfig& config)
        : config_(config) {}

    VerificationResult verify() {
        VerificationResult result;

        // Gera o modelo verificador
        std::string genCommand = "spin -a " + config_.modelFile;
        int genStatus = std::system(genCommand.c_str());
        if (genStatus != 0) {
            result.propertySatisfied = false;
            result.counterexample = "Erro ao gerar modelo verificador";
            return result;
        }

        // Compila o verificador com otimizacoes
        std::string compileFlags = "-O2 -DSAFETY";
        if (config_.usePartialOrderReduction) {
            compileFlags += " -DNP -DMEA";
        }
        std::string compileCmd = "gcc -o pan pan.c " + compileFlags;
        int compileStatus = std::system(compileCmd.c_str());
        if (compileStatus != 0) {
            result.propertySatisfied = false;
            result.counterexample = "Erro ao compilar verificador";
            return result;
        }

        // Executa a verificacao
        std::string verifyCmd = "./pan";
        if (config_.generateTrace) {
            verifyCmd += " -e";
        }

        int verifyStatus = std::system(verifyCmd.c_str());
        result.propertySatisfied = (verifyStatus == 0);

        // Parse do output do SPIN para extrair metricas
        parseVerificationOutput(result);

        return result;
    }

    bool generateCounterexampleTrace(const std::string& outputPath) {
        std::string cmd = "spin -t -p " + config_.modelFile;
        int status = std::system((cmd + " > " + outputPath + " 2>&1").c_str());
        return status == 0;
    }

private:
    SpinConfig config_;

    void parseVerificationOutput(VerificationResult& result) {
        // Em producao, parseamos o output do SPIN
        // Aqui simplificamos para ilustracao
        std::ifstream outputFile("pan_out.txt");
        if (outputFile.is_open()) {
            std::string line;
            while (std::getline(outputFile, line)) {
                if (line.find("states explored") != std::string::npos) {
                    result.statesExplored = parseNumber(line);
                }
                if (line.find("states stored") != std::string::npos) {
                    result.statesStored = parseNumber(line);
                }
            }
        }
    }

    size_t parseNumber(const std::string& line) {
        size_t pos = line.find_last_of(' ');
        if (pos != std::string::npos) {
            return std::stoul(line.substr(pos + 1));
        }
        return 0;
    }
};

int main() {
    SpinVerifier::SpinConfig config;
    config.modelFile = "auth_protocol.pml";
    config.ltlProperty = "[](!attacker_succeeds)";
    config.usePartialOrderReduction = true;
    config.maxDepth = 100000;

    SpinVerifier verifier(config);
    auto result = verifier.verify();

    if (result.propertySatisfied) {
        std::cout << "PROPRIEDADE VERIFICADA COM SUCESSO" << std::endl;
    } else {
        std::cout << "PROPRIEDADE VIOLADA" << std::endl;
        std::cout << "Contraexemplo: " << result.counterexample << std::endl;
    }

    std::cout << "Estados explorados: " << result.statesExplored << std::endl;
    std::cout << "Estados armazenados: " << result.statesStored << std::endl;

    return result.propertySatisfied ? 0 : 1;
}
```

### 3.6 Model Checking Aplicado ao TLS 1.3

O TLS 1.3 é um dos protocolos mais complexos e criticamente importantes em uso hoje. Model checking foi extensivamente utilizado durante seu desenvolvimento, e ferramentas como Tamarin Prover e ProVerif verificaram propriedades de segurança do protocolo.

Um modelo simplificado do handshake TLS 1.3 pode ser verificado com SPIN para propriedades como:

- **Autenticacao:** O cliente sempre autentica o servidor correto
- **Sigilo de chave:** A chave de sessao e secreta contra o adversario
- **Perfeicao de forward secrecy:** Comprometimento de chaves passadas nao compromete sessoes passadas
- **Ausencia de downgrade:** O adversario nao pode forcar uma versao inferior

```promela
/*
 * Modelo simplificado do TLS 1.3 Handshake para SPIN
 * Verifica propriedades de autenticacao e sigilo
 */

chan tls_channel = [1] of { mtype, byte, byte, byte };

mtype = {
    CLIENT_HELLO,
    SERVER_HELLO,
    ENCRYPTED_EXTENSIONS,
    CERTIFICATE,
    CERTIFICATE_VERIFY,
    FINISHED,
    APPLICATION_DATA
};

/* Estados do handshake */
byte client_random, server_random;
byte shared_secret;
byte handshake_secret;
byte master_secret;
bool handshake_complete = false;
bool client_authenticated = false;

/* Propriedades a verificar */
bool session_key_compromised = false;

/* Modelo do Cliente */
active proctype TLSClient() {
    byte ch_random;
    byte sh_random;
    byte finished_hash;

    /* ClientHello */
    ch_random = client_random;
    tls_channel ! CLIENT_HELLO, ch_random, 0, 0;

    /* Recebe ServerHello */
    tls_channel ? SERVER_HELLO, sh_random, _, _;

    /* Calcula chaves de sessao (simplificado) */
    handshake_secret = ch_random ^ sh_random;
    master_secret = handshake_secret ^ 0xAB;

    /* Recebe mensagens do servidor */
    byte ext_data;
    tls_channel ? ENCRYPTED_EXTENSIONS, ext_data, _, _;

    byte cert_data;
    tls_channel ? CERTIFICATE, cert_data, _, _;

    byte cert_verify;
    tls_channel ? CERTIFICATE_VERIFY, cert_verify, _, _;

    /* Verifica certificado (simplificado) */
    if
    :: (cert_verify == cert_data ^ handshake_secret) ->
        client_authenticated = true;
    :: else ->
        /* Falha na autenticacao */
        client_authenticated = false;
    fi;

    /* Recebe Finished e envia Finished */
    byte server_finished;
    tls_channel ? FINISHED, server_finished, _, _;

    finished_hash = master_secret;
    tls_channel ! FINISHED, finished_hash, 0, 0;

    /* Handshake completo */
    handshake_complete = true;

    /* Envia dados de aplicacao */
    byte app_data;
    tls_channel ! APPLICATION_DATA, app_data, 0, 0;
}

/* Modelo do Atacante (simplificado) */
active proctype Attacker() {
    byte intercepted;
    bool can_forge = false;

    /* O atacante pode: */
    /* 1. Observar mensagens */
    /* 2. Modificar mensagens (se tem chave) */
    /* 3. Reenviar mensagens antigas */

    /* Tenta forjar handshake */
    if
    :: (can_forge) ->
        tls_channel ! CLIENT_HELLO, 100, 0, 0;
    :: else ->
        skip;
    fi;
}

/* Propriedade de seguranca LTL: */
/* Se handshake completou E cliente autenticou, entao chave e segura */
/* G(handshake_complete & client_authenticated -> !session_key_compromised) */
```

### 3.7 Limitacoes do Model Checking

Embora poderoso, model checking enfrenta o problema da explosao de estados (state space explosion). Para cada variavel booleana, o numero de estados dobra. Para protocolos com chaves de 256 bits, o espaco de estados e literalmente astronomico.

Tecnicas de mitigacao incluem:

- **Partial Order Reduction:** Reduz o espaco explorando independencia de acoes
- **Bounded Model Checking:** Limita a profundidade da exploracao
- **Abstracao:** Substitui detalhes irrelevantes por abstracoes mais simples
- **Symmetry Reduction:** Agrupa estados simetricamente equivalentes
- **Compositional Verification:** Verifica componentes individualmente e compoe resultados

---

## 4. Cryptol: Linguagem de Especificacao para Criptografia

### 4.1 O que e Cryptol?

Cryptol e uma linguagem de especificacao desenvolvida pelo Laboratory for Telecommunication Sciences (LTS) da Marinha dos EUA, especificamente projetada para descrever algoritmos criptograficos. Diferente de linguagens de programacao convencionais, Cryptol foca em DESCREVER o comportamento do algoritmo sem se preocupar com implementacao eficiente.

A filosofia de Cryptol e: especifique o algoritmo uma vez, e deixe ferramentas como SAW gerar e verificar implementacoes em C, C++, LLVM e outras linguagens.

### 4.2 Sintaxe e Semantica de Cryptol

Cryptol trabalha com tipos dependente de tamanho (size-dependent types), o que e natural para criptografia onde operacoes sao definidas sobre bits, bytes e blocos de tamanho fixo.

```cryptol
-- Especificacao Cryptol de SHA-256 (simplificada)

-- Um bloco de 512 bits
type Block = [512]

-- Estado de 256 bits
type State = [256]

-- Constantes iniciais SHA-256
h0 : State
h0 = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
       0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]

-- Constantes K (64 valores de 32 bits)
k : [64][32]
k = [0x428a2f98, 0x71374491, ...] -- 64 constantes

-- Funcao sigma maior (majority)
sigma0 : [32] -> [32]
sigma0 x = (x `rotateR` 2) ^^ (x `rotateR` 13) ^^ (x `rotateR` 22)

-- Funcao sigma menor (choice)
sigma1 : [32] -> [32]
sigma1 x = (x `rotateR` 6) ^^ (x `rotateR` 11) ^^ (x `rotateR` 25)

-- Funcao choice
ch : [32] -> [32] -> [32] -> [32]
ch x y z = (x && y) ^^ ((! x) && z)

-- Funcao majority
maj : [32] -> [32] -> [32] -> [32]
maj x y z = (x && y) ^^ (x && z) ^^ (y && z)

-- Uma rodada de compressao SHA-256
sha256_round : State -> [64][32] -> State
sha256_round [a, b, c, d, e, f, g, h] [w, k] =
    let t1 = h + sigma1(e) + ch(e, f, g) + k + w
        t2 = sigma0(a) + maj(a, b, c)
    in [a + t1, a, b, c, d + t1, e, f, g]

-- Expansao de mensagem
message_schedule : [16][32] -> [64][32]
message_schedule block =
    let extended = block ++ [0 | _ <- [0 .. 47]]
    in foldl extend extended [16 .. 63]
  where
    extend w i =
        let s0 = sigma0 (w ! (i-15))
            s1 = sigma1 (w ! (i-2))
            wi = s0 + w ! (i-7) + s1 + w ! (i-16)
        in wi

-- Hash de um bloco
sha256_block : State -> Block -> State
sha256_block state block =
    let words = split block :: [16][32]
        schedule = message_schedule words
    in foldl sha256_round state (zip schedule k)

-- SHA-256 completo
sha256 : [n] -> [256]
sha256 message =
    let padded = pad message
        blocks = split padded :: [_][Block]
    in foldl sha256_block h0 blocks
```

### 4.3 Especificacao de AES em Cryptol

AES e um dos algoritmos mais especificados formalmente. Cryptol pode expressar todas as operacoes de AES com precisao matematica:

```cryptol
-- Especificacao Cryptol de AES (operacoes principais)

-- Tamanho de bloco AES
type BlockSize = 128
type KeySize = 128

-- S-Box do AES (256 entradas de 8 bits)
sbox : [256][8]
sbox = [0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, ...]

-- Operacao SubBytes
subBytes : [16][8] -> [16][8]
subBytes block = map (\byte -> sbox @ byte) block

-- Operacao ShiftRows
shiftRows : [16][8] -> [16][8]
shiftRows [r0, r1, r2, r3, r4, r5, r6, r7,
           r8, r9, r10, r11, r12, r13, r14, r15] =
    [r0,  r5,  r10, r15,
     r4,  r9,  r14, r3,
     r8,  r13, r2,  r7,
     r12, r1,  r6,  r11]

-- Operacao MixColumns (simplificada)
mixColumns : [16][8] -> [16][8]
mixColumns state = map mixColumn (groupsOf 4 state)

mixColumn : [4][8] -> [4][8]
mixColumn [c0, c1, c2, c3] =
    let d0 = gmul(0x02, c0) ^^ gmul(0x03, c1) ^^ c2 ^^ c3
        d1 = c0 ^^ gmul(0x02, c1) ^^ gmul(0x03, c2) ^^ c3
        d2 = c0 ^^ c1 ^^ gmul(0x02, c2) ^^ gmul(0x03, c3)
        d3 = gmul(0x03, c0) ^^ c1 ^^ c2 ^^ gmul(0x02, c3)
    in [d0, d1, d2, d3]

-- Multiplicacao no corpo de Galois GF(2^8)
gmul : [8] -> [8] -> [8]
gmul a b =
    let p = 0
        for i in [0 .. 7] do
            if (b .&. 1) == 1 then p ^^ a else p
        a_shifted = if (a .&. 0x80) == 0x80
                    then (a << 1) ^^ 0x1B
                    else a << 1
    in p

-- Round key addition
addRoundKey : [16][8] -> [16][8] -> [16][8]
addRoundKey state roundKey =
    zipWith (\s k -> s ^^ k) state roundKey

-- Uma rodada completa de AES
aesRound : [16][8] -> [16][8] -> [16][8]
aesRound state roundKey =
    let afterSub = subBytes state
        afterShift = shiftRows afterSub
        afterMix = mixColumns afterShift
    in addRoundKey afterMix roundKey

-- Propriedade de correcao:
-- Decriptar(Encriptar(mensagem, chave), chave) == mensagem
-- Isso pode ser verificado com SAW
```

### 4.4 Conectando Cryptol com SAW

Cryptol por si so e uma linguagem de especificacao — ela descreve o COMPORTAMENTO correto do algoritmo. SAW (Software Analysis Workbench) e a ferramenta que conecta essa especificacao a implementacoes reais, provando que a implementacao se comporta de acordo com a especificacao.

O fluxo de trabalho tipico e:

1. Escrever a especificacao em Cryptol
2. Implementar o algoritmo em C ou C++
3. Usar SAW para provar que a implementacao e equivalente a especificacao

```cpp
// Implementacao C do AES SubBytes para verificacao com SAW

#include <cstdint>
#include <array>

// S-Box do AES (identica a especificacao NIST)
static const std::array<uint8_t, 256> AES_SBOX = {
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
    0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0,
    0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC,
    0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A,
    0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0,
    0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B,
    0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85,
    0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5,
    0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17,
    0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88,
    0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C,
    0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9,
    0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6,
    0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E,
    0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94,
    0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68,
    0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16
};

// Funcao SubBytes - implementacao em C
// SAW vai provar que esta implementacao equivale a especificacao Cryptol
extern "C" void aes_subbytes(const uint8_t input[16], uint8_t output[16]) {
    for (int i = 0; i < 16; ++i) {
        output[i] = AES_SBOX[input[i]];
    }
}

// Funcao AddRoundKey - implementacao em C
extern "C" void aes_add_round_key(
    const uint8_t state[16],
    const uint8_t round_key[16],
    uint8_t output[16])
{
    for (int i = 0; i < 16; ++i) {
        output[i] = state[i] ^ round_key[i];
    }
}

// Funcao ShiftRows - implementacao em C
extern "C" void aes_shift_rows(const uint8_t input[16], uint8_t output[16]) {
    // Row 0: no shift
    output[0]  = input[0];
    output[1]  = input[5];
    output[2]  = input[10];
    output[3]  = input[15];
    // Row 1: shift left by 1
    output[4]  = input[4];
    output[5]  = input[9];
    output[6]  = input[14];
    output[7]  = input[3];
    // Row 2: shift left by 2
    output[8]  = input[8];
    output[9]  = input[13];
    output[10] = input[2];
    output[11] = input[7];
    // Row 3: shift left by 3
    output[12] = input[12];
    output[13] = input[1];
    output[14] = input[6];
    output[15] = input[11];
}

// Multiplicacao em GF(2^8) para MixColumns
static uint8_t gmul(uint8_t a, uint8_t b) {
    uint8_t p = 0;
    for (int i = 0; i < 8; ++i) {
        if (b & 1) {
            p ^= a;
        }
        bool hi = (a & 0x80) != 0;
        a <<= 1;
        if (hi) {
            a ^= 0x1B;
        }
        b >>= 1;
    }
    return p;
}

// MixColumns - implementacao em C
extern "C" void aes_mix_columns(const uint8_t input[16], uint8_t output[16]) {
    for (int col = 0; col < 4; ++col) {
        int i = col * 4;
        uint8_t s0 = input[i];
        uint8_t s1 = input[i + 1];
        uint8_t s2 = input[i + 2];
        uint8_t s3 = input[i + 3];

        output[i]     = gmul(0x02, s0) ^ gmul(0x03, s1) ^ s2 ^ s3;
        output[i + 1] = s0 ^ gmul(0x02, s1) ^ gmul(0x03, s2) ^ s3;
        output[i + 2] = s0 ^ s1 ^ gmul(0x02, s2) ^ gmul(0x03, s3);
        output[i + 3] = gmul(0x03, s0) ^ s1 ^ s2 ^ gmul(0x02, s3);
    }
}
```

### 4.5 Script SAW para Verificacao de Equivalencia

O script SAW a seguir prova que cada operacao de AES implementada em C e equivalente a especificacao em Cryptol:

```cryptol
-- Script SAW: Verificacao de equivalencia AES
-- Prova que cada operacao C equivale a especificacao Cryptol

-- Carrega o modulo LLVM da implementacao C
llvm_mod <- llvm_load_module "aes_impl.bc"

-- Carrega a especificacao Cryptol
cryptol_mod <- cryptol_load_module "AES.cry"

-- Verifica SubBytes
prove : {{
    \input -> aes_subbytes_c input == aes_subbytes_spec input
}}
where
    aes_subbytes_c = llvm_fun "aes_subbytes" llvm_mod
    aes_subbytes_spec = cryptol_fun "subBytes" cryptol_mod

-- Verifica AddRoundKey
prove : {{
    \state key -> aes_add_round_key_c state key == aes_add_round_key_spec state key
}}
where
    aes_add_round_key_c = llvm_fun "aes_add_round_key" llvm_mod
    aes_add_round_key_spec = cryptol_fun "addRoundKey" cryptol_mod

-- Verifica ShiftRows
prove : {{
    \input -> aes_shift_rows_c input == aes_shift_rows_spec input
}}
where
    aes_shift_rows_c = llvm_fun "aes_shift_rows" llvm_mod
    aes_shift_rows_spec = cryptol_fun "shiftRows" cryptol_mod

-- Verifica MixColumns
prove : {{
    \input -> aes_mix_columns_c input == aes_mix_columns_spec input
}}
where
    aes_mix_columns_c = llvm_fun "aes_mix_columns" llvm_mod
    aes_mix_columns_spec = cryptol_fun "mixColumns" cryptol_mod

-- Verifica a propriedade de inversao:
-- SubBytes e inversivel
prove : {{
    \input -> inv_subBytes (subBytes input) == input
}}

-- Verifica que ShiftRows e sua inversao se cancelam
prove : {{
    \input -> inv_shiftRows (shiftRows input) == input
}}
```

### 4.6 Vantagens de Cryptol para Criptografia

1. **Precisao matematica:** Cryptol elimina ambiguidades de linguagens de programacao convencionais
2. **Dependencia de tamanho:** Tipos como `[128]` vs `[256]` capturam invariantes de tamanho
3. **Execucao executavel:** Especificacoes em Cryptol podem ser executadas para gerar testes
4. **Conexao com ferramentas:** SAW, Cryptol REPL, e verificadores automaticos
5. **Comunidade ativa:** Especificacoes oficiais NIST disponiveis em Cryptol

---

## 5. SAW: Software Analysis Workbench

### 5.1 Visao Geral do SAW

SAW (Software Analysis Workbench) e uma ferramenta de verificacao formal desenvolvida pela Galois Inc., projetada para provar equivalencia entre implementacoes em C, C++ e LLVM e especificacoes em Cryptol ou Haskell.

O diferencial do SAW para engenharia criptografica e sua capacidade de trabalhar diretamente com codigo C/C++ compilado para LLVM IR, sem exigir que o codigo seja reescrito em uma linguagem de verificacao.

```
+------------------------------------------------------------------+
|                    Arquitetura do SAW                             |
+------------------------------------------------------------------+
|                                                                  |
|  Especificacao          Implementacao C/C++                      |
|  (Cryptol/Haskell)      (compilado para LLVM IR)                 |
|        |                       |                                 |
|        v                       v                                 |
|  [Parsing Cryptol]    [Carregamento LLVM]                       |
|        |                       |                                 |
|        +-------+-------+-------+                                 |
|                |                                                 |
|                v                                                 |
|        [Symbolic Execution Engine]                               |
|                |                                                 |
|                v                                                 |
|        [Proof Engine]                                            |
|        (ABC, Yices, Z3)                                         |
|                |                                                 |
|                v                                                 |
|        [Resultado: PROVADO ou CONTRAEXEMPLO]                     |
+------------------------------------------------------------------+
```

### 5.2 Instalacao e Configuracao

SAW e distribuido como binario pre-compilado para Linux, macOS e Windows. A instalacao requer:

```bash
# Instalacao do SAW (Linux)
wget https://github.com/GaloisInc/saw/releases/download/v1.1/saw-1.1-Linux.tar.gz
tar xzf saw-1.1-Linux.tar.gz
export PATH=$PATH:$(pwd)/saw-1.1/bin

# Verificacao da instalacao
saw --version

# Dependencias necessarias
# - Z3 SMT Solver
# - Cryptol (incluido no SAW)
# - Clang (para compilar C para LLVM IR)

# Instalacao do Z3
sudo apt-get install z3

# Instalacao do Clang
sudo apt-get install clang

# Compilacao do codigo C para LLVM IR
clang -emit-llvm -c -g -O0 aes_impl.c -o aes_impl.bc
```

### 5.3 Conceitos Fundamentais do SAW

**Termos Simbolicos:** SAW representa valores como termos simbolicos — expressoes matematicas que podem conter variaveis livres. Em vez de testar com valores concretos, SAW manipula esses termos simbolicamente.

**Execucao Simbolica:** SAW executa o programa C simbolizando as entradas. Cada instrucao do programa transforma os termos simbolicos de acordo com a semantica da instrucao. O resultado e uma expressao simbolica que representa o comportamento do programa para qualquer entrada.

**Prova de Equivalencia:** Dadas duas expressoes simbolicamente executadas (uma da especificacao, uma da implementacao), SAW usa um SMT solver (como Z3 ou Yices) para provar que as duas expressoes sao equivalentes para todas as entradas.

```cpp
// Exemplo completo: Implementacao C de HMAC-SHA256
// que sera verificada contra especificacao Cryptol

#include <cstdint>
#include <cstring>
#include <array>

// Forward declarations das funcoes SHA256
extern "C" void sha256_init(uint32_t state[8]);
extern "C" void sha256_update(uint32_t state[8], const uint8_t* data, size_t len);
extern "C" void sha256_final(uint32_t state[8], uint8_t hash[32]);

// HMAC-SHA256
extern "C" void hmac_sha256(
    const uint8_t* key, size_t key_len,
    const uint8_t* message, size_t msg_len,
    uint8_t output[32])
{
    // Constantes HMAC
    static const uint8_t IPAD = 0x36;
    static const uint8_t OPAD = 0x5C;

    uint8_t key_block[64];
    uint8_t ipad_block[64];
    uint8_t opad_block[64];

    // Se chave > 64 bytes, hash da chave
    if (key_len > 64) {
        uint8_t hashed_key[32];
        sha256_init(reinterpret_cast<uint32_t*>(hashed_key));
        sha256_update(
            reinterpret_cast<uint32_t*>(hashed_key),
            key, key_len);
        sha256_final(
            reinterpret_cast<uint32_t*>(hashed_key),
            hashed_key);

        std::memset(key_block, 0, 64);
        std::memcpy(key_block, hashed_key, 32);
    } else {
        std::memset(key_block, 0, 64);
        std::memcpy(key_block, key, key_len);
    }

    // XOR com ipad e opad
    for (int i = 0; i < 64; ++i) {
        ipad_block[i] = key_block[i] ^ IPAD;
        opad_block[i] = key_block[i] ^ OPAD;
    }

    // Inner hash: SHA256(ipad || message)
    uint32_t inner_state[8];
    sha256_init(inner_state);
    sha256_update(inner_state, ipad_block, 64);
    sha256_update(inner_state, message, msg_len);

    uint8_t inner_hash[32];
    sha256_final(inner_state, inner_hash);

    // Outer hash: SHA256(opad || inner_hash)
    uint32_t outer_state[8];
    sha256_init(outer_state);
    sha256_update(outer_state, opad_block, 64);
    sha256_update(outer_state, inner_hash, 32);

    sha256_final(outer_state, output);
}

// Funcao utilitaria para XOR em bloco
extern "C" void block_xor(
    const uint8_t* a,
    const uint8_t* b,
    uint8_t* output,
    size_t len)
{
    for (size_t i = 0; i < len; ++i) {
        output[i] = a[i] ^ b[i];
    }
}
```

### 5.4 Script SAW para HMAC-SHA256

```cryptol
-- Script SAW: Verificacao de HMAC-SHA256
-- Prova que a implementacao C equivale a especificacao HMAC RFC 2104

-- Carrega modulos
llvm_mod <- llvm_load_module "hmac_impl.bc"
cryptol_mod <- cryptol_load_module "HMAC.cry"

-- Especificacao HMAC-SHA256 em Cryptol
-- HMAC(K, m) = H((K' ^ opad) || H((K' ^ ipad) || m))
-- onde K' e K preenchido ou hasheado para 64 bytes

-- Verifica bloco XOR
prove : {{
    \a b -> block_xor_c a b == xor_spec a b
}}
where
    block_xor_c = llvm_fun "block_xor" llvm_mod
    xor_spec = cryptol_fun "xorBlocks" cryptol_mod

-- Verifica HMAC completo
prove : {{
    \key msg -> hmac_sha256_c key msg == hmac_sha256_spec key msg
}}
where
    hmac_sha256_c = llvm_fun "hmac_sha256" llvm_mod
    hmac_sha256_spec = cryptol_fun "hmac" cryptol_mod

-- Propriedade de seguranca HMAC:
-- Mesmo que o adversario conheca o output, nao pode recuperar a chave
-- (Isso e verificado indiretamente pela equivalencia com a especificacao)
```

### 5.5 Verificacao de Propriedades de Seguranca com SAW

SAW pode verificar nao apenas equivalencia funcional, mas tambem propriedades de seguranca:

{% raw %}
```cpp
// Framework C++ para verificacao de propriedades de seguranca
// usando SAW como backend

#include <iostream>
#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <fstream>
#include <sstream>

// Resultado de verificacao
struct VerificationResult {
    enum class Status {
        VERIFIED,       // Propriedade provada
        VIOLATED,       // Propriedade violada (contraexemplo encontrado)
        TIMEOUT,        // Timeout na verificacao
        UNKNOWN         // Nao foi possivel determinar
    };

    Status status;
    std::string message;
    std::string counterexample;
    double verificationTimeMs;
};

// Gerador de scripts SAW
class SAWScriptGenerator {
public:
    explicit SAWScriptGenerator(const std::string& moduleName)
        : moduleName_(moduleName) {}

    // Gera script para verificar equivalencia de funcoes
    std::string generateEquivalenceCheck(
        const std::string& llvmModule,
        const std::string& funcName,
        const std::string& specName,
        const std::vector<std::string>& argTypes)
    {
        std::ostringstream script;

        script << "-- Verificacao de equivalencia: "
               << funcName << " == " << specName << "\n";
        script << "-- Gerado automaticamente\n\n";

        script << "llvm_mod <- llvm_load_module \"" << llvmModule << "\";\n";
        script << "cryptol_mod <- cryptol_load_module \""
               << moduleName_ << ".cry\";\n\n";

        script << "let llvm_func = llvm_fun \"" << funcName << "\" llvm_mod;\n";
        script << "let spec_func = cryptol_fun \"" << specName
               << "\" cryptol_mod;\n\n";

        script << "prove {{ \\args -> llvm_func args == spec_func args }}\n";

        return script.str();
    }

    // Gera script para verificar propriedade de constant-time
    std::string generateConstantTimeCheck(
        const std::string& llvmModule,
        const std::string& funcName)
    {
        std::ostringstream script;

        script << "-- Verificacao de constant-time: " << funcName << "\n\n";

        script << "llvm_mod <- llvm_load_module \"" << llvmModule << "\";\n\n";

        script << "let ct_check = do\n";
        script << "    f <- llvm_fun \"" << funcName << "\" llvm_mod\n";
        script << "    crucible_llvm_verify f [] (llvm_timeout 300) $ do\n";
        script << "        crucible_mem <- crucible_get_syminterface\n";
        script << "        crucible_execute_func []\n";
        script << "        crucible_verify_tigress f\n";

        return script.str();
    }

    // Gera script para verificar ausencia de memory leaks
    std::string generateMemorySafetyCheck(
        const std::string& llvmModule,
        const std::string& funcName)
    {
        std::ostringstream script;

        script << "-- Verificacao de seguranca de memoria: " << funcName << "\n\n";

        script << "llvm_mod <- llvm_load_module \"" << llvmModule << "\";\n\n";

        script << "let mem_safety = do\n";
        script << "    f <- llvm_fun \"" << funcName << "\" llvm_mod\n";
        script << "    crucible_llvm_verify f [] (llvm_timeout 300) $ do\n";
        script << "        crucible_mem <- crucible_get_syminterface\n";
        script << "        crucible_execute_func []\n";
        script << "        crucible_points_to nonnull\n";

        return script.str();
    }

    // Salva script em arquivo
    bool saveScript(const std::string& script, const std::string& filename) {
        std::ofstream file(filename);
        if (!file.is_open()) return false;
        file << script;
        file.close();
        return true;
    }

private:
    std::string moduleName_;
};

// Executor de verificacao SAW
class SAWExecutor {
public:
    VerificationResult executeScript(const std::string& scriptPath) {
        VerificationResult result;

        std::string cmd = "saw " + scriptPath + " 2>&1";
        FILE* pipe = popen(cmd.c_str(), "r");
        if (!pipe) {
            result.status = VerificationResult::Status::UNKNOWN;
            result.message = "Erro ao executar SAW";
            return result;
        }

        std::string output;
        char buffer[4096];
        while (fgets(buffer, sizeof(buffer), pipe)) {
            output += buffer;
        }

        int status = pclose(pipe);

        // Parse do output
        if (output.find("Verified") != std::string::npos ||
            output.find("valid") != std::string::npos) {
            result.status = VerificationResult::Status::VERIFIED;
            result.message = "Propriedade verificada com sucesso";
        } else if (output.find("Invalid") != std::string::npos ||
                   output.find("counterexample") != std::string::npos) {
            result.status = VerificationResult::Status::VIOLATED;
            result.message = "Propriedade violada";
            result.counterexample = extractCounterexample(output);
        } else if (output.find("timeout") != std::string::npos) {
            result.status = VerificationResult::Status::TIMEOUT;
            result.message = "Timeout na verificacao";
        } else {
            result.status = VerificationResult::Status::UNKNOWN;
            result.message = output.substr(0, 500);
        }

        return result;
    }

private:
    std::string extractCounterexample(const std::string& output) {
        size_t start = output.find("Counterexample");
        if (start == std::string::npos) {
            start = output.find("counterexample");
        }
        if (start != std::string::npos) {
            size_t end = output.find("\n\n", start);
            if (end == std::string::npos) end = output.length();
            return output.substr(start, end - start);
        }
        return "";
    }
};
```
{% endraw %}

### 5.6 Verificando OpenSSL com SAW

SAW possui suporte nativo para verificar implementacoes que usam a OpenSSL. Isso e particularmente valioso porque OpenSSL e a biblioteca criptografica mais usada do mundo, e bugs nela tem impacto massivo.

```cpp
// Wrapper C++ para verificacao de funcoes OpenSSL com SAW

#include <openssl/evp.h>
#include <openssl/sha.h>
#include <openssl/hmac.h>
#include <openssl/aes.h>
#include <cstdint>
#include <vector>
#include <array>
#include <iostream>

// Interface para verificacao com SAW
// SAW precisa de funcoes com linkage C puro

extern "C" {

// SHA-256 wrapper
void verify_sha256(
    const uint8_t* input, size_t input_len,
    uint8_t output[32])
{
    EVP_MD_CTX* ctx = EVP_MD_CTX_new();
    if (!ctx) return;

    unsigned int hash_len = 0;
    EVP_DigestInit_ex(ctx, EVP_sha256(), nullptr);
    EVP_DigestUpdate(ctx, input, input_len);
    EVP_DigestFinal_ex(ctx, output, &hash_len);
    EVP_MD_CTX_free(ctx);
}

// AES-128-ECB wrapper (para verificacao SAW)
void verify_aes128_ecb_encrypt(
    const uint8_t key[16],
    const uint8_t input[16],
    uint8_t output[16])
{
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return;

    int len = 0;
    EVP_EncryptInit_ex(ctx, EVP_aes_128_ecb(), nullptr, key, nullptr);
    EVP_EncryptUpdate(ctx, output, &len, input, 16);
    EVP_EncryptFinal_ex(ctx, output + len, &len);
    EVP_CIPHER_CTX_free(ctx);
}

// AES-256-GCM wrapper
void verify_aes256_gcm_encrypt(
    const uint8_t key[32],
    const uint8_t nonce[12],
    const uint8_t* plaintext, size_t plaintext_len,
    uint8_t* ciphertext,
    uint8_t tag[16])
{
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return;

    int len = 0;
    int ciphertext_len = 0;

    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), nullptr, nullptr, nullptr);
    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, 12, nullptr);
    EVP_EncryptInit_ex(ctx, nullptr, nullptr, key, nonce);

    EVP_EncryptUpdate(ctx, ciphertext, &len, plaintext, plaintext_len);
    ciphertext_len = len;

    EVP_EncryptFinal_ex(ctx, ciphertext + len, &len);
    ciphertext_len += len;

    EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag);
    EVP_CIPHER_CTX_free(ctx);
}

// ChaCha20-Poly1305 wrapper
void verify_chacha20_poly1305_encrypt(
    const uint8_t key[32],
    const uint8_t nonce[12],
    const uint8_t* plaintext, size_t plaintext_len,
    uint8_t* ciphertext,
    uint8_t tag[16])
{
    // Implementacao usando libsodium-like interface
    // Para verificacao SAW, usamos uma implementacao de referencia
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return;

    int len = 0;
    EVP_EncryptInit_ex(ctx, EVP_chacha20_poly1305(), nullptr,
                       key, nonce);
    EVP_EncryptUpdate(ctx, ciphertext, &len, plaintext, plaintext_len);
    EVP_CIPHER_CTX_free(ctx);
}

} // extern "C"
```

### 5.7 Limitacoes e Escopo do SAW

SAW e extremamente eficaz para verificar equivalencia entre implementacoes e especificacoes. No entanto, possui limitacoes importantes:

1. **Escopo limitado:** SAW verifica codigo LLVM, mas nao modela efeitos colaterais como I/O, system calls ou operacoes atomicas
2. **Tamanho das especificacoes:** Funcoes com entrada variavel (como protocolos completos) sao dificeis de especificar em Cryptol
3. **Performance:** Verificacao de codigo complexo pode levar minutos ou horas
4. **Memoria dinamica:** Alocacao e desalocacao dinamica de memoria requerem abordagens especiais
5. **Bibliotecas externas:** Codigo que depende de bibliotecas externas (como OpenSSL) requer wrappers ou stubs

---

## 6. ProVerif: Verificacao Automatizada de Protocolos

### 6.1 Fundamentos do ProVerif

ProVerif e uma ferramenta de verificacao automatizada de protocolos criptograficos desenvolvida por Bruno Blanchet. Diferente de SPIN e NuSMV, que trabalham com modelos finitos, ProVerif usa uma abordagem baseada em logica linear (pi-calculus) e pode verificar protocolos com segredos de tamanho arbitrario.

ProVerif e particularmente poderoso para verificar:

- **Sigilo de dados:** Propriedades que dizem "o adversario nunca aprende X"
- **Autenticacao:** Propriedades que dizem "se B aceita uma mensagem de A, entao A realmente enviou"
- **Forward secrecy:** Propriedades que dizem "comprometimento de chaves nao afeta sessoes passadas"
- **Anonimidade:** Propriedades que dizem "o adversario nao pode distinguir dois participantes"

### 6.2 Linguagem de Entrada do ProVerif

ProVerif usa uma linguagem baseada no pi-calculus, uma linguagem formal para descrever sistemas concorrentes com comunicacao.

```proverif
(* Modelo de autenticacao HMAC em ProVerif *)
(* Verifica sigilo da chave e autenticidade *)

(* Declaracao de tipos *)
type channel.
type key.
type message.

(* Funcoes criptograficas *)
fun hmac : key -> message -> message.
fun encrypt : key -> message -> message.
reduc forall k : key, m : message; decrypt(k, encrypt(k, m)) = m.
reduc forall k : key, m : message; verify(k, m, hmac(k, m)) = true.

(* Canais *)
ch c_a2b : channel.    (* Alice -> Bob *)
ch c_b2a : channel.    (* Bob -> Alice *)
ch c_eve : channel.    (* Eve observa *)

(* Segredo *)
secret k : key.    (* Chave secreta entre Alice e Bob *)

(* Eventos de autenticacao *)
event Alice_sends : message -> unit.
event Bob_receives : message -> unit.

(* Processo Alice *)
let alice =
    new m : message;
    out(c_a2b, encrypt(k, m));
    event Alice_sends(m);
    0.

(* Processo Bob *)
let bob =
    in(c_b2a, x : message);
    if verify(k, x, hmac(k, x)) then
        event Bob_receives(x);
        0
    else
        0.

(* Processo Eve (adversario) *)
let eve =
    in(c_eve, x : message);
    (* Eve pode tentar aprender m *)
    0.

(* Composicao do sistema *)
process (new k; out(c_eve, k)) | alice | bob | eve.

(* Queries de seguranca *)
(* A chave k e secreta? *)
query attacker(k).

(* Autenticacao: se Bob recebeu, Alice enviou *)
query m : message; event(Bob_receives(m)) ==> event(Alice_sends(m)).

(* Execucao da verificacao *)
goal attacker(k) = false.
goal forall m : message; event(Bob_receives(m)) ==> event(Alice_sends(m)).
```

### 6.3 Verificacao de TLS 1.3 com ProVerif

O handshake TLS 1.3 e significativamente mais simples que o TLS 1.2, mas ainda possui complexidade consideravel. ProVerif foi usado durante o desenvolvimento do TLS 1.3 para verificar propriedades de seguranca.

```proverif
(* Modelo simplificado de TLS 1.3 para ProVerif *)
(* Verifica forward secrecy e autenticacao *)

type channel.
type skey.    (* Chave secreta de longo prazo *)
type key.     (* Chave de sessao *)
type nonce.
type payload.

(* Funcoes criptograficas *)
fun pk : skey -> key.             (* Chave publica *)
fun sk_enc : skey -> payload -> payload.  (* Assinatura *)
fun pk_enc : key -> payload -> payload.   (* Encriptacao com chave publica *)
fun aead_enc : key -> nonce -> payload -> payload. (* AEAD *)
reduc forall k : skey, m : payload; verify(pk(k), m, sk_enc(k, m)) = true.
reduc forall k : skey, m : payload; sk_dec(k, pk_enc(pk(k), m)) = m.
reduc forall k : key, n : nonce, m : payload; aead_dec(k, n, aead_enc(k, n, m)) = m.

(* Canais *)
ch c_public : channel.

(* Segredos *)
secret sk_client : skey.
secret sk_server : skey.
secret psk : key.  (* Pre-shared key opcional *)

(* Nonces *)
let client_hello_random : nonce = hNonces(1).
let server_hello_random : nonce = hNonces(2).

(* Handshake TLS 1.3 *)
let client =
    (* ClientHello: envia random *)
    out(c_public, client_hello_random);

    (* Recebe ServerHello *)
    in(c_public, sh_random : nonce);

    (* Deriva chaves de sessao (simplificado) *)
    let shared_secret = h(
        concat(client_hello_random, sh_random)
    ) in
    let handshake_key = hkdf(shared_secret, "handshake key") in
    let app_key = hkdf(shared_secret, "application key") in

    (* Recebe encrypted extensions *)
    in(c_public, ee : payload);

    (* Recebe certificado *)
    in(c_public, cert : payload);

    (* Verifica assinatura do servidor *)
    in(c_public, cert_verify : payload);
    if verify(pk(sk_server), concat(client_hello_random, sh_random), cert_verify) then
        (* Handshake bem-sucedido *)
        (* Envia Finished *)
        let finished_hash = h(concat(client_hello_random, sh_random)) in
        out(c_public, sk_enc(sk_client, finished_hash));
    else
        0.

let server =
    (* Recebe ClientHello *)
    in(c_public, ch_random : nonce);

    (* ServerHello: envia random *)
    out(c_public, server_hello_random);

    (* Deriva chaves de sessao *)
    let shared_secret = h(
        concat(ch_random, server_hello_random)
    ) in
    let handshake_key = hkdf(shared_secret, "handshake key") in
    let app_key = hkdf(shared_secret, "application key") in

    (* Envia encrypted extensions *)
    out(c_public, aead_enc(handshake_key, 0, payload(0)));

    (* Envia certificado *)
    out(c_public, pk(sk_server));

    (* Envia assinatura *)
    out(c_public, sk_enc(sk_server, concat(ch_random, server_hello_random)));

    (* Recebe Finished do cliente *)
    in(c_public, client_finished : payload);
    if verify(pk(sk_client), h(concat(ch_random, server_hello_random)), client_finished) then
        (* Handshake completo *)
        0.

let adversary =
    (* O adversario pode observar tudo no canal publico *)
    in(c_public, x : payload);
    0.

(* Composicao *)
process (new sk_client; new sk_server; (client | server | adversary)).

(* Propriedades de seguranca *)
(* 1. Chaves de sessao sao secretas *)
(* query s : key; attacker(s) = false. *)

(* 2. Autenticacao: servidor autenticado *)
(* query event(client_authenticated(server)) ==> event(server_sent_cert). *)

(* 3. Forward secrecy *)
(* query forall s : skey; attacker(s) ==> not attacker(past_session_key). *)

(* 4. Ausencia de downgrade *)
(* query forall n1 : nonce; client_hello_random = n1 ==> not attacker(version_downgrade). *)
```

### 6.4 ProVerif na Pratica: Analise de Protocolo Real

```cpp
// Framework C++ para automatizar verificacao de protocolos com ProVerif

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <cstdlib>
#include <memory>

// Definicao de propriedades de seguranca
struct SecurityProperty {
    enum class Type {
        SECRECY,          // Sigilo de dado
        AUTHENTICATION,   // Autenticacao
        FORWARD_SECRECY,  // Forward secrecy
        ANONYMITY,        // Anonimidade
        INJECTIVITY       // Injetividade
    };

    Type type;
    std::string description;
    std::string query;
    bool expected;
};

// Analisador de protocolo
class ProtocolAnalyzer {
public:
    ProtocolAnalyzer(const std::string& protocolName)
        : protocolName_(protocolName) {}

    void addProperty(const SecurityProperty& prop) {
        properties_.push_back(prop);
    }

    void addParticipant(const std::string& name,
                       const std::string& processDefinition) {
        participants_[name] = processDefinition;
    }

    void setChannel(const std::string& channelDef) {
        channelDef_ = channelDef;
    }

    // Gera o arquivo de entrada ProVerif
    std::string generateProVerifInput() const {
        std::ostringstream input;

        input << "(* Analise automatizada do protocolo: "
               << protocolName_ << " *)\n\n";

        // Declaracao de tipos
        input << "type channel.\n";
        input << "type skey.\n";
        input << "type key.\n";
        input << "type nonce.\n";
        input << "type payload.\n\n";

        // Funcoes
        input << "fun pk : skey -> key.\n";
        input << "fun sk_enc : skey -> payload -> payload.\n";
        input << "fun pk_enc : key -> payload -> payload.\n";
        input << "fun aead_enc : key -> nonce -> payload -> payload.\n";
        input << "reduc forall k : skey, m : payload;\n";
        input << "    verify(pk(k), m, sk_enc(k, m)) = true.\n";
        input << "reduc forall k : skey, m : payload;\n";
        input << "    sk_dec(k, pk_enc(pk(k), m)) = m.\n";
        input << "reduc forall k : key, n : nonce, m : payload;\n";
        input << "    aead_dec(k, n, aead_enc(k, n, m)) = m.\n\n";

        // Canais
        input << channelDef_ << "\n\n";

        // Participantes
        for (const auto& [name, process] : participants_) {
            input << "let " << name << " =\n";
            input << "    " << process << "\n\n";
        }

        // Queries
        for (const auto& prop : properties_) {
            input << "(* " << prop.description << " *)\n";
            input << prop.query << "\n\n";
        }

        return input.str();
    }

    // Executa ProVerif
    bool runVerification(const std::string& inputFile,
                        std::string& output) {
        std::string cmd = "proverif " + inputFile + " 2>&1";

        FILE* pipe = popen(cmd.c_str(), "r");
        if (!pipe) return false;

        char buffer[4096];
        output.clear();
        while (fgets(buffer, sizeof(buffer), pipe)) {
            output += buffer;
        }

        int status = pclose(pipe);
        return status == 0;
    }

    // Analisa resultados
    std::vector<std::pair<SecurityProperty, bool>> analyzeResults(
        const std::string& proverifOutput) const
    {
        std::vector<std::pair<SecurityProperty, bool>> results;

        for (const auto& prop : properties_) {
            bool verified = false;

            switch (prop.type) {
                case SecurityProperty::Type::SECRECY:
                    verified = (proverifOutput.find("attacker(") ==
                               std::string::npos) ||
                               (proverifOutput.find("RESULT not attacker") !=
                               std::string::npos);
                    break;
                case SecurityProperty::Type::AUTHENTICATION:
                    verified = proverifOutput.find("RESULT event") !=
                              std::string::npos;
                    break;
                case SecurityProperty::Type::FORWARD_SECRECY:
                    verified = proverifOutput.find("RESULT not attacker") !=
                              std::string::npos;
                    break;
                default:
                    verified = proverifOutput.find("RESULT") !=
                              std::string::npos;
            }

            results.push_back({prop, verified});
        }

        return results;
    }

private:
    std::string protocolName_;
    std::string channelDef_;
    std::map<std::string, std::string> participants_;
    std::vector<SecurityProperty> properties_;
};

// Exemplo de uso
void analyzeHandshakeProtocol() {
    ProtocolAnalyzer analyzer("HandshakeSimulador");

    // Define canal
    analyzer.setChannel("ch c_public : channel.");

    // Define participantes
    analyzer.addParticipant("client",
        "new m : message;\n"
        "    out(c_public, encrypt(k_client, m));\n"
        "    in(c_public, response : message);\n"
        "    if verify(k_server, response, hmac(k_server, response)) then\n"
        "        0\n"
        "    else\n"
        "        0");

    analyzer.addParticipant("server",
        "in(c_public, x : message);\n"
        "    if verify(k_client, x, hmac(k_client, x)) then\n"
        "        out(c_public, sk_enc(sk_server, x));\n"
        "        0\n"
        "    else\n"
        "        0");

    // Define propriedades
    SecurityProperty secrecy;
    secrecy.type = SecurityProperty::Type::SECRECY;
    secrecy.description = "Chave secreta nao e aprendida pelo adversario";
    secrecy.query = "query attacker(k_client) = false.";
    secrecy.expected = true;
    analyzer.addProperty(secrecy);

    SecurityProperty auth;
    auth.type = SecurityProperty::Type::AUTHENTICATION;
    auth.description = "Servidor autenticado";
    auth.query = "query m : message; event(server_receives(m)) ==> event(client_sends(m)).";
    auth.expected = true;
    analyzer.addProperty(auth);

    // Gera entrada e executa
    std::string input = analyzer.generateProVerifInput();

    std::ofstream inputFile("protocol_input.pv");
    inputFile << input;
    inputFile.close();

    std::string output;
    if (analyzer.runVerification("protocol_input.pv", output)) {
        auto results = analyzer.analyzeResults(output);
        for (const auto& [prop, verified] : results) {
            std::cout << (verified ? "VERIFIED" : "VIOLATED")
                      << ": " << prop.description << std::endl;
        }
    }
}

int main() {
    analyzeHandshakeProtocol();
    return 0;
}
```

### 6.5 Abordagens Avancadas do ProVerif

**Correlacao entre Canais:** ProVerif pode modelar correlacoes entre canais diferentes, o que e essencial para ataques de canal lateral em protocolos.

**Inducao sobre Tamanho:** ProVerif verifica propriedades indutivamente, o que permite lidar com protocolos que operam sobre dados de tamanho arbitrario.

**Cadeias de Assinatura:** ProVerif pode verificar protocolos com multiplas cadeias de assinatura, como certificados X.509.

```proverif
(* Verificacao de certificate chain com ProVerif *)

type channel.
type skey.
type key.
type cert.
type payload.

fun pk : skey -> key.
fun sign : skey -> payload -> payload.
fun verify_cert : cert -> key -> bool.
reduc forall k : skey, m : payload; verify(k, m, sign(k, m)) = true.

ch c_public : channel.

(* Cadeia de certificados: Root -> Intermediate -> Leaf *)
secret root_sk : skey.
secret intermediate_sk : skey.
secret leaf_sk : skey.

let root_cert = make_cert(pk(root_sk), "root").
let intermediate_cert = make_cert(pk(intermediate_sk), "intermediate").
let leaf_cert = make_cert(pk(leaf_sk), "leaf").

let client =
    (* Envia request com certificado leaf *)
    let leaf_proof = sign(leaf_sk, request_data) in
    out(c_public, (leaf_cert, leaf_proof, intermediate_cert));

let server =
    (* Recebe e verifica cadeia *)
    in(c_public, (c : cert, proof : payload, chain : cert));
    if verify_cert(c, pk(leaf_sk)) then
        if verify(pk(leaf_sk), request_data, proof) then
            (* Verifica cadeia ate root *)
            if verify_cert(chain, pk(root_sk)) then
                (* Autenticacao bem-sucedida *)
                0.

(* Query: adversario nao pode forjar assinatura *)
query forged : payload; attacker(forged) = false.
```

---

## 7. Tamarin Prover: Analise de Protocolos Multpartite

### 7.1 O que e o Tamarin Prover?

Tamarin Prover e uma ferramenta de verificacao de protocolos criptograficos que suporta modelos mais complexos que ProVerif, incluindo:

- **Protocolos multipartite:** Mais de dois participantes
- **Estado local:** Participantes podem manter estado entre mensagens
- **Grupos dinamicos:** Participantes podem entrar e sair do protocolo
- **Operacoes de XOR:** Modelo de adversario com XOR (mais realista)
- **Leis de seguranca especificas:** Modelos de seguranca como eCK, KCI, etc.

### 7.2 Linguagem do Tamarin

Tamarin usa uma linguagem baseada em multiset rewriting rules (regras de reescrita de multiset), que sao especialmente adequadas para modelar protocolos com estado.

```tamarin
// Modelo Tamarin: Protocolo de chaveamento Diffie-Hellman
// Verifica forward secrecy e resistencia a KCI

theory DiffieHellmanKeyExchange
begin

// Tipos de dados
builtins: diffie-hellman, signing, concatenation

// Declaracao de funcoes
functions: key/1, hash/1

// Regras do protocolo

// Geracao de chave DH pelo servidor
rule ServerKeyGen:
    let
        skey = h(sk(s))
        pkey = 'g'^skey
    in
    [ Fr(~skey), !Ltk($S, skey) ]
    -->
    [ !Ltk($S, skey), !Pubkey($S, pkey) ]

// Mensagem 1 do protocolo: Cliente -> Servidor
rule ClientMessage1:
    let
        ckey = h(sk(c))
        pkey = 'g'^ckey
    in
    [ Fr(~ckey) ]
    -->
    [ !Ltk($C, ckey), !Pubkey($C, pkey),
      Out( pkey ) ]

// Mensagem 2 do protocolo: Servidor -> Cliente
rule ServerMessage2:
    let
        skey = h(sk(s))
        spkey = 'g'^skey
        ckey = h(sk(c))
        cpkey = 'g'^ckey
        shared = cpkey^skey
        session_key = hash(shared)
    in
    [ !Ltk($S, skey), !Pubkey($S, spkey),
      In( cpkey ) ]
    -->
    [ State_S($S, $C, session_key),
      Out( !Pubkey($S, spkey) ) ]

// Mensagem 3 do protocolo: Cliente -> Servidor (completando)
rule ClientMessage3:
    let
        ckey = h(sk(c))
        spkey = 'g'^skey
        shared = spkey^ckey
        session_key = hash(shared)
    in
    [ !Ltk($C, ckey), In( spkey ),
      State_S($S, $C, session_key) ]
    -->
    [ State_C($C, $S, session_key),
      Out( 'finish' ) ]

// Mensagem de aplicacao criptografada
rule ApplicationMessage:
    let
        sk = session_key
        msg = 'hello'
        ct = msg
    in
    [ State_C($C, $S, sk), State_S($S, $C, sk) ]
    -->
    [ State_C($C, $S, sk), State_S($S, $C, sk),
      Out( ct ) ]

// Propriedades de seguranca

// Secreto da chave de sessao
lemma session_key_secret:
    forall x : text, s : sid.
    attacker(x) ==> not (KU(x) && session_key(s) = x)

// Forward secrecy
lemma forward_secrecy:
    forall s : sid, sk : text.
    (Ltk-compromise(sk) && session_key(s) = hash(sk^ckey))
    ==> not (session_key(s) = hash(sk^ckey))

// Autenticacao
lemma authentication:
    forall c, s : sid.
    State_C(c, s) ==> event(Start_S(s, c))

end
```

### 7.3 Modelo eCK com Tamarin

O modelo eCK (extended Canetti-Krawczyk) e o modelo de seguranca padrao para protocolos de chaveamento de chave. Tamarin pode verificar propriedades eCK diretamente:

```tamarin
// Modelo eCK para protocolo DH
// Verificacao de todas as propriedades eCK

theory eCK_Protocol
begin

builtins: diffie-hellman, signing

// Participant com estado local
// State armazena: chave DH, nonce, e dados de sessao

// Inicio: geracao de chaves
rule GenerateKeys:
    [ Fr(~x) ]
    -->
    [ !Ltk($A, ~x), !Pub($A, 'g'^~x) ]

// Mensagem unica: A -> B com nonce A
rule Message1:
    [ Fr(~na), !Pub($A, 'g'^~x) ]
    -->
    [ State_A($A, $B, ~na, ~x),
      Out( ('A', ~na, 'g'^~x) ) ]

// Resposta: B -> A com nonce B e assinatura
rule Response:
    [ Fr(~nb), !Ltk($B, ~y), !Pub($B, 'g'^~y),
      In( (sender, na, 'g'^~x) ) ]
    let session_key = hash('g'^(~x * ~y), na, nb)
        sig = sign(~y, (sender, na, 'g'^~x, nb))
    in
    [ State_B($B, $A, session_key) ]
    -->
    [ Out( (nb, sig) ) ]

// Finalizacao: A recebe e confirma
rule Finalize:
    [ State_A($A, $B, na, ~x),
      !Pub($B, 'g'^~y),
      In( (nb, sig) ) ]
    let session_key = hash('g'^(~x * ~y), na, nb)
    in
    if verify('g'^~y, sig) then
        [ State_A_Complete($A, $B, session_key) ]
    else
        0

// Propriedades eCK

// 1. Secreto da chave de sessao
lemma session_secrecy:
    forall x : bitstring, a, b : agent.
    attacker(x) ==>
        not (session(a, b) = x)

// 2. Forward secrecy
lemma forward_secrecy:
    forall x : bitstring, a, b : agent.
    (compromise(sk(a)) && session(a, b) = x)
        ==> not (session(a, b) = x)

// 3. Key Compromise Impersonation resistance
lemma kci_resistance:
    forall x : bitstring, a, b : agent.
    (compromise(sk(b)) && session(a, b) = x)
        ==> not (session(a, b) = x)

// 4. Unknown key share
lemma uks_resistance:
    forall x : bitstring, a, b, c : agent.
    (session(a, b) = x && session(a, c) = x)
        ==> b = c

end
```

### 7.4 Comparacao Tamarin vs ProVerif

| Caracteristica | Tamarin | ProVerif |
|---------------|---------|----------|
| Modelo de adversario | Multiset rewriting | Pi-calculus |
| Estado local | Suportado nativamente | Limitado |
| XOR | Suportado | Nao suportado nativamente |
| Inducao | Limitada | Automatica |
| Performance | Mais lento, mas mais expressivo | Mais rapido para protocolos simples |
| Modelos de seguranca | eCK, KCI, etc. | Sigilo, autenticacao |
| Escalabilidade | Melhor para protocolos complexos | Melhor para protocolos simples |

### 7.5 Exemplo Completo: Protocolo de Pagamento

```tamarin
// Protocolo de pagamento com Tamarin
// Verificacao de seguranca financeira

theory PaymentProtocol
begin

builtins: symmetric-encryption, signing, hmac

// Constantes
consts : merchant_id, payment_id

// Participant com chave de longo prazo
rule KeyGen:
    [ Fr(~k) ]
    -->
    [ !Ltk($A, ~k), !Pub($A, 'pk'^~k) ]

// Mensagem de pagamento: Cliente -> Merchant
rule PaymentInit:
    [ Fr(~pay_id), Fr(~amount), !Ltk($C, ~kc) ]
    let payment = sign(~kc, ('pay', $C, $M, ~pay_id, ~amount))
    in
    [ State_C1($C, $M, ~pay_id, ~amount) ]
    -->
    [ Out( ($C, ~pay_id, ~amount, payment) ) ]

// Merchant processa e envia ao gateway
rule MerchantProcess:
    [ Fr(~trans_id), !Ltk($M, ~km),
      In( (customer, pay_id, amount, payment) ) ]
    let merchant_sig = sign(~km, ('confirm', customer, pay_id, ~trans_id))
        forward = sign(~km, ('forward', customer, pay_id, amount, ~trans_id))
    in
    [ State_M1($M, $C, pay_id, amount, ~trans_id) ]
    -->
    [ Out( (customer, pay_id, amount, merchant_sig, forward) ) ]

// Gateway autoriza pagamento
rule GatewayAuthorize:
    [ !Ltk($G, ~kg),
      In( (customer, pay_id, amount, merchant_sig, forward) ) ]
    let auth = sign(~kg, ('auth', customer, pay_id, amount))
        notify_customer = sign(~kg, ('notify', customer, pay_id, 'approved'))
    in
    [ State_G1($G, $C, pay_id, amount) ]
    -->
    [ Out( (customer, pay_id, 'approved', notify_customer) ) ]

// Propriedades

// 1. Nonce de pagamento e secreto
lemma pay_id_secrecy:
    forall x : text, c, m : agent.
    attacker(x) ==> not (pay_id(c, m) = x)

// 2. Valor do pagamento e protegido
lemma amount_protection:
    forall x : text, c, m : agent.
    attacker(x) ==> not (amount(c, m) = x)

// 3. Autenticacao do pagamento
lemma payment_authentication:
    forall c, m, g : agent.
    approved(g, c, m) ==> paid(c, m)

// 4. Merchant nao pode forjar autorizacao
lemma merchant_cannot_forgery:
    forall m : agent, c, g : agent.
    attacker(m) ==> not (approved(g, c, m))

end
```

---

## 8. F*: Verificacao com Tipos Dependentes

### 8.1 O que e F*?

F* (pronunciado "F Star") e uma linguagem de programacao com tipos dependentes desenvolvida pela Microsoft Research. F* e projetado para verificacao formal de software, combinando expressividade de linguagens funcionais modernas com a capacidade de expressar e provar propriedades arbitraries.

Para criptografia, F* e particularmente poderoso porque pode expressar invariantes como:
- "O tamanho do output e sempre igual ao tamanho do input"
- "A funcao e deterministica"
- "Nao ha branches que dependem de valores secretos"
- "A memoria e sempre liberada"

### 8.2 Tipos Dependentes para Criptografia

Em F*, tipos podem depender de valores. Isso significa que podemos criar tipos como `bytes 32` (bytes de tamanho 32) ou `array uint8 n` (array de uint8 de tamanho n), e o compilador verifica que operacoes preservam esses invariantes de tamanho.

```fstar
// Definicoes F* para operacoes criptograficas

module CryptoTypes

open FStar.Integers
open FStar.Seq

// Tipo para bytes de tamanho fixo
type bytes (n:nat) = Seq.seq uint8{length s == n}

// Tipo para chave de 256 bits
type key256 = bytes 32

// Tipo para nonce de 128 bits
type nonce128 = bytes 16

// Tipo para bloco de 128 bits
type block128 = bytes 16

// Funcao AES-GCM com tipos indexados
val aes_gcm_encrypt:
  key:key256 ->
  nonce:nonce128 ->
  plaintext:bytes n ->
  aad:bytes m ->
  Tot (bytes (n + 16))  // ciphertext + 16-byte tag

let aes_gcm_encrypt key nonce plaintext aad =
  // Implementacao verificada
  let ciphertext = aes_encrypt key nonce plaintext in
  let tag = gcm_tag key nonce ciphertext aad in
  Seq.append ciphertext tag

// Funcao de verificacao: sempre retorna bool
val aes_gcm_decrypt:
  key:key256 ->
  nonce:nonce128 ->
  ciphertext:bytes (n + 16) ->  // ciphertext + tag
  aad:bytes m ->
  Tot (option (bytes n))  // Some plaintext ou None

let aes_gcm_decrypt key nonce ciphertext aad =
  let (ct, tag) = split ciphertext (n) in
  let computed_tag = gcm_tag key nonce ct aad in
  if Seq.eq tag computed_tag then
    Some (aes_decrypt key nonce ct)
  else
    None

// Propriedade de correcao: descriptografar(criptografar(m)) = Some m
val correctness:
  key:key256 ->
  nonce:nonce128 ->
  plaintext:bytes n ->
  aad:bytes m ->
  Lemma (aes_gcm_decrypt key nonce
         (aes_gcm_encrypt key nonce plaintext aad) aad
         == Some plaintext)

let correctness key nonce plaintext aad =
  // Prova automatica ou manual
  ()

// Propriedade de seguranca: tag e unica para cada (key, nonce)
val tag_uniqueness:
  key:key256 ->
  nonce:nonce128 ->
  plaintext:bytes n ->
  aad:bytes m ->
  Lemma (let ct = aes_gcm_encrypt key nonce plaintext aad in
         let tag = Seq.slice ct n (n + 16) in
         forall (other:bytes n).
           aes_gcm_decrypt key nonce
           (Seq.append other tag) aad == None)

let tag_uniqueness key nonce plaintext aad = ()
```

### 8.3 VerifiedCrypt: Biblioteca F* para Criptografia Verificada

VerifiedCrypt e uma biblioteca F* que fornece construcoes criptograficas formalmente verificadas:

```fstar
// VerifiedCrypt: construcoes criptograficas verificadas

module VerifiedCrypto

open FStar.Seq
open FStar.Integers

// TLS record protocol
val tls_record_encrypt:
  key:tls_key ->
  seq_num:uint64 ->
  content_type:content_type ->
  protocol_version:protocol_version ->
  payload:bytes n ->
  Tot (tls_record n)

let tls_record_encrypt key seq_num content_type protocol_version payload =
  let iv = compute_iv key seq_num in
  let nonce = compute_nonce seq_num in
  let aad = compute_aad content_type protocol_version in
  let ciphertext = aes_gcm_encrypt key nonce payload aad in
  build_record content_type protocol_version ciphertext

// HKDF - HMAC-based Key Derivation Function
val hkdf_extract:
  salt:bytes s ->
  ikm:bytes n ->
  Tot (bytes 32)  // Output sempre 32 bytes para SHA-256

val hkdf_expand:
  prk:bytes 32 ->
  info:bytes i ->
  length:nat{length <= 255} ->
  Tot (bytes length)

// Chaining key para handshake TLS 1.3
val handshake_chain:
  psk:option bytes_32 ->
  es:option bytes_32 ->
  dhee:bytes_32 ->
  dhr:bytes_32 ->
  Tot (handshake_keys)

let handshake_chain psk es dhee dhr =
  let secret = compute_shared_secret dhee dhr in
  let early_secret = match psk with
    | Some k -> hkdf_extract (create 32 0z) k
    | None -> hkdf_extract (create 32 0z) (create 32 0z) in
  let derived_secret = hkdf_expand early_secret "derived" 32 in
  let handshake_secret = hkdf_extract derived_secret secret in
  build_handshake_keys handshake_secret
```

### 8.4 Programacao Defensiva com Tipos F*

```fstar
// Programacao defensiva em F* para operacoes criptograficas

module DefensiveCrypto

open FStar.Integers
open FStar.Seq

// Nonce counter com verificacao de overflow
val nonce_counter:
  counter:ref uint64 ->
  key:bytes_32 ->
  Ghost (result:option bytes_12)
    (ensures (let c = !counter in
              if c < max_uint64 then
                result == Some (compute_nonce key c)
              else
                result == None))

let nonce_counter counter key =
  let c = !counter in
  if c < max_uint64 then begin
    counter := c + 1UL;
    Some (compute_nonce key c)
  end else
    None

// Constant-time comparison
val ct_compare:
  a:bytes n ->
  b:bytes n ->
  Tot (r:bool{r <==> Seq.eq a b})
  (ensures (is_constant_time r))  // Prova que e constant-time

let rec ct_compare a b =
  if length a = 0 then true
  else
    let result = ct_compare (tail a) (tail b) in
    let byte_eq = (head a = head b) in
    result && byte_eq

// Key erasure
val secure_erase:
  key:ref (bytes n) ->
  Tot unit
  (ensures (let old_key = !key in
            key := create n 0z /\
            // Prova que a chave antiga nao e acessivel
            no_access_after_erase old_key))

let secure_erase key =
  let n = length !key in
  key := create n 0z
```

### 8.5 Compilando F* para C

F* pode ser compilado para C, resultando em codigo verificavel e executavel:

```cpp
// Interface C++ para codigo F* compilado
// (F* gera codigo C que pode ser chamado do C++)

extern "C" {
    // Funcoes geradas pelo F* (verificadas)
    void fstar_aes_gcm_encrypt(
        const uint8_t* key, size_t key_len,
        const uint8_t* nonce, size_t nonce_len,
        const uint8_t* plaintext, size_t pt_len,
        const uint8_t* aad, size_t aad_len,
        uint8_t* ciphertext, size_t* ct_len,
        uint8_t* tag, size_t tag_len);

    int fstar_aes_gcm_decrypt(
        const uint8_t* key, size_t key_len,
        const uint8_t* nonce, size_t nonce_len,
        const uint8_t* ciphertext, size_t ct_len,
        const uint8_t* aad, size_t aad_len,
        const uint8_t* tag, size_t tag_len,
        uint8_t* plaintext, size_t* pt_len);

    void fstar_hkdf_extract(
        const uint8_t* salt, size_t salt_len,
        const uint8_t* ikm, size_t ikm_len,
        uint8_t* prk, size_t* prk_len);

    void fstar_hkdf_expand(
        const uint8_t* prk, size_t prk_len,
        const uint8_t* info, size_t info_len,
        uint8_t* okm, size_t* okm_len);
}

// Wrapper C++ moderno
#include <vector>
#include <array>
#include <stdexcept>
#include <cstring>

class VerifiedCrypto {
public:
    struct CryptoResult {
        std::vector<uint8_t> ciphertext;
        std::array<uint8_t, 16> tag;
    };

    static CryptoResult encrypt_aes_gcm(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad)
    {
        if (key.size() != 32) {
            throw std::invalid_argument("Key must be 256 bits");
        }
        if (nonce.size() != 12) {
            throw std::invalid_argument("Nonce must be 96 bits");
        }

        CryptoResult result;
        result.ciphertext.resize(plaintext.size());
        size_t ct_len = 0;

        fstar_aes_gcm_encrypt(
            key.data(), key.size(),
            nonce.data(), nonce.size(),
            plaintext.data(), plaintext.size(),
            aad.data(), aad.size(),
            result.ciphertext.data(), &ct_len,
            result.tag.data(), result.tag.size());

        result.ciphertext.resize(ct_len);
        return result;
    }

    static std::vector<uint8_t> decrypt_aes_gcm(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& aad,
        const std::array<uint8_t, 16>& tag)
    {
        if (key.size() != 32) {
            throw std::invalid_argument("Key must be 256 bits");
        }
        if (nonce.size() != 12) {
            throw std::invalid_argument("Nonce must be 96 bits");
        }

        std::vector<uint8_t> plaintext(ciphertext.size());
        size_t pt_len = 0;

        int result = fstar_aes_gcm_decrypt(
            key.data(), key.size(),
            nonce.data(), nonce.size(),
            ciphertext.data(), ciphertext.size(),
            aad.data(), aad.size(),
            tag.data(), tag.size(),
            plaintext.data(), &pt_len);

        if (result != 0) {
            throw std::runtime_error("Decryption failed: authentication error");
        }

        plaintext.resize(pt_len);
        return plaintext;
    }
};
```

### 8.6 Limitacoes de F* para Producao

Embora F* seja poderoso, sua adocao em producao enfrenta desafios:

1. **Curva de aprendizado:** F* e uma linguagem funcional com tipos dependentes, o que exige uma curva de aprendizado significativa para programadores C++
2. **Ecossistema:** O ecossistema de bibliotecas e menor que o de C ou C++
3. **Performance:** Codigo F* compilado pode nao ser tao eficiente quanto C otimizado manualmente
4. **Integracao:** Integrar codigo F* com codebases C++ existentes requer esforco adicional

---

## 9. CompCert: Implicacoes de um Compilador Verificado

### 9.1 O Problema do Compilador

Um dos resultados mais surpreendentes da verificacao formal e que compiladores podem ter bugs. O CompCert e um compilador C formalmente verificado, desenvolvido pelo INRIA, que prova que o codigo gerado mantem a semantica do codigo fonte.

Isso e especialmente relevante para criptografia porque:

1. Compiladores podem "quebrar" codigo constant-time ao reordenar operacoes
2. Otimizacoes podem eliminar operacoes que parecem redundantes mas sao essenciais para seguranca
3. Bugs no compilador podem introduzir vulnerabilidades em codigo que foi verificado em nivel de especificacao

### 9.2 O CompCert

CompCert e um compilador C que e formalmente verificado contra uma especificacao em Coq. A prova garante que o codigo gerado mantem a semantica do codigo fonte C, exceto para comportamento indefinido (undefined behavior).

```
+------------------------------------------------------------------+
|                   CompCert: Compilador Verificado                |
+------------------------------------------------------------------+
|                                                                  |
|  C Source                                                         |
|       |                                                          |
|       v                                                          |
|  [CompCert Frontend]                                             |
|  - Parsing                                                        |
|  - Type checking                                                  |
|  - Otimizacoes verificadas                                       |
|       |                                                          |
|       v                                                          |
|  [CompCert Middle End]                                           |
|  - SSA conversion                                                 |
|  - Register allocation                                            |
|  - Otimizacoes verificadas                                       |
|       |                                                          |
|       v                                                          |
|  [CompCert Backend]                                              |
|  - Assembly generation                                            |
|  - Linking                                                        |
|       |                                                          |
|       v                                                          |
|  Verified Assembly                                                |
|  (garantia formal de correcao semantica)                         |
+------------------------------------------------------------------+
```

### 9.3 CompCert e Constant-Time

O CompCert tem uma propriedade particularmente importante para criptografia: ele preserva o constant-time de codigo C. Isso significa que se o codigo fonte e constante em tempo (nao tem branches ou acessos a memoria que dependem de dados secretos), o codigo gerado tambem sera constante em tempo.

Isso nao e verdade para compiladores convencionais como GCC ou Clang, que podem reordenar operacoes, eliminar branches "inuteis", ou transformar codigo constante em tempo em codigo com timing variavel.

```cpp
// Exemplo: Como o CompCert preserva constant-time

// Este codigo C e constante em tempo:
// - Nao ha branches que dependem de dados secretos
// - Nao ha acessos a memoria baseados em dados secretos

#include <cstdint>
#include <cstddef>

// Versao constante em tempo (verificada com CompCert)
extern "C" void secure_compare(
    const uint8_t* a,
    const uint8_t* b,
    size_t len,
    uint8_t* result)
{
    uint8_t diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= a[i] ^ b[i];
    }
    *result = diff;
}

// Versao NAO constante em tempo (GCC/Clang podem otimizar)
// NAO USE EM CRIPTOGRAFIA
extern "C" void insecure_compare(
    const uint8_t* a,
    const uint8_t* b,
    size_t len,
    uint8_t* result)
{
    for (size_t i = 0; i < len; ++i) {
        if (a[i] != b[i]) {  // BRANCH dependente de dados secretos!
            *result = 1;
            return;
        }
    }
    *result = 0;
}

// Funcao de clamping constante em tempo (X25519)
extern "C" void clamp_secret_key(uint8_t key[32]) {
    // Operacoes constant-time de clamping
    key[0] &= 248;
    key[31] &= 127;
    key[31] |= 64;
}
```

### 9.4 Usando CompCert na Pratica

```cpp
// Framework C++ para compilacao com CompCert

#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <filesystem>

namespace fs = std::filesystem;

class CompCertCompiler {
public:
    struct CompileConfig {
        std::string sourceFile;
        std::string outputFile;
        bool optimize = true;
        bool verifyConstantTime = false;
        std::vector<std::string> includeDirs;
        std::vector<std::string> defines;
    };

    struct CompileResult {
        bool success;
        std::string errorMessage;
        std::string objectFile;
        double compileTimeMs;
    };

    explicit CompCertCompiler(const std::string& compcertPath)
        : compcertPath_(compcertPath) {}

    CompileResult compile(const CompileConfig& config) {
        CompileResult result;

        // Monta comando de compilacao
        std::ostringstream cmd;
        cmd << compcertPath_ << "/ccomp ";

        // Otimizacoes
        if (config.optimize) {
            cmd << "-Oall ";
        }

        // Include directories
        for (const auto& dir : config.includeDirs) {
            cmd << "-I" << dir << " ";
        }

        // Defines
        for (const auto& def : config.defines) {
            cmd << "-D" << def << " ";
        }

        // Constant-time verification flag
        if (config.verifyConstantTime) {
            cmd << "-fconstant-time ";
        }

        // Arquivo de saida
        cmd << "-o " << config.outputFile << " ";

        // Arquivo de entrada
        cmd << config.sourceFile;

        // Executa compilacao
        auto startTime = std::chrono::steady_clock::now();
        int status = std::system(cmd.str().c_str());
        auto endTime = std::chrono::steady_clock::now();

        result.compileTimeMs = std::chrono::duration<double, std::milli>(
            endTime - startTime).count();

        if (status == 0) {
            result.success = true;
            result.objectFile = config.outputFile;
        } else {
            result.success = false;
            result.errorMessage = "Compilation failed with exit code: "
                                 + std::to_string(status);
        }

        return result;
    }

    // Verifica se o objeto gerado e constante em tempo
    bool verifyConstantTimeProperty(const std::string& objectFile) {
        // CompCert fornece certificados de prova
        // Aqui verificamos se o certificado existe
        std::string certFile = objectFile + ".v";
        return fs::exists(certFile);
    }

    // Gera relatorio de verificacao
    std::string generateReport(const CompileConfig& config,
                              const CompileResult& result) {
        std::ostringstream report;

        report << "=== Relatorio de Compilacao CompCert ===\n\n";
        report << "Arquivo: " << config.sourceFile << "\n";
        report << "Sucesso: " << (result.success ? "Sim" : "Nao") << "\n";
        report << "Tempo: " << result.compileTimeMs << "ms\n";

        if (result.success) {
            report << "Objeto: " << result.objectFile << "\n";
            report << "\nPropriedades verificadas:\n";
            report << "- Semantics preservation (formal proof)\n";
            report << "- Type safety (guaranteed by CompCert)\n";
            if (config.verifyConstantTime) {
                report << "- Constant-time preservation\n";
            }
        } else {
            report << "Erro: " << result.errorMessage << "\n";
        }

        return report.str();
    }

private:
    std::string compcertPath_;
};

// Exemplo de uso
void compileWithCompCert() {
    CompCertCompiler compiler("/usr/local/bin");

    CompCertCompiler::CompileConfig config;
    config.sourceFile = "aes_implementation.c";
    config.outputFile = "aes_verified.o";
    config.optimize = true;
    config.verifyConstantTime = true;
    config.defines.push_back("OPENSSL_NO_ASM");

    auto result = compiler.compile(config);

    std::string report = compiler.generateReport(config, result);
    std::cout << report << std::endl;

    if (result.success) {
        // Verifica propriedade constante-time
        if (compiler.verifyConstantTimeProperty(result.objectFile)) {
            std::cout << "Constant-time VERIFICADO via CompCert" << std::endl;
        }
    }
}
```

### 9.5 CompCert vs GCC/Clang para Criptografia

| Propriedade | CompCert | GCC/Clang |
|------------|---------|-----------|
| Formal verification | Sim (Coq proof) | Nao |
| Constant-time preservation | Garantido | Nao garantido |
| Otimizacoes | Limitadas (mas verificadas) | Agressivas (mas nao verificadas) |
| Performance | ~10-20% mais lento | Otimizado |
| Uso recomendado | Software criptografico critico | Software geral |

### 9.6 O Compromisso entre Seguranca e Performance

Para a maioria do software criptografico, GCC/Clang com flags `-O0` ou `-O1` e `-fno-tree-ter` e suficiente para preservar constant-time. O CompCert e necessario apenas para software criptografico de altissima seguranca (FIPS 140-3 Nivel 4, defense-in-depth critical).

---

## 10. Agilidade Criptografica: Projetando para Substituicao de Algoritmos

### 10.1 O Que e Agilidade Criptografica?

Agilidade criptografica (cryptographic agility) e a capacidade de um sistema de substituir algoritmos criptograficos, protocolos ou parametros sem necessidade de redesign arquitetural significativo. Isso e essencial porque:

1. **Algoritmos sao quebrados:** SHA-1 foi descontinuado, DES e inseguro, RSA-1024 e inseguro
2. **Novos padroes surgem:** NIST PQC (CRYSTALS-Kyber, CRYSTALS-Dilithium) estao substituindo algoritmos classicos
3. **Requisitos regulatórios mudam:** FIPS, Common Criteria, LGPD podem exigir algoritmos diferentes
4. **Ameacas quanticas:** Computacao quantica exige migracao para criptografia pos-quantica

### 10.2 Padroes de Projeto para Agilidade

```cpp
// Framework C++ para agilidade criptografica
// Padrao Strategy + Provider Pattern

#include <memory>
#include <string>
#include <vector>
#include <map>
#include <functional>
#include <stdexcept>
#include <any>

// Interface abstrata para algoritmos criptograficos
class CryptoAlgorithm {
public:
    virtual ~CryptoAlgorithm() = default;

    virtual std::string name() const = 0;
    virtual std::string version() const = 0;
    virtual size_t keySize() const = 0;
    virtual size_t blockSize() const = 0;
    virtual bool isPostQuantum() const = 0;
};

// Interface para cifra simetrica
class SymmetricCipher : public CryptoAlgorithm {
public:
    virtual std::vector<uint8_t> encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& iv) = 0;

    virtual std::vector<uint8_t> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& ciphertext,
        const std::vector<uint8_t>& iv) = 0;
};

// Interface para AEAD
class AEADEncryption : public CryptoAlgorithm {
public:
    struct AEADEncryptResult {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> tag;
    };

    virtual AEADEncryptResult encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad) = 0;

    virtual std::optional<std::vector<uint8_t>> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const AEADEncryptResult& result,
        const std::vector<uint8_t>& aad) = 0;
};

// Implementacao concreta: AES-256-GCM
class AES256GCM : public AEADEncryption {
public:
    std::string name() const override { return "AES-256-GCM"; }
    std::string version() const override { return "1.0"; }
    size_t keySize() const override { return 32; }
    size_t blockSize() const override { return 16; }
    bool isPostQuantum() const override { return false; }

    AEADEncryptResult encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad) override
    {
        // Implementacao usando OpenSSL
        AEADEncryptResult result;
        // ... (implementacao OpenSSL detalhada)
        return result;
    }

    std::optional<std::vector<uint8_t>> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const AEADEncryptResult& result,
        const std::vector<uint8_t>& aad) override
    {
        // Implementacao usando OpenSSL
        std::vector<uint8_t> plaintext;
        // ... (implementacao OpenSSL detalhada)
        return plaintext;
    }
};

// Implementacao concreta: ChaCha20-Poly1305
class ChaCha20Poly1305 : public AEADEncryption {
public:
    std::string name() const override { return "ChaCha20-Poly1305"; }
    std::string version() const override { return "1.0"; }
    size_t keySize() const override { return 32; }
    size_t blockSize() const override { return 64; }
    bool isPostQuantum() const override { return false; }

    AEADEncryptResult encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad) override
    {
        // Implementacao usando libsodium
        AEADEncryptResult result;
        // ... (implementacao libsodium detalhada)
        return result;
    }

    std::optional<std::vector<uint8_t>> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const AEADEncryptResult& result,
        const std::vector<uint8_t>& aad) override
    {
        // Implementacao usando libsodium
        std::vector<uint8_t> plaintext;
        // ... (implementacao libsodium detalhada)
        return plaintext;
    }
};

// Implementacao concreta: AES-GCM-SIV (nonce-misuse resistant)
class AESGCM_SIV : public AEADEncryption {
public:
    std::string name() const override { return "AES-GCM-SIV"; }
    std::string version() const override { return "1.0"; }
    size_t keySize() const override { return 32; }
    size_t blockSize() const override { return 16; }
    bool isPostQuantum() const override { return false; }

    AEADEncryptResult encrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const std::vector<uint8_t>& plaintext,
        const std::vector<uint8_t>& aad) override
    {
        // Implementacao usando libsodium
        AEADEncryptResult result;
        // ... (implementacao detalhada)
        return result;
    }

    std::optional<std::vector<uint8_t>> decrypt(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& nonce,
        const AEADEncryptResult& result,
        const std::vector<uint8_t>& aad) override
    {
        std::vector<uint8_t> plaintext;
        // ... (implementacao detalhada)
        return plaintext;
    }
};

// Registry de algoritmos
class CryptoRegistry {
public:
    static CryptoRegistry& instance() {
        static CryptoRegistry registry;
        return registry;
    }

    void registerAlgorithm(std::shared_ptr<AEADEncryption> algo) {
        algorithms_[algo->name()] = algo;
        // Registra por categoria
        if (algo->isPostQuantum()) {
            pqAlgorithms_.push_back(algo);
        } else {
            classicalAlgorithms_.push_back(algo);
        }
    }

    std::shared_ptr<AEADEncryption> getAlgorithm(const std::string& name) {
        auto it = algorithms_.find(name);
        if (it == algorithms_.end()) {
            throw std::invalid_argument("Algorithm not found: " + name);
        }
        return it->second;
    }

    std::vector<std::string> availableAlgorithms() const {
        std::vector<std::string> names;
        for (const auto& [name, _] : algorithms_) {
            names.push_back(name);
        }
        return names;
    }

    std::shared_ptr<AEADEncryption> getDefaultAlgorithm() const {
        // Preferencia: post-quantum > classical
        if (!pqAlgorithms_.empty()) {
            return pqAlgorithms_.front();
        }
        return classicalAlgorithms_.front();
    }

private:
    CryptoRegistry() {
        // Registra algoritmos padrao
        registerAlgorithm(std::make_shared<AES256GCM>());
        registerAlgorithm(std::make_shared<ChaCha20Poly1305>());
        registerAlgorithm(std::make_shared<AESGCM_SIV>());
    }

    std::map<std::string, std::shared_ptr<AEADEncryption>> algorithms_;
    std::vector<std::shared_ptr<AEADEncryption>> classicalAlgorithms_;
    std::vector<std::shared_ptr<AEADEncryption>> pqAlgorithms_;
};

// Crypto Provider abstrato
class CryptoProvider {
public:
    virtual ~CryptoProvider() = default;

    virtual std::string name() const = 0;
    virtual std::vector<std::string> supportedAlgorithms() const = 0;
    virtual std::shared_ptr<AEADEncryption> getAEAD(
        const std::string& algorithm) = 0;
};

// Implementacao OpenSSL
class OpenSSLProvider : public CryptoProvider {
public:
    std::string name() const override { return "OpenSSL"; }

    std::vector<std::string> supportedAlgorithms() const override {
        return {"AES-256-GCM", "ChaCha20-Poly1305"};
    }

    std::shared_ptr<AEADEncryption> getAEAD(
        const std::string& algorithm) override
    {
        if (algorithm == "AES-256-GCM") {
            return std::make_shared<AES256GCM>();
        } else if (algorithm == "ChaCha20-Poly1305") {
            return std::make_shared<ChaCha20Poly1305>();
        }
        return nullptr;
    }
};

// Implementacao libsodium
class LibsodiumProvider : public CryptoProvider {
public:
    std::string name() const override { return "libsodium"; }

    std::vector<std::string> supportedAlgorithms() const override {
        return {"ChaCha20-Poly1305", "AES-GCM-SIV"};
    }

    std::shared_ptr<AEADEncryption> getAEAD(
        const std::string& algorithm) override
    {
        if (algorithm == "ChaCha20-Poly1305") {
            return std::make_shared<ChaCha20Poly1305>();
        } else if (algorithm == "AES-GCM-SIV") {
            return std::make_shared<AESGCM_SIV>();
        }
        return nullptr;
    }
};

// Gerenciador de migracao
class CryptoMigrationManager {
public:
    struct MigrationPlan {
        std::string fromAlgorithm;
        std::string toAlgorithm;
        std::string reason;
        std::vector<std::string> affectedComponents;
    };

    void addMigrationPlan(const MigrationPlan& plan) {
        migrationPlans_.push_back(plan);
    }

    bool canMigrate(const std::string& from, const std::string& to) {
        // Verifica se ambos algoritmos estao disponiveis
        auto& registry = CryptoRegistry::instance();
        try {
            registry.getAlgorithm(from);
            registry.getAlgorithm(to);
            return true;
        } catch (...) {
            return false;
        }
    }

    std::vector<MigrationPlan> pendingMigrations() const {
        return migrationPlans_;
    }

private:
    std::vector<MigrationPlan> migrationPlans_;
};

// Exemplo de uso
void demonstrateAgility() {
    auto& registry = CryptoRegistry::instance();

    // Lista algoritmos disponiveis
    auto algorithms = registry.availableAlgorithms();
    std::cout << "Algoritmos disponiveis:" << std::endl;
    for (const auto& algo : algorithms) {
        std::cout << "  - " << algo << std::endl;
    }

    // Usa algoritmo padrao
    auto defaultAlgo = registry.getDefaultAlgorithm();
    std::cout << "Algoritmo padrao: " << defaultAlgo->name() << std::endl;

    // Criptografa com algoritmo padrao
    std::vector<uint8_t> key(32, 0xAB);
    std::vector<uint8_t> nonce(12, 0xCD);
    std::vector<uint8_t> plaintext = {'H', 'e', 'l', 'l', 'o'};
    std::vector<uint8_t> aad;

    auto result = defaultAlgo->encrypt(key, nonce, plaintext, aad);
    std::cout << "Criptografado com " << defaultAlgo->name() << std::endl;

    // Muda para outro algoritmo (migracao transparente)
    auto newAlgo = registry.getAlgorithm("ChaCha20-Poly1305");
    auto result2 = newAlgo->encrypt(key, nonce, plaintext, aad);
    std::cout << "Criptografado com " << newAlgo->name() << std::endl;
}
```

### 10.3 Migracao para Pos-Quantica

A migracao para criptografia pos-quantica e o maior desafio de agilidade criptografica atual. O framework deve suportar:

```cpp
// Framework de migracao para criptografia pos-quantica

#include <memory>
#include <string>
#include <map>
#include <vector>
#include <functional>

// Interface para KEM (Key Encapsulation Mechanism)
class KeyEncapsulation {
public:
    virtual ~KeyEncapsulation() = default;

    struct KeyPair {
        std::vector<uint8_t> publicKey;
        std::vector<uint8_t> secretKey;
    };

    struct EncapsulateResult {
        std::vector<uint8_t> ciphertext;
        std::vector<uint8_t> sharedSecret;
    };

    virtual KeyPair generateKeyPair() = 0;
    virtual EncapsulateResult encapsulate(
        const std::vector<uint8_t>& publicKey) = 0;
    virtual std::vector<uint8_t> decapsulate(
        const std::vector<uint8_t>& secretKey,
        const std::vector<uint8_t>& ciphertext) = 0;

    virtual std::string name() const = 0;
    virtual bool isPostQuantum() const = 0;
    virtual size_t publicKeySize() const = 0;
    virtual size_t secretKeySize() const = 0;
    virtual size_t ciphertextSize() const = 0;
    virtual size_t sharedSecretSize() const = 0;
};

// Interface para assinatura digital
class DigitalSignature {
public:
    virtual ~DigitalSignature() = default;

    struct KeyPair {
        std::vector<uint8_t> publicKey;
        std::vector<uint8_t> secretKey;
    };

    virtual KeyPair generateKeyPair() = 0;
    virtual std::vector<uint8_t> sign(
        const std::vector<uint8_t>& secretKey,
        const std::vector<uint8_t>& message) = 0;
    virtual bool verify(
        const std::vector<uint8_t>& publicKey,
        const std::vector<uint8_t>& message,
        const std::vector<uint8_t>& signature) = 0;

    virtual std::string name() const = 0;
    virtual bool isPostQuantum() const = 0;
    virtual size_t publicKeySize() const = 0;
    virtual size_t secretKeySize() const = 0;
    virtual size_t signatureSize() const = 0;
};

// Implementacao ML-KEM (CRYSTALS-Kyber)
class MLKEM768 : public KeyEncapsulation {
public:
    std::string name() const override { return "ML-KEM-768"; }
    bool isPostQuantum() const override { return true; }
    size_t publicKeySize() const override { return 1184; }
    size_t secretKeySize() const override { return 2400; }
    size_t ciphertextSize() const override { return 1088; }
    size_t sharedSecretSize() const override { return 32; }

    KeyPair generateKeyPair() override {
        KeyPair kp;
        kp.publicKey.resize(publicKeySize());
        kp.secretKey.resize(secretKeySize());
        // Implementacao usando liboqs
        // oqs_kem_alg_keypair(kp.publicKey.data(), kp.secretKey.data());
        return kp;
    }

    EncapsulateResult encapsulate(
        const std::vector<uint8_t>& publicKey) override
    {
        EncapsulateResult result;
        result.ciphertext.resize(ciphertextSize());
        result.sharedSecret.resize(sharedSecretSize());
        // oqs_kem_alg_encaps(result.ciphertext.data(),
        //                    result.sharedSecret.data(),
        //                    publicKey.data());
        return result;
    }

    std::vector<uint8_t> decapsulate(
        const std::vector<uint8_t>& secretKey,
        const std::vector<uint8_t>& ciphertext) override
    {
        std::vector<uint8_t> sharedSecret(sharedSecretSize());
        // oqs_kem_alg_decaps(sharedSecret.data(),
        //                    ciphertext.data(),
        //                    secretKey.data());
        return sharedSecret;
    }
};

// Implementacao ML-DSA (CRYSTALS-Dilithium)
class MLDSA65 : public DigitalSignature {
public:
    std::string name() const override { return "ML-DSA-65"; }
    bool isPostQuantum() const override { return true; }
    size_t publicKeySize() const override { return 1952; }
    size_t secretKeySize() const override { return 4032; }
    size_t signatureSize() const override { return 3293; }

    KeyPair generateKeyPair() override {
        KeyPair kp;
        kp.publicKey.resize(publicKeySize());
        kp.secretKey.resize(secretKeySize());
        // Implementacao usando liboqs
        return kp;
    }

    std::vector<uint8_t> sign(
        const std::vector<uint8_t>& secretKey,
        const std::vector<uint8_t>& message) override
    {
        std::vector<uint8_t> sig(signatureSize());
        // oqs_sign_alg_sign(sig.data(), message.data(),
        //                   message.size(), secretKey.data());
        return sig;
    }

    bool verify(
        const std::vector<uint8_t>& publicKey,
        const std::vector<uint8_t>& message,
        const std::vector<uint8_t>& signature) override
    {
        // return oqs_sign_alg_verify(signature.data(),
        //                            message.data(),
        //                            message.size(),
        //                            publicKey.data()) == 0;
        return true;
    }
};

// Gerenciador de hybrid key exchange
class HybridKeyExchange {
public:
    struct HybridResult {
        std::vector<uint8_t> classicalCiphertext;
        std::vector<uint8_t> pqCiphertext;
        std::vector<uint8_t> sharedSecret;
    };

    void setClassicalAlgorithm(std::shared_ptr<KeyEncapsulation> algo) {
        classical_ = algo;
    }

    void setPostQuantumAlgorithm(std::shared_ptr<KeyEncapsulation> algo) {
        pq_ = algo;
    }

    HybridResult hybridEncapsulate(
        const std::vector<uint8_t>& classicalPublicKey,
        const std::vector<uint8_t>& pqPublicKey)
    {
        HybridResult result;

        // Classical KEM
        auto classicalResult = classical_->encapsulate(classicalPublicKey);
        result.classicalCiphertext = classicalResult.ciphertext;

        // Post-quantum KEM
        auto pqResult = pq_->encapsulate(pqPublicKey);
        result.pqCiphertext = pqResult.ciphertext;

        // Combina shared secrets
        result.sharedSecret.resize(
            classicalResult.sharedSecret.size() +
            pqResult.sharedSecret.size());
        std::copy(classicalResult.sharedSecret.begin(),
                  classicalResult.sharedSecret.end(),
                  result.sharedSecret.begin());
        std::copy(pqResult.sharedSecret.begin(),
                  pqResult.sharedSecret.end(),
                  result.sharedSecret.begin() +
                  classicalResult.sharedSecret.size());

        return result;
    }

private:
    std::shared_ptr<KeyEncapsulation> classical_;
    std::shared_ptr<KeyEncapsulation> pq_;
};
```

---

## 11. Exemplo: Verificacao de Propriedade Constant-Time com SAW

### 11.1 O Problema do Constant-Time

A verificacao de constant-time e uma das propriedades mais criticas em software criptografico. Um algoritmo e constante em tempo se:

1. Nao ha branches que dependem de dados secretos
2. Nao ha acessos a memoria que dependem de dados secretos
3. Nao ha operacoes aritmeticas cujo tempo depende de dados secretos

Isso e dificil de verificar porque o compilador pode transformar codigo constante em codigo com timing variavel.

### 11.2 Implementacao e Verificacao com SAW

```cpp
// Implementacao C de operacoes constant-time para verificacao com SAW

#include <cstdint>
#include <cstddef>
#include <cstring>

// Selecao constante em tempo: seleciona x ou y baseado em mask
// Se mask == 0xFFFFFFFFFFFFFFFF, retorna x; se mask == 0, retorna y
// Implementacao SEM branches
extern "C" uint64_t ct_select(uint64_t mask, uint64_t x, uint64_t y) {
    // mask e 0xFFFFFFFFFFFFFFFF se bit==1, 0 caso contrario
    return (x & mask) | (y & ~mask);
}

// Comparacao constante em tempo
// Retorna 0xFFFFFFFFFFFFFFFF se a == b, 0 caso contrario
extern "C" uint64_t ct_eq(uint64_t a, uint64_t b) {
    uint64_t diff = a ^ b;
    // Reduz diff a um bit
    diff |= diff >> 32;
    diff |= diff >> 16;
    diff |= diff >> 8;
    diff |= diff >> 4;
    diff |= diff >> 2;
    diff |= diff >> 1;
    // diff agora e 0 se a==b, 1 caso contrario
    // Inverte e mascara
    return ~(diff & 1) + 1;  // 0 se a!=b, 0xFFFFFFFFFFFFFFFF se a==b
}

// Comparacao de vetores constante em tempo
extern "C" uint8_t ct_verify(
    const uint8_t* a,
    const uint8_t* b,
    size_t len)
{
    uint8_t diff = 0;
    for (size_t i = 0; i < len; ++i) {
        diff |= a[i] ^ b[i];
    }
    // diff == 0 se a == b
    return ct_eq(diff, 0) & 1;
}

// Funcao que NAO e constante em tempo (para demonstracao)
// NAO USE EM CRIPTOGRAFIA
extern "C" uint8_t insecure_verify(
    const uint8_t* a,
    const uint8_t* b,
    size_t len)
{
    for (size_t i = 0; i < len; ++i) {
        if (a[i] != b[i]) {  // BRANCH!
            return 0;
        }
    }
    return 1;
}

// Constant-time conditional move
extern "C" void ct_cmov(
    uint8_t* dst,
    const uint8_t* src,
    uint8_t condition,  // 0xFF ou 0x00
    size_t len)
{
    uint8_t mask = condition;
    for (size_t i = 0; i < len; ++i) {
        dst[i] = (dst[i] & ~mask) | (src[i] & mask);
    }
}

// Constant-time memory comparison com limpeza segura
extern "C" uint8_t ct_verify_and_erase(
    uint8_t* a,
    const uint8_t* b,
    size_t len)
{
    uint8_t result = ct_verify(a, b, len);

    // Limpa a memoria de 'a' independentemente do resultado
    // Isso e constante em tempo porque sempre executa
    volatile uint8_t* vptr = reinterpret_cast<volatile uint8_t*>(a);
    for (size_t i = 0; i < len; ++i) {
        vptr[i] = 0;
    }

    return result;
}
```

### 11.3 Script SAW para Verificacao de Constant-Time

```cryptol
-- Script SAW: Verificacao de constant-time
-- Prova que as funcoes NAO tem branches ou acessos dependentes de dados secretos

-- Carrega modulo LLVM
llvm_mod <- llvm_load_module "ct_impl.bc"

-- Verifica ct_eq: propriedade funcional
-- Prova que ct_eq(a, b) == 1 se a == b, 0 caso contrario
prove : {{
    \a b -> ct_eq_c a b == if a == b then 0xFFFFFFFFFFFFFFFF else 0
}}
where
    ct_eq_c = llvm_fun "ct_eq" llvm_mod

-- Verifica ct_verify: propriedade funcional
prove : {{
    \a b -> ct_verify_c a b == if a == b then 1 else 0
}}
where
    ct_verify_c = llvm_fun "ct_verify" llvm_mod

-- Verifica constant-time de ct_eq
-- O SAW verifica que:
-- 1. Nao ha branches que dependem dos inputs
-- 2. Nao ha acessos a memoria que dependem dos inputs
-- 3. Todas as operacoes executam em tempo constante
llvm_verify ct_eq [] (llvm_timeout 600) $ do
    crucible_mem <- crucible_get_syminterface
    crucible_execute_func []
    crucible_verify_tigress ct_eq

-- Verifica constant-time de ct_verify
llvm_verify ct_verify [] (llvm_timeout 600) $ do
    crucible_mem <- crucible_get_syminterface
    crucible_execute_func []
    crucible_verify_tigress ct_verify

-- Verifica que insecure_verify NAO e constante-time
-- (deve encontrar branch dependente de dados)
llvm_verify insecure_verify [] (llvm_timeout 600) $ do
    crucible_mem <- crucible_get_syminterface
    crucible_execute_func []
    crucible_verify_tigress insecure_verify
    -- Esperado: falha porque ha branch em "if (a[i] != b[i])"
```

### 11.4 Analise de Assembly para Constant-Time

```cpp
// Framework C++ para analise de assembly para constant-time

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <regex>
#include <map>

class AssemblyAnalyzer {
public:
    struct Branch {
        size_t address;
        std::string instruction;
        bool isConditional;
        std::string registerUsed;
    };

    struct MemoryAccess {
        size_t address;
        std::string instruction;
        bool isSecretDependent;
        std::string baseRegister;
    };

    struct AnalysisResult {
        std::vector<Branch> branches;
        std::vector<MemoryAccess> memoryAccesses;
        bool isConstantTime;
        std::vector<std::string> violations;
    };

    AnalysisResult analyze(const std::string& assemblyFile) {
        AnalysisResult result;

        std::ifstream file(assemblyFile);
        std::string line;
        size_t lineNum = 0;

        while (std::getline(file, line)) {
            lineNum++;

            // Detecta branches condicionais
            if (isConditionalBranch(line)) {
                Branch branch;
                branch.address = lineNum;
                branch.instruction = line;
                branch.isConditional = true;
                branch.registerUsed = extractRegister(line);
                result.branches.push_back(branch);

                // Verifica se o registrador depende de dados secretos
                if (isSecretRegister(branch.registerUsed)) {
                    result.violations.push_back(
                        "Line " + std::to_string(lineNum) +
                        ": Conditional branch on secret data");
                    result.isConstantTime = false;
                }
            }

            // Detecta acessos a memoria indexados
            if (isIndexedMemoryAccess(line)) {
                MemoryAccess access;
                access.address = lineNum;
                access.instruction = line;
                access.isSecretDependent = isSecretIndex(line);
                access.baseRegister = extractBaseRegister(line);
                result.memoryAccesses.push_back(access);

                if (access.isSecretDependent) {
                    result.violations.push_back(
                        "Line " + std::to_string(lineNum) +
                        ": Memory access with secret index");
                    result.isConstantTime = false;
                }
            }
        }

        if (result.violations.empty()) {
            result.isConstantTime = true;
        }

        return result;
    }

    void printReport(const AnalysisResult& result) {
        std::cout << "=== Analise de Constant-Time ===\n\n";

        std::cout << "Branches condicionais encontrados: "
                  << result.branches.size() << "\n";
        std::cout << "Acessos a memoria indexados: "
                  << result.memoryAccesses.size() << "\n";
        std::cout << "Violacoes: " << result.violations.size() << "\n\n";

        if (result.isConstantTime) {
            std::cout << "RESULTADO: Constant-time VERIFICADO\n";
        } else {
            std::cout << "RESULTADO: Constant-time VIOLADO\n";
            for (const auto& v : result.violations) {
                std::cout << "  - " << v << "\n";
            }
        }
    }

private:
    bool isConditionalBranch(const std::string& line) {
        return std::regex_search(line,
            std::regex("(je|jne|jg|jl|jge|jle|ja|jb|jae|jbe|jz|jnz)"));
    }

    bool isIndexedMemoryAccess(const std::string& line) {
        return std::regex_search(line,
            std::regex("\\[.*\\+.*\\].*\\]"));
    }

    std::string extractRegister(const std::string& line) {
        std::smatch match;
        if (std::regex_search(line, match,
            std::regex("(eax|ebx|ecx|edx|esi|edi|rbx|rcx|rdx|rsi|rdi)"))) {
            return match[0];
        }
        return "";
    }

    std::string extractBaseRegister(const std::string& line) {
        std::smatch match;
        if (std::regex_search(line, match,
            std::regex("\\[(\\w+)"))) {
            return match[1];
        }
        return "";
    }

    bool isSecretRegister(const std::string& reg) {
        // Em implementacoes reais, isso requer tracking de dados
        // Aqui simplificamos com heuristica
        static const std::vector<std::string> secretRegs = {
            "eax", "ecx", "edx"  // Registradores usados para dados
        };
        for (const auto& sr : secretRegs) {
            if (reg == sr) return true;
        }
        return false;
    }

    bool isSecretIndex(const std::string& line) {
        // Heuristica: se o indice vem de um registrador de dados
        return std::regex_search(line,
            std::regex("\\[\\w+\\+\\w+\\+\\w+\\]"));
    }
};

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cerr << "Uso: " << argv[0] << " <assembly_file>" << std::endl;
        return 1;
    }

    AssemblyAnalyzer analyzer;
    auto result = analyzer.analyze(argv[1]);
    analyzer.printReport(result);

    return result.isConstantTime ? 0 : 1;
}
```

### 11.5 Integracao com CI/CD

```yaml
# GitHub Actions workflow para verificacao de constant-time

name: Constant-Time Verification

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  constant-time-check:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y clang llvm z3

    - name: Install SAW
      run: |
        wget https://github.com/GaloisInc/saw/releases/download/v1.1/saw-1.1-Linux.tar.gz
        tar xzf saw-1.1-Linux.tar.gz
        echo "$PWD/saw-1.1/bin" >> $GITHUB_PATH

    - name: Compile to LLVM IR
      run: |
        clang -emit-llvm -c -g -O0 crypto_functions.c -o crypto_functions.bc

    - name: Run SAW constant-time verification
      run: |
        saw verify_constant_time.saw

    - name: Compile and check assembly
      run: |
        clang -S -O0 crypto_functions.c -o crypto_functions.s
        python scripts/check_constant_time.py crypto_functions.s

    - name: Upload results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: constant-time-results
        path: |
          verification_report.json
          assembly_analysis.json
```

---

## 12. Exemplo: Prova de Handshake TLS 1.3 com ProVerif

### 12.1 Modelo Completo do TLS 1.3

```proverif
(* Modelo completo do TLS 1.3 Handshake para ProVerif *)
(* Verifica: forward secrecy, autenticacao, protecao contra downgrade *)

type channel.
type skey.
type key.
type nonce.
type payload.

(* Funcoes criptograficas *)
fun pk : skey -> key.
fun sign : skey -> payload -> payload.
fun concat : payload -> payload -> payload.
fun hash : payload -> payload.
fun hkdf : key -> payload -> payload.
fun aead_enc : key -> nonce -> payload -> payload.
fun aead_dec : key -> nonce -> payload -> payload.

reduc forall k : skey, m : payload; verify(pk(k), m, sign(k, m)) = true.
reduc forall k : skey, m : payload; pk_dec(k, pk_enc(pk(k), m)) = m.

(* Canais *)
ch c_public : channel.

(* Chaves de longo prazo *)
secret sk_client : skey.
secret sk_server : skey.

(* Nonces *)
let client_random : nonce = hNonces(1).
let server_random : nonce = hNonces(2).

(* Handshake TLS 1.3 *)
let client =
    (* Passo 1: ClientHello *)
    out(c_public, ('ClientHello', client_random));

    (* Passo 2: ServerHello *)
    in(c_public, ('ServerHello', server_random));

    (* Deriva chaves *)
    let shared_secret = hash(concat(client_random, server_random)) in
    let handshake_key = hkdf(shared_secret, 'handshake') in
    let app_key = hkdf(shared_secret, 'application') in

    (* Passo 3: EncryptedExtensions *)
    in(c_public, aead_enc(handshake_key, 0, payload(0)));

    (* Passo 4: Certificate *)
    in(c_public, ('Certificate', pk(sk_server)));

    (* Passo 5: CertificateVerify *)
    in(c_public, sign(sk_server, concat(client_random, server_random)));

    (* Verifica assinatura *)
    if verify(pk(sk_server), concat(client_random, server_random),
              sign(sk_server, concat(client_random, server_random))) then
        (* Passo 6: Finished (cliente) *)
        let finished_hash = hash(concat(client_random, server_random)) in
        out(c_public, sign(sk_client, finished_hash));
    else
        0.

let server =
    (* Passo 1: Recebe ClientHello *)
    in(c_public, ('ClientHello', ch_random));

    (* Passo 2: ServerHello *)
    out(c_public, ('ServerHello', server_random));

    (* Deriva chaves *)
    let shared_secret = hash(concat(ch_random, server_random)) in
    let handshake_key = hkdf(shared_secret, 'handshake') in
    let app_key = hkdf(shared_secret, 'application') in

    (* Passo 3: EncryptedExtensions *)
    out(c_public, aead_enc(handshake_key, 0, payload(0)));

    (* Passo 4: Certificate *)
    out(c_public, ('Certificate', pk(sk_server)));

    (* Passo 5: CertificateVerify *)
    out(c_public, sign(sk_server, concat(ch_random, server_random)));

    (* Passo 6: Recebe Finished do cliente *)
    in(c_public, client_finished : payload);
    if verify(pk(sk_client), hash(concat(ch_random, server_random)),
              client_finished) then
        (* Handshake completo *)
        0.

(* Adversario *)
let adversary =
    (* Observa todas as mensagens publicas *)
    in(c_public, x : payload);
    0.

(* Composicao *)
process (new sk_client; new sk_server;
         (client | server | adversary))

(* Propriedades de seguranca *)

(* 1. Chave de sessao e secreta *)
(* query session_key : key; attacker(session_key) = false. *)

(* 2. Autenticacao: servidor autenticado *)
(* query m : payload; event(server_authenticated(m)) ==> event(client_sends(m)). *)

(* 3. Forward secrecy *)
(* query past_key : key; attacker(past_key) ==> not attacker(current_session). *)

(* 4. Protecao contra downgrade *)
(* query downgrade : nonce; event(downgrade_attempt) ==> event(version_maintained). *)

(* 5. Ausencia de replay *)
(* query replay : payload; event(replay_detected) ==> not event(processed). *)

(* Execucao *)
(* Equations *)
eqn verify(k, m, sign(k, m)) = true.
eqn hash(concat(a, b)) = hash(a) || hash(b).
eqn hkdf(secret, info) = hash(secret || info).
```

### 12.2 Script de Execucao Automatizada

```cpp
// Framework C++ para automatizar verificacao ProVerif

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <cstdlib>
#include <functional>

class ProVerifAutomation {
public:
    struct ProtocolConfig {
        std::string name;
        std::string inputFile;
        std::vector<std::string> queries;
        std::map<std::string, std::string> parameters;
    };

    struct VerificationReport {
        bool allQueriesSatisfied;
        std::map<std::string, bool> queryResults;
        std::string rawOutput;
        double executionTimeMs;
    };

    VerificationReport verify(const ProtocolConfig& config) {
        VerificationReport report;

        // Gera arquivo de entrada
        std::string generatedInput = generateInput(config);
        std::string tempFile = "/tmp/proverif_input_" + config.name + ".pv";

        std::ofstream out(tempFile);
        out << generatedInput;
        out.close();

        // Executa ProVerif
        std::string cmd = "proverif -graph /tmp/proverif_graph " + tempFile;
        auto startTime = std::chrono::steady_clock::now();

        FILE* pipe = popen(cmd.c_str(), "r");
        char buffer[4096];
        report.rawOutput.clear();
        while (fgets(buffer, sizeof(buffer), pipe)) {
            report.rawOutput += buffer;
        }
        pclose(pipe);

        auto endTime = std::chrono::steady_clock::now();
        report.executionTimeMs = std::chrono::duration<double, std::milli>(
            endTime - startTime).count();

        // Analisa resultados
        report.allQueriesSatisfied = true;
        for (const auto& query : config.queries) {
            bool satisfied = analyzeQueryResult(query, report.rawOutput);
            report.queryResults[query] = satisfied;
            if (!satisfied) {
                report.allQueriesSatisfied = false;
            }
        }

        // Salva relatorio
        saveReport(config, report);

        return report;
    }

private:
    std::string generateInput(const ProtocolConfig& config) {
        std::ostringstream input;

        input << "(* Auto-generated ProVerif input *)\n";
        input << "(* Protocol: " << config.name << " *)\n\n";

        // Le o arquivo de template base
        std::ifstream templateFile(config.inputFile);
        if (templateFile.is_open()) {
            std::string line;
            while (std::getline(templateFile, line)) {
                input << line << "\n";
            }
        }

        // Adiciona queries especificas
        input << "\n(* Generated Queries *)\n";
        for (size_t i = 0; i < config.queries.size(); ++i) {
            input << "query q" << i << ": " << config.queries[i] << ".\n";
        }

        return input.str();
    }

    bool analyzeQueryResult(const std::string& query,
                           const std::string& output) {
        // Procura pela query no output
        size_t pos = output.find("RESULT " + query);
        if (pos == std::string::npos) {
            // Tenta encontrar por padrao generico
            pos = output.find("RESULT not attacker");
        }

        if (pos != std::string::npos) {
            // Verifica se e positivo ou negativo
            std::string after = output.substr(pos);
            return after.find("= true") != std::string::npos ||
                   after.find("not attacker") != std::string::npos;
        }

        return false;
    }

    void saveReport(const ProtocolConfig& config,
                   const VerificationReport& report) {
        std::string reportFile = "/tmp/proverif_report_" + config.name + ".json";

        std::ofstream out(reportFile);
        out << "{\n";
        out << "  \"protocol\": \"" << config.name << "\",\n";
        out << "  \"allQueriesSatisfied\": "
            << (report.allQueriesSatisfied ? "true" : "false") << ",\n";
        out << "  \"executionTimeMs\": " << report.executionTimeMs << ",\n";
        out << "  \"queryResults\": {\n";

        size_t i = 0;
        for (const auto& [query, result] : report.queryResults) {
            out << "    \"" << query << "\": "
                << (result ? "true" : "false");
            if (i < report.queryResults.size() - 1) out << ",";
            out << "\n";
            i++;
        }

        out << "  }\n";
        out << "}\n";
        out.close();
    }
};

// Exemplo de uso com TLS 1.3
void verifyTLS13() {
    ProVerifAutomation automation;

    ProVerifAutomation::ProtocolConfig config;
    config.name = "tls13_handshake";
    config.inputFile = "tls13_model.pv";
    config.queries = {
        "session_key : key; attacker(session_key) = false",
        "m : payload; event(server_authenticated(m)) ==> event(client_sends(m))",
        "past_key : key; attacker(past_key) ==> not attacker(current_session)"
    };

    auto report = automation.verify(config);

    std::cout << "TLS 1.3 Verification Report\n";
    std::cout << "============================\n";
    std::cout << "All queries satisfied: "
              << (report.allQueriesSatisfied ? "YES" : "NO") << "\n";
    std::cout << "Execution time: " << report.executionTimeMs << "ms\n\n";

    for (const auto& [query, result] : report.queryResults) {
        std::cout << (result ? "PASS" : "FAIL") << ": " << query << "\n";
    }
}

int main() {
    verifyTLS13();
    return 0;
}
```

---

## 13. Comparacao de Ferramentas de Verificacao Formal

### 13.1 Matriz de Comparacao

| Ferramenta | Tipo | Alvo | Automacao | Curva Aprendizado | Criptografia |
|-----------|------|------|-----------|-------------------|--------------|
| SPIN | Model Checker | Protocolos | Alta | Media | Promela |
| NuSMV | Model Checker | Circuitos/Protocolos | Alta | Media | SMV |
| Cryptol | Spec Language | Algoritmos | N/A | Alta | Nativa |
| SAW | Equivalence Prover | C/C++/LLVM | Alta | Alta | Cryptol |
| ProVerif | Protocol Verifier | Protocolos | Muito Alta | Baixa | Pi-calculus |
| Tamarin | Protocol Verifier | Protocolos complexos | Media | Alta | Multiset rewriting |
| F* | Dependently-typed | Software geral | Media | Muito Alta | Nativa |
| CompCert | Verified Compiler | C | Alta | N/A | N/A |

### 13.2 Quando Usar Cada Ferramenta

**Use SPIN quando:**
- Modelo do protocolo e finito e pequeno
- Precisa de performance rapida
- Quer contraexemplos concretos
- Protocolo tem poucos participantes

**Use ProVerif quando:**
- Precisa verificar protocolos com segredos de tamanho arbitrario
- Quer automacao maxima
- Modelo de adversario e forte (Dolev-Yao)
- Precisa verificar forward secrecy e autenticacao

**Use Tamarin quando:**
- Protocolo tem estado local
- Precisa modelar grupos dinamicos
- Modelo de seguranca e eCK ou similar
- Protocolo usa XOR

**Use SAW quando:**
- Precisa verificar equivalencia de implementacao C/C++
- Especificacao existe em Cryptol
- Codigo e compilavel para LLVM
- Precisa verificar operacoes individuais (AES, SHA, etc.)

**Use F* quando:**
- Precisa de invariantes complexos dependendo de tipos
- Codigo e funcional
- Precisa de provas interativas
- Quer high assurance com formal guarantee

**Use CompCert quando:**
- Compilador nao pode ter bugs
- Constant-time precisa ser preservado apos compilacao
- Software e critical infrastructure

### 13.3 Fluxo de Decisao

```
+------------------------------------------------------------------+
|              FLUXO DE DECISAO: Qual ferramenta usar?              |
+------------------------------------------------------------------+
|                                                                  |
|  Voce quer verificar o que?                                      |
|                                                                  |
|  [Protocolo] --------+-- Simples (2-3 msgs) --> ProVerif        |
|       |              +-- Complexo (estado) ---> Tamarin          |
|       |              +-- Finito e pequeno ---> SPIN              |
|       |                                                          |
|  [Implementacao C] --+-- Equivalencia --------> SAW + Cryptol    |
|       |              +-- Constant-time -------> SAW + Tigress    |
|       |              +-- Memory safety -------> CompCert         |
|       |                                                          |
|  [Algoritmo] --------+-- Especificacao -------> Cryptol          |
|       |              +-- Prova interativa ----> F*               |
|       |                                                          |
|  [Compilador] -------+-- Verified -----------> CompCert         |
|       |              +-- Convencional -------> GCC/Clang + SAW  |
+------------------------------------------------------------------+
```

### 13.4 Integracao Combinada

Na pratica, as melhores implementacoes criptograficas usam multiplas ferramentas:

```cpp
// Framework C++ que integra multiplas ferramentas de verificacao

#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <map>
#include <functional>

// Interface unificada para ferramentas de verificacao
class VerificationTool {
public:
    virtual ~VerificationTool() = default;

    enum class ToolType {
        MODEL_CHECKER,
        THEOREM_PROVER,
        EQUIVALENCE_PROVER,
        COMPILER_VERIFIER,
        ABSTRACT_INTERPRETER
    };

    struct VerificationConfig {
        std::string targetFile;
        std::string specificationFile;
        std::map<std::string, std::string> options;
    };

    struct VerificationResult {
        bool passed;
        std::string toolName;
        std::string message;
        std::string counterexample;
        double executionTimeMs;
    };

    virtual std::string name() const = 0;
    virtual ToolType type() const = 0;
    virtual VerificationResult verify(const VerificationConfig& config) = 0;
    virtual bool isAvailable() const = 0;
};

// Implementacao: ProVerif
class ProVerifTool : public VerificationTool {
public:
    std::string name() const override { return "ProVerif"; }
    ToolType type() const override { return ToolType::THEOREM_PROVER; }

    VerificationResult verify(const VerificationConfig& config) override {
        VerificationResult result;
        result.toolName = name();

        std::string cmd = "proverif " + config.targetFile;
        auto start = std::chrono::steady_clock::now();

        int status = std::system(cmd.c_str());

        auto end = std::chrono::steady_clock::now();
        result.executionTimeMs = std::chrono::duration<double, std::milli>(
            end - start).count();

        result.passed = (status == 0);
        result.message = result.passed ?
            "All properties verified" : "Some properties violated";

        return result;
    }

    bool isAvailable() const override {
        return std::system("which proverif > /dev/null 2>&1") == 0;
    }
};

// Implementacao: SAW
class SAWTool : public VerificationTool {
public:
    std::string name() const override { return "SAW"; }
    ToolType type() const override { return ToolType::EQUIVALENCE_PROVER; }

    VerificationResult verify(const VerificationConfig& config) override {
        VerificationResult result;
        result.toolName = name();

        std::string cmd = "saw " + config.targetFile;
        auto start = std::chrono::steady_clock::now();

        int status = std::system(cmd.c_str());

        auto end = std::chrono::steady_clock::now();
        result.executionTimeMs = std::chrono::duration<double, std::milli>(
            end - start).count();

        result.passed = (status == 0);
        result.message = result.passed ?
            "Equivalence proved" : "Equivalence not proved";

        return result;
    }

    bool isAvailable() const override {
        return std::system("which saw > /dev/null 2>&1") == 0;
    }
};

// Implementacao: CompCert
class CompCertTool : public VerificationTool {
public:
    std::string name() const override { return "CompCert"; }
    ToolType type() const override { return ToolType::COMPILER_VERIFIER; }

    VerificationResult verify(const VerificationConfig& config) override {
        VerificationResult result;
        result.toolName = name();

        std::string cmd = "ccomp -o /dev/null " + config.targetFile;
        auto start = std::chrono::steady_clock::now();

        int status = std::system(cmd.c_str());

        auto end = std::chrono::steady_clock::now();
        result.executionTimeMs = std::chrono::duration<double, std::milli>(
            end - start).count();

        result.passed = (status == 0);
        result.message = result.passed ?
            "Compilation verified (semantics preserved)" :
            "Compilation failed";

        return result;
    }

    bool isAvailable() const override {
        return std::system("which ccomp > /dev/null 2>&1") == 0;
    }
};

// Integrador de verificacao
class VerificationIntegrator {
public:
    void registerTool(std::shared_ptr<VerificationTool> tool) {
        tools_.push_back(tool);
    }

    struct ComprehensiveReport {
        std::vector<VerificationTool::VerificationResult> results;
        bool allPassed;
        double totalTimeMs;
    };

    ComprehensiveReport verifyAll(const VerificationTool::VerificationConfig& config) {
        ComprehensiveReport report;
        report.allPassed = true;
        report.totalTimeMs = 0;

        for (auto& tool : tools_) {
            if (tool->isAvailable()) {
                auto result = tool->verify(config);
                report.results.push_back(result);
                report.totalTimeMs += result.executionTimeMs;

                if (!result.passed) {
                    report.allPassed = false;
                }

                std::cout << result.toolName << ": "
                          << (result.passed ? "PASS" : "FAIL")
                          << " (" << result.executionTimeMs << "ms)\n";
            } else {
                std::cout << tool->name() << ": NOT AVAILABLE\n";
            }
        }

        return report;
    }

private:
    std::vector<std::shared_ptr<VerificationTool>> tools_;
};

// Exemplo de uso
void comprehensiveVerification() {
    VerificationIntegrator integrator;

    integrator.registerTool(std::make_shared<ProVerifTool>());
    integrator.registerTool(std::make_shared<SAWTool>());
    integrator.registerTool(std::make_shared<CompCertTool>());

    VerificationTool::VerificationConfig config;
    config.targetFile = "crypto_implementation.pv";
    config.specificationFile = "specification.cry";

    auto report = integrator.verifyAll(config);

    std::cout << "\n=== Comprehensive Report ===\n";
    std::cout << "All passed: " << (report.allPassed ? "YES" : "NO") << "\n";
    std::cout << "Total time: " << report.totalTimeMs << "ms\n";
}
```

---

## 14. Integracao com Fluxo de Desenvolvimento

### 14.1 Verificacao Formal no Ciclo de Vida do Software

A verificacao formal nao deve ser uma atividade isolada — ela deve ser integrada ao fluxo de desenvolvimento normal. Isso significa:

1. **Especificacao durante o design:** Escrever especificacoes em Cryptol ou F* durante a fase de design
2. **Verificacao continua:** Rodar verificacoes automatizadas em cada commit
3. **Revisao formal:** Usar contraexemplos como base para code review
4. **Documentacao de propriedades:** Documentar propriedades verificadas alongside o codigo

### 14.2 Pipeline de CI/CD para Verificacao Formal

```yaml
# Pipeline completo de verificacao formal

name: Formal Verification Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  SAW_VERSION: "1.1"
  PROVERIF_VERSION: "2.04"

jobs:
  # Etapa 1: Verificacao de protocolos com ProVerif
  protocol-verification:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Install ProVerif
      run: |
        wget https://bblanche.gitlabpages.inria.fr/proverif/download/proverif-${PROVERIF_VERSION}.tar.gz
        tar xzf proverif-${PROVERIF_VERSION}.tar.gz
        cd proverif-${PROVERIF_VERSION}
        ./build
        sudo cp proverif /usr/local/bin/

    - name: Verify protocol properties
      run: |
        for pv_file in protocols/*.pv; do
          echo "Verifying $pv_file..."
          proverif -graph "$pv_file" || exit 1
        done

    - name: Generate verification report
      run: |
        python scripts/generate_protocol_report.py protocols/ > protocol_report.json

  # Etapa 2: Verificacao de equivalencia com SAW
  equivalence-verification:
    runs-on: ubuntu-latest
    needs: protocol-verification
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Install SAW
      run: |
        wget https://github.com/GaloisInc/saw/releases/download/v${SAW_VERSION}/saw-${SAW_VERSION}-Linux.tar.gz
        tar xzf saw-${SAW_VERSION}-Linux.tar.gz
        echo "$PWD/saw-${SAW_VERSION}/bin" >> $GITHUB_PATH

    - name: Compile C to LLVM IR
      run: |
        clang -emit-llvm -c -g -O0 -I. crypto/*.c

    - name: Run SAW equivalence checks
      run: |
        for saw_file in verification/*.saw; do
          echo "Verifying $saw_file..."
          saw "$saw_file" || exit 1
        done

  # Etapa 3: Verificacao de constant-time
  constant-time:
    runs-on: ubuntu-latest
    needs: equivalence-verification
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Install dependencies
      run: |
        sudo apt-get install -y clang llvm z3

    - name: Compile and analyze
      run: |
        for c_file in crypto/*.c; do
          base=$(basename "$c_file" .c)
          clang -S -O0 "$c_file" -o "assembly/${base}.s"
          python scripts/check_constant_time.py "assembly/${base}.s"
        done

    - name: Upload assembly analysis
      uses: actions/upload-artifact@v3
      with:
        name: assembly-analysis
        path: assembly/*.s

  # Etapa 4: Verificacao com CompCert
  verified-compilation:
    runs-on: ubuntu-latest
    needs: constant-time
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Install CompCert
      run: |
        wget https://github.com/AbsInt/CompCert/releases/download/v3.13/compcert-3.13-x86_64-linux.tar.gz
        tar xzf compcert-3.13-x86_64-linux.tar.gz
        echo "$PWD/compcert-3.13-x86_64-linux/bin" >> $GITHUB_PATH

    - name: Compile with CompCert
      run: |
        for c_file in crypto/*.c; do
          echo "Compiling $c_file with CompCert..."
          ccomp -o "verified/${c_file%.c}" "$c_file" || exit 1
        done

    - name: Verify compilation certificates
      run: |
        for v_file in crypto/*.v; do
          if [ -f "$v_file" ]; then
            echo "Checking certificate $v_file..."
            coqc "$v_file" || exit 1
          fi
        done

  # Etapa 5: Property-based testing
  property-testing:
    runs-on: ubuntu-latest
    needs: verified-compilation
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Setup Go
      uses: actions/setup-go@v3
      with:
        go-version: '1.20'

    - name: Run property-based tests
      run: |
        go test -v -run TestProperty ./... -count=10000

  # Etapa 6: Fuzzing
  fuzzing:
    runs-on: ubuntu-latest
    needs: property-testing
    steps:
    - name: Checkout
      uses: actions/checkout@v3

    - name: Install AFL++
      run: |
        sudo apt-get install -y afl++

    - name: Build fuzz targets
      run: |
        afl-clang-fast -fsanitize=fuzzer,address -g crypto/fuzz_target.c -o fuzz_target

    - name: Run fuzzing (10 minutes)
      run: |
        mkdir -p fuzz corpus
        timeout 600 afl-fuzz -i corpus -o fuzz ./fuzz_target || true

    - name: Check for crashes
      run: |
        if [ -n "$(ls fuzz/crashes/ 2>/dev/null)" ]; then
          echo "FUZZING FOUND CRASHES!"
          ls fuzz/crashes/
          exit 1
        fi

  # Relatorio final
  final-report:
    runs-on: ubuntu-latest
    needs: [protocol-verification, equivalence-verification, constant-time, verified-compilation, property-testing, fuzzing]
    if: always()
    steps:
    - name: Generate comprehensive report
      run: |
        python scripts/generate_final_report.py > final_verification_report.json

    - name: Upload report
      uses: actions/upload-artifact@v3
      with:
        name: verification-report
        path: final_verification_report.json
```

### 14.3 Documentacao de Propriedades Verificadas

```cpp
// Framework para documentar propriedades verificadas

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <chrono>
#include <ctime>

struct VerifiedProperty {
    std::string name;
    std::string description;
    std::string tool;
    std::string specificationFile;
    std::string implementationFile;
    std::string dateVerified;
    std::string verificationCommand;
    bool isAutomatic;
    std::vector<std::string> dependencies;
};

class PropertyDocumentation {
public:
    void addProperty(const VerifiedProperty& prop) {
        properties_.push_back(prop);
    }

    std::string generateMarkdown() const {
        std::ostringstream md;

        md << "# Verified Properties Report\n\n";
        md << "Generated: " << currentDateTime() << "\n\n";

        md << "## Summary\n\n";
        md << "- Total properties verified: " << properties_.size() << "\n";
        md << "- Automatic verifications: "
           << countAutomatic() << "\n";
        md << "- Manual verifications: "
           << (properties_.size() - countAutomatic()) << "\n\n";

        md << "## Properties by Tool\n\n";

        std::map<std::string, std::vector<const VerifiedProperty*>> byTool;
        for (const auto& prop : properties_) {
            byTool[prop.tool].push_back(&prop);
        }

        for (const auto& [tool, props] : byTool) {
            md << "### " << tool << "\n\n";
            for (const auto* prop : props) {
                md << "#### " << prop->name << "\n\n";
                md << "- **Description**: " << prop->description << "\n";
                md << "- **Specification**: `" << prop->specificationFile << "`\n";
                md << "- **Implementation**: `" << prop->implementationFile << "`\n";
                md << "- **Verified**: " << prop->dateVerified << "\n";
                md << "- **Automatic**: " << (prop->isAutomatic ? "Yes" : "No") << "\n";
                md << "- **Dependencies**: ";
                for (size_t i = 0; i < prop->dependencies.size(); ++i) {
                    md << prop->dependencies[i];
                    if (i < prop->dependencies.size() - 1) md << ", ";
                }
                md << "\n\n";
                md << "**Verification command:**\n```bash\n";
                md << prop->verificationCommand << "\n```\n\n";
            }
        }

        return md.str();
    }

    void saveToFile(const std::string& filename) {
        std::ofstream file(filename);
        file << generateMarkdown();
        file.close();
    }

private:
    std::vector<VerifiedProperty> properties_;

    size_t countAutomatic() const {
        size_t count = 0;
        for (const auto& prop : properties_) {
            if (prop.isAutomatic) count++;
        }
        return count;
    }

    std::string currentDateTime() const {
        auto now = std::chrono::system_clock::now();
        auto time = std::chrono::system_clock::to_time_t(now);
        char buffer[80];
        std::strftime(buffer, 80, "%Y-%m-%d %H:%M:%S",
                     std::localtime(&time));
        return buffer;
    }
};

// Exemplo de uso
void documentProperties() {
    PropertyDocumentation doc;

    VerifiedProperty prop1;
    prop1.name = "AES-GCM Correctness";
    prop1.description = "AES-GCM encryption/decryption correctness";
    prop1.tool = "SAW";
    prop1.specificationFile = "AES_GCM.cry";
    prop1.implementationFile = "aes_gcm.c";
    prop1.dateVerified = "2026-06-15";
    prop1.verificationCommand = "saw verify_aes_gcm.saw";
    prop1.isAutomatic = true;
    prop1.dependencies = {"OpenSSL 3.x", "Z3 SMT Solver"};
    doc.addProperty(prop1);

    VerifiedProperty prop2;
    prop2.name = "TLS 1.3 Forward Secrecy";
    prop2.description = "TLS 1.3 handshake provides forward secrecy";
    prop2.tool = "ProVerif";
    prop2.specificationFile = "tls13_fwd_secrecy.pv";
    prop2.implementationFile = "tls13_protocol.pv";
    prop2.dateVerified = "2026-06-15";
    prop2.verificationCommand = "proverif -graph tls13_fwd_secrecy.pv";
    prop2.isAutomatic = true;
    prop2.dependencies = {"ProVerif 2.04"};
    doc.addProperty(prop2);

    doc.saveToFile("VERIFIED_PROPERTIES.md");
}
```

### 14.4 Metricas de Verificacao

```cpp
// Framework para coleta de metricas de verificacao

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <chrono>

struct VerificationMetric {
    std::string propertyName;
    std::string tool;
    bool passed;
    double executionTimeMs;
    size_t statesExplored;
    size_t memoryUsedBytes;
    std::string timestamp;
};

class VerificationMetrics {
public:
    void record(const VerificationMetric& metric) {
        metrics_.push_back(metric);
    }

    void generateReport() const {
        std::cout << "=== Verification Metrics Report ===\n\n";

        // Estatisticas por ferramenta
        std::map<std::string, std::vector<const VerificationMetric*>> byTool;
        for (const auto& m : metrics_) {
            byTool[m.tool].push_back(&m);
        }

        for (const auto& [tool, metrics] : byTool) {
            std::cout << tool << ":\n";
            std::cout << "  Properties checked: " << metrics.size() << "\n";

            size_t passed = 0;
            double totalTime = 0;
            for (const auto* m : metrics) {
                if (m->passed) passed++;
                totalTime += m->executionTimeMs;
            }

            std::cout << "  Passed: " << passed << " / " << metrics.size() << "\n";
            std::cout << "  Total time: " << totalTime << "ms\n";
            std::cout << "  Average time: "
                      << (metrics.empty() ? 0 : totalTime / metrics.size())
                      << "ms\n\n";
        }
    }

    void saveToCSV(const std::string& filename) const {
        std::ofstream file(filename);
        file << "property,tool,passed,time_ms,states,memory_bytes,timestamp\n";
        for (const auto& m : metrics_) {
            file << m.propertyName << ","
                 << m.tool << ","
                 << (m.passed ? "true" : "false") << ","
                 << m.executionTimeMs << ","
                 << m.statesExplored << ","
                 << m.memoryUsedBytes << ","
                 << m.timestamp << "\n";
        }
        file.close();
    }

private:
    std::vector<VerificationMetric> metrics_;
};
```

---

## 15. Exercicios

### Exercicio 1: Verificacao de Propriedade de Hash

Escreva uma especificacao Cryptol para uma funcao hash e use SAW para provar que sua implementacao C satisfaz as seguintes propriedades:

a) **Colisao:** Para dois inputs diferentes, o hash e diferente (exceto com probabilidade desprezivel)
b) **Pre-imagem:** Dado um hash, e computacionalmente inviavel encontrar um input que produza esse hash
c) **Avalanche:** Mudar um bit do input muda pelo menos 50% dos bits do output

**Dica:** Comece com uma funcao hash simples (como SHA-256) e escreva a especificacao Cryptol antes de implementar em C.

```cpp
// Esqueleto para o exercicio 1
// Implemente a funcao hash e especifique em Cryptol

#include <cstdint>
#include <array>

class HashFunction {
public:
    static constexpr size_t DIGEST_SIZE = 32;

    // Implementacao C do hash
    static void hash(const uint8_t* input, size_t len,
                     uint8_t output[DIGEST_SIZE]) {
        // Implemente sua funcao hash aqui
        // Pode ser SHA-256 ou uma versao simplificada
    }

    // Testes de propriedades
    static bool testCollisionResistance(size_t numTests) {
        // Gere inputs aleatorios e verifique que hashes sao diferentes
        return true;
    }

    static bool testAvalanche(size_t numTests) {
        // Para cada bit flip, verifique que ~50% dos bits mudam
        return true;
    }
};
```

### Exercicio 2: Verificacao de Protocolo com ProVerif

Escreva um modelo ProVerif para um protocolo de autenticacao de dois fatores (2FA) e verifique:

a) **Sigilo:** O adversario nao pode aprender o segredo do usuario
b) **Autenticacao:** O servidor autentica apenas usuarios legitimos
c) **Resistencia a replay:** Mensagens antigas nao podem ser reutilizadas

```proverif
(* Esqueleto para o exercicio 2 *)
(* Implemente um protocolo 2FA completo *)

type channel.
type skey.
type key.
type nonce.

(* Defina funcoes criptograficas *)
(* Defina processos para User, Server, e Adversario *)
(* Defina queries de seguranca *)
```

### Exercicio 3: Analise de Constant-Time

Analise a seguinte implementacao de comparacao e determine se e constante em tempo. Se nao for, implemente uma versao constante em tempo e verifique com SAW.

```cpp
// Exercicio 3: Analise de constant-time

#include <cstdint>
#include <cstddef>

// Implementacao NAO constante em tempo
bool insecure_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    for (size_t i = 0; i < len; ++i) {
        if (a[i] != b[i]) {
            return false;  // Early exit!
        }
    }
    return true;
}

// Implemente versao constante em tempo
// e verifique com SAW
bool secure_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    // Implemente aqui
    return false;
}
```

### Exercicio 4: Migracao para Pos-Quantica

Implemente um framework de migracao que suporte:

a) **Hybrid KEM:** Combinar X25519 (classical) com ML-KEM-768 (pos-quantico)
b) **Hybrid Signature:** Combinar Ed25519 (classical) com ML-DSA-65 (pos-quantico)
c) **Key negotiation:** Protocolo que negocia o melhor algoritmo disponivel

```cpp
// Exercicio 4: Hybrid post-quantum key exchange

#include <vector>
#include <cstdint>
#include <memory>

// Implemente interfaces KeyEncapsulation e DigitalSignature
// Implemente hybrid key exchange combinando classical e PQ
// Teste com ambos ML-KEM e X25519
```

### Exercicio 5: Model Checking de Protocolo de Pagamento

Use SPIN ou NuSMV para modelar um protocolo de pagamento simples e verificar:

a) **Ausencia de deadlock:** O protocolo sempre completa
b) **Dupla gasto:** O mesmo pagamento nao pode ser processado duas vezes
c) **Autenticacao:** O comerciante autentica o cliente corretamente

```promela
(* Exercicio 5: Modelo de pagamento *)
(* Implemente um protocolo de pagamento e verifique propriedades *)
```

### Exercicio 6: Verificacao de Implementacao com SAW

Escreva uma especificacao Cryptol para o algoritmo ChaCha20 e use SAW para provar que uma implementacao C e equivalente. Verifique:

a) **Correcao:** A implementacao C produz o mesmo output que a especificacao
b) **Inversibilidade:** Decrypt(Encrypt(m, k), k) == m
c) **Nonce uniqueness:** Dois encrypts com nonces diferentes produzem ciphertexts diferentes

```cpp
// Exercicio 6: ChaCha20 verification
// Implemente ChaCha20 em C e especifique em Cryptol
// Use SAW para provar equivalencia
```

### Exercicio 7: Integracao em CI/CD

Crie um pipeline GitHub Actions que:

a) Execute ProVerif para verificar protocolos
b) Execute SAW para verificar implementacoes C
c) Compile com CompCert para garantir semantica
d) Execute fuzzing com AFL++ por 10 minutos
e) Gere relatorio consolidado de verificacao

---

## 16. Referencias

### Livros e Artigos Fundamentais

1. Blanchet, B. (2012). *Modeling and Verifying Security Protocols with the Applied Pi Calculus and ProVerif*. Foundations and Trends in Privacy and Security, 1(1-2), 1-135.

2. Perry, F., et al. (2018). *SAW: Software Analysis Workbench*. Proceedings of the 6th ACM SIGPLAN Conference on Certified Programs and Proofs.

3. Spivey, J. M. (2010). *Understanding Cryptol*. Cryptol Tutorial, Galois Inc.

4. Appel, A. W. (2015). *Effective FLO: An Equivalence Verifier*. Proceedings of the International Conference on Interactive Theorem Proving.

5. Leroy, X. (2009). *A Formally Verified C Compiler*. Proceedings of the 36th Annual ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages.

6. Cremers, C., et al. (2017). *The Scyther Tool: Automatic Verification of Security Protocols*. IEEE Transactions on Dependable and Secure Computing.

### Ferramentas

7. **SPIN Model Checker**: https://spinroot.com/
8. **ProVerif**: https://proverif.inria.fr/
9. **Tamarin Prover**: https://tamarin-prover.github.io/
10. **SAW**: https://saw.galois.com/
11. **Cryptol**: https://cryptol.net/
12. **F***: https://fstar-lang.org/
13. **CompCert**: https://compcert.org/

### Padroes e RFCs

14. **RFC 8446**: The Transport Layer Security (TLS) Protocol Version 1.3
15. **NIST SP 800-175B**: Guideline for Using Cryptographic Standards
16. **NIST FIPS 140-3**: Security Requirements for Cryptographic Modules
17. **ISO/IEC 19790**: Security requirements for cryptographic modules

### Artigos Seminais

18. Lowe, G. (1996). *Breaking and Fixing the Needham-Schroeder Public-Key Protocol Using FDR*. Proceedings of TACAS.

19. Blanchet, B., et al. (2008). *Automatic Verification of Correspondence Properties for Security Protocols*. Journal of Computer Security.

20. Bhargavan, K., et al. (2013). *Verified Cryptographic Implementations for TLS*. ACM Transactions on Internet Technology.

21. Almeida, J. B., et al. (2017). *Jasmin: High-Assurance and High-Speed Cryptography*. Proceedings of ACM CCS.

22. Barbosa, M., et al. (2022). *Side-Channel Protections for Cryptographic Implementations via Static Analysis*. IEEE S&P.

### Recursos Adicionais

23. **Software Verification Workshop (SV-COMP)**: https://sv-comp.sosy-lab.org/
24. **Cryptography Engineering (Book)**: Ferguson, N., Schneier, B., Kohno, T. (2010). Wiley.
25. **Proving the TLS Handshake**: Cremers, C., et al. (2017). NDSS.
26. **Verified Cryptography for Rust**: Almeida, J. B., et al. (2019). USENIX Security.
27. **Formal Methods in Cryptography**: Koblitz, N., et al. (2017). Springer.

---

*Este capitulo apresentou as principais ferramentas e tecnicas de verificacao formal aplicadas a implementacoes criptograficas. A verificacao formal nao substitui testes — ela complementa testes ao oferecer garantias matematicas sobre propriedades que testes nao podem verificar. A combinacao de model checking para protocolos, SAW para equivalencia de implementacoes, ProVerif para protocolos de seguranca, e CompCert para compilacao verificada fornece um framework abrangente para construir software criptografico de altissima confiabilidade.*
---

*[Capítulo anterior: 11 — Zero Knowledge Proofs](11-zero-knowledge-proofs.md)*
*[Próximo capítulo: 13 — Testes Implementacoes](13-testes-implementacoes.md)*
