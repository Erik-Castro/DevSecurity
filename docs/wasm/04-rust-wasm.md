# Capítulo 4: Compilação Rust para WebAssembly

## Sumário

- [4.1 rustup e o target wasm32](#41-rustup-e-o-target-wasm32)
- [4.2 wasm-pack build](#42-wasm-pack-build)
- [4.3 wasm-bindgen FFI](#43-wasm-bindgen-ffi)
- [4.4 trunk framework](#44-trunk-framework)
- [4.5 Frameworks web: leptos e yew](#45-frameworks-web-leptos-e-yew)
- [4.6 wasm-pack test](#46-wasm-pack-test)
- [4.7 wasm-opt optimization](#47-wasm-opt-optimization)
- [4.8 wasm-tools](#48-wasm-tools)
- [4.9 Debugging com console.log](#49-debugging-com-consolelog)
- [4.10 Publicação no npm](#410-publicação-no-npm)
- [4.11 Exemplo de aplicação completa](#411-exemplo-de-aplicação-completa)

---

## 4.1 rustup e o target wasm32

### Instalação do Rust

O Rust é a linguagem de systems programming que mais rapidamente adotou WebAssembly como alvo de compilação de primeira classe. O ecossistema Rust para Wasm é maduro, bem documentado e amplamente utilizado em produção. Antes de compilar código Rust para WebAssembly, é necessário configurar o toolchain corretamente.

O Rust é gerenciado pelo rustup, um instalador e gerenciador de versões que permite alternar entre diferentes toolchains e targets de compilação. O rustup é a ferramenta oficial recomendada pela equipe do Rust para instalação e manutenção do compilador.

Para instalar o Rust em sistemas Unix-like (Linux, macOS, WSL):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Para instalar em Windows, o recomendado é usar o instalador disponível em https://rustup.rs.

Após a instalação, o rustup instala automaticamente a toolchain estável, que inclui o compilador rustc, o gerenciador de pacotes cargo e o formatador rustfmt. A instalação padrão coloca os binários em ~/.cargo/bin.

### Verificação da instalação

Após instalar, verifique a versão do compilador:

```bash
rustc --version
# Exemplo de saída: rustc 1.75.0 (82e1608df 2023-12-21)

cargo --version
# Exemplo de saída: cargo 1.75.0 (1d8ca0466 2023-11-20)
```

É recomendável manter o Rust atualizado, pois as versões mais recentes frequentemente incluem melhorias significativas na geração de código WebAssembly e correções de bugs no compilador.

### O target wasm32-unknown-unknown

O Rust suporta múltiplos targets de compilação através do sistema de target triples. Para WebAssembly, o target principal é wasm32-unknown-unknown. Esse target triple indica:

- **wasm32**: Arquitetura WebAssembly de 32 bits
- **unknown**: Sistema operacional não especificado (genérico)
- **unknown**: Abi (Application Binary Interface) não especificada

Para adicionar o target wasm32-unknown-unknown ao seu toolchain:

```bash
rustup target add wasm32-unknown-unknown
```

Esse comando baixa o stdlib (biblioteca padrão) pré-compilada para o target wasm32 e a instala no diretório de targets do rustup. Sem essa etapa, o compilador não conseguirá resolver as dependências padrão do Rust ao compilar para WebAssembly.

### Estrutura de targets

O rustup organiza os targets em uma estrutura de diretórios específica:

```
~/.rustup/toolchains/
  stable-x86_64-unknown-linux-gnu/
    lib/
      rustlib/
        wasm32-unknown-unknown/
          lib/
            libstd-*.rlib
            libcore-*.rlib
            liballoc-*.rlib
```

Cada target contém uma cópia da biblioteca padrão compilada para a arquitetura e plataforma específicas. O target wasm32-unknown-unknown inclui apenas a biblioteca std que não depende de funcionalidades específicas do sistema operacional, já que WebAssembly não expõe interface de sistema nativa.

### Diferença entre targets Wasm

O Rust oferece múltiplos targets WebAssembly, cada um com características diferentes:

| Target | Descrição | Uso Principal |
|--------|-----------|---------------|
| wasm32-unknown-unknown | Genérico, sem dependências | Navegador, sem WASI |
| wasm32-wasi | Suporte WASI completo | Servidor, CLI |
| wasm32-wasip1 | WASI Preview 1 (novo nome) | Servidor, CLI |
| wasm32-unknown-emscripten | Compilação via Emscripten | Compatibilidade Emscripten |
| wasm32-wasip1-threads | WASI com suporte a threads | Servidor com paralelismo |

O target wasm32-unknown-unknown é o mais utilizado para aplicações Web, pois gera código que não depende de nenhuma interface de sistema. Para aplicações WASI, o target wasm32-wasi (ou wasm32-wasip1) é o apropriado, pois inclui bindings para o WebAssembly System Interface.

### Configuração do Cargo.toml

Para projetos que sempre compilam para WebAssembly, você pode configurar o target padrão no Cargo.toml:

```toml
[build]
target = "wasm32-unknown-unknown"
```

Alternativamente, você pode criar um arquivo .cargo/config.toml na raiz do projeto:

```toml
[build]
target = "wasm32-unknown-unknown"

[target.wasm32-unknown-unknown]
rustflags = ["-C", "target-feature=+simd128"]
```

### Profiles de compilação

O Rust permite definir profiles de compilação que controlam otimizações, depuração e other opções. Para WebAssembly, é comum definir profiles específicos:

```toml
[profile.release]
opt-level = "z"      # Otimizar para tamanho
lto = true           # Link-Time Optimization
codegen-units = 1    # Máxima otimização
panic = "abort"      # Não usar unwinding
strip = true         # Remover símbolos

[profile.dev]
opt-level = 0        # Sem otimizações (debug)
debug = true         # Incluir informações de debug
```

O opt-level "z" é especialmente importante para WebAssembly, pois reduz significativamente o tamanho do binário final. O panic = "abort" remove o suporte a stack unwinding, que não é suportado pela maioria dos runtimes WebAssembly e adiciona overhead desnecessário.

### Atualização e gerenciamento de versões

O rustup permite gerenciar múltiplas versões do compilador. Para listar as versões disponíveis:

```bash
rustup show                   # Mostra a toolchain ativa
rustup toolchain list         # Lista toolchains instaladas
rustup update                 # Atualiza todas as toolchains
rustup check                  # Verifica atualizações disponíveis
```

Para usar uma versão específica do compilador (por exemplo, nightly para funcionalidades experimentais):

```bash
rustup toolchain install nightly
rustup target add wasm32-unknown-unknown --toolchain nightly
rustup run nightly cargo build --target wasm32-unknown-unknown
```

O toolchain nightly inclui funcionalidades experimentais que podem ser necessárias para uso avançado de WebAssembly, como WebAssembly GC proposal, exception handling e other proposals em estágio de teste.

### Considerações de segurança

Ao configurar o toolchain Rust para WebAssembly, algumas considerações de segurança são importantes:

1. **Verificação de integridade**: O rustup verifica automaticamente a integridade das assinaturas das toolchains baixadas
2. **Target isolation**: Cada target é compilado isoladamente, sem acesso a funcionalidades do sistema host
3. **Profile de compilação**: Use panic = "abort" para minimizar superfície de ataque
4. **LTO**: Link-Time Optimization pode remover código morto que aumentaria a superfície de ataque

```toml
# Configuração segura para produção
[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
panic = "abort"
strip = true
overflow-checks = true  # Manter checks de overflow
```

---

## 4.2 wasm-pack build

### Introdução ao wasm-pack

O wasm-pack é a ferramenta oficial para construir, testar e publicar pacotes WebAssembly gerados a partir de código Rust. Ele integra múltiplas ferramentas em um único comando, automatizando o processo de compilação, ligação com wasm-bindgen e empacotamento para diferentes ambientes (npm, bundlers, web).

O wasm-pack foi criado pela equipe do Rust/Wasm e se tornou a ferramenta padrão para o desenvolvimento de bibliotecas e aplicações Rust que rodam em WebAssembly. Ele simplifica significativamente o workflow de desenvolvimento, eliminando a necessidade de executar múltiplos comandos manualmente.

### Instalação

```bash
cargo install wasm-pack
```

Alternativamente, você pode instalar via package manager:

```bash
# macOS (Homebrew)
brew install wasm-pack

# Arch Linux
pacman -S wasm-pack

# Nix
nix-env -iA nixpkgs.wasm-pack
```

### Estrutura de um projeto wasm-pack

O wasm-pack espera uma estrutura de projeto específica. Um projeto típico tem a seguinte organização:

```
my-wasm-project/
├── Cargo.toml
├── src/
│   └── lib.rs
├── www/              # (opcional) Frontend
│   ├── index.html
│   ├── index.js
│   └── package.json
└── pkg/              # Gerado pelo wasm-pack
    ├── package.json
    ├── my_wasm_project.d.ts
    ├── my_wasm_project_bg.wasm
    ├── my_wasm_project_bg.wasm.d.ts
    └── my_wasm_project.js
```

O Cargo.toml deve incluir as dependências necessárias:

```toml
[package]
name = "my-wasm-project"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
wasm-bindgen = "0.2"

[dependencies.web-sys]
version = "0.3"
features = [
    "console",
    "Document",
    "Element",
    "HtmlElement",
    "Window",
]

[profile.release]
opt-level = "z"
lto = true
```

O campo crate-type = ["cdylib", "rlib"] é essencial para WebAssembly. O "cdylib" gera uma library dinâmica que pode ser carregada pelo runtime WebAssembly, enquanto "rlib" permite que o código seja usado como dependência em outros projetos Rust.

### Comandos principais do wasm-pack

**build**: Compila o projeto para WebAssembly

```bash
wasm-pack build
```

Esse comando executa as seguintes etapas automaticamente:
1. Compila o código Rust para o target wasm32-unknown-unknown
2. Executa o wasm-bindgen para gerar os bindings JavaScript
3. Cria o diretório pkg/ com todos os arquivos necessários
4. Gera o package.json para publicação no npm

**build com opções**:

```bash
# Compilar para naveguador (padrão)
wasm-pack build --target web

# Compilar para Node.js
wasm-pack build --target nodejs

# Compilar para bundler (webpack, vite, etc.)
wasm-pack build --target bundler

# Compilar em modo debug
wasm-pack build --dev

# Compilar com otimizações específicas
wasm-pack build --release
```

**test**: Executa testes do código Rust

```bash
wasm-pack test --headless --chrome
wasm-pack test --headless --firefox
wasm-pack test --headless --safari
```

**publish**: Publica o pacote no npm

```bash
wasm-pack publish
```

### Targets de compilação

O wasm-pack suporta diferentes targets que determinam como o código será consumido:

**Target web** (recomendado para aplicações standalone):

```bash
wasm-pack build --target web
```

Gera um módulo ES que pode ser importado diretamente no navegador:

```javascript
import init, { greet } from './pkg/my_project.js';

async function main() {
    await init();
    greet('World');
}
main();
```

**Target nodejs** (para uso em Node.js):

```bash
wasm-pack build --target nodejs
```

Gera um módulo CommonJS que pode ser requerido no Node.js:

```javascript
const { greet } = require('./pkg/my_project.js');
greet('World');
```

**Target bundler** (para uso com webpack, vite, rollup):

```bash
wasm-pack build --target bundler
```

Gera um módulo que funciona com bundlers modernos, permitindo code splitting e lazy loading automático.

### Variáveis de ambiente

O wasm-pack suporta variáveis de ambiente para controle fino da compilação:

```bash
# Definir nível de otimização
WASM_BUILD_OPT_LEVEL=z wasm-pack build

# Habilitar features específicas
WASM_PACK_FEATURES="feature1,feature2" wasm-pack build

# Definir diretório de saída
WASM_PACK_OUT_DIR=dist wasm-pack build

# Habilitar source maps para debug
WASM_PACK_DEV=1 wasm-pack build
```

### Estrutura do diretório pkg/

Após a compilação, o diretório pkg/ contém:

```
pkg/
├── package.json              # Metadados do pacote npm
├── my_project.js             # Wrapper JavaScript (target web)
├── my_project.d.ts           # Definições TypeScript
├── my_project_bg.wasm        # Binário WebAssembly
├── my_project_bg.wasm.d.ts   # Tipos para o módulo Wasm
├── my_project_bg.js          # JS glue code para o Wasm
└── README.md                 # Documentação gerada
```

O arquivo .wasm contém o bytecode WebAssembly compilado. O arquivo .js é o glue code que gerencia o carregamento e a inicialização do módulo Wasm. Os arquivos .d.ts fornecem tipos TypeScript para melhor experiência de desenvolvimento.

### Integração com npm

O wasm-pack gera automaticamente um package.json válido que pode ser publicado diretamente no npm:

```json
{
  "name": "my-wasm-project",
  "version": "0.1.0",
  "description": "My project compiled to WebAssembly",
  "main": "my_project.js",
  "types": "my_project.d.ts",
  "files": [
    "my_project.js",
    "my_project.d.ts",
    "my_project_bg.wasm",
    "my_project_bg.wasm.d.ts",
    "my_project_bg.js"
  ],
  "repository": {
    "type": "git",
    "url": "https://github.com/user/my-wasm-project"
  },
  "keywords": ["wasm", "webassembly", "rust"],
  "license": "MIT"
}
```

### Tratamento de erros

O wasm-pack fornece mensagens de erro detalhadas para ajudar no diagnóstico de problemas:

```bash
# Erro: target não encontrado
error: the `wasm32-unknown-unknown` target may not be installed
# Solução: rustup target add wasm32-unknown-unknown

# Erro: crate-type inadequado
error: cdylib crate type is required for wasm-pack
# Solução: adicionar crate-type = ["cdylib"] no Cargo.toml

# Erro: wasm-bindgen ausente
error: wasm-bindgen not found
# Solução: adicionar wasm-bindgen como dependência
```

### Otimizações de compilação

Para projetos em produção, várias otimizações podem ser aplicadas:

```toml
[profile.release]
opt-level = "z"          # Otimizar para tamanho mínimo
lto = true               # Link-Time Optimization
codegen-units = 1        # Máxima otimização
panic = "abort"          # Sem unwinding
strip = true             # Remover símbolos
debug = false            # Sem info de debug
```

Essas configurações podem reduzir o tamanho do binário Wasm em 50-70% comparado com configurações padrão.

---

## 4.3 wasm-bindgen FFI

### Introdução ao wasm-bindgen

O wasm-bindgen é a camada fundamental que permite a interoperação entre Rust e JavaScript no contexto WebAssembly. Ele fornece uma abstração de alto nível que elimina a necessidade de escrever código de FFI (Foreign Function Interface) manual, gerando automaticamente os bindings entre as duas linguagens.

O wasm-bindgen opera em duas fases:

1. **Fase de compilação**: O compilador Rust gera anotações especiais no bytecode WebAssembly
2. **Fase de geração**: O tool wasm-bindgen processa o bytecode e gera o código JavaScript necessário para a interoperação

### Anotações básicas

A macro #[wasm_bindgen] é o ponto de entrada principal para definir funções e estruturas que serão expostas ao JavaScript:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

#[wasm_bindgen]
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

Essas funções podem ser chamadas diretamente do JavaScript:

```javascript
import init, { greet, add } from './pkg/my_project.js';

await init();
console.log(greet("World"));  // "Hello, World!"
console.log(add(2, 3));       // 5
```

### Tipos de dados

O wasm-bindgen fornece automação de conversão entre tipos Rust e JavaScript:

**Tipos primitivos**:

| Rust | JavaScript | Observações |
|------|-----------|-------------|
| i8, i16, i32 | Number | Inteiros com sinal |
| u8, u16, u32 | Number | Inteiros sem sinal |
| i64, u64 | BigInt | Inteiros de 64 bits |
| f32, f64 | Number | Ponto flutuante |
| bool | Boolean | |
| &str | String | Referência emprestada |
| String | String | Propriedade transferida |
| () | undefined | |

**Strings**:

```rust
use wasm_bindgen::prelude::*;

// Receber string do JavaScript
#[wasm_bindgen]
pub fn process_string(input: &str) -> usize {
    input.len()
}

// Retornar string para JavaScript
#[wasm_bindgen]
pub fn get_greeting() -> String {
    String::from("Hello from Rust!")
}
```

**Arrays**:

```rust
use wasm_bindgen::prelude::*;

// Receber array do JavaScript
#[wasm_bindgen]
pub fn sum_array(data: &[f64]) -> f64 {
    data.iter().sum()
}

// Retornar array para JavaScript
#[wasm_bindgen]
pub fn create_array() -> Vec<f64> {
    vec![1.0, 2.0, 3.0, 4.0, 5.0]
}
```

### Estruturas e métodos

O wasm-bindgen permite expor structs Rust completas com seus métodos:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct Calculator {
    value: f64,
    history: Vec<f64>,
}

#[wasm_bindgen]
impl Calculator {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Calculator {
        Calculator {
            value: 0.0,
            history: Vec::new(),
        }
    }

    #[wasm_bindgen(js_name = add)]
    pub fn add_value(&mut self, value: f64) -> f64 {
        self.value += value;
        self.history.push(self.value);
        self.value
    }

    #[wasm_bindgen(js_name = subtract)]
    pub fn subtract_value(&mut self, value: f64) -> f64 {
        self.value -= value;
        self.history.push(self.value);
        self.value
    }

    #[wasm_bindgen(js_name = getValue)]
    pub fn get_value(&self) -> f64 {
        self.value
    }

    #[wasm_bindgen(js_name = getHistory)]
    pub fn get_history(&self) -> Vec<f64> {
        self.history.clone()
    }

    #[wasm_bindgen(js_name = reset)]
    pub fn reset(&mut self) {
        self.value = 0.0;
        self.history.clear();
    }
}
```

Uso no JavaScript:

```javascript
import init, { Calculator } from './pkg/my_project.js';

await init();
const calc = new Calculator();
console.log(calc.add(10));      // 10
console.log(calc.add(5));       // 15
console.log(calc.subtract(3));  // 12
console.log(calc.getHistory()); // [10, 15, 12]
```

### Callbacks e closures

O wasm-bindgen fornece JsValue para representar qualquer valor JavaScript, permitindo callbacks e closures:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn set_timeout(callback: &js_sys::Function, delay: i32) {
    let window = web_sys::window().unwrap();
    window
        .set_timeout_with_callback_and_timeout_and_arguments_0(callback, delay)
        .unwrap();
}

#[wasm_bindgen]
pub fn create_counter() -> js_sys::Function {
    let mut count = 0;
    let closure = Closure::wrap(Box::new(move || {
        count += 1;
        web_sys::console::log_1(&format!("Count: {}", count).into());
    }) as Box<dyn FnMut()>);

    let func = closure.as_ref().clone();
    closure.forget(); // Prevent drop - careful with memory!
    func
}
```

### Acesso ao DOM e APIs do navegador

O wasm-bindgen trabalha em conjunto com o crate web-sys para fornecer acesso tipado a todas as APIs do navegador:

```rust
use wasm_bindgen::prelude::*;
use web_sys::{Document, Element, HtmlElement, Window};

#[wasm_bindgen(start)]
pub fn main() -> Result<(), JsValue> {
    let window: Window = web_sys::window().expect("no global window");
    let document: Document = window.document().expect("no document");

    let body: HtmlElement = document.body().expect("no body");
    let div: Element = document.create_element("div")?;
    div.set_text_content(Some("Hello from Rust!"));
    body.append_child(&div)?;

    Ok(())
}
```

### Exceções e tratamento de erros

O wasm-bindgen permite propagar erros entre Rust e JavaScript:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn parse_number(input: &str) -> Result<f64, JsValue> {
    input
        .parse::<f64>()
        .map_err(|e| JsValue::from_str(&format!("Parse error: {}", e)))
}

#[wasm_bindgen]
pub fn divide(a: f64, b: f64) -> Result<f64, JsValue> {
    if b == 0.0 {
        Err(JsValue::from_str("Division by zero"))
    } else {
        Ok(a / b)
    }
}
```

No JavaScript, erros são tratados com try/catch:

```javascript
try {
    const result = parse_number("not a number");
} catch (e) {
    console.error(e.message);  // "Parse error: invalid float literal"
}
```

### Gerenciamento de memória

O wasm-bindgen gerencia automaticamente a alocação e desalocação de memória entre Rust e JavaScript. No entanto, é importante entender como funciona internamente para evitar vazamentos de memória:

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct LargeBuffer {
    data: Vec<u8>,
}

#[wasm_bindgen]
impl LargeBuffer {
    #[wasm_bindgen(constructor)]
    pub fn new(size: usize) -> LargeBuffer {
        LargeBuffer {
            data: vec![0; size],
        }
    }

    // Método que retorna referência - sem cópia
    #[wasm_bindgen(js_name = getData)]
    pub fn get_data(&self) -> &[u8] {
        &self.data
    }

    // Método que retorna owned value - cópia
    #[wasm_bindgen(js_name = cloneData)]
    pub fn clone_data(&self) -> Vec<u8> {
        self.data.clone()
    }
}
```

### Módulos e organização

Para projetos maiores, o wasm-bindgen suporta organização em módulos:

```rust
// src/lib.rs
pub mod math;
pub mod utils;
pub mod wasm_api;

// src/math.rs
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn fibonacci(n: u32) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => {
            let mut a: u64 = 0;
            let mut b: u64 = 1;
            for _ in 2..=n {
                let temp = b;
                b = a + b;
                a = temp;
            }
            b
        }
    }
}

// src/wasm_api.rs
use wasm_bindgen::prelude::*;
use crate::math;

#[wasm_bindgen]
pub fn calculate_fibonacci(n: u32) -> u64 {
    math::fibonacci(n)
}
```

### Features e conditional compilation

O wasm-bindgen pode ser configurado com features para incluir apenas o necessário:

```toml
[dependencies]
wasm-bindgen = { version = "0.2", features = ["serde-serialize"] }
js-sys = "0.3"
web-sys = { version = "0.3", features = [
    "console",
    "Document",
    "Element",
    "HtmlElement",
    "Window",
    "MouseEvent",
    "KeyboardEvent",
] }
```

---

## 4.4 trunk framework

### Introdução ao Trunk

O Trunk é um build tool e dev server para aplicações WebAssembly em Rust. Ele foi projetado para simplificar o desenvolvimento de aplicações web frontend compiladas para Wasm, automatizando a compilação, bundling e servimento de arquivos.

O Trunk se destaca por sua simplicidade e velocidade. Ele monitora mudanças nos arquivos e reconstrói automaticamente a aplicação, proporcionando uma experiência de desenvolvimento com hot reload. Diferentemente de outros bundlers, o Trunk é nativamente compatível com WebAssembly e não requer configurações complexas.

### Instalação

```bash
cargo install trunk
```

Para instalar a versão mais recente (recomendado para novos projetos):

```bash
cargo install trunk --git https://github.com/trunk-rs/trunk
```

### Estrutura de projeto

Um projeto típico com Trunk tem a seguinte estrutura:

```
my-app/
├── Cargo.toml
├── Trunk.toml
├── index.html
├── src/
│   └── main.rs
├── assets/
│   ├── css/
│   │   └── style.css
│   ├── images/
│   │   └── logo.png
│   └── js/
│       └── helper.js
└── dist/              # Gerado pelo Trunk
    ├── index.html
    ├── my_app-*.wasm
    └── my_app.js
```

### Arquivo index.html

O Trunk usa um arquivo index.html como template, com diretrizes especiais para incluir o código Wasm:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minha Aplicação</title>
    <link data-trunk rel="css" href="assets/css/style.css">
</head>
<body>
    <div id="app"></div>

    <link data-trunk rel="rust" data-wasm-opt="z">
</body>
</html>
```

A diretiva `<link data-trunk rel="rust">` informa ao Trunk que este é um projeto Rust que deve ser compilado para WebAssembly. O atributo data-wasm-opt aplica otimizações de tamanho ao binário Wasm gerado.

### Trunk.toml

O arquivo Trunk.toml permite configurar o comportamento do Trunk:

```toml
[build]
target = "index.html"
dist = "dist"
public = "public"

[watch]
watch = ["src", "index.html", "assets"]
ignore = ["dist", "target"]

[serve]
address = "127.0.0.1"
port = 8080
open = false

[tools]
wasm_bindgen = "0.2.87"
wasm_opt = "version_116"

[[hooks]]
stage = "build"
command = "sh"
args = ["-c", "sass assets/scss/main.scss assets/css/style.css"]
```

### Comandos do Trunk

**trunk serve**: Inicia o dev server com hot reload

```bash
trunk serve
```

O servidor observa mudanças nos arquivos e reconstrói automaticamente. A reconstrução é incremental, aproveitando o cache do compilador Rust para reconstruções rápidas.

**trunk build**: Compila a aplicação para produção

```bash
trunk build --release
```

**trunk build com opções**:

```bash
# Compilar em modo release com otimizações máximas
trunk build --release

# Compilar sem minificação
trunk build --release --no-minification

# Compilar com source maps
trunk build --release --dev
```

### Assets e processamento

O Trunk suporta processamento automático de diferentes tipos de assets:

**CSS**:

```html
<link data-trunk rel="css" href="assets/css/main.css">
```

**SCSS/SASS**:

```html
<link data-trunk rel="scss" href="assets/scss/main.scss">
```

**Imagens**:

```html
<link data-trunk rel="copy-file" href="assets/images/logo.png">
```

**JavaScript**:

```html
<script data-trunk type="module" src="assets/js/helper.js"></script>
```

**Favicon**:

```html
<link data-trunk rel="icon" type="image/png" href="assets/images/favicon.png">
```

### Integração com outros crates

O Trunk funciona perfeitamente com crates populares do ecossistema Rust/Wasm:

**web-sys + wasm-bindgen**:

```rust
use wasm_bindgen::prelude::*;
use web_sys::{Document, Element, HtmlElement, Window};

#[wasm_bindgen(start)]
pub fn main() -> Result<(), JsValue> {
    let window = web_sys::window().expect("no global window");
    let document = window.document().expect("no document");
    let body = document.body().expect("no body");

    let div = document.create_element("div")?;
    div.set_text_content(Some("Hello from Trunk!"));
    div.set_class_name("container");
    body.append_child(&div)?;

    Ok(())
}
```

**gloo (abstrações de alto nível)**:

```rust
use gloo::events::EventClosure;
use gloo::timers::callback::Interval;
use web_sys::{Document, Element};

fn setup_timer() {
    let interval = Interval::new(1000, || {
        web_sys::console::log_1(&"Tick".into());
    });

    // O interval continua ativo enquanto a referência existir
    interval.forget();
}
```

### Hot reload e performance

O Trunk implementa hot reload eficiente:

1. Monitora arquivos-fonte para mudanças
2. Detecta se a mudança afeta Rust ou apenas assets
3. Para mudanças em Rust: reconstrução incremental
4. Para mudanças em assets: atualização sem reconstrução
5. Injeta o novo código no navegador via WebSocket

A velocidade de rebuild depende do tamanho do projeto e das otimizações aplicadas. Projetos pequenos podem rebuildar em menos de 1 segundo em modo debug.

### Deploy e hospedagem

O Trunk gera arquivos estáticos que podem ser hospedados em qualquer servidor web:

```bash
# Gerar arquivos para produção
trunk build --release

# Resultado em dist/
# - index.html
# - my_app-*.wasm
# - my_app.js
# - assets/...
```

Esses arquivos podem ser hospedados em GitHub Pages, Netlify, Vercel, ou qualquer CDN estática.

### Depuração

O Trunk fornece opções de depuração:

```bash
# Modo verbose para ver detalhes da compilação
trunk serve --verbose

# Limpar cache e rebuildar
trunk clean && trunk serve

# Verificar erros sem iniciar servidor
trunk build 2>&1 | head -50
```

---

## 4.5 Frameworks web: leptos e yew

### Yew

O Yew é um framework de UI para Rust que compila para WebAssembly. Inspirado em React, ele permite criar interfaces de componentes usando uma abordagem declarativa com Virtual DOM.

**Instalação**:

```bash
cargo install trunk
cargo new my-yew-app --lib
cd my-yew-app
```

**Cargo.toml**:

```toml
[package]
name = "my-yew-app"
version = "0.1.0"
edition = "2021"

[dependencies]
yew = { version = "0.21", features = ["csr"] }
wasm-bindgen = "0.2"
web-sys = { version = "0.3", features = ["Document", "Element"] }
```

**Componente básico**:

```rust
use yew::prelude::*;

#[function_component(App)]
fn app() -> Html {
    let counter = use_state(|| 0);

    let onclick = {
        let counter = counter.clone();
        Callback::from(move |_| counter.set(*counter + 1))
    };

    html! {
        <div>
            <h1>{ "Contador: " }{ *counter }</h1>
            <button {onclick }>{ "+1" }</button>
        </div>
    }
}

fn main() {
    yew::Renderer::<App>::new().render();
}
```

**Componentes com Props**:

```rust
use yew::prelude::*;

#[derive(Properties, PartialEq)]
struct CardProps {
    title: String,
    content: String,
    #[prop_or_default]
    highlighted: bool,
}

#[function_component(Card)]
fn card(props: &CardProps) -> Html {
    let class = if props.highlighted {
        "card highlighted"
    } else {
        "card"
    };

    html! {
        <div class={class}>
            <h3>{ &props.title }</h3>
            <p>{ &props.content }</p>
        </div>
    }
}
```

**Hooks e estado**:

```rust
use yew::prelude::*;
use yew::hook;

#[hook]
fn use_fetch(url: &str) -> UseStateHandle<Option<String>> {
    let data = use_state(|| None::<String>);

    {
        let data = data.clone();
        let url = url.to_string();

        use_effect_with(url.clone(), move |_| {
            let data = data.clone();
            let url = url.clone();

            wasm_bindgen_futures::spawn_local(async move {
                let resp = reqwest::get(&url).await.unwrap();
                let text = resp.text().await.unwrap();
                data.set(Some(text));
            });

            || ()
        });
    }

    data
}

#[function_component(App)]
fn app() -> Html {
    let data = use_fetch("https://api.example.com/data");

    html! {
        <div>
            {
                match (*data).clone() {
                    Some(text) => html! { <pre>{ text }</pre> },
                    None => html! { <p>{ "Carregando..." }</p> },
                }
            }
        </div>
    }
}
```

### Leptos

O Leptos é um framework mais recente que se destaca pela performance e pela capacidade de renderização tanto no servidor (SSR) quanto no cliente (CSR). Ele usa reatividade granular em vez de Virtual DOM.

**Instalação**:

```bash
cargo new my-leptos-app --lib
cd my-leptos-app
```

**Cargo.toml**:

```toml
[package]
name = "my-leptos-app"
version = "0.1.0"
edition = "2021"

[dependencies]
leptos = { version = "0.6", features = ["csr"] }
leptos_dom = "0.6"
leptos_macro = "0.6"
```

**Componente básico**:

```rust
use leptos::*;

#[component]
fn App() -> impl IntoView {
    let (count, set_count) = create_signal(0);

    view! {
        <div>
            <h1>{ "Contador: " }{ move || *count.get() }</h1>
            <button on:click=move |_| set_count.update(|n| *n += 1)>
                { "+1" }
            </button>
        </div>
    }
}

fn main() {
    mount_to_body(|| view! { <App/> });
}
```

**Reatividade avançada**:

```rust
use leptos::*;

#[component]
fn App() -> impl IntoView {
    let (name, set_name) = create_signal(String::new());
    let (email, set_email) = create_signal(String::new());

    let is_valid = create_memo(move |_| {
        name.get().len() > 0 && email.get().contains('@')
    });

    let submit_disabled = move || !is_valid.get();

    view! {
        <form>
            <input
                type="text"
                placeholder="Nome"
                on:input=move |ev| set_name(event_target_value(&ev))
            />
            <input
                type="email"
                placeholder="Email"
                on:input=move |ev| set_email(event_target_value(&ev))
            />
            <button
                type="submit"
                disabled=submit_disabled
            >
                { "Enviar" }
            </button>
        </form>
    }
}
```

**Componentes e Props**:

```rust
use leptos::*;

#[component]
fn Card(
    title: ReadSignal<String>,
    content: ReadSignal<String>,
    #[prop(optional)] highlighted: bool,
) -> impl IntoView {
    let class = if highlighted {
        "card highlighted"
    } else {
        "card"
    };

    view! {
        <div class=class>
            <h3>{ title }</h3>
            <p>{ content }</p>
        </div>
    }
}
```

**Rotas e navegação**:

```rust
use leptos::*;
use leptos_router::*;

#[derive(Clone, PartialEq)]
struct Todo {
    id: usize,
    title: String,
    completed: bool,
}

#[component]
fn App() -> impl IntoView {
    view! {
        <Router>
            <nav>
                <A href="/">"Home"</A>
                <A href="/todos">"Todos"</A>
            </nav>
            <Routes>
                <Route path="/" view=Home/>
                <Route path="/todos" view=TodoList/>
            </Routes>
        </Router>
    }
}

#[component]
fn Home() -> impl IntoView {
    view! {
        <h1>{ "Home" }</h1>
    }
}

#[component]
fn TodoList() -> impl IntoView {
    let (todos, set_todos) = create_signal(vec![
        Todo { id: 1, title: "Aprender Leptos".into(), completed: false },
    ]);

    view! {
        <ul>
            { move || todos.get().into_iter().map(|todo| {
                view! {
                    <li class:completed=todo.completed>
                        { todo.title }
                    </li>
                }
            }).collect_view() }
        </ul>
    }
}
```

### Comparação Yew vs Leptos

| Característica | Yew | Leptos |
|---------------|-----|--------|
| Modelo de reatividade | Virtual DOM | Sinais granulares |
| Performance | Boa | Excelente |
| SSR | Experimental | Suporte completo |
| Tamanho do bundle | Maior | Menor |
| Curva de aprendizado | Mais fácil | Moderada |
| Maturidade | Maduro | Crescente |
| Ecossistema | Grande | Crescendo |

### SSR e SSG

Ambos os frameworks suportam renderização no servidor:

**Leptos SSR**:

```rust
#[component]
fn App() -> impl IntoView {
    let (count, set_count) = create_signal(0);

    view! {
        <div>
            <h1>{ "Server Rendered" }</h1>
            <p>{ move || format!("Count: {}", count.get()) }</p>
            <button on:click=move |_| set_count.update(|n| *n += 1)}>
                { "Increment" }
            </button>
        </div>
    }
}

#[cfg(feature = "ssr")]
#[tokio::main]
async fn main() {
    use axum::Router;
    use leptos::*;

    let conf = get_configuration(None).await.unwrap();
    let addr = conf.leptos_options.site_addr;
    let routes = generate_route_list(App);

    let app = Router::new()
        .leptos_routes(&conf, routes, App)
        .fallback(leptos_handler);

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app.into_make_service()).await.unwrap();
}
```

### Routing e navegação

```rust
use leptos_router::*;

#[derive(Routable, Clone, PartialEq)]
enum Routes {
    #[route("/")]
    Home,
    #[route("/about")]
    About,
    #[route("/users/:id")]
    User { id: usize },
    #[route("/posts/*posts")]
    Posts { posts: Vec<String> },
}

#[component]
fn App() -> impl IntoView {
    view! {
        <Router>
            <nav>
                <A href="/">"Home"</A>
                <A href="/about">"About"</A>
                <A href="/users/42">"User 42"</A>
            </nav>
            <Routes>
                <Route path="/" view=Home/>
                <Route path="/about" view=About/>
                <Route path="/users/:id" view=User/>
                <Route path="/posts/*posts" view=Posts/>
            </Routes>
        </Router>
    }
}

#[component]
fn User() -> impl IntoView {
    let params = use_params_map();
    let id = move || params.with(|p| p.get("id").cloned().unwrap_or_default());

    view! {
        <h1>{ "User " }{ id }</h1>
    }
}
```

### Integração com APIs

```rust
use leptos::*;

#[component]
fn App() -> impl IntoView {
    let (data, set_data) = create_signal(None::<String>);
    let (loading, set_loading) = create_signal(false);

    let fetch_data = move |_| {
        set_loading.set(true);
        set_data.set(None);

        wasm_bindgen_futures::spawn_local(async move {
            let resp = reqwest::get("https://api.example.com/data")
                .await
                .unwrap();
            let text = resp.text().await.unwrap();
            set_data.set(Some(text));
            set_loading.set(false);
        });
    };

    view! {
        <div>
            <button on:click=fetch_data disabled=loading>
                { "Fetch Data" }
            </button>
            { move || if loading.get() {
                view! { <p>"Loading..."</p> }.into_view()
            } else if let Some(d) = data.get() {
                view! { <pre>{ d }</pre> }.into_view()
            } else {
                view! { <p>"No data"</p> }.into_view()
            }}
        </div>
    }
}
```

### Estilização

**Inline styles**:

```rust
view! {
    <div style="color: red; font-size: 20px;">
        { "Styled text" }
    </div>
}
```

**Classes CSS**:

```rust
view! {
    <div class="container main">
        <span class:active=signal class:disabled=disabled_signal>
            { "Toggleable class" }
        </span>
    </div>
}
```

**CSS Modules com Trunk**:

```html
<!-- index.html -->
<link data-trunk rel="scss" href="assets/scss/main.scss">
```

### Performance tips

```rust
// 1. Use create_memo para valores derivados
let double = create_memo(move |_| count.get() * 2);

// 2. Evite re-renderizações desnecessárias
let expensive = create_memo(move |_| {
    // Só recalcula quando count muda
    heavy_computation(count.get())
});

// 3. Use Suspense para carregamento assíncrono
view! {
    <Suspense fallback=|| view! { <p>"Loading..."</p> }>
        { move || data.get() }
    </Suspense>
}

// 4. Use Transition para atualizações suaves
let (data, set_data) = create_signal(None);
let (is_pending, set_is_pending) = create_signal(false);

view! {
    <Transition fallback=|| view! { <p>"Updating..."</p> }>
        { move || data.get() }
    </Transition>
}
```

---

## 4.6 wasm-pack test

### Introdução ao wasm-pack test

O wasm-pack test é a ferramenta oficial para executar testes de código Rust que compila para WebAssembly. Ele permite testar funcionalidade que depende de APIs do navegador (DOM, fetch, Web Workers) em ambientes reais de execução.

Diferentemente dos testes unitários tradicionais do Rust, que rodam no ambiente nativo, os testes wasm-pack test executam o código no navegador real ou em um headless browser, garantindo que o comportamento testado seja idêntico ao que ocorrer em produção.

### Configuração

Adicione as dependências de teste no Cargo.toml:

```toml
[dev-dependencies]
wasm-bindgen-test = "0.3"
wasm-bindgen = "0.2"
web-sys = { version = "0.3", features = ["console", "Document"] }
```

### Testes básicos

```rust
use wasm_bindgen_test::*;
use web_sys::console;

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_addition() {
    let result = 2 + 2;
    assert_eq!(result, 4);
}

#[wasm_bindgen_test]
fn test_string_conversion() {
    let s = String::from("Hello, WebAssembly!");
    assert_eq!(s.len(), 19);
}
```

### Testes de DOM

```rust
use wasm_bindgen_test::*;
use web_sys::{Document, Element, HtmlElement, Window};

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_dom_manipulation() {
    let window: Window = web_sys::window().expect("no global window");
    let document: Document = window.document().expect("no document");

    let div: Element = document.create_element("div").expect("failed to create element");
    div.set_text_content(Some("Test content"));
    div.set_id("test-element");

    let body: HtmlElement = document.body().expect("no body");
    body.append_child(&div).expect("failed to append child");

    let element = document.get_element_by_id("test-element");
    assert!(element.is_some());

    let text = element.unwrap().text_content().unwrap();
    assert_eq!(text, "Test content");
}
```

### Testes assíncronos

```rust
use wasm_bindgen_test::*;
use wasm_bindgen::JsValue;
use gloo::timers::callback::Timeout;

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
async fn test_async_operation() {
    let result = async_operation().await;
    assert_eq!(result, 42);
}

async fn async_operation() -> i32 {
    // Simular operação assíncrona
    gloo::timers::future::TimeoutFuture::new(100).await;
    42
}

#[wasm_bindgen_test]
fn test_timeout() {
    let (tx, rx) = futures::channel::oneshot::channel::<()>();

    Timeout::new(100, move || {
        tx.send(()).unwrap();
    }).forget();

    wasm_bindgen_futures::spawn_local(async move {
        rx.await.unwrap();
        // Teste concluído
    });
}
```

### Executando testes

**No navegador (headless)**:

```bash
# Chrome headless
wasm-pack test --headless --chrome

# Firefox headless
wasm-pack test --headless --firefox

# Safari headless (macOS)
wasm-pack test --headless --safari
```

**Com opções adicionais**:

```bash
# Modo verbose
wasm-pack test --headless --chrome --verbose

# Definir URL base
wasm-pack test --headless --chrome -- --url http://localhost:8080

# Filtrar testes
wasm-pack test --headless --chrome -- --test test_addition
```

### Testes com múltiplos navegadores

```bash
# Testar em todos os navegadores disponíveis
for browser in chrome firefox; do
    echo "Testing in $browser..."
    wasm-pack test --headless --$browser
done
```

### Integração com CI/CD

**GitHub Actions**:

```yaml
name: WASM Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: wasm32-unknown-unknown

      - name: Install wasm-pack
        run: cargo install wasm-pack

      - name: Install Chrome
        uses: browser-actions/setup-chrome@v1

      - name: Run tests
        run: wasm-pack test --headless --chrome
```

### Testes de performance

```rust
use wasm_bindgen_test::*;
use web_sys::Performance;

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_performance() {
    let window = web_sys::window().unwrap();
    let performance = window.performance().unwrap();

    let start = performance.now();

    // Código a ser medido
    for _ in 0..1000000 {
        let _ = 2 + 2;
    }

    let end = performance.now();
    let duration = end - start;

    web_sys::console::log_1(&format!("Duration: {}ms", duration).into());

    // Verificar se o código roda dentro do tempo aceitável
    assert!(duration < 1000.0, "Performance regression detected");
}
```

### Testes de integração

```rust
use wasm_bindgen_test::*;
use wasm_bindgen::JsValue;

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
async fn test_api_integration() {
    let window = web_sys::window().unwrap();
    let resp_value = js_sys::Promise::resolve(&JsValue::NULL);

    // Usando fetch real
    let resp = gloo_net::http::Request::get("https://httpbin.org/get")
        .send()
        .await
        .unwrap();

    assert_eq!(resp.status(), 200);

    let text = resp.text().await.unwrap();
    assert!(text.contains("headers"));
}
```

### Organização de testes

Estrutura recomendada para testes:

```
src/
├── lib.rs
├── utils.rs
└── tests/
    ├── mod.rs
    ├── unit_tests.rs
    └── integration_tests.rs
```

```rust
// src/lib.rs
#[cfg(test)]
mod tests;

// src/tests/mod.rs
mod unit_tests;
mod integration_tests;

// src/tests/unit_tests.rs
use wasm_bindgen_test::*;
wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_basic_math() {
    assert_eq!(2 + 2, 4);
}
```

### Debugging de testes

```bash
# Executar com console output visível
wasm-pack test --headless --chrome -- --nocapture

# Usar Chrome DevTools
wasm-pack test --chrome  # Abre navegador para debug manual
```

---

## 4.7 wasm-opt optimization

### Introdução ao wasm-opt

O wasm-opt é uma ferramenta de otimização para binários WebAssembly. Ele faz parte do projeto Binaryen e realiza transformações no bytecode Wasm para reduzir tamanho, melhorar performance ou ambas. O wasm-opt opera no nível de instruções Wasm, aplicando otimizações que não são possíveis em estágios anteriores do pipeline de compilação.

O wasm-opt é especialmente importante para WebAssembly porque o tamanho do binário impacta diretamente o tempo de carregamento em ambientes web. Um binário menor significa downloads mais rápidos, menos uso de memória e melhor experiência do usuário.

### Instalação

```bash
# Via cargo
cargo install binaryen

# Via package manager
# macOS
brew install binaryen

# Ubuntu/Debian
apt install binaryen

# Arch Linux
pacman -S binaryen
```

### Níveis de otimização

O wasm-opt suporta diferentes níveis de otimização:

**Otimização para tamanho (-Os)**:

```bash
wasm-opt -Os input.wasm -o output.wasm
```

**Otimização para tamanho agressivo (-Oz)**:

```bash
wasm-opt -Oz input.wasm -o output.wasm
```

**Otimização para velocidade (-O)**:

```bash
wasm-opt -O input.wasm -o output.wasm
```

**Otimização máxima (-O3)**:

```bash
wasm-opt -O3 input.wasm -o output.wasm
```

### Passes de otimização

O wasm-opt pode executar passes específicos:

**Remoção de código morto**:

```bash
wasm-opt --remove-unused-functions input.wasm -o output.wasm
```

**Eliminação de código redundante**:

```bash
wasm-opt --dce input.wasm -o output.wasm
```

**Simplificação de fluxo de controle**:

```bash
wasm-opt --optimize-control-flow input.wasm -o output.wasm
```

**Fusão de variáveis**:

```bash
wasm-opt --merge-locals input.wasm -o output.wasm
```

### Combinando passes

```bash
wasm-opt -Oz \
    --remove-unused-functions \
    --dce \
    --optimize-control-flow \
    --merge-locals \
    --strip-debug \
    --strip-producers \
    input.wasm -o output.wasm
```

### Integração com Cargo

Para integrar o wasm-opt no build do Cargo, use o crate wasm-opt:

```toml
[dependencies]
wasm-opt = "0.112"
```

```rust
use wasm_opt::OptimizationOptions;

fn optimize_wasm(input_path: &str, output_path: &str) {
    OptimizationOptions::new_optimize_for_size()
        .run(input_path, output_path)
        .expect("wasm-opt optimization failed");
}
```

### Scripts de otimização

Crie um script de build personalizado:

```bash
#!/bin/bash
# optimize.sh

INPUT="target/wasm32-unknown-unknown/release/my_project.wasm"
OUTPUT="dist/my_project_optimized.wasm"

# Compilar
cargo build --release --target wasm32-unknown-unknown

# Otimizar
wasm-opt -Oz \
    --strip-debug \
    --strip-producers \
    --output-each-file \
    $INPUT -o $OUTPUT

# Mostrar redução de tamanho
ORIGINAL=$(wc -c < $INPUT)
OPTIMIZED=$(wc -c < $OUTPUT)
REDUCTION=$(( (ORIGINAL - OPTIMIZED) * 100 / ORIGINAL ))

echo "Original: $ORIGINAL bytes"
echo "Optimized: $OPTIMIZED bytes"
echo "Reduction: $REDUCTION%"
```

### Análise de binários

```bash
# Mostrar estatísticas
wasm-opt --stats input.wasm

# Listar funções
wasm-opt --list-functions input.wasm

# Verificar validade
wasm-opt --validate input.wasm

# Printar tamanho de cada seção
wasm-opt --output-binary-size input.wasm
```

### Otimizações específicas por caso de uso

**Para aplicações web**:

```bash
wasm-opt -Oz \
    --strip-debug \
    --strip-producers \
    --lowering-intrinsics \
    --vacuum \
    --merge-locals \
    --dce \
    --simplify-globals-optimizing \
    input.wasm -o output.wasm
```

**Para aplicação em produção**:

```bash
wasm-opt -O3 \
    --enable-simd \
    --enable-bulk-memory \
    --enable-reference-types \
    --strip-debug \
    --strip-producers \
    --strip-target-features \
    input.wasm -o output.wasm
```

### Resultados típicos

| Otimização | Redução típica | Trade-off |
|-----------|----------------|-----------|
| -Os | 20-30% | Leve perda de performance |
| -Oz | 30-50% | Maior perda de performance |
| -O | 10-20% | Sem perda significativa |
| -O3 | 15-25% | Possível ganho de performance |

### Verificação pós-otimização

```bash
# Verificar se o binário otimizado continua válido
wasm-opt --validate output.wasm

# Comparar comportamento
wasm-opt --output-source-map-url=source.map input.wasm -o output.wasm

# Testar execução
node --experimental-wasm-modules test.js
```

---

## 4.8 wasm-tools

### Introdução ao wasm-tools

O wasm-tools é um conjunto de ferramentas de linha de comando e bibliotecas Rust para manipulação de módulos WebAssembly. Diferentemente do wasm-opt, que foca em otimização, o wasm-tools fornece operações de baixo nível como inspeção, manipulação, composição e transformação de módulos Wasm.

O wasm-tools é mantido pelo Bytecode Alliance e é a ferramenta de referência para trabalho com o formato binário WebAssembly.

### Instalação

```bash
cargo install wasm-tools
```

### Comandos principais

**wasm-tools validate**: Valida um módulo Wasm

```bash
wasm-tools validate my_module.wasm
wasm-tools validate --features=bulk-memory,simd my_module.wasm
```

**wasm-tools print**: Converte binário Wasm para formato textual WAT

```bash
wasm-tools print my_module.wasm
wasm-tools print my_module.wasm --output my_module.wat
```

**wasm-tools parse**: Converte WAT para binário Wasm

```bash
wasm-tools parse my_module.wat -o my_module.wasm
```

**wasm-tools dump**: Mostra detalhes do módulo em formato legível

```bash
wasm-tools dump my_module.wasm
```

**wasm-tools stats**: Mostra estatísticas do módulo

```bash
wasm-tools stats my_module.wasm
```

### Inspeção de módulos

```bash
# Listar importações
wasm-tools dump my_module.wasm | grep "import"

# Listar exportações
wasm-tools dump my_module.wasm | grep "export"

# Listar funções
wasm-tools dump my_module.wasm | grep "func"

# Listar tipos
wasm-tools dump my_module.wasm | grep "type"
```

### Manipulação de módulos

**Merge de módulos**:

```bash
wasm-tools compose a.wasm b.wasm -o merged.wasm
```

**Adicionar WASI**:

```bash
wasm-tools component new my_module.wasm \
    --adapt wasi_snapshot_preview1=my_wasi_adapter.wasm \
    -o my_component.wasm
```

**Remover seções desnecessárias**:

```bash
wasm-tools strip my_module.wasm -o stripped.wasm
```

### Component Model

O wasm-tools suporta o novo Component Model do WebAssembly:

```bash
# Criar um componente
wasm-tools component new my_module.wasm \
    --world "my-world" \
    -o my_component.wasm

# Inspecionar componente
wasm-tools component wit my_component.wasm

# Validar componente
wasm-tools component validate my_component.wasm
```

### Wit (WebAssembly Interface Types)

O wasm-tools trabalha com arquivos WIT para definir interfaces:

```wit
// world.wit
package example:component;

interface calculator {
    add: func(a: s32, b: s32) -> s32;
    subtract: func(a: s32, b: s32) -> s32;
}

world my-calculator {
    export calculator;
}
```

### Uso em scripts

```bash
#!/bin/bash
# build_and_validate.sh

set -e

# Compilar
cargo build --release --target wasm32-unknown-unknown

INPUT="target/wasm32-unknown-unknown/release/my_project.wasm"
OUTPUT="dist/my_project.wasm"

# Validar
wasm-tools validate $INPUT

# Otimizar
wasm-opt -Oz $INPUT -o $OUTPUT

# Verificar resultado
wasm-tools stats $OUTPUT

echo "Build complete: $OUTPUT"
```

### Integração com CI

```yaml
# .github/workflows/wasm.yml
- name: Install wasm-tools
  run: cargo install wasm-tools

- name: Validate WASM
  run: wasm-tools validate target/wasm32-unknown-unknown/release/*.wasm

- name: Generate stats
  run: wasm-tools stats target/wasm32-unknown-unknown/release/*.wasm > stats.txt
```

### Subcomandos úteis

```bash
# Listar todos os subcomandos
wasm-tools --help

# Verificar versão
wasm-tools --version

# Ajuda específica
wasm-tools validate --help
wasm-tools print --help
wasm-tools dump --help
```

---

## 4.9 Debugging com console.log

### Introdução ao debugging Wasm

Debugging código WebAssembly no navegador apresenta desafios únicos. Diferentemente do JavaScript, que é interpretado e pode ser inspecionado diretamente no console, o código Wasm é compilado para bytecode de baixo nível. Isso requer ferramentas e técnicas específicas para entender o que está acontecendo durante a execução.

### wasm-bindgen console.log

A forma mais básica de debugging é usar console.log através do web-sys:

```rust
use web_sys::console;

#[wasm_bindgen]
pub fn debug_value(value: i32) {
    console::log_1(&format!("Value: {}", value).into());
}

#[wasm_bindgen]
pub fn debug_multiple(a: i32, b: i32, c: &str) {
    console::log_1(&format!("a={}, b={}, c={}", a, b, c).into());
}
```

### Macros de debug

Crie macros reutilizáveis para debugging:

```rust
macro_rules! console_log {
    ($($t:tt)*) => {
        web_sys::console::log_1(&format!($($t)*).into())
    };
}

macro_rules! console_error {
    ($($t:tt)*) => {
        web_sys::console::error_1(&format!($($t)*).into())
    };
}

macro_rules! console_warn {
    ($($t:tt)*) => {
        web_sys::console::warn_1(&format!($($t)*).into())
    };
}

#[wasm_bindgen]
pub fn debug_with_macros() {
    console_log!("Debug message: {}", 42);
    console_error!("Error occurred: {}", "something went wrong");
    console_warn!("Warning: {}", "potential issue");
}
```

### Logging estruturado

```rust
use serde::Serialize;
use wasm_bindgen::prelude::*;

#[derive(Serialize)]
struct DebugInfo {
    message: String,
    level: String,
    timestamp: f64,
    data: Option<String>,
}

#[wasm_bindgen]
pub fn log_structured(message: &str, data: Option<String>) {
    let window = web_sys::window().unwrap();
    let performance = window.performance().unwrap();

    let info = DebugInfo {
        message: message.to_string(),
        level: "info".to_string(),
        timestamp: performance.now(),
        data,
    };

    let json = serde_json::to_string(&info).unwrap();
    console::log_1(&json.into());
}
```

### Source Maps

Para debugging com source maps, compile com informações de debug:

```toml
[profile.dev]
debug = true
debug-assertions = true

[profile.release]
debug = true  # Incluir source maps em release
```

O Trunk gera automaticamente source maps quando compilado em modo debug:

```bash
trunk serve --dev
```

### Debugging com wasm-pack

```bash
# Compilar com source maps
wasm-pack build --dev

# Abrir navegador para debug
wasm-pack test --chrome  # Abre navegador com devtools
```

### Console API completa

```rust
use web_sys::console;

#[wasm_bindgen]
pub fn demonstrate_console_api() {
    // Log simples
    console::log_1(&"Simple log".into());

    // Log com múltiplos argumentos
    console::log_2(&"Name:".into(), &"John".into());

    // Tabela (para arrays de objetos)
    let data = js_sys::Array::new();
    data.push(&JsValue::from_str("item1"));
    data.push(&JsValue::from_str("item2"));
    console::table(&data);

    // Timing
    console::time_with_label("operation");
    // ... operação ...
    console::time_end_with_label("operation");

    // Contagem
    console::count_with_label("iterations");

    // Agrupamento
    console::group();
    console::log_1(&"Nested log".into());
    console::group_end();

    // Assert
    console::assert_with_condition(true, &"Assertion passed".into());

    // Clear
    console::clear();
}
```

### Breakpoints programáticos

```rust
use web_sys::console;

#[wasm_bindgen]
pub fn function_with_breakpoint(value: i32) {
    // Usar debugger statement via JS
    js_sys::eval("debugger;").unwrap();

    console::log_1(&format!("Processing: {}", value).into());
}
```

### Logging condicional

```rust
#[cfg(debug_assertions)]
macro_rules! debug_log {
    ($($t:tt)*) => {
        web_sys::console::log_1(&format!($($t)*).into())
    };
}

#[cfg(not(debug_assertions))]
macro_rules! debug_log {
    ($($t:tt)*) => {};
}

#[wasm_bindgen]
pub fn production_function(data: &[f64]) -> f64 {
    debug_log!("Input data length: {}", data.len());

    let result: f64 = data.iter().sum();

    debug_log!("Result: {}", result);
    result
}
```

### Performance profiling

```rust
use web_sys::{console, Performance, Window};

#[wasm_bindgen]
pub fn profile_operation() {
    let window: Window = web_sys::window().unwrap();
    let performance: Performance = window.performance().unwrap();

    let start = performance.now();

    // Código a ser medido
    let mut sum = 0.0;
    for i in 0..1_000_000 {
        sum += (i as f64).sqrt();
    }

    let end = performance.now();
    let duration = end - start;

    console::log_1(&format!("Operation took: {}ms", duration).into());
    console::log_1(&format!("Result: {}", sum).into());
}
```

### Error reporting

```rust
use web_sys::console;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn risky_operation() -> Result<f64, JsValue> {
    let input = "not a number";

    match input.parse::<f64>() {
        Ok(value) => Ok(value),
        Err(e) => {
            let error_msg = format!("Parse error: {} for input '{}'", e, input);
            console::error_1(&error_msg.into());
            Err(JsValue::from_str(&error_msg))
        }
    }
}

#[wasm_bindgen]
pub fn with_error_boundary() {
    match risky_operation() {
        Ok(value) => console::log_1(&format!("Success: {}", value).into()),
        Err(_) => console::error_1(&"Operation failed".into()),
    }
}
```

### DevTools Features

1. **Sources tab**: Navegue pelo código Wasm em formato decaompilado
2. **Memory tab**: Inspecione a memória linear do Wasm
3. **Performance tab**: Analise a performance do código Wasm
4. **Console**: Execute comandos e veja logs

### Dicas de debugging

1. Compile com `--dev` para ter source maps
2. Use `console.log` para valores intermediários
3. Aproveite o Performance profiling do navegador
4. Use breakpoints programáticos quando necessário
5. Implemente logging condicional para produção

---

## 4.10 Publicação no npm

### Preparação do pacote

Antes de publicar no npm, é necessário preparar o pacote com todas as informações necessárias:

```toml
# Cargo.toml
[package]
name = "my-wasm-lib"
version = "0.1.0"
description = "A WebAssembly library compiled from Rust"
license = "MIT"
repository = "https://github.com/user/my-wasm-lib"
```

### Configuração do wasm-pack para npm

```bash
wasm-pack build --target web --out-dir pkg
```

O diretório pkg/ conterá:

```
pkg/
├── package.json
├── my_wasm_lib.js
├── my_wasm_lib.d.ts
├── my_wasm_lib_bg.wasm
└── my_wasm_lib_bg.wasm.d.ts
```

### package.json personalizado

```json
{
  "name": "my-wasm-lib",
  "version": "0.1.0",
  "description": "WebAssembly library for advanced computations",
  "main": "my_wasm_lib.js",
  "types": "my_wasm_lib.d.ts",
  "files": [
    "my_wasm_lib.js",
    "my_wasm_lib.d.ts",
    "my_wasm_lib_bg.wasm",
    "my_wasm_lib_bg.wasm.d.ts"
  ],
  "scripts": {
    "build": "wasm-pack build --target web",
    "test": "wasm-pack test --headless --chrome",
    "prepublishOnly": "npm run build"
  },
  "keywords": [
    "wasm",
    "webassembly",
    "rust",
    "performance",
    "computation"
  ],
  "author": "Your Name",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/user/my-wasm-lib"
  },
  "homepage": "https://github.com/user/my-wasm-lib#readme",
  "bugs": {
    "url": "https://github.com/user/my-wasm-lib/issues"
  },
  "engines": {
    "node": ">=16.0.0"
  }
}
```

### Login no npm

```bash
npm login
```

### Publicação

```bash
# Publicar (primeira vez)
npm publish

# Atualizar versão
npm version patch  # 0.1.0 -> 0.1.1
npm version minor  # 0.1.1 -> 0.2.0
npm version major  # 0.2.0 -> 1.0.0
npm publish

# Publicar com tag
npm publish --tag beta

# Publicar com scope
npm publish --access public
```

### Escopo de pacotes

```bash
# Criar pacote com escopo
npm init --scope=@myorg
npm publish --access public
```

### Verificação de publicação

```bash
# Verificar pacote local
npm pack --dry-run

# Verificar no npm
npm view my-wasm-lib

# Testar instalação
npm install my-wasm-lib --save
```

### USO do pacote

```javascript
import init, { my_function } from 'my-wasm-lib';

async function main() {
    await init();

    const result = my_function(42);
    console.log(result);
}

main();
```

### CI/CD para npm

```yaml
# .github/workflows/npm-publish.yml
name: Publish to npm

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          targets: wasm32-unknown-unknown

      - name: Install wasm-pack
        run: cargo install wasm-pack

      - name: Build
        run: wasm-pack build --target web

      - name: Publish
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Versionamento

Siga Semantic Versioning (semver):

- **MAJOR** (1.0.0 -> 2.0.0): Breaking changes
- **MINOR** (0.1.0 -> 0.2.0): Novas funcionalidades
- **PATCH** (0.1.0 -> 0.1.1): Bug fixes

### README

```markdown
# my-wasm-lib

WebAssembly library for advanced computations, compiled from Rust.

## Installation

```bash
npm install my-wasm-lib
```

## Usage

```javascript
import init, { compute } from 'my-wasm-lib';

await init();
const result = compute([1, 2, 3, 4, 5]);
console.log(result);
```

## API

### `compute(data: number[]): number`

Computes the sum of an array of numbers.

## License

MIT
```

---

## 4.11 Exemplo de aplicação completa

### Projeto: Biblioteca de processamento de imagens

Este exemplo demonstra uma biblioteca completa que processa imagens usando Rust e WebAssembly.

**Estrutura do projeto**:

```
image-processor/
├── Cargo.toml
├── src/
│   └── lib.rs
├── benches/
│   └── benchmark.rs
├── tests/
│   └── integration_test.rs
├── www/
│   ├── index.html
│   ├── index.js
│   └── style.css
└── pkg/
```

**Cargo.toml**:

```toml
[package]
name = "image-processor"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
wasm-bindgen = "0.2"
js-sys = "0.3"
web-sys = { version = "0.3", features = [
    "console",
    "Document",
    "Element",
    "HtmlCanvasElement",
    "CanvasRenderingContext2d",
    "ImageData",
    "Window",
] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[dev-dependencies]
wasm-bindgen-test = "0.3"

[profile.release]
opt-level = "z"
lto = true
codegen-units = 1
panic = "abort"
strip = true
```

**src/lib.rs**:

```rust
use wasm_bindgen::prelude::*;
use web_sys::{CanvasRenderingContext2d, HtmlCanvasElement, ImageData};

// Filtros de imagem
#[wasm_bindgen]
pub fn grayscale(data: &mut [u8], width: u32, height: u32) {
    let pixel_count = (width * height) as usize;

    for i in 0..pixel_count {
        let offset = i * 4;
        let r = data[offset] as f64;
        let g = data[offset + 1] as f64;
        let b = data[offset + 2] as f64;

        let gray = (0.299 * r + 0.587 * g + 0.114 * b) as u8;

        data[offset] = gray;
        data[offset + 1] = gray;
        data[offset + 2] = gray;
    }
}

#[wasm_bindgen]
pub fn blur(data: &[u8], width: u32, height: u32, radius: u32) -> Vec<u8> {
    let mut output = vec![0u8; data.len()];
    let pixel_count = (width * height) as usize;

    for y in 0..height {
        for x in 0..width {
            let mut r = 0.0;
            let mut g = 0.0;
            let mut b = 0.0;
            let mut count = 0;

            for dy in -(radius as i32)..=(radius as i32) {
                for dx in -(radius as i32)..=(radius as i32) {
                    let nx = x as i32 + dx;
                    let ny = y as i32 + dy;

                    if nx >= 0 && nx < width as i32 && ny >= 0 && ny < height as i32 {
                        let idx = ((ny as u32 * width + nx as u32) * 4) as usize;
                        r += data[idx] as f64;
                        g += data[idx + 1] as f64;
                        b += data[idx + 2] as f64;
                        count += 1;
                    }
                }
            }

            let idx = ((y * width + x) * 4) as usize;
            output[idx] = (r / count as f64) as u8;
            output[idx + 1] = (g / count as f64) as u8;
            output[idx + 2] = (b / count as f64) as u8;
            output[idx + 3] = data[idx + 3];
        }
    }

    output
}

#[wasm_bindgen]
pub fn brightness(data: &mut [u8], factor: f64) {
    for i in (0..data.len()).step_by(4) {
        data[i] = (data[i] as f64 * factor).min(255.0) as u8;
        data[i + 1] = (data[i + 1] as f64 * factor).min(255.0) as u8;
        data[i + 2] = (data[i + 2] as f64 * factor).min(255.0) as u8;
    }
}

#[wasm_bindgen]
pub fn contrast(data: &mut [u8], factor: f64) {
    let intercept = 128.0 * (1.0 - factor);

    for i in (0..data.len()).step_by(4) {
        data[i] = (data[i] as f64 * factor + intercept).min(255.0).max(0.0) as u8;
        data[i + 1] = (data[i + 1] as f64 * factor + intercept).min(255.0).max(0.0) as u8;
        data[i + 2] = (data[i + 2] as f64 * factor + intercept).min(255.0).max(0.0) as u8;
    }
}

#[wasm_bindgen]
pub fn sepia(data: &mut [u8]) {
    for i in (0..data.len()).step_by(4) {
        let r = data[i] as f64;
        let g = data[i + 1] as f64;
        let b = data[i + 2] as f64;

        data[i] = (0.393 * r + 0.769 * g + 0.189 * b).min(255.0) as u8;
        data[i + 1] = (0.349 * r + 0.686 * g + 0.168 * b).min(255.0) as u8;
        data[i + 2] = (0.272 * r + 0.534 * g + 0.131 * b).min(255.0) as u8;
    }
}

// Estrutura para processamento de imagem
#[wasm_bindgen]
pub struct ImageProcessor {
    width: u32,
    height: u32,
    data: Vec<u8>,
}

#[wasm_bindgen]
impl ImageProcessor {
    #[wasm_bindgen(constructor)]
    pub fn new(width: u32, height: u32, data: &[u8]) -> ImageProcessor {
        ImageProcessor {
            width,
            height,
            data: data.to_vec(),
        }
    }

    #[wasm_bindgen(js_name = getWidth)]
    pub fn get_width(&self) -> u32 {
        self.width
    }

    #[wasm_bindgen(js_name = getHeight)]
    pub fn get_height(&self) -> u32 {
        self.height
    }

    #[wasm_bindgen(js_name = getData)]
    pub fn get_data(&self) -> &[u8] {
        &self.data
    }

    #[wasm_bindgen(js_name = applyGrayscale)]
    pub fn apply_grayscale(&mut self) {
        grayscale(&mut self.data, self.width, self.height);
    }

    #[wasm_bindgen(js_name = applyBlur)]
    pub fn apply_blur(&mut self, radius: u32) {
        self.data = blur(&self.data, self.width, self.height, radius);
    }

    #[wasm_bindgen(js_name = applyBrightness)]
    pub fn apply_brightness(&mut self, factor: f64) {
        brightness(&mut self.data, factor);
    }

    #[wasm_bindgen(js_name = applyContrast)]
    pub fn apply_contrast(&mut self, factor: f64) {
        contrast(&mut self.data, factor);
    }

    #[wasm_bindgen(js_name = applySepia)]
    pub fn apply_sepia(&mut self) {
        sepia(&mut self.data);
    }

    #[wasm_bindgen(js_name = applyCustomFilter)]
    pub fn apply_custom_filter(&mut self, filter_type: &str, params: &str) {
        match filter_type {
            "brightness" => {
                let factor: f64 = params.parse().unwrap_or(1.0);
                self.apply_brightness(factor);
            }
            "contrast" => {
                let factor: f64 = params.parse().unwrap_or(1.0);
                self.apply_contrast(factor);
            }
            "blur" => {
                let radius: u32 = params.parse().unwrap_or(1);
                self.apply_blur(radius);
            }
            _ => {
                web_sys::console::error_1(&format!("Unknown filter: {}", filter_type).into());
            }
        }
    }
}

// Funções utilitárias
#[wasm_bindgen]
pub fn get_pixel(data: &[u8], width: u32, x: u32, y: u32) -> Vec<u8> {
    let idx = ((y * width + x) * 4) as usize;
    vec![data[idx], data[idx + 1], data[idx + 2], data[idx + 3]]
}

#[wasm_bindgen]
pub fn set_pixel(data: &mut [u8], width: u32, x: u32, y: u32, color: &[u8]) {
    let idx = ((y * width + x) * 4) as usize;
    data[idx] = color[0];
    data[idx + 1] = color[1];
    data[idx + 2] = color[2];
    data[idx + 3] = color[3];
}

#[wasm_bindgen]
pub fn histogram(data: &[u8]) -> Vec<u32> {
    let mut hist = vec![0u32; 256];

    for i in (0..data.len()).step_by(4) {
        let gray = (0.299 * data[i] as f64 + 0.587 * data[i + 1] as f64 + 0.114 * data[i + 2] as f64) as u8;
        hist[gray as usize] += 1;
    }

    hist
}
```

**www/index.html**:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Processor - WASM</title>
    <link data-trunk rel="css" href="style.css">
</head>
<body>
    <div id="app">
        <h1>Image Processor</h1>
        <div class="controls">
            <input type="file" id="fileInput" accept="image/*">
            <select id="filterSelect">
                <option value="grayscale">Grayscale</option>
                <option value="blur">Blur</option>
                <option value="brightness">Brightness</option>
                <option value="contrast">Contrast</option>
                <option value="sepia">Sepia</option>
            </select>
            <input type="range" id="paramSlider" min="0" max="200" value="100">
            <button id="applyBtn">Apply Filter</button>
            <button id="resetBtn">Reset</button>
        </div>
        <div class="canvas-container">
            <canvas id="originalCanvas"></canvas>
            <canvas id="processedCanvas"></canvas>
        </div>
        <div id="stats"></div>
    </div>

    <link data-trunk rel="rust" data-wasm-opt="z">
</body>
</html>
```

**www/index.js**:

```javascript
import init, { ImageProcessor, grayscale, blur, histogram } from '../pkg/image_processor.js';

let processor = null;
let originalData = null;

async function main() {
    await init();

    const fileInput = document.getElementById('fileInput');
    const filterSelect = document.getElementById('filterSelect');
    const paramSlider = document.getElementById('paramSlider');
    const applyBtn = document.getElementById('applyBtn');
    const resetBtn = document.getElementById('resetBtn');
    const originalCanvas = document.getElementById('originalCanvas');
    const processedCanvas = document.getElementById('processedCanvas');

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const img = new Image();
        img.onload = () => {
            originalCanvas.width = img.width;
            originalCanvas.height = img.height;
            processedCanvas.width = img.width;
            processedCanvas.height = img.height;

            const ctx = originalCanvas.getContext('2d');
            ctx.drawImage(img, 0, 0);

            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            originalData = new Uint8Array(imageData.data);

            processor = new ImageProcessor(img.width, img.height, originalData);
        };
        img.src = URL.createObjectURL(file);
    });

    applyBtn.addEventListener('click', () => {
        if (!processor) return;

        const filter = filterSelect.value;
        const param = parseInt(paramSlider.value);

        const start = performance.now();

        switch (filter) {
            case 'grayscale':
                processor.applyGrayscale();
                break;
            case 'blur':
                processor.applyBlur(Math.floor(param / 20));
                break;
            case 'brightness':
                processor.applyBrightness(param / 100);
                break;
            case 'contrast':
                processor.applyContrast(param / 100);
                break;
            case 'sepia':
                processor.applySepia();
                break;
        }

        const end = performance.now();
        const duration = end - start;

        const processedCtx = processedCanvas.getContext('2d');
        const processedImageData = new ImageData(
            new Uint8ClampedArray(processor.getData()),
            processor.getWidth(),
            processor.getHeight()
        );
        processedCtx.putImageData(processedImageData, 0, 0);

        document.getElementById('stats').textContent = 
            `Processing time: ${duration.toFixed(2)}ms`;
    });

    resetBtn.addEventListener('click', () => {
        if (!processor || !originalData) return;

        const ctx = processedCanvas.getContext('2d');
        const imageData = new ImageData(
            new Uint8ClampedArray(originalData),
            processor.getWidth(),
            processor.getHeight()
        );
        ctx.putImageData(imageData, 0, 0);
    });
}

main();
```

**www/style.css**:

```css
body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: #1a1a2e;
    color: #eee;
}

h1 {
    text-align: center;
    color: #00d9ff;
}

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    justify-content: center;
}

.canvas-container {
    display: flex;
    gap: 20px;
    justify-content: center;
    flex-wrap: wrap;
}

canvas {
    max-width: 100%;
    border: 2px solid #333;
    background: #000;
}

#stats {
    text-align: center;
    margin-top: 20px;
    font-size: 1.2em;
    color: #00ff88;
}
```

### Executando o projeto

```bash
# Instalar dependências
rustup target add wasm32-unknown-unknown
cargo install wasm-pack trunk

# Compilar e servir
trunk serve
```

### Testes

```rust
// tests/integration_test.rs
use wasm_bindgen_test::*;
use image_processor::{ImageProcessor, grayscale, blur, histogram};

wasm_bindgen_test_configure!(run_in_browser);

#[wasm_bindgen_test]
fn test_grayscale() {
    let mut data = vec![
        255, 0, 0, 255,    // Vermelho
        0, 255, 0, 255,    // Verde
        0, 0, 255, 255,    // Azul
        255, 255, 255, 255 // Branco
    ];

    grayscale(&mut data, 2, 2);

    // Verificar se todos os canais RGB foram equalizados
    assert_eq!(data[0], data[1]);
    assert_eq!(data[1], data[2]);
}

#[wasm_bindgen_test]
fn test_histogram() {
    let data = vec![128, 128, 128, 255, 0, 0, 0, 255];
    let hist = histogram(&data);

    assert_eq!(hist[0], 1); // Um pixel preto
    assert_eq!(hist[128], 1); // Um pixel cinza
    assert_eq!(hist[255], 1); // Um pixel branco
}

#[wasm_bindgen_test]
fn test_image_processor() {
    let data = vec![255, 0, 0, 255, 0, 255, 0, 255];
    let mut processor = ImageProcessor::new(2, 1, &data);

    assert_eq!(processor.get_width(), 2);
    assert_eq!(processor.get_height(), 1);

    processor.applyGrayscale();

    let result = processor.getData();
    assert_eq!(result[0], result[1]);
    assert_eq!(result[1], result[2]);
}
```

### Benchmark

```rust
// benches/benchmark.rs
use criterion::{black_box, criterion_group, criterion_main, Criterion};
use image_processor::{ImageProcessor, grayscale, blur};

fn benchmark_grayscale(c: &mut Criterion) {
    let data = vec![128u8; 1920 * 1080 * 4]; // Full HD image

    c.bench_function("grayscale 1080p", |b| {
        b.iter(|| {
            let mut data_clone = data.clone();
            grayscale(black_box(&mut data_clone), 1920, 1080);
        });
    });
}

fn benchmark_blur(c: &mut Criterion) {
    let data = vec![128u8; 1920 * 1080 * 4]; // Full HD image

    c.bench_function("blur radius 5 1080p", |b| {
        b.iter(|| {
            blur(black_box(&data), 1920, 1080, 5);
        });
    });
}

criterion_group!(benches, benchmark_grayscale, benchmark_blur);
criterion_main!(benches);
```

### Publicação

```bash
# Build para produção
wasm-pack build --target web --release

# Publicar no npm
cd pkg
npm publish
```

### Resultados esperados

- Grayscale: ~2ms para imagem Full HD
- Blur (raio 5): ~50ms para imagem Full HD
- Tamanho do binário: ~100KB com otimizações

---

## Resumo

Este capítulo cobriu o ecossistema completo de Rust para WebAssembly:

1. **rustup e targets**: Configuração do toolchain e targets Wasm
2. **wasm-pack**: Build tool para compilação e empacotamento
3. **wasm-bindgen**: FFI entre Rust e JavaScript
4. **Trunk**: Framework de desenvolvimento web
5. **Leptos e Yew**: Frameworks de UI declarativa
6. **wasm-pack test**: Testes em ambientes reais
7. **wasm-opt**: Otimização de binários Wasm
8. **wasm-tools**: Manipulação de módulos Wasm
9. **Debugging**: Técnicas de depuração com console.log
10. **Publicação npm**: Distribuição de pacotes
11. **Exemplo completo**: Biblioteca de processamento de imagens

O Rust continua sendo uma das melhores escolhas para WebAssembly devido à sua segurança de memória, performance e ecossistema maduro. Combinado com ferramentas como wasm-pack e wasm-bindgen, o desenvolvimento de aplicações Wasm em Rust é eficiente e produtivo.
---

*[Capítulo anterior: 03 — Wasi System Interface](03-wasi-system-interface.md)*
*[Próximo capítulo: 05 — Cpp Emscripten](05-cpp-emscripten.md)*
