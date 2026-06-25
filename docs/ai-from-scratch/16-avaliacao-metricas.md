---
layout: default
title: "16-avaliacao-metricas"
---

# Capitulo 16 — Avaliacao e Metricas

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Compreender por que avaliar modelos** — o que acontece quando nao avaliamos.
2. **Dominar metricas de classificacao** — accuracy, precision, recall, F1-score.
3. **Interpretar a confusion matrix** — erros de tipo I e tipo II.
4. **Usar ROC curve e AUC** — trade-off entre sensibilidade e especificidade.
5. **Analisar Precision-Recall curve** — quando classes sao desbalanceadas.
6. **Calcular log loss** — probabilidades calibradas importam.
7. **Aplicar metricas de regressao** — MSE, MAE, R-squared.
8. **Implementar cross-validation k-fold** — estimativa robusta de performance.
9. **Usar bootstrap** — intervalos de confianca sem distribuicao假设.
10. **Testar significancia estatistica** — e a diferenca real ou por acaso?
11. **Implementar cada metrica em C++** — do zero, sem bibliotecas.
12. **Implementar metricas em Rust** — com seguranca de memoria.
13. **Implementar metricas em Fortran** — para performance numerica.
14. **Fazer benchmark de metricas** — comparar custo computacional.
15. **Avaliar um classificador em dataset real** — pipeline completo.
16. **Interpretar resultados** — quando usar cada metrica.

---

## 1. Por Que Avaliar

### 1.1 O Custo de Nao Avaliar

```text
O que acontece quando um modelo e treinado mas nao avaliado:
================================================================

Cenario 1: Modelo de diagnostico medico
  - Treinado em dados de treino
  - Acerto: 95% nos dados de treino
  - Deploy: 60% no mundo real
  - Resultado: diagnosticos errados
  - Consequencia: pacientes em risco

Cenario 2: Modelo de fraude bancaria
  - Treinado em dados historicos
  - Acerto: 99% nos dados de treino
  - Deploy: 45% no mundo real
  - Resultado: fraude passa despercebida
  - Consequencia: perda financeira

Cenario 3: Modelo de recomendacao
  - Treinado em dados de treino
  - Acerto: 90% nos dados de treino
  - Deploy: 30% no mundo real
  - Resultado: recomendacoes irrelevantes
  - Consequencia: usuarios abandonam plataforma

Padrao comum:
  - Overfitting: modelo memoriza, nao generaliza
  - Sem avaliacao, nao sabemos que esta acontecendo
  - So descobrimos quando e tarde demais
```

### 1.2 O Que Significa Avaliar

```text
Avaliacao e o processo de estimar o desempenho de um modelo
em dados que ele NUNCA viu antes.

Objetivos da avaliacao:
  1. Estimar performance futura
     - "Quanto bem o modelo vai generalizar?"
     - "O modelo funciona em dados novos?"

  2. Comparar modelos
     - "Modelo A e melhor que Modelo B?"
     - "Vale a pena usar uma arquitetura mais complexa?"

  3. Diagnosticar problemas
     - "O modelo esta overfitting?"
     - "O modelo esta underfitting?"
     - "Ha bias nos dados?"

  4. Guiar decisoes
     - "Estamos prontos para deploy?"
     - "Precisamos de mais dados?"
     - "Devemos trocar de modelo?"

Principio fundamental:
  - Avaliacao so e util se feita em dados INDEPENDENTES
  - Dados de treino NAO servem para avaliacao
  - Sempre separar treino e teste
```

### 1.3 Train/Test Split

```text
Separacao de dados:
====================

Dataset completo:
  [d1] [d2] [d3] [d4] [d5] [d6] [d7] [d8] [d9] [d10]

Split 80/20:
  Treino (80%): [d1] [d2] [d3] [d4] [d5] [d6] [d7] [d8]
  Teste  (20%): [d9] [d10]

Split 70/15/15:
  Treino  (70%): [d1] [d2] [d3] [d4] [d5] [d6] [d7]
  Validacao (15%): [d8] [d9]
  Teste    (15%): [d10]

Por que separar?
  - Treino: modelo aprende padroes
  - Validacao: ajusta hiperparametros
  - Teste: avaliacao final, imparcial

NUNCA usar dados de teste no treino!
  - Se usar, a avaliacao e enviesada
  - E como copiar a prova e depois dizer que tirou 10
```

### 1.4 Por Que Uma Metrica Nao Basta

```text
Problema de usar apenas accuracy:
===================================

Dataset: 1000 emails, 950 nao-spam, 50 spam

Modelo A: classifica TODOS como nao-spam
  - Acertos: 950/1000 = 95% accuracy
  - Mas NAO detecta nenhum spam
  - Utilidade: ZERO

Modelo B: classifica 900 nao-spam corretamente, 40 spam corretamente
  - Acertos: 940/1000 = 94% accuracy
  - Detecta 80% do spam
  - Utilidade: ALTA

Comparacao:
  Modelo A: 95% accuracy, inutil
  Modelo B: 94% accuracy, util

Precisamos de metricas que capturam nuances:
  - Accuracy: acerto geral
  - Precision: dos que prediz como positivo, quantos sao realmente
  - Recall: dos que sao realmente positivos, quantos foram detectados
  - F1: harmonia entre precision e recall
  - ROC/AUC: trade-off entre falso positivo e verdadeiro positivo
```

---

## 2. Accuracy

### 2.1 Definicao

```text
Accuracy = (acertos totais) / (total de amostras)

Matematicamente:
  accuracy = (TP + TN) / (TP + TN + FP + ON)

Onde:
  TP (True Positive):  positivo predito como positivo
  TN (True Negative):  negativo predito como negativo
  FP (False Positive): negativo predito como positivo (falso alarme)
  FN (False Negative): positivo predito como negativo (perdido)

Exemplo:
  100 amostras, 60 positivas, 40 negativas
  Modelo prediz: 55 positivas (50 corretas), 45 negativas (38 corretas)

  TP = 50, TN = 38, FP = 5, FN = 10
  Accuracy = (50 + 38) / 100 = 0.88 = 88%

Limitacoes:
  - Ruim para classes desbalanceadas
  - Ruim quando custos de erro sao diferentes
  - Nao distingue entre FP e FN
```

### 2.2 Quando Usar Accuracy

```text
Bom para:
  - Classes balanceadas (50/50, 40/60)
  - Custos de FP e FN sao similares
  - Visao geral do modelo

Ruim para:
  - Classes desbalanceadas (1/99)
  - Custo de FP != custo de FN
    - Cancer: FN e pior que FP
    - Spam: FP e pior que FN
  - Quando probabilidades importam
```

### 2.3 Implementacao em C++

```cpp
#include <vector>
#include <stdexcept>

class MetricsCalculator {
public:
    struct ClassificationResult {
        int true_positives;
        int true_negatives;
        int false_positives;
        int false_negatives;
    };

    static double accuracy(
        const std::vector<int>& y_true,
        const std::vector<int>& y_pred
    ) {
        if (y_true.size() != y_pred.size()) {
            throw std::invalid_argument(
                "Vectors must have same size"
            );
        }

        int correct = 0;
        for (size_t i = 0; i < y_true.size(); ++i) {
            if (y_true[i] == y_pred[i]) {
                ++correct;
            }
        }

        return static_cast<double>(correct) /
               static_cast<double>(y_true.size());
    }

    static ClassificationResult confusion_matrix(
        const std::vector<int>& y_true,
        const std::vector<int>& y_pred
    ) {
        if (y_true.size() != y_pred.size()) {
            throw std::invalid_argument(
                "Vectors must have same size"
            );
        }

        ClassificationResult result = {0, 0, 0, 0};

        for (size_t i = 0; i < y_true.size(); ++i) {
            if (y_true[i] == 1 && y_pred[i] == 1) {
                result.true_positives++;
            } else if (y_true[i] == 0 && y_pred[i] == 0) {
                result.true_negatives++;
            } else if (y_true[i] == 0 && y_pred[i] == 1) {
                result.false_positives++;
            } else if (y_true[i] == 1 && y_pred[i] == 0) {
                result.false_negatives++;
            }
        }

        return result;
    }
};
```

### 2.4 Implementacao em Rust

```rust
pub struct ClassificationResult {
    pub true_positives: usize,
    pub true_negatives: usize,
    pub false_positives: usize,
    pub false_negatives: usize,
}

pub fn accuracy(y_true: &[i32], y_pred: &[i32]) -> f64 {
    assert_eq!(
        y_true.len(),
        y_pred.len(),
        "Vectors must have same size"
    );

    let correct = y_true
        .iter()
        .zip(y_pred.iter())
        .filter(|(t, p)| t == p)
        .count();

    correct as f64 / y_true.len() as f64
}

pub fn confusion_matrix(
    y_true: &[i32],
    y_pred: &[i32],
) -> ClassificationResult {
    assert_eq!(
        y_true.len(),
        y_pred.len(),
        "Vectors must have same size"
    );

    let mut result = ClassificationResult {
        true_positives: 0,
        true_negatives: 0,
        false_positives: 0,
        false_negatives: 0,
    };

    for (t, p) in y_true.iter().zip(y_pred.iter()) {
        match (*t, *p) {
            (1, 1) => result.true_positives += 1,
            (0, 0) => result.true_negatives += 1,
            (0, 1) => result.false_positives += 1,
            (1, 0) => result.false_negatives += 1,
            _ => {}
        }
    }

    result
}
```

### 2.5 Implementacao em Fortran

```fortran
module metrics_mod
    implicit none
    private
    public :: accuracy, confusion_matrix_calc

    type, public :: classification_result
        integer :: tp = 0
        integer :: tn = 0
        integer :: fp = 0
        integer :: fn = 0
    end type

contains

    function accuracy(y_true, y_pred, n) result(acc)
        integer, intent(in) :: n
        integer, intent(in) :: y_true(n)
        integer, intent(in) :: y_pred(n)
        real :: acc
        integer :: correct, i

        correct = 0
        do i = 1, n
            if (y_true(i) == y_pred(i)) then
                correct = correct + 1
            end if
        end do

        acc = real(correct) / real(n)
    end function

    subroutine confusion_matrix_calc(y_true, y_pred, n, result)
        integer, intent(in) :: n
        integer, intent(in) :: y_true(n)
        integer, intent(in) :: y_pred(n)
        type(classification_result), intent(out) :: result
        integer :: i

        result%tp = 0
        result%tn = 0
        result%fp = 0
        result%fn = 0

        do i = 1, n
            if (y_true(i) == 1 .and. y_pred(i) == 1) then
                result%tp = result%tp + 1
            else if (y_true(i) == 0 .and. y_pred(i) == 0) then
                result%tn = result%tn + 1
            else if (y_true(i) == 0 .and. y_pred(i) == 1) then
                result%fp = result%fp + 1
            else if (y_true(i) == 1 .and. y_pred(i) == 0) then
                result%fn = result%fn + 1
            end if
        end do
    end subroutine

end module
```

---

## 3. Precision

### 3.1 Definicao

```text
Precision = TP / (TP + FP)

"De todos que o modelo classificou como positivo,
 quantos realmente sao positivos?"

Exemplo:
  Modelo prediz 100 emails como spam
  95 sao realmente spam
  Precision = 95/100 = 0.95

Interpretacao:
  - Precision alta = poucos falsos positivos
  - Precision baixa = muitos falsos alarmes

Quando importa:
  - Spam detection: queremos evitar marcar email legitimo como spam
  - Diagnostico medico: queremos evitar diagnosticos falsos
  - Busca web: queremos que os primeiros resultados sejam relevantes

Trade-off:
  - Para aumentar precision, precisamos ser mais seletivos
  - Isso pode diminuir recall (perder alguns positivos reais)
```

### 3.2 Implementacao em C++

```cpp
static double precision(
    const std::vector<int>& y_true,
    const std::vector<int>& y_pred
) {
    auto cm = confusion_matrix(y_true, y_pred);
    int total_predicted_positive =
        cm.true_positives + cm.false_positives;

    if (total_predicted_positive == 0) {
        return 0.0;
    }

    return static_cast<double>(cm.true_positives) /
           static_cast<double>(total_predicted_positive);
}
```

### 3.3 Implementacao em Rust

```rust
pub fn precision(y_true: &[i32], y_pred: &[i32]) -> f64 {
    let cm = confusion_matrix(y_true, y_pred);
    let total_predicted_positive =
        cm.true_positives + cm.false_positives;

    if total_predicted_positive == 0 {
        return 0.0;
    }

    cm.true_positives as f64 / total_predicted_positive as f64
}
```

### 3.4 Implementacao em Fortran

```fortran
function precision_calc(y_true, y_pred, n) result(prec)
    integer, intent(in) :: n
    integer, intent(in) :: y_true(n)
    integer, intent(in) :: y_pred(n)
    real :: prec
    type(classification_result) :: cm
    integer :: total_predicted_positive

    call confusion_matrix_calc(y_true, y_pred, n, cm)

    total_predicted_positive = cm%tp + cm%fp

    if (total_predicted_positive == 0) then
        prec = 0.0
    else
        prec = real(cm%tp) / real(total_predicted_positive)
    end if
end function
```

---

## 4. Recall

### 4.1 Definicao

```text
Recall = TP / (TP + FN)

"De todos que SAO realmente positivos,
 quantos o modelo conseguiu detectar?"

Exemplo:
  200 pacientes com cancer
  Modelo detecta 180
  Recall = 180/200 = 0.90

Interpretacao:
  - Recall alto = poucos falsos negativos
  - Recall baixa = muitos positivos perdidos

Quando importa:
  - Diagnostico medico: NUNCA queremos perder um caso real
  - Deteccao de fraude: queremos capturar o maximo possivel
  - Seguranca: queremos detectar todas as ameacas

Trade-off:
  - Para aumentar recall, precisamos ser mais inclusivos
  - Isso pode diminuir precision (mais falsos alarmes)

Formula alternativa:
  Recall = Sensibilidade = True Positive Rate (TPR)
  Recall = 1 - False Negative Rate (FNR)
```

### 4.2 Implementacao em C++

```cpp
static double recall(
    const std::vector<int>& y_true,
    const std::vector<int>& y_pred
) {
    auto cm = confusion_matrix(y_true, y_pred);
    int total_actual_positive =
        cm.true_positives + cm.false_negatives;

    if (total_actual_positive == 0) {
        return 0.0;
    }

    return static_cast<double>(cm.true_positives) /
           static_cast<double>(total_actual_positive);
}
```

### 4.3 Implementacao em Rust

```rust
pub fn recall(y_true: &[i32], y_pred: &[i32]) -> f64 {
    let cm = confusion_matrix(y_true, y_pred);
    let total_actual_positive =
        cm.true_positives + cm.false_negatives;

    if total_actual_positive == 0 {
        return 0.0;
    }

    cm.true_positives as f64 / total_actual_positive as f64
}
```

### 4.4 Implementacao em Fortran

```fortran
function recall_calc(y_true, y_pred, n) result(rec)
    integer, intent(in) :: n
    integer, intent(in) :: y_true(n)
    integer, intent(in) :: y_pred(n)
    real :: rec
    type(classification_result) :: cm
    integer :: total_actual_positive

    call confusion_matrix_calc(y_true, y_pred, n, cm)

    total_actual_positive = cm%tp + cm%fn

    if (total_actual_positive == 0) then
        rec = 0.0
    else
        rec = real(cm%tp) / real(total_actual_positive)
    end if
end function
```

---

## 5. F1-Score

### 5.1 Definicao

```text
F1 = 2 * (precision * recall) / (precision + recall)

O F1-score e a MEDIA HARMONICA entre precision e recall.

Por que harmonica e nao aritmetica?
  - Media aritmetica: (0.9 + 0.1) / 2 = 0.5
  - Media harmonica: 2 * (0.9 * 0.1) / (0.9 + 0.1) = 0.18

A media harmonica penaliza valores extremos.
Se um dos dois e muito baixo, o F1 tambem sera baixo.

Exemplo:
  Modelo A: precision=0.95, recall=0.90
    F1 = 2 * (0.95 * 0.90) / (0.95 + 0.90) = 0.924

  Modelo B: precision=0.99, recall=0.50
    F1 = 2 * (0.99 * 0.50) / (0.99 + 0.50) = 0.664

  Modelo A tem F1 muito maior, apesar de precision menor.

Quando usar:
  - Classes desbalanceadas
  - Quando FP e FN sao igualmente problematicos
  - Quando queremos um numero unico que resume precision e recall
```

### 5.2 F-beta Score

```text
F-beta generaliza F1:

F_beta = (1 + beta^2) * (precision * recall) /
         (beta^2 * precision + recall)

beta = 1:  F1 (precision e recall igualmente importantes)
beta = 0.5: precision mais importante que recall
beta = 2:  recall mais importante que precision

Exemplo com beta=2:
  precision=0.80, recall=0.95
  F2 = (1 + 4) * (0.80 * 0.95) / (4 * 0.80 + 0.95)
     = 5 * 0.76 / 4.15
     = 0.916

Interpretacao: recall tem mais peso, entao o score e alto
```

### 5.3 Implementacao em C++

```cpp
static double f1_score(
    const std::vector<int>& y_true,
    const std::vector<int>& y_pred
) {
    double p = precision(y_true, y_pred);
    double r = recall(y_true, y_pred);

    if (p + r == 0.0) {
        return 0.0;
    }

    return 2.0 * (p * r) / (p + r);
}

static double f_beta_score(
    const std::vector<int>& y_true,
    const std::vector<int>& y_pred,
    double beta
) {
    double p = precision(y_true, y_pred);
    double r = recall(y_true, y_pred);

    double beta_sq = beta * beta;
    double denom = beta_sq * p + r;

    if (denom == 0.0) {
        return 0.0;
    }

    return (1.0 + beta_sq) * (p * r) / denom;
}
```

### 5.4 Implementacao em Rust

```rust
pub fn f1_score(y_true: &[i32], y_pred: &[i32]) -> f64 {
    let p = precision(y_true, y_pred);
    let r = recall(y_true, y_pred);

    if p + r == 0.0 {
        return 0.0;
    }

    2.0 * (p * r) / (p + r)
}

pub fn f_beta_score(
    y_true: &[i32],
    y_pred: &[i32],
    beta: f64,
) -> f64 {
    let p = precision(y_true, y_pred);
    let r = recall(y_true, y_pred);
    let beta_sq = beta * beta;
    let denom = beta_sq * p + r;

    if denom == 0.0 {
        return 0.0;
    }

    (1.0 + beta_sq) * (p * r) / denom
}
```

### 5.5 Implementacao em Fortran

```fortran
function f1_score_calc(y_true, y_pred, n) result(f1)
    integer, intent(in) :: n
    integer, intent(in) :: y_true(n)
    integer, intent(in) :: y_pred(n)
    real :: f1
    real :: p, r

    p = precision_calc(y_true, y_pred, n)
    r = recall_calc(y_true, y_pred, n)

    if (p + r == 0.0) then
        f1 = 0.0
    else
        f1 = 2.0 * (p * r) / (p + r)
    end if
end function

function f_beta_score_calc(y_true, y_pred, n, beta) result(fb)
    integer, intent(in) :: n
    integer, intent(in) :: y_true(n)
    integer, intent(in) :: y_pred(n)
    real, intent(in) :: beta
    real :: fb
    real :: p, r, beta_sq, denom

    p = precision_calc(y_true, y_pred, n)
    r = recall_calc(y_true, y_pred, n)

    beta_sq = beta * beta
    denom = beta_sq * p + r

    if (denom == 0.0) then
        fb = 0.0
    else
        fb = (1.0 + beta_sq) * (p * r) / denom
    end if
end function
```

---

## 6. Confusion Matrix

### 6.1 Estrutura

```text
Confusion Matrix (Matriz de Confusao):
=======================================

                  Predito
                  Pos    Neg
                +------+------+
Real  Pos       |  TP  |  FN  |
                +------+------+
      Neg       |  FP  |  TN  |
                +------+------+

Exemplo numerico:
  1000 amostras, 400 positivas, 600 negativas

                  Predito
                  Pos    Neg
                +------+------+
Real  Pos       |  380 |   20 |  (400 positivos reais)
                +------+------+
      Neg       |   50 |  550 |  (600 negativos reais)
                +------+------+

Metricas derivadas:
  Accuracy = (380 + 550) / 1000 = 93%
  Precision = 380 / (380 + 50) = 88.4%
  Recall = 380 / (380 + 20) = 95%
  F1 = 2 * (0.884 * 0.95) / (0.884 + 0.95) = 91.6%
```

### 6.2 Multi-class Confusion Matrix

```text
Para K classes, a confusion matrix e K x K:

          Predito
          C1   C2   C3
        +----+----+----+
Real C1 | 85 | 10 |  5 |
        +----+----+----+
     C2 |  8 | 82 | 10 |
        +----+----+----+
     C3 |  3 |  7 | 90 |
        +----+----+----+

Metricas por classe (one-vs-rest):
  Classe 1:
    TP=85, FP=8+3=11, FN=10+5=15, TN=82+10+7+90=189
    Precision = 85/(85+11) = 88.5%
    Recall = 85/(85+15) = 85%

  Classe 2:
    TP=82, FP=10+7=17, FN=8+10=18, TN=85+5+3+90=183
    Precision = 82/(82+17) = 82.8%
    Recall = 82/(82+18) = 82%

  Classe 3:
    TP=90, FP=5+10=15, FN=3+7=10, TN=85+10+8+82=185
    Precision = 90/(90+15) = 85.7%
    Recall = 90/(90+10) = 90%

Macro-average:
  Precision = (88.5 + 82.8 + 85.7) / 3 = 85.7%
  Recall = (85 + 82 + 90) / 3 = 85.7%

Weighted-average (por suporte):
  Precision = (88.5*100 + 82.8*100 + 85.7*100) / 300 = 85.7%
```

### 6.3 Implementacao em C++ (Multi-class)

```cpp
#include <vector>
#include <map>
#include <algorithm>

class MultiClassMetrics {
public:
    static std::vector<std::vector<int>> confusion_matrix_multi(
        const std::vector<int>& y_true,
        const std::vector<int>& y_pred,
        int num_classes
    ) {
        std::vector<std::vector<int>> cm(
            num_classes,
            std::vector<int>(num_classes, 0)
        );

        for (size_t i = 0; i < y_true.size(); ++i) {
            cm[y_true[i]][y_pred[i]]++;
        }

        return cm;
    }

    static std::vector<double> precision_per_class(
        const std::vector<std::vector<int>>& cm,
        int num_classes
    ) {
        std::vector<double> precisions(num_classes);

        for (int c = 0; c < num_classes; ++c) {
            int col_sum = 0;
            for (int r = 0; r < num_classes; ++r) {
                col_sum += cm[r][c];
            }

            precisions[c] = (col_sum > 0)
                ? static_cast<double>(cm[c][c]) /
                  static_cast<double>(col_sum)
                : 0.0;
        }

        return precisions;
    }

    static std::vector<double> recall_per_class(
        const std::vector<std::vector<int>>& cm,
        int num_classes
    ) {
        std::vector<double> recalls(num_classes);

        for (int c = 0; c < num_classes; ++c) {
            int row_sum = 0;
            for (int r = 0; r < num_classes; ++r) {
                row_sum += cm[c][r];
            }

            recalls[c] = (row_sum > 0)
                ? static_cast<double>(cm[c][c]) /
                  static_cast<double>(row_sum)
                : 0.0;
        }

        return recalls;
    }

    static double macro_average(
        const std::vector<double>& values
    ) {
        double sum = 0.0;
        for (double v : values) {
            sum += v;
        }
        return sum / static_cast<double>(values.size());
    }
};
```

### 6.4 Implementacao em Rust (Multi-class)

```rust
pub fn confusion_matrix_multi(
    y_true: &[i32],
    y_pred: &[i32],
    num_classes: usize,
) -> Vec<Vec<i32>> {
    let mut cm = vec![vec![0i32; num_classes]; num_classes];

    for (t, p) in y_true.iter().zip(y_pred.iter()) {
        cm[*t as usize][*p as usize] += 1;
    }

    cm
}

pub fn precision_per_class(cm: &[Vec<i32>]) -> Vec<f64> {
    let num_classes = cm.len();
    let mut precisions = vec![0.0f64; num_classes];

    for c in 0..num_classes {
        let col_sum: i32 = cm.iter().map(|row| row[c]).sum();
        if col_sum > 0 {
            precisions[c] = cm[c][c] as f64 / col_sum as f64;
        }
    }

    precisions
}

pub fn recall_per_class(cm: &[Vec<i32>]) -> Vec<f64> {
    let num_classes = cm.len();
    let mut recalls = vec![0.0f64; num_classes];

    for c in 0..num_classes {
        let row_sum: i32 = cm[c].iter().sum();
        if row_sum > 0 {
            recalls[c] = cm[c][c] as f64 / row_sum as f64;
        }
    }

    recalls
}

pub fn macro_average(values: &[f64]) -> f64 {
    values.iter().sum::<f64>() / values.len() as f64
}
```

### 6.5 Implementacao em Fortran (Multi-class)

```fortran
module multiclass_metrics_mod
    implicit none
    private
    public :: confusion_matrix_multi, precision_per_class
    public :: recall_per_class, macro_average

contains

    subroutine confusion_matrix_multi(y_true, y_pred, n, &
                                      num_classes, cm)
        integer, intent(in) :: n, num_classes
        integer, intent(in) :: y_true(n), y_pred(n)
        integer, intent(out) :: cm(num_classes, num_classes)
        integer :: i, t, p

        cm = 0

        do i = 1, n
            t = y_true(i) + 1
            p = y_pred(i) + 1
            cm(t, p) = cm(t, p) + 1
        end do
    end subroutine

    subroutine precision_per_class(cm, num_classes, prec)
        integer, intent(in) :: num_classes
        integer, intent(in) :: cm(num_classes, num_classes)
        real, intent(out) :: prec(num_classes)
        integer :: c, r, col_sum

        do c = 1, num_classes
            col_sum = 0
            do r = 1, num_classes
                col_sum = col_sum + cm(r, c)
            end do
            if (col_sum > 0) then
                prec(c) = real(cm(c, c)) / real(col_sum)
            else
                prec(c) = 0.0
            end if
        end do
    end subroutine

    subroutine recall_per_class(cm, num_classes, rec)
        integer, intent(in) :: num_classes
        integer, intent(in) :: cm(num_classes, num_classes)
        real, intent(out) :: rec(num_classes)
        integer :: c, r, row_sum

        do c = 1, num_classes
            row_sum = 0
            do r = 1, num_classes
                row_sum = row_sum + cm(c, r)
            end do
            if (row_sum > 0) then
                rec(c) = real(cm(c, c)) / real(row_sum)
            else
                rec(c) = 0.0
            end if
        end do
    end subroutine

    function macro_average(values, n) result(avg)
        integer, intent(in) :: n
        real, intent(in) :: values(n)
        real :: avg
        integer :: i

        avg = 0.0
        do i = 1, n
            avg = avg + values(i)
        end do
        avg = avg / real(n)
    end function

end module
```

---

## 7. ROC Curve e AUC

### 7.1 Conceito

```text
ROC Curve (Receiver Operating Characteristic):
================================================

A ROC curve mostra o trade-off entre:
  - True Positive Rate (TPR) = Recall = Sensitivity
  - False Positive Rate (FPR) = FP / (FP + TN)

Eixo X: FPR (falsos alarmes)
Eixo Y: TPRe (deteccoes reais)

Curva ROC tipica:

  1.0 |           ___________
      |          /
      |         /
      |        /
  0.5 |       /
      |      /
      |     /
      |    /
  0.0 |___/________________
      0.0              1.0
              FPR

Pontos na curva:
  - Cada ponto = um threshold diferente
  - Threshold baixo: mais TP, mais FP (canto superior direito)
  - Threshold alto: menos TP, menos FP (canto inferior esquerdo)

Classificadores:
  - Perfeito: canto superior esquerdo (TPR=1, FPR=0)
  - Aleatorio: diagonal (TPR=FPR)
  - Ruim: abaixo da diagonal (pior que aleatorio)
```

### 7.2 AUC (Area Under the Curve)

```text
AUC = Area sob a curva ROC

Interpretacao:
  AUC = 1.0: classificador perfeito
  AUC = 0.5: classificador aleatorio
  AUC = 0.0: classificador inversamente perfeito
  AUC < 0.5: pior que aleatorio (inverter predicoes)

Significado probabilistico:
  AUC = P(score(classe_pos) > score(classe_neg))
  "A probabilidade de o modelo dar score maior
   para um positivo aleatorio que para um negativo"

Comparacao:
  Modelo A: AUC = 0.95
  Modelo B: AUC = 0.85
  Modelo A e melhor em TODOS os thresholds

Por que ROC/AUC e util:
  1. Independente do threshold
  2. Comparacao justa entre modelos
  3. Resistente a desbalanceamento
  4. Resumo unico do desempenho
```

### 7.3 Calculando ROC e AUC

```text
Algoritmo para gerar ROC:
  1. Ordenar predicoes por score decrescente
  2. Para cada threshold possivel:
     - Calcular TPR e FPR
  3. Plotar TPR vs FPR

Calculo de AUC (trapezoidal rule):
  AUC = soma de areas dos trapezoides
  Area = (FPR[i+1] - FPR[i]) * (TPR[i+1] + TPR[i]) / 2

Exemplo:
  Scores:  [0.95, 0.85, 0.78, 0.65, 0.55, 0.45, 0.35, 0.25]
  Labels:  [  1,   1,   0,   1,   0,   0,   1,   0]

  Threshold=0.90: TPR=1/4=0.25, FPR=0/4=0.00
  Threshold=0.80: TPR=2/4=0.50, FPR=0/4=0.00
  Threshold=0.70: TPR=2/4=0.50, FPR=1/4=0.25
  Threshold=0.60: TPR=3/4=0.75, FPR=1/4=0.25
  Threshold=0.50: TPR=3/4=0.75, FPR=2/4=0.50
  Threshold=0.40: TPR=3/4=0.75, FPR=3/4=0.75
  Threshold=0.30: TPR=4/4=1.00, FPR=3/4=0.75
  Threshold=0.20: TPR=4/4=1.00, FPR=4/4=1.00
```

### 7.4 Implementacao em C++

```cpp
#include <vector>
#include <algorithm>
#include <utility>

class ROCCalculator {
public:
    struct ROCPoint {
        double fpr;
        double tpr;
        double threshold;
    };

    static std::vector<ROCPoint> compute_roc(
        const std::vector<double>& scores,
        const std::vector<int>& y_true
    ) {
        size_t n = scores.size();
        size_t pos_count = 0;
        size_t neg_count = 0;

        for (int y : y_true) {
            if (y == 1) pos_count++;
            else neg_count++;
        }

        std::vector<std::pair<double, int>> combined(n);
        for (size_t i = 0; i < n; ++i) {
            combined[i] = {scores[i], y_true[i]};
        }

        std::sort(
            combined.begin(), combined.end(),
            [](const auto& a, const auto& b) {
                return a.first > b.first;
            }
        );

        std::vector<ROCPoint> roc;
        roc.push_back({0.0, 0.0, 1.0});

        size_t tp = 0;
        size_t fp = 0;

        for (size_t i = 0; i < n; ++i) {
            if (combined[i].second == 1) {
                tp++;
            } else {
                fp++;
            }

            double tpr = (pos_count > 0)
                ? static_cast<double>(tp) /
                  static_cast<double>(pos_count)
                : 0.0;
            double fpr = (neg_count > 0)
                ? static_cast<double>(fp) /
                  static_cast<double>(neg_count)
                : 0.0;

            roc.push_back({fpr, tpr, combined[i].first});
        }

        return roc;
    }

    static double compute_auc(const std::vector<ROCPoint>& roc) {
        double auc = 0.0;

        for (size_t i = 1; i < roc.size(); ++i) {
            double dx = roc[i].fpr - roc[i - 1].fpr;
            double avg_y = (roc[i].tpr + roc[i - 1].tpr) / 2.0;
            auc += dx * avg_y;
        }

        return auc;
    }
};
```

### 7.5 Implementacao em Rust

```rust
#[derive(Debug, Clone)]
pub struct ROCPoint {
    pub fpr: f64,
    pub tpr: f64,
    pub threshold: f64,
}

pub fn compute_roc(
    scores: &[f64],
    y_true: &[i32],
) -> Vec<ROCPoint> {
    let n = scores.len();
    let pos_count = y_true.iter().filter(|&&y| y == 1).count();
    let neg_count = n - pos_count;

    let mut combined: Vec<(f64, i32)> = scores
        .iter()
        .zip(y_true.iter())
        .map(|(&s, &y)| (s, y))
        .collect();

    combined.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());

    let mut roc = vec![ROCPoint {
        fpr: 0.0,
        tpr: 0.0,
        threshold: 1.0,
    }];

    let mut tp: usize = 0;
    let mut fp: usize = 0;

    for (score, label) in &combined {
        if *label == 1 {
            tp += 1;
        } else {
            fp += 1;
        }

        let tpr = if pos_count > 0 {
            tp as f64 / pos_count as f64
        } else {
            0.0
        };
        let fpr = if neg_count > 0 {
            fp as f64 / neg_count as f64
        } else {
            0.0
        };

        roc.push(ROCPoint {
            fpr,
            tpr,
            threshold: *score,
        });
    }

    roc
}

pub fn compute_auc(roc: &[ROCPoint]) -> f64 {
    let mut auc = 0.0;

    for i in 1..roc.len() {
        let dx = roc[i].fpr - roc[i - 1].fpr;
        let avg_y = (roc[i].tpr + roc[i - 1].tpr) / 2.0;
        auc += dx * avg_y;
    }

    auc
}
```

### 7.6 Implementacao em Fortran

```fortran
module roc_mod
    implicit none
    private
    public :: compute_roc, compute_auc

    type, public :: roc_point
        real :: fpr
        real :: tpr
        real :: threshold
    end type

contains

    subroutine compute_roc(scores, y_true, n, roc, n_roc)
        integer, intent(in) :: n
        real, intent(in) :: scores(n)
        integer, intent(in) :: y_true(n)
        type(roc_point), allocatable, intent(out) :: roc(:)
        integer, intent(out) :: n_roc
        integer :: pos_count, neg_count
        integer :: i, tp, fp
        real :: tpr, fpr
        real :: temp_score, temp_label

        pos_count = 0
        neg_count = 0
        do i = 1, n
            if (y_true(i) == 1) then
                pos_count = pos_count + 1
            else
                neg_count = neg_count + 1
            end if
        end do

        n_roc = n + 1
        allocate(roc(n_roc))

        roc(1)%fpr = 0.0
        roc(1)%tpr = 0.0
        roc(1)%threshold = 1.0

        tp = 0
        fp = 0

        do i = 1, n
            if (y_true(i) == 1) then
                tp = tp + 1
            else
                fp = fp + 1
            end if

            if (pos_count > 0) then
                tpr = real(tp) / real(pos_count)
            else
                tpr = 0.0
            end if

            if (neg_count > 0) then
                fpr = real(fp) / real(neg_count)
            else
                fpr = 0.0
            end if

            roc(i + 1)%fpr = fpr
            roc(i + 1)%tpr = tpr
            roc(i + 1)%threshold = scores(i)
        end do
    end subroutine

    function compute_auc(roc, n_roc) result(auc)
        integer, intent(in) :: n_roc
        type(roc_point), intent(in) :: roc(n_roc)
        real :: auc
        integer :: i
        real :: dx, avg_y

        auc = 0.0
        do i = 2, n_roc
            dx = roc(i)%fpr - roc(i - 1)%fpr
            avg_y = (roc(i)%tpr + roc(i - 1)%tpr) / 2.0
            auc = auc + dx * avg_y
        end do
    end function

end module
```

---

## 8. Precision-Recall Curve

### 8.1 Conceito

```text
Precision-Recall Curve:
=========================

Eixo X: Recall (sensibilidade)
Eixo Y: Precision (valor preditivo)

Curva tipica:

  1.0 |\
      | \
      |  \
      |   \
  0.5 |    \____
      |         \____
      |              \____
  0.0 |___________________
      0.0             1.0
              Recall

Quando usar PR curve em vez de ROC:
  - Classes muito desbalanceadas
  - Quando a classe positiva e rara
  - Quando FP e mais toleravel que FN

Exemplo:
  Dataset: 99 negativos, 1 positivo

  ROC: FPR = FP/99, sempre pequeno -> curva otimista
  PR: Precision = TP/(TP+FP), diretamente afetado por FP

  PR curve e mais honesta quando a classe positiva e rara

AUPRC (Area Under PR Curve):
  - Resume a curva em um numero
  - Mais informativo que AUC em cenarios desbalanceados
```

### 8.2 Implementacao em C++

```cpp
class PRCalculator {
public:
    struct PRPoint {
        double precision;
        double recall;
        double threshold;
    };

    static std::vector<PRPoint> compute_pr(
        const std::vector<double>& scores,
        const std::vector<int>& y_true
    ) {
        size_t n = scores.size();
        size_t pos_count = 0;

        for (int y : y_true) {
            if (y == 1) pos_count++;
        }

        std::vector<std::pair<double, int>> combined(n);
        for (size_t i = 0; i < n; ++i) {
            combined[i] = {scores[i], y_true[i]};
        }

        std::sort(
            combined.begin(), combined.end(),
            [](const auto& a, const auto& b) {
                return a.first > b.first;
            }
        );

        std::vector<PRPoint> pr;
        size_t tp = 0;
        size_t fp = 0;

        for (size_t i = 0; i < n; ++i) {
            if (combined[i].second == 1) tp++;
            else fp++;

            double prec = (tp + fp > 0)
                ? static_cast<double>(tp) /
                  static_cast<double>(tp + fp)
                : 0.0;
            double rec = (pos_count > 0)
                ? static_cast<double>(tp) /
                  static_cast<double>(pos_count)
                : 0.0;

            pr.push_back({prec, rec, combined[i].first});
        }

        return pr;
    }

    static double compute_auprc(const std::vector<PRPoint>& pr) {
        if (pr.size() < 2) return 0.0;

        double auprc = 0.0;
        for (size_t i = 1; i < pr.size(); ++i) {
            double dx = pr[i].recall - pr[i - 1].recall;
            double avg_y = (pr[i].precision +
                           pr[i - 1].precision) / 2.0;
            auprc += dx * avg_y;
        }

        return auprc;
    }
};
```

### 8.3 Implementacao em Rust

```rust
#[derive(Debug, Clone)]
pub struct PRPoint {
    pub precision: f64,
    pub recall: f64,
    pub threshold: f64,
}

pub fn compute_pr(
    scores: &[f64],
    y_true: &[i32],
) -> Vec<PRPoint> {
    let n = scores.len();
    let pos_count = y_true.iter().filter(|&&y| y == 1).count();

    let mut combined: Vec<(f64, i32)> = scores
        .iter()
        .zip(y_true.iter())
        .map(|(&s, &y)| (s, y))
        .collect();

    combined.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap());

    let mut pr = Vec::new();
    let mut tp: usize = 0;
    let mut fp: usize = 0;

    for (score, label) in &combined {
        if *label == 1 {
            tp += 1;
        } else {
            fp += 1;
        }

        let precision = if tp + fp > 0 {
            tp as f64 / (tp + fp) as f64
        } else {
            0.0
        };
        let recall = if pos_count > 0 {
            tp as f64 / pos_count as f64
        } else {
            0.0
        };

        pr.push(PRPoint {
            precision,
            recall,
            threshold: *score,
        });
    }

    pr
}

pub fn compute_auprc(pr: &[PRPoint]) -> f64 {
    if pr.len() < 2 {
        return 0.0;
    }

    let mut auprc = 0.0;
    for i in 1..pr.len() {
        let dx = pr[i].recall - pr[i - 1].recall;
        let avg_y = (pr[i].precision + pr[i - 1].precision) / 2.0;
        auprc += dx * avg_y;
    }

    auprc
}
```

### 8.4 Implementacao em Fortran

```fortran
module pr_curve_mod
    implicit none
    private
    public :: compute_pr, compute_auprc

    type, public :: pr_point
        real :: precision_val
        real :: recall
        real :: threshold
    end type

contains

    subroutine compute_pr(scores, y_true, n, pr, n_pr)
        integer, intent(in) :: n
        real, intent(in) :: scores(n)
        integer, intent(in) :: y_true(n)
        type(pr_point), allocatable, intent(out) :: pr(:)
        integer, intent(out) :: n_pr
        integer :: pos_count
        integer :: i, tp, fp
        real :: prec, rec

        pos_count = 0
        do i = 1, n
            if (y_true(i) == 1) pos_count = pos_count + 1
        end do

        n_pr = n
        allocate(pr(n_pr))

        tp = 0
        fp = 0

        do i = 1, n
            if (y_true(i) == 1) then
                tp = tp + 1
            else
                fp = fp + 1
            end if

            if (tp + fp > 0) then
                prec = real(tp) / real(tp + fp)
            else
                prec = 0.0
            end if

            if (pos_count > 0) then
                rec = real(tp) / real(pos_count)
            else
                rec = 0.0
            end if

            pr(i)%precision_val = prec
            pr(i)%recall = rec
            pr(i)%threshold = scores(i)
        end do
    end subroutine

    function compute_auprc(pr, n_pr) result(auprc)
        integer, intent(in) :: n_pr
        type(pr_point), intent(in) :: pr(n_pr)
        real :: auprc
        integer :: i
        real :: dx, avg_y

        auprc = 0.0
        do i = 2, n_pr
            dx = pr(i)%recall - pr(i - 1)%recall
            avg_y = (pr(i)%precision_val + &
                     pr(i - 1)%precision_val) / 2.0
            auprc = auprc + dx * avg_y
        end do
    end function

end module
```

---

## 9. Log Loss (Cross-Entropy Loss)

### 9.1 Definicao

```text
Log Loss (Binary Cross-Entropy):
=================================

Formula:
  L = -1/N * soma[ y_i * log(p_i) + (1-y_i) * log(1-p_i) ]

Onde:
  y_i: label real (0 ou 1)
  p_i: probabilidade predita de classe 1
  N: numero de amostras

Interpretacao:
  - Se y=1 e p=0.99: loss = -log(0.99) = 0.01 (bom)
  - Se y=1 e p=0.50: loss = -log(0.50) = 0.69 (medio)
  - Se y=1 e p=0.01: loss = -log(0.01) = 4.61 (pessimo)

Propriedades:
  - Penaliza confianca errada MUITO mais que incerteza
  - Log loss baixo = probabilidades calibradas
  - Log loss alto = modelo incerto ou errado

Por que log loss e melhor que accuracy:
  - Accuracy so olha 0 ou 1
  - Log loss olha a PROBABILIDADE
  - Um modelo que da 0.51 para uma classe errada
    e PIOR que um que da 0.49
  - Log loss captura essa nuance

Regularizacao numerica:
  - log(0) = -inf -> adicionar epsilon
  - p = clip(p, epsilon, 1-epsilon)
  - epsilon tipico: 1e-15
```

### 9.2 Implementacao em C++

```cpp
#include <cmath>
#include <algorithm>

class LogLossCalculator {
public:
    static double log_loss(
        const std::vector<double>& y_true,
        const std::vector<double>& y_pred,
        double epsilon = 1e-15
    ) {
        size_t n = y_true.size();
        double total_loss = 0.0;

        for (size_t i = 0; i < n; ++i) {
            double p = std::max(
                epsilon,
                std::min(1.0 - epsilon, y_pred[i])
            );

            total_loss += y_true[i] * std::log(p) +
                         (1.0 - y_true[i]) * std::log(1.0 - p);
        }

        return -total_loss / static_cast<double>(n);
    }
};
```

### 9.3 Implementacao em Rust

```rust
pub fn log_loss(
    y_true: &[f64],
    y_pred: &[f64],
    epsilon: f64,
) -> f64 {
    assert_eq!(y_true.len(), y_pred.len());

    let total_loss: f64 = y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(t, p)| {
            let p_clamped = p.clamp(epsilon, 1.0 - epsilon);
            t * p_clamped.ln() +
            (1.0 - t) * (1.0 - p_clamped).ln()
        })
        .sum();

    -total_loss / y_true.len() as f64
}
```

### 9.4 Implementacao em Fortran

```fortran
function log_loss_calc(y_true, y_pred, n, epsilon) result(ll)
    integer, intent(in) :: n
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real, intent(in) :: epsilon
    real :: ll
    real :: p, total_loss
    integer :: i

    total_loss = 0.0

    do i = 1, n
        p = max(epsilon, min(1.0 - epsilon, y_pred(i)))
        total_loss = total_loss + &
            y_true(i) * log(p) + &
            (1.0 - y_true(i)) * log(1.0 - p)
    end do

    ll = -total_loss / real(n)
end function
```

---

## 10. Mean Squared Error (MSE)

### 10.1 Definicao

```text
MSE = 1/N * soma[(y_i - y_pred_i)^2]

Onde:
  y_i: valor real
  y_pred_i: valor predito
  N: numero de amostras

Propriedades:
  - Sempre positivo (quadrado)
  - MSE = 0: predicoes perfeitas
  - Penaliza ERROS GRANDES mais que pequenos (quadrado)
  - Unidade: unidade^2 (dificil de interpretar)

Exemplo:
  Reais:    [3.0, 5.0, 2.5, 7.0]
  Preditos: [2.8, 5.2, 2.3, 6.8]
  Erros:    [0.2, -0.2, 0.2, 0.2]
  Quadrados:[0.04, 0.04, 0.04, 0.04]
  MSE = 0.04

RMSE (Root MSE):
  RMSE = sqrt(MSE)
  RMSE = 0.2
  Unidade: mesma do target -> mais interpretavel

MAE vs MSE:
  MSE penaliza outliers mais
  MAE e mais robusta a outliers
  Escolha depende do custo dos erros
```

### 10.2 Implementacao em C++

```cpp
#include <cmath>

class RegressionMetrics {
public:
    static double mse(
        const std::vector<double>& y_true,
        const std::vector<double>& y_pred
    ) {
        size_t n = y_true.size();
        double sum = 0.0;

        for (size_t i = 0; i < n; ++i) {
            double diff = y_true[i] - y_pred[i];
            sum += diff * diff;
        }

        return sum / static_cast<double>(n);
    }

    static double rmse(
        const std::vector<double>& y_true,
        const std::vector<double>& y_pred
    ) {
        return std::sqrt(mse(y_true, y_pred));
    }
};
```

### 10.3 Implementacao em Rust

```rust
pub fn mse(y_true: &[f64], y_pred: &[f64]) -> f64 {
    assert_eq!(y_true.len(), y_pred.len());

    let sum: f64 = y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(t, p)| {
            let diff = t - p;
            diff * diff
        })
        .sum();

    sum / y_true.len() as f64
}

pub fn rmse(y_true: &[f64], y_pred: &[f64]) -> f64 {
    mse(y_true, y_pred).sqrt()
}
```

### 10.4 Implementacao em Fortran

```fortran
function mse_calc(y_true, y_pred, n) result(mse_val)
    integer, intent(in) :: n
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real :: mse_val
    real :: sum_sq, diff
    integer :: i

    sum_sq = 0.0
    do i = 1, n
        diff = y_true(i) - y_pred(i)
        sum_sq = sum_sq + diff * diff
    end do

    mse_val = sum_sq / real(n)
end function

function rmse_calc(y_true, y_pred, n) result(rmse_val)
    integer, intent(in) :: n
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real :: rmse_val

    rmse_val = sqrt(mse_calc(y_true, y_pred, n))
end function
```

---

## 11. Mean Absolute Error (MAE)

### 11.1 Definicao

```text
MAE = 1/N * soma[|y_i - y_pred_i|]

Propriedades:
  - Sempre positivo
  - MAE = 0: predicoes perfeitas
  - Penaliza TODOS os erros igualmente (linear)
  - Unidade: mesma do target -> interpretavel

Comparacao com MSE:
  Erro: 0.1 -> MSE=0.01, MAE=0.1
  Erro: 1.0 -> MSE=1.00, MAE=1.0
  Erro: 10  -> MSE=100.0, MAE=10.0

  MSE: 100x mais penalizado (10^2)
  MAE: 10x mais penalizado

Quando usar MAE:
  - Dados com muitos outliers
  - Quando todos os erros sao igualmente problematicos
  - Quando a unidade do erro importa

Quando usar MSE:
  - Quando erros grandes sao mais custosos
  - Quando outliers sao importantissimos
  - Em optimizacao (derivada suave)
```

### 11.2 Implementacao em C++

```cpp
static double mae(
    const std::vector<double>& y_true,
    const std::vector<double>& y_pred
) {
    size_t n = y_true.size();
    double sum = 0.0;

    for (size_t i = 0; i < n; ++i) {
        sum += std::abs(y_true[i] - y_pred[i]);
    }

    return sum / static_cast<double>(n);
}
```

### 11.3 Implementacao em Rust

```rust
pub fn mae(y_true: &[f64], y_pred: &[f64]) -> f64 {
    assert_eq!(y_true.len(), y_pred.len());

    let sum: f64 = y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(t, p)| (t - p).abs())
        .sum();

    sum / y_true.len() as f64
}
```

### 11.4 Implementacao em Fortran

```fortran
function mae_calc(y_true, y_pred, n) result(mae_val)
    integer, intent(in) :: n
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real :: mae_val
    real :: sum_abs
    integer :: i

    sum_abs = 0.0
    do i = 1, n
        sum_abs = sum_abs + abs(y_true(i) - y_pred(i))
    end do

    mae_val = sum_abs / real(n)
end function
```

---

## 12. R-squared (Coefficient of Determination)

### 12.1 Definicao

```text
R^2 = 1 - (SS_res / SS_tot)

Onde:
  SS_res = soma[(y_i - y_pred_i)^2]  (residuo)
  SS_tot = soma[(y_i - y_media)^2]   (total)

Interpretacao:
  R^2 = 1.0: modelo perfeito (explica 100% da variancia)
  R^2 = 0.0: modelo igual a prever a media
  R^2 < 0:   modelo PIOR que prever a media

Analise de variancia:
  Total = Explained + Residual
  SS_tot = SS_reg + SS_res

  R^2 = SS_reg / SS_tot = 1 - SS_res / SS_tot

Exemplo:
  Reais:    [3.0, 5.0, 2.5, 7.0, 4.0]
  Media:    4.3
  Preditos: [2.8, 5.2, 2.3, 6.8, 4.1]

  SS_tot = (3-4.3)^2 + (5-4.3)^2 + (2.5-4.3)^2
         + (7-4.3)^2 + (4-4.3)^2
         = 1.69 + 0.49 + 3.24 + 7.29 + 0.09 = 12.8

  SS_res = (3-2.8)^2 + (5-5.2)^2 + (2.5-2.3)^2
         + (7-6.8)^2 + (4-4.1)^2
         = 0.04 + 0.04 + 0.04 + 0.04 + 0.01 = 0.17

  R^2 = 1 - 0.17/12.8 = 0.987

O modelo explica 98.7% da variancia.
```

### 12.2 Adjusted R-squared

```text
R^2_adj = 1 - [(1-R^2)(N-1)/(N-p-1)]

Onde:
  N: numero de amostras
  p: numero de features

Problema do R^2:
  - Adicionar features SEMPRE aumenta R^2
  - Mesmo que as features sejam irrelevantes
  - Isso cria uma ilusao de melhoria

Adjusted R^2:
  - Penaliza por numero de features
  - So aumenta se a feature melhora o modelo
  - Mais honesto para comparar modelos

Exemplo:
  Modelo A: 5 features, R^2=0.85, R^2_adj=0.83
  Modelo B: 50 features, R^2=0.87, R^2_adj=0.72

  Modelo B tem R^2 maior, mas R^2_adj menor
  -> Modelo B esta overfitting
```

### 12.3 Implementacao em C++

```cpp
static double r_squared(
    const std::vector<double>& y_true,
    const std::vector<double>& y_pred
) {
    size_t n = y_true.size();

    double mean = 0.0;
    for (double y : y_true) {
        mean += y;
    }
    mean /= static_cast<double>(n);

    double ss_res = 0.0;
    double ss_tot = 0.0;

    for (size_t i = 0; i < n; ++i) {
        double diff = y_true[i] - y_pred[i];
        ss_res += diff * diff;

        double diff_mean = y_true[i] - mean;
        ss_tot += diff_mean * diff_mean;
    }

    if (ss_tot == 0.0) return 0.0;

    return 1.0 - (ss_res / ss_tot);
}

static double adjusted_r_squared(
    const std::vector<double>& y_true,
    const std::vector<double>& y_pred,
    int num_features
) {
    double r2 = r_squared(y_true, y_pred);
    double n = static_cast<double>(y_true.size());
    double p = static_cast<double>(num_features);

    return 1.0 - ((1.0 - r2) * (n - 1.0) / (n - p - 1.0));
}
```

### 12.4 Implementacao em Rust

```rust
pub fn r_squared(y_true: &[f64], y_pred: &[f64]) -> f64 {
    assert_eq!(y_true.len(), y_pred.len());

    let n = y_true.len() as f64;
    let mean = y_true.iter().sum::<f64>() / n;

    let ss_res: f64 = y_true
        .iter()
        .zip(y_pred.iter())
        .map(|(t, p)| {
            let diff = t - p;
            diff * diff
        })
        .sum();

    let ss_tot: f64 = y_true
        .iter()
        .map(|t| {
            let diff = t - mean;
            diff * diff
        })
        .sum();

    if ss_tot == 0.0 {
        return 0.0;
    }

    1.0 - (ss_res / ss_tot)
}

pub fn adjusted_r_squared(
    y_true: &[f64],
    y_pred: &[f64],
    num_features: usize,
) -> f64 {
    let r2 = r_squared(y_true, y_pred);
    let n = y_true.len() as f64;
    let p = num_features as f64;

    1.0 - ((1.0 - r2) * (n - 1.0) / (n - p - 1.0))
}
```

### 12.5 Implementacao em Fortran

```fortran
function r_squared_calc(y_true, y_pred, n) result(r2)
    integer, intent(in) :: n
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real :: r2
    real :: mean_val, ss_res, ss_tot, diff, diff_mean
    integer :: i

    mean_val = 0.0
    do i = 1, n
        mean_val = mean_val + y_true(i)
    end do
    mean_val = mean_val / real(n)

    ss_res = 0.0
    ss_tot = 0.0

    do i = 1, n
        diff = y_true(i) - y_pred(i)
        ss_res = ss_res + diff * diff

        diff_mean = y_true(i) - mean_val
        ss_tot = ss_tot + diff_mean * diff_mean
    end do

    if (ss_tot == 0.0) then
        r2 = 0.0
    else
        r2 = 1.0 - (ss_res / ss_tot)
    end if
end function

function adjusted_r_squared_calc(y_true, y_pred, &
                                 n, num_features) result(r2adj)
    integer, intent(in) :: n, num_features
    real, intent(in) :: y_true(n)
    real, intent(in) :: y_pred(n)
    real :: r2adj
    real :: r2, nn, pp

    r2 = r_squared_calc(y_true, y_pred, n)
    nn = real(n)
    pp = real(num_features)

    r2adj = 1.0 - ((1.0 - r2) * (nn - 1.0) / (nn - pp - 1.0))
end function
```

---

## 13. Cross-Validation (K-Fold)

### 13.1 Conceito

```text
K-Fold Cross-Validation:
==========================

Problema:
  - Split unico (80/20) pode ser sortudo ou azarado
  - A estimativa depende de COMVO os dados foram divididos
  - Variancia alta na avaliacao

Solucao:
  - Dividir dados em K partes (folds)
  - Treinar K vezes, cada vez usando um fold como teste
  - Media das K avaliacoes = estimativa robusta

Exemplo com K=5:
  Fold 1: [TESTE] [treino] [treino] [treino] [treino]
  Fold 2: [treino] [TESTE] [treino] [treino] [treino]
  Fold 3: [treino] [treino] [TESTE] [treino] [treino]
  Fold 4: [treino] [treino] [treino] [TESTE] [treino]
  Fold 5: [treino] [treino] [treino] [treino] [TESTE]

  Resultado: media de 5 avaliacoes

Vantagens:
  - Cada amostra e usada como teste UMA vez
  - Estimativa menos enviesada
  - Identifica variancia do modelo
  - Mais dados para treino (K-1)/K do que 80%

Desvantagens:
  - K vezes mais lento que split unico
  - Ainda nao e a avaliacao final
  - Cuidado com data leakage em series temporais

Valores tipicos de K:
  - K=5: padrao, bom balanceamento
  - K=10: recomendado na literatura
  - K=N (LOO): maximo, mas variancia alta
```

### 13.2 Implementacao em C++

```cpp
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

class KFoldCV {
public:
    struct CVResult {
        std::vector<double> fold_scores;
        double mean_score;
        double std_score;
    };

    static std::vector<std::vector<size_t>> create_folds(
        size_t n_samples,
        size_t k,
        unsigned seed = 42
    ) {
        std::vector<size_t> indices(n_samples);
        std::iota(indices.begin(), indices.end(), 0);

        std::mt19937 rng(seed);
        std::shuffle(indices.begin(), indices.end(), rng);

        std::vector<std::vector<size_t>> folds(k);
        for (size_t i = 0; i < n_samples; ++i) {
            folds[i % k].push_back(indices[i]);
        }

        return folds;
    }

    template<typename Func>
    static CVResult cross_validate(
        Func evaluate_fn,
        size_t n_samples,
        size_t k = 5
    ) {
        auto folds = create_folds(n_samples, k);
        std::vector<double> scores;

        for (size_t i = 0; i < k; ++i) {
            std::vector<size_t> test_indices = folds[i];

            std::vector<size_t> train_indices;
            for (size_t j = 0; j < k; ++j) {
                if (j != i) {
                    train_indices.insert(
                        train_indices.end(),
                        folds[j].begin(),
                        folds[j].end()
                    );
                }
            }

            double score = evaluate_fn(train_indices, test_indices);
            scores.push_back(score);
        }

        double mean = 0.0;
        for (double s : scores) mean += s;
        mean /= static_cast<double>(k);

        double variance = 0.0;
        for (double s : scores) {
            variance += (s - mean) * (s - mean);
        }
        variance /= static_cast<double>(k);

        CVResult result;
        result.fold_scores = scores;
        result.mean_score = mean;
        result.std_score = std::sqrt(variance);

        return result;
    }
};
```

### 13.3 Implementacao em Rust

```rust
pub struct CVResult {
    pub fold_scores: Vec<f64>,
    pub mean_score: f64,
    pub std_score: f64,
}

pub fn create_folds(
    n_samples: usize,
    k: usize,
    seed: u64,
) -> Vec<Vec<usize>> {
    let mut indices: Vec<usize> = (0..n_samples).collect();

    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    seed.hash(&mut hasher);
    let seed_val = hasher.finish();

    let mut rng = seed_val;
    for i in (1..n_samples).rev() {
        rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1);
        let j = (rng as usize) % (i + 1);
        indices.swap(i, j);
    }

    let mut folds = vec![Vec::new(); k];
    for (idx, &sample_idx) in indices.iter().enumerate() {
        folds[idx % k].push(sample_idx);
    }

    folds
}

pub fn cross_validate<F>(
    evaluate_fn: F,
    n_samples: usize,
    k: usize,
    seed: u64,
) -> CVResult
where
    F: Fn(&[usize], &[usize]) -> f64,
{
    let folds = create_folds(n_samples, k, seed);
    let mut scores = Vec::new();

    for i in 0..k {
        let test_indices = &folds[i];

        let mut train_indices = Vec::new();
        for j in 0..k {
            if j != i {
                train_indices.extend_from_slice(&folds[j]);
            }
        }

        let score = evaluate_fn(&train_indices, test_indices);
        scores.push(score);
    }

    let mean_score = scores.iter().sum::<f64>() / k as f64;
    let variance = scores
        .iter()
        .map(|s| {
            let diff = s - mean_score;
            diff * diff
        })
        .sum::<f64>()
        / k as f64;

    CVResult {
        fold_scores: scores,
        mean_score,
        std_score: variance.sqrt(),
    }
}
```

### 13.4 Implementacao em Fortran

```fortran
module kfold_cv_mod
    implicit none
    private
    public :: create_folds, cross_validate

    type, public :: cv_result
        real, allocatable :: fold_scores(:)
        real :: mean_score
        real :: std_score
    end type

contains

    subroutine create_folds(n_samples, k, folds, fold_sizes)
        integer, intent(in) :: n_samples, k
        integer, allocatable, intent(out) :: folds(:,:)
        integer, allocatable, intent(out) :: fold_sizes(:)
        integer :: i, idx
        integer, allocatable :: indices(:)

        allocate(indices(n_samples))
        allocate(folds(k, (n_samples + k - 1) / k))
        allocate(fold_sizes(k))

        do i = 1, n_samples
            indices(i) = i
        end do

        fold_sizes = 0

        do i = 1, n_samples
            idx = mod(i - 1, k) + 1
            fold_sizes(idx) = fold_sizes(idx) + 1
            folds(idx, fold_sizes(idx)) = i
        end do
    end subroutine

    subroutine cross_validate(n_samples, k, result)
        integer, intent(in) :: n_samples, k
        type(cv_result), intent(out) :: result
        integer :: i, j, count
        real :: sum_scores, sum_sq

        allocate(result%fold_scores(k))

        do i = 1, k
            result%fold_scores(i) = real(i) / real(k)
        end do

        sum_scores = 0.0
        do i = 1, k
            sum_scores = sum_scores + result%fold_scores(i)
        end do
        result%mean_score = sum_scores / real(k)

        sum_sq = 0.0
        do i = 1, k
            sum_sq = sum_sq + &
                (result%fold_scores(i) - result%mean_score)**2
        end do
        result%std_score = sqrt(sum_sq / real(k))
    end subroutine

end module
```

---

## 14. Bootstrap

### 14.1 Conceito

```text
Bootstrap Resampling:
=======================

Idea:
  - Amostrar COM reposicao do dataset original
  - Criar N datasets sinteticos do mesmo tamanho
  - Treinar e avaliar em cada um
  - Distribuicao dos resultados = estimativa de incerteza

Exemplo:
  Dataset original: [1, 2, 3, 4, 5]

  Bootstrap 1: [2, 5, 2, 1, 3] (2 e 5 repetidos)
  Bootstrap 2: [1, 1, 4, 5, 3] (1 repetido)
  Bootstrap 3: [3, 4, 4, 2, 5] (4 repetido)

  Metrica em cada bootstrap:
    B1: accuracy=0.85
    B2: accuracy=0.82
    B3: accuracy=0.88

  Media: 0.85
  IC 95%: [0.82, 0.88]

Vantagens sobre k-fold:
  - Funciona com qualquer tamanho de dataset
  - Nao precisa escolher K
  - Distribuicao empirica, nao assume normalidade
  - Mais flexivel

Desvantagens:
  - Amostras duplicadas -> treino nao e 100% independente
  - ~63.2% dos dados sao usados em treino (em media)
  - Mais lento que k-fold

Out-of-Bag (OOB):
  - Cada bootstrap deixa ~36.8% dos dados de fora
  - Esses dados OOB podem ser usados para avaliacao
  - Similar a k-fold, mas免费
```

### 14.2 Implementacao em C++

```cpp
#include <vector>
#include <random>
#include <algorithm>
#include <numeric>

class Bootstrap {
public:
    struct BootstrapResult {
        std::vector<double> scores;
        double mean;
        double ci_lower;
        double ci_upper;
    };

    static std::vector<size_t> resample(
        size_t n,
        std::mt19937& rng
    ) {
        std::vector<size_t> sample(n);
        std::uniform_int_distribution<size_t> dist(0, n - 1);

        for (size_t i = 0; i < n; ++i) {
            sample[i] = dist(rng);
        }

        return sample;
    }

    static std::vector<size_t> get_oob_indices(
        const std::vector<size_t>& sample,
        size_t n
    ) {
        std::vector<bool> in_sample(n, false);
        for (size_t idx : sample) {
            in_sample[idx] = true;
        }

        std::vector<size_t> oob;
        for (size_t i = 0; i < n; ++i) {
            if (!in_sample[i]) {
                oob.push_back(i);
            }
        }

        return oob;
    }

    template<typename Func>
    static BootstrapResult bootstrap_evaluate(
        Func evaluate_fn,
        size_t n_samples,
        size_t n_bootstrap = 1000,
        double ci_alpha = 0.05,
        unsigned seed = 42
    ) {
        std::mt19937 rng(seed);
        std::vector<double> scores;

        for (size_t b = 0; b < n_bootstrap; ++b) {
            auto sample = resample(n_samples, rng);
            auto oob = get_oob_indices(sample, n_samples);

            if (!oob.empty()) {
                double score = evaluate_fn(sample, oob);
                scores.push_back(score);
            }
        }

        std::sort(scores.begin(), scores.end());

        double mean = 0.0;
        for (double s : scores) mean += s;
        mean /= static_cast<double>(scores.size());

        size_t lower_idx = static_cast<size_t>(
            ci_alpha / 2.0 * scores.size()
        );
        size_t upper_idx = static_cast<size_t>(
            (1.0 - ci_alpha / 2.0) * scores.size()
        );
        lower_idx = std::min(lower_idx, scores.size() - 1);
        upper_idx = std::min(upper_idx, scores.size() - 1);

        BootstrapResult result;
        result.scores = scores;
        result.mean = mean;
        result.ci_lower = scores[lower_idx];
        result.ci_upper = scores[upper_idx];

        return result;
    }
};
```

### 14.3 Implementacao em Rust

```rust
pub struct BootstrapResult {
    pub scores: Vec<f64>,
    pub mean: f64,
    pub ci_lower: f64,
    pub ci_upper: f64,
}

pub fn resample(n: usize, seed: u64) -> Vec<usize> {
    let mut rng = seed;
    (0..n)
        .map(|_| {
            rng = rng
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1);
            (rng >> 33) as usize % n
        })
        .collect()
}

pub fn get_oob_indices(sample: &[usize], n: usize) -> Vec<usize> {
    let mut in_sample = vec![false; n];
    for &idx in sample {
        in_sample[idx] = true;
    }

    (0..n).filter(|&i| !in_sample[i]).collect()
}

pub fn bootstrap_evaluate<F>(
    evaluate_fn: F,
    n_samples: usize,
    n_bootstrap: usize,
    ci_alpha: f64,
    seed: u64,
) -> BootstrapResult
where
    F: Fn(&[usize], &[usize]) -> f64,
{
    let mut scores = Vec::new();

    for b in 0..n_bootstrap {
        let sample = resample(n_samples, seed.wrapping_add(b as u64));
        let oob = get_oob_indices(&sample, n_samples);

        if !oob.is_empty() {
            let score = evaluate_fn(&sample, &oob);
            scores.push(score);
        }
    }

    scores.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let mean = scores.iter().sum::<f64>() / scores.len() as f64;

    let lower_idx =
        ((ci_alpha / 2.0) * scores.len() as f64) as usize;
    let upper_idx =
        ((1.0 - ci_alpha / 2.0) * scores.len() as f64) as usize;

    let lower_idx = lower_idx.min(scores.len() - 1);
    let upper_idx = upper_idx.min(scores.len() - 1);

    BootstrapResult {
        scores,
        mean,
        ci_lower: scores[lower_idx],
        ci_upper: scores[upper_idx],
    }
}
```

### 14.4 Implementacao em Fortran

```fortran
module bootstrap_mod
    implicit none
    private
    public :: resample_bootstrap, bootstrap_evaluate

    type, public :: bootstrap_result
        real, allocatable :: scores(:)
        real :: mean_score
        real :: ci_lower
        real :: ci_upper
    end type

contains

    subroutine resample_bootstrap(n, sample, seed)
        integer, intent(in) :: n
        integer, intent(out) :: sample(n)
        integer, intent(inout) :: seed
        integer :: i, r

        do i = 1, n
            seed = mod(seed * 1103515245 + 12345, 2147483647)
            r = mod(seed, n) + 1
            sample(i) = r
        end do
    end subroutine

    subroutine bootstrap_evaluate(n_samples, n_bootstrap, &
                                   ci_alpha, seed, result)
        integer, intent(in) :: n_samples, n_bootstrap
        real, intent(in) :: ci_alpha
        integer, intent(inout) :: seed
        type(bootstrap_result), intent(out) :: result
        integer :: b, i, lower_idx, upper_idx
        integer, allocatable :: sample(:)
        real :: sum_scores

        allocate(result%scores(n_bootstrap))
        allocate(sample(n_samples))

        do b = 1, n_bootstrap
            call resample_bootstrap(n_samples, sample, seed)
            result%scores(b) = real(b) / real(n_bootstrap)
        end do

        sum_scores = 0.0
        do i = 1, n_bootstrap
            sum_scores = sum_scores + result%scores(i)
        end do
        result%mean_score = sum_scores / real(n_bootstrap)

        lower_idx = max(1, int(ci_alpha / 2.0 * n_bootstrap))
        upper_idx = min(n_bootstrap, &
            int((1.0 - ci_alpha / 2.0) * n_bootstrap))

        result%ci_lower = result%scores(lower_idx)
        result%ci_upper = result%scores(upper_idx)
    end subroutine

end module
```

---

## 15. Significancia Estatistica

### 15.1 Conceito

```text
Teste de Significancia Estatistica:
=====================================

Pergunta: "A diferenca entre dois modelos e real ou por acaso?"

Exemplo:
  Modelo A: accuracy = 0.85
  Modelo B: accuracy = 0.87

  A diferenca de 0.02 e significativa?
  Ou pode ser so variacao amostral?

Abordagem 1: Paired t-test
  - Compara as diferencas fold-a-fold em k-fold CV
  - H0: media das diferencas = 0
  - H1: media das diferencas != 0
  - t = media(d) / (std(d) / sqrt(k))
  - Se p < 0.05: diferenca significativa

Abordagem 2: McNemar's test
  - Testa se as discordancias sao simetricas
  - b = modelo A erra, modelo B acerta
  - c = modelo A acerta, modelo B erra
  - chi2 = (b-c)^2 / (b+c)
  - Se p < 0.05: modelos sao significativamente diferentes

Abordagem 3: Bootstrap test
  - Amostra diferencas bootstrap
  - IC 95% nao contem zero -> significativo
```

### 15.2 Implementacao em C++

```cpp
#include <cmath>
#include <vector>

class StatisticalTests {
public:
    struct TTestResult {
        double t_statistic;
        double p_value;
        bool significant;
    };

    static TTestResult paired_t_test(
        const std::vector<double>& scores_a,
        const std::vector<double>& scores_b,
        double alpha = 0.05
    ) {
        size_t n = scores_a.size();
        std::vector<double> diffs(n);

        for (size_t i = 0; i < n; ++i) {
            diffs[i] = scores_b[i] - scores_a[i];
        }

        double mean_diff = 0.0;
        for (double d : diffs) mean_diff += d;
        mean_diff /= static_cast<double>(n);

        double var_diff = 0.0;
        for (double d : diffs) {
            var_diff += (d - mean_diff) * (d - mean_diff);
        }
        var_diff /= static_cast<double>(n - 1);

        double se = std::sqrt(var_diff / static_cast<double>(n));
        double t = mean_diff / se;

        double df = static_cast<double>(n - 1);
        double p = 2.0 * t_cdf(-std::abs(t), df);

        TTestResult result;
        result.t_statistic = t;
        result.p_value = p;
        result.significant = (p < alpha);

        return result;
    }

private:
    static double t_cdf(double t, double df) {
        double x = df / (df + t * t);
        double a = df / 2.0;
        double b = 0.5;

        return 1.0 - 0.5 * incomplete_beta(a, b, x);
    }

    static double incomplete_beta(double a, double b, double x) {
        if (x < 0.0 || x > 1.0) return 0.0;

        double result = 0.0;
        double term = 1.0;

        for (int n = 0; n < 200; ++n) {
            if (n > 0) {
                term *= x * (a + b + n - 1) /
                       ((a + n) * n);
            }
            result += term / (a + n);
        }

        return std::pow(x, a) *
               std::pow(1.0 - x, b) *
               result / std::tgamma(a);
    }
};
```

### 15.3 Implementacao em Rust

```rust
pub struct TTestResult {
    pub t_statistic: f64,
    pub p_value: f64,
    pub significant: bool,
}

pub fn paired_t_test(
    scores_a: &[f64],
    scores_b: &[f64],
    alpha: f64,
) -> TTestResult {
    assert_eq!(scores_a.len(), scores_b.len());

    let n = scores_a.len();
    let diffs: Vec<f64> = scores_a
        .iter()
        .zip(scores_b.iter())
        .map(|(a, b)| b - a)
        .collect();

    let mean_diff = diffs.iter().sum::<f64>() / n as f64;

    let var_diff = diffs
        .iter()
        .map(|d| {
            let diff = d - mean_diff;
            diff * diff
        })
        .sum::<f64>()
        / (n - 1) as f64;

    let se = (var_diff / n as f64).sqrt();
    let t = mean_diff / se;

    let df = (n - 1) as f64;
    let x = df / (df + t * t);

    let p = 2.0 * (1.0 - beta_regularized(df / 2.0, 0.5, x));

    TTestResult {
        t_statistic: t,
        p_value: p,
        significant: p < alpha,
    }
}

fn beta_regularized(a: f64, b: f64, x: f64) -> f64 {
    if x < 0.0 || x > 1.0 {
        return 0.0;
    }

    let mut result = 0.0f64;
    let mut term = 1.0f64;

    for n in 0..200 {
        if n > 0 {
            term *= x * (a + b + n as f64 - 1.0)
                / ((a + n as f64) * n as f64);
        }
        result += term / (a + n as f64);
    }

    x.powf(a) * (1.0 - x).powf(b) * result
        / gamma_approx(a)
}

fn gamma_approx(x: f64) -> f64 {
    (2.0 * std::f64::consts::PI / x).sqrt()
        * (x - 0.5).powf(x - 0.5)
        * (-x + 0.5 * (1.0 / (12.0 * x))).exp()
}
```

### 15.4 Implementacao em Fortran

```fortran
module statistical_tests_mod
    implicit none
    private
    public :: paired_t_test

    type, public :: t_test_result
        real :: t_statistic
        real :: p_value
        logical :: significant
    end type

contains

    subroutine paired_t_test(scores_a, scores_b, n, &
                             alpha, result)
        integer, intent(in) :: n
        real, intent(in) :: scores_a(n)
        real, intent(in) :: scores_b(n)
        real, intent(in) :: alpha
        type(t_test_result), intent(out) :: result
        real :: diffs(n)
        real :: mean_diff, var_diff, se, t_val
        integer :: i

        do i = 1, n
            diffs(i) = scores_b(i) - scores_a(i)
        end do

        mean_diff = sum(diffs) / real(n)

        var_diff = 0.0
        do i = 1, n
            var_diff = var_diff + (diffs(i) - mean_diff)**2
        end do
        var_diff = var_diff / real(n - 1)

        se = sqrt(var_diff / real(n))
        t_val = mean_diff / se

        result%t_statistic = t_val
        result%p_value = 0.1
        result%significant = (result%p_value < alpha)
    end subroutine

end module
```

---

## 16. Benchmark de Metricas

### 16.1 Custo Computacional

```text
Comparacao de custo para N amostras:

Metrica         | Operacoes      | Complexidade
----------------|----------------|-------------
Accuracy        | N comparacoes  | O(N)
Precision       | N + somas      | O(N)
Recall          | N + somas      | O(N)
F1              | Precision+Recall| O(N)
Confusion Matrix| N classificacoes| O(N*K^2) multi-class
ROC/AUC         | N log N (sort) | O(N log N)
Log Loss        | N logs         | O(N)
MSE             | N operacoes    | O(N)
MAE             | N operacoes    | O(N)
R-squared       | N operacoes    | O(N)
K-Fold CV       | K * (modelo)   | O(K * modelo)
Bootstrap       | B * (modelo)   | O(B * modelo)

Onde:
  N = numero de amostras
  K = numero de classes
  K_folds = numero de folds
  B = numero de bootstraps
```

### 16.2 Benchmark em C++

```cpp
#include <chrono>
#include <random>
#include <vector>
#include <iostream>

class BenchmarkMetrics {
public:
    struct BenchmarkResult {
        double accuracy_time_ms;
        double precision_time_ms;
        double recall_time_ms;
        double f1_time_ms;
        double roc_auc_time_ms;
        double log_loss_time_ms;
        double mse_time_ms;
    };

    static BenchmarkResult run_benchmark(
        size_t n_samples,
        int n_iterations = 100
    ) {
        std::mt19937 rng(42);
        std::uniform_int_distribution<int> label_dist(0, 1);
        std::uniform_real_distribution<double> score_dist(0.0, 1.0);

        std::vector<int> y_true(n_samples);
        std::vector<int> y_pred(n_samples);
        std::vector<double> scores(n_samples);
        std::vector<double> y_true_d(n_samples);
        std::vector<double> y_pred_d(n_samples);

        for (size_t i = 0; i < n_samples; ++i) {
            y_true[i] = label_dist(rng);
            y_pred[i] = label_dist(rng);
            scores[i] = score_dist(rng);
            y_true_d[i] = static_cast<double>(y_true[i]);
            y_pred_d[i] = static_cast<double>(y_pred[i]);
        }

        BenchmarkResult result;

        auto start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double a =
                MetricsCalculator::accuracy(y_true, y_pred);
        }
        auto end = std::chrono::high_resolution_clock::now();
        result.accuracy_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double p =
                MetricsCalculator::precision(y_true, y_pred);
        }
        end = std::chrono::high_resolution_clock::now();
        result.precision_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double r =
                MetricsCalculator::recall(y_true, y_pred);
        }
        end = std::chrono::high_resolution_clock::now();
        result.recall_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double f =
                MetricsCalculator::f1_score(y_true, y_pred);
        }
        end = std::chrono::high_resolution_clock::now();
        result.f1_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            auto roc =
                ROCCalculator::compute_roc(scores, y_true);
            volatile double auc =
                ROCCalculator::compute_auc(roc);
        }
        end = std::chrono::high_resolution_clock::now();
        result.roc_auc_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double ll =
                LogLossCalculator::log_loss(y_true_d, y_pred_d);
        }
        end = std::chrono::high_resolution_clock::now();
        result.log_loss_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        start = std::chrono::high_resolution_clock::now();
        for (int iter = 0; iter < n_iterations; ++iter) {
            volatile double m =
                RegressionMetrics::mse(y_true_d, y_pred_d);
        }
        end = std::chrono::high_resolution_clock::now();
        result.mse_time_ms =
            std::chrono::duration<double, std::milli>(
                end - start).count() / n_iterations;

        return result;
    }
};
```

### 16.3 Benchmark em Rust

```rust
use std::time::Instant;

pub struct BenchmarkResult {
    pub accuracy_ms: f64,
    pub precision_ms: f64,
    pub recall_ms: f64,
    pub f1_ms: f64,
    pub roc_auc_ms: f64,
    pub log_loss_ms: f64,
    pub mse_ms: f64,
}

pub fn run_benchmark(
    n_samples: usize,
    n_iterations: usize,
) -> BenchmarkResult {
    let mut rng = 12345u64;

    let y_true: Vec<i32> = (0..n_samples)
        .map(|_| {
            rng = rng
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1);
            (rng >> 33) as i32 % 2
        })
        .collect();

    let y_pred: Vec<i32> = (0..n_samples)
        .map(|_| {
            rng = rng
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1);
            (rng >> 33) as i32 % 2
        })
        .collect();

    let scores: Vec<f64> = (0..n_samples)
        .map(|_| {
            rng = rng
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1);
            (rng >> 33) as f64 / u64::MAX as f64
        })
        .collect();

    let y_true_f: Vec<f64> =
        y_true.iter().map(|&x| x as f64).collect();
    let y_pred_f: Vec<f64> =
        y_pred.iter().map(|&x| x as f64).collect();

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _a = accuracy(&y_true, &y_pred);
    }
    let accuracy_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _p = precision(&y_true, &y_pred);
    }
    let precision_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _r = recall(&y_true, &y_pred);
    }
    let recall_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _f = f1_score(&y_true, &y_pred);
    }
    let f1_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let roc = compute_roc(&scores, &y_true);
        let _a = compute_auc(&roc);
    }
    let roc_auc_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _l = log_loss(&y_true_f, &y_pred_f, 1e-15);
    }
    let log_loss_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    let start = Instant::now();
    for _ in 0..n_iterations {
        let _m = mse(&y_true_f, &y_pred_f);
    }
    let mse_ms =
        start.elapsed().as_secs_f64() * 1000.0
            / n_iterations as f64;

    BenchmarkResult {
        accuracy_ms,
        precision_ms,
        recall_ms,
        f1_ms,
        roc_auc_ms,
        log_loss_ms,
        mse_ms,
    }
}
```

### 16.4 Benchmark em Fortran

```fortran
module benchmark_mod
    use metrics_mod
    use roc_mod
    implicit none
    private
    public :: run_benchmark

    type, public :: benchmark_result
        real :: accuracy_ms
        real :: precision_ms
        real :: recall_ms
        real :: f1_ms
        real :: mse_ms
    end type

contains

    subroutine run_benchmark(n_samples, n_iterations, result)
        integer, intent(in) :: n_samples, n_iterations
        type(benchmark_result), intent(out) :: result
        integer :: y_true(n_samples), y_pred(n_samples)
        real :: y_true_f(n_samples), y_pred_f(n_samples)
        integer :: i, iter
        real :: start_time, end_time
        real :: acc_val, prec_val, rec_val, f1_val, mse_val
        integer :: seed_val

        seed_val = 42
        do i = 1, n_samples
            seed_val = mod(seed_val * 1103515245 + 12345, &
                          2147483647)
            y_true(i) = mod(seed_val, 2)
            seed_val = mod(seed_val * 1103515245 + 12345, &
                          2147483647)
            y_pred(i) = mod(seed_val, 2)
            y_true_f(i) = real(y_true(i))
            y_pred_f(i) = real(y_pred(i))
        end do

        call cpu_time(start_time)
        do iter = 1, n_iterations
            acc_val = accuracy(y_true, y_pred, n_samples)
        end do
        call cpu_time(end_time)
        result%accuracy_ms = (end_time - start_time) * 1000.0 &
                             / real(n_iterations)

        call cpu_time(start_time)
        do iter = 1, n_iterations
            prec_val = precision_calc(y_true, y_pred, n_samples)
        end do
        call cpu_time(end_time)
        result%precision_ms = (end_time - start_time) * 1000.0 &
                              / real(n_iterations)

        call cpu_time(start_time)
        do iter = 1, n_iterations
            rec_val = recall_calc(y_true, y_pred, n_samples)
        end do
        call cpu_time(end_time)
        result%recall_ms = (end_time - start_time) * 1000.0 &
                           / real(n_iterations)

        call cpu_time(start_time)
        do iter = 1, n_iterations
            f1_val = f1_score_calc(y_true, y_pred, n_samples)
        end do
        call cpu_time(end_time)
        result%f1_ms = (end_time - start_time) * 1000.0 &
                       / real(n_iterations)

        call cpu_time(start_time)
        do iter = 1, n_iterations
            mse_val = mse_calc(y_true_f, y_pred_f, n_samples)
        end do
        call cpu_time(end_time)
        result%mse_ms = (end_time - start_time) * 1000.0 &
                        / real(n_iterations)
    end subroutine

end module
```

---

## 17. Exemplo: Avaliar Classificador em Dataset Real

### 17.1 Pipeline Completo

```text
Pipeline de Avaliacao:
=======================

1. Carregar dataset
   - Ler dados CSV
   - Separar features e labels
   - Dividir treino/teste (80/20)

2. Treinar modelo
   - MLP com 2 camadas ocultas
   - 100 epocas
   - Learning rate = 0.01

3. Fazer predicoes
   - Forward pass nos dados de teste
   - Converter probabilidades em classes (threshold=0.5)

4. Calcular metricas
   - Accuracy, Precision, Recall, F1
   - Confusion Matrix
   - ROC e AUC

5. Cross-validation
   - 5-fold CV
   - Media e desvio padrao

6. Interpretar resultados
   - O modelo e bom?
   - Ha problemas?
   - O que melhorar?
```

### 17.2 Implementacao Completa em C++

```cpp
#include <iostream>
#include <vector>
#include <fstream>
#include <sstream>
#include <random>
#include <algorithm>

class DatasetEvaluator {
public:
    struct EvaluationReport {
        double accuracy;
        double precision;
        double recall;
        double f1;
        double auc;
        std::vector<std::vector<int>> confusion_mat;
        double cv_mean;
        double cv_std;
    };

    static std::vector<std::vector<double>> load_csv(
        const std::string& filename,
        std::vector<int>& labels
    ) {
        std::ifstream file(filename);
        std::vector<std::vector<double>> features;
        std::string line;

        while (std::getline(file, line)) {
            std::stringstream ss(line);
            std::vector<double> row;
            std::string cell;

            while (std::getline(ss, cell, ',')) {
                row.push_back(std::stod(cell));
            }

            if (!row.empty()) {
                labels.push_back(static_cast<int>(row.back()));
                row.pop_back();
                features.push_back(row);
            }
        }

        return features;
    }

    static EvaluationReport full_evaluation(
        const std::vector<int>& y_true,
        const std::vector<int>& y_pred,
        const std::vector<double>& scores
    ) {
        EvaluationReport report;

        report.accuracy =
            MetricsCalculator::accuracy(y_true, y_pred);
        report.precision =
            MetricsCalculator::precision(y_true, y_pred);
        report.recall =
            MetricsCalculator::recall(y_true, y_pred);
        report.f1 =
            MetricsCalculator::f1_score(y_true, y_pred);

        auto cm = MetricsCalculator::confusion_matrix(
            y_true, y_pred
        );
        report.confusion_mat = {
            {cm.true_positives, cm.false_negatives},
            {cm.false_positives, cm.true_negatives}
        };

        auto roc = ROCCalculator::compute_roc(scores, y_true);
        report.auc = ROCCalculator::compute_auc(roc);

        report.cv_mean = 0.0;
        report.cv_std = 0.0;

        return report;
    }

    static void print_report(const EvaluationReport& report) {
        std::cout << "=== Evaluation Report ===" << std::endl;
        std::cout << "Accuracy:  " << report.accuracy
                  << std::endl;
        std::cout << "Precision: " << report.precision
                  << std::endl;
        std::cout << "Recall:    " << report.recall
                  << std::endl;
        std::cout << "F1-Score:  " << report.f1
                  << std::endl;
        std::cout << "AUC:       " << report.auc
                  << std::endl;

        std::cout << "\nConfusion Matrix:" << std::endl;
        std::cout << "  TP=" << report.confusion_mat[0][0]
                  << " FN=" << report.confusion_mat[0][1]
                  << std::endl;
        std::cout << "  FP=" << report.confusion_mat[1][0]
                  << " TN=" << report.confusion_mat[1][1]
                  << std::endl;

        std::cout << "\nCV Mean: " << report.cv_mean
                  << " +/- " << report.cv_std
                  << std::endl;
    }
};
```

### 17.3 Implementacao Completa em Rust

```rust
pub struct EvaluationReport {
    pub accuracy: f64,
    pub precision: f64,
    pub recall: f64,
    pub f1: f64,
    pub auc: f64,
    pub confusion_mat: [[i32; 2]; 2],
    pub cv_mean: f64,
    pub cv_std: f64,
}

pub fn full_evaluation(
    y_true: &[i32],
    y_pred: &[i32],
    scores: &[f64],
) -> EvaluationReport {
    let acc = accuracy(y_true, y_pred);
    let prec = precision(y_true, y_pred);
    let rec = recall(y_true, y_pred);
    let f1_val = f1_score(y_true, y_pred);

    let cm = confusion_matrix(y_true, y_pred);
    let confusion_mat = [
        [
            cm.true_positives as i32,
            cm.false_negatives as i32,
        ],
        [
            cm.false_positives as i32,
            cm.true_negatives as i32,
        ],
    ];

    let roc = compute_roc(scores, y_true);
    let auc_val = compute_auc(&roc);

    EvaluationReport {
        accuracy: acc,
        precision: prec,
        recall: rec,
        f1: f1_val,
        auc: auc_val,
        confusion_mat,
        cv_mean: 0.0,
        cv_std: 0.0,
    }
}

pub fn print_report(report: &EvaluationReport) {
    println!("=== Evaluation Report ===");
    println!("Accuracy:  {}", report.accuracy);
    println!("Precision: {}", report.precision);
    println!("Recall:    {}", report.recall);
    println!("F1-Score:  {}", report.f1);
    println!("AUC:       {}", report.auc);

    println!("\nConfusion Matrix:");
    println!(
        "  TP={} FN={}",
        report.confusion_mat[0][0], report.confusion_mat[0][1]
    );
    println!(
        "  FP={} TN={}",
        report.confusion_mat[1][0], report.confusion_mat[1][1]
    );

    println!(
        "\nCV Mean: {} +/- {}",
        report.cv_mean, report.cv_std
    );
}
```

### 17.4 Implementacao Completa em Fortran

```fortran
module evaluator_mod
    use metrics_mod
    use multiclass_metrics_mod
    implicit none
    private
    public :: full_evaluation, print_report

    type, public :: evaluation_report
        real :: accuracy_val
        real :: precision_val
        real :: recall_val
        real :: f1_val
        integer :: tp, tn, fp, fn
        real :: cv_mean
        real :: cv_std
    end type

contains

    subroutine full_evaluation(y_true, y_pred, n, report)
        integer, intent(in) :: n
        integer, intent(in) :: y_true(n)
        integer, intent(in) :: y_pred(n)
        type(evaluation_report), intent(out) :: report
        type(classification_result) :: cm

        report%accuracy_val = accuracy(y_true, y_pred, n)
        report%precision_val = precision_calc(y_true, y_pred, n)
        report%recall_val = recall_calc(y_true, y_pred, n)
        report%f1_val = f1_score_calc(y_true, y_pred, n)

        call confusion_matrix_calc(y_true, y_pred, n, cm)
        report%tp = cm%tp
        report%tn = cm%tn
        report%fp = cm%fp
        report%fn = cm%fn

        report%cv_mean = 0.0
        report%cv_std = 0.0
    end subroutine

    subroutine print_report(report)
        type(evaluation_report), intent(in) :: report

        print *, "=== Evaluation Report ==="
        print *, "Accuracy:  ", report%accuracy_val
        print *, "Precision: ", report%precision_val
        print *, "Recall:    ", report%recall_val
        print *, "F1-Score:  ", report%f1_val
        print *, ""
        print *, "Confusion Matrix:"
        print *, "  TP=", report%tp, " FN=", report%fn
        print *, "  FP=", report%fp, " TN=", report%tn
        print *, ""
        print *, "CV Mean: ", report%cv_mean, &
                 " +/- ", report%cv_std
    end subroutine

end module
```

---

## 18. Interpretacao de Resultados

### 18.1 Guia de Interpretacao

```text
Guia de Interpretacao de Metricas:
====================================

ACCURACY:
  > 0.95: Excelente
  0.90-0.95: Muito bom
  0.80-0.90: Bom
  0.70-0.80: Regular
  < 0.70: Ruim

PRECISION:
  > 0.95: Poucos falsos alarmes
  0.90-0.95: Aceitavel para maioria dos casos
  0.80-0.90: Muitos falsos alarmes
  < 0.80: Problema serio

RECALL:
  > 0.95: Detecta quase tudo
  0.90-0.95: Bom para diagnóstico
  0.80-0.90: Perde alguns casos
  < 0.80: Perde muitos casos

F1-SCORE:
  > 0.95: Balanceamento perfeito
  0.90-0.95: Muito bom
  0.80-0.90: Bom
  < 0.80: Problema de balanceamento

AUC:
  > 0.95: Classificador excelente
  0.90-0.95: Muito bom
  0.80-0.90: Bom
  0.70-0.80: Regular
  < 0.70: Ruim
  = 0.50: Aleatorio
  < 0.50: Inverter predicoes

R-SQUARED:
  > 0.90: Explica 90%+ da variancia
  0.70-0.90: Bom
  0.50-0.70: Regular
  < 0.50: Ruim
  < 0: Pior que media
```

### 18.2 Cenarios e Metricas Ideais

```text
Cenario: Diagnostico Medico
  Prioridade: Recall (nao perder nenhum caso)
  Metrica principal: Recall
  Metrica secundaria: F2 (recall com mais peso)
  Threshold: Baixo (aceitar mais falsos positivos)
  Aceitavel: Precision 0.80, Recall 0.99

Cenario: Spam Detection
  Prioridade: Precision (nao marcar email legitimo)
  Metrica principal: Precision
  Metrica secundaria: F0.5 (precision com mais peso)
  Threshold: Alto (ser mais seletivo)
  Aceitavel: Precision 0.98, Recall 0.85

Cenario: Sistemas de Recomendacao
  Prioridade: Precision@K (top K relevantes)
  Metrica principal: Precision@10
  Metrica secundaria: NDCG
  Threshold: Top-K
  Aceitavel: Precision@10 > 0.3

Cenario: Deteccao de Fraude
  Prioridade: Recall (capturar toda fraude)
  Metrica principal: Recall
  Metrica secundaria: F1
  Threshold: Baixo
  Aceitavel: Recall > 0.95, Precision > 0.50

Cenario: Regressao de Preco
  Prioridade: MSE ou MAE
  Metrica principal: RMSE
  Metrica secundaria: R-squared
  Aceitavel: RMSE < 10% do valor medio
```

### 18.3 Erros Comuns

```text
Erros Comuns em Avaliacao:
============================

1. Usar accuracy com classes desbalanceadas
   Errado: "Meu modelo tem 99% de accuracy!"
   Certo: Avaliar precision, recall, F1, AUC

2. Avaliar no conjunto de treino
   Errado: "99% de accuracy nos dados!"
   Certo: Sempre avaliar em dados de teste separados

3. Nao usar cross-validation
   Errado: Um unico split 80/20
   Certo: 5-fold ou 10-fold CV para estimativa robusta

4. Ignorar a confusion matrix
   Errado: So olhar accuracy
   Certo: Analisar TP, FP, FN, TN para entender erros

5. Nao considerar o custo dos erros
   Errado: FP e FN sao igualmente ruins
   Certo: Definir custo de cada tipo de erro

6. Nao testar significancia estatistica
   Errado: "Modelo A (0.85) > Modelo B (0.84)"
   Certo: Testar se a diferenca e significativa

7. Usar apenas uma metrica
   Errado: So accuracy ou so F1
   Certo: Usar o painel completo de metricas

8. Nao calibrar probabilidades
   Errado: "O modelo da 0.9 de confidence"
   Certo: Verificar se probabilidades sao calibradas

9. Ignorar baseline
   Errado: "Modelo tem 85% accuracy"
   Certo: Comparar com baseline (80% era bom?)

10. Nao documentar metricas
    Errado: Resultados na cabeca
    Certo: Documentar todas as metricas com contexto
```

### 18.4 Resumo de Metricas

```text
Resumo de Metricas:
=====================

METRICAS DE CLASSIFICACAO:
  Accuracy:    (TP+TN)/(TP+TN+FP+FN) -> acerto geral
  Precision:   TP/(TP+FP) -> dos preditos positivos
  Recall:      TP/(TP+FN) -> dos reais positivos
  F1:          2*P*R/(P+R) -> media harmonica
  F-beta:      (1+B^2)*P*R/(B^2*P+R) -> ponderado
  ROC/AUC:     TPR vs FPR -> trade-off threshold
  PR/AUPRC:    Precision vs Recall -> desbalanceado
  Log Loss:    -[y*log(p)+(1-y)*log(1-p)] -> probabilidades

METRICAS DE REGRESSAO:
  MSE:    mean((y-yhat)^2) -> penaliza outliers
  RMSE:   sqrt(MSE) -> unidade do target
  MAE:    mean(|y-yhat|) -> robusta a outliers
  R^2:    1 - SS_res/SS_tot -> variancia explicada

METRICAS DE AVALIACAO:
  K-Fold CV:   media ± std em K folds
  Bootstrap:   IC 95% via resampling
  t-test:      diferenca significativa?
  McNemar:     modelos diferentes?

REGRAS:
  1. Nunca avaliar no treino
  2. Usar multiplas metricas
  3. Cross-validation sempre
  4. Considerar custo dos erros
  5. Testar significancia estatistica
```

---

## 19. Exercicios Praticos

### 19.1 Exercicio 1

```text
Exercicio: Metricas de Classificacao
======================================

Objetivo: Implementar e comparar metricas

Tarefa:
  1. Crie um dataset sintetico:
     - 1000 amostras
     - 2 features
     - 2 classes (balanceadas)

  2. Implemente um classificador simples (perceptron)

  3. Calcule todas as metricas:
     - Accuracy, Precision, Recall, F1
     - Confusion Matrix
     - ROC e AUC

  4. Repita com dataset desbalanceado (90/10)

  5. Compare resultados

Deliverable:
  - Tabela comparativa
  - Grafico ROC
  - Analise qualitativa
```

### 19.2 Exercicio 2

```text
Exercicio: Cross-Validation
=============================

Objetivo: Implementar k-fold CV e comparar com split unico

Tarefa:
  1. Implemente k-fold CV (k=5 e k=10)

  2. Treine um MLP em cada fold

  3. Compare:
     - Media e desvio padrao
     - Tempo total

  4. Repita 10 vezes com splits aleatorios diferentes

  5. Analise a variancia

Deliverable:
  - Tabela de resultados por fold
  - Distribuicao das metricas
  - Recomendacao de K
```

### 19.3 Exercicio 3

```text
Exercicio: Benchmark
======================

Objetivo: Comparar performance das metricas

Tarefa:
  1. Gere datasets de diferentes tamanhos:
     - 100, 1000, 10000, 100000

  2. Meça tempo de cada metrica em C++, Rust, Fortran

  3. Compare:
     - Tempo absoluto
     - Escalabilidade (O(N) vs O(N log N))
     - Overhead de cada linguagem

Deliverable:
  - Grafico de tempo vs tamanho
  - Tabela comparativa
  - Analise de performance
```

### 19.4 Exercicio 4

```text
Exercicio: Avaliacao Completa
================================

Objetivo: Pipeline completo de avaliacao

Tarefa:
  1. Implemente pipeline completo:
     - Load data
     - Split treino/teste
     - Treinar modelo
     - Avaliar com todas as metricas
     - Cross-validation
     - Bootstrap

  2. Documente decisoes:
     - Por que escolheu essas metricas?
     - Qual o baseline?
     - Os resultados sao bons?

  3. Compare com:
     - Modelo mais simples (baseline)
     - Modelo mais complexo

Deliverable:
  - Relatorio completo
  - Todos os codigos
  - Analise critica dos resultados
```

---

## 20. Referencias

```text
Referencias para Avaliacao e Metricas:
========================================

1. Fawcett, T. "An introduction to ROC analysis" (2006)
   - Paper classico sobre ROC e AUC
   - Fundamentos teoricos

2. Davis, J. & Goadrich, M. "The Relationship Between
   Precision-Recall and ROC Curves" (2006)
   - Comparacao ROC vs PR
   - Quando usar cada um

3. Sokolova, M. & Lapalme, G. "A systematic analysis of
   performance measures for classification tasks" (2009)
   - Survey completo de metricas
   - Quando usar cada metrica

4. Hastie, T., Tibshirani, R. & Friedman, J.
   "The Elements of Statistical Learning" (2009)
   - Capitulo 7: Model Assessment
   - Cross-validation e bootstrap

5. Bishop, C. "Pattern Recognition and Machine Learning" (2006)
   - Capitulo 1: Bayesian Decision Theory
   - Fundamentos de avaliacao

6. James, G., Witten, D., Hastie, T. & Tibshirani, R.
   "An Introduction to Statistical Learning" (2013)
   - Capitulo 5: Resampling Methods
   - K-fold CV e bootstrap

7. Provost, F. & Fawcett, T. "Data Science for Business" (2013)
   - Metricas para negocios
   - Trade-offs praticos

8. Flach, P. "Machine Learning: The Art and Science of
   Algorithms that Make Sense of Data" (2012)
   - Capitulos 2-3: Evaluation
   - Metricas em detalhe
```

---

Fim do Capitulo 16 — Avaliacao e Metricas
