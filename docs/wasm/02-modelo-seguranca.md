# Capítulo 2: Modelo de Segurança do WebAssembly

## Sumário

- [2.1 Modelo de sandbox](#21-modelo-de-sandbox)
- [2.2 Isolamento de memória](#22-isolamento-de-memória)
- [2.3 Integridade de fluxo de controle](#23-integridade-de-fluxo-de-controle)
- [2.4 Memória linear](#24-memória-linear)
- [2.5 Validação de tabelas](#25-validação-de-tabelas)
- [2.6 Segurança de importações e exportações](#26-segurança-de-importações-e-exportações)
- [2.7 Segurança baseada em capacidades](#27-segurança-baseada-em-capacidades)
- [2.8 Superfície de ataque](#28-superfície-de-ataque)
- [2.9 Exemplos de CVEs](#29-exemplos-de-cves)
- [2.10 Propriedades de segurança](#210-propriedades-de-segurança)

---

## 2.1 Modelo de sandbox

### Fundamentos do sandbox

O modelo de segurança do WebAssembly é construído sobre um sandbox robusto que isola completamente módulos Wasm do sistema operacional subjacente e de outros módulos. Esse sandbox é fundamentalmente diferente do sandbox de processos tradicionais — ele opera em um nível mais granular e com garantias mais fortes.

O sandbox do Wasm não é uma camada de proteção adicionada事后 (after the fact), mas sim uma propriedade inerente ao design da especificação. Um módulo WebAssembly não pode:

- Acessar a sistema de arquivos diretamente
- Criar ou manipular processos
- Estabelecer conexões de rede
- Acessar dispositivos de hardware
- Executar código nativo do sistema operacional
- Ler memória fora de seu espaço endereçável
- Acessar variáveis de ambiente sem permissão
- Manipular sinais ou interrupções

Essas restrições são impostas pela própria especificação, não por uma camada de virtualização ou container. Isso significa que a segurança não depende de configurações externas ou do sistema operacional.

### Níveis de sandbox

O WebAssembly opera em diferentes níveis de sandbox dependendo do ambiente de execução:

**1. Sandbox de memória**

Cada instância Wasm tem sua própria memória linear isolada. Não existe mecanismo na especificação para que duas instâncias compartilhem memória diretamente. Mesmo quando múltiplas instâncias rodam no mesmo processo, suas memórias são completamente separadas.

```wat
;; Módulo A - não pode acessar memória do Módulo B
(module
    (memory (export "memory") 1)
    ;; A memória começa em 0 e vai até initial * 64KiB
    ;; Não existe forma de endereçar memória fora desse limite
)

;; Qualquer acesso fora dos limites resulta em trap
;; (exceção fatal que encerra a execução)
```

**2. Sandbox de execução**

O código Wasm não pode alterar seu próprio fluxo de execução além do que as instruções permitem. Não há como:

- Executar código arbitrário da memória
- Modificar o program counter
- Alterar o comportamento de instruções
- Fazer jump para endereços arbitrários

**3. Sandbox de recursos**

Sem importações explícitas, um módulo Wasm não pode acessar nenhum recurso do sistema. A única forma de interagir com o mundo exterior é através de funções e objetos importados.

```javascript
// O host controla completamente o que o módulo pode acessar
const imports = {
    env: {
        // Somente funções que definirmos aqui estarão disponíveis
        log: (msg) => console.log(msg),
        // Sem importação = sem acesso
    }
};

// O módulo NÃO pode:
// - Acessar document, window (navegador)
// - Acessar fs, process (Node.js)
// - Acessar filesystem, network (servidor)
// A menos que explicitamente importadas
```

### Comparação com其他 sandbox

| Mecanismo | Nível | Granularidade | Overhead |
|-----------|-------|---------------|----------|
| Process sandbox | OS | Processo inteiro | Alto |
| Container (Docker) | OS + namespace | Container inteiro | Médio |
| V8 Isolates | Runtime | Isolate inteiro | Baixo |
| WebAssembly | Linguagem | Módulo/Instância | Muito baixo |

A granularidade do Wasm permite isolar múltiplos módulos dentro de um mesmo processo, cada um com seu próprio espaço de memória e permissões, sem o overhead de criar processos ou containers separados.

### Validação estática

Antes da execução, todo código WebAssembly passa por um processo de validação estática. Essa validação verifica:

1. **Tipagem**: todas as operações são usadas com os tipos corretos
2. **Pilha**: a pilha nunca fica em estado inválido (underflow ou overflow de tipos)
3. **Controle de fluxo**: branches são válidos e apontam para locais corretos
4. **Memória**: acessos a memória estão dentro dos limites
5. **Tabelas**: índices de tabela estão dentro dos limites
6. **Importações**: todas as importações são satisfeitas

```bash
# Validar um módulo antes de executar
wasm-validate module.wasm

# Se a validação falhar, o módulo é rejeitado
# e nunca entra em execução
```

A validação é uma operação O(n) no tamanho do código, o que a torna viável mesmo para módulos grandes. Um módulo que falha na validação nunca é compilado nem executado — ele é rejeitado imediatamente.

---

## 2.2 Isolamento de memória

### Modelo de memória isolada

O isolamento de memória é uma das garantias fundamentais de segurança do WebAssembly. Cada instância de módulo opera em sua própria memória linear, que é completamente isolada de outras instâncias e do sistema operacional.

A memória linear do Wasm é um array de bytes unidimensional que começa no endereço 0 e se estende até o tamanho alocado. O acesso é indexado por inteiros não-negativos, e qualquer tentativa de acesso fora dos limites resulta em uma trap (exceção fatal).

```wat
(module
    ;; Cada módulo tem sua própria memória
    (memory 1)  ;; 1 página = 64 KiB

    ;; Não existe forma de acessar memória de outro módulo
    ;; Não existe forma de acessar memória do sistema operacional
    ;; Não existe forma de acessar memória do host

    ;; O único acesso possível é dentro dos limites
    (func $safeAccess (param $offset i32)
        ;; Esse acesso é seguro se offset < 65536
        (i32.load (local.get $offset))
        drop
    )
)
```

### Proteções contra overflow

WebAssembly implementa múltiplas camadas de proteção contra violações de memória:

**1. Bounds checking estático**

Quando possível, o compilador e o validador determinam os limites de acesso em tempo de compilação:

```wat
;; Se o compilador sabe que o offset é seguro, pode pular bounds check
(i32.load offset=0 align=4  ;; acesso com offset fixo
    (i32.const 0)            ;; constante, sempre segura
)
```

**2. Bounds checking dinâmico**

Para acessos com índices variáveis, o runtime verifica os limites antes de cada acesso:

```wat
;; Acesso com índice variável - requer bounds check em runtime
(i32.load
    (local.get $index)  ;; index pode ser qualquer valor
)
;; O runtime verifica: index + 4 <= memory.size * 65536
;; Se não for verdade, trap é gerada
```

**3. Proteção contra arithmetic overflow**

Operações aritméticas que causam overflow são definidas modularmente, não geram traps:

```wat
;; Overflow de i32 é definido como wrap-around (modular)
i32.const 2147483647   ;; max i32
i32.const 1
i32.add                ;; resultado: -2147483648 (wrap, não trap)
```

**4. Divisão por zero**

Diferente de overflow, divisão por zero gera uma trap:

```wat
i32.const 0
i32.const 0
i32.div_s              ;; TRAP: integer divide by zero
```

### Isolamento entre instâncias

Quando múltiplas instâncias rodam no mesmo runtime, cada uma mantém sua memória isolada:

```javascript
async function demonstrateIsolation() {
    const module = await WebAssembly.compile(wasmBytes);

    // Criar memórias separadas
    const memory1 = new WebAssembly.Memory({ initial: 1 });
    const memory2 = new WebAssembly.Memory({ initial: 1 });

    // Instância 1
    const instance1 = await WebAssembly.instantiate(module, {
        env: { memory: memory1 }
    });

    // Instância 2
    const instance2 = await WebAssembly.instantiate(module, {
        env: { memory: memory2 }
    });

    // Escrever dados na instância 1
    const view1 = new Int32Array(memory1.buffer);
    view1[0] = 42;
    view1[1] = 100;

    // Instância 2 não vê os dados da instância 1
    const view2 = new Int32Array(memory2.buffer);
    console.log(view2[0]);  // 0, não 42
    console.log(view2[1]);  // 0, não 100

    // As memórias são completamente independentes
}
```

### SharedArrayBuffer e isolamento

Quando `SharedArrayBuffer` é usado, múltiplos threads podem acessar a mesma memória. Isso NÃO quebra o isolamento entre instâncias — apenas permite que threads dentro da mesma instância compartilhem memória:

```javascript
// SharedArrayBuffer permite compartilhamento DENTRO de uma instância
const sharedMemory = new WebAssembly.Memory({
    initial: 1,
    shared: true  // permite uso com SharedArrayBuffer
});

// Mas instâncias diferentes continuam isoladas
const instance1 = await WebAssembly.instantiate(module, {
    env: { memory: sharedMemory }  // instância 1 usa a memória compartilhada
});

// Instância 2 com memória separada
const memory2 = new WebAssembly.Memory({ initial: 1 });
const instance2 = await WebAssembly.instantiate(module, {
    env: { memory: memory2 }
});

// instance1 e instance2 continuam completamente isoladas
```

### Buffer views e transferência

O host pode criar múltiplas views sobre a mesma memória, mas isso não quebra o isolamento — são apenas diferentes perspectivas sobre os mesmos dados:

```javascript
const memory = new WebAssembly.Memory({ initial: 1 });

// Múltiplas views sobre a mesma memória
const u8View = new Uint8Array(memory.buffer);
const i32View = new Int32Array(memory.buffer);
const f64View = new Float64Array(memory.buffer);

// Todos veem os mesmos dados, interpretados de formas diferentes
u8View[0] = 0xFF;
console.log(i32View[0]);  // depende de endianness

// Isso NÃO quebra isolamento — são views do host sobre sua própria memória
```

---

## 2.3 Integridade de fluxo de controle

### O problema de CFI

A Integridade de Fluxo de Controle (Control Flow Integrity - CFI) é uma propriedade de segurança que garante que o fluxo de execução de um programa siga apenas caminhos legítimos. Em linguagens como C e C++, violações de CFI são uma classe comum de vulnerabilidades exploradas em ataques.

Exemplos de violações de CFI em código nativo:

- **Buffer overflow que sobrescreve ponteiro de função**: atacante redireciona execução para código arbitrário
- **Use-after-free**: objeto é reusado após dealocação, com ponteiro modificado
- **Return-oriented programming (ROP)**: cadeia de gadgets retomada por overflow de stack

### CFI no WebAssembly

WebAssembly implementa CFI nativamente através de sua especificação. O fluxo de controle é estritamente definido e validado antes da execução:

**1. Branches são validados estaticamente**

```wat
;; Branch target deve ser um label válido
(block $outer
    (block $inner
        (br $inner)   ;; válido: aponta para $inner
        (br $outer)   ;; válido: aponta para $outer
        (br 2)        ;; inválido: não existe label 2
    )
)
```

**2. Call indireta é tipada**

```wat
;; call_indirect verifica o tipo da função na tabela
(type $sig (func (param i32) (result i32)))

(table 1 funcref)
(elem (i32.const 0) $func1)

(func $func1 (param i32) (result i32)
    (local.get 0)
)

;; call_indirect verifica: a função na tabela tem o tipo correto?
(call_indirect (type $sig)
    (i32.const 0)  ;; índice na tabela
)
;; Se o tipo não corresponder: TRAP
```

**3. Não há computed jumps**

Diferente de assembly nativo, WebAssembly não permite jumps para endereços calculados. Todos os saltos são para labels conhecidos estáticamente:

```wat
;; Isso é IMPOSSÍVEL em WebAssembly:
;; jump para endereço calculado em runtime
;; Porque jumps são apenas para labels (blocks, loops, ifs)

;; O único "dispatch dinâmico" é call_indirect
;; e ele verifica o tipo da função
```

**4. Return é seguro**

Funções sempre retornam para o chamador. Não há forma de manipular o return address:

```wat
(func $caller
    (call $callee)
    ;; Aqui é sempre executado depois de $callee retornar
    ;; Não há forma de redirecionar o return
)

(func $callee
    ;; Não pode modificar pra onde retorna
    ;; O return address é controlado pelo runtime, não pelo código
)
```

### Proteção contra ROP/JOP

Return-Oriented Programming (ROP) e Jump-Oriented Programming (JOP) são técnicas que reutilizam trechos existentes de código ("gadgets") para executar operações não intencionais.

WebAssembly mitiga essas técnicas através de:

1. **Sem gadgets**: o bytecode não contém sequências de instruções que possam ser reutilizadas de forma inesperada
2. **Validação de tipos**: cada operação é verificada contra seu tipo esperado
3. **Controle de fluxo restrito**: não existem saltos arbitrários
4. **Sem código executável em dados**: a memória de código é separada da memória de dados

```wat
;; Em WebAssembly, não é possível:
;; 1. Executar dados como código
;; 2. Saltar para endereços arbitrários
;; 3. Modificar instruções em runtime
;; 4. Encadear gadgets de forma não intencionada
```

### Call_indirect e type safety

O `call_indirect` é a única forma de dispatch dinâmico no WebAssembly, e ele implementa verificações de tipo rigorosas:

```wat
(module
    ;; Dois tipos diferentes
    (type $typeA (func (param i32) (result i32)))
    (type $typeB (func (param i32 i32) (result i32)))

    ;; Tabela que pode conter funções de tipos diferentes
    (table 2 funcref)

    ;; Função do tipo A
    (func $funcA (type $typeA) (param $x i32) (result i32)
        (i32.mul (local.get $x) (i32.const 2))
    )

    ;; Função do tipo B
    (func $funcB (type $typeB) (param $x i32) (param $y i32) (result i32)
        (i32.add (local.get $x) (local.get $y))
    )

    ;; Inicializar tabela
    (elem (i32.const 0) $funcA $funcB)

    ;; Chamada que verifica o tipo
    (func $callWithTypeA (param $index i32) (result i32)
        ;; O runtime verifica: a função no índice $index tem tipo $typeA?
        ;; Se não tiver: TRAP
        (call_indirect (type $typeA) (local.get $index))
    )

    ;; Chamada que verifica outro tipo
    (func $callWithTypeB (param $index i32) (param $y i32) (result i32)
        ;; O runtime verifica: a função no índice $index tem tipo $typeB?
        (call_indirect (type $typeB) (local.get $index) (local.get $y))
    )
)
```

### Impacto na segurança

As garantias de CFI do WebAssembly têm implicações profundas:

- **Não existem exploits de buffer overflow que redirecionam execução**: overflows causam traps ou corrompem dados, mas não permitem execução arbitrária
- **Não existem return-oriented programming**: sem gadgets reutilizáveis
- **Não existem jump-oriented programming**: saltos são todos estáticos
- **Use-after-free não permite execução arbitrária**: pode causar comportamento indefinido, mas não execução de código arbitrário

---

## 2.4 Memória linear

### Semântica formal da memória

A memória linear do WebAssembly é definida formalmente na especificação como uma função de endereço para byte:

```
M: addr → byte
```

Essa função é parcial — ela é definida apenas para endereços dentro dos limites da memória. Para qualquer endereço fora dos limites, a função é indefinida, e acessar esse endereço resulta em uma trap.

### Organização da memória

A memória é organizada em páginas de 64 KiB (65.536 bytes). O tamanho da memória é sempre um múltiplo de 64 KiB:

```
Tamanho total = número_de_páginas × 65536

Exemplo:
1 página  = 64 KiB = 65.536 bytes
16 páginas = 1 MiB = 1.048.576 bytes
256 páginas = 16 MiB = 16.777.216 bytes
```

### Endereçamento

A memória é endereçada por byte, usando inteiros não-negativos (i32). Isso permite endereçar até 4 GiB de memória (2^32 bytes):

```
Endereço válido: 0 até (tamanho_da_memória - 1)
Endereço inválido: >= tamanho_da_memória
```

### Operações de memória

**Carregamento (Load)**:

```wat
;; Formato: <type>.load [offset] [align]
;; offset: constante adicionada ao índice (default: 0)
;; align: potência de 2 que define o alinhamento (default: tamanho do tipo)

;; Load de i32
i32.load offset=0 align=4  ;; carrega 4 bytes a partir de [index + 0], alinhado a 4

;; Load com offset
i32.load offset=8 align=4  ;; carrega 4 bytes a partir de [index + 8]

;; Load de diferentes tamanhos
i32.load8_s   ;; carrega 1 byte, extende com sinal para i32
i32.load8_u   ;; carrega 1 byte, extende sem sinal para i32
i32.load16_s  ;; carrega 2 bytes, extende com sinal para i32
i32.load16_u  ;; carrega 2 bytes, extende sem sinal para i32
i64.load8_s   ;; carrega 1 byte, extende com sinal para i64
i64.load8_u   ;; carrega 1 byte, extende sem sinal para i64
i64.load16_s  ;; carrega 2 bytes, extende com sinal para i64
i64.load16_u  ;; carrega 2 bytes, extende sem sinal para i64
i64.load32_s  ;; carrega 4 bytes, extende com sinal para i64
i64.load32_u  ;; carrega 4 bytes, extende sem sinal para i64
```

**Armazenamento (Store)**:

```wat
;; Formato: <type>.store [offset] [align]
;; Armazena o topo da pilha no endereço

;; Store de i32
i32.store offset=0 align=4  ;; armazena 4 bytes em [index + 0]

;; Store de diferentes tamanhos
i32.store8    ;; armazena 1 byte (trunca i32 para 8 bits)
i32.store16   ;; armazena 2 bytes (trunca i32 para 16 bits)
i64.store8    ;; armazena 1 byte (trunca i64 para 8 bits)
i64.store16   ;; armazena 2 bytes (trunca i64 para 16 bits)
i64.store32   ;; armazena 4 bytes (trunca i64 para 32 bits)
```

**Crescimento de memória**:

```wat
;; Verificar tamanho atual (em páginas)
memory.size    ;; retorna número de páginas

;; Crescer a memória
memory.grow    ;; empilha增量 (número de páginas a adicionar)
               ;; retorna tamanho anterior ou -1 se falhar
```

### Validação de memória

O validador verifica propriedades de segurança para operações de memória:

**1. Offset constante é verificado**

```wat
;; O compilador verifica: offset + tamanho_do_tipo <= memory.size * 65536
;; Se não for possível verificar em tempo de compilação, bounds check é inserido

i32.load offset=100  ;; compilador verifica: 100 + 4 <= tamanho_da_memória
```

**2. Acesso dinâmico requer bounds check em runtime**

```wat
;; Quando o índice é conhecido apenas em runtime
(i32.load (local.get $index))
;; O runtime verifica: index + 4 <= memory.size * 65536
;; Se não, trap
```

**3. Alinhamento é verificado (opcional)**

```wat
;; Se align > tamanho_do_tipo, é um erro
i32.load align=8  ;; ERRO: align 8 > tamanho 4
```

### Ataques de timing em memória

Em teoria, operações de memória com bounds checks dinâmicos podem ser vulneráveis a ataques de timing. Em prática, implementações modernas usam técnicas para minimizar essas vulnerabilidades:

1. **Branch prediction**: CPUs modernas predizem branches comuns, reduzindo variação de timing
2. **Constant-time bounds checks**: algumas implementações evitam branches na verificação
3. **Speculative execution**: o CPU pode executar instruções antes da verificação completar

No entanto, esses são considerações de implementação, não de especificação. A especificação define a semântica correta; as implementações otimizam a execução.

---

## 2.5 Validação de tabelas

### O papel das tabelas

As tabelas de funções no WebAssembly servem como arrays de referências a funções. Elas são usadas para implementar dispatch dinâmico (como ponteiros para funções em C), mas com verificações de tipo que garantem segurança.

Sem tabelas, não haveria forma de implementar polimorfismo ou callbacks em WebAssembly. Com tabelas, é possível ter código que chama diferentes funções dependendo de valores em runtime, mas com a garantia de que cada chamada é tipada corretamente.

### Validação de call_indirect

A instrução `call_indirect` é o mecanismo que usa tabelas para dispatch dinâmico. A validação verifica:

**1. O índice está dentro dos limites da tabela**

```wat
;; Se a tabela tem tamanho N, índices >= N causam trap
(table 10 funcref)

(call_indirect (type $sig) (i32.const 5))  ;; válido: 5 < 10
(call_indirect (type $sig) (i32.const 10)) ;; trap: 10 >= 10
(call_indirect (type $sig) (i32.const -1)) ;; trap: -1 < 0
```

**2. A função na tabela tem o tipo correto**

```wat
(type $typeA (func (param i32)))
(type $typeB (func (param i32 i32)))

(table 2 funcref)
(elem (i32.const 0) $funcA $funcB)

;; Chamada com tipo A
(call_indirect (type $typeA) (i32.const 0))  ;; ok: $funcA tem tipo $typeA
(call_indirect (type $typeA) (i32.const 1))  ;; trap: $funcB não tem tipo $typeA
```

**3. A função não é null (se o runtime suporta)**

```wat
;; Em runtimes que suportam referências nulas
(table 2 funcref)

;; Se o slot está vazio (null), chamada causa trap
(call_indirect (type $sig) (i32.const 0))  ;; trap se slot 0 é null
```

### Inicialização de tabelas

As tabelas são inicializadas através da seção de elementos:

```wat
(module
    (table 5 funcref)

    (func $f1 (result i32) (i32.const 1))
    (func $f2 (result i32) (i32.const 2))
    (func $f3 (result i32) (i32.const 3))

    ;; Inicialização estática
    (elem (i32.const 0) $f1 $f2 $f3)

    ;; Ou inicialização dinâmica
    ;; (elem (i32.const 0) (ref.func $f1) (ref.func $f2) (ref.func $f3))
)
```

### Tabelas e segurança

As tabelas contribuem para a segurança de várias formas:

**1. Tipo safety**: cada chamada indireta verifica o tipo

**2. Bounds checking**: índices fora dos limites causam trap

**3. Null checking**: referências nulas causam trap

**4. Imutabilidade parcial**: tabelas podem ser declaradas como imutáveis

```wat
;; Tabela imutável (não pode ser modificada após instanciação)
(table 10 funcref)

;; Modificação de tabela só pode ocorrer via elem.drop
;; e só em segmentos que foram declarados como declarativos
```

### Ataques contra tabelas

Embora as tabelas implementem verificações de tipo, existem considerações de segurança:

**1. Type confusion via type index**

Se um módulo é malicioso e tenta usar call_indirect com o tipo errado, a verificação de tipo detecta e gera trap.

**2. Out-of-bounds access**

Tentativas de acessar índices inválidos na tabela são detectadas e geram trap.

**3. Table overflow**

Tentativas de crescer uma tabela além do limite máximo falham silenciosamente (memory.grow retorna -1).

**4. Reentrancy**

Chamadas indiretas podem causar reentrância se a tabela for modificada durante a execução. O validador limita quando tabelas podem ser modificadas.

---

## 2.6 Segurança de importações e exportações

### O modelo de importações

As importações são o mecanismo pelo qual módulos WebAssembly acessam funcionalidade externa. Elas são definidas no módulo e satisfeitas durante a instanciação. Esse modelo de separação é fundamental para a segurança do Wasm.

```wat
(module
    ;; Declaração de importações
    ;; O módulo DECLARA o que precisa
    ;; O host DECIDE o que fornecer

    ;; Importar função
    (import "env" "log" (func $log (param i32)))

    ;; Importar memória
    (import "env" "memory" (memory 1))

    ;; Importar tabela
    (import "env" "table" (table 10 funcref))

    ;; Importar global
    (import "env" "counter" (global (mut i32)))

    ;; O módulo só pode usar o que foi importado
    ;; Não pode criar novas funcionalidades externas
)
```

### Validação de importações

O processo de instanciação valida que todas as importações satisfazem os requisitos do módulo:

**1. Todas as importações devem ser fornecidas**

```javascript
// Se o módulo espera import "env" "log" mas o host não fornece
const imports = {};  // falta env.log
const instance = await WebAssembly.instantiate(module, imports);
// ERRO: LinkError - import "env" "log" not found
```

**2. Tipos devem corresponder**

```javascript
// Se o módulo espera uma função (param i32) (result i32)
// mas o host fornece uma função (param i32 i32) (result i32)
const imports = {
    env: {
        log: (a, b) => a + b  // tipo errado
    }
};
// ERRO: LinkError - import type mismatch
```

**3. Limites de memória/tabela devem ser respeitados**

```javascript
// Se o módulo espera memória inicial de 2 páginas
// mas o host fornece memória com 1 página
const imports = {
    env: {
        memory: new WebAssembly.Memory({ initial: 1 })
    }
};
// ERRO: LinkError - memory initial size too small
```

### O modelo de exportações

As exportações permitem que o módulo expor funcionalidade para o host. Elas são tipadas e validadas:

```wat
(module
    ;; Exportar função
    (func $add (param i32 i32) (result i32)
        (i32.add (local.get 0) (local.get 1))
    )
    (export "add" (func $add))

    ;; Exportar memória
    (memory 1)
    (export "memory" (memory 0))

    ;; Exportar tabela
    (table 10 funcref)
    (export "table" (table 0))

    ;; Exportar global
    (global $counter (mut i32) (i32.const 0))
    (export "counter" (global 0))
)
```

### Controle de acesso via importações

O host controla completamente o que o módulo pode acessar. Esse controle é granular:

```javascript
// Host que fornece controle granular
const imports = {
    env: {
        // Somente leitura: módulo pode ler, não pode escrever
        memory: new WebAssembly.Memory({ initial: 1 }),

        // Somente leitura: módulo pode ler a global, não pode modificar
        config: new WebAssembly.Global({ value: 'i32', mutable: false }, 42),

        // Função com verificação
        writeFile: (path, data) => {
            // Verificar se o arquivo é permitido
            if (!isAllowedPath(path)) {
                return -1;  // erro
            }
            return fs.writeFileSync(path, data);
        },

        // Função sem permissão de rede
        // (não importamos nenhuma função de rede)
    }
};

// O módulo NÃO pode:
// - Conectar à rede (não importou funções de rede)
// - Escrever arquivos arbitrários (verificação na função)
// - Modificar config (global é imutável)
```

### Padrões de segurança de importações

**Padrão 1: Funções com verificações**

```javascript
// Funções que verificam permissões antes de executar
const safeImports = {
    env: {
        readFile: (pathPtr, pathLen) => {
            // Ler string da memória do módulo
            const path = readStringFromMemory(pathPtr, pathLen);

            // Verificar permissão
            if (!allowedPaths.some(p => path.startsWith(p))) {
                return -1;  // EACCES
            }

            // Executar operação
            const content = fs.readFileSync(path);
            return writeStringToMemory(content);
        }
    }
};
```

**Padrão 2: Memória compartilhada com isolamento**

```javascript
// Múltiplos módulos com memórias isoladas
function createSandbox() {
    const memory = new WebAssembly.Memory({ initial: 1 });

    return {
        memory: memory,
        exports: {
            read: (offset) => new Uint8Array(memory.buffer)[offset],
            write: (offset, value) => {
                new Uint8Array(memory.buffer)[offset] = value;
            }
        }
    };
}
```

**Padrão 3: Capabilidades limitadas**

```javascript
// Módulo recebe apenas as capabilidades que precisa
function createLimitedModule(capabilities) {
    const imports = {};

    if (capabilities.includes('filesystem')) {
        imports.fs = createFSInterface(capabilities.allowedPaths);
    }

    if (capabilities.includes('network')) {
        imports.net = createNetworkInterface(capabilities.allowedHosts);
    }

    if (capabilities.includes('clock')) {
        imports.time = createClockInterface();
    }

    return imports;
}
```

---

## 2.7 Segurança baseada em capacidades

### Conceito de capability-based security

A segurança baseada em capacidades é um modelo onde o acesso a recursos é determinado pela posse de objetos de acesso (capabilidades), não por identidade (como em sistemas Unix tradicionais). Em um sistema capability-based, não existem listas de controle de acesso (ACLs) — a própria referência ao recurso é a permissão.

No contexto do WebAssembly, isso significa que um módulo só pode acessar recursos para os quais tenha uma referência explícita. Não existe um "usuário" ou "processo" com permissões — apenas o código e suas referências.

### WASI e capabilities

WASI implementa o modelo de capacidades através de:

**1. Descritores pré-abertos**

Módulos WASI recebem descritores de arquivo pré-abertos que representam diretórios ou arquivos específicos. Esses descritores são as capacidades do módulo:

```bash
# O módulo só pode acessar /data (leitura) e /tmp (leitura/escrita)
wasmtime app.wasm --dir /data::read --dir /tmp::read,write
```

**2. Restrição de rede**

O módulo não pode建立 conexões de rede a menos que lhe sejam concedidos sockets:

```bash
# Permitir apenas conexões TCP para hosts específicos
wasmtime app.wasm --tcp-connect example.com:80
```

**3. Restrição de relógio**

O módulo pode acessar relógios apenas se lhe forem concedidos:

```bash
# Sem acesso a relógio
wasmtime app.wasm

# Com acesso a relógio
wasmtime app.wasm --TC=system
```

### Exemplo de capability-based design

```rust
// Servidor que usa capabilities para isolar módulos
use std::collections::HashMap;

struct Capability {
    fs_read: Vec<String>,      // diretórios legíveis
    fs_write: Vec<String>,     // diretórios graváveis
    net_connect: Vec<String>,  // hosts conectáveis
    env_vars: Vec<String>,     // variáveis de ambiente acessíveis
}

fn create_sandboxed_instance(
    module: &[u8],
    capabilities: &Capability,
) -> Result<Instance, Error> {
    let mut imports = HashMap::new();

    // Criar interfae de filesystem com restrições
    if !capabilities.fs_read.is_empty() || !capabilities.fs_write.is_empty() {
        imports.insert("wasi_snapshot_preview1", create_fs_interface(
            &capabilities.fs_read,
            &capabilities.fs_write,
        )?);
    }

    // Criar interface de rede com restrições
    if !capabilities.net_connect.is_empty() {
        imports.insert("wasi_snapshot_preview1", create_net_interface(
            &capabilities.net_connect,
        )?);
    }

    // Criar interface de variáveis de ambiente com restrições
    if !capabilities.env_vars.is_empty() {
        imports.insert("wasi_snapshot_preview1", create_env_interface(
            &capabilities.env_vars,
        )?);
    }

    // Instanciar módulo com capacidades limitadas
    let instance = WebAssembly::instantiate(module, &imports)?;

    Ok(instance)
}

// Exemplo de uso
fn main() {
    let capabilities = Capability {
        fs_read: vec!["/data".to_string(), "/config".to_string()],
        fs_write: vec!["/tmp".to_string()],
        net_connect: vec!["api.example.com:443".to_string()],
        env_vars: vec!["API_KEY".to_string(), "LOG_LEVEL".to_string()],
    };

    let module = std::fs::read("untrusted_module.wasm").unwrap();
    let instance = create_sandboxed_instance(&module, &capabilities).unwrap();

    // O módulo só pode acessar os recursos especificados
}
```

### Comparação com ACLs

| Aspecto | ACLs (Unix) | Capability-based (WASI) |
|---------|-------------|------------------------|
| Modelo | Lista de permissões por objeto | Referência ao recurso é a permissão |
| Revogação | Remover da lista | Remover referência |
| Transferência | Requer kernel | Natural (passar referência) |
| Granularidade | Por arquivo/processo | Por operação específica |
| Delegação | Complexo | Simples (passar capability) |

### Exemplo de delegação de capacidades

```rust
// Módulo A recebe capacidades e pode delegar sub-capacidades para Módulo B
// Mas só dentro dos limites de suas próprias capacidades

// Módulo A: recebe acesso a /data
// Módulo A pode delegar para Módulo B:
//   - /data/subdir (subdiretório de sua capacidade)
//   - Mas NÃO /etc (fora de sua capacidade)

// Isso cria uma hierarquia de confiança onde:
// - O host confia no módulo A
// - O módulo A confia no módulo B
// - O módulo B só pode acessar o que A pode acessar
```

---

## 2.8 Superfície de ataque

### Análise de superfície de ataque

A superfície de ataque do WebAssembly pode ser categorizada em several camadas:

**1. Bytecode malicioso**

Módulos WebAssembly maliciosos podem tentar explorar vulnerabilidades no runtime:

```wat
;; Exemplo de código potencialmente perigoso
(module
    (memory 1)

    ;; Tentar acessar memória fora dos limites
    (func $oob_access (result i32)
        (i32.load (i32.const 999999999))
    )

    ;; Tentar divisão por zero
    (func $div_zero
        (i32.div_s (i32.const 1) (i32.const 0))
    )

    ;; Tentar loop infinito (para testar timeouts)
    (func $infinite_loop
        (block $break
            (loop $loop
                (br $loop)
            )
        )
    )
)
```

**2. Ataques de denial-of-service**

Módulos podem tentar negar serviço consumindo recursos excessivos:

```wat
;; Alocação excessiva de memória
(module
    ;; Tentar alocar memória além do limite
    (func $memory_bomb
        (memory.grow (i32.const 1000000))
        drop
    )

    ;; Loop que consome CPU
    (func $cpu_bomb
        (loop $loop
            (br $loop)
        )
    )
)
```

**3. Ataques de timing**

Módulos podem medir tempos de execução para inferir informações:

```wat
;; Medir tempo de operações
(func $timing_attack
    ;; Se a execução de certa operação varia em tempo
    ;; dependendo de dados secretos, pode haver vazamento
    (local.get $secret)
    ;; ... operação que depende de $secret ...
)
```

**4. Ataques de canal lateral via memória**

Em memória compartilhada, módulos podem usar timing para comunicar:

```wat
;; Comunicação via timing em memória compartilhada
;; (difícil de prevenir, requer runtimes atentos)
```

### Mitigações

**1. Validação estática**

O validador rejeita código que viola invariantes de segurança:

```bash
# Rejeitar módulos com código inválido
wasm-validate malicious.wasm
# Erro: type mismatch: stack has [i32], instruction requires [i32 i32]
```

**2. Limits em memória e tabelas**

Limites definidos na instanciação previnem consumo excessivo:

```javascript
const memory = new WebAssembly.Memory({
    initial: 1,
    maximum: 16  // limita a 16 páginas = 1 MiB
});

// Tentativa de exceder o limite falha
memory.grow(100);  // retorna -1, não aumenta
```

**3. Timeouts**

Runtimes podem implementar timeouts para prevenir loops infinitos:

```javascript
// Wasmtime suporta fuel-based metering
let engine = wasmtime::Engine::new();
let module = wasmtime::Module::new(&engine, wasm_bytes)?;

// Configurar limite de instruções
config.consume_fuel(true);
let mut store = wasmtime::Store::new(&engine, ());
store.set_fuel(1_000_000)?;  // limite de 1M instruções

// Se o módulo exceder o limite, trap é gerada
```

**4. Sandboxing de threads**

Quando threads são usadas, o runtime deve prevenir:

- Deadlocks entre threads
- Races conditions que causem comportamento inseguro
- Consumo excessivo de recursos por threads

### Ataques conhecidos

**Spectre v1 (bounds check bypass)**

Em 2018, foi demonstrado que Spectre poderia ser usado para contornar bounds checks em WebAssembly. A defesa foi implementada nos runtimes:

```javascript
// Mitigação: lfence após cada bounds check
// Isso é implementado nos runtimes, não no código Wasm

// O código Wasm não muda
// A implementação do runtime insere lfence após bounds checks
```

**DeadCodeVulnerability**

Módulos podem conter código inacessível que o validador não analisa. Isso não é um problema de segurança porque código inacessível não é executado, mas pode esconder código malicioso para análise estática.

---

## 2.9 Exemplos de CVEs

### CVE-2017-15113: Buffer overflow em wabt

**Descrição**: Uma vulnerabilidade de buffer overflow foi encontrada na ferramenta wabt (WebAssembly Binary Toolkit) que poderia ser explorada através de um módulo WebAssembly malicioso.

**Impacto**: Execução de código arbitrário no contexto da ferramenta de conversão.

**Lição**: Ferramentas que processam bytecode Wasm precisam das mesmas proteções de segurança que runtimes.

```wat
;; Módulo que poderia explorar a vulnerabilidade
;; (exemplo simplificado)
(module
    ;; Seção de dados com tamanho manipulado
    (memory 1)
    ;; Dados que excedem o buffer alocado
    ;; (detalhes específicos omitidos por segurança)
)
```

### CVE-2018-1000007: Memory leak em wabt

**Descrição**: wabt continha um memory leak que poderia ser explorado através de módulos que alocavam muitas seções customizadas.

**Impacto**: Denial of service por exaustão de memória.

**Lição**: Runtimes e ferramentas precisam limitar recursos consumidos por módulos.

### CVE-2019-13983: Use-after-free em Wasmtime

**Descrição**: Uma vulnerabilidade de use-after-free foi encontrada no Wasmtime que poderia ser explorada através de módulos WebAssembly específicos.

**Impacto**: Potencial execução de código arbitrário.

**Correção**: A vulnerabilidade foi corrigida e um novo release foi publicado.

**Lição**: Runtimes WebAssembly precisam ser revisados e mantidos ativamente.

### CVE-2020-8215: Type confusion em SpiderMonkey

**Descrição**: Uma vulnerabilidade de type confusion foi encontrada no SpiderMonkey (motor JavaScript do Firefox) ao processar módulos WebAssembly.

**Impacto**: Possível execução de código arbitrário no contexto do navegador.

**Lição**: Implementações de runtimes em browsers precisam de auditoria rigorosa.

### CVE-2021-30553: Buffer overflow em V8

**Descrição**: Uma vulnerabilidade de buffer overflow foi encontrada no V8 ao processar código WebAssembly.

**Impacto**: Execução de código arbitrário no contexto do navegador.

**Lição**: Mesmo runtimes maduros podem ter vulnerabilidades — patches de segurança são essenciais.

### CVE-2022-22965: WebAssembly em contexto de chain attack

**Descrição**: Embora não seja uma vulnerabilidade direta do Wasm, essa CVE demonstrou como WebAssembly pode ser usado como parte de uma cadeia de exploração em aplicações web.

**Impacto**: O código Wasm é usado para executar payload malicioso após exploração inicial.

**Lição**: WebAssembly é uma ferramenta que pode ser usada tanto para defesa quanto para ataque.

### Padrões emergentes de vulnerabilidades

| Tipo de CVE | Frequência | Severidade média | Mitigation principal |
|-------------|-----------|-----------------|---------------------|
| Memory safety | Média | Alta | Validação estática, sandbox |
| Type confusion | Baixa | Crítica | Type checking rigoroso |
| DoS via resource exhaustion | Alta | Média | Limites de recursos |
| Side-channel | Baixa | Média | Mitigações no runtime |
| Logic bugs | Variável | Variável | Auditoria de código |

---

## 2.10 Propriedades de segurança

### Propriedades garantidas pela especificação

WebAssembly garante formalmente as seguintes propriedades de segurança:

**1. Type Safety**

Todo código é tipado estaticamente e validado antes da execução. Não é possível misturar tipos ou usar operações com tipos incorretos.

```wat
;; Validação rejeita isso:
(i32.add (i64.const 1) (i32.const 2))
;; Erro: type mismatch - operação i32.add espera (i32, i32)
```

**2. Memory Safety (dentro dos limites)**

Acessos à memória linear são validados e verificados. Fora dos limites, traps são geradas.

```wat
;; Se a memória tem 1 página (64 KiB):
(i32.load (i32.const 65536))  ;; trap: out of bounds
(i32.load (i32.const 65535))  ;; ok: último endereço válido para i32
```

**3. Control Flow Integrity**

O fluxo de controle é validado estaticamente e dinamicamente. Branches e calls são verificados.

```wat
;; call_indirect verifica tipo:
(call_indirect (type $sig) (i32.const 0))
;; Se a função na tabela não tem tipo $sig: trap
```

**4. Absence of Undefined Behavior**

Diferente de C/C++, WebAssembly define comportamento para todas as operações. Não existe "undefined behavior".

```wat
;; Em C: overflow de i32 é undefined behavior
;; Em Wasm: overflow de i32 é definido como wrap-around

;; Em C: divisão por zero pode causar qualquer coisa
;; Em Wasm: divisão por zero causa trap (exceção)
```

**5. Isolation**

Módulos são isolados uns dos outros e do sistema operacional. Sem importações explícitas, não há acesso a recursos.

### Propriedades de segurança do sandbox

| Propriedade | Descrição | Implementação |
|-------------|-----------|---------------|
| Memory isolation | Cada instância tem memória isolada | Runtime separation |
| Resource isolation | Sem acesso a recursos sem importação | Import model |
| Control flow integrity | Fluxo de controle validado | Static validation |
| Type safety | Tipos verificados estaticamente | Type system |
| No undefined behavior | Comportamento sempre definido | Specification |
| Fail-safe defaults | Sem permissão = sem acesso | Capability model |

### Limitações das garantias

Embora as propriedades acima sejam fortes, existem limitações:

**1. O sandbox depende do runtime**

Se o runtime tem vulnerabilidades, o sandbox pode ser comprometido. Isso já aconteceu (CVEs listadas anteriormente).

**2. Side-channels não são eliminados**

Ataques de canal lateral (timing, cache) podem ser possíveis dependendo da implementação do runtime.

**3. Não protege contra bugs lógicos**

Se o código Wasm tem bugs lógicos (cálculos incorretos, erros de design), o sandbox não os detecta.

**4. Não protege contra denegação de serviço**

Módulos podem consumir recursos excessivos se não houver limites configurados.

### Checklist de segurança para runtimes

Ao avaliar ou implementar um runtime WebAssembly, verifique:

- [ ] Validação completa de bytecode antes da execução
- [ ] Bounds checking em todas as operações de memória
- [ ] Type checking em call_indirect
- [ ] Limites configuráveis para memória, tabelas e tempo de execução
- [ ] Isolamento de instâncias
- [ ] Proteção contra side-channels (timing, cache)
- [ ] Proteção contra denial of service
- [ ] Atualizações de segurança regulares
- [ ] Auditoria de código por terceiros
- [ ] Conformidade com especificação W3C

### Formações de referência

1. **Especificação WebAssembly**: https://webassembly.github.io/spec/
2. **WASI Specification**: https://github.com/WebAssembly/WASI
3. **Bytecode Alliance**: https://bytecodealliance.org/
4. **WebAssembly Security**: https://webassembly.org/docs/security/

---

## 2.11 Validação de bytecode em profundidade

### O processo de validação

A validação de bytecode WebAssembly é uma operação O(n) no tamanho do código que verifica invariantes de segurança antes da execução. O validador é parte fundamental do runtime e deve ser implementado corretamente para garantir a segurança.

**Etapas da validação**:

1. **Parsing**: decodificação do formato binário
2. **Verificação de seções**: seções estão presentes e são válidas
3. **Verificação de tipos**: tipos são consistentes
4. **Verificação de função**: corpo da função é válido
5. **Verificação de memória**: acessos a memória são seguros
6. **Verificação de controle**: fluxo de controle é válido

### Validação de tipos

O validador verifica que todas as operações são usadas com os tipos corretos:

```wat
;; Validação rejeita mistura de tipos
(module
    (func $type_mismatch
        ;; ERRO: i32.add espera (i32, i32) mas recebe (i32, i64)
        i32.const 1
        i64.const 2
        i32.add  ;; type mismatch
    )
)

;; Validação aceita coerção explícita
(module
    (func $type_conversion
        ;; OK: usar instrução de conversão
        i64.const 2
        i32.wrap_i64  ;; converte i64 para i32
        i32.const 1
        i32.add  ;; agora ambos são i32
        drop
    )
)
```

### Validação de pilha

O validador simula a pilha de valores para garantir que nunca ocorra underflow ou overflow de tipos:

```wat
;; Validação rejeita underflow
(module
    (func $stack_underflow
        ;; ERRO: tentar usar valor que não está na pilha
        i32.add  ;; pilha está vazia, precisa de 2 operandos
    )
)

;; Validação rejeita overflow de tipos
(module
    (func $stack_overflow
        ;; ERRO: deixar mais de 1 valor na pilha no final
        i32.const 1
        i32.const 2
        ;; Pilha tem 2 valores, função retorna void
    )
)
```

### Validação de controle de fluxo

O validador verifica que branches são válidos:

```wat
;; Validação rejeita branch inválido
(module
    (func $invalid_branch
        block $outer
            block $inner
                ;; ERRO: br 2 não existe (só temos 2 labels)
                br 2
            end
        end
    )
)

;; Validação aceita branches válidos
(module
    (func $valid_branch
        block $outer
            block $inner
                ;; OK: br 0 aponta para $inner
                br 0
                ;; OK: br 1 aponta para $outer
                br 1
            end
        end
    )
)
```

### Validação de memória

O validador verifica acessos a memória:

```wat
;; Validação rejeita acessos inválidos
(module
    (memory 1)  ;; 1 página = 64 KiB

    (func $invalid_access
        ;; ERRO: offset fixo excede limite
        i32.const 0
        i32.load offset=65536  ;; 64 KiB + 4 bytes > limite
    )
)

;; Validação aceita acessos válidos
(module
    (memory 1)

    (func $valid_access
        ;; OK: offset fixo dentro do limite
        i32.const 0
        i32.load offset=0
        drop
    )
)
```

### Implementação de um validador

Exemplo simplificado de validador em Rust:

```rust
#[derive(Debug)]
enum ValidationError {
    TypeMismatch { expected: Vec<Type>, found: Vec<Type> },
    StackUnderflow { needed: usize, available: usize },
    InvalidBranch { depth: usize, max_depth: usize },
    MemoryOutOfBounds { offset: u32, memory_size: u32 },
    InvalidTypeIndex { index: u32, max: u32 },
    ImportMismatch { module: String, name: String },
}

struct Validator {
    types: Vec<FuncType>,
    functions: Vec<u32>,
    memories: Vec<MemoryType>,
    tables: Vec<TableType>,
    globals: Vec<GlobalType>,
    stack: Vec<Type>,
    labels: Vec<Vec<Type>>,
}

impl Validator {
    fn new(module: &Module) -> Self {
        Validator {
            types: module.types.clone(),
            functions: module.functions.clone(),
            memories: module.memories.clone(),
            tables: module.tables.clone(),
            globals: module.globals.clone(),
            stack: Vec::new(),
            labels: Vec::new(),
        }
    }

    fn validate(&mut self) -> Result<(), ValidationError> {
        // Validar seções
        self.validate_sections()?;

        // Validar cada função
        for (i, func) in self.code.iter().enumerate() {
            self.validate_function(i, func)?;
        }

        Ok(())
    }

    fn validate_function(&mut self, index: usize, func: &Function) -> Result<(), ValidationError> {
        // Obter tipo da função
        let type_index = self.functions[index];
        let func_type = &self.types[type_index as usize];

        // Preparar pilha com tipos de parâmetros
        self.stack.clear();
        for param in &func_type.params {
            self.stack.push(*param);
        }

        // Validar instruções
        for instr in &func.body {
            self.validate_instruction(instr)?;
        }

        // Verificar tipos de retorno
        let expected: Vec<Type> = func_type.results.clone();
        let found: Vec<Type> = self.stack.drain(..).collect();

        if expected != found {
            return Err(ValidationError::TypeMismatch { expected, found });
        }

        Ok(())
    }

    fn validate_instruction(&mut self, instr: &Instruction) -> Result<(), ValidationError> {
        match instr {
            Instruction::I32Const(_) => {
                self.stack.push(Type::I32);
            }
            Instruction::I32Add => {
                self.pop_type(Type::I32)?;
                self.pop_type(Type::I32)?;
                self.stack.push(Type::I32);
            }
            Instruction::I32Load { offset, align: _ } => {
                self.pop_type(Type::I32)?;  // endereço
                // Verificar se offset é válido
                if let Some(memory) = self.memories.first() {
                    if *offset + 4 > memory.minimum * 65536 {
                        return Err(ValidationError::MemoryOutOfBounds {
                            offset: *offset,
                            memory_size: memory.minimum * 65536,
                        });
                    }
                }
                self.stack.push(Type::I32);
            }
            // ... outras instruções
            _ => {}
        }
        Ok(())
    }

    fn pop_type(&mut self, expected: Type) -> Result<(), ValidationError> {
        let found = self.stack.pop().ok_or(ValidationError::StackUnderflow {
            needed: 1,
            available: 0,
        })?;

        if found != expected {
            self.stack.push(found);  // devolver à pilha
            return Err(ValidationError::TypeMismatch {
                expected: vec![expected],
                found: vec![found],
            });
        }

        Ok(())
    }
}
```

---

## 2.12 Análise de vetores de ataque detalhada

### Vetores de ataque baseados em memória

**1. Buffer overflow via indexação dinâmica**

```wat
;; Código potencialmente vulnerável (se o runtime não verificar bounds)
(module
    (memory 1)

    (func $unsafe_access (param $index i32) (result i32)
        ;; Se o runtime não verificar bounds:
        ;; $index pode ser qualquer valor, incluindo negativo ou > 64 KiB
        (i32.load (local.get $index))
    )
)
```

O runtime DEVE verificar bounds antes de cada acesso. Se a verificação falhar, um atacante pode ler/escrever memória fora dos limites.

**Mitigação no runtime**:

```rust
fn safe_load(memory: &[u8], index: u32, offset: u32) -> Result<u32, Trap> {
    let effective_index = index.checked_add(offset)
        .ok_or(Trap::IntegerOverflow)?;

    if effective_index + 4 > memory.len() as u32 {
        return Err(Trap::MemoryOutOfBounds);
    }

    let bytes = [
        memory[effective_index as usize],
        memory[effective_index as usize + 1],
        memory[effective_index as usize + 2],
        memory[effective_index as usize + 3],
    ];

    Ok(u32::from_le_bytes(bytes))
}
```

**2. Use-after-free em referências**

Em runtimes que suportam referências (externref), um atacante pode tentar usar referências inválidas:

```wat
(module
    (func $use_after_free (param $ref externref)
        ;; Se o runtime não verificar validade da referência:
        ;; $ref pode apontar para objeto dealocado
        (ref.test externref (local.get $ref))
        drop
    )
)
```

**Mitigação no runtime**:

```rust
fn validate_reference(ref_: &ExternRef) -> Result<(), Trap> {
    // Verificar se a referência é válida
    if !ref_.is_valid() {
        return Err(Trap::InvalidReference);
    }

    // Verificar se o objeto não foi dealocado
    if ref_.is_deallocated() {
        return Err(Trap::UseAfterFree);
    }

    Ok(())
}
```

**3. Integer overflow em offsets**

```wat
(module
    (memory 1)

    (func $overflow_offset (param $base i32) (param $offset i32) (result i32)
        ;; Se $base = 0xFFFFFFFF e $offset = 4:
        ;; $base + $offset = 3 (overflow)
        ;; Poderia acessar endereço 3 em vez de causar trap
        (i32.load offset=0
            (i32.add (local.get $base) (local.get $offset))
        )
    )
)
```

**Mitigação no runtime**:

```rust
fn safe_offset(base: u32, offset: u32) -> Result<u32, Trap> {
    base.checked_add(offset)
        .ok_or(Trap::IntegerOverflow)
}
```

### Vetores de ataque baseados em tempo

**1. Cache-timing side channel**

```wat
;; Código que pode vazar informação via timing
(module
    (memory 1)

    (func $timing_leak (param $secret i32) (param $guess i32) (result i32)
        ;; Se o tempo de execução depende de $secret:
        ;; Um atacante pode medir o tempo e inferir $secret

        ;; Por exemplo: acesso condicional à memória
        (if (i32.eq (local.get $secret) (local.get $guess))
            (then
                ;; Acesso à memória (pode estar em cache)
                (i32.load (i32.const 0))
                drop
            )
            (else
                ;; Não acessa memória
            )
        )

        (i32.const 0)
    )
)
```

**Mitigação**:

```rust
fn constant_time_comparison(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }

    let mut result = 0u8;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }

    result == 0
}
```

**2. Branch prediction side channel**

```wat
;; Código com branch previsível
(module
    (func $branch_leak (param $secret i32) (result i32)
        ;; Branch dependente de dado secreto
        (if (i32.and (local.get $secret) (i32.const 1))
            (then
                ;; Executa código pesado
                (call $heavy_computation)
            )
            (else
                ;; Não executa
            )
        )

        (i32.const 0)
    )
)
```

**Mitigação**:

```rust
// Usar operações sem branch
fn constant_time_if(condition: u32, true_val: u32, false_val: u32) -> u32 {
    // Branchless: condition é 0 ou 1
    (condition & true_val) | ((!condition) & false_val)
}
```

### Vetores de ataque baseados em recursos

**1. Memory exhaustion**

```wat
;; Módulo que tenta alocar memória excessiva
(module
    (memory 1)

    (func $memory_bomb
        ;; Tentar crescer memória além do limite
        (loop $loop
            (memory.grow (i32.const 1000))
            drop
            (br $loop)
        )
    )
)
```

**Mitigação**:

```rust
// Configurar limite máximo de memória
let memory = Memory::new(MemoryType {
    minimum: 1,
    maximum: Some(256),  // máximo 256 páginas = 16 MiB
    memory64: false,
})?;

// Verificar limite antes de crescer
fn grow_memory(current: u32, delta: u32, max: u32) -> Result<u32, Trap> {
    let new_size = current.checked_add(delta)
        .ok_or(Trap::MemoryGrowFailed)?;

    if new_size > max {
        return Err(Trap::MemoryGrowFailed);
    }

    Ok(new_size)
}
```

**2. CPU exhaustion via infinite loop**

```wat
;; Loop infinito que consome CPU
(module
    (func $cpu_bomb
        (block $break
            (loop $loop
                ;; Nenhuma condição de saída
                (br $loop)
            )
        )
    )
)
```

**Mitigação**:

```rust
// Implementar fuel-based metering
struct FuelMeter {
    fuel: u64,
    cost_per_instruction: u64,
}

impl FuelMeter {
    fn consume(&mut self, instructions: u64) -> Result<(), Trap> {
        let cost = instructions * self.cost_per_instruction;
        if self.fuel < cost {
            return Err(Trap::FuelExhausted);
        }
        self.fuel -= cost;
        Ok(())
    }
}

// Custo por tipo de instrução
fn instruction_cost(instr: &Instruction) -> u64 {
    match instr {
        Instruction::Nop => 1,
        Instruction::Block(_) => 1,
        Instruction::Loop(_) => 1,
        Instruction::Br(_) => 1,
        Instruction::BrIf(_) => 1,
        Instruction::Call(_) => 10,
        Instruction::CallIndirect(_) => 20,
        Instruction::I32Load { .. } => 5,
        Instruction::I32Store { .. } => 5,
        Instruction::MemoryGrow => 100,
        _ => 1,
    }
}
```

**3. Stack overflow via recursion**

```wat
;; Recursão infinita que causa stack overflow
(module
    (func $stack_bomb
        (call $stack_bomb)  ;; recursão infinita
    )
)
```

**Mitigação**:

```rust
// Limitar profundidade de chamadas
struct CallStack {
    frames: Vec<Frame>,
    max_depth: usize,
}

impl CallStack {
    fn push(&mut self, frame: Frame) -> Result<(), Trap> {
        if self.frames.len() >= self.max_depth {
            return Err(Trap::CallStackOverflow);
        }
        self.frames.push(frame);
        Ok(())
    }
}
```

### Vetores de ataque em WASI

**1. Path traversal**

```rust
// Módulo WASI tenta acessar arquivo fora do diretório permitido
fn path_traversal_attempt() {
    // Se o runtime não verificar paths:
    let malicious_path = "../../../etc/passwd";
    // O módulo tentaria ler este arquivo
}
```

**Mitigação no runtime WASI**:

```rust
fn validate_path(base_dir: &str, requested_path: &str) -> Result<String, Error> {
    // Normalizar o path
    let normalized = Path::new(requested_path)
        .normalize()
        .map_err(|_| Error::InvalidPath)?;

    // Verificar que não escapou do diretório base
    let full_path = Path::new(base_dir).join(&normalized);
    let canonical = full_path.canonicalize()
        .map_err(|_| Error::PathNotFound)?;

    if !canonical.starts_with(base_dir) {
        return Err(Error::PathTraversal);
    }

    Ok(canonical.to_string_lossy().to_string())
}
```

**2. Symlink attack**

```rust
// Módulo WASI cria symlink para escapar do sandbox
fn symlink_attack() {
    // Se o runtime não verificar symlinks:
    // 1. Criar symlink: /tmp/link -> /etc
    // 2. Acessar: /tmp/link/passwd
    // 3. Efeito: lê /etc/passwd
}
```

**Mitigação**:

```rust
fn safe_open(path: &str, flags: u32) -> Result<FileHandle, Error> {
    // Resolver symlinks
    let resolved = resolve_symlinks(path)?;

    // Verificar que resolved está dentro do sandbox
    if !is_within_sandbox(&resolved) {
        return Err(Error::SandboxEscape);
    }

    // Abrir arquivo
    open_file(&resolved, flags)
}
```

**3. Environment variable injection**

```rust
// Módulo WASI tenta injetar variáveis de ambiente
fn env_injection_attempt() {
    // Se o runtime não filtrar variáveis:
    // 1. Criar variável: LD_PRELOAD=/path/to/malicious.so
    // 2. Processo host carrega biblioteca maliciosa
}
```

**Mitigação**:

```rust
fn filter_env_vars(env: &[(String, String)], allowed: &[String]) -> Vec<(String, String)> {
    env.iter()
        .filter(|(key, _)| {
            // Filtrar variáveis perigosas
            !key.starts_with("LD_") &&
            !key.starts_with("DYLD_") &&
            allowed.contains(key)
        })
        .cloned()
        .collect()
}
```

---

## 2.13 Padrões de projeto para segurança

### Padrão 1: Defense in depth

Implementar múltiplas camadas de segurança:

```rust
struct SecureRuntime {
    validator: Validator,
    memory_manager: MemoryManager,
    fuel_meter: FuelMeter,
    call_stack: CallStack,
    capability_manager: CapabilityManager,
}

impl SecureRuntime {
    fn execute(&mut self, module: &Module) -> Result<(), Error> {
        // Camada 1: Validação estática
        self.validator.validate(module)?;

        // Camada 2: Verificação de capacidades
        self.capability_manager.verify_imports(module)?;

        // Camada 3: Limitação de recursos
        self.fuel_meter.reset(module.estimated_cost());

        // Camada 4: Execução com verificações
        while !self.is_finished() {
            self.fuel_meter.consume(1)?;
            self.call_stack.check_depth()?;
            self.execute_instruction()?;
        }

        Ok(())
    }
}
```

### Padrão 2: Fail-safe defaults

Sempre assumir o pior caso e falhar para um estado seguro:

```rust
fn safe_operation(module: &Module) -> Result<(), Error> {
    // Se não consegue validar: falhar
    // Se não tem permissão: falhar
    // Se excede limite: falhar
    // Se detecta anomalia: falhar

    // Nunca: assumir que é seguro
    // Nunca: continuar com estado inconsistente
    // Nunca: ignorar erros

    validate(module)?;
    check_permissions(module)?;
    enforce_limits(module)?;

    Ok(())
}
```

### Padrão 3: Least privilege

Conceder apenas o necessário:

```rust
fn create_sandbox(module: &Module, requirements: &Requirements) -> Sandbox {
    let mut capabilities = Capabilities::new();

    // Conceder apenas o que o módulo precisa
    if requirements.needs_filesystem {
        capabilities.add_fs_access(&requirements.allowed_paths);
    }

    if requirements.needs_network {
        capabilities.add_network_access(&requirements.allowed_hosts);
    }

    if requirements.needs_clock {
        capabilities.add_clock_access();
    }

    // Não conceder nada mais
    Sandbox::new(module, capabilities)
}
```

### Padrão 4: Input validation

Validar toda entrada de dados:

```rust
fn validate_input(data: &[u8], expected_format: Format) -> Result<(), Error> {
    // Verificar tamanho
    if data.len() > MAX_INPUT_SIZE {
        return Err(Error::InputTooLarge);
    }

    // Verificar formato
    match expected_format {
        Format::Json => validate_json(data)?,
        Format::Protobuf => validate_protobuf(data)?,
        Format::Custom => validate_custom(data)?,
    }

    // Verificar caracteres
    if data.windows(1).any(|w| w[0] == 0) {
        return Err(Error::InvalidNullByte);
    }

    Ok(())
}
```

### Padrão 5: Audit logging

Registrar todas as operações sensíveis:

```rust
struct AuditLogger {
    log_file: File,
}

impl AuditLogger {
    fn log_operation(&mut self, op: &str, module: &str, details: &str) {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let entry = format!(
            "[{}] module={} op={} details={}",
            timestamp, module, op, details
        );

        writeln!(self.log_file, "{}", entry).unwrap();
    }

    fn log_memory_access(&mut self, module: &str, offset: u32, size: u32, is_write: bool) {
        self.log_operation(
            if is_write { "mem_write" } else { "mem_read" },
            module,
            &format!("offset={} size={}", offset, size),
        );
    }

    fn log_syscall(&mut self, module: &str, syscall: &str, args: &[&str]) {
        self.log_operation(
            "syscall",
            module,
            &format!("{}({})", syscall, args.join(", ")),
        );
    }
}
```

---

## 2.14 Comparação com outras plataformas de sandbox

### WebAssembly vs JavaScript Sandbox

| Aspecto | JavaScript (V8) | WebAssembly |
|---------|-----------------|-------------|
| Modelo de segurança | Same-origin policy | Capability-based |
| Isolamento | Isolate | Instance |
| Memória | Heap gerenciado | Linear memory |
| GC | Sim (necessário) | Não (MVP) |
| Validação | Dinâmica | Estática |
| Overhead de segurança | Médio | Baixo |

### WebAssembly vs Native Sandbox (seccomp-bpf)

| Aspecto | seccomp-bpf | WebAssembly |
|---------|-------------|-------------|
| Granularidade | Syscalls | Operações Wasm |
| Overhead | Baixo | Muito baixo |
| Flexibilidade | Limitada | Alta |
| Portabilidade | Linux apenas | Multiplataforma |
| Formal verification | Difícil | Possível |

### WebAssembly vs Container (Docker)

| Aspecto | Docker | WebAssembly |
|---------|--------|-------------|
| Isolamento | Namespace + cgroups | Sandbox + capabilities |
| Overhead | Alto (MBs, 100ms+) | Baixo (KBs, <1ms) |
| Attack surface | Kernel + Docker daemon | Runtime apenas |
| Granularidade | Container | Módulo |
| Flexibilidade | Alta | Média |

---

## 2.15 Formal verification e propriedades prováveis

### O que é formal verification

Formal verification é o processo de provar matematicamente que um sistema satisfaz uma especificação formal. No contexto de WebAssembly, isso significa provar que um runtime implementa corretamente a semântica definida pela especificação.

### Propriedades passíveis de verificação

**1. Type safety**

Propriedade: se o código passa na validação, então todas as operações são usadas com os tipos corretos.

Prova sketch:

```
Para toda instrução I com tipos de entrada T_in e tipos de saída T_out:
  Se a pilha antes de I tem tipos S, então:
    S deve conter T_in como suffix
    A pilha depois de I é (S \ T_in) ++ T_out
```

**2. Memory safety**

Propriedade: todo acesso à memória é dentro dos limites.

Prova sketch:

```
Para toda instrução de load/store com offset O:
  Se o índice na pilha é I, então:
    I + O + sizeof(type) <= memory.size * 65536
    Caso contrário, trap é gerada
```

**3. Control flow integrity**

Propriedade: branches e calls são para locais válidos.

Prova sketch:

```
Para toda instrução br/br_if com rótulo L:
  L é um label válido no escopo atual

Para toda instrução call_indirect com tipo T:
  A função na tabela tem tipo T
  O índice está dentro dos limites da tabela
```

### Ferramentas de verificação

**K Framework**

O K Framework é uma ferramenta para definir semânticas formais de linguagens. Ele foi usado para definir a semântica do WebAssembly.

```k
module WASM-SEMANTICS
    imports WASM-CONFIGURATION
    imports WASM-RULES

    // Configuração do estado
    configuration
        <wasm>
            <k> $PGM:Module </k>
            <mem> .Map </mem>
            <tab> .Map </tab>
            <glob> .Map </glob>
            <stack> .List </stack>
        </wasm>

    // Regras de execução
    rule <k> (i32.const N):Val => N:i32 </k>
         <stack> STACK => STACK | N </stack>

    rule <k> (i32.add):UnOp => R </k>
         <stack> A:i32 | B:i32 | STACK => R </stack>
    where R =Int A +Int B
endmodule
```

**Coq/Rust verification**

```rust
// Exemplo de como uma propriedade poderia ser verificada
// usando Rust + Coq via Creusot

// Propriedade: bounds check é sempre executado
#[ensures(result == true ==> offset + size <= memory_len)]
fn check_bounds(offset: u32, size: u32, memory_len: u32) -> bool {
    offset.checked_add(size)
        .map(|end| end <= memory_len)
        .unwrap_or(false)
}

// Propriedade: tipo check é correto
#[ensures(result == true ==> expected_type == actual_type)]
fn check_type(expected_type: ValType, actual_type: ValType) -> bool {
    expected_type == actual_type
}
```

### Limitações da verificação formal

1. **Complexidade**: a especificação do WebAssembly é complexa, tornando a verificação formal desafiadora
2. **Performance**: provas formais podem ser custosas para produzir e manter
3. **Abstração**: modelos formais podem não capturar todos os detalhes de implementação
4. **Evolução**: a especificação muda, requerendo atualização das provas

---

## 2.16 Estudo de caso: Spectre no WebAssembly

### O ataque Spectre

Spectre é uma classe de vulnerabilidades de canal lateral que explora speculative execution em CPUs modernas. Em 2018, foi demonstrado que Spectre poderia ser usado para contornar bounds checks em WebAssembly.

### Mecanismo do ataque

```wat
;; Código WebAssembly que pode ser explorado via Spectre
(module
    (memory 1)

    (func $leak_byte (param $secret_offset i32) (result i32)
        (local $guess i32)
        (local $probe_offset i32)

        ;; 1. Acessar array com índice speculativamente
        ;; O CPU pode executar speculativamente antes de verificar bounds
        (local.set $guess
            (i32.load8_u
                (i32.add
                    (local.get $secret_offset)
                    (i32.const 0)
                )
            )
        )

        ;; 2. Usar o valor para acessar array de probe
        ;; Isso causa cache side channel
        (local.set $probe_offset
            (i32.mul (local.get $guess) (i32.const 256))
        )

        ;; 3. Acessar array de probe
        (i32.load8_u (local.get $probe_offset))
        drop

        (local.get $guess)
    )
)
```

### Mitigações implementadas

**1. LFENCE após bounds checks**

Runtimes como Wasmtime inserem instruções LFENCE após bounds checks para impedir speculative execution:

```asm
; Assembly x86-64 após bounds check
cmp rax, rcx      ; comparar índice com limite
jge .out_of_bounds ; saltar se fora dos limites
lfence             ; impedir speculative execution
; ... acesso à memória ...
```

**2. Retpoline**

Uma técnica que substitui branches por indirect jumps que não são preditos:

```asm
; Retpoline para call_indirect
call_retpoline:
    call .retpoline_slow
    pause
    jmp call_retpoline
.retpoline_slow:
    call .retpoline_push
    ; ...
```

**3. Array index masking**

Técnica que mascara o índice antes de usar como array index:

```rust
fn safe_array_access(array: &[u8], index: usize) -> u8 {
    let masked_index = index & (array.len() - 1);  // mascara
    array[masked_index]
}
```

### Impacto no WebAssembly

| Mitigação | Overhead | Proteção |
|-----------|----------|----------|
| LFENCE | 5-10% | Completa |
| Retpoline | 10-20% | Completa |
| Array masking | 1-5% | Parcial |
| Configuración de hardware | 0% | Completa (se disponível) |

### Estado atual

Após o disclosure de Spectre, runtimes WebAssembly implementaram mitigações:

- **Wasmtime**: LFENCE após bounds checks (opcional, pode ser desativado)
- **V8**: Combinação de LFENCE e retpoline
- **SpiderMonkey**: LFENCE após bounds checks

---

## 2.17 Checklist de segurança para desenvolvedores

### Antes de compilar

- [ ] Usar linguagem com memory safety (Rust, Go) ou ter certeza que C/C++ é seguro
- [ ] Habilitar todas as verificações de segurança no compilador
- [ ] Usar `-fsanitize=address` e `-fsanitize=undefined` para C/C++
- [ ] Revisar código para bugs de memória
- [ ] Verificar que não há integer overflows intencionais

### Durante a compilação

- [ ] Usar versão estável do compilador
- [ ] Habilitar otimizações que removem código morto
- [ ] Verificar que o módulo passa na validação (`wasm-validate`)
- [ ] Incluir sourcemaps para depuração
- [ ] Não incluir informações sensíveis no binário

### Na implantação

- [ ] Conceder apenas capabilities necessárias
- [ ] Configurar limites de memória
- [ ] Configurar timeout de execução
- [ ] Habilitar logging de segurança
- [ ] Monitorar uso de recursos

### Na operação

- [ ] Monitorar métricas de segurança
- [ ] Revisar logs regularmente
- [ ] Manter runtime atualizado
- [ ] Realizar auditorias de segurança periódicas
- [ ] Testar com ferramentas de fuzzing

### Exemplo de configuração segura

```bash
# Configuração segura para Wasmtime
wasmtime \
    --dir /data::read \
    --dir /tmp::read,write \
    --env API_KEY=secret123 \
    --tcplisten 0.0.0.0:8080 \
    --max-memory 256 \
    --max-stack-size 1048576 \
    --fuel 10000000 \
    app.wasm
```

---

## 2.18 Testing de segurança

### Fuzzing de módulos WebAssembly

Fuzzing é uma técnica de teste que gera entradas aleatórias para encontrar bugs. Para WebAssembly, existem ferramentas específicas:

**wasm-fuzzing**:

```rust
// Exemplo de corpus de fuzzing para um runtime
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {
    // Tentar compilar e instanciar o módulo fuzzed
    if let Ok(module) = wasmtime::Module::new(&ENGINE, data) {
        // Se compilar, tentar instanciar
        let mut store = wasmtime::Store::new(&ENGINE, ());
        let instance = wasmtime::Instance::new(&mut store, &module, &[]);

        // Se instanciar, tentar chamar exports
        if let Ok(instance) = instance {
            // Chamar cada export com dados aleatórios
            for export in instance.exports(&store) {
                if let wasmtime::Extern::Func(func) = export.into_extern() {
                    // Tentar chamar com parâmetros aleatórios
                    let _ = func.call(&mut store, &[]);
                }
            }
        }
    }
});
```

**Configuração de fuzzing**:

```toml
# fuzz/Cargo.toml
[package]
name = "wasm-fuzz"
version = "0.1.0"
edition = "2021"

[dependencies]
libfuzzer-sys = "0.4"
wasmtime = "14.0"

[[bin]]
name = "fuzz_target_1"
path = "fuzz_targets/fuzz_target_1.rs"
test = false
doc = false
bench = false
```

### Testes de propriedade

Property-based testing verifica que propriedades são mantidas para todas as entradas:

```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_valid_module_always_validates(module_bytes in "[0-9]{100,1000}") {
        // Se o módulo é válido, sempre passa na validação
        if let Ok(module) = Module::new(&ENGINE, module_bytes.as_bytes()) {
            let validator = Validator::new(&module);
            prop_assert!(validator.validate().is_ok());
        }
    }

    #[test]
    fn test_oob_access_always_traps(index: u32, offset: u32) {
        // Acesso fora dos limites sempre causa trap
        let memory = Memory::new(MemoryType::new(1, Some(1))).unwrap();
        let result = safe_load(&memory.data(), index, offset);
        prop_assert!(result.is_err());
    }

    #[test]
    fn test_type_mismatch_always_rejects(
        a_type in prop_oneof![Just(Type::I32), Just(Type::I64), Just(Type::F32)],
        b_type in prop_oneof![Just(Type::I32), Just(Type::I64), Just(Type::F32)]
    ) {
        // Tipos diferentes sempre são rejeitados
        let result = validate_operation(Type::I32, a_type, b_type);
        if a_type != Type::I32 || b_type != Type::I32 {
            prop_assert!(result.is_err());
        }
    }
}
```

### Análise estática

Ferramentas de análise estática podem encontrar vulnerabilidades antes da execução:

```rust
// Exemplo de análise estática simples
fn analyze_module(module: &Module) -> Vec<SecurityWarning> {
    let mut warnings = Vec::new();

    // Verificar por padrões perigosos
    for func in &module.code {
        for instr in &func.body {
            match instr {
                Instruction::MemoryGrow(_) => {
                    warnings.push(SecurityWarning::MemoryGrowth {
                        severity: Severity::Medium,
                        message: "Memory growth detected".to_string(),
                    });
                }
                Instruction::CallIndirect { .. } => {
                    warnings.push(SecurityWarning::IndirectCall {
                        severity: Severity::Low,
                        message: "Indirect call detected".to_string(),
                    });
                }
                _ => {}
            }
        }
    }

    warnings
}
```

### Testes de integração de segurança

```rust
#[test]
fn test_sandbox_isolation() {
    // Criar duas instâncias isoladas
    let memory1 = Memory::new(MemoryType::new(1, None)).unwrap();
    let memory2 = Memory::new(MemoryType::new(1, None)).unwrap();

    let instance1 = create_instance(&module, &memory1);
    let instance2 = create_instance(&module, &memory2);

    // Escrever dados na instância 1
    let data1 = [1u8, 2, 3, 4];
    memory1.data()[0..4].copy_from_slice(&data1);

    // Instância 2 não deve ver os dados
    let data2 = [0u8; 4];
    assert_eq!(memory2.data()[0..4], data2);
}

#[test]
fn test_bounds_check_enforced() {
    let memory = Memory::new(MemoryType::new(1, None)).unwrap();
    let instance = create_instance(&module, &memory);

    // Tentar acessar além dos limites
    let result = instance.exports.get::<Memory>("memory")
        .unwrap()
        .data()[65536..65540].copy_from_slice(&[0u8; 4]);

    // Deve falhar (panico ou trap)
    assert!(std::panic::catch_unwind(|| {
        let _ = result;
    }).is_err());
}

#[test]
fn test_type_safety_enforced() {
    let instance = create_instance(&module, &Memory::new(MemoryType::new(1, None)).unwrap());

    // Chamar função com tipos errados
    let func = instance.exports.get::<Func>("add_i32").unwrap();

    // Deve falhar porque i64 não é i32
    let result = func.call(&mut store, &[Val::I64(1), Val::I64(2)]);
    assert!(result.is_err());
}
```

---

## 2.19 Referências e recursos

### Especificação e padrões

1. **Especificação WebAssembly MVP**: https://webassembly.github.io/spec/core/
2. **Especificação WASI**: https://github.com/WebAssembly/WASI
3. **Component Model**: https://github.com/WebAssembly/component-model
4. **WebAssembly Working Group (W3C)**: https://www.w3.org/WoT/WG/

### Runtimes e ferramentas

5. **Wasmtime**: https://wasmtime.dev/ — runtime da Bytecode Alliance
6. **Wasmer**: https://wasmer.io/ — runtime com múltiplos backends
7. **WasmEdge**: https://wasmedge.org/ — runtime para edge computing
8. **WABT**: https://github.com/WebAssembly/wabt — WebAssembly Binary Toolkit
9. **wasm-tools**: https://github.com/bytecodealliance/wasm-tools — ferramentas CLI

### Recursos de segurança

10. **Bytecode Alliance**: https://bytecodealliance.org/ — organização focada em segurança
11. **WebAssembly Security**: https://webassembly.org/docs/security/
12. **Spectre mitigations**: https://github.com/nicowilliams/spectre-mitigation-docs

### Artigos e publicações

13. **"Bringing the Web Up to Speed with WebAssembly"**: artigo acadêmico sobre o design do Wasm
14. **"Spectre mitigations for WebAssembly"**: análise de mitigações de Spectre
15. **"Capability-based Security in WASI"**: modelo de segurança do WASI

---

## 2.20 Glossário de termos de segurança

| Termo | Definição |
|-------|-----------|
| **Sandbox** | Ambiente isolado onde código é executado com restrições |
| **Capability** | Referência que concede acesso a um recurso específico |
| **Trap** | Exceção fatal gerada quando uma operação viola restrições |
| **Bounds check** | Verificação de que acesso à memória está dentro dos limites |
| **Type safety** | Garantia de que operações são usadas com tipos corretos |
| **Control Flow Integrity** | Garantia de que fluxo de execução segue apenas caminhos legítimos |
| **CFI** | Abreviação de Control Flow Integrity |
| **ROP** | Return-Oriented Programming — técnica de exploração |
| **JOP** | Jump-Oriented Programming — técnica de exploração |
| **Spectre** | Classe de vulnerabilidades de canal lateral via speculative execution |
| **Side channel** | Canal de informação que vaza dados através de efeitos colaterais |
| **Linear memory** | Bloco contíguo de bytes acessível pelo código Wasm |
| **Fuel metering** | Técnica para limitar execução contando "combustível" |
| **Preopen** | Descritor de arquivo pré-aberto concedido ao módulo WASI |
| **Validation** | Processo estático de verificação de código antes da execução |
| **Instantiation** | Processo de criar uma instância executável de um módulo |
| **Instance** | Execução concreta de um módulo com seu próprio estado |
| **Module** | Código WebAssembly compilado e validado |
| **Import** | Funcionalidade externa que o módulo consome |
| **Export** | Funcionalidade que o módulo oferece ao mundo exterior |
| **Table** | Array de referências a funções para dispatch dinâmico |
| **Global** | Variável acessível por todo o módulo |
| **Branch** | Instrução que altera o fluxo de execução |
| **Label** | Ponto de destino para branches |
| **Pilha** | Estrutura de dados LIFO para operandos |
| **Frame** | Contexto de execução de uma chamada de função |
| **Pointer** | Endereço na memória linear |
| **Integer overflow** | Resultado de operação inteira que excede o range do tipo |
| **Integer underflow** | Resultado de operação inteira que é menor que o mínimo do tipo |
| **Floating point exception** | Exceção em operações com pontos flutuantes |
| **Denial of Service** | Ataque que torna o serviço indisponível |
| **Resource exhaustion** | Consumo excessivo de recursos (memória, CPU, etc.) |
| **Privilege escalation** | Obtenção de permissões superiores às concedidas |
| **Sandbox escape** | Violação do sandbox que permite acesso não autorizado |
| **Formal verification** | Prova matemática de propriedades de segurança |
| **Fuzzing** | Técnica de teste com entradas aleatórias |
| **Property-based testing** | Testes que verificam propriedades para todas as entradas |
| **Static analysis** | Análise de código sem executá-lo |
| **Dynamic analysis** | Análise de código durante a execução |
| **Memory safety** | Garantia de que acessos à memória são válidos |
| **Temporal safety** | Garantia de que objetos são usados apenas durante sua vida útil |
| **Spatial safety** | Garantia de que acessos são dentro dos limites do objeto |

---

## 2.21 Resumo executivo

### O que você aprendeu

Neste capítulo, exploramos profundamente o modelo de segurança do WebAssembly. Os principais tópicos cobertos incluem:

**Fundamentos de segurança**:

- O modelo de sandbox do Wasm é baseado em especificação, não em configuração externa
- Isolamento de memória garante que instâncias não compartilham dados
- Validação estática verifica código antes da execução
- Controle de fluxo é validado, prevenindo ROP e JOP

**Propriedades garantidas**:

- Type safety: operações são usadas com tipos corretos
- Memory safety: acessos à memória são verificados
- Control flow integrity: branches são para locais válidos
- No undefined behavior: comportamento sempre definido

**Vetores de ataque**:

- Buffer overflow via indexação dinâmica (mitigado por bounds checks)
- Spectre via speculative execution (mitigado por LFENCE)
- Resource exhaustion via loops infinitos (mitigado por fuel metering)
- Path traversal em WASI (mitigado por validação de paths)

**Padrões de projeto**:

- Defense in depth: múltiplas camadas de segurança
- Fail-safe defaults: falhar para estado seguro
- Least privilege: conceder apenas o necessário
- Input validation: validar toda entrada
- Audit logging: registrar operações sensíveis

### Próximos passos

1. Estude o Capítulo 3 sobre WASI para entender como capabilities são implementadas
2. Pratique com ferramentas de validação (wasm-validate, wasm-tools)
3. Implemente fuzzing em seus módulos WebAssembly
4. Revise a configuração de capabilities em suas aplicações
5. Monitore métricas de segurança em produção

### Perguntas para reflexão

1. Como você garantiria que um plugin de terceiros não acessa dados sensíveis?
2. Quais trade-offs existem entre segurança e performance no WebAssembly?
3. Como o modelo de capabilities do WASI se compara ao modelo Unix de permissões?
4. Quais são os riscos de usar WebAssembly em ambientes multi-tenant?
5. Como você testaria se um módulo Wasm respeita os limites de memória?

### Exercícios práticos

1. **Validação de bytecode**: Use `wasm-validate` para verificar módulos compilados
2. **Bounds checking**: Implemente um runtime simples com bounds checking em Rust
3. **Fuzzing**: Configure um corpus de fuzzing para um módulo WebAssembly
4. **Capability audit**: Audite as capabilities de uma aplicação WASI
5. **Spectre mitigation**: Implemente LFENCE após bounds checks em um runtime simples

### Leitura complementar

- **"Security Analysis of WebAssembly Programs"**: análise acadêmica de segurança
- **"Capability-Based Security"**: livro sobre o modelo de capacidades
- **"Spectre: Exploring Speculative Execution"**: paper original do Spectre
- **"Formal Verification of WebAssembly"**: verificação formal de Wasm

---

## Resumo

Neste capítulo, exploramos o modelo de segurança do WebAssembly:

- **Sandbox**: modelo de isolamento baseado em especificação, não em configuração externa
- **Isolamento de memória**: cada instância tem memória linear isolada e independente
- **CFI**: controle de fluxo validado estaticamente, prevenindo ROP/JOP
- **Validação**: toda memória, tabelas e tipos são verificados antes da execução
- **Importações/Exportações**: controle granular de acesso a recursos
- **Capability-based security**: modelo WASI onde acesso é concedido por referência
- **Superfície de ataque**: análise de vetores de ataque e mitigações
- **CVEs**: exemplos reais de vulnerabilidades e lições aprendidas
- **Propriedades garantidas**: type safety, memory safety, CFI, isolation
- **Formal verification**: possibilidades de verificação formal das propriedades
- **Spectre**: estudo de caso de ataque de canal lateral e mitigações
- **Checklists**: guias práticos para desenvolvedores e operadores
- **Testing**: fuzzing, property-based testing e análise estática

O modelo de segurança do WebAssembly é uma das suas principais vantagens competitivas. Ao combinar validação estática, isolamento de memória e capability-based security, o Wasm oferece um nível de segurança que é difícil de alcançar com outras tecnologias. No entanto, é importante lembrar que segurança é uma propriedade sistêmica — o sandbox do Wasm é forte, mas depende de uma implementação correta do runtime e de uma configuração adequada das capacidades.

No próximo capítulo, exploraremos WASI e a interface de sistema em detalhes, onde veremos na prática como o modelo de capacidades é implementado e como ele protege aplicações em produção. Estudaremos como runtimes como Wasmtime e Wasmer implementam as garantias de segurança, e como desenvolvedores podem configurar capabilities de forma segura para diferentes casos de uso.

Essas lições são fundamentais para qualquer profissional que deseja usar WebAssembly em ambientes de produção, seja para edge computing, serverless, plugins de terceiros ou multi-tenancy. A segurança não é uma funcionalidade que se adiciona depois — ela precisa estar incorporada no design desde o início.

Entender o modelo de segurança do WebAssembly é o primeiro passo para construir aplicações seguras e confiáveis. Com esse conhecimento, você estará preparado para enfrentar os desafios de segurança em qualquer projeto que utilize essa tecnologia revolucionária. Lembre-se sempre de aplicar o princípio do menor privilégio e de validar todas as entradas antes de confiar em código de terceiros.

Continue sua jornada de aprendizado explorando o Capítulo 3, onde aprofundaremos no WASI e veremos como as capabilities são implementadas na prática. Estudaremos exemplos reais de aplicações seguras e como configurar runtimes para máximo isolamento. Esse conhecimento será essencial para qualquer projeto de segurança em WebAssembly.

