# Capítulo 17: Boas Práticas e Checklist

## Introdução

Desenvolver aplicações WebAssembly seguras requer mais do que apenas conhecimento técnico — exige disciplina, processos bem definidos e adesão a boas práticas comprovadas. Este capítulo apresenta um guia abrangente de boas práticas, anti-patterns a evitar, árvores de decisão para escolhas técnicas e templates completos para projetos reais.

O WebAssembly traz benefícios significativos em termos de performance, portabilidade e segurança, mas esses benefícios só se realizam quando a tecnologia é aplicada corretamente. Erros de configuração, uso inadequado de APIs ou negligência em testes podem criar vulnerabilidades críticas que comprometem toda a aplicação.

Vamos explorar anti-patterns comuns, checklists de segurança, árvores de decisão para escolher runtimes e linguagens, templates completos para projetos Rust e C++, pipelines CI/CD, monitoramento e otimização de performance.

---

## 17.1 Anti-Patterns para Wasm

### 20+ Anti-Patterns Comuns

#### 1. Memória Não Inicializada

```rust
// ANTI-PATTERN: Acessar memória não inicializada
#[no_mangle]
pub extern "C" fn process_data(ptr: *mut u8, len: usize) {
    let slice = unsafe { std::slice::from_raw_parts_mut(ptr, len) };
    // PROBLEMA: slice pode conter dados não inicializados
    // Isso pode vazar dados sensíveis
    for byte in slice.iter_mut() {
        *byte = *byte; // No-op, mas mantém dados antigos
    }
}

// BOA PRÁTICA: Inicializar memória antes do uso
#[no_mangle]
pub extern "C" fn process_data_safe(ptr: *mut u8, len: usize) {
    let slice = unsafe { std::slice::from_raw_parts_mut(ptr, len) };
    // Solução 1: Zero-fill
    for byte in slice.iter_mut() {
        *byte = 0;
    }
    // Solução 2: Usar memória segura
    // use zeroize::Zeroize;
    // slice.zeroize();
}
```

#### 2. Overflow de Memória

```rust
// ANTI-PATTERN: Não verificar limites de memória
#[no_mangle]
pub extern "C" fn allocate_buffer(size: usize) -> *mut u8 {
    // PROBLEMA: Sem verificação de overflow
    let mut buffer = Vec::with_capacity(size);
    buffer.resize(size, 0);
    buffer.as_mut_ptr()
}

// BOA PRÁTICA: Verificar limites e usar checked arithmetic
#[no_mangle]
pub extern "C" fn allocate_buffer_safe(size: usize) -> *mut u8 {
    // Verificar se size é razoável
    const MAX_SIZE: usize = 1024 * 1024 * 100; // 100MB
    if size > MAX_SIZE {
        return std::ptr::null_mut();
    }

    // Usar checked multiplication
    let layout = match std::alloc::Layout::from_size_align(size, 8) {
        Ok(layout) => layout,
        Err(_) => return std::ptr::null_mut(),
    };

    unsafe {
        let ptr = std::alloc::alloc(layout);
        if ptr.is_null() {
            return std::ptr::null_mut();
        }
        // Inicializar memória
        std::ptr::write_bytes(ptr, 0, size);
        ptr
    }
}
```

#### 3. Uso Indiscriminado de unsafe

```rust
// ANTI-PATTERN: unsafe sem necessidade
#[no_mangle]
pub extern "C" fn process_string(input: *const u8, len: usize) -> *mut u8 {
    // PROBLEMA: unsafe desnecessário e inseguro
    unsafe {
        let slice = std::slice::from_raw_parts(input, len);
        let string = std::str::from_utf8_unchecked(slice);
        let result = string.to_uppercase();
        let result_ptr = result.as_ptr();
        std::mem::forget(result); // Memory leak!
        result_ptr
    }
}

// BOA PRÁTICA: Minimizar unsafe, usar abstrações seguras
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

#[no_mangle]
pub extern "C" fn process_string_safe(input: *const c_char) -> *mut c_char {
    // Usar CStr para validação segura
    let c_str = unsafe {
        if input.is_null() {
            return std::ptr::null_mut();
        }
        match CStr::from_ptr(input).to_str() {
            Ok(s) => s,
            Err(_) => return std::ptr::null_mut(),
        }
    };

    let result = c_str.to_uppercase();
    match CString::new(result) {
        Ok(c_string) => c_string.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
```

#### 4. Tratamento de Erros Inadequado

```rust
// ANTI-PATTERN: Ignorar erros ou usar unwrap
#[no_mangle]
pub extern "C" fn read_config(path: *const u8) -> *mut Config {
    let c_str = unsafe { CStr::from_ptr(path as *const c_char) };
    let path_str = c_str.to_str().unwrap(); // PROBLEMA: unwrap pode panicar

    let config = std::fs::read_to_string(path_str).unwrap(); // PROBLEMA: panic em production

    let parsed: Config = serde_json::from_str(&config).unwrap(); // PROBLEMA: mais um panic

    Box::into_raw(Box::new(parsed))
}

// BOA PRÁTICA: Tratar erros adequadamente
#[no_mangle]
pub extern "C" fn read_config_safe(path: *const c_char) -> *mut Config {
    // Validar input
    if path.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(path) };
    let path_str = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let config = match std::fs::read_to_string(path_str) {
        Ok(content) => content,
        Err(_) => return std::ptr::null_mut(),
    };

    let parsed: Config = match serde_json::from_str(&config) {
        Ok(c) => c,
        Err(_) => return std::ptr::null_mut(),
    };

    Box::into_raw(Box::new(parsed))
}
```

#### 5. Vazamento de Memória

```rust
// ANTI-PATTERN: Esquecer de liberar memória
#[no_mangle]
pub extern "C" fn create_string(len: usize) -> *mut u8 {
    let mut buffer = Vec::with_capacity(len);
    buffer.resize(len, 0);
    // PROBLEMA: Vec não é liberado quando função retorna
    buffer.as_mut_ptr()
}

// BOA PRÁTICA: Fornecer função de liberação
#[no_mangle]
pub extern "C" fn create_string_safe(len: usize) -> *mut u8 {
    let mut buffer = Vec::with_capacity(len);
    buffer.resize(len, 0);
    let ptr = buffer.as_mut_ptr();
    std::mem::forget(buffer); // Prevenir drop automático
    ptr
}

#[no_mangle]
pub extern "C" fn free_string(ptr: *mut u8, len: usize) {
    if !ptr.is_null() {
        unsafe {
            // Recriar Vec para liberar memória
            let _ = Vec::from_raw_parts(ptr, len, len);
        }
    }
}
```

#### 6. Race Conditions

```rust
// ANTI-PATTERN: Estado compartilhado sem sincronização
use std::sync::atomic::{AtomicUsize, Ordering};

static mut COUNTER: usize = 0; // PROBLEMA: Acesso inseguro

#[no_mangle]
pub extern "C" fn increment_counter() -> usize {
    unsafe {
        COUNTER += 1; // PROBLEMA: Race condition
        COUNTER
    }
}

// BOA PRÁTICA: Usar atomics ou mutex
static COUNTER: AtomicUsize = AtomicUsize::new(0);

#[no_mangle]
pub extern "C" fn increment_counter_safe() -> usize {
    COUNTER.fetch_add(1, Ordering::SeqCst)
}
```

#### 7. Entrada Não Validada

```rust
// ANTI-PATTERN: Confiança cega em dados externos
#[no_mangle]
pub extern "C" fn process_input(ptr: *const u8, len: usize) -> i32 {
    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
    // PROBLEMA: Não valida se slice contém dados numéricos
    let value = std::str::from_utf8(slice)
        .unwrap()
        .parse::<i32>()
        .unwrap(); // Pode panicar com input malicioso
    value * 2
}

// BOA PRÁTICA: Validar toda entrada externa
#[no_mangle]
pub extern "C" fn process_input_safe(ptr: *const u8, len: usize) -> i32 {
    if ptr.is_null() || len == 0 {
        return -1;
    }

    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };

    let string = match std::str::from_utf8(slice) {
        Ok(s) => s,
        Err(_) => return -1,
    };

    let value = match string.parse::<i32>() {
        Ok(v) => v,
        Err(_) => return -1,
    };

    // Verificar overflow
    value.checked_mul(2).unwrap_or(i32::MAX)
}
```

#### 8. Exposição de Símbolos Internos

```rust
// ANTI-PATTERN: Exportar funções internas
#[no_mangle]
pub extern "C" fn internal_helper() {
    // Esta função não deveria ser visível externamente
}

#[no_mangle]
pub extern "C" fn public_api() {
    internal_helper();
}

// BOA PRÁTICA: Controlar visibilidade
// Usar módulos e restringir exports
mod internal {
    pub fn helper() {
        // Implementação interna
    }
}

#[no_mangle]
pub extern "C" fn public_api_safe() {
    internal::helper();
}

// No Cargo.toml, usar:
// [lib]
// crate-type = ["cdylib"]
// 
// No Rust, usar apenas #[no_mangle] nas funções que devem ser exportadas
```

#### 9. Panic em Código Externo

```rust
// ANTI-PATTERN: Permitir panics em exports
#[no_mangle]
pub extern "C" fn risky_function() {
    panic!("Something went wrong"); // PROBLEMA: Panic não tratado
}

// BOA PRÁTICA: Prevenir panics ou tratá-los
use std::panic;

#[no_mangle]
pub extern "C" fn safe_function() -> i32 {
    let result = panic::catch_unwind(|| {
        // Código que pode panicar
        risky_operation()
    });

    match result {
        Ok(value) => value,
        Err(_) => {
            // Log do erro, retornar código de erro
            -1
        }
    }
}

fn risky_operation() -> i32 {
    // Operação que pode falhar
    42
}
```

#### 10. Dependências Não Verificadas

```toml
# ANTI-PATTERN: Usar dependências sem verificação
[dependencies]
rand = "*"  # PROBLEMA: Versão não especificada
serde = "*"  # PROBLEMA: Pode mudar comportamento

# BOA PRÁTICA: Versões exatas e hash verificado
[dependencies]
rand = "=0.8.5"  # Versão específica
serde = "=1.0.188"  # Versão específica

# Usar cargo-audit para verificar vulnerabilidades
# $ cargo install cargo-audit
# $ cargo audit
```

#### 11. Logs de Dados Sensíveis

```rust
// ANTI-PATTERN: Logar dados sensíveis
#[no_mangle]
pub extern "C" fn process_payment(card_number: *const u8, cvv: *const u8) {
    let card = unsafe { CStr::from_ptr(card_number as *const c_char) };
    let cvv_str = unsafe { CStr::from_ptr(cvv as *const c_char) };

    // PROBLEMA: Log contém dados sensíveis
    log::info!("Processing payment for card: {:?}", card);
    log::info!("CVV: {:?}", cvv_str);
}

// BOA PRÁTICA: Mascarar dados sensíveis em logs
#[no_mangle]
pub extern "C" fn process_payment_safe(card_number: *const u8, cvv: *const u8) {
    let card = unsafe { CStr::from_ptr(card_number as *const c_char) };
    let cvv_str = unsafe { CStr::from_ptr(cvv as *const c_char) };

    // Log seguro com mascaramento
    let masked_card = mask_card_number(card.to_str().unwrap_or(""));
    log::info!("Processing payment for card: {}", masked_card);
    log::info!("CVV provided"); // Nunca logar CVV
}

fn mask_card_number(card: &str) -> String {
    if card.len() < 4 {
        return "****".to_string();
    }
    let last_four = &card[card.len() - 4..];
    format!("****-****-****-{}", last_four)
}
```

#### 12. Tempo de Execução Não Limitado

```rust
// ANTI-PATTERN: Sem limite de tempo
#[no_mangle]
pub extern "C" fn long_running_task() {
    // PROBLEMA: Pode rodar indefinidamente
    loop {
        process_item();
    }
}

// BOA PRÁTICA: Implementar timeout
use std::time::{Duration, Instant};

#[no_mangle]
pub extern "C" fn long_running_task_with_timeout(timeout_ms: u64) -> i32 {
    let start = Instant::now();
    let timeout = Duration::from_millis(timeout_ms);

    loop {
        if start.elapsed() > timeout {
            return -1; // Timeout atingido
        }

        if !process_item() {
            return 0; // Processamento concluído
        }
    }
}

fn process_item() -> bool {
    // Processar um item
    true // Retorna true se há mais itens
}
```

#### 13. Sem Verificação de Integridade

```rust
// ANTI-PATTERN: Não verificar integridade dos dados
#[no_mangle]
pub extern "C" fn load_module(path: *const u8) -> *mut Module {
    let c_str = unsafe { CStr::from_ptr(path as *const c_char) };
    let path_str = c_str.to_str().unwrap();

    // PROBLEMA: Não verifica se o módulo foi modificado
    let module_bytes = std::fs::read(path_str).unwrap();

    let module = load_from_bytes(&module_bytes);
    Box::into_raw(Box::new(module))
}

// BOA PRÁTICA: Verificar hash e assinatura
use sha2::{Sha256, Digest};

#[no_mangle]
pub extern "C" fn load_module_safe(
    path: *const u8,
    expected_hash: *const u8,
) -> *mut Module {
    if path.is_null() || expected_hash.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(path as *const c_char) };
    let path_str = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let module_bytes = match std::fs::read(path_str) {
        Ok(b) => b,
        Err(_) => return std::ptr::null_mut(),
    };

    // Verificar hash
    let mut hasher = Sha256::new();
    hasher.update(&module_bytes);
    let computed_hash = hasher.finalize();

    let expected = unsafe { std::slice::from_raw_parts(expected_hash, 32) };
    if computed_hash.as_slice() != expected {
        return std::ptr::null_mut(); // Integridade comprometida
    }

    let module = load_from_bytes(&module_bytes);
    Box::into_raw(Box::new(module))
}
```

#### 14. Uso Indevido de Global State

```rust
// ANTI-PATTERN: Estado global mutável
static mut GLOBAL_CONFIG: Option<Config> = None;

#[no_mangle]
pub extern "C" fn init_config(config: *const Config) {
    unsafe {
        GLOBAL_CONFIG = Some((*config).clone()); // PROBELEMA: Não é thread-safe
    }
}

#[no_mangle]
pub extern "C" fn get_config() -> *const Config {
    unsafe {
        match &GLOBAL_CONFIG {
            Some(config) => config as *const Config,
            None => std::ptr::null(),
        }
    }
}

// BOA PRÁTICA: Usar thread-safe alternatives
use std::sync::Once;

static mut GLOBAL_CONFIG: Option<Config> = None;
static INIT: Once = Once::new();

pub fn init_config_safe(config: Config) {
    unsafe {
        INIT.call_once(|| {
            GLOBAL_CONFIG = Some(config);
        });
    }
}

pub fn get_config_safe() -> Option<&'static Config> {
    unsafe { GLOBAL_CONFIG.as_ref() }
}
```

#### 15. Sem Tratamento de Sinais

```rust
// ANTI-PATTERN: Não tratar sinais do sistema
#[no_mangle]
pub extern "C" fn main_function() {
    // PROBLEMA: Não trata SIGTERM, SIGINT
    loop {
        process_request();
    }
}

// BOA PRÁTICA: Tratar sinais para shutdown gracioso
use std::sync::atomic::{AtomicBool, Ordering};

static RUNNING: AtomicBool = AtomicBool::new(true);

pub fn setup_signal_handlers() {
    // Em WASM, sinais são limitados
    // Usar mecanismos de cooperação
}

#[no_mangle]
pub extern "C" fn main_function_safe() {
    setup_signal_handlers();

    while RUNNING.load(Ordering::SeqCst) {
        process_request();
    }

    // Cleanup
    cleanup_resources();
}

pub fn shutdown() {
    RUNNING.store(false, Ordering::SeqCst);
}
```

#### 16. Falta de Resource Limits

```rust
// ANTI-PATTERN: Sem limites de recursos
#[no_mangle]
pub extern "C" fn process_data_unlimited(data: *const u8, len: usize) {
    // PROBELEMA: Pode alocar memória indefinidamente
    let mut result = Vec::new();
    let slice = unsafe { std::slice::from_raw_parts(data, len) };

    for chunk in slice.chunks(1024) {
        result.extend_from_slice(chunk); // Sem limite!
    }
}

// BOA PRÁTICA: Definir e respeitar limites
const MAX_ALLOCATION: usize = 1024 * 1024 * 10; // 10MB

#[no_mangle]
pub extern "C" fn process_data_limited(data: *const u8, len: usize) -> i32 {
    if len > MAX_ALLOCATION {
        return -1; // Dados muito grandes
    }

    let mut result = Vec::new();
    let slice = unsafe { std::slice::from_raw_parts(data, len) };

    for chunk in slice.chunks(1024) {
        if result.len() + chunk.len() > MAX_ALLOCATION {
            return -2; // Limite atingido
        }
        result.extend_from_slice(chunk);
    }

    0 // Sucesso
}
```

#### 17. Output Não Validado

```rust
// ANTI-PATTERN: Retornar dados sem validação
#[no_mangle]
pub extern "C" fn generate_output() -> *mut u8 {
    let mut output = String::new();
    output.push_str("<script>alert('xss')</script>"); // PROBLEMA: XSS

    let c_string = CString::new(output).unwrap();
    c_string.into_raw()
}

// BOA PRÁTICA: Sanitizar output
use ammonia::clean;

#[no_mangle]
pub extern "C" fn generate_output_safe() -> *mut u8 {
    let output = "<script>alert('xss')</script>";

    // Limpar HTML
    let safe_output = clean(output);

    match CString::new(safe_output) {
        Ok(c_string) => c_string.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
```

#### 18. Sem Logging Estruturado

```rust
// ANTI-PATTERN: Logs não estruturados
#[no_mangle]
pub extern "C" fn process_request() {
    println!("Processing request"); // PROBLEMA: Não tem contexto
    println!("Error occurred"); // PROBLEMA: Não tem detalhes
}

// BOA PRÁTICA: Logs estruturados com contexto
use log::{info, error, debug, warn};
use std::time::Instant;

#[no_mangle]
pub extern "C" fn process_request_safe() {
    let request_id = generate_request_id();
    let start = Instant::now();

    info!(
        request_id = %request_id,
        "Processing request"
    );

    match execute_request() {
        Ok(result) => {
            info!(
                request_id = %request_id,
                duration_ms = start.elapsed().as_millis() as u64,
                "Request completed successfully"
            );
        }
        Err(e) => {
            error!(
                request_id = %request_id,
                error = %e,
                duration_ms = start.elapsed().as_millis() as u64,
                "Request failed"
            );
        }
    }
}

fn generate_request_id() -> String {
    uuid::Uuid::new_v4().to_string()
}

fn execute_request() -> Result<(), Box<dyn std::error::Error>> {
    Ok(())
}
```

#### 19. Memory Leaks em Loops

```rust
// ANTI-PATTERN: Vazamentos em loops
#[no_mangle]
pub extern "C" fn process_loop() {
    loop {
        // PROBLEMA: Vec nunca é liberado
        let data = vec![0u8; 1024];
        process_chunk(&data);
        // data é dropado aqui, mas em WASM pode não funcionar corretamente
    }
}

// BOA PRÁTICA: Gerenciar memória explicitamente
#[no_mangle]
pub extern "C" fn process_loop_safe() {
    // Pré-alocar buffer reutilizável
    let mut buffer = vec![0u8; 1024];

    loop {
        // Reutilizar buffer em vez de alocar novo
        fill_buffer(&mut buffer);
        process_chunk(&buffer);

        // Limpar dados sensíveis
        buffer.fill(0);
    }
}

fn fill_buffer(buffer: &mut [u8]) {
    // Preencher buffer
}

fn process_chunk(data: &[u8]) {
    // Processar chunk
}
```

#### 20. Falta de Input Sanitization

```rust
// ANTI-PATTERN: Input sem sanitização
#[no_mangle]
pub extern "C" fn search(query: *const u8, len: usize) -> *mut u8 {
    let slice = unsafe { std::slice::from_raw_parts(query, len) };
    let query_str = std::str::from_utf8(slice).unwrap();

    // PROBLEMA: query_str pode conter SQL injection, XSS, etc.
    let result = format!("Results for: {}", query_str);

    CString::new(result).unwrap().into_raw()
}

// BOA PRÁTICA: Sanitizar todo input
use regex::Regex;

#[no_mangle]
pub extern "C" fn search_safe(query: *const u8, len: usize) -> *mut u8 {
    if query.is_null() || len == 0 {
        return std::ptr::null_mut();
    }

    let slice = unsafe { std::slice::from_raw_parts(query, len) };

    let query_str = match std::str::from_utf8(slice) {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    // Remover caracteres perigosos
    let re = Regex::new(r"[<>\"'&]").unwrap();
    let sanitized = re.replace_all(query_str, "");

    // Limitar tamanho
    let truncated: String = sanitized.chars().take(100).collect();

    let result = format!("Results for: {}", truncated);

    match CString::new(result) {
        Ok(c_string) => c_string.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
```

#### 21. Sem Rate Limiting

```rust
// ANTI-PATTERN: Sem controle de taxa
#[no_mangle]
pub extern "C" fn api_endpoint() {
    // PROBLEMA: Pode ser abusado
    process_request();
}

// BOA PRÁTICA: Implementar rate limiting
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

struct RateLimiter {
    requests: Mutex<HashMap<String, Vec<Instant>>>,
    max_requests: usize,
    window: Duration,
}

impl RateLimiter {
    fn new(max_requests: usize, window_secs: u64) -> Self {
        Self {
            requests: Mutex::new(HashMap::new()),
            max_requests,
            window: Duration::from_secs(window_secs),
        }
    }

    fn is_allowed(&self, client_id: &str) -> bool {
        let mut requests = self.requests.lock().unwrap();
        let now = Instant::now();

        let client_requests = requests
            .entry(client_id.to_string())
            .or_insert_with(Vec::new);

        // Remover requisições antigas
        client_requests.retain(|&time| now.duration_since(time) < self.window);

        if client_requests.len() >= self.max_requests {
            return false;
        }

        client_requests.push(now);
        true
    }
}

static RATE_LIMITER: once_cell::sync::Lazy<RateLimiter> =
    once_cell::sync::Lazy::new(|| RateLimiter::new(100, 60));

#[no_mangle]
pub extern "C" fn api_endpoint_safe(client_id: *const u8) -> i32 {
    if client_id.is_null() {
        return -1;
    }

    let id = unsafe { CStr::from_ptr(client_id as *const c_char) };
    let id_str = match id.to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };

    if !RATE_LIMITER.is_allowed(id_str) {
        return -2; // Rate limit exceeded
    }

    process_request();
    0
}
```

#### 22. Sem Versionamento de API

```rust
// ANTI-PATTERN: Sem versionamento
#[no_mangle]
pub extern "C" fn process(data: *const u8) -> i32 {
    // PROBLEMA: Breaking changes quebram clientes existentes
    0
}

// BOA PRÁTICA: Versionar API explicitamente
#[no_mangle]
pub extern "C" fn api_v1_process(data: *const u8) -> i32 {
    // Versão 1 da API
    0
}

#[no_mangle]
pub extern "C" fn api_v2_process(data: *const u8) -> i32 {
    // Versão 2 com melhorias
    0
}

// Manter compatibilidade com versões anteriores
#[no_mangle]
pub extern "C" fn process_compat(data: *const u8) -> i32 {
    api_v1_process(data)
}
```

#### 23. Falta de Telemetria

```rust
// ANTI-PATTERN: Sem telemetria
#[no_mangle]
pub extern "C" fn critical_operation() {
    // PROBLEMA: Sem visibilidade sobre o que acontece
    do_something();
}

// BOA PRÁTICA: Telemetria abrangente
use std::sync::atomic::{AtomicU64, Ordering};

static OPERATIONS_TOTAL: AtomicU64 = AtomicU64::new(0);
static OPERATIONS_SUCCESS: AtomicU64 = AtomicU64::new(0);
static OPERATIONS_FAILURE: AtomicU64 = AtomicU64::new(0);

#[no_mangle]
pub extern "C" fn critical_operation_tracked() -> i32 {
    OPERATIONS_TOTAL.fetch_add(1, Ordering::Relaxed);

    let start = Instant::now();
    let result = do_something();
    let duration = start.elapsed();

    match result {
        Ok(_) => {
            OPERATIONS_SUCCESS.fetch_add(1, Ordering::Relaxed);
            info!(
                operation = "critical",
                duration_ms = duration.as_millis() as u64,
                "Operation completed"
            );
            0
        }
        Err(e) => {
            OPERATIONS_FAILURE.fetch_add(1, Ordering::Relaxed);
            error!(
                operation = "critical",
                error = %e,
                duration_ms = duration.as_millis() as u64,
                "Operation failed"
            );
            -1
        }
    }
}

fn do_something() -> Result<(), Box<dyn std::error::Error>> {
    Ok(())
}
```

---

## 17.2 Security Checklist

### Checklist de Segurança Completo

```rust
// security-checklist/src/lib.rs
pub struct SecurityChecklist {
    pub categories: Vec<SecurityCategory>,
}

pub struct SecurityCategory {
    pub name: String,
    pub items: Vec<SecurityCheckItem>,
}

pub struct SecurityCheckItem {
    pub id: String,
    pub description: String,
    pub priority: Priority,
    pub status: CheckStatus,
    pub evidence: Option<String>,
    pub notes: Option<String>,
}

pub enum Priority {
    Critical,
    High,
    Medium,
    Low,
}

pub enum CheckStatus {
    NotChecked,
    Pass,
    Fail,
    NotApplicable,
}

impl SecurityChecklist {
    pub fn new() -> Self {
        Self {
            categories: vec![
                Self::memory_safety_category(),
                Self::input_validation_category(),
                Self::authentication_category(),
                Self::authorization_category(),
                Self::cryptography_category(),
                Self::logging_category(),
                Self::error_handling_category(),
                Self::supply_chain_category(),
                Self::deployment_category(),
                Self::monitoring_category(),
            ],
        }
    }

    fn memory_safety_category() -> SecurityCategory {
        SecurityCategory {
            name: "Memory Safety".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "MS-001".to_string(),
                    description: "All memory allocations are bounds-checked".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MS-002".to_string(),
                    description: "No use-after-free vulnerabilities".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MS-003".to_string(),
                    description: "No double-free vulnerabilities".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MS-004".to_string(),
                    description: "Stack overflow protection enabled".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MS-005".to_string(),
                    description: "Memory is zeroed before deallocation".to_string(),
                    priority: Priority::Medium,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn input_validation_category() -> SecurityCategory {
        SecurityCategory {
            name: "Input Validation".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "IV-001".to_string(),
                    description: "All external inputs are validated".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "IV-002".to_string(),
                    description: "Input length limits are enforced".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "IV-003".to_string(),
                    description: "Input type validation is performed".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "IV-004".to_string(),
                    description: "Special characters are sanitized".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "IV-005".to_string(),
                    description: "SQL injection prevention implemented".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn authentication_category() -> SecurityCategory {
        SecurityCategory {
            name: "Authentication".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "AU-001".to_string(),
                    description: "Multi-factor authentication enabled".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AU-002".to_string(),
                    description: "Password policy enforced".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AU-003".to_string(),
                    description: "Account lockout after failed attempts".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AU-004".to_string(),
                    description: "Session timeout configured".to_string(),
                    priority: Priority::Medium,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AU-005".to_string(),
                    description: "Secure session management".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn authorization_category() -> SecurityCategory {
        SecurityCategory {
            name: "Authorization".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "AZ-001".to_string(),
                    description: "Role-based access control implemented".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AZ-002".to_string(),
                    description: "Principle of least privilege applied".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AZ-003".to_string(),
                    description: "Access control checks on all endpoints".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "AZ-004".to_string(),
                    description: "Privileged access is logged".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn cryptography_category() -> SecurityCategory {
        SecurityCategory {
            name: "Cryptography".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "CR-001".to_string(),
                    description: "TLS 1.3 used for all communications".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "CR-002".to_string(),
                    description: "AES-256 used for data at rest".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "CR-003".to_string(),
                    description: "Secure key management implemented".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "CR-004".to_string(),
                    description: "Cryptographic keys are rotated regularly".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn logging_category() -> SecurityCategory {
        SecurityCategory {
            name: "Logging".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "LG-001".to_string(),
                    description: "Security events are logged".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "LG-002".to_string(),
                    description: "Logs are tamper-proof".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "LG-003".to_string(),
                    description: "Sensitive data is not logged".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "LG-004".to_string(),
                    description: "Log retention policy is defined".to_string(),
                    priority: Priority::Medium,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn error_handling_category() -> SecurityCategory {
        SecurityCategory {
            name: "Error Handling".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "EH-001".to_string(),
                    description: "Errors are handled gracefully".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "EH-002".to_string(),
                    description: "Error messages do not leak sensitive info".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "EH-003".to_string(),
                    description: "Panics are caught and handled".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn supply_chain_category() -> SecurityCategory {
        SecurityCategory {
            name: "Supply Chain".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "SC-001".to_string(),
                    description: "Dependencies are audited for vulnerabilities".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "SC-002".to_string(),
                    description: "Dependency versions are pinned".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "SC-003".to_string(),
                    description: "Build is reproducible".to_string(),
                    priority: Priority::Medium,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "SC-004".to_string(),
                    description: "WASM modules are signed".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn deployment_category() -> SecurityCategory {
        SecurityCategory {
            name: "Deployment".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "DP-001".to_string(),
                    description: "Sandbox configuration is hardened".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "DP-002".to_string(),
                    description: "Resource limits are configured".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "DP-003".to_string(),
                    description: "Network access is restricted".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "DP-004".to_string(),
                    description: "File system access is restricted".to_string(),
                    priority: Priority::Critical,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    fn monitoring_category() -> SecurityCategory {
        SecurityCategory {
            name: "Monitoring".to_string(),
            items: vec![
                SecurityCheckItem {
                    id: "MN-001".to_string(),
                    description: "Security monitoring is enabled".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MN-002".to_string(),
                    description: "Alerts are configured for security events".to_string(),
                    priority: Priority::High,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
                SecurityCheckItem {
                    id: "MN-003".to_string(),
                    description: "Incident response plan is documented".to_string(),
                    priority: Priority::Medium,
                    status: CheckStatus::NotChecked,
                    evidence: None,
                    notes: None,
                },
            ],
        }
    }

    pub fn calculate_compliance_score(&self) -> f64 {
        let mut total = 0;
        let mut passed = 0;

        for category in &self.categories {
            for item in &category.items {
                total += 1;
                if matches!(item.status, CheckStatus::Pass) {
                    passed += 1;
                }
            }
        }

        if total == 0 {
            return 0.0;
        }

        (passed as f64 / total as f64) * 100.0
    }

    pub fn get_critical_failures(&self) -> Vec<&SecurityCheckItem> {
        let mut failures = Vec::new();

        for category in &self.categories {
            for item in &category.items {
                if matches!(item.priority, Priority::Critical)
                    && matches!(item.status, CheckStatus::Fail)
                {
                    failures.push(item);
                }
            }
        }

        failures
    }

    pub fn generate_report(&self) -> SecurityReport {
        let score = self.calculate_compliance_score();
        let critical_failures = self.get_critical_failures();

        SecurityReport {
            generated_at: current_timestamp(),
            overall_score: score,
            total_checks: self.categories.iter()
                .map(|c| c.items.len())
                .sum(),
            passed_checks: self.categories.iter()
                .flat_map(|c| &c.items)
                .filter(|i| matches!(i.status, CheckStatus::Pass))
                .count(),
            failed_checks: self.categories.iter()
                .flat_map(|c| &c.items)
                .filter(|i| matches!(i.status, CheckStatus::Fail))
                .count(),
            critical_failures: critical_failures.len() as u32,
            recommendations: self.generate_recommendations(),
        }
    }

    fn generate_recommendations(&self) -> Vec<String> {
        let mut recommendations = Vec::new();

        for category in &self.categories {
            for item in &category.items {
                if matches!(item.status, CheckStatus::Fail) {
                    recommendations.push(format!(
                        "[{:?}] {}: {}",
                        item.priority, item.id, item.description
                    ));
                }
            }
        }

        recommendations
    }
}

#[derive(Debug)]
pub struct SecurityReport {
    pub generated_at: u64,
    pub overall_score: f64,
    pub total_checks: usize,
    pub passed_checks: usize,
    pub failed_checks: usize,
    pub critical_failures: u32,
    pub recommendations: Vec<String>,
}

fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
```

---

## 17.3 Decision Trees

### Árvore de Decisão: Qual Runtime?

```
┌─────────────────────────────────────────────────────────────┐
│                    ESCOLHA DO RUNTIME                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Precisa de suporte WASI?                                   │
│  │                                                          │
│  ├─ SIM ──► Precisa de performance máxima?                  │
│  │          │                                               │
│  │          ├─ SIM ──► Precisa de GC?                       │
│  │          │          │                                    │
│  │          │          ├─ SIM ──► Wasmer (com GC)           │
│  │          │          │                                    │
│  │          │          └─ NÃO ──► Wasmtime                  │
│  │          │                                               │
│  │          └─ NÃO ──► Precisa de portabilidade?            │
│  │                     │                                    │
│  │                     ├─ SIM ──► Wasmer                    │
│  │                     │                                    │
│  │                     └─ NÃO ──► Wasmtime ou Wasmer        │
│  │                                                          │
│  └─ NÃO ──► É para navegador?                               │
│             │                                               │
│             ├─ SIM ──► browser nativo (Chrome, Firefox)     │
│             │                                               │
│             └─ NÃO ──► É para edge computing?               │
│                        │                                    │
│                        ├─ SIM ──► Precisa de isolamento?    │
│                        │          │                         │
│                        │          ├─ SIM ──► V8 (Isolates)  │
│                        │          │                         │
│                        │          └─ NÃO ──► Wasmer         │
│                        │                                    │
│                        └─ NÃO ──► É para blockchain?        │
│                                   │                         │
│                                   ├─ SIM ──► Plataforma     │
│                                   │          específica      │
│                                   │                         │
│                                   └─ NÃO ──► Wasmtime       │
│                                              (padrão)       │
└─────────────────────────────────────────────────────────────┘
```

### Implementação da Árvore de Decisão

```rust
// decision-tree/src/lib.rs
pub struct RuntimeDecisionTree;

impl RuntimeDecisionTree {
    pub fn recommend(config: RuntimeRequirements) -> RuntimeRecommendation {
        let mut steps = Vec::new();

        // Step 1: WASI support needed?
        if config.needs_wasi {
            steps.push("WASI support required".to_string());

            if config.needs_performance {
                steps.push("High performance required".to_string());

                if config.needs_gc {
                    steps.push("GC support required".to_string());
                    return RuntimeRecommendation {
                        runtime: Runtime::Wasmer,
                        reason: "Wasmer with GC support for WASI + performance + GC".to_string(),
                        steps,
                    };
                }

                steps.push("No GC needed".to_string());
                return RuntimeRecommendation {
                    runtime: Runtime::Wasmtime,
                    reason: "Wasmtime for WASI + maximum performance".to_string(),
                    steps,
                };
            }

            steps.push("Performance not critical".to_string());

            if config.needs_portability {
                steps.push("Portability required".to_string());
                return RuntimeRecommendation {
                    runtime: Runtime::Wasmer,
                    reason: "Wasmer for WASI + portability".to_string,
                    steps,
                };
            }

            return RuntimeRecommendation {
                runtime: Runtime::Wasmer,
                reason: "Wasmer for WASI support".to_string(),
                steps,
            };
        }

        steps.push("No WASI support needed".to_string());

        if config.is_browser {
            steps.push("Browser environment detected".to_string());
            return RuntimeRecommendation {
                runtime: Runtime::BrowserNative,
                reason: "Use browser's native WASM support".to_string(),
                steps,
            };
        }

        if config.is_edge {
            steps.push("Edge computing environment".to_string());

            if config.needs_isolation {
                steps.push("Strong isolation required".to_string());
                return RuntimeRecommendation {
                    runtime: Runtime::V8Isolates,
                    reason: "V8 Isolates for edge + isolation".to_string(),
                    steps,
                };
            }

            return RuntimeRecommendation {
                runtime: Runtime::Wasmer,
                reason: "Wasmer for edge computing".to_string(),
                steps,
            };
        }

        if config.is_blockchain {
            steps.push("Blockchain environment".to_string());
            return RuntimeRecommendation {
                runtime: Runtime::PlatformSpecific,
                reason: "Use platform-specific WASM runtime".to_string(),
                steps,
            };
        }

        steps.push("Default recommendation".to_string());
        RuntimeRecommendation {
            runtime: Runtime::Wasmtime,
            reason: "Wasmtime as default choice".to_string(),
            steps,
        }
    }
}

pub struct RuntimeRequirements {
    pub needs_wasi: bool,
    pub needs_performance: bool,
    pub needs_gc: bool,
    pub needs_portability: bool,
    pub is_browser: bool,
    pub is_edge: bool,
    pub is_blockchain: bool,
    pub needs_isolation: bool,
}

pub struct RuntimeRecommendation {
    pub runtime: Runtime,
    pub reason: String,
    pub steps: Vec<String>,
}

pub enum Runtime {
    Wasmtime,
    Wasmer,
    V8Isolates,
    BrowserNative,
    PlatformSpecific,
}
```

### Árvore de Decisão: Qual Linguagem?

```
┌─────────────────────────────────────────────────────────────┐
│                  ESCOLHA DA LINGUAGEM                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Prioridade é segurança?                                    │
│  │                                                          │
│  ├─ SIM ──► Equipe tem experiência com Rust?                │
│  │          │                                               │
│  │          ├─ SIM ──► RUST (recomendado)                   │
│  │          │                                               │
│  │          └─ NÃO ──► Tempo para aprender?                 │
│  │                     │                                    │
│  │                     ├─ SIM ──► RUST                      │
│  │                     │                                    │
│  │                     └─ NÃO ──► C++ (com cuidados)        │
│  │                                                          │
│  └─ NÃO ──► É projeto greenfield?                           │
│             │                                               │
│             ├─ SIM ──► RUST (melhor para novos projetos)    │
│             │                                               │
│             └─ NÃO ──► Código existente em C/C++?           │
│                        │                                    │
│                        ├─ SIM ──► C++/EMSCRIPTEN            │
│                        │                                   │
│                        └─ NÃO ──► Linguagem mais rápida?    │
│                                   │                         │
│                                   ├─ SIM ──► RUST           │
│                                   │                         │
│                                   └─ NÃO ──► C++            │
└─────────────────────────────────────────────────────────────┘
```

### Implementação da Árvore de Decisão

```rust
// decision-tree/src/language.rs
pub struct LanguageDecisionTree;

impl LanguageDecisionTree {
    pub fn recommend(config: LanguageRequirements) -> LanguageRecommendation {
        let mut steps = Vec::new();

        if config.security_priority {
            steps.push("Security is top priority".to_string());

            if config.team_knows_rust {
                steps.push("Team has Rust experience".to_string());
                return LanguageRecommendation {
                    language: Language::Rust,
                    reason: "Rust for security + team experience".to_string(),
                    steps,
                };
            }

            steps.push("Team lacks Rust experience".to_string());

            if config.time_to_learn {
                steps.push("Time available to learn Rust".to_string());
                return LanguageRecommendation {
                    language: Language::Rust,
                    reason: "Rust for security, worth the learning investment".to_string(),
                    steps,
                };
            }

            steps.push("No time to learn Rust".to_string());
            return LanguageRecommendation {
                language: Language::Cpp,
                reason: "C++ with strict safety practices".to_string(),
                steps,
            };
        }

        steps.push("Security is not top priority".to_string());

        if config.is_greenfield {
            steps.push("Greenfield project".to_string());
            return LanguageRecommendation {
                language: Language::Rust,
                reason: "Rust for new projects".to_string(),
                steps,
            };
        }

        steps.push("Existing project".to_string());

        if config.has_existing_cpp {
            steps.push("Existing C/C++ codebase".to_string());
            return LanguageRecommendation {
                language: Language::Cpp,
                reason: "C++/Emscripten for existing codebase".to_string(),
                steps,
            };
        }

        steps.push("No existing C++ code".to_string());

        if config.speed_matters {
            steps.push("Development speed matters".to_string());
            return LanguageRecommendation {
                language: Language::Rust,
                reason: "Rust for faster development with safety".to_string(),
                steps,
            };
        }

        steps.push("Default recommendation".to_string());
        LanguageRecommendation {
            language: Language::Cpp,
            reason: "C++ as default".to_string(),
            steps,
        }
    }
}

pub struct LanguageRequirements {
    pub security_priority: bool,
    pub team_knows_rust: bool,
    pub time_to_learn: bool,
    pub is_greenfield: bool,
    pub has_existing_cpp: bool,
    pub speed_matters: bool,
}

pub struct LanguageRecommendation {
    pub language: Language,
    pub reason: String,
    pub steps: Vec<String>,
}

pub enum Language {
    Rust,
    Cpp,
}
```

---

## 17.4 Complete Project Template (Rust+Wasm)

### Template Completo de Projeto

```rust
// Estrutura do projeto:
// wasm-project/
// ├── Cargo.toml
// ├── rust-toolchain.toml
// ├── src/
// │   ├── lib.rs
// │   ├── api.rs
// │   ├── memory.rs
// │   ├── error.rs
// │   └── utils.rs
// ├── tests/
// │   ├── integration.rs
// │   └── unit.rs
// ├── benches/
// │   └── performance.rs
// ├── scripts/
// │   ├── build.sh
// │   ├── test.sh
// │   └── deploy.sh
// └── wasm/
//     └── README.md
```

#### Cargo.toml

```toml
[package]
name = "wasm-project"
version = "0.1.0"
edition = "2021"
authors = ["Developer <dev@example.com>"]
description = "Secure WebAssembly project template"
license = "MIT"

[lib]
crate-type = ["cdylib", "rlib"]

[dependencies]
# Core
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# Security
zeroize = { version = "1.7", features = ["derive"] }
sha2 = "0.10"
rand = "0.8"

# Error handling
thiserror = "1.0"

# Logging
log = "0.4"
wasm-logger = "0.2"

# Utilities
chrono = "0.4"
uuid = { version = "1.0", features = ["v4"] }

[dev-dependencies]
wasm-bindgen-test = "0.3"
proptest = "1.0"
criterion = { version = "0.5", features = ["html_reports"] }

[profile.release]
opt-level = "s"  # Optimize for size
lto = true
codegen-units = 1
panic = "abort"
strip = "symbols"

[profile.release.package."*"]
opt-level = "s"

[[bench]]
name = "performance"
harness = false
```

#### src/lib.rs

```rust
//! Secure WebAssembly Project Template
//!
//! This module provides a secure, well-structured foundation for WebAssembly projects.

pub mod api;
pub mod error;
pub mod memory;
pub mod utils;

use wasm_bindgen::prelude::*;

/// Initialize the WASM module
#[wasm_bindgen(start)]
pub fn init() {
    // Set up logging
    wasm_logger::init(wasm_logger::Config::default());

    log::info!("WASM module initialized");
}

/// Main entry point for the application
#[wasm_bindgen]
pub struct WasmApp {
    state: AppState,
    initialized: bool,
}

#[derive(Clone)]
struct AppState {
    config: Config,
    data: Vec<u8>,
}

#[derive(Clone, serde::Serialize, serde::Deserialize)]
pub struct Config {
    pub max_size: usize,
    pub timeout_ms: u64,
    pub debug: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            max_size: 1024 * 1024, // 1MB
            timeout_ms: 5000,
            debug: false,
        }
    }
}

#[wasm_bindgen]
impl WasmApp {
    /// Create a new WasmApp instance
    #[wasm_bindgen(constructor)]
    pub fn new() -> Result<WasmApp, JsError> {
        let config = Config::default();

        Ok(WasmApp {
            state: AppState {
                config,
                data: Vec::new(),
            },
            initialized: false,
        })
    }

    /// Initialize the application with configuration
    #[wasm_bindgen]
    pub fn initialize(&mut self, config_json: &str) -> Result<(), JsError> {
        let config: Config = serde_json::from_str(config_json)
            .map_err(|e| JsError::new(&format!("Invalid config: {}", e)))?;

        // Validate configuration
        if config.max_size == 0 {
            return Err(JsError::new("max_size must be greater than 0"));
        }

        if config.timeout_ms == 0 {
            return Err(JsError::new("timeout_ms must be greater than 0"));
        }

        self.state.config = config;
        self.initialized = true;

        log::info!("Application initialized with config: {:?}", self.state.config);

        Ok(())
    }

    /// Process input data
    #[wasm_bindgen]
    pub fn process(&mut self, input: &[u8]) -> Result<Vec<u8>, JsError> {
        if !self.initialized {
            return Err(JsError::new("Application not initialized"));
        }

        // Validate input size
        if input.len() > self.state.config.max_size {
            return Err(JsError::new("Input exceeds maximum size"));
        }

        // Process the data
        let result = api::process_data(input, &self.state.config)?;

        Ok(result)
    }

    /// Get application state as JSON
    #[wasm_bindgen]
    pub fn get_state(&self) -> Result<String, JsError> {
        serde_json::to_string(&self.state.config)
            .map_err(|e| JsError::new(&format!("Serialization error: {}", e)))
    }

    /// Clear sensitive data
    #[wasm_bindgen]
    pub fn cleanup(&mut self) {
        // Zero out sensitive data
        self.state.data.zeroize();
        self.state.data.clear();
        self.initialized = false;

        log::info!("Application cleaned up");
    }
}

impl Drop for WasmApp {
    fn drop(&mut self) {
        self.cleanup();
    }
}
```

#### src/api.rs

```rust
//! API module for processing data

use crate::error::{WasmError, WasmResult};
use crate::Config;

/// Process input data securely
pub fn process_data(input: &[u8], config: &Config) -> WasmResult<Vec<u8>> {
    // Validate input
    if input.is_empty() {
        return Err(WasmError::InvalidInput("Input is empty".to_string()));
    }

    // Check for suspicious patterns
    if contains_suspicious_patterns(input) {
        return Err(WasmError::SecurityViolation("Suspicious patterns detected".to_string()));
    }

    // Process the data
    let mut output = Vec::with_capacity(input.len());

    for chunk in input.chunks(1024) {
        let processed = process_chunk(chunk)?;
        output.extend_from_slice(&processed);
    }

    // Verify output size
    if output.len() > config.max_size {
        return Err(WasmError::ResourceLimit("Output exceeds maximum size".to_string()));
    }

    Ok(output)
}

/// Process a chunk of data
fn process_chunk(chunk: &[u8]) -> WasmResult<Vec<u8>> {
    // Example processing: XOR with a key
    let key = generate_processing_key();
    let processed: Vec<u8> = chunk.iter()
        .zip(key.iter().cycle())
        .map(|(a, b)| a ^ b)
        .collect();

    Ok(processed)
}

/// Check for suspicious patterns in input
fn contains_suspicious_patterns(input: &[u8]) -> bool {
    // Check for common attack patterns
    let patterns: &[&[u8]] = &[
        b"<script",
        b"javascript:",
        b"onerror=",
        b"onload=",
        b"eval(",
        b"exec(",
    ];

    for pattern in patterns {
        if input.windows(pattern.len()).any(|window| window == *pattern) {
            return true;
        }
    }

    false
}

/// Generate a processing key
fn generate_processing_key() -> Vec<u8> {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    (0..32).map(|_| rng.gen()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_data_valid() {
        let config = Config::default();
        let input = b"Hello, World!";
        let result = process_data(input, &config);
        assert!(result.is_ok());
    }

    #[test]
    fn test_process_data_empty() {
        let config = Config::default();
        let input = b"";
        let result = process_data(input, &config);
        assert!(result.is_err());
    }

    #[test]
    fn test_process_data_suspicious() {
        let config = Config::default();
        let input = b"<script>alert('xss')</script>";
        let result = process_data(input, &config);
        assert!(result.is_err());
    }
}
```

#### src/error.rs

```rust
//! Error handling module

use std::fmt;
use wasm_bindgen::JsValue;

/// Application error types
#[derive(Debug, Clone)]
pub enum WasmError {
    InvalidInput(String),
    SecurityViolation(String),
    ResourceLimit(String),
    ProcessingError(String),
    SerializationError(String),
}

impl fmt::Display for WasmError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WasmError::InvalidInput(msg) => write!(f, "Invalid input: {}", msg),
            WasmError::SecurityViolation(msg) => write!(f, "Security violation: {}", msg),
            WasmError::ResourceLimit(msg) => write!(f, "Resource limit: {}", msg),
            WasmError::ProcessingError(msg) => write!(f, "Processing error: {}", msg),
            WasmError::SerializationError(msg) => write!(f, "Serialization error: {}", msg),
        }
    }
}

impl std::error::Error for WasmError {}

impl From<WasmError> for JsValue {
    fn from(error: WasmError) -> Self {
        JsValue::from_str(&error.to_string())
    }
}

impl From<serde_json::Error> for WasmError {
    fn from(error: serde_json::Error) -> Self {
        WasmError::SerializationError(error.to_string())
    }
}

/// Result type for WASM operations
pub type WasmResult<T> = Result<T, WasmError>;
```

#### src/memory.rs

```rust
//! Memory management module

use zeroize::Zeroize;

/// Secure memory wrapper
pub struct SecureBuffer {
    data: Vec<u8>,
}

impl SecureBuffer {
    /// Create a new secure buffer
    pub fn new(size: usize) -> Self {
        Self {
            data: vec![0u8; size],
        }
    }

    /// Create from existing data
    pub fn from_data(data: Vec<u8>) -> Self {
        Self { data }
    }

    /// Get buffer as slice
    pub fn as_slice(&self) -> &[u8] {
        &self.data
    }

    /// Get mutable slice
    pub fn as_mut_slice(&mut self) -> &mut [u8] {
        &mut self.data
    }

    /// Get buffer length
    pub fn len(&self) -> usize {
        self.data.len()
    }

    /// Check if buffer is empty
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    /// Clear and zeroize the buffer
    pub fn secure_clear(&mut self) {
        self.data.zeroize();
        self.data.clear();
    }
}

impl Drop for SecureBuffer {
    fn drop(&mut self) {
        self.secure_clear();
    }
}

impl Clone for SecureBuffer {
    fn clone(&self) -> Self {
        Self {
            data: self.data.clone(),
        }
    }
}

/// Memory pool for efficient allocation
pub struct MemoryPool {
    buffers: Vec<SecureBuffer>,
    max_size: usize,
}

impl MemoryPool {
    /// Create a new memory pool
    pub fn new(max_size: usize) -> Self {
        Self {
            buffers: Vec::new(),
            max_size,
        }
    }

    /// Allocate a buffer from the pool
    pub fn allocate(&mut self, size: usize) -> Option<SecureBuffer> {
        // Try to reuse an existing buffer
        if let Some(pos) = self.buffers.iter().position(|b| b.len() >= size) {
            let mut buffer = self.buffers.remove(pos);
            buffer.secure_clear();
            return Some(buffer);
        }

        // Check if we can allocate a new buffer
        if self.total_allocated() + size > self.max_size {
            return None;
        }

        Some(SecureBuffer::new(size))
    }

    /// Return a buffer to the pool
    pub fn deallocate(&mut self, mut buffer: SecureBuffer) {
        buffer.secure_clear();
        if self.buffers.len() < 100 {
            self.buffers.push(buffer);
        }
    }

    /// Get total allocated memory
    pub fn total_allocated(&self) -> usize {
        self.buffers.iter().map(|b| b.len()).sum()
    }

    /// Clear all buffers
    pub fn clear(&mut self) {
        for buffer in &mut self.buffers {
            buffer.secure_clear();
        }
        self.buffers.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_secure_buffer() {
        let mut buffer = SecureBuffer::new(100);
        assert_eq!(buffer.len(), 100);
        assert!(!buffer.is_empty());

        buffer.secure_clear();
        assert!(buffer.is_empty());
    }

    #[test]
    fn test_memory_pool() {
        let mut pool = MemoryPool::new(1024);

        let buf1 = pool.allocate(100);
        assert!(buf1.is_some());

        let buf2 = pool.allocate(200);
        assert!(buf2.is_some());

        assert!(pool.total_allocated() > 0);
    }
}
```

#### src/utils.rs

```rust
//! Utility functions

use chrono::{DateTime, Utc};

/// Get current timestamp
pub fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

/// Get current datetime as ISO string
pub fn current_datetime() -> String {
    let dt: DateTime<Utc> = Utc::now();
    dt.to_rfc3339()
}

/// Validate a string is safe (no injection)
pub fn validate_string(input: &str) -> bool {
    let dangerous_patterns = &[
        "<script", "javascript:", "onerror=", "onload=",
        "eval(", "exec(", "DROP TABLE", "DELETE FROM",
    ];

    let input_lower = input.to_lowercase();

    for pattern in dangerous_patterns {
        if input_lower.contains(pattern) {
            return false;
        }
    }

    true
}

/// Sanitize a string
pub fn sanitize_string(input: &str) -> String {
    input
        .chars()
        .filter(|c| c.is_alphanumeric() || *c == ' ' || *c == '_' || *c == '-')
        .collect()
}

/// Truncate a string to max length
pub fn truncate_string(input: &str, max_len: usize) -> String {
    if input.len() <= max_len {
        input.to_string()
    } else {
        format!("{}...", &input[..max_len - 3])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_string_safe() {
        assert!(validate_string("Hello World"));
    }

    #[test]
    fn test_validate_string_dangerous() {
        assert!(!validate_string("<script>alert('xss')</script>"));
    }

    #[test]
    fn test_sanitize_string() {
        let input = "Hello! @World #2024";
        let sanitized = sanitize_string(input);
        assert_eq!(sanitized, "Hello World 2024");
    }
}
```

---

## 17.5 Complete Project Template (C++/Emscripten)

### Template C++/Emscripten

```cpp
// Estrutura do projeto:
// wasm-cpp-project/
// ├── CMakeLists.txt
// ├── src/
// │   ├── main.cpp
// │   ├── api.h
// │   ├── api.cpp
// │   ├── memory.h
// │   ├── memory.cpp
// │   ├── error.h
│   │   └── utils.h
// ├── tests/
// │   └── test_api.cpp
// ├── scripts/
// │   ├── build.sh
// │   └── test.sh
// └── wasm/
//     └── index.html
```

#### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.15)
project(wasm-cpp-project VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Emscripten settings
if(EMSCRIPTEN)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s WASM=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s MODULARIZE=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s EXPORT_NAME='WasmModule'")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s ALLOW_MEMORY_GROWTH=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s MAXIMUM_MEMORY=1073741824")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s INITIAL_MEMORY=16777216")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s STACK_SIZE=5242880")
    
    # Security flags
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s STACK_OVERFLOW_CHECK=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s SAFE_HEAP=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s ASSERTIONS=1")
    
    # Optimization
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -flto")
    
    # Exported functions
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -s EXPORTED_FUNCTIONS=['_malloc','_free','_init','_process','_cleanup']")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -s EXPORTED_RUNTIME_METHODS=['ccall','cwrap','UTF8ToString','stringToUTF8']")
endif()

# Source files
set(SOURCES
    src/main.cpp
    src/api.cpp
    src/memory.cpp
)

# Create library
add_library(wasm_lib STATIC ${SOURCES})
target_include_directories(wasm_lib PUBLIC src/)

# Create executable
add_executable(wasm_project ${SOURCES})
target_link_libraries(wasm_project wasm_lib)

# Enable testing
enable_testing()
find_package(GTest QUIET)
if(GTest_FOUND)
    add_executable(tests tests/test_api.cpp)
    target_link_libraries(tests wasm_lib GTest::GTest GTest::Main)
    add_test(NAME tests COMMAND tests)
endif()

# Install
install(TARGETS wasm_project DESTINATION bin)
```

#### src/api.h

```cpp
#pragma once

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <memory>

namespace wasm {

// Configuration structure
struct Config {
    size_t max_size = 1024 * 1024;  // 1MB
    uint64_t timeout_ms = 5000;
    bool debug = false;
};

// Result structure
struct Result {
    bool success;
    std::string error;
    std::vector<uint8_t> data;
    
    Result() : success(false) {}
    Result(std::vector<uint8_t> d) : success(true), data(std::move(d)) {}
    Result(std::string e) : success(false), error(std::move(e)) {}
};

// Main application class
class WasmApp {
public:
    WasmApp();
    ~WasmApp();
    
    // Non-copyable
    WasmApp(const WasmApp&) = delete;
    WasmApp& operator=(const WasmApp&) = delete;
    
    // Initialize with configuration
    bool initialize(const std::string& config_json);
    
    // Process data
    Result process(const uint8_t* input, size_t input_size);
    
    // Get state as JSON
    std::string get_state() const;
    
    // Cleanup sensitive data
    void cleanup();
    
private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

}  // namespace wasm

// C API for WASM exports
extern "C" {
    void* wasm_init();
    int wasm_process(void* app, const uint8_t* input, size_t input_size, uint8_t** output, size_t* output_size);
    void wasm_cleanup(void* app);
    void wasm_free(void* ptr);
}
```

#### src/api.cpp

```cpp
#include "api.h"
#include "error.h"
#include "utils.h"

#include <nlohmann/json.hpp>
#include <cstring>

namespace wasm {

struct WasmApp::Impl {
    Config config;
    bool initialized = false;
    std::vector<uint8_t> data;
    
    Impl() = default;
    
    ~Impl() {
        secure_zero(data);
    }
};

WasmApp::WasmApp() : pimpl_(std::make_unique<Impl>()) {}

WasmApp::~WasmApp() {
    cleanup();
}

bool WasmApp::initialize(const std::string& config_json) {
    try {
        auto json = nlohmann::json::parse(config_json);
        
        if (json.contains("max_size")) {
            pimpl_->config.max_size = json["max_size"].get<size_t>();
        }
        
        if (json.contains("timeout_ms")) {
            pimpl_->config.timeout_ms = json["timeout_ms"].get<uint64_t>();
        }
        
        if (json.contains("debug")) {
            pimpl_->config.debug = json["debug"].get<bool>();
        }
        
        // Validate configuration
        if (pimpl_->config.max_size == 0) {
            throw WasmError("max_size must be greater than 0");
        }
        
        if (pimpl_->config.timeout_ms == 0) {
            throw WasmError("timeout_ms must be greater than 0");
        }
        
        pimpl_->initialized = true;
        
        if (pimpl_->config.debug) {
            log_info("Application initialized");
        }
        
        return true;
    } catch (const std::exception& e) {
        log_error("Initialization failed: " + std::string(e.what()));
        return false;
    }
}

Result WasmApp::process(const uint8_t* input, size_t input_size) {
    if (!pimpl_->initialized) {
        return Result("Application not initialized");
    }
    
    if (input == nullptr || input_size == 0) {
        return Result("Invalid input");
    }
    
    if (input_size > pimpl_->config.max_size) {
        return Result("Input exceeds maximum size");
    }
    
    // Check for suspicious patterns
    if (contains_suspicious_patterns(input, input_size)) {
        return Result("Suspicious patterns detected");
    }
    
    // Process the data
    std::vector<uint8_t> output;
    output.reserve(input_size);
    
    // Example processing
    for (size_t i = 0; i < input_size; ++i) {
        output.push_back(input[i] ^ 0x55);  // Simple XOR
    }
    
    // Verify output size
    if (output.size() > pimpl_->config.max_size) {
        return Result("Output exceeds maximum size");
    }
    
    return Result(std::move(output));
}

std::string WasmApp::get_state() const {
    nlohmann::json json;
    json["max_size"] = pimpl_->config.max_size;
    json["timeout_ms"] = pimpl_->config.timeout_ms;
    json["debug"] = pimpl_->config.debug;
    json["initialized"] = pimpl_->initialized;
    
    return json.dump();
}

void WasmApp::cleanup() {
    secure_zero(pimpl_->data);
    pimpl_->data.clear();
    pimpl_->initialized = false;
}

bool contains_suspicious_patterns(const uint8_t* data, size_t size) {
    const char* patterns[] = {
        "<script",
        "javascript:",
        "onerror=",
        "onload=",
        "eval(",
        "exec("
    };
    
    std::string input(reinterpret_cast<const char*>(data), size);
    std::string lower = input;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    for (const char* pattern : patterns) {
        if (lower.find(pattern) != std::string::npos) {
            return true;
        }
    }
    
    return false;
}

}  // namespace wasm

// C API implementations
extern "C" {

void* wasm_init() {
    try {
        auto app = new wasm::WasmApp();
        return static_cast<void*>(app);
    } catch (...) {
        return nullptr;
    }
}

int wasm_process(void* app, const uint8_t* input, size_t input_size, uint8_t** output, size_t* output_size) {
    if (app == nullptr || input == nullptr || output == nullptr || output_size == nullptr) {
        return -1;
    }
    
    try {
        auto* wasm_app = static_cast<wasm::WasmApp*>(app);
        auto result = wasm_app->process(input, input_size);
        
        if (!result.success) {
            return -2;
        }
        
        *output_size = result.data.size();
        *output = static_cast<uint8_t*>(malloc(*output_size));
        
        if (*output == nullptr) {
            return -3;
        }
        
        memcpy(*output, result.data.data(), *output_size);
        
        return 0;
    } catch (...) {
        return -4;
    }
}

void wasm_cleanup(void* app) {
    if (app != nullptr) {
        auto* wasm_app = static_cast<wasm::WasmApp*>(app);
        wasm_app->cleanup();
        delete wasm_app;
    }
}

void wasm_free(void* ptr) {
    if (ptr != nullptr) {
        free(ptr);
    }
}

}  // extern "C"
```

#### src/memory.h

```cpp
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>
#include <memory>

namespace wasm {

// Secure memory allocation
class SecureAllocator {
public:
    using value_type = uint8_t;
    
    uint8_t* allocate(size_t n) {
        return static_cast<uint8_t*>(::malloc(n));
    }
    
    void deallocate(uint8_t* p, size_t n) {
        secure_zero(p, n);
        ::free(p);
    }
};

// Secure buffer class
class SecureBuffer {
public:
    explicit SecureBuffer(size_t size)
        : data_(static_cast<uint8_t*>(::malloc(size)))
        , size_(size)
        , capacity_(size)
    {
        if (data_ != nullptr) {
            std::memset(data_, 0, size);
        }
    }
    
    ~SecureBuffer() {
        secure_zero();
    }
    
    // Non-copyable
    SecureBuffer(const SecureBuffer&) = delete;
    SecureBuffer& operator=(const SecureBuffer&) = delete;
    
    // Movable
    SecureBuffer(SecureBuffer&& other) noexcept
        : data_(other.data_)
        , size_(other.size_)
        , capacity_(other.capacity_)
    {
        other.data_ = nullptr;
        other.size_ = 0;
        other.capacity_ = 0;
    }
    
    SecureBuffer& operator=(SecureBuffer&& other) noexcept {
        if (this != &other) {
            secure_zero();
            data_ = other.data_;
            size_ = other.size_;
            capacity_ = other.capacity_;
            other.data_ = nullptr;
            other.size_ = 0;
            other.capacity_ = 0;
        }
        return *this;
    }
    
    uint8_t* data() { return data_; }
    const uint8_t* data() const { return data_; }
    size_t size() const { return size_; }
    size_t capacity() const { return capacity_; }
    bool empty() const { return size_ == 0; }
    
    void resize(size_t new_size) {
        if (new_size > capacity_) {
            uint8_t* new_data = static_cast<uint8_t*>(::malloc(new_size));
            if (new_data == nullptr) {
                throw std::bad_alloc();
            }
            if (data_ != nullptr) {
                std::memcpy(new_data, data_, size_);
                secure_zero();
            }
            data_ = new_data;
            capacity_ = new_size;
        }
        size_ = new_size;
    }
    
    void clear() {
        size_ = 0;
    }
    
    void secure_zero() {
        if (data_ != nullptr) {
            volatile uint8_t* p = data_;
            for (size_t i = 0; i < capacity_; ++i) {
                p[i] = 0;
            }
        }
    }

private:
    uint8_t* data_;
    size_t size_;
    size_t capacity_;
};

// Utility function for secure memory zeroing
inline void secure_zero(void* ptr, size_t size) {
    volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
    for (size_t i = 0; i < size; ++i) {
        p[i] = 0;
    }
}

}  // namespace wasm
```

#### src/error.h

```cpp
#pragma once

#include <stdexcept>
#include <string>

namespace wasm {

class WasmError : public std::runtime_error {
public:
    explicit WasmError(const std::string& message)
        : std::runtime_error(message) {}
};

class InvalidInputError : public WasmError {
public:
    explicit InvalidInputError(const std::string& message)
        : WasmError("Invalid input: " + message) {}
};

class SecurityViolationError : public WasmError {
public:
    explicit SecurityViolationError(const std::string& message)
        : WasmError("Security violation: " + message) {}
};

class ResourceLimitError : public WasmError {
public:
    explicit ResourceLimitError(const std::string& message)
        : WasmError("Resource limit: " + message) {}
};

}  // namespace wasm
```

#### src/utils.h

```cpp
#pragma once

#include <cstdint>
#include <string>
#include <chrono>
#include <algorithm>
#include <cctype>

namespace wasm {

// Get current timestamp
inline uint64_t current_timestamp() {
    return static_cast<uint64_t>(
        std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::system_clock::now().time_since_epoch()
        ).count()
    );
}

// Validate string is safe
inline bool validate_string(const std::string& input) {
    std::string lower = input;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    const std::string dangerous_patterns[] = {
        "<script", "javascript:", "onerror=", "onload=",
        "eval(", "exec(", "drop table", "delete from"
    };
    
    for (const auto& pattern : dangerous_patterns) {
        if (lower.find(pattern) != std::string::npos) {
            return false;
        }
    }
    
    return true;
}

// Sanitize string
inline std::string sanitize_string(const std::string& input) {
    std::string result;
    result.reserve(input.size());
    
    for (char c : input) {
        if (std::isalnum(c) || c == ' ' || c == '_' || c == '-') {
            result.push_back(c);
        }
    }
    
    return result;
}

// Truncate string
inline std::string truncate_string(const std::string& input, size_t max_len) {
    if (input.size() <= max_len) {
        return input;
    }
    return input.substr(0, max_len - 3) + "...";
}

// Logging functions
inline void log_info(const std::string& message) {
    #ifdef __EMSCRIPTEN__
    // In WASM, logging goes to console
    emscripten_log(EM_LOG_CONSOLE, "[INFO] %s", message.c_str());
    #else
    std::cout << "[INFO] " << message << std::endl;
    #endif
}

inline void log_error(const std::string& message) {
    #ifdef __EMSCRIPTEN__
    emscripten_log(EM_LOG_CONSOLE | EM_LOG_ERROR, "[ERROR] %s", message.c_str());
    #else
    std::cerr << "[ERROR] " << message << std::endl;
    #endif
}

}  // namespace wasm
```

---

## 17.6 CI/CD Pipeline Template

### Pipeline Completo

```yaml
# .github/workflows/wasm-security.yml
name: WASM Security Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly scan

env:
  RUST_VERSION: '1.75.0'
  WASM_TARGET: 'wasm32-wasi'

jobs:
  # Stage 1: Code Quality
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: ${{ env.RUST_VERSION }}
          targets: ${{ env.WASM_TARGET }}

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Check formatting
        run: cargo fmt --check

      - name: Run clippy
        run: cargo clippy --all-targets --all-features -- -D warnings

      - name: Check for vulnerabilities
        run: |
          cargo install cargo-audit
          cargo audit

  # Stage 2: Security Scanning
  security-scan:
    runs-on: ubuntu-latest
    needs: code-quality
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: p/rust

  # Stage 3: Build and Test
  build-test:
    runs-on: ubuntu-latest
    needs: security-scan
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: ${{ env.RUST_VERSION }}
          targets: ${{ env.WASM_TARGET }}

      - name: Install wasm-pack
        run: curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

      - name: Build WASM
        run: wasm-pack build --target web --release

      - name: Run unit tests
        run: cargo test

      - name: Run WASM tests
        run: wasm-pack test --headless --chrome

      - name: Run property tests
        run: cargo test --features proptest

      - name: Run benchmarks
        run: cargo bench

  # Stage 4: WASM Security Analysis
  wasm-security:
    runs-on: ubuntu-latest
    needs: build-test
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: ${{ env.RUST_VERSION }}
          targets: ${{ env.WASM_TARGET }}

      - name: Install wasm-opt
        run: |
          curl -L https://github.com/WebAssembly/binaryen/releases/download/version_111/binaryen-version_111-x86_64-linux.tar.gz | tar xz
          sudo mv binaryen-version_111/bin/wasm-opt /usr/local/bin/

      - name: Optimize WASM
        run: wasm-opt -O3 -g target/wasm32-wasi/release/*.wasm -o optimized.wasm

      - name: Analyze WASM size
        run: |
          echo "WASM Size Analysis"
          ls -lh optimized.wasm
          wasm-strip optimized.wasm
          echo "After stripping:"
          ls -lh optimized.wasm

      - name: Run WASM security checks
        run: |
          # Check for dangerous imports
          wasm-objdump -j Import -x optimized.wasm | grep -E "(env|wasi)" || true
          
          # Check exports
          wasm-objdump -j Export -x optimized.wasm

      - name: Upload WASM artifact
        uses: actions/upload-artifact@v3
        with:
          name: wasm-build
          path: optimized.wasm

  # Stage 5: Compliance Check
  compliance:
    runs-on: ubuntu-latest
    needs: wasm-security
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Check NIST compliance
        run: |
          echo "Checking NIST SP 800-53 controls..."
          # Add compliance checks here

      - name: Check OWASP Top 10
        run: |
          echo "Checking OWASP Wasm Top 10..."
          # Add OWASP checks here

      - name: Generate compliance report
        run: |
          echo "Generating compliance report..."
          # Generate report

  # Stage 6: Deploy (only on main)
  deploy:
    runs-on: ubuntu-latest
    needs: [build-test, wasm-security, compliance]
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download WASM artifact
        uses: actions/download-artifact@v3
        with:
          name: wasm-build

      - name: Deploy to production
        run: |
          echo "Deploying WASM module..."
          # Add deployment steps here

      - name: Notify deployment
        run: |
          echo "Deployment completed successfully"
          # Add notification steps here
```

---

## 17.7 Monitoring Template

### Sistema de Monitoramento

```rust
// monitoring/src/lib.rs
pub struct WasmMonitor {
    metrics: MetricsCollector,
    alerts: AlertManager,
    health: HealthChecker,
}

pub struct MetricsCollector {
    counters: HashMap<String, AtomicU64>,
    gauges: HashMap<String, Mutex<f64>>,
    histograms: HashMap<String, Mutex<Vec<f64>>>,
}

pub struct AlertManager {
    rules: Vec<AlertRule>,
    channels: Vec<Box<dyn AlertChannel>>,
}

pub struct HealthChecker {
    checks: Vec<Box<dyn HealthCheck>>,
    interval: Duration,
}

pub struct AlertRule {
    name: String,
    condition: AlertCondition,
    severity: AlertSeverity,
    enabled: bool,
}

pub enum AlertCondition {
    GreaterThan(f64),
    LessThan(f64),
    Equals(f64),
    NotEquals(f64),
}

pub enum AlertSeverity {
    Info,
    Warning,
    Critical,
}

pub trait AlertChannel: Send + Sync {
    fn send(&self, alert: &Alert);
}

pub trait HealthCheck: Send + Sync {
    fn name(&self) -> &str;
    fn check(&self) -> HealthStatus;
}

pub enum HealthStatus {
    Healthy,
    Degraded,
    Unhealthy,
}

pub struct Alert {
    timestamp: u64,
    rule: String,
    severity: AlertSeverity,
    message: String,
    metrics: HashMap<String, f64>,
}

impl WasmMonitor {
    pub fn new() -> Self {
        Self {
            metrics: MetricsCollector::new(),
            alerts: AlertManager::new(),
            health: HealthChecker::new(),
        }
    }

    pub fn record_counter(&self, name: &str, value: u64) {
        self.metrics.increment_counter(name, value);
    }

    pub fn record_gauge(&self, name: &str, value: f64) {
        self.metrics.set_gauge(name, value);
    }

    pub fn record_histogram(&self, name: &str, value: f64) {
        self.metrics.record_histogram(name, value);
    }

    pub fn evaluate_alerts(&self) -> Vec<Alert> {
        self.alerts.evaluate(&self.metrics)
    }

    pub fn check_health(&self) -> Vec<HealthCheckResult> {
        self.health.check_all()
    }
}

impl MetricsCollector {
    pub fn new() -> Self {
        Self {
            counters: HashMap::new(),
            gauges: HashMap::new(),
            histograms: HashMap::new(),
        }
    }

    pub fn increment_counter(&self, name: &str, value: u64) {
        self.counters
            .entry(name.to_string())
            .or_insert_with(|| AtomicU64::new(0))
            .fetch_add(value, Ordering::Relaxed);
    }

    pub fn set_gauge(&self, name: &str, value: f64) {
        *self.gauges
            .entry(name.to_string())
            .or_insert_with(|| Mutex::new(0.0))
            .lock()
            .unwrap() = value;
    }

    pub fn record_histogram(&self, name: &str, value: f64) {
        self.histograms
            .entry(name.to_string())
            .or_insert_with(|| Mutex::new(Vec::new()))
            .lock()
            .unwrap()
            .push(value);
    }

    pub fn get_counter(&self, name: &str) -> u64 {
        self.counters
            .get(name)
            .map(|c| c.load(Ordering::Relaxed))
            .unwrap_or(0)
    }

    pub fn get_gauge(&self, name: &str) -> f64 {
        self.gauges
            .get(name)
            .map(|g| *g.lock().unwrap())
            .unwrap_or(0.0)
    }

    pub fn get_histogram_stats(&self, name: &str) -> Option<HistogramStats> {
        self.histograms.get(name).map(|h| {
            let values = h.lock().unwrap();
            if values.is_empty() {
                return HistogramStats::default();
            }

            let mut sorted = values.clone();
            sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());

            HistogramStats {
                count: sorted.len(),
                sum: sorted.iter().sum(),
                min: sorted[0],
                max: sorted[sorted.len() - 1],
                mean: sorted.iter().sum::<f64>() / sorted.len() as f64,
                median: sorted[sorted.len() / 2],
                p95: sorted[(sorted.len() as f64 * 0.95) as usize],
                p99: sorted[(sorted.len() as f64 * 0.99) as usize],
            }
        })
    }
}

#[derive(Default)]
pub struct HistogramStats {
    pub count: usize,
    pub sum: f64,
    pub min: f64,
    pub max: f64,
    pub mean: f64,
    pub median: f64,
    pub p95: f64,
    pub p99: f64,
}

pub struct HealthCheckResult {
    pub name: String,
    pub status: HealthStatus,
    pub message: String,
    pub timestamp: u64,
}

impl HealthChecker {
    pub fn new() -> Self {
        Self {
            checks: Vec::new(),
            interval: Duration::from_secs(30),
        }
    }

    pub fn add_check(&mut self, check: Box<dyn HealthCheck>) {
        self.checks.push(check);
    }

    pub fn check_all(&self) -> Vec<HealthCheckResult> {
        self.checks.iter().map(|check| {
            let status = check.check();
            HealthCheckResult {
                name: check.name().to_string(),
                status,
                message: String::new(),
                timestamp: current_timestamp(),
            }
        }).collect()
    }
}

fn current_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}
```

---

## 17.8 Performance Optimization Guide

### Guia de Otimização

```rust
// optimization/src/lib.rs

// 1. Usar WASM features corretamente
#[cfg(target_arch = "wasm32")]
mod wasm_optimizations {
    // Usar SIMD para processamento paralelo
    #[cfg(target_feature = "simd128")]
    pub fn simd_process(data: &[f32]) -> Vec<f32> {
        use std::arch::wasm32::*;
        
        data.chunks(4)
            .map(|chunk| {
                let v = unsafe { f32x4_new(chunk[0], chunk[1], chunk[2], chunk[3]) };
                let result = unsafe { f32x4_mul(v, f32x4_splat(2.0)) };
                vec![
                    unsafe { f32x4_extract_lane::<0>(result) },
                    unsafe { f32x4_extract_lane::<1>(result) },
                    unsafe { f32x4_extract_lane::<2>(result) },
                    unsafe { f32x4_extract_lane::<3>(result) },
                ]
            })
            .flatten()
            .collect()
    }

    // Usar threads quando disponível
    #[cfg(target_feature = "atomics")]
    pub fn parallel_process(data: &[u8]) -> Vec<u8> {
        use std::thread;
        
        let chunk_size = data.len() / num_cpus::get();
        let chunks: Vec<_> = data.chunks(chunk_size).collect();
        
        let handles: Vec<_> = chunks.into_iter()
            .map(|chunk| {
                thread::spawn(move || {
                    chunk.iter().map(|b| b.wrapping_add(1)).collect::<Vec<_>>()
                })
            })
            .collect();
        
        handles.into_iter()
            .flat_map(|h| h.join().unwrap())
            .collect()
    }
}

// 2. Otimizações de memória
pub struct MemoryOptimizedBuffer {
    data: Vec<u8>,
    capacity: usize,
}

impl MemoryOptimizedBuffer {
    pub fn new(initial_capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(initial_capacity),
            capacity: initial_capacity,
        }
    }

    pub fn with_capacity(capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(capacity),
            capacity,
        }
    }

    // Reutilizar buffer em vez de alocar novo
    pub fn clear_and_reuse(&mut self) {
        self.data.clear();
    }

    // Pré-alocar memória
    pub fn ensure_capacity(&mut self, additional: usize) {
        let new_len = self.data.len() + additional;
        if new_len > self.capacity {
            self.data.reserve(new_len - self.capacity);
            self.capacity = new_len;
        }
    }
}

// 3. Otimizações de processamento
pub struct ProcessingOptimizer {
    chunk_size: usize,
    parallel: bool,
}

impl ProcessingOptimizer {
    pub fn new() -> Self {
        Self {
            chunk_size: 1024,
            parallel: false,
        }
    }

    pub fn with_chunk_size(chunk_size: usize) -> Self {
        Self {
            chunk_size,
            parallel: false,
        }
    }

    pub fn with_parallel(parallel: bool) -> Self {
        Self {
            chunk_size: 1024,
            parallel,
        }
    }

    pub fn process(&self, data: &[u8]) -> Vec<u8> {
        if self.parallel {
            self.process_parallel(data)
        } else {
            self.process_sequential(data)
        }
    }

    fn process_sequential(&self, data: &[u8]) -> Vec<u8> {
        data.chunks(self.chunk_size)
            .flat_map(|chunk| self.process_chunk(chunk))
            .collect()
    }

    fn process_parallel(&self, data: &[u8]) -> Vec<u8> {
        // Use rayon for parallel processing in native builds
        // For WASM, fall back to sequential
        #[cfg(not(target_arch = "wasm32"))]
        {
            use rayon::prelude::*;
            data.par_chunks(self.chunk_size)
                .flat_map(|chunk| self.process_chunk(chunk))
                .collect()
        }

        #[cfg(target_arch = "wasm32")]
        {
            self.process_sequential(data)
        }
    }

    fn process_chunk(&self, chunk: &[u8]) -> Vec<u8> {
        chunk.iter().map(|b| b.wrapping_add(1)).collect()
    }
}

// 4. Benchmarks
#[cfg(test)]
mod benchmarks {
    use super::*;
    use criterion::{black_box, criterion_group, criterion_main, Criterion};

    fn benchmark_sequential(c: &mut Criterion) {
        let data = vec![0u8; 1024 * 1024]; // 1MB
        let optimizer = ProcessingOptimizer::new();

        c.bench_function("sequential_process", |b| {
            b.iter(|| optimizer.process(black_box(&data)))
        });
    }

    fn benchmark_parallel(c: &mut Criterion) {
        let data = vec![0u8; 1024 * 1024]; // 1MB
        let optimizer = ProcessingOptimizer::with_parallel(true);

        c.bench_function("parallel_process", |b| {
            b.iter(|| optimizer.process(black_box(&data)))
        });
    }

    criterion_group!(benches, benchmark_sequential, benchmark_parallel);
    criterion_main!(benches);
}
```

---

## 17.9 Migration Guide from Legacy to Wasm

### Guia de Migração

```rust
// migration/src/lib.rs

pub struct MigrationGuide {
    pub phases: Vec<MigrationPhase>,
    pub checklist: MigrationChecklist,
}

pub struct MigrationPhase {
    pub name: String,
    pub description: String,
    pub steps: Vec<MigrationStep>,
    pub estimated_time: String,
    pub risks: Vec<String>,
}

pub struct MigrationStep {
    pub name: String,
    pub description: String,
    pub commands: Vec<String>,
    pub verification: String,
}

pub struct MigrationChecklist {
    pub pre_migration: Vec<CheckItem>,
    pub during_migration: Vec<CheckItem>,
    pub post_migration: Vec<CheckItem>,
}

pub struct CheckItem {
    pub id: String,
    pub description: String,
    pub status: CheckStatus,
}

pub enum CheckStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

impl MigrationGuide {
    pub fn new() -> Self {
        Self {
            phases: Self::define_phases(),
            checklist: MigrationChecklist::new(),
        }
    }

    fn define_phases() -> Vec<MigrationPhase> {
        vec![
            MigrationPhase {
                name: "Phase 1: Assessment".to_string(),
                description: "Evaluate current codebase and identify migration candidates".to_string(),
                steps: vec![
                    MigrationStep {
                        name: "Code Analysis".to_string(),
                        description: "Analyze existing code for WASM compatibility".to_string(),
                        commands: vec![
                            "cargo tree --depth 1".to_string(),
                            "grep -r 'unsafe' src/".to_string(),
                        ],
                        verification: "All unsafe blocks identified".to_string(),
                    },
                    MigrationStep {
                        name: "Dependency Audit".to_string(),
                        description: "Check dependencies for WASM support".to_string(),
                        commands: vec![
                            "cargo audit".to_string(),
                        ],
                        verification: "All dependencies are WASM-compatible".to_string(),
                    },
                ],
                estimated_time: "1-2 days".to_string(),
                risks: vec![
                    "Incompatible dependencies".to_string(),
                    "Unsafe code blocks".to_string(),
                ],
            },
            MigrationPhase {
                name: "Phase 2: Preparation".to_string(),
                description: "Set up WASM toolchain and project structure".to_string(),
                steps: vec![
                    MigrationStep {
                        name: "Install Toolchain".to_string(),
                        description: "Install Rust WASM toolchain".to_string(),
                        commands: vec![
                            "rustup target add wasm32-wasi".to_string(),
                            "cargo install wasm-pack".to_string(),
                        ],
                        verification: "Toolchain installed correctly".to_string(),
                    },
                    MigrationStep {
                        name: "Create WASM Project".to_string(),
                        description: "Set up new WASM project structure".to_string(),
                        commands: vec![
                            "cargo new --lib wasm-project".to_string(),
                            "cd wasm-project".to_string(),
                        ],
                        verification: "Project builds successfully".to_string(),
                    },
                ],
                estimated_time: "1 day".to_string(),
                risks: vec![
                    "Toolchain version conflicts".to_string(),
                ],
            },
            MigrationPhase {
                name: "Phase 3: Migration".to_string(),
                description: "Migrate code incrementally".to_string(),
                steps: vec![
                    MigrationStep {
                        name: "Core Logic Migration".to_string(),
                        description: "Migrate core business logic first".to_string(),
                        commands: vec![
                            "cp -r src/core wasm-project/src/".to_string(),
                            "cargo build --target wasm32-wasi".to_string(),
                        ],
                        verification: "Core logic compiles for WASM".to_string(),
                    },
                    MigrationStep {
                        name: "API Layer".to_string(),
                        description: "Create WASM-compatible API layer".to_string(),
                        commands: vec![
                            "Add wasm-bindgen dependencies".to_string(),
                            "Create FFI exports".to_string(),
                        ],
                        verification: "API exports work correctly".to_string(),
                    },
                ],
                estimated_time: "1-2 weeks".to_string(),
                risks: vec![
                    "Breaking changes".to_string(),
                    "Performance regression".to_string(),
                ],
            },
            MigrationPhase {
                name: "Phase 4: Testing".to_string(),
                description: "Comprehensive testing of WASM module".to_string(),
                steps: vec![
                    MigrationStep {
                        name: "Unit Tests".to_string(),
                        description: "Run all unit tests in WASM".to_string(),
                        commands: vec![
                            "wasm-pack test --headless --chrome".to_string(),
                        ],
                        verification: "All tests pass".to_string(),
                    },
                    MigrationStep {
                        name: "Integration Tests".to_string(),
                        description: "Test integration with host environment".to_string(),
                        commands: vec![
                            "npm test".to_string(),
                        ],
                        verification: "Integration tests pass".to_string(),
                    },
                ],
                estimated_time: "3-5 days".to_string(),
                risks: vec![
                    "Platform-specific behavior".to_string(),
                    "Memory issues".to_string(),
                ],
            },
            MigrationPhase {
                name: "Phase 5: Deployment".to_string(),
                description: "Deploy WASM module to production".to_string(),
                steps: vec![
                    MigrationStep {
                        name: "Build Production".to_string(),
                        description: "Build optimized WASM module".to_string(),
                        commands: vec![
                            "wasm-pack build --release".to_string(),
                            "wasm-opt -O3 *.wasm".to_string(),
                        ],
                        verification: "Module size is acceptable".to_string(),
                    },
                    MigrationStep {
                        name: "Deploy".to_string(),
                        description: "Deploy to production environment".to_string(),
                        commands: vec![
                            "npm publish".to_string(),
                        ],
                        verification: "Module works in production".to_string(),
                    },
                ],
                estimated_time: "1-2 days".to_string(),
                risks: vec![
                    "Deployment failures".to_string(),
                    "Performance issues in production".to_string(),
                ],
            },
        ]
    }
}

impl MigrationChecklist {
    pub fn new() -> Self {
        Self {
            pre_migration: vec![
                CheckItem {
                    id: "PRE-001".to_string(),
                    description: "Backup existing code".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "PRE-002".to_string(),
                    description: "Document current architecture".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "PRE-003".to_string(),
                    description: "Identify migration candidates".to_string(),
                    status: CheckStatus::Pending,
                },
            ],
            during_migration: vec![
                CheckItem {
                    id: "DUR-001".to_string(),
                    description: "Maintain test coverage".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "DUR-002".to_string(),
                    description: "Regular builds and tests".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "DUR-003".to_string(),
                    description: "Code reviews for all changes".to_string(),
                    status: CheckStatus::Pending,
                },
            ],
            post_migration: vec![
                CheckItem {
                    id: "POST-001".to_string(),
                    description: "Performance benchmarking".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "POST-002".to_string(),
                    description: "Security audit".to_string(),
                    status: CheckStatus::Pending,
                },
                CheckItem {
                    id: "POST-003".to_string(),
                    description: "Documentation update".to_string(),
                    status: CheckStatus::Pending,
                },
            ],
        }
    }
}
```

---

## Resumo

Este capítulo apresentou um guia abrangente de boas práticas para WebAssembly:

### Anti-Patterns
- 23 anti-patterns comuns e suas soluções
- Cobertura de memória, segurança, tratamento de erros e mais

### Security Checklist
- Checklist completo com 10 categorias
- Prioridades e status para cada item

### Decision Trees
- Árvore de decisão para escolher runtime
- Árvore de decisão para escolher linguagem

### Templates de Projeto
- Template completo para Rust+Wasm
- Template completo para C++/Emscripten
- Estrutura de diretórios e configurações

### CI/CD Pipeline
- Pipeline completo com 6 estágios
- Integração com ferramentas de segurança

### Monitoramento
- Sistema de monitoramento com métricas e alertas
- Health checks e dashboards

### Otimização de Performance
- Técnicas de otimização para WASM
- Benchmarks e profiling

### Guia de Migração
- Guia passo a passo para migrar de sistemas legados
- Checklist de migração

Seguir essas boas práticas é essencial para construir aplicações WebAssembly seguras, performáticas e manuteníveis.

---

## Próximos Passos

Com as boas práticas e checklists definidos, você está pronto para desenvolver aplicações WebAssembly seguras e eficientes. Lembre-se de:

1. Sempre começar com o checklist de segurança
2. Usar as árvores de decisão para escolher as tecnologias certas
3. Seguir os templates de projeto como ponto de partida
4. Implementar CI/CD desde o início
5. Monitorar continuamente em produção

O desenvolvimento seguro é uma jornada contínua, não um destino. Mantenha-se atualizado com as melhores práticas e sempre busque melhorar.
---

*[Capítulo anterior: 16 — Compliance](16-compliance.md)*

