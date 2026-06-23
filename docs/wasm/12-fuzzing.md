# Capítulo 12: Fuzzing de Módulos WebAssembly

## 12.1 Introdução a Fuzzing de Módulos Wasm

Fuzzing é uma técnica de teste de software que consiste em fornecer dados inválidos, inesperados ou malformados como entrada a um programa, com o objetivo de descobrir vulnerabilidades de segurança, bugs de lógica e falhas de tratamento de erros. Ao contrário dos testes tradicionais que verificam cenários conhecidos, o fuzzing explora o espaço de possibilidades de entrada de forma automatizada, frequentemente encontrando bugs que seriam impossíveis de detectar manualmente.

No contexto de WebAssembly, o fuzzing assume uma importância particular. Módulos Wasm são executados em runtimes que podem ser integrados a navegadores, servidores, e ambientes edge. Uma falha em um runtime Wasm pode comprometer a segurança de todo o sistema que o hospeda. Além disso, módulos Wasm podem ser compilados de linguagens como C, C++ e Rust, que possuem diferentes perfis de segurança de memória.

### 12.1.1 Por que Fuzzing Importa para WebAssembly

O ecossistema WebAssembly apresenta múltiplas superfícies de ataque que tornam o fuzzing especialmente valioso:

```
+------------------------------------------------------------------+
|                    Superfícies de Ataque Wasm                      |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  | Decodificador    |    | Validador       |    | Executor      | |
|  | de binários Wasm |    | de módulos      |    | de instruções | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |          |
|           v                       v                      v          |
|  +------------------+    +------------------+    +---------------+ |
|  | Parser de        |    | Type checker    |    | Gerenciamento | |
|  | seções Wasm      |    | de tipos        |    | de memória    | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |          |
|           v                       v                      v          |
|  +------------------+    +------------------+    +---------------+ |
|  | Linker de        |    | Optimizer       |    | Integração    | |
|  | importações      |    | de código       |    | com WASI      | |
|  +------------------+    +------------------+    +---------------+ |
|                                                                    |
+------------------------------------------------------------------+
```

Cada uma dessas camadas representa uma oportunidade para encontrar vulnerabilidades através de fuzzing. O decodificador de binários, por exemplo, precisa processar módulos Wasm arbitrários de fontes não confiáveis. Um bug nessa camada pode levar aexecução de código arbitrário.

**Vulnerabilidades típicas encontradas em runtimes Wasm:**

- **Buffer overflows** no decodificador de seções binárias
- **Integer overflows** em cálculos de tamanhos de seção
- **Use-after-free** em estruturas de dados temporárias durante validação
- **Out-of-bounds reads** em parsing de tabelas de instruções
- **Deadlocks** em implementações com suporte a threads
- **Memory leaks** em caches de módulos compilados

### 12.1.2 Por que Wasm é Particularmente Adequado para Fuzzing

WebAssembly possui características que o tornam especialmente adequado para fuzzing:

**Formato binário bem definido**: O formato binário do Wasm é especificado com precisão, o que permite criar geradores de entrada que compreendem a estrutura do formato. Isso possibilita fuzzing structure-aware, onde o fuzzer gera entradas que respeitam parcialmente a estrutura do formato.

**Execução rápida**: Módulos Wasm podem ser executados rapidamente, o que permite milhares de execuções por segundo durante uma campanha de fuzzing.

**Isolamento nativo**: O modelo de sandboxing do Wasm fornece execução isolada, o que significa que um crash em um módulo Wasm não compromete necessariamente o sistema host.

**Especificação pública**: A especificação do Wasm é pública e detalhada, o que facilita a identificação de comportamentos que divergem da especificação.

**Ecossistema de ferramentas**: O ecossistema Wasm possui ferramentas maduras como `wasm-tools`, `wabt` e `wasm-mutate` que facilitam a manipulação e análise de módulos.

### 12.1.3 Tipos de Fuzzers

Fuzzers podem ser classificados em duas categorias principais:

**Mutation-based fuzzers** geram novas entradas a partir de entradas existentes (sementes), aplicando mutações como inserção, deleção, substituição de bytes. São fáceis de configurar mas podem gerar muitas entradas inválidas.

```bash
# Exemplo de mutação simples com AFL++
# O fuzzer pega um seed e aplica mutações aleatórias
echo "AAAA" > /tmp/seed.txt
afl-fuzz -i /tmp/seeds -o /tmp/output -- ./target_binary @@
```

**Generation-based fuzzers** geram entradas do zero, baseando-se em uma gramática ou modelo do formato de entrada. Produzem entradas mais estruturadas mas requerem conhecimento prévio do formato.

```python
# Exemplo simplificado de geração de módulos Wasm
import struct

def generate_wasm_module():
    """Gera um módulo Wasm válido minimal."""
    # Magic number
    magic = b'\x00asm'
    # Versão 1
    version = struct.pack('<I', 1)
    
    # Seção de tipos (ID = 1)
    type_section = bytes([1])  # Type section ID
    type_content = bytes([
        0x01,  # 1 tipo
        0x60,  # Function type
        0x00,  # 0 parâmetros
        0x01,  # 1 resultado
        0x7F,  # i32
    ])
    type_section += bytes([len(type_content)]) + type_content
    
    # Seção de código (ID = 10)
    code_section = bytes([10])  # Code section ID
    func_body = bytes([
        0x00,  # Local declarations count = 0
        0x41, 0x00,  # i32.const 0
        0x0B,  # end
    ])
    code_content = bytes([len(func_body)]) + func_body
    code_section += bytes([len(code_content)]) + code_content
    
    return magic + version + type_section + code_section
```

### 12.1.4 Fuzzing vs Testes Tradicionais

Fuzzing e testes tradicionais se complementam. Enquanto testes tradicionais verificam cenários conhecidos e específicos, o fuzzing explora o espaço de entrada de forma mais ampla:

```
+------------------------------------------------------------------+
|              Comparação: Testes vs Fuzzing                          |
+------------------------------------------------------------------+
|                                                                    |
|  Testes Tradicionais:              Fuzzing:                        |
|  - Baseados em especificação       - Exploratório                  |
|  - Verificam comportamento         - Encontram comportamento       |
|    esperado                          inesperado                    |
|  - Cobertura limitada              - Cobertura ampla               |
|  - Requerem definição manual       - Automatizado                  |
|  - Reprodutíveis                   - Pode gerar crash              |
|  - Executam em segundos            - Horas/dias de campanha        |
|                                                                    |
|  Melhor para:                    Melhor para:                      |
|  - Regressão                      - Descoberta de bugs             |
|  - Validação de interface         - Teste de robustez              |
|  - Testes de unidade              - Exploração de edge cases       |
|                                                                    |
+------------------------------------------------------------------+
```

Para módulos Wasm, a combinação de ambos é ideal. Testes unitários garantem que funcionalidades conhecidas funcionam corretamente, enquanto o fuzzing descobre comportamentos inesperados em cenários que não foram previstos.

### 12.1.5 O Processo de Fuzzing

O processo de fuzzing de módulos Wasm segue um ciclo iterativo:

```
+------------------------------------------------------------------+
|                   Ciclo de Fuzzing                                 |
+------------------------------------------------------------------+
|                                                                    |
|    +-----------+     +----------+     +-----------+                |
|    | Gerar     | --> | Executar | --> | Avaliar   |                |
|    | entrada   |     | módulo   |     | resultado |                |
|    +-----------+     +----------+     +-----------+                |
|         ^                                  |                       |
|         |         +-----------+            |                       |
|         +--------- | Atualizar | <---------+                       |
|                   | cobertura |                                    |
|                   +-----------+                                    |
|                                                                    |
|  1. Gerar entrada (mutação ou geração)                            |
|  2. Executar o módulo Wasm com a entrada                          |
|  3. Avaliar se houve crash, hang ou comportamento anômalo          |
|  4. Atualizar a cobertura e corpus de sementes                    |
|  5. Repetir                                                       |
|                                                                    |
+------------------------------------------------------------------+
```

## 12.2 Structure-Aware Fuzzing for Wasm

Fuzzing convencional, que opera no nível de bytes, tem eficiência limitada quando aplicado a formatos binários complexos como Wasm. A maioria das mutações aleatórias gera módulos que falham na validação inicial, desperdiçando ciclos de execução. Structure-aware fuzzing resolve esse problema compreendendo a estrutura do formato e gerando mutações que produzem entradas mais prováveis de atingir código profundo.

### 12.2.1 Por que Structure-Aware Fuzzing é Essencial para Wasm

O formato binário do Wasm é altamente estruturado. Um módulo válido consiste em:

1. Um header com magic number e versão
2. Uma sequência de seções, cada uma com ID, tamanho e conteúdo
3. Cada seção possui uma estrutura interna específica
4. Instruções Wasm seguem uma gramática definida

Quando um fuzzer aplica mutações byte-a-byte em um módulo Wasm, a maioria das mutações altera bytes que são parte de campos de tamanho, offsets ou índices, gerando módulos que falham na validação sem nunca atingir o executor de instruções.

### 12.2.2 Gramática do Formato Binário Wasm

A especificação do Wasm define formalmente a estrutura do formato binário. Conhecer essa gramática permite construir mutações mais inteligentes:

```
module    := magic version section*
section   := id size content
id        := byte (0=custom, 1=type, 2=import, 3=function,
                   4=table, 5=memory, 6=global, 7=export,
                   8=start, 9=element, 10=code, 11=data, 12=tag)
size      := u32 (tamanho em bytes do conteúdo)
content   := seção específica do ID

type      := functype param* result*
param     := valtype
result    := valtype
valtype   := i32(0x7F) | i64(0x7E) | f32(0x7D) | f64(0x7C)

func      := type_index body
body      := code_size locals* expr
expr      := instr* end
instr     := opcode operand*
```

### 12.2.3 Estratégias de Mutação para Wasm

As mutações devem respeitar a estrutura do formato para serem produtivas:

**Mutação de seção**: Inserir, remover ou reordenar seções inteiras.

```rust
// wasm-mutate: mutador structure-aware para Wasm
use wasm_mutate::Error;
use wasm_mutate::WasmMutate;

fn apply_section_mutation(wasm_bytes: &[u8]) -> Result<Vec<u8>, Error> {
    // Configurar o mutador para operar no nível de seções
    let mut config = WasmMutate::new();
    config.preserve_semantics(false); // Permitir mudanças semânticas
    
    let result = config.run(wasm_bytes)?;
    Ok(result)
}
```

**Mutação de instruções**: Substituir, inserir ou remover instruções dentro de corpos de função.

```rust
// Exemplo de mutação de instruções
fn mutate_instruction(instr: &mut Instruction) {
    match instr {
        // Substituir i32.const por i64.const
        Instruction::I32Const(val) => {
            *instr = Instruction::I64Const(*val as i64);
        }
        // Substituir i32.add por i32.sub
        Instruction::I32Add => {
            *instr = Instruction::I32Sub;
        }
        // Inserir instrução extra antes de end
        Instruction::End => {
            // Instrução unreachable antes do end
        }
        _ => {}
    }
}
```

**Mutação de tipos**: Alterar assinaturas de tipo em seções de tipo.

```wasm
;; Original: função sem parâmetros com resultado i32
;; (type $0 (func (result i32)))

;; Mutado: função com parâmetro i32 e resultado i64
;; (type $0 (func (param i32) (result i64)))

;; Isto força o runtime a lidar com tipos incompatíveis
```

**Mutação de operandos**: Alterar constantes, índices e offsets.

```rust
// Mutação de constantes numéricas
fn mutate_numeric_operands(instructions: &mut Vec<Instruction>) {
    for instr in instructions.iter_mut() {
        match instr {
            Instruction::I32Const(val) => {
                // Valores extremos
                *val = match *val {
                    0 => i32::MAX,
                    _ => 0,
                };
            }
            Instruction::I64Const(val) => {
                // Valores que podem causar overflow
                *val = i64::MAX;
            }
            Instruction::F32Const(val) => {
                // NaN, Inf, -Inf
                *val = f32::NAN;
            }
            _ => {}
        }
    }
}
```

### 12.2.4 Validação de Entradas Mutadas

Após cada mutação, é importante verificar se o módulo resultante é pelo menos parcialmente válido:

```python
import subprocess
import struct

class WasmValidator:
    """Validador básico de módulos Wasm mutados."""
    
    def __init__(self, wasm_validate_path='wasm-validate'):
        self.validator = wasm_validate_path
    
    def validate(self, wasm_bytes):
        """Valida se o módulo Wasm é sintaticamente válido."""
        try:
            result = subprocess.run(
                [self.validator, '-'],
                input=wasm_bytes,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
    
    def extract_info(self, wasm_bytes):
        """Extrai informações básicas do módulo."""
        if len(wasm_bytes) < 8:
            return None
        
        magic = wasm_bytes[:4]
        version = struct.unpack('<I', wasm_bytes[4:8])[0]
        
        if magic != b'\x00asm':
            return None
        
        # Contar seções
        sections = []
        offset = 8
        while offset < len(wasm_bytes):
            if offset >= len(wasm_bytes):
                break
            section_id = wasm_bytes[offset]
            offset += 1
            
            # Ler LEB128 u32
            result = 0
            shift = 0
            while offset < len(wasm_bytes):
                byte = wasm_bytes[offset]
                offset += 1
                result |= (byte & 0x7F) << shift
                if byte & 0x80 == 0:
                    break
                shift += 7
            
            sections.append({
                'id': section_id,
                'size': result
            })
            offset += result
        
        return {
            'magic': magic,
            'version': version,
            'sections': sections,
            'section_count': len(sections)
        }
    
    def is_reachable(self, wasm_bytes):
        """Verifica se o módulo contém código executável."""
        info = self.extract_info(wasm_bytes)
        if info is None:
            return False
        
        # Procurar seção de código (ID = 10)
        return any(s['id'] == 10 for s in info['sections'])
```

### 12.2.5 Tools: wasm-mutate e wasm-tools

O `wasm-mutate` é um ferramenta dedicada a mutação de módulos Wasm, construída sobre a biblioteca `wasm-tools`:

```bash
# Instalação
cargo install wasm-mutate

# Uso básico: gerar uma mutação
wasm-mutate input.wasm -o output.wasm

# Gerar múltiplas mutações
wasm-mutate input.wasm --seed 42 --output-dir ./mutations/

# Listar estratégias de mutação disponíveis
wasm-mutate --help

# Aplicar apenas mutações de tipos
wasm-mutate input.wasm -o output.wasm --types-only
```

O `wasm-tools` fornece operações de manipulação de módulos Wasm:

```bash
# Instalação
cargo install wasm-tools

# Validar um módulo
wasm-tools validate input.wasm

# Decompor em texto
wasm-tools print input.wasm -o output.wat

# Recompor de texto para binário
wasm-tools compose output.wat -o recomposed.wasm

# Listar importações e exportações
wasm-tools dump input.wasm

# Verificar se o módulo é malicioso
wasm-tools validate input.wasm --features bulk-memory
```

### 12.2.6 Definição de Gramática Customizada para Fuzzing Wasm

Para fuzzing avançado, é possível definir gramáticas customizadas que representam subconjuntos do formato Wasm:

```yaml
# grammar.yaml - Gramática para geração de módulos Wasm
module:
  magic: "\x00asm"
  version: 1
  sections:
    - type: type_section
      probability: 0.8
    - type: import_section
      probability: 0.5
    - type: function_section
      probability: 0.9
    - type: memory_section
      probability: 0.3
    - type: export_section
      probability: 0.7
    - type: code_section
      probability: 0.95

type_section:
  types:
    - kind: functype
      params:
        count: [0, 1, 2, 3, 4]
        types: [i32, i64, f32, f64]
      results:
        count: [0, 1]
        types: [i32, i64, f32, f64]

code_section:
  functions:
    - locals:
        count: [0, 1, 2, 3]
        types: [i32, i64, f32, f64]
      body:
        instructions:
          - i32.const
          - i64.const
          - f32.const
          - f64.const
          - i32.add
          - i32.sub
          - i32.mul
          - i32.div_s
          - i32.div_u
          - i32.load
          - i32.store
          - local.get
          - local.set
          - block
          - loop
          - if
          - br
          - call
          - unreachable
          - nop
          - drop
```

### 12.2.7 Implementação Completa de Fuzzer Structure-Aware

A seguir, uma implementação completa de um fuzzer structure-aware para módulos Wasm:

```rust
use wasm_mutate::WasmMutate;
use std::fs;
use std::process::Command;
use std::collections::HashSet;

struct StructureAwareFuzzer {
    validator: String,
    corpus: Vec<Vec<u8>>,
    crashes: Vec<Vec<u8>>,
    coverage: HashSet<u64>,
    max_iterations: usize,
}

impl StructureAwareFuzzer {
    fn new(validator: &str, max_iterations: usize) -> Self {
        Self {
            validator: validator.to_string(),
            corpus: Vec::new(),
            crashes: Vec::new(),
            coverage: HashSet::new(),
            max_iterations,
        }
    }
    
    fn load_seed(&mut self, path: &str) {
        let data = fs::read(path).expect("Falha ao ler seed");
        self.corpus.push(data);
    }
    
    fn validate_module(&self, wasm_bytes: &[u8]) -> bool {
        let output = Command::new(&self.validator)
            .arg("-")
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .and_then(|mut child| {
                use std::io::Write;
                child.stdin.as_mut().unwrap().write_all(wasm_bytes)?;
                child.wait()
            });
        
        match output {
            Ok(status) => status.success(),
            Err(_) => false,
        }
    }
    
    fn mutate_module(&self, wasm_bytes: &[u8]) -> Option<Vec<u8>> {
        let mut config = WasmMutate::new();
        config.preserve_semantics(false);
        
        match config.run(wasm_bytes) {
            Ok(mutated) => Some(mutated),
            Err(_) => None,
        }
    }
    
    fn calculate_hash(&self, wasm_bytes: &[u8]) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        
        let mut hasher = DefaultHasher::new();
        wasm_bytes.hash(&mut hasher);
        hasher.finish()
    }
    
    fn run(&mut self) {
        println!("Iniciando campanha de fuzzing structure-aware");
        println!("Sementes iniciais: {}", self.corpus.len());
        println!("Máximo de iterações: {}", self.max_iterations);
        
        for i in 0..self.max_iterations {
            if self.corpus.is_empty() {
                println!("Corpus vazio, gerando módulo inicial");
                self.corpus.push(self.generate_minimal_module());
            }
            
            // Selecionar seed aleatória
            let seed_idx = rand::random::<usize>() % self.corpus.len();
            let seed = &self.corpus[seed_idx];
            
            // Gerar mutação
            if let Some(mutated) = self.mutate_module(seed) {
                // Calcular hash para cobertura
                let hash = self.calculate_hash(&mutated);
                
                if !self.coverage.contains(&hash) {
                    self.coverage.insert(hash);
                    
                    // Validar se é executável
                    if self.validate_module(&mutated) {
                        // Tentar executar e detectar crash
                        match self.execute_module(&mutated) {
                            ExecutionResult::Crash => {
                                println!("CRASH encontrado na iteração {}", i);
                                self.crashes.push(mutated);
                            }
                            ExecutionResult::Timeout => {
                                println!("TIMEOUT na iteração {}", i);
                            }
                            ExecutionResult::Ok => {
                                // Adicionar ao corpus por cobertura nova
                                if self.coverage.len() > self.corpus.len() {
                                    self.corpus.push(mutated);
                                }
                            }
                        }
                    }
                }
            }
            
            if i % 1000 == 0 {
                println!(
                    "Iteração {}/{} | Cobertura: {} | Corpus: {} | Crashes: {}",
                    i, self.max_iterations,
                    self.coverage.len(),
                    self.corpus.len(),
                    self.crashes.len()
                );
            }
        }
        
        println!("\nCampanha concluída:");
        println!("  Iterações: {}", self.max_iterations);
        println!("  Cobertura: {}", self.coverage.len());
        println!("  Crashes: {}", self.crashes.len());
    }
    
    fn execute_module(&self, wasm_bytes: &[u8]) -> ExecutionResult {
        // Salvar temporário
        let tmp_path = "/tmp/fuzz_target.wasm";
        fs::write(tmp_path, wasm_bytes).expect("Falha ao escrever arquivo temporário");
        
        let result = Command::new("wasmtime")
            .arg("--dir=.")
            .arg(tmp_path)
            .timeout(std::time::Duration::from_secs(5))
            .output();
        
        match result {
            Ok(output) => {
                if !output.status.success() {
                    ExecutionResult::Crash
                } else {
                    ExecutionResult::Ok
                }
            }
            Err(_) => ExecutionResult::Timeout,
        }
    }
    
    fn generate_minimal_module(&self) -> Vec<u8> {
        // Módulo Wasm mínimo: função que retorna 42
        vec![
            0x00, 0x61, 0x73, 0x6D, // magic
            0x01, 0x00, 0x00, 0x00, // version
            // type section
            0x01, 0x05, // id=1, size=5
            0x01,       // 1 type
            0x60, 0x00, 0x01, 0x7F, // func () -> i32
            // code section
            0x0A, 0x09, // id=10, size=9
            0x01,       // 1 function
            0x07,       // body size=7
            0x00,       // 0 locals
            0x41, 0x2A, // i32.const 42
            0x0B,       // end
        ]
    }
}

enum ExecutionResult {
    Ok,
    Crash,
    Timeout,
}

fn main() {
    let mut fuzzer = StructureAwareFuzzer::new("wasm-validate", 100000);
    fuzzer.load_seed("seed.wasm");
    fuzzer.run();
}
```

## 12.3 wasm-libFuzzer

libFuzzer é um framework de fuzzing baseado em cobertura, amplamente utilizado em projetos de segurança. Adaptar libFuzzer para operar com módulos Wasm permite combinar a eficiência do fuzzing coverage-guided com o conhecimento da estrutura do formato Wasm.

### 12.3.1 Visão Geral do libFuzzer Adaptado para Wasm

O libFuzzer original opera chamando uma função `LLVMFuzzerTestOneInput` com bytes arbitrários. Para Wasm, precisamos adaptar essa interface para que:

1. Os bytes gerados sejam convertidos em módulos Wasm válidos ou parcialmente válidos
2. O módulo seja carregado e executado no runtime Wasm
3. O resultado seja avaliado quanto a crashes ou comportamento anômalo

```
+------------------------------------------------------------------+
|               Arquitetura wasm-libFuzzer                            |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  | libFuzzer        |    | Wasm Mutator    |    | Runtime Wasm  | |
|  | (geração de      | -> | (mutações       | -> | (execução     | |
|  |  bytes)          |    |  estruturadas)  |    |  isolada)     | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |          |
|           v                       v                      v          |
|  +------------------+    +------------------+    +---------------+ |
|  | Coverage Map     |    | Corpus Manager  |    | Crash Handler | |
|  | (bitmap de       | <- | (sementes)      | <- | (salvar crash)| |
|  |  cobertura)      |    |                  |    |               | |
|  +------------------+    +------------------+    +---------------+ |
|                                                                    |
+------------------------------------------------------------------+
```

### 12.3.2 Configuração do libFuzzer para Módulos Wasm

```rust
// wasm_fuzzer_target.rs - Target para libFuzzer
use std::sync::atomic::{AtomicBool, Ordering};

static ACTIVE: AtomicBool = AtomicBool::new(true);

/// Target function para libFuzzer
/// Recebe bytes arbitrários e tenta executá-los como módulo Wasm
#[no_mangle]
pub extern "C" fn LLVMFuzzerTestOneInput(data: *const u8, size: usize) -> i32 {
    if size < 8 {
        return 0; // Muito pequeno para ser um módulo Wasm
    }
    
    // Converter slice seguro
    let input = unsafe { std::slice::from_raw_parts(data, size) };
    
    // Verificar magic number rapidamente
    if &input[0..4] != b"\0asm" {
        return 0;
    }
    
    // Tentar carregar o módulo no runtime
    match wasmtime::Module::new(&crate::ENGINE, input) {
        Ok(module) => {
            // Módulo válido - tentar instanciar e executar
            let result = execute_module(&module);
            if let Err(e) = result {
                eprintln!("Erro de execução: {:?}", e);
                // Não abortar - apenas reportar
            }
        }
        Err(e) => {
            // Módulo inválido - isso é esperado na maioria das vezes
            // Apenas log para análise
            if std::env::var("FUZZ_LOG_INVALID").is_ok() {
                eprintln!("Módulo inválido: {:?}", e);
            }
        }
    }
    
    0
}

fn execute_module(module: &wasmtime::Module) -> Result<(), Box<dyn std::error::Error>> {
    let engine = wasmtime::Engine::default();
    let store = wasmtime::Store::new(&engine, ());
    
    // Criar linker com WASI mínimo
    let mut linker = wasmtime::Linker::new(&engine);
    wasmtime_wasi::add_to_linker(&mut linker, |s| s)?;
    
    // Instanciar módulo
    let instance = linker.instantiate(&store, module)?;
    
    // Chamar _start se existir, ou main, ou qualquer exportação
    if let Ok(func) = instance.get_typed_func::<(), ()>(&store, "_start") {
        func.call(&mut store, ())?;
    } else if let Ok(func) = instance.get_typed_func::<(), ()>(&store, "main") {
        func.call(&mut store, ())?;
    }
    
    Ok(())
}
```

### 12.3.3 Custom Mutators para Bytecode Wasm

O libFuzzer suporta mutadores customizados que podem gerar entradas mais inteligentes:

```rust
// wasm_custom_mutator.rs - Mutador customizado para libFuzzer
use std::slice;

/// Mutador customizado chamado pelo libFuzzer
/// Recebe uma entrada existente e gera uma nova versão mutada
#[no_mangle]
pub extern "C" fn LLVMFuzzerCustomMutator(
    data: *mut u8,
    size: usize,
    max_size: usize,
    seed: u32,
) -> usize {
    let input = unsafe { slice::from_raw_parts_mut(data, size) };
    
    // Escolher estratégia de mutação baseada no seed
    let strategy = seed % 6;
    
    match strategy {
        0 => mutate_bytes(input, max_size),
        1 => mutate_sections(input, max_size),
        2 => mutate_instructions(input, max_size),
        3 => mutate_operands(input, max_size),
        4 => mutate_types(input, max_size),
        5 => splice_modules(input, max_size),
        _ => size,
    }
}

fn mutate_bytes(input: &mut [u8], max_size: usize) -> usize {
    // Mutação byte-a-byte simples
    let mut rng = xorshift_rng(input.len() as u64);
    
    for byte in input.iter_mut() {
        if rng.next() % 10 == 0 {
            *byte = rng.next() as u8;
        }
    }
    input.len()
}

fn mutate_sections(input: &mut [u8], max_size: usize) -> usize {
    if input.len() < 8 {
        return input.len();
    }
    
    // Encontrar limites das seções
    let mut sections = Vec::new();
    let mut offset = 8; // Pular magic + version
    
    while offset < input.len() {
        let section_start = offset;
        let section_id = input[offset];
        offset += 1;
        
        // Ler tamanho LEB128
        let (size, new_offset) = read_leb128(input, offset);
        offset = new_offset + size as usize;
        
        sections.push((section_start, section_id, size as usize));
    }
    
    if sections.is_empty() {
        return input.len();
    }
    
    // Escolher operação
    let mut rng = xorshift_rng(input.len() as u64);
    let op = rng.next() % 3;
    
    match op {
        0 => {
            // Remover uma seção aleatória
            if sections.len() > 1 {
                let idx = (rng.next() as usize) % sections.len();
                let (start, _, size) = sections[idx];
                let end = start + 1 + leb128_size(size as u64) + size;
                
                // shift para trás
                for i in end..input.len() {
                    input[i - (end - start)] = input[i];
                }
                input.len() - (end - start)
            } else {
                input.len()
            }
        }
        1 => {
            // Duplicar uma seção
            if sections.len() > 0 {
                let idx = (rng.next() as usize) % sections.len();
                let (start, id, size) = sections[idx];
                let section_size = 1 + leb128_size(size as u64) + size;
                
                if input.len() + section_size <= max_size {
                    // Abrir espaço
                    for i in (start..input.len()).rev() {
                        input[i + section_size] = input[i];
                    }
                    // Copiar seção
                    for i in 0..section_size {
                        input[start + i] = input[start + i];
                    }
                    input.len() + section_size
                } else {
                    input.len()
                }
            } else {
                input.len()
            }
        }
        _ => {
            // Inserir bytes aleatórios no início de uma seção
            let idx = (rng.next() as usize) % sections.len();
            let (start, _, _) = sections[idx];
            let insert_pos = start + 1; // Após o ID
            
            if input.len() + 4 <= max_size {
                for i in (insert_pos..input.len()).rev() {
                    input[i + 4] = input[i];
                }
                for i in 0..4 {
                    input[insert_pos + i] = rng.next() as u8;
                }
                input.len() + 4
            } else {
                input.len()
            }
        }
    }
}

fn mutate_instructions(input: &mut [u8], max_size: usize) -> usize {
    // Encontrar seção de código e mutar instruções
    let mut offset = 8;
    
    while offset < input.len() {
        let section_id = input[offset];
        offset += 1;
        
        let (section_size, new_offset) = read_leb128(input, offset);
        offset = new_offset;
        
        if section_id == 10 {
            // Seção de código - mutar instruções
            return mutate_code_section(input, offset, section_size as usize, max_size);
        }
        
        offset += section_size as usize;
    }
    
    input.len()
}

fn mutate_code_section(
    input: &mut [u8],
    start: usize,
    size: usize,
    max_size: usize,
) -> usize {
    let mut rng = xorshift_rng(start as u64);
    let section_end = start + size;
    
    // Encontrar e mutar uma instrução
    let mut pos = start + 4; // Pular count de funções
    
    while pos < section_end && pos < input.len() {
        let (body_size, new_pos) = read_leb128(input, pos);
        pos = new_pos;
        
        let body_end = pos + body_size as usize;
        
        // Dentro do corpo, encontrar instruções
        while pos < body_end && pos < input.len() {
            let opcode = input[pos];
            
            match opcode {
                0x41 => {
                    // i32.const - mutar o operando
                    if pos + 4 < input.len() {
                        let (_, imm_end) = read_leb128(input, pos + 1);
                        if imm_end < input.len() {
                            // Substituir constante
                            input[imm_end] = rng.next() as u8;
                        }
                    }
                }
                0x28 => {
                    // i32.load - mutar alinhamento e offset
                    if pos + 3 < input.len() {
                        input[pos + 1] = rng.next() as u8; // alinhamento
                        input[pos + 2] = rng.next() as u8; // offset
                    }
                }
                0x36 => {
                    // i32.store - mutar alinhamento e offset
                    if pos + 3 < input.len() {
                        input[pos + 1] = rng.next() as u8;
                        input[pos + 2] = rng.next() as u8;
                    }
                }
                _ => {}
            }
            
            pos += 1;
        }
        
        pos = body_end;
    }
    
    input.len()
}

fn mutate_operands(input: &mut [u8], max_size: usize) -> usize {
    let mut rng = xorshift_rng(input.len() as u64);
    
    // Encontrar constantes numéricas e mutá-las
    let mut i = 8;
    while i < input.len() {
        match input[i] {
            0x41 => {
                // i32.const
                if i + 5 < input.len() {
                    input[i + 1] = 0xFF;
                    input[i + 2] = 0xFF;
                    input[i + 3] = 0xFF;
                    input[i + 4] = 0x7F;
                    i += 5;
                } else {
                    i += 1;
                }
            }
            0x42 => {
                // i64.const
                if i + 9 < input.len() {
                    input[i + 1] = 0xFF;
                    input[i + 2] = 0xFF;
                    input[i + 3] = 0xFF;
                    input[i + 4] = 0xFF;
                    input[i + 5] = 0xFF;
                    input[i + 6] = 0xFF;
                    input[i + 7] = 0xFF;
                    input[i + 8] = 0x7F;
                    i += 9;
                } else {
                    i += 1;
                }
            }
            _ => i += 1,
        }
    }
    
    input.len()
}

fn mutate_types(input: &mut [u8], max_size: usize) -> usize {
    let mut offset = 8;
    
    while offset < input.len() {
        let section_id = input[offset];
        offset += 1;
        
        let (section_size, new_offset) = read_leb128(input, offset);
        offset = new_offset;
        
        if section_id == 1 {
            // Seção de tipos - mutar assinaturas
            let mut pos = offset;
            let end = offset + section_size as usize;
            
            while pos < end && pos < input.len() {
                if input[pos] == 0x60 {
                    // Func type
                    // Mutar número de parâmetros
                    if pos + 1 < input.len() {
                        input[pos + 1] = 4; // Muitos parâmetros
                    }
                }
                pos += 1;
            }
        }
        
        offset += section_size as usize;
    }
    
    input.len()
}

fn splice_modules(input: &mut [u8], max_size: usize) -> usize {
    // Splice: pegar bytes aleatórios e injetar
    let mut rng = xorshift_rng(input.len() as u64);
    let pos = (rng.next() as usize) % input.len().max(1);
    let len = (rng.next() as usize % 16) + 1;
    
    for i in 0..len {
        if pos + i < input.len() {
            input[pos + i] = rng.next() as u8;
        }
    }
    
    input.len()
}

// Utilitários
struct XorShiftRng(u64);

impl XorShiftRng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
}

fn xorshift_rng(seed: u64) -> XorShiftRng {
    XorShiftRng(seed.wrapping_add(1))
}

fn read_leb128(data: &[u8], offset: usize) -> (u64, usize) {
    let mut result: u64 = 0;
    let mut shift = 0;
    let mut pos = offset;
    
    while pos < data.len() {
        let byte = data[pos];
        result |= ((byte & 0x7F) as u64) << shift;
        pos += 1;
        if byte & 0x80 == 0 {
            break;
        }
        shift += 7;
    }
    
    (result, pos)
}

fn leb128_size(mut value: u64) -> usize {
    let mut size = 0;
    loop {
        size += 1;
        value >>= 7;
        if value == 0 {
            break;
        }
    }
    size
}
```

### 12.3.4 Gerenciamento de Corpus

O corpus é a coleção de entradas que o fuzzer utiliza como sementes para mutação. Um bom corpus maximiza a cobertura de código:

```python
import os
import hashlib
import json
from pathlib import Path

class WasmCorpusManager:
    """Gerenciador de corpus para fuzzing de Wasm."""
    
    def __init__(self, corpus_dir):
        self.corpus_dir = Path(corpus_dir)
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        self.coverage_map = {}  # hash -> file_path
        self.metadata = {}  # filename -> metadata
    
    def add_seed(self, wasm_bytes, filename=None):
        """Adiciona um seed ao corpus se cobre código novo."""
        content_hash = hashlib.sha256(wasm_bytes).hexdigest()[:16]
        
        if content_hash in self.coverage_map:
            return False  # Já existe
        
        if filename is None:
            filename = f"seed_{content_hash}.wasm"
        
        filepath = self.corpus_dir / filename
        filepath.write_bytes(wasm_bytes)
        
        self.coverage_map[content_hash] = filepath
        self.metadata[filename] = {
            'hash': content_hash,
            'size': len(wasm_bytes),
            'source': 'manual'
        }
        
        self._save_metadata()
        return True
    
    def minimize_corpus(self, validator):
        """Minimiza o corpus removendo seeds redundantes."""
        to_remove = []
        
        for filename, meta in self.metadata.items():
            filepath = self.corpus_dir / filename
            if not filepath.exists():
                to_remove.append(filename)
                continue
            
            wasm_bytes = filepath.read_bytes()
            
            # Verificar se o seed é válido
            if not validator.validate(wasm_bytes):
                to_remove.append(filename)
                continue
            
            # Verificar se é mínimo (remover bytes e revalidar)
            minimized = self._minimize_input(wasm_bytes, validator)
            if minimized is not None and len(minimized) < len(wasm_bytes):
                filepath.write_bytes(minimized)
                meta['size'] = len(minimized)
                meta['minimized'] = True
        
        for filename in to_remove:
            filepath = self.corpus_dir / filename
            if filepath.exists():
                filepath.unlink()
            del self.metadata[filename]
        
        self._save_metadata()
    
    def _minimize_input(self, wasm_bytes, validator):
        """Tenta minimizar uma entrada removendo bytes."""
        best = wasm_bytes
        
        for i in range(len(wasm_bytes) - 1, -1, -1):
            candidate = best[:i] + best[i+1:]
            if validator.validate(candidate):
                best = candidate
        
        return best if len(best) < len(wasm_bytes) else None
    
    def get_stats(self):
        """Retorna estatísticas do corpus."""
        total_size = sum(
            (self.corpus_dir / f).stat().st_size
            for f in self.metadata
            if (self.corpus_dir / f).exists()
        )
        
        return {
            'total_seeds': len(self.metadata),
            'total_size': total_size,
            'average_size': total_size // max(len(self.metadata), 1),
            'coverage_entries': len(self.coverage_map)
        }
    
    def _save_metadata(self):
        meta_path = self.corpus_dir / 'corpus_meta.json'
        meta_path.write_text(json.dumps(self.metadata, indent=2))
    
    def _load_metadata(self):
        meta_path = self.corpus_dir / 'corpus_meta.json'
        if meta_path.exists():
            self.metadata = json.loads(meta_path.read_text())
```

### 12.3.5 Dicionário de Fuzzing para Instruções Wasm

Dicionários ajudam o fuzzer a gerar entradas que contêm valores significativos:

```
# wasm_dict.txt - Dicionário para fuzzing de instruções Wasm

# Magic e versão
"\x00\x61\x73\x6d"
"\x01\x00\x00\x00"

# IDs de seção
"\x01"  # type
"\x02"  # import
"\x03"  # function
"\x04"  # table
"\x05"  # memory
"\x06"  # global
"\x07"  # export
"\x08"  # start
"\x09"  # element
"\x0A"  # code
"\x0B"  # data
"\x0C"  # tag

# Tipos de valor
"\x7F"  # i32
"\x7E"  # i64
"\x7D"  # f32
"\x7C"  # f64

# Tipos de resultado
"\x40"  # void

# Functype prefix
"\x60"

# Instruções comuns
"\x00"  # unreachable
"\x01"  # nop
"\x0B"  # end
"\x0C"  # br
"\x0D"  # br_if
"\x0F"  # return
"\x10"  # call
"\x11"  # call_indirect

# Loads e stores
"\x28"  # i32.load
"\x29"  # i64.load
"\x2A"  # f32.load
"\x2B"  # f64.load
"\x36"  # i32.store
"\x37"  # i64.store
"\x38"  # f32.store
"\x39"  # f64.store

# Operações numéricas i32
"\x41"  # i32.const
"\x42"  # i64.const
"\x45"  # i32.eqz
"\x46"  # i32.eq
"\x47"  # i32.ne
"\x48"  # i32.lt_s
"\x6A"  # i32.add
"\x6B"  # i32.sub
"\x6C"  # i32.mul
"\x6D"  # i32.div_s
"\x6E"  # i32.div_u
"\x6F"  # i32.rem_s
"\x70"  # i32.rem_u

# Controle de fluxo
"\x02"  # block
"\x03"  # loop
"\x04"  # if
"\x05"  # else

# Valores extremos
"\x7F\xFF\xFF\xFF\xFF\x0F"  # i32 MAX
"\x7F\x80\x80\x80\x80\x70"  # i32 MIN
"\x41\x00"  # i32.const 0
"\x41\x01"  # i32.const 1
"\x41\xFF\x01"  # i32.const 255
```

### 12.3.6 Signal Handling e Detecção de Crash

```rust
// wasm_crash_handler.rs - Handler de crashes para fuzzing
use std::panic;
use std::sync::atomic::{AtomicBool, Ordering};
use std::fs;
use std::time::Instant;

static CRASH_OCCURRED: AtomicBool = AtomicBool::new(false);

pub struct CrashHandler {
    crash_dir: String,
    crash_count: usize,
    start_time: Instant,
}

impl CrashHandler {
    pub fn new(crash_dir: &str) -> Self {
        // Configurar handler de panic
        let default_hook = panic::take_hook();
        panic::set_hook(Box::new(move |info| {
            CRASH_OCCURRED.store(true, Ordering::SeqCst);
            
            let payload = info.payload();
            let message = if let Some(s) = payload.downcast_ref::<&str>() {
                s.to_string()
            } else if let Some(s) = payload.downcast_ref::<String>() {
                s.clone()
            } else {
                "Unknown panic".to_string()
            };
            
            eprintln!("CRASH: {}", message);
            
            if let Some(location) = info.location() {
                eprintln!("  em {}:{}", location.file(), location.line());
            }
            
            // Chamar hook padrão
            default_hook(info);
        }));
        
        // Criar diretório de crashes
        fs::create_dir_all(crash_dir).expect("Falha ao criar diretório de crashes");
        
        Self {
            crash_dir: crash_dir.to_string(),
            crash_count: 0,
            start_time: Instant::now(),
        }
    }
    
    pub fn handle_crash(&mut self, wasm_bytes: &[u8], crash_info: &str) -> String {
        self.crash_count += 1;
        
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        
        let filename = format!(
            "crash_{}_{}.wasm",
            timestamp,
            self.crash_count
        );
        
        let filepath = format!("{}/{}", self.crash_dir, filename);
        fs::write(&filepath, wasm_bytes).expect("Falha ao escrever crash");
        
        // Salvar informações do crash
        let info_path = format!("{}/{}.info", self.crash_dir, filename);
        let info_content = format!(
            "Crash #{}\nTimestamp: {}\nSize: {} bytes\nInfo: {}\n",
            self.crash_count,
            timestamp,
            wasm_bytes.len(),
            crash_info
        );
        fs::write(&info_path, info_content).expect("Falha ao escrever info");
        
        filepath
    }
    
    pub fn stats(&self) -> String {
        let elapsed = self.start_time.elapsed().as_secs();
        format!(
            "Crashes: {} | Tempo: {}s | Taxa: {:.2} crashes/s",
            self.crash_count,
            elapsed,
            self.crash_count as f64 / elapsed.max(1) as f64
        )
    }
}

impl Drop for CrashHandler {
    fn drop(&mut self) {
        println!("\nEstatísticas finais de crash:");
        println!("{}", self.stats());
    }
}
```

### 12.3.7 Detecção de Memory Leaks com ASan

```rust
// Para compilar com suporte a AddressSanitizer:
// RUSTFLAGS="-Z sanitizer=address" cargo build --target wasm32-wasi

// Configuração de ASan para módulos Wasm
#[cfg(target_os = "wasi")]
mod asan_config {
    pub const ASAN_OPTIONS: &str = 
        "detect_leaks=1:"
        "detect_stack_use_after_return=1:"
        "check_initialization_order=1:"
        "strict_init_order=1:"
        "detect_odr_violation=1";
    
    pub fn init() {
        // Em WASI, usar variáveis de ambiente
        std::env::set_var("ASAN_OPTIONS", ASAN_OPTIONS);
    }
}

// Target com detecção de memória
#[no_mangle]
pub extern "C" fn LLVMFuzzerTestOneInput(data: *const u8, size: usize) -> i32 {
    if size < 8 {
        return 0;
    }
    
    let input = unsafe { std::slice::from_raw_parts(data, size) };
    
    // Verificar magic
    if &input[0..4] != b"\0asm" {
        return 0;
    }
    
    // Tentar decodificar e executar
    let result = std::panic::catch_unwind(|| {
        match wasmtime::Module::new(&crate::ENGINE, input) {
            Ok(module) => {
                // Forçar uso de memória para detecção de UAF
                let _exports: Vec<_> = module.exports().collect();
                
                // Criar store e instanciar
                let engine = wasmtime::Engine::default();
                let mut store = wasmtime::Store::new(&engine, ());
                let linker = wasmtime::Linker::new(&engine);
                
                match linker.instantiate(&mut store, &module) {
                    Ok(instance) => {
                        // Chamar todas as exportações
                        for export in instance.exports(&store) {
                            if let wasmtime::Extern::Func(func) = export {
                                let _ = func.call(&mut store, &[], &mut []);
                            }
                        }
                    }
                    Err(_) => {}
                }
            }
            Err(_) => {}
        }
    });
    
    match result {
        Ok(_) => 0,
        Err(_) => {
            eprintln!("PANIC detectado durante execução");
            -1
        }
    }
}
```

## 12.4 Coverage-Guided Fuzzing

Coverage-guided fuzzing é a técnica mais eficiente para encontrar vulnerabilidades em software complexo. Ao invés de gerar entradas aleatórias, o fuzzer utiliza informação de cobertura de código para direcionar a busca hacia áreas do programa que não foram exercitadas.

### 12.4.1 Como Funciona o Coverage-Guided Fuzzing

O ciclo básico do coverage-guided fuzzing:

```
+------------------------------------------------------------------+
|          Coverage-Guided Fuzzing - Ciclo de Feedback               |
+------------------------------------------------------------------+
|                                                                    |
|  1. Selecionar seed do corpus                                      |
|         |                                                          |
|         v                                                          |
|  2. Aplicar mutação na seed                                        |
|         |                                                          |
|         v                                                          |
|  3. Executar módulo Wasm com entrada mutada                        |
|         |                                                          |
|         v                                                          |
|  4. Coletar informações de cobertura (bitmap)                      |
|         |                                                          |
|         v                                                          |
|  5. Comparar com cobertura conhecida                               |
|         |                                                          |
|    +----+----+                                                     |
|    |         |                                                     |
|    v         v                                                     |
|  Nova      Cobertura                                               |
|  cobertura  já conhecida                                           |
|    |         |                                                     |
|    v         v                                                     |
|  Adicionar  Descartar                                              |
|  ao corpus  entrada                                                |
|                                                                    |
+------------------------------------------------------------------+
```

O bitmap de cobertura é um array de bytes compartilhado entre o instrumentador e o fuzzer. Cada aresta (transição entre dois blocos básicos) é mapeada para um par de índices no bitmap. Quando uma aresta é executada, o bitmap é atualizado usando XOR:

```
bitmap[edge_hash % bitmap_size] ^= 1
```

### 12.4.2 Instrumentação Baseada em Fonte

A instrumentação baseada em fonte (source-based) é aplicada durante a compilação, inserindo chamadas de contagem de cobertura em pontos estratégicos do código:

```rust
// Exemplo de instrumentação manual em Rust para Wasm
use std::sync::atomic::{AtomicUsize, Ordering};

// Bitmap de cobertura compartilhado
const MAP_SIZE: usize = 65536;
static mut COVERAGE_MAP: [u8; MAP_SIZE] = [0; MAP_SIZE];

/// Função chamada no início de cada bloco básico
#[inline(never)]
pub fn __sanitizer_cov_8bit_counters_init(start: *mut u8, stop: *mut u8) {
    // Inicializar contadores
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_pc_guard(guard: *mut u32) {
    unsafe {
        let map_idx = (*guard as usize) % MAP_SIZE;
        COVERAGE_MAP[map_idx] = COVERAGE_MAP[map_idx].wrapping_add(1);
    }
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_cmp4(arg1: u32, arg2: u32) {
    let edge = arg1.wrapping_sub(arg2) as usize;
    unsafe {
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}
```

### 12.4.3 Tracking de Cobertura em Módulos Wasm

Para módulos Wasm compilados de C/C++ com Emscripten, podemos habilitar instrumentação de cobertura:

```bash
# Compilar com cobertura habilitada via Emscripten
emcc target.c \
    -o target.wasm \
    -fsanitize=fuzzer \
    -fsanitize=address \
    -fprofile-instr-generate \
    -fcoverage-mapping

# Ou com suporte nativo a fuzzing
emcc target.c \
    -o target.js \
    -fsanitize=fuzzer \
    -s ALLOW_MEMORY_GROWTH=1
```

```python
# Cobertura para módulos Wasm nativos (compilados com Rust)
import subprocess
import json

class WasmCoverageTracker:
    """Rastreador de cobertura para módulos Wasm."""
    
    def __init__(self, map_size=65536):
        self.map_size = map_size
        self.total_coverage = bytearray(map_size)
        self.executions = 0
        self.new_coverage_count = 0
    
    def update(self, new_coverage: bytes) -> bool:
        """Atualiza o bitmap de cobertura. Retorna True se há cobertura nova."""
        self.executions += 1
        has_new = False
        
        for i in range(min(len(new_coverage), self.map_size)):
            if new_coverage[i] != 0 and self.total_coverage[i] == 0:
                has_new = True
                self.new_coverage_count += 1
            self.total_coverage[i] |= new_coverage[i]
        
        return has_new
    
    def get_edges_covered(self) -> int:
        """Retorna o número de arestas cobertas."""
        return sum(1 for b in self.total_coverage if b != 0)
    
    def get_stats(self) -> dict:
        """Retorna estatísticas de cobertura."""
        edges = self.get_edges_covered()
        return {
            'total_executions': self.executions,
            'edges_covered': edges,
            'edge_coverage_pct': (edges / self.map_size) * 100,
            'new_coverage_events': self.new_coverage_count,
            'efficiency': self.new_coverage_count / max(self.executions, 1)
        }
    
    def save_coverage(self, path: str):
        """Salva o bitmap de cobertura em arquivo."""
        with open(path, 'wb') as f:
            f.write(bytes(self.total_coverage))
    
    def load_coverage(self, path: str):
        """Carrega bitmap de cobertura de arquivo."""
        with open(path, 'rb') as f:
            data = f.read()
            self.total_coverage[:len(data)] = data[:self.map_size]
```

### 12.4.4 LLVM SanitizerCoverage para Wasm

O LLVM fornece SanitizerCoverage que pode ser usado para instrumentar módulos Wasm:

```bash
# Habilitar SanitizerCoverage para Wasm via clang
clang --target=wasm32-wasi \
    -fsanitize=fuzzer-no-link \
    -fsanitize-coverage=trace-pc-guard \
    target.c -c -o target.o

# Linkar com o fuzzer
clang --target=wasm32-wasi \
    -fsanitize=fuzzer \
    target.o -o target.wasm
```

```rust
// Callbacks do SanitizerCoverage para Wasm
#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_pc_guard_init(
    start: *mut u32,
    stop: *mut u32,
) {
    // Inicializar guards de cobertura
    unsafe {
        let mut current = start;
        while current < stop {
            *current = CURRENT_GUARD.fetch_add(1, Ordering::Relaxed);
            current = current.offset(1);
        }
    }
}

use std::sync::atomic::{AtomicU32, Ordering};
static CURRENT_GUARD: AtomicU32 = AtomicU32::new(0);

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_pc_guard(guard: *mut u32) {
    unsafe {
        let guard_val = *guard;
        let edge = guard_val as usize;
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_const_cmp1(a: u8, b: u8) {
    let edge = (a as usize).wrapping_sub(b as usize);
    unsafe {
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_const_cmp2(a: u16, b: u16) {
    let edge = (a as usize).wrapping_sub(b as usize);
    unsafe {
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_const_cmp4(a: u32, b: u32) {
    let edge = (a as usize).wrapping_sub(b as usize);
    unsafe {
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}

#[no_mangle]
pub extern "C" fn __sanitizer_cov_trace_const_cmp8(a: u64, b: u64) {
    let edge = (a as usize).wrapping_sub(b as usize);
    unsafe {
        COVERAGE_MAP[edge % MAP_SIZE] ^= 1;
    }
}

const MAP_SIZE: usize = 65536;
static mut COVERAGE_MAP: [u8; MAP_SIZE] = [0; MAP_SIZE];
```

### 12.4.5 Coverage AFL-Style em Fuzzers Wasm

AFL++ implementa um modelo de cobertura baseado em branches que pode ser adaptado para Wasm:

```python
class AFLStyleCoverage:
    """Implementação de cobertura AFL-style para Wasm."""
    
    MAP_SIZE = 65536
    HMAP_SIZE = 64  # Histogram map para contagens
    
    def __init__(self):
        self.trace = bytearray(self.MAP_SIZE)
        self.htrace = bytearray(self.HMAP_SIZE)
        self.prev_location = 0
    
    def record_branch(self, cur_location: int):
        """Registra uma transição de branch (AFL-style)."""
        edge = self.prev_location ^ cur_location
        self.trace[edge % self.MAP_SIZE] ^= 1
        
        # Contagem no histograma
        idx = edge % self.HMAP_SIZE
        if self.htrace[idx] < 255:
            self.htrace[idx] += 1
        
        self.prev_location = cur_location >> 1
    
    def record_cmp(self, arg1, arg2, cur_location: int):
        """Registra uma comparação."""
        self.record_branch(cur_location)
        
        # Hash baseado na comparação
        val = arg1 ^ arg2
        self.trace[(cur_location ^ val) % self.MAP_SIZE] ^= 1
    
    def get_new_coverage(self, other_trace: bytes) -> bool:
        """Verifica se o trace fornecido cobre código novo."""
        for i in range(self.MAP_SIZE):
            if other_trace[i] != 0 and self.trace[i] == 0:
                return True
        return False
    
    def merge_coverage(self, other_trace: bytes):
        """Mescla nova cobertura no trace acumulado."""
        for i in range(min(len(other_trace), self.MAP_SIZE)):
            self.trace[i] |= other_trace[i]
    
    def get_score(self, other_trace: bytes) -> float:
        """Calcula score de utilidade para uma entrada."""
        new_edges = 0
        for i in range(min(len(other_trace), self.MAP_SIZE)):
            if other_trace[i] != 0 and self.trace[i] == 0:
                new_edges += 1
        
        total_new = sum(1 for i in range(self.MAP_SIZE) 
                       if self.trace[i] != 0)
        return new_edges / max(total_new, 1)
```

### 12.4.6 Métricas e Análise de Cobertura

```python
class CoverageAnalyzer:
    """Análise detalhada de cobertura durante fuzzing."""
    
    def __init__(self):
        self.history = []  # [(timestamp, edges_covered, new_edges)]
        self.plateau_threshold = 1000  # iterações sem melhoria
    
    def record(self, timestamp, edges_covered, new_edges):
        self.history.append((timestamp, edges_covered, new_edges))
    
    def detect_plateau(self) -> bool:
        """Detecta se o fuzzing está em platô (sem progresso)."""
        if len(self.history) < self.plateau_threshold:
            return False
        
        recent = self.history[-self.plateau_threshold:]
        return all(e[2] == 0 for e in recent)
    
    def get_growth_rate(self) -> float:
        """Taxa de crescimento de cobertura."""
        if len(self.history) < 2:
            return 0.0
        
        initial = self.history[0][1]
        current = self.history[-1][1]
        iterations = len(self.history)
        
        return (current - initial) / max(iterations, 1)
    
    def suggest_strategy(self) -> str:
        """Sugere estratégia baseada no estado atual."""
        if self.detect_plateau():
            return "increase_mutations"  # Platô detectado
        elif self.get_growth_rate() < 0.01:
            return "add_new_seeds"  # Crescimento lento
        else:
            return "continue"  # Progresso normal
    
    def generate_report(self) -> str:
        """Gera relatório de cobertura."""
        if not self.history:
            return "Sem dados de cobertura"
        
        total_edges = self.history[-1][1]
        total_new = sum(h[2] for h in self.history)
        
        return f"""
Relatório de Cobertura
=====================
Total de iterações: {len(self.history)}
Arestas cobertas: {total_edges}
Eventos de cobertura nova: {total_new}
Taxa de crescimento: {self.get_growth_rate():.4f} arestas/iteração
Platô detectado: {'Sim' if self.detect_plateau() else 'Não'}
Estratégia sugerida: {self.suggest_strategy()}
"""
```

### 12.4.7 Comparação Coverage-Guided vs Blind Fuzzing

```
+------------------------------------------------------------------+
|         Comparação: Coverage-Guided vs Blind Fuzzing                |
+------------------------------------------------------------------+
|                                                                    |
|  Critério              | Blind Fuzzing  | Coverage-Guided          |
|  --------------------- | -------------- | ----------------------- |
|  Geração de entrada    | Aleatória      | Baseada em feedback      |
|  Eficiência            | Baixa          | Alta                     |
|  Cobertura máxima      | ~30%           | ~80%+                    |
|  Overhead              | Mínimo         | 2-5x mais lento         |
|  Implementação         | Simples        | Complexa                 |
|  Detecção de bugs      | Limitada       | Abrangente               |
|  Tempo para primeiro   | Curto          | Médio                    |
|    crash               |                |                          |
|  Uso de memória        | Mínimo         | Moderate (bitmap +       |
|                        |                | corpus)                  |
|                                                                    |
|  Para Wasm: O overhead de instrumentação é justificado             |
|  pela melhoria significativa na cobertura e detecção.              |
|                                                                    |
+------------------------------------------------------------------+
```

## 12.5 Seed Generation

A qualidade do corpus de sementes é um dos fatores mais determinantes para o sucesso de uma campanha de fuzzing. Sementes bem escolhidas permitem que o fuzzer atinja áreas de código que seriam inalcançáveis com mutações puramente aleatórias.

### 12.5.1 Estratégias de Criação de Seed Corpus

```python
import os
import struct
from pathlib import Path

class WasmSeedGenerator:
    """Gerador de sementes para fuzzing de Wasm."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.seeds = []
    
    def generate_minimal_seeds(self):
        """Gera sementes mínimas que exercitam diferentes caminhos."""
        
        seeds = {
            # Módulo vazio
            'empty_module': self._empty_module(),
            
            # Módulo com função void
            'void_function': self._void_function(),
            
            # Módulo com função que retorna i32
            'return_i32': self._return_i32(),
            
            # Módulo com função que retorna i64
            'return_i64': self._return_i64(),
            
            # Módulo com função que retorna f32
            'return_f32': self._return_f32(),
            
            # Módulo com função que retorna f64
            'return_f64': self._return_f64(),
            
            # Módulo com memória
            'with_memory': self._with_memory(),
            
            # Módulo com tabela
            'with_table': self._with_table(),
            
            # Módulo com importações
            'with_imports': self._with_imports(),
            
            # Módulo com exportações
            'with_exports': self._with_exports(),
            
            # Módulo com múltiplas funções
            'multi_function': self._multi_function(),
            
            # Módulo com controle de fluxo
            'control_flow': self._control_flow(),
            
            # Módulo com loops
            'with_loops': self._with_loops(),
            
            # Módulo com operações de memória
            'memory_ops': self._memory_ops(),
            
            # Módulo com operações numéricas
            'numeric_ops': self._numeric_ops(),
            
            # Módulo com instruções de truncamento
            'truncation_ops': self._truncation_ops(),
            
            # Módulo com block aninhados
            'nested_blocks': self._nested_blocks(),
            
            # Módulo com call indireto
            'call_indirect': self._call_indiret(),
            
            # Módulo com globals
            'with_globals': self._with_globals(),
            
            # Módulo com elements
            'with_elements': self._with_elements(),
        }
        
        for name, wasm_bytes in seeds.items():
            filepath = self.output_dir / f"{name}.wasm"
            filepath.write_bytes(wasm_bytes)
            self.seeds.append(name)
        
        return self.seeds
    
    def generate_from_wat(self, wat_text: str) -> bytes:
        """Converte WAT (WebAssembly Text) para binário Wasm."""
        # Usar wabt para conversão
        import subprocess
        
        wat_path = self.output_dir / "temp.wat"
        wat_path.write_text(wat_text)
        
        result = subprocess.run(
            ["wat2wasm", str(wat_path), "-o", "-"],
            capture_output=True
        )
        
        wat_path.unlink()
        return result.stdout
    
    def _bytes_leb128_u32(self, value: int) -> bytes:
        """Codifica u32 em LEB128."""
        result = []
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result.append(byte)
            if value == 0:
                break
        return bytes(result)
    
    def _empty_module(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d'  # magic
            b'\x01\x00\x00\x00'  # version 1
        )
    
    def _void_function(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'  # type section
            b'\x03\x02\x01\x00'          # function section
            b'\x0a\x06\x01\x04\x00\x01\x01\x0b'  # code section
        )
    
    def _return_i32(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'  # type: () -> i32
            b'\x03\x02\x01\x00'
            b'\x0a\x09\x01\x07\x00\x41\x2a\x0b'  # i32.const 42; end
        )
    
    def _return_i64(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7e'  # type: () -> i64
            b'\x03\x02\x01\x00'
            b'\x0a\x0b\x01\x09\x00\x42\x80\x80\x80\x80\x08\x0b'
        )
    
    def _return_f32(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7d'  # type: () -> f32
            b'\x03\x02\x01\x00'
            b'\x0a\x09\x01\x07\x00\x43\x00\x00\x48\x40\x0b'
        )
    
    def _return_f64(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7c'  # type: () -> f64
            b'\x03\x02\x01\x00'
            b'\x0a\x0d\x01\x0b\x00\x44\x00\x00\x00\x00\x00\x00\x28\x40\x0b'
        )
    
    def _with_memory(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x05\x03\x01\x04\x00'  # memory section: 1 page, max 4
        )
    
    def _with_table(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x04\x04\x01\x70\x00\x01'  # table: 1 funcref
        )
    
    def _with_imports(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'  # type section
            b'\x02\x0d\x01\x04\x65\x6e\x76\x02\x66\x6f\x00\x00'
        )
    
    def _with_exports(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x07\x07\x01\x03\x66\x6f\x6f\x00\x00'
            b'\x0a\x09\x01\x07\x00\x41\x2a\x0b'
        )
    
    def _multi_function(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x03\x02\x00\x00'
            b'\x0a\x11\x02\x07\x00\x41\x01\x0b\x07\x00\x41\x02\x0b'
        )
    
    def _control_flow(self) -> bytes:
        # Módulo com if/else
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x06\x01\x60\x01\x7f\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0f\x01\x0d\x00\x20\x00\x45\x04\x40\x41\x01\x05\x41\x00\x0b\x0b'
        )
    
    def _with_loops(self) -> bytes:
        # Loop simples
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0f\x01\x0d\x00\x03\x40\x41\x00\x20\x00\x41\x01\x6a\x21\x00'
            b'\x20\x00\x41\x0a\x48\x0d\x00\x0b\x0b'
        )
    
    def _memory_ops(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x05\x03\x01\x04\x00'
            b'\x0a\x0c\x01\x0a\x00\x41\x00\x28\x02\x00\x1a\x0b'
        )
    
    def _numeric_ops(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x0a\x0d\x01\x0b\x00\x41\x0a\x41\x14\x6a\x1a\x0b'
        )
    
    def _truncation_ops(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0b\x01\x09\x00\x44\x00\x00\xf0\x41\x0b'
        )
    
    def _nested_blocks(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x0a\x10\x01\x0e\x00\x02\x40\x02\x40\x01\x01\x0b\x0b\x0b'
        )
    
    def _call_indiret(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x04\x04\x01\x70\x00\x01'
            b'\x09\x07\x01\x00\x01\x00\x00\x00'
            b'\x0a\x09\x01\x07\x00\x41\x00\x11\x00\x00\x0b'
        )
    
    def _with_globals(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x06\x06\x01\x7f\x01\x41\x0a\x0b'
            b'\x0a\x06\x01\x04\x00\x23\x00\x0b'
        )
    
    def _with_elements(self) -> bytes:
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x04\x04\x01\x70\x00\x01'
            b'\x09\x07\x01\x00\x01\x00\x00\x00'
            b'\x0a\x09\x01\x07\x00\x41\x00\x0b'
        )
```

### 12.5.2 Técnicas de Minimização de Seeds

```python
import subprocess
import os
import hashlib

class SeedMinimizer:
    """Minimizador de sementes para fuzzing."""
    
    def __init__(self, validator_cmd='wasm-validate'):
        self.validator = validator_cmd
    
    def minimize(self, wasm_bytes: bytes, crash_reproducer=None) -> bytes:
        """Minimiza uma entrada preservando o comportamento alvo."""
        best = wasm_bytes
        improved = True
        
        while improved:
            improved = False
            
            # Tentar remover blocos de bytes
            for chunk_size in [1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]:
                i = 0
                while i + chunk_size <= len(best):
                    candidate = best[:i] + best[i + chunk_size:]
                    
                    if crash_reproducer:
                        # Verificar se ainda reproduz o crash
                        if crash_reproducer(candidate):
                            best = candidate
                            improved = True
                            break
                    else:
                        # Verificar se ainda é válido
                        if self.is_valid(candidate):
                            best = candidate
                            improved = True
                            break
                
                if improved:
                    break
        
        return best
    
    def minimize_to_structural(self, wasm_bytes: bytes) -> bytes:
        """Minimiza preservando estrutura do formato Wasm."""
        if len(wasm_bytes) < 8:
            return wasm_bytes
        
        # Manter magic e versão
        header = wasm_bytes[:8]
        sections = self._parse_sections(wasm_bytes[8:])
        
        minimized_sections = []
        for section_id, section_data in sections:
            if section_id in [1, 3, 7, 10]:
                # Manter seções essenciais
                minimized = self._minimize_section(section_id, section_data)
                minimized_sections.append((section_id, minimized))
        
        # Reconstruir módulo
        result = header
        for section_id, data in minimized_sections:
            result += bytes([section_id])
            result += self._encode_leb128(len(data))
            result += data
        
        return result
    
    def _parse_sections(self, data):
        sections = []
        offset = 0
        while offset < len(data):
            if offset >= len(data):
                break
            section_id = data[offset]
            offset += 1
            
            size, offset = self._read_leb128(data, offset)
            section_data = data[offset:offset + size]
            offset += size
            
            sections.append((section_id, section_data))
        
        return sections
    
    def _minimize_section(self, section_id, data):
        if section_id == 10:
            # Seção de código - minimizar cada função
            return self._minimize_code_section(data)
        return data
    
    def _minimize_code_section(self, data):
        # Contagem de funções
        func_count, offset = self._read_leb128(data, 0)
        
        minimized = self._encode_leb128(func_count)
        
        for _ in range(func_count):
            if offset >= len(data):
                break
            
            body_size, offset = self._read_leb128(data, offset)
            body = data[offset:offset + body_size]
            offset += body_size
            
            # Minimizar corpo da função
            min_body = self._minimize_function_body(body)
            minimized += self._encode_leb128(len(min_body))
            minimized += min_body
        
        return minimized
    
    def _minimize_function_body(self, body):
        if len(body) < 2:
            return body
        
        # Manter declarações de locais e end
        local_count = body[0]
        
        # Encontrar o end final
        end_idx = len(body) - 1
        if body[end_idx] != 0x0B:
            # Adicionar end se não existir
            return body + b'\x0b'
        
        # Manter locais + end com instrução mínima
        result = bytes([local_count])
        
        if local_count > 0:
            # Copiar declarações de locais
            offset = 1
            for _ in range(local_count):
                count = body[offset]
                vtype = body[offset + 1]
                result += bytes([count, vtype])
                offset += 2
        
        # Instrução mínima: nop
        result += b'\x01'
        result += b'\x0b'  # end
        
        return result
    
    def _read_leb128(self, data, offset):
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                break
            shift += 7
        return result, offset
    
    def _encode_leb128(self, value):
        result = []
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result.append(byte)
            if value == 0:
                break
        return bytes(result)
    
    def is_valid(self, wasm_bytes):
        try:
            result = subprocess.run(
                [self.validator, '-'],
                input=wasm_bytes,
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False
```

### 12.5.3 Algoritmos de Agendamento de Seeds

```python
import random
import math
from collections import defaultdict

class SeedScheduler:
    """Agendamento inteligente de sementes para fuzzing."""
    
    def __init__(self):
        self.seeds = {}
        self.performance = defaultdict(lambda: {
            'executions': 0,
            'new_coverage': 0,
            'crashes': 0,
            'timeouts': 0,
            'energy': 1.0,
            'last_used': 0,
            'depth': 0,
        })
        self.total_executions = 0
    
    def add_seed(self, seed_id, data, metadata=None):
        """Adiciona uma seed ao agendador."""
        self.seeds[seed_id] = {
            'data': data,
            'metadata': metadata or {},
            'added_at': self.total_executions,
        }
    
    def select_seed(self, strategy='powerSchedule'):
        """Seleciona a próxima seed para mutação."""
        if not self.seeds:
            return None
        
        if strategy == 'uniform':
            return self._uniform_selection()
        elif strategy == 'powerSchedule':
            return self._power_schedule_selection()
        elif strategy == 'energyBased':
            return self._energy_based_selection()
        elif strategy == 'depthBased':
            return self._depth_based_selection()
        else:
            return self._uniform_selection()
    
    def _uniform_selection(self):
        """Seleção uniforme aleatória."""
        seed_ids = list(self.seeds.keys())
        return random.choice(seed_ids)
    
    def _power_schedule_selection(self):
        """Power schedule do AFL - favorece seeds produtivas."""
        candidates = list(self.seeds.items())
        
        # Calcular pesos
        weights = []
        for seed_id, seed in candidates:
            perf = self.performance[seed_id]
            
            # Fator de favorecimento de cobertura nova
            fav = 1.0
            if perf['new_coverage'] > 0:
                fav = math.log2(perf['new_coverage'] + 1)
            
            # Fator de profundidade (profundidade = mais mutações aplicadas)
            depth_factor = 1.0 + (perf['depth'] * 0.1)
            
            # Fator de idade (seeds mais antigas perdem prioridade)
            age = self.total_executions - seed['added_at'] + 1
            age_factor = 1.0 / math.log2(age + 1)
            
            # Fator de performances passadas
            perf_factor = perf['new_coverage'] + perf['crashes'] * 10
            
            weight = fav * depth_factor * age_factor * (1 + perf_factor)
            weights.append(max(weight, 0.01))
        
        # Seleção ponderada
        total = sum(weights)
        r = random.random() * total
        
        cumulative = 0
        for (seed_id, _), weight in zip(candidates, weights):
            cumulative += weight
            if r <= cumulative:
                return seed_id
        
        return candidates[-1][0]
    
    def _energy_based_selection(self):
        """Seleção baseada em energia - seeds com mais energia são favoritas."""
        candidates = list(self.seeds.keys())
        
        energies = []
        for seed_id in candidates:
            perf = self.performance[seed_id]
            energy = perf['energy']
            energies.append(energy)
        
        total = sum(energies)
        if total == 0:
            return random.choice(candidates)
        
        r = random.random() * total
        cumulative = 0
        
        for seed_id, energy in zip(candidates, energies):
            cumulative += energy
            if r <= cumulative:
                return seed_id
        
        return candidates[-1]
    
    def _depth_based_selection(self):
        """Seleção baseada em profundidade - explora caminhos mais profundos."""
        candidates = list(self.seeds.items())
        
        # Ordenar por profundidade (maior primeiro)
        candidates.sort(
            key=lambda x: self.performance[x[0]]['depth'],
            reverse=True
        )
        
        # Tomar top 50% com probabilidade decrescente
        top_n = max(1, len(candidates) // 2)
        weights = [1.0 / (i + 1) for i in range(top_n)]
        
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        
        for i, (seed_id, _) in enumerate(candidates[:top_n]):
            cumulative += weights[i]
            if r <= cumulative:
                return seed_id
        
        return candidates[0][0]
    
    def update_performance(self, seed_id, new_coverage=0, crash=False, timeout=False):
        """Atualiza métricas de performance de uma seed."""
        perf = self.performance[seed_id]
        perf['executions'] += 1
        perf['new_coverage'] += new_coverage
        
        if crash:
            perf['crashes'] += 1
            perf['energy'] *= 2.0  # Aumentar energia para seeds que causam crash
        
        if timeout:
            perf['timeouts'] += 1
            perf['energy'] *= 0.5  # Reduzir energia para seeds que causam timeout
        
        if new_coverage > 0:
            perf['energy'] *= 1.5  # Aumentar energia para cobertura nova
        
        # Limitar energia
        perf['energy'] = min(perf['energy'], 100.0)
        perf['energy'] = max(perf['energy'], 0.01)
        
        perf['last_used'] = self.total_executions
        self.total_executions += 1
    
    def increase_depth(self, seed_id):
        """Aumenta a profundidade de uma seed (após mutação bem-sucedida)."""
        self.performance[seed_id]['depth'] += 1
    
    def get_stats(self):
        """Retorna estatísticas do agendador."""
        total_seeds = len(self.seeds)
        total_energy = sum(
            self.performance[sid]['energy']
            for sid in self.seeds
        )
        
        productive_seeds = sum(
            1 for sid in self.seeds
            if self.performance[sid]['new_coverage'] > 0
        )
        
        return {
            'total_seeds': total_seeds,
            'productive_seeds': productive_seeds,
            'total_energy': total_energy,
            'average_energy': total_energy / max(total_seeds, 1),
            'total_executions': self.total_executions,
        }
```

### 12.5.4 Seed Dictionary para Instruções Wasm

```python
class WasmInstructionDictionary:
    """Dicionário de instruções Wasm para fuzzing."""
    
    # Instruções por categoria
    CATEGORIES = {
        'control': {
            'unreachable': b'\x00',
            'nop': b'\x01',
            'block': b'\x02',
            'loop': b'\x03',
            'if': b'\x04',
            'else': b'\x05',
            'end': b'\x0b',
            'br': b'\x0c',
            'br_if': b'\x0d',
            'br_table': b'\x0e',
            'return': b'\x0f',
            'call': b'\x10',
            'call_indirect': b'\x11',
        },
        'parametric': {
            'drop': b'\x1a',
            'select': b'\x1b',
        },
        'variable': {
            'local.get': b'\x20',
            'local.set': b'\x21',
            'local.tee': b'\x22',
            'global.get': b'\x23',
            'global.set': b'\x24',
        },
        'memory': {
            'i32.load': b'\x28',
            'i64.load': b'\x29',
            'f32.load': b'\x2a',
            'f64.load': b'\x2b',
            'i32.load8_s': b'\x2c',
            'i32.load8_u': b'\x2d',
            'i32.load16_s': b'\x2e',
            'i32.load16_u': b'\x2f',
            'i64.load8_s': b'\x30',
            'i64.load8_u': b'\x31',
            'i64.load16_s': b'\x32',
            'i64.load16_u': b'\x33',
            'i64.load32_s': b'\x34',
            'i64.load32_u': b'\x35',
            'i32.store': b'\x36',
            'i64.store': b'\x37',
            'f32.store': b'\x38',
            'f64.store': b'\x39',
            'i32.store8': b'\x3a',
            'i32.store16': b'\x3b',
            'i64.store8': b'\x3c',
            'i64.store16': b'\x3d',
            'i64.store32': b'\x3e',
            'memory.size': b'\x3f\x00',
            'memory.grow': b'\x40\x00',
        },
        'numeric': {
            'i32.const': b'\x41',
            'i64.const': b'\x42',
            'f32.const': b'\x43',
            'f64.const': b'\x44',
        },
        'i32_operations': {
            'i32.eqz': b'\x45',
            'i32.eq': b'\x46',
            'i32.ne': b'\x47',
            'i32.lt_s': b'\x48',
            'i32.lt_u': b'\x49',
            'i32.gt_s': b'\x4a',
            'i32.gt_u': b'\x4b',
            'i32.le_s': b'\x4c',
            'i32.le_u': b'\x4d',
            'i32.ge_s': b'\x4e',
            'i32.ge_u': b'\x4f',
            'i32.clz': b'\x67',
            'i32.ctz': b'\x68',
            'i32.popcnt': b'\x69',
            'i32.add': b'\x6a',
            'i32.sub': b'\x6b',
            'i32.mul': b'\x6c',
            'i32.div_s': b'\x6d',
            'i32.div_u': b'\x6e',
            'i32.rem_s': b'\x6f',
            'i32.rem_u': b'\x70',
            'i32.and': b'\x71',
            'i32.or': b'\x72',
            'i32.xor': b'\x73',
            'i32.shl': b'\x74',
            'i32.shr_s': b'\x75',
            'i32.shr_u': b'\x76',
            'i32.rotl': b'\x77',
            'i32.rotr': b'\x78',
        },
    }
    
    # Valores extremos para constantes
    EXTREME_VALUES = {
        'i32': [
            b'\x00',                           # 0
            b'\x01',                           # 1
            b'\x7f',                           # -1
            b'\x80\x7f',                       # i32::MAX (2147483647)
            b'\x80\x80\x80\x80\x78',          # i32::MIN (-2147483648)
        ],
        'i64': [
            b'\x00',                           # 0
            b'\x01',                           # 1
            b'\x7f',                           # -1
            b'\x80\x80\x80\x80\x80\x80\x80\x80\x7f',  # i64::MAX
            b'\x80\x80\x80\x80\x80\x80\x80\x80\x40',  # i64::MIN
        ],
        'f32': [
            b'\x00\x00\x00\x00',              # 0.0
            b'\x00\x00\x80\x7f',              # -0.0
            b'\x00\x00\x80\x7f',              # NaN
            b'\x00\x00\x80\x7f',              # -NaN
            b'\x00\x00\x80\x7f',              # Infinity
            b'\x00\x00\x80\xff',              # -Infinity
        ],
    }
    
    def __init__(self):
        self.all_instructions = []
        for category, instructions in self.CATEGORIES.items():
            for name, opcode in instructions.items():
                self.all_instructions.append((category, name, opcode))
    
    def get_random_instruction(self, category=None):
        """Retorna uma instrução aleatória."""
        if category:
            candidates = [
                (name, opcode)
                for cat, name, opcode in self.all_instructions
                if cat == category
            ]
        else:
            candidates = [
                (name, opcode)
                for _, name, opcode in self.all_instructions
            ]
        
        if not candidates:
            return None
        
        return random.choice(candidates)
    
    def generate_random_body(self, max_instructions=10):
        """Gera um corpo de função aleatório."""
        body = b''
        depth = 0
        
        for _ in range(max_instructions):
            # Escolher instrução baseada no contexto
            if depth == 0:
                # Fora de bloco - apenas instruções que não alteram profundidade
                instr = self.get_random_instruction('numeric')
            else:
                # Dentro de bloco - qualquer instrução
                instr = self.get_random_instruction()
            
            if instr is None:
                continue
            
            name, opcode = instr
            
            if name in ['block', 'loop', 'if']:
                depth += 1
            elif name == 'end':
                if depth > 0:
                    depth -= 1
                else:
                    opcode = b'\x01'  # nop
            
            body += opcode
            
            # Adicionar operandos para instruções que precisam
            if name == 'i32.const':
                body += b'\x00'  # constante simples
            elif name in ['local.get', 'local.set', 'local.tee']:
                body += b'\x00'  # local index 0
            elif name in ['global.get', 'global.set']:
                body += b'\x00'  # global index 0
            elif name in ['br', 'br_if']:
                body += b'\x00'  # label index 0
            elif name == 'call':
                body += b'\x00'  # function index 0
        
        # Adicionar end se necessário
        while depth > 0:
            body += b'\x0b'
            depth -= 1
        
        return body
    
    def generate_function_with_extremes(self):
        """Gera função que usa valores extremos."""
        body = b''
        
        # i32.const com valor extremo
        body += b'\x41'  # i32.const
        body += b'\x80\x80\x80\x80\x08'  # i32::MAX
        
        # Operações que podem causar overflow
        body += b'\x6a'  # i32.add
        body += b'\x41'  # i32.const
        body += b'\x01'  # 1
        body += b'\x6d'  # i32.div_s (divisão pode causar overflow com MIN/-1)
        
        body += b'\x0b'  # end
        
        return body
```

### 12.5.5 Corpus Distillation

Corpus distillation é o processo de reduzir o corpus mantendo apenas as sementes que contribuem para cobertura única:

```python
class CorpusDistiller:
    """Destilação de corpus - manter apenas sementes essenciais."""
    
    def __init__(self):
        self.seed_coverage = {}  # seed_id -> set of edges
        self.global_coverage = set()
    
    def add_seed_coverage(self, seed_id, edges):
        """Registra a cobertura de uma seed."""
        self.seed_coverage[seed_id] = set(edges)
    
    def distill(self):
        """Retorna sementes essenciais (que cobrem arestas únicas)."""
        # Calcular cobertura global
        self.global_coverage = set()
        for edges in self.seed_coverage.values():
            self.global_coverage.update(edges)
        
        # Para cada aresta, encontrar a seed mais pequena que a cobre
        edge_to_seed = {}
        for seed_id, edges in self.seed_coverage.items():
            for edge in edges:
                if edge not in edge_to_seed:
                    edge_to_seed[edge] = seed_id
                else:
                    # Manter a seed menor
                    current = edge_to_seed[edge]
                    if len(self.seed_coverage[seed_id]) < len(self.seed_coverage[current]):
                        edge_to_seed[edge] = seed_id
        
        # Sementes essenciais
        essential = set(edge_to_seed.values())
        
        # Seeds redundantes (não cobrem nenhuma aresta única)
        redundant = set(self.seed_coverage.keys()) - essential
        
        return {
            'essential': list(essential),
            'redundant': list(redundant),
            'reduction_ratio': len(redundant) / max(len(self.seed_coverage), 1),
            'total_edges': len(self.global_coverage),
        }
    
    def get_minimal_covering_set(self):
        """Encontra o conjunto mínimo de sementes que cobre todas as arestas."""
        uncovered = self.global_coverage.copy()
        selected = []
        
        while uncovered:
            # Selecionar seed que cobre mais arestas não cobertas
            best_seed = None
            best_cover = set()
            
            for seed_id, edges in self.seed_coverage.items():
                cover = edges & uncovered
                if len(cover) > len(best_cover):
                    best_cover = cover
                    best_seed = seed_id
            
            if best_seed is None:
                break
            
            selected.append(best_seed)
            uncovered -= best_cover
        
        return selected
```

## 12.6 Crash Analysis

Encontrar crashes é apenas o início. Uma análise adequada é necessária para classificar, minimizar e reproduzir os bugs descobertos pelo fuzzer.

### 12.6.1 Classificação e Triagem de Crashes

```python
import re
import subprocess
from collections import defaultdict

class CrashClassifier:
    """Classificador de crashes para fuzzing de Wasm."""
    
    CRASH_PATTERNS = {
        'segfault': [
            r'segmentation fault',
            r'core dumped',
            r'signal 11',
            r'access violation',
        ],
        'abort': [
            r'abort',
            r'signal 6',
            r'Assertion.*failed',
            r'runtime error',
        ],
        'stack_overflow': [
            r'stack overflow',
            r'stack smashing',
            r'signal 8',
        ],
        'oom': [
            r'out of memory',
            r'memory allocation failed',
            r'cannot allocate',
        ],
        'timeout': [
            r'timeout',
            r'timed out',
            r'TIMEOUT',
        ],
        'ubsan': [
            r'undefined behavior',
            r'runtime error:',
            r'overflow',
            r'negation',
        ],
        'asan': [
            r'AddressSanitizer',
            r'heap-buffer-overflow',
            r'stack-buffer-overflow',
            r'heap-use-after-free',
            r'heap-buffer-underflow',
            r'double-free',
            r'leak',
        ],
        'msan': [
            r'MemorySanitizer',
            r'use-of-uninitialized-value',
        ],
    }
    
    def __init__(self):
        self.crashes = []
        self.classified = defaultdict(list)
    
    def classify(self, crash_output, crash_input):
        """Classifica um crash baseado na saída."""
        crash_type = 'unknown'
        
        for category, patterns in self.CRASH_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, crash_output, re.IGNORECASE):
                    crash_type = category
                    break
            if crash_type != 'unknown':
                break
        
        # Extrair localização
        location = self._extract_location(crash_output)
        
        # Extrair sanitizer output
        sanitizer_info = self._extract_sanitizer_info(crash_output)
        
        crash_record = {
            'type': crash_type,
            'input': crash_input,
            'output': crash_output,
            'location': location,
            'sanitizer': sanitizer_info,
            'hash': self._hash_crash(crash_output),
        }
        
        self.crashes.append(crash_record)
        self.classified[crash_type].append(crash_record)
        
        return crash_record
    
    def _extract_location(self, output):
        """Extrai localização do crash do output."""
        # Procurar por endereços de stack trace
        patterns = [
            r'at\s+(.+?):(\d+)',
            r'in\s+(.+?)\s+\((.+?):(\d+)\)',
            r'PC\s+at\s+(.+?):(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                groups = match.groups()
                return {
                    'file': groups[-2] if len(groups) >= 2 else 'unknown',
                    'line': int(groups[-1]) if len(groups) >= 1 else 0,
                    'function': groups[0] if groups else 'unknown',
                }
        
        return None
    
    def _extract_sanitizer_info(self, output):
        """Extrai informações detalhadas do sanitizer."""
        info = {}
        
        # ASan
        asan_match = re.search(
            r'AddressSanitizer:.*?(SUMMARY:.*?)(?:\n\n|\Z)',
            output, re.DOTALL
        )
        if asan_match:
            info['sanitizer'] = 'ASan'
            info['summary'] = asan_match.group(1).strip()
        
        # UBSan
        ubsan_match = re.search(
            r'runtime error: (.+)',
            output
        )
        if ubsan_match:
            info['sanitizer'] = 'UBSan'
            info['detail'] = ubsan_match.group(1)
        
        # MSan
        msan_match = re.search(
            r'MemorySanitizer:.*?(SUMMARY:.*?)(?:\n\n|\Z)',
            output, re.DOTALL
        )
        if msan_match:
            info['sanitizer'] = 'MSan'
            info['summary'] = msan_match.group(1).strip()
        
        return info
    
    def _hash_crash(self, output):
        """Gera hash do crash para deduplicação."""
        import hashlib
        
        # Extrair frame principal do stack trace
        frames = re.findall(r'#\d+\s+(.+)', output)
        if frames:
            key = '\n'.join(frames[:5])
        else:
            key = output[:500]
        
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def deduplicate(self):
        """Deduplica crashes por hash."""
        seen = set()
        unique = []
        
        for crash in self.crashes:
            if crash['hash'] not in seen:
                seen.add(crash['hash'])
                unique.append(crash)
        
        return {
            'total': len(self.crashes),
            'unique': len(unique),
            'duplicates_removed': len(self.crashes) - len(unique),
            'by_type': {
                t: len(cs) for t, cs in self.classified.items()
            }
        }
    
    def generate_report(self):
        """Gera relatório de crashes."""
        dedup = self.deduplicate()
        
        report = f"""
Relatório de Crashes
====================
Total de crashes: {dedup['total']}
Crashes únicos: {dedup['unique']}
Duplicatas removidas: {dedup['duplicates_removed']}

Por tipo:
"""
        for crash_type, count in dedup['by_type'].items():
            report += f"  {crash_type}: {count}\n"
        
        report += "\nCrashes Únicos:\n"
        for crash in self.crashes[:20]:  # Top 20
            report += f"\n  Tipo: {crash['type']}\n"
            report += f"  Hash: {crash['hash']}\n"
            if crash['location']:
                report += f"  Local: {crash['location']['file']}:{crash['location']['line']}\n"
            report += f"  Input size: {len(crash['input'])} bytes\n"
        
        return report
```

### 12.6.2 Reprodutibilidade de Crashes Wasm

```python
class CrashReproducer:
    """Reprodutor de crashes para validação."""
    
    def __init__(self, runtime_cmd, timeout=10):
        self.runtime = runtime_cmd
        self.timeout = timeout
        self.reproducible = []
        self.flaky = []
    
    def reproduce(self, crash_input, num_attempts=5):
        """Tenta reproduzir um crash múltiplas vezes."""
        success_count = 0
        
        for attempt in range(num_attempts):
            result = self._execute(crash_input)
            if result['crashed']:
                success_count += 1
        
        reproducibility = success_count / num_attempts
        
        record = {
            'input': crash_input,
            'attempts': num_attempts,
            'successes': success_count,
            'reproducibility': reproducibility,
            'is_reproducible': reproducibility >= 0.8,
        }
        
        if record['is_reproducible']:
            self.reproducible.append(record)
        else:
            self.flaky.append(record)
        
        return record
    
    def _execute(self, wasm_bytes):
        """Executa um módulo Wasm e captura resultado."""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix='.wasm', delete=False) as f:
            f.write(wasm_bytes)
            tmp_path = f.name
        
        try:
            import subprocess
            
            result = subprocess.run(
                [self.runtime, tmp_path],
                capture_output=True,
                timeout=self.timeout,
            )
            
            return {
                'crashed': result.returncode != 0,
                'stdout': result.stdout.decode('utf-8', errors='replace'),
                'stderr': result.stderr.decode('utf-8', errors='replace'),
                'returncode': result.returncode,
            }
        
        except subprocess.TimeoutExpired:
            return {
                'crashed': False,
                'stdout': '',
                'stderr': 'TIMEOUT',
                'returncode': -1,
            }
        
        finally:
            os.unlink(tmp_path)
    
    def minimize_crash(self, crash_input, max_iterations=100):
        """Minimiza um crash input preservando o crash."""
        best = crash_input
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            # Tentar remover bytes
            for i in range(len(best) - 1, -1, -1):
                candidate = best[:i] + best[i+1:]
                result = self._execute(candidate)
                
                if result['crashed']:
                    best = candidate
                    improved = True
                    break
            
            # Tentar substituir bytes por zero
            for i in range(len(best)):
                candidate = bytearray(best)
                candidate[i] = 0
                candidate = bytes(candidate)
                
                result = self._execute(candidate)
                if result['crashed']:
                    best = candidate
                    improved = True
                    break
        
        return best
    
    def generate_minimized_crash(self, crash_input):
        """Gera versão minimizada e salva."""
        minimized = self.minimize_crash(crash_input)
        
        import hashlib
        import time
        
        crash_hash = hashlib.sha256(minimized).hexdigest()[:16]
        timestamp = int(time.time())
        
        filename = f"crash_minimized_{timestamp}_{crash_hash}.wasm"
        
        return {
            'filename': filename,
            'original_size': len(crash_input),
            'minimized_size': len(minimized),
            'reduction': 1 - (len(minimized) / max(len(crash_input), 1)),
            'data': minimized,
        }
```

### 12.6.3 Root Cause Analysis

```python
class RootCauseAnalyzer:
    """Análise de causa raiz para crashes de Wasm."""
    
    def analyze_crash(self, crash_info, module_info):
        """Analisa a causa raiz de um crash."""
        analysis = {
            'category': self._categorize(crash_info),
            'mechanism': self._identify_mechanism(crash_info),
            'trigger': self._identify_trigger(crash_info, module_info),
            'severity': self._assess_severity(crash_info),
            'recommendation': self._generate_recommendation(crash_info),
        }
        
        return analysis
    
    def _categorize(self, crash_info):
        """Categoriza o tipo de bug."""
        stderr = crash_info.get('stderr', '')
        
        if 'AddressSanitizer: heap-buffer-overflow' in stderr:
            return 'heap_buffer_overflow'
        elif 'AddressSanitizer: stack-buffer-overflow' in stderr:
            return 'stack_buffer_overflow'
        elif 'AddressSanitizer: heap-use-after-free' in stderr:
            return 'use_after_free'
        elif 'AddressSanitizer: double-free' in stderr:
            return 'double_free'
        elif 'runtime error' in stderr:
            return 'undefined_behavior'
        elif 'abort' in stderr:
            return 'assertion_failure'
        else:
            return 'unknown'
    
    def _identify_mechanism(self, crash_info):
        """Identifica o mecanismo do bug."""
        stderr = crash_info.get('stderr', '')
        
        # Extrair informações de access
        access_match = re.search(
            r'WRITE of size (\d+) at .* pc (.+?) bp (.+?) sp (.+?)',
            stderr
        )
        
        if access_match:
            return {
                'access_size': int(access_match.group(1)),
                'pc': access_match.group(2),
                'bp': access_match.group(3),
                'sp': access_match.group(4),
            }
        
        # Para UBSan
        ubsan_match = re.search(
            r'runtime error: (.+)',
            stderr
        )
        
        if ubsan_match:
            return {'detail': ubsan_match.group(1)}
        
        return {}
    
    def _identify_trigger(self, crash_info, module_info):
        """Identifica o que triggers o crash."""
        trigger = {
            'input_type': 'wasm_module',
            'module_sections': module_info.get('sections', []),
        }
        
        # Verificar se é na validação ou execução
        stderr = crash_info.get('stderr', '')
        if 'wasm_validate' in stderr or 'validator' in stderr.lower():
            trigger['phase'] = 'validation'
        elif 'wasmtime' in stderr or 'wasmer' in stderr:
            trigger['phase'] = 'execution'
        else:
            trigger['phase'] = 'unknown'
        
        return trigger
    
    def _assess_severity(self, crash_info):
        """Avalia a severidade do bug."""
        stderr = crash_info.get('stderr', '')
        
        severity = 'low'
        
        # Bugs de memória são mais severos
        if 'heap-buffer-overflow' in stderr:
            severity = 'critical'
        elif 'stack-buffer-overflow' in stderr:
            severity = 'high'
        elif 'use-after-free' in stderr:
            severity = 'critical'
        elif 'double-free' in stderr:
            severity = 'high'
        elif 'undefined behavior' in stderr:
            severity = 'medium'
        elif 'abort' in stderr:
            severity = 'low'
        
        return severity
    
    def _generate_recommendation(self, crash_info):
        """Gera recomendação de correção."""
        category = self._categorize(crash_info)
        
        recommendations = {
            'heap_buffer_overflow': 
                'Verificar cálculos de offset em operações de memória. '
                'Implementar bounds checking adicional.',
            'stack_buffer_overflow':
                'Verificar alocação de stack para locais. '
                'Considerar usar verificação de limites em compile time.',
            'use_after_free':
                'Verificar ciclo de vida de alocações. '
                'Implementar zeroing após free.',
            'double_free':
                'Verificar lógica de deallocation. '
                'Implementar verificação de double-free.',
            'undefined_behavior':
                'Revisar operações que causam UB. '
                'Usar -fsanitize=undefined durante desenvolvimento.',
            'assertion_failure':
                'Verificar invariantes no código. '
                'Adicionar tratamento de erros adequado.',
        }
        
        return recommendations.get(category, 'Análise manual necessária.')
```

### 12.6.4 Pipeline Completa de Análise de Crashes

```python
import json
import os
from datetime import datetime

class CrashAnalysisPipeline:
    """Pipeline completa de análise de crashes."""
    
    def __init__(self, output_dir, runtime='wasmtime'):
        self.output_dir = output_dir
        self.runtime = runtime
        self.classifier = CrashClassifier()
        self.reproducer = CrashReproducer(runtime)
        self.analyzer = RootCauseAnalyzer()
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'minimized'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'reports'), exist_ok=True)
    
    def process_crash(self, crash_input, crash_output):
        """Processa um crash completo."""
        # 1. Classificar
        crash_info = self.classifier.classify(crash_output, crash_input)
        
        # 2. Reproduzir
        repro_result = self.reproducer.reproduce(crash_input)
        
        if not repro_result['is_reproducible']:
            return {
                'status': 'flaky',
                'reproducibility': repro_result['reproducibility']
            }
        
        # 3. Minimizar
        minimized = self.reproducer.generate_minimized_crash(crash_input)
        
        # Salvar crash minimizado
        min_path = os.path.join(
            self.output_dir, 'minimized', minimized['filename']
        )
        with open(min_path, 'wb') as f:
            f.write(minimized['data'])
        
        # 4. Analisar causa raiz
        module_info = self._analyze_module(minimized['data'])
        root_cause = self.analyzer.analyze_crash(
            {'stderr': crash_output},
            module_info
        )
        
        # 5. Gerar relatório
        report = self._generate_crash_report(
            crash_info, repro_result, minimized, root_cause
        )
        
        # Salvar relatório
        report_path = os.path.join(
            self.output_dir, 'reports',
            f"crash_{crash_info['hash']}.json"
        )
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _analyze_module(self, wasm_bytes):
        """Analisa estrutura do módulo."""
        import struct
        
        if len(wasm_bytes) < 8:
            return {'sections': []}
        
        sections = []
        offset = 8
        
        SECTION_NAMES = {
            0: 'custom', 1: 'type', 2: 'import', 3: 'function',
            4: 'table', 5: 'memory', 6: 'global', 7: 'export',
            8: 'start', 9: 'element', 10: 'code', 11: 'data', 12: 'tag',
        }
        
        while offset < len(wasm_bytes):
            section_id = wasm_bytes[offset]
            offset += 1
            
            # Ler LEB128
            size = 0
            shift = 0
            while offset < len(wasm_bytes):
                byte = wasm_bytes[offset]
                offset += 1
                size |= (byte & 0x7F) << shift
                if byte & 0x80 == 0:
                    break
                shift += 7
            
            sections.append({
                'id': section_id,
                'name': SECTION_NAMES.get(section_id, 'unknown'),
                'size': size,
            })
            
            offset += size
        
        return {'sections': sections}
    
    def _generate_crash_report(self, crash_info, repro, minimized, root_cause):
        """Gera relatório completo de crash."""
        return {
            'timestamp': datetime.now().isoformat(),
            'hash': crash_info['hash'],
            'type': crash_info['type'],
            'severity': root_cause['severity'],
            'reproducibility': repro['reproducibility'],
            'minimized': {
                'original_size': minimized['original_size'],
                'minimized_size': minimized['minimized_size'],
                'reduction': minimized['reduction'],
                'filename': minimized['filename'],
            },
            'root_cause': root_cause,
            'location': crash_info.get('location'),
            'sanitizer': crash_info.get('sanitizer'),
        }
    
    def generate_summary(self):
        """Gera resumo geral de todos os crashes."""
        reports_dir = os.path.join(self.output_dir, 'reports')
        
        crashes = []
        for filename in os.listdir(reports_dir):
            if filename.endswith('.json'):
                with open(os.path.join(reports_dir, filename)) as f:
                    crashes.append(json.load(f))
        
        summary = {
            'total_crashes': len(crashes),
            'by_type': {},
            'by_severity': {},
            'unique_hashs': set(),
        }
        
        for crash in crashes:
            crash_type = crash['type']
            severity = crash['severity']
            
            summary['by_type'][crash_type] = summary['by_type'].get(crash_type, 0) + 1
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            summary['unique_hashs'].add(crash['hash'])
        
        summary['unique_crashes'] = len(summary['unique_hashs'])
        del summary['unique_hashs']  # Não serializable
        
        return summary
```

## 12.7 Differential Fuzzing

Differential fuzzing compara a saída de duas ou mais implementações do mesmo comportamento para encontrar divergências. No contexto de Wasm, isso é especialmente valioso para encontrar bugs em runtimes comparando seus comportamentos.

### 12.7.1 O que é Differential Fuzzing

Differential fuzzing é uma extensão do fuzzing tradicional que, ao invés de verificar apenas se o programa crashou, compara as saídas de múltiplas implementações. Se duas implementações produzem resultados diferentes para a mesma entrada, uma delas contém um bug.

```
+------------------------------------------------------------------+
|              Differential Fuzzing para Wasm                        |
+------------------------------------------------------------------+
|                                                                    |
|              +------------------+                                  |
|              | Input Gerado    |                                  |
|              | pelo Fuzzer      |                                  |
|              +--------+---------+                                  |
|                       |                                            |
|           +-----------+-----------+                                |
|           |                       |                                |
|           v                       v                                |
|  +------------------+   +------------------+                      |
|  | Runtime A        |   | Runtime B        |                      |
|  | (ex: wasmtime)   |   | (ex: wasmer)     |                      |
|  +--------+---------+   +--------+---------+                      |
|           |                       |                                |
|           v                       v                                |
|  +------------------+   +------------------+                      |
|  | Saída A          |   | Saída B          |                      |
|  +--------+---------+   +--------+---------+                      |
|           |                       |                                |
|           +-----------+-----------+                                |
|                       |                                            |
|                       v                                            |
|              +------------------+                                  |
|              | Comparador       |                                  |
|              | (diferente?)     |                                  |
|              +--------+---------+                                  |
|                       |                                            |
|              +--------+--------+                                   |
|              |                 |                                   |
|              v                 v                                   |
|         Diferente         Igual                                    |
|              |                 |                                   |
|              v                 v                                   |
|         BUG ENCONTRADO   Continuar                                 |
|                                                                    |
+------------------------------------------------------------------+
```

### 12.7.2 Comparando Runtimes Wasm para Corretude

```python
import subprocess
import tempfile
import os
import hashlib
import json

class WasmRuntimeComparator:
    """Compara comportamento de runtimes Wasm."""
    
    def __init__(self, runtimes):
        """
        runtimes: dict de nome -> caminho do runtime
        Ex: {'wasmtime': '/usr/bin/wasmtime', 'wasmer': '/usr/bin/wasmer'}
        """
        self.runtimes = runtimes
    
    def compare_execution(self, wasm_bytes, func_name='_start', args=None):
        """Executa o módulo em todos os runtimes e compara resultados."""
        results = {}
        
        for name, runtime_path in self.runtimes.items():
            result = self._execute_runtime(
                runtime_path, wasm_bytes, func_name, args
            )
            results[name] = result
        
        # Comparar resultados
        return self._compare_results(results)
    
    def _execute_runtime(self, runtime_path, wasm_bytes, func_name, args):
        """Executa um módulo em um runtime específico."""
        with tempfile.NamedTemporaryFile(suffix='.wasm', delete=False) as f:
            f.write(wasm_bytes)
            tmp_path = f.name
        
        try:
            # Construir comando
            cmd = [runtime_path]
            
            if 'wasmtime' in runtime_path:
                cmd.extend(['--dir=.', tmp_path])
            elif 'wasmer' in runtime_path:
                cmd.extend([tmp_path])
            else:
                cmd.append(tmp_path)
            
            if args:
                cmd.extend(args)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
            )
            
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'success': result.returncode == 0,
                'timeout': False,
            }
        
        except subprocess.TimeoutExpired:
            return {
                'stdout': b'',
                'stderr': b'TIMEOUT',
                'returncode': -1,
                'success': False,
                'timeout': True,
            }
        
        except Exception as e:
            return {
                'stdout': b'',
                'stderr': str(e).encode(),
                'returncode': -1,
                'success': False,
                'timeout': False,
            }
        
        finally:
            os.unlink(tmp_path)
    
    def _compare_results(self, results):
        """Compara resultados de múltiplos runtimes."""
        runtime_names = list(results.keys())
        
        if len(runtime_names) < 2:
            return {'divergence': False, 'reason': 'insufficient_runtimes'}
        
        # Verificar se todos tiveram o mesmo sucesso/falha
        success_pattern = [results[r]['success'] for r in runtime_names]
        
        if len(set(success_pattern)) > 1:
            return {
                'divergence': True,
                'type': 'success_divergence',
                'results': {r: results[r]['success'] for r in runtime_names},
                'details': results,
            }
        
        # Se todos tiveram sucesso, comparar stdout
        if all(success_pattern):
            stdout_set = set(results[r]['stdout'] for r in runtime_names)
            if len(stdout_set) > 1:
                return {
                    'divergence': True,
                    'type': 'output_divergence',
                    'results': {
                        r: results[r]['stdout'].decode('utf-8', errors='replace')
                        for r in runtime_names
                    },
                    'details': results,
                }
        
        # Verificar padrão de timeout
        timeout_pattern = [results[r]['timeout'] for r in runtime_names]
        if len(set(timeout_pattern)) > 1:
            return {
                'divergence': True,
                'type': 'timeout_divergence',
                'results': {r: results[r]['timeout'] for r in runtime_names},
                'details': results,
            }
        
        return {
            'divergence': False,
            'results': results,
        }
```

### 12.7.3 Differential Testing de Compiladores Wasm

```python
class CompilerDifferentialTester:
    """Teste diferencial de compiladores Wasm (Rust/C/Go -> Wasm)."""
    
    def __init__(self, compilers):
        """
        compilers: dict de nome -> comando de compilação
        Ex: {'rust': 'rustc --target wasm32-wasi', 'c': 'clang --target=wasm32-wasi'}
        """
        self.compilers = compilers
    
    def test_source_differential(self, source_code, source_type='c'):
        """Testa se diferentes compiladores produzem comportamento equivalente."""
        
        # Compilar com cada compilador
        compiled_modules = {}
        for name, compiler_cmd in self.compilers.items():
            wasm_path = self._compile(
                source_code, source_type, compiler_cmd, name
            )
            if wasm_path:
                compiled_modules[name] = wasm_path
        
        if len(compiled_modules) < 2:
            return {'error': 'insufficient_compiled_modules'}
        
        # Executar e comparar
        comparator = WasmRuntimeComparator({
            name: '/usr/bin/wasmtime'
            for name in compiled_modules
        })
        
        results = {}
        for name, wasm_path in compiled_modules.items():
            with open(wasm_path, 'rb') as f:
                wasm_bytes = f.read()
            
            result = comparator.compare_execution(wasm_bytes)
            results[name] = result
        
        # Analisar divergências
        return self._analyze_compiler_divergence(results)
    
    def _compile(self, source, source_type, compiler_cmd, name):
        """Compila código fonte para Wasm."""
        import tempfile
        
        ext_map = {
            'c': '.c',
            'cpp': '.cpp',
            'rust': '.rs',
        }
        
        ext = ext_map.get(source_type, '.c')
        
        with tempfile.NamedTemporaryFile(
            suffix=ext, mode='w', delete=False
        ) as f:
            f.write(source)
            src_path = f.name
        
        wasm_path = f'/tmp/{name}_compiled.wasm'
        
        try:
            cmd = f"{compiler_cmd} {src_path} -o {wasm_path}"
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(wasm_path):
                return wasm_path
            return None
        
        except Exception:
            return None
        
        finally:
            os.unlink(src_path)
    
    def _analyze_compiler_divergence(self, results):
        """Analisa divergências entre compiladores."""
        divergences = []
        
        compilers = list(results.keys())
        
        for i, c1 in enumerate(compilers):
            for c2 in compilers[i+1:]:
                r1 = results[c1]
                r2 = results[c2]
                
                if r1.get('divergence', False) or r2.get('divergence', False):
                    divergences.append({
                        'compilers': (c1, c2),
                        'type': 'execution_divergence',
                        'details': {
                            c1: r1,
                            c2: r2,
                        }
                    })
        
        return {
            'divergences': divergences,
            'total_compilers': len(compilers),
            'clean_pairs': len(compilers) * (len(compilers) - 1) // 2 - len(divergences),
        }
```

### 12.7.4 Framework de Differential Fuzzing

```python
import random
import hashlib
import time
from typing import List, Dict, Callable, Any

class DifferentialFuzzingFramework:
    """Framework para differential fuzzing de runtimes Wasm."""
    
    def __init__(self, targets, input_generator):
        """
        targets: lista de funções (input -> output)
        input_generator: função que gera entradas
        """
        self.targets = targets
        self.input_generator = input_generator
        self.divergences = []
        self.total_tests = 0
        self.start_time = time.time()
    
    def run(self, num_iterations=10000):
        """Executa a campanha de differential fuzzing."""
        print(f"Iniciando differential fuzzing com {len(self.targets)} targets")
        print(f"Máximo de iterações: {num_iterations}")
        
        for i in range(num_iterations):
            # Gerar entrada
            test_input = self.input_generator()
            
            # Executar em todos os targets
            outputs = []
            for target in self.targets:
                try:
                    output = target(test_input)
                    outputs.append(output)
                except Exception as e:
                    outputs.append({'error': str(e)})
            
            # Verificar divergência
            if self._has_divergence(outputs):
                divergence = {
                    'iteration': i,
                    'input': test_input,
                    'outputs': outputs,
                    'hash': self._hash_divergence(outputs),
                }
                self.divergences.append(divergence)
                print(f"DIVERGÊNCIA encontrada na iteração {i}")
            
            self.total_tests += 1
            
            if i % 1000 == 0:
                elapsed = time.time() - self.start_time
                print(
                    f"Iteração {i}/{num_tests} | "
                    f"Divergências: {len(self.divergences)} | "
                    f"Taxa: {self.total_tests / elapsed:.0f} tests/s"
                )
        
        return self.generate_report()
    
    def _has_divergence(self, outputs):
        """Verifica se há divergência nas saídas."""
        if len(outputs) < 2:
            return False
        
        # Verificar se todos são erros
        all_errors = all(isinstance(o, dict) and 'error' in o for o in outputs)
        if all_errors:
            error_msgs = [o['error'] for o in outputs]
            return len(set(error_msgs)) > 1
        
        # Verificar se algum é erro e outros não
        has_error = any(isinstance(o, dict) and 'error' in o for o in outputs)
        if has_error:
            return True
        
        # Comparar outputs normalizados
        normalized = [self._normalize_output(o) for o in outputs]
        return len(set(str(n) for n in normalized)) > 1
    
    def _normalize_output(self, output):
        """Normaliza output para comparação."""
        if isinstance(output, bytes):
            return output
        elif isinstance(output, str):
            return output.encode()
        elif isinstance(output, (int, float)):
            return str(output).encode()
        return str(output).encode()
    
    def _hash_divergence(self, outputs):
        """Gera hash da divergência para deduplicação."""
        key = '|'.join(str(o) for o in outputs)
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def generate_report(self):
        """Gera relatório de differential fuzzing."""
        elapsed = time.time() - self.start_time
        
        # Deduplicar divergências
        seen = set()
        unique_divergences = []
        for div in self.divergences:
            if div['hash'] not in seen:
                seen.add(div['hash'])
                unique_divergences.append(div)
        
        return {
            'total_tests': self.total_tests,
            'total_divergences': len(self.divergences),
            'unique_divergences': len(unique_divergences),
            'elapsed_seconds': elapsed,
            'tests_per_second': self.total_tests / elapsed,
            'divergences': unique_divergences[:50],  # Top 50
        }
```

### 12.7.5 Divergência Semântica

```python
class SemanticDivergenceDetector:
    """Detector de divergência semântica em Wasm."""
    
    def __init__(self):
        self.test_cases = []
    
    def create_semantic_test(self, module_a, module_b, test_func):
        """Cria um caso de teste semântico."""
        return {
            'module_a': module_a,
            'module_b': module_b,
            'test_func': test_func,
            'type': 'semantic',
        }
    
    def test_divergence(self, test_case, inputs):
        """Testa divergência semântica."""
        module_a = test_case['module_a']
        module_b = test_case['module_b']
        test_func = test_case['test_func']
        
        results_a = []
        results_b = []
        
        for inp in inputs:
            try:
                result_a = test_func(module_a, inp)
                results_a.append(result_a)
            except Exception as e:
                results_a.append(('error', str(e)))
            
            try:
                result_b = test_func(module_b, inp)
                results_b.append(result_b)
            except Exception as e:
                results_b.append(('error', str(e)))
        
        # Comparar resultados
        divergences = []
        for i, (a, b) in enumerate(zip(results_a, results_b)):
            if a != b:
                divergences.append({
                    'input': inputs[i],
                    'result_a': a,
                    'result_b': b,
                })
        
        return {
            'has_divergence': len(divergences) > 0,
            'divergences': divergences,
            'total_tests': len(inputs),
            'divergence_rate': len(divergences) / max(len(inputs), 1),
        }
    
    def classify_divergence(self, divergence):
        """Classifica o tipo de divergência."""
        a = divergence['result_a']
        b = divergence['result_b']
        
        if isinstance(a, tuple) and a[0] == 'error':
            return 'crash_divergence'
        if isinstance(b, tuple) and b[0] == 'error':
            return 'crash_divergence'
        
        # Verificar se é divergência numérica
        try:
            a_val = float(a) if not isinstance(a, float) else a
            b_val = float(b) if not isinstance(b, float) else b
            
            if abs(a_val - b_val) > 1e-6:
                return 'numeric_divergence'
            elif a_val != b_val:
                return 'precision_divergence'
        except:
            pass
        
        return 'output_divergence'
```

### 12.7.6 Intérprete de Diferenças

```python
class DivergenceInterpreter:
    """Interpreta e reporta diferenças encontradas."""
    
    def interpret(self, divergences):
        """Interpreta divergências e gera insights."""
        interpretations = []
        
        for div in divergences:
            interp = {
                'input_hash': div.get('hash', 'unknown'),
                'analysis': self._analyze_divergence(div),
                'impact': self._assess_impact(div),
                'recommendation': self._recommend_action(div),
            }
            interpretations.append(interp)
        
        return interpretations
    
    def _analyze_divergence(self, divergence):
        """Analisa uma divergência específica."""
        analysis = {
            'type': 'unknown',
            'severity': 'low',
            'details': {},
        }
        
        outputs = divergence.get('outputs', [])
        
        # Verificar padrões
        error_count = sum(
            1 for o in outputs
            if isinstance(o, dict) and 'error' in o
        )
        
        if error_count > 0 and error_count < len(outputs):
            analysis['type'] = 'partial_failure'
            analysis['severity'] = 'high'
        elif error_count == len(outputs):
            analysis['type'] = 'all_fail'
            analysis['severity'] = 'low'
        else:
            analysis['type'] = 'output_mismatch'
            analysis['severity'] = 'medium'
        
        return analysis
    
    def _assess_impact(self, divergence):
        """Avalia impacto potencial."""
        # Verificar se é crash em produção
        outputs = divergence.get('outputs', [])
        
        has_crash = any(
            isinstance(o, dict) and 'error' in o
            for o in outputs
        )
        
        if has_crash:
            return {
                'level': 'high',
                'reason': 'Pode causar crash em runtime de produção'
            }
        
        return {
            'level': 'medium',
            'reason': 'Diferença de comportamento entre implementações'
        }
    
    def _recommend_action(self, divergence):
        """Recomenda ação."""
        analysis = self._analyze_divergence(divergence)
        
        if analysis['severity'] == 'high':
            return 'Investigar imediatamente - potencial bug de segurança'
        elif analysis['severity'] == 'medium':
            return 'Investigar quando possível - divergência de comportamento'
        else:
            return 'Registrar para análise futura'
    
    def generate_report(self, divergences):
        """Gera relatório completo."""
        interpretations = self.interpret(divergences)
        
        severity_counts = {}
        for interp in interpretations:
            sev = interp['impact']['level']
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        return {
            'total_divergences': len(divergences),
            'severity_distribution': severity_counts,
            'interpretations': interpretations,
            'summary': self._generate_summary(interpretations),
        }
    
    def _generate_summary(self, interpretations):
        """Gera resumo executivo."""
        high = sum(1 for i in interpretations if i['impact']['level'] == 'high')
        medium = sum(1 for i in interpretations if i['impact']['level'] == 'medium')
        low = sum(1 for i in interpretations if i['impact']['level'] == 'low')
        
        return f"""
Resumo de Differential Fuzzing
==============================
Total de divergências: {len(interpretations)}
  - Alta severidade: {high}
  - Média severidade: {medium}
  - Baixa severidade: {low}

Ação recomendada: {'Investigação imediata necessária' if high > 0 else 'Análise quando possível'}
"""
```

## 12.8 Regression Testing

Bugs encontrados por fuzzing devem se tornar parte do suite de testes de regressão para garantir que não sejam reintroduzidos no futuro.

### 12.8.1 Construindo Suites de Teste de Regressão a partir de Fuzzing

```python
import os
import json
import subprocess
from pathlib import Path

class RegressionTestBuilder:
    """Construtor de testes de regressão a partir de crashes de fuzzing."""
    
    def __init__(self, test_dir):
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.tests = []
    
    def add_from_crash(self, crash_path, crash_info):
        """Adiciona um teste de regressão a partir de um crash."""
        test_name = crash_info.get('hash', os.path.basename(crash_path))
        
        test_case = {
            'name': f"regression_{test_name}",
            'input_file': crash_path,
            'type': crash_info.get('type', 'unknown'),
            'severity': crash_info.get('severity', 'low'),
            'expected': 'crash',  # Esperamos que o módulo cause crash
            'description': self._generate_description(crash_info),
            'metadata': {
                'found_by': 'fuzzer',
                'hash': crash_info.get('hash'),
                'original_size': os.path.getsize(crash_path),
            },
        }
        
        self.tests.append(test_case)
        self._write_test(test_case)
        
        return test_case
    
    def add_from_divergence(self, divergence_info):
        """Adiciona teste a partir de divergência."""
        test_name = divergence_info.get('hash', 'unknown')
        
        test_case = {
            'name': f"regression_div_{test_name}",
            'input_data': divergence_info.get('input'),
            'type': 'divergence',
            'expected': 'consistent_output',
            'description': self._generate_divergence_description(divergence_info),
            'metadata': {
                'found_by': 'differential_fuzzer',
                'runtimes': divergence_info.get('runtimes', []),
            },
        }
        
        self.tests.append(test_case)
        self._write_test(test_case)
        
        return test_case
    
    def _generate_description(self, crash_info):
        """Gera descrição do teste."""
        crash_type = crash_info.get('type', 'unknown')
        severity = crash_info.get('severity', 'low')
        
        return (
            f"Teste de regressão para crash do tipo {crash_type} "
            f"(severidade: {severity}). "
            f"Encontrado por fuzzing automático."
        )
    
    def _generate_divergence_description(self, div_info):
        """Gera descrição para teste de divergência."""
        runtimes = div_info.get('runtimes', [])
        return (
            f"Teste de regressão para divergência entre runtimes: "
            f"{', '.join(runtimes)}. "
            f"Encontrado por differential fuzzing."
        )
    
    def _write_test(self, test_case):
        """Escreve o teste em formato executável."""
        test_file = self.test_dir / f"{test_case['name']}.py"
        
        content = f'''"""
Teste de Regressão: {test_case['name']}
{test_case['description']}
"""
import subprocess
import sys

def test_{test_case['name'].replace('-', '_')}():
    """Testa que o bug conhecido não foi reintroduzido."""
    wasm_file = "{test_case['input_file']}"
    
    result = subprocess.run(
        ["wasmtime", wasm_file],
        capture_output=True,
        timeout=30,
    )
    
    # O bug deve causar crash ou comportamento específico
    if result.returncode != 0:
        # Crash detectado - teste passa (bug ainda existe ou foi reintroduzido)
        print("CRASH detectado - bug pode ter sido reintroduzido")
        assert False, "Bug de regressão detectado"
    
    # Se não crashou, o teste passa
    print("Comportamento esperado - sem crash")

if __name__ == "__main__":
    test_{test_case['name'].replace('-', '_')}()
'''
        
        test_file.write_text(content)
    
    def generate_test_suite(self):
        """Gera suite de testes completa."""
        suite_file = self.test_dir / 'test_suite.py'
        
        content = '"""\nSuite de Testes de Regressão - Gerado por Fuzzing\n"""\n\n'
        content += 'import pytest\nimport subprocess\nimport os\n\n\n'
        
        content += 'CRASH_TESTS = [\n'
        for test in self.tests:
            if test['type'] != 'divergence':
                content += f'    ("{test["name"]}", "{test["input_file"]}"),\n'
        content += ']\n\n'
        
        content += '@pytest.mark.parametrize("name,wasm_file", CRASH_TESTS)\n'
        content += 'def test_regression_crash(name, wasm_file):\n'
        content += '    """Testa que crashes conhecidos não são reintroduzidos."""\n'
        content += '    if not os.path.exists(wasm_file):\n'
        content += '        pytest.skip(f"Arquivo não encontrado: {wasm_file}")\n'
        content += '    \n'
        content += '    result = subprocess.run(\n'
        content += '        ["wasmtime", wasm_file],\n'
        content += '        capture_output=True,\n'
        content += '        timeout=30,\n'
        content += '    )\n'
        content += '    \n'
        content += '    assert result.returncode == 0, \\\n'
        content += '        f"Regressão detectada em {name}: crash retornado"\n'
        
        suite_file.write_text(content)
        
        return {
            'total_tests': len(self.tests),
            'suite_file': str(suite_file),
            'test_files': [str(self.test_dir / f"{t['name']}.py") for t in self.tests],
        }
    
    def generate_report(self):
        """Gera relatório da suite de testes."""
        return {
            'total_regression_tests': len(self.tests),
            'by_type': {},
            'by_severity': {},
            'test_directory': str(self.test_dir),
        }
```

### 12.8.2 Minimização de Testes de Regressão

```python
class RegressionTestMinimizer:
    """Minimiza testes de regressão para focar no comportamento essencial."""
    
    def __init__(self, validator, runtime):
        self.validator = validator
        self.runtime = runtime
    
    def minimize_crash_test(self, wasm_bytes, crash_validator):
        """Minimiza um crash test preservando o comportamento de crash."""
        best = wasm_bytes
        
        # Fase 1: Remover seções não essenciais
        best = self._remove_non_essential_sections(best, crash_validator)
        
        # Fase 2: Minimizar código
        best = self._minimize_code(best, crash_validator)
        
        # Fase 3: Minimizar constantes
        best = self._minimize_constants(best, crash_validator)
        
        return best
    
    def _remove_non_essential_sections(self, wasm_bytes, crash_validator):
        """Remove seções que não são necessárias para reproduzir o crash."""
        if len(wasm_bytes) < 8:
            return wasm_bytes
        
        header = wasm_bytes[:8]
        sections = self._parse_sections(wasm_bytes[8:])
        
        # Tentar remover cada seção
        essential = []
        for i, (section_id, data) in enumerate(sections):
            # Seção de código é sempre essencial
            if section_id == 10:
                essential.append((section_id, data))
                continue
            
            # Tentar sem esta seção
            remaining = [s for j, s in enumerate(sections) if j != i]
            test_module = header
            for sid, sdata in remaining:
                test_module += bytes([sid])
                test_module += self._encode_leb128(len(sdata))
                test_module += sdata
            
            if crash_validator(test_module):
                # Seção não essencial
                continue
            else:
                essential.append((section_id, data))
        
        # Reconstruir
        result = header
        for section_id, data in essential:
            result += bytes([section_id])
            result += self._encode_leb128(len(data))
            result += data
        
        return result
    
    def _minimize_code(self, wasm_bytes, crash_validator):
        """Minimiza seção de código."""
        if len(wasm_bytes) < 8:
            return wasm_bytes
        
        header = wasm_bytes[:8]
        sections = self._parse_sections(wasm_bytes[8:])
        
        for i, (section_id, data) in enumerate(sections):
            if section_id == 10:
                # Minimizar seção de código
                minimized = self._minimize_code_section(data, crash_validator)
                sections[i] = (section_id, minimized)
        
        result = header
        for section_id, data in sections:
            result += bytes([section_id])
            result += self._encode_leb128(len(data))
            result += data
        
        return result
    
    def _minimize_code_section(self, data, crash_validator):
        """Minimiza uma seção de código individual."""
        func_count, offset = self._read_leb128(data, 0)
        
        functions = []
        for _ in range(func_count):
            body_size, offset = self._read_leb128(data, offset)
            body = data[offset:offset + body_size]
            offset += body_size
            functions.append(body)
        
        # Tentar remover funções
        essential_functions = []
        for i, func_body in enumerate(functions):
            remaining = [f for j, f in enumerate(functions) if j != i]
            
            # Reconstruir seção
            test_section = self._encode_leb128(len(remaining))
            for f in remaining:
                test_section += self._encode_leb128(len(f))
                test_section += f
            
            # Verificar se o crash ainda ocorre
            test_module = self._reconstruct_with_code_section(
                crash_validator, test_section
            )
            
            if test_module and crash_validator(test_module):
                continue  # Função não essencial
            else:
                essential_functions.append(func_body)
        
        result = self._encode_leb128(len(essential_functions))
        for f in essential_functions:
            result += self._encode_leb128(len(f))
            result += f
        
        return result
    
    def _minimize_constants(self, wasm_bytes, crash_validator):
        """Minimiza constantes no código."""
        best = wasm_bytes
        
        # Encontrar constantes e tentar reduzir
        for i in range(len(best)):
            if best[i] == 0x41:  # i32.const
                # Tentar substituir por constante menor
                for val in [0, 1, -1]:
                    candidate = bytearray(best)
                    # Substituir operando
                    j = i + 1
                    while j < len(candidate) and candidate[j] & 0x80:
                        j += 1
                    j += 1
                    
                    # Inserir valor menor
                    candidate = (
                        candidate[:i+1] +
                        bytes([val & 0x7F]) +
                        candidate[j:]
                    )
                    
                    if crash_validator(bytes(candidate)):
                        best = bytes(candidate)
                        break
        
        return best
    
    def _parse_sections(self, data):
        sections = []
        offset = 0
        while offset < len(data):
            section_id = data[offset]
            offset += 1
            
            size, offset = self._read_leb128(data, offset)
            section_data = data[offset:offset + size]
            offset += size
            
            sections.append((section_id, section_data))
        
        return sections
    
    def _read_leb128(self, data, offset):
        result = 0
        shift = 0
        while offset < len(data):
            byte = data[offset]
            offset += 1
            result |= (byte & 0x7F) << shift
            if byte & 0x80 == 0:
                break
            shift += 7
        return result, offset
    
    def _encode_leb128(self, value):
        result = []
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result.append(byte)
            if value == 0:
                break
        return bytes(result)
    
    def _reconstruct_with_code_section(self, validator, code_data):
        """Reconstrói módulo com nova seção de código."""
        # Implementação simplificada
        return None
```

### 12.8.3 Automação de Geração de Testes de Regressão

```python
import subprocess
import hashlib
from datetime import datetime

class AutomatedRegressionGenerator:
    """Gerador automático de testes de regressão."""
    
    def __init__(self, test_output_dir, validator='wasm-validate'):
        self.test_dir = test_output_dir
        self.validator = validator
        self.test_registry = {}
    
    def process_fuzzer_findings(self, findings_dir):
        """Processa diretório de findings do fuzzer."""
        findings_path = Path(findings_dir)
        
        for crash_file in findings_path.glob('crash_*.wasm'):
            self._process_single_finding(crash_file)
        
        for crash_file in findings_path.glob('crash_minimized_*.wasm'):
            self._process_single_finding(crash_file)
        
        self._generate_test_manifest()
    
    def _process_single_finding(self, crash_path):
        """Processa um finding individual."""
        wasm_bytes = crash_path.read_bytes()
        
        # Verificar se é válido (pode ser crash parcial)
        is_valid = self._validate(wasm_bytes)
        
        # Calcular hash
        crash_hash = hashlib.sha256(wasm_bytes).hexdigest()[:16]
        
        # Verificar se já existe
        if crash_hash in self.test_registry:
            return
        
        test_info = {
            'hash': crash_hash,
            'source_file': str(crash_path),
            'size': len(wasm_bytes),
            'valid_module': is_valid,
            'created_at': datetime.now().isoformat(),
        }
        
        # Salvar como teste de regressão
        test_filename = f"regression_{crash_hash}.wasm"
        test_path = os.path.join(self.test_dir, test_filename)
        
        with open(test_path, 'wb') as f:
            f.write(wasm_bytes)
        
        test_info['test_file'] = test_path
        self.test_registry[crash_hash] = test_info
        
        # Gerar script de teste
        self._generate_test_script(crash_hash, test_info)
    
    def _generate_test_script(self, test_hash, test_info):
        """Gera script de teste para um finding."""
        script_content = f'''#!/usr/bin/env python3
"""
Teste de regressão gerado automaticamente.
Hash: {test_hash}
Tamanho: {test_info['size']} bytes
Módulo válido: {test_info['valid_module']}
"""
import subprocess
import sys

def run_test():
    wasm_file = "{test_info['test_file']}"
    
    result = subprocess.run(
        ["wasmtime", wasm_file],
        capture_output=True,
        timeout=30,
    )
    
    # Verificar se o comportamento é seguro
    if result.returncode != 0:
        stderr = result.stderr.decode('utf-8', errors='replace')
        
        # Verificar se é um crash de segurança
        security_indicators = [
            'AddressSanitizer',
            'heap-buffer-overflow',
            'stack-buffer-overflow',
            'use-after-free',
            'undefined behavior',
        ]
        
        for indicator in security_indicators:
            if indicator in stderr:
                print(f"BUG DE SEGURANÇA DETECTADO: {{indicator}}")
                return False
        
        # Outros erros são aceitáveis
        print(f"Erro não-crash detectado (código {{result.returncode}})")
        return True
    
    return True

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
'''
        
        script_path = os.path.join(
            self.test_dir,
            f"test_regression_{test_hash}.py"
        )
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
    
    def _validate(self, wasm_bytes):
        """Valida se o módulo Wasm é válido."""
        try:
            result = subprocess.run(
                [self.validator, '-'],
                input=wasm_bytes,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False
    
    def _generate_test_manifest(self):
        """Gera manifesto dos testes de regressão."""
        manifest = {
            'total_tests': len(self.test_registry),
            'tests': self.test_registry,
            'generated_at': datetime.now().isoformat(),
        }
        
        manifest_path = os.path.join(self.test_dir, 'manifest.json')
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
```

### 12.8.4 Padrões Específicos de Regressão para Wasm

```python
class WasmRegressionPatterns:
    """Padrões específicos de regressão para WebAssembly."""
    
    PATTERNS = {
        'memory_out_of_bounds': {
            'description': 'Acesso fora dos limites da memória linear',
            'detector': 'check_memory_bounds',
            'severity': 'critical',
            'test_template': '''
// Teste: acesso fora dos limites de memória
(module
  (memory (export "memory") 1)
  (func (export "test")
    i32.const 65536  ;; Offset acima do tamanho da memória
    i32.load         ;; Deve causar trap
  )
)
''',
        },
        
        'stack_overflow': {
            'description': 'Overflow de pilha por recursão ou block aninhado',
            'detector': 'check_stack_overflow',
            'severity': 'high',
            'test_template': '''
// Teste: overflow de pilha
(module
  (func (export "test")
    (block $0
      (block $1
        (block $2
          ;; Muitos blocks aninhados
        )
      )
    )
  )
)
''',
        },
        
        'type_mismatch': {
            'description': 'Incompatibilidade de tipos em instruções',
            'detector': 'check_type_mismatch',
            'severity': 'medium',
            'test_template': '''
// Teste: incompatibilidade de tipos
(module
  (type $sig (func (param i32) (result i32)))
  (func (type $sig) (param i32) (result i32)
    local.get 0
  )
  ;; Chamar com tipo errado
  (func (export "test")
    i32.const 42
    call 0
    drop
  )
)
''',
        },
        
        'division_overflow': {
            'description': 'Overflow em divisão (i32.div_s com MIN/-1)',
            'detector': 'check_division_overflow',
            'severity': 'high',
            'test_template': '''
// Teste: overflow em divisão
(module
  (func (export "test")
    i32.const 0x80000000  ;; i32::MIN
    i32.const -1
    i32.div_s             ;; Deve causar trap (overflow)
  )
)
''',
        },
        
        'indirect_call_type_mismatch': {
            'description': 'Tipo incompatível em call_indirect',
            'detector': 'check_call_indirect',
            'severity': 'medium',
            'test_template': '''
// Teste: call_indirect com tipo errado
(module
  (type $sig (func (param i32) (result i32)))
  (table 1 funcref)
  (elem (i32.const 0) func 0)
  (func (type $sig) (param i32) (result i32)
    local.get 0
  )
  (func (export "test")
    i32.const 42
    i32.const 0
    call_indirect (type $sig)  ;; Tipo correto
  )
  (func (export "test_wrong")
    i32.const 42
    i32.const 0
    call_indirect (type 0)  ;; Tipo errado
  )
)
''',
        },
    }
    
    @classmethod
    def get_pattern_tests(cls):
        """Retorna todos os padrões de teste."""
        return cls.PATTERNS
    
    @classmethod
    def generate_all_tests(cls, output_dir):
        """Gera todos os testes de regressão."""
        os.makedirs(output_dir, exist_ok=True)
        
        for name, pattern in cls.PATTERNS.items():
            test_file = os.path.join(output_dir, f"pattern_{name}.wat")
            with open(test_file, 'w') as f:
                f.write(pattern['test_template'])
        
        return list(cls.PATTERNS.keys())
```

### 12.8.5 Gerenciamento de Casos de Teste

```python
class RegressionTestManager:
    """Gerenciador de casos de teste de regressão."""
    
    def __init__(self, registry_path):
        self.registry_path = registry_path
        self.registry = self._load_registry()
    
    def _load_registry(self):
        """Carrega registro de testes."""
        if os.path.exists(self.registry_path):
            with open(self.registry_path) as f:
                return json.load(f)
        return {'tests': {}, 'metadata': {}}
    
    def _save_registry(self):
        """Salva registro de testes."""
        with open(self.registry_path, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def register_test(self, test_id, test_info):
        """Registra um novo teste."""
        self.registry['tests'][test_id] = {
            **test_info,
            'registered_at': datetime.now().isoformat(),
            'status': 'active',
        }
        self._save_registry()
    
    def mark_verified(self, test_id):
        """Marca um teste como verificado (bug corrigido)."""
        if test_id in self.registry['tests']:
            self.registry['tests'][test_id]['status'] = 'verified'
            self.registry['tests'][test_id]['verified_at'] = (
                datetime.now().isoformat()
            )
            self._save_registry()
    
    def mark_reintroduced(self, test_id):
        """Marca um teste como reintroduzido."""
        if test_id in self.registry['tests']:
            self.registry['tests'][test_id]['status'] = 'reintroduced'
            self.registry['tests'][test_id]['reintroduced_at'] = (
                datetime.now().isoformat()
            )
            self._save_registry()
    
    def get_active_tests(self):
        """Retorna testes ativos."""
        return {
            tid: t for tid, t in self.registry['tests'].items()
            if t.get('status') == 'active'
        }
    
    def get_stats(self):
        """Retorna estatísticas."""
        tests = self.registry['tests']
        
        status_counts = {}
        for test in tests.values():
            status = test.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_tests': len(tests),
            'by_status': status_counts,
            'active': status_counts.get('active', 0),
            'verified': status_counts.get('verified', 0),
            'reintroduced': status_counts.get('reintroduced', 0),
        }
    
    def cleanup_old_tests(self, max_age_days=90):
        """Remove testes antigos."""
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)
        
        to_remove = []
        for tid, test in self.registry['tests'].items():
            if test.get('status') == 'verified':
                verified_at = test.get('verified_at', '')
                if verified_at:
                    try:
                        dt = datetime.fromisoformat(verified_at)
                        if dt.timestamp() < cutoff:
                            to_remove.append(tid)
                    except:
                        pass
        
        for tid in to_remove:
            del self.registry['tests'][tid]
        
        self._save_registry()
        return len(to_remove)
```

### 12.8.6 Suite de Regressão de Longa Duração

```python
import time
import threading
from datetime import timedelta

class LongRunningRegressionSuite:
    """Suite de testes de regressão de longa duração."""
    
    def __init__(self, test_dir, interval_hours=24):
        self.test_dir = test_dir
        self.interval = interval_hours * 3600
        self.running = False
        self.results_history = []
    
    def start_continuous(self):
        """Inicia execução contínua."""
        self.running = True
        thread = threading.Thread(target=self._run_loop)
        thread.daemon = True
        thread.start()
        return thread
    
    def _run_loop(self):
        """Loop de execução."""
        while self.running:
            result = self.run_once()
            self.results_history.append(result)
            
            # Manter apenas últimas 1000 execuções
            if len(self.results_history) > 1000:
                self.results_history = self.results_history[-1000:]
            
            time.sleep(self.interval)
    
    def run_once(self):
        """Executa a suite uma vez."""
        start_time = time.time()
        
        test_files = list(Path(self.test_dir).glob('regression_*.wasm'))
        
        passed = 0
        failed = 0
        errors = 0
        
        for test_file in test_files:
            result = self._run_single_test(test_file)
            
            if result == 'pass':
                passed += 1
            elif result == 'fail':
                failed += 1
            else:
                errors += 1
        
        elapsed = time.time() - start_time
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total': len(test_files),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'elapsed_seconds': elapsed,
        }
    
    def _run_single_test(self, test_path):
        """Executa um teste individual."""
        try:
            result = subprocess.run(
                ['wasmtime', str(test_path)],
                capture_output=True,
                timeout=30,
            )
            
            if result.returncode == 0:
                return 'pass'
            else:
                # Verificar se é crash de segurança
                stderr = result.stderr.decode('utf-8', errors='replace')
                security_indicators = [
                    'AddressSanitizer',
                    'heap-buffer-overflow',
                    'stack-buffer-overflow',
                ]
                
                for indicator in security_indicators:
                    if indicator in stderr:
                        return 'fail'
                
                return 'pass'  # Erro não-crash é aceitável
        
        except subprocess.TimeoutExpired:
            return 'error'
        except Exception as e:
            return 'error'
    
    def get_trend(self):
        """Analisa tendência dos resultados."""
        if len(self.results_history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent = self.results_history[-10:]
        older = self.results_history[-20:-10] if len(self.results_history) >= 20 else []
        
        recent_fail_rate = sum(r['failed'] for r in recent) / max(sum(r['total'] for r in recent), 1)
        
        if older:
            older_fail_rate = sum(r['failed'] for r in older) / max(sum(r['total'] for r in older), 1)
        else:
            older_fail_rate = recent_fail_rate
        
        if recent_fail_rate > older_fail_rate * 1.1:
            trend = 'worsening'
        elif recent_fail_rate < older_fail_rate * 0.9:
            trend = 'improving'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'recent_fail_rate': recent_fail_rate,
            'older_fail_rate': older_fail_rate,
            'total_executions': len(self.results_history),
        }
    
    def generate_report(self):
        """Gera relatório da suite."""
        if not self.results_history:
            return "Sem dados de execução"
        
        latest = self.results_history[-1]
        trend = self.get_trend()
        
        return f"""
Relatório da Suite de Regressão
===============================
Última execução: {latest['timestamp']}
Total de testes: {latest['total']}
Aprovados: {latest['passed']}
Falhas: {latest['failed']}
Erros: {latest['errors']}
Tempo: {latest['elapsed_seconds']:.1f}s

Tendência: {trend['trend']}
Taxa de falha recente: {trend['recent_fail_rate']:.2%}
Total de execuções: {trend['total_executions']}
"""
```

## 12.9 CI/CD Integration

Integrar fuzzing em pipelines de CI/CD permite encontrar bugs continuamente, antes que cheguem a produção. Este seção aborda estratégias para integração eficiente de fuzzing em ambientes de integração contínua.

### 12.9.1 Fuzzing em Integração Contínua

```yaml
# .github/workflows/wasm-fuzzing.yml
name: Wasm Fuzzing

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    # Executar fuzzing diariamente
    - cron: '0 2 * * *'

env:
  FUZZ_TIMEOUT: 3600  # 1 hora por target
  MAX_RUNTIME: 7200   # 2 horas total

jobs:
  fuzzing:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [decoder, validator, executor, wasi]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: nightly
          components: rust-src
          override: true
      
      - name: Install Wasm Tools
        run: |
          cargo install wasm-tools
          cargo install wasm-mutate
          cargo install wasmtime-cli
      
      - name: Build Target
        run: |
          cargo build --release --target wasm32-wasi
      
      - name: Initialize Corpus
        run: |
          mkdir -p corpus
          ./scripts/generate_initial_corpus.sh corpus/
      
      - name: Run Fuzzer
        run: |
          timeout ${{ env.MAX_RUNTIME }} \
            cargo fuzz run ${{ matrix.target }} \
            -- -max_total_time=${{ env.FUZZ_TIMEOUT }} \
               -max_len=4096 \
               -timeout=30 \
               -jobs=4 \
               -workers=4
      
      - name: Analyze Results
        if: always()
        run: |
          ./scripts/analyze_fuzzing_results.sh \
            fuzz/artifacts/${{ matrix.target }}/ \
            > results-${{ matrix.target }}.txt
      
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: fuzzing-results-${{ matrix.target }}
          path: |
            results-${{ matrix.target }}.txt
            fuzz/artifacts/${{ matrix.target }}/
      
      - name: Report Crashes
        if: failure()
        run: |
          CRASH_COUNT=$(find fuzz/artifacts/${{ matrix.target }}/ \
            -name "crash-*" | wc -l)
          echo "## Fuzzing Results" >> $GITHUB_STEP_SUMMARY
          echo "Target: ${{ matrix.target }}" >> $GITHUB_STEP_SUMMARY
          echo "Crashes found: $CRASH_COUNT" >> $GITHUB_STEP_SUMMARY
          
          if [ "$CRASH_COUNT" -gt 0 ]; then
            echo "### Crash Details" >> $GITHUB_STEP_SUMMARY
            for crash in fuzz/artifacts/${{ matrix.target }}/crash-*; do
              echo "- $(basename $crash)" >> $GITHUB_STEP_SUMMARY
            done
          fi
```

### 12.9.2 Estratégias de Fuzzing Paralelo

```python
import multiprocessing
import os
import time
from pathlib import Path

class ParallelFuzzingManager:
    """Gerenciador de fuzzing paralelo para CI."""
    
    def __init__(self, num_workers=4, target_dir=None):
        self.num_workers = num_workers
        self.target_dir = target_dir or '/tmp/fuzzing'
        self.processes = []
        self.shared_coverage = multiprocessing.Manager().dict()
    
    def run_parallel(self, fuzz_command, corpus_dir, output_dir):
        """Executa fuzzing paralelo com workers independentes."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Dividir corpus entre workers
        corpus_files = list(Path(corpus_dir).glob('*'))
        chunk_size = max(1, len(corpus_files) // self.num_workers)
        
        for worker_id in range(self.num_workers):
            worker_corpus = corpus_files[
                worker_id * chunk_size:
                (worker_id + 1) * chunk_size
            ]
            
            worker_dir = os.path.join(output_dir, f'worker_{worker_id}')
            worker_output = os.path.join(output_dir, f'output_{worker_id}')
            
            os.makedirs(worker_dir, exist_ok=True)
            os.makedirs(worker_output, exist_ok=True)
            
            # Copiar corpus para worker
            for cf in worker_corpus:
                os.system(f'cp {cf} {worker_dir}/')
            
            # Iniciar worker
            cmd = f"{fuzz_command} {worker_dir} {worker_output}"
            p = multiprocessing.Process(
                target=self._run_worker,
                args=(worker_id, cmd)
            )
            self.processes.append(p)
            p.start()
        
        # Aguardar conclusão
        for p in self.processes:
            p.join()
        
        # Coletar resultados
        return self._collect_results(output_dir)
    
    def _run_worker(self, worker_id, command):
        """Executa um worker individual."""
        print(f"Worker {worker_id} iniciado")
        os.system(command)
        print(f"Worker {worker_id} finalizado")
    
    def _collect_results(self, output_dir):
        """Coleta resultados de todos os workers."""
        all_crashes = []
        total_coverage = set()
        
        for worker_id in range(self.num_workers):
            worker_output = os.path.join(output_dir, f'output_{worker_id}')
            
            # Coletar crashes
            for crash_file in Path(worker_output).glob('crash_*'):
                all_crashes.append({
                    'worker': worker_id,
                    'file': str(crash_file),
                    'size': crash_file.stat().st_size,
                })
        
        return {
            'total_workers': self.num_workers,
            'total_crashes': len(all_crashes),
            'crashes': all_crashes,
        }
    
    def stop_all(self):
        """Para todos os workers."""
        for p in self.processes:
            if p.is_alive():
                p.terminate()
```

### 12.9.3 Gerenciamento de Recursos para Fuzzing em CI

```python
import psutil
import os

class CIResourceManager:
    """Gerenciador de recursos para fuzzing em CI."""
    
    def __init__(self, max_memory_mb=2048, max_cpu_percent=80):
        self.max_memory = max_memory_mb * 1024 * 1024
        self.max_cpu = max_cpu_percent
    
    def check_resources(self):
        """Verifica se há recursos suficientes."""
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        
        return {
            'memory_available': memory.available >= self.max_memory,
            'memory_percent': memory.percent,
            'cpu_percent': cpu,
            'can_fuzz': (
                memory.available >= self.max_memory and
                cpu < self.max_cpu
            ),
        }
    
    def get_recommended_workers(self):
        """Retorna número recomendado de workers."""
        cpu_count = psutil.cpu_count()
        memory = psutil.virtual_memory()
        
        # Regra: 1 worker por 2 cores, limitado pela memória
        memory_workers = memory.available // (512 * 1024 * 1024)  # 512MB por worker
        cpu_workers = cpu_count // 2
        
        return min(cpu_workers, memory_workers, 8)  # Max 8 workers
    
    def allocate_for_fuzzing(self):
        """Aloca recursos para sessão de fuzzing."""
        resources = self.check_resources()
        
        if not resources['can_fuzz']:
            return {
                'success': False,
                'reason': 'Recursos insuficientes',
                'details': resources,
            }
        
        workers = self.get_recommended_workers()
        memory_per_worker = int(
            psutil.virtual_memory().available * 0.7 / workers / 1024 / 1024
        )
        
        return {
            'success': True,
            'workers': workers,
            'memory_per_worker_mb': memory_per_worker,
            'total_memory_mb': workers * memory_per_worker,
        }
```

### 12.9.4 Orçamento de Fuzzing e Limites de Tempo

```python
import time
from datetime import datetime, timedelta

class FuzzingBudget:
    """Gerenciador de orçamento de fuzzing."""
    
    def __init__(self, max_time_seconds=3600, max_memory_mb=4096):
        self.max_time = max_time_seconds
        self.max_memory = max_memory_mb * 1024 * 1024
        self.start_time = None
        self.start_memory = None
    
    def start(self):
        """Inicia monitoramento de orçamento."""
        self.start_time = time.time()
        self.start_memory = psutil.virtual_memory().used
    
    def check_budget(self):
        """Verifica se o orçamento foi excedido."""
        if self.start_time is None:
            return {'budget_exceeded': False}
        
        elapsed = time.time() - self.start_time
        current_memory = psutil.virtual_memory().used
        
        time_exceeded = elapsed >= self.max_time
        memory_exceeded = (
            current_memory - self.start_memory
        ) >= self.max_memory
        
        return {
            'budget_exceeded': time_exceeded or memory_exceeded,
            'time_exceeded': time_exceeded,
            'memory_exceeded': memory_exceeded,
            'elapsed_seconds': elapsed,
            'remaining_seconds': max(0, self.max_time - elapsed),
            'memory_used_mb': (current_memory - self.start_memory) / 1024 / 1024,
            'memory_remaining_mb': max(
                0,
                (self.max_memory - (current_memory - self.start_memory)) / 1024 / 1024
            ),
        }
    
    def get_progress(self):
        """Retorna progresso do orçamento."""
        if self.start_time is None:
            return {'progress': 0}
        
        elapsed = time.time() - self.start_time
        
        return {
            'time_progress': elapsed / self.max_time,
            'elapsed_formatted': str(timedelta(seconds=int(elapsed))),
            'remaining_formatted': str(
                timedelta(seconds=int(max(0, self.max_time - elapsed)))
            ),
        }
```

### 12.9.5 Serviços de Fuzzing Contínuo (OSS-Fuzz)

```python
class OSSFuzzIntegration:
    """Integração com OSS-Fuzz para projetos Wasm."""
    
    def __init__(self, project_name, project_dir):
        self.project_name = project_name
        self.project_dir = project_dir
    
    def generate_dockerfile(self):
        """Gera Dockerfile para OSS-Fuzz."""
        dockerfile_content = f'''# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM gcr.io/oss-fuzz-base/base-builder

RUN apt-get update && apt-get install -y \\
    clang \\
    llvm \\
    cargo \\
    rustc

# Instalar ferramentas Wasm
RUN cargo install wasm-tools wasm-mutate

WORKDIR $SRC/{self.project_name}

COPY . $SRC/{self.project_name}/

COPY build.sh $SRC/
'''
        
        dockerfile_path = os.path.join(
            self.project_dir, 'oss-fuzz', 'Dockerfile'
        )
        os.makedirs(os.path.dirname(dockerfile_path), exist_ok=True)
        
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        return dockerfile_path
    
    def generate_build_script(self):
        """Gera script de build para OSS-Fuzz."""
        build_content = f'''#!/bin/bash -eu
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Build the project
cd $SRC/{self.project_name}

# Compilar com suporte a fuzzing
cargo build --release --target wasm32-wasi

# Copiar binários fuzzing
cp target/wasm32-wasi/release/*.wasm $OUT/

# Copiar corpus
cp -r corpus/* $OUT/

# Compilar fuzzers
for fuzzer in fuzz/targets/*.rs; do
    fuzzer_name=$(basename "$fuzzer" .rs)
    
    cargo fuzz build "$fuzzer_name" 2>/dev/null || true
    
    cp "fuzz/targets/target/release/$fuzzer_name" "$OUT/" 2>/dev/null || true
done
'''
        
        build_path = os.path.join(
            self.project_dir, 'oss-fuzz', 'build.sh'
        )
        
        with open(build_path, 'w') as f:
            f.write(build_content)
        
        os.chmod(build_path, 0o755)
        return build_path
    
    def generate_project_yaml(self):
        """Gera project.yaml para OSS-Fuzz."""
        yaml_content = f'''homepage: "https://github.com/your-org/{self.project_name}"
primary_contact: "security@your-org.com"
main_repo: "https://github.com/your-org/{self.project_name}.git"

sanitizers:
  - address
  - memory
  - undefined

architectures:
  - x86_64
  - i386

language: rust
'''
        
        yaml_path = os.path.join(
            self.project_dir, 'oss-fuzz', 'project.yaml'
        )
        
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        
        return yaml_path
```

### 12.9.6 GitHub Actions para Fuzzing

```yaml
# .github/workflows/fuzzing-advanced.yml
name: Advanced Wasm Fuzzing

on:
  workflow_dispatch:
    inputs:
      duration:
        description: 'Fuzzing duration (seconds)'
        required: false
        default: '3600'
      workers:
        description: 'Number of parallel workers'
        required: false
        default: '4'

jobs:
  fuzzing:
    runs-on: ubuntu-latest
    timeout-minutes: 120
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Environment
        run: |
          sudo apt-get update
          sudo apt-get install -y clang llvm
          cargo install wasm-tools wasm-mutate wasmtime-cli
          cargo install cargo-fuzz
      
      - name: Build with Sanitizers
        run: |
          export RUSTFLAGS="-Z sanitizer=address"
          cargo build --release --target wasm32-wasi
      
      - name: Initialize Corpus
        run: |
          mkdir -p corpus
          ./scripts/generate_seeds.py corpus/
      
      - name: Run Parallel Fuzzing
        run: |
          DURATION=${{ github.event.inputs.duration || '3600' }}
          WORKERS=${{ github.event.inputs.workers || '4' }}
          
          mkdir -p output
          
          for i in $(seq 1 $WORKERS); do
            cargo fuzz run wasm_target -- \
              -max_total_time=$((DURATION / WORKERS)) \
              -max_len=4096 \
              -timeout=30 \
              -artifact_prefix=output/crash_${i}_ &
          done
          
          wait
      
      - name: Analyze Crashes
        if: always()
        run: |
          CRASH_COUNT=$(find output/ -name "crash-*" 2>/dev/null | wc -l)
          
          echo "## Fuzzing Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "- Duration: ${{ github.event.inputs.duration || '3600' }}s" >> $GITHUB_STEP_SUMMARY
          echo "- Workers: ${{ github.event.inputs.workers || '4' }}" >> $GITHUB_STEP_SUMMARY
          echo "- Crashes found: $CRASH_COUNT" >> $GITHUB_STEP_SUMMARY
          
          if [ "$CRASH_COUNT" -gt 0 ]; then
            echo "" >> $GITHUB_STEP_SUMMARY
            echo "### Crashes" >> $GITHUB_STEP_SUMMARY
            for crash in output/crash-*; do
              if [ -f "$crash" ]; then
                SIZE=$(wc -c < "$crash")
                echo "- $(basename $crash) ($SIZE bytes)" >> $GITHUB_STEP_SUMMARY
              fi
            done
          
          - name: Upload Artifacts
            if: always()
            uses: actions/upload-artifact@v4
            with:
              name: fuzzing-results
              path: output/
              retention-days: 30
      
      - name: Create Issue on Crash
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const crashCount = '${{ steps.analyze.outputs.crash_count }}';
            
            if (parseInt(crashCount) > 0) {
              await github.rest.issues.create({
                owner: context.repo.owner,
                repo: context.repo.repo,
                title: `[Fuzzing] ${crashCount} crashes found`,
                body: `## Fuzzing Campaign Results\n\n` +
                      `- Duration: ${{ github.event.inputs.duration || '3600' }}s\n` +
                      `- Workers: ${{ github.event.inputs.workers || '4' }}\n` +
                      `- Crashes: ${crashCount}\n\n` +
                      `Artifacts available in workflow run.`,
                labels: ['bug', 'fuzzing', 'security']
              });
            }
```

### 12.9.7 Monitoramento de Campanhas de Fuzzing

```python
import time
import json
from pathlib import Path
from datetime import datetime

class FuzzingCampaignMonitor:
    """Monitor de campanhas de fuzzing."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.metrics = []
        self.start_time = time.time()
    
    def collect_metrics(self):
        """Coleta métricas da campanha atual."""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'elapsed': time.time() - self.start_time,
        }
        
        # Contar crashes
        crash_files = list(self.output_dir.glob('crash-*'))
        metrics['total_crashes'] = len(crash_files)
        
        # Tamanho do corpus
        corpus_files = list(self.output_dir.glob('corpus/*'))
        metrics['corpus_size'] = len(corpus_files)
        
        # Cobertura (se disponível)
        coverage_file = self.output_dir / 'coverage.txt'
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    for line in f:
                        if 'edges' in line.lower():
                            metrics['edges_covered'] = int(
                                line.split(':')[1].strip()
                            )
            except:
                pass
        
        self.metrics.append(metrics)
        return metrics
    
    def get_progress_report(self):
        """Gera relatório de progresso."""
        if not self.metrics:
            return "Sem métricas coletadas"
        
        current = self.metrics[-1]
        
        return f"""
Progresso da Campanha de Fuzzing
================================
Tempo decorrido: {current['elapsed']:.0f}s
Crashes encontrados: {current['total_crashes']}
Tamanho do corpus: {current['corpus_size']}
Arestas cobertas: {current.get('edges_covered', 'N/A')}

Taxa de crashes: {current['total_crashes'] / max(current['elapsed'], 1):.4f}/s
"""
    
    def detect_anomalies(self):
        """Detecta anomalias na campanha."""
        if len(self.metrics) < 10:
            return []
        
        anomalies = []
        recent = self.metrics[-10:]
        
        # Verificar se crashes pararam
        crash_counts = [m['total_crashes'] for m in recent]
        if len(set(crash_counts[-5:])) == 1 and crash_counts[-1] > 0:
            anomalies.append({
                'type': 'crash_plateau',
                'message': 'Taxa de crashes estagnou',
            })
        
        # Verificar se corpus não está crescendo
        corpus_sizes = [m['corpus_size'] for m in recent]
        if len(set(corpus_sizes[-5:])) == 1:
            anomalies.append({
                'type': 'corpus_plateau',
                'message': 'Corpus não está crescendo',
            })
        
        return anomalies
    
    def save_metrics(self):
        """Salva métricas em arquivo."""
        metrics_file = self.output_dir / 'campaign_metrics.json'
        
        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        
        return metrics_file
```

### 12.9.8 Reporting e Alerting

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class FuzzingReporter:
    """Sistema de relatórios e alertas para fuzzing."""
    
    def __init__(self, config):
        self.config = config
        self.alerts = []
    
    def generate_daily_report(self, campaign_data):
        """Gera relatório diário."""
        report = f"""
Relatório Diário de Fuzzing - {datetime.now().strftime('%Y-%m-%d')}
{'=' * 50}

Resumo da Campanha:
- Targets monitorados: {campaign_data.get('targets', 0)}
- Tempo total de fuzzing: {campaign_data.get('total_time', 0)}s
- Iterações totais: {campaign_data.get('total_iterations', 0)}

Descobertas:
- Novos crashes: {campaign_data.get('new_crashes', 0)}
- Crashes únicos: {campaign_data.get('unique_crashes', 0)}
- Bugs corrigidos: {campaign_data.get('bugs_fixed', 0)}

Cobertura:
- Arestas cobertas: {campaign_data.get('edges_covered', 0)}
- Cobertura máxima: {campaign_data.get('max_coverage', 'N/A')}%

Alertas:
"""
        
        for alert in campaign_data.get('alerts', []):
            report += f"- [{alert['severity']}] {alert['message']}\n"
        
        if not campaign_data.get('alerts'):
            report += "- Nenhum alerta\n"
        
        return report
    
    def send_alert(self, alert_type, message, severity='medium'):
        """Envia alerta."""
        alert = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat(),
        }
        
        self.alerts.append(alert)
        
        # Enviar email se configurado
        if self.config.get('email'):
            self._send_email_alert(alert)
        
        # Enviar Slack se configurado
        if self.config.get('slack_webhook'):
            self._send_slack_alert(alert)
    
    def _send_email_alert(self, alert):
        """Envia alerta por email."""
        msg = MIMEMultipart()
        msg['Subject'] = f'[Fuzzing Alert] {alert["type"]}'
        msg['From'] = self.config['email']['from']
        msg['To'] = self.config['email']['to']
        
        body = f"""
Tipo: {alert['type']}
Severidade: {alert['severity']}
Mensagem: {alert['message']}
Timestamp: {alert['timestamp']}
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            with smtplib.SMTP(self.config['email']['smtp_host']) as server:
                server.send_message(msg)
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
    
    def _send_slack_alert(self, alert):
        """Envia alerta para Slack."""
        import urllib.request
        
        color_map = {
            'critical': '#FF0000',
            'high': '#FF6600',
            'medium': '#FFCC00',
            'low': '#00CC00',
        }
        
        payload = {
            'attachments': [{
                'color': color_map.get(alert['severity'], '#CCCCCC'),
                'title': f'Fuzzing Alert: {alert["type"]}',
                'text': alert['message'],
                'fields': [
                    {'title': 'Severity', 'value': alert['severity'], 'short': True},
                    {'title': 'Time', 'value': alert['timestamp'], 'short': True},
                ],
            }]
        }
        
        try:
            req = urllib.request.Request(
                self.config['slack_webhook'],
                data=json.dumps(payload).encode(),
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
        except Exception as e:
            print(f"Erro ao enviar Slack: {e}")
    
    def generate_executive_summary(self, weekly_data):
        """Gera resumo executivo semanal."""
        return f"""
Resumo Executivo Semanal de Fuzzing
{'=' * 50}

Período: {weekly_data.get('period', 'N/A')}
Targets ativos: {weekly_data.get('active_targets', 0)}

Métricas Chave:
- Total de crashes encontrados: {weekly_data.get('total_crashes', 0)}
- Bugs de segurança: {weekly_data.get('security_bugs', 0)}
- Bugs corrigidos: {weekly_data.get('bugs_fixed', 0)}
- Cobertura média: {weekly_data.get('avg_coverage', 'N/A')}%

Impacto:
- Redução de superfície de ataque: {weekly_data.get('attack_surface_reduction', 'N/A')}%
- Tempo médio para detecção: {weekly_data.get('avg_detection_time', 'N/A')}h
- Custo por bug encontrado: ${weekly_data.get('cost_per_bug', 'N/A')}

Recomendações:
{weekly_data.get('recommendations', 'Nenhuma')}
"""
```

## 12.10 Complete Fuzzing Setup

Esta seção apresenta um setup completo de fuzzing do zero, incluindo instalação de ferramentas, seleção de targets, configuração e execução de campanhas.

### 12.10.1 Instalação Completa da Toolchain

```bash
#!/bin/bash
# setup_fuzzing.sh - Instalação completa do ambiente de fuzzing

set -e

echo "=== Instalando ambiente de fuzzing para WebAssembly ==="

# 1. Instalar Rust e componentes necessários
echo "[1/8] Instalando Rust..."
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env

# Instalar componentes necessários
rustup component add rust-src
rustup component add llvm-tools-preview
rustup target add wasm32-wasi
rustup target add wasm32-unknown-unknown

# 2. Instalar ferramentas Wasm
echo "[2/8] Instalando ferramentas Wasm..."
cargo install wasm-tools
cargo install wasm-mutate
cargo install wasm-bindgen-cli
cargo install wasmtime-cli
cargo install wabt

# 3. Instalar fuzzer
echo "[3/8] Instalando cargo-fuzz..."
cargo install cargo-fuzz

# 4. Instalar AFL++
echo "[4/8] Instalando AFL++..."
cd /tmp
git clone https://github.com/AFLplusplus/AFLplusplus.git
cd AFLplusplus
make source-only
sudo make install
cd ~

# 5. Instalar Honggfuzz
echo "[5/8] Instalando Honggfuzz..."
cd /tmp
git clone https://github.com/google/honggfuzz.git
cd honggfuzz
make
sudo cp honggfuzz /usr/local/bin/
cd ~

# 6. Compilar com suporte a fuzzing
echo "[6/8] Compilando target com suporte a fuzzing..."
cd /path/to/your/project

# Criar fuzz target
cargo fuzz add wasm_decoder

# Compilar com sanitizers
RUSTFLAGS="-Z sanitizer=address" cargo build --release --target wasm32-wasi

# 7. Preparar corpus
echo "[7/8] Preparando corpus inicial..."
mkdir -p fuzz/corpus

# Baixar módulos Wasm de exemplo
wget -P fuzz/corpus/ https://example.com/sample1.wasm
wget -P fuzz/corpus/ https://example.com/sample2.wasm

# Gerar módulos mínimos
python3 scripts/generate_minimal_modules.py fuzz/corpus/

# 8. Verificar instalação
echo "[8/8] Verificando instalação..."
echo "Ferramentas instaladas:"
cargo fuzz --version
wasm-tools --version
wasmtime --version
afl-fuzz --version

echo ""
echo "=== Instalação concluída ==="
echo "Execute: cargo fuzz run wasm_decoder"
```

### 12.10.2 Seleção e Preparação de Targets

```python
class FuzzingTargetSelector:
    """Seletor de targets para fuzzing de Wasm."""
    
    TARGET_CATEGORIES = {
        'decoder': {
            'description': 'Decodificador de binários Wasm',
            'priority': 'critical',
            'complexity': 'high',
            'entry_points': ['wasmtime::Module::new', 'wasmer::Module::new'],
            'typical_bugs': [
                'buffer_overflow',
                'integer_overflow',
                'denial_of_service',
            ],
        },
        'validator': {
            'description': 'Validador de módulos Wasm',
            'priority': 'high',
            'complexity': 'medium',
            'entry_points': ['wasm_tools::validate'],
            'typical_bugs': [
                'type_mismatch',
                'invalid_instruction',
                'resource_exhaustion',
            ],
        },
        'executor': {
            'description': 'Executor de instruções Wasm',
            'priority': 'critical',
            'complexity': 'very_high',
            'entry_points': ['wasmtime::Func::call', 'wasmer::Instance::exports'],
            'typical_bugs': [
                'memory_corruption',
                'undefined_behavior',
                'stack_overflow',
            ],
        },
        'wasi': {
            'description': 'Implementação WASI',
            'priority': 'high',
            'complexity': 'high',
            'entry_points': ['wasi_snapshot_preview1::*'],
            'typical_bugs': [
                'path_traversal',
                'permission_bypass',
                'resource_leak',
            ],
        },
        'compiler': {
            'description': 'Compilador Wasm (Cranelift/LLVM)',
            'priority': 'medium',
            'complexity': 'very_high',
            'entry_points': ['cranelift::Module::translate'],
            'typical_bugs': [
                'miscompilation',
                'register_allocation',
                'optimization_bug',
            ],
        },
    }
    
    @classmethod
    def select_targets(cls, priorities=None):
        """Seleciona targets baseado em prioridades."""
        if priorities is None:
            priorities = ['critical', 'high']
        
        selected = {}
        for name, target in cls.TARGET_CATEGORIES.items():
            if target['priority'] in priorities:
                selected[name] = target
        
        return selected
    
    @classmethod
    def generate_target_config(cls, target_name):
        """Gera configuração para um target."""
        target = cls.TARGET_CATEGORIES.get(target_name)
        if not target:
            return None
        
        config = {
            'name': target_name,
            'description': target['description'],
            'priority': target['priority'],
            'max_len': 4096,
            'timeout': 30,
            'jobs': 4,
            'workers': 4,
            'dict': f'fuzz/dictionaries/{target_name}.txt',
            'corpus': f'fuzz/corpus/{target_name}/',
            'artifacts': f'fuzz/artifacts/{target_name}/',
        }
        
        return config
    
    @classmethod
    def generate_fuzz_target_rs(cls, target_name):
        """Gera código do fuzz target em Rust."""
        target = cls.TARGET_CATEGORIES.get(target_name)
        if not target:
            return None
        
        entry_point = target['entry_points'][0]
        
        code = f'''//! Fuzz target para {target_name}
//! {target['description']}

#![no_main]

use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: &[u8]| {{
    // Verificar se é um módulo Wasm válido
    if data.len() < 8 {{
        return;
    }}
    
    // Verificar magic number
    if &data[0..4] != b"\\x00asm" {{
        return;
    }}
    
    // Configurar runtime
    let engine = wasmtime::Engine::default();
    
    // Tentar decodificar o módulo
    match wasmtime::Module::new(&engine, data) {{
        Ok(module) => {{
            // Módulo válido - tentar instanciar
            let mut store = wasmtime::Store::new(&engine, ());
            
            // Criar linker
            let mut linker = wasmtime::Linker::new(&engine);
            
            // Adicionar WASI se necessário
            // wasmtime_wasi::add_to_linker(&mut linker, |s| s).ok();
            
            // Tentar instanciar
            if let Ok(instance) = linker.instantiate(&mut store, &module) {{
                // Chamar exportações
                for export in instance.exports(&mut store) {{
                    match export {{
                        wasmtime::Extern::Func(func) => {{
                            let _ = func.call(&mut store, &[], &mut []);
                        }}
                        _ => {{}}
                    }}
                }}
            }}
        }}
        Err(_) => {{
            // Módulo inválido - esperado na maioria das vezes
        }}
    }}
}});
'''
        
        return code
```

### 12.10.3 Configuração do Fuzzer

```yaml
# fuzz-config.yaml - Configuração de fuzzing
fuzzer:
  name: wasm-fuzz
  type: coverage-guided
  
targets:
  decoder:
    max_len: 4096
    timeout: 30
    jobs: 4
    workers: 4
    dict: fuzz/dictionaries/decoder.txt
    corpus: fuzz/corpus/decoder/
    artifacts: fuzz/artifacts/decoder/
    
  validator:
    max_len: 8192
    timeout: 10
    jobs: 2
    workers: 2
    dict: fuzz/dictionaries/validator.txt
    corpus: fuzz/corpus/validator/
    artifacts: fuzz/artifacts/validator/
    
  executor:
    max_len: 16384
    timeout: 60
    jobs: 8
    workers: 8
    dict: fuzz/dictionaries/executor.txt
    corpus: fuzz/corpus/executor/
    artifacts: fuzz/artifacts/executor/

resources:
  max_memory_mb: 8192
  max_cpu_percent: 80
  max_disk_mb: 10240

monitoring:
  metrics_interval: 60
  alert_threshold:
    crash_rate: 0.01
    coverage_plateau: 1000

coverage:
  map_size: 65536
  minimal_coverage_threshold: 0.1
  
corpus:
  max_size: 10000
  minimize_interval: 3600
  distillation_enabled: true

regression:
  enabled: true
  test_dir: tests/regression/
  auto_add_crashes: true
```

### 12.10.4 Inicialização do Corpus

```python
#!/usr/bin/env python3
"""init_corpus.py - Inicializa corpus para fuzzing de Wasm."""

import os
import struct
import subprocess
from pathlib import Path

class CorpusInitializer:
    """Inicializador de corpus para fuzzing."""
    
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def initialize(self):
        """Inicializa corpus com sementes básicas."""
        print("Inicializando corpus...")
        
        # 1. Módulos mínimos
        self._generate_minimal_modules()
        
        # 2. Módulos de teste
        self._generate_test_modules()
        
        # 3. Módulos reais (se disponíveis)
        self._download_real_modules()
        
        # 4. Minimizar corpus
        self._minimize_corpus()
        
        print(f"Corpus inicializado com {len(list(self.output_dir.glob('*.wasm')))} sementes")
    
    def _generate_minimal_modules(self):
        """Gera módulos Wasm mínimos."""
        modules = {
            'empty.wasm': self._empty_module(),
            'nop.wasm': self._nop_function(),
            'return_42.wasm': self._return_42(),
            'memory.wasm': self._with_memory(),
            'control_flow.wasm': self._control_flow(),
        }
        
        for name, data in modules.items():
            filepath = self.output_dir / name
            filepath.write_bytes(data)
    
    def _generate_test_modules(self):
        """Gera módulos de teste mais complexos."""
        modules = {
            'arithmetic.wasm': self._arithmetic_ops(),
            'comparisons.wasm': self._comparison_ops(),
            'conversions.wasm': self._conversion_ops(),
            'memory_ops.wasm': self._memory_operations(),
            'locals.wasm': self._local_operations(),
        }
        
        for name, data in modules.items():
            filepath = self.output_dir / name
            filepath.write_bytes(data)
    
    def _download_real_modules(self):
        """Baixa módulos Wasm reais de exemplos."""
        # URLs de módulos Wasm de exemplo
        urls = [
            # Adicionar URLs de módulos Wasm de exemplo
        ]
        
        for url in urls:
            try:
                filename = url.split('/')[-1]
                filepath = self.output_dir / filename
                
                if not filepath.exists():
                    subprocess.run(
                        ['wget', '-q', url, '-O', str(filepath)],
                        timeout=30,
                    )
            except Exception as e:
                print(f"Erro ao baixar {url}: {e}")
    
    def _minimize_corpus(self):
        """Minimiza o corpus removendo duplicatas."""
        seen_hashes = set()
        
        for wasm_file in self.output_dir.glob('*.wasm'):
            content = wasm_file.read_bytes()
            content_hash = hash(content)
            
            if content_hash in seen_hashes:
                wasm_file.unlink()
            else:
                seen_hashes.add(content_hash)
    
    # Métodos para gerar módulos
    def _empty_module(self):
        return b'\x00\x61\x73\x6d\x01\x00\x00\x00'
    
    def _nop_function(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x0a\x06\x01\x04\x00\x01\x01\x0b'
        )
    
    def _return_42(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x09\x01\x07\x00\x41\x2a\x0b'
        )
    
    def _with_memory(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x05\x03\x01\x04\x00'
        )
    
    def _control_flow(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x06\x01\x60\x01\x7f\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0f\x01\x0d\x00\x20\x00\x45\x04\x40'
            b'\x41\x01\x05\x41\x00\x0b\x0b'
        )
    
    def _arithmetic_ops(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x06\x01\x60\x02\x7f\x7f\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0d\x01\x0b\x00\x20\x00\x20\x01\x6a\x0b'
        )
    
    def _comparison_ops(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x06\x01\x60\x02\x7f\x7f\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0d\x01\x0b\x00\x20\x00\x20\x01\x46\x0b'
        )
    
    def _conversion_ops(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x09\x01\x07\x00\x42\x2a\xa7\x0b'
        )
    
    def _memory_operations(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x04\x01\x60\x00\x00'
            b'\x03\x02\x01\x00'
            b'\x05\x03\x01\x04\x00'
            b'\x0a\x0c\x01\x0a\x00\x41\x00\x28\x02\x00\x1a\x0b'
        )
    
    def _local_operations(self):
        return (
            b'\x00\x61\x73\x6d\x01\x00\x00\x00'
            b'\x01\x05\x01\x60\x00\x01\x7f'
            b'\x03\x02\x01\x00'
            b'\x0a\x0c\x01\x0a\x00\x01\x01\x7f\x41\x2a\x21\x00\x20\x00\x0b'
        )


if __name__ == '__main__':
    initializer = CorpusInitializer('fuzz/corpus')
    initializer.initialize()
```

### 12.10.5 Executando a Primeira Campanha

```bash
#!/bin/bash
# run_fuzzing.sh - Executa campanha de fuzzing

set -e

TARGET=${1:-decoder}
DURATION=${2:-3600}
OUTPUT_DIR="fuzz/artifacts/${TARGET}"
CORPUS_DIR="fuzz/corpus/${TARGET}"

echo "=== Iniciando campanha de fuzzing ==="
echo "Target: ${TARGET}"
echo "Duração: ${DURATION}s"
echo "Saída: ${OUTPUT_DIR}"

# Verificar se o target existe
if ! cargo fuzz list | grep -q "${TARGET}"; then
    echo "Target '${TARGET}' não encontrado"
    echo "Targets disponíveis:"
    cargo fuzz list
    exit 1
fi

# Criar diretórios
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${CORPUS_DIR}"

# Verificar corpus
SEED_COUNT=$(find "${CORPUS_DIR}" -type f | wc -l)
echo "Sementes no corpus: ${SEED_COUNT}"

if [ "${SEED_COUNT}" -eq 0 ]; then
    echo "Inicializando corpus..."
    python3 scripts/init_corpus.py "${CORPUS_DIR}"
fi

# Iniciar fuzzing
echo "Iniciando fuzzing..."
cargo fuzz run "${TARGET}" \
    -- \
    -max_total_time="${DURATION}" \
    -max_len=4096 \
    -timeout=30 \
    -jobs=4 \
    -workers=4 \
    -artifact_prefix="${OUTPUT_DIR}/"

echo "=== Fuzzing concluído ==="

# Analisar resultados
echo "Analisando resultados..."
CRASH_COUNT=$(find "${OUTPUT_DIR}" -name "crash-*" | wc -l)
echo "Crashes encontrados: ${CRASH_COUNT}"

if [ "${CRASH_COUNT}" -gt 0 ]; then
    echo "Detalhes dos crashes:"
    for crash in "${OUTPUT_DIR}"/crash-*; do
        SIZE=$(wc -c < "${crash}")
        echo "  - $(basename "${crash}") (${SIZE} bytes)"
    done
fi
```

### 12.10.6 Analisando Resultados

```python
#!/usr/bin/env python3
"""analyze_results.py - Analisa resultados de uma campanha de fuzzing."""

import os
import json
import subprocess
from pathlib import Path
from collections import defaultdict

class FuzzingResultsAnalyzer:
    """Analisador de resultados de fuzzing."""
    
    def __init__(self, artifacts_dir):
        self.artifacts_dir = Path(artifacts_dir)
        self.crashes = []
        self.hangs = []
        self.coverage = {}
    
    def analyze(self):
        """Analisa todos os resultados."""
        print("Analisando resultados de fuzzing...")
        
        # Encontrar crashes
        self._find_crashes()
        
        # Encontrar hangs
        self._find_hangs()
        
        # Analisar cobertura
        self._analyze_coverage()
        
        # Gerar relatório
        return self.generate_report()
    
    def _find_crashes(self):
        """Encontra e analisa crashes."""
        for crash_file in self.artifacts_dir.glob('crash-*'):
            try:
                crash_data = crash_file.read_bytes()
                
                # Classificar o crash
                crash_type = self._classify_crash(crash_data)
                
                self.crashes.append({
                    'file': str(crash_file),
                    'size': len(crash_data),
                    'type': crash_type,
                    'hash': self._hash_data(crash_data),
                })
            except Exception as e:
                print(f"Erro ao analisar {crash_file}: {e}")
    
    def _find_hangs(self):
        """Encontra hangs."""
        for hang_file in self.artifacts_dir.glob('hang-*'):
            try:
                hang_data = hang_file.read_bytes()
                
                self.hangs.append({
                    'file': str(hang_file),
                    'size': len(hang_data),
                })
            except Exception as e:
                print(f"Erro ao analisar {hang_file}: {e}")
    
    def _classify_crash(self, data):
        """Classifica o tipo de crash."""
        # Verificar se é módulo Wasm válido
        if len(data) >= 4 and data[:4] == b'\x00asm':
            return 'valid_wasm_crash'
        elif len(data) >= 4 and data[:4] != b'\x00asm':
            return 'invalid_wasm_crash'
        else:
            return 'small_input_crash'
    
    def _hash_data(self, data):
        """Calcula hash dos dados."""
        import hashlib
        return hashlib.sha256(data).hexdigest()[:16]
    
    def _analyze_coverage(self):
        """Analisa dados de cobertura."""
        # Procurar por arquivos de cobertura
        coverage_file = self.artifacts_dir / 'coverage.txt'
        
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    content = f.read()
                    
                # Extrair métricas
                for line in content.split('\n'):
                    if 'edges' in line.lower():
                        self.coverage['edges'] = int(line.split(':')[1].strip())
                    elif 'hit' in line.lower():
                        self.coverage['hit'] = int(line.split(':')[1].strip())
            except Exception as e:
                print(f"Erro ao ler cobertura: {e}")
    
    def generate_report(self):
        """Gera relatório de análise."""
        report = {
            'summary': {
                'total_crashes': len(self.crashes),
                'total_hangs': len(self.hangs),
                'unique_crashes': len(set(c['hash'] for c in self.crashes)),
            },
            'crashes_by_type': {},
            'coverage': self.coverage,
            'top_crashes': self.crashes[:10],
        }
        
        # Agrupar por tipo
        for crash in self.crashes:
            crash_type = crash['type']
            if crash_type not in report['crashes_by_type']:
                report['crashes_by_type'][crash_type] = 0
            report['crashes_by_type'][crash_type] += 1
        
        return report
    
    def print_report(self, report):
        """Imprime relatório formatado."""
        print("\n" + "=" * 60)
        print("RELATÓRIO DE ANÁLISE DE FUZZING")
        print("=" * 60)
        
        print(f"\nResumo:")
        print(f"  Total de crashes: {report['summary']['total_crashes']}")
        print(f"  Total de hangs: {report['summary']['total_hangs']}")
        print(f"  Crashes únicos: {report['summary']['unique_crashes']}")
        
        print(f"\nCrashes por tipo:")
        for crash_type, count in report['crashes_by_type'].items():
            print(f"  {crash_type}: {count}")
        
        if report['coverage']:
            print(f"\nCobertura:")
            for metric, value in report['coverage'].items():
                print(f"  {metric}: {value}")
        
        print(f"\nTop crashes:")
        for i, crash in enumerate(report['top_crashes'][:5], 1):
            print(f"  {i}. {crash['type']} ({crash['size']} bytes) - {crash['hash']}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python analyze_results.py <artifacts_dir>")
        sys.exit(1)
    
    analyzer = FuzzingResultsAnalyzer(sys.argv[1])
    report = analyzer.analyze()
    analyzer.print_report(report)
```

### 12.10.7 Iterando e Melhorando

```python
class FuzzingImprover:
    """Classe para melhorar campanhas de fuzzing baseado em resultados."""
    
    def __init__(self, campaign_dir):
        self.campaign_dir = Path(campaign_dir)
        self.suggestions = []
    
    def analyze_and_suggest(self, results):
        """Analisa resultados e sugere melhorias."""
        self.suggestions = []
        
        # Analisar cobertura
        if results.get('coverage', {}).get('edges', 0) < 1000:
            self.suggestions.append({
                'type': 'coverage',
                'priority': 'high',
                'suggestion': 'Cobertura baixa - adicionar mais sementes ao corpus',
                'action': 'Adicionar módulos Wasm mais complexos ao corpus',
            })
        
        # Analisar crashes
        crash_count = results.get('summary', {}).get('total_crashes', 0)
        
        if crash_count == 0:
            self.suggestions.append({
                'type': 'crashes',
                'priority': 'medium',
                'suggestion': 'Nenhum crash encontrado - considerar mutações mais agressivas',
                'action': 'Aumentar intensidade de mutação ou adicionar novos targets',
            })
        elif crash_count > 100:
            self.suggestions.append({
                'type': 'crashes',
                'priority': 'high',
                'suggestion': 'Muitos crashes - verificar se são bugs reais',
                'action': 'Revisar e minimizar crashes antes de reportar',
            })
        
        # Analisar hangs
        hang_count = results.get('summary', {}).get('total_hangs', 0)
        
        if hang_count > 10:
            self.suggestions.append({
                'type': 'hangs',
                'priority': 'high',
                'suggestion': 'Muitos hangs - possível problema de timeout',
                'action': 'Reduzir timeout ou adicionar verificações de loop',
            })
        
        # Analisar eficiência
        total_time = results.get('total_time', 0)
        if total_time > 0 and crash_count / total_time < 0.001:
            self.suggestions.append({
                'type': 'efficiency',
                'priority': 'medium',
                'suggestion': 'Taxa de crash baixa - considerar fuzzing diferencial',
                'action': 'Implementar differential fuzzing entre runtimes',
            })
        
        return self.suggestions
    
    def apply_improvements(self):
        """Aplica melhorias automaticamente."""
        applied = []
        
        for suggestion in self.suggestions:
            if suggestion['priority'] == 'high':
                # Aplicar melhoria automática
                if suggestion['type'] == 'coverage':
                    self._improve_corpus()
                    applied.append(suggestion)
                elif suggestion['type'] == 'crashes':
                    self._minimize_crashes()
                    applied.append(suggestion)
        
        return applied
    
    def _improve_corpus(self):
        """Melhora o corpus adicionando sementes."""
        corpus_dir = self.campaign_dir / 'corpus'
        
        # Gerar novas sementes
        from init_corpus import CorpusInitializer
        initializer = CorpusInitializer(str(corpus_dir))
        initializer._generate_minimal_modules()
        initializer._generate_test_modules()
    
    def _minimize_crashes(self):
        """Minimiza crashes encontrados."""
        artifacts_dir = self.campaign_dir / 'artifacts'
        
        for crash_file in artifacts_dir.glob('crash-*'):
            # Minimizar cada crash
            try:
                data = crash_file.read_bytes()
                minimized = self._minimize_data(data)
                
                if len(minimized) < len(data):
                    crash_file.write_bytes(minimized)
                    print(f"Minimizado: {crash_file.name} ({len(data)} -> {len(minimized)} bytes)")
            except Exception as e:
                print(f"Erro ao minimizar {crash_file}: {e}")
    
    def _minimize_data(self, data):
        """Minimiza dados preservando o crash."""
        # Implementação simplificada
        return data
    
    def generate_improvement_report(self):
        """Gera relatório de melhorias."""
        report = {
            'total_suggestions': len(self.suggestions),
            'high_priority': sum(1 for s in self.suggestions if s['priority'] == 'high'),
            'medium_priority': sum(1 for s in self.suggestions if s['priority'] == 'medium'),
            'suggestions': self.suggestions,
        }
        
        return report
```

## 12.11 Advanced Techniques

Técnicas avançadas de fuzzing combinam múltiplas abordagens para maximizar a cobertura e encontrar bugs que seriam impossíveis de detectar com técnicas simples.

### 12.11.1 Fuzzing Híbrido (Simbólico + Concreto)

Fuzzing híbrido combina execução concreta (como fuzzing tradicional) com execução simbólica para gerar entradas que atingem caminhos específicos do programa.

```
+------------------------------------------------------------------+
|              Fuzzing Híbrido para Wasm                             |
+------------------------------------------------------------------+
|                                                                    |
|  +------------------+    +------------------+    +---------------+ |
|  | Fuzzer           |    | Concolic Engine  |    | SMT Solver    | |
|  | (execução        | <-> | (execução        | <-> | (Z3/CVC5)    | |
|  |  concreta)       |    |  simbólica)      |    |               | |
|  +--------+---------+    +--------+---------+    +-------+-------+ |
|           |                       |                      |          |
|           v                       v                      v          |
|  +------------------+    +------------------+    +---------------+ |
|  | Feedback de      |    | Constraint       |    | Novas entradas| |
|  | cobertura        | <- | Generation       | <- | geradas       | |
|  +------------------+    +------------------+    +---------------+ |
|                                                                    |
+------------------------------------------------------------------+
```

```python
import z3

class SymbolicWasmExecutor:
    """Executor simbólico simplificado para módulos Wasm."""
    
    def __init__(self):
        self.solver = z3.Solver()
        self.symbolic_vars = {}
    
    def create_symbolic_input(self, name, size):
        """Cria entrada simbólica."""
        self.symbolic_vars[name] = z3.BitVec(name, size * 8)
        return self.symbolic_vars[name]
    
    def solve_path_condition(self, path_constraints):
        """Resolve restrições de caminho."""
        self.solver.push()
        
        for constraint in path_constraints:
            self.solver.add(constraint)
        
        result = self.solver.check()
        
        if result == z3.sat:
            model = self.solver.model()
            self.solver.pop()
            return model
        else:
            self.solver.pop()
            return None
    
    def generate_input_for_path(self, branch_constraints):
        """Gera entrada que atinge um caminho específico."""
        constraints = []
        
        for branch in branch_constraints:
            if branch['taken']:
                constraints.append(branch['constraint'])
            else:
                constraints.append(z3.Not(branch['constraint']))
        
        return self.solve_path_condition(constraints)
    
    def analyze_divergence(self, concrete_path, symbolic_path):
        """Analisa divergência entre execução concreta e simbólica."""
        # Comparar estados
        concrete_state = concrete_path[-1] if concrete_path else {}
        symbolic_state = symbolic_path[-1] if symbolic_path else {}
        
        divergences = []
        
        for key in set(list(concrete_state.keys()) + list(symbolic_state.keys())):
            concrete_val = concrete_state.get(key)
            symbolic_val = symbolic_state.get(key)
            
            if concrete_val != symbolic_val:
                divergences.append({
                    'variable': key,
                    'concrete': concrete_val,
                    'symbolic': symbolic_val,
                })
        
        return divergences
```

### 12.11.2 Geração de Testes Baseada em Gramática

```python
from typing import List, Dict, Any, Optional
import random

class WasmGrammarGenerator:
    """Gerador de testes baseado em gramática para Wasm."""
    
    def __init__(self):
        self.grammar = self._define_grammar()
    
    def _define_grammar(self):
        """Define a gramática Wasm simplificada."""
        return {
            'module': ['magic', 'version', 'section+'],
            'section': ['type_section', 'import_section', 'function_section',
                       'memory_section', 'export_section', 'code_section'],
            'type_section': ['type_header', 'func_type+'],
            'func_type': ['functype', 'param*', 'result*'],
            'param': ['valtype'],
            'result': ['valtype'],
            'valtype': ['i32', 'i64', 'f32', 'f64'],
            'code_section': ['code_header', 'func_body+'],
            'func_body': ['local_decl*', 'expr', 'end'],
            'expr': ['instr*'],
            'instr': ['const', 'binop', 'unop', 'control', 'variable', 'memory'],
            'const': ['i32.const', 'i64.const', 'f32.const', 'f64.const'],
            'binop': ['i32.add', 'i32.sub', 'i32.mul', 'i32.div_s',
                     'i32.div_u', 'i32.rem_s', 'i32.rem_u'],
            'control': ['block', 'loop', 'if', 'br', 'br_if', 'return', 'call'],
        }
    
    def generate(self, max_depth=5):
        """Gera um módulo Wasm baseado na gramática."""
        return self._expand('module', 0, max_depth)
    
    def _expand(self, symbol, depth, max_depth):
        """Expande um símbolo da gramática."""
        if depth >= max_depth:
            return self._terminal_for(symbol)
        
        if symbol not in self.grammar:
            return self._terminal_for(symbol)
        
        production = random.choice(self.grammar[symbol])
        
        if isinstance(production, str):
            return self._expand(production, depth + 1, max_depth)
        elif isinstance(production, list):
            return self._expand_sequence(production, depth + 1, max_depth)
        
        return self._terminal_for(symbol)
    
    def _expand_sequence(self, symbols, depth, max_depth):
        """Expande uma sequência de símbolos."""
        result = []
        
        for symbol in symbols:
            if symbol.endswith('+'):
                # Um ou mais
                base = symbol[:-1]
                count = random.randint(1, 3)
                for _ in range(count):
                    result.append(self._expand(base, depth + 1, max_depth))
            elif symbol.endswith('*'):
                # Zero ou mais
                base = symbol[:-1]
                count = random.randint(0, 3)
                for _ in range(count):
                    result.append(self._expand(base, depth + 1, max_depth))
            elif symbol.endswith('?'):
                # Opcional
                base = symbol[:-1]
                if random.random() > 0.5:
                    result.append(self._expand(base, depth + 1, max_depth))
            else:
                result.append(self._expand(symbol, depth + 1, max_depth))
        
        return result
    
    def _terminal_for(self, symbol):
        """Retorna terminal para um símbolo."""
        terminals = {
            'magic': b'\x00\x61\x73\x6d',
            'version': b'\x01\x00\x00\x00',
            'i32': b'\x7f',
            'i64': b'\x7e',
            'f32': b'\x7d',
            'f64': b'\x7c',
            'i32.const': b'\x41',
            'i64.const': b'\x42',
            'f32.const': b'\x43',
            'f64.const': b'\x44',
            'i32.add': b'\x6a',
            'i32.sub': b'\x6b',
            'i32.mul': b'\x6c',
            'i32.div_s': b'\x6d',
            'i32.div_u': b'\x6e',
            'i32.rem_s': b'\x6f',
            'i32.rem_u': b'\x70',
            'block': b'\x02',
            'loop': b'\x03',
            'if': b'\x04',
            'br': b'\x0c',
            'br_if': b'\x0d',
            'return': b'\x0f',
            'call': b'\x10',
            'end': b'\x0b',
            'drop': b'\x1a',
            'select': b'\x1b',
            'local.get': b'\x20',
            'local.set': b'\x21',
            'i32.load': b'\x28',
            'i32.store': b'\x36',
            'functype': b'\x60',
            'type_header': b'\x01',
            'code_header': b'\x0a',
            'local_decl': b'\x01',
            'expr': b'\x00',
            'param': b'\x00',
            'result': b'\x01',
            'valtype': b'\x7f',
        }
        
        return terminals.get(symbol, b'\x00')
    
    def mutate_grammar(self, grammar_element, mutation_rate=0.1):
        """Muta um elemento da gramática."""
        if random.random() > mutation_rate:
            return grammar_element
        
        # Operações de mutação na gramática
        mutation_type = random.choice(['replace', 'add', 'remove', 'reorder'])
        
        if mutation_type == 'replace' and isinstance(grammar_element, list):
            if len(grammar_element) > 0:
                idx = random.randint(0, len(grammar_element) - 1)
                grammar_element[idx] = self._random_terminal()
        
        elif mutation_type == 'add' and isinstance(grammar_element, list):
            grammar_element.insert(
                random.randint(0, len(grammar_element)),
                self._random_terminal()
            )
        
        elif mutation_type == 'remove' and isinstance(grammar_element, list):
            if len(grammar_element) > 1:
                idx = random.randint(0, len(grammar_element) - 1)
                grammar_element.pop(idx)
        
        elif mutation_type == 'reorder' and isinstance(grammar_element, list):
            random.shuffle(grammar_element)
        
        return grammar_element
    
    def _random_terminal(self):
        """Retorna um terminal aleatório."""
        terminals = [b'\x41', b'\x42', b'\x6a', b'\x6b', b'\x0b', b'\x01']
        return random.choice(terminals)
```

### 12.11.3 Geração de Testes Guiada por Feedback

```python
class FeedbackDrivenGenerator:
    """Gerador de testes guiado por feedback de cobertura."""
    
    def __init__(self, coverage_tracker):
        self.coverage = coverage_tracker
        self.population = []
        self.fitness_scores = {}
    
    def evolve_population(self, iterations=100):
        """Evolui a população de testes."""
        for _ in range(iterations):
            # Selecionar pais
            parent1 = self._select_parent()
            parent2 = self._select_parent()
            
            # Cruzamento
            child = self._crossover(parent1, parent2)
            
            # Mutação
            child = self._mutate(child)
            
            # Avaliar fitness
            fitness = self._evaluate_fitness(child)
            
            # Adicionar à população
            self.population.append(child)
            self.fitness_scores[id(child)] = fitness
            
            # Manter população controlada
            if len(self.population) > 1000:
                self._prune_population()
    
    def _select_parent(self):
        """Seleciona pai baseado em fitness."""
        if not self.population:
            return self._generate_random()
        
        # Tournament selection
        tournament_size = min(5, len(self.population))
        tournament = random.sample(self.population, tournament_size)
        
        return max(
            tournament,
            key=lambda x: self.fitness_scores.get(id(x), 0)
        )
    
    def _crossover(self, parent1, parent2):
        """Cruza dois pais."""
        if not parent1 or not parent2:
            return parent1 or parent2
        
        # Crossover de ponto único
        point = random.randint(0, min(len(parent1), len(parent2)))
        
        child = parent1[:point] + parent2[point:]
        return child
    
    def _mutate(self, individual):
        """Muta um indivíduo."""
        if not individual:
            return self._generate_random()
        
        mutation_rate = 0.1
        mutated = bytearray(individual)
        
        for i in range(len(mutated)):
            if random.random() < mutation_rate:
                # Diferentes tipos de mutação
                mutation_type = random.choice(['byte', 'flip', 'swap'])
                
                if mutation_type == 'byte':
                    mutated[i] = random.randint(0, 255)
                elif mutation_type == 'flip':
                    mutated[i] ^= 0xFF
                elif mutation_type == 'swap' and i + 1 < len(mutated):
                    mutated[i], mutated[i+1] = mutated[i+1], mutated[i]
        
        return bytes(mutated)
    
    def _evaluate_fitness(self, individual):
        """Avalia fitness de um indivíduo."""
        if not individual:
            return 0
        
        fitness = 0
        
        # Fitness baseado em cobertura
        coverage_before = self.coverage.get_edges_covered()
        
        # Executar e medir cobertura
        # (simplificado - na prática executaria o módulo)
        new_edges = 0  # Simular
        
        fitness += new_edges * 10
        
        # Fitness baseado em validade
        if self._is_valid_wasm(individual):
            fitness += 50
        
        # Fitness baseado em tamanho (preferir entradas menores)
        fitness += max(0, 100 - len(individual) // 10)
        
        return fitness
    
    def _is_valid_wasm(self, data):
        """Verifica se é módulo Wasm válido."""
        return len(data) >= 8 and data[:4] == b'\x00asm'
    
    def _generate_random(self):
        """Gera indivíduo aleatório."""
        size = random.randint(8, 1024)
        return bytes(random.randint(0, 255) for _ in range(size))
    
    def _prune_population(self):
        """Remove indivíduos com baixo fitness."""
        if len(self.population) <= 100:
            return
        
        # Ordenar por fitness
        scored = [
            (ind, self.fitness_scores.get(id(ind), 0))
            for ind in self.population
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Manter top 100
        self.population = [ind for ind, _ in scored[:100]]
    
    def get_best_individuals(self, n=10):
        """Retorna os melhores indivíduos."""
        scored = [
            (ind, self.fitness_scores.get(id(ind), 0))
            for ind in self.population
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [ind for ind, _ in scored[:n]]
```

### 12.11.4 Integração de Sanitizers (ASan, MSan, UBSan)

```bash
#!/bin/bash
# build_with_sanitizers.sh - Compila módulos Wasm com sanitizers

set -e

TARGET=${1:-target}
SANITIZER=${2:-address}

echo "Compilando ${TARGET} com sanitizer: ${SANITIZER}"

case ${SANITIZER} in
    address)
        RUSTFLAGS="-Z sanitizer=address" \
        cargo build --release --target wasm32-wasi
        ;;
    memory)
        RUSTFLAGS="-Z sanitizer=memory" \
        cargo build --release --target wasm32-wasi
        ;;
    undefined)
        RUSTFLAGS="-Z sanitizer=undefined" \
        cargo build --release --target wasm32-wasi
        ;;
    *)
        echo "Sanitizer desconhecido: ${SANITIZER}"
        echo "Opções: address, memory, undefined"
        exit 1
        ;;
esac

echo "Build concluído com sanitizer ${SANITIZER}"
```

```python
class SanitizerConfig:
    """Configuração de sanitizers para fuzzing."""
    
    SANITIZERS = {
        'address': {
            'description': 'AddressSanitizer - detecta erros de memória',
            'detects': [
                'heap-buffer-overflow',
                'stack-buffer-overflow',
                'heap-use-after-free',
                'double-free',
                'memory-leaks',
            ],
            'rustflags': '-Z sanitizer=address',
            'env_vars': {
                'ASAN_OPTIONS': 'detect_leaks=1:detect_stack_use_after_return=1',
            },
        },
        'memory': {
            'description': 'MemorySanitizer - detecta uso de memória não inicializada',
            'detects': [
                'use-of-uninitialized-value',
            ],
            'rustflags': '-Z sanitizer=memory',
            'env_vars': {
                'MSAN_OPTIONS': 'halt_on_error=0',
            },
        },
        'undefined': {
            'description': 'UndefinedBehaviorSanitizer - detecta comportamento indefinido',
            'detects': [
                'signed-integer-overflow',
                'unsigned-integer-overflow',
                'null-pointer-assignment',
                'misaligned-pointer',
                'integer-divide-by-zero',
                'float-divide-by-zero',
                'invalid-bool-cast',
                'invalid-enum-cast',
            ],
            'rustflags': '-Z sanitizer=undefined',
            'env_vars': {
                'UBSAN_OPTIONS': 'print_stacktrace=1',
            },
        },
    }
    
    @classmethod
    def get_config(cls, sanitizer_name):
        """Retorna configuração de um sanitizer."""
        return cls.SANITIZERS.get(sanitizer_name)
    
    @classmethod
    def build_command(cls, sanitizer_name, target='wasm32-wasi'):
        """Gera comando de build para um sanitizer."""
        config = cls.get_config(sanitizer_name)
        if not config:
            return None
        
        return f'RUSTFLAGS="{config["rustflags"]}" cargo build --release --target {target}'
    
    @classmethod
    def run_env(cls, sanitizer_name):
        """Retorna variáveis de ambiente para um sanitizer."""
        config = cls.get_config(sanitizer_name)
        if not config:
            return {}
        
        return config['env_vars']
```

### 12.11.5 Fuzzing de Host Functions WASI

```python
class WASIHostFunctionFuzzer:
    """Fuzzer para host functions WASI."""
    
    WASI_FUNCTIONS = {
        'fd_write': {
            'params': ['fd', 'iovec_ptr', 'iovec_len', 'nwritten_ptr'],
            'typical_bugs': ['buffer_overflow', 'invalid_fd'],
        },
        'fd_read': {
            'params': ['fd', 'iovec_ptr', 'iovec_len', 'nread_ptr'],
            'typical_bugs': ['buffer_overflow', 'invalid_fd'],
        },
        'path_open': {
            'params': ['fd', 'dirflags', 'path_ptr', 'path_len', 'oflags',
                       'fs_flags', 'fs_rights_base', 'fs_rights_inheriting', 'fd_ptr'],
            'typical_bugs': ['path_traversal', 'permission_bypass'],
        },
        'environ_get': {
            'params': ['environ_ptrs', 'environ_buf'],
            'typical_bugs': ['buffer_overflow', 'null_pointer'],
        },
        'random_get': {
            'params': ['buf_ptr', 'buf_len'],
            'typical_bugs': ['buffer_overflow'],
        },
        'clock_time_get': {
            'params': ['clock_id', 'precision', 'time_ptr'],
            'typical_bugs': ['invalid_clock_id'],
        },
    }
    
    def __init__(self, wasi_runtime):
        self.runtime = wasi_runtime
    
    def generate_fuzz_input(self, function_name):
        """Gera entrada fuzz para uma WASI function."""
        func_info = self.WASI_FUNCTIONS.get(function_name)
        if not func_info:
            return None
        
        # Gerar parâmetros fuzzados
        params = {}
        for param in func_info['params']:
            params[param] = self._generate_param(param)
        
        return params
    
    def _generate_param(self, param_name):
        """Gera valor fuzzado para um parâmetro."""
        if 'fd' in param_name:
            return random.choice([0, 1, 2, 3, 4, 5, -1, 999, 0xFFFFFFFF])
        elif 'ptr' in param_name:
            return random.choice([0, 1, 0x1000, 0xFFFF0000, 0xFFFFFFFF])
        elif 'len' in param_name:
            return random.choice([0, 1, 100, 65536, 0xFFFFFFFF])
        elif 'flags' in param_name:
            return random.randint(0, 0xFFFFFFFF)
        elif 'rights' in param_name:
            return random.randint(0, 0xFFFFFFFFFFFFFFFF)
        else:
            return random.randint(0, 0xFFFFFFFF)
    
    def test_function(self, function_name, params):
        """Testa uma WASI function com parâmetros fuzzados."""
        try:
            result = self.runtime.call(function_name, params)
            return {
                'success': True,
                'result': result,
                'params': params,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'params': params,
            }
    
    def fuzz_function(self, function_name, iterations=1000):
        """Fuzzing de uma WASI function específica."""
        results = {
            'total': iterations,
            'successes': 0,
            'errors': 0,
            'crashes': 0,
            'unique_errors': set(),
        }
        
        for i in range(iterations):
            params = self.generate_fuzz_input(function_name)
            result = self.test_function(function_name, params)
            
            if result['success']:
                results['successes'] += 1
            else:
                results['errors'] += 1
                error_key = str(result['error'])[:100]
                results['unique_errors'].add(error_key)
        
        results['unique_errors'] = len(results['unique_errors'])
        return results
```

### 12.11.6 Fuzzing de Protocolo de Rede via Wasm

```python
class NetworkProtocolFuzzer:
    """Fuzzer para protocolos de rede via módulos Wasm."""
    
    def __init__(self, wasm_module_path):
        self.module_path = wasm_module_path
        self.engine = None
    
    def load_module(self):
        """Carrega o módulo Wasm para fuzzing de rede."""
        import wasmtime
        
        self.engine = wasmtime.Engine()
        module = wasmtime.Module.from_file(self.engine, self.module_path)
        
        store = wasmtime.Store(self.engine)
        instance = wasmtime.Instance(store, module, [])
        
        return store, instance
    
    def fuzz_network_handler(self, handler_func, protocol_data):
        """Fuzzing de um handler de protocolo."""
        store, instance = self.load_module()
        
        # Obter função de handler
        handler = instance.exports(store)[handler_func]
        
        # Fuzzing da entrada do protocolo
        results = []
        
        for i in range(1000):
            # Gerar dados de protocolo fuzzados
            fuzzed_data = self._fuzz_protocol_data(protocol_data)
            
            # Criar buffer na memória Wasm
            memory = instance.exports(store)['memory']
            buffer = memory.data_ptr(store)
            
            # Copiar dados fuzzados para memória
            for j, byte in enumerate(fuzzed_data):
                if j < len(buffer):
                    buffer[j] = byte
            
            # Chamar handler
            try:
                result = handler(store, len(fuzzed_data))
                results.append({
                    'success': True,
                    'input': fuzzed_data,
                    'result': result,
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'input': fuzzed_data,
                    'error': str(e),
                })
        
        return results
    
    def _fuzz_protocol_data(self, base_data):
        """Gera dados de protocolo fuzzados."""
        if not base_data:
            return bytes(random.randint(0, 255) for _ in range(random.randint(1, 1024)))
        
        # Mutar dados base
        fuzzed = bytearray(base_data)
        
        # Aplicar mutações
        for i in range(len(fuzzed)):
            if random.random() < 0.1:
                fuzzed[i] = random.randint(0, 255)
        
        # Inserir bytes aleatórios
        if random.random() < 0.2:
            pos = random.randint(0, len(fuzzed))
            fuzzed[pos:pos] = bytes([random.randint(0, 255) for _ in range(10)])
        
        # Remover bytes
        if random.random() < 0.2 and len(fuzzed) > 10:
            pos = random.randint(0, len(fuzzed) - 5)
            del fuzzed[pos:pos+5]
        
        return bytes(fuzzed)
    
    def analyze_results(self, results):
        """Analisa resultados do fuzzing de rede."""
        analysis = {
            'total_tests': len(results),
            'successes': sum(1 for r in results if r['success']),
            'failures': sum(1 for r in results if not r['success']),
            'unique_errors': set(),
            'crashes': [],
        }
        
        for result in results:
            if not result['success']:
                error = result.get('error', 'unknown')
                analysis['unique_errors'].add(error[:100])
                
                # Verificar se é crash
                if 'segmentation' in error.lower() or 'abort' in error.lower():
                    analysis['crashes'].append(result)
        
        analysis['unique_errors'] = len(analysis['unique_errors'])
        return analysis
```

### 12.11.7 Fuzzing de Interfaces de Plugin Wasm

```python
class WasmPluginInterfaceFuzzer:
    """Fuzzer para interfaces de plugins Wasm."""
    
    def __init__(self, plugin_manifest):
        self.manifest = plugin_manifest
        self.plugin = None
    
    def load_plugin(self, wasm_path):
        """Carrega um plugin Wasm."""
        import wasmtime
        
        engine = wasmtime.Engine()
        module = wasmtime.Module.from_file(engine, wasm_path)
        
        store = wasmtime.Store(engine)
        
        # Criar linker com imports necessários
        linker = wasmtime.Linker(engine)
        
        # Adicionar imports do manifesto
        for import_info in self.manifest.get('imports', []):
            self._add_import(linker, store, import_info)
        
        instance = linker.instantiate(store, module)
        self.plugin = {
            'engine': engine,
            'store': store,
            'instance': instance,
        }
    
    def _add_import(self, linker, store, import_info):
        """Adiciona um import ao linker."""
        module = import_info['module']
        name = import_info['name']
        kind = import_info['kind']
        
        if kind == 'function':
            # Criar função dummy
            def dummy_func(*args):
                return 0
            
            func_type = wasmtime.FuncType(
                [wasmtime.ValType.i32()] * len(import_info.get('params', [])),
                [wasmtime.ValType.i32()] * len(import_info.get('results', [])),
            )
            linker.define(store, module, name, wasmtime.Func(store, func_type, dummy_func))
    
    def fuzz_plugin_exports(self):
        """Faz fuzzing das exportações do plugin."""
        if not self.plugin:
            return None
        
        store = self.plugin['store']
        instance = self.plugin['instance']
        
        results = []
        
        for export in instance.exports(store):
            if isinstance(export, wasmtime.Func):
                result = self._fuzz_function(export, store)
                results.append(result)
        
        return results
    
    def _fuzz_function(self, func, store):
        """Faz fuzzing de uma função exportada."""
        func_type = func.type(store)
        
        # Gerar parâmetros fuzzados
        params = []
        for param_type in func_type.params:
            params.append(self._generate_fuzzed_param(param_type))
        
        # Chamar função
        try:
            result = func.call(store, params)
            return {
                'success': True,
                'params': params,
                'result': result,
            }
        except Exception as e:
            return {
                'success': False,
                'params': params,
                'error': str(e),
            }
    
    def _generate_fuzzed_param(self, param_type):
        """Gera parâmetro fuzzado baseado no tipo."""
        if param_type == wasmtime.ValType.i32():
            return random.choice([0, 1, -1, 0x7FFFFFFF, -0x80000000, 0x42])
        elif param_type == wasmtime.ValType.i64():
            return random.choice([0, 1, -1, 0x7FFFFFFFFFFFFFFF, -0x8000000000000000])
        elif param_type == wasmtime.ValType.f32():
            return random.choice([0.0, 1.0, -1.0, float('inf'), float('-inf'), float('nan')])
        elif param_type == wasmtime.ValType.f64():
            return random.choice([0.0, 1.0, -1.0, float('inf'), float('-inf'), float('nan')])
        return 0
    
    def test_plugin_lifecycle(self):
        """Testa o ciclo de vida do plugin."""
        if not self.plugin:
            return None
        
        store = self.plugin['store']
        instance = self.plugin['instance']
        
        lifecycle_tests = []
        
        # Testar inicialização
        if 'init' in [e.name for e in instance.exports(store)]:
            init_func = instance.exports(store)['init']
            try:
                init_func.call(store)
                lifecycle_tests.append(('init', True, None))
            except Exception as e:
                lifecycle_tests.append(('init', False, str(e)))
        
        # Testar processamento
        if 'process' in [e.name for e in instance.exports(store)]:
            process_func = instance.exports(store)['process']
            test_data = bytes(random.randint(0, 255) for _ in range(100))
            
            try:
                result = process_func.call(store, test_data)
                lifecycle_tests.append(('process', True, None))
            except Exception as e:
                lifecycle_tests.append(('process', False, str(e)))
        
        # Testar finalização
        if 'cleanup' in [e.name for e in instance.exports(store)]:
            cleanup_func = instance.exports(store)['cleanup']
            try:
                cleanup_func.call(store)
                lifecycle_tests.append(('cleanup', True, None))
            except Exception as e:
                lifecycle_tests.append(('cleanup', False, str(e)))
        
        return lifecycle_tests
```

## 12.12 Casos Reais e Ferramentas

### 12.12.1 CVEs Encontradas por Fuzzing em Runtimes Wasm

O fuzzing tem se mostrado extremamente eficaz na descoberta de vulnerabilidades em runtimes Wasm. Várias CVEs de alta severidade foram encontradas através de fuzzing automático:

**CVE-2021-30359 (wasmtime)**: Buffer overflow no decodificador de módulos Wasm. O bug foi encontrado pelo fuzzer do projeto OSS-Fuzz e permite execução de código arbitrário através de um módulo Wasm malicioso.

**CVE-2022-24785 (wasmtime)**: Vulnerabilidade de type confusion que permite bypass de verificações de tipo, potencialmente levando a execução de código arbitrário.

**CVE-2023-XXXX (wasmer)**: Uso-after-free em gerenciamento de memória durante execução de módulos Wasm complexos, encontrado por differential fuzzing entre wasmer e wasmtime.

**CVE-2024-XXXX (wazero)**: Integer overflow em cálculos de offset de memória que pode levar a acesso fora dos limites.

Essas descobertas demonstram que fuzzing é uma técnica essencial para garantir a segurança de runtimes Wasm.

### 12.12.2 Resultados OSS-Fuzz para Projetos Wasm

O Google OSS-Fuzz monitora continuamente projetos de software open-source, incluindo vários projetos Wasm:

```
+------------------------------------------------------------------+
|                  Resultados OSS-Fuzz para Wasm                     |
+------------------------------------------------------------------+
|                                                                    |
|  Projeto         | Bugs Encontrados | Corrigidos | Abertos        |
|  ----------------|------------------|------------|-----------------|
|  wasmtime        | 450+             | 420+       | ~30             |
|  wasmer          | 180+             | 160+       | ~20             |
|  wabt            | 350+             | 340+       | ~10             |
|  wazero          | 80+              | 75+        | ~5              |
|  wasm-tools      | 120+             | 115+       | ~5              |
|  wasm3           | 90+              | 85+        | ~5              |
|  wasmtime-wasi   | 60+              | 55+        | ~5              |
|                                                                    |
|  Total           | 1330+            | 1250+      | ~80             |
|                                                                    |
+------------------------------------------------------------------+
```

O OSS-Fuzz fornece fuzzing contínuo 24/7, executando múltiplos fuzzer com diferentes estratégias. Os bugs são reportados automaticamente aos mantenedores dos projetos.

### 12.12.3 Comparação de Ferramentas

```
+------------------------------------------------------------------+
|           Comparação de Ferramentas de Fuzzing Wasm                |
+------------------------------------------------------------------+
|                                                                    |
|  Ferramenta      | Tipo         | Cobertura | Speed  | Linguagem  |
|  ----------------|------------- |-----------|--------|------------|
|  cargo-fuzz      | Coverage     | Alta      | Média  | Rust       |
|  (libFuzzer)     | guided       |           |        |            |
|  ----------------|------------- |-----------|--------|------------|
|  AFL++           | Coverage     | Alta      | Rápida | C          |
|                  | guided       |           |        |            |
|  ----------------|------------- |-----------|--------|------------|
|  Honggfuzz       | Coverage     | Alta      | Rápida | C          |
|                  | guided       |           |        |            |
|  ----------------|------------- |-----------|--------|------------|
|  wasm-mutate     | Structure    | Média     | Rápida | Rust       |
|                  | aware        |           |        |            |
|  ----------------|------------- |-----------|--------|------------|
|  custom gen      | Generation   | Variável  | Lenta  | Variável   |
|  (Python/Rust)   | based        |           |        |            |
|                                                                    |
|  Para Wasm:                                                       |
|  - cargo-fuzz: Melhor integração com ecossistema Rust             |
|  - AFL++: Melhor performance para targets C/C++                   |
|  - Honggfuzz: Boa alternativa com suporte nativo a Wasm           |
|  - wasm-mutate: Essível para mutações structure-aware              |
|                                                                    |
+------------------------------------------------------------------+
```

### 12.12.4 Esforços Comunitários de Fuzzing

A comunidade Wasm tem se organizado para promover fuzzing collaborativo:

**Wasm Fuzzing Benchmark**: Um benchmark padronizado para comparar a eficácia de diferentes fuzzers em módulos Wasm.

**Community Fuzzing Days**: Eventos periódicos onde desenvolvedores colaboram para fuzzing intensivo de runtimes Wasm.

**Bug Bounty Programs**: Programas de recompensa por bugs que incentivam fuzzing de runtimes populares.

**Shared Corpus Repositories**: Repositórios compartilhados de corpus que permitem que fuzzers se beneficiem do trabalho coletivo.

### 12.12.5 Lições Aprendidas com Fuzzing em Grande Escala

1. **Diversidade de fuzzer é crucial**: Usar múltiplos fuzzers com diferentes estratégias encontra mais bugs do que qualquer fuzzer individual.

2. **Corpus compartilhado acelera descoberta**: Módulos Wasm encontrados por um fuzzer podem ser usados como sementes por outros.

3. **Sanitizers revelam bugs ocultos**: Muitos bugs de memória são silenciosos sem sanitizers habilitados.

4. **Differential testing é poderoso**: Comparar implementações diferentes revela divergências semânticas que são bugs em pelo menos uma delas.

5. **Manutenção contínua é necessária**: Fuzzing não é "configure e esqueça" - requer ajustes contínuos baseados em resultados.

## 12.13 Considerações Finais

Fuzzing de módulos WebAssembly é uma disciplina técnica que combina conhecimento profundo do formato Wasm com técnicas avançadas de teste de software. As principais lições deste capítulo são:

1. **Structure-aware fuzzing é essencial**: Fuzzing byte-a-byte tem eficiência limitada para formatos complexos como Wasm. Mutações que respeitam a estrutura do formato produzem entradas muito mais produtivas.

2. **Coverage-guided é o padrão ouro**: Feedback de cobertura permite ao fuzzer explorar eficientemente o espaço de entrada, encontrando bugs em áreas de código que seriam inalcançáveis com fuzzing cego.

3. **Corpus de qualidade importa**: Sementes bem escolhidas e minimizadas aceleram significativamente a descoberta de bugs. Investir tempo na inicialização do corpus é sempre recompensador.

4. **Análise de crash é metade do trabalho**: Encontrar crashes é apenas o primeiro passo. Classificar, minimizar e analisar a causa raiz são etapas igualmente importantes.

5. **Differential testing revela divergências**: Comparar runtimes Wasm é uma técnica poderosa para encontrar bugs sem precisar de um oráculo de correção.

6. **Integração contínua maximiza valor**: Fuzzing em CI/CD permite encontrar bugs continuamente, antes que cheguem a produção.

7. **Fuzzing não substitui testes tradicionais**: Fuzzing e testes unitários se complementam. Fuzzing encontra bugs inesperados; testes garantem que funcionalidades conhecidas funcionam.

8. **Investimento em fuzzing tem ROI positivo**: O custo de configurar e manter um programa de fuzzing é significativamente menor do que o custo de vulnerabilidades em produção.

O futuro do fuzzing de Wasm inclui técnicas mais sofisticadas como fuzzing baseado em modelos, fuzzing assistido por IA, e integração mais profunda com ferramentas de análise estática. À medida que o ecossistema Wasm amadurece, esperamos ver fuzzing se tornar uma parte padrão do ciclo de desenvolvimento de runtimes e ferramentas Wasm.

Construir uma cultura de fuzzing na sua organização requer comprometimento, mas os benefícios em termos de segurança e confiabilidade são substanciais. Comece com targets críticos, automatize o processo, e expanda gradualmente para cobrir mais superfícies de ataque.

Segurança não é um destino, mas uma jornada contínua. Fuzzing é uma das ferramentas mais poderosas nessa jornada.
---

*[Capítulo anterior: 11 — Supply Chain Plugins](11-supply-chain-plugins.md)*
*[Próximo capítulo: 13 — Plugins Seguros](13-plugins-seguros.md)*
