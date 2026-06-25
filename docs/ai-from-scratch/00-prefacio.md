---
layout: default
title: "00-prefacio"
---

# Prefacio — IA do Zero: Implementando Algoritmos de Machine Learning em C++, Fortran e Rust

> *"A melhor forma de entender um algoritmo e implementa-lo do zero."*

---

## Por Que Este Livro Existe

A maioria dos engenheiros usa TensorFlow ou PyTorch como caixas-pretas. Constroem modelos, treinam, deployam — mas nao entendem o que acontece por baixo dos panos. Quando o modelo falha, nao sabem diagnosticar. Quando o hardware e limitado, nao sabem otimizar. Quando a seguranca importa, nao sabem o que esta acontecendo nos bastidores.

Este livro resolve esse problema implementando cada algoritmo de machine learning **do zero**, em tres linguagens de sistema de alto desempenho:

- **C++**: A linguagem dominante em production ML (TensorFlow, PyTorch, XGBoost sao C++)
- **Rust**: Seguranca de memoria sem garbage collector, ideal para ML seguro
- **Fortran**: O pai dos numerical computing — ainda o mais rapido para operacoes matriciais

Nao usamos nenhuma biblioteca de ML. Cada matrix, cada gradiente, cada optimizador e escrito do zero. Isso garante que voce entenda **cada byte** do que esta acontecendo.

---

## Publico-Alvo

- **Engenheiros C++** que querem entender ML em profundidade
- **Cientistas de dados** que querem ir alem de scikit-learn
- **Pesquisadores** que precisam de controle total sobre algoritmos
- **Engenheiros Rust** que constroem ML em producao
- **Estudantes avancados** de computacao e inteligencia artificial

---

## Pre-Requisitos

| Tecnologia | Nivel | Uso no Livro |
|------------|-------|-------------|
| C++ | Intermediario | Linguagem primaria |
| Rust | Basico | Implementacoes seguras |
| Fortran | Nenhum | Introduzido no livro |
| Algebra Linear | Basico | Matrizes, vetores, operacoes |
| Calculo | Basico | Derivadas, gradiente |
| Probabilidade | Basico | Distribuicoes, expectativa |

---

## Estrutura do Livro

### Parte I: Fundamentos (00-03)
- Prefacio, introducao, algebra linear, funcoes de ativacao

### Parte II: Redes Neurais Classicas (04-08)
- Perceptron, MLP, backpropagation, optimizadores, regularizacao

### Parte III: Redes Convolucionais e Recorrentes (09-12)
- CNN, RNN, GRU, LSTM

### Parte IV: Arquiteturas Modernas (13-17)
- Attention, Transformer, GANs, boas praticas, projetos

---

## Convencoes

- **Texto**: Portugues brasileiro (PT-BR)
- **Codigo**: Identificadores em ingles
- **Exemplos**: C++17, Rust 1.70+, Fortran 2018
- **Nenhuma biblioteca de ML**: Tudo implementado do zero

---

*[Proximo capitulo: 01 — Introducao a IA e Machine Learning](01-introducao-ia-ml.md)*
