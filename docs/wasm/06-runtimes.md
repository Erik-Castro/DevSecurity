# Capítulo 6: Runtimes de WebAssembly

## Sumário

- [6.1 Runtimes de navegador (V8, SpiderMonkey, JavaScriptCore)](#61-runtimes-de-navegador-v8-spidermonkey-javascriptcore)
- [6.2 Runtimes WASI (Wasmtime, Wasmer, WasmEdge)](#62-runtimes-wasi-wasmtime-wasmer-wasmedge)
- [6.3 Comparação: Wasmtime vs Wasmer](#63-comparação-wasmtime-vs-wasmer)
- [6.4 Características de performance](#64-características-de-performance)
- [6.5 Incorporação de Wasm em aplicações](#65-incorporação-de-wasm-em-aplicações)
- [6.6 Modelo de segurança dos runtimes](#66-modelo-de-segurança-dos-runtimes)
- [6.7 Sistemas de plugins](#67-sistemas-de-plugins)
- [6.8 Exemplo completo de incorporação em Rust/C++](#68-exemplo-completo-de-incorporação-em-rustcpp)

---

## 6.1 Runtimes de navegador (V8, SpiderMonkey, JavaScriptCore)

### Visão geral

Os runtimes de navegador são motores JavaScript que incluem suporte a WebAssembly. Eles são responsáveis por compilar, otimizar e executar código Wasm dentro do contexto do navegador. Cada navegador principal implementa seu próprio runtime, embora todos sigam a mesma especificação do WebAssembly.

Os runtimes de navegador diferem dos runtimes WASI em vários aspectos fundamentais: eles rodam dentro de um sandbox de navegador, dependem de APIs JavaScript para interação com o sistema, e são otimizados para o caso de uso específico de aplicações web.

### V8 (Chrome, Edge, Opera)

O V8 é o motor JavaScript desenvolvido pelo Google, utilizado no Chrome, Edge, Opera e outros navegadores baseados em Chromium. Ele também é usado no Node.js e Deno.

**Arquitetura do V8 para WebAssembly**:

O V8 implementa o pipeline de compilação do WebAssembly em várias etapas:

1. **Parsing e validação**: O bytecode Wasm é parseado e validado contra a especificação
2. **Decodificação**: O bytecode é decodificado em uma representação interna (IR)
3. **Compilação baseline (Liftoff)**: Compilação rápida para código nativo, sem otimizações
4. **Compilação otimizada (TurboFan)**: Re-compilação com otimizações agressivas
5. **Execução**: Código nativo executado diretamente no processador

```javascript
// O V8 fornece APIs para inspecionar módulos Wasm
const response = await fetch('module.wasm');
const bytes = await response.arrayBuffer();
const module = await WebAssembly.compile(bytes);

// Verificar imports e exports
console.log(WebAssembly.Module.imports(module));
console.log(WebAssembly.Module.exports(module));
```

**Otimizações do V8**:

- **Liftoff**: Compilador baseline que gera código rápido sem otimizações
- **TurboFan**: Compilador otimizador com JIT, inlining, e eliminação de código morto
- **Wasm tier-up**: Transição automática de Liftoff para TurboFan baseado em uso
- **Speculative optimization**: Otimizações baseadas em assumptions verificadas em runtime

**Estatísticas e debugging**:

```javascript
// Habilitar estatísticas no V8
// chrome://flags/#enable-webassembly-tiering

// Usar Chrome DevTools para inspecionar módulos Wasm
// - Sources tab mostra código Wasm decompilado
// - Memory tab mostra heap do Wasm
// - Performance tab mostra profiling do Wasm
```

### SpiderMonkey (Firefox)

O SpiderMonkey é o motor JavaScript desenvolvido pela Mozilla, utilizado no Firefox. A Mozilla foi uma das pioneiras no desenvolvimento do WebAssembly e do asm.js.

**Arquitetura do SpiderMonkey**:

O SpiderMonkey implementa um pipeline similar ao V8, mas com algumas diferenças:

1. **Baseline compiler**: Compilação rápida sem otimizações
2. **WarpBuilder**: Compilador JIT que otimiza código Wasm
3. **IonMonkey**: Compilador otimizador para hot code paths

```javascript
// Firefox fornece APIs de debugging para Wasm
const module = await WebAssembly.compile(bytes);

// Inspecionar no Firefox DevTools
// - Debugger tab permite breakpoints em código Wasm
// - Console permite interagir com módulos Wasm
```

**Recursos únicos do Firefox**:

- **WebAssembly.debugger**: Suporte a breakpoints em código Wasm
- **Source maps**: Integração com source maps para debugging
- **Memory tooling**: Inspeção avançada de memória

### JavaScriptCore (Safari)

O JavaScriptCore (JSC) é o motor JavaScript desenvolvido pela Apple, utilizado no Safari e em aplicações iOS/macOS.

**Arquitetura do JSC**:

O JSC implementa o WebAssembly com foco em eficiência de memória:

1. **LLInt**: Interpretador de baixo nível para código frio
2. **Baseline JIT**: Compilação rápida para código morno
3. **DFG JIT**: Compilador otimizador para código quente
4. **FTL JIT**: Frontend to LLVM, otimizações máximas para hot paths

```javascript
// Safari suporta WebAssembly desde o iOS 11
const module = await WebAssembly.compile(bytes);
const instance = await WebAssembly.instantiate(module);

// Safari DevTools inclui debugging Wasm
```

### Comparação entre runtimes de navegador

| Característica | V8 | SpiderMonkey | JavaScriptCore |
|---------------|-----|--------------|----------------|
| Navegador | Chrome, Edge | Firefox | Safari |
| JIT tiers | 2 (Liftoff, TurboFan) | 2 (Baseline, WarpBuilder) | 4 (LLInt, Baseline, DFG, FTL) |
| Compilação lazy | Sim | Sim | Sim |
| Otimização especulativa | Sim | Sim | Sim |
| Source maps | Sim | Sim | Sim |
| Web Workers | Sim | Sim | Sim |
| SharedArrayBuffer | Sim | Sim | Sim |
| WASI (navegador) | Não | Não | Não |

### Performance dos runtimes de navegador

A performance dos runtimes de navegador varia dependendo do caso de uso:

```javascript
// Benchmark simples
function benchmark(name, fn, iterations = 1000000) {
    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
        fn();
    }
    const end = performance.now();
    console.log(`${name}: ${(end - start).toFixed(2)}ms`);
}

// Usar WebAssembly para computação intensiva
const wasmModule = await WebAssembly.compile(wasmBytes);
const instance = await WebAssembly.instantiate(wasmModule);

benchmark('JavaScript', () => {
    // Código JavaScript
});

benchmark('WebAssembly', () => {
    instance.exports.intensiveComputation();
});
```

### Limitações dos runtimes de navegador

1. **Sandbox restritivo**: Não acesso direto ao sistema de arquivos
2. **Dependência de JavaScript**: I/O e UI requerem chamadas JavaScript
3. **Performance de FFI**: Custo de chamadas entre Wasm e JavaScript
4. **Memória compartilhada limitada**: SharedArrayBuffer com restrições de segurança

### APIs do navegador para Wasm

```javascript
// Carregar e instanciar módulo
const response = await fetch('module.wasm');
const bytes = await response.arrayBuffer();

// Compilar (cacheável)
const module = await WebAssembly.compile(bytes);

// Instanciar com imports
const imports = {
    env: {
        memory: new WebAssembly.Memory({ initial: 256, maximum: 512 }),
        table: new WebAssembly.Table({ initial: 256, element: 'anyfunc' }),
    }
};
const instance = await WebAssembly.instantiate(module, imports);

// Chamar funções exportadas
const result = instance.exports.myFunction(42);
```

---

## 6.2 Runtimes WASI (Wasmtime, Wasmer, WasmEdge)

### Visão geral

Os runtimes WASI (WebAssembly System Interface) são ambientes de execução que permitem rodar código WebAssembly fora do navegador, com acesso controlado a recursos do sistema operacional. Diferentemente dos runtimes de navegador, os runtimes WASI expõem APIs de sistema (arquivos, rede, processos) através da especificação WASI.

### Wasmtime

O Wasmtime é o runtime WebAssembly desenvolvido pelo Bytecode Alliance, uma organização dedicada a promover tecnologias seguras e高效 para WebAssembly. É considerado o runtime de referência para WASI.

**Características principais**:

- Implementação completa de WASI Preview 1 e Preview 2
- Compilador Cranelift para geração de código nativo
- Suporte a WebAssembly System Interface (WASI)
- Embeddable em múltiplas linguagens (C, Rust, Python, Go)
- Foco em segurança e sandboxing

**Instalação**:

```bash
# Linux/macOS
curl https://wasmtime.dev/install.sh -sSf | bash

# Windows
# Download from https://wasmtime.dev/

# Via Cargo (Rust)
cargo install wasmtime-cli
```

**Uso básico**:

```bash
# Executar módulo WASI
wasmtime my_module.wasm

# Executar com argumentos
wasmtime my_module.wasm -- arg1 arg2

# Executar com diretório pré-montado
wasmtime --dir=. my_module.wasm

# Executar com variáveis de ambiente
wasmtime --env KEY=VALUE my_module.wasm
```

**API Rust**:

```rust
use wasmtime::*;

fn main() -> Result<()> {
    // Criar engine e store
    let engine = Engine::default();
    let mut store = Store::new(&engine, ());

    // Carregar módulo
    let module = Module::from_file(&engine, "my_module.wasm")?;

    // Definir imports
    let hello_func = Func::wrap(&mut store, || {
        println!("Hello from Wasmtime!");
    });

    let imports = [hello_func.into()];

    // Instanciar módulo
    let instance = Instance::new(&mut store, &module, &imports)?;

    // Chamar função exportada
    let run = instance.get_typed_func::<(), ()>(&mut store, "run")?;
    run.call(&mut store, ())?;

    Ok(())
}
```

**API C**:

```c
#include <wasm.h>
#include <wasmtime.h>

int main() {
    wasm_engine_t* engine = wasm_engine_new();
    wasmtime_store_t* store = wasmtime_store_new(engine, NULL, NULL);

    // Carregar módulo
    wasm_byte_vec_t wasm_bytes;
    FILE* file = fopen("my_module.wasm", "rb");
    fseek(file, 0, SEEK_END);
    size_t size = ftell(file);
    fseek(file, 0, SEEK_SET);
    wasm_byte_vec_new_uninitialized(&wasm_bytes, size);
    fread(wasm_bytes.data, 1, size, file);
    fclose(file);

    wasmtime_module_t* module;
    wasmtime_module_new(engine, wasm_bytes.data, wasm_bytes.size, &module);

    // Instanciar
    wasmtime_instance_t instance;
    wasmtime_instance_new(store, module, NULL, 0, &instance);

    // Chamar função
    wasmtime_func_t func = wasmtime_instance_func_new(&instance, "run", 3);
    wasmtime_val_t result;
    wasmtime_func_call(store, &func, NULL, 0, &result, 1);

    // Limpar
    wasm_byte_vec_delete(&wasm_bytes);
    wasmtime_module_delete(module);
    wasmtime_store_delete(store);
    wasm_engine_delete(engine);

    return 0;
}
```

### Wasmer

O Wasmer é um runtime WebAssembly independente que suporta múltiplos backends de compilação. Ele se destaca por sua facilidade de uso e suporte a múltiplas linguagens de embed.

**Características principais**:

- Múltiplos backends: Cranelift, LLVM, Singlepass
- Suporte a WASI e WASIX (extensões do Wasmer)
- Pacotes WAPM (WebAssembly Package Manager)
- Embeddable em Rust, C, C++, Python, Go, JavaScript
- Compilação ahead-of-time (AOT) e em tempo de execução

**Instalação**:

```bash
# Via script de instalação
curl https://get.wasmer.io -sSfL | sh

# Via Homebrew (macOS)
brew install wasmer

# Via Cargo
cargo install wasmer-cli

# Via PowerShell (Windows)
iwr https://win.wasmer.io -OutFile install.ps1; .\install.ps1
```

**Uso básico**:

```bash
# Executar módulo
wasmer run my_module.wasm

# Executar com runtime específico
wasmer run --cranelift my_module.wasm
wasmer run --singlepass my_module.wasm
wasmer run --llvm my_module.wasm

# Instalar pacote do WAPM
wasmer run python/python

# Compilar para nativo
wasmer compile my_module.wasm -o my_module_native
```

**API Rust**:

```rust
use wasmer::{Store, Module, Instance, Value, imports};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Criar store com backend específico
    let store = Store::new(Some(&wasmer::Cranelift::new()));

    // Carregar módulo
    let module = Module::from_file(&store, "my_module.wasm")?;

    // Instanciar com imports vazios
    let import_object = imports! {};
    let instance = Instance::new(&module, &import_object)?;

    // Chamar função
    let add = instance.exports.get_function("add")?;
    let result = add.call(&[Value::I32(2), Value::I32(3)])?;
    println!("Result: {:?}", result[0]);

    Ok(())
}
```

**API C**:

```c
#include <wasmer.h>
#include <stdio.h>

int main() {
    // Configurar engine
    wasmer_engine_t* engine = wasmer_engine_new_cranelift();
    wasmer_store_t* store = wasmer_store_new(engine);

    // Carregar módulo
    wasmer_module_t* module;
    wasmer_module_deserialize_file(store, "my_module.wasm", &module);

    // Instanciar
    wasmer_instance_t* instance;
    wasmer_instance_new(module, NULL, 0, &instance);

    // Chamar função
    wasmer_value_t params[] = {{.I32 = 2}, {.I32 = 3}};
    wasmer_value_t results[1];
    wasmer_instance_call(instance, "add", params, 2, results, 1);

    printf("Result: %d\n", results[0].I32);

    // Limpar
    wasmer_instance_destroy(instance);
    wasmer_module_destroy(module);
    wasmer_store_destroy(store);
    wasmer_engine_destroy(engine);

    return 0;
}
```

### WasmEdge

O WasmEdge é um runtime WebAssembly de alta performance, originalmente desenvolvido para edge computing e IoT. Ele se destaca por sua baixa latência e suporte a extensões.

**Características principais**:

- Foco em edge computing e IoT
- Suporte a WASI e extensões proprietárias
- Múltiplos backends (LLVM, AOT)
- Suporte a threading e SIMD
- Extensões para machine learning, networking
- Embeddable em Rust, C, C++, Go, Python

**Instalação**:

```bash
# Linux
curl -sSf https://raw.githubusercontent.com/WasmEdge/WasmEdge/master/utils/install.sh | bash

# macOS
brew install wasmedge

# Via Docker
docker pull wasmedge/wasmedge:latest
```

**Uso básico**:

```bash
# Executar módulo
wasmedge my_module.wasm

# Executar com AOT
wasmedge --dir . my_module.wasm

# Compilar para AOT
wasmedgec my_module.wasm my_module_aot.so

# Executar AOT
wasmedge --dir . my_module_aot.so
```

**API Rust**:

```rust
use wasmedge_sdk::{Vmo, Config, Store};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Criar configuração
    let config = Config::default()
        .with_wasi(true)
        .with_wasm_bulk_memory(true)
        .with_wasm_simd(true);

    // Criar store
    let store = Store::new(Some(config))?;

    // Carregar e instanciar módulo
    let module = Vmo::from_file("my_module.wasm")?;
    let instance = module.run(&store, "main", vec![])?;

    // Obter resultado
    let result = instance.get_global("result")?;
    println!("Result: {:?}", result);

    Ok(())
}
```

**API C**:

```c
#include <wasmedge/wasmedge.h>
#include <stdio.h>

int main() {
    // Configurar
    WasmEdge_ConfigureContext* config = WasmEdge_ConfigureCreate();
    WasmEdge_ConfigureAddWasi(config);

    // Criar runtime
    WasmEdge_VMContext* vm = WasmEdge_VMCreate(config, NULL);

    // Carregar módulo
    WasmEdge_Result result = WasmEdge_VMRunWasmFromFile(
        vm, "my_module.wasm", "main", NULL, 0, NULL, 0
    );

    if (WasmEdge_ResultOK(result)) {
        printf("Execution successful\n");
    } else {
        printf("Error: %s\n", WasmEdge_ResultGetMessage(result));
    }

    // Limpar
    WasmEdge_VMDelete(vm);
    WasmEdge_ConfigureDelete(config);

    return 0;
}
```

### Outros runtimes WASI

**Wasmer Edge**: Versão gerenciada do Wasmer para edge computing
**WAMR (WebAssembly Micro Runtime)**: Runtime leve para IoT e embedded
**Wasm3**: Runtime interpretado ultra-compacto
**Wazero**: Runtime puro Go, sem dependências externas
**wasmRPC**: Runtime focado em chamadas de procedimento remoto

---

## 6.3 Comparação: Wasmtime vs Wasmer

### Visão geral

Wasmtime e Wasmer são os dois runtimes WASI mais populares e maduros. Ambos suportam WASI, possuem múltiplos backends de compilação, e podem ser incorporados em diversas linguagens. No entanto, existem diferenças significativas entre eles.

### Arquitetura

**Wasmtime**:

- Desenvolvido pelo Bytecode Alliance
- Backend padrão: Cranelift (compilador JIT do Mozilla)
- Foco em segurança e conformidade com especificações
- Implementação de referência de WASI

**Wasmer**:

- Desenvolvido pela Wasmer, Inc.
- Múltiplos backends: Cranelift, LLVM, Singlepass
- Foco em usabilidade e ecossistema
- Extensões proprietárias (WASIX)

### Backends de compilação

| Backend | Wasmtime | Wasmer | Descrição |
|---------|----------|--------|-----------|
| Cranelift | Padrão | Suportado | JIT seguro, boa performance |
| LLVM | Não | Suportado | Máxima performance, maior binário |
| Singlepass | Não | Suportado | Compilação rápida, menor performance |
| V8 | Não | Não | (navegador apenas) |

### WASI e extensões

**Wasmtime**:

- WASI Preview 1 completo
- WASI Preview 2 em desenvolvimento
- Foco em conformidade com especificação

**Wasmer**:

- WASI Preview 1 completo
- WASIX: extensões proprietárias (networking, threading)
- WAPM: package manager integrado

### Performance

```
Benchmarks típicos (compilação e execução):

Compilação:
- Wasmtime (Cranelift): ~100ms
- Wasmer (Cranelift): ~100ms
- Wasmer (Singlepass): ~50ms
- Wasmer (LLVM): ~500ms

Execução (fatorial de 40):
- Wasmtime: ~15ms
- Wasmer (Cranelift): ~15ms
- Wasmer (Singlepass): ~25ms
- Wasmer (LLVM): ~12ms
```

### Embedding

**Wasmtime**:

```rust
use wasmtime::*;

let engine = Engine::default();
let module = Module::from_file(&engine, "module.wasm")?;
let instance = Instance::new(&mut store, &module, &imports)?;
```

**Wasmer**:

```rust
use wasmer::{Store, Module, Instance};

let store = Store::new(Some(&wasmer::Cranelift::new()));
let module = Module::from_file(&store, "module.wasm")?;
let instance = Instance::new(&module, &imports)?;
```

### Segurança

**Wasmtime**:

- Sandbox baseado em capacidades
- Validação estática rigorosa
- Memory safety via Cranelift
- Fuzzing contínuo
- Resposta rápida a CVEs

**Wasmer**:

- Sandbox similar ao Wasmtime
- Suporte a múltiplos backends (trade-off segurança vs performance)
- WASIX adiciona superfície de ataque
- Audit de segurança periódico

### Ecossistema

**Wasmtime**:

- Parte do Bytecode Alliance
- Integrado com Rust, C, Python, Go
- Suporte a WASI Preview 2
- Foco em padrões abertos

**Wasmer**:

- Empresa por trás do runtime
- WAPM (package manager)
- Wasmer Edge (edge computing)
- Suporte a 40+ linguagens de embed

### Casos de uso recomendados

**Use Wasmtime quando**:

- Conformidade com especificações é crítica
- Segurança é prioridade máxima
- Precisa de WASI Preview 2
- Está em ambiente enterprise

**Use Wasmer quando**:

- Precisa de múltiplos backends
- Quer usar WASIX (networking, threading)
- Precisa de package manager (WAPM)
- Está em edge computing ou IoT

### Migração entre runtimes

```rust
// Código Wasmtime
use wasmtime::*;

let engine = Engine::default();
let module = Module::from_file(&engine, "module.wasm")?;

// Código Wasmer equivalente
use wasmer::{Store, Module};

let store = Store::new(Some(&wasmer::Cranelift::new()));
let module = Module::from_file(&store, "module.wasm")?;

// A interface é similar, mas não idêntica
// Principais diferenças:
// - Wasmtime usa Engine + Store separados
// - Wasmer usa Store como container principal
// - APIs de imports diferem ligeiramente
```

---

## 6.4 Características de performance

### Fatores que afetam performance

A performance de código WebAssembly depende de vários fatores:

1. **Qualidade do código fonte**: Compiladores produzem melhor código de linguagens estátamente tipadas
2. **Otimizações de compilação**: LTO, inlining, eliminação de código morto
3. **Runtime**: JIT vs AOT vs interpretação
4. **Hardware**: SIMD, threads, cache
5. **Tamanho do módulo**: Módulos menores carregam e compilam mais rápido

### Pipeline de compilação

**Compilação AOT (Ahead-of-Time)**:

```bash
# Wasmer: compilar para nativo
wasmer compile module.wasm -o module_native

# Vantagens: execução instantânea
# Desvantagens: binário maior, sem otimizações adaptativas
```

**Compilação JIT (Just-in-Time)**:

```bash
# Wasmtime: compilar em runtime
wasmtime run module.wasm

# Vantagens: otimizações adaptativas, binário menor
# Desvantagens: latência inicial de compilação
```

**Interpretação**:

```bash
# Wasm3: interpretar bytecode
wasm3 module.wasm

# Vantagens: startup instantâneo, footprint mínimo
# Desvantagens: performance 10-100x menor que JIT
```

### Benchmarks

**CPU-bound (computação numérica)**:

```rust
// Fibonacci recursivo - CPU intensive
fn fibonacci(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

// Resultados (n=40):
// Native (Rust): 15ms
// Wasmtime (JIT): 18ms
// Wasmer (Cranelift): 18ms
// Wasmer (LLVM): 16ms
// Wasmer (Singlepass): 25ms
// JavaScript V8: 45ms
```

**I/O-bound (operações de arquivo)**:

```c
// Leitura de arquivo - I/O intensive
void read_file(const char* path) {
    FILE* f = fopen(path, "r");
    char buffer[1024];
    while (fgets(buffer, sizeof(buffer), f)) {
        // Processar linha
    }
    fclose(f);
}

// Resultados (ler arquivo de 1MB):
// Native: 2ms
// WASI (Wasmtime): 5ms
// WASI (Wasmer): 5ms
// JavaScript (Node.js): 8ms
```

### Otimizações de performance

**1. Usar SIMD quando disponível**:

```c
#include <wasm_simd128.h>

void add_simd(float* a, float* b, float* result, int n) {
    for (int i = 0; i < n; i += 4) {
        v128_t va = wasm_v128_load(&a[i]);
        v128_t vb = wasm_v128_load(&b[i]);
        v128_t vr = wasm_f32x4_add(va, vb);
        wasm_v128_store(&result[i], vr);
    }
}
```

**2. Usar threads para paralelismo**:

```c
#include <pthread.h>

#define NUM_THREADS 4

void* worker(void* arg) {
    int id = *(int*)arg;
    // Processar parte do trabalho
    return NULL;
}

int main() {
    pthread_t threads[NUM_THREADS];
    int ids[NUM_THREADS];

    for (int i = 0; i < NUM_THREADS; i++) {
        ids[i] = i;
        pthread_create(&threads[i], NULL, worker, &ids[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    return 0;
}
```

**3. Minimizar crossing overhead (Wasm <-> Host)**:

```rust
// RUIM: muitas chamadas
for i in 0..1000 {
    host_function(i);  // 1000 crossings
}

// BOM: batch de chamadas
let data: Vec<i32> = (0..1000).collect();
host_function_batch(&data);  // 1 crossing
```

**4. Usar memória compartilhada**:

```rust
use std::sync::Arc;
use std::sync::atomic::{AtomicI32, Ordering};

// Compartilhar dados entre threads sem cópia
let counter = Arc::new(AtomicI32::new(0));

let handles: Vec<_> = (0..4).map(|_| {
    let counter = counter.clone();
    std::thread::spawn(move || {
        for _ in 0..1000000 {
            counter.fetch_add(1, Ordering::SeqCst);
        }
    })
}).collect();
```

### Monitoramento de performance

```rust
use std::time::Instant;

let start = Instant::now();
// Código a ser medido
let duration = start.elapsed();
println!("Execution time: {:?}", duration);
```

```javascript
// JavaScript
const start = performance.now();
// Código a ser medido
const duration = performance.now() - start;
console.log(`Execution time: ${duration}ms`);
```

---

## 6.5 Incorporação de Wasm em aplicações

### Visão geral

A incorporação (embedding) de WebAssembly permite que aplicações nativas carreguem e executem módulos Wasm. Isso é útil para sistemas de plugins, extensões, e sandboxing de código de terceiros.

### Embedding em Rust

**Usando Wasmtime**:

```rust
use wasmtime::*;

struct MyState {
    counter: i32,
}

fn main() -> Result<()> {
    // Criar engine com configuração personalizada
    let engine = Engine::new(
        Config::default()
            .epoch_interruption(true)
            .memory_init_cow(true)
    )?;

    // Criar store com estado personalizado
    let mut store = Store::new(&engine, MyState { counter: 0 });

    // Definir limites de recursos
    store.limiter(|state| &mut StoreLimits::default()
        .memory_size(1024 * 1024 * 100)  // 100MB
        .table_elements(10000)
        .instances(10)
    );

    // Carregar módulo
    let module = Module::from_file(&engine, "plugin.wasm")?;

    // Definir imports
    let host_func = Func::wrap(&mut store, |caller: Caller<'_, MyState>, x: i32| {
        println!("Host function called with: {}", x);
        caller.data_mut().counter += 1;
    });

    let imports = [
        ("host".into(), "log".into(), host_func.into()),
    ];

    // Instanciar
    let instance = Instance::new(&mut store, &module, &imports)?;

    // Chamar função
    let run = instance.get_typed_func::<i32, i32>(&mut store, "run")?;
    let result = run.call(&mut store, 42)?;
    println!("Result: {}", result);

    Ok(())
}
```

**Usando Wasmer**:

```rust
use wasmer::{Store, Module, Instance, Value, imports, Function};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Criar store com backend
    let store = Store::new(Some(&wasmer::Cranelift::new()));

    // Carregar módulo
    let module = Module::from_file(&store, "plugin.wasm")?;

    // Definir imports
    let log_func = Function::new_native(&store, |value: i32| {
        println!("Log: {}", value);
    });

    let import_object = imports! {
        "host" => {
            "log" => log_func,
        }
    };

    // Instanciar
    let instance = Instance::new(&module, &import_object)?;

    // Chamar função
    let run = instance.exports.get_function("run")?;
    let result = run.call(&[Value::I32(42)])?;
    println!("Result: {:?}", result[0]);

    Ok(())
}
```

### Embedding em C++

**Usando Wasmtime C API**:

```cpp
#include <wasm.h>
#include <wasmtime.h>
#include <iostream>
#include <vector>

class WasmRuntime {
private:
    wasm_engine_t* engine;
    wasmtime_store_t* store;

public:
    WasmRuntime() {
        engine = wasm_engine_new();
        store = wasmtime_store_new(engine, this, NULL);
    }

    ~WasmRuntime() {
        wasmtime_store_delete(store);
        wasm_engine_delete(engine);
    }

    bool loadModule(const std::string& path) {
        // Ler arquivo
        FILE* file = fopen(path.c_str(), "rb");
        if (!file) return false;

        fseek(file, 0, SEEK_END);
        size_t size = ftell(file);
        fseek(file, 0, SEEK_SET);

        wasm_byte_vec_t wasm_bytes;
        wasm_byte_vec_new_uninitialized(&wasm_bytes, size);
        fread(wasm_bytes.data, 1, size, file);
        fclose(file);

        // Compilar
        wasmtime_module_t* module;
        wasmtime_module_new(engine, wasm_bytes.data, wasm_bytes.size, &module);

        wasm_byte_vec_delete(&wasm_bytes);
        return module != nullptr;
    }

    void run() {
        // Instanciar e executar
        wasmtime_instance_t instance;
        wasmtime_instance_new(store, module, NULL, 0, &instance);

        wasmtime_func_t func = wasmtime_instance_func_new(&instance, "run", 3);
        wasmtime_val_t result;
        wasmtime_func_call(store, &func, NULL, 0, &result, 1);
    }
};

int main() {
    WasmRuntime runtime;
    if (runtime.loadModule("plugin.wasm")) {
        runtime.run();
    }
    return 0;
}
```

### Embedding em Python

**Usando wasmer-python**:

```python
from wasmer import Engine, Store, Module, Instance, Value, ImportObject, Function

# Criar engine e store
engine = Engine()
store = Store(engine)

# Carregar módulo
module = Module(store, open("plugin.wasm", "rb").read())

# Definir imports
def log_function(value: int):
    print(f"Log: {value}")

import_object = ImportObject({
    "host": {
        "log": Function(store, log_function, [], [])
    }
})

# Instanciar
instance = Instance(module, import_object)

# Chamar função
result = instance.exports.run(42)
print(f"Result: {result}")
```

### Embedding em Go

**Usando wazero**:

```go
package main

import (
    "context"
    "os"
    "github.com/tetratelabs/wazero"
    "github.com/tetratelabs/wazero/api"
    "github.com/tetratelabs/wazero/imports/wasi_snapshot_preview1"
)

func main() {
    ctx := context.Background()

    // Criar runtime
    runtime := wazero.NewRuntime(ctx)

    // Instanciar WASI
    wasi_snapshot_preview1.Instantiate(ctx, runtime)

    // Carregar módulo
    wasmBytes, _ := os.ReadFile("plugin.wasm")
    module, _ := runtime.CompileModule(ctx, wasmBytes)

    // Instanciar
    instance, _ := runtime.InstantiateModule(ctx, module, wazero.NewModuleConfig())

    // Chamar função
    result, _ := instance.ExportedFunction("run").Call(ctx, 42)
    println("Result:", result[0])
}
```

---

## 6.6 Modelo de segurança dos runtimes

### Princípios de segurança

Os runtimes WebAssembly implementam múltiplas camadas de segurança:

1. **Sandboxing de memória**: Acesso limitado a memória linear
2. **Validação estática**: Verificação antes da execução
3. **Controle de acesso baseado em capacidades**: Imports explícitos
4. **Isolamento de instâncias**: Múltiplos módulos isolados
5. **Limitação de recursos**: CPU, memória, tempo de execução

### Sandbox de memória

```cpp
// O módulo só pode acessar sua própria memória linear
// Acesso fora dos limites resulta em trap
extern "C" {
    // Definir memória
    __attribute__((export_name("memory")))
    char memory[1024 * 1024];  // 1MB
}

// Tentativa de acesso ilegal (será interceptada pelo runtime)
void illegal_access() {
    char* ptr = (char*)0xFFFFFFFF;  // Endereço inválido
    *ptr = 'x';  // Trap: out of bounds
}
```

### Validação estática

```cpp
// Antes da execução, o runtime valida:
// 1. Tipos das instruções
// 2. Profundidade da pilha
// 3. Acesso à memória
// 4. Chamadas de função
// 5. Controle de fluxo

// Exemplo de código que PASSA na validação:
(int (i32.const 1) (i32.const 2) (i32.add))

// Exemplo de código que FALHA na validação:
// (i32.add (f32.const 1.0))  // Tipo incompatível
```

### Controle de acesso baseado em capacidades

```rust
// O host controla explicitamente o que o módulo pode acessar
let imports = imports! {
    "wasi_snapshot_preview1" => {
        "fd_write" => wasi_fd_write,  // Permitido
        // "proc_exit" => ...,  // NÃO incluído = não permitido
    }
};

// Módulo só pode usar funções que foram importadas
```

### Isolamento de instâncias

```rust
// Cada instância tem seu próprio espaço de memória
let instance1 = Instance::new(&module1, &imports)?;
let instance2 = Instance::new(&module2, &imports)?;

// instance1 e instance2 NÃO podem se acessar mutuamente
// Não existe mecanismo para compartilhar memória diretamente
```

### Limitação de recursos

```rust
// Configurar limites por instância
let store = Store::new(&engine, ());
store.limiter(|_| &mut StoreLimits::default()
    .memory_size(100 * 1024 * 1024)  // 100MB max
    .table_elements(10000)            // 10k elementos
    .instances(10)                     // 10 instâncias
    .memories(5)                       // 5 memórias
);
```

### Proteção contra ataques comuns

**1. Buffer overflow**:

```cpp
// O Wasm previne buffer overflow via validação estática
// Todo acesso à memória é verificado em runtime
void safe_access(int* array, int index, int value) {
    // O runtime verifica se index está dentro dos limites
    array[index] = value;  // Trap se index for inválido
}
```

**2. Integer overflow**:

```cpp
// Habilitar checks de overflow (menor performance, maior segurança)
// Compile com -ftrapv ou -fsanitize=integer

int32_t safe_add(int32_t a, int32_t b) {
    int32_t result = a + b;
    // Verificar overflow (em release, usar instrução nativa)
    if ((b > 0 && result < a) || (b < 0 && result > a)) {
        // Overflow detectado
        abort();
    }
    return result;
}
```

**3. Code injection**:

```cpp
// Wasm não permite execução de código dinâmico
// Não há como injetar e executar código arbitrário
void no_injection() {
    // Não existe equivalente a eval() em Wasm
    // Código é validado estaticamente antes da execução
}
```

**4. Return-oriented programming (ROP)**:

```cpp
// Wasm não permite retorno para endereços arbitrários
// Controle de fluxo é validado estaticamente
void no_rop() {
    // Não há gadgets úteis para ROP
    // Todas as instruções são verificadas
}
```

### Modelos de segurança por runtime

**Wasmtime**:

- Foco em formally verified components
- Cranelift com propriedades de segurança
- Validação completa de especificação
- Fuzzing contínuo

**Wasmer**:

- Múltiplos backends (trade-off segurança vs performance)
- Singlepass: compilação sem otimizações globais (mais seguro)
- LLVM: otimizações agressivas (menos seguro, mais rápido)

**WasmEdge**:

- Foco em edge computing
- Sandboxing para IoT
- Extensões controladas

### Melhores práticas de segurança

1. **Não confie em código Wasm de terceiros**: Sempre sandbox
2. **Defina limites de recursos**: Memória, CPU, tempo
3. **Use imports mínimos**: Só o que é estritamente necessário
4. **Valide outputs**: Nunca confie cegamente em dados Wasm
5. **Atualize runtimes**: Correções de segurança são frequentes
6. **Use WASI**: Evite APIs proprietárias quando possível
7. **Implemente monitoring**: Detecte comportamento anômalo

---

## 6.7 Sistemas de plugins

### Visão geral

Sistemas de plugins usam WebAssembly para carregar e executar código de terceiros de forma segura. O Wasm fornece sandboxing, controle de recursos, e portabilidade que o tornam ideal para plugins.

### Arquitetura de plugin system

```
Host Application
    |
    +-- Plugin Manager
         |
         +-- Plugin Runtime (Wasmtime/Wasmer)
              |
              +-- Plugin 1 (Wasm module)
              +-- Plugin 2 (Wasm module)
              +-- Plugin N (Wasm module)
```

### Definição de interface de plugin

```wit
// plugin-interface.wit
package example:plugin;

interface guest {
    /// Nome do plugin
    name: func() -> string;

    /// Versão do plugin
    version: func() -> string;

    /// Inicializar plugin
    init: func(config: string) -> result<_, string>;

    /// Processar dados
    process: func(input: list<u8>) -> result<list<u8>, string>;

    /// Finalizar plugin
    fini: func() -> result<_, string>;
}

world plugin {
    export guest;
}
```

### Implementação de plugin em Rust

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct PluginConfig {
    name: String,
    version: String,
    settings: std::collections::HashMap<String, String>,
}

#[no_mangle]
pub extern "C" fn plugin_name() -> *const u8 {
    b"My Plugin\0".as_ptr()
}

#[no_mangle]
pub extern "C" fn plugin_version() -> *const u8 {
    b"1.0.0\0".as_ptr()
}

#[no_mangle]
pub extern "C" fn plugin_init(config_ptr: *const u8, config_len: usize) -> i32 {
    let config_bytes = unsafe {
        std::slice::from_raw_parts(config_ptr, config_len)
    };

    match serde_json::from_slice::<PluginConfig>(config_bytes) {
        Ok(config) => {
            // Inicializar plugin
            println!("Initializing plugin: {}", config.name);
            0  // Sucesso
        }
        Err(_) => -1,  // Erro
    }
}

#[no_mangle]
pub extern "C" fn plugin_process(
    input_ptr: *const u8,
    input_len: usize,
    output_ptr: *mut u8,
    output_len: *mut usize,
) -> i32 {
    let input = unsafe {
        std::slice::from_raw_parts(input_ptr, input_len)
    };

    // Processar dados
    let output = process_data(input);

    // Copiar resultado
    unsafe {
        std::ptr::copy_nonoverlapping(
            output.as_ptr(),
            output_ptr,
            output.len(),
        );
        *output_len = output.len();
    }

    0  // Sucesso
}

#[no_mangle]
pub extern "C" fn plugin_fini() -> i32 {
    println!("Finalizing plugin");
    0  // Sucesso
}

fn process_data(input: &[u8]) -> Vec<u8> {
    // Lógica de processamento
    input.to_vec()
}
```

### Carregador de plugins no host

```rust
use wasmtime::*;
use std::path::Path;

struct Plugin {
    instance: Instance,
    name: Option<String>,
    version: Option<String>,
}

impl Plugin {
    fn load(path: &Path, store: &mut Store<()>) -> Result<Self> {
        let module = Module::from_file(store.engine(), path)?;

        let imports = Self::create_imports(store);

        let instance = Instance::new(store, &module, &imports)?;

        Ok(Plugin {
            instance,
            name: None,
            version: None,
        })
    }

    fn create_imports(store: &mut Store<()>) -> Vec<(String, String, Func)> {
        // Definir imports disponíveis para o plugin
        vec![
            ("host".into(), "log".into(),
             Func::wrap(store, |msg: &str| println!("Plugin: {}", msg))),
        ]
    }

    fn init(&mut self, config: &str, store: &mut Store<()>) -> Result<()> {
        let init_fn = self.instance
            .get_typed_func::<(u32, u32), i32>(store, "plugin_init")?;

        // Alocar memória para config
        let memory = self.instance.get_memory(store, "memory").unwrap();
        let alloc_fn = self.instance
            .get_typed_func::<u32, u32>(store, "alloc")?;

        let config_bytes = config.as_bytes();
        let ptr = alloc_fn.call(store, config_bytes.len() as u32)?;

        // Copiar config para memória do módulo
        memory.data_mut(store)[ptr as usize..ptr as usize + config_bytes.len()]
            .copy_from_slice(config_bytes);

        let result = init_fn.call(store, (ptr, config_bytes.len() as u32))?;

        if result != 0 {
            return Err(anyhow::anyhow!("Plugin init failed"));
        }

        Ok(())
    }

    fn process(&mut self, input: &[u8], store: &mut Store<()>) -> Result<Vec<u8>> {
        let process_fn = self.instance
            .get_typed_func::<(u32, u32, u32, u32), i32>(store, "plugin_process")?;

        // Alocar memória para input e output
        let memory = self.instance.get_memory(store, "memory").unwrap();
        let alloc_fn = self.instance
            .get_typed_func::<u32, u32>(store, "alloc")?;

        let input_ptr = alloc_fn.call(store, input.len() as u32)?;
        let output_ptr = alloc_fn.call(store, input.len() as u32)?;  // Max output size
        let output_len_ptr = alloc_fn.call(store, 4)?;  // u32 para output_len

        // Copiar input
        memory.data_mut(store)[input_ptr as usize..input_ptr as usize + input.len()]
            .copy_from_slice(input);

        let result = process_fn.call(store, (
            input_ptr,
            input.len() as u32,
            output_ptr,
            output_len_ptr,
        ))?;

        if result != 0 {
            return Err(anyhow::anyhow!("Plugin process failed"));
        }

        // Ler output
        let output_len = u32::from_ne_bytes(
            memory.data(store)[output_len_ptr as usize..output_len_ptr as usize + 4]
                .try_into()?
        );

        let output = memory.data(store)
            [output_ptr as usize..output_ptr as usize + output_len as usize]
            .to_vec();

        Ok(output)
    }
}

fn main() -> Result<()> {
    let engine = Engine::default();
    let mut store = Store::new(&engine, ());

    // Carregar plugins
    let mut plugins = Vec::new();
    for entry in std::fs::read_dir("plugins")? {
        let path = entry?.path();
        if path.extension().map_or(false, |e| e == "wasm") {
            let plugin = Plugin::load(&path, &mut store)?;
            plugins.push(plugin);
        }
    }

    // Inicializar plugins
    let config = r#"{"name": "my-plugin", "version": "1.0.0"}"#;
    for plugin in &mut plugins {
        plugin.init(config, &mut store)?;
    }

    // Usar plugins
    let input = b"Hello, Plugin!";
    for plugin in &mut plugins {
        let output = plugin.process(input, &mut store)?;
        println!("Plugin output: {:?}", String::from_utf8_lossy(&output));
    }

    Ok(())
}
```

### Gerenciamento de dependências

```rust
use std::collections::HashMap;

struct PluginManager {
    plugins: HashMap<String, Plugin>,
    dependencies: HashMap<String, Vec<String>>,
}

impl PluginManager {
    fn new() -> Self {
        PluginManager {
            plugins: HashMap::new(),
            dependencies: HashMap::new(),
        }
    }

    fn load_plugin(&mut self, name: &str, path: &Path, store: &mut Store<()>) -> Result<()> {
        // Verificar dependências
        if let Some(deps) = self.dependencies.get(name) {
            for dep in deps {
                if !self.plugins.contains_key(dep) {
                    return Err(anyhow::anyhow!("Missing dependency: {}", dep));
                }
            }
        }

        let plugin = Plugin::load(path, store)?;
        self.plugins.insert(name.to_string(), plugin);
        Ok(())
    }

    fn get_plugin(&mut self, name: &str) -> Option<&mut Plugin> {
        self.plugins.get_mut(name)
    }
}
```

### Segurança de plugins

```rust
struct SecurePluginRuntime {
    engine: Engine,
    store_limits: StoreLimits,
}

impl SecurePluginRuntime {
    fn new() -> Self {
        let engine = Engine::new(
            Config::default()
                .epoch_interruption(true)  // Timeout
                .memory_init_cow(true)     // COW memory
        ).unwrap();

        SecurePluginRuntime {
            engine,
            store_limits: StoreLimits::default()
                .memory_size(50 * 1024 * 1024)  // 50MB max
                .instances(1)                      // 1 instância
                .tables(100)                       // 100 tabelas
                .memories(1)                       // 1 memória
                .fuel_remaining(1_000_000)          // 1M de fuel
        }
    }

    fn create_store(&self) -> Store<()> {
        let mut store = Store::new(&self.engine, ());
        store.limiter(|_| &mut self.store_limits.clone());
        store
    }

    fn load_plugin(&self, path: &Path, store: &mut Store<()>) -> Result<Plugin> {
        let module = Module::from_file(&self.engine, path)?;

        // Verificar que o módulo não usa instruções perigosas
        validate_module(&module)?;

        Plugin::load(path, store)
    }
}

fn validate_module(module: &Module) -> Result<()> {
    // Verificar imports
    for import in module.imports() {
        match import.ty() {
            ExternType::Func(_) => {
                // Verificar se a função é permitida
            }
            ExternType::Memory(_) => {
                // Verificar limites de memória
            }
            _ => {}
        }
    }

    // Verificar exports
    for export in module.exports() {
        match export.ty() {
            ExternType::Func(_) => {
                // Verificar assinatura da função
            }
            _ => {}
        }
    }

    Ok(())
}
```

---

## 6.8 Exemplo completo de incorporação em Rust/C++

### Projeto: Sistema de plugins para processamento de dados

Este exemplo demonstra um sistema completo de plugins usando WebAssembly, com um host em Rust e plugins em Rust/C++.

**Estrutura do projeto**:

```
plugin-system/
├── host/
│   ├── Cargo.toml
│   └── src/
│       └── main.rs
├── plugin-api/
│   ├── Cargo.toml
│   └── src/
│       └── lib.rs
├── plugins/
│   ├── uppercase/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── lib.rs
│   ├── compress/
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── lib.rs
│   └── encrypt/
│       ├── Cargo.toml
│       └── src/
│           └── lib.rs
└── data/
    └── sample.txt
```

**host/Cargo.toml**:

```toml
[package]
name = "plugin-host"
version = "0.1.0"
edition = "2021"

[dependencies]
wasmtime = "16"
anyhow = "1"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
log = "0.4"
env_logger = "0.10"
```

**host/src/main.rs**:

```rust
use wasmtime::*;
use std::path::{Path, PathBuf};
use std::collections::HashMap;
use anyhow::{Result, Context};

struct Plugin {
    name: String,
    instance: Instance,
    store: Store<PluginState>,
}

struct PluginState {
    config: serde_json::Value,
    memory: Vec<u8>,
}

impl Plugin {
    fn new(
        engine: &Engine,
        path: &Path,
        host_log: impl Fn(&str) + 'static,
    ) -> Result<Self> {
        // Carregar módulo
        let module = Module::from_file(engine, path)
            .context("Failed to load plugin module")?;

        // Criar store com estado
        let mut store = Store::new(engine, PluginState {
            config: serde_json::Value::Null,
            memory: Vec::new(),
        });

        // Definir fuel para limitar execução
        store.limiter(|_| &mut StoreLimits::default()
            .fuel_remaining(1_000_000)
            .memory_size(10 * 1024 * 1024)  // 10MB
        );

        // Criar imports
        let host_log_func = Func::wrap(&mut store, move |caller: Caller<'_, PluginState>, ptr: i32, len: i32| {
            if let Some(memory) = caller.get_export("memory") {
                if let Memory::Memory(memory) = memory {
                    let data = &memory.data(&caller)[ptr as usize..(ptr + len) as usize];
                    if let Ok(msg) = std::str::from_utf8(data) {
                        host_log(msg);
                    }
                }
            }
        });

        let host_alloc_func = Func::wrap(&mut store, |caller: Caller<'_, PluginState>, size: i32| -> i32 {
            let state = caller.data();
            state.memory.len() as i32
            // Simplificado: na prática, gerenciaria um allocator
        });

        let imports = [
            ("host".into(), "log".into(), host_log_func.into()),
            ("host".into(), "alloc".into(), host_alloc_func.into()),
        ];

        // Instanciar módulo
        let instance = Instance::new(&mut store, &module, &imports)
            .context("Failed to instantiate plugin")?;

        // Obter nome do plugin
        let get_name = instance.get_typed_func::<(), i32>(&store, "plugin_name")?;
        let name_ptr = get_name.call(&mut store, ())?;

        let memory = instance.get_memory(&store, "memory").unwrap();
        let name_bytes = &memory.data(&store)[name_ptr as usize..];
        let name_end = name_bytes.iter().position(|&b| b == 0).unwrap_or(name_bytes.len());
        let name = String::from_utf8_lossy(&name_bytes[..name_end]).to_string();

        Ok(Plugin {
            name,
            instance,
            store,
        })
    }

    fn init(&mut self, config: serde_json::Value) -> Result<()> {
        self.store.data_mut().config = config.clone();

        // Alocar memória para config
        let config_str = serde_json::to_string(&config)?;
        let alloc_fn = self.instance
            .get_typed_func::<i32, i32>(&self.store, "alloc")?;
        let ptr = alloc_fn.call(&mut self.store, config_str.len() as i32)?;

        // Copiar config para memória
        let memory = self.instance.get_memory(&self.store, "memory").unwrap();
        memory.data_mut(&mut self.store)[ptr as usize..ptr as usize + config_str.len()]
            .copy_from_slice(config_str.as_bytes());

        // Chamar init
        let init_fn = self.instance
            .get_typed_func::<(i32, i32), i32>(&self.store, "plugin_init")?;
        let result = init_fn.call(&mut self.store, (ptr, config_str.len() as i32))?;

        if result != 0 {
            return Err(anyhow::anyhow!("Plugin init failed with code {}", result));
        }

        Ok(())
    }

    fn process(&mut self, input: &[u8]) -> Result<Vec<u8>> {
        // Alocar memória para input
        let alloc_fn = self.instance
            .get_typed_func::<i32, i32>(&self.store, "alloc")?;
        let input_ptr = alloc_fn.call(&mut self.store, input.len() as i32)?;
        let output_ptr = alloc_fn.call(&mut self.store, input.len() as i32 * 2)?;  // Max 2x
        let output_len_ptr = alloc_fn.call(&mut self.store, 4)?;  // u32

        // Copiar input
        let memory = self.instance.get_memory(&self.store, "memory").unwrap();
        memory.data_mut(&mut self.store)[input_ptr as usize..input_ptr as usize + input.len()]
            .copy_from_slice(input);

        // Chamar process
        let process_fn = self.instance
            .get_typed_func::<(i32, i32, i32, i32), i32>(&self.store, "plugin_process")?;
        let result = process_fn.call(&mut self.store, (
            input_ptr,
            input.len() as i32,
            output_ptr,
            output_len_ptr,
        ))?;

        if result != 0 {
            return Err(anyhow::anyhow!("Plugin process failed with code {}", result));
        }

        // Ler output
        let output_len = u32::from_ne_bytes(
            memory.data(&self.store)[output_len_ptr as usize..output_len_ptr as usize + 4]
                .try_into()?
        );

        let output = memory.data(&self.store)
            [output_ptr as usize..output_ptr as usize + output_len as usize]
            .to_vec();

        Ok(output)
    }
}

struct PluginManager {
    engine: Engine,
    plugins: Vec<Plugin>,
}

impl PluginManager {
    fn new() -> Result<Self> {
        let engine = Engine::new(
            Config::default()
                .epoch_interruption(true)
                .memory_init_cow(true)
        )?;

        Ok(PluginManager {
            engine,
            plugins: Vec::new(),
        })
    }

    fn load_plugins_from_dir(&mut self, dir: &Path) -> Result<()> {
        if !dir.exists() {
            return Ok(());
        }

        for entry in std::fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.extension().map_or(false, |e| e == "wasm") {
                match self.load_plugin(&path) {
                    Ok(plugin) => {
                        log::info!("Loaded plugin: {}", plugin.name);
                        self.plugins.push(plugin);
                    }
                    Err(e) => {
                        log::error!("Failed to load plugin {:?}: {}", path, e);
                    }
                }
            }
        }

        Ok(())
    }

    fn load_plugin(&self, path: &Path) -> Result<Plugin> {
        Plugin::new(&self.engine, path, |msg| {
            log::info!("[Plugin] {}", msg);
        })
    }

    fn init_plugins(&mut self, config: serde_json::Value) -> Result<()> {
        for plugin in &mut self.plugins {
            plugin.init(config.clone())?;
        }
        Ok(())
    }

    fn process_with_all_plugins(&mut self, input: &[u8]) -> Result<Vec<u8>> {
        let mut data = input.to_vec();

        for plugin in &mut self.plugins {
            log::info!("Processing with plugin: {}", plugin.name);
            data = plugin.process(&data)?;
        }

        Ok(data)
    }
}

fn main() -> Result<()> {
    env_logger::init();

    log::info!("Starting plugin host");

    // Criar plugin manager
    let mut manager = PluginManager::new()?;

    // Carregar plugins
    let plugins_dir = Path::new("target/wasm32-unknown-unknown/release");
    manager.load_plugins_from_dir(plugins_dir)?;

    // Configuração
    let config = serde_json::json!({
        "plugins": {
            "uppercase": {},
            "compress": {"level": 6},
            "encrypt": {"algorithm": "aes-256"}
        }
    });

    // Inicializar plugins
    manager.init_plugins(config)?;

    // Ler dados de entrada
    let input_data = std::fs::read("data/sample.txt")
        .context("Failed to read input file")?;

    // Processar com todos os plugins
    let output_data = manager.process_with_all_plugins(&input_data)?;

    // Salvar resultado
    std::fs::write("output.txt", &output_data)
        .context("Failed to write output file")?;

    log::info!("Processing complete. Output: {} bytes", output_data.len());

    Ok(())
}
```

**plugin-api/Cargo.toml**:

```toml
[package]
name = "plugin-api"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

**plugin-api/src/lib.rs**:

```rust
use std::alloc::{alloc, dealloc, Layout};
use std::slice;

static mut HOST_LOG: Option<extern "C" fn(i32, i32)> = None;
static mut HOST_ALLOC: Option<extern "C" fn(i32) -> i32> = None;

#[no_mangle]
pub extern "C" fn set_host_log(func: extern "C" fn(i32, i32)) {
    unsafe { HOST_LOG = Some(func); }
}

#[no_mangle]
pub extern "C" fn set_host_alloc(func: extern "C" fn(i32) -> i32) {
    unsafe { HOST_ALLOC = Some(func); }
}

pub fn host_log(msg: &str) {
    unsafe {
        if let Some(func) = HOST_LOG {
            let ptr = msg.as_ptr() as i32;
            let len = msg.len() as i32;
            func(ptr, len);
        }
    }
}

pub fn host_alloc(size: usize) -> *mut u8 {
    unsafe {
        if let Some(func) = HOST_ALLOC {
            let ptr = func(size as i32);
            ptr as *mut u8
        } else {
            // Fallback: usar allocator padrão
            let layout = Layout::from_size_align(size, 8).unwrap();
            unsafe { alloc(layout) }
        }
    }
}

pub unsafe fn string_from_host(ptr: i32, len: i32) -> String {
    let slice = slice::from_raw_parts(ptr as *const u8, len as usize);
    String::from_utf8_unchecked(slice.to_vec())
}

pub unsafe fn string_to_host(s: &str) -> (i32, i32) {
    let ptr = s.as_ptr() as i32;
    let len = s.len() as i32;
    (ptr, len)
}
```

**plugins/uppercase/Cargo.toml**:

```toml
[package]
name = "uppercase-plugin"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
plugin-api = { path = "../../plugin-api" }
```

**plugins/uppercase/src/lib.rs**:

```rust
use plugin_api::*;

#[no_mangle]
pub extern "C" fn plugin_name() -> i32 {
    let name = "uppercase";
    let (ptr, len) = unsafe { string_to_host(name) };
    ptr
}

#[no_mangle]
pub extern "C" fn plugin_version() -> i32 {
    let version = "1.0.0";
    let (ptr, len) = unsafe { string_to_host(version) };
    ptr
}

#[no_mangle]
pub extern "C" fn plugin_init(config_ptr: i32, config_len: i32) -> i32 {
    let config = unsafe { string_from_host(config_ptr, config_len) };
    host_log(&format!("Uppercase plugin initialized with config: {}", config));
    0
}

#[no_mangle]
pub extern "C" fn plugin_process(
    input_ptr: i32,
    input_len: i32,
    output_ptr: i32,
    output_len_ptr: i32,
) -> i32 {
    let input = unsafe {
        let slice = slice::from_raw_parts(input_ptr as *const u8, input_len as usize);
        String::from_utf8_unchecked(slice.to_vec())
    };

    let output = input.to_uppercase();

    unsafe {
        let out_slice = slice::from_raw_parts_mut(output_ptr as *mut u8, output.len());
        out_slice.copy_from_slice(output.as_bytes());

        let len_ptr = output_len_ptr as *mut u32;
        *len_ptr = output.len() as u32;
    }

    0
}

#[no_mangle]
pub extern "C" fn plugin_fini() -> i32 {
    host_log("Uppercase plugin finalized");
    0
}
```

### Compilação

```bash
# Instalar target
rustup target add wasm32-unknown-unknown

# Compilar plugins
cd plugins/uppercase
cargo build --release --target wasm32-unknown-unknown
cd ../..

# Compilar host
cd host
cargo build --release
cd ..
```

### Execução

```bash
# Criar diretório de dados
mkdir -p data
echo "Hello, World! This is a test." > data/sample.txt

# Executar host
RUST_LOG=info ./target/release/plugin-host
```

### Resultado esperado

```
[INFO] Starting plugin host
[INFO] Loaded plugin: uppercase
[INFO] [Plugin] Uppercase plugin initialized with config: {"plugins":{"uppercase":{}}}
[INFO] Processing with plugin: uppercase
[INFO] [Plugin] Uppercase plugin finalized
[INFO] Processing complete. Output: 28 bytes
```

O arquivo output.txt conterá: "HELLO, WORLD! THIS IS A TEST."

### Extensões possíveis

1. **Hot reloading**: Recarregar plugins sem reiniciar o host
2. **Assinatura digital**: Verificar integridade dos plugins
3. **Rate limiting**: Limitar uso de recursos por plugin
4. **Sandboxing avançado**: Restrições por plugin
5. **Persistência**: Estado dos plugins em disco
6. **Comunicação entre plugins**: Passagem de dados entre plugins
7. **Métricas**: Coleta de métricas de uso dos plugins

---

## 6.9 Monitoramento e observabilidade

### Coleta de métricas

O monitoramento de aplicações WebAssembly é essencial para entender comportamento, detectar anomalias e otimizar performance. Os runtimes modernos fornecem APIs para coleta de métricas detalhadas.

**Métricas básicas**:

```rust
use wasmtime::*;
use std::time::Instant;

struct Metrics {
    pub fuel_consumed: u64,
    pub memory_used: usize,
    pub execution_time: std::time::Duration,
    pub call_count: u64,
}

impl Metrics {
    fn new() -> Self {
        Metrics {
            fuel_consumed: 0,
            memory_used: 0,
            execution_time: std::time::Duration::ZERO,
            call_count: 0,
        }
    }
}

struct MonitoredRuntime {
    engine: Engine,
    metrics: std::sync::Arc<std::sync::Mutex<Metrics>>,
}

impl MonitoredRuntime {
    fn new() -> Self {
        let engine = Engine::new(
            Config::default()
                .epoch_interruption(true)
                .consume_fuel(true)
        ).unwrap();

        MonitoredRuntime {
            engine,
            metrics: std::sync::Arc::new(std::sync::Mutex::new(Metrics::new())),
        }
    }

    fn execute(&self, module: &Module, func_name: &str) -> Result<()> {
        let mut store = Store::new(&self.engine, ());
        store.limiter(|_| &mut StoreLimits::default()
            .fuel_remaining(1_000_000)
        );

        let instance = Instance::new(&mut store, &module, &[])?;
        let func = instance.get_typed_func::<(), ()>(&mut store, func_name)?;

        let start = Instant::now();
        func.call(&mut store, ())?;
        let duration = start.elapsed();

        let mut metrics = self.metrics.lock().unwrap();
        metrics.execution_time += duration;
        metrics.call_count += 1;
        metrics.fuel_consumed += 1_000_000 - store.get_fuel().unwrap_or(0);

        Ok(())
    }

    fn get_metrics(&self) -> Metrics {
        self.metrics.lock().unwrap().clone()
    }
}
```

**Coleta de métricas em tempo real**:

```rust
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

struct MetricsCollector {
    counters: Arc<Mutex<HashMap<String, u64>>>,
    gauges: Arc<Mutex<HashMap<String, f64>>>,
    histograms: Arc<Mutex<HashMap<String, Vec<f64>>>>,
}

impl MetricsCollector {
    fn new() -> Self {
        MetricsCollector {
            counters: Arc::new(Mutex::new(HashMap::new())),
            gauges: Arc::new(Mutex::new(HashMap::new())),
            histograms: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    fn increment_counter(&self, name: &str, value: u64) {
        let mut counters = self.counters.lock().unwrap();
        *counters.entry(name.to_string()).or_insert(0) += value;
    }

    fn set_gauge(&self, name: &str, value: f64) {
        let mut gauges = self.gauges.lock().unwrap();
        gauges.insert(name.to_string(), value);
    }

    fn record_histogram(&self, name: &str, value: f64) {
        let mut histograms = self.histograms.lock().unwrap();
        histograms.entry(name.to_string()).or_insert_with(Vec::new).push(value);
    }

    fn get_summary(&self) -> String {
        let counters = self.counters.lock().unwrap();
        let gauges = self.gauges.lock().unwrap();
        let histograms = self.histograms.lock().unwrap();

        let mut summary = String::new();

        summary.push_str("=== Metrics Summary ===\n\n");

        summary.push_str("Counters:\n");
        for (name, value) in counters.iter() {
            summary.push_str(&format!("  {}: {}\n", name, value));
        }

        summary.push_str("\nGauges:\n");
        for (name, value) in gauges.iter() {
            summary.push_str(&format!("  {}: {:.2}\n", name, value));
        }

        summary.push_str("\nHistograms:\n");
        for (name, values) in histograms.iter() {
            let sum: f64 = values.iter().sum();
            let avg = sum / values.len() as f64;
            let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
            let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            summary.push_str(&format!("  {}: count={}, avg={:.2}, min={:.2}, max={:.2}\n",
                name, values.len(), avg, min, max));
        }

        summary
    }
}
```

### Logging estruturado

```rust
use log::{info, warn, error, debug, trace};

struct StructuredLogger {
    module_name: String,
}

impl StructuredLogger {
    fn new(module_name: &str) -> Self {
        StructuredLogger {
            module_name: module_name.to_string(),
        }
    }

    fn log_execution_start(&self, func_name: &str) {
        info!(
            module = self.module_name.as_str(),
            function = func_name,
            "Execution started"
        );
    }

    fn log_execution_end(&self, func_name: &str, duration_ms: f64, success: bool) {
        if success {
            info!(
                module = self.module_name.as_str(),
                function = func_name,
                duration_ms = duration_ms,
                "Execution completed"
            );
        } else {
            error!(
                module = self.module_name.as_str(),
                function = func_name,
                duration_ms = duration_ms,
                "Execution failed"
            );
        }
    }

    fn log_memory_usage(&self, current: usize, peak: usize, limit: usize) {
        debug!(
            module = self.module_name.as_str(),
            memory_current = current,
            memory_peak = peak,
            memory_limit = limit,
            "Memory usage"
        );
    }

    fn log_fuel_consumption(&self, consumed: u64, remaining: u64) {
        trace!(
            module = self.module_name.as_str(),
            fuel_consumed = consumed,
            fuel_remaining = remaining,
            "Fuel consumption"
        );
    }
}
```

### Exportação de métricas

**Prometheus**:

```rust
use prometheus::{Encoder, TextEncoder, Counter, Gauge, Histogram, Registry};

struct PrometheusExporter {
    registry: Registry,
    execution_counter: Counter,
    execution_duration: Histogram,
    memory_usage: Gauge,
}

impl PrometheusExporter {
    fn new() -> Self {
        let registry = Registry::new();

        let execution_counter = Counter::new(
            "wasm_executions_total",
            "Total number of WebAssembly executions"
        ).unwrap();

        let execution_duration = Histogram::with_opts(
            prometheus::HistogramOpts::new(
                "wasm_execution_duration_seconds",
                "WebAssembly execution duration in seconds"
            ).buckets(vec![0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0])
        ).unwrap();

        let memory_usage = Gauge::new(
            "wasm_memory_usage_bytes",
            "Current WebAssembly memory usage in bytes"
        ).unwrap();

        registry.register(Box::new(execution_counter.clone())).unwrap();
        registry.register(Box::new(execution_duration.clone())).unwrap();
        registry.register(Box::new(memory_usage.clone())).unwrap();

        PrometheusExporter {
            registry,
            execution_counter,
            execution_duration,
            memory_usage,
        }
    }

    fn record_execution(&self, duration_secs: f64) {
        self.execution_counter.inc();
        self.execution_duration.observe(duration_secs);
    }

    fn set_memory_usage(&self, bytes: f64) {
        self.memory_usage.set(bytes);
    }

    fn export(&self) -> String {
        let encoder = TextEncoder::new();
        let metric_families = self.registry.gather();
        let mut buffer = Vec::new();
        encoder.encode(&metric_families, &mut buffer).unwrap();
        String::from_utf8(buffer).unwrap()
    }
}
```

**JSON para APIs**:

```rust
use serde::Serialize;

#[derive(Serialize)]
struct MetricsResponse {
    execution_count: u64,
    avg_duration_ms: f64,
    memory_used_mb: f64,
    fuel_consumed: u64,
    active_instances: u32,
}

impl MetricsResponse {
    fn from_metrics(metrics: &Metrics) -> Self {
        MetricsResponse {
            execution_count: metrics.call_count,
            avg_duration_ms: if metrics.call_count > 0 {
                metrics.execution_time.as_millis() as f64 / metrics.call_count as f64
            } else {
                0.0
            },
            memory_used_mb: metrics.memory_used as f64 / (1024.0 * 1024.0),
            fuel_consumed: metrics.fuel_consumed,
            active_instances: 0,  // Implementar contagem
        }
    }

    fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap()
    }
}
```

### Tracing distribuído

```rust
use std::time::Instant;

struct Span {
    name: String,
    start: Instant,
    attributes: std::collections::HashMap<String, String>,
}

impl Span {
    fn new(name: &str) -> Self {
        Span {
            name: name.to_string(),
            start: Instant::now(),
            attributes: std::collections::HashMap::new(),
        }
    }

    fn with_attribute(mut self, key: &str, value: &str) -> Self {
        self.attributes.insert(key.to_string(), value.to_string());
        self
    }

    fn finish(self) -> SpanResult {
        SpanResult {
            name: self.name,
            duration: self.start.elapsed(),
            attributes: self.attributes,
        }
    }
}

struct SpanResult {
    name: String,
    duration: std::time::Duration,
    attributes: std::collections::HashMap<String, String>,
}

struct Tracer {
    spans: std::sync::Arc<std::sync::Mutex<Vec<SpanResult>>>,
}

impl Tracer {
    fn new() -> Self {
        Tracer {
            spans: std::sync::Arc::new(std::sync::Mutex::new(Vec::new())),
        }
    }

    fn start_span(&self, name: &str) -> Span {
        Span::new(name)
    }

    fn end_span(&self, span: Span) {
        let result = span.finish();
        let mut spans = self.spans.lock().unwrap();
        spans.push(result);
    }

    fn export_spans(&self) -> Vec<SpanResult> {
        self.spans.lock().unwrap().clone()
    }
}
```

---

## 6.10 Otimização de runtimes

### Estratégias de otimização

**1. Compilação AOT vs JIT**:

```bash
# AOT: compilar antes da execução
wasmer compile module.wasm -o module_native
# Vantagens: startup instantâneo, performance consistente
# Desvantagens: binário maior, sem otimizações adaptativas

# JIT: compilar durante a execução
wasmtime run module.wasm
# Vantagens: binário menor, otimizações adaptativas
# Desvantagens: latência inicial de compilação
```

**2. Configuração de engines**:

```rust
// Wasmtime: configuração otimizada
let engine = Engine::new(
    Config::default()
        .epoch_interruption(true)
        .memory_init_cow(true)
        .memory_guard_size(65536)
        .parallel_compilation(true)
        .cranelift_opt_level(OptLevel::Speed)
)?;

// Wasmer: backend LLVM para máxima performance
let store = Store::new(Some(&wasmer::LLVM::new()));
```

**3. Uso de fuel para limitar execução**:

```rust
// Definir fuel por instância
let mut store = Store::new(&engine, ());
store.limiter(|_| &mut StoreLimits::default()
    .fuel_remaining(10_000_000)  // 10M de instruções
);

// Consumir fuel durante execução
store.consume_fuel(100)?;  // Consumer 100 unidades

// Verificar fuel restante
let remaining = store.get_fuel()?;
```

**4. Otimização de memória**:

```rust
// Configurar limites de memória
let memory = Memory::new(&mut store, MemoryType::new(256, Some(512)))?;

// Usar memory.init para inicialização eficiente
// Usar memory.copy para cópias em bloco
// Usar memory.fill para preenchimento eficiente
```

**5. Parallelização**:

```rust
use std::sync::Arc;
use std::thread;

// Criar múltiplos stores para execução paralela
let engine = Arc::new(Engine::default());

let handles: Vec<_> = (0..4).map(|_| {
    let engine = engine.clone();
    thread::spawn(move || {
        let mut store = Store::new(&engine, ());
        // Executar módulo
    })
}).collect();

for handle in handles {
    handle.join().unwrap();
}
```

### Benchmarking

```rust
use std::time::Instant;

struct Benchmark {
    name: String,
    iterations: u64,
    results: Vec<std::time::Duration>,
}

impl Benchmark {
    fn new(name: &str, iterations: u64) -> Self {
        Benchmark {
            name: name.to_string(),
            iterations,
            results: Vec::new(),
        }
    }

    fn run<F: FnMut()>(&mut self, mut f: F) {
        for _ in 0..self.iterations {
            let start = Instant::now();
            f();
            self.results.push(start.elapsed());
        }
    }

    fn report(&self) -> String {
        let total: std::time::Duration = self.results.iter().sum();
        let avg = total / self.results.len() as u32;

        let mut sorted = self.results.clone();
        sorted.sort();
        let median = sorted[sorted.len() / 2];
        let p95 = sorted[(sorted.len() as f64 * 0.95) as usize];
        let p99 = sorted[(sorted.len() as f64 * 0.99) as usize];

        format!(
            "Benchmark: {}\n  Iterations: {}\n  Total: {:?}\n  Average: {:?}\n  Median: {:?}\n  P95: {:?}\n  P99: {:?}\n",
            self.name, self.iterations, total, avg, median, p95, p99
        )
    }
}

fn benchmark_wasm_runtime() {
    let engine = Engine::default();
    let module = Module::from_file(&engine, "module.wasm").unwrap();

    let mut bench = Benchmark::new("Wasm Execution", 1000);
    bench.run(|| {
        let mut store = Store::new(&engine, ());
        let instance = Instance::new(&mut store, &module, &[]).unwrap();
        let func = instance.get_typed_func::<(), ()>(&mut store, "run").unwrap();
        func.call(&mut store, ()).unwrap();
    });

    println!("{}", bench.report());
}
```

---

## 6.11 Casos de uso reais

### Edge Computing

```rust
// Edge function usando Wasmtime
use wasmtime::*;

struct EdgeFunction {
    runtime: Engine,
    module: Module,
}

impl EdgeFunction {
    fn new(wasm_path: &str) -> Result<Self> {
        let runtime = Engine::new(
            Config::default()
                .epoch_interruption(true)
                .memory_init_cow(true)
        )?;

        let module = Module::from_file(&runtime, wasm_path)?;

        Ok(EdgeFunction { runtime, module })
    }

    fn execute(&self, request: &Request) -> Result<Response> {
        let mut store = Store::new(&self.runtime, ());
        store.limiter(|_| &mut StoreLimits::default()
            .fuel_remaining(1_000_000)
            .memory_size(50 * 1024 * 1024)
        );

        // Timeout de 100ms
        store.epoch_deadline_callback(|_| {
            Err(anyhow::anyhow!("Execution timeout"))
        });

        let instance = Instance::new(&mut store, &self.module, &[])?;
        let func = instance.get_typed_func::<i32, i32>(&mut store, "handle")?;

        let request_ptr = serialize_request(&mut store, &instance, request)?;
        let response_ptr = func.call(&mut store, request_ptr)?;
        let response = deserialize_response(&store, &instance, response_ptr)?;

        Ok(response)
    }
}
```

### Serverless Functions

```rust
// Serverless function runtime
use wasmtime::*;
use std::collections::HashMap;

struct ServerlessRuntime {
    engine: Engine,
    modules: HashMap<String, Module>,
}

impl ServerlessRuntime {
    fn new() -> Result<Self> {
        let engine = Engine::default();
        Ok(ServerlessRuntime {
            engine,
            modules: HashMap::new(),
        })
    }

    fn load_function(&mut self, name: &str, path: &str) -> Result<()> {
        let module = Module::from_file(&self.engine, path)?;
        self.modules.insert(name.to_string(), module);
        Ok(())
    }

    fn invoke(&self, name: &str, payload: &[u8]) -> Result<Vec<u8>> {
        let module = self.modules.get(name)
            .ok_or_else(|| anyhow::anyhow!("Function not found"))?;

        let mut store = Store::new(&self.engine, ());

        // Configurar limites para serverless
        store.limiter(|_| &mut StoreLimits::default()
            .fuel_remaining(10_000_000)
            .memory_size(128 * 1024 * 1024)  // 128MB
        );

        let instance = Instance::new(&mut store, module, &[])?;

        // Alocar payload na memória
        let memory = instance.get_memory(&store, "memory").unwrap();
        let alloc = instance.get_typed_func::<i32, i32>(&store, "alloc")?;
        let ptr = alloc.call(&mut store, payload.len() as i32)?;

        memory.data_mut(&mut store)[ptr as usize..ptr as usize + payload.len()]
            .copy_from_slice(payload);

        // Chamar função
        let func = instance.get_typed_func::<(i32, i32), i32>(&store, "invoke")?;
        let result_ptr = func.call(&mut store, (ptr, payload.len() as i32))?;

        // Ler resultado
        let result_len = memory.data(&store)[(result_ptr + 4) as usize..(result_ptr + 8) as usize]
            .try_into()
            .map(u32::from_ne_bytes)
            .unwrap_or(0);

        let result = memory.data(&store)
            [result_ptr as usize..result_ptr as usize + result_len as usize]
            .to_vec();

        Ok(result)
    }
}
```

### Plugin Sandboxing

```rust
// Sandboxing avançado para plugins
use wasmtime::*;

struct SandboxedPlugin {
    engine: Engine,
    module: Module,
    limits: StoreLimits,
}

impl SandboxedPlugin {
    fn new(path: &Path, config: PluginConfig) -> Result<Self> {
        let engine = Engine::new(
            Config::default()
                .epoch_interruption(true)
                .memory_init_cow(true)
                .memory_guard_size(65536)
        )?;

        let module = Module::from_file(&engine, path)?;

        // Verificar que o módulo é seguro
        Self::validate_module(&module)?;

        let limits = StoreLimits::default()
            .memory_size(config.max_memory)
            .instances(1)
            .tables(100)
            .memories(1)
            .fuel_remaining(config.max_fuel);

        Ok(SandboxedPlugin { engine, module, limits })
    }

    fn validate_module(module: &Module) -> Result<()> {
        // Verificar imports perigosos
        for import in module.imports() {
            match import.ty() {
                ExternType::Func(func_ty) => {
                    // Verificar se a função é permitida
                    // Implementar allowlist
                }
                ExternType::Memory(mem_ty) => {
                    // Verificar limites de memória
                    if let Some(max) = mem_ty.maximum() {
                        if max > 256 {  // 16MB max
                            return Err(anyhow::anyhow!("Memory limit exceeded"));
                        }
                    }
                }
                _ => {}
            }
        }

        // Verificar que não usa instruções perigosas
        // (wasm_trap, unreachable, etc.)

        Ok(())
    }

    fn execute(&self, input: &[u8]) -> Result<Vec<u8>> {
        let mut store = Store::new(&self.engine, ());
        store.limiter(|_| &mut self.limits.clone());

        // Configurar timeout
        store.epoch_deadline_callback(|_| {
            Err(anyhow::anyhow!("Plugin execution timeout"))
        });

        let instance = Instance::new(&mut store, &self.module, &[])?;

        // Executar com tratamento de erros
        match self.run_plugin(&mut store, &instance, input) {
            Ok(output) => Ok(output),
            Err(e) => {
                log::error!("Plugin execution failed: {}", e);
                Err(e)
            }
        }
    }

    fn run_plugin(&self, store: &mut Store<()>, instance: &Instance, input: &[u8]) -> Result<Vec<u8>> {
        // Implementar execução segura
        todo!()
    }
}
```

### Multi-tenancy

```rust
// Runtime multi-tenant
use wasmtime::*;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

struct Tenant {
    id: String,
    store: Store<TenantState>,
    instance: Instance,
}

struct TenantState {
    name: String,
    limits: StoreLimits,
    usage: UsageMetrics,
}

struct UsageMetrics {
    fuel_consumed: u64,
    memory_used: usize,
    execution_count: u64,
}

struct MultiTenantRuntime {
    engine: Engine,
    tenants: Arc<Mutex<HashMap<String, Tenant>>>,
}

impl MultiTenantRuntime {
    fn new() -> Result<Self> {
        let engine = Engine::new(
            Config::default()
                .epoch_interruption(true)
        )?;

        Ok(MultiTenantRuntime {
            engine,
            tenants: Arc::new(Mutex::new(HashMap::new())),
        })
    }

    fn add_tenant(&self, tenant_id: &str, module: &Module, limits: StoreLimits) -> Result<()> {
        let mut store = Store::new(&self.engine, TenantState {
            name: tenant_id.to_string(),
            limits: limits.clone(),
            usage: UsageMetrics {
                fuel_consumed: 0,
                memory_used: 0,
                execution_count: 0,
            },
        });

        store.limiter(|state| &mut state.limits);

        let instance = Instance::new(&mut store, module, &[])?;

        let tenant = Tenant {
            id: tenant_id.to_string(),
            store,
            instance,
        };

        let mut tenants = self.tenants.lock().unwrap();
        tenants.insert(tenant_id.to_string(), tenant);

        Ok(())
    }

    fn invoke(&self, tenant_id: &str, func_name: &str, args: &[i32]) -> Result<Vec<i32>> {
        let mut tenants = self.tenants.lock().unwrap();
        let tenant = tenants.get_mut(tenant_id)
            .ok_or_else(|| anyhow::anyhow!("Tenant not found"))?;

        let func = tenant.instance.get_typed_func::<(i32, i32), i32>(
            &tenant.store, func_name
        )?;

        let result = func.call(&mut tenant.store, (args[0], args[1]))?;

        tenant.store.data_mut().usage.execution_count += 1;

        Ok(vec![result])
    }

    fn get_tenant_usage(&self, tenant_id: &str) -> Result<UsageMetrics> {
        let tenants = self.tenants.lock().unwrap();
        let tenant = tenants.get(tenant_id)
            .ok_or_else(|| anyhow::anyhow!("Tenant not found"))?;

        Ok(tenant.store.data().usage.clone())
    }
}
```

---

## 6.12 Troubleshooting

### Problemas comuns e soluções

**1. Erro de memória insuficiente**:

```
Error: failed to grow memory
```

Solução:

```rust
// Aumentar limite de memória
let module = Module::from_file(&engine, "module.wasm")?;

// Verificar limits do módulo
for memory in module.memories() {
    println!("Memory: initial={}, maximum={:?}",
        memory.initial(),
        memory.maximum());
}

// Configurar store com mais memória
store.limiter(|_| &mut StoreLimits::default()
    .memory_size(256 * 1024 * 1024)  // 256MB
);
```

**2. Timeout de execução**:

```
Error: epoch deadline reached
```

Solução:

```rust
// Aumentar fuel
store.limiter(|_| &mut StoreLimits::default()
    .fuel_remaining(100_000_000)  // 100M
);

// Ou desabilitar epoch interruption para debug
let config = Config::default()
    .epoch_interruption(false);
```

**3. Import não encontrado**:

```
Error: import not found
```

Solução:

```rust
// Listar imports do módulo
for import in module.imports() {
    println!("Import: {}::{} ({:?})",
        import.module(),
        import.name(),
        import.ty());
}

// Definir todos os imports necessários
let imports = imports! {
    "env" => {
        "memory" => memory,
        "function" => func,
    }
};
```

**4. Tipo incompatível**:

```
Error: type mismatch
```

Solução:

```rust
// Verificar assinatura da função
for export in module.exports() {
    if let ExternType::Func(func_ty) = export.ty() {
        println!("Export: {} -> {:?}", export.name(), func_ty);
    }
}

// Usar tipagem correta
let func = instance.get_typed_func::<(i32, f64), i32>(&store, "my_func")?;
```

**5. Performance ruim**:

```bash
# Verificar se está usando JIT
wasmtime run --wasm tail-call=yes module.wasm

# Usar AOT para startup rápido
wasmer compile module.wasm -o module_native
wasmer run module_native

# Verificar se O3 está habilitado
# No compile time: -C opt-level=3
```

### Debugging avançado

```rust
// Habilitar logging detalhado
env_logger::Builder::from_env(
    env_logger::Env::default().default_filter_or("wasmtime=debug")
).init();

// Usar breakpoints (via GDB/LLDB com source maps)
// Compilar com -g para informações de debug

// Inspecionar estado do store
let fuel = store.get_fuel()?;
let memory = instance.get_memory(&store, "memory")?;
let memory_size = memory.data_size(&store);
println!("Fuel: {}, Memory: {} bytes", fuel, memory_size);
```

### Coleta de diagnósticos

```rust
struct Diagnostics {
    start_time: Instant,
    events: Vec<DiagnosticEvent>,
}

#[derive(Clone)]
struct DiagnosticEvent {
    timestamp: Instant,
    level: LogLevel,
    message: String,
    context: std::collections::HashMap<String, String>,
}

enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
}

impl Diagnostics {
    fn new() -> Self {
        Diagnostics {
            start_time: Instant::now(),
            events: Vec::new(),
        }
    }

    fn log(&mut self, level: LogLevel, message: &str, context: std::collections::HashMap<String, String>) {
        self.events.push(DiagnosticEvent {
            timestamp: Instant::now(),
            level,
            message: message.to_string(),
            context,
        });
    }

    fn export_json(&self) -> String {
        serde_json::to_string_pretty(&self.events).unwrap()
    }

    fn export_summary(&self) -> String {
        let mut summary = String::new();
        let elapsed = self.start_time.elapsed();

        summary.push_str(&format!("Diagnostics Summary\n"));
        summary.push_str(&format!("Duration: {:?}\n", elapsed));
        summary.push_str(&format!("Events: {}\n", self.events.len()));

        let errors = self.events.iter().filter(|e| matches!(e.level, LogLevel::Error)).count();
        let warnings = self.events.iter().filter(|e| matches!(e.level, LogLevel::Warn)).count();

        summary.push_str(&format!("Errors: {}\n", errors));
        summary.push_str(&format!("Warnings: {}\n", warnings));

        summary
    }
}
```

---

## Resumo

Este capítulo cobriu os principais runtimes de WebAssembly e como incorporá-los em aplicações:

1. **Runtimes de navegador**: V8, SpiderMonkey, JavaScriptCore
2. **Runtimes WASI**: Wasmtime, Wasmer, WasmEdge
3. **Comparação Wasmtime vs Wasmer**: Arquitetura, performance, segurança
4. **Características de performance**: Compilação JIT/AOT, otimizações
5. **Incorporação**: Embedding em Rust, C++, Python, Go
6. **Modelo de segurança**: Sandboxing, validação, controle de acesso
7. **Sistemas de plugins**: Arquitetura, implementação, segurança
8. **Exemplo completo**: Sistema de plugins em Rust

Os runtimes de WebAssembly estão evoluindo rapidamente, com foco em performance, segurança e portabilidade. Para aplicações de navegador, os runtimes nativos (V8, SpiderMonkey, JavaScriptCore) são a escolha natural. Para aplicações server-side e edge, Wasmtime e Wasmer oferecem soluções maduras e eficientes.

A incorporação de WebAssembly permite criar sistemas de plugins seguros e portáveis, que podem ser usados em qualquer linguagem suportada. O modelo de segurança baseado em capacidades fornece garantias fortes contra código malicioso, tornando o WebAssembly ideal para execução de código de terceiros.

---

*Fim do Capítulo 6: Runtimes de WebAssembly*
