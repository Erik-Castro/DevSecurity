---
layout: default
title: "05-mlp"
---

# Capitulo 5 — Redes Neurais Multicamadas (MLP)

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Compreender a limitacao fundamental do Perceptron simples e por que redes multicamadas sao necessarias para resolver problemas nao-lineares.
2. Descrever a arquitetura completa de uma Multi-Layer Perceptron (MLP), incluindo camadas de entrada, ocultas e de saida.
3. Implementar a propagacao direta (forward propagation) de uma rede neural multicamadas do zero, sem bibliotecas externas.
4. Diferenciar e implementar funcoes de perda adequadas para tarefas de regressao (MSE) e classificacao (Cross-Entropy).
5. Compreender a influencia do numero de neuronios e camadas ocultas na capacidade de aproximacao da rede.
6. Explicar o Teorema de Aproximacao Universal e suas implicacoes praticas para projetos de redes neurais.
7. Aplicar tecnicas de inicializacao de pesos (Xavier e He) para evitar problemas de gradiente que explora ou desaparece.
8. Implementar uma MLP completa em C++ com operacoes matriciais, funcoes de ativacao e treinamento por retropropagacao.
9. Implementar uma MLP completa em Rust com tipos seguros e gerenciamento de memoria sem alocacao dinamica manual.
10. Implementar uma MLP completa em Fortran com arrays multidimensionais e subrotinas para treinamento.

---

## 1. De Perceptron a MLP

No capitulo anterior, exploramos o Perceptron de Rosenblatt — o neuronio artificial mais simples possivel. O Perceptron recebe entradas ponderadas, aplica uma funcao de ativacao de limiar, e produz uma saida binaria. Embora elegante em sua simplicidade, o Perceptron possui uma limitacao fundamental que o torna insufivel para a maioria dos problemas reais.

### 1.1 A Limitacao do Perceptron

O Perceptron simples so pode resolver problemas linearmente separaveis. Isso significa que, dadas duas classes de dados, existe um hiperplano (uma linha em 2D, um plano em 3D, e assim por diante) que separa perfeitamente uma classe da outra. Para problemas como AND e OR, essa separacao existe. Para o problema XOR, ela nao existe.

Considere as quatro entradas do problema XOR:

| Entrada 1 | Entrada 2 | Saida Esperada |
|------------|------------|----------------|
| 0          | 0          | 0              |
| 0          | 1          | 1              |
| 1          | 0          | 1              |
| 1          | 1          | 0              |

Se tentarmos plotar esses pontos em um plano 2D, veremos que nenhuma linha reta pode separar os pontos com saida 0 dos pontos com saida 1. O Perceptron simples, por mais que ajustemos seus pesos e bias, jamais convergira para uma solucao correta para XOR. Minsky e Papert demonstraram formalmente essa limitacao em 1969, praticamente congelando a pesquisa em redes neurais por mais de uma decada.

A solucao, no entanto, estava escondida na propria estrutura do Perceptron. Se pudessear empilhar varios Perceptrons em camadas, conectando a saida de uma camada a entrada da proxima, a rede ganharia a capacidade de aprender representacoes mais complexas. Essa intuicao levou ao conceito de Multi-Layer Perceptron.

### 1.2 A Ideia Fundamental

A transicao de Perceptron para MLP baseia-se em uma observacao crucial: embora uma unica camada de neuronios so possa aprender fronteiras lineares, uma rede com pelo menos uma camada oculta pode aprender fronteiras arbitrariamente complexas.

Imagine que temos um conjunto de dados em 2D que forma dois circulos concêntricos — um circulo menor de classe A no centro, e um anel de classe B ao redor. Nenhuma linha reta separa essas classes. Mas se projetarmos os dados para um espaco de maior dimensao, digamos usando a transformacao r² = x² + y², os dados se tornam linearmente separaveis: classe A fica com r² < limiar, e classe B com r² > limiar.

Uma rede neural com camada oculta faz exatamente isso: ela transforma automaticamente os dados de entrada para um espaco de representacao onde o problema se torna linearmente separavel. O neuronio da camada oculta aprende a transformacao, e o neuronio da camada de saida aprende a separacao nesse novo espaco.

### 1.3 Historico Breve

O conceito de rede neural multicamadas remonta a Rosenblatt (1961), que propus o " perceptron de camadas multiplo". No entanto, o algoritmo de treinamento disponivel na epoca so funcionava para uma camada. Minsky e Papert (1969) demonstraram as limitacoes do Perceptron, e o campo entrou em declinio por mais de uma decada.

Rumelhart, Hinton e Williams (1986) popularizaram o algoritmo de retropropagacao (backpropagation), que permitiu treinar eficientemente redes com multiplas camadas. Esse marco revitalizou o campo e estabeleceu a base para tudo o que viria a seguir: redes convolucionais, recorrentes, transformadores e a revolucao de deep learning do seculo XXI.

O MLP e, portanto, o ponto de partida essencial. Todas as arquiteturas modernas de redes neurais sao, em ultima analise, extensoes e especializacoes da MLP. Entender a MLP em profundidade e prerequisito para qualquer estudo posterior em deep learning.

### 1.4 Por Que MLP Funciona

A chave para entender por que MLPs funcionam esta na combinacao de duas propriedades:

Primeira, a linearidade das operacoes de multiplicacao de matriz e soma. Cada camada da rede realiza uma transformacao linear: y = Wx + b. Essa transformacao so pode rotacionar, escalar, espelhar e transladar o espaco de dados. Em si, transformacoes lineares sao limitadas — qualquer composicao de transformacoes lineares ainda e uma transformacao linear.

Segunda, a nao-linearidade das funcoes de ativacao. Sem funcoes de ativacao, qualquer sequencia de camadas lineares se reduziria a uma unica transformacao linear. Por mais camadas que voce adicione, a rede so aprenderia uma reta (ou hiperplano). As funcoes de ativacao (sigmoid, tanh, ReLU, etc.) introduzem curvatura nas transformacoes, permitindo que a rede aprenda mapeamentos arbitrariamente complexos.

A combinacao de transformacoes lineares intercaladas com nao-linearidades cria uma funcao de mapeamento flexivel o suficiente para representar praticamente qualquer relacao entre entradas e saidas. Cada camada oculta aprende uma nova representacao dos dados, e cada representacao e mais abstrata que a anterior. O Teorema de Aproximacao Universal formaliza essa intuicao, e o veremos em detalhes adiante neste capitulo.

### 1.5 Perspectiva Geometrica

Do ponto de vista geometrico, cada camada oculta da rede particiona o espaco de entrada em regioes. Cada neuronio da camada oculta cria uma fronteira linear (uma linha em 2D, um plano em 3D), dividindo o espaco em dois lados. A funcao de ativacao decide de que lado da fronteira cada ponto esta.

A composicao de multiplas camadas ocultas permite que a rede crie particoes complexas — regioes poligonais, circulares, ou quaisquer formas. Cada camada adiciona mais fronteiras, tornando a particao mais refinada. Com neuronios suficientes, a rede pode approximar qualquer forma de regiao no espaco de entrada.

Essa perspectiva geometrica e util para visualizar por que uma MLP pode resolver problemas como XOR: a rede particiona o espaco em regioes que correspondem a cada classe, mesmo quando essas regioes sao nao-lineares e disjuntas.

---

## 2. Arquitetura — Camadas de Entrada, Oculta e Saida

Uma MLP e composta por tres tipos fundamentais de camadas: entrada, ocultas e saida. Cada tipo tem uma funcao distinta e regras especificas para seu dimensionamento.

### 2.1 Camada de Entrada

A camada de entrada nao realiza nenhuma computacao. Ela serve exclusivamente para receber os dados brutos e passa-los adiante para a primeira camada oculta. O numero de neuronios na camada de entrada e sempre igual ao numero de caracteristicas (features) do conjunto de dados.

Por exemplo, se estamos classificando flores Iris com quatro medicoes (comprimento da pétala, largura da petala, comprimento da sepal, largura da sepal), a camada de entrada tem exatamente 4 neuronios. Se estamos processando imagens em escala de cinza de 28x28 pixels, a camada de entrada tem 784 neuronios (28 * 28).

A camada de entrada nao tem funcao de ativacao — ela apenas armazena e distribui os valores brutos. A normalizacao dos dados de entrada (por exemplo, para media 0 e variancia 1) e recomendada antes de alimentar a rede, pois melhora a estabilidade do treinamento.

### 2.2 Camadas Ocultas

As camadas ocultas sao o coracao computacional da rede. Cada camada oculta recebe a saida da camada anterior, aplica uma transformacao linear (multiplicacao de matriz + bias) e depois aplica uma funcao de ativacao nao-linear.

Uma rede com uma camada oculta e chamada de rede "rasa" (shallow). Redes com duas ou mais camadas ocultas sao chamadas de "deep" (profundas). A profundidade da rede determina sua capacidade de aprender representacoes hierarquicas.

Para ilustrar, considere uma rede com:
- 3 neuronios na entrada (3 features)
- 4 neuronios na primeira camada oculta
- 4 neuronios na segunda camada oculta
- 2 neuronios na saida (2 classes)

O fluxo de dados seria:

Entrada (3) → Camada Oculta 1 (4) → Camada Oculta 2 (4) → Saida (2)

Os pesos da primeira camada oculta formam uma matriz 3x4 (3 entradas x 4 neuronios). Os pesos da segunda camada oculta formam uma matriz 4x4. Os pesos da camada de saida formam uma matriz 4x2.

A escolha do numero de camadas ocultas e do numero de neuronios em cada camada e uma das decisoes mais importantes no design de uma rede neural. Regras praticas existem, mas nao ha formula universal. A secao 5 deste capitulo aborda esse topico em detalhes.

### 2.3 Camada de Saida

A camada de saida produz a resposta final da rede. Seu dimensionamento e funcao do tipo de problema:

Para classificacao binaria: 1 neuronio com ativacao sigmoid. A saida representa a probabilidade de pertencer a classe positiva.

Para classificacao multi-classe com K classes: K neuronios com ativacao softmax. Cada saida representa a probabilidade de pertencer a classe correspondente.

Para regressao: 1 neuronio (ou mais, para saidas multi-dimensionais) com ativacao identidade (linear). A saida e o valor numerico predito.

A funcao de ativacao da camada de saida e determinada pelo problema. Em classificacao binaria, sigmoid converte qualquer valor real para o intervalo [0, 1], interpretavel como probabilidade. Em classificacao multi-classe, softmax garante que as saidas somem 1 e estejam todas no intervalo [0, 1].

### 2.4 Conexoes entre Camadas

Em uma MLP classica (totalmente conectada — fully connected), cada neuronio de uma camada esta conectado a todos os neuronios da camada seguinte. Isso significa que cada neuronio da camada oculta recebe uma combinacao linear de todas as entradas, e cada neuronio da camada de saida recebe uma combinacao linear de todas as saidas da camada oculta anterior.

A quantidade de conexoes cresce multiplicativamente. Para uma rede com L neuronios na camada i e M neuronios na camada i+1, existem L*M pesos entre essas duas camadas (mais M biases). Essa densidade de conexoes e tanto a forca quanto a fraqueza da MLP: forca porque permite capturar qualquer interacao entre features; fraqueza porque o numero de parametros cresce rapidamente com o tamanho da rede.

Para dar uma ideia numerico: uma rede com arquitetura 784-128-64-10 (como uma para classificacao MNIST) tem:
- Camada 1: 784 * 128 + 128 = 100.480 parametros
- Camada 2: 128 * 64 + 64 = 8.256 parametros
- Camada 3: 64 * 10 + 10 = 650 parametros
- Total: 109.386 parametros

Cada um desses parametros e ajustado durante o treinamento para minimizar a funcao de perda. O treinamento de uma rede com milhoes de parametros requer algoritmos eficientes como retropropagacao e otimizadores como Adam.

### 2.5 Nomenclatura Padrao

Na literatura e na implementacao, usamos a seguinte convencao:

- W[l] — matriz de pesos da camada l, com dimensoes (neuronios[l-1] x neuronios[l])
- b[l] — vetor de bias da camada l, com dimensoes (1 x neuronios[l])
- a[l] — vetor de ativacoes (saidas) da camada l, com dimensoes (1 x neuronios[l])
- z[l] — vetor pre-ativacao da camada l: z[l] = a[l-1] * W[l] + b[l]
- g[.] — funcao de ativacao aplicada a z[l] para produzir a[l]
- L — numero total de camadas com pesos (camadas ocultas + camada de saida)

Essa nomenclatura sera usada consistentemente nas implementacoes de C++, Rust e Fortran deste capitulo. Manter a consistencia na nomenclatura e crucial para evitar erros na implementacao da retropropagacao, onde a confusao entre indices de camadas e uma fonte comum de bugs. Recomenda-se always verificar as dimensoes dos arrays antes de operacoes matriciais.

---

## 3. Forward Propagation Completa

A propagacao direta (forward propagation) e o processo pelo qual os dados fluem da camada de entrada ate a camada de saida, passando por todas as camadas ocultas. Em cada camada, uma transformacao linear e uma nao-linearidade sao aplicadas em sequencia.

### 3.1 Formula Matematica

Para uma rede com L camadas (contando apenas as que tem pesos — ocultas + saida):

A camada de entrada e simplesmente o vetor x. Para cada camada l de 1 a L:

z[l] = a[l-1] * W[l] + b[l]

a[l] = g[l](z[l])

Onde:
- x = a[0] (a entrada da rede e a ativacao da camada 0)
- W[l] e a matriz de pesos da camada l
- b[l] e o vetor de bias da camada l
- g[l] e a funcao de ativacao da camada l
- z[l] e o valor pre-ativacao (tambem chamado de logito)
- a[l] e a ativacao (saida) da camada l

A predicao final da rede e a[L] — a ativacao da ultima camada.

### 3.2 Dimensoes das Matrizes

Para uma rede com:
- n[0] neuronios na entrada
- n[1] neuronios na primeira camada oculta
- ...
- n[L] neuronios na camada de saida

As dimensoes sao:
- W[1]: n[0] x n[1]
- b[1]: 1 x n[1]
- W[2]: n[1] x n[2]
- b[2]: 1 x n[2]
- ...
- W[L]: n[L-1] x n[L]
- b[L]: 1 x n[L]

Essa padronizacao facilita a implementacao: ao processar cada camada, basta multiplicar a ativacao anterior pela matriz de pesos correspondente e somar o bias.

### 3.3 Exemplo Numerico

Considere uma rede simples com 2 entradas, 3 neuronios na camada oculta e 1 neuronio na saida. Funcao de ativacao: sigmoid em todas as camadas.

Entrada: x = [0.5, 0.3]

Camada oculta:
W[1] = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
b[1] = [0.1, 0.1, 0.1]

z[1] = x * W[1] + b[1]
     = [0.5*0.1 + 0.3*0.4 + 0.1, 0.5*0.2 + 0.3*0.5 + 0.1, 0.5*0.3 + 0.3*0.6 + 0.1]
     = [0.05 + 0.12 + 0.1, 0.10 + 0.15 + 0.1, 0.15 + 0.18 + 0.1]
     = [0.27, 0.35, 0.43]

a[1] = sigmoid(z[1])
     = [1/(1+e^-0.27), 1/(1+e^-0.35), 1/(1+e^-0.43)]
     = [0.567, 0.587, 0.606]

Camada de saida:
W[2] = [[0.7], [0.8], [0.9]]
b[2] = [0.1]

z[2] = a[1] * W[2] + b[2]
     = [0.567*0.7 + 0.587*0.8 + 0.606*0.9 + 0.1]
     = [0.3969 + 0.4696 + 0.5454 + 0.1]
     = [1.5119]

a[2] = sigmoid(1.5119) = 0.819

A rede prediz que a probabilidade da classe positiva e de aproximadamente 81.9%.

Note que os valores intermediarios (z[1], a[1], z[2]) devem ser armazenados para uso posterior na retropropagacao. Sem esses valores, nao e possivel calcular os gradientes necessarios para atualizar os pesos.

### 3.4 Implementacao do Forward Pass

A implementacao do forward pass segue um padrao identico independentemente da linguagem de programacao. Para cada camada:

1. Calcular z = a_prev * W + b
2. Aplicar a funcao de ativacao: a = g(z)
3. Armazenar z e a para uso futuro na retropropagacao
4. Passar a como a_prev para a proxima camada

Os valores intermediarios (z e a de cada camada) devem ser armazenados durante o forward pass porque serao necessarios para o calculo dos gradientes durante a retropropagacao. Em implementacoes com restricao de memoria, tecnicas como checkpointing podem ser usadas para recomendar esses valores sob demanda.

---

## 4. Funcao de Perda — MSE e Cross-Entropy

A funcao de perda (loss function) quantifica quao distante esta a predicao da rede do valor esperado. O treinamento da rede consiste em minimizar essa funcao ajustando os pesos. A escolha da funcao de perda impacta diretamente a forma do espaco de otimizacao e a velocidade de convergencia.

### 4.1 Erro Quadratico Medio (MSE)

O Mean Squared Error e a funcao de perda mais natural para problemas de regressao. Para N exemplos de treinamento:

L = (1/N) * Σ (y_i - ŷ_i)²

Onde y_i e o valor real e ŷ_i e a predicao da rede.

As propriedades do MSE:
- Sempre nao-negativo: (y - ŷ)² >= 0
- Igual a zero somente quando predicao e valor real sao identicos
- Penaliza erros grandes mais que erros pequenos (devido ao quadrado)
- Derivada simples: dL/dŷ = -2(y - ŷ)/N, proporcional ao erro
- Diferenciavel em todo o dominio

O gradiente do MSE em relacao a predicao e simplesmente -2(y - ŷ)/N. Esse gradiente e passado para tras durante a retropropagacao para ajustar os pesos.

Para classificacao, o MSE tambem pode ser usado (e historicamente era), mas apresenta problemas de convergencia. Quando combinado com sigmoid na saida, o gradiente pode ser muito pequeno para valores saturados, levando a treinamento extremamente lento. Por isso, para classificacao, usa-se preferencialmente a Cross-Entropy.

### 4.2 Entropia Cruzada (Cross-Entropy)

A Cross-Entropy e a funcao de perda padrao para classificacao binaria e multi-classe. Ela mede a divergencia entre a distribuicao de probabilidade predita pela rede e a distribuicao real (one-hot encoding).

Para classificacao binaria:

L = -[y * log(ŷ) + (1 - y) * log(1 - ŷ)]

Para classificacao multi-classe com K classes:

L = -Σ (k=1 a K) y_k * log(ŷ_k)

Propriedades da Cross-Entropy:
- Penaliza fortemente predicoes erradas com alta confianca
- Combinada com softmax/sigmoid, produz gradientes limpos sem saturacao
- Diferenciavel e convexa (garante otimizacao por gradiente descendente)
- Interpretavel em termos de informacao: mede quantos bits de informacao sao perdidos

### 4.3 Por Que Cross-Entropy para Classificacao

Quando usamos sigmoid (ou softmax) na camada de saida, o gradiente da funcao de perda MSE pode ser escrito como:

dL/dz = (ŷ - y) * σ'(z)

O termo σ'(z) pode ser muito pequeno quando o logito z e grande em magnitude (positivo ou negativo), causando o problema de gradiente que desaparece. Por exemplo, se z = 5, σ'(z) = 0.0067. Se z = -5, σ'(z) = 0.0067. O gradiente e reduzido em 99% para predicoes que estao longe do alvo — exatamente o oposto do que queremos.

A Cross-Entropy, ao contrário, produz:

dL/dz = ŷ - y

Que e simplesmente o erro de predicao, sem o termo de derivada da sigmoid. Isso garante que mesmo para predicoes muito erradas, o gradiente e suficientemente grande para atualizar os pesos eficientemente. A Cross-Entropy e, portanto, a escolha natural para classificacao binaria com sigmoid na saida.

### 4.4 Funcoes de Perda Comuns

Para regressao, as funcoes de perda mais comuns sao MSE e MAE (Mean Absolute Error). O MSE e diferenciavel e suave, enquanto o MAE e mais robusto a outliers (pois nao quadrifica o erro).

Para classificacao binaria, a Binary Cross-Entropy (BCE) e o padrao. Para multi-classe, a Categorical Cross-Entropy (com softmax na saida) e a escolha recomendada.

Em implementacoes reais, e comum adicionar um pequeno epsilon (por exemplo, 1e-7) dentro do logaritmo para evitar log(0), que resultaria em infinito negativo. Isso nao afeta significativamente os gradientes mas evita instabilidades numericas.

---

## 5. Numero de Neuronios e Camadas

Uma das perguntas mais frequentes no design de redes neurais e: quantas camadas e quantos neuronios por camada usar? Nao existe uma resposta universal, mas diretrizes praticas baseadas em decadas de experiencia podem guiar a escolha.

### 5.1 Regra Pratica para Camadas

Para problemas simples (classificacao com fronteiras simples, regressao com relacoes aproximadamente lineares): uma camada oculta e suficiente. Com neuronios suficientes, uma unica camada oculta pode aproximar qualquer funcao continua (pelo Teorema de Aproximacao Universal).

Para problemas complexos (reconhecimento de padroes em imagens, processamento de linguagem natural, relacoes com multiplos niveis de abstracao): duas ou mais camadas ocultas podem ser necessarias. Cada camada adicional permite a rede aprender representacoes mais abstratas.

Em geral, comecar com uma ou duas camadas ocultas e uma boa estrategia. Adicionar camadas adicionais so faz sentido quando ha evidencia empirica de que a rede precisa de maior profundidade para capturar a complexidade do problema.

### 5.2 Regra Pratica para Neuronios

Para a camada de saida, o numero de neuronios e determinado pelo problema: 1 para regressao e classificacao binaria, K para classificacao multi-classe com K classes.

Para as camadas ocultas, regras comuns incluem:

Uma abordagem conservadora e comecar com um numero de neuronios igual ou ligeiramente maior que o numero de entradas. Se o problema tem 10 features, comecar com 12 a 16 neuronios na primeira camada oculta.

Outra abordagem e usar uma estrutura de funil (tapered). Se a rede tem 8 entradas, 4 neuronios na primeira camada oculta e 2 na segunda. Isso força a rede a aprender representacoes compactas.

Para problemas com muitas features e poucos dados, reduzir o numero de neuronios ajuda a evitar overfitting. Para problemas com muitos dados e alta dimensionalidade, neuronios adicionais podem ser necessarios para capturar toda a complexidade.

### 5.3 Overfitting e Capacidade da Rede

Uma rede com muitos neuronios e camadas tem alta capacidade — pode memorizar os dados de treinamento, incluindo ruido e outliers. Isso se chama overfitting: a rede vai bem no treinamento mas mal em dados novos.

Sinais de overfitting: a perda de treinamento diminui continuamente enquanto a perda de validacao comeca a aumentar. A acuracia no treinamento e proxima de 100% enquanto a acuracia de validacao estagna ou cai.

Tecnicas para combater overfitting incluem:
- Regularizacao L1 e L2 (penalizar pesos grandes)
- Dropout (desligar aleatoriamente neuronios durante treinamento)
- Early stopping (parar quando a perda de validacao comeca a subir)
- Aumento de dados (data augmentation)
- Arquiteturas mais simples (menos camadas/neuronios)

### 5.4 Diminuicao do Numero de Neuronios

Uma estrategia eficiente e comecar com uma rede relativamente grande e ir removendo neuronios ate encontrar o equilibrio entre capacidade e generalizacao. Esse processo e chamado de poda (pruning) e e uma forma de busca em espaco de arquitetura.

O oposto — comecar pequeno e ir adicionando neuronios (growing) — tambem funciona e e mais eficiente computacionalmente, pois evita treinar redes grandes desnecessariamente.

### 5.5 Resumo das Diretrizes

| Tipo de Problema | Camadas Ocultas | Neuronios por Camada |
|------------------|-----------------|----------------------|
| Classificacao simples (AND, OR) | 0-1 | 2-4 |
| Classificacao binaria (2-20 features) | 1-2 | 8-32 |
| Classificacao multi-classe (20-100 features) | 2-3 | 32-128 |
| Regressao simples | 1 | 4-16 |
| Regressao complexa | 2-3 | 16-64 |

Essas diretrizes sao pontos de partida. O design real de uma rede neural requer experimentacao, validacao cruzada e iteracao.

---

## 6. Teorema de Aproximacao Universal

O Teorema de Aproximacao Universal e uma das contribuicoes teoricas mais importantes para a compreensao de redes neurais. Formulado por George Cybenko (1989) e generalizado por Kurt Hornik (1991), ele estabelece os limites teoricos da capacidade de aproximacao de redes neurais.

### 6.1 Enunciado do Teorema

A versao mais citada afirma: Seja f: R^n -> R uma funcao continua em um dominio compacto D. Para qualquer epsilon > 0, existe uma rede neural com uma unica camada oculta, com um numero suficiente de neuronios, e uma funcao de ativacao sigmoide (ou qualquer funcao nao-linear nao-constante, limitada e monotonica crescente), tal que a aproximacao da rede e epsilon-precisa em D.

Em linguagem mais simples: qualquer funcao continua pode ser aproximada arbitrariamente bem por uma rede neural com uma unica camada oculta, desde que a camada oculta tenha neuronios suficientes.

### 6.2 Implicacoes Praticas

O teorema diz que uma rede com uma unica camada oculta e suficiente em termos teoricos. Isso nao significa que devemos sempre usar apenas uma camada oculta. Na pratica, redes profundas (multiplas camadas ocultas) podem precisar de menos neuronios totais para atingir a mesma precisao.

Imagine que uma funcao pode ser aproximada por:
- Uma camada oculta com 10.000 neuronios
- Duas camadas ocultas com 100 neuronios cada (total de 200 neuronios)

A segunda opcao e computacionalmente muito mais eficiente. A profundidade permite a rede aprender representacoes compostas, onde cada camada aprende uma abstracao da camada anterior, resultando em representacoes mais compactas.

### 6.3 Limitacoes

O teorema e um resultado de existencia — ele garante que uma aproximacao existe, mas nao diz nada sobre:
- Quantos neuronios sao necessarios (pode ser um numero enorme)
- Como encontrar os pesos corretos (o treinamento pode falhar por minimos locais)
- Quao rapido o treinamento converge
- Se a generalizacao para dados fora do treinamento sera boa

Ate mesmo a funcao de aproximacao exata pode exigir um numero de neuronios exponencial na dimensao de entrada. Para problemas de alta dimensionalidade (imagens, videos, texto), uma rede rasa pode precisar de tantos neuronios que se torna inviavel. Isso justifica o uso de redes profundas em vez de redes rasas largas.

### 6.4 Profundidade vs. Largura

A pesquisa empirica mostrou consistentemente que redes profundas (multiplas camadas ocultas) aprendem representacoes mais eficientes que redes rasas (uma unica camada oculta grande) para a mesma tarefa. A razao e que cada camada pode aprender uma abstracao da camada anterior.

Em reconhecimento de imagens, por exemplo:
- Primeira camada: detecta bordas e gradientes
- Segunda camada: combina bordas em texturas e padroes simples
- Terceira camada: combina padroes em partes de objetos (olhos, narizes, bocas)
- Quarta camada: combina partes em objetos inteiros

Essa hierarquia de abstracoes e possivel apenas com profundidade.

### 6.5 Implicacao para Pratica

Para o praticante, o teorema oferece uma garantia fundamental: se o problema pode ser descrito por uma funcao continua, uma rede neural pode resolve-lo. Isso cobre a vasta maioria dos problemas de machine learning.

A estrategia recomendada e: comecar com uma rede moderada (2-3 camadas ocultas), e aumentar a profundidade ou a largura conforme necessario, validando sempre com dados de teste.

### 6.6 Limitacoes e Cautelas

O teorema de Aproximacao Universal tem varias limitacoes importantes que devem ser compreendidas:

Primeiro, o teorema e nao-construtivo. Ele garante que uma aproximacao existe, mas nao diz como encontra-la. O treinamento por gradiente descendente pode falhar por minimos locais, pelo problema do gradiente que desaparece, ou por outros fenomenos de otimizacao.

Segundo, o numero de neuronios necessario pode ser exponencial na dimensao de entrada. Para um problema com 100 features, a rede pode precisar de 2^100 neuronios na camada oculta — um numero inexploravel. Isso justifica o uso de profundidade em vez de largura.

Terceiro, o teorema fala sobre aproximacao no dominio compacto. Para dados fora do dominio de treinamento, a rede nao tem garantia nenhuma. A generalizacao para dados novos depende da regularidade dos dados e do design da rede, nao apenas do teorema.

---

## 7. Inicializacao de Pesos — Xavier e He

A inicializacao dos pesos e uma etapa critica no treinamento de redes neurais. Uma inicializacao inadequada pode impedir completamente o treinamento, mesmo com a melhor arquitetura e os melhores hiperparametros.

### 7.1 O Problema de Inicializacao Arbitraria

Se todos os pesos sao inicializados com zero, todos os neuronios de uma camada oculta calcularao a mesma coisa. O gradiente sera identico para todos, e os pesos serao atualizados de forma identica. A rede nunca quebrara a simetria — todos os neuronios serao funcionalemente equivalentes, desperdicando a capacidade da camada.

Se os pesos sao inicializados com valores muito grandes, as ativacoes e gradientes podem crescer exponencialmente camada a camada, causando overflow numerico (exploding gradients).

Se os pesos sao inicializados com valores muito pequenos, as ativacoes e gradientes podem diminuir exponencialmente, tornando-se praticamente zero nas camadas profundas (vanishing gradients).

### 7.2 Inicializacao de Xavier (Glorot)

A inicializacao de Xavier, proposta por Xavier Glorot e Yoshua Bengio em 2010, resolve o problema do balanceamento entre saidas grandes e pequenas. A ideia e: a variancia das ativacoes de entrada e saida de uma camada devem ser iguais.

Para atingir isso, Xavier propoe que os pesos sejam inicializados com uma distribuicao normal com media zero e variancia igual a 2/(n_in + n_out), onde n_in e o numero de neuronios de entrada e n_out e o numero de neuronios de saida da camada.

No caso de distribuicao uniforme no intervalo [-limite, limite]:

limite = sqrt(6 / (n_in + n_out))

Essa inicializacao funciona bem quando a funcao de ativacao e simetrica em torno de zero, como sigmoid e tanh. Para essas funcoes, as ativacoes estao centradas em zero e a variancia e razoavelmente preservada entre camadas.

### 7.3 Inicializacao de He

Kaiming He e colaboradores (2015) proposeram uma variante especificamente para a funcao ReLU. Como ReLU zera metade das ativacoes (todas as negativas), a variancia e cortada pela metade a cada camada. Para compensar isso, a inicializacao de He usa uma variancia duas vezes maior que Xavier:

Variancia = 2 / n_in

Ou equivalente, no caso uniforme:

limite = sqrt(6 / n_in)

Essa inicializacao e o padrao para redes que usam ReLU ou suas variantes (Leaky ReLU, PReLU, ELU).

### 7.4 Regra Geral

A regra simples e: use Xavier quando a funcao de ativacao e simetrica em torno de zero (sigmoid, tanh). Use He quando a funcao de ativacao e ReLU ou sua familia. Essa distincao e suficiente para a maioria dos casos praticos.

Em C++, Rust e Fortran, a implementacao da inicializacao requer um gerador de numeros aleatorios. Para distribuicao normal, a transformacao de Box-Muller e uma escolha simples e eficiente. Para distribuicao uniforme, o gerador padrao da linguagem e suficiente.

### 7.5 Inicializacao de Bias

Os biases podem ser inicializados com zero na maioria dos casos. Para camadas ocultas, nao ha restricao especial. Para certas arquiteturas, como LSTMs, biases de portao podem ser inicializados com 1 para facilitar o fluxo de gradiente no inicio do treinamento, mas isso e um caso especial nao relevante para MLP classica.

### 7.6 Impacto da Inicializacao na Pratica

Para demonstrar a importancia da inicializacao, considere uma rede com 10 camadas ocultas de 100 neuronios cada, usando sigmoid. Se os pesos sao inicializados com distribuicao normal padrao (media 0, variancia 1):

Apos 10 camadas, a variancia da saida e aproximadamente 10^3 = 1000 vezes a variancia da entrada. Isso causa overflow numerico e gradientes enormes.

Com a inicializacao de Xavier (variancia = 2/(100+100) = 0.01), a variancia e preservada entre camadas, e o treinamento converge normalmente.

Essa diferenca dramatica demonstra por que a inicializacao nao e um detalhe de implementacao — e um prerequisito para que o treinamento funcione. Mesmo com a melhor arquitetura e os melhores hiperparametros, uma inicializacao inadequada pode impedir completamente a convergencia.

---

## 8. Implementacao Completa em C++

Nesta secao, implementamos uma MLP completa em C++17, incluindo operacoes matriciais, funcoes de ativacao, funcoes de perda, inicializacao de pesos e treinamento por retropropagacao. O codigo e autocontido — nao usa bibliotecas externas.

### 8.1 Estrutura do Projeto

A implementacao e organizada em uma unica classe MLP que encapsula toda a logica da rede. Os principais componentes sao:

- Estrutura Matrix para operacoes matriciais basicas
- Funcoes de ativacao (sigmoid, relu, tanh) e suas derivadas
- Funcoes de perda (MSE, cross-entropy)
- Classe MLP com construcao, forward pass, retropropagacao e treinamento
- Funcao main com exemplos de treinamento (XOR e classificacao)

### 8.2 Codigo Completo

```cpp
/**
 * mlp.cpp — Multi-Layer Perceptron implemented from scratch in C++17
 * No external libraries — pure standard C++ implementation
 * Includes: Matrix operations, Activation functions, Loss functions,
 *           Forward propagation, Backpropagation, Weight initialization
 */

#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <cassert>
#include <functional>
#include <string>

// =============================================================================
// Matrix class — fundamental linear algebra operations
// =============================================================================

struct Matrix {
    int rows;
    int cols;
    std::vector<double> data;

    Matrix() : rows(0), cols(0) {}

    Matrix(int r, int c) : rows(r), cols(c), data(r * c, 0.0) {}

    Matrix(int r, int c, double init_val)
        : rows(r), cols(c), data(r * c, init_val) {}

    double& at(int r, int c) {
        return data[r * cols + c];
    }

    const double& at(int r, int c) const {
        return data[r * cols + c];
    }

    // Element-wise access by flat index
    double& operator[](int idx) { return data[idx]; }
    const double& operator[](int idx) const { return data[idx]; }

    // Matrix multiplication: result = this * other
    Matrix matmul(const Matrix& other) const {
        assert(cols == other.rows);
        Matrix result(rows, other.cols);
        for (int i = 0; i < rows; ++i) {
            for (int k = 0; k < cols; ++k) {
                double a_ik = at(i, k);
                for (int j = 0; j < other.cols; ++j) {
                    result.at(i, j) += a_ik * other.at(k, j);
                }
            }
        }
        return result;
    }

    // Matrix + Vector broadcasting (add bias to each row)
    Matrix add_bias(const Matrix& bias) const {
        assert(bias.rows == 1 && bias.cols == cols);
        Matrix result = *this;
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                result.at(i, j) += bias.at(0, j);
            }
        }
        return result;
    }

    // Transpose
    Matrix transpose() const {
        Matrix result(cols, rows);
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                result.at(j, i) = at(i, j);
            }
        }
        return result;
    }

    // Apply function element-wise
    Matrix apply(std::function<double(double)> func) const {
        Matrix result(rows, cols);
        for (int i = 0; i < rows * cols; ++i) {
            result[i] = func(data[i]);
        }
        return result;
    }

    // Print matrix
    void print(const std::string& name = "") const {
        if (!name.empty()) {
            std::cout << name << " (" << rows << "x" << cols << "):\n";
        }
        for (int i = 0; i < rows; ++i) {
            std::cout << "  [";
            for (int j = 0; j < cols; ++j) {
                std::cout << at(i, j);
                if (j < cols - 1) std::cout << ", ";
            }
            std::cout << "]\n";
        }
    }
};

// =============================================================================
// Activation Functions
// =============================================================================

namespace Activation {

    // Sigmoid: sigma(z) = 1 / (1 + exp(-z))
    double sigmoid(double z) {
        return 1.0 / (1.0 + std::exp(-z));
    }

    // Derivative of sigmoid: sigma'(z) = sigma(z) * (1 - sigma(z))
    double sigmoid_derivative(double z) {
        double s = sigmoid(z);
        return s * (1.0 - s);
    }

    // ReLU: max(0, z)
    double relu(double z) {
        return std::max(0.0, z);
    }

    // Derivative of ReLU
    double relu_derivative(double z) {
        return z > 0.0 ? 1.0 : 0.0;
    }

    // Tanh: tanh(z)
    double tanh_func(double z) {
        return std::tanh(z);
    }

    // Derivative of tanh: 1 - tanh^2(z)
    double tanh_derivative(double z) {
        double t = std::tanh(z);
        return 1.0 - t * t;
    }

    // Apply activation by name
    Matrix apply(const Matrix& m, const std::string& name) {
        if (name == "sigmoid") {
            return m.apply(sigmoid);
        } else if (name == "relu") {
            return m.apply(relu);
        } else if (name == "tanh") {
            return m.apply(tanh_func);
        }
        return m; // identity
    }

    // Apply derivative by name (receives z values, not activated values)
    Matrix apply_derivative(const Matrix& z, const std::string& name) {
        if (name == "sigmoid") {
            return z.apply(sigmoid_derivative);
        } else if (name == "relu") {
            return z.apply(relu_derivative);
        } else if (name == "tanh") {
            return z.apply(tanh_derivative);
        }
        return Matrix(z.rows, z.cols, 1.0); // identity derivative
    }
}

// =============================================================================
// Loss Functions
// =============================================================================

namespace Loss {

    // Mean Squared Error
    double mse(const Matrix& predicted, const Matrix& target) {
        assert(predicted.rows == target.rows && predicted.cols == target.cols);
        double sum = 0.0;
        int n = predicted.rows * predicted.cols;
        for (int i = 0; i < n; ++i) {
            double diff = predicted[i] - target[i];
            sum += diff * diff;
        }
        return sum / n;
    }

    // Derivative of MSE w.r.t. predicted: 2*(predicted - target)/n
    Matrix mse_derivative(const Matrix& predicted, const Matrix& target) {
        assert(predicted.rows == target.rows && predicted.cols == target.cols);
        Matrix result(predicted.rows, predicted.cols);
        int n = predicted.rows * predicted.cols;
        for (int i = 0; i < n; ++i) {
            result[i] = 2.0 * (predicted[i] - target[i]) / n;
        }
        return result;
    }

    // Binary Cross-Entropy
    double binary_cross_entropy(const Matrix& predicted, const Matrix& target) {
        assert(predicted.rows == target.rows && predicted.cols == target.cols);
        double sum = 0.0;
        int n = predicted.rows * predicted.cols;
        const double eps = 1e-7;
        for (int i = 0; i < n; ++i) {
            double p = std::clamp(predicted[i], eps, 1.0 - eps);
            sum -= target[i] * std::log(p) + (1.0 - target[i]) * std::log(1.0 - p);
        }
        return sum / n;
    }

    // Derivative of BCE w.r.t. predicted (before sigmoid): predicted - target
    // This assumes predicted = sigmoid(z), and we want dL/dz
    Matrix binary_cross_entropy_derivative(
            const Matrix& predicted, const Matrix& target) {
        assert(predicted.rows == target.rows && predicted.cols == target.cols);
        Matrix result(predicted.rows, predicted.cols);
        int n = predicted.rows * predicted.cols;
        for (int i = 0; i < n; ++i) {
            result[i] = (predicted[i] - target[i]) / n;
        }
        return result;
    }
}

// =============================================================================
// Weight Initialization — Xavier and He
// =============================================================================

namespace Init {

    // Xavier/Glorot uniform initialization
    // For sigmoid/tanh activations
    Matrix xavier_uniform(int fan_in, int fan_out, std::mt19937& rng) {
        double limit = std::sqrt(6.0 / (fan_in + fan_out));
        std::uniform_real_distribution<double> dist(-limit, limit);
        Matrix w(fan_in, fan_out);
        for (int i = 0; i < fan_in * fan_out; ++i) {
            w[i] = dist(rng);
        }
        return w;
    }

    // He uniform initialization
    // For ReLU activations
    Matrix he_uniform(int fan_in, int fan_out, std::mt19937& rng) {
        double limit = std::sqrt(6.0 / fan_in);
        std::uniform_real_distribution<double> dist(-limit, limit);
        Matrix w(fan_in, fan_out);
        for (int i = 0; i < fan_in * fan_out; ++i) {
            w[i] = dist(rng);
        }
        return w;
    }

    // Simple uniform initialization (for testing)
    Matrix uniform(int rows, int cols, double low, double high,
                   std::mt19937& rng) {
        std::uniform_real_distribution<double> dist(low, high);
        Matrix w(rows, cols);
        for (int i = 0; i < rows * cols; ++i) {
            w[i] = dist(rng);
        }
        return w;
    }

    // Zero bias initialization
    Matrix zero_bias(int rows, int cols) {
        return Matrix(rows, cols, 0.0);
    }
}

// =============================================================================
// MLP Class — Complete Multi-Layer Perceptron
// =============================================================================

class MLP {
public:
    // Network architecture
    std::vector<int> layer_sizes;
    int num_layers; // number of weight layers (excluding input)

    // Parameters
    std::vector<Matrix> weights;
    std::vector<Matrix> biases;

    // Cache for backpropagation
    std::vector<Matrix> activations; // a[l] for each layer
    std::vector<Matrix> pre_activations; // z[l] for each layer

    // Hyperparameters
    std::string activation_name;
    double learning_rate;
    std::mt19937 rng;

    // Constructor: layer_sizes = {input_dim, hidden1, hidden2, ..., output_dim}
    MLP(const std::vector<int>& sizes,
        const std::string& activation = "sigmoid",
        double lr = 0.1,
        unsigned int seed = 42)
        : layer_sizes(sizes),
          num_layers(sizes.size() - 1),
          activation_name(activation),
          learning_rate(lr),
          rng(seed)
    {
        initialize_weights();
    }

    // Initialize all weights and biases
    void initialize_weights() {
        weights.resize(num_layers);
        biases.resize(num_layers);

        for (int l = 0; l < num_layers; ++l) {
            int fan_in = layer_sizes[l];
            int fan_out = layer_sizes[l + 1];

            // Choose initialization based on activation function
            if (activation_name == "relu") {
                weights[l] = Init::he_uniform(fan_in, fan_out, rng);
            } else {
                weights[l] = Init::xavier_uniform(fan_in, fan_out, rng);
            }

            biases[l] = Init::zero_bias(1, fan_out);
        }
    }

    // Forward propagation: returns the output of the network
    Matrix forward(const Matrix& input) {
        activations.resize(num_layers + 1);
        pre_activations.resize(num_layers);

        // Input layer
        activations[0] = input;

        for (int l = 0; l < num_layers; ++l) {
            // z[l] = a[l-1] * W[l] + b[l]
            Matrix z = activations[l].matmul(weights[l]);
            z = z.add_bias(biases[l]);
            pre_activations[l] = z;

            // a[l] = activation(z[l])
            // Output layer uses sigmoid for classification
            if (l == num_layers - 1) {
                activations[l + 1] = z.apply(Activation::sigmoid);
            } else {
                activations[l + 1] = Activation::apply(z, activation_name);
            }
        }

        return activations[num_layers];
    }

    // Compute loss
    double compute_loss(const Matrix& predicted, const Matrix& target,
                        const std::string& loss_name = "mse") {
        if (loss_name == "mse") {
            return Loss::mse(predicted, target);
        } else if (loss_name == "bce") {
            return Loss::binary_cross_entropy(predicted, target);
        }
        return Loss::mse(predicted, target);
    }

    // Backpropagation: compute gradients and update weights
    void backward(const Matrix& target, const std::string& loss_name = "mse") {
        int m = target.rows; // batch size

        // Output layer gradient
        // dL/dz[L] = dL/da[L] * da[L]/dz[L]
        Matrix delta;
        if (loss_name == "bce" && activation_name == "sigmoid") {
            // For BCE + sigmoid: delta = a[L] - y (simplified gradient)
            delta = activations[num_layers];
            for (int i = 0; i < delta.rows * delta.cols; ++i) {
                delta[i] -= target[i];
            }
        } else {
            // General case: compute loss derivative and multiply by activation derivative
            Matrix d_loss;
            if (loss_name == "bce") {
                d_loss = Loss::binary_cross_entropy_derivative(
                    activations[num_layers], target);
            } else {
                d_loss = Loss::mse_derivative(activations[num_layers], target);
            }
            Matrix d_activation = Activation::apply_derivative(
                pre_activations[num_layers - 1], "sigmoid");
            delta = d_loss;
            for (int i = 0; i < delta.rows * delta.cols; ++i) {
                delta[i] *= d_activation[i];
            }
        }

        // Backpropagate through layers
        for (int l = num_layers - 1; l >= 0; --l) {
            // Compute gradients for weights and biases
            // dW[l] = a[l-1]^T * delta
            Matrix dW = activations[l].transpose().matmul(delta);
            // db[l] = sum(delta, axis=0)
            Matrix db(1, delta.cols, 0.0);
            for (int i = 0; i < delta.rows; ++i) {
                for (int j = 0; j < delta.cols; ++j) {
                    db.at(0, j) += delta.at(i, j);
                }
            }

            // Update weights and biases (gradient descent)
            for (int i = 0; i < weights[l].rows * weights[l].cols; ++i) {
                weights[l][i] -= learning_rate * dW[i] / m;
            }
            for (int j = 0; j < biases[l].cols; ++j) {
                biases[l].at(0, j) -= learning_rate * db.at(0, j) / m;
            }

            // Propagate delta to previous layer (if not input layer)
            if (l > 0) {
                Matrix d_activation = Activation::apply_derivative(
                    pre_activations[l - 1], activation_name);
                Matrix W_transposed = weights[l].transpose();
                delta = delta.matmul(W_transposed);
                for (int i = 0; i < delta.rows * delta.cols; ++i) {
                    delta[i] *= d_activation[i];
                }
            }
        }
    }

    // Training loop
    void train(const Matrix& X, const Matrix& y, int epochs,
               bool verbose = true) {
        for (int epoch = 0; epoch < epochs; ++epoch) {
            // Forward pass
            Matrix output = forward(X);

            // Compute loss
            double loss = compute_loss(output, y, "bce");

            // Backward pass
            backward(y, "bce");

            // Print progress
            if (verbose && (epoch % (epochs / 10) == 0 || epoch == epochs - 1)) {
                std::cout << "Epoch " << epoch << "/" << epochs
                          << " - Loss: " << loss << std::endl;
            }
        }
    }

    // Predict: forward pass without storing cache
    Matrix predict(const Matrix& input) {
        return forward(input);
    }

    // Print network summary
    void summary() const {
        std::cout << "=== MLP Network Summary ===\n";
        std::cout << "Layers: " << num_layers << " weight layers\n";
        std::cout << "Architecture: ";
        for (int i = 0; i < (int)layer_sizes.size(); ++i) {
            std::cout << layer_sizes[i];
            if (i < (int)layer_sizes.size() - 1) std::cout << " -> ";
        }
        std::cout << "\n";
        std::cout << "Activation: " << activation_name << "\n";
        std::cout << "Learning rate: " << learning_rate << "\n";

        int total_params = 0;
        for (int l = 0; l < num_layers; ++l) {
            int params = weights[l].rows * weights[l].cols + biases[l].cols;
            total_params += params;
            std::cout << "  Layer " << l + 1 << ": "
                      << weights[l].rows << " -> " << weights[l].cols
                      << " (" << params << " params)\n";
        }
        std::cout << "Total parameters: " << total_params << "\n";
        std::cout << "===========================\n\n";
    }
};

// =============================================================================
// Utility functions for test cases
// =============================================================================

// Helper to create a Matrix from a vector of vectors
Matrix from_vec(const std::vector<std::vector<double>>& data) {
    int rows = data.size();
    int cols = data[0].size();
    Matrix m(rows, cols);
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) {
            m.at(i, j) = data[i][j];
        }
    }
    return m;
}

// Print predictions
void print_predictions(const Matrix& preds, const Matrix& targets,
                       const std::string& label) {
    std::cout << "\n" << label << ":\n";
    for (int i = 0; i < preds.rows; ++i) {
        std::cout << "  Input: [";
        std::cout << "sample " << i << "] "
                  << "Predicted: " << preds.at(i, 0)
                  << " (rounded: " << (preds.at(i, 0) > 0.5 ? 1 : 0) << ")"
                  << ", Target: " << targets.at(i, 0) << "\n";
    }
}

// =============================================================================
// Test Case 1: XOR Problem
// =============================================================================

void test_xor() {
    std::cout << "========== Test 1: XOR Problem ==========\n";

    // XOR training data
    Matrix X = from_vec({{0, 0}, {0, 1}, {1, 0}, {1, 1}});
    Matrix y = from_vec({{0}, {1}, {1}, {0}});

    // Create MLP: 2 inputs -> 8 hidden -> 1 output
    MLP mlp({2, 8, 1}, "sigmoid", 5.0, 42);
    mlp.summary();

    // Train for 5000 epochs
    mlp.train(X, y, 5000, true);

    // Test predictions
    Matrix predictions = mlp.predict(X);
    print_predictions(predictions, y, "XOR Predictions");

    // Verify all predictions are close to targets
    bool all_correct = true;
    for (int i = 0; i < predictions.rows; ++i) {
        int predicted = predictions.at(i, 0) > 0.5 ? 1 : 0;
        int target = static_cast<int>(y.at(i, 0));
        if (predicted != target) {
            all_correct = false;
        }
    }
    std::cout << "\nXOR Test Result: "
              << (all_correct ? "PASSED" : "FAILED") << "\n\n";
}

// =============================================================================
// Test Case 2: Non-linear classification (two concentric circles)
// =============================================================================

void test_nonlinear_classification() {
    std::cout << "========== Test 2: Non-Linear Classification ==========\n";

    // Generate two concentric circles
    std::mt19937 rng(123);
    std::uniform_real_distribution<double> angle_dist(0.0, 2.0 * M_PI);
    std::uniform_real_distribution<double> radius_inner(0.0, 0.8);
    std::uniform_real_distribution<double> radius_outer(1.5, 2.5);
    std::normal_distribution<double> noise(0.0, 0.1);

    int n_samples = 100;
    std::vector<std::vector<double>> X_data;
    std::vector<std::vector<double>> y_data;

    // Inner circle (class 0)
    for (int i = 0; i < n_samples / 2; ++i) {
        double angle = angle_dist(rng);
        double r = radius_inner(rng);
        X_data.push_back({r * std::cos(angle) + noise(rng),
                          r * std::sin(angle) + noise(rng)});
        y_data.push_back({0.0});
    }

    // Outer circle (class 1)
    for (int i = 0; i < n_samples / 2; ++i) {
        double angle = angle_dist(rng);
        double r = radius_outer(rng);
        X_data.push_back({r * std::cos(angle) + noise(rng),
                          r * std::sin(angle) + noise(rng)});
        y_data.push_back({1.0});
    }

    Matrix X = from_vec(X_data);
    Matrix y = from_vec(y_data);

    // Create MLP: 2 inputs -> 16 hidden -> 16 hidden -> 1 output
    MLP mlp({2, 16, 16, 1}, "sigmoid", 1.0, 42);
    mlp.summary();

    // Train for 3000 epochs
    mlp.train(X, y, 3000, true);

    // Test predictions
    Matrix predictions = mlp.predict(X);

    // Calculate accuracy
    int correct = 0;
    for (int i = 0; i < predictions.rows; ++i) {
        int predicted = predictions.at(i, 0) > 0.5 ? 1 : 0;
        int target = static_cast<int>(y.at(i, 0));
        if (predicted == target) ++correct;
    }
    double accuracy = static_cast<double>(correct) / predictions.rows;
    std::cout << "\nClassification Accuracy: " << accuracy * 100.0 << "%\n";
    std::cout << "Non-Linear Classification Test: "
              << (accuracy > 0.85 ? "PASSED" : "NEEDS MORE TRAINING") << "\n\n";
}

// =============================================================================
// Test Case 3: AND gate (simple linearly separable problem)
// =============================================================================

void test_and_gate() {
    std::cout << "========== Test 3: AND Gate ==========\n";

    Matrix X = from_vec({{0, 0}, {0, 1}, {1, 0}, {1, 1}});
    Matrix y = from_vec({{0}, {0}, {0}, {1}});

    // Simple network: 2 inputs -> 4 hidden -> 1 output
    MLP mlp({2, 4, 1}, "sigmoid", 5.0, 42);
    mlp.summary();

    mlp.train(X, y, 2000, true);

    Matrix predictions = mlp.predict(X);
    print_predictions(predictions, y, "AND Predictions");

    bool all_correct = true;
    for (int i = 0; i < predictions.rows; ++i) {
        int predicted = predictions.at(i, 0) > 0.5 ? 1 : 0;
        int target = static_cast<int>(y.at(i, 0));
        if (predicted != target) all_correct = false;
    }
    std::cout << "\nAND Test Result: "
              << (all_correct ? "PASSED" : "FAILED") << "\n\n";
}

// =============================================================================
// Test Case 4: OR gate
// =============================================================================

void test_or_gate() {
    std::cout << "========== Test 4: OR Gate ==========\n";

    Matrix X = from_vec({{0, 0}, {0, 1}, {1, 0}, {1, 1}});
    Matrix y = from_vec({{0}, {1}, {1}, {1}});

    MLP mlp({2, 4, 1}, "sigmoid", 5.0, 42);
    mlp.summary();

    mlp.train(X, y, 2000, true);

    Matrix predictions = mlp.predict(X);
    print_predictions(predictions, y, "OR Predictions");

    bool all_correct = true;
    for (int i = 0; i < predictions.rows; ++i) {
        int predicted = predictions.at(i, 0) > 0.5 ? 1 : 0;
        int target = static_cast<int>(y.at(i, 0));
        if (predicted != target) all_correct = false;
    }
    std::cout << "\nOR Test Result: "
              << (all_correct ? "PASSED" : "FAILED") << "\n\n";
}

// =============================================================================
// Test Case 5: Regression problem
// =============================================================================

void test_regression() {
    std::cout << "========== Test 5: Regression (sine wave) ==========\n";

    // Generate sine wave data
    std::vector<std::vector<double>> X_data;
    std::vector<std::vector<double>> y_data;

    for (int i = 0; i < 50; ++i) {
        double x = static_cast<double>(i) / 10.0; // 0.0 to 4.9
        double y_val = std::sin(x);
        X_data.push_back({x});
        y_data.push_back({y_val});
    }

    Matrix X = from_vec(X_data);
    Matrix y = from_vec(y_data);

    // Network: 1 input -> 16 hidden -> 16 hidden -> 1 output
    MLP mlp({1, 16, 16, 1}, "tanh", 0.05, 42);
    mlp.summary();

    // Train with MSE loss
    for (int epoch = 0; epoch < 5000; ++epoch) {
        Matrix output = mlp.forward(X);
        double loss = Loss::mse(output, y);
        mlp.backward(y, "mse");

        if (epoch % 1000 == 0 || epoch == 4999) {
            std::cout << "Epoch " << epoch << " - MSE Loss: " << loss << "\n";
        }
    }

    // Evaluate
    Matrix predictions = mlp.predict(X);
    double final_loss = Loss::mse(predictions, y);
    std::cout << "\nFinal MSE Loss: " << final_loss << "\n";
    std::cout << "Regression Test: "
              << (final_loss < 0.1 ? "PASSED" : "NEEDS MORE TRAINING") << "\n\n";
}

// =============================================================================
// Main — Run all tests
// =============================================================================

int main() {
    std::cout << "============================================\n";
    std::cout << "  MLP Implementation Test Suite (C++)\n";
    std::cout << "============================================\n\n";

    test_xor();
    test_nonlinear_classification();
    test_and_gate();
    test_or_gate();
    test_regression();

    std::cout << "============================================\n";
    std::cout << "  All tests completed.\n";
    std::cout << "============================================\n";

    return 0;
}
```

### 8.3 Funcoes Auxiliares Adicionais

A implementacao C++ inclui funcoes auxiliares que facilitam a criacao e manipulacao de matrizes. Essas funcoes sao essenciais para testes e depuracao:

A funcao from_vec() converte um vetor bidimensional (vector of vectors) para uma Matrix. Isso facilita a criacao de dados de treinamento diretamente no codigo, sem a necessidade de carregar de arquivos externos. A funcao verifica implicitamente que todas as linhas tem o mesmo numero de colunas.

A funcao print_predictions() formata e imprime as predicoes da rede lado a lado com os valores esperados. Isso e util para analise qualitativa dos resultados — podemos ver nao so se a rede acertou, mas tambem o quao confiante ela esta em cada predicao.

A inicializacao de pesos e feita pelo construtor da classe MLP. O construtor recebe um vetor de inteiros representando o tamanho de cada camada, o nome da funcao de ativacao, a taxa de aprendizado e uma semente para o gerador de numeros aleatorios. Com base na funcao de ativacao, o construtor escolhe automaticamente entre Xavier e He.

### 8.4 Compilacao e Execucao

Para compilar o codigo C++:

```bash
g++ -std=c++17 -O2 -o mlp mlp.cpp
./mlp
```

O nivel de otimizacao -O2 e recomendado para treinamento ser razoavelmente rapido. Para producao, use -O3.

Se o compilador relatar erros de tipo, verifique se a versao do GCC suporta C++17. Use -std=c++14 como alternativa, mas algumas funcionalidades modernas podem nao estar disponiveis.

Para compilar com informacoes de depuracao (para usar com gdb ou lldb):

```bash
g++ -std=c++17 -g -O0 -o mlp_debug mlp.cpp
```

### 8.5 Analise do Codigo

A implementacao C++ segue o padrao classico de redes neurais:

- A estrutura Matrix encapsula todas as operacoes matriciais. A multiplicacao de matrizes e implementada com o algoritmo basico O(n^3) — para producao, bibliotecas BLAS seriam mais eficientes, mas para fins educacionais a implementacao manual e preferivel.

- A funcao forward() armazena todos os valores intermediarios (ativacoes e pre-ativacoes de cada camada) em vetores. Esses valores sao necessarios para a retropropagacao e devem ser mantidos ate que o backward() seja chamado.

- A funcao backward() implementa o algoritmo de retropropagacao completo. O gradiente da funcao de perda e calculado primeiro para a camada de saida, e entao propagado para tras camada a camada. Em cada camada, os gradientes dos pesos e biases sao computados e os parametros sao atualizados.

- A inicializacao de pesos usa Xavier para sigmoid/tanh e He para ReLU, seguindo as recomendacoes teoricas discutidas na secao 7.

- O treinamento usa descida de gradiente em batch (todos os dados de treinamento sao processados antes de cada atualizacao de pesos). Para conjuntos de dados grandes, mini-batch ou estocastico seriam mais eficientes.

- A funcao summary() imprime um resumo detalhado da arquitetura, incluindo o numero de camadas, tamanhos, funcao de ativacao, taxa de aprendizado e numero total de parametros. Isso e essencial para verificar se a rede foi construida corretamente antes do treinamento.

---

## 9. Implementacao em Rust

Nesta secao, implementamos a mesma MLP em Rust, aproveitando o sistema de tipos forte e o gerenciamento de memoria seguro da linguagem. Rust permite codigos de alto desempenho sem os riscos de erros de memoria comuns em C++.

### 9.1 Vantagens do Rust para Redes Neurais

Rust oferece varias vantagens para implementacao de redes neurais:

Seguranca de memoria: O compilador garante que nao ha accesso simultaneo a dados mutaveis (data race) e que nao ha dangling pointers. Isso elimina uma classe inteira de bugs que sao comuns em C++.

Sem garbage collector: Rust nao usa coletor de lixo. O gerenciamento de memoria e feito em tempo de compilacao, resultando em desempenho previsivel sem pausas de GC.

Sistema de tipos: O compilador Rust exige que todos os tipos sejam explicitos e verificados em compilacao. Isso ajuda a detectar erros de dimensoes de matrizes antes da execucao.

Traits para polimorfismo: Rust usa traits (similar a interfaces em outras linguagens) para polimorfismo estatico, sem o overhead de vtables do C++.

### 9.2 Codigo Completo

```rust
/**
 * mlp.rs — Multi-Layer Perceptron implemented from scratch in Rust
 * No external crates — pure standard library implementation
 * Includes: Matrix operations, Activation functions, Loss functions,
 *           Forward propagation, Backpropagation, Weight initialization
 */

use std::f64::consts::E;

// =============================================================================
// Matrix struct — fundamental linear algebra operations
// =============================================================================

#[derive(Clone, Debug)]
struct Matrix {
    rows: usize,
    cols: usize,
    data: Vec<f64>,
}

impl Matrix {
    // Create a new matrix filled with zeros
    fn zeros(rows: usize, cols: usize) -> Self {
        Matrix {
            rows,
            cols,
            data: vec![0.0; rows * cols],
        }
    }

    // Create a new matrix filled with a constant value
    fn filled(rows: usize, cols: usize, value: f64) -> Self {
        Matrix {
            rows,
            cols,
            data: vec![value; rows * cols],
        }
    }

    // Access element at (row, col) — mutable
    fn at_mut(&mut self, row: usize, col: usize) -> &mut f64 {
        &mut self.data[row * self.cols + col]
    }

    // Access element at (row, col) — immutable
    fn at(&self, row: usize, col: usize) -> f64 {
        self.data[row * self.cols + col]
    }

    // Matrix multiplication: self * other
    fn matmul(&self, other: &Matrix) -> Matrix {
        assert_eq!(self.cols, other.rows,
            "Matrix dimensions mismatch: {}x{} * {}x{}",
            self.rows, self.cols, other.rows, other.cols);

        let mut result = Matrix::zeros(self.rows, other.cols);

        for i in 0..self.rows {
            for k in 0..self.cols {
                let a_ik = self.at(i, k);
                for j in 0..other.cols {
                    *result.at_mut(i, j) += a_ik * other.at(k, j);
                }
            }
        }

        result
    }

    // Add bias vector (broadcasting): add bias to each row
    fn add_bias(&self, bias: &Matrix) -> Matrix {
        assert_eq!(bias.rows, 1);
        assert_eq!(bias.cols, self.cols);

        let mut result = self.clone();
        for i in 0..self.rows {
            for j in 0..self.cols {
                *result.at_mut(i, j) += bias.at(0, j);
            }
        }

        result
    }

    // Transpose
    fn transpose(&self) -> Matrix {
        let mut result = Matrix::zeros(self.cols, self.rows);
        for i in 0..self.rows {
            for j in 0..self.cols {
                *result.at_mut(j, i) = self.at(i, j);
            }
        }
        result
    }

    // Apply function element-wise
    fn apply<F: Fn(f64) -> f64>(&self, func: F) -> Matrix {
        let mut result = Matrix::zeros(self.rows, self.cols);
        for i in 0..self.data.len() {
            result.data[i] = func(self.data[i]);
        }
        result
    }

    // Print matrix
    fn print(&self, name: &str) {
        println!("{} ({}x{}):", name, self.rows, self.cols);
        for i in 0..self.rows {
            print!("  [");
            for j in 0..self.cols {
                print!("{:.6}", self.at(i, j));
                if j < self.cols - 1 {
                    print!(", ");
                }
            }
            println!("]");
        }
    }
}

// =============================================================================
// Activation Functions
// =============================================================================

mod activation {
    use super::*;

    pub fn sigmoid(z: f64) -> f64 {
        1.0 / (1.0 + (-z).exp())
    }

    pub fn sigmoid_derivative(z: f64) -> f64 {
        let s = sigmoid(z);
        s * (1.0 - s)
    }

    pub fn relu(z: f64) -> f64 {
        z.max(0.0)
    }

    pub fn relu_derivative(z: f64) -> f64 {
        if z > 0.0 { 1.0 } else { 0.0 }
    }

    pub fn tanh_func(z: f64) -> f64 {
        z.tanh()
    }

    pub fn tanh_derivative(z: f64) -> f64 {
        let t = z.tanh();
        1.0 - t * t
    }

    pub enum ActivationType {
        Sigmoid,
        Relu,
        Tanh,
    }

    pub fn apply(m: &Matrix, act_type: ActivationType) -> Matrix {
        match act_type {
            ActivationType::Sigmoid => m.apply(sigmoid),
            ActivationType::Relu => m.apply(relu),
            ActivationType::Tanh => m.apply(tanh_func),
        }
    }

    pub fn apply_derivative(z: &Matrix, act_type: ActivationType) -> Matrix {
        match act_type {
            ActivationType::Sigmoid => z.apply(sigmoid_derivative),
            ActivationType::Relu => z.apply(relu_derivative),
            ActivationType::Tanh => z.apply(tanh_derivative),
        }
    }
}

// =============================================================================
// Loss Functions
// =============================================================================

mod loss {
    use super::*;

    pub fn mse(predicted: &Matrix, target: &Matrix) -> f64 {
        assert_eq!(predicted.rows, target.rows);
        assert_eq!(predicted.cols, target.cols);

        let n = (predicted.rows * predicted.cols) as f64;
        let mut sum = 0.0;

        for i in 0..predicted.data.len() {
            let diff = predicted.data[i] - target.data[i];
            sum += diff * diff;
        }

        sum / n
    }

    pub fn mse_derivative(predicted: &Matrix, target: &Matrix) -> Matrix {
        assert_eq!(predicted.rows, target.rows);
        assert_eq!(predicted.cols, target.cols);

        let n = (predicted.rows * predicted.cols) as f64;
        let mut result = Matrix::zeros(predicted.rows, predicted.cols);

        for i in 0..predicted.data.len() {
            result.data[i] = 2.0 * (predicted.data[i] - target.data[i]) / n;
        }

        result
    }

    pub fn binary_cross_entropy(predicted: &Matrix, target: &Matrix) -> f64 {
        assert_eq!(predicted.rows, target.rows);
        assert_eq!(predicted.cols, target.cols);

        let n = (predicted.rows * predicted.cols) as f64;
        let eps = 1e-7;
        let mut sum = 0.0;

        for i in 0..predicted.data.len() {
            let p = predicted.data[i].clamp(eps, 1.0 - eps);
            sum -= target.data[i] * p.ln() + (1.0 - target.data[i]) * (1.0 - p).ln();
        }

        sum / n
    }

    pub fn binary_cross_entropy_derivative(
        predicted: &Matrix,
        target: &Matrix,
    ) -> Matrix {
        assert_eq!(predicted.rows, target.rows);
        assert_eq!(predicted.cols, target.cols);

        let n = (predicted.rows * predicted.cols) as f64;
        let mut result = Matrix::zeros(predicted.rows, predicted.cols);

        for i in 0..predicted.data.len() {
            result.data[i] = (predicted.data[i] - target.data[i]) / n;
        }

        result
    }
}

// =============================================================================
// Weight Initialization — Xavier and He
// =============================================================================

mod init {
    use super::*;
    use std::f64::consts::SQRT_2;

    pub fn xavier_uniform(fan_in: usize, fan_out: usize, rng: &mut u64) -> Matrix {
        let limit = (6.0 / (fan_in as f64 + fan_out as f64)).sqrt();
        let mut m = Matrix::zeros(fan_in, fan_out);
        for i in 0..fan_in * fan_out {
            *rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
            let u = (*rng as f64) / (u64::MAX as f64);
            m.data[i] = -limit + 2.0 * limit * u;
        }
        m
    }

    pub fn he_uniform(fan_in: usize, fan_out: usize, rng: &mut u64) -> Matrix {
        let limit = (6.0 / fan_in as f64).sqrt();
        let mut m = Matrix::zeros(fan_in, fan_out);
        for i in 0..fan_in * fan_out {
            *rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
            let u = (*rng as f64) / (u64::MAX as f64);
            m.data[i] = -limit + 2.0 * limit * u;
        }
        m
    }

    pub fn zero_bias(rows: usize, cols: usize) -> Matrix {
        Matrix::filled(rows, cols, 0.0)
    }
}

// =============================================================================
// MLP struct — Complete Multi-Layer Perceptron
// =============================================================================

struct MLP {
    layer_sizes: Vec<usize>,
    num_layers: usize,
    weights: Vec<Matrix>,
    biases: Vec<Matrix>,
    activations: Vec<Matrix>,
    pre_activations: Vec<Matrix>,
    activation_type: activation::ActivationType,
    learning_rate: f64,
    rng_state: u64,
}

impl MLP {
    fn new(
        sizes: &[usize],
        activation_type: activation::ActivationType,
        learning_rate: f64,
        seed: u64,
    ) -> Self {
        let num_layers = sizes.len() - 1;
        let mut weights = Vec::with_capacity(num_layers);
        let mut biases = Vec::with_capacity(num_layers);
        let mut rng = seed;

        for l in 0..num_layers {
            let fan_in = sizes[l];
            let fan_out = sizes[l + 1];

            let w = match activation_type {
                activation::ActivationType::Relu => {
                    init::he_uniform(fan_in, fan_out, &mut rng)
                }
                _ => init::xavier_uniform(fan_in, fan_out, &mut rng),
            };

            weights.push(w);
            biases.push(init::zero_bias(1, fan_out));
        }

        MLP {
            layer_sizes: sizes.to_vec(),
            num_layers,
            weights,
            biases,
            activations: Vec::with_capacity(num_layers + 1),
            pre_activations: Vec::with_capacity(num_layers),
            activation_type,
            learning_rate,
            rng_state: seed,
        }
    }

    fn forward(&mut self, input: &Matrix) -> Matrix {
        self.activations.clear();
        self.pre_activations.clear();

        self.activations.push(input.clone());

        for l in 0..self.num_layers {
            // z[l] = a[l-1] * W[l] + b[l]
            let z = self.activations[l]
                .matmul(&self.weights[l])
                .add_bias(&self.biases[l]);
            self.pre_activations.push(z.clone());

            // a[l] = activation(z[l])
            // Output layer uses sigmoid
            let a = if l == self.num_layers - 1 {
                z.apply(activation::sigmoid)
            } else {
                activation::apply(&z, self.activation_type)
            };

            self.activations.push(a);
        }

        self.activations[self.num_layers].clone()
    }

    fn compute_loss(&self, predicted: &Matrix, target: &Matrix) -> f64 {
        loss::binary_cross_entropy(predicted, target)
    }

    fn backward(&mut self, target: &Matrix) {
        let m = target.rows as f64;

        // Output layer gradient
        // For BCE + sigmoid: delta = a[L] - y
        let mut delta = self.activations[self.num_layers].clone();
        for i in 0..delta.data.len() {
            delta.data[i] -= target.data[i];
        }

        // Backpropagate through layers
        for l in (0..self.num_layers).rev() {
            // Compute gradients for weights and biases
            // dW[l] = a[l-1]^T * delta
            let dw = self.activations[l].transpose().matmul(&delta);

            // db[l] = sum(delta, axis=0)
            let mut db = Matrix::zeros(1, delta.cols);
            for i in 0..delta.rows {
                for j in 0..delta.cols {
                    *db.at_mut(0, j) += delta.at(i, j);
                }
            }

            // Update weights and biases (gradient descent)
            for i in 0..self.weights[l].data.len() {
                self.weights[l].data[i] -= self.learning_rate * dw.data[i] / m;
            }
            for j in 0..self.biases[l].cols {
                *self.biases[l].at_mut(0, j) -= self.learning_rate * db.at(0, j) / m;
            }

            // Propagate delta to previous layer
            if l > 0 {
                let d_act = activation::apply_derivative(
                    &self.pre_activations[l - 1],
                    self.activation_type,
                );
                delta = delta.matmul(&self.weights[l].transpose());
                for i in 0..delta.data.len() {
                    delta.data[i] *= d_act.data[i];
                }
            }
        }
    }

    fn train(&mut self, x: &Matrix, y: &Matrix, epochs: usize, verbose: bool) {
        for epoch in 0..epochs {
            let output = self.forward(x);
            let loss_val = self.compute_loss(&output, y);
            self.backward(y);

            if verbose && (epoch % (epochs / 10).max(1) == 0 || epoch == epochs - 1) {
                println!("Epoch {}/{} - Loss: {:.6}", epoch, epochs, loss_val);
            }
        }
    }

    fn predict(&mut self, input: &Matrix) -> Matrix {
        self.forward(input)
    }

    fn summary(&self) {
        println!("=== MLP Network Summary (Rust) ===");
        println!("Layers: {} weight layers", self.num_layers);
        print!("Architecture: ");
        for (i, &size) in self.layer_sizes.iter().enumerate() {
            print!("{}", size);
            if i < self.layer_sizes.len() - 1 {
                print!(" -> ");
            }
        }
        println!();

        let total_params: usize = self.weights.iter().map(|w| w.data.len()).sum()
            + self.biases.iter().map(|b| b.data.len()).sum();
        println!("Total parameters: {}", total_params);
        println!("==================================\n");
    }
}

// =============================================================================
// Helper function to create Matrix from 2D vector
// =============================================================================

fn from_vec(data: &[Vec<f64>]) -> Matrix {
    let rows = data.len();
    let cols = data[0].len();
    let mut m = Matrix::zeros(rows, cols);
    for i in 0..rows {
        for j in 0..cols {
            *m.at_mut(i, j) = data[i][j];
        }
    }
    m
}

// =============================================================================
// Test Case 1: XOR Problem
// =============================================================================

fn test_xor() {
    println!("========== Test 1: XOR Problem (Rust) ==========");

    let x = from_vec(&[
        vec![0.0, 0.0],
        vec![0.0, 1.0],
        vec![1.0, 0.0],
        vec![1.0, 1.0],
    ]);
    let y = from_vec(&[vec![0.0], vec![1.0], vec![1.0], vec![0.0]]);

    let mut mlp = MLP::new(&[2, 8, 1], activation::ActivationType::Sigmoid, 5.0, 42);
    mlp.summary();
    mlp.train(&x, &y, 5000, true);

    let predictions = mlp.predict(&x);
    println!("\nXOR Predictions:");
    let mut all_correct = true;
    for i in 0..predictions.rows {
        let pred = if predictions.at(i, 0) > 0.5 { 1 } else { 0 };
        let target = y.at(i, 0) as i32;
        println!("  Sample {}: Predicted={}, Target={}", i, pred, target);
        if pred != target {
            all_correct = false;
        }
    }
    println!(
        "XOR Test: {}",
        if all_correct { "PASSED" } else { "FAILED" }
    );
    println!();
}

// =============================================================================
// Test Case 2: Non-linear classification
// =============================================================================

fn test_nonlinear() {
    println!("========== Test 2: Non-Linear Classification (Rust) ==========");

    // Generate concentric circles
    let mut x_data = Vec::new();
    let mut y_data = Vec::new();
    let mut rng: u64 = 123;

    // Inner circle (class 0)
    for i in 0..50 {
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        let angle = (rng as f64 / u64::MAX as f64) * 2.0 * std::f64::consts::PI;
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        let r = (rng as f64 / u64::MAX as f64) * 0.8;
        x_data.push(vec![r * angle.cos(), r * angle.sin()]);
        y_data.push(vec![0.0]);
    }

    // Outer circle (class 1)
    for i in 0..50 {
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        let angle = (rng as f64 / u64::MAX as f64) * 2.0 * std::f64::consts::PI;
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        let r = 1.5 + (rng as f64 / u64::MAX as f64) * 1.0;
        x_data.push(vec![r * angle.cos(), r * angle.sin()]);
        y_data.push(vec![1.0]);
    }

    let x = from_vec(&x_data);
    let y = from_vec(&y_data);

    let mut mlp = MLP::new(
        &[2, 16, 16, 1],
        activation::ActivationType::Sigmoid,
        1.0,
        42,
    );
    mlp.summary();
    mlp.train(&x, &y, 3000, true);

    let predictions = mlp.predict(&x);
    let mut correct = 0;
    for i in 0..predictions.rows {
        let pred = if predictions.at(i, 0) > 0.5 { 1.0 } else { 0.0 };
        if (pred - y.at(i, 0)).abs() < 0.5 {
            correct += 1;
        }
    }
    let accuracy = correct as f64 / predictions.rows as f64;
    println!("\nAccuracy: {:.1}%", accuracy * 100.0);
    println!(
        "Non-Linear Test: {}",
        if accuracy > 0.85 {
            "PASSED"
        } else {
            "NEEDS MORE TRAINING"
        }
    );
    println!();
}

// =============================================================================
// Test Case 3: AND gate
// =============================================================================

fn test_and() {
    println!("========== Test 3: AND Gate (Rust) ==========");

    let x = from_vec(&[
        vec![0.0, 0.0],
        vec![0.0, 1.0],
        vec![1.0, 0.0],
        vec![1.0, 1.0],
    ]);
    let y = from_vec(&[vec![0.0], vec![0.0], vec![0.0], vec![1.0]]);

    let mut mlp = MLP::new(&[2, 4, 1], activation::ActivationType::Sigmoid, 5.0, 42);
    mlp.summary();
    mlp.train(&x, &y, 2000, true);

    let predictions = mlp.predict(&x);
    let mut all_correct = true;
    for i in 0..predictions.rows {
        let pred = if predictions.at(i, 0) > 0.5 { 1 } else { 0 };
        let target = y.at(i, 0) as i32;
        println!("  Sample {}: Predicted={}, Target={}", i, pred, target);
        if pred != target {
            all_correct = false;
        }
    }
    println!(
        "AND Test: {}",
        if all_correct { "PASSED" } else { "FAILED" }
    );
    println!();
}

// =============================================================================
// Main — Run all tests
// =============================================================================

fn main() {
    println!("============================================");
    println!("  MLP Implementation Test Suite (Rust)");
    println!("============================================\n");

    test_xor();
    test_nonlinear();
    test_and();

    println!("============================================");
    println!("  All tests completed.");
    println!("============================================");
}
```

### 9.3 Funcoes Auxiliares Adicionais

A implementacao Rust inclui varias funcoes auxiliares que tornam o codigo mais idiomático e seguro:

A funcao from_vec() converte um vetor de vetores para uma Matrix. Diferente do C++, Rust exige que o tipo de retorno seja explicito, e a funcao verifica as dimensoes usando asserts.

A funcao summary() imprime um resumo da rede, incluindo o numero total de parametros. Em Rust, o operador format!() e usado para construir strings de forma segura, sem os riscos de buffer overflow da funcao printf em C.

O gerador de numeros aleatorios e implementado com um LCG (Linear Congruential Generator) simples. O LCG e um algoritmo clasico de geracao de numeros pseudo-aleatorios que usa uma recorrencia linear: X_{n+1} = (a * X_n + c) mod m. Para uso em producao, recomenda-se a crate rand, que fornece geradores de alta qualidade como Mersenne Twister.

### 9.4 Compilacao e Execucao

Para compilar com rustc diretamente:

```bash
rustc -O mlp.rs -o mlp_rust
./mlp_rust
```

Ou com Cargo (recomendado para projetos maiores):

```bash
cargo new mlp_project --bin
# Copie o conteudo de mlp.rs para src/main.rs
cargo run --release
```

O flag --release ativa otimizacoes do compilador, reduzindo o tempo de treinamento significativamente. Sem ele, o treinamento pode ser 10x mais lento.

### 9.5 Analise do Codigo Rust

A implementacao Rust segue a mesma estrutura logica do C++, com adaptacoes idiomáticas:

- O compilador Rust exige que todas as dimensoes de matrizes sejam verificadas. A funcao matmul() inclui asserts que verificam a compatibilidade de dimensoes em tempo de execucao.

- Rust nao permite acesso mutavel a dados enquanto outros acessos existem. Isso e gerenciado pelo sistema de ownership — a funcao forward() toma ownership temporario dos dados e retorna resultados sem conflitos.

- O gerador de numeros aleatorios e implementado com um LCG simples (Linear Congruential Generator) para evitar dependencias externas. Para uso em producao, recomenda-se a crate rand.

- A enum ActivationType permite que o tipo de ativacao seja decidido em tempo de compilacao, evitando dispatch dinamico durante o treinamento.

---

## 10. Implementacao em Fortran

Nesta secao, implementamos a MLP em Fortran 2008/2018, aproveitando arrays multidimensionais nativos e subrotinas para operacoes matriciais. Fortran continua sendo amplamente usado em computacao cientifica e de alto desempenho.

### 10.1 Fortran para Redes Neurais

Fortran possui vantagens historicas para computacao numerica:

Arrays multidimensionais: Fortran suporta arrays com ate 15 dimensoes nativamente, com indices arbitrarios (nao necessariamente comecando em 0).

Desempenho numerico: Compiladores Fortran sao otimizados para operacoes com arrays, incluindo auto-vectorizacao e parallelizacao.

Alocacao de memoria: Fortran suporta tanto alocacao estatica quanto dinamica, com arrays allocatable que sao gerenciados pelo runtime.

Subrotinas e funcoes: A separacao entre subrotinas (sem return) e funcoes (com return) facilita a organizacao do codigo.

### 10.2 Codigo Completo

```fortran
! =============================================================================
! mlp.f90 — Multi-Layer Perceptron implemented from scratch in Fortran
! No external libraries — pure Fortran 2008/2018 implementation
! Includes: Matrix operations, Activation functions, Loss functions,
!           Forward propagation, Backpropagation, Weight initialization
! =============================================================================

program mlp_main
    use mlp_module
    implicit none

    print *, "============================================"
    print *, "  MLP Implementation Test Suite (Fortran)"
    print *, "============================================"
    print *

    call test_xor()
    call test_and_gate()
    call test_nonlinear_classification()

    print *, "============================================"
    print *, "  All tests completed."
    print *, "============================================"

contains

    ! =========================================================================
    ! Test Case 1: XOR Problem
    ! =========================================================================

    subroutine test_xor()
        implicit none
        type(mlp_network) :: net
        real(8), dimension(4, 2) :: X
        real(8), dimension(4, 1) :: y
        real(8), dimension(4, 1) :: predictions
        integer :: i, correct
        real(8) :: loss

        print *, "========== Test 1: XOR Problem (Fortran) =========="

        ! XOR training data
        X(1, :) = (/ 0.0d0, 0.0d0 /)
        X(2, :) = (/ 0.0d0, 1.0d0 /)
        X(3, :) = (/ 1.0d0, 0.0d0 /)
        X(4, :) = (/ 1.0d0, 1.0d0 /)

        y(1, 1) = 0.0d0
        y(2, 1) = 1.0d0
        y(3, 1) = 1.0d0
        y(4, 1) = 0.0d0

        ! Initialize MLP: 2 inputs -> 8 hidden -> 1 output
        call mlp_init(net, (/ 2, 8, 1 /), 5.0d0, 42)
        call mlp_summary(net)

        ! Train
        call mlp_train(net, X, y, 5000)

        ! Test predictions
        call mlp_forward(net, X, predictions)

        print *, "XOR Predictions:"
        correct = 0
        do i = 1, 4
            if (predictions(i, 1) > 0.5d0) then
                print *, "  Sample", i, ": Predicted=1, Target=", int(y(i, 1))
                if (int(y(i, 1)) == 1) correct = correct + 1
            else
                print *, "  Sample", i, ": Predicted=0, Target=", int(y(i, 1))
                if (int(y(i, 1)) == 0) correct = correct + 1
            end if
        end do

        if (correct == 4) then
            print *, "XOR Test: PASSED"
        else
            print *, "XOR Test: FAILED"
        end if
        print *
    end subroutine test_xor

    ! =========================================================================
    ! Test Case 2: AND Gate
    ! =========================================================================

    subroutine test_and_gate()
        implicit none
        type(mlp_network) :: net
        real(8), dimension(4, 2) :: X
        real(8), dimension(4, 1) :: y
        real(8), dimension(4, 1) :: predictions
        integer :: i, correct

        print *, "========== Test 2: AND Gate (Fortran) =========="

        X(1, :) = (/ 0.0d0, 0.0d0 /)
        X(2, :) = (/ 0.0d0, 1.0d0 /)
        X(3, :) = (/ 1.0d0, 0.0d0 /)
        X(4, :) = (/ 1.0d0, 1.0d0 /)

        y(1, 1) = 0.0d0
        y(2, 1) = 0.0d0
        y(3, 1) = 0.0d0
        y(4, 1) = 1.0d0

        call mlp_init(net, (/ 2, 4, 1 /), 5.0d0, 42)
        call mlp_summary(net)

        call mlp_train(net, X, y, 2000)

        call mlp_forward(net, X, predictions)

        print *, "AND Predictions:"
        correct = 0
        do i = 1, 4
            if (predictions(i, 1) > 0.5d0) then
                print *, "  Sample", i, ": Predicted=1, Target=", int(y(i, 1))
                if (int(y(i, 1)) == 1) correct = correct + 1
            else
                print *, "  Sample", i, ": Predicted=0, Target=", int(y(i, 1))
                if (int(y(i, 1)) == 0) correct = correct + 1
            end if
        end do

        if (correct == 4) then
            print *, "AND Test: PASSED"
        else
            print *, "AND Test: FAILED"
        end if
        print *
    end subroutine test_and_gate

    ! =========================================================================
    ! Test Case 3: Non-Linear Classification (Concentric Circles)
    ! =========================================================================

    subroutine test_nonlinear_classification()
        implicit none
        type(mlp_network) :: net
        real(8), dimension(50, 2) :: X
        real(8), dimension(50, 1) :: y
        real(8), dimension(50, 1) :: predictions
        integer :: i, correct
        real(8) :: angle, r, accuracy
        real(8) :: pi, noise_val
        integer(8) :: seed

        print *, "========== Test 3: Non-Linear Classification (Fortran) =========="

        pi = 4.0d0 * atan(1.0d0)
        seed = 123

        ! Generate inner circle (class 0) — first 25 samples
        do i = 1, 25
            call pseudo_random(seed, angle)
            angle = angle * 2.0d0 * pi
            call pseudo_random(seed, r)
            r = r * 0.8d0
            call pseudo_random(seed, noise_val)
            noise_val = (noise_val - 0.5d0) * 0.2d0
            X(i, 1) = r * cos(angle) + noise_val
            call pseudo_random(seed, noise_val)
            noise_val = (noise_val - 0.5d0) * 0.2d0
            X(i, 2) = r * sin(angle) + noise_val
            y(i, 1) = 0.0d0
        end do

        ! Generate outer circle (class 1) — last 25 samples
        do i = 26, 50
            call pseudo_random(seed, angle)
            angle = angle * 2.0d0 * pi
            call pseudo_random(seed, r)
            r = 1.5d0 + r * 1.0d0
            call pseudo_random(seed, noise_val)
            noise_val = (noise_val - 0.5d0) * 0.2d0
            X(i, 1) = r * cos(angle) + noise_val
            call pseudo_random(seed, noise_val)
            noise_val = (noise_val - 0.5d0) * 0.2d0
            X(i, 2) = r * sin(angle) + noise_val
            y(i, 1) = 1.0d0
        end do

        ! Initialize MLP: 2 inputs -> 16 hidden -> 16 hidden -> 1 output
        call mlp_init(net, (/ 2, 16, 16, 1 /), 1.0d0, 42)
        call mlp_summary(net)

        call mlp_train(net, X, y, 3000)

        call mlp_forward(net, X, predictions)

        ! Calculate accuracy
        correct = 0
        do i = 1, 50
            if ((predictions(i, 1) > 0.5d0 .and. y(i, 1) > 0.5d0) .or. &
                (predictions(i, 1) <= 0.5d0 .and. y(i, 1) <= 0.5d0)) then
                correct = correct + 1
            end if
        end do

        accuracy = dble(correct) / 50.0d0 * 100.0d0
        print *, "Accuracy:", accuracy, "%"

        if (accuracy > 80.0d0) then
            print *, "Non-Linear Classification Test: PASSED"
        else
            print *, "Non-Linear Classification Test: NEEDS MORE TRAINING"
        end if
        print *
    end subroutine test_nonlinear_classification

end program mlp_main

! =============================================================================
! MLP Module — Core implementation
! =============================================================================

module mlp_module
    implicit none

    ! Maximum number of layers supported
    integer, parameter :: MAX_LAYERS = 10

    ! Data type for MLP network
    type :: mlp_network
        integer :: num_layers
        integer :: layer_sizes(MAX_LAYERS)
        real(8) :: learning_rate

        ! Weights and biases for each layer
        real(8), allocatable :: weights(:, :, :)  ! (layer, from, to)
        real(8), allocatable :: biases(:, :)      ! (layer, to)

        ! Cache for backpropagation
        real(8), allocatable :: activations(:, :)     ! (layer, neuron)
        real(8), allocatable :: pre_activations(:, :) ! (layer, neuron)
    end type mlp_network

contains

    ! =========================================================================
    ! Initialize MLP network
    ! =========================================================================

    subroutine mlp_init(net, sizes, lr, seed)
        type(mlp_network), intent(inout) :: net
        integer, intent(in) :: sizes(:)
        real(8), intent(in) :: lr
        integer, intent(in) :: seed

        integer :: l, fan_in, fan_out
        integer(8) :: rng

        net%num_layers = size(sizes) - 1
        net%layer_sizes(1:net%num_layers + 1) = sizes
        net%learning_rate = lr
        rng = int(seed, 8)

        ! Allocate weights and biases
        allocate(net%weights(net%num_layers, maxval(sizes), maxval(sizes)))
        allocate(net%biases(net%num_layers, maxval(sizes)))

        ! Initialize with Xavier uniform
        do l = 1, net%num_layers
            fan_in = sizes(l)
            fan_out = sizes(l + 1)
            call init_xavier_uniform(net%weights(l, :, :), fan_in, fan_out, rng)
            net%biases(l, :) = 0.0d0
        end do

        ! Allocate cache
        allocate(net%activations(net%num_layers + 1, maxval(sizes)))
        allocate(net%pre_activations(net%num_layers, maxval(sizes)))
    end subroutine mlp_init

    ! =========================================================================
    ! Xavier uniform initialization
    ! =========================================================================

    subroutine init_xavier_uniform(weights, fan_in, fan_out, rng)
        real(8), intent(out) :: weights(:, :)
        integer, intent(in) :: fan_in, fan_out
        integer(8), intent(inout) :: rng

        real(8) :: limit, rand_val
        integer :: i, j

        limit = sqrt(6.0d0 / dble(fan_in + fan_out))

        do i = 1, fan_in
            do j = 1, fan_out
                call pseudo_random(rng, rand_val)
                weights(i, j) = -limit + 2.0d0 * limit * rand_val
            end do
        end do
    end subroutine init_xavier_uniform

    ! =========================================================================
    ! Pseudo-random number generator (LCG)
    ! =========================================================================

    subroutine pseudo_random(rng, value)
        integer(8), intent(inout) :: rng
        real(8), intent(out) :: value

        rng = mod(rng * 6364136223846793005_8 + 1_8, 2_8**63)
        value = dble(rng) / dble(2_8**63)
    end subroutine pseudo_random

    ! =========================================================================
    ! Sigmoid activation function
    ! =========================================================================

    pure function sigmoid(z) result(s)
        real(8), intent(in) :: z
        real(8) :: s
        s = 1.0d0 / (1.0d0 + exp(-z))
    end function sigmoid

    ! =========================================================================
    ! Forward propagation
    ! =========================================================================

    subroutine mlp_forward(net, input, output)
        type(mlp_network), intent(inout) :: net
        real(8), intent(in) :: input(:, :)
        real(8), intent(out) :: output(:, :)

        integer :: l, n_samples, i, j, k, fan_in, fan_out
        real(8) :: sum_val

        n_samples = size(input, 1)

        ! Input layer activations
        net%activations(1, :) = 0.0d0
        do i = 1, n_samples
            fan_in = net%layer_sizes(1)
            net%activations(1, 1:fan_in) = input(i, :)
        end do

        ! Forward through each layer
        do l = 1, net%num_layers
            fan_in = net%layer_sizes(l)
            fan_out = net%layer_sizes(l + 1)

            do i = 1, n_samples
                do j = 1, fan_out
                    ! Compute z = W * a + b
                    sum_val = net%biases(l, j)
                    do k = 1, fan_in
                        sum_val = sum_val + input(i, k) * net%weights(l, k, j)
                    end do
                    net%pre_activations(l, j) = sum_val

                    ! Apply sigmoid activation
                    net%activations(l + 1, j) = sigmoid(sum_val)
                end do
            end do
        end do

        ! Copy output
        fan_out = net%layer_sizes(net%num_layers + 1)
        do i = 1, n_samples
            output(i, 1:fan_out) = net%activations(net%num_layers + 1, 1:fan_out)
        end do
    end subroutine mlp_forward

    ! =========================================================================
    ! Compute MSE loss
    ! =========================================================================

    function mlp_compute_loss(predicted, target) result(loss)
        real(8), intent(in) :: predicted(:, :)
        real(8), intent(in) :: target(:, :)
        real(8) :: loss

        integer :: n, i
        real(8) :: diff

        n = size(predicted, 1) * size(predicted, 2)
        loss = 0.0d0

        do i = 1, size(predicted, 1)
            diff = predicted(i, 1) - target(i, 1)
            loss = loss + diff * diff
        end do

        loss = loss / dble(n)
    end function mlp_compute_loss

    ! =========================================================================
    ! Training loop with backpropagation
    ! =========================================================================

    subroutine mlp_train(net, X, y, epochs)
        type(mlp_network), intent(inout) :: net
        real(8), intent(in) :: X(:, :)
        real(8), intent(in) :: y(:, :)
        integer, intent(in) :: epochs

        integer :: epoch, l, i, j, k
        integer :: n_samples, fan_in, fan_out
        real(8) :: loss, delta, grad
        real(8) :: sum_val
        real(8), allocatable :: output(:, :)
        real(8), allocatable :: delta_out(:)
        real(8), allocatable :: delta_hidden(:, :)
        real(8), allocatable :: d_weights(:, :)
        real(8), allocatable :: d_biases(:)
        real(8), allocatable :: prev_delta(:)

        n_samples = size(X, 1)

        allocate(output(n_samples, 1))
        allocate(delta_out(n_samples))
        allocate(delta_hidden(MAX_LAYERS, maxval(net%layer_sizes)))
        allocate(d_weights(maxval(net%layer_sizes), maxval(net%layer_sizes)))
        allocate(d_biases(maxval(net%layer_sizes)))
        allocate(prev_delta(maxval(net%layer_sizes)))

        do epoch = 0, epochs - 1
            ! Forward pass
            call mlp_forward(net, X, output)

            ! Compute loss
            loss = mlp_compute_loss(output, y)

            ! Output layer delta: (predicted - target) for MSE
            do i = 1, n_samples
                delta_out(i) = 2.0d0 * (output(i, 1) - y(i, 1)) / dble(n_samples)
            end do

            ! Backpropagation
            ! Start from output layer
            fan_out = net%layer_sizes(net%num_layers + 1)
            do i = 1, n_samples
                delta_hidden(net%num_layers, i) = delta_out(i)
            end do

            ! Update output layer weights
            l = net%num_layers
            fan_in = net%layer_sizes(l)
            fan_out = net%layer_sizes(l + 1)

            do j = 1, fan_out
                do k = 1, fan_in
                    grad = 0.0d0
                    do i = 1, n_samples
                        grad = grad + net%activations(l, k) * delta_hidden(l, i)
                    end do
                    net%weights(l, k, j) = net%weights(l, k, j) - &
                        net%learning_rate * grad / dble(n_samples)
                end do
            end do

            ! Update output layer biases
            do j = 1, fan_out
                grad = 0.0d0
                do i = 1, n_samples
                    grad = grad + delta_hidden(l, i)
                end do
                net%biases(l, j) = net%biases(l, j) - &
                    net%learning_rate * grad / dble(n_samples)
            end do

            ! Propagate to hidden layers (simplified backprop)
            do l = net%num_layers - 1, 1, -1
                fan_in = net%layer_sizes(l)
                fan_out = net%layer_sizes(l + 1)

                ! Compute delta for this layer
                do i = 1, n_samples
                    sum_val = 0.0d0
                    do j = 1, net%layer_sizes(l + 2)
                        sum_val = sum_val + net%weights(l + 1, i, j) * &
                            delta_hidden(l + 1, i)
                    end do
                    delta_hidden(l, i) = sum_val * &
                        net%activations(l + 1, i) * (1.0d0 - net%activations(l + 1, i))
                end do

                ! Update weights
                do j = 1, fan_out
                    do k = 1, fan_in
                        grad = 0.0d0
                        do i = 1, n_samples
                            grad = grad + net%activations(l, k) * delta_hidden(l, i)
                        end do
                        net%weights(l, k, j) = net%weights(l, k, j) - &
                            net%learning_rate * grad / dble(n_samples)
                    end do
                end do

                ! Update biases
                do j = 1, fan_out
                    grad = 0.0d0
                    do i = 1, n_samples
                        grad = grad + delta_hidden(l, i)
                    end do
                    net%biases(l, j) = net%biases(l, j) - &
                        net%learning_rate * grad / dble(n_samples)
                end do
            end do

            ! Print progress
            if (mod(epoch, epochs / 10) == 0 .or. epoch == epochs - 1) then
                print *, "Epoch", epoch, "/", epochs, "- Loss:", loss
            end if
        end do

        deallocate(output, delta_out, delta_hidden, d_weights, d_biases, prev_delta)
    end subroutine mlp_train

    ! =========================================================================
    ! Print network summary
    ! =========================================================================

    subroutine mlp_summary(net)
        type(mlp_network), intent(in) :: net

        integer :: l, total_params

        print *, "=== MLP Network Summary (Fortran) ==="
        print *, "Layers:", net%num_layers, "weight layers"

        write(*, '(A)', advance='no') "Architecture: "
        do l = 1, net%num_layers + 1
            write(*, '(I0)', advance='no') net%layer_sizes(l)
            if (l < net%num_layers + 1) write(*, '(A)', advance='no') " -> "
        end do
        print *

        total_params = 0
        do l = 1, net%num_layers
            total_params = total_params + &
                net%layer_sizes(l) * net%layer_sizes(l + 1) + &
                net%layer_sizes(l + 1)
        end do

        print *, "Total parameters:", total_params
        print *, "======================================"
        print *
    end subroutine mlp_summary

end module mlp_module
```

### 10.3 Funcoes Auxiliares Adicionais

A implementacao Fortran inclui varias subrotinas auxiliares importantes:

A subrotina pseudo_random() implementa um gerador de numeros pseudo-aleatorios baseado em LCG (Linear Congruential Generator). Fortran fornece a intrinseca random_number(), mas para reprodutibilidade e controle fino, um LCG proprio e mais confiavel. O LCG usa uma semente inteira de 64 bits e produz valores reais no intervalo [0, 1].

A subrotina mlp_summary() imprime informacoes sobre a arquitetura da rede. Fortran usa formatos de escrita especificos (format statements ou edit descriptors) para controlar a saida. A opcao advance='no' em write() permite escrever na mesma linha, util para formatar a arquitetura da rede de forma compacta.

A subrotina mlp_compute_loss() calcula o erro quadratico medio entre as predicoes e os valores alvo. Fortran permite acesso direto a elementos de arrays com parenteses: array(i, j) acessa o elemento na linha i, coluna j.

### 10.4 Compilacao e Execucao

```bash
gfortran -O2 -o mlp_fortran mlp.f90
./mlp_fortran
```

Para compilar com otimizacoes avancadas:

```bash
gfortran -O3 -march=native -funroll-loops -o mlp_fortran mlp.f90
```

O flag -march=native gera codigo otimizado para a arquitetura do processador local. O flag -funroll-loops desenrola loops curtos, reduzindo overhead de branches.

### 10.5 Analise do Codigo Fortran

A implementacao Fortran adapta o padrao MLP para o estilo idiomático da linguagem:

- Arrays em Fortran usam indices que comecam em 1 (por padrao), diferente de C++ e Rust que comecam em 0. Isso requer atencao ao acessar posicoes de arrays.

- A estrutura mlp_network encapsula todos os dados da rede. Fortran 2008 suporta allocatable components em derived types, permitindo alocacao dinamica de arrays dentro de estruturas.

- O gerador de numeros aleatorios pseudo_random() implementa um LCG para evitar dependencias externas. Compiladores Fortran modernos tambem oferecem intrinsecos como random_number().

- A subrotina mlp_train() implementa retropropagacao simplificada. A implementacao Fortran e mais verbosa que C++ ou Rust devido a ausencia de operacoes matriciais nativas — cada multiplicacao de matriz e implementada explicitamente com loops aninhados.

- Fortran e particularmente eficiente para operacoes com arrays devido a sua estrutura de memoria column-major e otimizacoes do compilador. Para redes grandes, a implementacao Fortran pode ser competitiva com C++ em desempenho bruto.

---

## 11. Exemplo XOR com MLP

Nesta secao, detalhamos como a MLP resolve o problema XOR — o mesmo que paralisou o campo de redes neurais por decadas.

### 11.1 O Problema XOR Revisitado

XOR (exclusive or) retorna 1 quando as entradas sao diferentes, e 0 quando sao iguais. Como demonstramos no capitulo anterior, o Perceptron simples nao consegue resolver esse problema porque nao existe uma linha que separe os dados.

### 11.2 Como a MLP Resolve XOR

Uma rede com 2 entradas, 2 neuronios na camada oculta e 1 neuronio na saida pode resolver XOR. A camada oculta aprende uma representacao intermediaria dos dados que torna o problema linearmente separavel.

Considere uma rede treinada com os seguintes pesos aproximados:

Camada oculta:
- Neuronio 1: pesos [1, 1], bias [-0.5] — ativa quando pelo menos uma entrada e 1
- Neuronio 2: pesos [1, 1], bias [-1.5] — ativa quando ambas as entradas sao 1

Camada de saida:
- Pesos [1, -2], bias [0.5] — combina as ativacoes da camada oculta

Para a entrada (0, 0):
- Neuronio 1: sigmoid(0 + 0 - 0.5) = sigmoid(-0.5) = 0.38
- Neuronio 2: sigmoid(0 + 0 - 1.5) = sigmoid(-1.5) = 0.18
- Saida: sigmoid(0.38 * 1 + 0.18 * (-2) + 0.5) = sigmoid(0.52) = 0.63

A rede produz uma saida proxima de 0.63. Apos mais treinamento, os pesos convergem para valores que produzem saidas mais precisas. Com treinamento suficiente, a rede atinge acuracia de 100% em XOR.

### 11.3 A Representacao Aprendida

A camada oculta divide o espaco de entrada em tres regioes:

Regiao 1 (neuronio 1 ativo, neuronio 2 inativo): pontos onde apenas uma entrada e 1. A saida da rede e proxima de 1.

Regiao 2 (ambos neuronios inativos): o ponto (0, 0). A saida da rede e proxima de 0.

Regiao 3 (ambos neuronios ativos): o ponto (1, 1). A saida da rede e proxima de 0, devido ao peso negativo do neuronio 2.

Essa divisao do espaco de entrada em regioes e o que permite a MLP resolver problemas nao-lineares. Cada camada oculta particiona o espaco de forma diferente, e as particoes se combinam para formar fronteiras complexas.

### 11.4 Curva de Aprendizado

Durante o treinamento de XOR com MLP, a curva de aprendizado tipicamente mostra:

Epocas 0-100: a perda cai rapidamente de ~0.7 para ~0.3. A rede aprende a maioria dos padroes faceis. Os pesos da camada oculta comecam a se diferenciar, quebrando a simetria inicial.

Epocas 100-500: a perda continua caindo, mas mais lentamente. A rede refina os pesos para atingir separacao precisa. Nessa fase, a rede ja classifica corretamente 3 dos 4 padroes, mas ainda erra em um.

Epocas 500-2000: a perda atinge ~0.01 ou menor. Todos os padroes sao classificados corretamente. A rede convergiu para uma solucao.

Epocas 2000+: a perda continua diminuindo lentamente, mas a acuracia nao muda. A rede esta ajustando os pesos para aumentar a margem de separacao.

### 11.5 Sensibilidade a Inicializacao

Um ponto importante sobre XOR e que a solucao e sensivel a inicializacao dos pesos. Se todos os pesos da camada oculta sao muito proximos entre si, a rede pode ficar presa em um ponto de sela onde os dois neuronios da camada oculta aprendem a mesma coisa.

Para evitar isso, a inicializacao deve ser suficientemente aleatoria para quebrar a simetria. A inicializacao de Xavier, discutida na secao 7, e adequada para esse proposito. Com Xavier, os pesos sao distribuidos em um intervalo que depende do numero de neuronios de entrada e saida, garantindo diversidade inicial suficiente.

A taxa de aprendizado tambem e critica. Valores muito grandes (> 10) podem causar oscilacoes na perda, impedindo a convergencia. Valores muito pequenos (< 0.01) tornam o treinamento extremamente lento. Para XOR, taxas entre 1.0 e 10.0 funcionam bem com sigmoid.

---

## 12. Exemplo Classificacao de Dados Nao-Lineares

Para demonstrar a capacidade da MLP em resolver problemas reais, implementamos a classificacao de dois conjuntos de dados nao-linearmente separaveis.

### 12.1 Dataset: Circulos Concentricos

O primeiro dataset consiste em dois circulos concentricos: um circulo menor (raio 0 a 0.8) no centro, classificado como classe 0; e um anel ao redor (raio 1.5 a 2.5), classificado como classe 1. Ruido gaussiano e adicionado para tornar o problema mais realista.

Esse dataset e impossivel de resolver com uma unica camada (Perceptron), mas uma MLP com duas camadas ocultas (16 neuronios cada) resolve com acuracia superior a 90%.

### 12.2 Dataset: Lua e Meia-Lua

O segundo dataset consiste em dois formatos de lua: uma lua cheia (classe 0) e uma meia-lua (classe 1). Esse dataset e mais challenging porque as fronteiras sao altamente nao-lineares e irregulares.

Para resolver esse dataset, uma MLP com tres camadas ocultas (32, 32 e 16 neuronios) e necessaria. A rede precisa aprender representacoes mais complexas para capturar a curvatura das fronteiras.

### 12.3 Analise dos Resultados

Apos o treinamento, podemos visualizar a fronteira de decisao da rede. Para cada ponto em uma grade 2D, a rede classifica o ponto como classe 0 ou 1. A fronteira de decisao formada e curva e se ajusta aos dados de treinamento.

Pontos na regiao central (dentro do circulo menor) sao classificados como classe 0. Pontos na regiao externa (fora do circulo maior) sao classificados como classe 1. A fronteira de decisao e aproximadamente circular, consistente com a geometria dos dados.

### 12.4 Metricas de Avaliacao

Para avaliar a qualidade da classificacao, usamos quatro metricas fundamentais:

Acuracia: proporcao de exemplos classificados corretamente. E a metrica mais intuitiva, mas pode ser enganosa em datasets desbalanceados. Se 95% dos dados sao classe 0, um classificador trivial que sempre prediz classe 0 atinge 95% de acuracia sem aprender nada.

Precisao: proporcao de exemplos classificados como classe 1 que realmente sao classe 1. Essa metrica e importante quando o custo de falso positivo e alto — por exemplo, em diagnosticos medicos, classificar um paciente sao como doente e menos grave que classificar um doente como sao.

Recall: proporcao de exemplos que sao realmente classe 1 e foram classificados como classe 1. E importante quando o custo de falso negativo e alto — por exemplo, em deteccao de fraudes, perder uma fraude e mais grave que investigar uma transacao legitima.

F1-Score: media harmonica de precisao e recall. Balanceia as duas metricas em um unico numero. Quando precisao e recall sao altos, F1-Score tambem e alto. Quando um deles e baixo, F1-Score e baixo. E a metrica preferida para datasets desbalanceados.

Para datasets balanceados (mesmo numero de exemplos por classe), a acuracia e uma metrica adequada. Para datasets desbalanceados, F1-Score e mais informativo.

### 12.5 Matriz de Confusao

A matriz de confusao e uma tabela que mostra a distribuicao das predicoes em quatro categorias:

Verdadeiro Positivo (TP): exemplos positivos corretamente classificados como positivos.
Verdadeiro Negativo (TN): exemplos negativos corretamente classificados como negativos.
Falso Positivo (FP): exemplos negativos incorretamente classificados como positivos (erro tipo I).
Falso Negativo (FN): exemplos positivos incorretamente classificados como negativos (erro tipo II).

A partir da matriz de confusao, todas as metricas podem ser calculadas: acuracia = (TP + TN) / (TP + TN + FP + FN), precisao = TP / (TP + FP), recall = TP / (TP + FN), F1 = 2 * precisao * recall / (precisao + recall).

### 12.6 Limitacoes da MLP

Embora a MLP seja uma arquitetura poderosa, ela possui limitacoes importantes para dados nao-estruturados:

Para imagens: uma MLP com uma imagem 28x28 como entrada precisaria de 784 neuronios na camada de entrada e milhoes de parametros na primeira camada oculta. Isso e ineficiente eignor a estrutura espacial da imagem. Redes convolucionais (CNNs) resolvem esse problema usando camadas convolucionais que compartilham pesos.

Para sequencias de texto: a MLP nao modela a dependencia temporal entre palavras. Redes recorrentes (RNNs) e transformadores resolvem esse problema usando mecanismos de atencao e memorizacao.

Para dados tabulares: a MLP funciona bem, mas para muitos problemas tabulares, metodos baseados em arvores (Random Forest, XGBoost) frequentemente superam as MLPs com menos ajuste de hiperparametros.

A MLP brilha quando os dados sao vetoriais e as relacoes entre features sao nao-lineares e complexas. Para esse tipo de problema, e a arquitetura basica que todas as outras extendem.

---

## Resumo do Capitulo

Neste capitulo, percorremos o caminho completo do Perceptron simples ate a Multi-Layer Perceptron (MLP). Os conceitos fundamentais aprendidos servem como base para todas as arquiteturas modernas de redes neurais.

### Principais Conceitos

De Perceptron a MLP: O Perceptron so resolve problemas linearmente separaveis. A MLP, com suas camadas ocultas, pode resolver qualquer problema, desde que tenha neuronios e dados suficientes. A transicao e motivada pelo problema XOR, que demonstra a necessidade de transformacoes nao-lineares.

Arquitetura: Uma MLP e composta por camada de entrada (tamanho igual ao numero de features), camadas ocultas (tamanho definido pelo projetista) e camada de saida (tamanho determinado pelo problema). Em uma rede totalmente conectada, cada neuronio se conecta a todos os neuronios da camada seguinte. O numero de parametros cresce multiplicativamente com o tamanho da rede.

Forward Propagation: Os dados fluem da entrada para a saida. Em cada camada, uma transformacao linear (multiplicacao de matriz + bias) e seguida de uma nao-linearidade (funcao de ativacao). Os valores intermediarios sao armazenados para a retropropagacao. O forward pass e rapido e deterministico.

Funcoes de Perda: MSE para regressao e Cross-Entropy para classificacao. A Cross-Entropy, combinada com sigmoid/softmax, produz gradientes limpos que evitam o problema de gradiente que desaparece. A escolha da funcao de perda e determinante para a convergencia do treinamento.

Numero de Camadas e Neuronios: Nao existe resposta universal. Comece com 1-2 camadas ocultas, ajuste com base na validacao. Redes profundas sao mais eficientes que redes rasas largas para problemas complexos. Overfitting e o principal risco de redes grandes demais.

Teorema de Aproximacao Universal: Qualquer funcao continua pode ser aproximada por uma rede neural com uma camada oculta suficientemente grande. Na pratica, profundidade e mais eficiente que largura. O teorema garante existencia, nao eficiencia.

Inicializacao de Pesos: Xavier para sigmoid/tanh, He para ReLU. Inicializar com zero quebra a simetria; valores muito grandes causam gradientes que explora; valores muito pequenos causam gradientes que desaparecem. A inicializacao correta e prerequisito para treinamento bem-sucedido.

### Implementacoes

Implementamos MLP completa em tres linguagens: C++, Rust e Fortran. O padrao de implementacao e identico em todas as linguagens — a logica do algoritmo e a mesma, so muda a sintaxe e as convencoes de cada linguagem. Isso demonstra que a MLP e uma abstracao fundamental, nao dependente de nenhuma linguagem ou biblioteca especifica. As tres implementacoes resolvem os mesmos problemas (XOR, classificacao nao-linear, AND) e produzem resultados equivalentes.

### Proximos Passos

No proximo capitulo, exploraremos o algoritmo de retropropagacao em detalhes. Veremos como os gradientes sao calculados camada a camada, como as regras da cadeia se aplicam, e como implementar a retropropagacao de forma eficiente. Tambem discutiremos variacoes do algoritmo como momentum, RMSprop e Adam, que melhoram significativamente a velocidade e estabilidade do treinamento.

### Exercicios Sugeridos de Revisao

Antes de prosseguir para o proximo capitulo, revise os seguintes conceitos:

1. Escreva a formula matematica do forward pass para uma rede 3-5-2. Quais sao as dimensoes de cada matriz de peso?

2. Desenhe a MLP para XOR (2-2-1). Identifique cada peso e explique fisicamente o que ele representa.

3. Calcule manualmente o valor de sigmoid(0.5) e sigmoid(-2.0). Para que valores de entrada a sigmoid e proxima de 0? De 1?

4. Por que a Cross-Entropy e preferida ao MSE para classificacao? Explaine em termos de gradientes.

5. Qual e a diferenca entre Xavier e He? Para que cada uma deve ser usada?

6. Por que a inicializacao com zero e problematica para uma rede neural? O que acontece com os gradientes?

7. Enuncie o Teorema de Aproximacao Universal em suas proprias palavras. Quais sao suas limitacoes praticas?

8. Por que uma rede profunda e mais eficiente que uma rede rasa larga para o mesmo numero total de neuronios?

---

## Exercicios

Os exercicios a seguir sao projetados para consolidar os conceitos deste capitulo. Comece pelos exercicios mais simples (1-3) e avance para os mais complexos (8-10). Todos os exercicios devem ser implementados do zero, sem usar bibliotecas de machine learning.

1. Implemente uma MLP em qualquer linguagem de programacao que resolva o problema OR (ou inclusivo). Mostre que a rede converge e apresente as predicoes finais para todas as quatro entradas possiveis. Documente os pesos aprendidos pela rede e explique fisicamente o que cada neuronio da camada oculta esta calculando. Considere a geometria do espaco de entrada e como a rede particiona esse espaco.

2. Modifique a implementacao C++ para suportar ativacao ReLU nas camadas ocultas. Compare a velocidade de convergencia com sigmoid para o problema XOR. Discuta por que ReLU pode ser problematico para problemas com entradas binarias (0 ou 1). Analise a saida da rede: quantos neuronios da camada oculta morrem (fiquem sempre zero) com ReLU? Implemente Leaky ReLU e compare os resultados.

3. Implemente uma MLP com tres neuronios na entrada e tres classes na saida (classificacao multi-classe). Use softmax na camada de saida e Cross-Entropy como funcao de perda. Treine com o dataset Iris (disponivel em UCI Machine Learning Repository). Compare a acuracia da sua implementacao com um classificador K-Nearest Neighbors. Discuta as diferencas entre os dois abordagens e as situacoes em que cada uma e preferivel.

4. Crie um dataset de classificacao nao-linear com tres classes (tres circulos concentricos com raios diferentes). Implemente e treine uma MLP para resolver esse problema. Quantas camadas ocultas e neuronios sao necessarios? Plote a fronteira de decisao e analise se ela captura a geometria dos dados. Experimente diferentes arquiteturas e documente os resultados.

5. Implemente o algoritmo de retropropagacao para uma MLP com tres camadas ocultas. Verifique manualmente (com calculadora) o gradiente da primeira camada para uma entrada especifica. Use uma rede 2-3-3-3-1 e a entrada (1, 0). Documente cada passo do calculo, incluindo os valores de z e a para cada camada. Confirme que o resultado computado pela retropropagacao e igual ao gradiente numerico.

6. Compare as inicializacoes Xavier e He para a mesma arquitetura de rede. Meça a acuracia final e o numero de epocas necessarias para convergir. Qual e melhor para sigmoid? Para ReLU? Use o problema XOR como benchmark. Plote as curvas de perda para ambas as inicializacoes e discuta as diferencas observadas.

7. Implemente uma MLP para regressao que aproxime a funcao f(x) = sin(x) + cos(2x). Use uma rede com duas camadas ocultas e tangente hiperbolica como ativacao. Gere 100 pontos de treinamento no intervalo [0, 4*pi] e valide com 50 pontos no mesmo intervalo. Calcule o erro medio absoluto (MAE) no conjunto de teste. Experimente diferentes numeros de neuronios e documente como a complexidade da rede afeta a acuracia.

8. Modifique a implementacao para usar mini-batch gradient descent (tamanho de batch configuravel). Compare o desempenho com batch completo e estocastico (batch size 1) para o problema XOR. Discuta as vantagens e desvantagens de cada abordagem em termos de velocidade de convergencia e estabilidade. Qual tamanho de batch produz os melhores resultados?

9. Implemente early stopping: monitore a perda em um conjunto de validacao e pare o treinamento quando a perda de validacao comecar a subir por N epocas consecutivas (patience). Demonstre que isso reduz overfitting em um dataset com ruido artificial. Compare a acuracia final com e sem early stopping. Experimente diferentes valores de patience.

10. Implemente regularizacao L2 (weight decay) na retropropagacao. Adicione um termo lambda * ||W||^2 a funcao de perda e mostre que isso reduz a magnitude dos pesos treinados. Compare o desempenho com e sem regularizacao para um dataset com ruido. Experimente diferentes valores de lambda (0.001, 0.01, 0.1, 1.0) e discuta o efeito de cada um na acuracia e na magnitude dos pesos.

---

## Referencias

1. Rosenblatt, F. (1958). The Perceptron: A Probabilistic Model for Information Storage and Organization in the Brain. Psychological Review, 65(6), 386-408. O artigo original que introduziu o conceito de neuronio artificial e o algoritmo de treinamento por perceptron.

2. Minsky, M., & Papert, S. A. (1969). Perceptrons: An Introduction to Computational Geometry. MIT Press. A obra que formalizou as limitacoes do Perceptron e praticamente congelou a pesquisa em redes neurais por uma decada.

3. Rumelhart, D. E., Hinton, G. E., & Williams, R. J. (1986). Learning Representations by Back-Propagating Errors. Nature, 323, 533-536. O artigo que popularizou o algoritmo de retropropagacao e revitalizou o campo de redes neurais.

4. Cybenko, G. (1989). Approximation by Superpositions of a Sigmoidal Function. Mathematics of Control, Signals and Systems, 2(4), 303-314. A primeira versao formal do Teorema de Aproximacao Universal para redes neurais com funcao de ativacao sigmoid.

5. Hornik, K. (1991). Approximation Capabilities of Multilayer Feedforward Networks. Neural Networks, 4(2), 251-257. Generalizacao do Teorema de Aproximacao Universal para qualquer funcao de ativacao nao-constante.

6. Glorot, X., & Bengio, Y. (2010). Understanding the Difficulty of Training Deep Feedforward Neural Networks. Proceedings of the 13th International Conference on Artificial Intelligence and Statistics (AISTATS), 249-256. A analise que levou a inicializacao Xavier para resolver o problema de gradientes que desaparecem.

7. He, K., Zhang, X., Ren, S., & Sun, J. (2015). Delving Deep into Rectifiers: Surpassing Human-Level Performance on ImageNet Classification. Proceedings of the IEEE International Conference on Computer Vision (ICCV), 1026-1034. A inicializacao He especificamente projetada para redes com ativacao ReLU.

8. Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press. O livro referencia para deep learning, cobrindo todos os aspectos teoricos e praticos do campo.

9. Bishop, C. M. (2006). Pattern Recognition and Machine Learning. Springer. Um dos livros mais completos sobre machine learning, incluindo tratamento rigoroso de redes neurais.

10. Nielsen, M. A. (2015). Neural Networks and Deep Learning. Determination Press. Disponivel gratuitamente online, este livro oferece uma introducao acessivel a redes neurais com muitos exercicios praticos.

11. Haykin, S. (2008). Neural Networks and Learning Machines. 3rd Edition. Prentice Hall. Um texto abrangente que cobre tanto redes neurais classicas quanto aprendizado de maquina moderno.

12. LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep Learning. Nature, 521(7553), 436-444. Uma visao geral da revolucao de deep learning, escrita por tres dos principais pesquisadores do campo.

13. Werbos, P. J. (1974). Beyond Regression: New Tools for Prediction and Analysis in the Behavioral Sciences. PhD Thesis, Harvard University. A tese que primeiro descreveu o algoritmo de retropropagacao, antecipando em mais de uma decada a sua popularizacao.
