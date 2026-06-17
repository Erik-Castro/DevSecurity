# Capítulo 8: Component Model

## 8.1 Introdução ao Component Model

O Component Model do WebAssembly é uma evolução significativa do ecossistema Wasm, projetado para resolver um dos desafios mais fundamentais da plataforma: a interoperação segura e eficiente entre módulos de diferentes linguagens. Enquanto o modelo de segurança Wasm fornece isolamento de memória e computação, o Component Model adiciona um sistema de tipos rico e mecanismos de composição que permitem criar aplicações complexas a partir de componentes heterogêneos.

### 8.1.1 O Problema que o Component Model Resolve

No Wasm tradicional, módulos se comunicam através de funções exportadas e importadas com assinaturas limitadas a tipos numéricos básicos (i32, i64, f32, f64). Isso cria várias limitações:

**Falta de tipos compostos**: Não é possível passar estruturas, strings ou listas diretamente entre módulos. Toda comunicação requer serialização manual.

**Sem semântica de interfaces**: As importações e exportações não comunicam a intenção do programador. Uma função `process(i32, i32) -> i32` pode significar qualquer coisa.

**Interoperabilidade limitada**: Módulos em diferentes linguagens não conseguem se comunicar facilmente, pois cada linguagem tem convenções diferentes para passagem de parâmetros.

**Sem suporte a recursos**: O modelo original não distingue entre dados e recursos que possuem ciclo de vida (como handles de arquivo ou conexões de rede).

### 8.1.2 Visão Geral da Arquitetura

O Component Model introduz uma camada de abstração acima dos módulos Wasm tradicionais:

```
┌─────────────────────────────────────────────────────────┐
│                   Aplicação                             │
├─────────────────────────────────────────────────────────┤
│              Component Model Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Component A │  │ Component B │  │ Component C │    │
│  │  (Rust)     │←→│  (Python)   │←→│  (Go)       │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│         ↕               ↕               ↕               │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Interface Types Layer                  │   │
│  │  string, list, record, variant, enum, flags     │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│              Wasm Core Layer                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │         Linear Memory + Functions                │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 8.2 Tipos de Interface do Componente

O Component Model define um sistema de tipos rico que vai muito além dos tipos numéricos básicos do Wasm core. Esses tipos de interface permitem expressar estruturas de dados complexas de forma segura e eficiente.

### 8.2.1 Tipos Primitivos Estendidos

Além dos tipos numéricos do Wasm core, o Component Model adiciona:

```wit
// Tipos numéricos com semântica clara
package example:types;

// Inteiros com tamanhos específicos
type byte = u8;
type signed-byte = s8;
type short = u16;
type signed-short = s16;
type int = u32;
type signed-int = s32;
type long = u64;
type signed-long = s64;

// Tipos de ponto flutuante
type float = f32;
type double = f64;

// Booleano
type boolean = bool;

// Caractere Unicode
type char = char;

// String UTF-8
type string = string;

// Lista homogênea
type list-of-bytes = list<u8>;
type list-of-strings = list<string>;

// Tupla (tipos heterogêneos)
type name-and-age = tuple<string, u32>;

// Option (pode ser null ou ter valor)
type maybe-string = option<string>;

// Result (sucesso ou erro)
type parse-result = result<u64, string>;

// Tuple com múltiplos elementos
type coordinate = tuple<f64, f64, f64>;
```

### 8.2.2 Records (Registros)

Records são estruturas nomeadas, similares a structs em C ou records em outros linguagens:

```wit
package example:records;

// Record básico
record person {
    name: string,
    age: u32,
    email: option<string>,
}

// Record com campos complexos
record address {
    street: string,
    city: string,
    state: string,
    zip-code: string,
    country: string,
}

// Record aninhado
record person-with-address {
    person: person,
    address: address,
    metadata: option<map<string, string>>,
}

// Record com opções
record configuration {
    host: string,
    port: u16,
    use-tls: bool,
    timeout-seconds: option<u32>,
    max-connections: option<u32>,
}

// Uso em funções
interface person-api {
    create-person: func(name: string, age: u32) -> person;
    validate-person: func(person: person) -> result<_, string>;
    serialize-person: func(person: person) -> list<u8>;
}
```

### 8.2.3 Variants (Variantes)

Variants são tipos discriminados, similares a unions ou enums com dados:

```wit
package example:variants;

// Enum simples
enum color {
    red,
    green,
    blue,
    yellow,
}

// Variant com dados associados
variant shape {
    circle(f64),                    // raio
    rectangle(f64, f64),           // largura, altura
    triangle(f64, f64, f64),       // três lados
    polygon(list<tuple<f64, f64>>), // vértices
}

// Result type (já definido, mas para referência)
variant result-ok<ok, err> {
    ok(ok),
    err(err),
}

// Error types tipados
variant http-error {
    not-found,
    forbidden,
    internal-server-error(string),
    timeout(u32),  // timeout em ms
}

// Command pattern
variant command {
    start(u32),           // job id
    stop(u32),            // job id
    pause(u32),           // job id
    resume(u32),          // job id
    status,               // query
}

// Uso em funções
interface shape-api {
    area: func(shape: shape) -> result<f64, string>;
    perimeter: func(shape: shape) -> result<f64, string>;
    to-svg: func(shape: shape, color: color) -> string;
}
```

### 8.2.4 Flags

Flags são conjuntos de opções booleanas, eficientes para configurações:

```wit
package example:flags;

// Flags para permissões de arquivo
flags file-permissions {
    read,
    write,
    execute,
    delete,
    rename,
    create,
}

// Flags para opções de log
flags log-options {
    timestamp,
    level,
    source,
    backtrace,
    json-format,
}

// Flags para opções de compilação
flags compile-options {
    optimize,
    debug,
    strip-symbols,
    generate-docs,
    run-tests,
}

// Uso em funções
interface file-api {
    open: func(path: string, permissions: file-permissions) -> result<file-descriptor, string>;
    configure-logging: func(options: log-options) -> unit;
}
```

### 8.2.5 Resources (Recursos)

Resources representam handles para objetos com ciclo de vida gerenciado:

```wit
package example:resources;

// Resource com ciclo de vida
resource database-connection {
    constructor(url: string);
    query: func(sql: string) -> result<list<row>, string>;
    execute: func(sql: string) -> result<u64, string>;
    close: func() -> unit;
}

// Resource para arquivo
resource file-handle {
    constructor(path: string, mode: string);
    read: func(buffer: list<u8>, offset: u64) -> result<u64, string>;
    write: func(data: list<u8>) -> result<u64, string>;
    seek: func(offset: u64, whence: seek-mode) -> result<u64, string>;
    close: func() -> unit;
}

// Resource para thread
resource thread {
    constructor(entry: func());
    join: func() -> unit;
    detach: func() -> unit;
    is-running: func() -> bool;
}

// Enum para seek
enum seek-mode {
    start,
    current,
    end,
}

// Resource para network socket
resource tcp-socket {
    constructor();
    connect: func(host: string, port: u16) -> result<_, string>;
    send: func(data: list<u8>) -> result<u64, string>;
    receive: func(buffer: list<u8>) -> result<u64, string>;
    close: func() -> unit;
}

// Uso em interfaces
interface storage-api {
    connect: func(url: string) -> result<database-connection, string>;
    open-file: func(path: string) -> result<file-handle, string>;
}
```

## 8.3 WASI Preview 2

O WASI Preview 2 é a especificação que implementa o Component Model para acesso a recursos do sistema operacional. Ele substitui o WASI Preview 1 com um sistema de interfaces mais rico e seguro.

### 8.3.1 Estrutura do WASI Preview 2

O WASI Preview 2 é organizado em "worlds" (mundos) que definem o ambiente completo de um componente:

```wit
// wasi:http/proxy.wld - World principal do WASI Preview 2

package wasi:http;

default world proxy {
    /// Imports disponíveis para um proxy HTTP
    import wasi:cli/stdin@0.2.0;
    import wasi:cli/stdout@0.2.0;
    import wasi:cli/stderr@0.2.0;
    import wasi:cli/environment@0.2.0;
    import wasi:cli/exit@0.2.0;
    import wasi:cli/terminal-input@0.2.0;
    import wasi:cli/terminal-output@0.2.0;
    import wasi:cli/terminal-stdin@0.2.0;
    import wasi:cli/terminal-stdout@0.2.0;
    import wasi:cli/terminal-stderr@0.2.0;
    
    import wasi:clocks/monotonic-clock@0.2.0;
    import wasi:clocks/wall-clock@0.2.0;
    
    import wasi:filesystem/preopens@0.2.0;
    import wasi:filesystem/types@0.2.0;
    
    import wasi:io/error@0.2.0;
    import wasi:io/streams@0.2.0;
    import wasi:io/poll@0.2.0;
    
    import wasi:http/types@0.2.0;
    import wasi/http/outgoing-handler@0.2.0;
    
    import wasi:sockets/instance-network@0.2.0;
    import wasi:sockets/network@0.2.0;
    import wasi:sockets/tcp-create-socket@0.2.0;
    import wasi:sockets/tcp@0.2.0;
    import wasi:sockets/udp-create-socket@0.2.0;
    import wasi:sockets/udp@0.2.0;
    
    /// Export que o componente deve implementar
    export wasi:http/incoming-handler@0.2.0;
}
```

### 8.3.2 Interfaces Principais do WASI Preview 2

```wit
// wasi:cli/environment - Acesso a variáveis de ambiente
package wasi:cli@0.2.0;

interface environment {
    get-environment: func() -> list<tuple<string, string>>;
    get-arguments: func() -> list<string>;
    initial-cwd: func() -> option<string>;
}

// wasi:filesystem/types - Operações de filesystem
package wasi:filesystem@0.2.0;

interface types {
    /// Descriptor de arquivo
    resource descriptor;
    
    /// Tipos de arquivo
    enum descriptor-type {
        unknown,
        block-device,
        character-device,
        directory,
        fifo,
        symbolic-link,
        regular-file,
        socket,
        message-queue,
        semaphore,
        shared-memory,
    }
    
    /// Metadados do arquivo
    record metadata {
        type: descriptor-type,
        link-count: option<u64>,
        data-size: option<u64>,
        data-access-time: option<wall-clock>,
        data-modification-time: option<wall-clock>,
        status-change-time: option<wall-clock>,
    }
    
    /// Operações de leitura
    resource input-stream {
        read: func(len: u64) -> result<list<u8>, error>;
        blocking-read: func(len: u64) -> result<list<u8>, error>;
        skip: func(len: u64) -> result<u64, error>;
        blocking-skip: func(len: u64) -> result<u64, error>;
        subscribe: func() -> pollable;
    }
    
    /// Operações de escrita
    resource output-stream {
        check-write: func() -> result<u64, error>;
        write: func(contents: list<u8>) -> result<u64, error>;
        blocking-write-and-flush: func(contents: list<u8>) -> result<_, error>;
        flush: func() -> result<_, error>;
        blocking-flush: func() -> result<_, error>;
        subscribe: func() -> pollable;
    }
}

// wasi:http/types - Operações HTTP
package wasi:http@0.2.0;

interface types {
    /// Método HTTP
    enum method {
        get,
        head,
        post,
        put,
        delete,
        connect,
        options,
        trace,
        patch,
        other(string),
    }
    
    /// Esquema de URI
    enum scheme {
        http,
        https,
        other(string),
    }
    
    /// Status HTTP
    type status-code = u16;
    
    /// Requisição HTTP
    record request {
        method: method,
        path-with-query: option<string>,
        authority: option<string>,
        scheme: option<scheme>,
        headers: list<tuple<string, string>>;
    }
    
    /// Resposta HTTP
    record response {
        status-code: status-code,
        headers: list<tuple<string, string>>;
    }
    
    /// Handler de requisição
    resource incoming-request {
        method: func() -> method;
        path-with-query: func() -> option<string>;
        authority: func() -> option<string>;
        scheme: func() -> option<scheme>;
        headers: func() -> list<tuple<string, string>>;
        consume: func() -> result<incoming-body, _>;
    }
    
    /// Handler de resposta
    resource outgoing-request {
        constructor();
        method: func() -> method;
        set-method: func(method: method) -> result<_, _>;
        path-with-query: func() -> option<string>;
        set-path-with-query: func(path: option<string>) -> result<_, _>;
        authority: func() -> option<string>;
        set-authority: func(authority: option<string>) -> result<_, _>;
        scheme: func() -> option<scheme>;
        set-scheme: func(scheme: option<scheme>) -> result<_, _>;
        headers: func() -> list<tuple<string, string>>;
        set-headers: func(headers: list<tuple<string, string>>) -> result<_, _>;
    }
}
```

### 8.3.3 Implementação com wasmtime

```rust
// Implementação de um componente WASI Preview 2
use wasmtime::component::{Component, Linker, ResourceTable};
use wasmtime::{Engine, Store, Result};
use wasmtime_wasi::preview2;

// Definir o componente
wascomponent::generate!({
    world: "proxy",
    path: "wit/"
});

struct MyState {
    wasi: preview2::WasiCtx,
    table: ResourceTable,
}

impl preview2::WasiView for MyState {
    fn table(&mut self) -> &mut ResourceTable {
        &mut self.table
    }
    
    fn ctx(&mut self) -> &mut preview2::WasiCtx {
        &mut self.wasi
    }
}

struct HttpServer;

impl exports::wasi::http::incoming_handler::Guest for HttpServer {
    fn handle(request: Request, response_out: ResponseOutparam) {
        // Processar requisição
        let method = request.method();
        let path = request.path_with_query().unwrap_or_default();
        
        // Criar resposta
        let response = Response::new(Some(
            &format!("Olá de WASI Preview 2!\nMétodo: {:?}\nCaminho: {}", method, path)
        ));
        
        // Enviar resposta
        response_out.set(response).unwrap();
    }
}

fn main() -> Result<()> {
    let engine = Engine::new(&wasmtime_wasi::preview2::wasi_config_with_ctx(
        preview2::WasiCtxBuilder::new()
            .inherit_stdio()
            .build()
    )?)?;
    
    let component = Component::from_file(&engine, "http-server.wasm")?;
    
    let mut linker = Linker::<MyState>::new(&engine);
    preview2::add_to_linker(&mut linker)?;
    
    let wasi = preview2::WasiCtxBuilder::new()
        .inherit_stdio()
        .build();
    
    let state = MyState {
        wasi,
        table: ResourceTable::new(),
    };
    
    let mut store = Store::new(&engine, state);
    
    let (instance, _) = HttpServer::instantiate(&mut store, &component, &linker)?;
    
    // O servidor está pronto para processar requisições
    println("Servidor HTTP WASI Preview 2 iniciado");
    
    Ok(())
}
```

## 8.4 Resource Types em Detalhe

Os resource types são uma das adições mais importantes do Component Model, permitindo que componentes gerenciem objetos com ciclo de vida de forma segura.

### 8.4.1 Ciclo de Vida de Resources

```wit
package example:lifecycle;

// Resource com ciclo de vida gerenciado
resource managed-resource {
    /// Construtor - chamado quando o resource é criado
    constructor(config: resource-config);
    
    /// Método de uso normal
    process: func(data: list<u8>) -> result<list<u8>, string>;
    
    /// Método de limpeza - chamado quando o resource é destruído
    drop: func() -> unit;
}

record resource-config {
    name: string,
    max-size: u64,
    timeout-ms: u32,
}

// Interface que gerencia o resource
interface resource-manager {
    /// Criar resource
    create-resource: func(config: resource-config) -> managed-resource;
    
    /// Usar resource (garante que está vivo)
    use-resource: func(resource: managed-resource, data: list<u8>) -> result<list<u8>, string>;
    
    /// Explicitamente destruir resource
    destroy-resource: func(resource: managed-resource) -> unit;
}
```

### 8.4.2 Implementação em Rust

```rust
use std::collections::HashMap;

// Estrutura interna do resource
struct ManagedResourceInternal {
    name: String,
    max_size: usize,
    timeout_ms: u32,
    data: Vec<u8>,
    created_at: std::time::Instant,
}

// Gerenciador de resources
struct ResourceManager {
    resources: HashMap<u64, ManagedResourceInternal>,
    next_id: u64,
}

impl ResourceManager {
    fn new() -> Self {
        Self {
            resources: HashMap::new(),
            next_id: 1,
        }
    }
    
    fn create(&mut self, config: ResourceConfig) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        
        let resource = ManagedResourceInternal {
            name: config.name,
            max_size: config.max_size as usize,
            timeout_ms: config.timeout_ms,
            data: Vec::new(),
            created_at: std::time::Instant::now(),
        };
        
        self.resources.insert(id, resource);
        id
    }
    
    fn process(&mut self, id: u64, data: &[u8]) -> Result<Vec<u8>, String> {
        let resource = self.resources.get_mut(&id)
            .ok_or_else(|| format!("Resource {} não encontrado", id))?;
        
        // Verificar timeout
        let elapsed = resource.created_at.elapsed().as_millis() as u32;
        if elapsed > resource.timeout_ms {
            return Err("Resource expirado".to_string());
        }
        
        // Verificar tamanho
        if data.len() > resource.max_size {
            return Err(format!("Dados excedem tamanho máximo: {} > {}", 
                             data.len(), resource.max_size));
        }
        
        // Processar dados
        resource.data.extend_from_slice(data);
        
        // Retornar resultado processado
        Ok(data.iter().map(|b| b.wrapping_add(1)).collect())
    }
    
    fn drop(&mut self, id: u64) -> Result<(), String> {
        self.resources.remove(&id)
            .ok_or_else(|| format!("Resource {} não encontrado", id))?;
        Ok(())
    }
    
    fn is_alive(&self, id: u64) -> bool {
        if let Some(resource) = self.resources.get(&id) {
            let elapsed = resource.created_at.elapsed().as_millis() as u32;
            elapsed <= resource.timeout_ms
        } else {
            false
        }
    }
}

// Implementação das funções exportadas
#[no_mangle]
pub extern "C" fn create_resource(config_ptr: *const u8, config_len: usize) -> u64 {
    // Deserializar config do WASM memory
    let config_bytes = unsafe {
        std::slice::from_raw_parts(config_ptr, config_len)
    };
    
    let config: ResourceConfig = bincode::deserialize(config_bytes)
        .expect("Falha ao deserializar config");
    
    MANAGER.lock().unwrap().create(config)
}

#[no_mangle]
pub extern "C" fn process_resource(
    id: u64, 
    data_ptr: *const u8, 
    data_len: usize,
    result_ptr: *mut u8,
    result_len: *mut usize
) -> i32 {
    let data = unsafe {
        std::slice::from_raw_parts(data_ptr, data_len)
    };
    
    match MANAGER.lock().unwrap().process(id, data) {
        Ok(result) => {
            let result_bytes = bincode::serialize(&result).unwrap();
            let len = result_bytes.len().min(*result_len);
            
            unsafe {
                std::ptr::copy_nonoverlapping(
                    result_bytes.as_ptr(),
                    result_ptr,
                    len
                );
                *result_len = len;
            }
            
            0 // Sucesso
        }
        Err(e) => {
            eprintln!("Erro: {}", e);
            -1 // Erro
        }
    }
}

#[no_mangle]
pub extern "C" fn drop_resource(id: u64) -> i32 {
    match MANAGER.lock().unwrap().drop(id) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("Erro: {}", e);
            -1
        }
    }
}

static MANAGER: std::sync::Mutex<ResourceManager> = 
    std::sync::Mutex::new(ResourceManager::new());
```

### 8.4.3 Resource Types com Generics

```wit
package example:generic-resources;

// Resource genérico com tipo parametrizado
resource pool<T> {
    constructor(max-size: u32);
    acquire: func() -> option<T>;
    release: func(item: T);
    size: func() -> u32;
    available: func() -> u32;
}

// Resource para conexões de banco de dados
resource db-pool {
    constructor(config: db-config, max-connections: u32);
    acquire: func() -> option<db-connection>;
    release: func(conn: db-connection);
    stats: func() -> pool-stats;
}

record db-config {
    host: string,
    port: u16,
    database: string,
    username: string,
    password: string,
}

resource db-connection {
    query: func(sql: string) -> result<query-result, string>;
    execute: func(sql: string) -> result<u64, string>;
    begin-transaction: func() -> result<transaction, string>;
}

resource transaction {
    commit: func() -> result<_, string>;
    rollback: func() -> result<_, string>;
}

record pool-stats {
    total: u32,
    active: u32,
    idle: u32,
    waiting: u32,
}

// Interface completa de banco de dados
interface database {
    create-pool: func(config: db-config, max-connections: u32) -> db-pool;
    execute-query: func(pool: db-pool, sql: string) -> result<query-result, string>;
    health-check: func(pool: db-pool) -> bool;
}
```

## 8.5 Streaming

O Component Model suporta streaming de dados através de interfaces de input e output streams, permitindo processamento eficiente de grandes volumes de dados.

### 8.5.1 Interfaces de Streaming

```wit
package example:streaming;

// Input stream para leitura
resource input-stream {
    read: func(len: u64) -> result<list<u8>, stream-error>;
    blocking-read: func(len: u64) -> result<list<u8>, stream-error>;
    skip: func(len: u64) -> result<u64, stream-error>;
    blocking-skip: func(len: u64) -> result<u64, stream-error>;
    subscribe: func() -> pollable;
}

// Output stream para escrita
resource output-stream {
    check-write: func() -> result<u64, stream-error>;
    write: func(contents: list<u8>) -> result<u64, stream-error>;
    blocking-write-and-flush: func(contents: list<u8>) -> result<_, stream-error>;
    flush: func() -> result<_, stream-error>;
    blocking-flush: func() -> result<_, stream-error>;
    subscribe: func() -> pollable;
}

// Erros de stream
variant stream-error {
    last-operation-failed(string),
    closed,
}

// Interface de streaming
interface streams {
    /// Ler dados de uma stream
    read-exactly: func(stream: input-stream, len: u64) -> result<list<u8>, stream-error>;
    
    /// Escrever todos os dados
    write-all: func(stream: output-stream, data: list<u8>) -> result<_, stream-error>;
    
    /// Transferir dados entre streams
    transfer: func(src: input-stream, dst: output-stream, len: u64) -> result<u64, stream-error>;
    
    /// Criar duplex stream (par input/output)
    create duplex-stream: func() -> tuple<input-stream, output-stream>;
}

// Pipeline de processamento
interface pipeline {
    /// Criar pipeline de processamento
    create-pipeline: func(stages: list<func(input-stream) -> output-stream>) -> duplex-stream;
    
    /// Processar dados através do pipeline
    process: func(pipeline: duplex-stream, input: input-stream) -> result<output-stream, string>;
}
```

### 8.5.2 Implementação de Streaming

```rust
use std::io::{Read, Write, BufRead, BufReader};
use std::collections::VecDeque;

// Buffer circular para streaming
struct CircularBuffer {
    buffer: Vec<u8>,
    head: usize,
    tail: usize,
    size: usize,
    capacity: usize,
}

impl CircularBuffer {
    fn new(capacity: usize) -> Self {
        Self {
            buffer: vec![0; capacity],
            head: 0,
            tail: 0,
            size: 0,
            capacity,
        }
    }
    
    fn write(&mut self, data: &[u8]) -> Result<usize, StreamError> {
        let available = self.capacity - self.size;
        let to_write = data.len().min(available);
        
        for i in 0..to_write {
            self.buffer[(self.tail + i) % self.capacity] = data[i];
        }
        
        self.tail = (self.tail + to_write) % self.capacity;
        self.size += to_write;
        
        Ok(to_write)
    }
    
    fn read(&mut self, buf: &mut [u8]) -> Result<usize, StreamError> {
        let to_read = buf.len().min(self.size);
        
        for i in 0..to_read {
            buf[i] = self.buffer[(self.head + i) % self.capacity];
        }
        
        self.head = (self.head + to_read) % self.capacity;
        self.size -= to_read;
        
        Ok(to_read)
    }
    
    fn available(&self) -> usize {
        self.size
    }
    
    fn capacity(&self) -> usize {
        self.capacity - self.size
    }
}

// Stream de entrada com buffering
struct InputStream {
    buffer: CircularBuffer,
    source: Box<dyn Read + Send>,
    eof: bool,
}

impl InputStream {
    fn new(source: Box<dyn Read + Send>) -> Self {
        Self {
            buffer: CircularBuffer::new(8192),
            source,
            eof: false,
        }
    }
    
    fn read(&mut self, len: usize) -> Result<Vec<u8>, StreamError> {
        let mut result = vec![0u8; len];
        let mut total_read = 0;
        
        // Primeiro, ler do buffer
        if self.buffer.available() > 0 {
            let read = self.buffer.read(&mut result)?;
            total_read += read;
        }
        
        // Se precisar de mais dados, ler da fonte
        while total_read < len && !self.eof {
            let remaining = len - total_read;
            let mut temp = vec![0u8; remaining.min(4096)];
            
            match self.source.read(&mut temp) {
                Ok(0) => {
                    self.eof = true;
                    break;
                }
                Ok(n) => {
                    if total_read + n <= len {
                        result[total_read..total_read + n].copy_from_slice(&temp[..n]);
                        total_read += n;
                    } else {
                        // Armazenar excesso no buffer
                        let excess = n - (len - total_read);
                        result[total_read..len].copy_from_slice(&temp[..len - total_read]);
                        self.buffer.write(&temp[len - total_read..n])?;
                        total_read = len;
                    }
                }
                Err(e) => {
                    return Err(StreamError::LastOperationFailed(e.to_string()));
                }
            }
        }
        
        result.truncate(total_read);
        Ok(result)
    }
    
    fn blocking_read(&mut self, len: usize) -> Result<Vec<u8>, StreamError> {
        self.read(len)
    }
    
    fn skip(&mut self, len: u64) -> Result<u64, StreamError> {
        let mut skipped = 0u64;
        let mut temp = vec![0u8; 4096];
        
        while skipped < len {
            let remaining = (len - skipped) as usize;
            let to_read = temp.len().min(remaining);
            
            match self.read(to_read) {
                Ok(0) => break,
                Ok(n) => skipped += n as u64,
                Err(e) => return Err(e),
            }
        }
        
        Ok(skipped)
    }
}

// Stream de saída com buffering e flush
struct OutputStream {
    buffer: CircularBuffer,
    sink: Box<dyn Write + Send>,
}

impl OutputStream {
    fn new(sink: Box<dyn Write + Send>) -> Self {
        Self {
            buffer: CircularBuffer::new(8192),
            sink,
        }
    }
    
    fn write(&mut self, data: &[u8]) -> Result<usize, StreamError> {
        self.buffer.write(data)
    }
    
    fn flush(&mut self) -> Result<(), StreamError> {
        let mut temp = vec![0u8; self.buffer.available()];
        
        while self.buffer.available() > 0 {
            let read = self.buffer.read(&mut temp)?;
            self.sink.write_all(&temp[..read])
                .map_err(|e| StreamError::LastOperationFailed(e.to_string()))?;
        }
        
        self.sink.flush()
            .map_err(|e| StreamError::LastOperationFailed(e.to_string()))?;
        
        Ok(())
    }
    
    fn blocking_write_and_flush(&mut self, data: &[u8]) -> Result<(), StreamError> {
        self.write(data)?;
        self.flush()
    }
}

// Duplex stream (par input/output)
struct DuplexStream {
    input: InputStream,
    output: OutputStream,
}

impl DuplexStream {
    fn new() -> Self {
        let (input_tx, input_rx) = std::sync::mpsc::channel();
        let (output_tx, output_rx) = std::sync::mpsc::channel();
        
        // Criar pipes internos
        // Na prática, isso seria implementado com pipes do sistema
        todo!("Implementar duplex stream")
    }
}
```

## 8.6 World Declarations

World declarations definem o contrato completo de um componente, especificando todas as imports e exports que ele requer e fornece.

### 8.6.1 Estrutura de Worlds

```wit
package example:worlds;

// World simples para uma biblioteca
default world library {
    import wasi:cli/environment@0.2.0;
    
    export calculate: func(input: list<f64>) -> f64;
    export validate: func(input: list<f64>) -> result<_, string>;
}

// World para um servidor HTTP
world http-server {
    import wasi:cli/stdin@0.2.0;
    import wasi:cli/stdout@0.2.0;
    import wasi:cli/stderr@0.2.0;
    import wasi:cli/environment@0.2.0;
    
    import wasi:clocks/monotonic-clock@0.2.0;
    import wasi:clocks/wall-clock@0.2.0;
    
    import wasi:filesystem/preopens@0.2.0;
    import wasi:filesystem/types@0.2.0;
    
    import wasi:io/error@0.2.0;
    import wasi:io/streams@0.2.0;
    import wasi:io/poll@0.2.0;
    
    import wasi:http/types@0.2.0;
    import wasi/http/outgoing-handler@0.2.0;
    
    export wasi:http/incoming-handler@0.2.0;
}

// World para um processador de dados
world data-processor {
    import wasi:cli/stdin@0.2.0;
    import wasi:cli/stdout@0.2.0;
    import wasi:cli/environment@0.2.0;
    
    import wasi:filesystem/types@0.2.0;
    
    import example:transformer@1.0.0;
    import example:validator@1.0.0;
    
    export process: func(input: string) -> result<string, string>;
    export batch-process: func(inputs: list<string>) -> list<result<string, string>>;
}

// World para um plugin
world plugin {
    import wasi:cli/environment@0.2.0;
    
    import example:config@1.0.0;
    import example:logger@1.0.0;
    
    export initialize: func(config: plugin-config) -> result<_, string>;
    export execute: func(input: plugin-input) -> result<plugin-output, string>;
    export shutdown: func() -> result<_, string>;
}

record plugin-config {
    name: string,
    version: string,
    settings: map<string, string>,
}

record plugin-input {
    command: string,
    data: option<string>,
    metadata: map<string, string>,
}

record plugin-output {
    success: bool,
    data: option<string>,
    errors: list<string>,
}
```

### 8.6.2 Composição de Worlds

```wit
package example:composition;

// World base com funcionalidades comuns
world base {
    import wasi:cli/environment@0.2.0;
    import wasi:cli/stdout@0.2.0;
    import wasi:cli/stderr@0.2.0;
}

// World estendido com filesystem
world with-filesystem {
    include base;
    
    import wasi:filesystem/preopens@0.2.0;
    import wasi:filesystem/types@0.2.0;
}

// World estendido com rede
world with-network {
    include base;
    
    import wasi:sockets/instance-network@0.2.0;
    import wasi:sockets/network@0.2.0;
}

// World composto com tudo
world full-stack {
    include with-filesystem;
    include with-network;
    
    import wasi:clocks/monotonic-clock@0.2.0;
    import wasi:clocks/wall-clock@0.2.0;
    
    import wasi:http/types@0.2.0;
    import wasi/http/outgoing-handler@0.2.0;
}

// World minimalista para edge
world minimal {
    import wasi:cli/environment@0.2.0;
    
    export handle: func(input: string) -> string;
}
```

## 8.7 wit-bindgen

wit-bindgen é a ferramenta que gera código de ligação entre linguagens e o Component Model Wasm.

### 8.7.1 Configuração e Uso

```bash
# Instalar wit-bindgen
cargo install wit-bindgen-cli

# Estrutura de projeto
my-component/
├── wit/
│   ├── world.wit
│   └── interfaces/
│       ├── calculator.wit
│       └── logger.wit
├── src/
│   └── lib.rs
├── Cargo.toml
└── wit-bindgen.toml

# Configurar wit-bindgen no Cargo.toml
cat > Cargo.toml << 'EOF'
[package]
name = "my-component"
version = "0.1.0"
edition = "2021"

[dependencies]
wit-bindgen = "0.16"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[lib]
crate-type = ["cdylib"]

[package.metadata.component]
package = "example:my-component"
version = "0.1.0"

[package.metadata.component.exports]
calculator = "src/calculator.rs"
logger = "src/logger.rs"
EOF
```

### 8.7.2 Definição de Interfaces

```wit
// wit/interfaces/calculator.wit
package example:calculator@0.1.0;

interface types {
    /// Operações matemáticas
    enum operation {
        add,
        subtract,
        multiply,
        divide,
        power,
        square-root,
    }
    
    /// Resultado de cálculo
    record calculation-result {
        value: f64,
        operation: operation,
        operands: list<f64>,
        timestamp: u64,
    }
    
    /// Erro de cálculo
    variant calculation-error {
        division-by-zero,
        invalid-operation(string),
        overflow,
        underflow,
        precision-loss(f64),
    }
}

interface calculator {
    use types.{operation, calculation-result, calculation-error};
    
    /// Calcular com dois operandos
    calculate-two: func(op: operation, a: f64, b: f64) -> result<calculation-result, calculation-error>;
    
    /// Calcular com lista de operandos
    calculate-list: func(op: operation, operands: list<f64>) -> result<calculation-result, calculation-error>;
    
    /// Calcular expressão complexa
    calculate-expression: func(expression: string) -> result<calculation-result, calculation-error>;
    
    /// Obter histórico de cálculos
    get-history: func(limit: u32) -> list<calculation-result>;
    
    /// Limpar histórico
    clear-history: func() -> unit;
}

// wit/interfaces/logger.wit
package example:logger@0.1.0;

interface logger {
    /// Níveis de log
    enum log-level {
        trace,
        debug,
        info,
        warn,
        error,
    }
    
    /// Registrar mensagem de log
    log: func(level: log-level, message: string, context: option<map<string, string>>) -> unit;
    
    /// Configurar nível mínimo de log
    set-level: func(level: log-level) -> unit;
    
    /// Obter nível atual
    get-level: func() -> log-level;
}

// wit/world.wit
package example:my-component@0.1.0;

default world calculator-app {
    import example:calculator@0.1.0;
    import example:logger@0.1.0;
    
    export run: func() -> result<_, string>;
    export calculate: func(op: string, operands: list<f64>) -> result<f64, string>;
}
```

### 8.7.3 Implementação em Rust

```rust
// src/lib.rs
wit_bindgen::generate!({
    world: "calculator-app",
    exports: {
        "example:my-component/run": MyComponent,
        "example:my-component/calculate": MyComponent,
    }
});

use std::collections::VecDeque;

// Estado global do componente
struct CalculatorState {
    history: VecDeque<CalculationResult>,
    max_history: usize,
    log_level: LogLevel,
}

impl CalculatorState {
    fn new() -> Self {
        Self {
            history: VecDeque::new(),
            max_history: 1000,
            log_level: LogLevel::Info,
        }
    }
    
    fn add_to_history(&mut self, result: CalculationResult) {
        if self.history.len() >= self.max_history {
            self.history.pop_front();
        }
        self.history.push_back(result);
    }
}

static mut STATE: Option<CalculatorState> = None;

fn get_state() -> &'static mut CalculatorState {
    unsafe {
        if STATE.is_none() {
            STATE = Some(CalculatorState::new());
        }
        STATE.as_mut().unwrap()
    }
}

// Implementação das exports
struct MyComponent;

impl exports::example::my_component::Guest for MyComponent {
    fn run() -> Result<(), String> {
        // Log de inicialização
        example::logger::log(
            LogLevel::Info,
            "Calculadora inicializada",
            None,
        );
        
        Ok(())
    }
    
    fn calculate(op: String, operands: Vec<f64>) -> Result<f64, String> {
        // Log da operação
        example::logger::log(
            LogLevel::Debug,
            &format!("Calculando: {} com {} operandos", op, operands.len()),
            None,
        );
        
        let operation = match op.as_str() {
            "add" => Operation::Add,
            "subtract" => Operation::Subtract,
            "multiply" => Operation::Multiply,
            "divide" => Operation::Divide,
            "power" => Operation::Power,
            "sqrt" => Operation::SquareRoot,
            _ => return Err(format!("Operação desconhecida: {}", op)),
        };
        
        let result = calculate_operation(operation, &operands)?;
        
        // Adicionar ao histórico
        let calc_result = CalculationResult {
            value: result,
            operation: operation.clone(),
            operands: operands.clone(),
            timestamp: get_timestamp(),
        };
        
        get_state().add_to_history(calc_result);
        
        Ok(result)
    }
}

fn calculate_operation(op: Operation, operands: &[f64]) -> Result<f64, String> {
    if operands.is_empty() {
        return Err("Nenhum operando fornecido".to_string());
    }
    
    match op {
        Operation::Add => {
            Ok(operands.iter().sum())
        }
        Operation::Subtract => {
            let mut result = operands[0];
            for &operand in &operands[1..] {
                result -= operand;
            }
            Ok(result)
        }
        Operation::Multiply => {
            Ok(operands.iter().product())
        }
        Operation::Divide => {
            let mut result = operands[0];
            for &operand in &operands[1..] {
                if operand == 0.0 {
                    return Err("Divisão por zero".to_string());
                }
                result /= operand;
            }
            Ok(result)
        }
        Operation::Power => {
            if operands.len() != 2 {
                return Err("Potência requer exatamente 2 operandos".to_string());
            }
            Ok(operands[0].powf(operands[1]))
        }
        Operation::SquareRoot => {
            if operands.len() != 1 {
                return Err("Raiz quadrada requer exatamente 1 operando".to_string());
            }
            if operands[0] < 0.0 {
                return Err("Raiz quadrada de número negativo".to_string());
            }
            Ok(operands[0].sqrt())
        }
    }
}

fn get_timestamp() -> u64 {
    // Em WASI, usar wasi:clocks/wall-clock
    0 // Placeholder
}

// Registrar o componente
wit_bindgen::export!({
    world: "calculator-app",
    exports: {
        "example:my-component/run": MyComponent,
        "example:my-component/calculate": MyComponent,
    }
});
```

## 8.8 Composição de Componentes

O Component Model permite compor múltiplos componentes em uma aplicação maior, definindo como eles se conectam.

### 8.8.1 Definição de Composição

```wit
package example:composition;

// Componente de cálculo
world calculator {
    export calculate: func(op: string, operands: list<f64>) -> result<f64, string>;
    export get-history: func(limit: u32) -> list<calculation-result>;
}

// Componente de log
world logger {
    export log: func(level: string, message: string) -> unit;
    export get-logs: func(level: string, limit: u32) -> list<log-entry>;
}

// Componente composto que combina calculadora e logger
world calculator-with-logging {
    include calculator;
    include logger;
    
    // Conectar logger à calculadora
    alias calculator::calculate as calc;
    alias logger::log as log;
    
    // Função que usa ambos
    export calculate-and-log: func(
        op: string, 
        operands: list<f64>
    ) -> result<f64, string>;
}

//world composition: composition.wit
package example:app@0.1.0;

// Definir componentes
world backend {
    import wasi:filesystem/types@0.2.0;
    import wasi:http/types@0.2.0;
    
    export handle-request: func(request: request) -> response;
}

world frontend {
    import example:ui@0.1.0;
    import example:state@0.1.0;
    
    export render: func(state: app-state) -> ui-component;
    export handle-event: func(event: ui-event) -> app-state;
}

// Compor frontend e backend
world full-app {
    include backend;
    include frontend;
    
    // Dados compartilhados
    import example:shared-state@0.1.0;
    
    // Conectar frontend ao backend
    alias backend::handle-request as api;
    alias frontend::render as render-ui;
    alias frontend::handle-event as handle-ui-event;
    
    export start: func(config: app-config) -> result<_, string>;
}
```

### 8.8.2 Composição com wasmtime

```rust
use wasmtime::component::{Component, Linker, ResourceTable};
use wasmtime::{Engine, Store, Result};

// Definir interfaces dos componentes
mod calculator {
    wasmtime::component::bindgen!({
        path: "wit/calculator/",
        world: "calculator",
    });
}

mod logger {
    wasmtime::component::bindgen!({
        path: "wit/logger/",
        world: "logger",
    });
}

mod app {
    wasmtime::component::bindgen!({
        path: "wit/app/",
        world: "calculator-with-logging",
    });
}

// Estado compartilhado
struct AppState {
    wasi: wasmtime_wasi::preview2::WasiCtx,
    table: ResourceTable,
    logs: Vec<(String, String)>,
}

impl wasmtime_wasi::preview2::WasiView for AppState {
    fn table(&mut self) -> &mut ResourceTable {
        &mut self.table
    }
    
    fn ctx(&mut self) -> &mut wasmtime_wasi::preview2::WasiCtx {
        &mut self.wasi
    }
}

// Implementar logger para o app
impl logger::Guest for AppState {
    fn log(level: String, message: String) {
        self.logs.push((level, message));
    }
    
    fn get_logs(level: String, limit: u32) -> Vec<logger::LogEntry> {
        self.logs.iter()
            .filter(|(l, _)| l == &level)
            .take(limit as usize)
            .map(|(level, message)| logger::LogEntry {
                level: level.clone(),
                message: message.clone(),
                timestamp: 0, // Placeholder
            })
            .collect()
    }
}

fn main() -> Result<()> {
    let engine = Engine::default();
    
    // Carregar componentes
    let calculator_component = Component::from_file(&engine, "calculator.wasm")?;
    let logger_component = Component::from_file(&engine, "logger.wasm")?;
    let app_component = Component::from_file(&engine, "app.wasm")?;
    
    // Criar linker
    let mut linker = Linker::<AppState>::new(&engine);
    
    // Adicionar WASI
    wasmtime_wasi::preview2::add_to_linker(&mut linker)?;
    
    // Adicionar imports do app
    app::Calculator::add_to_linker(&mut linker, |state| state)?;
    app::Logger::add_to_linker(&mut linker, |state| state)?;
    
    // Criar store
    let state = AppState {
        wasi: wasmtime_wasi::preview2::WasiCtxBuilder::new()
            .inherit_stdio()
            .build(),
        table: ResourceTable::new(),
        logs: Vec::new(),
    };
    
    let mut store = Store::new(&engine, state);
    
    // Instanciar app
    let (instance, _) = app::CalculatorWithLogging::instantiate(&mut store, &app_component, &linker)?;
    
    // Usar o app
    let result = instance.call_calculate_and_log(&mut store, "add", &[1.0, 2.0, 3.0])?;
    
    println!("Resultado: {:?}", result);
    
    // Verificar logs
    let logs = store.data().logs.clone();
    for (level, message) in &logs {
        println!("[{}] {}", level, message);
    }
    
    Ok(())
}
```

## 8.9 Interoperabilidade Entre Linguagens

Uma das principais vantagens do Component Model é permitir que componentes em diferentes linguagens se comuniquem de forma segura e eficiente.

### 8.9.1 Exemplos em Diferentes Linguagens

**Componente em Rust:**

```rust
// rust-component/src/lib.rs
wit_bindgen::generate!({
    world: "string-processor",
    exports: {
        "example:string-processor/process": Processor,
        "example:string-processor/validate": Validator,
    }
});

struct Processor;

impl exports::example::string_processor::Guest for Processor {
    fn process(input: String) -> String {
        // Processar string em Rust
        input.to_uppercase()
            .replace(" ", "_")
            .chars()
            .filter(|c| c.is_alphanumeric() || *c == '_')
            .collect()
    }
}

struct Validator;

impl exports::example::string_processor::Guest for Validator {
    fn validate(input: String) -> Result<(), String> {
        if input.is_empty() {
            return Err("String vazia".to_string());
        }
        
        if input.len() > 1000 {
            return Err("String muito longa".to_string());
        }
        
        if !input.chars().all(|c| c.is_alphanumeric() || c.is_whitespace()) {
            return Err("Caracteres inválidos".to_string());
        }
        
        Ok(())
    }
}
```

**Componente em AssemblyScript:**

```typescript
// assembly-component/assembly/index.ts
import { string_processor } from "./generated/bindings";

export class Processor implements string_processor.Processor {
    process(input: string): string {
        // Processar string em AssemblyScript
        return input
            .toUpperCase()
            .replace(/ /g, "_")
            .replace(/[^A-Z0-9_]/g, "");
    }
}

export class Validator implements string_processor.Validator {
    validate(input: string): Result<void, string> {
        if (input.length === 0) {
            return Result.Error("String vazia");
        }
        
        if (input.length > 1000) {
            return Result.Error("String muito longa");
        }
        
        for (let i = 0; i < input.length; i++) {
            const char = input.charCodeAt(i);
            if (
                !(char >= 48 && char <= 57) &&  // 0-9
                !(char >= 65 && char <= 90) &&  // A-Z
                !(char >= 97 && char <= 122) && // a-z
                char !== 32  // space
            ) {
                return Result.Error("Caracteres inválidos");
            }
        }
        
        return Result.Ok();
    }
}
```

**Componente em Go:**

```go
// go-component/main.go
package main

import (
    "fmt"
    "strings"
    "unicode"
)

// Implementar a interface string-processor
type Processor struct{}

func (p Processor) Process(input string) string {
    // Processar string em Go
    result := strings.ToUpper(input)
    result = strings.ReplaceAll(result, " ", "_")
    
    var filtered strings.Builder
    for _, r := range result {
        if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' {
            filtered.WriteRune(r)
        }
    }
    
    return filtered.String()
}

type Validator struct{}

func (v Validator) Validate(input string) error {
    if len(input) == 0 {
        return fmt.Errorf("string vazia")
    }
    
    if len(input) > 1000 {
        return fmt.Errorf("string muito longa")
    }
    
    for _, r := range input {
        if !unicode.IsLetter(r) && !unicode.IsDigit(r) && !unicode.IsSpace(r) {
            return fmt.Errorf("caracteres inválidos")
        }
    }
    
    return nil
}

func main() {
    // Registrar componentes
    RegisterProcessor(Processor{})
    RegisterValidator(Validator{})
}
```

### 8.9.2 Integração Cross-Language

```wit
// Definição da interface para cross-language
package example:cross-lang;

interface string-processing {
    /// Processador de strings
    resource processor {
        constructor();
        process: func(input: string) -> string;
        validate: func(input: string) -> result<_, string>;
    }
    
    /// Cache de resultados
    resource cache {
        constructor(max-size: u32);
        get: func(key: string) -> option<string>;
        set: func(key: string, value: string) -> unit;
        clear: func() -> unit;
    }
}

// Pipeline que combina componentes de diferentes linguagens
world cross-language-pipeline {
    import example:rust-processor@0.1.0;    // Rust para processamento pesado
    import example:go-cache@0.1.0;          // Go para cache
    import example:python-ml@0.1.0;         // Python para ML
    
    export process: func(input: string) -> result<string, string>;
    export analyze: func(text: string) -> analysis-result;
}

record analysis-result {
    sentiment: f64,
    keywords: list<string>,
    language: string,
    confidence: f64,
}
```

## 8.10 Implicações de Segurança

O Component Model introduz novas considerações de segurança que devem ser levadas em conta.

### 8.10.1 Segurança de Tipos

```wit
package example:security;

// Interfaces com tipos seguros
interface safe-api {
    /// Tipos seguros para dados sensíveis
    resource encrypted-data {
        constructor(data: list<u8>, key-ref: key-reference);
        decrypt: func(key: symmetric-key) -> result<list<u8>, crypto-error>;
        is-encrypted: func() -> bool;
    }
    
    resource symmetric-key {
        constructor(algorithm: key-algorithm);
        encrypt: func(data: list<u8>) -> encrypted-data;
        decrypt: func(data: encrypted-data) -> result<list<u8>, crypto-error>;
        destroy: func() -> unit;
    }
    
    resource key-reference {
        /// Apenas referência, não expõe a chave
        algorithm: func() -> key-algorithm;
        fingerprint: func() -> string;
    }
    
    enum key-algorithm {
        aes-256-gcm,
        chacha20-poly1305,
        xchacha20-poly1305,
    }
    
    variant crypto-error {
        invalid-key,
        decryption-failed,
        authentication-failed,
        algorithm-not-supported,
    }
}

// Controle de acesso baseado em capability
interface capability-based-api {
    /// Capability para operação específica
    resource read-capability {
        path: func() -> string;
        is-valid: func() -> bool;
        revoke: func() -> unit;
    }
    
    resource write-capability {
        path: func() -> string;
        is-valid: func() -> bool;
        revoke: func() -> unit;
    }
    
    /// Operações que requerem capabilities
    secure-read: func(cap: read-capability) -> result<list<u8>, string>;
    secure-write: func(cap: write-capability, data: list<u8>) -> result<_, string>;
    
    /// Conceder capabilities
    grant-read: func(path: string) -> read-capability;
    grant-write: func(path: string) -> write-capability;
}
```

### 8.10.2 Sandboxing de Componentes

```yaml
# Configuração de segurança para composição de componentes
apiVersion: component-security/v1
kind: ComponentPolicy
metadata:
  name: secure-composition
spec:
  # Políticas por componente
  components:
    - name: rust-processor
      runtime: wasmtime
      resources:
        memory: 256Mi
        cpu: 1.0
      permissions:
        filesystem:
          - path: /data/input
            mode: read-only
          - path: /data/output
            mode: write-only
        network: denied
        process: denied
        
    - name: go-cache
      runtime: wasmtime
      resources:
        memory: 128Mi
        cpu: 0.5
      permissions:
        filesystem:
          - path: /tmp/cache
            mode: read-write
        network: denied
        process: denied
        
    - name: python-ml
      runtime: wasmtime
      resources:
        memory: 512Mi
        cpu: 2.0
      permissions:
        filesystem:
          - path: /data/models
            mode: read-only
          - path: /tmp/ml
            mode: read-write
        network:
          allowed:
            - host: model-server.internal
              port: 8080
        process: denied
        
  # Políticas de comunicação
  communication:
    # Limitar tamanhos de mensagem
    max-message-size: 10Mi
    
    # Timeout para operações
    timeout: 30s
    
    # Auditoria de chamadas
    audit: true
    
  # Controle de fluxo de dados
  data-flow:
    # Componentes que podem acessar dados sensíveis
    sensitive-data:
      - rust-processor
      - go-cache
      
    # Componentes que podem exportar dados
    data-export:
      - rust-processor
```

### 8.10.3 Validação de Interfaces

```rust
use std::collections::HashMap;

// Validador de interfaces
struct InterfaceValidator {
    allowed_interfaces: HashMap<String, InterfaceDefinition>,
    security_policies: Vec<SecurityPolicy>,
}

#[derive(Debug, Clone)]
struct InterfaceDefinition {
    name: String,
    version: String,
    imports: Vec<String>,
    exports: Vec<String>,
    resources: Vec<ResourceDefinition>,
}

#[derive(Debug, Clone)]
struct ResourceDefinition {
    name: String,
    methods: Vec<MethodDefinition>,
    capabilities: Vec<String>,
}

#[derive(Debug, Clone)]
struct MethodDefinition {
    name: String,
    params: Vec<ParamDefinition>,
    return_type: String,
    required_capabilities: Vec<String>,
}

#[derive(Debug, Clone)]
struct ParamDefinition {
    name: String,
    type_name: String,
    constraints: Vec<Constraint>,
}

#[derive(Debug, Clone)]
enum Constraint {
    MaxLength(usize),
    MinLength(usize),
    Pattern(String),
    Range(f64, f64),
    NotEmpty,
}

#[derive(Debug, Clone)]
struct SecurityPolicy {
    name: String,
    rules: Vec<SecurityRule>,
}

#[derive(Debug, Clone)]
enum SecurityRule {
    RequireCapability(String),
    DenyCapability(String),
    MaxResourceUsage(ResourceType, f64),
    AllowNetwork(Vec<String>),
    DenyNetwork,
    AllowFilesystem(Vec<String>),
    DenyFilesystem,
}

#[derive(Debug, Clone)]
enum ResourceType {
    Memory,
    Cpu,
    Storage,
    Bandwidth,
}

impl InterfaceValidator {
    fn new() -> Self {
        Self {
            allowed_interfaces: HashMap::new(),
            security_policies: Vec::new(),
        }
    }
    
    fn register_interface(&mut self, interface: InterfaceDefinition) {
        self.allowed_interfaces.insert(
            interface.name.clone(),
            interface,
        );
    }
    
    fn add_policy(&mut self, policy: SecurityPolicy) {
        self.security_policies.push(policy);
    }
    
    fn validate_interface(&self, name: &str) -> Result<(), ValidationError> {
        let interface = self.allowed_interfaces.get(name)
            .ok_or_else(|| ValidationError::InterfaceNotFound(name.to_string()))?;
        
        // Validar imports
        for import in &interface.imports {
            if !self.allowed_interfaces.contains_key(import) {
                return Err(ValidationError::ImportNotFound(import.clone()));
            }
        }
        
        // Validar exports
        for export in &interface.exports {
            // Verificar se export não viola políticas
            for policy in &self.security_policies {
                for rule in &policy.rules {
                    match rule {
                        SecurityRule::DenyCapability(cap) => {
                            if export.contains(cap) {
                                return Err(ValidationError::CapabilityDenied(
                                    export.clone(),
                                    cap.clone(),
                                ));
                            }
                        }
                        _ => {}
                    }
                }
            }
        }
        
        // Validar resources
        for resource in &interface.resources {
            for method in &resource.methods {
                self.validate_method(method)?;
            }
        }
        
        Ok(())
    }
    
    fn validate_method(&self, method: &MethodDefinition) -> Result<(), ValidationError> {
        // Validar parâmetros
        for param in &method.params {
            for constraint in &param.constraints {
                match constraint {
                    Constraint::MaxLength(max) => {
                        if param.type_name == "string" {
                            // Validação será feita em runtime
                        }
                    }
                    Constraint::Pattern(pattern) => {
                        // Validação regex será feita em runtime
                    }
                    _ => {}
                }
            }
        }
        
        // Validar capacidades requeridas
        for cap in &method.required_capabilities {
            // Verificar se a política permite essa capacidade
            let mut allowed = false;
            
            for policy in &self.security_policies {
                for rule in &policy.rules {
                    if let SecurityRule::RequireCapability(required) = rule {
                        if required == cap {
                            allowed = true;
                            break;
                        }
                    }
                }
                if allowed {
                    break;
                }
            }
            
            if !allowed {
                return Err(ValidationError::CapabilityRequired(
                    method.name.clone(),
                    cap.clone(),
                ));
            }
        }
        
        Ok(())
    }
    
    fn validate_call(&self, interface: &str, method: &str, args: &[Value]) -> Result<(), CallError> {
        let iface = self.allowed_interfaces.get(interface)
            .ok_or_else(|| CallError::InterfaceNotFound(interface.to_string()))?;
        
        // Encontrar método
        let method_def = iface.resources.iter()
            .flat_map(|r| &r.methods)
            .find(|m| m.name == method)
            .ok_or_else(|| CallError::MethodNotFound(method.to_string()))?;
        
        // Validar argumentos
        if args.len() != method_def.params.len() {
            return Err(CallError::ArgumentCountMismatch {
                expected: method_def.params.len(),
                actual: args.len(),
            });
        }
        
        for (arg, param) in args.iter().zip(&method_def.params) {
            validate_value(arg, &param.type_name, &param.constraints)?;
        }
        
        Ok(())
    }
}

fn validate_value(value: &Value, expected_type: &str, constraints: &[Constraint]) -> Result<(), CallError> {
    match (value, expected_type) {
        (Value::String(s), "string") => {
            for constraint in constraints {
                match constraint {
                    Constraint::MaxLength(max) => {
                        if s.len() > *max {
                            return Err(CallError::ConstraintViolation(
                                format!("String excede tamanho máximo: {} > {}", s.len(), max)
                            ));
                        }
                    }
                    Constraint::MinLength(min) => {
                        if s.len() < *min {
                            return Err(CallError::ConstraintViolation(
                                format!("String menor que tamanho mínimo: {} < {}", s.len(), min)
                            ));
                        }
                    }
                    Constraint::NotEmpty => {
                        if s.is_empty() {
                            return Err(CallError::ConstraintViolation(
                                "String não pode ser vazia".to_string()
                            ));
                        }
                    }
                    _ => {}
                }
            }
        }
        (Value::I32(n), "i32") | (Value::I64(n), "i64") => {
            for constraint in constraints {
                if let Constraint::Range(min, max) = constraint {
                    let value = *n as f64;
                    if value < *min || value > *max {
                        return Err(CallError::ConstraintViolation(
                            format!("Valor fora do range: {} not in [{}, {}]", value, min, max)
                        ));
                    }
                }
            }
        }
        _ => {
            return Err(CallError::TypeMismatch {
                expected: expected_type.to_string(),
                actual: format!("{:?}", value),
            });
        }
    }
    
    Ok(())
}

#[derive(Debug)]
enum ValidationError {
    InterfaceNotFound(String),
    ImportNotFound(String),
    CapabilityDenied(String, String),
    CapabilityRequired(String, String),
    InvalidConstraint(String),
}

#[derive(Debug)]
enum CallError {
    InterfaceNotFound(String),
    MethodNotFound(String),
    ArgumentCountMismatch { expected: usize, actual: usize },
    TypeMismatch { expected: String, actual: String },
    ConstraintViolation(String),
    PermissionDenied(String),
}

#[derive(Debug, Clone)]
enum Value {
    Bool(bool),
    I32(i32),
    I64(i64),
    F32(f32),
    F64(f64),
    String(String),
    List(Vec<Value>),
    Record(HashMap<String, Value>),
    Option(Option<Box<Value>>),
    Result(Result<Box<Value>, Box<Value>>),
}
```

## 8.11 Exemplo Completo

Vamos criar um exemplo completo de aplicação usando o Component Model com múltiplos componentes em diferentes linguagens.

### 8.11.1 Arquitetura do Exemplo

```
┌─────────────────────────────────────────────────────────┐
│                    Aplicação Completa                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Parser    │    │  Validator  │    │  Formatter  │ │
│  │   (Rust)    │───▶│  (Go)       │───▶│  (Python)   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                  │                  │         │
│         └──────────────────┼──────────────────┘         │
│                            │                            │
│                    ┌───────▼───────┐                    │
│                    │    Logger     │                    │
│                    │  (Assembly)   │                    │
│                    └───────────────┘                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 8.11.2 Definições de Interfaces

```wit
// wit/parser.wit
package example:parser@0.1.0;

interface types {
    record parsed-document {
        title: string,
        content: string,
        metadata: map<string, string>,
        timestamp: u64,
    }
    
    variant parse-error {
        syntax-error(string),
        invalid-encoding,
        too-large(u64),
    }
}

interface parser {
    use types.{parsed-document, parse-error};
    
    parse-document: func(content: list<u8>, format: string) -> result<parsed-document, parse-error>;
    supported-formats: func() -> list<string>;
}

// wit/validator.wit
package example:validator@0.1.0;

interface types {
    record validation-result {
        valid: bool,
        errors: list<string>,
        warnings: list<string>,
        score: f64,
    }
    
    enum severity {
        error,
        warning,
        info,
    }
    
    record validation-rule {
        name: string,
        pattern: string,
        severity: severity,
        description: string,
    }
}

interface validator {
    use types.{validation-result, validation-rule};
    
    validate: func(content: string, rules: list<validation-rule>) -> validation-result;
    get-default-rules: func() -> list<validation-rule>;
}

// wit/formatter.wit
package example:formatter@0.1.0;

interface types {
    enum output-format {
        html,
        markdown,
        json,
        pdf,
    }
    
    record formatted-document {
        content: string,
        format: output-format,
        size: u64,
    }
}

interface formatter {
    use types.{formatted-document, output-format};
    
    format: func(content: string, format: output-format) -> formatted-document;
    supported-formats: func() -> list<output-format>;
}

// wit/logger.wit
package example:logger@0.1.0;

interface logger {
    enum log-level {
        trace,
        debug,
        info,
        warn,
        error,
    }
    
    log: func(level: log-level, message: string, context: option<map<string, string>>) -> unit;
    set-level: func(level: log-level) -> unit;
    get-logs: func(level: log-level, limit: u32) -> list<log-entry>;
}

record log-entry {
    level: log-level,
    message: string,
    context: option<map<string, string>>,
    timestamp: u64,
}

// wit/pipeline.wit
package example:pipeline@0.1.0;

import example:parser@0.1.0;
import example:validator@0.1.0;
import example:formatter@0.1.0;
import example:logger@0.1.0;

default world document-pipeline {
    import parser;
    import validator;
    import formatter;
    import logger;
    
    export process-document: func(
        content: list<u8>,
        input-format: string,
        output-format: formatter.output-format,
        validation-rules: list<validator.validation-rule>,
    ) -> result<formatter.formatted-document, string>;
    
    export get-pipeline-info: func() -> pipeline-info;
}

record pipeline-info {
    name: string,
    version: string,
    stages: list<string>,
    supported-inputs: list<string>,
    supported-outputs: list<formatter.output-format>,
}
```

### 8.11.3 Implementações

**Parser em Rust:**

```rust
// rust-parser/src/lib.rs
wit_bindgen::generate!({
    world: "parser",
    exports: {
        "example:parser/parse-document": ParserImpl,
        "example:parser/supported-formats": ParserImpl,
    }
});

struct ParserImpl;

impl exports::example::parser::Guest for ParserImpl {
    fn parse_document(content: Vec<u8>, format: String) -> Result<ParsedDocument, ParseError> {
        match format.as_str() {
            "markdown" => parse_markdown(&content),
            "html" => parse_html(&content),
            "json" => parse_json(&content),
            _ => Err(ParseError::SyntaxError(format!("Formato não suportado: {}", format))),
        }
    }
    
    fn supported_formats() -> Vec<String> {
        vec!["markdown".to_string(), "html".to_string(), "json".to_string()]
    }
}

fn parse_markdown(content: &[u8]) -> Result<ParsedDocument, ParseError> {
    let text = String::from_utf8(content.to_vec())
        .map_err(|_| ParseError::InvalidEncoding)?;
    
    // Parseamento simples de markdown
    let mut title = String::new();
    let mut metadata = HashMap::new();
    
    for line in text.lines() {
        if line.starts_with("# ") {
            title = line[2..].to_string();
        } else if let Some(pos) = line.find(':') {
            let key = line[..pos].trim().to_string();
            let value = line[pos+1..].trim().to_string();
            metadata.insert(key, value);
        }
    }
    
    Ok(ParsedDocument {
        title,
        content: text,
        metadata,
        timestamp: get_timestamp(),
    })
}

fn parse_html(content: &[u8]) -> Result<ParsedDocument, ParseError> {
    // Implementação de parse HTML
    todo!("Implementar parse HTML")
}

fn parse_json(content: &[u8]) -> Result<ParsedDocument, ParseError> {
    let text = String::from_utf8(content.to_vec())
        .map_err(|_| ParseError::InvalidEncoding)?;
    
    let json: serde_json::Value = serde_json::from_str(&text)
        .map_err(|e| ParseError::SyntaxError(e.to_string()))?;
    
    let title = json["title"].as_str().unwrap_or("").to_string();
    let content = json["content"].as_str().unwrap_or("").to_string();
    
    let mut metadata = HashMap::new();
    if let Some(obj) = json["metadata"].as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                metadata.insert(k.clone(), s.to_string());
            }
        }
    }
    
    Ok(ParsedDocument {
        title,
        content,
        metadata,
        timestamp: get_timestamp(),
    })
}

fn get_timestamp() -> u64 {
    // Em WASI, usar wasi:clocks/wall-clock
    0
}
```

**Validator em Go:**

```go
// go-validator/main.go
package main

import (
    "fmt"
    "regexp"
    "strings"
)

// Estruturas de dados
type ValidationResult struct {
    Valid    bool     `json:"valid"`
    Errors   []string `json:"errors"`
    Warnings []string `json:"warnings"`
    Score    float64  `json:"score"`
}

type ValidationRule struct {
    Name        string `json:"name"`
    Pattern     string `json:"pattern"`
    Severity    string `json:"severity"`
    Description string `json:"description"`
}

// Implementação do validador
type Validator struct{}

func (v Validator) Validate(content string, rules []ValidationRule) ValidationResult {
    result := ValidationResult{
        Valid:    true,
        Errors:   []string{},
        Warnings: []string{},
        Score:    1.0,
    }

    for _, rule := range rules {
        matched, err := regexp.MatchString(rule.Pattern, content)
        if err != nil {
            result.Errors = append(result.Errors, fmt.Sprintf("Erro na regra %s: %v", rule.Name, err))
            result.Valid = false
            result.Score -= 0.1
            continue
        }

        if !matched {
            switch rule.Severity {
            case "error":
                result.Errors = append(result.Errors, rule.Description)
                result.Valid = false
                result.Score -= 0.2
            case "warning":
                result.Warnings = append(result.Warnings, rule.Description)
                result.Score -= 0.05
            case "info":
                // Apenas informativo
            }
        }
    }

    // Garantir que score está entre 0 e 1
    if result.Score < 0 {
        result.Score = 0
    }

    return result
}

func (v Validator) GetDefaultRules() []ValidationRule {
    return []ValidationRule{
        {
            Name:        "no-empty-content",
            Pattern:     ".+",
            Severity:    "error",
            Description: "Conteúdo não pode ser vazio",
        },
        {
            Name:        "max-length",
            Pattern:     "^.{0,10000}$",
            Severity:    "error",
            Description: "Conteúdo excede tamanho máximo",
        },
        {
            Name:        "no-script-tags",
            Pattern:     "(?i)<script",
            Severity:    "warning",
            Description: "Conteúdo contém tags de script",
        },
        {
            Name:        "proper-encoding",
            Pattern:     "^[\\x00-\\x7F\\xC0-\\xFF]+$",
            Severity:    "error",
            Description: "Encoding inválido detectado",
        },
    }
}

func main() {
    // Registrar componente
    RegisterValidator(Validator{})
}
```

**Formatter em Python:**

```python
# python-formatter/formatter.py
import json
import html
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class OutputFormat(Enum):
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
    PDF = "pdf"

@dataclass
class FormattedDocument:
    content: str
    format: OutputFormat
    size: int

class Formatter:
    def format(self, content: str, format: OutputFormat) -> FormattedDocument:
        if format == OutputFormat.HTML:
            return self._format_html(content)
        elif format == OutputFormat.MARKDOWN:
            return self._format_markdown(content)
        elif format == OutputFormat.JSON:
            return self._format_json(content)
        elif format == OutputFormat.PDF:
            return self._format_pdf(content)
        else:
            raise ValueError(f"Formato não suportado: {format}")
    
    def _format_html(self, content: str) -> FormattedDocument:
        # Converter para HTML
        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documento Processado</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
        .content {{ max-width: 800px; margin: 0 auto; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="content">
        {html.escape(content)}
    </div>
</body>
</html>"""
        
        return FormattedDocument(
            content=html_content,
            format=OutputFormat.HTML,
            size=len(html_content.encode('utf-8'))
        )
    
    def _format_markdown(self, content: str) -> FormattedDocument:
        # Processar para Markdown
        lines = content.split('\n')
        md_lines = []
        
        for line in lines:
            # Detectar headers
            if line.startswith('#'):
                md_lines.append(f"\n{line}\n")
            elif line.startswith('-') or line.startswith('*'):
                md_lines.append(line)
            elif line.strip():
                md_lines.append(f"{line}\n")
        
        md_content = '\n'.join(md_lines)
        
        return FormattedDocument(
            content=md_content,
            format=OutputFormat.MARKDOWN,
            size=len(md_content.encode('utf-8'))
        )
    
    def _format_json(self, content: str) -> FormattedDocument:
        # Estruturar como JSON
        data = {
            "document": {
                "content": content,
                "metadata": {
                    "format": "text",
                    "encoding": "utf-8",
                    "processed": True
                }
            }
        }
        
        json_content = json.dumps(data, indent=2, ensure_ascii=False)
        
        return FormattedDocument(
            content=json_content,
            format=OutputFormat.JSON,
            size=len(json_content.encode('utf-8'))
        )
    
    def _format_pdf(self, content: str) -> FormattedDocument:
        # Para PDF, normalmente usaríamos uma biblioteca como reportlab
        # Aqui retornamos uma representação simples
        pdf_content = f"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000266 00000 n \ntrailer<</Size 5/Root 1 0 R>>\nstartxref\n345\n%%EOF"
        
        return FormattedDocument(
            content=pdf_content,
            format=OutputFormat.PDF,
            size=len(pdf_content.encode('utf-8'))
        )
    
    def supported_formats(self) -> List[OutputFormat]:
        return list(OutputFormat)

# Registrar componente
formatter = Formatter()
```

### 8.11.4 Composição Final

```rust
// pipeline/src/main.rs
use wasmtime::component::{Component, Linker, ResourceTable};
use wasmtime::{Engine, Store, Result};

// Bindgen para o pipeline completo
wasmtime::component::bindgen!({
    path: "wit/pipeline/",
    world: "document-pipeline",
});

struct PipelineState {
    wasi: wasmtime_wasi::preview2::WasiCtx,
    table: ResourceTable,
}

impl wasmtime_wasi::preview2::WasiView for PipelineState {
    fn table(&mut self) -> &mut ResourceTable {
        &mut self.table
    }
    
    fn ctx(&mut self) -> &mut wasmtime_wasi::preview2::WasiCtx {
        &mut self.wasi
    }
}

fn main() -> Result<()> {
    let engine = Engine::default();
    
    // Carregar componentes
    let parser_component = Component::from_file(&engine, "parser.wasm")?;
    let validator_component = Component::from_file(&engine, "validator.wasm")?;
    let formatter_component = Component::from_file(&engine, "formatter.wasm")?;
    let logger_component = Component::from_file(&engine, "logger.wasm")?;
    
    // Criar pipeline composto
    let pipeline_component = Component::from_file(&engine, "pipeline.wasm")?;
    
    // Configurar linker
    let mut linker = Linker::<PipelineState>::new(&engine);
    
    // Adicionar WASI
    wasmtime_wasi::preview2::add_to_linker(&mut linker)?;
    
    // Adicionar imports
    document_pipeline::Example::Parser::add_to_linker(&mut linker, |state| state)?;
    document_pipeline::Example::Validator::add_to_linker(&mut linker, |state| state)?;
    document_pipeline::Example::Formatter::add_to_linker(&mut linker, |state| state)?;
    document_pipeline::Example::Logger::add_to_linker(&mut linker, |state| state)?;
    
    // Criar store
    let state = PipelineState {
        wasi: wasmtime_wasi::preview2::WasiCtxBuilder::new()
            .inherit_stdio()
            .build(),
        table: ResourceTable::new(),
    };
    
    let mut store = Store::new(&engine, state);
    
    // Instanciar pipeline
    let (instance, _) = DocumentPipeline::instantiate(&mut store, &pipeline_component, &linker)?;
    
    // Documento de teste
    let document = r#"# Meu Documento

author: João Silva
date: 2024-01-15
version: 1.0

Este é um documento de teste para o pipeline de processamento.
Contém texto simples que será processado por múltiplos componentes.
"#;
    
    // Processar documento
    let result = instance.call_process_document(
        &mut store,
        document.as_bytes(),
        "markdown",
        &OutputFormat::Html,
        &[],  // Usar regras padrão
    )?;
    
    match result {
        Ok(formatted) => {
            println!("Documento processado com sucesso!");
            println!("Formato: {:?}", formatted.format);
            println!("Tamanho: {} bytes", formatted.size);
            println!(" Conteúdo:");
            println!("{}", formatted.content);
        }
        Err(e) => {
            eprintln!("Erro ao processar documento: {}", e);
        }
    }
    
    // Obter informações do pipeline
    let info = instance.call_get_pipeline_info(&mut store)?;
    println!("\nInformações do Pipeline:");
    println!("Nome: {}", info.name);
    println!("Versão: {}", info.version);
    println!("Estágios: {:?}", info.stages);
    
    Ok(())
}
```

### 8.11.5 Build e Execução

```bash
# Estrutura do projeto
document-pipeline/
├── wit/
│   ├── parser.wit
│   ├── validator.wit
│   ├── formatter.wit
│   ├── logger.wit
│   └── pipeline.wit
├── rust-parser/
│   ├── Cargo.toml
│   └── src/lib.rs
├── go-validator/
│   ├── go.mod
│   └── main.go
├── python-formatter/
│   ├── requirements.txt
│   └── formatter.py
├── pipeline/
│   ├── Cargo.toml
│   └── src/main.rs
└── Makefile

# Makefile
cat > Makefile << 'EOF'
.PHONY: all build clean test

all: build

build: build-parser build-validator build-formatter build-pipeline

build-parser:
	cd rust-parser && cargo build --target wasm32-wasi --release
	mv rust-parser/target/wasm32-wasi/release/rust_parser.wasm parser.wasm

build-validator:
	cd go-validator && GOOS=wasip1 GOARCH=wasm go build -o validator.wasm .

build-formatter:
	cd python-formatter && componentize-py formatter.wasm formatter.py

build-pipeline:
	cd pipeline && cargo build --release

clean:
	rm -f *.wasm
	cd rust-parser && cargo clean
	cd go-validator && rm -f validator.wasm
	cd pipeline && cargo clean

test: build
	cargo test --manifest-path pipeline/Cargo.toml

run: build
	./pipeline/target/release/pipeline
EOF

# Compilar e executar
make build
make run
```

## 8.12 Considerações Finais

O Component Model representa uma evolução fundamental do WebAssembly, transformando-o de uma plataforma de execução isolada para um ecossistema de composição segura de componentes. As principais vantagens incluem:

1. **Interoperabilidade segura**: Componentes em diferentes linguagens podem se comunicar de forma segura e eficiente.

2. **Tipos ricos**: O sistema de tipos vai muito além dos tipos numéricos básicos, suportando estruturas complexas, variantes, resources e streaming.

3. **Composição flexível**: Componentes podem ser combinados de diferentes maneiras para criar aplicações complexas.

4. **Segurança por design**: O modelo impõe isolamento e valida interfaces em tempo de composição.

5. **Ecossistema em crescimento**: Ferramentas como wit-bindgen e runtimes como wasmtime estão amadurecendo rapidamente.

O Component Model está no início de sua adoção, mas já está sendo utilizado em produção em vários cenários, incluindo edge computing, serverless e plugins. À medida que o ecossistema amadurece, esperamos ver uma adoção ainda maior e novos casos de uso inovadores.

No próximo capítulo, exploraremos a segurança de memória em WebAssembly, incluindo técnicas de detecção e prevenção de bugs de memória.
