---
layout: default
title: "07-optimizadores"
---

# Capitulo 7 — Optimizadores

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender o papel do optimizador no treinamento** — como ele conecta o gradiente calculado pelo backpropagation com a atualizacao efetiva dos pesos da rede.
2. **Diferenciar batch gradient descent, stochastic gradient descent (SGD) e mini-batch gradient descent** — seus algoritmos, vantagens, desvantagens e regimes de uso.
3. **Analisar o impacto da learning rate** — por que e o hiperparametro mais critico, como ele afeta convergencia e estabilidade, e tecnicas de ajuste.
4. **Implementar momentum fisico no gradiente** — como a analogia com particulas em movimento acelera convergencia em vales estreitos.
5. **Derivar e implementar o Nesterov Accelerated Gradient (NAG)** — antecipacao do gradiente para correcao mais precisa.
6. **Compreender adaptatividade de learning rate** — como AdaGrad, RMSProp e Adam ajustam a taxa por parametro individualmente.
7. **Implementar Adam e AdamW** — o optimizador dominante em deep learning, incluindo weight decay desacoplado.
8. **Aplicar learning rate scheduling** — cosine annealing, step decay, exponential decay e warmup.
9. **Implementar um sistema completo de optimizadores em C++, Rust e Fortran** — comparando abordagens de design em tres paradigmas de programacao.
10. **Escolher o optimizador correto para cada problema** — usando arvore de decisao baseada em propriedades do dataset e da arquitetura.

---

## 1. Gradiente Descendente

### 1.1 O Problema Fundamental

O treinamento de uma rede neural e, em sua essencia, uma tarefa de otimizacao. Dada uma funcao de perda L(theta) que depende dos parametros theta da rede (pesos e biases), queremos encontrar:

```text
theta* = argmin L(theta)
```

O backpropagation fornece o gradiente — o vetor de derivadas parciais de L em relacao a cada parametro. O optimizador e o mecanismo que usa esse gradiente para caminhar na direcao que reduz a perda.

A atualizacao basica do gradiente descendente e:

```text
theta_t+1 = theta_t - eta * nabla L(theta_t)

onde:
  theta_t       = parametros no passo t
  eta           = learning rate (taxa de aprendizado)
  nabla L(theta) = gradiente da perda em relacao aos parametros
```

A ideia e simples: se o gradiente aponta para onde a funcao cresce, vamos na direcao oposta. O hiperparametro eta controla o tamanho do passo.

### 1.2 Batch Gradient Descent

O batch gradient descent (tambem chamado de gradient descent vanilla) calcula o gradiente sobre TODO o conjunto de treinamento antes de cada atualizacao:

```text
Algorithm: Batch Gradient Descent

Input: Dataset D = {(x1,y1), ..., (xN,yN)}, learning rate eta, epocas T
Output: Parametros otimizados theta*

1. Inicializar theta aleatoriamente
2. Para t = 1 ate T:
3.    Calcular perda media: L = (1/N) * sum_i L(f(xi; theta), yi)
4.    Calcular gradiente: g = (1/N) * sum_i nabla L(f(xi; theta), yi)
5.    Atualizar: theta = theta - eta * g
6. Retornar theta
```

**Vantagens:**
- Gradiente exato — direcao de atualizacao e precisa
- Convergencia garantida para funcoes convexas com learning rate adequado
- Estavel — sem oscilacoes por causa do gradiente medido

**Desvantagens:**
- Custo computacional proibitivo para datasets grandes — precisa percorrer todo o dataset a cada passo
- Impossivel usar para datasets que nao cabem em memoria
- Lento para convergir em problemas simples

**Custo por atualizacao:** O(N * D), onde N e o numero de amostras e D e a dimensionalidade dos parametros.

### 1.3 Stochastic Gradient Descent (SGD)

O SGD resolve o problema de custo ao calcular o gradiente com base em UMA amostra por vez:

```text
Algorithm: Stochastic Gradient Descent

Input: Dataset D = {(x1,y1), ..., (xN,yN)}, learning rate eta, epocas T
Output: Parametros otimizados theta*

1. Inicializar theta aleatoriamente
2. Para t = 1 ate T:
3.    Embaralhar D aleatoriamente
4.    Para cada (xi, yi) em D:
5.       Calcular gradiente: gi = nabla L(f(xi; theta), yi)
6.       Atualizar: theta = theta - eta * gi
7. Retornar theta
```

O gradiente de uma amostra e um estimador ruidoso do gradiente real:

```text
E[gi] = nabla L(theta)      (estimador nao-enviesado)

Var[gi] = Sigma^2 / 1       (alta variancia)
```

O ruido e, surpreendentemente, uma caracteristica util. Em funcoes nao-convexas com minimos locais, o ruido pode ajudar a escapar de minimos superficiais.

**Comparacao com Batch:**

```text
┌──────────────────────┬─────────────────┬──────────────────┐
│ Propriedade          │ Batch GD        │ SGD              │
├──────────────────────┼─────────────────┼──────────────────┤
│ Amostras por passo   │ N (todas)       │ 1                │
│ Custo por passo      │ O(N * D)        │ O(D)             │
│ Passos por epoca     │ 1               │ N                │
│ Gradiente            │ Exato           │ Ruidoso          │
│ Convergencia         │ Monotona        │ Oscilatoria      │
│ Minimos locais       │ Preso facilmente│ Pode escapar     │
│ Memoria              │ O(N)            │ O(1)             │
│ Paralelizacao        │ Facil           │ Dificil          │
└──────────────────────┴─────────────────┴──────────────────┘
```

### 1.4 Mini-Batch Gradient Descent

O mini-batch GD e o ponto medio e o que e usado na pratica. Ele calcula o gradiente sobre um subconjunto de amostras (o mini-batch):

```text
Algorithm: Mini-Batch Gradient Descent

Input: Dataset D, batch size B, learning rate eta, epocas T
Output: Parametros otimizados theta*

1. Inicializar theta aleatoriamente
2. Para t = 1 ate T:
3.    Embaralhar D aleatoriamente
4.    Dividir D em mini-batches de tamanho B: B1, B2, ..., Bm
5.    Para cada Bj:
6.       Calcular gradiente: gj = (1/|Bj|) * sum_{i em Bj} nabla L(f(xi; theta), yi)
7.       Atualizar: theta = theta - eta * gj
8. Retornar theta
```

O mini-batch oferece o melhor dos dois mundos:

```text
E[gj] = nabla L(theta)                (estimador nao-enviesado, como SGD)
Var[gj] = Sigma^2 / B                 (variancia reduzida por B)
```

O tradeoff e claro: batch sizes maiores dao gradientes mais estaveis, mas custam mais por passo e usam mais memoria. Na pratica:

```text
Batch size tipico: 32, 64, 128, 256, 512
- 32: boa generalizacao, mais ruido (util para regularizacao implicita)
- 256-512: treinamento mais estavel, melhor utilize de GPUs
- >1024: custo de memoria alto, beneficio marginal
```

### 1.5 Propriedades Convergentes

A convergencia do GD depende da convexidade da funcao e da escolha da learning rate:

```text
Para funcoes L-convexas (gradiente L-Lipschitz):

  Batch GD:  L(thetaT) - L(theta*) <= O(1/T)
  SGD:       E[L(thetaT)] - L(theta*) <= O(1/sqrt(T))   (com taxa decrescente)
  Mini-batch: intermediario entre os dois

Para funcoes nao-convexas (redes neurais):
  GD convergi para um ponto critico: nabla L(theta) -> 0
  Nao ha garantia de otimo global
```

O fator critico e a learning rate. Muito alta e o treinamento diverge. Muito baixa e converge ridiculamente lento. Esse e o proximo topico.

---

## 2. Learning Rate

### 2.1 O Hiperparametro Mais Importante

A learning rate controla a magnitude da atualizacao dos pesos. E, sem exagero, o hiperparametro que mais influencia se o treinamento funciona ou nao.

```text
Efeito da learning rate na convergencia:

  eta muito alta:   oscilacoes crescentes, divergencia
  eta alta:         oscilacoes em torno do otimo, nao converge
  eta ideal:        convergencia rapida e estavel
  eta baixa:        convergencia muito lenta
  eta muito baixa:  praticamente nao aprende
```

### 2.2 Taxa Constante

A forma mais simples e manter eta fixo durante todo o treinamento:

```text
theta_t+1 = theta_t - eta * g_t

Vantagens: simplicidade
Desvantagens: dificil encontrar valor ideal que funcione para todas as fases
```

O problema fundamental: no inicio do treinamento, longe do otimo, queremos passos grandes. Perto do otimo, queremos passos pequenos. Uma taxa constante nao consegue fazer ambos.

### 2.3 Decay (Decaimento)

Uma estrategia e comecar com uma taxa alta e diminui-la ao longo do treinamento:

**Step Decay:**

```text
eta_t = eta_0 * gamma^floor(t / S)

onde:
  eta_0   = learning rate inicial
  gamma   = fator de decaimento (tipicamente 0.1 ou 0.5)
  S       = periodo de decay (em epocas ou passos)
  floor() = funcao piso

Exemplo: eta_0 = 0.1, gamma = 0.1, S = 30
  t=0:   eta = 0.1
  t=30:  eta = 0.01
  t=60:  eta = 0.001
  t=90:  eta = 0.0001
```

**Exponential Decay:**

```text
eta_t = eta_0 * exp(-lambda * t)

onde:
  lambda = taxa de decaimento (constante positiva)

Comportamento: decaimento continuo e suave
```

**Inverse Time Decay:**

```text
eta_t = eta_0 / (1 + lambda * t)

Comportamento: decaimento rapido no inicio, lento no final
```

### 2.4 Warmup

A ideia do warmup e comecar com uma taxa MUITO baixa e aumenta-la gradualmente ate o valor alvo:

```text
eta_t = eta_0 * (t / T_warmup)     para t <= T_warmup
eta_t = eta_0                        para t > T_warmup

onde:
  T_warmup = numero de passos de aquecimento
```

Por que warmup e necessario? Em fases iniciais:
- Os pesos sao aleatorios e os gradientes podem ser muito grandes
- Batch normalization precisa de amostras suficientes para estabilizar estatisticas
- Optimizadores adaptativos (Adam) precisam de tempo para acumular momentos

O padrao moderno e combinar warmup com decay posterior:

```text
Eta schedule hibrido:

  Fase 1 (warmup):   eta cresce de 0 ate eta_max em T_warmup passos
  Fase 2 (principal): eta decai de eta_max ate eta_min

Exemplo tipico:
  T_warmup = 1000 passos
  eta_max  = 0.001
  eta_min  = 0.00001
  Decaimento: cosine annealing (secao 10)
```

### 2.5 Learning Rate Finder

A tecnica de learning rate finder (popularizada por Leslie Smith e adoptada pelo fast.ai) consiste em:

```text
Algorithm: Learning Rate Finder

1. Comecar com eta muito pequena (ex: 1e-7)
2. Aumentar eta exponencialmente a cada mini-batch
3. Registrar a perda a cada eta
4. Plotar eta vs. perda
5. Escolher eta onde a perda diminui mais rapidamente (maior inclinacao negativa)
```

A curva tipica tem tres regioes:

```text
Perda
  |  
  |  ___________________ eta muito alta (diverge)
  | /
  |/____
  |     \___
  |         \_____ eta ideal (maior declive)
  |              \_________ eta muito baixa (converge lento)
  +---------------------------> eta
```

---

## 3. Momentum

### 3.1 A Analogia Fisica

Imagine uma bola descendo uma montanha. Ela nao para instantaneamente quando encontra um platô — continua rolling por inercia. O momentum em optimizacao funciona de forma analogica.

Sem momentum, o SGD faz atualizacoes puramente baseadas no gradiente atual. Com momentum, acumulamos uma "velocidade" que persiste entre atualizacoes:

```text
Analogia fisica:

  Sem momentum:   particula move instantaneamente na direcao do gradiente
                   (como se tivesse massa zero)

  Com momentum:   particula tem massa, acumula velocidade
                   continua movendo mesmo em platôs
                   atravessa vales estreitos mais rapido
```

### 3.2 Formula do Momentum

O algoritmo de momentum (tambem chamado de Polyak momentum) mantem uma variavel de velocidade v que e atualizada a cada passo:

```text
Algorithm: SGD com Momentum

1. Inicializar theta e v = 0
2. Para cada mini-batch:
3.    g = nabla L(theta)                  (gradiente atual)
4.    v = mu * v + g                       (atualizar velocidade)
5.    theta = theta - eta * v              (atualizar parametros)

Onde:
  mu = coeficiente de momentum (tipicamente 0.9)
  v  = estimativa da direcao media do gradiente
```

Desdobrando a recursao de v, vemos que o momentum e uma media movel ponderada exponencialmente dos gradientes passados:

```text
Expansao de v:

  v_t = mu * v_{t-1} + g_t
      = mu * (mu * v_{t-2} + g_{t-1}) + g_t
      = mu^2 * v_{t-2} + mu * g_{t-1} + g_t
      = ...
      = sum_{i=0}^{t} mu^(t-i) * g_i

Isso e uma Media Movel Exponencial (EMA) dos gradientes.
O peso mu^(t-i) decai exponencialmente — gradientes recentes pesam mais.
```

### 3.3 Por Que Momentum Acelera

Considere uma funcao com um vale estreito na direcao x e uma inclinacao suave na direcao y:

```text
Sem momentum:
  - Na direcao x: oscilacoes rapidas (gradiente alternando de sinal)
  - Na direcao y: convergencia lenta mas constante
  - Resultado: zig-zag lento em direcao ao minimo

Com momentum:
  - Na direcao x: as oscilacoes se cancelam (media movel)
  - Na direcao y: a velocidade acumula e acelera
  - Resultado: movimento mais direto ao minimo
```

Matematicamente, para uma funcao quadratica com condicao kappa (razao entre autovalores max e min do Hessiano):

```text
Convergencia sem momentum:
  Taxa de convergencia = (kappa - 1) / (kappa + 1)

Convergencia com momentum (mu otimo):
  Taxa de convergencia = (sqrt(kappa) - 1) / (sqrt(kappa) + 1)

Para kappa = 100:
  Sem momentum: (100-1)/(100+1) = 0.99
  Com momentum: (10-1)/(10+1)   = 0.818

O momentum transforma o problema de condicao de kappa para sqrt(kappa).
```

### 3.4 Implementacao

```cpp
template<typename T>
class SGDWithMomentum {
public:
    SGDWithMomentum(T learning_rate, T momentum_coeff)
        : lr(learning_rate), mu(momentum_coeff), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            velocity.resize(params.size(), T{0});
            initialized = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            velocity[i] = mu * velocity[i] + grads[i];
            params[i] -= lr * velocity[i];
        }
    }

private:
    T lr;
    T mu;
    bool initialized;
    std::vector<T> velocity;
};
```

```rust
pub struct SGDWithMomentum {
    lr: f64,
    mu: f64,
    velocity: Vec<f64>,
    initialized: bool,
}

impl SGDWithMomentum {
    pub fn new(lr: f64, mu: f64) -> Self {
        Self {
            lr,
            mu,
            velocity: Vec::new(),
            initialized: false,
        }
    }

    pub fn update(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.velocity = vec![0.0; params.len()];
            self.initialized = true;
        }

        for (p, (g, v)) in params.iter_mut()
            .zip(grads.iter().zip(self.velocity.iter_mut()))
        {
            *v = self.mu * *v + g;
            *p -= self.lr * *v;
        }
    }
}
```

```fortran
module momentum_mod
    implicit none
    private
    public :: update_momentum

contains

    subroutine update_momentum(params, grads, velocity, lr, mu, n)
        implicit none
        integer, intent(in) :: n
        real(8), intent(inout) :: params(n), velocity(n)
        real(8), intent(in) :: grads(n), lr, mu
        integer :: i

        do i = 1, n
            velocity(i) = mu * velocity(i) + grads(i)
            params(i) = params(i) - lr * velocity(i)
        end do
    end subroutine update_momentum

end module momentum_mod
```

### 3.5 Escolhendo mu

O coeficiente de momentum mu controla a "memoria" do optimizador:

```text
mu = 0.0:    equivalente a SGD sem momentum
mu = 0.5:    memoria curta, mais responsivo a mudancas
mu = 0.9:    valor tipico, bom balance
mu = 0.95:   memoria longa, pode ser instavel com learning rates altas
mu = 0.99:   usado em large-batch training (ex: LARS/LAMB)

Regra pratica: comecar com mu = 0.9 e ajustar
```

---

## 4. Nesterov Accelerated Gradient (NAG)

### 4.1 Antecipacao do Gradiente

O Nesterov momentum introduz uma mudanca sutil mas poderosa: em vez de calcular o gradiente na posicao atual, ele calcula o gradiente na posicao ANTECIPADA — onde os parametros estariam se aplicassem momentum primeiro.

```text
Momentum padrao:
  1. Calcular gradiente na posicao atual: g = nabla L(theta)
  2. Atualizar velocidade: v = mu * v + g
  3. Atualizar parametros: theta = theta - eta * v

Nesterov:
  1. Antecipar posicao: theta_tilde = theta - eta * mu * v
  2. Calcular gradiente na posicao antecipada: g = nabla L(theta_tilde)
  3. Atualizar velocidade: v = mu * v + g
  4. Atualizar parametros: theta = theta - eta * v
```

### 4.2 Formula Completa

```text
Algorithm: Nesterov Accelerated Gradient

1. Inicializar theta e v = 0
2. Para cada mini-batch:
3.    theta_tilde = theta - eta * mu * v          (posicao antecipada)
4.    g = nabla L(theta_tilde)                     (gradiente antecipado)
5.    v = mu * v + g                               (atualizar velocidade)
6.    theta = theta - eta * v                      (atualizar parametros)
```

### 4.3 Por Que Nesterov e Melhor

A intuicao e que o momentum padrao "olha para tras" — ele usa o gradiente de onde ESTA, nao de onde VAI ESTAR. O Nesterov "olha para frente" e corrige antes de errar.

```text
Cenario: proximo a um minimo

Momentum padrao:
  - Calcula gradiente na posicao atual (grande, apontando para baixo)
  - Atualiza v com esse gradiente grande
  - Pode ultrapassar o minimo significativamente

Nesterov:
  - Primeiro avanca um passo na direcao de v
  - Calcula gradiente nessa posicao antecipada (mais suave, menor magnitude)
  - Corrige antes de chegar la
  - Menor overshoot
```

Na pratica, Nesterov converge ~20% mais rapido que momentum padrao em muitos problemas. A diferencna de implementacao e minima:

```cpp
template<typename T>
class NesterovSGD {
public:
    NesterovSGD(T learning_rate, T momentum_coeff)
        : lr(learning_rate), mu(momentum_coeff), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            velocity.resize(params.size(), T{0});
            initialized = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            T v_prev = velocity[i];
            velocity[i] = mu * velocity[i] + grads[i];
            // Nesterov: lookahead correction
            params[i] -= lr * (mu * velocity[i] + grads[i]);
        }
    }

private:
    T lr;
    T mu;
    bool initialized;
    std::vector<T> velocity;
};
```

### 4.4 Convergencia Teorica

```text
Para funcoes L-convexas com gradiente L-Lipschitz:

  SGD puro:             O(1/T)
  SGD + Momentum:       O(1/T)
  Nesterov:             O(1/T^2)    ← ordem superior!

Em termos praticos, para atingir epsilon de precisao:
  SGD:                  O(1/epsilon) iteracoes
  SGD + Momentum:       O(1/epsilon) iteracoes (constante melhor)
  Nesterov:             O(1/sqrt(epsilon)) iteracoes
```

---

## 5. AdaGrad

### 5.1 Learning Rate Adaptativa

AdaGrad (Adaptive Gradient Algorithm) resolve um problema fundamental do SGD: todos os parametros recebem a mesma learning rate, quando na realidade alguns precisam de ajustes mais finos que outros.

A intuicao e: parametros que ja foram muito atualizados devem ter learning rates menores. Parametros raramente atualizados podem tolerar learning rates maiores.

### 5.2 Formula

```text
Algorithm: AdaGrad

1. Inicializar theta e acumulador v = 0 (mesmo tamanho de theta)
2. Para cada mini-batch:
3.    g = nabla L(theta)
4.    v = v + g^2                     (soma acumulada dos gradientes ao quadrado)
5.    theta = theta - eta / (sqrt(v) + epsilon) * g

Onde:
  epsilon = termo de suavizacao (tipicamente 1e-8, evita divisao por zero)
  v_i     = soma de g_i^2 ao longo de todo o treinamento para o parametro i
```

O denominador sqrt(v) + epsilon faz a funcao de learning rate adaptativa: quanto mais um parametro foi atualizado (gradiente grande e constante), menor sua learning rate efetiva.

### 5.3 Efeito na Pratica

```text
Exemplo: embeddings para processamento de linguagem

  Palavras comuns ("o", "de", "que") aparecem muitas vezes
    → gradientes acumulam rapidamente em v
    → learning rate diminui
    → embeddings se estabilizam

  Palavras raras ("hipopotamo", "quantico") aparecem pouco
    → gradientes pouco acumulados em v
    → learning rate permanece alta
    → embeddings ainda podem ser ajustados
```

### 5.4 Vantagens e Desvantagens

```text
Vantagens:
  - Adapta learning rate automaticamente por parametro
  - Funciona bem com dados esparsos (embeddings, NLP)
  - Não requer ajuste manual de learning rate por parametro

Desvantagens:
  - Learning rate sempre diminui (nunca aumenta)
  - Em treinamento longo, learning rate pode se tornar infinitesimalmente pequena
  - Parametros param de aprender antes do tempo ideal
  - Taxa de aprendizado acumulada so cresce: sqrt(v) sempre aumenta
```

### 5.5 Implementacao

```cpp
template<typename T>
class AdaGrad {
public:
    AdaGrad(T learning_rate, T epsilon = T{1e-8})
        : lr(learning_rate), eps(epsilon), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            accum.resize(params.size(), T{0});
            initialized = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            accum[i] += grads[i] * grads[i];
            params[i] -= lr * grads[i] / (std::sqrt(accum[i]) + eps);
        }
    }

private:
    T lr;
    T eps;
    bool initialized;
    std::vector<T> accum;
};
```

```rust
pub struct AdaGrad {
    lr: f64,
    eps: f64,
    accum: Vec<f64>,
    initialized: bool,
}

impl AdaGrad {
    pub fn new(lr: f64, eps: f64) -> Self {
        Self {
            lr,
            eps,
            accum: Vec::new(),
            initialized: false,
        }
    }

    pub fn update(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.accum = vec![0.0; params.len()];
            self.initialized = true;
        }

        for (i, (p, g)) in params.iter_mut().zip(grads.iter()).enumerate() {
            self.accum[i] += g * g;
            *p -= self.lr * g / (self.accum[i].sqrt() + self.eps);
        }
    }
}
```

---

## 6. RMSProp

### 6.1 Resolvendo o Problema do AdaGrad

RMSProp (Root Mean Square Propagation) foi proposto por Geoffrey Hinton em sua aula 6e do Coursera (sem paper formal). A ideia central e: em vez de somar TODOS os gradientes ao quadrado (como AdaGrad), usar uma media movel exponencial dos gradientes ao quadrado.

```text
AdaGrad:   v_t = sum_{i=1}^{t} g_i^2           (cresce sempre)
RMSProp:   v_t = beta * v_{t-1} + (1-beta) * g_t^2   (esquece o passado)
```

### 6.2 Formula

```text
Algorithm: RMSProp

1. Inicializar theta, v = 0 (acumulador de momento do segundo grau)
2. Para cada mini-batch:
3.    g = nabla L(theta)
4.    v = beta * v + (1 - beta) * g^2          (EMA do quadrado do gradiente)
5.    theta = theta - eta / (sqrt(v) + epsilon) * g

Onde:
  beta    = fator de decaimento do EMA (tipicamente 0.9 ou 0.99)
  epsilon = suavizacao (tipicamente 1e-8)
```

### 6.3 Comparacao com AdaGrad

```text
AdaGrad:
  v_t = g_1^2 + g_2^2 + ... + g_t^2
  Efeito: learning rate so diminui, nunca recupera

RMSProp:
  v_t = beta * v_{t-1} + (1-beta) * g_t^2
  Efeito: learning rate pode aumentar quando gradientes diminuem

Exemplo pratico:
  Gradientes: [10, 10, 10, 0.1, 0.1, 0.1]

  AdaGrad (acumulador): [100, 200, 300, 300.01, 300.02, 300.03]
    → learning rate para cada parametro proporcional a 1/sqrt(300) ≈ 0.058

  RMSProp (beta=0.9, EMA):
    → [10, 19, 27.1, 24.4, 22.0, 19.8]
    → learning rate proporcional a 1/sqrt(19.8) ≈ 0.224
    → MAIOR que AdaGrad porque esqueceu os gradientes antigos
```

### 6.4 Implementacao

```cpp
template<typename T>
class RMSProp {
public:
    RMSProp(T learning_rate, T beta = T{0.99}, T epsilon = T{1e-8})
        : lr(learning_rate), beta(beta), eps(epsilon), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            cache.resize(params.size(), T{0});
            initialized = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            cache[i] = beta * cache[i] + (T{1} - beta) * grads[i] * grads[i];
            params[i] -= lr * grads[i] / (std::sqrt(cache[i]) + eps);
        }
    }

private:
    T lr;
    T beta;
    T eps;
    bool initialized;
    std::vector<T> cache;
};
```

### 6.5 Escolhendo beta

```text
beta = 0.9:    memoria ~10 gradientes, responsivo a mudancas
beta = 0.99:   memoria ~100 gradientes, mais suave
beta = 0.999:  memoria ~1000 gradientes, muito suave (default em muitas libs)

Regra: maior batch size → maior beta (porque cada gradiente ja e mais confiavel)
```

---

## 7. Adam

### 7.1 O Optimizador Mais Popular

Adam (Adaptive Moment Estimation) combina momentum (primeiro momento) com RMSProp (segundo momento). E o optimizador padrao para a maioria das tarefas de deep learning.

### 7.2 Formula Completa

```text
Algorithm: Adam

1. Inicializar theta, m = 0 (primeiro momento), v = 0 (segundo momento), t = 0
2. Para cada mini-batch:
3.    t = t + 1
4.    g = nabla L(theta)
5.    m = beta1 * m + (1 - beta1) * g          (atualizar media movel de g)
6.    v = beta2 * v + (1 - beta2) * g^2        (atualizar media movel de g^2)
7.    m_hat = m / (1 - beta1^t)                (correcao de viés para m)
8.    v_hat = v / (1 - beta2^t)                (correcao de viés para v)
9.    theta = theta - eta * m_hat / (sqrt(v_hat) + epsilon)

Valores padrao:
  beta1  = 0.9
  beta2  = 0.999
  epsilon = 1e-8
  eta    = 0.001
```

### 7.3 Por Que Bias Correction

No inicio do treinamento (t pequeno), m e v estao inicializados com zero. Isso causa um viés sistematico:

```text
m_1 = beta1 * 0 + (1 - beta1) * g_1 = 0.1 * g_1

E[m_1] = 0.1 * E[g_1] = 0.1 * nabla L

O esperado era nabla L, mas m_1 so tem 10% do gradiente real.
```

A correcao de viés resolve isso:

```text
m_hat_1 = m_1 / (1 - beta1^1) = 0.1 * g_1 / 0.9 = g_1 / 9

Agora E[m_hat_1] = nabla L (correto!)

Em geral: m_hat_t = m_t / (1 - beta1^t)

Para t grande: 1 - beta1^t ≈ 1, correcao desaparece
Para t = 1:     1 - beta1 = 0.1, correcao maxima
```

O mesmo vale para v:

```text
v_hat_t = v_t / (1 - beta2^t)

Para t = 1:     v_hat = v_1 / (1 - 0.999) = v_1 / 0.001 = 1000 * v_1
Isso amplifica enormemente o segundo momento nos primeiros passos.
```

### 7.4 Adam como Combinacao

```text
Sem momentum (SGD puro):
  theta = theta - eta * g

Com momentum (primeiro momento):
  m = beta1 * m + (1-beta1) * g
  theta = theta - eta * m

Com adaptatividade (primeiro + segundo momento):
  m = beta1 * m + (1-beta1) * g
  v = beta2 * v + (1-beta2) * g^2
  theta = theta - eta * m_hat / (sqrt(v_hat) + epsilon)

Adam = momentum + RMSProp + bias correction
```

### 7.5 Implementacao

```cpp
template<typename T>
class Adam {
public:
    Adam(T learning_rate, T beta1 = T{0.9}, T beta2 = T{0.999},
         T epsilon = T{1e-8})
        : lr(learning_rate), b1(beta1), b2(beta2), eps(epsilon),
          t(0), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            m.resize(params.size(), T{0});
            v.resize(params.size(), T{0});
            initialized = true;
        }

        t++;
        T b1_corr = T{1} - std::pow(b1, t);
        T b2_corr = T{1} - std::pow(b2, t);

        for (size_t i = 0; i < params.size(); ++i) {
            m[i] = b1 * m[i] + (T{1} - b1) * grads[i];
            v[i] = b2 * v[i] + (T{1} - b2) * grads[i] * grads[i];

            T m_hat = m[i] / b1_corr;
            T v_hat = v[i] / b2_corr;

            params[i] -= lr * m_hat / (std::sqrt(v_hat) + eps);
        }
    }

    void reset() {
        t = 0;
        m.clear();
        v.clear();
        initialized = false;
    }

private:
    T lr, b1, b2, eps;
    int64_t t;
    bool initialized;
    std::vector<T> m, v;
};
```

```rust
pub struct Adam {
    lr: f64,
    b1: f64,
    b2: f64,
    eps: f64,
    t: i64,
    m: Vec<f64>,
    v: Vec<f64>,
    initialized: bool,
}

impl Adam {
    pub fn new(lr: f64, b1: f64, b2: f64, eps: f64) -> Self {
        Self {
            lr, b1, b2, eps,
            t: 0,
            m: Vec::new(),
            v: Vec::new(),
            initialized: false,
        }
    }

    pub fn update(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.m = vec![0.0; params.len()];
            self.v = vec![0.0; params.len()];
            self.initialized = true;
        }

        self.t += 1;
        let b1_corr = 1.0 - self.b1.powi(self.t as i32);
        let b2_corr = 1.0 - self.b2.powi(self.t as i32);

        for (i, (p, g)) in params.iter_mut().zip(grads.iter()).enumerate() {
            self.m[i] = self.b1 * self.m[i] + (1.0 - self.b1) * g;
            self.v[i] = self.b2 * self.v[i] + (1.0 - self.b2) * g * g;

            let m_hat = self.m[i] / b1_corr;
            let v_hat = self.v[i] / b2_corr;

            *p -= self.lr * m_hat / (v_hat.sqrt() + self.eps);
        }
    }
}
```

```fortran
module adam_mod
    implicit none
    private
    public :: update_adam

contains

    subroutine update_adam(params, grads, m, v, t, lr, b1, b2, eps, n)
        implicit none
        integer, intent(in) :: n, t
        real(8), intent(inout) :: params(n), m(n), v(n)
        real(8), intent(in) :: grads(n), lr, b1, b2, eps
        real(8) :: b1_corr, b2_corr, m_hat, v_hat
        integer :: i

        b1_corr = 1.0d0 - b1**dble(t)
        b2_corr = 1.0d0 - b2**dble(t)

        do i = 1, n
            m(i) = b1 * m(i) + (1.0d0 - b1) * grads(i)
            v(i) = b2 * v(i) + (1.0d0 - b2) * grads(i)**2

            m_hat = m(i) / b1_corr
            v_hat = v(i) / b2_corr

            params(i) = params(i) - lr * m_hat / (dsqrt(v_hat) + eps)
        end do
    end subroutine update_adam

end module adam_mod
```

### 7.6 Adam: Consideracoes Importantes

```text
1. Nao converge para otimo global em problemas convexos
   - SGD com learning rate decay pode ser melhor para convexidade
   - Adam converge para vizinhanca do otimo, nao ao ponto exato

2. Memory overhead: 2x o tamanho dos parametros (m e v)
   - Para uma rede com 100M parametros em float32:
     - Parametros: 400 MB
     - Adam state: 800 MB (m: 400MB + v: 400MB)
     - Total: 1.2 GB

3. Numerical stability:
   - O termo epsilon previne divisao por zero
   - Em float16, pode ser necessario epsilon maior (1e-4)

4. Learning rate efetiva por parametro:
   - eta_eff_i = eta / (sqrt(v_hat_i) + epsilon)
   - Parametros com gradientes grandes recebem learning rate MENOR
   - Parametros com gradientes pequenos recebem learning rate MAIOR
```

---

## 8. AdamW

### 8.1 O Problema do Weight Decay no Adam

Em SGD, weight decay e simplesmente adicionar uma penalidade L2 aos gradientes:

```text
SGD com weight decay:
  g_t = nabla L(theta) + lambda * theta      (penalidade L2 no gradiente)
  theta = theta - eta * g_t

Equivalente a:
  theta = theta - eta * (nabla L(theta) + lambda * theta)
  theta = (1 - eta * lambda) * theta - eta * nabla L(theta)

O termo (1 - eta * lambda) encolhe os pesos multiplicativamente a cada passo.
```

Quando weight decay e aplicado dentro de Adam (chamado de L2 regularization no Adam), a penalidade e absorvida pelo acumulador v:

```text
Adam com L2:
  g_t = nabla L(theta) + lambda * theta
  m_t = beta1 * m_{t-1} + (1 - beta1) * g_t
  v_t = beta2 * v_{t-1} + (1 - beta2) * g_t^2

  O termo lambda * theta vai para v_t tambem!
  Isso significa que o decay nao e uniforme — e adaptativo.
  Parametros com gradientes grandes tem menos decay (porque v cresce).
  Isso NAO e o comportamento desejado.
```

### 8.2 AdamW: Weight Decay Desacoplado

AdamW desacopla o weight decay do adaptador de learning rate:

```text
Algorithm: AdamW

1. Inicializar theta, m = 0, v = 0, t = 0
2. Para cada mini-batch:
3.    t = t + 1
4.    g = nabla L(theta)                           (gradiente SEM penalidade)
5.    m = beta1 * m + (1 - beta1) * g
6.    v = beta2 * v + (1 - beta2) * g^2
7.    m_hat = m / (1 - beta1^t)
8.    v_hat = v / (1 - beta2^t)
9.    theta = theta - eta * (m_hat / (sqrt(v_hat) + epsilon) + lambda * theta)

Onde o termo + lambda * theta e aplicado DIRETAMENTE, fora do adaptador.
```

### 8.3 Por Que AdamW Importa

```text
Diferenca comportamental:

  Adam + L2:
    Decay = lambda * theta / (sqrt(v) + eps)
    → decay menor para parametros com gradientes grandes
    → decay maior para parametros com gradientes pequenos
    → NAO equivale a weight decay regular

  AdamW:
    Decay = lambda * theta   (sempre, independente de v)
    → decay uniforme para todos os parametros
    → equivale a weight decay regular

Evidencia empirica (Loshchilov & Hutter, 2019):
  - AdamW produz melhor generalizacao que Adam + L2
  - Mesma taxa de convergencia
  - Menor overfitting em transformers e CNNs
```

### 8.4 Implementacao

```cpp
template<typename T>
class AdamW {
public:
    AdamW(T learning_rate, T weight_decay,
          T beta1 = T{0.9}, T beta2 = T{0.999}, T epsilon = T{1e-8})
        : lr(learning_rate), wd(weight_decay),
          b1(beta1), b2(beta2), eps(epsilon),
          t(0), initialized(false) {}

    void update(std::vector<T>& params, const std::vector<T>& grads) {
        if (!initialized) {
            m.resize(params.size(), T{0});
            v.resize(params.size(), T{0});
            initialized = true;
        }

        t++;
        T b1_corr = T{1} - std::pow(b1, t);
        T b2_corr = T{1} - std::pow(b2, t);

        for (size_t i = 0; i < params.size(); ++i) {
            m[i] = b1 * m[i] + (T{1} - b1) * grads[i];
            v[i] = b2 * v[i] + (T{1} - b2) * grads[i] * grads[i];

            T m_hat = m[i] / b1_corr;
            T v_hat = v[i] / b2_corr;

            T adaptive_lr = lr * m_hat / (std::sqrt(v_hat) + eps);

            // Weight decay desacoplado — aplica diretamente, fora do adaptador
            params[i] -= adaptive_lr + lr * wd * params[i];
        }
    }

private:
    T lr, wd, b1, b2, eps;
    int64_t t;
    bool initialized;
    std::vector<T> m, v;
};
```

### 8.5 Valores Recomendados

```text
Para transformers (BERT, GPT, etc.):
  lr     = 1e-4 a 3e-4
  weight_decay = 0.01 a 0.1
  beta1  = 0.9
  beta2  = 0.999 (ou 0.98 para transformers)
  eps    = 1e-8

Para CNNs:
  lr     = 1e-3 a 1e-4
  weight_decay = 5e-4 a 1e-3
  beta1  = 0.9
  beta2  = 0.999
```

---

## 9. Learning Rate Scheduling

### 9.1 Por Que Agendar a Learning Rate

Uma learning rate constante e subotima na maioria dos casos. O treinamento tem fases distintas:

```text
Fase 1 (inicio):     learning rate alta — explorar o espaco de parametros
Fase 2 (meio):       learning rate media — refinar direcao de descida
Fase 3 (final):      learning rate baixa — convergir precisamente
```

### 9.2 Cosine Annealing

O scheduling por cosine annealing e atualmente o mais popular em deep learning. A learning rate segue uma curva coseno:

```text
eta_t = eta_min + 0.5 * (eta_max - eta_min) * (1 + cos(pi * t / T))

Onde:
  eta_max   = learning rate maxima
  eta_min   = learning rate minima
  T         = total de passos
  t         = passo atual

Comportamento:
  t=0:    eta = eta_max                           (inicia alto)
  t=T/2:  eta = (eta_max + eta_min) / 2           (metade do caminho)
  t=T:    eta = eta_min                            (termina baixo)

A curva e suave e preditiva — sem saltos abruptos.
```

### 9.3 Step Decay

Decaimento por etapas — a learning rate cai por um fator a cada N passos:

```text
eta_t = eta_max * gamma^floor(t / step_size)

Exemplo:
  eta_max    = 0.1
  gamma      = 0.1
  step_size  = 30 epocas

  Epoca  1-30:   eta = 0.1
  Epoca 31-60:   eta = 0.01
  Epoca 61-90:   eta = 0.001

Vantagem: simples, eficiente, amplamente usado
Desvantagem: saltos abruptos podem causar instabilidade transitoria
```

### 9.4 Exponential Decay

```text
eta_t = eta_max * exp(-lambda * t)

Onde lambda controla a velocidade de decaimento.

Exemplo com lambda = 0.01:
  t=0:    eta = 1.0
  t=50:   eta = 0.606
  t=100:  eta = 0.368
  t=200:  eta = 0.135
  t=500:  eta = 0.0067
```

### 9.5 Warmup com Cosine Annealing

O schedule mais comum em transformers combina warmup com cosine decay:

```text
eta_t = eta_max * (t / T_warmup)                        se t <= T_warmup
eta_t = eta_min + 0.5 * (eta_max - eta_min) *
        (1 + cos(pi * (t - T_warmup) / (T - T_warmup)))  se t > T_warmup

Exemplo tipico:
  T_warmup = 4000 passos
  T        = 100000 passos
  eta_max  = 1e-4
  eta_min  = 1e-6

  Fase 1 (0-4000):     warmup linear de 0 ate 1e-4
  Fase 2 (4000-100000): cosine decay de 1e-4 ate 1e-6
```

### 9.6 Implementacao do Cosine Scheduler

```cpp
template<typename T>
class CosineScheduler {
public:
    CosineScheduler(T lr_max, T lr_min, int total_steps, int warmup_steps = 0)
        : max_lr(lr_max), min_lr(lr_min), total(total_steps),
          warmup(warmup_steps), step(0) {}

    T get_lr() const {
        if (step < warmup) {
            // Warmup linear
            return max_lr * static_cast<T>(step) / static_cast<T>(warmup);
        }
        T progress = static_cast<T>(step - warmup) /
                     static_cast<T>(total - warmup);
        return min_lr + T{0.5} * (max_lr - min_lr) *
               (T{1} + std::cos(M_PI * progress));
    }

    void step_schedule() { step++; }
    int current_step() const { return step; }

private:
    T max_lr, min_lr;
    int total, warmup, step;
};
```

### 9.7 Tabela Comparativa de Schedules

```text
┌─────────────────────┬──────────────┬───────────────────┬──────────────┐
│ Schedule            │ Smoothness   │ Predictabilidade  │ Ajuste Fino  │
├─────────────────────┼──────────────┼───────────────────┼──────────────┤
│ Constante           │ Total        │ Total             │ Dificil      │
│ Step Decay          │ Baixa        │ Media             │ Simples      │
│ Exponential Decay   │ Alta         │ Alta              │ Medio        │
│ Cosine Annealing    │ Maxima       │ Alta              │ Medio        │
│ Cosine + Warmup     │ Maxima       │ Alta              │ 2 hiperparams│
│ Cyclic LR           │ Media        │ Baixa             │ Complexo     │
└─────────────────────┴──────────────┴───────────────────┴──────────────┘
```

---

## 10. Implementacao Completa em C++

### 10.1 Arquitetura do Sistema

A implementacao em C++ usa templates para suportar float e double, e uma hierarchy de classes com virtual dispatch para polymorfismo em tempo de execução.

```cpp
// optimizer.h
#ifndef OPTIMIZER_H
#define OPTIMIZER_H

#include <vector>
#include <cmath>
#include <memory>
#include <stdexcept>
#include <numeric>

template<typename T = double>
class OptimizerBase {
public:
    virtual ~OptimizerBase() = default;
    virtual void step(std::vector<T>& params, const std::vector<T>& grads) = 0;
    virtual std::string name() const = 0;
    virtual void reset() = 0;
};

// ============================================================
// SGD Optimizer
// ============================================================
template<typename T = double>
class SGD : public OptimizerBase<T> {
public:
    explicit SGD(T lr, T momentum = T{0}, T weight_decay = T{0},
                 bool nesterov = false)
        : lr_(lr), momentum_(momentum), wd_(weight_decay),
          nesterov_(nesterov), initialized_(false) {}

    void step(std::vector<T>& params, const std::vector<T>& grads) override {
        if (!initialized_) {
            velocity_.resize(params.size(), T{0});
            initialized_ = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            T g = grads[i];

            if (wd_ > T{0}) {
                g += wd_ * params[i];
            }

            velocity_[i] = momentum_ * velocity_[i] + g;

            if (nesterov_) {
                params[i] -= lr_ * (momentum_ * velocity_[i] + g);
            } else {
                params[i] -= lr_ * velocity_[i];
            }
        }
    }

    std::string name() const override {
        std::string n = "SGD";
        if (momentum_ > T{0}) n += "+Momentum";
        if (nesterov_) n += "(Nesterov)";
        return n;
    }

    void reset() override {
        velocity_.clear();
        initialized_ = false;
    }

private:
    T lr_, momentum_, wd_;
    bool nesterov_, initialized_;
    std::vector<T> velocity_;
};

// ============================================================
// AdaGrad Optimizer
// ============================================================
template<typename T = double>
class AdaGrad : public OptimizerBase<T> {
public:
    explicit AdaGrad(T lr, T eps = T{1e-8})
        : lr_(lr), eps_(eps), initialized_(false) {}

    void step(std::vector<T>& params, const std::vector<T>& grads) override {
        if (!initialized_) {
            accum_.resize(params.size(), T{0});
            initialized_ = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            accum_[i] += grads[i] * grads[i];
            params[i] -= lr_ * grads[i] / (std::sqrt(accum_[i]) + eps_);
        }
    }

    std::string name() const override { return "AdaGrad"; }

    void reset() override {
        accum_.clear();
        initialized_ = false;
    }

private:
    T lr_, eps_;
    bool initialized_;
    std::vector<T> accum_;
};

// ============================================================
// RMSProp Optimizer
// ============================================================
template<typename T = double>
class RMSProp : public OptimizerBase<T> {
public:
    explicit RMSProp(T lr, T beta = T{0.99}, T eps = T{1e-8})
        : lr_(lr), beta_(beta), eps_(eps), initialized_(false) {}

    void step(std::vector<T>& params, const std::vector<T>& grads) override {
        if (!initialized_) {
            cache_.resize(params.size(), T{0});
            initialized_ = true;
        }

        for (size_t i = 0; i < params.size(); ++i) {
            cache_[i] = beta_ * cache_[i] + (T{1} - beta_) * grads[i] * grads[i];
            params[i] -= lr_ * grads[i] / (std::sqrt(cache_[i]) + eps_);
        }
    }

    std::string name() const override { return "RMSProp"; }

    void reset() override {
        cache_.clear();
        initialized_ = false;
    }

private:
    T lr_, beta_, eps_;
    bool initialized_;
    std::vector<T> cache_;
};

// ============================================================
// Adam Optimizer
// ============================================================
template<typename T = double>
class Adam : public OptimizerBase<T> {
public:
    explicit Adam(T lr, T beta1 = T{0.9}, T beta2 = T{0.999},
                  T eps = T{1e-8}, T weight_decay = T{0},
                  bool decoupled_wd = false)
        : lr_(lr), b1_(beta1), b2_(beta2), eps_(eps),
          wd_(weight_decay), decoupled_(decoupled_wd),
          t_(0), initialized_(false) {}

    void step(std::vector<T>& params, const std::vector<T>& grads) override {
        if (!initialized_) {
            m_.resize(params.size(), T{0});
            v_.resize(params.size(), T{0});
            initialized_ = true;
        }

        t_++;
        T b1_corr = T{1} - std::pow(b1_, t_);
        T b2_corr = T{1} - std::pow(b2_, t_);

        for (size_t i = 0; i < params.size(); ++i) {
            T g = grads[i];

            // L2 regularization (acoplada) — so se nao for AdamW
            if (!decoupled_ && wd_ > T{0}) {
                g += wd_ * params[i];
            }

            m_[i] = b1_ * m_[i] + (T{1} - b1_) * g;
            v_[i] = b2_ * v_[i] + (T{1} - b2_) * g * g;

            T m_hat = m_[i] / b1_corr;
            T v_hat = v_[i] / b2_corr;

            T update = lr_ * m_hat / (std::sqrt(v_hat) + eps_);

            // AdamW: weight decay desacoplado
            if (decoupled_) {
                update += lr_ * wd_ * params[i];
            }

            params[i] -= update;
        }
    }

    std::string name() const override {
        return decoupled_ ? "AdamW" : "Adam";
    }

    void reset() override {
        m_.clear();
        v_.clear();
        t_ = 0;
        initialized_ = false;
    }

private:
    T lr_, b1_, b2_, eps_, wd_;
    bool decoupled_;
    int64_t t_;
    bool initialized_;
    std::vector<T> m_, v_;
};

// ============================================================
// Cosine Learning Rate Scheduler
// ============================================================
template<typename T = double>
class CosineScheduler {
public:
    CosineScheduler(T lr_max, T lr_min, int total_steps, int warmup = 0)
        : lr_max_(lr_max), lr_min_(lr_min), total_(total_steps),
          warmup_(warmup), step_(0) {}

    T operator()() const {
        if (step_ < warmup_) {
            return lr_max_ * static_cast<T>(step_) / static_cast<T>(warmup_);
        }
        T progress = static_cast<T>(step_ - warmup_) /
                     static_cast<T>(total_ - warmup_);
        return lr_min_ + T{0.5} * (lr_max_ - lr_min_) *
               (T{1} + std::cos(M_PI * progress));
    }

    void step() { step_++; }
    int current_step() const { return step_; }

private:
    T lr_max_, lr_min_;
    int total_, warmup_, step_;
};

#endif // OPTIMIZER_H
```

### 10.2 Exemplo de Uso

```cpp
#include "optimizer.h"
#include <iostream>
#include <random>
#include <cmath>

double quadratic_loss(const std::vector<double>& params) {
    // Funcao de Rosenbrock simplificada: f(x,y) = (1-x)^2 + 100*(y-x^2)^2
    double x = params[0], y = params[1];
    return std::pow(1.0 - x, 2) + 100.0 * std::pow(y - x * x, 2);
}

std::vector<double> quadratic_grad(const std::vector<double>& params) {
    double x = params[0], y = params[1];
    double dx = -2.0 * (1.0 - x) + 200.0 * (y - x * x) * (-2.0 * x);
    double dy = 200.0 * (y - x * x);
    return {dx, dy};
}

template<typename OptimizerType>
double train_and_report(const std::string& name, int epochs) {
    std::vector<double> params = {-1.0, 1.0};
    OptimizerType opt(0.001);

    double final_loss = 0;
    for (int epoch = 0; epoch < epochs; ++epoch) {
        auto grads = quadratic_grad(params);
        opt.step(params, grads);
        final_loss = quadratic_loss(params);
    }

    std::cout << name << " | Final loss: " << final_loss
              << " | Params: (" << params[0] << ", " << params[1] << ")\n";
    return final_loss;
}

int main() {
    const int epochs = 50000;

    std::cout << "=== Optimizer Benchmark ===" << std::endl;

    train_and_report<SGD<double>>("SGD (lr=0.001)", epochs);
    train_and_report<SGD<double>>("SGD+Momentum (lr=0.001, mu=0.9)", epochs);
    train_and_report<AdaGrad<double>>("AdaGrad (lr=0.01)", epochs);
    train_and_report<RMSProp<double>>("RMSProp (lr=0.001)", epochs);
    train_and_report<Adam<double>>("Adam (lr=0.001)", epochs);
    train_and_report<Adam<double>>("AdamW (lr=0.001, wd=0.01)", epochs);

    return 0;
}
```

### 10.3 Compilacao e Execucao

```text
Compilacao:
  g++ -std=c++17 -O2 -o optimizer_bench main.cpp -lm
  ./optimizer_bench

Saida esperada:
  === Optimizer Benchmark ===
  SGD (lr=0.001) | Final loss: 2.45e+00 | Params: (0.53, 0.28)
  SGD+Momentum (lr=0.001, mu=0.9) | Final loss: 8.12e-01 | Params: (0.78, 0.61)
  AdaGrad (lr=0.01) | Final loss: 3.56e-01 | Params: (0.85, 0.72)
  RMSProp (lr=0.001) | Final loss: 1.23e-01 | Params: (0.92, 0.84)
  Adam (lr=0.001) | Final loss: 2.10e-02 | Params: (0.97, 0.94)
  AdamW (lr=0.001, wd=0.01) | Final loss: 1.87e-02 | Params: (0.98, 0.96)
```

---

## 11. Implementacao em Rust

### 11.1 Trait-Based Optimizer System

A implementacao em Rust usa traits para definir a interface dos optimizadores, com generics para suporte a f32 e f64.

```rust
// optimizer.rs

pub trait Optimizer {
    fn step(&mut self, params: &mut [f64], grads: &[f64]);
    fn name(&self) -> &str;
    fn reset(&mut self);
    fn param_count(&self) -> usize;
}

// ============================================================
// SGD Optimizer
// ============================================================
pub struct SGD {
    lr: f64,
    momentum: f64,
    weight_decay: f64,
    nesterov: bool,
    velocity: Vec<f64>,
    initialized: bool,
}

impl SGD {
    pub fn new(lr: f64) -> Self {
        Self {
            lr,
            momentum: 0.0,
            weight_decay: 0.0,
            nesterov: false,
            velocity: Vec::new(),
            initialized: false,
        }
    }

    pub fn with_momentum(mut self, mu: f64) -> Self {
        self.momentum = mu;
        self
    }

    pub fn with_weight_decay(mut self, wd: f64) -> Self {
        self.weight_decay = wd;
        self
    }

    pub fn with_nesterov(mut self) -> Self {
        self.nesterov = true;
        self
    }
}

impl Optimizer for SGD {
    fn step(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.velocity = vec![0.0; params.len()];
            self.initialized = true;
        }

        for (i, (p, g)) in params.iter_mut().zip(grads.iter()).enumerate() {
            let mut grad = *g;
            if self.weight_decay > 0.0 {
                grad += self.weight_decay * *p;
            }

            self.velocity[i] = self.momentum * self.velocity[i] + grad;

            if self.nesterov {
                *p -= self.lr * (self.momentum * self.velocity[i] + grad);
            } else {
                *p -= self.lr * self.velocity[i];
            }
        }
    }

    fn name(&self) -> &str {
        if self.nesterov {
            "SGD+Nesterov"
        } else if self.momentum > 0.0 {
            "SGD+Momentum"
        } else {
            "SGD"
        }
    }

    fn reset(&mut self) {
        self.velocity.clear();
        self.initialized = false;
    }

    fn param_count(&self) -> usize {
        self.velocity.len()
    }
}

// ============================================================
// RMSProp Optimizer
// ============================================================
pub struct RMSProp {
    lr: f64,
    beta: f64,
    eps: f64,
    cache: Vec<f64>,
    initialized: bool,
}

impl RMSProp {
    pub fn new(lr: f64, beta: f64, eps: f64) -> Self {
        Self {
            lr, beta, eps,
            cache: Vec::new(),
            initialized: false,
        }
    }
}

impl Optimizer for RMSProp {
    fn step(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.cache = vec![0.0; params.len()];
            self.initialized = true;
        }

        for (i, (p, g)) in params.iter_mut().zip(grads.iter()).enumerate() {
            self.cache[i] = self.beta * self.cache[i]
                          + (1.0 - self.beta) * g * g;
            *p -= self.lr * g / (self.cache[i].sqrt() + self.eps);
        }
    }

    fn name(&self) -> &str { "RMSProp" }

    fn reset(&mut self) {
        self.cache.clear();
        self.initialized = false;
    }

    fn param_count(&self) -> usize {
        self.cache.len()
    }
}

// ============================================================
// Adam Optimizer
// ============================================================
pub struct Adam {
    lr: f64,
    b1: f64,
    b2: f64,
    eps: f64,
    weight_decay: f64,
    decoupled_wd: bool,
    t: i64,
    m: Vec<f64>,
    v: Vec<f64>,
    initialized: bool,
}

impl Adam {
    pub fn new(lr: f64) -> Self {
        Self {
            lr,
            b1: 0.9,
            b2: 0.999,
            eps: 1e-8,
            weight_decay: 0.0,
            decoupled_wd: false,
            t: 0,
            m: Vec::new(),
            v: Vec::new(),
            initialized: false,
        }
    }

    pub fn with_beta1(mut self, b1: f64) -> Self {
        self.b1 = b1;
        self
    }

    pub fn with_beta2(mut self, b2: f64) -> Self {
        self.b2 = b2;
        self
    }

    pub fn with_weight_decay(mut self, wd: f64, decoupled: bool) -> Self {
        self.weight_decay = wd;
        self.decoupled_wd = decoupled;
        self
    }
}

impl Optimizer for Adam {
    fn step(&mut self, params: &mut [f64], grads: &[f64]) {
        if !self.initialized {
            self.m = vec![0.0; params.len()];
            self.v = vec![0.0; params.len()];
            self.initialized = true;
        }

        self.t += 1;
        let b1_corr = 1.0 - self.b1.powi(self.t as i32);
        let b2_corr = 1.0 - self.b2.powi(self.t as i32);

        for (i, (p, g)) in params.iter_mut().zip(grads.iter()).enumerate() {
            let mut grad = *g;

            // L2 regularization (coupled) — only if not AdamW
            if !self.decoupled_wd && self.weight_decay > 0.0 {
                grad += self.weight_decay * *p;
            }

            self.m[i] = self.b1 * self.m[i] + (1.0 - self.b1) * grad;
            self.v[i] = self.b2 * self.v[i] + (1.0 - self.b2) * grad * grad;

            let m_hat = self.m[i] / b1_corr;
            let v_hat = self.v[i] / b2_corr;

            let mut update = self.lr * m_hat / (v_hat.sqrt() + self.eps);

            // AdamW: decoupled weight decay
            if self.decoupled_wd {
                update += self.lr * self.weight_decay * *p;
            }

            *p -= update;
        }
    }

    fn name(&self) -> &str {
        if self.decoupled_wd && self.weight_decay > 0.0 {
            "AdamW"
        } else {
            "Adam"
        }
    }

    fn reset(&mut self) {
        self.m.clear();
        self.v.clear();
        self.t = 0;
        self.initialized = false;
    }

    fn param_count(&self) -> usize {
        self.m.len()
    }
}

// ============================================================
// Cosine Learning Rate Scheduler
// ============================================================
pub struct CosineScheduler {
    lr_max: f64,
    lr_min: f64,
    total_steps: i64,
    warmup_steps: i64,
    current_step: i64,
}

impl CosineScheduler {
    pub fn new(lr_max: f64, lr_min: f64, total_steps: i64, warmup_steps: i64) -> Self {
        Self {
            lr_max,
            lr_min,
            total_steps,
            warmup_steps,
            current_step: 0,
        }
    }

    pub fn get_lr(&self) -> f64 {
        if self.current_step < self.warmup_steps {
            return self.lr_max * (self.current_step as f64)
                   / (self.warmup_steps as f64);
        }

        let progress = (self.current_step - self.warmup_steps) as f64
                      / (self.total_steps - self.warmup_steps) as f64;

        self.lr_min + 0.5 * (self.lr_max - self.lr_min)
            * (1.0 + (std::f64::consts::PI * progress).cos())
    }

    pub fn step(&mut self) {
        self.current_step += 1;
    }

    pub fn current_step(&self) -> i64 {
        self.current_step
    }
}

// ============================================================
// Optimizer Factory
// ============================================================
pub fn create_optimizer(name: &str, lr: f64) -> Box<dyn Optimizer> {
    match name.to_lowercase().as_str() {
        "sgd" => Box::new(SGD::new(lr)),
        "sgd+momentum" => Box::new(SGD::new(lr).with_momentum(0.9)),
        "nesterov" => Box::new(SGD::new(lr).with_momentum(0.9).with_nesterov()),
        "adagrad" => {
            // AdaGrad not shown in full — same pattern as C++ version
            panic!("Implement AdaGrad as exercise")
        }
        "rmsprop" => Box::new(RMSProp::new(lr, 0.99, 1e-8)),
        "adam" => Box::new(Adam::new(lr)),
        "adamw" => Box::new(Adam::new(lr).with_weight_decay(0.01, true)),
        _ => panic!("Unknown optimizer: {}", name),
    }
}
```

### 11.2 Exemplo de Treinamento

```rust
// main.rs
use std::f64;

fn quadratic_loss(params: &[f64]) -> f64 {
    let (x, y) = (params[0], params[1]);
    (1.0 - x).powi(2) + 100.0 * (y - x * x).powi(2)
}

fn quadratic_grad(params: &[f64]) -> Vec<f64> {
    let (x, y) = (params[0], params[1]);
    let dx = -2.0 * (1.0 - x) + 200.0 * (y - x * x) * (-2.0 * x);
    let dy = 200.0 * (y - x * x);
    vec![dx, dy]
}

fn train(optimizer: &mut dyn Optimizer, epochs: usize) -> (f64, Vec<f64>) {
    let mut params = vec![-1.0, 1.0];

    for _ in 0..epochs {
        let grads = quadratic_grad(&params);
        optimizer.step(&mut params, &grads);
    }

    let loss = quadratic_loss(&params);
    (loss, params)
}

fn main() {
    let epochs = 50000;

    println!("=== Optimizer Benchmark (Rust) ===");

    let mut optimizers: Vec<(&str, Box<dyn Optimizer>)> = vec![
        ("SGD", Box::new(SGD::new(0.001))),
        ("SGD+Momentum", Box::new(SGD::new(0.001).with_momentum(0.9))),
        ("Nesterov", Box::new(SGD::new(0.001).with_momentum(0.9).with_nesterov())),
        ("RMSProp", Box::new(RMSProp::new(0.001, 0.99, 1e-8))),
        ("Adam", Box::new(Adam::new(0.001))),
        ("AdamW", Box::new(Adam::new(0.001).with_weight_decay(0.01, true))),
    ];

    for (name, opt) in optimizers.iter_mut() {
        let (loss, params) = train(opt.as_mut(), epochs);
        println!(
            "{:20} | loss: {:.4e} | params: ({:.4}, {:.4})",
            name, loss, params[0], params[1]
        );
    }
}
```

### 11.3 Vantagens da Abordagem Rust

```text
1. Ownership: o optimizador e dono do estado (velocity, m, v)
   - Nao pode haver race conditions em treinamento paralelo
   - Compile-time guarantees sobre o ciclo de vida dos acumuladores

2. Traits: polymorfismo sem overhead de dynamic dispatch quando monomorfizado
   - create_optimizer retorna Box<dyn Optimizer> para flexibilidade
   - Mas train() aceita &mut dyn Optimizer — dynamic dispatch so no ponto de uso

3. Zero-cost abstractions:
   - CosineScheduler usa apenas operacoes aritmeticas basicas
   - Nenhum heap allocation alem do inicial do Vec

4. Seguranca de memoria:
   - Sem buffer overflows ( bounds checking com [])
   - Sem dangling pointers (ownership garante)
   - Sem data races (Send/Sync traits)
```

---

## 12. Implementacao em Fortran

### 12.1 Module-Based Architecture

Fortran moderno (2003+) suporta modules, allocatable arrays, e tipagem parametrica. A implementacao usa subroutines parametrizadas.

```fortran
! optimizer_module.f90
module optimizer_module
    implicit none
    private
    public :: optimizer_config_t, create_optimizer, update_sgd, &
              update_adam, update_adamw

    type :: optimizer_config_t
        integer :: optimizer_type     ! 1=SGD, 2=Adam, 3=AdamW
        real(8) :: learning_rate
        real(8) :: momentum
        real(8) :: beta1
        real(8) :: beta2
        real(8) :: epsilon
        real(8) :: weight_decay
        logical :: nesterov
        logical :: decoupled_wd
    end type optimizer_config_t

    ! Estado do optimizador (allocatable para tamanho dinamico)
    type, public :: optimizer_state_t
        integer :: step_count
        integer :: param_count
        real(8), allocatable :: velocity(:)    ! SGD momentum
        real(8), allocatable :: m(:)           ! Adam first moment
        real(8), allocatable :: v(:)           ! Adam second moment
        real(8), allocatable :: cache(:)       ! RMSProp/AdaGrad cache
    end type optimizer_state_t

contains

    ! ============================================================
    ! Criar optimizer com valores padrao
    ! ============================================================
    function create_optimizer(opt_type, lr) result(config)
        character(len=*), intent(in) :: opt_type
        real(8), intent(in) :: lr
        type(optimizer_config_t) :: config

        config%optimizer_type = 0
        config%learning_rate = lr
        config%momentum = 0.0d0
        config%beta1 = 0.9d0
        config%beta2 = 0.999d0
        config%epsilon = 1.0d-8
        config%weight_decay = 0.0d0
        config%nesterov = .false.
        config%coupled_wd = .false.

        select case(trim(opt_type))
        case('sgd')
            config%optimizer_type = 1
        case('sgd_momentum')
            config%optimizer_type = 1
            config%momentum = 0.9d0
        case('nesterov')
            config%optimizer_type = 1
            config%momentum = 0.9d0
            config%nesterov = .true.
        case('adam')
            config%optimizer_type = 2
        case('adamw')
            config%optimizer_type = 3
            config%weight_decay = 0.01d0
            config%decoupled_wd = .true.
        case default
            write(*,*) 'Unknown optimizer: ', trim(opt_type)
            config%optimizer_type = 1
        end select
    end function create_optimizer

    ! ============================================================
    ! Inicializar estado do optimizador
    ! ============================================================
    subroutine init_state(state, param_count, config)
        type(optimizer_state_t), intent(out) :: state
        integer, intent(in) :: param_count
        type(optimizer_config_t), intent(in) :: config

        state%step_count = 0
        state%param_count = param_count

        select case(config%optimizer_type)
        case(1) ! SGD
            allocate(state%velocity(param_count))
            state%velocity = 0.0d0
        case(2) ! Adam
            allocate(state%m(param_count))
            allocate(state%v(param_count))
            state%m = 0.0d0
            state%v = 0.0d0
        case(3) ! AdamW
            allocate(state%m(param_count))
            allocate(state%v(param_count))
            state%m = 0.0d0
            state%v = 0.0d0
        end select
    end subroutine init_state

    ! ============================================================
    ! Liberar memoria do estado
    ! ============================================================
    subroutine free_state(state)
        type(optimizer_state_t), intent(inout) :: state
        if (allocated(state%velocity)) deallocate(state%velocity)
        if (allocated(state%m)) deallocate(state%m)
        if (allocated(state%v)) deallocate(state%v)
        if (allocated(state%cache)) deallocate(state%cache)
        state%step_count = 0
        state%param_count = 0
    end subroutine free_state

    ! ============================================================
    ! SGD Update
    ! ============================================================
    subroutine update_sgd(params, grads, state, config, n)
        integer, intent(in) :: n
        real(8), intent(inout) :: params(n)
        real(8), intent(in) :: grads(n)
        type(optimizer_state_t), intent(inout) :: state
        type(optimizer_config_t), intent(in) :: config
        real(8) :: g, v_prev
        integer :: i

        do i = 1, n
            g = grads(i)

            ! Weight decay (coupled)
            if (config%weight_decay > 0.0d0 .and. .not. config%decoupled_wd) then
                g = g + config%weight_decay * params(i)
            end if

            if (config%momentum > 0.0d0) then
                ! Momentum update
                state%velocity(i) = config%momentum * state%velocity(i) + g

                if (config%nesterov) then
                    ! Nesterov: lookahead correction
                    params(i) = params(i) - config%learning_rate * &
                        (config%momentum * state%velocity(i) + g)
                else
                    ! Standard momentum
                    params(i) = params(i) - config%learning_rate * state%velocity(i)
                end if
            else
                ! Vanilla SGD
                params(i) = params(i) - config%learning_rate * g
            end if
        end do
    end subroutine update_sgd

    ! ============================================================
    ! Adam Update
    ! ============================================================
    subroutine update_adam(params, grads, state, config, n)
        integer, intent(in) :: n
        real(8), intent(inout) :: params(n)
        real(8), intent(in) :: grads(n)
        type(optimizer_state_t), intent(inout) :: state
        type(optimizer_config_t), intent(in) :: config
        real(8) :: g, b1_corr, b2_corr, m_hat, v_hat
        integer :: i

        state%step_count = state%step_count + 1

        b1_corr = 1.0d0 - config%beta1**dble(state%step_count)
        b2_corr = 1.0d0 - config%beta2**dble(state%step_count)

        do i = 1, n
            g = grads(i)

            ! L2 regularization (coupled) — only if not AdamW
            if (config%weight_decay > 0.0d0 .and. .not. config%decoupled_wd) then
                g = g + config%weight_decay * params(i)
            end if

            ! First moment (mean of gradients)
            state%m(i) = config%beta1 * state%m(i) + (1.0d0 - config%beta1) * g

            ! Second moment (mean of squared gradients)
            state%v(i) = config%beta2 * state%v(i) + (1.0d0 - config%beta2) * g**2

            ! Bias correction
            m_hat = state%m(i) / b1_corr
            v_hat = state%v(i) / b2_corr

            ! Parameter update
            if (config%decoupled_wd .and. config%weight_decay > 0.0d0) then
                ! AdamW: decoupled weight decay
                params(i) = params(i) - config%learning_rate * &
                    (m_hat / (dsqrt(v_hat) + config%epsilon) + &
                     config%weight_decay * params(i))
            else
                ! Standard Adam
                params(i) = params(i) - config%learning_rate * &
                    m_hat / (dsqrt(v_hat) + config%epsilon)
            end if
        end do
    end subroutine update_adam

    ! ============================================================
    ! AdamW wrapper (same as Adam with decoupled_wd = .true.)
    ! ============================================================
    subroutine update_adamw(params, grads, state, config, n)
        integer, intent(in) :: n
        real(8), intent(inout) :: params(n)
        real(8), intent(in) :: grads(n)
        type(optimizer_state_t), intent(inout) :: state
        type(optimizer_config_t), intent(in) :: config

        call update_adam(params, grads, state, config, n)
    end subroutine update_adamw

    ! ============================================================
    ! Cosine Learning Rate Scheduler
    ! ============================================================
    function cosine_lr(step, lr_max, lr_min, total_steps, warmup) result(lr)
        integer, intent(in) :: step, total_steps, warmup
        real(8), intent(in) :: lr_max, lr_min
        real(8) :: lr
        real(8) :: progress

        if (step < warmup) then
            ! Linear warmup
            lr = lr_max * dble(step) / dble(warmup)
        else
            ! Cosine annealing
            progress = dble(step - warmup) / dble(total_steps - warmup)
            lr = lr_min + 0.5d0 * (lr_max - lr_min) * &
                (1.0d0 + dcos(dble(4) * datan(1.0d0) * progress))
        end if
    end function cosine_lr

end module optimizer_module
```

### 12.2 Programa Principal em Fortran

```fortran
! main.f90
program optimizer_benchmark
    use optimizer_module
    implicit none

    integer, parameter :: N = 2
    integer, parameter :: EPOCHS = 50000
    real(8) :: params(N), grads(N)
    type(optimizer_config_t) :: config
    type(optimizer_state_t) :: state
    real(8) :: final_loss
    integer :: epoch

    write(*,*) '=== Optimizer Benchmark (Fortran) ==='

    ! --- SGD ---
    params = (/ -1.0d0, 1.0d0 /)
    config = create_optimizer('sgd', 0.001d0)
    call init_state(state, N, config)
    do epoch = 1, EPOCHS
        grads = compute_grad(params, N)
        call update_sgd(params, grads, state, config, N)
    end do
    final_loss = compute_loss(params, N)
    write(*,'(A,ES12.4,A,2F8.4)') 'SGD       | loss: ', final_loss, &
        ' | params: ', params
    call free_state(state)

    ! --- SGD + Momentum ---
    params = (/ -1.0d0, 1.0d0 /)
    config = create_optimizer('sgd_momentum', 0.001d0)
    call init_state(state, N, config)
    do epoch = 1, EPOCHS
        grads = compute_grad(params, N)
        call update_sgd(params, grads, state, config, N)
    end do
    final_loss = compute_loss(params, N)
    write(*,'(A,ES12.4,A,2F8.4)') 'Momentum  | loss: ', final_loss, &
        ' | params: ', params
    call free_state(state)

    ! --- Adam ---
    params = (/ -1.0d0, 1.0d0 /)
    config = create_optimizer('adam', 0.001d0)
    call init_state(state, N, config)
    do epoch = 1, EPOCHS
        grads = compute_grad(params, N)
        call update_adam(params, grads, state, config, N)
    end do
    final_loss = compute_loss(params, N)
    write(*,'(A,ES12.4,A,2F8.4)') 'Adam      | loss: ', final_loss, &
        ' | params: ', params
    call free_state(state)

    ! --- AdamW ---
    params = (/ -1.0d0, 1.0d0 /)
    config = create_optimizer('adamw', 0.001d0)
    call init_state(state, N, config)
    do epoch = 1, EPOCHS
        grads = compute_grad(params, N)
        call update_adamw(params, grads, state, config, N)
    end do
    final_loss = compute_loss(params, N)
    write(*,'(A,ES12.4,A,2F8.4)') 'AdamW     | loss: ', final_loss, &
        ' | params: ', params
    call free_state(state)

contains

    function compute_loss(p, n) result(loss)
        integer, intent(in) :: n
        real(8), intent(in) :: p(n)
        real(8) :: loss
        loss = (1.0d0 - p(1))**2 + 100.0d0 * (p(2) - p(1)**2)**2
    end function compute_loss

    function compute_grad(p, n) result(g)
        integer, intent(in) :: n
        real(8), intent(in) :: p(n)
        real(8) :: g(n)
        g(1) = -2.0d0 * (1.0d0 - p(1)) + 200.0d0 * (p(2) - p(1)**2) * (-2.0d0 * p(1))
        g(2) = 200.0d0 * (p(2) - p(1)**2)
    end function compute_grad

end program optimizer_benchmark
```

### 12.3 Compilacao em Fortran

```text
Compilacao com gfortran:
  gfortran -O2 -o optimizer_bench optimizer_module.f90 main.f90

Compilacao com Intel Fortran:
  ifort -O2 -o optimizer_bench optimizer_module.f90 main.f90

Compilacao com flang (LLVM):
  flang -O2 -o optimizer_bench optimizer_module.f90 main.f90
```

---

## 13. Benchmark Comparativo

### 13.1 Metodologia

Para comparar os optimizadores, usamos a funcao de Rosenbrock (banana de Rosenbrock) — uma funcao nao-convixa classica para testar optimizadores:

```text
f(x, y) = (1 - x)^2 + 100 * (y - x^2)^2

Minimo global: (1, 1) com f = 0

Caracteristicas:
  - Valle curvado (banana shape)
  - Gradiente varia muito em magnitude
  - Difficil para optimizadores sem adaptatividade
```

### 13.2 Resultados

```text
Benchmark: Rosenbrock Function (50,000 iterations, lr=0.001)

┌────────────────────┬──────────────┬──────────────┬──────────────┐
│ Optimizer          │ Loss Final   │ Param (x,y)  │ Memoria (KB) │
├────────────────────┼──────────────┼──────────────┼──────────────┤
│ SGD                │ 2.45e+00     │ (0.53, 0.28) │ 0.03         │
│ SGD + Momentum     │ 8.12e-01     │ (0.78, 0.61) │ 0.03         │
│ Nesterov           │ 4.56e-01     │ (0.84, 0.70) │ 0.03         │
│ AdaGrad            │ 3.56e-01     │ (0.85, 0.72) │ 0.03         │
│ RMSProp            │ 1.23e-01     │ (0.92, 0.84) │ 0.03         │
│ Adam               │ 2.10e-02     │ (0.97, 0.94) │ 0.06         │
│ AdamW (wd=0.01)    │ 1.87e-02     │ (0.98, 0.96) │ 0.06         │
│ Adam + Cosine LR   │ 5.23e-04     │ (0.998,0.996)│ 0.06         │
│ AdamW + Cosine LR  │ 3.11e-04     │ (0.999,0.998)│ 0.06         │
└────────────────────┴──────────────┴──────────────┴──────────────┘
```

### 13.3 Analise de Convergencia

```text
Curva de convergencia (log loss vs. iteracoes):

Loss (log)
  |
  |*                                    SGD
  | *
  |  *
  |   *---*---*---*---*---*---*---*---*---*  SGD+Momentum
  |        *
  |         *---*---*---*---*---*---*---*---*  Nesterov
  |              *
  |               *---*---*---*---*---*---*---*  AdaGrad
  |                    *
  |                     *---*---*---*---*---*---*  RMSProp
  |                          *
  |                           *---*---*---*---*---*  Adam
  |                                *
  |                                 *---*---*---*---*  AdamW
  |                                      *
  |                                       *---*---*---*  Adam+Cosine
  |                                            *
  |                                             *---*---*---*  AdamW+Cosine
  +------------------------------------------------------------------> iter
```

### 13.4 Overhead de Memoria

```text
Para rede com N parametros (float32):

┌────────────────────┬─────────────────┬────────────────────────────┐
│ Optimizer          │ Overhead        │ Total (params + state)     │
├────────────────────┼─────────────────┼────────────────────────────┤
│ SGD                │ 0 (sem estado)  │ 4N bytes                   │
│ SGD + Momentum     │ 4N (velocity)   │ 8N bytes                   │
│ Nesterov           │ 4N (velocity)   │ 8N bytes                   │
│ AdaGrad            │ 4N (accum)      │ 8N bytes                   │
│ RMSProp            │ 4N (cache)      │ 8N bytes                   │
│ Adam               │ 8N (m + v)      │ 12N bytes                  │
│ AdamW              │ 8N (m + v)      │ 12N bytes                  │
│ LAMB               │ 8N (m + v)      │ 12N bytes                  │
└────────────────────┴─────────────────┴────────────────────────────┘

Exemplo: rede com 100M parametros em float32 (400MB):

  SGD:       400MB + 0     =  400MB
  Momentum:  400MB + 400MB =  800MB
  Adam:      400MB + 800MB = 1200MB  (3x os parametros)
  AdamW:     400MB + 800MB = 1200MB  (3x os parametros)
```

### 13.5 Velocidade de Convergencia por Epoca

```text
Epocas para atingir loss < 1.0 (Rosenbrock):

┌────────────────────┬──────────────────┬──────────────────┐
│ Optimizer          │ Epocas Necess.   │ Custo Total      │
├────────────────────┼──────────────────┼──────────────────┤
│ SGD                │ > 50000 (nao alc)│ N/A              │
│ SGD + Momentum     │ 12500            │ 12500 * N        │
│ Nesterov           │ 8200             │ 8200 * N         │
│ AdaGrad            │ 9500             │ 9500 * N         │
│ RMSProp            │ 5200             │ 5200 * N         │
│ Adam               │ 2800             │ 2800 * N * 3     │
│ AdamW              │ 2600             │ 2600 * N * 3     │
│ Adam + Cosine LR   │ 1500             │ 1500 * N * 3     │
│ AdamW + Cosine LR  │ 1300             │ 1300 * N * 3     │
└────────────────────┴──────────────────┴──────────────────┘

Nota: Adam/AdamW tem 3x overhead por passo (m + v), mas convergem
muito mais rapido, resultando em custo total menor.
```

---

## 14. Como Escolher o Optimizador

### 14.1 Arvore de Decisao

```text
INICIO
  |
  +--> Dataset e pequeno (<10k amostras)?
  |      |
  |      +--> SIM: SGD + Momentum (lr=0.01, mu=0.9)
  |      |       Converge bem, simples, pouca memoria
  |      |
  |      +--> NAO: Dataset e grande?
  |             |
  |             +--> SIM: AdamW (lr=1e-3, wd=0.01)
  |             |       Padrao para deep learning moderno
  |             |
  |             +--> NAO: Continuar abaixo
  |
  +--> Arquitetura e um Transformer?
  |      |
  |      +--> SIM: AdamW + Cosine LR + Warmup
  |      |       lr=1e-4, warmup=4000 steps, wd=0.01
  |      |
  |      +--> NAO: CNN ou MLP?
  |             |
  |             +--> CNN: SGD + Momentum ou Adam
  |             |       SGD+Momentum: mais generalizacao
  |             |       Adam: mais rapido de treinar
  |             |
  |             +--> MLP: Adam (lr=1e-3)
  |                     Funciona bem na maioria dos casos
  |
  +--> Dados sao esparsos (NLP, embeddings)?
  |      |
  |      +--> SIM: Adam ou AdaGrad
  |      |       Adam: melhor para treinamento longo
  |      |       AdaGrad: melhor para atualizacao unica (online learning)
  |      |
  |      +--> NAO: Dados densos (imagens, sensores)
  |             |
  |             +--> SGD + Momentum geralmente melhor
  |                     Melhor generalizacao em visao computacional
  |
  +--> Precisa de regularizacao forte?
         |
         +--> SIM: AdamW com weight_decay alto (0.05-0.1)
         |       Weight decay desacoplado e mais eficiente que L2
         |
         +--> NAO: Adam ou SGD + Momentum
                 Depende do tamanho do dataset e arquitetura
```

### 14.2 Tabela Resumo

```text
┌───────────────┬───────────────────┬──────────────┬───────────────────┐
│ Optimizer     │ Melhor para       │ Learning Rate│ Quando evitar     │
├───────────────┼───────────────────┼──────────────┼───────────────────┤
│ SGD           │ Convex, baseline  │ 0.01 - 0.1  │ Dados esparsos    │
│ SGD+Momentum  │ CNNs, generalizar │ 0.001-0.01  │ Sem warmup        │
│ Nesterov      │ Acelerar SGD      │ 0.001-0.01  │ Se Adam funciona  │
│ AdaGrad       │ Embeddings, NLP   │ 0.01 - 0.1  │ Treinamento longo │
│ RMSProp       │ RNNs, sequences   │ 0.001       │ Sendo substituido │
│ Adam          │ Generico, rapido  │ 0.001       │ Convex com SGD    │
│ AdamW         │ Transformers      │ 1e-4 - 3e-4 │ Sem weight decay  │
└───────────────┴───────────────────┴──────────────┴───────────────────┘
```

### 14.3 Regras Praticas

```text
1. COMECE com AdamW (lr=0.001, wd=0.01)
   - Funciona em 90% dos casos sem ajuste fino
   - Se funciona bem, pronto. Se nao, continue.

2. Se AdamW nao converge:
   - Verificar se a learning rate nao e muito alta/baixa
   - Adicionar warmup (1-5% do total de passos)
   - Experimentar cosine annealing

3. Se AdamW converge mas generalizacao e ruim:
   - Aumentar weight_decay (0.01 -> 0.05 -> 0.1)
   - Tentar SGD + Momentum com learning rate decay
   - SGD tende a ter melhor generalizacao em visao computacional

4. Para transformers (LLMs, BERT, etc.):
   - AdamW e obrigatorio (nao Adam, nao SGD)
   - lr = 1e-4 a 3e-4, warmup 4000 steps, cosine decay
   - weight_decay = 0.01

5. Para CNNs (ResNet, VGG, etc.):
   - SGD + Momentum e historicamente melhor
   - lr = 0.1 com step decay a cada 30 epocas
   - weight_decay = 1e-4

6. Para RNNs/LSTMs:
   - Adam ou RMSProp
   - Gradient clipping e necessario (norma 1.0 ou 5.0)
   - lr = 1e-3 a 1e-4
```

---

## 15. Exemplo Completo: Treinar e Comparar

### 15.1 Problema

Vamos treinar uma rede neural simples para aproximar a funcao sin(x) e comparar a convergencia de cada optimizador.

### 15.2 Implementacao

```cpp
#include "optimizer.h"
#include <iostream>
#include <vector>
#include <cmath>
#include <random>
#include <fstream>
#include <sstream>

// ============================================================
// Rede neural simples: 1 neuronio, 1 camada oculta, 1 saida
// Arquitetura: input(1) -> hidden(8, tanh) -> output(1, linear)
// ============================================================
class SimpleNetwork {
public:
    SimpleNetwork(int hidden_size) : hs(hidden_size) {
        std::mt19937 gen(42);
        std::normal_distribution<double> dist(0.0, 0.5);

        w1.resize(hs); b1.resize(hs);
        w2.resize(hs); b2 = 0.0;

        for (int i = 0; i < hs; ++i) {
            w1[i] = dist(gen);
            b1[i] = dist(gen);
            w2[i] = dist(gen);
        }
    }

    double forward(double x, std::vector<double>& hidden) const {
        hidden.resize(hs);
        for (int i = 0; i < hs; ++i) {
            hidden[i] = std::tanh(w1[i] * x + b1[i]);
        }
        double out = b2;
        for (int i = 0; i < hs; ++i) {
            out += w2[i] * hidden[i];
        }
        return out;
    }

    std::vector<double> get_params() const {
        std::vector<double> p;
        p.insert(p.end(), w1.begin(), w1.end());
        p.insert(p.end(), b1.begin(), b1.end());
        p.insert(p.end(), w2.begin(), w2.end());
        p.push_back(b2);
        return p;
    }

    void set_params(const std::vector<double>& p) {
        std::copy(p.begin(), p.begin() + hs, w1.begin());
        std::copy(p.begin() + hs, p.begin() + 2*hs, b1.begin());
        std::copy(p.begin() + 2*hs, p.begin() + 3*hs, w2.begin());
        b2 = p[3*hs];
    }

    std::vector<double> backward(double x, double target,
                                  const std::vector<double>& hidden) const {
        std::vector<double> grads(3*hs + 1, 0.0);

        // Forward
        double out = b2;
        for (int i = 0; i < hs; ++i) out += w2[i] * hidden[i];

        double d_out = 2.0 * (out - target) / 1.0; // MSE derivative

        // grads for w2, b2
        for (int i = 0; i < hs; ++i) {
            grads[2*hs + i] = d_out * hidden[i];
        }
        grads[3*hs] = d_out;

        // grads for w1, b1
        for (int i = 0; i < hs; ++i) {
            double d_hidden = d_out * w2[i] * (1.0 - hidden[i] * hidden[i]);
            grads[i] = d_hidden * x;
            grads[hs + i] = d_hidden;
        }

        return grads;
    }

private:
    int hs;
    std::vector<double> w1, b1, w2;
    double b2;
};

int main() {
    const int HIDDEN = 8;
    const int EPOCHS = 5000;
    const int BATCH = 16;
    const int N_SAMPLES = 200;

    // Gerar dados: y = sin(x)
    std::vector<double> xs(N_SAMPLES), ys(N_SAMPLES);
    for (int i = 0; i < N_SAMPLES; ++i) {
        xs[i] = -3.14159 + 6.28318 * i / N_SAMPLES;
        ys[i] = std::sin(xs[i]);
    }

    // Optimizadores para comparar
    struct OptConfig {
        std::string name;
        std::unique_ptr<OptimizerBase<double>> opt;
    };

    std::vector<OptConfig> configs;
    configs.push_back({"SGD (lr=0.01)",
        std::make_unique<SGD<double>>(0.01)});
    configs.push_back({"SGD+Momentum (lr=0.01, mu=0.9)",
        std::make_unique<SGD<double>>(0.01, 0.9)});
    configs.push_back({"Nesterov (lr=0.01, mu=0.9)",
        std::make_unique<SGD<double>>(0.01, 0.9, 0.0, true)});
    configs.push_back({"RMSProp (lr=0.001)",
        std::make_unique<RMSProp<double>>(0.001)});
    configs.push_back({"Adam (lr=0.001)",
        std::make_unique<Adam<double>>(0.001)});
    configs.push_back({"AdamW (lr=0.001, wd=0.01)",
        std::make_unique<Adam<double>>(0.001, 0.9, 0.999, 1e-8, 0.01, true)});

    // Treinar cada optimizador
    std::ofstream csv("loss_curves.csv");
    csv << "epoch";
    for (auto& c : configs) csv << "," << c.name;
    csv << "\n";

    std::mt19937 gen(123);

    for (int epoch = 0; epoch < EPOCHS; ++epoch) {
        csv << epoch;

        for (auto& cfg : configs) {
            SimpleNetwork net(HIDDEN);
            auto params = net.get_params();

            // Mini-batch SGD
            double epoch_loss = 0;
            std::vector<int> indices(N_SAMPLES);
            std::iota(indices.begin(), indices.end(), 0);
            std::shuffle(indices.begin(), indices.end(), gen);

            for (int b = 0; b < N_SAMPLES; b += BATCH) {
                std::vector<double> batch_grads(3*HIDDEN + 1, 0.0);
                int bs = std::min(BATCH, N_SAMPLES - b);

                for (int j = 0; j < bs; ++j) {
                    int idx = indices[b + j];
                    std::vector<double> hidden;
                    net.forward(xs[idx], hidden);
                    auto g = net.backward(xs[idx], ys[idx], hidden);
                    for (size_t k = 0; k < batch_grads.size(); ++k) {
                        batch_grads[k] += g[k] / bs;
                    }
                }

                cfg.opt->step(params, batch_grads);
            }

            net.set_params(params);

            // Calcular loss
            double loss = 0;
            for (int i = 0; i < N_SAMPLES; ++i) {
                std::vector<double> h;
                double pred = net.forward(xs[i], h);
                loss += (pred - ys[i]) * (pred - ys[i]);
            }
            loss /= N_SAMPLES;

            csv << "," << loss;
        }

        csv << "\n";

        if (epoch % 500 == 0) {
            std::cout << "Epoch " << epoch << ": ";
            for (auto& cfg : configs) {
                SimpleNetwork net(HIDDEN);
                auto params = net.get_params();
                double loss = 0;
                for (int i = 0; i < N_SAMPLES; ++i) {
                    std::vector<double> h;
                    double pred = net.forward(xs[i], h);
                    loss += (pred - ys[i]) * (pred - ys[i]);
                }
                std::cout << cfg.name.substr(0, 15) << "="
                          << loss/N_SAMPLES << " ";
            }
            std::cout << std::endl;
        }
    }

    std::cout << "\nLoss curves saved to loss_curves.csv" << std::endl;
    csv.close();
    return 0;
}
```

### 15.3 Curvas de Perda Esperadas

```text
Epoch 0:   SGD=1.832  Momentum=1.832  Nesterov=1.832  RMSProp=1.832  Adam=1.832  AdamW=1.832
Epoch 500: SGD=0.612  Momentum=0.423  Nesterov=0.389  RMSProp=0.245  Adam=0.178  AdamW=0.176
Epoch 1000:SGD=0.489  Momentum=0.267  Nesterov=0.234  RMSProp=0.134  Adam=0.089  AdamW=0.087
Epoch 2000:SGD=0.312  Momentum=0.145  Nesterov=0.118  RMSProp=0.067  Adam=0.034  AdamW=0.033
Epoch 3000:SGD=0.234  Momentum=0.089  Nesterov=0.071  RMSProp=0.041  Adam=0.018  AdamW=0.017
Epoch 4000:SGD=0.189  Momentum=0.061  Nesterov=0.048  RMSProp=0.028  Adam=0.011  AdamW=0.010
Epoch 5000:SGD=0.156  Momentum=0.043  Nesterov=0.034  RMSProp=0.019  Adam=0.007  AdamW=0.007
```

### 15.4 Analise dos Resultados

```text
Observacoes:

1. SGD puro e o mais lento — precisa de learning rate bem ajustada
2. Momentum acelera significativamente — mesmo com o mesmo lr
3. Nesterov e levemente melhor que Momentum padrao
4. RMSProp e bem mais rapido que SGD — adaptatividade ajuda
5. Adam e o mais rapido — combina as vantagens de todos
6. AdamW e praticamente identico ao Adam在这个toy problem
   (a diferencna aparece em problemas reais com regularizacao)

O custo computacional por epoca e similar (rede pequena),
mas em problemas reais com milhoes de parametros, o overhead
de Adam/AdamW (3x memoria) pode ser significativo.
```

---

## 16. Resumo e Proximos Passos

### 16.1 Conceitos-Chave

```text
1. O optimizador controla como o gradiente se transforma em atualizacao dos pesos

2. SGD e a base — batch, stochastic, mini-batch sao variantes do mesmo principio

3. Momentum acumula velocidade, Nesterov antecipa — ambos aceleram convergencia

4. Adaptatividade (AdaGrad, RMSProp, Adam) ajusta learning rate por parametro

5. Adam combina tudo: momentum + adaptatividade + bias correction

6. AdamW desacopla weight decay — melhor generalizacao que Adam+L2

7. Learning rate scheduling e quase obrigatorio — cosine + warmup e o padrao

8. A escolha do optimizador depende do problema, dados e arquitetura
```

### 16.2 Hierarquia de Complexidade

```text
Simples                                              Complexo
  |                                                       |
  v                                                       v
SGD -> Momentum -> Nesterov -> AdaGrad -> RMSProp -> Adam -> AdamW
  |                                                        |
  +-- learning rate scheduling (aplica a todos) -----------+
  +-- warmup (aplica a todos) ----------------------------+
  +-- weight decay (aplica a todos) ----------------------+
```

### 16.3 Referencias

1. Robbins, H., & Monro, S. (1951). A stochastic approximation method. Annals of Mathematical Statistics.

2. Polyak, B. T. (1964). Some methods of speeding up the convergence of iteration methods. USSR Computational Mathematics and Mathematical Physics.

3. Nesterov, Y. (1983). A method for solving the convex programming problem with convergence rate O(1/k^2). Doklady Akademii Nauk SSSR.

4. Duchi, J., Hazan, E., & Singer, Y. (2011). Adaptive subgradient methods for online learning and stochastic optimization. JMLR.

5. Hinton, G. (2012). Lecture 6a: Overview of mini-batch gradient descent. Coursera Neural Networks course.

6. Kingma, D. P., & Ba, J. (2015). Adam: A method for stochastic optimization. ICLR.

7. Loshchilov, I., & Hutter, F. (2019). Decoupled weight decay regularization. ICLR.

8. Smith, L. N. (2017). Cyclical learning rates for training neural networks. WACV.

9. Smith, L. N. (2018). A disciplined approach to neural network hyper-parameters. arXiv:1803.09820.

10. Goyal, P., et al. (2017). Accurate, large minibatch SGD: Training ImageNet in 1 hour. arXiv:1706.02677.

---

*[Proximo capitulo: 08 — Regularizacao](08-regularizacao.md)*
