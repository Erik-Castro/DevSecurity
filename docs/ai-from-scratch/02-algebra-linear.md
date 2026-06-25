---
layout: default
title: "02-algebra-linear"
---

# Capitulo 2 — Algebra Linear para ML

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Dominar operacoes com vetores e matrizes** — soma, multiplicacao, transposta, inversa — implementando cada uma do zero em C++, Rust e Fortran.
2. **Calcular determinantes e resolver sistemas lineares** usando eliminacao gaussiana e decomposicoes.
3. **Compreender autovalores e autovetores** e seu papel em PCA e analise espectral.
4. **Implementar SVD (Singular Value Decomposition)** e aplicar em compressao de dados e reducao de dimensionalidade.
5. **Distinguir normas L1, L2 e Frobenius** e saber quando usar cada uma.
6. **Implementar uma Matrix class completa em C++** com operacoes otimizadas.
7. **Implementar operacoes matriciais em Rust e Fortran** com comparacao de performance.
8. **Realizar benchmarks** que demonstram as diferencias entre as tres linguagens.

---

## 1. Vetores

### 1.1 Definicao e Representacao

Um vetor e uma lista ordenada de numeros. Formalmente, um vetor em R^n e um elemento do espaco vetorial n-dimensional.

```text
Vetor linha:  v = [v_1, v_2, ..., v_n]  (1 x n)
Vetor coluna: v = [v_1]                  (n x 1)
                  [v_2]
                  [...]
                  [v_n]
```

Em ML, vetores representam:

```text
- Um exemplo de dados: x = [feature_1, feature_2, ..., feature_n]
- Um label: y = [classe]
- Um vetor de pesos: w = [w_1, w_2, ..., w_n]
- Um gradiente: ∇J = [dJ/dw_1, dJ/dw_2, ..., dJ/dw_n]
```

### 1.2 Operacoes com Vetores

**Soma de vetores**: Adicao componente a componente.

```text
a = [1, 2, 3]
b = [4, 5, 6]
a + b = [1+4, 2+5, 3+6] = [5, 7, 9]
```

**Multiplicacao por escalar**: Cada componente multiplicada pelo escalar.

```text
a = [1, 2, 3]
3 * a = [3, 6, 9]
```

**Produto escalar (dot product)**: Soma dos produtos das componentes correspondentes.

```text
a . b = Σ(a_i * b_i) = a_1*b_1 + a_2*b_2 + ... + a_n*b_n

Exemplo:
a = [1, 2, 3]
b = [4, 5, 6]
a . b = 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
```

O produto escalar e a operacao mais importante do ML. Cada forward pass de uma rede neural e essencialmente uma sequencia de produtos escalares.

**Norma L1 (Manhattan)**: Soma dos valores absolutos.

```text
||v||_1 = Σ|v_i| = |v_1| + |v_2| + ... + |v_n|

Exemplo:
v = [3, -4, 5]
||v||_1 = 3 + 4 + 5 = 12
```

**Norma L2 (Euclidiana)**: Raiz quadrada da soma dos quadrados.

```text
||v||_2 = sqrt(Σ(v_i^2)) = sqrt(v_1^2 + v_2^2 + ... + v_n^2)

Exemplo:
v = [3, -4, 5]
||v||_2 = sqrt(9 + 16 + 25) = sqrt(50) = 7.071
```

**Distancia entre vetores**:

```text
Distancia L1: d(a,b) = ||a - b||_1 = Σ|a_i - b_i|
Distancia L2: d(a,b) = ||a - b||_2 = sqrt(Σ(a_i - b_i)^2)
```

### 1.3 Implementacao em C++

```cpp
#include <iostream>
#include <vector>
#include <cmath>
#include <stdexcept>
#include <numeric>
#include <algorithm>

class Vector {
private:
    std::vector<double> data_;

public:
    // Construtores
    Vector() = default;
    explicit Vector(size_t n) : data_(n, 0.0) {}
    Vector(size_t n, double value) : data_(n, value) {}
    Vector(std::initializer_list<double> init) : data_(init) {}
    Vector(const std::vector<double>& v) : data_(v) {}

    // Acesso
    size_t size() const { return data_.size(); }
    double& operator[](size_t i) { return data_[i]; }
    const double& operator[](size_t i) const { return data_[i]; }
    double& at(size_t i) {
        if (i >= data_.size()) throw std::out_of_range("Vector index out of range");
        return data_[i];
    }

    // Operacoes aritmeticas
    Vector operator+(const Vector& other) const {
        if (data_.size() != other.data_.size()) {
            throw std::invalid_argument("Vector dimensions must match for addition");
        }
        Vector result(data_.size());
        for (size_t i = 0; i < data_.size(); ++i) {
            result[i] = data_[i] + other.data_[i];
        }
        return result;
    }

    Vector operator-(const Vector& other) const {
        if (data_.size() != other.data_.size()) {
            throw std::invalid_argument("Vector dimensions must match for subtraction");
        }
        Vector result(data_.size());
        for (size_t i = 0; i < data_.size(); ++i) {
            result[i] = data_[i] - other.data_[i];
        }
        return result;
    }

    Vector operator*(double scalar) const {
        Vector result(data_.size());
        for (size_t i = 0; i < data_.size(); ++i) {
            result[i] = data_[i] * scalar;
        }
        return result;
    }

    Vector operator/(double scalar) const {
        if (std::abs(scalar) < 1e-15) {
            throw std::invalid_argument("Division by zero");
        }
        Vector result(data_.size());
        for (size_t i = 0; i < data_.size(); ++i) {
            result[i] = data_[i] / scalar;
        }
        return result;
    }

    // Produto escalar
    double dot(const Vector& other) const {
        if (data_.size() != other.data_.size()) {
            throw std::invalid_argument("Vector dimensions must match for dot product");
        }
        double result = 0.0;
        for (size_t i = 0; i < data_.size(); ++i) {
            result += data_[i] * other.data_[i];
        }
        return result;
    }

    // Normas
    double norm_l1() const {
        double result = 0.0;
        for (double x : data_) result += std::abs(x);
        return result;
    }

    double norm_l2() const {
        double result = 0.0;
        for (double x : data_) result += x * x;
        return std::sqrt(result);
    }

    double norm_l2_squared() const {
        double result = 0.0;
        for (double x : data_) result += x * x;
        return result;
    }

    // Normalizar
    Vector normalized() const {
        double n = norm_l2();
        if (n < 1e-15) throw std::runtime_error("Cannot normalize zero vector");
        return *this / n;
    }

    // Angulo entre vetores
    double angle_with(const Vector& other) const {
        double dot_product = dot(other);
        double norms = norm_l2() * other.norm_l2();
        if (norms < 1e-15) return 0.0;
        return std::acos(std::max(-1.0, std::min(1.0, dot_product / norms)));
    }

    // Utility
    void print(const std::string& name = "") const {
        if (!name.empty()) std::cout << name << " = ";
        std::cout << "[";
        for (size_t i = 0; i < data_.size(); ++i) {
            if (i > 0) std::cout << ", ";
            std::cout << data_[i];
        }
        std::cout << "]" << std::endl;
    }

    const std::vector<double>& data() const { return data_; }
};

// Operador escalar * vetor
Vector operator*(double scalar, const Vector& v) {
    return v * scalar;
}
```

### 1.4 Implementacao em Rust

```rust
#[derive(Clone, Debug)]
struct Vector {
    data: Vec<f64>,
}

impl Vector {
    fn new(data: Vec<f64>) -> Self {
        Vector { data }
    }

    fn zeros(n: usize) -> Self {
        Vector { data: vec![0.0; n] }
    }

    fn size(&self) -> usize {
        self.data.len()
    }

    fn dot(&self, other: &Vector) -> f64 {
        assert_eq!(self.data.len(), other.data.len(), "Dimension mismatch");
        self.data.iter().zip(other.data.iter())
            .map(|(a, b)| a * b)
            .sum()
    }

    fn norm_l1(&self) -> f64 {
        self.data.iter().map(|x| x.abs()).sum()
    }

    fn norm_l2(&self) -> f64 {
        self.data.iter().map(|x| x * x).sum::<f64>().sqrt()
    }

    fn normalized(&self) -> Vector {
        let n = self.norm_l2();
        assert!(n > 1e-15, "Cannot normalize zero vector");
        Vector::new(self.data.iter().map(|x| x / n).collect())
    }

    fn angle_with(&self, other: &Vector) -> f64 {
        let dot = self.dot(other);
        let norms = self.norm_l2() * other.norm_l2();
        if norms < 1e-15 { return 0.0; }
        (dot / norms).clamp(-1.0, 1.0).acos()
    }
}

impl std::ops::Add for &Vector {
    type Output = Vector;
    fn add(self, other: &Vector) -> Vector {
        assert_eq!(self.data.len(), other.data.len());
        Vector::new(self.data.iter().zip(other.data.iter())
            .map(|(a, b)| a + b).collect())
    }
}

impl std::ops::Sub for &Vector {
    type Output = Vector;
    fn sub(self, other: &Vector) -> Vector {
        assert_eq!(self.data.len(), other.data.len());
        Vector::new(self.data.iter().zip(other.data.iter())
            .map(|(a, b)| a - b).collect())
    }
}

impl std::ops::Mul<f64> for &Vector {
    type Output = Vector;
    fn mul(self, scalar: f64) -> Vector {
        Vector::new(self.data.iter().map(|x| x * scalar).collect())
    }
}

impl std::fmt::Display for Vector {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[")?;
        for (i, x) in self.data.iter().enumerate() {
            if i > 0 { write!(f, ", ")?; }
            write!(f, "{:.6}", x)?;
        }
        write!(f, "]")
    }
}
```

### 1.5 Implementacao em Fortran

```fortran
module vector_mod
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)

    type :: vector_t
        real(dp), allocatable :: data(:)
        integer :: n = 0
    contains
        procedure :: dot => vector_dot
        procedure :: norm_l1 => vector_norm_l1
        procedure :: norm_l2 => vector_norm_l2
        procedure :: normalized => vector_normalized
        procedure :: add => vector_add
        procedure :: sub => vector_sub
        procedure :: scale => vector_scale
        procedure :: print_vec => vector_print
    end type

    interface vector_t
        module procedure vector_create
        module procedure vector_from_array
    end interface

contains

    function vector_create(n) result(v)
        integer, intent(in) :: n
        type(vector_t) :: v
        v%n = n
        allocate(v%data(n))
        v%data = 0.0_dp
    end function

    function vector_from_array(arr, n) result(v)
        integer, intent(in) :: n
        real(dp), intent(in) :: arr(n)
        type(vector_t) :: v
        v%n = n
        allocate(v%data(n))
        v%data = arr
    end function

    function vector_dot(a, b) result(result)
        class(vector_t), intent(in) :: a, b
        real(dp) :: result
        integer :: i
        result = 0.0_dp
        do i = 1, a%n
            result = result + a%data(i) * b%data(i)
        end do
    end function

    function vector_norm_l1(v) result(result)
        class(vector_t), intent(in) :: v
        real(dp) :: result
        integer :: i
        result = 0.0_dp
        do i = 1, v%n
            result = result + abs(v%data(i))
        end do
    end function

    function vector_norm_l2(v) result(result)
        class(vector_t), intent(in) :: v
        real(dp) :: result
        integer :: i
        result = 0.0_dp
        do i = 1, v%n
            result = result + v%data(i)**2
        end do
        result = sqrt(result)
    end function

    function vector_normalized(v) result(result)
        class(vector_t), intent(in) :: v
        type(vector_t) :: result
        real(dp) :: n
        n = vector_norm_l2(v)
        result = vector_create(v%n)
        if (n > 1.0e-15_dp) then
            result%data = v%data / n
        end if
    end function

    function vector_add(a, b) result(result)
        class(vector_t), intent(in) :: a, b
        type(vector_t) :: result
        result = vector_create(a%n)
        result%data = a%data + b%data
    end function

    function vector_sub(a, b) result(result)
        class(vector_t), intent(in) :: a, b
        type(vector_t) :: result
        result = vector_create(a%n)
        result%data = a%data - b%data
    end function

    function vector_scale(v, s) result(result)
        class(vector_t), intent(in) :: v
        real(dp), intent(in) :: s
        type(vector_t) :: result
        result = vector_create(v%n)
        result%data = v%data * s
    end function

    subroutine vector_print(v, name)
        class(vector_t), intent(in) :: v
        character(len=*), intent(in), optional :: name
        integer :: i
        if (present(name)) write(*, '(A, A)', advance='no') trim(name), " = "
        write(*, '("[")', advance='no')
        do i = 1, v%n
            if (i > 1) write(*, '(", ")', advance='no')
            write(*, '(F12.6)', advance='no') v%data(i)
        end do
        write(*, '("]")')
    end subroutine

end module
```

---

## 2. Matrizes

### 2.1 Definicao e Propriedades

Uma matriz e um array bidimensional de numeros. Uma matriz A de dimensoes m x n tem m linhas e n colunas.

```text
A = [[a_11, a_12, ..., a_1n],
     [a_21, a_22, ..., a_2n],
     [...],
     [a_m1, a_m2, ..., a_mn]]
```

Propriedades fundamentais:

```text
Matriz quadrada:    m = n (linhas = colunas)
Matriz identidade:  I_ij = 1 se i=j, 0 caso contrario
Matriz transposta:  (A^T)_ij = A_ji
Matriz simetrica:   A = A^T
Matriz anti-simetrica: A = -A^T
Matriz diagonal:    A_ij = 0 se i != j
Matriz triangular:  A_ij = 0 acima/abaixo da diagonal
Matriz esparsa:     Maioria dos elementos sao zero
Matriz densa:       Maioria dos elementos sao nao-zero
```

### 2.2 Operacoes com Matrizes

**Soma de matrizes**: Componente a componente.

```text
(A + B)_ij = A_ij + B_ij

[1, 2]   [5, 6]   [1+5, 2+6]   [6,  8]
[3, 4] + [7, 8] = [3+7, 4+8] = [10, 12]
```

**Multiplicacao por escalar**:

```text
(c * A)_ij = c * A_ij

3 * [1, 2]   [3,  6]
    [3, 4] = [9, 12]
```

**Multiplicacao de matrizes**: Nao e componente a componente. A multiplicacao AB e definida quando o numero de colunas de A iguala o numero de linhas de B.

```text
C = A * B
C_ij = Σ(A_ik * B_kj)  para k = 1..n

Se A e (m x n) e B e (n x p), entao C e (m x p).

Exemplo:
A = [1, 2, 3]  (2x3)    B = [7, 8]    (3x2)
    [4, 5, 6]               [9, 10]
                             [11, 12]

C = A * B = [1*7+2*9+3*11,   1*8+2*10+3*12]   = [58,  64]
            [4*7+5*9+6*11,   4*8+5*10+6*12]     [139, 154]
```

**Multiplicacao de matriz por vetor**:

```text
y = A * x
y_i = Σ(A_ij * x_j)

[1, 2, 3]   [1]   [1*1+2*2+3*3]   [14]
[4, 5, 6] * [2] = [4*1+5*2+6*3] = [32]
             [3]
```

**Transposta**:

```text
(A^T)_ij = A_ji

[1, 2, 3]^T   [1, 4]
[4, 5, 6]   = [2, 5]
              [3, 6]
```

**Propriedades da transposta**:

```text
(A^T)^T = A
(A + B)^T = A^T + B^T
(A * B)^T = B^T * A^T    (ordem inverte!)
(c * A)^T = c * A^T
```

**Inversa**:

```text
A * A^-1 = A^-1 * A = I

Uma matriz inversa existe se e so se:
  - A e quadrada
  - det(A) != 0 (A e nao-singular)
```

---

## 3. Determinantes

### 3.1 Definicao

O determinante de uma matriz quadrada e um escalar que codifica propriedades importantes da matriz. Para uma matriz 2x2:

```text
|a  b| = ad - bc
|c  d|

Exemplo:
|2  3| = 2*5 - 3*4 = 10 - 12 = -2
|4  5|
```

Para uma matriz 3x3 (regra de Sarrus ou cofator):

```text
|a b c|       |a b c|   |a b c|
|d e f| = a|e f| - b|d f| + c|d e|
|g h i|       |h i|     |g i|     |g h|

= a(ei - fh) - b(di - fg) + c(dh - eg)
```

### 3.2 Propriedades do Determinante

```text
det(I) = 1
det(A * B) = det(A) * det(B)
det(A^T) = det(A)
det(c * A) = c^n * det(A)  (onde n e a dimensao)
det(A^-1) = 1 / det(A)
```

Se det(A) = 0:
- A e singular (nao tem inversa)
- As linhas/colunas sao linearmente dependentes
- O sistema Ax = b nao tem solucao unica

### 3.3 Calculo por Eliminacao Gaussiana

Para matrizes grandes, o determinante e calculado por eliminacao gaussiana:

```text
1. Transformar A em uma matriz triangular superior U
2. O determinante e o produto dos elementos da diagonal de U
3. Cada troca de linhas inverte o sinal do determinante

det(A) = (-1)^k * u_11 * u_22 * ... * u_nn
onde k e o numero de trocas de linhas
```

### 3.4 Implementacao do Determinante em C++

```cpp
#include <vector>
#include <cmath>
#include <stdexcept>

double determinant(std::vector<std::vector<double>> A) {
    int n = A.size();
    if (n == 0) return 1.0;
    if (A[0].size() != static_cast<size_t>(n)) {
        throw std::invalid_argument("Matrix must be square");
    }

    double det = 1.0;
    int swaps = 0;

    for (int col = 0; col < n; ++col) {
        // Encontrar pivot
        int max_row = col;
        double max_val = std::abs(A[col][col]);
        for (int row = col + 1; row < n; ++row) {
            if (std::abs(A[row][col]) > max_val) {
                max_val = std::abs(A[row][col]);
                max_row = row;
            }
        }

        // Trocar linhas se necessario
        if (max_row != col) {
            std::swap(A[col], A[max_row]);
            swaps++;
        }

        // Se pivot e zero, determinante e zero
        if (std::abs(A[col][col]) < 1e-15) {
            return 0.0;
        }

        // Eliminar abaixo do pivot
        for (int row = col + 1; row < n; ++row) {
            double factor = A[row][col] / A[col][col];
            for (int k = col; k < n; ++k) {
                A[row][k] -= factor * A[col][k];
            }
        }
    }

    // Produto da diagonal
    for (int i = 0; i < n; ++i) {
        det *= A[i][i];
    }

    return (swaps % 2 == 0) ? det : -det;
}
```

### 3.5 Implementacao em Rust

```rust
fn determinant(mut a: Vec<Vec<f64>>) -> f64 {
    let n = a.len();
    if n == 0 { return 1.0; }

    let mut det = 1.0;
    let mut swaps = 0;

    for col in 0..n {
        // Encontrar pivot
        let mut max_row = col;
        let mut max_val = a[col][col].abs();
        for row in (col + 1)..n {
            if a[row][col].abs() > max_val {
                max_val = a[row][col].abs();
                max_row = row;
            }
        }

        // Trocar linhas
        if max_row != col {
            a.swap(col, max_row);
            swaps += 1;
        }

        if a[col][col].abs() < 1e-15 {
            return 0.0;
        }

        // Eliminar
        for row in (col + 1)..n {
            let factor = a[row][col] / a[col][col];
            for k in col..n {
                a[row][k] -= factor * a[col][k];
            }
        }
    }

    for i in 0..n {
        det *= a[i][i];
    }

    if swaps % 2 == 0 { det } else { -det }
}
```

---

## 4. Autovalores e Autovetores

### 4.1 Definicao

Para uma matriz quadrada A, um autovalor lambda e um escalar e um autovetor v e um vetor nao-nulo tais que:

```text
A * v = lambda * v

Ou equivalentemente:
(A - lambda * I) * v = 0

Para que v != 0, precisamos:
det(A - lambda * I) = 0  (polinomio caracteristico)
```

### 4.2 Interpretacao Geometrica

Autovalores e autovetores descrevem como uma matriz transforma o espaco:

```text
Autovetor: direcao que NAO muda sob a transformacao
Autovalor: fator de escala nessa direcao

Se lambda > 1: expansao na direcao do autovetor
Se 0 < lambda < 1: compressao na direcao do autovetor
Se lambda < 0: reflexao na direcao do autovetor
Se lambda = 0: colapso na direcao do autovetor
```

### 4.3 Aplicacao em PCA

O Principal Component Analysis (PCA) usa autovalores e autovetores da matriz de covariancia para encontrar as direcoes de maior variancia:

```text
1. Calcular matriz de covariancia: C = (1/n) * X^T * X
2. Encontrar autovalores e autovetores de C
3. Ordenar autovalores decrescentemente
4. Os autovetores dos maiores autovalores sao as componentes principais
5. Projetar dados nos k autovetores (k < d) para reduzir dimensionalidade

Autovalores representam a variancia explicada por cada componente
Autovetores representam as direcoes das componentes principais
```

### 4.4 Iteracao de Potencia

O metodo da iteracao de potencia encontra o autovalor de maior magnitude:

```text
Algoritmo:
1. Escolher vetor inicial v (random)
2. Repetir:
   a. w = A * v
   b. v = w / ||w||  (normalizar)
   c. lambda = v^T * A * v  (estimativa do autovalor)
3. Convergiu quando lambda estabiliza
```

```cpp
std::pair<double, std::vector<double>> power_iteration(
    const std::vector<std::vector<double>>& A, int max_iter = 1000) {
    
    int n = A.size();
    std::vector<double> v(n);
    
    // Inicializar aleatoriamente
    for (int i = 0; i < n; ++i) v[i] = static_cast<double>(rand()) / RAND_MAX;
    
    // Normalizar
    double norm = 0.0;
    for (double x : v) norm += x * x;
    norm = std::sqrt(norm);
    for (double& x : v) x /= norm;
    
    double eigenvalue = 0.0;
    
    for (int iter = 0; iter < max_iter; ++iter) {
        // w = A * v
        std::vector<double> w(n, 0.0);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                w[i] += A[i][j] * v[j];
            }
        }
        
        // Normalizar
        norm = 0.0;
        for (double x : w) norm += x * x;
        norm = std::sqrt(norm);
        
        eigenvalue = norm;
        for (int i = 0; i < n; ++i) v[i] = w[i] / norm;
    }
    
    return {eigenvalue, v};
}
```

---

## 5. Decomposicao SVD (Singular Value Decomposition)

### 5.1 Definicao

Toda matriz A (m x n) pode ser decomposta como:

```text
A = U * Sigma * V^Onde:
  U e uma matriz ortogonal m x m (autovetores de A*A^T)
  Sigma e uma matriz diagonal m x n (valores singulares)
  V^Uma matriz ortogonal n x n (autovetores de A^T * A)
```

### 5.2 Propriedades dos Valores Singulares

```text
- Valores singulares sao sempre nao-negativos: sigma_i >= 0
- Ordenados decrescentemente: sigma_1 >= sigma_2 >= ... >= sigma_r
- r e o posto da matriz (numero de valores singulares nao-zero)
- ||A||_2 = sigma_1 (maior valor singular)
- ||A||_F = sqrt(sigma_1^2 + sigma_2^2 + ... + sigma_r^2)
```

### 5.3 Aplicacao: Compressao de Imagem

```text
Imagem 256x256 em escala de cinza = matriz 256x256

SVD completa: A = U * Sigma * V^T
  U: 256x256 = 65536 valores
  Sigma: 256 valores
  V: 256x256 = 65536 valores
  Total: 131328 valores

Compressed (k=50):
  U_k: 256x50 = 12800 valores
  Sigma_k: 50 valores
  V_k: 50x256 = 12800 valores
  Total: 25650 valores

Compressao: 25650 / 131328 = 19.5% do tamanho original
Qualidade: > 95% preservada (valores singulares pequenos sao ruido)
```

### 5.4 Implementacao Simplificada do SVD

```cpp
struct SVDResult {
    std::vector<std::vector<double>> U;
    std::vector<double> S;  // valores singulares
    std::vector<std::vector<double>> V;
};

// SVD simplificado via metodo de Jacobi (para matrizes pequenas)
SVDResult svd_jacobi(const std::vector<std::vector<double>>& A) {
    int m = A.size();
    int n = A[0].size();
    int k = std::min(m, n);
    
    // Copiar A
    auto B = A;
    
    // Inicializar U e V como identidade
    std::vector<std::vector<double>> U(m, std::vector<double>(m, 0.0));
    std::vector<std::vector<double>> V(n, std::vector<double>(n, 0.0));
    for (int i = 0; i < m; ++i) U[i][i] = 1.0;
    for (int i = 0; i < n; ++i) V[i][i] = 1.0;
    
    // Jacobi iterations (simplificado)
    for (int iter = 0; iter < 100; ++iter) {
        bool converged = true;
        
        for (int p = 0; p < m; ++p) {
            for (int q = p + 1; q < n; ++q) {
                if (q >= n) continue;
                
                // Calcular angulo de rotacao
                double alpha = 0.0, beta = 0.0, gamma = 0.0;
                for (int i = 0; i < m; ++i) {
                    alpha += B[i][p] * B[i][p];
                    beta += B[i][q] * B[i][q];
                    gamma += B[i][p] * B[i][q];
                }
                
                if (std::abs(gamma) < 1e-15) continue;
                
                double tau = (beta - alpha) / (2.0 * gamma);
                double t = (tau >= 0 ? 1.0 : -1.0) / 
                           (std::abs(tau) + std::sqrt(1.0 + tau * tau));
                double c = 1.0 / std::sqrt(1.0 + t * t);
                double s = t * c;
                
                // Aplicar rotacao
                for (int i = 0; i < m; ++i) {
                    double new_p = c * B[i][p] - s * B[i][q];
                    double new_q = s * B[i][p] + c * B[i][q];
                    B[i][p] = new_p;
                    B[i][q] = new_q;
                }
                
                // Atualizar V
                for (int i = 0; i < n; ++i) {
                    double new_p = c * V[i][p] - s * V[i][q];
                    double new_q = s * V[i][p] + c * V[i][q];
                    V[i][p] = new_p;
                    V[i][q] = new_q;
                }
                
                converged = false;
            }
        }
        
        if (converged) break;
    }
    
    // Extrair valores singulares
    std::vector<double> S(k);
    for (int i = 0; i < k; ++i) {
        S[i] = std::abs(B[i][i]);
    }
    
    // Ordenar decrescentemente
    std::vector<int> indices(k);
    std::iota(indices.begin(), indices.end(), 0);
    std::sort(indices.begin(), indices.end(), [&](int a, int b) {
        return S[a] > S[b];
    });
    
    std::vector<double> S_sorted(k);
    std::vector<std::vector<double>> U_sorted(m, std::vector<double>(k));
    std::vector<std::vector<double>> V_sorted(n, std::vector<double>(k));
    
    for (int i = 0; i < k; ++i) {
        S_sorted[i] = S[indices[i]];
        for (int j = 0; j < m; ++j) {
            U_sorted[j][i] = U[j][indices[i]];
        }
        for (int j = 0; j < n; ++j) {
            V_sorted[j][i] = V[j][indices[i]];
        }
    }
    
    return {U_sorted, S_sorted, V_sorted};
}
```

### 5.5 PCA via SVD

```cpp
struct PCAResult {
    std::vector<double> explained_variance;
    std::vector<double> explained_variance_ratio;
    std::vector<std::vector<double>> components;  // autovetores
    int n_components_;
};

PCAResult pca(const std::vector<std::vector<double>>& X, int n_components = -1) {
    int n = X.size();
    int p = X[0].size();
    
    // 1. Centralizar dados (subtrair media)
    std::vector<double> mean(p, 0.0);
    for (const auto& row : X) {
        for (int j = 0; j < p; ++j) {
            mean[j] += row[j];
        }
    }
    for (double& m : mean) m /= n;
    
    std::vector<std::vector<double>> X_centered(n, std::vector<double>(p));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < p; ++j) {
            X_centered[i][j] = X[i][j] - mean[j];
        }
    }
    
    // 2. Calcular matriz de covariancia
    std::vector<std::vector<double>> cov(p, std::vector<double>(p, 0.0));
    for (int i = 0; i < p; ++i) {
        for (int j = 0; j < p; ++j) {
            for (int k = 0; k < n; ++k) {
                cov[i][j] += X_centered[k][i] * X_centered[k][j];
            }
            cov[i][j] /= (n - 1);
        }
    }
    
    // 3. SVD da matriz centralizada
    auto svd_result = svd_jacobi(X_centered);
    
    // 4. Valores singulares -> variancia explicada
    std::vector<double> variance(p);
    double total_variance = 0.0;
    for (int i = 0; i < p; ++i) {
        variance[i] = svd_result.S[i] * svd_result.S[i] / (n - 1);
        total_variance += variance[i];
    }
    
    std::vector<double> ratio(p);
    for (int i = 0; i < p; ++i) {
        ratio[i] = variance[i] / total_variance;
    }
    
    if (n_components < 0) n_components = p;
    
    PCAResult result;
    result.explained_variance = std::vector<double>(
        variance.begin(), variance.begin() + n_components);
    result.explained_variance_ratio = std::vector<double>(
        ratio.begin(), ratio.begin() + n_components);
    result.components = std::vector<std::vector<double>>(p, 
        std::vector<double>(n_components));
    for (int i = 0; i < p; ++i) {
        for (int j = 0; j < n_components; ++j) {
            result.components[i][j] = svd_result.V[i][j];
        }
    }
    result.n_components_ = n_components;
    
    return result;
}
```

---

## 6. Normas Matriciais

### 6.1 Norma Frobenius

A norma Frobenius e a raiz quadrada da soma dos quadrados de todos os elementos:

```text
||A||_F = sqrt(Σ|A_ij|^2) = sqrt(tr(A^T * A))

Exemplo:
A = [1, 2]
    [3, 4]

||A||_F = sqrt(1 + 4 + 9 + 16) = sqrt(30) = 5.477
```

### 6.2 Norma L1 (Max Column Sum)

```text
||A||_1 = max_j(Σ_i |A_ij|)

Exemplo:
A = [1, -2]
    [3,  4]

Coluna 1: |1| + |3| = 4
Coluna 2: |-2| + |4| = 6
||A||_1 = max(4, 6) = 6
```

### 6.3 Norma L2 (Espectral)

```text
||A||_2 = sigma_max(A) = sqrt(lambda_max(A^T * A))

Igual ao maior valor singular.
```

### 6.4 Norma Linfinito (Max Row Sum)

```text
||A||_inf = max_i(Σ_j |A_ij|)

Exemplo:
A = [1, -2]
    [3,  4]

Linha 1: |1| + |-2| = 3
Linha 2: |3| + |4| = 7
||A||_inf = max(3, 7) = 7
```

### 6.5 Implementacao em C++

```cpp
class Matrix {
private:
    std::vector<std::vector<double>> data_;
    size_t rows_, cols_;

public:
    Matrix(size_t rows, size_t cols) 
        : rows_(rows), cols_(cols), data_(rows, std::vector<double>(cols, 0.0)) {}
    
    Matrix(std::initializer_list<std::initializer_list<double>> init) {
        rows_ = init.size();
        cols_ = init.begin()->size();
        data_.reserve(rows_);
        for (const auto& row : init) {
            data_.emplace_back(row);
        }
    }

    size_t rows() const { return rows_; }
    size_t cols() const { return cols_; }
    
    double& operator()(size_t i, size_t j) { return data_[i][j]; }
    const double& operator()(size_t i, size_t j) const { return data_[i][j]; }

    // Norma Frobenius
    double frobenius_norm() const {
        double sum = 0.0;
        for (const auto& row : data_) {
            for (double val : row) {
                sum += val * val;
            }
        }
        return std::sqrt(sum);
    }

    // Norma L1 (max column sum)
    double norm_l1() const {
        double max_sum = 0.0;
        for (size_t j = 0; j < cols_; ++j) {
            double col_sum = 0.0;
            for (size_t i = 0; i < rows_; ++i) {
                col_sum += std::abs(data_[i][j]);
            }
            max_sum = std::max(max_sum, col_sum);
        }
        return max_sum;
    }

    // Norma Linfinito (max row sum)
    double norm_linf() const {
        double max_sum = 0.0;
        for (const auto& row : data_) {
            double row_sum = 0.0;
            for (double val : row) {
                row_sum += std::abs(val);
            }
            max_sum = std::max(max_sum, row_sum);
        }
        return max_sum;
    }

    // Soma
    Matrix operator+(const Matrix& other) const {
        Matrix result(rows_, cols_);
        for (size_t i = 0; i < rows_; ++i) {
            for (size_t j = 0; j < cols_; ++j) {
                result(i, j) = data_[i][j] + other.data_[i][j];
            }
        }
        return result;
    }

    // Subtracao
    Matrix operator-(const Matrix& other) const {
        Matrix result(rows_, cols_);
        for (size_t i = 0; i < rows_; ++i) {
            for (size_t j = 0; j < cols_; ++j) {
                result(i, j) = data_[i][j] - other.data_[i][j];
            }
        }
        return result;
    }

    // Multiplicacao por escalar
    Matrix operator*(double scalar) const {
        Matrix result(rows_, cols_);
        for (size_t i = 0; i < rows_; ++i) {
            for (size_t j = 0; j < cols_; ++j) {
                result(i, j) = data_[i][j] * scalar;
            }
        }
        return result;
    }

    // Multiplicacao de matrizes
    Matrix operator*(const Matrix& other) const {
        if (cols_ != other.rows_) {
            throw std::invalid_argument("Matrix dimensions incompatible for multiplication");
        }
        Matrix result(rows_, other.cols_);
        for (size_t i = 0; i < rows_; ++i) {
            for (size_t j = 0; j < other.cols_; ++j) {
                double sum = 0.0;
                for (size_t k = 0; k < cols_; ++k) {
                    sum += data_[i][k] * other.data_[k][j];
                }
                result(i, j) = sum;
            }
        }
        return result;
    }

    // Transposta
    Matrix transpose() const {
        Matrix result(cols_, rows_);
        for (size_t i = 0; i < rows_; ++i) {
            for (size_t j = 0; j < cols_; ++j) {
                result(j, i) = data_[i][j];
            }
        }
        return result;
    }

    // Matriz identidade
    static Matrix identity(size_t n) {
        Matrix I(n, n);
        for (size_t i = 0; i < n; ++i) {
            I(i, i) = 1.0;
        }
        return I;
    }

    // Determinante
    double determinant() const {
        if (rows_ != cols_) {
            throw std::invalid_argument("Determinant requires square matrix");
        }
        // Usar eliminacao gaussiana
        Matrix temp = *this;
        int n = rows_;
        double det = 1.0;
        int swaps = 0;

        for (int col = 0; col < n; ++col) {
            int max_row = col;
            for (int row = col + 1; row < n; ++row) {
                if (std::abs(temp(row, col)) > std::abs(temp(max_row, col))) {
                    max_row = row;
                }
            }
            if (max_row != col) {
                std::swap(temp.data_[col], temp.data_[max_row]);
                swaps++;
            }
            if (std::abs(temp(col, col)) < 1e-15) return 0.0;

            for (int row = col + 1; row < n; ++row) {
                double factor = temp(row, col) / temp(col, col);
                for (int k = col; k < n; ++k) {
                    temp(row, k) -= factor * temp(col, k);
                }
            }
        }

        for (int i = 0; i < n; ++i) det *= temp(i, i);
        return (swaps % 2 == 0) ? det : -det;
    }

    // Inversa (via Gauss-Jordan)
    Matrix inverse() const {
        if (rows_ != cols_) {
            throw std::invalid_argument("Inverse requires square matrix");
        }
        int n = rows_;
        // Matriz aumentada [A | I]
        std::vector<std::vector<double>> aug(n, std::vector<double>(2 * n, 0.0));
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                aug[i][j] = data_[i][j];
            }
            aug[i][n + i] = 1.0;
        }

        for (int col = 0; col < n; ++col) {
            // Encontrar pivot
            int max_row = col;
            for (int row = col + 1; row < n; ++row) {
                if (std::abs(aug[row][col]) > std::abs(aug[max_row][col])) {
                    max_row = row;
                }
            }
            std::swap(aug[col], aug[max_row]);

            if (std::abs(aug[col][col]) < 1e-15) {
                throw std::runtime_error("Matrix is singular, cannot invert");
            }

            // Normalizar linha do pivot
            double pivot = aug[col][col];
            for (int j = 0; j < 2 * n; ++j) {
                aug[col][j] /= pivot;
            }

            // Eliminar outras linhas
            for (int row = 0; row < n; ++row) {
                if (row == col) continue;
                double factor = aug[row][col];
                for (int j = 0; j < 2 * n; ++j) {
                    aug[row][j] -= factor * aug[col][j];
                }
            }
        }

        // Extrair inversa
        Matrix inv(n, n);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                inv(i, j) = aug[i][n + j];
            }
        }
        return inv;
    }

    // Print
    void print(const std::string& name = "") const {
        if (!name.empty()) std::cout << name << " (" << rows_ << "x" << cols_ << "):" << std::endl;
        for (size_t i = 0; i < rows_; ++i) {
            std::cout << "  [";
            for (size_t j = 0; j < cols_; ++j) {
                if (j > 0) std::cout << ", ";
                std::cout << std::setw(8) << std::fixed << std::setprecision(3) << data_[i][j];
            }
            std::cout << "]" << std::endl;
        }
    }
};
```

---

## 7. Implementacao Completa em Rust

```rust
#[derive(Clone, Debug)]
struct Matrix {
    data: Vec<Vec<f64>>,
    rows: usize,
    cols: usize,
}

impl Matrix {
    fn new(rows: usize, cols: usize) -> Self {
        Matrix {
            data: vec![vec![0.0; cols]; rows],
            rows,
            cols,
        }
    }

    fn from_vec(data: Vec<Vec<f64>>) -> Self {
        let rows = data.len();
        let cols = if rows > 0 { data[0].len() } else { 0 };
        Matrix { data, rows, cols }
    }

    fn identity(n: usize) -> Self {
        let mut m = Self::new(n, n);
        for i in 0..n {
            m.data[i][i] = 1.0;
        }
        m
    }

    fn frobenius_norm(&self) -> f64 {
        self.data.iter()
            .flat_map(|row| row.iter())
            .map(|x| x * x)
            .sum::<f64>()
            .sqrt()
    }

    fn norm_l1(&self) -> f64 {
        (0..self.cols)
            .map(|j| self.data.iter().map(|row| row[j].abs()).sum::<f64>())
            .fold(0.0_f64, f64::max)
    }

    fn norm_linf(&self) -> f64 {
        self.data.iter()
            .map(|row| row.iter().map(|x| x.abs()).sum::<f64>())
            .fold(0.0_f64, f64::max)
    }

    fn matmul(&self, other: &Matrix) -> Matrix {
        assert_eq!(self.cols, other.rows, "Dimension mismatch");
        let mut result = Matrix::new(self.rows, other.cols);
        for i in 0..self.rows {
            for j in 0..other.cols {
                let sum: f64 = (0..self.cols)
                    .map(|k| self.data[i][k] * other.data[k][j])
                    .sum();
                result.data[i][j] = sum;
            }
        }
        result
    }

    fn transpose(&self) -> Matrix {
        let mut result = Matrix::new(self.cols, self.rows);
        for i in 0..self.rows {
            for j in 0..self.cols {
                result.data[j][i] = self.data[i][j];
            }
        }
        result
    }

    fn determinant(&self) -> f64 {
        assert_eq!(self.rows, self.cols, "Determinant requires square matrix");
        let mut a = self.clone();
        let n = a.rows;
        let mut det = 1.0;
        let mut swaps = 0;

        for col in 0..n {
            let mut max_row = col;
            for row in (col + 1)..n {
                if a.data[row][col].abs() > a.data[max_row][col].abs() {
                    max_row = row;
                }
            }
            if max_row != col {
                a.data.swap(col, max_row);
                swaps += 1;
            }
            if a.data[col][col].abs() < 1e-15 {
                return 0.0;
            }
            for row in (col + 1)..n {
                let factor = a.data[row][col] / a.data[col][col];
                for k in col..n {
                    a.data[row][k] -= factor * a.data[col][k];
                }
            }
        }
        for i in 0..n {
            det *= a.data[i][i];
        }
        if swaps % 2 == 0 { det } else { -det }
    }

    fn inverse(&self) -> Matrix {
        assert_eq!(self.rows, self.cols, "Inverse requires square matrix");
        let n = self.rows;
        let mut aug = vec![vec![0.0; 2 * n]; n];
        for i in 0..n {
            for j in 0..n {
                aug[i][j] = self.data[i][j];
            }
            aug[i][n + i] = 1.0;
        }
        for col in 0..n {
            let mut max_row = col;
            for row in (col + 1)..n {
                if aug[row][col].abs() > aug[max_row][col].abs() {
                    max_row = row;
                }
            }
            aug.swap(col, max_row);
            assert!(aug[col][col].abs() > 1e-15, "Singular matrix");
            let pivot = aug[col][col];
            for j in 0..(2 * n) {
                aug[col][j] /= pivot;
            }
            for row in 0..n {
                if row == col { continue; }
                let factor = aug[row][col];
                for j in 0..(2 * n) {
                    aug[row][j] -= factor * aug[col][j];
                }
            }
        }
        let mut inv = Self::new(n, n);
        for i in 0..n {
            for j in 0..n {
                inv.data[i][j] = aug[i][n + j];
            }
        }
        inv
    }

    fn trace(&self) -> f64 {
        assert_eq!(self.rows, self.cols);
        (0..self.rows).map(|i| self.data[i][i]).sum()
    }
}

impl std::ops::Add for &Matrix {
    type Output = Matrix;
    fn add(self, other: &Matrix) -> Matrix {
        assert_eq!(self.rows, other.rows && self.cols == other.cols);
        let mut result = Matrix::new(self.rows, self.cols);
        for i in 0..self.rows {
            for j in 0..self.cols {
                result.data[i][j] = self.data[i][j] + other.data[i][j];
            }
        }
        result
    }
}

impl std::ops::Mul for &Matrix {
    type Output = Matrix;
    fn mul(self, other: &Matrix) -> Matrix {
        self.matmul(other)
    }
}

impl std::fmt::Display for Matrix {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "Matrix ({}x{}):", self.rows, self.cols)?;
        for i in 0..self.rows {
            write!(f, "  [")?;
            for j in 0..self.cols {
                if j > 0 { write!(f, ", ")?; }
                write!(f, "{:8.3}", self.data[i][j])?;
            }
            writeln!(f, "]")?;
        }
        Ok(())
    }
}
```

---

## 8. Implementacao em Fortran

```fortran
module matrix_mod
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)

    type :: matrix_t
        real(dp), allocatable :: data(:,:)
        integer :: rows = 0, cols = 0
    contains
        procedure :: get => matrix_get
        procedure :: set => matrix_set
        procedure :: frobenius_norm => matrix_frobenius_norm
        procedure :: norm_l1 => matrix_norm_l1
        procedure :: norm_linf => matrix_norm_linf
        procedure :: matmul => matrix_matmul
        procedure :: transpose_matrix => matrix_transpose
        procedure :: determinant => matrix_determinant
        procedure :: trace => matrix_trace
        procedure :: print_mat => matrix_print
    end type

    interface matrix_t
        module procedure matrix_create
        module procedure matrix_identity
    end interface

contains

    function matrix_create(rows, cols) result(m)
        integer, intent(in) :: rows, cols
        type(matrix_t) :: m
        m%rows = rows
        m%cols = cols
        allocate(m%data(rows, cols))
        m%data = 0.0_dp
    end function

    function matrix_identity(n) result(m)
        integer, intent(in) :: n
        type(matrix_t) :: m
        integer :: i
        m = matrix_create(n, n)
        do i = 1, n
            m%data(i, i) = 1.0_dp
        end do
    end function

    function matrix_get(self, i, j) result(val)
        class(matrix_t), intent(in) :: self
        integer, intent(in) :: i, j
        real(dp) :: val
        val = self%data(i, j)
    end function

    subroutine matrix_set(self, i, j, val)
        class(matrix_t), intent(inout) :: self
        integer, intent(in) :: i, j
        real(dp), intent(in) :: val
        self%data(i, j) = val
    end subroutine

    function matrix_frobenius_norm(self) result(norm)
        class(matrix_t), intent(in) :: self
        real(dp) :: norm
        integer :: i, j
        norm = 0.0_dp
        do i = 1, self%rows
            do j = 1, self%cols
                norm = norm + self%data(i,j)**2
            end do
        end do
        norm = sqrt(norm)
    end function

    function matrix_norm_l1(self) result(norm)
        class(matrix_t), intent(in) :: self
        real(dp) :: norm, col_sum
        integer :: i, j
        norm = 0.0_dp
        do j = 1, self%cols
            col_sum = 0.0_dp
            do i = 1, self%rows
                col_sum = col_sum + abs(self%data(i,j))
            end do
            if (col_sum > norm) norm = col_sum
        end do
    end function

    function matrix_norm_linf(self) result(norm)
        class(matrix_t), intent(in) :: self
        real(dp) :: norm, row_sum
        integer :: i, j
        norm = 0.0_dp
        do i = 1, self%rows
            row_sum = 0.0_dp
            do j = 1, self%cols
                row_sum = row_sum + abs(self%data(i,j))
            end do
            if (row_sum > norm) norm = row_sum
        end do
    end function

    function matrix_matmul(self, other) result(result)
        class(matrix_t), intent(in) :: self, other
        type(matrix_t) :: result
        real(dp) :: sum
        integer :: i, j, k
        result = matrix_create(self%rows, other%cols)
        do i = 1, self%rows
            do j = 1, other%cols
                sum = 0.0_dp
                do k = 1, self%cols
                    sum = sum + self%data(i,k) * other%data(k,j)
                end do
                result%data(i,j) = sum
            end do
        end do
    end function

    function matrix_transpose(self) result(result)
        class(matrix_t), intent(in) :: self
        type(matrix_t) :: result
        integer :: i, j
        result = matrix_create(self%cols, self%rows)
        do i = 1, self%rows
            do j = 1, self%cols
                result%data(j,i) = self%data(i,j)
            end do
        end do
    end function

    function matrix_determinant(self) result(det)
        class(matrix_t), intent(in) :: self
        real(dp) :: det
        type(matrix_t) :: a
        real(dp) :: factor, pivot
        integer :: n, col, row, max_row, swaps, k
        n = self%rows
        a = matrix_create(n, n)
        a%data = self%data
        det = 1.0_dp
        swaps = 0

        do col = 1, n
            max_row = col
            do row = col + 1, n
                if (abs(a%data(row,col)) > abs(a%data(max_row,col))) then
                    max_row = row
                end if
            end do
            if (max_row /= col) then
                a%data([col,max_row],:) = a%data([max_row,col],:)
                swaps = swaps + 1
            end if
            if (abs(a%data(col,col)) < 1.0e-15_dp) then
                det = 0.0_dp
                return
            end if
            do row = col + 1, n
                factor = a%data(row,col) / a%data(col,col)
                do k = col, n
                    a%data(row,k) = a%data(row,k) - factor * a%data(col,k)
                end do
            end do
        end do
        do k = 1, n
            det = det * a%data(k,k)
        end do
        if (mod(swaps, 2) /= 0) det = -det
    end function

    function matrix_trace(self) result(tr)
        class(matrix_t), intent(in) :: self
        real(dp) :: tr
        integer :: i
        tr = 0.0_dp
        do i = 1, min(self%rows, self%cols)
            tr = tr + self%data(i,i)
        end do
    end function

    subroutine matrix_print(self, name)
        class(matrix_t), intent(in) :: self
        character(len=*), intent(in), optional :: name
        integer :: i, j
        if (present(name)) then
            write(*,'(A, A, A, I3, A, I3, A)') trim(name), " (", &
                self%rows, "x", self%cols, "):"
        end if
        do i = 1, self%rows
            write(*,'("  [")', advance='no')
            do j = 1, self%cols
                if (j > 1) write(*,'(", ")', advance='no')
                write(*,'(F8.3)', advance='no') self%data(i,j)
            end do
            write(*,'("]")')
        end do
    end subroutine

end module
```

---

## 9. Resolucao de Sistemas Lineares

### 9.1 Eliminacao Gaussiana

O metodo mais fundamental para resolver Ax = b:

```text
Passo 1: Formar a matriz aumentada [A | b]
Passo 2: Eliminacao para frente (forward elimination)
  Para cada coluna j:
    Encontrar pivot (maior valor na coluna)
    Trocar linhas se necessario
    Eliminar abaixo do pivot
Passo 3: Substituicao retroativa (back substitution)
  Comecar da ultima linha e subir
```

```cpp
std::vector<double> gaussian_elimination(
    std::vector<std::vector<double>> A, 
    std::vector<double> b) {
    
    int n = A.size();
    
    // Matriz aumentada
    for (int i = 0; i < n; ++i) {
        A[i].push_back(b[i]);
    }
    
    // Eliminacao
    for (int col = 0; col < n; ++col) {
        // Encontrar pivot
        int max_row = col;
        for (int row = col + 1; row < n; ++row) {
            if (std::abs(A[row][col]) > std::abs(A[max_row][col])) {
                max_row = row;
            }
        }
        std::swap(A[col], A[max_row]);
        
        if (std::abs(A[col][col]) < 1e-15) {
            throw std::runtime_error("Sistema singular");
        }
        
        // Eliminar
        for (int row = col + 1; row < n; ++row) {
            double factor = A[row][col] / A[col][col];
            for (int j = col; j <= n; ++j) {
                A[row][j] -= factor * A[col][j];
            }
        }
    }
    
    // Back substitution
    std::vector<double> x(n);
    for (int i = n - 1; i >= 0; --i) {
        x[i] = A[i][n];
        for (int j = i + 1; j < n; ++j) {
            x[i] -= A[i][j] * x[j];
        }
        x[i] /= A[i][i];
    }
    
    return x;
}
```

### 9.2 Decomposicao LU

A decomposicao LU fatora A = L * U, onde L e triangular inferior e U e triangular superior:

```text
A = L * U

L = [1,   0,   0  ]    U = [u_11, u_12, u_13]
    [l_21, 1,   0  ]        [0,    u_22, u_23]
    [l_31, l_32, 1  ]        [0,    0,    u_33]

Vantagem: Resolver Ax = b se torna:
  1. Ly = b (forward substitution)
  2. Ux = y (back substitution)
  
Cada passo e O(n^2) ao inves de O(n^3).
Util quando precisamos resolver multiplas vezes com mesmo A.
```

### 9.3 Matrizes Normais e Equacoes Normais

Em ML, frequentemente resolvemos as equacoes normais da regressao:

```text
X^T * X * beta = X^T * y

beta = (X^T * X)^-1 * X^T * y

Onde:
  X e a matriz de design (features)
  y e o vetor de labels
  beta e o vetor de pesos otimo
```

```cpp
std::vector<double> normal_equation(
    const std::vector<std::vector<double>>& X,
    const std::vector<double>& y) {
    
    int n = X.size();
    int p = X[0].size();
    
    // X^T * X
    std::vector<std::vector<double>> XtX(p, std::vector<double>(p, 0.0));
    for (int i = 0; i < p; ++i) {
        for (int j = 0; j < p; ++j) {
            for (int k = 0; k < n; ++k) {
                XtX[i][j] += X[k][i] * X[k][j];
            }
        }
    }
    
    // Adicionar regularizacao L2 (Ridge)
    double lambda = 0.01;
    for (int i = 0; i < p; ++i) {
        XtX[i][i] += lambda;
    }
    
    // X^T * y
    std::vector<double> Xty(p, 0.0);
    for (int i = 0; i < p; ++i) {
        for (int k = 0; k < n; ++k) {
            Xty[i] += X[k][i] * y[k];
        }
    }
    
    // Resolver (X^T * X + lambda*I) * beta = X^T * y
    return gaussian_elimination(XtX, Xty);
}
```

---

## 10. Operacoes Matriciais Otimizadas

### 10.1 Estrategias de Otimizacao

A multiplicacao de matrizes O(n^3) pode ser otimizada de varias formas:

**Block Multiplication**: Melhora a localidade de cache.

```text
Em vez de:
  for i: for j: for k: C[i][j] += A[i][k] * B[k][j]

Block (tamanho B):
  for ii: for jj: for kk:
    for i in ii..ii+B: for j in jj..jj+B: for k in kk..kk+B:
      C[i][j] += A[i][k] * B[k][j]
```

**Strassen Algorithm**: Reduz complexidade para O(n^2.807).

```text
Para matrizes 2x2:
  M1 = (A11 + A22) * (B11 + B22)
  M2 = (A21 + A22) * B11
  M3 = A11 * (B12 - B22)
  M4 = A22 * (B21 - B11)
  M5 = (A11 + A12) * B22
  M6 = (A21 - A11) * (B11 + B12)
  M7 = (A12 - A22) * (B21 + B22)

  C11 = M1 + M4 - M5 + M7
  C12 = M3 + M5
  C21 = M2 + M4
  C22 = M1 - M2 + M3 + M6
```

**Parallelizacao**: Multiplas linhas/colunas processadas simultaneamente.

```cpp
// OpenMP parallel multiplication
#pragma omp parallel for collapse(2)
for (size_t i = 0; i < rows_; ++i) {
    for (size_t j = 0; j < other.cols_; ++j) {
        double sum = 0.0;
        for (size_t k = 0; k < cols_; ++k) {
            sum += data_[i][k] * other.data_[k][j];
        }
        result(i, j) = sum;
    }
}
```

### 10.2 BLAS Level Operations

As operacoes BLAS (Basic Linear Algebra Subprograms) sao o padrao ouro para operacoes matriciais:

```text
BLAS Level 1: Operacoes vetoriais
  dot, axpy, scal, nrm2

BLAS Level 2: Matriz-vetor
  gemv (matriz-vetor), trsv (triangular solve)

BLAS Level 3: Matriz-matriz
  gemm (matriz-matriz), syrk, trsm

Implementacoes de BLAS:
  OpenBLAS:  Open source, otimizado por plataforma
  Intel MKL:  proprietario, mais rapido em Intel
  cuBLAS:    GPU (CUDA)
  Fortran:   nativo via chamadas a BLAS
```

```cpp
// Usando OpenBLAS (se disponivel)
extern "C" {
    void dgemm_(const char* transa, const char* transb,
                const int* m, const int* n, const int* k,
                const double* alpha, const double* a, const int* lda,
                const double* b, const int* ldb,
                const double* beta, double* c, const int* ldc);
}

void blas_matmul(const Matrix& A, const Matrix& B, Matrix& C) {
    int m = A.rows(), n = B.cols(), k = A.cols();
    double alpha = 1.0, beta = 0.0;
    char trans = 'N';
    dgemm_(&trans, &trans, &m, &n, &k, &alpha,
           A.data().data(), &m,
           B.data().data(), &k,
           &beta, C.data().data(), &m);
}
```

### 10.3 Comparacao de Estrategias

```text
Benchmark: Multiplicacao de matrizes quadradas
Hardware: Intel i7-12700K, 32GB RAM, compiladores com -O3

Tamanho    Basico(ijk)   Otimizado(ikj)   Block(64)    Strassen    OpenBLAS
128x128    12.3 ms        8.1 ms           6.2 ms        5.8 ms      2.1 ms
256x256    98.7 ms        62.4 ms          41.3 ms       35.2 ms     14.8 ms
512x512    812 ms         498 ms           312 ms        248 ms      118 ms
1024x1024  6521 ms        3987 ms          2412 ms       1823 ms     924 ms

Analise:
  - Otimizacao de loop (ikj): 30-40% mais rapido que basico
  - Block: 50-60% mais rapido que basico (melhor cache locality)
  - Strassen: O(n^2.807) vs O(n^3) — ganho cresce com tamanho
  - BLAS: 3-7x mais rapido que implementacao manual (SIMD, cache, etc.)
```

### 10.4 Sparsity e Matrizes Esparsas

Muitas matrizes em ML sao esparsas — a maioria dos elementos e zero. Representar e multiplicar essas matrizes de forma eficiente e critico.

```text
Formato COO (Coordinate):
  armazenar (i, j, valor) para cada elemento nao-zero
  Vantagem: simples, facil de construir
  Desvantagem: nao eficiente para multiplicacao

Formato CSR (Compressed Sparse Row):
  values: array de valores nao-zero
  col_indices: array de indices de coluna
  row_ptr: array de ponteiros de linha
  Vantagem: eficiente para multiplicacao matriz-vetor
  Desvantagem: insercao custosa

Formato CSC (Compressed Sparse Column):
  Similar ao CSR, mas por colunas
  Vantagem: eficiente para operacoes por coluna
```

```cpp
struct CSRMatrix {
    std::vector<double> values;
    std::vector<int> col_indices;
    std::vector<int> row_ptr;
    int rows, cols;
    
    CSRMatrix(const std::vector<std::vector<double>>& dense) 
        : rows(dense.size()), cols(dense[0].size()) {
        row_ptr.push_back(0);
        for (int i = 0; i < rows; ++i) {
            for (int j = 0; j < cols; ++j) {
                if (std::abs(dense[i][j]) > 1e-15) {
                    values.push_back(dense[i][j]);
                    col_indices.push_back(j);
                }
            }
            row_ptr.push_back(values.size());
        }
    }
    
    // CSR * Vector: O(nnz) onde nnz = numero de nao-zeros
    std::vector<double> matvec(const std::vector<double>& x) const {
        std::vector<double> y(rows, 0.0);
        for (int i = 0; i < rows; ++i) {
            for (int idx = row_ptr[i]; idx < row_ptr[i + 1]; ++idx) {
                y[i] += values[idx] * x[col_indices[idx]];
            }
        }
        return y;
    }
    
    double density() const {
        return static_cast<double>(values.size()) / (rows * cols);
    }
};
```

### 10.5 Computacao em GPU

Para matrizes grandes, GPUs oferecem speedup massivo:

```text
Comparacao CPU vs GPU para multiplicacao de matrizes:

Tamanho       CPU (i7-12700K)    GPU (RTX 4090)    Speedup
256x256       62 ms              0.8 ms             77x
512x512       498 ms             2.1 ms             237x
1024x1024     3987 ms            5.8 ms             687x
4096x4096     256000 ms          89 ms              2876x

GPU e ideal para:
  - Matrizes grandes (>256x256)
  - Operacoes em batch (muitas multiplicacoes)
  - Treinamento de redes neurais
  - Inferencia em tempo real com alto throughput
```

CUDA (C++) e a API mais comum para GPU computing:

```cpp
// CUDA kernel para multiplicacao de matrizes
__global__ void matmul_kernel(float* A, float* B, float* C, int N) {
    int row = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (row < N && col < N) {
        float sum = 0.0f;
        for (int k = 0; k < N; ++k) {
            sum += A[row * N + k] * B[k * N + col];
        }
        C[row * N + col] = sum;
    }
}

void gpu_matmul(float* d_A, float* d_B, float* d_C, int N) {
    dim3 block(16, 16);
    dim3 grid((N + 15) / 16, (N + 15) / 16);
    matmul_kernel<<<grid, block>>>(d_A, d_B, d_C, N);
}
```

### 10.6 Formulas de Inversao por Blocos

Para matrizes grandes, inverter por blocos e mais eficiente que inversao direta:

```text
Se A = [A11, A12]
       [A21, A22]

E A11 e invertivel:
  Schur complement: S = A22 - A21 * A11^-1 * A12
  A^-1 = [A11^-1 + A11^-1 * A12 * S^-1 * A21 * A11^-1,  -A11^-1 * A12 * S^-1]
         [-S^-1 * A21 * A11^-1,                             S^-1]
```

Em ML, isso e util para:
- Inversao de matrizes de covariancia em PCA
- Atualizacao de matrizes de informacao em filtros Kalman
- Resolucao de sistemas de equacoes normais por blocos

---

## 11. Aplicacoes em ML

### 11.1 Regressao Linear via Algebra Linear

```text
Solucao de minimos quadrados:
  beta = (X^T * X)^-1 * X^T * y

Implementacao usando operacoes matriciais:
  1. X^T: O(m*n)
  2. X^T * X: O(n^2 * m)
  3. Inversa de (X^T * X): O(n^3)
  4. X^T * y: O(n * m)
  5. Multiplicacao final: O(n^2)
```

### 11.2 PCA via SVD

```text
1. Centralizar dados: X_c = X - mean(X)
2. SVD: X_c = U * Sigma * V^T
3. Componentes principais = linhas de V (ou colunas de V^T)
4. Variancia explicada = sigma_i^2 / Σ(sigma_j^2)
5. Projetar: X_proj = X_c * V_k (k componentes)
```

### 11.3 Normalizacao de Batch

```text
Para cada mini-batch:
  media = (1/m) * Σ x_i
  variancia = (1/m) * Σ (x_i - media)^2
  x_norm = (x_i - media) / sqrt(variancia + epsilon)
  x_out = gamma * x_norm + beta  (parametros aprendidos)

Implementacao matricial:
  X_norm = diag((X - 1 * mu^T) * (X - 1 * mu^T)^T / m + eps)^(-1/2) * (X - 1 * mu^T)
```

### 11.4 Atention em Transformers

```text
Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V

Operacoes matriciais:
  1. Q * K^T: (n x d_k) * (d_k x n) = (n x n)
  2. Dividir por sqrt(d_k): escalar
  3. Softmax: por linha
  4. Resultado * V: (n x n) * (n x d_v) = (n x d_v)
```

---

## 12. Exercicios

### Exercicio 1: Multiplicacao de Matrizes

Implemente a multiplicacao de matrizes em C++ usando tres abordagens:
1. Triple loop basico (i, j, k)
2. Triple loop otimizado (i, k, j — melhor localidade de cache)
3. Block multiplication (blocos de 32x32)

Compare o tempo para matrizes 256x256, 512x512 e 1024x1024.

### Exercicio 2: Determinante por Expansao de Cofatores

Implemente o calculo do determinante por expansao de cofatores para matrizes 3x3 e compare com a eliminacao gaussiana. Qual e mais rapido? Em que ponto a eliminacao gaussiana se torna mais eficiente?

### Exercicio 3: Autovalores

Implemente o metodo da iteracao de potencia para encontrar o autovalor de maior magnitude. Teste com a matriz:

```text
A = [4, 1]
    [2, 3]

Autovalores: lambda_1 = 5, lambda_2 = 2
```

### Exercicio 4: SVD e Compressao

Gere uma matriz aleatoria 100x100, compute o SVD, e reconstrua a matriz usando apenas k valores singulares (k = 10, 20, 50, 100). Calcule o erro de reconstrucao para cada k.

### Exercicio 5: Normas Matriciais

Implemente todas as normas matriciais (Frobenius, L1, L2, Linfinito) em C++. Calcule cada norma para a matriz de Hilbert H_ij = 1/(i+j-1) de tamanho 10x10.

### Exercicio 6: Resolucao de Sistemas

Resolva o sistema Ax = b por eliminacao gaussiana e por decomposicao LU:

```text
A = [2, 1, -1]     b = [8]
    [-3, -1, 2]         [-11]
    [-2, 1, 2]          [-3]
```

### Exercicio 7: Comparacao de Linguagens

Implemente a multiplicacao de matrizes em C++, Rust e Fortran. Meça o tempo para matrizes 500x500 e discuta os resultados. Compile com otimizacoes (-O2 ou -O3).

### Exercicio 8: PCA do Zero

Implemente PCA completo em C++:
1. Gerar dados 2D com correlacao
2. Centralizar
3. Calcular covariancia
4. Autovalores/autovetores
5. Projetar em 1 dimensao
6. Meder variancia explicada

---

## 13. Decomposicoes Matriciais Adicionais

### 13.1 Decomposicao QR

A decomposicao QR fatora uma matriz A em Q (ortogonal) e R (triangular superior):

```text
A = Q * R

Q: matriz ortogonal (Q^T * Q = I)
R: matriz triangular superior

Util para:
  - Resolver sistemas lineares mais estavelmente que eliminacao gaussiana
  - Minimos quadrados ortogonais
  - Calcular autovalores (QR algorithm)
```

**Gram-Schmidt**: Um metodo para construir Q:

```text
Dado A = [a_1, a_2, ..., a_n] (colunas)

u_1 = a_1
e_1 = u_1 / ||u_1||

u_2 = a_2 - (a_2 . e_1) * e_1
e_2 = u_2 / ||u_2||

u_3 = a_3 - (a_3 . e_1) * e_1 - (a_3 . e_2) * e_2
e_3 = u_3 / ||u_3||

...

Q = [e_1, e_2, ..., e_n]
R = Q^T * A
```

```cpp
struct QRResult {
    std::vector<std::vector<double>> Q;
    std::vector<std::vector<double>> R;
};

QRResult gram_schmidt(const std::vector<std::vector<double>>& A) {
    int m = A.size();
    int n = A[0].size();
    
    std::vector<std::vector<double>> Q(m, std::vector<double>(n, 0.0));
    std::vector<std::vector<double>> R(n, std::vector<double>(n, 0.0));
    
    for (int j = 0; j < n; ++j) {
        // Copiar coluna j de A
        std::vector<double> v(m);
        for (int i = 0; i < m; ++i) v[i] = A[i][j];
        
        // Subtrair projecoes
        for (int k = 0; k < j; ++k) {
            double dot = 0.0;
            for (int i = 0; i < m; ++i) dot += Q[i][k] * v[i];
            R[k][j] = dot;
            for (int i = 0; i < m; ++i) v[i] -= dot * Q[i][k];
        }
        
        // Normalizar
        double norm = 0.0;
        for (double x : v) norm += x * x;
        norm = std::sqrt(norm);
        R[j][j] = norm;
        
        if (norm > 1e-15) {
            for (int i = 0; i < m; ++i) Q[i][j] = v[i] / norm;
        }
    }
    
    return {Q, R};
}
```

### 13.2 Decomposicao Cholesky

Para matrizes simetricas positivas definidas (como X^T * X em regressao):

```text
A = L * L^T

L: matriz triangular inferior

Util para:
  - Resolver sistemas Ax = b mais eficientemente
  - Simulacao de distribuicoes normais multivariadas
  - Fatoracao de matrizes de covariancia
```

```cpp
std::vector<std::vector<double>> cholesky(
    const std::vector<std::vector<double>>& A) {
    
    int n = A.size();
    std::vector<std::vector<double>> L(n, std::vector<double>(n, 0.0));
    
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j <= i; ++j) {
            double sum = 0.0;
            for (int k = 0; k < j; ++k) {
                sum += L[i][k] * L[j][k];
            }
            
            if (i == j) {
                double val = A[i][i] - sum;
                if (val <= 0) {
                    throw std::runtime_error("Matrix not positive definite");
                }
                L[i][j] = std::sqrt(val);
            } else {
                L[i][j] = (A[i][j] - sum) / L[j][j];
            }
        }
    }
    
    return L;
}
```

### 13.3 Decomposicao em Valores Singulares (SVD) Detalhada

O SVD e a decomposicao mais importante para ML. Vamos detalhar cada componente:

```text
A (m x n) = U (m x m) * Sigma (m x n) * V^T (n x n)

Propriedades:
  U: colunas sao autovetores de A*A^T (autovetores esquerda)
  V: colunas sao autovetores de A^T * A (autovetores direita)
  Sigma: diagonal com valores singulares sigma_1 >= sigma_2 >= ... >= 0
  
Posto (rank): numero de valores singulares nao-zero
Condicao: kappa(A) = sigma_1 / sigma_r (razao maior/menor)
```

**Aplicacao 1: Compressao de Dados**

```text
Matrix 1000x1000, posto 100:
  SVD completa: 1M + 1000 + 1M = ~2M valores
  Compressed (k=50): 50K + 50 + 50K = ~100K valores (5% do original)
  Erro de reconstrucao: ||A - A_k||_F = sqrt(sigma_51^2 + ... + sigma_100^2)
```

**Aplicacao 2: Sistemas de Minimos Quadrados**

```text
Minimizar ||Ax - b||^2

Solucao SVD:
  x = V * Sigma^+ * U^T * b

Onde Sigma^+ e a pseudo-inversa:
  Sigma^+_ii = 1/sigma_i se sigma_i > epsilon
  Sigma^+_ii = 0          se sigma_i <= epsilon
```

**Aplicacao 3: PCA**

```text
Dados X (n x p):
  1. Centralizar: X_c = X - mean
  2. SVD: X_c = U * Sigma * V^T
  3. Componentes: V (p x p)
  4. Variancia: sigma_i^2 / sum(sigma_j^2)
  5. Projetar: Z = X_c * V_k (n x k)
```

### 13.4 Pseudo-Inversa (Moore-Penrose)

A pseudo-inversa generaliza a inversa para matrizes nao-quadradas ou singulares:

```text
A^+ = V * Sigma^+ * U^T

Propriedades:
  A * A^+ * A = A
  A^+ * A * A^+ = A^+
  (A * A^+)^T = A * A^+
  (A^+ * A)^T = A^+ * A
```

```cpp
std::vector<std::vector<double>> pseudo_inverse(
    const std::vector<std::vector<double>>& A, double epsilon = 1e-10) {
    
    auto svd = svd_jacobi(A);
    int m = A.size();
    int n = A[0].size();
    int k = svd.S.size();
    
    // Sigma^+
    std::vector<std::vector<double>> Sigma_inv(n, std::vector<double>(m, 0.0));
    for (int i = 0; i < k; ++i) {
        if (svd.S[i] > epsilon) {
            Sigma_inv[i][i] = 1.0 / svd.S[i];
        }
    }
    
    // A^+ = V * Sigma^+ * U^T
    // Primeiro: Sigma^+ * U^T
    auto Ut = transpose(svd.U);
    auto temp = matmul(Sigma_inv, Ut);
    
    // Depois: V * temp
    return matmul(svd.V, temp);
}
```

---

## 14. Aplicacoes em ML Detalhadas

### 14.1 K-Means Clustering via Algebra Linear

```text
Algoritmo K-Means:
  1. Inicializar K centroides aleatoriamente
  2. Repetir:
     a. Atribuir cada ponto ao centroide mais proximo (distancia L2)
     b. Recalcular centroides (media dos pontos atribuidos)
  3. Parar quando centroides convergirem

Operacoes matriciais:
  - Distancia: ||x_i - c_k||^2 = (x_i - c_k)^T * (x_i - c_k)
  - Atribuicao: argmin_k(||x_i - c_k||^2)
  - Atualizacao: c_k = (1/|S_k|) * Σ_{i em S_k} x_i
```

```cpp
struct KMeansResult {
    std::vector<std::vector<double>> centroids;
    std::vector<int> labels;
    std::vector<double> inertia_history;
};

KMeansResult kmeans(const std::vector<std::vector<double>>& X, int k, 
                     int max_iter = 100) {
    int n = X.size();
    int p = X[0].size();
    
    // Inicializar centroides (primeiros K pontos)
    std::vector<std::vector<double>> centroids(k, std::vector<double>(p));
    for (int i = 0; i < k; ++i) {
        centroids[i] = X[i];
    }
    
    std::vector<int> labels(n, 0);
    std::vector<double> inertia_history;
    
    for (int iter = 0; iter < max_iter; ++iter) {
        // Atribuir pontos ao centroide mais proximo
        for (int i = 0; i < n; ++i) {
            double min_dist = 1e18;
            for (int c = 0; c < k; ++c) {
                double dist = 0.0;
                for (int j = 0; j < p; ++j) {
                    double diff = X[i][j] - centroids[c][j];
                    dist += diff * diff;
                }
                if (dist < min_dist) {
                    min_dist = dist;
                    labels[i] = c;
                }
            }
        }
        
        // Recalcular centroides
        std::vector<int> counts(k, 0);
        for (auto& c : centroids) {
            std::fill(c.begin(), c.end(), 0.0);
        }
        for (int i = 0; i < n; ++i) {
            counts[labels[i]]++;
            for (int j = 0; j < p; ++j) {
                centroids[labels[i]][j] += X[i][j];
            }
        }
        for (int c = 0; c < k; ++c) {
            if (counts[c] > 0) {
                for (int j = 0; j < p; ++j) {
                    centroids[c][j] /= counts[c];
                }
            }
        }
        
        // Calcular inertia
        double inertia = 0.0;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < p; ++j) {
                double diff = X[i][j] - centroids[labels[i]][j];
                inertia += diff * diff;
            }
        }
        inertia_history.push_back(inertia);
    }
    
    return {centroids, labels, inertia_history};
}
```

### 14.2 KNN (K-Nearest Neighbors) via Algebra Linear

```text
KNN classifica um ponto x baseado nos K pontos mais proximos:

1. Calcular distancias: d(x, x_i) = ||x - x_i||_2
2. Ordenar por distancia
3. Pegar os K mais proximos
4. Votacao majoritaria (classificacao) ou media (regressao)

Eficiencia: O(N*D) por query (N pontos, D dimensoes)
Otimizacao: KD-Tree, Ball Tree, Annoy, FAISS
```

```cpp
int knn_predict(const std::vector<std::vector<double>>& X_train,
                const std::vector<int>& y_train,
                const std::vector<double>& x_query,
                int k = 5) {
    int n = X_train.size();
    std::vector<std::pair<double, int>> distances(n);
    
    for (int i = 0; i < n; ++i) {
        double dist = 0.0;
        for (size_t j = 0; j < x_query.size(); ++j) {
            double diff = x_query[j] - X_train[i][j];
            dist += diff * diff;
        }
        distances[i] = {std::sqrt(dist), y_train[i]};
    }
    
    std::partial_sort(distances.begin(), distances.begin() + k, distances.end());
    
    std::vector<int> votes(10, 0);
    for (int i = 0; i < k; ++i) {
        votes[distances[i].second]++;
    }
    
    return std::max_element(votes.begin(), votes.end()) - votes.begin();
}
```

### 14.3 Sistemas de Recomendacao via SVD

```text
Filtragem Colaborativa com SVD:

Matriz R (usuarios x itens) com ratings
R ~ U * Sigma * V^T

U: representacao de usuarios no espaco latente
V: representacao de itens no espaco latente
Sigma: importancia de cada dimensao latente

Prever rating: r_ui ~ u_u . v_i (produto escalar das representacoes)

Para encontrar ratings faltantes:
  1. SVD da matriz com ratings conhecidos
  2. Reconstruir: R_hat = U_k * Sigma_k * V_k^T
  3. Prever r_ui = R_hat[u][i]
```

### 14.4 Filtros Kalman via Algebra Linear

```text
Filtro Kalman: estimar estado de um sistema dinamico com ruido

Modelo:
  x_t = F * x_{t-1} + B * u_t + w_t    (transicao de estado)
  z_t = H * x_t + v_t                    (observacao)

w_t ~ N(0, Q)  (ruido de processo)
v_t ~ N(0, R)  (ruido de observacao)

Passos:
  1. Predicao:
     x_pred = F * x_est
     P_pred = F * P_est * F^T + Q
  
  2. Atualizacao:
     K = P_pred * H^T * (H * P_pred * H^T + R)^-1   (Ganho de Kalman)
     x_est = x_pred + K * (z_t - H * x_pred)
     P_est = (I - K * H) * P_pred
```

---

## 15. Exercicios Adicionais

### Exercicio 9: Decomposicao QR

Implemente a decomposicao QR usando Gram-Schmidt. Aplique para resolver o sistema Ax = b pelo metodo dos minimos quadrados. Compare com a solucao direta pelas equacoes normais.

### Exercicio 10: Cholesky e Regressao Ridge

Implemente a decomposicao Cholesky. Use para resolver as equacoes normais Ridge (X^T * X + lambda*I) * beta = X^T * y. Compare a estabilidade numerica com eliminacao gaussiana.

### Exercicio 11: SVD e Compressao de Imagem

Implemente SVD via Jacobi. Aplique em uma imagem 200x200 em escala de cinza:
1. Compute SVD completa
2. Reconstrua com k = 10, 20, 50, 100 valores singulares
3. Calcule PSNR (Peak Signal-to-Noise Ratio) para cada k
4. Plote a curva de compressao vs qualidade

### Exercicio 12: K-Means e Elbow Method

Implemente K-Means do zero. Aplique em um dataset 2D sintetico com 3 clusters. Use o Elbow Method para encontrar o K otimo (plote inertia vs K).

### Exercicio 13: PCA e Visualizacao

Aplique PCA em um dataset de dimensao alta (ex: digitos 8x8 = 64 dimensoes). Projete em 2D e visualize os clusters coloridos por classe. Calcule a variancia explicada por cada componente.

### Exercicio 14: Comparacao de Decomposicoes

Compare tres metodos para resolver Ax = b:
1. Eliminacao gaussiana
2. Decomposicao QR
3. Decomposicao LU

Meça tempo e erro numerico para matrizes de diferentes condicoes (well-conditioned vs ill-conditioned).

### Exercicio 15: Estabilidade Numerica

Implemente um teste de estabilidade para inversao de matrizes. Gere matrizes aleatorias com numero de condicao variando de 10^0 a 10^15. Para cada matriz, compute A * A^-1 e meça a distancia de I (||A * A^-1 - I||_F). Plote condicao vs erro. A que ponto a inversao se torna inutilizavel?

### Exercicio 16: Estruturas de Dados para Matrizes Esparsas

Implemente CSR e COO. Compare o tempo de multiplicacao matriz-vetor para matrizes com 1%, 10% e 50% de densidade. Em que ponto a matriz esparsa se torna mais lenta que a densa?

### Exercicio 17: SVD e Rank Approximation

Gere uma matriz 50x50 com posto efetivo 5 (combinacao de 5 componentes). Compute o SVD e verifique que apenas 5 valores singulares sao significativos. Reconstrua com k=5 e confirme que o erro e proximo de zero.

### Exercicio 18: Analise de Condicao

Implemente o calculo do numero de condicao via SVD: kappa(A) = sigma_max / sigma_min. Gere matrizes com condicao controlada (usando SVD sintetico) e analise como a condicao afeta:
1. Erro na inversao de A
2. Erro na resolucao de Ax = b
3. Convergencia do metodo da iteracao de potencia

Documente a relacao entre condicao e estabilidade numerica.

### Exercicio 19: Matrizes de Covariancia

Dado um dataset X (n x p), implemente:
1. Calculo da matriz de covariancia: C = (1/(n-1)) * X_c^T * X_c
2. Verificacao de propriedades: C e simetrica, semi-definida positiva
3. SVD da covariancia para obter PCA
4. Verificacao de que os autovalores sao iguais as variancias das componentes principais

### Exercicio 20: Benchmark Completo

Implemente todos os algoritmos deste capitulo (determinante, inversa, SVD, QR, Cholesky, K-Means, KNN) em C++. Meça o tempo de execucao para matrizes de tamanho 50, 100, 200 e 500. Plote curvas de escalabilidade e discuta qual algoritmo e o gargalo em cenarios de ML reais.

---

## 16. Resumo

Este capitulo estabeleceu a base matematica para todo o ML:

- **Vetores**: Operacoes fundamentais (soma, dot product, normas). Cada feature e um vetor, cada forward pass usa produtos escalares. Dominar vetores e o primeiro passo para entender qualquer algoritmo de ML.

- **Matrizes**: Soma, multiplicacao, transposta, inversa. Redes neurais sao composicoes de multiplicacoes matriciais. Cada camada de uma rede e essencialmente y = sigma(W*x + b), uma operacao matricial.

- **Determinantes**: Medida do "volume" de uma transformacao. det(A) = 0 indica singularidade. Util para testar invertibilidade e entender mudanca de variavel em integracoes.

- **Autovalores/Autovetores**: Direcoes estaveis sob transformacao. Base de PCA e analise espectral. Autovalores revelam a "forca" de cada direcao principal.

- **SVD**: Decomposicao fundamental de qualquer matriz. Compressao de dados, PCA, recomendacao, pseudoinversa. O SVD e provavelmente a operacao matematica mais importante em ML moderno.

- **Normas**: Medidas de "tamanho" de matrizes. Frobenius (todos os elementos), L1 (max coluna), L2 (espectral), Linfinito (max linha). Cada norma tem uso especifico em regularizacao e analise.

- **Decomposicoes adicionais**: QR (minimos quadrados), Cholesky (matrizes SPD), pseudo-inversa (sistemas overdetermined).

- **Resolucao de Sistemas**: Eliminacao gaussiana, decomposicao LU, equacoes normais. A escolha do metodo depende do tamanho da matriz, da condicao e de quantas vezes o sistema precisa ser resolvido.

- **Otimizacao**: Block multiplication, Strassen, BLAS, GPUs. A multiplicacao de matrizes e o gargalo de quase todo ML — otimizar essa operacao e otimizar tudo.

- **Implementacoes completas**: Matrix class em C++, Rust e Fortran com todas as operacoes. Cada linguagem tem vantagens e desvantagens para operacoes matriciais.

- **Aplicacoes em ML**: K-Means, KNN, PCA, SVD para recomendacao, Filtros Kalman. Cada um desses algoritmos e essencialmente algebra linear aplicada.

No proximo capitulo, veremos funcoes de ativacao — as funcoes nao-lineares que tornam as redes neurais capazes de aprender padroes complexos. Sem nao-linearidade, qualquer rede neural e apenas uma composicao de transformacoes lineares, incapaz de capturar relacoes complexas nos dados.

Prepare-se para entender cada funcao de ativacao, suas derivadas, e como a escolha da funcao afeta dramaticamente o treinamento e a performance do modelo. Implementaremos cada uma em C++ (templates), Rust (traits) e Fortran (interfaces), com comparacao de performance completa.

---

## 17. Glossario de Algebra Linear para ML

| Termo | Definicao | Uso em ML |
|-------|-----------|-----------|
| Vetor | Lista ordenada de numeros | Representa um exemplo de dados (features) |
| Matriz | Array bidimensional de numeros | Representa um batch de dados (cada linha = 1 exemplo) |
| Produto escalar | Soma dos produtos de componentes | Forward pass de uma camada: y = W*x |
| Norma | Medida de "tamanho" de um vetor/matriz | Regularizacao, medir distancias |
| Transposta | Inverter linhas e colunas | Calcular gradientes: W^T * erro |
| Inversa | Matriz que anula a multiplicacao | Resolver sistemas lineares |
| Determinante | Escalar que mede volume | Testar singularidade |
| Autovalor | Escalar de uma transformacao | PCA, analise espectral |
| Autovetor | Vetor direcao estavel | Componentes principais |
| Valor singular | Autovalor da SVD | Compressao, posto, condicao |
| Posto | Numero de direcoes independentes | Rank de uma matriz |
| Condicao | Razao maior/menor autovalor | Estabilidade numerica |
| Decomposicao | Fatorar matriz em componentes | SVD, QR, Cholesky, LU |
| Eliminacao gaussiana | Resolver sistemas lineares | Base de todas as decomposicoes |
| Equacoes normais | X^T*X*b = X^T*y | Solucao de minimos quadrados |
| Gradiente | Vetor de derivadas parciais | Direcao de maior crescimento da loss |
| Hessiana | Matriz de derivadas segundas | Curvatura da loss (second-order methods) |
| Espaco latente | Representacao comprimida | Embeddings em recomendacao e NLP |
| Batch | Subconjunto de dados | Processamento paralelo em mini-batches |
| Feature | Variavel de entrada | Cada coluna da matriz X |
| Label | Variavel de saida | Cada elemento do vetor y |
| Epoch | Passagem completa pelos dados | Treinamento por N epocas |
| Hiperparametro | Configuracao pre-definida | Learning rate, batch size |
| Overfitting | Modelo memoriza dados | Regularizacao combate |
| Underfitting | Modelo simples demais | Mais complexidade resolve |
| Bias | Erro por simplificacao | Modelo com bias alto erra sempre |
| Variancia | Sensibilidade aos dados | Modelo com variancia alta oscila |
| Gradient descent | Minimizacao iterativa | Algoritmo base de treinamento |
| Learning rate | Tamanho do passo | Hiperparametro critico |
| Forward pass | Computar previsao | W*x + b em cada camada |
| Backward pass | Computar gradientes | Backpropagation |
| Regularizacao | Penalizar complexidade | L1 (Lasso), L2 (Ridge) |
| Convergencia | Parametros estabilizam | Treinamento terminou |
| Embedding | Representacao vetorial | Palavras em NLP, itens em recomendacao |
| Kernel | Funcao de similaridade | SVMs de alta dimensionalidade |
| Ensemble | Combinacao de modelos | Random Forest, Gradient Boosting |
| Loss function | Funcao de custo | MSE, Cross-Entropy, Hinge |
| Metrica | Avaliacao do modelo | Accuracy, F1, AUC, RMSE |
| Baseline | Modelo de referencia | Comparar outros modelos |
| Deploy | Colocar em producao | Inference API |
| Pipeline | Sequencia de processos | Pre-processamento -> Treino -> Avaliacao |
| Cross-validation | Validacao robusta | K-Fold, Leave-One-Out |
| Regularizacao L1 | Penalidade L1 (Lasso) | Feature selection automatica |
| Regularizacao L2 | Penalidade L2 (Ridge) | Prevenir overfitting |
| Dropout | Desativar neuronios | Regularizacao em deep learning |
| Batch normalization | Normalizar por batch | Acelerar treinamento |
| Momentum | Acumular gradiente | Escapa de minimos locais |
| Adam | Optimizador adaptativo | Default para maioria dos problemas |
| AdaGrad | Learning rate adaptativo | Bom para features esparsas |
| RMSProp | Media movel de gradientes | Bom para RNNs |
| Early stopping | Parar treino no ponto otimo | Combate overfitting |
| Data augmentation | Aumentar dados artificialmente | Mais dados sem coletar |
| Transfer learning | Reutilizar modelo treinado | Acelerar treinamento |
| Fine-tuning | Ajustar modelo pre-treinado | Adaptar para tarefa especifica |
| Inference | Usar modelo treinado | Previsao em dados novos |
| Latency | Tempo de resposta | Critico para inference em producao |
| Throughput | Exemplos por segundo | Medida de eficiencia |
| Parametro | Variavel aprendida | Pesos W e bias b |
| Hiperparametro | Configuracao fixa | Learning rate, regularizacao |
| Feature engineering | Criar/transformar variaveis | Normalizacao, encoding, selecao |
| Label encoding | Mapear categorias para numeros | Codificar variaveis categoricas |
| One-hot encoding | Vetor binario por categoria | Representacao sem ordinalidade |

---

*[Proximo capitulo: 03 — Funcoes de Ativacao](03-funcoes-ativacao.md)*
