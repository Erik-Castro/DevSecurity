# Capítulo 14: Wasm no Edge Computing

## Introdução

O edge computing representa uma revolução na arquitetura de aplicações distribuídas, aproximando o processamento dos usuários finais para reduzir latência e melhorar a experiência do usuário. O WebAssembly emergiu como uma tecnologia fundamental para o edge computing, oferecendo execução segura e performática em ambientes distribuídos com recursos limitados.

Diferente da computação em nuvem tradicional, onde as aplicações rodam em data centers centralizados, o edge computing distribui a computação para pontos de presença (PoPs) geograficamente dispersos. Isso cria desafios únicos: recursos limitados, necessidade de冷启动 rápido, segurança em ambientes distribuídos e gerenciamento de estado.

O WebAssembly aborda esses desafios com sua arquitetura leve, inicialização rápida e modelo de segurança sandboxed. Plataformas como Cloudflare Workers, Fastly Compute e Fermyon Spin já utilizam WASM como base para suas plataformas de edge computing, demonstrando a viabilidade e benefícios dessa abordagem.

Vamos explorar como cada plataforma implementa WASM no edge, as técnicas para otimizar冷启动, gerenciar estado distribuído e garantir segurança em ambientes edge.

---

## 14.1 Cloudflare Workers Architecture

### Visão Geral da Arquitetura

O Cloudflare Workers é uma das plataformas de edge computing mais maduras, processando bilhões de solicitações diárias usando V8 isolates com suporte a WebAssembly. A arquitetura do Workers distribui código para mais de 300 cidades ao redor do mundo, executando funções em milissegundos.

### Estrutura Básica de um Worker com WASM

```typescript
// cloudflare-worker/src/index.ts
export interface Env {
  WASM_MODULE: WebAssembly.Module;
  CACHE_KV: KVNamespace;
  RATE_LIMITER: RateLimit;
  ANALYTICS: AnalyticsEngine;
  ENVIRONMENT: string;
}

interface SecurityHeaders {
  [key: string]: string;
}

interface RateLimitResult {
  success: boolean;
  limit: number;
  remaining: number;
  reset: number;
}

export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    const startTime = Date.now();
    
    try {
      // Security validation
      const securityCheck = await validateRequest(request, env);
      if (!securityCheck.valid) {
        return new Response(securityCheck.error, { status: 403 });
      }
      
      // Rate limiting
      const rateLimitResult = await checkRateLimit(request, env);
      if (!rateLimitResult.success) {
        return new Response('Rate limit exceeded', {
          status: 429,
          headers: {
            'X-RateLimit-Limit': rateLimitResult.limit.toString(),
            'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
            'X-RateLimit-Reset': rateLimitResult.reset.toString(),
            'Retry-After': Math.ceil((rateLimitResult.reset - Date.now()) / 1000).toString(),
          },
        });
      }
      
      // Initialize WASM module
      const wasmInstance = await initializeWasm(env.WASM_MODULE);
      
      // Process request based on method and path
      const url = new URL(request.url);
      const response = await processRequest(request, wasmInstance, env, ctx);
      
      // Add security headers
      const securityHeaders = getSecurityHeaders(env.ENVIRONMENT);
      Object.entries(securityHeaders).forEach(([key, value]) => {
        response.headers.set(key, value);
      });
      
      // Add performance headers
      const duration = Date.now() - startTime;
      response.headers.set('X-Response-Time', `${duration}ms`);
      response.headers.set('X-Edge-Location', request.cf?.colo || 'unknown');
      
      // Analytics
      ctx.waitUntil(
        env.ANALYTICS.writeDataPoint({
          blobs: [request.url, request.method],
          doubles: [duration, response.status],
        })
      );
      
      return response;
    } catch (error) {
      console.error('Worker error:', error);
      return new Response('Internal Server Error', { status: 500 });
    }
  },
};

async function validateRequest(
  request: Request,
  env: Env
): Promise<{ valid: boolean; error?: string }> {
  // Check for malicious patterns
  const url = new URL(request.url);
  
  const blockedPatterns = [
    /\.\./,  // Path traversal
    /<script/i,  // XSS attempts
    /union\s+select/i,  // SQL injection
    /javascript:/i,  // Protocol handlers
  ];
  
  for (const pattern of blockedPatterns) {
    if (pattern.test(url.pathname) || pattern.test(url.search)) {
      return { valid: false, error: 'Malicious request detected' };
    }
  }
  
  // Check Content-Length for oversized requests
  const contentLength = request.headers.get('content-length');
  if (contentLength && parseInt(contentLength) > 10 * 1024 * 1024) {
    return { valid: false, error: 'Request too large' };
  }
  
  return { valid: true };
}

async function checkRateLimit(
  request: Request,
  env: Env
): Promise<RateLimitResult> {
  const ip = request.headers.get('cf-connecting-ip') || 'unknown';
  const key = `rate:${ip}`;
  
  const { success, limit, remaining, reset } = await env.RATE_LIMITER.limit({
    key,
  });
  
  return { success, limit, remaining, reset };
}

async function initializeWasm(
  module: WebAssembly.Module
): Promise<WebAssembly.Instance> {
  const memory = new WebAssembly.Memory({ initial: 256, maximum: 1024 });
  
  const imports = {
    env: {
      memory,
      log: (ptr: number, len: number) => {
        // Read string from WASM memory
        const buffer = new Uint8Array(memory.buffer);
        const bytes = buffer.slice(ptr, ptr + len);
        const text = new TextDecoder().decode(bytes);
        console.log('[WASM]', text);
      },
      performance_now: () => performance.now(),
      random_bytes: (ptr: number, len: number) => {
        const buffer = new Uint8Array(memory.buffer);
        const randomValues = crypto.getRandomValues(new Uint8Array(len));
        buffer.set(randomValues, ptr);
      },
    },
  };
  
  return WebAssembly.instantiate(module, imports);
}

async function processRequest(
  request: Request,
  wasmInstance: WebAssembly.Instance,
  env: Env,
  ctx: ExecutionContext
): Promise<Response> {
  const url = new URL(request.url);
  const exports = wasmInstance.exports as any;
  
  // Route based on path
  switch (true) {
    case url.pathname.startsWith('/api/data'):
      return handleDataRequest(request, wasmInstance, env, ctx);
    
    case url.pathname.startsWith('/api/transform'):
      return handleTransformRequest(request, wasmInstance, env);
    
    case url.pathname.startsWith('/api/validate'):
      return handleValidationRequest(request, wasmInstance, env);
    
    case url.pathname === '/health':
      return new Response(JSON.stringify({ status: 'healthy' }), {
        headers: { 'Content-Type': 'application/json' },
      });
    
    default:
      return new Response('Not Found', { status: 404 });
  }
}

async function handleDataRequest(
  request: Request,
  wasmInstance: WebAssembly.Instance,
  env: Env,
  ctx: ExecutionContext
): Promise<Response> {
  const cacheKey = new URL(request.url).pathname + new URL(request.url).search;
  
  // Check cache first
  const cached = await env.CACHE_KV.get(cacheKey, 'json');
  if (cached) {
    return new Response(JSON.stringify(cached), {
      headers: { 'Content-Type': 'application/json', 'X-Cache': 'HIT' },
    });
  }
  
  // Process with WASM
  const exports = wasmInstance.exports as any;
  const result = exports.process_data(0, 0);
  
  // Cache result
  ctx.waitUntil(
    env.CACHE_KV.put(cacheKey, JSON.stringify(result), {
      expirationTtl: 300, // 5 minutes
    })
  );
  
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json', 'X-Cache': 'MISS' },
  });
}

async function handleTransformRequest(
  request: Request,
  wasmInstance: WebAssembly.Instance,
  env: Env
): Promise<Response> {
  if (request.method !== 'POST') {
    return new Response('Method not allowed', { status: 405 });
  }
  
  const body = await request.text();
  const exports = wasmInstance.exports as any;
  
  // Write input to WASM memory
  const inputPtr = exports.allocate(body.length);
  const memory = new Uint8Array(
    (wasmInstance.exports.memory as WebAssembly.Memory).buffer
  );
  memory.set(new TextEncoder().encode(body), inputPtr);
  
  // Transform
  const outputPtr = exports.transform(inputPtr, body.length);
  const outputLen = exports.get_output_length();
  
  // Read output
  const output = new TextDecoder().decode(
    memory.slice(outputPtr, outputPtr + outputLen)
  );
  
  // Clean up
  exports.deallocate(inputPtr, body.length);
  exports.deallocate(outputPtr, outputLen);
  
  return new Response(output, {
    headers: { 'Content-Type': 'application/json' },
  });
}

async function handleValidationRequest(
  request: Request,
  wasmInstance: WebAssembly.Instance,
  env: Env
): Promise<Response> {
  const url = new URL(request.url);
  const data = url.searchParams.get('data') || '';
  
  const exports = wasmInstance.exports as any;
  const isValid = exports.validate_input(data.length) === 1;
  
  return new Response(
    JSON.stringify({ valid: isValid, input: data }),
    {
      headers: { 'Content-Type': 'application/json' },
    }
  );
}

function getSecurityHeaders(environment: string): SecurityHeaders {
  const headers: SecurityHeaders = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  };
  
  if (environment === 'production') {
    headers['Strict-Transport-Security'] =
      'max-age=31536000; includeSubDomains; preload';
    headers['Content-Security-Policy'] =
      "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";
  }
  
  return headers;
}
```

### Configuração do wrangler.toml

```toml
# wrangler.toml
name = "wasm-edge-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"
compatibility_flags = ["nodejs_compat"]

[vars]
ENVIRONMENT = "production"

[[wasm_modules]]
binding = "WASM_MODULE"
path = "./pkg/processor.wasm"

[[kv_namespaces]]
binding = "CACHE_KV"
id = "cache-kv-id"
preview_id = "cache-kv-preview-id"

[[unsafe.bindings]]
name = "RATE_LIMITER"
type = "ratelimit"
namespace_id = "rate-limit-namespace-id"
simple = { limit = 100, period = 60 }

[[analytics_engine_datasets]]
binding = "ANALYTICS"
dataset = "worker-analytics"

[build]
command = "cargo build --target wasm32-unknown-unknown --release"

[build.upload]
format = "modules"
dir = "pkg"
binding = "WASM_MODULE"
```

---

## 14.2 Fastly Compute

### Arquitetura do Fastly Compute

O Fastly Compute é uma plataforma de edge computing que utiliza WebAssembly nativamente, oferecendo execução próxima ao edge com performance excepcional.

### Aplicação Fastly Compute com WASM

```rust
// fastly-compute/src/main.rs
use fastly::error::Error;
use fastly::{mime, Request, Response};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct ApiRequest {
    action: String,
    data: String,
    metadata: HashMap<String, String>,
}

#[derive(Serialize, Deserialize)]
struct ApiResponse {
    success: bool,
    result: Option<serde_json::Value>,
    error: Option<String>,
    timing: TimingInfo,
}

#[derive(Serialize, Deserialize)]
struct TimingInfo {
    total_ms: f64,
    wasm_init_ms: f64,
    processing_ms: f64,
}

#[fastly::main]
fn main(req: Request) -> Result<Response, Error> {
    let start_time = std::time::Instant::now();
    
    // Security validation
    validate_request(&req)?;
    
    // Rate limiting using edge cache
    check_rate_limit(&req)?;
    
    // Initialize WASM module
    let wasm_start = std::time::Instant::now();
    let wasm_instance = initialize_wasm()?;
    let wasm_init_ms = wasm_start.elapsed().as_secs_f64() * 1000.0;
    
    // Route request
    let path = req.get_path().to_string();
    let method = req.get_method().clone();
    
    let mut response = match (method.as_str(), path.as_str()) {
        ("GET", "/api/health") => handle_health_check(),
        
        ("POST", "/api/process") => {
            let process_start = std::time::Instant::now();
            let result = handle_process_request(req, &wasm_instance)?;
            let processing_ms = process_start.elapsed().as_secs_f64() * 1000.0;
            
            let total_ms = start_time.elapsed().as_secs_f64() * 1000.0;
            
            let api_response = ApiResponse {
                success: true,
                result: Some(serde_json::to_value(result)?),
                error: None,
                timing: TimingInfo {
                    total_ms,
                    wasm_init_ms,
                    processing_ms,
                },
            };
            
            Response::from_body(serde_json::to_string(&api_response)?)
                .with_content_type(mime::APPLICATION_JSON)
        }
        
        ("GET", path) if path.starts_with("/api/data/") => {
            let id = path.trim_start_matches("/api/data/");
            handle_data_request(id, &wasm_instance)?
        }
        
        _ => Response::from_status(404)
            .with_body_text_plain("Not Found"),
    };
    
    // Add security headers
    response = add_security_headers(response);
    
    // Add timing headers
    let total_ms = start_time.elapsed().as_secs_f64() * 1000.0;
    response.set_header("X-Response-Time", format!("{}ms", total_ms));
    response.set_header("X-Edge-Location", get_edge_location());
    
    Ok(response)
}

fn validate_request(req: &Request) -> Result<(), Error> {
    // Check for malicious patterns
    let path = req.get_path();
    let query = req.get_query_str().unwrap_or("");
    
    let blocked_patterns = [
        r"\.\.",
        r"<script",
        r"union\s+select",
        r"javascript:",
        r"eval\(",
    ];
    
    for pattern in &blocked_patterns {
        if regex::Regex::new(pattern)
            .unwrap()
            .is_match(path)
            || regex::Regex::new(pattern)
                .unwrap()
                .is_match(query)
        {
            return Err(Error::msg("Malicious request detected"));
        }
    }
    
    // Check content length
    if let Some(content_length) = req.get_header("content-length") {
        let length: usize = content_length.to_str()?.parse()?;
        if length > 10 * 1024 * 1024 {
            return Err(Error::msg("Request too large"));
        }
    }
    
    Ok(())
}

fn check_rate_limit(req: &Request) -> Result<(), Error> {
    let client_ip = req
        .get_header("fastly-client-ip")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("unknown");
    
    let cache_key = format!("rate_limit:{}", client_ip);
    
    // Check if rate limit exists in cache
    let cache = fastly::CacheHandle::open("rate_limit_cache");
    
    if let Some(entry) = cache.lookup(&cache_key) {
        let count: u32 = entry.text()?.parse()?;
        if count >= 100 {
            return Err(Error::msg("Rate limit exceeded"));
        }
        
        // Increment counter
        cache.insert(&cache_key, &(count + 1).to_string())?;
    } else {
        // First request, initialize counter
        cache.insert(&cache_key, "1")?;
    }
    
    Ok(())
}

fn initialize_wasm() -> Result<WebAssemblyInstance, Error> {
    // Load WASM module from configuration
    let wasm_bytes = include_bytes!("../pkg/processor.wasm");
    
    let memory = WebAssembly::Memory::new(WebAssembly::MemoryDescriptor {
        initial: 256,
        maximum: Some(1024),
        shared: false,
    })?;
    
    let imports = WebAssembly::Imports::new();
    imports.register(
        "env",
        WebAssembly::Extern::Memory(WebAssembly::Extern::Memory(memory)),
    );
    
    let module = WebAssembly::Module::from_binary(wasm_bytes)?;
    let instance = WebAssembly::Instance::new(&module, &imports)?;
    
    Ok(instance)
}

fn handle_health_check() -> Response {
    let health = serde_json::json!({
        "status": "healthy",
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "version": env!("CARGO_PKG_VERSION"),
    });
    
    Response::from_body(serde_json::to_string(&health).unwrap())
        .with_content_type(mime::APPLICATION_JSON)
}

fn handle_process_request(
    req: Request,
    wasm_instance: &WebAssemblyInstance,
) -> Result<serde_json::Value, Error> {
    let body = req.into_body().text()?;
    let api_request: ApiRequest = serde_json::from_str(&body)?;
    
    // Process with WASM
    let exports = wasm_instance.exports();
    let memory = exports.get_memory("memory").unwrap();
    
    // Write input to WASM memory
    let input_bytes = api_request.data.as_bytes();
    let input_ptr = exports.call::<(u32, u32), u32>(
        "allocate",
        (input_bytes.len() as u32, 0),
    )?;
    
    let memory_array = unsafe { memory.data_unchecked_mut() };
    memory_array[input_ptr as usize..input_ptr as usize + input_bytes.len()]
        .copy_from_slice(input_bytes);
    
    // Process
    let output_ptr = exports.call::<(u32, u32), u32>(
        "process",
        (input_ptr, input_bytes.len() as u32),
    )?;
    
    let output_len = exports.call::<(u32,), u32>("get_output_length", (output_ptr,))?;
    
    // Read output
    let output_bytes = &memory_array[output_ptr as usize..output_ptr as usize + output_len as usize];
    let output = serde_json::from_slice(output_bytes)?;
    
    // Clean up
    exports.call::<(u32, u32), ()>("deallocate", (input_ptr, input_bytes.len() as u32))?;
    exports.call::<(u32, u32), ()>("deallocate", (output_ptr, output_len))?;
    
    Ok(output)
}

fn handle_data_request(
    id: &str,
    wasm_instance: &WebAssemblyInstance,
) -> Result<Response, Error> {
    // Check edge cache first
    let cache = fastly::CacheHandle::open("data_cache");
    let cache_key = format!("data:{}", id);
    
    if let Some(entry) = cache.lookup(&cache_key) {
        return Ok(Response::from_body(entry.text()?)
            .with_content_type(mime::APPLICATION_JSON)
            .with_header("X-Cache", "HIT"));
    }
    
    // Process with WASM
    let exports = wasm_instance.exports();
    let result = exports.call::<(u32,), u32>("fetch_data", (id.parse()?,))?;
    
    let memory = exports.get_memory("memory").unwrap();
    let memory_array = unsafe { memory.data_unchecked() };
    
    let result_len = exports.call::<(u32,), u32>("get_result_length", (result,))?;
    let result_bytes = &memory_array[result as usize..result as usize + result_len as usize];
    let result_str = String::from_utf8(result_bytes.to_vec())?;
    
    // Cache result
    cache.insert(&cache_key, &result_str)?;
    
    Ok(Response::from_body(result_str)
        .with_content_type(mime::APPLICATION_JSON)
        .with_header("X-Cache", "MISS"))
}

fn add_security_headers(mut response: Response) -> Response {
    response.set_header("X-Content-Type-Options", "nosniff");
    response.set_header("X-Frame-Options", "DENY");
    response.set_header("X-XSS-Protection", "1; mode=block");
    response.set_header("Referrer-Policy", "strict-origin-when-cross-origin");
    response.set_header(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=()",
    );
    response
}

fn get_edge_location() -> String {
    fastly::dynamic_backend("origin")
        .map(|b| b.hostname().to_string())
        .unwrap_or_else(|_| "unknown".to_string())
}
```

---

## 14.3 Fermyon Spin

### Arquitetura do Fermyon Spin

O Fermyon Spin é um framework de aplicações WebAssembly para edge computing que permite criar microserviços leves e rápidos usando WASM como runtime.

### Aplicação Spin Completa

```rust
// spin-app/src/lib.rs
use spin_sdk::{
    http::{IntoResponse, Request, Response},
    http_component,
    key_value::Store,
    variables,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
struct AppConfig {
    name: String,
    version: String,
    max_request_size: usize,
    allowed_origins: Vec<String>,
    cache_ttl: u64,
}

#[derive(Serialize, Deserialize)]
struct ApiRequest {
    action: String,
    data: String,
    options: HashMap<String, String>,
}

#[derive(Serialize, Deserialize)]
struct ApiResponse {
    success: bool,
    data: Option<serde_json::Value>,
    error: Option<String>,
    metadata: ResponseMetadata,
}

#[derive(Serialize, Deserialize)]
struct ResponseMetadata {
    request_id: String,
    processing_time_ms: f64,
    cache_hit: bool,
    edge_region: String,
}

#[http_component]
fn handle_request(req: Request) -> anyhow::Result<impl IntoResponse> {
    let start_time = std::time::Instant::now();
    let request_id = generate_request_id();
    
    // Security validation
    validate_request(&req)?;
    
    // Load configuration
    let config = load_config()?;
    
    // Initialize WASM module
    let wasm_module = initialize_wasm()?;
    
    // Route request
    let path = req.uri().path();
    let method = req.method();
    
    let response = match (method, path) {
        ("GET", "/health") => handle_health(&config),
        
        ("POST", "/api/process") => {
            let process_start = std::time::Instant::now();
            let result = handle_process(req, &wasm_module, &config)?;
            let processing_time = process_start.elapsed().as_secs_f64() * 1000.0;
            
            let api_response = ApiResponse {
                success: true,
                data: Some(serde_json::to_value(result)?),
                error: None,
                metadata: ResponseMetadata {
                    request_id,
                    processing_time_ms: processing_time,
                    cache_hit: false,
                    edge_region: get_edge_region(),
                },
            };
            
            Response::builder()
                .status(200)
                .header("content-type", "application/json")
                .body(serde_json::to_string(&api_response)?)
                .build()
        }
        
        ("GET", path) if path.starts_with("/api/data/") => {
            let id = path.trim_start_matches("/api/data/");
            handle_data_request(id, &wasm_module, &config)?
        }
        
        ("POST", "/api/cache/invalidate") => {
            handle_cache_invalidation(req)?
        }
        
        _ => Response::builder()
            .status(404)
            .body("Not Found")
            .build(),
    };
    
    // Add security headers
    let mut response = add_security_headers(response);
    
    // Add timing information
    let total_time = start_time.elapsed().as_secs_f64() * 1000.0;
    response = response
        .header("x-request-id", &request_id)
        .header("x-response-time", format!("{}ms", total_time))
        .header("x-edge-region", get_edge_region());
    
    Ok(response)
}

fn validate_request(req: &Request) -> anyhow::Result<()> {
    let path = req.uri().path();
    let query = req.uri().query().unwrap_or("");
    
    // Check for path traversal
    if path.contains("..") {
        return Err(anyhow::anyhow!("Path traversal detected"));
    }
    
    // Check for XSS attempts
    let xss_patterns = ["<script", "javascript:", "eval(", "document.cookie"];
    for pattern in &xss_patterns {
        if path.contains(pattern) || query.contains(pattern) {
            return Err(anyhow::anyhow!("XSS attempt detected"));
        }
    }
    
    // Check Content-Length
    if let Some(content_length) = req.headers().get("content-length") {
        let length: usize = content_length.to_str()?.parse()?;
        if length > 10 * 1024 * 1024 {
            return Err(anyhow::anyhow!("Request too large"));
        }
    }
    
    // Check Origin header
    if let Some(origin) = req.headers().get("origin") {
        let config = load_config()?;
        let origin_str = origin.to_str()?;
        if !config.allowed_origins.is_empty() && !config.allowed_origins.contains(&origin_str.to_string()) {
            return Err(anyhow::anyhow!("Origin not allowed"));
        }
    }
    
    Ok(())
}

fn load_config() -> anyhow::Result<AppConfig> {
    Ok(AppConfig {
        name: variables::get("app_name")?,
        version: variables::get("app_version")?,
        max_request_size: variables::get("max_request_size")?
            .parse()
            .unwrap_or(10 * 1024 * 1024),
        allowed_origins: variables::get("allowed_origins")?
            .split(',')
            .map(|s| s.trim().to_string())
            .collect(),
        cache_ttl: variables::get("cache_ttl")?
            .parse()
            .unwrap_or(300),
    })
}

fn initialize_wasm() -> anyhow::Result<WebAssemblyInstance> {
    let wasm_bytes = include_bytes!("../pkg/processor.wasm");
    
    let memory = WebAssembly::Memory::new(WebAssembly::MemoryDescriptor {
        initial: 256,
        maximum: Some(1024),
        shared: false,
    })?;
    
    let imports = WebAssembly::Imports::new();
    imports.register(
        "env",
        WebAssembly::Extern::Memory(WebAssembly::Extern::Memory(memory)),
    );
    
    let module = WebAssembly::Module::from_binary(wasm_bytes)?;
    let instance = WebAssembly::Instance::new(&module, &imports)?;
    
    Ok(instance)
}

fn handle_health(config: &AppConfig) -> Response {
    let health = serde_json::json!({
        "status": "healthy",
        "app": config.name,
        "version": config.version,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    });
    
    Response::builder()
        .status(200)
        .header("content-type", "application/json")
        .body(serde_json::to_string(&health).unwrap())
        .build()
}

fn handle_process(
    req: Request,
    wasm_instance: &WebAssemblyInstance,
    config: &AppConfig,
) -> anyhow::Result<serde_json::Value> {
    let body = req.body().text()?;
    let api_request: ApiRequest = serde_json::from_str(&body)?;
    
    // Validate request size
    if body.len() > config.max_request_size {
        return Err(anyhow::anyhow!("Request too large"));
    }
    
    // Process with WASM
    let exports = wasm_instance.exports();
    let memory = exports.get_memory("memory").unwrap();
    
    // Write input to WASM memory
    let input_bytes = api_request.data.as_bytes();
    let input_ptr = exports.call::<(u32, u32), u32>(
        "allocate",
        (input_bytes.len() as u32, 0),
    )?;
    
    let memory_array = unsafe { memory.data_unchecked_mut() };
    memory_array[input_ptr as usize..input_ptr as usize + input_bytes.len()]
        .copy_from_slice(input_bytes);
    
    // Process
    let output_ptr = exports.call::<(u32, u32), u32>(
        "process",
        (input_ptr, input_bytes.len() as u32),
    )?;
    
    let output_len = exports.call::<(u32,), u32>("get_output_length", (output_ptr,))?;
    
    // Read output
    let output_bytes = &memory_array[output_ptr as usize..output_ptr as usize + output_len as usize];
    let output = serde_json::from_slice(output_bytes)?;
    
    // Clean up
    exports.call::<(u32, u32), ()>("deallocate", (input_ptr, input_bytes.len() as u32))?;
    exports.call::<(u32, u32), ()>("deallocate", (output_ptr, output_len))?;
    
    Ok(output)
}

fn handle_data_request(
    id: &str,
    wasm_instance: &WebAssemblyInstance,
    config: &AppConfig,
) -> anyhow::Result<Response> {
    // Check edge cache first
    let store = Store::open_default()?;
    let cache_key = format!("data:{}", id);
    
    if let Some(cached) = store.get(&cache_key)? {
        return Ok(Response::builder()
            .status(200)
            .header("content-type", "application/json")
            .header("x-cache", "HIT")
            .body(String::from_utf8(cached)?)
            .build());
    }
    
    // Process with WASM
    let exports = wasm_instance.exports();
    let result = exports.call::<(u32,), u32>("fetch_data", (id.parse()?,))?;
    
    let memory = exports.get_memory("memory").unwrap();
    let memory_array = unsafe { memory.data_unchecked() };
    
    let result_len = exports.call::<(u32,), u32>("get_result_length", (result,))?;
    let result_bytes = &memory_array[result as usize..result as usize + result_len as usize];
    let result_str = String::from_utf8(result_bytes.to_vec())?;
    
    // Cache result
    store.set(&cache_key, result_str.as_bytes())?;
    
    Ok(Response::builder()
        .status(200)
        .header("content-type", "application/json")
        .header("x-cache", "MISS")
        .body(result_str)
        .build())
}

fn handle_cache_invalidation(req: Request) -> anyhow::Result<Response> {
    let body = req.body().text()?;
    let invalidation: serde_json::Value = serde_json::from_str(&body)?;
    
    let pattern = invalidation["pattern"]
        .as_str()
        .ok_or_else(|| anyhow::anyhow!("Missing pattern"))?;
    
    let store = Store::open_default()?;
    
    // Get all keys and filter by pattern
    let keys = store.get_keys()?;
    let mut invalidated = 0;
    
    for key in keys {
        if key.contains(pattern) {
            store.delete(&key)?;
            invalidated += 1;
        }
    }
    
    Ok(Response::builder()
        .status(200)
        .header("content-type", "application/json")
        .body(serde_json::json!({
            "success": true,
            "invalidated": invalidated,
        }).to_string())
        .build())
}

fn add_security_headers(mut response: Response) -> Response {
    response = response
        .header("x-content-type-options", "nosniff")
        .header("x-frame-options", "DENY")
        .header("x-xss-protection", "1; mode=block")
        .header("referrer-policy", "strict-origin-when-cross-origin")
        .header(
            "permissions-policy",
            "camera=(), microphone=(), geolocation=()",
        );
    response
}

fn generate_request_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("req-{:x}-{:x}", timestamp, rand::random::<u32>())
}

fn get_edge_region() -> String {
    std::env::var("FASTLY_REGION").unwrap_or_else(|_| "unknown".to_string())
}
```

---

## 14.4 Edge vs Serverless

### Comparação Detalhada

```typescript
// edge-vs-serverless/src/comparison.ts
interface ComparisonResult {
  metric: string;
  edge: PerformanceMetrics;
  serverless: PerformanceMetrics;
  winner: 'edge' | 'serverless' | 'tie';
}

interface PerformanceMetrics {
  coldStartMs: number;
  warmExecutionMs: number;
  p50LatencyMs: number;
  p99LatencyMs: number;
  memoryUsageMB: number;
  costPerMillion: number;
}

class EdgeVsServerlessAnalyzer {
  private results: ComparisonResult[] = [];
  
  async analyze(
    edgeConfig: EdgeConfig,
    serverlessConfig: ServerlessConfig,
    testCases: TestCase[]
  ): Promise<ComparisonReport> {
    const edgeMetrics = await this.benchmarkEdge(edgeConfig, testCases);
    const serverlessMetrics = await this.benchmarkServerless(
      serverlessConfig,
      testCases
    );
    
    const comparison = this.compareMetrics(edgeMetrics, serverlessMetrics);
    const recommendations = this.generateRecommendations(comparison);
    
    return {
      timestamp: new Date().toISOString(),
      testCases: testCases.length,
      edgeProvider: edgeConfig.provider,
      serverlessProvider: serverlessConfig.provider,
      results: comparison,
      recommendations,
      summary: this.generateSummary(comparison),
    };
  }
  
  private async benchmarkEdge(
    config: EdgeConfig,
    testCases: TestCase[]
  ): Promise<MetricsSummary> {
    const results: PerformanceMetrics[] = [];
    
    for (const testCase of testCases) {
      const metrics = await this.runEdgeBenchmark(config, testCase);
      results.push(metrics);
    }
    
    return this.aggregateMetrics(results);
  }
  
  private async benchmarkServerless(
    config: ServerlessConfig,
    testCases: TestCase[]
  ): Promise<MetricsSummary> {
    const results: PerformanceMetrics[] = [];
    
    for (const testCase of testCases) {
      const metrics = await this.runServerlessBenchmark(config, testCase);
      results.push(metrics);
    }
    
    return this.aggregateMetrics(results);
  }
  
  private async runEdgeBenchmark(
    config: EdgeConfig,
    testCase: TestCase
  ): Promise<PerformanceMetrics> {
    const iterations = 100;
    const coldStarts: number[] = [];
    const warmExecutions: number[] = [];
    const latencies: number[] = [];
    
    // Cold start test
    for (let i = 0; i < 10; i++) {
      const start = performance.now();
      await this.invokeEdgeFunction(config, testCase, true);
      coldStarts.push(performance.now() - start);
    }
    
    // Warm execution test
    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      await this.invokeEdgeFunction(config, testCase, false);
      const duration = performance.now() - start;
      warmExecutions.push(duration);
      latencies.push(duration);
    }
    
    latencies.sort((a, b) => a - b);
    
    return {
      coldStartMs: coldStarts.reduce((a, b) => a + b) / coldStarts.length,
      warmExecutionMs:
        warmExecutions.reduce((a, b) => a + b) / warmExecutions.length,
      p50LatencyMs: latencies[Math.floor(latencies.length * 0.5)],
      p99LatencyMs: latencies[Math.floor(latencies.length * 0.99)],
      memoryUsageMB: await this.measureEdgeMemory(config, testCase),
      costPerMillion: this.calculateEdgeCost(config, testCase),
    };
  }
  
  private async runServerlessBenchmark(
    config: ServerlessConfig,
    testCase: TestCase
  ): Promise<PerformanceMetrics> {
    const iterations = 100;
    const coldStarts: number[] = [];
    const warmExecutions: number[] = [];
    const latencies: number[] = [];
    
    // Cold start test
    for (let i = 0; i < 10; i++) {
      const start = performance.now();
      await this.invokeServerlessFunction(config, testCase, true);
      coldStarts.push(performance.now() - start);
    }
    
    // Warm execution test
    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      await this.invokeServerlessFunction(config, testCase, false);
      const duration = performance.now() - start;
      warmExecutions.push(duration);
      latencies.push(duration);
    }
    
    latencies.sort((a, b) => a - b);
    
    return {
      coldStartMs: coldStarts.reduce((a, b) => a + b) / coldStarts.length,
      warmExecutionMs:
        warmExecutions.reduce((a, b) => a + b) / warmExecutions.length,
      p50LatencyMs: latencies[Math.floor(latencies.length * 0.5)],
      p99LatencyMs: latencies[Math.floor(latencies.length * 0.99)],
      memoryUsageMB: await this.measureServerlessMemory(config, testCase),
      costPerMillion: this.calculateServerlessCost(config, testCase),
    };
  }
  
  private compareMetrics(
    edge: MetricsSummary,
    serverless: MetricsSummary
  ): ComparisonResult[] {
    const metrics: (keyof PerformanceMetrics)[] = [
      'coldStartMs',
      'warmExecutionMs',
      'p50LatencyMs',
      'p99LatencyMs',
      'memoryUsageMB',
      'costPerMillion',
    ];
    
    return metrics.map((metric) => {
      const edgeValue = edge[metric];
      const serverlessValue = serverless[metric];
      
      // For most metrics, lower is better
      const lowerIsBetter = metric !== 'memoryUsageMB';
      
      let winner: 'edge' | 'serverless' | 'tie';
      if (Math.abs(edgeValue - serverlessValue) < 0.1) {
        winner = 'tie';
      } else if (lowerIsBetter) {
        winner = edgeValue < serverlessValue ? 'edge' : 'serverless';
      } else {
        winner = edgeValue > serverlessValue ? 'edge' : 'serverless';
      }
      
      return {
        metric,
        edge: edge,
        serverless: serverless,
        winner,
      };
    });
  }
  
  private generateRecommendations(
    results: ComparisonResult[]
  ): string[] {
    const recommendations: string[] = [];
    
    const edgeWins = results.filter((r) => r.winner === 'edge').length;
    const serverlessWins = results.filter((r) => r.winner === 'serverless').length;
    
    if (edgeWins > serverlessWins) {
      recommendations.push(
        'Edge computing is recommended for this use case based on performance metrics.'
      );
    } else if (serverlessWins > edgeWins) {
      recommendations.push(
        'Traditional serverless is recommended for this use case based on performance metrics.'
      );
    } else {
      recommendations.push(
        'Both approaches are viable; consider other factors like cost and complexity.'
      );
    }
    
    // Specific recommendations based on metrics
    const latencyResult = results.find((r) => r.metric === 'p99LatencyMs');
    if (latencyResult?.winner === 'edge') {
      recommendations.push(
        'Edge computing provides better tail latency, important for user experience.'
      );
    }
    
    const costResult = results.find((r) => r.metric === 'costPerMillion');
    if (costResult?.winner === 'serverless') {
      recommendations.push(
        'Serverless may be more cost-effective for low-traffic applications.'
      );
    }
    
    return recommendations;
  }
  
  private generateSummary(results: ComparisonResult[]): string {
    const edgeWins = results.filter((r) => r.winner === 'edge').length;
    const serverlessWins = results.filter((r) => r.winner === 'serverless').length;
    const ties = results.filter((r) => r.winner === 'tie').length;
    
    return `Edge: ${edgeWins} wins, Serverless: ${serverlessWins} wins, Ties: ${ties}`;
  }
  
  private aggregateMetrics(results: PerformanceMetrics[]): MetricsSummary {
    return {
      coldStartMs:
        results.reduce((sum, r) => sum + r.coldStartMs, 0) / results.length,
      warmExecutionMs:
        results.reduce((sum, r) => sum + r.warmExecutionMs, 0) / results.length,
      p50LatencyMs:
        results.reduce((sum, r) => sum + r.p50LatencyMs, 0) / results.length,
      p99LatencyMs:
        results.reduce((sum, r) => sum + r.p99LatencyMs, 0) / results.length,
      memoryUsageMB:
        results.reduce((sum, r) => sum + r.memoryUsageMB, 0) / results.length,
      costPerMillion:
        results.reduce((sum, r) => sum + r.costPerMillion, 0) / results.length,
    };
  }
  
  // Placeholder methods for actual implementation
  private async invokeEdgeFunction(
    config: EdgeConfig,
    testCase: TestCase,
    cold: boolean
  ): Promise<void> {
    // Actual invocation logic
  }
  
  private async invokeServerlessFunction(
    config: ServerlessConfig,
    testCase: TestCase,
    cold: boolean
  ): Promise<void> {
    // Actual invocation logic
  }
  
  private async measureEdgeMemory(
    config: EdgeConfig,
    testCase: TestCase
  ): Promise<number> {
    return 0; // Actual measurement
  }
  
  private async measureServerlessMemory(
    config: ServerlessConfig,
    testCase: TestCase
  ): Promise<number> {
    return 0; // Actual measurement
  }
  
  private calculateEdgeCost(
    config: EdgeConfig,
    testCase: TestCase
  ): number {
    return 0; // Actual calculation
  }
  
  private calculateServerlessCost(
    config: ServerlessConfig,
    testCase: TestCase
  ): number {
    return 0; // Actual calculation
  }
}

interface EdgeConfig {
  provider: string;
  region: string;
  memoryLimit: number;
  timeout: number;
}

interface ServerlessConfig {
  provider: string;
  runtime: string;
  memorySize: number;
  timeout: number;
}

interface TestCase {
  name: string;
  input: any;
  expectedOutput: any;
  complexity: 'low' | 'medium' | 'high';
}

interface MetricsSummary {
  coldStartMs: number;
  warmExecutionMs: number;
  p50LatencyMs: number;
  p99LatencyMs: number;
  memoryUsageMB: number;
  costPerMillion: number;
}

interface ComparisonReport {
  timestamp: string;
  testCases: number;
  edgeProvider: string;
  serverlessProvider: string;
  results: ComparisonResult[];
  recommendations: string[];
  summary: string;
}
```

---

## 14.5 Cold Start Optimization

### Técnicas de Otimização de冷启动

```typescript
// cold-start-optimization/src/optimizer.ts
interface ColdStartOptimizer {
  optimize(module: WebAssembly.Module): OptimizedModule;
  preload(modules: WebAssembly.Module[]): void;
  getMetrics(): ColdStartMetrics;
}

interface OptimizedModule {
  module: WebAssembly.Module;
  precompiled: boolean;
  optimizedImports: WebAssembly.Imports;
  memoryPool: MemoryPool;
}

interface ColdStartMetrics {
  averageColdStartMs: number;
  p95ColdStartMs: number;
  p99ColdStartMs: number;
  cacheHitRate: number;
  memoryReuseRate: number;
}

class WasmColdStartOptimizer implements ColdStartOptimizer {
  private moduleCache: Map<string, WebAssembly.Module> = new Map();
  private memoryPool: MemoryPool;
  private compilationCache: CompilationCache;
  private importResolver: ImportResolver;
  
  constructor(config: OptimizerConfig) {
    this.memoryPool = new MemoryPool(config.memoryPoolSize);
    this.compilationCache = new CompilationCache(config.cacheSize);
    this.importResolver = new ImportResolver(config.allowedImports);
  }
  
  optimize(module: WebAssembly.Module): OptimizedModule {
    // Pre-optimize module
    const optimizedModule = this.preOptimizeModule(module);
    
    // Create optimized imports
    const optimizedImports = this.createOptimizedImports(module);
    
    // Pre-allocate memory
    const memory = this.memoryPool.allocate(module);
    
    return {
      module: optimizedModule,
      precompiled: true,
      optimizedImports,
      memoryPool: this.memoryPool,
    };
  }
  
  preload(modules: WebAssembly.Module[]): void {
    // Batch preload modules
    for (const module of modules) {
      const moduleHash = this.computeModuleHash(module);
      
      if (!this.moduleCache.has(moduleHash)) {
        // Compile and cache
        const optimized = this.preOptimizeModule(module);
        this.moduleCache.set(moduleHash, optimized);
        
        // Pre-allocate memory
        this.memoryPool.preAllocate(module);
      }
    }
  }
  
  getMetrics(): ColdStartMetrics {
    return {
      averageColdStartMs: this.compilationCache.getAverageCompilationTime(),
      p95ColdStartMs: this.compilationCache.getPercentile(95),
      p99ColdStartMs: this.compilationCache.getPercentile(99),
      cacheHitRate: this.compilationCache.getHitRate(),
      memoryReuseRate: this.memoryPool.getReuseRate(),
    };
  }
  
  private preOptimizeModule(module: WebAssembly.Module): WebAssembly.Module {
    // Extract and optimize imports
    const imports = WebAssembly.Module.imports(module);
    const exports = WebAssembly.Module.exports(module);
    
    // Analyze module structure
    const analysis = this.analyzeModule(module);
    
    // Apply optimizations based on analysis
    let optimizedModule = module;
    
    if (analysis.canOptimizeMemory) {
      optimizedModule = this.optimizeMemoryAccess(optimizedModule, analysis);
    }
    
    if (analysis.canOptimizeLoops) {
      optimizedModule = this.optimizeLoops(optimizedModule, analysis);
    }
    
    if (analysis.canInlineFunctions) {
      optimizedModule = this.inlineSmallFunctions(optimizedModule, analysis);
    }
    
    return optimizedModule;
  }
  
  private createOptimizedImports(
    module: WebAssembly.Module
  ): WebAssembly.Imports {
    const imports = WebAssembly.Module.imports(module);
    const optimizedImports = new Map<string, WebAssembly.Module>();
    
    for (const importItem of imports) {
      if (importItem.kind === 'function') {
        const optimizedFunction = this.optimizeHostFunction(
          importItem.module,
          importItem.name
        );
        
        if (!optimizedImports.has(importItem.module)) {
          optimizedImports.set(importItem.module, new Map());
        }
        
        optimizedImports.get(importItem.module)!.set(
          importItem.name,
          optimizedFunction
        );
      }
    }
    
    return optimizedImports;
  }
  
  private analyzeModule(module: WebAssembly.Module): ModuleAnalysis {
    const imports = WebAssembly.Module.imports(module);
    const exports = WebAssembly.Module.exports(module);
    
    // Analyze memory usage patterns
    const memoryImports = imports.filter((i) => i.kind === 'memory');
    const functionImports = imports.filter((i) => i.kind === 'function');
    const globalImports = imports.filter((i) => i.kind === 'global');
    
    // Estimate module size
    const estimatedSize = this.estimateModuleSize(module);
    
    // Check for optimization opportunities
    const canOptimizeMemory = memoryImports.length > 0;
    const canOptimizeLoops = this.hasLoopPatterns(module);
    const canInlineFunctions = this.hasSmallFunctions(module);
    
    return {
      memoryImports: memoryImports.length,
      functionImports: functionImports.length,
      globalImports: globalImports.length,
      estimatedSize,
      canOptimizeMemory,
      canOptimizeLoops,
      canInlineFunctions,
      complexityScore: this.calculateComplexityScore(module),
    };
  }
  
  private optimizeMemoryAccess(
    module: WebAssembly.Module,
    analysis: ModuleAnalysis
  ): WebAssembly.Module {
    // Create memory with optimal configuration
    const memory = new WebAssembly.Memory({
      initial: Math.max(16, Math.ceil(analysis.estimatedSize / 65536)),
      maximum: Math.min(256, Math.ceil(analysis.estimatedSize / 65536) * 4),
      shared: false,
    });
    
    // Pre-populate memory pages
    const buffer = memory.buffer;
    const uint8Array = new Uint8Array(buffer);
    
    // Zero-initialize first few pages for common patterns
    for (let i = 0; i < Math.min(4, uint8Array.length / 65536); i++) {
      uint8Array.fill(0, i * 65536, (i + 1) * 65536);
    }
    
    return module; // In practice, would recompile with optimized memory
  }
  
  private optimizeLoops(
    module: WebAssembly.Module,
    analysis: ModuleAnalysis
  ): WebAssembly.Module {
    // Loop optimization would involve:
    // 1. Identifying hot loops through profiling
    // 2. Applying loop unrolling for small loops
    // 3. Optimizing branch prediction hints
    // 4. Reducing loop overhead
    
    return module; // Placeholder
  }
  
  private inlineSmallFunctions(
    module: WebAssembly.Module,
    analysis: ModuleAnalysis
  ): WebAssembly.Module {
    // Function inlining would involve:
    // 1. Identifying small functions (less than N instructions)
    // 2. Analyzing call frequency
    // 3. Inlining frequently called small functions
    // 4. Reducing function call overhead
    
    return module; // Placeholder
  }
  
  private optimizeHostFunction(
    module: string,
    name: string
  ): WebAssembly.ImportValue {
    // Create optimized host function with caching
    return (...args: any[]) => {
      // Check cache
      const cacheKey = `${module}:${name}:${JSON.stringify(args)}`;
      const cached = this.compilationCache.get(cacheKey);
      
      if (cached) {
        return cached;
      }
      
      // Execute and cache
      const result = this.executeHostFunction(module, name, args);
      this.compilationCache.set(cacheKey, result);
      
      return result;
    };
  }
  
  private executeHostFunction(
    module: string,
    name: string,
    args: any[]
  ): any {
    // Actual host function execution
    return null;
  }
  
  private computeModuleHash(module: WebAssembly.Module): string {
    // Compute hash for module caching
    const buffer = WebAssembly.Module.customSections(module, 'custom');
    let hash = 0;
    for (let i = 0; i < buffer.byteLength; i++) {
      hash = (hash * 31 + buffer[i]) | 0;
    }
    return hash.toString(16);
  }
  
  private estimateModuleSize(module: WebAssembly.Module): number {
    // Estimate module size for memory allocation
    const exports = WebAssembly.Module.exports(module);
    const imports = WebAssembly.Module.imports(module);
    
    return exports.length * 1024 + imports.length * 512; // Rough estimate
  }
  
  private hasLoopPatterns(module: WebAssembly.Module): boolean {
    // Analyze for loop patterns
    return true; // Placeholder
  }
  
  private hasSmallFunctions(module: WebAssembly.Module): boolean {
    // Analyze for small functions
    return true; // Placeholder
  }
  
  private calculateComplexityScore(module: WebAssembly.Module): number {
    // Calculate complexity score for optimization decisions
    return 0.5; // Placeholder
  }
}

class MemoryPool {
  private pools: Map<number, WebAssembly.Memory[]> = new Map();
  private allocated: number = 0;
  private reused: number = 0;
  
  constructor(private maxSize: number) {}
  
  allocate(module: WebAssembly.Module): WebAssembly.Memory {
    const estimatedSize = this.estimateMemorySize(module);
    const pageSize = this.getNextPageSize(estimatedSize);
    
    // Check for available memory in pool
    const pool = this.pools.get(pageSize);
    if (pool && pool.length > 0) {
      this.reused++;
      return pool.pop()!;
    }
    
    // Allocate new memory
    this.allocated++;
    return new WebAssembly.Memory({
      initial: pageSize,
      maximum: Math.min(pageSize * 4, this.maxSize / 65536),
      shared: false,
    });
  }
  
  preAllocate(module: WebAssembly.Module): void {
    const estimatedSize = this.estimateMemorySize(module);
    const pageSize = this.getNextPageSize(estimatedSize);
    
    // Pre-allocate multiple instances
    const preAllocationCount = 3;
    for (let i = 0; i < preAllocationCount; i++) {
      const memory = new WebAssembly.Memory({
        initial: pageSize,
        maximum: Math.min(pageSize * 4, this.maxSize / 65536),
        shared: false,
      });
      
      if (!this.pools.has(pageSize)) {
        this.pools.set(pageSize, []);
      }
      
      this.pools.get(pageSize)!.push(memory);
    }
  }
  
  deallocate(memory: WebAssembly.Memory): void {
    const pageSize = memory.buffer.byteLength / 65536;
    
    if (!this.pools.has(pageSize)) {
      this.pools.set(pageSize, []);
    }
    
    this.pools.get(pageSize)!.push(memory);
  }
  
  getReuseRate(): number {
    const total = this.allocated + this.reused;
    return total > 0 ? this.reused / total : 0;
  }
  
  private estimateMemorySize(module: WebAssembly.Module): number {
    // Estimate memory requirements
    return 1024 * 1024; // 1MB default
  }
  
  private getNextPageSize(size: number): number {
    return Math.max(1, Math.ceil(size / 65536));
  }
}

class CompilationCache {
  private cache: Map<string, any> = new Map();
  private hitCount: number = 0;
  private missCount: number = 0;
  private compilationTimes: number[] = [];
  
  constructor(private maxSize: number) {}
  
  get(key: string): any | null {
    if (this.cache.has(key)) {
      this.hitCount++;
      return this.cache.get(key);
    }
    
    this.missCount++;
    return null;
  }
  
  set(key: string, value: any): void {
    if (this.cache.size >= this.maxSize) {
      // Evict oldest entry
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
    
    this.cache.set(key, value);
  }
  
  getHitRate(): number {
    const total = this.hitCount + this.missCount;
    return total > 0 ? this.hitCount / total : 0;
  }
  
  getAverageCompilationTime(): number {
    if (this.compilationTimes.length === 0) {
      return 0;
    }
    
    return (
      this.compilationTimes.reduce((a, b) => a + b) /
      this.compilationTimes.length
    );
  }
  
  getPercentile(percentile: number): number {
    if (this.compilationTimes.length === 0) {
      return 0;
    }
    
    const sorted = [...this.compilationTimes].sort((a, b) => a - b);
    const index = Math.floor((percentile / 100) * sorted.length);
    return sorted[index];
  }
  
  recordCompilationTime(time: number): void {
    this.compilationTimes.push(time);
  }
}

class ImportResolver {
  private allowedImports: Set<string>;
  private resolvedImports: Map<string, WebAssembly.ImportValue> = new Map();
  
  constructor(allowedImports: string[]) {
    this.allowedImports = new Set(allowedImports);
  }
  
  resolve(
    imports: WebAssembly.ModuleImports[]
  ): WebAssembly.Imports {
    const resolved: WebAssembly.Imports = {};
    
    for (const importItem of imports) {
      if (!this.allowedImports.has(importItem.module)) {
        throw new Error(`Import module not allowed: ${importItem.module}`);
      }
      
      if (!resolved[importItem.module]) {
        resolved[importItem.module] = {};
      }
      
      const key = `${importItem.module}:${importItem.name}`;
      
      if (!this.resolvedImports.has(key)) {
        this.resolvedImports.set(
          key,
          this.createImportFunction(importItem)
        );
      }
      
      resolved[importItem.module][importItem.name] =
        this.resolvedImports.get(key);
    }
    
    return resolved;
  }
  
  private createImportFunction(
    importItem: WebAssembly.ModuleImports
  ): WebAssembly.ImportValue {
    // Create optimized import function
    return (...args: any[]) => {
      // Default implementation
      return null;
    };
  }
}

interface OptimizerConfig {
  memoryPoolSize: number;
  cacheSize: number;
  allowedImports: string[];
}

interface ModuleAnalysis {
  memoryImports: number;
  functionImports: number;
  globalImports: number;
  estimatedSize: number;
  canOptimizeMemory: boolean;
  canOptimizeLoops: boolean;
  canInlineFunctions: boolean;
  complexityScore: number;
}
```

---

## 14.6 KV Storage at Edge

### Sistema de Armazenamento Key-Value Distribuído

```typescript
// edge-kv-storage/src/kv-storage.ts
interface EdgeKVStorage {
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, options?: SetOptions): Promise<void>;
  delete(key: string): Promise<boolean>;
  list(options?: ListOptions): Promise<string[]>;
  getWithMetadata<T>(key: string): Promise<KVEntry<T> | null>;
}

interface SetOptions {
  expirationTtl?: number;
  expiration?: Date;
  metadata?: Record<string, any>;
}

interface ListOptions {
  prefix?: string;
  limit?: number;
  cursor?: string;
}

interface KVEntry<T> {
  value: T;
  metadata?: Record<string, any>;
  expiration?: Date;
}

interface ListResult {
  keys: string[];
  list_complete: boolean;
  cursor?: string;
}

class CloudflareKVStorage implements EdgeKVStorage {
  private namespace: KVNamespace;
  private cache: Map<string, { value: any; expiry: number }> = new Map();
  private cacheTtl: number = 60000; // 1 minute
  
  constructor(namespace: KVNamespace, cacheTtl: number = 60000) {
    this.namespace = namespace;
    this.cacheTtl = cacheTtl;
  }
  
  async get<T>(key: string): Promise<T | null> {
    // Check local cache first
    const cached = this.getFromCache<T>(key);
    if (cached !== null) {
      return cached;
    }
    
    // Fetch from KV
    const value = await this.namespace.get<T>(key, 'json');
    
    if (value !== null) {
      // Cache the result
      this.setInCache(key, value);
    }
    
    return value;
  }
  
  async set<T>(key: string, value: T, options?: SetOptions): Promise<void> {
    const kvOptions: KVNamespacePutOptions = {};
    
    if (options?.expirationTtl) {
      kvOptions.expirationTtl = options.expirationTtl;
    }
    
    if (options?.expiration) {
      kvOptions.expiration = options.expiration;
    }
    
    if (options?.metadata) {
      kvOptions.metadata = options.metadata;
    }
    
    await this.namespace.put(key, JSON.stringify(value), kvOptions);
    
    // Update local cache
    this.setInCache(key, value);
  }
  
  async delete(key: string): Promise<boolean> {
    try {
      await this.namespace.delete(key);
      this.deleteFromCache(key);
      return true;
    } catch {
      return false;
    }
  }
  
  async list(options?: ListOptions): Promise<string[]> {
    const result: string[] = [];
    let cursor: string | undefined;
    let complete = false;
    
    while (!complete) {
      const listResult: ListResult = await this.namespace.list({
        prefix: options?.prefix,
        limit: options?.limit || 100,
        cursor,
      });
      
      result.push(...listResult.keys);
      cursor = listResult.cursor;
      complete = listResult.list_complete;
      
      if (options?.limit && result.length >= options.limit) {
        break;
      }
    }
    
    return result.slice(0, options?.limit);
  }
  
  async getWithMetadata<T>(key: string): Promise<KVEntry<T> | null> {
    const value = await this.namespace.getWithMetadata<T>(key, 'json');
    
    if (value.value === null) {
      return null;
    }
    
    return {
      value: value.value,
      metadata: value.metadata as Record<string, any> | undefined,
      expiration: value.expiration,
    };
  }
  
  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);
    
    if (!entry) {
      return null;
    }
    
    if (Date.now() > entry.expiry) {
      this.cache.delete(key);
      return null;
    }
    
    return entry.value as T;
  }
  
  private setInCache(key: string, value: any): void {
    this.cache.set(key, {
      value,
      expiry: Date.now() + this.cacheTtl,
    });
    
    // Evict old entries if cache is too large
    if (this.cache.size > 1000) {
      const oldestKey = this.cache.keys().next().value;
      this.cache.delete(oldestKey);
    }
  }
  
  private deleteFromCache(key: string): void {
    this.cache.delete(key);
  }
}

class ReplicatedKVStorage implements EdgeKVStorage {
  private primary: EdgeKVStorage;
  private replicas: EdgeKVStorage[];
  private consistency: ConsistencyLevel;
  
  constructor(
    primary: EdgeKVStorage,
    replicas: EdgeKVStorage[],
    consistency: ConsistencyLevel = 'eventual'
  ) {
    this.primary = primary;
    this.replicas = replicas;
    this.consistency = consistency;
  }
  
  async get<T>(key: string): Promise<T | null> {
    // Read from primary
    const value = await this.primary.get<T>(key);
    
    if (value !== null) {
      return value;
    }
    
    // If not found, check replicas (for eventual consistency)
    if (this.consistency === 'eventual') {
      for (const replica of this.replicas) {
        const replicaValue = await replica.get<T>(key);
        if (replicaValue !== null) {
          // Replicate back to primary
          await this.primary.set(key, replicaValue);
          return replicaValue;
        }
      }
    }
    
    return null;
  }
  
  async set<T>(key: string, value: T, options?: SetOptions): Promise<void> {
    // Write to primary
    await this.primary.set(key, value, options);
    
    // Replicate to replicas asynchronously
    if (this.consistency === 'eventual') {
      const replicationPromises = this.replicas.map((replica) =>
        replica.set(key, value, options).catch((error) => {
          console.error('Replication failed:', error);
        })
      );
      
      // Don't wait for replication in eventual consistency
      Promise.all(replicationPromises).catch(() => {});
    } else {
      // Strong consistency: wait for all replicas
      await Promise.all(
        this.replicas.map((replica) => replica.set(key, value, options))
      );
    }
  }
  
  async delete(key: string): Promise<boolean> {
    const primaryResult = await this.primary.delete(key);
    
    if (this.consistency === 'eventual') {
      const replicationPromises = this.replicas.map((replica) =>
        replica.delete(key).catch((error) => {
          console.error('Replication failed:', error);
        })
      );
      
      Promise.all(replicationPromises).catch(() => {});
    } else {
      await Promise.all(
        this.replicas.map((replica) => replica.delete(key))
      );
    }
    
    return primaryResult;
  }
  
  async list(options?: ListOptions): Promise<string[]> {
    // List from primary
    return this.primary.list(options);
  }
  
  async getWithMetadata<T>(key: string): Promise<KVEntry<T> | null> {
    return this.primary.getWithMetadata<T>(key);
  }
}

type ConsistencyLevel = 'strong' | 'eventual';

class KVStorageWithEncryption implements EdgeKVStorage {
  private storage: EdgeKVStorage;
  private encryptionKey: CryptoKey;
  
  constructor(storage: EdgeKVStorage, encryptionKey: CryptoKey) {
    this.storage = storage;
    this.encryptionKey = encryptionKey;
  }
  
  async get<T>(key: string): Promise<T | null> {
    const encryptedEntry = await this.storage.get<EncryptedEntry>(key);
    
    if (!encryptedEntry) {
      return null;
    }
    
    const decrypted = await this.decrypt(encryptedEntry);
    return JSON.parse(decrypted) as T;
  }
  
  async set<T>(key: string, value: T, options?: SetOptions): Promise<void> {
    const plaintext = JSON.stringify(value);
    const encrypted = await this.encrypt(plaintext);
    
    await this.storage.set(key, encrypted, options);
  }
  
  async delete(key: string): Promise<boolean> {
    return this.storage.delete(key);
  }
  
  async list(options?: ListOptions): Promise<string[]> {
    return this.storage.list(options);
  }
  
  async getWithMetadata<T>(key: string): Promise<KVEntry<T> | null> {
    const entry = await this.storage.getWithMetadata<EncryptedEntry>(key);
    
    if (!entry) {
      return null;
    }
    
    const decrypted = await this.decrypt(entry.value);
    return {
      value: JSON.parse(decrypted) as T,
      metadata: entry.metadata,
      expiration: entry.expiration,
    };
  }
  
  private async encrypt(plaintext: string): Promise<EncryptedEntry> {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(plaintext);
    
    const encrypted = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv,
      },
      this.encryptionKey,
      encoded
    );
    
    return {
      iv: Array.from(iv),
      data: Array.from(new Uint8Array(encrypted)),
    };
  }
  
  private async decrypt(entry: EncryptedEntry): Promise<string> {
    const iv = new Uint8Array(entry.iv);
    const data = new Uint8Array(entry.data);
    
    const decrypted = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv,
      },
      this.encryptionKey,
      data
    );
    
    return new TextDecoder().decode(decrypted);
  }
}

interface EncryptedEntry {
  iv: number[];
  data: number[];
}
```

---

## 14.7 Durable Objects

### Padrões de Durable Objects com WASM

```typescript
// durable-objects/src/durable-object.ts
interface DurableObjectState {
  id: string;
  storage: DurableObjectStorage;
  blockConcurrencyWhile<T>(fn: () => Promise<T>): Promise<T>;
}

interface DurableObjectStorage {
  get<T>(key: string): Promise<T | undefined>;
  put<T>(key: string, value: T): Promise<void>;
  delete(key: string): Promise<boolean>;
  list(options?: { prefix?: string; limit?: number }): Promise<Map<string, any>>;
  transaction<T>(fn: (txn: DurableObjectTransaction) => Promise<T>): Promise<T>;
}

interface DurableObjectTransaction {
  get<T>(key: string): Promise<T | undefined>;
  put<T>(key: string, value: T): Promise<void>;
  delete(key: string): Promise<boolean>;
  rollback(): void;
}

interface DurableObjectResponse extends Response {
  waitUntil?: Promise<any>;
}

class WasmDurableObject {
  private state: DurableObjectState;
  private env: Env;
  private wasmInstance: WebAssembly.Instance | null = null;
  
  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
  }
  
  async fetch(request: Request): Promise<Response> {
    // Initialize WASM if not already done
    if (!this.wasmInstance) {
      await this.initializeWasm();
    }
    
    const url = new URL(request.url);
    const path = url.pathname;
    
    switch (true) {
      case path.endsWith('/process'):
        return this.handleProcess(request);
      
      case path.endsWith('/state'):
        return this.handleGetState();
      
      case path.endsWith('/sync'):
        return this.handleSync(request);
      
      case path.endsWith('/alarm'):
        return this.handleAlarm();
      
      default:
        return new Response('Not Found', { status: 404 });
    }
  }
  
  private async initializeWasm(): Promise<void> {
    const wasmModule = await WebAssembly.compile(
      this.env.WASM_MODULE.bytes()
    );
    
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 1024 });
    
    const imports = {
      env: {
        memory,
        log: (ptr: number, len: number) => {
          const buffer = new Uint8Array(memory.buffer);
          const bytes = buffer.slice(ptr, ptr + len);
          console.log('[WASM]', new TextDecoder().decode(bytes));
        },
        storage_get: (keyPtr: number, keyLen: number) => {
          const buffer = new Uint8Array(memory.buffer);
          const key = new TextDecoder().decode(
            buffer.slice(keyPtr, keyPtr + keyLen)
          );
          
          // This would need to be async in practice
          // Using a workaround with shared memory
          return 0;
        },
        storage_set: (
          keyPtr: number,
          keyLen: number,
          valuePtr: number,
          valueLen: number
        ) => {
          const buffer = new Uint8Array(memory.buffer);
          const key = new TextDecoder().decode(
            buffer.slice(keyPtr, keyPtr + keyLen)
          );
          const value = new TextDecoder().decode(
            buffer.slice(valuePtr, valuePtr + valueLen)
          );
          
          // Store asynchronously
          this.state.storage.put(key, value).catch(console.error);
          
          return 1;
        },
      },
    };
    
    this.wasmInstance = await WebAssembly.instantiate(wasmModule, imports);
  }
  
  private async handleProcess(request: Request): Promise<Response> {
    const body = await request.text();
    const exports = this.wasmInstance!.exports as any;
    const memory = new WebAssembly.Memory();
    
    // Write input to WASM memory
    const inputBytes = new TextEncoder().encode(body);
    const inputPtr = exports.allocate(inputBytes.length);
    
    const buffer = new Uint8Array(memory.buffer);
    buffer.set(inputBytes, inputPtr);
    
    // Process
    const outputPtr = exports.process(inputPtr, inputBytes.length);
    const outputLen = exports.get_output_length();
    
    // Read output
    const output = new TextDecoder().decode(
      buffer.slice(outputPtr, outputPtr + outputLen)
    );
    
    // Clean up
    exports.deallocate(inputPtr, inputBytes.length);
    exports.deallocate(outputPtr, outputLen);
    
    return new Response(output, {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async handleGetState(): Promise<Response> {
    const state = await this.state.storage.list();
    const stateObj: Record<string, any> = {};
    
    for (const [key, value] of state) {
      stateObj[key] = value;
    }
    
    return new Response(JSON.stringify(stateObj), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async handleSync(request: Request): Promise<Response> {
    const body = await request.json() as SyncRequest;
    
    // Process sync data
    const result = await this.state.storage.transaction(async (txn) => {
      // Apply sync operations
      for (const op of body.operations) {
        switch (op.type) {
          case 'put':
            await txn.put(op.key, op.value);
            break;
          case 'delete':
            await txn.delete(op.key);
            break;
        }
      }
      
      // Return sync result
      return {
        success: true,
        timestamp: Date.now(),
        version: body.version,
      };
    });
    
    return new Response(JSON.stringify(result), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async handleAlarm(): Promise<Response> {
    // Handle alarm for scheduled tasks
    const exports = this.wasmInstance!.exports as any;
    
    // Execute scheduled task in WASM
    exports.execute_scheduled_task();
    
    // Set next alarm
    await this.state.storage.put('alarm', Date.now() + 60000); // 1 minute
    
    return new Response('Alarm processed');
  }
  
  async alarm(): Promise<void> {
    // Called when alarm fires
    await this.handleAlarm();
  }
}

interface Env {
  WASM_MODULE: DurableObjectNamespace;
  STORAGE: KVNamespace;
}

interface SyncRequest {
  operations: SyncOperation[];
  version: number;
}

interface SyncOperation {
  type: 'put' | 'delete';
  key: string;
  value?: any;
}

class DurableObjectCoordination {
  private namespace: DurableObjectNamespace;
  
  constructor(namespace: DurableObjectNamespace) {
    this.namespace = namespace;
  }
  
  async getOrCreateObject(id: string): Promise<DurableObjectStub> {
    const stub = this.namespace.get(this.namespace.idFromName(id));
    return stub;
  }
  
  async processWithCoordination(
    objectId: string,
    operation: string,
    data: any
  ): Promise<any> {
    const stub = await this.getOrCreateObject(objectId);
    
    const response = await stub.fetch(
      new Request(`https://durable-objects.internal/${operation}`, {
        method: 'POST',
        body: JSON.stringify(data),
        headers: { 'Content-Type': 'application/json' },
      })
    );
    
    return response.json();
  }
  
  async broadcastToObjectGroup(
    objectIds: string[],
    operation: string,
    data: any
  ): Promise<Map<string, any>> {
    const results = new Map<string, any>();
    
    const promises = objectIds.map(async (id) => {
      try {
        const result = await this.processWithCoordination(id, operation, data);
        results.set(id, result);
      } catch (error) {
        results.set(id, { error: (error as Error).message });
      }
    });
    
    await Promise.all(promises);
    
    return results;
  }
}
```

---

## 14.8 Security at Edge

### Camadas de Segurança no Edge

```typescript
// edge-security/src/security.ts
interface EdgeSecurity {
  validateRequest(request: Request): SecurityCheckResult;
  authenticateToken(token: string): Promise<AuthResult>;
  encryptData(data: string): Promise<EncryptedData>;
  decryptData(encrypted: EncryptedData): Promise<string>;
  checkRateLimit(key: string): Promise<RateLimitResult>;
  auditLog(event: SecurityEvent): Promise<void>;
}

interface SecurityCheckResult {
  valid: boolean;
  issues: SecurityIssue[];
  riskScore: number;
}

interface SecurityIssue {
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  recommendation: string;
}

interface AuthResult {
  authenticated: boolean;
  userId?: string;
  permissions?: string[];
  expiresAt?: Date;
  error?: string;
}

interface EncryptedData {
  iv: number[];
  data: number[];
  algorithm: string;
}

interface RateLimitResult {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: Date;
}

interface SecurityEvent {
  type: string;
  timestamp: Date;
  source: string;
  details: Record<string, any>;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

class EdgeSecurityManager implements EdgeSecurity {
  private rateLimiter: RateLimiter;
  private tokenVerifier: TokenVerifier;
  private encryptionService: EncryptionService;
  private auditLogger: AuditLogger;
  private threatDetector: ThreatDetector;
  
  constructor(config: SecurityConfig) {
    this.rateLimiter = new RateLimiter(config.rateLimitConfig);
    this.tokenVerifier = new TokenVerifier(config.authConfig);
    this.encryptionService = new EncryptionService(config.encryptionConfig);
    this.auditLogger = new AuditLogger(config.auditConfig);
    this.threatDetector = new ThreatDetector(config.threatConfig);
  }
  
  validateRequest(request: Request): SecurityCheckResult {
    const issues: SecurityIssue[] = [];
    let riskScore = 0;
    
    // Check for common attack patterns
    const url = new URL(request.url);
    
    // Path traversal check
    if (this.detectPathTraversal(url.pathname)) {
      issues.push({
        type: 'path_traversal',
        severity: 'high',
        description: 'Path traversal attempt detected',
        recommendation: 'Block request and log for investigation',
      });
      riskScore += 0.3;
    }
    
    // XSS check
    if (this.detectXSS(request)) {
      issues.push({
        type: 'xss_attempt',
        severity: 'high',
        description: 'XSS attack pattern detected',
        recommendation: 'Sanitize input and block request',
      });
      riskScore += 0.3;
    }
    
    // SQL injection check
    if (this.detectSQLInjection(request)) {
      issues.push({
        type: 'sql_injection',
        severity: 'critical',
        description: 'SQL injection attempt detected',
        recommendation: 'Block request immediately',
      });
      riskScore += 0.5;
    }
    
    // Request size check
    const contentLength = parseInt(
      request.headers.get('content-length') || '0'
    );
    if (contentLength > 10 * 1024 * 1024) {
      issues.push({
        type: 'oversized_request',
        severity: 'medium',
        description: 'Request exceeds maximum allowed size',
        recommendation: 'Reject request with 413 status',
      });
      riskScore += 0.1;
    }
    
    // Check for suspicious headers
    if (this.detectSuspiciousHeaders(request)) {
      issues.push({
        type: 'suspicious_headers',
        severity: 'medium',
        description: 'Suspicious headers detected',
        recommendation: 'Review and potentially block request',
      });
      riskScore += 0.2;
    }
    
    // Geographic anomaly detection
    if (request.cf?.country) {
      const riskCountry = this.isHighRiskCountry(request.cf.country);
      if (riskCountry) {
        issues.push({
          type: 'high_risk_origin',
          severity: 'low',
          description: `Request from high-risk country: ${request.cf.country}`,
          recommendation: 'Apply additional verification',
        });
        riskScore += 0.1;
      }
    }
    
    return {
      valid: issues.length === 0 || riskScore < 0.5,
      issues,
      riskScore: Math.min(riskScore, 1.0),
    };
  }
  
  async authenticateToken(token: string): Promise<AuthResult> {
    try {
      const result = await this.tokenVerifier.verify(token);
      
      if (result.valid) {
        await this.auditLog({
          type: 'authentication_success',
          timestamp: new Date(),
          source: 'edge-security',
          details: { userId: result.userId },
          riskLevel: 'low',
        });
      } else {
        await this.auditLog({
          type: 'authentication_failure',
          timestamp: new Date(),
          source: 'edge-security',
          details: { error: result.error },
          riskLevel: 'medium',
        });
      }
      
      return result;
    } catch (error) {
      await this.auditLog({
        type: 'authentication_error',
        timestamp: new Date(),
        source: 'edge-security',
        details: { error: (error as Error).message },
        riskLevel: 'high',
      });
      
      return {
        authenticated: false,
        error: 'Authentication failed',
      };
    }
  }
  
  async encryptData(data: string): Promise<EncryptedData> {
    return this.encryptionService.encrypt(data);
  }
  
  async decryptData(encrypted: EncryptedData): Promise<string> {
    return this.encryptionService.decrypt(encrypted);
  }
  
  async checkRateLimit(key: string): Promise<RateLimitResult> {
    return this.rateLimiter.check(key);
  }
  
  async auditLog(event: SecurityEvent): Promise<void> {
    await this.auditLogger.log(event);
  }
  
  private detectPathTraversal(path: string): boolean {
    const patterns = [
      /\.\./,
      /%2e%2e/i,
      /\.\.%2f/i,
      /%2e%2e%2f/i,
      /\.\.\\/,
    ];
    
    return patterns.some((pattern) => pattern.test(path));
  }
  
  private detectXSS(request: Request): boolean {
    const url = new URL(request.url);
    const body = request.body;
    
    const xssPatterns = [
      /<script[^>]*>/i,
      /javascript:/i,
      /on\w+\s*=/i,
      /eval\s*\(/i,
      /document\.cookie/i,
    ];
    
    const checkString = (str: string) =>
      xssPatterns.some((pattern) => pattern.test(str));
    
    if (checkString(url.pathname) || checkString(url.search)) {
      return true;
    }
    
    // Would need to read body for POST requests
    return false;
  }
  
  private detectSQLInjection(request: Request): boolean {
    const url = new URL(request.url);
    
    const sqlPatterns = [
      /union\s+select/i,
      /or\s+1\s*=\s*1/i,
      /drop\s+table/i,
      /insert\s+into/i,
      /delete\s+from/i,
      /--\s*$/,
      /;\s*drop/i,
    ];
    
    const checkString = (str: string) =>
      sqlPatterns.some((pattern) => pattern.test(str));
    
    return checkString(url.pathname) || checkString(url.search);
  }
  
  private detectSuspiciousHeaders(request: Request): boolean {
    const suspiciousHeaders = [
      'x-forwarded-for',
      'x-real-ip',
      'x-originating-ip',
      'x-remote-ip',
      'x-remote-addr',
    ];
    
    // Check for header manipulation
    for (const header of suspiciousHeaders) {
      const value = request.headers.get(header);
      if (value && value.split(',').length > 3) {
        return true;
      }
    }
    
    // Check for missing required headers
    if (!request.headers.get('user-agent')) {
      return true;
    }
    
    return false;
  }
  
  private isHighRiskCountry(country: string): boolean {
    const highRiskCountries = ['XX', 'YY']; // Placeholder
    return highRiskCountries.includes(country);
  }
}

class RateLimiter {
  private store: Map<string, { count: number; resetAt: number }> = new Map();
  private config: RateLimitConfig;
  
  constructor(config: RateLimitConfig) {
    this.config = config;
    
    // Clean up expired entries periodically
    setInterval(() => this.cleanup(), 60000);
  }
  
  async check(key: string): Promise<RateLimitResult> {
    const now = Date.now();
    const entry = this.store.get(key);
    
    if (!entry || now > entry.resetAt) {
      // New window or expired
      this.store.set(key, {
        count: 1,
        resetAt: now + this.config.windowMs,
      });
      
      return {
        allowed: true,
        limit: this.config.maxRequests,
        remaining: this.config.maxRequests - 1,
        resetAt: new Date(now + this.config.windowMs),
      };
    }
    
    if (entry.count >= this.config.maxRequests) {
      return {
        allowed: false,
        limit: this.config.maxRequests,
        remaining: 0,
        resetAt: new Date(entry.resetAt),
      };
    }
    
    entry.count++;
    
    return {
      allowed: true,
      limit: this.config.maxRequests,
      remaining: this.config.maxRequests - entry.count,
      resetAt: new Date(entry.resetAt),
    };
  }
  
  private cleanup(): void {
    const now = Date.now();
    
    for (const [key, entry] of this.store) {
      if (now > entry.resetAt) {
        this.store.delete(key);
      }
    }
  }
}

class TokenVerifier {
  private config: AuthConfig;
  private jwksClient: any;
  
  constructor(config: AuthConfig) {
    this.config = config;
  }
  
  async verify(token: string): Promise<AuthResult> {
    try {
      // Decode JWT header to get key ID
      const header = this.decodeHeader(token);
      
      // Get signing key
      const key = await this.getSigningKey(header.kid);
      
      // Verify token
      const payload = await this.verifyToken(token, key);
      
      // Check expiration
      if (payload.exp && payload.exp < Date.now() / 1000) {
        return {
          authenticated: false,
          error: 'Token expired',
        };
      }
      
      return {
        authenticated: true,
        userId: payload.sub,
        permissions: payload.permissions || [],
        expiresAt: new Date(payload.exp * 1000),
      };
    } catch (error) {
      return {
        authenticated: false,
        error: (error as Error).message,
      };
    }
  }
  
  private decodeHeader(token: string): any {
    const parts = token.split('.');
    if (parts.length !== 3) {
      throw new Error('Invalid token format');
    }
    
    return JSON.parse(atob(parts[0]));
  }
  
  private async getSigningKey(kid: string): Promise<CryptoKey> {
    // Would fetch from JWKS endpoint
    throw new Error('Not implemented');
  }
  
  private async verifyToken(
    token: string,
    key: CryptoKey
  ): Promise<any> {
    // Would verify JWT signature
    throw new Error('Not implemented');
  }
}

class EncryptionService {
  private config: EncryptionConfig;
  private keyCache: Map<string, CryptoKey> = new Map();
  
  constructor(config: EncryptionConfig) {
    this.config = config;
  }
  
  async encrypt(data: string): Promise<EncryptedData> {
    const key = await this.getKey();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const encoded = new TextEncoder().encode(data);
    
    const encrypted = await crypto.subtle.encrypt(
      {
        name: this.config.algorithm,
        iv,
      },
      key,
      encoded
    );
    
    return {
      iv: Array.from(iv),
      data: Array.from(new Uint8Array(encrypted)),
      algorithm: this.config.algorithm,
    };
  }
  
  async decrypt(encrypted: EncryptedData): Promise<string> {
    const key = await this.getKey();
    const iv = new Uint8Array(encrypted.iv);
    const data = new Uint8Array(encrypted.data);
    
    const decrypted = await crypto.subtle.decrypt(
      {
        name: encrypted.algorithm,
        iv,
      },
      key,
      data
    );
    
    return new TextDecoder().decode(decrypted);
  }
  
  private async getKey(): Promise<CryptoKey> {
    const keyId = this.config.keyId;
    
    if (this.keyCache.has(keyId)) {
      return this.keyCache.get(keyId)!;
    }
    
    // Would fetch key from key management service
    const key = await this.fetchKey(keyId);
    this.keyCache.set(keyId, key);
    
    return key;
  }
  
  private async fetchKey(keyId: string): Promise<CryptoKey> {
    // Placeholder - would fetch from KMS
    return crypto.subtle.generateKey(
      {
        name: this.config.algorithm,
        length: 256,
      },
      true,
      ['encrypt', 'decrypt']
    );
  }
}

class AuditLogger {
  private config: AuditConfig;
  private buffer: SecurityEvent[] = [];
  private flushInterval: number;
  
  constructor(config: AuditConfig) {
    this.config = config;
    this.flushInterval = config.flushIntervalMs || 5000;
    
    // Start flush interval
    setInterval(() => this.flush(), this.flushInterval);
  }
  
  async log(event: SecurityEvent): Promise<void> {
    this.buffer.push(event);
    
    if (event.riskLevel === 'critical') {
      await this.flush();
    }
  }
  
  private async flush(): Promise<void> {
    if (this.buffer.length === 0) {
      return;
    }
    
    const events = [...this.buffer];
    this.buffer = [];
    
    try {
      await this.sendToAuditService(events);
    } catch (error) {
      console.error('Failed to flush audit logs:', error);
      // Re-add events to buffer
      this.buffer.unshift(...events);
    }
  }
  
  private async sendToAuditService(events: SecurityEvent[]): Promise<void> {
    // Would send to audit service
    console.log('Sending audit events:', events.length);
  }
}

class ThreatDetector {
  private config: ThreatConfig;
  private patterns: ThreatPattern[];
  
  constructor(config: ThreatConfig) {
    this.config = config;
    this.patterns = this.loadPatterns();
  }
  
  analyze(request: Request): ThreatAnalysis {
    const threats: Threat[] = [];
    
    // Analyze request patterns
    for (const pattern of this.patterns) {
      if (this.matchesPattern(request, pattern)) {
        threats.push({
          pattern: pattern.name,
          severity: pattern.severity,
          confidence: pattern.confidence,
        });
      }
    }
    
    return {
      threats,
      riskScore: this.calculateRiskScore(threats),
      recommendation: this.getRecommendation(threats),
    };
  }
  
  private matchesPattern(
    request: Request,
    pattern: ThreatPattern
  ): boolean {
    // Pattern matching logic
    return false;
  }
  
  private calculateRiskScore(threats: Threat[]): number {
    if (threats.length === 0) {
      return 0;
    }
    
    const maxSeverity = threats.reduce((max, threat) => {
      const severityScore = {
        low: 0.25,
        medium: 0.5,
        high: 0.75,
        critical: 1.0,
      };
      return Math.max(max, severityScore[threat.severity]);
    }, 0);
    
    return maxSeverity;
  }
  
  private getRecommendation(threats: Threat[]): string {
    if (threats.length === 0) {
      return 'No threats detected';
    }
    
    const criticalThreats = threats.filter((t) => t.severity === 'critical');
    if (criticalThreats.length > 0) {
      return 'Block request and alert security team';
    }
    
    const highThreats = threats.filter((t) => t.severity === 'high');
    if (highThreats.length > 0) {
      return 'Apply additional verification';
    }
    
    return 'Continue with caution';
  }
  
  private loadPatterns(): ThreatPattern[] {
    return [
      {
        name: 'sql_injection',
        regex: /union\s+select|or\s+1\s*=\s*1|drop\s+table/i,
        severity: 'critical',
        confidence: 0.9,
      },
      {
        name: 'xss_attempt',
        regex: /<script|javascript:|on\w+\s*=/i,
        severity: 'high',
        confidence: 0.8,
      },
      {
        name: 'path_traversal',
        regex: /\.\.\/|\.\.\\|%2e%2e/i,
        severity: 'high',
        confidence: 0.85,
      },
    ];
  }
}

interface SecurityConfig {
  rateLimitConfig: RateLimitConfig;
  authConfig: AuthConfig;
  encryptionConfig: EncryptionConfig;
  auditConfig: AuditConfig;
  threatConfig: ThreatConfig;
}

interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
}

interface AuthConfig {
  jwksUri: string;
  issuer: string;
  audience: string;
}

interface EncryptionConfig {
  algorithm: string;
  keyId: string;
  keyManagementUrl: string;
}

interface AuditConfig {
  endpoint: string;
  flushIntervalMs: number;
  batchSize: number;
}

interface ThreatConfig {
  patternsUrl: string;
  updateIntervalMs: number;
}

interface ThreatPattern {
  name: string;
  regex: RegExp;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
}

interface Threat {
  pattern: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  confidence: number;
}

interface ThreatAnalysis {
  threats: Threat[];
  riskScore: number;
  recommendation: string;
}
```

---

## 14.9 Rate Limiting

### Rate Limiting Avançado no Edge

```typescript
// edge-rate-limiting/src/rate-limiter.ts
interface RateLimiter {
  check(key: string): Promise<RateLimitResult>;
  reset(key: string): Promise<void>;
  getUsage(key: string): Promise<UsageStats>;
}

interface RateLimitResult {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetAt: Date;
  retryAfter?: number;
}

interface UsageStats {
  totalRequests: number;
  blockedRequests: number;
  uniqueKeys: number;
  averageRequestsPerMinute: number;
}

class SlidingWindowRateLimiter implements RateLimiter {
  private store: KVNamespace;
  private config: SlidingWindowConfig;
  
  constructor(store: KVNamespace, config: SlidingWindowConfig) {
    this.store = store;
    this.config = config;
  }
  
  async check(key: string): Promise<RateLimitResult> {
    const now = Date.now();
    const windowMs = this.config.windowMs;
    const maxRequests = this.config.maxRequests;
    
    // Get current window data
    const windowKey = this.getWindowKey(key, now);
    const windowData = await this.store.get<WindowData>(windowKey, 'json');
    
    if (!windowData) {
      // First request in window
      const newData: WindowData = {
        count: 1,
        windowStart: now,
        requests: [now],
      };
      
      await this.store.put(windowKey, JSON.stringify(newData), {
        expirationTtl: Math.ceil(windowMs / 1000) + 60,
      });
      
      return {
        allowed: true,
        limit: maxRequests,
        remaining: maxRequests - 1,
        resetAt: new Date(now + windowMs),
      };
    }
    
    // Filter requests within current window
    const windowRequests = windowData.requests.filter(
      (timestamp) => now - timestamp < windowMs
    );
    
    if (windowRequests.length >= maxRequests) {
      // Rate limit exceeded
      const oldestRequest = windowRequests[0];
      const retryAfter = Math.ceil((oldestRequest + windowMs - now) / 1000);
      
      return {
        allowed: false,
        limit: maxRequests,
        remaining: 0,
        resetAt: new Date(oldestRequest + windowMs),
        retryAfter,
      };
    }
    
    // Add new request
    windowRequests.push(now);
    
    const updatedData: WindowData = {
      count: windowRequests.length,
      windowStart: windowData.windowStart,
      requests: windowRequests,
    };
    
    await this.store.put(windowKey, JSON.stringify(updatedData), {
      expirationTtl: Math.ceil(windowMs / 1000) + 60,
    });
    
    return {
      allowed: true,
      limit: maxRequests,
      remaining: maxRequests - windowRequests.length,
      resetAt: new Date(now + windowMs),
    };
  }
  
  async reset(key: string): Promise<void> {
    const now = Date.now();
    const windowKey = this.getWindowKey(key, now);
    await this.store.delete(windowKey);
  }
  
  async getUsage(key: string): Promise<UsageStats> {
    const now = Date.now();
    const windowKey = this.getWindowKey(key, now);
    const windowData = await this.store.get<WindowData>(windowKey, 'json');
    
    if (!windowData) {
      return {
        totalRequests: 0,
        blockedRequests: 0,
        uniqueKeys: 0,
        averageRequestsPerMinute: 0,
      };
    }
    
    const windowMs = this.config.windowMs;
    const windowRequests = windowData.requests.filter(
      (timestamp) => now - timestamp < windowMs
    );
    
    return {
      totalRequests: windowRequests.length,
      blockedRequests: 0,
      uniqueKeys: 1,
      averageRequestsPerMinute:
        (windowRequests.length / windowMs) * 60000,
    };
  }
  
  private getWindowKey(key: string, timestamp: number): string {
    const windowMs = this.config.windowMs;
    const windowNumber = Math.floor(timestamp / windowMs);
    return `ratelimit:${key}:${windowNumber}`;
  }
}

interface WindowData {
  count: number;
  windowStart: number;
  requests: number[];
}

interface SlidingWindowConfig {
  windowMs: number;
  maxRequests: number;
}

class TokenBucketRateLimiter implements RateLimiter {
  private store: KVNamespace;
  private config: TokenBucketConfig;
  
  constructor(store: KVNamespace, config: TokenBucketConfig) {
    this.store = store;
    this.config = config;
  }
  
  async check(key: string): Promise<RateLimitResult> {
    const now = Date.now();
    const bucket = await this.getBucket(key);
    
    if (!bucket) {
      // Initialize bucket
      const newBucket: TokenBucket = {
        tokens: this.config.maxTokens - 1,
        lastRefill: now,
      };
      
      await this.store.put(key, JSON.stringify(newBucket), {
        expirationTtl: Math.ceil(this.config.refillIntervalMs / 1000) * 2,
      });
      
      return {
        allowed: true,
        limit: this.config.maxTokens,
        remaining: newBucket.tokens,
        resetAt: new Date(now + this.config.refillIntervalMs),
      };
    }
    
    // Refill tokens
    const elapsed = now - bucket.lastRefill;
    const refillAmount = Math.floor(
      (elapsed / this.config.refillIntervalMs) * this.config.refillRate
    );
    
    if (refillAmount > 0) {
      bucket.tokens = Math.min(
        this.config.maxTokens,
        bucket.tokens + refillAmount
      );
      bucket.lastRefill = now;
    }
    
    // Check if token available
    if (bucket.tokens <= 0) {
      const timeUntilRefill =
        this.config.refillIntervalMs - (now - bucket.lastRefill);
      
      return {
        allowed: false,
        limit: this.config.maxTokens,
        remaining: 0,
        resetAt: new Date(now + timeUntilRefill),
        retryAfter: Math.ceil(timeUntilRefill / 1000),
      };
    }
    
    // Consume token
    bucket.tokens--;
    
    await this.store.put(key, JSON.stringify(bucket), {
      expirationTtl: Math.ceil(this.config.refillIntervalMs / 1000) * 2,
    });
    
    return {
      allowed: true,
      limit: this.config.maxTokens,
      remaining: bucket.tokens,
      resetAt: new Date(now + this.config.refillIntervalMs),
    };
  }
  
  async reset(key: string): Promise<void> {
    await this.store.delete(key);
  }
  
  async getUsage(key: string): Promise<UsageStats> {
    const bucket = await this.getBucket(key);
    
    if (!bucket) {
      return {
        totalRequests: 0,
        blockedRequests: 0,
        uniqueKeys: 0,
        averageRequestsPerMinute: 0,
      };
    }
    
    const usedTokens = this.config.maxTokens - bucket.tokens;
    
    return {
      totalRequests: usedTokens,
      blockedRequests: 0,
      uniqueKeys: 1,
      averageRequestsPerMinute:
        (usedTokens / this.config.refillIntervalMs) * 60000,
    };
  }
  
  private async getBucket(key: string): Promise<TokenBucket | null> {
    const data = await this.store.get(key, 'json');
    return data as TokenBucket | null;
  }
}

interface TokenBucket {
  tokens: number;
  lastRefill: number;
}

interface TokenBucketConfig {
  maxTokens: number;
  refillRate: number;
  refillIntervalMs: number;
}

class MultiTierRateLimiter implements RateLimiter {
  private tiers: RateLimiter[];
  private keyExtractor: (key: string) => string;
  
  constructor(
    tiers: RateLimiter[],
    keyExtractor: (key: string) => string
  ) {
    this.tiers = tiers;
    this.keyExtractor = keyExtractor;
  }
  
  async check(key: string): Promise<RateLimitResult> {
    const extractedKey = this.keyExtractor(key);
    
    for (const tier of this.tiers) {
      const result = await tier.check(extractedKey);
      
      if (!result.allowed) {
        return result;
      }
    }
    
    // All tiers passed
    const lastTier = this.tiers[this.tiers.length - 1];
    return lastTier.check(extractedKey);
  }
  
  async reset(key: string): Promise<void> {
    const extractedKey = this.keyExtractor(key);
    
    for (const tier of this.tiers) {
      await tier.reset(extractedKey);
    }
  }
  
  async getUsage(key: string): Promise<UsageStats> {
    const extractedKey = this.keyExtractor(key);
    const lastTier = this.tiers[this.tiers.length - 1];
    
    return lastTier.getUsage(extractedKey);
  }
}

class AdaptiveRateLimiter implements RateLimiter {
  private baseLimiter: RateLimiter;
  private metricsCollector: MetricsCollector;
  private adjustmentFactor: number;
  
  constructor(
    baseLimiter: RateLimiter,
    metricsCollector: MetricsCollector,
    adjustmentFactor: number = 0.1
  ) {
    this.baseLimiter = baseLimiter;
    this.metricsCollector = metricsCollector;
    this.adjustmentFactor = adjustmentFactor;
  }
  
  async check(key: string): Promise<RateLimitResult> {
    // Get current metrics
    const metrics = await this.metricsCollector.getMetrics();
    
    // Adjust rate limit based on system load
    const adjustedLimiter = this.adjustForLoad(metrics);
    
    return adjustedLimiter.check(key);
  }
  
  async reset(key: string): Promise<void> {
    await this.baseLimiter.reset(key);
  }
  
  async getUsage(key: string): Promise<UsageStats> {
    return this.baseLimiter.getUsage(key);
  }
  
  private adjustForLoad(metrics: SystemMetrics): RateLimiter {
    const loadFactor = metrics.cpuUsage / 100;
    
    if (loadFactor > 0.8) {
      // High load - reduce rate limits
      return new AdjustedRateLimiter(
        this.baseLimiter,
        1 - this.adjustmentFactor * 2
      );
    } else if (loadFactor < 0.3) {
      // Low load - increase rate limits
      return new AdjustedRateLimiter(
        this.baseLimiter,
        1 + this.adjustmentFactor
      );
    }
    
    return this.baseLimiter;
  }
}

class AdjustedRateLimiter implements RateLimiter {
  private baseLimiter: RateLimiter;
  private adjustmentFactor: number;
  
  constructor(baseLimiter: RateLimiter, adjustmentFactor: number) {
    this.baseLimiter = baseLimiter;
    this.adjustmentFactor = adjustmentFactor;
  }
  
  async check(key: string): Promise<RateLimitResult> {
    // Would adjust limits based on factor
    return this.baseLimiter.check(key);
  }
  
  async reset(key: string): Promise<void> {
    await this.baseLimiter.reset(key);
  }
  
  async getUsage(key: string): Promise<UsageStats> {
    return this.baseLimiter.getUsage(key);
  }
}

interface MetricsCollector {
  getMetrics(): Promise<SystemMetrics>;
}

interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  requestRate: number;
  errorRate: number;
}
```

---

## 14.10 Complete Edge Application

### Aplicação Edge Completa com WASM

```typescript
// complete-edge-app/src/index.ts
interface EdgeApplication {
  handleRequest(request: Request): Promise<Response>;
  initialize(): Promise<void>;
  shutdown(): Promise<void>;
}

class WasmEdgeApplication implements EdgeApplication {
  private config: AppConfig;
  private security: EdgeSecurityManager;
  private cache: EdgeKVStorage;
  private rateLimiter: RateLimiter;
  private wasmModule: WebAssembly.Module | null = null;
  private metrics: MetricsCollector;
  private auditLogger: AuditLogger;
  
  constructor(config: AppConfig) {
    this.config = config;
    this.security = new EdgeSecurityManager(config.security);
    this.cache = new CloudflareKVStorage(config.cacheNamespace);
    this.rateLimiter = new SlidingWindowRateLimiter(
      config.rateLimitNamespace,
      config.rateLimit
    );
    this.metrics = new CloudflareMetrics(config.analyticsDataset);
    this.auditLogger = new CloudflareAuditLogger(config.auditNamespace);
  }
  
  async initialize(): Promise<void> {
    // Load WASM module
    const wasmBytes = await fetch(this.config.wasmModuleUrl);
    this.wasmModule = await WebAssembly.compile(
      await wasmBytes.arrayBuffer()
    );
    
    console.log('WASM module loaded successfully');
  }
  
  async shutdown(): Promise<void> {
    // Cleanup resources
    console.log('Shutting down edge application');
  }
  
  async handleRequest(request: Request): Promise<Response> {
    const startTime = Date.now();
    const requestId = this.generateRequestId();
    
    try {
      // Security validation
      const securityCheck = this.security.validateRequest(request);
      if (!securityCheck.valid) {
        await this.auditLogger.log({
          type: 'security_violation',
          timestamp: new Date(),
          source: 'edge-app',
          details: {
            requestId,
            issues: securityCheck.issues,
            riskScore: securityCheck.riskScore,
          },
          riskLevel: securityCheck.riskScore > 0.7 ? 'critical' : 'high',
        });
        
        return new Response(
          JSON.stringify({
            error: 'Request rejected',
            requestId,
          }),
          {
            status: 403,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
      
      // Rate limiting
      const clientIp =
        request.headers.get('cf-connecting-ip') || 'unknown';
      const rateLimitResult = await this.rateLimiter.check(clientIp);
      
      if (!rateLimitResult.allowed) {
        return new Response(
          JSON.stringify({
            error: 'Rate limit exceeded',
            retryAfter: rateLimitResult.retryAfter,
          }),
          {
            status: 429,
            headers: {
              'Content-Type': 'application/json',
              'X-RateLimit-Limit': rateLimitResult.limit.toString(),
              'X-RateLimit-Remaining': rateLimitResult.remaining.toString(),
              'X-RateLimit-Reset': rateLimitResult.resetAt.toISOString(),
              'Retry-After': (rateLimitResult.retryAfter || 60).toString(),
            },
          }
        );
      }
      
      // Authentication (if required)
      const authHeader = request.headers.get('authorization');
      if (authHeader && this.config.requireAuth) {
        const token = authHeader.replace('Bearer ', '');
        const authResult = await this.security.authenticateToken(token);
        
        if (!authResult.authenticated) {
          return new Response(
            JSON.stringify({
              error: 'Authentication failed',
              message: authResult.error,
            }),
            {
              status: 401,
              headers: { 'Content-Type': 'application/json' },
            }
          );
        }
      }
      
      // Process request
      const response = await this.processRequest(request, requestId);
      
      // Add security headers
      this.addSecurityHeaders(response);
      
      // Add timing headers
      const duration = Date.now() - startTime;
      response.headers.set('X-Request-ID', requestId);
      response.headers.set('X-Response-Time', `${duration}ms`);
      response.headers.set('X-Edge-Location', request.cf?.colo || 'unknown');
      
      // Record metrics
      await this.metrics.record({
        requestId,
        path: new URL(request.url).pathname,
        method: request.method,
        status: response.status,
        duration,
        cacheHit: response.headers.get('X-Cache') === 'HIT',
      });
      
      return response;
    } catch (error) {
      console.error('Request processing error:', error);
      
      await this.auditLogger.log({
        type: 'application_error',
        timestamp: new Date(),
        source: 'edge-app',
        details: {
          requestId,
          error: (error as Error).message,
          stack: (error as Error).stack,
        },
        riskLevel: 'medium',
      });
      
      return new Response(
        JSON.stringify({
          error: 'Internal server error',
          requestId,
        }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  }
  
  private async processRequest(
    request: Request,
    requestId: string
  ): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    
    // Route based on path
    switch (true) {
      case path === '/health':
        return this.handleHealthCheck();
      
      case path.startsWith('/api/data/'):
        return this.handleDataRequest(request);
      
      case path === '/api/process':
        return this.handleProcessRequest(request);
      
      case path === '/api/cache/invalidate':
        return this.handleCacheInvalidation(request);
      
      case path === '/api/metrics':
        return this.handleMetricsRequest(request);
      
      default:
        return new Response('Not Found', { status: 404 });
    }
  }
  
  private handleHealthCheck(): Response {
    const health = {
      status: 'healthy',
      timestamp: new Date().toISOString(),
      version: this.config.version,
      wasmLoaded: this.wasmModule !== null,
    };
    
    return new Response(JSON.stringify(health), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async handleDataRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const pathParts = url.pathname.split('/');
    const id = pathParts[pathParts.length - 1];
    
    // Check cache first
    const cached = await this.cache.get(`data:${id}`);
    if (cached) {
      return new Response(JSON.stringify(cached), {
        headers: {
          'Content-Type': 'application/json',
          'X-Cache': 'HIT',
        },
      });
    }
    
    // Process with WASM
    const result = await this.processWithWasm('fetch_data', { id });
    
    // Cache result
    await this.cache.set(`data:${id}`, result, {
      expirationTtl: this.config.cacheTtl,
    });
    
    return new Response(JSON.stringify(result), {
      headers: {
        'Content-Type': 'application/json',
        'X-Cache': 'MISS',
      },
    });
  }
  
  private async handleProcessRequest(request: Request): Promise<Response> {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }
    
    const body = await request.text();
    
    // Validate request size
    if (body.length > this.config.maxRequestSize) {
      return new Response('Request too large', { status: 413 });
    }
    
    // Process with WASM
    const result = await this.processWithWasm('process', { data: body });
    
    return new Response(JSON.stringify(result), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async handleCacheInvalidation(
    request: Request
  ): Promise<Response> {
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }
    
    const body = await request.json() as { pattern: string };
    
    // Get all cache keys
    const keys = await this.cache.list({ prefix: 'data:' });
    
    // Filter by pattern
    const matchingKeys = keys.filter((key) =>
      key.includes(body.pattern)
    );
    
    // Delete matching keys
    let invalidated = 0;
    for (const key of matchingKeys) {
      await this.cache.delete(key);
      invalidated++;
    }
    
    return new Response(
      JSON.stringify({
        success: true,
        invalidated,
      }),
      {
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
  
  private async handleMetricsRequest(
    request: Request
  ): Promise<Response> {
    const url = new URL(request.url);
    const timeRange = url.searchParams.get('range') || '1h';
    
    const metrics = await this.metrics.getMetrics(timeRange);
    
    return new Response(JSON.stringify(metrics), {
      headers: { 'Content-Type': 'application/json' },
    });
  }
  
  private async processWithWasm(
    function_: string,
    input: any
  ): Promise<any> {
    if (!this.wasmModule) {
      throw new Error('WASM module not loaded');
    }
    
    const memory = new WebAssembly.Memory({ initial: 256, maximum: 1024 });
    
    const imports = {
      env: {
        memory,
        log: (ptr: number, len: number) => {
          const buffer = new Uint8Array(memory.buffer);
          const bytes = buffer.slice(ptr, ptr + len);
          console.log('[WASM]', new TextDecoder().decode(bytes));
        },
      },
    };
    
    const instance = await WebAssembly.instantiate(this.wasmModule, imports);
    const exports = instance.exports as any;
    
    // Write input to WASM memory
    const inputStr = JSON.stringify(input);
    const inputBytes = new TextEncoder().encode(inputStr);
    const inputPtr = exports.allocate(inputBytes.length);
    
    const buffer = new Uint8Array(memory.buffer);
    buffer.set(inputBytes, inputPtr);
    
    // Call function
    const outputPtr = exports[function_](inputPtr, inputBytes.length);
    const outputLen = exports.get_output_length();
    
    // Read output
    const outputBytes = buffer.slice(outputPtr, outputPtr + outputLen);
    const outputStr = new TextDecoder().decode(outputBytes);
    
    // Clean up
    exports.deallocate(inputPtr, inputBytes.length);
    exports.deallocate(outputPtr, outputLen);
    
    return JSON.parse(outputStr);
  }
  
  private addSecurityHeaders(response: Response): void {
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('X-Frame-Options', 'DENY');
    response.headers.set('X-XSS-Protection', '1; mode=block');
    response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    response.headers.set(
      'Permissions-Policy',
      'camera=(), microphone=(), geolocation=()'
    );
    
    if (this.config.environment === 'production') {
      response.headers.set(
        'Strict-Transport-Security',
        'max-age=31536000; includeSubDomains; preload'
      );
    }
  }
  
  private generateRequestId(): string {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substring(2, 8);
    return `req-${timestamp}-${random}`;
  }
}

interface AppConfig {
  environment: string;
  version: string;
  wasmModuleUrl: string;
  cacheNamespace: KVNamespace;
  rateLimitNamespace: KVNamespace;
  analyticsDataset: AnalyticsEngineDataset;
  auditNamespace: KVNamespace;
  rateLimit: SlidingWindowConfig;
  security: SecurityConfig;
  requireAuth: boolean;
  maxRequestSize: number;
  cacheTtl: number;
}

// Worker entry point
export default {
  async fetch(
    request: Request,
    env: Env,
    ctx: ExecutionContext
  ): Promise<Response> {
    const app = new WasmEdgeApplication({
      environment: env.ENVIRONMENT,
      version: '1.0.0',
      wasmModuleUrl: env.WASM_MODULE_URL,
      cacheNamespace: env.CACHE_KV,
      rateLimitNamespace: env.RATE_LIMIT_KV,
      analyticsDataset: env.ANALYTICS,
      auditNamespace: env.AUDIT_KV,
      rateLimit: {
        windowMs: 60000,
        maxRequests: 100,
      },
      security: {
        rateLimitConfig: { windowMs: 60000, maxRequests: 100 },
        authConfig: {
          jwksUri: env.JWKS_URI,
          issuer: env.AUTH_ISSUER,
          audience: env.AUTH_AUDIENCE,
        },
        encryptionConfig: {
          algorithm: 'AES-GCM',
          keyId: env.ENCRYPTION_KEY_ID,
          keyManagementUrl: env.KMS_URL,
        },
        auditConfig: {
          endpoint: env.AUDIT_ENDPOINT,
          flushIntervalMs: 5000,
          batchSize: 100,
        },
        threatConfig: {
          patternsUrl: env.THREAT_PATTERNS_URL,
          updateIntervalMs: 300000,
        },
      },
      requireAuth: env.REQUIRE_AUTH === 'true',
      maxRequestSize: 10 * 1024 * 1024,
      cacheTtl: 300,
    });
    
    await app.initialize();
    
    const response = await app.handleRequest(request);
    
    ctx.waitUntil(app.shutdown());
    
    return response;
  },
};

interface Env {
  ENVIRONMENT: string;
  WASM_MODULE_URL: string;
  CACHE_KV: KVNamespace;
  RATE_LIMIT_KV: KVNamespace;
  ANALYTICS: AnalyticsEngineDataset;
  AUDIT_KV: KVNamespace;
  JWKS_URI: string;
  AUTH_ISSUER: string;
  AUTH_AUDIENCE: string;
  ENCRYPTION_KEY_ID: string;
  KMS_URL: string;
  AUDIT_ENDPOINT: string;
  THREAT_PATTERNS_URL: string;
  REQUIRE_AUTH: string;
}
```

---

## Conclusão

Neste capítulo, exploramos como o WebAssembly está sendo utilizado no edge computing através de plataformas como Cloudflare Workers, Fastly Compute e Fermyon Spin. Cobrimos desde a arquitetura básica até técnicas avançadas de otimização de冷启动, armazenamento distribuído e segurança no edge.

Os pontos-chave abordados incluem:

1. **Cloudflare Workers**: Arquitetura de isolamento com V8 e WASM
2. **Fastly Compute**: Edge computing nativo com WASM
3. **Fermyon Spin**: Framework de microserviços WASM
4. **Edge vs Serverless**: Comparação detalhada de trade-offs
5. **Cold Start Optimization**: Técnicas para inicialização rápida
6. **KV Storage at Edge**: Armazenamento key-value distribuído
7. **Durable Objects**: Estado persistente no edge
8. **Security at Edge**: Múltiplas camadas de segurança
9. **Rate Limiting**: Controle de taxa avançado
10. **Complete Application**: Integração de todos os componentes

O edge computing com WASM oferece benefícios significativos em termos de latência, segurança e escalabilidade. No entanto, requer consideração cuidadosa de trade-offs como consistência, complexidade operacional e custos.

No próximo capítulo, exploraremos como o WebAssembly está sendo utilizado em blockchain e smart contracts.
---

*[Capítulo anterior: 13 — Plugins Seguros](13-plugins-seguros.md)*
*[Próximo capítulo: 15 — Blockchain](15-blockchain.md)*
