# Capítulo 11: Zero-Knowledge Proofs em C++

> *"Posso provar que sei um segredo sem revelar o segredo."*

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Explicar as três propriedades fundamentais de um ZKP: completeness, soundness e zero-knowledge
2. Diferenciar zk-SNARKs, zk-STARKs e Bulletproofs em termos de trusted setup, tamanho de prova e performance
3. Implementar uma prova de conhecimento de discrete logarithm em C++17 usando OpenSSL
4. Configurar e usar libsnark para gerar e verificar provas em circuitos aritméticos R1CS
5. Avaliar trade-offs entre diferentes sistemas ZKP para casos de uso reais

---

## 11.1 Fundamentos de Zero-Knowledge Proofs

### 11.1.1 Definição Formal

Um protocolo de Prova de Conhecimento Zero é um protocolo interativo entre dois participantes:

- **Prover**: possui informação secreta e quer provar que a conhece
- **Verifier**: quer se convencer de que o Prover conhece o segredo, sem aprender nada sobre ele

Formalmente, um ZKP para uma linguagem L deve satisfazer três propriedades:

| Propriedade | Definição Matemática | Intuição Prática |
|-------------|---------------------|------------------|
| **Completeness** | Para todo x ∈ L, Pr[Verify(P(x), V) = aceita] ≥ 1 - negl(n) | Prover honesto sempre convence o verificador |
| **Soundness** | Para todo x ∉ L e qualquer Prover P*, Pr[Verify(P*(x), V) = aceita] ≤ negl(n) | Prover desonesto não consegue enganar |
| **Zero-Knowledge** | Para todo x ∈ L, existe um simulador S que produz transcritos indistinguíveis dos reais | O verificador não aprende nada além da verdade |

A notação negl(n) significa uma função negligenciável em n (tamanho do input).

### 11.1.2 Exemplo Intuitivo: A Caverna de Ali Baba

Imagine uma caverna circular com duas entradas (A e B) e um corredor no centro bloqueado por uma porta mágica que só abre com a senha "Abre Sesamo":

```
              Entrada A
                  |
                  |
         +--------+--------+
        /                    \
       |    Caverna Circular   |
       |                      |
       |    Corredor    Corredor
        \                    /
         +--------+--------+
                  |
              [Porta Magica]
                  |
              Corredor
                  |
              Entrada B
```

**Protocolo ZKP:**

1. O Prover entra pela caverna pela entrada que quiser (A ou B). O Verificador fica do lado de fora e NÃO vê qual entrada foi usada.
2. O Verificador caminha até a caverna e grita: "Saia pela entrada esquerda!" ou "Saia pela entrada direita!"
3. Se o Prover conhece a senha, pode abrir a porta e sair pela entrada pedida — independentemente de qual entrada usou para entrar.
4. Se o Prover NÃO conhece a senha, só pode sair pela mesma entrada que entrou — e acerta apenas 50% das vezes.

Após 20 rodadas, a probabilidade de um Prover desonesto acertar todas as vezes é (1/2)^20 ≈ 0.00000095 — praticamente zero.

**Propriedades verificadas:**
- **Completeness**: Prover que sabe a senha sempre acerta
- **Soundness**: Prover que não sabe a senha falha com alta probabilidade
- **Zero-Knowledge**: O Verificador só aprende "o Prover sabe a senha" — nada sobre qual senha é

### 11.1.3 Sigma Protocols (3-Messages)

A construção fundamental de ZKPs interativos é o protocolo Sigma, que consiste em três mensagens:

```
Prover                                         Verifier
  |                                               |
  |  1. Escolhe r aleatório                      |
  |     a = Commit(r)  = g^r                     |
  |---- a (commitment) --------------------->    |
  |                                               |
  |                              e = Challenge()  |
  |<---- e (challenge) --------------------|     |
  |                                               |
  |  3. z = Response = r + e * s  (mod q)        |
  |---- z (response) ---------------------->     |
  |                                               |
  |     Verifica: g^z == a * h^e (mod p)         |
```

**Construção para Discrete Logarithm:**
- Prover conhece `s` tal que `h = g^s mod p`
- Commit: `a = g^r mod p` (r aleatório)
- Challenge: `e` (aleatório ou via Fiat-Shamir hash)
- Response: `z = r + e * s mod q`
- Verificação: `g^z = g^(r + e*s) = g^r * g^(e*s) = a * h^e mod p`

**Propriedade Special Soundness:** Dados dois transcritos válidos (a, e₁, z₁) e (a, e₂, z₂) com o mesmo commitment mas challenges diferentes, podemos extrair o segredo:

```
g^z₁ = a * h^e₁  →  g^(z₁-z₂) = h^(e₁-e₂)  →  s = (z₁-z₂) / (e₁-e₂) mod q
```

### 11.1.4 Transformação Fiat-Shamir

O protocolo Sigma é interativo — o challenge depende do Verifier. A heurística Fiat-Shamir transforma um protocolo interativo em não-interativo substituindo o challenge aleatório por um hash criptográfico:

```
e = H(g, h, a)  // hash dos elementos públicos e do commitment
```

Isso funciona porque:
1. O Prover não pode "adivinhar" o hash antes de commits (commitment já foi enviado)
2. O Prover não pode encontrar dois challenges diferentes para o mesmo commitment
3. A segurança depende da resistência a colisões do hash

**Atenção:** A transformação Fiat-Shamir é uma heurística, não uma prova formal. Em cenários adversariais adversariais fortes, pode ser necessário usar o framework ROM (Random Oracle Model).

---

## 11.2 zk-SNARKs: Zero-Knowledge Succinct Non-Interactive Arguments of Knowledge

### 11.2.1 Propriedades

| Propriedade | Significado | Impacto Prático |
|-------------|-------------|-----------------|
| **Zero-Knowledge** | O verificador não aprende nada sobre o witness | Privacidade dos dados de entrada |
| **Succinct** | A prova tem tamanho constante ou logarítmico (~200-400 bytes) | Verificação rápida, ideal para blockchains |
| **Non-Interactive** | Uma única mensagem do Prover ao Verificador | Prático para sistemas assíncronos |
| **Argument of Knowledge** | Soundness computacional (não estatístico) | Segurança baseada em hard assumptions |

### 11.2.2 Pipeline Completo

```
Programa → Circuito Aritmético → R1CS → QAP → Prova SNARK
                                    ↑                ↑
                              trusted setup    Groth16/PLONK
```

**Estágio 1: Circuito Aritmético**

O programa original é convertido em uma sequência de operações aritméticas (+, ×) sobre um corpo finito Fp. Exemplo:

```
// Programa original: y = x³ + x + 5
// Circuito:
//   sym_1 = x × x          (multiplicação)
//   sym_2 = sym_1 × x      (multiplicação)
//   y = sym_2 + x + 5      (adição — linear combination)
```

**Estágio 2: Rank-1 Constraint System (R1CS)**

Cada operação de multiplicação é expressa como uma restrição:

```
<A_i, w> × <B_i, w> = <C_i, w>
```

onde w = [1, x, y, sym_1, sym_2] é o witness vector.

Para o exemplo acima:

| Restrição | A | B | C |
|-----------|---|---|---|
| x × x = sym_1 | [0,1,0,0,0] | [0,1,0,0,0] | [0,0,0,1,0] |
| sym_1 × x = sym_2 | [0,0,0,1,0] | [0,1,0,0,0] | [0,0,0,0,1] |
| sym_2 + x + 5 = y | [5,1,0,0,1] | [1,0,0,0,0] | [0,0,1,0,0] |

**Estágio 3: Quadratic Arithmetic Program (QAP)**

As matrizes A, B, C são transformadas em polinômios via interpolação de Lagrange. Cada coluna se torna um polinômio L(x) que passa pelos valores correspondentes nos pontos de avaliação.

**Estágio 4: Prova e Verificação**

O Prover computa polinômios de quociente e fornece evaluates em pontos aleatórios. O Verifier verifica identidades polinomiais usando pairings bilineares.

### 11.2.3 Groth16

Groth16 é o sistema SNARK mais eficiente para provas individuais:

| Métrica | Groth16 |
|---------|---------|
| Tamanho da prova | 128 bytes (3 elementos G1/G2) |
| Tempo de verificação | 2-5ms |
| Tempo de geração | 1-10s (depende do circuito) |
| Número de constraints suportadas | Até ~2^20 na prática |
| Trusted setup | Sim (per-circuit, toxic waste) |
| Assunções | Knowledge of Exponent (KEA), q-SDH |

**Estrutura da prova Groth16:**

```
π = (π_A ∈ G1, π_B ∈ G2, π_C ∈ G1)
```

**Verificação:**

```
e(π_A, π_B) = e(α, β) · e(L(x), δ) · e(I(x), γ)
```

onde e é um pairing bilinear sobre uma curva elíptica (ex: BN254, BLS12-381).

### 11.2.4 PLONK

PLONK é um sistema SNARK com trusted setup universal — uma única ceremony serve para todos os circuitos:

| Métrica | PLONK |
|---------|-------|
| Tamanho da prova | ~400 bytes |
| Tempo de verificação | 5-10ms |
| Trusted setup | Sim (universal — per-srs, não per-circuit) |
| Flexibilidade | Custom gates, lookup tables |

A vantagem do PLONK é que o trusted setup precisa ser feito apenas uma vez por curva, não por circuito. Isso elimina o risco de toxic waste específico por aplicação.

---

## 11.3 zk-STARKs: Scalable Transparent Arguments of Knowledge

### 11.3.1 Vantagens Fundamentais

| Propriedade | SNARK (Groth16) | STARK |
|-------------|-----------------|-------|
| Trusted setup | Obrigatório | **Nenhum** |
| Tamanho da prova | 128 bytes | ~200 KB |
| Tempo de verificação | 2-5ms | 5-15ms |
| Tempo de geração | 1-10s | 10-100s |
| Assunção criptográfica | Curva elíptica (pairing) | **Hash functions** |
| Post-quantum | Não | **Sim** |
| Escalabilidade | O(n log n) | O(n polylog n) |

### 11.3.2 Construção

STARKs usam quatro componentes principais:

**1. Arithmetization (ALI)**

O programa é expresso como uma Polynomial Identity Language (PIL). O computador define uma relação entre polinômios que deve ser satisfeita:

```
F(x) = 0  para todos x ∈ H (domain)
```

**2. Commitment via Merkle Tree**

Polinômios são avaliados em um domain H e comprometidos via Merkle tree sobre extension fields. Isso permite queries eficientes.

**3. FRI Protocol (Fast Reed-Solomon IOP)**

FRI prova que um polinômio tem grau baixo — essencial para garantir que o computador não "trapaceou" ao escolher polinômios de alto grau.

```
Prover: commit polinômio p₀ de grau d
Verifier: pede evaluated em ponto aleatório r
Prover: revela p₀(r), commit p₁ = fold(p₀, r)
Verifier: repete N vezes
Verificação final: grau baixo do polinômio residual
```

**4. DEEP (Deep Extended FRI)**

Extensão do FRI para verificar valores de polinômios em pontos fora do domain original.

### 11.3.3 Arquitetura de um STARK Prover em C++

```cpp
#include <vector>
#include <array>
#include <cstdint>
#include <cstring>
#include <random>
#include <functional>

// Campo finito Fp para STARKs (ex: Goldilocks field, p = 2^64 - 2^32 + 1)
struct Goldilocks {
    static constexpr uint64_t P = 0xFFFFFFFF00000001ULL;
    uint64_t val;
    
    Goldilocks() : val(0) {}
    explicit Goldilocks(uint64_t v) : val(v % P) {}
    
    Goldilocks operator+(const Goldilocks& o) const {
        uint64_t r = val + o.val;
        return Goldilocks(r >= P ? r - P : r);
    }
    
    Goldilocks operator-(const Goldilocks& o) const {
        uint64_t r = val - o.val + P;
        return Goldilocks(r >= P ? r - P : r);
    }
    
    Goldilocks operator*(const Goldilocks& o) const {
        __uint128_t r = (__uint128_t)val * o.val;
        uint64_t lo = (uint64_t)r;
        uint64_t hi = (uint64_t)(r >> 64);
        uint64_t result = lo - hi * 0xFFFFFFFF00000001ULL;
        return Goldilocks(result >= P ? result - P : result);
    }
    
    bool operator==(const Goldilocks& o) const { return val == o.val; }
};

using F = Goldilocks;

// NTT (Number Theoretic Transform) — FFT sobre campo finito
void ntt(std::vector<F>& a, bool inverse = false) {
    size_t n = a.size();
    if (n == 1) return;
    
    // Bit-reversal permutation
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) std::swap(a[i], a[j]);
    }
    
    // Cooley-Tukey butterfly
    for (size_t len = 2; len <= n; len <<= 1) {
        F wn = root_of_unity(len, inverse);
        for (size_t i = 0; i < n; i += len) {
            F w(1);
            for (size_t j = 0; j < len / 2; j++) {
                F u = a[i + j];
                F v = a[i + j + len / 2] * w;
                a[i + j] = u + v;
                a[i + j + len / 2] = u - v;
                w = w * wn;
            }
        }
    }
    
    if (inverse) {
        F inv_n(F(n).inverse());
        for (auto& x : a) x = x * inv_n;
    }
}

// Merkle Tree para commitments
class MerkleTree {
    std::vector<std::array<uint8_t, 32>> nodes;
    size_t leaf_count;
    
public:
    MerkleTree(const std::vector<std::array<uint8_t, 32>>& leaves) 
        : leaf_count(leaves.size()) {
        nodes.resize(2 * leaf_count);
        for (size_t i = 0; i < leaf_count; i++) {
            nodes[leaf_count + i] = leaves[i];
        }
        for (size_t i = leaf_count - 1; i > 0; i--) {
            nodes[i] = hash_pair(nodes[2 * i], nodes[2 * i + 1]);
        }
    }
    
    std::array<uint8_t, 32> root() const { return nodes[1]; }
    
    // Abrir nó para verificação
    std::vector<std::array<uint8_t, 32>> open(size_t index) const {
        std::vector<std::array<uint8_t, 32>> path;
        size_t pos = index + leaf_count;
        while (pos > 1) {
            path.push_back(nodes[pos ^ 1]);
            pos >>= 1;
        }
        return path;
    }
    
    // Verificar abertura
    static bool verify(const std::array<uint8_t, 32>& root,
                       size_t index,
                       const std::array<uint8_t, 32>& leaf,
                       const std::vector<std::array<uint8_t, 32>>& path) {
        std::array<uint8_t, 32> current = leaf;
        size_t pos = index;
        for (const auto& sibling : path) {
            if (pos & 1) {
                current = hash_pair(sibling, current);
            } else {
                current = hash_pair(current, sibling);
            }
            pos >>= 1;
        }
        return current == root;
    }
    
private:
    static std::array<uint8_t, 32> hash_pair(
        const std::array<uint8_t, 32>& a,
        const std::array<uint8_t, 32>& b) {
        // SHA-256(a || b)
        std::array<uint8_t, 32> result;
        // ... SHA-256 implementation
        return result;
    }
};

// STARK Prover simplificado
struct STARKProof {
    std::vector<F> trace_evaluations;
    std::vector<F> constraint_evaluations;
    std::vector<std::array<uint8_t, 32>> merkle_paths;
    std::vector<F> fri_layers;
};

class STARKProver {
public:
    STARKProof prove(
        const std::vector<F>& trace,
        size_t constraint_count,
        size_t trace_length
    ) {
        STARKProof proof;
        
        // 1. Interpolação: trace → polinômio p(x) via NTT
        auto trace_poly = trace;
        ntt(trace_poly, true); // interpolate
        
        // 2. Commitment: Merkle tree do trace
        auto trace_commitment = commit_polynomial(trace_poly);
        
        // 3. Constraint evaluation
        // Avaliar constraints no domain estendido
        auto extended_domain = compute_extended_domain(trace_length * 8);
        auto constraint_values = evaluate_constraints(trace_poly, extended_domain);
        
        // 4. Constraint commitment
        auto constraint_commitment = commit_polynomial(constraint_values);
        
        // 5. FRI layers
        proof.fri_layers = compute_fri_layers(trace_poly);
        
        // 6. Openings
        proof.trace_evaluations = query_openings(trace_poly);
        proof.constraint_evaluations = query_openings(constraint_values);
        
        return proof;
    }
    
private:
    std::vector<F> compute_extended_domain(size_t size) {
        std::vector<F> domain(size);
        F g = primitive_root(size);
        F current(1);
        for (size_t i = 0; i < size; i++) {
            domain[i] = current;
            current = current * g;
        }
        return domain;
    }
    
    std::vector<F> evaluate_constraints(
        const std::vector<F>& trace_poly,
        const std::vector<F>& domain
    ) {
        // Avalia cada constraint C_i(x, trace(x), trace(g*x))
        size_t n = domain.size();
        std::vector<F> results(n);
        // ... constraint evaluation logic
        return results;
    }
    
    std::vector<F> compute_fri_layers(const std::vector<F>& poly) {
        // FRI folding: reduz grau do polinômio iterativamente
        std::vector<F> layers;
        auto current = poly;
        
        for (int i = 0; i < 80; i++) { // 80 rounds de segurança
            if (current.size() <= 2) break;
            
            // Fold com challenge aleatório
            std::vector<F> folded(current.size() / 2);
            F challenge = F(i + 1); // Em produção: hash dos commitments
            
            for (size_t j = 0; j < folded.size(); j++) {
                folded[j] = current[2*j] + challenge * current[2*j + 1];
            }
            
            layers.insert(layers.end(), folded.begin(), folded.end());
            current = folded;
        }
        
        return layers;
    }
    
    std::vector<F> query_openings(const std::vector<F>& poly) {
        // Abrir em pontos aleatórios para verificação
        std::vector<F> openings;
        for (size_t i = 0; i < 80; i++) {
            size_t idx = i % poly.size();
            openings.push_back(poly[idx]);
        }
        return openings;
    }
    
    std::array<uint8_t, 32> commit_polynomial(const std::vector<F>& poly) {
        std::vector<std::array<uint8_t, 32>> leaves(poly.size());
        // Hash de cada avaliação
        // ...
        MerkleTree tree(leaves);
        return tree.root();
    }
    
    F primitive_root(size_t n) {
        // Encontrar raiz primitiva n-ésima de unidade
        return F(7); // simplificado — em produção, busca algoritmo
    }
};
```

---

## 11.4 Bulletproofs

### 11.4.1 Range Proofs

Bulletproofs são otimizados para range proofs — provar que um valor está em um intervalo [0, 2^n):

```
Provar: v ∈ [0, 2^n)  sem revelar v
```

**Construção básica (1-bit):**

Para cada bit b_i do valor v:
- b_i ∈ {0, 1} equivale a b_i × (1 - b_i) = 0
- Se ambos b_i e (1-b_i) são positivos, então b_i ∈ {0, 1}

**Agregação (Multi-Range Proofs):**

Múltiplos range proofs podem ser agregados em um único proof de tamanho O(log N):

| Número de Range Proofs | Tamanho Individual | Tamanho Agregado |
|------------------------|--------------------|-------------------|
| 1 | 672 bytes | 672 bytes |
| 4 | 672 bytes | 736 bytes |
| 8 | 672 bytes | 800 bytes |
| 64 | 672 bytes | 1,152 bytes |
| 256 | 672 bytes | 1,408 bytes |

### 11.4.2 Uso em Monero

Monero usa Bulletproofs para Confidential Transactions:

```
Transação Monero:
  Input:  commitment C = v·G + r·H  (Pedersen commitment)
  Output: commitment C' = v'·G + r'·H
  
  Bulletproof prova: v' ≥ 0 E v' ∈ [0, 2^64)
  Sem revelar v' nem r'
```

Antes de Bulletproofs, Monero usava rangos de 64 bits com prufoos — cada range proof tinha ~13 KB. Bulletproofs reduziu isso para ~1.5 KB.

---

## 11.5 Bibliotecas C++ para ZKP

### 11.5.1 libsnark

libsnark é a biblioteca de referência para zk-SNARKs em C++:

```cpp
#include <libsnark/common/default_r1cs_ppzksnark_pp.hpp>
#include <libsnark/gadgetlib1/protoboard.hpp>
#include <libsnark/relations/constraint_satisfaction_problems/r1cs/r1cs.hpp>

using namespace libsnark;
using namespace std;

// Tipo de curva: BN128 (default)
using ppT = default_r1cs_ppzksnark_pp;
using FieldT = libff::Fr<ppT>;

// Circuito: provar conhecimento de x tal que x³ + x + 5 = y
class CubicEquationGadget {
public:
    protoboard<FieldT> pb;
    libff::pb_variable<FieldT> x;
    libff::pb_variable<FieldT> y;
    libff::pb_variable<FieldT> sym_1;
    libff::pb_variable<FieldT> sym_2;
    
    CubicEquationGadget() : pb() {
        x.allocate(pb, "x");
        y.allocate(pb, "y");
        sym_1.allocate(pb, "sym_1");
        sym_2.allocate(pb, "sym_2");
    }
    
    void generate_r1cs_constraints() {
        // x * x = sym_1
        pb.add_r1cs_constraint(
            r1cs_constraint<FieldT>(x, x, sym_1));
        // sym_1 * x = sym_2
        pb.add_r1cs_constraint(
            r1cs_constraint<FieldT>(sym_1, x, sym_2));
        // sym_2 + x + 5 = y
        pb.add_r1cs_constraint(
            r1cs_constraint<FieldT>(
                sym_2 + x + FieldT("5"), 
                FieldT("1"), y));
    }
    
    void generate_r1cs_witness(FieldT x_val, FieldT y_val) {
        pb.val(x) = x_val;
        pb.val(sym_1) = x_val * x_val;
        pb.val(sym_2) = pb.val(sym_1) * x_val;
        pb.val(y) = y_val;
    }
};

int main() {
    libff::inhibit_profiling_info = true;
    ppT::init_public_params();
    
    // Criar e popular o circuito
    CubicEquationGadget gadget;
    gadget.generate_r1cs_constraints();
    
    // Witness: x = 3, y = 35 (3³ + 3 + 5 = 35)
    gadget.generate_r1cs_witness(FieldT("3"), FieldT("35"));
    assert(gadget.pb.is_satisfied());
    
    // Trusted setup
    auto keypair = r1cs_ppzksnark<ppT>::setup(gadget.pb);
    
    // Gerar prova
    auto proof = r1cs_ppzksnark<ppT>::prove(gadget.pb);
    
    // Verificar
    bool ok = r1cs_ppzksnark<ppT>::verify(
        keypair.vk, gadget.pb.primary_input(), proof);
    
    cout << "Prova verificada: " << (ok ? "SIM" : "NAO") << endl;
    
    // Serializar prova para armazenamento/transmissão
    std::stringstream ss;
    proof.write(ss);
    cout << "Tamanho da prova: " << ss.str().size() << " bytes" << endl;
    
    return 0;
}
```

### 11.5.2 Construção de Circuitos Complexos

Para circuitos mais complexos, libsnark fornece gadgets reutilizables:

```cpp
// Gadget de SHA-256 dentro de um circuito ZKP
#include <libsnark/gadgetlib1/gadgets/hashes/sha256/sha256_two_to_one_gadget.hpp>

class HashPreimageGadget {
    protoboard<FieldT> pb;
    digest_variable<FieldT> digest;  // hash público
    pb_variable_array<FieldT> preimage;  // preimage secreta
    std::shared_ptr<digest_variable<FieldT>> intermediate;
    
public:
    HashPreimageGadget(size_t preimage_bits) 
        : pb(), digest(pb, 256, "digest") {
        
        // Alocar variáveis do preimage
        preimage.allocate(pb, preimage_bits, "preimage");
        
        // Alocação intermediária para chaining
        intermediate = std::make_shared<digest_variable<FieldT>>(pb, 256, "intermediate");
    }
    
    void generate_r1cs_constraints() {
        // SHA-256(preimage) = digest
        sha256_two_to_one_gadget<FieldT> sha_gadget(
            pb, preimage, digest, "sha256");
        sha_gadget.generate_r1cs_constraints();
    }
    
    void generate_r1cs_witness(const libff::bit_vector& preimage_bits) {
        // Popular o witness com o preimage conhecido
        pb.val(preimage) = preimage_bits;
        // O gadget computa o hash internamente
    }
};
```

### 11.5.3 Comparação de Bibliotecas

| Biblioteca | Tipo | Linguagem | Trusted Setup | Prova (bytes) | Verificação | Uso Principal |
|------------|------|-----------|---------------|---------------|-------------|---------------|
| libsnark | Groth16 | C++ | Sim (per-circuit) | 128 | ~3ms | Pesquisa, prototipação |
| libstark | STARK | C++ | Não | ~200KB | ~10ms | Post-quantum |
| libff | Primitivas | C++ | — | — | — | Curvas elípticas |
| bellman | Groth16 | Rust | Sim | 128 | ~3ms | zkSync, production |
| gnark | Groth16/PLONK | Go | Sim | 128-400 | ~5-10ms | Chain apps |
| circom + snarkjs | DSL+JS | JS/C++ | Sim | 128 | ~3ms | Circuit authoring |
| Noir | DSL | Rust | Sim (Barretenberg) | ~400 | ~5ms | Developer-friendly |

---

## 11.6 Exemplo Completo: Prova de Discrete Logarithm

### 11.6.1 Protocolo Schnorr com OpenSSL

```cpp
#include <openssl/bn.h>
#include <openssl/sha.h>
#include <openssl/ec.h>
#include <openssl/obj_mac.h>
#include <iostream>
#include <vector>
#include <cstring>

class SchnorrZKP {
    EC_GROUP* group;
    EC_POINT* g;  // gerador
    BIGNUM* order;
    
public:
    SchnorrZKP(int curve_nid = NID_X9_62_prime256v1) {
        group = EC_GROUP_new_by_curve_name(curve_nid);
        g = EC_POINT_new(group);
        order = BN_new();
        
        EC_GROUP_get_order(group, order, nullptr);
        EC_GROUP_get_generator(group, g);
    }
    
    ~SchnorrZKP() {
        EC_GROUP_free(group);
        EC_POINT_free(g);
        BN_free(order);
    }
    
    // Estrutura da prova Schnorr
    struct Proof {
        EC_POINT* commitment;  // t = g^r
        BIGNUM* challenge;     // e = H(g, h, t)
        BIGNUM* response;      // s = r + e * x mod q
    };
    
    // Gerar par de chaves
    void keygen(EC_POINT*& public_key, BIGNUM*& private_key) {
        BN_CTX* ctx = BN_CTX_new();
        private_key = BN_new();
        public_key = EC_POINT_new(group);
        
        // Gerar chave privada aleatória
        BN_rand_range(private_key, order);
        
        // h = g^x mod p
        EC_POINT_mul(group, public_key, nullptr, g, private_key, ctx);
        
        BN_CTX_free(ctx);
    }
    
    // Prover: gerar prova
    Proof prove(const BIGNUM* private_key, const EC_POINT* public_key) {
        BN_CTX* ctx = BN_CTX_new();
        
        // 1. Escolher r aleatório
        BIGNUM* r = BN_new();
        BN_rand_range(r, order);
        
        // 2. Commit: t = g^r
        EC_POINT* t = EC_POINT_new(group);
        EC_POINT_mul(group, t, nullptr, g, r, ctx);
        
        // 3. Challenge: e = H(g || h || t) via Fiat-Shamir
        BIGNUM* e = compute_challenge(g, public_key, t);
        
        // 4. Response: s = r + e * x mod q
        BIGNUM* s = BN_new();
        BIGNUM* ex = BN_new();
        BN_mod_mul(ex, e, private_key, order, ctx);
        BN_mod_add(s, r, ex, order, ctx);
        
        BN_free(r);
        BN_free(ex);
        BN_CTX_free(ctx);
        
        return {t, e, s};
    }
    
    // Verifier: verificar prova
    bool verify(const EC_POINT* public_key, const Proof& proof) {
        BN_CTX* ctx = BN_CTX_new();
        
        // 1. Recalcular challenge
        BIGNUM* e_expected = compute_challenge(g, public_key, proof.commitment);
        if (BN_cmp(proof.challenge, e_expected) != 0) {
            BN_free(e_expected);
            BN_CTX_free(ctx);
            return false;
        }
        
        // 2. Verificar g^s = t * h^e
        // LHS: g^s
        EC_POINT* lhs = EC_POINT_new(group);
        EC_POINT_mul(group, lhs, nullptr, g, proof.response, ctx);
        
        // RHS: t * h^e
        EC_POINT* h_e = EC_POINT_new(group);
        EC_POINT_mul(group, h_e, nullptr, public_key, proof.challenge, ctx);
        
        EC_POINT* rhs = EC_POINT_new(group);
        EC_POINT_add(group, rhs, proof.commitment, h_e, ctx);
        
        bool valid = (EC_POINT_cmp(group, lhs, rhs, ctx) == 0);
        
        EC_POINT_free(lhs);
        EC_POINT_free(h_e);
        EC_POINT_free(rhs);
        BN_free(e_expected);
        BN_CTX_free(ctx);
        
        return valid;
    }
    
private:
    // Fiat-Shamir challenge: e = SHA-256(g || h || t) mod order
    BIGNUM* compute_challenge(const EC_POINT* g_pt, 
                               const EC_POINT* h_pt, 
                               const EC_POINT* t_pt) {
        SHA256_CTX sha;
        unsigned char hash[32];
        unsigned char buf[256];
        size_t len;
        
        SHA256_Init(&sha);
        
        // Hash de g
        len = EC_POINT_point2oct(group, g_pt, 
                                  POINT_CONVERSION_UNCOMPRESSED,
                                  buf, sizeof(buf), nullptr);
        SHA256_Update(&sha, buf, len);
        
        // Hash de h
        len = EC_POINT_point2oct(group, h_pt, 
                                  POINT_CONVERSION_UNCOMPRESSED,
                                  buf, sizeof(buf), nullptr);
        SHA256_Update(&sha, buf, len);
        
        // Hash de t
        len = EC_POINT_point2oct(group, t_pt, 
                                  POINT_CONVERSION_UNCOMPRESSED,
                                  buf, sizeof(buf), nullptr);
        SHA256_Update(&sha, buf, len);
        
        SHA256_Final(hash, &sha);
        
        BIGNUM* e = BN_bin2bn(hash, 32, nullptr);
        BN_mod(e, e, order, BN_CTX_new());
        return e;
    }
};

// Demonstração completa
int main() {
    // 1. Setup
    SchnorrZKP zkp(NID_X9_62_prime256v1);
    
    // 2. Key generation
    EC_POINT* public_key = nullptr;
    BIGNUM* private_key = nullptr;
    zkp.keygen(public_key, private_key);
    
    std::cout << "Chave privada gerada" << std::endl;
    
    // 3. Prover gera prova (conhece a chave privada)
    auto proof = zkp.prove(private_key, public_key);
    std::cout << "Prova gerada" << std::endl;
    
    // 4. Verifier verifica a prova
    bool valid = zkp.verify(public_key, proof);
    std::cout << "Verificacao: " << (valid ? "ACEITA" : "REJEITA") << std::endl;
    
    // 5. Teste com chave incorreta (deve rejeitar)
    BIGNUM* wrong_key = BN_new();
    BN_set_word(wrong_key, 42);  // chave incorreta
    auto fake_proof = zkp.prove(wrong_key, public_key);
    bool fake_valid = zkp.verify(public_key, fake_proof);
    std::cout << "Prova falsa: " << (fake_valid ? "ACEITA" : "REJEITA") << std::endl;
    
    // Cleanup
    EC_POINT_free(public_key);
    BN_free(private_key);
    BN_free(wrong_key);
    EC_POINT_free(proof.commitment);
    BN_free(proof.challenge);
    BN_free(proof.response);
    EC_POINT_free(fake_proof.commitment);
    BN_free(fake_proof.challenge);
    BN_free(fake_proof.response);
    
    return 0;
}
```

### 11.6.2 Compilação e Execução

```bash
# Compilar
g++ -std=c++17 -O2 -o schnorr_zkp schnorr_zkp.cpp \
    -lssl -lcrypto -lstdc++fs

# Executar
./schnorr_zkp
# Output:
# Chave privada gerada
# Prova gerada
# Verificacao: ACEITA
# Prova falsa: REJEITA
```

---

## 11.7 Uso em Sistemas Reais

### 11.7.1 Zcash — Shielded Transactions

Zcash é o exemplo mais bem-sucedido de ZKPs em produção. O protocolo Sapling (2018) usa Groth16 sobre a curva BLS12-381:

**Componentes da Transação Shielded:**

| Componente | Descrição | Privacidade |
|------------|-----------|-------------|
| Note commitment | CM = H(v, r, rho, psi) | Valor v oculto |
| Merkle path | Prova de inclusão na Merkle tree | Qual nota foi gasta |
| Nullifier | NF = H(nf_key, rho) | Previne double-spend |
| Value commitment | CV = v·G + rcv·H | Bind ao valor |
| Range proof | v ∈ [0, 2^64) | Previne valores negativos |
| Signature | SpendAuthSig | Autentica o gasto |

**Fluxo de uma Shielded Transaction:**

```
1. Sender cria note: (v, rho, r, recipient, memo)
2. Compute note commitment: CM = H(v, r, rho, psi)
3. Adiciona CM à Merkle tree
4. Para gastar:
   a. Provar conhecimento de (v, r, rho, psi) tal que:
      - CM é válido
      - CM está na Merkle tree (inclusion proof)
      - v ∈ [0, 2^64) (range proof via Bulletproofs)
   b. Compute nullifier: NF = H(nf_key, rho)
   c. Assinar com spend authority key
5. Verifier (nodes da rede):
   a. Verifica a prova ZK
   b. Verifica nullifier não foi gasto
   c. Adiciona nullifier à lista de gastos
```

**Impacto:**
- Sapling reduziu o tamanho de transações shielded de ~50 KB para ~2 KB
- Tempo de geração de prova caiu de ~37s para ~1s
- ~95% das transações Zcash são shielded

### 11.7.2 Filecoin — Proof of Replication

Filecoin usa zk-STARKs para provar armazenamento de dados:

**Two Proofs:**
1. **PoRep (Proof of Replication):** Prova que dados foram armazenados de forma única (replicated)
2. **PoSt (Proof of Spacetime):** Prova que dados continuam armazenados ao longo do tempo

**Arquitetura:**

```
Miner
  |
  ├── 1. Receive sealed sector
  ├── 2. Generate PoRep proof (STARK, ~10min)
  ├── 3. Submit to blockchain
  |
Verifier (network)
  |
  ├── 1. Verify PoRep proof (~10ms)
  ├── 2. Check seal is valid
  └── 3. Award storage power
```

**Escala:**
- Filecoin processa ~10,000 provas por hora
- Proof size: ~200 KB por STARK
- Total de dados armazenados: ~20 EiB (2024)

### 11.7.3 Identidade Digital e Credenciais

ZKPs são usados para verificação de credenciais sem revelar dados pessoais:

| Caso de Uso | ZKP Tipo | Dado Privado | Dado Público | Biblioteca |
|-------------|----------|-------------|--------------|------------|
| Idade (18+) | Range proof | Data de nascimento | Idade >= 18 | Bulletproofs |
| Renda | Range proof | Salário exato | Renda >= threshold | Bulletproofs |
| Nacionalidade | Set membership | País de origem | País ∈ {lista} | Groth16 |
| Diploma | Set membership | Hash do diploma | Universidade ∈ {lista} | Groth16 |
| KYC completo | Selective disclosure | Todos os dados | Atributos específicos | Idemix |
| Votação | Shuffle + proof | Voto | Resultado | Verificável |

**Exemplo: Prova de Idade sem Revelar Data**

```cpp
// Provar: idade >= 18 sem revelar data de nascimento
// Usando Bulletproof range proof
//
// Dado público: data atual (now)
// Dado privado: data de nascimento (dob)
// 
// Computação: idade_em_dias = now - dob
// Prova: idade_em_dias >= 18 * 365

struct AgeProof {
    Bulletproof range_proof;  // provar idade >= threshold
    PedersenCommitment commitment;  // compromisso com idade
};

AgeProof prove_age(time_t birth_date, time_t threshold_date) {
    uint64_t age_days = difftime(time(nullptr), birth_date) / 86400;
    uint64_t threshold_days = threshold_date / 86400;
    
    // Range proof: (age_days - threshold_days) ∈ [0, 2^64)
    // Isso prova que age_days >= threshold_days
    uint64_t adjusted_value = age_days - threshold_days;
    
    return {
        .range_proof = bulletproof_prove(adjusted_value, 64),
        .commitment = pedersen_commit(adjusted_value)
    };
}

bool verify_age_proof(const AgeProof& proof) {
    // Verificar range proof
    return bulletproof_verify(proof.range_proof, proof.commitment);
}
```

---

## 11.8 Performance e Benchmarks

### 11.8.1 Comparação Detalhada

| Sistema | Tamanho Prova | Geração | Verificação | Trusted Setup | Quantum-Safe |
|---------|--------------|---------|-------------|---------------|-------------|
| Groth16 (BN254) | 128 bytes | 0.5-5s | 2-5ms | Sim (per-circuit) | Não |
| PLONK (BLS12-381) | 400 bytes | 1-10s | 5-10ms | Sim (universal) | Não |
| Marlin (BLS12-381) | 600 bytes | 2-15s | 8-15ms | Sim (universal) | Não |
| STARK (Goldilocks) | 200 KB | 5-50s | 5-15ms | **Não** | **Sim** |
| Bulletproof (secp256k1) | 672 bytes | 0.5-5s | 10-50ms | **Não** | Não |
| Halo2 (Pasta) | 400 bytes | 1-10s | 5-10ms | **Não** | Não |

### 11.8.2 Fatores de Performance

Os principais gargalos na geração de provas:

**1. Multi-Scalar Multiplication (MSM)**
- 50-80% do tempo de geração
- Otimização: Pippenger's algorithm, GPU acceleration
- Speedup: 10-100x com GPU

**2. Number Theoretic Transform (NTT)**
- Equivalente a FFT sobre campos finitos
- Complexidade: O(n log n)
- Otimização: Parallel NTT, cache-friendly layouts

**3. Hash sobre Campo**
- Merkle tree building
- Challenge computation
- Speedup: Poseidon hash (arithmetic-friendly)

### 11.8.3 Benchmarks em Diferentes Hardware

| Hardware | Groth16 Geração | STARK Geração | Bulletproof Geração |
|----------|-----------------|---------------|---------------------|
| CPU (Intel i9) | 2s | 20s | 3s |
| GPU (RTX 4090) | 0.2s | 5s | 1s |
| GPU cluster (8x A100) | 0.05s | 1s | 0.2s |
| ARM (Apple M2) | 3s | 30s | 5s |

---

## 11.9 Limitações e Desafios

### 11.9.1 Trusted Setup

O trusted setup em Groth16 é o maior risco prático:

**Problema:** Se o "toxic waste" (parâmetros aleatórios da ceremony) não for destruído, um atacante pode gerar provas falsas.

**Mitigações:**

| Abordagem | Descrição | Risco Residual |
|-----------|-----------|----------------|
| MPC Ceremony | Múltiplos participantes; basta 1 honesto | Colusão total |
| Universal Setup | PLONK: 1 ceremony para todos os circuitos | Mesmo risco, menor superfície |
| Sem Setup | STARKs/Bulletproofs | Nenhum |
| Subversion resistance | Protocolos resistentes a subversão do setup | Pesquisa ativa |

**Exemplo de Ceremony bem-sucedida:**
- Powers of Tau (zCash): 90+ participantes, multi-jurisdictions
- Sequal ceremony: 175+ participantes, organização Open Source
- Nenhum participante revelou sua contribuição

### 11.9.2 Complexidade de Circuitos

Expressar programas como circuitos aritméticos é difícil:

| Desafio | Descrição | Impacto |
|---------|-----------|---------|
| Loops | Circuitos são estáticos; loops requerem unrolling | Explosão de tamanho |
| Memória dinâmica | Alocação dinâmica não existe em circuitos | Não suportado |
| Operações complexas | SHA-256 requer ~25,000 gates | Circuitos enormes |
| Erros silenciosos | Bug no circuito → provas válidas para inputs inválidos | Segurança comprometida |

**Soluções emergentes:**

1. **Circuit Compilers**: Circom, Noir, Leo — linguagens de alto nível compilam para circuits
2. **Lookup Tables**: Reduzem complexidade de operações complexas (SHA, Keccak)
3. **Custom Gates**: Gates específicos para operações frequentes
4. **Virtual Machine**: zkEVM — executar EVM dentro de um circuito ZK

### 11.9.3 Quantum Resistance

| Sistema | Base Criptográfica | Quantum-Safe |
|---------|-------------------|--------------|
| Groth16 | ECDLP (curva elíptica) | Não |
| PLONK | ECDLP | Não |
| Marlin | ECDLP | Não |
| Bulletproof | ECDLP | Não |
| STARK | Hash functions | **Sim** |
| Halo2 | ECDLP | Não |

Para aplicações que precisam de quantum resistance (dados sensíveis com longa vida útil), STARKs são a escolha atual.

---

## 11.10 Exercícios

### Exercício 1: Schnorr Protocol
Implemente o protocolo Schnorr completo em C++ usando OpenSSL. Inclua:
- Geração de chave (curva P-256)
- Geração de prova (3 mensagens)
- Verificação de prova
- Teste com chave incorreta (deve rejeitar)

### Exercício 2: Range Proof Conceitual
Implemente um range proof simples para provar que `v ∈ [0, 15)` usando decomposição em bits. Cada bit é provado ser 0 ou 1 via produto b × (1-b) = 0.

### Exercício 3: Circuit R1CS com libsnark
Crie um circuito que prova conhecimento de fatores de N:
- Input público: N
- Input privado: p, q tal que p × q = N
- Compile e gere prova

### Exercício 4: Benchmark
Meça tempo de geração e verificação para circuitos de 10, 100, 1000 constraints. Plot os resultados e analise a complexidade.

### Exercício 5: Fiat-Shamir Transform
Implemente a transformação Fiat-Shamir para o protocolo Schnorr. Compare o tamanho da prova interativa vs não-interativa.

### Exercício 6: Merkle Tree para ZKP
Implemente uma Merkle tree otimizada para provas de inclusão. Inclua:
- Build: O(n)
- Open: O(log n)
- Verify: O(log n)
- Teste com 1M de folhas

### Exercício 7: Comparison Table
Crie uma tabela comparativa experimental entre Groth16 e Bulletproofs para o mesmo circuito. Meça: tamanho de prova, tempo de geração, tempo de verificação, e consumo de memória.

---

## 11.11 Referências

### Papers Fundamentais

1. Goldwasser, S., Micali, S., Rackoff, C. (1989). "The Knowledge Complexity of Interactive Proof Systems." *SIAM Journal on Computing*, 18(1), 186-208.
2. Schnorr, C.P. (1991). "Efficient Signature Generation by Smart Cards." *Journal of Cryptology*, 4(3), 161-174.
3. Fiat, A., Shamir, A. (1987). "How to Prove Yourself: Practical Solutions to Identification and Signature Problems." *CRYPTO 1986*.
4. Groth, J. (2016). "On the Size of Pairing-based Non-interactive Arguments." *EUROCRYPT 2016*, 305-326.
5. Ben-Sasson, E. et al. (2018). "Scalable, transparent, and post-quantum secure computational integrity." *IACR ePrint 2018/046*.
6. Bünz, B. et al. (2018). "Bulletproofs: Short Proofs for Confidential Transactions and More." *IEEE S&P 2018*.
7. Gabizon, A., Williamson, Z., Ciobotaru, O. (2019). "PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive Arguments of Knowledge." *IACR ePrint 2019/953*.
8. Bowe, S. et al. (2019). "Halo 2: Recursive Proof Composition without a Trusted Setup." *IACR ePrint 2019/1021*.

### Bibliotecas

9. libsnark: https://github.com/scipr-lab/libsnark
10. libstark (StarkWare): https://github.com/starkware-libs
11. libff: https://github.com/scipr-lab/libff
12. Circom: https://docs.circom.io/
13. Noir: https://noir-lang.org/
14. gnark: https://github.com/consensys/gnark
15. bellman: https://github.com/privacy-exploration/bellman

### Aplicações

16. Ben-Sasson, E. et al. (2014). "Zerocash: Decentralized Anonymous Payments from Bitcoin." *IEEE S&P 2014*.
17. Ben-Sasson, E. et al. (2019). "A Deep Dive into zkSNARKs." *Zcash Blog*.
18. Filecoin Specification: "Proof of Replication." https://spec.filecoin.io/
19. Protocol Labs (2019). "PoSt (Proof of Spacetime)." Filecoin Documentation.

### Recursos Adicionais

20. Buterin, V. (2017). "Quadratic Arithmetic Programs: from Zero to Hero." Vitalik.ca.
21. 3Blue1Brown (2023). "zk-SNARKs Explained Visually." YouTube.
22. Boneh, D. (2023). "Stanford CS255: Introduction to Cryptography." Stanford.
23. ZKP MOOC (2023). "Zero Knowledge Proofs." by Dan Boneh and others.
24. Kozlov, A. (2022). "Understanding zk-SNARKs from the Ground Up." Medium.
25. Ethereum Foundation (2023). "Zero Knowledge Proof Ecosystem." ethereum.org.
---

*[Capítulo anterior: 10 — Criptografia Homomorfica](10-criptografia-homomorfica.md)*
*[Próximo capítulo: 12 — Verificacao Formal](12-verificacao-formal.md)*
