---
layout: default
title: "15-gans"
---

# Capitulo 15 — Generative Adversarial Networks (GANs)

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender o que e geracao de dados** — como modelos aprendem a criar dados novos.
2. **Dominar a arquitetura basica de GAN** — generator + discriminator adversariais.
3. **Entender a funcao de perda do GAN** — minimax game e suas implicacoes.
4. **Analisar training dynamics** — como generator e discriminator evoluem juntos.
5. **Identificar e resolver mode collapse** — o problema mais comum em GANs.
6. **Dominar Wasserstein GAN (WGAN)** — loss mais estavel e com propriedades teoricas.
7. **Entender Conditional GAN** — geracao condicionada em labels.
8. **Implementar GAN completo em C++** — generator, discriminator, e training loop.
9. **Implementar GAN em Rust** — com seguranca de memoria.
10. **Implementar GAN em Fortran** — para performance numerica.
11. **Gerar dados sinteticos** — pipeline completo de geracao.
12. **Avaliar GANs** — metricas de qualidade e diversidade.

---

## 1. O Que e Geracao

### 1.1 Aprendizado Generativo

```text
Aprendizado Generativo vs Discriminativo:
============================================

Discriminativo (MLP, CNN, etc):
  - Aprende P(y | x)
  - Dado input x, prediz label y
  - Exemplo: "essa imagem e um gato?" -> sim/nao

Generativo (GANs, VAEs, etc):
  - Aprende P(x) ou P(x | z)
  - Aprende a DISTRIBUICAO dos dados
  - Gera dados NOVOS amostrados dessa distribuicao
  - Exemplo: "gere uma imagem de gato" -> imagem nova

Diferenca fundamental:
  - Discriminativo: classifica dados existentes
  - Generativo: cria dados novos
```

### 1.2 Por Que Gerar Dados

```text
Aplicacoes de Geracao:
=======================

1. Data Augmentation:
   - Dados limitados? Gere mais
   - Medicos: gerar radiografias sinteticas
   - Robótica: gerar cenarios de treinamento

2. Arte e Criatividade:
   - Gerar pinturas, musicas, textos
   - Ferramentas criativas para artistas

3. Simulacao:
   - Gerar cenarios realistas
   - Testes autonomos (carros)
   - Simulacao de fisica

4. Anonimizacao:
   - Gerar dados sinteticos que preservam estatisticas
   - Privacidade de dados sensiveis

5. Super-Resolution:
   - Melhorar resolucao de imagens
   - Deblur, inpainting

6. Traducao:
   - Image-to-image translation
   - Estilo, dominio
```

### 1.3 Abordagens de Geracao

```text
Abordagens Generativas:
========================

1. GANs (Generative Adversarial Networks):
   - Generator vs Discriminator
   - Treinamento adversarial
   - Alta qualidade, instavel

2. VAEs (Variational Autoencoders):
   - Encoder-Decoder com latent space
   - Treinamento por maximum likelihood
   - Mais estavel, menos nitido

3. Flows:
   - Transformacoes invertiveis
   - Density estimation exata
   - Flexivel mas caro

4. Diffusion Models:
   - Ruido gradual
   - Melhor qualidade atual
   - Lento para amostrar

5. Autoregressive:
   - Pixel-by-pixel (ou token-by-token)
   - GPT, WaveNet
   - Lento mas preciso

GANs se destacam:
  + Gerasamples rapidamente
  + Alta qualidade visual
  + Treinamento competitivo
  - Instavel, mode collapse
```

---

## 2. GAN Basico (Generator + Discriminator)

### 2.1 Arquitetura

```text
Arquitetura GAN:
==================

       z ~ N(0,1)      
          |            
    +-----v-----+      
    | GENERATOR |      
    |    (G)    |      
    +-----+-----+      
          |            
      G(z) (fake)      
          |            
    +-----v-----+      
    | DISCRIMINATOR|    
    |    (D)    |      
    +-----+-----+      
          |            
      D(G(z)) (score) 

Discriminador tambem recebe dados reais:
  
  x ~ p_data  -> D(x) -> "real"
  G(z) -> D(G(z)) -> "fake"

Treinamento:
  G quer: D(G(z)) -> 1 (engana D)
  D quer: D(x) -> 1, D(G(z)) -> 0 (detecta)
```

### 2.2 Generator

```text
Generator:
===========

Funcao: z -> G(z)
  - z: vetor de ruido (latent space)
  - G(z): dado sintetizado (imagem, texto, etc.)

Arquitetura tipica (para imagens):
  - Input: z ∈ R^100 (ruido gaussiano)
  - Camadas: Linear -> Reshape -> ConvTranspose -> ReLU/BN -> Tanh
  - Output: imagem (ex: 64x64x3)

Exemplo para MNIST (28x28):
  z: (100,)
  -> Linear(100, 256) -> ReLU -> BN
  -> Linear(256, 512) -> ReLU -> BN
  -> Linear(512, 784) -> Tanh
  -> Reshape para (28, 28)

Propriedade importante:
  - G e DIFERENCIAMENTO em funcao de z
  - Permite backpropagation de D para G
```

### 2.3 Discriminator

```text
Discriminator:
===============

Funcao: x -> D(x) ∈ [0, 1]
  - x: dado real ou fake
  - D(x): probabilidade de ser real

Arquitetura tipica (para imagens):
  - Input: imagem (ex: 28x28x1)
  - Camadas: Conv -> LeakyReLU -> Dropout -> Linear -> Sigmoid
  - Output: escalar (probabilidade)

Exemplo para MNIST:
  Input: (28, 28, 1)
  -> Conv(1, 64, 4, 2, 1) -> LeakyReLU(0.2)
  -> Conv(64, 128, 4, 2, 1) -> LeakyReLU(0.2) -> BN
  -> Flatten -> Linear(6272, 1) -> Sigmoid
  -> Output: (1,) probabilidade

Propriedade:
  - D e CLASSIFICADOR binario
  - Treinado com dados reais (label=1) e fake (label=0)
```

### 2.4 Interacao

```text
Interacao G e D:
==================

Dado um batch:
  1. Amostrar z ~ N(0, I) (ruido)
  2. Gerar fakes: G(z)
  3. Amostrar reais: x ~ p_data
  4. Treinar D:
     - D(x) -> 1 (real)
     - D(G(z)) -> 0 (fake)
  5. Treinar G:
     - D(G(z)) -> 1 (engana D)

Equilibrio:
  - G perfeito: G(z) indistinguivel de x
  - D perfeito: D(x) = 1, D(G(z)) = 0
  - Em equilibrio: D(x) = 0.5 para todo x
```

---

## 3. Funcao de Perda do GAN

### 3.1 Minimax Loss

```text
Funcao de Perda Original:
===========================

min_G max_D V(D, G) = E_{x~p_data}[log D(x)] + E_{z~p_z}[log(1 - D(G(z)))]

Interpretacao:
  - D quer MAXIMIZAR V:
    * log D(x) alto (classifica real como real)
    * log(1 - D(G(z))) alto (classifica fake como fake)
  
  - G quer MINIMIZAR V:
    * log(1 - D(G(z))) baixo (D(G(z)) alto -> engana D)

Alternativa (non-saturating):
  max_G E_{z~p_z}[log D(G(z))]

  - G quer MAXIMIZAR log D(G(z))
  - Mais estavel para treinamento
  - Equivalente ao minimax no equilibrio
```

### 3.2 Perda por Componente

```text
Perda do Discriminador:
=========================

L_D = -E_{x~p_data}[log D(x)] - E_{z~p_z}[log(1 - D(G(z)))]

Simplificado (por batch):
  L_D = -mean(log(D(x_real))) - mean(log(1 - D(x_fake)))

Gradiente:
  dL_D/dtheta_D = -mean((1/D(x_real)) * dD/dtheta) 
                  + mean((1/(1-D(x_fake))) * dD/dtheta)

Perda do Generator:
=====================

L_G = -E_{z~p_z}[log D(G(z))]

Simplificado:
  L_G = -mean(log(D(x_fake)))

Gradiente:
  dL_G/dtheta_G = -mean((1/D(x_fake)) * dD/dG * dG/dtheta_G)

Onde dD/dG: gradiente de D em relacao a entrada fake
```

### 3.3 Por Que Log

```text
Por Que Usar Log:
===================

1. Estabilidade Numerica:
   - D(x) ∈ (0, 1)
   - log(D(x)) ∈ (-inf, 0)
   - Mais estavel que D(x) diretamente

2. Entropia Cruzada:
   - A perda do GAN e entropia cruzada binaria
   - Interpretacao probabilistica clara

3. Gradiente:
   - log converte multiplicacoes em somas
   - Mais estavel numericamente

4. Equilibrio:
   - No equilibrio perfeito: D(x) = 0.5
   - log(0.5) = -0.693
   - Perda converge para valor finito
```

---

## 4. Minimax Game

### 4.1 Teoria dos Jogos

```text
GAN como Jogo Adversarial:
============================

Dois jogadores:
  - Generator (G): quer enganar Discriminator
  - Discriminator (D): quer detectar fakes

Estrategia:
  - G: distribuicao p_g sobre dados
  - D: classificador binario

Jogo zero-soma:
  - Ganho de G = Perda de D
  - min_G max_D V(D, G)

Teorema (Goodfellow et al., 2014):
  Para G fixo, o D otimo e:
    D*_G(x) = p_data(x) / (p_data(x) + p_g(x))

  No equilibrio global:
    p_g = p_data
    D*(x) = 0.5 para todo x

Significado:
  - Quando p_g = p_data, D nao consegue distinguir
  - G aprendeu a distribuicao real dos dados
```

### 4.2 Convergencia

```text
Convergencia do GAN:
=====================

Algoritmo (por passo):
  1. Para k passos:
     - Amostrar batch de reais
     - Amostrar batch de fakes
     - Atualizar D (ascendente de gradiente)
  2. Amostrar batch de fakes
  3. Atualizar G (descendente de gradiente)

Convergencia:
  - Com D otimo, G converge para p_data
  - Na pratica, D nao e otimo
  - Treinamento pode oscilar

Problemas:
  - D muito forte: gradiente de G desaparece
  - D muito fraco: G nao aprende
  - Balance e chave
```

---

## 5. Training Dynamics

### 5.1 Fases do Treinamento

```text
Fases do Treinamento GAN:
===========================

Fase 1: D dominante (inicial)
  - D e bom em detectar fakes obvios
  - G gera lixo, D detecta facil
  - Gradiente de G e forte
  - G aprende rapido

Fase 2: G melhorando
  - G comeca a gerar dados mais realistas
  - D comeca a ter duvidas
  - Gradiente de G diminui
  - Aprendizado desacelera

Fase 3: Equilibrio (ideal)
  - G gera dados indistinguiaveis
  - D: D(x) = 0.5 para todo x
  - Gradientes estaveis
  - Treinamento convergiu

Fase 4: D colapsa (problema)
  - D se torna muito confiante
  - Gradiente de G -> 0
  - G para de aprender
  - Mode collapse pode ocorrer
```

### 5.2 Diagnostico

```text
Diagnosticando o Treinamento:
================================

Metricas para monitorar:
  1. D_loss (real): deve diminuir e estabilizar
  2. D_loss (fake): deve aumentar e estabilizar
  3. G_loss: deve diminuir inicialmente, depois oscilar
  4. D(x): deve convergir para ~0.5
  5. D(G(z)): deve convergir para ~0.5

Sinais de problemas:
  - D_loss -> 0: D muito forte, G nao aprende
  - D_loss -> inf: D muito fraco, G engana facil
  - G_loss -> 0: G muito forte, D colapsou
  - D_loss oscila muito: instabilidade

Solucoes:
  - D_loss baixo: treinar D menos (k < 5)
  - D_loss alto: treinar D mais (k > 5)
  - Oscilacao: reduzir learning rate
  - Mode collapse: usar WGAN, label smoothing
```

---

## 6. Mode Collapse

### 6.1 O Que e Mode Collapse

```text
Mode Collapse:
================

Problema: G aprende a gerar POUCOS modos (tipos de dados)

Exemplo com MNIST:
  - Digitos 0-9 devem ser gerados
  - G aprende a gerar APENAS 1 e 7
  - D e enganado porque 1 e 7 sao realistas
  - Mas G NAO gera 0, 2, 3, 4, 5, 6, 8, 9

Por que acontece:
  - G encontra UMA estrategia que engana D
  - Nao ha incentivo para diversidade
  - D nao penaliza falta de diversidade

Tipos:
  1. Complete collapse: G gera apenas 1 amostra
  2. Partial collapse: G gera poucos modos
  3. Tempo collapse: G oscila entre modos
```

### 6.2 Solucoes

```text
Solucoes para Mode Collapse:
==============================

1. Minibatch Discrimination:
   - D olha para AMOSTRAS do batch
   - Detecta se sao todas iguais
   - Penaliza falta de diversidade

2. Unrolled GAN:
   - G considera futuros updates de D
   - Usa D desatualizado para calcular loss
   - Mais estavel mas mais caro

3. Feature Matching:
   - G maximiza E[features reais] = E[features fakes]
   - Nao usa saida binaria de D
   - Mais estavel

4. Wasserstein GAN:
   - Loss mais estavel
   - Melhor gradiente para G
   - Reduz mode collapse

5. Spectral Normalization:
   - Normaliza pesos de D
   - Impede D de se tornar muito forte
   - Mais estavel

6. Label Smoothing:
   - Em vez de label=1, usa 0.9
   - D nao fica muito confiante
   - Mais robusto
```

---

## 7. Wasserstein GAN (WGAN)

### 7.1 Motivacao

```text
Problemas do GAN Original:
============================

1. Instabilidade de Treinamento:
   - D muito forte: gradiente -> 0
   - D muito fraco: gradiente instavel
   - Balance dificil

2. Mode Collapse:
   - G engana D com poucos modos
   - Nao ha penalidade por falta de diversidade

3. Metricas ruins:
   - Nao ha metrica continua de qualidade
   - D_loss nao indica qualidade do gerador

Solucao: Wasserstein Distance
  - Distancia entre distribuicoes
  - Mais estavel teoricamente
  - Gradientes mais informativos
```

### 7.2 Wasserstein Distance

```text
Wasserstein Distance (Earth Mover's Distance):
================================================

W(p_data, p_g) = inf_{gamma ∈ Γ(p_data, p_g)} E_{(x,y)~gamma}[||x - y||]

Onde Γ(p_data, p_g) e o conjunto de todas as distribucoes conjuntas com marginais p_data e p_g

Interpretacao:
  - Quanto "movimento" de terra e necessario
  - para transformar p_data em p_g
  - Custo = distancia * quantidade movida

Propriedades:
  1. W = 0 iff p_data = p_g
  2. Continua (diferente de KL/JS que podem ser inf)
  3. Gradientes mais estaveis
  4. Correlaciona com qualidade visual
```

### 7.3 WGAN Loss

```text
WGAN Loss:
============

D (agora chamado Critic):
  - Nao tem sigmoid na saida
  - Output: escalar (sem sigmoid)
  - Peso restringido: ||W|| <= 1 (weight clipping ou gradient penalty)

Perda do Critic:
  L_C = E_{x~p_data}[C(x)] - E_{z~p_z}[C(G(z))]

  Critic quer MAXIMIZAR L_C:
    * C(x) alto (dado real recebe score alto)
    * C(G(z)) baixo (dado fake recebe score baixo)

Perda do Generator:
  L_G = -E_{z~p_z}[C(G(z))]

  G quer MINIMIZAR L_G:
    * C(G(z)) alto (fake parece real)

Weight Clipping (WGAN original):
  - Apos update, clip pesos: W = clip(W, -c, c)
  - Garante Lipschitz constraint
  - Problematico: causa vanishing/exploding gradients

Gradient Penalty (WGAN-GP):
  - Penaliza gradiente de C em relacao a input
  - L_gp = lambda * E[(||nabla_x C(x_hat)||_2 - 1)^2]
  - x_hat: interpolacao entre real e fake
  - Mais estavel que weight clipping
```

### 7.4 WGAN-GP

```text
WGAN-GP (Gradient Penalty):
==============================

Perda completa:
  L_C = E_{x~p_data}[C(x)] - E_{z~p_z}[C(G(z))]
        + lambda * E_{x_hat~p_x_hat}[(||nabla_{x_hat} C(x_hat)||_2 - 1)^2]

Onde:
  x_hat = epsilon * x + (1 - epsilon) * G(z)
  epsilon ~ U(0, 1)
  lambda: hiperparametro (tipicamente 10)

Por que funciona:
  - Forca ||nabla C|| = 1 em interpolacoes
  - Impede C de ser muito inclinado ou plano
  - Lipschitz constraint de forma suave
  - Nao precisa de weight clipping

Vantagens:
  + Treinamento mais estavel
  + Gradientes mais informativos
  + Menos mode collapse
  + Metrica continua (W distance)

Desvantagens:
  - Mais lento (calcular gradient penalty)
  - Mais memoria (calcular gradient)
  - lambda sensivel
```

---

## 8. Conditional GAN

### 8.1 Motivacao

```text
GAN Incondicional vs Condicional:
====================================

Incondicional:
  - G: z -> G(z)
  - Gera dados aleatorios
  - Nao controle sobre o que gerar

Condicional:
  - G: (z, y) -> G(z, y)
  - y: condicao (label, texto, imagem)
  - Gera dados com caracteristica especifica

Exemplo:
  - Incondicional: "gere um digito" (aleatorio)
  - Condicional: "gere um digito 7" (especifico)

Aplicacoes:
  - Text-to-Image: "um gato sentado"
  - Image-to-Image: dia -> noite
  - Super-resolution: baixa -> alta resolucao
  - Inpainting: preencher regioes
```

### 8.2 Arquitetura

```text
Conditional GAN Architecture:
================================

Generator:
  - Input: z (ruido) + y (condicao)
  - Concatenar: [z, y]
  - Rede neural: [z, y] -> G(z, y)
  - Output: dado sintetizado

Discriminator:
  - Input: x (dado) + y (condicao)
  - Concatenar: [x, y]
  - Rede neural: [x, y] -> D(x, y)
  - Output: probabilidade de ser real

Perda:
  L_D = -E[log D(x, y)] - E[log(1 - D(G(z, y), y))]
  L_G = -E[log D(G(z, y), y)]

Diferenca:
  - D recebe condicao junto com dado
  - D aprende a avaliar "x e y sao consistentes?"
  - G aprende a gerar "x consistente com y"
```

### 8.3 Exemplos

```text
Exemplos de Conditional GAN:
==============================

1. Image Generation from Labels:
   - y: label (ex: "gato", "cachorro")
   - G: (z, label) -> imagem
   - D: (imagem, label) -> real/fake

2. Text-to-Image:
   - y:embedding de texto
   - G: (z, texto_embedding) -> imagem
   - D: (imagem, texto_embedding) -> real/fake

3. Image-to-Image:
   - y: imagem de entrada
   - G: (z, imagem_entrada) -> imagem_saida
   - D: (imagem_saida, imagem_entrada) -> real/fake
   - Exemplo: aerial -> map, day -> night

4. Super-Resolution:
   - y: imagem de baixa resolucao
   - G: (z, lr_image) -> hr_image
   - D: (hr_image, lr_image) -> real/fake

5. Inpainting:
   - y: imagem com mascara
   - G: (z, masked_image) -> imagem_completa
   - D: (imagem_completa, masked_image) -> real/fake
```

---

## 9. Implementacao Completa em C++

```cpp
// gans.h - Generative Adversarial Networks do Zero em C++
// Implementacao completa sem bibliotecas externas

#ifndef GANS_H
#define GANS_H

#include <vector>
#include <cmath>
#include <random>
#include <algorithm>
#include <numeric>
#include <limits>
#include <iostream>
#include <cassert>

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

    void zero() { std::fill(data.begin(), data.end(), 0.0f); }

    Tensor clone() const {
        Tensor t;
        t.shape = shape;
        t.total_size = total_size;
        t.data = data;
        return t;
    }
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
// Matmul
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
// Leaky ReLU
// ============================================================

float leaky_relu(float x, float alpha = 0.2f) {
    return x > 0 ? x : alpha * x;
}

float leaky_relu_grad(float x, float alpha = 0.2f) {
    return x > 0 ? 1.0f : alpha;
}

// ============================================================
// Sigmoid
// ============================================================

float sigmoid(float x) {
    return 1.0f / (1.0f + std::exp(-x));
}

// ============================================================
// Batch Normalization (simplificado)
// ============================================================

class BatchNorm {
public:
    Tensor gamma, beta;
    Tensor running_mean, running_var;
    int d;
    float momentum, eps;

    BatchNorm(int d, float momentum = 0.1f, float eps = 1e-5f)
        : d(d), momentum(momentum), eps(eps) {
        gamma = Tensor({d});
        beta = Tensor({d});
        running_mean = Tensor({d});
        running_var = Tensor({d});
        for (int i = 0; i < d; i++) gamma.at(i) = 1.0f;
    }

    Tensor forward(const Tensor& x, bool training = true) {
        int batch_size = x.shape[0];
        Tensor output = x.clone();

        if (training) {
            // Calcular media do batch
            Tensor mean({d});
            mean.zero();
            for (int i = 0; i < batch_size; i++) {
                for (int j = 0; j < d; j++) {
                    mean.at(j) += x.at(i, j);
                }
            }
            for (int j = 0; j < d; j++) mean.at(j) /= batch_size;

            // Calcular variancia
            Tensor var({d});
            var.zero();
            for (int i = 0; i < batch_size; i++) {
                for (int j = 0; j < d; j++) {
                    float diff = x.at(i, j) - mean.at(j);
                    var.at(j) += diff * diff;
                }
            }
            for (int j = 0; j < d; j++) var.at(j) /= batch_size;

            // Normalizar
            for (int i = 0; i < batch_size; i++) {
                for (int j = 0; j < d; j++) {
                    float norm = (x.at(i, j) - mean.at(j)) / std::sqrt(var.at(j) + eps);
                    output.at(i, j) = gamma.at(j) * norm + beta.at(j);
                }
            }

            // Atualizar running stats
            for (int j = 0; j < d; j++) {
                running_mean.at(j) = (1 - momentum) * running_mean.at(j) + momentum * mean.at(j);
                running_var.at(j) = (1 - momentum) * running_var.at(j) + momentum * var.at(j);
            }
        } else {
            // Inferencia: usar running stats
            for (int i = 0; i < batch_size; i++) {
                for (int j = 0; j < d; j++) {
                    float norm = (x.at(i, j) - running_mean.at(j)) /
                                 std::sqrt(running_var.at(j) + eps);
                    output.at(i, j) = gamma.at(j) * norm + beta.at(j);
                }
            }
        }

        return output;
    }
};

// ============================================================
// Generator
// ============================================================

class Generator {
public:
    Tensor W1, b1;  // z -> hidden1
    Tensor W2, b2;  // hidden1 -> hidden2
    Tensor W3, b3;  // hidden2 -> output
    BatchNorm bn1, bn2;
    int z_dim, hidden1, hidden2, output_dim;

    Generator(int z_dim, int hidden1, int hidden2, int output_dim)
        : z_dim(z_dim), hidden1(hidden1), hidden2(hidden2), output_dim(output_dim),
          bn1(hidden1), bn2(hidden2) {
        W1 = Tensor({z_dim, hidden1});
        b1 = Tensor({hidden1});
        W2 = Tensor({hidden1, hidden2});
        b2 = Tensor({hidden2});
        W3 = Tensor({hidden2, output_dim});
        b3 = Tensor({output_dim});
    }

    void init_weights(std::mt19937& gen) {
        xavier_init(W1, gen);
        xavier_init(W2, gen);
        xavier_init(W3, gen);
    }

    Tensor forward(const Tensor& z, bool training = true) {
        int batch_size = z.shape[0];

        // Camada 1: Linear + BN + ReLU
        Tensor h1({batch_size, hidden1});
        matmul(z, W1, h1, batch_size, z_dim, hidden1);
        for (int i = 0; i < batch_size; i++) {
            for (int j = 0; j < hidden1; j++) {
                h1.at(i, j) += b1.at(j);
            }
        }
        h1 = bn1.forward(h1, training);
        for (float& val : h1.data) val = std::max(0.0f, val);  // ReLU

        // Camada 2: Linear + BN + ReLU
        Tensor h2({batch_size, hidden2});
        matmul(h1, W2, h2, batch_size, hidden1, hidden2);
        for (int i = 0; i < batch_size; i++) {
            for (int j = 0; j < hidden2; j++) {
                h2.at(i, j) += b2.at(j);
            }
        }
        h2 = bn2.forward(h2, training);
        for (float& val : h2.data) val = std::max(0.0f, val);  // ReLU

        // Camada 3: Linear + Tanh
        Tensor output({batch_size, output_dim});
        matmul(h2, W3, output, batch_size, hidden2, output_dim);
        for (int i = 0; i < batch_size; i++) {
            for (int j = 0; j < output_dim; j++) {
                output.at(i, j) = std::tanh(output.at(i, j) + b3.at(j));
            }
        }

        return output;
    }
};

// ============================================================
// Discriminator
// ============================================================

class Discriminator {
public:
    Tensor W1, b1;  // input -> hidden1
    Tensor W2, b2;  // hidden1 -> hidden2
    Tensor W3, b3;  // hidden2 -> output
    int input_dim, hidden1, hidden2;

    Discriminator(int input_dim, int hidden1, int hidden2)
        : input_dim(input_dim), hidden1(hidden1), hidden2(hidden2) {
        W1 = Tensor({input_dim, hidden1});
        b1 = Tensor({hidden1});
        W2 = Tensor({hidden1, hidden2});
        b2 = Tensor({hidden2});
        W3 = Tensor({hidden2, 1});
        b3 = Tensor({1});
    }

    void init_weights(std::mt19937& gen) {
        xavier_init(W1, gen);
        xavier_init(W2, gen);
        xavier_init(W3, gen);
    }

    // Forward sem sigmoid (para WGAN) ou com sigmoid (para GAN normal)
    Tensor forward(const Tensor& x, bool use_sigmoid = true) {
        int batch_size = x.shape[0];

        // Camada 1: Linear + LeakyReLU
        Tensor h1({batch_size, hidden1});
        matmul(x, W1, h1, batch_size, input_dim, hidden1);
        for (int i = 0; i < batch_size; i++) {
            for (int j = 0; j < hidden1; j++) {
                h1.at(i, j) = leaky_relu(h1.at(i, j) + b1.at(j));
            }
        }

        // Camada 2: Linear + LeakyReLU
        Tensor h2({batch_size, hidden2});
        matmul(h1, W2, h2, batch_size, hidden1, hidden2);
        for (int i = 0; i < batch_size; i++) {
            for (int j = 0; j < hidden2; j++) {
                h2.at(i, j) = leaky_relu(h2.at(i, j) + b2.at(j));
            }
        }

        // Camada 3: Linear
        Tensor output({batch_size, 1});
        matmul(h2, W3, output, batch_size, hidden2, 1);
        for (int i = 0; i < batch_size; i++) {
            output.at(i, 0) += b3.at(0);
        }

        // Sigmoid opcional
        if (use_sigmoid) {
            for (float& val : output.data) {
                val = sigmoid(val);
            }
        }

        return output;
    }

    // Calcular loss (GAN normal ou WGAN)
    float compute_loss(const Tensor& real_output, const Tensor& fake_output, bool use_wgan = false) {
        int batch_size = real_output.shape[0];

        if (use_wgan) {
            // WGAN loss: -E[C(real)] + E[C(fake)]
            float loss = 0.0f;
            for (int i = 0; i < batch_size; i++) {
                loss -= real_output.at(i, 0);  // -C(real)
                loss += fake_output.at(i, 0);  // +C(fake)
            }
            return loss / batch_size;
        } else {
            // GAN loss: -E[log(D(real))] - E[log(1 - D(fake))]
            float loss = 0.0f;
            for (int i = 0; i < batch_size; i++) {
                float real_val = std::max(real_output.at(i, 0), 1e-7f);
                float fake_val = std::max(1.0f - fake_output.at(i, 0), 1e-7f);
                loss -= std::log(real_val);
                loss -= std::log(fake_val);
            }
            return loss / batch_size;
        }
    }
};

// ============================================================
// GAN Completo
// ============================================================

class GAN {
public:
    Generator generator;
    Discriminator discriminator;
    int z_dim;

    GAN(int z_dim, int hidden_g1, int hidden_g2, int output_dim,
        int hidden_d1, int hidden_d2)
        : generator(z_dim, hidden_g1, hidden_g2, output_dim),
          discriminator(output_dim, hidden_d1, hidden_d2),
          z_dim(z_dim) {}

    void init_weights(std::mt19937& gen) {
        generator.init_weights(gen);
        discriminator.init_weights(gen);
    }

    // Amostrar ruido
    Tensor sample_noise(int batch_size, std::mt19937& gen) {
        Tensor z({batch_size, z_dim});
        std::normal_distribution<float> dist(0.0f, 1.0f);
        for (float& val : z.data) val = dist(gen);
        return z;
    }

    // Gerar fakes
    Tensor generate(int batch_size, std::mt19937& gen) {
        Tensor z = sample_noise(batch_size, gen);
        return generator.forward(z, false);
    }

    // Um passo de treinamento
    std::pair<float, float> train_step(const Tensor& real_data,
                                        int batch_size,
                                        std::mt19937& gen,
                                        bool use_wgan = false) {
        // 1. Gerar fakes
        Tensor z = sample_noise(batch_size, gen);
        Tensor fake_data = generator.forward(z, true);

        // 2. Forward do Discriminator
        Tensor real_output = discriminator.forward(real_data, !use_wgan);
        Tensor fake_output = discriminator.forward(fake_data.detach(), !use_wgan);

        // 3. Calcular loss do D
        float d_loss = discriminator.compute_loss(real_output, fake_output, use_wgan);

        // 4. Forward do Generator
        Tensor fake_output_g = discriminator.forward(fake_data, !use_wgan);

        // 5. Calcular loss do G
        float g_loss = 0.0f;
        int bs = fake_output_g.shape[0];
        if (use_wgan) {
            for (int i = 0; i < bs; i++) {
                g_loss -= fake_output_g.at(i, 0);
            }
        } else {
            for (int i = 0; i < bs; i++) {
                float val = std::max(fake_output_g.at(i, 0), 1e-7f);
                g_loss -= std::log(val);
            }
        }
        g_loss /= bs;

        return {d_loss, g_loss};
    }
};

// ============================================================
// WGAN com Gradient Penalty
// ============================================================

class WGAN_GP {
public:
    Generator generator;
    Discriminator critic;  // WGAN chama de "critic"
    int z_dim;
    float lambda_gp;

    WGAN_GP(int z_dim, int hidden_g1, int hidden_g2, int output_dim,
            int hidden_d1, int hidden_d2, float lambda_gp = 10.0f)
        : generator(z_dim, hidden_g1, hidden_g2, output_dim),
          critic(output_dim, hidden_d1, hidden_d2),
          z_dim(z_dim), lambda_gp(lambda_gp) {}

    void init_weights(std::mt19937& gen) {
        generator.init_weights(gen);
        critic.init_weights(gen);
    }

    Tensor sample_noise(int batch_size, std::mt19937& gen) {
        Tensor z({batch_size, z_dim});
        std::normal_distribution<float> dist(0.0f, 1.0f);
        for (float& val : z.data) val = dist(gen);
        return z;
    }

    // Interpolacao para gradient penalty
    Tensor interpolate(const Tensor& real, const Tensor& fake, std::mt19937& gen) {
        int batch_size = real.shape[0];
        int dim = real.shape[1];
        Tensor interp({batch_size, dim});
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);

        for (int i = 0; i < batch_size; i++) {
            float eps = dist(gen);
            for (int j = 0; j < dim; j++) {
                interp.at(i, j) = eps * real.at(i, j) + (1 - eps) * fake.at(i, j);
            }
        }

        return interp;
    }

    // Gradient penalty (aproximacao numerica)
    float compute_gradient_penalty(const Tensor& interpolated) {
        int batch_size = interpolated.shape[0];
        int dim = interpolated.shape[1];
        float penalty = 0.0f;

        // Aproximar gradiente numericamente
        float h = 1e-4f;
        for (int i = 0; i < batch_size; i++) {
            float grad_norm_sq = 0.0f;
            for (int j = 0; j < dim; j++) {
                // Finite difference
                Tensor x_plus = interpolated.clone();
                Tensor x_minus = interpolated.clone();
                x_plus.at(i, j) += h;
                x_minus.at(i, j) -= h;

                Tensor out_plus = critic.forward(x_plus, false);
                Tensor out_minus = critic.forward(x_minus, false);

                float grad = (out_plus.at(0, 0) - out_minus.at(0, 0)) / (2 * h);
                grad_norm_sq += grad * grad;
            }
            float grad_norm = std::sqrt(grad_norm_sq);
            penalty += (grad_norm - 1.0f) * (grad_norm - 1.0f);
        }

        return penalty / batch_size;
    }

    std::pair<float, float> train_step(const Tensor& real_data,
                                        int batch_size,
                                        std::mt19937& gen) {
        // 1. Gerar fakes
        Tensor z = sample_noise(batch_size, gen);
        Tensor fake_data = generator.forward(z, true);

        // 2. Critic scores
        Tensor real_score = critic.forward(real_data, false);
        Tensor fake_score = critic.forward(fake_data, false);

        // 3. Critic loss
        float c_loss = 0.0f;
        for (int i = 0; i < batch_size; i++) {
            c_loss -= real_score.at(i, 0);
            c_loss += fake_score.at(i, 0);
        }
        c_loss /= batch_size;

        // 4. Gradient penalty
        Tensor interp = interpolate(real_data, fake_data, gen);
        float gp = compute_gradient_penalty(interp);
        c_loss += lambda_gp * gp;

        // 5. Generator loss
        Tensor fake_score_g = critic.forward(fake_data, false);
        float g_loss = 0.0f;
        for (int i = 0; i < batch_size; i++) {
            g_loss -= fake_score_g.at(i, 0);
        }
        g_loss /= batch_size;

        return {c_loss, g_loss};
    }
};

// ============================================================
// Exemplo: Gerar numeros
// ============================================================

void example_generate_numbers() {
    std::mt19937 gen(42);

    // Configuracao: gerar numeros 1D (distribuicao bimodal)
    int z_dim = 8;
    int output_dim = 1;

    // Criar GAN
    GAN gan(z_dim, 32, 32, output_dim, 32, 32);
    gan.init_weights(gen);

    // Dados reais: bimodal (pics em 2.0 e 8.0)
    int batch_size = 64;
    int n_epochs = 1000;

    std::cout << "Treinando GAN para gerar numeros..." << std::endl;

    for (int epoch = 0; epoch < n_epochs; epoch++) {
        // Gerar dados reais
        Tensor real_data({batch_size, output_dim});
        std::normal_distribution<float> dist1(2.0f, 0.5f);
        std::normal_distribution<float> dist2(8.0f, 0.5f);
        std::uniform_real_distribution<float> coin(0.0f, 1.0f);

        for (int i = 0; i < batch_size; i++) {
            if (coin(gen) < 0.5f) {
                real_data.at(i, 0) = dist1(gen);
            } else {
                real_data.at(i, 0) = dist2(gen);
            }
        }

        // Treinar
        auto [d_loss, g_loss] = gan.train_step(real_data, batch_size, gen);

        if (epoch % 100 == 0) {
            std::cout << "Epoch " << epoch
                      << " - D_loss: " << d_loss
                      << " - G_loss: " << g_loss << std::endl;
        }
    }

    // Gerar amostras
    std::cout << "\nAmostras geradas:" << std::endl;
    Tensor generated = gan.generate(10, gen);
    for (int i = 0; i < 10; i++) {
        std::cout << "  " << generated.at(i, 0) << std::endl;
    }
}

#endif // GANS_H
```

---

## 10. Implementacao em Rust

```rust
// gans.rs - Generative Adversarial Networks do Zero em Rust

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

    pub fn detach(&self) -> Tensor {
        self.clone()
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
// Generator
// ============================================================

pub struct Generator {
    pub w1: Tensor,
    pub b1: Tensor,
    pub w2: Tensor,
    pub b2: Tensor,
    pub w3: Tensor,
    pub b3: Tensor,
    pub z_dim: usize,
    pub hidden1: usize,
    pub hidden2: usize,
    pub output_dim: usize,
}

impl Generator {
    pub fn new(z_dim: usize, hidden1: usize, hidden2: usize, output_dim: usize) -> Self {
        Generator {
            w1: Tensor::randn(vec![z_dim, hidden1], 0.1),
            b1: Tensor::new(vec![hidden1]),
            w2: Tensor::randn(vec![hidden1, hidden2], 0.1),
            b2: Tensor::new(vec![hidden2]),
            w3: Tensor::randn(vec![hidden2, output_dim], 0.1),
            b3: Tensor::new(vec![output_dim]),
            z_dim, hidden1, hidden2, output_dim,
        }
    }

    pub fn forward(&self, z: &Tensor) -> Tensor {
        let batch_size = z.shape[0];

        // Camada 1: Linear + ReLU
        let mut h1 = matmul(z, &self.w1, batch_size, self.z_dim, self.hidden1);
        for i in 0..batch_size {
            for j in 0..self.hidden1 {
                let val = h1.get(i, j) + self.b1.get(0, j);
                h1.set(i, j, val.max(0.0));  // ReLU
            }
        }

        // Camada 2: Linear + ReLU
        let mut h2 = matmul(&h1, &self.w2, batch_size, self.hidden1, self.hidden2);
        for i in 0..batch_size {
            for j in 0..self.hidden2 {
                let val = h2.get(i, j) + self.b2.get(0, j);
                h2.set(i, j, val.max(0.0));  // ReLU
            }
        }

        // Camada 3: Linear + Tanh
        let mut output = matmul(&h2, &self.w3, batch_size, self.hidden2, self.output_dim);
        for i in 0..batch_size {
            for j in 0..self.output_dim {
                let val = output.get(i, j) + self.b3.get(0, j);
                output.set(i, j, val.tanh());
            }
        }

        output
    }
}

// ============================================================
// Discriminator
// ============================================================

pub struct Discriminator {
    pub w1: Tensor,
    pub b1: Tensor,
    pub w2: Tensor,
    pub b2: Tensor,
    pub w3: Tensor,
    pub b3: Tensor,
    pub input_dim: usize,
    pub hidden1: usize,
    pub hidden2: usize,
}

impl Discriminator {
    pub fn new(input_dim: usize, hidden1: usize, hidden2: usize) -> Self {
        Discriminator {
            w1: Tensor::randn(vec![input_dim, hidden1], 0.1),
            b1: Tensor::new(vec![hidden1]),
            w2: Tensor::randn(vec![hidden1, hidden2], 0.1),
            b2: Tensor::new(vec![hidden2]),
            w3: Tensor::randn(vec![hidden2, 1], 0.1),
            b3: Tensor::new(vec![1]),
            input_dim, hidden1, hidden2,
        }
    }

    pub fn forward(&self, x: &Tensor, use_sigmoid: bool) -> Tensor {
        let batch_size = x.shape[0];

        // Camada 1: Linear + LeakyReLU
        let mut h1 = matmul(x, &self.w1, batch_size, self.input_dim, self.hidden1);
        for i in 0..batch_size {
            for j in 0..self.hidden1 {
                let val = h1.get(i, j) + self.b1.get(0, j);
                h1.set(i, j, if val > 0.0 { val } else { 0.2 * val });
            }
        }

        // Camada 2: Linear + LeakyReLU
        let mut h2 = matmul(&h1, &self.w2, batch_size, self.hidden1, self.hidden2);
        for i in 0..batch_size {
            for j in 0..self.hidden2 {
                let val = h2.get(i, j) + self.b2.get(0, j);
                h2.set(i, j, if val > 0.0 { val } else { 0.2 * val });
            }
        }

        // Camada 3: Linear
        let mut output = matmul(&h2, &self.w3, batch_size, self.hidden2, 1);
        for i in 0..batch_size {
            output.set(i, 0, output.get(i, 0) + self.b3.get(0, 0));
        }

        // Sigmoid opcional
        if use_sigmoid {
            for val in output.data.iter_mut() {
                *val = 1.0 / (1.0 + (-val).exp());
            }
        }

        output
    }
}

// ============================================================
// GAN
// ============================================================

pub struct GAN {
    pub generator: Generator,
    pub discriminator: Discriminator,
    pub z_dim: usize,
}

impl GAN {
    pub fn new(z_dim: usize, hidden_g: usize, output_dim: usize, hidden_d: usize) -> Self {
        GAN {
            generator: Generator::new(z_dim, hidden_g, hidden_g, output_dim),
            discriminator: Discriminator::new(output_dim, hidden_d, hidden_d),
            z_dim,
        }
    }

    pub fn sample_noise(&self, batch_size: usize) -> Tensor {
        Tensor::randn(vec![batch_size, self.z_dim], 1.0)
    }

    pub fn generate(&self, batch_size: usize) -> Tensor {
        let z = self.sample_noise(batch_size);
        self.generator.forward(&z)
    }

    pub fn train_step(&self, real_data: &Tensor, batch_size: usize) -> (f32, f32) {
        // 1. Gerar fakes
        let z = self.sample_noise(batch_size);
        let fake_data = self.generator.forward(&z);

        // 2. Forward D
        let real_output = self.discriminator.forward(real_data, true);
        let fake_output = self.discriminator.forward(&fake_data.detach(), true);

        // 3. D loss
        let mut d_loss = 0.0f32;
        for i in 0..batch_size {
            let real_val = real_output.get(i, 0).max(1e-7);
            let fake_val = (1.0 - fake_output.get(i, 0)).max(1e-7);
            d_loss -= real_val.ln() + fake_val.ln();
        }
        d_loss /= batch_size as f32;

        // 4. G loss
        let fake_output_g = self.discriminator.forward(&fake_data, true);
        let mut g_loss = 0.0f32;
        for i in 0..batch_size {
            let val = fake_output_g.get(i, 0).max(1e-7);
            g_loss -= val.ln();
        }
        g_loss /= batch_size as f32;

        (d_loss, g_loss)
    }
}

// ============================================================
// WGAN
// ============================================================

pub struct WGAN {
    pub generator: Generator,
    pub critic: Discriminator,
    pub z_dim: usize,
    pub lambda_gp: f32,
}

impl WGAN {
    pub fn new(z_dim: usize, hidden_g: usize, output_dim: usize,
               hidden_d: usize, lambda_gp: f32) -> Self {
        WGAN {
            generator: Generator::new(z_dim, hidden_g, hidden_g, output_dim),
            critic: Discriminator::new(output_dim, hidden_d, hidden_d),
            z_dim,
            lambda_gp,
        }
    }

    pub fn sample_noise(&self, batch_size: usize) -> Tensor {
        Tensor::randn(vec![batch_size, self.z_dim], 1.0)
    }

    pub fn interpolate(&self, real: &Tensor, fake: &Tensor) -> Tensor {
        let batch_size = real.shape[0];
        let dim = real.shape[1];
        let mut interp = Tensor::new(vec![batch_size, dim]);

        for i in 0..batch_size {
            let eps = rand_f32();
            for j in 0..dim {
                let val = eps * real.get(i, j) + (1.0 - eps) * fake.get(i, j);
                interp.set(i, j, val);
            }
        }

        interp
    }

    pub fn compute_gradient_penalty(&self, interpolated: &Tensor) -> f32 {
        let batch_size = interpolated.shape[0];
        let dim = interpolated.shape[1];
        let mut penalty = 0.0f32;
        let h = 1e-4f32;

        for i in 0..batch_size {
            let mut grad_norm_sq = 0.0f32;
            for j in 0..dim {
                let mut x_plus = interpolated.clone();
                let mut x_minus = interpolated.clone();

                let val_plus = x_plus.get(i, j) + h;
                let val_minus = x_minus.get(i, j) - h;
                x_plus.set(i, j, val_plus);
                x_minus.set(i, j, val_minus);

                let out_plus = self.critic.forward(&x_plus, false);
                let out_minus = self.critic.forward(&x_minus, false);

                let grad = (out_plus.get(0, 0) - out_minus.get(0, 0)) / (2.0 * h);
                grad_norm_sq += grad * grad;
            }
            let grad_norm = grad_norm_sq.sqrt();
            penalty += (grad_norm - 1.0).powi(2);
        }

        penalty / batch_size as f32
    }

    pub fn train_step(&self, real_data: &Tensor, batch_size: usize) -> (f32, f32) {
        let z = self.sample_noise(batch_size);
        let fake_data = self.generator.forward(&z);

        let real_score = self.critic.forward(real_data, false);
        let fake_score = self.critic.forward(&fake_data.detach(), false);

        let mut c_loss = 0.0f32;
        for i in 0..batch_size {
            c_loss -= real_score.get(i, 0);
            c_loss += fake_score.get(i, 0);
        }
        c_loss /= batch_size as f32;

        let interp = self.interpolate(real_data, &fake_data);
        let gp = self.compute_gradient_penalty(&interp);
        c_loss += self.lambda_gp * gp;

        let fake_score_g = self.critic.forward(&fake_data, false);
        let mut g_loss = 0.0f32;
        for i in 0..batch_size {
            g_loss -= fake_score_g.get(i, 0);
        }
        g_loss /= batch_size as f32;

        (c_loss, g_loss)
    }
}

// ============================================================
// Exemplo
// ============================================================

pub fn example_gan() {
    let z_dim = 8;
    let output_dim = 1;
    let batch_size = 64;
    let n_epochs = 1000;

    let gan = GAN::new(z_dim, 32, output_dim, 32);

    println!("Treinando GAN...");

    for epoch in 0..n_epochs {
        // Gerar dados reais (bimodal)
        let mut real_data = Tensor::new(vec![batch_size, output_dim]);
        for i in 0..batch_size {
            let val = if rand_f32() < 0.5 {
                2.0 + rand_f32() * 0.5
            } else {
                8.0 + rand_f32() * 0.5
            };
            real_data.set(i, 0, val);
        }

        let (d_loss, g_loss) = gan.train_step(&real_data, batch_size);

        if epoch % 100 == 0 {
            println!("Epoch {} - D_loss: {:.4} - G_loss: {:.4}", epoch, d_loss, g_loss);
        }
    }

    // Gerar amostras
    println!("\nAmostras geradas:");
    let generated = gan.generate(10);
    for i in 0..10 {
        println!("  {:.4}", generated.get(i, 0));
    }
}

fn main() {
    example_gan();
}
```

---

## 11. Implementacao em Fortran

```fortran
! gans.f90 - Generative Adversarial Networks do Zero em Fortran

module gans_mod
    implicit none
    integer, parameter :: sp = kind(0.0)

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
    ! Leaky ReLU
    ! ============================================================
    pure function leaky_relu(x, alpha) result(y)
        real(sp), intent(in) :: x, alpha
        real(sp) :: y
        if (x > 0.0_sp) then
            y = x
        else
            y = alpha * x
        end if
    end function leaky_relu

    ! ============================================================
    ! Sigmoid
    ! ============================================================
    pure function sigmoid(x) result(y)
        real(sp), intent(in) :: x
        real(sp) :: y
        y = 1.0_sp / (1.0_sp + exp(-x))
    end function sigmoid

    ! ============================================================
    ! Generator Forward
    ! ============================================================
    subroutine generator_forward(z, W1, b1, W2, b2, W3, b3, &
                                  batch_size, z_dim, h1, h2, out_dim, output)
        integer, intent(in) :: batch_size, z_dim, h1, h2, out_dim
        real(sp), intent(in) :: z(batch_size, z_dim)
        real(sp), intent(in) :: W1(z_dim, h1), b1(h1)
        real(sp), intent(in) :: W2(h1, h2), b2(h2)
        real(sp), intent(in) :: W3(h2, out_dim), b3(out_dim)
        real(sp), intent(out) :: output(batch_size, out_dim)
        real(sp) :: hidden1(batch_size, h1)
        real(sp) :: hidden2(batch_size, h2)
        integer :: i, j

        ! Camada 1: Linear + ReLU
        call matmul_2d(z, W1, hidden1, batch_size, z_dim, h1)
        do i = 1, batch_size
            do j = 1, h1
                hidden1(i, j) = max(0.0_sp, hidden1(i, j) + b1(j))
            end do
        end do

        ! Camada 2: Linear + ReLU
        call matmul_2d(hidden1, W2, hidden2, batch_size, h1, h2)
        do i = 1, batch_size
            do j = 1, h2
                hidden2(i, j) = max(0.0_sp, hidden2(i, j) + b2(j))
            end do
        end do

        ! Camada 3: Linear + Tanh
        call matmul_2d(hidden2, W3, output, batch_size, h2, out_dim)
        do i = 1, batch_size
            do j = 1, out_dim
                output(i, j) = tanh(output(i, j) + b3(j))
            end do
        end do
    end subroutine generator_forward

    ! ============================================================
    ! Discriminator Forward
    ! ============================================================
    subroutine discriminator_forward(x, W1, b1, W2, b2, W3, b3, &
                                      batch_size, in_dim, h1, h2, output, use_sigmoid)
        integer, intent(in) :: batch_size, in_dim, h1, h2
        real(sp), intent(in) :: x(batch_size, in_dim)
        real(sp), intent(in) :: W1(in_dim, h1), b1(h1)
        real(sp), intent(in) :: W2(h1, h2), b2(h2)
        real(sp), intent(in) :: W3(h2, 1), b3(1)
        logical, intent(in) :: use_sigmoid
        real(sp), intent(out) :: output(batch_size, 1)
        real(sp) :: hidden1(batch_size, h1)
        real(sp) :: hidden2(batch_size, h2)
        integer :: i, j

        ! Camada 1: Linear + LeakyReLU
        call matmul_2d(x, W1, hidden1, batch_size, in_dim, h1)
        do i = 1, batch_size
            do j = 1, h1
                hidden1(i, j) = leaky_relu(hidden1(i, j) + b1(j), 0.2_sp)
            end do
        end do

        ! Camada 2: Linear + LeakyReLU
        call matmul_2d(hidden1, W2, hidden2, batch_size, h1, h2)
        do i = 1, batch_size
            do j = 1, h2
                hidden2(i, j) = leaky_relu(hidden2(i, j) + b2(j), 0.2_sp)
            end do
        end do

        ! Camada 3: Linear
        call matmul_2d(hidden2, W3, output, batch_size, h2, 1)
        do i = 1, batch_size
            output(i, 1) = output(i, 1) + b3(1)
        end do

        ! Sigmoid opcional
        if (use_sigmoid) then
            do i = 1, batch_size
                output(i, 1) = sigmoid(output(i, 1))
            end do
        end if
    end subroutine discriminator_forward

    ! ============================================================
    ! Gerar ruido
    ! ============================================================
    subroutine sample_noise(z, batch_size, z_dim)
        integer, intent(in) :: batch_size, z_dim
        real(sp), intent(out) :: z(batch_size, z_dim)
        integer :: i, j

        call random_number(z)
        ! Transformar para N(0,1) usando Box-Muller
        do i = 1, batch_size
            do j = 1, z_dim, 2
                if (j + 1 <= z_dim) then
                    z(i, j) = sqrt(-2.0_sp * log(z(i, j) + 1.0e-10_sp)) * cos(2.0_sp * 3.14159_sp * z(i, j+1))
                    z(i, j+1) = sqrt(-2.0_sp * log(z(i, j) + 1.0e-10_sp)) * sin(2.0_sp * 3.14159_sp * z(i, j+1))
                end if
            end do
        end do
    end subroutine sample_noise

    ! ============================================================
    ! GAN Loss
    ! ============================================================
    subroutine compute_gan_loss(real_out, fake_out, batch_size, d_loss, g_loss)
        integer, intent(in) :: batch_size
        real(sp), intent(in) :: real_out(batch_size, 1), fake_out(batch_size, 1)
        real(sp), intent(out) :: d_loss, g_loss
        integer :: i
        real(sp) :: eps

        eps = 1.0e-7_sp

        d_loss = 0.0_sp
        g_loss = 0.0_sp
        do i = 1, batch_size
            d_loss = d_loss - log(max(real_out(i, 1), eps)) &
                     - log(max(1.0_sp - fake_out(i, 1), eps))
            g_loss = g_loss - log(max(fake_out(i, 1), eps))
        end do

        d_loss = d_loss / batch_size
        g_loss = g_loss / batch_size
    end subroutine compute_gan_loss

end module gans_mod

! ============================================================
! Programa principal
! ============================================================
program gan_example
    use gans_mod
    implicit none

    integer, parameter :: z_dim = 8, h_dim = 32, out_dim = 1
    integer, parameter :: batch_size = 64, n_epochs = 1000
    real(sp) :: z(batch_size, z_dim)
    real(sp) :: W1_g(z_dim, h_dim), b1_g(h_dim)
    real(sp) :: W2_g(h_dim, h_dim), b2_g(h_dim)
    real(sp) :: W3_g(h_dim, out_dim), b3_g(out_dim)
    real(sp) :: W1_d(out_dim, h_dim), b1_d(h_dim)
    real(sp) :: W2_d(h_dim, h_dim), b2_d(h_dim)
    real(sp) :: W3_d(h_dim, 1), b3_d(1)
    real(sp) :: real_data(batch_size, out_dim)
    real(sp) :: fake_data(batch_size, out_dim)
    real(sp) :: real_out(batch_size, 1), fake_out(batch_size, 1)
    real(sp) :: d_loss, g_loss
    integer :: epoch, i

    call random_seed()

    ! Inicializar pesos aleatoriamente
    call random_number(W1_g); W1_g = W1_g - 0.5_sp
    call random_number(W2_g); W2_g = W2_g - 0.5_sp
    call random_number(W3_g); W3_g = W3_g - 0.5_sp
    call random_number(W1_d); W1_d = W1_d - 0.5_sp
    call random_number(W2_d); W2_d = W2_d - 0.5_sp
    call random_number(W3_d); W3_d = W3_d - 0.5_sp

    print *, "Treinando GAN para gerar numeros..."

    do epoch = 0, n_epochs - 1
        ! Gerar dados reais (bimodal)
        call random_number(real_data)
        do i = 1, batch_size
            if (real_data(i, 1) < 0.5_sp) then
                real_data(i, 1) = 2.0_sp + real_data(i, 1)
            else
                real_data(i, 1) = 8.0_sp + real_data(i, 1)
            end if
        end do

        ! Gerar fakes
        call sample_noise(z, batch_size, z_dim)
        call generator_forward(z, W1_g, b1_g, W2_g, b2_g, W3_g, b3_g, &
                                batch_size, z_dim, h_dim, h_dim, out_dim, fake_data)

        ! Discriminator forward
        call discriminator_forward(real_data, W1_d, b1_d, W2_d, b2_d, W3_d, b3_d, &
                                    batch_size, out_dim, h_dim, h_dim, real_out, .true.)
        call discriminator_forward(fake_data, W1_d, b1_d, W2_d, b2_d, W3_d, b3_d, &
                                    batch_size, out_dim, h_dim, h_dim, fake_out, .true.)

        ! Calcular loss
        call compute_gan_loss(real_out, fake_out, batch_size, d_loss, g_loss)

        if (mod(epoch, 100) == 0) then
            print *, "Epoch ", epoch, " - D_loss: ", d_loss, " - G_loss: ", g_loss
        end if
    end do

    ! Gerar amostras finais
    print *, ""
    print *, "Amostras geradas:"
    call sample_noise(z, 10, z_dim)
    call generator_forward(z, W1_g, b1_g, W2_g, b2_g, W3_g, b3_g, &
                            10, z_dim, h_dim, h_dim, out_dim, fake_data)
    do i = 1, 10
        print *, "  ", fake_data(i, 1)
    end do

end program gan_example
```

---

## 12. Exemplo: Gerar Numeros

### 12.1 Pipeline Completo

```text
Pipeline de Geracao de Numeros:
==================================

1. Definir Distribuicao Alvo:
   - Bimodal: N(2, 0.5) + N(8, 0.5)
   - 50% de chance de cada pico
   - Objetivo: G aprenda essa distribuicao

2. Arquitetura:
   - Generator:
     * Input: z ∈ R^8 (ruido gaussiano)
     * Hidden: 32, 32 (ReLU)
     * Output: 1 (Tanh -> escalar)
   
   - Discriminator:
     * Input: 1 (escalar)
     * Hidden: 32, 32 (LeakyReLU)
     * Output: 1 (Sigmoid)

3. Treinamento:
   - Batch size: 64
   - Epocas: 1000
   - D: 1 passo por batch
   - G: 1 passo por batch

4. Avaliacao:
   - Gerar 1000 amostras
   - Plotar histograma
   - Comparar com distribuicao real
   - Calcular media e variancia
```

### 12.2 Resultados Esperados

```text
Resultados Esperados:
=======================

Distribuicao Real:
  Media: 5.0
  Variancia: ~9.0
  Histograma: dois picos em 2 e 8

Distribuicao Gerada (apos treinamento):
  Media: ~5.0
  Variancia: ~8.0-10.0
  Histograma: dois picos (pode ser mais nitidos ou suaves)

Metricas:
  - KS test: p > 0.05 (nao rejeitar H0)
  - Wasserstein distance: < 1.0
  - D(x): ~0.5 para todos os x

Problemas comuns:
  - Mode collapse: gera apenas 1 pico
  - Oscilacao: picos mudam de posicao
  - D muito forte: G nao aprende
```

---

## 13. Avaliacao de GANs

### 13.1 Metricas

```text
Metricas de Avaliacao de GANs:
================================

1. FID (Fréchet Inception Distance):
   - Compara distribuicao real vs gerada
   - Usa features do Inception v3
   - Menor = melhor
   - FID = 0: distribuicoes identicas
   - FID < 10: excelencia

2. IS (Inception Score):
   - Qualidade e diversidade
   - IS = E[KL(p(y|x) || p(y))]
   - Maior = melhor
   - IS > 1: bom
   - IS > 3: excelente

3. Precision e Recall:
   - Precision: % de fakes que sao "bons"
   - Recall: % de reais que sao cobertos
   - Balance entre qualidade e diversidade

4. Wasserstein Distance:
   - Distancia entre distribuicoes
   - Menor = melhor
   - Continua e diferenciavel

5. Kernel MMD:
   - Maximum Mean Discrepancy
   - Menor = melhor
   - Mais robusto que KL/JS

6. Visual Inspection:
   - Ainda a metrica mais importante
   - Humans avaliam qualidade visual
   - Diversidade, nitidez, realismo
```

### 13.2 Codigo de Avaliacao

```cpp
// Exemplo de avaliacao
float compute_fid(const std::vector<Tensor>& real_features,
                  const std::vector<Tensor>& fake_features) {
    int dim = real_features[0].shape[0];
    int n = real_features.size();

    // Media real
    Tensor mean_real({dim});
    mean_real.zero();
    for (const auto& f : real_features) {
        for (int i = 0; i < dim; i++) {
            mean_real.at(i) += f.at(i);
        }
    }
    for (int i = 0; i < dim; i++) mean_real.at(i) /= n;

    // Media fake
    Tensor mean_fake({dim});
    mean_fake.zero();
    for (const auto& f : fake_features) {
        for (int i = 0; i < dim; i++) {
            mean_fake.at(i) += f.at(i);
        }
    }
    for (int i = 0; i < dim; i++) mean_fake.at(i) /= n;

    // Covariancia real
    Tensor cov_real({dim, dim});
    cov_real.zero();
    for (const auto& f : real_features) {
        for (int i = 0; i < dim; i++) {
            for (int j = 0; j < dim; j++) {
                cov_real.at(i, j) += (f.at(i) - mean_real.at(i)) *
                                      (f.at(j) - mean_real.at(j));
            }
        }
    }
    for (int i = 0; i < dim; i++) {
        for (int j = 0; j < dim; j++) {
            cov_real.at(i, j) /= (n - 1);
        }
    }

    // Covariancia fake
    Tensor cov_fake({dim, dim});
    cov_fake.zero();
    for (const auto& f : fake_features) {
        for (int i = 0; i < dim; i++) {
            for (int j = 0; j < dim; j++) {
                cov_fake.at(i, j) += (f.at(i) - mean_fake.at(i)) *
                                      (f.at(j) - mean_fake.at(j));
            }
        }
    }
    for (int i = 0; i < dim; i++) {
        for (int j = 0; j < dim; j++) {
            cov_fake.at(i, j) /= (n - 1);
        }
    }

    // FID = ||mean_real - mean_fake||^2 + trace(cov_real + cov_fake - 2*sqrt(cov_real * cov_fake))
    // Simplificado: apenas distancia entre medias
    float dist = 0.0f;
    for (int i = 0; i < dim; i++) {
        float diff = mean_real.at(i) - mean_fake.at(i);
        dist += diff * diff;
    }

    return dist;
}
```

---

## 14. Exercicios

### 14.1 Exercicio Basico

```text
Exercicio 1: Implemente um GAN para gerar numeros 1D
  - Distribuicao: N(0, 1)
  - Generator: z -> 1
  - Discriminator: 1 -> 1
  - Treine por 500 epocas
  - Plote histograma das amostras

Exercicio 2: Implemente WGAN para o mesmo problema
  - Compare estabilidade de treinamento
  - Compare distribuicao gerada
  - Qual e melhor?
```

### 14.2 Exercicio Intermediario

```text
Exercicio 3: Implemente Conditional GAN
  - 3 distribuicoes: N(-3, 1), N(0, 1), N(3, 1)
  - Label: 0, 1, 2
  - G: (z, label) -> x
  - D: (x, label) -> real/fake
  - Gere amostras de cada classe

Exercicio 4: Mode collapse
  - Crie scenario que cause mode collapse
  - Implemente minibatch discrimination
  - Verifique se melhora diversidade
```

### 14.3 Exercicio Avancado

```text
Exercicio 5: GAN para imagens (MNIST)
  - Generator: z(100) -> 28x28
  - Discriminator: 28x28 -> 1
  - Treine por 10 epocas
  - Avalie com FID

Exercicio 6: Comparacao de losses
  - GAN original vs WGAN vs WGAN-GP
  - Mesma arquitetura
  - Compare: estabilidade, velocidade, qualidade
  - Qual e melhor e por que?
```

---

## 15. Resumo

### 15.1 Conceitos-Chave

```text
Conceitos Essenciais de GANs:
================================

1. Arquitetura:
   - Generator: z -> G(z) (ruido -> dado)
   - Discriminator: x -> D(x) (dado -> real/fake)
   - Treinamento adversarial

2. Funcao de Perda:
   - Minimax: min_G max_D V(D, G)
   - Non-saturating: max_G log D(G(z))
   - Wasserstein: E[C(real)] - E[C(fake)]

3. Training Dynamics:
   - D e G treinados alternadamente
   - Equilibrio: D(x) = 0.5 para todo x
   - Balance e dificil

4. Mode Collapse:
   - G gera poucos modos
   - Solucoes: minibatch, WGAN, label smoothing

5. WGAN:
   - Loss mais estavel
   - Gradient penalty
   - Melhor para treinamento

6. Conditional GAN:
   - Geracao condicionada
   - G: (z, y) -> G(z, y)
   - Controle sobre o que gerar

7. Avaliacao:
   - FID, IS, Precision/Recall
   - Visual inspection ainda e chave
```

### 15.2 Quando Usar

```text
Quando Usar GANs:
===================

USE GANs quando:
  + Precisa gerar dados realistas
  + Tem dados para treinar
  + Qualidade visual importa
  + GeraSamples rapidos

NAO use GANs quando:
  - Dados sao muito complexos (use Diffusion)
  - Precisa de density estimation (use VAE/Flow)
  - Treinamento precisa ser estavel (use VAE)
  - Dados sao tabulares (use CTGAN ou VAE)

Alternativas:
  - VAE: mais estavel, menos nitido
  - Diffusion: melhor qualidade, mais lento
  - Flow: density estimation, flexivel
  - Autoregressive: preciso, lento
```

---

## 16. Referencias

```text
Referencias:
==============

1. Goodfellow et al., "Generative Adversarial Nets" (2014)

2. Arjovsky et al., "Wasserstein GAN" (2017)

3. Gulrajani et al., "Improved Training of Wasserstein GANs" (2017)

4. Mirza and Osindero, "Conditional Generative Adversarial Nets" (2014)

5. Salimans et al., "Improved Techniques for Training GANs" (2016)

6. Karras et al., "Progressive Growing of GANs" (2017)

7. Karras et al., "A Style-Based Generator Architecture for GANs" (2018)
```

---

## 16. GANs Modernos

### 16.1 StyleGAN

```text
StyleGAN (NVIDIA):
====================

Arquitetura avancada para geracao de faces.

Inovacoes:
  1. Mapping Network:
     - z -> w (latent space estilizado)
     - 8 camadas MLP
     - Desacopla atributos

  2. AdaIN (Adaptive Instance Normalization):
     - Injeta estilo em cada camada
     - Controle fino de atributos

  3. Progressive Growing:
     - Treina de baixa para alta resolucao
     - 4x4 -> 8x8 -> ... -> 1024x1024
     - Mais estavel

  4. Noise Injection:
     - Ruido por pixel
     - Detalhes estocasticos (cabelo, pele)

Resultados:
  - Faces 1024x1024 fotorealisticas
  - Controle de idade, genero, etnia
  - Interpolacao suave entre faces
  - StyleGAN2, StyleGAN3
```

### 16.2 BigGAN

```text
BigGAN (DeepMind):
====================

Escalabilidade para ImageNet.

Arquitetura:
  - ResNet-based generator
  - Class-conditional
  - Batch size grande (2048)
  - Precisao mista

Truques:
  1. Truncation Trick:
     - z ~ N(0, I), mas truncado em [-psi, psi]
     - psi < 1: menor variancia, mais nitido
     - psi > 1: maior variancia, mais artefatos

  2. Class-conditional:
     - y (label) injetado via class-embedding
     - Gera imagem de classe especifica

  3. Self-Attention:
     - Camada de attention em 64x64
     - Captura dependencias longas

Resultados:
  - FID: 6.95 (state-of-the-art na epoca)
  - IS: 9.22
  - 128x128, 256x256, 512x512
```

### 16.3 Diffusion Models

```text
Diffusion Models (DDPM):
==========================

Alternativa a GANs com melhor qualidade.

Ideia:
  1. Forward: adicionar ruido gradualmente
     x_t = sqrt(1 - beta_t) * x_{t-1} + sqrt(beta_t) * noise
  
  2. Reverse: aprender a remover ruido
     x_{t-1} = mu_theta(x_t, t) + sigma_t * noise

Treinamento:
  - Predizer ruido em cada passo
  - Loss: ||epsilon - epsilon_theta(x_t, t)||^2
  - T passos (ex: T=1000)

Amostragem:
  - Comecar com ruido puro
  - Iterativamente remover ruido
  - T passos (lento)

Vantagens vs GANs:
  + Melhor qualidade (FID menor)
  + Mais estavel (sem adversarial)
  + Sem mode collapse
  + Density estimation

Desvantagens:
  - Lento (1000 passos)
  - Mais lento que GAN

Solucoes para velocidade:
  - DDIM: 50 passos
  - Consistency Models: 1-2 passos
  - Latent Diffusion: espaço latente
  - SDXL, DALL-E 3, Midjourney
```

---

## 17. GANs para Dados Tabulares

### 17.1 CTGAN

```text
CTGAN (Conditional Tabular GAN):
==================================

Problema: GANs nao funcionam bem com dados tabulares.

Solucos do CTGAN:
  1. Conditional Generator:
     - G: (z, condition) -> row
     - Condition: coluna categorica selecionada
     - Mais diversidade

  2. Mode-specific Normalization:
     - Dados continuos: GMM (Gaussian Mixture)
     - Cada modo normalizado separadamente
     - Evita mode collapse

  3. PacGAN:
     - Discriminator recebe N amostras juntas
     - Detecta colapso de modos
     - Mais robusto

  4. Training by Batching:
     - Batches por coluna condicionada
     - Balance de categorias
     - Evita viés

Arquitetura:
  - Generator: MLP com BatchNorm
  - Discriminator: MLP com Dropout
  - Otimizador: Adam
  - Loss: vanilla GAN
```

### 17.2 Privacidade

```text
Privacidade em GANs Tabulares:
================================

Differential Privacy:
  - Adicionar ruido aos gradientes
  - epsilon-DP: bound na informacao vazada
  - epsilon < 1: forte
  - epsilon > 10: fraco

DP-SGD para GANs:
  - Clip gradientes por sample
  - Adicionar ruido gaussiano
  - Trade-off: privacidade vs qualidade

Aplicacoes:
  - Dados medicos (HIPAA)
  - Dados financeiros (GDPR)
  - Dados pessoais (LGPD)

Exemplo:
  - Dados reais: 1000 pacientes
  - GAN treinada com DP
  - Epsilon = 1.0
  - Dados sinteticos gerados
  - Qualidade menor mas privacidade garantida
```

---

## 18. GANs e Etica

### 18.1 Deepfakes

```text
Deepfakes:
============

Uso malicioso de GANs:
  1. Face Swapping:
     - Trocar rostos em videos
     - Politica, fraude, vinganca
     - Dificil de detectar

  2. Voice Cloning:
     - Clonar voz de pessoa
     - Fraude telefonica
     - Phishing avancado

  3. Text Generation:
     - Gerar textos falsos
     - Noticias falsas
     - Propaganda

Defesas:
  - Deepfake detection models
  - Watermarking
  - Blockchain para autenticidade
  - Educacao midia
```

### 18.2 Viés e Equidade

```text
Viés em GANs:
===============

Problemas:
  1. Dados de treino enviesados:
     - GAN aprende viés
     - Gera dados enviesados
     - Reforça desigualdade

  2. Underrepresentation:
     - Minorias menos presentes
     - GAN gera menos dessas classes
     - Viés amplificado

  3. Fairness:
     - GAN deve gerar dados justos
     - Mesma qualidade para todos grupos
     - Metricas de equidade

Solucoes:
  - Dados balanceados
  - Fairness-aware training
  - Audit de saidas
  - Diversidade de equipe
```

---

## 19. Casos de Estudo

### 19.1 Medicina

```text
GANs em Medicina:
====================

1. Geracao de Imagens Medicas:
   - Radiografias sinteticas
   - Aumentar dataset
   - Privacidade de pacientes

2. Augmentation para Deteccao:
   - Tumores raros
   - Gerar mais exemplos
   - Melhorar classificadores

3. Sintese de Dados:
   - EHR (Electronic Health Records)
   - Dados tabulares sinteticos
   - Treinar modelos sem vazar dados

Resultados:
   - Radiografias: FID < 10
   - Melhoria: 5-15% em classificacao
   - Privacidade: HIPAA compliant
```

### 19.2 Artes e Design

```text
GANs em Artes:
================

1. Geracao de Arte:
   - StyleGAN para faces
   - BigGAN para objetos
   - DALL-E para texto->imagem

2. Super-Resolution:
   - SRGAN, ESRGAN
   - Imagens de baixa->alta resolucao
   - Restauracao de fotos antigas

3. Inpainting:
   - Preencher regioes faltantes
   - Remover objetos
   - Restaurar fotos danificadas

4. Style Transfer:
   - Mover estilo entre imagens
   - Neural style transfer
   - Controle fino de estilo

Exemplos:
   - Obra vendida por $432k (Edmond de Belamy)
   - NVIDIA GauGAN: desenho->foto
   - Midjourney, Stable Diffusion
```

---

## 20. Exercicios Complementares

### 20.1 Exercicio de Mode Collapse

```text
Exercicio: Detectar e Corrigir Mode Collapse
==============================================

Cenário:
  - GAN treinando em MNIST
  - Apos 100 epocas, gera apenas digitos 1 e 7

Tarefa:
  1. Plote distribuicao de classes geradas
  2. Identifique quais modos faltam
  3. Implemente uma solucao:
     - Opcao A: Minibatch Discrimination
     - Opcao B: Unrolled GAN
     - Opcao C: Feature Matching
  4. Compare resultados

Metricas:
  - Entropia da distribuicao de classes
  - Coverage (quantos modos sao cobertos)
  - FID por classe
```

### 20.2 Exercicio de Avaliacao

```text
Exercicio: Avaliar GAN com Metricas Reais
==========================================

Tarefa:
  1. Treine GAN em MNIST
  2. Implemente:
     - FID (Fréchet Inception Distance)
     - IS (Inception Score)
     - Precision e Recall
  3. Compare com VAE
  4. Analise correlacao com qualidade visual

Dataset:
  - MNIST (facil)
  - Fashion-MNIST (medio)
  - CIFAR-10 (dificil)

Esperado:
  - FID: < 50 para MNIST
  - IS: > 5 para MNIST
  - Precision/Recall balanceados
```

---

## 21. Glossario

```text
Glossario de GANs:
====================

GAN: Generative Adversarial Network.

Generator: Rede que gera dados sinteticos.

Discriminator: Rede que classifica real vs fake.

Mode Collapse: G gera poucos modos.

Minimax Game: Jogo adversarial G vs D.

Wasserstein Distance: Distancia entre distribuicoes.

Gradient Penalty: Penalidade de gradiente para WGAN.

Conditional GAN: Geracao condicionada.

StyleGAN: GAN estilizado (NVIDIA).

Diffusion Model: Geracao por remocao de ruido.

FID: Fréchet Inception Distance.

IS: Inception Score.

CTGAN: Conditional Tabular GAN.

Deepfake: Uso malicioso de geracao.

Adversarial Training: Treinar contra adversarios.

Lipschitz Constraint: Limitar inclinacao de D.

Mode Seeking: Diversidade vs qualidade.

Data Augmentation: Aumentar dados sinteticamente.
```

---

## 22. Implementacao Detalhada: Pipeline Completo

### 22.1 Preparacao de Dados

```text
Pipeline de Preparacao:
========================

1. Carregamento:
   - Ler dados do disco
   - Validar formato
   - Contar estatisticas basicas

2. Preprocessamento:
   - Normalizacao: [0, 1] ou [-1, 1]
   - Para imagens: / 127.5 - 1 (Tanh range)
   - Para numericos: StandardScaler

3. Batching:
   - Embaralhar dados
   - Dividir em batches
   - Batch size: 32, 64, 128, 256
   - Drop last: remover batch incompleto

4. Data Augmentation (imagens):
   - Flip horizontal
   - Rotacao leve (±15 graus)
   - Crop aleatorio
   - Color jitter

5. Validacao:
   - Split: 80% treino, 20% validacao
   - Nao usar teste para treinar
   - Manter distribuicao consistente
```

### 22.2 Hiperparametros

```text
Hiperparametros para GANs:
=============================

Generator:
  - z_dim: 64-128 (ruido)
  - hidden: 256-1024
  - activation: ReLU, LeakyReLU
  - BatchNorm: sim (exceto output)
  - Output: Tanh (imagens) ou Linear (tabular)

Discriminator:
  - hidden: 256-1024
  - activation: LeakyReLU(0.2)
  - Dropout: 0.3 (opcional)
  - BatchNorm: NAO (instabiliza)
  - Output: Sigmoid (GAN) ou Linear (WGAN)

Training:
  - Optimizer: Adam (lr=0.0002, beta1=0.5)
  - n_critic: 1-5 (D por G)
  - Label smoothing: 0.9 em vez de 1.0
  - Noise: adicionar ruido nos labels

WGAN-GP:
  - lambda_gp: 10.0
  - n_critic: 5
  - Optimizer: Adam (lr=0.0001, beta1=0.0, beta2=0.9)
  - Nao usar BatchNorm em D

Grid Search:
  - z_dim: [32, 64, 128]
  - hidden: [128, 256, 512]
  - lr: [0.0001, 0.0002, 0.0005]
  - batch: [32, 64, 128]
```

### 22.3 Monitoring e Debugging

```text
Monitoramento de Treinamento:
================================

Metricas para logar:
  1. d_loss_real: loss de D em dados reais
  2. d_loss_fake: loss de D em dados fakes
  3. g_loss: loss de G
  4. d(x): media de D em dados reais (ideal: 0.5)
  5. d(g(z)): media de D em dados fakes (ideal: 0.5)
  6. FID: qualidade (se computacionalmente viavel)

Sinais de problemas:
  - d_loss -> 0: D muito forte, reduzir n_critic
  - d_loss -> inf: D muito fraco, reduzir lr de D
  - g_loss -> 0: G muito forte, verificar D
  - d(x) >> 0.5: D nao aprendeu
  - d(x) << 0.5: D muito confiante

Debugging:
  1. Treinar D sozinho (deve convergir)
  2. Treinar G com D fixo (deve melhorar)
  3. Visualizar amostras a cada 100 epocas
  4. Plotar distribuicao de scores
  5. Verificar gradients (norma, NaN)
```

---

## 23. GANs em Producao

### 23.1 Deploy

```text
Deploy de GANs:
=================

1. Exportar modelo:
   - Salvar pesos (PTH, ONNX)
   - Script de inferencia
   - Dependencias minimal

2. Serving:
   - FastAPI, Flask, gRPC
   - Batch inference
   - Async processing
   - Cache de latencia

3. Escalabilidade:
   - Horizontal: multi-GPU
   - Load balancing
   - Auto-scaling
   - Queue system

4. Monitoramento:
   - Latencia de geracao
   - Qualidade (FID online)
   - Uso de memoria
   - Erros e timeouts

5. Seguranca:
   - Rate limiting
   - Input validation
   - Watermarking
   - Audit log
```

### 23.2 Otimizacao

```text
Otimizacao de GANs para Producao:
====================================

1. Model Distillation:
   - Treinar modelo menor para imitar maior
   - Reduzir parametros 4-10x
   - Perda minima de qualidade

2. Quantization:
   - INT8: 4x menos memoria
   - FP16: 2x menos memoria
   - Perda: < 1% em FID

3. Pruning:
   - Remover neuronios nao importantes
   - 30-50% reducao
   - Fine-tune apos pruning

4. TensorRT:
   - Otimizacao automatica
   - Kernel fusion
   - 2-5x mais rapido

5. ONNX Runtime:
   - Multi-platform
   - CPU e GPU
   - Otimizacoes especificas
```

---

## 24. Exercicios Finais

### 24.1 Projeto Completo

```text
Projeto: GAN para Geracao de Numeros
======================================

Objetivo:
  - Implemente GAN do zero
  - Gere numeros de distribuicao bimodal
  - Avalie qualidade

Etapas:
  1. Implementar Generator (3 camadas)
  2. Implementar Discriminator (3 camadas)
  3. Implementar training loop
  4. Treinar 2000 epocas
  5. Gerar 1000 amostras
  6. Plotar histograma
  7. Calcular metricas (media, variancia)
  8. Comparar com distribuicao real

Metricas de sucesso:
  - Media gerada: 4.5-5.5 (real: 5.0)
  - Variancia: 7.0-11.0 (real: ~9.0)
  - Histograma: dois picos visiveis
  - D(x): 0.4-0.6 (equilibrio)
```

### 24.2 Desafio

```text
Desafio: WGAN-GP vs GAN
==========================

Comparacao:
  1. Treine GAN normal
  2. Treine WGAN-GP
  3. Compare:
     - Estabilidade (loss ao longo do treino)
     - Qualidade (histograma)
     - Velocidade (tempo total)
     - Mode coverage (modos gerados)

Relatorio:
  - Grafico de losses
  - Histogramas sobrepostos
  - Tabela de metricas
  - Analise qualitativa
  - Conclusao: qual e melhor?
```

---

## 25. Referencias Complementares

```text
Referencias Adicionais:
========================

8. Karras et al., "Analyzing and Improving the Image Quality of StyleGAN" (2019)

9. Brock et al., "Large Scale GAN Training for High Fidelity Natural Image Synthesis" (2018)

10. Ho et al., "Denoising Diffusion Probabilistic Models" (2020)

11. Song et al., "Denoising Diffusion Implicit Models" (2020)

12. Zhang et al., "CTGAN: Conditional Tabular GAN" (2019)

13. Xu et al., "Synthesizing Tabular Data using Generative Adversarial Networks" (2019)

14. Creswell et al., "Adversarial Examples in Deep Learning: Characterization and Divergence" (2018)

15. Tolosana et al., "DeepFakes and Beyond: A Survey of Face Manipulation and Fake Detection" (2020)
```

---

Fim do Capitulo 15 — Generative Adversarial Networks (GANs)
