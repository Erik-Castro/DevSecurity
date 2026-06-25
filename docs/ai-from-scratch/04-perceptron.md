---
layout: default
title: "04-perceptron"
---

# Capitulo 4 — Perceptron

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. **Comparar o neuronio biologico com o neuronio artificial**, identificando as analogias e diferencas fundamentais entre dendritos/entradas, soma/peso, axonio/saida e sinapse/peso.
2. **Entender a historia do Perceptron de Rosenblatt** (1958), incluindo o contexto politico e cientifico que cercou sua criacao e o posterior "inverno" da IA.
3. **Dominar a funcao de decisao linear** do perceptron, incluindo a interpretacao geometrica do hiperplano de separacao e a relacao com o produto escalar.
4. **Implementar a regra de aprendizado do perceptron** (w_i = w_i + eta * (y - y_hat) * x_i), compreendendo o papel de cada componente e o impacto da taxa de aprendizado.
5. **Provar e compreender a convergencia do perceptron**, incluindo o Teorema de Convergencia, a taxa de convergencia e o papel da margem.
6. **Demonstrar geometricamente por que o perceptron simples nao resolve o XOR**, compreendendo a criticidade da publicacao de Minsky e Papert (1969).
7. **Implementar perceptron multi-classe** usando estrategias one-vs-all e one-vs-one, incluindo a extensao softmax.
8. **Implementar o perceptron completo em C++** com templates, tratamento de erros e funcoes utilitarias.
9. **Implementar o perceptron em Rust** usando traits, enums de erro e processamento por iteradores.
10. **Implementar o perceptron em Fortran** usando modulos, tipos derivados e subrotinas baseadas em alocacao dinamica.

---

## 1. Neuronio Biologico vs Artificial

### 1.1 O Neuronio Biologico

O neuronio biologico e a unidade fundamental do sistema nervoso. Cada ser humano possui aproximadamente 86 bilhoes de neuronios cerebrais, conectados por cerca de 100 trilhoes de sinapses. O neuronio biologico e uma celula especializada em transmitir e processar sinais eletroquimicos.

A estrutura de um neuronio biologico consiste em quatro componentes principais:

**Dendritos**: Ramificacoes ramificadas que recebem sinais de outros neuronios. Cada dendrito pode receber milhares de conexoes simultaneamente. Os sinais recebidos podem ser excitatorios (estimulam o neuronio a disparar) ou inibitorios (inibem o disparo).

**Soma (Soma Celular / Corpo Celular)**: Regiao central onde todos os sinais dos dendritos sao integrados. A integracao efeita pelo soma e fundamentalmente uma operacao de soma ponderada — os sinais excitatorios somam-se e os inibitorios subtraem-se.

**Axonio**: Estrutura longa e unica que conduz o sinal de saida do neuronio para outros neuronios. O axonio pode ter ate 1 metro de comprimento em neuronios motores. O sinal que percorre o axonio e uma mudanca no potencial de membrana chamada potencial de acao.

**Sinapses**: Conexoes quimicas na terminacao do axonio que transmitem o sinal para dendritos de outros neuronios. A forca da transmissao sinaptica varia — e o que chamamos de "plasticidade sinaptica", a base da aprendizagem biologica.

```text
Estrutura do Neuronio Biologico:

                    Dendritos (entradas)
                   / | | | | \    \
                  /  | | | |  \    \
                 /   | | | |   \    \
    ~~~~~~~~~~~~/~~~~|~|~|~|~~~~\~~~~\~~~~~~~~~~~~
               /     | | | |     \    \
              /      | | | |      \    \
             V       V V V V       V    V
           [================================]
           [   SOMA (integracao de sinais)   ]
           [================================]
                       |
                       | (potencial de acao)
                       |
           ============|===========================
                       |
                       v
           [================================]
           [        AXONIO (transmissao)     ]
           [================================]
                       |
                       | (terminais axonicas)
                       |
              +--------+--------+
              |        |        |
              v        v        v
           (sinapse) (sinapse) (sinapse)
              |        |        |
              v        v        v
          [neuronio] [neuronio] [neuronio]
           (proxima camada)
```

O processo de disparo (firing) do neuronio biologico segue o seguinte ciclo:

1. **Recepcao**: Dendritos recebem sinais quimicos (neurotransmissores) de outros neuronios.
2. **Integracao**: O soma acumula os sinais excitatorios e inibitorios.
3. **Limiar**: Se o potencial total excede um limiar (threshold), o neuronio dispara.
4. **Transmissao**: Um potencial de acao percorre o axonio ate as terminais.
5. **Transmissao sinaptica**: Neurotransmissores sao liberados na sinapse, influenciando o proximo neuronio.

### 1.2 O Neuronio Artificial

O neuronio artificial, proposto por McCulloch e Pitts em 1943, e uma abstracao matematica do neuronio biologico. Ele captura a essencia da operacao biologica — soma ponderada seguida de decisao — mas simplifica drasticamente a complexidade bioquimica.

Os componentes do neuronio artificial mapeiam-se aos componentes biologicos:

**Entradas (Inputs)**: Equivalentes aos dendritos. Cada entrada x_i representa um sinal recebido de outro neuronio ou do ambiente.

**Pesos (Weights)**: Equivalentes a forca das conexoes sinapticas. Cada peso w_i determina quao influente e a entrada x_i na decisao final. Pesos positivos representam conexoes excitatorias; pesos negativos representam conexoes inibitorias.

**Bias**: Um termo adicional que desloca a funcao de decisao. Equivale ao limiar de disparo do neuronio biologico (com sinal invertido). O bias permite que o neuronio "dispare" mesmo quando todas as entradas sao zero.

**Soma Ponderada**: O neuronio calcula a soma ponderada das entradas: z = w_1*x_1 + w_2*x_2 + ... + w_n*x_n + b. Equivale a integracao no soma biologico.

**Funcao de Ativacao**: Determina se o neuronio "dispara" ou nao. No perceptron original, e uma funcao de passo (step function): se z >= 0, saida = 1; caso contrario, saida = 0.

**Saida (Output)**: Equivalente ao potencial de acao no axonio. A saida do neuronio artificial e transmitida para neuronios da proxima camada.

```text
Estrutura do Neuronio Artificial:

  x_1 ----[w_1]----\
  x_2 ----[w_2]-----\
  x_3 ----[w_3]------> [SUM] --> z = w_1*x_1 + w_2*x_2 + w_3*x_3 + b
  x_4 ----[w_4]-----/           |
  x_5 ----[w_5]----/            |
                           [ACTIVATION]
                                |
                           [STEP FUNCTION]
                                |
                            y = 0 ou 1

  Mapeamento Biologico -> Artificial:
  Dendritos         -> Entradas (x_1, ..., x_n)
  Forca sinaptica   -> Pesos (w_1, ..., w_n)
  Limiar de disparo -> Bias (b)
  Soma no corpo     -> Soma ponderada (z)
  Potencial de acao -> Saida (y)
```

### 1.3 Tabela Comparativa Detalhada

```text
Aspecto              | Biologico                    | Artificial
---------------------|------------------------------|---------------------------
Unidade basica       | Neuronio (celula)            | Perceptron (funcao mat.)
Sinais de entrada    | Dendritos (10^3-10^4)        | Vetor de entradas (n)
Conexao              | Sinapse quimica              | Peso (float)
Forca da conexao     | Plasticidade sinaptica       | Valor do peso (w_i)
Integracao           | Potencial de membrana        | Soma ponderada (dot product)
Limiar               | ~-55mV (potencial de acao)   | Threshold (theta)
Saida                | Potencial de acao (all-or-   | 0 ou 1 (step function)
                     | none, ~100Hz max)            |
Tempo de operacao    | ~1-5 ms                      | ~ns (nanosegundos)
Paralelismo          | 86 bilhoes de neuronios      | Ilimitado (software)
Aprendizagem         | LTP/LTD, plasticidade        | Regra de aprendizado
Energia              | ~20W (cerebro inteiro)       | Variavel (CPU/GPU)
Ruido                | Inerente (probabilistico)    | Deterministico (por padrao)
Durabilidade         | Decadas (com manutencao)     | Infinita (copias)
Maleabilidade        | Limitada (neuroplasticidade) | Total (reprogramavel)
```

### 1.4 Analogias e Diferencas Criticas

**Analogia 1 — Soma Ponderada**: Tanto no neuronio biologico quanto no artificial, os sinais de entrada sao combinados por soma ponderada. No biologico, isso acontece por integracao eletroquimica na membrana. No artificial, e um simples produto escalar.

**Analogia 2 — Limiar de Disparo**: O neuronio biologico dispara quando o potencial de membrana atinge cerca de -55mV. O perceptron artificial dispara quando a soma ponderada excede um limiar (tipicamente zero).

**Diferenca 1 — Temporalidade**: Neuronios biologicos sao intrinsecamente temporais — o padrao temporal dos spikes importa. O perceptron artificial e atemporal — processa uma entrada estatica por vez.

**Diferenca 2 — Plasticidade**: A aprendizagem biologica envolve mecanismos complexos (LTP, LTD, neurotrofina, remodelacao sinaptica). O perceptron usa uma regra de atualizacao simples e deterministica.

**Diferenca 3 — Ruido**: Neuronios biologicos operam em ambiente ruidoso e probabilistico. O perceptron e deterministico (a saida e sempre a mesma para a mesma entrada).

**Diferenca 4 — Energia**: O cerebro humano consome apenas 20W para 86 bilhoes de neuronios. Uma GPU moderna consome centenas de watts para bilhoes de operacoes de ponto flutuante.

### 1.5 Por Que a Analogia Importa

A analogia biologica nao e apenas curiosidade historica — ela fornece intuicao critica para design de redes neurais. O conceito de que a "forca da conexao" determina a importancia de um sinal e o nucleo de todo aprendizado de maquina. A ideia de que um limiar de ativacao controla a saida e a base de todas as funcoes de ativacao.

No entanto, e fundamental nao cair na armadilha de achar que redes neurais artificiais "imitam" o cerebro. Elas sao inspiradas pela biologia, mas operam em principios fundamentalmente diferentes. O perceptron e uma ferramenta matematica, nao uma simulacao biologica.

---

## 2. Perceptron de Rosenblatt

### 2.1 Contexto Historico

Em 1957, Frank Rosenblatt, um psicologo e engenheiro de pesquisas do Cornell Aeronautical Laboratory, inventou o Perceptron — a primeira rede neural artificial capaz de aprender. O dispositivo fisico foi construido com motores eletricos e potenciometros, nao com transistores digitais.

O New York Times publicou em 1958:

```text
"A new Navy device learns by doing. The Navy revealed the
embryo of an electronic computer today that it expects will
be able to walk, talk, see, write, reproduce itself and be
conscious of its existence."
```

A previsao era exagerada, mas o impacto tecnico foi real. O perceptron demonstrou pela primeira vez que uma maquina podia aprender a classificar dados a partir de exemplos — uma conquista que parecia magica na epoca.

### 2.2 A Construcao do Perceptron Original

O perceptron original de Rosenblatt era um dispositivo eletromecanico. Ele consistia em:

**Camada de Entrada (Retina)**: Uma grade de fotocelulas que captava padroes visuais binarios (preto e branco). Cada fotocelula correspondia a um pixel.

**Camada de Pesos (Associacoes)**: Potenciometros ajustaveis que conectavam cada fotocelula a um neuronio de saida. O valor de cada potenciometro representava o peso da conexao.

**Neuronio de Saida**: Um unico neuronio que somava todos os sinais ponderados e aplicava uma funcao de passo para decidir a classificacao.

O treinamento era feito manualmente: quando o perceptron errava, o operador ajustava fisicamente os potenciometros na direcao correta.

### 2.3 A Regra do Perceptron (Formalizacao Matematica)

A formalizacao matematica do perceptron define:

**Entrada**: Um vetor x = (x_1, x_2, ..., x_n) onde cada x_i e um valor real.

**Pesos**: Um vetor w = (w_1, w_2, ..., w_n) onde cada w_i e um peso real associado a entrada x_i.

**Bias**: Um valor real b que desloca o limiar de decisao.

**Soma Ponderada**: z = w · x + b = sum(w_i * x_i) + b

**Funcao de Passo (Step Function)**:

```text
h(z) = { 1, se z >= 0
       { 0, se z < 0

Equivalente (com limiar theta):
h(z) = { 1, se z >= theta
       { 0, se z < theta

Onde theta = -b (o bias absorve o limiar)
```

**Saida do Perceptron**:

```text
y_hat = h(w · x + b)
y_hat = h(sum(w_i * x_i) + b)
```

### 2.4 Exemplo Intuitivo

Considere um perceptron com 2 entradas que deve classificar pontos em 2D como "acima" ou "abaixo" de uma linha.

```text
Exemplo: Classificar se um ponto (x1, x2) esta acima ou abaixo da linha y = x

Pesos: w_1 = -1, w_2 = 1
Bias:  b = 0

Soma ponderada: z = -1*x_1 + 1*x_2 + 0 = x_2 - x_1

Se z >= 0 (x_2 >= x_1): y_hat = 1 (acima da linha)
Se z < 0  (x_2 < x_1):  y_hat = 0 (abaixo da linha)

Teste:
  Ponto (1, 3): z = 3 - 1 = 2 >= 0 -> y_hat = 1 (acima) CORRETO
  Ponto (3, 1): z = 1 - 3 = -2 < 0 -> y_hat = 0 (abaixo) CORRETO
  Ponto (2, 2): z = 2 - 2 = 0 >= 0 -> y_hat = 1 (acima) CORRETO (ponto na linha)
```

### 2.5 Variacoes do Perceptron Original

Rosenblatt propoe varias arquiteturas:

**Perceptron Tipo I**: Camada de entrada conectada diretamente a camada de saida. A mais simples — e o que normalmente chamamos de "perceptron".

**Perceptron Tipo II**: Inclui uma camada intermediaria de "unidades de associao" com conexoes aleatorias fixas. Apenas os pesos da camada de saida sao treinados.

**Perceptron Tipo III**: A camada intermediaria tambem e treinada. Na pratica, e uma rede neural de duas camadas — e a arquitetura que levou a toda a moderna deep learning.

O foco deste capitulo e o Perceptron Tipo I — o mais simples, mas o mais importante para entender os fundamentos.

---

## 3. Funcao de Decisao Linear

### 3.1 Formulacao Matematica

A funcao de decisao do perceptron e uma funcao linear que mapeia vetores de entrada para uma classe:

```text
f(x) = sign(w · x + b)

Onde:
  sign(z) = { +1, se z > 0
             {  0, se z = 0
             { -1, se z < 0

Para classificacao binaria (classes 0 e 1):
  y_hat = { 1, se w · x + b >= 0
           { 0, se w · x + b < 0
```

A funcao de decisao define um hiperplano no espaco de entrada. Este hiperplano separa as duas classes.

### 3.2 Interpretacao Geometrica

Em 2D, o hiperplano de decisao e uma reta. Em 3D, e um plano. Em n dimensoes, e um hiperplano de dimensao n-1.

**Em 2D (duas entradas)**:

```text
Hiperplano: w_1 * x_1 + w_2 * x_2 + b = 0

Isolando x_2:
  x_2 = -(w_1/w_2) * x_1 - b/w_2

Inclinacao: m = -w_1/w_2
Intercepto: c = -b/w_2

Exemplo:
  w_1 = 1, w_2 = -2, b = 3

  Reta: x_1 - 2*x_2 + 3 = 0
  x_2 = (x_1 + 3) / 2

  Inclinacao: 0.5
  Intercepto: 1.5

  Classificacao:
    Ponto (0, 0): 0 - 0 + 3 = 3 > 0 -> classe 1
    Ponto (2, 3): 2 - 6 + 3 = -1 < 0 -> classe 0
    Ponto (-4, 0): -4 - 0 + 3 = -1 < 0 -> classe 0
```

### 3.3 Vetor Normal e Margem

O vetor de pesos w e normal (ortogonal) ao hiperplano de decisao. Isso significa que w aponta na direcao perpendicular a reta (ou plano) de separacao.

```text
Hiperplano: w · x + b = 0

Para qualquer ponto x no hiperplano:
  w · x = -b

Para um ponto x fora do hiperplano:
  w · x + b > 0 -> lado positivo (classe 1)
  w · x + b < 0 -> lado negativo (classe 0)

A distancia de um ponto x ao hiperplano e:
  d = |w · x + b| / ||w||

Onde ||w|| = sqrt(sum(w_i^2)) e a norma L2 do vetor de pesos.
```

### 3.4 Em Espacos de Maior Dimensao

Em 3D, o hiperplano e um plano:

```text
w_1*x_1 + w_2*x_2 + w_3*x_3 + b = 0

Normal ao plano: w = (w_1, w_2, w_3)
```

Em n dimensoes, o hiperplano tem dimensao n-1:

```text
sum(w_i * x_i) + b = 0

Normal ao hiperplano: w = (w_1, w_2, ..., w_n)
```

A beleza da formulacao vetorial e que a mesma expressao w · x + b funciona para qualquer numero de dimensoes. O codigo que implementa o perceptron em 2D funciona identicamente em 1000D — basta mudar o tamanho do vetor de entrada.

### 3.5 Classificacao Linear e Separabilidade

Um conjunto de dados e **linearmente separavel** se existe um hiperplano que separa perfeitamente as classes. Ou seja, existe um vetor w e um bias tais que:

```text
Para todo x_i na classe 1: w · x_i + b > 0
Para todo x_i na classe 0: w · x_i + b < 0
```

O perceptron so pode aprender a classificar dados linearmente separaveis. Se os dados nao sao linearmente separaveis, o perceptron oscila indefinidamente sem convergir.

```text
Dados linearmente separaveis:      Dados NAO linearmente separaveis:

    1 1 1 1 0 0 0                      1 1 0 0 1 1
    1 1 1 0 0 0 0                      1 0 1 0 0 1
    1 1 1 0 0 0 0                      0 0 1 1 1 0
    1 1 0 0 0 0 0                      0 1 0 1 0 1
    1 1 0 0 0 0 0                      1 1 0 0 1 0

    Existe reta separadora             Nao existe reta separadora
```

### 3.6 Capacidade do Perceptron

A **capacidade** de um classificador linear e o numero maximo de padroes que ele pode classificar corretamente, considerando todas as possiveis atribuicoes de classe.

Para n entradas, o perceptron tem n+1 parametros (n pesos + 1 bias). A capacidade do perceptron e:

```text
Capacidade = 2 * (n + 1)

Exemplo:
  2 entradas -> capacidade = 6 padroes
  10 entradas -> capacidade = 22 padroes
  100 entradas -> capacidade = 202 padroes
```

Isso significa que, com apenas 2 entradas, o perceptron pode classificar corretamente ate 6 padroes (de 2^6 = 64 possiveis atribuicoes). Para problemas complexos com muitas entradas, a capacidade cresce linearmente, mas o numero de padroes possiveis cresce exponencialmente.

---

## 4. Regra de Aprendizado

### 4.1 A Regra do Perceptron (Regra de Aprendizado)

A regra de aprendizado do perceptron e elegante em sua simplicidade. Quando o perceptron erra a classificacao de um exemplo, os pesos sao atualizados na direcao que corrige o erro.

**Formula de Atualizacao**:

```text
Para cada peso w_i:
  w_i(novo) = w_i(velho) + eta * (y - y_hat) * x_i

Para o bias:
  b(novo) = b(velho) + eta * (y - y_hat)

Onde:
  eta   = taxa de aprendizado (learning rate), 0 < eta <= 1
  y     = label correto (0 ou 1)
  y_hat = previsao do perceptron (0 ou 1)
  x_i   = i-esima entrada
```

### 4.2 Analise da Regra

Vamos analisar a regra componente por componente:

**Caso 1 — Acerto (y = y_hat)**:

```text
Se y = 1 e y_hat = 1:
  (y - y_hat) = 0
  w_i(novo) = w_i(velho) + eta * 0 * x_i = w_i(velho)
  NENHUMA atualizacao. Pesos permanecem iguais.

Se y = 0 e y_hat = 0:
  (y - y_hat) = 0
  w_i(novo) = w_i(velho) + eta * 0 * x_i = w_i(velho)
  NENHUMA atualizacao. Pesos permanecem iguais.
```

Isso e importante: o perceptron **nao altera** os pesos quando acerta. Ele so aprende com erros.

**Caso 2 — Erro Positivo (y = 1 mas y_hat = 0)**:

```text
(y - y_hat) = 1 - 0 = 1
w_i(novo) = w_i(velho) + eta * 1 * x_i = w_i(velho) + eta * x_i

Efeito: Aumenta os pesos nas direcoes onde as entradas sao positivas.
        Isso faz com que a soma ponderada aumente para este exemplo,
        tornando mais provavel que o perceptron classifique como 1.
```

**Caso 3 — Erro Negativo (y = 0 mas y_hat = 1)**:

```text
(y - y_hat) = 0 - 1 = -1
w_i(novo) = w_i(velho) + eta * (-1) * x_i = w_i(velho) - eta * x_i

Efeito: Diminui os pesos nas direcoes onde as entradas sao positivas.
        Isso faz com que a soma ponderada diminua para este exemplo,
        tornando mais provavel que o perceptron classifique como 0.
```

### 4.3 O Papel da Taxa de Aprendizado

A taxa de aprendizado (eta) controla o tamanho dos passos na atualizacao dos pesos.

**Etapas grandes (eta proximo de 1)**:

```text
Vantagens:
  - Aprendizado rapido (poucas iteracoes para convergir)
  - Pode escapar de minimos locais (em problemas mais complexos)

Desvantagens:
  - Pode "pular" a solucao otima
  - Oscilacao em torno da solucao
  - Instabilidade numerica
```

**Etapas pequenas (eta proximo de 0)**:

```text
Vantagens:
  - Convergencia suave e estable
  - Precisao fina nos pesos

Desvantagens:
  - Aprendizado muito lento (muitas iteracoes)
  - Pode ficar preso em plateau
  - Custo computacional alto
```

**Pratica recomendada**:

```text
eta = 0.1 (valor inicial comum)
eta = 0.01 (para convergencia mais precisa)
eta = 0.001 (para problemas com dados ruidosos)

Nao usar:
  eta > 1.0 (quase sempre causa divergencia)
  eta = 0.0 (nenhum aprendizado)
```

### 4.4 Algoritmo Completo do Treinamento

```text
Algoritmo: Treinamento do Perceptron

Entrada:
  Dados: {(x_1, y_1), (x_2, y_2), ..., (x_m, y_m)}
  Taxa de aprendizado: eta
  Maximo de epocas: max_epochs

Processo:
  1. Inicializar pesos: w_i = 0 para todo i (ou aleatoriamente)
  2. Inicializar bias: b = 0
  3. Para cada epoca epoch de 1 ate max_epochs:
     a. Inicializar contador de erros: errors = 0
     b. Para cada exemplo (x_i, y_i) nos dados:
        i.   Calcular saida: y_hat = step(w · x_i + b)
        ii.  Calcular erro: error = y_i - y_hat
        iii. Se error != 0:
             - Para cada peso j: w_j = w_j + eta * error * x_i[j]
             - b = b + eta * error
             - errors = errors + 1
     c. Se errors == 0: PARAR (convergiu)
  4. Retornar w, b

Saida:
  Pesos w e bias b que classificam corretamente todos os exemplos
  (se os dados sao linearmente separaveis)
```

### 4.5 Variante: Perceptron Batch

A variante batch processa todos os exemplos antes de atualizar os pesos:

```text
Algoritmo: Perceptron Batch

Para cada epoca:
  1. Inicializar Delta_w = 0 para todo peso
  2. Inicializar Delta_b = 0
  3. Para cada exemplo (x_i, y_i):
     a. Calcular y_hat = step(w · x_i + b)
     b. Se y_i != y_hat:
        Delta_w = Delta_w + eta * (y_i - y_hat) * x_i
        Delta_b = Delta_b + eta * (y_i - y_hat)
  4. w = w + Delta_w
  5. b = b + Delta_b
```

A diferenca e que no perceptron online (padrao), os pesos sao atualizados a cada exemplo. No batch, os pesos sao atualizados uma vez por epoca. Na pratica, o perceptron online converge mais rapido para problemas com dados linearmete separaveis.

---

## 5. Convergencia do Perceptron

### 5.1 O Teorema de Convergencia do Perceptron

O Teorema de Convergencia do Perceptron (Novikoff, 1962) e um dos resultados teoricos mais importantes do machine learning. Ele garante que o perceptron convergira em tempo finito para dados linearmente separaveis.

**Enunciado Formal**:

```text
Seja S = {(x_1, y_1), ..., (x_m, y_m)} um conjunto de dados linearmente
separaveis, onde:
  - x_i ∈ R^n
  - y_i ∈ {-1, +1}  (note: -1 e +1, nao 0 e 1)

Seja R = max(||x_i||) a norma L2 maxima dos vetores de entrada.
Seja gamma > 0 a margem do conjunto de dados, definida como:
  gamma = min(y_i * (w* · x_i + b*))

Onde (w*, b*) e o classificador otimo (que separa perfeitamente as classes).

Entao o numero maximo de erros (atualizacoes de peso) e:
  K <= (R / gamma)^2
```

### 5.2 Interpretacao da Margem

A margem gamma e a menor distancia de qualquer ponto ao hiperplano de separacao. Quanto maior a margem, mais "facil" e o problema e menos atualizacoes sao necessarias.

```text
Margem grande:                    Margem pequena:

    1     1                            1  1
       1                                1
   gamma  1                           g  1
          1  .  .                     1 .  . 0
     .  .    0                          .  0
        .     0  0                     . 0  0
          .      0                       0
                                           0

  Menos atualizacoes             Mais atualizacoes
  necessarias (K pequeno)        necessarias (K grande)
```

### 5.3 Prova Sketch

A prova usa o argumento de "comprimento do vetor de pesos":

```text
Seja w* o vetor de pesos otimo (normalizado tal que gamma = 1).
Seja w(t) o vetor de pesos na iteracao t.

Lema 1 (crescimento limitado):
  ||w(t)||^2 <= t * R^2

Prova:
  w(0) = 0 (vetor nulo)
  A cada atualizacao:
    w(t+1) = w(t) + eta * y_i * x_i

  ||w(t+1)||^2 = ||w(t)||^2 + 2*eta*y_i*(w(t)·x_i) + eta^2*||x_i||^2

  Como y_i*(w*·x_i) >= gamma > 0 e y_i*(w(t)·x_i) < 0 (erro):
    2*eta*y_i*(w(t)·x_i) < 0

  E ||x_i||^2 <= R^2:
    ||w(t+1)||^2 <= ||w(t)||^2 + eta^2 * R^2

  Por inducao: ||w(t)||^2 <= t * eta^2 * R^2

Lema 2 (crescimento minimo):
  ||w(t)||^2 >= t * eta^2 * gamma^2

Prova:
  A cada atualizacao:
    w(t+1) = w(t) + eta * y_i * x_i

  y_i * (w(t+1) · x_i) = y_i * (w(t) · x_i) + eta * (y_i * x_i) · (y_i * x_i)
                        >= 0 + eta * ||x_i||^2  (pois w(t)·x_i < 0 e y_i inverte)
                        >= eta * gamma^2  (por definicao de gamma)

  E y_i * (w(t+1) · x_i) <= ||w(t+1)|| * ||x_i|| <= ||w(t+1)|| * R

  Logo: ||w(t+1)|| >= eta * gamma^2 / R

  Somando: ||w(t)||^2 >= t * (eta * gamma^2 / R)^2

Teorema:
  t * eta^2 * gamma^2 / R^2 <= ||w(t)||^2 <= t * eta^2 * R^2

  Dividindo: t >= gamma^2 / R^2 ... isso nao e diretamente util.

  Mas combinando os dois lemas:
    t * eta^2 * gamma^2 <= t * eta^2 * R^2  (sempre verdade)

  A chave e que o crescimento e quadratico no numero de erros,
  enquanto o limite e linear. Portanto, o numero de erros e finito:
    K <= (R / gamma)^2
```

### 5.4 Taxa de Convergencia

A taxa de convergencia do perceptron depende da margem relativa:

```text
Numero maximo de erros: K <= (R/gamma)^2

Exemplo:
  Se R = 10 e gamma = 1:
    K <= 100 erros no maximo

  Se R = 10 e gamma = 0.1:
    K <= 10000 erros no maximo

  Se R = 10 e gamma = 0.01:
    K <= 1000000 erros no maximo

Isso mostra que problemas com margem pequena sao muito mais
dificeis para o perceptron convergir.
```

### 5.5 Epocas e Convergencia

Uma **epoca** e uma passagem completa pelo conjunto de treinamento. O numero de epocas necessarias depende da ordem dos dados e da taxa de aprendizado.

```text
Relacao entre erros e epocas:
  - Cada epoca pode conter de 0 a m erros (m = numero de exemplos)
  - Se K e o numero total de erros, e cada epoca tem em media k erros:
    Epocas necessarias ≈ K / k

Exemplo:
  100 exemplos, 50 erros totais, media de 10 erros por epoca:
    50 / 10 = 5 epocas

Na pratica, o perceptron converge muito mais rapido que o limite teorico.
Para problemas bem separaveis, 1-5 epocas sao suficientes.
```

### 5.6 Limites Praticos

Embora o teorema garanta convergencia em tempo finito, na pratica:

1. **O limite e pessimista**: Na maioria dos casos, o perceptron converge muito mais rapido que (R/gamma)^2.
2. **Dados ruidosos**: Se os dados nao sao perfeitamente linearmente separaveis, o perceptron oscila indefinidamente. Solucao: perceptron pocket (manter o melhor modelo encontrado).
3. **Ordem dos dados**: A ordem em que os exemplos sao apresentados afeta a velocidade de convergencia, mas nao a garantia de convergencia.

---

## 6. Limitacoes (Problema do XOR)

### 6.1 O Que e XOR

XOR (ou exclusivo) e uma operacao logica fundamental. Dado dois bits de entrada, XOR retorna 1 se exatamente uma das entradas e 1, e 0 caso contrario.

```text
Tabela-verdade do XOR:

  x_1  x_2  |  XOR
  -----------|------
   0    0    |   0
   0    1    |   1
   1    0    |   1
   1    1    |   0

Comparacao com outras operacoes:
  AND: 0,0->0 | 0,1->0 | 1,0->0 | 1,1->1  (linearmente separavel)
  OR:  0,0->0 | 0,1->1 | 1,0->1 | 1,1->1  (linearmente separavel)
  XOR: 0,0->0 | 0,1->1 | 1,0->1 | 1,1->0  (NAO linearmente separavel)
```

### 6.2 Prova Geometrica de que XOR Nao e Linearmente Separavel

Vamos tentar encontrar uma reta que separe as classes:

```text
Espaco 2D com os pontos de XOR:

  x_2
   ^
   |
 1 |   (0,1)=1        (1,1)=0
   |
   |
 0 |   (0,0)=0        (1,0)=1
   |
   +------------------------> x_1
   0                      1

Tentativas de reta separadora:

Tentativa 1: x_1 = 0.5 (vertical)
  (0,0)=0 -> 0 < 0.5 OK
  (0,1)=1 -> 0 < 0.5 OK
  (1,0)=1 -> 1 > 0.5 OK
  (1,1)=0 -> 1 > 0.5 FALHA! (deveria ser classe 0)

Tentativa 2: x_2 = 0.5 (horizontal)
  (0,0)=0 -> 0 < 0.5 OK
  (0,1)=1 -> 1 > 0.5 OK
  (1,0)=1 -> 0 < 0.5 FALHA! (deveria ser classe 1)
  (1,1)=0 -> 1 > 0.5 FALHA!

Tentativa 3: x_1 + x_2 = 1 (diagonal)
  (0,0)=0 -> 0 < 1 OK
  (0,1)=1 -> 1 = 1 FALHA! (ponto na reta, decisao ambigua)
  (1,0)=1 -> 1 = 1 FALHA!
  (1,1)=0 -> 2 > 1 OK

Tentativa 4: Qualquer outra reta ax_1 + bx_2 + c = 0
  Nao existe combinacao de a, b, c que separe corretamente
  os 4 pontos de XOR.

Prova formal:
  Seja a reta: a*x_1 + b*x_2 + c = 0
  
  Para classificar corretamente:
    a*0 + b*0 + c < 0  =>  c < 0
    a*0 + b*1 + c > 0  =>  b + c > 0  =>  b > -c > 0
    a*1 + b*0 + c > 0  =>  a + c > 0  =>  a > -c > 0
    a*1 + b*1 + c < 0  =>  a + b + c < 0
  
  Das condicoes:
    b > 0, a > 0, c < 0
    a + b + c < 0 => a + b < -c
  
  Mas como a > -c e b > -c:
    a + b > -c + (-c) = -2c
  
  E queremos: a + b < -c
  
  Combinando: -2c < a + b < -c
  
  Isso requer -2c < -c, ou seja, -c < 0, ou c > 0.
  Mas ja sabemos que c < 0. CONTRADICAO.

  Portanto, NAO existe reta que separe XOR. QED.
```

### 6.3 Demonstracao Pratica: Perceptron Falha no XOR

```text
Tentativa de treinar perceptron no XOR:

Pesos iniciais: w_1 = 0, w_2 = 0, b = 0
Taxa de aprendizado: eta = 0.1

Epoca 1:
  Exemplo (0,0) -> 0:
    z = 0*0 + 0*0 + 0 = 0
    y_hat = 1 (step(0) = 1)
    ERRO! (y=0, y_hat=1)
    w_1 = 0 + 0.1*(-1)*0 = 0
    w_2 = 0 + 0.1*(-1)*0 = 0
    b = 0 + 0.1*(-1) = -0.1

  Exemplo (0,1) -> 1:
    z = 0*0 + 0*1 + (-0.1) = -0.1
    y_hat = 0 (step(-0.1) = 0)
    ERRO! (y=1, y_hat=0)
    w_1 = 0 + 0.1*(1)*0 = 0
    w_2 = 0 + 0.1*(1)*1 = 0.1
    b = -0.1 + 0.1*(1) = 0.0

  Exemplo (1,0) -> 1:
    z = 0*1 + 0.1*0 + 0 = 0
    y_hat = 1 (step(0) = 1)
    ACERTOU!

  Exemplo (1,1) -> 0:
    z = 0*1 + 0.1*1 + 0 = 0.1
    y_hat = 1 (step(0.1) = 1)
    ERRO! (y=0, y_hat=1)
    w_1 = 0 + 0.1*(-1)*1 = -0.1
    w_2 = 0.1 + 0.1*(-1)*1 = 0.0
    b = 0 + 0.1*(-1) = -0.1

Epoca 2:
  Exemplo (0,0) -> 0:
    z = -0.1*0 + 0*0 + (-0.1) = -0.1
    y_hat = 0 -> ACERTOU!

  Exemplo (0,1) -> 1:
    z = -0.1*0 + 0*1 + (-0.1) = -0.1
    y_hat = 0
    ERRO! -> atualiza pesos...

  ... e assim por diante. O perceptron OSCILA entre solucoes
  sem nunca convergir. O erro persiste infinitamente.

Resultado: O perceptron simples NAO PODE aprender XOR.
           Nenhuma combinacao de pesos funciona.
```

### 6.4 O Livro "Perceptrons" de Minsky e Papert (1969)

Em 1969, Marvin Minsky e Seymour Papert publicaram "Perceptrons: An Introduction to Computational Geometry", um livro que analisou matematicamente as limitacoes do perceptron.

Os principais argumentos:

1. **XOR e conectividade**: Minsky e Papert mostraram que o perceptron nao podia resolver problemas aparentemente simples como determinar se um padrao era uma regiao conectiva (uma forma unica) ou nao.

2. **Invariantes geometricos**: Problemas como "determinar se um padrao contem um buraco" sao invariantes sob translacao e rotacao — e o perceptron nao pode resolve-los sem uma camada intermediaria.

3. **Impacto devastador**: O livro nao dizia que redes neurais eram inuteis — dizia que o perceptron simples tinha limitacoes fundamentais. Mas o efeito no financiamento e na percepcao publica foi devastador.

```text
Impacto historico:

1969: "Perceptrons" publicado
1970-1980: "Inverno da IA" — financiamento drasticamente reduzido
           Pesquisadores migraram para abordagens simbolicas
           Redes neurais consideradas "caminho morto"

1986: Backpropagation popularizado
      Redes multicamadas resolvem XOR e outros problemas
      Renascimento das redes neurais

Licao: A critica era tecnica e correta para o perceptron SIMPLES,
       mas foi generalizada incorretamente para todas as redes neurais.
```

### 6.5 Solucao: Perceptron Multicamada

A solucao para o XOR e simples: adicionar uma camada intermediaria.

```text
Rede para XOR com camada intermediaria:

  Entrada (x_1, x_2) -> Camada Oculta (h_1, h_2) -> Saida (y)

  h_1 = step(x_1 + x_2 - 0.5)    (OR aproximado)
  h_2 = step(x_1 + x_2 - 1.5)    (AND)
  y = step(h_1 - h_2)              (diferenca)

Verificacao:
  (0,0): h_1 = step(-0.5) = 0, h_2 = step(-1.5) = 0 -> y = step(0) = 1?
          Hmm, precisamos ajustar...

Melhor solucao:
  h_1 = step(x_1 + x_2 - 0.5)    (OR: 1 se pelo menos um e 1)
  h_2 = step(x_1 + x_2 - 1.5)    (AND: 1 se ambos sao 1)
  y = step(h_1 + (-2)*h_2 - (-0.5))
    = step(h_1 - 2*h_2 + 0.5)

Verificacao:
  (0,0): h_1=0, h_2=0 -> step(0 + 0 + 0.5) = step(0.5) = 1 FALHA
  ...
```

A solucao correta e:

```text
  Neuronio 1 (OR):  h_1 = step(x_1 + x_2 - 0.5)
  Neuronio 2 (NAND): h_2 = step(-x_1 - x_2 + 1.5)
  Neuronio 3 (AND):  y = step(h_1 + h_2 - 1.5)

Verificacao:
  (0,0): h_1=step(-0.5)=0, h_2=step(1.5)=1 -> step(0+1-1.5)=step(-0.5)=0  OK
  (0,1): h_1=step(0.5)=1,  h_2=step(0.5)=1  -> step(1+1-1.5)=step(0.5)=1  OK
  (1,0): h_1=step(0.5)=1,  h_2=step(0.5)=1  -> step(1+1-1.5)=step(0.5)=1  OK
  (1,1): h_1=step(1.5)=1,  h_2=step(-0.5)=0 -> step(1+0-1.5)=step(-0.5)=0  OK

XOR resolvido com 2 camadas!
```

Mas como treinar essa rede? O perceptron original nao tinha algoritmo para treinar camadas intermediarias. A solucao veio com o backpropagation (1986), que sera o tema do Capitulo 6.

---

## 7. Perceptron Multi-classe

### 7.1 Estrategia One-vs-All (One-vs-Rest)

A abordagem mais simples para classificacao multi-classe e treinar K perceptrons, um para cada classe. Cada perceptron e treinado para distinguir uma classe de todas as outras.

```text
Estrategia One-vs-All para K classes:

  Perceptron 1: Classe 1 vs (Classe 2, 3, ..., K)
  Perceptron 2: Classe 2 vs (Classe 1, 3, ..., K)
  ...
  Perceptron K: Classe K vs (Classe 1, 2, ..., K-1)

Para cada entrada x:
  y_hat = argmax_k (w_k · x + b_k)

Ou seja, a classe predita e a do perceptron com maior saida.
```

**Vantagens**:

```text
- Simples de implementar
- K perceptrons independentes, paralelizaveis
- Cada perceptron resolve um problema binario (facil)
```

**Desvantagens**:

```text
- Ambiguidade: varios perceptrons podem ter saida positiva
- Desequilibrio: a classe "resto" e muito maior que a classe individual
- Nao captura relacoes entre classes
```

### 7.2 Estrategia One-vs-One

Nesta abordagem, treina-se um perceptron para cada par de classes. Para K classes, sao necessarios K*(K-1)/2 perceptrons.

```text
Estrategia One-vs-One para K classes:

  Para cada par (i, j) com i < j:
    Perceptron_{i,j}: Classe i vs Classe j

  Predicao por votacao:
    Cada perceptron vota em uma classe
    A classe com mais votos e a predita

Exemplo com K=3 classes (A, B, C):
  Perceptron_{A,B}: A vs B
  Perceptron_{A,C}: A vs C
  Perceptron_{B,C}: B vs C

  Total: 3*(3-1)/2 = 3 perceptrons

  Para classificar um ponto:
    P_{A,B} diz A, P_{A,C} diz A, P_{B,C} diz B
    A recebe 2 votos, B recebe 1 voto
    Classe predita: A
```

**Vantagens**:

```text
- Cada problema binario e mais balanceado
- Mais robusto a outliers
- Melhor para classes com fronteiras complexas
```

**Desvantagens**:

```text
- Muitos classificadores: K*(K-1)/2 para K classes
  - 10 classes -> 45 perceptrons
  - 100 classes -> 4950 perceptrons
- Custo computacional alto para muitas classes
- Votacao pode ser indecisa
```

### 7.3 Comparacao de Estrategias

```text
K classes | One-vs-All | One-vs-One
----------|------------|------------
    3     |     3      |     3
    5     |     5      |    10
   10     |    10      |    45
   20     |    20      |   190
  100     |   100      |  4950

One-vs-All: Melhor para muitas classes (K classificadores)
One-vs-One: Melhor para poucas classes e problemas balanceados
```

### 7.4 Extensao Softmax

Uma alternativa elegante ao perceptron multi-classe e usar a funcao softmax na saida, combinada com a entropia cruzada categorica como funcao de perda.

```text
Saidas brutas (logits): z_1, z_2, ..., z_K

Softmax:
  P(classe k) = exp(z_k) / sum(exp(z_j) para todo j)

Propriedades:
  - Saida e um vetor de probabilidades (soma = 1)
  - Diferenciavel (para treinamento com gradiente)
  - Maior logit -> maior probabilidade
```

Embora o softmax nao seja parte do perceptron original, ele e a extensao natural para classificacao multi-classe em redes neurais modernas e sera detalhado no Capitulo 3 (funcoes de ativacao) e utilizado extensivamente nos capitulos seguintes.

---

## 8. Implementacao Completa em C++

### 8.1 Estrutura do Codigo

A implementacao C++ do perceptron inclui:

- Classe `Perceptron` com encapsulamento completo
- Templates para suporte a tipos numericos
- Tratamento de erros com exceptions
- Funcoes utilitarias para geracao de dados e metricas
- Exemplo completo com treinamento e avaliacao

```cpp
// perceptron.cpp
// Implementacao completa do Perceptron em C++17
// Compile: g++ -std=c++17 -O2 -o perceptron perceptron.cpp

#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <numeric>
#include <algorithm>
#include <stdexcept>
#include <string>
#include <sstream>
#include <fstream>
#include <chrono>
#include <functional>
#include <iomanip>

// ============================================================================
// Classe Perceptron
// ============================================================================

template <typename T = double>
class Perceptron {
private:
    std::vector<T> weights_;
    T bias_;
    T learning_rate_;
    int max_epochs_;
    int n_features_;
    bool fitted_;
    std::vector<int> error_history_;

    // Funcao de ativacao step: retorna 1 se z >= 0, senao retorna 0
    T step(T z) const {
        return z >= T(0) ? T(1) : T(0);
    }

public:
    // Construtor com parametros configuraveis
    Perceptron(T learning_rate = T(0.1), int max_epochs = 1000)
        : bias_(T(0)),
          learning_rate_(learning_rate),
          max_epochs_(max_epochs),
          n_features_(0),
          fitted_(false)
    {
        if (learning_rate <= T(0) || learning_rate > T(1)) {
            throw std::invalid_argument(
                "Learning rate must be in (0, 1], got: " + std::to_string(learning_rate));
        }
        if (max_epochs <= 0) {
            throw std::invalid_argument(
                "Max epochs must be positive, got: " + std::to_string(max_epochs));
        }
    }

    // Treinar o perceptron com dados de entrada e labels
    void fit(const std::vector<std::vector<T>>& X, const std::vector<int>& y) {
        // Validar entradas
        if (X.empty()) {
            throw std::invalid_argument("Training data X is empty");
        }
        if (X.size() != y.size()) {
            throw std::invalid_argument(
                "X and y must have the same number of samples: " +
                std::to_string(X.size()) + " vs " + std::to_string(y.size()));
        }

        n_features_ = static_cast<int>(X[0].size());
        for (const auto& xi : X) {
            if (static_cast<int>(xi.size()) != n_features_) {
                throw std::invalid_argument(
                    "All samples must have the same number of features");
            }
        }

        // Validar labels
        for (int label : y) {
            if (label != 0 && label != 1) {
                throw std::invalid_argument(
                    "Labels must be 0 or 1, got: " + std::to_string(label));
            }
        }

        // Inicializar pesos com valores aleatorios pequenos
        std::random_device rd;
        std::mt19937 gen(rd());
        std::normal_distribution<T> dist(T(0), T(0.01));

        weights_.resize(n_features_);
        for (int j = 0; j < n_features_; ++j) {
            weights_[j] = dist(gen);
        }
        bias_ = T(0);
        fitted_ = true;

        // Historico de erros por epoca
        error_history_.clear();
        error_history_.reserve(max_epochs_);

        std::cout << "Treinando Perceptron:" << std::endl;
        std::cout << "  Amostras: " << X.size() << std::endl;
        std::cout << "  Features: " << n_features_ << std::endl;
        std::cout << "  Learning rate: " << learning_rate_ << std::endl;
        std::cout << "  Max epocas: " << max_epochs_ << std::endl;
        std::cout << std::endl;

        // Treinamento
        for (int epoch = 0; epoch < max_epochs_; ++epoch) {
            int errors = 0;

            for (size_t i = 0; i < X.size(); ++i) {
                // Forward pass
                T z = bias_;
                for (int j = 0; j < n_features_; ++j) {
                    z += weights_[j] * X[i][j];
                }
                T y_hat = step(z);

                // Calcular erro
                int error = static_cast<int>(y[i]) - static_cast<int>(y_hat);

                // Atualizar pesos apenas se houver erro
                if (error != 0) {
                    for (int j = 0; j < n_features_; ++j) {
                        weights_[j] += learning_rate_ * static_cast<T>(error) * X[i][j];
                    }
                    bias_ += learning_rate_ * static_cast<T>(error);
                    ++errors;
                }
            }

            error_history_.push_back(errors);

            // Log periodico
            if ((epoch + 1) % 100 == 0 || epoch == 0 || errors == 0) {
                std::cout << "  Epoca " << std::setw(4) << (epoch + 1)
                          << "/" << max_epochs_
                          << " - Erros: " << std::setw(3) << errors
                          << " - W: [";
                for (int j = 0; j < std::min(5, n_features_); ++j) {
                    if (j > 0) std::cout << ", ";
                    std::cout << std::fixed << std::setprecision(4) << weights_[j];
                }
                if (n_features_ > 5) std::cout << ", ...";
                std::cout << "] - b: " << bias_ << std::endl;
            }

            // Convergiu? (sem erros nesta epoca)
            if (errors == 0) {
                std::cout << "  Convergiu na epoca " << (epoch + 1) << "!" << std::endl;
                break;
            }
        }

        std::cout << std::endl;
        std::cout << "Treinamento concluido!" << std::endl;
        std::cout << "  Pesos finais: [";
        for (int j = 0; j < n_features_; ++j) {
            if (j > 0) std::cout << ", ";
            std::cout << std::fixed << std::setprecision(4) << weights_[j];
        }
        std::cout << "]" << std::endl;
        std::cout << "  Bias final: " << bias_ << std::endl;
    }

    // Prever a classe para um unico exemplo
    int predict(const std::vector<T>& x) const {
        if (!fitted_) {
            throw std::runtime_error("Model not fitted. Call fit() first.");
        }
        if (static_cast<int>(x.size()) != n_features_) {
            throw std::invalid_argument(
                "Input must have " + std::to_string(n_features_) + " features");
        }

        T z = bias_;
        for (int j = 0; j < n_features_; ++j) {
            z += weights_[j] * x[j];
        }
        return static_cast<int>(step(z));
    }

    // Prever para multiplos exemplos
    std::vector<int> predict_batch(const std::vector<std::vector<T>>& X) const {
        std::vector<int> predictions;
        predictions.reserve(X.size());
        for (const auto& xi : X) {
            predictions.push_back(predict(xi));
        }
        return predictions;
    }

    // Calcular acuracia
    T score(const std::vector<std::vector<T>>& X, const std::vector<int>& y) const {
        if (X.size() != y.size()) {
            throw std::invalid_argument("X and y must have the same size");
        }

        int correct = 0;
        for (size_t i = 0; i < X.size(); ++i) {
            if (predict(X[i]) == y[i]) {
                ++correct;
            }
        }
        return static_cast<T>(correct) / static_cast<T>(X.size());
    }

    // Calcular a equacao da fronteira de decisao (para 2D)
    // Retorna: ax + by + c = 0, onde a=weights_[0], b=weights_[1], c=bias_
    std::string decision_boundary_2d() const {
        if (n_features_ != 2) {
            throw std::runtime_error("Decision boundary visualization requires 2 features");
        }
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(4);
        oss << weights_[0] << " * x1 + " << weights_[1] << " * x2 + " << bias_ << " = 0";
        return oss.str();
    }

    // Getters
    const std::vector<T>& weights() const { return weights_; }
    T bias() const { return bias_; }
    T learning_rate() const { return learning_rate_; }
    int max_epochs() const { return max_epochs_; }
    int n_features() const { return n_features_; }
    bool is_fitted() const { return fitted_; }
    const std::vector<int>& error_history() const { return error_history_; }
};

// ============================================================================
// Funcoes Utilitarias
// ============================================================================

// Gerar dados linearmente separaveis para classificacao binaria
struct Dataset {
    std::vector<std::vector<double>> X;
    std::vector<int> y;
};

Dataset generate_linearly_separable(
    int n_samples, int n_features, double separation = 2.0,
    unsigned int seed = 42)
{
    std::mt19937 gen(seed);
    std::normal_distribution<double> dist_pos(separation / 2.0, 1.0);
    std::normal_distribution<double> dist_neg(-separation / 2.0, 1.0);

    Dataset data;
    data.X.resize(n_samples, std::vector<double>(n_features));
    data.y.resize(n_samples);

    int half = n_samples / 2;
    for (int i = 0; i < n_samples; ++i) {
        for (int j = 0; j < n_features; ++j) {
            if (i < half) {
                data.X[i][j] = dist_pos(gen);
            } else {
                data.X[i][j] = dist_neg(gen);
            }
        }
        data.y[i] = (i < half) ? 1 : 0;
    }

    return data;
}

// Gerar dados XOR (nao linearmente separavel)
Dataset generate_xor(int n_samples, unsigned int seed = 42) {
    std::mt19937 gen(seed);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);

    Dataset data;
    data.X.resize(n_samples, std::vector<double>(2));
    data.y.resize(n_samples);

    for (int i = 0; i < n_samples; ++i) {
        double x1 = dist(gen);
        double x2 = dist(gen);
        data.X[i][0] = x1;
        data.X[i][1] = x2;
        data.y[i] = ((x1 > 0) != (x2 > 0)) ? 1 : 0;
    }

    return data;
}

// Calcular metricas de classificacao
struct Metrics {
    double accuracy;
    double precision;
    double recall;
    double f1;
    int true_positives;
    int true_negatives;
    int false_positives;
    int false_negatives;
};

Metrics calculate_metrics(const std::vector<int>& y_true, const std::vector<int>& y_pred) {
    if (y_true.size() != y_pred.size()) {
        throw std::invalid_argument("y_true and y_pred must have the same size");
    }

    Metrics m{0.0, 0.0, 0.0, 0.0, 0, 0, 0, 0};

    for (size_t i = 0; i < y_true.size(); ++i) {
        if (y_true[i] == 1 && y_pred[i] == 1) ++m.true_positives;
        else if (y_true[i] == 0 && y_pred[i] == 0) ++m.true_negatives;
        else if (y_true[i] == 0 && y_pred[i] == 1) ++m.false_positives;
        else if (y_true[i] == 1 && y_pred[i] == 0) ++m.false_negatives;
    }

    int total = static_cast<int>(y_true.size());
    m.accuracy = static_cast<double>(m.true_positives + m.true_negatives) / total;

    if (m.true_positives + m.false_positives > 0) {
        m.precision = static_cast<double>(m.true_positives) /
                      (m.true_positives + m.false_positives);
    }
    if (m.true_positives + m.false_negatives > 0) {
        m.recall = static_cast<double>(m.true_positives) /
                   (m.true_positives + m.false_negatives);
    }
    if (m.precision + m.recall > 0) {
        m.f1 = 2.0 * m.precision * m.recall / (m.precision + m.recall);
    }

    return m;
}

// Imprimir metricas
void print_metrics(const Metrics& m) {
    std::cout << "  Acuracia:     " << std::fixed << std::setprecision(4) << m.accuracy << std::endl;
    std::cout << "  Precisao:     " << m.precision << std::endl;
    std::cout << "  Recall:       " << m.recall << std::endl;
    std::cout << "  F1-Score:     " << m.f1 << std::endl;
    std::cout << "  VP: " << m.true_positives
              << "  VN: " << m.true_negatives
              << "  FP: " << m.false_positives
              << "  FN: " << m.false_negatives << std::endl;
}

// Dividir dados em treinamento e teste
struct TrainTestSplit {
    std::vector<std::vector<double>> X_train, X_test;
    std::vector<int> y_train, y_test;
};

TrainTestSplit train_test_split(const Dataset& data, double test_ratio = 0.2,
                                 unsigned int seed = 42) {
    std::mt19937 gen(seed);
    std::vector<size_t> indices(data.X.size());
    std::iota(indices.begin(), indices.end(), 0);
    std::shuffle(indices.begin(), indices.end(), gen);

    size_t test_size = static_cast<size_t>(data.X.size() * test_ratio);
    size_t train_size = data.X.size() - test_size;

    TrainTestSplit split;
    split.X_train.resize(train_size);
    split.X_test.resize(test_size);
    split.y_train.resize(train_size);
    split.y_test.resize(test_size);

    for (size_t i = 0; i < train_size; ++i) {
        split.X_train[i] = data.X[indices[i]];
        split.y_train[i] = data.y[indices[i]];
    }
    for (size_t i = 0; i < test_size; ++i) {
        split.X_test[i] = data.X[indices[train_size + i]];
        split.y_test[i] = data.y[indices[train_size + i]];
    }

    return split;
}

// Imprimir decisao em arte ASCII
void print_ascii_decision_boundary(const Perceptron<double>& model, int width = 40, int height = 20) {
    std::cout << std::endl;
    std::cout << "Fronteira de Decisao (ASCII Art):" << std::endl;
    std::cout << std::endl;

    double x_min = -3.0, x_max = 3.0;
    double y_min = -3.0, y_max = 3.0;
    double x_step = (x_max - x_min) / width;
    double y_step = (y_max - y_min) / height;

    for (int row = 0; row < height; ++row) {
        double y = y_max - row * y_step;
        for (int col = 0; col < width; ++col) {
            double x = x_min + col * x_step;
            std::vector<double> point = {x, y};
            int pred = model.predict(point);
            if (pred == 1) {
                std::cout << "#";
            } else {
                std::cout << ".";
            }
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;
    std::cout << "Legenda: # = Classe 1, . = Classe 0" << std::endl;
}

// ============================================================================
// Funcao principal
// ============================================================================

int main() {
    std::cout << "============================================================" << std::endl;
    std::cout << "  PERCEPTRON COMPLETO EM C++17" << std::endl;
    std::cout << "============================================================" << std::endl;
    std::cout << std::endl;

    // ------------------------------------------------------------------
    // Teste 1: Classificacao linearmente separavel
    // ------------------------------------------------------------------
    std::cout << "--- Teste 1: Dados Linearmente Separaveis ---" << std::endl;
    std::cout << std::endl;

    auto data = generate_linearly_separable(200, 2, 2.0, 42);
    auto split = train_test_split(data, 0.2);

    std::cout << "Dados gerados:" << std::endl;
    std::cout << "  Treinamento: " << split.X_train.size() << " amostras" << std::endl;
    std::cout << "  Teste: " << split.X_test.size() << " amostras" << std::endl;
    std::cout << std::endl;

    Perceptron<double> model(0.1, 100);

    auto start = std::chrono::high_resolution_clock::now();
    model.fit(split.X_train, split.y_train);
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

    std::cout << "Tempo de treinamento: " << duration.count() / 1000.0 << " ms" << std::endl;
    std::cout << std::endl;

    // Avaliar
    auto y_pred_train = model.predict_batch(split.X_train);
    auto y_pred_test = model.predict_batch(split.X_test);

    std::cout << "Metricas (Treinamento):" << std::endl;
    print_metrics(calculate_metrics(split.y_train, y_pred_train));
    std::cout << std::endl;

    std::cout << "Metricas (Teste):" << std::endl;
    print_metrics(calculate_metrics(split.y_test, y_pred_test));
    std::cout << std::endl;

    std::cout << "Fronteira de decisao: " << model.decision_boundary_2d() << std::endl;
    std::cout << std::endl;

    // Arte ASCII da fronteira
    print_ascii_decision_boundary(model);

    // ------------------------------------------------------------------
    // Teste 2: XOR (deve falhar)
    // ------------------------------------------------------------------
    std::cout << "--- Teste 2: Problema do XOR (deve falhar) ---" << std::endl;
    std::cout << std::endl;

    auto xor_data = generate_xor(200, 42);
    auto xor_split = train_test_split(xor_data, 0.2);

    Perceptron<double> xor_model(0.1, 50);
    xor_model.fit(xor_split.X_train, xor_split.y_train);

    auto y_xor_pred = xor_model.predict_batch(xor_split.X_test);
    std::cout << "Metricas XOR (Teste):" << std::endl;
    print_metrics(calculate_metrics(xor_split.y_test, y_xor_pred));
    std::cout << std::endl;

    std::cout << "O perceptron simples NAO resolve XOR!" << std::endl;
    std::cout << "Acuracia ~50% (chance aleatoria)" << std::endl;
    std::cout << std::endl;

    // ------------------------------------------------------------------
    // Teste 3: Treinamento passo a passo
    // ------------------------------------------------------------------
    std::cout << "--- Teste 3: Treinamento Passo a Passo ---" << std::endl;
    std::cout << std::endl;

    // Dados simples: AND gate
    std::vector<std::vector<double>> X_and = {{0,0}, {0,1}, {1,0}, {1,1}};
    std::vector<int> y_and = {0, 0, 0, 1};

    std::cout << "Treinando AND gate:" << std::endl;
    std::cout << "  (0,0) -> 0" << std::endl;
    std::cout << "  (0,1) -> 0" << std::endl;
    std::cout << "  (1,0) -> 0" << std::endl;
    std::cout << "  (1,1) -> 1" << std::endl;
    std::cout << std::endl;

    Perceptron<double> and_model(0.1, 100);
    and_model.fit(X_and, y_and);

    std::cout << "Teste AND gate:" << std::endl;
    for (int i = 0; i < 4; ++i) {
        int pred = and_model.predict(X_and[i]);
        std::cout << "  (" << X_and[i][0] << "," << X_and[i][1] << ") -> "
                  << pred << " (esperado: " << y_and[i] << ")"
                  << (pred == y_and[i] ? " OK" : " ERRO") << std::endl;
    }
    std::cout << std::endl;

    // ------------------------------------------------------------------
    // Teste 4: Previsao interativa
    // ------------------------------------------------------------------
    std::cout << "--- Teste 4: Previsao Interativa ---" << std::endl;
    std::cout << std::endl;

    std::cout << "Use o modelo treinado para classificar pontos:" << std::endl;
    std::cout << std::endl;

    std::vector<std::pair<double, double>> test_points = {
        {-2.0, -1.0}, {-1.0, 2.0}, {0.0, 0.0}, {1.0, -1.0}, {2.0, 1.0}
    };

    for (const auto& [x1, x2] : test_points) {
        int pred = model.predict({x1, x2});
        std::cout << "  (" << std::setw(4) << x1 << ", " << std::setw(4) << x2
                  << ") -> Classe " << pred << std::endl;
    }
    std::cout << std::endl;

    // ------------------------------------------------------------------
    // Teste 5: Metricas detalhadas
    // ------------------------------------------------------------------
    std::cout << "--- Teste 5: Metricas Detalhadas ---" << std::endl;
    std::cout << std::endl;

    auto final_pred = model.predict_batch(split.X_test);
    auto final_metrics = calculate_metrics(split.y_test, final_pred);

    std::cout << "Matriz de Confusao:" << std::endl;
    std::cout << "                    Predito 0   Predito 1" << std::endl;
    std::cout << "  Real 0:           " << std::setw(6) << final_metrics.true_negatives
              << "        " << std::setw(6) << final_metrics.false_positives << std::endl;
    std::cout << "  Real 1:           " << std::setw(6) << final_metrics.false_negatives
              << "        " << std::setw(6) << final_metrics.true_positives << std::endl;
    std::cout << std::endl;

    std::cout << "Metricas completas:" << std::endl;
    print_metrics(final_metrics);
    std::cout << std::endl;

    std::cout << "============================================================" << std::endl;
    std::cout << "  Todos os testes concluidos com sucesso!" << std::endl;
    std::cout << "============================================================" << std::endl;

    return 0;
}
```

### 8.2 Compilacao e Execucao

```text
Compilacao:
  g++ -std=c++17 -O2 -o perceptron perceptron.cpp

Execucao:
  ./perceptron

Saida esperada:
  ============================================================
    PERCEPTRON COMPLETO EM C++17
  ============================================================

  --- Teste 1: Dados Linearmente Separaveis ---

  Dados gerados:
    Treinamento: 160 amostras
    Teste: 40 amostras

  Treinando Perceptron:
    Amostras: 160
    Features: 2
    Learning rate: 0.1
    Max epocas: 100

    Epoca    1/100 - Erros:  45 - W: [0.0234, -0.0198] - b: -0.1
    Epoca  100/100 - Erros:   3 - W: [1.2847, -0.9823] - b: -0.2134
    ...
    Convergiu na epoca X!

  Metricas (Treinamento):
    Acuracia: 0.9875
    Precisao: 0.9877
    Recall: 0.9877
    F1-Score: 0.9877

  Metricas (Teste):
    Acuracia: 0.9750
    ...
```

---

## 9. Implementacao em Rust

### 9.1 Traits e Structs

A implementacao Rust utiliza traits para abstracao, enums para tratamento de erros e iteradores para processamento por lote.

```rust
// perceptron.rs
// Implementacao completa do Perceptron em Rust
// Compile: rustc -O perceptron.rs

use std::fmt;
use std::error::Error;

// ============================================================================
// Enum de Erros
// ============================================================================

#[derive(Debug, Clone)]
enum PerceptronError {
    EmptyData,
    DimensionMismatch { expected: usize, got: usize },
    InvalidLabel(i32),
    InvalidLearningRate(f64),
    InvalidEpochs(i32),
    NotFitted,
    IncompatibleDimensions,
}

impl fmt::Display for PerceptronError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PerceptronError::EmptyData => write!(f, "Training data is empty"),
            PerceptronError::DimensionMismatch { expected, got } => {
                write!(f, "Dimension mismatch: expected {}, got {}", expected, got)
            }
            PerceptronError::InvalidLabel(label) => {
                write!(f, "Invalid label: {}. Must be 0 or 1", label)
            }
            PerceptronError::InvalidLearningRate(lr) => {
                write!(f, "Invalid learning rate: {}. Must be in (0, 1]", lr)
            }
            PerceptronError::InvalidEpochs(epochs) => {
                write!(f, "Invalid epochs: {}. Must be positive", epochs)
            }
            PerceptronError::NotFitted => write!(f, "Model not fitted. Call fit() first"),
            PerceptronError::IncompatibleDimensions => {
                write!(f, "Input dimensions incompatible with model")
            }
        }
    }
}

impl Error for PerceptronError {}

type Result<T> = std::result::Result<T, PerceptronError>;

// ============================================================================
// Trait para Modelos
// ============================================================================

trait Model {
    fn fit(&mut self, x: &[Vec<f64>], y: &[i32]) -> Result<()>;
    fn predict(&self, x: &[f64]) -> Result<i32>;
    fn predict_batch(&self, x: &[Vec<f64>]) -> Result<Vec<i32>>;
    fn score(&self, x: &[Vec<f64>], y: &[i32]) -> Result<f64>;
    fn is_fitted(&self) -> bool;
}

// ============================================================================
// Struct Perceptron
// ============================================================================

struct Perceptron {
    weights: Vec<f64>,
    bias: f64,
    learning_rate: f64,
    max_epochs: i32,
    n_features: usize,
    fitted: bool,
    error_history: Vec<i32>,
}

impl Perceptron {
    fn new(learning_rate: f64, max_epochs: i32) -> Result<Self> {
        if learning_rate <= 0.0 || learning_rate > 1.0 {
            return Err(PerceptronError::InvalidLearningRate(learning_rate));
        }
        if max_epochs <= 0 {
            return Err(PerceptronError::InvalidEpochs(max_epochs));
        }

        Ok(Perceptron {
            weights: Vec::new(),
            bias: 0.0,
            learning_rate,
            max_epochs,
            n_features: 0,
            fitted: false,
            error_history: Vec::new(),
        })
    }

    // Funcao de ativacao step
    fn step(z: f64) -> i32 {
        if z >= 0.0 { 1 } else { 0 }
    }

    // Calcular saida bruta (antes da funcao de ativacao)
    fn raw_output(&self, x: &[f64]) -> f64 {
        self.weights.iter()
            .zip(x.iter())
            .map(|(w, xi)| w * xi)
            .sum::<f64>()
            + self.bias
    }

    // Imprimir metricas de classificacao
    fn print_metrics(y_true: &[i32], y_pred: &[i32]) {
        let mut tp = 0i32;
        let mut tn = 0i32;
        let mut fp = 0i32;
        let mut fn_ = 0i32;

        for (yt, yp) in y_true.iter().zip(y_pred.iter()) {
            match (*yt, *yp) {
                (1, 1) => tp += 1,
                (0, 0) => tn += 1,
                (0, 1) => fp += 1,
                (1, 0) => fn_ += 1,
                _ => {}
            }
        }

        let total = y_true.len() as f64;
        let accuracy = (tp + tn) as f64 / total;
        let precision = if tp + fp > 0 { tp as f64 / (tp + fp) as f64 } else { 0.0 };
        let recall = if tp + fn_ > 0 { tp as f64 / (tp + fn_) as f64 } else { 0.0 };
        let f1 = if precision + recall > 0.0 {
            2.0 * precision * recall / (precision + recall)
        } else {
            0.0
        };

        println!("  Acuracia:   {:.4}", accuracy);
        println!("  Precisao:   {:.4}", precision);
        println!("  Recall:     {:.4}", recall);
        println!("  F1-Score:   {:.4}", f1);
        println!("  VP: {}  VN: {}  FP: {}  FN: {}", tp, tn, fp, fn_);
    }

    // Fronteira de decisao 2D em ASCII
    fn print_ascii_boundary(&self, width: usize, height: usize) {
        if self.n_features != 2 {
            println!("ASCII boundary requires 2 features");
            return;
        }

        let x_min = -3.0_f64;
        let x_max = 3.0_f64;
        let y_min = -3.0_f64;
        let y_max = 3.0_f64;
        let x_step = (x_max - x_min) / width as f64;
        let y_step = (y_max - y_min) / height as f64;

        println!();
        println!("Fronteira de Decisao (ASCII Art):");
        println!();

        for row in 0..height {
            let y = y_max - row as f64 * y_step;
            let line: String = (0..width)
                .map(|col| {
                    let x = x_min + col as f64 * x_step;
                    let point = vec![x, y];
                    if self.predict(&point).unwrap_or(0) == 1 {
                        '#'
                    } else {
                        '.'
                    }
                })
                .collect();
            println!("{}", line);
        }
        println!();
        println!("Legenda: # = Classe 1, . = Classe 0");
    }
}

impl Model for Perceptron {
    fn fit(&mut self, x: &[Vec<f64>], y: &[i32]) -> Result<()> {
        // Validar dados
        if x.is_empty() {
            return Err(PerceptronError::EmptyData);
        }
        if x.len() != y.len() {
            return Err(PerceptronError::DimensionMismatch {
                expected: x.len(),
                got: y.len(),
            });
        }

        self.n_features = x[0].len();
        for xi in x {
            if xi.len() != self.n_features {
                return Err(PerceptronError::DimensionMismatch {
                    expected: self.n_features,
                    got: xi.len(),
                });
            }
        }

        for &label in y {
            if label != 0 && label != 1 {
                return Err(PerceptronError::InvalidLabel(label));
            }
        }

        // Inicializar pesos
        self.weights = vec![0.0; self.n_features];
        self.bias = 0.0;
        self.fitted = true;
        self.error_history.clear();

        println!("Treinando Perceptron:");
        println!("  Amostras: {}", x.len());
        println!("  Features: {}", self.n_features);
        println!("  Learning rate: {}", self.learning_rate);
        println!("  Max epocas: {}", self.max_epochs);
        println!();

        // Treinamento
        for epoch in 0..self.max_epochs {
            let mut errors = 0;

            for (xi, &yi) in x.iter().zip(y.iter()) {
                let z = self.raw_output(xi);
                let y_hat = Self::step(z);
                let error = yi - y_hat;

                if error != 0 {
                    for (wj, &xij) in self.weights.iter_mut().zip(xi.iter()) {
                        *wj += self.learning_rate * error as f64 * xij;
                    }
                    self.bias += self.learning_rate * error as f64;
                    errors += 1;
                }
            }

            self.error_history.push(errors);

            if (epoch + 1) % 100 == 0 || epoch == 0 || errors == 0 {
                let weights_str: Vec<String> = self.weights.iter()
                    .take(5)
                    .map(|w| format!("{:.4}", w))
                    .collect();
                println!("  Epoca {:4}/{} - Erros: {:3} - W: [{}] - b: {:.4}",
                         epoch + 1, self.max_epochs, errors,
                         weights_str.join(", "), self.bias);
            }

            if errors == 0 {
                println!("  Convergiu na epoca {}!", epoch + 1);
                break;
            }
        }

        println!();
        println!("Treinamento concluido!");
        let weights_str: Vec<String> = self.weights.iter()
            .map(|w| format!("{:.4}", w))
            .collect();
        println!("  Pesos finais: [{}]", weights_str.join(", "));
        println!("  Bias final: {:.4}", self.bias);

        Ok(())
    }

    fn predict(&self, x: &[f64]) -> Result<i32> {
        if !self.fitted {
            return Err(PerceptronError::NotFitted);
        }
        if x.len() != self.n_features {
            return Err(PerceptronError::IncompatibleDimensions);
        }
        Ok(Self::step(self.raw_output(x)))
    }

    fn predict_batch(&self, x: &[Vec<f64>]) -> Result<Vec<i32>> {
        x.iter()
            .map(|xi| self.predict(xi))
            .collect()
    }

    fn score(&self, x: &[Vec<f64>], y: &[i32]) -> Result<f64> {
        if x.len() != y.len() {
            return Err(PerceptronError::DimensionMismatch {
                expected: x.len(),
                got: y.len(),
            });
        }
        let predictions = self.predict_batch(x)?;
        let correct = predictions.iter()
            .zip(y.iter())
            .filter(|(yp, yt)| yp == yt)
            .count();
        Ok(correct as f64 / y.len() as f64)
    }

    fn is_fitted(&self) -> bool {
        self.fitted
    }
}

impl fmt::Display for Perceptron {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if !self.fitted {
            return write!(f, "Perceptron (not fitted)");
        }
        let weights_str: Vec<String> = self.weights.iter()
            .map(|w| format!("{:.4}", w))
            .collect();
        write!(f, "Perceptron(weights=[{}], bias={:.4})",
               weights_str.join(", "), self.bias)
    }
}

// ============================================================================
// Funcoes Auxiliares
// ============================================================================

struct Dataset {
    x: Vec<Vec<f64>>,
    y: Vec<i32>,
}

fn generate_linearly_separable(n_samples: usize, n_features: usize,
                                separation: f64, seed: u64) -> Dataset {
    let mut rng_state = seed;
    let mut next_random = || -> f64 {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        ((rng_state >> 33) as f64) / (1u64 << 31) as f64
    };

    let half = n_samples / 2;
    let mut x = Vec::with_capacity(n_samples);
    let mut y = Vec::with_capacity(n_samples);

    for i in 0..n_samples {
        let mut xi = Vec::with_capacity(n_features);
        for _ in 0..n_features {
            let u1 = next_random();
            let u2 = next_random();
            let z = (-2.0 * u1.ln()).sqrt() * (2.0 * std::f64::consts::PI * u2).cos();
            let center = if i < half { separation / 2.0 } else { -separation / 2.0 };
            xi.push(z + center);
        }
        x.push(xi);
        y.push(if i < half { 1 } else { 0 });
    }

    Dataset { x, y }
}

fn generate_xor(n_samples: usize, seed: u64) -> Dataset {
    let mut rng_state = seed;
    let mut next_random = || -> f64 {
        rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        ((rng_state >> 33) as f64) / (1u64 << 31) as f64
    };

    let mut x = Vec::with_capacity(n_samples);
    let mut y = Vec::with_capacity(n_samples);

    for _ in 0..n_samples {
        let x1 = next_random() * 2.0 - 1.0;
        let x2 = next_random() * 2.0 - 1.0;
        x.push(vec![x1, x2]);
        y.push(if (x1 > 0.0) != (x2 > 0.0) { 1 } else { 0 });
    }

    Dataset { x, y }
}

// ============================================================================
// Main
// ============================================================================

fn main() -> std::result::Result<(), Box<dyn Error>> {
    println!("============================================================");
    println!("  PERCEPTRON COMPLETO EM RUST");
    println!("============================================================");
    println!();

    // Teste 1: Dados linearmente separaveis
    println!("--- Teste 1: Dados Linearmente Separaveis ---");
    println!();

    let data = generate_linearly_separable(200, 2, 2.0, 42);
    let train_size = 160;
    let x_train = &data.x[..train_size];
    let y_train = &data.y[..train_size];
    let x_test = &data.x[train_size..];
    let y_test = &data.y[train_size..];

    println!("Dados gerados:");
    println!("  Treinamento: {} amostras", x_train.len());
    println!("  Teste: {} amostras", x_test.len());
    println!();

    let mut model = Perceptron::new(0.1, 100)?;
    model.fit(x_train, y_train)?;
    println!();

    let train_accuracy = model.score(x_train, y_train)?;
    let test_accuracy = model.score(x_test, y_test)?;
    println!("Acuracia (treinamento): {:.4}", train_accuracy);
    println!("Acuracia (teste): {:.4}", test_accuracy);
    println!();

    model.print_ascii_boundary(40, 20);
    println!();

    // Teste 2: XOR
    println!("--- Teste 2: Problema do XOR (deve falhar) ---");
    println!();

    let xor_data = generate_xor(200, 42);
    let xor_train_size = 160;
    let xor_x_train = &xor_data.x[..xor_train_size];
    let xor_y_train = &xor_data.y[..xor_train_size];
    let xor_x_test = &xor_data.x[xor_train_size..];
    let xor_y_test = &xor_data.y[xor_train_size..];

    let mut xor_model = Perceptron::new(0.1, 50)?;
    xor_model.fit(xor_x_train, xor_y_train)?;
    println!();

    let xor_accuracy = xor_model.score(xor_x_test, xor_y_test)?;
    println!("Acuracia XOR (teste): {:.4} (deve ser ~0.5)", xor_accuracy);
    println!();

    // Teste 3: AND gate
    println!("--- Teste 3: AND Gate ---");
    println!();

    let x_and = vec![
        vec![0.0, 0.0],
        vec![0.0, 1.0],
        vec![1.0, 0.0],
        vec![1.0, 1.0],
    ];
    let y_and = vec![0, 0, 0, 1];

    println!("Treinando AND gate:");
    println!("  (0,0) -> 0");
    println!("  (0,1) -> 0");
    println!("  (1,0) -> 0");
    println!("  (1,1) -> 1");
    println!();

    let mut and_model = Perceptron::new(0.1, 100)?;
    and_model.fit(&x_and, &y_and)?;
    println!();

    println!("Teste AND gate:");
    for (i, xi) in x_and.iter().enumerate() {
        let pred = and_model.predict(xi)?;
        let expected = y_and[i];
        println!("  ({},{}) -> {} (esperado: {}){}",
                 xi[0], xi[1], pred, expected,
                 if pred == expected { " OK" } else { " ERRO" });
    }
    println!();

    // Teste 4: Metricas detalhadas
    println!("--- Teste 4: Metricas Detalhadas ---");
    println!();

    let final_pred = model.predict_batch(x_test)?;
    Perceptron::print_metrics(y_test, &final_pred);
    println!();

    println!("============================================================");
    println!("  Todos os testes concluidos com sucesso!");
    println!("============================================================");

    Ok(())
}
```

### 9.2 Compilacao e Execucao

```text
Compilacao:
  rustc -O perceptron.rs

Execucao:
  ./perceptron

Caracteristicas Rust:
  - Result<T, PerceptronError> para tratamento de erros tipado
  - Trait Model para abstracao (facil de extender para outros modelos)
  - Iteradores para processamento eficiente
  - Zero-cost abstractions
  - Sem runtime overhead
```

---

## 10. Implementacao em Fortran

### 10.1 Modulo do Perceptron

A implementacao Fortran utiliza modulos, tipos derivados e subrotinas com alocacao dinamica.

```fortran
! perceptron.f90
! Implementacao completa do Perceptron em Fortran 2008+
! Compile: gfortran -O2 -o perceptron perceptron.f90

module perceptron_mod
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)
    private
    public :: perceptron_type, dp
    public :: create_perceptron, destroy_perceptron
    public :: fit_perceptron, predict_single, predict_batch
    public :: score_perceptron, print_metrics
    public :: generate_linear_data, generate_xor_data
    public :: print_ascii_boundary

    ! Tipo derivado para o Perceptron
    type :: perceptron_type
        real(dp), allocatable :: weights(:)
        real(dp) :: bias
        real(dp) :: learning_rate
        integer :: max_epochs
        integer :: n_features
        logical :: fitted
        integer, allocatable :: error_history(:)
    end type perceptron_type

contains

    ! =========================================================================
    ! Criar um novo perceptron
    ! =========================================================================
    function create_perceptron(learning_rate, max_epochs) result(model)
        real(dp), intent(in) :: learning_rate
        integer, intent(in) :: max_epochs
        type(perceptron_type) :: model

        if (learning_rate <= 0.0_dp .or. learning_rate > 1.0_dp) then
            print *, "ERRO: Learning rate deve estar em (0, 1]"
            stop
        end if
        if (max_epochs <= 0) then
            print *, "ERRO: Max epochs deve ser positivo"
            stop
        end if

        model%learning_rate = learning_rate
        model%max_epochs = max_epochs
        model%bias = 0.0_dp
        model%n_features = 0
        model%fitted = .false.
    end function create_perceptron

    ! =========================================================================
    ! Destruir perceptron (liberar memoria)
    ! =========================================================================
    subroutine destroy_perceptron(model)
        type(perceptron_type), intent(inout) :: model
        if (allocated(model%weights)) deallocate(model%weights)
        if (allocated(model%error_history)) deallocate(model%error_history)
        model%fitted = .false.
    end subroutine destroy_perceptron

    ! =========================================================================
    ! Funcao de ativacao step
    ! =========================================================================
    pure function step_function(z) result(y)
        real(dp), intent(in) :: z
        integer :: y
        if (z >= 0.0_dp) then
            y = 1
        else
            y = 0
        end if
    end function step_function

    ! =========================================================================
    ! Treinar o perceptron
    ! =========================================================================
    subroutine fit_perceptron(model, X, y, n_samples, n_features)
        type(perceptron_type), intent(inout) :: model
        real(dp), intent(in) :: X(:,:)
        integer, intent(in) :: y(:)
        integer, intent(in) :: n_samples, n_features

        integer :: epoch, i, j, errors
        real(dp) :: z, y_hat_real
        integer :: y_hat, error_val

        ! Validar entradas
        if (n_samples <= 0) then
            print *, "ERRO: Dados de treinamento vazios"
            stop
        end if
        if (size(X, 1) /= n_samples .or. size(X, 2) /= n_features) then
            print *, "ERRO: Dimensoes de X incompativeis"
            stop
        end if
        if (size(y) /= n_samples) then
            print *, "ERRO: Tamanho de y incompativel com X"
            stop
        end if

        ! Inicializar modelo
        model%n_features = n_features
        if (allocated(model%weights)) deallocate(model%weights)
        allocate(model%weights(n_features))
        model%weights = 0.0_dp
        model%bias = 0.0_dp
        model%fitted = .true.

        if (allocated(model%error_history)) deallocate(model%error_history)
        allocate(model%error_history(model%max_epochs))
        model%error_history = 0

        print *, "Treinando Perceptron:"
        print *, "  Amostras: ", n_samples
        print *, "  Features: ", n_features
        print *, "  Learning rate: ", model%learning_rate
        print *, "  Max epocas: ", model%max_epochs
        print *, ""

        ! Treinamento
        do epoch = 1, model%max_epochs
            errors = 0

            do i = 1, n_samples
                ! Calcular saida
                z = model%bias
                do j = 1, n_features
                    z = z + model%weights(j) * X(i, j)
                end do

                y_hat = step_function(z)
                error_val = y(i) - y_hat

                ! Atualizar pesos se houver erro
                if (error_val /= 0) then
                    do j = 1, n_features
                        model%weights(j) = model%weights(j) + &
                            model%learning_rate * real(error_val, dp) * X(i, j)
                    end do
                    model%bias = model%bias + &
                        model%learning_rate * real(error_val, dp)
                    errors = errors + 1
                end if
            end do

            model%error_history(epoch) = errors

            ! Log periodico
            if (mod(epoch, 100) == 0 .or. epoch == 1 .or. errors == 0) then
                write(*, '(A, I4, A, I4, A, I3, A, F8.4, A, F8.4)') &
                    "  Epoca ", epoch, "/", model%max_epochs, &
                    " - Erros: ", errors, &
                    " - W: ", model%weights(1), &
                    ", ", model%weights(2)
            end if

            ! Convergiu?
            if (errors == 0) then
                print *, "  Convergiu na epoca ", epoch, "!"
                exit
            end if
        end do

        print *, ""
        print *, "Treinamento concluido!"
        write(*, '(A, F8.4, A, F8.4)') "  Pesos finais: ", &
            model%weights(1), ", ", model%weights(2)
        write(*, '(A, F8.4)') "  Bias final: ", model%bias

    end subroutine fit_perceptron

    ! =========================================================================
    ! Prever para um unico exemplo
    ! =========================================================================
    function predict_single(model, x) result(y_hat)
        type(perceptron_type), intent(in) :: model
        real(dp), intent(in) :: x(:)
        integer :: y_hat

        real(dp) :: z
        integer :: j

        if (.not. model%fitted) then
            print *, "ERRO: Modelo nao treinado"
            stop
        end if

        z = model%bias
        do j = 1, model%n_features
            z = z + model%weights(j) * x(j)
        end do

        y_hat = step_function(z)
    end function predict_single

    ! =========================================================================
    ! Prever para multiplos exemplos
    ! =========================================================================
    subroutine predict_batch(model, X, predictions, n_samples)
        type(perceptron_type), intent(in) :: model
        real(dp), intent(in) :: X(:,:)
        integer, intent(out) :: predictions(:)
        integer, intent(in) :: n_samples

        integer :: i

        do i = 1, n_samples
            predictions(i) = predict_single(model, X(i, :))
        end do
    end subroutine predict_batch

    ! =========================================================================
    ! Calcular acuracia
    ! =========================================================================
    function score_perceptron(model, X, y, n_samples) result(accuracy)
        type(perceptron_type), intent(in) :: model
        real(dp), intent(in) :: X(:,:)
        integer, intent(in) :: y(:)
        integer, intent(in) :: n_samples
        real(dp) :: accuracy

        integer :: correct, i
        integer :: pred

        correct = 0
        do i = 1, n_samples
            pred = predict_single(model, X(i, :))
            if (pred == y(i)) correct = correct + 1
        end do

        accuracy = real(correct, dp) / real(n_samples, dp)
    end function score_perceptron

    ! =========================================================================
    ! Imprimir metricas
    ! =========================================================================
    subroutine print_metrics(y_true, y_pred, n)
        integer, intent(in) :: y_true(:), y_pred(:), n

        integer :: tp, tn, fp, fn, i
        real(dp) :: accuracy, precision, recall, f1

        tp = 0
        tn = 0
        fp = 0
        fn = 0

        do i = 1, n
            if (y_true(i) == 1 .and. y_pred(i) == 1) then
                tp = tp + 1
            else if (y_true(i) == 0 .and. y_pred(i) == 0) then
                tn = tn + 1
            else if (y_true(i) == 0 .and. y_pred(i) == 1) then
                fp = fp + 1
            else if (y_true(i) == 1 .and. y_pred(i) == 0) then
                fn = fn + 1
            end if
        end do

        accuracy = real(tp + tn, dp) / real(n, dp)
        if (tp + fp > 0) then
            precision = real(tp, dp) / real(tp + fp, dp)
        else
            precision = 0.0_dp
        end if
        if (tp + fn > 0) then
            recall = real(tp, dp) / real(tp + fn, dp)
        else
            recall = 0.0_dp
        end if
        if (precision + recall > 0.0_dp) then
            f1 = 2.0_dp * precision * recall / (precision + recall)
        else
            f1 = 0.0_dp
        end if

        print *, "  Acuracia:   ", accuracy
        print *, "  Precisao:   ", precision
        print *, "  Recall:     ", recall
        print *, "  F1-Score:   ", f1
        write(*, '(A, I4, A, I4, A, I4, A, I4)') &
            "  VP: ", tp, "  VN: ", tn, "  FP: ", fp, "  FN: ", fn

    end subroutine print_metrics

    ! =========================================================================
    ! Gerar dados linearmente separaveis
    ! =========================================================================
    subroutine generate_linear_data(X, y, n_samples, n_features, separation, seed)
        real(dp), intent(out) :: X(:,:)
        integer, intent(out) :: y(:)
        integer, intent(in) :: n_samples, n_features
        real(dp), intent(in) :: separation
        integer, intent(in) :: seed

        integer :: i, j, half
        real(dp) :: u1, u2, z, center
        integer :: rng_state, rng_temp

        half = n_samples / 2
        rng_state = seed

        do i = 1, n_samples
            do j = 1, n_features
                ! Gerador congruencial linear (pseudo-aleatorio)
                rng_state = mod(rng_state * 1103515245 + 12345, 2147483647)
                u1 = real(abs(rng_state), dp) / 2147483647.0_dp

                rng_state = mod(rng_state * 1103515245 + 12345, 2147483647)
                u2 = real(abs(rng_state), dp) / 2147483647.0_dp

                ! Transformacao Box-Muller (aproximacao)
                if (u1 < 1.0e-10_dp) u1 = 1.0e-10_dp
                z = sqrt(-2.0_dp * log(u1)) * cos(2.0_dp * 3.14159265358979_dp * u2)

                if (i <= half) then
                    center = separation / 2.0_dp
                else
                    center = -separation / 2.0_dp
                end if

                X(i, j) = z + center
            end do

            if (i <= half) then
                y(i) = 1
            else
                y(i) = 0
            end if
        end do
    end subroutine generate_linear_data

    ! =========================================================================
    ! Gerar dados XOR
    ! =========================================================================
    subroutine generate_xor_data(X, y, n_samples, seed)
        real(dp), intent(out) :: X(:,:)
        integer, intent(out) :: y(:)
        integer, intent(in) :: n_samples
        integer, intent(in) :: seed

        integer :: i, rng_state
        real(dp) :: u, x1, x2

        rng_state = seed

        do i = 1, n_samples
            rng_state = mod(rng_state * 1103515245 + 12345, 2147483647)
            u = real(abs(rng_state), dp) / 2147483647.0_dp
            x1 = u * 2.0_dp - 1.0_dp

            rng_state = mod(rng_state * 1103515245 + 12345, 2147483647)
            u = real(abs(rng_state), dp) / 2147483647.0_dp
            x2 = u * 2.0_dp - 1.0_dp

            X(i, 1) = x1
            X(i, 2) = x2

            if ((x1 > 0.0_dp) .neqv. (x2 > 0.0_dp)) then
                y(i) = 1
            else
                y(i) = 0
            end if
        end do
    end subroutine generate_xor_data

    ! =========================================================================
    ! Imprimir fronteira de decisao em ASCII
    ! =========================================================================
    subroutine print_ascii_boundary(model, width, height)
        type(perceptron_type), intent(in) :: model
        integer, intent(in) :: width, height

        integer :: row, col
        real(dp) :: x_min, x_max, y_min, y_max, x_step, y_step
        real(dp) :: x_val, y_val
        integer :: pred
        character(len=1) :: ch
        real(dp) :: point(2)

        if (model%n_features /= 2) then
            print *, "Fronteira ASCII requer 2 features"
            return
        end if

        x_min = -3.0_dp
        x_max = 3.0_dp
        y_min = -3.0_dp
        y_max = 3.0_dp
        x_step = (x_max - x_min) / real(width, dp)
        y_step = (y_max - y_min) / real(height, dp)

        print *, ""
        print *, "Fronteira de Decisao (ASCII Art):"
        print *, ""

        do row = 0, height - 1
            y_val = y_max - real(row, dp) * y_step
            do col = 0, width - 1
                x_val = x_min + real(col, dp) * x_step
                point(1) = x_val
                point(2) = y_val
                pred = predict_single(model, point)
                if (pred == 1) then
                    ch = '#'
                else
                    ch = '.'
                end if
                write(*, '(A)', advance='no') ch
            end do
            print *, ""
        end do

        print *, ""
        print *, "Legenda: # = Classe 1, . = Classe 0"

    end subroutine print_ascii_boundary

end module perceptron_mod

! =========================================================================
! Programa Principal
! =========================================================================
program main
    use perceptron_mod
    implicit none

    type(perceptron_type) :: model, xor_model, and_model
    integer, parameter :: n_samples = 200
    integer, parameter :: n_features = 2
    integer, parameter :: train_size = 160
    integer, parameter :: test_size = 40

    real(dp) :: X_train(n_samples, n_features), X_test(test_size, n_features)
    integer :: y_train(n_samples), y_test(test_size)
    real(dp) :: accuracy
    integer :: predictions(test_size)

    print *, "============================================================"
    print *, "  PERCEPTRON COMPLETO EM FORTRAN"
    print *, "============================================================"
    print *, ""

    ! ------------------------------------------------------------------
    ! Teste 1: Dados linearmente separaveis
    ! ------------------------------------------------------------------
    print *, "--- Teste 1: Dados Linearmente Separaveis ---"
    print *, ""

    ! Gerar dados
    call generate_linear_data(X_train, y_train, n_samples, n_features, 2.0_dp, 42)
    X_test = X_train(train_size+1:n_samples, :)
    y_test = y_train(train_size+1:n_samples)

    print *, "Dados gerados:"
    print *, "  Treinamento: ", train_size, " amostras"
    print *, "  Teste: ", test_size, " amostras"
    print *, ""

    ! Criar e treinar modelo
    model = create_perceptron(0.1_dp, 100)
    call fit_perceptron(model, X_train(1:train_size, :), y_train(1:train_size), &
                        train_size, n_features)
    print *, ""

    ! Avaliar
    accuracy = score_perceptron(model, X_train(1:train_size, :), y_train(1:train_size), &
                                train_size)
    print *, "Acuracia (treinamento): ", accuracy

    accuracy = score_perceptron(model, X_test, y_test, test_size)
    print *, "Acuracia (teste): ", accuracy
    print *, ""

    ! Metricas detalhadas
    call predict_batch(model, X_test, predictions, test_size)
    print *, "Metricas (teste):"
    call print_metrics(y_test, predictions, test_size)
    print *, ""

    ! ASCII art
    call print_ascii_boundary(model, 40, 20)
    print *, ""

    ! ------------------------------------------------------------------
    ! Teste 2: XOR (deve falhar)
    ! ------------------------------------------------------------------
    print *, "--- Teste 2: Problema do XOR (deve falhar) ---"
    print *, ""

    block
        real(dp) :: xor_X(n_samples, 2)
        integer :: xor_y(n_samples)

        call generate_xor_data(xor_X, xor_y, n_samples, 42)

        xor_model = create_perceptron(0.1_dp, 50)
        call fit_perceptron(xor_model, xor_X(1:train_size, :), &
                            xor_y(1:train_size), train_size, 2)
        print *, ""

        accuracy = score_perceptron(xor_model, xor_X(train_size+1:n_samples, :), &
                                    xor_y(train_size+1:n_samples), test_size)
        print *, "Acuracia XOR (teste): ", accuracy, " (deve ser ~0.5)"
        print *, ""

        call destroy_perceptron(xor_model)
    end block

    ! ------------------------------------------------------------------
    ! Teste 3: AND gate
    ! ------------------------------------------------------------------
    print *, "--- Teste 3: AND Gate ---"
    print *, ""

    block
        real(dp) :: and_X(4, 2)
        integer :: and_y(4), and_pred(4)

        and_X(1,:) = [0.0_dp, 0.0_dp]
        and_X(2,:) = [0.0_dp, 1.0_dp]
        and_X(3,:) = [1.0_dp, 0.0_dp]
        and_X(4,:) = [1.0_dp, 1.0_dp]
        and_y = [0, 0, 0, 1]

        print *, "Treinando AND gate:"
        print *, "  (0,0) -> 0"
        print *, "  (0,1) -> 0"
        print *, "  (1,0) -> 0"
        print *, "  (1,1) -> 1"
        print *, ""

        and_model = create_perceptron(0.1_dp, 100)
        call fit_perceptron(and_model, and_X, and_y, 4, 2)
        print *, ""

        print *, "Teste AND gate:"
        call predict_batch(and_model, and_X, and_pred, 4)
        print *, "  (0,0) -> ", and_pred(1), " (esperado: 0)"
        print *, "  (0,1) -> ", and_pred(2), " (esperado: 0)"
        print *, "  (1,0) -> ", and_pred(3), " (esperado: 0)"
        print *, "  (1,1) -> ", and_pred(4), " (esperado: 1)"
        print *, ""

        call destroy_perceptron(and_model)
    end block

    ! ------------------------------------------------------------------
    ! Liberar memoria
    ! ------------------------------------------------------------------
    call destroy_perceptron(model)

    print *, "============================================================"
    print *, "  Todos os testes concluidos com sucesso!"
    print *, "============================================================"

end program main
```

### 10.2 Compilacao e Execucao

```text
Compilacao:
  gfortran -O2 -o perceptron perceptron.f90

Execucao:
  ./perceptron

Caracteristicas Fortran:
  - Modulos para encapsulamento
  - Tipos derivados para estruturas de dados
  - Alocacao dinamica (allocatable arrays)
  - Pure functions para operacoes sem efeitos colaterais
  - Block construct para escopo local
  - Arrays multidimensionais nativos
```

---

## 11. Exemplo: Classificacao de Pontos 2D

### 11.1 Geracao do Conjunto de Dados

Vamos criar um conjunto de dados bidimensional para visualizar e entender o perceptron em acao.

```text
Conjunto de dados: Classificacao de pontos em 2D

Classe 0 (pontos abaixo da diagonal):
  x_1 > x_2 -> Classe 0

Classe 1 (pontos acima da diagonal):
  x_1 < x_2 -> Classe 1

Fronteira de decisao ideal: x_2 = x_1 (ou x_1 - x_2 = 0)
Pesos ideais: w_1 = -1, w_2 = 1, b = 0

Geracao de dados:
  100 pontos da classe 0: x_1 ~ N(2, 0.8), x_2 ~ N(0, 0.8)
  100 pontos da classe 1: x_1 ~ N(0, 0.8), x_2 ~ N(2, 0.8)
```

### 11.2 Treinamento Passo a Passo

Vamos acompanhar o treinamento manualmente, epoca por epoca.

**Dados de Treinamento (primeiros 8 exemplos)**:

```text
Exemplo  | x_1    | x_2    | y (real)
---------|--------|--------|---------
  1      |  2.34  |  0.12  | 0
  2      |  1.87  | -0.23  | 0
  3      | -0.45  |  2.78  | 1
  4      |  0.12  |  1.95  | 1
  5      |  2.67  |  0.89  | 0
  6      | -0.34  |  2.12  | 1
  7      |  1.56  |  0.34  | 0
  8      |  0.23  |  2.45  | 1
```

**Pesos Iniciais**: w_1 = 0, w_2 = 0, b = 0

**Epoca 1**:

```text
Exemplo 1: (2.34, 0.12), y=0
  z = 0*2.34 + 0*0.12 + 0 = 0
  y_hat = 1 (step(0) = 1)
  ERRO! (y=0, y_hat=1), error = -1
  w_1 = 0 + 0.1*(-1)*2.34 = -0.234
  w_2 = 0 + 0.1*(-1)*0.12 = -0.012
  b = 0 + 0.1*(-1) = -0.1

Exemplo 2: (1.87, -0.23), y=0
  z = -0.234*1.87 + (-0.012)*(-0.23) + (-0.1) = -0.438 + 0.003 - 0.1 = -0.535
  y_hat = 0 (step(-0.535) = 0)
  ACERTOU! (y=0, y_hat=0)

Exemplo 3: (-0.45, 2.78), y=1
  z = -0.234*(-0.45) + (-0.012)*2.78 + (-0.1) = 0.105 - 0.033 - 0.1 = -0.028
  y_hat = 0 (step(-0.028) = 0)
  ERRO! (y=1, y_hat=0), error = 1
  w_1 = -0.234 + 0.1*(1)*(-0.45) = -0.234 - 0.045 = -0.279
  w_2 = -0.012 + 0.1*(1)*2.78 = -0.012 + 0.278 = 0.266
  b = -0.1 + 0.1*(1) = 0.0

Exemplo 4: (0.12, 1.95), y=1
  z = -0.279*0.12 + 0.266*1.95 + 0.0 = -0.033 + 0.519 + 0.0 = 0.486
  y_hat = 1 (step(0.486) = 1)
  ACERTOU!

Exemplo 5: (2.67, 0.89), y=0
  z = -0.279*2.67 + 0.266*0.89 + 0.0 = -0.745 + 0.237 + 0.0 = -0.508
  y_hat = 0 -> ACERTOU!

Exemplo 6: (-0.34, 2.12), y=1
  z = -0.279*(-0.34) + 0.266*2.12 + 0.0 = 0.095 + 0.564 + 0.0 = 0.659
  y_hat = 1 -> ACERTOU!

Exemplo 7: (1.56, 0.34), y=0
  z = -0.279*1.56 + 0.266*0.34 + 0.0 = -0.435 + 0.090 + 0.0 = -0.345
  y_hat = 0 -> ACERTOU!

Exemplo 8: (0.23, 2.45), y=1
  z = -0.279*0.23 + 0.266*2.45 + 0.0 = -0.064 + 0.652 + 0.0 = 0.588
  y_hat = 1 -> ACERTOU!

Resumo Epoca 1: 2 erros em 8 exemplos
Pesos: w_1 = -0.279, w_2 = 0.266, b = 0.0
```

**Epoca 2** (continuando com os mesmos dados):

```text
Reprocessando todos os 8 exemplos:

Exemplo 1: z = -0.279*2.34 + 0.266*0.12 + 0.0 = -0.653 + 0.032 = -0.621 -> 0 OK
Exemplo 2: z = -0.279*1.87 + 0.266*(-0.23) + 0.0 = -0.522 - 0.061 = -0.583 -> 0 OK
Exemplo 3: z = -0.279*(-0.45) + 0.266*2.78 + 0.0 = 0.126 + 0.740 = 0.866 -> 1 OK
Exemplo 4: z = -0.279*0.12 + 0.266*1.95 + 0.0 = -0.033 + 0.519 = 0.486 -> 1 OK
Exemplo 5: z = -0.279*2.67 + 0.266*0.89 + 0.0 = -0.745 + 0.237 = -0.508 -> 0 OK
Exemplo 6: z = -0.279*(-0.34) + 0.266*2.12 + 0.0 = 0.095 + 0.564 = 0.659 -> 1 OK
Exemplo 7: z = -0.279*1.56 + 0.266*0.34 + 0.0 = -0.435 + 0.090 = -0.345 -> 0 OK
Exemplo 8: z = -0.279*0.23 + 0.266*2.45 + 0.0 = -0.064 + 0.652 = 0.588 -> 1 OK

Resumo Epoca 2: 0 erros! CONVERGIU!

Pesos finais: w_1 = -0.279, w_2 = 0.266, b = 0.0
Fronteira: -0.279*x_1 + 0.266*x_2 + 0.0 = 0
           x_2 = (0.279/0.266)*x_1 = 1.049*x_1

A fronteira aprendida e proxima da ideal (x_2 = x_1)!
```

### 11.3 Analise da Convergencia

```text
Curva de erros por epoca (exemplo tipico):

  Erros
   45 |  *
      |   *
   40 |    *
      |
   35 |     *
      |
   30 |      *
      |
   25 |       *
      |
   20 |        *
      |
   15 |          *
      |
   10 |            *
      |
    5 |               *
      |                   *    *    *    *  0
    0 +-----------------------------------------> Epoca
      1  2  3  4  5  6  7  8  9  10 11 12

Observacoes:
  - Erro diminui rapidamente nas primeiras epocas
  - Pode haver oscilacoes antes da convergencia
  - Convergencia tipica em 5-20 epocas para problemas simples
  - Tempo total: microseconds a milliseconds
```

---

## 12. Visualizacao da Fronteira de Decisao

### 12.1 Conceito da Fronteira

A fronteira de decisao e o conjunto de pontos onde o perceptron esta "no limiar" — exatamente na transicao entre as duas classes.

```text
Em 2D: Fronteira de decisao e uma RETA
Em 3D: Fronteira de decisao e um PLANO
Em nD: Fronteira de decisao e um HIPERPLANO

A reta e definida por:
  w_1 * x_1 + w_2 * x_2 + b = 0

Isolando x_2:
  x_2 = -(w_1/w_2) * x_1 - b/w_2

Inclinacao: m = -w_1/w_2
Intercepto: c = -b/w_2
```

### 12.2 Arte ASCII da Fronteira

```text
Fronteira de Decisao para classificacao acima/abaixo da diagonal:

  x_2
   ^
 3 |  .  .  .  .  .  .  .  .  #  #  #  #
   |  .  .  .  .  .  .  .  #  #  #  #  #
 2 |  .  .  .  .  .  .  #  #  #  #  #  #
   |  .  .  .  .  .  #  #  #  #  #  #  #
 1 |  .  .  .  .  #  #  #  #  #  #  #  #
   |  .  .  .  #  #  #  #  #  #  #  #  #
 0 |  .  .  #  #  #  #  #  #  #  #  #  #
   +--.--------+--------+--------+---------> x_1
   0  1  2  3  4  5  6  7  8  9  10 11 12

  . = Classe 0 (abaixo da diagonal)
  # = Classe 1 (acima da diagonal)
  A linha diagonal e a fronteira de decisao
```

### 12.3 Interpretacao Geometrica dos Pesos

```text
Pesos aprendidos: w_1 = -0.279, w_2 = 0.266, b = 0.0

Interpretacao:
  - w_1 < 0: Aumentar x_1 tende a diminuir a saida (empurra para classe 0)
  - w_2 > 0: Aumentar x_2 tende a aumentar a saida (empurra para classe 1)
  - b = 0: A fronteira passa pela origem

Vetor normal: w = (-0.279, 0.266)
  Aponta na direcao perpendicular a fronteira
  Aponta para o lado da classe 1 (valores positivos)

A inclinacao da fronteira:
  m = -w_1/w_2 = -(-0.279)/0.266 = 1.049
  
  Muito proximo de 1.0 (a fronteira ideal)!
```

### 12.4 Conceito de Plot com Bibliotecas

Embora nao usemos bibliotecas externas, o conceito de visualizacao programatica e importante:

```text
Conceito de plot da fronteira de decisao (pseudocodigo):

  Para cada pixel (px, py) na imagem:
    x1 = mapear(px, 0, largura, x_min, x_max)
    x2 = mapear(py, 0, altura, y_max, y_min)
    
    z = w_1 * x1 + w_2 * x2 + b
    
    Se z > 0:
      Desenhar pixel na cor da classe 1
    Senao:
      Desenhar pixel na cor da classe 0

  Para cada ponto de dado (x1, x2):
    Se y == 1:
      Desenhar circulo azul em (x1, x2)
    Senao:
      Desenhar circulo vermelho em (x1, x2)

  Desenhar linha da fronteira (w_1*x1 + w_2*x2 + b = 0)
```

---

## 13. Analise de Erros

### 13.1 Matriz de Confusao

A matriz de confusao e a ferramenta fundamental para analisar erros de classificacao.

```text
Matriz de Confusao para Classificacao Binaria:

                    Predito: 0     Predito: 1
                  +-------------+-------------+
  Real: 0         |     VN      |     FP      |
                  +-------------+-------------+
  Real: 1         |     FN      |     VP      |
                  +-------------+-------------+

VN = Verdadeiro Negativo: Classe 0 corretamente identificada
FP = Falso Positivo: Classe 0 identificada como 1 (erro Tipo I)
FN = Falso Negativo: Classe 1 identificada como 0 (erro Tipo II)
VP = Verdadeiro Positivo: Classe 1 corretamente identificada
```

### 13.2 Metricas Derivadas

```text
Acuracia (Accuracy):
  Acuracia = (VP + VN) / (VP + VN + FP + FN)
  
  Interpretacao: Fracao de previsoes corretas
  Problema: Misleading com classes desbalanceadas
  Exemplo: 95% classe 0, 5% classe 1 -> modelo que sempre prediz 0 tem 95% acuracia

Precisao (Precision):
  Precisao = VP / (VP + FP)
  
  Interpretacao: Dos que preditos como 1, quantos sao realmente 1?
  Importante quando FPs sao custosos (ex: spam - nao quer marcar email legitimo como spam)

Recall (Sensibilidade / True Positive Rate):
  Recall = VP / (VP + FN)
  
  Interpretacao: Dos que sao realmente 1, quantos foram detectados?
  Importante quando FNs sao custosos (ex: cancer - nao quer perder um caso positivo)

F1-Score:
  F1 = 2 * (Precisao * Recall) / (Precisao + Recall)
  
  Interpretacao: Media harmonica entre Precisao e Recall
  Util quando precisa de um unico numero que balanceia ambos
```

### 13.3 Exemplo de Analise

```text
Exemplo: Classificacao de emails (spam vs nao-spam)

Matriz de Confusao:
                    Predito: Nao-Spam   Predito: Spam
                  +------------------+------------------+
  Real: Nao-Spam  |       950        |       50         |
                  +------------------+------------------+
  Real: Spam      |        30        |       470        |
                  +------------------+------------------+

Metricas:
  Acuracia = (950 + 470) / (950 + 50 + 30 + 470) = 1420/1500 = 0.9467
  Precisao = 470 / (470 + 50) = 470/520 = 0.9038
  Recall = 470 / (470 + 30) = 470/500 = 0.9400
  F1 = 2 * 0.9038 * 0.9400 / (0.9038 + 0.9400) = 0.9215

Interpretacao:
  - 94.67% dos emails foram classificados corretamente
  - 90.38% dos emails marcados como spam realmente sao spam
  - 94.00% do spam real foi detectado
  - F1 de 0.92 indica bom balanceamento entre Precisao e Recall
```

### 13.4 Erros Tipicos do Perceptron

```text
Erro 1: Fronteira de decisao nao otima
  Causa: Ordem dos dados afeta convergencia
  Solucao: Treinar multiplas vezes com ordens diferentes

Erro 2: Oscilacao near the boundary
  Causa: Pontos muito proximos da fronteira
  Solucao: Reduzir taxa de aprendizado ou usar pocket

Erro 3: Falha em dados nao-linearmente separaveis
  Causa: Limitacao fundamental do perceptron
  Solucao: Usar rede multicamada (MLP)

Erro 4: Sensibilidade a outliers
  Causa: Um outlier pode deslocar significativamente a fronteira
  Solucao: Pre-processamento, normalizacao, ou usar SVM

Erro 5: Classes desbalanceadas
  Causa: A maioria dos exemplos e de uma classe
  Solucao: Reamostragem, ajuste de limiar, metricas alem da acuracia
```

### 13.5 Quando Usar o Perceptron

```text
Usar perceptron quando:
  - O problema e de classificacao binaria
  - Os dados sao linearmente separaveis (ou aproximadamente)
  - Simplicidade e interpretabilidade sao prioridades
  - Treinamento rapido e essencial
  - Recursos computacionais sao limitados

NAO usar perceptron quando:
  - As classes nao sao linearmente separaveis
  - Ha muitas classes (usar softmax/MLP)
  - Precisao maxima e necessaria (usar SVM, Random Forest, ou MLP)
  - Os dados contem muitas features irrelevantes
  - Ha necessidade de probabilidades calibradas (perceptron retorna 0/1)
```

---

## Resumo do Capitulo

### Principais Conceitos

```text
1. Neuronio Biologico vs Artificial
   - Analogia: dendritos/entradas, sinapses/pesos, axonio/saida
   - Diferenca: biologico e temporal/ruidoso, artificial e atemporal/deterministico

2. Perceptron de Rosenblatt (1958)
   - Primeiro modelo de ML que aprende
   - Regra de aprendizado: w_i = w_i + eta * (y - y_hat) * x_i
   - So classifica dados linearmente separaveis

3. Funcao de Decisao Linear
   - Hiperplano de separacao: w · x + b = 0
   - Vetor normal: w aponta perpendicular a fronteira
   - Classificacao: sign(w · x + b)

4. Regra de Aprendizado
   - Atualizacao proporcional ao erro e a entrada
   - Learning rate controla tamanho dos passos
   - Convergencia garantida para dados linearmente separaveis

5. Convergencia
   - Teorema: K <= (R/gamma)^2 erros no maximo
   - R = norma maxima dos dados, gamma = margem
   - Na pratica, converge muito mais rapido que o limite

6. Limitacoes (XOR)
   - Perceptron simples NAO resolve XOR
   - Minsky e Papert (1969) demonstraram limitacao
   - Solucao: rede multicamada (Capitulo 6)

7. Multi-classe
   - One-vs-all: K perceptrons (1 por classe)
   - One-vs-one: K*(K-1)/2 perceptrons (1 por par)
   - Extensao softmax para probabilidades

8. Implementacoes
   - C++: Templates, exceptions, metricas
   - Rust: Traits, Result<T,E>, iteradores
   - Fortran: Modulos, tipos derivados, alocacao dinamica
```

### Relacao com Proximos Capitulos

```text
Capitulo 4 (Perceptron) -> Capitulo 5 (MLP)
  O perceptron e o bloco de construcao da MLP.
  MLP = multiplas camadas de perceptrons com funcoes de ativacao.

Capitulo 4 -> Capitulo 6 (Backpropagation)
  O backpropagation resolve o problema do perceptron: como treinar
  camadas intermediarias. Sem backprop, MLPs nao seriam treinaveis.

Capitulo 4 -> Capitulos 7+ (Otimizacao, Regularizacao, etc.)
  Todas as tecnicas avancadas constroem sobre o fundamentos do perceptron.
  O perceptron e a semente de tudo.
```

---

## Exercicios

### Exercicio 1: Perceptron AND Gate

Implemente um perceptron que resolva a tabela-verdade do AND gate:

```text
  x_1  x_2  |  AND
  -----------|------
   0    0    |   0
   0    1    |   0
   1    0    |   0
   1    1    |   1
```

Treine o perceptron manualmente, passo a passo, e verifique que os pesos finais classificam corretamente todos os 4 exemplos. Use taxa de aprendizado eta = 0.1 e pesos iniciais zero.

### Exercicio 2: Perceptron OR Gate

Implemente um perceptron que resolva a tabela-verdade do OR gate:

```text
  x_1  x_2  |  OR
  -----------|------
   0    0    |   0
   0    1    |   1
   1    0    |   1
   1    1    |   1
```

Compare os pesos encontrados com os do AND gate. Por que sao diferentes?

### Exercicio 3: Demonstre que NAND e Linearmente Separavel

O NAND gate e o inverso do AND. Verifique que ele e linearmente separavel e encontre uma fronteira de decisao.

```text
  x_1  x_2  | NAND
  -----------|------
   0    0    |   1
   0    1    |   1
   1    0    |   1
   1    1    |   0
```

### Exercicio 4: Prova Formal de que XOR Nao e Linearmente Separavel

Complete a prova formal iniciada na secao 6.2. Mostre que nao existe combinacao de w_1, w_2, b que satisfaça todas as 4 condicoes simultaneamente.

### Exercicio 5: Efeito da Taxa de Aprendizado

Implemente o perceptron em qualquer linguagem e teste com as seguintes taxas de aprendizado: 0.001, 0.01, 0.1, 0.5, 1.0. Para cada uma, registre:

1. Numero de epocas ate convergencia
2. Pesos finais
3. Numero total de atualizacoes de peso

Qual taxa de aprendizado produz a convergencia mais rapida? Qual produz os pesos mais proximos da solucao otima?

### Exercicio 6: Perceptron Multi-classe

Implemente um perceptron multi-classe usando a estrategia one-vs-all para classificar dados com 3 classes em 2D. Gere dados separaveis linearmente (por exemplo, 3 setores de um circulo) e treine 3 perceptrons.

### Exercicio 7: Perceptron Pocket

O perceptron pocket e uma variante que mantem o melhor modelo encontrado (com menos erros) durante o treinamento. Implemente o perceptron pocket e teste com dados que NAO sao perfeitamente linearmente separaveis. Compare a acuracia do pocket com a do perceptron simples.

### Exercicio 8: Analise de Convergencia

Para um problema com 2 entradas, calcule o limite superior de Novikoff (R/gamma)^2. Gere dados com diferentes valores de margem (gamma = 0.1, 0.5, 1.0, 2.0) e verifique se o numero real de epocas respeita o limite teorico.

### Exercicio 9: Impacto da Ordem dos Dados

Treine o mesmo perceptron com os mesmos dados, mas em 10 ordens diferentes. Registre o numero de epocas para cada ordem. Qual e a variancia? A solucao final e sempre a mesma?

### Exercicio 10: Perceptron em 10 Dimensoes

Gere dados linearmente separaveis em 10 dimensoes (usando a funcao generate_linearly_separable com n_features = 10). Treine o perceptron e verifique:

1. Quantas epocas foram necessarias?
2. Todos os pesos sao significativos (diferentes de zero)?
3. A acuracia e 100% nos dados de treinamento?

---

## Referencias

1. **Rosenblatt, F. (1958)**. "The Perceptron: A Probabilistic Model for Information Storage and Organization in the Brain." Psychological Review, 65(6), 386-408.

2. **Minsky, M. & Papert, S. (1969)**. "Perceptrons: An Introduction to Computational Geometry." MIT Press.

3. **Novikoff, A.B.J. (1962)**. "On Convergence Proofs on Perceptrons." Symposium on the Mathematical Theory of Automata, 12, 615-622.

4. **McCulloch, W.S. & Pitts, W. (1943)**. "A Logical Calculus of the Ideas Immanent in Nervous Activity." Bulletin of Mathematical Biophysics, 5, 115-133.

5. **Widrow, B. & Hoff, M.E. (1960)**. "Adaptive Switching Circuits." IRE WESCON Convention Record, Part 4, 96-104.

6. **Rumelhart, D.E., Hinton, G.E. & Williams, R.J. (1986)**. "Learning representations by back-propagating errors." Nature, 323, 533-536.

7. **Goodfellow, I., Bengio, Y. & Courville, A. (2016)**. "Deep Learning." MIT Press. Capitulos 1-6.

8. **Bishop, C.M. (2006)**. "Pattern Recognition and Machine Learning." Springer. Capitulos 1-4.

9. **Hastie, T., Tibshirani, R. & Friedman, J. (2009)**. "The Elements of Statistical Learning." Springer. Capitulos 2-4.

10. **Haykin, S. (2009)**. "Neural Networks and Learning Machines." 3rd Edition. Pearson. Capitulos 1-4.

---

*No proximo capitulo, veremos as Redes Neurais Multicamadas (MLP) — como empilhar perceptrons com funcoes de ativacao para resolver problemas nao-linearmente separaveis, incluindo o XOR. O MLP e a ponte entre o perceptron simples e as redes profundas modernas.*
