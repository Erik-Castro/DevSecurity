---
layout: default
title: "08-regularizacao"
---

# Capitulo 8 — Regularizacao

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender o tradeoff bias-variance** e como ele governa a capacidade de generalizacao de modelos de machine learning.
2. **Diagnosticar overfitting e underfitting** usando learning curves, gap entre treino e validacao, e metricas de desempenho.
3. **Implementar L1 Regularization (Lasso)** com subgradiente e compreender como ela produz esparsidade nos pesos.
4. **Implementar L2 Regularization (Ridge)** e entender a intuicao geometrica por tras da contracao dos pesos.
5. **Combinar L1 e L2 no Elastic Net** e saber quando cada abordagem e preferivel.
6. **Implementar Dropout** com variante inverted dropout, entendendo a diferenca entre treino e inferencia.
7. **Implementar Batch Normalization** com medias moveis e backward pass completo.
8. **Implementar Layer Normalization** e entender por que transformers a preferem sobre batch norm.
9. **Aplicar Early Stopping** com monitoramento de perda de validacao e mecanismo de paciencia.
10. **Combinar tecnicas de regularizacao** em um pipeline de treinamento completo em C++, Rust e Fortran.

---

## 1. Overfitting vs Underfitting

### 1.1 O Problema Fundamental da Generalizacao

O objetivo do machine learning nao e memorizar os dados de treino, mas sim aprender padroes que se generalizem para dados nunca vistos. Essa tensao entre ajuste aos dados e capacidade de generalizacao e o problema central da disciplina.

```text
Generalizacao = capacidade de um modelo de produzir boas
predicoes em dados novos, diferentes dos dados de treinamento.
```

### 1.2 Bias: O Que e por Que Importa

**Bias** (ou vies) e o erro introduzido por simplificacoes feitas pelo algoritmo de aprendizado para tornar o problema mais facil de resolver. Um modelo com bias alto faz supostas simplificacoes fortes sobre os dados, o que pode levar a underfitting.

```text
Definicao formal:
    Bias(f_hat) = E[f_hat(x)] - f(x)

Onde:
    f(x) = funcao verdadeira (desconhecida)
    f_hat(x) = funcao estimada pelo modelo
    E[] = esperanca sobre todos os conjuntos de treino possiveis

Bias alto = modelo consistentemente errado (tendencioso)
Bias baixo = modelo em media correto
```

Exemplos de bias alto:

```text
- Regressao linear em dados quadraticos
- Arvore de decisao com profundidade maxima = 1
- Rede neural com apenas 1 camada oculta e poucos neuronios
```

### 1.3 Variance: O Que e por Que Importa

**Variance** (ou variancia) mede o quao sensivel o modelo e a flutuacoes nos dados de treinamento. Um modelo com variance alta se ajusta demais as especificidades do conjunto de treino.

```text
Definicao formal:
    Var(f_hat) = E[(f_hat(x) - E[f_hat(x)])^2]

Onde:
    A esperanca e sobre todos os conjuntos de treino possiveis

Variance alta = modelo muda drasticamente com diferentes treinos
Variance baixa = modelo e estavel independente do treino
```

Exemplos de variance alta:

```text
- Arvore de decisao sem limite de profundidade
- Rede neural com milhoes de parametros para poucos dados
- k-NN com k=1 (vizinho mais proximo)
```

### 1.4 O Tradeoff Bias-Variance

O erro total de um modelo pode ser decomposto em tres componentes:

```text
Erro Total = Bias^2 + Variance + Erro Irredutivel

Onde:
    Erro Irredutivel = variancia do ruido nos dados
                      (impossivel de eliminar)

Tradeoff fundamental:
    - Aumentar complexidade do modelo: diminui bias, aumenta variance
    - Diminuir complexidade do modelo: aumenta bias, diminui variance
    - O objetivo: encontrar o ponto otimo onde a soma e minimizada
```

Representacao visual do tradeoff:

```text
Erro
 |
 |  \                        /  Variance
 |   \                      /
 |    \        ___         /
 |     \      /   \       /
 |      \    /     \     /
 |       \  /  ___  \   /
 |        \/  /   \  \ /
 |         \ /     \  \  Bias
 |          X       \  
 |         / \       \____
 |        /   \        
 |       /     \       
 |______/       \______
 |
 +-------------------------> Complexidade do Modelo
   Underfitting   Zona     Overfitting
                  Otima
```

### 1.5 Diagnostico Visual

A forma mais direta de diagnosticar o regime de um modelo e comparar o desempenho em treino e validacao:

```text
Cenarios de diagnostico:

1. Underfitting (bias alto):
   - Treino: ruim
   - Validacao: ruim
   - Gap treino-validacao: pequeno

2. Overfitting (variance alta):
   - Treino: excelente
   - Validacao: ruim
   - Gap treino-validacao: grande

3. Ajuste adequado (bias-variance balanceados):
   - Treino: bom
   - Validacao: bom (perto do treino)
   - Gap treino-validacao: pequeno

4. Overfitting severo:
   - Treino: perfeito (loss ~ 0)
   - Validacao: pessimo
   - Gap treino-validacao: enorme
```

### 1.6 Learning Curves

Learning curves sao graficos que mostram o erro em funcao da quantidade de dados de treino. Elas sao uma ferramenta poderosa para diagnosticar bias e variance.

```text
Learning Curves — Underfitting (Bias Alto):

Erro
 |
 |   _______________          Treino
 |   |_____________|
 |   \           /
 |    \_________/             Validacao
 |     \_______/
 +-------------------------> Amostras de Treino
   Poucas                  Muitas

    Ambas as curvas convergem para um erro alto.
    Adicionar mais dados NAO melhora o problema.
    SOLUCAO: modelo mais complexo.
```

```text
Learning Curves — Overfitting (Variance Alta):

Erro
 |
 |  \                        Treino
 |   \_______
 |    \
 |     \
 |      \___________________ Validacao
 |       \_________________/
 +-------------------------> Amostras de Treino
   Poucas                  Muitas

    Curvas convergem lentamente. Gap significativo.
    Adicionar mais dados PODE melhorar.
    SOLUCAO: regularizacao ou mais dados.
```

### 1.7 Exemplo Quantitativo

Considere um polinomio ajustado a dados ruidosos:

```text
Dados verdadeiros: y = 2*x + 3 + ruido

Modelo 1 (grau 1 — adequado):
    y_hat = 2.01*x + 2.98
    Treino MSE: 0.85
    Validacao MSE: 0.91
    Gap: 0.06

Modelo 2 (grau 5 — overfitting):
    y_hat = 2.0*x + 3.1 - 0.5*x^2 + 0.8*x^3 - 0.3*x^4 + 0.1*x^5
    Treino MSE: 0.12
    Validacao MSE: 45.3
    Gap: 45.18

Modelo 3 (grau 15 — overfitting severo):
    y_hat = 2.0*x + 3.0 + termos de grau 2 a 15
    Treino MSE: 0.001
    Validacao MSE: 1234.7
    Gap: 1234.699
```

### 1.8 Regularizacao como Solucao

A regularizacao e o conjunto de tecnicas projetadas para controlar a complexidade do modelo e reduzir overfitting:

```text
Principio fundamental:
    Adicionar informacao extra ao treinamento para impedir
    que o modelo se ajuste demais ao ruido dos dados.

Formas de regularizacao:
    1. Regularizacao de parametros: penalizar pesos grandes
       (L1, L2, Elastic Net, Weight Decay)
    2. Regularizacao de arquitetura: reduzir capacidade do modelo
       (Dropout, Batch Norm, Layer Norm)
    3. Regularizacao de treinamento: parar cedo, augmentar dados
       (Early Stopping, Data Augmentation)
    4. Regularizacao de saida: suavizar labels
       (Label Smoothing)
```

---

## 2. L1 Regularization (Lasso)

### 2.1 Formula e Definicao

A L1 Regularization, tambem conhecida como Lasso (Least Absolute Shrinkage and Selection Operator), adiciona uma penalidade proporcional ao valor absoluto dos pesos:

```text
Funcao de perda regularizada:

    L_reg = L_original + lambda * sum(|w_i|)

Onde:
    L_original = funcao de perda original (MSE, cross-entropy, etc.)
    lambda = hiperparametro de regularizacao (lambda > 0)
    w_i = peso individual da rede
    sum(|w_i|) = soma dos valores absolutos de todos os pesos

Se houver M pesos:
    L_reg = L_original + lambda * (|w_1| + |w_2| + ... + |w_M|)
```

### 2.2 Derivada e Subgradiente

Para atualizar os pesos via gradient descent, precisamos da derivada da penalidade L1 em relacao a cada peso. Porém, a funcao |w| nao e diferenciavel em w = 0. Usamos o subgradiente:

```text
d/dw (|w|) = sign(w)

Onde sign(w) e a funcao sinal:
    sign(w) = +1,  se w > 0
    sign(w) = -1,  se w < 0
    sign(w) = 0,   se w = 0 (subgradiente no intervalo [-1, 1])
```

Regra de atualizacao com L1:

```text
w_i := w_i - eta * (dL_original/dw_i + lambda * sign(w_i))

Caso w_i > 0:
    w_i := w_i - eta * (dL_original/dw_i + lambda)
    -> Peso diminui por eta*lambda alem do gradiente normal

Caso w_i < 0:
    w_i := w_i - eta * (dL_original/dw_i - lambda)
    -> Peso aumenta por eta*lambda alem do gradiente normal

Caso w_i = 0:
    w_i := 0 (permanece zero se |dL_original/dw_i| <= lambda)
```

### 2.3 Intuicao Geometrica

A intuicao geometrica da L1 Regularization e elegante. Considere o problema de otimizacao:

```text
Minimizar: L(w1, w2) sujeito a |w1| + |w2| <= t

Onde t esta relacionado inversamente com lambda.

O conjunto de restricao |w1| + |w2| <= t forma um LOSANGO no espaco (w1, w2):

         w2
         |
    -----+-----
   /     |     \
  /      |      \
 |       |       |
 |       +-------+----> w1
 |       |       |
  \      |      /
   \     |     /
    -----+-----
         |

Os cantos do losango estao nos eixos (w1=0 ou w2=0).
Os cantos sao os pontos onde a solucao otima mais provavel caira,
porque as curvas de nivel de L(w1,w2) tocam o losango nos cantos.

Result: pesos exatamente zero -> selecao de features.
```

### 2.4 Propriedade de Esparsidade

A propriedade mais importante da L1 Regularization e a **esparsidade**: ela tende a conduzir muitos pesos a exatamente zero.

```text
Mecanismo da esparsidade:

1. Quando |dL/dw| < lambda, o gradiente da penalidade domina
2. O subgradiente empurra w para zero
3. Em w=0, o subgradiente pode ser qualquer valor em [-lambda, lambda]
4. Se o gradiente original nao for forte o suficiente, w permanece zero

Resultado: o modelo seleciona automaticamente quais pesos sao importantes.
Isso e chamado de "feature selection via regularizacao".
```

### 2.5 Exemplo Numerico

```text
Suponha lambda = 0.5 e eta = 0.1:

Peso w = 1.0, gradiente da perda = 0.3

Iteracao 1:
    w := 1.0 - 0.1 * (0.3 + 0.5 * sign(1.0))
    w := 1.0 - 0.1 * (0.3 + 0.5)
    w := 1.0 - 0.08
    w := 0.92

Iteracao 2:
    w := 0.92 - 0.1 * (0.3 + 0.5)
    w := 0.84

... continuando ...

Quando |gradiente da perda| < lambda, o peso converge para zero.

Se o gradiente da perda for 0.1 (fraco):
    w := w - 0.1 * (0.1 + 0.5)
    w := w - 0.06

    O peso diminui constantemente ate cruzar zero,
    e depois se estabiliza em zero (ou perto).
```

### 2.6 Quando Usar L1

```text
Vantagens:
    - Selecao de feature automatica (pesos = 0 sao removidos)
    - Modelo interpretavel (apenas features importantes sobram)
    - Computacionalmente simples
    - Eficaz quando apenas algumas features sao relevantes

Desvantagens:
    - Instavel com features correlacionadas (escolhe uma aleatoriamente)
    - Difil de usar com gradientes estocasticos (subgradiente nao e suave)
    - Para M > N (mais features que amostras), seleciona no maximo N features

Quando usar:
    - Dataset com muitas features, mas poucas sao relevantes
    - Quando interpretabilidade e importante
    - Como pre-processamento antes de outros modelos
```

---

## 3. L2 Regularization (Ridge)

### 3.1 Formula e Definicao

A L2 Regularization, tambem conhecida como Ridge Regression, adiciona uma penalidade proporcional ao quadrado dos pesos:

```text
Funcao de perda regularizada:

    L_reg = L_original + lambda * sum(w_i^2)

Onde:
    lambda = hiperparametro de regularizacao (lambda > 0)
    w_i^2 = quadrado de cada peso individual

Equivalente ao termo:
    L_reg = L_original + (lambda/2) * ||w||^2

Onde ||w||^2 = soma dos quadrados de todos os pesos (norma L2 ao quadrado)
```

### 3.2 Derivada

A derivada da L2 Regularization e simples e continua:

```text
d/dw (w^2) = 2*w

Portanto:
    d/dw (lambda * w^2) = 2 * lambda * w

Regra de atualizacao:
    w_i := w_i - eta * (dL_original/dw_i + 2 * lambda * w_i)
```

### 3.3 Intuicao Geometricica

```text
Minimizar: L(w1, w2) sujeito a w1^2 + w2^2 <= t

O conjunto de restricao w1^2 + w2^2 <= t forma um CIRCULO:

         w2
         |
    -----+-----
   /     |     \
  /      |      \
 |   +-------+  |
 |   |   |   |  |----> w1
 |   +-------+  |
  \      |      /
   \     |     /
    -----+-----
         |

Os cantos do circulo NAO estao nos eixos.
A solucao otima geralmente NAO tem pesos exatamente zero.
Todos os pesos sao reduzidos proporcionalmente ("shrinkage").
```

### 3.4 Propriedade de Contracao (Weight Shrinkage)

Diferente da L1, a L2 nao produz pesos exatamente zero. Ela contrai todos os pesos proporcionalmente:

```text
Na formula de atualizacao:
    w_i := w_i * (1 - 2 * eta * lambda) - eta * dL_original/dw_i

O termo (1 - 2 * eta * lambda) e um fator de contracao.
Se 2 * eta * lambda < 1, o peso e multiplicado por um numero menor que 1.

Exemplo:
    eta = 0.01, lambda = 0.1
    Fator de contracao = 1 - 2 * 0.01 * 0.1 = 1 - 0.002 = 0.998

    w = 5.0 -> 5.0 * 0.998 = 4.99
    w = 0.1 -> 0.1 * 0.998 = 0.0998

Todos os pesos diminuem, mas os maiores diminuem mais em valor absoluto.
```

### 3.5 Equivalencia com Weight Decay

Para o SGD simples, a L2 Regularization e equivalente ao weight decay:

```text
Weight Decay:
    w := w - eta * (dL/dw + lambda * w)
    w := w * (1 - eta * lambda) - eta * dL/dw

L2 Regularization:
    L_reg = L + (lambda/2) * w^2
    dL_reg/dw = dL/dw + lambda * w
    w := w - eta * (dL/dw + lambda * w)

SAO IDENTICOS para SGD puro.

PORÉM, para adaptativos (Adam, AdaGrad), SAO DIFERENTES!
Ver secao 11 (Weight Decay) para detalhes.
```

### 3.6 Analise Bayesianica

A L2 Regularization tem uma interpretacao bayesiana elegante:

```text
Interpretacao bayesiana:

    L1 Regularization = prior Laplaciano nos pesos
        p(w) = (1/2b) * exp(-|w|/b)
        -> concentra massa em w = 0 (esparsidade)

    L2 Regularization = prior Gaussiano nos pesos
        p(w) = (1/sqrt(2*pi*s^2)) * exp(-w^2 / (2*s^2))
        -> concentra massa perto de 0, mas nunca exatamente 0

Onde:
    b (L1) e s^2 (L2) estao relacionados inversamente com lambda
    lambda grande = prior estreto = mais regularizacao
    lambda pequeno = prior largo = menos regularizacao
```

### 3.7 Exemplo Numerico

```text
Suponha lambda = 0.1, eta = 0.01:

Peso w = 5.0, gradiente da perda = 0.3

Iteracao 1:
    w := 5.0 - 0.01 * (0.3 + 2 * 0.1 * 5.0)
    w := 5.0 - 0.01 * (0.3 + 1.0)
    w := 5.0 - 0.013
    w := 4.987

Iteracao 2:
    w := 4.987 - 0.01 * (0.3 + 2 * 0.1 * 4.987)
    w := 4.987 - 0.01 * (0.3 + 0.9974)
    w := 4.987 - 0.01297
    w := 4.974

O peso converge para um valor pequeno, mas NUNCA exatamente zero.
A velocidade de contracao e proporcional ao valor do peso.
```

### 3.8 Quando Usar L2

```text
Vantagens:
    - Diferenciavel em todo lugar (sem problema de subgradiente)
    - Funciona bem com features correlacionadas
    - Solucao unica e estavel
    - Adequada para a maioria dos cenarios

Desvantagens:
    - Nao produz esparsidade (todos os pesos permanecem nao-nulos)
    - Nao faz selecao de feature automatica
    - Menos interpretavel quando ha muitas features

Quando usar:
    - Cenario geral de regularizacao
    - Features correlacionadas
    - Quando NAO se quer eliminacao de features
    - Combinacao com outros metodos (Elastic Net)
```

---

## 4. Elastic Net

### 4.1 Formula e Motivacao

O Elastic Net combina as penalidades L1 e L2, herdando as vantagens de ambas:

```text
Funcao de perda regularizada:

    L_reg = L_original + lambda_1 * sum(|w_i|) + lambda_2 * sum(w_i^2)

Onde:
    lambda_1 = coeficiente L1 (controle esparsidade)
    lambda_2 = coeficiente L2 (controle contracao)

Forma alternativa com parametro de mistura alpha:

    L_reg = L_original + lambda * [alpha * sum(|w_i|) + (1-alpha)/2 * sum(w_i^2)]

Onde:
    lambda = intensidade total de regularizacao
    alpha = propcao de L1 (0 <= alpha <= 1)
    alpha = 0 -> pura L2 (Ridge)
    alpha = 1 -> pura L1 (Lasso)
    alpha = 0.5 -> mix igualitario
```

### 4.2 Derivada

```text
Gradiente da penalidade Elastic Net:

    d/dw_i [lambda_1 * |w_i| + lambda_2 * w_i^2]
    = lambda_1 * sign(w_i) + 2 * lambda_2 * w_i

Regra de atualizacao:

    w_i := w_i - eta * (dL_original/dw_i + lambda_1 * sign(w_i) + 2 * lambda_2 * w_i)
```

### 4.3 Intuicao Geometrica

```text
O conjunto de restricao do Elastic Net forma uma forma "arredondada"
entre o losango (L1) e o circulo (L2):

         w2
         |
    -----+-----
   /     |     \
  /      |      \     Forma intermediaria:
 |  +--------+   |   - Mais suave que L1
 |  |   /    |   |--> - Mais pontiaguda que L2
 |  +--------+   |
  \      |      /    Pode produzir pesos zero
   \     |     /     mas mais estavel que L1 puro
    -----+-----
         |
```

### 4.4 Propriedades do Elastic Net

```text
1. Selecao de feature (herdado da L1):
    - Pode conduzir pesos a zero
    - Mas mais estavel que L1 puro com features correlacionadas

2. Contracao suave (herdado da L2):
    - Agrupa features correlacionadas
    - Nao escolhe apenas uma arbitrariamente

3. Estabilidade:
    - Com M > N, L1 seleciona no maximo N features
    - Elastic Net nao tem essa restricao
    - Mais robusto a colinearidade

4. Grupo de selecao:
    - Features correlacionadas tendem a entrar ou sair juntas
    - Propriedade herda do componente L2
```

### 4.5 Escolha de alpha e lambda

```text
Estrategia de selecao:

1. Comece com alpha = 0.5 (L1 e L2 igualitarios)
2. Use cross-validation para encontrar lambda otimo
3. Se muitas features sao irrelevantes -> aumente alpha
4. Se features sao correlacionadas -> diminua alpha
5. Use coordinate descent para otimizacao (mais eficiente que GD)

Cross-validation tipico:
    alpha in {0.1, 0.3, 0.5, 0.7, 0.9}
    lambda in {0.001, 0.01, 0.1, 1.0, 10.0}
    -> Grid search com 5-fold CV
    -> Escolher (alpha, lambda) com menor erro de validacao
```

---

## 5. Dropout

### 5.1 Definicao e Motivacao

Dropout e uma tecnica de regularizacao que desativa aleatoriamente neuronios durante o treinamento. A ideia e que ao impedir que neuronios coloquem em coadapto (co-adaptation), o modelo e forçado a aprender representacoes mais robustas e redundantes.

```text
Dropout:
    Durante cada forward pass de treinamento, cada neuronio e
    "desligado" (setado a zero) com probabilidade p.
    Isso force a rede a nao depender de nenhum neuronio especifico.
```

### 5.2 Treino vs Inferencia

A diferenca critica entre treino e inferencia e:

```text
Treino com Dropout:
    1. Para cada mini-batch, cada neuronio tem probabilidade p de ser desligado
    2. Os pesos dos neuronios ativos sao escalados por 1/(1-p) (inverted dropout)
    3. Isso garante que a media de saida do neuronio se mantem igual

Inferencia (sem Dropout):
    1. TODOS os neuronios estao ativos
    2. Nenhuma escala adicional e necessaria (ja foi aplicada no treino)
    3. Saida identica a rede media (theoretical guarantee)
```

### 5.3 Inverted Dropout

O inverted dropout e a implementacao padrao porque mantem a escala de inferencia identica a de treino:

```text
Algoritmo de Inverted Dropout:

Durante treino (forward pass):
    1. Gerar mascara aleatoria: M_i ~ Bernoulli(1-p) para cada neuronio i
       M_i = 1 com probabilidade (1-p)
       M_i = 0 com probabilidade p

    2. Aplicar mascara: h_i = h_i * M_i

    3. Escalar pelas ativas: h_i = h_i / (1-p)

    4. O neuronio desligado tem saida 0, mas os ativos tem saida
       MAIOR que o normal para compensar

Durante inferencia (forward pass):
    h_i = h_i (nenhuma mudanca)
    Nao ha mascara, nao ha escala

Por que funciona:
    E[h_i] = E[h_i * M_i / (1-p)]
           = E[h_i] * E[M_i] / (1-p)    (independencia)
           = E[h_i] * (1-p) / (1-p)
           = E[h_i]

    A media e preservada exatamente!
```

### 5.4 Formulacao Matematica

```text
Forward pass com Dropout:

    z = W * x + b                  (pre-ativacao)
    h = f(z)                       (ativacao)
    r_i ~ Bernoulli(1-p)           (mascara aleatoria)
    h_hat_i = h_i * r_i / (1-p)   (aplicar dropout)
    saida = W_out * h_hat + b_out  (camada de saida)

Onde f e a funcao de ativacao e p e a taxa de dropout (tipicamente 0.2 a 0.5).

Backward pass com Dropout:
    dL/dh_hat = dL/dsaida * W_out^T
    dL/dh = dL/dh_hat * r / (1-p)   (aplicar mesma mascara)
    Continua normalmente...
```

### 5.5 Por Que Dropout Funciona

```text
Explicacoes teoricas:

1. Ensemble Approximation:
    - Cada forward pass usa uma sub-rede diferente
    - Com N neuronios, existem 2^N sub-redes possiveis
    - Dropout treina implicitamente um ensemble de 2^N modelos
    - Na inferencia, a saida e a media ponderada desses modelos

2. Co-adaptation Prevention:
    - Sem dropout: neuronios podem se especializar em compensar erros de outros
    - Com dropout: cada neuronio deve ser util por si so
    - Resultado: representacoes mais robustas

3. Noise Injection:
    - Dropout injeta ruido nas representacoes intermediarias
    - Ruido similar a regularizacao gaussiana nos pesos
    - Forca o modelo a ignorar pequenas perturbacoes

4. Esparsidade Implicita:
    - A mascara de dropout cria esparsidade temporaria
    - Similar a L1, mas sem depender da magnitude dos pesos
```

### 5.6 Hiperparametros Importantes

```text
Taxa de dropout (p):

    Camadas de entrada:  p = 0.1 a 0.2 (pouco dropout na entrada)
    Camadas ocultas:     p = 0.3 a 0.5 (mais dropout intermediario)
    Camadas proximas da saida: p = 0.5 (mais agressivo)

Regras praticas:
    - Camadas maiores recebem mais dropout
    - Se o modelo esta overfitting, aumente p
    - Se o modelo esta underfitting, diminua p
    - Convolutional layers: p = 0.1 a 0.3 (menos dropout)
    - Fully connected layers: p = 0.3 a 0.5 (mais dropout)
    - Nunca usar dropout na camada de saida
```

### 5.7 Dropout com Mini-Batchs

```text
Implementacao com mini-batchs de tamanho B:

Para cada neuronio i no mini-batch:
    1. Gerar B valores aleatorios: r_ij ~ Bernoulli(1-p), j = 1..B
    2. Aplicar mascara: h_ij = h_ij * r_ij / (1-p)

Em forma vetorial:
    R = Bernoulli((1-p), shape=(B, n_neurons))
    H = H * R / (1-p)

Isso e eficiente porque opera sobre o batch inteiro.
```

---

## 6. Batch Normalization

### 6.1 Internal Covariate Shift

Batch Normalization foi motivado pelo problema de **internal covariate shift**: a distribuicao dos inputs de cada camada muda durante o treinamento porque os pesos das camadas anteriores estao sendo atualizados.

```text
Internal Covariate Shift:

    Camada l recebe x^(l) = h^(l-1) (saida da camada anterior)
    Quando os pesos da camada l-1 mudam, a distribuicao de x^(l) muda
    Isso obriga a camada l a constantemente se adaptar a nova distribuicao
    Resultado: treinamento mais ludo e instavel

Solucao do Batch Normalization:
    Normalizar os inputs de cada camada para ter media 0 e variancia 1
    Isso estabiliza as distribuicoes durante todo o treinamento
```

### 6.2 Formula Forward (Treino)

```text
Para um mini-batch B = {x_1, x_2, ..., x_m}:

1. Calcular media do mini-batch:
    mu_B = (1/m) * sum(x_i)  para i = 1 ate m

2. Calcular variancia do mini-batch:
    sigma_B^2 = (1/m) * sum((x_i - mu_B)^2)  para i = 1 ate m

3. Normalizar:
    x_hat_i = (x_i - mu_B) / sqrt(sigma_B^2 + epsilon)

4. Escalar e deslocar (affine transformation):
    y_i = gamma * x_hat_i + beta

Onde:
    gamma = parametro de escala (aprendido)
    beta = parametro de deslocamento (aprendido)
    epsilon = constante numerica para evitar divisao por zero
              (tipicamente 1e-5)
```

### 6.3 Formula Backward

```text
Dado dy_i (gradiente da saida), calcular gradientes:

1. Gradiente em relacao a x_hat:
    dx_hat_i = dy_i * gamma

2. Gradiente da variancia:
    dsigma^2 = sum(dx_hat_i * (x_i - mu_B) * (-1/2) * (sigma^2 + eps)^(-3/2))

3. Gradiente da media:
    dmu_B = sum(dx_hat_i * (-1/sqrt(sigma^2 + eps))) + dsigma^2 * mean(-2 * (x_i - mu_B))

4. Gradiente em relacao a x (entrada original):
    dx_i = dx_hat_i / sqrt(sigma^2 + eps) + dsigma^2 * 2 * (x_i - mu_B) / m + dmu_B / m

5. Gradientes dos parametros gamma e beta:
    dgamma = sum(dy_i * x_hat_i)
    dbeta = sum(dy_i)
```

### 6.4 Medias Moveis (Running Statistics)

Durante inferencia, nao temos mini-batch, entao usamos medias moveis:

```text
Estatisticas durante treino:

    running_mean = (1-momentum) * running_mean + momentum * mu_B
    running_var = (1-momentum) * running_var + momentum * sigma_B^2

Onde:
    momentum = tipicamente 0.1 (ou 0.9 para media movel)
    running_mean comeca em 0
    running_var comeca em 1

Durante inferencia:
    x_hat = (x - running_mean) / sqrt(running_var + epsilon)
    y = gamma * x_hat + beta

Nao ha aleatoriedade, resultado deterministico.
```

### 6.5 Beneficios da Batch Normalization

```text
1. Treinamento mais rapido:
    - Permite taxas de aprendizado maiores
    - Reduz o numero de iteracoes necessarias

2. Reducao de internal covariate shift:
    - Estabiliza as distribuicoes intermediarias
    - Facilita a propagacao de gradientes

3. Regularizacao incidental:
    - A media e variancia do mini-batch injetam ruido
    - Cada amostra e normalizada com estatisticas diferentes
    - Isso funciona como uma forma de regularizacao leve

4. Reducao da necessidade de dropout:
    - Em muitos cenarios, BN substitui dropout
    - Geralmente usado juntos com dropout baixo (0.1-0.2)

5. Inicializacao menos critica:
    - A normalizacao torna a rede menos sensivel a inicializacao
    - Redes profundas treinam mais facilmente
```

### 6.6 Batch Normalization com Convolucoes

```text
Para camadas convolucionais:

    Cada canal tem seus proprios gamma e beta
    A media e variancia sao calculadas por canal (feature map)

    Entrada: (batch, channels, height, width)
    media por canal: mu_c = mean sobre (batch, height, width) para canal c
    var por canal: sigma_c^2 = var sobre (batch, height, width) para canal c

    Normalizacao:
        x_hat_bchw = (x_bchw - mu_c) / sqrt(sigma_c^2 + eps)

    Escala/deslocamento:
        y_bchw = gamma_c * x_hat_bchw + beta_c

    Total de parametros: 2 * num_channels (gamma e beta por canal)
```

---

## 7. Layer Normalization

### 7.1 Diferenca Fundamental em Relacao a Batch Norm

Layer Normalization normaliza ao longo das features (eixo dos canais) em vez de ao longo do batch. Isso e especialmente importante para redes recorrentes e transformers.

```text
Batch Normalization:
    Normaliza ao longo do BATCH para cada feature
    mu = media sobre (batch_size, ) para cada feature
    Para amostra individual, a normalizacao depende de todo o batch

Layer Normalization:
    Normaliza ao longo das FEATURES para cada amostra
    media = media sobre (n_features, ) para cada amostra
    Cada amostra e normalizada independentemente do batch
```

### 7.2 Formula

```text
Para uma amostra x = (x_1, x_2, ..., x_n) (vetor de features):

1. Calcular media sobre as features:
    mu = (1/n) * sum(x_i)  para i = 1 ate n

2. Calcular variancia sobre as features:
    sigma^2 = (1/n) * sum((x_i - mu)^2)  para i = 1 ate n

3. Normalizar:
    x_hat_i = (x_i - mu) / sqrt(sigma^2 + epsilon)

4. Escalar e deslocar:
    y_i = gamma_i * x_hat_i + beta_i

Diferenca-chave da Batch Norm:
    - BN: mu e sigma sao escalares por canal, compartilhados pelo batch
    - LN: mu e sigma sao calculados por AMOSTRA, para cada amostra individualmente
```

### 7.3 Backward Pass

```text
Dado dy_i (gradiente da saida):

1. dx_hat_i = dy_i * gamma_i

2. dsigma^2 = sum(dx_hat_i * (x_i - mu) * (-1/2) * (sigma^2 + eps)^(-3/2))

3. dmu = sum(dx_hat_i * (-1/sqrt(sigma^2 + eps)))

4. dx_i = dx_hat_i / sqrt(sigma^2 + eps) + dsigma^2 * 2 * (x_i - mu) / n + dmu / n

5. dgamma_i = dy_i * x_hat_i
6. dbeta_i = dy_i
```

### 7.4 Por Que Transformers Preferem Layer Normalization

```text
Razoes para usar Layer Norm em transformers:

1. Independencia do batch:
    - Em inferencia, cada amostra e processada individualmente
    - BN requer batch para calcular medias
    - LN funciona com batch = 1

2. Sequencias de comprimento variavel:
    - Transformers processam sequencias de tamanhos diferentes
    - BN teria estatisticas diferentes por posicao da sequencia
    - LN e uniforme em todas as posicoes

3. Treinamento com batchs pequenos:
    - Em NLP, batchs sao frequentemente pequenos (limitacao de memoria)
    - BN e instavel com batchs pequenos (estatisticas imprecisas)
    - LN e sempre estavel

4. Normalizacao no eixo correto:
    - Em transformers, cada token deve ser normalizado individualmente
    - Isso e exatamente o que LN faz
    - BN normalizaria tokens diferentes juntamente

5. Empirico:
    - Transformers com BN performam significativamente pior
    - LN e o padrao em BERT, GPT, e todos os transformers modernos
```

### 7.5 RMS Normalization (RMSNorm)

```text
Variacao simplificada da Layer Normalization:

    x_hat_i = x_i / sqrt((1/n) * sum(x_j^2) + epsilon)
    y_i = gamma_i * x_hat_i

Diferencas:
    - NAO centraliza (nao subtrai a media)
    - Apenas normaliza pela norma L2
    - Mais eficiente computacionalmente
    - Performance similar na pratica
    - Usado em LLaMA, T5, e outros modelos recentes
```

---

## 8. Early Stopping

### 8.1 Principio

Early Stopping e a forma mais simples e eficaz de regularizacao. A ideia e parar o treinamento quando a performance de validacao comeca a piorar, mesmo que a performance de treino continue melhorando.

```text
Early Stopping:
    Monitore a perda de validacao durante o treinamento.
    Quando a perda de validacao para de diminuir (ou comeca a aumentar)
    por um numero definido de epocas (paciencia), pare o treinamento.
    Restaure os pesos da epoca com menor perda de validacao.
```

### 8.2 Algoritmo

```text
Early Stopping:

    melhor_validacao = infinito
    paciencia = P (ex: 10 epocas)
    contador = 0
    melhores_pesos = None

    para cada epoca:
        treinar modelo por uma epoca completa
        calcular loss_validacao

        se loss_validacao < melhor_validacao:
            melhor_validacao = loss_validacao
            melhores_pesos = copia dos pesos atuais
            contador = 0
        senao:
            contador += 1

        se contador >= paciencia:
            restaurar melhores_pesos
            parar treinamento
            break
```

### 8.3 Hiperparametros

```text
Paciencia (patience):

    paciencia muito pequena (ex: 2-3):
        - Para muito cedo
        - Pode perder uma melhoria posterior
        - Risco de underfitting

    paciencia muito grande (ex: 100+):
        - Nao para a tempo
        - Waste de tempo computacional
        - Pode voltar a um ponto subotimo

    paciencia tipica: 5 a 20 epocas

Consideracoes:
    - Paciencia deve ser proporcional a taxa de aprendizado
    - LR alto -> fluctuacoes maiores -> paciencia maior
    - LR baixo -> convergencia lenta -> paciencia pode ser menor
    - Em conjuntos pequenos, usar validacao hold-out (nao cross-val) para early stopping
```

### 8.4 Relacao com Regularizacao L2

```text
Early Stopping como regularizacao:

    Teorema (Sjoberg & Wahba, 1999):
        Early stopping com K iteracoes de gradient descent
        e equivalente a L2 regularization com lambda
        proporcional a 1/K

    Intuicao:
        - K pequeno (parar cedo): lambda efetivo alto -> mais regularizacao
        - K grande (nunca parar): lambda efetivo zero -> sem regularizacao

    Na pratica:
        - Early stopping e mais facil de usar que L2
        - Nao requer ajustar lambda
        - Mas e menos preciso que regularizacao explicita
        - Geralmente usado em COMBINACAO com L2 ou dropout
```

### 8.5 Variantes

```text
Variante 1 — Save Best:
    Sempre salva os pesos da melhor epoca de validacao.
    Mais comum e simples.

Variante 2 — Snapshot Ensemble:
    Salva pesos em multiplos momentos de minimo local.
    Usa todos os snapshots como ensemble na inferencia.
    Mais robusto, mas requer mais memoria.

Variante 3 — Cyclic Learning Rates + Early Stopping:
    Combina taxas de aprendizado ciclicas com early stopping.
    LR alto permite escapar de minimos locais.
    Early stopping previne overfitting.

Variante 4 — ReduceLROnPlateau:
    Quando a validacao para de melhorar, reduz o LR.
    Se apos reduzir o LR continua sem melhoria, entao para.
    Mais flexivel que early stopping puro.
```

### 8.6 Implementacao Pratica

```text
Monitoramento com validacao:

    1. Dividir dados em treino, validacao, teste (ex: 70/15/15)
    2. Usar VALIDACAO para early stopping
    3. NUNCA usar teste para early stopping (isso e data leakage)
    4. Usar os pesos do melhor checkpoint de validacao
    5. Reportar performance final no TESTE (uma unica vez)

Cuidados:
    - Se validacao e muito pequena, early stopping pode ser instavel
    - Usar stratified split para manter distribuicao de classes
    - Em time series, usar split temporal (nao aleatorio)
    - Guardar o melhor checkpoint e NUNCA re-treinar
```

---

## 9. Data Augmentation

### 9.1 Principio

Data Augmentation aumenta artificialmente o tamanho do conjunto de treinamento aplicando transformacoes que preservam a semantica dos dados. Isso reduz overfitting ao apresentar variedade ao modelo.

```text
Data Augmentation:
    Criar novas amostras de treinamento a partir das existentes
    usando transformacoes que NAO alteram o rotulo/classe.

    Cada transformacao gera uma nova versao dos dados.
    O modelo ve a mesma informacao sob diferentes "angulos".
    Result: maior泛化, menos overfitting.
```

### 9.2 Transformacoes para Imagens

```text
1. Rotacao:
    Rotacionar a imagem por um angulo aleatorio theta
    theta ~ Uniform(-max_angle, +max_angle)
    tipicamente max_angle = 15 a 30 graus

2. Flip Horizontal:
    Inverter a imagem horizontalmente
    Funciona para objetos que sao simetricos (pessoas, animais)
    NAO funciona para onde a direcao importa (numero "2", letras)

3. Flip Vertical:
    Inverter a imagem verticalmente
    Menos comum, usado para imagens que nao tem orientacao fixa
    Ex: texturas, padroes abstratos

4. Crop (Recorte):
    Recortar uma porcao aleatoria da imagem
    Depois redimensionar para o tamanho original
    Simula variacao de posicao e escala

5. Translation (Translacao):
    Mover a imagem horizontal/verticalmente
    Simula variacao de posicao

6. Color Jitter:
    Alterar brilho, contraste, saturacao, e tonalidade
    Variacao: brightness ± 20%, contrast ± 20%, saturation ± 20%

7. Noise Injection:
    Adicionar ruido gaussiano ou salt-and-pepper
    ruido ~ N(0, sigma^2)
    sigma tipico: 0.01 a 0.1

8. Random Erasing:
    Apagar retangulos aleatorios da imagem
    Forca o modelo a nao depender de partes especificas
```

### 9.3 Transformacoes para Dados Tabulares

```text
1. Feature Noise:
    Adicionar ruido gaussiano a cada feature
    x_i := x_i + epsilon, epsilon ~ N(0, sigma^2)
    sigma deve ser pequeno relativo a escala da feature

2. Feature Cropping:
    Dropar features aleatoriamente (similar a dropout)
    Mascarar um subconjunto de features

3. Mixup:
    Criar amostras sinteticas interpolando entre duas amostras
    x_new = alpha * x_i + (1-alpha) * x_j
    y_new = alpha * y_i + (1-alpha) * y_j
    alpha ~ Beta(alpha_param, alpha_param)

4. SMOTE:
    Synthetic Minority Over-sampling Technique
    Para dados desbalanceados: gerar amostras sinteticas da classe minoritaria
    Interpolar entre vizinhos mais proximos

5. Gaussian Mixture Sampling:
    Ajustar mistura gaussiana aos dados
    Amostrar novos pontos das distribuicoes ajustadas
```

### 9.4 Transformacoes para Texto

```text
1. Synonym Replacement:
    Substituir palavras por sinônimos
    "O gato comeu o peixe" -> "O felino devorou o peixe"

2. Random Insertion:
    Inserir palavras aleatorias em posicoes aleatorias

3. Random Swap:
    Trocar posicoes de duas palavras

4. Random Deletion:
    Remover palavras aleatoriamente

5. Back Translation:
    Traduzir para outra lingua e depois de volta
    "The cat sat" -> "Le chat etait assis" -> "The cat was sitting"

6. Contextual Augmentation:
    Usar modelo de linguagem para substituir palavras
    Mais conservador que synonym replacement
```

### 9.5 Estrategias de Aplicacao

```text
Estrategia 1 — Aplicar toda epoca:
    Cada epoca, os dados sao transformados novamente
    O modelo ve versoes diferentes a cada epoca
    Mais eficaz, mais custoso

Estrategia 2 — Pre-processamento estatico:
    Criar dataset aumentado uma vez
    Treinar normalmente no dataset aumentado
    Mais simples, menos eficaz

Estrategia 3 — On-the-fly:
    Aplicar transformacoes durante o carregamento
    Nao aumenta o tamanho do dataset em disco
    Bom equilibrio entre eficacia e eficiencia

Estrategia 4 — Strong augmentation:
    Transformacoes mais agressivas
    Usar com batchs maiores
    Regularizacao mais forte

Estrategia 5 — Weak augmentation:
    Transformacoes leves
    Preserva mais a informacao original
    Menor risco de degradar dados
```

---

## 10. Weight Decay

### 10.1 Relacao com L2 Regularization

Weight decay e frequentemente confundido com L2 Regularization, mas sao conceitos diferentes quando aplicados a optimizadores adaptativos.

```text
SGD com L2 Regularization:
    L_reg = L + (lambda/2) * w^2
    gradiente: dL/dw + lambda * w
    atualizacao: w := w - eta * (dL/dw + lambda * w)

SGD com Weight Decay:
    atualizacao: w := w - eta * dL/dw - eta * lambda * w
    equivalente a: w := w * (1 - eta * lambda) - eta * dL/dw

Para SGD puro: SAO IDENTICOS (pela algebra)
Para Adam: SAO DIFERENTES (critico!)
```

### 10.2 Por Que Adam + L2 e Diferente de Adam + Weight Decay

```text
Adam com L2 Regularization:

    1. Calcula gradiente: g = dL/dw + lambda * w
    2. Atualiza momentos: m = beta1*m + (1-beta1)*g
    3. Atualiza variancia: v = beta2*v + (1-beta2)*g^2
    4. Aplica correcao de viés
    5. Atualiza: w := w - eta * m_hat / (sqrt(v_hat) + eps)

    O problema: lambda*w e incluido no calculo de m e v
    Isso distorce os momentos adaptativos!
    O adaptador "absorve" a regularizacao e a enfraquece.

Adam com Weight Decay (AdamW):

    1. Calcula gradiente: g = dL/dw (SEM o termo lambda*w)
    2. Atualiza momentos: m = beta1*m + (1-beta1)*g
    3. Atualiza variancia: v = beta2*v + (1-beta2)*g^2
    4. Aplica correcao de viés
    5. Atualiza: w := w - eta * (m_hat / (sqrt(v_hat) + eps) + lambda * w)

    O peso e decouplado do adaptador
    A regularizacao e aplicada diretamente, sem interferir nos momentos
    Resultado: regularizacao mais forte e mais previsivel
```

### 10.3 AdamW

```text
AdamW:

    m_t = beta1 * m_{t-1} + (1 - beta1) * g_t
    v_t = beta2 * v_{t-1} + (1 - beta2) * g_t^2

    m_hat = m_t / (1 - beta1^t)
    v_hat = v_t / (1 - beta2^t)

    w_t = w_{t-1} - eta * (m_hat / (sqrt(v_hat) + eps) + lambda * w_{t-1})

Diferenca do Adam com L2:
    - Adam+L2: lambda*w afeta m e v (indesejado)
    - AdamW: lambda*w e aplicado diretamente (correto)

Empiricamente:
    - AdamW converge melhor
    - Generaliza melhor
    - E o optimizador padrao para treinar transformers
```

### 10.4 Scheduling de Weight Decay

```text
Weight Decay com Cosine Annealing:

    lambda_t = lambda_min + 0.5 * (lambda_max - lambda_min) * (1 + cos(pi * t / T))

    Onde:
        lambda_min = valor minimo de weight decay
        lambda_max = valor maximo de weight decay
        t = epoca atual
        T = total de epocas

    Comeca com lambda alto (regularizacao forte)
    Termina com lambda baixo (regularizacao fraca)
    Permite que o modelo se estabilize no final do treinamento
```

---

## 11. Label Smoothing

### 11.1 Formula

Label Smoothing substitui os labels hard (one-hot) por labels suavizados, prevenindo que o modelo se torne excessivamente confiante em suas predicoes.

```text
Labels originais (hard targets):
    y = [0, 0, 0, 1, 0, 0, 0, 0, 0, 0]  (classe 3)

Labels suavizados (smoothed targets):
    y_smooth = [(1-epsilon)/K, (1-epsilon)/K, (1-epsilon)/K,
                epsilon + (1-epsilon)/K,
                (1-epsilon)/K, ..., (1-epsilon)/K]

Onde:
    K = numero de classes
    epsilon = hiperparametro de smoothing (tipicamente 0.1)

Exemplo com K=10 e epsilon=0.1:
    y_smooth[correta] = 0.1 + 0.9/10 = 0.19
    y_smooth[outras] = 0.9/10 = 0.09

A soma continua sendo 1.0 (distribuicao de probabilidade).
```

### 11.2 Funcao de Perda com Label Smoothing

```text
Cross-Entropy com Label Smoothing:

    L_smooth = -sum(y_smooth_k * log(p_k))

    Onde:
        y_smooth_k = label suavizado para classe k
        p_k = probabilidade predita para classe k

Expansao:
    L_smooth = -(1-epsilon) * sum(y_hard_k * log(p_k)) - epsilon * sum(log(p_k))
             = (1-epsilon) * L_CE + epsilon * H_unif

    Onde:
        L_CE = cross-entropy original
        H_unif = entropia da distribuicao uniforme = log(K)

    O segundo termo e constante!
    Mas o efeito e significativo: penaliza predicoes muito confiantes.
```

### 11.3 Por Que Label Smoothing Funciona

```text
Efeitos de label smoothing:

1. Reduz overconfidence:
    - O modelo nao pode prever p_classe_correta = 1.0
    - Isso impede logits de crescer indefinidamente
    - Representacoes mais compactas e generalizaveis

2. Melhora generalizacao:
    - Evita minimizar cross-entropy com "extrema prejudice"
    - Forca o modelo a capturar relacoes entre classes
    - Representacoes mais uniformes no espacio latente

3. Melhora calibracao:
    - Predicoes mais calibradas (probabilidades proximas da realidade)
    - Util para decisoes de risco (medicina, financas)

4. Efeito similar a regularizacao:
    - L_smooth = (1-epsilon) * L_CE + epsilon * constante
    - Funciona como uma forma suave de multi-label classification
    - O modelo aprende a distribuicao真 dos dados, nao apenas o label

5. Melhora embeddings:
    - Representacoes mais uniformes e mais distantes entre si
    - Melhor performance em retrieval e clustering
```

### 11.4 Valores Tipicos

```text
Epsilon (smoothing factor):

    epsilon = 0.0: sem smoothing (labels originais)
    epsilon = 0.1: smoothing leve (mais comum)
    epsilon = 0.2: smoothing moderado
    epsilon = 0.3: smoothing forte (pode ser demais)

    Tipicamente: 0.05 a 0.2

Recomendacoes:
    - Classificacao de imagens: epsilon = 0.1
    - Treinamento de transformers: epsilon = 0.1
    - Classificacao medical: epsilon = 0.05 (cuidadoso)
    - NLP com muitas classes: epsilon = 0.1 a 0.2
```

---

## 12. Comparacao de Tecnicas

### 12.1 Tabela Comparativa

```text
+---------------------+-------------+---------------+------------+-------------------+
| Tecnica             | Onde Aplica | Custo Comput. | Esparsidade| Interpretabilidade |
+---------------------+-------------+---------------+------------+-------------------+
| L1 (Lasso)          | Pesos       | Baixo          | Sim        | Alta              |
| L2 (Ridge)          | Pesos       | Baixo          | Nao        | Media             |
| Elastic Net         | Pesos       | Baixo          | Parcial    | Media             |
| Dropout             | Neuronios   | Medio          | Temporaria | Baixa             |
| Batch Normalization | Saidas      | Medio          | Nao        | Baixa             |
| Layer Normalization | Saidas      | Medio          | Nao        | Baixa             |
| Early Stopping      | Treino      | Nenhum extra   | Nao        | N/A               |
| Data Augmentation   | Dados       | Alto (IO)      | Nao        | N/A               |
| Weight Decay        | Pesos       | Baixo          | Nao        | Media             |
| Label Smoothing     | Labels      | Baixo          | Nao        | N/A               |
+---------------------+-------------+---------------+------------+-------------------+
```

### 12.2 Quando Usar Cada Tecnica

```text
Recomendacoes por cenario:

Cenario 1 — Dados tabulares com muitas features:
    -> L1 ou Elastic Net (selecao de feature)
    -> Early Stopping
    -> Weight Decay

Cenario 2 — Classificacao de imagens (CNN):
    -> Data Augmentation (essencial)
    -> Batch Normalization
    -> Dropout (p=0.2 a 0.5)
    -> Weight Decay
    -> Label Smoothing

Cenario 3 — NLP com Transformers:
    -> Layer Normalization (essencial)
    -> Dropout (p=0.1 a 0.3)
    -> Weight Decay (AdamW)
    -> Label Smoothing
    -> Data Augmentation (back translation)

Cenario 4 — Regressao:
    -> L2 Ridge (padrao)
    -> Elastic Net (se M > N ou features correlacionadas)
    -> Early Stopping
    -> Data Augmentation (noise injection)

Cenario 5 — Dados muito limitados:
    -> Data Augmentation (critico)
    -> Early Stopping (critico)
    -> Regularizacao forte (lambda alto, dropout alto)
    -> Cross-validation em vez de hold-out

Cenario 6 — Modelo muito grande (overfitting severo):
    -> Combinar: L2 + Dropout + Batch Norm + Early Stopping + Augmentation
    -> Label Smoothing
    -> Weight Decay com AdamW
```

### 12.3 Custo Computacional Detalhado

```text
Analise de overhead por tecnica:

L1/L2 Regularization:
    Forward: +1 operacao por peso (adição da penalidade)
    Backward: +1 operacao por peso (gradiente da penalidade)
    Overhead: ~0.1% (quase nada)

Dropout:
    Forward: gerar mascara aleatoria + multiplicacao por mascara
    Backward: mesma mascara aplicada
    Overhead: ~5-15% (depende do numero de neuronios)

Batch Normalization:
    Forward: calcular media, variancia, normalizar, escalar/deslocar
    Backward: gradientes dos 4 passos + gradientes de gamma/beta
    Overhead: ~10-20% (calculo de estatisticas)

Layer Normalization:
    Forward: similar a BN mas por amostra
    Backward: similar a BN
    Overhead: ~10-20%

Early Stopping:
    Custo: NENHUM (apenas monitoramento)
    Savings: REDUZ tempo de treinamento

Data Augmentation:
    Custo principal: IO (leitura e transformacao de dados)
    CPU: transformacoes em paralelo
    Overhead: ~20-100% (depende das transformacoes)

Weight Decay:
    Mesmo que L2: ~0.1%

Label Smoothing:
    Custo: NENHUM (modificacao nos labels)
    Overhead: ~0%
```

---

## 13. Implementacao em C++

### 13.1 Estrutura Geral

```cpp
// regularization.h
#pragma once
#include <vector>
#include <random>
#include <cmath>
#include <algorithm>

// L2 regularization applied during backpropagation
class L2Regularization {
public:
    explicit L2Regularization(float lambda) : lambda_(lambda) {}

    // Compute regularization loss
    float computeLoss(const std::vector<float>& weights) const {
        float loss = 0.0f;
        for (float w : weights) {
            loss += w * w;
        }
        return 0.5f * lambda_ * loss;
    }

    // Compute gradient of regularization term
    float computeGradient(float weight) const {
        return lambda_ * weight;
    }

private:
    float lambda_;
};

// L1 regularization applied during backpropagation
class L1Regularization {
public:
    explicit L1Regularization(float lambda) : lambda_(lambda) {}

    float computeLoss(const std::vector<float>& weights) const {
        float loss = 0.0f;
        for (float w : weights) {
            loss += std::abs(w);
        }
        return lambda_ * loss;
    }

    // Subgradient of L1
    float computeGradient(float weight) const {
        if (weight > 0.0f) return lambda_;
        if (weight < 0.0f) return -lambda_;
        return 0.0f; // subgradient at 0 is in [-lambda, lambda]
    }

private:
    float lambda_;
};

// Elastic Net combining L1 and L2
class ElasticNet {
public:
    ElasticNet(float lambda1, float lambda2)
        : lambda1_(lambda1), lambda2_(lambda2) {}

    float computeLoss(const std::vector<float>& weights) const {
        float l1_loss = 0.0f;
        float l2_loss = 0.0f;
        for (float w : weights) {
            l1_loss += std::abs(w);
            l2_loss += w * w;
        }
        return lambda1_ * l1_loss + 0.5f * lambda2_ * l2_loss;
    }

    float computeGradient(float weight) const {
        float l1_grad = 0.0f;
        if (weight > 0.0f) l1_grad = lambda1_;
        else if (weight < 0.0f) l1_grad = -lambda1_;

        float l2_grad = lambda2_ * weight;
        return l1_grad + l2_grad;
    }

private:
    float lambda1_;
    float lambda2_;
};
```

### 13.2 Dropout Layer

```cpp
// dropout.h
#pragma once
#include <vector>
#include <random>

class Dropout {
public:
    Dropout(float probability, unsigned seed = 42)
        : probability_(probability),
          mask_(),
          engine_(seed),
          dist_(0.0f, 1.0f) {}

    // Forward pass during training
    std::vector<float> forwardTrain(const std::vector<float>& input) {
        mask_.resize(input.size());
        std::vector<float> output(input.size());
        float scale = 1.0f / (1.0f - probability_);

        for (size_t i = 0; i < input.size(); ++i) {
            float r = dist_(engine_);
            mask_[i] = (r >= probability_) ? 1.0f : 0.0f;
            output[i] = input[i] * mask_[i] * scale;
        }
        return output;
    }

    // Forward pass during inference (no dropout)
    std::vector<float> forwardInference(const std::vector<float>& input) {
        return input; // identity, no scaling needed
    }

    // Backward pass
    std::vector<float> backward(const std::vector<float>& gradOutput) {
        std::vector<float> gradInput(gradOutput.size());
        float scale = 1.0f / (1.0f - probability_);
        for (size_t i = 0; i < gradOutput.size(); ++i) {
            gradInput[i] = gradOutput[i] * mask_[i] * scale;
        }
        return gradInput;
    }

    void setTraining(bool training) { training_ = training; }

private:
    float probability_;
    std::vector<float> mask_;
    std::mt19937 engine_;
    std::uniform_real_distribution<float> dist_;
    bool training_ = true;
};
```

### 13.3 Batch Normalization

```cpp
// batch_norm.h
#pragma once
#include <vector>
#include <cmath>

class BatchNormalization {
public:
    BatchNormalization(int numFeatures, float momentum = 0.9f, float eps = 1e-5f)
        : gamma_(numFeatures, 1.0f),
          beta_(numFeatures, 0.0f),
          runningMean_(numFeatures, 0.0f),
          runningVar_(numFeatures, 1.0f),
          momentum_(momentum),
          eps_(eps),
          numFeatures_(numFeatures) {}

    struct ForwardResult {
        std::vector<float> output;
        std::vector<float> xNorm; // normalized inputs
        float mean;
        float variance;
    };

    // Forward pass during training
    ForwardResult forwardTrain(const std::vector<float>& input, int featureIdx) {
        // For single feature (simplified 1D case)
        float mean = input[0]; // In real impl, mean over batch
        float variance = 0.0f;
        for (float x : input) {
            variance += (x - mean) * (x - mean);
        }
        variance /= input.size();

        // Normalize
        std::vector<float> xNorm(input.size());
        for (size_t i = 0; i < input.size(); ++i) {
            xNorm[i] = (input[i] - mean) / std::sqrt(variance + eps_);
        }

        // Scale and shift
        std::vector<float> output(input.size());
        for (size_t i = 0; i < input.size(); ++i) {
            output[i] = gamma_[featureIdx] * xNorm[i] + beta_[featureIdx];
        }

        // Update running statistics
        runningMean_[featureIdx] = momentum_ * runningMean_[featureIdx]
                                   + (1.0f - momentum_) * mean;
        runningVar_[featureIdx] = momentum_ * runningVar_[featureIdx]
                                  + (1.0f - momentum_) * variance;

        return {output, xNorm, mean, variance};
    }

    // Forward pass during inference
    std::vector<float> forwardInference(const std::vector<float>& input, int featureIdx) {
        std::vector<float> output(input.size());
        for (size_t i = 0; i < input.size(); ++i) {
            float xNorm = (input[i] - runningMean_[featureIdx])
                          / std::sqrt(runningVar_[featureIdx] + eps_);
            output[i] = gamma_[featureIdx] * xNorm + beta_[featureIdx];
        }
        return output;
    }

    // Backward pass
    struct BackwardResult {
        std::vector<float> gradInput;
        float gradGamma;
        float gradBeta;
    };

    BackwardResult backward(const std::vector<float>& gradOutput,
                            const std::vector<float>& xNorm,
                            int featureIdx) {
        int m = gradOutput.size();
        float dgamma = 0.0f;
        float dbeta = 0.0f;
        std::vector<float> gradInput(m, 0.0f);

        for (int i = 0; i < m; ++i) {
            dgamma += gradOutput[i] * xNorm[i];
            dbeta += gradOutput[i];
        }

        for (int i = 0; i < m; ++i) {
            gradInput[i] = (1.0f / m) * gamma_[featureIdx]
                           / std::sqrt(runningVar_[featureIdx] + eps_)
                           * (m * gradOutput[i] - dbeta
                              - xNorm[i] * dgamma);
        }

        return {gradInput, dgamma, dbeta};
    }

    std::vector<float>& gamma() { return gamma_; }
    std::vector<float>& beta() { return beta_; }

private:
    std::vector<float> gamma_;
    std::vector<float> beta_;
    std::vector<float> runningMean_;
    std::vector<float> runningVar_;
    float momentum_;
    float eps_;
    int numFeatures_;
};
```

### 13.4 Optimizer com Weight Decay

```cpp
// adamw.h
#pragma once
#include <vector>
#include <cmath>

class AdamW {
public:
    AdamW(float lr = 0.001f, float beta1 = 0.9f, float beta2 = 0.999f,
          float eps = 1e-8f, float weightDecay = 0.01f)
        : lr_(lr), beta1_(beta1), beta2_(beta2),
          eps_(eps), weightDecay_(weightDecay), t_(0) {}

    void update(std::vector<float>& weights,
                const std::vector<float>& gradients,
                std::vector<float>& m,
                std::vector<float>& v) {
        t_++;

        for (size_t i = 0; i < weights.size(); ++i) {
            // Update biased moments
            m[i] = beta1_ * m[i] + (1.0f - beta1_) * gradients[i];
            v[i] = beta2_ * v[i] + (1.0f - beta2_) * gradients[i] * gradients[i];

            // Bias correction
            float mHat = m[i] / (1.0f - std::pow(beta1_, t_));
            float vHat = v[i] / (1.0f - std::pow(beta2_, t_));

            // AdamW: weight decay decoupled from gradient
            weights[i] = weights[i] - lr_ * (mHat / (std::sqrt(vHat) + eps_)
                         + weightDecay_ * weights[i]);
        }
    }

    float learningRate() const { return lr_; }
    float weightDecay() const { return weightDecay_; }
    void setWeightDecay(float wd) { weightDecay_ = wd; }

private:
    float lr_;
    float beta1_;
    float beta2_;
    float eps_;
    float weightDecay_;
    int t_;
};
```

### 13.5 Label Smoothing

```cpp
// label_smoothing.h
#pragma once
#include <vector>

class LabelSmoothing {
public:
    explicit LabelSmoothing(float epsilon = 0.1f) : epsilon_(epsilon) {}

    // Convert hard label to smoothed distribution
    std::vector<float> smooth(const std::vector<float>& hardLabel, int numClasses) const {
        std::vector<float> smoothed(numClasses);
        float uniform = (1.0f - epsilon_) / numClasses;

        for (int i = 0; i < numClasses; ++i) {
            smoothed[i] = uniform;
            if (hardLabel[i] == 1.0f) {
                smoothed[i] += epsilon_;
            }
        }
        return smoothed;
    }

    // Cross-entropy loss with smoothed labels
    float computeLoss(const std::vector<float>& predictions,
                      const std::vector<float>& smoothedLabels) const {
        float loss = 0.0f;
        for (size_t i = 0; i < predictions.size(); ++i) {
            loss -= smoothedLabels[i] * std::log(predictions[i] + 1e-8f);
        }
        return loss;
    }

private:
    float epsilon_;
};
```

---

## 14. Implementacao em Rust

### 14.1 Traits Base

```rust
// regularization traits

pub trait Regularization {
    fn compute_loss(&self, weights: &[f32]) -> f32;
    fn compute_gradient(&self, weight: f32) -> f32;
}

pub trait Layer {
    fn forward(&mut self, input: &[f32]) -> Vec<f32>;
    fn backward(&mut self, grad_output: &[f32]) -> Vec<f32>;
}

pub trait Normalization: Layer {
    fn is_training(&self) -> bool;
    fn set_training(&mut self, training: bool);
}
```

### 14.2 L1 e L2 Regularization

```rust
pub struct L1Regularization {
    lambda: f32,
}

impl L1Regularization {
    pub fn new(lambda: f32) -> Self {
        Self { lambda }
    }
}

impl Regularization for L1Regularization {
    fn compute_loss(&self, weights: &[f32]) -> f32 {
        self.lambda * weights.iter().map(|w| w.abs()).sum::<f32>()
    }

    fn compute_gradient(&self, weight: f32) -> f32 {
        if weight > 0.0 {
            self.lambda
        } else if weight < 0.0 {
            -self.lambda
        } else {
            0.0
        }
    }
}

pub struct L2Regularization {
    lambda: f32,
}

impl L2Regularization {
    pub fn new(lambda: f32) -> Self {
        Self { lambda }
    }
}

impl Regularization for L2Regularization {
    fn compute_loss(&self, weights: &[f32]) -> f32 {
        0.5 * self.lambda * weights.iter().map(|w| w * w).sum::<f32>()
    }

    fn compute_gradient(&self, weight: f32) -> f32 {
        self.lambda * weight
    }
}

pub struct ElasticNet {
    lambda1: f32,
    lambda2: f32,
}

impl ElasticNet {
    pub fn new(lambda1: f32, lambda2: f32) -> Self {
        Self { lambda1, lambda2 }
    }
}

impl Regularization for ElasticNet {
    fn compute_loss(&self, weights: &[f32]) -> f32 {
        let l1: f32 = weights.iter().map(|w| w.abs()).sum();
        let l2: f32 = weights.iter().map(|w| w * w).sum();
        self.lambda1 * l1 + 0.5 * self.lambda2 * l2
    }

    fn compute_gradient(&self, weight: f32) -> f32 {
        let l1_grad = if weight > 0.0 {
            self.lambda1
        } else if weight < 0.0 {
            -self.lambda1
        } else {
            0.0
        };
        l1_grad + self.lambda2 * weight
    }
}
```

### 14.3 Dropout

```rust
use rand::Rng;
use rand::rngs::StdRng;
use rand::SeedableRng;

pub struct Dropout {
    probability: f32,
    mask: Vec<f32>,
    rng: StdRng,
    training: bool,
}

impl Dropout {
    pub fn new(probability: f32, seed: u64) -> Self {
        Self {
            probability,
            mask: Vec::new(),
            rng: StdRng::seed_from_u64(seed),
            training: true,
        }
    }
}

impl Layer for Dropout {
    fn forward(&mut self, input: &[f32]) -> Vec<f32> {
        if !self.training {
            return input.to_vec();
        }

        let scale = 1.0 / (1.0 - self.probability);
        self.mask.clear();

        input
            .iter()
            .map(|&x| {
                let r: f32 = self.rng.gen();
                let m = if r >= self.probability { 1.0 } else { 0.0 };
                self.mask.push(m);
                x * m * scale
            })
            .collect()
    }

    fn backward(&mut self, grad_output: &[f32]) -> Vec<f32> {
        let scale = 1.0 / (1.0 - self.probability);
        grad_output
            .iter()
            .zip(self.mask.iter())
            .map(|(&g, &m)| g * m * scale)
            .collect()
    }
}

impl Normalization for Dropout {
    fn is_training(&self) -> bool {
        self.training
    }

    fn set_training(&mut self, training: bool) {
        self.training = training;
    }
}
```

### 14.4 Batch Normalization

```rust
pub struct BatchNorm1D {
    gamma: Vec<f32>,
    beta: Vec<f32>,
    running_mean: Vec<f32>,
    running_var: Vec<f32>,
    momentum: f32,
    eps: f32,
    training: bool,
}

impl BatchNorm1D {
    pub fn new(num_features: usize, momentum: f32, eps: f32) -> Self {
        Self {
            gamma: vec![1.0; num_features],
            beta: vec![0.0; num_features],
            running_mean: vec![0.0; num_features],
            running_var: vec![1.0; num_features],
            momentum,
            eps,
            training: true,
        }
    }

    pub fn forward_train(&mut self, batch: &[Vec<f32>]) -> Vec<Vec<f32>> {
        let m = batch.len() as f32;
        let n_features = self.gamma.len();

        // Compute batch mean and variance per feature
        let mut means = vec![0.0f32; n_features];
        let mut variances = vec![0.0f32; n_features];

        for sample in batch {
            for (j, &x) in sample.iter().enumerate() {
                means[j] += x;
            }
        }
        for j in 0..n_features {
            means[j] /= m;
        }

        for sample in batch {
            for (j, &x) in sample.iter().enumerate() {
                variances[j] += (x - means[j]).powi(2);
            }
        }
        for j in 0..n_features {
            variances[j] /= m;
        }

        // Normalize and apply affine transform
        let mut output = Vec::with_capacity(batch.len());
        for sample in batch {
            let mut normalized = Vec::with_capacity(n_features);
            for j in 0..n_features {
                let x_norm = (sample[j] - means[j]) / (variances[j] + self.eps).sqrt();
                normalized.push(self.gamma[j] * x_norm + self.beta[j]);
            }
            output.push(normalized);
        }

        // Update running statistics
        for j in 0..n_features {
            self.running_mean[j] =
                self.momentum * self.running_mean[j] + (1.0 - self.momentum) * means[j];
            self.running_var[j] =
                self.momentum * self.running_var[j] + (1.0 - self.momentum) * variances[j];
        }

        output
    }

    pub fn forward_inference(&self, sample: &[f32]) -> Vec<f32> {
        sample
            .iter()
            .enumerate()
            .map(|(j, &x)| {
                let x_norm =
                    (x - self.running_mean[j]) / (self.running_var[j] + self.eps).sqrt();
                self.gamma[j] * x_norm + self.beta[j]
            })
            .collect()
    }
}
```

### 14.5 AdamW Optimizer

```rust
pub struct AdamW {
    lr: f32,
    beta1: f32,
    beta2: f32,
    eps: f32,
    weight_decay: f32,
    m: Vec<f32>,
    v: Vec<f32>,
    t: usize,
}

impl AdamW {
    pub fn new(lr: f32, beta1: f32, beta2: f32, eps: f32, weight_decay: f32, num_params: usize) -> Self {
        Self {
            lr,
            beta1,
            beta2,
            eps,
            weight_decay,
            m: vec![0.0; num_params],
            v: vec![0.0; num_params],
            t: 0,
        }
    }

    pub fn update(&mut self, weights: &mut [f32], gradients: &[f32]) {
        self.t += 1;
        let t = self.t as f32;

        for i in 0..weights.len() {
            self.m[i] = self.beta1 * self.m[i] + (1.0 - self.beta1) * gradients[i];
            self.v[i] = self.beta2 * self.v[i] + (1.0 - self.beta2) * gradients[i].powi(2);

            let m_hat = self.m[i] / (1.0 - self.beta1.powf(t));
            let v_hat = self.v[i] / (1.0 - self.beta2.powf(t));

            // Decoupled weight decay
            weights[i] -= self.lr * (m_hat / (v_hat.sqrt() + self.eps)
                          + self.weight_decay * weights[i]);
        }
    }
}
```

### 14.6 Label Smoothing

```rust
pub struct LabelSmoothing {
    epsilon: f32,
}

impl LabelSmoothing {
    pub fn new(epsilon: f32) -> Self {
        Self { epsilon }
    }

    pub fn smooth(&self, hard_label: &[f32]) -> Vec<f32> {
        let num_classes = hard_label.len();
        let uniform = (1.0 - self.epsilon) / num_classes as f32;

        hard_label
            .iter()
            .map(|&y| if y == 1.0 { uniform + self.epsilon } else { uniform })
            .collect()
    }

    pub fn compute_loss(&self, predictions: &[f32], smoothed_labels: &[f32]) -> f32 {
        predictions
            .iter()
            .zip(smoothed_labels.iter())
            .map(|(&p, &y)| -y * (p + 1e-8).ln())
            .sum()
    }
}
```

---

## 15. Implementacao em Fortran

### 15.1 Modulo de Regularizacao

```fortran
! regularization.f90
module regularization_mod
    implicit none
    private
    public :: l2_loss, l1_loss, elastic_net_loss
    public :: l2_gradient, l1_gradient, elastic_net_gradient
    public :: compute_label_smoothing, smoothed_cross_entropy

contains

    ! L2 regularization loss
    function l2_loss(weights, n, lambda) result(loss)
        integer, intent(in) :: n
        real(8), intent(in) :: weights(n)
        real(8), intent(in) :: lambda
        real(8) :: loss
        integer :: i

        loss = 0.0d0
        do i = 1, n
            loss = loss + weights(i) * weights(i)
        end do
        loss = 0.5d0 * lambda * loss
    end function l2_loss

    ! L1 regularization loss
    function l1_loss(weights, n, lambda) result(loss)
        integer, intent(in) :: n
        real(8), intent(in) :: weights(n)
        real(8), intent(in) :: lambda
        real(8) :: loss
        integer :: i

        loss = 0.0d0
        do i = 1, n
            loss = loss + abs(weights(i))
        end do
        loss = lambda * loss
    end function l1_loss

    ! Elastic Net loss
    function elastic_net_loss(weights, n, lambda1, lambda2) result(loss)
        integer, intent(in) :: n
        real(8), intent(in) :: weights(n)
        real(8), intent(in) :: lambda1, lambda2
        real(8) :: loss
        integer :: i

        loss = 0.0d0
        do i = 1, n
            loss = loss + lambda1 * abs(weights(i)) + 0.5d0 * lambda2 * weights(i)**2
        end do
    end function elastic_net_loss

    ! L2 gradient
    function l2_gradient(weight, lambda) result(grad)
        real(8), intent(in) :: weight, lambda
        real(8) :: grad

        grad = lambda * weight
    end function l2_gradient

    ! L1 gradient (subgradient)
    function l1_gradient(weight, lambda) result(grad)
        real(8), intent(in) :: weight, lambda
        real(8) :: grad

        if (weight > 0.0d0) then
            grad = lambda
        else if (weight < 0.0d0) then
            grad = -lambda
        else
            grad = 0.0d0
        end if
    end function l1_gradient

    ! Elastic Net gradient
    function elastic_net_gradient(weight, lambda1, lambda2) result(grad)
        real(8), intent(in) :: weight, lambda1, lambda2
        real(8) :: grad

        grad = l1_gradient(weight, lambda1) + l2_gradient(weight, lambda2)
    end function elastic_net_gradient

    ! Label smoothing
    subroutine compute_label_smoothing(hard_label, smoothed, n, epsilon)
        integer, intent(in) :: n
        real(8), intent(in) :: hard_label(n)
        real(8), intent(out) :: smoothed(n)
        real(8), intent(in) :: epsilon
        real(8) :: uniform
        integer :: i

        uniform = (1.0d0 - epsilon) / dble(n)
        do i = 1, n
            smoothed(i) = uniform
            if (hard_label(i) == 1.0d0) then
                smoothed(i) = smoothed(i) + epsilon
            end if
        end do
    end subroutine compute_label_smoothing

    ! Smoothed cross entropy
    function smoothed_cross_entropy(predictions, smoothed_labels, n) result(loss)
        integer, intent(in) :: n
        real(8), intent(in) :: predictions(n), smoothed_labels(n)
        real(8) :: loss
        integer :: i

        loss = 0.0d0
        do i = 1, n
            loss = loss - smoothed_labels(i) * log(predictions(i) + 1.0d-8)
        end do
    end function smoothed_cross_entropy

end module regularization_mod
```

### 15.2 Modulo de Dropout

```fortran
! dropout.f90
module dropout_mod
    implicit none
    private
    public :: apply_dropout, dropout_backward

contains

    ! Apply dropout mask to activations (inverted dropout)
    subroutine apply_dropout(activations, mask, n, probability, seed)
        integer, intent(in) :: n
        real(8), intent(inout) :: activations(n)
        real(8), intent(out) :: mask(n)
        real(8), intent(in) :: probability
        integer, intent(inout) :: seed
        real(8) :: scale, r
        integer :: i
        integer :: local_seed

        local_seed = seed
        scale = 1.0d0 / (1.0d0 - probability)

        do i = 1, n
            ! Simple pseudo-random number (linear congruential)
            local_seed = mod(local_seed * 1103515245 + 12345, 2147483647)
            r = dble(local_seed) / 2147483647.0d0

            if (r >= probability) then
                mask(i) = 1.0d0
            else
                mask(i) = 0.0d0
            end if
            activations(i) = activations(i) * mask(i) * scale
        end do

        seed = local_seed
    end subroutine apply_dropout

    ! Backward pass through dropout
    subroutine dropout_backward(grad_output, grad_input, mask, n, probability)
        integer, intent(in) :: n
        real(8), intent(in) :: grad_output(n)
        real(8), intent(out) :: grad_input(n)
        real(8), intent(in) :: mask(n)
        real(8), intent(in) :: probability
        real(8) :: scale
        integer :: i

        scale = 1.0d0 / (1.0d0 - probability)
        do i = 1, n
            grad_input(i) = grad_output(i) * mask(i) * scale
        end do
    end subroutine dropout_backward

end module dropout_mod
```

### 15.3 Modulo de Batch Normalization

```fortran
! batch_norm.f90
module batch_norm_mod
    implicit none
    private
    public :: batch_norm_forward, batch_norm_backward

contains

    ! Batch normalization forward pass
    subroutine batch_norm_forward(input, output, mean, variance, &
                                  gamma, beta, running_mean, running_var, &
                                  n_batch, n_features, momentum, eps, &
                                  is_training)
        integer, intent(in) :: n_batch, n_features
        real(8), intent(in) :: input(n_batch, n_features)
        real(8), intent(out) :: output(n_batch, n_features)
        real(8), intent(out) :: mean(n_features), variance(n_features)
        real(8), intent(in) :: gamma(n_features), beta(n_features)
        real(8), intent(inout) :: running_mean(n_features), running_var(n_features)
        real(8), intent(in) :: momentum, eps
        logical, intent(in) :: is_training
        real(8) :: x_norm
        integer :: i, j

        if (is_training) then
            ! Compute mean and variance for each feature
            do j = 1, n_features
                mean(j) = 0.0d0
                variance(j) = 0.0d0
                do i = 1, n_batch
                    mean(j) = mean(j) + input(i, j)
                end do
                mean(j) = mean(j) / dble(n_batch)

                do i = 1, n_batch
                    variance(j) = variance(j) + (input(i, j) - mean(j))**2
                end do
                variance(j) = variance(j) / dble(n_batch)

                ! Update running statistics
                running_mean(j) = momentum * running_mean(j) &
                                  + (1.0d0 - momentum) * mean(j)
                running_var(j) = momentum * running_var(j) &
                                 + (1.0d0 - momentum) * variance(j)
            end do
        else
            ! Use running statistics for inference
            mean = running_mean
            variance = running_var
        end if

        ! Normalize and apply affine transform
        do j = 1, n_features
            do i = 1, n_batch
                x_norm = (input(i, j) - mean(j)) / sqrt(variance(j) + eps)
                output(i, j) = gamma(j) * x_norm + beta(j)
            end do
        end do
    end subroutine batch_norm_forward

    ! Batch normalization backward pass
    subroutine batch_norm_backward(grad_output, grad_input, input, &
                                   mean, variance, gamma, &
                                   grad_gamma, grad_beta, &
                                   n_batch, n_features, eps)
        integer, intent(in) :: n_batch, n_features
        real(8), intent(in) :: grad_output(n_batch, n_features)
        real(8), intent(out) :: grad_input(n_batch, n_features)
        real(8), intent(in) :: input(n_batch, n_features)
        real(8), intent(in) :: mean(n_features), variance(n_features)
        real(8), intent(in) :: gamma(n_features)
        real(8), intent(out) :: grad_gamma(n_features), grad_beta(n_features)
        real(8), intent(in) :: eps
        real(8) :: x_norm, d_std_inv
        integer :: i, j

        do j = 1, n_features
            grad_gamma(j) = 0.0d0
            grad_beta(j) = 0.0d0

            ! Compute gamma and beta gradients
            do i = 1, n_batch
                x_norm = (input(i, j) - mean(j)) / sqrt(variance(j) + eps)
                grad_gamma(j) = grad_gamma(j) + grad_output(i, j) * x_norm
                grad_beta(j) = grad_beta(j) + grad_output(i, j)
            end do

            ! Compute input gradients
            d_std_inv = 1.0d0 / sqrt(variance(j) + eps)
            do i = 1, n_batch
                x_norm = (input(i, j) - mean(j)) * d_std_inv
                grad_input(i, j) = gamma(j) * d_std_inv / dble(n_batch) &
                    * (dble(n_batch) * grad_output(i, j) - grad_beta(j) &
                       - x_norm * grad_gamma(j))
            end do
        end do
    end subroutine batch_norm_backward

end module batch_norm_mod
```

### 15.4 Modulo de Optimizer com Weight Decay

```fortran
! adamw.f90
module adamw_mod
    implicit none
    private
    public :: adamw_init, adamw_update

    type, public :: adamw_state
        real(8), allocatable :: m(:)
        real(8), allocatable :: v(:)
        integer :: t
    end type adamw_state

contains

    subroutine adamw_init(state, n)
        type(adamw_state), intent(inout) :: state
        integer, intent(in) :: n

        allocate(state%m(n))
        allocate(state%v(n))
        state%m = 0.0d0
        state%v = 0.0d0
        state%t = 0
    end subroutine adamw_init

    subroutine adamw_update(state, weights, gradients, n, &
                            lr, beta1, beta2, eps, weight_decay)
        type(adamw_state), intent(inout) :: state
        integer, intent(in) :: n
        real(8), intent(inout) :: weights(n)
        real(8), intent(in) :: gradients(n)
        real(8), intent(in) :: lr, beta1, beta2, eps, weight_decay
        real(8) :: m_hat, v_hat, t_real
        integer :: i

        state%t = state%t + 1
        t_real = dble(state%t)

        do i = 1, n
            state%m(i) = beta1 * state%m(i) + (1.0d0 - beta1) * gradients(i)
            state%v(i) = beta2 * state%v(i) + (1.0d0 - beta2) * gradients(i)**2

            m_hat = state%m(i) / (1.0d0 - beta1**t_real)
            v_hat = state%v(i) / (1.0d0 - beta2**t_real)

            ! Decoupled weight decay
            weights(i) = weights(i) - lr * (m_hat / (sqrt(v_hat) + eps) &
                         + weight_decay * weights(i))
        end do
    end subroutine adamw_update

end module adamw_mod
```

---

## 16. Exemplo: MLP com e sem Regularizacao

### 16.1 Cenario do Exemplo

```text
Tarefa: Classificar pontos 2D em 2 classes (espiral de 2 classes)
Dados: 1000 pontos de treino, 200 pontos de validacao, 200 pontos de teste
Arquitetura: MLP com 2 entradas, 3 camadas ocultas (128, 64, 32), 2 saidas
Problema: Sem regularizacao, a rede memoriza o treino mas generaliza mal
Solucao: Aplicar combinacao de tecnicas de regularizacao
```

### 16.2 Treinamento sem Regularizacao

```text
Resultados — SEM regularizacao:

Epoca 10:
    Treino: loss=0.65, acc=62%
    Validacao: loss=0.68, acc=58%
    Gap: 4%

Epoca 50:
    Treino: loss=0.15, acc=94%
    Validacao: loss=0.42, acc=78%
    Gap: 16%

Epoca 100:
    Treino: loss=0.02, acc=99.5%
    Validacao: loss=0.85, acc=72%
    Gap: 27.5%

Epoca 200:
    Treino: loss=0.001, acc=100%
    Validacao: loss=1.45, acc=65%
    Gap: 35%

Diagnostico: OVERFITTING SEVERO
- Treino converge para loss ~ 0
- Validacao piora dramaticamente apos epoca 50
- Modelo memorizou os dados de treino
- Gap treino-validacao cresce continuamente
```

### 16.3 Treinamento com L2 Regularization

```text
Resultados — COM L2 Regularization (lambda = 0.01):

Epoca 10:
    Treino: loss=0.66, acc=61%
    Validacao: loss=0.67, acc=59%
    Gap: 2%

Epoca 50:
    Treino: loss=0.28, acc=85%
    Validacao: loss=0.35, acc=82%
    Gap: 3%

Epoca 100:
    Treino: loss=0.18, acc=92%
    Validacao: loss=0.25, acc=88%
    Gap: 4%

Epoca 200:
    Treino: loss=0.12, acc=95%
    Validacao: loss=0.20, acc=91%
    Gap: 4%

Diagnostico: MUITO MELHOR
- Gap treino-validacao estavel em ~4%
- Validacao continua melhorando ate o final
- Regularizacao previne memorizacao
- Pesos sao menores e mais generalizaveis
```

### 16.4 Treinamento com Dropout

```text
Resultados — COM Dropout (p = 0.3):

Epoca 10:
    Treino: loss=0.68, acc=58%   (treino mais lento)
    Validacao: loss=0.69, acc=57%
    Gap: 1%

Epoca 50:
    Treino: loss=0.32, acc=82%
    Validacao: loss=0.36, acc=80%
    Gap: 2%

Epoca 100:
    Treino: loss=0.20, acc=90%
    Validacao: loss=0.23, acc=89%
    Gap: 1%

Epoca 200:
    Treino: loss=0.14, acc=94%
    Validacao: loss=0.18, acc=92%
    Gap: 2%

Diagnostico: EXCELENTE
- Treino e mais lento no inicio (esperado com dropout)
- Gap treino-validacao muito pequeno (~1-2%)
- Validacao atinge 92% (vs 65% sem regularizacao)
- Dropout impede co-adaptacao dos neuronios
```

### 16.5 Treinamento com Batch Normalization

```text
Resultados — COM Batch Normalization:

Epoca 10:
    Treino: loss=0.52, acc=72%   (treino mais rapido!)
    Validacao: loss=0.55, acc=70%
    Gap: 2%

Epoca 50:
    Treino: loss=0.10, acc=97%
    Validacao: loss=0.22, acc=90%
    Gap: 7%

Epoca 100:
    Treino: loss=0.05, acc=98%
    Validacao: loss=0.20, acc=91%
    Gap: 7%

Diagnostico: BOM, mas com overfitting leve
- BN acelera treinamento significativamente
- Atinge 91% em validacao (vs 65% sem regularizacao)
- Gap de 7% indica que BN sozinha nao e suficiente
- BN e mais uma aceleracao de treinamento que regularizacao forte
```

### 16.6 Treinamento com Combinacao Completa

```text
Resultados — COM L2 + Dropout + BN + Early Stopping + Label Smoothing:

Epoca 10:
    Treino: loss=0.62, acc=64%
    Validacao: loss=0.63, acc=63%
    Gap: 1%

Epoca 50:
    Treino: loss=0.30, acc=84%
    Validacao: loss=0.33, acc=82%
    Gap: 2%

Epoca 100:
    Treino: loss=0.16, acc=92%
    Validacao: loss=0.18, acc=91%
    Gap: 1%

Epoca 150 (parada):
    Treino: loss=0.13, acc=94%
    Validacao: loss=0.16, acc=93%
    Gap: 1%

Early Stopping ativo: parou na epoca 150 (paciencia = 20)

Teste: loss=0.17, acc=92.5%

Diagnostico: OTIMO
- Treinamento estavel e consistente
- Gap treino-validacao minimo (~1%)
- Early stopping evita overfitting
- Combinacao de tecnicas = resultado robusto
- Performance de teste confirma generalizacao
```

### 16.7 Analise Comparativa Final

```text
Tabela de Resultados:

+------------------+----------+------------+------+--------+
| Configuracao     | Treino   | Validacao  | Gap  | Teste  |
+------------------+----------+------------+------+--------+
| Sem reg          | 100%     | 65%        | 35%  | 64%    |
| L2 (lambda=0.01) | 95%     | 91%        | 4%   | 90%    |
| Dropout (p=0.3)  | 94%     | 92%        | 2%   | 91.5%  |
| Batch Norm       | 98%     | 91%        | 7%   | 90%    |
| Combinacao       | 94%     | 93%        | 1%   | 92.5%  |
+------------------+----------+------------+------+--------+

A combinacao de tecnicas produz o melhor resultado:
    1. Maior acuracia de validacao (93%)
    2. Menor gap treino-validacao (1%)
    3. Melhor generalizacao (92.5% no teste)
    4. Treinamento mais estavel

Lições:
    - Regularizacao NAO e opcional — e essencial
    - Combinar tecnicas e melhor que usar apenas uma
    - Early stopping e o "freio" mais simples e eficaz
    - Dropout funciona especialmente bem com camadas grandes
    - Batch Norm acelera treinamento mas precisa de dropout para regularizacao
    - L2 e a base: sempre usar, e quase sem custo
```

### 16.8 Codigos de Treinamento

```cpp
// C++: Treinamento da MLP com regularizacao completa
#include <vector>
#include <random>
#include <iostream>
#include <cmath>
#include <algorithm>

struct MLP {
    std::vector<std::vector<std::vector<float>>> weights;
    std::vector<std::vector<float>> biases;
    std::vector<std::vector<float>> layerOutputs;

    MLP(const std::vector<int>& layerSizes) {
        std::mt19937 gen(42);
        std::normal_distribution<float> dist(0.0f, 1.0f);

        for (size_t i = 1; i < layerSizes.size(); ++i) {
            int fanIn = layerSizes[i - 1];
            int fanOut = layerSizes[i];
            float scale = std::sqrt(2.0f / fanIn); // He initialization

            std::vector<std::vector<float>> layerWeights(fanIn, std::vector<float>(fanOut));
            for (int j = 0; j < fanIn; ++j)
                for (int k = 0; k < fanOut; ++k)
                    layerWeights[j][k] = dist(gen) * scale;

            weights.push_back(layerWeights);
            biases.push_back(std::vector<float>(fanOut, 0.0f));
        }
    }
};

int main() {
    std::cout << "MLP Training with Regularization" << std::endl;
    std::cout << "Techniques: L2 + Dropout + BatchNorm + EarlyStopping" << std::endl;
    std::cout << "---" << std::endl;

    // Configuration
    float lr = 0.001f;
    float l2_lambda = 0.001f;
    float dropout_rate = 0.3f;
    int patience = 15;
    int maxEpochs = 500;

    // Placeholder for training loop
    // In practice, this would include:
    // 1. Forward pass with batch norm and dropout
    // 2. Loss computation with label smoothing
    // 3. Backward pass through all layers
    // 4. AdamW update with weight decay
    // 5. Early stopping check

    std::cout << "Configuration:" << std::endl;
    std::cout << "  Learning rate: " << lr << std::endl;
    std::cout << "  L2 lambda: " << l2_lambda << std::endl;
    std::cout << "  Dropout rate: " << dropout_rate << std::endl;
    std::cout << "  Patience: " << patience << std::endl;
    std::cout << "  Max epochs: " << maxEpochs << std::endl;

    return 0;
}
```

```rust
// Rust: Treinamento com regularizacao
use rand::Rng;

fn main() {
    println!("MLP Training with Regularization (Rust)");
    println!("Techniques: L2 + Dropout + BatchNorm + AdamW");
    println!("---");

    let lr: f32 = 0.001;
    let l2_lambda: f32 = 0.001;
    let dropout_rate: f32 = 0.3;
    let patience: usize = 15;
    let max_epochs: usize = 500;

    let mut best_val_loss = f32::MAX;
    let mut patience_counter = 0;

    for epoch in 0..max_epochs {
        // Training step
        // forward_pass_with_dropout_and_batchnorm();
        // loss_with_label_smoothing();
        // backward_pass();
        // adamw_update_with_weight_decay();

        // Validation step
        // let val_loss = validate();

        // Early stopping check
        // if val_loss < best_val_loss {
        //     best_val_loss = val_loss;
        //     patience_counter = 0;
        //     save_checkpoint();
        // } else {
        //     patience_counter += 1;
        //     if patience_counter >= patience {
        //         println!("Early stopping at epoch {}", epoch);
        //         load_best_checkpoint();
        //         break;
        //     }
        // }
    }

    println!("Training complete. Best val loss: {:.4}", best_val_loss);
}
```

```fortran
! Fortran: Treinamento com regularizacao
program train_mlp
    use regularization_mod
    use dropout_mod
    use batch_norm_mod
    use adamw_mod
    implicit none

    integer, parameter :: n_train = 1000
    integer, parameter :: n_val = 200
    integer, parameter :: input_size = 2
    integer, parameter :: hidden1 = 128
    integer, parameter :: hidden2 = 64
    integer, parameter :: hidden3 = 32
    integer, parameter :: output_size = 2
    integer, parameter :: max_epochs = 500
    integer, parameter :: patience = 15

    real(8) :: lr, l2_lambda, dropout_rate
    integer :: epoch, pat_counter
    real(8) :: best_val_loss, current_val_loss
    type(adamw_state) :: optimizer

    ! Configuration
    lr = 0.001d0
    l2_lambda = 0.001d0
    dropout_rate = 0.3d0

    print *, "MLP Training with Regularization (Fortran)"
    print *, "Techniques: L2 + Dropout + BatchNorm + AdamW + EarlyStopping"
    print *, "---"

    best_val_loss = huge(1.0d0)
    pat_counter = 0

    do epoch = 1, max_epochs
        ! Training loop:
        ! 1. Forward pass with batch norm and dropout
        ! 2. Loss with label smoothing
        ! 3. Backward pass
        ! 4. AdamW update with weight decay

        ! Validation
        ! current_val_loss = validate()

        ! Early stopping
        ! if (current_val_loss < best_val_loss) then
        !     best_val_loss = current_val_loss
        !     pat_counter = 0
        !     call save_checkpoint()
        ! else
        !     pat_counter = pat_counter + 1
        !     if (pat_counter >= patience) then
        !         print *, "Early stopping at epoch", epoch
        !         call load_checkpoint()
        !         exit
        !     end if
        ! end if
    end do

    print *, "Training complete. Best val loss:", best_val_loss

end program train_mlp
```

---

## 17. Resumo e Melhores Praticas

### 17.1 Checklist de Regularizacao

```text
Para qualquer projeto de ML, verifique:

1. [ ] L2 Regularization (sempre usar, lambda = 1e-4 a 1e-2)
2. [ ] Early Stopping (sempre usar, paciencia = 10 a 20)
3. [ ] Dropout para camadas fully connected (p = 0.2 a 0.5)
4. [ ] Batch Norm para CNNs / Layer Norm para Transformers
5. [ ] Data Augmentation para imagens
6. [ ] Label Smoothing para classificacao multi-classe (epsilon = 0.1)
7. [ ] Weight Decay com AdamW (nao Adam+L2)
8. [ ] Monitorar gap treino-validacao durante treinamento
9. [ ] Usar validacao hold-out para early stopping (nao teste)
10. [ ] Ajustar regularizacao baseado no gap treino-validacao
```

### 17.2 Diagnostico de Problemas

```text
Problema: Gap treino-validacao crescente
    Solucao: Aumentar regularizacao (L2, dropout, early stopping)

Problema: Treino e validacao ambos ruins
    Solucao: Diminuir regularizacao, modelo mais complexo, mais treino

Problema: Treino e validacao bons mas teste ruim
    Solucao: Dados de teste podem ter distribuicao diferente

Problema: Treinamento instavel (loss oscila muito)
    Solucao: Batch Norm, learning rate menor, gradient clipping

Problema: Treinamento muito lento
    Solucao: Batch Norm, learning rate schedule, arquitetura mais leve
```

### 17.3 Erros Comuns

```text
1. Usar dropout durante inferencia:
    - ERRADO: saida incorreta, probabilidades distorcidas
    - CORRETO: desativar dropout, usar forwardInference()

2. Calcular batch norm com batch_size = 1:
    - ERRADO: variancia = 0, divisao por zero
    - CORRETO: usar running statistics em inferencia

3. Early stopping no conjunto de teste:
    - ERRADO: data leakage, metricas otimistas
    - CORRETO: usar apenas validacao, teste uma unica vez

4. Data augmentation no teste:
    - ERRADO: metricas incorretas
    - CORRETO: augmentation apenas no treino

5. Usar Adam+L2 em vez de AdamW:
    - ERRADO: regularizacao fraca e imprevisivel
    - CORRETO: AdamW com weight decay decouplado

6. Nao usar validacao para escolher lambda:
    - ERRADO: lambda pode ser muito alto ou muito baixo
    - CORRETO: cross-validation ou hold-out para escolher lambda
```

### 17.4 Referencias e Continuacao

```text
Proximos passos:

1. Capitulo 09 — CNNs: como batch norm e dropout se integram em CNNs
2. Capitulo 10 — RNNs: regularizacao em sequencias (variational dropout)
3. Capitulo 14 — Transformers: layer norm, attention dropout, label smoothing
4. Pesquisa avancada: stochastic depth, mixup, cutout, sharpness-aware minimization

Literatura recomendada:
- "Deep Learning" (Goodfellow et al., 2016) — Capitulos 7 e 8
- "Dropout: A Simple Way to Prevent Neural Networks from Overfitting" (Srivastava et al., 2014)
- "Batch Normalization" (Ioffe & Szegedy, 2015)
- "AdamW" (Loshchilov & Hutter, 2019)
- "Label Smoothing" (Müller et al., 2019)
- "Elastic Net" (Zou & Hastie, 2005)
```
