---
layout: default
title: "06-hardening-binarios"
---

# Capitulo 06 — Hardening de Binarios

> *"Compilar nao e suficiente. O binario precisa ser uma fortaleza antes de encontrar o primeiro adversario."*

---

## Sumario

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Fundamento: Por Que Hardening de Binarios Importa](#2-fundamento-por-que-hardening-de-binarios-importa)
3. [RELRO: Partial vs Full RELRO](#3-relro-partial-vs-full-relro)
4. [Stack Canaries: Como Funcionam](#4-stack-canaries-como-funcionam)
5. [ASLR/PIE: Randomizacao de Endereco](#5-aslrpie-randomizacao-de-endereco)
6. [Strip de Simbolos: -s, --strip-all](#6-strip-de-simbolos--s---strip-all)
7. [Debug Info: -g vs Strip](#7-debug-info--g-vs-strip)
8. [Reproducible Builds: Determinismo](#8-reproducible-builds-determinismo)
9. [Binary Diffing: Verificacao de Integridade](#9-binary-diffing-verificacao-de-integridade)
10. [Code Signing: Sign e Verify](#10-code-signing-sign-e-verify)
11. [CMake Properties: INSTALL_RPATH, SKIP_BUILD_RPATH](#11-cmake-properties-install_rpath-skip_build_rpath)
12. [CMake Install: DESTDIR, CMAKE_INSTALL_PREFIX](#12-cmake-install-destdir-cmake_install_prefix)
13. [Security Headers no Binario: stack_chk_fail](#13-security-headers-no-binario-stack_chk_fail)
14. [Exemplo: Target Hardening Completo](#14-exemplo-target-hardening-completo)
15. [Exercicios](#15-exercicios)
16. [Referencias](#16-referencias)

---

## 1. Objetivos de Aprendizado

Apos este capitulo, voce sera capaz de:

- Explicar a diferenca entre Partial RELRO e Full RELRO e por que Full RELRO e preferivel para binaries de producao
- Implementar stack canaries e entender como eles detectam buffer overflows em tempo de execucao
- Configurar ASLR/PIE para randomizacao de endereco e dificultar exploits baseados em ret2libc
- Decidir quando usar strip de simbolos e como preservar informacoes de debug
- Implementar builds reproduziveis com CMake para garantir determinismo binario
- Usar binary diffing para verificar integridade de artefatos de build
- Assinar binarios e verificar assinaturas como parte do pipeline de seguranca
- Configurar propriedades CMake de install (DESTDIR, RPATH) de forma segura
- Criar um target CMake com hardening completo e todas as protecoes integradas
- Verificar a presenca de protecoes em binarios existentes usando ferramentas de analise

---

## 2. Fundamento: Por Que Hardening de Binarios Importa

### O Que Acontece Sem Hardening

Quando voce compila um binario basico com `gcc -o app main.c`, o resultado e um executavel que:

- Possui tabelas de simbolos completas, permitindo engenharia reversa facilitada
- Usa enderecos fixos, facilitando ret2libc e ROP chains
- Nao possui verificacao de integridade da stack, permitindo buffer overflows silenciosos
- Tem a GOT (Global Offset Table) vulneravel a sobreescrita
- Pode ser executado em qualquer endereco sem aleatorizacao
- Carrega informacoes de debug que revelam estrutura interna
- Permite execucao de codigo arbitrario na stack e no heap

Um atacante que encontra uma vulnerabilidade de memoria nesse binario tem o trabalho consideravelmente facilitado. O hardening de binarios adiciona multiplas camadas de defesa que tornam cada etapa do ataque mais dificil, mais custosa ou ate mesmo impossivel.

### Modelando o Problema

Considere o seguinte modelo de ataque:

```
Vulnerabilidade (buffer overflow, use-after-free, etc.)
  -> Controle do fluxo de execucao
    -> Leak de endereco base (para bypassar ASLR)
      -> Construcao de ROP chain
        -> Execucao de shellcode ou chamadas de sistema
          -> Escalacao de privilegios ou exfiltracao de dados
```

Cada tecnica de hardening ataca um ou mais pontos nessa cadeia:

| Tecnica | Ponto de Ataque Interceptado | Custo de Bypass |
|---------|------------------------------|-----------------|
| Stack Canaries | Controle de fluxo via stack smash | Leak + brute force do canary |
| ASLR/PIE | Leak de endereco base | Ate 2^bits de randomizacao |
| Full RELRO | Sobreescrita da GOT | Impossivel (GOT e read-only) |
| NX/DEP | Execucao de shellcode na stack | ROP chain necessaria |
| FORTIFY_SOURCE | Overflows em funcoes de string | Bypass complexo |
| Strip de simbolos | Engenharia reversa facilitada | Analise manual obrigatoria |

### Estatisticas e Impacto

De acordo com estudos da MITRE, vulnerabilidades de memoria representam aproximadamente 70% das vulnerabilidades de seguranca em software C/C++. O hardening de binarios e uma das defesas mais eficazes contra essa categoria.

```
# Exemplo real: CVE-2021-4034 (PwnKit)
# Vulnerabilidade no polkit que permite escalacao de privilegios
# Causa: buffer overflow no parsing de argumentos
# Se stack canary estivesse ativo: overflow detectado e programa abortado
# Se ASLR/PIE estivesse ativo: enderecos nao seriam previsiveis
# Se Full RELRO estivesse ativo: GOT não poderia ser sobrescrita
```

### Custo vs Beneficio

| Protecao | Custo de Implementacao | Custo de Performance | Beneficio |
|----------|----------------------|---------------------|-----------|
| Stack Canaries | Baixo (flag do compilador) | < 1% | Alto |
| ASLR/PIE | Baixo (flag do compilador) | Negligivel | Alto |
| Full RELRO | Baixo (flag do linker) | 50-200ms na inicializacao | Muito Alto |
| NX/DEP | Baixo (flag do linker) | Zero | Muito Alto |
| FORTIFY_SOURCE | Baixo (define) | < 1% | Medio |
| Strip | Baixo (comando pos-build) | Zero | Medio |
| Reproducible Builds | Medio (configuracao) | Zero | Alto |

---

## 3. RELRO: Partial vs Full RELRO

### O Que e a GOT

A Global Offset Table (GOT) e uma estrutura de dados usada pelo linker dinamico para resolver simbolos de bibliotecas compartilhadas em tempo de execucao. Quando voce chama uma funcao de libc como `printf`, o primeiro acesso vai para a PLT (Procedure Linkage Table), que por sua vez consulta a GOT para encontrar o endereco real da funcao.

Esse mecanismo e essencial para o funcionamento de bibliotecas compartilhadas, mas cria uma superficie de ataque: se um atacante conseguiu um buffer overflow, ele pode sobrescrever uma entrada da GOT e redirecionar o fluxo de execucao para qualquer endereco.

### Fluxo de Resolucao de Simbolos

```
Chamada: printf("hello")

1. Instrucao: call printf@PLT
   -> Salta para a PLT

2. PLT (Procedure Linkage Table):
   -> Verifica se o endereco ja foi resolvido
   -> Se nao: chama o linker dinamico para resolver
   -> Se sim: usa o endereco na GOT

3. GOT (Global Offset Table):
   -> Armazena o endereco real de printf
   -> Primeira chamada: endereco do stub do linker
   -> Chamadas subsequentes: endereco real de printf

4. Resolucao lazy:
   -> Primeira chamada: linker resolve e atualiza GOT
   -> Demais chamadas: usa endereco ja resolvido
```

### O Ataque de Sobreescrita da GOT

```
Estado antes do ataque:
+------------------+
| GOT entry 0x00   | -> endereco de malloc
+------------------+
| GOT entry 0x08   | -> endereco de printf  <-- Atacante quer sobrescrever
+------------------+
| GOT entry 0x10   | -> endereco de free
+------------------+

Apos buffer overflow bem-sucedido:
+------------------+
| GOT entry 0x00   | -> endereco de malloc
+------------------+
| GOT entry 0x08   | -> endereco de system()  <-- Sobrescrito!
+------------------+
| GOT entry 0x10   | -> endereco de free
+------------------+

Quando printf e chamada:
-> PLT consulta GOT
-> GOT retorna endereco de system()
-> system() e executado com argumento do atacante
```

### Partial RELRO

O Partial RELRO (Relocation Read-Only) e o padrao na maioria dos compiladores. Ele:

- Marca as secoes `.init_array`, `.fini_array`, `.dynamic` e `.got` como somente leitura apos o relocate
- Deixa a `.got.plt` (usada por funcoes lazy-bound) como leitura-escrita
- Resolve apenas as relocacoes necessarias para o startup

```
# Verificando o nivel RELRO de um binario
readelf -l /usr/bin/example | grep GNU_RELRO
readelf -d /usr/bin/example | grep BIND_NOW

# Com Partial RELRO:
# GNU_RELRO segment presente
# BIND_NOW NAO presente
# .got.plt permanece escritavel

# Com Full RELRO:
# GNU_RELRO segment presente
# BIND_NOW presente
# Toda a GOT e protegida
```

### Full RELRO

O Full RELRO resolve todas as relocacoes no momento da carga e marca toda a GOT como somente leitura. Isso elimina completamente o ataque de sobreescrita da GOT.

A diferenca e resolvida com a flag `-Wl,-z,relro,-z,now`:

```
# Full RELRO: resolve todas as relocacoes imediatamente
gcc -o app main.c -Wl,-z,relro,-z,now

# Partial RELRO: apenas relocacoes iniciais sao protegidas
gcc -o app main.c -Wl,-z,relro

# Sem RELRO: nenhuma protecao
gcc -o app main.c

# Flags equivalentes no linker
ld -z relro -z now -o app main.o

# No CMake
target_link_options(myapp PRIVATE -Wl,-z,relro,-z,now)
```

### Impacto no Tempo de Inicializacao

Full RELRO tem um custo: todas as bibliotecas compartilhadas sao resolvidas no momento da carga, aumentando o tempo de inicializacao. Para a maioria dos servicos, esse custo e negligivel. Para aplicacoes com centenas de bibliotecas compartilhadas, o impacto pode ser percebido.

```
# Benchmarking do tempo de inicializacao
time ./app-with-partial-relro --version
time ./app-with-full-relro --version

# Exemplo de resultado:
# real    0m0.012s (Partial RELRO)
# real    0m0.015s (Full RELRO)
# Diferenca: ~3ms (desprezivel para servicos)

# Para servicos com muitas dependencias:
# real    0m0.045s (Partial RELRO)
# real    0m0.089s (Full RELRO)
# Diferenca: ~44ms (aceitavel para a maioria dos casos)
```

### Verificando RELRO em Binarios Existentes

```
# Usando checksec (disponivel em pacotes de seguranca)
checksec --file=/usr/bin/example

# Output esperado para Full RELRO:
#   RELRO:           Full RELRO
#   Stack:           Canary found
#   NX:              NX enabled
#   PIE:             PIE enabled
#   FORTIFY:         Fortified

# Verificacao manual com readelf
readelf -d /usr/bin/example | grep -E '(BIND_NOW|FLAGS)'
# BIND_NOW indica Full RELRO

# Verificacao com objdump
objdump -x /usr/bin/example | grep -A1 'GNU_RELRO'

# Script completo de verificacao
#!/bin/bash
BINARY=$1
echo "=== Analise de RELRO para $BINARY ==="
if readelf -l "$BINARY" | grep -q GNU_RELRO; then
    echo "GNU_RELRO: Presente"
    if readelf -d "$BINARY" | grep -q BIND_NOW; then
        echo "BIND_NOW: Presente"
        echo "Nivel: Full RELRO"
    else
        echo "BIND_NOW: Ausente"
        echo "Nivel: Partial RELRO"
    fi
else
    echo "GNU_RELRO: Ausente"
    echo "Nivel: Sem RELRO"
fi
```

### Decisao: Full vs Partial RELRO

| Criterio | Partial RELRO | Full RELRO |
|----------|---------------|------------|
| Protecao da GOT | Parcial | Completa |
| Tempo de inicializacao | Mais rapido | Mais lento |
| Compatibilidade | Universal | Quase universal |
| Uso recomendado | Embedded, tempo critico | Servicos, desktop, producao |

**Recomendacao**: Para a maioria dos projetos, Full RELRO e a escolha correta. O custo de inicializacao e quase sempre desprezivel comparado ao beneficio de seguranca.

---

## 4. Stack Canaries: Como Funcionam

### O Problema

Buffer overflows classicos funcionam sobrescrevendo o endereco de retorno na stack. Quando a funcao retorna, o processador pula para o endereco controlado pelo atacante. Stack canaries sao valores secretos colocados entre as variaveis locais e o endereco de retorno na stack.

### Mecanismo de Funcionamento

```
Stack layout antes do overflow:
+-------------------+
| Variavel local    |  <- Buffer do usuario
| (buffer[64])      |
+-------------------+
| Canary (valor     |  <- Valor secreto gerado no inicio
| secreto)          |     da execucao do processo
+-------------------+
| Frame pointer     |  <- EBP/RBP
+-------------------+
| Endereco de       |  <- Destino do 'ret'
| retorno           |
+-------------------+

Stack layout apos buffer overflow:
+-------------------+
| Variavel local    |  <- Buffer do usuario (overflow)
| (buffer[64])      |     dados do atacante vao ate aqui
+-------------------+
| Canary (ALTERADO) |  <- Sobrescrito pelo atacante
+-------------------+
| Frame pointer     |  <- Sobrescrito pelo atacante
+-------------------+
| Endereco de       |  <- Controlado pelo atacante
| retorno           |
+-------------------+
```

Antes de retornar, o compilador insere codigo que verifica se o canary foi alterado. Se sim, o programa e terminado imediatamente, evitando que o fluxo de execucao seja corrompido.

### Codigo Inserido pelo Compilador

```
# O compilador gera codigo equivalente a:
void funcao_com_canary() {
    // Prologo: salvar canary na stack
    __canary_local = __stack_chk_guard;

    // Corpo da funcao
    // ... codigo do usuario ...

    // Epilogo: verificar canary
    if (__canary_local != __stack_chk_guard) {
        __stack_chk_fail();  // Abortar o processo
    }

    // Retorno
    return;
}
```

### Flags de Compilacao

```
# Protecao basica: -fstack-protector
# Ativa canary para funcoes com buffers grandes
gcc -o app main.c -fstack-protector

# Protecao para funcoes com buffers grandes (>= 8 bytes)
# Mais eficiente: apenas funcoes com risco real
gcc -o app main.c -fstack-protector-strong

# Protecao para todas as funcoes (maximo custo)
# Ativa canary em TODAS as funcoes, mesmo sem buffers
gcc -o app main.c -fstack-protector-all

# Desabilitar protecao (PERIGOSO - apenas para debug)
gcc -o app main.c -fno-stack-protector

# Verificar se canary esta ativo
gcc -Q --help=stack-protector 2>/dev/null | grep stack-protector
```

### Comportamento em Funcoes Especificas

O `-fstack-protector-strong` ativa o canary quando:

- A funcao contem um array de char de qualquer tamanho
- A funcao contem um array de qualquer tipo com tamanho >= 8 bytes
- A funcao contem uma variavel enderecada (usando `&`)
- A funcao contem um array de caractere com tamanho desconhecido em tempo de compilacao

```
// Exemplo 1: Protegido com -fstack-protector-strong
// Array de char detectado -> canary ativado
void vulnerable_function() {
    char buffer[64];
    strcpy(buffer, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
    // Compiler insere verificacao de canary
}

// Exemplo 2: Protegido por causa do endereco
// Variavel enderecada detectada -> canary ativado
void another_vulnerable() {
    int arr[10];
    int *ptr = arr;   // Endereco tomado
    ptr[0] = 100;     // Overflow possivel via ptr
}

// Exemplo 3: Protegido por array grande
// Array >= 8 bytes detectado -> canary ativado
void large_array_function() {
    int arr[3];   // 12 bytes >= 8
    arr[0] = 1;
    arr[1] = 2;
    arr[2] = 3;
}

// Exemplo 4: Nao protegido com -fstack-protector-strong
// Sem arrays, sem enderecos tomados -> sem canary
void safe_function() {
    int x = 42;
    int y = x + 1;
    int z = x * y;
}
```

### stack Stack Clash

Stack clash e uma variacao de ataque onde o atacante usa uma sequencia de allocacoes grandes na stack para "pular" por cima do canary e de outros guard pages.

```
# Protecao contra stack clash
gcc -o app main.c -fstack-clash-protection

# Como funciona:
# - Compilador insere codigos que verificam a cada frame se a stack
#   esta dentro dos limites esperados
# - Impede que o atacante pule por cima de guard pages
# - Funciona mesmo com otimizacoes
```

### O Papel de __stack_chk_fail

Quando o canary e detectado como alterado, o compilador chama `__stack_chk_fail()`. Essa funcao:

1. Escreve uma mensagem de erro no `stderr`
2. Envia SIGABRT para o processo
3. Gera um core dump (se configurado)

```
# Testando a deteccao de stack smash
cat > test_canary.c << 'EOF'
#include <stdio.h>
#include <string.h>

void vulnerable() {
    char buffer[16];
    strcpy(buffer, "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
}

int main() {
    vulnerable();
    return 0;
}
EOF

# Compilar com canary
gcc -fstack-protector-strong -o test_canary test_canary.c

# Executar - deve abortar
./test_canary
# Output: *** stack smashing detected ***: terminated
# Exit code: 134 (128 + 6 = SIGABRT)
```

### Canaries e Entropy

O valor do canary e gerado aleatoriamente no inicio da execucao do processo (nao na compilacao). Isso significa que:

- O atacante nao pode prever o valor do canary apenas inspecionando o binario
- Cada execucao tem um canary diferente
- O canary e compartilhado entre todas as funcoes do mesmo processo

```
# O canary e armazenado em uma variavel global
# Acessivel via auxval ou variavel de thread
# Em Linux, esta em libc: __stack_chk_guard

# Para ver o canary em tempo de execucao (exemplo educacional):
#include <stdio.h>
#include <stdint.h>

extern uintptr_t __stack_chk_guard;

int main() {
    printf("Canary value: 0x%lx\n", __stack_chk_guard);
    return 0;
}

# Cada execucao retorna um valor diferente:
# Execucao 1: 0xa3b2c1d0e5f6a7b8
# Execucao 2: 0x1f2e3d4c5b6a7089
```

### Stack Canaries e Entropia

A entropia do canary e importante para a seguranca:

```
# Em x86-64, o canary tem 64 bits de entropia
# Isso significa 2^64 = 18.4 quintilhoes de valores possiveis

# Ataque de brute force do canary:
# - Precisaria de ~2^32 tentativas em media (metade do espaco)
# - Cada tentativa mata o processo
# - Impossivel na pratica

# Canary com zero no byte mais baixo:
# - O byte mais baixo e sempre 0x00
# - Isso evita que o canary seja vazado via string functions
# - Ex: strcpy para no \0, nao vaza o canary inteiro
```

---

## 5. ASLR/PIE: Randomizacao de Endereco

### Address Space Layout Randomization (ASLR)

ASLR randomiza as posicoes das principais estruturas na memoria:

- Stack
- Heap
- Bibliotecas compartilhadas (mmap)
- Executavel principal (quando compilado como PIE)
- VDSO (Virtual Dynamic Shared Object)

```
# Nivel de ASLR no Linux (0-2)
cat /proc/sys/kernel/randomize_va_space

# 0: ASLR desabilitado
# 1: Randomizacao parcial (stack, mmap, vdso)
# 2: Randomizacao completa (stack, mmap, vdso, heap)

# Para desabilitar (APENAS PARA TESTES):
sudo sysctl -w kernel.randomize_va_space=0

# Para restaurar:
sudo sysctl -w kernel.randomize_va_space=2
```

### Position Independent Executable (PIE)

PIE e a parte que depende do compilador. Sem PIE, o executavel e carregado em um endereco fixo, tornando possivel bypassar ASLR para o codigo do proprio programa.

```
# Compilar COM PIE (recomendado)
gcc -o app main.c -pie -fPIE

# Compilar SEM PIE (inseguro para binaries que precisam de protecao)
gcc -o app main.c -no-pie

# Verificar se um binario e PIE
readelf -h /usr/bin/example | grep Type
# Type: DYN (shared object) -> PIE habilitado
# Type: EXEC (executable) -> PIE desabilitado

# Verificar apos execucao
cat /proc/$(pidof myapp)/maps | head -5
# Com PIE: enderecos diferentes a cada execucao
# Sem PIE: enderecos sempre iguais
```

### Como ASLR Funciona em Detalhes

Quando um processo com ASLR habilitado e carregado:

1. O kernel gera um valor aleatorio para cada regiao de memoria
2. O loader (ld-linux) usa esses enderecos para posicionar as estruturas
3. Todas as referencias relativas sao ajustadas de acordo
4. O vdso e mapeado em um endereco aleatorio

```
# Sem ASLR:
#   0x00400000: Codigo do executavel
#   0x00600000: Dados estaticos
#   0x7ffffffde000: Stack
#   Sempre os mesmos enderecos

# Com ASLR (execucao 1):
#   0x55a1b2c3d000: Codigo do executavel
#   0x55a1b2e3e000: Dados estaticos
#   0x7ffd12345000: Stack
#   Enderecos diferentes

# Com ASLR (execucao 2):
#   0x55f8c9d2a000: Codigo do executavel
#   0x55f8c9f2b000: Dados estaticos
#   0x7ffc98765000: Stack
#   Enderecos completamente diferentes
```

### Entropia do ASLR

A entropia do ASLR determina quantos bits de randomizacao estao disponiveis:

```
# x86-64 Linux:
# Stack: 28 bits de entropia (2^28 = 268 milhoes de posicoes)
# Mmap: 28 bits de entropia
# Heap: 13 bits de entropia (limitado pelo brk)
# VDSO: 28 bits de entropia

# x86 (32-bit):
# Stack: 8 bits de entropia (2^25 = 33 milhoes, mas limitado a 8 bits)
# Mmap: 8 bits de entropia
# Heap: 8 bits de entropia

# Verificando a entropia:
# cat /proc/sys/kernel/randomize_va_space
# No Linux, a entropia e configurada no kernel
```

### Ret2libc e Bypass de ASLR

O ataque ret2libc usa funcoes ja carregadas na memoria (como `system()`). Com ASLR, o atacante precisa:

1. Leak de um endereco (via vulnerabilidade de formato ou similar)
2. Calcular o offset ate `system()`
3. Redirecionar a execucao

```
# Cenarios de bypass:
# 1. Info leak + ret2libc
#    - Atacante le um endereco via vulnerabilidade de formato
#    - Calcula offset ate system() usando o endereco leaked
#    - Redireciona execucao para system()

# 2. ROP chain com gadgets
#    - Atacante encontra gadgets no binario
#    - Usa gadgets para construir chamada a system()
#    - Mais dificil com PIE + ASLR

# 3. Brute force
#    - Em 32-bit, espaco de enderecos e pequeno
#    - Brute force pode funcionar em minutos
#    - Em 64-bit, praticamente impossivel
```

### Combinando Protecoes

```
# Stack de protecao completo para ASLR:
gcc -o app main.c \
    -pie -fPIE \           # PIE: randomiza o executavel
    -Wl,-z,relro,-z,now \  # Full RELRO: protege a GOT
    -fstack-protector-strong \  # Canaries: detecta stack smash
    -Wl,-z,noexecstack \   # NX: impede execucao na stack
    -D_FORTIFY_SOURCE=2     # Fortify: protege funcoes de string

# Verificando todas as protecoes:
checksec --file=app
# Expected output:
#   RELRO:           Full RELRO
#   Stack:           Canary found
#   NX:              NX enabled
#   PIE:             PIE enabled
#   FORTIFY:         Fortified
```

### ASLR e Containers

```
# Em containers Docker, ASLR pode ter entropia reduzida
# Para verificar:
cat /proc/1/randomize_va_space  # dentro do container

# Para habilitar em Docker:
# docker run --sysctl kernel.randomize_va_space=2

# Ou no docker-compose.yml:
# sysctls:
#   - kernel.randomize_va_space=2
```

---

## 6. Strip de Simbolos: -s, --strip-all

### O Que Sao Simbolos

Quando voce compila um binario, o compilador gera uma tabela de simbolos que mapeia nomes de funcoes e variaveis para enderecos. Essa tabela e util para:

- Debugging (stack traces, breakpoints)
- Engenharia reversa (analise de binarios)
- Profiling e analise de performance
- Resolucao de simbolos em tempo de execucao

### Por Que Strip

Em producao, a tabela de simbolos e informacao que auxilia um atacante a:

- Identificar funcoes vulneraveis e mapear a estrutura do programa
- Encontrar gadgets para ROP chains
- Entender a logica do codigo sem ler assembly
- Identificar bibliotecas e versoes usadas
- Localizar funcoes de interesse para exploits

```
# Tipos de simbolos em um binario:
# - Funcoes (T, t, W, w)
# - Variaveis globais (D, d, B, b)
# - Constantes (R, r)
# - Simbolos de debug (N, n)
# - Simbolos dinamicos (U, w)

# Listar todos os simbolos
nm -a /usr/bin/example | head -20

# Listar apenas simbolos exportados
nm -D /usr/bin/example | head -20

# Contar simbolos
nm /usr/bin/example | wc -l
```

### Opcoes de Strip

```
# Strip basico: remove simbolos de debug
strip --strip-debug app
# Remove: informacoes DWARF, debug sections
# Mantem: simbolos de referencia, dynamic symbols

# Strip completo: remove todos os simbolos
strip --strip-all app
# Remove: todos os simbolos, debug info, symbol tables
# Mantem: apenas dynamic symbols (necessarios para execucao)

# Strip apenas simbolos desnecessarios
strip --strip-unneeded app
# Remove: simbolos nao referenciados
# Mantem: simbolos usados pelo linker dinamico

# Strip com objcopy (mais controle)
objcopy --strip-debug app app-stripped           # So debug
objcopy --strip-unneeded app app-stripped        # So nao-necessarios
objcopy --strip-all app app-stripped             # Todos
objcopy --keep-symbol=myfunc app app-stripped    # Manter simbolo especifico
objcopy --keep-global-symbol=myfunc app app-stripped  # Manter simbolo global
```

### Comparacao de Tamanhos

```
# Exemplo tipico:
# Antes do strip: 1.2 MB
# Apos --strip-debug: 1.0 MB (reducao de 17%)
# Apos --strip-unneeded: 850 KB (reducao de 29%)
# Apos --strip-all: 720 KB (reducao de 40%)

# Medindo em um projeto real:
ls -la app-before-strip
# -rwxr-xr-x 1 user user 1245672 Jun 15 10:00 app-before-strip

strip --strip-all app-before-strip -o app-after-strip
ls -la app-after-strip
# -rwxr-xr-x 1 user user  745672 Jun 15 10:01 app-after-strip
```

### Impacto no Debugging

Apos strip, voce perde:

- Nomes de funcoes em stack traces (aparecem enderecos)
- Breakpoints baseados em nome de funcao
- Variaveis acessiveis via debugger
- Informacao de tipo para debugging

```
# Exemplo de stack trace sem simbolos:
# #0  0x0000555555555129 in ?? ()
# #1  0x0000555555555147 in ?? ()
# #2  0x00007ffff7e2d083 in __libc_start_main ()

# Exemplo de stack trace com simbolos:
# #0  0x0000555555555129 in vulnerable_function ()
# #1  0x0000555555555147 in main ()
# #2  0x00007ffff7e2d083 in __libc_start_main ()
```

### Estrategias de Gerenciamento

```
# Estrategia 1: Debug completo (desenvolvimento)
gcc -g3 -O0 -o app-debug main.c
# Binario grande, com todos os simbolos e debug info
# Nao strip

# Estrategia 2: Release com debug (producao, com capacidade de debug)
gcc -g2 -O2 -o app main.c
strip --strip-unneeded app
# Binario menor, mas com informacoes de debug preservadas

# Estrategia 3: Producao sem debug
gcc -O2 -o app main.c
strip --strip-all app
# Binario minimo, sem informacoes de debug

# Estrategia 4: Separar debug info
gcc -g2 -O2 -o app main.c
objcopy --only-keep-debug app app.debug
strip --strip-debug app
# Dois arquivos: app (producao) + app.debug (debug)
# Para debug:
# gdb ./app -ex 'add-symbol-file app.debug'

# Estrategia 5: debuginfod
# Servico que fornece debug info sob demanda
export DEBUGINFOD_URLS="https://debuginfod.elfutils.org/"
# GDB busca automaticamente debug info
```

### Symbolling e Seguranca

```
# Verificando se um binario esta stripado
file /usr/bin/example
# ELF 64-bit LSB shared object, ... stripped
# Se nao diz "stripped", os simbolos estao presentes

# Verificando quantos simbolos restam
nm -D /usr/bin/example | wc -l
# Binarios stripados mostram apenas simbolos dinamicos

# Analise de seguranca apos strip
# Mesmo sem simbolos, o binario pode conter:
# - Strings uteis (mensagens de erro, URLs)
# - Patterns de codigo (sequencias de instrucoes)
# - Metadados ELF (headers, sections)
# Strip nao e protecao perfeita, apenas aumenta o custo
```

---

## 7. Debug Info: -g vs Strip

### Formato DWARF

O formato DWARF e o padrao de informacao de debug em binarios ELF. Ele contem:

- Mapeamento de endereco para linha de codigo
- Tipos de dados e estruturas
- Escopo de variaveis
- Informacoes de otimizacao
- Mapeamento de fonte para assembly
- Informacoes de template (C++)
- Closures e lambdas (C++11+)

```
# DWARF versions:
# DWARF 2: Mais antigo, suporte amplo
# DWARF 3: Adiciona compressed debug sections
# DWARF 4: Melhor suporte a C++11
# DWARF 5: Mais recente, melhor compressao e organizacao

# Compilar com DWARF especifico
gcc -gdwarf-4 -g -O2 -o app main.c   # DWARF 4
gcc -gdwarf-5 -g -O2 -o app main.c   # DWARF 5 (default em GCC 11+)

# Niveis de debug
gcc -g0 -o app main.c   # Nenhum debug
gcc -g1 -o app main.c   # Informacoes minimas
gcc -g2 -o app main.c   # Informacoes padrao (recomendado)
gcc -g3 -o app main.c   # Informacoes extras (macros, etc.)
```

### Estrategias de Gerenciamento

```
# Estrategia 1: Debug completo (desenvolvimento)
gcc -g3 -O0 -o app-debug main.c
# Binario grande, com todos os simbolos e debug info
# IDE e debugger funcionam perfeitamente
# Tamanho: ~10x maior que release

# Estrategia 2: Release com debug (producao, debug remoto)
gcc -g2 -O2 -o app main.c
strip --strip-unneeded app
# Binario menor, mas com informacoes de debug preservadas
# Stack traces mostram nomes de funcoes
# Breakpoints baseados em nome funcionam

# Estrategia 3: Producao sem debug
gcc -O2 -o app main.c
strip --strip-all app
# Binario minimo, sem informacoes de debug
# Stack traces mostram apenas enderecos
# Debug requer symbol server ou debuginfod

# Estrategia 4: Separar debug info
gcc -g2 -O2 -o app main.c
objcopy --only-keep-debug app app.debug
strip --strip-debug app
# Dois arquivos: app (producao, ~700KB) + app.debug (debug, ~5MB)
# Para debug:
# gdb ./app -ex 'add-symbol-file app.debug'
# Ou copiar app.debug para symbol server

# Estrategia 5: debuginfod
# Servico que fornece debug info sob demanda
export DEBUGINFOD_URLS="https://debuginfod.elfutils.org/"
# GDB busca automaticamente debug info
# Sem necessidade de manter arquivos .debug locais
```

### Decidindo a Estrategia

| Contexto | Estrategia Recomendada | Tamanho Tipico |
|----------|----------------------|----------------|
| Desenvolvimento local | -g3 -O0, sem strip | 5-20 MB |
| QA/Staging | -g2 -O2, strip --strip-unneeded | 1-3 MB |
| Producao (servico) | -g1 -O2, objcopy --only-keep-debug | 700KB-2MB |
| Producao (embedded) | -O2, strip --strip-all | 100KB-1MB |
| Distribuicao publica | -O2, strip --strip-all + debuginfod | 100KB-1MB |
| Crash reporting | -g2 -O2, strip --strip-debug | 1-2 MB + .debug |

### Debuginfod em Detalhes

```
# debuginfod e um servico HTTP que fornece:
# - Debug info (DWARF)
# - Source code
# - Executables (para comparacao)

# Configuracao no GDB:
set debuginfod enabled on
set debuginfod urls https://debuginfod.elfutils.org/

# Ou via variavel de ambiente:
export DEBUGINFOD_URLS="https://debuginfod.elfutils.org/"

# Como funciona:
# 1. GDB calcula build-id do binario
# 2. GDB faz request HTTP para debuginfod
# 3. debuginfod retorna debug info correspondente
# 4. GDB usa debug info para debugging

# Vantagens:
# - Nao precisa manter arquivos .debug locais
# - Funciona para binarios de distribuicoes Linux
# - Atualizado automaticamente

# Limitacoes:
# - Depende de conexao com a internet
# - Nem todos os binarios estao disponiveis
# - Pode ter latencia na primeira conexao
```

---

## 8. Reproducible Builds: Determinismo

### O Que Sao Builds Reproduziveis

Uma build e reproduzivel quando, dados os mesmos fontes, configuracao e ambiente de compilacao, o resultado binario e identico byte a byte. Isso permite:

- Verificar que o binario distribuido realmente corresponde ao codigo fonte
- Detectar compilacoes adulteradas (supply chain attacks)
- Validar builds de terceiros
- Auditoria independente de binarios distribuidos

### Fontes de Nao-Determinismo

```
# 1. Timestamps embutidos
# __DATE__ e __TIME__ sao comuns mas destroem reproducibilidade
const char *build_time = __TIME__;
const char *build_date = __DATE__;

# 2. Ordem de arquivos no filesystem
# O linker pode incluir arquivos em ordem diferente
# Solucao: usar -frandom-seed e listar arquivos explicitamente

# 3. Enderecos de locais de erro
# Alguns compiladores incluem enderecos de erro no binario
# Solucao: usar -frandom-seed=constante

# 4. Variaveis de ambiente
# LANG, LC_ALL, etc. podem afetar a compilacao
# Solucao: fixar variaveis de ambiente

# 5. Timestamps de metadados
# __TIMESTAMP__ tambem quebra reproducibilidade
# Solucao: nao usar ou usar SOURCE_DATE_EPOCH

# 6. Informacoes de otimizacao
# Compilador pode usar informacoes de profiling
# Solucao: usar -fprofile-arcs ou desabilitar
```

### Configurando CMake para Builds Reproduziveis

```cmake
cmake_minimum_required(VERSION 3.20)
project(ReproducibleApp LANGUAGES C CXX)

# 1. Desabilitar timestamps embutidos
# Usar SOURCE_DATE_EPOCH em vez de __DATE__/__TIME__
if(DEFINED ENV{SOURCE_DATE_EPOCH})
    set(SOURCE_DATE_EPOCH $ENV{SOURCE_DATE_EPOCH})
else()
    # Usar a data do ultimo commit do git
    execute_process(
        COMMAND git log -1 --format=%ct
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        OUTPUT_VARIABLE GIT_TIMESTAMP
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(GIT_TIMESTAMP)
        set(SOURCE_DATE_EPOCH ${GIT_TIMESTAMP})
    else()
        # Fallback: data atual
        string(TIMESTAMP SOURCE_DATE_EPOCH "%s")
    endif()
endif()

add_compile_definitions(SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH})

# 2. Usar -frandom-seed para gerar nomes de temporarios deterministas
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -frandom-seed=${TARGET_NAME}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -frandom-seed=${TARGET_NAME}")

# 3. Determinar o padrao de formatacao
set(LANG "en_US.UTF-8")
set(LC_ALL "en_US.UTF-8")
set(TZ "UTC")

# 4. Garantir compilacao determinista no linker
add_link_options(
    -Wl,--hash-style=both
    -Wl,--build-id=sha1
)

# 5. Desabilitar informacoes que quebram determinismo
add_compile_options(
    -frandom-seed=${TARGET_NAME}
    -Wno-date-time  # Desabilita warning sobre __DATE__/__TIME__
)
```

### Ambiente de Build Controlado

```bash
#!/bin/bash
# build-reproducible.sh - Script para build reproduzivel
set -euo pipefail

# Configurar ambiente determinista
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export TZ=UTC

# Limpar build anterior
rm -rf build-reproducible
mkdir build-reproducible

# Configurar compiladores padrao
export CC=gcc
export CXX=g++
export CFLAGS="-O2 -frandom-seed=${SOURCE_DATE_EPOCH}"
export CXXFLAGS="-O2 -frandom-seed=${SOURCE_DATE_EPOCH}"

# Configurar cmake com opcoes reproduziveis
cmake -B build-reproducible \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DSOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH} \
    -DCMAKE_C_FLAGS="-frandom-seed=reproducible" \
    -DCMAKE_CXX_FLAGS="-frandom-seed=reproducible"

# Build
cmake --build build-reproducible

# Gerar checksums
cd build-reproducible
sha256sum app > ../checksums-build1.sha256
echo "Build 1 completada. Checksum: $(cat ../checksums-build1.sha256)"
```

### Verificando Reproducibilidade

```bash
# Build 1
./build-reproducible.sh
cp build-reproducible/app app-build1

# Build 2 (mesmo ambiente)
./build-reproducible.sh
cp build-reproducible/app app-build2

# Comparar binarios
echo "=== Comparacao de binarios ==="
echo "Tamanho Build 1: $(wc -c < app-build1) bytes"
echo "Tamanho Build 2: $(wc -c < app-build2) bytes"
echo "Hash Build 1: $(sha256sum app-build1 | cut -d' ' -f1)"
echo "Hash Build 2: $(sha256sum app-build2 | cut -d' ' -f1)"

# Comparar byte a byte
if diff <(xxd app-build1) <(xxd app-build2) > /dev/null 2>&1; then
    echo "BUILD REPRODUZIVEL: Binarios identicos"
else
    echo "BUILD NAO REPRODUZIVEL: Binarios diferentes"
    diff <(xxd app-build1) <(xxd app-build2) | head -20
fi

# Ou usando sha256sum
if sha256sum app-build1 app-build2 | awk '{print $1}' | sort -u | wc -l | grep -q '^1$'; then
    echo "BUILD REPRODUZIVEL: Mesmo hash SHA-256"
else
    echo "BUILD NAO REPRODUZIVEL: Hashes diferentes"
fi
```

### Ferramentas de Verificacao

```
# diffoscope: comparacao profunda de binarios
diffoscope app-build1 app-build2

# reprotest: testa reprodutibilidade
reprotest --auto-test --vary=-all ./build-script.sh .

# diffbin: comparacao de binarios
diffbin app-build1 app-build2

# Comparacao manual com xxd
diff <(xxd app-build1) <(xxd app-build2)
```

### Caso Real: Debian

```
# O Debian e um dos maiores projetos de builds reproduziveis
# Mais de 95% dos pacotes sao reproduziveis

# Para verificar a reprodutibilidade de um pacote Debian:
# 1. Baixar o pacote .deb
# 2. Baixar o codigo fonte
# 3. Compilar no mesmo ambiente
# 4. Comparar os binarios

# Ferramentas:
# - diffoscope
# - difftest
# - reprotest
```

---

## 9. Binary Diffing: Verificacao de Integridade

### Por Que Binary Diffing

Binary diffing e a comparacao entre dois binarios para identificar diferencas. E util para:

- Verificar que uma atualizacao de compilacao nao introduziu mudancas inesperadas
- Comparar versoes de bibliotecas antes e depois de patches
- Detectar adulteracao em binarios distribuidos
- Validar que builds reproduziveis realmente produzem o mesmo resultado
- Analisar mudancas em bibliotecas de terceiros

### Ferramentas de Binary Diffing

```
# diff binario simples com xxd
diff <(xxd binary1) <(xxd binary2)

# Comparar com binwalk (analise de firmware/binarios)
binwalk -W binary1 binary2

# Usando radiff2 (do Radare2)
radiff2 -s binary1 binary2  # Comparacao estatica
radiff2 -d binary1 binary2  # Comparacao dinamica
radiff2 -x binary1 binary2  # Comparacao de exportacoes

# Usando Diaphora (plugin IDA Pro)
# Ferramenta grafica para diffing detalhado
# Identifica funcoes correspondentes entre binarios

# Usando Binary Ninja
# Ferramenta comercial com diffing integrado
```

### Implementando Verificacao em CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(BinaryIntegrity LANGUAGES C CXX)

add_executable(myapp main.c)

# Gerar checksums apos build
add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E sha256sum $<TARGET_FILE:myapp>
    > ${CMAKE_BINARY_DIR}/${TARGET_NAME}.sha256
    COMMENT "Gerando checksum SHA-256 do binario"
)

# Verificar checksum contra valor esperado
set(EXPECTED_HASH "" CACHE STRING "Hash SHA-256 esperado")

if(EXPECTED_HASH)
    add_custom_target(verify-integrity
        COMMAND ${CMAKE_COMMAND} -E echo "Verificando integridade..."
        COMMAND ${CMAKE_COMMAND} -E sha256sum $<TARGET_FILE:myapp>
        > ${CMAKE_BINARY_DIR}/current-hash.sha256
        COMMAND diff ${CMAKE_BINARY_DIR}/current-hash.sha256
            <(echo "${EXPECTED_HASH}  $<TARGET_FILE:myapp>")
        DEPENDS myapp
        COMMENT "Verificando integridade do binario"
    )
endif()

# Target para comparar com build anterior
set(PREVIOUS_BINARY "" CACHE FILEPATH "Binario anterior para comparar")

if(PREVIOUS_BINARY)
    add_custom_target(diff-binary
        COMMAND diff <(xxd ${PREVIOUS_BINARY})
                     <(xxd $<TARGET_FILE:myapp>)
        COMMENT "Comparando binarios"
    )

    # Comparacao detalhada com readelf
    add_custom_target(diff-binary-detailed
        COMMAND ${CMAKE_COMMAND} -E echo "=== Headers ELF ==="
        COMMAND diff <(readelf -h ${PREVIOUS_BINARY})
                     <(readelf -h $<TARGET_FILE:myapp>)
        COMMAND ${CMAKE_COMMAND} -E echo "=== Sections ==="
        COMMAND diff <(readelf -S ${PREVIOUS_BINARY})
                     <(readelf -S $<TARGET_FILE:myapp>)
        COMMAND ${CMAKE_COMMAND} -E echo "=== Symbols ==="
        COMMAND diff <(nm ${PREVIOUS_BINARY} | sort)
                     <(nm $<TARGET_FILE:myapp> | sort)
        COMMENT "Comparacao detalhada de binarios"
    )
endif()

# SBOM e Binary Attestation
find_program(SYFT_EXECUTABLE syft)
if(SYFT_EXECUTABLE)
    add_custom_target(generate-sbom
        COMMAND ${SYFT_EXECUTABLE} scan dir:${CMAKE_BINARY_DIR}
            -o spdx-json > ${CMAKE_BINARY_DIR}/sbom.spdx.json
        COMMENT "Gerando SBOM"
    )
endif()

find_program(COSIGN_EXECUTABLE cosign)
if(COSIGN_EXECUTABLE)
    add_custom_target(attest-binary
        COMMAND ${COSIGN_EXECUTABLE} attest
            --predicate ${CMAKE_BINARY_DIR}/sbom.spdx.json
            --type spdxjson
            $<TARGET_FILE:myapp>
        COMMENT "Gerando attestacao do binario"
    )
endif()
```

### Analise de Diferencas

```
# Quando comparar dois binarios, as diferencas podem indicar:
# 1. Mudancas no codigo fonte (normal)
# 2. Mudancas no compilador ou flags (possivel problema)
# 3. Adulteracao ou compilacao maliciosa (problema de seguranca)

# Tipos de diferencas:
# - Secao .text: mudancas de codigo
# - Secao .data: mudancas de dados globais
# - Secao .rodata: mudancas de constantes
# - Secao .bss: mudancas de variaveis nao inicializadas
# - Build ID: mudanca indica compilacao diferente

# Build ID:
readelf -n binary1 | grep "Build ID"
readelf -n binary2 | grep "Build ID"
# Mesmo build ID = mesma compilacao
# Build ID diferente = compilacao diferente

# Para projetos que exigem verificacao de integridade:
# 1. Gerar build ID durante compilacao
# 2. Armazenar build ID junto com o binario
# 3. Verificar build ID antes de executar
```

---

## 10. Code Signing: Sign e Verify

### Conceitos Fundamentais

Code signing usa criptografia assimetrica para provar:

- **Autenticidade**: Quem assinou e realmente quem diz ser
- **Integridade**: O binario nao foi alterado desde a assinatura
- **Nao-repudio**: O assinante nao pode negar que assinou
- **Tempo**: A assinatura prova que o binario existia em uma data especifica

### Fluxo de Assinatura

```
Fluxo de Assinatura:
1. Desenvolvedor gera par de chaves (privada + publica)
2. Desenvolvedor assina o binario com a chave privada
3. A assinatura e distribuida junto com o binario
4. Usuario obtem a chave publica (de fonte confiavel)
5. Usuario verifica a assinatura com a chave publica

Fluxo de Verificacao:
1. Usuario recebe binario + assinatura
2. Usuario baixa chave publica do assinante
3. Ferramenta de verificacao compara:
   a. Hash do binario com hash na assinatura
   b. Assinatura com chave publica
4. Se tudo bate: binario e autentico e integro
5. Se nao bate: binario pode ter sido adulterado
```

### Assinatura com GPG

```bash
# Gerar par de chaves
gpg --full-generate-key
# Escolher:
# - RSA and RSA (padrao)
# - 4096 bits
# - Nunca expira
# - Nome e email validos

# Exportar chave publica (para distribuicao)
gpg --export --armor dev@example.com > public-key.asc

# Importar chave publica (para verificacao)
gpg --import public-key.asc

# Assinar o binario
gpg --armor --detach-sign myapp
# Gera myapp.asc (assinatura detached)

# Assinar com chave especifica
gpg --armor --detach-sign --local-user ABCD1234 myapp

# Verificar a assinatura
gpg --verify myapp.asc myapp
# Output esperado:
# gpg: Signature used key ABCD1234
# gpg: Good signature from "Developer <dev@example.com>"

# Verificar com verificacao verbose
gpg --verify --verbose myapp.asc myapp

# Listar assinaturas em um binario
gpg --list-packets myapp.asc
```

### Assinatura com Sigstore/cosign

```
# Sigstore e um ecossistema de assinatura sem gerenciar chaves
# Usa identidade (email, OIDC) em vez de chaves long-term

# Assinar com cosign (sem gerenciar chaves)
cosign sign-blob myapp > myapp.sig

# Assinar com OIDC (GitHub Actions, Google, etc.)
cosign sign-blob \
    --oidc-issuer=https://token.actions.githubusercontent.com \
    --identity-token=$GITHUB_TOKEN \
    myapp > myapp.sig

# Verificar com cosign
cosign verify-blob myapp \
    --signature myapp.sig \
    --certificate-identity=dev@example.com \
    --certificate-oidc-issuer=https://accounts.google.com

# Verificar com chave publica
cosign verify-blob myapp \
    --signature myapp.sig \
    --key=cosign.pub

# Assinar com SBOM integrado
cosign attest \
    --predicate sbom.spdx.json \
    --type spdxjson \
    myapp
```

### Assinatura com minisign

```
# minisign e uma ferramenta simples e segura de assinatura
# Mais simples que GPG, focada em assinatura de artefatos

# Gerar chave
minisign -G -s private-key.txt -p public-key.txt

# Assinar
minisign -S -s private-key.txt -m myapp

# Verificar
minisign -Vm myapp -P public-key.txt
# Output: Signature and comment signature verified
```

### Integracao com CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(SignedApp LANGUAGES C CXX)

add_executable(myapp main.c)

# Assinatura com GPG
find_program(GPG_EXECUTABLE gpg)
set(GPG_KEY_ID "" CACHE STRING "ID da chave GPG para assinatura")

if(GPG_EXECUTABLE AND GPG_KEY_ID)
    add_custom_command(TARGET myapp POST_BUILD
        COMMAND ${GPG_EXECUTABLE} --armor --detach-sign
            --local-user ${GPG_KEY_ID}
            $<TARGET_FILE:myapp>
        COMMENT "Assinando binario com GPG"
    )
endif()

# Assinatura com cosign (Sigstore)
find_program(COSIGN_EXECUTABLE cosign)
if(COSIGN_EXECUTABLE)
    add_custom_command(TARGET myapp POST_BUILD
        COMMAND ${COSIGN_EXECUTABLE} sign-blob
            $<TARGET_FILE:myapp>
            > $<TARGET_FILE:myapp>.sig
        COMMENT "Assinando binario com Sigstore"
    )
endif()

# Assinatura com minisign
find_program(MINISIGN_EXECUTABLE minisign)
if(MINISIGN_EXECUTABLE)
    set(MINISIGN_KEY "" CACHE FILEPATH "Chave privada minisign")
    if(MINISIGN_KEY)
        add_custom_command(TARGET myapp POST_BUILD
            COMMAND ${MINISIGN_EXECUTABLE} -S
                -s ${MINISIGN_KEY}
                -m $<TARGET_FILE:myapp>
            COMMENT "Assinando binario com minisign"
        )
    endif()
endif()

# Verificacao de assinatura
add_custom_target(verify-signature
    COMMAND ${CMAKE_COMMAND} -E echo "=== Verificacao de Assinatura ==="
    COMMAND ${GPG_EXECUTABLE} --verify
        $<TARGET_FILE:myapp>.asc
        $<TARGET_FILE:myapp>
    DEPENDS myapp
    COMMENT "Verificando assinatura GPG"
)
```

### Chain of Trust

```
# Para que a verificacao de assinatura seja util, e necessario
# estabelecer uma cadeia de confianca (chain of trust):

# 1. Gerar chaves em ambiente seguro
# 2. Publicar chave publica em fonte confiavel
# 3. Usar HSM ou KMS para proteger chave privada
# 4. Implementar revogacao de chaves
# 5. Usar timestamping para provar data de assinatura

# Timestamping:
# - RFC 3161: padrao de timestamping
# - Autoridades: DigiCert, Sectigo, etc.
# - Prova que a assinatura foi feita antes de uma data

# Para GPG:
gpg --detach-sign --timestamp myapp
# O timestamp e incluido na assinatura

# Para Sigstore:
# Sigstore usa transparency logs (Rekor)
# Cada assinatura e registrada em um log publico
```

---

## 11. CMake Properties: INSTALL_RPATH, SKIP_BUILD_RPATH

### O Que e RPATH

RPATH (Run Path) e uma lista de diretorios embutida no binario que o loader usa para encontrar bibliotecas compartilhadas em tempo de execucao. E uma alternativa mais segura ao `LD_LIBRARY_PATH`, que pode ser manipulado por atacantes.

### Propriedades CMake Relevantes

```cmake
# CMAKE_SKIP_BUILD_RPATH
# Se TRUE, nao inclui rpath durante o build
# Util para builds de desenvolvimento onde as bibliotecas
# estao no diretorio de build
set(CMAKE_SKIP_BUILD_RPATH FALSE)

# CMAKE_SKIP_INSTALL_RPATH
# Se TRUE, nao inclui rpath no install
# Util quando as bibliotecas estao em diretorios padrao
set(CMAKE_SKIP_INSTALL_RPATH FALSE)

# CMAKE_INSTALL_RPATH
# Diretorios adicionais para rpath no install
# Pode usar $ORIGIN para referenciar diretorio do executavel
set(CMAKE_INSTALL_RPATH "/opt/myapp/lib;/usr/local/lib")
set(CMAKE_INSTALL_RPATH "$ORIGIN/../lib;$ORIGIN/lib")

# CMAKE_INSTALL_RPATH_USE_LINK_PATH
# Se TRUE, adiciona diretorios de link ao rpath
# Util quando as bibliotecas estao em diretorios nao-padrao
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

# INSTALL_RPATH (propriedade por target)
# Permite configurar RPATH especifico para cada target
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "/opt/myapp/lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# BUILD_RPATH
# RPATH usado durante o build (nao durante a instalacao)
set_target_properties(myapp PROPERTIES
    BUILD_RPATH "$<TARGET_FILE_DIR:mylib>"
)

# BUILD_WITH_INSTALL_RPATH
# Se TRUE, usa o INSTALL_RPATH durante o build
set_target_properties(myapp PROPERTIES
    BUILD_WITH_INSTALL_RPATH FALSE
)

# SKIP_BUILD_RPATH
# Se TRUE, nao inclui rpath durante o build
set_target_properties(myapp PROPERTIES
    SKIP_BUILD_RPATH FALSE
)
```

### RPATH vs LD_LIBRARY_PATH

```
# Usar rpath (RECOMENDADO):
# - O binario sabe onde encontrar suas bibliotecas
# - Nao depende de configuracao externa
# - Mais seguro: atacante nao pode redirecionar
# - Funciona em qualquer ambiente

# Usar LD_LIBRARY_PATH (NAO RECOMENDADO):
# - Variavel de ambiente pode ser manipulada
# - Atacante pode apontar para bibliotecas maliciosas
# - Funciona apenas no momento da execucao
# - Nao e persistente entre sessoes

# Uso aceitavel de LD_LIBRARY_PATH:
# - Desenvolvimento local
# - Testes
# - Sistemas embedded onde rpath nao e suportado

# Perigo real:
# Se LD_LIBRARY_PATH for configurado via /etc/environment
# ou ~/.bashrc, um atacante que compromete esses arquivos
# pode redirecionar todas as chamadas de biblioteca
```

### $ORIGIN e RPATH Relativo

```
# $ORIGIN e expandido para o diretorio do executavel
# Isso permite distribuicao portavel

# Exemplo de estrutura de distribuicao:
# myapp-1.0/
#   bin/myapp
#   lib/libmylib.so
#   lib/libother.so

# RPATH com $ORIGIN:
# myapp procura libmylib.so em $ORIGIN/../lib
# Independente de onde myapp esteja instalado

# Configuracao no CMake:
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
)

# Verificando o rpath:
readelf -d myapp | grep RPATH
# RPATH: $ORIGIN/../lib
```

### Exemplo Pratico de RPATH

```cmake
cmake_minimum_required(VERSION 3.20)
project(RpathExample LANGUAGES C CXX)

# Biblioteca interna
add_library(mylib SHARED mylib.c)
set_target_properties(mylib PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    INSTALL_RPATH "$ORIGIN"
)

# Biblioteca de sistema (nao precisa de rPATH)
find_library(MATH_LIB m)

# Executavel que usa as bibliotecas
add_executable(myapp main.c)
target_link_libraries(myapp PRIVATE mylib ${MATH_LIB})

# Configurar RPATH
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib;$ORIGIN/lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
    BUILD_RPATH "$<TARGET_FILE_DIR:mylib>"
    BUILD_WITH_INSTALL_RPATH FALSE
)

# Instalacao
install(TARGETS mylib
    LIBRARY DESTINATION lib
)
install(TARGETS myapp
    RUNTIME DESTINATION bin
)
```

### Verificando RPATH

```
# Ver rpath de um binario
readelf -d /opt/myapp/bin/myapp | grep -E '(RPATH|RUNPATH)'

# Output:
# RPATH: /opt/myapp/lib

# Ou com objdump
objdump -x /opt/myapp/bin/myapp | grep -E '(RPATH|RUNPATH)'

# Ou com patchelf (ferramenta para modificar rPATH)
patchelf --print-rpath /opt/myapp/bin/myapp
patchelf --set-rpath '/opt/myapp/lib' /opt/myapp/bin/myapp

# Verificar LD_LIBRARY_PATH usado
LD_DEBUG=libs /opt/myapp/bin/myapp 2>&1 | head -20
# Mostra onde o loader procura cada biblioteca

# Verificar se rpath e seguro
# Rpath deve apontar para diretorios controlados pelo desenvolvedor
# Rpath NAO deve apontar para diretorios globaveis
```

---

## 12. CMake Install: DESTDIR, CMAKE_INSTALL_PREFIX

### O Problema de Instalacao

Quando voce instala um software, o processo precisa:

1. Copiar binarios para o diretorio correto
2. Configurar permissoes adequadas
3. Gerar scripts de inicializacao
4. Respeitar a hierarquia de diretorios do sistema
5. Funcionar tanto para instalacao direta quanto para staging

### DESTDIR

DESTDIR e uma variavel usada para instalar o software em um diretorio temporario (staging). E essencial para:

- Gerenciadores de pacote (dpkg, rpm, pacman)
- Builds de container
- Testes de instalacao
- Instalacao em ambientes controlados

```bash
# Instalacao normal (requer permissao de root)
cmake --install build --prefix /usr/local

# Instalacao com DESTDIR (staging, nao requer root)
DESTDIR=/tmp/staging cmake --install build --prefix /usr/local

# Resultado:
# /tmp/staging/usr/local/bin/myapp
# /tmp/staging/usr/local/lib/libmylib.so
# /tmp/staging/usr/local/share/doc/myapp/README.md

# Para gerar pacote .deb:
dpkg-buildpackage -us -uc
# Internamente usa DESTDIR para staging

# Para gerar pacote .rpm:
rpmbuild
# Internamente usa DESTDIR para staging
```

### CMAKE_INSTALL_PREFIX

CMAKE_INSTALL_PREFIX define o diretorio raiz para instalacao:

```cmake
cmake_minimum_required(VERSION 3.20)
project(InstallExample LANGUAGES C CXX)

add_executable(myapp main.c)

# Usar GNUInstallDirs para padronizacao
include(GNUInstallDirs)

# Instalacao padrao
install(TARGETS myapp
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Comando de configuracao:
# cmake -B build -DCMAKE_INSTALL_PREFIX=/usr/local
# cmake --install build

# Para instalacao em diretorio do usuario:
# cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/.local
# cmake --install build
```

### GNUInstallDirs

O modulo GNUInstallDirs padroniza os diretorios de instalacao:

```
# Diretorios padrao (variaveis CMAKE_INSTALL_*):
CMAKE_INSTALL_BINDIR      -> bin
CMAKE_INSTALL_SBINDIR     -> sbin
CMAKE_INSTALL_LIBDIR      -> lib ou lib64
CMAKE_INSTALL_LIBEXECDIR  -> libexec
CMAKE_INSTALL_INCLUDEDIR  -> include
CMAKE_INSTALL_DATADIR     -> share
CMAKE_INSTALL_MANDIR      -> share/man
CMAKE_INSTALL_INFODIR     -> share/info
CMAKE_INSTALL_SYSCONFDIR  -> etc
CMAKE_INSTALL_LOCALSTATEDIR -> var

# Uso no CMake:
include(GNUInstallDirs)

install(TARGETS myapp
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(FILES myapp.conf
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}/myapp
)

install(DIRECTORY DESTINATION ${CMAKE_INSTALL_LOCALSTATEDIR}/lib/myapp)
```

### Instalacao Segura

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureInstall LANGUAGES C CXX)

add_executable(myapp main.c)

include(GNUInstallDirs)

# Instalacao com permissoes restritas
install(TARGETS myapp
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE
        GROUP_READ GROUP_EXECUTE
        WORLD_READ WORLD_EXECUTE
)

# Configuracao com permissoes restritas
install(FILES myapp.conf
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}/myapp
    PERMISSIONS
        OWNER_READ OWNER_WRITE
        GROUP_READ
        WORLD_READ
)

# Diretorio de dados privado
install(DIRECTORY DESTINATION ${CMAKE_INSTALL_LOCALSTATEDIR}/lib/myapp
    DIRECTORY_PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE
        GROUP_READ GROUP_EXECUTE
        WORLD_NONE
)

# Arquivos de documentacao
install(FILES README.md LICENSE
    DESTINATION ${CMAKE_INSTALL_DOCDIR}
    PERMISSIONS
        OWNER_READ OWNER_WRITE
        GROUP_READ
        WORLD_READ
)
```

### Scripts de Desinstalacao

```cmake
# Gerar script de desinstalacao
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake_uninstall.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
    @ONLY
)

add_custom_target(uninstall
    COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
)
```

```cmake
# cmake_uninstall.cmake.in
if(NOT EXISTS "@CMAKE_CURRENT_BINARY_DIR@/install_manifest.txt")
    message(FATAL_ERROR
        "Cannot find install manifest: "
        "@CMAKE_CURRENT_BINARY_DIR@/install_manifest.txt")
endif()

file(READ "@CMAKE_CURRENT_BINARY_DIR@/install_manifest.txt" files)
string(REGEX REPLACE "\n" ";" files "${files}")

foreach(file ${files})
    message(STATUS "Uninstalling $ENV{DESTDIR}${file}")
    if(IS_SYMLINK "$ENV{DESTDIR}${file}" OR EXISTS "$ENV{DESTDIR}${file}")
        exec_program(
            "@CMAKE_COMMAND@" ARGS "-E remove \"$ENV{DESTDIR}${file}\""
            OUTPUT_VARIABLE rm_out
            RETURN_VALUE rm_retval
        )
        if(NOT "${rm_retval}" STREQUAL 0)
            message(FATAL_ERROR "Problem when removing $ENV{DESTDIR}${file}")
        endif()
    else()
        message(STATUS "File $ENV{DESTDIR}${file} does not exist.")
    endif()
endforeach()
```

---

## 13. Security Headers no Binario: stack_chk_fail

### Headers de Seguranca

Os "security headers" no contexto de binarios sao as funcoes e estruturas que o compilador usa para implementar protecoes em tempo de execucao.

### stack_chk_fail e Suas Dependencias

```
# A funcao __stack_chk_fail e fornecida por:
# - libc (glibc)
# - musl libc
# - libssp (Stack Smashing Protection)

# Para sistemas sem libc completa (embedded):
# Compilar libssp estaticamente
gcc -fstack-protector-strong -static-libssp -o app main.c

# Ou implementar __stack_chk_fail manualmente (emergencia)
void __stack_chk_fail(void) {
    // Log do erro
    write(2, "Stack smashing detected!\n", 25);
    // Abortar o processo
    _exit(127);
}

# Ou desabilitar stack canary (PERIGOSO)
gcc -fno-stack-protector -o app main.c
```

### Outras Funcoes de Seguranca

```
# __fortify_chk: verificacao de buffer em funcoes de string
# Ativada com -D_FORTIFY_SOURCE=2

# Funcoes protegidas por FORTIFY_SOURCE:
# - memcpy, memmove, memccpy
# - strcpy, strncpy, stpcpy, stpncpy
# - strcat, strncat
# - sprintf, snprintf, vsprintf, vsnprintf
# - gets (descontinuada)
# - realpath
# - getcwd
# - getwd

# Como funciona:
# O compilador substitui chamadas como:
#   memcpy(dest, src, n)
# Por:
#   __memcpy_chk(dest, src, n, __bos(dest))
# Onde __bos retorna o tamanho do buffer destino

# Se n > __bos(dest):
#   __fortify_chk_abort("buffer overflow detected")
```

### Protecao Contra Formato String

```
# Compilador pode detectar format strings em tempo de compilacao
# Com -Wformat -Wformat-security

# Ruim:
printf(user_input);  // Vulneravel a format string
fprintf(stderr, user_input);  // Vulneravel

# Bom:
printf("%s", user_input);  // Seguro
fprintf(stderr, "%s", user_input);  // Seguro

# CMake para ativar warnings de formato:
add_compile_options(-Wformat -Wformat-security -Werror=format-security)

# Verificacao em runtime:
# Com FORTIFY_SOURCE, o compilador detecta format strings
# em tempo de compilacao quando possivel
```

### Protecao Contra Integer Overflow

```
# Compilador pode detectar overflows de inteiro
# Com -ftrapv (debug) e -fstack-protector-strong

# Ruim:
int malloc_size = count * sizeof(void*);
void *p = malloc(malloc_size);  // Overflow possivel

# Bom:
size_t malloc_size;
if (__builtin_mul_overflow(count, sizeof(void*), &malloc_size)) {
    return -1;  // Overflow detectado
}
void *p = malloc(malloc_size);

# Ou usando a verificacao de C:
#include <stdint.h>
#include <stdbool.h>

bool safe_multiply(size_t a, size_t b, size_t *result) {
    return __builtin_mul_overflow(a, b, result);
}
```

### Protecao Contra Return-Oriented Programming (ROP)

```
# Full RELRO impede a sobreescrita da GOT
# Mas o atacante pode usar ROP com gadgets ja no binario

# Protecoes contra ROP:
# 1. Stack canaries: detectam stack smash
# 2. ASLR/PIE: randomizam enderecos
# 3. Full RELRO: protegem a GOT
# 4. CFI (Control Flow Integrity): verifica saltos
#    - Clang: -fsanitize=cfi
#    - GCC: -fcf-protection

# CFI com Clang:
clang -fsanitize=cfi -fvisibility=hidden -o app main.c

# CFI com GCC:
gcc -fcf-protection=full -o app main.c

# CFI impede:
# - Saltos para enderecos arbitrarios
# - Chamadas indiretas para funcoes incorretas
# - Retornos para enderecos incorretos
```

---

## 14. Exemplo: Target Hardening Completo

Este e um exemplo completo de CMakeLists.txt que aplica todas as tecnicas de hardening discutidas neste capitulo.

```cmake
cmake_minimum_required(VERSION 3.20)
project(HardenedApp
    VERSION 1.0.0
    DESCRIPTION "Aplicacao com hardening completo"
    LANGUAGES C CXX
)

# ============================================================
# Configuracao de Build
# ============================================================

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type padrao: Release com otimizacoes
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# ============================================================
# Flags de Seguranca do Compilador
# ============================================================

# Protecao de stack
add_compile_options(
    -fstack-protector-strong     # Stack canaries
    -fstack-clash-protection     # Protecao contra stack clash
)

# Protecao de memoria
add_compile_options(
    -D_FORTIFY_SOURCE=2          # Fortify em funcoes de string
    -Wformat -Wformat-security -Werror=format-security
)

# Warnings de seguranca
add_compile_options(
    -Wall -Wextra -Wpedantic
    -Wconversion
    -Wsign-conversion
    -Wnull-dereference
    -Wimplicit-fallthrough
    -Wdouble-promotion
    -Wformat=2
)

# Otimizacoes que auxiliam seguranca
add_compile_options(
    -fPIE                        # Position Independent Executable
    -ftrapv                      # Trap em overflow de inteiro (debug)
)

# Flags especificas por build type
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_compile_options(-g3 -O0)
elseif(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_compile_options(-O2 -DNDEBUG)
elseif(CMAKE_BUILD_TYPE STREQUAL "RelWithDebInfo")
    add_compile_options(-g2 -O2)
elseif(CMAKE_BUILD_TYPE STREQUAL "MinSizeRel")
    add_compile_options(-Os -DNDEBUG)
endif()

# ============================================================
# Flags de Seguranca do Linker
# ============================================================

add_link_options(
    -Wl,-z,relro,-z,now         # Full RELRO
    -Wl,-z,noexecstack           # NX/DEP na stack
    -Wl,-z,separate-code          # Codigo separado de dados
    -Wl,--hash-style=both         # Hash style para performance
    -Wl,--build-id=sha1           # Build ID para verificacao
    -pie                          # PIE no executavel
)

# ============================================================
# Target Principal
# ============================================================

add_executable(myapp
    src/main.c
    src/utils.c
    src/crypto.c
)

target_include_directories(myapp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_link_libraries(myapp PRIVATE
    m        # math library
    pthread  # threading
)

# ============================================================
# RPATH Seguro
# ============================================================

set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
    BUILD_RPATH_USE_ORIGIN TRUE
    SKIP_BUILD_RPATH FALSE
    BUILD_WITH_INSTALL_RPATH FALSE
)

# ============================================================
# Symbol Stripping
# ============================================================

# Strip completo para Release
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    find_program(CMAKE_STRIP strip)
    if(CMAKE_STRIP)
        add_custom_command(TARGET myapp POST_BUILD
            COMMAND ${CMAKE_STRIP} --strip-all $<TARGET_FILE:myapp>
            COMMENT "Removendo simbolos do binario"
        )
    endif()
endif()

# ============================================================
# Debug Info Separado
# ============================================================

if(CMAKE_BUILD_TYPE STREQUAL "RelWithDebInfo")
    find_program(CMAKE_OBJCOPY objcopy)
    if(CMAKE_OBJCOPY)
        add_custom_command(TARGET myapp POST_BUILD
            COMMAND ${CMAKE_OBJCOPY} --only-keep-debug
                $<TARGET_FILE:myapp>
                $<TARGET_FILE:myapp>.debug
            COMMAND ${CMAKE_STRIP} --strip-debug $<TARGET_FILE:myapp>
            COMMENT "Separando informacoes de debug"
        )
    endif()
endif()

# ============================================================
# Checksum e Verificacao de Integridade
# ============================================================

add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E sha256sum $<TARGET_FILE:myapp>
        > ${CMAKE_BINARY_DIR}/${TARGET_NAME}-${PROJECT_VERSION}.sha256
    COMMENT "Gerando checksum SHA-256"
)

# ============================================================
# Code Signing (opcional)
# ============================================================

option(ENABLE_SIGNING "Habilitar assinatura de binarios" OFF)

if(ENABLE_SIGNING)
    find_program(GPG_EXECUTABLE gpg)
    if(GPG_EXECUTABLE)
        set(GPG_KEY_ID "" CACHE STRING "ID da chave GPG")

        add_custom_command(TARGET myapp POST_BUILD
            COMMAND ${GPG_EXECUTABLE} --armor --detach-sign
                --local-user ${GPG_KEY_ID}
                $<TARGET_FILE:myapp>
            COMMENT "Assinando binario com GPG"
        )
    endif()
endif()

# ============================================================
# Instalacao Segura
# ============================================================

include(GNUInstallDirs)

install(TARGETS myapp
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE
        GROUP_READ GROUP_EXECUTE
        WORLD_READ WORLD_EXECUTE
)

# Configuracao do usuario
install(FILES config/myapp.conf
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}/myapp
    PERMISSIONS
        OWNER_READ OWNER_WRITE
        GROUP_READ
        WORLD_READ
)

# ============================================================
# Verificacao de Build
# ============================================================

# Target para verificar o binario resultante
add_custom_target(verify-harden
    COMMAND ${CMAKE_COMMAND} -E echo "=== Verificacao de Hardening ==="
    COMMAND checksec --file=$<TARGET_FILE:myapp> || echo "checksec nao encontrado"
    COMMAND readelf -d $<TARGET_FILE:myapp> | grep -E '(BIND_NOW|RPATH)' || true
    COMMAND readelf -l $<TARGET_FILE:myapp> | grep GNU_STACK || true
    COMMAND readelf -h $<TARGET_FILE:myapp> | grep Type || true
    DEPENDS myapp
    COMMENT "Verificando protecoes do binario"
)

# Target para verificacao completa
add_custom_target(security-audit
    COMMAND ${CMAKE_COMMAND} --build . --target verify-harden
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "=== Tamanho do Binario ==="
    COMMAND ls -lh $<TARGET_FILE:myapp>
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "=== Simbolos Restantes ==="
    COMMAND nm -D $<TARGET_FILE:myapp> | wc -l
    COMMAND ${CMAKE_COMMAND} -E echo ""
    COMMAND ${CMAKE_COMMAND} -E echo "=== Sections ==="
    COMMAND readelf -S $<TARGET_FILE:myapp> | grep -E '(stack|relro|gnu)' || true
    DEPENDS myapp
    COMMENT "Auditoria completa de seguranca do binario"
)
```

### Analisando o Exemplo

Este CMakeLists.txt implementa:

1. **Stack canaries** via `-fstack-protector-strong` e `-fstack-clash-protection`
2. **Full RELRO** via `-Wl,-z,relro,-z,now`
3. **PIE** via `-fPIE` e `-pie`
4. **NX/DEP** via `-Wl,-z,noexecstack`
5. **FORTIFY_SOURCE** via `-D_FORTIFY_SOURCE=2`
6. **Strip de simbolos** via `cmake --strip-all` apos build
7. **Debug info separado** para builds com informacoes de debug
8. **Checksums** SHA-256 para verificacao de integridade
9. **Code signing** opcional com GPG
10. **RPATH seguro** com `$ORIGIN`
11. **Instalacao com permissoes** controladas
12. **Targets de verificacao** para auditoria de seguranca

---

## 15. Exercicios

### Exercicio 1: Analise de Binarios Existentes

Escolha tres binarios do seu sistema (como `/usr/bin/ls`, `/usr/bin/curl`, `/usr/bin/ssh`) e analise as protecoes de cada um usando `readelf` e `checksec`.

Para cada binario, responda:

- Qual nivel de RELRO esta ativo?
- Stack canaries estao habilitados?
- O binario e PIE?
- NX esta habilitado?
- O binario esta stripado?

```
# Comandos uteis para comecar:
readelf -l /usr/bin/ls | grep GNU_RELRO
readelf -d /usr/bin/ls | grep BIND_NOW
readelf -s /usr/bin/ls | wc -l
readelf -h /usr/bin/ls | grep Type
```

### Exercicio 2: Implemente Full RELRO

Dado o seguinte CMakeLists.txt minimo:

```cmake
cmake_minimum_required(VERSION 3.20)
project(SimpleApp LANGUAGES C)
add_executable(app main.c)
```

Modifique-o para incluir Full RELRO e verifique que a protecao esta ativa no binario resultante. Inclua um comando `add_custom_target` que mostre o resultado da verificacao.

### Exercicio 3: Build Reproduzivel

Implemente um script de build que:

- Use `SOURCE_DATE_EPOCH` baseado no ultimo commit do git
- Defina `LANG` e `LC_ALL` para `en_US.UTF-8`
- Execute o build duas vezes
- Compare os binarios resultantes usando `sha256sum`
- Documente se a build e reproduzivel ou nao e por que

### Exercicio 4: RPATH Seguro

Crie um projeto com:

- Uma biblioteca compartilhada (`libmylib.so`)
- Um executavel que linka contra essa biblioteca
- RPATH configurado para usar `$ORIGIN/../lib`
- Verificacao de que o RPATH esta correto no binario instalado

### Exercicio 5: Hardening Completo e Verificacao

Crie um CMakeLists.txt que:

- Implemente TODAS as protecoes discutidas neste capitulo
- Inclua um target `verify-harden` que verifique cada protecao
- Inclua um target `security-audit` que gere um relatorio completo
- O build deve funcionar tanto para Debug quanto para Release

### Exercicio 6: Code Signing

Configure seu projeto para assinar o binario resultante com GPG e inclua:

- Um target para gerar a assinatura
- Um target para verificar a assinatura
- Documentacao de como um usuario final deve verificar o binario

### Exercicio 7: Binary Diffing

Apos implementar o Exercicio 5:

1. Faca uma primeira build e salve o checksum
2. Modifique uma linha de codigo fonte
3. Faca uma segunda build e salve o checksum
4. Use `diff` para comparar os dois binarios
5. Documente quantos bytes mudaram e por que

---

## 16. Referencias

### Documentacao Oficial

- **CMake Documentation**: https://cmake.org/cmake/help/latest/
- **GNU ld Manual — Options**: https://sourceware.org/binutils/docs/ld/
- **GCC Manual — Security Options**: https://gcc.gnu.org/onlinedocs/gcc/Security.html
- **Linux Programmer's Manual — ld.so**: `man ld.so`
- **ELF Specification**: https://refspecs.linuxfoundation.org/elf/elf.pdf

### Artigos e Papers

- **"Smashing the Stack for Fun and Profit"** — Aleph One (1996). Paper classico sobre buffer overflows e stack smashing.
- **"Advances in Stack Smashing Protection"** — Phrack (2004). Evolucao das stack canaries e tecnicas de bypass.
- **"How a Buffer Overflow Vulnerability Becomes an Exploit"** — OpenBSD documentation. Documentacao detalhada sobre o processo de exploitação.
- **"The ELF Format"** — Ulrich Drepper. Paper sobre o formato ELF e como o linker funciona internamente.
- **"Practical Binary Analysis"** — Dennis Andriesse. Livro completo sobre analise de binarios ELF.
- **"Hacking: The Art of Exploitation"** — Jon Erickson. Fundamentos de exploitação e protecao.

### Ferramentas

- **checksec**: https://github.com/slimm609/checksec.sh — Verificacao de protecoes de binarios
- **readelf**: https://man7.org/linux/man-pages/man1/readelf.1.html — Analise de ELF
- **objdump**: https://man7.org/linux/man-pages/man1/objdump.1.html — Desassembly e analise
- **patchelf**: https://github.com/NixOS/patchelf — Modificacao de RPATH e interpreter
- **cosign**: https://github.com/sigstore/cosign — Assinatura com Sigstore
- **syft**: https://github.com/anchore/syft — Geracao de SBOM
- **radiff2**: https://github.com/radareorg/radare2 — Binary diffing
- **diffoscope**: https://diffoscope.org/ — Comparacao profunda de binarios
- **binwalk**: https://github.com/ReFirmLabs/binwalk — Analise de binarios e firmware
- **radare2**: https://rada.re/ — Framework de analise de binarios

### Normas e Padroes

- **CWE-121**: Stack-based Buffer Overflow — https://cwe.mitre.org/data/definitions/121.html
- **CWE-134**: Use of Externally-Controlled Format String — https://cwe.mitre.org/data/definitions/134.html
- **CWE-252**: Unchecked Return Value — https://cwe.mitre.org/data/definitions/252.html
- **CWE-426**: Untrusted Search Path — https://cwe.mitre.org/data/definitions/426.html
- **CWE-693**: Protection Mechanism Failure — https://cwe.mitre.org/data/definitions/693.html

### CVEs Relacionadas

| CVE | Descricao | Relevancia |
|-----|-----------|------------|
| CVE-2021-4034 | PwnKit (polkit) | Stack overflow sem canary |
| CVE-2021-3156 | Baron Samedit (sudo) | Heap overflow em parsing |
| CVE-2016-6210 | OpenSSH user enumeration | Information disclosure |
| CVE-2014-6271 | Shellshock (bash) | Code injection via env |
| CVE-2017-1000364 | Stack Clash (Linux kernel) | Stack clash attack |
---

*[Capítulo anterior: 05 — Sanitizers Debug](05-sanitizers-debug.md)*
*[Próximo capítulo: 07 — Analise Estatica](07-analise-estatica.md)*
