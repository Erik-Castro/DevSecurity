---
layout: default
title: "14-transformer"
---

# Capitulo 14 — Transformer

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender a evolucao de RNNs para Transformers** — por que o Transformer revolucionou o Deep Learning.
2. **Dominar a arquitetura completa encoder-decoder** — cada componente e seu papel.
3. **Implementar multi-head self-attention** — o bloco construtor fundamental.
4. **Dominar positional encoding** — sinusoidal, learned, e rotary (RoPE).
5. **Implementar feed-forward network** — a camada MLP interna do Transformer.
6. **Dominar layer normalization** — pre-norm vs post-norm, e por que importa.
7. **Entender residual connections** — como mantem o fluxo de gradiente.
8. **Implementar decoder-only (GPT-style)** — para modelagem de linguagem.
9. **Implementar encoder-only (BERT-style)** — para classificacao e embeddings.
10. **Implementar Transformer completo em C++** — encoder-decoder funcional.
11. **Implementar Transformer em Rust** — com seguranca de memoria.
12. **Implementar Transformer em Fortran** — para performance numerica.
13. **Aplicar Transformer a classificacao** — pipeline completo.
14. **Analisar performance** — tempo, memoria, e escalabilidade.

---

## 1. De RNN a Transformer

### 1.1 Limitacoes das RNNs

As RNNs processam sequencias passo a passo, criando gargalos fundamentais:

```text
Limitacoes das RNNs:
======================

1. Sequencialidade:
   h_1 -> h_2 -> h_3 -> ... -> h_n
   Cada passo DEPENDE do anterior
   NAO paralelizavel (GPU subutilizada)

2. Vanishing Gradient:
   Gradiente precisa atravessar n passos
   Dependencias de longo prazo se perdem
   LSTM/GRU mitigam mas NAO resolvem完全

3. Memoria Limitada:
   Hidden state h_t: vetor fixo (ex: 512 dims)
   Precisa resumir TODA a informacao ate o momento
   Bottleneck informacional inevitavel

4. Computacao Recorrente:
   Tempo: O(n * d^2) por camada
   Memoria: O(d) por passo
   Nao escala bem para sequencias longas
```

### 1.2 A Revolucao do Transformer

```text
O Que o Transformer Mudou:
============================

ANTES (RNN/LSTM):
  - Processa 1 token por vez
  - Memoria: O(d) por step
  - Paralelismo: zero

DEPOIS (Transformer):
  - Processa TODOS os tokens ao mesmo tempo
  - Memoria: O(n^2) mas totalmente paralelo
  - GPU utilization: maxima

O insight fundamental:
  "Nao precisamos de recorrencia para modelar sequencias.
   Attention sozinho captura dependencias de任意 distanciamento."

Resultado:
  - Treinamento 10-100x mais rapido
  - Dependencias de longo prazo perfeitas
  - Base de todos os LLMs modernos
```

### 1.3 Evolucao Historica

```text
Linha do Tempo do Transformer:
================================

2017: "Attention Is All You Need" (Vaswani et al.)
      -> Transformer original: encoder-decoder
      -> Multi-head attention
      -> 64 GPUs, 4 dias de treino

2018: BERT (Devlin et al.)
      -> Encoder-only Transformer
      -> Pre-treinamento bidirecional
      -> Masked Language Modeling

2018: GPT (Radford et al.)
      -> Decoder-only Transformer
      -> Generacao autoregressiva
      -> 117M parametros

2019: GPT-2 (Radford et al.)
      -> 1.5B parametros
      -> Zero-shot learning

2020: GPT-3 (Brown et al.)
      -> 175B parametros
      -> Few-shot learning

2020: Vision Transformer (ViT) (Dosovitskiy et al.)
      -> Transformer para imagens
      -> Patches como tokens

2022: ChatGPT / InstructGPT
      -> RLHF + Transformer
      -> Conversacao natural

2023-2024: GPT-4, Claude, Gemini, LLaMA, Mistral
      -> Multimodal, enormous scale
```

---

## 2. Arquitetura Completa (Encoder-Decoder)

### 2.1 Visao Geral

```text
Arquitetura Transformer:
==========================

ENCODER (esquerda):                    DECODER (direita):
+--------------------------+          +--------------------------+
| Input Embedding          |          | Output Embedding         |
| + Positional Encoding    |          | + Positional Encoding    |
+--------------------------+          +--------------------------+
|                          |          |                          |
| +----------------------+ |          | +----------------------+ |
| | Multi-Head           | |          | | Masked Multi-Head    | |
| | Self-Attention       | |          | | Self-Attention       | |
| +----------------------+ |          | +----------------------+ |
| | Add & Norm           | |          | | Add & Norm           | |
| +----------------------+ |          | +----------------------+ |
| |                      | |          | |                      | |
| +----------------------+ |          | +----------------------+ |
| | Feed-Forward         | |          | | Multi-Head           | |
| | Network              | |          | | Cross-Attention      | |
| +----------------------+ |          | +----------------------+ |
| | Add & Norm           | |          | | Add & Norm           | |
| +----------------------+ |          | +----------------------+ |
|                          |          | |                      | |
| (N camadas)              |          | +----------------------+ |
|                          |          | | Feed-Forward         | |
+--------------------------+          | | Network              | |
                                      | +----------------------+ |
                                      | | Add & Norm           | |
                                      | +----------------------+ |
                                      |                          |
                                      | (N camadas)              |
                                      +--------------------------+
                                               |
                                      +--------------------------+
                                      | Linear + Softmax        |
                                      +--------------------------+

Fluxo:
  1. Encoder processa input (frase em ingles)
  2. Encoder produz representacoes contextuais
  3. Decoder recebe output parcial (frase em portugues)
  4. Decoder usa self-attention (causal) no output
  5. Decoder usa cross-attention com encoder
  6. Linear + Softmax prediz proximo token
```

### 2.2 Componentes Individuais

```text
Componentes do Transformer:
=============================

1. Input/Output Embedding:
   - Converte tokens (inteiros) em vetores (d_model)
   - Matriz de embedding: (vocab_size x d_model)

2. Positional Encoding:
   - Adiciona informacao posicional
   - Sinusoidal (original) ou Learned

3. Multi-Head Self-Attention:
   - Captura dependencias entre tokens
   - h heads paralelas
   - Cada head aprende tipo diferente de relacao

4. Masked Self-Attention (Decoder):
   - Igual ao self-attention
   - MAS com mascara causal
   - Impede olhar para tokens futuros

5. Cross-Attention (Decoder):
   - Q do decoder
   - K, V do encoder
   - Permite ao decoder "buscar" informacao do input

6. Feed-Forward Network:
   - MLP por posicao: FFN(x) = max(0, xW_1 + b_1)W_2 + b_2
   - Dims internas: d_ff (tipicamente 4 * d_model)
   - Transformacao nao-linear independente

7. Add & Norm (Residual + LayerNorm):
   - Residual: output = x + sublayer(x)
   - LayerNorm: normaliza por dimensao
   - Mantem fluxo de gradiente
```

### 2.3 Fluxo Completo

```text
Fluxo de Dados no Transformer:
================================

ENCODER:
  Input: [token_1, token_2, ..., token_n]
  
  1. Embedding: tokens -> (n x d_model)
  2. + Positional Encoding
  3. Para cada camada i (i = 1..N):
     a. Self-Attention (todos vs todos)
     b. Add & Norm
     c. Feed-Forward
     d. Add & Norm
  4. Output: (n x d_model) representacoes contextuais

DECODER (durante treinamento):
  Input: [BOS, token_1, token_2, ..., token_m]
  
  1. Embedding + Positional Encoding
  2. Para cada camada i (i = 1..N):
     a. Masked Self-Attention (so olha para tras)
     b. Add & Norm
     c. Cross-Attention (Q=decoder, K/V=encoder)
     d. Add & Norm
     e. Feed-Forward
     f. Add & Norm
  3. Linear: (m x d_model) -> (m x vocab_size)
  4. Softmax: probabilidades por token
  5. Output: tokens preditos

DECODER (durante inferencia):
  Autoregressivo:
    1. Comeca com BOS
    2. Prediz proximo token
    3. Adiciona token predito a sequencia
    4. Repete ate EOS ou max_len
```

---

## 3. Multi-Head Self-Attention

### 3.1 Revisao Detalhada

```text
Multi-Head Self-Attention:
============================

Equacao:
  MultiHead(Q,K,V) = Concat(head_1, ..., head_h) * W_o
  
  onde head_i = Attention(Q * W_q^i, K * W_k^i, V * W_v^i)

Para Self-Attention:
  Q = K = V = X * W (mesmo input)

Dimensoes:
  X: (n x d_model)
  W_q, W_k: (d_model x d_k) onde d_k = d_model / h
  W_v: (d_model x d_v) onde d_v = d_model / h
  W_o: (h * d_v x d_model)

Saida:
  (n x d_model)

Exemplo:
  d_model = 512, h = 8
  d_k = 64, d_v = 64
  Parametros: 4 * 512^2 = 1,048,576
```

### 3.2 Por Que Multiplas Heads

```text
Por Que Multiplas Heads:
==========================

Uma unica head de attention:
  - Pode focar em UM tipo de relacao por vez
  - Ex: apenas relacao sintatica

Multiplas heads:
  - Cada head pode focar em tipo DIFERENTE
  - Head 1: relacao sintatica (sujeito-verbo)
  - Head 2: relacao semantica (sinonimos)
  - Head 3: relacao posicional (proximo-distante)
  - Head 4: relacao coreferencia (pronome-antecedente)

Concatenacao:
  - Junta todas as perspectivas
  - Projecao final combina informacoes
  - Resultado: representacao rica e multi-facetada
```

### 3.3 Implementacao Detalhada

```text
Implementacao Multi-Head Self-Attention:
==========================================

Passo 1: Projetar Q, K, V
  Q = X * W_q   (n x d_k)
  K = X * W_k   (n x d_k)
  V = X * W_v   (n x d_v)

Passo 2: Reshape para heads
  Q: (n x d_k) -> (h x n x d_k)
  K: (n x d_k) -> (h x n x d_k)
  V: (n x d_v) -> (h x n x d_v)

Passo 3: Calcular attention para cada head (paralelo)
  Para cada head i:
    scores_i = Q_i * K_i^T / sqrt(d_k)   (h x n x n)
    weights_i = softmax(scores_i)          (h x n x n)
    output_i = weights_i * V_i             (h x n x d_v)

Passo 4: Concatenar
  output: (h x n x d_v) -> (n x h * d_v)

Passo 5: Projecao final
  final = output * W_o   (n x d_model)

Parametros por head:
  W_q^i: (d_model x d_k)
  W_k^i: (d_model x d_k)
  W_v^i: (d_model x d_v)
Total: h * (2 * d_model * d_k + d_model * d_v)
     = 3 * d_model^2 (quando d_k = d_v = d_model/h)
```

---

## 4. Positional Encoding (Sinusoidal, Learned)

### 4.1 Positional Encoding Sinusoidal

```text
Positional Encoding Sinusoidal:
=================================

Formula:
  PE(pos, 2i)   = sin(pos / 10000^(2i/d_model))
  PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))

Propriedades:
  1. Cada posicao tem vetor unico
  2. Valores em [-1, 1]
  3. Relacoes relativas preservadas
  4. Generaliza para sequencias mais longas
  5. Sem parametros aprendiveis

Como injetar:
  output = embedding + PE

Por que funciona:
  - PE(pos+k) = T_k(PE(pos)) para algum T_k linear
  - Modelo pode aprender relacoes relativas
  - Frequencias diferentes capturam diferentes escalas
```

### 4.2 Learned Positional Encoding

```text
Learned Positional Encoding:
==============================

Implementacao:
  PE = Embedding(max_seq_len, d_model)
  
  posicao 0 -> embedding[0]
  posicao 1 -> embedding[1]
  ...

Vantagens:
  + Pode capturar padroes complexos
  + Simples de implementar

Desvantagens:
  - Nao generaliza para seq > max_len
  - Mais parametros (max_len * d_model)
  - Precisa de dados para treinar

Usado em:
  BERT (max_len = 512)
  GPT-2 (max_len = 1024)
  GPT-3 (max_len = 2048)
```

### 4.3 Rotary Positional Encoding (RoPE)

```text
RoPE (Rotary Positional Encoding):
====================================

Implementado em LLaMA, PaLM, GPT-4

Idea:
  - Aplica rotacao ao vetor de embedding
  - Angulo de rotacao = f(posicao)
  - Relacao entre dois tokens depende da DISTANCIA

Formula (simplificada):
  Para cada par de dimensoes (2i, 2i+1):
    q'_i = rotate(q_i, theta_i * pos)
    k'_i = rotate(k_i, theta_i * pos)
  
  onde theta_i = 1 / 10000^(2i/d)

Vantagens:
  + Preserva relacoes relativas
  + Mais eficiente que sinusoidal
  + Escala bem para sequencias longas
  + Sem parametros extras
```

---

## 5. Feed-Forward Network

### 5.1 Arquitetura

```text
Feed-Forward Network (FFN):
==============================

Equacao:
  FFN(x) = max(0, x * W_1 + b_1) * W_2 + b_2

Dimensoes:
  x: (n x d_model)
  W_1: (d_model x d_ff)   onde d_ff = 4 * d_model
  W_2: (d_ff x d_model)

Fluxo:
  1. Projetar para dimensao maior: (n x d_model) -> (n x d_ff)
  2. Aplicar ReLU (ou GELU): nao-linearidade
  3. Projetar de volta: (n x d_ff) -> (n x d_model)

Por que d_ff = 4 * d_model:
  - Heuristica do paper original
  - Maior capacidade de representacao
  - Pode ser ajustado conforme necessidade

Exemplo:
  d_model = 512, d_ff = 2048
  Parametros: 512*2048 + 2048*512 = 2,097,152
  (mais que attention: 1,048,576)
```

### 5.2 Variacoes Modernas

```text
Variacoes do FFN:
====================

1. GELU (Gaussian Error Linear Unit):
   GELU(x) = x * Phi(x)
   Onde Phi e CDF da distribuicao normal
   Usado em: BERT, GPT-2, GPT-3

2. SwiGLU (Swish-Gated Linear Unit):
   FFN(x) = (x * W_1) * sigmoid(x * W_1') * W_2
   Usado em: PaLM, LLaMA
   Mais eficiente que ReLU

3. GLU (Gated Linear Unit):
   FFN(x) = (x * W_1) * sigmoid(x * W_1') * W_2
   Variante com gating

4. Sparse FFN:
   So ativa neuronios relevantes
   Mais eficiente para modelos grandes
```

---

## 6. Layer Normalization

### 6.1 O Que e Layer Normalization

```text
Layer Normalization:
======================

Equacao:
  LayerNorm(x) = gamma * (x - mean(x)) / sqrt(var(x) + eps) + beta

Onde:
  mean(x) = media ao longo das dimensoes
  var(x) = variancia ao longo das dimensoes
  gamma, beta: parametros aprendiveis
  eps: constante para estabilidade numerica

Diferenca com Batch Normalization:
  - BatchNorm: normaliza por BATCH (mesma feature em todos os examples)
  - LayerNorm: normaliza por FEATURE (todas as features no mesmo example)

Por que LayerNorm no Transformer:
  - Funciona com batch_size = 1
  - Independente de outros examples no batch
  - Mais estavel para sequencias
```

### 6.2 Pre-Norm vs Post-Norm

```text
Pre-Norm vs Post-Norm:
========================

Post-Norm (original Transformer):
  output = LayerNorm(x + Sublayer(x))

  Problema: gradientes podem explodir
  Solucao: warmup, learning rate scheduling

Pre-Norm (moderno):
  output = x + Sublayer(LayerNorm(x))

  Vantagem: gradientes mais estaveis
  Usado em: GPT-2, GPT-3, LLaMA

Comparacao:
  Post-Norm:
    x -> Sublayer -> Add -> LayerNorm -> output
  
  Pre-Norm:
    x -> LayerNorm -> Sublayer -> Add -> output

Pre-Norm e preferido em modelos modernos
por ser mais estavel durante treinamento.
```

### 6.3 RMSNorm

```text
RMSNorm (Root Mean Square Normalization):
============================================

Equacao:
  RMSNorm(x) = x / sqrt(mean(x^2) + eps) * gamma

Simplificacao do LayerNorm:
  - Nao subtrai media
  - Nao tem bias (beta)
  - Mais rapido de computar

Usado em:
  LLaMA
  GPT-4 (provavelmente)
  Maioria dos modelos modernos

Vantagem:
  - ~10% mais rapido que LayerNorm
  - Resultados comparaveis
```

---

## 7. Residual Connections

### 7.1 O Problema que Resolvem

```text
Problema de Redes Profundas:
==============================

Em redes muito profundas:
  - Gradiente desaparece ou explode
  - Camadas profundas nao aprendem
  - Treinamento estagna

Exemplo:
  Rede com 100 camadas
  Gradiente: dL/dx_0 = prod(dL/dx_i)
  Se cada dL/di < 1: produto -> 0
  Se cada dL/di > 1: produto -> infinito
```

### 7.2 Solucao Residual

```text
Residual Connection:
======================

Equacao:
  output = x + F(x)

onde F(x) e a transformacao (attention ou FFN)

Por que funciona:
  1. Gradiente flui DIRETO pelo skip connection
     d(output)/dx = 1 + dF/dx
     O "1" garante gradiente nao-zero

  2. A rede aprende RESIDUOS
     F(x) = output - x
     Se F(x) = 0, output = x (identidade)
     Facilita aprendizado

  3. Redes podem ser muito profundas
     ResNet (152 camadas) usa residual
     Transformer (96 camadas) usa residual
```

### 7.3 Implementacao

```text
Implementacao Residual:
========================

No Transformer, cada subcamada tem:

  # Subcamada: Attention
  sublayer_output = MultiHeadAttention(LayerNorm(x))
  output = x + sublayer_output  # Residual connection

  # Subcamada: FFN
  sublayer_output = FFN(LayerNorm(output))
  output = output + sublayer_output  # Residual connection

Ou em Pre-Norm:

  # Subcamada: Attention
  normed = LayerNorm(x)
  sublayer_output = MultiHeadAttention(normed)
  output = x + sublayer_output

  # Subcamada: FFN
  normed = LayerNorm(output)
  sublayer_output = FFN(normed)
  output = output + sublayer_output
```

---

## 8. Decoder-Only (GPT-style)

### 8.1 Arquitetura

```text
Decoder-Only Transformer:
===========================

Usado em: GPT, GPT-2, GPT-3, LLaMA, Mistral

Caracteristicas:
  - Apenas decoder (sem encoder)
  - Self-attention com mascara causal
  - Generacao autoregressiva
  - Modelagem de linguagem: P(x_t | x_1, ..., x_{t-1})

Arquitetura:
  Input: tokens anteriores
  
  Para cada camada:
    1. Masked Self-Attention
    2. Add & Norm
    3. Feed-Forward
    4. Add & Norm
  
  Output: logits para proximo token

Parametros:
  GPT-2 small: 117M
  GPT-2 medium: 345M
  GPT-2 large: 774M
  GPT-3: 175B
  LLaMA-7B: 7B
```

### 8.2 Causal Masking

```text
Causal Mask:
==============

No decoder, cada posicao so pode olhar para ANTERIORES:

  Pos 0: [0, -inf, -inf, -inf]
  Pos 1: [0,   0, -inf, -inf]
  Pos 2: [0,   0,   0, -inf]
  Pos 3: [0,   0,   0,   0]

Apos softmax:
  Pos 0: [1.0,  0,    0,    0  ]
  Pos 1: [0.5,  0.5,  0,    0  ]
  Pos 2: [0.3,  0.3,  0.4,  0  ]
  Pos 3: [0.2,  0.2,  0.3,  0.3]

Isso garante:
  - Generacao autoregressiva
  - Nao ha "vazamento" de informacao futura
  - Treinamento e inferencia sao consistentes
```

### 8.3 Treinamento e Inferencia

```text
Treinamento do Decoder-Only:
===============================

1. Teacher Forcing:
   - Input: [BOS, x_1, x_2, ..., x_{n-1}]
   - Target: [x_1, x_2, ..., x_n]
   - Loss: cross-entropy em cada posicao

2. Exemplo:
   Input:  ["<BOS>", "O", "gato", "comeu"]
   Target: ["O", "gato", "comeu", "<EOS>"]
   
   Predicoes:
     pos 0: P("O" | <BOS>)
     pos 1: P("gato" | <BOS>, "O")
     pos 2: P("comeu" | <BOS>, "O", "gato")
     pos 3: P("<EOS>" | <BOS>, "O", "gato", "comeu")

3. Loss total:
   L = -sum(log(P(target_t | context_t)))

Inferencia Autoregressiva:
  1. Input: ["<BOS>"]
  2. Prediz: P(token | <BOS>)
  3. Escolhe: token_1 = argmax ou sample
  4. Input: ["<BOS>", token_1]
  5. Prediz: P(token | <BOS>, token_1)
  6. Repete ate <EOS> ou max_len
```

---

## 9. Encoder-Only (BERT-style)

### 9.1 Arquitetura

```text
Encoder-Only Transformer:
============================

Usado em: BERT, RoBERTa, ALBERT, DeBERTa

Caracteristicas:
  - Apenas encoder (sem decoder)
  - Self-attention bidirecional (sem mascara)
  - Representacoes contextuais
  - Para classificacao, NER, etc.

Arquitetura:
  Input: sequencia completa
  
  Para cada camada:
    1. Self-Attention (bidirecional)
    2. Add & Norm
    3. Feed-Forward
    4. Add & Norm
  
  Output: representacao por token

Diferenca do Decoder:
  - SEM mascara causal
  - Cada token olha para TODOS os outros
  - Bidirecional (passado e futuro)
```

### 9.2 Pre-Treinamento

```text
Pre-Treinamento do BERT:
==========================

1. Masked Language Modeling (MLM):
   - Mascara 15% dos tokens
   - Modelo prediz tokens mascarados
   - Exemplo:
     Input:  "O [MASK] comeu o [MASK]"
     Target: "O gato comeu o peixe"

2. Next Sentence Prediction (NSP):
   - Pares de sentencas
   - Modelo prediz se segunda segue primeira
   - Exemplo:
     Par 1: "O gato comeu. Ele estava faminto." -> IsNext
     Par 2: "O gato comeu. O tempo esta bom." -> NotNext

3. Treinamento:
   - Dados: Wikipedia + BookCorpus
   - 3.3B tokens
   - 40 epochs
   - Batch size: 256
   - Learning rate: 1e-4
```

### 9.3 Fine-Tuning

```text
Fine-Tuning do BERT:
======================

Para Classificacao:
  - Adiciona [CLS] token no inicio
  - Usa representacao do [CLS] como input
  - Adiciona classificador linear
  - Treina com dados rotulados

Para NER:
  - Representacao de cada token
  - Classificador linear por token
  - Prediz label para cada posicao

Para QA:
  - Representacao de pergunta + contexto
  - Classificador para inicio e fim da resposta
  - Prediz span de resposta

Exemplo Fine-Tuning:
  - Base: BERT (pre-treinado)
  - Dados: 1000 exemplos rotulados
  - Epocas: 3-5
  - Learning rate: 2e-5
  - Resultado: modelo especializado
```

---

## 10. Implementacao Completa do Transformer em C++

```cpp
// transformer.h - Transformer Completo do Zero em C++
// Implementacao sem bibliotecas externas

#ifndef TRANSFORMER_H
#define TRANSFORMER_H

#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <numeric>
#include <limits>
#include <iostream>
#include <cassert>
#include <memory>

// ============================================================
// Tensor basico
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

    float& at(int i0) { return data[i0]; }
    float& at(int i0, int i1) { return data[i0 * shape[1] + i1]; }
    float& at(int i0, int i1, int i2) {
        return data[(i0 * shape[1] + i1) * shape[2] + i2];
    }
    float at(int i0) const { return data[i0]; }
    float at(int i0, int i1) const { return data[i0 * shape[1] + i1]; }
    float at(int i0, int i1, int i2) const {
        return data[(i0 * shape[1] + i1) * shape[2] + i2];
    }

    void zero() { std::fill(data.begin(), data.end(), 0.0f); }
};

// ============================================================
// Inicializacao Xavier
// ============================================================

void xavier_init(Tensor& t, std::mt19937& gen) {
    int fan_in = t.shape.size() >= 2 ? t.shape[t.shape.size() - 2] : 1;
    int fan_out = t.shape.size() >= 2 ? t.shape[t.shape.size() - 1] : 1;
    float limit = std::sqrt(6.0f / (fan_in + fan_out));
    std::uniform_real_distribution<float> dist(-limit, limit);
    for (float& val : t.data) val = dist(gen);
}

// ============================================================
// Matmul: C = A * B
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
// Softmax por linha
// ============================================================

void softmax_row(Tensor& S, int n_rows, int n_cols) {
    for (int i = 0; i < n_rows; i++) {
        float max_val = -std::numeric_limits<float>::infinity();
        for (int j = 0; j < n_cols; j++) {
            max_val = std::max(max_val, S.at(i, j));
        }
        float sum_exp = 0.0f;
        for (int j = 0; j < n_cols; j++) {
            S.at(i, j) = std::exp(S.at(i, j) - max_val);
            sum_exp += S.at(i, j);
        }
        for (int j = 0; j < n_cols; j++) {
            S.at(i, j) /= sum_exp;
        }
    }
}

// ============================================================
// Layer Normalization
// ============================================================

class LayerNorm {
public:
    Tensor gamma, beta;
    int d_model;
    float eps;

    LayerNorm(int d_model, float eps = 1e-5f)
        : d_model(d_model), eps(eps) {
        gamma = Tensor({d_model});
        beta = Tensor({d_model});
        // gamma = 1, beta = 0
        for (int i = 0; i < d_model; i++) gamma.at(i) = 1.0f;
    }

    Tensor forward(const Tensor& x) {
        int seq_len = x.shape[0];
        Tensor output = x;

        for (int i = 0; i < seq_len; i++) {
            // Calcular media
            float mean = 0.0f;
            for (int j = 0; j < d_model; j++) {
                mean += x.at(i, j);
            }
            mean /= d_model;

            // Calcular variancia
            float var = 0.0f;
            for (int j = 0; j < d_model; j++) {
                float diff = x.at(i, j) - mean;
                var += diff * diff;
            }
            var /= d_model;

            // Normalizar
            float std_inv = 1.0f / std::sqrt(var + eps);
            for (int j = 0; j < d_model; j++) {
                output.at(i, j) = gamma.at(j) * (x.at(i, j) - mean) * std_inv + beta.at(j);
            }
        }

        return output;
    }
};

// ============================================================
// Positional Encoding Sinusoidal
// ============================================================

class PositionalEncoding {
public:
    Tensor pe;

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
// Multi-Head Attention
// ============================================================

class MultiHeadAttention {
public:
    int d_model, n_heads, d_k, d_v;
    Tensor W_q, W_k, W_v, W_o;

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
        xavier_init(W_q, gen);
        xavier_init(W_k, gen);
        xavier_init(W_v, gen);
        xavier_init(W_o, gen);
    }

    Tensor forward(const Tensor& X, bool causal = false) {
        int seq_len = X.shape[0];
        float scale = std::sqrt(static_cast<float>(d_k));

        // Projetar
        Tensor Q({seq_len, d_k});
        Tensor K({seq_len, d_k});
        Tensor V({seq_len, d_v});
        matmul(X, W_q, Q, seq_len, d_model, d_k);
        matmul(X, W_k, K, seq_len, d_model, d_k);
        matmul(X, W_v, V, seq_len, d_model, d_v);

        // Concatenar heads
        Tensor concat({seq_len, n_heads * d_v});
        concat.zero();

        for (int h = 0; h < n_heads; h++) {
            // Extrair head
            Tensor Q_h({seq_len, d_k}), K_h({seq_len, d_k}), V_h({seq_len, d_v});
            for (int i = 0; i < seq_len; i++) {
                for (int j = 0; j < d_k; j++) {
                    Q_h.at(i, j) = Q.at(i, h * d_k + j);
                    K_h.at(i, j) = K.at(i, h * d_k + j);
                }
                for (int j = 0; j < d_v; j++) {
                    V_h.at(i, j) = V.at(i, h * d_v + j);
                }
            }

            // Scores
            Tensor K_T({d_k, seq_len});
            for (int i = 0; i < seq_len; i++)
                for (int j = 0; j < d_k; j++)
                    K_T.at(j, i) = K_h.at(i, j);

            Tensor scores({seq_len, seq_len});
            matmul(Q_h, K_T, scores, seq_len, d_k, seq_len);

            // Escalar
            for (int i = 0; i < seq_len * seq_len; i++)
                scores.data[i] /= scale;

            // Causal mask
            if (causal) {
                for (int i = 0; i < seq_len; i++) {
                    for (int j = i + 1; j < seq_len; j++) {
                        scores.at(i, j) = -1e9f;
                    }
                }
            }

            // Softmax
            softmax_row(scores, seq_len, seq_len);

            // Multiplicar por V
            Tensor head_out({seq_len, d_v});
            matmul(scores, V_h, head_out, seq_len, seq_len, d_v);

            // Concatenar
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
// Feed-Forward Network
// ============================================================

class FeedForward {
public:
    int d_model, d_ff;
    Tensor W_1, b_1, W_2, b_2;

    FeedForward(int d_model, int d_ff)
        : d_model(d_model), d_ff(d_ff) {
        W_1 = Tensor({d_model, d_ff});
        b_1 = Tensor({d_ff});
        W_2 = Tensor({d_ff, d_model});
        b_2 = Tensor({d_model});
    }

    void init_weights(std::mt19937& gen) {
        xavier_init(W_1, gen);
        xavier_init(W_2, gen);
    }

    Tensor forward(const Tensor& x) {
        int seq_len = x.shape[0];

        // Camada 1: ReLU
        Tensor hidden({seq_len, d_ff});
        matmul(x, W_1, hidden, seq_len, d_model, d_ff);

        for (int i = 0; i < seq_len; i++) {
            for (int j = 0; j < d_ff; j++) {
                hidden.at(i, j) = std::max(0.0f, hidden.at(i, j) + b_1.at(j));
            }
        }

        // Camada 2
        Tensor output({seq_len, d_model});
        matmul(hidden, W_2, output, seq_len, d_ff, d_model);

        for (int i = 0; i < seq_len; i++) {
            for (int j = 0; j < d_model; j++) {
                output.at(i, j) += b_2.at(j);
            }
        }

        return output;
    }
};

// ============================================================
// Transformer Layer
// ============================================================

class TransformerLayer {
public:
    MultiHeadAttention self_attn;
    LayerNorm norm1;
    FeedForward ffn;
    LayerNorm norm2;

    TransformerLayer(int d_model, int n_heads, int d_ff)
        : self_attn(d_model, n_heads),
          norm1(d_model),
          ffn(d_model, d_ff),
          norm2(d_model) {}

    void init_weights(std::mt19937& gen) {
        self_attn.init_weights(gen);
        ffn.init_weights(gen);
    }

    Tensor forward(const Tensor& x, bool causal = false) {
        // Self-Attention + Residual
        Tensor normed = norm1.forward(x);
        Tensor attn_out = self_attn.forward(normed, causal);
        Tensor residual1 = x;
        for (int i = 0; i < x.total_size; i++) {
            residual1.data[i] += attn_out.data[i];
        }

        // FFN + Residual
        Tensor normed2 = norm2.forward(residual1);
        Tensor ffn_out = ffn.forward(normed2);
        Tensor residual2 = residual1;
        for (int i = 0; i < residual1.total_size; i++) {
            residual2.data[i] += ffn_out.data[i];
        }

        return residual2;
    }
};

// ============================================================
// Transformer Encoder
// ============================================================

class TransformerEncoder {
public:
    std::vector<TransformerLayer> layers;
    int d_model;

    TransformerEncoder(int d_model, int n_heads, int d_ff, int n_layers)
        : d_model(d_model) {
        for (int i = 0; i < n_layers; i++) {
            layers.emplace_back(d_model, n_heads, d_ff);
        }
    }

    void init_weights(std::mt19937& gen) {
        for (auto& layer : layers) {
            layer.init_weights(gen);
        }
    }

    Tensor forward(const Tensor& x) {
        Tensor output = x;
        for (auto& layer : layers) {
            output = layer.forward(output, false);
        }
        return output;
    }
};

// ============================================================
// Transformer Decoder
// ============================================================

class TransformerDecoder {
public:
    std::vector<TransformerLayer> self_attn_layers;
    std::vector<TransformerLayer> cross_attn_layers;  // simplificado
    std::vector<FeedForward> ffn_layers;
    std::vector<LayerNorm> norm_layers;
    int d_model, n_heads, d_ff;

    TransformerDecoder(int d_model, int n_heads, int d_ff, int n_layers)
        : d_model(d_model), n_heads(n_heads), d_ff(d_ff) {
        for (int i = 0; i < n_layers; i++) {
            self_attn_layers.emplace_back(d_model, n_heads, d_ff);
            norm_layers.emplace_back(d_model);
        }
    }

    void init_weights(std::mt19937& gen) {
        for (auto& layer : self_attn_layers) {
            layer.init_weights(gen);
        }
    }

    Tensor forward(const Tensor& x, const Tensor& encoder_output) {
        Tensor output = x;

        for (auto& layer : self_attn_layers) {
            // Masked self-attention
            Tensor normed = layer.norm1.forward(output);
            Tensor attn_out = layer.self_attn.forward(normed, true);
            for (int i = 0; i < output.total_size; i++) {
                output.data[i] += attn_out.data[i];
            }

            // FFN
            Tensor normed2 = layer.norm2.forward(output);
            Tensor ffn_out = layer.ffn.forward(normed2);
            for (int i = 0; i < output.total_size; i++) {
                output.data[i] += ffn_out.data[i];
            }
        }

        return output;
    }
};

// ============================================================
// Transformer Completo
// ============================================================

class Transformer {
public:
    TransformerEncoder encoder;
    TransformerDecoder decoder;
    Tensor output_projection;  // (d_model x vocab_size)
    int d_model, vocab_size;

    Transformer(int vocab_size, int d_model, int n_heads,
                int d_ff, int n_layers, int max_len)
        : encoder(d_model, n_heads, d_ff, n_layers),
          decoder(d_model, n_heads, d_ff, n_layers),
          d_model(d_model), vocab_size(vocab_size) {
        output_projection = Tensor({d_model, vocab_size});
    }

    void init_weights(std::mt19937& gen) {
        encoder.init_weights(gen);
        decoder.init_weights(gen);
        xavier_init(output_projection, gen);
    }

    Tensor forward(const Tensor& src, const Tensor& tgt) {
        // Encoder
        Tensor enc_output = encoder.forward(src);

        // Decoder
        Tensor dec_output = decoder.forward(tgt, enc_output);

        // Projecao para vocab
        int tgt_len = tgt.shape[0];
        Tensor logits({tgt_len, vocab_size});
        matmul(dec_output, output_projection, logits, tgt_len, d_model, vocab_size);

        return logits;
    }
};

// ============================================================
// Exemplo: Classificacao com Transformer
// ============================================================

void example_classification() {
    std::mt19937 gen(42);

    int vocab_size = 1000;
    int d_model = 128;
    int n_heads = 4;
    int d_ff = 512;
    int n_layers = 2;
    int seq_len = 10;
    int n_classes = 5;

    // Criar Transformer
    Transformer transformer(vocab_size, d_model, n_heads, d_ff, n_layers, 100);
    transformer.init_weights(gen);

    // Input: 10 tokens
    Tensor input({seq_len});
    std::uniform_int_distribution<int> token_dist(0, vocab_size - 1);
    for (int i = 0; i < seq_len; i++) {
        input.at(i) = static_cast<float>(token_dist(gen));
    }

    // Embedding (simplificado: one-hot -> dense)
    Tensor embedded({seq_len, d_model});
    std::normal_distribution<float> embed_dist(0.0f, 0.1f);
    for (float& val : embedded.data) val = embed_dist(gen);

    // Positional encoding
    PositionalEncoding pe(100, d_model);
    Tensor x_pe = pe.add(embedded);

    // Forward
    Tensor enc_output = transformer.encoder.forward(x_pe);

    // Classificacao: media do output
    Tensor cls_embedding({d_model});
    cls_embedding.zero();
    for (int i = 0; i < seq_len; i++) {
        for (int j = 0; j < d_model; j++) {
            cls_embedding.at(j) += enc_output.at(i, j);
        }
    }
    for (int j = 0; j < d_model; j++) {
        cls_embedding.at(j) /= seq_len;
    }

    // Classificador
    Tensor classifier({d_model, n_classes});
    xavier_init(classifier, gen);
    Tensor logits({n_classes});
    matmul(cls_embedding, classifier, logits, 1, d_model, n_classes);

    // Predicao
    int pred_class = 0;
    float max_logit = logits.at(0);
    for (int i = 1; i < n_classes; i++) {
        if (logits.at(i) > max_logit) {
            max_logit = logits.at(i);
            pred_class = i;
        }
    }

    std::cout << "Classe predita: " << pred_class << std::endl;
}

#endif // TRANSFORMER_H
```

---

## 11. Implementacao em Rust

```rust
// transformer.rs - Transformer Completo do Zero em Rust
// Implementacao sem bibliotecas externas

use std::f32;

// ============================================================
// Tensor
// ============================================================

#[derive(Clone)]
pub struct Tensor {
    pub data: Vec<f32>,
    pub shape: Vec<usize>,
}

impl Tensor {
    pub fn new(shape: Vec<usize>) -> Self {
        let total: usize = shape.iter().product();
        Tensor { data: vec![0.0; total], shape }
    }

    pub fn randn(shape: Vec<usize>, scale: f32) -> Self {
        let total: usize = shape.iter().product();
        let mut data = vec![0.0f32; total];
        for val in data.iter_mut() {
            *val = rand_f32() * scale;
        }
        Tensor { data, shape }
    }

    pub fn get(&self, i: usize, j: usize) -> f32 {
        self.data[i * self.shape[1] + j]
    }

    pub fn set(&mut self, i: usize, j: usize, val: f32) {
        self.data[i * self.shape[1] + j] = val;
    }

    pub fn zero(&mut self) {
        self.data.iter_mut().for_each(|v| *v = 0.0);
    }

    pub fn add_in_place(&mut self, other: &Tensor) {
        for (a, b) in self.data.iter_mut().zip(other.data.iter()) {
            *a += b;
        }
    }
}

fn rand_f32() -> f32 {
    static mut STATE: u32 = 12345;
    unsafe {
        STATE = STATE.wrapping_mul(1664525).wrapping_add(1013904223);
        (STATE as f32) / (u32::MAX as f32)
    }
}

// ============================================================
// Matmul
// ============================================================

pub fn matmul(a: &Tensor, b: &Tensor, m: usize, k: usize, n: usize) -> Tensor {
    let mut c = Tensor::new(vec![m, n]);
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
// Softmax
// ============================================================

pub fn softmax_row(s: &mut Tensor, n_rows: usize, n_cols: usize) {
    for i in 0..n_rows {
        let mut max_val = f32::NEG_INFINITY;
        for j in 0..n_cols {
            let val = s.get(i, j);
            if val > max_val { max_val = val; }
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
// Layer Normalization
// ============================================================

pub struct LayerNorm {
    pub gamma: Vec<f32>,
    pub beta: Vec<f32>,
    pub d_model: usize,
    pub eps: f32,
}

impl LayerNorm {
    pub fn new(d_model: usize) -> Self {
        LayerNorm {
            gamma: vec![1.0; d_model],
            beta: vec![0.0; d_model],
            d_model,
            eps: 1e-5,
        }
    }

    pub fn forward(&self, x: &Tensor) -> Tensor {
        let seq_len = x.shape[0];
        let mut output = x.clone();

        for i in 0..seq_len {
            let mut mean = 0.0f32;
            for j in 0..self.d_model {
                mean += x.get(i, j);
            }
            mean /= self.d_model as f32;

            let mut var = 0.0f32;
            for j in 0..self.d_model {
                let diff = x.get(i, j) - mean;
                var += diff * diff;
            }
            var /= self.d_model as f32;

            let std_inv = 1.0 / (var + self.eps).sqrt();
            for j in 0..self.d_model {
                let val = self.gamma[j] * (x.get(i, j) - mean) * std_inv + self.beta[j];
                output.set(i, j, val);
            }
        }

        output
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
        MultiHeadAttention {
            d_model,
            n_heads,
            d_k,
            d_v,
            w_q: Tensor::randn(vec![d_model, d_k], 0.1),
            w_k: Tensor::randn(vec![d_model, d_k], 0.1),
            w_v: Tensor::randn(vec![d_model, d_v], 0.1),
            w_o: Tensor::randn(vec![n_heads * d_v, d_model], 0.1),
        }
    }

    pub fn forward(&self, x: &Tensor, causal: bool) -> Tensor {
        let seq_len = x.shape[0];
        let scale = (self.d_k as f32).sqrt();

        let q = matmul(x, &self.w_q, seq_len, self.d_model, self.d_k);
        let k = matmul(x, &self.w_k, seq_len, self.d_model, self.d_k);
        let v = matmul(x, &self.w_v, seq_len, self.d_model, self.d_v);

        let mut concat = Tensor::new(vec![seq_len, self.n_heads * self.d_v]);

        for h in 0..self.n_heads {
            let mut q_h = Tensor::new(vec![seq_len, self.d_k]);
            let mut k_h = Tensor::new(vec![seq_len, self.d_k]);
            let mut v_h = Tensor::new(vec![seq_len, self.d_v]);

            for i in 0..seq_len {
                for j in 0..self.d_k {
                    q_h.set(i, j, q.get(i, h * self.d_k + j));
                    k_h.set(i, j, k.get(i, h * self.d_k + j));
                }
                for j in 0..self.d_v {
                    v_h.set(i, j, v.get(i, h * self.d_v + j));
                }
            }

            // K^T
            let mut k_t = Tensor::new(vec![self.d_k, seq_len]);
            for i in 0..seq_len {
                for j in 0..self.d_k {
                    k_t.set(j, i, k_h.get(i, j));
                }
            }

            let mut scores = matmul(&q_h, &k_t, seq_len, self.d_k, seq_len);
            for val in scores.data.iter_mut() { *val /= scale; }

            if causal {
                for i in 0..seq_len {
                    for j in (i + 1)..seq_len {
                        scores.set(i, j, -1e9);
                    }
                }
            }

            softmax_row(&mut scores, seq_len, seq_len);

            let head_out = matmul(&scores, &v_h, seq_len, seq_len, self.d_v);

            for i in 0..seq_len {
                for j in 0..self.d_v {
                    concat.set(i, h * self.d_v + j, head_out.get(i, j));
                }
            }
        }

        matmul(&concat, &self.w_o, seq_len, self.n_heads * self.d_v, self.d_model)
    }
}

// ============================================================
// Feed-Forward Network
// ============================================================

pub struct FeedForward {
    pub d_model: usize,
    pub d_ff: usize,
    pub w1: Tensor,
    pub b1: Tensor,
    pub w2: Tensor,
    pub b2: Tensor,
}

impl FeedForward {
    pub fn new(d_model: usize, d_ff: usize) -> Self {
        FeedForward {
            d_model,
            d_ff,
            w1: Tensor::randn(vec![d_model, d_ff], 0.1),
            b1: Tensor::new(vec![d_ff]),
            w2: Tensor::randn(vec![d_ff, d_model], 0.1),
            b2: Tensor::new(vec![d_model]),
        }
    }

    pub fn forward(&self, x: &Tensor) -> Tensor {
        let seq_len = x.shape[0];
        let mut hidden = matmul(x, &self.w1, seq_len, self.d_model, self.d_ff);

        for i in 0..seq_len {
            for j in 0..self.d_ff {
                let val = hidden.get(i, j) + self.b1.get(0, j);
                hidden.set(i, j, val.max(0.0));
            }
        }

        let mut output = matmul(&hidden, &self.w2, seq_len, self.d_ff, self.d_model);
        for i in 0..seq_len {
            for j in 0..self.d_model {
                output.set(i, j, output.get(i, j) + self.b2.get(0, j));
            }
        }

        output
    }
}

// ============================================================
// Transformer Layer
// ============================================================

pub struct TransformerLayer {
    pub self_attn: MultiHeadAttention,
    pub norm1: LayerNorm,
    pub ffn: FeedForward,
    pub norm2: LayerNorm,
}

impl TransformerLayer {
    pub fn new(d_model: usize, n_heads: usize, d_ff: usize) -> Self {
        TransformerLayer {
            self_attn: MultiHeadAttention::new(d_model, n_heads),
            norm1: LayerNorm::new(d_model),
            ffn: FeedForward::new(d_model, d_ff),
            norm2: LayerNorm::new(d_model),
        }
    }

    pub fn forward(&self, x: &Tensor, causal: bool) -> Tensor {
        let normed = self.norm1.forward(x);
        let attn_out = self.self_attn.forward(&normed, causal);
        let mut residual1 = x.clone();
        residual1.add_in_place(&attn_out);

        let normed2 = self.norm2.forward(&residual1);
        let ffn_out = self.ffn.forward(&normed2);
        let mut residual2 = residual1;
        residual2.add_in_place(&ffn_out);

        residual2
    }
}

// ============================================================
// Transformer Encoder
// ============================================================

pub struct TransformerEncoder {
    pub layers: Vec<TransformerLayer>,
}

impl TransformerEncoder {
    pub fn new(d_model: usize, n_heads: usize, d_ff: usize, n_layers: usize) -> Self {
        let layers = (0..n_layers)
            .map(|_| TransformerLayer::new(d_model, n_heads, d_ff))
            .collect();
        TransformerEncoder { layers }
    }

    pub fn forward(&self, x: &Tensor) -> Tensor {
        let mut output = x.clone();
        for layer in &self.layers {
            output = layer.forward(&output, false);
        }
        output
    }
}

// ============================================================
// Transformer Decoder
// ============================================================

pub struct TransformerDecoder {
    pub layers: Vec<TransformerLayer>,
}

impl TransformerDecoder {
    pub fn new(d_model: usize, n_heads: usize, d_ff: usize, n_layers: usize) -> Self {
        let layers = (0..n_layers)
            .map(|_| TransformerLayer::new(d_model, n_heads, d_ff))
            .collect();
        TransformerDecoder { layers }
    }

    pub fn forward(&self, x: &Tensor, _encoder_output: &Tensor) -> Tensor {
        let mut output = x.clone();
        for layer in &self.layers {
            output = layer.forward(&output, true);  // causal
        }
        output
    }
}

// ============================================================
// Transformer Completo
// ============================================================

pub struct Transformer {
    pub encoder: TransformerEncoder,
    pub decoder: TransformerDecoder,
    pub output_proj: Tensor,
    pub d_model: usize,
    pub vocab_size: usize,
}

impl Transformer {
    pub fn new(vocab_size: usize, d_model: usize, n_heads: usize,
               d_ff: usize, n_layers: usize) -> Self {
        Transformer {
            encoder: TransformerEncoder::new(d_model, n_heads, d_ff, n_layers),
            decoder: TransformerDecoder::new(d_model, n_heads, d_ff, n_layers),
            output_proj: Tensor::randn(vec![d_model, vocab_size], 0.1),
            d_model,
            vocab_size,
        }
    }

    pub fn forward(&self, src: &Tensor, tgt: &Tensor) -> Tensor {
        let enc_output = self.encoder.forward(src);
        let dec_output = self.decoder.forward(tgt, &enc_output);
        let tgt_len = tgt.shape[0];
        matmul(&dec_output, &self.output_proj, tgt_len, self.d_model, self.vocab_size)
    }
}

// ============================================================
// Positional Encoding
// ============================================================

pub struct PositionalEncoding {
    pub pe: Tensor,
}

impl PositionalEncoding {
    pub fn new(max_len: usize, d_model: usize) -> Self {
        let mut pe = Tensor::new(vec![max_len, d_model]);
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
        let mut output = x.clone();
        let seq_len = x.shape[0];
        let d_model = x.shape[1];
        for i in 0..seq_len {
            for j in 0..d_model {
                output.data[i * d_model + j] += self.pe.get(i, j);
            }
        }
        output
    }
}

// ============================================================
// Exemplo
// ============================================================

pub fn example_transformer() {
    let vocab_size = 1000;
    let d_model = 128;
    let n_heads = 4;
    let d_ff = 512;
    let n_layers = 2;
    let seq_len = 10;

    let transformer = Transformer::new(vocab_size, d_model, n_heads, d_ff, n_layers);
    let pe = PositionalEncoding::new(100, d_model);

    // Input embedding
    let x = Tensor::randn(vec![seq_len, d_model], 0.1);
    let x_pe = pe.add(&x);

    // Encoder
    let enc_output = transformer.encoder.forward(&x_pe);

    println!("Encoder output shape: {:?}", enc_output.shape);

    // Classificacao (media)
    let mut cls = Tensor::new(vec![1, d_model]);
    for j in 0..d_model {
        let mut sum = 0.0f32;
        for i in 0..seq_len {
            sum += enc_output.get(i, j);
        }
        cls.set(0, j, sum / seq_len as f32);
    }

    println!("Classification embedding computed");
}

fn main() {
    example_transformer();
}
```

---

## 12. Implementacao em Fortran

```fortran
! transformer.f90 - Transformer Completo do Zero em Fortran
! Implementacao sem bibliotecas externas

module transformer_mod
    implicit none
    integer, parameter :: sp = kind(0.0)
    real(sp), parameter :: PI = 3.14159265358979323846_sp

contains

    ! ============================================================
    ! Matmul
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
    ! Softmax por linha
    ! ============================================================
    subroutine softmax_row(S, n_rows, n_cols)
        integer, intent(in) :: n_rows, n_cols
        real(sp), intent(inout) :: S(n_rows, n_cols)
        real(sp) :: max_val, sum_exp
        integer :: i, j
        do i = 1, n_rows
            max_val = -huge(1.0_sp)
            do j = 1, n_cols
                if (S(i, j) > max_val) max_val = S(i, j)
            end do
            sum_exp = 0.0_sp
            do j = 1, n_cols
                S(i, j) = exp(S(i, j) - max_val)
                sum_exp = sum_exp + S(i, j)
            end do
            do j = 1, n_cols
                S(i, j) = S(i, j) / sum_exp
            end do
        end do
    end subroutine softmax_row

    ! ============================================================
    ! Layer Normalization
    ! ============================================================
    subroutine layer_norm(X, gamma, beta, seq_len, d_model, output)
        integer, intent(in) :: seq_len, d_model
        real(sp), intent(in) :: X(seq_len, d_model), gamma(d_model), beta(d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        real(sp) :: mean_val, var_val, eps, std_inv
        integer :: i, j
        eps = 1.0e-5_sp

        do i = 1, seq_len
            mean_val = sum(X(i, :)) / d_model
            var_val = sum((X(i, :) - mean_val)**2) / d_model
            std_inv = 1.0_sp / sqrt(var_val + eps)
            do j = 1, d_model
                output(i, j) = gamma(j) * (X(i, j) - mean_val) * std_inv + beta(j)
            end do
        end do
    end subroutine layer_norm

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
    ! Multi-Head Self-Attention
    ! ============================================================
    subroutine multi_head_self_attention(X, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, output)
        integer, intent(in) :: seq_len, d_model, n_heads
        real(sp), intent(in) :: X(seq_len, d_model)
        real(sp), intent(in) :: W_Q(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_K(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_V(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_O(d_model, d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        integer :: d_k, d_v, h
        real(sp) :: Q(seq_len, d_model/n_heads)
        real(sp) :: K(seq_len, d_model/n_heads)
        real(sp) :: V(seq_len, d_model/n_heads)
        real(sp) :: scores(seq_len, seq_len)
        real(sp) :: head_out(seq_len, d_model/n_heads)
        real(sp) :: concat(seq_len, d_model)
        real(sp) :: K_T(d_model/n_heads, seq_len), scale

        d_k = d_model / n_heads
        d_v = d_model / n_heads
        scale = sqrt(real(d_k, sp))

        call matmul_2d(X, W_Q, Q, seq_len, d_model, d_k)
        call matmul_2d(X, W_K, K, seq_len, d_model, d_k)
        call matmul_2d(X, W_V, V, seq_len, d_model, d_v)

        concat = 0.0_sp
        do h = 1, n_heads
            call transpose_2d(K(:, (h-1)*d_k+1:h*d_k), K_T, seq_len, d_k)
            call matmul_2d(Q(:, (h-1)*d_k+1:h*d_k), K_T, scores, seq_len, d_k, seq_len)
            scores = scores / scale
            call softmax_row(scores, seq_len, seq_len)
            call matmul_2d(scores, V(:, (h-1)*d_v+1:h*d_v), head_out, seq_len, seq_len, d_v)
            concat(:, (h-1)*d_v+1:h*d_v) = head_out
        end do

        call matmul_2d(concat, W_O, output, seq_len, d_model, d_model)
    end subroutine multi_head_self_attention

    ! ============================================================
    ! Feed-Forward Network
    ! ============================================================
    subroutine feed_forward(X, W_1, b_1, W_2, b_2, seq_len, d_model, d_ff, output)
        integer, intent(in) :: seq_len, d_model, d_ff
        real(sp), intent(in) :: X(seq_len, d_model)
        real(sp), intent(in) :: W_1(d_model, d_ff), b_1(d_ff)
        real(sp), intent(in) :: W_2(d_ff, d_model), b_2(d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        real(sp) :: hidden(seq_len, d_ff)
        integer :: i, j

        call matmul_2d(X, W_1, hidden, seq_len, d_model, d_ff)
        do i = 1, seq_len
            do j = 1, d_ff
                hidden(i, j) = max(0.0_sp, hidden(i, j) + b_1(j))
            end do
        end do

        call matmul_2d(hidden, W_2, output, seq_len, d_ff, d_model)
        do i = 1, seq_len
            output(i, :) = output(i, :) + b_2
        end do
    end subroutine feed_forward

    ! ============================================================
    ! Transformer Layer
    ! ============================================================
    subroutine transformer_layer(X, W_Q, W_K, W_V, W_O, gamma_1, beta_1, &
                                  W_F1, b_F1, W_F2, b_F2, gamma_2, beta_2, &
                                  seq_len, d_model, n_heads, d_ff, output)
        integer, intent(in) :: seq_len, d_model, n_heads, d_ff
        real(sp), intent(in) :: X(seq_len, d_model)
        real(sp), intent(in) :: W_Q(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_K(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_V(d_model, d_model/n_heads)
        real(sp), intent(in) :: W_O(d_model, d_model)
        real(sp), intent(in) :: gamma_1(d_model), beta_1(d_model)
        real(sp), intent(in) :: W_F1(d_model, d_ff), b_F1(d_ff)
        real(sp), intent(in) :: W_F2(d_ff, d_model), b_F2(d_model)
        real(sp), intent(in) :: gamma_2(d_model), beta_2(d_model)
        real(sp), intent(out) :: output(seq_len, d_model)
        real(sp) :: normed(seq_len, d_model), attn_out(seq_len, d_model)
        real(sp) :: residual1(seq_len, d_model)
        real(sp) :: normed2(seq_len, d_model), ffn_out(seq_len, d_model)

        call layer_norm(X, gamma_1, beta_1, seq_len, d_model, normed)
        call multi_head_self_attention(normed, seq_len, d_model, n_heads, W_Q, W_K, W_V, W_O, attn_out)
        residual1 = X + attn_out

        call layer_norm(residual1, gamma_2, beta_2, seq_len, d_model, normed2)
        call feed_forward(normed2, W_F1, b_F1, W_F2, b_F2, seq_len, d_model, d_ff, ffn_out)
        output = residual1 + ffn_out
    end subroutine transformer_layer

    ! ============================================================
    ! Transpor
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

end module transformer_mod

! ============================================================
! Programa principal
! ============================================================
program transformer_example
    use transformer_mod
    implicit none

    integer, parameter :: seq_len = 10, d_model = 128, n_heads = 4
    integer, parameter :: d_ff = 512, n_layers = 2, max_len = 100
    real(sp) :: X(seq_len, d_model), X_pe(seq_len, d_model)
    real(sp) :: PE(max_len, d_model)
    real(sp) :: output(seq_len, d_model)
    integer :: i, j

    call random_seed()
    call random_number(X)

    call positional_encoding(max_len, d_model, PE)
    X_pe = X + PE(1:seq_len, :)

    print *, "Transformer Layer (simplified) output shape:", shape(output)
    print *, "Positional encoding shape:", shape(PE)
    print *, "Input embedding shape:", shape(X_pe)

    ! Para uma implementacao completa, seriam necessarios
    ! todos os pesos W_Q, W_K, W_V, W_O, W_F1, W_F2, etc.

end program transformer_example
```

---

## 13. Exemplo: Classificacao com Transformer

### 13.1 Pipeline Completo

```text
Pipeline de Classificacao com Transformer:
=============================================

1. Preparacao dos Dados:
   - Dataset: sentimentos de filmes (pos/neg)
   - Tokenizacao: words -> indices
   - Padding: sequencias de tamanho fixo
   - Split: treino (80%), validacao (10%), teste (10%)

2. Arquitetura:
   - Vocabulario: 25000 tokens
   - d_model: 256
   - n_heads: 8
   - d_ff: 1024
   - n_layers: 4
   - max_len: 512
   - n_classes: 2 (pos/neg)

3. Treinamento:
   - Optimizer: Adam (lr=1e-4)
   - Loss: Cross-Entropy
   - Batch size: 32
   - Epocas: 10
   - Warmup: 4000 passos

4. Inferencia:
   - Tokenizar input
   - Adicionar [CLS] token
   - Forward pass
   - Argmax na saida
   - Mapear para label
```

### 13.2 Codigo de Exemplo

```cpp
// Exemplo de classificacao com Transformer
void sentiment_classification() {
    std::mt19937 gen(42);

    // Hiperparametros
    int vocab_size = 25000;
    int d_model = 256;
    int n_heads = 8;
    int d_ff = 1024;
    int n_layers = 4;
    int max_len = 512;
    int n_classes = 2;
    int batch_size = 32;

    // Criar Transformer
    TransformerEncoder encoder(d_model, n_heads, d_ff, n_layers);
    encoder.init_weights(gen);

    // Classificador
    Tensor classifier({d_model, n_classes});
    xavier_init(classifier, gen);

    // Simular batch de dados
    Tensor batch_input({batch_size, max_len});
    std::uniform_int_distribution<int> token_dist(0, vocab_size - 1);
    for (float& val : batch_input.data) {
        val = static_cast<float>(token_dist(gen));
    }

    // Positional encoding
    PositionalEncoding pe(max_len, d_model);

    // Para cada exemplo no batch
    Tensor embeddings({batch_size, d_model});

    for (int b = 0; b < batch_size; b++) {
        // Extrair sequencia
        Tensor seq({max_len});
        for (int i = 0; i < max_len; i++) {
            seq.at(i) = batch_input.at(b, i);
        }

        // Embedding (simplificado)
        Tensor seq_emb({max_len, d_model});
        std::normal_distribution<float> emb_dist(0.0f, 0.1f);
        for (float& val : seq_emb.data) val = emb_dist(gen);

        // + Positional Encoding
        Tensor seq_pe = pe.add(seq_emb);

        // Encoder
        Tensor enc_out = encoder.forward(seq_pe);

        // Pooling: media
        for (int j = 0; j < d_model; j++) {
            float sum = 0.0f;
            for (int i = 0; i < max_len; i++) {
                sum += enc_out.at(i, j);
            }
            embeddings.at(b, j) = sum / max_len;
        }
    }

    // Classificacao
    Tensor logits({batch_size, n_classes});
    matmul(embeddings, classifier, logits, batch_size, d_model, n_classes);

    // Predicoes
    std::cout << "Predicoes (0=neg, 1=pos):" << std::endl;
    for (int b = 0; b < batch_size; b++) {
        int pred = logits.at(b, 1) > logits.at(b, 0) ? 1 : 0;
        std::cout << "  Batch " << b << ": " << pred << std::endl;
    }
}
```

---

## 14. Analise de Performance

### 14.1 Tempo de Execucao

```text
Performance do Transformer:
==============================

Fatores que afetam tempo:
  1. Tamanho da sequencia (n): O(n^2)
  2. Dimensao do modelo (d): O(d^2)
  3. Numero de camadas (L): O(L)
  4. Numero de heads (h): O(h)

Formula aproximada:
  Tempo ≈ L * (2 * n^2 * d + n * d^2)

Exemplo (BERT-base):
  L = 12, n = 512, d = 768
  Tempo ≈ 12 * (2 * 512^2 * 768 + 512 * 768^2)
       ≈ 12 * (402M + 302M)
       ≈ 8.5 GFLOPs

Exemplo (GPT-3 175B):
  L = 96, n = 2048, d = 12288
  Tempo ≈ 96 * (2 * 2048^2 * 12288 + 2048 * 12288^2)
       ≈ 96 * (101G + 307G)
       ≈ 39 TFLOPs por forward pass
```

### 14.2 Memoria

```text
Memoria do Transformer:
==========================

1. Pesos:
   BERT-base: 110M params * 4 bytes = 440 MB
   GPT-3: 175B params * 4 bytes = 700 GB (FP32)
          175B params * 2 bytes = 350 GB (FP16)

2. Ativacoes (por layer):
   Q, K, V: 3 * n * d * 4 bytes
   Scores: n^2 * 4 bytes
   Output: n * d * 4 bytes

3. Gradientes:
   Igual aos pesos

4. Otimizador (Adam):
   2x os pesos (momento + variancia)

Total BERT-base (treinamento):
  Pesos: 440 MB
  Gradientes: 440 MB
  Otimizador: 880 MB
  Ativacoes: ~2 GB (n=512)
  Total: ~3.7 GB
```

### 14.3 Otimizacoes

```text
Otimizacoes Comuns:
====================

1. Mixed Precision (FP16):
   - Pesos eativacoes em FP16
   - Acumulacao em FP32
   - 2x menos memoria, ~2x mais rapido em GPU

2. Gradient Checkpointing:
   - Nao salva ativacoes de todas as camadas
   - Recomputa durante backward
   - 30% mais lento, 60% menos memoria

3. Flash Attention:
   - Otimiza IO de memoria
   - Mais rapido em GPUs modernas
   - Mesma complexidade O(n^2)

4. Sparse Attention:
   - Nao attende todas as posicoes
   - Local + global attention
   - Reduz O(n^2) para O(n*sqrt(n))

5. Linear Attention:
   - Aproximacao do attention
   - O(n) em tempo e memoria
   - Qualidade menor
```

---

## 15. Exercicios

### 15.1 Exercicio Basico

```text
Exercicio 1: Implemente uma camada Transformer
  - Multi-head self-attention
  - Feed-forward network
  - Residual connections
  - Layer normalization
  - Teste com input (10, 64)

Exercicio 2: Implemente positional encoding
  - Sinusoidal para d_model = 64
  - Verifique propriedades ([-1, 1], unico por posicao)
  - Compare com learned PE
```

### 15.2 Exercicio Intermediario

```text
Exercicio 3: Implemente Transformer Encoder
  - 4 camadas, d_model = 128, n_heads = 4
  - Forward pass completo
  - Verifique shape da saida
  - Conte numero de parametros

Exercicio 4: Implemente classificacao
  - Dataset sintetico (1000 exemplos)
  - Encoder + pooling + classificador
  - Treine por 10 epocas
  - Meacure accuracy
```

### 15.3 Exercicio Avancado

```text
Exercicio 5: Implemente Transformer Decoder
  - Causal masking
  - Autoregressive generation
  - Gere texto apos treinamento

Exercicio 6: Otimizacao de performance
  - Implemente Flash Attention
  - Compare com implementacao basica
  - Meacure speedup e uso de memoria
```

---

## 16. Resumo

### 16.1 Conceitos-Chave

```text
Conceitos Essenciais do Transformer:
=======================================

1. Multi-Head Self-Attention:
   - Captura dependencias entre todos os tokens
   - h heads paralelas
   - O(n^2 * d) por camada

2. Positional Encoding:
   - Injeta informacao de posicao
   - Sinusoidal (fixo) ou Learned
   - Sem ela, attention e permutacao-invariante

3. Feed-Forward Network:
   - MLP por posicao
   - d_ff = 4 * d_model tipicamente
   - Transformacao nao-linear

4. Layer Normalization:
   - Normaliza por feature
   - Pre-norm (moderno) ou Post-norm (original)
   - Estabiliza treinamento

5. Residual Connections:
   - Skip connections
   - Mantem fluxo de gradiente
   - Redes podem ser profundas

6. Encoder-Decoder:
   - Encoder: self-attention bidirecional
   - Decoder: masked self-attention + cross-attention
   - Para tarefas seq2seq (NMT, sumarizacao)
```

### 16.2 Variantes

```text
Variantes do Transformer:
===========================

1. Encoder-Only (BERT):
   - Self-attention bidirecional
   - Para classificacao, NER, QA
   - Pre-treinamento: MLM + NSP

2. Decoder-Only (GPT):
   - Self-attention causal
   - Para generacao de texto
   - Pre-treinamento: next token prediction

3. Encoder-Decoder (T5):
   - Completo
   - Para NMT, sumarizacao
   - Pre-treinamento: span corruption

4. Vision Transformer (ViT):
   - Para imagens
   - Patches como tokens
   - Self-attention em patches

5. Swin Transformer:
   - Hierarquico
   - Window attention
   - Para deteccao de objetos
```

---

## 17. Referencias

```text
Referencias:
==============

1. Vaswani et al., "Attention Is All You Need" (2017)

2. Devlin et al., "BERT: Pre-training of Deep Bidirectional Transformers" (2018)

3. Radford et al., "Improving Language Understanding by Generative Pre-Training" (2018)

4. Brown et al., "Language Models are Few-Shot Learners" (2020)

5. Dosovitskiy et al., "An Image is Worth 16x16 Words: Transformers for Image Recognition" (2020)

6. Liu et al., "Swin Transformer: Hierarchical Vision Transformer using Shifted Windows" (2021)
```

---

## 18. Tendencias Modernas

### 18.1 Mixture of Experts (MoE)

```text
Mixture of Experts:
=====================

Ideia: ativar APENAS parte dos parametros por token.

Arquitetura:
  - FFN normal: todos os neuronios ativados
  - MoE FFN: K experts, seleciona top-K

Formula:
  y = sum_{i in topK} g_i * Expert_i(x)

  g_i = softmax(W_g * x)  (gating network)

Exemplo:
  - 8 experts, top-2
  - Cada token usa 2/8 = 25% dos parametros
  - Total: 8x parametros, mas 2x compute

GPT-4 (estimativa):
  - 1.8T parametros totais
  - 16 experts por layer
  - ~280B parametros ativos por forward

Vantagens:
  + Mais parametros (mais conhecimento)
  + Mesmo compute (mesma velocidade)
  + Especializacao de experts

Desvantagens:
  - Load balancing: experts podem colapsar
  - Mais memoria (todos os experts na GPU)
  - Comunicacao entre GPUs (expert parallel)
```

### 18.2 State Space Models

```text
State Space Models (SSM):
============================

Alternativa ao Transformer com O(n) complexidade.

Mamba (2023):
  - SSM seletivo
  - gating dependente do input
  - O(n) em tempo e memoria
  - Competitive com Transformer

Arquitetura:
  h_t = A * h_{t-1} + B * x_t
  y_t = C * h_t

  A, B, C sao dependents do input (seletivo)

Vantagens:
  + O(n) complexidade
  + Memoria constante
  + Sequencias longas (1M+ tokens)

Desvantagens:
  - Nao e paralelizavel (recorrente)
  - Menos expressivo que attention
  - Ainda em pesquisa

Hybridos:
  - Mamba + Attention
  - Camadas alternadas
  - Melhor dos dois mundos
```

### 18.3 Retentive Network

```text
Retentive Network (RetNet):
==============================

Solucao hibrida:
  - Parallel (como Transformer)
  - Recurrent (como RNN)
  - Chunkwise (híbrido)

Formula:
  y_t = sum_{j<=t} gamma^{t-j} * (Q_t * K_j^T) * V_j

  gamma: decay factor (exponencial)

Vantagens:
  + O(n) em inference (recorrente)
  + O(n^2) em treinamento (parallel)
  + O(n * chunk_size) chunkwise
  + State que pode ser comprimido

Microsoft RetNet:
  - 7B parametros
  - Competitive com Transformer
  - 3x mais rapido em inference
```

---

## 19. Transformer em Producao

### 19.1 Serving Otimizado

```text
Transformer Serving:
=====================

Problema:
  - Latencia baixa necessaria
  - Throughput alto necessario
  - Memoria limitada

Solucoes:
  1. KV Cache:
     - Cache de K e V para tokens anteriores
     - Nao recalcula attention completa
     - Memoria: O(n * d) por layer
     - Speedup: 10x para geracao autoregressiva

  2. Continuous Batching:
     - Batch dinamico (nao fixo)
     - Novos requests entram durante batch
     - Throughput: 2-5x

  3. Speculative Decoding:
     - Modelo pequeno gera candidatos
     - Modelo grande verfica em paralelo
     - Speedup: 2-3x

  4. Quantization:
     - INT8, INT4, FP8
     - 2-4x menos memoria
     - ~1% perda de qualidade
     - GPTQ, AWQ, GGML

  5. Tensor Parallelism:
     - Dividir modelo em GPUs
     - Cada GPU calcula parte
     - Linear scaling com GPUs
```

### 19.2 Infraestrutura

```text
Infraestrutura para Transformers:
====================================

Hardware:
  - NVIDIA A100: 80GB HBM2e, 312 TFLOPS FP16
  - NVIDIA H100: 80GB HBM3, 989 TFLOPS FP16
  - AMD MI250X: 128GB HBM2e, 383 TFLOPS
  - Google TPU v4: 32GB HBM2e, 275 TFLOPS

Software:
  - vLLM: serving otimizado
  - TensorRT-LLM: NVIDIA otimizado
  - Text Generation Inference (TGI)
  - llama.cpp: CPU inference
  - Ollama: local deployment

Frameworks:
  - PyTorch + CUDA
  - JAX + XLA
  - TensorRT
  - ONNX Runtime

Monitoramento:
  - Latencia por token
  - Throughput (tokens/s)
  - GPU utilization
  - Memory usage
  - Queue depth
```

---

## 20. Aplicacoes em Seguranca

### 20.1 Transformers em Cybersecurity

```text
Transformers em Seguranca:
============================

1. Deteccao de Malware:
   - Analise de sequencias de chamadas
   - Attention em API calls
   - Classificacao de binarios

2. Analise de Vulnerabilidades:
   - Code review automatico
   - Attention em codigo fonte
   - Deteccao de padroes inseguros

3. Phishing Detection:
   - Analise de URLs e emails
   - Attention em texto
   - Classificacao binaria

4. Network Intrusion:
   - Sequencias de pacotes
   - Attention temporal
   - Detecao de anomalias

5. Code Generation:
   - GitHub Copilot
   - Geracao de codigo
  - Risk: gerar codigo com vulnerabilities

6. Social Engineering:
  - Deteccao de manipulacao
  - Attention em dialogo
  - Alertas para usuarios
```

### 20.2 Adversarial Attacks

```text
Ataques Adversariais em Transformers:
========================================

1. Textual Adversarial:
   - Perturbacoes em tokens
   - Synonym substitution
   - Character-level attacks
   - Ex: "good" -> "g00d"

2. Backdoor Attacks:
   - Trigger escondido no input
   - Modelo classifica incorretamente
   - Dificil de detectar

3. Prompt Injection:
   - Input manipula o modelo
   - Override de instrucoes
   - Risco em LLMs

4. Model Extraction:
   - Query model para treinar copia
   - Risco de propriedade intelectual
   - Defesa: rate limiting

5. Data Poisoning:
   - Inserir dados maliciosos no treino
   - Comprometer comportamento
   - Dificil de detectar

Defesas:
  - Adversarial training
  - Input validation
  - Model watermarking
  - Differential privacy
```

---

## 21. Exercicios Avancados

### 21.1 Implementacao de MoE

```text
Exercicio: Mixture of Experts
==============================

Tarefa:
  1. Implemente FFN com 4 experts
  2. Gating network: 2 experts por token
  3. Load balancing loss
  4. Treine em dataset sintetico

Especificacoes:
  - d_model: 256
  - d_ff: 1024 por expert
  - 4 experts, top-2
  - Load balance lambda: 0.01

Metricas:
  - Taxa de uso por expert
  - Load balance loss
  - Performance vs FFN normal
```

### 21.2 KV Cache

```text
Exercicio: KV Cache
====================

Tarefa:
  1. Implemente KV cache para Transformer decoder
  2. Meacure speedup vs recomputacao
  3. Analise uso de memoria

Cenarios:
  - seq_len: 128, 256, 512, 1024
  - Compare: recomputacao vs cache
  - Plote: tempo vs seq_len

Esperado:
  - Speedup: 2-5x para seq_len=1024
  - Memoria extra: O(n * d * layers)
```

---

## 22. Resumo Final

### 22.1 O Que Aprendemos

```text
Resumo do Capitulo:
=====================

1. Evolucao:
   - RNN -> LSTM -> Transformer
   - Paralelismo e dependencias longas

2. Arquitetura:
   - Encoder-Decoder (original)
   - Encoder-only (BERT)
   - Decoder-only (GPT)

3. Componentes:
   - Multi-Head Self-Attention
   - Positional Encoding
   - Feed-Forward Network
   - Layer Normalization
   - Residual Connections

4. Variantes:
   - Sinusoidal vs Learned PE
   - Pre-Norm vs Post-Norm
   - GELU vs ReLU
   - Flash Attention

5. Aplicacoes:
   - NLP (BERT, GPT)
   - Vision (ViT, Swin)
   - Multimodal (CLIP, DALL-E)
   - Audio (Whisper)

6. Producao:
   - KV Cache
   - Quantization
   - Tensor Parallelism
   - Serving frameworks
```

---

Fim do Capitulo 14 — Transformer
