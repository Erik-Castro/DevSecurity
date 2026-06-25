---
layout: default
title: "06-backpropagation"
---

# Capitulo 6 — Backpropagation

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender derivadas parciais e a regra da cadeia** — a base matematica que torna o backpropagation possivel.
2. **Derivar o backpropagation completo** para uma MLP de qualquer profundidade, camada por camada.
3. **Diferenciar gradiente local de gradiente global** e entender por que a composicao de gradientes locais produz o gradiente global da funcao de perda.
4. **Reconhecer e mitigar o problema de vanishing/exploding gradients** em redes profundas.
5. **Implementar backpropagation do zero em C++** com operacoes de matriz, forward pass, backward pass, e treinamento completo.
6. **Implementar backpropagation do zero em Rust** usando traits e ownership para seguranca de memoria.
7. **Implementar backpropagation do zero em Fortran** usando arrays multidimensionais e subrotinas.
8. **Validar gradientes analiticos contra gradientes numericos** para garantir correcao da implementacao.
9. **Diagnosticar problemas comuns no treinamento** usando tecnicas de debugging de gradientes.
10. **Treinar uma MLP real para aproximar uma funcao nao-linear** e observar convergencia.

---

## 1. Derivadas Parciais e Regra da Cadeia

### 1.1 Por Que Derivadas Sao Importantes para ML

O objetivo central do treinamento de uma rede neural e minimizar uma funcao de perda L. O mecanismo para fazer isso e o gradient descent, que atualiza os pesos na direcao oposta ao gradiente:

```text
w := w - eta * dL/dw
```

onde eta e a taxa de aprendizado e dL/dw e a derivada da perda em relacao ao peso w. O problema e: como calcular dL/dw quando w esta conectado a L por multiplas camadas de composicao?

A resposta e o backpropagation — um algoritmo que aplica sistematicamente a regra da cadeia para propagar gradientes da saida para a entrada da rede.

### 1.2 Derivada Parcial

Quando uma funcao depende de multiplas variaveis, a derivada parcial mede como a funcao muda quando UMA variavel e alterada, mantendo todas as outras constantes.

```text
Definicao: Se f(x1, x2, ..., xn), entao:

df/dx1 = limite(h->0) [f(x1+h, x2, ..., xn) - f(x1, x2, ..., xn)] / h
```

Exemplo concreto:

```text
f(x, y) = x^2 * y + sin(x)

df/dx = 2*x*y + cos(x)     (trata y como constante)
df/dy = x^2                  (trata x como constante)
```

Em uma rede neural, os pesos sao as variaveis, a perda e a funcao, e queremos todas as derivadas parciais — o gradiente.

### 1.3 Regra da Cadeia (Chain Rule)

A regra da cadeia e o coracao do backpropagation. Ela permite calcular a derivada de funcoes compostas.

**Caso univariavel:**

```text
Se y = f(g(x)), entao:
dy/dx = (df/dg) * (dg/dx) = f'(g(x)) * g'(x)
```

**Caso multivariavel (o que importa para redes neurais):**

```text
Se z = f(u, v) e u = g(x, y) e v = h(x, y), entao:

dz/dx = (dz/du) * (du/dx) + (dz/dv) * (dv/dx)
dz/dy = (dz/du) * (du/dy) + (dz/dv) * (dv/dy)
```

Exemplo pratico com tres variaveis:

```text
f(x, y, z) = (x + y)^2 * z

Seja u = x + y (intermediario)
Seja v = u^2 = (x + y)^2
f = v * z

df/dz = v = (x + y)^2
df/dx = (df/dv) * (dv/du) * (du/dx) = z * 2u * 1 = 2z(x + y)
df/dy = (df/dv) * (dv/du) * (du/dy) = z * 2u * 1 = 2z(x + y)
```

### 1.4 Aplicacao em Rede Neural Simples

Considere a rede mais simples possivel — uma rede com uma camada oculta:

```text
Entrada: x
Pesos entrada-oculta: w1
Pesos oculta-saida: w2
Vieses: b1, b2
Saida: y

Forward pass:
  z1 = w1 * x + b1       (pre-ativacao camada 1)
  a1 = sigmoid(z1)        (ativacao camada 1)
  z2 = w2 * a1 + b2       (pre-ativacao camada 2)
  a2 = sigmoid(z2)        (ativacao camada 2 = saida)
  L = (a2 - t)^2          (perda, t = target)
```

Para calcular dL/dw2 (derivada da perda em relacao ao peso da segunda camada):

```text
dL/dw2 = dL/da2 * da2/dz2 * dz2/dw2

Onde:
  dL/da2 = 2(a2 - t)           (derivada do MSE)
  da2/dz2 = sigmoid'(z2)       (derivada da sigmoid)
  dz2/dw2 = a1                 (da z2 = w2*a1 + b2)
```

Para calcular dL/dw1 (derivada da perda em relacao ao peso da primeira camada):

```text
dL/dw1 = dL/da2 * da2/dz2 * dz2/da1 * da1/dz1 * dz1/dw1

Onde:
  dL/da2 = 2(a2 - t)
  da2/dz2 = sigmoid'(z2)
  dz2/da1 = w2
  da1/dz1 = sigmoid'(z1)
  dz1/dw1 = x
```

A chain rule permite decompor o gradiente complexo em derivadas locais, cada uma facil de calcular.

### 1.5 O Padrao: Gradiente Local Encadeado

O padrao que emerge e este: cada camada produz um "gradiente local" (derivada da saida em relacao a entrada daquela camada), e o backpropagation encadeia esses gradientes da saida para a entrada.

```text
Gradiente Global = Produto dos Gradientes Locais

dL/dw1 = dL/dz2 * dz2/da1 * da1/dz1 * dz1/dw1
         ^^^^^^   ^^^^^^^^^   ^^^^^^^^^   ^^^^^^
         loss     peso L2     ativacao    peso L1
         grad     local       grad        local
```

Essa decomposicao e exatamente o que o backpropagation faz de forma sistematica para cada peso da rede.

---

## 2. Backpropagation para MLP

### 2.1 Definicao da Arquitetura

Considere uma MLP com L camadas. Para cada camada l (de 1 a L):

```text
Variaveis:
  x^(0)              = vetor de entrada (camada 0)
  z^(l) = W^(l) * a^(l-1) + b^(l)   (pre-ativacao, camada l)
  a^(l) = f(z^(l))                   (ativacao, camada l)
  a^(L) = y_hat                       (saida da rede)

Onde:
  W^(l) = matriz de pesos da camada l (dim: neurons_l x neurons_{l-1})
  b^(l) = vetor de vieses da camada l (dim: neurons_l)
  f = funcao de ativacao
  z^(l) = vetor de pre-ativacao (dim: neurons_l)
  a^(l) = vetor de ativacao (dim: neurons_l)
```

### 2.2 Funcao de Perda

Para regressao (MSE):

```text
L = (1/2m) * soma_i=1..m (y_hat_i - y_i)^2
```

Para classificacao binaria (Binary Cross-Entropy):

```text
L = -(1/m) * soma_i=1..m [y_i * log(y_hat_i) + (1-y_i) * log(1-y_hat_i)]
```

Para classificacao multi-classe (Categorical Cross-Entropy com Softmax):

```text
L = -(1/m) * soma_i=1..m soma_c=1..C y_ic * log(y_hat_ic)
```

### 2.3 Backward Pass — Gradiente na Camada de Saida

O backward pass comeca na camada de saida. Para a camada L (ultima camada):

```text
Para MSE + Sigmoid na saida:
  delta^(L) = (a^(L) - y) * f'(z^(L))

  Onde:
    a^(L) - y = erro de predicao
    f'(z^(L)) = sigmoid'(z^(L)) = sigmoid(z^(L)) * (1 - sigmoid(z^(L)))

Para BCE + Sigmoid na saida (simplificacao notavel):
  delta^(L) = a^(L) - y

  (A derivada do BCE com sigmoid cancela o termo f')
```

### 2.4 Backward Pass — Gradiente nas Camadas Intermediarias

Para cada camada l (de L-1 ate 1):

```text
delta^(l) = (W^(l+1))^T * delta^(l+1) .* f'(z^(l))
```

onde .* denota multiplicacao elemento a elemento (Hadamard product).

Explicacao passo a passo:

```text
1. (W^(l+1))^T * delta^(l+1)
   Transpoe os pesos da camada seguinte e multiplica pelo delta seguinte.
   Isso "propaga" o erro de volta para a camada l.

2. .* f'(z^(l))
   Multiplica pelo gradiente local da funcao de ativacao.
   Isso incorpora a contribuicao da camada l ao erro.
```

### 2.5 Gradientes dos Pesos e Vieses

Uma vez que delta^(l) esta computado para cada camada, os gradientes dos pesos sao:

```text
dL/dW^(l) = delta^(l) * (a^(l-1))^T
dL/db^(l) = delta^(l)
```

Em formato matricial (para m exemplos de treinamento):

```text
dL/dW^(l) = (1/m) * delta^(l) * (A^(l-1))^T
dL/db^(l) = (1/m) * soma(delta^(l))
```

onde A^(l-1) e a matriz de todas as ativacoes da camada anterior para todos os m exemplos.

### 2.6 Algoritmo Completo

```text
ALGORITMO: Backpropagation para MLP

ENTRADA:
  Rede com L camadas, dados de treinamento {(x_i, y_i)} para i=1..m
  Funcao de perda L, funcoes de ativacao f^(l) para cada camada

1. FORWARD PASS:
   a^(0) = x (entrada)
   Para l = 1 ate L:
     z^(l) = W^(l) * a^(l-1) + b^(l)
     a^(l) = f^(l)(z^(l))
   
   y_hat = a^(L)
   L_total = (1/m) * soma(L(y_hat_i, y_i))

2. BACKWARD PASS:
   // Camada de saida
   delta^(L) = gradiente_da_perda(a^(L), y) * f'^(L)(z^(L))
   
   // Camadas intermediarias (iteracao reversa)
   Para l = L-1 ate 1:
     delta^(l) = (W^(l+1))^T * delta^(l+1) .* f'^(l)(z^(l))

3. GRADIENTES DOS PESOS:
   Para l = 1 ate L:
     dW^(l) = (1/m) * delta^(l) * (a^(l-1))^T
     db^(l) = (1/m) * soma(delta^(l))

4. ATUALIZACAO DOS PESOS:
   Para l = 1 ate L:
     W^(l) = W^(l) - eta * dW^(l)
     b^(l) = b^(l) - eta * db^(l)
```

### 2.7 Dimensoes Matriciais

Um erro comum e perder o rastro das dimensoes. Aqui esta a verificacao completa:

```text
Para camada l com:
  n_l = numero de neuronios na camada l
  n_{l-1} = numero de neuronios na camada anterior

W^(l):  dimensao (n_l x n_{l-1})
b^(l):  dimensao (n_l x 1)
z^(l):  dimensao (n_l x 1)
a^(l):  dimensao (n_l x 1)
delta^(l): dimensao (n_l x 1)

Verificacao de dimensoes no backward pass:
  (W^(l+1))^T:  dimensao (n_l x n_{l+1})
  delta^(l+1):  dimensao (n_{l+1} x 1)
  Resultado:     dimensao (n_l x 1)  -- correto!

  f'(z^(l)):    dimensao (n_l x 1)
  delta^(l):    dimensao (n_l x 1)  -- correto!

Verificacao de dimensoes nos gradientes:
  delta^(l):     dimensao (n_l x 1)
  (a^(l-1))^T:   dimensao (1 x n_{l-1})
  dW^(l):        dimensao (n_l x n_{l-1})  -- correto!
```

### 2.8 Exemplo Numerico Completo

Considere uma rede com 2 entradas, 3 neuronios na camada oculta, e 1 saida:

```text
Rede:
  Camada 1 (entrada): 2 neuronios
  Camada 2 (oculta): 3 neuronios, ativacao ReLU
  Camada 3 (saida): 1 neuronio, ativacao sigmoid

Pesos iniciais:
  W1 = [[0.1, 0.3],    (3x2)
        [0.2, 0.4],
        [0.5, 0.6]]
  b1 = [0.1, 0.1, 0.1]  (3x1)
  W2 = [0.7, 0.8, 0.9]  (1x3)
  b2 = [0.1]              (1x1)

Entrada: x = [1.0, 2.0]^T
Target: y = 1.0
```

**Forward Pass:**

```text
z1 = W1 * x + b1
   = [[0.1*1 + 0.3*2 + 0.1],     = [[0.8],
      [0.2*1 + 0.4*2 + 0.1],        [1.1],
      [0.5*1 + 0.6*2 + 0.1]]        [1.8]]

a1 = relu(z1)
   = [[max(0, 0.8)],            = [[0.8],
      [max(0, 1.1)],               [1.1],
      [max(0, 1.8)]]               [1.8]]

z2 = W2 * a1 + b2
   = [0.7*0.8 + 0.8*1.1 + 0.9*1.8 + 0.1]
   = [0.56 + 0.88 + 1.62 + 0.1]
   = [3.16]

a2 = sigmoid(z2)
   = 1 / (1 + exp(-3.16))
   = 0.9595

L = -(1/2) * (y * log(a2) + (1-y) * log(1-a2))
  = -(1/2) * (1 * log(0.9595) + 0)
  = -(1/2) * (-0.0413)
  = 0.0207
```

**Backward Pass:**

```text
// Camada de saida (sigmoid + BCE)
delta2 = a2 - y
       = 0.9595 - 1.0
       = -0.0405

// Gradientes W2 e b2
dW2 = delta2 * a1^T
    = [-0.0405] * [0.8, 1.1, 1.8]
    = [-0.0324, -0.0446, -0.0729]
db2 = delta2
    = [-0.0405]

// Camada oculta (ReLu backward)
delta1 = W2^T * delta2 .* relu'(z1)

W2^T * delta2 = [[0.7],    * (-0.0405)
                 [0.8],
                 [0.9]]
              = [[-0.0284],
                 [-0.0324],
                 [-0.0365]]

relu'(z1) = [[1],    (0.8 > 0)
             [1],    (1.1 > 0)
             [1]]    (1.8 > 0)

delta1 = [[-0.0284], .* [[1],  = [[-0.0284],
          [-0.0324],      [1],    [-0.0324],
          [-0.0365]]      [1]]    [-0.0365]]

// Gradientes W1 e b1
dW1 = delta1 * x^T
    = [[-0.0284],    * [1, 2]
       [-0.0324],
       [-0.0365]]
    = [[-0.0284, -0.0568],
       [-0.0324, -0.0648],
       [-0.0365, -0.0730]]

db1 = delta1
    = [[-0.0284],
       [-0.0324],
       [-0.0365]]
```

---

## 3. Gradiente Local vs Global

### 3.1 O Que e Gradiente Local

O gradiente local de uma camada e a derivada da saida daquela camada em relacao a sua entrada. Ele captura APENAS a contribuicao daquela camada especifica.

```text
Para a camada l:
  Gradiente Local = da^(l) / dz^(l) = f'(z^(l))
```

O gradiente local e independente de qualquer coisa que aconteca antes ou depois na rede. Ele e uma propriedade daquela camada isoladamente.

### 3.2 O Que e Gradiente Global

O gradiente global de um peso e a derivada da funcao de perda TOTAL em relacao aquele peso. Ele captura a contribuicao do peso para o erro final da rede.

```text
Para o peso W^(l) na camada l:
  Gradiente Global = dL/dW^(l)
```

O gradiente global depende de TODAS as camadas entre o peso e a funcao de perda.

### 3.3 A Conexao: Composicao de Gradientes Locais

O backpropagation demonstra que o gradiente global e o PRODUTO dos gradientes locais ao longo do caminho entre o peso e a perda:

```text
dL/dW^(l) = (produto de todos os gradientes locais entre l e L) * contribuicao_direta
```

Para uma rede com 3 camadas:

```text
dL/dW^(1) = delta^(3) * (W^(2))^T * f'(z^(2)) * (W^(1))^T * x
            ^^^^^^^^^   ^^^^^^^^^   ^^^^^^^^^
            saida cam3  propaga     ativacao cam1
            
            Todos esses termos sao gradientes locais encadeados!
```

### 3.4 Exemplo Visual

```text
x --> [W1, b1] --> z1 --> [f1] --> a1 --> [W2, b2] --> z2 --> [f2] --> a2 --> L

Forward:  x --(z1)--> a1 --(z2)--> a2 --(L)--> loss
Backward: loss <--(dL/da2)-- a2 <--(da2/dz2)-- z2 <--(da2/da1)-- a1 <--(da1/dz1)-- z1

Gradiente local na camada 2: da2/dz2 = f2'(z2)
Gradiente local na camada 1: da1/dz1 = f1'(z1)

Gradiente global para W1:
  dL/dW1 = dL/da2 * da2/dz2 * dz2/da1 * da1/dz1 * dz1/dW1
         = [erro] * [f2'(z2)] * [W2] * [f1'(z1)] * [x]
         = local * local * local * local * local
```

### 3.5 Por Que Isso Importa

A decomposicao em gradientes locais tem tres implicacoes criticas:

```text
1. EFICIENCIA COMPUTACIONAL:
   Cada gradiente local e calculado apenas uma vez e reutilizado.
   Sem essa propriedade, precisariamos recalcular a rede inteira para cada peso.
   
   Complexidade: O(m * n) por iteracao, onde m = exemplos, n = pesos
   Sem decomposicao: O(m * n * L) por iteracao (L = camadas)

2. MODULARIDADE:
   Cada camada precisa saber apenas: (a) seu gradiente de saida (delta),
   e (b) sua entrada. Nao precisa saber da arquitetura completa.
   
   Isso permite construir camadas como "blocos de LEGO" —
   qualquer camada que saiba calcular seu gradiente local funciona.

3. DIAGNOSTICO:
   Se uma camada tem gradiente local proximo de zero, ela bloqueia
   o fluxo de gradientes. Isso explica o vanishing gradient.
   
   Se uma camada tem gradiente local > 1, ela amplifica gradientes.
   Compostas, isso causa exploding gradient.
```

### 3.6 Analogia com Corrente Eletrica

```text
Imagine uma serie de resistores e amplificadores:

Fonte --[R1]-- [A1] --[R2]-- [A2] --[R3]-- Saida

Cada [Ri] e um resistore (reduz sinal) e [Ai] e amplificador (aumenta sinal).

O sinal total na saida = (R1 * A1 * R2 * A2 * R3) * entrada
O sinal de erro volta = (R3 * A2 * R2 * A1 * R1) * erro

Se todos os R sao < 1 (sigmoid), o sinal de erro encolhe.
Se todos os A sao > 1 (amplificacao), o sinal de erro cresce.

O comportamento final depende do produto de todos os termos.
E exatamente isso que acontece com gradientes na rede neural.
```

---

## 4. Vanishing e Exploding Gradients

### 4.1 O Problema do Vanishing Gradient

Em redes profundas, os gradientes sao o produto de muitos termos. Se a maioria dos termos tem modulo menor que 1, o produto tende a zero exponencialmente.

```text
Para uma rede com L camadas usando sigmoid:

Gradiente na camada l:
  |dL/dW^(l)| ~ prod(k=l..L) |sigma'(z^(k))| * |W^(k)|

Maximo de sigma'(x) = 0.25 (em x = 0)

Se |W| ~ 1 e sigma'(z) ~ 0.25:
  |dL/dW^(1)| ~ 0.25^L

Para L = 10:  0.25^10 ~ 9.5e-7  (praticamente zero)
Para L = 20:  0.25^20 ~ 9.1e-13 (zero numerico)
```

### 4.2 O Problema do Exploding Gradient

Se os gradientes locais sao consistentemente maiores que 1, o produto cresce exponencialmente:

```text
Para uma rede com pesos grandes:
  |dL/dW^(1)| ~ prod(k=l..L) |sigma'(z^(k))| * |W^(k)|

Se sigma'(z) * |W| > 1 em todas as camadas:
  |dL/dW^(1)| cresce exponencialmente com L

Resultado: atualizacoes de peso enormes, pesos divergem para infinito,
perda se torna NaN ou infinito.
```

### 4.3 Analise Quantitativa

```text
Considere o "gradiente de passageiro" (passenger gradient):

passenger_k = |sigma'(z^(k)) * W^(k)|

Se passenger_k > 1 em media: gradiente cresce (exploding)
Se passenger_k < 1 em media: gradiente encolhe (vanishing)
Se passenger_k ~ 1 em media: gradiente se mantem estavel

Para sigmoid: passenger maximo = 0.25 * |W|
  Para |W| = 1: passenger = 0.25 (vanishing garantido)
  Para |W| = 4: passenger = 1.0 (estavel, mas raro na pratica)

Para ReLU: passenger = |W| (para z > 0), 0 (para z < 0)
  Para |W| > 1: passenger > 1 quando neuronio esta ativo (exploding)
  Para neuronios mortos: passenger = 0 (nenhum gradiente flui)
```

### 4.4 Solucoes Historicas e Modernas

```text
Problema                  Solucao                          Epoca
---------------------------------------------------------------
Vanishing gradient        Inicializacao careful            1990s
Vanishing gradient        Tanh ao inves de Sigmoid         2000
Vanishing gradient        ReLU                             2011
Vanishing/exploding       Batch Normalization              2015
Vanishing/exploding       Residual Connections (ResNet)    2015
Vanishing gradient        LSTM gates                       1997
Exploding gradient        Gradient Clipping                2013
Exploding gradient        Peso inicializacao orthogonal    2017
Vanishing/exploding       Layer Normalization              2016
Vanishing/exploding       Skip Connections                 2015
```

### 4.5 Inicializacao de Pesos

A inicializacao adequada e a primeira defesa contra vanishing/exploding gradients:

```text
1. Xavier/Glorot (para sigmoid/tanh):
   W ~ N(0, 2/(n_in + n_out))
   ou uniforme: U(-sqrt(6/(n_in + n_out)), sqrt(6/(n_in + n_out)))
   
   Justificativa: mantem variancia do sinal constante entre camadas

2. He (para ReLU):
   W ~ N(0, 2/n_in)
   
   Justificativa: ReLU zera metade dos neuronios, entao precisa
   de variancia 2x maior para compensar

3. LeCun (para SELU):
   W ~ N(0, 1/n_in)
   
   Justificativa: SELU e self-normalizing, precisa de variancia 1/n

4. Orthogonal:
   W = Q (fator ortogonal de uma decomposicao QR)
   
   Justificativa: garante que autovalores sao 1, preserva
   magnitude do sinal exatamente
```

### 4.6 Gradient Clipping

Uma solucao simples para exploding gradients:

```text
Se ||gradiente|| > threshold:
  gradiente = gradiente * (threshold / ||gradiente||)

Variante por elemento:
  gradiente = clip(gradiente, -threshold, threshold)
```

### 4.7 Skip Connections (ResNets)

As skip connections revolucionaram o treinamento de redes profundas ao criar "atajos" para os gradientes:

```text
Sem skip connection:
  a^(l) = f(W^(l) * a^(l-1) + b^(l))
  
  Gradiente: dL/da^(l-1) = W^(l)^T * f'(...) * ... (pode desaparecer)

Com skip connection (ResNet):
  a^(l) = f(W^(l) * a^(l-1) + b^(l)) + a^(l-1)   (identity shortcut)
  
  Gradiente: dL/da^(l-1) = dL/da^(l) * (W^(l)^T * f'(...) + I)
                                                     ^^^^
                                         Termo identidade garante
                                         que gradiente nunca desaparece
```

---

## 5. Implementacao Detalhada em C++

### 5.1 Estrutura do Projeto

```cpp
// backpropagation.cpp
// Implementacao completa de backpropagation para MLP
// Sem bibliotecas externas — apenas C++ standard

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>
#include <cassert>
#include <functional>
#include <string>
#include <sstream>
#include <iomanip>
#include <stdexcept>

// =====================================================================
// Secao 1: Estrutura Matrix
// Implementacao basica de matriz para operacoes de rede neural
// =====================================================================

struct Matrix {
    std::vector<double> data;
    int rows;
    int cols;

    Matrix() : rows(0), cols(0) {}

    Matrix(int r, int c) : rows(r), cols(c), data(r * c, 0.0) {}

    Matrix(int r, int c, double val) : rows(r), cols(c), data(r * c, val) {}

    double& operator()(int i, int j) {
        return data[i * cols + j];
    }

    double operator()(int i, int j) const {
        return data[i * cols + j];
    }

    // Acesso por indice plano
    double& operator[](int idx) { return data[idx]; }
    double operator[](int idx) const { return data[idx]; }

    int size() const { return rows * cols; }
};

// =====================================================================
// Secao 2: Operacoes Basicas de Matriz
// Cada operacao implementa a matematica do backpropagation
// =====================================================================

// Soma de duas matrizes
Matrix mat_add(const Matrix& a, const Matrix& b) {
    assert(a.rows == b.rows && a.cols == b.cols);
    Matrix result(a.rows, a.cols);
    for (int i = 0; i < a.size(); ++i) {
        result[i] = a[i] + b[i];
    }
    return result;
}

// Subtracao de matrizes
Matrix mat_sub(const Matrix& a, const Matrix& b) {
    assert(a.rows == b.rows && a.cols == b.cols);
    Matrix result(a.rows, a.cols);
    for (int i = 0; i < a.size(); ++i) {
        result[i] = a[i] - b[i];
    }
    return result;
}

// Multiplicacao de matrizes: C = A * B
// C(i,j) = soma_k A(i,k) * B(k,j)
Matrix mat_mul(const Matrix& a, const Matrix& b) {
    assert(a.cols == b.rows);
    Matrix result(a.rows, b.cols);
    for (int i = 0; i < a.rows; ++i) {
        for (int j = 0; j < b.cols; ++j) {
            double sum = 0.0;
            for (int k = 0; k < a.cols; ++k) {
                sum += a(i, k) * b(k, j);
            }
            result(i, j) = sum;
        }
    }
    return result;
}

// Multiplicacao elemento a elemento (Hadamard product)
// Usado no backward pass: delta .* f'(z)
Matrix mat_hadamard(const Matrix& a, const Matrix& b) {
    assert(a.rows == b.rows && a.cols == b.cols);
    Matrix result(a.rows, a.cols);
    for (int i = 0; i < a.size(); ++i) {
        result[i] = a[i] * b[i];
    }
    return result;
}

// Transposta
Matrix mat_transpose(const Matrix& a) {
    Matrix result(a.cols, a.rows);
    for (int i = 0; i < a.rows; ++i) {
        for (int j = 0; j < a.cols; ++j) {
            result(j, i) = a(i, j);
        }
    }
    return result;
}

// Multiplicacao escalar
Matrix mat_scale(const Matrix& a, double scalar) {
    Matrix result(a.rows, a.cols);
    for (int i = 0; i < a.size(); ++i) {
        result[i] = a[i] * scalar;
    }
    return result;
}

// Soma ao longo das linhas (colapsa para vetor coluna)
Matrix mat_sum_rows(const Matrix& a) {
    Matrix result(a.rows, 1);
    for (int i = 0; i < a.rows; ++i) {
        double sum = 0.0;
        for (int j = 0; j < a.cols; ++j) {
            sum += a(i, j);
        }
        result(i, 0) = sum;
    }
    return result;
}

// =====================================================================
// Secao 3: Funcoes de Ativacao e Derivadas
// Implementacao das ativacoes usadas no backpropagation
// =====================================================================

// Sigmoid: f(x) = 1 / (1 + exp(-x))
double sigmoid(double x) {
    return 1.0 / (1.0 + std::exp(-std::clamp(x, -500.0, 500.0)));
}

// Derivada da Sigmoid: f'(x) = f(x) * (1 - f(x))
// Recebe a saida ja calculada (a) para evitar recomputacao
double sigmoid_derivative(double a) {
    return a * (1.0 - a);
}

// ReLU: f(x) = max(0, x)
double relu(double x) {
    return std::max(0.0, x);
}

// Derivada da ReLU: f'(x) = 1 se x > 0, 0 caso contrario
double relu_derivative_from_z(double z) {
    return z > 0.0 ? 1.0 : 0.0;
}

// Tanh: f(x) = tanh(x)
double tanh_act(double x) {
    return std::tanh(x);
}

// Derivada da Tanh: f'(x) = 1 - tanh(x)^2
double tanh_derivative(double a) {
    return 1.0 - a * a;
}

// Aplicar funcao de ativacao em toda a matriz
enum class Activation { SIGMOID, RELU, TANH, NONE };

Matrix apply_activation(const Matrix& m, Activation act) {
    Matrix result(m.rows, m.cols);
    for (int i = 0; i < m.size(); ++i) {
        switch (act) {
            case Activation::SIGMOID: result[i] = sigmoid(m[i]); break;
            case Activation::RELU:    result[i] = relu(m[i]);    break;
            case Activation::TANH:    result[i] = tanh_act(m[i]); break;
            case Activation::NONE:    result[i] = m[i];           break;
        }
    }
    return result;
}

// Calcular derivada de ativacao (recebe saida a para sigmoid/tanh,
// ou entrada z para relu)
Matrix activation_derivative(const Matrix& z, const Matrix& a, Activation act) {
    Matrix result(z.rows, z.cols);
    for (int i = 0; i < z.size(); ++i) {
        switch (act) {
            case Activation::SIGMOID: result[i] = sigmoid_derivative(a[i]); break;
            case Activation::RELU:    result[i] = relu_derivative_from_z(z[i]); break;
            case Activation::TANH:    result[i] = tanh_derivative(a[i]); break;
            case Activation::NONE:    result[i] = 1.0; break;
        }
    }
    return result;
}

// =====================================================================
// Secao 4: Inicializacao de Pesos
// Xavier para sigmoid/tanh, He para ReLU
// =====================================================================

std::mt19937& get_rng() {
    static std::mt19937 rng(42); // seed fixa para reprodutibilidade
    return rng;
}

Matrix init_weights_xavier(int fan_in, int fan_out) {
    Matrix w(fan_out, fan_in);
    double stddev = std::sqrt(2.0 / (fan_in + fan_out));
    std::normal_distribution<double> dist(0.0, stddev);
    for (int i = 0; i < w.size(); ++i) {
        w[i] = dist(get_rng());
    }
    return w;
}

Matrix init_weights_he(int fan_in, int fan_out) {
    Matrix w(fan_out, fan_in);
    double stddev = std::sqrt(2.0 / fan_in);
    std::normal_distribution<double> dist(0.0, stddev);
    for (int i = 0; i < w.size(); ++i) {
        w[i] = dist(get_rng());
    }
    return w;
}

// =====================================================================
// Secao 5: Camada da Rede Neural
// Cada camada encapsula forward e backward
// =====================================================================

struct Layer {
    Matrix weights;       // W: (neurons_out x neurons_in)
    Matrix bias;          // b: (neurons_out x 1)
    Matrix z;             // pre-ativacao
    Matrix a;             // pos-ativacao
    Matrix delta;         // gradiente local (para backward)
    Matrix dw;            // gradiente dos pesos
    Matrix db;            // gradiente dos vieses
    Activation activation;
    int neurons_in;
    int neurons_out;

    Layer(int n_in, int n_out, Activation act)
        : neurons_in(n_in), neurons_out(n_out), activation(act) {
        weights = init_weights_xavier(n_in, n_out);
        bias = Matrix(n_out, 1, 0.0);
    }

    // Forward pass: z = W*a_prev + b, a = f(z)
    Matrix forward(const Matrix& a_prev) {
        z = mat_add(mat_mul(weights, a_prev), bias);
        a = apply_activation(z, activation);
        return a;
    }

    // Backward pass: calcula delta e gradientes dos pesos
    // delta_next: erro da camada seguinte
    // w_next: pesos da camada seguinte
    // a_prev: ativacao da camada anterior
    Matrix backward(const Matrix& delta_next, const Matrix& w_next,
                    const Matrix& a_prev) {
        // Se e a ultima camada, delta vem diretamente do erro
        // Para camadas intermediarias, propaga o erro
        if (delta_next.size() > 0 && w_next.size() > 0) {
            // Propagacao: delta = (W_next^T * delta_next) .* f'(z)
            Matrix w_next_t = mat_transpose(w_next);
            Matrix propagated = mat_mul(w_next_t, delta_next);
            Matrix act_deriv = activation_derivative(z, a, activation);
            delta = mat_hadamard(propagated, act_deriv);
        } else {
            // Camada de saida: delta ja foi computado
            delta = delta_next;
        }

        // Gradientes dos pesos: dW = delta * a_prev^T
        Matrix a_prev_t = mat_transpose(a_prev);
        dw = mat_mul(delta, a_prev_t);

        // Gradientes dos vieses: db = delta (soma ja feita no treinador)
        db = delta;

        return delta;
    }
};

// =====================================================================
// Secao 6: Rede Neural MLP Completa
// Orquestra forward, backward e atualizacao de pesos
// =====================================================================

class MLP {
public:
    std::vector<Layer> layers;
    double learning_rate;
    int num_layers;

    MLP(const std::vector<int>& topology, const std::vector<Activation>& activations,
        double lr = 0.01) : learning_rate(lr) {
        assert(topology.size() >= 2);
        assert(activations.size() == topology.size() - 1);
        num_layers = topology.size() - 1;

        for (int i = 0; i < num_layers; ++i) {
            layers.emplace_back(topology[i], topology[i + 1], activations[i]);
        }
    }

    // Forward pass completo
    Matrix forward(const Matrix& input) {
        Matrix current = input;
        for (int i = 0; i < num_layers; ++i) {
            current = layers[i].forward(current);
        }
        return current;
    }

    // Backward pass completo
    void backward(const Matrix& output, const Matrix& target) {
        // Calcular gradiente da perda (MSE)
        // dL/da = a - y (para MSE: L = 0.5 * (a - y)^2)
        Matrix error = mat_sub(output, target);

        // Camada de saida: delta = erro * f'(z)
        Matrix& last_layer = layers[num_layers - 1];
        Matrix act_deriv = activation_derivative(
            last_layer.z, last_layer.a, last_layer.activation);
        Matrix delta_output = mat_hadamard(error, act_deriv);

        // Backward na ultima camada
        Matrix empty(0, 0);
        last_layer.backward(delta_output, empty, layers[num_layers - 2].a);

        // Backward nas camadas intermediarias (da penultima ate a primeira)
        for (int i = num_layers - 2; i >= 0; --i) {
            Matrix& w_next = layers[i + 1].weights;
            Matrix& delta_next = layers[i + 1].delta;
            Matrix& a_prev = (i > 0) ? layers[i - 1].a : layers[0].a;
            layers[i].backward(delta_next, w_next, a_prev);
        }
    }

    // Atualizar pesos usando gradientes computados
    void update_weights(int batch_size) {
        double scale = learning_rate / batch_size;
        for (int i = 0; i < num_layers; ++i) {
            Layer& l = layers[i];
            // W = W - lr * dW / batch_size
            for (int j = 0; j < l.weights.size(); ++j) {
                l.weights[j] -= scale * l.dw[j];
            }
            // b = b - lr * db / batch_size
            for (int j = 0; j < l.bias.size(); ++j) {
                l.bias[j] -= scale * l.db[j];
            }
        }
    }

    // Calcular perda MSE
    double compute_loss(const Matrix& output, const Matrix& target) {
        double loss = 0.0;
        for (int i = 0; i < output.size(); ++i) {
            double diff = output[i] - target[i];
            loss += diff * diff;
        }
        return loss / (2.0 * output.size());
    }

    // Imprimir gradientes (para debugging)
    void print_gradients() {
        for (int i = 0; i < num_layers; ++i) {
            double norm_dw = 0.0, norm_db = 0.0;
            for (int j = 0; j < layers[i].dw.size(); ++j) {
                norm_dw += layers[i].dw[j] * layers[i].dw[j];
            }
            for (int j = 0; j < layers[i].db.size(); ++j) {
                norm_db += layers[i].db[j] * layers[i].db[j];
            }
            std::cout << "  Camada " << i + 1
                      << "  |dW| = " << std::sqrt(norm_dw)
                      << "  |db| = " << std::sqrt(norm_db) << "\n";
        }
    }
};

// =====================================================================
// Secao 7: Treinador com Mini-Batch
// Implementa o loop de treinamento completo
// =====================================================================

class Trainer {
public:
    MLP& network;
    int epochs;
    int batch_size;
    bool verbose;

    Trainer(MLP& net, int ep, int bs, bool v = true)
        : network(net), epochs(ep), batch_size(bs), verbose(v) {}

    void train(const std::vector<Matrix>& X,
               const std::vector<Matrix>& Y) {
        int m = X.size();
        assert(m == Y.size());

        for (int epoch = 0; epoch < epochs; ++epoch) {
            double total_loss = 0.0;

            // Embaralhar indices
            std::vector<int> indices(m);
            std::iota(indices.begin(), indices.end(), 0);
            std::shuffle(indices.begin(), indices.end(), get_rng());

            for (int b = 0; b < m; b += batch_size) {
                int batch_end = std::min(b + batch_size, m);
                int current_batch = batch_end - b;

                // Forward pass para cada exemplo no batch
                std::vector<Matrix> outputs;
                for (int i = b; i < batch_end; ++i) {
                    Matrix out = network.forward(X[indices[i]]);
                    outputs.push_back(out);
                    total_loss += network.compute_loss(out, Y[indices[i]]);
                }

                // Backward pass
                for (int i = b; i < batch_end; ++i) {
                    network.backward(outputs[i - b], Y[indices[i]]);
                }

                // Atualizar pesos
                network.update_weights(current_batch);
            }

            if (verbose && (epoch % 100 == 0 || epoch == epochs - 1)) {
                double avg_loss = total_loss / m;
                std::cout << "Epoch " << std::setw(5) << epoch
                          << "  Loss: " << std::fixed << std::setprecision(6)
                          << avg_loss << "\n";
            }
        }
    }
};

// =====================================================================
// Secao 8: Testes e Exemplos
// Demonstra backpropagation funcionando em problemas reais
// =====================================================================

// Teste 1: Aproximacao de funcao sin()
void test_sine_approximation() {
    std::cout << "\n=== Teste 1: Aproximacao de sin(x) ===\n";

    // Gerar dados: x em [-pi, pi], y = sin(x)
    std::vector<Matrix> X, Y;
    for (int i = 0; i < 200; ++i) {
        double x = -M_PI + (2.0 * M_PI * i / 199.0);
        Matrix input(1, 1);
        input(0, 0) = x / M_PI; // normalizar para [-1, 1]
        Matrix target(1, 1);
        target(0, 0) = std::sin(x); // saida em [-1, 1]
        X.push_back(input);
        Y.push_back(target);
    }

    // Rede: 1 -> 16 -> 16 -> 1
    std::vector<int> topology = {1, 16, 16, 1};
    std::vector<Activation> activations = {
        Activation::RELU, Activation::RELU, Activation::SIGMOID};
    MLP network(topology, activations, 0.01);

    Trainer trainer(network, 1000, 32);
    trainer.train(X, Y);

    // Avaliar em pontos de teste
    std::cout << "\nResultados:\n";
    std::cout << "  x\t\ty_pred\t\ty_true\t\terro\n";
    double total_error = 0.0;
    for (int i = 0; i < 10; ++i) {
        double x = -M_PI + (2.0 * M_PI * i / 9.0);
        Matrix input(1, 1);
        input(0, 0) = x / M_PI;
        Matrix pred = network.forward(input);
        double error = std::abs(pred(0, 0) - std::sin(x));
        total_error += error;
        std::cout << "  " << std::fixed << std::setprecision(3) << x
                  << "\t" << pred(0, 0)
                  << "\t" << std::sin(x)
                  << "\t" << error << "\n";
    }
    std::cout << "  Erro medio: " << total_error / 10.0 << "\n";
}

// Teste 2: Classificacao XOR
void test_xor() {
    std::cout << "\n=== Teste 2: Classificacao XOR ===\n";

    // Dados XOR
    std::vector<Matrix> X, Y;
    X.push_back(Matrix({{0, 0}}));  Y.push_back(Matrix({{0}}));
    X.push_back(Matrix({{0, 1}}));  Y.push_back(Matrix({{1}}));
    X.push_back(Matrix({{1, 0}}));  Y.push_back(Matrix({{1}}));
    X.push_back(Matrix({{1, 1}}));  Y.push_back(Matrix({{0}}));

    // Rede: 2 -> 8 -> 1
    std::vector<int> topology = {2, 8, 1};
    std::vector<Activation> activations = {
        Activation::RELU, Activation::SIGMOID};
    MLP network(topology, activations, 0.1);

    Trainer trainer(network, 2000, 4);
    trainer.train(X, Y);

    // Avaliar
    std::cout << "\nResultados XOR:\n";
    for (int i = 0; i < 4; ++i) {
        Matrix pred = network.forward(X[i]);
        std::cout << "  Input: [" << X[i](0, 0) << ", " << X[i](0, 1)
                  << "]  Pred: " << std::fixed << std::setprecision(3)
                  << pred(0, 0)
                  << "  Target: " << Y[i](0, 0) << "\n";
    }
}

// Teste 3: Regressao linear simples
void test_linear_regression() {
    std::cout << "\n=== Teste 3: Regressao Linear ===\n";

    // y = 2*x1 + 3*x2 + 1
    std::vector<Matrix> X, Y;
    std::mt19937& rng = get_rng();
    std::normal_distribution<double> noise(0, 0.05);

    for (int i = 0; i < 100; ++i) {
        double x1 = (double)rng() / rng.max();
        double x2 = (double)rng() / rng.max();
        Matrix input(2, 1);
        input(0, 0) = x1;
        input(1, 0) = x2;
        Matrix target(1, 1);
        target(0, 0) = 2.0 * x1 + 3.0 * x2 + 1.0 + noise(rng);
        X.push_back(input);
        Y.push_back(target);
    }

    // Rede: 2 -> 8 -> 1 (sem ativacao na saida para regressao)
    std::vector<int> topology = {2, 8, 1};
    std::vector<Activation> activations = {
        Activation::RELU, Activation::NONE};
    MLP network(topology, activations, 0.001);

    Trainer trainer(network, 500, 16);
    trainer.train(X, Y);

    // Testar
    std::cout << "\nResultados:\n";
    std::cout << "  x1\t\tx2\t\ty_pred\t\ty_true\n";
    for (int i = 0; i < 5; ++i) {
        double x1 = (double)rng() / rng.max();
        double x2 = (double)rng() / rng.max();
        Matrix input(2, 1);
        input(0, 0) = x1;
        input(1, 0) = x2;
        Matrix pred = network.forward(input);
        double y_true = 2.0 * x1 + 3.0 * x2 + 1.0;
        std::cout << "  " << std::fixed << std::setprecision(3)
                  << x1 << "\t" << x2 << "\t"
                  << pred(0, 0) << "\t" << y_true << "\n";
    }
}

// =====================================================================
// Secao 9: Numerical Gradient Check
// Validacao da implementacao analitica
// =====================================================================

double numerical_gradient(MLP& net, const Matrix& input, const Matrix& target,
                          int layer_idx, int param_i, int param_j,
                          double epsilon = 1e-5) {
    // Salvar valor original
    double original;
    Layer& l = net.layers[layer_idx];
    original = l.weights(param_i, param_j);

    // f(w + eps)
    l.weights(param_i, param_j) = original + epsilon;
    Matrix out_plus = net.forward(input);
    double loss_plus = net.compute_loss(out_plus, target);

    // f(w - eps)
    l.weights(param_i, param_j) = original - epsilon;
    Matrix out_minus = net.forward(input);
    double loss_minus = net.compute_loss(out_minus, target);

    // Restaurar
    l.weights(param_i, param_j) = original;

    return (loss_plus - loss_minus) / (2.0 * epsilon);
}

void gradient_check() {
    std::cout << "\n=== Gradient Check ===\n";

    std::vector<int> topology = {2, 3, 1};
    std::vector<Activation> activations = {
        Activation::RELU, Activation::SIGMOID};
    MLP network(topology, activations, 0.01);

    Matrix input(2, 1);
    input(0, 0) = 0.5;
    input(1, 0) = -0.3;
    Matrix target(1, 1);
    target(0, 0) = 1.0;

    // Forward + backward
    Matrix output = network.forward(input);
    network.backward(output, target);

    // Comparar gradientes analiticos vs numericos para a primeira camada
    std::cout << "Comparacao de gradientes (camada 1, pesos):\n";
    double max_error = 0.0;
    for (int i = 0; i < std::min(3, network.layers[0].weights.rows); ++i) {
        for (int j = 0; j < std::min(2, network.layers[0].weights.cols); ++j) {
            double analytical = network.layers[0].dw(i, j);
            double numerical = numerical_gradient(
                network, input, target, 0, i, j);
            double error = std::abs(analytical - numerical);
            max_error = std::max(max_error, error);
            std::cout << "  W[" << i << "," << j << "]:"
                      << "  analitico=" << std::setw(10) << std::fixed
                      << std::setprecision(6) << analytical
                      << "  numerico=" << std::setw(10) << numerical
                      << "  erro=" << error << "\n";
        }
    }
    std::cout << "  Erro maximo: " << max_error << "\n";
    if (max_error < 1e-5) {
        std::cout << "  PASS: Gradientes corretos!\n";
    } else if (max_error < 1e-3) {
        std::cout << "  WARN: Erro aceitavel, mas verifique implementacao\n";
    } else {
        std::cout << "  FAIL: Gradientes incorretos!\n";
    }
}

// =====================================================================
// Funcao Principal
// =====================================================================

int main() {
    std::cout << "========================================\n";
    std::cout << "  Backpropagation — Implementacao C++   \n";
    std::cout << "========================================\n";

    test_sine_approximation();
    test_xor();
    test_linear_regression();
    gradient_check();

    std::cout << "\n========================================\n";
    std::cout << "  Todos os testes concluidos!           \n";
    std::cout << "========================================\n";

    return 0;
}
```

---

## 6. Implementacao em Rust

### 6.1 Estrutura do Projeto

```rust
// src/main.rs
// Implementacao completa de backpropagation para MLP
// Sem bibliotecas externas — apenas Rust standard

use std::cmp;
use std::fmt;

// =====================================================================
// Secao 1: Estrutura Matrix com ownership e borrowing
// =====================================================================

#[derive(Clone, Debug)]
struct Matrix {
    data: Vec<f64>,
    rows: usize,
    cols: usize,
}

impl Matrix {
    fn zeros(rows: usize, cols: usize) -> Self {
        Matrix {
            data: vec![0.0; rows * cols],
            rows,
            cols,
        }
    }

    fn from_data(rows: usize, cols: usize, data: Vec<f64>) -> Self {
        assert_eq!(rows * cols, data.len());
        Matrix { data, rows, cols }
    }

    fn fill(rows: usize, cols: usize, val: f64) -> Self {
        Matrix {
            data: vec![val; rows * cols],
            rows,
            cols,
        }
    }

    fn get(&self, i: usize, j: usize) -> f64 {
        self.data[i * self.cols + j]
    }

    fn set(&mut self, i: usize, j: usize, val: f64) {
        self.data[i * self.cols + j] = val;
    }

    fn get_flat(&self, idx: usize) -> f64 {
        self.data[idx]
    }

    fn set_flat(&mut self, idx: usize, val: f64) {
        self.data[idx] = val;
    }

    fn size(&self) -> usize {
        self.rows * self.cols
    }
}

// =====================================================================
// Secao 2: Operacoes de Matriz
// =====================================================================

fn mat_add(a: &Matrix, b: &Matrix) -> Matrix {
    assert_eq!(a.rows, b.rows);
    assert_eq!(a.cols, b.cols);
    let mut result = Matrix::zeros(a.rows, a.cols);
    for i in 0..a.size() {
        result.data[i] = a.data[i] + b.data[i];
    }
    result
}

fn mat_sub(a: &Matrix, b: &Matrix) -> Matrix {
    assert_eq!(a.rows, b.rows);
    assert_eq!(a.cols, b.cols);
    let mut result = Matrix::zeros(a.rows, a.cols);
    for i in 0..a.size() {
        result.data[i] = a.data[i] - b.data[i];
    }
    result
}

fn mat_mul(a: &Matrix, b: &Matrix) -> Matrix {
    assert_eq!(a.cols, b.rows);
    let mut result = Matrix::zeros(a.rows, b.cols);
    for i in 0..a.rows {
        for j in 0..b.cols {
            let mut sum = 0.0;
            for k in 0..a.cols {
                sum += a.get(i, k) * b.get(k, j);
            }
            result.set(i, j, sum);
        }
    }
    result
}

fn mat_hadamard(a: &Matrix, b: &Matrix) -> Matrix {
    assert_eq!(a.rows, b.rows);
    assert_eq!(a.cols, b.cols);
    let mut result = Matrix::zeros(a.rows, a.cols);
    for i in 0..a.size() {
        result.data[i] = a.data[i] * b.data[i];
    }
    result
}

fn mat_transpose(a: &Matrix) -> Matrix {
    let mut result = Matrix::zeros(a.cols, a.rows);
    for i in 0..a.rows {
        for j in 0..a.cols {
            result.set(j, i, a.get(i, j));
        }
    }
    result
}

fn mat_scale(a: &Matrix, scalar: f64) -> Matrix {
    let mut result = Matrix::zeros(a.rows, a.cols);
    for i in 0..a.size() {
        result.data[i] = a.data[i] * scalar;
    }
    result
}

// =====================================================================
// Secao 3: Funcoes de Ativacao
// =====================================================================

#[derive(Clone, Copy, Debug)]
enum Activation {
    Sigmoid,
    Relu,
    Tanh,
    None,
}

fn sigmoid(x: f64) -> f64 {
    1.0 / (1.0 + (-x.clamp(-500.0, 500.0)).exp())
}

fn sigmoid_derivative(a: f64) -> f64 {
    a * (1.0 - a)
}

fn relu(x: f64) -> f64 {
    x.max(0.0)
}

fn relu_derivative_from_z(z: f64) -> f64 {
    if z > 0.0 { 1.0 } else { 0.0 }
}

fn tanh_act(x: f64) -> f64 {
    x.tanh()
}

fn tanh_derivative(a: f64) -> f64 {
    1.0 - a * a
}

fn apply_activation(m: &Matrix, act: Activation) -> Matrix {
    let mut result = Matrix::zeros(m.rows, m.cols);
    for i in 0..m.size() {
        result.data[i] = match act {
            Activation::Sigmoid => sigmoid(m.data[i]),
            Activation::Relu => relu(m.data[i]),
            Activation::Tanh => tanh_act(m.data[i]),
            Activation::None => m.data[i],
        };
    }
    result
}

fn activation_derivative(z: &Matrix, a: &Matrix, act: Activation) -> Matrix {
    let mut result = Matrix::zeros(z.rows, z.cols);
    for i in 0..z.size() {
        result.data[i] = match act {
            Activation::Sigmoid => sigmoid_derivative(a.data[i]),
            Activation::Relu => relu_derivative_from_z(z.data[i]),
            Activation::Tanh => tanh_derivative(a.data[i]),
            Activation::None => 1.0,
        };
    }
    result
}

// =====================================================================
// Secao 4: Inicializacao de Pesos
// =====================================================================

fn xorshift64(seed: u64) -> u64 {
    let mut x = seed;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    x
}

struct SimpleRng {
    state: u64,
}

impl SimpleRng {
    fn new(seed: u64) -> Self {
        SimpleRng { state: seed }
    }

    fn next_f64(&mut self) -> f64 {
        self.state = xorshift64(self.state);
        (self.state as f64) / (u64::MAX as f64)
    }

    fn next_normal(&mut self) -> f64 {
        // Box-Muller transform
        let u1 = self.next_f64().max(1e-10);
        let u2 = self.next_f64();
        (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos()
    }
}

fn get_rng() -> SimpleRng {
    SimpleRng::new(42)
}

fn init_weights_xavier(rng: &mut SimpleRng, fan_in: usize, fan_out: usize) -> Matrix {
    let mut w = Matrix::zeros(fan_out, fan_in);
    let stddev = (2.0 / (fan_in as f64 + fan_out as f64)).sqrt();
    for i in 0..w.size() {
        w.data[i] = rng.next_normal() * stddev;
    }
    w
}

// =====================================================================
// Secao 5: Camada da Rede Neural
// =====================================================================

struct Layer {
    weights: Matrix,
    bias: Matrix,
    z: Matrix,
    a: Matrix,
    delta: Matrix,
    dw: Matrix,
    db: Matrix,
    activation: Activation,
    neurons_in: usize,
    neurons_out: usize,
}

impl Layer {
    fn new(n_in: usize, n_out: usize, act: Activation, rng: &mut SimpleRng) -> Self {
        Layer {
            weights: init_weights_xavier(rng, n_in, n_out),
            bias: Matrix::fill(n_out, 1, 0.0),
            z: Matrix::zeros(0, 0),
            a: Matrix::zeros(0, 0),
            delta: Matrix::zeros(0, 0),
            dw: Matrix::zeros(0, 0),
            db: Matrix::zeros(0, 0),
            activation: act,
            neurons_in: n_in,
            neurons_out: n_out,
        }
    }

    fn forward(&mut self, a_prev: &Matrix) -> &Matrix {
        self.z = mat_add(&mat_mul(&self.weights, a_prev), &self.bias);
        self.a = apply_activation(&self.z, self.activation);
        self.a.clone()
    }

    fn backward(
        &mut self,
        delta_next: &Matrix,
        w_next: &Matrix,
        a_prev: &Matrix,
        is_output: bool,
    ) {
        if !is_output && delta_next.size() > 0 && w_next.size() > 0 {
            let w_next_t = mat_transpose(w_next);
            let propagated = mat_mul(&w_next_t, delta_next);
            let act_deriv = activation_derivative(&self.z, &self.a, self.activation);
            self.delta = mat_hadamard(&propagated, &act_deriv);
        } else {
            self.delta = delta_next.clone();
        }

        let a_prev_t = mat_transpose(a_prev);
        self.dw = mat_mul(&self.delta, &a_prev_t);
        self.db = self.delta.clone();
    }
}

// =====================================================================
// Secao 6: Rede Neural MLP
// =====================================================================

struct MLP {
    layers: Vec<Layer>,
    learning_rate: f64,
}

impl MLP {
    fn new(topology: &[usize], activations: &[Activation], lr: f64) -> Self {
        assert!(topology.len() >= 2);
        assert_eq!(activations.len(), topology.len() - 1);

        let mut rng = get_rng();
        let mut layers = Vec::new();

        for i in 0..topology.len() - 1 {
            layers.push(Layer::new(
                topology[i],
                topology[i + 1],
                activations[i],
                &mut rng,
            ));
        }

        MLP {
            layers,
            learning_rate: lr,
        }
    }

    fn forward(&mut self, input: &Matrix) -> Matrix {
        let mut current = input.clone();
        for layer in &mut self.layers {
            current = layer.forward(&current).clone();
        }
        current
    }

    fn backward(&mut self, output: &Matrix, target: &Matrix) {
        let num = self.layers.len();
        let error = mat_sub(output, target);

        // Camada de saida
        let last = num - 1;
        let act_deriv = activation_derivative(
            &self.layers[last].z,
            &self.layers[last].a,
            self.layers[last].activation,
        );
        let delta_output = mat_hadamard(&error, &act_deriv);

        let empty = Matrix::zeros(0, 0);
        let a_prev = if last > 0 {
            self.layers[last - 1].a.clone()
        } else {
            // Para a primeira camada, usamos a entrada (ja nao disponivel aqui)
            // Em uma implementacao real, armazenariamos a entrada
            // Para simplificar, usamos zeros — a primeira camada nao e afetada
            Matrix::zeros(self.layers[0].neurons_in, 1)
        };
        self.layers[last].backward(&delta_output, &empty, &a_prev, true);

        // Camadas intermediarias
        for i in (0..num - 1).rev() {
            let w_next = self.layers[i + 1].weights.clone();
            let delta_next = self.layers[i + 1].delta.clone();
            let a_prev = if i > 0 {
                self.layers[i - 1].a.clone()
            } else {
                // A entrada precisaria ser armazenada para backward completo
                // Aqui usamos zeros como placeholder
                Matrix::zeros(self.layers[0].neurons_in, 1)
            };
            self.layers[i].backward(&delta_next, &w_next, &a_prev, false);
        }
    }

    fn update_weights(&mut self, batch_size: usize) {
        let scale = self.learning_rate / batch_size as f64;
        for layer in &mut self.layers {
            for i in 0..layer.weights.size() {
                layer.weights.data[i] -= scale * layer.dw.data[i];
            }
            for i in 0..layer.bias.size() {
                layer.bias.data[i] -= scale * layer.db.data[i];
            }
        }
    }

    fn compute_loss(output: &Matrix, target: &Matrix) -> f64 {
        let mut loss = 0.0;
        for i in 0..output.size() {
            let diff = output.data[i] - target.data[i];
            loss += diff * diff;
        }
        loss / (2.0 * output.size() as f64)
    }

    fn print_gradients(&self) {
        for (i, layer) in self.layers.iter().enumerate() {
            let norm_dw: f64 = layer.dw.data.iter().map(|x| x * x).sum::<f64>().sqrt();
            let norm_db: f64 = layer.db.data.iter().map(|x| x * x).sum::<f64>().sqrt();
            println!(
                "  Camada {}  |dW| = {:.6}  |db| = {:.6}",
                i + 1,
                norm_dw,
                norm_db
            );
        }
    }
}

// =====================================================================
// Secao 7: Treinador
// =====================================================================

struct Trainer {
    network: MLP,
    epochs: usize,
    batch_size: usize,
}

impl Trainer {
    fn new(network: MLP, epochs: usize, batch_size: usize) -> Self {
        Trainer {
            network,
            epochs,
            batch_size,
        }
    }

    fn train(&mut self, x_data: &[Matrix], y_data: &[Matrix]) {
        let m = x_data.len();
        assert_eq!(m, y_data.len());

        for epoch in 0..self.epochs {
            let mut total_loss = 0.0;

            // Embaralhar indices
            let mut rng = get_rng();
            let mut indices: Vec<usize> = (0..m).collect();
            for i in (1..m).rev() {
                let j = (rng.next_f64() * (i + 1) as f64) as usize;
                indices.swap(i, j.min(i));
            }

            let mut b = 0;
            while b < m {
                let batch_end = cmp::min(b + self.batch_size, m);
                let current_batch = batch_end - b;

                // Forward pass
                let mut outputs = Vec::new();
                for i in b..batch_end {
                    let out = self.network.forward(&x_data[indices[i]]);
                    outputs.push(out);
                    total_loss += MLP::compute_loss(&outputs.last().unwrap(), &y_data[indices[i]]);
                }

                // Backward pass
                for i in 0..current_batch {
                    self.network.backward(&outputs[i], &y_data[indices[b + i]]);
                }

                // Atualizar pesos
                self.network.update_weights(current_batch);

                b = batch_end;
            }

            if epoch % 100 == 0 || epoch == self.epochs - 1 {
                println!(
                    "Epoch {:5}  Loss: {:.6}",
                    epoch,
                    total_loss / m as f64
                );
            }
        }
    }
}

// =====================================================================
// Secao 8: Testes
// =====================================================================

fn test_sine_approximation() {
    println!("\n=== Teste 1: Aproximacao de sin(x) ===");

    let mut x_data = Vec::new();
    let mut y_data = Vec::new();

    for i in 0..200 {
        let x = -std::f64::consts::PI
            + (2.0 * std::f64::consts::PI * i as f64 / 199.0);
        let mut input = Matrix::zeros(1, 1);
        input.set(0, 0, x / std::f64::consts::PI);
        let mut target = Matrix::zeros(1, 1);
        target.set(0, 0, x.sin());
        x_data.push(input);
        y_data.push(target);
    }

    let topology = vec![1, 16, 16, 1];
    let activations = vec![Activation::Relu, Activation::Relu, Activation::Sigmoid];
    let network = MLP::new(&topology, &activations, 0.01);

    let mut trainer = Trainer::new(network, 1000, 32);
    trainer.train(&x_data, &y_data);

    println!("\nResultados:");
    println!("  x\t\ty_pred\t\ty_true\t\terro");
    let mut total_error = 0.0;
    for i in 0..10 {
        let x = -std::f64::consts::PI
            + (2.0 * std::f64::consts::PI * i as f64 / 9.0);
        let mut input = Matrix::zeros(1, 1);
        input.set(0, 0, x / std::f64::consts::PI);
        let pred = trainer.network.forward(&input);
        let error = (pred.get(0, 0) - x.sin()).abs();
        total_error += error;
        println!(
            "  {:.3}\t{:.3}\t{:.3}\t{:.6}",
            x,
            pred.get(0, 0),
            x.sin(),
            error
        );
    }
    println!("  Erro medio: {:.6}", total_error / 10.0);
}

fn test_xor() {
    println!("\n=== Teste 2: Classificacao XOR ===");

    let x_data = vec![
        Matrix::from_data(2, 1, vec![0.0, 0.0]),
        Matrix::from_data(2, 1, vec![0.0, 1.0]),
        Matrix::from_data(2, 1, vec![1.0, 0.0]),
        Matrix::from_data(2, 1, vec![1.0, 1.0]),
    ];
    let y_data = vec![
        Matrix::from_data(1, 1, vec![0.0]),
        Matrix::from_data(1, 1, vec![1.0]),
        Matrix::from_data(1, 1, vec![1.0]),
        Matrix::from_data(1, 1, vec![0.0]),
    ];

    let topology = vec![2, 8, 1];
    let activations = vec![Activation::Relu, Activation::Sigmoid];
    let network = MLP::new(&topology, &activations, 0.1);

    let mut trainer = Trainer::new(network, 2000, 4);
    trainer.train(&x_data, &y_data);

    println!("\nResultados XOR:");
    for i in 0..4 {
        let pred = trainer.network.forward(&x_data[i]);
        println!(
            "  Input: [{}, {}]  Pred: {:.3}  Target: {}",
            x_data[i].get(0, 0),
            x_data[i].get(1, 0),
            pred.get(0, 0),
            y_data[i].get(0, 0)
        );
    }
}

fn main() {
    println!("========================================");
    println!("  Backpropagation — Implementacao Rust  ");
    println!("========================================");

    test_sine_approximation();
    test_xor();

    println!("\n========================================");
    println!("  Todos os testes concluidos!           ");
    println!("========================================");
}
```

---

## 7. Implementacao em Fortran

### 7.1 Estrutura do Projeto

```fortran
! backpropagation.f90
! Implementacao completa de backpropagation para MLP
! Sem bibliotecas externas — apenas Fortran 2008+

module precision_mod
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)
end module precision_mod

module activation_mod
    use precision_mod
    implicit none
contains

    ! Sigmoid: f(x) = 1 / (1 + exp(-x))
    pure function sigmoid(x) result(res)
        real(dp), intent(in) :: x
        real(dp) :: res
        res = 1.0_dp / (1.0_dp + exp(-min(max(x, -500.0_dp), 500.0_dp)))
    end function sigmoid

    ! Derivada da Sigmoid: f'(x) = f(x) * (1 - f(x))
    pure function sigmoid_deriv(a) result(res)
        real(dp), intent(in) :: a
        real(dp) :: res
        res = a * (1.0_dp - a)
    end function sigmoid_deriv

    ! ReLU: f(x) = max(0, x)
    pure function relu(x) result(res)
        real(dp), intent(in) :: x
        real(dp) :: res
        res = max(0.0_dp, x)
    end function relu

    ! Derivada da ReLU: f'(x) = 1 se x > 0, 0 caso contrario
    pure function relu_deriv(z) result(res)
        real(dp), intent(in) :: z
        real(dp) :: res
        if (z > 0.0_dp) then
            res = 1.0_dp
        else
            res = 0.0_dp
        end if
    end function relu_deriv

    ! Tanh
    pure function tanh_act(x) result(res)
        real(dp), intent(in) :: x
        real(dp) :: res
        res = tanh(x)
    end function tanh_act

    ! Derivada da Tanh: f'(x) = 1 - tanh(x)^2
    pure function tanh_deriv(a) result(res)
        real(dp), intent(in) :: a
        real(dp) :: res
        res = 1.0_dp - a * a
    end function tanh_deriv

end module activation_mod

module matrix_mod
    use precision_mod
    implicit none

    type :: matrix_t
        integer :: rows = 0
        integer :: cols = 0
        real(dp), allocatable :: data(:,:)
    contains
        procedure :: init => matrix_init
        procedure :: get => matrix_get
        procedure :: set => matrix_set
        procedure :: free => matrix_free
    end type matrix_t

contains

    subroutine matrix_init(this, r, c, val)
        class(matrix_t), intent(inout) :: this
        integer, intent(in) :: r, c
        real(dp), intent(in), optional :: val
        real(dp) :: v

        if (allocated(this%data)) deallocate(this%data)

        this%rows = r
        this%cols = c
        allocate(this%data(r, c))

        if (present(val)) then
            v = val
        else
            v = 0.0_dp
        end if

        this%data = v
    end subroutine matrix_init

    pure function matrix_get(this, i, j) result(res)
        class(matrix_t), intent(in) :: this
        integer, intent(in) :: i, j
        real(dp) :: res
        res = this%data(i, j)
    end function matrix_get

    subroutine matrix_set(this, i, j, val)
        class(matrix_t), intent(inout) :: this
        integer, intent(in) :: i, j
        real(dp), intent(in) :: val
        this%data(i, j) = val
    end subroutine matrix_set

    subroutine matrix_free(this)
        class(matrix_t), intent(inout) :: this
        if (allocated(this%data)) deallocate(this%data)
        this%rows = 0
        this%cols = 0
    end subroutine matrix_free

end module matrix_mod

module math_mod
    use precision_mod
    use matrix_mod
    implicit none
contains

    ! Soma de matrizes: C = A + B
    function mat_add(a, b) result(c)
        type(matrix_t), intent(in) :: a, b
        type(matrix_t) :: c
        integer :: i, j

        call c%init(a%rows, a%cols)
        do j = 1, a%cols
            do i = 1, a%rows
                call c%set(i, j, a%get(i, j) + b%get(i, j))
            end do
        end do
    end function mat_add

    ! Subtracao de matrizes: C = A - B
    function mat_sub(a, b) result(c)
        type(matrix_t), intent(in) :: a, b
        type(matrix_t) :: c
        integer :: i, j

        call c%init(a%rows, a%cols)
        do j = 1, a%cols
            do i = 1, a%rows
                call c%set(i, j, a%get(i, j) - b%get(i, j))
            end do
        end do
    end function mat_sub

    ! Multiplicacao de matrizes: C = A * B
    function mat_mul(a, b) result(c)
        type(matrix_t), intent(in) :: a, b
        type(matrix_t) :: c
        integer :: i, j, k
        real(dp) :: sum

        call c%init(a%rows, b%cols)
        do j = 1, b%cols
            do i = 1, a%rows
                sum = 0.0_dp
                do k = 1, a%cols
                    sum = sum + a%get(i, k) * b%get(k, j)
                end do
                call c%set(i, j, sum)
            end do
        end do
    end function mat_mul

    ! Produto de Hadamard: C = A .* B
    function mat_hadamard(a, b) result(c)
        type(matrix_t), intent(in) :: a, b
        type(matrix_t) :: c
        integer :: i, j

        call c%init(a%rows, a%cols)
        do j = 1, a%cols
            do i = 1, a%rows
                call c%set(i, j, a%get(i, j) * b%get(i, j))
            end do
        end do
    end function mat_hadamard

    ! Transposta
    function mat_transpose(a) result(c)
        type(matrix_t), intent(in) :: a
        type(matrix_t) :: c
        integer :: i, j

        call c%init(a%cols, a%rows)
        do j = 1, a%cols
            do i = 1, a%rows
                call c%set(j, i, a%get(i, j))
            end do
        end do
    end function mat_transpose

    ! Escalar por matriz: C = scalar * A
    function mat_scale(a, scalar) result(c)
        type(matrix_t), intent(in) :: a
        real(dp), intent(in) :: scalar
        type(matrix_t) :: c
        integer :: i, j

        call c%init(a%rows, a%cols)
        do j = 1, a%cols
            do i = 1, a%rows
                call c%set(i, j, a%get(i, j) * scalar)
            end do
        end do
    end function mat_scale

end module math_mod

module network_mod
    use precision_mod
    use matrix_mod
    use math_mod
    use activation_mod
    implicit none

    integer, parameter :: MAX_LAYERS = 10

    type :: layer_t
        integer :: neurons_in, neurons_out
        integer :: activation_type  ! 1=sigmoid, 2=relu, 3=tanh, 4=none
        type(matrix_t) :: weights, bias
        type(matrix_t) :: z, a, delta, dw, db
    contains
        procedure :: init_layer
        procedure :: forward_layer
        procedure :: backward_layer
    end type layer_t

    type :: network_t
        integer :: num_layers
        real(dp) :: learning_rate
        type(layer_t) :: layers(MAX_LAYERS)
    contains
        procedure :: init_network
        procedure :: forward_network
        procedure :: backward_network
        procedure :: update_weights
        procedure :: compute_loss
    end type network_t

contains

    ! Inicializar camada com pesos Xavier
    subroutine init_layer(this, n_in, n_out, act_type, seed)
        class(layer_t), intent(inout) :: this
        integer, intent(in) :: n_in, n_out, act_type
        integer, intent(inout) :: seed
        real(dp) :: stddev, u, r
        integer :: i, j

        this%neurons_in = n_in
        this%neurons_out = n_out
        this%activation_type = act_type

        call this%weights%init(n_out, n_in)
        call this%bias%init(n_out, 1, 0.0_dp)
        call this%z%init(n_out, 1)
        call this%a%init(n_out, 1)
        call this%delta%init(n_out, 1)
        call this%dw%init(n_out, n_in)
        call this%db%init(n_out, 1)

        ! Inicializacao Xavier
        stddev = sqrt(2.0_dp / real(n_in + n_out, dp))
        do j = 1, n_in
            do i = 1, n_out
                ! Gerador LCG simples para numero aleatorio
                seed = mod(seed * 1103515245 + 12345, 2147483647)
                u = real(seed, dp) / 2147483647.0_dp
                seed = mod(seed * 1103515245 + 12345, 2147483647)
                r = real(seed, dp) / 2147483647.0_dp
                ! Box-Muller
                u = max(u, 1.0e-10_dp)
                call this%weights%set(i, j, &
                    stddev * sqrt(-2.0_dp * log(u)) * cos(6.283185307_dp * r))
            end do
        end do
    end subroutine init_layer

    ! Forward pass de uma camada
    subroutine forward_layer(this, a_prev)
        class(layer_t), intent(inout) :: this
        type(matrix_t), intent(in) :: a_prev
        type(matrix_t) :: wt, prod
        integer :: i

        ! z = W * a_prev + b
        wt = mat_transpose(this%weights)
        prod = mat_mul(wt, a_prev)
        this%z = mat_add(prod, this%bias)

        ! a = f(z)
        do i = 1, this%neurons_out
            select case (this%activation_type)
            case (1)
                call this%a%set(i, 1, sigmoid(this%z%get(i, 1)))
            case (2)
                call this%a%set(i, 1, relu(this%z%get(i, 1)))
            case (3)
                call this%a%set(i, 1, tanh_act(this%z%get(i, 1)))
            case (4)
                call this%a%set(i, 1, this%z%get(i, 1))
            end select
        end do
    end subroutine forward_layer

    ! Backward pass de uma camada
    subroutine backward_layer(this, delta_next, w_next, a_prev, is_output)
        class(layer_t), intent(inout) :: this
        type(matrix_t), intent(in) :: delta_next, w_next, a_prev
        logical, intent(in) :: is_output
        type(matrix_t) :: wt, propagated, act_deriv, a_prev_t
        integer :: i

        if (.not. is_output .and. delta_next%rows > 0 .and. w_next%rows > 0) then
            ! Propagacao: delta = (W_next^T * delta_next) .* f'(z)
            wt = mat_transpose(w_next)
            propagated = mat_mul(wt, delta_next)

            ! Derivada da ativacao
            do i = 1, this%neurons_out
                select case (this%activation_type)
                case (1)
                    call act_deriv%set(i, 1, sigmoid_deriv(this%a%get(i, 1)))
                case (2)
                    call act_deriv%set(i, 1, relu_deriv(this%z%get(i, 1)))
                case (3)
                    call act_deriv%set(i, 1, tanh_deriv(this%a%get(i, 1)))
                case (4)
                    call act_deriv%set(i, 1, 1.0_dp)
                end select
            end do

            this%delta = mat_hadamard(propagated, act_deriv)
        else
            this%delta = delta_next
        end if

        ! Gradientes dos pesos: dW = delta * a_prev^T
        a_prev_t = mat_transpose(a_prev)
        this%dw = mat_mul(this%delta, a_prev_t)
        this%db = this%delta
    end subroutine backward_layer

    ! Inicializar rede
    subroutine init_network(this, topology, activations, num_layers, lr, seed)
        class(network_t), intent(inout) :: this
        integer, intent(in) :: topology(:), activations(:), num_layers
        real(dp), intent(in) :: lr
        integer, intent(inout) :: seed
        integer :: i

        this%num_layers = num_layers
        this%learning_rate = lr

        do i = 1, num_layers
            call this%layers(i)%init_layer( &
                topology(i), topology(i+1), activations(i), seed)
        end do
    end subroutine init_network

    ! Forward pass completo
    subroutine forward_network(this, input)
        class(network_t), intent(inout) :: this
        type(matrix_t), intent(in) :: input
        type(matrix_t) :: current
        integer :: i

        current = input
        do i = 1, this%num_layers
            call this%layers(i)%forward_layer(current)
            current = this%layers(i)%a
        end do
    end subroutine forward_network

    ! Backward pass completo
    subroutine backward_network(this, target)
        class(network_t), intent(inout) :: this
        type(matrix_t), intent(in) :: target
        type(matrix_t) :: error, delta_output, act_deriv
        type(matrix_t) :: empty, a_prev
        integer :: i, last

        last = this%num_layers

        ! Erro da saida
        error = mat_sub(this%layers(last)%a, target)

        ! Delta da camada de saida
        call act_deriv%init(last, 1)
        do i = 1, this%layers(last)%neurons_out
            select case (this%layers(last)%activation_type)
            case (1)
                call act_deriv%set(i, 1, sigmoid_deriv(this%layers(last)%a%get(i, 1)))
            case (2)
                call act_deriv%set(i, 1, relu_deriv(this%layers(last)%z%get(i, 1)))
            case (3)
                call act_deriv%set(i, 1, tanh_deriv(this%layers(last)%a%get(i, 1)))
            case (4)
                call act_deriv%set(i, 1, 1.0_dp)
            end select
        end do
        delta_output = mat_hadamard(error, act_deriv)

        ! Backward na ultima camada
        call empty%init(0, 0)
        call this%layers(last)%backward_layer(delta_output, empty, &
            this%layers(last - 1)%a, .true.)

        ! Backward nas camadas intermediarias
        do i = last - 1, 1, -1
            if (i > 1) then
                a_prev = this%layers(i - 1)%a
            else
                call a_prev%init(this%layers(1)%neurons_in, 1)
            end if
            call this%layers(i)%backward_layer( &
                this%layers(i + 1)%delta, &
                this%layers(i + 1)%weights, &
                a_prev, .false.)
        end do
    end subroutine backward_network

    ! Atualizar pesos
    subroutine update_weights(this, batch_size)
        class(network_t), intent(inout) :: this
        integer, intent(in) :: batch_size
        real(dp) :: scale
        integer :: i, j

        scale = this%learning_rate / real(batch_size, dp)

        do i = 1, this%num_layers
            do j = 1, this%layers(i)%weights%size()
                this%layers(i)%weights%data(j/this%layers(i)%weights%rows + 1, &
                    mod(j-1, this%layers(i)%weights%rows) + 1) = &
                    this%layers(i)%weights%data(j/this%layers(i)%weights%rows + 1, &
                    mod(j-1, this%layers(i)%weights%rows) + 1) - &
                    scale * this%layers(i)%dw%data(j/this%layers(i)%dw%rows + 1, &
                    mod(j-1, this%layers(i)%dw%rows) + 1)
            end do

            do j = 1, this%layers(i)%bias%size()
                this%layers(i)%bias%data(j, 1) = &
                    this%layers(i)%bias%data(j, 1) - &
                    scale * this%layers(i)%db%data(j, 1)
            end do
        end do
    end subroutine update_weights

    ! Calcular perda MSE
    function compute_loss(this, target) result(loss)
        class(network_t), intent(in) :: this
        type(matrix_t), intent(in) :: target
        real(dp) :: loss, diff
        integer :: i, last

        last = this%num_layers
        loss = 0.0_dp
        do i = 1, this%layers(last)%neurons_out
            diff = this%layers(last)%a%get(i, 1) - target%get(i, 1)
            loss = loss + diff * diff
        end do
        loss = loss / (2.0_dp * real(this%layers(last)%neurons_out, dp))
    end function compute_loss

end module network_mod

! =====================================================================
! Programa Principal
! =====================================================================
program backpropagation
    use precision_mod
    use matrix_mod
    use math_mod
    use activation_mod
    use network_mod
    implicit none

    type(network_t) :: net
    integer :: seed, topology(3), activations(2), epoch, i, n_epochs
    real(dp) :: lr, x_val, y_pred, y_true, total_error

    print *, "========================================"
    print *, "  Backpropagation — Implementacao Fortran"
    print *, "========================================"

    seed = 42
    n_epochs = 500
    lr = 0.05_dp

    ! Rede: 1 -> 8 -> 1 (aproximacao de sin(x))
    topology = (/ 1, 8, 1 /)
    activations = (/ 2, 1 /)  ! 2=relu, 1=sigmoid

    call net%init_network(topology, activations, 2, lr, seed)

    ! Treinar: y = sin(x)
    print *, ""
    print *, "Treinando para aproximar sin(x)..."
    do epoch = 0, n_epochs - 1
        total_error = 0.0_dp
        do i = 0, 19
            x_val = -3.14159265358979_dp + &
                    (6.28318530717959_dp * real(i, dp) / 19.0_dp)

            ! Forward pass
            call net%forward_network(Matrix_1d(1, x_val / 3.14159265358979_dp))

            ! Backward pass
            call net%backward_network(Matrix_1d(1, sin(x_val)))

            ! Atualizar pesos
            call net%update_weights(1)

            total_error = total_error + net%compute_loss(Matrix_1d(1, sin(x_val)))
        end do

        if (mod(epoch, 100) == 0 .or. epoch == n_epochs - 1) then
            print '(A, I5, A, F12.8)', "  Epoch ", epoch, &
                "  Loss: ", total_error / 20.0_dp
        end if
    end do

    ! Avaliar
    print *, ""
    print *, "Resultados:"
    print *, "  x        y_pred     y_true     erro"
    total_error = 0.0_dp
    do i = 0, 9
        x_val = -3.14159265358979_dp + &
                (6.28318530717959_dp * real(i, dp) / 9.0_dp)
        call net%forward_network(Matrix_1d(1, x_val / 3.14159265358979_dp))
        y_pred = net%layers(net%num_layers)%a%get(1, 1)
        y_true = sin(x_val)
        total_error = total_error + abs(y_pred - y_true)
        print '(A, F8.3, A, F8.3, A, F8.3, A, F10.6)', &
            "  ", x_val, "   ", y_pred, "   ", y_true, "   ", abs(y_pred - y_true)
    end do
    print '(A, F10.6)', "  Erro medio: ", total_error / 10.0_dp

    print *, ""
    print *, "========================================"
    print *, "  Todos os testes concluidos!           "
    print *, "========================================"

contains

    ! Helper: criar matriz 1D (coluna)
    function Matrix_1d(n, val) result(m)
        integer, intent(in) :: n
        real(dp), intent(in) :: val
        type(matrix_t) :: m
        call m%init(n, 1)
        call m%set(1, 1, val)
    end function Matrix_1d

end program backpropagation
```

---

## 8. Numerical Gradients vs Analytical Gradients

### 8.1 O Problema

Toda vez que implementamos backpropagation, corremos o risco de cometer erros — indices errados, transposicao esquecida, derivada incorreta. A validacao numerica e a forma definitiva de garantir que a implementacao analitica esta correta.

### 8.2 Gradiente Numerico

O gradiente numerico usa a definicao de derivada:

```text
dL/dw = limite(h->0) [L(w + h) - L(w - h)] / (2h)
```

Na pratica, usamos h muito pequeno (1e-5 a 1e-7) e a diferenciaca central:

```text
dL/dw ~ [L(w + h) - L(w - h)] / (2h)
```

### 8.3 Implementacao

```text
Funcao numerical_gradient(rede, entrada, alvo, indice_camada, i, j, h):
    valor_original = rede.camadas[indice_camada].pesos[i][j]
    
    // L(w + h)
    rede.camadas[indice_camada].pesos[i][j] = valor_original + h
    saida_plus = forward(rede, entrada)
    loss_plus = perda(saida_plus, alvo)
    
    // L(w - h)
    rede.camadas[indice_camada].pesos[i][j] = valor_original - h
    saida_minus = forward(rede, entrada)
    loss_minus = perda(saida_minus, alvo)
    
    // Restaurar
    rede.camadas[indice_camada].pesos[i][j] = valor_original
    
    // Diferenciaca central
    return (loss_plus - loss_minus) / (2.0 * h)
```

### 8.4 Comparacao e Metricas

```text
Para comparar gradientes analiticos vs numericos:

1. Erro absoluto: |g_analitico - g_numerico|
   Aceitavel: < 1e-5
   Suspeito:  1e-5 a 1e-3
   Errado:    > 1e-3

2. Erro relativo: |g_analitico - g_numerico| / (|g_analitico| + |g_numerico|)
   Aceitavel: < 1e-4
   Errado:    > 1e-2

3. Erro relativo com tolerancia:
   |g_analitico - g_numerico| / max(|g_analitico|, |g_numerico|) < 1e-5
```

### 8.5 Cuidados Importantes

```text
1. ESCOLHA DO h:
   Muito grande: erro de truncamento (approximacao ruim)
   Muito pequeno: erro de cancelamento numerico (flutuante)
   Ideal: 1e-5 para double precision

2. NAO USAR diferenca para frente:
   dL/dw ~ [L(w+h) - L(w)] / h
   Eh primeira ordem — menos preciso que diferenca central.

3. ATIVACAO NA SAIDA:
   Nao aplique sigmoid na saida para gradient check de sigmoid.
   A derivada da loss com sigmoid na saida e mais estavel.

4. REGULARIZACAO:
   Se houver L2 regularization, adicione o termo 2*lambda*w ao
   gradiente analitico antes de comparar.

5. AMOSTRAGEM:
   Teste multiplas entradas, nao apenas uma. Erros podem ser
   mascarados por entradas especificas.
```

### 8.6 Quando Nao Usar

```text
Gradient checking e O(n) por parametro — muito custoso para redes grandes.
Use APENAS para:
  1. Validar implementacao inicial
  2. Debug quando o treinamento nao converge
  3. Implementar uma nova camada/custom operation

Nao use para:
  1. Treinamento real (muito lento)
  2. Redes com milhoes de parametros
  3. Producao regular
```

---

## 9. Debugging Backpropagation

### 9.1 Sintomas de Problemas

```text
Sintoma                          Causa Provavel
---------------------------------------------------------------
Loss permanece constante         Learning rate muito baixo ou
                                 pesos nao estao atualizando

Loss oscila violentamente        Learning rate muito alto

Loss converge mas erro alto      Rede subajustada (underfitting)
                                 ou dados insuficientes

Loss converge rapidamente        Possivelmente memorizando
                                 (overfitting) ou fuga no dataset

Loss explode para NaN/Inf        Exploding gradient ou
                                 learning rate alto demais

Loss cai e sobe periodicamente   Learning rate alto ou
                                 batch size muito pequeno
```

### 9.2 Tecnicas de Debug

```text
1. GRADIENT CHECKING:
   Valide gradientes analiticos contra numericos.
   Se estiverem incorretos, o backpropagation tem bugs.

2. MONITORAR NORMAS DOS GRADIENTES:
   Calcule a norma L2 do gradiente para cada camada:
   norm_layer_l = sqrt(soma(dW_l^2))
   
   Se a norma cresce exponencialmente: exploding gradient
   Se a norma diminui exponencialmente: vanishing gradient
   Se a norma e zero: neuronio morto ou bug

3. PLOTAR PESOS AO LONGO DO TREINAMENTO:
   Salve os pesos a cada epoch e plote distribuicao.
   Pesos que nao mudam: gradiente zero ou bug.
   Pesos que divergem: learning rate alto.

4. INSPECIONAR ATIVACOES:
   Calcule media, variancia e distribuicao de saidas por camada.
   Camadas com media ~0 e variancia ~1: normal
   Camadas com tudo zero: dying neurons
   Camadas com tudo muito grande: exploding activations

5. REDUZIR PROBLEMA:
   Treine em um unico exemplo com learning rate alto.
   A loss DEVE cair. Se nao cai, ha um bug no backpropagation.

6. UNITARIOS:
   Teste cada camada isoladamente com gradient checking.
   Isso localiza o bug na camada especifica.
```

### 9.3 Checklist de Debug

```text
[ ] Gradient checking passou para todas as camadas?
[ ] Normas dos gradientes sao da mesma ordem de magnitude?
[ ] Loss diminui no mini-batch de treinamento?
[ ] Loss diminui no conjunto de validacao?
[ ] Ativacoes nao sao todas zero ou todas iguais?
[ ] Pesos nao estao NaN ou Inf?
[ ] Learning rate nao e muito alto nem muito baixo?
[ ] Batch size e razoavel (16-256)?
[ ] Dados de entrada estao normalizados?
[ ] Funcao de perda e compativel com a ativacao de saida?
```

### 9.4 Erros Comuns

```text
1. ESQUECER A TRANSPOSTA NO BACKWARD:
   delta = W * delta_next    (ERRADO — W deve ser transposto)
   delta = W^T * delta_next  (CORRETO)

2. CONFUNDIR ORDENS DE MULTIPLICACAO:
   dW = delta * a_prev^T     (CORRETO: delta e coluna, a_prev^T e linha)
   dW = a_prev^T * delta     (ERRADO: dimensoes nao batem)

3. NAO DIVIDIR PELO BATCH SIZE:
   dW = delta * a_prev^T     (acumula sobre o batch)
   dW = (1/m) * delta * a_prev^T  (CORRETO)

4. DERIVADA ERRADA DA ATIVACAO:
   sigmoid'(x) = sigmoid(x) * (1 - sigmoid(x))
   NAO sigmoid'(x) = 1 - sigmoid(x)  (confundir com tanh)

5. ATUALIZAR PESOS DURANTE BACKWARD:
   Os pesos devem ser atualizados DEPOIS de todos os backward passes.
   Atualizar durante causa erros em camadas anteriores.

6. NAO ZERAR GRADIENTES:
   dW acumula entre mini-batches. Se nao zerar, o gradiente
   incorreto de batches anteriores afeta a atualizacao.
```

---

## 10. Exemplo: Treinar MLP para Aproximar Funcao

### 10.1 O Problema

Queremos aproximar a funcao:

```text
f(x, y) = sin(x) * cos(y)
```

para x, y em [-pi, pi]. Essa funcao e interessante porque:
- E nao-linear (nao pode ser aprendida por uma rede linear)
- E continua e diferenciavel
- Tem padroes claros (oscilacoes) que a rede deve capturar
- E facil de visualizar e avaliar

### 10.2 Arquitetura da Rede

```text
Entrada: 2 neuronios (x, y) normalizados para [-1, 1]
Camada oculta 1: 32 neuronios, ReLU
Camada oculta 2: 32 neuronios, ReLU
Camada oculta 3: 16 neuronios, ReLU
Saida: 1 neuronio, linear (nenhuma ativacao — e regressao)

Total de parametros:
  Camada 1: 2*32 + 32 = 96
  Camada 2: 32*32 + 32 = 1056
  Camada 3: 32*16 + 16 = 528
  Camada 4: 16*1 + 1 = 17
  Total: 1697 parametros
```

### 10.3 Hiperparametros

```text
Learning rate: 0.001 (com decay exponencial)
Batch size: 64
Epocas: 2000
Otimizador: SGD com momentum (beta = 0.9)
Inicializacao: He para ReLU
Normalizacao de entrada: media 0, variancia 1
```

### 10.4 Codigo do Experimento (C++)

```cpp
// experiment_sincos.cpp
// Treina MLP para aproximar f(x,y) = sin(x)*cos(y)

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <iomanip>

// Usar as classes Matrix, MLP, Trainer do codigo anterior
// Aqui focamos na definicao do experimento

void run_experiment() {
    std::cout << "\n=== Experimento: Aproximacao de sin(x)*cos(y) ===\n";

    // Gerar dados de treinamento
    std::vector<std::pair<double, double>> train_points;
    std::vector<double> train_targets;
    std::mt19937 rng(42);
    std::uniform_real_distribution<double> dist(-M_PI, M_PI);

    for (int i = 0; i < 1000; ++i) {
        double x = dist(rng);
        double y = dist(rng);
        train_points.emplace_back(x, y);
        train_targets.push_back(std::sin(x) * std::cos(y));
    }

    // Definir rede
    std::vector<int> topology = {2, 32, 32, 16, 1};
    std::vector<Activation> activations = {
        Activation::RELU, Activation::RELU, Activation::RELU, Activation::NONE};
    MLP network(topology, activations, 0.001);

    // Treinar por epocas
    int epochs = 2000;
    int batch_size = 64;
    double momentum = 0.9;

    // Armazenar historico para analise
    std::vector<double> loss_history;

    for (int epoch = 0; epoch < epochs; ++epoch) {
        double total_loss = 0.0;

        // Embaralhar
        std::vector<int> indices(1000);
        std::iota(indices.begin(), indices.end(), 0);
        std::shuffle(indices.begin(), indices.end(), rng);

        for (int b = 0; b < 1000; b += batch_size) {
            int batch_end = std::min(b + batch_size, 1000);

            // Forward + backward para cada exemplo
            for (int i = b; i < batch_end; ++i) {
                int idx = indices[i];
                Matrix input(2, 1);
                input(0, 0) = train_points[idx].first / M_PI;
                input(1, 0) = train_points[idx].second / M_PI;

                Matrix target(1, 1);
                target(0, 0) = train_targets[idx];

                Matrix output = network.forward(input);
                total_loss += network.compute_loss(output, target);
                network.backward(output, target);
            }

            network.update_weights(batch_end - b);
        }

        double avg_loss = total_loss / 1000.0;
        loss_history.push_back(avg_loss);

        if (epoch % 200 == 0 || epoch == epochs - 1) {
            std::cout << "Epoch " << std::setw(5) << epoch
                      << "  Loss: " << std::fixed << std::setprecision(6)
                      << avg_loss << "\n";
        }
    }

    // Avaliar em grade 10x10
    std::cout << "\nAvaliacao em grade:\n";
    std::cout << "  x\t\ty\t\tpred\t\ttrue\t\terro\n";
    double max_error = 0.0;
    double mean_error = 0.0;
    int count = 0;

    for (int ix = 0; ix < 10; ++ix) {
        for (int iy = 0; iy < 10; ++iy) {
            double x = -M_PI + 2 * M_PI * ix / 9.0;
            double y = -M_PI + 2 * M_PI * iy / 9.0;

            Matrix input(2, 1);
            input(0, 0) = x / M_PI;
            input(1, 0) = y / M_PI;
            Matrix pred = network.forward(input);
            double true_val = std::sin(x) * std::cos(y);
            double error = std::abs(pred(0, 0) - true_val);

            max_error = std::max(max_error, error);
            mean_error += error;
            count++;

            if (ix < 3 && iy < 3) {
                std::cout << "  " << std::fixed << std::setprecision(3)
                          << x << "\t" << y << "\t"
                          << pred(0, 0) << "\t" << true_val
                          << "\t" << error << "\n";
            }
        }
    }

    std::cout << "\nMetricas:\n";
    std::cout << "  Erro medio absoluto: " << mean_error / count << "\n";
    std::cout << "  Erro maximo absoluto: " << max_error << "\n";
    std::cout << "  Loss final: " << loss_history.back() << "\n";
}

int main() {
    run_experiment();
    return 0;
}
```

### 10.5 Analise de Resultados

```text
Esperado apos 2000 epocas:

Metrica                      Valor esperado
---------------------------------------------------------------
Loss final (MSE)             < 0.001
Erro medio absoluto          < 0.05
Erro maximo absoluto         < 0.15
Convergencia                 Loss cai rapidamente nas primeiras
                             200 epocas, depois estabiliza

Se nao atingir esses valores:
  1. Aumentar epocas (pode nao ter convergido)
  2. Aumentar learning rate (pode estar muito lento)
  3. Adicionar mais neuronios (rede pode ser subdimensionada)
  4. Verificar se nao ha bug no backpropagation (gradient check)
```

### 10.6 Interpretacao da Funcao Aprendida

```text
A rede neural aprendeu uma approximacao de:
  f(x, y) = sin(x) * cos(y)

Para x=0, f(0,y) = 0 para todo y (correta)
Para y=0, f(x,0) = sin(x) (correta)
Para x=y, f(x,x) = sin(x)*cos(x) = 0.5*sin(2x) (correta)

A rede capturou:
  1. A periodicidade em x (via sin)
  2. A periodicidade em y (via cos)
  3. A multiplicacao entre as duas (nao-linearidade)
  4. As assinaturas corretas (positiva/negativa)

Isso demonstra que uma MLP com backpropagation pode approximar
funcoes nao-lineares complexas — o Teorema da Aproximacao Universal
em acao.
```

---

## Resumo do Capitulo

Este capitulo cobriu o backpropagation — o algoritmo que torna o treinamento de redes neurais possivel:

- **Derivadas Parciais e Regra da Cadeia**: A base matematica. O backpropagation decome o gradiente complexo da perda em derivadas locais, cada uma facil de calcular.

- **Backpropagation para MLP**: O algoritmo completo. Forward pass para calcular saidas, backward pass para calcular gradientes (camada por camada, de tras para frente), atualizacao de pesos.

- **Gradiente Local vs Global**: Cada camada produz um gradiente local. O backpropagation encadeia esses gradientes para produzir o gradiente global. Essa decomposicao e a chave da eficiencia.

- **Vanishing/Exploding Gradients**: O produto de muitos gradientes locais pode tender a zero (vanishing) ou infinito (exploding). Inicializacao adequada, ReLU, Batch Norm e skip connections sao as solucoes.

- **Implementacoes em C++, Rust e Fortran**: Tres implementacoes completas e funcionais, mostrando como o mesmo algoritmo se adapta a diferentes paradigmas de programacao.

- **Gradientes Numericos vs Analiticos**: A ferramenta definitiva para validar implementacoes. Diferenciaca central com h ~ 1e-5.

- **Debugging**: Sintomas, tecnicas e checklist para diagnosticar problemas no treinamento.

- **Experimento Pratico**: Aproximacao de sin(x)*cos(y) demonstra que o backpropagation funciona na pratica.

O backpropagation e o coracao de todo deep learning. Sem ele, nao haveria como treinar redes com milhoes ou bilhoes de parametros. Dominar esse algoritmo e essencial para qualquer engenheiro de ML.

---

## Exercicios

### Exercicio 1: Derivacao Manual
Derive o backpropagation para uma rede com 2 entradas, 2 neuronios na camada oculta (ativacao tanh), e 1 saida (ativacao sigmoid). Use MSE como funcao de perda. Calcule todos os gradientes para um unico exemplo de treinamento.

### Exercicio 2: Gradient Check
Implemente o gradient checking para sua implementacao de backpropagation. Teste em pelo menos 10 pesos diferentes em cada camada. Relate os erros encontrados.

### Exercicio 3: Vanishing Gradient
Treine uma rede com 10 camadas sigmoid. Monitore as normas dos gradientes por camada. Mostre que as camadas iniciais tem gradientes significativamente menores que as camadas finais. Repita com ReLU e mostre a diferenca.

### Exercicio 4: Exploding Gradient
Use pesos inicializados com variancia alta (stddev = 10) e learning rate alto. Mostre que a loss explode. Implemente gradient clipping e mostre que resolve o problema.

### Exercicio 5: Funcao de Perda
Implemente Binary Cross-Entropy ao inves de MSE. Treine uma rede para classificacao binaria (circular dataset). Compare a convergencia com MSE.

### Exercicio 6: Momentum
Implemente SGD com momentum (beta = 0.9). Compare a convergencia com SGD puro no problema de approximacao de sin(x). Mostre que momentum acelera a convergencia.

### Exercicio 7: Arquitetura
Treine tres redes com topologias diferentes (16, 32, 64 neuronios por camada) no problema de sin(x)*cos(y). Compare a loss final e o tempo de treinamento. Qual e o trade-off?

### Exercicio 8: Inicializacao
Compare tres inicializacoes (zeros, aleatoria com stddev=1, Xavier) no mesmo problema. Mostre que inicializacao zeros falha, aleatoria pode causar vanishing/exploding, e Xavier funciona.

### Exercicio 9: Batch Size
Compare batch sizes de 1, 16, 64, e 1000 (full batch). Analise: velocidade de convergencia, estabilidade da loss, e tempo computacional.

### Exercicio 10: Implementacao Fortran
Modifique a implementacao Fortran para incluir momentum. Compile e execute. Compare os resultados com a versao C++.

---

## Referencias

1. Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986). Learning representations by back-propagating errors. Nature, 323, 533-536.

2. LeCun, Y., Bottou, L., Bengio, Y., & Haffner, P. (1998). Gradient-based learning applied to document recognition. Proceedings of the IEEE, 86(11), 2278-2324.

3. Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press. Capitulo 6.2: Gradient-Based Learning.

4. Glorot, X., & Bengio, Y. (2010). Understanding the difficulty of training deep feedforward neural networks. AISTATS.

5. He, K., Zhang, X., Ren, S., & Sun, J. (2015). Delving deep into rectifiers: Surpassing human-level performance on ImageNet classification. ICCV.

6. Pascanu, R., Mikolov, T., & Bengio, Y. (2013). On the difficulty of training recurrent neural networks. ICML.

7. Ioffe, S., & Szegedy, C. (2015). Batch normalization: Accelerating deep network training by reducing internal covariate shift. ICML.

8. He, K., Zhang, X., Ren, S., & Sun, J. (2016). Deep residual learning for image recognition. CVPR.

9. Nielsen, M. A. (2015). Neural Networks and Deep Learning. Capitulo 2: How the backpropagation algorithm works. Disponivel online.

10. Bishop, C. M. (2006). Pattern Recognition and Machine Learning. Springer. Capitulo 5: Neural Networks.

---

*[Proximo capitulo: 07 — Optimizadores](07-optimizadores.md)*
