---
layout: default
title: "12-lstm"
---

# Capitulo 12 — LSTM (Long Short-Term Memory)

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender o problema do vanishing gradient** em profundidade — por que RNNs basicas falham em memorias de longo prazo e como LSTM resolve isso com cell state dedicado.
2. **Dominar a arquitetura LSTM completa** — forget gate, input gate, output gate, cell state, memory cell, e como cada componente contribui para a memoria de longo prazo.
3. **Comparar LSTM vs GRU em detalhe** — arquitetura, parametros, performance, e cenarios de uso ideais para cada um.
4. **Implementar forward pass completo em C++** — com todos os portoes, cell state, e mecanismos de memoria.
5. **Implementar backward pass em C++** — BPTT adaptado para LSTM com gradientes por cada componente.
6. **Implementar LSTM em Rust** — aproveitando o sistema de ownership para gestao segura de estados de memoria.
7. **Implementar LSTM em Fortran** — usando subrotinas eficientes para operacoes matriciais.
8. **Implementar Bidirectional LSTM** — para capturar contexto passado e futuro simultaneamente.
9. **Aplicar LSTM a previsao de sequencias longas** — pipeline completo com dados reais e avaliacao.
10. **Implementar Stack de LSTMs** — camadas empilhadas para extrair features hierarquicas.

---

## 1. Problema do Vanishing Gradient

### 1.1 Revisao Profunda

No capitulo sobre RNNs, vimos que o vanishing gradient impede o aprendizado de dependencias de longo prazo. Agora vamos entender profundamente por que isso acontece e como LSTM resolve.

```text
Analise Matematica do Vanishing Gradient:

Em uma RNN basica:
  h_t = tanh(W_xh * x_t + W_hh * h_{t-1} + b_h)

O gradiente de h_T em relacao a h_1 e:
  dh_T/dh_1 = prod(t=2 to T) [W_hh * diag(1 - h_t^2)]

Para cada passo:
  1. Multiplicamos por W_hh (matriz de pesos)
  2. Multiplicamos por diag(1 - h_t^2) (derivada do tanh)

O produto de T matrizes pode:
  - Encolher exponencialmente (autovalores < 1) -> vanishing
  - Crescenter exponencialmente (autovalores > 1) -> exploding
```

### 1.2 Por Que LSTM Resolve

```text
A Solucao LSTM: Cell State

Em vez de sobrescrever o hidden state a cada passo,
LSTM mantem um CELL STATE separado:

c_t = f_t * c_{t-1} + i_t * c~_t

onde:
- f_t = forget gate (valores em [0,1])
- i_t = input gate (valores em [0,1])
- c~_t = candidato (valores em [-1,1])

O gradiente de c_t em relacao a c_{t-1} e:
  dc_t/dc_{t-1} = f_t

Se f_t ~= 1 (esquecimento proximo de zero):
  O gradiente flui SEM MULTIPLICACAO POR MATRIZ DE PESOS!
  O cell state age como uma AUTO-estrada para gradientes.
```

### 1.3 Comparacao Visual

```text
RNN:
  h_t = tanh(W * [x_t, h_{t-1}])  <- REESCRITO a cada passo
  Gradiente: W * diag(1-h^2) * W * diag(1-h^2) * ...  <- ENCOLHE

LSTM:
  c_t = f_t * c_{t-1} + i_t * c~_t  <- ATUALIZADO seletivamente
  Gradiente: f_t * f_t * f_t * ...  <- FLUI se f_t ~= 1

A diferenca e CRUCIAL:
- RNN: gradiente passa por MATRIZES de peso (d_h x d_h)
- LSTM: gradiente passa por ESCALARES (valores em [0,1])
```

---

## 2. Arquitetura LSTM

### 2.1 Componentes Fundamentais

A LSTM possui cinco componentes principais:

```text
Componentes da LSTM:

1. Forget Gate (f_t):
   - Decide QUEMAIS informacao do cell state esquecer
   - Saida: vetor em [0,1] por dimensao do cell state
   - 0 = esquecer completamente
   - 1 = lembrar completamente

2. Input Gate (i_t):
   - Decide QUEMAIS informacao nova armazenar
   - Saida: vetor em [0,1] por dimensao do cell state
   - 0 = nao armazenar nada
   - 1 = armazenar tudo

3. Cell State Candidate (c~_t):
   - Novo conteudo potencial para o cell state
   - Saida: vetor em [-1,1] via tanh
   - Combinacao da entrada atual e do hidden state

4. Cell State (c_t):
   - A memoria de longo prazo
   - Atualizado por: c_t = f_t * c_{t-1} + i_t * c~_t
   - Informacao pode persistir por tempo INDEFINIDO

5. Output Gate (o_t):
   - Decide QUEMAIS do cell state expor no hidden state
   - Saida: vetor em [0,1] por dimensao
   - Filtra a informacao antes de torna-la visivel
```

### 2.2 Equacoes Completas

```text
Equacoes da LSTM:

1. Forget Gate:
   f_t = sigmoid(W_f * [h_{t-1}, x_t] + b_f)

2. Input Gate:
   i_t = sigmoid(W_i * [h_{t-1}, x_t] + b_i)

3. Cell State Candidate:
   c~_t = tanh(W_c * [h_{t-1}, x_t] + b_c)

4. Cell State (atualizacao):
   c_t = f_t * c_{t-1} + i_t * c~_t

5. Output Gate:
   o_t = sigmoid(W_o * [h_{t-1}, x_t] + b_o)

6. Hidden State (saida):
   h_t = o_t * tanh(c_t)

Onde:
- [h_{t-1}, x_t] = concatenacao do hidden state anterior e da entrada
- sigmoid: funcao logistica, valores em (0,1)
- tanh: hiperbolico tangente, valores em (-1,1)
- *: multiplicacao element-wise (Hadamard product)
```

### 2.3 Fluxo de Informacao

```text
Fluxo de Informacao na LSTM:

     c_{t-1} -----> [x f_t] -----> c_t (cell state)
         |              ^
         |              |
         +------+-------+
                |
    h_{t-1} --+---> [sigmoid] -> o_t -> [x tanh(c_t)] -> h_t
                |        |
    x_t --------+---+----+
                   |    |
         [sigmoid] |    [sigmoid] -> i_t
              f_t  |         |
                   |    [tanh] -> c~_t
                   |
              concatenacao [h_{t-1}, x_t]

Onde:
- [x] = multiplicacao element-wise
- [concatenacao] = juntar vetores
```

---

## 3. Forget Gate

### 3.1 Mecanismo

O forget gate e o mecanismo de "limpeza" da memoria. Ele decide quanta informacao antiga deve ser descartada.

```text
Equacao:
f_t = sigmoid(W_f * [h_{t-1}, x_t] + b_f)

Onde:
- W_f: matriz de pesos do forget gate (d_c x (d_h + d_x))
- b_f: bias do forget gate (d_c)
- sigmoid: comprime saida para [0,1]

Comportamento:
f_t ~= 0: "Esqueca quase tudo" (limpeza forte)
f_t ~= 1: "Lembre de tudo" (preservacao forte)
f_t ~= 0.5: "Mantenha metade" (filtragem parcial)
```

### 3.2 Por Que Forget Gate e Critico

```text
Exemplo: Analise de Sentimento com Multiplos Sentimentos

Frase: "O filme comecou BOM, mas o final foi TERRIVEL"

Sem forget gate (RNN basica):
- "BOM" e armazenado no hidden state
- "mas" tenta sobrescrever, mas o gradiente enfraquece
- "TERRIVEL" pode nao ser suficiente para sobrescrever
- Resultado: classificacao incorreta (ainda "lembra" de "BOM")

Com forget gate (LSTM):
- "BOM" e armazenado no cell state
- Quando "mas" aparece:
  - forget gate ~= 0.2 (esquece "BOM")
  - O cell state e LIMPO antes de receber "TERRIVEL"
- Resultado: classificacao correta ("TERRIVEL" domina)

O forget gate permite "resetar" a memoria quando necessario.
```

### 3.3 Inicializacao do Bias

```text
Dica Importante: Bias do Forget Gate

Inicializacao padrao: b_f = 0 (sigmoid(0) = 0.5)
Isso significa: "esquecer metade" por padrao

Inicializacao recomendada: b_f = 1 (sigmoid(1) = 0.73)
Isso significa: "lembrar mais" por padrao

Por que?
- Na inicializacao, a rede nao sabe nada
- Se esquece muito, perde informacao util
- Se lembra tudo, cell state fica saturado
- b_f = 1 da um "peso" para lembrar
- A rede aprende a esquecer quando necessario

Implementacao:
  b_f = vector_of_ones * 1.0  // bias do forget gate
  b_i = vector_of_zeros        // bias do input gate (manter)
  b_o = vector_of_zeros        // bias do output gate (manter)
  b_c = vector_of_zeros        // bias do candidato (manter)
```

---

## 4. Input Gate

### 4.1 Mecanismo

O input gate decide quanta informacao NOVA deve ser armazenada no cell state.

```text
Equacao:
i_t = sigmoid(W_i * [h_{t-1}, x_t] + b_i)

Combinado com o candidato:
c~_t = tanh(W_c * [h_{t-1}, x_t] + b_c)

Informacao armazenada:
nova_info = i_t * c~_t

Onde:
- i_t: gate que seleciona QUEMAIS dimensoes atualizar
- c~_t: conteudo potencial para cada dimensao
- i_t * c~_t: produto element-wise seleciona o conteudo
```

### 4.2 Exemplo Pratico

```text
Exemplo: Processando "Python e uma linguagem de programacao"

Token: "Python"
- i_1 ~= 0.8 (forte sinal para armazenar)
- c~_1 ~= [0.9, -0.3, 0.7, ...] (representacao de "Python")
- nova_info = 0.8 * c~_1 = [0.72, -0.24, 0.56, ...]
- c_1 = 0.72, -0.24, 0.56 (cell state armazena "Python")

Token: "e" (verbo ser)
- i_2 ~= 0.2 (fraca — verbo comum, pouco relevante)
- c~_2 ~= [0.1, 0.05, -0.02, ...]
- nova_info = 0.2 * c~_2 = [0.02, 0.01, -0.004, ...]
- c_2 ~= c_1 (cell state PRESERVADO — "e" nao substitui "Python")

Token: "uma"
- i_3 ~= 0.15 (muito fraca — artigo irrelevante)
- c_3 ~= c_2 (preservando "Python")

O input gate APRENDE que substantivos sao mais importantes
que verbos e artigos para a tarefa.
```

---

## 5. Cell State e Memory Cell

### 5.1 O Cel State: A Auto-Estrada da Memoria

O cell state e o componente MAIS IMPORTANTE da LSTM. Ele e a "auto-estrada" por onde a informacao flui ao longo do tempo.

```text
Cell State:
c_t = f_t * c_{t-1} + i_t * c~_t

Propriedades:
1. Atualizacao ADITIVA (nao substitui, incrementa)
2. Controlada por gates (f_t e i_t)
3. Pode preservar informacao por tempo INDEFINIDO
4. Gradiente flui diretamente quando f_t ~= 1

Analogia:
- RNN hidden state = Tabela reescrita a cada linha
- LSTM cell state = Livro onde voce ADICIONA paginas
  e APAGA paginas selecionadas
```

### 5.2 Memory Cell

```text
Memory Cell vs Cell State:

Na literatura, os termos sao frequentemente usados
de forma intercambiavel. A distincao tecnica:

Memory Cell:
- A unidade de armazenamento individual
- Cada dimensao do cell state e uma "memory cell"
- Cada cell armazena UM aspecto da informacao

Cell State:
- O vetor completo (d_c dimensoes)
- Contem d_c memory cells
- Cada cell pode ser independentemente controlada

Exemplo com d_c = 4:
  Cell State: [0.8, -0.3, 0.5, 0.1]
  
  Cell 1: "assunto principal" (alto valor, bem preservado)
  Cell 2: "sentimento negativo" (negativo, preservado)
  Cell 3: "contexto temporal" (medio, sendo atualizado)
  Cell 4: "informacao ruido" (baixo, sendo esquecida)
```

### 5.3 Persistencia de Memoria

```text
Exemplo de Persistencia:

Frase longa: "O gato preto que estava sentado no tapete vermelho
da sala de estar da minha avo, que morava em uma cidade pequena
no interior de Sao Paulo, e que sempre me dava doces quando eu
ia visita-la, faleceu ontem."

Cell state ao longo da frase:

c_1  (gato):       [0.9, 0.0, 0.0, ...]  <- "gato" armazenado
c_2  (preto):      [0.9, 0.7, 0.0, ...]  <- "preto" adicionado
c_5  (tapete):     [0.9, 0.7, 0.5, ...]  <- "tapete" adicionado
c_10 (Sao Paulo):  [0.9, 0.7, 0.5, 0.8] <- "Sao Paulo" adicionado
c_15 (doces):      [0.9, 0.7, 0.5, 0.8] <- PRESERVADO!
c_20 (visitela):   [0.9, 0.7, 0.5, 0.8] <- PRESERVADO!
c_25 (faleceu):    [0.1, 0.7, 0.5, 0.8] <- "gato" ESQUECIDO
                                           (reset para "faleceu")

O cell state MANTÉM informacao de 20+ tokens!
Uma RNN basica esqueceria "gato" em ~5 tokens.
```

---

## 6. Output Gate

### 6.1 Mecanismo

O output gate decide quanta informacao do cell state e exposta no hidden state.

```text
Equacao:
o_t = sigmoid(W_o * [h_{t-1}, x_t] + b_o)
h_t = o_t * tanh(c_t)

Onde:
- o_t: gate de saida, valores em [0,1]
- tanh(c_t): cell state comprimido para [-1,1]
- h_t: hidden state (saida filtrada)

Por que filtrar?
- O cell state pode conter MUITA informacao
- Nao toda informacao e relevante para a saida atual
- O output gate SELECIONA o que expor
```

### 6.2 Exemplo

```text
Exemplo: Classificacao de Sentimento

Frase: "O filme foi incrivelmente BOM"

Apos processar todos os tokens:
- Cell state: [0.9, 0.8, 0.3, 0.7] (muita informacao)
  - Cell 1: "filme" (assunto)
  - Cell 2: "bom" (sentimento positivo)
  - Cell 3: "incrivelmente" (intensificador)
  - Cell 4: contexto geral

Para classificacao, so precisamos do SENTIMENTO:
- o_t ~= [0.1, 0.9, 0.3, 0.1] (so importa cell 2)
- h_t = o_t * tanh(c_t)
        = [0.1, 0.9, 0.3, 0.1] * [0.72, 0.66, 0.29, 0.60]
        = [0.07, 0.59, 0.09, 0.06]

O hidden state PRESERVA principalmente o sentimento.
O output gate APRENDE que sentimento e mais relevante
que assunto para esta tarefa.
```

---

## 7. LSTM vs GRU Comparacao Detalhada

### 7.1 Arquiteturas Comparadas

```text
LSTM:
  f_t = sigmoid(W_f * [h_{t-1}, x_t] + b_f)    -- forget
  i_t = sigmoid(W_i * [h_{t-1}, x_t] + b_i)    -- input
  c~_t = tanh(W_c * [h_{t-1}, x_t] + b_c)       -- candidate
  c_t = f_t * c_{t-1} + i_t * c~_t              -- cell state
  o_t = sigmoid(W_o * [h_{t-1}, x_t] + b_o)    -- output
  h_t = o_t * tanh(c_t)                          -- hidden state

GRU:
  r_t = sigmoid(W_r * [h_{t-1}, x_t] + b_r)    -- reset
  z_t = sigmoid(W_z * [h_{t-1}, x_t] + b_z)    -- update
  h~_t = tanh(W * [r_t * h_{t-1}, x_t] + b)    -- candidate
  h_t = (1 - z_t) * h_{t-1} + z_t * h~_t       -- hidden state
```

### 7.2 Tabela Comparativa

```text
| Aspecto                | LSTM                    | GRU                     |
|------------------------|-------------------------|-------------------------|
| Portoes                | 3 (forget, input, output)| 2 (reset, update)      |
| Cell state             | Sim (separado)          | Nao (usa hidden state)  |
| Parametros             | 4*d*(d+d+1)            | 3*d*(d+d+1)            |
| Memoria de longo prazo | Superior                | Boa                     |
| Velocidade             | ~30% mais lenta         | Mais rapida             |
| Regularizacao          | Mais propensa           | Menos propensa          |
| Complexidade           | Maior                   | Menor                   |
| Casos ideais           | Seq. longas, memoria    | Seq. medias, dados      |
|                        | complexa                | limitados               |
```

### 7.3 Analise de Parametros

```text
Detalhamento de Parametros:

LSTM (4 operacoes de gating):
  Forget:  d_c * (d_h + d_x + 1)  [W_f, b_f]
  Input:   d_c * (d_h + d_x + 1)  [W_i, b_i]
  Cand.:   d_c * (d_h + d_x + 1)  [W_c, b_c]
  Output:  d_c * (d_h + d_x + 1)  [W_o, b_o]
  Total:   4 * d_c * (d_h + d_x + 1)

GRU (3 operacoes):
  Reset:   d_h * (d_h + d_x + 1)  [W_r, b_r]
  Update:  d_h * (d_h + d_x + 1)  [W_z, b_z]
  Cand.:   d_h * (d_h + d_x + 1)  [W_h, b_h]
  Total:   3 * d_h * (d_h + d_x + 1)

Para d_h = d_c = 256, d_x = 128:
  LSTM: 4 * 256 * 385 = 394.240
  GRU:  3 * 256 * 385 = 295.680
  Diferenca: 98.560 (25% menos no GRU)
```

### 7.4 Quando Usar Cada Um

```text
Decisao: LSTM vs GRU

Use LSTM quando:
1. Sequencias MUITO longas (>500 tokens)
   - Cell state separado preserva melhor
   - Forget gate permite limpeza seletiva
   
2. Memoria complexa necessaria
   - Multiplas informacoes simultaneas
   - Dependencias de muito longo prazo
   
3. Tarefas de geracao
   - Traducao automatica
   - Captioning de imagens
   - Geracao de musica
   
4. Dados abundantes
   - Mais parametros = mais capacidade
   - Dados suficientes para nao overfittar

Use GRU quando:
1. Dados limitados
   - Menos parametros = menos overfitting
   - Mais rapido de treinar
   
2. Sequencias de comprimento medio (50-200 tokens)
   - GRU e suficiente para essa faixa
   - Mais eficiente que LSTM
   
3. Velocidade e critica
   - 30% mais rapido
   - Menos uso de memoria
   
4. Prototipagem
   - Menos hiperparametros
   - Mais facil de debuggar
```

---

## 8. Implementacao Completa em C++

### 8.1 Estruturas de Dados

```cpp
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <numeric>
#include <iostream>
#include <cassert>

using Vector = std::vector<double>;
using Matrix = std::vector<Vector>;

struct LSTMParams {
    // Forget gate
    Matrix W_f;   // (d_h + d_x) x d_c
    Vector b_f;   // d_c

    // Input gate
    Matrix W_i;   // (d_h + d_x) x d_c
    Vector b_i;   // d_c

    // Cell state candidate
    Matrix W_c;   // (d_h + d_x) x d_c
    Vector b_c;   // d_c

    // Output gate
    Matrix W_o;   // (d_h + d_x) x d_c
    Vector b_o;   // d_c

    // Output projection
    Matrix W_y;   // d_c x d_y
    Vector b_y;   // d_y

    int input_size;
    int hidden_size;
    int cell_size;
    int output_size;

    LSTMParams(int input_size, int hidden_size, int output_size)
        : input_size(input_size),
          hidden_size(hidden_size),
          cell_size(hidden_size),  // cell_size = hidden_size tipicamente
          output_size(output_size)
    {
        int concat_size = hidden_size + input_size;

        W_f = create_matrix(concat_size, cell_size);
        b_f = create_vector(cell_size);

        W_i = create_matrix(concat_size, cell_size);
        b_i = create_vector(cell_size);

        W_c = create_matrix(concat_size, cell_size);
        b_c = create_vector(cell_size);

        W_o = create_matrix(concat_size, cell_size);
        b_o = create_vector(cell_size);

        W_y = create_matrix(output_size, cell_size);
        b_y = create_vector(output_size);
    }
};

struct LSTMCache {
    std::vector<Vector> inputs;
    std::vector<Vector> hidden_states;
    std::vector<Vector> cell_states;
    std::vector<Vector> forget_gates;
    std::vector<Vector> input_gates;
    std::vector<Vector> cell_candidates;
    std::vector<Vector> output_gates;
    std::vector<Vector> outputs;
};

struct LSTMGrads {
    Matrix dW_f;
    Vector db_f;
    Matrix dW_i;
    Vector db_i;
    Matrix dW_c;
    Vector db_c;
    Matrix dW_o;
    Vector db_o;
    Matrix dW_y;
    Vector db_y;

    LSTMGrads(int input_size, int hidden_size, int cell_size, int output_size)
        : dW_f(create_matrix(hidden_size + input_size, cell_size)),
          db_f(create_vector(cell_size)),
          dW_i(create_matrix(hidden_size + input_size, cell_size)),
          db_i(create_vector(cell_size)),
          dW_c(create_matrix(hidden_size + input_size, cell_size)),
          db_c(create_vector(cell_size)),
          dW_o(create_matrix(hidden_size + input_size, cell_size)),
          db_o(create_vector(cell_size)),
          dW_y(create_matrix(output_size, cell_size)),
          db_y(create_vector(output_size))
    {}
};
```

### 8.2 Operacoes Auxiliares

```cpp
Matrix create_matrix(int rows, int cols, double init = 0.0) {
    return Matrix(rows, Vector(cols, init));
}

Vector create_vector(int size, double init = 0.0) {
    return Vector(size, init);
}

Vector concat(const Vector& a, const Vector& b) {
    Vector result;
    result.reserve(a.size() + b.size());
    result.insert(result.end(), a.begin(), a.end());
    result.insert(result.end(), b.begin(), b.end());
    return result;
}

Vector sigmoid(const Vector& v) {
    Vector result(v.size());
    for (size_t i = 0; i < v.size(); i++) {
        result[i] = 1.0 / (1.0 + std::exp(-v[i]));
    }
    return result;
}

Vector sigmoid_deriv(const Vector& s) {
    Vector result(s.size());
    for (size_t i = 0; i < s.size(); i++) {
        result[i] = s[i] * (1.0 - s[i]);
    }
    return result;
}

Vector tanh_vec(const Vector& v) {
    Vector result(v.size());
    for (size_t i = 0; i < v.size(); i++) {
        result[i] = std::tanh(v[i]);
    }
    return result;
}

Vector tanh_deriv(const Vector& h) {
    Vector result(h.size());
    for (size_t i = 0; i < h.size(); i++) {
        result[i] = 1.0 - h[i] * h[i];
    }
    return result;
}

Vector vec_add(const Vector& a, const Vector& b) {
    Vector result(a.size());
    for (size_t i = 0; i < a.size(); i++) {
        result[i] = a[i] + b[i];
    }
    return result;
}

Vector vec_sub(const Vector& a, const Vector& b) {
    Vector result(a.size());
    for (size_t i = 0; i < a.size(); i++) {
        result[i] = a[i] - b[i];
    }
    return result;
}

Vector vec_mul(const Vector& a, const Vector& b) {
    Vector result(a.size());
    for (size_t i = 0; i < a.size(); i++) {
        result[i] = a[i] * b[i];
    }
    return result;
}

Vector matvec(const Matrix& M, const Vector& v) {
    Vector result(M.size(), 0.0);
    for (size_t i = 0; i < M.size(); i++) {
        for (size_t j = 0; j < v.size(); j++) {
            result[i] += M[i][j] * v[j];
        }
    }
    return result;
}

Vector softmax(const Vector& v) {
    double max_val = *std::max_element(v.begin(), v.end());
    Vector exp_v(v.size());
    double sum = 0.0;
    for (size_t i = 0; i < v.size(); i++) {
        exp_v[i] = std::exp(v[i] - max_val);
        sum += exp_v[i];
    }
    for (size_t i = 0; i < v.size(); i++) {
        exp_v[i] /= sum;
    }
    return exp_v;
}

double cross_entropy(const Vector& predicted, int target) {
    double eps = 1e-12;
    return -std::log(std::max(predicted[target], eps));
}

void init_matrix(Matrix& M, double std_dev) {
    std::mt19937 gen(42);
    std::normal_distribution<> dist(0.0, std_dev);
    for (auto& row : M) {
        for (auto& val : row) {
            val = dist(gen);
        }
    }
}

void init_lstm_weights(LSTMParams& params) {
    int concat = params.hidden_size + params.input_size;
    double std_val = std::sqrt(2.0 / concat);

    init_matrix(params.W_f, std_val);
    init_matrix(params.W_i, std_val);
    init_matrix(params.W_c, std_val);
    init_matrix(params.W_o, std_val);
    init_matrix(params.W_y, std_val);

    // Bias do forget gate = 1.0 (importante!)
    for (auto& val : params.b_f) val = 1.0;
}
```

### 8.3 Forward Pass

```cpp
LSTMCache lstm_forward(const LSTMParams& params, const std::vector<Vector>& inputs) {
    int seq_len = inputs.size();
    int cs = params.cell_size;

    LSTMCache cache;
    cache.inputs = inputs;
    cache.hidden_states.resize(seq_len + 1);
    cache.cell_states.resize(seq_len + 1);
    cache.forget_gates.resize(seq_len);
    cache.input_gates.resize(seq_len);
    cache.cell_candidates.resize(seq_len);
    cache.output_gates.resize(seq_len);
    cache.outputs.resize(seq_len);

    // Inicializar h_0 e c_0 com zeros
    cache.hidden_states[0] = create_vector(cs);
    cache.cell_states[0] = create_vector(cs);

    for (int t = 0; t < seq_len; t++) {
        Vector h_prev = cache.hidden_states[t];
        Vector c_prev = cache.cell_states[t];
        Vector x_t = inputs[t];

        // Concatenar [h_{t-1}, x_t]
        Vector concat_hx = concat(h_prev, x_t);

        // Forget gate: f_t = sigmoid(W_f * [h, x] + b_f)
        Vector f_t = sigmoid(vec_add(matvec(params.W_f, concat_hx), params.b_f));
        cache.forget_gates[t] = f_t;

        // Input gate: i_t = sigmoid(W_i * [h, x] + b_i)
        Vector i_t = sigmoid(vec_add(matvec(params.W_i, concat_hx), params.b_i));
        cache.input_gates[t] = i_t;

        // Cell candidate: c~_t = tanh(W_c * [h, x] + b_c)
        Vector c_cand = tanh_vec(vec_add(matvec(params.W_c, concat_hx), params.b_c));
        cache.cell_candidates[t] = c_cand;

        // Cell state: c_t = f_t * c_{t-1} + i_t * c~_t
        Vector c_new = vec_add(vec_mul(f_t, c_prev), vec_mul(i_t, c_cand));
        cache.cell_states[t + 1] = c_new;

        // Output gate: o_t = sigmoid(W_o * [h, x] + b_o)
        Vector o_t = sigmoid(vec_add(matvec(params.W_o, concat_hx), params.b_o));
        cache.output_gates[t] = o_t;

        // Hidden state: h_t = o_t * tanh(c_t)
        Vector h_new = vec_mul(o_t, tanh_vec(c_new));
        cache.hidden_states[t + 1] = h_new;

        // Output projection: y_t = softmax(W_y * h_t + b_y)
        Vector logits = vec_add(matvec(params.W_y, h_new), params.b_y);
        cache.outputs[t] = softmax(logits);
    }

    return cache;
}
```

### 8.4 Backward Pass

```cpp
LSTMGrads lstm_backward(
    const LSTMParams& params,
    const LSTMCache& cache,
    const std::vector<int>& targets,
    int seq_len
) {
    int cs = params.cell_size;
    int concat = params.hidden_size + params.input_size;

    LSTMGrads grads(params.input_size, params.hidden_size, cs, params.output_size);

    Vector dh_next(cs, 0.0);
    Vector dc_next(cs, 0.0);

    for (int t = seq_len - 1; t >= 0; t--) {
        // Gradiente da saida
        Vector dy = cache.outputs[t];
        dy[targets[t]] -= 1.0;

        // dW_y += dy * h_t^T
        for (int i = 0; i < params.output_size; i++) {
            for (int j = 0; j < cs; j++) {
                grads.dW_y[i][j] += dy[i] * cache.hidden_states[t + 1][j];
            }
            grads.db_y[i] += dy[i];
        }

        // dh = W_y^T * dy + dh_next
        Vector dh(cs, 0.0);
        for (int j = 0; j < cs; j++) {
            for (int i = 0; i < params.output_size; i++) {
                dh[j] += params.W_y[i][j] * dy[i];
            }
            dh[j] += dh_next[j];
        }

        Vector& o_t = cache.output_gates[t];
        Vector& c_t = cache.cell_states[t + 1];
        Vector& c_prev = cache.cell_states[t];
        Vector& f_t = cache.forget_gates[t];
        Vector& i_t = cache.input_gates[t];
        Vector& c_cand = cache.cell_candidates[t];

        // dh = o_t * tanh(c_t) -> do = dh * tanh(c_t)
        Vector tanh_c = tanh_vec(c_t);
        Vector do_gate = vec_mul(dh, tanh_c);

        // dc += dh * o_t * (1 - tanh^2(c_t))
        Vector dtanh_c = tanh_deriv(tanh_c);
        Vector dc = vec_mul(vec_mul(dh, o_t), dtanh_c);
        for (int j = 0; j < cs; j++) {
            dc[j] += dc_next[j];
        }

        // di = dc * c~_t
        Vector di = vec_mul(dc, c_cand);

        // df = dc * c_{t-1}
        Vector df = vec_mul(dc, c_prev);

        // dc_prev = dc * f_t
        Vector dc_prev_new = vec_mul(dc, f_t);

        // dc~ = dc * i_t
        Vector dc_cand = vec_mul(dc, i_t);

        // Backprop through gates
        Vector do_raw = vec_mul(do_gate, sigmoid_deriv(o_t));
        Vector di_raw = vec_mul(di, sigmoid_deriv(i_t));
        Vector df_raw = vec_mul(df, sigmoid_deriv(f_t));
        Vector dc_cand_raw = vec_mul(dc_cand, tanh_deriv(c_cand));

        // Concatenar [h_{t-1}, x_t] para gradientes
        Vector concat_hx = concat(cache.hidden_states[t], cache.inputs[t]);

        // dW_o += do_raw * [h, x]^T
        for (int j = 0; j < cs; j++) {
            for (int i = 0; i < concat; i++) {
                grads.dW_o[j][i] += do_raw[j] * concat_hx[i];
            }
            grads.db_o[j] += do_raw[j];
        }

        // dW_i += di_raw * [h, x]^T
        for (int j = 0; j < cs; j++) {
            for (int i = 0; i < concat; i++) {
                grads.dW_i[j][i] += di_raw[j] * concat_hx[i];
            }
            grads.db_i[j] += di_raw[j];
        }

        // dW_f += df_raw * [h, x]^T
        for (int j = 0; j < cs; j++) {
            for (int i = 0; i < concat; i++) {
                grads.dW_f[j][i] += df_raw[j] * concat_hx[i];
            }
            grads.db_f[j] += df_raw[j];
        }

        // dW_c += dc_cand_raw * [h, x]^T
        for (int j = 0; j < cs; j++) {
            for (int i = 0; i < concat; i++) {
                grads.dW_c[j][i] += dc_cand_raw[j] * concat_hx[i];
            }
            grads.db_c[j] += dc_cand_raw[j];
        }

        // dh_prev = W_o^T * do_raw + W_i^T * di_raw + W_f^T * df_raw + W_c^T * dc_cand_raw
        Vector dh_prev(cs, 0.0);
        for (int i = 0; i < cs; i++) {
            for (int j = 0; j < cs; j++) {
                dh_prev[i] += params.W_o[j][i] * do_raw[j];
                dh_prev[i] += params.W_i[j][i] * di_raw[j];
                dh_prev[i] += params.W_f[j][i] * df_raw[j];
                dh_prev[i] += params.W_c[j][i] * dc_cand_raw[j];
            }
        }

        dh_next = dh_prev;
        dc_next = dc_prev_new;
    }

    return grads;
}
```

### 8.5 Treinamento

```cpp
void update_lstm(LSTMParams& params, const LSTMGrads& grads, double lr, int seq_len) {
    double scale = lr / seq_len;
    int concat = params.hidden_size + params.input_size;

    auto update_m = [&](Matrix& W, const Matrix& dW, int rows, int cols) {
        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                W[i][j] -= scale * dW[i][j];
            }
        }
    };

    auto update_v = [&](Vector& b, const Vector& db) {
        for (size_t i = 0; i < b.size(); i++) {
            b[i] -= scale * db[i];
        }
    };

    update_m(params.W_f, grads.dW_f, params.cell_size, concat);
    update_v(params.b_f, grads.db_f);

    update_m(params.W_i, grads.dW_i, params.cell_size, concat);
    update_v(params.b_i, grads.db_i);

    update_m(params.W_c, grads.dW_c, params.cell_size, concat);
    update_v(params.b_c, grads.db_c);

    update_m(params.W_o, grads.dW_o, params.cell_size, concat);
    update_v(params.b_o, grads.db_o);

    update_m(params.W_y, grads.dW_y, params.output_size, params.cell_size);
    update_v(params.b_y, grads.db_y);
}

double train_lstm(
    LSTMParams& params,
    const std::vector<std::vector<Vector>>& all_inputs,
    const std::vector<std::vector<int>>& all_targets,
    double lr,
    int epochs,
    double clip_norm,
    bool verbose
) {
    init_lstm_weights(params);
    int num_seq = all_inputs.size();
    double final_loss = 0.0;

    for (int e = 0; e < epochs; e++) {
        double epoch_loss = 0.0;

        for (int s = 0; s < num_seq; s++) {
            int seq_len = all_inputs[s].size();
            auto cache = lstm_forward(params, all_inputs[s]);

            double seq_loss = 0.0;
            for (int t = 0; t < seq_len; t++) {
                seq_loss += cross_entropy(cache.outputs[t], all_targets[s][t]);
            }
            epoch_loss += seq_loss;

            auto grads = lstm_backward(params, cache, all_targets[s], seq_len);

            // Gradient clipping
            double total_norm = 0.0;
            for (const auto& row : grads.dW_f) for (double g : row) total_norm += g * g;
            for (const auto& row : grads.dW_i) for (double g : row) total_norm += g * g;
            for (const auto& row : grads.dW_c) for (double g : row) total_norm += g * g;
            for (const auto& row : grads.dW_o) for (double g : row) total_norm += g * g;
            for (const auto& row : grads.dW_y) for (double g : row) total_norm += g * g;
            total_norm = std::sqrt(total_norm);

            if (total_norm > clip_norm) {
                double scale_cl = clip_norm / total_norm;
                auto clip_m = [&](Matrix& m) {
                    for (auto& row : m) for (double& g : row) g *= scale_cl;
                };
                clip_m(grads.dW_f);
                clip_m(grads.dW_i);
                clip_m(grads.dW_c);
                clip_m(grads.dW_o);
                clip_m(grads.dW_y);
                for (double& g : grads.db_f) g *= scale_cl;
                for (double& g : grads.db_i) g *= scale_cl;
                for (double& g : grads.db_c) g *= scale_cl;
                for (double& g : grads.db_o) g *= scale_cl;
                for (double& g : grads.db_y) g *= scale_cl;
            }

            update_lstm(params, grads, lr, seq_len);
        }

        epoch_loss /= num_seq;
        if (verbose && (e % 10 == 0 || e == epochs - 1)) {
            std::cout << "Epoch " << e << " | Loss: " << epoch_loss << std::endl;
        }
        final_loss = epoch_loss;
    }

    return final_loss;
}
```

### 8.6 Exemplo Completo

```cpp
int main() {
    int input_size = 1;
    int hidden_size = 64;
    int output_size = 10;
    int seq_len = 50;

    LSTMParams params(input_size, hidden_size, output_size);

    std::vector<std::vector<Vector>> all_inputs;
    std::vector<std::vector<int>> all_targets;

    for (int i = 0; i < 200; i++) {
        std::vector<Vector> inputs;
        std::vector<int> targets;
        double phase = i * 0.05;

        for (int t = 0; t < seq_len; t++) {
            inputs.push_back({std::sin(phase + t * 0.1) + 0.3 * std::sin(phase + t * 0.3)});
            double next = std::sin(phase + (t + 1) * 0.1) + 0.3 * std::sin(phase + (t + 1) * 0.3);
            int bin = static_cast<int>((next + 1.5) * 4.0);
            targets.push_back(std::max(0, std::min(bin, output_size - 1)));
        }

        all_inputs.push_back(inputs);
        all_targets.push_back(targets);
    }

    double final_loss = train_lstm(params, all_inputs, all_targets, 0.005, 200, 5.0, true);

    std::cout << "\nLSTM Treinamento concluido!" << std::endl;
    std::cout << "Loss final: " << final_loss << std::endl;
    std::cout << "Parametros: "
              << 4 * params.cell_size * (params.hidden_size + params.input_size + 1)
              << std::endl;

    return 0;
}
```

---

## 9. Implementacao em Rust

### 9.1 Modulo LSTM

```rust
type Vector = Vec<f64>;
type Matrix = Vec<Vec<f64>>;

fn create_matrix(rows: usize, cols: usize, init: f64) -> Matrix {
    (0..rows).map(|_| vec![init; cols]).collect()
}

fn create_vector(size: usize, init: f64) -> Vector {
    vec![init; size]
}

fn concat(a: &Vector, b: &Vector) -> Vector {
    let mut result = Vec::with_capacity(a.len() + b.len());
    result.extend_from_slice(a);
    result.extend_from_slice(b);
    result
}

fn sigmoid(v: &Vector) -> Vector {
    v.iter().map(|x| 1.0 / (1.0 + (-x).exp())).collect()
}

fn sigmoid_deriv(s: &Vector) -> Vector {
    s.iter().map(|x| x * (1.0 - x)).collect()
}

fn tanh_activate(v: &Vector) -> Vector {
    v.iter().map(|x| x.tanh()).collect()
}

fn tanh_deriv(h: &Vector) -> Vector {
    h.iter().map(|x| 1.0 - x * x).collect()
}

fn vec_add(a: &Vector, b: &Vector) -> Vector {
    a.iter().zip(b.iter()).map(|(x, y)| x + y).collect()
}

fn vec_mul(a: &Vector, b: &Vector) -> Vector {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).collect()
}

fn matvec(m: &Matrix, v: &Vector) -> Vector {
    m.iter().map(|row| row.iter().zip(v.iter()).map(|(a, b)| a * b).sum()).collect()
}

fn softmax(v: &Vector) -> Vector {
    let max_val = v.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let exp_v: Vector = v.iter().map(|x| (x - max_val).exp()).collect();
    let sum: f64 = exp_v.iter().sum();
    exp_v.iter().map(|x| x / sum).collect()
}

fn cross_entropy(predicted: &Vector, target: usize) -> f64 {
    -((predicted[target]).max(1e-12)).ln()
}

struct LSTMParams {
    w_f: Matrix, b_f: Vector,
    w_i: Matrix, b_i: Vector,
    w_c: Matrix, b_c: Vector,
    w_o: Matrix, b_o: Vector,
    w_y: Matrix, b_y: Vector,
    input_size: usize,
    hidden_size: usize,
    cell_size: usize,
    output_size: usize,
}

struct LSTMCache {
    inputs: Vec<Vector>,
    hidden_states: Vec<Vector>,
    cell_states: Vec<Vector>,
    forget_gates: Vec<Vector>,
    input_gates: Vec<Vector>,
    cell_candidates: Vec<Vector>,
    output_gates: Vec<Vector>,
    outputs: Vec<Vector>,
}

impl LSTMParams {
    fn new(input_size: usize, hidden_size: usize, output_size: usize) -> Self {
        let concat = hidden_size + input_size;
        Self {
            w_f: create_matrix(concat, hidden_size, 0.0),
            b_f: vec![1.0; hidden_size],
            w_i: create_matrix(concat, hidden_size, 0.0),
            b_i: create_vector(hidden_size, 0.0),
            w_c: create_matrix(concat, hidden_size, 0.0),
            b_c: create_vector(hidden_size, 0.0),
            w_o: create_matrix(concat, hidden_size, 0.0),
            b_o: create_vector(hidden_size, 0.0),
            w_y: create_matrix(output_size, hidden_size, 0.0),
            b_y: create_vector(output_size, 0.0),
            input_size,
            hidden_size,
            cell_size: hidden_size,
            output_size,
        }
    }

    fn init_weights(&mut self) {
        use std::f64::consts::SQRT_2;
        let concat = self.hidden_size + self.input_size;
        let std_val = (SQRT_2 / concat as f64).sqrt();
        randomize(&mut self.w_f, std_val);
        randomize(&mut self.w_i, std_val);
        randomize(&mut self.w_c, std_val);
        randomize(&mut self.w_o, std_val);
        randomize(&mut self.w_y, std_val);
    }
}

fn randomize(m: &mut Matrix, std_dev: f64) {
    let mut seed: u64 = 12345;
    for row in m.iter_mut() {
        for val in row.iter_mut() {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u = (seed >> 11) as f64 / (1u64 << 53) as f64;
            let z = (-2.0 * (1.0 - u).ln()).sqrt()
                * (2.0 * std::f64::consts::PI * ((seed >> 11) as f64 / (1u64 << 53) as f64)).cos();
            *val = z * std_dev;
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        }
    }
}

fn lstm_forward(params: &LSTMParams, inputs: &[Vector]) -> LSTMCache {
    let seq_len = inputs.len();
    let cs = params.cell_size;
    let mut cache = LSTMCache {
        inputs: inputs.to_vec(),
        hidden_states: vec![create_vector(cs, 0.0)],
        cell_states: vec![create_vector(cs, 0.0)],
        forget_gates: Vec::with_capacity(seq_len),
        input_gates: Vec::with_capacity(seq_len),
        cell_candidates: Vec::with_capacity(seq_len),
        output_gates: Vec::with_capacity(seq_len),
        outputs: Vec::with_capacity(seq_len),
    };

    for t in 0..seq_len {
        let h_prev = &cache.hidden_states[t];
        let c_prev = &cache.cell_states[t];
        let concat_hx = concat(h_prev, &inputs[t]);

        let f_t = sigmoid(&vec_add(&matvec(&params.w_f, &concat_hx), &params.b_f));
        let i_t = sigmoid(&vec_add(&matvec(&params.w_i, &concat_hx), &params.b_i));
        let c_cand = tanh_activate(&vec_add(&matvec(&params.w_c, &concat_hx), &params.b_c));
        let c_new = vec_add(&vec_mul(&f_t, c_prev), &vec_mul(&i_t, &c_cand));
        let o_t = sigmoid(&vec_add(&matvec(&params.w_o, &concat_hx), &params.b_o));
        let h_new = vec_mul(&o_t, &tanh_activate(&c_new));

        cache.forget_gates.push(f_t);
        cache.input_gates.push(i_t);
        cache.cell_candidates.push(c_cand);
        cache.cell_states.push(c_new);
        cache.output_gates.push(o_t);
        cache.hidden_states.push(h_new.clone());

        let logits = vec_add(&matvec(&params.w_y, &h_new), &params.b_y);
        cache.outputs.push(softmax(&logits));
    }

    cache
}

fn main() {
    let input_size = 1;
    let hidden_size = 64;
    let output_size = 10;
    let seq_len = 50;

    let mut params = LSTMParams::new(input_size, hidden_size, output_size);
    params.init_weights();

    let mut all_inputs: Vec<Vec<Vector>> = Vec::new();
    let mut all_targets: Vec<Vec<usize>> = Vec::new();

    for i in 0..200 {
        let mut inputs = Vec::new();
        let mut targets = Vec::new();
        let phase = i as f64 * 0.05;

        for t in 0..seq_len {
            inputs.push(vec![(phase + t as f64 * 0.1).sin() + 0.3 * (phase + t as f64 * 0.3).sin()]);
            let next = (phase + (t + 1) as f64 * 0.1).sin() + 0.3 * (phase + (t + 1) as f64 * 0.3).sin();
            let bin = ((next + 1.5) * 4.0) as usize;
            targets.push(bin.min(output_size - 1));
        }

        all_inputs.push(inputs);
        all_targets.push(targets);
    }

    for e in 0..200 {
        let mut epoch_loss = 0.0;
        for s in 0..all_inputs.len() {
            let cache = lstm_forward(&params, &all_inputs[s]);
            let mut seq_loss = 0.0;
            for t in 0..seq_len {
                seq_loss += cross_entropy(&cache.outputs[t], all_targets[s][t]);
            }
            epoch_loss += seq_loss;
        }
        epoch_loss /= all_inputs.len() as f64;
        if e % 10 == 0 { println!("Epoch {} | LSTM Loss: {:.6}", e, epoch_loss); }
    }

    println!("LSTM Treinamento concluido!");
}
```

---

## 10. Implementacao em Fortran

### 10.1 Modulo LSTM

```fortran
module lstm_module
    implicit none
    private
    public :: lstm_forward_step, lstm_forward_seq

contains

    subroutine lstm_forward_step(x_t, h_prev, c_prev, &
                                 W_f, b_f, W_i, b_i, W_c, b_c, W_o, b_o, &
                                 h_new, c_new, f_t, i_t, o_t, c_cand, &
                                 input_size, cell_size)
        implicit none
        integer, intent(in) :: input_size, cell_size
        real(8), intent(in) :: x_t(input_size)
        real(8), intent(in) :: h_prev(cell_size)
        real(8), intent(in) :: c_prev(cell_size)
        real(8), intent(in) :: W_f(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_f(cell_size)
        real(8), intent(in) :: W_i(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_i(cell_size)
        real(8), intent(in) :: W_c(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_c(cell_size)
        real(8), intent(in) :: W_o(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_o(cell_size)
        real(8), intent(out) :: h_new(cell_size)
        real(8), intent(out) :: c_new(cell_size)
        real(8), intent(out) :: f_t(cell_size)
        real(8), intent(out) :: i_t(cell_size)
        real(8), intent(out) :: o_t(cell_size)
        real(8), intent(out) :: c_cand(cell_size)

        real(8) :: concat_hx(cell_size + input_size)
        real(8) :: pre_act(cell_size)
        integer :: i, j

        ! Concatenate [h_prev, x_t]
        do i = 1, cell_size
            concat_hx(i) = h_prev(i)
        end do
        do i = 1, input_size
            concat_hx(cell_size + i) = x_t(i)
        end do

        ! Forget gate: f_t = sigmoid(W_f * [h, x] + b_f)
        do i = 1, cell_size
            pre_act(i) = b_f(i)
            do j = 1, cell_size + input_size
                pre_act(i) = pre_act(i) + W_f(i, j) * concat_hx(j)
            end do
            f_t(i) = 1.0d0 / (1.0d0 + exp(-pre_act(i)))
        end do

        ! Input gate: i_t = sigmoid(W_i * [h, x] + b_i)
        do i = 1, cell_size
            pre_act(i) = b_i(i)
            do j = 1, cell_size + input_size
                pre_act(i) = pre_act(i) + W_i(i, j) * concat_hx(j)
            end do
            i_t(i) = 1.0d0 / (1.0d0 + exp(-pre_act(i)))
        end do

        ! Cell candidate: c~ = tanh(W_c * [h, x] + b_c)
        do i = 1, cell_size
            pre_act(i) = b_c(i)
            do j = 1, cell_size + input_size
                pre_act(i) = pre_act(i) + W_c(i, j) * concat_hx(j)
            end do
            c_cand(i) = tanh(pre_act(i))
        end do

        ! Cell state: c_t = f_t * c_{t-1} + i_t * c~
        do i = 1, cell_size
            c_new(i) = f_t(i) * c_prev(i) + i_t(i) * c_cand(i)
        end do

        ! Output gate: o_t = sigmoid(W_o * [h, x] + b_o)
        do i = 1, cell_size
            pre_act(i) = b_o(i)
            do j = 1, cell_size + input_size
                pre_act(i) = pre_act(i) + W_o(i, j) * concat_hx(j)
            end do
            o_t(i) = 1.0d0 / (1.0d0 + exp(-pre_act(i)))
        end do

        ! Hidden state: h_t = o_t * tanh(c_t)
        do i = 1, cell_size
            h_new(i) = o_t(i) * tanh(c_new(i))
        end do
    end subroutine lstm_forward_step

    subroutine lstm_forward_seq(inputs, seq_len, &
                                W_f, b_f, W_i, b_i, W_c, b_c, W_o, b_o, &
                                hidden_states, cell_states, &
                                forget_gates, input_gates, output_gates, candidates, &
                                input_size, cell_size)
        implicit none
        integer, intent(in) :: seq_len, input_size, cell_size
        real(8), intent(in) :: inputs(input_size, seq_len)
        real(8), intent(in) :: W_f(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_f(cell_size)
        real(8), intent(in) :: W_i(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_i(cell_size)
        real(8), intent(in) :: W_c(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_c(cell_size)
        real(8), intent(in) :: W_o(cell_size, cell_size + input_size)
        real(8), intent(in) :: b_o(cell_size)
        real(8), intent(out) :: hidden_states(cell_size, seq_len + 1)
        real(8), intent(out) :: cell_states(cell_size, seq_len + 1)
        real(8), intent(out) :: forget_gates(cell_size, seq_len)
        real(8), intent(out) :: input_gates(cell_size, seq_len)
        real(8), intent(out) :: output_gates(cell_size, seq_len)
        real(8), intent(out) :: candidates(cell_size, seq_len)

        real(8) :: h_prev(cell_size), c_prev(cell_size)
        real(8) :: h_new(cell_size), c_new(cell_size)
        real(8) :: f_t(cell_size), i_t(cell_size), o_t(cell_size), c_cand(cell_size)
        integer :: t, i

        ! h_0, c_0 = zeros
        do i = 1, cell_size
            hidden_states(i, 1) = 0.0d0
            cell_states(i, 1) = 0.0d0
        end do

        do t = 1, seq_len
            h_prev = hidden_states(:, t)
            c_prev = cell_states(:, t)
            call lstm_forward_step(inputs(:, t), h_prev, c_prev, &
                                   W_f, b_f, W_i, b_i, W_c, b_c, W_o, b_o, &
                                   h_new, c_new, f_t, i_t, o_t, c_cand, &
                                   input_size, cell_size)
            hidden_states(:, t + 1) = h_new
            cell_states(:, t + 1) = c_new
            forget_gates(:, t) = f_t
            input_gates(:, t) = i_t
            output_gates(:, t) = o_t
            candidates(:, t) = c_cand
        end do
    end subroutine lstm_forward_seq

end module lstm_module
```

### 10.2 Programa Principal

```fortran
program lstm_example
    use lstm_module
    implicit none

    integer, parameter :: input_size = 1
    integer, parameter :: cell_size = 32
    integer, parameter :: seq_len = 20
    integer, parameter :: num_samples = 100
    integer, parameter :: epochs = 100
    real(8), parameter :: lr = 0.01d0

    real(8) :: W_f(cell_size, cell_size + input_size)
    real(8) :: W_i(cell_size, cell_size + input_size)
    real(8) :: W_c(cell_size, cell_size + input_size)
    real(8) :: W_o(cell_size, cell_size + input_size)
    real(8) :: b_f(cell_size), b_i(cell_size), b_c(cell_size), b_o(cell_size)

    real(8) :: inputs(input_size, seq_len)
    real(8) :: hidden_states(cell_size, seq_len + 1)
    real(8) :: cell_states(cell_size, seq_len + 1)
    real(8) :: forget_gates(cell_size, seq_len)
    real(8) :: input_gates(cell_size, seq_len)
    real(8) :: output_gates(cell_size, seq_len)
    real(8) :: candidates(cell_size, seq_len)

    real(8) :: phase, epoch_loss
    integer :: e, s, t

    ! Initialize weights
    call random_number(W_f); W_f = (W_f - 0.5d0) * 0.1d0
    call random_number(W_i); W_i = (W_i - 0.5d0) * 0.1d0
    call random_number(W_c); W_c = (W_c - 0.5d0) * 0.1d0
    call random_number(W_o); W_o = (W_o - 0.5d0) * 0.1d0
    b_f = 1.0d0  ! Forget gate bias = 1 (importante!)
    b_i = 0.0d0
    b_c = 0.0d0
    b_o = 0.0d0

    do e = 0, epochs - 1
        epoch_loss = 0.0d0
        do s = 1, num_samples
            phase = dble(s) * 0.1d0
            do t = 1, seq_len
                inputs(1, t) = sin(phase + dble(t) * 0.1d0) + &
                               0.3d0 * sin(phase + dble(t) * 0.3d0)
            end do

            call lstm_forward_seq(inputs, seq_len, &
                                  W_f, b_f, W_i, b_i, W_c, b_c, W_o, b_o, &
                                  hidden_states, cell_states, &
                                  forget_gates, input_gates, output_gates, candidates, &
                                  input_size, cell_size)
        end do

        if (mod(e, 10) == 0) then
            write(*, '(A, I4, A, F10.6)') 'Epoch ', e, ' | LSTM Loss: ', &
                epoch_loss / dble(num_samples)
        end if
    end do

    write(*, *) 'LSTM Treinamento concluido!'
end program lstm_example
```

---

## 11. Bidirectional LSTM

### 11.1 Conceito

Assim como Bidirectional RNN, o Bidirectional LSTM processa a sequencia em ambas as direcoes, mas usando LSTM em vez de RNN simples.

```text
Bidirectional LSTM:

Forward LSTM:
  x_1 ->[LSTM_f]-> h_f1 -> h_f2 -> h_f3

Backward LSTM:
  x_3 ->[LSTM_b]-> h_b3
  x_2 ->[LSTM_b]-> h_b2
  x_1 ->[LSTM_b]-> h_b1

Saida concatenada:
  y_1 = [h_f1; h_b1]
  y_2 = [h_f2; h_b2]
  y_3 = [h_f3; h_b3]

Cada direcao tem:
- Seus proprios W_f, W_i, W_c, W_o
- Seus proprios b_f, b_i, b_c, b_o
- Seus proprios cell state e hidden state
```

### 11.2 Implementacao

```cpp
struct BiLSTMParams {
    LSTMParams forward;
    LSTMParams backward;

    BiLSTMParams(int input_size, int hidden_size, int output_size)
        : forward(input_size, hidden_size, hidden_size),
          backward(input_size, hidden_size, hidden_size)
    {
        // Saida concatena ambas as direcoes
        forward.W_y = create_matrix(hidden_size, hidden_size * 2);
        backward.W_y = create_matrix(output_size, hidden_size * 2);
    }
};

struct BiLSTMCache {
    LSTMCache forward_cache;
    LSTMCache backward_cache;
    std::vector<Vector> outputs;  // concatenados
};

BiLSTMCache bilstm_forward(
    const BiLSTMParams& params,
    const std::vector<Vector>& inputs
) {
    int seq_len = inputs.size();

    // Forward
    auto fwd_cache = lstm_forward(params.forward, inputs);

    // Backward (reverter sequencia)
    std::vector<Vector> reversed = inputs;
    std::reverse(reversed.begin(), reversed.end());
    auto bwd_cache = lstm_forward(params.backward, reversed);

    // Concatenar saidas
    BiLSTMCache cache;
    cache.forward_cache = fwd_cache;
    cache.backward_cache = bwd_cache;
    cache.outputs.resize(seq_len);

    for (int t = 0; t < seq_len; t++) {
        Vector concat_h = concat(
            fwd_cache.hidden_states[t + 1],
            bwd_cache.hidden_states[seq_len - t]
        );
        cache.outputs[t] = concat_h;
    }

    return cache;
}
```

---

## 12. Exemplo: Previsao de Sequencias Longas

### 12.1 Configuracao

```text
Tarefa: Prever sinais complexos com dependencias de longo prazo

Sinal composto:
  x(t) = sin(0.01*t) + 0.5*sin(0.05*t) + 0.3*sin(0.1*t) + ruido

Caracteristicas:
- Frequencia baixa (0.01): ciclo de 628 passos
- Frequencia media (0.05): ciclo de 126 passos
- Frequencia alta (0.1): ciclo de 63 passos
- Para prever bem, a rede precisa "lembrar" de ~600 passos

Configuracao:
- Sequencia de entrada: 500 passos
- Saida: proximo valor
- Hidden size: 128
- Cell size: 128
- Epochs: 500
```

### 12.2 Codigo Completo

```cpp
// Previsao de sequencia longa com LSTM

std::vector<Vector> generate_complex_signal(int total_length) {
    std::vector<Vector> signal;
    std::mt19937 gen(42);
    std::normal_distribution<> noise(0.0, 0.05);

    for (int t = 0; t < total_length; t++) {
        double val = std::sin(0.01 * t)
                   + 0.5 * std::sin(0.05 * t)
                   + 0.3 * std::sin(0.1 * t)
                   + noise(gen);
        signal.push_back({val});
    }
    return signal;
}

int main() {
    auto signal = generate_complex_signal(2000);

    int input_size = 1;
    int hidden_size = 128;
    int output_size = 1;
    int seq_len = 500;

    LSTMParams params(input_size, hidden_size, output_size);

    std::vector<std::vector<Vector>> all_inputs;
    std::vector<std::vector<int>> all_targets;

    for (int i = 0; i + seq_len + 1 < (int)signal.size(); i += 10) {
        std::vector<Vector> inputs;
        std::vector<int> targets;

        for (int t = 0; t < seq_len; t++) {
            inputs.push_back(signal[i + t]);
            double next = signal[i + t + 1][0];
            int bin = static_cast<int>((next + 2.0) * 5.0);
            targets.push_back(std::max(0, std::min(bin, output_size - 1)));
        }

        all_inputs.push_back(inputs);
        all_targets.push_back(targets);
    }

    std::cout << "Sequencias de treinamento: " << all_inputs.size() << std::endl;
    std::cout << "Comprimento: " << seq_len << std::endl;

    double final_loss = train_lstm(params, all_inputs, all_targets, 0.001, 500, 10.0, true);

    std::cout << "\n=== Resultados ===" << std::endl;
    std::cout << "Loss final: " << final_loss << std::endl;
    std::cout << "Parametros: "
              << 4 * params.cell_size * (params.hidden_size + params.input_size + 1)
              << std::endl;

    return 0;
}
```

---

## 13. Stack de LSTMs

### 13.1 Conceito

Um Stack de LSTMs e quando varias camadas LSTM sao empilhadas, onde a saida de uma camada e a entrada da proxima.

```text
Stack de LSTMs:

Camada 4 (mais profunda):   -> h_4_t -> saida
          ^
Camada 3:                    -> h_3_t
          ^
Camada 2:                    -> h_2_t
          ^
Camada 1 (mais rasa): x_t -> h_1_t

Cada camada tem seus PROPRIOS parametros.
A camada 1 processa a entrada original.
Camadas superiores processam features mais abstratas.
```

### 13.2 Por Que Empilhar?

```text
Vantagens do Stack:

1. Hierarquia de features:
   - Camada 1: features de baixo nivel (fonemas, caracteres)
   - Camada 2: features de medio nivel (palavras, frases)
   - Camada 3: features de alto nivel (sentimento, intencao)
   - Camada 4: decisao final

2. Mais capacidade:
   - Mais parametros = mais poder de representacao
   - Cada camada pode aprender transformacoes complexas

3. Representacao mais rica:
   - A saida da camada anterior e uma representacao
     mais densa e abstrata da sequencia
   - Permite aprendizado de padroes compostos

Desvantagens:
- Mais parametros (risco de overfitting)
- Mais lento de treinar
- Mais dificil de otimizar (vanishing gradient entre camadas)
- Mais memoria necessaria
```

### 13.3 Implementacao

```cpp
struct StackedLSTMParams {
    std::vector<LSTMParams> layers;

    StackedLSTMParams(int input_size, int hidden_size, int output_size, int num_layers) {
        for (int i = 0; i < num_layers; i++) {
            int in_size = (i == 0) ? input_size : hidden_size;
            int out_size = (i == num_layers - 1) ? hidden_size : hidden_size;
            layers.emplace_back(in_size, hidden_size, out_size);
        }
        // Camada de saida final
        layers.back().W_y = create_matrix(output_size, hidden_size);
        layers.back().b_y = create_vector(output_size);
        layers.back().output_size = output_size;
    }
};

struct StackedLSTMCache {
    std::vector<LSTMCache> layer_caches;
};

StackedLSTMCache stacked_lstm_forward(
    const StackedLSTMParams& params,
    const std::vector<Vector>& inputs
) {
    StackedLSTMCache cache;
    cache.layer_caches.resize(params.layers.size());

    std::vector<Vector> current_input = inputs;

    for (size_t layer = 0; layer < params.layers.size(); layer++) {
        cache.layer_caches[layer] = lstm_forward(params.layers[layer], current_input);

        // A entrada da proxima camada e o hidden state desta camada
        current_input.clear();
        for (size_t t = 0; t < cache.layer_caches[layer].hidden_states.size() - 1; t++) {
            current_input.push_back(cache.layer_caches[layer].hidden_states[t + 1]);
        }
    }

    return cache;
}
```

### 13.4 Exemplo de Configuracao

```cpp
int main() {
    int input_size = 100;   // word embeddings
    int hidden_size = 256;  // por camada
    int output_size = 2;    // classificacao binaria
    int num_layers = 3;     // 3 camadas LSTM

    StackedLSTMParams params(input_size, hidden_size, output_size, num_layers);

    std::cout << "Stacked LSTM (" << num_layers << " layers)" << std::endl;

    int total_params = 0;
    for (const auto& layer : params.layers) {
        int concat = layer.hidden_size + layer.input_size;
        total_params += 4 * layer.cell_size * (concat + 1);
        total_params += layer.output_size * (layer.cell_size + 1);
    }

    std::cout << "Total parameters: " << total_params << std::endl;

    return 0;
}
```

---

## 14. Resumo e Proximos Passos

### 14.1 Conceitos Fundamentais

```text
Resumo do Capitulo:

1. LSTM resolve vanishing gradient com CELL STATE separado
   - Cell state age como auto-estrada para gradientes
   - Gradiente flui diretamente quando forget gate ~= 1

2. Tres portoes controlam o fluxo de informacao:
   - Forget gate: decide o que esquecer
   - Input gate: decide o que lembrar
   - Output gate: decide o que expor

3. Cell state permite memorias de longo prazo:
   - Informacao pode persistir por tempo indefinido
   - Atualizacao aditiva, nao substitutiva

4. LSTM vs GRU:
   - LSTM: mais flexivel, mais parametros, melhor para seq. longas
   - GRU: mais simples, mais rapido, melhor para dados limitados

5. Bidirectional LSTM:
   - Captura contexto passado e futuro
   - Ideal para classificacao e NER

6. Stacked LSTM:
   - Mais capacidade de representacao
   - Hierarquia de features
```

### 14.2 Tabela Comparativa Final

```text
Comparacao Final: RNN vs GRU vs LSTM

| Aspecto            | RNN       | GRU       | LSTM      |
|--------------------|-----------|-----------|-----------|
| Portoes            | 0         | 2         | 3         |
| Cell state         | Nao       | Nao       | Sim       |
| Memoria longo prazo| Fraca     | Boa       | Excelente |
| Parametros (d=256) | 163K      | 245K      | 327K      |
| Velocidade         | Rapida    | Media     | Lenta     |
| Vanishing gradient | Sim       | Nao       | Nao       |
| Complexidade       | Baixa     | Media     | Alta      |
| Caso de uso        | Seq. curtas| Seq. medias| Seq. longas|
```

### 14.3 Proximo Capitulo

No proximo capitulo, veremos o mecanismo de Attention — uma forma de permitir que a rede "olhe" para qualquer parte da sequencia de entrada ao gerar cada parte da saida, resolvendo o problema do contexto fixo em Seq2Seq.

```text
Dependencias para o proximo capitulo:
- Compreender LSTM (este capitulo)
- Compreender Seq2Seq (capitulo 10)
- Operacoes matriciais (capitulo 2)
- Conceito de similaridade (capitulo 2)
```

---

## 15. Analise Detalhada dos Portoes

### 15.1 Comportamento dos Portoes ao Longo do Treinamento

Os portoes da LSTM aprendem comportamentos complexos e especificos para cada tarefa.

```text
Evolucao dos Portoes durante o Treinamento:

Epoca 0 (inicializacao):
  f_t ~= 0.5 (bias=1.0 -> sigmoid(1) = 0.73)
  i_t ~= 0.5
  o_t ~= 0.5
  Comportamento: aleatorio, portoes abertos parcialmente

Epoca 20:
  f_t varia entre 0.3 e 0.9
  i_t varia entre 0.2 e 0.8
  o_t varia entre 0.3 e 0.7
  Comportamento: comecando a discriminar

Epoca 50:
  f_t ~= 0.1 em palavras irrelevantes
  f_t ~= 0.95 em informacao critica
  i_t ~= 0.8 em substantivos/chaves
  i_t ~= 0.2 em artigos/verbos comuns
  o_t ~= 0.7 em posicoes de decisao
  Comportamento: discriminacao clara

Epoca 100:
  Portoes bem definidos
  Cell state preserva informacao por 50+ tokens
  Comportamento: otimo
```

### 15.2 Visualizacao dos Portoes

```text
Heatmap para: "O filme NAO foi tao BOM quanto esperava"

         O    filme  NAO   foi   tao   BOM   quanto  esperava
f_t:    [0.8,  0.7,  0.1,  0.6,  0.5,  0.05, 0.7,   0.8]
i_t:    [0.3,  0.7,  0.9,  0.2,  0.1,  0.95, 0.2,   0.3]
o_t:    [0.4,  0.5,  0.8,  0.3,  0.2,  0.9,  0.5,   0.6]

Analise:
- "O": f=0.8 (preservar), i=0.3 (pouco novo), o=0.4 (pouco expor)
- "filme": f=0.7 (preservar), i=0.7 (armazenar assunto), o=0.5
- "NAO": f=0.1 (ESQUECER "filme"!), i=0.9 (armazenar negacao forte!), o=0.8 (expor negacao)
- "foi": f=0.6 (manter negacao), i=0.2 (pouco novo), o=0.3
- "tao": f=0.5 (manter), i=0.1 (irrelevante), o=0.2
- "BOM": f=0.05 (ESQUECER tudo!), i=0.95 (armazenar sentimento!), o=0.9 (expor sentimento)
- "quanto": f=0.7 (preservar), i=0.2 (pouco), o=0.5
- "esperava": f=0.8 (preservar), i=0.3 (pouco), o=0.6

O forget gate e CRITICO em "NAO" e "BOM" — zera o cell state
antes de armazenar informacao conflitante.
```

### 15.3 Analise por Dimensao do Cell State

```text
Cada dimensao do cell state pode aprender funcao diferente:

Cell dimension 1: "assunto principal" (gato, filme)
  - Alto valor quando substantivo aparece
  - Preservado por longo tempo

Cell dimension 2: "sentimento" (bom, ruim, incrivel)
  - Atualizado fortemente quando adjetivo aparece
  - Forget gate zera em transicoes de sentimento

Cell dimension 3: "negacao" (nao, jamais, nunca)
  - Valor alto = frase negativa
  - Preservado ate sentimento oposto aparecer

Cell dimension 4: "intensidade" (muito, incrivelmente, um pouco)
  - Multiplica o sentimento
  - Atualizado rapidamente

Cell dimension 5-128: features mais abstratas
  - Aprendidas automaticamente
  - Dificil de interpretar
```

---

## 16. Gradientes na LSTM

### 16.1 Analise do Gradiente

```text
Gradiente da LSTM ao Longo do Tempo:

c_t = f_t * c_{t-1} + i_t * c~_t

dc_t/dc_{t-1} = f_t

O gradiente do cell state e ESCALAR por dimensao!
Nao depende de matrizes de peso!

Para T=100 passos:
  dc_T/dc_1 = prod(f_2, f_3, ..., f_T)

Se todos f_t ~= 0.9 (forget gate alto):
  dc_T/dc_1 = 0.9^99 ~= 0.00003

Se todos f_t ~= 1.0 (forget gate maximo):
  dc_T/dc_1 = 1.0^99 = 1.0

A diferenca e EXPONENCIAL!
```

### 16.2 Comparacao de Gradientes

```text
Comparacao: RNN vs GRU vs LSTM

RNN basica:
  dh_t/dh_{t-1} = W_hh * diag(1-h^2)
  Para T=50: ||grad|| ~ 0.005

GRU (z ~= 0.5):
  dh_t/dh_{t-1} ~= 0.5 + 0.5 * dh~
  Para T=50: ||grad|| ~ 0.0000003

LSTM (f ~= 0.9):
  dc_t/dc_{t-1} = f_t ~= 0.9
  Para T=50: ||grad|| ~ 0.005

LSTM (f ~= 1.0):
  dc_t/dc_{t-1} = 1.0
  Para T=50: ||grad|| = 1.0  (PERFEITO!)

A LSTM pode ter gradiente PERFEITO se os forget gates
aprendem a ficar proximos de 1.0.
```

### 16.3 Inicializacao do Bias do Forget Gate

```text
Por que b_f = 1.0 e importante:

sigmoid(0) = 0.5  -> "esquecer metade" por padrao
sigmoid(1) = 0.73 -> "lembrar 73%" por padrao
sigmoid(2) = 0.88 -> "lembrar 88%" por padrao

Com b_f = 0:
  - Rede comeca esquecendo metade
  - Cell state encolhe rapidamente
  - Gradient flow e prejudicado
  - Treinamento mais lento

Com b_f = 1:
  - Rede comeca lembrando bastante
  - Cell state e preservado
  - Gradient flow e otimo
  - Treinamento mais rapido

Implementacao:
  b_f = ones(d_c) * 1.0
  b_i = zeros(d_c)
  b_c = zeros(d_c)
  b_o = zeros(d_c)
```

---

## 17. Variacoes da LSTM

### 17.1 Variacoes Propostas na Literatura

```text
Variacoes da LSTM:

1. LSTM Padrao (Hochreiter & Schmidhuber, 1997):
   - 3 gates + cell state
   - Baseline para comparacoes

2. Peephole LSTM (Gers & Schmidhuber, 2000):
   - Gates "olham" para o cell state
   - f_t = sigmoid(W_f * [h, x] + W_p * c)
   - Mais preciso, mais parametros

3. Coupled Forget-Input Gate:
   - i_t = 1 - f_t (so um gate para esquecer/atualizar)
   - Menos parametros
   - Performance similar

4. GRU (Cho et al., 2014):
   - 2 gates, sem cell state separado
   - Mais simples, mais rapido
   - Performance comparavel

5. LSTM com Layer Normalization:
   - LayerNorm antes de cada gate
   - Mais estavel
   - Melhor para batchs grandes

6. LSTM com Dropout Recorrente:
   - Dropout no hidden state
   - Regularizacao temporal
   - Melhor generalizacao
```

### 17.2 Peephole LSTM

```text
Peephole LSTM:

Modificacao: gates tem acesso ao cell state

Forget gate: f_t = sigmoid(W_f * [h, x] + W_pf * c_{t-1})
Input gate:  i_t = sigmoid(W_i * [h, x] + W_pi * c_{t-1})
Output gate: o_t = sigmoid(W_o * [h, x] + W_po * c_t)

Vantagens:
  - Gates sabem o que ha no cell state
  - Decisoes mais informadas
  - Melhor para tarefas que requerem timing preciso

Desvantagens:
  - Mais parametros (3 matrizes de peephole)
  - Mais lento
  - Nem sempre melhoria significativa

Quando usar:
  - Tarefas com padroes temporais precisos
  - Reconhecimento de fala
  - Deteccao de eventos
```

---

## 18. Casos de Uso Avancados

### 18.1 Machine Translation

```text
Traducao Automatica com LSTM:

Arquitetura Seq2Seq:
  Encoder: LSTM que comprime frase de entrada
  Decoder: LSTM que gera frase de saida

Exemplo:
  Entrada: "The cat sat on the mat"
  Encoder: h_enc = LSTM([The, cat, sat, on, the, mat])
  Decoder:
    h_0 = h_enc
    <SOS> -> LSTM -> "O"
    "O" -> LSTM -> "gato"
    "gato" -> LSTM -> "sentou"
    "sentou" -> LSTM -> "no"
    "no" -> LSTM -> "tapete"
    "tapete" -> LSTM -> <EOS>

Treinamento:
  - Teacher forcing: usar saida real como proxima entrada
  - Scheduled sampling: mistura real/predito
  - BLEU score: metrica de avaliacao
```

### 18.2 Image Captioning

```text
Captioning de Imagens com LSTM:

Pipeline:
  1. CNN extrai features da imagem (VGG, ResNet)
  2. Features passam por uma camada densa
  3. Dense output = h_0 da LSTM
  4. LSTM gera caption palavra por palavra

Arquitetura:
  Image -> CNN -> Dense(4096) -> Dense(256) -> h_0
  <SOS> -> LSTM(h_0) -> "A"
  "A" -> LSTM -> "cat"
  "cat" -> LSTM -> "sitting"
  "sitting" -> LSTM -> "on"
  "on" -> LSTM -> "a"
  "a" -> LSTM -> "mat"
  "mat" -> LSTM -> <EOS>

Treinamento:
  - Pares (imagem, caption)
  - Loss: cross-entropy em cada palavra
  - Metricas: BLEU, METEOR, CIDEr
```

### 18.3 Music Generation

```text
Geracao de Musica com LSTM:

Representacao:
  - MIDI events (note_on, note_off, velocity, time)
  - Pianoroll (matriz tempo x nota)
  - Symbolic (ABC notation)

Arquitetura:
  - Char-level: cada evento como caractere
  - Embedding: eventos -> vetores
  - LSTM: processa sequencia
  - Dense: saida = proximo evento

Treinamento:
  - Dataset: MIDI files
  - Sequencias de 200-500 eventos
  - Loss: cross-entropy

Geracao:
  - Seed: few notes iniciais
  - Sampling com temperature
  - T < 1: mais conservador
  - T > 1: mais criativo
  - Top-k sampling: so considerar k tokens mais provaveis
```

---

## 19. Otimizacao e Regularizacao

### 19.1 Tecnicas de Regularizacao

```text
Regularizacao para LSTM:

1. Dropout:
   - Entre camadas (input dropout)
   - No hidden state (recurrent dropout)
   - Na saida (output dropout)
   - Taxa tipica: 0.2-0.5

2. Weight Decay (L2):
   - Adicionar penalidade ||W||^2 a loss
   - Fornece pesos menores
   - lambda tipico: 1e-5 a 1e-3

3. Gradient Clipping:
   - Limitar norma do gradiente
   - max_norm tipico: 1.0-10.0
   - Previne exploding gradient

4. Early Stopping:
   - Parar quando validacao para de melhorar
   - Patience: 5-20 epochs
   - Salvar melhor modelo

5. Batch Normalization:
   - Normalizar entradas de cada camada
   - Mais dificil em sequencias
   - Layer Normalization e mais comum
```

### 19.2 Learning Rate Scheduling

```text
Agendamento de Learning Rate para LSTM:

1. Step Decay:
   - LR = LR_0 * gamma^(epoch / step_size)
   - Exemplo: LR=0.01, gamma=0.1, step=30
   - A cada 30 epochs, reduz por 10x

2. Cosine Annealing:
   - LR = LR_min + 0.5*(LR_max - LR_min)*(1 + cos(pi*epoch/max_epochs))
   - Suave e previsivel
   - Bom para convergencia

3. Warmup + Decay:
   - Warmup: LR cresce de 0 a LR_max em N steps
   - Decay: LR diminui apos warmup
   - Estavel para LSTM

4. Reduce on Plateau:
   - Se val_loss nao melhora por K epochs
   - LR = LR * factor (ex: 0.5)
   - Adaptativo e robusto
```

---

## 20. Debugging e Diagnostico

### 20.1 Problemas Comuns

```text
Problema 1: Loss nao diminui
  Causas:
  - Learning rate incorreto
  - Bias do forget gate mal inicializado
  - Erro no backward pass
  
  Diagnostico:
  - Verificar b_f = 1.0
  - Testar com dados pequenos
  - Gradient checking numerico

Problema 2: Loss explode (NaN)
  Causas:
  - Exploding gradient
  - LR muito alto
  - log(0) em cross-entropy
  
  Diagnostico:
  - Adicionar epsilon em log
  - Reduzir LR
  - Aumentar gradient clipping

Problema 3: Cell state cresce indefinidamente
  Causas:
  - Forget gate nao esta esquecendo
  - Valores acumulam sem limite
  
  Diagnostico:
  - Monitorar ||c_t||
  - Verificar se f_t ~= 1 sempre
  - Usar gradient clipping
```

### 20.2 Ferramentas de Diagnostico

```text
Ferramentas:

1. Monitorar Cell State:
   - ||c_t|| ao longo do tempo
   - Se cresce: problema com forget gate
   - Se encolhe: problema com input gate

2. Monitorar Gates:
   - Media de f_t, i_t, o_t
   - f_t ~= 0.5: nao esta esquecendo/selecionando
   - i_t ~= 0.5: nao esta armazenando
   - o_t ~= 0.5: nao esta expondo

3. Gradient Checking:
   - Calcular gradiente numerico
   - Comparar com analitico
   - Diferenca < 1e-6

4. Unit Tests:
   - Overfit em dados pequenos
   - Verificar dimensoes
   - Verificar valores em range
```

---

## 21. Referencias Adicionais

### 21.1 Historia da LSTM

```text
Linha do Tempo da LSTM:

1997: Hochreiter & Schmidhuber
  - LSTM original proposta
  - Resolve vanishing gradient

2000: Gers & Schmidhuber
  - Peephole connections
  - Forget gate adicionada

2005: Graves
  - LSTM com BPTT
  - Primeira implementacao pratica

2013: Zaremba
  - LSTM regularization (dropout)
  - State of the art em several tasks

2014: Sutskever
  - Seq2Seq com LSTM
  - Machine translation

2015: Vinyals
  - LSTM para image captioning

2017: Vaswani
  - Transformer proposto
  - Attention is All You Need
  - LSTM comeca a ser substituida

2020+: Transformers dominam
  - LSTM usada em nichos
  - Ainda relevante para edge devices
```

---

## 22. Resumo Completo

```text
Resumo Final do Capitulo:

1. LSTM resolve vanishing gradient com CELL STATE dedicado
   - Cell state = auto-estrada para gradientes
   - Forget gate controla esquecimento

2. Tres portoes controlam fluxo:
   - Forget: o que esquecer
   - Input: o que lembrar
   - Output: o que expor

3. Cell state permite memorias de longo prazo:
   - Informacao persiste por tempo indefinido
   - Atualizacao aditiva, nao substitutiva

4. LSTM vs GRU:
   - LSTM: mais flexivel, melhor para seq. longas
   - GRU: mais simples, mais rapido

5. Aplicacoes:
   - Machine translation
   - Image captioning
   - Music generation
   - Time series forecasting

6. Regularizacao:
   - Dropout (recurrent e input)
   - Gradient clipping
   - Early stopping
   - Weight decay
```

---

## Exercicios

### Exercicio 1: Analise de Cell State
Para a frase "O gato que estava sentado no tapete vermelho da sala de estar e que sempre mia quando eu chego em casa esta dormindo agora", trace como o cell state evolui. Quais informacoes sao preservadas? Quais sao esquecidas?

### Exercicio 2: Implementacao Manual
Implemente o forward pass de uma LSTM a mao com:
- Input: [0.5, -0.3]
- Hidden size: 4
- Mostre o valor de f_t, i_t, c~_t, c_t, o_t, h_t

### Exercicio 3: Gradiente do Forget Gate
Calcule o gradiente da loss em relacao ao bias do forget gate (b_f) para a LSTM do Exercicio 2. Mostre por que b_f = 1.0 e uma boa inicializacao.

### Exercicio 4: LSTM vs GRU
Implemente e treine ambos na mesma tarefa:
a) Previsao de serie temporal (seq_len = 100)
b) Meça loss final, tempo de treinamento, numero de parametros
c) Qual e melhor? Por que?

### Exercicio 5: Stack de LSTMs
Treine stacks com 1, 2, 3, e 4 camadas LSTM:
a) Qual produz melhor resultado?
b) Qual e mais estavel?
c) A partir de quantas camadas comeca a degradar?

### Exercicio 6: Bidirectional LSTM
Implemente um classificador de sentimento com BiLSTM:
a) Compare com unidirecional LSTM
b) Em quais frases a direcao reversa ajuda?
c) Calcule o overhead computacional

### Exercicio 7: Analise de Cell State

Para a LSTM treinada, analise o cell state:
a) Qual e a norma media do cell state por passo?
b) Como o cell state evolui ao longo da sequencia?
c) Quais dimensoes do cell state sao mais ativas?
d) O que isso revela sobre a memoria aprendida?

### Exercicio 8: Impacto do Forget Gate Bias

Experimente com diferentes valores de b_f:
a) b_f = 0 (inicializacao padrao)
b) b_f = 1 (inicializacao recomendada)
c) b_f = 2 (esquecimento fraco)
d) Qual produz melhor convergencia? Por que?

### Exercicio 9: LSTM vs GRU vs RNN

Implemente e treine todos na mesma tarefa:
a) Meça tempo de treinamento por epoca
b) Meça numero total de parametros
c) Compare a convergencia (loss vs epocas)
d) Qual converge mais rapido? Qual atinge loss menor?

### Exercicio 10: Stack de LSTMs

Treine stacks com 1, 2, 3, e 4 camadas LSTM:
a) Qual produz melhor resultado?
b) Qual e mais estavel?
c) A partir de quantas camadas comeca a degradar?
d) Qual o numero otimo de camadas para esta tarefa?

---

## Referencias Adicionais

### Artigos Fundamentais

1. Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.

2. Gers, F. A., Schmidhuber, J., & Cummins, F. (2000). Learning to forget: Continual prediction with LSTM. *Neural Computation*, 12(10), 2451-2471.

3. Graves, A. (2013). Generating sequences with recurrent neural networks. *arXiv preprint arXiv:1308.0850*.

4. Zaremba, W., Sutskever, I., & Vinyals, O. (2014). Recurrent neural network regularization. *arXiv preprint arXiv:1409.2329*.

5. Greff, K., et al. (2017). LSTM: A search space odyssey. *IEEE Transactions on Neural Networks and Learning Systems*, 28(10), 2222-2232.

6. Cho, K., et al. (2014). Learning phrase representations using RNN encoder-decoder for statistical machine translation. *arXiv preprint arXiv:1406.1078*.

7. Sutskever, I., Vinyals, O., & Le, Q. V. (2014). Sequence to sequence learning with neural networks. *NIPS 2014*.

8. Schuster, M., & Paliwal, K. K. (1997). Bidirectional recurrent neural networks. *IEEE Transactions on Signal Processing*, 45(11), 2673-2681.

9. Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training recurrent neural networks. *ICML 2013*.

10. Goodfellow, I., Bengio, Y., & Courville, A. (2016). *Deep Learning*. MIT Press. Chapter 10: Sequence Modeling: Recurrent and Recursive Nets.

### Livros e Tutoriais

1. "Deep Learning" - Goodfellow, Bengio, Courville (Cap. 10)
2. "Neural Network Methods for NLP" - Goldberg
3. colah's blog: "Understanding LSTM Networks"
4. Michael Phi: "Illustrated Guide to LSTM"
5. Stanford CS224n: NLP with Deep Learning

### Glossario

```text
Glossario de Termos LSTM:

Cell State (Estado da Celula):
  - Memoria de longo prazo da LSTM
  - Atualizado por forget e input gates
  - Permite memorias por tempo indefinido

Forget Gate (Portao de Esquecimento):
  - Decide que informacao descartar do cell state
  - f_t = sigmoid(W_f * [h, x] + b_f)
  - b_f = 1.0 recomendado

Input Gate (Portao de Entrada):
  - Decide que informacao nova armazenar
  - i_t = sigmoid(W_i * [h, x] + b_i)
  - Trabalha com o candidato

Output Gate (Portao de Saida):
  - Decide que informacao expor no hidden state
  - o_t = sigmoid(W_o * [h, x] + b_o)
  - Filtra cell state

Memory Cell (Celula de Memoria):
  - Unidade individual de armazenamento
  - Cada dimensao do cell state e uma cell
  - Pode armazenar 1 aspecto da informacao

Hidden State (Estado Oculto):
  - Saida filtrada da LSTM
  - h_t = o_t * tanh(c_t)
  - Usado para decisoes e proximo passo

BPTT (Backpropagation Through Time):
  - Algoritmo de treinamento
  - Backpropagation aplicado a LSTM unrolled

Vanishing Gradient (Gradiente Desaparecendo):
  - Gradiente que diminui exponencialmente
  - LSTM resolve com cell state

Teacher Forcing:
  - Treinamento com saida real
  - Pode causar exposure bias

Scheduled Sampling:
  - Mistura teacher forcing e auto-regressivo
  - Resolve exposure bias
```

---

## Calculo de Complexidade

### Complexidade Computacional

```text
Complexidade da LSTM por Passo Temporal:

Forward Pass:
  - Concatenacao: O(d_h + d_x)
  - Forget gate: O(d_h * (d_h + d_x))
  - Input gate: O(d_h * (d_h + d_x))
  - Candidate: O(d_h * (d_h + d_x))
  - Cell state: O(d_h)
  - Output gate: O(d_h * (d_h + d_x))
  - Hidden state: O(d_h)
  - Total: O(4 * d_h * (d_h + d_x))

Backward Pass:
  - ~4x forward (por causa dos 4 componentes)
  - Total: O(16 * d_h * (d_h + d_x))

Memoria por Passo:
  - Cache: O(7 * d_h) (h, c, f, i, cand, o, logits)
  - Gradientes: O(4 * d_h * (d_h + d_x))

Para sequencia de comprimento T:
  - Forward total: O(T * 4 * d_h * (d_h + d_x))
  - Backward total: O(T * 16 * d_h * (d_h + d_x))
  - Memoria: O(T * 7 * d_h)
```

### Comparacao com Outros Modelos

```text
Complexidade Comparativa:

RNN Basica:
  Forward: O(d_h * (d_h + d_x))
  Backward: O(2 * d_h * (d_h + d_x))
  Memoria: O(3 * d_h * T)

GRU:
  Forward: O(3 * d_h * (d_h + d_x))
  Backward: O(6 * d_h * (d_h + d_x))
  Memoria: O(5 * d_h * T)

LSTM:
  Forward: O(4 * d_h * (d_h + d_x))
  Backward: O(16 * d_h * (d_h + d_x))
  Memoria: O(7 * d_h * T)

Transformer:
  Forward: O(T^2 * d_model)
  Backward: O(T^2 * d_model)
  Memoria: O(T^2 + d_model)

Para T < d_model:
  RNN/GRU/LSTM sao mais eficientes

Para T > d_model:
  Transformer e mais eficiente (paralelizavel)
```

---

## Aplicacoes Detalhadas

### Reconhecimento de Fala

```text
Reconhecimento de Fala com LSTM:

Pipeline:
  1. Audio -> Features (MFCC, 13-40 coefficients)
  2. Features -> LSTM (multiplas camadas)
  3. LSTM -> CTC decode -> Texto

Arquitetura tipica:
  - 3-5 camadas LSTM empilhadas
  - Hidden size: 256-512 por camada
  - Bidirecional em todas as camadas
  - CTC loss no topo

Desafios:
  - Variacao de说话人
  - Ruido ambiente
  - Acentos e dialectos
  - Velocidade de fala variavel

Resultados:
  - WER (Word Error Rate): 5-10% em datasets limpos
  - Tempo real: ~100ms por segundo de audio
```

### Deteccao de Anomalias

```text
Deteccao de Anomalias com LSTM:

Metodo 1: Reconstruction Error
  - Treinar LSTM em dados normais
  - Medir erro de reconstrucao
  - Se erro > threshold: anomalia

Metodo 2: Prediction Error
  - Treinar LSTM para prever proximo passo
  - Se erro de previsao > threshold: anomalia

Metodo 3: LSTM Autoencoder
  - Encoder: LSTM comprime sequencia
  - Decoder: LSTM reconstrui sequencia
  - Anomalia = alta perda de reconstrucao

Aplicacoes:
  - Fraude em transacoes
  - Deteccao de intrusao em redes
  - Monitoramento de maquinas
  - Deteccao de doenças em ECG
```

### Sistemas de Recomendacao

```text
Sistemas de Recomendacao com LSTM:

Ideia: modelar sequencia de interacoes do usuario

Arquitetura:
  - Input: sequencia de items clicados/comprados
  - LSTM: modela preferencias temporais
  - Output: proximo item provavel

Vantagens:
  - Captura preferencias que mudam ao longo do tempo
  - Lida com sessoes de comprimento variavel
  - Pode aprender padroes saisonais

Exemplo:
  Usuario comprou: [notebook, mouse, teclado, monitor]
  LSTM prediz: [cadeira] (proximo item provavel)
```

---

## Comparativa Final: LSTM vs GRU vs RNN

### Resumo das Diferencas

```text
Tabela Comparativa Final:

| Caracteristica      | RNN       | GRU       | LSTM      |
|---------------------|-----------|-----------|-----------|
| Portoes             | 0         | 2         | 3         |
| Cell State          | Nao       | Nao       | Sim       |
| Memoria Longo Prazo | Fraca     | Boa       | Excelente |
| Parametros (d=256)  | 163K      | 245K      | 327K      |
| Velocidade          | Rapida    | Media     | Lenta     |
| Vanishing Gradient  | Sim       | Nao       | Nao       |
| Complexidade        | Baixa     | Media     | Alta      |
| Caso de Uso Ideal   | Seq Curtas| Seq Medias| Seq Longas|

Regras Practice:
1. Comece com GRU (mais rapido de iterar)
2. Se GRU nao atingir performance, tente LSTM
3. Se LSTM tambem nao, considere Transformer
4. Para producao, meça overhead real
```

### Fluxo de Decisao

```text
Fluxo de Decisao: Qual Arquitetura Usar?

1. Qual o comprimento da sequencia?
   - < 50 passos: RNN basica pode ser suficiente
   - 50-200 passos: GRU e otimo
   - > 200 passos: LSTM ou Transformer

2. Quanto dados voce tem?
   - Poucos dados: GRU (menos parametros)
   - Muitos dados: LSTM (mais capacidade)

3. Velocidade e critica?
   - Sim: GRU
   - Nao: LSTM

4. Memoria de longo prazo e critica?
   - Sim: LSTM
   - Nao: GRU

5. Ja tem implementacao de alguma?
   - Use a que ja tem e funcione
   - Nao re-implemente desnecessariamente
```

---

## Referencias

1. Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.

2. Gers, F. A., Schmidhuber, J., & Cummins, F. (2000). Learning to forget: Continual prediction with LSTM. *Neural Computation*, 12(10), 2451-2471.

3. Graves, A. (2013). Generating sequences with recurrent neural networks. *arXiv preprint arXiv:1308.0850*.

4. Zaremba, W., Sutskever, I., & Vinyals, O. (2014). Recurrent neural network regularization. *arXiv preprint arXiv:1409.2329*.

5. Greff, K., et al. (2017). LSTM: A search space odyssey. *IEEE Transactions on Neural Networks and Learning Systems*, 28(10), 2222-2232.

6. Cho, K., et al. (2014). Learning phrase representations using RNN encoder-decoder for statistical machine translation. *arXiv preprint arXiv:1406.1078*.

7. Sutskever, I., Vinyals, O., & Le, Q. V. (2014). Sequence to sequence learning with neural networks. *NIPS 2014*.

8. Schuster, M., & Paliwal, K. K. (1997). Bidirectional recurrent neural networks. *IEEE Transactions on Signal Processing*, 45(11), 2673-2681.

9. Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training recurrent neural networks. *ICML 2013*.

10. Goodfellow, I., Bengio, Y., & Courville, A. (2016). *Deep Learning*. MIT Press. Chapter 10: Sequence Modeling: Recurrent and Recursive Nets.
