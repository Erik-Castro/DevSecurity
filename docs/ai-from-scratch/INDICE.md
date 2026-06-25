---
layout: default
title: "INDICE"
---

# IA do Zero: ML em C++, Fortran e Rust — Indice

---

| # | Capitulo | Tema Principal |
|---|----------|----------------|
| 00 | [Prefacio](00-prefacio.md) | Motivacao, linguagens, abordagem |
| 01 | [Introducao a IA e ML](01-introducao-ia-ml.md) | Historia, conceitos, tipos de ML | 2802 |
| 02 | [Algebra Linear para ML](02-algebra-linear.md) | Matrizes, vetores, operacoes, decomposicoes | 2800 |
| 03 | [Funcoes de Ativacao](03-funcoes-ativacao.md) | Sigmoid, ReLU, Softmax, derivadas | 2800 |
| 04 | [Perceptron](04-perceptron.md) | Perceptron simples, classificacao linear | 3293 |
| 05 | [Redes Neurais Multicamadas (MLP)](05-mlp.md) | Arquitetura, forward propagation | 2800 |
| 06 | [Backpropagation](06-backpropagation.md) | Gradiente, cadeia, implementacao | 3015 |
| 07 | [Optimizadores](07-optimizadores.md) | SGD, Adam, AdaGrad, RMSProp | 2895 |
| 08 | [Regularizacao](08-regularizacao.md) | Dropout, L1/L2, early stopping, batch norm | 3109 |
| 09 | [Redes Neurais Convolucionais (CNN)](09-cnn.md) | Convolucao, pooling, arquiteturas | 3634 |
| 10 | [Redes Neurais Recorrentes (RNN)](10-rnn.md) | Vanishing gradient, BPTT | 3226 |
| 11 | [GRU](11-gru.md) | Gated Recurrent Unit, implementacao | 2863 |
| 12 | [LSTM](12-lstm.md) | Long Short-Term Memory, gates | 2803 |
| 13 | [Mecanismo de Attention](13-attention.md) | Self-attention, multi-head | 2878 |
| 14 | [Transformer](14-transformer.md) | Arquitetura completa, positional encoding | 2850 |
| 15 | [Generative Adversarial Networks (GANs)](15-gans.md) | Generator, discriminator, treinamento | 2971 |
| 16 | [Avaliacao e Metricas](16-avaliacao-metricas.md) | Accuracy, F1, ROC, confusion matrix | 3974 |
| 17 | [Projetos e Casos Reais](17-projetos-casos.md) | MNIST, classificacao de imagens, NLP | 3260 |

---

## Dependencias

```
00 -> 01 -> 02 -> 03
                 |
         +-------+-------+
         |       |       |
         04      05      06
         |       |       |
         +---+---+---+---+
             |       |
             07      08
             |       |
         +---+---+---+---+
         |       |       |
         09      10      11
         |       |       |
         +---+---+---+---+
         |       |
         12      13
         |       |
         +---+---+---+
         |       |
         14      15
         |       |
         +---+---+---+
             |
         16 -> 17
```
