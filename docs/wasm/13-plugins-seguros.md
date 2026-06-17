# Capítulo 13: Plugins Seguros

## Introdução

O paradigma de plugins representa uma das aplicações mais promissoras e desafiadoras do WebAssembly. Ao permitir que código de terceiros seja executado dentro de ambientes controlados, o Wasm oferece um modelo de extensibilidade que combina flexibilidade com segurança. Este capítulo explora como construir sistemas de plugins seguros usando WebAssembly, desde hospedeiros de plugins como Envoy e VS Code até marketplaces completos com verificação criptográfica e auditoria.

A segurança em sistemas de plugins é um desafio fundamental da computação moderna. Cada extensão, módulo ou plugin que adicionamos a um sistema aumenta a superfície de ataque potencial. O WebAssembly aborda esse problema oferecendo um modelo de sandboxing nativo, memória isolada e controle granular de capacidades que permite executar código de terceiros com confiança significativamente maior do que as abordagens tradicionais baseadas em processos separados ou isolamento de memória parcial.

Vamos explorar como diferentes plataformas e frameworks implementam plugins usando WASM, as técnicas de segurança disponíveis e como construir um sistema completo que balanceie segurança, performance e usabilidade.

---

## 13.1 Envoy WASM Plugins

### Visão Geral da Arquitetura

O Envoy Proxy é um dos proxy de serviço modernos mais utilizados, sendo a base do Istio e muitas outras soluções de service mesh. Sua arquitetura modular permite extensão através de WASM plugins que podem interceptar e modificar o tráfego HTTP/gRPC de forma segura e performática.

### Estrutura Básica de um Plugin Envoy

```rust
// envoy-wasm-plugin/src/lib.rs
use proxy_wasm::traits::*;
use proxy_wasm::types::*;
use std::time::Duration;

pub struct TrafficInterceptor {
    context_id: u32,
    config: PluginConfig,
    metrics: MetricsCollector,
}

struct PluginConfig {
    max_request_size: usize,
    blocked_patterns: Vec<String>,
    rate_limit: u32,
    log_level: LogLevel,
}

struct MetricsCollector {
    requests_total: MetricsCounter,
    blocked_requests: MetricsCounter,
    latency_histogram: MetricsHistogram,
}

impl Default for PluginConfig {
    fn default() -> Self {
        Self {
            max_request_size: 1024 * 1024, // 1MB
            blocked_patterns: Vec::new(),
            rate_limit: 100,
            log_level: LogLevel::Info,
        }
    }
}

impl Context for TrafficInterceptor {
    fn on_log(&mut self) {
        proxy_wasm::log LogLevel::Info, "Request processing completed");
    }
}

impl HttpContext for TrafficInterceptor {
    fn on_http_request_headers(&mut self, num_headers: usize) -> Action {
        self.metrics.requests_total.increment();
        
        // Extract and validate request headers
        let content_length = self
            .get_http_request_header("content-length")
            .and_then(|v| v.parse::<usize>().ok())
            .unwrap_or(0);
            
        if content_length > self.config.max_request_size {
            self.metrics.blocked_requests.increment();
            self.send_http_response(
                413,
                vec![("content-type".to_string(), "text/plain".to_string())],
                Some(b"Request too large"),
            );
            return Action::Pause;
        }
        
        // Pattern matching for blocked content
        if let Some(path) = self.get_http_request_header(":path") {
            for pattern in &self.config.blocked_patterns {
                if path.contains(pattern) {
                    self.metrics.blocked_requests.increment();
                    proxy_wasm::log!(
                        LogLevel::Warn,
                        "Blocked request matching pattern: {}",
                        pattern
                    );
                    self.send_http_response(
                        403,
                        vec![("content-type".to_string(), "text/plain".to_string())],
                        Some(b"Forbidden"),
                    );
                    return Action::Pause;
                }
            }
        }
        
        // Add custom headers
        self.add_http_request_header("x-plugin-version", "1.0.0");
        self.add_http_request_header("x-request-id", &generate_request_id());
        
        Action::Continue
    }
    
    fn on_http_response_headers(&mut self, num_headers: usize) -> Action {
        // Remove sensitive headers from upstream
        self.remove_http_response_header("x-powered-by");
        self.remove_http_response_header("server");
        
        // Add security headers
        self.add_http_response_header("x-content-type-options", "nosniff");
        self.add_http_response_header("x-frame-options", "DENY");
        
        Action::Continue
    }
    
    fn on_http_response_body(&mut self, body_size: usize, end_of_stream: bool) -> Action {
        if end_of_stream {
            self.metrics.latency_histogram.record(
                self.get_property_str(["request", "time_to_last_byte"])
                    .and_then(|v| v.parse::<u64>().ok())
                    .unwrap_or(0)
            );
        }
        Action::Continue
    }
}

impl RootContext for TrafficInterceptor {
    fn on_configure(&mut self, plugin_config_size: usize) -> bool {
        if plugin_config_size == 0 {
            return true;
        }
        
        let config_bytes = self.get_plugin_configuration().unwrap();
        match parse_config(&config_bytes) {
            Ok(config) => {
                self.config = config;
                self.metrics = init_metrics();
                true
            }
            Err(e) => {
                proxy_wasm::log!(
                    LogLevel::Error,
                    "Failed to parse plugin configuration: {}",
                    e
                );
                false
            }
        }
    }
    
    fn create_http_context(&mut self, _context_id: u32) -> Option<Box<dyn HttpContext>> {
        Some(Box::new(TrafficInterceptor {
            context_id: _context_id,
            config: self.config.clone(),
            metrics: self.metrics.clone(),
        }))
    }
    
    fn on_tick(&mut self) {
        // Periodic cleanup and metric reporting
        self.cleanup_expired_entries();
        self.report_metrics();
    }
}

fn parse_config(data: &[u8]) -> Result<PluginConfig, String> {
    let config_str = std::str::from_utf8(data)
        .map_err(|e| format!("Invalid UTF-8: {}", e))?;
    
    let config: PluginConfig = serde_json::from_str(config_str)
        .map_err(|e| format!("JSON parse error: {}", e))?;
    
    if config.max_request_size > 10 * 1024 * 1024 {
        return Err("max_request_size exceeds 10MB limit".to_string());
    }
    
    if config.rate_limit > 10000 {
        return Err("rate_limit exceeds maximum allowed value".to_string());
    }
    
    Ok(config)
}

fn generate_request_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    format!("req-{:x}-{:x}", timestamp, rand::random::<u32>())
}

proxy_wasm::main! {{
    proxy_wasm::set_root_context(|_| -> Box<dyn RootContext> {
        Box::new(TrafficInterceptor {
            context_id: 0,
            config: PluginConfig::default(),
            metrics: MetricsCollector::new(),
        })
    });
}}
```

### Configuration YAML do Envoy

```yaml
# envoy-config.yaml
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 10000
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                stat_prefix: ingress_http
                route_config:
                  name: local_route
                  virtual_hosts:
                    - name: local_service
                      domains: ["*"]
                      routes:
                        - match: { prefix: "/" }
                          route: { cluster: upstream_service }
                http_filters:
                  - name: envoy.filters.http.wasm
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.wasm.v3.Wasm
                      config:
                        name: "traffic_interceptor"
                        configuration:
                          "@type": type.googleapis.com/google.protobuf.StringValue
                          value: |
                            {
                              "max_request_size": 5242880,
                              "blocked_patterns": ["/admin", "/.env", "/debug"],
                              "rate_limit": 500,
                              "log_level": "warn"
                            }
                        vm_config:
                          runtime: "envoy.wasm.runtime.wasmtime"
                          code:
                            local:
                              filename: "/etc/envoy/plugins/traffic_interceptor.wasm"
                          configuration:
                            "@type": type.googleapis.com/google.protobuf.Struct
                  - name: envoy.filters.http.router
                    typed_config:
                      "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
```

### Sandboxing e Isolamento

O modelo de sandboxing do Envoy WASM oferece várias camadas de proteção:

```rust
// security-policies/src/sandbox.rs
use std::collections::HashMap;

pub struct WasmSandbox {
    memory_limit: usize,
    cpu_time_limit: Duration,
    network_access: bool,
    filesystem_access: FileSystemPolicy,
    allowed_syscalls: Vec<Syscall>,
}

pub enum FileSystemPolicy {
    ReadOnly(Vec<String>),
    WriteWhitelist(Vec<String>),
    NoAccess,
}

impl WasmSandbox {
    pub fn new() -> Self {
        Self {
            memory_limit: 64 * 1024 * 1024, // 64MB
            cpu_time_limit: Duration::from_millis(100),
            network_access: false,
            filesystem_access: FileSystemPolicy::NoAccess,
            allowed_syscalls: Vec::new(),
        }
    }
    
    pub fn validate_plugin(&self, plugin: &WasmPlugin) -> Result<(), SandboxViolation> {
        // Check memory requirements
        if plugin.estimated_memory_usage() > self.memory_limit {
            return Err(SandboxViolation::MemoryExceeded {
                requested: plugin.estimated_memory_usage(),
                limit: self.memory_limit,
            });
        }
        
        // Validate imports
        for import in plugin.imports() {
            if !self.is_import_allowed(import) {
                return Err(SandboxViolation::UnauthorizedImport {
                    module: import.module.clone(),
                    function: import.function.clone(),
                });
            }
        }
        
        // Check for dangerous patterns
        if plugin.contains_patterns(&DANGEROUS_PATTERNS) {
            return Err(SandboxViolation::DangerousPatternDetected);
        }
        
        Ok(())
    }
    
    fn is_import_allowed(&self, import: &WasmImport) -> bool {
        match import.module.as_str() {
            "env" => {
                // Envoy host functions - always allowed but rate-limited
                true
            }
            "wasi_snapshot_preview1" => {
                // WASI functions - check filesystem policy
                match &import.function.as_str() {
                    "path_open" | "fd_write" => {
                        matches!(self.filesystem_access, 
                            FileSystemPolicy::WriteWhitelist(_))
                    }
                    "fd_read" | "fd_prestat_get" => {
                        !matches!(self.filesystem_access, 
                            FileSystemPolicy::NoAccess)
                    }
                    _ => true,
                }
            }
            "envoy_proxy_wasm" => {
                // Proxy WASM host functions
                true
            }
            _ => false, // Unknown modules blocked by default
        }
    }
}

pub enum SandboxViolation {
    MemoryExceeded { requested: usize, limit: usize },
    UnauthorizedImport { module: String, function: String },
    DangerousPatternDetected,
    CpuTimeExceeded { elapsed: Duration, limit: Duration },
    NetworkAccessDenied,
}

impl std::fmt::Display for SandboxViolation {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::MemoryExceeded { requested, limit } => {
                write!(f, "Memory exceeded: {} > {} bytes", requested, limit)
            }
            Self::UnauthorizedImport { module, function } => {
                write!(f, "Unauthorized import: {}.{}", module, function)
            }
            Self::DangerousPatternDetected => {
                write!(f, "Dangerous code pattern detected")
            }
            Self::CpuTimeExceeded { elapsed, limit } => {
                write!(f, "CPU time exceeded: {:?} > {:?}", elapsed, limit)
            }
            Self::NetworkAccessDenied => {
                write!(f, "Network access denied")
            }
        }
    }
}

const DANGEROUS_PATTERNS: &[&str] = &[
    "eval(",
    "Function(",
    "setTimeout(",
    "setInterval(",
    "importScripts(",
    "XMLHttpRequest",
    "fetch(",
    "WebAssembly",
];
```

---

## 13.2 VS Code Extensions

### Arquitetura de Extensões VS Code com WASM

O VS Code permite a criação de extensões usando WebAssembly para código de alto desempenho enquanto mantém a interface TypeScript para interação com a API do editor.

### Estrutura de uma Extensão

```typescript
// vscode-wasm-extension/src/extension.ts
import * as vscode from 'vscode';
import { WasmModuleLoader } from './wasm-loader';

interface AnalysisResult {
    file_path: string;
    issues: SecurityIssue[];
    metrics: CodeMetrics;
    timestamp: number;
}

interface SecurityIssue {
    line: number;
    column: number;
    severity: 'critical' | 'high' | 'medium' | 'low';
    rule_id: string;
    message: string;
    fix_suggestion?: string;
}

interface CodeMetrics {
    lines_of_code: number;
    complexity: number;
    duplication_percentage: number;
    security_score: number;
}

export class WasmSecurityAnalyzer {
    private wasmModule: WebAssembly.Module | null = null;
    private analysisCache: Map<string, AnalysisResult> = new Map();
    private outputChannel: vscode.OutputChannel;
    private statusBarItem: vscode.StatusBarItem;

    constructor(private context: vscode.ExtensionContext) {
        this.outputChannel = vscode.window.createOutputChannel('WASM Security');
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
    }

    async initialize(): Promise<void> {
        try {
            const wasmPath = vscode.Uri.joinPath(
                this.context.extensionUri,
                'bin',
                'security_analyzer.wasm'
            );
            
            const wasmBinary = await vscode.workspace.fs.readFile(wasmPath);
            this.wasmModule = await WebAssembly.compile(wasmBinary);
            
            this.outputChannel.appendLine('WASM module loaded successfully');
            this.statusBarItem.text = '$(shield) WASM Analyzer';
            this.statusBarItem.tooltip = 'WASM Security Analyzer Active';
            this.statusBarItem.show();
        } catch (error) {
            this.outputChannel.appendLine(`Failed to load WASM: ${error}`);
            vscode.window.showErrorMessage(
                'Failed to initialize WASM Security Analyzer'
            );
        }
    }

    async analyzeDocument(
        document: vscode.TextDocument
    ): Promise<AnalysisResult> {
        if (!this.wasmModule) {
            throw new Error('WASM module not initialized');
        }

        const documentUri = document.uri.toString();
        const cacheKey = `${documentUri}:${document.version}`;
        
        if (this.analysisCache.has(cacheKey)) {
            return this.analysisCache.get(cacheKey)!;
        }

        this.statusBarItem.text = '$(loading~ spinner) Analyzing...';
        
        try {
            const content = document.getText();
            const filePath = document.fileName;
            
            const result = await this.runWasmAnalysis(filePath, content);
            
            this.analysisCache.set(cacheKey, result);
            this.updateDiagnostics(document, result.issues);
            
            this.statusBarItem.text = '$(check) Analysis Complete';
            setTimeout(() => {
                this.statusBarItem.text = '$(shield) WASM Analyzer';
            }, 2000);
            
            return result;
        } catch (error) {
            this.statusBarItem.text = '$(error) Analysis Failed';
            throw error;
        }
    }

    private async runWasmAnalysis(
        filePath: string,
        content: string
    ): Promise<AnalysisResult> {
        const memory = new WebAssembly.Memory({ initial: 256, maximum: 1024 });
        const heap = new Uint8Array(memory.buffer);
        
        // Write input to WASM memory
        const encoder = new TextEncoder();
        const inputBytes = encoder.encode(content);
        const inputPtr = this.allocateMemory(heap, inputBytes.length);
        heap.set(inputBytes, inputPtr);
        
        const instance = await WebAssembly.instantiate(this.wasmModule!, {
            env: {
                memory,
                allocate: (size: number) => this.allocateMemory(heap, size),
                deallocate: (ptr: number, size: number) => {
                    // Simple deallocation tracking
                },
                log: (ptr: number, len: number) => {
                    const msg = this.readStringFromMemory(heap, ptr, len);
                    this.outputChannel.appendLine(`[WASM] ${msg}`);
                },
                report_issue: (
                    line: number,
                    column: number,
                    severity: number,
                    ruleId: number,
                    message: number,
                    msgLen: number
                ) => {
                    // This callback is called from WASM for each issue found
                },
            },
        });
        
        // Run analysis
        const exports = instance.exports as any;
        const resultPtr = exports.analyze(
            inputPtr,
            content.length,
            encoder.encode(filePath).length
        );
        
        // Read result from memory
        const resultJson = this.readStringFromMemory(
            heap,
            resultPtr,
            exports.get_result_size()
        );
        
        return JSON.parse(resultJson);
    }

    private allocateMemory(heap: Uint8Array, size: number): number {
        // Simple bump allocator for WASM communication
        const ALIGN = 8;
        const currentOffset = heap.length;
        const alignedOffset = (currentOffset + ALIGN - 1) & ~(ALIGN - 1);
        return alignedOffset;
    }

    private readStringFromMemory(
        heap: Uint8Array,
        ptr: number,
        len: number
    ): string {
        const decoder = new TextDecoder();
        return decoder.decode(heap.slice(ptr, ptr + len));
    }

    private updateDiagnostics(
        document: vscode.TextDocument,
        issues: SecurityIssue[]
    ): void {
        const diagnosticCollection = vscode.languages.createDiagnosticCollection(
            'wasm-security'
        );
        
        const diagnostics: vscode.Diagnostic[] = issues.map(issue => {
            const range = new vscode.Range(
                new vscode.Position(issue.line - 1, issue.column),
                new vscode.Position(issue.line - 1, issue.column + 10)
            );
            
            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                this.mapSeverity(issue.severity)
            );
            
            diagnostic.code = issue.rule_id;
            diagnostic.source = 'WASM Security Analyzer';
            
            if (issue.fix_suggestion) {
                diagnostic.relatedInformation = [
                    new vscode.DiagnosticRelatedInformation(
                        new vscode.Location(document.uri, range),
                        `Suggestion: ${issue.fix_suggestion}`
                    ),
                ];
            }
            
            return diagnostic;
        });
        
        diagnosticCollection.set(document.uri, diagnostics);
    }

    private mapSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'critical':
                return vscode.DiagnosticSeverity.Error;
            case 'high':
                return vscode.DiagnosticSeverity.Warning;
            case 'medium':
                return vscode.DiagnosticSeverity.Information;
            case 'low':
            default:
                return vscode.DiagnosticSeverity.Hint;
        }
    }
}

export function activate(context: vscode.ExtensionContext) {
    const analyzer = new WasmSecurityAnalyzer(context);
    
    analyzer.initialize();
    
    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'wasm-security.analyze',
            async () => {
                const editor = vscode.window.activeTextEditor;
                if (editor) {
                    await analyzer.analyzeDocument(editor.document);
                }
            }
        )
    );
    
    // Auto-analyze on save
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(async document => {
            await analyzer.analyzeDocument(document);
        })
    );
    
    // Register language providers for inline hints
    context.subscriptions.push(
        vscode.languages.registerCodeLensProvider(
            { scheme: 'file' },
            {
                provideCodeLenses(document) {
                    const lenses: vscode.CodeLens[] = [];
                    // Add security score lens at top of file
                    lenses.push(
                        new vscode.CodeLens(
                            new vscode.Range(0, 0, 0, 0),
                            {
                                title: 'Security Analysis',
                                command: 'wasm-security.analyze',
                            }
                        )
                    );
                    return lenses;
                },
            }
        )
    );
}

export function deactivate() {}
```

### WASM Analyzer Core

```rust
// vscode-wasm-extension/wasm-core/src/lib.rs
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize)]
pub struct AnalysisResult {
    pub file_path: String,
    pub issues: Vec<SecurityIssue>,
    pub metrics: CodeMetrics,
    pub timestamp: i64,
}

#[derive(Serialize, Deserialize)]
pub struct SecurityIssue {
    pub line: usize,
    pub column: usize,
    pub severity: Severity,
    pub rule_id: String,
    pub message: String,
    pub fix_suggestion: Option<String>,
}

#[derive(Serialize, Deserialize)]
pub enum Severity {
    Critical,
    High,
    Medium,
    Low,
}

#[derive(Serialize, Deserialize)]
pub struct CodeMetrics {
    pub lines_of_code: usize,
    pub complexity: usize,
    pub duplication_percentage: f64,
    pub security_score: f64,
}

pub struct SecurityAnalyzer {
    rules: Vec<SecurityRule>,
    patterns: HashMap<String, Vec<CompiledPattern>>,
}

struct SecurityRule {
    id: String,
    name: String,
    severity: Severity,
    pattern: String,
    description: String,
    fix_suggestion: Option<String>,
}

struct CompiledPattern {
    regex: regex::Regex,
    capture_groups: Vec<String>,
}

impl SecurityAnalyzer {
    pub fn new() -> Self {
        let mut analyzer = Self {
            rules: Vec::new(),
            patterns: HashMap::new(),
        };
        analyzer.load_default_rules();
        analyzer
    }
    
    fn load_default_rules(&mut self) {
        let rules = vec![
            SecurityRule {
                id: "SEC001".to_string(),
                name: "Hardcoded Credentials".to_string(),
                severity: Severity::Critical,
                pattern: r#"password\s*=\s*["'][^"']+["']"#.to_string(),
                description: "Hardcoded passwords detected".to_string(),
                fix_suggestion: Some("Use environment variables or secrets manager".to_string()),
            },
            SecurityRule {
                id: "SEC002".to_string(),
                name: "SQL Injection".to_string(),
                severity: Severity::High,
                pattern: r#"query\s*\(\s*["'].*\+.*["']\s*\)"#.to_string(),
                description: "Potential SQL injection vulnerability".to_string(),
                fix_suggestion: Some("Use parameterized queries".to_string()),
            },
            SecurityRule {
                id: "SEC003".to_string(),
                name: "XSS Vulnerability".to_string(),
                severity: Severity::High,
                pattern: r#"innerHTML\s*=|document\.write"#.to_string(),
                description: "Potential XSS vulnerability".to_string(),
                fix_suggestion: Some("Use textContent or sanitize input".to_string()),
            },
            SecurityRule {
                id: "SEC004".to_string(),
                name: "Eval Usage".to_string(),
                severity: Severity::High,
                pattern: r#"\beval\s*\(|new\s+Function\(|setTimeout\s*\(\s*["']"#.to_string(),
                description: "Dynamic code execution detected".to_string(),
                fix_suggestion: Some("Avoid eval, use safer alternatives".to_string()),
            },
            SecurityRule {
                id: "SEC005".to_string(),
                name: "Weak Cryptography".to_string(),
                severity: Severity::Medium,
                pattern: r#"MD5|SHA1|DES\b|RC4"#.to_string(),
                description: "Weak cryptographic algorithm detected".to_string(),
                fix_suggestion: Some("Use SHA-256 or stronger algorithms".to_string()),
            },
        ];
        
        for rule in rules {
            self.add_rule(rule);
        }
    }
    
    pub fn add_rule(&mut self, rule: SecurityRule) {
        let compiled = regex::Regex::new(&rule.pattern)
            .expect("Invalid regex pattern in security rule");
        
        self.patterns
            .entry(rule.id.clone())
            .or_insert_with(Vec::new)
            .push(CompiledPattern {
                regex: compiled,
                capture_groups: Vec::new(),
            });
        
        self.rules.push(rule);
    }
    
    pub fn analyze(&self, file_path: &str, content: &str) -> AnalysisResult {
        let mut issues = Vec::new();
        let lines: Vec<&str> = content.lines().collect();
        
        // Run pattern-based analysis
        for rule in &self.rules {
            if let Some(patterns) = self.patterns.get(&rule.id) {
                for pattern in patterns {
                    for (line_num, line) in lines.iter().enumerate() {
                        if pattern.regex.is_match(line) {
                            issues.push(SecurityIssue {
                                line: line_num + 1,
                                column: pattern
                                    .regex
                                    .find(line)
                                    .map(|m| m.start())
                                    .unwrap_or(0),
                                severity: rule.severity.clone(),
                                rule_id: rule.id.clone(),
                                message: rule.description.clone(),
                                fix_suggestion: rule.fix_suggestion.clone(),
                            });
                        }
                    }
                }
            }
        }
        
        // Calculate metrics
        let metrics = self.calculate_metrics(&lines, &issues);
        
        AnalysisResult {
            file_path: file_path.to_string(),
            issues,
            metrics,
            timestamp: js_sys::Date::now() as i64,
        }
    }
    
    fn calculate_metrics(&self, lines: &[&str], issues: &[SecurityIssue]) -> CodeMetrics {
        let lines_of_code = lines.len();
        
        // Simple complexity metric based on control flow
        let complexity = lines
            .iter()
            .filter(|line| {
                let trimmed = line.trim();
                trimmed.starts_with("if ")
                    || trimmed.starts_with("else")
                    || trimmed.starts_with("for ")
                    || trimmed.starts_with("while ")
                    || trimmed.starts_with("match ")
                    || trimmed.starts_with("catch")
                    || trimmed.contains("&&")
                    || trimmed.contains("||")
            })
            .count();
        
        // Security score based on issues
        let critical_count = issues.iter()
            .filter(|i| matches!(i.severity, Severity::Critical))
            .count();
        let high_count = issues.iter()
            .filter(|i| matches!(i.severity, Severity::High))
            .count();
        let medium_count = issues.iter()
            .filter(|i| matches!(i.severity, Severity::Medium))
            .count();
        
        let security_score = 100.0
            - (critical_count as f64 * 25.0)
            - (high_count as f64 * 15.0)
            - (medium_count as f64 * 5.0);
        
        CodeMetrics {
            lines_of_code,
            complexity,
            duplication_percentage: 0.0, // Would need AST analysis
            security_score: security_score.max(0.0),
        }
    }
}

// WASM exports
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn analyze(file_path_ptr: u32, file_path_len: u32, content_ptr: u32, content_len: u32) -> u32 {
    let memory = unsafe { &*(0x0 as *const [u8; 0]) };
    // In practice, would use wasm_bindgen for proper memory handling
    0
}

#[wasm_bindgen]
pub fn get_result_size() -> u32 {
    0
}

#[wasm_bindgen]
pub fn get_rule_count() -> u32 {
    let analyzer = SecurityAnalyzer::new();
    analyzer.rules.len() as u32
}

#[wasm_bindgen]
pub fn get_rule_info(rule_id_ptr: u32, rule_id_len: u32) -> u32 {
    0
}
```

---

## 13.3 Extism Plugin System

### Visão Geral do Extism

Extism é um framework de plugins universal que permite executar plugins WASM em qualquer linguagem. Suporta múltiplos host functions e oferece um modelo de permissões granular.

### Plugin Host em Rust

```rust
// extism-host/src/main.rs
use extism::*;
use extism_convert::*;
use std::collections::HashMap;

#[derive(serde::Serialize, serde::Deserialize, Jsonify)]
struct PluginManifest {
    name: String,
    version: String,
    permissions: Vec<String>,
    host_functions: Vec<String>,
}

#[derive(serde::Serialize, serde::Deserialize, Jsonify)]
struct PluginRequest {
    action: String,
    data: String,
    metadata: HashMap<String, String>,
}

#[derive(serde::Serialize, serde::Deserialize, Jsonify)]
struct PluginResponse {
    success: bool,
    data: String,
    errors: Vec<String>,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let manifest = Manifest::new([
        Wasm::file("plugins/analysis_plugin.wasm")
            .with_function::<(String,), String, _>(
                "host_log",
                UserData::default(),
                |data, log_msg| {
                    println!("[Plugin Log]: {}", log_msg.0);
                    Ok(log_msg.0)
                },
            )
            .with_function::<(String, String), bool, _>(
                "host_validate_input",
                UserData::default(),
                |data, (input, rule)| {
                    Ok(validate_input(&input.0, &rule.0))
                },
            )
            .with_function::<(), String, _>(
                "host_get_timestamp",
                UserData::default(),
                |data, _| {
                    Ok(chrono::Utc::now().to_rfc3339())
                },
            ),
    ]);
    
    let mut plugin = Plugin::new(&manifest)?;
    
    // Set initial configuration
    plugin.set_config("api_key", "secure-key-123")?;
    plugin.set_config("max_retries", "3")?;
    
    // Initialize plugin
    plugin.call::<&str, &str>("init", "")?;
    
    // Process requests
    let request = PluginRequest {
        action: "analyze".to_string(),
        data: "test input data".to_string(),
        metadata: HashMap::new(),
    };
    
    let response: PluginResponse = plugin.call("process", &request.to_json())?;
    
    println!("Plugin response: {:?}", response);
    
    Ok(())
}

fn validate_input(input: &str, rule: &str) -> bool {
    match rule {
        "no_html" => !input.contains('<'),
        "no_sql" => !input.contains(';') && !input.contains("DROP"),
        "max_length" => input.len() <= 1000,
        _ => true,
    }
}
```

### Plugin WASM para Extism

```rust
// extism-plugin/src/lib.rs
use extism_pdk::*;

static mut PLUGIN_STATE: Option<PluginState> = None;

struct PluginState {
    initialized: bool,
    config: HashMap<String, String>,
    buffers: Vec<Vec<u8>>,
}

impl PluginState {
    fn new() -> Self {
        Self {
            initialized: false,
            config: HashMap::new(),
            buffers: Vec::new(),
        }
    }
    
    fn initialize(&mut self) -> Result<(), String> {
        // Load configuration from host
        if let Some(api_key) = config::get("api_key") {
            self.config.insert("api_key".to_string(), api_key);
        }
        
        if let Some(max_retries) = config::get("max_retries") {
            self.config.insert("max_retries".to_string(), max_retries);
        }
        
        self.initialized = true;
        Ok(())
    }
}

#[no_mangle]
pub extern "C" fn init() -> i32 {
    let mut state = PluginState::new();
    match state.initialize() {
        Ok(()) => {
            unsafe { PLUGIN_STATE = Some(state) };
            0
        }
        Err(e) => {
            log::error!("Initialization failed: {}", e);
            1
        }
    }
}

#[no_mangle]
pub extern "C" fn process() -> i32 {
    let state = unsafe { PLUGIN_STATE.as_mut().unwrap() };
    
    if !state.initialized {
        return error("Plugin not initialized");
    }
    
    // Read input from memory
    let input = match input::get() {
        Some(data) => data,
        None => return error("No input provided"),
    };
    
    // Validate input
    let validation_rules = vec!["no_html", "no_sql", "max_length"];
    for rule in validation_rules {
        let is_valid: bool = host::call(
            "host_validate_input",
            (&input, rule),
            &mut [],
        );
        
        if !is_valid {
            return error(&format!("Input failed validation: {}", rule));
        }
    }
    
    // Process based on action
    let result = match process_request(&input) {
        Ok(output) => output,
        Err(e) => return error(&e),
    };
    
    // Write output
    if let Err(e) = output::set(&result) {
        return error(&format!("Failed to set output: {}", e));
    }
    
    0
}

fn process_request(input: &str) -> Result<String, String> {
    let request: serde_json::Value = serde_json::from_str(input)
        .map_err(|e| format!("Invalid JSON: {}", e))?;
    
    let action = request["action"]
        .as_str()
        .ok_or("Missing action field")?;
    
    let data = request["data"]
        .as_str()
        .ok_or("Missing data field")?;
    
    match action {
        "analyze" => analyze_data(data),
        "transform" => transform_data(data),
        "validate" => validate_data(data),
        _ => Err(format!("Unknown action: {}", action)),
    }
}

fn analyze_data(data: &str) -> Result<String, String> {
    let mut result = serde_json::Map::new();
    
    result.insert("length".to_string(), data.len().into());
    result.insert("word_count".to_string(), data.split_whitespace().count().into());
    result.insert("has_html".to_string(), data.contains('<').into());
    
    let response = serde_json::Value::Object(result);
    Ok(response.to_string())
}

fn transform_data(data: &str) -> Result<String, String> {
    let transformed = data.to_uppercase();
    Ok(transformed)
}

fn validate_data(data: &str) -> Result<String, String> {
    let mut errors = Vec::new();
    
    if data.is_empty() {
        errors.push("Data cannot be empty".to_string());
    }
    
    if data.len() > 10000 {
        errors.push("Data exceeds maximum length".to_string());
    }
    
    if data.contains('\0') {
        errors.push("Data contains null bytes".to_string());
    }
    
    let result = serde_json::json!({
        "valid": errors.is_empty(),
        "errors": errors,
    });
    
    Ok(result.to_string())
}

fn error(msg: &str) -> i32 {
    log::error!("{}", msg);
    output::set(msg).ok();
    1
}

use std::collections::HashMap;
```

---

## 13.4 Plugin Sandboxing

### Modelo de Sandboxing Multicamada

O isolamento de plugins requer múltiplas camadas de proteção trabalhando em conjunto:

```rust
// sandbox-engine/src/lib.rs
use std::sync::{Arc, Mutex};
use std::collections::{HashMap, HashSet};
use std::time::{Duration, Instant};

pub struct PluginSandbox {
    config: SandboxConfig,
    resource_monitor: ResourceMonitor,
    permission_manager: PermissionManager,
    audit_logger: AuditLogger,
}

pub struct SandboxConfig {
    pub memory_limit_bytes: usize,
    pub cpu_time_limit: Duration,
    pub max_threads: usize,
    pub allowed_imports: HashSet<String>,
    pub allowed_exports: HashSet<String>,
    pub filesystem_access: FilesystemPolicy,
    pub network_access: NetworkPolicy,
    pub env_var_whitelist: Vec<String>,
}

pub enum FilesystemPolicy {
    NoAccess,
    ReadOnly(Vec<PathBuf>),
    ReadWrite(Vec<PathBuf>),
    TemporaryOnly,
}

pub enum NetworkPolicy {
    NoAccess,
    OutboundOnly(Vec<String>),
    FullAccess(Vec<String>), // Allowed hosts
}

struct ResourceMonitor {
    memory_usage: Arc<Mutex<usize>>,
    cpu_time_used: Arc<Mutex<Duration>>,
    start_time: Instant,
    allocations: Arc<Mutex<Vec<MemoryAllocation>>>,
}

struct MemoryAllocation {
    ptr: usize,
    size: usize,
    timestamp: Instant,
    caller: String,
}

struct PermissionManager {
    granted_permissions: HashSet<Permission>,
    pending_requests: Vec<PermissionRequest>,
}

#[derive(Hash, Eq, PartialEq, Clone)]
pub enum Permission {
    ReadMemory,
    WriteMemory,
    AllocateMemory,
    ExecuteCode,
    CallHostFunction(String),
    AccessFileSystem(PathBuf),
    NetworkAccess(String),
    SpawnThread,
    AccessTimer,
}

struct PermissionRequest {
    permission: Permission,
    reason: String,
    timestamp: Instant,
    auto_grant: bool,
}

struct AuditLogger {
    entries: Vec<AuditEntry>,
    log_file: Option<File>,
}

struct AuditEntry {
    timestamp: Instant,
    event_type: EventType,
    plugin_id: String,
    details: String,
    risk_level: RiskLevel,
}

enum EventType {
    PermissionRequested,
    PermissionGranted,
    PermissionDenied,
    ResourceWarning,
    ResourceExceeded,
    Error,
    SuspiciousActivity,
}

enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

impl PluginSandbox {
    pub fn new(config: SandboxConfig) -> Self {
        Self {
            config,
            resource_monitor: ResourceMonitor::new(),
            permission_manager: PermissionManager::new(),
            audit_logger: AuditLogger::new(),
        }
    }
    
    pub fn create_isolated_environment(
        &self,
        plugin_id: &str,
        wasm_bytes: &[u8],
    ) -> Result<IsolatedPlugin, SandboxError> {
        // Validate WASM module before loading
        let module = self.validate_wasm_module(wasm_bytes)?;
        
        // Create memory with limits
        let memory = self.create_limited_memory()?;
        
        // Create import object with restricted host functions
        let imports = self.create_restricted_imports(plugin_id)?;
        
        // Set up resource limits
        let resource_limits = ResourceLimits {
            memory: self.config.memory_limit_bytes,
            cpu_time: self.config.cpu_time_limit,
            max_threads: self.config.max_threads,
        };
        
        // Instantiate with monitoring
        let instance = self.instantiate_with_monitoring(
            &module,
            imports,
            resource_limits,
            plugin_id,
        )?;
        
        Ok(IsolatedPlugin {
            instance,
            sandbox: self.clone(),
            plugin_id: plugin_id.to_string(),
            start_time: Instant::now(),
        })
    }
    
    fn validate_wasm_module(&self, wasm_bytes: &[u8]) -> Result<WebAssembly::Module, SandboxError> {
        // Validate magic number and version
        if wasm_bytes.len() < 8 {
            return Err(SandboxError::InvalidModule("Too small".to_string()));
        }
        
        if &wasm_bytes[0..4] != b"\0asm" {
            return Err(SandboxError::InvalidModule("Invalid magic number".to_string()));
        }
        
        let version = u32::from_le_bytes(wasm_bytes[4..8].try_into().unwrap());
        if version != 1 {
            return Err(SandboxError::InvalidModule(
                format!("Unsupported version: {}", version)
            ));
        }
        
        // Parse and validate module structure
        let module = wasmparser::validate(wasm_bytes)
            .map_err(|e| SandboxError::InvalidModule(format!("Parse error: {}", e)))?;
        
        // Check for dangerous imports
        self.validate_imports(&module)?;
        
        // Check for excessive code size
        if wasm_bytes.len() > 10 * 1024 * 1024 {
            return Err(SandboxError::ModuleTooLarge(wasm_bytes.len()));
        }
        
        WebAssembly::Module::from_binary(wasm_bytes)
            .map_err(|e| SandboxError::CompilationError(e.to_string()))
    }
    
    fn create_limited_memory(&self) -> Result<WebAssembly::Memory, SandboxError> {
        let initial_pages = (self.config.memory_limit_bytes / 65536).min(256);
        let maximum_pages = (self.config.memory_limit_bytes / 65536).min(16384);
        
        WebAssembly::Memory::new(WebAssembly::MemoryDescriptor {
            initial: initial_pages as u32,
            maximum: Some(maximum_pages as u32),
            shared: false,
        })
        .map_err(|e| SandboxError::MemoryError(e.to_string()))
    }
    
    fn create_restricted_imports(
        &self,
        plugin_id: &str,
    ) -> Result<WebAssembly::Imports, SandboxError> {
        let mut imports = WebAssembly::Imports::new();
        
        // Only add allowed imports
        for import_name in &self.config.allowed_imports {
            match import_name.as_str() {
                "env" => {
                    imports.register(
                        "env",
                        self.create_env_imports(plugin_id)?,
                    );
                }
                "wasi_snapshot_preview1" => {
                    imports.register(
                        "wasi_snapshot_preview1",
                        self.create_wasi_imports(plugin_id)?,
                    );
                }
                _ => {
                    return Err(SandboxError::ImportDenied(import_name.clone()));
                }
            }
        }
        
        Ok(imports)
    }
    
    fn create_env_imports(
        &self,
        plugin_id: &str,
    ) -> Result<HashMap<String, WebAssembly::Extern>, SandboxError> {
        let mut env_imports = HashMap::new();
        
        // Memory access
        if self.permission_manager.has_permission(&Permission::ReadMemory) {
            env_imports.insert(
                "memory".to_string(),
                WebAssembly::Extern::Memory(self.create_limited_memory()?),
            );
        }
        
        // Logging (always available but rate-limited)
        env_imports.insert(
            "log".to_string(),
            WebAssembly::Extern::Function(
                WebAssembly::Function::new(
                    &WebAssembly::FunctionType::new(
                        vec![WebAssembly::ValType::I32, WebAssembly::ValType::I32],
                        vec![],
                    ),
                    move |args| {
                        // Rate-limited logging
                        let ptr = args[0].i32().unwrap() as usize;
                        let len = args[1].i32().unwrap() as usize;
                        // Would read from memory and log
                        vec![]
                    },
                )
            ),
        );
        
        // Timer access (if allowed)
        if self.permission_manager.has_permission(&Permission::AccessTimer) {
            env_imports.insert(
                "time".to_string(),
                WebAssembly::Extern::Function(
                    WebAssembly::Function::new(
                        &WebAssembly::FunctionType::new(vec![], vec![WebAssembly::ValType::I64]),
                        move |_| {
                            let now = std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap()
                                .as_millis() as i64;
                            vec![WebAssembly::Val::I64(now)]
                        },
                    )
                ),
            );
        }
        
        Ok(env_imports)
    }
}

#[derive(Debug)]
pub enum SandboxError {
    InvalidModule(String),
    ModuleTooLarge(usize),
    CompilationError(String),
    MemoryError(String),
    ImportDenied(String),
    PermissionDenied(Permission),
    ResourceExceeded(String),
    Timeout,
    InternalError(String),
}

impl std::fmt::Display for SandboxError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::InvalidModule(msg) => write!(f, "Invalid module: {}", msg),
            Self::ModuleTooLarge(size) => write!(f, "Module too large: {} bytes", size),
            Self::CompilationError(msg) => write!(f, "Compilation error: {}", msg),
            Self::MemoryError(msg) => write!(f, "Memory error: {}", msg),
            Self::ImportDenied(name) => write!(f, "Import denied: {}", name),
            Self::PermissionDenied(perm) => write!(f, "Permission denied: {:?}", perm),
            Self::ResourceExceeded(msg) => write!(f, "Resource exceeded: {}", msg),
            Self::Timeout => write!(f, "Execution timeout"),
            Self::InternalError(msg) => write!(f, "Internal error: {}", msg),
        }
    }
}
```

---

## 13.5 Capability-Based Plugin Access

### Sistema de Capacidades Granular

```rust
// capability-system/src/lib.rs
use std::collections::{HashMap, HashSet};
use std::sync::Arc;

pub struct CapabilitySystem {
    capabilities: HashMap<PluginId, CapabilitySet>,
    grants: Vec<CapabilityGrant>,
    policies: Vec<AccessPolicy>,
}

#[derive(Hash, Eq, PartialEq, Clone, Debug)]
pub struct PluginId(pub String);

#[derive(Clone, Debug)]
pub struct CapabilitySet {
    pub granted: HashSet<Capability>,
    pub pending: HashSet<Capability>,
    pub denied: HashSet<Capability>,
}

#[derive(Hash, Eq, PartialEq, Clone, Debug)]
pub enum Capability {
    FileRead { path: String },
    FileWrite { path: String },
    NetworkOut { host: String, port: u16 },
    NetworkIn { port: u16 },
    Execute { command: String },
    EnvRead { var: String },
    MemoryAccess { size: usize },
    ThreadSpawn { max_threads: usize },
    DatabaseAccess { connection: String },
    CryptographicOps { algorithms: Vec<CryptoAlgorithm> },
    TimeAccess { precision: TimePrecision },
}

#[derive(Clone, Debug)]
pub enum CryptoAlgorithm {
    AES256,
    RSA2048,
    SHA256,
    Ed25519,
    ChaCha20,
}

#[derive(Clone, Debug)]
pub enum TimePrecision {
    Second,
    Millisecond,
    Microsecond,
    Nanosecond,
}

#[derive(Clone, Debug)]
pub struct CapabilityGrant {
    pub plugin_id: PluginId,
    pub capability: Capability,
    pub granted_by: Identity,
    pub conditions: Vec<GrantCondition>,
    pub expires_at: Option<Instant>,
    pub revocable: bool,
}

#[derive(Clone, Debug)]
pub enum GrantCondition {
    TimeWindow { start: Instant, end: Instant },
    MaxUsage { count: usize },
    RateLimit { requests_per_second: f64 },
    RequireApproval { approvers: Vec<Identity> },
    AuditRequired { log_level: LogLevel },
}

#[derive(Clone, Debug)]
pub struct AccessPolicy {
    pub name: String,
    pub rules: Vec<PolicyRule>,
    pub effect: PolicyEffect,
}

#[derive(Clone, Debug)]
pub struct PolicyRule {
    pub subject: PolicySubject,
    pub action: PolicyAction,
    pub resource: PolicyResource,
    pub conditions: Vec<PolicyCondition>,
}

#[derive(Clone, Debug)]
pub enum PolicySubject {
    Plugin(PluginId),
    PluginCategory(String),
    All,
}

#[derive(Clone, Debug)]
pub enum PolicyAction {
    Allow,
    Deny,
    RequireApproval,
    Audit,
}

#[derive(Clone, Debug)]
pub enum PolicyResource {
    Capability(Capability),
    All,
}

#[derive(Clone, Debug)]
pub enum PolicyCondition {
    TimeOfDay { start: u8, end: u8 },
    MaxConcurrent { count: usize },
    RequireMFA,
    IpWhitelist(Vec<String>),
}

#[derive(Clone, Debug)]
pub enum PolicyEffect {
    Permit,
    Deny,
    DenyWithOverride(Vec<Identity>),
}

pub struct Identity {
    pub name: String,
    pub roles: Vec<String>,
    pub public_key: Option<Vec<u8>>,
}

impl CapabilitySystem {
    pub fn new() -> Self {
        Self {
            capabilities: HashMap::new(),
            grants: Vec::new(),
            policies: Self::default_policies(),
        }
    }
    
    fn default_policies() -> Vec<AccessPolicy> {
        vec![
            AccessPolicy {
                name: "Deny Dangerous Operations".to_string(),
                rules: vec![PolicyRule {
                    subject: PolicySubject::All,
                    action: PolicyAction::Deny,
                    resource: PolicyResource::Capability(Capability::Execute {
                        command: "rm".to_string(),
                    }),
                    conditions: vec![],
                }],
                effect: PolicyEffect::Deny,
            },
            AccessPolicy {
                name: "Require Approval for Network".to_string(),
                rules: vec![PolicyRule {
                    subject: PolicySubject::All,
                    action: PolicyAction::RequireApproval,
                    resource: PolicyResource::Capability(Capability::NetworkOut {
                        host: "*".to_string(),
                        port: 0,
                    }),
                    conditions: vec![PolicyCondition::RequireMFA],
                }],
                effect: PolicyEffect::DenyWithOverride(vec![]),
            },
        ]
    }
    
    pub fn request_capability(
        &mut self,
        plugin_id: &PluginId,
        capability: Capability,
        reason: &str,
    ) -> CapabilityRequestResult {
        // Check explicit denials first
        if self.is_explicitly_denied(plugin_id, &capability) {
            return CapabilityRequestResult::Denied {
                reason: "Explicitly denied by policy".to_string(),
            };
        }
        
        // Check if already granted
        if self.is_granted(plugin_id, &capability) {
            return CapabilityRequestResult::Granted;
        }
        
        // Check policies
        let policy_decision = self.evaluate_policies(plugin_id, &capability);
        match policy_decision {
            PolicyDecision::Allow => {
                self.grant_capability(plugin_id, capability);
                CapabilityRequestResult::Granted
            }
            PolicyDecision::Deny => {
                CapabilityRequestResult::Denied {
                    reason: "Denied by security policy".to_string(),
                }
            }
            PolicyDecision::RequireApproval => {
                CapabilityRequestResult::PendingApproval {
                    required_approvers: self.get_required_approvers(&capability),
                }
            }
        }
    }
    
    fn is_explicitly_denied(
        &self,
        plugin_id: &PluginId,
        capability: &Capability,
    ) -> bool {
        if let Some(cap_set) = self.capabilities.get(plugin_id) {
            return cap_set.denied.contains(capability);
        }
        false
    }
    
    fn is_granted(&self, plugin_id: &PluginId, capability: &Capability) -> bool {
        if let Some(cap_set) = self.capabilities.get(plugin_id) {
            return cap_set.granted.contains(capability);
        }
        false
    }
    
    fn evaluate_policies(
        &self,
        plugin_id: &PluginId,
        capability: &Capability,
    ) -> PolicyDecision {
        for policy in &self.policies {
            for rule in &policy.rules {
                if self.rule_matches(rule, plugin_id, capability) {
                    return match rule.action {
                        PolicyAction::Allow => PolicyDecision::Allow,
                        PolicyAction::Deny => PolicyDecision::Deny,
                        PolicyAction::RequireApproval => PolicyDecision::RequireApproval,
                        PolicyAction::Audit => PolicyDecision::Allow, // Allow but audit
                    };
                }
            }
        }
        PolicyDecision::Deny // Default deny
    }
    
    fn rule_matches(
        &self,
        rule: &PolicyRule,
        plugin_id: &PluginId,
        capability: &Capability,
    ) -> bool {
        // Check subject match
        let subject_matches = match &rule.subject {
            PolicySubject::Plugin(id) => id == plugin_id,
            PolicySubject::PluginCategory(cat) => {
                // Would check plugin's category
                true
            }
            PolicySubject::All => true,
        };
        
        if !subject_matches {
            return false;
        }
        
        // Check resource match
        match &rule.resource {
            PolicyResource::Capability(cap) => {
                std::mem::discriminant(cap) == std::mem::discriminant(capability)
            }
            PolicyResource::All => true,
        }
    }
    
    fn grant_capability(&mut self, plugin_id: &PluginId, capability: Capability) {
        let cap_set = self.capabilities
            .entry(plugin_id.clone())
            .or_insert_with(|| CapabilitySet {
                granted: HashSet::new(),
                pending: HashSet::new(),
                denied: HashSet::new(),
            });
        
        cap_set.granted.insert(capability.clone());
        
        self.grants.push(CapabilityGrant {
            plugin_id: plugin_id.clone(),
            capability,
            granted_by: Identity {
                name: "system".to_string(),
                roles: vec!["admin".to_string()],
                public_key: None,
            },
            conditions: vec![],
            expires_at: None,
            revocable: true,
        });
    }
    
    fn get_required_approvers(&self, capability: &Capability) -> Vec<Identity> {
        // Would look up from policy configuration
        vec![]
    }
}

enum PolicyDecision {
    Allow,
    Deny,
    RequireApproval,
}

pub enum CapabilityRequestResult {
    Granted,
    Denied { reason: String },
    PendingApproval { required_approvers: Vec<Identity> },
}
```

---

## 13.6 Plugin Signing and Verification

### Sistema de Assinatura Criptográfica

```rust
// plugin-signing/src/lib.rs
use ed25519_dalek::{Signer, SigningKey, Verifier, VerifyingKey};
use sha2::{Sha256, Digest};
use std::collections::HashMap;

pub struct PluginSigner {
    signing_key: SigningKey,
    trusted_keys: HashMap<String, VerifyingKey>,
}

pub struct PluginVerifier {
    trusted_keys: HashMap<String, VerifyingKey>,
    revoked_keys: HashSet<Vec<u8>>,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct SignedPlugin {
    pub manifest: PluginManifest,
    pub bytecode: Vec<u8>,
    pub signature: PluginSignature,
    pub metadata: PluginMetadata,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct PluginManifest {
    pub name: String,
    pub version: String,
    pub author: String,
    pub description: String,
    pub permissions: Vec<String>,
    pub min_host_version: String,
    pub checksum: String,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct PluginSignature {
    pub algorithm: String,
    pub signature: Vec<u8>,
    pub key_id: String,
    pub timestamp: i64,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct PluginMetadata {
    pub signed_at: i64,
    pub expires_at: Option<i64>,
    pub build_info: BuildInfo,
    pub source_hash: Option<String>,
}

#[derive(serde::Serialize, serde::Deserialize)]
pub struct BuildInfo {
    pub compiler_version: String,
    pub target: String,
    pub optimization_level: u8,
    pub reproducible_build: bool,
}

impl PluginSigner {
    pub fn new(seed: &[u8; 32]) -> Self {
        let signing_key = SigningKey::from_bytes(seed);
        Self {
            signing_key,
            trusted_keys: HashMap::new(),
        }
    }
    
    pub fn sign_plugin(
        &self,
        manifest: PluginManifest,
        bytecode: Vec<u8>,
    ) -> Result<SignedPlugin, SigningError> {
        // Validate manifest
        self.validate_manifest(&manifest)?;
        
        // Verify bytecode matches manifest checksum
        let actual_checksum = compute_checksum(&bytecode);
        if actual_checksum != manifest.checksum {
            return Err(SigningError::ChecksumMismatch {
                expected: manifest.checksum.clone(),
                actual: actual_checksum,
            });
        }
        
        // Create signature payload
        let payload = self.create_signature_payload(&manifest, &bytecode);
        
        // Sign
        let signature = self.signing_key.sign(&payload);
        
        // Create key ID
        let verifying_key = self.signing_key.verifying_key();
        let key_id = compute_key_id(&verifying_key);
        
        let signed_plugin = SignedPlugin {
            manifest,
            bytecode,
            signature: PluginSignature {
                algorithm: "Ed25519".to_string(),
                signature: signature.to_bytes().to_vec(),
                key_id,
                timestamp: current_timestamp(),
            },
            metadata: PluginMetadata {
                signed_at: current_timestamp(),
                expires_at: Some(current_timestamp() + 365 * 24 * 60 * 60), // 1 year
                build_info: BuildInfo {
                    compiler_version: "1.0.0".to_string(),
                    target: "wasm32-unknown-unknown".to_string(),
                    optimization_level: 3,
                    reproducible_build: true,
                },
                source_hash: None,
            },
        };
        
        Ok(signed_plugin)
    }
    
    fn validate_manifest(&self, manifest: &PluginManifest) -> Result<(), SigningError> {
        // Validate version format
        if !semver::Version::parse(&manifest.version).is_ok() {
            return Err(SigningError::InvalidManifest(
                "Invalid version format".to_string()
            ));
        }
        
        // Validate name
        if manifest.name.is_empty() || manifest.name.len() > 64 {
            return Err(SigningError::InvalidManifest(
                "Invalid plugin name".to_string()
            ));
        }
        
        // Validate permissions
        let valid_permissions = [
            "read:filesystem",
            "write:filesystem",
            "network:outbound",
            "network:inbound",
            "memory:allocate",
            "thread:spawn",
            "crypto:use",
        ];
        
        for perm in &manifest.permissions {
            if !valid_permissions.contains(&perm.as_str()) {
                return Err(SigningError::InvalidManifest(
                    format!("Invalid permission: {}", perm)
                ));
            }
        }
        
        Ok(())
    }
    
    fn create_signature_payload(
        &self,
        manifest: &PluginManifest,
        bytecode: &[u8],
    ) -> Vec<u8> {
        let mut hasher = Sha256::new();
        
        // Hash manifest
        let manifest_json = serde_json::to_string(manifest).unwrap();
        hasher.update(manifest_json.as_bytes());
        
        // Hash bytecode
        hasher.update(bytecode);
        
        // Hash metadata
        hasher.update(current_timestamp().to_le_bytes());
        
        hasher.finalize().to_vec()
    }
}

impl PluginVerifier {
    pub fn new() -> Self {
        Self {
            trusted_keys: HashMap::new(),
            revoked_keys: HashSet::new(),
        }
    }
    
    pub fn add_trusted_key(&mut self, key_id: String, key: VerifyingKey) {
        self.trusted_keys.insert(key_id, key);
    }
    
    pub fn revoke_key(&mut self, key_bytes: Vec<u8>) {
        self.revoked_keys.insert(key_bytes);
    }
    
    pub fn verify_plugin(&self, plugin: &SignedPlugin) -> VerificationResult {
        // Check if signature key is revoked
        if self.revoked_keys.contains(&plugin.signature.signature) {
            return VerificationResult::RevokedKey;
        }
        
        // Find trusted key
        let verifying_key = match self.trusted_keys.get(&plugin.signature.key_id) {
            Some(key) => key,
            None => return VerificationResult::UnknownKey,
        };
        
        // Check expiration
        if let Some(expires_at) = plugin.metadata.expires_at {
            if current_timestamp() > expires_at {
                return VerificationResult::Expired;
            }
        }
        
        // Verify checksum
        let actual_checksum = compute_checksum(&plugin.bytecode);
        if actual_checksum != plugin.manifest.checksum {
            return VerificationResult::ChecksumMismatch;
        }
        
        // Verify signature
        let payload = self.create_verification_payload(plugin);
        let signature = ed25519_dalek::Signature::from_bytes(
            &plugin.signature.signature.try_into().unwrap()
        );
        
        match verifying_key.verify(&payload, &signature) {
            Ok(()) => VerificationResult::Valid,
            Err(_) => VerificationResult::InvalidSignature,
        }
    }
    
    fn create_verification_payload(&self, plugin: &SignedPlugin) -> Vec<u8> {
        let mut hasher = Sha256::new();
        
        let manifest_json = serde_json::to_string(&plugin.manifest).unwrap();
        hasher.update(manifest_json.as_bytes());
        hasher.update(&plugin.bytecode);
        hasher.update(plugin.signature.timestamp.to_le_bytes());
        
        hasher.finalize().to_vec()
    }
}

pub enum VerificationResult {
    Valid,
    InvalidSignature,
    Expired,
    RevokedKey,
    UnknownKey,
    ChecksumMismatch,
}

fn compute_checksum(data: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(data);
    format!("{:x}", hasher.finalize())
}

fn compute_key_id(key: &VerifyingKey) -> String {
    let mut hasher = Sha256::new();
    hasher.update(key.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn current_timestamp() -> i64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

#[derive(Debug)]
pub enum SigningError {
    InvalidManifest(String),
    ChecksumMismatch { expected: String, actual: String },
    SigningFailed(String),
}
```

---

## 13.7 Plugin Marketplace Security

### Marketplace com Verificação em Múltiplas Etapas

```rust
// marketplace-security/src/lib.rs
use std::collections::HashMap;
use serde::{Deserialize, Serialize};

pub struct PluginMarketplace {
    plugins: HashMap<String, MarketplacePlugin>,
    reviews: HashMap<String, Vec<Review>>,
    scan_results: HashMap<String, SecurityScan>,
    publisher_registry: HashMap<String, Publisher>,
}

#[derive(Serialize, Deserialize)]
pub struct MarketplacePlugin {
    pub id: String,
    pub name: String,
    pub description: String,
    pub author: PublisherId,
    pub versions: Vec<PluginVersion>,
    pub security_score: f64,
    pub verified: bool,
    pub category: PluginCategory,
    pub downloads: u64,
    pub last_updated: i64,
}

#[derive(Serialize, Deserialize)]
pub struct PluginVersion {
    pub version: String,
    pub checksum: String,
    pub signed_plugin: SignedPlugin,
    pub published_at: i64,
    pub changelog: String,
    pub compatibility: CompatibilityInfo,
}

#[derive(Serialize, Deserialize)]
pub struct CompatibilityInfo {
    pub min_host_version: String,
    pub max_host_version: Option<String>,
    pub required_capabilities: Vec<String>,
    pub platform: Vec<String>,
}

#[derive(Serialize, Deserialize)]
pub enum PluginCategory {
    Security,
    Productivity,
    Development,
    Analytics,
    Communication,
    Other,
}

#[derive(Serialize, Deserialize)]
pub struct Publisher {
    pub id: String,
    pub name: String,
    pub verified: bool,
    pub public_key: String,
    pub reputation: f64,
    pub plugins_published: u32,
    pub joined_at: i64,
}

#[derive(Serialize, Deserialize)]
pub struct PublisherId(pub String);

#[derive(Serialize, Deserialize)]
pub struct Review {
    pub reviewer: String,
    pub rating: u8,
    pub comment: String,
    pub verified_purchase: bool,
    pub created_at: i64,
}

#[derive(Serialize, Deserialize)]
pub struct SecurityScan {
    pub scan_id: String,
    pub plugin_id: String,
    pub version: String,
    pub status: ScanStatus,
    pub findings: Vec<SecurityFinding>,
    pub risk_score: f64,
    pub scanned_at: i64,
    pub scanner_version: String,
}

#[derive(Serialize, Deserialize)]
pub enum ScanStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

#[derive(Serialize, Deserialize)]
pub struct SecurityFinding {
    pub id: String,
    pub severity: FindingSeverity,
    pub category: String,
    pub title: String,
    pub description: String,
    pub recommendation: String,
    pub cwe_id: Option<String>,
    pub affected_code: Option<CodeLocation>,
}

#[derive(Serialize, Deserialize)]
pub enum FindingSeverity {
    Critical,
    High,
    Medium,
    Low,
    Informational,
}

#[derive(Serialize, Deserialize)]
pub struct CodeLocation {
    pub file: String,
    pub line: u32,
    pub column: u32,
    pub snippet: String,
}

impl PluginMarketplace {
    pub fn new() -> Self {
        Self {
            plugins: HashMap::new(),
            reviews: HashMap::new(),
            scan_results: HashMap::new(),
            publisher_registry: HashMap::new(),
        }
    }
    
    pub fn submit_plugin(
        &mut self,
        plugin: SignedPlugin,
        publisher_id: &str,
    ) -> Result<SubmissionResult, SubmissionError> {
        // Step 1: Verify publisher
        let publisher = self.verify_publisher(publisher_id)?;
        
        // Step 2: Verify signature
        let verifier = PluginVerifier::new();
        match verifier.verify_plugin(&plugin) {
            VerificationResult::Valid => {}
            result => return Err(SubmissionError::SignatureInvalid(format!("{:?}", result))),
        }
        
        // Step 3: Security scan
        let scan_result = self.scan_plugin(&plugin)?;
        if scan_result.risk_score > 0.7 {
            return Err(SubmissionError::SecurityScanFailed {
                risk_score: scan_result.risk_score,
                critical_findings: scan_result.findings.iter()
                    .filter(|f| matches!(f.severity, FindingSeverity::Critical))
                    .count(),
            });
        }
        
        // Step 4: Check for duplicates
        if self.has_duplicate(&plugin.manifest.name, &plugin.manifest.version) {
            return Err(SubmissionError::DuplicateVersion);
        }
        
        // Step 5: Validate metadata
        self.validate_metadata(&plugin)?;
        
        // Step 6: Store plugin
        let plugin_id = self.generate_plugin_id(&plugin.manifest);
        
        let marketplace_plugin = MarketplacePlugin {
            id: plugin_id.clone(),
            name: plugin.manifest.name.clone(),
            description: plugin.manifest.description.clone(),
            author: PublisherId(publisher_id.to_string()),
            versions: vec![PluginVersion {
                version: plugin.manifest.version.clone(),
                checksum: plugin.manifest.checksum.clone(),
                signed_plugin: plugin,
                published_at: current_timestamp(),
                changelog: String::new(),
                compatibility: CompatibilityInfo {
                    min_host_version: plugin.manifest.min_host_version.clone(),
                    max_host_version: None,
                    required_capabilities: plugin.manifest.permissions.clone(),
                    platform: vec!["wasm32".to_string()],
                },
            }],
            security_score: 100.0 - (scan_result.risk_score * 100.0),
            verified: publisher.verified,
            category: PluginCategory::Other,
            downloads: 0,
            last_updated: current_timestamp(),
        };
        
        self.plugins.insert(plugin_id.clone(), marketplace_plugin);
        self.scan_results.insert(plugin_id.clone(), scan_result);
        
        Ok(SubmissionResult {
            plugin_id,
            status: SubmissionStatus::Published,
            warnings: vec![],
        })
    }
    
    fn verify_publisher(&self, publisher_id: &str) -> Result<Publisher, SubmissionError> {
        self.publisher_registry
            .get(publisher_id)
            .cloned()
            .ok_or_else(|| SubmissionError::PublisherNotFound(publisher_id.to_string()))
    }
    
    fn scan_plugin(&self, plugin: &SignedPlugin) -> Result<SecurityScan, SubmissionError> {
        let mut findings = Vec::new();
        
        // Analyze WASM bytecode
        let analysis = self.analyze_bytecode(&plugin.bytecode);
        findings.extend(analysis.findings);
        
        // Check for known vulnerabilities
        let vuln_check = self.check_known_vulnerabilities(&plugin.bytecode);
        findings.extend(vuln_check);
        
        // Permission analysis
        let perm_analysis = self.analyze_permissions(&plugin.manifest.permissions);
        findings.extend(perm_analysis);
        
        let risk_score = self.calculate_risk_score(&findings);
        
        Ok(SecurityScan {
            scan_id: generate_scan_id(),
            plugin_id: String::new(),
            version: plugin.manifest.version.clone(),
            status: ScanStatus::Completed,
            findings,
            risk_score,
            scanned_at: current_timestamp(),
            scanner_version: "1.0.0".to_string(),
        })
    }
    
    fn analyze_bytecode(&self, bytecode: &[u8]) -> BytecodeAnalysis {
        let mut findings = Vec::new();
        
        // Check for suspicious imports
        if let Ok(module) = wasmparser::validate(bytecode) {
            // Would analyze imports in detail
        }
        
        // Check code size
        if bytecode.len() > 5 * 1024 * 1024 {
            findings.push(SecurityFinding {
                id: "SCAN001".to_string(),
                severity: FindingSeverity::Medium,
                category: "Code Quality".to_string(),
                title: "Large plugin size".to_string(),
                description: "Plugin bytecode exceeds 5MB".to_string(),
                recommendation: "Consider optimizing the plugin".to_string(),
                cwe_id: None,
                affected_code: None,
            });
        }
        
        BytecodeAnalysis { findings }
    }
    
    fn check_known_vulnerabilities(&self, bytecode: &[u8]) -> Vec<SecurityFinding> {
        // Would check against CVE database
        vec![]
    }
    
    fn analyze_permissions(&self, permissions: &[String]) -> Vec<SecurityFinding> {
        let mut findings = Vec::new();
        
        let dangerous_perms = [
            "network:inbound",
            "thread:spawn",
            "memory:unlimited",
        ];
        
        for perm in permissions {
            if dangerous_perms.contains(&perm.as_str()) {
                findings.push(SecurityFinding {
                    id: format!("PERM001-{}", perm),
                    severity: FindingSeverity::High,
                    category: "Permissions".to_string(),
                    title: format!("Dangerous permission requested: {}", perm),
                    description: format!(
                        "Plugin requests potentially dangerous permission: {}",
                        perm
                    ),
                    recommendation: "Review if this permission is necessary".to_string(),
                    cwe_id: Some("CWE-250".to_string()),
                    affected_code: None,
                });
            }
        }
        
        findings
    }
    
    fn calculate_risk_score(&self, findings: &[SecurityFinding]) -> f64 {
        let mut score = 0.0;
        
        for finding in findings {
            let weight = match finding.severity {
                FindingSeverity::Critical => 0.4,
                FindingSeverity::High => 0.25,
                FindingSeverity::Medium => 0.1,
                FindingSeverity::Low => 0.05,
                FindingSeverity::Informational => 0.01,
            };
            score += weight;
        }
        
        score.min(1.0)
    }
    
    fn has_duplicate(&self, name: &str, version: &str) -> bool {
        self.plugins.values().any(|p| {
            p.name == name && p.versions.iter().any(|v| v.version == version)
        })
    }
    
    fn validate_metadata(&self, plugin: &SignedPlugin) -> Result<(), SubmissionError> {
        if plugin.manifest.name.is_empty() {
            return Err(SubmissionError::InvalidMetadata(
                "Plugin name is required".to_string()
            ));
        }
        
        if plugin.manifest.description.len() < 20 {
            return Err(SubmissionError::InvalidMetadata(
                "Description must be at least 20 characters".to_string()
            ));
        }
        
        Ok(())
    }
    
    fn generate_plugin_id(&self, manifest: &PluginManifest) -> String {
        use sha2::{Sha256, Digest};
        let mut hasher = Sha256::new();
        hasher.update(manifest.name.as_bytes());
        hasher.update(manifest.author.as_bytes());
        format!("{:x}", hasher.finalize())
    }
}

pub struct SubmissionResult {
    pub plugin_id: String,
    pub status: SubmissionStatus,
    pub warnings: Vec<String>,
}

pub enum SubmissionStatus {
    Published,
    PendingReview,
    Rejected,
}

pub enum SubmissionError {
    PublisherNotFound(String),
    SignatureInvalid(String),
    SecurityScanFailed { risk_score: f64, critical_findings: usize },
    DuplicateVersion,
    InvalidMetadata(String),
}

struct BytecodeAnalysis {
    findings: Vec<SecurityFinding>,
}

fn generate_scan_id() -> String {
    use uuid::Uuid;
    Uuid::new_v4().to_string()
}
```

---

## 13.8 Audit Trails

### Sistema de Auditoria Completo

```rust
// audit-trail/src/lib.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

pub struct AuditSystem {
    events: Arc<Mutex<Vec<AuditEvent>>>,
    event_store: EventStore,
    integrity_checker: IntegrityChecker,
    retention_policy: RetentionPolicy,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct AuditEvent {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    pub event_type: EventType,
    pub actor: Actor,
    pub resource: Resource,
    pub action: Action,
    pub outcome: Outcome,
    pub details: HashMap<String, serde_json::Value>,
    pub previous_hash: Option<String>,
    pub hash: String,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub enum EventType {
    PluginInstalled,
    PluginRemoved,
    PluginUpdated,
    PluginExecuted,
    PermissionGranted,
    PermissionDenied,
    CapabilityRequested,
    SecurityScanCompleted,
    VulnerabilityDetected,
    ConfigurationChanged,
    AccessAttempt,
    ErrorOccurred,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Actor {
    pub id: String,
    pub actor_type: ActorType,
    pub ip_address: Option<String>,
    pub user_agent: Option<String>,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub enum ActorType {
    User,
    Plugin,
    System,
    Admin,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Resource {
    pub id: String,
    pub resource_type: ResourceType,
    pub name: Option<String>,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub enum ResourceType {
    Plugin,
    Permission,
    Capability,
    Configuration,
    AuditLog,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Action {
    pub name: String,
    pub parameters: HashMap<String, serde_json::Value>,
}

#[derive(Clone, Debug, serde::Serialize, serde::Deserialize)]
pub struct Outcome {
    pub success: bool,
    pub error_code: Option<String>,
    pub error_message: Option<String>,
}

pub struct EventStore {
    events: Vec<AuditEvent>,
    index_by_type: HashMap<EventType, Vec<usize>>,
    index_by_actor: HashMap<String, Vec<usize>>,
    index_by_resource: HashMap<String, Vec<usize>>,
}

pub struct IntegrityChecker {
    chain: Vec<String>,
    last_hash: Option<String>,
}

pub struct RetentionPolicy {
    max_age_days: u32,
    max_events: usize,
    compress_after_days: u32,
}

impl AuditSystem {
    pub fn new() -> Self {
        Self {
            events: Arc::new(Mutex::new(Vec::new())),
            event_store: EventStore::new(),
            integrity_checker: IntegrityChecker::new(),
            retention_policy: RetentionPolicy::default(),
        }
    }
    
    pub fn log_event(
        &self,
        event_type: EventType,
        actor: Actor,
        resource: Resource,
        action: Action,
        outcome: Outcome,
        details: HashMap<String, serde_json::Value>,
    ) -> AuditEvent {
        let mut events = self.events.lock().unwrap();
        
        let previous_hash = self.integrity_checker.last_hash.clone();
        
        let event = AuditEvent {
            id: generate_event_id(),
            timestamp: Utc::now(),
            event_type: event_type.clone(),
            actor: actor.clone(),
            resource: resource.clone(),
            action: action.clone(),
            outcome: outcome.clone(),
            details,
            previous_hash: previous_hash.clone(),
            hash: String::new(), // Will be computed
        };
        
        // Compute hash
        let event_with_hash = self.compute_event_hash(&event);
        
        // Update integrity chain
        self.integrity_checker.add_event(&event_with_hash);
        
        // Store event
        events.push(event_with_hash.clone());
        self.event_store.index_event(&event_with_hash, events.len() - 1);
        
        event_with_hash
    }
    
    fn compute_event_hash(&self, event: &AuditEvent) -> AuditEvent {
        use sha2::{Sha256, Digest};
        
        let mut hasher = Sha256::new();
        hasher.update(event.id.as_bytes());
        hasher.update(event.timestamp.to_rfc3339().as_bytes());
        hasher.update(format!("{:?}", event.event_type).as_bytes());
        hasher.update(event.actor.id.as_bytes());
        hasher.update(event.resource.id.as_bytes());
        hasher.update(event.action.name.as_bytes());
        hasher.update(event.previous_hash.as_deref().unwrap_or(""));
        
        let hash = format!("{:x}", hasher.finalize());
        
        let mut event_clone = event.clone();
        event_clone.hash = hash;
        event_clone
    }
    
    pub fn verify_integrity(&self) -> IntegrityResult {
        let events = self.events.lock().unwrap();
        
        for i in 1..events.len() {
            let event = &events[i];
            let previous = &events[i - 1];
            
            // Verify chain link
            if event.previous_hash.as_ref() != Some(&previous.hash) {
                return IntegrityResult::Broken {
                    at_index: i,
                    expected: previous.hash.clone(),
                    actual: event.previous_hash.clone().unwrap_or_default(),
                };
            }
            
            // Verify event hash
            let computed_hash = self.compute_event_hash(event);
            if computed_hash.hash != event.hash {
                return IntegrityResult::Tampered { at_index: i };
            }
        }
        
        IntegrityResult::Valid
    }
    
    pub fn query_events(
        &self,
        filter: EventFilter,
    ) -> Vec<AuditEvent> {
        let events = self.events.lock().unwrap();
        
        events.iter()
            .filter(|event| self.matches_filter(event, &filter))
            .cloned()
            .collect()
    }
    
    fn matches_filter(&self, event: &AuditEvent, filter: &EventFilter) -> bool {
        if let Some(ref event_types) = filter.event_types {
            if !event_types.contains(&event.event_type) {
                return false;
            }
        }
        
        if let Some(ref actor_id) = filter.actor_id {
            if event.actor.id != *actor_id {
                return false;
            }
        }
        
        if let Some(ref resource_id) = filter.resource_id {
            if event.resource.id != *resource_id {
                return false;
            }
        }
        
        if let Some(start_time) = filter.start_time {
            if event.timestamp < start_time {
                return false;
            }
        }
        
        if let Some(end_time) = filter.end_time {
            if event.timestamp > end_time {
                return false;
            }
        }
        
        if let Some(success_only) = filter.success_only {
            if event.outcome.success != success_only {
                return false;
            }
        }
        
        true
    }
    
    pub fn export_events(
        &self,
        format: ExportFormat,
        filter: EventFilter,
    ) -> Result<Vec<u8>, ExportError> {
        let events = self.query_events(filter);
        
        match format {
            ExportFormat::Json => {
                serde_json::to_vec_pretty(&events)
                    .map_err(|e| ExportError::SerializationError(e.to_string()))
            }
            ExportFormat::Csv => {
                let mut wtr = csv::Writer::from_writer(vec![]);
                for event in &events {
                    wtr.serialize(event)
                        .map_err(|e| ExportError::SerializationError(e.to_string()))?;
                }
                wtr.into_inner()
                    .map_err(|e| ExportError::IoError(e))
            }
            ExportFormat::Protobuf => {
                // Would use prost or similar
                Ok(vec![])
            }
        }
    }
}

pub struct EventFilter {
    pub event_types: Option<Vec<EventType>>,
    pub actor_id: Option<String>,
    pub resource_id: Option<String>,
    pub start_time: Option<DateTime<Utc>>,
    pub end_time: Option<DateTime<Utc>>,
    pub success_only: Option<bool>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
}

pub enum ExportFormat {
    Json,
    Csv,
    Protobuf,
}

pub enum IntegrityResult {
    Valid,
    Broken { at_index: usize, expected: String, actual: String },
    Tampered { at_index: usize },
}

pub enum ExportError {
    SerializationError(String),
    IoError(std::io::Error),
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            max_age_days: 365,
            max_events: 1_000_000,
            compress_after_days: 30,
        }
    }
}

fn generate_event_id() -> String {
    use uuid::Uuid;
    Uuid::new_v4().to_string()
}
```

---

## 13.9 Performance Implications

### Benchmarks e Otimizações

```rust
// performance-analysis/src/lib.rs
use std::time::{Duration, Instant};

pub struct PerformanceBenchmark {
    results: Vec<BenchmarkResult>,
}

pub struct BenchmarkResult {
    pub name: String,
    pub iterations: u64,
    pub total_duration: Duration,
    pub avg_duration: Duration,
    pub min_duration: Duration,
    pub max_duration: Duration,
    pub percentile_95: Duration,
    pub percentile_99: Duration,
    pub memory_usage: MemoryStats,
}

pub struct MemoryStats {
    pub peak_memory: usize,
    pub avg_memory: usize,
    pub allocations: u64,
    pub deallocations: u64,
}

impl PerformanceBenchmark {
    pub fn new() -> Self {
        Self {
            results: Vec::new(),
        }
    }
    
    pub fn benchmark_plugin_instantiation(
        &mut self,
        wasm_bytes: &[u8],
        iterations: u64,
    ) -> BenchmarkResult {
        let mut durations = Vec::with_capacity(iterations as usize);
        let mut memory_samples = Vec::new();
        
        for _ in 0..iterations {
            let start = Instant::now();
            let memory_before = get_memory_usage();
            
            // Compile module
            let module = WebAssembly::Module::from_binary(wasm_bytes).unwrap();
            
            // Create memory
            let memory = WebAssembly::Memory::new(
                WebAssembly::MemoryDescriptor::new(256, Some(1024))
            ).unwrap();
            
            // Create imports
            let imports = WebAssembly::Imports::new();
            
            // Instantiate
            let _instance = WebAssembly::Instance::new(&module, &imports).unwrap();
            
            let duration = start.elapsed();
            durations.push(duration);
            
            let memory_after = get_memory_usage();
            memory_samples.push(memory_after - memory_before);
        }
        
        self.compute_stats("plugin_instantiation", iterations, durations, memory_samples)
    }
    
    pub fn benchmark_plugin_execution(
        &mut self,
        instance: &WebAssembly::Instance,
        function_name: &str,
        iterations: u64,
    ) -> BenchmarkResult {
        let mut durations = Vec::with_capacity(iterations as usize);
        let mut memory_samples = Vec::new();
        
        let func = instance.exports.get_function(function_name).unwrap();
        
        for _ in 0..iterations {
            let memory_before = get_memory_usage();
            let start = Instant::now();
            
            let _ = func.call(&[]);
            
            let duration = start.elapsed();
            durations.push(duration);
            
            let memory_after = get_memory_usage();
            memory_samples.push(memory_after - memory_before);
        }
        
        self.compute_stats(
            &format!("plugin_execution_{}", function_name),
            iterations,
            durations,
            memory_samples,
        )
    }
    
    pub fn benchmark_memory_operations(
        &mut self,
        memory: &WebAssembly::Memory,
        iterations: u64,
    ) -> BenchmarkResult {
        let mut durations = Vec::with_capacity(iterations as usize);
        let mut memory_samples = Vec::new();
        
        let data_size = 1024 * 1024; // 1MB
        
        for _ in 0..iterations {
            let memory_before = get_memory_usage();
            let start = Instant::now();
            
            // Allocate
            let current_pages = memory.size();
            memory.grow(1).unwrap();
            
            // Write
            let buffer = memory.buffer();
            let mut uint8_array = js_sys::Uint8Array::new(&buffer);
            let data = vec![0u8; data_size];
            uint8_array.set(&js_sys::Uint8Array::from(&data[..]), 0);
            
            // Read
            let _ = uint8_array.to_vec();
            
            // Deallocate
            memory.grow(-1).unwrap();
            
            let duration = start.elapsed();
            durations.push(duration);
            
            let memory_after = get_memory_usage();
            memory_samples.push(memory_after - memory_before);
        }
        
        self.compute_stats("memory_operations", iterations, durations, memory_samples)
    }
    
    fn compute_stats(
        &mut self,
        name: &str,
        iterations: u64,
        mut durations: Vec<Duration>,
        memory_samples: Vec<usize>,
    ) -> BenchmarkResult {
        durations.sort();
        
        let total: Duration = durations.iter().sum();
        let avg = total / iterations as u32;
        let min = durations[0];
        let max = durations[(durations.len() - 1) as usize];
        
        let p95_index = (iterations as f64 * 0.95) as usize;
        let p99_index = (iterations as f64 * 0.99) as usize;
        
        let percentile_95 = durations[p95_index.min(durations.len() - 1)];
        let percentile_99 = durations[p99_index.min(durations.len() - 1)];
        
        let memory_stats = MemoryStats {
            peak_memory: memory_samples.iter().copied().max().unwrap_or(0),
            avg_memory: memory_samples.iter().sum::<usize>() / memory_samples.len().max(1),
            allocations: iterations,
            deallocations: iterations,
        };
        
        let result = BenchmarkResult {
            name: name.to_string(),
            iterations,
            total_duration: total,
            avg_duration: avg,
            min_duration: min,
            max_duration: max,
            percentile_95,
            percentile_99,
            memory_usage: memory_stats,
        };
        
        self.results.push(result.clone());
        result
    }
    
    pub fn generate_report(&self) -> String {
        let mut report = String::new();
        
        report.push_str("# WASM Plugin Performance Report\n\n");
        report.push_str(&format!("Generated: {}\n\n", chrono::Utc::now()));
        
        for result in &self.results {
            report.push_str(&format!("## {}\n\n", result.name));
            report.push_str(&format!("- Iterations: {}\n", result.iterations));
            report.push_str(&format!("- Total Duration: {:?}\n", result.total_duration));
            report.push_str(&format!("- Average Duration: {:?}\n", result.avg_duration));
            report.push_str(&format!("- Min Duration: {:?}\n", result.min_duration));
            report.push_str(&format!("- Max Duration: {:?}\n", result.max_duration));
            report.push_str(&format!("- 95th Percentile: {:?}\n", result.percentile_95));
            report.push_str(&format!("- 99th Percentile: {:?}\n", result.percentile_99));
            report.push_str(&format!("- Peak Memory: {} bytes\n", result.memory_usage.peak_memory));
            report.push_str("\n");
        }
        
        report
    }
}

fn get_memory_usage() -> usize {
    // Platform-specific memory usage retrieval
    #[cfg(target_arch = "wasm32")]
    {
        // WASM memory usage
        0
    }
    #[cfg(not(target_arch = "wasm32"))]
    {
        // For native benchmarks
        use std::process::Command;
        let output = Command::new("ps")
            .args(["-o", "rss=", "-p", &std::process::id().to_string()])
            .output()
            .unwrap();
        String::from_utf8_lossy(&output.stdout)
            .trim()
            .parse::<usize>()
            .unwrap_or(0)
            * 1024
    }
}
```

---

## 13.10 Complete Plugin System Example

### Sistema Completo de Plugins Seguros

```rust
// complete-plugin-system/src/lib.rs
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::Duration;

pub struct SecurePluginSystem {
    plugin_manager: PluginManager,
    sandbox_engine: SandboxEngine,
    capability_system: CapabilitySystem,
    signing_service: SigningService,
    marketplace: PluginMarketplace,
    audit_system: AuditSystem,
    performance_monitor: PerformanceMonitor,
}

struct PluginManager {
    plugins: HashMap<String, ManagedPlugin>,
    lifecycle_hooks: LifecycleHooks,
}

struct ManagedPlugin {
    id: String,
    manifest: PluginManifest,
    instance: Option<WebAssembly::Instance>,
    state: PluginState,
    metrics: PluginMetrics,
    capabilities: Vec<Capability>,
}

enum PluginState {
    Installed,
    Loaded,
    Running,
    Suspended,
    Error(String),
}

struct PluginMetrics {
    execution_count: u64,
    total_execution_time: Duration,
    memory_usage: usize,
    error_count: u64,
    last_execution: Option<chrono::DateTime<chrono::Utc>>,
}

struct LifecycleHooks {
    pre_install: Vec<Box<dyn Fn(&PluginManifest) -> bool>>,
    post_install: Vec<Box<dyn Fn(&ManagedPlugin)>>,
    pre_execute: Vec<Box<dyn Fn(&ManagedPlugin) -> bool>>,
    post_execute: Vec<Box<dyn Fn(&ManagedPlugin, &ExecutionResult)>>,
}

struct SandboxEngine {
    sandboxes: HashMap<String, PluginSandbox>,
    global_config: SandboxConfig,
}

struct SigningService {
    signer: PluginSigner,
    verifier: PluginVerifier,
}

struct PerformanceMonitor {
    benchmarks: PerformanceBenchmark,
    alerts: Vec<PerformanceAlert>,
    thresholds: PerformanceThresholds,
}

struct PerformanceThresholds {
    max_instantiation_time: Duration,
    max_execution_time: Duration,
    max_memory_usage: usize,
    max_error_rate: f64,
}

struct PerformanceAlert {
    plugin_id: String,
    alert_type: AlertType,
    message: String,
    timestamp: chrono::DateTime<chrono::Utc>,
    severity: AlertSeverity,
}

enum AlertType {
    HighLatency,
    MemoryLeak,
    HighErrorRate,
    ResourceExhaustion,
}

enum AlertSeverity {
    Warning,
    Critical,
}

impl SecurePluginSystem {
    pub fn new() -> Self {
        Self {
            plugin_manager: PluginManager::new(),
            sandbox_engine: SandboxEngine::new(),
            capability_system: CapabilitySystem::new(),
            signing_service: SigningService::new(),
            marketplace: PluginMarketplace::new(),
            audit_system: AuditSystem::new(),
            performance_monitor: PerformanceMonitor::new(),
        }
    }
    
    pub async fn install_plugin(
        &mut self,
        plugin_id: &str,
        user: &str,
    ) -> Result<InstallResult, PluginError> {
        // Step 1: Download from marketplace
        let signed_plugin = self.marketplace.get_plugin(plugin_id)
            .map_err(|e| PluginError::DownloadFailed(e))?;
        
        // Step 2: Verify signature
        match self.signing_service.verifier.verify_plugin(&signed_plugin) {
            VerificationResult::Valid => {}
            result => return Err(PluginError::SignatureInvalid(result)),
        }
        
        // Step 3: Run security scan
        let scan_result = self.marketplace.scan_plugin(&signed_plugin)?;
        if scan_result.risk_score > 0.5 {
            return Err(PluginError::SecurityScanFailed(scan_result));
        }
        
        // Step 4: Create sandbox
        let sandbox_config = self.create_sandbox_config(&signed_plugin.manifest);
        let sandbox = self.sandbox_engine.create_sandbox(
            &signed_plugin.manifest.name,
            &sandbox_config,
        )?;
        
        // Step 5: Request capabilities
        let required_caps = self.determine_required_capabilities(&signed_plugin.manifest);
        for cap in required_caps {
            match self.capability_system.request_capability(
                &PluginId(plugin_id.to_string()),
                cap,
                "Plugin installation",
            ) {
                CapabilityRequestResult::Granted => {}
                CapabilityRequestResult::Denied { reason } => {
                    return Err(PluginError::CapabilityDenied(reason));
                }
                CapabilityRequestResult::PendingApproval { .. } => {
                    return Err(PluginError::RequiresApproval);
                }
            }
        }
        
        // Step 6: Execute lifecycle hooks
        for hook in &self.plugin_manager.lifecycle_hooks.pre_install {
            if !hook(&signed_plugin.manifest) {
                return Err(PluginError::PreInstallHookFailed);
            }
        }
        
        // Step 7: Store plugin
        let managed_plugin = ManagedPlugin {
            id: plugin_id.to_string(),
            manifest: signed_plugin.manifest.clone(),
            instance: None,
            state: PluginState::Installed,
            metrics: PluginMetrics::new(),
            capabilities: required_caps,
        };
        
        self.plugin_manager.plugins.insert(
            plugin_id.to_string(),
            managed_plugin,
        );
        
        // Step 8: Audit log
        self.audit_system.log_event(
            EventType::PluginInstalled,
            Actor {
                id: user.to_string(),
                actor_type: ActorType::User,
                ip_address: None,
                user_agent: None,
            },
            Resource {
                id: plugin_id.to_string(),
                resource_type: ResourceType::Plugin,
                name: Some(signed_plugin.manifest.name),
            },
            Action {
                name: "install".to_string(),
                parameters: HashMap::new(),
            },
            Outcome {
                success: true,
                error_code: None,
                error_message: None,
            },
            HashMap::new(),
        );
        
        // Step 9: Execute post-install hooks
        if let Some(plugin) = self.plugin_manager.plugins.get(plugin_id) {
            for hook in &self.plugin_manager.lifecycle_hooks.post_install {
                hook(plugin);
            }
        }
        
        Ok(InstallResult {
            plugin_id: plugin_id.to_string(),
            status: InstallationStatus::Installed,
            warnings: vec![],
        })
    }
    
    pub async fn execute_plugin(
        &mut self,
        plugin_id: &str,
        function: &str,
        input: &[u8],
    ) -> Result<Vec<u8>, PluginError> {
        let plugin = self.plugin_manager.plugins.get_mut(plugin_id)
            .ok_or_else(|| PluginError::PluginNotFound(plugin_id.to_string()))?;
        
        // Check plugin state
        match &plugin.state {
            PluginState::Installed => {
                // Need to load first
                self.load_plugin(plugin_id)?;
            }
            PluginState::Running => {}
            PluginState::Error(e) => {
                return Err(PluginError::PluginInError(e.clone()));
            }
            _ => return Err(PluginError::InvalidState),
        }
        
        // Execute pre-execution hooks
        for hook in &self.plugin_manager.lifecycle_hooks.pre_execute {
            if !hook(plugin) {
                return Err(PluginError::PreExecutionHookFailed);
            }
        }
        
        // Get sandbox
        let sandbox = self.sandbox_engine.sandboxes.get(plugin_id)
            .ok_or(PluginError::SandboxNotFound)?;
        
        // Set resource limits
        let limits = ResourceLimits {
            memory: 64 * 1024 * 1024, // 64MB
            cpu_time: Duration::from_secs(5),
            max_threads: 1,
        };
        
        // Execute with monitoring
        let start = std::time::Instant::now();
        let result = sandbox.execute_with_limits(
            function,
            input,
            limits,
        ).await;
        let duration = start.elapsed();
        
        // Update metrics
        plugin.metrics.execution_count += 1;
        plugin.metrics.total_execution_time += duration;
        plugin.metrics.last_execution = Some(chrono::Utc::now());
        
        // Check performance thresholds
        self.performance_monitor.check_thresholds(
            plugin_id,
            &duration,
            sandbox.get_memory_usage(),
        );
        
        match result {
            Ok(output) => {
                // Execute post-execution hooks
                let exec_result = ExecutionResult {
                    success: true,
                    output: output.clone(),
                    duration,
                };
                
                for hook in &self.plugin_manager.lifecycle_hooks.post_execute {
                    hook(plugin, &exec_result);
                }
                
                // Audit log
                self.audit_system.log_event(
                    EventType::PluginExecuted,
                    Actor {
                        id: "system".to_string(),
                        actor_type: ActorType::System,
                        ip_address: None,
                        user_agent: None,
                    },
                    Resource {
                        id: plugin_id.to_string(),
                        resource_type: ResourceType::Plugin,
                        name: Some(plugin.manifest.name.clone()),
                    },
                    Action {
                        name: function.to_string(),
                        parameters: HashMap::new(),
                    },
                    Outcome {
                        success: true,
                        error_code: None,
                        error_message: None,
                    },
                    HashMap::new(),
                );
                
                Ok(output)
            }
            Err(e) => {
                plugin.metrics.error_count += 1;
                plugin.state = PluginState::Error(e.to_string());
                
                // Audit log
                self.audit_system.log_event(
                    EventType::ErrorOccurred,
                    Actor {
                        id: "system".to_string(),
                        actor_type: ActorType::System,
                        ip_address: None,
                        user_agent: None,
                    },
                    Resource {
                        id: plugin_id.to_string(),
                        resource_type: ResourceType::Plugin,
                        name: Some(plugin.manifest.name.clone()),
                    },
                    Action {
                        name: function.to_string(),
                        parameters: HashMap::new(),
                    },
                    Outcome {
                        success: false,
                        error_code: Some(e.error_code()),
                        error_message: Some(e.to_string()),
                    },
                    HashMap::new(),
                );
                
                Err(PluginError::ExecutionFailed(e))
            }
        }
    }
    
    fn load_plugin(&mut self, plugin_id: &str) -> Result<(), PluginError> {
        let plugin = self.plugin_manager.plugins.get_mut(plugin_id)
            .ok_or_else(|| PluginError::PluginNotFound(plugin_id.to_string()))?;
        
        // Get WASM bytes from storage
        let wasm_bytes = self.get_plugin_bytecode(plugin_id)?;
        
        // Create isolated environment
        let sandbox = self.sandbox_engine.create_isolated_environment(
            plugin_id,
            &wasm_bytes,
        )?;
        
        // Instantiate
        let instance = sandbox.instantiate()?;
        
        plugin.instance = Some(instance);
        plugin.state = PluginState::Loaded;
        
        Ok(())
    }
    
    fn create_sandbox_config(&self, manifest: &PluginManifest) -> SandboxConfig {
        SandboxConfig {
            memory_limit_bytes: self.calculate_memory_limit(manifest),
            cpu_time_limit: Duration::from_secs(5),
            max_threads: 1,
            allowed_imports: manifest.required_imports.iter().cloned().collect(),
            allowed_exports: manifest.exports.iter().cloned().collect(),
            filesystem_access: FilesystemPolicy::TemporaryOnly,
            network_access: if manifest.requires_network {
                NetworkPolicy::OutboundOnly(vec![])
            } else {
                NetworkPolicy::NoAccess
            },
            env_var_whitelist: vec![],
        }
    }
    
    fn calculate_memory_limit(&self, manifest: &PluginManifest) -> usize {
        let base = 32 * 1024 * 1024; // 32MB base
        let extra = manifest.estimated_memory_pages.unwrap_or(0) * 65536;
        (base + extra).min(256 * 1024 * 1024) // Max 256MB
    }
    
    fn determine_required_capabilities(&self, manifest: &PluginManifest) -> Vec<Capability> {
        let mut caps = Vec::new();
        
        if manifest.requires_network {
            caps.push(Capability::NetworkOut {
                host: "*".to_string(),
                port: 443,
            });
        }
        
        if manifest.requires_filesystem {
            caps.push(Capability::FileRead {
                path: "/tmp/plugin-data".to_string(),
            });
            caps.push(Capability::FileWrite {
                path: "/tmp/plugin-data".to_string(),
            });
        }
        
        caps.push(Capability::MemoryAccess {
            size: self.calculate_memory_limit(manifest),
        });
        
        caps
    }
    
    fn get_plugin_bytecode(&self, plugin_id: &str) -> Result<Vec<u8>, PluginError> {
        // Would load from plugin storage
        Ok(vec![])
    }
    
    pub fn get_system_status(&self) -> SystemStatus {
        SystemStatus {
            total_plugins: self.plugin_manager.plugins.len(),
            running_plugins: self.plugin_manager.plugins.values()
                .filter(|p| matches!(p.state, PluginState::Running))
                .count(),
            total_executions: self.plugin_manager.plugins.values()
                .map(|p| p.metrics.execution_count)
                .sum(),
            total_errors: self.plugin_manager.plugins.values()
                .map(|p| p.metrics.error_count)
                .sum(),
            audit_events: self.audit_system.events.lock().unwrap().len(),
            alerts: self.performance_monitor.alerts.len(),
        }
    }
}

pub struct SystemStatus {
    pub total_plugins: usize,
    pub running_plugins: usize,
    pub total_executions: u64,
    pub total_errors: u64,
    pub audit_events: usize,
    pub alerts: usize,
}

pub struct InstallResult {
    pub plugin_id: String,
    pub status: InstallationStatus,
    pub warnings: Vec<String>,
}

pub enum InstallationStatus {
    Installed,
    PendingApproval,
    Failed,
}

pub struct ExecutionResult {
    pub success: bool,
    pub output: Vec<u8>,
    pub duration: Duration,
}

pub enum PluginError {
    DownloadFailed(String),
    SignatureInvalid(VerificationResult),
    SecurityScanFailed(SecurityScan),
    CapabilityDenied(String),
    RequiresApproval,
    PreInstallHookFailed,
    PreExecutionHookFailed,
    PluginNotFound(String),
    PluginInError(String),
    InvalidState,
    SandboxNotFound,
    ExecutionFailed(Box<dyn std::error::Error>),
    IoError(std::io::Error),
}

impl std::fmt::Display for PluginError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            Self::DownloadFailed(e) => write!(f, "Download failed: {}", e),
            Self::SignatureInvalid(r) => write!(f, "Signature invalid: {:?}", r),
            Self::SecurityScanFailed(s) => write!(f, "Security scan failed: score {}", s.risk_score),
            Self::CapabilityDenied(reason) => write!(f, "Capability denied: {}", reason),
            Self::RequiresApproval => write!(f, "Requires approval"),
            Self::PreInstallHookFailed => write!(f, "Pre-install hook failed"),
            Self::PreExecutionHookFailed => write!(f, "Pre-execution hook failed"),
            Self::PluginNotFound(id) => write!(f, "Plugin not found: {}", id),
            Self::PluginInError(e) => write!(f, "Plugin in error state: {}", e),
            Self::InvalidState => write!(f, "Invalid plugin state"),
            Self::SandboxNotFound => write!(f, "Sandbox not found"),
            Self::ExecutionFailed(e) => write!(f, "Execution failed: {}", e),
            Self::IoError(e) => write!(f, "IO error: {}", e),
        }
    }
}

impl PluginError {
    pub fn error_code(&self) -> String {
        match self {
            Self::DownloadFailed(_) => "E001".to_string(),
            Self::SignatureInvalid(_) => "E002".to_string(),
            Self::SecurityScanFailed(_) => "E003".to_string(),
            Self::CapabilityDenied(_) => "E004".to_string(),
            Self::RequiresApproval => "E005".to_string(),
            Self::PreInstallHookFailed => "E006".to_string(),
            Self::PreExecutionHookFailed => "E007".to_string(),
            Self::PluginNotFound(_) => "E008".to_string(),
            Self::PluginInError(_) => "E009".to_string(),
            Self::InvalidState => "E010".to_string(),
            Self::SandboxNotFound => "E011".to_string(),
            Self::ExecutionFailed(_) => "E012".to_string(),
            Self::IoError(_) => "E013".to_string(),
        }
    }
}

impl PluginMetrics {
    fn new() -> Self {
        Self {
            execution_count: 0,
            total_execution_time: Duration::default(),
            memory_usage: 0,
            error_count: 0,
            last_execution: None,
        }
    }
}

impl PerformanceMonitor {
    fn check_thresholds(
        &mut self,
        plugin_id: &str,
        duration: &Duration,
        memory_usage: usize,
    ) {
        if *duration > self.thresholds.max_execution_time {
            self.alerts.push(PerformanceAlert {
                plugin_id: plugin_id.to_string(),
                alert_type: AlertType::HighLatency,
                message: format!("Execution took {:?}", duration),
                timestamp: chrono::Utc::now(),
                severity: AlertSeverity::Warning,
            });
        }
        
        if memory_usage > self.thresholds.max_memory_usage {
            self.alerts.push(PerformanceAlert {
                plugin_id: plugin_id.to_string(),
                alert_type: AlertType::MemoryLeak,
                message: format!("Memory usage: {} bytes", memory_usage),
                timestamp: chrono::Utc::now(),
                severity: AlertSeverity::Critical,
            });
        }
    }
}
```

---

## Conclusão

Neste capítulo, exploramos os fundamentos e práticas avançadas para construir sistemas de plugins seguros usando WebAssembly. Cobrimos desde integração com proxies de serviço como Envoy até marketplaces completos com verificação criptográfica e auditoria.

Os pontos-chave abordados incluem:

1. **Envoy WASM Plugins**: Como estender proxies de serviço com código seguro
2. **VS Code Extensions**: Extensões de editor com análise de segurança
3. **Extism Plugin System**: Framework universal de plugins
4. **Plugin Sandboxing**: Múltiplas camadas de isolamento
5. **Capability-Based Access**: Controle granular de permissões
6. **Plugin Signing**: Verificação criptográfica de integridade
7. **Marketplace Security**: Pipeline de segurança para distribuição
8. **Audit Trails**: Rastreamento completo de ações
9. **Performance**: Benchmarks e otimizações
10. **Sistema Completo**: Integração de todos os componentes

O WebAssembly oferece uma base sólida para sistemas de plugins seguros, mas a segurança não é automática. É necessário implementar múltiplas camadas de proteção, desde sandboxing até verificação de assinatura, para criar um ecossistema de plugins confiável.

No próximo capítulo, exploraremos como o WebAssembly está sendo utilizado em edge computing para executar código próximo aos usuários finais.
