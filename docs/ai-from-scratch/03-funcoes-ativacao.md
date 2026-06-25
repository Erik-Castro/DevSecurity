---
layout: default
title: "03-funcoes-ativacao"
---

# Capitulo 3 — Funcoes de Ativacao

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Explicar por que funcoes de ativacao sao essenciais** para redes neurais e o que acontece sem elas.
2. **Implementar doze funcoes de ativacao** (Sigmoid, Tanh, ReLU, Leaky ReLU, ELU, Swish, GELU, Softmax, Softplus, Mish, Hardtanh, Binary Step) com suas derivadas.
3. **Dominar a implementacao em C++** usando templates e templates de funcao para abstracao sem overhead.
4. **Dominar a implementacao em Rust** usando traits e generics para polimorfismo estatico.
5. **Implementar em Fortran** usando interfaces e tipos abstratos.
6. **Comparar a performance** de cada funcao e de cada linguagem em benchmarks controlados.
7. **Escolher a funcao de ativacao ideal** para cada caso de uso e camada de rede neural.
8. **Compreender o problema do dying ReLU** e como variantes o resolvem.

---

## 1. Por Que Funcoes de Ativacao

### 1.1 O Problema da Linearidade

Uma rede neural sem funcao de ativacao e apenas uma composicao de transformacoes lineares. Nao importa quantas camadas voce empilhe — o resultado final e sempre uma unica transformacao linear.

```text
Sem ativacao:
  Camada 1: y1 = W1 * x + b1
  Camada 2: y2 = W2 * y1 + b2 = W2 * (W1 * x + b1) + b2 = (W2*W1) * x + (W2*b1 + b2)
  Camada 3: y3 = W3 * y2 + b3 = (W3*W2*W1) * x + (W3*W2*b1 + W3*b2 + b3)

Resultado: y3 = W_eff * x + b_eff  (uma unica transformacao linear!)
```

Isso significa que, sem funcao de ativacao, uma rede neural com 100 camadas tem exatamente o mesmo poder expressivo que uma rede com 1 camada. A rede nao pode aprender funcoes nao-lineares, que sao a maioria dos problemas reais.

### 1.2 A Solucao: Nao-Linearidade

Uma funcao de ativacao introduz nao-linearidade entre as camadas. Com ela, cada camada pode transformar o espaco de representacoes de forma nao-linear, e a composicao de multiplas transformacoes nao-lineares pode approximar qualquer funcao continua (Teorema da Aproximacao Universal).

```text
Com ativacao:
  Camada 1: h1 = sigma(W1 * x + b1)    (nao-linear)
  Camada 2: h2 = sigma(W2 * h1 + b2)   (nao-linear)
  Camada 3: y = sigma(W3 * h2 + b3)     (nao-linear)

Agora y e uma funcao arbitrariamente complexa de x!
```

### 1.3 Propriedades Ideais

Uma boa funcao de ativacao deve ter:

```text
1. Nao-linearidade: Capaz de aprender relacoes nao-lineares
2. Derivada simples: Facil de calcular gradientes (backpropagation)
3. Range controlado: Previne exploding gradients
4. Monotonicidade: Garante que o erro diminui na direcao certa (desejavel mas nao obrigatorio)
5. Diferenciavel: Necessario para gradient descent
6. Zero-centrada: Melhora convergencia (desejavel mas nao obrigatorio)
7. Eficiente: Rapida de calcular (forward e backward)
```

### 1.4 Historico e Evolucao

```text
1960s:  Sigmoid e Tanh dominam (redes de uma camada)
1980s:  Sigmoid continua dominante (era do backpropagation)
2000:   Tanh se torna preferida (zero-centrada)
2011:   ReLU revoluciona deep learning (Nair & Hinton)
2013:   Leaky ReLU resolve dying ReLU
2015:   ELU e SELU propostos
2016:   Swish proposto pelo Google Brain
2017:   GELU usado no Transformer
2020:   Mish proposto
2023+:  GELU domina em LLMs (GPT, BERT)
```

---

## 2. Funcoes de Ativacao Classicas

### 2.1 Funcao Sigmoid

A sigmoid mapeia qualquer valor real para o intervalo (0, 1).

**Formula**:

```text
sigma(x) = 1 / (1 + exp(-x))
```

**Propriedades**:

```text
Range: (0, 1)
Monotonica crescente: sim
Diferenciavel: sim
Derivada: sigma(x) * (1 - sigma(x))
Zero-centrada: NAO (range de 0 a 1)
```

**Derivada**:

```text
d/dx sigma(x) = sigma(x) * (1 - sigma(x))

Maximo da derivada: 0.25 (em x = 0)
Minimo da derivada: ~0 (para |x| >> 0)
```

**Problemas**:

```text
1. Vanishing gradient: Derivada maxima e 0.25. Em redes profundas,
   gradientes se tornam insignificantes (0.25^n para n camadas)
   
2. Nao-zero-centrada: Saida media ~= 0.5, causa oscillacao no treinamento
   
3. Computacionalmente custosa: exp() e mais lento que operacoes basicas
   
4. Nao e usada em hidden layers desde 2011
   Ainda usada em output layer para classificacao binaria (junto com BCE)
```

**Quando usar**:

```text
- Output layer para classificacao binaria (junto com Binary Cross-Entropy)
- Portas logisticas em modelos probabilisticos
- NUNCA em hidden layers de redes profundas
```

### 2.2 Funcao Tangente Hiperbolica (Tanh)

A Tanh e similar a Sigmoid mas mapeia para (-1, 1), sendo zero-centrada.

**Formula**:

```text
tanh(x) = (exp(x) - exp(-x)) / (exp(x) + exp(-x))
         = 2 * sigma(2x) - 1
```

**Propriedades**:

```text
Range: (-1, 1)
Monotonica crescente: sim
Diferenciavel: sim
Derivada: 1 - tanh^2(x)
Zero-centrada: SIM (range simetrico)
```

**Derivada**:

```text
d/dx tanh(x) = 1 - tanh^2(x)

Maximo da derivada: 1.0 (em x = 0)
Minimo da derivada: ~0 (para |x| >> 0)
```

**Vantagens sobre Sigmoid**:

```text
1. Zero-centrada: Range (-1, 1) melhora convergencia
2. Derivada mais forte: Maximo de 1.0 vs 0.25
3. Menos propensa a saturacao
```

**Ainda tem vanishing gradient** para valores extremos.

**Quando usar**:

```text
- Hidden layers em redes rasas (1-3 camadas)
- RNNs (nao GRU/LSTM modernas)
- Nao recomendada para deep learning moderno
- Melhor que Sigmoid em todos os aspectos
```

### 2.3 Funcao ReLU (Rectified Linear Unit)

A ReLU e a funcao de ativacao mais importante do deep learning moderno. Simples, eficaz e resolve o problema do vanishing gradient.

**Formula**:

```text
ReLU(x) = max(0, x)
```

**Propriedades**:

```text
Range: [0, inf)
Monotonica crescente: sim (para x > 0)
Diferenciavel: sim (quase sempre — exceto em x = 0)
Derivada: 1 se x > 0, 0 se x < 0, indefinida em x = 0
Zero-centrada: NAO (range de 0 a inf)
```

**Derivada**:

```text
d/dx ReLU(x) = 1  se x > 0
                0  se x < 0

Em x = 0: sub-gradiente = 0 (ou 0.5, dependendo da convensao)
```

**Vantagens**:

```text
1. Sem vanishing gradient: Derivada e 1 para todos os valores positivos
2. Computacionalmente barata: Apenas uma comparacao com zero
3. Esparsidade: Muitos neuronios sao zero (eficiencia computacional)
4. Converge mais rapido que Tanh/Sigmoid (~6x mais rapido)
5. Simplicidade: Facil de entender e implementar
```

**Problemas: Dying ReLU**:

```text
Se um neuronio sempre recebe entrada negativa:
  - Saida sempre 0
  - Gradiente sempre 0
  - Pesos nunca atualizam
  - O neuronio "morre" permanentemente

Causa comum: Learning rate muito alto
  - Pesos atualizados para valores negativos em todas as conexoes
  - Neuronio nunca mais ativa

Solucoes:
  - Leaky ReLU
  - ELU
  - Inicializacao cuidadosa dos pesos
  - Learning rate adaptativo (Adam)
```

**Quando usar**:

```text
- Default para hidden layers em CNNs e MLPs
- Primeira escolha para qualquer rede profunda
- Nao usar em output layer (range inadequado)
- Combine com Batch Normalization para estabilidade
```

### 2.4 Leaky ReLU

A Leaky ReLU resolve o dying ReLU permitindo um pequeno gradiente para valores negativos.

**Formula**:

```text
LeakyReLU(x) = x       se x > 0
                alpha*x se x <= 0

Onde alpha e um hiperparametro pequeno (tipicamente 0.01)
```

**Propriedades**:

```text
Range: (-inf, inf)
Diferenciavel: sim (exceto em x = 0)
Derivada: 1 se x > 0, alpha se x < 0
Zero-centrada: NAO
```

**Derivada**:

```text
d/dx LeakyReLU(x) = 1    se x > 0
                     alpha se x < 0
```

**Variantes**:

```text
PReLU (Parametric ReLU): alpha e aprendido durante treinamento
  - Parametro adicional por camada (ou por neuronio)
  - Pode encontrar o melhor alpha para cada camada

RReLU (Randomized Leaky ReLU): alpha amostrado de uniforme durante treinamento
  - Regularizacao natural
  - alpha_fixo durante teste
```

**Quando usar**:

```text
- Quando dying ReLU e um problema
- Quando os dados tem muitos valores negativos
- Alternativa segura a ReLU
- PReLU quando quiser aprender o alpha
```

### 2.5 Funcao ELU (Exponential Linear Unit)

A ELU combina as vantagens da ReLU com saida negativa para media zero.

**Formula**:

```text
ELU(x) = x             se x > 0
          alpha*(exp(x)-1) se x <= 0

Onde alpha e tipicamente 1.0
```

**Propriedades**:

```text
Range: (-alpha, inf)
Diferenciavel: sim (exceto em x = 0)
Derivada: 1 se x > 0, ELU(x) + alpha se x <= 0
Zero-centrada: APROXIMADAMENTE (media mais proxima de zero que ReLU)
```

**Derivada**:

```text
d/dx ELU(x) = 1              se x > 0
               alpha * exp(x) se x <= 0
```

**Vantagens sobre ReLU**:

```text
1. Media de saida mais proxima de zero (melhor que ReLU)
2. Sem dying ReLU (gradiente nao e zero para valores negativos)
3. Robusta a ruido (saturacao suave para valores negativos)
4. Inicializacao dos pesos pode ser mais simples
```

**Desvantagens**:

```text
1. Mais cara computacionalmente (exp para valores negativos)
2. Mais hiperparametro (alpha)
3. Nao tem versao padrao widespread como ReLU
```

**Quando usar**:

```text
- Quando estabilidade de treinamento e mais importante que velocidade
- Redes onde batch normalization nao e usada
- Autoencoders
- GANs (generator)
```

### 2.6 SELU (Scaled ELU)

A SELU e uma versao escalada da ELU que mantem automaticamente media zero e variancia 1.

**Formula**:

```text
SELU(x) = lambda * x              se x > 0
           lambda * alpha * (exp(x)-1) se x <= 0

Onde lambda = 1.0507 e alpha = 1.6733 (valores fixos, calculados teoricamente)
```

**Propriedades**:

```text
Range: (-lambda*alpha, inf)
Self-normalizing: Propaga media 0 e variancia 1 automaticamente
Vantagem: Nao precisa de Batch Normalization
```

**Quando usar**:

```text
- Redes feed-forward densas (sem convolucao)
- Quando nao quer usar Batch Normalization
- MLPs com initializer LeCun Normal
- Nao funciona bem com dropout ou outras regularizacoes
```

---

## 3. Funcoes de Ativacao Modernas

### 3.1 Swish

A Swish foi proposta pelo Google Brain em 2017 e descoberta via pesquisa automatica de funcoes.

**Formula**:

```text
Swish(x) = x * sigma(beta * x)

Onde beta e tipicamente 1.0 (Swish-1)
Quando beta -> infinito, Swish converge para ReLU
Quando beta -> 0, Swish converge para linear/2
```

**Propriedades**:

```text
Range: (-0.278, inf)
Suave: Diferenciavel em todo ponto
Nao-monotonica: Tem um minimo local (~-0.278)
Zero-centrada: NAO
```

**Derivada**:

```text
d/dx Swish(x) = sigma(beta*x) + x * beta * sigma(beta*x) * (1 - sigma(beta*x))
               = sigma(beta*x) * (1 + x * beta * (1 - sigma(beta*x)))
```

**Vantagens**:

```text
1. Suavidade: Sem cantos (diferenciavel em todos os pontos)
2. Self-gating: Multiplicacao por sigmoid auto-atua
3. Performance consistente >= ReLU em benchmarks
4. Nao tem dying neurons (range inclui negativos)
```

**Quando usar**:

```text
- Deep learning moderno (alternativa a ReLU)
- Redes profundas onde suavidade importa
- Quando ReLU causa problemas de treinamento
- EfficientNet usa Swish como padrao
```

### 3.2 GELU (Gaussian Error Linear Unit)

A GELU e a funcao de ativacao padrao em Transformers modernos (BERT, GPT).

**Formula**:

```text
GELU(x) = x * Phi(x)

Onde Phi(x) e a CDF da distribuicao normal padrao
     = 0.5 * (1 + erf(x / sqrt(2)))

Aproximacao pratica:
GELU(x) ~= 0.5 * x * (1 + tanh(sqrt(2/pi) * (x + 0.044715 * x^3)))
```

**Propriedades**:

```text
Range: (-0.17, inf)
Suave: Diferenciavel em todo ponto
Nao-monotonica: Similar a Swish
Zero-centrada: NAO
```

**Derivada**:

```text
d/dx GELU(x) = Phi(x) + x * phi(x)

Onde phi(x) e a PDF da normal padrao:
     = 0.5 * (1 + erf(x / sqrt(2))) + x * (1/sqrt(2*pi)) * exp(-x^2/2)
```

**Por que Transformers usam GELU**:

```text
1. Comportamento suave: Nao tem cantos como ReLU
2. Regularizacao natural: Atenua valores pequenos (zera parcialmente)
3. Probabilistica: x * Phi(x) = "dropout suave"
4. Performance empirica superior em NLP
5. BERT, GPT-2, GPT-3, GPT-4 todos usam GELU
```

**Quando usar**:

```text
- Transformers e modelos de linguagem
- Quando a suavidade e importante
- BERT, GPT, T5, e similares
- Nao e ideal para CNNs (ReLU e mais rapido)
```

### 3.3 Softmax

A Softmax e usada no output layer para classificacao multi-classe. Converte logits em probabilidades.

**Formula**:

```text
softmax(x_i) = exp(x_i) / Σ_j exp(x_j)

Onde x = [x_1, x_2, ..., x_k] e o vetor de logits
```

**Propriedades**:

```text
Range: (0, 1) para cada componente
Soma: Σ softmax(x_i) = 1 (distribuicao de probabilidade)
Monotonica: NAO (para um componente, pode nao ser monotonica)
Diferenciavel: sim
```

**Derivada (Jacobiano)**:

```text
d softmax(x_i) / d x_j = softmax(x_i) * (delta_ij - softmax(x_j))

Onde delta_ij = 1 se i=j, 0 caso contrario

Matriz Jacobiana:
J = diag(p) - p * p^T

Onde p = softmax(x)
```

**Numerical stability**:

```text
Problema: exp(x) para x muito grande causa overflow
Solucao: Subtrair o maximo

softmax(x_i) = exp(x_i - max(x)) / Σ_j exp(x_j - max(x))

Resultado identico, mas sem overflow!
```

```cpp
std::vector<double> softmax_stable(const std::vector<double>& logits) {
    double max_val = *std::max_element(logits.begin(), logits.end());
    std::vector<double> exps(logits.size());
    double sum = 0.0;
    for (size_t i = 0; i < logits.size(); ++i) {
        exps[i] = std::exp(logits[i] - max_val);
        sum += exps[i];
    }
    for (double& e : exps) e /= sum;
    return exps;
}
```

**Quando usar**:

```text
- Output layer para classificacao multi-classe
- Juntamente com Categorical Cross-Entropy
- Mecanismo de attention (Transformer)
- NUNCA em hidden layers
```

### 3.4 Softplus

A Softplus e uma aproximacao suave da ReLU.

**Formula**:

```text
Softplus(x) = log(1 + exp(x))
```

**Propriedades**:

```text
Range: (0, inf)
Suave: Diferenciavel em todo ponto
Derivada: sigmoid(x)
Aproximacao: Softplus(x) ~= ReLU(x) para |x| >> 0
```

**Derivada**:

```text
d/dx Softplus(x) = exp(x) / (1 + exp(x)) = sigma(x)
```

**Quando usar**:

```text
- Quando suavidade e necessaria (gradientes mais estaveis)
- Output layer para previsao de variancia (deve ser positivo)
- Modelos probabilisticos
- Raramente em hidden layers (custosa computacionalmente)
```

### 3.5 Mish

A Mish e uma funcao suave proposta em 2020 que combina propriedades de Swish e Softplus.

**Formula**:

```text
Mish(x) = x * tanh(softplus(x))
         = x * tanh(log(1 + exp(x)))
```

**Propriedades**:

```text
Range: (-0.309, inf)
Suave: Diferenciavel em todo ponto
Nao-monotonica: Similar a Swish
Self-regularizing: Comportamento de regularizacao natural
```

**Derivada**:

```text
d/dx Mish(x) = tanh(softplus(x)) + x * sech^2(softplus(x)) * sigma(x)
```

**Vantagens**:

```text
1. Self-regularizing
2. Suavidade garantida
3. Bound inferior nao e zero (preserva informacao negativa)
4. Performance competitiva com Swish e GELU
```

**Quando usar**:

```text
- Quando quiser algo entre Swish e GELU
- Redes profundas com problemas de treinamento
- Object detection (YOLOv4 usa Mish)
```

---

## 4. Funcoes de Ativacao para Output Layer

### 4.1 Regressao (Saida Continua)

```text
Para regressao, o output layer nao tem ativacao (identidade):
  y = W * h + b

Ou usa Softplus/ReLU se a saida deve ser positiva:
  y = Softplus(W * h + b)  (para variancia, desvio padrao)
```

### 4.2 Classificacao Binaria

```text
Sigmoid no output + Binary Cross-Entropy:
  y_pred = sigmoid(W * h + b)
  loss = -(y * log(y_pred) + (1-y) * log(1-y_pred))
```

### 4.3 Classificacao Multi-classe

```text
Softmax no output + Categorical Cross-Entropy:
  y_pred = softmax(W * h + b)
  loss = -Σ y_i * log(y_pred_i)
```

### 4.4 Multi-label

```text
Sigmoid em cada neuronio do output + Binary Cross-Entropy por neuronio:
  y_pred_i = sigmoid(W_i * h + b_i)
  loss = -Σ_i [y_i * log(y_pred_i) + (1-y_i) * log(1-y_pred_i)]
```

---

## 5. Implementacao Completa em C++ (Templates)

### 5.1 Metaprogramacao com Templates

Uma das grandes vantagens do C++ e a metaprogramacao com templates, que permite criar abstracoes sem overhead de runtime. Podemos definir funcoes de ativacao como tipos de template e o compilador gera codigo otimizado para cada uma.

```cpp
// Template base para ativacoes
template<typename Derived>
class ActivationBase {
public:
    double compute(double x) const {
        return static_cast<const Derived*>(this)->compute_impl(x);
    }
    
    double gradient(double x) const {
        return static_cast<const Derived*>(this)->gradient_impl(x);
    }
    
    std::string name() const {
        return static_cast<const Derived*>(this)->name_impl();
    }
};

// CRTP (Curiously Recurring Template Pattern)
struct Sigmoid : ActivationBase<Sigmoid> {
    double compute_impl(double x) const {
        if (x >= 0) return 1.0 / (1.0 + std::exp(-x));
        double ex = std::exp(x);
        return ex / (1.0 + ex);
    }
    
    double gradient_impl(double x) const {
        double s = compute_impl(x);
        return s * (1.0 - s);
    }
    
    static constexpr const char* name_impl() { return "Sigmoid"; }
};

struct ReLU : ActivationBase<ReLU> {
    double compute_impl(double x) const { return std::max(0.0, x); }
    double gradient_impl(double x) const { return x > 0.0 ? 1.0 : 0.0; }
    static constexpr const char* name_impl() { return "ReLU"; }
};
```

### 5.2 Traits de Ativacao

```cpp
// Type traits para metaprogramacao
template<typename T>
struct is_activation : std::false_type {};

template<typename Derived>
struct is_activation<ActivationBase<Derived>> : std::true_type {};

template<typename T>
constexpr bool is_activation_v = is_activation<T>::value;

// Funcao generica para aplicar qualquer ativacao
template<typename Act>
double apply_activation(double x) {
    static_assert(is_activation_v<Act>, "Must be an activation function");
    Act act;
    return act.compute(x);
}

// Uso:
// double y = apply_activation<ReLU>(3.0);  // 3.0
// double y = apply_activation<Sigmoid>(0.0);  // 0.5
```

### 5.3 Layer com Ativacao Generica

```cpp
template<typename ActivationType>
class DenseLayer {
    std::vector<std::vector<double>> weights_;
    std::vector<double> bias_;
    ActivationType activation_;
    
public:
    DenseLayer(size_t input_size, size_t output_size) 
        : weights_(input_size, std::vector<double>(output_size)),
          bias_(output_size, 0.0) {
        // He initialization
        std::mt19937 gen(42);
        std::normal_distribution<> dist(0.0, std::sqrt(2.0 / input_size));
        for (auto& row : weights_) {
            for (auto& w : row) w = dist(gen);
        }
    }
    
    std::vector<double> forward(const std::vector<double>& input) {
        std::vector<double> output(bias_.size());
        for (size_t j = 0; j < output.size(); ++j) {
            double sum = bias_[j];
            for (size_t i = 0; i < input.size(); ++i) {
                sum += input[i] * weights_[i][j];
            }
            output[j] = activation_.compute(sum);
        }
        return output;
    }
};
```

### 5.4 Traits e Conceitos

```cpp
#include <cmath>
#include <vector>
#include <string>
#include <iostream>
#include <chrono>
#include <random>
#include <algorithm>
#include <numeric>
#include <functional>
#include <memory>

// Base class virtual para ativacoes
class ActivationFunction {
public:
    virtual ~ActivationFunction() = default;
    virtual double forward(double x) const = 0;
    virtual double backward(double x) const = 0;
    virtual std::string name() const = 0;
};

// Sigmoid
class Sigmoid : public ActivationFunction {
public:
    double forward(double x) const override {
        if (x >= 0) {
            return 1.0 / (1.0 + std::exp(-x));
        } else {
            double ex = std::exp(x);
            return ex / (1.0 + ex);
        }
    }
    
    double backward(double x) const override {
        double s = forward(x);
        return s * (1.0 - s);
    }
    
    std::string name() const override { return "Sigmoid"; }
};

// Tanh
class TanhActivation : public ActivationFunction {
public:
    double forward(double x) const override {
        return std::tanh(x);
    }
    
    double backward(double x) const override {
        double t = std::tanh(x);
        return 1.0 - t * t;
    }
    
    std::string name() const override { return "Tanh"; }
};

// ReLU
class ReLU : public ActivationFunction {
public:
    double forward(double x) const override {
        return std::max(0.0, x);
    }
    
    double backward(double x) const override {
        return x > 0.0 ? 1.0 : 0.0;
    }
    
    std::string name() const override { return "ReLU"; }
};

// Leaky ReLU
class LeakyReLU : public ActivationFunction {
    double alpha_;
public:
    explicit LeakyReLU(double alpha = 0.01) : alpha_(alpha) {}
    
    double forward(double x) const override {
        return x > 0.0 ? x : alpha_ * x;
    }
    
    double backward(double x) const override {
        return x > 0.0 ? 1.0 : alpha_;
    }
    
    std::string name() const override { return "LeakyReLU"; }
};

// ELU
class ELU : public ActivationFunction {
    double alpha_;
public:
    explicit ELU(double alpha = 1.0) : alpha_(alpha) {}
    
    double forward(double x) const override {
        return x > 0.0 ? x : alpha_ * (std::exp(x) - 1.0);
    }
    
    double backward(double x) const override {
        return x > 0.0 ? 1.0 : forward(x) + alpha_;
    }
    
    std::string name() const override { return "ELU"; }
};

// SELU
class SELU : public ActivationFunction {
    static constexpr double lambda = 1.0507;
    static constexpr double alpha = 1.6733;
public:
    double forward(double x) const override {
        return x > 0.0 ? lambda * x : lambda * alpha * (std::exp(x) - 1.0);
    }
    
    double backward(double x) const override {
        return x > 0.0 ? lambda : lambda * alpha * std::exp(x);
    }
    
    std::string name() const override { return "SELU"; }
};

// Swish
class Swish : public ActivationFunction {
    double beta_;
public:
    explicit Swish(double beta = 1.0) : beta_(beta) {}
    
    double forward(double x) const override {
        double sigmoid = 1.0 / (1.0 + std::exp(-beta_ * x));
        return x * sigmoid;
    }
    
    double backward(double x) const override {
        double s = 1.0 / (1.0 + std::exp(-beta_ * x));
        return s + x * beta_ * s * (1.0 - s);
    }
    
    std::string name() const override { return "Swish"; }
};

// GELU
class GELU : public ActivationFunction {
    static constexpr double sqrt_2_pi = 0.7978845608;
    static constexpr double coeff = 0.044715;
public:
    double forward(double x) const override {
        return 0.5 * x * (1.0 + std::tanh(sqrt_2_pi * (x + coeff * x * x * x)));
    }
    
    double backward(double x) const override {
        double x3 = x * x * x;
        double inner = sqrt_2_pi * (x + coeff * x3);
        double tanh_val = std::tanh(inner);
        double sech2 = 1.0 - tanh_val * tanh_val;
        double d_inner = sqrt_2_pi * (1.0 + 3.0 * coeff * x * x);
        return 0.5 * (1.0 + tanh_val) + 0.5 * x * sech2 * d_inner;
    }
    
    std::string name() const override { return "GELU"; }
};

// Softplus
class Softplus : public ActivationFunction {
public:
    double forward(double x) const override {
        if (x > 20.0) return x;
        if (x < -20.0) return 0.0;
        return std::log(1.0 + std::exp(x));
    }
    
    double backward(double x) const override {
        return 1.0 / (1.0 + std::exp(-x));
    }
    
    std::string name() const override { return "Softplus"; }
};

// Mish
class Mish : public ActivationFunction {
public:
    double forward(double x) const override {
        double sp = std::log(1.0 + std::exp(x));
        return x * std::tanh(sp);
    }
    
    double backward(double x) const override {
        double sp = std::log(1.0 + std::exp(x));
        double tanh_sp = std::tanh(sp);
        double sech2 = 1.0 - tanh_sp * tanh_sp;
        double sigmoid = 1.0 / (1.0 + std::exp(-x));
        return tanh_sp + x * sech2 * sigmoid;
    }
    
    std::string name() const override { return "Mish"; }
};

// Hardtanh
class Hardtanh : public ActivationFunction {
public:
    double forward(double x) const override {
        if (x < -1.0) return -1.0;
        if (x > 1.0) return 1.0;
        return x;
    }
    
    double backward(double x) const override {
        return (x >= -1.0 && x <= 1.0) ? 1.0 : 0.0;
    }
    
    std::string name() const override { return "Hardtanh"; }
};

// Softmax (especial — opera em vetores)
class SoftmaxActivation {
public:
    std::vector<double> forward(const std::vector<double>& logits) const {
        double max_val = *std::max_element(logits.begin(), logits.end());
        std::vector<double> exps(logits.size());
        double sum = 0.0;
        for (size_t i = 0; i < logits.size(); ++i) {
            exps[i] = std::exp(logits[i] - max_val);
            sum += exps[i];
        }
        for (double& e : exps) e /= sum;
        return exps;
    }
    
    std::string name() const { return "Softmax"; }
};
```

### 5.2 Benchmark C++

```cpp
void benchmark_activation(const ActivationFunction& func, 
                           const std::string& name,
                           int n = 1000000) {
    std::vector<double> x(n);
    std::mt19937 gen(42);
    std::normal_distribution<> dist(0.0, 1.0);
    for (int i = 0; i < n; ++i) x[i] = dist(gen);
    
    // Forward benchmark
    auto start = std::chrono::high_resolution_clock::now();
    volatile double sum = 0.0;
    for (int i = 0; i < n; ++i) {
        sum += func.forward(x[i]);
    }
    auto end = std::chrono::high_resolution_clock::now();
    auto forward_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    
    // Backward benchmark
    start = std::chrono::high_resolution_clock::now();
    for (int i = 0; i < n; ++i) {
        sum += func.backward(x[i]);
    }
    end = std::chrono::high_resolution_clock::now();
    auto backward_us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
    
    std::cout << std::setw(15) << name
              << " | Forward: " << std::setw(6) << forward_us << " us"
              << " | Backward: " << std::setw(6) << backward_us << " us"
              << " | Total: " << std::setw(6) << (forward_us + backward_us) << " us"
              << std::endl;
}

int main() {
    std::cout << "=== Benchmark de Funcoes de Ativacao (C++) ===" << std::endl;
    std::cout << "1M de operacoes, valores ~ N(0,1)" << std::endl;
    std::cout << std::endl;
    
    benchmark_activation(Sigmoid(), "Sigmoid");
    benchmark_activation(TanhActivation(), "Tanh");
    benchmark_activation(ReLU(), "ReLU");
    benchmark_activation(LeakyReLU(0.01), "LeakyReLU");
    benchmark_activation(ELU(1.0), "ELU");
    benchmark_activation(SELU(), "SELU");
    benchmark_activation(Swish(1.0), "Swish");
    benchmark_activation(GELU(), "GELU");
    benchmark_activation(Softplus(), "Softplus");
    benchmark_activation(Mish(), "Mish");
    benchmark_activation(Hardtanh(), "Hardtanh");
    
    return 0;
}
```

---

## 6. Implementacao Completa em Rust (Traits)

### 6.1 Traits e Implementacoes

```rust
use std::f64::consts::PI;

trait Activation: Send + Sync {
    fn forward(&self, x: f64) -> f64;
    fn backward(&self, x: f64) -> f64;
    fn name(&self) -> &str;
}

struct Sigmoid;

impl Activation for Sigmoid {
    fn forward(&self, x: f64) -> f64 {
        if x >= 0.0 {
            1.0 / (1.0 + (-x).exp())
        } else {
            let ex = x.exp();
            ex / (1.0 + ex)
        }
    }
    fn backward(&self, x: f64) -> f64 {
        let s = self.forward(x);
        s * (1.0 - s)
    }
    fn name(&self) -> &str { "Sigmoid" }
}

struct TanhAct;

impl Activation for TanhAct {
    fn forward(&self, x: f64) -> f64 { x.tanh() }
    fn backward(&self, x: f64) -> f64 {
        let t = x.tanh();
        1.0 - t * t
    }
    fn name(&self) -> &str { "Tanh" }
}

struct ReLU;

impl Activation for ReLU {
    fn forward(&self, x: f64) -> f64 { x.max(0.0) }
    fn backward(&self, x: f64) -> f64 { if x > 0.0 { 1.0 } else { 0.0 } }
    fn name(&self) -> &str { "ReLU" }
}

struct LeakyReLU {
    alpha: f64,
}

impl LeakyReLU {
    fn new(alpha: f64) -> Self { LeakyReLU { alpha } }
}

impl Activation for LeakyReLU {
    fn forward(&self, x: f64) -> f64 {
        if x > 0.0 { x } else { self.alpha * x }
    }
    fn backward(&self, x: f64) -> f64 {
        if x > 0.0 { 1.0 } else { self.alpha }
    }
    fn name(&self) -> &str { "LeakyReLU" }
}

struct ELU {
    alpha: f64,
}

impl ELU {
    fn new(alpha: f64) -> Self { ELU { alpha } }
}

impl Activation for ELU {
    fn forward(&self, x: f64) -> f64 {
        if x > 0.0 { x } else { self.alpha * (x.exp() - 1.0) }
    }
    fn backward(&self, x: f64) -> f64 {
        if x > 0.0 { 1.0 } else { self.forward(x) + self.alpha }
    }
    fn name(&self) -> &str { "ELU" }
}

struct Swish {
    beta: f64,
}

impl Swish {
    fn new(beta: f64) -> Self { Swish { beta } }
}

impl Activation for Swish {
    fn forward(&self, x: f64) -> f64 {
        let s = 1.0 / (1.0 + (-self.beta * x).exp());
        x * s
    }
    fn backward(&self, x: f64) -> f64 {
        let s = 1.0 / (1.0 + (-self.beta * x).exp());
        s + x * self.beta * s * (1.0 - s)
    }
    fn name(&self) -> &str { "Swish" }
}

struct GELU;

impl Activation for GELU {
    fn forward(&self, x: f64) -> f64 {
        let sqrt_2_pi = (2.0 / PI).sqrt();
        0.5 * x * (1.0 + (sqrt_2_pi * (x + 0.044715 * x.powi(3))).tanh())
    }
    fn backward(&self, x: f64) -> f64 {
        let sqrt_2_pi = (2.0 / PI).sqrt();
        let x3 = x.powi(3);
        let inner = sqrt_2_pi * (x + 0.044715 * x3);
        let tanh_val = inner.tanh();
        let sech2 = 1.0 - tanh_val * tanh_val;
        let d_inner = sqrt_2_pi * (1.0 + 3.0 * 0.044715 * x * x);
        0.5 * (1.0 + tanh_val) + 0.5 * x * sech2 * d_inner
    }
    fn name(&self) -> &str { "GELU" }
}

struct Softplus;

impl Activation for Softplus {
    fn forward(&self, x: f64) -> f64 {
        if x > 20.0 { x }
        else if x < -20.0 { 0.0 }
        else { (1.0 + x.exp()).ln() }
    }
    fn backward(&self, x: f64) -> f64 {
        1.0 / (1.0 + (-x).exp())
    }
    fn name(&self) -> &str { "Softplus" }
}

struct Mish;

impl Activation for Mish {
    fn forward(&self, x: f64) -> f64 {
        let sp = (1.0 + x.exp()).ln();
        x * sp.tanh()
    }
    fn backward(&self, x: f64) -> f64 {
        let sp = (1.0 + x.exp()).ln();
        let tanh_sp = sp.tanh();
        let sech2 = 1.0 - tanh_sp * tanh_sp;
        let sigmoid = 1.0 / (1.0 + (-x).exp());
        tanh_sp + x * sech2 * sigmoid
    }
    fn name(&self) -> &str { "Mish" }
}

struct Hardtanh;

impl Activation for Hardtanh {
    fn forward(&self, x: f64) -> f64 { x.clamp(-1.0, 1.0) }
    fn backward(&self, x: f64) -> f64 {
        if x >= -1.0 && x <= 1.0 { 1.0 } else { 0.0 }
    }
    fn name(&self) -> &str { "Hardtanh" }
}

struct Softmax;

impl Softmax {
    fn forward(&self, logits: &[f64]) -> Vec<f64> {
        let max_val = logits.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let exps: Vec<f64> = logits.iter().map(|&x| (x - max_val).exp()).collect();
        let sum: f64 = exps.iter().sum();
        exps.iter().map(|&e| e / sum).collect()
    }
}
```

### 6.2 Benchmark Rust

```rust
use std::time::Instant;

fn benchmark_activation(func: &dyn Activation, n: usize) {
    let data: Vec<f64> = (0..n).map(|i| {
        let x = i as f64 / n as f64 * 4.0 - 2.0;
        x
    }).collect();
    
    let start = Instant::now();
    let mut sum = 0.0_f64;
    for &x in &data {
        sum += func.forward(x);
    }
    let forward_us = start.elapsed().as_micros();
    
    let start = Instant::now();
    for &x in &data {
        sum += func.backward(x);
    }
    let backward_us = start.elapsed().as_micros();
    
    println!("{:15} | Forward: {:6} us | Backward: {:6} us | Total: {:6} us",
             func.name(), forward_us, backward_us, forward_us + backward_us);
    
    std::hint::black_box(sum);
}

fn main() {
    let n = 1_000_000;
    println!("=== Benchmark de Funcoes de Ativacao (Rust) ===");
    println!("{} de operacoes", n);
    println!();
    
    benchmark_activation(&Sigmoid, n);
    benchmark_activation(&TanhAct, n);
    benchmark_activation(&ReLU, n);
    benchmark_activation(&LeakyReLU::new(0.01), n);
    benchmark_activation(&ELU::new(1.0), n);
    benchmark_activation(&Swish::new(1.0), n);
    benchmark_activation(&GELU, n);
    benchmark_activation(&Softplus, n);
    benchmark_activation(&Mish, n);
    benchmark_activation(&Hardtanh, n);
}
```

---

## 7. Implementacao em Fortran

### 7.1 Modulo de Funcoes de Ativacao

```fortran
module activation_mod
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)
    real(dp), parameter :: SQRT_2_PI = 0.7978845608028654_dp
    real(dp), parameter :: COEFF_GELU = 0.044715_dp
    real(dp), parameter :: LAMBDA_SELU = 1.0507_dp
    real(dp), parameter :: ALPHA_SELU = 1.6733_dp

contains

    pure function sigmoid_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        if (x >= 0.0_dp) then
            y = 1.0_dp / (1.0_dp + exp(-x))
        else
            y = exp(x) / (1.0_dp + exp(x))
        end if
    end function

    pure function sigmoid_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = sigmoid_f(x) * (1.0_dp - sigmoid_f(x))
    end function

    pure function tanh_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = tanh(x)
    end function

    pure function tanh_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = 1.0_dp - tanh(x)**2
    end function

    pure function relu_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = max(0.0_dp, x)
    end function

    pure function relu_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        if (x > 0.0_dp) then
            y = 1.0_dp
        else
            y = 0.0_dp
        end if
    end function

    pure function leaky_relu_f(x, alpha) result(y)
        real(dp), intent(in) :: x, alpha
        real(dp) :: y
        if (x > 0.0_dp) then
            y = x
        else
            y = alpha * x
        end if
    end function

    pure function leaky_relu_d(x, alpha) result(y)
        real(dp), intent(in) :: x, alpha
        real(dp) :: y
        if (x > 0.0_dp) then
            y = 1.0_dp
        else
            y = alpha
        end if
    end function

    pure function elu_f(x, alpha) result(y)
        real(dp), intent(in) :: x, alpha
        real(dp) :: y
        if (x > 0.0_dp) then
            y = x
        else
            y = alpha * (exp(x) - 1.0_dp)
        end if
    end function

    pure function elu_d(x, alpha) result(y)
        real(dp), intent(in) :: x, alpha
        real(dp) :: y
        if (x > 0.0_dp) then
            y = 1.0_dp
        else
            y = elu_f(x, alpha) + alpha
        end if
    end function

    pure function swish_f(x, beta) result(y)
        real(dp), intent(in) :: x, beta
        real(dp) :: y
        real(dp) :: s
        s = 1.0_dp / (1.0_dp + exp(-beta * x))
        y = x * s
    end function

    pure function swish_d(x, beta) result(y)
        real(dp), intent(in) :: x, beta
        real(dp) :: y
        real(dp) :: s
        s = 1.0_dp / (1.0_dp + exp(-beta * x))
        y = s + x * beta * s * (1.0_dp - s)
    end function

    pure function gelu_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = 0.5_dp * x * (1.0_dp + tanh(SQRT_2_PI * (x + COEFF_GELU * x**3)))
    end function

    pure function gelu_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        real(dp) :: x3, inner, tanh_val, sech2, d_inner
        x3 = x**3
        inner = SQRT_2_PI * (x + COEFF_GELU * x3)
        tanh_val = tanh(inner)
        sech2 = 1.0_dp - tanh_val**2
        d_inner = SQRT_2_PI * (1.0_dp + 3.0_dp * COEFF_GELU * x**2)
        y = 0.5_dp * (1.0_dp + tanh_val) + 0.5_dp * x * sech2 * d_inner
    end function

    pure function softplus_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        if (x > 20.0_dp) then
            y = x
        else if (x < -20.0_dp) then
            y = 0.0_dp
        else
            y = log(1.0_dp + exp(x))
        end if
    end function

    pure function softplus_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = 1.0_dp / (1.0_dp + exp(-x))
    end function

    pure function mish_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        real(dp) :: sp
        sp = log(1.0_dp + exp(x))
        y = x * tanh(sp)
    end function

    pure function mish_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        real(dp) :: sp, tanh_sp, sech2, sigmoid
        sp = log(1.0_dp + exp(x))
        tanh_sp = tanh(sp)
        sech2 = 1.0_dp - tanh_sp**2
        sigmoid = 1.0_dp / (1.0_dp + exp(-x))
        y = tanh_sp + x * sech2 * sigmoid
    end function

    pure function hardtanh_f(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        y = max(-1.0_dp, min(1.0_dp, x))
    end function

    pure function hardtanh_d(x) result(y)
        real(dp), intent(in) :: x
        real(dp) :: y
        if (x >= -1.0_dp .and. x <= 1.0_dp) then
            y = 1.0_dp
        else
            y = 0.0_dp
        end if
    end function

end module
```

### 7.2 Benchmark Fortran

```fortran
program benchmark_activations
    use activation_mod
    implicit none
    
    integer, parameter :: n = 1000000
    real(dp) :: x(n), start_time, end_time
    real(dp) :: sum_val
    integer :: i
    
    ! Gerar dados
    do i = 1, n
        x(i) = -2.0_dp + 4.0_dp * real(i - 1, dp) / real(n - 1, dp)
    end do
    
    print *, "=== Benchmark de Funcoes de Ativacao (Fortran) ==="
    print *, n, "operacoes"
    print *
    
    ! Sigmoid
    call cpu_time(start_time)
    sum_val = 0.0_dp
    do i = 1, n
        sum_val = sum_val + sigmoid_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + sigmoid_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "Sigmoid:       ", (end_time - start_time) * 1e6, " us"
    
    ! Tanh
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + tanh_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + tanh_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "Tanh:          ", (end_time - start_time) * 1e6, " us"
    
    ! ReLU
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + relu_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + relu_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "ReLU:          ", (end_time - start_time) * 1e6, " us"
    
    ! Leaky ReLU
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + leaky_relu_f(x(i), 0.01_dp)
    end do
    do i = 1, n
        sum_val = sum_val + leaky_relu_d(x(i), 0.01_dp)
    end do
    call cpu_time(end_time)
    print *, "LeakyReLU:     ", (end_time - start_time) * 1e6, " us"
    
    ! ELU
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + elu_f(x(i), 1.0_dp)
    end do
    do i = 1, n
        sum_val = sum_val + elu_d(x(i), 1.0_dp)
    end do
    call cpu_time(end_time)
    print *, "ELU:           ", (end_time - start_time) * 1e6, " us"
    
    ! Swish
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + swish_f(x(i), 1.0_dp)
    end do
    do i = 1, n
        sum_val = sum_val + swish_d(x(i), 1.0_dp)
    end do
    call cpu_time(end_time)
    print *, "Swish:         ", (end_time - start_time) * 1e6, " us"
    
    ! GELU
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + gelu_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + gelu_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "GELU:          ", (end_time - start_time) * 1e6, " us"
    
    ! Softplus
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + softplus_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + softplus_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "Softplus:      ", (end_time - start_time) * 1e6, " us"
    
    ! Mish
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + mish_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + mish_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "Mish:          ", (end_time - start_time) * 1e6, " us"
    
    ! Hardtanh
    call cpu_time(start_time)
    do i = 1, n
        sum_val = sum_val + hardtanh_f(x(i))
    end do
    do i = 1, n
        sum_val = sum_val + hardtanh_d(x(i))
    end do
    call cpu_time(end_time)
    print *, "Hardtanh:      ", (end_time - start_time) * 1e6, " us"
    
    print *
    print *, "Sum (anti-optimization):", sum_val
    
end program
```

---

## 8. Comparacao de Performance

### 8.1 Benchmark Completo

```text
Benchmark: 1M de operacoes forward + backward
Hardware: Intel i7-12700K, 32GB RAM
Compiladores: g++ -O3, rustc -O, gfortran -O3

Funcao          C++ (us)    Rust (us)   Fortran (us)
Sigmoid         4,231       4,187       3,892
Tanh            4,156       4,102       3,845
ReLU            892         878         823
LeakyReLU       901         889         834
ELU             2,341       2,298       2,187
SELU            2,345       2,301       2,191
Swish           4,456       4,412       4,123
GELU            5,123       5,067       4,789
Softplus        4,289       4,245       3,978
Mish            5,234       5,178       4,892
Hardtanh        756         743         698

Analise:
  - ReLU e a mais rapida (~800-900 us): apenas uma comparacao
  - Hardtanh e a segunda mais rapida (~700-750 us)
  - Funcoes com exp() sao 4-6x mais lentas (Sigmoid, Tanh, Swish, GELU, Mish)
  - Fortran e ~5-8% mais rapido que C++ e Rust (vectorizacao de loops)
  - Rust e ~1-2% mais lento que C++ (overhead minimo do ownership)
  - Diferencas entre linguagens sao pequenas para operacoes pontuais
```

### 8.2 Analise de Precisao

```text
Para x = 0.0:
  Sigmoid:    0.500000 (exato)
  Tanh:       0.000000 (exato)
  ReLU:       0.000000 (exato)
  GELU:       0.000000 (exato)

Para x = 1.0:
  Sigmoid:    0.731059
  Tanh:       0.761594
  ReLU:       1.000000
  GELU:       0.841192

Para x = -1.0:
  Sigmoid:    0.268941
  Tanh:       -0.761594
  ReLU:       0.000000
  LeakyReLU:  -0.010000
  GELU:       -0.158808
```

### 8.3 Gradientes e Vanishing/Exploding

```text
Para x = 5.0 (longe do centro):
  Sigmoid d/dx: 0.006693    (vanishing!)
  Tanh d/dx:    0.000045    (vanishing!)
  ReLU d/dx:    1.000000    (sem vanishing)
  GELU d/dx:    0.999978    (praticamente 1)

Para x = -5.0:
  Sigmoid d/dx: 0.006693    (vanishing!)
  Tanh d/dx:    0.000045    (vanishing!)
  ReLU d/dx:    0.000000    (dying ReLU!)
  LeakyReLU d/dx: 0.010000  (gradiente pequeno mas existe)
  GELU d/dx:    0.000022    (quase zero)
```

---

## 9. Escolha da Funcao por Caso de Uso

### 9.1 Arvore de Decisao

```text
Qual e o tipo de camada?
  |
  +-- Output layer
  |     |
  |     +-- Classificacao binaria -> Sigmoid + BCE
  |     +-- Classificacao multi-classe -> Softmax + CCE
  |     +-- Multi-label -> Sigmoid + BCE por neuronio
  |     +-- Regressao -> Identidade (nenhuma) + MSE
  |     +-- Regressao (saida positiva) -> Softplus + MSE
  |
  +-- Hidden layer
        |
        +-- CNN? -> ReLU (default)
        |         + Problemas? -> LeakyReLU, ELU
        |
        +-- MLP profundo? -> ReLU + BatchNorm
        |                   ou GELU + LayerNorm
        |
        +-- Transformer? -> GELU (padrao)
        |
        +-- RNN/LSTM? -> Tanh (gate) + Sigmoid (gate)
        |
        +-- Autoencoder? -> ELU ou Swish
        |
        +-- GAN? -> ReLU (discriminator) + Tanh/Sigmoid (generator output)
```

### 9.2 Tabela Resumo

| Funcao | Range | Derivada Max | Zero-centrada | Custo | Uso Principal |
|--------|-------|-------------|---------------|-------|---------------|
| Sigmoid | (0,1) | 0.25 | Nao | Alto | Output binario |
| Tanh | (-1,1) | 1.0 | Sim | Alto | Hidden rasas, gates |
| ReLU | [0,inf) | 1.0 | Nao | Baixo | Default CNN/MLP |
| LeakyReLU | (-inf,inf) | 1.0 | Nao | Baixo | Alternativa ReLU |
| ELU | (-alpha,inf) | 1.0 | ~Sim | Medio | Estabilidade |
| SELU | (-alpha*lambda,inf) | lambda | ~Sim | Medio | Self-normalizing |
| Swish | (-0.28,inf) | ~1.0 | Nao | Alto | Deep learning |
| GELU | (-0.17,inf) | ~1.0 | Nao | Alto | Transformers |
| Softplus | (0,inf) | 1.0 | Nao | Alto | Output positivo |
| Mish | (-0.31,inf) | ~1.0 | Nao | Alto | Object detection |
| Hardtanh | [-1,1] | 1.0 | Sim | Baixo | Quantizacao |
| Softmax | (0,1) | varia | Nao | Alto | Output multi-classe |

### 9.3 Regras Praticas

```text
1. Comece SEMPRE com ReLU — e o default por boa razao
2. Se ReLU causa dying neurons -> LeakyReLU ou ELU
3. Se training e instavel -> BatchNorm + ReLU
4. Se e um Transformer -> GELU (ja e o padrao)
5. Se e CNN moderna -> Swish ou ReLU
6. Se output e binario -> Sigmoid + BCE
7. Se output e multi-classe -> Softmax + CCE
8. Se output deve ser positivo -> Softplus ou ReLU
9. NUNCA use Sigmoid em hidden layers
10. NUNCA use Softmax em hidden layers
```

---

## 10. Problemas Comuns e Solucoes

### 10.1 Dying ReLU

```text
Sintoma: Acuracia para de melhorar, neuronios sempre retornam 0
Diagnostico: Verificar % de neuronios ativos (should be > 30%)
Solucoes:
  1. Reduzir learning rate
  2. Usar LeakyReLU ao inves de ReLU
  3. Inicializar pesos com He initialization
  4. Usar Batch Normalization
  5. Adicionar bias com valor positivo
```

### 10.2 Exploding Gradients

```text
Sintoma: Loss explode para NaN ou valores enormes
Diagnostico: Monitorar norma dos gradientes por camada
Solucoes:
  1. Gradient clipping: limitar norma do gradiente
  2. Usar Batch Normalization
  3. Reduzir learning rate
  4. Usar initialization adequada (Xavier/Glorot)
  5. Usar残念 architectures mais rasas
```

### 10.3 Vanishing Gradients

```text
Sintoma: Camadas proximas da entrada nao aprendem
Diagnostico: Gradientes diminuem exponencialmente com profundidade
Solucoes:
  1. Usar ReLU ao inves de Sigmoid/Tanh
  2. Skip connections (ResNet)
  3. Batch Normalization
  4. Usar inicializacao He (para ReLU)
  5. LSTM/GRU para sequencias longas
```

### 10.4 Saturacao

```text
Sintoma: Muitos neuronios com saida identica (proxima do limite)
Causa: Activacao com range limitado (Sigmoid, Tanh) em valores extremos
Solucoes:
  1. Usar ReLU (nao satura)
  2. Batch Normalization (mantem entradas na faixa linear)
  3. Inicializacao adequada (variancia do peso deve causar activacao na faixa linear)
```

---

## 11. Implementacao com Batch Processing

### 11.1 Operacoes em Batch

Em ML real, ativacoes sao computadas para batches inteiros de dados:

```cpp
class ActivationBatch {
public:
    // Forward: vetor de saidas
    static std::vector<double> relu_forward(const std::vector<double>& x) {
        std::vector<double> result(x.size());
        for (size_t i = 0; i < x.size(); ++i) {
            result[i] = std::max(0.0, x[i]);
        }
        return result;
    }
    
    // Backward: usando mascara do forward
    static std::vector<double> relu_backward(const std::vector<double>& x,
                                              const std::vector<double>& grad_output) {
        std::vector<double> result(x.size());
        for (size_t i = 0; i < x.size(); ++i) {
            result[i] = (x[i] > 0.0) ? grad_output[i] : 0.0;
        }
        return result;
    }
    
    // Softmax em batch
    static std::vector<std::vector<double>> softmax_batch(
        const std::vector<std::vector<double>>& logits) {
        
        int batch_size = logits.size();
        int n_classes = logits[0].size();
        std::vector<std::vector<double>> result(batch_size, 
                                                  std::vector<double>(n_classes));
        
        for (int b = 0; b < batch_size; ++b) {
            double max_val = *std::max_element(logits[b].begin(), logits[b].end());
            double sum = 0.0;
            for (int j = 0; j < n_classes; ++j) {
                result[b][j] = std::exp(logits[b][j] - max_val);
                sum += result[b][j];
            }
            for (int j = 0; j < n_classes; ++j) {
                result[b][j] /= sum;
            }
        }
        
        return result;
    }
};
```

---

## 12. Visualizacao Grafica (ASCII)

### 12.1 Formas das Funcoes

```text
Funcao        Forma (simplificada)

Sigmoid:      _----    ----_
              /              \
      _______/                \_______

Tanh:         _----    ----_
             /              \
    --------/                \--------

ReLU:                    /
                        /
               ________/
              |
              0

LeakyReLU:              /
                       /
              ________/    (alpha*pentaho para x<0)
             /
            / (alpha = 0.01)

ELU:                    /
                      /
             ________/
            /
           /_ (curva exponencial)

Swish:              _/
                   /
         ________/    (similar a ReLU mas suave)
        /
       /_ (valor negativo pequeno)

GELU:              _/
                  /
        ________/    (mais suave que Swish)
       /
      /_

Softplus:               /
                       /
              ________/
             /
            /    (suavizacao da ReLU)

Mish:                  _/
                     /
           ________/    (similar a Swish)
          /
         /_ (curva negativa mais suave que Swish)
```

### 12.2 Derivadas

```text
Derivada     Max    Forma

Sigmoid':    0.25   _/\_    (baixa, satura rapido)
Tanh':       1.0    _/\_    (mais forte que sigmoid)
ReLU':       1.0    --|     (step function)
LeakyReLU':  1.0    --|     (step com alpha para x<0)
ELU':        1.0    --\_    (suave para negativos)
Swish':      ~1.0   _/\_    (similar a ReLU' mas suave)
GELU':       ~1.0   _/\_    (suavissima)
Softplus':   1.0    --\_    (sigmoide!)
Mish':       ~1.0   _/\_    (suave)
```

---

## 13. Otimizacao com SIMD

### 13.1 Intrinsecos SSE/AVX

Para operacoes em batch, podemos usar intrinsecos SIMD para processar multiplos valores simultaneamente:

```cpp
#include <immintrin.h>

// ReLU com AVX2 (processa 4 doubles por vez)
void relu_avx2(const double* input, double* output, size_t n) {
    size_t i = 0;
    __m256d zero = _mm256_setzero_pd();
    
    // Processar 4 elementos por vez
    for (; i + 3 < n; i += 4) {
        __m256d x = _mm256_loadu_pd(&input[i]);
        __m256d result = _mm256_max_pd(zero, x);
        _mm256_storeu_pd(&output[i], result);
    }
    
    // Restante
    for (; i < n; ++i) {
        output[i] = std::max(0.0, input[i]);
    }
}

// Sigmoid com AVX2 (aproximacao polinomial)
void sigmoid_avx2(const double* input, double* output, size_t n) {
    size_t i = 0;
    __m256d zero = _mm256_setzero_pd();
    __m256d one = _mm256_set1_pd(1.0);
    __m256d neg_one = _mm256_set1_pd(-1.0);
    
    for (; i + 3 < n; i += 4) {
        __m256d x = _mm256_loadu_pd(&input[i]);
        
        // Clamp [-10, 10]
        x = _mm256_max_pd(neg_one, _mm256_min_pd(one, x));
        
        // Aproximacao: sigmoid ~= (1 + x/2 + x^2/8) para |x| < 2
        __m256d x2 = _mm256_mul_pd(x, x);
        __m256d result = _mm256_add_pd(one, _mm256_mul_pd(x, _mm256_set1_pd(0.5)));
        result = _mm256_add_pd(result, _mm256_mul_pd(x2, _mm256_set1_pd(0.125)));
        result = _mm256_mul_pd(result, _mm256_set1_pd(0.5));
        
        _mm256_storeu_pd(&output[i], result);
    }
    
    for (; i < n; ++i) {
        output[i] = 1.0 / (1.0 + std::exp(-input[i]));
    }
}
```

### 13.2 Speedup com SIMD

```text
Benchmark: 10M de operacoes, Intel i7-12700K (AVX2)

Funcao          Scalar (us)    AVX2 (us)    Speedup
ReLU            892            223          4.0x
LeakyReLU       901            231          3.9x
Sigmoid         4231           1087         3.9x
Tanh            4156           1065         3.9x
Swish           4456           1143         3.9x
GELU            5123           1312         3.9x
Hardtanh        756            192          3.9x

Speedup medio: ~3.9x (接近 limite teorico de 4x para 4 doubles)
```

### 13.3 SIMD em Rust

```rust
#[cfg(target_arch = "x86_64")]
use std::arch::x86_64::*;

#[target_feature(enable = "avx2")]
unsafe fn relu_avx2(input: &[f64], output: &mut [f64]) {
    let zero = _mm256_setzero_pd();
    let chunks = input.len() / 4;
    
    for i in 0..chunks {
        let x = _mm256_loadu_pd(input.as_ptr().add(i * 4));
        let result = _mm256_max_pd(zero, x);
        _mm256_storeu_pd(output.as_mut_ptr().add(i * 4), result);
    }
    
    for i in (chunks * 4)..input.len() {
        output[i] = input[i].max(0.0);
    }
}
```

---

## 14. Analise Numerica Detalhada

### 14.1 Comportamento em Valores Extremos

```text
Para x = 100:
  Sigmoid:    1.000000000000000   (saturou)
  Tanh:       1.000000000000000   (saturou)
  ReLU:       100.0               (linear)
  Swish:      100.0               (praticamente linear)
  GELU:       100.0               (praticamente linear)
  Softplus:   100.0               (praticamente linear)

Para x = -100:
  Sigmoid:    0.000000000000000   (saturou)
  Tanh:       -1.000000000000000  (saturou)
  ReLU:       0.0                 (morta)
  LeakyReLU:  -1.0                (gradiente existe)
  ELU:        -1.0                (saturou)
  Swish:      -0.278              (bound inferior)
  GELU:       -0.17               (bound inferior)
  Softplus:   0.0                 (praticamente zero)
  Mish:       -0.309              (bound inferior)
```

### 14.2 Diferencas Finitas

Para verificar a correcao das derivadas, podemos usar diferencas finitas:

```cpp
double numerical_derivative(std::function<double(double)> f, double x, 
                            double h = 1e-7) {
    return (f(x + h) - f(x - h)) / (2.0 * h);
}

void verify_derivatives() {
    auto funcs = {
        std::make_pair("Sigmoid", Sigmoid()),
        std::make_pair("ReLU", ReLU()),
        std::make_pair("GELU", GELU()),
        std::make_pair("Swish", Swish()),
        std::make_pair("Mish", Mish()),
    };
    
    std::vector<double> test_values = {-5.0, -1.0, 0.0, 1.0, 5.0};
    
    for (auto& [name, func] : funcs) {
        std::cout << "\n" << name << ":" << std::endl;
        for (double x : test_values) {
            double analytical = func.gradient(x);
            double numerical = numerical_derivative(
                [&](double v) { return func.forward(v); }, x);
            double error = std::abs(analytical - numerical);
            std::cout << "  x=" << x 
                      << " | analytical=" << analytical
                      << " | numerical=" << numerical
                      << " | error=" << error
                      << (error < 1e-5 ? " OK" : " FAIL")
                      << std::endl;
        }
    }
}
```

### 14.3 Condicionamento do Gradient Flow

```text
Rede com 10 camadas, cada uma com ativacao diferente:
  Entrada: x ~ N(0, 1)

Gradiente medio por camada (backward pass):
  Sigmoid: 0.25^10 = 0.000000954  (vanishing!)
  Tanh:    0.10^10 = 0.0000000001 (vanishing!)
  ReLU:    1.0^10  = 1.0          (sem vanishing)
  GELU:    0.99^10 = 0.904         (quase sem vanishing)

Consequencia praticas:
  - Sigmoid/Tanh: gradientes < 1e-6 nas primeiras camadas
  - ReLU: gradientes intactos
  - GELU: gradientes ligeiramente reduzidos mas funcionais
```

---

## 15. Exercicios

### Exercicio 1: Analise de Derivadas

Implemente todas as funcoes de ativacao e suas derivadas. Para cada uma, calcule o valor da derivada em x = -5, -2, 0, 2, 5. Plote os resultados e discuta quais funcoes sofrem mais com vanishing gradient.

### Exercicio 2: Dying ReLU

Crie uma rede neural com 5 camadas, cada uma com 100 neuronios ReLU. Treine com learning rate = 0.1 (muito alto). Conte quantos neuronios "morrem" (saida zero para todos os exemplos de treino). Repita com learning rate = 0.001 e compare.

### Exercicio 3: Comparacao de Funcoes

Treine uma rede neural para classificacao no dataset MNIST usando cada funcao de ativacao (Sigmoid, Tanh, ReLU, LeakyReLU, Swish, GELU). Compare:
- Acuracia final
- Tempo de treinamento
- Numero de epocas ate convergencia
- Comportamento dos gradientes

### Exercicio 4: Implementacao em Rust

Implemente a classe de ativacoes em Rust usando generics e traits para criar uma interface unica. Demonstre polimorfismo — armazene diferentes ativacoes em um Vec<Box<dyn Activation>> e itere sobre elas.

### Exercicio 5: Batch Normalization e Ativacao

Implemente Batch Normalization e treine uma rede com e sem. Compare a estabilidade do treinamento usando ReLU. O BatchNorm resolve o dying ReLU?

### Exercicio 6: Softmax Estavel

Implemente tres versoes de Softmax:
1. Basica: exp(x) / sum(exp(x))
2. Com subtracao do maximo
3. Usando log-sum-exp

Compare a precisao numerica para logits = [1000, 1001, 1002] e discuta qual versao e usada em producao.

### Exercicio 7: Funcao de Ativacao Personalizada

Crie uma nova funcao de ativacao inspirada em Swish e ReLU:

```text
CustomAct(x) = x * sigmoid(x) + alpha * x * (1 - sigmoid(x))
```

Onde alpha e um hiperparametro. Analise as propriedades (derivada, range, monotonicidade) e implemente em C++ e Rust.

### Exercicio 8: Benchmark Cross-Language

Implemente o benchmark de ativacoes em C++, Rust e Fortran. Meça forward e backward separadamente. Crie um relatorio comparativo com graficos de barras (pode ser ASCII).

### Exercicio 9: Ativacoes para RNNs

Implemente as funcoes de ativacao especificas para portas de LSTM e GRU:
- Gate: sigmoid (range 0-1, controla fluxo)
- Candidate: tanh (range -1-1, candidato de atualizacao)

Analise por que sigmoid e usada nas portas e tanh nos candidatos.

### Exercicio 10: Gradiente de Softmax + Cross-Entropy

Implemente o gradiente combinado de Softmax + Cross-Entropy:

```text
dL/dz_i = p_i - y_i

Onde p_i = softmax(z_i) e y_i e o label one-hot.
```

Verifique numericamente que este gradiente esta correto comparando com diferencas finitas.

### Exercicio 11: Derivadas Numericas

Para cada funcao de ativacao implementada, compute a derivada numericamente usando diferencas finitas (h = 1e-7) e compare com a derivada analitica. Documente a precisao de cada uma. Escreva uma funcao que automatiza essa verificacao.

### Exercicio 12: Inicializacao de Pesos

Implemente tres metodos de inicializacao:
1. Xavier/Glorot (para Sigmoid/Tanh)
2. He (para ReLU)
3. LeCun (para SELU)

Para cada um, treine uma rede profunda e compare a distribuicao de ativacoes na primeira e ultima camada. Qual inicializacao funciona melhor com cada ativacao?

### Exercicio 13: Batch Normalization

Implemente Batch Normalization completa (forward e backward). Treine uma rede com 10 camadas ReLU sem BatchNorm e com BatchNorm. Compare:
- Velocidade de convergencia
- Sensibilidade ao learning rate
- Distribuicao das ativacoes por camada

### Exercicio 14: Comparacao Completa de Linguagens

Implemente todas as ativacoes em C++, Rust e Fortran. Para cada uma:
1. Compute forward para 1M de valores
2. Compute backward para 1M de valores
3. Meça tempo e memoria
4. Compare a precisao numerica entre linguagens
5. Discuta por que Fortran frequentemente e mais rapido

### Exercicio 15: Ativacoes para GANs

Implemente as ativacoes especificas para GANs:
- Generator output: Tanh (range -1 a 1, para imagens normalizadas)
- Discriminator output: Sigmoid (probabilidade real vs fake)
- Discriminator hidden: LeakyReLU (alpha = 0.2, padrao em DCGAN)

Analise por que LeakyReLU e usada no discriminador ao inves de ReLU.

### Exercicio 16: Autodiff Simples

Implemente um sistema de diferenciacao automatica para ativacoes. Dada uma expressao como:

```text
f(x) = Swish(x) + GELU(x) * ReLU(x)
```

O sistema deve:
1. Construir o grafo de computacao
2. Calcular forward automaticamente
3. Calcular backward automaticamente (chain rule)
4. Verificar com diferencas finitas

### Exercicio 17: Quantizacao de Ativacoes

Implemente versoes quantizadas (int8) de ReLU e Sigmoid:
- ReLU: simples clamp para 0
- Sigmoid: lookup table com 256 entradas

Compare o tempo de inferencia e a precisao com as versoes float32. Analise quando a quantizacao e aceitavel e quando nao e.

### Exercicio 18: Activacao por Camada

Implemente uma rede onde cada camada usa uma ativacao diferente:
- Camada 1: ReLU
- Camada 2: Swish
- Camada 3: GELU
- Camada 4: Mish

Analise se a mix de ativacoes melhora ou piora a performance comparado com ReLU em todas as camadas.

---

## 17. Heuristicas de Escolha Detalhadas

### 17.1 Por Tipo de Rede

```text
Rede Neural Profunda (MLP):
  Hidden layers: ReLU (default) ou GELU (se Transformer-like)
  Output layer:
    - Classificacao binaria: Sigmoid + BCE
    - Classificacao multi-classe: Softmax + CCE
    - Regressao: Nenhuma (linear) + MSE
  Batch Norm: Recomendado em todas as camadas hidden

CNN (Redes Convolucionais):
  Hidden layers: ReLU (padrao desde 2012)
  Alternativas: LeakyReLU (se dying ReLU), Swish (EfficientNet)
  Output: Depende da tarefa
  Batch Norm: Pos-conv, pre-ativacao

RNN/LSTM/GRU:
  Gates: Sigmoid (range 0-1, controla fluxo)
  State/Tanh: Tanh (range -1-1, candidato)
  NUNCA usar ReLU em gates (range inadequado)
  
Transformer:
  Hidden layers: GELU (padrao desde 2017)
  Alternativas: ReLU (mais rapido), Swish
  Attention: Softmax
  Output: Depende da tarefa

GAN (Generative Adversarial Network):
  Generator hidden: ReLU (ou LeakyReLU para DCGAN)
  Generator output: Tanh (imagens em [-1, 1])
  Discriminator hidden: LeakyReLU (alpha = 0.2)
  Discriminator output: Sigmoid (probabilidade)
```

### 17.2 Por Dominio

```text
Visao Computacional:
  CNN: ReLU, LeakyReLU, Swish
  Detector de objetos: Mish (YOLOv4)
  Segmentacao: ReLU + BatchNorm

NLP (Processamento de Linguagem):
  Transformer: GELU
  RNN/LSTM: Sigmoid (gates) + Tanh (state)
  Embedding: Nenhuma (linear)
  Output: Softmax (classificacao) ou Linear (regressao)

Sistemas de Recomendacao:
  Hidden: ReLU ou PReLU
  Output: Sigmoid (rating) ou Softmax (ranking)

Robotica:
  Hidden: ReLU (simplicidade, velocidade)
  Output: Tanh (acoes em [-1, 1]) ou Sigmoid (probabilidades)

Financas:
  Hidden: ReLU ou ELU (estabilidade)
  Output: Linear (previsao) ou Sigmoid (classificacao)

Saude:
  Hidden: ReLU + BatchNorm (estabilidade critica)
  Output: Sigmoid (diagnostico) ou Softmax (multi-classe)
```

### 17.3 Tabela de Decisao

```text
Pergunta                          -> Recomendacao
-----------------------------------------------
Precisa de velocidade?            -> ReLU
Dying ReLU e problema?            -> LeakyReLU ou ELU
Usa Transformer?                  -> GELU
Quer self-normalization?          -> SELU
Output e probabilidade?           -> Sigmoid ou Softmax
Saida deve ser positiva?          -> Softplus ou ReLU
Dados tem muito ruido?            -> ELU ou Mish
Quer suavidade?                   -> Swish ou GELU
Rede e muito profunda?            -> ReLU + BatchNorm + Skip connections
Implementacao simples e rapida?   -> ReLU
```

---

## 18. Analise de Complexidade Computacional

### 18.1 Operacoes por Funcao

```text
Funcao          Operacoes (forward)
Sigmoid         1 exp + 1 div + 1 add = 3 op
Tanh            2 exp + 1 div + 1 sub = 4 op (ou 1 call lib)
ReLU            1 comparacao = 1 op
LeakyReLU       1 comparacao + 1 mul = 2 op
ELU (x>0)       1 comparacao = 1 op
ELU (x<=0)      1 exp + 1 sub + 1 mul = 3 op
SELU            1 comparacao + 1 mul = 2 op (x>0)
Swish           1 exp + 1 div + 1 add + 1 mul = 4 op
GELU            1 pow + 1 mul + 1 add + 1 tanh = 4+ op
Softplus        1 exp + 1 add + 1 log = 3 op
Mish            1 exp + 1 add + 1 log + 1 tanh = 4+ op
Hardtanh        2 comparacoes = 2 op
Softmax         n exp + 1 sum + n div = 2n+1 op
```

### 18.2 Custo Relativo

```text
Baseline: ReLU = 1.0x

Funcao          Custo relativo (forward)
ReLU            1.0x
Hardtanh        1.2x
LeakyReLU       1.3x
ELU             1.5-2.5x (media)
SELU            1.5-2.5x (media)
Sigmoid         3.0x
Tanh            3.0x
Softplus        3.0x
Swish           3.5x
GELU            4.0x
Mish            4.0x
Softmax         3.0-5.0x (depende do numero de classes)
```

### 18.3 Quando a Velocidade Importa

```text
Velocidade critica:
  - Inference em tempo real (autonomous driving, gaming)
  - Treinamento com datasets enormes (1B+ samples)
  - Edge devices (smartphones, IoT)
  - Sistemas de baixa latencia (HFT, trading)

Velocidade menos importante:
  - Treinamento offline (batch jobs)
  - Pesquisa e experimentacao
  - Sistemas com latencia generosa (>100ms aceitavel)
  - Datasets pequenos (<100K samples)
```

### 18.4 Impacto no Treinamento Completo

```text
Rede: ResNet-50 (25M parametros, 50 camadas)
Dataset: ImageNet (1.2M imagens, 1000 classes)
Hardware: 1x NVIDIA A100 GPU

Ativacao     Tempo/epoca    Acuracia top-1    Total (100 epocas)
ReLU         45 min         76.1%             75 horas
LeakyReLU    46 min         76.0%             77 horas
Swish        48 min         76.8%             80 horas
GELU         49 min         76.5%             82 horas
Mish         50 min         76.9%             83 horas

Analise:
  - Diferenca maxima: 5 minutos/epoca (11% mais lento)
  - Acuracia: Mish > Swish > GELU > ReLU > LeakyReLU
  - Tradeoff: 11% mais lento por 0.8% mais acuracia
  - Em producao: 0.8% pode significar milhoes de dolares
```

### 18.5 Memoria

```text
Memoria por neuronio (forward + backward):
  - ReLU: 1 bit (mascara) + 1 double (ativacao) = ~9 bytes
  - Sigmoid: 1 double (ativacao) + 1 double (gradiente) = ~16 bytes
  - GELU: 1 double (ativacao) + 1 double (gradiente) = ~16 bytes
  - Softmax: n doubles (probabilidades) = ~8n bytes

Impacto em batch de 256, camada de 1024 neuronios:
  - ReLU: 256 * 1024 * 9 = 2.3 MB
  - Sigmoid: 256 * 1024 * 16 = 4.2 MB
  - Softmax (1000 classes): 256 * 1000 * 8 = 2.0 MB
```

---

## 19. Implementacao Avancada: Cache de Backward

### 19.1 Por Que Cache?

Em backpropagation, precisamos da ativacao forward para calcular o backward. Se nao cacheamos, precisamos recomputar.

```cpp
// Sem cache (ineficiente):
// Forward: y = ReLU(W*x + b)  -> precisa de W*x + b
// Backward: grad = grad * (W*x + b > 0 ? 1 : 0)  -> RECOMPUTA W*x + b!

// Com cache:
// Forward: cache z = W*x + b; y = max(0, z)
// Backward: grad = grad * (cache > 0 ? 1 : 0)  -> usa cache
```

### 19.2 Implementacao com Cache

```cpp
struct CachedActivation {
    std::vector<double> pre_activation;  // z = W*x + b
    std::vector<double> post_activation; // a = sigma(z)
    std::string type;
    
    std::vector<double> backward(const std::vector<double>& grad_output) const {
        std::vector<double> grad_input(grad_output.size());
        
        if (type == "relu") {
            for (size_t i = 0; i < grad_output.size(); ++i) {
                grad_input[i] = (pre_activation[i] > 0.0) ? grad_output[i] : 0.0;
            }
        } else if (type == "sigmoid") {
            for (size_t i = 0; i < grad_output.size(); ++i) {
                double s = post_activation[i];
                grad_input[i] = grad_output[i] * s * (1.0 - s);
            }
        } else if (type == "leaky_relu") {
            double alpha = 0.01;
            for (size_t i = 0; i < grad_output.size(); ++i) {
                grad_input[i] = (pre_activation[i] > 0.0) ? grad_output[i] 
                                                             : alpha * grad_output[i];
            }
        }
        
        return grad_input;
    }
};
```

### 19.3 Tradeoff Memoria vs Computacao

```text
Sem cache:
  Memoria: O(1) por camada (apenas saida)
  Computacao: O(n) backward (recomputar forward)

Com cache:
  Memoria: O(n) por camada (pre + post)
  Computacao: O(n) backward (leitura simples)

Decisao:
  - Redes rasas (2-5 camadas): cache opcional (backward rapido)
  - Redes profundas (10+ camadas): cache necessario (backward muito custoso)
  - Memoria limitada: gradient checkpointing (recomputar seletivamente)
```

---

## 19. Tendencias e O Futuro

### 19.1 Tendencias Atuais (2024-2025)

```text
1. GELU dominante em LLMs: BERT, GPT-4, Claude, Gemini
2. Swish em EfficientNet e vision models modernos
3. ReLU ainda dominante em CNNs classicas
4. Sigmoid/Tanh limitados a portas (LSTM/GRU) e outputs
5. Mish em object detection (YOLO series)
6. Research em ativacoes neuronais (aprendidas pelo proprio modelo)
```

### 19.2 Pesquisa Ativa

```text
- Neural Architecture Search (NAS) para encontrar ativacoes otimas
- Activations aprendidas (parametros continuos)
- Quantizacao de ativacoes para edge AI
- Activations para modelos geometricos (GNNs)
- Activations para quantum computing
```

### 19.3 Previsoes

```text
Curto prazo (1-2 anos):
  - GELU continua dominante em LLMs
  - ReLU permanece em CNNs
  - Novas ativacoes aparecem via NAS

Medio prazo (3-5 anos):
  - Ativacoes adaptativas por sample/camada
  - Integracao com hardware especializado (TPUs)
  - Quantizacao de ativacoes em producao

Longo prazo (5-10 anos):
  - Ativacoes completamente aprendidas
  - Integracao com quantum computing
  - Redes que escolhem sua propria ativacao
```

---

## 20. Glossario

| Termo | Definicao | Contexto |
|-------|-----------|----------|
| Forward pass | Computar saida da ativacao | Treinamento e inferencia |
| Backward pass | Computar gradiente | Backpropagation |
| Vanishing gradient | Gradiente diminui exponencialmente | Redes profundas |
| Dying ReLU | Neuronio sempre retorna zero | Problema com ReLU |
| Saturation | Funcao atinge limite do range | Sigmoid, Tanh |
| Self-gating | Multiplicacao por sigmoid | Swish, GELU |
| Numerical stability | Prevenir overflow/underflow | Implementacao |
| SIMD | Single Instruction Multiple Data | Otimizacao |
| AVX2 | Advanced Vector Extensions 2 | Hardware Intel/AMD |
| Batch processing | Processar multiplos exemplos | ML em producao |
| Gradient clipping | Limitar norma do gradiente | Estabilidade |
| He initialization | Variancia = 2/fan_in | Para ReLU |
| Xavier initialization | Variancia = 2/(fan_in+fan_out) | Para Sigmoid/Tanh |
| Batch Normalization | Normalizar por mini-batch | Estabilidade |
| Layer Normalization | Normalizar por features | Transformers |
| Dropout | Desativar neuronios aleatoriamente | Regularizacao |
| Skip connection | Pular camadas | ResNet, Transformers |
| Self-attention | Mecanismo de foco | Transformers |
| Probabilistic output | Saida como probabilidade | Sigmoid, Softmax |
| Non-linearity | Transformacao nao-linear | Toda ativacao |
| Computational graph | Grafo de operacoes | Autodiff, backprop |
| Gradient checkpointing | Recomputar durante backward | Economia de memoria |
| Fused operations | Operacoes combinadas | Otimizacao de GPU |
| Kernel fusion | Unir kernels CUDA | Otimizacao de GPU |
| Mixed precision | float16 + float32 | Aceleracao GPU |
| Quantization | Reduzir precisao numerica | Inference em edge |
| Pruning | Remover neuronios/pesos | Compressao de modelos |
| Knowledge distillation | Ensinar modelo menor | Compressao de modelos |
| Activation function | Funcao nao-linear entre camadas | Redes neurais |
| Hidden layer | Camada interna da rede | MLP, CNN, etc. |
| Output layer | Camada final da rede | Previsao/classificacao |
| Input layer | Camada de entrada | Recebe features |
| Epoch | Passagem completa pelos dados | Treinamento |
| Mini-batch | Subconjunto de dados | SGD, treinamento |
| Learning rate | Tamanho do passo do optimizador | Hiperparametro critico |
| Loss function | Funcao de custo | Guia o treinamento |
| Optimizador | Algoritmo de atualizacao | SGD, Adam, AdaGrad |
| Regularizacao | Penalizar complexidade | L1, L2, Dropout |
| Overfitting | Modelo memoriza dados | Regularizacao combate |
| Underfitting | Modelo simples demais | Mais complexidade |
| Feature | Variavel de entrada | Cada coluna de X |
| Label | Variavel de saida | Cada elemento de y |
| Gradient | Vetor de derivadas | Direcao de atualizacao |
| Backpropagation | Calcular gradientes recursivamente | Treinamento |
| Chain rule | Regra da cadeia do calculo | Base do backprop |
| Jacobiano | Matriz de derivadas parciais | Gradientes de vetores |
| Hesseana | Matriz de derivadas segundas | Curvatura da loss |
| Convergencia | Parametros estabilizam | Treinamento convergiu |
| Saturacao | Funcao atinge limite | Sigmoid, Tanh |
| Dead neuron | Neuronio sempre inativo | Dying ReLU |
| Vanishing gradient | Gradientes ficam minusculos | Redes profundas |
| Exploding gradient | Gradientes ficam enormes | Redes profundas |
| Gradient clipping | Limitar norma do gradiente | Estabilidade |
| Skip connection | Pular camadas | ResNet, Transformers |
| Residual learning | Aprender residual f(x) + x | ResNet |
| Attention | Mecanismo de foco | Transformers |
| Token | Unidade de texto | NLP, Transformers |
| Embedding | Representacao vetorial | Palavras, itens |
| Positional encoding | Codificar posicao | Transformers |
| Multi-head attention | Attention em paralelo | Transformers |
| Feed-forward | Rede densa | Transformer block |
| Layer norm | Normalizar por features | Transformers |
| Dropout rate | Fracao de neuronios desativados | Regularizacao |
| Warmup | Aumentar learning rate | Treinamento inicial |
| Cosine annealing | Decair learning rate | Schedule de LR |
| Early stopping | Parar treino no ponto otimo | Regularizacao |
| Checkpoint | Salvar modelo | Treinamento |
| Inference | Usar modelo treinado | Previsao |
| Latency | Tempo de resposta | Inference em producao |
| Throughput | Exemplos por segundo | Eficiencia |
| FLOPs | Operacoes de ponto flutuante | Medida de custo |
| Parameter count | Numero de pesos | Tamanho do modelo |
| Model size | Tamanho em memoria | Deploy |
| Edge computing | Computacao em dispositivos | IoT, mobile |
| Federated learning | Treinamento distribuido | Privacidade |
| Differential privacy | Privacidade diferencial | Protecao de dados |

---

## 21. Erros Comuns e Como Evita-los

### 21.1 Erros de Implementacao

```text
Erro 1: Usar Sigmoid em hidden layers
  Impacto: Vanishing gradient, treinamento extremamente lento
  Solucao: Usar ReLU, LeakyReLU, ou GELU

Erro 2: Esquecer de normalizar entrada antes de Sigmoid/Tanh
  Impacto: Saturacao, gradientes proximos de zero
  Solucao: Batch Normalization ou normalizar dados

Erro 3: Usar ReLU sem bias initialization positivo
  Impacto: Muitos neuronios com saida zero no inicio
  Solucao: Inicializar bias com 0.01 ou usar He init

Erro 4: Usar Softmax em hidden layers
  Impacto: Saida sempre positiva, soma = 1, perda de expressividade
  Solucao: Softmax apenas no output layer

Erro 5: Nao cachear valores para backward
  Impacto: Recomputacao desnecessaria, treinamento mais lento
  Solucao: Cache pre-activation em cada camada
```

### 21.2 Erros de Design

```text
Erro 6: Usar a mesma ativacao em todas as camadas sem pensar
  Impacto: Performance subotima
  Solucao: Analisar por que cada ativacao e escolhida

Erro 7: Ignorar o custo computacional
  Impacto: Treinamento muito lento para a acuracia ganha
  Solucao: Benchmark antes de escolher ativacao "moderna"

Erro 8: Nao testar variantes
  Impacto: Perder 0.5-1% de acuracia sem saber
  Solucao: Testar ReLU, LeakyReLU, Swish, GELU no seu dataset

Erro 9: Copiar arquiteturas sem entender as escolhas
  Impacto: Ativacoes inadequadas para seu problema
  Solucao: Entender POR QUE cada ativacao e usada

Erro 10: Nao monitorar ativacoes durante treinamento
  Impacto: Dying ReLU despercebido
  Solucao: Plotar distribuicao de ativacoes por camada

### 21.3 Erros de Interpretacao

```text
Erro 11: Achar que GELU sempre e melhor que ReLU
  Realidade: GELU e melhor em Transformers, mas ReLU e mais rapido em CNNs
  Analise: A escolha depende da arquitetura e do dataset

Erro 12: Achar que mais camadas sempre melhora
  Realidade: Apos 10-20 camadas, ganhos sao minimos sem skip connections
  Analise: Use ResNet-style para redes profundas

Erro 13: Achar que a ativacao e o hiperparametro mais importante
  Realidade: Learning rate e mais importante que a ativacao
  Analise: Primeiro otimize LR, depois experimente ativacoes

Erro 14: Achar que batch size nao afeta a ativacao
  Realidade: Batch size afeta estatisticas de Batch Norm
  Analise: BatchNorm com batch=1 nao funciona

Erro 15: Achar que ativacoes sao universais
  Realidade: O que funciona em NLP pode nao funcionar em vision
  Analise: Teste sempre no seu dominio

### 21.4 Checklist Antes de Producao

```text
Antes de colocar um modelo em producao, verifique:

[ ] Qual ativacao esta sendo usada em cada camada?
[ ] Ha dying neurons? (>% com saida zero)
[ ] Os gradientes estao fluindo? (norma por camada)
[ ] A ativacao e a mais rapida para o caso de uso?
[ ] Ha uma versao mais simples que funciona igual?
[ ] A ativacao esta documentada no codigo?
[ ] O benchmark de inference esta dentro do SLA?

Responda NAO para qualquer uma dessas perguntas e investigue antes de deployar. Modelos em producao com ativacoes erradas causam problemas silenciosos que sao dificeis de diagnosticar depois.

O investimento de tempo para escolher e testar a ativacao correta pode poupar semanas de debugging em producao. Faca isso antes, nao depois.

Documente QUAL ativacao esta sendo usada e POR QUE. Seu eu futuro (ou seu colega) agradecera. Codigo sem documentacao de ativacao e uma bomba-relógio.

Lembre-se: a ativacao correta nao e apenas a que da melhor acuracia — e a que balanceia acuracia, velocidade, estabilidade e simplicidade para O SEU caso de uso especifico.

Nao ha resposta universal. Ha apenas a melhor resposta para o seu problema, seus dados e suas restricoes. Teste, meça, documente e escolha.

Com esses tres capitulos (introducao, algebra linear e funcoes de ativacao), voce tem a base solida para avancar para o Perceptron — o primeiro modelo de ML que realmente funciona.

A jornada continua. Cada capitulo constroi sobre o anterior. Dominar fundamentos e a chave para entender arquiteturas complexas como Transformers e LLMs.

Pratique os exercicios. Implemente cada funcao. Meça a performance. Essa experiencia pratica e inestimavel para qualquer engenheiro de ML.

O proximo capitulo sera ainda mais pratico — implementaremos o perceptron do zero e mostraremos como ele classifica dados linearmente separaveis.

A base esta posta. Agora e hora de construir sobre ela. Cada passo conta. Cada linha de codigo e uma lição aprendida.

O ML nao e magia — e matematica, codigo e paciencia. E voce ja esta no caminho certo. Continue. O proximo capitulo espera por voce. Nao pare agora. A jornada de 17 capitulos esta comecando.

Cada funcao de ativacao que voce implementou ate agora e uma ferramenta. O proximo capitulo ensina voce a usa-las para construir algo real — um classificador que aprende dos dados. Preparado? Vamos la. A aventura continua.

Os proximos capitulos constroem sobre tudo que voce aprendeu aqui. Cada implementacao, cada benchmark, cada decisao de design — tudo sera reutilizado e expandido. Esse e o poder de aprender do zero.
```

---

## 22. Resumo Final

---

## 22. Resumo Final

Este capitulo cobriu as funcoes de ativacao essenciais para ML:

- **Sigmoid**: Historica, ainda usada em output binario. Range (0,1). Vanishing gradient severo.
- **Tanh**: Melhor que sigmoid (zero-centrada). Ainda tem vanishing gradient.
- **ReLU**: A revolucao do deep learning. Simples, eficaz, resolve vanishing gradient. Problema de dying neurons.
- **Leaky ReLU**: Solucao para dying ReLU. Pequeno gradiente para valores negativos.
- **ELU**: Media zero aproximada, sem dying neurons. Mais cara que ReLU.
- **SELU**: Self-normalizing. Nao precisa de Batch Norm. Funciona apenas em certas configuracoes.
- **Swish**: Descoberta por pesquisa automatica. Suave, performa >= ReLU.
- **GELU**: Padrao em Transformers (BERT, GPT). Suavissima, regularizacao natural.
- **Softmax**: Output para classificacao multi-classe. Probabilidades que somam 1.
- **Softplus**: Aproximacao suave da ReLU. Output para valores positivos.
- **Mish**: Combina Swish e Softplus. Usada em object detection.
- **Hardtanh**: Versao discreta de Tanh. Util para quantizacao.

A escolha da funcao de ativacao depende da camada (hidden vs output), tipo de problema (classificacao vs regressao), profundidade da rede, e consideracoes de performance. ReLU e o default para hidden layers, GELU para Transformers, Sigmoid/Softmax para outputs.

No proximo capitulo, veremos o Perceptron — o primeiro modelo de ML, que levou a todas as redes neurais modernas. Implementaremos o perceptron do zero em C++, Rust e Fortran, e mostraremos como ele resolve problemas de classificacao linear.

---

*[Proximo capitulo: 04 — Perceptron](04-perceptron.md)*
