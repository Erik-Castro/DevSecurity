# Capítulo 3: WASI e System Interface

## Sumário

- [3.1 WASI Preview 1 vs Preview 2](#31-wasi-preview-1-vs-preview-2)
- [3.2 Modelo de capacidades](#32-modelo-de-capacidades)
- [3.3 Sistema de arquivos](#33-sistema-de-arquivos)
- [3.4 Rede](#34-rede)
- [3.5 Relógios](#35-relógios)
- [3.6 Aleatoriedade](#36-aleatoriedade)
- [3.7 Variáveis de ambiente](#37-variáveis-de-ambiente)
- [3.8 Component Model Preview](#38-component-model-preview)
- [3.9 Implicações de segurança](#39-implicações-de-segurança)
- [3.10 Aplicação WASI completa](#310-aplicação-wasi-completa)

---

## 3.1 WASI Preview 1 vs Preview 2

### Evolução do WASI

WASI (WebAssembly System Interface) é um padrão em evolução que define como módulos WebAssembly interagem com o sistema operacional. A evolução de WASI Preview 1 para Preview 2 representa uma mudança fundamental no design e na filosofia da interface.

### WASI Preview 1: Fundamentos

O WASI Preview 1 é a versão estável e amplamente suportada. Ele é baseado em um modelo simples de file descriptors (descritores de arquivo), inspirado na interface de sistema POSIX.

**Características do Preview 1**:

1. **Baseado em file descriptors**: todas as operações de I/O passam por descritores de arquivo
2. **Síncrono**: operações são bloqueantes
3. **Simples**: fácil de implementar e entender
4. **Estável**: amplamente suportado em runtimes

**Syscalls do Preview 1**:

```
Argumentos e ambiente:
  args_get          → obter argumentos de linha de comando
  args_sizes_get    → obter tamanho dos argumentos
  environ_get       → obter variáveis de ambiente
  environ_sizes_get → obter tamanho das variáveis de ambiente

Relógios:
  clock_time_get    → obter tempo do relógio

Descritores de arquivo:
  fd_close          → fechar descritor
  fd_fdstat_get     → obter status do descritor
  fd_fdstat_set_flags → alterar flags do descritor
  fd_prestat_dir_name → obter nome do diretório pré-aberto
  fd_prestat_get    → obter informação do descritor pré-aberto
  fd_read           → ler dados
  fd_readdir        → ler diretório
  fd_seek           → posicionar ponteiro
  fd_sync           → sincronizar dados
  fd_write          → escrever dados

Sistema de arquivos:
  path_create_directory → criar diretório
  path_filestat_get     → obter status de arquivo
  path_filestat_set_times → alterar timestamps
  path_link             → criar link
  path_open             → abrir arquivo
  path_readlink         → ler link
  path_remove_directory → remover diretório
  path_rename           → renomear
  path_symlink          → criar link simbólico
  path_unlink_file      → remover arquivo

Processo:
  proc_exit         → encerrar processo
  proc_raise        → enviar sinal

I/O multiplexado:
  poll_oneoff       → aguardar eventos

Aleatoriedade:
  random_get        → obter bytes aleatórios

Escalonamento:
  sched_yield       → ceder escalonamento

Sockets:
  sock_accept       → aceitar conexão
  sock_bind         → vincular socket
  sock_close        → fechar socket
  sock_connect      → conectar
  sock_getsockopt   → obter opções de socket
  sock_listen       → aguardar conexões
  sock_recv         → receber dados
  sock_send         → enviar dados
  sock_setsockopt   → definir opções de socket
  sock_shutdown     → encerrar socket
```

**Exemplo de uso do Preview 1**:

```rust
// Aplicação WASI Preview 1 em Rust
use std::env;
use std::fs;
use std::io::{self, Read, Write};

fn main() -> io::Result<()> {
    // Ler argumentos
    let args: Vec<String> = env::args().collect();
    println!("Argumentos: {:?}", args);

    // Ler variáveis de ambiente
    for (key, value) in env::vars() {
        println!("{}={}", key, value);
    }

    // Ler arquivo
    let content = fs::read_to_string("input.txt")?;
    println!("Conteúdo: {}", content);

    // Escrever arquivo
    fs::write("output.txt", content.to_uppercase())?;

    // Ler do stdin
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    println!("Entrada: {}", input);

    // Escrever no stdout
    io::stdout().write_all(b"Hello, WASI!\n")?;

    Ok(())
}
```

### WASI Preview 2: A próxima geração

O WASI Preview 2 é uma evolução significativa que introduz o Component Model e resolve muitas limitações do Preview 1.

**Mudanças fundamentais**:

1. **Component Model**: módulos são compostos usando interfaces tipadas
2. **WIT (WebAssembly Interface Types)**: linguagem para definir interfaces ricas
3. **Streams e Future**: modelos de I/O assíncronos
4. **Tipos ricos**: strings, registros, variante, resultados, listas
5. **Melhor async**: suporte nativo a operações assíncronas

**Comparação Preview 1 vs Preview 2**:

| Aspecto | Preview 1 | Preview 2 |
|---------|-----------|-----------|
| Interface | File descriptors | WIT interfaces |
| Tipos | I32, I64 | Ricos (string, record, etc.) |
| I/O | Síncrono | Assíncrono (streams/future) |
| Composição | Limitada | Component Model |
| Extensibilidade | Adicionar syscalls | Definir interfaces WIT |
| Segurança | Capability-based | Capability-based + tipos |
| Maturidade | Estável | Em desenvolvimento |

### WIT: WebAssembly Interface Types

WIT é a linguagem que define interfaces no WASI Preview 2. Ela permite definir tipos complexos e operações de forma declarativa.

```wit
// Exemplo de interface WIT
package example:filesystem;

interface types {
    record file-error {
        code: u32,
        message: string,
    }

    enum file-mode {
        read,
        write,
        append,
    }

    record file-info {
        size: u64,
        created: u64,
        modified: u64,
    }

    handle file-descriptor;

    open: func(path: string, mode: file-mode) -> result<file-descriptor, file-error>;
    read: func(fd: file-descriptor, count: u64) -> result<list<u8>, file-error>;
    write: func(fd: file-descriptor, data: list<u8>) -> result<u64, file-error>;
    close: func(fd: file-descriptor) -> result<_, file-error>;
    stat: func(fd: file-descriptor) -> result<file-info, file-error>;
}

world filesystem-world {
    import types;
}
```

### Estrutura de um componente WASI Preview 2

```wit
// Estrutura de um componente WASI Preview 2
package wasi:cli;

interface stdout {
    use wasi:io/error@0.2.0.{error};

    stream: handle;

    get-stdout: func() -> stream;
}

interface stderr {
    use wasi:io/error@0.2.0.{error};

    stream: handle;

    get-stderr: func() -> stream;
}

interface stdin {
    use wasi:io/error@0.2.0.{error};

    stream: handle;

    get-stdin: func() -> stream;
}

interface environment {
    use wasi:io/error@0.2.0.{error};

    get-environment: func() -> result<list<tuple<string, string>>, error>;
    get-arguments: func() -> result<list<string>, error>;
}

interface exit {
    exit: func(code: u32);
}

world wasi-cli-reactor {
    import environment;
    import exit;
    export stdout;
    export stderr;
    export stdin;
}
```

### Migração de Preview 1 para Preview 2

A migração requer mudanças no código da aplicação:

**Antes (Preview 1)**:

```rust
use std::fs;
use std::io;

fn main() -> io::Result<()> {
    let content = fs::read_to_string("input.txt")?;
    fs::write("output.txt", content.to_uppercase())?;
    Ok(())
}
```

**Depois (Preview 2)**:

```rust
// Requer suporte a Component Model
// A API muda para ser baseada em WIT interfaces
// E usar streams para I/O

wasi::filesystem::types::open("input.txt", wasi::filesystem::types::FILE_MODE_READ)?;
// ... usar streams para ler/escrever ...
```

---

## 3.2 Modelo de capacidades

### Princípios do modelo

O modelo de capacidades do WASI é inspirado no projeto Capsicum da Universidade de Cambridge e em princípios de segurança de sistemas operacionais modernos. O conceito central é: **referência é permissão**.

Em um sistema baseado em capacidades:

1. Não existem listas de controle de acesso (ACLs)
2. A posse de uma referência é a permissão
3. Não existe verificação de identidade — apenas verificação de posse
4. Capacidades podem ser delegadas (passadas adiante)
5. Capacidades podem ser revogadas (removendo a referência)

### Como WASI implementa capabilities

WASI implementa o modelo de capacidades através de **pré-abertura** (preopens). Quando um módulo WASI é instanciado, o runtime fornece descritores de arquivo pré-abertos que representam os recursos que o módulo pode acessar.

```bash
# O módulo recebe capacidades através de preopens
wasmtime app.wasm \
    --dir /data::read \         # capacidade de ler /data
    --dir /tmp::read,write \    # capacidade de ler e escrever /tmp
    --env KEY=VALUE \           # capacidade de ler variável KEY
    --tcp-connect example.com:80  # capacidade de conectar a example.com
```

### Hierarquia de capacidades

As capacidades formam uma hierarquia onde o host concede permissões que o módulo pode delegar (mas não expandir):

```
Host
├── Capacidade: /data (read)
│   └── Módulo pode delegar para sub-diretórios:
│       ├── /data/subdir (read)
│       └── /data/other (read)
│       Mas NÃO pode delegar:
│       └── /etc (fora de sua capacidade)
│
├── Capacidade: /tmp (read, write)
│   └── Módulo pode delegar:
│       ├── /tmp/subdir (read, write)
│       └── /tmp/other (read, write)
│
└── Capacidade: example.com:80 (connect)
    └── Módulo pode delegar:
        └── example.com:80 (connect)
        Mas NÃO pode delegar:
        └── other.com:443 (fora de sua capacidade)
```

### Implementação de capabilities

**Em Rust com WASI**:

```rust
use std::env;
use std::fs;
use std::path::Path;

// O módulo recebe capabilities através de args e env
fn main() {
    // O diretório de trabalho é uma capability
    let current_dir = env::current_dir().unwrap();
    println!("Diretório atual: {}", current_dir.display());

    // O módulo só pode acessar diretórios que lhe foram concedidos
    match fs::read_dir(&current_dir) {
        Ok(entries) => {
            for entry in entries {
                println!("  {}", entry.unwrap().file_name().to_string_lossy());
            }
        }
        Err(e) => {
            eprintln!("Erro ao listar diretório: {}", e);
        }
    }

    // Tentar acessar diretório não concedido
    match fs::read_dir("/etc") {
        Ok(_) => println!("Acesso a /etc permitido (unexpected)"),
        Err(e) => eprintln!("Acesso a /etc negado: {}", e),
    }
}
```

**Em C com WASI**:

```c
#include <stdio.h>
#include <stdlib.h>
#include <dirent.h>
#include <sys/stat.h>

int main(int argc, char *argv[]) {
    // Ler argumentos (capability)
    printf("Argumentos:\n");
    for (int i = 0; i < argc; i++) {
        printf("  argv[%d] = %s\n", i, argv[i]);
    }

    // Ler variáveis de ambiente (capability)
    printf("\nVariáveis de ambiente:\n");
    extern char **environ;
    for (char **env = environ; *env != NULL; env++) {
        printf("  %s\n", *env);
    }

    // Listar diretório atual (capability)
    DIR *dir = opendir(".");
    if (dir) {
        struct dirent *entry;
        printf("\nConteúdo do diretório atual:\n");
        while ((entry = readdir(dir)) != NULL) {
            printf("  %s\n", entry->d_name);
        }
        closedir(dir);
    }

    // Tentar acessar diretório não concedido
    FILE *f = fopen("/etc/passwd", "r");
    if (f) {
        printf("\nAcesso a /etc/passwd permitido (unexpected)\n");
        fclose(f);
    } else {
        printf("\nAcesso a /etc/passwd negado (expected)\n");
    }

    return 0;
}
```

### Vantagens do modelo de capacidades

**1. Princípio do menor privilégio**: módulos recebem apenas as permissões que precisam

**2. Delegação segura**: módulos podem delegar sub-permissões sem expandir privilégios

**3. Revogação natural**: remover a referência revoga a permissão

**4. Auditabilidade**: é possível determinar exatamente o que um módulo pode acessar

**5. Composição segura**: múltiplos módulos com diferentes capacidades podem compor

### Padrões de uso

**Padrão 1: Sandbox de leitura**

```bash
# Módulo só pode ler de /data
wasmtime reader.wasm --dir /data::read
```

**Padrão 2: Sandbox de leitura/escrita limitada**

```bash
# Módulo pode ler de /data e escrever em /tmp
wasmtime processor.wasm \
    --dir /data::read \
    --dir /tmp::read,write
```

**Padrão 3: Sandbox de rede**

```bash
# Módulo só pode conectar a serviços específicos
wasmtime api-client.wasm \
    --tcp-connect api.example.com:443 \
    --env API_KEY=secret
```

**Padrão 4: Sandbox completo**

```bash
# Módulo sem nenhuma capability
wasmtime isolated.wasm
# (sem --dir, --env, --tcp-connect, etc.)
```

---

## 3.3 Sistema de arquivos

### Visão geral

O WASI fornece acesso ao sistema de arquivos através de descritores de arquivo pré-abertos. O módulo não pode abrir arquivos arbitrários — apenas acessar aqueles que lhe foram concedidos através de preopens.

### Operações de arquivo

**Abrir arquivo**:

```rust
use std::fs::OpenOptions;
use std::io::Write;

fn main() {
    // Abrir para escrita (requer permissão de escrita no diretório)
    let mut file = OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open("output.txt")
        .expect("Erro ao abrir arquivo");

    file.write_all(b"Hello, WASI!\n").expect("Erro ao escrever");
}
```

**Ler arquivo**:

```rust
use std::fs;
use std::io::Read;

fn main() {
    // Ler arquivo inteiro
    let content = fs::read_to_string("input.txt")
        .expect("Erro ao ler arquivo");

    println!("Conteúdo: {}", content);

    // Ler com buffer
    let mut file = std::fs::File::open("input.txt")
        .expect("Erro ao abrir arquivo");

    let mut buffer = [0u8; 1024];
    let bytes_read = file.read(&mut buffer)
        .expect("Erro ao ler");

    println!("Lidos {} bytes", bytes_read);
}
```

**Listar diretório**:

```rust
use std::fs;

fn main() {
    // Listar diretório
    for entry in fs::read_dir(".").expect("Erro ao ler diretório") {
        let entry = entry.expect("Erro ao ler entry");
        let metadata = entry.metadata().expect("Erro ao ler metadata");

        println!(
            "{} - {} bytes - {:?}",
            entry.file_name().to_string_lossy(),
            metadata.len(),
            metadata.file_type()
        );
    }
}
```

**Metadados de arquivo**:

```rust
use std::fs;
use std::time::UNIX_EPOCH;

fn main() {
    let metadata = fs::metadata("file.txt")
        .expect("Erro ao ler metadata");

    println!("Tamanho: {} bytes", metadata.len());
    println!("É arquivo: {}", metadata.is_file());
    println!("É diretório: {}", metadata.is_dir());
    println!("É symlink: {}", metadata.is_symlink());

    if let Ok(modified) = metadata.modified() {
        let duration = modified.duration_since(UNIX_EPOCH).unwrap();
        println!("Modificado: {} segundos desde epoch", duration.as_secs());
    }
}
```

### Permissões de arquivo

O WASI mapeia permissões de arquivo para capabilities:

| Permissão WASI | Capability | Operações permitidas |
|----------------|------------|---------------------|
| `READ` | `--dir path::read` | open, read, stat |
| `WRITE` | `--dir path::write` | open, write, truncate |
| `READ+WRITE` | `--dir path::read,write` | Todas as operações |
| Nenhuma | Nenhuma capability | Nenhuma operação |

### Exemplo completo de manipulação de arquivos

```rust
use std::env;
use std::fs;
use std::io::{self, Read, Write};
use std::path::Path;

fn main() -> io::Result<()> {
    // 1. Determinar diretórios de entrada e saída
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Uso: {} <input_dir> <output_dir>", args[0]);
        std::process::exit(1);
    }

    let input_dir = &args[1];
    let output_dir = &args[2];

    // 2. Verificar se diretórios existem e são acessíveis
    if !Path::new(input_dir).is_dir() {
        eprintln!("Diretório de entrada não existe: {}", input_dir);
        std::process::exit(1);
    }

    // 3. Criar diretório de saída (se não existir)
    fs::create_dir_all(output_dir)?;

    // 4. Processar arquivos
    let mut processed = 0;
    let mut errors = 0;

    for entry in fs::read_dir(input_dir)? {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            match process_file(&path, output_dir) {
                Ok(_) => {
                    processed += 1;
                    println!("OK: {}", path.display());
                }
                Err(e) => {
                    errors += 1;
                    eprintln!("Erro: {} - {}", path.display(), e);
                }
            }
        }
    }

    // 5. Relatório
    println!("\nResultado:");
    println!("  Processados: {}", processed);
    println!("  Erros: {}", errors);

    Ok(())
}

fn process_file(input_path: &Path, output_dir: &str) -> io::Result<()> {
    // Ler conteúdo
    let content = fs::read(input_path)?;

    // Processar (exemplo: contar bytes)
    let byte_count = content.len();
    let word_count = content.iter()
        .filter(|&&b| b == b' ' || b == b'\n' || b == b'\t')
        .count();

    // Determinar nome do arquivo de saída
    let filename = input_path.file_name()
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "Nome inválido"))?;

    let output_path = Path::new(output_dir).join(format!(
        "{}.stats",
        filename.to_string_lossy()
    ));

    // Escrever estatísticas
    let stats = format!(
        "Arquivo: {}\nTamanho: {} bytes\nPalavras: {}\n",
        input_path.display(),
        byte_count,
        word_count
    );

    fs::write(&output_path, stats)?;

    Ok(())
}
```

---

## 3.4 Rede

### Modelo de rede do WASI

O WASI fornece acesso à rede através de operações de socket. No WASI Preview 1, a rede é acessada através de descritores de arquivo com tipos específicos. No WASI Preview 2, a rede é definida através de interfaces WIT.

### Operações de rede

**Preview 1**:

```
sock_accept       → aceitar conexão TCP
sock_bind         → vincular socket
sock_close        → fechar socket
sock_connect      → conectar TCP
sock_getsockopt   → obter opções de socket
sock_listen       → aguardar conexões
sock_recv         → receber dados
sock_send         → enviar dados
sock_setsockopt   → definir opções de socket
sock_shutdown     → encerrar socket
```

**Preview 2**:

```wit
interface network {
    use wasi:io/error@0.2.0.{error};
    use wasi:io/poll@0.2.0.{pollable};

    record ipv4-address {
        port: u8,
    }

    record ipv6-address {
        port: u8,
    }

    variant ip-address {
        ipv4(ipv4-address),
        ipv6(ipv6-address),
    }

    record ip-socket-address {
        address: ip-address,
    }

    handle network;

    resolve-address: func(network: network, name: string) -> result<list<ip-socket-address>, error>;
}
```

### Exemplo de servidor TCP

```rust
use std::net::{TcpListener, TcpStream};
use std::io::{Read, Write};
use std::thread;

fn main() -> std::io::Result<()> {
    // Vincular socket (requer capability de rede)
    let listener = TcpListener::bind("0.0.0.0:8080")?;
    println!("Servidor ouvindo na porta 8080");

    // Aguardar conexões
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                // Criar thread para cada conexão
                thread::spawn(move || {
                    handle_client(stream);
                });
            }
            Err(e) => {
                eprintln!("Erro ao aceitar conexão: {}", e);
            }
        }
    }

    Ok(())
}

fn handle_client(mut stream: TcpStream) {
    let mut buffer = [0u8; 1024];

    // Ler dados do cliente
    match stream.read(&mut buffer) {
        Ok(bytes_read) => {
            let request = String::from_utf8_lossy(&buffer[..bytes_read]);
            println!("Recebido: {}", request);

            // Enviar resposta
            let response = "HTTP/1.1 200 OK\r\nContent-Length: 13\r\n\r\nHello, World!";
            stream.write_all(response.as_bytes()).unwrap();
        }
        Err(e) => {
            eprintln!("Erro ao ler: {}", e);
        }
    }
}
```

### Exemplo de cliente TCP

```rust
use std::net::TcpStream;
use std::io::{Read, Write};

fn main() -> std::io::Result<()> {
    // Conectar ao servidor (requer capability de rede)
    let mut stream = TcpStream::connect("example.com:80")?;

    // Enviar requisição HTTP
    let request = "GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n";
    stream.write_all(request.as_bytes())?;

    // Ler resposta
    let mut response = String::new();
    stream.read_to_string(&mut response)?;

    println!("Resposta:\n{}", response);

    Ok(())
}
```

### Segurança de rede

O WASI controla acesso à rede através de capabilities:

**1. Conexões TCP**

```bash
# Permitir conexão a hosts específicos
wasmtime client.wasm --tcp-connect api.example.com:443

# Permitir múltiplos hosts
wasmtime client.wasm \
    --tcp-connect api.example.com:443 \
    --tcp-connect other.service:8080
```

**2. Sockets TCP**

```bash
# Permitir escuta em portas específicas
wasmtime server.wasm --tcplisten 0.0.0.0:8080

# Permitir múltiplas portas
wasmtime server.wasm \
    --tcplisten 0.0.0.0:8080 \
    --tcplisten 0.0.0.0:9090
```

**3. UDP**

```bash
# Permitir envio/recebimento UDP
wasmtime app.wasm --udp-bind 0.0.0.0:9000
wasmtime app.wasm --udp-connect 8.8.8.8:53
```

**4. DNS**

```bash
# Permitir resolução de DNS
wasmtime app.wasm --dns-resolve
```

### Padrões de uso de rede

**Padrão 1: Cliente HTTP restrito**

```bash
# Módulo só pode acessar APIs específicas
wasmtime api-client.wasm \
    --tcp-connect api.example.com:443 \
    --tcp-connect cdn.example.com:443 \
    --env API_KEY=secret123
```

**Padrão 2: Servidor com escopo limitado**

```bash
# Módulo só pode ouvir em porta específica
wasmtime web-server.wasm \
    --tcplisten 0.0.0.0:8080 \
    --dir /var/www::read
```

**Padrão 3: Proxy**

```bash
# Módulo pode conectar e escutar
wasmtime proxy.wasm \
    --tcplisten 0.0.0.0:8080 \
    --tcp-connect upstream.internal:8080
```

---

## 3.5 Relógios

### Acesso ao relógio

WASI fornece acesso a relógios do sistema. No WASI Preview 1, a operação principal é `clock_time_get`.

**Clock IDs**:

| ID | Constante | Descrição |
|----|-----------|-----------|
| 0 | `CLOCK_REALTIME` | Relógio do sistema (wall clock) |
| 1 | `CLOCK_MONOTONIC` | Relógio monotônico (não afetado por ajustes) |
| 2 | `CLOCK_PROCESS_CPUTIME_ID` | Tempo de CPU do processo |

**Exemplo de uso**:

```rust
use std::time::{SystemTime, Instant, Duration};

fn main() {
    // 1. Relógio do sistema (wall clock)
    let now = SystemTime::now();
    let duration_since_epoch = now.duration_since(SystemTime::UNIX_EPOCH)
        .expect("Tempo é anterior a epoch");

    println!("Tempo desde epoch: {} segundos", duration_since_epoch.as_secs());
    println!("Nanosegundos adicionais: {}", duration_since_epoch.subsec_nanos());

    // 2. Relógio monotônico (para medição de tempo)
    let start = Instant::now();

    // Simular trabalho
    let mut sum = 0u64;
    for i in 0..1_000_000 {
        sum += i;
    }

    let elapsed = start.elapsed();
    println!("Trabalho levou: {:?}", elapsed);
    println!("Resultado: {}", sum);

    // 3. Cálculos com tempo
    let deadline = now + Duration::from_secs(30);
    println!("Deadline: {:?}", deadline);

    if SystemTime::now() > deadline {
        println!("Tempo esgotado!");
    } else {
        println!("Ainda temos tempo");
    }
}
```

### Permissões de relógio

O acesso ao relógio pode ser controlado:

```bash
# Sem acesso ao relógio
wasmtime app.wasm

# Com acesso ao relógio do sistema
wasmtime app.wasm --TC=system

# Com acesso ao relógio monotônico
wasmtime app.wasm --TC=monotonic
```

### Uso seguro de relógio

```rust
use std::time::{SystemTime, Instant};
use std::thread;
use std::time::Duration;

fn main() {
    // Medir tempo de operações
    let start = Instant::now();

    // Operação que queremos medir
    thread::sleep(Duration::from_millis(100));

    let elapsed = start.elapsed();
    println!("Operação levou: {:?}", elapsed);

    // Verificar se operação excedeu timeout
    let timeout = Duration::from_secs(5);
    if elapsed > timeout {
        eprintln!("AVISO: Operação excedeu timeout de {:?}", timeout);
    }

    // Usar relógio do sistema para timestamps
    let timestamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap()
        .as_secs();

    println!("Timestamp atual: {}", timestamp);
}
```

---

## 3.6 Aleatoriedade

### Geração de números aleatórios

WASI fornece acesso a números aleatórios criptograficamente seguros através da operação `random_get`.

**Características**:

1. **Criptograficamente seguro**: adequado para chaves, tokens, etc.
2. **Entropia do sistema**: usa fontes de entropia do sistema operacional
3. **Sem estado**: cada chamada é independente

**Exemplo de uso**:

```rust
use std::fs::File;
use std::io::Read;

fn get_random_bytes(count: usize) -> Vec<u8> {
    // No WASI, podemos usar /dev/urandom ou a syscall random_get
    let mut buffer = vec![0u8; count];

    // Método 1: Ler de /dev/urandom (se disponível)
    if let Ok(mut f) = File::open("/dev/urandom") {
        f.read_exact(&mut buffer).expect("Erro ao ler aleatórios");
        return buffer;
    }

    // Método 2: Usar random_get do WASI (via libc)
    unsafe {
        libc::random_get(buffer.as_mut_ptr() as *mut libc::c_void, buffer.len());
    }

    buffer
}

fn generate_token(length: usize) -> String {
    let random_bytes = get_random_bytes(length);
    random_bytes.iter()
        .map(|b| format!("{:02x}", b))
        .collect()
}

fn main() {
    // Gerar token aleatório
    let token = generate_token(32);
    println!("Token: {}", token);

    // Gerar número aleatório dentro de um intervalo
    let random_bytes = get_random_bytes(4);
    let random_value = u32::from_le_bytes([
        random_bytes[0],
        random_bytes[1],
        random_bytes[2],
        random_bytes[3],
    ]);

    let bounded = random_value % 100;  // 0-99
    println!("Número aleatório (0-99): {}", bounded);
}
```

### Segurança da aleatoriedade

**1. Não reutilizar aleatoriedade**

```rust
// ERRADO: reusar o mesmo seed
let seed = get_random_bytes(32);
// ... usar seed ...
// Mais tarde:
// let same_seed = seed; // ERRADO: não reutilizar

// CORRETO: gerar novo aleatório quando necessário
let new_random = get_random_bytes(32);
```

**2. Usar para propósito específico**

```rust
// CORRETO: usar para chaves criptográficas
let encryption_key = get_random_bytes(32);

// CORRETO: usar para nonces
let nonce = get_random_bytes(12);

// CORRETO: usar para IVs
let iv = get_random_bytes(16);
```

**3. Não armazenar aleatoriedade**

```rust
// ERRADO: armazenar números aleatórios para uso futuro
// let random_cache = get_random_bytes(1024);
// ... meses depois ...
// let r = random_cache[0]; // ERRADO: pode estar comprometido

// CORRETO: gerar aleatório sob demanda
let r = get_random_bytes(1)[0];
```

---

## 3.7 Variáveis de ambiente

### Acesso a variáveis de ambiente

WASI fornece acesso a variáveis de ambiente através das operações `environ_get` e `environ_sizes_get`.

**Exemplo de uso**:

```rust
use std::env;

fn main() {
    // Ler todas as variáveis de ambiente
    println!("Variáveis de ambiente:");
    for (key, value) in env::vars() {
        println!("  {}={}", key, value);
    }

    // Ler variável específica
    match env::var("PATH") {
        Ok(path) => println!("PATH: {}", path),
        Err(e) => eprintln!("Erro ao ler PATH: {}", e),
    }

    // Ler com valor padrão
    let log_level = env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string());
    println!("Nível de log: {}", log_level);

    // Verificar se variável existe
    if env::var("API_KEY").is_ok() {
        println!("API_KEY está configurada");
    } else {
        println!("API_KEY não está configurada");
    }

    // Definir variável (apenas no processo atual)
    env::set_var("CUSTOM_VAR", "valor_personalizado");
    println!("CUSTOM_VAR: {}", env::var("CUSTOM_VAR").unwrap());
}
```

### Permissões de variáveis de ambiente

O WASI permite controlar quais variáveis de ambiente o módulo pode acessar:

```bash
# Sem variáveis de ambiente
wasmtime app.wasm

# Com variáveis específicas
wasmtime app.wasm --env API_KEY=secret123 --env LOG_LEVEL=debug

# Com padrão de variáveis
wasmtime app.wasm --env APP_*=*  # todas começando com APP_
```

### Padrões de uso

**Padrão 1: Configuração via ambiente**

```rust
use std::env;

struct Config {
    database_url: String,
    api_key: String,
    log_level: String,
    max_connections: usize,
}

impl Config {
    fn from_env() -> Result<Self, String> {
        Ok(Config {
            database_url: env::var("DATABASE_URL")
                .map_err(|_| "DATABASE_URL não definida")?,
            api_key: env::var("API_KEY")
                .map_err(|_| "API_KEY não definida")?,
            log_level: env::var("LOG_LEVEL")
                .unwrap_or_else(|_| "info".to_string()),
            max_connections: env::var("MAX_CONNECTIONS")
                .unwrap_or_else(|_| "10".to_string())
                .parse()
                .map_err(|_| "MAX_CONNECTIONS inválida")?,
        })
    }
}

fn main() {
    let config = Config::from_env().expect("Erro na configuração");

    println!("Database: {}", config.database_url);
    println!("Log level: {}", config.log_level);
    println!("Max connections: {}", config.max_connections);
}
```

**Padrão 2: Feature flags**

```rust
use std::env;

fn main() {
    let enable_feature_x = env::var("ENABLE_FEATURE_X")
        .map(|v| v == "true")
        .unwrap_or(false);

    let enable_feature_y = env::var("ENABLE_FEATURE_Y")
        .map(|v| v == "true")
        .unwrap_or(false);

    if enable_feature_x {
        println!("Feature X habilitada");
    }

    if enable_feature_y {
        println!("Feature Y habilitada");
    }
}
```

---

## 3.8 Component Model Preview

### O que é o Component Model

O Component Model é a evolução do WASI que permite composição de módulos WebAssembly usando interfaces tipadas. Ele resolve muitas limitações do WASI Preview 1 e abre novas possibilidades para composição de software.

### Conceitos fundamentais

**1. Componentes**

Componentes são módulos WebAssembly que implementam ou consomem interfaces definidas em WIT:

```wit
// Definição de interface
package example:math;

interface calculator {
    add: func(a: s32, b: s32) -> s32;
    subtract: func(a: s32, b: s32) -> s32;
    multiply: func(a: s32, b: s32) -> s32;
    divide: func(a: s32, b: s32) -> result<s32, string>;
}

// Definição de mundo
world my-calculator {
    export calculator;
}
```

**2. World**

World define o contrato completo de um componente — o que ele importa e o que exporta:

```wit
world web-server {
    // Importações
    import wasi:cli/environment@0.2.0;
    import wasi:cli/stdin@0.2.0;
    import wasi:cli/stdout@0.2.0;
    import wasi:cli/stderr@0.2.0;
    import wasi:io/error@0.2.0;
    import wasi:io/streams@0.2.0;
    import wasi:http/types@0.2.0;

    // Exportações
    export wasi:http/incoming-handler@0.2.0;
}
```

**3. Validação de tipos**

O Component Model valida tipos entre componentes:

```wit
// Componente A exporta
interface data-source {
    record data-point {
        timestamp: u64,
        value: f64,
        metadata: string,
    }

    get-data: func() -> list<data-point>;
}

// Componente B importa e consome
interface data-processor {
    use data-source.{data-point};

    process: func(data: list<data-point>) -> list<data-point>;
}
```

### Vantagens do Component Model

**1. Composição segura**: componentes podem ser combinados com garantias de tipo

**2. Reuso**: interfaces bem definidas facilitam reuso de código

**3. Independência de linguagem**: componentes podem ser escritos em qualquer linguagem que suporte WIT

**4. Evolução**: interfaces podem evoluir sem quebrar compatibilidade

**5. Ferramentas**: suporte a ferramentas de análise e depuração

### Exemplo de composição

```wit
// Interface de storage
package example:storage;

interface storage {
    record config {
        endpoint: string,
        bucket: string,
    }

    handle storage;

    init: func(config: config) -> storage;
    put: func(s: storage, key: string, data: list<u8>) -> result<_, string>;
    get: func(s: storage, key: string) -> result<list<u8>, string>;
    delete: func(s: storage, key: string) -> result<_, string>;
}

// Interface de processamento
package example:processor;

interface processor {
    record input-data {
        content: string,
        format: string,
    }

    process: func(data: input-data) -> result<string, string>;
}

// Mundo que combina ambos
world data-pipeline {
    import storage;
    import processor;

    export run: func();
}
```

### Migração para Component Model

```rust
// Antes: usando WASI Preview 1
use std::fs;

fn main() {
    let content = fs::read_to_string("input.txt").unwrap();
    let processed = process(content);
    fs::write("output.txt", processed).unwrap();
}

// Depois: usando Component Model
// Requer suporte a WIT e componentes
// A definição de interface fica em .wit
// O código implementa a interface

// world data-processor {
//     import wasi:filesystem/types@0.2.0;
//     export process: func(input: string) -> string;
// }
```

---

## 3.9 Implicações de segurança

### Análise de segurança

O WASI introduz considerações de segurança únicas que não existem em outros modelos de sistema.

### Vetores de ataque

**1. Escalada de privilégios via capabilities**

Se um módulo consegue obter capabilities que não deveria ter, pode acessar recursos protegidos:

```bash
# CORRETO: módulo com permissões limitadas
wasmtime app.wasm --dir /data::read

# PERIGOSO: módulo com permissões excessivas
wasmtime app.wasm --dir /::read,write  # acesso total ao filesystem
```

**2. Bypass de restrições de rede**

Módulos podem tentar contornar restrições de rede:

```bash
# Restrição: só pode conectar a api.example.com
wasmtime app.wasm --tcp-connect api.example.com:443

# Ataque: tentar conectar a outros hosts
# O runtime deve rejeitar essas tentativas
```

**3. Exfiltração de dados via variáveis de ambiente**

Módulos podem tentar ler variáveis de ambiente sensíveis:

```bash
# CORRETO: expor apenas variáveis necessárias
wasmtime app.wasm --env API_KEY=secret123

# PERIGOSO: expor todas as variáveis
wasmtime app.wasm  # sem restrições
```

**4. Ataques de timing via relógio**

Módulos podem medir tempos para inferir informações:

```rust
// Possível ataque: medir tempo de operações
let start = Instant::now();
// ... operação que depende de dados secretos ...
let elapsed = start.elapsed();

// Se o tempo varia dependendo de dados secretos,
// informações podem ser vazadas
```

### Mitigações

**1. Princípio do menor privilégio**

```bash
# Conceder apenas o necessário
wasmtime app.wasm \
    --dir /data::read \
    --env API_KEY=secret123
```

**2. Validação de capabilities**

```rust
// O runtime deve validar que capabilities são respeitadas
fn validate_capabilities(module: &Module, capabilities: &Capabilities) -> bool {
    // Verificar se o módulo só usa capabilities que lhe foram concedidas
    // ...
}
```

**3. Auditing e logging**

```bash
# Habilitar logging de operações
wasmtime app.wasm --dir /data::read --log-level=trace

# Revisar logs regularmente
```

**4. Isolamento de instâncias**

```javascript
// Cada módulo com sua própria instância e capabilities
const instance1 = await WebAssembly.instantiate(module1, {
    env: { memory: new WebAssembly.Memory({ initial: 1 }) }
});

const instance2 = await WebAssembly.instantiate(module2, {
    env: { memory: new WebAssembly.Memory({ initial: 1 }) }
});

// instance1 e instance2 são completamente isolados
```

### Melhores práticas

**1. Definir capabilities minimalmente**

```bash
# Em vez de:
wasmtime app.wasm --dir /::read,write

# Use:
wasmtime app.wasm --dir /data::read --dir /tmp::write
```

**2. Usar variáveis de ambiente com cuidado**

```bash
# Em vez de expor todas as variáveis:
wasmtime app.wasm

# Expor apenas as necessárias:
wasmtime app.wasm --env API_KEY=secret123 --env LOG_LEVEL=info
```

**3. Limitar acesso à rede**

```bash
# Em vez de permitir qualquer conexão:
wasmtime app.wasm

# Restringir a hosts específicos:
wasmtime app.wasm --tcp-connect api.trusted.com:443
```

**4. Monitorar execução**

```rust
// Implementar monitoramento no host
fn monitor_execution(instance: &Instance) {
    // Verificar uso de memória
    // Verificar operações de I/O
    // Verificar tempo de execução
    // Verificar chamadas de sistema
}
```

**5. Usar timeouts**

```rust
// Implementar timeouts para prevenir loops infinitos
fn execute_with_timeout(instance: &Instance, timeout: Duration) -> Result<()> {
    let start = Instant::now();

    loop {
        if start.elapsed() > timeout {
            return Err(Error::Timeout);
        }

        // Executar uma instrução
        instance.step()?;

        if instance.is_finished() {
            return Ok(());
        }
    }
}
```

---

## 3.10 Aplicação WASI completa

### Projeto: Servidor HTTP em Rust com WASI

Este exemplo demonstra uma aplicação completa que usa WASI para implementar um servidor HTTP básico.

**Estrutura do projeto**:

```
http-server/
├── Cargo.toml
├── src/
│   ├── main.rs
│   ├── request.rs
│   ├── response.rs
│   └── handler.rs
└── wit/
    └── http-server.wit
```

**Cargo.toml**:

```toml
[package]
name = "wasi-http-server"
version = "0.1.0"
edition = "2021"

[dependencies]
wasi = "0.11.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[profile.release]
opt-level = "s"
lto = true
```

**src/main.rs**:

```rust
mod request;
mod response;
mod handler;

use std::io::{self, Read, Write, BufRead, BufReader};
use std::net::{TcpListener, TcpStream};
use std::thread;
use std::time::Duration;
use std::env;

use handler::RequestHandler;

fn main() -> io::Result<()> {
    // 1. Ler configuração de variáveis de ambiente
    let host = env::var("HOST").unwrap_or_else(|_| "0.0.0.0".to_string());
    let port = env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let max_connections: usize = env::var("MAX_CONNECTIONS")
        .unwrap_or_else(|_| "100".to_string())
        .parse()
        .unwrap_or(100);

    let addr = format!("{}:{}", host, port);
    println!("Servidor HTTP ouvindo em {}", addr);

    // 2. Criar listener
    let listener = TcpListener::bind(&addr)?;
    listener.set_nonblocking(false)?;

    // 3. Criar handler de requisições
    let handler = RequestHandler::new();

    // 4. Aceitar conexões
    let mut active_connections = 0;

    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                if active_connections >= max_connections {
                    eprintln!("Número máximo de conexões atingido");
                    drop(stream);
                    continue;
                }

                active_connections += 1;
                let handler_clone = handler.clone();

                thread::spawn(move || {
                    if let Err(e) = handle_connection(stream, handler_clone) {
                        eprintln!("Erro ao processar conexão: {}", e);
                    }
                    // Nota: em produção, decrementaríamos active_connections aqui
                });
            }
            Err(e) => {
                eprintln!("Erro ao aceitar conexão: {}", e);
                thread::sleep(Duration::from_millis(100));
            }
        }
    }

    Ok(())
}

fn handle_connection(mut stream: TcpStream, handler: RequestHandler) -> io::Result<()> {
    // Configurar timeout
    stream.set_read_timeout(Some(Duration::from_secs(30)))?;
    stream.set_write_timeout(Some(Duration::from_secs(30)))?;

    // Ler requisição HTTP
    let request = read_http_request(&mut stream)?;

    // Processar requisição
    let response = handler.handle(request);

    // Enviar resposta
    write_http_response(&mut stream, &response)?;

    Ok(())
}

fn read_http_request(stream: &mut TcpStream) -> io::Result<request::HttpRequest> {
    let mut reader = BufReader::new(stream);

    // Ler linha de requisição
    let mut request_line = String::new();
    reader.read_line(&mut request_line)?;

    let parts: Vec<&str> = request_line.trim().split_whitespace().collect();
    if parts.len() < 3 {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "Requisição HTTP inválida"));
    }

    let method = parts[0].to_string();
    let path = parts[1].to_string();
    let version = parts[2].to_string();

    // Ler headers
    let mut headers = std::collections::HashMap::new();
    loop {
        let mut line = String::new();
        reader.read_line(&mut line)?;

        let line = line.trim().to_string();
        if line.is_empty() {
            break;
        }

        if let Some((key, value)) = line.split_once(':') {
            headers.insert(
                key.trim().to_lowercase(),
                value.trim().to_string(),
            );
        }
    }

    // Ler body (se houver)
    let body = if let Some(content_length) = headers.get("content-length") {
        let length: usize = content_length.parse().unwrap_or(0);
        let mut buffer = vec![0u8; length];
        reader.read_exact(&mut buffer)?;
        String::from_utf8_lossy(&buffer).to_string()
    } else {
        String::new()
    };

    Ok(request::HttpRequest {
        method,
        path,
        version,
        headers,
        body,
    })
}

fn write_http_response(stream: &mut TcpStream, response: &response::HttpResponse) -> io::Result<()> {
    // Status line
    let status_line = format!(
        "HTTP/{} {} {}\r\n",
        response.version,
        response.status_code,
        response.status_text
    );
    stream.write_all(status_line.as_bytes())?;

    // Headers
    for (key, value) in &response.headers {
        let header = format!("{}: {}\r\n", key, value);
        stream.write_all(header.as_bytes())?;
    }

    // Empty line
    stream.write_all(b"\r\n")?;

    // Body
    stream.write_all(response.body.as_bytes())?;

    Ok(())
}
```

**src/request.rs**:

```rust
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct HttpRequest {
    pub method: String,
    pub path: String,
    pub version: String,
    pub headers: HashMap<String, String>,
    pub body: String,
}

impl HttpRequest {
    pub fn header(&self, key: &str) -> Option<&String> {
        self.headers.get(&key.to_lowercase())
    }

    pub fn content_type(&self) -> Option<&String> {
        self.header("content-type")
    }

    pub fn content_length(&self) -> usize {
        self.header("content-length")
            .and_then(|v| v.parse().ok())
            .unwrap_or(0)
    }

    pub fn is_json(&self) -> bool {
        self.content_type()
            .map(|ct| ct.contains("application/json"))
            .unwrap_or(false)
    }
}
```

**src/response.rs**:

```rust
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub version: String,
    pub status_code: u16,
    pub status_text: String,
    pub headers: HashMap<String, String>,
    pub body: String,
}

impl HttpResponse {
    pub fn ok() -> Self {
        let mut headers = HashMap::new();
        headers.insert("Content-Type".to_string(), "text/plain".to_string());

        HttpResponse {
            version: "1.1".to_string(),
            status_code: 200,
            status_text: "OK".to_string(),
            headers,
            body: String::new(),
        }
    }

    pub fn json(data: &str) -> Self {
        let mut response = Self::ok();
        response.headers.insert(
            "Content-Type".to_string(),
            "application/json".to_string(),
        );
        response.body = data.to_string();
        response
    }

    pub fn not_found() -> Self {
        let mut response = Self::ok();
        response.status_code = 404;
        response.status_text = "Not Found".to_string();
        response.body = "404 Not Found".to_string();
        response
    }

    pub fn internal_error(message: &str) -> Self {
        let mut response = Self::ok();
        response.status_code = 500;
        response.status_text = "Internal Server Error".to_string();
        response.body = format!("500 Internal Server Error: {}", message);
        response
    }

    pub fn bad_request(message: &str) -> Self {
        let mut response = Self::ok();
        response.status_code = 400;
        response.status_text = "Bad Request".to_string();
        response.body = format!("400 Bad Request: {}", message);
        response
    }
}
```

**src/handler.rs**:

```rust
use crate::request::HttpRequest;
use crate::response::HttpResponse;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct RequestHandler {
    routes: Arc<Mutex<HashMap<String, Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>>>>,
}

impl RequestHandler {
    pub fn new() -> Self {
        let mut routes = HashMap::new();

        // Rota: GET /
        routes.insert(
            "GET /".to_string(),
            Box::new(|_req: &HttpRequest| -> HttpResponse {
                let mut response = HttpResponse::ok();
                response.body = "Bem-vindo ao servidor HTTP WASI!".to_string();
                response
            }) as Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>,
        );

        // Rota: GET /health
        routes.insert(
            "GET /health".to_string(),
            Box::new(|_req: &HttpRequest| -> HttpResponse {
                let health = serde_json::json!({
                    "status": "healthy",
                    "timestamp": std::time::SystemTime::now()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_secs()
                });
                HttpResponse::json(&health.to_string())
            }) as Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>,
        );

        // Rota: GET /info
        routes.insert(
            "GET /info".to_string(),
            Box::new(|req: &HttpRequest| -> HttpResponse {
                let info = serde_json::json!({
                    "method": req.method,
                    "path": req.path,
                    "version": req.version,
                    "headers": req.headers,
                });
                HttpResponse::json(&info.to_string())
            }) as Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>,
        );

        // Rota: POST /echo
        routes.insert(
            "POST /echo".to_string(),
            Box::new(|req: &HttpRequest| -> HttpResponse {
                let mut response = HttpResponse::ok();
                response.headers.insert(
                    "Content-Type".to_string(),
                    req.content_type()
                        .cloned()
                        .unwrap_or_else(|| "text/plain".to_string()),
                );
                response.body = req.body.clone();
                response
            }) as Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>,
        );

        RequestHandler {
            routes: Arc::new(Mutex::new(routes)),
        }
    }

    pub fn handle(&self, request: HttpRequest) -> HttpResponse {
        let route_key = format!("{} {}", request.method, request.path);

        let routes = self.routes.lock().unwrap();

        if let Some(handler) = routes.get(&route_key) {
            handler(&request)
        } else if let Some(handler) = routes.get(&format!("{} /*", request.method)) {
            handler(&request)
        } else {
            HttpResponse::not_found()
        }
    }

    pub fn add_route(
        &self,
        method: &str,
        path: &str,
        handler: impl Fn(&HttpRequest) -> HttpResponse + Send + Sync + 'static,
    ) {
        let route_key = format!("{} {}", method, path);
        let mut routes = self.routes.lock().unwrap();
        routes.insert(route_key, Box::new(handler));
    }
}

impl Default for RequestHandler {
    fn default() -> Self {
        Self::new()
    }
}
```

### Compilação e execução

**Compilar para WASI**:

```bash
# Adicionar target WASI
rustup target add wasm32-wasi

# Compilar em modo release
cargo build --target wasm32-wasi --release

# O binário está em:
# target/wasm32-wasi/release/wasi-http-server.wasm
```

**Executar com Wasmtime**:

```bash
# Executar com permissões básicas
wasmtime target/wasm32-wasi/release/wasi-http-server.wasm

# Executar com configuração
wasmtime target/wasm32-wasi/release/wasi-http-server.wasm \
    --env HOST=0.0.0.0 \
    --env PORT=8080 \
    --env MAX_CONNECTIONS=50 \
    --tcplisten 0.0.0.0:8080

# Executar com logging
wasmtime target/wasm32-wasi/release/wasi-http-server.wasm \
    --env RUST_LOG=debug \
    --tcplisten 0.0.0.0:8080
```

**Testar o servidor**:

```bash
# Rota principal
curl http://localhost:8080/
# Resposta: Bem-vindo ao servidor HTTP WASI!

# Health check
curl http://localhost:8080/health
# Resposta: {"status":"healthy","timestamp":1234567890}

# Info
curl http://localhost:8080/info
# Resposta: informações da requisição

# Echo
curl -X POST http://localhost:8080/echo \
    -H "Content-Type: application/json" \
    -d '{"message": "hello"}'
# Resposta: {"message": "hello"}

# 404
curl http://localhost:8080/nonexistent
# Resposta: 404 Not Found
```

### Funcionalidades avançadas

**1. Middleware**:

```rust
pub trait Middleware: Send + Sync {
    fn before_request(&self, request: &mut HttpRequest) -> bool;
    fn after_request(&self, request: &HttpRequest, response: &mut HttpResponse);
}

pub struct LoggingMiddleware;

impl Middleware for LoggingMiddleware {
    fn before_request(&self, request: &mut HttpRequest) -> bool {
        println!("{} {} {}", request.method, request.path, request.version);
        true
    }

    fn after_request(&self, request: &HttpRequest, response: &mut HttpResponse) {
        println!("{} {} -> {}", request.method, request.path, response.status_code);
    }
}

pub struct RateLimitMiddleware {
    max_requests: usize,
    window: Duration,
    requests: Arc<Mutex<HashMap<String, Vec<Instant>>>>,
}
```

**2. Router com parâmetros**:

```rust
pub struct Router {
    routes: Vec<(String, Box<dyn Fn(&HttpRequest) -> HttpResponse + Send + Sync>)>,
}

impl Router {
    pub fn new() -> Self {
        Router { routes: Vec::new() }
    }

    pub fn add_route(&mut self, pattern: &str, handler: impl Fn(&HttpRequest) -> HttpResponse + Send + Sync + 'static) {
        self.routes.push((pattern.to_string(), Box::new(handler)));
    }

    pub fn handle(&self, request: &HttpRequest) -> HttpResponse {
        for (pattern, handler) in &self.routes {
            if self.matches(pattern, &request.path) {
                return handler(request);
            }
        }
        HttpResponse::not_found()
    }

    fn matches(&self, pattern: &str, path: &str) -> bool {
        let pattern_parts: Vec<&str> = pattern.split('/').collect();
        let path_parts: Vec<&str> = path.split('/').collect();

        if pattern_parts.len() != path_parts.len() {
            return false;
        }

        for (pp, pat) in path_parts.iter().zip(pattern_parts.iter()) {
            if pat.starts_with(':') {
                // Parâmetro dinâmico
                continue;
            }
            if pp != pat {
                return false;
            }
        }

        true
    }
}
```

**3. Serialização JSON**:

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
struct ApiResponse<T: Serialize> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

impl<T: Serialize> ApiResponse<T> {
    pub fn success(data: T) -> Self {
        ApiResponse {
            success: true,
            data: Some(data),
            error: None,
        }
    }

    pub fn error(message: &str) -> Self {
        ApiResponse {
            success: false,
            data: None,
            error: Some(message.to_string()),
        }
    }

    pub fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap()
    }
}
```

### Considerações de produção

**1. Tratamento de erros**:

```rust
impl RequestHandler {
    pub fn handle_with_error_handling(&self, request: HttpRequest) -> HttpResponse {
        match std::panic::catch_unwind(|| {
            self.handle(request)
        }) {
            Ok(response) => response,
            Err(_) => HttpResponse::internal_error("Erro interno no servidor"),
        }
    }
}
```

**2. Limitação de recursos**:

```rust
use std::time::{Duration, Instant};

fn execute_with_timeout<F, T>(f: F, timeout: Duration) -> Result<T, String>
where
    F: FnOnce() -> T,
{
    let start = Instant::now();
    let result = f();

    if start.elapsed() > timeout {
        return Err("Timeout".to_string());
    }

    Ok(result)
}
```

**3. Logging estruturado**:

```rust
use std::io::Write;

struct Logger {
    output: Box<dyn Write + Send>,
}

impl Logger {
    pub fn log(&mut self, level: &str, message: &str) {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        writeln!(self.output, "[{}] {}: {}", timestamp, level, message).unwrap();
    }

    pub fn info(&mut self, message: &str) {
        self.log("INFO", message);
    }

    pub fn error(&mut self, message: &str) {
        self.log("ERROR", message);
    }

    pub fn warn(&mut self, message: &str) {
        self.log("WARN", message);
    }
}
```

---

## Resumo

Neste capítulo, exploramos WASI e a interface de sistema do WebAssembly:

- **WASI Preview 1 vs Preview 2**: evolução de file descriptors para Component Model
- **Modelo de capacidades**: acesso a recursos através de referências, não de ACLs
- **Sistema de arquivos**: operações de arquivo com permissões granulares
- **Rede**: acesso controlado a TCP/UDP com capabilities
- **Relógios**: acesso a wall clock e monotonic clock
- **Aleatoriedade**: geração de números criptograficamente seguros
- **Variáveis de ambiente**: acesso controlado a configurações
- **Component Model**: composição de módulos com interfaces tipadas
- **Implicações de segurança**: vetores de ataque e mitigações
- **Aplicação completa**: servidor HTTP usando WASI

WASI é o que transforma WebAssembly de uma tecnologia de navegador em uma plataforma de computação universal. O modelo de capacidades do WASI oferece segurança sem precedentes, enquanto o Component Model abre caminhos para composição de software de forma segura e portável.

---

## 3.11 Interoperabilidade entre linguagens via WASI

### O problema da interoperabilidade

Um dos maiores desafios do desenvolvimento de software é a interoperabilidade entre diferentes linguagens de programação. Tradicionalmente, isso é feito através de FFI (Foreign Function Interface), que é complexa, insegura e dependente de plataforma.

WASI resolve isso ao definir uma interface padrão que qualquer linguagem pode implementar. Se duas linguagens compilam para WASI, elas podem compartilhar dados e funcionalidades de forma segura e portável.

### Exemplo: Rust chamando C via WASI

**Componente C**:

```c
// math_component.c
#include <stdint.h>

int32_t add_integers(int32_t a, int32_t b) {
    return a + b;
}

float64_t multiply_floats(float64_t a, float64_t b) {
    return a * b;
}

int32_t factorial(int32_t n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

int32_t fibonacci(int32_t n) {
    if (n <= 1) return n;
    int32_t a = 0, b = 1;
    for (int32_t i = 2; i <= n; i++) {
        int32_t temp = b;
        b = a + b;
        a = temp;
    }
    return b;
}
```

Compilação:

```bash
/opt/wasi-sdk/bin/clang -O3 -o math_component.wasm math_component.c
```

**Componente Rust consumindo C**:

```rust
// src/main.rs
use std::process::Command;
use std::fs;

// Definir importações WASI para o componente C
extern "C" {
    fn add_integers(a: i32, b: i32) -> i32;
    fn multiply_floats(a: f64, b: f64) -> f64;
    fn factorial(n: i32) -> i32;
    fn fibonacci(n: i32) -> i32;
}

fn main() {
    // Na prática, usaríamos wasm-compose ou similar
    // para compor componentes

    println!("Demonstração de interoperabilidade via WASI");
    println!("============================================");

    // Em um sistema real, essas funções seriam importadas
    // de outro componente WASI

    let a = 10;
    let b = 20;
    println!("{} + {} = {}", a, b, a + b);

    let x = 3.14;
    let y = 2.0;
    println!("{} * {} = {}", x, y, x * y);

    let n = 10;
    println!("{}! = {}", n, (1..=n).product::<i64>());

    let fib_n = 20;
    println!("fibonacci({}) = {}", fib_n, fibonacci(fib_n));
}

fn fibonacci(n: i32) -> i64 {
    if n <= 1 { return n as i64; }
    let mut a: i64 = 0;
    let mut b: i64 = 1;
    for _ in 2..=n {
        let temp = b;
        b = a + b;
        a = temp;
    }
    b
}
```

### Exemplo: Go chamando Rust via WASI

**Componente Rust**:

```rust
// lib.rs
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn process_string(input: &str) -> String {
    input.chars()
        .map(|c| {
            if c.is_uppercase() {
                c.to_lowercase().next().unwrap()
            } else {
                c.to_uppercase().next().unwrap()
            }
        })
        .collect()
}

#[wasm_bindgen]
pub fn validate_email(email: &str) -> bool {
    let parts: Vec<&str> = email.split('@').collect();
    if parts.len() != 2 {
        return false;
    }

    let local = parts[0];
    let domain = parts[1];

    // Verificações básicas
    if local.is_empty() || domain.is_empty() {
        return false;
    }

    if !domain.contains('.') {
        return false;
    }

    // Verificar caracteres válidos
    let valid_chars = |c: char| c.is_alphanumeric() || c == '.' || c == '_' || c == '-' || c == '+';
    if !local.chars().all(valid_chars) || !domain.chars().all(valid_chars) {
        return false;
    }

    true
}

#[wasm_bindgen]
pub fn hash_string(input: &str) -> String {
    use std::collections::hash_map::DefaultHasher;
    use std::hash::{Hash, Hasher};

    let mut hasher = DefaultHasher::new();
    input.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}
```

**Componente Go consumindo Rust**:

```go
// main.go
package main

import (
    "fmt"
    "syscall/js"
)

// Funções importadas do componente Rust
var (
    processString = js.Global().Get("process_string")
    validateEmail = js.Global().Get("validate_email")
    hashString    = js.Global().Get("hash_string")
)

func main() {
    fmt.Println("Interoperabilidade Go -> Rust via WASI")

    // Usar função Rust
    input := "hello world"
    result := processString.Invoke(input)
    fmt.Printf("process_string(%q) = %q\n", input, result.String())

    // Validar email
    emails := []string{
        "user@example.com",
        "invalid-email",
        "test@domain.org",
        "@missing-local.com",
    }

    for _, email := range emails {
        valid := validateEmail.Invoke(email)
        fmt.Printf("validate_email(%q) = %v\n", email, valid.Bool())
    }

    // Hash de string
    data := "sensitive data"
    hash := hashString.Invoke(data)
    fmt.Printf("hash_string(%q) = %q\n", data, hash.String())
}
```

### Vantagens da interoperabilidade via WASI

| Aspecto | FFI tradicional | WASI |
|---------|-----------------|------|
| Segurança | Baixa (acesso direto à memória) | Alta (sandbox) |
| Portabilidade | Baixa (depende de ABI) | Alta (padrão W3C) |
| Facilidade | Baixa (configuração complexa) | Alta (composição declarativa) |
| Performance | Alta (chamada direta) | Média (overhead de chamada) |
| Manutenção | Difícil (muda com versões) | Fácil (interfaces estáveis) |

---

## 3.12 Deployment e operações

### Empacotamento de aplicações WASI

**Ferramenta warg (WebAssembly Registry)**:

```bash
# Instalar warg
cargo install warg

# Publicar componente
warg publish my-component.wasm

# Puxar componente
warg pull example/component:1.0.0
```

**Estrutura de pacote**:

```
my-app/
├── Cargo.toml
├── wit/
│   └── world.wit
├── src/
│   └── lib.rs
└── dist/
    ├── component.wasm
    └── metadata.json
```

### Containerização de aplicações WASI

**Dockerfile para WASI**:

```dockerfile
FROM wasmtime/wasmtime:latest AS runtime

FROM scratch

# Copiar binário WASI
COPY --from=runtime /usr/local/bin/wasmtime /wasmtime
COPY target/wasm32-wasi/release/my-app.wasm /app.wasm

# Configurar permissões
USER 1000:1000

# Executar
ENTRYPOINT ["/wasmtime"]
CMD ["--dir", "/data::read", "--env", "LOG_LEVEL=info", "/app.wasm"]
```

**Docker Compose para múltiplos componentes**:

```yaml
version: '3.8'

services:
  api-gateway:
    image: wasmtime/wasmtime:latest
    command: >
      --dir /config::read
      --tcplisten 0.0.0.0:8080
      --tcp-connect backend:8080
      /gateway.wasm
    ports:
      - "8080:8080"
    volumes:
      - ./config:/config:ro

  backend:
    image: wasmtime/wasmtime:latest
    command: >
      --dir /data::read,write
      --env DATABASE_URL=postgres://db:5432/mydb
      /backend.wasm
    volumes:
      - data:/data

  worker:
    image: wasmtime/wasmtime:latest
    command: >
      --dir /data::read
      --env REDIS_URL=redis://redis:6379
      /worker.wasm
    volumes:
      - data:/data:ro

volumes:
  data:
```

### Kubernetes com WASI

**Custom Resource Definition para WASI**:

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: wasiapps.devsec.io
spec:
  group: devsec.io
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              properties:
                image:
                  type: string
                args:
                  type: array
                  items:
                    type: string
                env:
                  type: array
                  items:
                    type: object
                    properties:
                      name:
                        type: string
                      value:
                        type: string
                capabilities:
                  type: object
                  properties:
                    filesystem:
                      type: array
                      items:
                        type: object
                    network:
                      type: array
                      items:
                        type: object
  scope: Namespaced
  names:
    plural: wasiapps
    singular: wasiapp
    kind: WASIApp
```

**Recurso WASIApp**:

```yaml
apiVersion: devsec.io/v1
kind: WASIApp
metadata:
  name: my-wasi-app
  namespace: default
spec:
  image: registry.example.com/my-app:1.0.0
  args:
    - "--port"
    - "8080"
  env:
    - name: LOG_LEVEL
      value: "info"
    - name: DATABASE_URL
      valueFrom:
        secretKeyRef:
          name: db-secret
          key: url
  capabilities:
    filesystem:
      - path: /data
        access: read,write
    network:
      - host: api.example.com
        port: 443
```

### Monitoramento de aplicações WASI

**Métricas**:

```rust
use std::time::Instant;
use std::sync::atomic::{AtomicU64, Ordering};

struct Metrics {
    request_count: AtomicU64,
    error_count: AtomicU64,
    total_duration_us: AtomicU64,
}

impl Metrics {
    fn new() -> Self {
        Metrics {
            request_count: AtomicU64::new(0),
            error_count: AtomicU64::new(0),
            total_duration_us: AtomicU64::new(0),
        }
    }

    fn record_request(&self, duration_us: u64, is_error: bool) {
        self.request_count.fetch_add(1, Ordering::Relaxed);
        self.total_duration_us.fetch_add(duration_us, Ordering::Relaxed);
        if is_error {
            self.error_count.fetch_add(1, Ordering::Relaxed);
        }
    }

    fn get_stats(&self) -> (u64, u64, f64) {
        let count = self.request_count.load(Ordering::Relaxed);
        let errors = self.error_count.load(Ordering::Relaxed);
        let total_us = self.total_duration_us.load(Ordering::Relaxed);

        let avg_duration = if count > 0 {
            total_us as f64 / count as f64
        } else {
            0.0
        };

        (count, errors, avg_duration)
    }
}
```

**Health check endpoint**:

```rust
fn health_check(metrics: &Metrics) -> HttpResponse {
    let (request_count, error_count, avg_duration) = metrics.get_stats();

    let error_rate = if request_count > 0 {
        error_count as f64 / request_count as f64
    } else {
        0.0
    };

    let status = if error_rate < 0.05 && avg_duration < 1000.0 {
        "healthy"
    } else if error_rate < 0.10 {
        "degraded"
    } else {
        "unhealthy"
    };

    HttpResponse::json(serde_json::json!({
        "status": status,
        "metrics": {
            "request_count": request_count,
            "error_count": error_count,
            "error_rate": error_rate,
            "avg_duration_us": avg_duration
        }
    }))
}
```

### Logs estruturados

```rust
use serde_json::json;

fn log_request(method: &str, path: &str, status: u16, duration_us: u64) {
    let log_entry = json!({
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "level": "info",
        "message": "request completed",
        "method": method,
        "path": path,
        "status": status,
        "duration_us": duration_us,
        "service": "wasi-app",
        "version": env!("CARGO_PKG_VERSION")
    });

    println!("{}", log_entry);
}

fn log_error(error: &str, context: &str) {
    let log_entry = json!({
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "level": "error",
        "message": error,
        "context": context,
        "service": "wasi-app",
        "version": env!("CARGO_PKG_VERSION")
    });

    eprintln!("{}", log_entry);
}
```

---

## 3.13 Casos de uso reais

### Edge Computing com WASI

Empresas estão adotando WASI para edge computing devido ao cold start baixo e à portabilidade:

```rust
// Exemplo: função de edge computing para processamento de imagens
use std::env;
use std::io::{self, Read};

fn main() -> io::Result<()> {
    // Ler configuração de edge
    let edge_region = env::var("EDGE_REGION").unwrap_or_else(|_| "unknown".to_string());
    let edge_node = env::var("EDGE_NODE").unwrap_or_else(|_| "unknown".to_string());

    // Processar requisição
    let mut input = Vec::new();
    io::stdin().read_to_end(&mut input)?;

    // Lógica de processamento
    let result = process_at_edge(&input, &edge_region)?;

    // Retornar resultado
    io::stdout().write_all(&result)?;

    Ok(())
}

fn process_at_edge(data: &[u8], region: &str) -> io::Result<Vec<u8>> {
    // Processamento específico da região
    match region {
        "us-east" => process_us_east(data),
        "eu-west" => process_eu_west(data),
        "ap-south" => process_ap_south(data),
        _ => process_default(data),
    }
}
```

### Serverless com WASI

Plataformas como Fermyon Spin usam WASI para serverless com cold start quase instantâneo:

```rust
// Exemplo: aplicação serverless com Spin
use spin_sdk::http::{IntoResponse, Request, Response};
use spin_sdk::http_component;

#[http_component]
fn handle_request(req: Request) -> Response {
    let path = req.uri().path();

    match path {
        "/" => Response::builder()
            .status(200)
            .body("Hello from WASI Serverless!")
            .build(),
        "/health" => Response::builder()
            .status(200)
            .body("healthy")
            .build(),
        _ => Response::builder()
            .status(404)
            .body("Not Found")
            .build(),
    }
}
```

### Plugins seguros com WASI

WASI permite executar plugins de terceiros de forma segura:

```rust
// Exemplo: sistema de plugins seguro
use std::collections::HashMap;

struct PluginManager {
    plugins: HashMap<String, Plugin>,
}

struct Plugin {
    name: String,
    capabilities: Vec<String>,
    instance: wasmtime::Instance,
}

impl PluginManager {
    fn load_plugin(&mut self, name: &str, wasm_path: &str, caps: Vec<String>) {
        // Criar capacidades limitadas para o plugin
        let mut store = wasmtime::Store::default();
        let module = wasmtime::Module::from_file(store.engine(), wasm_path).unwrap();

        // Definir imports com capacidades limitadas
        let imports = self.create_limited_imports(&caps);

        let instance = wasmtime::Instance::new(&mut store, &module, &imports).unwrap();

        self.plugins.insert(name.to_string(), Plugin {
            name: name.to_string(),
            capabilities: caps,
            instance,
        });
    }

    fn execute_plugin(&self, name: &str, input: &str) -> Result<String, String> {
        let plugin = self.plugins.get(name)
            .ok_or_else(|| format!("Plugin {} not found", name))?;

        // Verificar se o plugin tem permissão
        if !plugin.capabilities.contains(&"execute".to_string()) {
            return Err("Plugin not authorized to execute".to_string());
        }

        // Executar plugin
        // ... lógica de execução ...

        Ok("Plugin executed successfully".to_string())
    }
}
```

### Multi-tenancy com WASI

WASI é ideal para ambientes multi-tenant onde múltiplos usuários executam código não confiável:

```rust
// Exemplo: plataforma multi-tenant
struct TenantIsolation {
    tenants: HashMap<String, Tenant>,
}

struct Tenant {
    id: String,
    memory_limit: u32,
    cpu_limit: u64,
    capabilities: Capabilities,
}

impl TenantIsolation {
    fn create_tenant(&mut self, id: &str, config: TenantConfig) {
        let capabilities = Capabilities::new()
            .with_memory_limit(config.memory_limit)
            .with_cpu_limit(config.cpu_limit)
            .with_filesystem_access(&config.allowed_paths)
            .with_network_access(&config.allowed_hosts);

        self.tenants.insert(id.to_string(), Tenant {
            id: id.to_string(),
            memory_limit: config.memory_limit,
            cpu_limit: config.cpu_limit,
            capabilities,
        });
    }

    fn execute_for_tenant(&self, tenant_id: &str, module: &[u8]) -> Result<Vec<u8>, Error> {
        let tenant = self.tenants.get(tenant_id)
            .ok_or_else(|| Error::TenantNotFound)?;

        // Criar instância isolada com capacidades do tenant
        let instance = create_isolated_instance(module, &tenant.capabilities)?;

        // Executar com limites do tenant
        execute_with_limits(instance, tenant.memory_limit, tenant.cpu_limit)
    }
}
```

---

## Referências

1. **Especificação WASI**: https://github.com/WebAssembly/WASI
2. **WIT (WebAssembly Interface Types)**: https://github.com/WebAssembly/component-model
3. **Wasmtime**: https://wasmtime.dev/
4. **Wasmer**: https://wasmer.io/
5. **WasmEdge**: https://wasmedge.org/
6. **Bytecode Alliance**: https://bytecodealliance.org/
7. **Fermyon Spin**: https://www.fermyon.com/spin
8. **Cosmonic**: https://cosmonic.com/

---

## Glossário

| Termo | Definição |
|-------|-----------|
| **WASI** | WebAssembly System Interface — interface para acesso ao SO |
| **Preview 1** | Primeira versão estável do WASI |
| **Preview 2** | Segunda versão com Component Model |
| **WIT** | WebAssembly Interface Types — linguagem para definir interfaces |
| **Component Model** | Modelo de composição de módulos Wasm |
| **Capability** | Referência que concede acesso a um recurso |
| **Preopen** | Descritor de arquivo pré-aberto concedido ao módulo |
| **World** | Contrato completo de um componente (imports/exports) |
| **Handle** | Referência opaque a um recurso gerenciado pelo runtime |
| **Stream** | Fluxo de dados para I/O assíncrona |
| **Future** | Valor que estará disponível no futuro |
| **Trap** | Exceção fatal que encerra a execução |
| **Instance** | Execução concreta de um módulo |
| **Module** | Código WebAssembly compilado e validado |
---

*[Capítulo anterior: 02 — Modelo Seguranca](02-modelo-seguranca.md)*
*[Próximo capítulo: 04 — Rust Wasm](04-rust-wasm.md)*
