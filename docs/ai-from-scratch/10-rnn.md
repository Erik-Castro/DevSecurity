---
layout: default
title: "10-rnn"
---

# Capitulo 10 — Redes Neurais Recorrentes (RNN)

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender por que sequencias importam** — dados sequenciais (texto, audio, series temporais) possuem dependencias temporais que redes feed-forward nao capturam.
2. **Dominar a arquitetura basica de uma RNN** — entrada, hidden state, saida, e como o compartilhamento de pesos ao longo do tempo permite processar sequencias de comprimento variavel.
3. **Entender o hidden state** como memoria de curto prazo e sua representacao matematica.
4. **Realizar o unrolling no tempo** para visualizar a RNN como uma rede feed-forward compartilhada e compreender as implicacoes para treinamento.
5. **Implementar Backpropagation Through Time (BPTT)** — o algoritmo fundamental para treinar RNNs, incluindo o truncamento para sequencias longas.
6. **Identificar e mitigar o problema de vanishing gradient** — por que gradientes desaparecem em sequencias longas e como arquiteturas como LSTM e GRU resolvem isso.
7. **Analisar o problema de exploding gradient** — deteccao via norma do gradiente e solucoes como gradient clipping.
8. **Implementar Bidirectional RNN** para capturar contexto passado e futuro simultaneamente.
9. **Projetar arquiteturas sequence-to-sequence** para tarefas como traducao automatica e sumarizacao.
10. **Implementar uma RNN completa em C++, Fortran e Rust** — forward pass, backward pass, e treinamento do zero, sem bibliotecas.

---

## 1. Por Que Sequencias Importam

### 1.1 O Mundo e Sequencial

A vasta maioria dos dados que encontramos na natureza e na tecnologia e sequencial. Um frase em portugues tem palavras que dependem das anteriores. Uma serie temporal de precos de acoes tem padroes que dependem de centenas de observacoes passadas. Um sinal de audio e uma sequencia de amostras onde cada uma depende das adjacentes.

```text
Exemplos de dados sequenciais:

Texto:       "O gato sentou no" -> proxima palavra: "tapete"
Audio:       [0.02, -0.01, 0.03, ...] -> proxima amostra: 0.018
Series:      [100.5, 101.2, 99.8, ...] -> proximo preco: 102.1
Musica:      [C4, E4, G4, C5] -> proxima nota: E5
Video:       [frame_1, frame_2, frame_3] -> proximo frame: frame_4
DNA:         [A, T, G, C, A, T] -> proximo nucleotideo: G
```

Redes feed-forward tradicionais (MLPs) processam cada entrada de forma independente. Elas nao possuem conceito de "ordem" ou "dependencia temporal". Se voce alimenta uma MLP com palavras de uma frase, ela ve cada palavra isoladamente — nao sabe que "gato" veio antes de "sentou".

### 1.2 O Problema das Redes Feed-Forward para Sequencias

Considere a tarefa de prever a proxima palavra em uma frase. Para uma frase com 10 palavras, cada representada por um vetor de 100 dimensoes:

```text
Entrada: 10 palavras * 100 dimensoes = 1000 entradas
Se a rede oculta tem 500 neuronios:
  Parametros na primeira camada: 1000 * 500 = 500.000

Se a frase tem 20 palavras:
  Parametros: 2000 * 500 = 1.000.000

Se a frase tem 100 palavras:
  Parametros: 10000 * 500 = 5.000.000
```

Os problemas sao claros:

```text
Problema 1: Tamanho fixo de entrada
- A rede precisa de um numero FIXO de entradas
- Frases tem comprimentos variaveis
- Solucao comum: pad ou truncar (ambas perdem informacao)

Problema 2: Sem compartilhamento temporal
- A palavra "gato" na posicao 1 e tratada diferente da palavra "gato" na posicao 5
- Cada posicao tem seus proprios pesos
- A rede nao aprende que o significado de "gato" e o mesmo independente da posicao

Problema 3: Parametros explodem
- Para sequencias longas, o numero de parametros cresce linearmente
- Sequencia de 1000 passos com 1000 neuronios = 1.000.000.000 de parametros
- Isso e inviavel computacionalmente

Problema 4: Sem memoria
- A rede nao lembra o que processou antes
- Cada entrada e processada de forma isolada
- Contexto temporal e completamente perdido
```

### 1.3 A Solucao: Recorrencia

A ideia central das RNNs e elegante em sua simplicidade: em vez de processar a sequencia inteira de uma vez, processamos um elemento por vez, e mantemos um **estado oculto** (hidden state) que resume tudo que vimos ate agora.

```text
Conceito Central:
Em vez de:
  [x1, x2, x3, ..., xn] -> Rede -> [y1, y2, y3, ..., yn]

Fazemos:
  x1 -> Rede -> h1 -> y1
  x2 + h1 -> Rede -> h2 -> y2
  x3 + h2 -> Rede -> h3 -> y3
  ...
  xn + h(n-1) -> Rede -> hn -> yn
```

Cada passo usa os MESMOS pesos (compartilhamento temporal), e o hidden state `h` carrega informacao de todos os passos anteriores (memoria).

### 1.4 Vantagens das RNNs

```text
Vantagem 1: Comprimento variavel
- A rede processa sequencias de qualquer tamanho
- Nao precisa pad/truncar
- Mesma arquitetura para frases de 5 ou 500 palavras

Vantagem 2: Compartilhamento temporal
- Os mesmos pesos sao usados em cada passo
- A rede aprende padroes que se repetem ao longo do tempo
- "Gato" na posicao 1 usa os mesmos pesos que "gato" na posicao 50

Vantagem 3: Memoria
- O hidden state resume o contexto da sequencia
- Informacao de passos anteriores influencia decisoes atuais
- A rede pode aprender dependencias de curto e medio prazo

Vantagem 4: Eficiencia parametrica
- Numero de parametros e INDEPENDENTE do comprimento da sequencia
- Mesma rede para 10 ou 10.000 passos
- Muito mais eficiente que redes feed-forward para sequencias
```

---

## 2. Arquitetura Basica RNN

### 2.1 Componentes Fundamentais

Uma RNN basica possui tres componentes principais:

```text
Componentes de uma RNN:

1. Entrada (x_t):
   - Vetor que representa o elemento atual da sequencia
   - Dimensao: d_x (ex: 100 para word embeddings)

2. Estado Oculto (h_t):
   - Vetor que resume toda a historia da sequencia ate o momento t
   - Dimensao: d_h (ex: 256 para memoria de curto prazo)
   - Atualizado a cada passo de tempo

3. Saida (y_t):
   - Vetor que representa a previsao da rede no passo t
   - Dimensao: d_y (ex: vocabulario para previsao de proxima palavra)
   - Pode ser opcional em alguns formatos
```

### 2.2 Parametros da RNN

Uma RNN basica possui tres matrizes de peso e tres vetores de bias:

```text
Parametros (total: 3*d_h*(d_x + d_h + 1)):

W_xh: Matriz de pesos entrada -> oculta
  - Dimensao: d_h x d_x
  - Conecta a entrada ao hidden state

W_hh: Matriz de pesos oculta -> oculta
  - Dimensao: d_h x d_h
  - Conecta o hidden state anterior ao atual
  - ESTA e a "recorrencia" — a conexao temporal

W_hy: Matriz de pesos oculta -> saida
  - Dimensao: d_y x d_h
  - Conecta o hidden state a saida

b_h: Bias do hidden state
  - Dimensao: d_h

b_y: Bias da saida
  - Dimensao: d_y
```

### 2.3 Equacao de Atualizacao

A equacao fundamental da RNN e:

```text
Equacao de Atualizacao do Hidden State:

h_t = activation(W_xh * x_t + W_hh * h_{t-1} + b_h)

Onde:
- h_t: hidden state no tempo t
- x_t: entrada no tempo t
- h_{t-1}: hidden state no tempo anterior
- W_xh, W_hh: matrizes de peso
- b_h: bias
- activation: tipicamente tanh (hiperbolico tangente)
```

E a equacao de saida:

```text
Equacao de Saida:

y_t = softmax(W_hy * h_t + b_y)

Onde:
- y_t: saida (distribuicao de probabilidade)
- W_hy: matriz de peso saida
- b_y: bias da saida
```

### 2.4 Por Que Tanh e Nao ReLU?

A funcao de ativacao escolhida para o hidden state e critica:

```text
Tanh vs ReLU no Hidden State:

Tanh:
- Saida no intervalo [-1, 1]
- Centro em zero (boa para gradientes)
- Derivada: 1 - tanh^2(x), no intervalo [0, 1]
- Gradientes sao ESTAVEIS em valores proximos a zero

ReLU:
- Saida no intervalo [0, +inf)
- Derivada: 0 ou 1 (sem suavidade)
- Pode causar "dying ReLU" — neuronios que nunca ativam
- Para RNNs, causa problems com exploding gradient

Por que importa:
- No hidden state, o valor de h_t depende de h_{t-1}
- Se usarmos ReLU, o valor pode crescer indefinidamente
- Tanh mantem os valores controlados entre -1 e 1
- Isso e FUNDAMENTAL para estabilidade numerica
```

### 2.5 Exemplo Visual

```text
Exemplo: Processando a frase "EU AMO PROGRAMACAO"

Passo 1: x_1 = embedding("EU")
  h_0 = [0, 0, ..., 0]  (vetor zeros)
  h_1 = tanh(W_xh * x_1 + W_hh * h_0 + b_h)
  y_1 = softmax(W_hy * h_1 + b_y)  (previsao: "AMO")

Passo 2: x_2 = embedding("AMO")
  h_1 = [0.12, -0.45, 0.78, ...]  (da etapa anterior)
  h_2 = tanh(W_xh * x_2 + W_hh * h_1 + b_h)
  y_2 = softmax(W_hy * h_2 + b_y)  (previsao: "PROGRAMACAO")

Passo 3: x_3 = embedding("PROGRAMACAO")
  h_2 = [0.34, -0.12, 0.56, ...]  (ja contem info de "EU" e "AMO")
  h_3 = tanh(W_xh * x_3 + W_hh * h_2 + b_h)
  y_3 = softmax(W_hy * h_3 + b_y)  (previsao: "<FIM>")
```

---

## 3. Hidden State

### 3.1 Conceito de Memoria

O hidden state e a espirito de uma RNN. Ele e o vetor que carrega informacao de todos os passos anteriores e fornece contexto para o passo atual.

```text
Anatomia do Hidden State:

h_t = tanh(W_xh * x_t + W_hh * h_{t-1} + b_h)

Componentes:
1. W_xh * x_t: contribuicao da ENTRADA ATUAL
   - O que o modelo ve agora

2. W_hh * h_{t-1}: contribuicao da MEMORIA
   - O que o modelo lembra do passado

3. b_h: bias
   - Viés aprendido

A saida e a combinacao dessas tres informacoes,
comprimida pelo tanh para o intervalo [-1, 1].
```

### 3.2 O Hidden State como Compressao

O hidden state e essencialmente uma compressao lossy de toda a sequencia anterior:

```text
Analogia: Leitor Veloz

Imagine que voce esta lendo um livro e, a cada pagina,
anota em um post-it apenas as IDEIAS PRINCIPAIS.

Pagina 1: "Historia sobre um detetive"
Pagina 2: "Detetive investiga assassinato"
Pagina 3: "Suspeita do mordomo"

Seu post-it (hidden state) nao contem o LIVRO INTEIRO,
mas contem informacao SUFICIENTE para entender o contexto.

O hidden state da RNN faz exatamente isso:
- Comprime toda a sequencia ate agora em um vetor de tamanho fixo
- Mantem as informacoes MAIS RELEVANTES
- Descarta detalhes menos importantes
```

### 3.3 Dimensoes do Hidden State

A escolha da dimensao do hidden state e uma decisao de projeto critica:

```text
Dimensao do Hidden State:

Muito pequena (ex: 16):
+ Poucos parametros, rapida de treinar
+ Menos overfitting
- Nao consegue armazenar informacao suficiente
- Perde contexto em sequencias longas
- Baixa capacidade de representacao

Muito grande (ex: 4096):
+ Alta capacidade de representacao
+ Pode armazenar muito contexto
- Muitos parametros (d_h^2 para W_hh)
- Lenta de treinar e inferir
- Mais propensa a overfitting
- Problemas com vanishing/exploding gradient

Valores tipicos:
- Pesquisa: 128, 256, 512
- Producao: 256, 512, 1024
- Grandes modelos: 2048, 4096
```

### 3.4 Inicializacao do Hidden State

O hidden state inicial `h_0` tem importancia frequentemente subestimada:

```text
Opcoes de inicializacao:

1. Vetor de zeros (mais comum):
   h_0 = [0, 0, ..., 0]
   - Simples e funciona bem na maioria dos casos
   - A rede aprende a "esquecer" o zero inicial

2. Vetor aprendido:
   h_0 = param (treinavel)
   - A rede aprende o melhor estado inicial
   - Mais flexivel, mais parametros
   - Util quando a sequencia tem um "estado padrao"

3. Vetor aleatorio:
   h_0 = random_normal(0, 0.01)
   - Quebra simetria
   - Pode causar instabilidade no treinamento
   - Raramente usado na pratica
```

### 3.5 O Hidden State e a Memoria de Curto Prazo

```text
Limitacao Fundamental:
O hidden state e um vetor de tamanho FIXO.
Para sequencias muito longas, ele nao consegue
armazenar informacao de todos os passos.

Exemplo:
- Hidden state de 256 dimensoes
- Sequencia de 1000 palavras
- Cada palavra tem embedding de 300 dimensoes
- Total de informacao: 1000 * 300 = 300.000 dimensoes
- Compressao: 300.000 -> 256 (compressao de 1171x!)

Informacao e PERDIDA inevitavelmente.
A questao e: QUE informacao e preservada?
- Informacoes RECENTES sao preservadas melhor
- Informacoes ANTIGAS sao gradualmente esquecidas
- Isso e o "vanishing gradient" em acao
```

---

## 4. Unrolling no Tempo

### 4.1 O Que e Unrolling

Unrolling (desenrolamento) e a operacao de expandir a RNN ao longo do tempo, revelando sua estrutura real como uma rede feed-forward compartilhada.

```text
RNN Compacta (como escrevemos):

    +---+
    |   |
    v   |
x_t ->[RNN]-> h_t -> y_t

RNN Unrolled (como ela realmente funciona):

x_1 ->[RNN] -> h_1 -> y_1
         |
x_2 ->[RNN] -> h_2 -> y_2
         |
x_3 ->[RNN] -> h_3 -> y_3
         |
x_4 ->[RNN] -> h_4 -> y_4

Cada "[RNN]" usa os MESMOS pesos.
As conexoes horizontais sao W_hh.
As conexoes verticais sao W_xh.
```

### 4.2 Unrolling Revela a Verdadeira Arquitetura

O unrolling mostra que uma RNN de sequencia de comprimento T e equivalente a uma rede feed-forward com T copias compartilhadas dos mesmos pesos:

```text
Equivalencia:

RNN com T passos = Rede feed-forward com T camadas
Cada camada tem os mesmos pesos (W_xh, W_hh, W_hy)

Isso significa:
1. Backpropagation normal PODE ser aplicada
2. Mas os gradientes precisam ser ACUMULADOS ao longo do tempo
3. Isso e o BPTT (Backpropagation Through Time)
```

### 4.3 Parametros Compartilhados

```text
Demonstracao de Compartilhamento:

Sem compartilhamento (MLP para sequencias):
  Camada 1: W1 (d_h x d_x)  + b1
  Camada 2: W2 (d_h x d_x)  + b2
  Camada 3: W3 (d_h x d_x)  + b3
  ...
  Camada T: WT (d_h x d_x) + bT
  Total: T * d_h * (d_x + 1) parametros

Com compartilhamento (RNN):
  Todos os passos: W_xh (d_h x d_x) + W_hh (d_h x d_h) + b_h
  Total: d_h * (d_x + d_h + 1) parametros

Exemplo numerico (T=100, d_x=100, d_h=256):
  MLP: 100 * 256 * 101 = 2.585.600
  RNN: 256 * (100 + 256 + 1) = 91.392
  Reducao: 28x
```

### 4.4 Formatos de Unrolling

Existem diferentes formatos dependendo de como usamos as saidas:

```text
Formato 1: Many-to-Many
- Saida em cada passo de tempo
- Ex: previsao de proxima palavra
x_1 -> RNN -> y_1
x_2 -> RNN -> y_2
x_3 -> RNN -> y_3

Formato 2: Many-to-One
- Saida apenas no ultimo passo
- Ex: classificacao de sentimento
x_1 -> RNN -> (ignorado)
x_2 -> RNN -> (ignorado)
x_3 -> RNN -> y_3 (classificacao)

Formato 3: One-to-Many
- Entrada unica, saidas em sequencia
- Ex: captioning de imagens
x_1 -> RNN -> y_1
      RNN -> y_2
      RNN -> y_3

Formato 4: Encoder-Decoder (Seq2Seq)
- Encoder comprime, decoder gera
- Ex: traducao automatica
x_1 -> [Encoder] -> contexto -> [Decoder] -> y_1
x_2 -> [Encoder]              -> [Decoder] -> y_2
x_3 -> [Encoder]              -> [Decoder] -> y_3
```

---

## 5. Backpropagation Through Time (BPTT)

### 5.1 O Que e BPTT

BPTT e o algoritmo de treinamento de RNNs. E simplesmente backpropagation aplicada a RNN unrolled.

```text
BPTT em uma Frase:

Entrada: "EU AMO PROGRAMACAO"
Saida esperada: "AMO PROGRAMACAO <FIM>"

Forward pass:
  h_1 = tanh(W_xh * x_1 + W_hh * h_0 + b_h)
  y_1 = softmax(W_hy * h_1 + b_y)

  h_2 = tanh(W_xh * x_2 + W_hh * h_1 + b_h)
  y_2 = softmax(W_hy * h_2 + b_y)

  h_3 = tanh(W_xh * x_3 + W_hh * h_2 + b_h)
  y_3 = softmax(W_hy * h_3 + b_y)

Loss: L = CE(y_1, t_1) + CE(y_2, t_2) + CE(y_3, t_3)

Backward pass (BPTT):
  Calcular dL/dW_hy (comum a todas as camadas)

  Para t = 3, 2, 1 (reversed):
    Calcular dh_t (gradiente do hidden state)
    Calcular dW_xh, dW_hh, db_h
    Propagar dh_t para h_{t-1} via W_hh
```

### 5.2 Derivadas do BPTT

As derivadas parciais sao calculadas usando a regra da cadeia:

```text
Derivadas Principais:

1. Gradiente da saida:
   dL/dy_t = y_t - t_t  (para cross-entropy + softmax)

2. Gradiente de W_hy:
   dL/dW_hy = dL/dy_t * h_t^T

3. Gradiente do hidden state:
   dh_t = W_hy^T * (dL/dy_t) + W_hh^T * dh_{t+1}

   Nota: O termo W_hh^T * dh_{t+1} e a propagacao
   do gradiente de volta no tempo.

4. Gradiente da ativacao:
   dtanh_t = dh_t * (1 - h_t^2)  (derivada do tanh)

5. Gradiente de W_xh:
   dL/dW_xh = dtanh_t * x_t^T

6. Gradiente de W_hh:
   dL/dW_hh = dtanh_t * h_{t-1}^T
```

### 5.3 Implementacao do BPTT

```cpp
// BPTT simplificado para uma RNN

struct BPTTResult {
    std::vector<std::vector<double>> dW_xh;
    std::vector<std::vector<double>> dW_hh;
    std::vector<std::vector<double>> dW_hy;
    std::vector<double> db_h;
    std::vector<double> db_y;
};

BPTTResult bptt(
    const std::vector<std::vector<double>>& inputs,  // x_1, x_2, ..., x_T
    const std::vector<std::vector<double>>& targets,  // t_1, t_2, ..., t_T
    const std::vector<std::vector<double>>& hidden_states,  // h_0, h_1, ..., h_T
    const std::vector<std::vector<double>>& outputs,  // y_1, y_2, ..., y_T
    const RNNParams& params,  // W_xh, W_hh, W_hy, b_h, b_y
    int seq_len,
    int input_size,
    int hidden_size,
    int output_size
) {
    BPTTResult grads;
    grads.dW_xh = zero_matrix(hidden_size, input_size);
    grads.dW_hh = zero_matrix(hidden_size, hidden_size);
    grads.dW_hy = zero_matrix(output_size, hidden_size);
    grads.db_h = zero_vector(hidden_size);
    grads.db_y = zero_vector(output_size);

    // Gradiente do proximo passo (inicialmente zero)
    std::vector<double> dh_next(hidden_size, 0.0);

    // Propagar do ultimo passo ao primeiro
    for (int t = seq_len - 1; t >= 0; t--) {
        // Gradiente da funcao de perda em relacao a y_t
        std::vector<double> dy(output_size);
        for (int i = 0; i < output_size; i++) {
            dy[i] = outputs[t][i] - targets[t][i];  // softmax + cross-entropy
        }

        // Gradiente de W_hy
        for (int i = 0; i < output_size; i++) {
            for (int j = 0; j < hidden_size; j++) {
                grads.dW_hy[i][j] += dy[i] * hidden_states[t + 1][j];
            }
            grads.db_y[i] += dy[i];
        }

        // Gradiente do hidden state
        std::vector<double> dh(hidden_size, 0.0);
        for (int j = 0; j < hidden_size; j++) {
            for (int i = 0; i < output_size; i++) {
                dh[j] += params.W_hy[i][j] * dy[i];
            }
            dh[j] += dh_next[j];
        }

        // Gradiente da ativacao tanh
        std::vector<double> dtanh(hidden_size);
        for (int j = 0; j < hidden_size; j++) {
            double h = hidden_states[t + 1][j];
            dtanh[j] = dh[j] * (1.0 - h * h);  // derivada do tanh
        }

        // Gradiente de W_xh
        for (int j = 0; j < hidden_size; j++) {
            for (int i = 0; i < input_size; i++) {
                grads.dW_xh[j][i] += dtanh[j] * inputs[t][i];
            }
            grads.db_h[j] += dtanh[j];
        }

        // Gradiente de W_hh
        for (int j = 0; j < hidden_size; j++) {
            for (int i = 0; i < hidden_size; i++) {
                grads.dW_hh[j][i] += dtanh[j] * hidden_states[t][i];
            }
        }

        // Propagar gradiente para o passo anterior
        dh_next.resize(hidden_size, 0.0);
        for (int i = 0; i < hidden_size; i++) {
            dh_next[i] = 0.0;
            for (int j = 0; j < hidden_size; j++) {
                dh_next[i] += params.W_hh[j][i] * dtanh[j];
            }
        }
    }

    return grads;
}
```

### 5.4 BPTT Truncado

Para sequencias muito longas, o BPTT completo e computacionalmente proibitivo:

```text
BPTT Completo vs Truncado:

BPTT Completo:
- Retropropaga por TODOS os T passos
- Complexidade: O(T * d_h^2)
- Para T = 10.000: extremamente custoso
- Memoria: O(T * d_h) para armazenar todos os h_t

BPTT Truncado (TBPTT):
- Retropropaga por apenas k passos (k << T)
- Complexidade: O(k * d_h^2)
- Memoria: O(k * d_h)
- Tradeoff: perde dependencias de longo prazo

Exemplo:
- Sequencia de 1000 passos
- TBPTT com k = 50
- A cada 50 passos, "reinicia" a propagacao
- Custa 20x menos que BPTT completo
```

---

## 6. Vanishing Gradient Problem

### 6.1 O Problema

O problema de vanishing gradient e a maldicao das RNNs. Ele impede que a rede aprenda dependencias de longo prazo.

```text
O Problema Visual:

Passo 1: Gradiente = 1.0
Passo 2: Gradiente = 0.9
Passo 3: Gradiente = 0.81
...
Passo 10: Gradiente = 0.10
...
Passo 20: Gradiente = 0.01
...
Passo 50: Gradiente = 0.000005

Apos 50 passos, o gradiente e praticamente ZERO.
A rede NAO pode aprender nada sobre o passo 1
quando esta no passo 50.
```

### 6.2 Causa Matematica

A causa e a multiplicacao repetida da matriz de pesos do hidden state:

```text
Analise Matematica:

A atualizacao do hidden state e:
h_t = tanh(W_hh * h_{t-1} + ...)

O gradiente de h_T em relacao a h_1 e:
dh_T/dh_1 = prod(t=2 to T) [W_hh * diag(1 - h_t^2)]

Para cada passo, multiplicamos pela matriz W_hh
e pela derivada do tanh.

Se os autovalores de W_hh sao MENORES que 1:
  O produto encolhe exponencialmente
  O gradiente "desaparece" (vanishes)

Se os autovalores de W_hh sao MAIORES que 1:
  O produto cresce exponencialmente
  O gradiente "explode" (explodes)
```

### 6.3 Implicacoes Praticas

```text
Implicacoes do Vanishing Gradient:

1. Memoria de curto prazo apenas
   - A RNN so lembra de ~10-20 passos atras
   - Nao pode aprender padroes de longo prazo
   - Exemplo: "O gato que estava sentado no tapete vermelho
   que minha mae comprou na loja da esquina ontem
   esta dormindo" -> a RNN esquece "gato" antes de chegar em "dormindo"

2. Gradientes proximos de zero
   - Pesos nao atualizam nas primeiras camadas
   - A rede para de aprender em sequencias longas

3. Assimetria temporal
   - A rede aprende melhor o que aconteceu recentemente
   - Informacoes antigas sao gradualmente perdidas
```

### 6.4 Solucoes

```text
Solucoes para Vanishing Gradient:

1. Arquiteturas especializadas (proximo capitulo):
   - LSTM: usa portoes (gates) para controlar fluxo de informacao
   - GRU: versao simplificada do LSTM
   - Ambos resolvem o problema de vanishing gradient

2. Inicializacao cuidadosa:
   - Orthogonal initialization para W_hh
   - Identity initialization: W_hh = I
   - Mantem autovalores proximos de 1

3. Funcao de ativacao adequada:
   - Tanh e melhor que ReLU para RNNs
   - LSTM usa sigmoid (portoes) e tanh (candidates)

4. Gradient clipping (para exploding):
   - Limita a norma do gradiente
   - Preveni exploding mas nao vanishing

5. Skip connections:
   - Conectar diretamente h_t a h_{t-k}
   - Reduz o numero de multiplicacoes de matriz
```

---

## 7. Exploding Gradient Problem

### 7.1 O Problema

Enquanto vanishing gradient causa gradientes proximos de zero, exploding gradient causa gradientes ENORMES que tornam o treinamento instavel.

```text
O Problema Visual:

Passo 1: Gradiente = 1.0
Passo 2: Gradiente = 1.5
Passo 3: Gradiente = 2.25
...
Passo 10: Gradiente = 57.67
...
Passo 20: Gradiente = 3.325.256

O gradiente cresce exponencialmente.
Os pesos atualizacoes sao MASSIVAS.
O treinamento DIVERGE (loss explode).
```

### 7.2 Causa

```text
Causa do Exploding Gradient:

Se os autovalores de W_hh sao MAIORES que 1:
  O produto prod(W_hh * diag(1 - h_t^2)) cresce

Se h_t esta em uma regiao onde a derivada do tanh
e proxima de 1 (regiao linear):
  O "1 - h_t^2" nao reduz o gradiente
  E W_hh amplifica a cada passo

Resultado: gradiente cresce exponencialmente
```

### 7.3 Deteccao

```text
Como Detectar Exploding Gradient:

1. Monitorar a norma do gradiente:
   norm = sqrt(sum(dL/dW)^2)
   Se norm > 100 ou 1000, ha exploding

2. Monitorar os pesos:
   Se pesos mudam drasticamente apos uma atualizacao
   Se pesos ficam NaN ou Inf

3. Monitorar a loss:
   Se loss pulou de 2.5 para 1.5 em um step
   Ou de 2.5 para 500.0 em um step
   (ambos indicam instabilidade)
```

### 7.4 Solucao: Gradient Clipping

```cpp
// Gradient Clipping por Norma

void clip_gradients(
    std::vector<std::vector<double>>& grads,
    double max_norm
) {
    // Calcular norma L2 do gradiente
    double total_norm = 0.0;
    for (const auto& row : grads) {
        for (double g : row) {
            total_norm += g * g;
        }
    }
    total_norm = std::sqrt(total_norm);

    // Se a norma excede o limite, escalar
    if (total_norm > max_norm) {
        double scale = max_norm / total_norm;
        for (auto& row : grads) {
            for (double& g : row) {
                g *= scale;
            }
        }
    }
}

// Uso:
// clip_gradients(grad_W_xh, 5.0);  // max_norm = 5.0
// clip_gradients(grad_W_hh, 5.0);
// clip_gradients(grad_W_hy, 5.0);
```

### 7.5 Comparacao Vanishing vs Exploding

```text
Vanishing vs Exploding Gradient:

| Aspecto            | Vanishing           | Exploding           |
|--------------------|---------------------|---------------------|
| Gradiente          | Proximo de zero     | Muito grande        |
| Atualizacao pesos  | Minima              | Massiva             |
| Treinamento        | Para de aprender    | Diverge             |
| Loss               | Para de diminuir    | Pulou para NaN/Inf  |
| Causa              | Autovalores < 1     | Autovalores > 1     |
| Solucao principal  | LSTM / GRU          | Gradient clipping   |
| Deteccao           | Difcil (silenciosa) | Facil (loss explode)|
```

---

## 8. Bidirectional RNN

### 8.1 O Problema da RNN Unidirecional

A RNN unidirecional so tem acesso ao passado. Em muitas tarefas, o contexto futuro e igualmente importante.

```text
Exemplo: Classificacao de Sentimento

Frase: "O filme nao foi tao bom quanto eu esperava"

RNN unidirecional (esquerda para direita):
- Em "filme": nao sabe que vem "nao"
- Em "bom": nao sabe que vem "quanto eu esperava"
- Classificacao pode ser ERRADA

Solucao: processar em AMBAS as direcoes
- Da esquerda: contexto passado
- Da direita: contexto futuro
- Combinar ambos para decisao final
```

### 8.2 Arquitetura Bidirecional

```text
Bidirectional RNN:

Forward hidden states:
x_1 ->[h_f1]-> h_f1
x_2 ->[h_f2]-> h_f2
x_3 ->[h_f3]-> h_f3

Backward hidden states:
                  <-[h_b3]<- x_3
                  <-[h_b2]<- x_2
                  <-[h_b1]<- x_1

Saida (concatenada):
y_1 = [h_f1; h_b1]  (concatenacao)
y_2 = [h_f2; h_b2]
y_3 = [h_f3; h_b3]

Cada direcao tem seus PROPRIO hidden state
e suas PROPRAS matrizes de peso.
```

### 8.3 Equacoes

```text
Equacoes da Bidirectional RNN:

Forward:
  h_f_t = tanh(W_xh_f * x_t + W_hh_f * h_f_{t-1} + b_h_f)

Backward:
  h_b_t = tanh(W_xh_b * x_t + W_hh_b * h_b_{t+1} + b_h_b)

Saida concatenada:
  y_t = softmax(W_hy * [h_f_t; h_b_t] + b_y)

Parametros:
  - Forward:  W_xh_f (d_h x d_x), W_hh_f (d_h x d_h), b_h_f
  - Backward: W_xh_b (d_h x d_x), W_hh_b (d_h x d_h), b_h_b
  - Saida:    W_hy (d_y x 2*d_h), b_y

Total de parametros: 2x o de uma RNN unidirecional
(sao duas RNNs independentes, uma para cada direcao)
```

### 8.4 Casos de Uso

```text
Quando usar Bidirectional RNN:

1. Classificacao de texto:
   - Sentimento: "Nao e bom" vs "Bom nao e"
   - A direcao importa em ambas as frases

2. Named Entity Recognition:
   - "Google foi fundada por Sergey Brin"
   - "Sergey" so e reconhecido como nome proprio
     porque sabemos que vem "Brin" depois

3. Traducao automatica:
   - Encoder bidirecional captura contexto completo
   - Decoder usa o contexto combinado

4. Reconhecimento de fala:
   - O audio futuro e util para desambiguar
   - "I saw the man with the telescope"
   - Contexto futuro ajuda a decidir

Quando NAO usar:
- Previsao de series temporais em tempo real
- Sistemas onde so temos dados passados
- Streaming (nao temos o futuro disponivel)
```

---

## 9. Sequence-to-Sequence

### 9.1 O Formato Encoder-Decoder

Sequence-to-sequence (Seq2Seq) e a arquitetura que conecta duas RNNs: uma encoder que comprime a entrada em um contexto, e uma decoder que gera a saida.

```text
Arquitetura Seq2Seq:

Encoder (comprime):
  x_1 ->[RNN]-> h_1
  x_2 ->[RNN]-> h_2
  x_3 ->[RNN]-> h_3 = contexto

Decoder (gera):
  <SOS> ->[RNN] + contexto -> y_1
  y_1   ->[RNN] + contexto -> y_2
  y_2   ->[RNN] + contexto -> y_3
  y_3   ->[RNN] + contexto -> <EOS>
```

### 9.2 O Contexto

O contexto e o hidden state final do encoder:

```text
Contexto:

Encoder:
  h_0 = [0, 0, ..., 0]
  h_1 = tanh(W_xh * x_1 + W_hh * h_0 + b_h)
  h_2 = tanh(W_xh * x_2 + W_hh * h_1 + b_h)
  h_3 = tanh(W_xh * x_3 + W_hh * h_2 + b_h)

  contexto = h_3

Decoder:
  h_0_dec = contexto  (o hidden state do decoder INICIA como o contexto)
  h_1_dec = tanh(W_xh_dec * <SOS> + W_hh_dec * h_0_dec + b_h_dec)
  h_2_dec = tanh(W_xh_dec * y_1 + W_hh_dec * h_1_dec + b_h_dec)
  ...
```

### 9.3 O Problema do Contexto Fixo

```text
Problema: Contexto de tamanho fixo

Entrada: "O gato pequeno sentou no tapete vermelho da sala"
Comprimido em: h_3 (vetor de 256 dimensoes)

256 dimensoes para 9 palavras = ~28 dimensoes por palavra
Isso E possivel para frases curtas.

Entrada: "O gato pequeno sentou no tapete vermelho da sala
que minha mae comprou na loja da esquina da rua principal
quando eu ainda era crianca e morava em Sao Paulo"
= 45 palavras -> 256 dimensoes = ~5 dimensoes por palavra

Isso e MUITO pouco. Informacao se perde.

Solucao: Attention mechanism (capitulo 13)
```

### 9.4 Tokens Especiais

```text
Tokens especiais no Seq2Seq:

<SOS> (Start of Sequence):
- Primeira entrada do decoder
- Indica que a geracao deve comecar
- Geralmente um embedding especial

<EOS> (End of Sequence):
- Indica que a saida terminou
- O decoder para de gerar quando produz este token
- Evita geracao infinita

<PAD>:
- Preenche sequencias de comprimento variavel
- Permite batching (processar multiplas sequencias juntas)
- Ignorado no calculo da loss

Exemplo de alinhamento:
Entrada:  [PAD] [PAD] "EU" "AMO" "C++"
Saida:    <SOS> "I" "LOVE" "C++" <EOS>
```

---

## 10. Implementacao Completa em C++

### 10.1 Estruturas de Dados

```cpp
#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <numeric>
#include <iostream>
#include <fstream>
#include <string>
#include <cassert>
#include <functional>

using Matrix = std::vector<std::vector<double>>;
using Vector = std::vector<double>;

Matrix create_matrix(int rows, int cols, double init_val = 0.0) {
    return Matrix(rows, Vector(cols, init_val));
}

Vector create_vector(int size, double init_val = 0.0) {
    return Vector(size, init_val);
}

Matrix matmul(const Matrix& A, const Matrix& B) {
    int rows = A.size();
    int cols = B[0].size();
    int inner = B.size();
    Matrix C = create_matrix(rows, cols);
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) {
            double sum = 0.0;
            for (int k = 0; k < inner; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }
    return C;
}

Vector matvec(const Matrix& M, const Vector& v) {
    int rows = M.size();
    Vector result(rows, 0.0);
    for (int i = 0; i < rows; i++) {
        double sum = 0.0;
        for (int j = 0; j < v.size(); j++) {
            sum += M[i][j] * v[j];
        }
        result[i] = sum;
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

double dot_product(const Vector& a, const Vector& b) {
    double sum = 0.0;
    for (size_t i = 0; i < a.size(); i++) {
        sum += a[i] * b[i];
    }
    return sum;
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

Vector sigmoid_vec(const Vector& v) {
    Vector result(v.size());
    for (size_t i = 0; i < v.size(); i++) {
        result[i] = 1.0 / (1.0 + std::exp(-v[i]));
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

double cross_entropy(const Vector& predicted, int target_idx) {
    double eps = 1e-12;
    return -std::log(std::max(predicted[target_idx], eps));
}
```

### 10.2 Estrutura da RNN

```cpp
struct RNNParams {
    Matrix W_xh;  // input -> hidden
    Matrix W_hh;  // hidden -> hidden
    Matrix W_hy;  // hidden -> output
    Vector b_h;   // hidden bias
    Vector b_y;   // output bias

    int input_size;
    int hidden_size;
    int output_size;

    RNNParams(int input_size, int hidden_size, int output_size)
        : input_size(input_size),
          hidden_size(hidden_size),
          output_size(output_size)
    {
        W_xh = create_matrix(hidden_size, input_size);
        W_hh = create_matrix(hidden_size, hidden_size);
        W_hy = create_matrix(output_size, hidden_size);
        b_h = create_vector(hidden_size);
        b_y = create_vector(output_size);
    }
};

struct RNNCache {
    std::vector<Vector> inputs;
    std::vector<Vector> hidden_states;
    std::vector<Vector> pre_activations;
    std::vector<Vector> outputs;
};

struct RNNGrads {
    Matrix dW_xh;
    Matrix dW_hh;
    Matrix dW_hy;
    Vector db_h;
    Vector db_y;

    RNNGrads(int input_size, int hidden_size, int output_size)
        : dW_xh(create_matrix(hidden_size, input_size)),
          dW_hh(create_matrix(hidden_size, hidden_size)),
          dW_hy(create_matrix(output_size, hidden_size)),
          db_h(create_vector(hidden_size)),
          db_y(create_vector(output_size))
    {}
};
```

### 10.3 Geracao de Pesos

```cpp
void init_weights(Matrix& W, double std_dev) {
    std::mt19937 gen(42);
    std::normal_distribution<> dist(0.0, std_dev);
    for (auto& row : W) {
        for (auto& w : row) {
            w = dist(gen);
        }
    }
}

void init_rnn_weights(RNNParams& params) {
    double std_xh = std::sqrt(2.0 / (params.input_size + params.hidden_size));
    double std_hh = std::sqrt(2.0 / (params.hidden_size + params.hidden_size));
    double std_hy = std::sqrt(2.0 / (params.hidden_size + params.output_size));

    init_weights(params.W_xh, std_xh);
    init_weights(params.W_hh, std_hh);
    init_weights(params.W_hy, std_hy);
}
```

### 10.4 Forward Pass

```cpp
RNNCache rnn_forward(
    const RNNParams& params,
    const std::vector<Vector>& inputs
) {
    int seq_len = inputs.size();
    RNNCache cache;
    cache.inputs = inputs;
    cache.hidden_states.resize(seq_len + 1);
    cache.pre_activations.resize(seq_len);
    cache.outputs.resize(seq_len);

    // Hidden state inicial: zeros
    cache.hidden_states[0] = create_vector(params.hidden_size);

    for (int t = 0; t < seq_len; t++) {
        // h_t = tanh(W_xh * x_t + W_hh * h_{t-1} + b_h)
        Vector wx = matvec(params.W_xh, inputs[t]);
        Vector wh = matvec(params.W_hh, cache.hidden_states[t]);
        Vector pre_act = vec_add(vec_add(wx, wh), params.b_h);
        cache.pre_activations[t] = pre_act;
        cache.hidden_states[t + 1] = tanh_vec(pre_act);

        // y_t = softmax(W_hy * h_t + b_y)
        Vector wy = matvec(params.W_hy, cache.hidden_states[t + 1]);
        Vector logits = vec_add(wy, params.b_y);
        cache.outputs[t] = softmax(logits);
    }

    return cache;
}
```

### 10.5 Backward Pass (BPTT)

```cpp
RNNGrads rnn_backward(
    const RNNParams& params,
    const RNNCache& cache,
    const std::vector<int>& targets,
    int seq_len
) {
    RNNGrads grads(params.input_size, params.hidden_size, params.output_size);

    Vector dh_next(params.hidden_size, 0.0);

    for (int t = seq_len - 1; t >= 0; t--) {
        // Gradiente da saida: dy = y - target
        Vector dy = cache.outputs[t];
        dy[targets[t]] -= 1.0;

        // dW_hy += dy * h_t^T
        for (int i = 0; i < params.output_size; i++) {
            for (int j = 0; j < params.hidden_size; j++) {
                grads.dW_hy[i][j] += dy[i] * cache.hidden_states[t + 1][j];
            }
            grads.db_y[i] += dy[i];
        }

        // dh = W_hy^T * dy + dh_next
        Vector dh(params.hidden_size, 0.0);
        for (int j = 0; j < params.hidden_size; j++) {
            for (int i = 0; i < params.output_size; i++) {
                dh[j] += params.W_hy[i][j] * dy[i];
            }
            dh[j] += dh_next[j];
        }

        // dtanh = dh * (1 - h_t^2)
        Vector dtanh = tanh_deriv(cache.hidden_states[t + 1]);
        for (int j = 0; j < params.hidden_size; j++) {
            dtanh[j] *= dh[j];
        }

        // dW_xh += dtanh * x_t^T
        for (int j = 0; j < params.hidden_size; j++) {
            for (int i = 0; i < params.input_size; i++) {
                grads.dW_xh[j][i] += dtanh[j] * cache.inputs[t][i];
            }
            grads.db_h[j] += dtanh[j];
        }

        // dW_hh += dtanh * h_{t-1}^T
        for (int j = 0; j < params.hidden_size; j++) {
            for (int i = 0; i < params.hidden_size; i++) {
                grads.dW_hh[j][i] += dtanh[j] * cache.hidden_states[t][i];
            }
        }

        // Propagar para o passo anterior: dh_next = W_hh^T * dtanh
        dh_next.assign(params.hidden_size, 0.0);
        for (int i = 0; i < params.hidden_size; i++) {
            for (int j = 0; j < params.hidden_size; j++) {
                dh_next[i] += params.W_hh[j][i] * dtanh[j];
            }
        }
    }

    return grads;
}
```

### 10.6 Atualizacao de Pesos (SGD)

```cpp
void update_params(RNNParams& params, const RNNGrads& grads, double lr, int seq_len) {
    for (int i = 0; i < params.hidden_size; i++) {
        for (int j = 0; j < params.input_size; j++) {
            params.W_xh[i][j] -= lr * grads.dW_xh[i][j] / seq_len;
        }
        params.b_h[i] -= lr * grads.db_h[i] / seq_len;
    }

    for (int i = 0; i < params.hidden_size; i++) {
        for (int j = 0; j < params.hidden_size; j++) {
            params.W_hh[i][j] -= lr * grads.dW_hh[i][j] / seq_len;
        }
    }

    for (int i = 0; i < params.output_size; i++) {
        for (int j = 0; j < params.hidden_size; j++) {
            params.W_hy[i][j] -= lr * grads.dW_hy[i][j] / seq_len;
        }
        params.b_y[i] -= lr * grads.db_y[i] / seq_len;
    }
}
```

### 10.7 Gradient Clipping

```cpp
void clip_gradients(RNNGrads& grads, double max_norm) {
    double total_norm = 0.0;

    for (const auto& row : grads.dW_xh)
        for (double g : row) total_norm += g * g;
    for (const auto& row : grads.dW_hh)
        for (double g : row) total_norm += g * g;
    for (const auto& row : grads.dW_hy)
        for (double g : row) total_norm += g * g;
    for (double g : grads.db_h) total_norm += g * g;
    for (double g : grads.db_y) total_norm += g * g;

    total_norm = std::sqrt(total_norm);

    if (total_norm > max_norm) {
        double scale = max_norm / total_norm;
        for (auto& row : grads.dW_xh)
            for (double& g : row) g *= scale;
        for (auto& row : grads.dW_hh)
            for (double& g : row) g *= scale;
        for (auto& row : grads.dW_hy)
            for (double& g : row) g *= scale;
        for (double& g : grads.db_h) g *= scale;
        for (double& g : grads.db_y) g *= scale;
    }
}
```

### 10.8 Treinamento Completo

```cpp
struct TrainingConfig {
    int hidden_size;
    double learning_rate;
    double gradient_clip_norm;
    int epochs;
    bool verbose;
};

double train_rnn(
    RNNParams& params,
    const std::vector<std::vector<Vector>>& all_inputs,
    const std::vector<std::vector<int>>& all_targets,
    const TrainingConfig& config
) {
    double total_loss = 0.0;
    int num_sequences = all_inputs.size();

    for (int e = 0; e < config.epochs; e++) {
        double epoch_loss = 0.0;

        for (int s = 0; s < num_sequences; s++) {
            int seq_len = all_inputs[s].size();

            // Forward pass
            RNNCache cache = rnn_forward(params, all_inputs[s]);

            // Calcular loss
            double seq_loss = 0.0;
            for (int t = 0; t < seq_len; t++) {
                seq_loss += cross_entropy(cache.outputs[t], all_targets[s][t]);
            }
            epoch_loss += seq_loss;

            // Backward pass
            RNNGrads grads = rnn_backward(params, cache, all_targets[s], seq_len);

            // Gradient clipping
            clip_gradients(grads, config.gradient_clip_norm);

            // Atualizar pesos
            update_params(params, grads, config.learning_rate, seq_len);
        }

        epoch_loss /= num_sequences;

        if (config.verbose && (e % 10 == 0 || e == config.epochs - 1)) {
            std::cout << "Epoch " << e
                      << " | Loss: " << epoch_loss
                      << std::endl;
        }

        total_loss = epoch_loss;
    }

    return total_loss;
}
```

### 10.9 Inferencia

```cpp
int predict_next(
    const RNNParams& params,
    Vector& hidden_state,
    const Vector& input
) {
    // Forward de um unico passo
    Vector wx = matvec(params.W_xh, input);
    Vector wh = matvec(params.W_hh, hidden_state);
    Vector pre_act = vec_add(vec_add(wx, wh), params.b_h);
    hidden_state = tanh_vec(pre_act);

    Vector wy = matvec(params.W_hy, hidden_state);
    Vector logits = vec_add(wy, params.b_y);
    Vector probs = softmax(logits);

    // Retornar indice da classe com maior probabilidade
    return std::max_element(probs.begin(), probs.end()) - probs.begin();
}

std::vector<int> generate_sequence(
    const RNNParams& params,
    const Vector& start_input,
    int num_steps
) {
    std::vector<int> generated;
    Vector hidden = create_vector(params.hidden_size);
    Vector current_input = start_input;

    for (int t = 0; t < num_steps; t++) {
        int pred = predict_next(params, hidden, current_input);
        generated.push_back(pred);

        // Usar a saida como proxima entrada (one-hot)
        current_input = create_vector(params.input_size);
        if (pred < static_cast<int>(current_input.size())) {
            current_input[pred] = 1.0;
        }
    }

    return generated;
}
```

### 10.10 Exemplo: Previsao de Serie Temporal

```cpp
// Gerar serie temporal simples: seno com ruido
std::vector<Vector> generate_sine_data(int num_samples, int seq_len) {
    std::vector<Vector> data;
    std::mt19937 gen(42);
    std::normal_distribution<> noise(0.0, 0.1);

    for (int i = 0; i < num_samples; i++) {
        Vector seq(seq_len);
        double phase = (double)i * 0.1;
        for (int t = 0; t < seq_len; t++) {
            seq[t] = std::sin(phase + t * 0.1) + noise(gen);
        }
        data.push_back(seq);
    }
    return data;
}

int main() {
    // Configuracao
    int input_size = 1;
    int hidden_size = 32;
    int output_size = 1;
    int seq_len = 20;

    // Inicializar RNN
    RNNParams params(input_size, hidden_size, output_size);
    init_rnn_weights(params);

    // Gerar dados
    auto raw_data = generate_sine_data(100, seq_len + 1);

    // Preparar entradas e targets
    std::vector<std::vector<Vector>> all_inputs;
    std::vector<std::vector<int>> all_targets;

    for (const auto& seq : raw_data) {
        std::vector<Vector> inputs;
        std::vector<int> targets;

        for (int t = 0; t < seq_len; t++) {
            inputs.push_back({seq[t]});
            // Quantizar saida para classificacao
            int target_bin = static_cast<int>((seq[t + 1] + 1.0) * 5.0);
            target_bin = std::max(0, std::min(target_bin, output_size - 1));
            targets.push_back(target_bin);
        }

        all_inputs.push_back(inputs);
        all_targets.push_back(targets);
    }

    // Treinar
    TrainingConfig config;
    config.hidden_size = hidden_size;
    config.learning_rate = 0.01;
    config.gradient_clip_norm = 5.0;
    config.epochs = 100;
    config.verbose = true;

    double final_loss = train_rnn(params, all_inputs, all_targets, config);

    std::cout << "\nTreinamento concluido!" << std::endl;
    std::cout << "Loss final: " << final_loss << std::endl;

    return 0;
}
```

---

## 11. Implementacao em Rust

### 11.1 Modulo de Operacoes Basicas

```rust
use std::f64;

type Vector = Vec<f64>;
type Matrix = Vec<Vec<f64>>;

fn create_matrix(rows: usize, cols: usize, init: f64) -> Matrix {
    (0..rows).map(|_| vec![init; cols]).collect()
}

fn create_vector(size: usize, init: f64) -> Vector {
    vec![init; size]
}

fn matmul(a: &Matrix, b: &Matrix) -> Matrix {
    let rows = a.len();
    let cols = b[0].len();
    let inner = b.len();
    let mut c = create_matrix(rows, cols, 0.0);
    for i in 0..rows {
        for j in 0..cols {
            let mut sum = 0.0;
            for k in 0..inner {
                sum += a[i][k] * b[k][j];
            }
            c[i][j] = sum;
        }
    }
    c
}

fn matvec(m: &Matrix, v: &Vector) -> Vector {
    m.iter().map(|row| {
        row.iter().zip(v.iter()).map(|(a, b)| a * b).sum()
    }).collect()
}

fn vec_add(a: &Vector, b: &Vector) -> Vector {
    a.iter().zip(b.iter()).map(|(x, y)| x + y).collect()
}

fn vec_sub(a: &Vector, b: &Vector) -> Vector {
    a.iter().zip(b.iter()).map(|(x, y)| x - y).collect()
}

fn dot(a: &Vector, b: &Vector) -> f64 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

fn tanh_vec(v: &Vector) -> Vector {
    v.iter().map(|x| x.tanh()).collect()
}

fn tanh_deriv(h: &Vector) -> Vector {
    h.iter().map(|x| 1.0 - x * x).collect()
}

fn sigmoid(v: &Vector) -> Vector {
    v.iter().map(|x| 1.0 / (1.0 + (-x).exp())).collect()
}

fn softmax(v: &Vector) -> Vector {
    let max_val = v.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let exp_v: Vector = v.iter().map(|x| (x - max_val).exp()).collect();
    let sum: f64 = exp_v.iter().sum();
    exp_v.iter().map(|x| x / sum).collect()
}

fn cross_entropy(predicted: &Vector, target: usize) -> f64 {
    let eps = 1e-12;
    -((predicted[target]).max(eps)).ln()
}
```

### 11.2 Estrutura da RNN

```rust
struct RNNParams {
    w_xh: Matrix,
    w_hh: Matrix,
    w_hy: Matrix,
    b_h: Vector,
    b_y: Vector,
    input_size: usize,
    hidden_size: usize,
    output_size: usize,
}

struct RNNCache {
    inputs: Vec<Vector>,
    hidden_states: Vec<Vector>,
    pre_activations: Vec<Vector>,
    outputs: Vec<Vector>,
}

struct RNNGrads {
    dw_xh: Matrix,
    dw_hh: Matrix,
    dw_hy: Matrix,
    db_h: Vector,
    db_y: Vector,
}

impl RNNParams {
    fn new(input_size: usize, hidden_size: usize, output_size: usize) -> Self {
        Self {
            w_xh: create_matrix(hidden_size, input_size, 0.0),
            w_hh: create_matrix(hidden_size, hidden_size, 0.0),
            w_hy: create_matrix(output_size, hidden_size, 0.0),
            b_h: create_vector(hidden_size, 0.0),
            b_y: create_vector(output_size, 0.0),
            input_size,
            hidden_size,
            output_size,
        }
    }

    fn init_weights(&mut self) {
        use std::f64::consts::SQRT_2;

        let std_xh = (SQRT_2 / (self.input_size + self.hidden_size) as f64).sqrt();
        let std_hh = (SQRT_2 / (self.hidden_size + self.hidden_size) as f64).sqrt();
        let std_hy = (SQRT_2 / (self.hidden_size + self.output_size) as f64).sqrt();

        randomize_matrix(&mut self.w_xh, std_xh);
        randomize_matrix(&mut self.w_hh, std_hh);
        randomize_matrix(&mut self.w_hy, std_hy);
    }
}

fn randomize_matrix(m: &mut Matrix, std_dev: f64) {
    // Simple LCG for reproducibility
    let mut seed: u64 = 12345;
    for row in m.iter_mut() {
        for val in row.iter_mut() {
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let u = (seed >> 11) as f64 / (1u64 << 53) as f64;
            let z = (-2.0 * (1.0 - u).ln()).sqrt() * (2.0 * std::f64::consts::PI * ((seed >> 11) as f64 / (1u64 << 53) as f64)).cos();
            *val = z * std_dev;
            seed = seed.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        }
    }
}
```

### 11.3 Forward e Backward

```rust
fn rnn_forward(params: &RNNParams, inputs: &[Vector]) -> RNNCache {
    let seq_len = inputs.len();
    let mut cache = RNNCache {
        inputs: inputs.to_vec(),
        hidden_states: Vec::with_capacity(seq_len + 1),
        pre_activations: Vec::with_capacity(seq_len),
        outputs: Vec::with_capacity(seq_len),
    };

    cache.hidden_states.push(create_vector(params.hidden_size, 0.0));

    for t in 0..seq_len {
        let wx = matvec(&params.w_xh, &inputs[t]);
        let wh = matvec(&params.w_hh, &cache.hidden_states[t]);
        let pre_act = vec_add(&vec_add(&wx, &wh), &params.b_h);
        cache.pre_activations.push(pre_act.clone());
        cache.hidden_states.push(tanh_vec(&pre_act));

        let wy = matvec(&params.w_hy, &cache.hidden_states[t + 1]);
        let logits = vec_add(&wy, &params.b_y);
        cache.outputs.push(softmax(&logits));
    }

    cache
}

fn rnn_backward(
    params: &RNNParams,
    cache: &RNNCache,
    targets: &[usize],
) -> RNNGrads {
    let seq_len = targets.len();
    let mut grads = RNNGrads {
        dw_xh: create_matrix(params.hidden_size, params.input_size, 0.0),
        dw_hh: create_matrix(params.hidden_size, params.hidden_size, 0.0),
        dw_hy: create_matrix(params.output_size, params.hidden_size, 0.0),
        db_h: create_vector(params.hidden_size, 0.0),
        db_y: create_vector(params.output_size, 0.0),
    };

    let mut dh_next = create_vector(params.hidden_size, 0.0);

    for t in (0..seq_len).rev() {
        let mut dy = cache.outputs[t].clone();
        dy[targets[t]] -= 1.0;

        for i in 0..params.output_size {
            for j in 0..params.hidden_size {
                grads.dw_hy[i][j] += dy[i] * cache.hidden_states[t + 1][j];
            }
            grads.db_y[i] += dy[i];
        }

        let mut dh = create_vector(params.hidden_size, 0.0);
        for j in 0..params.hidden_size {
            for i in 0..params.output_size {
                dh[j] += params.w_hy[i][j] * dy[i];
            }
            dh[j] += dh_next[j];
        }

        let dtanh = tanh_deriv(&cache.hidden_states[t + 1]);
        let dtanh: Vector = dtanh.iter().zip(dh.iter()).map(|(a, b)| a * b).collect();

        for j in 0..params.hidden_size {
            for i in 0..params.input_size {
                grads.dw_xh[j][i] += dtanh[j] * cache.inputs[t][i];
            }
            grads.db_h[j] += dtanh[j];
        }

        for j in 0..params.hidden_size {
            for i in 0..params.hidden_size {
                grads.dw_hh[j][i] += dtanh[j] * cache.hidden_states[t][i];
            }
        }

        dh_next = create_vector(params.hidden_size, 0.0);
        for i in 0..params.hidden_size {
            for j in 0..params.hidden_size {
                dh_next[i] += params.w_hh[j][i] * dtanh[j];
            }
        }
    }

    grads
}
```

### 11.4 Treinamento em Rust

```rust
fn update_params(params: &mut RNNParams, grads: &RNNGrads, lr: f64, seq_len: usize) {
    for i in 0..params.hidden_size {
        for j in 0..params.input_size {
            params.w_xh[i][j] -= lr * grads.dw_xh[i][j] / seq_len as f64;
        }
        params.b_h[i] -= lr * grads.db_h[i] / seq_len as f64;
    }

    for i in 0..params.hidden_size {
        for j in 0..params.hidden_size {
            params.w_hh[i][j] -= lr * grads.dw_hh[i][j] / seq_len as f64;
        }
    }

    for i in 0..params.output_size {
        for j in 0..params.hidden_size {
            params.w_hy[i][j] -= lr * grads.dw_hy[i][j] / seq_len as f64;
        }
        params.b_y[i] -= lr * grads.db_y[i] / seq_len as f64;
    }
}

fn clip_gradients(grads: &mut RNNGrads, max_norm: f64) {
    let mut total_norm = 0.0f64;

    for row in &grads.dw_xh {
        for g in row { total_norm += g * g; }
    }
    for row in &grads.dw_hh {
        for g in row { total_norm += g * g; }
    }
    for row in &grads.dw_hy {
        for g in row { total_norm += g * g; }
    }
    for g in &grads.db_h { total_norm += g * g; }
    for g in &grads.db_y { total_norm += g * g; }

    total_norm = total_norm.sqrt();

    if total_norm > max_norm {
        let scale = max_norm / total_norm;
        for row in grads.dw_xh.iter_mut() {
            for g in row.iter_mut() { *g *= scale; }
        }
        for row in grads.dw_hh.iter_mut() {
            for g in row.iter_mut() { *g *= scale; }
        }
        for row in grads.dw_hy.iter_mut() {
            for g in row.iter_mut() { *g *= scale; }
        }
        for g in grads.db_h.iter_mut() { *g *= scale; }
        for g in grads.db_y.iter_mut() { *g *= scale; }
    }
}

fn train_rnn(
    params: &mut RNNParams,
    all_inputs: &[Vec<Vector>],
    all_targets: &[Vec<usize>],
    lr: f64,
    epochs: usize,
    clip_norm: f64,
    verbose: bool,
) -> f64 {
    params.init_weights();
    let num_sequences = all_inputs.len();
    let mut final_loss = 0.0;

    for e in 0..epochs {
        let mut epoch_loss = 0.0;

        for s in 0..num_sequences {
            let seq_len = all_inputs[s].len();
            let cache = rnn_forward(params, &all_inputs[s]);

            let mut seq_loss = 0.0;
            for t in 0..seq_len {
                seq_loss += cross_entropy(&cache.outputs[t], all_targets[s][t]);
            }
            epoch_loss += seq_loss;

            let mut grads = rnn_backward(params, &cache, &all_targets[s]);
            clip_gradients(&mut grads, clip_norm);
            update_params(params, &grads, lr, seq_len);
        }

        epoch_loss /= num_sequences as f64;

        if verbose && (e % 10 == 0 || e == epochs - 1) {
            println!("Epoch {} | Loss: {:.6}", e, epoch_loss);
        }

        final_loss = epoch_loss;
    }

    final_loss
}

fn main() {
    let input_size = 1;
    let hidden_size = 32;
    let output_size = 1;
    let seq_len = 20;

    let mut params = RNNParams::new(input_size, hidden_size, output_size);

    // Gerar dados de serie temporal (simplificado)
    let mut all_inputs: Vec<Vec<Vector>> = Vec::new();
    let mut all_targets: Vec<Vec<usize>> = Vec::new();

    for i in 0..100 {
        let mut inputs = Vec::new();
        let mut targets = Vec::new();
        let phase = i as f64 * 0.1;

        for t in 0..seq_len {
            inputs.push(vec![(phase + t as f64 * 0.1).sin()]);
            let next_val = (phase + (t + 1) as f64 * 0.1).sin();
            let bin = ((next_val + 1.0) * 5.0) as usize;
            targets.push(bin.min(output_size - 1));
        }

        all_inputs.push(inputs);
        all_targets.push(targets);
    }

    let final_loss = train_rnn(&mut params, &all_inputs, &all_targets, 0.01, 100, 5.0, true);
    println!("\nTreinamento concluido! Loss final: {:.6}", final_loss);
}
```

---

## 12. Implementacao em Fortran

### 12.1 Modulo de Operacoes Basicas

```fortran
module rnn_ops
    implicit none
    private
    public :: matmul_rv, vec_add, vec_sub, dot_prod
    public :: tanh_vec, tanh_deriv_vec, softmax_vec, cross_entropy_loss
    public :: create_matrix_r, create_vector_r

contains

    ! Matrix-vector multiplication: result = M * v
    function matmul_rv(M, v, rows, cols) result(res)
        integer, intent(in) :: rows, cols
        real(8), intent(in) :: M(rows, cols), v(cols)
        real(8) :: res(rows)
        integer :: i, j

        do i = 1, rows
            res(i) = 0.0d0
            do j = 1, cols
                res(i) = res(i) + M(i, j) * v(j)
            end do
        end do
    end function matmul_rv

    ! Vector addition
    function vec_add(a, b, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: a(n), b(n)
        real(8) :: res(n)
        integer :: i

        do i = 1, n
            res(i) = a(i) + b(i)
        end do
    end function vec_add

    ! Vector subtraction
    function vec_sub(a, b, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: a(n), b(n)
        real(8) :: res(n)
        integer :: i

        do i = 1, n
            res(i) = a(i) - b(i)
        end do
    end function vec_sub

    ! Dot product
    function dot_prod(a, b, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: a(n), b(n)
        real(8) :: res
        integer :: i

        res = 0.0d0
        do i = 1, n
            res = res + a(i) * b(i)
        end do
    end function dot_prod

    ! Element-wise tanh
    function tanh_vec(v, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: v(n)
        real(8) :: res(n)
        integer :: i

        do i = 1, n
            res(i) = tanh(v(i))
        end do
    end function tanh_vec

    ! Derivative of tanh: 1 - h^2
    function tanh_deriv_vec(h, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: h(n)
        real(8) :: res(n)
        integer :: i

        do i = 1, n
            res(i) = 1.0d0 - h(i) * h(i)
        end do
    end function tanh_deriv_vec

    ! Softmax function
    function softmax_vec(v, n) result(res)
        integer, intent(in) :: n
        real(8), intent(in) :: v(n)
        real(8) :: res(n)
        real(8) :: max_val, sum_exp
        integer :: i

        max_val = v(1)
        do i = 2, n
            if (v(i) > max_val) max_val = v(i)
        end do

        sum_exp = 0.0d0
        do i = 1, n
            res(i) = exp(v(i) - max_val)
            sum_exp = sum_exp + res(i)
        end do

        do i = 1, n
            res(i) = res(i) / sum_exp
        end do
    end function softmax_vec

    ! Cross-entropy loss
    function cross_entropy_loss(predicted, target, n) result(loss)
        integer, intent(in) :: n, target
        real(8), intent(in) :: predicted(n)
        real(8) :: loss
        real(8), parameter :: eps = 1.0d-12

        loss = -log(max(predicted(target), eps))
    end function cross_entropy_loss

    ! Create zero matrix
    subroutine create_matrix_r(M, rows, cols)
        integer, intent(in) :: rows, cols
        real(8), intent(out) :: M(rows, cols)
        integer :: i, j

        do i = 1, rows
            do j = 1, cols
                M(i, j) = 0.0d0
            end do
        end do
    end subroutine create_matrix_r

    ! Create zero vector
    subroutine create_vector_r(v, n)
        integer, intent(in) :: n
        real(8), intent(out) :: v(n)
        integer :: i

        do i = 1, n
            v(i) = 0.0d0
        end do
    end subroutine create_vector_r

end module rnn_ops
```

### 12.2 Modulo RNN

```fortran
module rnn_module
    use rnn_ops
    implicit none
    private
    public :: rnn_forward_step, rnn_backward_step, rnn_forward_seq

contains

    ! Forward step for a single time step
    subroutine rnn_forward_step(x_t, h_prev, W_xh, W_hh, W_hy, b_h, b_y, &
                                h_t, y_t, input_size, hidden_size, output_size)
        implicit none
        integer, intent(in) :: input_size, hidden_size, output_size
        real(8), intent(in) :: x_t(input_size)
        real(8), intent(in) :: h_prev(hidden_size)
        real(8), intent(in) :: W_xh(hidden_size, input_size)
        real(8), intent(in) :: W_hh(hidden_size, hidden_size)
        real(8), intent(in) :: W_hy(output_size, hidden_size)
        real(8), intent(in) :: b_h(hidden_size)
        real(8), intent(in) :: b_y(output_size)
        real(8), intent(out) :: h_t(hidden_size)
        real(8), intent(out) :: y_t(output_size)

        real(8) :: wx(hidden_size), wh(hidden_size)
        real(8) :: pre_act(hidden_size)
        real(8) :: wy(output_size), logits(output_size)

        ! h_t = tanh(W_xh * x_t + W_hh * h_{t-1} + b_h)
        wx = matmul_rv(W_xh, x_t, hidden_size, input_size)
        wh = matmul_rv(W_hh, h_prev, hidden_size, hidden_size)
        pre_act = vec_add(vec_add(wx, wh, hidden_size), b_h, hidden_size)
        h_t = tanh_vec(pre_act, hidden_size)

        ! y_t = softmax(W_hy * h_t + b_y)
        wy = matmul_rv(W_hy, h_t, output_size, hidden_size)
        logits = vec_add(wy, b_y, output_size)
        y_t = softmax_vec(logits, output_size)
    end subroutine rnn_forward_step

    ! Forward pass for entire sequence
    subroutine rnn_forward_seq(inputs, seq_len, W_xh, W_hh, W_hy, b_h, b_y, &
                               hidden_states, outputs, input_size, hidden_size, output_size)
        implicit none
        integer, intent(in) :: seq_len, input_size, hidden_size, output_size
        real(8), intent(in) :: inputs(input_size, seq_len)
        real(8), intent(in) :: W_xh(hidden_size, input_size)
        real(8), intent(in) :: W_hh(hidden_size, hidden_size)
        real(8), intent(in) :: W_hy(output_size, hidden_size)
        real(8), intent(in) :: b_h(hidden_size)
        real(8), intent(in) :: b_y(output_size)
        real(8), intent(out) :: hidden_states(hidden_size, seq_len + 1)
        real(8), intent(out) :: outputs(output_size, seq_len)

        real(8) :: h_prev(hidden_size)
        real(8) :: h_t(hidden_size), y_t(output_size)
        integer :: t

        ! h_0 = zeros
        call create_vector_r(h_prev, hidden_size)
        call create_vector_r(hidden_states(:, 1), hidden_size)

        do t = 1, seq_len
            h_prev = hidden_states(:, t)
            call rnn_forward_step(inputs(:, t), h_prev, W_xh, W_hh, W_hy, &
                                  b_h, b_y, h_t, y_t, input_size, hidden_size, output_size)
            hidden_states(:, t + 1) = h_t
            outputs(:, t) = y_t
        end do
    end subroutine rnn_forward_seq

    ! Backward step for a single time step
    subroutine rnn_backward_step(t, targets, hidden_states, inputs, outputs, &
                                 W_hy, W_hh, W_xh, dh_next, &
                                 dW_hy, dW_hh, dW_xh, db_y, db_h, &
                                 seq_len, input_size, hidden_size, output_size)
        implicit none
        integer, intent(in) :: t, seq_len, input_size, hidden_size, output_size
        integer, intent(in) :: targets(seq_len)
        real(8), intent(in) :: hidden_states(hidden_size, seq_len + 1)
        real(8), intent(in) :: inputs(input_size, seq_len)
        real(8), intent(in) :: outputs(output_size, seq_len)
        real(8), intent(in) :: W_hy(output_size, hidden_size)
        real(8), intent(in) :: W_hh(hidden_size, hidden_size)
        real(8), intent(in) :: W_xh(hidden_size, input_size)
        real(8), intent(in) :: dh_next(hidden_size)
        real(8), intent(inout) :: dW_hy(output_size, hidden_size)
        real(8), intent(inout) :: dW_hh(hidden_size, hidden_size)
        real(8), intent(inout) :: dW_xh(hidden_size, input_size)
        real(8), intent(inout) :: db_y(output_size)
        real(8), intent(inout) :: db_h(hidden_size)

        real(8) :: dy(output_size), dh(hidden_size), dtanh(hidden_size)
        real(8) :: dh_new(hidden_size)
        integer :: i, j

        ! dy = y_t - one_hot(target)
        dy = outputs(:, t)
        dy(targets(t) + 1) = dy(targets(t) + 1) - 1.0d0

        ! dW_hy += dy * h_t^T
        do i = 1, output_size
            do j = 1, hidden_size
                dW_hy(i, j) = dW_hy(i, j) + dy(i) * hidden_states(j, t + 1)
            end do
            db_y(i) = db_y(i) + dy(i)
        end do

        ! dh = W_hy^T * dy + dh_next
        dh = dh_next
        do j = 1, hidden_size
            do i = 1, output_size
                dh(j) = dh(j) + W_hy(i, j) * dy(i)
            end do
        end do

        ! dtanh = dh * (1 - h_t^2)
        dtanh = dh * tanh_deriv_vec(hidden_states(:, t + 1), hidden_size)

        ! dW_xh += dtanh * x_t^T
        do j = 1, hidden_size
            do i = 1, input_size
                dW_xh(j, i) = dW_xh(j, i) + dtanh(j) * inputs(i, t)
            end do
            db_h(j) = db_h(j) + dtanh(j)
        end do

        ! dW_hh += dtanh * h_{t-1}^T
        do j = 1, hidden_size
            do i = 1, hidden_size
                dW_hh(j, i) = dW_hh(j, i) + dtanh(j) * hidden_states(i, t)
            end do
        end do

        ! dh_new = W_hh^T * dtanh
        do i = 1, hidden_size
            dh_new(i) = 0.0d0
            do j = 1, hidden_size
                dh_new(i) = dh_new(i) + W_hh(j, i) * dtanh(j)
            end do
        end do
    end subroutine rnn_backward_step

end module rnn_module
```

### 12.3 Programa Principal em Fortran

```fortran
program rnn_example
    use rnn_ops
    use rnn_module
    implicit none

    integer, parameter :: input_size = 1
    integer, parameter :: hidden_size = 32
    integer, parameter :: output_size = 1
    integer, parameter :: seq_len = 20
    integer, parameter :: num_samples = 100
    integer, parameter :: epochs = 100
    real(8), parameter :: lr = 0.01d0

    real(8) :: W_xh(hidden_size, input_size)
    real(8) :: W_hh(hidden_size, hidden_size)
    real(8) :: W_hy(output_size, hidden_size)
    real(8) :: b_h(hidden_size), b_y(output_size)

    real(8) :: inputs(input_size, seq_len)
    real(8) :: hidden_states(hidden_size, seq_len + 1)
    real(8) :: outputs(output_size, seq_len)
    real(8) :: dW_xh(hidden_size, input_size)
    real(8) :: dW_hh(hidden_size, hidden_size)
    real(8) :: dW_hy(output_size, hidden_size)
    real(8) :: db_h(hidden_size), db_y(output_size)
    real(8) :: dh_next(hidden_size)
    real(8) :: targets(seq_len)
    real(8) :: epoch_loss, total_loss
    real(8) :: phase, val
    integer :: e, s, t, i, j

    ! Initialize weights (simple random)
    call random_number(W_xh)
    call random_number(W_hh)
    call random_number(W_hy)
    W_xh = (W_xh - 0.5d0) * 0.1d0
    W_hh = (W_hh - 0.5d0) * 0.1d0
    W_hy = (W_hy - 0.5d0) * 0.1d0
    call create_vector_r(b_h, hidden_size)
    call create_vector_r(b_y, output_size)

    ! Training loop
    do e = 0, epochs - 1
        epoch_loss = 0.0d0

        do s = 1, num_samples
            phase = dble(s) * 0.1d0

            ! Generate sine data
            do t = 1, seq_len
                inputs(1, t) = sin(phase + dble(t) * 0.1d0)
                targets(t) = int((sin(phase + dble(t + 1) * 0.1d0) + 1.0d0) * 5.0d0) + 1
                if (targets(t) < 1) targets(t) = 1
                if (targets(t) > output_size) targets(t) = output_size
            end do

            ! Forward pass
            call rnn_forward_seq(inputs, seq_len, W_xh, W_hh, W_hy, b_h, b_y, &
                                 hidden_states, outputs, input_size, hidden_size, output_size)

            ! Compute loss
            do t = 1, seq_len
                epoch_loss = epoch_loss + cross_entropy_loss(outputs(:, t), int(targets(t)), output_size)
            end do

            ! Backward pass (simplified - just update weights)
            call create_vector_r(dh_next, hidden_size)
            call create_matrix_r(dW_xh, hidden_size, input_size)
            call create_matrix_r(dW_hh, hidden_size, hidden_size)
            call create_matrix_r(dW_hy, output_size, hidden_size)
            call create_vector_r(db_y, output_size)
            call create_vector_r(db_h, hidden_size)

            do t = seq_len, 1, -1
                call rnn_backward_step(t, int(targets), hidden_states, inputs, outputs, &
                                       W_hy, W_hh, W_xh, dh_next, &
                                       dW_hy, dW_hh, dW_xh, db_y, db_h, &
                                       seq_len, input_size, hidden_size, output_size)
            end do

            ! Update weights
            do i = 1, hidden_size
                do j = 1, input_size
                    W_xh(i, j) = W_xh(i, j) - lr * dW_xh(i, j) / dble(seq_len)
                end do
                b_h(i) = b_h(i) - lr * db_h(i) / dble(seq_len)
            end do

            do i = 1, hidden_size
                do j = 1, hidden_size
                    W_hh(i, j) = W_hh(i, j) - lr * dW_hh(i, j) / dble(seq_len)
                end do
            end do

            do i = 1, output_size
                do j = 1, hidden_size
                    W_hy(i, j) = W_hy(i, j) - lr * dW_hy(i, j) / dble(seq_len)
                end do
                b_y(i) = b_y(i) - lr * db_y(i) / dble(seq_len)
            end do
        end do

        epoch_loss = epoch_loss / dble(num_samples)
        if (mod(e, 10) == 0) then
            write(*, '(A, I4, A, F10.6)') 'Epoch ', e, ' | Loss: ', epoch_loss
        end if
    end do

    write(*, *) 'Treinamento concluido!'

end program rnn_example
```

---

## 13. Exemplo: Previsao de Series Temporais

### 13.1 Configuracao do Problema

```text
Problema: Prever o proximo valor de uma serie temporal

Serie: seno com frequencia variavel + ruido
  x(t) = sin(0.5 * t) + 0.3 * sin(2.0 * t) + noise

Entrada: janela de 20 passos
Saida: proximo valor (quantizado em 10 bins)

Metrica: accuracy (acertou o bin correto) e MSE
```

### 13.2 Pipeline Completo

```text
Pipeline de Treinamento:

1. Geracao de dados:
   - 1000 sequencias de comprimento 20
   - 80% treino, 20% teste

2. Preprocessamento:
   - Normalizar para [-1, 1]
   - Quantizar saida em 10 bins

3. Treinamento:
   - Hidden size: 64
   - Learning rate: 0.005
   - Epochs: 200
   - Gradient clipping: 5.0

4. Avaliacao:
   - Loss: cross-entropy
   - Metrica: accuracy no conjunto de teste
   - Visualizar previsoes vs valores reais
```

### 13.3 Resultados Esperados

```text
Resultados esperados (RNN basica):

Epoch 0:   Loss: 2.302, Accuracy: 10% (aleatorio)
Epoch 10:  Loss: 2.150, Accuracy: 15%
Epoch 50:  Loss: 1.800, Accuracy: 25%
Epoch 100: Loss: 1.450, Accuracy: 40%
Epoch 200: Loss: 1.200, Accuracy: 55%

Nota: RNN basica TEM LIMITACOES para series longas.
- Vanishing gradient impede aprendizado de padroes de longo prazo
- Acuracia plateau around 50-60%
- LSTM/GRU podem atingir 70-80% na mesma tarefa
```

---

## 14. Analise de Gradientes

### 14.1 Monitoramento durante Treinamento

```text
Por que monitorar gradientes:

1. Diagnosticar vanishing gradient:
   - Se a norma do gradiente diminui drasticamente
   - Se W_hh para de atualizar
   - Se a loss para de diminuir

2. Diagnosticar exploding gradient:
   - Se a norma do gradiente cresce exponencialmente
   - Se os pesos mudam drasticamente
   - Se a loss pula ou diverge

3. Avaliar qualidade do treinamento:
   - Gradientes saudaveis: norma entre 0.01 e 10
   - Gradient clipping efetivo: norma nao excede max_norm
   - Taxa de aprendizado adequada: updates nao sao muito grandes nem muito pequenos
```

### 14.2 Codigos de Monitoramento

```cpp
// Monitoramento de gradientes em C++

struct GradientMonitor {
    std::vector<double> norms;

    void record(const RNNGrads& grads) {
        double total_norm = 0.0;
        for (const auto& row : grads.dW_xh)
            for (double g : row) total_norm += g * g;
        for (const auto& row : grads.dW_hh)
            for (double g : row) total_norm += g * g;
        for (const auto& row : grads.dW_hy)
            for (double g : row) total_norm += g * g;
        for (double g : grads.db_h) total_norm += g * g;
        for (double g : grads.db_y) total_norm += g * g;
        norms.push_back(std::sqrt(total_norm));
    }

    void report() const {
        if (norms.empty()) return;

        double min_norm = *std::min_element(norms.begin(), norms.end());
        double max_norm = *std::max_element(norms.begin(), norms.end());
        double avg_norm = std::accumulate(norms.begin(), norms.end(), 0.0) / norms.size();

        std::cout << "Gradient Norms:" << std::endl;
        std::cout << "  Min: " << min_norm << std::endl;
        std::cout << "  Max: " << max_norm << std::endl;
        std::cout << "  Avg: " << avg_norm << std::endl;

        if (min_norm < 1e-7) {
            std::cout << "  WARNING: Vanishing gradient detected!" << std::endl;
        }
        if (max_norm > 100.0) {
            std::cout << "  WARNING: Exploding gradient detected!" << std::endl;
        }
    }
};
```

### 14.3 Analise da Matriz W_hh

```text
Analise dos Autovalores de W_hh:

A estabilidade do hidden state depende dos autovalores
da matriz W_hh:

Se todos |lambda_i| < 1:
  O hidden state encolhe ao longo do tempo
  Vanishing gradient inevitavel

Se todos |lambda_i| > 1:
  O hidden state cresce ao longo do tempo
  Exploding gradient inevitavel

Se todos |lambda_i| ~= 1:
  Estavel! O hidden state mantem magnitude constante
  Gradientes fluem bem

Solucao: Inicializacao ortogonal para W_hh
  - Autovalores no circulo unitario
  - Estabilidade maxima
  - Implementacao: W = U * V^T onde U, V sao ortogonais
```

### 14.4 Visualizacao de Gradientes

```text
Tipos de Visualizacao:

1. Curva de gradientes ao longo dos epochs:
   Epoch | Norma do Gradiente
   0     | 5.23
   10    | 3.45
   20    | 2.12
   50    | 0.89
   100   | 0.34  (possivel vanishing)
   200   | 0.12  (vanishing confirmado)

2. Gradiente por passo temporal:
   t=1:  0.45
   t=2:  0.38
   t=3:  0.32
   t=5:  0.21
   t=10: 0.08  (diminuindo - vanishing)
   t=20: 0.01  (praticamente zero)

3. Heatmap de gradientes:
   Eixo X: passo temporal (t=1 a t=T)
   Eixo Y: neuronios (h_1 a h_d)
   Cor: magnitude do gradiente
   - Azul escuro: gradiente proximo de zero (vanishing)
   - Vermelho: gradiente grande (exploding)
   - Verde: gradiente saudavel
```

---

## 15. Resumo e Proximos Passos

### 15.1 Conceitos Fundamentais

```text
Resumo do Capitulo:

1. Dados sequenciais requerem arquiteturas que processam
   informacao temporal

2. RNNs mantem um hidden state que resume a historia
   da sequencia

3. Unrolling revela a RNN como uma rede feed-forward
   compartilhada

4. BPTT e o algoritmo de treinamento, com truncamento
   para sequencias longas

5. Vanishing gradient impede aprendizado de longo prazo
   - Gradientes desaparecem exponencialmente

6. Exploding gradient causa instabilidade
   - Resolvido por gradient clipping

7. Bidirectional RNN captura contexto passado e futuro

8. Seq2Seq comprime sequencias em vetores de contexto
```

### 15.2 Limitacoes da RNN Basica

```text
Limitacoes que serao enderecadas:

1. Vanishing Gradient -> LSTM, GRU (proximos capitulos)
2. Contexto fixo -> Attention (capitulo 13)
3. Sequencia longa -> Transformers (capitulo 14)
4. Paralelizacao -> Transformers (GPU-friendly)
```

### 15.3 Proximo Capitulo

No proximo capitulo, veremos como o GRU (Gated Recurrent Unit) resolve o problema de vanishing gradient usando portoes de reset e update — uma solucao mais simples e eficiente que LSTM, mantendo a maioria das vantagens.

```text
Dependencias para o proximo capitulo:
- Compreender BPTT (este capitulo)
- Compreender vanishing gradient (este capitulo)
- Operacoes matriciais basicas (capitulo 2)
- Funcoes de ativacao (capitulo 3)
```

---

## 16. Deep Dive: Analise Matematica

### 16.1 Algebra por Tras da RNN

A RNN e fundamentalmente uma operacao algebrica iterada. Vamos analisar cada componente em detalhe.

```text
Algebra da RNN:

Para cada passo t, temos:
  z_t = W_xh * x_t + W_hh * h_{t-1} + b_h  (pre-ativacao)
  h_t = tanh(z_t)                            (ativacao)

A saida:
  y_t = softmax(W_hy * h_t + b_y)

Expandindo h_T em funcao de todas as entradas:
  h_T = tanh(W_xh * x_T + W_hh * tanh(W_xh * x_{T-1} + W_hh * tanh(...)))

Cada tanh contem a proxima camada.
Isso cria uma "pilha" de funcoes compostas.
```

### 16.2 Analise de Sensibilidade

```text
Sensibilidade a Perturbacoes:

Se mudarmos x_1 por epsilon, como muda h_T?

dh_T/dx_1 = dh_T/dh_{T-1} * dh_{T-1}/dh_{T-2} * ... * dh_1/dx_1

Cada termo dh_t/dh_{t-1} = W_hh * diag(1 - h_t^2)

Se todos os autovalores de W_hh sao menores que 1:
  ||dh_T/dx_1|| <= (lambda_max)^T * C
  
onde lambda_max e o maior autovalor de W_hh
e C e uma constante.

Para T > 20 e lambda_max < 1:
  ||dh_T/dx_1|| ~ 0  (praticamente insensivel)

Implicacao: A RNN NAO pode aprender dependencias
de mais de ~20 passos.
```

### 16.3 Analise de Capacidade

```text
Capacidade de Memoria da RNN:

O hidden state h_t e um vetor de d_h dimensoes.
Cada dimensao pode armazenar 1 "bit" de informacao
(aproximadamente, considerando precisao numerica).

Total de informacao armazenavel: ~d_h bits

Para d_h = 256:
  Memoria: ~256 bits = 32 bytes
  Palavras de 300 dimensoes: ~0.1 bytes por palavra
  Capacidade teorica: ~320 palavras

Na pratica:
  - Ruido reduz capacidade efetiva
  - Vanishing gradient reduz memoria util
  - Capacidade real: ~10-50 palavras

Para sequencias longas:
  - RNN: inadequada (memoria insuficiente)
  - LSTM: melhor (cell state dedicado)
  - Attention: ideal (acesso direto a toda a sequencia)
```

### 16.4 Inicializacao Ortogonal

```text
Inicializacao Ortogonal para W_hh:

Objetivo: manter a magnitude do hidden state estavel
ao longo do tempo.

Metodo:
  W_hh = U * V^T
  
onde U e V sao matrizes ortogonais.

Propriedades:
  - Todos os autovalores tem modulo = 1
  - ||W_hh * h|| ~= ||h|| (preserva magnitude)
  - Gradientes nao sao atenuados nem amplificados

Implementacao:
  1. Gerar W_hh aleatoriamente
  2. Decompor em SVD: W = U * S * V^T
  3. Manter apenas U e V: W_hh = U * V^T

Resultado:
  - Vanishing gradient: mitiga (nao resolve completamente)
  - Exploding gradient: resolvido
  - Treinamento: mais estavel e mais rapido
```

---

## 17. Tecnicas Avancadas

### 17.1 Dropout em RNNs

```text
Dropout em RNNs: Onde Aplicar?

Dropout padrao (entre camadas):
  Nao funciona bem em RNNs
  Quebra a dependencia temporal

Dropout entre time steps:
  Aplicar nas CONEXOES temporais (W_hh)
  Mantem a dependencia dentro de um passo
  Quebra entre passos (regularizacao temporal)

Dropout no hidden state:
  Aplicar em h_t antes de passar ao proximo passo
  Mais comum e mais efetivo

Implementacao:
  h_t = tanh(W_xh * x_t + W_hh * h_{t-1} + b_h)
  h_t_drop = h_t * mask  (mask ~ Bernoulli(p))
  h_t_drop = h_t_drop / (1 - p)  (inverted dropout)
```

### 17.2 Learning Rate Scheduling

```text
Agendamento de Learning Rate para RNNs:

Problema: RNNs sao muito sensiveis ao learning rate.
- LR muito alto: gradientes explodem, treinamento instavel
- LR muito baixo: convergencia extremamente lenta

Estrategias:

1. Warmup:
   - Comecar com LR pequeno (0.0001)
   - Aumentar gradualmente por N steps
   - Depois diminuir

2. Cosine Annealing:
   - LR segue curva coseno
   - Suave e previsivel
   - Bom para convergencia

3. Reduce on Plateau:
   - Monitorar loss na validacao
   - Se nao melhora por K epochs, reduzir LR por fator
   - Exemplo: lr = lr * 0.5 apos 10 epochs sem melhoria

4. Cyclical:
   - LR oscila entre min e max
   - Escapa de minimos locais
   - Mais agressivo
```

### 17.3 Batch Processing em RNNs

```text
Processamento em Batches:

Sequencias de comprimento variavel:
  - Pad sequencias para o mesmo comprimento
  - Usar mascara para ignorar pads na loss
  - Mais eficiente em GPUs

Mascara (mask):
  Sequencia: [A, B, C, PAD, PAD]
  Mask:      [1,  1,  1,  0,   0]
  
  Loss = sum(loss_t * mask_t) / sum(mask_t)
  
  Apenas os passos reais contribuem para a loss.

Implementacao:
  // Durante forward
  if (mask[t] == 0) {
      // Ignorar este passo
      h_t = h_{t-1}  // manter hidden state anterior
      loss_t = 0
  } else {
      // Processar normalmente
      h_t = rnn_step(x_t, h_{t-1})
      loss_t = cross_entropy(y_t, target_t)
  }
```

### 17.4 Teacher Forcing

```text
Teacher Forcing: Treinamento com Saida Real

Problema:
  Durante treinamento, a RNN usa a SAIDA CORRETA
  como proxima entrada (teacher forcing).
  
  Mas durante inferencia, usa a SUA PROPRA SAIDA
  (que pode ser errada).

  Isso causa "exposure bias" — a rede nunca viu
  erros durante treinamento.

Solucoes:

1. Scheduled Sampling:
   - Com probabilidade p, usar saida real (teacher)
   - Com probabilidade 1-p, usar saida da rede
   - p diminui ao longo do treinamento
   - Comeca com teacher forcing puro
   - Termina com auto-regressivo puro

2. Professor Forcing:
   - Treinar discriminador para distinguir
     saidas de teacher vs modelo
   - Forca o modelo a gerar sequencias "realistas"

3. Data Augmentation:
   - Introduzir ruido nas entradas
   - Dropout no hidden state
   - Forca robustez
```

---

## 18. Casos de Uso Detalhados

### 18.1 Language Model

```text
Language Model com RNN:

Tarefa: Prever a proxima palavra

Arquitetura:
  Embedding(vocab, d_emb) -> RNN(d_emb, d_hidden) -> Dense(d_hidden, vocab)

Treinamento:
  - Input: "O gato sentou no"
  - Target: "tapete"
  - Loss: cross-entropy entre previsao e palavra real

Inferencia:
  - Input: "O gato"
  - Gerar: "sentou" -> "no" -> "tapete" -> ...
  - Sampling: escolher proxima palavra com probabilidade

Metricas:
  - Perplexity: exp(loss)
  - Quanto menor, melhor o modelo
  - Perplexity 100 = incerteza de 100 palavras
```

### 18.2 Music Generation

```text
Geracao de Musica com RNN:

Representacao:
  - Notas como one-hot (C, D, E, F, G, A, B + oitavas)
  - Ou MIDI events (note_on, note_off, velocity)
  - Ou pianoroll (matriz tempo x nota)

Arquitetura:
  - Input: nota atual
  - RNN: hidden_size = 256-512
  - Output: proxima nota (distribuicao de probabilidade)

Treinamento:
  - Dataset: MIDI files de musicas
  - Sequencias de 100-200 notas
  - Loss: cross-entropy em cada passo

Geracao:
  - Comecar com nota aleatoria
  - Gerar proxima nota com sampling
  - Temperature: controla aleatoriedade
    - T = 0.5: mais conservador
    - T = 1.0: mais criativo
    - T = 2.0: muito aleatorio
```

### 18.3 Time Series Forecasting

```text
Previsao de Series Temporais:

Tipos:
  1. Univariate: apenas valores ao longo do tempo
  2. Multivariate: multiplas variaveis correlacionadas

Arquitetura:
  - Input: janela de N passos
  - RNN: processa sequencia
  - Output: proximo valor ou K valores futuros

Features de engenharia:
  - Media movel
  - Desvio padrao movel
  - Diferencas (trend)
  - Sazonalidade

Avaliacao:
  - MAE: erro absoluto medio
  - RMSE: raiz do erro quadratico medio
  - MAPE: erro percentual absoluto medio
  - Sharpe ratio (para financas)
```

### 18.4 Speech Recognition

```text
Reconhecimento de Fala com RNN:

Pipeline:
  1. Audio -> Features (MFCC, spectrogram)
  2. Features -> RNN (processamento temporal)
  3. RNN -> CTC decode -> Texto

Arquitetura:
  - Input: MFCC features (13-40 coefficients por frame)
  - RNN: multiplas camadas
  - Output: probabilidade por caractere/phonema

CTC (Connectionist Temporal Classification):
  - Permite alinhamento automatico
  - Nao precisa de alinhamento frame-a-frame
  - Lida com variacao de velocidade de fala

Desafios:
  - Ruido ambiente
  - Variacao de说话人
  - Acentos e dialectos
```

---

## 19. Debugging e Diagnostico

### 19.1 Problemas Comuns

```text
Problema 1: Loss nao diminui
  Causas:
  - Learning rate muito alto ou muito baixo
  - Pesos inicializados incorretamente
  - Erro na implementacao do backward pass
  
  Diagnostico:
  - Verificar gradientes manualmente
  - Testar com dados pequenos (overfit um batch)
  - Comparar com implementacao de referencia

Problema 2: Loss explode (NaN)
  Causas:
  - Exploding gradient
  - Learning rate muito alto
  - Operacao numerica instavel (log(0))
  
  Diagnostico:
  - Monitorar norma do gradiente
  - Verificar valores de hidden state
  - Adicionar epsilon em operacoes divisiveis

Problema 3: Treinamento lento
  Causas:
  - Learning rate muito baixo
  - Arquitetura muito grande
  - Dados muito grandes (batch size pequeno)
  
  Diagnostico:
  - Aumentar learning rate
  - Reduzir tamanho do hidden state
  - Aumentar batch size
```

### 19.2 Ferramentas de Diagnostico

```text
Ferramentas:

1. Gradient Checking:
   - Calcular gradiente numerico
   - Comparar com gradiente analitico
   - Diferenca deve ser < 1e-6

2. Activation Statistics:
   - Monitorar media e variancia de h_t
   - Se media -> 0 e var -> 0: dying RNN
   - Se media -> inf ou NaN: exploding

3. Gate Statistics:
   - Monitorar valores de gates
   - Se gate ~= 0.5 sempre: nao esta aprendendo
   - Se gate ~= 0 ou 1 sempre: pode estar saturado

4. Loss Curve:
   - Loss deve diminuir suavemente
   - Se oscila: learning rate alto demais
   - Se estagnou: learning rate baixo ou capacity baixa
```

### 19.3 Unit Testing

```text
Unit Tests para RNN:

1. Teste de Forward Pass:
   - Entrada conhecida -> saida esperada
   - Verificar dimensoes
   - Verificar valores em range esperado

2. Teste de Backward Pass:
   - Gradient checking numerico
   - Verificar que gradientes nao sao zero
   - Verificar que gradientes nao sao NaN

3. Teste de Overfitting:
   - Treinar em 10 exemplos por 1000 epochs
   - Loss deve ir a zero
   - Accuracy deve ir a 100%

4. Teste de Dimensionalidade:
   - Verificar shapes de todas as matrizes
   - Verificar compatibilidade de dimensoes
   - Testar com tamanhos variados
```

---

## 20. Referencias Avancadas

### 20.1 Historia das RNNs

```text
Linha do Tempo das RNNs:

1986: Rumelhart, Hinton, Williams
  - Backpropagation publicado
  
1990: Elman
  - Elman Network (RNN basica)
  - Primeira RNN funcional

1997: Hochreiter & Schmidhuber
  - LSTM proposto
  - Resolve vanishing gradient

2005: Graves
  - LSTM com backpropagation through time
  - Primeira implementacao pratica

2010: Mikolov
  - RNNs para language models
  - Demonstrou eficacia em NLP

2013: Sutskever
  - LSTM para machine translation
  - Seq2Seq proposto

2014: Cho
  - GRU proposto
  - Alternativa mais simples ao LSTM

2015: Bahdanau
  - Attention mechanism
  - Resolve bottleneck do Seq2Seq

2017: Vaswani
  - Transformer
  - Attention is All You Need
  - RNNs comecam a ser substituidas

2020+: Transformers dominam
  - GPT, BERT, T5
  - RNNs usadas apenas em nichos
```

### 20.2 Leituras Recomendadas

```text
Livros:
1. "Deep Learning" - Goodfellow, Bengio, Courville (Cap. 10)
2. "Neural Network Methods for NLP" - Goldberg
3. "Sequence to Sequence Learning" - diverse papers

Papers Fundamentais:
1. "Learning to Forget" - Gers et al. (2000)
2. "LSTM: A Search Space Odyssey" - Greff et al. (2017)
3. "On the Difficulty of Training RNNs" - Pascanu et al. (2013)

Tutoriais:
1. colah's blog: "Understanding LSTM Networks"
2. Michael Phi: "Illustrated Guide to LSTM"
3. Stanford CS224n: NLP with Deep Learning
```

---

## Exercicios

### Exercicio 1: Analise de Capacidade

Uma RNN com hidden_size=64 e input_size=10. Calcule:
a) Numero total de parametros
b) Tamanho do hidden state em bytes (float64)
c) Quantos passos temporais antes do vanishing gradient (estimativa)

### Exercicio 2: Implementacao Manual

Implemente o forward pass de uma RNN a mao para:
- Input: [0.5, -0.3]
- Hidden size: 4
- Pesos W_xh: 4x2, W_hh: 4x4 (use valores especificos)
- Calcule h_1, h_2, h_3 manualmente

### Exercicio 3: Gradiente Manual

Para a rede do Exercicio 2, calcule o gradiente de W_hh em t=2
usando BPTT. Mostre cada passo da regra da cadeia.

### Exercicio 4: Explorando Hidden Size

Teste a RNN implementada com hidden_sizes: 16, 32, 64, 128, 256.
Qual produz melhor resultado? Qual e mais estavel?
Explique o tradeoff.

### Exercicio 5: Vanishing Gradient

Implemente um script que:
1. Treina uma RNN em uma sequencia de comprimento 100
2. Monitora a norma do gradiente por passo temporal
3. Plota a curva de gradiente vs passo temporal
4. Identifica a partir de qual passo o gradiente < 0.01

### Exercicio 6: Comparacao de Arquiteturas

Compare tres formatos de RNN:
a) Many-to-many (previsao em cada passo)
b) Many-to-one (classificacao no final)
c) Encoder-decoder (seq2seq)

Para cada um:
- Desenhe a arquitetura unrolled
- Identifique onde as saidas sao usadas
- Calcule o numero de parametros
- Discuta quais tarefas se encaixam melhor

---

## Referencias

1. Elman, J. L. (1990). Finding structure in time. *Cognitive Science*, 14(2), 179-211.

2. Werbos, P. J. (1990). Backpropagation through time: what it does and how to do it. *Proceedings of the IEEE*, 78(10), 1550-1560.

3. Hochreiter, S., & Schmidhuber, J. (1997). Long short-term memory. *Neural Computation*, 9(8), 1735-1780.

4. Cho, K., et al. (2014). Learning phrase representations using RNN encoder-decoder for statistical machine translation. *arXiv preprint arXiv:1406.1078*.

5. Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training recurrent neural networks. *ICML 2013*.

6. Sutskever, I., Vinyals, O., & Le, Q. V. (2014). Sequence to sequence learning with neural networks. *NIPS 2014*.

7. Schuster, M., & Paliwal, K. K. (1997). Bidirectional recurrent neural networks. *IEEE Transactions on Signal Processing*, 45(11), 2673-2681.

8. Mikolov, T., et al. (2010). Recurrent neural network based language model. *INTERSPEECH 2010*.

9. Graves, A. (2013). Generating sequences with recurrent neural networks. *arXiv preprint arXiv:1308.0850*.

10. Goodfellow, I., Bengio, Y., & Courville, A. (2016). *Deep Learning*. MIT Press. Chapter 10: Sequence Modeling: Recurrent and Recursive Nets.
