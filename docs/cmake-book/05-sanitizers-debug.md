---
layout: default
title: "05-sanitizers-debug"
---

# Capitulo 05 — Sanitizers e Debug Builds

> *"Um bug de memoria que so aparece em producao e um bug que ninguem quis encontrar."*

---

## Objetivos de Aprendizado

Apos completar este capitulo, voce sera capaz de:

- Configurar AddressSanitizer (ASan) para detectar erros de memoria em projetos C/C++
- Usar ThreadSanitizer (TSan) para identificar data races e potenciais deadlocks
- Aplicar UndefinedBehaviorSanitizer (UBSan) para detectar comportamento indefinido
- Configurar MemorySanitizer (MSan) para encontrar leituras de memoria nao inicializada
- Integrar sanitizers em CMakeLists.txt usando `target_compile_options` e `option()`
- Respeitar regras de exclusao mutua entre sanitizers
- Combinar ASan com UBSan de forma segura
- Criar suppressions para TSan em projetos com codigo legado
- Integrar sanitizers em pipelines CI/CD com falhas automaticas
- Analisar o impacto de performance de cada sanitizer
- Configurar builds de debug com `-g` e `-O0`
- Comparar Valgrind com sanitizers e escolher a ferramenta correta

---

## 5.1 Por Que Sanitizers Importam na Seguranca

Antes de mergulhar nos detalhes tecnicos, e fundamental entender porque sanitizers sao uma ferramenta critica de seguranca. A maioria das vulnerabilidades de seguranca em software C/C++ tem origem em erros de memoria:

- **Buffer overflows**: escrever alem dos limites de um array
- **Use-after-free**: acessar memoria que ja foi liberada
- **Double-free**: liberar a mesma memoria duas vezes
- **Memory leaks**: nao liberar memoria alocada
- **Data races**: acessos concorrentes sem sincronizacao
- **Comportamento indefinido**: operacoes que o padrao nao define

Esses erros nao apenas causam crashes — eles podem ser explorados para executar codigo arbitrario, escprivilegios, ou vazar dados sensiveis. Historicos reais mostram a gravidade:

**Heartbleed (CVE-2014-0160)**: Um buffer over-read no OpenSSL permitiu que atacantes lessem ate 64KB de memoria do servidor. O bug existia por anos sem ser detectado. Um sanitizer de memoria teria capturado a leitura fora dos limites imediatamente.

**Cloudbleed (CVE-2017-5882)**: Um bug de buffer overflow no Cloudflare vazou dados de clientes como tokens de autenticacao e chaves privadas. Memory sanitizers teriam detectado o overflow antes do deploy.

**CVE-2021-22555**: Um double-free no kernel do Linux (netfilter) permitiu escprivilegios. O bug existia desde o kernel 2.6.19 (2006) e so foi encontrado em 2021. ASan em testes automatizados poderia ter capturado isso em qualquer versao.

A pratica de executar sanitizers durante desenvolvimento e testes transforma esses bugs de "vulnerabilidades de producao" em "erros de compilacao" — encontrados minutos apos a escrita do codigo, nao anos depois em producao.

### 5.1.1 Historico dos Sanitizers

Os sanitizers foram criados no Google, com AddressSanitizer sendo publicado em 2012 por Konstantin Serebryany, Evgeniy Stepanov e Dmitry Vyukov. O projeto original era parte do LLVM/Compiler-RT e rapidamente se expandiu:

| Ano | Evento |
|-----|--------|
| 2012 | AddressSanitizer publicado no Google |
| 2013 | ThreadSanitizer v2 lancado |
| 2014 | MemorySanitizer adicionado ao Clang |
| 2015 | UndefinedBehaviorSanitizer adicionado ao Clang |
| 2016 | Sanitizers integrados ao GCC |
| 2017 | LeakSanitizer integrado ao ASan |
| 2019 | HWASan (Hardware Address Sanitizer) para ARM |
| 2021 | Scudo sanitizer integrado ao Android |
| 2023 | Scudo, GWP-San, e MTE no Android 14 |

O sucesso dos sanitizers no Google foi massivo — eles encontraram milhares de bugs em projetos como Chromium, Android, OpenSSL e kernel do Linux. Segundo dados publicos do Google, o ASan so encontra mais de 30% dos bugs de memoria em kod-projetos internos.

### 5.1.2 Sanitizers como Ferramenta de Defesa em Profundidade

Sanitizers nao substituem boas praticas de programacao — eles complementam. Em um modelo de defesa em profundidade:

```
Nivel 1: Prevencao (code review, boas praticas, RAII)
Nivel 2: Analise estatica (clang-tidy, cppcheck)
Nivel 3: Sanitizers (ASan, TSan, UBSan, MSan)  <-- Este capitulo
Nivel 4: Fuzzing (libFuzzer, AFL++)
Nivel 5: Analise dinamica (Valgrind, Dr. Memory)
Nivel 6: Hardening de binarios (PIE, RELRO, stack canaries)
```

Cada nivel captura o que escapou do anterior. Nenhum e suficiente sozinho. O erro mais comum e confiar apenas em code review — seres humanos sao ruins em encontrar bugs de memoria porque o padrao de C++ e complexo demais para rastrear mentalmente.

---

## 5.2 AddressSanitizer (ASan)

AddressSanitizer e o sanitizer mais utilizado e mais maduro. Ele detecta:

- **Buffer overflows** (stack e heap)
- **Use-after-free**
- **Use-after-return**
- **Use-after-scope**
- **Double-free**
- **Memory leaks** (quando combinado com LeakSanitizer)
- **Invalid free**

### 5.2.1 Como ASan Funciona Internamente

ASan usa duas tecnicas principais:

**Shadow Memory**: ASan mantem uma "shadow memory" que mapeia cada 8 bytes de memoria real para 1 byte de shadow. O byte de shadow indica se os 8 bytes estao alocados, livres, ou contaminados (redzones).

```
Memoria Real:   [8 bytes][8 bytes][8 bytes][8 bytes]
Shadow:         [  OK  ][ RED  ][ RED  ][  OK  ]
                 ^ alocado   ^ livre   ^ redzone  ^ alocado
```

O mapeamento e feito com a formula:

```
shadow_addr = (real_addr >> 3) + offset
```

Isso permite deteccao O(1) — verificar se um endereco e valido e apenas uma operacao de lookup na shadow memory.

**Redzones**: ASan injeta "redzones" (zonas vermelhas) ao redor de cada alocacao. Essas redzones contem valores magicos (0xf1, 0xf2, 0xf3, 0xf5) que sao verificados durante operacoes de free e durante acessos.

```
[Redzone 16B][User Data 64B][Redzone 16B]
     ^              ^              ^
  padding        malloc()      padding
```

Se um programa acessa uma redzone, ASan detecta imediatamente. Se um programa acessa alem da alocacao, ele entra na redzone adjacente e tambem e detectado.

### 5.2.2 Habilitando ASan no GCC e Clang

ASan e habilitado com a flag `-fsanitize=address`:

**GCC:**
```bash
gcc -fsanitize=address -fno-omit-frame-pointer -g -O1 program.c -o program
```

**Clang:**
```bash
clang -fsanitize=address -fno-omit-frame-pointer -g -O1 program.c -o program
```

A flag `-fno-omit-frame-pointer` e importante para que os stack traces sejam completos. Sem ela, ASan ainda funciona, mas os reports de erro mostram enderecos em vez de nomes de funcoes.

A flag `-g` adiciona informacoes de debug (nomes de variaveis, numeros de linha). Sem ela, os reports mostram apenas enderecos de memoria.

A flag `-O1` e necessaria porque ASan precisa de alguma otimizacao para funcionar corretamente. `-O0` causa problemas com o frame pointer e puede gerar falsos positivos em alguns cenarios.

### 5.2.3 Exemplo Completo com ASan

Considere o seguinte programa com um bug de buffer overflow:

```cpp
// vulnerable.c — contem bugs de memoria intencionais
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

// Bug 1: Stack buffer overflow
void stack_overflow() {
    char buffer[64];
    // Escreve 128 bytes em um buffer de 64
    memset(buffer, 'A', 128);
    printf("Stack overflow executado\n");
}

// Bug 2: Use-after-free
void use_after_free() {
    int *ptr = (int *)malloc(sizeof(int) * 10);
    if (!ptr) return;
    
    ptr[0] = 42;
    free(ptr);
    
    // Acessa memoria ja liberada
    printf("Valor apos free: %d\n", ptr[0]);
}

// Bug 3: Heap buffer overflow
void heap_overflow() {
    char *buffer = (char *)malloc(32);
    if (!buffer) return;
    
    // Escreve 64 bytes em um buffer de 32
    memset(buffer, 'B', 64);
    free(buffer);
}

// Bug 4: Double free
void double_free() {
    char *buffer = (char *)malloc(64);
    if (!buffer) return;
    
    free(buffer);
    free(buffer);  // Double free
}

// Bug 5: Memory leak
void memory_leak() {
    char *buffer = (char *)malloc(1024);
    if (!buffer) return;
    
    // Nunca chama free(buffer)
    printf("Alocacao sem free\n");
}

int main() {
    printf("Iniciando testes de sanitizers...\n");
    
    // Descomente um bug por vez para testar
    // stack_overflow();
    // use_after_free();
    // heap_overflow();
    // double_free();
    // memory_leak();
    
    return 0;
}
```

Compilando e executando com ASan:

```bash
# Compilar com ASan
gcc -fsanitize=address -fno-omit-frame-pointer -g -O1 \
    vulnerable.c -o vulnerable_asan

# Testar stack overflow
./vulnerable_asan 2>&1 | head -50
```

Saida esperada do ASan para stack overflow:

```
=================================================================
==12345==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x7fff12345678 at pc 0x555555555149 bp 0x7fff12345600 sp 0x7fff123455f8
WRITE of size 128 at 0x7fff12345678 thread T0
    #0 0x555555555148 in stack_overflow vulnerable.c:10
    #1 0x5555555551b2 in main vulnerable.c:42
    #2 0x7ffff7a03d8f in __libc_start_call_main libc-start.c:443

0x7fff12345678 is located 0 bytes to the right of 64-byte region [0x7fff12345638,0x7fff12345678)
allocated by thread T0 here:
    #0 0x555555555812 in __asan_allocavol stack_buffer_overflow:16
    #1 0x555555555134 in stack_overflow vulnerable.c:8

SUMMARY: AddressSanitizer: stack-buffer-overflow vulnerable.c:10:128
Shadow bytes around the buggy address:
  0x10007fff0a70: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0a80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0a90: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0aa0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0ab0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0ac0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0ad0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0ae0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0af0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x10007fff0b00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend:
  Addressable:           00
  Addressable partial:   01
  Heap left redzone:     fa
  Heap right redzone:    fb
  Freed heap region:     fd
  Stack left redzone:    f1
  Stack mid redzone:     f2
  Stack right redzone:   f3
  Stack partial redzone: f4
  Stack after return:    f5
  Stack use after scope: f8
  Global redzone:        f9
  Global init order:     f6
  Poisoned by user:      f7
  ASan internal:         fe
  Left alloca redzone:   ca
  Right alloca redzone:  cb
==12345==ABORTING
```

### 5.2.4 Variaveis de Ambiente do ASan

ASan oferece varias variaveis de ambiente para controle fino:

```bash
# Desabilitar prints detalhados
export ASAN_OPTIONS=verbosity=0

# Abortar no primeiro erro (padrao: sim)
export ASAN_OPTIONS=abort_on_error=1

# Detectar memory leaks (desabilitado por padrao)
export ASAN_OPTIONS=detect_leaks=1

# Definir numero maximo de leaks a reportar
export ASAN_OPTIONS=max_leaks=10

# Desabilitar leak detection para testes que esperam leaks
export ASAN_OPTIONS=detect_leaks=0

# Definir tamanho maximo de allocacao para shadow memory
export ASAN_OPTIONS=malloc_context_size=16

# Log de allocations (muito verboso, so para debug)
export ASAN_OPTIONS=log_path=asan_log.txt

# Suppressor de erros especificos
export ASAN_OPTIONS=suppressions=asan.suppressions
```

Tabela completa de opcoes do ASan:

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `abort_on_error` | Abortar no primeiro erro | 1 |
| `print_stacktrace` | Imprimir stack trace completo | 1 |
| `detect_leaks` | Habilitar LeakSanitizer | 1 (Linux) |
| `check_initialization_order` | Verificar ordem de inicializacao | 1 |
| `detect_stack_use_after_return` | Detectar uso apos return | 0 |
| `quarantine_size_kb` | Tamanho da quarantine em KB | 256 |
| `max_malloc_fill_size` | Tamanho max para fill apos malloc | -1 (sem limite) |
| `allocator_may_return_null` | Malloc pode retornar NULL | 0 |

### 5.2.5 Use-After-Free: O Bug Mais Perigoso

Use-after-free e frequentemente considerado o tipo de bug de memoria mais perigoso para seguranca. Um atacante pode:

1. Liberar um objeto
2. Alocar novo conteudo na mesma regiao de memoria
3. Acessar o objeto "liberado" que agora contem dados controlados pelo atacante

Exemplo de use-after-free que ASan detecta:

```cpp
#include <cstdlib>
#include <cstdio>
#include <cstring>

struct SensitiveData {
    char username[64];
    char password[64];
    int is_admin;
};

void process_user(SensitiveData *data) {
    // Processa dados do usuario
    printf("User: %s\n", data->username);
    printf("Admin: %d\n", data->is_admin);
}

int main() {
    SensitiveData *user_data = new SensitiveData();
    strcpy(user_data->username, "admin");
    strcpy(user_data->password, "supersecret123");
    user_data->is_admin = 1;
    
    // Libera a memoria
    delete user_data;
    
    // Aloca algo novo na mesma regiao
    char *attacker_buffer = new char[128];
    // O atacante pode ter preenchido esta memoria
    // com dados que se parecem com um SensitiveData
    
    // Bug: acessa user_data que ja foi liberado
    // ASan detecta isso imediatamente
    process_user(user_data);
    
    delete[] attacker_buffer;
    return 0;
}
```

### 5.2.6 ASan e Multi-Threading

ASan funciona com programas multi-threaded. Cada thread tem seu proprio stack frame monitorado, e o heap compartilhado e protegido por locks internos:

```cpp
#include <thread>
#include <vector>
#include <cstdlib>
#include <cstdio>

void worker(int id) {
    // Cada thread aloca e libera memoria
    char *buffer = (char *)malloc(256);
    sprintf(buffer, "Thread %d alocou buffer", id);
    printf("%s\n", buffer);
    free(buffer);
}

int main() {
    const int NUM_THREADS = 8;
    std::vector<std::thread> threads;
    
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back(worker, i);
    }
    
    for (auto &t : threads) {
        t.join();
    }
    
    printf("Todos os threads completaram\n");
    return 0;
}
```

Compilando com ASan e multi-threading:

```bash
# Asan com threads (GCC ou Clang)
g++ -fsanitize=address -fno-omit-frame-pointer -g -O1 \
    -pthread thread_test.cpp -o thread_test_asan

./thread_test_asan
```

ASan adiciona overhead significativo em multi-threading porque cada alocacao e monitorada individualmente. Para programas com muitas threads, considere usar TSan em vez de ASan para deteccao de data races, e ASan separadamente para erros de memoria.

### 5.2.7 ASan com C++ Standard Library

ASan e compativel com as implementacoes da STL. Ao usar `-fsanitize=address`, o compilador automaticamente instrumenta as chamadas de `new`, `delete`, `malloc`, `free`, e operacoes de array:

```cpp
#include <vector>
#include <string>
#include <iostream>

int main() {
    // ASan detecta overflow em vector
    std::vector<int> vec(10);
    vec[15] = 42;  // Heap buffer overflow detectado
    
    // ASan detecta string issues
    std::string str = "hello";
    str.resize(1000);  // Isso e valido (alloca nova memoria)
    
    // ASan detecta uso apos liberacao de vector
    std::vector<int> *pv = new std::vector<int>(100);
    delete pv;
    pv->push_back(1);  // Use-after-free detectado
    
    return 0;
}
```

---

## 5.3 ThreadSanitizer (TSan)

ThreadSanitizer e o detector de data races. Ele detecta acessos concorrentes nao sincronizados a memoria compartilhada — o que e uma das causas mais comuns de comportamento indefinido em programas multi-threaded.

### 5.3.1 Por Que Data Races Sao Perigosas

Um data race ocorre quando:

1. Dois ou mais threads acessam a mesma regiao de memoria
2. Pelo menos um dos acessos e uma escrita
3. Nao existe sincronizacao entre os acessos

Data races podem causar:

- **Corrupcao de dados**: valores inconsistentes lidos por threads
- **Crashes**: segfaults por pointers corrompidos
- **Vulnerabilidades de seguranca**: um data race pode ser explorado para bypass de checks
- **Comportamento indefinido**: o compilador pode reordenar operacoes

Exemplo real de data race em producao:

**CVE-2016-0728 (Linux Kernel Keyring)**: Um data race no subsystemo de keyring do Linux permitiu que um atacante localescalasse privilegios. O bug existia porque operacoes de refcount nao eram atomicas em todas as rotas de execucao. TSan teria detectado a falta de sincronizacao entre threads.

**CVE-2019-11135 (TSX Asynchronous Abort)**: Um data race relacionado a transacoes TSX no kernel Intel causou informacao vazada entre contexts. A deteccao requer analise de acesso concorrente a variaveis compartilhadas.

### 5.3.2 Habilitando TSan

TSan e habilitado com `-fsanitize=thread`:

```bash
# GCC
gcc -fsanitize=thread -g -O1 program.c -o program_tsan

# Clang
clang -fsanitize=thread -g -O1 program.c -o program_tsan
```

**IMPORTANTE**: TSan e incompativel com ASan. Voce NAO pode usar ambos ao mesmo tempo. Use um ou outro em cada execucao.

### 5.3.3 Exemplo de Data Race Detectado por TSan

```cpp
#include <thread>
#include <vector>
#include <cstdio>
#include <cstdlib>

// Compartilhado entre threads — SEM sincronizacao
int shared_counter = 0;

void increment_worker() {
    for (int i = 0; i < 100000; ++i) {
        shared_counter++;  // DATA RACE: incremento nao atomico
    }
}

int main() {
    const int NUM_THREADS = 4;
    std::vector<std::thread> threads;
    
    for (int i = 0; i < NUM_THREADS; ++i) {
        threads.emplace_back(increment_worker);
    }
    
    for (auto &t : threads) {
        t.join();
    }
    
    printf("Counter: %d (esperado: %d)\n", shared_counter, NUM_THREADS * 100000);
    return 0;
}
```

Compilando e executando com TSan:

```bash
g++ -fsanitize=thread -g -O1 data_race.cpp -o data_race_tsan
./data_race_tsan
```

Saida do TSan:

```
==================
WARNING: ThreadSanitizer: data race (pid=12345)
  Write of size 4 at 0x555555558024 by thread T1:
    #0 increment_worker() data_race.cpp:10
    #1 void std::thread::_Invoker<std::tuple<main::{lambda()#1}>>::operator()() /usr/include/c++/11/bits/std_thread.h:253

  Previous write of size 4 at 0x555555558024 by thread T2:
    #0 increment_worker() data_race.cpp:10
    #1 void std::thread::_Invoker<std::tuple<main::{lambda()#1}>>::operator()() /usr/include/c++/11/bits/std_thread.h:253

  Location is global 'shared_counter' of size 4 at 0x555555558024

SUMMARY: ThreadSanitizer: data race data_race.cpp:10:30 in increment_worker
==================
Counter: 287453 (esperado: 400000)
ThreadSanitizer: reported 1 warnings
```

O TSan detecta:
- Onde esta a primeira escrita (thread T1, linha 10)
- Onde esta a segunda escrita (thread T2, linha 10)
- A localizacao global da variavel compartilhada

### 5.3.4 Corrigindo o Data Race

A correcao e usar operacoes atomicas ou mutex:

```cpp
#include <thread>
#include <vector>
#include <atomic>
#include <mutex>
#include <cstdio>

// Solucao 1: atomic
std::atomic<int> atomic_counter{0};

void increment_atomic() {
    for (int i = 0; i < 100000; ++i) {
        atomic_counter.fetch_add(1, std::memory_order_relaxed);
    }
}

// Solucao 2: mutex
std::mutex mtx;
int mutex_counter = 0;

void increment_mutex() {
    for (int i = 0; i < 100000; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        mutex_counter++;
    }
}

int main() {
    // Testar atomic
    {
        std::vector<std::thread> threads;
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back(increment_atomic);
        }
        for (auto &t : threads) t.join();
        printf("Atomic counter: %d\n", atomic_counter.load());
    }
    
    // Testar mutex
    {
        std::vector<std::thread> threads;
        for (int i = 0; i < 4; ++i) {
            threads.emplace_back(increment_mutex);
        }
        for (auto &t : threads) t.join();
        printf("Mutex counter: %d\n", mutex_counter);
    }
    
    return 0;
}
```

### 5.3.5 TSan e Detectando Deadlocks

TSan tambem pode detectar deadlocks potenciais quando combinado com a opcao `detect_deadlocks=1` (padrao no Clang):

```cpp
#include <thread>
#include <mutex>
#include <cstdio>

std::mutex mutex_a;
std::mutex mutex_b;

void thread_1() {
    std::lock_guard<std::mutex> lock_a(mutex_a);
    // Simula trabalho
    for (volatile int i = 0; i < 1000000; ++i) {}
    std::lock_guard<std::mutex> lock_b(mutex_b);
    printf("Thread 1 completou\n");
}

void thread_2() {
    std::lock_guard<std::mutex> lock_b(mutex_b);
    // Simula trabalho
    for (volatile int i = 0; i < 1000000; ++i) {}
    std::lock_guard<std::mutex> lock_a(mutex_a);
    printf("Thread 2 completou\n");
}

int main() {
    std::thread t1(thread_1);
    std::thread t2(thread_2);
    
    t1.join();
    t2.join();
    
    return 0;
}
```

TSan detecta o potencial deadlock:

```
==================
WARNING: ThreadSanitizer: deadlock (pid=12345)
  Thread T1 (running) acquired mutex at 0x555555558060 and is trying to acquire mutex at 0x555555558070
  Thread T2 (running) acquired mutex at 0x555555558070 and is trying to acquire mutex at 0x555555558060

  Conflicting lock ordering:
    Thread T1: mutex at 0x555555558060 -> mutex at 0x555555558070
    Thread T2: mutex at 0x555555558070 -> mutex at 0x555555558060

  mutex at 0x555555558060 is a mutex at 0x555555558060
  mutex at 0x555555558070 is a mutex at 0x555555558070

SUMMARY: ThreadSanitizer: deadlock deadlock.cpp:8
==================
```

### 5.3.6 TSan e Supressoes

Em projetos grandes, pode ser necessario suprimir reports falsos positivos ou de terceiros:

```bash
# Criar arquivo de supressao
cat > tsan.suppressions << 'EOF'
# Suprimir data race em biblioteca de terceiros
race:third_party_lib/src/legacy_code.c

# Suprimir data race em variavel especifica
race:global_config_
race:some_global_variable

# Suprimir deadlock em biblioteca de terceiros
deadlock:third_party_lib/src/pool.c
EOF

# Usar supressao
TSAN_OPTIONS="suppressions=tsan.suppressions" ./meu_programa
```

Formato do arquivo de supressao:

```
# Comentario
race:padrao_para_funcao_ou_variavel
deadlock:padrao_para_modulo
```

O padrao e uma substring que e comparada contra o caminho completo no stack trace. Use `*` como curinga:

```
# Suprimir qualquer data race em src/third_party/
race:src/third_party/*

# Suprimir data race em uma funcao especifica
race:void third_party::SomeClass::init()
```

### 5.3.7 Variaveis de Ambiente do TSan

| Opcao | Descricao | Padrao |
|-------|-----------|--------|
| `history_size` | Profundidade do historico por goroutine | 7 |
| `second_deadlock_stack` | Mostrar segundo stack de deadlock | 1 |
| `report_bugs` | Habilitar reports de bugs | 1 |
| `halt_on_error` | Parar no primeiro erro | 0 |
| `suppressions` | Arquivo de supressoes | - |
| `print_suppressions` | Imprimir supressoes usadas | 1 |
| `detect_deadlocks` | Detectar deadlocks | 1 |
| `strip_path_prefix` | Prefixo para remover de paths | - |

```bash
# Usar TSan com opcoes customizadas
TSAN_OPTIONS="history_size=5 halt_on_error=1" ./programa_tsan

# Com supressoes e paths limpos
TSAN_OPTIONS="suppressions=tsan.suppressions strip_path_prefix=/home/user/project/" ./programa_tsan
```

---

## 5.4 UndefinedBehaviorSanitizer (UBSan)

UBSan detecta comportamento indefinido definido pelo padrao C/C++. Isso inclui operacoes que o compilador assume que nunca acontecem — e quando acontecem, o comportamento e imprevisivel.

### 5.4.1 Tipos de Comportamento Indefinido Detectados

UBSan detecta uma variedade impressionante de UB:

| Categoria | Exemplo |
|-----------|---------|
| Aritmetica | Divisao por zero, overflow de inteiro |
| Ponteiros | Dereferenciar pointer nulo, pointer desalinhado |
| Conversoes | Truncamento de tipo, enum invalido |
| Virutal | Chamada de virtual em objeto destruido |
| VLA | Variable-length array com tamanho invalido |
| Bool | Valor nao-bool em contexto bool |
| Signed integer | Overflow de signed integer (UB no C++) |
| Null | Dereferenciar pointer nulo |
| Object size | Alocacao com tamanho negativo ou excedente |

### 5.4.2 Habilitando UBSan

```bash
# GCC e Clang
gcc -fsanitize=undefined -g program.c -o program_ubsan
clang -fsanitize=undefined -g program.c -o program_ubsan

# Habilitar todas as categorias
gcc -fsanitize=undefined,float-divide-by-zero,float-cast-overflow \
    -g program.c -o program_ubsan
```

### 5.4.3 Exemplos de UB Detectado

```cpp
#include <cstdint>
#include <cstdio>

// Bug 1: Signed integer overflow
int signed_overflow() {
    int x = INT32_MAX;
    return x + 1;  // UB: signed integer overflow
}

// Bug 2: Division by zero
int division_by_zero(int x) {
    return 42 / x;  // UB: divisao por zero
}

// Bug 3: Null pointer dereference
void null_dereference() {
    int *ptr = nullptr;
    *ptr = 42;  // UB: dereferenciar pointer nulo
}

// Bug 4: Invalid shift
int invalid_shift() {
    int x = 1;
    return x << 32;  // UB: shift excede largura do tipo
}

// Bug 5: Misaligned pointer
void misaligned_access() {
    char buffer[16];
    // Forca acesso desalinhado
    int *misaligned = reinterpret_cast<int*>(buffer + 1);
    *misaligned = 42;  // UB: pointer desalinhado (em arquiteturas que exigem alinhamento)
}

// Bug 6: Out-of-bounds array access
void out_of_bounds() {
    int arr[10];
    arr[15] = 42;  // UB: acesso fora dos limites
}

// Bug 7: Invalid enum value
enum Color { RED = 0, GREEN = 1, BLUE = 2 };

void invalid_enum(int x) {
    Color c = static_cast<Color>(x);
    switch (c) {
        case RED: printf("Red\n"); break;
        case GREEN: printf("Green\n"); break;
        case BLUE: printf("Blue\n"); break;
        // UBSan detecta se x nao e 0, 1, ou 2
    }
}

int main() {
    printf("Testando UBSan...\n");
    
    // Descomente um bug por vez
    // signed_overflow();
    // division_by_zero(0);
    // null_dereference();
    // invalid_shift();
    // misaligned_access();
    // out_of_bounds();
    // invalid_enum(99);
    
    return 0;
}
```

### 5.4.4 Opcoes do UBSan

```bash
# Com traps (abort no primeiro UB)
gcc -fsanitize=undefined -fno-sanitize-recover=all -g program.c -o program

# Sem traps (reportar todos os UBs e continuar)
gcc -fsanitize=undefined -fsanitize-recover=all -g program.c -o program

# UBSan com trap para categorias especificas
gcc -fsanitize=signed-integer-overflow,null,alignment \
    -fno-sanitize-recover=signed-integer-overflow \
    -g program.c -o program
```

Variaveis de ambiente:

```bash
# UBSan com opcoes de ambiente
UBSAN_OPTIONS="print_stacktrace=1 halt_on_error=0" ./programa_ubsan

# Suprimir UBs especificos
UBSAN_OPTIONS="suppressions=ubsan.suppressions" ./programa_ubsan
```

### 5.4.5 UBSan e a Deteccao de Vulnerabilidades Reais

Muitas vulnerabilidades de seguranca tem comportamento indefinido como raiz:

**CVE-2014-0160 (Heartbleed)**: Embora seja um buffer over-read, o acesso alem do limite e comportamento indefinido em C. UBSan com `-fsanitize=bounds` teria detectado o acesso fora do buffer.

**CVE-2022-3676**: Signed integer overflow em um componente de rede. UBSan com `-fsanitize=signed-integer-overflow` detecta esses overflows que podem ser explorados.

```cpp
// Exemplo simplificado baseado em CVE real
#include <cstdint>
#include <cstring>
#include <cstdlib>

// Simulacao de um parser de rede vulneravel
struct PacketHeader {
    uint16_t type;
    uint16_t length;
    uint32_t sequence;
};

bool process_packet(const uint8_t *data, size_t data_len) {
    if (data_len < sizeof(PacketHeader)) {
        return false;
    }
    
    PacketHeader header;
    memcpy(&header, data, sizeof(header));
    
    // BUG: signed integer overflow
    // Se header.length for 0xFFFF e o offset for 1,
    // a soma causa overflow e pode bypass do check
    size_t payload_offset = sizeof(PacketHeader) + header.length;
    
    if (payload_offset > data_len) {
        return false;  // Check parece correto mas pode ser bypassado
    }
    
    // UBSan detecta o overflow em payload_offset
    const uint8_t *payload = data + payload_offset;
    
    // Processa payload
    printf("Payload offset: %zu\n", payload_offset);
    
    return true;
}

int main() {
    // Dados de exemplo
    uint8_t malicious_packet[] = {
        0x01, 0x00,  // type = 1
        0xFF, 0xFF,  // length = 65535 (causara overflow)
        0x00, 0x00, 0x00, 0x01,  // sequence = 1
        0x41, 0x42, 0x43, 0x44   // payload
    };
    
    process_packet(malicious_packet, sizeof(malicious_packet));
    
    return 0;
}
```

### 5.4.6 UBSan com C++ Moderno

UBSan e particularmente util com C++17/20, onde ha mais operacoes que podem causar UB:

```cpp
#include <variant>
#include <optional>
#include <memory>
#include <cstdio>

// UB com std::variant
void variant_ub() {
    std::variant<int, float, char*> v{42};
    
    // OK: acessa o tipo correto
    int val = std::get<int>(v);
    printf("Value: %d\n", val);
    
    // UB: acessa o tipo errado (em C++17, lanca std::bad_variant_access)
    // float wrong = std::get<float>(v);  // Exception, nao UB em C++17
}

// UB com unique_ptr
void unique_ptr_ub() {
    std::unique_ptr<int> ptr = std::make_unique<int>(42);
    
    // OK
    printf("Value: %d\n", *ptr);
    
    // Libera
    ptr.reset();
    
    // UBSan detecta acesso apos libera
    // int val = *ptr;  // Use-after-free
}

// UB com reinterpret_cast
void reinterpret_cast_ub() {
    double d = 3.14159;
    int *ip = reinterpret_cast<int*>(&d);
    
    // UBSan com strict aliasing detecta violacao de strict aliasing
    printf("First int: 0x%x\n", *ip);
}

int main() {
    variant_ub();
    unique_ptr_ub();
    reinterpret_cast_ub();
    return 0;
}
```

---

## 5.5 MemorySanitizer (MSan)

MemorySanitizer detecta leituras de memoria nao inicializada. E o menos utilizado dos sanitizers porque e o mais restritivo — requer que TODA a biblioteca do sistema tambem seja compilada com MSan.

### 5.5.1 Como MSan Funciona

MSan mantem uma shadow memory similar ao ASan, mas em vez de rastrear se a memoria e valida, ele rastreia se cada byte de memoria foi inicializado. Quando um programa le um valor de memoria que nao foi explicitamente inicializado, MSan gera um warning.

```
Memoria Real:   [4 bytes][4 bytes][4 bytes][4 bytes]
Shadow:         [ UNINIT ][ INIT  ][ UNINIT ][ INIT  ]
                ^ nao ini.  ^ ini.  ^ nao ini.  ^ ini.
```

### 5.5.2 Limitacao Principal

A limitacao critica do MSan e que ele requer que todas as bibliotecas do sistema (libc, libstdc++, etc.) tambem sejam compiladas com MSan. Isso e porque o MSan precisa rastrear o estado de inicializacao de TODA a memoria, incluindo a que vem de bibliotecas do sistema.

Na pratica, isso significa:
- Linux com Clang: possivel usando bibliotecas pre-compiladas do MSan
- GCC: nao suporta MSan
- Outros sistemas: dificil de configurar

### 5.5.3 Habilitando MSan

```bash
# Apenas Clang suporta MSan
clang -fsanitize=memory -fno-omit-frame-pointer -g -O1 \
    program.c -o program_msan

# Com track origins (mais lento mas mais util)
clang -fsanitize=memory -fsanitize-memory-track-origins=2 \
    -fno-omit-frame-pointer -g -O1 \
    program.c -o program_msan
```

### 5.5.4 Exemplo de MSan Detectando Variavel Nao Inicializada

```cpp
#include <cstdio>
#include <cstdlib>
#include <cstring>

int read_uninitialized() {
    int arr[10];
    // arr nao foi inicializado!
    // MSan detecta esta leitura
    return arr[5];
}

char *string_from_uninitialized() {
    char *str = (char *)malloc(100);
    // str aponta para memoria nao inicializada
    // MSan detecta quando usamos o conteudo
    return str;
}

struct Config {
    int timeout;
    bool enabled;
    char hostname[256];
};

void use_uninitialized_config() {
    Config config;
    // Config nao foi inicializado
    // MSan detecta estas leituras
    if (config.enabled) {
        printf("Timeout: %d\n", config.timeout);
        printf("Host: %s\n", config.hostname);
    }
}

int main() {
    // Descomente um por vez
    // int val = read_uninitialized();
    // printf("Value: %d\n", val);
    
    // char *str = string_from_uninitialized();
    // printf("String: %s\n", str);  // MSan: leitura de string nao terminada
    // free(str);
    
    // use_uninitialized_config();
    
    return 0;
}
```

### 5.5.5 MSan com Track Origins

A opcao `-fsanitize-memory-track-origins=2` faz o MSan rastrear a origem de cada valor nao inicializado, incluindo de onde a memoria foi alocada:

```bash
# Com track origins maximizado
clang -fsanitize=memory -fsanitize-memory-track-origins=2 \
    -fno-omit-frame-pointer -g -O1 \
    program.c -o program_msan
```

Saida do MSan com track origins:

```
==12345==WARNING: MemorySanitizer: use-of-uninitialized-value
    #0 0x555555555168 in read_uninitialized program.c:6
    #1 0x5555555551b2 in main program.c:28

  Uninitialized value was stored to memory at
    #0 0x555555555148 in read_uninitialized program.c:6

  Uninitialized value was created by a stack allocation
    #0 0x555555555134 in read_uninitialized program.c:4

SUMMARY: MemorySanitizer: use-of-uninitialized-value program.c:6:14
```

### 5.5.6 Quando Usar MSan

MSan e mais util em:
- **Sistemas embarcados**: onde memoria nao inicializada pode causar comportamento imprevisivel
- **Software critico**: medicos, automotivos, aeronauticos
- **Bibliotecas de rede**: onde buffers recebidos de rede podem conter lixo

Para a maioria dos projetos, ASan + UBSan cobrem a maioria dos casos de uso. MSan e um complemento para cenarios especificos onde a inicializacao de memoria e critica.

---

## 5.6 Configuracao no CMake

A integracao de sanitizers com CMake requer configuracao cuidadosa. O objetivo e criar opcoes que permitam habilitar sanitizers de forma seletiva, sem afetar builds normais.

### 5.6.1 Abordagem Basica com `option()` e `target_compile_options()`

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerExample
    VERSION 1.0.0
    LANGUAGES CXX
)

# Opcoes de sanitizers
option(ENABLE_ASAN "Habilitar AddressSanitizer" OFF)
option(ENABLE_TSAN "Habilitar ThreadSanitizer" OFF)
option(ENABLE_UBSAN "Habilitar UndefinedBehaviorSanitizer" OFF)
option(ENABLE_MSAN "Habilitar MemorySanitizer" OFF)

# Target principal
add_executable(myapp
    src/main.cpp
    src/utils.cpp
    src/parser.cpp
)

target_compile_features(myapp PRIVATE cxx_std_17)

# Configurar sanitizers
if(ENABLE_ASAN)
    message(STATUS "AddressSanitizer HABILITADO")
    target_compile_options(myapp PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(myapp PRIVATE -fsanitize=address)
endif()

if(ENABLE_TSAN)
    message(STATUS "ThreadSanitizer HABILITADO")
    target_compile_options(myapp PRIVATE -fsanitize=thread -fno-omit-frame-pointer)
    target_link_options(myapp PRIVATE -fsanitize=thread)
endif()

if(ENABLE_UBSAN)
    message(STATUS "UndefinedBehaviorSanitizer HABILITADO")
    target_compile_options(myapp PRIVATE -fsanitize=undefined -fno-omit-frame-pointer)
    target_link_options(myapp PRIVATE -fsanitize=undefined)
endif()

if(ENABLE_MSAN)
    message(STATUS "MemorySanitizer HABILITADO")
    target_compile_options(myapp PRIVATE -fsanitize=memory -fno-omit-frame-pointer)
    target_link_options(myapp PRIVATE -fsanitize=memory)
endif()
```

**Pontos criticos在这个 Abordagem:**

1. `target_compile_options` aplica flags apenas ao target especificado
2. `target_link_options` e necessario para propagar flags para o linker (ASan precisa de libs de runtime)
3. `-fno-omit-frame-pointer` e essencial para stack traces completos
4. As flags precisam estar em AMBOS compile e link options

### 5.6.2 Funcao Reutilizavel para Sanitizers

Para projetos com multiplos targets, e melhor criar uma funcao reutilizavel:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerExample VERSION 1.0.0 LANGUAGES CXX)

# Funcao para habilitar sanitizers em um target
function(enable_sanitizers target)
    set(_options "")
    set(_oneValueArgs "")
    set(_multiValueArgs SANITIZERS)
    
    cmake_parse_arguments(SAN "${_options}" "${_oneValueArgs}" 
        "${_multiValueArgs}" ${ARGN})
    
    # Validar sanitizers fornecidos
    set(_valid_sanitizers ASAN TSAN UBSAN MSAN)
    set(_cmake_sanitizers "")
    
    foreach(_san IN LISTS SAN_SANITIZERS)
        string(TOUPPER "${_san}" _san_upper)
        if(NOT _san_upper IN_LIST _valid_sanitizers)
            message(FATAL_ERROR 
                "Sanitizer invalido: ${_san}. Valores validos: ${_valid_sanitizers}")
        endif()
        
        if(_san_upper STREQUAL "ASAN")
            list(APPEND _cmake_sanitizers "address")
        elseif(_san_upper STREQUAL "TSAN")
            list(APPEND _cmake_sanitizers "thread")
        elseif(_san_upper STREQUAL "UBSAN")
            list(APPEND _cmake_sanitizers "undefined")
        elseif(_san_upper STREQUAL "MSAN")
            list(APPEND _cmake_sanitizers "memory")
        endif()
    endforeach()
    
    if(_cmake_sanitizers)
        message(STATUS "Sanitizers para ${target}: ${_cmake_sanitizers}")
        target_compile_options(${target} PRIVATE
            -fsanitize=${_cmake_sanitizers}
            -fno-omit-frame-pointer
        )
        target_link_options(${target} PRIVATE
            -fsanitize=${_cmake_sanitizers}
        )
    endif()
endfunction()

# Exemplo de uso
add_executable(app1 src/app1.cpp)
add_executable(app2 src/app2.cpp)

# app1 com ASan e UBSan
enable_sanitizers(app1 SANITIZERS ASAN UBSAN)

# app2 apenas com TSan
enable_sanitizers(app2 SANITIZERS TSAN)
```

### 5.6.3 Configuracao Avancada com Multi-Config Generators

Generators multi-config (Visual Studio, Xcode) precisam de abordagem diferente:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerExample VERSION 1.0.0 LANGUAGES CXX)

# Para generators multi-config, usar per-config properties
function(enable_sanitizers_multi_config target)
    set(_options "")
    set(_oneValueArgs "")
    set(_multiValueArgs SANITIZERS)
    
    cmake_parse_arguments(SAN "${_options}" "${_oneValueArgs}" 
        "${_multiValueArgs}" ${ARGN})
    
    set(_valid_sanitizers ASAN TSAN UBSAN MSAN)
    set(_asan_flags "")
    set(_tsan_flags "")
    set(_ubsan_flags "")
    set(_msan_flags "")
    
    foreach(_san IN LISTS SAN_SANITIZERS)
        string(TOUPPER "${_san}" _san_upper)
        if(_san_upper STREQUAL "ASAN")
            set(_asan_flags "-fsanitize=address;-fno-omit-frame-pointer")
        elseif(_san_upper STREQUAL "TSAN")
            set(_tsan_flags "-fsanitize=thread;-fno-omit-frame-pointer")
        elseif(_san_upper STREQUAL "UBSAN")
            set(_ubsan_flags "-fsanitize=undefined;-fno-omit-frame-pointer")
        elseif(_san_upper STREQUAL "MSAN")
            set(_msan_flags "-fsanitize=memory;-fno-omit-frame-pointer")
        endif()
    endforeach()
    
    # Debug: habilitar todos
    if(_asan_flags)
        set_property(TARGET ${target} PROPERTY 
            COMPILE_OPTIONS "${_asan_flags}")
        set_property(TARGET ${target} PROPERTY 
            LINK_OPTIONS "${_asan_flags}")
    endif()
    
    # Release: desabilitar sanitizers (ou manter UBSan apenas)
    set_property(TARGET ${target} APPEND PROPERTY
        COMPILE_OPTIONS "$<$<CONFIG:Release>:>")
endfunction()
```

### 5.6.4 Configuracao com CMake Presets

CMake 3.19+ suporta presets, que sao excelentes para configurar sanitizers:

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "debug-asan",
            "displayName": "Debug com ASan",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/debug-asan",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_ASAN": "ON",
                "CMAKE_CXX_FLAGS": "-fsanitize=address -fno-omit-frame-pointer"
            }
        },
        {
            "name": "debug-tsan",
            "displayName": "Debug com TSan",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/debug-tsan",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_TSAN": "ON",
                "CMAKE_CXX_FLAGS": "-fsanitize=thread -fno-omit-frame-pointer"
            }
        },
        {
            "name": "debug-ubsan",
            "displayName": "Debug com UBSan",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/debug-ubsan",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_UBSAN": "ON",
                "CMAKE_CXX_FLAGS": "-fsanitize=undefined -fno-omit-frame-pointer"
            }
        },
        {
            "name": "release",
            "displayName": "Release (sem sanitizers)",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/release",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "ENABLE_ASAN": "OFF",
                "ENABLE_TSAN": "OFF",
                "ENABLE_UBSAN": "OFF",
                "ENABLE_MSAN": "OFF"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "debug-asan",
            "configurePreset": "debug-asan"
        },
        {
            "name": "debug-tsan",
            "configurePreset": "debug-tsan"
        },
        {
            "name": "debug-ubsan",
            "configurePreset": "debug-ubsan"
        },
        {
            "name": "release",
            "configurePreset": "release"
        }
    ]
}
```

Uso:

```bash
# Configurar com ASan
cmake --preset debug-asan

# Buildar
cmake --build --preset debug-asan

# Executar testes com sanitizers
ctest --preset debug-asan
```

### 5.6.5 Configuracao com Compiler Checks

Antes de habilitar sanitizers, e util verificar se o compilador suporta:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerExample VERSION 1.0.0 LANGUAGES CXX C)

include(CheckCXXCompilerFlag)
include(CheckCXXSourceCompiles)

# Verificar suporte a ASan
check_cxx_compiler_flag("-fsanitize=address" HAS_ASAN)
check_cxx_source_compiles("
    int main() { return 0; }
" ASAN_COMPILE_TEST)

# Verificar suporte a TSan
check_cxx_compiler_flag("-fsanitize=thread" HAS_TSAN)

# Verificar suporte a UBSan
check_cxx_compiler_flag("-fsanitize=undefined" HAS_UBSAN)

# Verificar se ASan funciona (pode precisar de libasan)
set(CMAKE_REQUIRED_FLAGS "-fsanitize=address")
check_cxx_source_compiles("
    int main() { return 0; }
" ASAN_WORKS)
set(CMAKE_REQUIRED_FLAGS "")

if(ENABLE_ASAN AND HAS_ASAN AND ASAN_WORKS)
    message(STATUS "ASan: suportado e funcional")
    add_executable(app src/main.cpp)
    target_compile_options(app PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(app PRIVATE -fsanitize=address)
elseif(ENABLE_ASAN)
    message(WARNING "ASan solicitado mas nao disponivel")
endif()
```

### 5.6.6 Integracao com Target Properties

CMake permite configurar propriedades diretamente nos targets:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerProperties VERSION 1.0.0 LANGUAGES CXX)

# Criar interface library para sanitizers
add_library(sanitizer INTERFACE)

if(ENABLE_ASAN)
    target_compile_options(sanitizer INTERFACE 
        -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(sanitizer INTERFACE 
        -fsanitize=address)
    target_compile_definitions(sanitizer INTERFACE 
        SANITIZER_ASAN=1)
endif()

if(ENABLE_TSAN)
    target_compile_options(sanitizer INTERFACE 
        -fsanitize=thread -fno-omit-frame-pointer)
    target_link_options(sanitizer INTERFACE 
        -fsanitize=thread)
    target_compile_definitions(sanitizer INTERFACE 
        SANITIZER_TSAN=1)
endif()

# Targets que usam sanitizers
add_executable(server src/server.cpp)
target_link_libraries(server PRIVATE sanitizer)

add_executable(client src/client.cpp)
target_link_libraries(client PRIVATE sanitizer)

# Target que NAO usa sanitizers (ex: ferramenta de producao)
add_executable(deploy_tool src/deploy.cpp)
# Nao linka sanitizer
```

---

## 5.7 Regras de Exclusao Mutua entre Sanitizers

**REGRA CRITICA**: Certos sanitizers sao incompativeis entre si. Usar dois incompativeis causa erros de compilacao ou comportamento imprevisivel.

### 5.7.1 Matriz de Compatibilidade

| | ASan | TSan | UBSan | MSan | LSan |
|---|---|---|---|---|---|
| **ASan** | - | INCOMPATIVEL | COMPATIVEL | INCOMPATIVEL | COMPATIVEL |
| **TSan** | INCOMPATIVEL | - | COMPATIVEL | INCOMPATIVEL | INCOMPATIVEL |
| **UBSan** | COMPATIVEL | COMPATIVEL | - | COMPATIVEL | COMPATIVEL |
| **MSan** | INCOMPATIVEL | INCOMPATIVEL | COMPATIVEL | - | INCOMPATIVEL |
| **LSan** | COMPATIVEL | INCOMPATIVEL | COMPATIVEL | INCOMPATIVEL | - |

### 5.7.2 Combinacoes Validas

**ASan + UBSan** (recomendado para desenvolvimento):
```bash
gcc -fsanitize=address,undefined -g -O1 program.c -o program
```

**ASan + LSan** (padrao no ASan no Linux):
```bash
gcc -fsanitize=address -g -O1 program.c -o program
# LSan ja vem habilitado por padrao no ASan
```

**TSan + UBSan** (para testes de threading):
```bash
gcc -fsanitize=thread,undefined -g -O1 program.c -o program
```

**UBSan isolado** (para validacao rapida):
```bash
gcc -fsanitize=undefined -g program.c -o program
```

### 5.7.3 Por Que Sao Incompativeis

**ASan vs TSan**: Ambos modificam a memoria de formas incompativeis. ASan usa shadow memory para rastrear allocacoes, enquanto TSan usa shadow memory para rastrear acessos de threads. Os dois sistemas de shadow memory conflitam.

**ASan vs MSan**: Ambos usam shadow memory com esquemas de mapeamento diferentes. ASan mapeia 8:1, enquanto MSan mapeia 2:1 (porque precisa de mais informacao por byte). O conflito de shadow memory corrompe ambos os sistemas.

**TSan vs MSan**: Mesmo conflito de shadow memory — TSan e MSan usam a mesma regiao de memoria de forma incompativel.

### 5.7.4 Validacao no CMake

Para evitar que alguem acidentalmente combine sanitizers incompativeis:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerValidation VERSION 1.0.0 LANGUAGES CXX)

option(ENABLE_ASAN "AddressSanitizer" OFF)
option(ENABLE_TSAN "ThreadSanitizer" OFF)
option(ENABLE_UBSAN "UndefinedBehaviorSanitizer" OFF)
option(ENABLE_MSAN "MemorySanitizer" OFF)

# Validar exclusao mutua
set(_sanitizer_count 0)
if(ENABLE_ASAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
    set(_active_asan TRUE)
endif()
if(ENABLE_TSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
    set(_active_tsan TRUE)
endif()
if(ENABLE_UBSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
    set(_active_ubsan TRUE)
endif()
if(ENABLE_MSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
    set(_active_msan TRUE)
endif()

# Verificar incompatibilidades
if(_active_asan AND _active_tsan)
    message(FATAL_ERROR 
        "ASan e TSan sao INCOMPATIVEIS. "
        "Use um ou outro por execucao.")
endif()

if(_active_asan AND _active_msan)
    message(FATAL_ERROR 
        "ASan e MSan sao INCOMPATIVEIS. "
        "Use um ou outro por execucao.")
endif()

if(_active_tsan AND _active_msan)
    message(FATAL_ERROR 
        "TSan e MSan sao INCOMPATIVEIS. "
        "Use um ou outro por execucao.")
endif()

# Combinacoes validas
if(_active_asan AND _active_ubsan)
    message(STATUS "Combinacao ASan + UBSan (valida)")
endif()

if(_active_tsan AND _active_ubsan)
    message(STATUS "Combinacao TSan + UBSan (valida)")
endif()
```

---

## 5.8 ASan + UBSan Combinados

A combinacao ASan + UBSan e a mais recomendada para desenvolvimento. Ela cobre erros de memoria (ASan) E comportamento indefinido (UBSan) ao mesmo tempo.

### 5.8.1 Configuracao no CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(ASanUBSan VERSION 1.0.0 LANGUAGES CXX)

option(ENABLE_ASAN_UBSAN "Habilitar ASan + UBSan combinados" OFF)

add_executable(myapp src/main.cpp src/utils.cpp)

if(ENABLE_ASAN_UBSAN)
    message(STATUS "ASan + UBSan HABILITADOS")
    
    # Verificar incompatibilidade com TSan/MSan
    if(ENABLE_TSAN)
        message(FATAL_ERROR 
            "ASan e TSan sao incompativeis. "
            "Use ASan+UBSan ou TSan+UBSan.")
    endif()
    if(ENABLE_MSAN)
        message(FATAL_ERROR 
            "ASan e MSan sao incompativeis. "
            "Use ASan+UBSan ou MSan+UBSan.")
    endif()
    
    target_compile_options(myapp PRIVATE
        -fsanitize=address,undefined
        -fno-omit-frame-pointer
        -fno-sanitize-recover=undefined
    )
    target_link_options(myapp PRIVATE
        -fsanitize=address,undefined
    )
    
    # Definir macro para codigos que precisam saber se ASan esta ativo
    target_compile_definitions(myapp PRIVATE
        SANITIZER_ACTIVE=1
    )
endif()
```

### 5.8.2 Exemplo de Deteccao Combinada

```cpp
#include <cstdlib>
#include <cstring>
#include <cstdio>

// Este codigo contem TANTO um bug de memoria quanto UB
// ASan detecta o bug de memoria
// UBSan detecta o UB

struct Buffer {
    char data[256];
    size_t length;
};

Buffer* create_buffer(const char *input) {
    Buffer *buf = (Buffer *)malloc(sizeof(Buffer));
    if (!buf) return nullptr;
    
    buf->length = strlen(input);
    
    // BUG 1: Buffer overflow (detectado por ASan)
    memcpy(buf->data, input, buf->length + 100);
    
    return buf;
}

int process_buffer(Buffer *buf) {
    if (!buf) return -1;
    
    // BUG 2: Signed integer overflow (detectado por UBSan)
    int index = buf->length;
    index = index + 2000000000;  // Pode causar overflow
    
    // BUG 3: Use-after-free (detectado por ASan)
    free(buf);
    return buf->data[0];  // Acesso apos free
}

int main() {
    const char *test_input = "Hello, World!";
    
    Buffer *buf = create_buffer(test_input);
    if (buf) {
        int result = process_buffer(buf);
        printf("Result: %d\n", result);
    }
    
    return 0;
}
```

Compilando e executando:

```bash
# Compilar com ASan + UBSan
g++ -fsanitize=address,undefined -fno-omit-frame-pointer \
    -fno-sanitize-recover=undefined -g -O1 \
    combined.cpp -o combined_test

# Executar
./combined_test 2>&1
```

O ASan detectara o buffer overflow e o use-after-free, enquanto o UBSan detectara o signed integer overflow. Ambos os reports aparecerao na saida, permitindo que voce corrija TODOS os bugs em uma unica sessao de debug.

### 5.8.3 Tratamento de Erros Combinados

Quando ASan e UBSan estao ambos ativos, e importante configurar o comportamento de erro:

```bash
# Parar no primeiro erro de QUALQUER sanitizer
ASAN_OPTIONS="abort_on_error=1" \
UBSAN_OPTIONS="halt_on_error=1" \
./programa

# Continuar apos erros (reportar todos)
ASAN_OPTIONS="halt_on_error=0" \
UBSAN_OPTIONS="halt_on_error=0" \
./programa
```

Para testes automatizados, a configuracao recomendada e:

```bash
# Falhar no primeiro erro em CI/CD
ASAN_OPTIONS="abort_on_error=1 print_stacktrace=1" \
UBSAN_OPTIONS="halt_on_error=1 print_stacktrace=1" \
./programa
```

---

## 5.9 TSan Suppressions: tsan.suppressions

Em projetos grandes e realistas, nem todos os data races sao bugs. Alguns sao intencionais (variaveis atomicas mal usadas, patterns de double-check locking) ou vao de bibliotecas de terceiros. Suprimir esses reports falsos positivos e essencial para manter a utilidade do TSan.

### 5.9.1 Estrutura do Arquivo de Supressoes

O arquivo `tsan.suppressions` usa um formato simples:

```
# Comentario: descreve porque a supressao existe
race:padrao_de_busca

# Comentario: supressao para deadlock
deadlock:padrao_de_busca

# Comentario: supressao para use-after-free
deadlock:padrao_de_busca
```

O padrao de busca e comparado contra os caminhos completos no stack trace. Use `*` como curinga:

```
# Suprimir qualquer race em bibliotecas de terceiros
race:third_party/*

# Suprimir race em uma funcao especifica
race:void mylib::legacy_function()

# Suprimir race em uma variavel global
race:global_config_
race:global_state_

# Suprimir deadlock em um modulo
deadlock:src/network/*
```

### 5.9.2 Exemplo Completo de Supressoes

```cpp
// third_party_legacy.cpp — codigo de terceiros com data races conhecidos
#include <cstdio>
#include <thread>
#include <mutex>

// Variavel global em biblioteca legada — data race intencional
static int legacy_counter = 0;
static std::mutex legacy_mutex;

void legacy_increment() {
    // A biblioteca original nao usava mutex
    // Data race aqui — suprimir no tsan.suppressions
    legacy_counter++;
}

// Double-check locking pattern — possivel data race
static bool initialized = false;
static int *cached_value = nullptr;

int* get_cached_value() {
    if (!initialized) {  // Primeira leitura — pode ser race
        std::lock_guard<std::mutex> lock(legacy_mutex);
        if (!initialized) {
            cached_value = new int(42);
            initialized = true;
        }
    }
    return cached_value;
}
```

```
# tsan.suppressions
# Suprimir race em variavel global da biblioteca legada
# Motivo: a biblioteca original nao usava sincronizacao
race:legacy_counter

# Suprimir race no double-check locking pattern
# Motivo: padrao intencional com atomic que o TSan nao entende
race:initialized
race:cached_value
```

### 5.9.3 Gerenciando Supressoes em Projetos Grandes

Para projetos com muitos modulos e muitas supressoes:

```
tsan/
  suppressions/
    base.suppressions          # Supressoes base
    third_party.suppressions  # Bibliotecas de terceiros
    legacy.suppressions       # Codigo legado
    known_issues.suppressions # Issues conhecidos
```

No CMakeLists.txt:

```cmake
# Concatenar supressoes
file(GLOB TSAN_SUPPRESSIONS "tsan/suppressions/*.suppressions")
file(WRITE "${CMAKE_BINARY_DIR}/tsan.suppressions" "")

foreach(_supp IN LISTS TSAN_SUPPRESSIONS)
    file(READ "${_supp}" _content)
    file(APPEND "${CMAKE_BINARY_DIR}/tsan.suppressions" "${_content}\n")
endforeach()

# Opcao para usar supressoes
option(TSAN_USE_SUPPRESSIONS "Usar supressoes TSan" ON)
if(TSAN_USE_SUPPRESSIONS AND ENABLE_TSAN)
    set(ENV{TSAN_OPTIONS} "suppressions=${CMAKE_BINARY_DIR}/tsan.suppressions")
endif()
```

### 5.9.4 Gerando Supressoes Automaticamente

TSan pode gerar supressoes automaticamente quando encontra um data race:

```bash
# Executar com TSan e gerar supressoes
TSAN_OPTIONS="suppressions=tsan.suppressions print_suppressions=1" \
    ./programa_tsan 2>&1 | grep "^race:" > novas_supressoes.txt
```

Apos revisar e ajustar as supressoes geradas, adicione-as ao arquivo de supressoes.

### 5.9.5 Verificando Supressoes em CI/CD

Para garantir que supressoes nao estao sendo usadas para esconder bugs reais:

```yaml
# GitHub Actions: verificar supressoes
- name: Verificar supressoes TSan
  run: |
    # Executar com supressoes e contar reports
    TSAN_OPTIONS="suppressions=tsan.suppressions" \
        ./programa_tsan 2>&1 | tee tsan_output.txt
    
    # Contar reports nao suprimidos
    REPORTS=$(grep -c "WARNING: ThreadSanitizer" tsan_output.txt || true)
    
    if [ "$REPORTS" -gt 0 ]; then
        echo "ERRO: $REPORTS reports de TSan nao suprimidos"
        cat tsan_output.txt
        exit 1
    fi
```

---

## 5.10 Integracao com CI/CD

Integrar sanitizers em pipelines CI/CD e essencial para encontrar bugs antes de chegar em producao. O objetivo e falhar builds quando sanitizers detectam erros.

### 5.10.1 Pipeline Basico com Sanitizers

```yaml
# .github/workflows/sanitizers.yml
name: Sanitizers

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  asan:
    name: "AddressSanitizer"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          cmake -B build-asan \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_ASAN=ON \
            -DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer"
      
      - name: Buildar
        run: cmake --build build-asan --parallel
      
      - name: Executar testes com ASan
        run: |
          cd build-asan
          ctest --output-on-failure
      
      - name: Verificar memory leaks
        run: |
          cd build-asan
          ASAN_OPTIONS="detect_leaks=1 abort_on_error=1" \
            ctest --output-on-failure
  
  tsan:
    name: "ThreadSanitizer"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          cmake -B build-tsan \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_TSAN=ON \
            -DCMAKE_CXX_FLAGS="-fsanitize=thread -fno-omit-frame-pointer"
      
      - name: Buildar
        run: cmake --build build-tsan --parallel
      
      - name: Executar testes com TSan
        run: |
          cd build-tsan
          TSAN_OPTIONS="halt_on_error=1 print_stacktrace=1" \
            ctest --output-on-failure
  
  ubsan:
    name: "UndefinedBehaviorSanitizer"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          cmake -B build-ubsan \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_UBSAN=ON \
            -DCMAKE_CXX_FLAGS="-fsanitize=undefined -fno-omit-frame-pointer"
      
      - name: Buildar
        run: cmake --build build-ubsan --parallel
      
      - name: Executar testes com UBSan
        run: |
          cd build-ubsan
          UBSAN_OPTIONS="halt_on_error=1 print_stacktrace=1" \
            ctest --output-on-failure
```

### 5.10.2 Pipeline com Sanitizers Combinados

```yaml
  asan-ubsan:
    name: "ASan + UBSan"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          cmake -B build-sanitizers \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer -fno-sanitize-recover=undefined"
      
      - name: Buildar
        run: cmake --build build-sanitizers --parallel
      
      - name: Executar testes
        run: |
          cd build-sanitizers
          ASAN_OPTIONS="abort_on_error=1 print_stacktrace=1" \
          UBSAN_OPTIONS="halt_on_error=1 print_stacktrace=1" \
            ctest --output-on-failure
      
      - name: Upload relatorios de sanitizer
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: sanitizer-reports
          path: |
            build-sanitizers/Testing/
            build-sanitizers/CMakeFiles/
```

### 5.10.3 Pipeline com Supressoes

```yaml
  tsan-with-suppressions:
    name: "TSan com Supressoes"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          cmake -B build-tsan \
            -DCMAKE_BUILD_TYPE=Debug \
            -DENABLE_TSAN=ON
      
      - name: Buildar
        run: cmake --build build-tsan --parallel
      
      - name: Executar testes com supressoes
        run: |
          cd build-tsan
          
          # Verificar se supressoes existem
          if [ -f "${GITHUB_WORKSPACE}/tsan.suppressions" ]; then
            export TSAN_OPTIONS="suppressions=${GITHUB_WORKSPACE}/tsan.suppressions"
          fi
          
          TSAN_OPTIONS="${TSAN_OPTIONS} halt_on_error=1" \
            ctest --output-on-failure
      
      - name: Verificar reports nao suprimidos
        if: always()
        run: |
          cd build-tsan
          TSAN_OPTIONS="suppressions=${GITHUB_WORKSPACE}/tsan.suppressions" \
            ctest --output-on-failure 2>&1 | tee tsan_report.txt
          
          # Falhar se houver reports nao suprimidos
          if grep -q "ThreadSanitizer" tsan_report.txt; then
            if ! grep -q "suppressed" tsan_report.txt; then
              echo "ERRO: Reports de TSan nao suprimidos"
              exit 1
            fi
          fi
```

### 5.10.4 Execucao Sequencial (Importante)

Sanitizers com memória compartilhada (ASan e MSan) NAO podem executar em paralelo no mesmo host. Para pipelines que usam multiplos sanitizers:

```yaml
jobs:
  sanitizers:
    name: "Sanitizers"
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        sanitizer: [asan, tsan, ubsan]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar CMake
        run: |
          case "${{ matrix.sanitizer }}" in
            asan)
              cmake -B build \
                -DCMAKE_BUILD_TYPE=Debug \
                -DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer"
              ;;
            tsan)
              cmake -B build \
                -DCMAKE_BUILD_TYPE=Debug \
                -DCMAKE_CXX_FLAGS="-fsanitize=thread -fno-omit-frame-pointer"
              ;;
            ubsan)
              cmake -B build \
                -DCMAKE_BUILD_TYPE=Debug \
                -DCMAKE_CXX_FLAGS="-fsanitize=undefined -fno-omit-frame-pointer"
              ;;
          esac
      
      - name: Buildar
        run: cmake --build build --parallel
      
      - name: Executar testes
        run: |
          cd build
          case "${{ matrix.sanitizer }}" in
            asan)
              ASAN_OPTIONS="abort_on_error=1" ctest --output-on-failure
              ;;
            tsan)
              TSAN_OPTIONS="halt_on_error=1" ctest --output-on-failure
              ;;
            ubsan)
              UBSAN_OPTIONS="halt_on_error=1" ctest --output-on-failure
              ;;
          esac
```

### 5.10.5 Fail-Fast vs Fail-Continue

Decidir se a pipeline deve falhar no primeiro erro ou continuar:

**Fail-Fast (recomendado para CI/CD)**:
```yaml
- name: Executar testes
  run: |
    ASAN_OPTIONS="abort_on_error=1" ctest --output-on-failure
  # Se ASan encontrar erro, o processo aborta e a job falha
```

**Fail-Continue (para analise completa)**:
```yaml
- name: Executar testes
  continue-on-error: true
  run: |
    # Coletar TODOS os erros de sanitizer
    ASAN_OPTIONS="halt_on_error=0" ctest --output-on-failure 2>&1 | tee sanitizer_report.txt
    
    # Verificar se houve erros
    if grep -q "ERROR:" sanitizer_report.txt; then
      echo "Erros de sanitizer encontrados:"
      grep "ERROR:" sanitizer_report.txt
      exit 1
    fi
```

### 5.10.6 Relatorios e Notificacoes

```yaml
  sanitizer-report:
    name: "Relatorio de Sanitizers"
    runs-on: ubuntu-latest
    if: always()
    needs: [asan, tsan, ubsan]
    
    steps:
      - name: Gerar relatorio
        run: |
          echo "## Relatorio de Sanitizers" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Sanitizer | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|-----------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| ASan | ${{ needs.asan.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| TSan | ${{ needs.tsan.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| UBSan | ${{ needs.ubsan.result }} |" >> $GITHUB_STEP_SUMMARY
      
      - name: Notificar em caso de falha
        if: contains(needs.*.result, 'failure')
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'ERRO: Sanitizers detectaram problemas',
              body: 'Um ou mais sanitizers detectaram erros no codigo.',
              labels: ['bug', 'security']
            })
```

---

## 5.11 Impacto de Performance de Cada Sanitizer

Sanitizers adicionam overhead significativo. Entender o impacto de cada um e crucial para decisoes de build e para evitar surpresas em producao.

### 5.11.1 Tabela Comparativa de Performance

| Sanitizer | Overhead de Tempo | Overhead de Memoria | Trade-off |
|-----------|-------------------|---------------------|-----------|
| **ASan** | 2x-3x | 3x | Moderado — aceitavel para testes |
| **TSan** | 5x-15x | 5x-10x | Alto — so para testes de threading |
| **UBSan** | 1.1x-1.5x | 1.05x | Baixo — pode ser usado em producao |
| **MSan** | 3x-4x | 3x | Alto — requer libs recompiladas |
| **Valgrind** | 20x-50x | 5x-10x | Muito alto — so para analise offline |

### 5.11.2 ASan: Impacto Detalhado

ASan adiciona overhead por:

1. **Instrumentacao de cada alocacao/free**: Cada malloc/free e interceptado e instrumentado
2. **Verificacao de redzones**: Cada acesso a memoria verifica a shadow memory
3. **Shadow memory**: Cada 8 bytes de memoria real usa 1 byte de shadow
4. **Quarantine**: Memoria liberada fica em quarantine antes de ser reusada

```cpp
// Benchmark simples para medir overhead do ASan
#include <chrono>
#include <cstdlib>
#include <cstdio>
#include <vector>

void benchmark_alloc_free(size_t iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    for (size_t i = 0; i < iterations; ++i) {
        void *p = malloc(64);
        free(p);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start).count();
    
    printf("malloc/free %zu iteracoes: %ld ms\n", iterations, duration);
}

void benchmark_array_alloc(size_t iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<void*> ptrs;
    ptrs.reserve(iterations);
    
    for (size_t i = 0; i < iterations; ++i) {
        ptrs.push_back(malloc(1024));
    }
    
    for (void *p : ptrs) {
        free(p);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start).count();
    
    printf("alloc/free em lote %zu iteracoes: %ld ms\n", iterations, duration);
}

int main() {
    benchmark_alloc_free(1000000);
    benchmark_array_alloc(1000000);
    return 0;
}
```

Resultados tipicos:

```
# Sem sanitizers
malloc/free 1000000 iteracoes: 45 ms
alloc/free em lote 1000000 iteracoes: 38 ms

# Com ASan
malloc/free 1000000 iteracoes: 120 ms  (~2.7x mais lento)
alloc/free em lote 1000000 iteracoes: 95 ms  (~2.5x mais lento)
```

### 5.11.3 TSan: Impacto Detalhado

TSan e o sanitizer mais lento porque precisa:

1. **Rastrear cada acesso de memoria**: Cada leitura e escrita e instrumentada
2. **Manter historico por thread**: Cada thread mantem um historico de acessos
3. **Verificar conflitos**: Cada acesso verifica contra acessos anteriores de outras threads

O overhead do TSan e MUITO maior em programas com muitas threads:

```cpp
#include <thread>
#include <vector>
#include <mutex>
#include <atomic>
#include <chrono>
#include <cstdio>

std::mutex mtx;
std::atomic<int> atomic_counter{0};
int mutex_counter = 0;
int raw_counter = 0;

void worker_atomic(int iterations) {
    for (int i = 0; i < iterations; ++i) {
        atomic_counter.fetch_add(1, std::memory_order_relaxed);
    }
}

void worker_mutex(int iterations) {
    for (int i = 0; i < iterations; ++i) {
        std::lock_guard<std::mutex> lock(mtx);
        mutex_counter++;
    }
}

void worker_raw(int iterations) {
    for (int i = 0; i < iterations; ++i) {
        raw_counter++;  // Data race intencional
    }
}

void benchmark(const char *name, int num_threads, int iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    std::vector<std::thread> threads;
    for (int i = 0; i < num_threads; ++i) {
        if (name[0] == 'a') {
            threads.emplace_back(worker_atomic, iterations);
        } else if (name[0] == 'm') {
            threads.emplace_back(worker_mutex, iterations);
        } else {
            threads.emplace_back(worker_raw, iterations);
        }
    }
    
    for (auto &t : threads) t.join();
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start).count();
    
    printf("%s (%d threads, %d iter/thread): %ld ms\n", 
           name, num_threads, iterations, duration);
}

int main() {
    benchmark("atomic", 8, 1000000);
    benchmark("mutex", 8, 1000000);
    benchmark("raw", 8, 1000000);
    return 0;
}
```

### 5.11.4 UBSan: Impacto Detalhado

UBSan e o sanitizer mais leve porque so verifica operacoes especificas, nao cada acesso a memoria:

```cpp
#include <chrono>
#include <cstdio>
#include <cstdint>

int benchmark_integer_ops(size_t iterations) {
    auto start = std::chrono::high_resolution_clock::now();
    
    int64_t result = 0;
    for (size_t i = 0; i < iterations; ++i) {
        result += i;
        result ^= (i << 3);
        result = result % 1000;
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(
        end - start).count();
    
    printf("Integer ops %zu iteracoes: %ld ms\n", iterations, duration);
    return result;
}

int main() {
    benchmark_integer_ops(100000000);
    return 0;
}
```

Resultado tipico:

```
# Sem sanitizers
Integer ops 100000000 iteracoes: 85 ms

# Com UBSan
Integer ops 100000000 iteracoes: 102 ms  (~1.2x mais lento)
```

O overhead de 20% e aceitavel para muitos cenarios, inclusive testes automatizados em CI/CD.

### 5.11.5 Quando NAO Usar Sanitizers

Sanitizers NAO devem ser usados em:

1. **Producao**: O overhead e muito alto para servidores em producao
2. **Benchmarking de performance**: Sanitizers distorcem metricas de tempo
3. **Testes de carga**: Sanitizers alteram o comportamento de threads
4. **Deploy final**: Sanitizers adicionam informacoes de debug ao binario

**Excecao**: UBSan pode ser usado em producao quando o custo de comportamento indefinido e muito alto (sistema medico, controlador de voo). Nesse caso, o overhead de 20% e aceitavel em troca de seguranca.

---

## 5.12 Debug Builds: -g, -O0, Address Sanitizer Friendly

A configuracao correta de builds de debug e essencial para que sanitizers funcionem corretamente.

### 5.12.1 Flags de Debug no CMake

```cmake
cmake_minimum_required(VERSION 3.20)

project(DebugBuilds VERSION 1.0.0 LANGUAGES CXX)

option(ENABLE_ASAN "AddressSanitizer" OFF)

# Configurar tipo de build padrao
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug" CACHE STRING "Tipo de build" FORCE)
endif()

# Flags por tipo de build
set(CMAKE_CXX_FLAGS_DEBUG "-g -O0 -Wall -Wextra -Wpedantic")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-g -O2 -DNDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG")

add_executable(myapp src/main.cpp)

# ASan funciona melhor com -O1 (nao -O0)
# Mas -O0 e melhor para debugging interativo
if(ENABLE_ASAN)
    # ASan requer -O1 minimo
    target_compile_options(myapp PRIVATE -fsanitize=address -O1 -g)
    target_link_options(myapp PRIVATE -fsanitize=address)
else()
    # Debug puro sem sanitizer
    target_compile_options(myapp PRIVATE -g -O0)
endif()
```

### 5.12.2 Por Que ASan Precisa de -O1

ASan funciona com `-O0`, mas ha problemas conhecidos:

1. **Frame pointer omitido**: `-O0` pode omitir frame pointers em algumas arquiteturas, causando stack traces incompletos
2. **Inlining de funcoes**: `-O0` nao inlinia funcoes, o que pode mascarar alguns bugs
3. **Otimizacoes de registrador**: `-O0` nao usa registradores eficientemente, o que pode causar falsos positivos em alguns cenarios

A recomendacao e usar `-O1` com ASan:

```bash
# ASan com -O1 (recomendado)
gcc -fsanitize=address -fno-omit-frame-pointer -O1 -g program.c

# ASan com -O0 (funcional mas menos preciso)
gcc -fsanitize=address -fno-omit-frame-pointer -O0 -g program.c
```

### 5.12.3 Configuracao de Debug Amigavel a Sanitizers

```cmake
cmake_minimum_required(VERSION 3.20)

project(DebugFriendly VERSION 1.0.0 LANGUAGES CXX)

option(ENABLE_ASAN "AddressSanitizer" OFF)
option(ENABLE_TSAN "ThreadSanitizer" OFF)
option(ENABLE_UBSAN "UndefinedBehaviorSanitizer" OFF)

# Detectar se estamos em modo debug
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    set(IS_DEBUG TRUE)
else()
    set(IS_DEBUG FALSE)
endif()

add_executable(myapp src/main.cpp)

# Configurar flags baseadas no build type e sanitizers
if(IS_DEBUG)
    if(ENABLE_ASAN OR ENABLE_TSAN OR ENABLE_UBSAN)
        # Com sanitizers: usar -O1 (minimo para ASan)
        target_compile_options(myapp PRIVATE -g -O1 -Wall -Wextra)
        
        if(ENABLE_ASAN)
            target_compile_options(myapp PRIVATE -fsanitize=address -fno-omit-frame-pointer)
            target_link_options(myapp PRIVATE -fsanitize=address)
        endif()
        
        if(ENABLE_TSAN)
            target_compile_options(myapp PRIVATE -fsanitize=thread -fno-omit-frame-pointer)
            target_link_options(myapp PRIVATE -fsanitize=thread)
        endif()
        
        if(ENABLE_UBSAN)
            target_compile_options(myapp PRIVATE -fsanitize=undefined -fno-omit-frame-pointer)
            target_link_options(myapp PRIVATE -fsanitize=undefined)
        endif()
    else()
        # Debug puro: -O0 para debugging interativo
        target_compile_options(myapp PRIVATE -g -O0 -Wall -Wextra)
    endif()
endif()
```

### 5.12.4 Debug Info com Sanitizers

Para stacks traces completos, e importante ter informacoes de debug (DWARF):

```cmake
# Garantir que debug info e gerado
target_compile_options(myapp PRIVATE -g -gdwarf-4)

# Para builds maiores, usar -g1 (informacoes minimas)
# Para debug completo, usar -g3 (includes macros)
```

Comparacao de niveis de debug info:

| Flag | Tamanho | Informacao |
|------|---------|------------|
| `-g0` | Nenhum | Sem debug info |
| `-g1` | Pequeno | Labels, linhas |
| `-g2` | Medio | Padrao — tipos, funcoes, linhas |
| `-g3` | Grande | Inclui macros, tipos internos |
| `-gdwarf-4` | Medio | DWARF 4 (compativel com ASan) |
| `-gdwarf-5` | Medio | DWARF 5 (mais compacto) |

---

## 5.13 Valgrind vs Sanitizers: Quando Usar Cada

Valgrind e Sanitizers sao ferramentas complementares, nao substitutas. Cada uma tem vantagens em cenarios diferentes.

### 5.13.1 Tabela Comparativa

| Aspecto | Sanitizers (ASan/TSan/etc.) | Valgrind |
|---------|---------------------------|----------|
| **Velocidade** | 2x-3x mais lento | 20x-50x mais lento |
| **Precisao** | Alta (deteccao em tempo real) | Muito alta (analise completa) |
| **Setup** | Requer recompilacao | Sem recompilacao |
| **Binario** | Binario instrumentado | Binario original |
| **Memoria** | Shadow memory + overhead | Virtualizacao de instrucoes |
| **Multi-threading** | Suportado nativamente | Limitado (Helgrind/DRD) |
| **Leak detection** | Integrado no ASan | Suprimido (Memcheck) |
| **Plataformas** | Linux, macOS, Windows (limitado) | Linux, macOS |
| **Producao** | Nao (overhead alto) | Nao (overhead muito alto) |
| **CI/CD** | Sim (overhead aceitavel) | Nao (muito lento) |

### 5.13.2 Quando Usar ASan

**Use ASan quando:**
- Desenvolvimento ativo (feedback rapido)
- Testes automatizados em CI/CD
- Deteccao de buffer overflows e use-after-free
- Precisa de stack traces detalhados
- Programa multi-threaded (funciona bem com threads)

**Exemplo de uso ASan:**

```bash
# Desenvolvimento: executar testes com ASan
cmake -B build-asan -DCMAKE_CXX_FLAGS="-fsanitize=address -fno-omit-frame-pointer"
cmake --build build-asan
cd build-asan && ctest --output-on-failure
```

### 5.13.3 Quando Usar Valgrind

**Use Valgrind quando:**
- Analise offline de binarios ja compilados
- Quando NAO pode recompilar o codigo
- Deteccao precisa de memory leaks (Memcheck)
- Analise de cachegrind para otimizacao de performance
- Quando precisa de informacoes que sanitizers nao dao

**Exemplo de uso Valgrind:**

```bash
# Analise de memoria com Valgrind
valgrind --leak-check=full \
         --show-leak-kinds=all \
         --track-origins=yes \
         --verbose \
         ./programa

# Analise de cachegrind
valgrind --tool=cachegrind ./programa

# Analise de callgrind (profiling)
valgrind --tool=callgrind ./programa
```

### 5.13.4 Helgrind/DRD: Alternativa do Valgrind a TSan

Helgrind e DRD sao ferramentas do Valgrind para deteccao de data races:

```bash
# Helgrind: deteccao de data races e deadlocks
valgrind --tool=helgrind ./programa

# DRD: deteccao de data races (mais preciso que Helgrind para alguns casos)
valgrind --tool=drd ./programa
```

Comparacao TSan vs Helgrind/DRD:

| Aspecto | TSan | Helgrind/DRD |
|---------|------|--------------|
| **Velocidade** | 5x-15x | 50x-100x |
| **Precisao** | Alta | Muito alta |
| **Setup** | Recompilacao | Sem recompilacao |
| **Deteccao** | Data races, deadlocks | Data races, deadlocks |
| **Multi-threading** | Nativo | Virtualizacao |

### 5.13.5 Estrategia Recomendada: Usar Ambos

A melhor estrategia e usar sanitizers durante desenvolvimento e testes, e Valgrind para analise profunda antes de releases:

```
Desenvolvimento:
  - ASan + UBSan (feedback rapido, 2-3x mais lento)
  - TSan para testes de threading
  
CI/CD:
  - ASan + UBSan em cada PR
  - TSan em testes de threading
  
Pre-release:
  - Valgrind Memcheck para memory leaks
  - Valgrind Helgrind para data races
  - Valgrind Cachegrind para performance
```

---

## 5.14 Exemplo: CMakeLists.txt Completo com Opcoes de Sanitizer

Este CMakeLists.txt e um exemplo completo que demonstra todas as configuracoes discutidas neste capitulo:

```cmake
cmake_minimum_required(VERSION 3.20)

project(SanitizerDemo
    VERSION 1.0.0
    DESCRIPTION "Projeto com Sanitizers configurados"
    LANGUAGES CXX C
)

include(CheckCXXCompilerFlag)
include(CheckCXXSourceCompiles)

# ============================================================================
# Opcoes de Sanitizers
# ============================================================================

option(ENABLE_ASAN "Habilitar AddressSanitizer" OFF)
option(ENABLE_TSAN "Habilitar ThreadSanitizer" OFF)
option(ENABLE_UBSAN "Habilitar UndefinedBehaviorSanitizer" OFF)
option(ENABLE_MSAN "Habilitar MemorySanitizer" OFF)
option(SANITIZER_FAIL_ON_ERROR "Falhar no primeiro erro de sanitizer" ON)

# ============================================================================
# Verificacao de compatibilidade
# ============================================================================

# Contar sanitizers ativos
set(_sanitizer_count 0)
if(ENABLE_ASAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
endif()
if(ENABLE_TSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
endif()
if(ENABLE_UBSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
endif()
if(ENABLE_MSAN)
    math(EXPR _sanitizer_count "${_sanitizer_count} + 1")
endif()

# Verificar incompatibilidades
if(ENABLE_ASAN AND ENABLE_TSAN)
    message(FATAL_ERROR
        "ERRO: ASan e TSan sao INCOMPATIVEIS.\n"
        "Use um ou outro por execucao.\n"
        "Solucoes:\n"
        "  cmake -DENABLE_ASAN=ON -DENABLE_TSAN=OFF\n"
        "  cmake -DENABLE_ASAN=OFF -DENABLE_TSAN=ON")
endif()

if(ENABLE_ASAN AND ENABLE_MSAN)
    message(FATAL_ERROR
        "ERRO: ASan e MSan sao INCOMPATIVEIS.\n"
        "Use um ou outro por execucao.")
endif()

if(ENABLE_TSAN AND ENABLE_MSAN)
    message(FATAL_ERROR
        "ERRO: TSan e MSan sao INCOMPATIVEIS.\n"
        "Use um ou outro por execucao.")
endif()

# Verificar combinacoes validas
if(ENABLE_ASAN AND ENABLE_UBSAN)
    message(STATUS "Combinacao ASan + UBSan (valida e recomendada)")
endif()

if(ENABLE_TSAN AND ENABLE_UBSAN)
    message(STATUS "Combinacao TSan + UBSan (valida)")
endif()

if(_sanitizer_count EQUAL 0)
    message(STATUS "Nenhum sanitizer habilitado")
elseif(_sanitizer_count EQUAL 1)
    if(ENABLE_ASAN)
        message(STATUS "AddressSanitizer HABILITADO")
    elseif(ENABLE_TSAN)
        message(STATUS "ThreadSanitizer HABILITADO")
    elseif(ENABLE_UBSAN)
        message(STATUS "UndefinedBehaviorSanitizer HABILITADO")
    elseif(ENABLE_MSAN)
        message(STATUS "MemorySanitizer HABILITADO")
    endif()
endif()

# ============================================================================
# Verificar suporte do compilador
# ============================================================================

check_cxx_compiler_flag("-fsanitize=address" HAS_ASAN_FLAG)
check_cxx_compiler_flag("-fsanitize=thread" HAS_TSAN_FLAG)
check_cxx_compiler_flag("-fsanitize=undefined" HAS_UBSAN_FLAG)

if(ENABLE_ASAN AND NOT HAS_ASAN_FLAG)
    message(FATAL_ERROR "Compilador nao suporta -fsanitize=address")
endif()

if(ENABLE_TSAN AND NOT HAS_TSAN_FLAG)
    message(FATAL_ERROR "Compilador nao suporta -fsanitize=thread")
endif()

if(ENABLE_UBSAN AND NOT HAS_UBSAN_FLAG)
    message(FATAL_ERROR "Compilador nao suporta -fsanitize=undefined")
endif()

# ============================================================================
# Target: Library
# ============================================================================

add_library(mylib STATIC
    src/mylib/core.cpp
    src/mylib/parser.cpp
    src/mylib/network.cpp
)

target_include_directories(mylib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(mylib PUBLIC cxx_std_17)

# ============================================================================
# Target: Executavel principal
# ============================================================================

add_executable(myapp
    src/main.cpp
    src/config.cpp
    src/logger.cpp
)

target_link_libraries(myapp PRIVATE mylib)

# ============================================================================
# Aplicar sanitizers
# ============================================================================

# Funcao para aplicar sanitizers em um target
function(apply_sanitizers target)
    set(_sanitizer_flags "")
    
    if(ENABLE_ASAN)
        list(APPEND _sanitizer_flags -fsanitize=address)
    endif()
    
    if(ENABLE_TSAN)
        list(APPEND _sanitizer_flags -fsanitize=thread)
    endif()
    
    if(ENABLE_UBSAN)
        list(APPEND _sanitizer_flags -fsanitize=undefined)
    endif()
    
    if(ENABLE_MSAN)
        list(APPEND _sanitizer_flags -fsanitize=memory)
    endif()
    
    if(_sanitizer_flags)
        # Adicionar -fno-omit-frame-pointer para stack traces completos
        list(APPEND _sanitizer_flags -fno-omit-frame-pointer)
        
        # Aplicar flags
        target_compile_options(${target} PRIVATE ${_sanitizer_flags})
        target_link_options(${target} PRIVATE ${_sanitizer_flags})
        
        # Definir macro para codigo que precisa saber se sanitizer esta ativo
        target_compile_definitions(${target} PRIVATE
            SANITIZER_ENABLED=1
        )
        
        # Configurar variaveis de ambiente para executaveis
        if(SANITIZER_FAIL_ON_ERROR)
            if(ENABLE_ASAN)
                set_property(TARGET ${target} PROPERTY
                    ENVIRONMENT "ASAN_OPTIONS=abort_on_error=1;print_stacktrace=1")
            endif()
            if(ENABLE_TSAN)
                set_property(TARGET ${target} PROPERTY
                    ENVIRONMENT "TSAN_OPTIONS=halt_on_error=1;print_stacktrace=1")
            endif()
            if(ENABLE_UBSAN)
                set_property(TARGET ${target} PROPERTY
                    ENVIRONMENT "UBSAN_OPTIONS=halt_on_error=1;print_stacktrace=1")
            endif()
        endif()
    endif()
endfunction()

# Aplicar sanitizers a todos os targets
apply_sanitizers(mylib)
apply_sanitizers(myapp)

# ============================================================================
# Testes
# ============================================================================

enable_testing()

add_executable(test_core tests/test_core.cpp)
target_link_libraries(test_core PRIVATE mylib)
apply_sanitizers(test_core)
add_test(NAME test_core COMMAND test_core)

add_executable(test_parser tests/test_parser.cpp)
target_link_libraries(test_parser PRIVATE mylib)
apply_sanitizers(test_parser)
add_test(NAME test_parser COMMAND test_parser)

add_executable(test_network tests/test_network.cpp)
target_link_libraries(test_network PRIVATE mylib)
apply_sanitizers(test_network)
add_test(NAME test_network COMMAND test_network)

# Configurar CTest para falhar em erros de sanitizer
if(SANITIZER_FAIL_ON_ERROR)
    set_tests_properties(test_core test_parser test_network PROPERTIES
        ENVIRONMENT_MODIFICATION
        "ASAN_OPTIONS=abort_on_error=1,print_stacktrace=1;"
        "TSAN_OPTIONS=halt_on_error=1,print_stacktrace=1;"
        "UBSAN_OPTIONS=halt_on_error=1,print_stacktrace=1"
    )
endif()

# ============================================================================
# Supressoes
# ============================================================================

if(ENABLE_TSAN)
    set(TSAN_SUPPRESSIONS_FILE "${CMAKE_CURRENT_SOURCE_DIR}/tsan.suppressions")
    if(EXISTS ${TSAN_SUPPRESSIONS_FILE})
        message(STATUS "Supressoes TSan: ${TSAN_SUPPRESSIONS_FILE}")
    else()
        message(WARNING "Arquivo de supressoes TSan nao encontrado: ${TSAN_SUPPRESSIONS_FILE}")
    endif()
endif()

# ============================================================================
# Relatorio de configuracao
# ============================================================================

message(STATUS "")
message(STATUS "=== Configuracao de Sanitizers ===")
message(STATUS "  ASan:    ${ENABLE_ASAN}")
message(STATUS "  TSan:    ${ENABLE_TSAN}")
message(STATUS "  UBSan:   ${ENABLE_UBSAN}")
message(STATUS "  MSan:    ${ENABLE_MSAN}")
message(STATUS "  Fail:    ${SANITIZER_FAIL_ON_ERROR}")
message(STATUS "==================================")
message(STATUS "")
```

---

## 5.15 Exercicios

### Exercicio 1: Configuracao Basica de ASan

**Objetivo**: Configurar ASan em um projeto CMake existente.

**Instrucoes**:
1. Crie um novo projeto CMake com um executavel simples
2. Adicione a opcao `ENABLE_ASAN` ao CMakeLists.txt
3. Implemente uma funcao com um buffer overflow intencional
4. Compile e execute com ASan habilitado
5. Documente o output completo do ASan

**Solucao esperada**:
```cmake
option(ENABLE_ASAN "Habilitar AddressSanitizer" OFF)

add_executable(exercicio1 src/exercicio1.cpp)

if(ENABLE_ASAN)
    target_compile_options(exercicio1 PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(exercicio1 PRIVATE -fsanitize=address)
endif()
```

**Verificacao**: O ASan deve detectar o buffer overflow e mostrar o stack trace completo.

---

### Exercicio 2: Deteccao de Use-After-Free

**Objetivo**: Criar um programa que demonstra use-after-free e como ASan detecta.

**Instrucoes**:
1. Crie um programa com `malloc` e `free` seguido de acesso ao pointer
2. Compile com e sem ASan
3. Compare as saidas
4. Corrija o bug e verifique que nao ha mais reports

**Requisitos**:
- Usar `malloc` e `free` (nao `new`/`delete`)
- Acessar o pointer apos o `free`
- Mostrar a diferenca entre saida com e sem ASan

---

### Exercicio 3: TSan em Programa Multi-Threaded

**Objetivo**: Criar um programa com data race e detectar com TSan.

**Instrucoes**:
1. Crie um programa com 4 threads incrementando uma variavel compartilhada
2. Implemente SEM sincronizacao (data race intencional)
3. Compile com TSan e documente o report
4. Corrija usando `std::atomic` e verifique que nao ha mais reports
5. Corrija usando `std::mutex` e compare o overhead

**Requisitos**:
- Usar `std::thread` e `std::vector`
- Medir tempo com e sem sincronizacao
- Documentar a diferenca de performance

---

### Exercicio 4: UBSan em Codigo com Comportamento Indefinido

**Objetivo**: Identificar e corrigir varios tipos de UB.

**Instrucoes**:
1. Crie um programa com pelo menos 3 tipos diferentes de UB:
   - Signed integer overflow
   - Division by zero
   - Null pointer dereference
2. Compile com UBSan e documente cada report
3. Corrija cada bug e verifique que nao ha mais reports

**Requisitos**:
- Cada bug deve ser em uma funcao separada
- Documentar o tipo de UB detectado para cada funcao
- Usar `-fno-sanitize-recover=all` para parar no primeiro erro

---

### Exercicio 5: Configuracao de Supressoes TSan

**Objetivo**: Criar e gerenciar supressoes para TSan.

**Instrucoes**:
1. Crie um modulo de biblioteca de terceiros (simulado) com data races conhecidos
2. Crie um arquivo `tsan.suppressions` com as supressoes apropriadas
3. Execute com e sem supressoes
4. Documente a diferenca entre os outputs
5. Crie um script que verifica se supressoes nao estao escondendo bugs reais

**Requisitos**:
- Pelo menos 3 supressoes diferentes
- Cada supressao deve ter um comentario explicando porque
- Script de verificacao deve falhar se houver reports nao suprimidos

---

### Exercicio 6: Pipeline CI/CD com Sanitizers

**Objetivo**: Configurar uma pipeline GitHub Actions com multiplos sanitizers.

**Instrucoes**:
1. Crie um arquivo `.github/workflows/sanitizers.yml`
2. Implemente jobs para ASan, TSan e UBSan
3. Adicione job de relatorio que consolida resultados
4. Configure para falhar a PR se qualquer sanitizer detectar erro

**Requisitos**:
- Usar matrix strategy para sanitizers
- Incluir upload de artifacts em caso de falha
- Gerar relatorio Markdown no GitHub Step Summary

---

### Exercicio 7: Benchmark de Overhead de Sanitizers

**Objetivo**: Medir e comparar o overhead de cada sanitizer.

**Instrucoes**:
1. Crie um programa com operacoes computacionais intensivas
2. Meça o tempo com cada sanitizer separadamente
3. Meça o tempo com ASan + UBSan combinados
4. Meça o tempo sem sanitizers
5. Gere uma tabela comparativa

**Requisitos**:
- Pelo menos 10 operacoes diferentes (alocacao, thread, arithmetic, etc.)
- Media de 10 execucoes por configuracao
- Incluir overhead de memoria (se possivel)

---

### Exercicio 8: Valgrind vs ASan

**Objetivo**: Comparar Valgrind e ASan na deteccao de memory leaks.

**Instrucoes**:
1. Crie um programa com 5 memory leaks diferentes
2. Execute com Valgrind Memcheck
3. Execute com ASan (detect_leaks=1)
4. Compare: qual encontra mais? Qual e mais rapido?
5. Documente as diferencas nos reports

**Requisitos**:
- Usar `valgrind --leak-check=full`
- Usar `ASAN_OPTIONS=detect_leaks=1`
- Medir tempo de cada ferramenta

---

## 5.16 Referencias

### Documentacao Oficial

1. **Google AddressSanitizer**: https://github.com/google/sanitizers/wiki/AddressSanitizer
2. **Google ThreadSanitizer**: https://github.com/google/sanitizers/wiki/ThreadSanitizerCppManual
3. **Google UndefinedBehaviorSanitizer**: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
4. **Google MemorySanitizer**: https://github.com/google/sanitizers/wiki/MemorySanitizer
5. **CMake Sanitizers Documentation**: https://cmake.org/cmake/help/latest/prop_tgt/COMPILE_OPTIONS.html

### Papers e Artigos Academicos

6. Serebryany, K., Bruening, D., Potapenko, A., & Vyukov, D. (2012). "AddressSanitizer: A Fast Address Sanity Checker." USENIX ATC.
7. Serebryany, K., & Mitrokhin, D. (2015). "Implementing a Data Race Detector for C/C++ with Sanitizers." CppCon.
8. Vyukov, D. (2014). "Kernel Concurrency Sanitizer (KCSAN)." USENIX ATC.

### Documentacao do Clang/GCC

9. **Clang Sanitizers Documentation**: https://clang.llvm.org/docs/index.html
10. **GCC Sanitizer Options**: https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html
11. **GCC Address Sanitizer**: https://gcc.gnu.org/gcc-4.8/changes.html

### Casos Reais e CVEs

12. **Heartbleed (CVE-2014-0160)**: https://heartbleed.com/
13. **Cloudbleed (CVE-2017-5882)**: https://blog.cloudflare.com/incident-report-on-memory-leak-causing-misformation-of-some-ssl-certificates/
14. **CVE-2016-0728**: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2016-0728
15. **CVE-2021-22555**: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-22555

### Ferramentas Relacionadas

16. **Valgrind**: https://valgrind.org/
17. **Dr. Memory**: https://drmemory.org/
18. **Helgrind**: https://valgrind.org/docs/manual/hg-manual.html
19. **DRD**: https://valgrind.org/docs/manual/drd-manual.html
20. **libFuzzer**: https://llvm.org/docs/LibFuzzer.html

### Livros

21. **"Secure Coding in C and C++"** - Robert C. Seacord, 2nd Edition
22. **"The Art of Software Security Assessment"** - Mark Dowd, John McDonald, Justin Schuh
23. **"Writing Secure Code"** - Michael Howard, David LeBlanc, 2nd Edition
24. **"C++ Software Design"** - Klaus Iglberger (padroes que evitam UB)

---

## Resumo

Este capitulo cobriu os principais sanitizers disponiveis para projetos C/C++ com CMake:

- **ASan**: O sanitizer mais util para erros de memoria. Detecta buffer overflows, use-after-free, double-free, e memory leaks. Overhead de 2x-3x.

- **TSan**: Essencial para programas multi-threaded. Detecta data races e deadlocks. Overhead de 5x-15x.

- **UBSan**: O mais leve e preciso para comportamento indefinido. Detecta divisao por zero, overflow de inteiro, null pointer dereference. Overhead de 1.1x-1.5x.

- **MSan**: Especializado em memoria nao inicializada. Requer libs do sistema recompiladas. Menos utilizado.

- **Combinacoes**: ASan+UBSan e a recomendacao para desenvolvimento. TSan+UBSan para projetos com threading.

- **CMake**: Use `option()` para configurar sanitizers e `target_compile_options()` + `target_link_options()` para aplicar.

- **CI/CD**: Execute sanitizers em cada PR para encontrar bugs antes de producao.

- **Valgrind**: Complementar para analise offline quando nao pode recompilar.

A regra de ouro: **sempre tenha pelo menos um sanitizer habilitado durante desenvolvimento e testes**. O custo de encontrar um bug em producao e 100x maior que o custo de executar sanitizers em desenvolvimento.
---

*[Capítulo anterior: 04 — Flags Seguranca Compilador](04-flags-seguranca-compilador.md)*
*[Próximo capítulo: 06 — Hardening Binarios](06-hardening-binarios.md)*
