# Capítulo 9: Memory Safety em WebAssembly

## 9.1 Introdução à Segurança de Memória

Segurança de memória é um dos aspectos mais críticos de segurança em software. Bugs de memória, como buffer overflows, use-after-free e null pointer dereferences, representam historicamente uma grande porção das vulnerabilidades de segurança encontradas em sistemas de software. De acordo com estudos da Microsoft e do Google, aproximadamente 70% das vulnerabilidades de segurança são causadas por erros de memória.

WebAssembly foi projetado com segurança de memória como um de seus princípios fundamentais. O modelo de memória linear do Wasm, combinado com verificações de limites em tempo de execução, fornece uma camada significativa de proteção contra muitos tipos de bugs de memória. No entanto, a segurança de memória em Wasm não é absoluta e requer entendimento cuidadoso das suas capacidades e limitações.

### 9.1.1 Por que Segurança de Memória Importa em Wasm

Apesar das proteções nativas do Wasm, ainda existem várias razões pelas quais segurança de memória é importante:

**Código compilado de C/C++**: Muitos módulos Wasm são compilados de C ou C++ usando Emscripten ou similar. Essas linguagens não possuem segurança de memória intrínseca.

**Bibliotecas de terceiros**: Componentes Wasm frequentemente dependem de bibliotecas que podem conter bugs de memória.

**Interação com WASI**: Chamadas para WASI podem expor vulnerabilidades se os buffers não forem gerenciados corretamente.

**Complexidade crescente**: Aplicações Wasm cada vez mais complexas aumentam a superfície de ataque.

### 9.1.2 Categorias de Bugs de Memória

Understanding memory safety requires knowledge of the main categories of memory bugs:

**Buffer Overflow/Underflow**: Acesso a memória fora dos limites de um buffer alocado.

```c
// Exemplo de buffer overflow em C
void vulnerable_function(char *input) {
    char buffer[64];
    // Perigoso: sem verificação de tamanho
    strcpy(buffer, input);  // Se input > 64 bytes, overflow
}

// Exemplo de buffer underflow
void underflow_example(int *array, int index) {
    // Se index < 0, acesso inválido
    int value = array[index - 1];
}
```

**Use-After-Free**: Acesso a memória que já foi liberada.

```c
// Exemplo de use-after-free
void use_after_free_example() {
    char *ptr = malloc(100);
    free(ptr);
    
    // Perigoso: ptr ainda aponta para memória liberada
    strcpy(ptr, "data");  // Use-after-free
}
```

**Double Free**: Liberar a mesma memória duas vezes.

```c
// Exemplo de double free
void double_free_example() {
    char *ptr = malloc(100);
    free(ptr);
    free(ptr);  // Double free - comportamento indefinido
}
```

**Null Pointer Dereference**: Acessar memória através de um ponteiro nulo.

```c
// Exemplo de null pointer dereference
void null_dereference_example(char *ptr) {
    if (ptr == NULL) {
        // Mesmo com verificação, pode haver race condition
    }
    *ptr = 'a';  // Se ptr é NULL, crash
}
```

**Memory Leak**: Falha em liberar memória alocada.

```c
// Exemplo de memory leak
void memory_leak_example() {
    while (1) {
        char *ptr = malloc(1024);
        // Nunca é liberado - memory leak
        if (some_condition()) {
            break;
        }
    }
}
```

## 9.2 Modelo de Memória Linear

O modelo de memória linear é o coração do sistema de memória do WebAssembly. Ele fornece um espaço de endereço contíguo e isolado que é acessível apenas pelo módulo Wasm.

### 9.2.1 Estrutura da Memória Linear

A memória linear do Wasm é composta por páginas de 64KB cada. O tamanho da memória pode ser dinamicamente ajustado, mas sempre permanece como um ArrayBuffer contíguo.

```wasm
;; Declaração de memória no Wasm
(module
  ;; Memória inicial com 1 página (64KB), exportada
  (memory (export "memory") 1)
  
  ;; Memória com tamanho máximo (256 páginas = 16MB)
  (memory 1 256)
  
  ;; Função que demonstra acesso à memória
  (func $read_byte (param $offset i32) (result i32)
    local.get $offset
    i32.load8_u  ;; Ler byte sem sinal
  )
  
  (func $write_byte (param $offset i32) (param $value i32)
    local.get $offset
    local.get $value
    i32.store8  ;; Escrever byte
  )
  
  ;; Função com verificação manual de limites
  (func $safe_read (param $offset i32) (param $size i32) (result i32)
    ;; Verificar se o acesso está dentro dos limites
    local.get $offset
    local.get $size
    i32.add
    memory.size
    i32.const 65536  ;; Tamanho de uma página
    i32.mul
    i32.le_u
    
    if (result i32)
      local.get $offset
      i32.load
    else
      i32.const -1  ;; Erro: acesso fora dos limites
    end
  )
  
  ;; Exportar memória para acesso externo
  (export "memory" (memory 0))
)
```

### 9.2.2 Gerenciamento de Memória em Rust

Rust fornece garantias de segurança de memória em compile time através do borrow checker, que se traduz em código Wasm seguro:

```rust
use wasm_bindgen::prelude::*;

// Gerenciador de memória seguro para Wasm
#[wasm_bindgen]
pub struct MemoryManager {
    buffer: Vec<u8>,
    initialized: bool,
}

#[wasm_bindgen]
impl MemoryManager {
    #[wasm_bindgen(constructor)]
    pub fn new(initial_size: usize) -> Self {
        Self {
            buffer: vec![0; initial_size],
            initialized: true,
        }
    }
    
    // Leitura segura com verificação de limites
    pub fn read(&self, offset: usize, length: usize) -> Result<Vec<u8>, String> {
        if offset + length > self.buffer.len() {
            return Err(format!(
                "Acesso fora dos limites: offset={}, length={}, buffer_size={}",
                offset, length, self.buffer.len()
            ));
        }
        
        if !self.initialized {
            return Err("Memória não inicializada".to_string());
        }
        
        Ok(self.buffer[offset..offset + length].to_vec())
    }
    
    // Escrita segura com verificação de limites
    pub fn write(&mut self, offset: usize, data: &[u8]) -> Result<(), String> {
        if offset + data.len() > self.buffer.len() {
            return Err(format!(
                "Acesso fora dos limites: offset={}, data_len={}, buffer_size={}",
                offset, data.len(), self.buffer.len()
            ));
        }
        
        if !self.initialized {
            return Err("Memória não inicializada".to_string());
        }
        
        // Copiar dados de forma segura
        self.buffer[offset..offset + data.len()].copy_from_slice(data);
        Ok(())
    }
    
    // Redimensionar memória de forma segura
    pub fn resize(&mut self, new_size: usize) -> Result<(), String> {
        if new_size == 0 {
            return Err("Tamanho deve ser maior que zero".to_string());
        }
        
        self.buffer.resize(new_size, 0);
        Ok(())
    }
    
    // Obter tamanho atual
    pub fn size(&self) -> usize {
        self.buffer.len()
    }
    
    // Preencher memória com valor específico
    pub fn fill(&mut self, offset: usize, length: usize, value: u8) -> Result<(), String> {
        if offset + length > self.buffer.len() {
            return Err("Acesso fora dos limites".to_string());
        }
        
        for i in offset..offset + length {
            self.buffer[i] = value;
        }
        
        Ok(())
    }
    
    // Copiar dados dentro da memória (com tratamento de overlap)
    pub fn copy(&mut self, dst: usize, src: usize, length: usize) -> Result<(), String> {
        if src + length > self.buffer.len() || dst + length > self.buffer.len() {
            return Err("Acesso fora dos limites".to_string());
        }
        
        // Rust lida automaticamente com overlap usando copy_within
        if dst > src {
            // Copiar de trás para frente para evitar overwrite
            for i in (0..length).rev() {
                self.buffer[dst + i] = self.buffer[src + i];
            }
        } else {
            // Copiar de frente para trás
            for i in 0..length {
                self.buffer[dst + i] = self.buffer[src + i];
            }
        }
        
        Ok(())
    }
}

// Implementação de allocador seguro
#[wasm_bindgen]
pub struct SafeAllocator {
    memory: Vec<u8>,
    allocated: Vec<(usize, usize)>, // (offset, size)
    next_free: usize,
}

#[wasm_bindgen]
impl SafeAllocator {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Self {
        Self {
            memory: vec![0; capacity],
            allocated: Vec::new(),
            next_free: 0,
        }
    }
    
    // Alocar memória de forma segura
    pub fn alloc(&mut self, size: usize) -> Result<usize, String> {
        // Verificar se há espaço disponível
        let aligned_size = (size + 7) & !7; // Alinhar em 8 bytes
        
        if self.next_free + aligned_size > self.memory.len() {
            return Err("Memória insuficiente".to_string());
        }
        
        let offset = self.next_free;
        self.next_free += aligned_size;
        
        self.allocated.push((offset, size));
        
        Ok(offset)
    }
    
    // Liberar memória de forma segura
    pub fn free(&mut self, offset: usize) -> Result<(), String> {
        if let Some(pos) = self.allocated.iter().position(|&(o, _)| o == offset) {
            self.allocated.remove(pos);
            Ok(())
        } else {
            Err(format!("Tentativa de liberar memória não alocada: {}", offset))
        }
    }
    
    // Verificar se um offset está alocado
    pub fn is_allocated(&self, offset: usize) -> bool {
        self.allocated.iter().any(|&(o, _)| o == offset)
    }
    
    // Obter tamanho de uma alocação
    pub fn allocation_size(&self, offset: usize) -> Result<usize, String> {
        self.allocated.iter()
            .find(|&&(o, _)| o == offset)
            .map(|&(_, s)| s)
            .ok_or_else(|| format!("Alocação não encontrada: {}", offset))
    }
}
```

### 9.2.3 Memória em AssemblyScript

AssemblyScript oferece segurança de memória através de verificações em tempo de execução:

```typescript
// assembly/index.ts
import { memory } from "wasm";

// Alocador de memória seguro
export class SafeAllocator {
    private buffer: StaticArray<u8>;
    private size: i32;
    private used: i32;
    private allocations: Map<i32, i32>; // offset -> size
    
    constructor(initialSize: i32) {
        this.buffer = new StaticArray<u8>(initialSize);
        this.size = initialSize;
        this.used = 0;
        this.allocations = new Map<i32, i32>();
    }
    
    // Alocar memória com verificação de limites
    alloc(size: i32): i32 {
        // Alinhar em 8 bytes
        const alignedSize = (size + 7) & ~7;
        
        if (this.used + alignedSize > this.size) {
            throw new Error("Memória insuficiente");
        }
        
        const offset = this.used;
        this.used += alignedSize;
        
        this.allocations.set(offset, size);
        
        return offset;
    }
    
    // Liberar memória com verificação
    free(offset: i32): void {
        if (!this.allocations.has(offset)) {
            throw new Error(`Tentativa de liberar memória não alocada: ${offset}`);
        }
        
        this.allocations.delete(offset);
    }
    
    // Leitura segura
    read(offset: i32, length: i32): StaticArray<u8> {
        if (offset < 0 || offset + length > this.size) {
            throw new Error("Acesso fora dos limites");
        }
        
        if (!this.allocations.has(offset)) {
            throw new Error("Leitura de memória não alocada");
        }
        
        const result = new StaticArray<u8>(length);
        for (let i: i32 = 0; i < length; i++) {
            unchecked(result[i] = this.buffer[offset + i]);
        }
        
        return result;
    }
    
    // Escrita segura
    write(offset: i32, data: StaticArray<u8>): void {
        if (offset < 0 || offset + data.length > this.size) {
            throw new Error("Acesso fora dos limites");
        }
        
        if (!this.allocations.has(offset)) {
            throw new Error("Escrita em memória não alocada");
        }
        
        for (let i: i32 = 0; i < data.length; i++) {
            unchecked(this.buffer[offset + i] = data[i]);
        }
    }
    
    // Verificar se um offset está alocado
    isAllocated(offset: i32): bool {
        return this.allocations.has(offset);
    }
    
    // Obter tamanho de uma alocação
    allocationSize(offset: i32): i32 {
        if (!this.allocations.has(offset)) {
            throw new Error("Alocação não encontrada");
        }
        
        return this.allocations.get(offset);
    }
    
    // Verificar integridade da memória
    checkIntegrity(): bool {
        let totalAllocated: i32 = 0;
        
        const entries = this.allocations.entries();
        while (!entries.done) {
            const entry = entries.next();
            totalAllocated += entry.value.value;
        }
        
        return totalAllocated <= this.used;
    }
}

// Buffer com verificação de limites
export class SafeBuffer {
    private data: StaticArray<u8>;
    private length: i32;
    private capacity: i32;
    
    constructor(capacity: i32) {
        this.data = new StaticArray<u8>(capacity);
        this.length = 0;
        this.capacity = capacity;
    }
    
    // Escrever dados com verificação
    write(offset: i32, data: StaticArray<u8>): i32 {
        if (offset < 0 || offset > this.length) {
            throw new Error("Offset inválido");
        }
        
        const available = this.capacity - offset;
        const toWrite = min(data.length, available);
        
        if (toWrite < data.length) {
            throw new Error("Buffer cheio");
        }
        
        for (let i: i32 = 0; i < toWrite; i++) {
            unchecked(this.data[offset + i] = data[i]);
        }
        
        this.length = max(this.length, offset + toWrite);
        
        return toWrite;
    }
    
    // Ler dados com verificação
    read(offset: i32, length: i32): StaticArray<u8> {
        if (offset < 0 || offset >= this.length) {
            throw new Error("Offset inválido");
        }
        
        const available = this.length - offset;
        const toRead = min(length, available);
        
        const result = new StaticArray<u8>(toRead);
        for (let i: i32 = 0; i < toRead; i++) {
            unchecked(result[i] = this.data[offset + i]);
        }
        
        return result;
    }
    
    // Resetar buffer
    clear(): void {
        this.length = 0;
    }
    
    // Obter tamanho atual
    getLength(): i32 {
        return this.length;
    }
    
    // Obter capacidade
    getCapacity(): i32 {
        return this.capacity;
    }
}
```

## 9.3 Bounds Checking

Bounds checking é a verificação de que acessos a memória estão dentro dos limites de buffers ou áreas de memória alocadas. No Wasm, isso é implementado em múltiplos níveis.

### 9.3.1 Bounds Checking no Runtime

O runtime Wasm implementa bounds checking para todas as operações de memória:

```wasm
;; Exemplo de bounds checking implícito
(module
  (memory (export "memory") 1)
  
  ;; Esta função causará trap se o índice for inválido
  (func $unsafe_access (param $index i32) (result i32)
    local.get $index
    i32.load  ;; Trap se index >= memory.size * 64KB
  )
  
  ;; Bounds checking manual explícito
  (func $safe_access (param $index i32) (result i32)
    ;; Verificar se o índice está dentro dos limites
    local.get $index
    i32.const 0
    i32.ge_s  ;; index >= 0
    
    local.get $index
    memory.size
    i32.const 65536
    i32.mul
    i32.const 4
    i32.sub
    i32.le_s  ;; index <= memory.size * 64KB - 4
    
    i32.and
    
    if (result i32)
      local.get $index
      i32.load
    else
      i32.const 0  ;; Retornar valor seguro em caso de erro
    end
  )
  
  ;; Bounds checking com mensagem de erro
  (func $checked_access (param $index i32) (param $buffer_size i32) (result i32)
    ;; Verificar lower bound
    local.get $index
    i32.const 0
    i32.lt_s
    
    if
      i32.const 0  ;; Erro: índice negativo
      return
    end
    
    ;; Verificar upper bound
    local.get $index
    local.get $buffer_size
    i32.ge_s
    
    if
      i32.const 0  ;; Erro: índice >= tamanho do buffer
      return
    end
    
    ;; Acesso seguro
    local.get $index
    i32.load
  )
)
```

### 9.3.2 Bounds Checking em C/C++ (Emscripten)

Quando compilamos C/C++ para Wasm, precisamos garantir que o código faça bounds checking adequado:

```c
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// Estrutura para buffer seguro
typedef struct {
    void *data;
    size_t size;
    size_t capacity;
    int initialized;
} SafeBuffer;

// Criar buffer seguro
SafeBuffer* safe_buffer_create(size_t initial_capacity) {
    SafeBuffer *buf = (SafeBuffer*)malloc(sizeof(SafeBuffer));
    if (!buf) return NULL;
    
    buf->data = malloc(initial_capacity);
    if (!buf->data) {
        free(buf);
        return NULL;
    }
    
    buf->size = 0;
    buf->capacity = initial_capacity;
    buf->initialized = 1;
    
    return buf;
}

// Liberar buffer seguro
void safe_buffer_destroy(SafeBuffer *buf) {
    if (buf && buf->initialized) {
        // Limpar dados sensíveis antes de liberar
        if (buf->data) {
            memset(buf->data, 0, buf->capacity);
            free(buf->data);
        }
        memset(buf, 0, sizeof(SafeBuffer));
        free(buf);
    }
}

// Leitura segura com bounds checking
int safe_buffer_read(SafeBuffer *buf, size_t offset, void *dest, size_t length) {
    if (!buf || !buf->initialized || !buf->data) {
        return -1;  // Buffer inválido
    }
    
    if (offset + length > buf->size) {
        return -2;  // Acesso fora dos limites
    }
    
    if (dest == NULL) {
        return -3;  // Destino inválido
    }
    
    memcpy(dest, (char*)buf->data + offset, length);
    return 0;  // Sucesso
}

// Escrita segura com bounds checking
int safe_buffer_write(SafeBuffer *buf, size_t offset, const void *src, size_t length) {
    if (!buf || !buf->initialized || !buf->data) {
        return -1;  // Buffer inválido
    }
    
    if (src == NULL) {
        return -2;  // Fonte inválida
    }
    
    // Verificar se precisa redimensionar
    if (offset + length > buf->capacity) {
        size_t new_capacity = buf->capacity * 2;
        while (new_capacity < offset + length) {
            new_capacity *= 2;
        }
        
        void *new_data = realloc(buf->data, new_capacity);
        if (!new_data) {
            return -3;  // Falha ao redimensionar
        }
        
        // Limpar nova memória
        memset((char*)new_data + buf->capacity, 0, new_capacity - buf->capacity);
        
        buf->data = new_data;
        buf->capacity = new_capacity;
    }
    
    memcpy((char*)buf->data + offset, src, length);
    
    // Atualizar tamanho se necessário
    if (offset + length > buf->size) {
        buf->size = offset + length;
    }
    
    return 0;  // Sucesso
}

// Função para demostrar bounds checking
void demonstrate_bounds_checking() {
    SafeBuffer *buf = safe_buffer_create(1024);
    if (!buf) {
        fprintf(stderr, "Falha ao criar buffer\n");
        return;
    }
    
    // Escrever dados
    const char *message = "Hello, WebAssembly!";
    int result = safe_buffer_write(buf, 0, message, strlen(message) + 1);
    if (result != 0) {
        fprintf(stderr, "Erro ao escrever: %d\n", result);
        safe_buffer_destroy(buf);
        return;
    }
    
    // Ler dados dentro dos limites
    char read_buf[64];
    result = safe_buffer_read(buf, 0, read_buf, strlen(message) + 1);
    if (result == 0) {
        printf("Lido com sucesso: %s\n", read_buf);
    }
    
    // Tentar ler fora dos limites (deve falhar)
    result = safe_buffer_read(buf, 100, read_buf, 64);
    if (result != 0) {
        printf("Acesso fora dos limites detectado corretamente: %d\n", result);
    }
    
    safe_buffer_destroy(buf);
}

// WASI bindings para uso em Wasm
#include <wasi/api.h>

__wasi_errno_t wasm_safe_read(
    __wasi_fd_t fd,
    void *buffer,
    size_t buffer_len,
    size_t *bytes_read
) {
    // Verificar se o buffer é válido
    if (buffer == NULL || bytes_read == NULL) {
        return __WASI_ERRNO_INVAL;
    }
    
    // Verificar se o tamanho é razoável
    if (buffer_len > 1024 * 1024) {  // Máximo 1MB
        return __WASI_ERRNO_FBIG;
    }
    
    // Ler dados usando WASI
    __wasi_iovec_t iov = {
        .buf = buffer,
        .buf_len = buffer_len
    };
    
    __wasi_errno_t err = __wasi_fd_read(fd, &iov, 1, bytes_read);
    
    return err;
}
```

### 9.3.3 Bounds Checking em Rust

Rust fornece bounds checking automático em tempo de execução:

```rust
use wasm_bindgen::prelude::*;

// Implementação de buffer seguro em Rust para Wasm
#[wasm_bindgen]
pub struct SafeBuffer {
    data: Vec<u8>,
    read_pos: usize,
    write_pos: usize,
}

#[wasm_bindgen]
impl SafeBuffer {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Self {
        Self {
            data: vec![0; capacity],
            read_pos: 0,
            write_pos: 0,
        }
    }
    
    // Leitura segura com bounds checking automático do Rust
    pub fn read(&mut self, length: usize) -> Result<Vec<u8>, String> {
        if self.read_pos + length > self.data.len() {
            return Err(format!(
                "Leitura fora dos limites: pos={}, len={}, total={}",
                self.read_pos, length, self.data.len()
            ));
        }
        
        let result = self.data[self.read_pos..self.read_pos + length].to_vec();
        self.read_pos += length;
        
        Ok(result)
    }
    
    // Leitura de posição específica
    pub fn read_at(&self, offset: usize, length: usize) -> Result<Vec<u8>, String> {
        if offset + length > self.data.len() {
            return Err(format!(
                "Leitura fora dos limites: offset={}, len={}, total={}",
                offset, length, self.data.len()
            ));
        }
        
        Ok(self.data[offset..offset + length].to_vec())
    }
    
    // Escrita segura com bounds checking
    pub fn write(&mut self, data: &[u8]) -> Result<(), String> {
        if self.write_pos + data.len() > self.data.len() {
            return Err(format!(
                "Escrita fora dos limites: pos={}, data_len={}, total={}",
                self.write_pos, data.len(), self.data.len()
            ));
        }
        
        self.data[self.write_pos..self.write_pos + data.len()].copy_from_slice(data);
        self.write_pos += data.len();
        
        Ok(())
    }
    
    // Escrita em posição específica
    pub fn write_at(&mut self, offset: usize, data: &[u8]) -> Result<(), String> {
        if offset + data.len() > self.data.len() {
            return Err(format!(
                "Escrita fora dos limites: offset={}, data_len={}, total={}",
                offset, data.len(), self.data.len()
            ));
        }
        
        self.data[offset..offset + data.len()].copy_from_slice(data);
        
        Ok(())
    }
    
    // Preencher área com valor
    pub fn fill(&mut self, offset: usize, length: usize, value: u8) -> Result<(), String> {
        if offset + length > self.data.len() {
            return Err("Acesso fora dos limites".to_string());
        }
        
        for i in offset..offset + length {
            self.data[i] = value;
        }
        
        Ok(())
    }
    
    // Copiar dados dentro do buffer (com tratamento de overlap)
    pub fn copy_within(&mut self, dst: usize, src: usize, length: usize) -> Result<(), String> {
        if src + length > self.data.len() || dst + length > self.data.len() {
            return Err("Acesso fora dos limites".to_string());
        }
        
        // Rust lida automaticamente com overlap usando copy_within
        self.data.copy_within(src..src + length, dst);
        
        Ok(())
    }
    
    // Resetar posições de leitura/escrita
    pub fn reset(&mut self) {
        self.read_pos = 0;
        self.write_pos = 0;
    }
    
    // Obter tamanho atual dos dados
    pub fn len(&self) -> usize {
        self.write_pos
    }
    
    // Verificar se está vazio
    pub fn is_empty(&self) -> bool {
        self.write_pos == 0
    }
    
    // Obter capacidade total
    pub fn capacity(&self) -> usize {
        self.data.len()
    }
    
    // Verificar integridade do buffer
    pub fn check_integrity(&self) -> bool {
        self.read_pos <= self.write_pos && self.write_pos <= self.data.len()
    }
}

// Implementação de arena allocator seguro
#[wasm_bindgen]
pub struct ArenaAllocator {
    memory: Vec<u8>,
    offset: usize,
    allocations: Vec<(usize, usize)>, // (offset, size)
}

#[wasm_bindgen]
impl ArenaAllocator {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Self {
        Self {
            memory: vec![0; capacity],
            offset: 0,
            allocations: Vec::new(),
        }
    }
    
    // Alocar memória
    pub fn alloc(&mut self, size: usize) -> Result<usize, String> {
        // Alinhar em 8 bytes
        let aligned_size = (size + 7) & !7;
        
        if self.offset + aligned_size > self.memory.len() {
            return Err("Memória insuficiente".to_string());
        }
        
        let alloc_offset = self.offset;
        self.offset += aligned_size;
        
        self.allocations.push((alloc_offset, size));
        
        Ok(alloc_offset)
    }
    
    // Liberar todas as alocações (reset da arena)
    pub fn reset(&mut self) {
        self.offset = 0;
        self.allocations.clear();
    }
    
    // Obter informações de uma alocação
    pub fn allocation_info(&self, offset: usize) -> Result<(usize, usize), String> {
        self.allocations.iter()
            .find(|&&(o, _)| o == offset)
            .map(|&(_, s)| (offset, s))
            .ok_or_else(|| format!("Alocação não encontrada: {}", offset))
    }
    
    // Verificar se um offset está alocado
    pub fn is_allocated(&self, offset: usize) -> bool {
        self.allocations.iter().any(|&(o, _)| o == offset)
    }
    
    // Obter memória disponível
    pub fn available(&self) -> usize {
        self.memory.len() - self.offset
    }
    
    // Obter memória total
    pub fn total(&self) -> usize {
        self.memory.len()
    }
}
```

## 9.4 Guard Pages

Guard pages são páginas de memória não acessíveis que são colocadas entre regiões de memória para detectar acessos fora dos limites. Elas servem como barreiras de segurança que causam trap quando acessadas.

### 9.4.1 Implementação com WASI

```c
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <wasi/api.h>

// Tamanho de uma página (64KB)
#define PAGE_SIZE 65536

// Estrutura para gerenciar guard pages
typedef struct {
    void *memory;
    size_t total_size;
    size_t usable_size;
    size_t page_count;
    int *guard_pages;  // Array de flags indicando quais páginas são guard
} GuardedMemory;

// Criar memória com guard pages
GuardedMemory* guarded_memory_create(size_t usable_size, int guard_page_interval) {
    GuardedMemory *gm = (GuardedMemory*)malloc(sizeof(GuardedMemory));
    if (!gm) return NULL;
    
    // Calcular número total de páginas (incluindo guard pages)
    size_t data_pages = (usable_size + PAGE_SIZE - 1) / PAGE_SIZE;
    size_t guard_pages_count = data_pages / guard_page_interval + 1;
    size_t total_pages = data_pages + guard_pages_count;
    
    gm->total_size = total_pages * PAGE_SIZE;
    gm->usable_size = usable_size;
    gm->page_count = total_pages;
    
    // Alocar memória usando WASI
    __wasi_size_t memory_size = gm->total_size;
    __wasi_errno_t err = __wasi_memory_grow(&memory_size);
    if (err != __WASI_ERRNO_SUCCESS) {
        free(gm);
        return NULL;
    }
    
    gm->memory = __builtin_wasm_memory_base(0);
    
    // Criar array de flags para guard pages
    gm->guard_pages = (int*)calloc(total_pages, sizeof(int));
    if (!gm->guard_pages) {
        free(gm);
        return NULL;
    }
    
    // Marcar páginas de guard
    int page_index = 0;
    for (size_t i = 0; i < data_pages; i++) {
        page_index++;
        if ((i + 1) % guard_page_interval == 0 && i + 1 < data_pages) {
            gm->guard_pages[page_index] = 1;  // É uma guard page
            page_index++;
        }
    }
    
    // Tornar guard pages inacessíveis
    for (size_t i = 0; i < total_pages; i++) {
        if (gm->guard_pages[i]) {
            void *page_start = (char*)gm->memory + (i * PAGE_SIZE);
            // Em WASI, não podemos usar mprotect diretamente
            // Mas podemos usar other mechanisms
        }
    }
    
    return gm;
}

// Liberar memória com guard pages
void guarded_memory_destroy(GuardedMemory *gm) {
    if (gm) {
        if (gm->memory) {
            // Limpar dados sensíveis
            memset(gm->memory, 0, gm->total_size);
        }
        if (gm->guard_pages) {
            free(gm->guard_pages);
        }
        free(gm);
    }
}

// Obter offset linear a partir de offset lógico (considerando guard pages)
size_t guarded_memory_translate(GuardedMemory *gm, size_t logical_offset) {
    if (logical_offset >= gm->usable_size) {
        return (size_t)-1;  // Erro
    }
    
    size_t data_page = logical_offset / PAGE_SIZE;
    size_t offset_in_page = logical_offset % PAGE_SIZE;
    
    // Contar guard pages antes desta posição
    size_t guard_pages_before = 0;
    for (size_t i = 0; i < data_page; i++) {
        int page_index = 0;
        for (size_t j = 0; j <= i; j++) {
            if (gm->guard_pages[page_index]) {
                guard_pages_before++;
            }
            page_index++;
        }
    }
    
    size_t physical_page = data_page + guard_pages_before;
    return physical_page * PAGE_SIZE + offset_in_page;
}

// Leitura segura com verificação de guard pages
int guarded_memory_read(GuardedMemory *gm, size_t offset, void *dest, size_t length) {
    if (!gm || !gm->memory || !dest) {
        return -1;
    }
    
    if (offset + length > gm->usable_size) {
        return -2;  // Acesso fora dos limites
    }
    
    // Verificar se o acesso cruza uma guard page
    size_t start_page = offset / PAGE_SIZE;
    size_t end_page = (offset + length - 1) / PAGE_SIZE;
    
    for (size_t page = start_page; page <= end_page; page++) {
        if (gm->guard_pages[page]) {
            return -3;  // Tentativa de acessar guard page
        }
    }
    
    // Traduzir offset lógico para físico
    size_t physical_offset = guarded_memory_translate(gm, offset);
    if (physical_offset == (size_t)-1) {
        return -4;
    }
    
    memcpy(dest, (char*)gm->memory + physical_offset, length);
    return 0;
}

// Escrita segura com verificação de guard pages
int guarded_memory_write(GuardedMemory *gm, size_t offset, const void *src, size_t length) {
    if (!gm || !gm->memory || !src) {
        return -1;
    }
    
    if (offset + length > gm->usable_size) {
        return -2;  // Acesso fora dos limites
    }
    
    // Verificar se o acesso cruza uma guard page
    size_t start_page = offset / PAGE_SIZE;
    size_t end_page = (offset + length - 1) / PAGE_SIZE;
    
    for (size_t page = start_page; page <= end_page; page++) {
        if (gm->guard_pages[page]) {
            return -3;  // Tentativa de acessar guard page
        }
    }
    
    // Traduzir offset lógico para físico
    size_t physical_offset = guarded_memory_translate(gm, offset);
    if (physical_offset == (size_t)-1) {
        return -4;
    }
    
    memcpy((char*)gm->memory + physical_offset, src, length);
    return 0;
}

// Função para demonstrar guard pages
void demonstrate_guard_pages() {
    GuardedMemory *gm = guarded_memory_create(1024 * 1024, 8);  // 1MB com guard a cada 8 páginas
    if (!gm) {
        fprintf(stderr, "Falha ao criar memória com guard pages\n");
        return;
    }
    
    printf("Memória criada: %zu bytes úteis, %zu bytes total\n", 
           gm->usable_size, gm->total_size);
    
    // Escrever dados
    const char *data = "Dados de teste";
    int result = guarded_memory_write(gm, 0, data, strlen(data) + 1);
    if (result == 0) {
        printf("Escrita bem-sucedida\n");
    }
    
    // Ler dados
    char read_buf[64];
    result = guarded_memory_read(gm, 0, read_buf, strlen(data) + 1);
    if (result == 0) {
        printf("Leitura: %s\n", read_buf);
    }
    
    guarded_memory_destroy(gm);
}
```

### 9.4.2 Guard Pages em Rust

```rust
use wasm_bindgen::prelude::*;

// Tamanho de página do Wasm
const PAGE_SIZE: usize = 65536;

// Estrutura para memória com guard pages
#[wasm_bindgen]
pub struct GuardedMemory {
    data: Vec<u8>,
    guard_intervals: Vec<usize>,
    usable_size: usize,
}

#[wasm_bindgen]
impl GuardedMemory {
    #[wasm_bindgen(constructor)]
    pub fn new(usable_size: usize, guard_interval: usize) -> Self {
        // Calcular número de guard pages necessárias
        let data_pages = (usable_size + PAGE_SIZE - 1) / PAGE_SIZE;
        let guard_pages = data_pages / guard_interval + 1;
        let total_size = (data_pages + guard_pages) * PAGE_SIZE;
        
        // Criar vetor com zeros
        let mut data = vec![0u8; total_size];
        
        // Marcar guard pages com padrão especial
        let mut guard_intervals = Vec::new();
        let mut current_page = 0;
        let mut guard_count = 0;
        
        for i in 0..data_pages {
            current_page += 1;
            if (i + 1) % guard_interval == 0 && i + 1 < data_pages {
                guard_intervals.push(current_page);
                current_page += 1;
                guard_count += 1;
            }
        }
        
        Self {
            data,
            guard_intervals,
            usable_size,
        }
    }
    
    // Traduzir offset lógico para físico
    fn translate_offset(&self, logical_offset: usize) -> Result<usize, String> {
        if logical_offset >= self.usable_size {
            return Err("Offset fora dos limites".to_string());
        }
        
        let logical_page = logical_offset / PAGE_SIZE;
        let offset_in_page = logical_offset % PAGE_SIZE;
        
        // Contar guard pages antes desta posição
        let guards_before = self.guard_intervals.iter()
            .filter(|&&g| g < logical_page)
            .count();
        
        let physical_page = logical_page + guards_before;
        Ok(physical_page * PAGE_SIZE + offset_in_page)
    }
    
    // Verificar se um intervalo contém guard pages
    fn contains_guard_pages(&self, start_offset: usize, length: usize) -> bool {
        let start_page = start_offset / PAGE_SIZE;
        let end_page = (start_offset + length - 1) / PAGE_SIZE;
        
        self.guard_intervals.iter()
            .any(|&g| g >= start_page && g <= end_page)
    }
    
    // Leitura segura
    pub fn read(&self, offset: usize, length: usize) -> Result<Vec<u8>, String> {
        if offset + length > self.usable_size {
            return Err("Acesso fora dos limites".to_string());
        }
        
        if self.contains_guard_pages(offset, length) {
            return Err("Acesso cruzando guard pages detectado".to_string());
        }
        
        let physical_offset = self.translate_offset(offset)?;
        
        Ok(self.data[physical_offset..physical_offset + length].to_vec())
    }
    
    // Escrita segura
    pub fn write(&mut self, offset: usize, data: &[u8]) -> Result<(), String> {
        if offset + data.len() > self.usable_size {
            return Err("Acesso fora dos limites".to_string());
        }
        
        if self.contains_guard_pages(offset, data.len()) {
            return Err("Acesso cruzando guard pages detectado".to_string());
        }
        
        let physical_offset = self.translate_offset(offset)?;
        
        self.data[physical_offset..physical_offset + data.len()].copy_from_slice(data);
        
        Ok(())
    }
    
    // Verificar se um offset está em uma guard page
    pub fn is_guard_page(&self, offset: usize) -> bool {
        let page = offset / PAGE_SIZE;
        self.guard_intervals.contains(&page)
    }
    
    // Obter tamanho útil
    pub fn usable_size(&self) -> usize {
        self.usable_size
    }
    
    // Obter tamanho total
    pub fn total_size(&self) -> usize {
        self.data.len()
    }
    
    // Obter número de guard pages
    pub fn guard_page_count(&self) -> usize {
        self.guard_intervals.len()
    }
}

// Teste da implementação
#[wasm_bindgen]
pub fn test_guarded_memory() -> Result<String, String> {
    let mut gm = GuardedMemory::new(1024 * 1024, 8);  // 1MB com guard a cada 8 páginas
    
    // Teste de escrita e leitura
    let test_data = b"Hello, Guard Pages!";
    gm.write(0, test_data)?;
    
    let read_data = gm.read(0, test_data.len())?;
    if read_data != test_data {
        return Err("Dados não conferem após leitura".to_string());
    }
    
    // Teste de detecção de guard pages
    if gm.is_guard_page(0) {
        return Err("Offset 0 não deveria ser guard page".to_string());
    }
    
    // Teste de acesso fora dos limites
    if gm.read(gm.usable_size(), 1).is_ok() {
        return Err("Deveria falhar ao acessar fora dos limites".to_string());
    }
    
    Ok("Todos os testes passaram".to_string())
}
```

## 9.5 ASLR em WebAssembly

Address Space Layout Randomization (ASLR) é uma técnica de segurança que randomiza os endereços de memória de componentes de um programa, tornando mais difícil para um atacante prever onde código ou dados específicos estão localizados.

### 9.5.1 ASLR no Contexto do Wasm

O Wasm não possui ASLR no sentido tradicional, pois a memória linear é um ArrayBuffer contíguo. No entanto, existem técnicas que podem ser aplicadas:

```rust
use wasm_bindgen::prelude::*;
use std::collections::HashMap;

// Simulação de ASLR para Wasm
#[wasm_bindgen]
pub struct WasmASLR {
    base_address: usize,
    page_offsets: HashMap<String, usize>,
    randomized_regions: Vec<(usize, usize)>,
}

#[wasm_bindgen]
impl WasmASLR {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        // Gerar endereço base aleatório
        // Em WASI, usar wasi:random
        let base_address = Self::generate_random_base();
        
        Self {
            base_address,
            page_offsets: HashMap::new(),
            randomized_regions: Vec::new(),
        }
    }
    
    // Gerar endereço base aleatório
    fn generate_random_base() -> usize {
        // Em produção, usar RNG criptograficamente seguro
        // Aqui usamos uma simulação simples
        let mut seed: usize = 0;
        
        // Usar tempo como seed (em produção, usar wasi:random)
        seed = seed.wrapping_add(12345);
        seed = seed.wrapping_mul(1103515245);
        seed = seed.wrapping_add(12345);
        
        // Garantir que está alinhado em página e não muito alto
        (seed % 0x1000) * 0x10000
    }
    
    // Mapear região com randomização
    pub fn map_region(&mut self, name: &str, size: usize) -> Result<usize, String> {
        if self.page_offsets.contains_key(name) {
            return Err(format!("Região '{}' já mapeada", name));
        }
        
        // Gerar offset aleatório dentro de um range seguro
        let random_offset = Self::generate_random_offset();
        
        // Verificar colisões
        for &(_, end) in &self.randomized_regions {
            if random_offset < end && random_offset + size > Self::get_region_start(end - 1) {
                return Err("Colisão de endereços detectada".to_string());
            }
        }
        
        let absolute_address = self.base_address + random_offset;
        
        self.page_offsets.insert(name.to_string(), absolute_address);
        self.randomized_regions.push((absolute_address, absolute_address + size));
        
        Ok(absolute_address)
    }
    
    // Obter endereço de uma região
    pub fn get_region_address(&self, name: &str) -> Result<usize, String> {
        self.page_offsets.get(name)
            .copied()
            .ok_or_else(|| format!("Região '{}' não encontrada", name))
    }
    
    // Traduzir endereço virtual para endereço real
    pub fn translate_address(&self, virtual_addr: usize) -> Result<usize, String> {
        for &(start, end) in &self.randomized_regions {
            if virtual_addr >= start && virtual_addr < end {
                return Ok(virtual_addr);
            }
        }
        
        Err("Endereço não mapeado".to_string())
    }
    
    // Verificar se um endereço está em uma região mapeada
    pub fn is_mapped(&self, address: usize) -> bool {
        self.randomized_regions.iter()
            .any(|&(start, end)| address >= start && address < end)
    }
    
    // Gerar offset aleatório
    fn generate_random_offset() -> usize {
        // Simulação - em produção usar RNG seguro
        let mut seed: usize = 42;
        seed = seed.wrapping_mul(1103515245);
        seed = seed.wrapping_add(12345);
        seed % 0x100000  // Até 1MB de offset
    }
    
    // Obter início de uma região
    fn get_region_start(addr: usize) -> usize {
        addr & !0xFFFF  // Alinhar em página
    }
    
    // Listar todas as regiões mapeadas
    pub fn list_regions(&self) -> Vec<String> {
        self.page_offsets.keys().cloned().collect()
    }
    
    // Resetar randomização
    pub fn reset(&mut self) {
        self.base_address = Self::generate_random_base();
        self.page_offsets.clear();
        self.randomized_regions.clear();
    }
}

// Gerador de números aleatórios seguro para Wasm
#[wasm_bindgen]
pub struct SecureRng {
    state: [u32; 4],
}

#[wasm_bindgen]
impl SecureRng {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        let mut rng = Self {
            state: [0; 4],
        };
        
        // Inicializar com seed pseudo-aleatória
        // Em produção, usar wasi:random/random
        rng.state[0] = 123456789;
        rng.state[1] = 362436069;
        rng.state[2] = 521288629;
        rng.state[3] = 88675123;
        
        rng
    }
    
    // Gerar próximo número aleatório usando xorshift128
    pub fn next_u32(&mut self) -> u32 {
        let mut t = self.state[3];
        let s = self.state[0];
        
        self.state[3] = self.state[2];
        self.state[2] = self.state[1];
        self.state[1] = s;
        
        t ^= t << 11;
        t ^= t >> 8;
        t ^= s;
        t ^= s >> 19;
        
        self.state[0] = t;
        
        t.wrapping_add(self.state[1])
    }
    
    // Gerar número aleatório em range
    pub fn next_range(&mut self, min: u32, max: u32) -> u32 {
        if min >= max {
            return min;
        }
        
        let range = max - min;
        let random = self.next_u32();
        
        min + (random % range)
    }
    
    // Gerar bytes aleatórios
    pub fn fill_bytes(&mut self, buffer: &mut [u8]) {
        for chunk in buffer.chunks_mut(4) {
            let random = self.next_u32();
            let bytes = random.to_le_bytes();
            
            for (i, byte) in chunk.iter_mut().enumerate() {
                if i < 4 {
                    *byte = bytes[i];
                }
            }
        }
    }
    
    // Resetar estado
    pub fn reset(&mut self) {
        self.state = [123456789, 362436069, 521288629, 88675123];
    }
}

// Teste de ASLR
#[wasm_bindgen]
pub fn test_aslr() -> Result<String, String> {
    let mut aslr = WasmASLR::new();
    
    // Mapear regiões
    let code_addr = aslr.map_region("code", 65536)?;
    let data_addr = aslr.map_region("data", 65536)?;
    let heap_addr = aslr.map_region("heap", 131072)?;
    
    // Verificar que endereços são diferentes
    if code_addr == data_addr || data_addr == heap_addr || code_addr == heap_addr {
        return Err("Endereços deveriam ser diferentes".to_string());
    }
    
    // Verificar que estão dentro do range esperado
    if code_addr < 0x10000 || code_addr > 0x1000000 {
        return Err("Endereço de código fora do range esperado".to_string());
    }
    
    // Testar tradução de endereço
    let translated = aslr.translate_address(code_addr)?;
    if translated != code_addr {
        return Err("Tradução de endereço falhou".to_string());
    }
    
    // Testar detecção de regiões não mapeadas
    if aslr.is_mapped(0x99999) {
        return Err("Endereço não mapeado foi detectado como mapeado".to_string());
    }
    
    Ok("Testes de ASLR passaram".to_string())
}
```

## 9.6 Proteção contra Stack Overflow

Stack overflow occurs when a program uses more stack space than is available. In Wasm, the stack is allocated within the linear memory and has fixed bounds.

### 9.6.1 Detecção e Prevenção

```wasm
;; Stack overflow protection no Wasm
(module
  ;; Importar funções de trap
  (import "wasi_snapshot_preview1" "proc_exit" (func $proc_exit (param i32)))
  
  ;; Variável global para limite da stack
  (global $stack_limit (mut i32) (i32.const 65536))  ;; 64KB
  
  ;; Variável global para posição atual da stack
  (global $stack_pointer (mut i32) (i32.const 0))
  
  ;; Função para alocar espaço na stack
  (func $stack_alloc (param $size i32) (result i32)
    ;; Calcular nova posição
    global.get $stack_pointer
    local.get $size
    i32.add
    
    ;; Verificar se excede o limite
    global.get $stack_limit
    i32.gt_s
    
    if
      ;; Stack overflow - chamar trap
      call $stack_overflow_trap
    end
    
    ;; Atualizar ponteiro da stack
    global.get $stack_pointer
    local.set $result
    
    global.get $stack_pointer
    local.get $size
    i32.add
    global.set $stack_pointer
    
    local.get $result
  )
  
  ;; Função para liberar espaço da stack
  (func $stack_free (param $size i32)
    global.get $stack_pointer
    local.get $size
    i32.sub
    global.set $stack_pointer
  )
  
  ;; Função de trap para stack overflow
  (func $stack_overflow_trap
    ;; Em produção, usar handler de erro apropriado
    i32.const 1
    call $proc_exit
  )
  
  ;; Função recursiva com proteção
  (func $safe_recursive (param $n i32) (result i32)
    ;; Alocar frame na stack
    i32.const 16
    call $stack_alloc
    drop
    
    ;; Verificar caso base
    local.get $n
    i32.const 0
    i32.le_s
    
    if (result i32)
      i32.const 1
    else
      ;; Chamada recursiva
      local.get $n
      i32.const 1
      i32.sub
      call $safe_recursive
      
      ;; Multiplicar pelo nível atual
      local.get $n
      i32.mul
    end
    
    ;; Liberar frame da stack
    i32.const 16
    call $stack_free
  )
  
  ;; Função com loop para evitar recursão profunda
  (func $iterative_factorial (param $n i32) (result i32)
    (local $result i32)
    (local $i i32)
    
    i32.const 1
    local.set $result
    
    i32.const 1
    local.set $i
    
    block $break
      loop $continue
        local.get $i
        local.get $n
        i32.gt_s
        
        br_if $break
        
        local.get $result
        local.get $i
        i32.mul
        local.set $result
        
        local.get $i
        i32.const 1
        i32.add
        local.set $i
        
        br $continue
      end
    end
    
    local.get $result
  )
)
```

### 9.6.2 Stack Protection em C/C++ (Emscripten)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>

// Configurações de stack
#define STACK_SIZE (1024 * 1024)  // 1MB
#define STACK_GUARD_SIZE (4096)   // 4KB guard page
#define STACK_WARNING_THRESHOLD (STACK_SIZE - STACK_GUARD_SIZE - 1024)

// Variáveis para monitoramento de stack
static void *stack_base = NULL;
static size_t stack_size = 0;

// Inicializar monitoramento de stack
void init_stack_monitor() {
    // Obter endereço da stack (em Wasm, isso pode ser diferente)
    // Em produção, usar information from runtime
    
    stack_base = __builtin_frame_address(0);
    stack_size = STACK_SIZE;
    
    printf("Stack monitor inicializado: base=%p, size=%zu\n", 
           stack_base, stack_size);
}

// Verificar se a stack está próxima do limite
int check_stack_overflow() {
    void *current = __builtin_frame_address(0);
    
    if (!stack_base || !current) {
        return 0;
    }
    
    // Calcular distância do início da stack
    ptrdiff_t distance;
    if (current > stack_base) {
        distance = (char*)current - (char*)stack_base;
    } else {
        distance = (char*)stack_base - (char*)current;
    }
    
    // Verificar se está próxima do limite
    if (distance > STACK_WARNING_THRESHOLD) {
        fprintf(stderr, "AVISO: Stack próxima do limite! Distância: %td\n", distance);
        return 1;
    }
    
    return 0;
}

// Função com proteção de stack overflow
int safe_function_with_deep_recursion(int n) {
    // Verificar overflow antes de cada chamada recursiva
    if (check_stack_overflow()) {
        fprintf(stderr, "Stack overflow detectado na recursão nivel %d\n", n);
        return -1;
    }
    
    // Caso base
    if (n <= 0) {
        return 1;
    }
    
    // Buffer local para demonstrar uso de stack
    char local_buffer[1024];
    memset(local_buffer, 0, sizeof(local_buffer));
    
    // Chamada recursiva
    return n * safe_function_with_deep_recursion(n - 1);
}

// Função iterativa alternativa
long long iterative_factorial(int n) {
    long long result = 1;
    
    for (int i = 1; i <= n; i++) {
        result *= i;
    }
    
    return result;
}

// Stack allocator seguro
typedef struct {
    char *base;
    char *current;
    size_t size;
    size_t used;
} StackAllocator;

StackAllocator* stack_allocator_create(size_t size) {
    StackAllocator *alloc = (StackAllocator*)malloc(sizeof(StackAllocator));
    if (!alloc) return NULL;
    
    alloc->base = (char*)malloc(size);
    if (!alloc->base) {
        free(alloc);
        return NULL;
    }
    
    alloc->current = alloc->base;
    alloc->size = size;
    alloc->used = 0;
    
    return alloc;
}

void* stack_allocator_alloc(StackAllocator *alloc, size_t size) {
    if (!alloc) return NULL;
    
    // Verificar se há espaço suficiente
    if (alloc->used + size > alloc->size) {
        fprintf(stderr, "Stack allocator: memória insuficiente\n");
        return NULL;
    }
    
    void *result = alloc->current;
    alloc->current += size;
    alloc->used += size;
    
    return result;
}

void stack_allocator_free(StackAllocator *alloc, size_t size) {
    if (!alloc) return;
    
    if (size > alloc->used) {
        size = alloc->used;
    }
    
    alloc->current -= size;
    alloc->used -= size;
}

void stack_allocator_destroy(StackAllocator *alloc) {
    if (alloc) {
        // Limpar dados sensíveis
        if (alloc->base) {
            memset(alloc->base, 0, alloc->size);
            free(alloc->base);
        }
        free(alloc);
    }
}

// Função para testar stack overflow
void test_stack_overflow() {
    printf("Testando detecção de stack overflow...\n");
    
    // Isso deve causar stack overflow em sistemas reais
    // Em Wasm, pode ser limitado pelo tamanho da memória
    int result = safe_function_with_deep_recursion(10000);
    
    if (result == -1) {
        printf("Stack overflow detectado corretamente\n");
    } else {
        printf("Resultado: %d (pode não ter detectado overflow)\n", result);
    }
}

// WASI signal handler para stack overflow
// Nota: WASI não suporta sinais diretamente, mas podemos usar técnicas alternativas
void setup_stack_overflow_handler() {
    // Em Wasm, não podemos usar signal handlers diretamente
    // Mas podemos configurar handlers de erro no runtime
    
    printf("Handler de stack overflow configurado\n");
}

int main() {
    init_stack_monitor();
    setup_stack_overflow_handler();
    
    // Testar com número pequeno
    printf("Fatorial de 10: %lld\n", iterative_factorial(10));
    
    // Testar stack overflow
    test_stack_overflow();
    
    // Testar stack allocator
    StackAllocator *alloc = stack_allocator_create(1024 * 1024);
    if (alloc) {
        void *ptr1 = stack_allocator_alloc(alloc, 1024);
        void *ptr2 = stack_allocator_alloc(alloc, 2048);
        
        printf("Alocações: %p, %p\n", ptr1, ptr2);
        
        stack_allocator_free(alloc, 2048);
        stack_allocator_destroy(alloc);
    }
    
    return 0;
}
```

## 9.7 Prevenção de Use-After-Free

Use-after-free occurs when a program continues to use a pointer after the memory it points to has been freed. In Wasm, this is mitigated by the linear memory model, but careful programming is still required.

### 9.7.1 Técnicas de Prevenção

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Tamanho máximo de objetos gerenciados
#define MAX_OBJECTS 1024
#define OBJECT_MAGIC 0xDEADBEEF

// Estrutura para rastrear alocações
typedef struct {
    void *ptr;
    size_t size;
    uint32_t magic;
    int freed;
    const char *alloc_file;
    int alloc_line;
} AllocationRecord;

// Tabela de rastreamento de alocações
static AllocationRecord allocation_table[MAX_OBJECTS];
static int allocation_count = 0;

// Macro para registrar alocação
#define TRACK_ALLOC(ptr, size) track_allocation(ptr, size, __FILE__, __LINE__)

// Macro para verificar se está liberado
#define CHECK_NOT_FREED(ptr) check_not_freed(ptr, __FILE__, __LINE__)

// Macro para liberar memória
#define SAFE_FREE(ptr) safe_free(ptr, __FILE__, __LINE__)

// Registrar uma alocação
void track_allocation(void *ptr, size_t size, const char *file, int line) {
    if (allocation_count >= MAX_OBJECTS) {
        fprintf(stderr, "Número máximo de alocações excedido\n");
        return;
    }
    
    allocation_table[allocation_count].ptr = ptr;
    allocation_table[allocation_count].size = size;
    allocation_table[allocation_count].magic = OBJECT_MAGIC;
    allocation_table[allocation_count].freed = 0;
    allocation_table[allocation_count].alloc_file = file;
    allocation_table[allocation_count].alloc_line = line;
    
    allocation_count++;
}

// Verificar se um ponteiro não foi liberado
int check_not_freed(void *ptr, const char *file, int line) {
    for (int i = 0; i < allocation_count; i++) {
        if (allocation_table[i].ptr == ptr) {
            if (allocation_table[i].freed) {
                fprintf(stderr, 
                    "ERRO: Use-after-free detectado em %s:%d\n"
                    "  Ponteiro %p foi alocado em %s:%d e liberado\n",
                    file, line, ptr,
                    allocation_table[i].alloc_file,
                    allocation_table[i].alloc_line);
                return 0;  // Falso - está liberado
            }
            return 1;  // Verdadeiro - não foi liberado
        }
    }
    
    // Não encontrado na tabela - pode ser válido se não foi rastreado
    return 1;
}

// Liberar memória com rastreamento
void safe_free(void *ptr, const char *file, int line) {
    if (!ptr) {
        return;
    }
    
    for (int i = 0; i < allocation_count; i++) {
        if (allocation_table[i].ptr == ptr) {
            if (allocation_table[i].freed) {
                fprintf(stderr,
                    "ERRO: Double free detectado em %s:%d\n"
                    "  Ponteiro %p já foi liberado em %s:%d\n",
                    file, line, ptr,
                    allocation_table[i].alloc_file,
                    allocation_table[i].alloc_line);
                return;
            }
            
            // Marcar como liberado
            allocation_table[i].freed = 1;
            
            // Preencher com padrão de liberado
            memset(ptr, 0xDD, allocation_table[i].size);
            
            // Realmente liberar
            free(ptr);
            
            return;
        }
    }
    
    // Ponteiro não encontrado - liberar normalmente
    free(ptr);
}

// Alocação segura com rastreamento
void* safe_malloc(size_t size, const char *file, int line) {
    void *ptr = malloc(size);
    if (ptr) {
        TRACK_ALLOC(ptr, size);
    }
    return ptr;
}

// Alocação segura com calloc
void* safe_calloc(size_t nmemb, size_t size, const char *file, int line) {
    void *ptr = calloc(nmemb, size);
    if (ptr) {
        TRACK_ALLOC(ptr, nmemb * size);
    }
    return ptr;
}

// Realocação segura
void* safe_realloc(void *ptr, size_t size, const char *file, int line) {
    if (!ptr) {
        return safe_malloc(size, file, line);
    }
    
    // Verificar se o ponteiro atual não foi liberado
    if (!check_not_freed(ptr, file, line)) {
        return NULL;
    }
    
    // Encontrar e atualizar o registro
    for (int i = 0; i < allocation_count; i++) {
        if (allocation_table[i].ptr == ptr) {
            void *new_ptr = realloc(ptr, size);
            if (new_ptr) {
                allocation_table[i].ptr = new_ptr;
                allocation_table[i].size = size;
            }
            return new_ptr;
        }
    }
    
    return realloc(ptr, size);
}

// Macros para uso fácil
#define malloc(size) safe_malloc(size, __FILE__, __LINE__)
#define calloc(nmemb, size) safe_calloc(nmemb, size, __FILE__, __LINE__)
#define realloc(ptr, size) safe_realloc(ptr, size, __FILE__, __LINE__)
#define free(ptr) SAFE_FREE(ptr)

// Estrutura para objeto com ponteiro inteligente
typedef struct {
    void *data;
    size_t size;
    int ref_count;
    void (*destructor)(void*);
} SmartPointer;

// Criar ponteiro inteligente
SmartPointer* smart_pointer_create(size_t size, void (*destructor)(void*)) {
    SmartPointer *sp = (SmartPointer*)malloc(sizeof(SmartPointer));
    if (!sp) return NULL;
    
    sp->data = malloc(size);
    if (!sp->data) {
        free(sp);
        return NULL;
    }
    
    sp->size = size;
    sp->ref_count = 1;
    sp->destructor = destructor;
    
    TRACK_ALLOC(sp->data, size);
    
    return sp;
}

// Incrementar referência
void smart_pointer_add_ref(SmartPointer *sp) {
    if (sp) {
        sp->ref_count++;
    }
}

// Decrementar referência
void smart_pointer_release(SmartPointer *sp) {
    if (!sp) return;
    
    sp->ref_count--;
    
    if (sp->ref_count <= 0) {
        if (sp->destructor && sp->data) {
            sp->destructor(sp->data);
        }
        
        if (sp->data) {
            SAFE_FREE(sp->data);
        }
        
        SAFE_FREE(sp);
    }
}

// Função destruidora de exemplo
void string_destructor(void *data) {
    if (data) {
        // Limpar dados sensíveis
        size_t len = strlen((char*)data);
        memset(data, 0, len);
    }
}

// Exemplo de uso correto
void example_correct_usage() {
    printf("Exemplo de uso correto:\n");
    
    // Criar ponteiro inteligente
    SmartPointer *str = smart_pointer_create(100, string_destructor);
    if (str) {
        strcpy((char*)str->data, "Hello, World!");
        printf("String: %s\n", (char*)str->data);
        
        // Adicionar referência
        smart_pointer_add_ref(str);
        
        // Usar em outra função
        printf("Referências: %d\n", str->ref_count);
        
        // Liberar referências
        smart_pointer_release(str);
        smart_pointer_release(str);  // Isso deve liberar a memória
    }
}

// Exemplo de use-after-free (para demonstração)
void example_use_after_free() {
    printf("\nExemplo de use-after-free (deve ser detectado):\n");
    
    // Alocar e liberar
    char *ptr = (char*)malloc(100);
    strcpy(ptr, "Dados importantes");
    SAFE_FREE(ptr);
    
    // Tentar usar após liberar - deve ser detectado
    // CHECK_NOT_FREED(ptr);  // Descomentar para testar detecção
    
    // Tentar liberar novamente - deve ser detectado
    // SAFE_FREE(ptr);  // Descomentar para testar double-free
}

// Função para verificar memory leaks
void check_memory_leaks() {
    printf("\nVerificando memory leaks...\n");
    
    int leaked = 0;
    for (int i = 0; i < allocation_count; i++) {
        if (!allocation_table[i].freed) {
            fprintf(stderr, 
                "Memory leak: %p (%zu bytes) alocado em %s:%d\n",
                allocation_table[i].ptr,
                allocation_table[i].size,
                allocation_table[i].alloc_file,
                allocation_table[i].alloc_line);
            leaked++;
        }
    }
    
    if (leaked == 0) {
        printf("Nenhum memory leak detectado\n");
    } else {
        printf("Total de leaks: %d\n", leaked);
    }
}

int main() {
    // Testar uso correto
    example_correct_usage();
    
    // Testar use-after-free
    example_use_after_free();
    
    // Verificar memory leaks
    check_memory_leaks();
    
    return 0;
}
```

### 9.7.2 Use-After-Free Prevention em Rust

Rust previne use-after-free através do borrow checker:

```rust
use wasm_bindgen::prelude::*;

// Estrutura que demonstra prevenção de use-after-free em Rust
#[wasm_bindgen]
pub struct SafeContainer {
    data: Vec<Option<Vec<u8>>>,
    free_list: Vec<usize>,
}

#[wasm_bindgen]
impl SafeContainer {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Self {
        Self {
            data: vec![None; capacity],
            free_list: Vec::new(),
        }
    }
    
    // Alocar slot
    pub fn allocate(&mut self, size: usize) -> Result<usize, String> {
        if let Some(index) = self.free_list.pop() {
            self.data[index] = Some(vec![0; size]);
            Ok(index)
        } else if self.data.len() < self.data.capacity() {
            self.data.push(Some(vec![0; size]));
            Ok(self.data.len() - 1)
        } else {
            Err("Container cheio".to_string())
        }
    }
    
    // Liberar slot
    pub fn free(&mut self, index: usize) -> Result<(), String> {
        if index >= self.data.len() {
            return Err("Índice fora dos limites".to_string());
        }
        
        if self.data[index].is_none() {
            return Err("Slot já está livre".to_string());
        }
        
        // Limpar dados sensíveis
        if let Some(ref mut data) = self.data[index] {
            for byte in data.iter_mut() {
                *byte = 0;
            }
        }
        
        self.data[index] = None;
        self.free_list.push(index);
        
        Ok(())
    }
    
    // Ler dados de forma segura
    pub fn read(&self, index: usize) -> Result<Vec<u8>, String> {
        if index >= self.data.len() {
            return Err("Índice fora dos limites".to_string());
        }
        
        match &self.data[index] {
            Some(data) => Ok(data.clone()),
            None => Err("Slot está livre".to_string()),
        }
    }
    
    // Escrever dados de forma segura
    pub fn write(&mut self, index: usize, data: &[u8]) -> Result<(), String> {
        if index >= self.data.len() {
            return Err("Índice fora dos limites".to_string());
        }
        
        match &mut self.data[index] {
            Some(slot) => {
                if data.len() != slot.len() {
                    return Err("Tamanho dos dados não confere".to_string());
                }
                slot.copy_from_slice(data);
                Ok(())
            }
            None => Err("Slot está livre".to_string()),
        }
    }
    
    // Verificar se um slot está alocado
    pub fn is_allocated(&self, index: usize) -> bool {
        index < self.data.len() && self.data[index].is_some()
    }
    
    // Obter tamanho de um slot
    pub fn slot_size(&self, index: usize) -> Result<usize, String> {
        match &self.data[index] {
            Some(data) => Ok(data.len()),
            None => Err("Slot está livre".to_string()),
        }
    }
    
    // Número de slots alocados
    pub fn allocated_count(&self) -> usize {
        self.data.iter().filter(|s| s.is_some()).count()
    }
    
    // Número de slots livres
    pub fn free_count(&self) -> usize {
        self.free_list.len()
    }
}

// Smart pointer implementation with reference counting
#[wasm_bindgen]
pub struct Rc<T> {
    value: T,
    ref_count: usize,
}

#[wasm_bindgen]
impl<T> Rc<T> {
    pub fn new(value: T) -> Self {
        Self {
            value,
            ref_count: 1,
        }
    }
    
    pub fn clone_ref(&mut self) -> usize {
        self.ref_count += 1;
        self.ref_count
    }
    
    pub fn release(&mut self) -> usize {
        if self.ref_count > 0 {
            self.ref_count -= 1;
        }
        self.ref_count
    }
    
    pub fn ref_count(&self) -> usize {
        self.ref_count
    }
    
    pub fn get(&self) -> &T {
        &self.value
    }
    
    pub fn get_mut(&mut self) -> &mut T {
        &mut self.value
    }
}

// Exemplo de uso seguro
#[wasm_bindgen]
pub fn demonstrate_safe_memory() -> Result<String, String> {
    let mut container = SafeContainer::new(10);
    
    // Alocar slots
    let idx1 = container.allocate(100)?;
    let idx2 = container.allocate(200)?;
    
    // Escrever dados
    container.write(idx1, b"Primeiro slot")?;
    container.write(idx2, b"Segundo slot com mais dados")?;
    
    // Ler dados
    let data1 = container.read(idx1)?;
    let data2 = container.read(idx2)?;
    
    // Liberar primeiro slot
    container.free(idx1)?;
    
    // Tentar ler slot liberado (deve falhar)
    if container.read(idx1).is_ok() {
        return Err("Deveria falhar ao ler slot liberado".to_string());
    }
    
    // Reutilizar slot liberado
    let idx3 = container.allocate(50)?;
    if idx3 != idx1 {
        return Err("Deveria reutilizar o mesmo slot".to_string());
    }
    
    // Verificar estado
    if container.allocated_count() != 2 {
        return Err("Número incorreto de slots alocados".to_string());
    }
    
    Ok("Prevenção de use-after-free demonstrada com sucesso".to_string())
}
```

## 9.8 Prevenção de Buffer Overflow

Buffer overflow is one of the most common and dangerous memory safety issues. Wasm provides bounds checking, but careful programming is still essential.

### 9.8.1 Técnicas de Prevenção

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

// Estrutura para buffer seguro com metadados
typedef struct {
    uint8_t *data;
    size_t capacity;
    size_t length;
    uint32_t canary;  // Valor canário para detectar overflow
    bool initialized;
} SafeBuffer;

// Valor canário padrão
#define BUFFER_CANARY 0xCAFEBABE

// Criar buffer seguro
SafeBuffer* safe_buffer_create(size_t capacity) {
    SafeBuffer *buf = (SafeBuffer*)malloc(sizeof(SafeBuffer));
    if (!buf) return NULL;
    
    buf->data = (uint8_t*)malloc(capacity + sizeof(uint32_t));
    if (!buf->data) {
        free(buf);
        return NULL;
    }
    
    // Escrever canário no final
    uint32_t *canary_ptr = (uint32_t*)(buf->data + capacity);
    *canary_ptr = BUFFER_CANARY;
    
    buf->capacity = capacity;
    buf->length = 0;
    buf->canary = BUFFER_CANARY;
    buf->initialized = true;
    
    return buf;
}

// Verificar integridade do buffer
bool safe_buffer_check_canary(SafeBuffer *buf) {
    if (!buf || !buf->initialized || !buf->data) {
        return false;
    }
    
    uint32_t *canary_ptr = (uint32_t*)(buf->data + buf->capacity);
    return *canary_ptr == BUFFER_CANARY;
}

// Liberar buffer seguro
void safe_buffer_destroy(SafeBuffer *buf) {
    if (buf && buf->initialized) {
        if (buf->data) {
            // Limpar dados sensíveis
            memset(buf->data, 0, buf->capacity + sizeof(uint32_t));
            free(buf->data);
        }
        memset(buf, 0, sizeof(SafeBuffer));
        free(buf);
    }
}

// Escrever dados no buffer com verificação de limites
int safe_buffer_write(SafeBuffer *buf, const void *src, size_t length) {
    if (!buf || !buf->initialized || !buf->data) {
        return -1;  // Buffer inválido
    }
    
    if (!src) {
        return -2;  // Fonte inválida
    }
    
    if (length > buf->capacity - buf->length) {
        return -3;  // Não há espaço suficiente
    }
    
    // Verificar canário antes da escrita
    if (!safe_buffer_check_canary(buf)) {
        return -4;  // Buffer corrompido
    }
    
    // Copiar dados
    memcpy(buf->data + buf->length, src, length);
    buf->length += length;
    
    // Verificar canário após a escrita
    if (!safe_buffer_check_canary(buf)) {
        return -5;  // Overflow detectado durante escrita
    }
    
    return 0;  // Sucesso
}

// Ler dados do buffer com verificação de limites
int safe_buffer_read(SafeBuffer *buf, void *dest, size_t length, size_t offset) {
    if (!buf || !buf->initialized || !buf->data) {
        return -1;  // Buffer inválido
    }
    
    if (!dest) {
        return -2;  // Destino inválido
    }
    
    if (offset + length > buf->length) {
        return -3;  // Leitura fora dos limites
    }
    
    // Verificar canário
    if (!safe_buffer_check_canary(buf)) {
        return -4;  // Buffer corrompido
    }
    
    // Copiar dados
    memcpy(dest, buf->data + offset, length);
    
    return 0;  // Sucesso
}

// Resize seguro do buffer
int safe_buffer_resize(SafeBuffer *buf, size_t new_capacity) {
    if (!buf || !buf->initialized || !buf->data) {
        return -1;
    }
    
    if (new_capacity < buf->length) {
        return -2;  // Nova capacidade menor que dados atuais
    }
    
    // Verificar canário atual
    if (!safe_buffer_check_canary(buf)) {
        return -3;  // Buffer corrompido
    }
    
    // Realocar memória
    uint8_t *new_data = (uint8_t*)realloc(buf->data, new_capacity + sizeof(uint32_t));
    if (!new_data) {
        return -4;  // Falha na realocação
    }
    
    buf->data = new_data;
    
    // Escrever novo canário
    uint32_t *canary_ptr = (uint32_t*)(buf->data + new_capacity);
    *canary_ptr = BUFFER_CANARY;
    
    buf->capacity = new_capacity;
    
    return 0;
}

// Função para demostrar prevenção de buffer overflow
void demonstrate_buffer_overflow_prevention() {
    printf("Demonstrando prevenção de buffer overflow:\n");
    
    // Criar buffer de 100 bytes
    SafeBuffer *buf = safe_buffer_create(100);
    if (!buf) {
        fprintf(stderr, "Falha ao criar buffer\n");
        return;
    }
    
    // Escrever dados dentro dos limites
    const char *data1 = "Dados seguros";
    int result = safe_buffer_write(buf, data1, strlen(data1) + 1);
    if (result == 0) {
        printf("Escrita 1 bem-sucedida\n");
    }
    
    // Verificar canário
    if (safe_buffer_check_canary(buf)) {
        printf("Canário intacto após escrita 1\n");
    }
    
    // Tentar escrever dados que causariam overflow
    char large_data[200];
    memset(large_data, 'A', sizeof(large_data));
    
    result = safe_buffer_write(buf, large_data, sizeof(large_data));
    if (result != 0) {
        printf("Overflow prevenido corretamente (erro: %d)\n", result);
    }
    
    // Verificar canário novamente
    if (safe_buffer_check_canary(buf)) {
        printf("Canário intacto - buffer não foi corrompido\n");
    }
    
    // Ler dados
    char read_buf[64];
    result = safe_buffer_read(buf, read_buf, strlen(data1) + 1, 0);
    if (result == 0) {
        printf("Leitura: %s\n", read_buf);
    }
    
    safe_buffer_destroy(buf);
}

// Estrutura para string segura
typedef struct {
    char *data;
    size_t length;
    size_t capacity;
} SafeString;

// Criar string segura
SafeString* safe_string_create(size_t initial_capacity) {
    SafeString *str = (SafeString*)malloc(sizeof(SafeString));
    if (!str) return NULL;
    
    str->data = (char*)malloc(initial_capacity);
    if (!str->data) {
        free(str);
        return NULL;
    }
    
    str->data[0] = '\0';
    str->length = 0;
    str->capacity = initial_capacity;
    
    return str;
}

// Copiar string com verificação de limites
int safe_string_copy(SafeString *dest, const char *src) {
    if (!dest || !dest->data || !src) {
        return -1;
    }
    
    size_t src_len = strlen(src);
    
    // Verificar se precisa redimensionar
    if (src_len + 1 > dest->capacity) {
        size_t new_capacity = dest->capacity;
        while (new_capacity < src_len + 1) {
            new_capacity *= 2;
        }
        
        char *new_data = (char*)realloc(dest->data, new_capacity);
        if (!new_data) {
            return -2;
        }
        
        dest->data = new_data;
        dest->capacity = new_capacity;
    }
    
    // Copiar dados
    memcpy(dest->data, src, src_len + 1);
    dest->length = src_len;
    
    return 0;
}

// Concatenar strings com verificação de limites
int safe_string_concat(SafeString *dest, const char *src) {
    if (!dest || !dest->data || !src) {
        return -1;
    }
    
    size_t src_len = strlen(src);
    size_t new_length = dest->length + src_len;
    
    // Verificar se precisa redimensionar
    if (new_length + 1 > dest->capacity) {
        size_t new_capacity = dest->capacity;
        while (new_capacity < new_length + 1) {
            new_capacity *= 2;
        }
        
        char *new_data = (char*)realloc(dest->data, new_capacity);
        if (!new_data) {
            return -2;
        }
        
        dest->data = new_data;
        dest->capacity = new_capacity;
    }
    
    // Concatenar
    memcpy(dest->data + dest->length, src, src_len + 1);
    dest->length = new_length;
    
    return 0;
}

// Liberar string segura
void safe_string_destroy(SafeString *str) {
    if (str) {
        if (str->data) {
            // Limpar dados sensíveis
            memset(str->data, 0, str->capacity);
            free(str->data);
        }
        free(str);
    }
}

// Função para testar prevenção em string
void test_string_overflow_prevention() {
    printf("\nTestando prevenção de overflow em strings:\n");
    
    SafeString *str = safe_string_create(16);
    if (!str) {
        fprintf(stderr, "Falha ao criar string\n");
        return;
    }
    
    // Copiar string curta
    safe_string_copy(str, "Hello");
    printf("String: %s (comprimento: %zu)\n", str->data, str->length);
    
    // Concatenar mais dados
    safe_string_concat(str, ", World!");
    printf("String: %s (comprimento: %zu)\n", str->data, str->length);
    
    // Tentar copiar string longa (deve redimensionar)
    char long_str[1000];
    memset(long_str, 'A', sizeof(long_str) - 1);
    long_str[sizeof(long_str) - 1] = '\0';
    
    int result = safe_string_copy(str, long_str);
    if (result == 0) {
        printf("String longa copiada com sucesso (comprimento: %zu)\n", str->length);
    }
    
    safe_string_destroy(str);
}

int main() {
    demonstrate_buffer_overflow_prevention();
    test_string_overflow_prevention();
    
    return 0;
}
```

## 9.9 Gerenciamento de Heap

Heap management in Wasm requires careful consideration to prevent fragmentation, leaks, and corruption.

### 9.9.1 Implementação de Heap Seguro

```rust
use wasm_bindgen::prelude::*;
use std::collections::BTreeMap;

// Estrutura para bloco de heap
#[derive(Debug, Clone)]
struct HeapBlock {
    offset: usize,
    size: usize,
    allocated: bool,
    magic: u32,
}

// Gerenciador de heap seguro
#[wasm_bindgen]
pub struct SafeHeap {
    memory: Vec<u8>,
    blocks: BTreeMap<usize, HeapBlock>,
    free_list: Vec<usize>,
    total_size: usize,
    used_size: usize,
    magic: u32,
}

#[wasm_bindgen]
impl SafeHeap {
    #[wasm_bindgen(constructor)]
    pub fn new(initial_size: usize) -> Self {
        let mut blocks = BTreeMap::new();
        
        // Criar bloco inicial livre
        let initial_block = HeapBlock {
            offset: 0,
            size: initial_size,
            allocated: false,
            magic: 0xDEADBEEF,
        };
        
        blocks.insert(0, initial_block);
        
        Self {
            memory: vec![0; initial_size],
            blocks,
            free_list: vec![0],
            total_size: initial_size,
            used_size: 0,
            magic: 0xDEADBEEF,
        }
    }
    
    // Alocar memória com first-fit
    pub fn alloc(&mut self, size: usize) -> Result<usize, String> {
        // Alinhar em 8 bytes
        let aligned_size = (size + 7) & !7;
        
        // Procurar bloco livre adequado
        let mut found_offset = None;
        
        for &offset in &self.free_list.clone() {
            if let Some(block) = self.blocks.get(&offset) {
                if !block.allocated && block.size >= aligned_size {
                    found_offset = Some(offset);
                    break;
                }
            }
        }
        
        let offset = found_offset.ok_or_else(|| "Memória insuficiente".to_string())?;
        
        // Dividir bloco se for maior que o necessário
        let block = self.blocks.get(&offset).cloned().unwrap();
        
        if block.size > aligned_size + 16 {  // 16 bytes mínimo para novo bloco
            // Criar novo bloco livre
            let new_block = HeapBlock {
                offset: offset + aligned_size,
                size: block.size - aligned_size,
                allocated: false,
                magic: self.magic,
            };
            
            self.blocks.insert(new_block.offset, new_block);
            self.free_list.push(new_block.offset);
        }
        
        // Marcar bloco como alocado
        let allocated_block = HeapBlock {
            offset,
            size: aligned_size,
            allocated: true,
            magic: self.magic,
        };
        
        self.blocks.insert(offset, allocated_block);
        self.free_list.retain(|&o| o != offset);
        
        self.used_size += aligned_size;
        
        // Escrever canário no final do bloco
        let canary_offset = offset + size;
        if canary_offset + 4 <= self.total_size {
            let canary_bytes = self.magic.to_le_bytes();
            self.memory[canary_offset..canary_offset + 4].copy_from_slice(&canary_bytes);
        }
        
        Ok(offset)
    }
    
    // Liberar memória
    pub fn free(&mut self, offset: usize) -> Result<(), String> {
        let block = self.blocks.get(&offset)
            .ok_or_else(|| format!("Bloco não encontrado: {}", offset))?;
        
        if !block.allocated {
            return Err(format!("Bloco já está livre: {}", offset));
        }
        
        // Verificar canário
        let canary_offset = offset + block.size - 4;
        if canary_offset + 4 <= self.total_size {
            let canary_bytes = self.memory[canary_offset..canary_offset + 4]
                .try_into()
                .map_err(|_| "Erro ao ler canário")?;
            let canary = u32::from_le_bytes(canary_bytes);
            
            if canary != self.magic {
                return Err("Buffer overflow detectado - canário corrompido".to_string());
            }
        }
        
        // Limpar dados sensíveis
        for i in offset..offset + block.size {
            self.memory[i] = 0;
        }
        
        // Marcar como livre
        let freed_block = HeapBlock {
            offset,
            size: block.size,
            allocated: false,
            magic: self.magic,
        };
        
        self.blocks.insert(offset, freed_block);
        self.free_list.push(offset);
        
        self.used_size -= block.size;
        
        // Tentar fundir blocos adjacentes livres
        self.coalesce_free_blocks();
        
        Ok(())
    }
    
    // Fundir blocos adjacentes livres
    fn coalesce_free_blocks(&mut self) {
        let offsets: Vec<usize> = self.blocks.keys().cloned().collect();
        let mut i = 0;
        
        while i < offsets.len() {
            let offset = offsets[i];
            let block = self.blocks.get(&offset).cloned().unwrap();
            
            if !block.allocated {
                // Verificar se o próximo bloco é adjacente e livre
                let next_offset = offset + block.size;
                
                if let Some(next_block) = self.blocks.get(&next_offset).cloned() {
                    if !next_block.allocated {
                        // Fundir blocos
                        let merged_block = HeapBlock {
                            offset,
                            size: block.size + next_block.size,
                            allocated: false,
                            magic: self.magic,
                        };
                        
                        self.blocks.insert(offset, merged_block);
                        self.blocks.remove(&next_offset);
                        
                        self.free_list.retain(|&o| o != next_offset);
                        
                        // Não incrementar i - verificar se pode fundir mais
                        continue;
                    }
                }
            }
            
            i += 1;
        }
    }
    
    // Verificar integridade do heap
    pub fn check_integrity(&self) -> Result<bool, String> {
        let mut total_used = 0;
        let mut valid_blocks = 0;
        
        for (&offset, block) in &self.blocks {
            // Verificar se o bloco está dentro dos limites
            if offset + block.size > self.total_size {
                return Err(format!("Bloco fora dos limites: {}", offset));
            }
            
            // Verificar magic number
            if block.magic != self.magic {
                return Err(format!("Magic number inválido no bloco: {}", offset));
            }
            
            if block.allocated {
                total_used += block.size;
                valid_blocks += 1;
                
                // Verificar canário
                let canary_offset = offset + block.size - 4;
                if canary_offset + 4 <= self.total_size {
                    let canary_bytes = self.memory[canary_offset..canary_offset + 4]
                        .try_into()
                        .map_err(|_| "Erro ao ler canário")?;
                    let canary = u32::from_le_bytes(canary_bytes);
                    
                    if canary != self.magic {
                        return Err(format!("Canário corrompido no bloco: {}", offset));
                    }
                }
            }
        }
        
        // Verificar consistência
        if total_used != self.used_size {
            return Err("Inconsistência no tamanho usado".to_string());
        }
        
        Ok(true)
    }
    
    // Obter estatísticas
    pub fn stats(&self) -> String {
        let allocated_blocks = self.blocks.values().filter(|b| b.allocated).count();
        let free_blocks = self.blocks.values().filter(|b| !b.allocated).count();
        
        format!(
            "Heap Stats: total={}, used={}, free={}, allocated_blocks={}, free_blocks={}",
            self.total_size,
            self.used_size,
            self.total_size - self.used_size,
            allocated_blocks,
            free_blocks
        )
    }
    
    // Listar todos os blocos
    pub fn list_blocks(&self) -> Vec<String> {
        self.blocks.values()
            .map(|b| {
                format!(
                    "Block at {}: size={}, allocated={}, magic={:#x}",
                    b.offset, b.size, b.allocated, b.magic
                )
            })
            .collect()
    }
}

// Teste do gerenciamento de heap
#[wasm_bindgen]
pub fn test_heap_management() -> Result<String, String> {
    let mut heap = SafeHeap::new(1024 * 1024);  // 1MB
    
    // Alocar alguns blocos
    let ptr1 = heap.alloc(100)?;
    let ptr2 = heap.alloc(200)?;
    let ptr3 = heap.alloc(300)?;
    
    println!("Alocado: ptr1={}, ptr2={}, ptr3={}", ptr1, ptr2, ptr3);
    
    // Verificar integridade
    if !heap.check_integrity()? {
        return Err("Integridade do heap comprometida".to_string());
    }
    
    // Liberar bloco do meio
    heap.free(ptr2)?;
    
    // Verificar integridade novamente
    if !heap.check_integrity()? {
        return Err("Integridade do heap comprometida após free".to_string());
    }
    
    // Alocar novamente (deveria reutilizar espaço)
    let ptr4 = heap.alloc(150)?;
    println!("Novo bloco alocado: ptr4={}", ptr4);
    
    // Verificar estatísticas
    println!("{}", heap.stats());
    
    // Listar blocos
    for block in heap.list_blocks() {
        println!("  {}", block);
    }
    
    // Verificar integridade final
    if !heap.check_integrity()? {
        return Err("Integridade do heap comprometida no final".to_string());
    }
    
    Ok("Testes de gerenciamento de heap passaram".to_string())
}
```

## 9.10 Linguagens Memory-Safe para Wasm

Using memory-safe languages for Wasm development can significantly reduce the risk of memory safety issues.

### 9.10.1 Rust para Wasm

Rust é a linguagem mais popular para desenvolvimento Wasm devido às suas garantias de segurança de memória:

```rust
use wasm_bindgen::prelude::*;

// Estrutura segura em Rust
#[wasm_bindgen]
pub struct SecureData {
    data: Vec<u8>,
    checksum: u32,
}

#[wasm_bindgen]
impl SecureData {
    #[wasm_bindgen(constructor)]
    pub fn new(initial_capacity: usize) -> Self {
        Self {
            data: Vec::with_capacity(initial_capacity),
            checksum: 0,
        }
    }
    
    // Push seguro
    pub fn push(&mut self, byte: u8) {
        self.data.push(byte);
        self.update_checksum();
    }
    
    // Pop seguro
    pub fn pop(&mut self) -> Option<u8> {
        let result = self.data.pop();
        if result.is_some() {
            self.update_checksum();
        }
        result
    }
    
    // Leitura segura com bounds checking
    pub fn get(&self, index: usize) -> Result<u8, String> {
        self.data.get(index)
            .copied()
            .ok_or_else(|| format!("Índice fora dos limites: {}", index))
    }
    
    // Escrita segura com bounds checking
    pub fn set(&mut self, index: usize, value: u8) -> Result<(), String> {
        if index >= self.data.len() {
            return Err(format!("Índice fora dos limites: {}", index));
        }
        
        self.data[index] = value;
        self.update_checksum();
        
        Ok(())
    }
    
    // Atualizar checksum
    fn update_checksum(&mut self) {
        self.checksum = self.data.iter()
            .fold(0u32, |acc, &b| acc.wrapping_add(b as u32));
    }
    
    // Verificar integridade
    pub fn verify_integrity(&self) -> bool {
        let current_checksum = self.data.iter()
            .fold(0u32, |acc, &b| acc.wrapping_add(b as u32));
        
        current_checksum == self.checksum
    }
    
    // Obter tamanho
    pub fn len(&self) -> usize {
        self.data.len()
    }
    
    // Verificar se está vazio
    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }
    
    // Limpar dados sensíveis
    pub fn clear(&mut self) {
        // Sobrescrever dados antes de limpar
        for byte in self.data.iter_mut() {
            *byte = 0;
        }
        self.data.clear();
        self.checksum = 0;
    }
}

// Implementação de buffer circular seguro
#[wasm_bindgen]
pub struct CircularBuffer {
    buffer: Vec<Option<u8>>,
    head: usize,
    tail: usize,
    size: usize,
    capacity: usize,
}

#[wasm_bindgen]
impl CircularBuffer {
    #[wasm_bindgen(constructor)]
    pub fn new(capacity: usize) -> Self {
        let mut buffer = Vec::with_capacity(capacity);
        for _ in 0..capacity {
            buffer.push(None);
        }
        
        Self {
            buffer,
            head: 0,
            tail: 0,
            size: 0,
            capacity,
        }
    }
    
    // Escrever no buffer
    pub fn push(&mut self, value: u8) -> Result<(), String> {
        if self.size >= self.capacity {
            return Err("Buffer cheio".to_string());
        }
        
        self.buffer[self.tail] = Some(value);
        self.tail = (self.tail + 1) % self.capacity;
        self.size += 1;
        
        Ok(())
    }
    
    // Ler do buffer
    pub fn pop(&mut self) -> Result<u8, String> {
        if self.size == 0 {
            return Err("Buffer vazio".to_string());
        }
        
        let value = self.buffer[self.head].take().unwrap();
        self.head = (self.head + 1) % self.capacity;
        self.size -= 1;
        
        Ok(value)
    }
    
    // Olhar o próximo valor sem remover
    pub fn peek(&self) -> Result<u8, String> {
        if self.size == 0 {
            return Err("Buffer vazio".to_string());
        }
        
        self.buffer[self.head]
            .ok_or_else(|| "Valor inválido no buffer".to_string())
    }
    
    // Verificar se está cheio
    pub fn is_full(&self) -> bool {
        self.size >= self.capacity
    }
    
    // Verificar se está vazio
    pub fn is_empty(&self) -> bool {
        self.size == 0
    }
    
    // Obter tamanho atual
    pub fn len(&self) -> usize {
        self.size
    }
    
    // Obter capacidade
    pub fn capacity(&self) -> usize {
        self.capacity
    }
    
    // Limpar buffer
    pub fn clear(&mut self) {
        for slot in self.buffer.iter_mut() {
            *slot = None;
        }
        self.head = 0;
        self.tail = 0;
        self.size = 0;
    }
}

// Exemplo de uso seguro
#[wasm_bindgen]
pub fn demonstrate_memory_safe_wasm() -> Result<String, String> {
    // Testar SecureData
    let mut data = SecureData::new(100);
    
    for i in 0..10 {
        data.push(i as u8);
    }
    
    if !data.verify_integrity() {
        return Err("Integridade comprometida".to_string());
    }
    
    // Testar CircularBuffer
    let mut buffer = CircularBuffer::new(5);
    
    for i in 0..5 {
        buffer.push(i as u8)?;
    }
    
    if !buffer.is_full() {
        return Err("Buffer deveria estar cheio".to_string());
    }
    
    // Ler valores
    for i in 0..5 {
        let value = buffer.pop()?;
        if value != i as u8 {
            return Err(format!("Valor incorreto: esperado {}, obtido {}", i, value));
        }
    }
    
    if !buffer.is_empty() {
        return Err("Buffer deveria estar vazio".to_string());
    }
    
    Ok("Demonstração de memory safety concluída".to_string())
}
```

### 9.10.2 AssemblyScript para Wasm

AssemblyScript oferece segurança de memória através de verificações em tempo de execução:

```typescript
// assembly/index.ts
import { memory } from "wasm";

// Estrutura segura em AssemblyScript
export class SecureArray {
    private data: StaticArray<u8>;
    private _length: i32;
    private capacity: i32;
    
    constructor(initialCapacity: i32) {
        this.data = new StaticArray<u8>(initialCapacity);
        this._length = 0;
        this.capacity = initialCapacity;
    }
    
    // Push seguro com verificação de limites
    push(value: u8): void {
        if (this._length >= this.capacity) {
            this.resize(this.capacity * 2);
        }
        
        unchecked(this.data[this._length] = value);
        this._length++;
    }
    
    // Pop seguro
    pop(): u8 {
        if (this._length == 0) {
            throw new Error("Array vazio");
        }
        
        this._length--;
        const value = unchecked(this.data[this._length]);
        unchecked(this.data[this._length] = 0);  // Limpar
        
        return value;
    }
    
    // Leitura segura com bounds checking
    get(index: i32): u8 {
        if (index < 0 || index >= this._length) {
            throw new Error(`Índice fora dos limites: ${index}`);
        }
        
        return unchecked(this.data[index]);
    }
    
    // Escrita segura
    set(index: i32, value: u8): void {
        if (index < 0 || index >= this._length) {
            throw new Error(`Índice fora dos limites: ${index}`);
        }
        
        unchecked(this.data[index] = value);
    }
    
    // Redimensionar array
    private resize(newCapacity: i32): void {
        const newData = new StaticArray<u8>(newCapacity);
        
        for (let i: i32 = 0; i < this._length; i++) {
            unchecked(newData[i] = this.data[i]);
        }
        
        this.data = newData;
        this.capacity = newCapacity;
    }
    
    // Obter comprimento
    get length(): i32 {
        return this._length;
    }
    
    // Verificar se está vazio
    isEmpty(): bool {
        return this._length == 0;
    }
    
    // Limpar array
    clear(): void {
        for (let i: i32 = 0; i < this._length; i++) {
            unchecked(this.data[i] = 0);
        }
        this._length = 0;
    }
}

// Buffer seguro com canário
export class CanaryBuffer {
    private buffer: StaticArray<u8>;
    private _size: i32;
    private canary: u32;
    
    constructor(capacity: i32) {
        this.buffer = new StaticArray<u8>(capacity + 4);  // +4 para canário
        this._size = 0;
        this.canary = 0xCAFEBABE;
        
        this.writeCanary();
    }
    
    private writeCanary(): void {
        const canaryBytes = this.canary.toBytesLE();
        for (let i: i32 = 0; i < 4; i++) {
            unchecked(this.buffer[this._size + i] = canaryBytes[i]);
        }
    }
    
    private checkCanary(): bool {
        const canaryBytes = this.canary.toBytesLE();
        for (let i: i32 = 0; i < 4; i++) {
            if (unchecked(this.buffer[this._size + i]) != canaryBytes[i]) {
                return false;
            }
        }
        return true;
    }
    
    // Escrever dados com verificação
    write(data: StaticArray<u8>): void {
        if (this._size + data.length > this.buffer.length - 4) {
            throw new Error("Buffer overflow detectado");
        }
        
        if (!this.checkCanary()) {
            throw new Error("Canário corrompido - buffer overflow occurred");
        }
        
        for (let i: i32 = 0; i < data.length; i++) {
            unchecked(this.buffer[this._size + i] = data[i]);
        }
        
        this._size += data.length;
        this.writeCanary();
    }
    
    // Ler dados com verificação
    read(offset: i32, length: i32): StaticArray<u8> {
        if (offset < 0 || offset + length > this._size) {
            throw new Error("Leitura fora dos limites");
        }
        
        if (!this.checkCanary()) {
            throw new Error("Canário corrompido");
        }
        
        const result = new StaticArray<u8>(length);
        for (let i: i32 = 0; i < length; i++) {
            unchecked(result[i] = this.buffer[offset + i]);
        }
        
        return result;
    }
    
    // Obter tamanho atual
    get size(): i32 {
        return this._size;
    }
    
    // Resetar buffer
    reset(): void {
        for (let i: i32 = 0; i < this.buffer.length; i++) {
            unchecked(this.buffer[i] = 0);
        }
        this._size = 0;
        this.writeCanary();
    }
}
```

## 9.11 ASan/MSan para Wasm

AddressSanitizer (ASan) and MemorySanitizer (MSan) are powerful tools for detecting memory errors. While they don't run natively in Wasm, they can be used during development.

### 9.11.1 Uso com Emscripten

```bash
# Compilar com AddressSanitizer para Wasm
emcc -fsanitize=address \
     -fno-omit-frame-pointer \
     -g \
     -O1 \
     -o output.html \
     source.c

# Compilar com MemorySanitizer
emcc -fsanitize=memory \
     -fno-omit-frame-pointer \
     -g \
     -O1 \
     -o output.html \
     source.c

# Configurar opções de sanitizers
export ASAN_OPTIONS = "detect_leaks=1:halt_on_error=0"
export MSAN_OPTIONS = "halt_on_error=0"

# Executar com sanitizers habilitados
node --experimental-wasm-memory64 output.js
```

### 9.11.2 Detecção Manual de Problemas

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

// Implementação de AddressSanitizer simplificado para Wasm
#define ASAN_SHADOW_OFFSET 0
#define ASAN_SHADOW_SCALE 3

// Estados de memória
#define ASAN_MEM_VALID 0
#define ASAN_MEM_FREED 1
#define ASAN_MEM_OVERFLOW 2

// Estrutura para rastrear alocações
typedef struct {
    void *ptr;
    size_t size;
    uint32_t state;
    const char *file;
    int line;
} AllocationInfo;

#define MAX_ALLOCATIONS 4096
static AllocationInfo allocations[MAX_ALLOCATIONS];
static int allocation_count = 0;

// Registrar alocação
void asan_track_alloc(void *ptr, size_t size, const char *file, int line) {
    if (allocation_count >= MAX_ALLOCATIONS) {
        fprintf(stderr, "ASAN: Número máximo de alocações excedido\n");
        return;
    }
    
    allocations[allocation_count].ptr = ptr;
    allocations[allocation_count].size = size;
    allocations[allocation_count].state = ASAN_MEM_VALID;
    allocations[allocation_count].file = file;
    allocations[allocation_count].line = line;
    
    allocation_count++;
}

// Verificar se um ponteiro é válido
int asan_is_valid(void *ptr) {
    for (int i = 0; i < allocation_count; i++) {
        if (allocations[i].ptr == ptr) {
            return allocations[i].state == ASAN_MEM_VALID;
        }
    }
    return 0;
}

// Marcar memória como liberada
void asan_mark_freed(void *ptr) {
    for (int i = 0; i < allocation_count; i++) {
        if (allocations[i].ptr == ptr) {
            allocations[i].state = ASAN_MEM_FREED;
            return;
        }
    }
}

// Verificar bounds
int asan_check_bounds(void *ptr, size_t access_size) {
    for (int i = 0; i < allocation_count; i++) {
        if (allocations[i].ptr <= ptr && 
            (char*)ptr + access_size <= (char*)allocations[i].ptr + allocations[i].size) {
            return 1;  // Válido
        }
    }
    return 0;  // Fora dos limites
}

// Alocação segura com verificação
void* asan_malloc(size_t size, const char *file, int line) {
    void *ptr = malloc(size);
    if (ptr) {
        asan_track_alloc(ptr, size, file, line);
        
        // Preencher com padrão de inicialização
        memset(ptr, 0xAB, size);
    }
    return ptr;
}

// Free seguro com verificação
void asan_free(void *ptr, const char *file, int line) {
    if (!ptr) return;
    
    // Verificar se já foi liberado
    if (!asan_is_valid(ptr)) {
        fprintf(stderr, 
            "ASAN ERROR: Double free at %s:%d\n"
            "  Pointer: %p\n",
            file, line, ptr);
        return;
    }
    
    // Marcar como liberado
    asan_mark_freed(ptr);
    
    // Preencher com padrão de liberado
    for (int i = 0; i < allocation_count; i++) {
        if (allocations[i].ptr == ptr) {
            memset(ptr, 0xDD, allocations[i].size);
            break;
        }
    }
    
    free(ptr);
}

// Leitura segura com verificação
int asan_read(void *dst, void *src, size_t size, const char *file, int line) {
    if (!asan_is_valid(src)) {
        fprintf(stderr,
            "ASAN ERROR: Use-after-free at %s:%d\n"
            "  Pointer: %p\n",
            file, line, src);
        return -1;
    }
    
    if (!asan_check_bounds(src, size)) {
        fprintf(stderr,
            "ASAN ERROR: Heap-buffer-overflow at %s:%d\n"
            "  Pointer: %p, Size: %zu\n",
            file, line, src, size);
        return -2;
    }
    
    memcpy(dst, src, size);
    return 0;
}

// Escrita segura com verificação
int asan_write(void *dst, void *src, size_t size, const char *file, int line) {
    if (!asan_is_valid(dst)) {
        fprintf(stderr,
            "ASAN ERROR: Use-after-free at %s:%d\n"
            "  Pointer: %p\n",
            file, line, dst);
        return -1;
    }
    
    if (!asan_check_bounds(dst, size)) {
        fprintf(stderr,
            "ASAN ERROR: Heap-buffer-overflow at %s:%d\n"
            "  Pointer: %p, Size: %zu\n",
            file, line, dst, size);
        return -2;
    }
    
    memcpy(dst, src, size);
    return 0;
}

// Macros para uso fácil
#define ASAN_MALLOC(size) asan_malloc(size, __FILE__, __LINE__)
#define ASAN_FREE(ptr) asan_free(ptr, __FILE__, __LINE__)
#define ASAN_READ(dst, src, size) asan_read(dst, src, size, __FILE__, __LINE__)
#define ASAN_WRITE(dst, src, size) asan_write(dst, src, size, __FILE__, __LINE__)

// Verificar memory leaks
void asan_check_leaks() {
    printf("Verificando memory leaks...\n");
    
    int leaks = 0;
    for (int i = 0; i < allocation_count; i++) {
        if (allocations[i].state == ASAN_MEM_VALID) {
            fprintf(stderr,
                "ASAN LEAK: %p (%zu bytes) allocated at %s:%d\n",
                allocations[i].ptr,
                allocations[i].size,
                allocations[i].file,
                allocations[i].line);
            leaks++;
        }
    }
    
    if (leaks == 0) {
        printf("Nenhum memory leak detectado\n");
    } else {
        printf("Total de leaks: %d\n", leaks);
    }
}

// Exemplo de uso
void test_asan() {
    printf("Testando AddressSanitizer para Wasm:\n");
    
    // Alocar memória
    char *ptr1 = (char*)ASAN_MALLOC(100);
    char *ptr2 = (char*)ASAN_MALLOC(200);
    
    // Usar memória
    ASAN_WRITE(ptr1, "Hello", 6);
    
    char buffer[64];
    ASAN_READ(buffer, ptr1, 6);
    printf("Lido: %s\n", buffer);
    
    // Liberar memória
    ASAN_FREE(ptr1);
    
    // Tentar usar memória liberada (deve ser detectado)
    // ASAN_READ(buffer, ptr1, 6);  // Descomentar para testar
    
    // Tentar liberar novamente (deve ser detectado)
    // ASAN_FREE(ptr1);  // Descomentar para testar
    
    ASAN_FREE(ptr2);
    
    // Verificar leaks
    asan_check_leaks();
}

int main() {
    test_asan();
    return 0;
}
```

## 9.12 Exemplos Completos

### 9.12.1 Aplicação Completa com Segurança de Memória

```rust
use wasm_bindgen::prelude::*;
use std::collections::HashMap;

// Aplicação completa demonstrando segurança de memória em Wasm
#[wasm_bindgen]
pub struct SecureApplication {
    // Dados do usuário
    user_data: HashMap<String, Vec<u8>>,
    
    // Buffers seguros
    input_buffer: Vec<u8>,
    output_buffer: Vec<u8>,
    
    // Estado
    initialized: bool,
    error_count: u32,
}

#[wasm_bindgen]
impl SecureApplication {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        Self {
            user_data: HashMap::new(),
            input_buffer: Vec::with_capacity(1024),
            output_buffer: Vec::with_capacity(1024),
            initialized: true,
            error_count: 0,
        }
    }
    
    // Processar dados de entrada com validação
    pub fn process_input(&mut self, data: &[u8]) -> Result<Vec<u8>, String> {
        if !self.initialized {
            return Err("Aplicação não inicializada".to_string());
        }
        
        // Validar tamanho dos dados
        if data.len() > 1024 * 1024 {  // Máximo 1MB
            self.error_count += 1;
            return Err("Dados excedem tamanho máximo".to_string());
        }
        
        // Validar dados
        self.validate_data(data)?;
        
        // Processar
        let processed = self.process_data(data)?;
        
        // Armazenar resultado
        let key = format!("item_{}", self.user_data.len());
        self.user_data.insert(key, processed.clone());
        
        Ok(processed)
    }
    
    // Validar dados de entrada
    fn validate_data(&self, data: &[u8]) -> Result<(), String> {
        // Verificar se não está vazio
        if data.is_empty() {
            return Err("Dados não podem ser vazios".to_string());
        }
        
        // Verificar encoding (exemplo simples)
        if let Err(_) = std::str::from_utf8(data) {
            return Err("Encoding inválido".to_string());
        }
        
        // Verificar conteúdo suspeito
        let suspicious_patterns = vec![b"<script", b"javascript:", b"onerror="];
        let data_str = String::from_utf8_lossy(data).to_lowercase();
        
        for pattern in suspicious_patterns {
            if data_str.contains(pattern) {
                return Err("Conteúdo suspeito detectado".to_string());
            }
        }
        
        Ok(())
    }
    
    // Processar dados
    fn process_data(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        // Exemplo: criptografia simples (não use em produção!)
        let mut processed = Vec::with_capacity(data.len());
        
        for &byte in data {
            // XOR com chave simples
            let encrypted = byte ^ 0x5A;
            processed.push(encrypted);
        }
        
        Ok(processed)
    }
    
    // Recuperar dados
    pub fn get_data(&self, key: &str) -> Result<Vec<u8>, String> {
        self.user_data.get(key)
            .cloned()
            .ok_or_else(|| format!("Dados não encontrados: {}", key))
    }
    
    // Listar todas as chaves
    pub fn list_keys(&self) -> Vec<String> {
        self.user_data.keys().cloned().collect()
    }
    
    // Remover dados
    pub fn remove_data(&mut self, key: &str) -> Result<(), String> {
        if self.user_data.remove(key).is_some() {
            Ok(())
        } else {
            Err(format!("Dados não encontrados: {}", key))
        }
    }
    
    // Limpar dados sensíveis
    pub fn clear_sensitive_data(&mut self) {
        // Sobrescrever dados antes de limpar
        for (_, data) in self.user_data.iter_mut() {
            for byte in data.iter_mut() {
                *byte = 0;
            }
        }
        self.user_data.clear();
        
        // Limpar buffers
        for byte in self.input_buffer.iter_mut() {
            *byte = 0;
        }
        self.input_buffer.clear();
        
        for byte in self.output_buffer.iter_mut() {
            *byte = 0;
        }
        self.output_buffer.clear();
    }
    
    // Verificar integridade
    pub fn check_integrity(&self) -> Result<bool, String> {
        // Verificar se o HashMap está consistente
        let expected_count = self.user_data.len();
        let actual_count = self.user_data.keys().count();
        
        if expected_count != actual_count {
            return Err("Inconsistência no HashMap".to_string());
        }
        
        // Verificar cada entrada
        for (key, data) in &self.user_data {
            if key.is_empty() {
                return Err("Chave vazia encontrada".to_string());
            }
            
            if data.is_empty() {
                return Err(format!("Dados vazios para chave: {}", key));
            }
            
            // Verificar se dados são UTF-8 válido
            if let Err(_) = std::str::from_utf8(data) {
                return Err(format!("Dados inválidos para chave: {}", key));
            }
        }
        
        Ok(true)
    }
    
    // Obter estatísticas
    pub fn stats(&self) -> String {
        let total_size: usize = self.user_data.values()
            .map(|v| v.len())
            .sum();
        
        format!(
            "SecureApplication Stats:\n"
            "  Initialized: {}\n"
            "  Items: {}\n"
            "  Total size: {} bytes\n"
            "  Input buffer: {} bytes\n"
            "  Output buffer: {} bytes\n"
            "  Error count: {}",
            self.initialized,
            self.user_data.len(),
            total_size,
            self.input_buffer.capacity(),
            self.output_buffer.capacity(),
            self.error_count
        )
    }
    
    // Fechar aplicação
    pub fn shutdown(&mut self) {
        self.clear_sensitive_data();
        self.initialized = false;
    }
}

// Implementação de Drop para limpeza automática
impl Drop for SecureApplication {
    fn drop(&mut self) {
        self.clear_sensitive_data();
    }
}

// Exemplo de uso completo
#[wasm_bindgen]
pub fn run_secure_application() -> Result<String, String> {
    let mut app = SecureApplication::new();
    
    // Processar dados
    let data1 = b"Hello, Secure WebAssembly!";
    let result1 = app.process_input(data1)?;
    
    let data2 = b"Another test message";
    let result2 = app.process_input(data2)?;
    
    // Verificar integridade
    if !app.check_integrity()? {
        return Err("Integridade comprometida".to_string());
    }
    
    // Listar chaves
    let keys = app.list_keys();
    println!("Chaves: {:?}", keys);
    
    // Recuperar dados
    for key in &keys {
        let data = app.get_data(key)?;
        println!("Dados para {}: {} bytes", key, data.len());
    }
    
    // Obter estatísticas
    println!("{}", app.stats());
    
    // Limpar e fechar
    app.shutdown();
    
    Ok("Aplicação segura executada com sucesso".to_string())
}
```

### 9.12.2 Testes de Segurança

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_buffer_overflow_prevention() {
        let mut app = SecureApplication::new();
        
        // Criar dados que causariam overflow
        let large_data = vec![0u8; 1024 * 1024 + 1];  // 1MB + 1 byte
        
        // Deve falhar
        let result = app.process_input(&large_data);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("tamanho máximo"));
    }
    
    #[test]
    fn test_use_after_free_prevention() {
        let mut app = SecureApplication::new();
        
        // Processar dados
        let data = b"Test data";
        app.process_input(data).unwrap();
        
        // Limpar dados
        app.clear_sensitive_data();
        
        // Tentar acessar dados limpos
        let keys = app.list_keys();
        assert!(keys.is_empty());
    }
    
    #[test]
    fn test_memory_leak_prevention() {
        let mut app = SecureApplication::new();
        
        // Processar muitos dados
        for i in 0..1000 {
            let data = format!("Item {}", i);
            app.process_input(data.as_bytes()).unwrap();
        }
        
        // Verificar estatísticas
        let stats = app.stats();
        assert!(stats.contains("Items: 1000"));
        
        // Limpar
        app.clear_sensitive_data();
        
        let stats = app.stats();
        assert!(stats.contains("Items: 0"));
    }
    
    #[test]
    fn test_buffer_integrity() {
        let mut app = SecureApplication::new();
        
        // Processar dados
        let data = b"Integrity test";
        let result = app.process_input(data).unwrap();
        
        // Verificar integridade
        assert!(app.check_integrity().unwrap());
        
        // Verificar dados
        let keys = app.list_keys();
        assert_eq!(keys.len(), 1);
        
        let stored = app.get_data(&keys[0]).unwrap();
        assert_eq!(stored.len(), data.len());
    }
    
    #[test]
    fn test_suspicious_content_detection() {
        let mut app = SecureApplication::new();
        
        // Testar conteúdo suspeito
        let malicious_data = b"<script>alert('xss')</script>";
        let result = app.process_input(malicious_data);
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("suspeito"));
    }
    
    #[test]
    fn test_concurrent_access_safety() {
        let mut app = SecureApplication::new();
        
        // Simular acesso concorrente (em Wasm single-threaded)
        let data1 = b"Thread 1";
        let data2 = b"Thread 2";
        
        app.process_input(data1).unwrap();
        app.process_input(data2).unwrap();
        
        // Verificar que ambos foram processados
        let keys = app.list_keys();
        assert_eq!(keys.len(), 2);
    }
}

fn main() {
    // Executar testes
    println!("Executando testes de segurança...");
    
    // Em produção, usar framework de testes
    let app = SecureApplication::new();
    println!("Aplicação criada com sucesso");
    
    let stats = app.stats();
    println!("{}", stats);
}
```

## 9.13 Considerações Finais

Segurança de memória em WebAssembly é um tópico complexo mas fundamental. O modelo de memória linear do Wasm fornece uma base sólida, mas não é infalível. As principais lições são:

1. **Wasm não é mágico**: Apesar das proteções nativas, bugs de memória ainda podem ocorrer, especialmente em código compilado de C/C++.

2. **Linguagens memory-safe são preferíveis**: Rust e AssemblyScript oferecem garantias de segurança de memória em compile time.

3. **Bounds checking é essencial**: Toda acesso a memória deve ser verificado, mesmo em Wasm.

4. **Ferramentas de detecção ajudam**: ASan, MSan e técnicas manuais podem ajudar a encontrar bugs durante desenvolvimento.

5. **Defesa em profundidade**: Combinação de múltiplas técnicas fornece melhor proteção.

6. **Testes são cruciais**: Testes unitários e de integração devem cobrir cenários de segurança de memória.

7. **Monitoramento em produção**: Detecção e resposta a incidentes são importantes.

O futuro da segurança de memória em Wasm inclui melhorias no modelo de memória, suporte a garbage collection, e ferramentas mais sofisticadas de detecção. À medida que o ecossistema amadurece, esperamos ver ainda mais proteções e melhores práticas emergirem.

Segurança de memória não é apenas uma característica técnica - é uma responsabilidade fundamental de todos os desenvolvedores que criam software que roda em WebAssembly.
---

*[Capítulo anterior: 08 — Component Model](08-component-model.md)*
*[Próximo capítulo: 10 — Side Channels](10-side-channels.md)*
