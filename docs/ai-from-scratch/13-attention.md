---
layout: default
title: "13-attention"
---

# Capitulo 13 — Mecanismo de Attention

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender o problema das sequencias longas** — por que RNNs e LSTMs perdem informacao em sequencias longas e como attention resolve isso.
2. **Entender o mecanismo attention completo** — query, key, value, e como esses tres componentes interagem.
3. **Dominar scaled dot-product attention** — a formula matematica, por que a divisao por sqrt(d_k), e quando usar.
4. **Implementar multi-head attention** — varias heads de attention paralelas e concatenacao.
5. **Diferenciar self-attention de cross-attention** — quando cada um e usado e por que.
6. **Dominar softmax para attention** — estabilidade numerica, temperatura, e mascaramento.
7. **Implementar positional encoding** — sinusoidal e learned, para injetar informacao posicional.
8. **Implementar attention completo em C++** — todas as variantes, forward e backward.
9. **Implementar attention em Rust** — usando ownership para gestao segura de tensores.
10. **Implementar attention em Fortran** — usando arrays e subrotinas eficientes.
11. **Analisar complexidade** — O(n^2*d) e como reduzir.
12. **Visualizar attention weights** — entender o que o modelo esta "olhando".

---

## 1. O Problema das Sequencias Longas

### 1.1 Limitacoes das RNNs

As RNNs processam sequencias passo a passo, o que cria problemas fundamentais:

```text
Problema 1: Vanishing Gradient
===============================
Em uma RNN basica:
  h_t = tanh(W_hh * h_{t-1} + W_xh * x_t + b)

O gradiente de h_T em relacao a h_1:
  dh_T/dh_1 = prod(t=2..T) [W_hh * diag(1 - h_t^2)]

Para T = 1000 passos:
  - Autovalores < 1: gradiente encolhe ~lambda^1000 -> 0
  - Autovalores > 1: gradiente cresce ~lambda^1000 -> infinito

Resultado: a rede NAO consegue aprender dependencias de longo prazo.
```

```text
Problema 2: Bottleneck Informacional
=====================================
O hidden state h_t e um VETOR FIXO que precisa resumir
TODA a informacao da sequencia ate o momento:

  "O gato sentou no" -> h_50 = [0.12, -0.45, ...] (d=512)

Problema: como comprimir "O gato sentou no sofá azul que estava 
no quarto da vovó que mora em São Paulo" em um unico vetor?

Solucao RNN: processa sequencialmente, mas perde informacao.
Solucao ATTENTION: acessa QUALQUER posicao diretamente.
```

### 1.2 A Intuicao do Attention

O attention mecanismo foi inspirado no atendimento humano:

```text
Atencao Humana vs Machine Attention:
======================================

Humano lendo: "O gato sentou no sofá azul"
  - Para saber a cor do sofá, olha para "sofá"
  - Para saber quem sentou, olha para "gato"
  - NÃO precisa relembrar toda a frase

Machine Attention:
  - Para cada posicao, calcula "quanto olhar" para CADA outra posicao
  - Peso de attention w_{i,j} = "importancia de j quando processando i"
  - Output = soma ponderada de TODOS os valores
  - NÃO precisa processar sequencialmente
```

### 1.3 Historia e Evolucao

```text
Linha do Tempo do Attention:
==============================

2014: Bahdanau et al. - "Neural Machine Translation by Jointly 
      Learning to Align and Translate"
      -> Primeiro attention mecanismo para NMT
      -> Attention aditivo (additive attention)

2015: Luong et al. - "Effective Approaches to Attention-based 
      Neural Machine Translation"
      -> Attention multiplicativo (dot-product)
      -> Mais eficiente computacionalmente

2016: Xu et al. - "Show, Attend and Tell"
      -> Attention para Computer Vision
      -> Visual attention para legendas de imagens

2017: Vaswani et al. - "Attention Is All You Need"
      -> Multi-head self-attention
      -> Transformer architecture
      -> Relevou RNNs completamente
```

---

## 2. Attention Basico: Query, Key, Value

### 2.1 Os Tres Componentes

O mecanismo attention opera sobre tres projetoes do dado de entrada:

```text
Os Tres Componentes do Attention:
==================================

Dado um input x_i, projetamos em tres vetores:

  Query (q_i): O que EU estou procurando?
               "Qual informacao eu preciso agora?"

  Key (k_j):   O que EU ofereco?
               "Que tipo de informacao eu tenho?"

  Value (v_j): O conteudo REAL que eu传输
               "Qual e a informacao que eu realmente carrego?"

Analogia com busca em banco de dados:
  - Query = "SELECT * FROM dados WHERE..."
  - Key   = indices do banco (indices sao comparados com query)
  - Value = os dados retornados

Diferenca: em ML, queries, keys e values SAO APRENDIDOS.
  W_q, W_k, W_v sao matrizes de pesos que o modelo treina.
```

### 2.2 Projecoes Lineares

Cada componente e obtido por uma projecao linear do input:

```text
Projecoes:
===========

Dado input X ∈ R^{n x d_model} (n tokens, d_model dimensoes):

  Q = X * W_q   (n x d_model) * (d_model x d_k) = (n x d_k)
  K = X * W_k   (n x d_model) * (d_model x d_k) = (n x d_k)
  V = X * W_v   (n x d_model) * (d_model x d_v) = (n x d_v)

Onde:
  - W_q: matriz de projecao para queries
  - W_k: matriz de projecao para keys
  - W_v: matriz de projecao para values
  - d_k: dimensao das keys/queries
  - d_v: dimensao dos values (pode ser diferente de d_k)

Exemplo com numeros:
  X = [[1.0, 2.0, 3.0],    (3 tokens, d_model=3)
       [4.0, 5.0, 6.0],
       [7.0, 8.0, 9.0]]

  W_q = [[0.1, 0.2],       (d_model=3, d_k=2)
         [0.3, 0.4],
         [0.5, 0.6]]

  Q = X * W_q
    = [[1*0.1+2*0.3+3*0.5, 1*0.2+2*0.4+3*0.6],
       [4*0.1+5*0.3+6*0.5, 4*0.2+5*0.4+6*0.6],
       [7*0.1+8*0.3+9*0.5, 7*0.2+8*0.4+9*0.6]]
    = [[2.2, 2.8],
       [4.9, 6.4],
       [7.6, 10.0]]
```

### 2.3 Calculo dos Pesos de Attention

Os pesos de attention sao calculados comparando queries com keys:

```text
Computacao dos Pesos:
======================

Para cada query q_i, comparamos com TODAS as keys k_j:

  score(q_i, k_j) = q_i · k_j   (produto escalar)

Matricialmente:
  S = Q * K^T   (n x d_k) * (d_k x n) = (n x n)

S[i][j] = "quao relevante e a posicao j para a posicao i"

Exemplo:
  Q = [[2.2, 2.8],     K = [[1.1, 1.4],
       [4.9, 6.4],          [2.5, 3.2],
       [7.6, 10.0]]         [3.8, 5.0]]

  S = Q * K^T
    = [[2.2*1.1+2.8*1.4, 2.2*2.5+2.8*3.2, 2.2*3.8+2.8*5.0],
       [4.9*1.1+6.4*1.4, 4.9*2.5+6.4*3.2, 4.9*3.8+6.4*5.0],
       [7.6*1.1+10*1.4,  7.6*2.5+10*3.2,  7.6*3.8+10*5.0]]
    = [[6.3, 14.2, 28.3],
       [14.5, 33.0, 50.4],
       [22.8, 51.4, 78.7]]
```

### 2.4 Normalizacao: Scaled Dot-Product

O produto escalar pode gerar valores muito grandes, especialmente para dimensoes altas:

```text
Problema de Escala:
====================

Se d_k = 512 e os valores de q_i e k_j sao ~N(0,1):
  Var(q_i · k_j) = d_k * Var(q_1) * Var(k_1) = 512

  Isso significa que os scores podem ser muito grandes
  -> softmax fica "too peaky" (quase um one-hot)
  -> gradientes ficam proximos de zero
  -> treinamento estagna

Solucao: dividir por sqrt(d_k):

  Scaled_Score = (Q * K^T) / sqrt(d_k)

  Var(Scaled_Score) = Var(q_i · k_j) / d_k = 1

  Resultado: scores com variancia controlada
  -> softmax distribui mais uniformemente
  -> gradientes saudaveis para treinamento
```

---

## 3. Scaled Dot-Product Attention

### 3.1 Formula Completa

A formula completa do scaled dot-product attention:

```text
Scaled Dot-Product Attention:
===============================

                    Q * K^T
Attention(Q,K,V) = softmax(-------) * V
                    sqrt(d_k)

Passo a passo:
  1. S = Q * K^T          (n x n) scores brutos
  2. S = S / sqrt(d_k)    (n x n) scores escalados
  3. A = softmax(S)        (n x n) pesos normalizados
  4. O = A * V             (n x d_v) saida ponderada

Dimensoes:
  Q: (n x d_k)
  K: (n x d_k)
  V: (n x d_v)
  S: (n x n)
  A: (n x n)
  O: (n x d_v)
```

### 3.2 Softmax em Detalhes

O softmax converte scores em probabilidades:

```text
Softmax:
=========

Para cada linha i da matriz de scores S[i]:
  softmax(S[i][j]) = exp(S[i][j]) / sum_k(exp(S[i][k]))

Propriedades:
  - Todos os valores em (0, 1)
  - Soma de cada linha = 1
  - Diferenciavel (usado no treinamento)
  - Preserva a ordem dos valores

Exemplo:
  S[i] = [2.0, 1.0, 0.1]
  exp:   [7.39, 2.72, 1.10]
  soma:  11.21
  softmax: [0.659, 0.242, 0.098]

Interpretacao:
  - Posicao 0 recebe 65.9% da atencao
  - Posicao 1 recebe 24.2% da atencao
  - Posicao 2 recebe 9.8% da atencao
```

### 3.3 Mascaramento (Masking)

Em muitos cenarios precisamos mascarar posicoes:

```text
Tipos de Mascara:
==================

1. Padding Mask:
   - Para sequencias de tamanhos diferentes em um batch
   - Posicoes de padding recebem score = -inf
   - softmax(zero) = 0 na saida

   S[i] = [1.2, 0.5, -inf, -inf, -inf]
   softmax: [0.65, 0.35, 0, 0, 0]

2. Causal Mask (Look-ahead):
   - No decoder, NAO podemos olhar para o futuro
   - Posicoes futuras recebem score = -inf
   - Garante autoregressividade

   S[i] = [1.2, 0.8, 0.5, -inf, -inf]
   softmax: [0.42, 0.28, 0.30, 0, 0]

3. Combined Mask:
   - Junta padding + causal
   - Usado no decoder do Transformer

   S[i] = [1.2, 0.8, -inf, -inf, -inf]
   softmax: [0.59, 0.41, 0, 0, 0]
```

---

## 4. Multi-Head Attention

### 4.1 Por Que Multiplas Heads

Uma unica head de attention pode nao capturar todas as relacoes:

```text
Problema com Uma Head:
========================

Frase: "O gato comeu o peixe porque ele estava faminto"

Uma head pode focar:
  - Sintaxe: "gato" -> "comeu" (sujeito-verbo)
  - Semantica: "ele" -> "gato" (coreferencia)
  - Mas NAO consegue focar em AMBOS ao mesmo tempo

Solucao Multi-Head:
  - Multiplas heads paralelas
  - Cada head aprende um tipo de relacao diferente
  - Concatenacao combina todas as perspectivas
```

### 4.2 Arquitetura

```text
Multi-Head Attention:
=======================

Para h heads:
  head_i = Attention(Q * W_q^i, K * W_k^i, V * W_v^i)

  MultiHead(Q,K,V) = Concat(head_1, ..., head_h) * W_o

Dimensoes:
  d_k = d_model / h  (dimensao por head)
  d_v = d_model / h  (dimensao por head)

  W_q^i: (d_model x d_k) = (d_model x d_model/h)
  W_k^i: (d_model x d_k) = (d_model x d_model/h)
  W_v^i: (d_model x d_v) = (d_model x d_model/h)
  W_o:   (h*d_v x d_model) = (d_model x d_model)

Exemplo com d_model = 512, h = 8:
  d_k = 64, d_v = 64
  Cada head processa 64 dimensoes
  8 heads * 64 = 512 -> concatenado = 512
  W_o: 512 x 512
```

### 4.3 Implementacao Detalhada

```text
Passo a passo do Multi-Head:
==============================

1. Dividir em heads:
   Q_reshaped = reshape(Q, [n, h, d_k])
   K_reshaped = reshape(K, [n, h, d_k])
   V_reshaped = reshape(V, [n, h, d_v])

2. Transpor para heads paralelas:
   Q_heads = transpose(Q_reshaped, [1, 0, 2])  # (h, n, d_k)
   K_heads = transpose(K_reshaped, [1, 0, 2])  # (h, n, d_k)
   V_heads = transpose(V_reshaped, [1, 0, 2])  # (h, n, d_v)

3. Para cada head i (paralelizavel):
   head_i = softmax(Q_heads[i] * K_heads[i]^T / sqrt(d_k)) * V_heads[i]

4. Concatenar heads:
   Concat = Concatenate(head_1, ..., head_h)  # (n, h*d_v)

5. Projecao final:
   Output = Concat * W_o  # (n, d_model)

Contagem de Parametros:
  W_q: h * (d_model * d_k) = h * d_model * (d_model/h) = d_model^2
  W_k: d_model^2
  W_v: d_model^2
  W_o: d_model^2
  Total: 4 * d_model^2
```

---

## 5. Self-Attention

### 5.1 Conceito

Self-attention e o caso onde Q, K, V vêm da MESMA sequencia:

```text
Self-Attention:
================

Q = X * W_q  (queries do proprio input)
K = X * W_k  (keys do proprio input)
V = X * W_v  (values do proprio input)

Cada posicao olha para TODAS as outras posicoes
na MESMA sequencia.

Exemplo:
  Sequencia: "O gato comeu o peixe"
  Token 2 ("gato") olha para:
    - "O" (artigo antes)
    - "comeu" (verbo depois)
    - "o" (artigo depois)
    - "peixe" (objeto)
  -> Aprende que "gato" e o SUJEITO de "comeu"
```

### 5.2 Self-Attention no Encoder

```text
Encoder Self-Attention:
=========================

Caracteristicas:
  - Bidirecional: cada token olha para TODOS os outros
  - Sem mascara causal
  - Sem mascara de padding (opcional)

Uso:
  - Capturar relacoes sintaticas e semanticas
  - Base do BERT e do encoder do Transformer
  - Cada camada refina a representacao

Fluxo:
  Input: ["O", "gato", "comeu", "o", "peixe"]
  
  Camada 1:
    "O" -> attention -> [0.1, 0.6, 0.1, 0.1, 0.1]  # foca em "gato"
    "gato" -> attention -> [0.2, 0.1, 0.5, 0.1, 0.1]  # foca em "comeu"
    "comeu" -> attention -> [0.1, 0.4, 0.1, 0.1, 0.3]  # foca em "gato" e "peixe"
  
  Output: representacoes enriquecidas com contexto
```

---

## 6. Cross-Attention

### 6.1 Diferenca para Self-Attention

Em cross-attention, Q vem de uma fonte e K,V de outra:

```text
Cross-Attention:
=================

Q = Source * W_q    (do encoder, por exemplo)
K = Target * W_k    (do decoder, por exemplo)
V = Target * W_v    (do decoder, por exemplo)

O "Source" faz perguntas ao "Target".

Exemplo no Transformer:
  - Encoder produz representacao da frase em ingles
  - Decoder esta gerando traducao em portugues
  - Cada posicao do decoder (portugues) olha para
    TODAS as posicoes do encoder (ingles)
  - "gato" (PT) -> attende para "cat" (EN)
```

### 6.2 Cross-Attention no Transformer

```text
Cross-Attention no Transformer:
================================

No Decoder:
  1. Masked Self-Attention:
     - Cada token olha para tokens ANTERIORES
     - Mascara causal impede olhar para futuro
     - Output: representacao contextual do decoder

  2. Cross-Attention:
     - Q do decoder (output do masked self-attention)
     - K, V do encoder (representacao final)
     - Output: decoder "busca" informacao do encoder

  3. Feed-Forward:
     - Transformacao nao-linear independente

Fluxo visual:
  Encoder: [x1, x2, x3] -> [e1, e2, e3]
                                       |
  Decoder: [y1] -> [Masked SA] -> [d1] -> [Cross-Attn(Q=d1, K=e, V=e)] -> [c1] -> [FFN]
                                       
  Cada passo do decoder:
    - Primeiro processa o que ja gerou (masked self-attention)
    - Depois consulta o encoder (cross-attention)
    - Finalmente transforma (feed-forward)
```

---

## 7. Attention Weights e Softmax

### 7.1 Propriedades dos Pesos de Attention

```text
Propriedades dos Pesos:
========================

1. Non-negatividade:
   w_{i,j} >= 0 (resultante do softmax)

2. Normalizacao:
   sum_j(w_{i,j}) = 1 (softmax normaliza)

3. Interpretabilidade:
   w_{i,j} = "importancia da posicao j quando processando i"

4. Dependencia:
   w_{i,j} depende de q_i e k_j
   NAO depende de v_j (v so e usado no output)

5. Densidade:
   Todos os pesos sao nao-zero (mas podem ser numericamente zero)
   -> attention e DENSO por padrao
   -> Sparse attention e uma variante
```

### 7.2 Estabilidade Numerica do Softmax

```text
Problema de Estabilidade:
==========================

Computar exp(x) para x muito grande causa overflow:
  exp(1000) = inf (overflow)
  exp(-1000) = 0 (underflow)

Solucao: subtract max:

  softmax(x_i) = exp(x_i - max(x)) / sum(exp(x_j - max(x)))

Isso garante que o maior valor de exp() e sempre 1.
Todos os outros valores sao <= 1.
Nao ha overflow.

Implementacao estavel:
  max_val = max(x)  # encontra o maior
  exp_x = exp(x - max_val)  # desloca para baixo
  softmax_x = exp_x / sum(exp_x)  # normaliza
```

### 7.3 Temperatura

```text
Temperatura no Softmax:
========================

Softmax com temperatura tau:
  softmax(x_i / tau) = exp(x_i / tau) / sum(exp(x_j / tau))

Efeitos:
  tau = 1: softmax padrao
  tau > 1: distribuicao mais uniforme (menos focada)
  tau < 1: distribuicao mais pico (mais focada)
  tau -> 0: approximacao de argmax (one-hot)
  tau -> infinito: distribuicao uniforme

Uso:
  - tau baixo em temperature sampling (texto mais deterministico)
  - tau alto em temperature sampling (texto mais variado)
  - tau = 1 em treinamento normal
```

---

## 8. Positional Encoding

### 8.1 Por Que Positional Encoding

O attention mecanismo e permutacao-invariante:

```text
Problema da Permutacao:
========================

Self-attention NAO distingue ordem:
  "gato comeu peixe" e "peixe comeu gato"
  produzem os MESMOS scores de attention
  (se os tokens fossem os mesmos)

Isso e porque attention usa SOMENTE produtos escalares.
Nao ha "posicao" na computacao.

Solucao: adicionar informacao posicional AO INPUT.

O positional encoding injeta "onde cada token esta"
na representacao, ANTES do attention.
```

### 8.2 Positional Encoding Sinusoidal

O Transformer original usa funcoes sinusoidais:

```text
Positional Encoding Sinusoidal:
================================

Para posicao pos e dimensao i:

  PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
  PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))

Onde:
  pos: posicao do token na sequencia (0, 1, 2, ...)
  i: indice da dimensao (0, 1, 2, ..., d_model/2 - 1)
  d_model: dimensao do modelo

Propriedades:
  1. Cada dimensao tem uma frequencia diferente
  2. Dimensoes pares: seno
  3. Dimensoes impares: cosseno
  4. Frequencia diminui com a dimensao
  5. Modelos relacoes de distancia

Exemplo (d_model = 4):
  pos=0: [sin(0/10000^0), cos(0/10000^0), sin(0/10000^0.5), cos(0/10000^0.5)]
        = [0.0, 1.0, 0.0, 1.0]

  pos=1: [sin(1/1), cos(1/1), sin(1/100), cos(1/100)]
        = [0.84, 0.54, 0.01, 1.00]

  pos=2: [sin(2/1), cos(2/1), sin(2/100), cos(2/100)]
        = [0.91, -0.42, 0.02, 1.00]
```

### 8.3 Propriedades Importantes

```text
Propriedades do PE Sinusoidal:
================================

1. Distancia Relativa:
   PE(pos+k) pode ser representado como transformacao linear de PE(pos)
   Isso permite ao modelo aprender relacoes relativas

2. Valores Limitados:
   PE(pos, i) ∈ [-1, 1] para todas as posicoes e dimensoes
   Nao causa explosao de valores

3. Unicidade:
   Cada posicao tem um vetor unico
   (nao ha colisoes para posicoes razoaveis)

4. Generalizacao:
   Pode generalizar para sequencias mais longas que as vistas no treino
   (as funcoes continuam definidas)
```

### 8.4 Learned Positional Encoding

Alternativa: aprender os embeddings de posicao:

```text
Learned Positional Encoding:
==============================

Em vez de funcoes fixas, aprende embeddings:
  PE = Embedding(max_seq_len, d_model)

  posicao 0 -> embedding[0] = [0.12, -0.45, ...]
  posicao 1 -> embedding[1] = [0.78, 0.23, ...]
  ...

Vantagens:
  + Pode capturar padroes complexos
  + Simples de implementar

Desvantagens:
  - Nao generaliza para sequencias mais longas
  - Mais parametros (max_seq_len * d_model)
  - Precisa de dados suficientes para treinar

Usado em: BERT, GPT-2, GPT-3
Original Transformer: sinusoidal
```

---

## 9. Implementacao Completa em C++

Agora implementamos o mecanismo attention completo em C++:

```cpp
// attention.h - Mecanismo de Attention do Zero
// Implementacao completa em C++ sem bibliotecas externas

#ifndef ATTENTION_H
#define ATTENTION_H

#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <numeric>
#include <limits>
#include <iostream>
#include <cassert>

// ============================================================
// Tensor basico para operacoes matriciais
// ============================================================

class Tensor {
public:
    std::vector<float> data;
    std::vector<int> shape;
    int total_size;

    Tensor() : total_size(0) {}

    Tensor(const std::vector<int>& shape) : shape(shape) {
        total_size = 1;
        for (int s : shape) total_size *= s;
        data.resize(total_size, 0.0f);
    }

    Tensor(const std::vector<int>& shape, float val) : shape(shape) {
        total_size = 1;
        for (int s : shape) total_size *= s;
        data.resize(total_size, val);
    }

    // Acesso por indices (ate 4D)
    float& at(int i0) { return data[i0]; }
    float& at(int i0, int i1) {
        return data[i0 * shape[1] + i1];
    }
    float& at(int i0, int i1, int i2) {
        return data[(i0 * shape[1] + i1) * shape[2] + i2];
    }
    float& at(int i0, int i1, int i2, int i3) {
        return data[((i0 * shape[1] + i1) * shape[2] + i2) * shape[3] + i3];
    }

    float at(int i0) const { return data[i0]; }
    float at(int i0, int i1) const {
        return data[i0 * shape[1] + i1];
    }
    float at(int i0, int i1, int i2) const {
        return data[(i0 * shape[1] + i1) * shape[2] + i2];
    }
    float at(int i0, int i1, int i2, int i3) const {
        return data[((i0 * shape[1] + i1) * shape[2] + i2) * shape[3] + i3];
    }

    // Zerar
    void zero() {
        std::fill(data.begin(), data.end(), 0.0f);
    }
};

// ============================================================
// Inicializacao Xavier/Glorot
// ============================================================

class XavierInit {
public:
    static void initialize(Tensor& t, std::mt19937& gen) {
        int fan_in = 1, fan_out = 1;
        if (t.shape.size() >= 2) {
            fan_in = t.shape[t.shape.size() - 2];
            fan_out = t.shape[t.shape.size() - 1];
        }
        float limit = std::sqrt(6.0f / (fan_in + fan_out));
        std::uniform_real_distribution<float> dist(-limit, limit);
        for (float& val : t.data) {
            val = dist(gen);
        }
    }
};

// ============================================================
// Matmul: C = A * B
// A: (m x k), B: (k x n), C: (m x n)
// ============================================================

void matmul(const Tensor& A, const Tensor& B, Tensor& C, int m, int k, int n) {
    C.zero();
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            float sum = 0.0f;
            for (int l = 0; l < k; l++) {
                sum += A.at(i, l) * B.at(l, j);
            }
            C.at(i, j) = sum;
        }
    }
}

// ============================================================
// Transpor matriz: B = A^T
// A: (m x n), B: (n x m)
// ============================================================

void transpose(const Tensor& A, Tensor& B, int m, int n) {
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            B.at(j, i) = A.at(i, j);
        }
    }
}

// ============================================================
// Softmax por linha (com estabilidade numerica)
// ============================================================

void softmax_row(Tensor& S, int n_rows, int n_cols) {
    for (int i = 0; i < n_rows; i++) {
        // Encontrar max para estabilidade
        float max_val = -std::numeric_limits<float>::infinity();
        for (int j = 0; j < n_cols; j++) {
            max_val = std::max(max_val, S.at(i, j));
        }

        // Calcular exp e soma
        float sum_exp = 0.0f;
        for (int j = 0; j < n_cols; j++) {
            S.at(i, j) = std::exp(S.at(i, j) - max_val);
            sum_exp += S.at(i, j);
        }

        // Normalizar
        for (int j = 0; j < n_cols; j++) {
            S.at(i, j) /= sum_val;
        }
    }
}

// ============================================================
// Scaled Dot-Product Attention
// ============================================================

class ScaledDotProductAttention {
public:
    // Forward pass
    // Q, K, V: (seq_len x d_k)
    // Output: (seq_len x d_v)
    // Scores: (seq_len x seq_len) - para visualizacao
    static Tensor forward(const Tensor& Q, const Tensor& K, const Tensor& V,
                          float scale, Tensor& scores) {
        int seq_len = Q.shape[0];
        int d_k = Q.shape[1];
        int d_v = V.shape[1];

        // 1. Calcular scores: S = Q * K^T
        Tensor K_T({d_k, seq_len});
        transpose(K, K_T, seq_len, d_k);

        Tensor raw_scores({seq_len, seq_len});
        matmul(Q, K_T, raw_scores, seq_len, d_k, seq_len);

        // 2. Escalar: S = S / sqrt(d_k)
        for (int i = 0; i < seq_len * seq_len; i++) {
            raw_scores.data[i] /= scale;
        }

        // 3. Softmax por linha
        softmax_row(raw_scores, seq_len, seq_len);

        // Salvar scores para visualizacao
        scores = raw_scores;

        // 4. Multiplicar por V: O = A * V
        Tensor output({seq_len, d_v});
        matmul(raw_scores, V, output, seq_len, seq_len, d_v);

        return output;
    }
};

// ============================================================
// Multi-Head Attention
// ============================================================

class MultiHeadAttention {
public:
    int d_model;
    int n_heads;
    int d_k;
    int d_v;

    // Pesos de projecao
    Tensor W_q;  // (d_model x d_k)
    Tensor W_k;  // (d_model x d_k)
    Tensor W_v;  // (d_model x d_v)
    Tensor W_o;  // (n_heads * d_v x d_model)

    MultiHeadAttention(int d_model, int n_heads)
        : d_model(d_model), n_heads(n_heads) {
        d_k = d_model / n_heads;
        d_v = d_model / n_heads;

        W_q = Tensor({d_model, d_k});
        W_k = Tensor({d_model, d_k});
        W_v = Tensor({d_model, d_v});
        W_o = Tensor({n_heads * d_v, d_model});
    }

    void init_weights(std::mt19937& gen) {
        XavierInit::initialize(W_q, gen);
        XavierInit::initialize(W_k, gen);
        XavierInit::initialize(W_v, gen);
        XavierInit::initialize(W_o, gen);
    }

    // Forward pass
    // X: (seq_len x d_model)
    // Output: (seq_len x d_model)
    Tensor forward(const Tensor& X,
                   std::vector<Tensor>& all_scores) {
        int seq_len = X.shape[0];
        float scale = std::sqrt(static_cast<float>(d_k));

        // Projetar Q, K, V
        Tensor Q({seq_len, d_k});
        Tensor K({seq_len, d_k});
        Tensor V({seq_len, d_v});
        matmul(X, W_q, Q, seq_len, d_model, d_k);
        matmul(X, W_k, K, seq_len, d_model, d_k);
        matmul(X, W_v, V, seq_len, d_model, d_v);

        // Dividir em heads
        // Cada head: Q_i = Q[:, i*d_k:(i+1)*d_k]
        Tensor concat({seq_len, n_heads * d_v});
        concat.zero();

        all_scores.resize(n_heads);

        for (int h = 0; h < n_heads; h++) {
            // Extrair slice para head h
            Tensor Q_h({seq_len, d_k});
            Tensor K_h({seq_len, d_k});
            Tensor V_h({seq_len, d_v});

            for (int i = 0; i < seq_len; i++) {
                for (int j = 0; j < d_k; j++) {
                    Q_h.at(i, j) = Q.at(i, h * d_k + j);
                    K_h.at(i, j) = K.at(i, h * d_k + j);
                }
                for (int j = 0; j < d_v; j++) {
                    V_h.at(i, j) = V.at(i, h * d_v + j);
                }
            }

            // Attention para esta head
            Tensor scores_h;
            Tensor head_out = ScaledDotProductAttention::forward(
                Q_h, K_h, V_h, scale, scores_h
            );
            all_scores[h] = scores_h;

            // Concatenar na saida
            for (int i = 0; i < seq_len; i++) {
                for (int j = 0; j < d_v; j++) {
                    concat.at(i, h * d_v + j) = head_out.at(i, j);
                }
            }
        }

        // Projecao final
        Tensor output({seq_len, d_model});
        matmul(concat, W_o, output, seq_len, n_heads * d_v, d_model);

        return output;
    }
};

// ============================================================
// Self-Attention (wrapper para Multi-Head com X = Q = K = V)
// ============================================================

class SelfAttention {
public:
    MultiHeadAttention mha;

    SelfAttention(int d_model, int n_heads) : mha(d_model, n_heads) {}

    void init_weights(std::mt19937& gen) {
        mha.init_weights(gen);
    }

    Tensor forward(const Tensor& X, std::vector<Tensor>& scores) {
        return mha.forward(X, scores);
    }
};

// ============================================================
// Cross-Attention (Q de uma fonte, K/V de outra)
// ============================================================

class CrossAttention {
public:
    MultiHeadAttention mha;

    CrossAttention(int d_model, int n_heads) : mha(d_model, n_heads) {}

    void init_weights(std::mt19937& gen) {
        mha.init_weights(gen);
    }

    // Q do decoder, K/V do encoder
    Tensor forward(const Tensor& Q_source,
                   const Tensor& KV_target,
                   std::vector<Tensor>& scores) {
        int seq_len_q = Q_source.shape[0];
        int seq_len_kv = KV_target.shape[0];
        float scale = std::sqrt(static_cast<float>(mha.d_k));

        // Projetar Q de Q_source
        Tensor Q({seq_len_q, mha.d_k});
        matmul(Q_source, mha.W_q, Q, seq_len_q, mha.d_model, mha.d_k);

        // Projetar K e V de KV_target
        Tensor K({seq_len_kv, mha.d_k});
        Tensor V({seq_len_kv, mha.d_v});
        matmul(KV_target, mha.W_k, K, seq_len_kv, mha.d_model, mha.d_k);
        matmul(KV_target, mha.W_v, V, seq_len_kv, mha.d_model, mha.d_v);

        // Scores: Q * K^T / sqrt(d_k)
        Tensor K_T({mha.d_k, seq_len_kv});
        transpose(K, K_T, mha.d_k, seq_len_kv);

        Tensor raw_scores({seq_len_q, seq_len_kv});
        matmul(Q, K_T, raw_scores, seq_len_q, mha.d_k, seq_len_kv);

        for (int i = 0; i < seq_len_q * seq_len_kv; i++) {
            raw_scores.data[i] /= scale;
        }

        softmax_row(raw_scores, seq_len_q, seq_len_kv);
        scores.resize(1);
        scores[0] = raw_scores;

        // Saida
        Tensor output({seq_len_q, mha.d_v});
        matmul(raw_scores, V, output, seq_len_q, seq_len_kv, mha.d_v);

        // Projetar
        Tensor final_out({seq_len_q, mha.d_model});
        matmul(output, mha.W_o, final_out, seq_len_q, mha.n_heads * mha.d_v, mha.d_model);

        return final_out;
    }
};

// ============================================================
// Positional Encoding Sinusoidal
// ============================================================

class PositionalEncoding {
public:
    Tensor pe;  // (max_len x d_model)

    PositionalEncoding(int max_len, int d_model) {
        pe = Tensor({max_len, d_model});

        for (int pos = 0; pos < max_len; pos++) {
            for (int i = 0; i < d_model / 2; i++) {
                float angle = pos / std::pow(10000.0f, (2.0f * i) / d_model);
                pe.at(pos, 2 * i) = std::sin(angle);
                pe.at(pos, 2 * i + 1) = std::cos(angle);
            }
        }
    }

    // Adicionar positional encoding ao input
    // X: (seq_len x d_model)
    Tensor add(const Tensor& X) {
        int seq_len = X.shape[0];
        int d_model = X.shape[1];

        Tensor output = X;
        for (int i = 0; i < seq_len; i++) {
            for (int j = 0; j < d_model; j++) {
                output.at(i, j) += pe.at(i, j);
            }
        }
        return output;
    }
};

// ============================================================
// Exemplo de uso
// ============================================================

void example_attention() {
    std::mt19937 gen(42);

    int seq_len = 5;
    int d_model = 64;
    int n_heads = 8;

    // Input: 5 tokens, 64 dimensoes
    Tensor X({seq_len, d_model});
    std::normal_distribution<float> dist(0.0f, 1.0f);
    for (float& val : X.data) val = dist(gen);

    // Adicionar positional encoding
    PositionalEncoding pe(100, d_model);
    Tensor X_pe = pe.add(X);

    // Self-Attention
    SelfAttention sa(d_model, n_heads);
    sa.init_weights(gen);

    std::vector<Tensor> scores;
    Tensor output = sa.forward(X_pe, scores);

    // Exibir scores de attention
    std::cout << "Attention weights (head 0):" << std::endl;
    for (int i = 0; i < seq_len; i++) {
        for (int j = 0; j < seq_len; j++) {
            std::cout << scores[0].at(i, j) << " ";
        }
        std::cout << std::endl;
    }
}

#endif // ATTENTION_H
```

---

## 10. Implementacao em Rust

```rust
// attention.rs - Mecanismo de Attention do Zero em Rust
// Implementacao completa sem bibliotecas externas

use std::f32;

// ============================================================
// Tensor basico
// ============================================================

#[derive(Clone, Debug)]
pub struct Tensor {
    pub data: Vec<f32>,
    pub shape: Vec<usize>,
}

impl Tensor {
    pub fn new(shape: Vec<usize>) -> Self {
        let total: usize = shape.iter().product();
        Tensor {
            data: vec![0.0; total],
            shape,
        }
    }

    pub fn zeros(shape: Vec<usize>) -> Self {
        Self::new(shape)
    }

    pub fn from_vec(shape: Vec<usize>, data: Vec<f32>) -> Self {
        assert_eq!(shape.iter().product::<usize>(), data.len());
        Tensor { data, shape }
    }

    pub fn randn(shape: Vec<usize>, scale: f32) -> Self {
        let total: usize = shape.iter().product();
        let mut data = vec![0.0f32; total];
        for val in data.iter_mut() {
            *val = rand_f32() * scale;
        }
        Tensor { data, shape }
    }

    // Acesso 2D
    pub fn get(&self, i: usize, j: usize) -> f32 {
        self.data[i * self.shape[1] + j]
    }

    pub fn set(&mut self, i: usize, j: usize, val: f32) {
        self.data[i * self.shape[1] + j] = val;
    }

    pub fn zero(&mut self) {
        self.data.iter_mut().for_each(|v| *v = 0.0);
    }
}

fn rand_f32() -> f32 {
    // LCG simples para demo (nao-producao)
    static mut STATE: u32 = 12345;
    unsafe {
        STATE = STATE.wrapping_mul(1664525).wrapping_add(1013904223);
        (STATE as f32) / (u32::MAX as f32)
    }
}

// ============================================================
// Matmul: C = A * B
// ============================================================

pub fn matmul(a: &Tensor, b: &Tensor, m: usize, k: usize, n: usize) -> Tensor {
    let mut c = Tensor::zeros(vec![m, n]);
    for i in 0..m {
        for j in 0..n {
            let mut sum = 0.0f32;
            for l in 0..k {
                sum += a.get(i, l) * b.get(l, j);
            }
            c.set(i, j, sum);
        }
    }
    c
}

// ============================================================
// Transpor
// ============================================================

pub fn transpose(a: &Tensor, m: usize, n: usize) -> Tensor {
    let mut b = Tensor::zeros(vec![n, m]);
    for i in 0..m {
        for j in 0..n {
            b.set(j, i, a.get(i, j));
        }
    }
    b
}

// ============================================================
// Softmax por linha
// ============================================================

pub fn softmax_row(s: &mut Tensor, n_rows: usize, n_cols: usize) {
    for i in 0..n_rows {
        let mut max_val = f32::NEG_INFINITY;
        for j in 0..n_cols {
            let val = s.get(i, j);
            if val > max_val {
                max_val = val;
            }
        }

        let mut sum_exp = 0.0f32;
        for j in 0..n_cols {
            let val = (s.get(i, j) - max_val).exp();
            s.set(i, j, val);
            sum_exp += val;
        }

        for j in 0..n_cols {
            s.set(i, j, s.get(i, j) / sum_exp);
        }
    }
}

// ============================================================
// Scaled Dot-Product Attention
// ============================================================

pub struct ScaledDotProductAttention;

impl ScaledDotProductAttention {
    pub fn forward(
        q: &Tensor,
        k: &Tensor,
        v: &Tensor,
        scale: f32,
    ) -> (Tensor, Tensor) {
        let seq_len = q.shape[0];
        let d_k = q.shape[1];
        let d_v = v.shape[1];

        // K^T
        let k_t = transpose(k, seq_len, d_k);

        // Scores = Q * K^T
        let mut scores = matmul(q, &k_t, seq_len, d_k, seq_len);

        // Escalar
        for val in scores.data.iter_mut() {
            *val /= scale;
        }

        // Softmax
        softmax_row(&mut scores, seq_len, seq_len);

        // Output = Scores * V
        let output = matmul(&scores, v, seq_len, seq_len, d_v);

        (output, scores)
    }
}

// ============================================================
// Multi-Head Attention
// ============================================================

pub struct MultiHeadAttention {
    pub d_model: usize,
    pub n_heads: usize,
    pub d_k: usize,
    pub d_v: usize,
    pub w_q: Tensor,
    pub w_k: Tensor,
    pub w_v: Tensor,
    pub w_o: Tensor,
}

impl MultiHeadAttention {
    pub fn new(d_model: usize, n_heads: usize) -> Self {
        let d_k = d_model / n_heads;
        let d_v = d_model / n_heads;

        let w_q = Tensor::randn(vec![d_model, d_k], 0.1);
        let w_k = Tensor::randn(vec![d_model, d_k], 0.1);
        let w_v = Tensor::randn(vec![d_model, d_v], 0.1);
        let w_o = Tensor::randn(vec![n_heads * d_v, d_model], 0.1);

        MultiHeadAttention {
            d_model,
            n_heads,
            d_k,
            d_v,
            w_q,
            w_k,
            w_v,
            w_o,
        }
    }

    pub fn forward(&self, x: &Tensor) -> (Tensor, Vec<Tensor>) {
        let seq_len = x.shape[0];
        let scale = (self.d_k as f32).sqrt();

        // Projetar
        let q = matmul(x, &self.w_q, seq_len, self.d_model, self.d_k);
        let k = matmul(x, &self.w_k, seq_len, self.d_model, self.d_k);
        let v = matmul(x, &self.w_v, seq_len, self.d_model, self.d_v);

        // Processar cada head
        let mut concat = Tensor::zeros(vec![seq_len, self.n_heads * self.d_v]);
        let mut all_scores = Vec::new();

        for h in 0..self.n_heads {
            // Extrair slice para head h
            let mut q_h = Tensor::zeros(vec![seq_len, self.d_k]);
            let mut k_h = Tensor::zeros(vec![seq_len, self.d_k]);
            let mut v_h = Tensor::zeros(vec![seq_len, self.d_v]);

            for i in 0..seq_len {
                for j in 0..self.d_k {
                    q_h.set(i, j, q.get(i, h * self.d_k + j));
                    k_h.set(i, j, k.get(i, h * self.d_k + j));
                }
                for j in 0..self.d_v {
                    v_h.set(i, j, v.get(i, h * self.d_v + j));
                }
            }

            let (head_out, scores) = ScaledDotProductAttention::forward(
                &q_h, &k_h, &v_h, scale,
            );
            all_scores.push(scores);

            // Concatenar
            for i in 0..seq_len {
                for j in 0..self.d_v {
                    concat.set(i, h * self.d_v + j, head_out.get(i, j));
                }
            }
        }

        let output = matmul(&concat, &self.w_o, seq_len, self.n_heads * self.d_v, self.d_model);

        (output, all_scores)
    }
}

// ============================================================
// Positional Encoding Sinusoidal
// ============================================================

pub struct PositionalEncoding {
    pub pe: Tensor,
}

impl PositionalEncoding {
    pub fn new(max_len: usize, d_model: usize) -> Self {
        let mut pe = Tensor::zeros(vec![max_len, d_model]);

        for pos in 0..max_len {
            for i in 0..d_model / 2 {
                let angle = pos as f32 / 10000f32.powf(2.0 * i as f32 / d_model as f32);
                pe.set(pos, 2 * i, angle.sin());
                pe.set(pos, 2 * i + 1, angle.cos());
            }
        }

        PositionalEncoding { pe }
    }

    pub fn add(&self, x: &Tensor) -> Tensor {
        let seq_len = x.shape[0];
        let d_model = x.shape[1];
        let mut output = x.clone();

        for i in 0..seq_len {
            for j in 0..d_model {
                output.data[i * d_model + j] += self.pe.get(i, j);
            }
        }

        output
    }
}

// ============================================================
// Self-Attention wrapper
// ============================================================

pub struct SelfAttention {
    pub mha: MultiHeadAttention,
}

impl SelfAttention {
    pub fn new(d_model: usize, n_heads: usize) -> Self {
        SelfAttention {
            mha: MultiHeadAttention::new(d_model, n_heads),
        }
    }

    pub fn forward(&self, x: &Tensor) -> (Tensor, Vec<Tensor>) {
        self.mha.forward(x)
    }
}

// ============================================================
// Cross-Attention
// ============================================================

pub struct CrossAttention {
    pub mha: MultiHeadAttention,
}

impl CrossAttention {
    pub fn new(d_model: usize, n_heads: usize) -> Self {
        CrossAttention {
            mha: MultiHeadAttention::new(d_model, n_heads),
        }
    }

    pub fn forward(&self, q_source: &Tensor, kv_target: &Tensor) -> (Tensor, Vec<Tensor>) {
        let seq_len_q = q_source.shape[0];
        let seq_len_kv = kv_target.shape[0];
        let scale = (self.mha.d_k as f32).sqrt();

        // Projetar Q de q_source
        let q = matmul(q_source, &self.mha.w_q, seq_len_q, self.mha.d_model, self.mha.d_k);

        // Projetar K e V de kv_target
        let k = matmul(kv_target, &self.mha.w_k, seq_len_kv, self.mha.d_model, self.mha.d_k);
        let v = matmul(kv_target, &self.mha.w_v, seq_len_kv, self.mha.d_model, self.mha.d_v);

        // Scores
        let k_t = transpose(&k, seq_len_kv, self.mha.d_k);
        let mut scores = matmul(&q, &k_t, seq_len_q, self.mha.d_k, seq_len_kv);

        for val in scores.data.iter_mut() {
            *val /= scale;
        }

        softmax_row(&mut scores, seq_len_q, seq_len_kv);

        let head_out = matmul(&scores, &v, seq_len_q, seq_len_kv, self.mha.d_v);
        let output = matmul(&head_out, &self.mha.w_o, seq_len_q, self.mha.n_heads * self.mha.d_v, self.mha.d_model);

        (output, vec![scores])
    }
}

// ============================================================
// Exemplo de uso
// ============================================================

pub fn example_attention() {
    let seq_len = 5;
    let d_model = 64;
    let n_heads = 8;

    // Input aleatorio
    let x = Tensor::randn(vec![seq_len, d_model], 1.0);

    // Positional encoding
    let pe = PositionalEncoding::new(100, d_model);
    let x_pe = pe.add(&x);

    // Self-Attention
    let sa = SelfAttention::new(d_model, n_heads);
    let (output, scores) = sa.forward(&x_pe);

    println!("Output shape: {:?}", output.shape);
    println!("Number of heads: {}", scores.len());

    // Exibir weights da head 0
    println!("Attention weights (head 0):");
    for i in 0..seq_len {
        for j in 0..seq_len {
            print!("{:.3} ", scores[0].get(i, j));
        }
        println!();
    }
}

fn main() {
    example_attention();
}
```

---

## 11. Implementacao em Fortran

```fortran
! attention.f90 - Mecanismo de Attention do Zero em Fortran
! Implementacao completa sem bibliotecas externas

module attention_mod
    implicit none
    integer, parameter :: sp = kind(0.0)
    real(sp), parameter :: PI = 3.14159265358979323846_sp

contains

    ! ============================================================
    ! Matmul: C = A * B
    ! A: (m x k), B: (k x n), C: (m x n)
    ! ============================================================
    subroutine matmul_2d(A, B, C, m, k, n)
        integer, intent(in) :: m, k, n
        real(sp), intent(in) :: A(m, k), B(k, n)
        real(sp), intent(out) :: C(m, n)
        integer :: i, j, l

        C = 0.0_sp
        do i = 1, m
            do j = 1, n
                do l = 1, k
                    C(i, j) = C(i, j) + A(i, l) * B(l, j)
                end do
            end do
        end do
    end subroutine matmul_2d

    ! ============================================================
    ! Transpor: B = A^T
    ! A: (m x n), B: (n x m)
    ! ============================================================
    subroutine transpose_2d(A, B, m, n)
        integer, intent(in) :: m, n
        real(sp), intent(in) :: A(m, n)
        real(sp), intent(out) :: B(n, m)
        integer :: i, j

        do i = 1, m
            do j = 1, n
                B(j, i) = A(i, j)
            end do
        end do
    end subroutine transpose_2d

    ! ============================================================
    ! Softmax por linha (com estabilidade numerica)
    ! ============================================================
    subroutine softmax_row(S, n_rows, n_cols)
        integer, intent(in) :: n_rows, n_cols
        real(sp), intent(inout) :: S(n_rows, n_cols)
        real(sp) :: max_val, sum_exp
        integer :: i, j

        do i = 1, n_rows
            ! Encontrar max
            max_val = -huge(1.0_sp)
            do j = 1, n_cols
                if (S(i, j) > max_val) max_val = S(i, j)
            end do

            ! Calcular exp e soma
            sum_exp = 0.0_sp
            do j = 1, n_cols
                S(i, j) = exp(S(i, j) - max_val)
                sum_exp = sum_exp + S(i, j)
            end do

            ! Normalizar
            do j = 1, n_cols
                S(i, j) = S(i, j) / sum_exp
            end do
        end do
    end subroutine softmax_row

    ! ============================================================
    ! Scaled Dot-Product Attention
    ! ============================================================
    subroutine scaled_dot_product_attention(Q, K, V, seq_len, d_k, d_v, output, scores)
        integer, intent(in) :: seq_len, d_k, d_v
        real(sp), intent(in) :: Q(seq_len, d_k), K(seq_len, d_k), V(seq_len, d_v)
        real(sp), intent(out) :: output(seq_len, d_v), scores(seq_len, seq_len)
        real(sp) :: K_T(d_k, seq_len), scale
        integer :: i, j

        scale = sqrt(real(d_k, sp))

        ! K^T
        call transpose_2d(K, K_T, seq_len, d_k)

        ! Scores = Q * K^T
        call matmul_2d(Q, K_T, scores, seq_len, d_k, seq_len)

        ! Escalar
        scores = scores / scale

        ! Softmax
        call softmax_row(scores, seq_len, seq_len)

        ! Output = Scores * V
        call matmul_2d(scores, V, output, seq_len, seq_len, d_v)
    end subroutine scaled_dot_product_attention

    ! ============================================================
    ! Multi-Head Attention
    ! ============================================================
    subroutine multi_head_attention(X, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, output, all_scores)
        integer, intent(in) :: seq_len, d_model, n_heads
        real(sp), intent(in) :: X(seq_len, d_model)
        real(sp), intent(in) :: W_Q(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_K(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_V(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_O(d_model, d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        real(sp), intent(out) :: all_scores(n_heads, seq_len, seq_len)
        integer :: d_k, d_v, h, i, j
        real(sp) :: Q(seq_len, d_model/n_heads)
        real(sp) :: K(seq_len, d_model/n_heads)
        real(sp) :: V(seq_len, d_model/n_heads)
        real(sp) :: head_out(seq_len, d_model/n_heads)
        real(sp) :: concat(seq_len, d_model)
        real(sp) :: scores(seq_len, seq_len)

        d_k = d_model / n_heads
        d_v = d_model / n_heads

        ! Projetar Q, K, V
        call matmul_2d(X, W_Q, Q, seq_len, d_model, d_k)
        call matmul_2d(X, W_K, K, seq_len, d_model, d_k)
        call matmul_2d(X, W_V, V, seq_len, d_model, d_v)

        ! Processar cada head
        concat = 0.0_sp
        do h = 1, n_heads
            ! Extrair colunas para head h
            ! (na Fortran, coluna h*d_k+1 ate (h+1)*d_k)
            ! Nota: usamos Q(:, (h-1)*d_k+1 : h*d_k)

            call scaled_dot_product_attention( &
                Q(:, (h-1)*d_k+1:h*d_k), &
                K(:, (h-1)*d_k+1:h*d_k), &
                V(:, (h-1)*d_v+1:h*d_v), &
                seq_len, d_k, d_v, head_out, scores)

            all_scores(h, :, :) = scores

            ! Concatenar
            concat(:, (h-1)*d_v+1:h*d_v) = head_out
        end do

        ! Projecao final
        call matmul_2d(concat, W_O, output, seq_len, d_model, d_model)
    end subroutine multi_head_attention

    ! ============================================================
    ! Positional Encoding Sinusoidal
    ! ============================================================
    subroutine positional_encoding(max_len, d_model, PE)
        integer, intent(in) :: max_len, d_model
        real(sp), intent(out) :: PE(max_len, d_model)
        real(sp) :: angle
        integer :: pos, i

        do pos = 1, max_len
            do i = 1, d_model / 2
                angle = real(pos - 1, sp) / (10000.0_sp ** (2.0_sp * real(i - 1, sp) / real(d_model, sp)))
                PE(pos, 2*i-1) = sin(angle)
                PE(pos, 2*i) = cos(angle)
            end do
        end do
    end subroutine positional_encoding

    ! ============================================================
    ! Adicionar positional encoding
    ! ============================================================
    subroutine add_positional_encoding(X, PE, seq_len, d_model, output)
        integer, intent(in) :: seq_len, d_model
        real(sp), intent(in) :: X(seq_len, d_model), PE(seq_len, d_model)
        real(sp), intent(out) :: output(seq_len, d_model)

        output = X + PE
    end subroutine add_positional_encoding

    ! ============================================================
    ! Self-Attention wrapper
    ! ============================================================
    subroutine self_attention(X, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, output, all_scores)
        integer, intent(in) :: seq_len, d_model, n_heads
        real(sp), intent(in) :: X(seq_len, d_model)
        real(sp), intent(in) :: W_Q(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_K(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_V(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_O(d_model, d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        real(sp), intent(out) :: all_scores(n_heads, seq_len, seq_len)

        call multi_head_attention(X, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, output, all_scores)
    end subroutine self_attention

    ! ============================================================
    ! Cross-Attention
    ! ============================================================
    subroutine cross_attention(Q_src, KV_tgt, seq_len_q, seq_len_kv, d_model, n_heads, &
                               W_Q, W_K, W_V, W_O, output, scores)
        integer, intent(in) :: seq_len_q, seq_len_kv, d_model, n_heads
        real(sp), intent(in) :: Q_src(seq_len_q, d_model)
        real(sp), intent(in) :: KV_tgt(seq_len_kv, d_model)
        real(sp), intent(in) :: W_Q(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_K(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_V(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_O(d_model, d_model)
        real(sp), intent(out) :: output(seq_len_q, d_model)
        real(sp), intent(out) :: scores(seq_len_q, seq_len_kv)
        integer :: d_k, d_v
        real(sp) :: Q(seq_len_q, d_model/n_heads)
        real(sp) :: K(seq_len_kv, d_model/n_heads)
        real(sp) :: V(seq_len_kv, d_model/n_heads)
        real(sp) :: head_out(seq_len_q, d_model/n_heads)
        real(sp) :: concat(seq_len_q, d_model)
        real(sp) :: K_T(d_model/n_heads, seq_len_kv), scale
        integer :: h

        d_k = d_model / n_heads
        d_v = d_model / n_heads
        scale = sqrt(real(d_k, sp))

        ! Projetar Q de Q_src
        call matmul_2d(Q_src, W_Q, Q, seq_len_q, d_model, d_k)

        ! Projetar K e V de KV_tgt
        call matmul_2d(KV_tgt, W_K, K, seq_len_kv, d_model, d_k)
        call matmul_2d(KV_tgt, W_V, V, seq_len_kv, d_model, d_v)

        ! Scores = Q * K^T / scale
        call transpose_2d(K, K_T, seq_len_kv, d_k)
        call matmul_2d(Q, K_T, scores, seq_len_q, d_k, seq_len_kv)
        scores = scores / scale

        ! Softmax
        call softmax_row(scores, seq_len_q, seq_len_kv)

        ! Output = scores * V
        call matmul_2d(scores, V, head_out, seq_len_q, seq_len_kv, d_v)

        ! Concatenar e projetar
        ! Para simplificar, usamos apenas 1 head aqui
        concat = 0.0_sp
        concat(:, 1:d_v) = head_out

        call matmul_2d(concat, W_O, output, seq_len_q, d_model, d_model)
    end subroutine cross_attention

end module attention_mod

! ============================================================
! Programa principal de exemplo
! ============================================================
program attention_example
    use attention_mod
    implicit none

    integer, parameter :: seq_len = 5, d_model = 64, n_heads = 8
    integer, parameter :: d_k = d_model / n_heads, d_v = d_model / n_heads
    real(sp) :: X(seq_len, d_model), X_pe(seq_len, d_model)
    real(sp) :: PE(100, d_model)
    real(sp) :: W_Q(d_model, d_k), W_K(d_model, d_k)
    real(sp) :: W_V(d_model, d_v), W_O(d_model, d_model)
    real(sp) :: output(seq_len, d_model)
    real(sp) :: all_scores(n_heads, seq_len, seq_len)
    integer :: i, j, h

    ! Inicializar seed aleatoria
    call random_seed()

    ! Gerar input aleatorio
    call random_number(X)

    ! Gerar positional encoding
    call positional_encoding(100, d_model, PE)

    ! Adicionar PE ao input
    call add_positional_encoding(X, PE, seq_len, d_model, X_pe)

    ! Inicializar pesos aleatoriamente
    call random_number(W_Q)
    call random_number(W_K)
    call random_number(W_V)
    call random_number(W_O)
    W_Q = W_Q - 0.5_sp
    W_K = W_K - 0.5_sp
    W_V = W_V - 0.5_sp
    W_O = W_O - 0.5_sp

    ! Self-Attention
    call self_attention(X_pe, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, output, all_scores)

    ! Exibir resultados
    print *, "Self-Attention output shape:", shape(output)
    print *, ""
    print *, "Attention weights (head 1):"
    h = 1
    do i = 1, seq_len
        do j = 1, seq_len
            write(*, '(F8.4)', advance='no') all_scores(h, i, j)
        end do
        print *, ""
    end do

end program attention_example
```

---

## 12. Analise de Complexidade

### 12.1 Complexidade Computacional

```text
Complexidade do Scaled Dot-Product Attention:
===============================================

1. Calculo de scores:
   S = Q * K^T
   Q: (n x d_k), K: (n x d_k)
   Resultado: (n x n)
   Complexidade: O(n^2 * d_k)

2. Softmax:
   Para cada linha (n linhas):
     - Encontrar max: O(n)
     - Calcular exp: O(n)
     - Somar e normalizar: O(n)
   Total: O(n^2)

3. Multiplicacao por V:
   A * V
   A: (n x n), V: (n x d_v)
   Resultado: (n x d_v)
   Complexidade: O(n^2 * d_v)

Total: O(n^2 * d_k + n^2 * d_v) = O(n^2 * d)

Para Multi-Head com h heads:
  - h heads paralelas, cada uma O(n^2 * d/h)
  - Concatenacao: O(n * d)
  - Projecao W_o: O(n * d^2)
  Total: O(n^2 * d + n * d^2)

Quando n > d: O(n^2 * d) domina
Quando d > n: O(n * d^2) domina
```

### 12.2 Complexidade de Memoria

```text
Memoria do Attention:
=======================

1. Matriz de scores: O(n^2) floats
   Para n = 1000: 4 MB
   Para n = 10000: 400 MB
   Para n = 100000: 40 GB  <- PROBLEMA

2. Pesos intermediarios: O(n * d) por tensor
   Q, K, V, output: 4 * n * d floats

3. Gradientes: O(n^2 + n * d) durante treinamento

Problema: O(n^2) e proibitivo para sequencias longas
Solucao: Sparse attention, linear attention, etc.
```

### 12.3 Comparacao com RNNs

```text
Comparacao Attention vs RNN:
==============================

                  RNN          Attention
Tempo por camada  O(n * d^2)   O(n^2 * d + n * d^2)
Paralelizavel     Nao           Sim (totalmente)
Acesso a historio O(1) por passo O(n) por passo (via attention)
Memoria          O(d)          O(n^2 + n * d)
Gradiente        O(n) passos    O(1) caminho direto

Vantagens do Attention:
  + Paralelizavel (GPU-friendly)
  + Caminho direto para gradientes (sem vanishing)
  + Captura dependencias de longo prazo
  + Interpretabilidade (attention weights)

Desvantagens:
  - O(n^2) em memoria
  - O(n^2) em tempo para sequencias longas
  - Nao tem nocao natural de ordem (precisa de PE)
```

---

## 13. Visualizacao de Attention Weights

### 13.1 Como Interpretar

```text
Interpretacao dos Pesos:
==========================

Para a frase "O gato comeu o peixe":

Matriz de attention (5x5):
         O    gato  comeu  o    peixe
O     [ 0.1   0.7   0.05  0.1  0.05 ]
gato  [ 0.1   0.1   0.6   0.1  0.1  ]
comeu [ 0.1   0.5   0.1   0.1  0.2  ]
o     [ 0.1   0.1   0.05  0.1  0.65 ]
peixe [ 0.05  0.1   0.4   0.05 0.4  ]

Leitura:
  - "O" (pos 0): foca em "gato" (0.7) -> artigo do sujeito
  - "gato": foca em "comeu" (0.6) -> sujeito-verbo
  - "comeu": foca em "gato" (0.5) e "peixe" (0.2) -> verbo com sujeito e objeto
  - "o": foca em "peixe" (0.65) -> artigo do objeto
  - "peixe": foca em "comeu" (0.4) e "peixe" (0.4) -> objeto e reflexao
```

### 13.2 Metodos de Visualizacao

```text
Metodos de Visualizacao:
==========================

1. Heatmap (mais comum):
   - Cada celula = cor baseada no peso
   - Mais escuro = mais atencao
   - Eixo X: posicao da key (de onde vem)
   - Eixo Y: posicao da query (para quem vai)

2. Arrows/Linhas:
   - Linhas conectam posicoes
   - Espessura = peso de attention
   - Mais grosso = mais atencao

3. Grafos de Atencao:
   - Nos = tokens
   - Arestas = pesos (espessura = peso)
   - Util para ver padroes globais

4. Attention Rollout:
   - Agrega attention de multiplas camadas
   - Mostra atencao acumulada
   - Mais fiel a importancia real

5. Attention Flow:
   - Fluxo maximo entre posicoes
   - Caminho de maior peso
   - Util para rastrear informacao
```

### 13.3 Padroes Comuns

```text
Padroes Tipicos de Attention:
===============================

1. Sintatico:
   - Sujeito <-> Verbo
   - Substantivo <-> Adjetivo
   - Verbo <-> Objeto

2. Semantico:
   - Pronome <-> Referente ("ele" -> "gato")
   - Sinonimos -> conceitos similares

3. Posicional:
   - Tokens proximos tendem a ter mais atencao
   - Mas attention pode "pular" tokens

4. Hierarquico:
   - Camadas baixas: atencao local
   - Camadas altas: atencao global
```

---

## 14. Exemplo: Attention em Sequencia de Texto

### 14.1 Pipeline Completo

```text
Pipeline de Attention para Texto:
===================================

1. Tokenizacao:
   "O gato comeu o peixe" -> ["O", "gato", "comeu", "o", "peixe"]
   Cada token -> indice inteiro: [0, 1, 2, 3, 4]

2. Embedding:
   Indice -> vetor denso: [0] -> [0.12, -0.45, 0.78, ...]
   Dimensao: d_model (ex: 64)

3. Positional Encoding:
   Adicionar PE sinusoidal ao embedding
   [0.12, -0.45, 0.78, ...] + [0.0, 1.0, 0.0, ...]

4. Self-Attention:
   Input: (5 x 64)
   Q, K, V via projecoes lineares
   Scores: (5 x 5) -> softmax -> pesos
   Output: (5 x 64) representacoes contextuais

5. Feed-Forward (opcional neste exemplo):
   Transformacao nao-linear por posicao
   Output: (5 x 64)

6. Saida:
   Cada token agora tem representacao contextual
   "gato" agora sabe que e sujeito de "comeu"
```

### 14.2 Exemplo Numerico Completo

```text
Exemplo Numerico Simplificado:
================================

Frase: "eu gosto de programar"
Tokens: ["eu", "gosto", "de", "programar"]
Indices: [0, 1, 2, 3]

Embeddings (d_model = 4, simplificado):
  "eu":        [1.0, 0.0, 0.0, 0.0]
  "gosto":     [0.0, 1.0, 0.0, 0.0]
  "de":        [0.0, 0.0, 1.0, 0.0]
  "programar": [0.0, 0.0, 0.0, 1.0]

Positional Encoding (d_model = 4):
  pos 0: [sin(0), cos(0), sin(0), cos(0)] = [0, 1, 0, 1]
  pos 1: [sin(1), cos(1), sin(0.01), cos(0.01)] = [0.84, 0.54, 0.01, 1.0]
  pos 2: [sin(2), cos(2), sin(0.02), cos(0.02)] = [0.91, -0.42, 0.02, 1.0]
  pos 3: [sin(3), cos(3), sin(0.03), cos(0.03)] = [0.14, -0.99, 0.03, 1.0]

X = Embeddings + PE:
  "eu":        [1.00, 1.00, 0.00, 1.00]
  "gosto":     [0.84, 1.54, 0.01, 1.00]
  "de":        [0.91, -0.42, 1.02, 1.00]
  "programar": [0.14, -0.99, 0.03, 2.00]

Pesos W_q, W_k, W_v (simplificados, 4x2):
  W_q = [[0.5, 0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]
  W_k = [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.5, -0.5]]
  W_v = [[0.5, 0.0], [0.0, 0.5], [0.5, 0.5], [0.0, 0.5]]

Q = X * W_q (4x4 * 4x2 = 4x2):
  "eu":        [0.50, 1.00]
  "gosto":     [0.67, 0.42]
  "de":        [0.25, 0.72]
  "programar": [-0.43, 0.93]

K = X * W_k:
  "eu":        [1.00, 0.50]
  "gosto":     [0.42, 1.17]
  "de":        [0.88, 0.24]
  "programar": [0.56, 0.58]

V = X * W_v:
  "eu":        [0.50, 0.50]
  "gosto":     [0.77, 0.77]
  "de":        [0.96, 0.71]
  "programar": [0.07, 1.00]

Scores = Q * K^T / sqrt(2):
  sqrt(2) = 1.414

  "eu" vs "eu":        (0.50*1.00 + 1.00*0.50)/1.414 = 0.71
  "eu" vs "gosto":     (0.50*0.42 + 1.00*1.17)/1.414 = 0.96
  "eu" vs "de":        (0.50*0.88 + 1.00*0.24)/1.414 = 0.48
  "eu" vs "programar": (0.50*0.56 + 1.00*0.58)/1.414 = 0.61

  (continua para todas as combinacoes...)

  S = [[0.71, 0.96, 0.48, 0.61],
       [0.65, 1.06, 0.45, 0.57],
       [0.52, 0.90, 0.56, 0.58],
       [0.20, 0.37, 0.42, 0.56]]

Softmax(S):
  A = [[0.27, 0.34, 0.21, 0.23],
       [0.24, 0.35, 0.20, 0.22],
       [0.24, 0.33, 0.24, 0.24],
       [0.20, 0.24, 0.26, 0.30]]

Output = A * V:
  "eu" = 0.27*[0.50,0.50] + 0.34*[0.77,0.77] + 0.21*[0.96,0.71] + 0.23*[0.07,1.00]
       = [0.55, 0.72]

  (cada token agora tem representacao CONTEXTUAL)
```

---

## 15. Exercicios

### 15.1 Exercicio Basico

```text
Exercicio 1: Implemente scaled dot-product attention
  - Entrada: Q, K, V de shape (4, 8)
  - Calcule os scores
  - Aplique softmax
  - Retorne o output
  - Verifique que os pesos somam 1 por linha

Exercicio 2: Implemente positional encoding sinusoidal
  - Para d_model = 16, max_len = 50
  - Verifique que PE(pos=0) = [0, 1, 0, 1, ...]
  - Verifique que PE esta em [-1, 1]
```

### 15.2 Exercicio Intermediario

```text
Exercicio 3: Implemente multi-head attention
  - d_model = 32, n_heads = 4
  - Entrada: (8, 32) - 8 tokens
  - Implemente divisao em heads
  - Execute attention paralela
  - Concatene e projete
  - Verifique shape da saida: (8, 32)

Exercicio 4: Compare self-attention vs cross-attention
  - Crie dois inputs diferentes
  - Execute self-attention em cada
  - Execute cross-attention (Q de um, K/V de outro)
  - Compare os pesos de attention
```

### 15.3 Exercicio Avancado

```text
Exercicio 5: Implemente causal masking
  - Adicione mascara triangular superior
  - Verifique que posicoes futuras tem peso 0
  - Teste com frase e veja que cada token so olha para tras

Exercicio 6: Analise de complexidade
  - Meça tempo para differentes tamanhos de sequencia
  - n = [10, 50, 100, 500, 1000]
  - Verifique que tempo cresce O(n^2)
  - Compare com implementacao ingenua vs otimizada
```

---

## 16. Resumo

### 16.1 Conceitos-Chave

```text
Conceitos Essenciais:
=======================

1. Attention: mecanismo para pesar importancia de cada posicao
   - Query: o que estou procurando
   - Key: o que ofereco
   - Value: o conteudo real

2. Scaled Dot-Product:
   Attention(Q,K,V) = softmax(Q*K^T/sqrt(d_k)) * V
   - sqrt(d_k) previne gradientes estourados

3. Multi-Head:
   Multiplas heads paralelas capturam diferentes tipos de relacoes
   Concatenacao combina todas as perspectivas

4. Self-Attention:
   Q, K, V vêm da mesma sequencia
   Cada token olha para todos os outros

5. Cross-Attention:
   Q de uma fonte, K/V de outra
   Usado entre encoder e decoder

6. Positional Encoding:
   Injeta informacao de posicao (attention e permutacao-invariante)
   Sinusoidal ou learned
```

### 16.2 Quando Usar

```text
Quando Usar Attention:
========================

USE attention quando:
  + Precisa capturar dependencias de longo prazo
  + Sequencias sao paralelizaveis (GPU)
  + Interpretabilidade e importante
  + Dados sao sequencias (texto, audio, series temporais)

NAO use attention quando:
  - Sequencias sao muito longas (n > 10000)
  - Memoria e limitada
  - Ordem e mais importante que relacao (RNN pode bastar)
  - Dados sao independentes (MLP pode bastar)
```

---

## 17. Referencias

```text
Referencias:
==============

1. Bahdanau et al., "Neural Machine Translation by Jointly Learning
   to Align and Translate" (2014)

2. Luong et al., "Effective Approaches to Attention-based Neural
   Machine Translation" (2015)

3. Vaswani et al., "Attention Is All You Need" (2017)

4. Xiao et al., "Self-Attention with Relative Position Representations" (2018)

5. Child et al., "Generating Long Sequences with Sparse Transformers" (2019)

6. Beltagy et al., "Longformer: The Long-Document Transformer" (2020)
```

---

## 18. Variantes Avancadas de Attention

### 18.1 Sparse Attention

```text
Sparse Attention:
===================

Problema: attention denso e O(n^2) em tempo e memoria.
Solucao: attention esparso (cada token olha para poucos).

Tipos:
  1. Local/Windowed:
     - Cada token olha para k vizinhos
     - O(n * k) em vez de O(n^2)
     - Perde dependencias de longo prazo

  2. Strided/Dilated:
     - A cada s passos, olha para um token
     - Captura dependencias longas
     - O(n * n/s)

  3. Global Tokens:
     - Alguns tokens olham para todos
     - Outros olham apenas localmente
     - Ex: <[BOS]>, <[EOS]> sao globais

  4. Longformer:
     - Windowed + Global
     - Local: janela de 512 tokens
     - Global: 256 tokens selecionados
     - O(n) para sequencias longas

  5. BigBird:
     - Windowed + Random + Global
     - Random: conexoes aleatorias
     - Prova teorica de universalidade
```

### 18.2 Linear Attention

```text
Linear Attention:
===================

Problema: softmax causa O(n^2).
Solucao: approximar softmax com kernel linear.

Formula:
  Attention(Q,K,V) = phi(Q) * (phi(K)^T * V) / (phi(Q) * phi(K)^T * 1)

Onde phi e uma funcao de feature (ex: elu(x) + 1)

Complexidade:
  - Denso: O(n^2 * d)
  - Linear: O(n * d^2)

Quando d < n: linear e mais rapido

Variantes:
  1. Performers:
     - phi(x) = exp(-x^2/2) * random_features
     - Aproximacao estocastica

  2. Random Feature Attention:
     - Amostra features aleatorias
     - Aproxima kernel de attention

  3. Linear Transformer:
     - phi(x) = elu(x) + 1
     - Associatividade: (A*B)*C = A*(B*C)
```

### 18.3 Flash Attention

```text
Flash Attention:
==================

Otimizacao IO-aware para GPUs modernas.

Problema:
  - Attention precisa de O(n^2) memoria para scores
  - GPU tem pouca SRAM (20MB em A100)
  - HBM e lento (1.5TB/s vs 19TB/s SRAM)

Solucao:
  - Tiling: divide Q, K, V em blocos
  - Calcula attention por bloco
  - Nao materializa matriz n x n completa
  - Mesma saida (exata, nao approximacao)

Algoritmo:
  1. Dividir Q em blocos de B linhas
  2. Para cada bloco Q_i:
     a. Para cada bloco K_j, V_j:
        - Calcular score = Q_i * K_j^T
        - Atualizar saida com softmax online
  3. Concatenar blocos

Ganhos:
  - 2-4x mais rapido
  - Memoria: O(n) em vez de O(n^2)
  - Precisao exata (nao approximacao)

Implementado em:
  - PyTorch 2.0+
  - Triton
  - CUDA custom
```

---

## 19. Attention em Visao Computacional

### 19.1 Self-Attention para Imagens

```text
Self-Attention em Imagens:
============================

Vision Transformer (ViT):
  - Divide imagem em patches (16x16)
  - Cada patch = token (256 pixels -> embedding)
  - Aplica self-attention entre patches
  - 196 patches para imagem 224x224

Atencao por Posicao:
  - Patch (0,0) attende para patch (0,1): vizinho horizontal
  - Patch (0,0) attende para patch (1,0): vizinho vertical
  - Patch (0,0) attende para patch (15,15): canto oposto

Vantagens:
  - Captura dependencias de longo prazo (global)
  - Nao tem bias de convolucao (local)
  - Paralelizavel

Desvantagens:
  - O(n^2) onde n = numero de patches
  - Para imagem 224x224 com 16x16 patches: n=196
  - Para imagem 1024x1024: n=4096 (muito caro)
```

### 19.2 Swin Transformer

```text
Swin Transformer:
====================

Solucao para attention O(n^2) em imagens.

Ideias:
  1. Window Attention:
     - Divide imagem em janelas 7x7
     - Attention APENAS dentro de cada janela
     - O(n) em vez de O(n^2)

  2. Shifted Windows:
     - Alterna janelas entre camadas
     - Conecta informacao entre janelas
     - Hierarquia de features

  3. Hierarquico:
     - Stage 1: 56x56 patches, C=96
     - Stage 2: 28x28, C=192
     - Stage 3: 14x14, C=384
     - Stage 4: 7x7, C=768
     - Como CNN (piramide de features)

Resultados:
  - 87.3% top-1 em ImageNet
  - 3x mais rapido que ViT
  - State-of-the-art em deteccao
```

---

## 20. Attention em NLP Moderno

### 20.1 BERT Attention Patterns

```text
Padroes de Attention no BERT:
===============================

Analise por camada:
  - Camadas baixas (1-4):
    * Attention local (vizinhos proximos)
    * Relacao sintatica (sujeito-verbo)
    
  - Camadas medias (5-8):
    * Attention mista (local + global)
    * Relacao semantica (sinonimos)
    
  - Camadas altas (9-12):
    * Attention global
    * Coreferencia (pronome-antecedente)
    * Tarefa especifica

Analise por head:
  - Head 1: Attention ao proximo token
  - Head 2: Attention ao token anterior
  - Head 3: Attention a tokens de mesma POS
  - Head 4: Attention a dependentes sintaticos

Interpretabilidade:
  - Attention weights NAO sao explicacoes fiaveis
  - Correlaciona fracamente com importancia
  - UsarIntegrated Gradients para explicacoes
```

### 20.2 GPT Attention

```text
Attention no GPT:
===================

Padroes emergentes:
  1. Induction Heads:
     - Head que copia padrao A B ... A -> B
     * Essencial para in-context learning
     * Aparece na camada 2-3

  2. Previous Token Head:
     - Sempre attende ao token anterior
     * Copia informacao para proxima posicao

  3. Duplicate Token Head:
     - Detecta tokens duplicados
     * "The the" -> attention forte

 4. Name Mover Head:
     - Move informacao de nome para posicao certa
     * "John said he..." -> "he" attende "John"

In-Context Learning:
  - Aparece com modelos grandes (1B+ params)
  - Nao e programado explicitamente
  - Emerge de attention patterns
```

---

## 21. Otimizacoes de Implementacao

### 21.1 Vectorizacao

```text
Otimizacao: Vectorizacao:
============================

Em vez de loops em C++:
  // Lento
  for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
          scores[i][j] = dot(q[i], k[j]);
      }
  }

Usar operacoes matriciais:
  // Rapido
  scores = Q * K^T;  // BLAS routine

BLAS (Basic Linear Algebra Subprograms):
  - dgemm: matrix multiply
  - dgemv: matrix-vector multiply
  - ddot: dot product
  - Implementado com SIMD, multi-thread

Libraries:
  - OpenBLAS: open source, otimizado
  - Intel MKL: rapido em Intel CPUs
  - cuBLAS: GPU (CUDA)
  - clBLAS: GPU (OpenCL)
```

### 21.2 GPU Optimization

```text
Otimizacao GPU:
=================

1. Memory Coalescing:
   - Threads acessam memoria contigua
   - Melhor throughput
   - Organizar dados por threads

2. Shared Memory:
   - Memoria rapida compartilhada (SM)
   - Cache de tiles de Q, K, V
   - Reduz acessos a global memory

3. Warp-level Primitives:
   - __shfl_down: compartilhar entre threads
   - atomicAdd: operacoes atomicas
   - Melhor para reducoes

4. Tensor Cores (A100):
   - Matmul 4x4 ou 8x8
   - FP16, BF16, INT8
   - 10x mais rapido que CUDA cores

Exemplo CUDA kernel simplificado:
  __global__ void attention_kernel(
      float* Q, float* K, float* V, float* O,
      int n, int d) {
      
      // Shared memory para tiles
      __shared__ float Qs[32][64];
      __shared__ float Ks[32][64];
      
      int row = blockIdx.y * 32 + threadIdx.y;
      int col = blockIdx.x * 32 + threadIdx.x;
      
      // Carregar tiles
      Qs[threadIdx.y][threadIdx.x] = Q[row * d + threadIdx.x];
      Ks[threadIdx.y][threadIdx.x] = K[col * d + threadIdx.x];
      
      __syncthreads();
      
      // Calcular score
      float score = 0;
      for (int i = 0; i < 64; i++) {
          score += Qs[threadIdx.y][i] * Ks[threadIdx.x][i];
      }
      
      // ... softmax e accumulation
  }
```

### 21.3 Mixed Precision

```text
Mixed Precision Training:
===========================

Uso de FP16 (half) e FP32 (float):

  - Pesos: FP32 (master copy)
  - Forward/Backward: FP16 (mais rapido)
  - Accumulation: FP32 (precisao)
  - Pesos atualizados: FP32

Vantagens:
  - 2x menos memoria
  - 2-3x mais rapido em GPUs com tensor cores
  - Mesma precisao (se bem implementado)

Implementacao:
  // Pesos em FP32
  float weights_fp32[N];
  
  // Forward em FP16
  half weights_fp16[N];
  half input_fp16[N];
  half output_fp16[N];
  forward_fp16(weights_fp16, input_fp16, output_fp16);
  
  // Backward em FP16
  half grad_fp16[N];
  backward_fp16(weights_fp16, grad_fp16);
  
  // Update em FP32
  weights_fp32 -= lr * grad_fp32;

Loss Scaling:
  - Multiplicar loss por fator (ex: 1024)
  - Evita underflow de gradientes pequenos
  - Dividir gradiente pelo fator antes de update
```

---

## 22. Attention em Outros Dominios

### 22.1 Audio/Musica

```text
Attention em Audio:
====================

WaveNet:
  - Attention dilatado causal
  - Dilation: 1, 2, 4, 8, 16, ...
  - Alcance exponencial com O(n) parametros
  - Para geracao de audio

Transformer para Audio:
  - Spectrograma como "imagem"
  - Patches de frequencia-tempo
  - Self-attention entre patches
  - Ex: Music Transformer

Jukebox (OpenAI):
  - 3 levels de VQ-VAE
  - Transformer por nivel
  - Gera musicas completas
```

### 22.2 Grafos

```text
Attention em Grafos:
======================

Graph Attention Network (GAT):
  - Para dados em grafos
  - Cada no attende para vizinhos
  - Pesos de attention por aresta

Formula:
  h_i = sigma(sum_{j in N(i)} alpha_{ij} * W * h_j)

  alpha_{ij} = softmax(leaky_relu(a^T [Wh_i || Wh_j]))

Aplicacoes:
  - Classificacao de nos
  - Predicao de arestas
  - Molecular design
  - Social networks
```

### 22.3 Multimodal

```text
Attention Multimodal:
=======================

CLIP (OpenAI):
  - Texto + Imagem
  - Cross-attention entre modalidades
  - Zero-shot classification

DALL-E:
  - Texto -> Imagem
  - Transformer autoregressivo
  - Tokens de imagem e texto juntos

Flamingo (DeepMind):
  - Few-shot visual QA
  - Cross-attention para injetar visual
  - Perceiver Resampler

 unified-IO:
  - Todos modalidades
  - Texto, imagem, audio, acoes
  - Transformer unico
```

---

## 23. Tendencias e Pesquisa

### 23.1 Modelos de Escala

```text
Escalabilidade do Attention:
==============================

Leis de Escala:
  - Loss ~ N^{-alpha} (power law)
  - alpha ~ 0.07-0.1 para Transformer
  - Mais dados + mais parametros = melhor

GPT-4:
  - ~1.8T parametros (estimativa)
  - MoE (Mixture of Experts)
  - 16 experts por token

PaLM 2:
  - ~340B parametros
  - Melhor que GPT-4 em algumas tasks
  - Efficient attention

Gemini:
  - Multimodal nativo
  - Treinado com texto, imagem, audio, video
  - Contexto de 1M tokens
```

### 23.2 Attention Eficiente

```text
Pesquisa em Attention Eficiente:
==================================

1. Sub-quadratic:
   - Linear attention: O(n)
   - State Space Models: Mamba
   - RWKV: attention linear recorrente

2. Hardware-aware:
   - Flash Attention v2, v3
   - PagedAttention (vLLM)
   - Tensor Core utilization

3. Sparse Patterns:
   - Learning to attend
   - Dynamic sparsity
   - Adaptive computation

4. Hybrid Architectures:
   - Transformer + SSM
   - Transformer + CNN
   - Heterogeneous layers
```

### 23.3 Limitacoes

```text
Limitacoes do Attention:
==========================

1. Quadratic Complexity:
   - O(n^2) em tempo e memoria
   - Sequencias longas (>100k) problematicas
   - Solucoes: sparse, linear, SSM

2. No Inductive Bias:
   - Nao sabe que imagem tem estrutura 2D
   - Nao sabe que texto tem ordem
   - Precisa de PE e muitos dados

3. Interpretabilidade:
   - Attention weights NAO sao explicacoes
   - Correlaciona fracamente com importancia
   - Nao e sufficiente para accountability

4. Computational Cost:
   - Treinar GPT-4: ~$100M
   - Inferencia: $0.01-0.1 por 1k tokens
   - Acessivel apenas para empresas grandes

5. Data hungry:
   - Precisa de muitos dados
   - Transfer learning indispensavel
   - Few-shot nao resolve tudo
```

---

## 24. Glossario

```text
Glossario de Attention:
=========================

Attention: Mecanismo para pesar importancia de posicoes.

Query (Q): O que estou procurando.

Key (K): O que ofereco (indice).

Value (V): O conteudo real transmitido.

Self-Attention: Q, K, V da mesma sequencia.

Cross-Attention: Q de uma fonte, K/V de outra.

Multi-Head: Multiplas heads paralelas de attention.

Scaled Dot-Product: Attention com divisao por sqrt(d_k).

Positional Encoding: Injecao de informacao posicional.

Causal Mask: Impede olhar para tokens futuros.

Attention Weights: Matriz de probabilidades (softmax).

Softmax: Converte scores em probabilidades.

Temperature: Fator de escala no softmax.

Sparse Attention: Attention esparso (O(n*k)).

Linear Attention: Attention O(n) via kernel.

Flash Attention: Otimizacao IO-aware.

RoPE: Rotary Positional Encoding.

ALiBi: Attention with Linear Biases.
```

---

Fim do Capitulo 13 — Mecanismo de Attention
