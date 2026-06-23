# Capítulo 10 — Criptografia Homomórfica

## Computação Segura sobre Dados Encriptados em C++17

---

## Sumário

- [10.1 Objetivos de Aprendizado](#101-objetivos-de-aprendizado)
- [10.2 O que é Criptografia Homomórfica?](#102-o-que-é-criptografia-homomórfica)
- [10.3 Taxonomia dos Esquemas HE](#103-taxonomia-dos-esquemas-he)
- [10.4 Microsoft SEAL: Fundamentos](#104-microsoft-seal-fundamentos)
- [10.5 BGV/BFV: Aritmética Inteira sobre Ciphertexts](#105-bgvbfv-aritmética-inteira-sobre-ciphertexts)
- [10.6 CKKS: Aritmética Aproximada](#106-ckks-aritmética-aproximada)
- [10.7 TFHE: Portas Booleanas sobre Ciphertexts](#107-tfhe-portas-booleanas-sobre-ciphertexts)
- [10.8 Características de Performance e Gerenciamento de Ruído](#108-características-de-performance-e-gerenciamento-de-ruído)
- [10.9 Casos de Uso](#109-casos-de-uso)
- [10.10 Limitações e Bootstrapping](#1010-limitações-e-bootstrapping)
- [10.11 Exemplo Completo: Interseção Privativa de Conjuntos](#1011-exemplo-completo-interseção-privativa-de-conjuntos)
- [10.12 Comparação de Bibliotecas](#1012-comparação-de-bibliotecas)
- [10.13 Exercícios](#1013-exercícios)
- [10.14 Referências](#1014-referências)

---

## 10.1 Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

1. **Compreender os fundamentos teóricos** da criptografia homomórfica e por que ela representa um paradigma revolucionário em segurança computacional.

2. **Distinguir entre os diferentes tipos** de esquemas homomórficos: parcialmente homomórficos (PHE), somewhat homomórficos (SHE), e totalmente homomórficos (FHE).

3. **Configurar e utilizar o Microsoft SEAL** em projetos C++17, incluindo a geração de chaves, encriptação, computação e decriptação.

4. **Implementar operações aritméticas** sobre dados encriptados usando os esquemas BGV e BFV para inteiros e CKKS para números de ponto flutuante.

5. **Entender o gerenciamento de ruído** em esquemas baseados em reticulados e como o bootstrapping permite computação arbitrariamente profunda.

6. **Avaliar trade-offs** entre diferentes bibliotecas FHE (SEAL, HElib, Lattigo, TFHE) para decisões de arquitetura.

7. **Implementar protocolos criptográficos avançados**, como interseção privativa de conjuntos, usando criptografia homomórfica.

8. **Analisar as limitações** práticas da FHE em termos de performance, consumo de memória e viabilidade para produção.

---

## 10.2 O que é Criptografia Homomórfica?

### 10.2.1 O Problema Fundamental

A criptografia tradicional resolve um problema aparentemente impossível: permitir que duas partes comuniquem dados sensíveis através de um canal inseguro. No entanto, essa solução introduz uma limitação fundamental — para **processar** dados encriptados, o servidor precisa primeiramente **decriptá-los**.

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Cliente    │ ──────► │   Servidor   │ ──────► │  Resultado  │
│  (dados     │ 密文    │  (precisa   │  密文    │  (precisa  │
│   sensíveis)│         │  ver dados)  │         │  decriptar) │
└─────────────┘         └─────────────┘         └─────────────┘
```

Esse modelo requer **confiança** no servidor — ele deve ser honesto, competente e não comprometido. Na prática, essa confiança frequentemente falha:

- **Violações de dados**: servidores são invadidos regularmente
- **Insider threats**: funcionários maliciosos acessam dados
- **Cumprimento de ordens judiciais**: governos podem compelir servidores a entregar dados
- **Subcontratação**: dados passam por terceiros que podem ser negligentes

### 10.2.2 A Solução: Computação sobre Dados Encriptados

A criptografia homomórfica (HE) resolve esse problema ao permitir que **cálculos sejam realizados diretamente sobre dados encriptados**, sem que o servidor ever precise acessar os dados em texto plano.

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Cliente    │ ──────► │   Servidor   │ ──────► │   Cliente   │
│  (dados     │  密文    │  computa    │  密文    │  decripta  │
│   sensíveis)│         │  sem ver!   │         │  resultado  │
└─────────────┘         └─────────────┘         └─────────────┘
```

A propriedade matemática que torna isso possível é a **homomorfismo**: se `E(x)` denota a encriptação de `x`, então para certas operações `⊕`:

```
E(x) ⊕ E(y) = E(x + y)
```

O servidor pode combinar dois ciphertexts e, quando o cliente decriptar o resultado, obterá a soma dos dados originais — sem que o servidor jamais saiba quais valores estavam encriptados.

### 10.2.3 Analogia com o Mundo Físico

Imagine uma **caixa-forte com luvas**. A caixa-forte permite que você insira suas mãos através de luvas de borracha grossa e manipule objetos dentro dela, sem nunca poder abri-la ou ver o que está dentro. Alguém de fora pode ordenar que você execute tarefas (mover objetos, somar pesos, comparar tamanhos), mas nunca poderá acessar os objetos diretamente.

Essa analogia é imperfeita — na criptografia homomórfica, as operações são limitadas ao conjunto de operações suportadas pelo esquema, e há "desgaste" (ruído) a cada operação. Mas captura a essência: **o computador processa dados sem nunca vê-los**.

### 10.2.4 Definição Formal

Um esquema de criptografia homomórfica é um esquema de encriptação com a seguinte propriedade adicional:

Dado um conjunto de operações `F = {f₁, f₂, ..., fₖ}`, o esquema é **F-homomórfico** se, para toda chave de encriptação `pk`, para todo dado `x`, e para toda operação `f ∈ F`:

```
Dec(sk, f(E(pk, x₁), E(pk, x₂), ..., E(pk, xₙ))) = f(x₁, x₂, ..., xₙ)
```

Em palavras: decriptar o resultado da operação aplicada a ciphertexts produz o mesmo resultado que aplicar a operação diretamente aos dados originais.

### 10.2.5 Propriedades de Segurança

A segurança da criptografia homomórfica é baseada em **hard problems** da teoria dos reticulados (lattice problems), que são considerados resistentes a ataques quânticos:

**Learning With Errors (LWE):**
Dado um par ` (A, b = A·s + e) ` onde `A` é uma matriz aleatória, `s` é o vetor secreto, e `e` é um vetor de erros pequenos, encontrar `s` éComputacionalmente difícil.

**Ring-LWE:**
Uma variante estruturada do LWE que opera sobre anéis polinomiais, permitindo representações mais compactas e operações mais eficientes.

**Decisional版本:**
O adversário deve **distinguir** entre pares `(A, A·s + e)` e `(A, u)` onde `u` é uniformemente aleatório. Mesmo essa tarefa aparentemente mais fácil é computacionalmente difícil.

Esses problemas são considerados **Hard** mesmo para computadores quânticos, o que significa que a criptografia homomórfica oferece segurança de longo prazo — um diferencial crucial em relação a RSA e ECC.

### 10.2.6 Breve Histórico

| Ano | Marco | Significado |
|-----|-------|-------------|
| 1978 | Rivest, Shamir, Adleman | RSA descoberto; propriedade multiplicativa intrínseca |
| 1982 | Goldwasser, Micali | Conceito formal de criptografia probabilística |
| 1999 | Paillier | Esquema PHE aditivo eficiente baseado em residuos quadráticos |
| 2005 | Gentry | Primeiro esquema FHE prático baseado em ideal lattices |
| 2011 | BGV (Brakerski, Gentry, Vaikuntanathan) | FHE eficiente baseado em LWE com rotação de chave |
| 2012 | BFV (Brakerski/Fan-Vercauteren) | Variante BGV com operações de mensagens |
| 2016 | CKKS (Cheon, Kim, Kim, Song) | Aritmética aproximada para números reais |
| 2016 | TFHE (Chillotti, Gama, Georgieva, Izabachene) | FHE baseado em torções com bootstrapping eficiente |
| 2018 | Microsoft SEAL | Biblioteca open-source da Microsoft |
| 2020 | Concrete (Zama) | TFHE otimizado para produção |
| 2022 | FHE Standardization | Padronização em andamento |

---

## 10.3 Taxonomia dos Esquemas HE

### 10.3.1 Visão Geral da Hierarquia

A criptografia homomórfica pode ser classificada em três categorias, baseadas na riqueza de operações suportadas:

```
                    ┌─────────────────────────────────────────┐
                    │       Criptografia Homomórfica           │
                    └─────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
    ┌─────────▼─────────┐  ┌─────────▼─────────┐  ┌─────────▼─────────┐
    │  Parcialmente HE   │  │  Somewhat HE      │  │  Totally HE       │
    │  (PHE)             │  │  (SHE)            │  │  (FHE)            │
    │                    │  │                   │  │                   │
    │  Paillier          │  │  BGV, BFV         │  │  CKKS, TFHE       │
    │  RSA (múltiplo)    │  │  (com limites)    │  │  (ilimitado)      │
    └────────────────────┘  └───────────────────┘  └───────────────────┘
```

### 10.3.2 Parcialmente Homomórfico (PHE)

Um esquema PHE suporta apenas **um tipo de operação** sobre ciphertexts, com número ilimitado de aplicações.

**RSA (multiplicativo):**
```
E(x) · E(y) = E(x · y)     // homomórfico multiplicativamente
```

O RSA original é naturalmente homomórfico em relação à multiplicação. Se `c₁ = m₁^e mod N` e `c₂ = m₂^e mod N`, então `c₁ · c₂ = (m₁ · m₂)^e mod N`.

**Paillier (aditivo):**
```
E(x) · E(y) = E(x + y)     // homomórfico aditivamente
```

O esquema de Paillier, baseado em residuos quadráticos módulo `N²`, é homomórfico em relação à adição:

```cpp
// Esquema Paillier simplificado
// Chave pública: (N, g) onde N = p·q, p e q primos
// Encriptação: c = g^m · r^N mod N²
// Decriptação: m = L(c^λ mod N²) · μ mod N

// Homomorfismo aditivo:
// E(m₁) · E(m₂) mod N² = E(m₁ + m₂)
// E(m)^k mod N² = E(m · k)    para inteiro k
```

**Vantagens do PHE:**
- Alta performance: operações são rápidas
- Sem necessidade de bootstrapping
- Fácil de implementar e otimizar
- Adequado para aplicações específicas (votação, contagem)

**Limitações:**
- Apenas uma operação (ou soma ou produto)
- Não permite circuitos computacionais complexos

**Aplicação típica — Votação Eletrônica:**
```cpp
// Servidor de votação recebe ciphertexts de votos
// Pode computar a contagem total sem ver votos individuais
E(voto1) · E(voto2) · E(voto3) · ... · E(votoN) = E(voto1 + voto2 + ... + votoN)
```

### 10.3.3 Somewhat Homomórfico (SHE)

Um esquema SHE suporta **ambas as operações** (adição e multiplicação), mas com um **número limitado** de operações antes de o ruído acumulado tornar a decriptação incorreta.

**A Intuição do Ruído:**
Cada operação homomórfica adiciona uma pequena quantidade de "ruído" ao ciphertext. Após muitas operações, o ruído domina a mensagem e a decriptação falha.

```
Ciphertext inicial:  m + ruídoPequeno
Após 1 adição:       m + ruídoMédio
Após 1 multiplicação: m + ruídoGrande
Após 5 multiplicações: m + ruídoDominante → DECRYPT FAIL
```

**Nível de Ruído (Noise Budget):**
O conceito de "noise budget" é central em SHE e FHE:

```
Noise Budget = log(q) - log(noise)
```

onde `q` é o módulo de ciphertext e `noise` é a magnitude do ruído atual. Cada operação consome uma quantidade fixa do budget:

| Operação | Custo em Noise Budget |
|----------|----------------------|
| Adição   | ~0 bits (cresce log) |
| Multiplicação | ~Δ bits (cresce exponencialmente) |

O esquema é "somewhat" porque suporta um número **finito** de multiplicações antes do budget se esgotar.

**Esquemas SHE principais:**

**BGV (Brakerski-Gentry-Vaikuntanathan):**
- Baseado em LWE/Ring-LWE
- Suporta operações exatas sobre inteiros
- Usa modulus switching para controlar crescimento de ruído
- Adequado para aritmética modular

**BFV (Brakerski/Fan-Vercauteren):**
- Variante do BGV com mensagens definidas no anel
- Usa Relinearization para manter ciphertexts compactos
- Implementado no Microsoft SEAL como esquema de inteiros

**Limite prático:**
Em um cenário típico com parâmetros de segurança de 128 bits, um esquema SHE pode suportar aproximadamente:
- 4-6 multiplicações em cadeia, ou
- Circuitos de profundidade limitada (e.g., classificadores lineares simples)

### 10.3.4 Totalmente Homomórfico (FHE)

Um esquema FHE permite computação **arbitrária** sobre dados encriptados. Teoricamente, qualquer programa pode ser executado sobre ciphertexts — é uma "máquina de Turing criptografada".

**A Solução de Gentry (2009):**
Craig Gentry mostrou que a construção de um FHE a partir de um SHE é possível através de uma técnica chamada **bootstrapping**:

1. Comece com um SHE que suporta algumas operações
2. O bootstrapping "renova" o ciphertext, reduzindo o ruído
3. Isso permite encadear operações infinitamente

**O Bootstrapping — Ideia Central:**
O bootstrapping é essencialmente uma **decriptação homomórfica**: o servidor encripta a chave de decriptação, e usa o SHE para decriptar o ciphertext ruidoso, produzindo um novo ciphertext com ruído menor.

```
Antes do bootstrapping:  CT(m, noise_grande)
Chave de decriptação encriptada: EK = E(sk)
Bootstrapping: CT_novo = HomDec(CT_velho, EK)
Depois: CT_novo(m, noise_pequeno)
```

**Esquemas FHE principais:**

**CKKS (Cheon-Kim-Kim-Song):**
- Aritmética **aproximada** sobre números reais/complexos
- Mensagens são vetores de ponto flutuante
- Erro de precisão é aceitável (e até desejável) para ML
- Ideal para machine learning e análise de dados
- Usado em privacy-preserving ML

**TFHE (Torus FHE):**
- Baseado em LWE sobre o torus `T = R/Z`
- Suporta operações bit-a-bit (portas booleanas)
- Bootstrapping eficiente (~10ms por gate)
- Ideal para lógica booleana arbitrária
- Usado em computação genérica de baixo nível

### 10.3.5 Tabela Comparativa

| Propriedade | PHE (Paillier) | SHE (BGV/BFV) | FHE (CKKS) | FHE (TFHE) |
|-------------|----------------|---------------|------------|------------|
| Adição | Sim | Sim | Sim | Sim (bits) |
| Multiplicação | Nao | Sim (limitado) | Sim (limitado) | Via gates |
| Profundidade | Infinita (1 op) | Limitada (~4-8) | Limitada sem bootstrapping | Infinita |
| Tipo de dado | Inteiros | Inteiros mod q | Ponto flutuante | Bits |
| Precisão | Exata | Exata | Aproximada | Exata (bits) |
| Performance | Muito rápida | Rápida | Moderada | Lenta |
| Uso típico | Votação | Contadores, agregações | ML, análise | Criptografia genérica |
| Bootstrapping | Nao | Não necessário | Opcional | Central |

### 10.3.6 Escolhendo o Esquema Certo

A decisão de qual esquema usar depende do problema específico:

```
┌────────────────────────────────────────────────────────────┐
│                    Fluxo de Decisão HE                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Precisa apenas de soma?                                   │
│  ├─ Sim → Paillier (PHE aditivo)                          │
│  └─ Não ↓                                                 │
│                                                            │
│  Precisa apenas de produto?                                │
│  ├─ Sim → RSA (PHE multiplicativo)                        │
│  └─ Não ↓                                                 │
│                                                            │
│  Precisa de adição + multiplicação sobre inteiros?         │
│  ├─ Sim, poucas multiplicações → BGV/BFV (SHE)           │
│  └─ Não ↓                                                 │
│                                                            │
│  Precisa de ML/análise sobre números reais?                │
│  ├─ Sim → CKKS (FHE aproximado)                           │
│  └─ Não ↓                                                 │
│                                                            │
│  Precisa de computação booleana arbitrária?                │
│  ├─ Sim → TFHE (FHE booleano)                             │
│  └─ Não ↓                                                 │
│                                                            │
│  Use FHE com bootstrapping (CKKS ou TFHE)                 │
└────────────────────────────────────────────────────────────┘
```

---

## 10.4 Microsoft SEAL: Fundamentos

### 10.4.1 O que é o Microsoft SEAL?

O Microsoft SEAL é uma biblioteca open-source de criptografia homomórfica desenvolvida pelo Microsoft Research. Escrita em C++17, ela implementa três esquemas principais:

- **BFV** (Brakerski/Fan-Vercauteren): aritmética sobre inteiros mod q
- **BGV** (Brakerski/Gentry/Vaikuntanathan): variante de BGV para inteiros
- **CKKS** (Cheon/Kim/Kim/Song): aritmética aproximada sobre números reais

**Características:**
- Totalmente open-source (MIT License)
- Sem dependências externas
- Otimizado para performance em x86-64
- Suporte a parallelismo via OpenMP
- APIs para C++ e Python

### 10.4.2 Arquitetura do SEAL

```
┌─────────────────────────────────────────────────────┐
│                   Microsoft SEAL                    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │    BFV      │  │    BGV      │  │    CKKS     ││
│  │  (inteiros) │  │  (inteiros) │  │  (reais)    ││
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘│
│         │                │                │        │
│  ┌──────▼────────────────▼────────────────▼──────┐│
│  │         Core Library (C++17)                  ││
│  │  ┌────────────┐  ┌──────────────────────┐    ││
│  │  │ Relinear.  │  │ Rescaling (CKKS)     │    ││
│  │  └────────────┘  └──────────────────────┘    ││
│  │  ┌────────────┐  ┌──────────────────────┐    ││
│  │  │ Galois     │  │ Rotation Keys        │    ││
│  │  └────────────┘  └──────────────────────┘    ││
│  │  ┌──────────────────────────────────────┐    ││
│  │  │ NTT (Number Theoretic Transform)     │    ││
│  │  └──────────────────────────────────────┘    ││
│  └──────────────────────────────────────────────┘│
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  MemoryPool, Serialization, ThreadSafety     │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 10.4.3 Instalação e Configuração

**Compilando o SEAL a partir do código-fonte:**

```bash
# Clonar o repositório
git clone https://github.com/microsoft/SEAL.git
cd SEAL

# Criar diretório de build
mkdir build && cd build

# Configurar com CMake
cmake -S .. -B . \
    -DSEAL_BUILD_TESTS=OFF \
    -DSEAL_BUILD_DEPS=ON \
    -DSEAL_BUILD_SEAL_C=ON \
    -DCMAKE_BUILD_TYPE=Release

# Compilar (use -j para paralelismo)
cmake --build . --config Release -j$(nproc)

# Instalar
sudo cmake --install .
```

**Configuração em CMakeLists.txt do seu projeto:**

```cmake
cmake_minimum_required(VERSION 3.16)
project(HEProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Encontrar o SEAL instalado
find_package(SEAL REQUIRED)

# Definir o executável
add_executable(he_example main.cpp)

# Linkar com SEAL
target_link_libraries(he_example PRIVATE SEAL::seal)
```

**Estrutura básica de um projeto:**

```
he_project/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   ├── he_utils.h
│   └── he_utils.cpp
├── tests/
│   └── test_he.cpp
└── README.md
```

### 10.4.4 Estrutura de um Programa SEAL

Todo programa SEAL segue um padrão consistente:

```cpp
#include "seal/seal.h"
#include <iostream>
#include <vector>

using namespace seal;

int main() {
    // 1. Configurar parâmetros
    EncryptionParameters params(scheme_type::bfv);
    // ... configurar parâmetros ...

    // 2. Validar parâmetros
    SEALContext context(params);

    // 3. Gerar chaves
    KeyGenerator keygen(context);
    auto secret_key = keygen.secret_key();
    PublicKey public_key;
    keygen.create_public_key(public_key);

    // 4. Criptografar dados
    Encryptor encryptor(context, public_key);
    // ...

    // 5. Realizar computação
    Evaluator evaluator(context);
    // ...

    // 6. Decriptar resultado
    Decryptor decryptor(context, secret_key);
    // ...

    return 0;
}
```

### 10.4.5 Configuração de Parâmetros

Os parâmetros controlam o trade-off entre segurança, performance e capacidade de computação:

```cpp
// Configuração para BFV (inteiros)
EncryptionParameters params(scheme_type::bfv);

// Tamanho do polinômio (grau do anel)
// Valores típicos: 1024, 2048, 4096, 8192, 16384
params.set_poly_modulus_degree(4096);

// Coeficientes do polinômio de módulo (ciphertext modulus)
// Deve ser primo e conter fator cyclotomic como divisor
params.set_coeff_modulus(
    CoeffModulus::BFVDefault(4096)
);

// Módulo da mensagem (plaintext modulus)
// Controla o range dos valores encriptados: [-t/2, t/2)
params.set_plain_modulus(1024);
```

**Impacto dos parâmetros:**

| Parâmetro | Efeito no Security | Efeito no Ruído | Efeito na Performance |
|-----------|-------------------|-----------------|----------------------|
| `poly_modulus_degree` ↑ | Segurança ↑ | Mais budget | Mais lento |
| `coeff_modulus` ↑ | Segurança ↑ | Mais budget | Mais lento |
| `plain_modulus` ↑ | Sem efeito | Mais ruído relativo | Sem efeito |

**Níveis de Segurança:**

```cpp
// SEAL fornece funções de conveniência para configurar parâmetros seguros

// Para BFV/BGV:
auto coeff_modulus = CoeffModulus::BFVDefault(
    poly_modulus_degree,     // ex: 4096
    sec_level_type::tc128    // 128 bits de segurança
);

// Para CKKS:
auto coeff_modulus = CoeffModulus::CKKS(
    poly_modulus_degree,     // ex: 8192
    {60, 40, 40, 60}        // chain depths: quantos rescalings
);
```

### 10.4.6 Geração de Chaves

```cpp
#include "seal/seal.h"
#include <iostream>

void demonstrate_key_generation() {
    using namespace seal;

    // Setup de parâmetros
    EncryptionParameters params(scheme_type::bfv);
    params.set_poly_modulus_degree(4096);
    params.set_coeff_modulus(CoeffModulus::BFVDefault(4096));
    params.set_plain_modulus(1024);

    SEALContext context(params);

    // Gerador de chaves
    KeyGenerator keygen(context);

    // Chave secreta: usada apenas pelo dono dos dados
    auto secret_key = keygen.secret_key();

    // Chave pública: distribuída ao servidor de computação
    PublicKey public_key;
    keygen.create_public_key(public_key);

    // Chaves de relinearização: usadas após multiplicações
    RelinKeys relin_keys;
    keygen.create_relin_keys(relin_keys);

    // Chaves de rotação: usadas para permutar elementos
    GaloisKeys galois_keys;
    keygen.create_galois_keys(galois_keys);

    std::cout << "Chaves geradas com sucesso.\n";
    std::cout << "Tamanho da chave secreta: "
              << secret_key.save_size() << " bytes\n";
    std::cout << "Tamanho da chave pública: "
              << public_key.save_size() << " bytes\n";
    std::cout << "Tamanho das relin keys: "
              << relin_keys.save_size() << " bytes\n";
}

int main() {
    demonstrate_key_generation();
    return 0;
}
```

### 10.4.7 Encriptação e Decriptação

```cpp
#include "seal/seal.h"
#include <iostream>
#include <vector>

using namespace seal;

int main() {
    // Setup
    EncryptionParameters params(scheme_type::bfv);
    params.set_poly_modulus_degree(4096);
    params.set_coeff_modulus(CoeffModulus::BFVDefault(4096));
    params.set_plain_modulus(1024);

    SEALContext context(params);
    KeyGenerator keygen(context);
    auto secret_key = keygen.secret_key();
    PublicKey public_key;
    keygen.create_public_key(public_key);

    // Encryptor: encripta usando chave pública
    Encryptor encryptor(context, public_key);

    // Decryptor: decripta usando chave secreta
    Decryptor decryptor(context, secret_key);

    // Criar um plaintext (mensagem)
    // BFV opera sobre inteiros mod plain_modulus
    Plaintext plain("42");  // valor 42
    std::cout << "Plaintext original: " << plain.to_string() << "\n";

    // Encriptar
    Ciphertext encrypted;
    encryptor.encrypt(plain, encrypted);

    std::cout << "Ciphertext criado com sucesso.\n";
    std::cout << "  Coeficientes: " << encrypted.coeff_count() << "\n";
    std::cout << "  Primeiro coef: " << encrypted.data()[0] << "\n";

    // Decriptar
    Plaintext decrypted;
    decryptor.decrypt(encrypted, decrypted);

    std::cout << "Plaintext decriptado: " << decrypted.to_string() << "\n";

    // Verificar
    bool correto = (decrypted.to_string() == "42");
    std::cout << "Verificacao: " << (correto ? "OK" : "FALHA") << "\n";

    return 0;
}
```

### 10.4.8 Serialização

O SEAL suporta serialização de ciphertexts e chaves para transmissão ou armazenamento:

```cpp
#include "seal/seal.h"
#include <fstream>
#include <vector>

using namespace seal;

int main() {
    // ... setup e encriptação ...

    // Serializar ciphertext para um vector de bytes
    std::vector<std::byte> encrypted_bytes;
    encrypted.save(encrypted_bytes);

    // Salvar em arquivo
    std::ofstream ofs("ciphertext.bin", std::ios::binary);
    ofs.write(
        reinterpret_cast<const char*>(encrypted_bytes.data()),
        static_cast<std::streamsize>(encrypted_bytes.size())
    );
    ofs.close();

    // Carregar de arquivo
    std::ifstream ifs("ciphertext.bin", std::ios::binary);
    std::vector<std::byte> loaded_bytes(
        (std::istreambuf_iterator<char>(ifs)),
        std::istreambuf_iterator<char>()
    );
    ifs.close();

    Ciphertext loaded_encrypted;
    loaded_encrypted.load(context, loaded_bytes.data(), loaded_bytes.size());

    std::cout << "Ciphertext serializado e carregado com sucesso.\n";

    return 0;
}
```

---

## 10.5 BGV/BFV: Aritmética Inteira sobre Ciphertexts

### 10.5.1 Modelo de Mensagem

No esquema BFV, os dados encriptados são inteiros no intervalo `[-t/2, t/2)` onde `t` é o plaintext modulus. A aritmética é **modular**:

```
E(a) + E(b) = E((a + b) mod t)
E(a) * E(b) = E((a * b) mod t)
```

Isso significa que o overflow é tratado automaticamente pela aritmética modular. Para valores fora do range, o resultado é wrap-around.

### 10.5.2 Operações Básicas

```cpp
#include "seal/seal.h"
#include <iostream>
#include <vector>

using namespace seal;

class BFVCalculator {
public:
    BFVCalculator() {
        // Configurar parâmetros BFV
        EncryptionParameters params(scheme_type::bfv);
        params.set_poly_modulus_degree(4096);
        params.set_coeff_modulus(
            CoeffModulus::BFVDefault(4096)
        );
        params.set_plain_modulus(1024);

        context_ = std::make_unique<SEALContext>(params);

        KeyGenerator keygen(*context_);
        secret_key_ = keygen.secret_key();

        PublicKey public_key;
        keygen.create_public_key(public_key);

        keygen.create_relin_keys(relin_keys_);
        keygen.create_galois_keys(galois_keys_);

        encryptor_ = std::make_unique<Encryptor>(*context_, public_key);
        evaluator_ = std::make_unique<Evaluator>(*context_);
        decryptor_ = std::make_unique<Decryptor>(*context_, secret_key_);
    }

    Ciphertext encrypt(int64_t value) {
        Plaintext plain(std::to_string(value >= 0 ? value : value + 1024));
        Ciphertext encrypted;
        encryptor_->encrypt(plain, encrypted);
        return encrypted;
    }

    int64_t decrypt(const Ciphertext& ciphertext) {
        Plaintext plain;
        decryptor_->decrypt(ciphertext, plain);
        int64_t result = static_cast<int64_t>(plain.to_string()[0] - '0');
        return result;
    }

    // Soma homomórfica
    Ciphertext add(const Ciphertext& a, const Ciphertext& b) {
        Ciphertext result;
        evaluator_->add(a, b, result);
        return result;
    }

    // Multiplicação homomórfica
    Ciphertext multiply(const Ciphertext& a, const Ciphertext& b) {
        Ciphertext result;
        evaluator_->multiply(a, b, result);
        return result;
    }

    // Relinearização (reduz tamanho do ciphertext após multiplicação)
    Ciphertext relinearize(const Ciphertext& ciphertext) {
        Ciphertext result;
        evaluator_->relinearize_inplace(ciphertext, relin_keys_);
        return ciphertext;
    }

    // Soma de N ciphertexts (voting-like)
    Ciphertext sum_many(const std::vector<Ciphertext>& ciphertexts) {
        if (ciphertexts.empty()) {
            throw std::invalid_argument("Vector vazio");
        }

        Ciphertext result = ciphertexts[0];
        for (size_t i = 1; i < ciphertexts.size(); ++i) {
            evaluator_->add_inplace(result, ciphertexts[i]);
        }
        return result;
    }

private:
    std::unique_ptr<SEALContext> context_;
    SecretKey secret_key_;
    RelinKeys relin_keys_;
    GaloisKeys galois_keys_;
    std::unique_ptr<Encryptor> encryptor_;
    std::unique_ptr<Evaluator> evaluator_;
    std::unique_ptr<Decryptor> decryptor_;
};

int main() {
    try {
        BFVCalculator calc;

        // Criptografar valores
        auto enc_a = calc.encrypt(7);
        auto enc_b = calc.encrypt(3);

        // Operações homomórficas
        auto enc_sum = calc.add(enc_a, enc_b);
        auto enc_prod = calc.multiply(enc_a, enc_b);

        // Relinearizar após multiplicação
        calc.relinearize(enc_prod);

        // Decriptar resultados
        std::cout << "7 + 3 = " << calc.decrypt(enc_sum) << "\n";
        std::cout << "7 * 3 = " << calc.decrypt(enc_prod) << "\n";

        // Soma de N valores
        std::vector<Ciphertext> votes;
        for (int i = 0; i < 5; ++i) {
            votes.push_back(calc.encrypt(1));
        }
        auto enc_total = calc.sum_many(votes);
        std::cout << "Total de votos: " << calc.decrypt(enc_total) << "\n";

    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << "\n";
    }

    return 0;
}
```

### 10.5.3 Relinearização

Após uma multiplicação, o ciphertext resultante tem **dois pares** de polinomios (efeito do ciphertext squaring). A relinearização reduz isso de volta para um par, usando as relin keys:

```
Antes: CT = (c₀, c₁, c₂)     // tamanho 3
Relin: CT' = (c₀', c₁')       // tamanho 2
```

```cpp
// Relinearização
Ciphertext multiply_and_relin(const Evaluator& evaluator,
                               const Ciphertext& a,
                               const Ciphertext& b,
                               const RelinKeys& relin_keys) {
    Ciphertext result;
    evaluator.multiply(a, b, result);
    evaluator.relinearize_inplace(result, relin_keys);
    return result;
}
```

**Quando relinearizar:**
- Sempre após uma multiplicação antes de outra operação
- Para manter ciphertexts compactos
- Para reduzir consumo de memória

### 10.5.4 Rotações

As rotações permitem permutar os coeficientes de um ciphertext vetorial:

```cpp
// Rotação de ciphertexts vetoriais
Ciphertext rotate_slots(const Evaluator& evaluator,
                        const Ciphertext& ciphertext,
                        const GaloisKeys& galois_keys,
                        int steps) {
    Ciphertext result;
    evaluator.rotate_vector(ciphertext, steps, galois_keys, result);
    return result;
}

// Exemplo: computar média de N valores encriptados
Ciphertext compute_encrypted_average(const std::vector<Ciphertext>& values,
                                     const Evaluator& evaluator,
                                     const GaloisKeys& galois_keys) {
    // Somar todos os valores
    Ciphertext sum = values[0];
    for (size_t i = 1; i < values.size(); ++i) {
        evaluator.add_inplace(sum, values[i]);
    }

    // Dividir por N (usando multiplicação por N^-1 mod t)
    // Para t=1024 e N=4: 4^-1 mod 1024 = 256 (pois 4*256 = 1024 ≡ 0)
    // Na prática, use N⁻¹ mod t correto
    Plaintext scalar("256");  // N^-1 mod 1024
    Ciphertext result;
    evaluator.multiply_plain(sum, scalar, result);

    return result;
}
```

### 10.5.5 BGV vs BFV: Diferenças Práticas

Embora BGV e BFV sejam matematicamente relacionados, há diferenças na implementação:

| Aspecto | BGV | BFV |
|---------|-----|-----|
| Modelo de mensagem | Mensagem separada | Mensagem no anel |
| Rescaling | Após cada operação | Não aplicável |
| Crescimento de módulo | Gerenciado por modulus switching | Fixo |
| Performance | Ligeiramente mais lento | Mais rápido |
| SEAL | Não implementado | Implementado |

**Nota:** O Microsoft SEAL implementa apenas BFV e CKKS. BGV está disponível em outras bibliotecas como HElib e PALISADE/OpenFHE.

---

## 10.6 CKKS: Aritmética Aproximada

### 10.6.1 O Paradigma da Aproximação

CKKS (Cheon-Kim-Kim-Song) é revolucionário porque trata mensagens como **números reais** em vez de inteiros. A crucial diferença: a decriptação produz uma **aproximação** da mensagem original, não o valor exato.

```
BFV:  Dec(E(42)) = 42              (exato)
CKKS: Dec(E(3.14159)) ≈ 3.14159   (aproximado)
```

Isso é análogo a aritmética de ponto flutuante em hardware — perdemos precisão, mas ganhamos a capacidade de representar números reais.

### 10.6.2 Encoding: Inserindo Dados Reais

CKKS encripta **vetores** de números reais, não valores únicos. O encoding agrupa múltiplos valores em um único plaintext:

```cpp
#include "seal/seal.h"
#include <iostream>
#include <vector>
#include <cmath>

using namespace seal;

int main() {
    // Setup CKKS
    EncryptionParameters params(scheme_type::ckks);
    params.set_poly_modulus_degree(8192);
    params.set_coeff_modulus(CoeffModulus::CKKS(
        8192, {60, 40, 40, 60}
    ));
    params.set_plain_modulus(0);  // CKKS não usa plain_modulus fixo

    SEALContext context(params);
    KeyGenerator keygen(context);
    auto secret_key = keygen.secret_key();
    PublicKey public_key;
    keygen.create_public_key(public_key);
    RelinKeys relin_keys;
    keygen.create_relin_keys(relin_keys);

    Encryptor encryptor(context, public_key);
    Evaluator evaluator(context);
    Decryptor decryptor(context, secret_key);

    // CKKSEncoder: codifica vetores reais em plaintexts
    CKKSEncoder encoder(context);

    // Parâmetros de escala
    // scale controla a precisão: mais bits = mais precisão
    double scale = pow(2.0, 40);

    // Dados de entrada
    std::vector<double> x = {1.0, 2.0, 3.0, 4.0};
    std::vector<double> y = {5.0, 6.0, 7.0, 0.5};

    // Codificar e encriptar
    Plaintext plain_x, plain_y;
    encoder.encode(x, scale, plain_x);
    encoder.encode(y, scale, plain_y);

    Ciphertext enc_x, enc_y;
    encryptor.encrypt(plain_x, enc_x);
    encryptor.encrypt(plain_y, enc_y);

    // Operações homomórficas
    Ciphertext enc_sum, enc_prod, enc_diff;
    evaluator.add(enc_x, enc_y, enc_sum);
    evaluator.multiply(enc_x, enc_y, enc_prod);
    evaluator.sub(enc_x, enc_y, enc_diff);

    // Relinearizar e rescale (essencial em CKKS!)
    evaluator.relinearize_inplace(enc_prod, relin_keys);
    evaluator.rescale_to_next_inplace(enc_prod, scale);
    evaluator.rescale_to_next_inplace(enc_sum, scale);
    evaluator.rescale_to_next_inplace(enc_diff, scale);

    // Decriptar e decodificar
    Plaintext plain_result_x, plain_result_y, plain_result_z;
    decryptor.decrypt(enc_sum, plain_result_x);
    decryptor.decrypt(enc_prod, plain_result_y);
    decryptor.decrypt(enc_diff, plain_result_z);

    std::vector<double> result_sum, result_prod, result_diff;
    encoder.decode(plain_result_x, result_sum);
    encoder.decode(plain_result_y, result_prod);
    encoder.decode(plain_result_z, result_diff);

    std::cout << "Soma:    [";
    for (size_t i = 0; i < result_sum.size(); ++i) {
        std::cout << result_sum[i];
        if (i < result_sum.size() - 1) std::cout << ", ";
    }
    std::cout << "]\n";

    std::cout << "Produto: [";
    for (size_t i = 0; i < result_prod.size(); ++i) {
        std::cout << result_prod[i];
        if (i < result_prod.size() - 1) std::cout << ", ";
    }
    std::cout << "]\n";

    std::cout << "Diferenca: [";
    for (size_t i = 0; i < result_diff.size(); ++i) {
        std::cout << result_diff[i];
        if (i < result_diff.size() - 1) std::cout << ", ";
    }
    std::cout << "]\n";

    return 0;
}
```

### 10.6.3 Rescaling: Gerenciamento de Escala

Em CKKS, cada multiplicação **dobra a escala** do ciphertext. Sem rescaling, a escala cresceria exponencialmente e rapidamente excederia o ciphertext modulus.

```
Escala inicial:     s
Após 1 multiplicação: 2s
Após 2 multiplicações: 4s
...
Após k multiplicações: 2^k · s
```

O **rescaling** divide a escala por um fator do modulus chain, mantendo-a estável:

```cpp
// Rescaling: dividir escala por um nível do modulus chain
void demonstrate_rescaling(Evaluator& evaluator,
                           Ciphertext& ciphertext,
                           double& scale,
                           const RelinKeys& relin_keys) {
    std::cout << "Escala antes: " << scale << "\n";

    // Relinearizar (necessário após multiplicação)
    evaluator.relinearize_inplace(ciphertext, relin_keys);

    // Rescale: dividir escala e descer um nível no modulus chain
    evaluator.rescale_to_next_inplace(ciphertext, scale);

    std::cout << "Escala depois: " << scale << "\n";
    // scale ≈ scale / 2^40 (depende do coeff_modulus)
}
```

**Regra de ouro:** Antes de somar dois ciphertexts, eles devem estar no **mesmo nível** do modulus chain e com a **mesma escala**.

### 10.6.4 Operações Aritméticas Completa

```cpp
class CKKSCalculator {
public:
    CKKSCalculator(size_t poly_modulus_degree = 8192) {
        EncryptionParameters params(scheme_type::ckks);

        // Escolher parâmetros baseado no grau do polinômio
        if (poly_modulus_degree == 8192) {
            params.set_poly_modulus_degree(8192);
            params.set_coeff_modulus(CoeffModulus::CKKS(
                8192, {60, 40, 40, 60}
            ));
        } else if (poly_modulus_degree == 16384) {
            params.set_poly_modulus_degree(16384);
            params.set_coeff_modulus(CoeffModulus::CKKS(
                16384, {60, 40, 40, 40, 40, 60}
            ));
        } else {
            throw std::invalid_argument("Grau nao suportado");
        }

        context_ = std::make_unique<SEALContext>(params);
        encoder_ = std::make_unique<CKKSEncoder>(*context_);

        KeyGenerator keygen(*context_);
        secret_key_ = keygen.secret_key();

        PublicKey public_key;
        keygen.create_public_key(public_key);

        keygen.create_relin_keys(relin_keys_);
        keygen.create_galois_keys(galois_keys_);

        encryptor_ = std::make_unique<Encryptor>(*context_, public_key);
        evaluator_ = std::make_unique<Evaluator>(*context_);
        decryptor_ = std::make_unique<Decryptor>(*context_, secret_key_);

        scale_ = pow(2.0, 40);
    }

    // Encoding/decoding
    Plaintext encode(const std::vector<double>& values) {
        Plaintext plain;
        encoder_->encode(values, scale_, plain);
        return plain;
    }

    std::vector<double> decode(const Plaintext& plain) {
        std::vector<double> values;
        encoder_->decode(plain, values);
        return values;
    }

    // Criptografia/decriptação
    Ciphertext encrypt(const std::vector<double>& values) {
        Plaintext plain = encode(values);
        Ciphertext encrypted;
        encryptor_->encrypt(plain, encrypted);
        return encrypted;
    }

    std::vector<double> decrypt(const Ciphertext& ciphertext) {
        Plaintext plain;
        decryptor_->decrypt(ciphertext, plain);
        return decode(plain);
    }

    // Operações homomórficas
    Ciphertext add(const Ciphertext& a, const Ciphertext& b) {
        Ciphertext result;
        evaluator_->add(a, b, result);
        return result;
    }

    Ciphertext sub(const Ciphertext& a, const Ciphertext& b) {
        Ciphertext result;
        evaluator_->sub(a, b, result);
        return result;
    }

    Ciphertext multiply(const Ciphertext& a, const Ciphertext& b) {
        Ciphertext result;
        evaluator_->multiply(a, b, result);
        // Relinearizar
        evaluator_->relinearize_inplace(result, relin_keys_);
        // Rescale para manter escala consistente
        evaluator_->rescale_to_next_inplace(result, scale_);
        return result;
    }

    Ciphertext multiply_plain(const Ciphertext& a, const std::vector<double>& b) {
        Plaintext plain_b;
        encoder_->encode(b, scale_, plain_b);
        Ciphertext result;
        evaluator_->multiply_plain(a, plain_b, result);
        return result;
    }

    Ciphertext add_plain(const Ciphertext& a, const std::vector<double>& b) {
        Plaintext plain_b;
        encoder_->encode(b, scale_, plain_b);
        Ciphertext result;
        evaluator_->add_plain(a, plain_b, result);
        return result;
    }

    // Rotação de slots
    Ciphertext rotate(const Ciphertext& a, int steps) {
        Ciphertext result;
        evaluator_->rotate_vector(a, steps, galois_keys_, result);
        return result;
    }

    // Soma de todos os slots (para agregar valores)
    Ciphertext sum_all_slots(const Ciphertext& a) {
        Ciphertext result = a;
        size_t slot_count = encoder_->slot_count();

        // Rotações em potências de 2
        for (size_t i = 1; i < slot_count; i <<= 1) {
            Ciphertext rotated = rotate(result, static_cast<int>(i));
            evaluator_->add_inplace(result, rotated);
        }

        return result;
    }

    double get_scale() const { return scale_; }

private:
    std::unique_ptr<SEALContext> context_;
    std::unique_ptr<CKKSEncoder> encoder_;
    SecretKey secret_key_;
    RelinKeys relin_keys_;
    GaloisKeys galois_keys_;
    std::unique_ptr<Encryptor> encryptor_;
    std::unique_ptr<Evaluator> evaluator_;
    std::unique_ptr<Decryptor> decryptor_;
    double scale_;
};

int main() {
    try {
        CKKSCalculator calc;

        // Exemplo: computar produto escalar entre dois vetores
        // a = [1.0, 2.0, 3.0, 4.0]
        // b = [5.0, 6.0, 7.0, 8.0]
        // dot = 1*5 + 2*6 + 3*7 + 4*8 = 70

        std::vector<double> a = {1.0, 2.0, 3.0, 4.0};
        std::vector<double> b = {5.0, 6.0, 7.0, 8.0};

        auto enc_a = calc.encrypt(a);
        auto enc_b = calc.encrypt(b);

        // Produto elemento a elemento
        auto enc_prod = calc.multiply(enc_a, enc_b);

        // Soma de todos os slots
        auto enc_dot = calc.sum_all_slots(enc_prod);

        // Decriptar
        auto result = calc.decrypt(enc_dot);
        std::cout << "Produto escalar: " << result[0] << "\n";
        // Resultado deve ser aproximadamente 70.0

        // Exemplo 2: média de N valores
        std::vector<double> values = {10.0, 20.0, 30.0, 40.0};
        auto enc_values = calc.encrypt(values);
        auto enc_sum = calc.sum_all_slots(enc_values);

        // Dividir por 4 (número de valores)
        std::vector<double> inv_n = {0.25, 0.25, 0.25, 0.25};
        auto enc_avg = calc.multiply_plain(enc_sum, inv_n);

        auto avg_result = calc.decrypt(enc_avg);
        std::cout << "Media: " << avg_result[0] << "\n";
        // Resultado deve ser aproximadamente 25.0

    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << "\n";
    }

    return 0;
}
```

### 10.6.5 Erro de Precisão

CKKS é um esquema **aproximado**. O erro de precisão depende de:

1. **Escala inicial**: maior escala = menor erro relativo
2. **Profundidade do circuito**: cada operação acumula erro
3. **Modulus chain length**: mais níveis = mais operações antes de falhar

```cpp
// Medir erro de precisão em CKKS
void measure_precision_error() {
    CKKSCalculator calc;

    double valor_original = 3.141592653589793;
    std::vector<double> x = {valor_original};

    auto enc_x = calc.encrypt(x);

    // Múltiplas multiplicações para observar degradação
    Ciphertext current = enc_x;
    for (int i = 0; i < 5; ++i) {
        current = calc.multiply(current, enc_x);
    }

    auto result = calc.decrypt(current);
    double valor_aproximado = result[0];
    double erro_relativo = std::abs(valor_aproximado - valor_original)
                         / std::abs(valor_original);

    std::cout << "Original:     " << valor_original << "\n";
    std::cout << "Aproximado:   " << valor_aproximado << "\n";
    std::cout << "Erro relativo: " << erro_relativo << "\n";
    // Erro típico: < 1e-6 para operações simples
}
```

### 10.6.6 Comparações com Ponto Flutuante IEEE 754

| Aspecto | IEEE 754 (hardware) | CKKS |
|---------|--------------------|----|
| Precisão | 23-52 bits (single/double) | ~40 bits (configurável) |
| Operações | Hardware (muito rápido) | Criptografadas (lento) |
| Underflow/Overflow | Sim | Não (operações modulares) |
| Denormal numbers | Sim | Não |
| NaN/Inf | Sim | Não |
| Parallelismo | SIMD nativo | Packing em slots |

---

## 10.7 TFHE: Portas Booleanas sobre Ciphertexts

### 10.7.1 Fundamentos do TFHE

TFHE (Torus FHE) é uma biblioteca de criptografia homomórfica baseada em LWE sobre o torus `T = R_q/Z`. Diferente de SEAL (que opera sobre polinômios), TFHE trabalha com **bits individuais** através de portas booleanas.

**Vantagens do modelo booleano:**
- Qualquer computação pode ser expressa como circuitos booleanos
- Bootstrapping eficiente (~10ms por gate em hardware moderno)
- Precisão exata (sem erros de aproximação)
- Fácil de compilar de qualquer linguagem para circuitos booleanos

### 10.7.2 Estrutura do Ciphertext TFHE

Em TFHE, um ciphertext consiste em:
- `a`: polinômio de coeficientes (componente público)
- `b`: valor escalar (componente público)
- `p`: plaintext bit (0 ou 1)
- `noise`: ruído aleatório pequeno

A relação é: `b ≈ a·s + noise + p/2 (mod q)`

onde `s` é a chave secreta.

### 10.7.3 Portas Booleanas Básicas

```cpp
// TFHE API simplificada (conceitual)
// Na prática, use a biblioteca tfhe++

#include <tfhe/tfhe.h>
#include <tfhe/tfhe_io.h>

void demonstrate_tfhe_gates() {
    // Setup de parâmetros
    TFheGateBootstrappingParameterSet* params =
        new_default_gate_bootstrapping_parameters(128);

    // Gerar chaves
    TFheGateBootstrappingSecretKeySet* keys =
        new_random_gate_bootstrapping_keyset(params);

    // Criptografar bits
    uint8_t a = 1;
    uint8_t b = 0;

    LweSample* enc_a = new_gate_bootstrapping_ciphertext_array(8, params);
    LweSample* enc_b = new_gate_bootstrapping_ciphertext_array(8, params);

    // Encriptar cada bit individualmente
    for (int i = 0; i < 8; ++i) {
        tfheBootstrapEncryptKeyBit(
            enc_a[i], keys->cloud,
            (a >> i) & 1
        );
        tfheBootstrapEncryptKeyBit(
            enc_b[i], keys->cloud,
            (b >> i) & 1
        );
    }

    // AND gate
    LweSample* enc_and = new_gate_bootstrapping_ciphertext_array(8, params);
    for (int i = 0; i < 8; ++i) {
        tfheGateAND(enc_and[i], enc_a[i], enc_b[i], keys->cloud);
    }

    // Decriptar resultado
    uint8_t result_and = 0;
    for (int i = 0; i < 8; ++i) {
        uint8_t bit = tfheGateBootstrappingSchemeBitDecript(
            enc_and[i], keys->secret
        );
        result_and |= (bit << i);
    }

    std::cout << "AND(" << (int)a << ", " << (int)b
              << ") = " << (int)result_and << "\n";

    // Limpeza
    delete_gate_bootstrapping_ciphertext_array(8, enc_a);
    delete_gate_bootstrapping_ciphertext_array(8, enc_b);
    delete_gate_bootstrapping_ciphertext_array(8, enc_and);
    delete_gate_bootstrapping_keyset(keys);
    delete_gate_bootstrapping_parameters(params);
}
```

### 10.7.4 Implementação Completa com tfhe++

A biblioteca `tfhe++` é uma implementação moderna de TFHE em C++17:

```cpp
// tfhe++ é uma implementação moderna de TFHE
// GitHub: https://github.com/tuneinsight/lattigo

// Estrutura conceitual de uso:
// 1. Gerar parâmetros
// 2. Gerar chaves
// 3. Encriptar bits
// 4. Aplicar portas booleanas
// 5. Decriptar bits

// Circuitos booleanos complexos são compostos de portas básicas:
// - AND, OR, XOR, NOT, NAND, NOR
// Cada porta inclui bootstrapping para manter o ruído controlado
```

### 10.7.5 Circuito Booleano Completo

```cpp
// Construindo um somador completo encriptado
// Um somador completo soma 3 bits: a, b, carry_in
// Resultado: sum (XOR), carry_out (MAJORITY)

class EncryptedFullAdder {
public:
    EncryptedFullAdder(const TFheGateBootstrappingCloudKeySet* cloud_key)
        : cloud_key_(cloud_key) {}

    // XOR de dois bits encriptados
    void xor_gate(LweSample* result,
                  const LweSample* a,
                  const LweSample* b) {
        // XOR = AND(OR(a,b), NAND(a,b))
        LweSample* temp_or = new_gate_bootstrapping_ciphertext(params());
        LweSample* temp_nand = new_gate_bootstrapping_ciphertext(params());

        tfheGateOR(temp_or, a, b, cloud_key_);
        tfheGateNAND(temp_nand, a, b, cloud_key_);
        tfheGateAND(result, temp_or, temp_nand, cloud_key_);

        delete_gate_bootstrapping_ciphertext(temp_or);
        delete_gate_bootstrapping_ciphertext(temp_nand);
    }

    // Majority gate (carry_out)
    void majority_gate(LweSample* result,
                       const LweSample* a,
                       const LweSample* b,
                       const LweSample* c) {
        // Majority(a,b,c) = OR(AND(a,b), OR(AND(a,c), AND(b,c)))
        LweSample* ab = new_gate_bootstrapping_ciphertext(params());
        LweSample* ac = new_gate_bootstrapping_ciphertext(params());
        LweSample* bc = new_gate_bootstrapping_ciphertext(params());
        LweSample* ac_or_bc = new_gate_bootstrapping_ciphertext(params());

        tfheGateAND(ab, a, b, cloud_key_);
        tfheGateAND(ac, a, c, cloud_key_);
        tfheGateAND(bc, b, c, cloud_key_);
        tfheGateOR(ac_or_bc, ac, bc, cloud_key_);
        tfheGateOR(result, ab, ac_or_bc, cloud_key_);

        delete_gate_bootstrapping_ciphertext(ab);
        delete_gate_bootstrapping_ciphertext(ac);
        delete_gate_bootstrapping_ciphertext(bc);
        delete_gate_bootstrapping_ciphertext(ac_or_bc);
    }

    // Somador completo: retorna sum e carry_out
    void full_add(LweSample* sum,
                  LweSample* carry_out,
                  const LweSample* a,
                  const LweSample* b,
                  const LweSample* carry_in) {
        LweSample* a_xor_b = new_gate_bootstrapping_ciphertext(params());
        LweSample* a_and_b = new_gate_bootstrapping_ciphertext(params());
        LweSample* a_xor_b_and_cin = new_gate_bootstrapping_ciphertext(params());

        // sum = a XOR b XOR carry_in
        xor_gate(a_xor_b, a, b);
        xor_gate(sum, a_xor_b, carry_in);

        // carry_out = majority(a, b, carry_in)
        majority_gate(carry_out, a, b, carry_in);

        delete_gate_bootstrapping_ciphertext(a_xor_b);
        delete_gate_bootstrapping_ciphertext(a_and_b);
        delete_gate_bootstrapping_ciphertext(a_xor_b_and_cin);
    }

    // Somador de N bits
    std::vector<LweSample*> add_n_bits(
        const std::vector<LweSample*>& a,
        const std::vector<LweSample*>& b) {
        size_t n = a.size();
        std::vector<LweSample*> sum(n);
        LweSample* carry = new_gate_bootstrapping_ciphertext(params());

        // Inicializar carry como 0
        tfheGateConstantZero(carry, cloud_key_);

        // Somar bit a bit
        for (size_t i = 0; i < n; ++i) {
            sum[i] = new_gate_bootstrapping_ciphertext(params());
            LweSample* new_carry =
                new_gate_bootstrapping_ciphertext(params());

            full_add(sum[i], new_carry, a[i], b[i], carry);

            delete_gate_bootstrapping_ciphertext(carry);
            carry = new_carry;
        }

        return sum;
    }

private:
    const TFheGateBootstrappingCloudKeySet* cloud_key_;

    const TFheGateBootstrappingParameterSet* params() const {
        return cloud_key_->params;
    }
};
```

### 10.7.6 Comparação: TFHE vs CKKS para Computação

| Aspecto | TFHE | CKKS |
|---------|------|------|
| Unidade de compute | Bit | Slot (vetor de reais) |
| Granularidade | Booleana | Numérica |
| Bootstrapping | Obrigatório por gate | Opcional (rescale) |
| Precisão | Exata | Aproximada |
| Performance por operação | Lenta (10ms/gate) | Rápida (μs/operação) |
| Circuitos complexos | Naturais | Necessita decomposição |
| Uso típico | Lógica, comparações | ML, análise de dados |

---

## 10.8 Características de Performance e Gerenciamento de Ruído

### 10.8.1 O Ciclo de Vida do Ruído

Em esquemas baseados em LWE, o ruído é intrínseco ao processo de encriptação e cresce com cada operação:

```
Fase 1: Encriptação
  CT(m, 0)  →  CT(m, e)  onde e é pequeno

Fase 2: Operações
  CT(m₁, e₁) + CT(m₂, e₂) → CT(m₁+m₂, e₁+e₂)
  CT(m₁, e₁) × CT(m₂, e₂) → CT(m₁×m₂, e₁·e₂ + m₁·e₂ + m₂·e₁)

Fase 3: Limite
  Quando |noise| > q/2t, a decriptação falha
```

### 10.8.2 Técnicas de Controle de Ruído

**Modulus Switching (BGV/BFV):**
Reduz o tamanho do ciphertext divide o ruído proporcionalmente:

```
Antes: CT(m, e) módulo q
Depois: CT(m, e·(q'/q)) módulo q' onde q' < q
```

**Relinearization (BFV):**
Após multiplicação, o ciphertext cresce. A relinearização o comprime de volta:

```
Antes: CT = (c₀, c₁, c₂)  // grau 2
Relin: CT' = (c₀', c₁')    // grau 1
```

**Rescaling (CKKS):**
Reduz a escala e desce no modulus chain:

```
scale: 2^40 → 2^0 (após rescale)
level: L → L-1
```

**Bootstrapping (FHE):**
Renova completamente o ciphertext, resetando o ruído:

```
CT(m, noise_grande) → CT(m, noise_pequeno)
Custo: ~10ms (TFHE) a ~1s (BFV/CKKS)
```

### 10.8.3 Custos Operacionais

**Benchmark típico em Intel i7-12700K (2023):**

| Operação | BFV (4096) | BFV (8192) | CKKS (8192) |
|----------|-----------|-----------|-------------|
| KeyGen   | 50 ms     | 200 ms    | 180 ms      |
| Encrypt  | 0.1 ms    | 0.5 ms    | 0.4 ms      |
| Decrypt  | 0.05 ms   | 0.3 ms    | 0.2 ms      |
| Add      | 0.001 ms  | 0.005 ms  | 0.004 ms    |
| Multiply | 0.05 ms   | 0.3 ms    | 0.25 ms     |
| Reline   | 0.05 ms   | 0.3 ms    | 0.25 ms     |
| Rescale  | —         | —         | 0.1 ms      |
| Rotate   | —         | —         | 0.3 ms      |
| **Total add** | 0.15 ms | 1.0 ms | 0.8 ms |
| **Total mul** | 0.25 ms | 1.8 ms | 1.5 ms |

**Benchmark com GPU (NVIDIA A100):**

| Operação | BFV (4096) | CKKS (8192) |
|----------|-----------|-------------|
| KeyGen   | 5 ms      | 4 ms        |
| Encrypt  | 0.01 ms   | 0.008 ms    |
| Add      | 0.0001 ms | 0.0001 ms   |
| Multiply | 0.005 ms  | 0.004 ms    |

**Análise de Escala:**

```
Para processar 1M de registros:

BFV (4096, 1M somas):
  Tempo: ~150s (sequencial) / ~20s (8 threads)
  Memória: ~500 MB

CKKS (8192, 1M × 4 slots = 4M valores):
  Tempo: ~50s (sequencial) / ~8s (8 threads)
  Memória: ~2 GB

Versão em texto plano (reference):
  Tempo: ~0.01s
  Fator de overhead: 5,000x a 50,000x
```

### 10.8.4 Otimização de Performance

**1. Paralelismo de Dados (Packing):**
```
Em vez de encriptar N valores individualmente:
  N encriptações × 1 slot = N ciphertexts

Use 1 encriptação × N slots:
  1 ciphertext com N slots = N valores simultâneos
```

**2. NTT (Number Theoretic Transform):**
O SEAL usa NTT internamente para multiplicação eficiente de polinômios:

```cpp
// O SEAL otimiza automaticamente com NTT
// Mas você pode influenciar escolhendo poly_modulus_degree
// que é uma potência de 2 para NTT eficiente

// Bons valores: 1024, 2048, 4096, 8192, 16384
```

**3. Batchamento (BGV/BFV):**
```cpp
// Em vez de processar 1 valor por ciphertext,
// batche N valores em 1 ciphertext

// BGV/BV: Use o BatchEncoder para operações SIMD
BatchEncoder encoder(context);
std::vector<uint64_t> batch = {1, 2, 3, 4, 5, 6, 7, 8};
Plaintext plain;
encoder.encode(batch, plain);

// Agora 8 valores são processados simultaneamente
```

**4. Multithreading:**
```cpp
// SEAL suporta paralelismo via OpenMP
// Defina OMP_NUM_THREADS antes de executar
export OMP_NUM_THREADS=8

// Ou no código:
#include <omp.h>

#pragma omp parallel for
for (size_t i = 0; i < n; ++i) {
    // Operações independentes em ciphertexts diferentes
}
```

### 10.8.5 Consumo de Memória

```
Tamanho de um ciphertext BFV (poly_modulus_degree = 4096):
  2 polinômios × 4096 coeficientes × 8 bytes = 64 KB
  + metadados ≈ 65 KB por ciphertext

Para CKKS (8192, 4 níveis):
  2 polinômios × 8192 × 8 bytes × 4 níveis = 512 KB
  + metadados ≈ 520 KB por ciphertext

Chaves:
  Secret key:  ~65 KB (BFV-4096)
  Public key:   ~260 KB
  Relin keys:  ~260 KB
  Galois keys: ~2.6 MB
```

---

## 10.9 Casos de Uso

### 10.9.1 Machine Learning Privativo

Um dos casos de uso mais promissores é treinar e inferir modelos de ML sobre dados sensíveis sem expô-los:

```cpp
// Inferência de regressão linear encriptada
// Modelo: y = w₀ + w₁·x₁ + w₂·x₂
// Os pesos w são públicos, os dados x são privados

class EncryptedLinearRegression {
public:
    EncryptedLinearRegression(const CKKSEncoder& encoder,
                              const Evaluator& evaluator,
                              const Encryptor& encryptor,
                              const Decryptor& decryptor,
                              double scale)
        : encoder_(encoder), evaluator_(evaluator),
          encryptor_(encryptor), decryptor_(decryptor),
          scale_(scale) {}

    // Treinar modelo (em texto plano — treinamento é offline)
    void train(const std::vector<std::vector<double>>& X,
               const std::vector<double>& y) {
        // Usar qualquer método de treinamento (OLS, gradient descent)
        // Aqui simplificado com média ponderada
        size_t n_features = X[0].size();
        weights_.resize(n_features + 1, 0.0);

        // Treinamento simplificado
        for (size_t i = 0; i < X.size(); ++i) {
            weights_[0] += y[i];
            for (size_t j = 0; j < n_features; ++j) {
                weights_[j + 1] += X[i][j] * y[i];
            }
        }

        for (auto& w : weights_) {
            w /= X.size();
        }
    }

    // Inferência sobre dados encriptados
    Ciphertext predict_encrypted(const Ciphertext& enc_features) {
        // y = w₀ + w₁·x₁ + w₂·x₂
        // Em CKKS: features são um vetor [x₁, x₂, ...]

        // Adicionar bias (w₀) a cada slot
        std::vector<double> bias(weights_.size(), weights_[0]);
        Ciphertext result = evaluator_.add_plain(enc_features,
            CKKSEncoder::encode(bias, scale_));

        // Multiplicar por pesos
        Ciphertext weighted = evaluator_.multiply_plain(
            enc_features,
            CKKSEncoder::encode(
                std::vector<double>(weights_.begin() + 1, weights_.end()),
                scale_
            )
        );

        // Soma para produto escalar
        Ciphertext prediction = sum_slots(weighted);

        return evaluator_.add(prediction, result);
    }

private:
    std::vector<double> weights_;
    const CKKSEncoder& encoder_;
    const Evaluator& evaluator_;
    const Encryptor& encryptor_;
    const Decryptor& decryptor_;
    double scale_;
};
```

### 10.9.2 Computação Segura em Saúde

```cpp
// Exemplo: cálculo de estatísticas de saúde encriptadas
// Hospital encripta dados, servidor computa médias e correlações

class EncryptedHealthStats {
public:
    // Dados: vetor de idades, vetor de pressão arterial, etc.
    // Todos encriptados no mesmo ciphertext (packing)

    Ciphertext compute_encrypted_mean(
        const std::vector<Ciphertext>& patient_data,
        const Evaluator& evaluator) {
        // Somar todos os dados
        Ciphertext sum = patient_data[0];
        for (size_t i = 1; i < patient_data.size(); ++i) {
            evaluator.add_inplace(sum, patient_data[i]);
        }

        // Dividir por N (pré-computar N⁻¹)
        // Para CKKS, multiply_plain com escalar
        return sum;
    }

    // Correlação entre duas variáveis encriptadas
    // corr(X, Y) = E[(X-μx)(Y-μy)] / (σx · σy)
    Ciphertext compute_encrypted_correlation(
        const Ciphertext& enc_x,
        const Ciphertext& enc_y,
        const Evaluator& evaluator) {
        // Centrar dados
        // corr = E[XY] - E[X]·E[Y]

        // E[XY]
        auto enc_xy = evaluator.multiply(enc_x, enc_y);
        // ... rescaling, relinearization ...

        return enc_xy;  // Simplificado
    }

    // Rank sum test encriptado (non-parametric)
    // Compara distribuições sem revelar valores individuais
};
```

### 10.9.3 Votação Eletrônica

```cpp
// Sistema de votação encriptado
// Cada eleitor encripta seu voto (1 para candidato A, 0 para B)
// Servidor computa total sem ver votos individuais

class EncryptedVoting {
public:
    EncryptedVoting(size_t num_candidates) {
        EncryptionParameters params(scheme_type::bfv);
        params.set_poly_modulus_degree(4096);
        params.set_coeff_modulus(CoeffModulus::BFVDefault(4096));
        params.set_plain_modulus(1024);

        context_ = std::make_unique<SEALContext>(params);

        KeyGenerator keygen(*context_);
        public_key_ = std::make_unique<PublicKey>();
        keygen.create_public_key(*public_key_);

        secret_key_ = keygen.secret_key();
        keygen.create_relin_keys(relin_keys_);
    }

    // Eleitor: encriptar voto
    Ciphertext cast_vote(size_t candidate_id) {
        Encryptor encryptor(*context_, *public_key_);

        // Voto representado como valor inteiro
        Plaintext vote(std::to_string(candidate_id));

        Ciphertext encrypted;
        encryptor.encrypt(vote, encrypted);
        return encrypted;
    }

    // Servidor: computar resultado (sem ver votos!)
    std::map<size_t, int> tally_votes(
        const std::vector<Ciphertext>& encrypted_votes) {
        // Na prática, isso requer circuitos mais complexos
        // para contar votos por candidato
        // Aqui simplificado como soma total
        Evaluator evaluator(*context_);

        Ciphertext total = encrypted_votes[0];
        for (size_t i = 1; i < encrypted_votes.size(); ++i) {
            evaluator.add_inplace(total, encrypted_votes[i]);
        }

        // Retornar total (decriptado pelo cliente)
        return {};  // Placeholder
    }

private:
    std::unique_ptr<SEALContext> context_;
    std::unique_ptr<PublicKey> public_key_;
    SecretKey secret_key_;
    RelinKeys relin_keys_;
};
```

### 10.9.4 Análise de Dados Financeiros

```cpp
// Cálculo de VaR (Value at Risk) encriptado
// Bancos podem compartilhar dados encriptados para
// calcular risco sistêmico sem expor posições individuais

class EncryptedVaR {
public:
    // Simular portfólio encriptado e calcular retorno esperado
    std::vector<Ciphertext> compute_portfolio_returns(
        const std::vector<Ciphertext>& enc_weights,
        const std::vector<Ciphertext>& enc_returns) {
        // Portfolio return = sum(w_i * r_i)
        CKKSEncoder encoder(context_);
        Evaluator evaluator(context_);

        std::vector<Ciphertext> results;

        // Para cada cenário de retorno
        for (size_t scenario = 0; scenario < enc_returns.size(); ++scenario) {
            // w · r para este cenário
            auto enc_product = evaluator.multiply(
                enc_weights[scenario], enc_returns[scenario]
            );

            // Somar para todos os ativos
            Ciphertext total = enc_product;
            for (size_t asset = 1; asset < enc_weights.size(); ++asset) {
                auto weighted = evaluator.multiply(
                    enc_weights[asset], enc_returns[scenario]
                );
                evaluator.add_inplace(total, weighted);
            }

            results.push_back(total);
        }

        return results;
    }

private:
    const SEALContext& context_;
};
```

---

## 10.10 Limitações e Bootstrapping

### 10.10.1 Limitações Fundamentais

**1. Overhead de Performance:**
```
FHE overhead vs texto plano: 10,000x a 1,000,000x
Exemplo: multiplicação de 1000 inteiros
  - Texto plano: ~0.001 ms
  - FHE (BFV-4096): ~50 ms (50,000x mais lento)
```

**2. Consumo de Memória:**
```
Um ciphertext ocupa 64 KB a 2 MB dependendo dos parâmetros
Para 1M registros: 64 GB a 2 TB de memória
```

**3. Complexidade de Implementação:**
```
- Gerenciamento de parâmetros é complexo
- Erros de configuração causam falhas silenciosas
- Testes requerem verificação de precisão
```

**4. Latência:**
```
Bootstrapping (renovação de ciphertext):
  - BFV/BGV: ~100-1000 ms
  - CKKS: ~50-200 ms
  - TFHE: ~10 ms por gate
```

### 10.10.2 O Problema do Bootstrapping

O bootstrapping é o mecanismo que transforma SHE em FHE, mas introduz custos significativos:

```
┌─────────────────────────────────────────────────┐
│              Bootstrapping Process              │
├─────────────────────────────────────────────────┤
│                                                 │
│  Entrada: CT(m, noise_grande)                   │
│                                                 │
│  1. Encriptar chave secreta sk sob pk           │
│     EK = E(pk, sk)                             │
│                                                 │
│  2. Avaliar circuito de decriptação             │
│     CT_novo = HomDec(CT_velho, EK)             │
│     - Circuit: operações sobre CTs              │
│     - Usa relin keys internamente              │
│                                                 │
│  3. Resultado: CT(m, noise_pequeno)             │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Custos do Bootstrapping:**

| Parâmetro | Valor Típico | Efeito |
|-----------|-------------|--------|
| Tempo     | 10-1000 ms  | Gargalo principal |
| Memória   | 50-500 MB   | Para EK e intermediários |
| Parâmetros | Mais altos | Segurança e profundidade |

### 10.10.3 Estratégias de Mitigação

**1. Circuitos Otimizados:**
```cpp
// Em vez de bootstrapping frequentemente,
// otimize o circuito para minimizar profundidade

// RUIM: multiplicações encadeadas sem relinearização
// a * b * c * d → 3 multiplicações, profundidade 3

// BOM: agrupar multiplicações com relinearização
// (a * b) * (c * d) → 2 multiplicações paralelas, profundidade 2
```

**2. Aproveitamento de Dados:**
```cpp
// CKKS: packing de múltiplos valores em 1 ciphertext
// 8192 slots × 1 ciphertext = processar 8192 valores simultaneamente

// Reduz overhead em 8192x para operações SIMD
```

**3. Híbrido FHE + Texto Plano:**
```cpp
// Usar FHE apenas onde a privacidade é crítica
// Manter dados não-sensíveis em texto plano
class HybridProcessor {
    Ciphertext process_sensitive(const Ciphertext& data) {
        // Operações FHE para dados sensíveis
        return evaluator_.multiply(data, weights_);
    }

    double process_public(double data) {
        // Operações normais para dados públicos
        return data * 3.14;
    }
};
```

**4. Batchamento e Assincronismo:**
```cpp
// Processar múltiplas solicitações em lote
// Reduz overhead de KeyGen e bootstrapping

std::vector<Ciphertext> batch_process(
    const std::vector<Ciphertext>& inputs) {
    // Processar em lotes para amortizar custos fixos
    // ...
}
```

### 10.10.4 Limitações Atuais (2024)

| Aspecto | Estado | Perspectiva |
|---------|--------|-------------|
| Performance | 10K-1Mx overhead | Hardware dedicado pode reduzir para 100-1000x |
| Memória | Gbytes para 1M registros | Compressão e streaming |
| Bootstrapping | 10-1000ms | Otimizações contínuas |
| Usabilidade | Complexa | SDKs e ferramentas de alto nível |
| Padrões | Em formação | HomomorphicEncryption.org |
| Adoção | Pilotos em empresas grandes | Crescimento com maturidade |

---

## 10.11 Exemplo Completo: Interseção Privativa de Conjuntos

### 10.11.1 Definição do Problema

Dois conjuntos `A` e `A` são mantidos por duas partes (Alice e Bob). O protocolo de interseção privativa de conjuntos (PSI) permite que ambas as partes computem `A ∩ B` sem revelar elementos que não estão na interseção.

**Aplicações:**
- Deduplicação de dados entre empresas
- Publicidade digital (matching de audiência)
- Detecção de fraude (sem compartilhar clientes)
- Genômica (encontrar variantes compartilhadas)

### 10.11.2 Protocolo com Criptografia Homomórfica

```
┌─────────────┐                           ┌─────────────┐
│    Alice     │                           │     Bob     │
│  Conjunto A  │                           │  Conjunto B │
│  {1, 3, 5}  │                           │  {2, 3, 4}  │
└──────┬───────┘                           └──────┬──────┘
       │                                          │
       │  1. Gerar chaves FHE                     │
       │  pk, sk                                  │
       │                                          │
       │  2. Encriptar elementos de A              │
       │  E(1), E(3), E(5) ─────────────────────►│
       │                                          │
       │  3. Para cada b ∈ B:                     │
       │     Para cada E(a) ∈ A:                  │
       │       Computar E(b - a)                  │
       │       Avaliar se b == a                  │
       │                                          │
       │  4. Retornar elemento de interseção       │
       │◄─────────────────────────────────────────│
       │  (apenas elementos em comum)             │
```

### 10.11.3 Implementação Completa em C++17

```cpp
#include "seal/seal.h"
#include <iostream>
#include <vector>
#include <set>
#include <unordered_set>
#include <algorithm>
#include <cmath>
#include <chrono>

using namespace seal;

class PrivateSetIntersection {
public:
    PrivateSetIntersection() {
        // Configurar CKKS para operações aproximadas
        EncryptionParameters params(scheme_type::ckks);
        params.set_poly_modulus_degree(8192);
        params.set_coeff_modulus(CoeffModulus::CKKS(
            8192, {60, 40, 40, 60}
        ));

        context_ = std::make_unique<SEALContext>(params);
        encoder_ = std::make_unique<CKKSEncoder>(*context_);

        // Gerar chaves
        KeyGenerator keygen(*context_);
        secret_key_ = keygen.secret_key();

        PublicKey public_key;
        keygen.create_public_key(public_key);

        keygen.create_relin_keys(relin_keys_);
        keygen.create_galois_keys(galois_keys_);

        encryptor_ = std::make_unique<Encryptor>(*context_, public_key);
        evaluator_ = std::make_unique<Evaluator>(*context_);
        decryptor_ = std::make_unique<Decryptor>(*context_, secret_key_);

        scale_ = pow(2.0, 40);
    }

    // Fase 1: Alice encripta seus elementos
    std::vector<Ciphertext> encrypt_set(
        const std::vector<double>& set_elements) {
        std::vector<Ciphertext> encrypted_elements;
        encrypted_elements.reserve(set_elements.size());

        for (double elem : set_elements) {
            std::vector<double> single_value = {elem};
            Plaintext plain;
            encoder_->encode(single_value, scale_, plain);

            Ciphertext encrypted;
            encryptor_->encrypt(plain, encrypted);
            encrypted_elements.push_back(std::move(encrypted));
        }

        std::cout << "[Alice] " << set_elements.size()
                  << " elementos encriptados.\n";
        return encrypted_elements;
    }

    // Fase 2: Bob computa interseção
    // Para cada elemento b em B, verifica se existe em A
    std::vector<double> compute_intersection(
        const std::vector<Ciphertext>& encrypted_A,
        const std::vector<double>& B) {
        std::vector<double> intersection;

        // Para cada elemento de Bob
        for (double b : B) {
            bool found = false;

            // Comparar com cada elemento encriptado de Alice
            for (const auto& enc_a : encrypted_A) {
                // Calcular (b - a) homomorficamente
                // Se b == a, resultado ≈ 0

                // Criptografar b
                std::vector<double> b_vec = {b};
                Plaintext plain_b;
                encoder_->encode(b_vec, scale_, plain_b);

                Ciphertext enc_b;
                encryptor_->encrypt(plain_b, enc_b);

                // Diferença encriptada: E(b) - E(a) = E(b - a)
                Ciphertext diff;
                evaluator_->sub(enc_b, enc_a, diff);

                // Verificar se resultado é próximo de 0
                Plaintext plain_diff;
                decryptor_->decrypt(diff, plain_diff);

                std::vector<double> diff_values;
                encoder_->decode(plain_diff, diff_values);

                if (std::abs(diff_values[0]) < 0.1) {
                    // b está na interseção
                    intersection.push_back(b);
                    found = true;
                    break;
                }
            }
        }

        return intersection;
    }

    // Versão otimizada: usar batchamento para verificar múltiplos
    // elementos simultaneamente
    std::vector<double> compute_intersection_batch(
        const std::vector<double>& A,
        const std::vector<double>& B) {
        std::vector<double> intersection;

        size_t slot_count = encoder_->slot_count();
        size_t batch_size = std::min(slot_count, A.size());

        // Processar A em lotes
        for (size_t i = 0; i < A.size(); i += batch_size) {
            size_t current_batch = std::min(batch_size, A.size() - i);

            // Criar plaintext com vários elementos de A
            std::vector<double> batch_a(slot_count, 0.0);
            for (size_t j = 0; j < current_batch; ++j) {
                batch_a[j] = A[i + j];
            }

            Plaintext plain_a;
            encoder_->encode(batch_a, scale_, plain_a);

            Ciphertext enc_a;
            encryptor_->encrypt(plain_a, enc_a);

            // Para cada elemento de B
            for (double b : B) {
                std::vector<double> b_vec(slot_count, b);
                Plaintext plain_b;
                encoder_->encode(b_vec, scale_, plain_b);

                Ciphertext enc_b;
                encryptor_->encrypt(plain_b, enc_b);

                // Diferença
                Ciphertext diff;
                evaluator_->sub(enc_b, enc_a, diff);

                // Relinearizar e rescale
                evaluator_->relinearize_inplace(diff, relin_keys_);
                evaluator_->rescale_to_next_inplace(diff, scale_);

                // Decriptar para verificar (apenas para verificação)
                Plaintext plain_diff;
                decryptor_->decrypt(diff, plain_diff);

                std::vector<double> diff_values;
                encoder_->decode(plain_diff, diff_values);

                // Verificar se algum slot é próximo de 0
                for (size_t j = 0; j < current_batch; ++j) {
                    if (std::abs(diff_values[j]) < 0.1) {
                        intersection.push_back(b);
                        break;
                    }
                }
            }
        }

        return intersection;
    }

private:
    std::unique_ptr<SEALContext> context_;
    std::unique_ptr<CKKSEncoder> encoder_;
    SecretKey secret_key_;
    RelinKeys relin_keys_;
    GaloisKeys galois_keys_;
    std::unique_ptr<Encryptor> encryptor_;
    std::unique_ptr<Evaluator> evaluator_;
    std::unique_ptr<Decryptor> decryptor_;
    double scale_;
};

int main() {
    try {
        auto start_time = std::chrono::high_resolution_clock::now();

        // Criar instância do PSI
        PrivateSetIntersection psi;

        // Conjuntos de teste
        std::vector<double> set_A = {1.0, 3.0, 5.0, 7.0, 9.0};
        std::vector<double> set_B = {2.0, 3.0, 4.0, 7.0, 8.0};

        std::cout << "Conjunto A: {";
        for (size_t i = 0; i < set_A.size(); ++i) {
            std::cout << set_A[i];
            if (i < set_A.size() - 1) std::cout << ", ";
        }
        std::cout << "}\n";

        std::cout << "Conjunto B: {";
        for (size_t i = 0; i < set_B.size(); ++i) {
            std::cout << set_B[i];
            if (i < set_B.size() - 1) std::cout << ", ";
        }
        std::cout << "}\n";

        // Executar PSI
        std::cout << "\n--- Executando PSI ---\n";

        // Alice encripta
        auto enc_A = psi.encrypt_set(set_A);

        // Bob computa interseção
        auto intersection = psi.compute_intersection(enc_A, set_B);

        // Resultado
        std::cout << "\nIntersecao encontrada: {";
        for (size_t i = 0; i < intersection.size(); ++i) {
            std::cout << intersection[i];
            if (i < intersection.size() - 1) std::cout << ", ";
        }
        std::cout << "}\n";

        // Verificar com interseção em texto plano
        std::set<double> plaintext_A(set_A.begin(), set_A.end());
        std::set<double> plaintext_B(set_B.begin(), set_B.end());
        std::vector<double> expected_intersection;
        std::set_intersection(
            plaintext_A.begin(), plaintext_A.end(),
            plaintext_B.begin(), plaintext_B.end(),
            std::back_inserter(expected_intersection)
        );

        std::cout << "Intersecao esperada: {";
        for (size_t i = 0; i < expected_intersection.size(); ++i) {
            std::cout << expected_intersection[i];
            if (i < expected_intersection.size() - 1)
                std::cout << ", ";
        }
        std::cout << "}\n";

        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
            end_time - start_time
        ).count();

        std::cout << "\nTempo total: " << duration << " ms\n";

        // Verificar correção
        bool correto = (intersection == expected_intersection);
        std::cout << "Resultado correto: "
                  << (correto ? "SIM" : "NAO") << "\n";

    } catch (const std::exception& e) {
        std::cerr << "Erro: " << e.what() << "\n";
        return 1;
    }

    return 0;
}
```

### 10.11.4 Versão Avançada: PSI com BFV

```cpp
// PSI usando BFV (inteiros exatos)
// Mais eficiente para dados discretos

class BFVPrivateSetIntersection {
public:
    BFVPrivateSetIntersection() {
        EncryptionParameters params(scheme_type::bfv);
        params.set_poly_modulus_degree(8192);
        params.set_coeff_modulus(CoeffModulus::BFVDefault(8192));
        params.set_plain_modulus(1024);

        context_ = std::make_unique<SEALContext>(params);

        KeyGenerator keygen(*context_);
        secret_key_ = keygen.secret_key();

        PublicKey public_key;
        keygen.create_public_key(public_key);

        keygen.create_relin_keys(relin_keys_);

        encryptor_ = std::make_unique<Encryptor>(*context_, public_key);
        evaluator_ = std::make_unique<Evaluator>(*context_);
        decryptor_ = std::make_unique<Decryptor>(*context_, secret_key_);
    }

    // Batch encoding: múltiplos inteiros em 1 plaintext
    Ciphertext encrypt_batch(const std::vector<uint64_t>& values) {
        BatchEncoder encoder(*context_);

        // Pad para slot count
        size_t slot_count = encoder.slot_count();
        std::vector<uint64_t> padded(slot_count, 0);
        for (size_t i = 0; i < std::min(values.size(), slot_count); ++i) {
            padded[i] = values[i] % 1024;  // mod plain_modulus
        }

        Plaintext plain;
        encoder.encode(padded, plain);

        Ciphertext encrypted;
        encryptor_->encrypt(plain, encrypted);
        return encrypted;
    }

    // Verificar interseção usando batch
    std::vector<uint64_t> find_intersection_batch(
        const std::vector<uint64_t>& A,
        const std::vector<uint64_t>& B) {
        std::vector<uint64_t> intersection;

        BatchEncoder encoder(*context_);
        size_t slot_count = encoder.slot_count();

        // Processar A em lotes
        for (size_t i = 0; i < A.size(); i += slot_count) {
            size_t batch_size = std::min(slot_count, A.size() - i);

            // Batch de A
            std::vector<uint64_t> batch_a(slot_count, 0);
            for (size_t j = 0; j < batch_size; ++j) {
                batch_a[j] = A[i + j];
            }

            auto enc_batch = encrypt_batch(batch_a);

            // Para cada elemento de B, verificar se existe
            for (uint64_t b : B) {
                // Criptografar b como plaintext constante
                std::vector<uint64_t> b_vec(slot_count, b);
                Plaintext plain_b;
                encoder.encode(b_vec, plain_b);

                // Diferença: E(batch_a) - E(b_vec)
                Ciphertext diff;
                evaluator_->sub_plain(enc_batch, plain_b, diff);

                // Relinearizar
                evaluator_->relinearize_inplace(diff, relin_keys_);

                // Decriptar para verificar
                Plaintext plain_diff;
                decryptor_->decrypt(diff, plain_diff);

                std::vector<uint64_t> diff_values;
                encoder.decode(plain_diff, diff_values);

                // Se algum slot é 0, há match
                for (size_t j = 0; j < batch_size; ++j) {
                    if (diff_values[j] == 0) {
                        intersection.push_back(A[i + j]);
                        break;
                    }
                }
            }
        }

        return intersection;
    }

private:
    std::unique_ptr<SEALContext> context_;
    SecretKey secret_key_;
    RelinKeys relin_keys_;
    std::unique_ptr<Encryptor> encryptor_;
    std::unique_ptr<Evaluator> evaluator_;
    std::unique_ptr<Decryptor> decryptor_;
};
```

### 10.11.5 Análise de Segurança do PSI

```cpp
// O protocolo PSI acima tem uma limitação de segurança:
// Bob pode aprender a distância entre elementos (b - a)
// para cada par (a, b), mesmo sem ver a diretamente.

// Para segurança mais forte, usar:
// 1. Oblivious Transfer (OT)
// 2. Private Polynomial Evaluation
// 3. PSI com DH assumption
// 4. Circuit-based PSI

// Implementação conceitual de PSI mais seguro:
class SecurePSI {
    // 1. Alice escolhe polinômio P(x) = (x-a₁)(x-a₂)...(x-aₙ)
    // 2. Bob avalia P(bᵢ) para cada bᵢ
    // 3. Se P(bᵢ) = 0, então bᵢ ∈ A

    // Vantagens:
    // - Não revela distâncias entre elementos
    // - Baseado em DH assumption
    // - Não requer FHE (usar OT ou DH)

    // Implementação real requer troca de chaves Diffie-Hellman
    // e avaliação de polinômios de grau alto
};
```

### 10.11.6 Testes e Validação

```cpp
#include <cassert>

void test_psi_basic() {
    PrivateSetIntersection psi;

    // Caso 1: Interseção não-vazia
    std::vector<double> A1 = {1.0, 2.0, 3.0};
    std::vector<double> B1 = {2.0, 3.0, 4.0};
    auto enc_A1 = psi.encrypt_set(A1);
    auto result1 = psi.compute_intersection(enc_A1, B1);
    assert(result1.size() == 2);  // {2, 3}

    // Caso 2: Interseção vazia
    std::vector<double> A2 = {1.0, 2.0};
    std::vector<double> B2 = {3.0, 4.0};
    auto enc_A2 = psi.encrypt_set(A2);
    auto result2 = psi.compute_intersection(enc_A2, B2);
    assert(result2.empty());

    // Caso 3: Interseção total
    std::vector<double> A3 = {1.0, 2.0, 3.0};
    std::vector<double> B3 = {1.0, 2.0, 3.0};
    auto enc_A3 = psi.encrypt_set(A3);
    auto result3 = psi.compute_intersection(enc_A3, B3);
    assert(result3.size() == 3);

    // Caso 4: Conjuntos grandes
    std::vector<double> A4(100), B4(100);
    for (int i = 0; i < 100; ++i) {
        A4[i] = static_cast<double>(i);
        B4[i] = static_cast<double>(i + 50);  // Overlap: 50-99
    }
    auto enc_A4 = psi.encrypt_set(A4);
    auto result4 = psi.compute_intersection(enc_A4, B4);
    assert(result4.size() == 50);

    std::cout << "Todos os testes passaram!\n";
}

int main() {
    test_psi_basic();
    return 0;
}
```

---

## 10.12 Comparação de Bibliotecas

### 10.12.1 Visão Geral

| Biblioteca | Desenvolvedor | Linguagem | Esquemas | Licença |
|-----------|--------------|-----------|----------|---------|
| Microsoft SEAL | Microsoft Research | C++17 | BFV, CKKS | MIT |
| HElib | IBM Research | C++ | BGV, CKKS | Apache-2.0 |
| Lattigo | Tune Insight | Go | BFV, CKKS, RLWE | Apache-2.0 |
| TFHE | Zama | C/C++ | TFHE | BSD-3 |
| OpenFHE | Duality Tech | C++17 | BGV, BFV, CKKS, TFHE | BSD-2 |
| Concrete | Zama | Rust/Python | TFHE | BSD-3 |

### 10.12.2 Microsoft SEAL

**Vantagens:**
- Excelente documentação
- APIs limpas e intuitivas
- Bom suporte a serialização
- Comunidade ativa (GitHub)
- Otimizado para x86-64
- Multi-threading via OpenMP

**Limitações:**
- Apenas BFV e CKKS (sem BGV puro)
- Sem bootstrapping (apenas SHE)
- Sem suporte a GPU nativo

**Código mínimo:**
```cpp
// SEAL: 20 linhas para encriptar, somar e decriptar
EncryptionParameters params(scheme_type::bfv);
params.set_poly_modulus_degree(4096);
params.set_coeff_modulus(CoeffModulus::BFVDefault(4096));
params.set_plain_modulus(1024);
SEALContext context(params);
KeyGenerator keygen(context);
// ... encrypt, add, decrypt
```

### 10.12.3 HElib

**Vantagens:**
- Implementação madura do BGV
- Suporte a bootstrapping
- Batch encoding avançado
- Mais opções de parâmetros
- Pesquisas em privacidade diferencial integrada

**Limitações:**
- API mais complexa
- Documentação menos acessível
- Performance inferior ao SEAL em muitos benchmarks
- Menor comunidade de usuários

**Código mínimo:**
```cpp
// HElib: BGV com batching
#include <helib/helib.h>

// Configuração mais verbosa
NTL::zz_p::init(NTL::power(2, 20));
Context context(m, p, r, gens, ords);
context.buildModChain(30, 2);

SecKey secret_key(context);
secret_key.GenSecKey();
const PubKey& public_key = secret_key;

// Encriptar usando batching
EncryptedArray ea(context);
PlaintextArray plaintext(ea);
// ...
```

### 10.12.4 Lattigo

**Vantagens:**
- Linguagem Go (mais fácil de deploy)
- APIs idiomáticas em Go
- BFV, CKKS, e RLWE
- Boa serialização e networking
- Suporte a concorrência natural do Go

**Limitações:**
- Go em vez de C++ (overhead de FFI para C++)
- Performance inferior ao SEAL
- Comunidade menor

**Código mínimo:**
```go
// Lattigo: Go idiomático
params, _ := bfv.NewParametersFromLiteral(bfv.DefaultParamsLvl0)

encoder, _ := bfv.NewEncoder(params)
keygen, _ := bfv.NewKeyGenerator(params)
sk, pk := keygen.GenKeyPair()

encryptor, _ := bfv.NewEncryptor(params, pk)
decryptor, _ := bfv.NewDecryptor(params, sk)

pt, _ := encoder.EncodeNew([]uint64{42})
ct, _ := encryptor.EncryptNew(pt)
```

### 10.12.5 TFHE

**Vantagens:**
- Bootstrapping eficiente
- Operações bit-a-bit
- Precisão exata
- Ideal para computação booleana
- Suporte a torção (TFHE sobre torus)

**Limitações:**
- Apenas operações booleanas
- Performance por gate ~10ms (mesmo com bootstrapping)
- Não é otimizado para aritmética numérica
- Menos opções de parâmetros

**Código mínimo:**
```cpp
// TFHE: portas booleanas
#include <tfhe/tfhe.h>

auto params = new_default_gate_bootstrapping_parameters(128);
auto keys = new_random_gate_bootstrapping_keyset(params);

LweSample* a = new_gate_bootstrapping_ciphertext(params);
LweSample* b = new_gate_bootstrapping_ciphertext(params);
LweSample* c = new_gate_bootstrapping_ciphertext(params);

tfheGateBootstrappingEncryptKeyBit(a, keys->cloud, 1);
tfheGateBootstrappingEncryptKeyBit(b, keys->cloud, 0);

tfheGateAND(c, a, b, keys->cloud);
uint8_t result = tfheGateBootstrappingSchemeBitDecript(c, keys->secret);
```

### 10.12.6 OpenFHE

**Vantagens:**
- Suporta todos os esquemas (BGV, BFV, CKKS, TFHE)
- Bootstrapping para BGV/BFV
- Modular e extensível
- Compatibilidade com leitura de chaves de outros formatos
- Multi-precision

**Limitações:**
- Mais recente, menos maduro que SEAL
- Documentação em crescimento
- Complexidade pela amplitude de features

**Código mínimo:**
```cpp
// OpenFHE: suporte multi-esquema
#include "openfhe.h"

using namespace lbcrypto;

auto cryptoParams = std::make_shared<CryptoContextCKKS<DCRTPoly>>();
// ... configuração similar ao SEAL
```

### 10.12.7 Tabela de Decisão

```
┌─────────────────────────────────────────────────────────────────┐
│                  Escolhendo uma Biblioteca HE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Precisa de C++ e simplicidade?                                │
│  ├─ Sim → Microsoft SEAL (melhor documentação)                │
│  └─ Não ↓                                                      │
│                                                                 │
│  Precisa de BGV puro ou bootstrapping?                         │
│  ├─ Sim → HElib ou OpenFHE                                    │
│  └─ Não ↓                                                      │
│                                                                 │
│  Precisa de Go para deploy?                                    │
│  ├─ Sim → Lattigo                                              │
│  └─ Não ↓                                                      │
│                                                                 │
│  Precisa de operações booleanas (TFHE)?                        │
│  ├─ Sim → TFHE ou OpenFHE (TFHE mode)                        │
│  └─ Não ↓                                                      │
│                                                                 │
│  Precisa de suporte multi-esquema?                             │
│  ├─ Sim → OpenFHE                                              │
│  └─ Não → Microsoft SEAL (CKKS ou BFV)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 10.12.8 Benchmarks Comparativos

```cpp
// Benchmark: soma de 1000 ciphertexts (BFV-4096, 128-bit security)
//
// SEAL:    ~15ms total (0.015ms por soma)
// HElib:   ~25ms total (0.025ms por soma)
// OpenFHE: ~18ms total (0.018ms por soma)
// Lattigo: ~30ms total (0.030ms por soma)

// Benchmark: multiplicação (BFV-4096)
//
// SEAL:    ~0.3ms por multiplicação
// HElib:   ~0.5ms por multiplicação
// OpenFHE: ~0.35ms por multiplicação
// Lattigo: ~0.6ms por multiplicação

// Benchmark: CKKS (8192, 4 níveis, 8 slots)
//
// SEAL:    ~0.8ms por multiply-rescale
// Lattigo: ~1.2ms por multiply-rescale

// Nota: benchmarks variam significativamente com hardware,
// parâmetros, e otimizações específicas
```

---

## 10.13 Exercícios

### Exercício 1: Somatório Encriptado

Implemente um sistema que encripta uma lista de valores usando BFV e computa a soma total homomorficamente. Compare o tempo de execução com a soma em texto plano.

**Requisitos:**
- Usar Microsoft SEAL com poly_modulus_degree = 4096
- Encriptar 1000 valores inteiros
- Computar soma homomorfica
- Medir e comparar performance
- Verificar correção

```cpp
// Seu código aqui
// Dicas:
// 1. Usar BatchEncoder para múltiplos valores por ciphertext
// 2. Usar evaluator.add_inplace para somar
// 3. Usar std::chrono para medir tempo
```

### Exercício 2: Média Aritmética Encriptada

Implemente o cálculo da média aritmética de N valores encriptados usando CKKS.

**Requisitos:**
- Usar CKKS com poly_modulus_degree = 8192
- Encriptar vetores com até 8192 slots
- Computar soma e dividir por N
- Tratar rescaling corretamente
- Medir erro de precisão

```cpp
// Seu código aqui
// Dicas:
// 1. O rescale deve ser feito após cada multiplicação
// 2. Todos os ciphertexts devem estar no mesmo nível antes de somar
// 3. Usar CKKSEncoder para encode/decode
```

### Exercício 3: Circuito Booleano com TFHE

Implemente um somador completo de 8 bits usando TFHE (ou biblioteca similar).

**Requisitos:**
- Usar tfhe++ ou equivalente
- Implementar half-adder e full-adder
- Somar dois números de 8 bits encriptados
- Verificar correção (comparar com texto plano)

```cpp
// Seu código aqui
// Dicas:
// 1. Half-adder: sum = XOR(a,b), carry = AND(a,b)
// 2. Full-adder: sum = XOR(XOR(a,b),cin), carry = MAJORITY(a,b,cin)
// 3. Cascatear full-adders para N bits
```

### Exercício 4: Comparação de Bibliotecas

Escreva o mesmo programa (soma de 100 inteiros) usando SEAL, HElib e Lattigo (ou OpenFHE). Compare:
- Tempo de execução
- Consumo de memória
- Facilidade de uso (subjetiva)
- Tamanho do código

### Exercício 5: PSI Otimizado

Melhore a implementação de PSI do exemplo anterior:
- Use OT (Oblivious Transfer) para evitar revelar distâncias
- Implemente batchamento eficiente
- Teste com conjuntos de 10.000 elementos
- Meça tempo e memória

```cpp
// Seu código aqui
// Conceitos avançados:
// 1. OT: 2-out-of-1 oblivious transfer
// 2. Polynomial evaluation: P(x) = (x-a₁)...(x-aₙ)
// 3. Zero-knowledge proofs para validação
```

### Exercício 6: ML Inferência Encriptada

Implemente inferência de uma rede neural simples (perceptron) sobre dados encriptados.

**Requisitos:**
- Rede: 1 camada (perceptron)
- Dados de entrada encriptados com CKKS
- Pesos do modelo em texto plano
- Ativação: sign function (aproximada)

```cpp
// Seu código aqui
// Dicas:
// 1. y = sign(w₁x₁ + w₂x₂ + ... + wₙxₙ)
// 2. Usar polynomial approximation para sign()
// 3. Limitar profundidade do circuito
```

### Exercício 7: Bootstrapping (Avançado)

Para usuários avançados: implemente bootstrapping simples em CKKS (ou TFHE).

**Conceitos:**
- O bootstrapping encripta a chave secreta
- Avalia o circuito de decriptação homomorficamente
- O resultado é um ciphertext com ruído reduzido

**Referências:**
- "Fully Homomorphic Encryption" por Craig Gentry (2009)
- CKKS bootstrapping paper (2017)
- TFHE bootstrapping optimization (2016)

### Exercício 8: Benchmark Suite

Crie uma suíte de benchmarks completa comparando:
- BFV vs CKKS para a mesma tarefa
- Diferentes poly_modulus_degree (2048, 4096, 8192, 16384)
- Sequencial vs paralelo (1, 2, 4, 8 threads)
- Com e sem relinearização

---

## 10.14 Referências

### Papers Fundamentais

1. **Gentry, C.** (2009). "A Fully Homomorphic Encryption Scheme." Stanford University. PhD Thesis.
   - Primeiro esquema FHE prático baseado em ideal lattices.

2. **Brakerski, Z., Gentry, C., & Vaikuntanathan, V.** (2012). "Leveled Fully Homomorphic Encryption without Bootstrapping." ACM TOCT.
   - BGV: FHE escalável sem bootstrapping.

3. **Brakerski, Z., & Vaikuntanathan, V.** (2011). "Efficient Fully Homomorphic Encryption from (Standard) LWE." FOCS.
   - Base teórica para BGV e BFV.

4. **Fan, J., & Vercauteren, F.** (2012). "Somewhat Practical Fully Homomorphic Encryption." IACR ePrint.
   - BFV: variante prática de BGV.

5. **Cheon, J.H., Kim, A., Kim, M., & Song, Y.** (2017). "Homomorphic Encryption for Arithmetic of Approximate Numbers." ASIACRYPT.
   - CKKS: revolução em aritmética aproximada.

6. **Chillotti, I., Gama, N., Georgieva, M., & Izabachène, M.** (2016). "TFHE: Fast Fully Homomorphic Encryption over the Torus." IACR ePrint.
   - TFHE: bootstrapping eficiente para portas booleanas.

### Livros e Survey Papers

7. **Gentry, C., Halevi, S., & Smart, N.P.** (2012). "Homomorphic Encryption for Arithmetic of Approximate Numbers." — Survey abrangente.

8. **Peikert, C.** (2016). "A Decade of Lattice Cryptography." Foundations and Trends in Theoretical Computer Science.
   - Revisão de problemas de reticulados e aplicações criptográficas.

9. **Boneh, D., & Shoup, V.** (2023). "A Graduate Course in Applied Cryptography."
   - Capítulo 18: Homomorphic Encryption.

### Documentação de Bibliotecas

10. **Microsoft SEAL Documentation.** https://github.com/microsoft/SEAL
    - Documentação oficial com tutoriais e API reference.

11. **HElib.** https://github.com/homenc/HElib
    - Biblioteca IBM para BGV/CKKS.

12. **Lattigo.** https://github.com/tuneinsight/lattigo
    - Implementação Go de FHE.

13. **TFHE.** https://github.com/tfheorg/tfhe
    - Biblioteca C++ para TFHE.

14. **OpenFHE.** https://github.com/openfheorg/openfhe-development
    - Biblioteca multi-esquema de Duality Tech.

### Recursos Online

15. **HomomorphicEncryption.org.** — Padrões e especificações de FHE.

16. **Microsoft SEAL Workshop.** — Tutoriais práticos em vídeo.

17. **FHE.org.** — Comunidade e conferências sobre criptografia homomórfica.

### Papers de Aplicação

18. **Graepel, T., Lauter, K., & Naor, M.** (2012). "Private Learning on Neural Networks Using Homomorphic Encryption." — ML sobre dados encriptados.

19. **Lauter, K., Naehrig, M., & Vaikuntanathan, V.** (2014). "Can Homomorphic Encryption be Practical?" — Análise de viabilidade prática.

20. **Chen, H., Laine, K., & Player, R.** (2017). "Simple Encrypted Arithmetic Library with SEAL." — Tutorial prático com SEAL.

---

## Resumo do Capítulo

Este capítulo cobriu os fundamentos e práticas da criptografia homomórfica em C++17:

**Conceitos-chave:**
- Criptografia homomórfica permite computação sobre dados encriptados
- Três categorias: PHE, SHE, FHE
- Segurança baseada em problemas de reticulados (resistentes a quânticos)
- Gerenciamento de ruído é o desafio central

**Bibliotecas:**
- **SEAL**: melhor para C++ e uso geral (BFV/CKKS)
- **HElib**: melhor para BGV e bootstrapping
- **TFHE**: melhor para operações booleanas
- **OpenFHE**: melhor para multi-esquema
- **Lattigo**: melhor para Go e deploy

**Trade-offs:**
- Performance: 10K-1M mais lento que texto plano
- Memória: ciphertexts grandes (64KB-2MB cada)
- Complexidade: gerenciamento de parâmetros é não-trivial
- Privacidade: sem precedentes em segurança computacional

**Próximos passos:**
- Experimentar com os exercícios
- Explorar a documentação oficial do SEAL
- Considerar FHE para casos de uso que exigem privacidade máxima
- Acompanhar evolução da padronização (HomomorphicEncryption.org)

A criptografia homomórfica representa o estado da arte em computação privativa. Embora ainda tenha limitações significativas de performance, sua adoção está crescendo em áreas como saúde, finanças e machine learning. C++17 fornece a base ideal para implementar sistemas FHE de alta performance.
---

*[Capítulo anterior: 09 — Hardware Security Tpm](09-hardware-security-tpm.md)*
*[Próximo capítulo: 11 — Zero Knowledge Proofs](11-zero-knowledge-proofs.md)*
