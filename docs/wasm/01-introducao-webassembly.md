# Capítulo 1: Introdução ao WebAssembly

## Sumário

- [1.1 História: de asm.js ao WebAssembly](#11-história-de-asmjs-ao-webassembly)
- [1.2 Arquitetura: a máquina de pilha](#12-arquitetura-a-máquina-de-pilha)
- [1.3 Formato de bytecode](#13-formato-de-bytecode)
- [1.4 Pipeline de compilação](#14-pipeline-de-compilação)
- [1.5 Módulo, Instância, Memória e Tabela](#15-módulo-instância-memória-e-tabela)
- [1.6 Integração com o navegador](#16-integração-com-o-navegador)
- [1.7 WebAssembly no lado do servidor](#17-webassembly-no-lado-do-servidor)
- [1.8 WASI Preview](#18-wasi-preview)
- [1.9 Comparação com outras tecnologias](#19-comparação-com-outras-tecnologias)
- [1.10 Exemplo WAT completo](#110-exemplo-wat-completo)

---

## 1.1 História: de asm.js ao WebAssembly

### O problema original

Desde os primórdios da Web, o navegador era um ambiente dominado por JavaScript. Linguagens como C, C++ e Rust não tinham um caminho natural para executar código de alta performance dentro do contexto do browser. A solução tradicional era converter o código para JavaScript, mas essa abordagem sofria com limitações fundamentais de desempenho.

JavaScript foi projetado como uma linguagem interpretada e dinamicamente tipada. Essas características, que facilitam o uso para scripts simples, tornam impossível otimizar o código de forma agressiva. O navegador precisa realizar inferência de tipos em tempo de execução, o que adiciona overhead significativo em operações numéricas intensivas.

### asm.js: o primeiro passo

Em 2012, a Mozilla iniciou o projeto Emscripten, um compilador LLVM-to-JavaScript. A motivação era compilar o motor do Firefox (escrito em C++) para que ele pudesse rodar dentro de outro navegador. Esse projeto revelou que o JavaScript poderia ser usado como um alvo de compilação de baixo nível, desde que seguisse certas restrições.

Em 2013, Alon Zakai (criador do Emscripten) e Luke Wagner formalizaram o asm.js como um subconjunto otimizável de JavaScript. O asm.js definia restrições específicas que permitiam aos navegadores realizar Ahead-of-Time (AOT) compilation, eliminando a necessidade de interpretação.

As principais restrições do asm.js incluíam:

- Declaração explícita de tipos numéricos
- Uso estritamente controlado de variáveis
- Ausência de closures e garbage collection
- Alocação de memória linear via ArrayBuffer

```javascript
// Exemplo simplificado de código asm.js
function MyModule(stdlib, foreign, heap) {
    "use asm";

    // Declaração explícita de tipos
    var sqrt = stdlib.Math.sqrt;
    var HEAPF64 = new stdlib.Float64Array(heap);

    // Função com tipo explícito
    function distance(x, y) {
        x = +x;  // coerção para double
        y = +y;
        return +sqrt(x * x + y * y);
    }

    // Função que acessa memória linear
    function processArray(offset, count) {
        offset = offset | 0;   // coerção para int32
        count = count | 0;
        var i = 0;
        var sum = 0.0;

        for (i = 0; (i | 0) < (count | 0); i = (i + 1) | 0) {
            sum = sum + HEAPF64[(offset + (i << 3)) >> 3];
        }

        return +sum;
    }

    return {
        distance: distance,
        processArray: processArray
    };
}
```

O asm.js permitiu que aplicações complexas rodassem no navegador com desempenho significativamente superior ao JavaScript puro. Projetos como Unreal Engine 4 e Unity usaram asm.js para portar jogos 3D completos para o browser. No entanto, o asm.js ainda era JavaScript válido, o que limitava as otimizações possíveis.

### A transição para WebAssembly

Embora o asm.js fosse uma melhoria substancial, tinha limitações inerentes:

1. **Tamanho do código**: asm.js era JavaScript em texto, o que resultava em arquivos grandes e lenta parse
2. **Velocidade de compilação**: mesmo com AOT compilation, o parser do JavaScript ainda era um gargalo
3. **Paridade de linguagem**: nem toda funcionalidade de C++ podia ser expressa eficientemente em asm.js
4. **Sintaxe**: o formato textual não era otimizado para consumo de máquina

Em 2015, representantes da Mozilla, Google, Microsoft e Apple se reuniram para criar um novo formato binário que resolvesse essas limitações. O resultado foi o WebAssembly (Wasm), anunciado publicamente em março de 2016 e com suporte estável em todos os navegadores principais em dezembro de 2017.

### Marco temporal do WebAssembly

| Ano | Marco |
|------|-------|
| 2012 | Início do projeto Emscripten |
| 2013 | Publicação do asm.js |
| 2015 | Anúncio do projeto WebAssembly |
| 2016 | Primeira demonstração em navegradore |
| 2017 | MVP (Minimum Viable Product) estabilizado |
| 2017 | Suporte em Chrome, Firefox, Edge e Safari |
| 2019 | WASI (WebAssembly System Interface) publicado |
| 2020 | Component Model proposto |
| 2022 | WASI Preview 2 iniciado |
| 2024 | Threads, GC e Exception Handling em estáveis |

### A comunidade e a governança

WebAssembly é especificado como um padrão W3C. A Working Group do W3C é responsável pela especificação, mas o desenvolvimento ativo ocorre na Communiation Group e na Community Group do WebAssembly. Isso permite que empresas e indivíduos contribuam diretamente com propostas de evolução do padrão.

O processo de especificação é transparente e aberto. As propostas de extensões (propostas) são publicadas no repositório oficial do WebAssembly e passam por revisão pública antes de serem incorporadas ao padrão.

---

## 1.2 Arquitetura: a máquina de pilha

### Fundamentos da máquina de pilha

WebAssembly é especificado como uma máquina de pilha (stack machine), uma escolha arquitetural que tem implicações profundas no design e na segurança da plataforma. Uma máquina de pilha é uma arquitetura de computador onde as operações trabalham primariamente com uma pilha de valores, em vez de registradores.

Nessa arquitetura, os operandos são empilhados antes de uma operação e o resultado substitui os operandos no topo da pilha. Por exemplo, para calcular `3 + 4`, o fluxo seria:

```
Pilha inicial: []
Empilhar 3:    [3]
Empilhar 4:    [3, 4]
Executar add:  [7]
```

Essa arquitetura é particularly bem-suited para WebAssembly por vários motivos:

1. **Simplicidade de validação**: é fácil verificar se os tipos dos operandos corretos
2. **Compactação**: operandos implícitos (estão na pilha) reduzem o tamanho do bytecode
3. **Segurança**: a validação estática pode garantir que a pilha nunca fique em estado inválido
4. **Compatibilidade**: muitas linguagens compilam naturalmente para código orientado a pilha

### A pilha de valores do Wasm

A pilha de valores do WebAssembly é uma estrutura de dados que mantém valores de tipos conhecidos. Diferente de uma pilha genérica, a pilha do Wasm é tipada estaticamente, o que significa que, em qualquer ponto da execução, é possível determinar exatamente quais tipos estão na pilha.

Os tipos suportados no MVP incluem:

| Tipo | Descrição | Tamanho |
|------|-----------|---------|
| `i32` | Inteiro de 32 bits com sinal | 4 bytes |
| `i64` | Inteiro de 64 bits com sinal | 8 bytes |
| `f32` | Ponto flutuante de 32 bits (IEEE 754) | 4 bytes |
| `f64` | Ponto flutuante de 64 bits (IEEE 754) | 8 bytes |

Extensões posteriores adicionaram:

| Tipo | Descrição | Extensão |
|------|-----------|----------|
| `v128` | Vetor de 128 bits | SIMD |
| `funcref` | Referência a função | Ref Types |
| `externref` | Referência externa | Ref Types |

### Categorias de instruções

As instruções do WebAssembly são organizadas em categorias funcionais. Cada categoria manipula a pilha de formas específicas:

**Instruções de constante**: empilham valores na pilha

```wat
;; Empilhar constantes
i32.const 42      ;; Pilha: [42 : i32]
i64.const 1000    ;; Pilha: [1000 : i64]
f32.const 3.14    ;; Pilha: [3.14 : f32]
f64.const 2.71828 ;; Pilha: [2.71828 : f64]
```

**Instruções aritméticas**: operam sobre valores numéricos

```wat
;; Operações aritméticas básicas
i32.add     ;; (i32, i32) -> i32
i32.sub     ;; (i32, i32) -> i32
i32.mul     ;; (i32, i32) -> i32
i32.div_s   ;; divisão com sinal (i32, i32) -> i32
i32.div_u   ;; divisão sem sinal (i32, i32) -> i32
i32.rem_s   ;; resto com sinal (i32, i32) -> i32
i32.rem_u   ;; resto sem sinal (i32, i32) -> i32

;; Operações bit a bit
i32.and     ;; AND (i32, i32) -> i32
i32.or      ;; OR (i32, i32) -> i32
i32.xor     ;; XOR (i32, i32) -> i32
i32.shl     ;; shift left (i32, i32) -> i32
i32.shr_s   ;; shift right com sinal (i32, i32) -> i32
i32.shr_u   ;; shift right sem sinal (i32, i32) -> i32

;; Operações de comparação
i32.eq      ;; igualdade (i32, i32) -> i32
i32.ne      ;; desigualdade (i32, i32) -> i32
i32.lt_s    ;; menor que, sinal (i32, i32) -> i32
i32.lt_u    ;; menor que, sem sinal (i32, i32) -> i32
i32.gt_s    ;; maior que, sinal (i32, i32) -> i32
i32.gt_u    ;; maior que, sem sinal (i32, i32) -> i32
i32.le_s    ;; menor ou igual, sinal (i32, i32) -> i32
i32.le_u    ;; menor ou igual, sem sinal (i32, i32) -> i32
i32.ge_s    ;; maior ou igual, sinal (i32, i32) -> i32
i32.ge_u    ;; maior ou igual, sem sinal (i32, i32) -> i32
```

**Instruções de controle**: alteram o fluxo de execução

```wat
;; Bloco, loop e if/else
block (result i32)
    i32.const 1
end

loop (result i32)
    i32.const 0
end

if (result i32)
    i32.const 1
else
    i32.const 0
end
```

**Instruções de memória**: acessam memória linear

```wat
;; Load e Store
i32.load offset=0 align=4   ;; carrega i32 da memória
i32.store offset=0 align=4  ;; armazena i32 na memória

;; Operações de memória
memory.size    ;; retorna o tamanho atual da memória em páginas
memory.grow    ;; aumenta o tamanho da memória
```

**Instruções de variáveis**: manipulam variáveis locais e globais

```wat
local.get 0     ;;获取 variável local 0
local.set 1     ;; seta variável local 1
local.tee 2     ;; seta e empilha (como set + get)
global.get 0    ;;获取 variável global 0
global.set 1    ;; seta variável global 1
```

### O modelo de execução

O modelo de execução do WebAssembly define formalmente como as instruções transformam o estado. O estado de uma instância WebAssembly consiste em:

1. **Pilha de valores** (operand stack)
2. **Pilha de chamadas** (call stack)
3. **Memória linear**
4. **Tabela de funções**
5. **Variáveis locais** (para cada frame de chamada)
6. **Variáveis globais**

Cada instrução é definida em termos de como ela transforma esses componentes de estado. A especificação formal usa semântica small-step, o que significa que cada instrução é definida como uma transformação atômica do estado.

A pilha de chamadas é uma pilha de frames, onde cada frame representa uma execução de função. Um frame contém:

- Referência para o módulo que contém a função
- Variáveis locais da função
- Um ponteiro de instrução (program counter)
- O rótulo de continuação (usado para branches)

Quando uma função é chamada, um novo frame é empilhado. Quando a função retorna, o frame é desempilhado e os valores de retorno são transferidos para a pilha do chamador.

---

## 1.3 Formato de bytecode

### Visão geral do formato binário

WebAssembly define dois formatos para módulos: um formato binário compacto (`.wasm`) e um formato textual equivalente (`.wat`). O formato binário é o que os navegadores e runtimes efetivamente consomem, enquanto o formato textual serve para depuração, análise e escrita manual.

Ambos os formatos são equivalentes e intercambiáveis — um tradutor (wat2wasm ou wasm2wat) pode converter entre eles sem perda de informação. No entanto, o formato binário é tipicamente 10-30% menor que o textual equivalente.

### Estrutura de um módulo binário

Um módulo binário é organizado em seções, cada uma contendo informações específicas sobre o módulo. O formato usa um sistema de IDs de seção onde cada tipo de informação tem um ID numérico fixo.

| ID | Seção | Descrição |
|------|-------|-----------|
| 0 | Custom | Informações adicionais (nomes, depuração) |
| 1 | Type | Assinaturas de tipos de funções |
| 2 | Import | Importações de outros módulos |
| 3 | Function | Mapeamento de funções para tipos |
| 4 | Table | Definição de tabelas de funções |
| 5 | Memory | Definição de memórias lineares |
| 6 | Global | Definição de variáveis globais |
| 7 | Export | Exportações do módulo |
| 8 | Start | Função de inicialização |
| 9 | Element | Inicialização de tabelas e referências |
| 10 | Code | Corpos das funções |
| 11 | Data | Inicialização da memória linear |
| 12 | Data Count | Contagem de segmentos de dados |

### Encoding de tipos

WebAssembly usa um sistema de encoding compacto para tipos e valores. O encoding é tipicamente representado em hexadecimal no formato binário.

**Tipos de valor** (1 byte):

| Byte | Tipo |
|------|------|
| 0x7F | i32 |
| 0x7E | i64 |
| 0x7D | f32 |
| 0x7C | f64 |
| 0x70 | funcref |
| 0x6F | externref |

**Tipos de função**: precedidos por byte 0x60

```
0x60 <count params> <param types...> <count results> <result types...>
```

**Tipo de bloco**: precedidos por bytes específicos

| Byte | Tipo |
|------|------|
| 0x40 | void (nenhum resultado) |
| 0x7F | i32 |
| 0x7E | i64 |
| 0x7D | f32 |
| 0x7C | f64 |

### LEB128: codificação de inteiros

WebAssembly usa a codificação LEB128 (Little Endian Base 128) para representar inteiros de forma compacta. Essa codificação é particularly eficiente para números pequenos, que são comuns em código compilado.

O princípio é simples: cada byte contém 7 bits de dados e 1 bit de continuação. Se o bit de continuação é 1, há mais um byte seguindo. Para inteiros com sinal, o último bit do byte final é estendido com sinal.

```
Exemplos de encoding LEB128 sem sinal:
1   → 0x01
127 → 0x7F
128 → 0x80 0x01
300 → 0xAC 0x02

Exemplos de encoding LEB128 com sinal:
-1  → 0x7F
-128 → 0x80 0x7F
127 → 0x7F
128 → 0x80 0x00
```

### Seção de funções

A seção de funções é uma das partes mais importantes do módulo. Ela mapeia cada índice de função para um tipo na seção de tipos. O corpo real da função fica na seção de código, separada da seção de funções.

```
Seção de funções:
func_0: type_index_0
func_1: type_index_1
func_2: type_index_0  ;; pode reutilizar o mesmo tipo
...
```

### Seção de código

Cada corpo de função na seção de código contém:

1. Tamanho do corpo (em bytes)
2. Número de variáveis locais
3. Declarações de variáveis locais (tipo e quantidade)
4. Instruções expressas como sequência de opcodes

```
Corpo da função:
<size> <local_decls> <code>

Local declarations:
<declaration_count> <type> <count>
```

### Seção de memória

A memória é definida com limites mínimo e máximo (em páginas de 64 KiB):

```
memory_section:
    limits:
        flag: 0x00 (sem máximo) ou 0x01 (com máximo)
        initial: pages iniciais
        maximum: pages máximos (apenas se flag = 0x01)
```

### Seção de dados

A seção de dados inicializa segmentos da memória linear:

```
data_segment:
    mode: 0x00 (passiva) | 0x01 (ativa, memória 0) | 0x02 (ativa, memória index)
    offset: expressão constante (para segmentos ativos)
    data: bytes de inicialização
```

### Seção de export

As exportações permitem que o módulo expor funções, memórias, tabelas ou globais para o mundo exterior:

```
export:
    name: string (UTF-8)
    kind: 0x00 (função) | 0x01 (tabela) | 0x02 (memória) | 0x03 (global)
    index: índice no respectivo space
```

### Seção de import

As importações permitem que o módulo consuma funcionalidade de outros módulos:

```
import:
    module: string (nome do módulo)
    name: string (nome da importação)
    kind: tipo da importação
    type_index: índice do tipo (para funções)
```

### Custom sections

Seções customizadas (ID 0) permitem informações adicionais sem afetar a semântica do módulo. O nome da seção customizada é uma string UTF-8. As custom sections mais comuns são:

- **name**: mapeia índices para nomes legíveis
- **producers**: informações sobre a ferramenta que gerou o módulo
- **reloc**: informações de relocação para linking

---

## 1.4 Pipeline de compilação

### Visão geral do pipeline

O pipeline de compilação de WebAssembly é fundamentalmente diferente do pipeline tradicional de compilação. Enquanto compiladores tradicionais geram código nativo para uma arquitetura específica, o pipeline do Wasm gera bytecode portável que pode ser executado em qualquer plataforma com um runtime compatível.

O pipeline padrão envolve as seguintes etapas:

```
Código fonte → Compilador → LLVM IR → LLVM backend → .wasm
                                                  ↓
                                            WAT (opcional)
```

### Etapas do compilador

**1. Frontend do compilador**

O frontend é responsável por analisar o código fonte e gerar uma representação intermediária (IR). Dependendo da linguagem de origem, diferentes frontends são usados:

- **C/C++**: Clang (parte do projeto LLVM)
- **Rust**: rustc (compilador nativo do Rust)
- **Go**: TinyGo ou Go WASI
- **AssemblyScript**: compilador dedicado

Cada frontend produz LLVM IR otimizado para o alvo WebAssembly.

**2. LLVM como middle-end**

O LLVM serve como middle-end do pipeline, realizando otimizações independentes de arquitetura. As principais otimizações incluem:

- Eliminação de código morto (DCE)
- Propagação de constantes
- Inline de funções
- Otimização de loops
- Eliminação de redundâncias

**3. Backend do LLVM para WebAssembly**

O backend do LLVM é responsável por gerar o bytecode WebAssembly a partir do LLVM IR. Esse processo inclui:

- Alocação de variáveis locais
- Geração de instruções para a máquina de pilha
- Otimização de padrões de carga/estocagem
- Geração de código para controle de fluxo

### Ferramentas de compilação

**Emscripten**

Emscripten é a ferramenta mais madura para compilar C/C++ para WebAssembly. Ele fornece um compilador compatível com Clang que gera código Wasm a partir de código C/C++ existente.

```c
// hello.c - código fonte original
#include <stdio.h>
#include <emscripten.h>

EMSCRIPTEN_KEEPALIVE
int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

EMSCRIPTEN_KEEPALIVE
void print_result(int result) {
    printf("Fibonacci result: %d\n", result);
}
```

Comando de compilação:

```bash
emcc hello.c -O3 -s WASM=1 -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -o hello.js
```

Isso gera dois arquivos:
- `hello.wasm`: o bytecode WebAssembly
- `hello.js`: o glue code JavaScript para carregar e instanciar o módulo

**Rust com wasm-pack**

Rust tem suporte nativo para WebAssembly e oferece ferramentas dedicadas:

```rust
// lib.rs - biblioteca Rust para Wasm
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a: u32 = 0;
            let mut b: u32 = 1;
            for _ in 2..=n {
                let temp = b;
                b = a + b;
                a = temp;
            }
            b
        }
    }
}

#[wasm_bindgen]
pub fn is_prime(n: u64) -> bool {
    if n < 2 {
        return false;
    }
    if n == 2 {
        return true;
    }
    if n % 2 == 0 {
        return false;
    }
    let mut i = 3;
    while i * i <= n {
        if n % i == 0 {
            return false;
        }
        i += 2;
    }
    true
}

#[wasm_bindgen]
pub fn sum_array(data: &[i32]) -> i64 {
    data.iter().map(|&x| x as i64).sum()
}

#[wasm_bindgen]
pub struct Matrix {
    data: Vec<f64>,
    rows: usize,
    cols: usize,
}

#[wasm_bindgen]
impl Matrix {
    #[wasm_bindgen(constructor)]
    pub fn new(rows: usize, cols: usize) -> Matrix {
        Matrix {
            data: vec![0.0; rows * cols],
            rows,
            cols,
        }
    }

    pub fn get(&self, row: usize, col: usize) -> f64 {
        self.data[row * self.cols + col]
    }

    pub fn set(&mut self, row: usize, col: usize, value: f64) {
        self.data[row * self.cols + col] = value;
    }

    pub fn multiply(&self, other: &Matrix) -> Matrix {
        assert_eq!(self.cols, other.rows);
        let mut result = Matrix::new(self.rows, other.cols);
        for i in 0..self.rows {
            for j in 0..other.cols {
                let mut sum = 0.0;
                for k in 0..self.cols {
                    sum += self.get(i, k) * other.get(k, j);
                }
                result.set(i, j, sum);
            }
        }
        result
    }
}
```

Compilação com wasm-pack:

```bash
wasm-pack build --target web
wasm-pack build --target nodejs
wasm-pack build --target bundler
```

**AssemblyScript**

AssemblyScript é uma linguagem que se parece com TypeScript mas compila diretamente para WebAssembly:

```typescript
// assembly/index.ts
export function fibonacci(n: i32): i32 {
    if (n <= 1) return n;
    let a: i32 = 0;
    let b: i32 = 1;
    for (let i: i32 = 2; i <= n; i++) {
        let temp = b;
        b = a + b;
        a = temp;
    }
    return b;
}

export function matmul(
    a: Float64Array,
    b: Float64Array,
    result: Float64Array,
    m: i32,
    n: i32,
    p: i32
): void {
    for (let i: i32 = 0; i < m; i++) {
        for (let j: i32 = 0; j < p; j++) {
            let sum: f64 = 0;
            for (let k: i32 = 0; k < n; k++) {
                sum += a[i * n + k] * b[k * p + j];
            }
            result[i * p + j] = sum;
        }
    }
}
```

Compilação com AssemblyScript:

```bash
asc assembly/index.ts --outFile build/module.wasm --optimize
```

### Otimizações específicas para Wasm

O bytecode WebAssembly tem características únicas que permitem otimizações específicas:

**1. Eliminação de branches desnecessários**

Como Wasm usa uma pilha de valores, operações como `if/else` podem ser otimizadas para `select` quando o padrão de uso é simples:

```wat
;; Antes da otimização
(if (result i32)
    (i32.gt_s (local.get $a) (local.get $b))
    (then (local.get $a))
    (else (local.get $b))
)

;; Depois da otimização
(i32.select
    (i32.gt_s (local.get $a) (local.get $b))
    (local.get $a)
    (local.get $b)
)
```

**2. Combinación de load/store**

Sequences de load/store adjacentes podem ser combinadas em operações de maior largura:

```wat
;; Dois loads de 32 bits
(i32.load offset=0)
(i32.load offset=4)

;; Potencialmente combinado em um load de 64 bits (quando alinhado)
(i64.load offset=0)
```

**3. Dead code elimination**

A seção de código pode conter código inacessível após branches. Compiladores eficientes removem esse código para reduzir o tamanho do módulo.

---

## 1.5 Módulo, Instância, Memória e Tabela

### O ciclo de vida de um módulo

Um módulo WebAssembly é a unidade fundamental de código. Ele contém todas as definições de funções, tipos, memórias, tabelas e globais necessárias para a execução. No entanto, um módulo por si só não é executável — ele precisa ser instanciado.

O ciclo de vida completo é:

```
Module (texto/binário) → Compile → Compiled Module → Instantiate → Instance
                                        ↓
                                   Validate
                                        ↓
                                   Cache
```

### Módulo compilado vs instância

**Módulo compilado**: resultado do parsing e validação do bytecode. Pode ser armazenado em cache e reutilizado para criar múltiplas instâncias. A compilação é uma operação custosa, mas a instância é rápida.

**Instância**: uma execução concreta do módulo. Cada instância tem seu próprio estado (memória, globais), mas compartilha o código com o módulo compilado.

```javascript
// Exemplo de uso no navegador
async function runWasm() {
    // 1. Buscar o módulo binário
    const response = await fetch('module.wasm');
    const bytes = await response.arrayBuffer();

    // 2. Compilar (pode ser reutilizado)
    const module = await WebAssembly.compile(bytes);

    // 3. Preparar importações
    const importObject = {
        env: {
            memory: new WebAssembly.Memory({ initial: 256 }),
            table: new WebAssembly.Table({ initial: 256, element: 'anyfunc' }),
            add: (a, b) => a + b
        }
    };

    // 4. Instanciar (pode ser feito múltiplas vezes)
    const instance1 = await WebAssembly.instantiate(module, importObject);
    const instance2 = await WebAssembly.instantiate(module, importObject);

    // Cada instância tem sua própria memória
    console.log(instance1.exports.process(42));  // Instância 1
    console.log(instance2.exports.process(99));  // Instância 2
}
```

### Memória linear

A memória linear é o mecanismo pelo qual módulos WebAssembly armazenam e acessam dados. É um bloco contíguo de bytes endereçável que começa no endereço 0 e pode ser expandido em páginas de 64 KiB.

**Características da memória linear**:

- Começa sempre no endereço 0
- Expansível dinamicamente (via `memory.grow`)
- Limite inicial e máximo definidos no módulo ou na criação
- Cada instância tem sua própria memória isolada
- Não pode ser acessada diretamente por código Wasm de fora do módulo

**Layout típico de memória**:

```
Endereço 0x00000000
┌─────────────────────────┐
│  Dados estáticos        │  (seção .data)
├─────────────────────────┤
│  Heap                   │  (alocação dinâmica)
├─────────────────────────┤
│  ...                    │
├─────────────────────────┤
│  Stack                  │  (cresce para baixo)
└─────────────────────────┘
Endereço 0xFFFFFFFF (limite)
```

**Acesso à memória**:

```wat
;; Store: armazenar valor na memória
i32.const 100          ;; endereço
i32.const 42           ;; valor
i32.store offset=0     ;; mem[100] = 42

;; Load: carregar valor da memória
i32.const 100          ;; endereço
i32.load offset=0      ;; empilha mem[100]

;; Operações com endereçamento
i32.load offset=4 align=2   ;; carrega i32 com offset 4, alinhamento 2^2=4
i32.load8_s offset=0        ;; carrega byte com extensão de sinal
i32.load8_u offset=0        ;; carrega byte com extensão sem sinal
i32.load16_s offset=0       ;; carrega 16 bits com extensão de sinal
i32.load16_u offset=0       ;; carrega 16 bits com extensão sem sinal
```

**Crescimento da memória**:

```wat
;; Verificar tamanho atual
memory.size    ;; retorna número de páginas

;; Crescer a memória
memory.grow    ;; empilha número de páginas a adicionar
               ;; retorna tamanho anterior ou -1 se falhar
```

Em JavaScript:

```javascript
const memory = new WebAssembly.Memory({
    initial: 256,   // 256 páginas = 16 MiB
    maximum: 512    // 512 páginas = 32 MiB (opcional)
});

// Verificar tamanho
console.log(memory.buffer.byteLength);  // 16777216 (16 MiB)

// Crescer (cuidado: invalida buffer anterior)
const oldPages = memory.grow(256);
console.log(memory.buffer.byteLength);  // 33554432 (32 MiB)
```

### Tabela de funções

A tabela de funções é um array de referências que pode conter referências a funções. Ela é fundamental para implementar dispatch dinâmico, funções callback e ponteiros para funções.

**Características**:

- Indexada por inteiros não-negativos
- Tipada: cada elemento é uma referência a função (funcref)
- Inicializável via seção de elementos
- Pode ser exportada ou importada
- Limite inicial e máximo definidos

```wat
;; Definição de tabela
(module
    (table 10 funcref)  ;; tabela com 10 slots

    ;; Funções
    (func $f1 (result i32) i32.const 1)
    (func $f2 (result i32) i32.const 2)
    (func $f3 (result i32) i32.const 3)

    ;; Inicialização da tabela
    (elem (i32.const 0) $f1 $f2 $f3)

    ;; Função que usa a tabela
    (func $dispatch (param $index i32) (result i32)
        (call_indirect (result i32)
            (local.get $index)
        )
    )

    (export "dispatch" (func $dispatch))
)
```

### Variáveis globais

Variáveis globais são valores que podem ser lidos e escritos pelo código e pelo host. Elas são tipadas e imutáveis em termos de tipo (mas mutáveis em termos de valor, exceto quando declaradas como imutáveis).

```wat
(module
    ;; Global mutável
    (global $counter (mut i32) (i32.const 0))

    ;; Global imutável
    (global $max_size i32 (i32.const 1024))

    ;; Função que usa global
    (func $increment (result i32)
        (global.set $counter
            (i32.add
                (global.get $counter)
                (i32.const 1)
            )
        )
        (global.get $counter)
    )

    (export "increment" (func $increment))
)
```

---

## 1.6 Integração com o navegador

### API principal do navegador

O navegador fornece a API `WebAssembly` que permite carregar, compilar e instanciar módulos. Essa API é definida pelo W3C e está disponível em todos os navegadores modernos.

**Carregamento e instanciação**:

```javascript
// Forma assíncrona (recomendada)
async function loadWasm() {
    try {
        // Buscar e compilar em paralelo
        const [module, importObject] = await Promise.all([
            WebAssembly.compileStreaming(fetch('module.wasm')),
            prepareImports()
        ]);

        // Instanciar
        const instance = await WebAssembly.instantiate(module, importObject);

        // Usar
        const result = instance.exports.myFunction(42);
        console.log('Resultado:', result);
    } catch (error) {
        console.error('Erro ao carregar Wasm:', error);
    }
}

// Forma síncrona (menor suporte, não recomendada)
function loadWasmSync() {
    const bytes = new Uint8Array(/* bytes do módulo */);
    const module = new WebAssembly.Module(bytes);
    const instance = new WebAssembly.Instance(module, {});
    return instance.exports;
}
```

**Preparação de importações**:

```javascript
function prepareImports() {
    // Memória compartilhada
    const memory = new WebAssembly.Memory({
        initial: 256,
        maximum: 512,
        shared: true  // para uso com threads
    });

    // Tabela de funções
    const table = new WebAssembly.Table({
        initial: 256,
        maximum: 512,
        element: 'anyfunc'
    });

    // Funções importadas
    const imports = {
        env: {
            memory: memory,
            table: table,

            // Função de log
            consoleLog: (value) => {
                console.log('Wasm diz:', value);
            },

            // Alocação de memória
            malloc: (size) => {
                // Implementação simplificada
                return allocateMemory(size);
            },

            // Dealocação de memória
            free: (ptr) => {
                freeMemory(ptr);
            },

            // Abort
            abort: (msg) => {
                throw new Error(`Wasm abort: ${msg}`);
            }
        },

        // Módulo de tempo
        wasi_snapshot_preview1: {
            fd_write: (fd, iovs, iovsLen, nwritten) => {
                // Implementação de escrita
                return 0;
            },
            fd_read: (fd, iovs, iovsLen, nread) => {
                // Implementação de leitura
                return 0;
            }
        }
    };

    return imports;
}
```

### Streaming compilation

O `compileStreaming` permite compilar o módulo WebAssembly diretamente a partir do stream de rede, sem precisar esperar o download completo:

```javascript
// Streaming compilation (otimizado)
const response = await fetch('module.wasm');
const module = await WebAssembly.compileStreaming(response);

// Comparação com a forma tradicional
const response2 = await fetch('module.wasm');
const bytes = await response2.arrayBuffer();
const module2 = await WebAssembly.compile(bytes);
```

O `compileStreaming` é mais eficiente porque pode começar a compilar antes de o download estar completo, paralelizando download e compilação.

### Error handling

A API WebAssembly fornece erros específicos para diferentes situações:

```javascript
try {
    const module = await WebAssembly.compile(bytes);
    const instance = await WebAssembly.instantiate(module, imports);
} catch (error) {
    if (error instanceof WebAssembly.CompileError) {
        console.error('Erro de compilação:', error.message);
    } else if (error instanceof WebAssembly.LinkError) {
        console.error('Erro de linkage:', error.message);
    } else if (error instanceof WebAssembly.RuntimeError) {
        console.error('Erro de runtime:', error.message);
    } else {
        console.error('Erro desconhecido:', error);
    }
}
```

**Tipos de erro**:

| Erro | Quando ocorre |
|------|---------------|
| `CompileError` | Bytecode inválido, seção malformada |
| `LinkError` | Importações não correspondem |
| `RuntimeError` | Divisão por zero, out of bounds |

### Workers e Threads

WebAssembly pode ser usado em Web Workers para paralelismo real:

```javascript
// main.js
const worker = new Worker('worker.js');

worker.onmessage = (event) => {
    console.log('Resultado do worker:', event.data);
};

worker.postMessage({ data: largeArray });

// worker.js
self.onmessage = async (event) => {
    const response = await fetch('processor.wasm');
    const module = await WebAssembly.compileStreaming(response);

    const memory = new WebAssembly.Memory({
        initial: 256,
        shared: true,
        maximum: 512
    });

    const instance = await WebAssembly.instantiate(module, {
        env: { memory: memory }
    });

    // Processar dados
    const result = instance.exports.process(event.data);
    self.postMessage(result);
};
```

### SharedArrayBuffer e Atomics

Para uso com threads, WebAssembly pode operar sobre memória compartilhada:

```javascript
// Memória compartilhada entre threads
const memory = new WebAssembly.Memory({
    initial: 256,
    maximum: 512,
    shared: true
});

// Threads diferentes podem ler/escrever na mesma memória
// Usando Atomics para sincronização
```

---

## 1.7 WebAssembly no lado do servidor

### O movimento server-side

Embora o WebAssembly tenha sido projetado inicialmente para o navegador, sua portabilidade e segurança o tornam atrativo para o lado do servidor. O conceito é simples: se o Wasm pode rodar de forma segura e portável no navegador, por que não em outros ambientes?

Os principais motivos para usar Wasm no servidor incluem:

1. **Segurança**: sandbox forte sem necessidade de containerização pesada
2. **Portabilidade**: o mesmo binário roda em qualquer plataforma com um runtime Wasm
3. **Performance**: instâncias rápidas, cold start baixo
4. **Isolamento**: cada instância é isolada, ideal para multi-tenancy
5. **Polyglot**: múltiplas linguagens compilam para o mesmo alvo

### Runtimes server-side

**Wasmtime**

Wasmtime é um runtime WebAssembly criado pela Bytecode Alliance. Ele implementa WASI e é otimizado para segurança e performance.

```bash
# Instalação
curl https://wasmtime.dev/install.sh -sSf | bash

# Execução de um módulo
wasmtime app.wasm

# Com argumentos
wasmtime app.wasm -- arg1 arg2

# Com diretórios mapeados
wasmtime app.wasm --dir .::current_dir
```

**Wasmer**

Wasmer é outro runtime popular que suporta múltiplos backends de compilação (Cranelift, LLVM, Singlepass).

```bash
# Instalação
curl https://get.wasmer.io -sSfL | sh

# Execução
wasmer run app.wasm

# Com permissões
wasmer run app.wasm --dir . --env KEY=VALUE
```

**WasmEdge**

WasmEdge é um runtime focado em edge computing e IoT, com suporte a extensões para machine learning.

```bash
# Instalação
curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install.sh | bash

# Execução
wasmedge app.wasm
```

### WASI: a interface de sistema

WASI (WebAssembly System Interface) é o padrão que permite que módulos Wasm acessem funcionalidades do sistema operacional de forma segura e portável. WASI é baseado em um modelo de capacidades (capability-based), onde cada módulo só pode acessar recursos que lhe foram explicitamente concedidos.

```rust
// Exemplo de aplicação WASI em Rust
use std::fs;
use std::io::{self, Read, Write};

fn main() -> io::Result<()> {
    // Ler arquivo (requer permissão de diretório)
    let content = fs::read_to_string("input.txt")?;
    println!("Arquivo lido: {} bytes", content.len());

    // Escrever arquivo (requer permissão de diretório)
    fs::write("output.txt", content.to_uppercase())?;

    // Ler variável de ambiente
    if let Ok(name) = std::env::var("USER_NAME") {
        println!("Olá, {}!", name);
    }

    // Obter tempo atual
    let now = std::time::SystemTime::now();
    println!("Tempo: {:?}", now);

    // Gerar número aleatório (se disponível)
    println!("Aleatório: {}", rand::random::<u32>());

    Ok(())
}
```

Compilação para WASI:

```bash
# Rust
rustup target add wasm32-wasi
cargo build --target wasm32-wasi --release

# C com wasi-sdk
/opt/wasi-sdk/bin/clang -o app.wasm app.c

# Go
GOOS=wasip1 GOARCH=wasm go build -o app.wasm .
```

### Comparação com containers

| Aspecto | Docker/Containers | WebAssembly |
|---------|-------------------|-------------|
| Tamanho da imagem | 10MB - 1GB | 10KB - 10MB |
| Cold start | 100ms - 5s | < 1ms |
| Isolamento | Namespace + cgroups | Sandbox + capability model |
| Segurança | Kernel Linux | Linguagem + runtime |
| Portabilidade | Linux (na prática) | Multiplataforma |
| Multi-tenancy | Possível mas complexo | Natural |

### Casos de uso no servidor

**Edge Computing**: Wasm é ideal para edge computing devido ao cold start baixo e ao tamanho reduzido dos módulos.

**Plugins**: Wasm pode ser usado como mecanismo de plugins seguro, permitindo que usuários executem código customizado sem acesso total ao sistema.

**Serverless**: Plataformas como Fermyon Spin e Cosmonic usam Wasm para serverless com cold start quase instantâneo.

**Multi-tenancy**: Em ambientes onde múltiplos usuários executam código não confiável, o isolamento do Wasm é fundamental.

---

## 1.8 WASI Preview

### O que é WASI

WASI (WebAssembly System Interface) é um padrão que define como módulos WebAssembly interagem com o sistema operacional. O objetivo do WASI é fornecer uma interface portável e segura que funcione em diferentes sistemas operacionais.

O design do WASI é influenciado por um modelo de capacidades (capability-based), inspirado no projeto Capsicum da Universidade de Cambridge. Nesse modelo, acesso a recursos é concedido explicitamente, em vez de ser baseado em identidade (como o modelo Unix tradicional).

### WASI Preview 1

O WASI Preview 1 é a versão estável e amplamente implementada. Ele fornece interface simples baseada em descritores de arquivo (file descriptors).

**Principais APIs do Preview 1**:

```
args_get        → obter argumentos de linha de comando
args_sizes_get  → obter tamanho dos argumentos
environ_get     → obter variáveis de ambiente
environ_sizes_get → obter tamanho das variáveis de ambiente
clock_time_get  → obter tempo do relógio
fd_close        → fechar descritor de arquivo
fd_fdstat_get   → obter status do descritor
fd_fdstat_set_flags → alterar flags do descritor
fd_prestat_dir_name → obter nome do diretório pré-aberto
fd_prestat_get  → obter informação do descritor pré-aberto
fd_read         → ler dados
fd_readdir      → ler diretório
fd_seek         → posicionar ponteiro
fd_sync         → sincronizar dados
fd_write        → escrever dados
path_create_directory → criar diretório
path_filestat_get → obter status de arquivo
path_filestat_set_times → alterar timestamps
path_link       → criar link
path_open       → abrir arquivo
path_readlink   → ler link
path_remove_directory → remover diretório
path_rename     → renomear
path_symlink    → criar link simbólico
path_unlink_file → remover arquivo
poll_oneoff     → aguardar eventos
proc_exit       → encerrar processo
proc_raise      → enviar sinal
random_get      → obter bytes aleatórios
sched_yield     → ceder escalonamento
sock_accept     → aceitar conexão
sock_address_local_get → obter endereço local
sock_address_remote_get → obter endereço remoto
sock_bind       → vincular socket
sock_close       → fechar socket
sock_connect    → conectar
sock_getsockopt → obter opções de socket
sock_listen     → aguardar conexões
sock_recv       → receber dados
sock_send       → enviar dados
sock_setsockopt → definir opções de socket
sock_shutdown   → encerrar socket
```

### WASI Preview 2

O WASI Preview 2 é uma evolução significativa que introduz o Component Model e permite composição de módulos.

**Mudanças principais**:

1. **Component Model**: módulos podem ser compostos usando interfaces tipadas
2. **Streams e Future**: modelos de I/O assíncronos
3. **WIT (WebAssembly Interface Type)**: linguagem para definir interfaces
4. **Better async**: suporte nativo a operações assíncronas

**Exemplo de interface WIT**:

```wit
// examples/hello.wit
package example:hello;

interface greeting {
    record message {
        content: string,
        language: string,
    }

    greet: func(name: string) -> string;
    translate: func(msg: message) -> string;
}

world hello-world {
    export greeting;
}
```

### Modelo de segurança do WASI

O WASI implementa segurança através de:

**1. Restrição de diretórios**

```bash
# Permissões granulares
wasmtime app.wasm --dir /data::read          # somente leitura
wasmtime app.wasm --dir /data::read,write    # leitura e escrita
wasmtime app.wasm --dir /tmp::read,write     # diretório temporário
wasmtime app.wasm --mapdir /output::/data    # mapeamento de diretório
```

**2. Variáveis de ambiente controladas**

```bash
wasmtime app.wasm --env KEY=VALUE            # exportar variável
wasmtime app.wasm --env KEY=                 # variável vazia
```

**3. Redes restritas**

```bash
wasmtime app.wasm --tcplisten 0.0.0.0:8080  # aceitar conexões TCP
wasmtime app.wasm --tcp-connect example.com:80  # conectar TCP
wasmtime app.wasm --udp-bind 0.0.0.0:9000   # vincular UDP
```

**4. clocks**

```bash
wasmtime app.wasm --tcpproxy 0.0.0.0:8080   # proxy TCP
```

### Exemplo completo de aplicação WASI

```rust
// src/main.rs - aplicação WASI completa
use std::env;
use std::fs;
use std::io::{self, Read, Write};
use std::path::Path;

fn main() -> io::Result<()> {
    // 1. Argumentos de linha de comando
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Uso: {} <input_dir> <output_dir>", args[0]);
        std::process::exit(1);
    }

    let input_dir = &args[1];
    let output_dir = &args[2];

    // 2. Verificar diretório de entrada
    if !Path::new(input_dir).exists() {
        eprintln!("Diretório de entrada não existe: {}", input_dir);
        std::process::exit(1);
    }

    // 3. Criar diretório de saída
    fs::create_dir_all(output_dir)?;

    // 4. Ler variáveis de ambiente
    let prefix = env::var("OUTPUT_PREFIX").unwrap_or_default();
    let verbose = env::var("VERBOSE").map(|v| v == "true").unwrap_or(false);

    // 5. Listar arquivos no diretório de entrada
    let entries = fs::read_dir(input_dir)?;

    for entry in entries {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            if verbose {
                println!("Processando: {}", path.display());
            }

            // Ler conteúdo
            let content = fs::read(&path)?;

            // Processar (exemplo: converter para maiúsculas se for texto)
            let processed = if is_text_file(&path) {
                String::from_utf8_lossy(&content).to_uppercase().into_bytes()
            } else {
                content
            };

            // Escrever no diretório de saída
            let filename = path.file_name().unwrap();
            let output_path = Path::new(output_dir).join(format!("{}{}", prefix, filename.to_string_lossy()));
            fs::write(&output_path, &processed)?;

            if verbose {
                println!("  Escrito: {}", output_path.display());
            }
        }
    }

    // 6. Registrar estatísticas
    let stats_path = Path::new(output_dir).join("stats.txt");
    let timestamp = format!("{:?}", std::time::SystemTime::now());
    fs::write(&stats_path, format!(
        "Processado em: {}\nInput: {}\nOutput: {}\n",
        timestamp, input_dir, output_dir
    ))?;

    println!("Processamento concluído com sucesso!");
    Ok(())
}

fn is_text_file(path: &Path) -> bool {
    path.extension()
        .map(|ext| {
            let ext = ext.to_string_lossy().to_lowercase();
            matches!(ext.as_str(), "txt" | "md" | "json" | "toml" | "yaml" | "yml")
        })
        .unwrap_or(false)
}
```

---

## 1.9 Comparação com outras tecnologias

### WebAssembly vs JavaScript

A comparação mais comum e relevante. JavaScript continua sendo a linguagem principal da Web, mas WebAssembly preenche lacunas específicas de performance.

| Aspecto | JavaScript | WebAssembly |
|---------|-----------|-------------|
| Compilação | JIT / AOT | AOT (ahead of time) |
| Tipagem | Dinâmica | Estática |
| Velocidade de parse | Lenta (texto) | Rápida (binário) |
| Performance numérica | Moderada | Alta |
| Velocidade de cold start | Média | Muito alta |
| Ecossistema | Extremamente rico | Crescendo |
| Depuração | Excelente | Em melhoria |
| Acesso ao DOM | Nativo | Via JavaScript |
| Uso no servidor | Node.js | WASI |

**Quando usar JavaScript**:
- Aplicações com interface rica
- Código que interage intensamente com o DOM
- Prototipagem rápida
- Scripts e automação

**Quando usar WebAssembly**:
- Processamento de dados pesado
- Codec de áudio/vídeo
- Criptografia
- Simulações e física
- Port de código C/C++ existente
- Plugins de terceiros

### WebAssembly vs Java/.NET bytecode

| Aspecto | Java/.NET | WebAssembly |
|---------|-----------|-------------|
| Alvo | VM específica | Qualquer runtime |
| Segurança | JVM sandbox | Capability-based |
| Garbage Collection | Sim | Não (MVP) |
| Peso do runtime | 100MB+ | KB a MB |
| Cold start | Alto (JVM init) | Muito baixo |
| Ecossistema | Maduro | Em crescimento |

### WebAssembly vs NaCl/PNaCl

| Aspecto | NaCl/PNaCl | WebAssembly |
|---------|-----------|-------------|
| Status | Descontinuado | Ativo |
| Portabilidade | Chrome apenas | Todos os navegadores |
| Portabilidade CPU | PNaCl: sim | Wasm: sim |
| Segurança | Sandbox baseado em páginas | Sandbox baseado em módulos |
| Formato | ELF modificado | Formato próprio |

### WebAssembly vs GLSL/HLSL (shaders)

| Aspecto | Shaders (GLSL/HLSL) | WebAssembly |
|---------|---------------------|-------------|
| Propósito | Renderização gráfica | Computação genérica |
| Execução | GPU | CPU/Wasm runtime |
| Paralelismo | Massivo (SIMT) | Limitado (SIMD opcional) |
| Memória | Restrita | Linear, expansível |

### WebAssembly vs Rust (nativo)

| Aspecto | Rust nativo | Rust + Wasm |
|---------|-------------|-------------|
| Target | x86_64, ARM, etc. | wasm32-wasi, wasm32-unknown-unknown |
| Biblioteca std | Completa | Parcial |
| FFI | C ABI | WASI imports |
| Binário | Executável nativo | .wasm |
| Performance | 100% (baseline) | 70-95% |
| Uso | Aplicações desktop/server | Navegador, edge, plugins |

### WebAssembly vs Docker

| Aspecto | Docker | WebAssembly |
|---------|--------|-------------|
| Abstração | Sistema operacional | Interface de sistema |
| Tamanho | 10MB - 1GB | 10KB - 10MB |
| Isolamento | Namespace, cgroups | Sandbox, capability model |
| Cold start | 100ms - 5s | < 1ms |
| Portabilidade | Linux | Multiplataforma |
| Multi-tenancy | Complexo | Natural |
| Ecossistema | Maduro | Em crescimento |

### Quando escolher WebAssembly

WebAssembly é a escolha certa quando:

1. **Performance é crítica**: codecs, criptografia, simulações
2. **Segurança é prioridade**: plugins de terceiros, sandbox de código
3. **Portabilidade importa**: o mesmo binário em múltiplas plataformas
4. **Cold start importa**: edge computing, serverless
5. **Multi-tenancy é necessário**: SaaS com código de usuário
6. **Código legado precisa ser portado**: C/C++ existente

WebAssembly NÃO é a escolha certa quando:

1. **Acesso ao DOM é necessário**: use JavaScript
2. **Ecossistema maduro é essencial**: use JavaScript, Python, etc.
3. **Equipe não tem experiência com linguagens compiladas**: curva de aprendizado
4. **A aplicação é simples**: overhead do toolchain não compensa
5. **GC é essencial para o caso de uso**: Wasm ainda não tem GC integrado

---

## 1.10 Exemplo WAT completo

### Projeto: Calculadora com memória persistente

Este exemplo demonstra um módulo WebAssembly completo que implementa uma calculadora com memória persistente, demonstrando todos os conceitos discutidos neste capítulo.

```wat
;; calculator.wat
;; Uma calculadora completa em WebAssembly
;; Demonstra: memória, tabelas, globais, importações, exportações

(module
    ;; ============================================================
    ;; Seção de Importações
    ;; ============================================================

    ;; Importar memória do host
    (import "env" "memory" (memory 1 16))

    ;; Importar função de log do host
    (import "env" "log" (func $log (param i32)))

    ;; Importar função de leitura do host
    (import "env" "readInput" (func $readInput (result i32)))

    ;; ============================================================
    ;; Seção de Tipos
    ;; ============================================================

    ;; Tipo para operações binárias: (i32, i32) -> i32
    (type $binop (func (param i32 i32) (result i32)))

    ;; Tipo para operações unárias: (i32) -> i32
    (type $unop (func (param i32) (result i32)))

    ;; Tipo para funções de processamento
    (type $processor (func (param i32) (result i32)))

    ;; ============================================================
    ;; Seção de Tabelas
    ;; ============================================================

    ;; Tabela para operações binárias (8 operações)
    (table 8 funcref)

    ;; ============================================================
    ;; Seção de Memória (já importada)
    ;; ============================================================

    ;; Layout da memória:
    ;; [0x0000 - 0x00FF] Área de constantes
    ;; [0x0100 - 0x01FF] Área de variáveis globais
    ;; [0x0200 - 0x0FFF] Stack de cálculos
    ;; [0x1000 - 0xFFFF] Área de dados

    ;; ============================================================
    ;; Seção de Variáveis Globais
    ;; ============================================================

    ;; Contador de operações realizadas
    (global $opCount (mut i32) (i32.const 0))

    ;; Contador de erros
    (global $errorCount (mut i32) (i32.const 0))

    ;; Último resultado
    (global $lastResult (mut i32) (i32.const 0))

    ;; Topo da stack de cálculos
    (global $stackTop (mut i32) (i32.const 0x0200))

    ;; ============================================================
    ;; Seção de Exportações
    ;; ============================================================

    ;; Exportar funções principais
    (export "add" (func $add))
    (export "subtract" (func $subtract))
    (export "multiply" (func $multiply))
    (export "divide" (func $divide))
    (export "modulo" (func $modulo))
    (export "power" (func $power))
    (export "abs" (func $abs))
    (export "negate" (func $negate))

    ;; Exportar funções de stack
    (export "push" (func $push))
    (export "pop" (func $pop))
    (export "peek" (func $peek))
    (export "clear" (func $clear))

    ;; Exportar funções de informação
    (export "getOpCount" (func $getOpCount))
    (export "getErrorCount" (func $getErrorCount))
    (export "getLastResult" (func $getLastResult))

    ;; Exportar memória para inspeção
    (export "memory" (memory 0))

    ;; ============================================================
    ;; Seção de Elementos (inicialização da tabela)
    ;; ============================================================

    ;; Tabela de operações binárias
    ;; Índice 0: add
    ;; Índice 1: subtract
    ;; Índice 2: multiply
    ;; Índice 3: divide
    ;; Índice 4: modulo
    ;; Índice 5: power
    ;; Índice 6: bitwise and
    ;; Índice 7: bitwise or
    (elem (i32.const 0)
        $add $subtract $multiply $divide
        $modulo $power $bitand $bitor
    )

    ;; ============================================================
    ;; Funções Internas (não exportadas)
    ;; ============================================================

    ;; Calcular potência (exponenciação por multiplicação sucessiva)
    (func $pow (param $base i32) (param $exp i32) (result i32)
        (local $result i32)
        (local $i i32)

        (local.set $result (i32.const 1))
        (local.set $i (i32.const 0))

        (block $break
            (loop $loop
                ;; Se i >= exp, sair do loop
                (br_if $break
                    (i32.ge_u (local.get $i) (local.get $exp))
                )

                ;; result = result * base
                (local.set $result
                    (i32.mul (local.get $result) (local.get $base))
                )

                ;; i++
                (local.set $i
                    (i32.add (local.get $i) (i32.const 1))
                )

                (br $loop)
            )
        )

        (local.get $result)
    )

    ;; Verificar se o divisor é zero
    (func $checkDivisor (param $divisor i32) (result i32)
        (if (result i32)
            (i32.eqz (local.get $divisor))
            (then
                ;; Incrementar contador de erros
                (global.set $errorCount
                    (i32.add (global.get $errorCount) (i32.const 1))
                )
                (i32.const 0)  ;; retornar 0 como erro
            )
            (else
                (i32.const 1)  ;; divisor válido
            )
        )
    )

    ;; Incrementar contador de operações
    (func $incOpCount
        (global.set $opCount
            (i32.add (global.get $opCount) (i32.const 1))
        )
    )

    ;; ============================================================
    ;; Operações Aritméticas Básicas
    ;; ============================================================

    ;; Adição
    (func $add (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.add (local.get $a) (local.get $b))
    )

    ;; Subtração
    (func $subtract (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.sub (local.get $a) (local.get $b))
    )

    ;; Multiplicação
    (func $multiply (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.mul (local.get $a) (local.get $b))
    )

    ;; Divisão (com verificação de zero)
    (func $divide (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)

        ;; Verificar se divisor é válido
        (if (i32.eqz (call $checkDivisor (local.get $b)))
            (then
                ;; Divisor é zero, logar erro
                (call $log (i32.const -1))
                (return (i32.const 0))
            )
        )

        ;; Divisão com sinal
        (i32.div_s (local.get $a) (local.get $b))
    )

    ;; Módulo (resto da divisão)
    (func $modulo (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)

        ;; Verificar se divisor é válido
        (if (i32.eqz (call $checkDivisor (local.get $b)))
            (then
                (call $log (i32.const -1))
                (return (i32.const 0))
            )
        )

        ;; Resto com sinal
        (i32.rem_s (local.get $a) (local.get $b))
    )

    ;; Potência
    (func $power (param $base i32) (param $exp i32) (result i32)
        (call $incOpCount)
        (call $pow (local.get $base) (local.get $exp))
    )

    ;; ============================================================
    ;; Operações Bitwise
    ;; ============================================================

    ;; AND bit a bit
    (func $bitand (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.and (local.get $a) (local.get $b))
    )

    ;; OR bit a bit
    (func $bitor (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.or (local.get $a) (local.get $b))
    )

    ;; XOR bit a bit
    (func $bitxor (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.xor (local.get $a) (local.get $b))
    )

    ;; NOT bit a bit (unário)
    (func $bitnot (param $a i32) (result i32)
        (call $incOpCount)
        (i32.xor (local.get $a) (i32.const -1))
    )

    ;; Shift left
    (func $shl (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.shl (local.get $a) (local.get $b))
    )

    ;; Shift right aritmético
    (func $shr_s (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.shr_s (local.get $a) (local.get $b))
    )

    ;; Shift right lógico
    (func $shr_u (param $a i32) (param $b i32) (result i32)
        (call $incOpCount)
        (i32.shr_u (local.get $a) (local.get $b))
    )

    ;; ============================================================
    ;; Operações Unárias
    ;; ============================================================

    ;; Valor absoluto
    (func $abs (param $a i32) (result i32)
        (call $incOpCount)

        (if (result i32)
            (i32.lt_s (local.get $a) (i32.const 0))
            (then
                (i32.sub (i32.const 0) (local.get $a))
            )
            (else
                (local.get $a)
            )
        )
    )

    ;; Negação
    (func $negate (param $a i32) (result i32)
        (call $incOpCount)
        (i32.sub (i32.const 0) (local.get $a))
    )

    ;; ============================================================
    ;; Funções de Stack
    ;; ============================================================

    ;; Empilhar valor
    (func $push (param $value i32)
        (local $addr i32)

        ;; Calcular endereço
        (local.set $addr (global.get $stackTop))

        ;; Armazenar valor
        (i32.store (local.get $addr) (local.get $value))

        ;; Avançar ponteiro (4 bytes por i32)
        (global.set $stackTop
            (i32.add (local.get $addr) (i32.const 4))
        )
    )

    ;; Desempilhar valor
    (func $pop (result i32)
        (local $addr i32)
        (local $value i32)

        ;; Verificar se a stack não está vazia
        (if (i32.le_u (global.get $stackTop) (i32.const 0x0200))
            (then
                ;; Stack vazia, retornar 0
                (return (i32.const 0))
            )
        )

        ;; Decrementar ponteiro
        (global.set $stackTop
            (i32.sub (global.get $stackTop) (i32.const 4))
        )

        ;; Calcular endereço
        (local.set $addr (global.get $stackTop))

        ;; Carregar valor
        (local.set $value (i32.load (local.get $addr)))

        (local.get $value)
    )

    ;; Ver topo da stack (sem desempilhar)
    (func $peek (result i32)
        (local $addr i32)

        ;; Verificar se a stack não está vazia
        (if (i32.le_u (global.get $stackTop) (i32.const 0x0200))
            (then
                (return (i32.const 0))
            )
        )

        ;; Calcular endereço do topo
        (local.set $addr
            (i32.sub (global.get $stackTop) (i32.const 4))
        )

        ;; Retornar valor
        (i32.load (local.get $addr))
    )

    ;; Limpar stack
    (func $clear
        (global.set $stackTop (i32.const 0x0200))
    )

    ;; ============================================================
    ;; Funções de Informação
    ;; ============================================================

    ;; Obter contagem de operações
    (func $getOpCount (result i32)
        (global.get $opCount)
    )

    ;; Obter contagem de erros
    (func $getErrorCount (result i32)
        (global.get $errorCount)
    )

    ;; Obter último resultado
    (func $getLastResult (result i32)
        (global.get $lastResult)
    )

    ;; ============================================================
    ;; Função de Inicialização
    ;; ============================================================

    ;; Função start (executada na instanciação)
    (func $init
        ;; Inicializar variáveis
        (global.set $opCount (i32.const 0))
        (global.set $errorCount (i32.const 0))
        (global.set $lastResult (i32.const 0))
        (global.set $stackTop (i32.const 0x0200))

        ;; Limpar memória de dados
        (memory.fill (i32.const 0x1000) (i32.const 0) (i32.const 0xF000))
    )

    ;; ============================================================
    ;; Seção de Start
    ;; ============================================================

    (start $init)
)
```

### Usando o módulo

**Em JavaScript (navegador)**:

```javascript
async function initCalculator() {
    const response = await fetch('calculator.wasm');
    const bytes = await response.arrayBuffer();

    const importObject = {
        env: {
            memory: new WebAssembly.Memory({
                initial: 1,
                maximum: 16
            }),
            log: (value) => {
                console.log('Wasm log:', value);
            },
            readInput: () => {
                return parseInt(prompt('Digite um número:')) || 0;
            }
        }
    };

    const { instance } = await WebAssembly.instantiate(bytes, importObject);
    const calc = instance.exports;

    // Usar a calculadora
    console.log('5 + 3 =', calc.add(5, 3));           // 8
    console.log('10 - 4 =', calc.subtract(10, 4));    // 6
    console.log('6 * 7 =', calc.multiply(6, 7));      // 42
    console.log('15 / 3 =', calc.divide(15, 3));      // 5
    console.log('17 % 5 =', calc.modulo(17, 5));      // 2
    console.log('2^10 =', calc.power(2, 10));         // 1024
    console.log('|-5| =', calc.abs(-5));               // 5
    console.log('-7 =', calc.negate(7));               // -7

    // Usar a stack
    calc.push(10);
    calc.push(20);
    calc.push(30);
    console.log('Topo:', calc.peek());                 // 30
    console.log('Pop:', calc.pop());                   // 30
    console.log('Pop:', calc.pop());                   // 20

    // Informações
    console.log('Operações:', calc.getOpCount());
    console.log('Erros:', calc.getErrorCount());
}
```

**Compilando com WABT**:

```bash
# Converter WAT para WASM
wat2wasm calculator.wasm -o calculator.wasm

# Decompor WASM de volta para WAT (para análise)
wasm2wat calculator.wasm -o calculator_decompiled.wat

# Validar o módulo
wasm-validate calculator.wasm
```

---

## 1.11 Ferramentas do ecossistema

### Compiladores e ferramentas de compilação

O ecossistema WebAssembly dispõe de diversas ferramentas para compilar código de diferentes linguagens para Wasm.

**Emscripten — compilação de C/C++**

Emscripten é a ferramenta mais madura para compilar código C/C++ para WebAssembly. Ele fornece um toolchain completo que inclui Clang, LLVM e bibliotecas portadas.

Instalação e configuração:

```bash
# Clonar repositório
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk

# Instalar e ativar
./emsdk install latest
./emsdk activate latest
source ./emsdk_env.sh

# Verificar instalação
emcc --version
```

Uso básico:

```c
// math_utils.c
#include <math.h>
#include <emscripten.h>

EMSCRIPTEN_KEEPALIVE
double circle_area(double radius) {
    return M_PI * radius * radius;
}

EMSCRIPTEN_KEEPALIVE
double circle_circumference(double radius) {
    return 2 * M_PI * radius;
}

EMSCRIPTEN_KEEPALIVE
double sphere_volume(double radius) {
    return (4.0 / 3.0) * M_PI * radius * radius * radius;
}

EMSCRIPTEN_KEEPALIVE
double distance_3d(double x1, double y1, double z1,
                   double x2, double y2, double z2) {
    double dx = x2 - x1;
    double dy = y2 - y1;
    double dz = z2 - z1;
    return sqrt(dx * dx + dy * dy + dz * dz);
}
```

Compilação com diferentes otimizações:

```bash
# Sem otimização (debug)
emcc math_utils.c -o math_utils.js \
    -s EXPORTED_FUNCTIONS='["_circle_area", "_circle_circumference", "_sphere_volume", "_distance_3d"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]'

# Otimização básica
emcc math_utils.c -O1 -o math_utils.js \
    -s EXPORTED_FUNCTIONS='["_circle_area", "_circle_circumference"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]'

# Otimização máxima
emcc math_utils.c -O3 -o math_utils.js \
    -s EXPORTED_FUNCTIONS='["_circle_area", "_circle_circumference", "_sphere_volume", "_distance_3d"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ALLOW_MEMORY_GROWTH=1

# Tamanho mínimo
emcc math_utils.c -Os -o math_utils.js \
    -s EXPORTED_FUNCTIONS='["_circle_area", "_circle_circumference"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s ENVIRONMENT='web'

# Apenas WASM (sem JS glue)
emcc math_utils.c -O3 -o math_utils.html \
    -s EXPORTED_FUNCTIONS='["_circle_area", "_circle_circumference", "_sphere_volume"]' \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s SINGLE_FILE=1 \
    -s ENVIRONMENT='web'
```

Uso no navegador:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Math Utils WASM</title>
</head>
<body>
    <h1>Calculadora de Geometria</h1>

    <div>
        <label>Raio: <input type="number" id="radius" value="5"></label>
    </div>

    <button onclick="calcular()">Calcular</button>

    <div id="results"></div>

    <script src="math_utils.js"></script>
    <script>
        Module.onRuntimeInitialized = function() {
            // Usar cwrap para criar wrappers tipados
            const circleArea = Module.cwrap('circle_area', 'number', ['number']);
            const circleCircumference = Module.cwrap('circle_circumference', 'number', ['number']);
            const sphereVolume = Module.cwrap('sphere_volume', 'number', ['number']);

            window.calcular = function() {
                const radius = parseFloat(document.getElementById('radius').value);

                const area = circleArea(radius);
                const circumference = circleCircumference(radius);
                const volume = sphereVolume(radius);

                document.getElementById('results').innerHTML = `
                    <h2>Resultados para raio = ${radius}</h2>
                    <p>Área do círculo: ${area.toFixed(4)}</p>
                    <p>Circunferência: ${circumference.toFixed(4)}</p>
                    <p>Volume da esfera: ${volume.toFixed(4)}</p>
                `;
            };
        };
    </script>
</body>
</html>
```

**wasm-pack — compilação de Rust**

wasm-pack é a ferramenta oficial para compilar Rust para WebAssembly, com suporte a wasm-bindgen para interoperação JavaScript.

Instalação:

```bash
curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh
```

Configuração do projeto:

```toml
# Cargo.toml
[package]
name = "image-processor"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
wasm-bindgen = "0.2"
js-sys = "0.3"
web-sys = "0.3"

[dependencies.web-sys]
features = [
    "Document",
    "Element",
    "HtmlElement",
    "Window",
]

[profile.release]
opt-level = "s"
lto = true
```

Código Rust:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct ImageProcessor {
    width: u32,
    height: u32,
    data: Vec<u8>,
}

#[wasm_bindgen]
impl ImageProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new(width: u32, height: u32) -> ImageProcessor {
        ImageProcessor {
            width,
            height,
            data: vec![0; (width * height * 4) as usize],
        }
    }

    pub fn width(&self) -> u32 {
        self.width
    }

    pub fn height(&self) -> u32 {
        self.height
    }

    pub fn data_ptr(&self) -> *const u8 {
        self.data.as_ptr()
    }

    pub fn grayscale(&mut self) {
        for i in (0..self.data.len()).step_by(4) {
            let r = self.data[i] as f32;
            let g = self.data[i + 1] as f32;
            let b = self.data[i + 2] as f32;

            let gray = (0.299 * r + 0.587 * g + 0.114 * b) as u8;

            self.data[i] = gray;
            self.data[i + 1] = gray;
            self.data[i + 2] = gray;
        }
    }

    pub fn blur(&mut self, radius: u32) {
        let kernel_size = (radius * 2 + 1) as usize;
        let kernel_area = (kernel_size * kernel_size) as f32;

        let mut new_data = self.data.clone();

        for y in radius..self.height - radius {
            for x in radius..self.width - radius {
                let mut r_sum = 0.0;
                let mut g_sum = 0.0;
                let mut b_sum = 0.0;

                for ky in 0..kernel_size {
                    for kx in 0..kernel_size {
                        let px = (x + kx as u32 - radius) as usize;
                        let py = (y + ky as u32 - radius) as usize;
                        let idx = (py * self.width as usize + px) * 4;

                        r_sum += self.data[idx] as f32;
                        g_sum += self.data[idx + 1] as f32;
                        b_sum += self.data[idx + 2] as f32;
                    }
                }

                let idx = (y as usize * self.width as usize + x as usize) * 4;
                new_data[idx] = (r_sum / kernel_area) as u8;
                new_data[idx + 1] = (g_sum / kernel_area) as u8;
                new_data[idx + 2] = (b_sum / kernel_area) as u8;
            }
        }

        self.data = new_data;
    }

    pub fn threshold(&mut self, value: u8) {
        for i in (0..self.data.len()).step_by(4) {
            let r = self.data[i];
            let g = self.data[i + 1];
            let b = self.data[i + 2];

            let gray = ((0.299 * r as f32 + 0.587 * g as f32 + 0.114 * b as f32)) as u8;

            let binary = if gray > value { 255 } else { 0 };

            self.data[i] = binary;
            self.data[i + 1] = binary;
            self.data[i + 2] = binary;
        }
    }

    pub fn invert(&mut self) {
        for i in (0..self.data.len()).step_by(4) {
            self.data[i] = 255 - self.data[i];
            self.data[i + 1] = 255 - self.data[i + 1];
            self.data[i + 2] = 255 - self.data[i + 2];
        }
    }

    pub fn sepia(&mut self) {
        for i in (0..self.data.len()).step_by(4) {
            let r = self.data[i] as f32;
            let g = self.data[i + 1] as f32;
            let b = self.data[i + 2] as f32;

            let tr = 0.393 * r + 0.769 * g + 0.189 * b;
            let tg = 0.349 * r + 0.686 * g + 0.168 * b;
            let tb = 0.272 * r + 0.534 * g + 0.131 * b;

            self.data[i] = tr.min(255.0) as u8;
            self.data[i + 1] = tg.min(255.0) as u8;
            self.data[i + 2] = tb.min(255.0) as u8;
        }
    }
}
```

Compilação:

```bash
# Compilar para web
wasm-pack build --target web

# Compilar para Node.js
wasm-pack build --target nodejs

# Compilar para bundler (webpack, vite, etc.)
wasm-pack build --target bundler

# Compilar com otimizações
wasm-pack build --target web --release

# Compilar com features específicas
wasm-pack build --target web --features "simd,threads"
```

**AssemblyScript — TypeScript para Wasm**

AssemblyScript é uma linguagem que se parece com TypeScript mas compila diretamente para WebAssembly.

Configuração:

```bash
npm init -y
npm install --save-dev assemblyscript
npx asinit . --yes
```

Código AssemblyScript:

```typescript
// assembly/index.ts
export function fibonacciIterative(n: i32): i32 {
    if (n <= 1) return n;
    let a: i32 = 0;
    let b: i32 = 1;
    for (let i: i32 = 2; i <= n; i++) {
        let temp = b;
        b = a + b;
        a = temp;
    }
    return b;
}

export function fibonacciRecursive(n: i32): i32 {
    if (n <= 1) return n;
    return fibonacciRecursive(n - 1) + fibonacciRecursive(n - 2);
}

export function isPrime(n: i64): boolean {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;
    let i: i64 = 3;
    while (i * i <= n) {
        if (n % i == 0) return false;
        i += 2;
    }
    return true;
}

export function gcd(a: i32, b: i32): i32 {
    while (b != 0) {
        let temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

export function lcm(a: i32, b: i32): i32 {
    return (a / gcd(a, b)) * b;
}

export function sumArray(data: StaticArray<i32>): i64 {
    let sum: i64 = 0;
    for (let i = 0; i < data.length; i++) {
        sum += data[i] as i64;
    }
    return sum;
}

export function matrixMultiply(
    a: StaticArray<f64>,
    b: StaticArray<f64>,
    result: StaticArray<f64>,
    m: i32,
    n: i32,
    p: i32
): void {
    for (let i: i32 = 0; i < m; i++) {
        for (let j: i32 = 0; j < p; j++) {
            let sum: f64 = 0;
            for (let k: i32 = 0; k < n; k++) {
                sum += unchecked(a[i * n + k]) * unchecked(b[k * p + j]);
            }
            unchecked(result[i * p + j] = sum);
        }
    }
}
```

Compilação:

```bash
# Compilar com otimizações
npx asc assembly/index.ts --outFile build/module.wasm --optimize

# Compilar com sourcemaps
npx asc assembly/index.ts --outFile build/module.wasm --sourceMap

# Compilar com múltiplos exports
npx asc assembly/index.ts --outFile build/module.wasm \
    --exportTable \
    --memoryBase 1024
```

### Ferramentas de análise e depuração

**WABT (WebAssembly Binary Toolkit)**

WABT é um conjunto de ferramentas para trabalhar com bytecode WebAssembly.

Instalação:

```bash
# Ubuntu/Debian
sudo apt-get install wabt

# macOS
brew install wabt

# Compilar do código fonte
git clone https://github.com/WebAssembly/wabt.git
cd wabt
git submodule update --init
mkdir build && cd build
cmake ..
cmake --build .
```

Ferramentas disponíveis:

```bash
# Converter WASM para WAT (texto)
wasm2wat module.wasm -o module.wat

# Converter WAT para WASM
wat2wasm module.wat -o module.wasm

# Validar módulo
wasm-validate module.wasm

# Desmontar para ver instruções
wasm-objdump -x module.wasm

# Verificar se módulo é válido
wasm-validate module.wasm && echo "Válido" || echo "Inválido"

# Converter para formato C
wasm2c module.wasm -o module.c -o module.h

# Estatísticas do módulo
wasm-stats module.wasm

# Interpeter módulo
wasm-interp module.wasm --run-all-exports
```

**Wasmi — interpretador WebAssembly**

Wasmi é um interpretador WebAssembly leve que pode ser usado para testes e depuração.

```rust
// Uso do Wasmi em Rust
use wasmi::{Engine, Module, Store, Func, FuncType, Val};

fn main() {
    // Criar engine
    let engine = Engine::default();

    // Carregar módulo
    let wasm_bytes = std::fs::read("module.wasm").unwrap();
    let module = Module::new(&engine, &wasm_bytes).unwrap();

    // Criar store
    let mut store = Store::new(&engine, ());

    // Definir importações
    let host_fn = Func::wrap(&mut store, |caller: wasmi::Caller<'_, ()>, a: i32, b: i32| -> i32 {
        println!("Host function called with {} and {}", a, b);
        a + b
    });

    // Instanciar
    let instance = wasmi::Instance::new(&mut store, &module, &[host_fn.into()]).unwrap();

    // Chamar função exportada
    let add = instance.get_func(&store, "add").unwrap();
    let result = add.call(&mut store, &[Val::I32(5), Val::I32(3)]).unwrap();
    println!("Resultado: {}", result[0].i32().unwrap());
}
```

**wasm-tools — ferramentas da Bytecode Alliance**

wasm-tools é uma coleção de ferramentas para manipulação de módulos WebAssembly.

Instalação:

```bash
cargo install wasm-tools
```

Uso:

```bash
# Listar seções de um módulo
wasm-tools module-info module.wasm

# Visualizar estrutura
wasm-tools dump module.wasm

# Validar módulo
wasm-tools validate module.wasm

# Remover custom sections
wasm-tools strip module.wasm -o module_stripped.wasm

# Adicionar names section
wasm-tools names module.wasm -o module_named.wasm

# Combinar módulos
wasm-tools compose module1.wasm module2.wasm -o combined.wasm

# Gerar componente
wasm-tools component new module.wasm --encoding utf8 -o component.wasm

# Converter entre formatos
wasm-tools component wit component.wasm > component.wit
```

### IDEs e editores

**VS Code**

Extensões recomendadas para WebAssembly:

- **WebAssembly Toolkit for VS Code**: suporte a WAT, syntax highlighting, validação
- **AssemblyScript**: suporte a AssemblyScript
- **rust-analyzer**: suporte a Rust (para wasm-bindgen)
- **C/C++**: suporte a C/C++ (para Emscripten)

Configuração do VS Code para WAT:

```json
{
    "files.associations": {
        "*.wat": "wat",
        "*.wasm": "wasm"
    },
    "editor.tabSize": 2,
    "editor.insertSpaces": true
}
```

**IntelliJ IDEA / RustRover**

Plugins disponíveis:

- WebAssembly Plugin
- Rust Plugin (com suporte a wasm32-wasi)
- AssemblyScript Plugin

### Ferramentas de teste

**wasm-pack test**

wasm-pack fornece ferramentas integradas para testar módulos WebAssembly:

```rust
// src/lib.rs com testes
use wasm_bindgen::prelude::*;
use wasm_bindgen_test::*;

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_fibonacci() {
    assert_eq!(fibonacci(0), 0);
    assert_eq!(fibonacci(1), 1);
    assert_eq!(fibonacci(10), 55);
    assert_eq!(fibonacci(20), 6765);
}

#[wasm_bindgen_test]
fn test_prime() {
    assert!(!is_prime(0));
    assert!(!is_prime(1));
    assert!(is_prime(2));
    assert!(is_prime(3));
    assert!(!is_prime(4));
    assert!(is_prime(17));
}

#[wasm_bindgen]
pub fn fibonacci(n: u32) -> u32 {
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a = 0;
            let mut b = 1;
            for _ in 2..=n {
                let temp = b;
                b = a + b;
                a = temp;
            }
            b
        }
    }
}

#[wasm_bindgen]
pub fn is_prime(n: u64) -> bool {
    if n < 2 { return false; }
    if n == 2 { return true; }
    if n % 2 == 0 { return false; }
    let mut i = 3;
    while i * i <= n {
        if n % i == 0 { return false; }
        i += 2;
    }
    true
}
```

Executar testes:

```bash
# Testar no navegador
wasm-pack test --chrome --headless

# Testar no Firefox
wasm-pack test --firefox --headless

# Testar no Node.js
wasm-pack test --node

# Testar com verbose
wasm-pack test --chrome --headless -- --nocapture
```

**wasm-bindgen-test para Rust**

```bash
# Instalar wasm-bindgen-cli
cargo install wasm-bindgen-cli

# Executar testes
wasm-pack test --headless --chrome
```

### Ferramentas de profiling

**Profiling com Wasmtime**

```bash
# Habilitar profiling
wasmtime --profile cpu module.wasm

# Gerar relatório de profiling
wasmtime --profile jitdump module.wasm

# Usar perf com Wasmtime
perf record -g wasmtime module.wasm
perf report
```

**Profiling no navegador**

```javascript
// Usar Performance API para medir tempo de funções Wasm
const start = performance.now();
instance.exports.processData(data);
const end = performance.now();
console.log(`Wasm levou ${end - start} milliseconds`);

// Usar Chrome DevTools
// 1. Abrir DevTools
// 2. Ir para aba Performance
// 3. Gravar perfil enquanto Wasm executa
// 4. Analisar call stack e timing
```

---

## 1.12 Padrões de design em WebAssembly

### Padrão 1: Memory allocator pattern

Um padrão comum é implementar um alocador de memória dentro da memória linear do Wasm:

```wat
(module
    (memory (export "memory") 1)

    ;; Ponteiro do heap (início da área alocável)
    (global $heap_ptr (mut i32) (i32.const 1024))

    ;; Alocação simples (bump allocator)
    (func $malloc (param $size i32) (result i32)
        (local $ptr i32)

        ;; Obter ponteiro atual
        (local.set $ptr (global.get $heap_ptr))

        ;; Alinhar para 8 bytes
        (local.set $ptr
            (i32.and
                (i32.add (local.get $ptr) (i32.const 7))
                (i32.xor (i32.const 7))
            )
        )

        ;; Avançar heap
        (global.set $heap_ptr
            (i32.add (local.get $ptr) (local.get $size))
        )

        (local.get $ptr)
    )

    ;; Deallocation (simplificada - apenas para bump allocator)
    (func $free (param $ptr i32)
        ;; Bump allocator não suporta free
        ;; Em produção, usar um allocator mais sofisticado
        nop
    )

    ;; Alocação de array
    (func $alloc_array (param $count i32) (param $elem_size i32) (result i32)
        (call $malloc
            (i32.mul (local.get $count) (local.get $elem_size))
        )
    )

    (export "malloc" (func $malloc))
    (export "free" (func $free))
    (export "alloc_array" (func $alloc_array))
)
```

### Padrão 2: String interop pattern

```wat
(module
    (memory (export "memory") 1)

    ;; Área de strings (início em 0x10000)
    (global $string_area (mut i32) (i32.const 65536))

    ;; Armazenar string na memória
    ;; Retorna ponteiro para a string
    (func $string_new (param $ptr i32) (param $len i32) (result i32)
        (local $dest i32)

        ;; Obter ponteiro de destino
        (local.set $dest (global.get $string_area))

        ;; Armazenar comprimento (4 bytes)
        (i32.store (local.get $dest) (local.get $len))

        ;; Copiar dados
        (memory.copy
            (i32.add (local.get $dest) (i32.const 4))
            (local.get $ptr)
            (local.get $len)
        )

        ;; Avançar ponteiro
        (global.set $string_area
            (i32.add
                (i32.add (local.get $dest) (i32.const 4))
                (local.get $len)
            )
        )

        (local.get $dest)
    )

    ;; Obter comprimento de string
    (func $string_len (param $ptr i32) (result i32)
        (i32.load (local.get $ptr))
    )

    ;; Obter dados da string
    (func $string_data (param $ptr i32) (result i32)
        (i32.add (local.get $ptr) (i32.const 4))
    )

    ;; Comparar duas strings
    (func $string_eq (param $a i32) (param $b i32) (result i32)
        (local $len_a i32)
        (local $len_b i32)
        (local $i i32)

        (local.set $len_a (call $string_len (local.get $a)))
        (local.set $len_b (call $string_len (local.get $b)))

        ;; Comprimentos diferentes
        (if (i32.ne (local.get $len_a) (local.get $len_b))
            (then (return (i32.const 0)))
        )

        ;; Comparar byte a byte
        (local.set $i (i32.const 0))
        (block $break
            (loop $loop
                (br_if $break (i32.ge_u (local.get $i) (local.get $len_a)))

                (if (i32.ne
                        (i32.load8_u (i32.add (call $string_data (local.get $a)) (local.get $i)))
                        (i32.load8_u (i32.add (call $string_data (local.get $b)) (local.get $i)))
                    )
                    (then (return (i32.const 0)))
                )

                (local.set $i (i32.add (local.get $i) (i32.const 1)))
                (br $loop)
            )
        )

        (i32.const 1)
    )

    (export "string_new" (func $string_new))
    (export "string_len" (func $string_len))
    (export "string_data" (func $string_data))
    (export "string_eq" (func $string_eq))
)
```

### Padrão 3: Error handling pattern

```wat
(module
    ;; Código de erro: 0 = sucesso, qualquer outro = erro
    (global $last_error (mut i32) (i32.const 0))

    ;; Mensagens de erro
    (data (i32.const 0) "Success")
    (data (i32.const 16) "Invalid argument")
    (data (i32.const 48) "Out of memory")
    (data (i32.const 72) "Not found")

    ;; Definir erro
    (func $set_error (param $code i32)
        (global.set $last_error (local.get $code))
    )

    ;; Obter último erro
    (func $get_error (result i32)
        (global.get $last_error)
    )

    ;; Obter mensagem de erro
    (func $error_message (param $code i32) (result i32 i32)
        (if (result i32 i32)
            (i32.eq (local.get $code) (i32.const 0))
            (then
                ;; Sucesso
                (i32.const 0)   ;; ponteiro
                (i32.const 7)   ;; comprimento
            )
            (else (if (result i32 i32)
                (i32.eq (local.get $code) (i32.const 1))
                (then
                    ;; Argumento inválido
                    (i32.const 16)
                    (i32.const 16)
                )
                (else (if (result i32 i32)
                    (i32.eq (local.get $code) (i32.const 2))
                    (then
                        ;; Memória insuficiente
                        (i32.const 48)
                        (i32.const 14)
                    )
                    (else
                        ;; Não encontrado
                        (i32.const 72)
                        (i32.const 9)
                    )
                ))
            ))
        )
    )

    ;; Operação que pode falhar
    (func $divide (param $a i32) (param $b i32) (result i32)
        ;; Verificar divisão por zero
        (if (i32.eqz (local.get $b))
            (then
                (call $set_error (i32.const 1))
                (return (i32.const 0))
            )
        )

        ;; Limpar erro anterior
        (call $set_error (i32.const 0))

        ;; Retornar resultado
        (i32.div_s (local.get $a) (local.get $b))
    )

    (export "get_error" (func $get_error))
    (export "error_message" (func $error_message))
    (export "divide" (func $divide))
)
```

### Padrão 4: Callback pattern

```wat
(module
    ;; Tabela de callbacks
    (table 4 funcref)
    (elem (i32.const 0) $callback_a $callback_b $callback_c $callback_d)

    ;; Tipo de callback: (i32) -> i32
    (type $callback_type (func (param i32) (result i32)))

    ;; Callbacks
    (func $callback_a (param $x i32) (result i32)
        (i32.mul (local.get $x) (i32.const 2))
    )

    (func $callback_b (param $x i32) (result i32)
        (i32.add (local.get $x) (i32.const 10))
    )

    (func $callback_c (param $x i32) (result i32)
        (i32.sub (i32.const 100) (local.get $x))
    )

    (func $callback_d (param $x i32) (result i32)
        (i32.div_s (local.get $x) (i32.const 3))
    )

    ;; Registrar callback (armazenar índice)
    (global $current_callback (mut i32) (i32.const 0))

    ;; Definir callback ativo
    (func $set_callback (param $index i32)
        (global.set $current_callback (local.get $index))
    )

    ;; Chamar callback registrado
    (func $call_callback (param $value i32) (result i32)
        (call_indirect (type $callback_type)
            (local.get $value)
            (global.get $current_callback)
        )
    )

    ;; Chamar callback específico
    (func $call_specific (param $index i32) (param $value i32) (result i32)
        (call_indirect (type $callback_type)
            (local.get $value)
            (local.get $index)
        )
    )

    (export "set_callback" (func $set_callback))
    (export "call_callback" (func $call_callback))
    (export "call_specific" (func $call_specific))
)
```

---

## Resumo

Neste capítulo, exploramos os fundamentos do WebAssembly:

- **História**: de asm.js ao Wasm, uma evolução natural de JavaScript otimizável para bytecode portável
- **Arquitetura**: máquina de pilha com validação estática forte
- **Bytecode**: formato binário compacto com seções organizadas
- **Pipeline**: compilação via LLVM, Emscripten, wasm-pack
- **Módulo/Instância**: ciclo de vida que separa compilação de execução
- **Memória linear**: bloco contíguo de bytes, expansível, isolado por instância
- **Tabela de funções**: array de referências para dispatch dinâmico
- **Navegador**: API WebAssembly completa com streaming compilation
- **Servidor**: WASI como ponte para acesso ao sistema operacional
- **Comparação**: Wasm vs JavaScript, containers, e outras tecnologias

No próximo capítulo, exploraremos o modelo de segurança do WebAssembly em detalhes.
