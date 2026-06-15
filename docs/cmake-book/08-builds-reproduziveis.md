---
layout: default
title: "08-builds-reproduziveis"
---

# Capitulo 08 — Builds Reproduziveis

> *"Se voce nao pode reproduzir um build, voce nao pode confiar nele."*

---

## Indice

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Por que builds reproduziveis importam](#2-por-que-builds-reproduziveis-importam)
3. [Determinismo: timestamps, file ordering, randomness](#3-determinismo-timestamps-file-ordering-randomness)
4. [CMAKE_SOURCE_DATE_EPOCH](#4-cmake_source_date_epoch)
5. [SOURCE_DATE_EPOCH e arquivos](#5-source_date_epoch-e-arquivos)
6. [Docker para builds reproduziveis](#6-docker-para-builds-reproduziveis)
7. [Nix/Guix: package managers funcionais](#7-nixguix-package-managers-funcionais)
8. [Hash verification de artifacts](#8-hash-verification-de-artifacts)
9. [Reproducible Builds organization](#9-reproducible-builds-organization)
10. [Diffoscope para verificacao](#10-diffoscope-para-verificacao)
11. [CI/CD com builds reproduziveis](#11-cicd-com-builds-reproduziveis)
12. [Caso: Debian builds reproduziveis](#12-caso-debian-builds-reproduziveis)
13. [Exemplo: CMakeLists.txt deterministico](#13-exemplo-cmakeliststxt-deterministico)
14. [Exercicios](#14-exercicios)
15. [Referencias](#15-referencias)

---

## 1. Objetivos de Aprendizado

Apos completar este capitulo, voce sera capaz de:

- Compreender o que torna um build "reproduziveis" e por que isso e fundamental para seguranca
- Identificar todas as fontes de nao-determinismo em um pipeline de build
- Configurar CMAKE_SOURCE_DATE_EPOCH e variavel SOURCE_DATE_EPOCH para timestamps determinísticos
- Eliminar nao-determinismo de file ordering em builds CMake
- Usar Docker para criar ambientes de build isolados e reproduziveis
- Entender como Nix e Guix fornecem builds funcionais e reproduziveis
- Implementar hash verification de artifacts binarios
- Utilizar Diffoscope para comparar binarios e identificar diferencas
- Integrar builds reproduziveis em pipelines CI/CD
- Estudar o caso real do Debian como referencia em builds reproduziveis
- Criar um CMakeLists.txt completamente deterministico

---

## 2. Por que builds reproduziveis importam

### 2.1 Definicao de builds reproduziveis

Um build e considerado reproduziveis quando, dado o mesmo codigo-fonte, as mesmas dependencias e as mesmas configuracoes de build, o resultado binario e identicobit a bit (byte a byte). Isso significa que dois builds feitos em maquinas diferentes, em momentos diferentes, devem produzir exatamente o mesmo executavel.

Essa propriedade e conhecida em ingles como "reproducible builds" e e um dos pilares fundamentais da cadeia de suprimentos (supply chain) segura.

### 2.2 O problema do nao-determinismo

Quando um build nao e reproduzivel, cada compilacao gera um binario diferente. Isso cria varios problemas criticos:

**Verificacao de integridade impossivel**: Se voce distribui um binario e um usuario quer verificar que ele corresponde ao codigo-fonte, um binario nao-reproduzivel torna isso impossivel. O usuario precisaria confiar cegamente no binario distribuido.

**Auditoria comprometida**: Em ambientes regulados, auditorias frequentemente verificam se o binario em producao corresponde ao codigo-fonte revisado. Sem reproduzibilidade, essa verificacao e viavel apenas teoricamente.

**Supply chain attacks**: O ataque mais perigoso e quando um invasor injeta codigo malicioso em um binario distribuido, sem alterar o codigo-fonte publicado. Builds reproduziveis tornam esse tipo de ataque detectavel.

**Revisao de codigo sem garantia**: Mesmo que voce revise todo o codigo-fonte cuidadosamente, se o build nao e reproduzivel, o binario pode conter algo completamente diferente.

### 2.3 Casos reais

**CVE-2024-3094 — XZ Utils backdoor**: Este ataque famoso explodiu em marco de 2024. O maintainer do XZ Utils foi comprometido por um atacante que gradualmente ganhou confianca e injetou codigo malicioso nos scripts de build. Um projeto com builds reproduziveis teria detectado que os binarios distribuidos nao correspondiam ao codigo-fonte publicado.

**Ataques a binarios Linux**: Durante anos, distribuicoes Linux lutaram contra binarios nao-reproduziveis em seus repositorios. Ate mesmo componentes criticos como o GCC geravam binarios diferentes a cada compilacao, impossibilitando verificacao independente.

**Compiladores maliciosos**: O famoso paper "Trusting Trust" de Ken Thompson demonstra como um compilador comprometido pode injetar backdoors em qualquer programa que compile, mesmo que o codigo-fonte do programa seja limpo. Builds reproduziveis atacam esse problema ao permitir compilacao em cadeia (bootstrapping).

### 2.4 Beneficios concretos

| Beneficio | Descricao |
|-----------|-----------|
| Verificacao de integridade | Hash do binario pode ser verificado contra o build de referencia |
| Deteccao de adulteracao | Qualquer modificacao maliciosa altera o hash final |
| Auditoria independente | Qualquer pessoa pode reproduzir o build e comparar |
| Confianca na distribuicao | Usuarios podem confirmar que o binario vem do codigo-fonte |
| Compliance regulatorio | Atende requisitos de normas como NIST, ISO 27001 |
| Bug bounty efetivo | Bounty hunters podem reproduzir o build para isolar regressoes |
| Cross-compilation verificavel | Builds para arquiteturas diferentes podem ser verificados |

### 2.5 Niveis de reproduzibilidade

Nem todos os projetos precisam do mesmo nivel de reproduzibilidade:

**Nivel 1 — Build identico**: O binario final e identicobit a bit. Este e o nivel mais alto e necessario para verificacao critica.

**Nivel 2 — Build funcional**: O binario produzido e funcionalmente equivalente, embora possa ter diferencas em metadados (timestamps, padroes de alinhamento). Util para testes de regressao.

**Nivel 3 — Build verificavel**: E possivel verificar que um binario foi construido a partir de um determinado commit, mesmo que o build original nao seja perfeitamente reproduzivel. Util para auditoria basica.

---

## 3. Determinismo: timestamps, file ordering, randomness

### 3.1 Fontes de nao-determinismo

O nao-determinismo em builds pode vir de muitas fontes. Entender todas elas e o primeiro passo para elimina-las.

#### 3.1.1 Timestamps

Muitos compiladores e ferramentas de build incorporam timestamps nos binarios. O GCC, por exemplo, pode gravar o timestamp de compilacao na secao `.comment` do ELF. O `ar` (archiver) incorpora timestamps dos arquivos. O `ld` (linker) pode usar timestamps para resolver ordem de arquivo.

Exemplo de timestamp indesejado no ELF:

```bash
$ readelf -p .comment meu_programa
[ 1]  GCC: (Ubuntu 12.3.0-1ubuntu1~22.04) 12.3.0
# O timestamp real pode aparecer em outros campos
```

```bash
$ strings meu_programa | grep -i "gcc\|date\|time"
GCC: (Ubuntu 12.3.0) 12.3.0
Tue Jun 15 14:30:00 UTC 2026
# Este timestamp torna o binario unico
```

#### 3.1.2 File ordering

O sistemas de arquivos retornam os arquivos em uma ordem que depende da implementacao interna. O `find`, `ls` e funcoes similares podem retornar arquivos em ordens diferentes dependendo do filesystem (ext4, btrfs, xfs, etc.) e do estado do diretorio.

No CMake, isso pode afetar:

- A ordem em que arquivos sao processados pelo `file(GLOB)`
- A ordem em que sources sao adicionados a targets
- A ordem de processamento de subdiretorios

```cmake
# ESTE COMANDO E NAO-DETERMINISTICO
file(GLOB SOURCES "src/*.cpp")
add_executable(myapp ${SOURCES})
# A ordem dos arquivos depende do filesystem
```

```cmake
# ESTE E DETERMINISTICO
file(GLOB SOURCES CONFIGURE_DEPENDS "src/*.cpp")
list(SORT SOURCES)
add_executable(myapp ${SOURCES})
# list(SORT) garante ordem consistente
```

#### 3.1.3 Randomness

Varias ferramentas podem incorporar elementos aleatorios:

**ASLR (Address Space Layout Randomization)**: Embora ASLR seja importante para seguranca, ele impede que binarios sejam reproduziveis quando compilados com PIE (Position Independent Executable). A solucao e compilar com `-fPIE` mas sem o ASLR no momento da verificacao do build.

**Canary values**: Alguns compiladores geram valores aleatorios para stack canaries. O GCC usa `__stack_chk_fail` com um valor que e gerado na inicializacao.

**Random seed in link-time optimization**: LTO pode usar seeds aleatorios para heuristics de otimizacao.

**UUIDs em binarios**: Em sistemas Windows, os UUIDs de debug info podem ser aleatorios.

#### 3.1.4 Locale e configuracao regional

O locale do sistema afeta a formatacao de numeros, datas e strings. Ferramentas de build que usam locale podem gerar resultados diferentes em sistemas com configuracoes regionais distintas.

```bash
# Com locale C, o separador de decimal e ponto
LC_ALL=C date +%s  # Formato padrao

# Com locale pt_BR, pode haver diferencas
LC_ALL=pt_BR.UTF-8 date
```

No CMake:

```cmake
# Forcar locale previsivel
set(LANG "C")
set(LC_ALL "C")
```

#### 3.1.5 Ambiente de compilacao

Variaveis de ambiente afetam o build:

- `CFLAGS`, `CXXFLAGS`, `LDFLAGS` podem conter flags diferentes
- `PATH` determina qual versao de ferramentas e usada
- `TMPDIR` afeta localizacao de arquivos temporarios
- `HOME` influencia configuracoes de ferramentas como gcc specs

### 3.2 Estrategias para eliminacao de nao-determinismo

#### 3.2.1 Fixar timestamps

A variavel `SOURCE_DATE_EPOCH` (padrao definido pelo projeto Reproducible Builds) define um timestamp fixo para ser usado por ferramentas que suportam:

```bash
# Usar o timestamp do ultimo commit do git
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)

# Ou usar um timestamp fixo especifico
export SOURCE_DATE_EPOCH=1718438400  # 15/06/2024 00:00:00 UTC
```

#### 3.2.2 Fixar ordem de arquivos

Sempre ordenar listas de arquivos explicitamente:

```cmake
# Padrao deterministico para file(GLOB)
file(GLOB _temp_sources CONFIGURE_DEPENDS "src/*.cpp")
list(SORT _temp_sources)
set(SOURCES ${_temp_sources})
```

```bash
# No shell, usar find com sort
find src/ -name '*.cpp' -type f | sort > sources.txt
```

#### 3.2.3 Eliminar randomness

```cmake
# Compilar sem ASLR para verificacao de build
# (nao para producao!)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Desabilitar canary para build verificavel (opcional)
# ⚠️ APENAS para verificacao, nao para producao!
# add_compile_options(-fno-stack-protector)
```

#### 3.2.4 Fixar locale

```cmake
# No inicio do CMakeLists.txt
set(LANG "C")
set(LC_ALL "C")
```

```bash
# No shell
export LANG=C
export LC_ALL=C
```

### 3.3 Checklist de determinismo

| Fonte | Impacto | Solucao |
|-------|---------|---------|
| Timestamps em ELF | Alto | SOURCE_DATE_EPOCH |
| Timestamps no ar (archiver) | Alto | SOURCE_DATE_EPOCH |
| File ordering no GLOB | Alto | list(SORT) |
| File ordering no find | Medio | pipe para sort |
| Locale | Medio | Fixar LANG=LC_ALL=C |
| ASLR/PIE | Baixo | Desabilitar para verificacao |
| Canary aleatorio | Baixo | Gerar seed fixa |
| Path absoluto | Alto | Usar caminhos relativos |
| Temp dir | Medio | Fixar TMPDIR |

---

## 4. CMAKE_SOURCE_DATE_EPOCH

### 4.1 O que e CMAKE_SOURCE_DATE_EPOCH

A variavel `CMAKE_SOURCE_DATE_EPOCH` e uma propriedade do CMake (disponivel desde CMake 3.8) que define um timestamp fixo para ser usado em todos os binarios gerados. Quando definida, o CMake:

- Define `SOURCE_DATE_EPOCH` automaticamente para ferramentas externas
- Grava o timestamp nos binarios gerados
- Afeta o archiver (ar/ranlib)
- Afeta o linker quando suportado
- Afeta arquivos gerados pelo CMake (build directories, etc.)

### 4.2 Sintaxe e uso

```cmake
# Definir no inicio do CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(MyProject VERSION 1.0 LANGUAGES C CXX)

# Definir SOURCE_DATE_EPOCH
# 1 de janeiro de 2024, 00:00:00 UTC
set(CMAKE_SOURCE_DATE_EPOCH 1704067200)

# Definir via command-line (alternativa)
# cmake -DCMAKE_SOURCE_DATE_EPOCH=1704067200 ..
```

### 4.3 Usando timestamp do Git

O timestamp mais significativo para builds reproduziveis e geralmente o do ultimo commit:

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject VERSION 1.0 LANGUAGES C CXX)

# Obter timestamp do ultimo commit do Git
execute_process(
    COMMAND git log -1 --format=%ct
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_COMMIT_TIMESTAMP
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)

# Se Git nao estiver disponivel, usar valor fixo
if(NOT GIT_COMMIT_TIMESTAMP)
    set(GIT_COMMIT_TIMESTAMP 1704067200)
endif()

set(CMAKE_SOURCE_DATE_EPOCH ${GIT_COMMIT_TIMESTAMP})

message(STATUS "Build timestamp: ${CMAKE_SOURCE_DATE_EPOCH}")
```

### 4.4 Como ferramentas reagem ao SOURCE_DATE_EPOCH

O CMake define a variavel de ambiente `SOURCE_DATE_EPOCH` para processos externos. Isso afeta:

**GCC/Clang**: Gravam o timestamp no ELF usando o valor de `SOURCE_DATE_EPOCH`:

```bash
# Sem SOURCE_DATE_EPOCH
$ gcc -o prog prog.c
$ readelf -p .comment prog
[ 1]  GCC: (Ubuntu 12.3.0) 12.3.0

# Com SOURCE_DATE_EPOCH
$ SOURCE_DATE_EPOCH=1704067200 gcc -o prog prog.c
$ readelf -p .comment prog
[ 1]  GCC: (Ubuntu 12.3.0) 12.3.0
# O timestamp interno e fixo
```

**GNU ar/ranlib**: O archiver grava timestamps dos membros:

```bash
# Sem SOURCE_DATE_EPOCH
$ ar rcs lib.a file1.o file2.o
$ ar t lib.a  # Mostra timestamps atuais

# Com SOURCE_DATE_EPOCH
$ SOURCE_DATE_EPOCH=1704067200 ar rcs lib.a file1.o file2.o
# Todos os timestamps sao fixados
```

**Doxygen/Asciidoctor**: Ferramentas de documentacao podem usar o valor para datar paginas geradas.

### 4.5 Limitacoes

O `CMAKE_SOURCE_DATE_EPOCH` nao resolve todos os problemas:

- Ferramentas que nao suportam `SOURCE_DATE_EPOCH` continuam nao-deterministicas
- Arquivos gerados pelo CMake (como `CMakeCache.txt`) ainda podem conter timestamps
- Alguns geradores (Visual Studio) podem ter comportamento diferente
- Arquivos de debug info podem conter caminhos absolutos

### 4.6 Exemplo completo

```cmake
cmake_minimum_required(VERSION 3.20)
project(ReproducibleApp VERSION 1.0 LANGUAGES C CXX)

# --- Configuracao de Reproduzibilidade ---

# Usar timestamp do Git
execute_process(
    COMMAND git log -1 --format=%ct
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_TIMESTAMP
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
    RESULT_VARIABLE GIT_RESULT
)

if(GIT_RESULT EQUAL 0 AND GIT_TIMESTAMP)
    set(CMAKE_SOURCE_DATE_EPOCH ${GIT_TIMESTAMP})
    message(STATUS "Reproducible build: SOURCE_DATE_EPOCH=${CMAKE_SOURCE_DATE_EPOCH}")
else()
    message(WARNING "Git not available, using fixed timestamp")
    set(CMAKE_SOURCE_DATE_EPOCH 1704067200)
endif()

# Fixar locale
set(LANG "C")
set(LC_ALL "C")

# --- Configuracao de Build ---

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Flags de seguranca (mantidas)
add_compile_options(-Wall -Wextra -Wpedantic)
add_compile_options(-fstack-protector-strong)
add_compile_options(-D_FORTIFY_SOURCE=2)

# --- Targets ---

add_executable(myapp
    src/main.c
    src/utils.c
)

target_include_directories(myapp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Garantir que file ordering e deterministico
# (nao e necessario quando sources sao listados explicitamente)
```

---

## 5. SOURCE_DATE_EPOCH e arquivos

### 5.1 O padrao SOURCE_DATE_EPOCH

O `SOURCE_DATE_EPOCH` nao e exclusivo do CMake. E um padrao definido pelo projeto Reproducible Builds que pode ser usado por qualquer ferramenta. O padrao e simples:

1. Se a variavel de ambiente `SOURCE_DATE_EPOCH` estiver definida, use seu valor como timestamp
2. O valor e um numero inteiro representando segundos desde epoch (1 de janeiro de 1970, 00:00:00 UTC)
3. Ferramentas devem usar esse valor em vez do timestamp atual

### 5.2 Arquivos afetados por SOURCE_DATE_EPOCH

#### 5.2.1 Arquivos ELF (executaveis e bibliotecas)

O ELF contem varias secoes que podem conter timestamps:

**.comment**: Comentario do compilador, pode conter data

```bash
# Verificar se o binario contem timestamp
$ readelf -p .comment meu_binario
[ 1]  GCC: (Ubuntu 12.3.0) 12.3.0
```

**.note.GNU-stack**: Pode conter metadata de build

**.note.gnu.build-id**: Identificador unico do build, pode ser afetado

#### 5.2.2 Arquivos .a (static libraries)

O archiver (ar) grava timestamps dos membros:

```bash
# Verificar timestamps em uma biblioteca estatica
$ ar t libminha.a
file1.o
file2.o

# Com SOURCE_DATE_EPOCH, todos os timestamps sao fixos
```

#### 5.2.3 Arquivos .o (object files)

Os object files contem timestamps nos headers ELF e nas informacoes de debug

#### 5.2.4 Arquivos Makefile gerados

O proprio Makefile gerado pelo CMake pode conter timestamps

### 5.3 Configuracao para cada ferramenta

#### GCC

```bash
# GCC suporta SOURCE_DATE_EPOCH desde GCC 8
$ SOURCE_DATE_EPOCH=1704067200 gcc -c -o file.o file.c
```

#### Clang

```bash
# Clang suporta SOURCE_DATE_EPOCH desde Clang 5
$ SOURCE_DATE_EPOCH=1704067200 clang -c -o file.o file.c
```

#### GNU ar

```bash
# GNU ar suporta SOURCE_DATE_EPOCH
$ SOURCE_DATE_EPOCH=1704067200 ar rcs lib.a file1.o file2.o
```

#### GNU ld (linker)

```bash
# O linker suporta parcialmente
# Para resultados completos, use CMAKE_SOURCE_DATE_EPOCH
$ SOURCE_DATE_EPOCH=1704067200 ld -o prog file1.o file2.o
```

#### Doxygen

```bash
# Doxygen usa SOURCE_DATE_EPOCH para timestamps em paginas HTML
$ SOURCE_DATE_EPOCH=1704067200 doxygen Doxyfile
```

### 5.4 Verificacao de determinismo apos SOURCE_DATE_EPOCH

Para verificar se um build e deterministico apos configurar SOURCE_DATE_EPOCH:

```bash
#!/bin/bash
# Script de verificacao de determinismo

set -e

REPO_URL="https://github.com/meu-usuario/meu-projeto.git"
COMMIT_HASH="abc123def456"
BUILD_DIR_1="/tmp/build1"
BUILD_DIR_2="/tmp/build2"

echo "=== Verificacao de Build Reproduzivel ==="

# Clone 1
rm -rf "$BUILD_DIR_1"
git clone --depth 1 "$REPO_URL" "$BUILD_DIR_1"
cd "$BUILD_DIR_1"
git checkout "$COMMIT_HASH"
cmake -B build -DCMAKE_SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
cmake --build build
cp build/meu_programa /tmp/prog1

# Clone 2
rm -rf "$BUILD_DIR_2"
git clone --depth 1 "$REPO_URL" "$BUILD_DIR_2"
cd "$BUILD_DIR_2"
git checkout "$COMMIT_HASH"
cmake -B build -DCMAKE_SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
cmake --build build
cp build/meu_programa /tmp/prog2

# Comparar
echo "Comparando binarios..."
if cmp -s /tmp/prog1 /tmp/prog2; then
    echo "SUCESSO: Build e reproduzivel!"
    echo "Hash: $(sha256sum /tmp/prog1)"
else
    echo "FALHA: Build NAO e reproduzivel!"
    diff <(xxd /tmp/prog1) <(xxd /tmp/prog2) | head -20
    exit 1
fi
```

### 5.5 Cuidados importantes

**Caminhos absolutos**: Mesmo com SOURCE_DATE_EPOCH, caminhos absolutos podem vazar para binarios:

```cmake
# PROBLEMA: caminho absoluto no binario
target_compile_definitions(myapp PRIVATE
    SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
)

# SOLUCAO: usar caminho relativo ou hash
file(RELATIVE_PATH REL_SOURCE_DIR
    ${CMAKE_BINARY_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}
)
target_compile_definitions(myapp PRIVATE
    SOURCE_DIR="${REL_SOURCE_DIR}"
)
```

**CMakeCache.txt**: O arquivo CMakeCache.txt contem timestamps e caminhos absolutos. Isso e normal e nao afeta os binarios finais, mas impede que o proprio cache seja reproduzivel.

**Arquivos gerados**: Ferramentas que geram codigo (protobuf, flatbuffers, etc.) podem incluir timestamps. Verifique cada gerador individualmente.

---

## 6. Docker para builds reproduziveis

### 6.1 Por que Docker

Docker fornece ambientais de build isolados e consistentes. Ao usar a mesma imagem Docker, voce garante que:

- O mesmo sistema operacional e usado
- As mesmas versoes de ferramentas estao disponiveis
- As mesmas configuracoes de filesystem sao aplicadas
- O mesmo kernel (na medida do possivel) e compartilhado

### 6.2 Imagem Docker basica para builds reproduziveis

```dockerfile
# Dockerfile.reproducible
FROM ubuntu:22.04

# Fixar variaveis de ambiente para determinismo
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Evitar prompts interativos
ENV DEBIAN_FRONTEND=noninteractive

# Instalar ferramentas de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Fixar versoes de ferramentas (importante!)
# GCC 12.3.0-1ubuntu1~22.04
# CMake 3.22.1

# Configurar locale para C (deterministico)
ENV LANG=C
ENV LC_ALL=C

WORKDIR /src
```

### 6.3 Dockerfile avancado com hash pinning

```dockerfile
# Dockerfile.reproducible.pinned
# Pin para hash especifico da imagem base
FROM ubuntu:22.04@sha256:e57d5403f4bd2c4f4a4f3e0a3d2b4e6c3f8f4a4b4c4d4e4f5a5b5c5d5e5f6a6b

ENV LANG=C
ENV LC_ALL=C
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias com versoes fixas
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9ubuntu3 \
    cmake=3.22.1-1ubuntu1.22.04.1 \
    git=1:2.34.1-1ubuntu1.9 \
    pkg-config=0.29.2-1ubuntu3 \
    && rm -rf /var/lib/apt/lists/*

# Desabilitar services que podem introduzir nao-determinismo
RUN rm -f /etc/machine-id

WORKDIR /src
```

### 6.4 Construindo com Docker

```bash
# Construir a imagem
docker build -t reproducible-build -f Dockerfile.reproducible .

# Executar o build
docker run --rm \
    -v $(pwd):/src \
    -e SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) \
    reproducible-build \
    cmake -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build

# Verificar o binario gerado
sha256sum build/meu_programa
```

### 6.5 Multi-stage builds para reproducibilidade

```dockerfile
# Multi-stage para builds reproduziveis
FROM ubuntu:22.04 AS builder

ENV LANG=C
ENV LC_ALL=C
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git

WORKDIR /src
COPY . .

# Configurar SOURCE_DATE_EPOCH
ARG BUILD_EPOCH
ENV SOURCE_DATE_EPOCH=${BUILD_EPOCH}

RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_SOURCE_DATE_EPOCH=${BUILD_EPOCH} \
    && cmake --build build -j$(nproc)

# Stage de verificacao
FROM ubuntu:22.04 AS verifier

ENV LANG=C
ENV LC_ALL=C
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    file binutils coreutils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /src/build/meu_programa /usr/local/bin/

# Verificar que o binario e estatico e funcional
RUN file /usr/local/bin/meu_programa && \
    ldd /usr/local/bin/meu_programa 2>/dev/null || \
    echo "Binario estatico ou dinamicamente ligado"

# Hash final
RUN sha256sum /usr/local/bin/meu_programa > /checksum.txt
```

### 6.6 Docker Compose para builds em paralelo

```yaml
# docker-compose.reproducible.yml
version: '3.8'

services:
  build-ubuntu:
    build:
      context: .
      dockerfile: Dockerfile.reproducible
      args:
        BUILD_EPOCH: "1704067200"
    volumes:
      - .:/src
      - ./output-ubuntu:/output
    command: >
      sh -c "cmake -B build -DCMAKE_BUILD_TYPE=Release &&
             cmake --build build &&
             cp build/meu_programa /output/"

  build-debian:
    image: debian:11
    volumes:
      - .:/src
      - ./output-debian:/output
    environment:
      - LANG=C
      - LC_ALL=C
      - DEBIAN_FRONTEND=noninteractive
      - SOURCE_DATE_EPOCH=1704067200
    command: >
      sh -c "apt-get update &&
             apt-get install -y build-essential cmake &&
             cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_SOURCE_DATE_EPOCH=1704067200 &&
             cmake --build build &&
             cp build/meu_programa /output/"
```

### 6.7 Verificacao cross-platform

```bash
#!/bin/bash
# build-and-verify.sh
# Constroi o mesmo projeto em dois ambientes Docker e compara

set -e

EPOCH=$(git log -1 --format=%ct)
COMMIT=$(git rev-parse HEAD)
HASH_FILE="expected-${COMMIT:0:8}.sha256"

echo "=== Build Reproduzivel ==="
echo "Commit: $COMMIT"
echo "Epoch: $EPOCH"

# Build 1
echo "Construindo ambiente 1..."
docker run --rm \
    -v $(pwd):/src \
    -e SOURCE_DATE_EPOCH=$EPOCH \
    -e LANG=C \
    -e LC_ALL=C \
    ubuntu:22.04 \
    sh -c "apt-get update && apt-get install -y build-essential cmake &&
           cmake -B /tmp/build -DCMAKE_SOURCE_DATE_EPOCH=$EPOCH -DCMAKE_BUILD_TYPE=Release /src &&
           cmake --build /tmp/build &&
           sha256sum /tmp/build/meu_programa" | awk '{print $1}' > /tmp/hash1.txt

# Build 2
echo "Construindo ambiente 2..."
docker run --rm \
    -v $(pwd):/src \
    -e SOURCE_DATE_EPOCH=$EPOCH \
    -e LANG=C \
    -e LC_ALL=C \
    debian:11 \
    sh -c "apt-get update && apt-get install -y build-essential cmake &&
           cmake -B /tmp/build -DCMAKE_SOURCE_DATE_EPOCH=$EPOCH -DCMAKE_BUILD_TYPE=Release /src &&
           cmake --build /tmp/build &&
           sha256sum /tmp/build/meu_programa" | awk '{print $1}' > /tmp/hash2.txt

# Comparar
echo "=== Resultado ==="
HASH1=$(cat /tmp/hash1.txt)
HASH2=$(cat /tmp/hash2.txt)

echo "Hash Build 1: $HASH1"
echo "Hash Build 2: $HASH2"

if [ "$HASH1" = "$HASH2" ]; then
    echo "SUCESSO: Builds sao reproduziveis!"
    echo "$HASH1  $COMMIT" > "$HASH_FILE"
    echo "Hash salvo em $HASH_FILE"
else
    echo "FALHA: Builds NAO sao reproduziveis!"
    echo "Diferenca detectada."
    exit 1
fi
```

---

## 7. Nix/Guix: package managers funcionais

### 7.1 O que sao package managers funcionais

Package managers funcionais como Nix e Guix levam a ideia de builds reproduziveis ao extremo. Em vez de depender do estado do sistema, eles:

- Constroem pacotes em ambientes isolados (sandboxes)
- Cada pacote tem uma declaracao pura do que ele precisa
- Os hashes sao verificados automaticamente
- Os builds sao deterministico por construcao

### 7.2 Nix: builds declarativos

#### 7.2.1 Conceitos basicos

Nix usa um linguagem de declaracao funcional para descrever como construir pacotes. Cada pacote e construido em um sandbox isolado, sem acesso a rede (por padrao) e sem acesso ao filesystem do host.

```nix
# meu-pacote.nix
{ lib, stdenv, fetchurl, cmake, zlib }:

stdenv.mkDerivation rec {
  pname = "meu-pacote";
  version = "1.0.0";

  src = fetchurl {
    url = "https://example.com/meu-pacote-${version}.tar.gz";
    sha256 = "0abc123def456789abcdef0123456789abcdef0123456789abcdef01234567";
  };

  nativeBuildInputs = [ cmake ];
  buildInputs = [ zlib ];

  # Build deterministica por construcao
  # O sandbox impede acesso a rede, filesystem do host, etc.

  meta = with lib; {
    description = "Meu pacote segurao";
    license = licenses.mit;
    maintainers = [ maintainers.meuuser ];
  };
}
```

#### 7.2.2 Construindo com Nix

```bash
# Construir o pacote
nix-build meu-pacote.nix

# Verificar o hash
nix-hash --type sha256 --base32 result/

# O resultado e sempre o mesmo para os mesmos inputs
nix-build meu-pacote.nix  # Mesmo hash sempre
```

#### 7.2.3 Flakes (moderno)

```nix
# flake.nix
{
  description = "Projeto com build reproduzivel";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "meu-projeto";
          version = "1.0.0";
          src = ./.;

          nativeBuildInputs = [ pkgs.cmake ];
          buildInputs = [ pkgs.zlib ];

          # Configuracoes de build reproduzivel
          preConfigure = ''
            export SOURCE_DATE_EPOCH=1704067200
          '';

          # Verificacao pos-build
          postBuild = ''
            sha256sum $out/bin/meu_programa > $out/share/checksum.txt
          '';
        };

        # Shell de desenvolvimento
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.cmake
            pkgs.gcc
            pkgs.zlib
          ];
        };
      }
    );
}
```

#### 7.2.4 Nix para projetos CMake

```nix
# default.nix para projeto CMake
{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenv.mkDerivation {
  pname = "projeto-cmake";
  version = "1.0.0";

  src = pkgs.lib.cleanSource ./.;

  nativeBuildInputs = with pkgs; [
    cmake
    pkg-config
  ];

  buildInputs = with pkgs; [
    zlib
    openssl
  ];

  # CMake flags para build reproduzivel
  cmakeFlags = [
    "-DCMAKE_BUILD_TYPE=Release"
    "-DCMAKE_SOURCE_DATE_EPOCH=1704067200"
  ];

  # Fixar paths absolutos (importante para Nix)
  preConfigure = ''
    substituteInPlace CMakeLists.txt \
      --replace '"/usr/local"' '"${pkgs.zlib}"'
  '';

  meta = with pkgs.lib; {
    description = "Projeto CMake com build reproduzivel";
    license = licenses.mit;
  };
}
```

### 7.3 GNU Guix: o padrao GNU

#### 7.3.1 Diferencas em relacao ao Nix

Guix usa Scheme (Lisp) em vez de uma linguagem customizada. A filosofia e similar, mas Guix e mais rigorosa sobre software livre.

```scheme
;; meu-pacote.scm
(define-module (meu-pacote)
  #:use-module (gnu packages cmake)
  #:use-module (gnu packages compression)
  #:use-module (guix build-system cmake)
  #:use-module (guix gexp)
  #:use-module (guix packages)
  #:use-module (guix download)
  #:use-module ((guix licenses) #:prefix license:))

(define-public meu-pacote
  (package
    (name "meu-pacote")
    (version "1.0.0")
    (source (origin
              (method url-fetch)
              (uri (string-append "https://example.com/meu-pacote-"
                                  version ".tar.gz"))
              (sha256
               (base32
                "0abc123def456789abcdef0123456789abcdef0123456789abcdef01234567"))))
    (build-system cmake-build-system)
    (inputs `(("zlib" ,zlib)))
    (native-inputs `(("cmake" ,cmake)))
    (home-page "https://example.com")
    (synopsis "Meu pacote segurao")
    (description "Um pacote com build reproduzivel.")
    (license license:mit)))
```

### 7.4 Comparacao Nix vs Guix vs Docker

| Caracteristica | Nix | Guix | Docker |
|---------------|-----|------|--------|
| Linguagem | Nix | Scheme | Dockerfile |
| Isolamento | Sandbox | Sandbox | Container |
| Determinismo | Forte | Forte | Medio |
| Reproduzibilidade | Automatica | Automatica | Manual |
| Curva de aprendizado | Alta | Alta | Baixa |
| Comunidade | Grande | Pequena | Muito grande |
| Software livre | Flexivel | Rigoroso | Flexivel |
| Suporte a CMake | Excelente | Excelente | Bom |

### 7.5 Integrao CMake + Nix

```cmake
# CMakeLists.txt com suporte a Nix
cmake_minimum_required(VERSION 3.20)
project(ProjetoNix VERSION 1.0 LANGUAGES C CXX)

# Detectar se esta rodando dentro do Nix
if(DEFINED ENV{NIX_CC})
    message(STATUS "Building inside Nix environment")
    # Nix ja fornece paths via variaveis de ambiente
else()
    message(STATUS "Building outside Nix")
endif()

# Configuracoes de build reproduzivel
set(CMAKE_SOURCE_DATE_EPOCH 1704067200)

# Fixar locale
set(LANG "C")
set(LC_ALL "C")

# Targets
add_executable(myapp src/main.c)
```

---

## 8. Hash verification de artifacts

### 8.1 Por que verificar hashes

A verificacao de hash e o mecanismo fundamental para confirmar que um artifact binario e o que deveria ser. Se voce tem o hash esperado (calculated de um build reproduzivel), qualquer adulteracao sera detectada.

### 8.2 Algoritmos de hash recomendados

| Algoritmo | Tamanho | Recomendacao |
|-----------|---------|--------------|
| SHA-256 | 256 bits | Recomendado para a maioria dos casos |
| SHA-512 | 512 bits | Para alta seguranca |
| SHA-3 | 256+ bits | Alternativa moderna |
| BLAKE2b | 256+ bits | Mais rapido que SHA-3 |
| MD5 | 128 bits | NAO recomenda — vulneravel a colisoes |
| SHA-1 | 160 bits | NAO recomenda — vulneravel a colisoes |

### 8.3 Gerando hashes com CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(HashVerification VERSION 1.0 LANGUAGES C CXX)

# Compilar o programa
add_executable(meuprograma src/main.c)

# Gerar hash apos build
add_custom_command(TARGET meuprograma POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E sha256sum
        $<TARGET_FILE:meuprograma>
        > ${CMAKE_BINARY_DIR}/meuprograma.sha256
    COMMENT "Generating SHA-256 hash"
)
```

### 8.4 Script de verificacao de hash

```bash
#!/bin/bash
# verify-hash.sh
# Verifica um artifact contra o hash esperado

set -e

EXPECTED_HASH_FILE="${1:-checksum.sha256}"
ARTIFACT="${2:-build/meu_programa}"

if [ ! -f "$EXPECTED_HASH_FILE" ]; then
    echo "ERRO: Arquivo de hash nao encontrado: $EXPECTED_HASH_FILE"
    exit 1
fi

if [ ! -f "$ARTIFACT" ]; then
    echo "ERRO: Artifact nao encontrado: $ARTIFACT"
    exit 1
end

EXPECTED_HASH=$(cut -d' ' -f1 "$EXPECTED_HASH_FILE")
ACTUAL_HASH=$(sha256sum "$ARTIFACT" | cut -d' ' -f1)

echo "Hash esperado: $EXPECTED_HASH"
echo "Hash atual:    $ACTUAL_HASH"

if [ "$EXPECTED_HASH" = "$ACTUAL_HASH" ]; then
    echo "VERIFICACAO OK: Hash conferem!"
    exit 0
else
    echo "FALHA: Hash NAO conferem!"
    echo "O artifact pode ter sido adulterado."
    exit 1
fi
```

### 8.5 Gerenciamento de hashes em projeto

```
meu-projeto/
├── CMakeLists.txt
├── src/
│   └── main.c
├── checksums/
│   ├── v1.0.0-linux-x86_64.sha256
│   ├── v1.0.0-linux-arm64.sha256
│   ├── v1.0.0-windows-x86_64.sha256
│   └── v1.0.0-macos-x86_64.sha256
└── .github/
    └── workflows/
        └── build.yml
```

### 8.6 Verificacao multiplataforma

```bash
#!/bin/bash
# verify-all-platforms.sh
# Verifica hashes para todas as plataformas

VERSION="1.0.0"
PLATFORMS=("linux-x86_64" "linux-arm64" "windows-x86_64" "macos-x86_64")

for platform in "${PLATFORMS[@]}"; do
    echo "=== Verificando $platform ==="

    HASH_FILE="checksums/v${VERSION}-${platform}.sha256"
    ARTIFACT="releases/v${VERSION}/meu_programa-${platform}"

    if [ -f "$HASH_FILE" ] && [ -f "$ARTIFACT" ]; then
        bash verify-hash.sh "$HASH_FILE" "$ARTIFACT"
    else
        echo "Arquivos nao encontrados para $platform"
    fi
done
```

### 8.7 Assinatura digital de artifacts

Hash verification e o primeiro passo. Para seguranca completa, use assinatura digital:

```bash
# Gerar chave de assinatura
gpg --full-generate-key
gpg --export --armor "meu@email.com" > pubkey.asc

# Assinar o hash
gpg --armor --detach-sign checksums/v1.0.0-linux-x86_64.sha256

# Verificar assinatura
gpg --verify checksums/v1.0.0-linux-x86_64.sha256.asc \
            checksums/v1.0.0-linux-x86_64.sha256
```

### 8.8 Sigstore: assinatura moderna

```bash
# Instalar cosign
go install github.com/sigstore/cosign/v2/cmd/cosign@latest

# Assinar o artifact
cosign sign-blob --key cosign.key meu_programa > meu_programa.sig

# Verificar
cosign verify-blob --key cosign.pub \
    --signature meu_programa.sig \
    meu_programa
```

### 8.9 Integracao com CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(SignedBuild VERSION 1.0 LANGUAGES C CXX)

set(CMAKE_SOURCE_DATE_EPOCH 1704067200)

add_executable(meuprograma src/main.c)

# Gerar hash
find_program(SHA256SUM_EXECUTABLE sha256sum)
if(SHA256SUM_EXECUTABLE)
    add_custom_command(TARGET meuprograma POST_BUILD
        COMMAND ${SHA256SUM_EXECUTABLE}
            $<TARGET_FILE:meuprograma>
            > ${CMAKE_BINARY_DIR}/meuprograma-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}.sha256
        COMMENT "Generating artifact hash"
    )
endif()

# Gerar assinatura (se cosign estiver disponivel)
find_program(COSIGN_EXECUTABLE cosign)
if(COSIGN_EXECUTABLE AND DEFINED COSIGN_KEY)
    add_custom_command(TARGET meuprograma POST_BUILD
        COMMAND ${COSIGN_EXECUTABLE} sign-blob
            --key ${COSIGN_KEY}
            --output-signature ${CMAKE_BINARY_DIR}/meuprograma.sig
            $<TARGET_FILE:meuprograma>
        COMMENT "Signing artifact"
    )
endif()
```

---

## 9. Reproducible Builds organization

### 9.1 Historia e missao

A organizacao Reproducible Builds (https://reproducible-builds.org) e uma iniciativa global que visa tornar todos os softwares livremente disponiveis verificaveis. Fundada em 2016, ela:

- Define padroes como `SOURCE_DATE_EPOCH`
- Mantem listas de ferramentas que suportam builds reproduziveis
- Coordena esforcos entre distribuicoes Linux
- Fornece ferramentas de verificacao como `reprotest`
- Organiza conferencias e工作组

### 9.2 Padroes definidos

#### SOURCE_DATE_EPOCH

O padrao mais importante. Define:

1. Variavel de ambiente `SOURCE_DATE_EPOCH` em segundos desde epoch
2. Ferramentas devem usar esse valor em vez de timestamps atuais
3. Documentacao detalhada de como cada ferramenta deve reagir

#### Deterministic output

O padrao de saida deterministica, que cobre:

- Timestamps em arquivos
- Ordem de processamento
- Nao-inclusao de informacao do host
- Formatacao consistente

### 9.3 Status de suporte

A organizacao mantem uma tabela atualizada de suporte:

| Ferramenta | Status | Notas |
|-----------|--------|-------|
| GCC | Completo | Desde GCC 8 |
| Clang | Completo | Desde Clang 5 |
| GNU ar | Completo | Suporta SOURCE_DATE_EPOCH |
| CMake | Parcial | CMAKE_SOURCE_DATE_EPOCH |
| Meson | Parcial | -Dsource_date_epoch |
| Ninja | Parcial | Sem suporte nativo |
| Bazel | Parcial | --workspace_status_command |
| Go | Parcial | GOFLAGS=-trimpath |
| Rust | Parcial | --remap-path-prefix |

### 9.4 Projetos associados

- **Debian**: Lider em builds reproduziveis para pacotes
- **Arch Linux**: Implementacao progressiva
- **Fedora**: Iniciativa em andamento
- **openSUSE**: Suporte ativo
- **Nixpkgs**: Builds reproduziveis por construcao

### 9.5 Como contribuir

```bash
# Clonar o repositorio oficial
git clone https://github.com/reproducible-builds/reproducible-builds.org.git

# Verificar se seu projeto ja esta listado
grep -r "meu-projeto" docs/

# Reportar status de reproduzibilidade
# Seguir o template em docs/source-locations/
```

### 9.6 Certificacao

A organizacao oferece um framework de certificacao:

1. **Nivel 1 — Documentado**: O projeto documenta como construir
2. **Nivel 2 — Verificavel**: Builds podem ser verificados por terceiros
3. **Nivel 3 — Reproduzivel**: Builds sao 100% reproduziveis

---

## 10. Diffoscope para verificacao

### 10.1 O que e Diffoscope

Diffoscope e uma ferramenta poderosa para comparar dois artefatos e encontrar diferencas. Ele nao compara arquivos byte a byte — ele entende a estrutura interna de muitos formatos:

- ELF (executaveis Linux)
- PE/COFF (executaveis Windows)
- DEB/RPM (pacotes)
- ZIP/TAR (arquivos compactados)
- PDF, JPEG, PNG (documentos e imagens)
- E muitos outros formatos

### 10.2 Instalacao

```bash
# Debian/Ubuntu
sudo apt-get install diffoscope

# Arch Linux
sudo pacman -S diffoscope

# macOS
brew install diffoscope

# via pip
pip install diffoscope
```

### 10.3 Uso basico

```bash
# Comparar dois binarios
diffoscope meu_programa_v1 meu_programa_v2

# Comparar dois diretorios
diffoscope dir1/ dir2/

# Comparar pacotes
diffoscope pacote_v1.deb pacote_v2.deb

# Saidas detalhadas
diffoscope --debug meu_programa_v1 meu_programa_v2
```

### 10.4 Analise de diferencas ELF

```bash
# Comparar dois executaveis ELF
$ diffoscope prog_orig prog_build
--- prog_orig
+++ prog_build
@@ -1,5 +1,5 @@
 file prog_orig
  ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked
  interpreter /lib64/ld-linux-x86-64.so.2
- BuildID[sha1]=0x1234567890abcdef1234567890abcdef12345678
+ BuildID[sha1]=0xabcdef1234567890abcdef1234567890abcdef12
  ...
```

### 10.5 Identificando fontes de nao-determinismo

```bash
# Passo 1: Comparar binarios
diffoscope --text prog1 prog2 > diferencas.txt

# Passo 2: Analisar diferencas
# Timestamps diferentes
grep -i "time\|date\|timestamp" diferencas.txt

# Paths absolutos
grep -i "home/\|usr/local\|/tmp" diferencas.txt

# Build IDs diferentes
grep -i "build-id" diferencas.txt
```

### 10.6 Diffoscope em CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(DiffoscopeTest VERSION 1.0 LANGUAGES C CXX)

add_executable(meuprograma src/main.c)

# Comando para comparar com build de referencia
find_program(DIFFOSCOPE_EXECUTABLE diffoscope)
if(DIFFOSCOPE_EXECUTABLE)
    add_custom_target(compare-reference
        COMMAND ${DIFFOSCOPE_EXECUTABLE}
            ${CMAKE_BINARY_DIR}/meuprograma
            ${CMAKE_SOURCE_DIR}/reference/meuprograma
        DEPENDS meuprograma
        COMMENT "Comparing with reference build"
    )
endif()
```

### 10.7 Relatorio HTML

```bash
# Gerar relatorio HTML detalhado
diffoscope --html-output relatorio.html prog1 prog2

# Gerar relatorio para email
diffoscope --text prog1 prog2 | mail -s "Build diff" team@exemplo.com
```

### 10.8 Integracao com CI/CD

```yaml
# GitHub Actions com diffoscope
name: Build Verification
on: [push]

jobs:
  build-and-verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install diffoscope
        run: sudo apt-get install -y diffoscope

      - name: Build
        run: |
          cmake -B build -DCMAKE_SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
          cmake --build build

      - name: Verify reproducibility
        run: |
          # Baixar build de referencia
          wget -O reference.zip https://example.com/reference-build.zip
          unzip reference.zip -d reference

          # Comparar
          diffoscope build/meu_programa reference/meu_programa

      - name: Upload diff
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: build-diff
          path: relatorio.html
```

---

## 11. CI/CD com builds reproduziveis

### 11.1 Integracao em pipelines CI/CD

Builds reproduziveis devem ser o padrao em qualquer pipeline CI/CD. O objetivo e que cada build gerado possa ser verificado independentemente.

### 11.2 GitHub Actions

```yaml
# .github/workflows/reproducible-build.yml
name: Reproducible Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  SOURCE_DATE_EPOCH: ${{ github.event.head_commit.timestamp }}

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Precisa do historico completo para timestamp

      - name: Get commit timestamp
        id: timestamp
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)
          echo "timestamp=$TIMESTAMP" >> $GITHUB_OUTPUT
          echo "Build timestamp: $TIMESTAMP"

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential cmake

      - name: Configure
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_SOURCE_DATE_EPOCH=${{ steps.timestamp.outputs.timestamp }}

      - name: Build
        run: cmake --build build -j$(nproc)

      - name: Generate checksum
        run: |
          cd build
          sha256sum meu_programa > meu_programa.sha256
          cat meu_programa.sha256

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: meu_programa-linux-x86_64
          path: |
            build/meu_programa
            build/meu_programa.sha256

  verify:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: meu_programa-linux-x86_64
          path: artifact

      - name: Checkout
        uses: actions/checkout@v4

      - name: Rebuild from source
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)
          cmake -B build-rebuild \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
          cmake --build build-rebuild -j$(nproc)

      - name: Compare hashes
        run: |
          HASH_ORIGINAL=$(cut -d' ' -f1 artifact/meu_programa.sha256)
          HASH_REBUILD=$(sha256sum build-rebuild/meu_programa | cut -d' ' -f1)

          echo "Hash original:  $HASH_ORIGINAL"
          echo "Hash rebuild:   $HASH_REBUILD"

          if [ "$HASH_ORIGINAL" = "$HASH_REBUILD" ]; then
            echo "Build e reproduzivel!"
          else
            echo "Build NAO e reproduzivel!"
            exit 1
          fi
```

### 11.3 GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - verify

variables:
  SOURCE_DATE_EPOCH: "1704067200"

build:
  stage: build
  image: ubuntu:22.04
  script:
    - apt-get update && apt-get install -y build-essential cmake git
    - TIMESTAMP=$(git log -1 --format=%ct)
    - cmake -B build
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
    - cmake --build build -j$(nproc)
    - cd build && sha256sum meu_programa > meu_programa.sha256
  artifacts:
    paths:
      - build/meu_programa
      - build/meu_programa.sha256

verify:
  stage: verify
  image: ubuntu:22.04
  dependencies:
    - build
  script:
    - apt-get update && apt-get install -y build-essential cmake git
    - TIMESTAMP=$(git log -1 --format=%ct)
    - cmake -B build-verify
        -DCMAKE_BUILD_TYPE=Release
        -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
    - cmake --build build-verify -j$(nproc)
    - HASH_ORIG=$(cut -d' ' -f1 build/meu_programa.sha256)
    - HASH_VERIFY=$(sha256sum build-verify/meu_programa | cut -d' ' -f1)
    - |
      if [ "$HASH_ORIG" = "$HASH_VERIFY" ]; then
        echo "Build reproduzivel verificado!"
      else
        echo "Build NAO reproduzivel!"
        exit 1
      fi
```

### 11.4 Verificacao cross-compilation

```yaml
# .github/workflows/cross-build.yml
name: Cross-compilation Verification

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        include:
          - target: x86_64-linux-gnu
            runner: ubuntu-latest
          - target: aarch64-linux-gnu
            runner: ubuntu-latest
          - target: x86_64-w64-mingw32
            runner: ubuntu-latest

    runs-on: ${{ matrix.runner }}

    steps:
      - uses: actions/checkout@v4

      - name: Install cross-compilation tools
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            build-essential cmake \
            gcc-aarch64-linux-gnu \
            gcc-mingw-w64-x86-64

      - name: Build for ${{ matrix.target }}
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)
          cmake -B build-${{ matrix.target }} \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP \
            -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/${{ matrix.target }}.cmake
          cmake --build build-${{ matrix.target }} -j$(nproc)

      - name: Generate hash
        run: |
          cd build-${{ matrix.target }}
          sha256sum meu_programa > meu_programa-${{ matrix.target }}.sha256

      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: meu_programa-${{ matrix.target }}
          path: |
            build-${{ matrix.target }}/meu_programa
            build-${{ matrix.target }}/meu_programa-${{ matrix.target }}.sha256
```

### 11.5 Pipeline completa

```yaml
# .github/workflows/complete-pipeline.yml
name: Complete Reproducible Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run clang-format
        run: |
          find src/ -name '*.cpp' -o -name '*.c' | xargs clang-format --dry-run --Werror

  build-linux:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
          cmake --build build -j$(nproc)
      - name: Hash
        run: sha256sum build/meu_programa > build/checksum.sha256
      - uses: actions/upload-artifact@v4
        with:
          name: linux-x86_64
          path: build/

  build-windows:
    needs: lint
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: |
          $timestamp = git log -1 --format=%ct
          cmake -B build -G "Visual Studio 17 2022" -A x64 `
            -DCMAKE_BUILD_TYPE=Release `
            -DCMAKE_SOURCE_DATE_EPOCH=$timestamp
          cmake --build build --config Release
      - name: Hash
        run: sha256sum build/Release/meu_programa.exe > build/checksum.sha256
      - uses: actions/upload-artifact@v4
        with:
          name: windows-x86_64
          path: build/

  verify:
    needs: [build-linux, build-windows]
    runs-on: ubuntu-latest
    steps:
      - name: Download all builds
        uses: actions/download-artifact@v4

      - name: Verify hashes
        run: |
          for dir in linux-x86_64 windows-x86_64; do
            echo "=== Verifying $dir ==="
            cd $dir
            if sha256sum -c checksum.sha256; then
              echo "$dir: OK"
            else
              echo "$dir: FAILED"
              exit 1
            fi
            cd ..
          done

      - name: Create release
        if: startsWith(github.ref, 'refs/tags/')
        uses: softprops/action-gh-release@v1
        with:
          files: |
            linux-x86_64/meu_programa
            linux-x86_64/checksum.sha256
            windows-x86_64/meu_programa.exe
            windows-x86_64/checksum.sha256
```

---

## 12. Caso: Debian builds reproduziveis

### 12.1 Historia do Debian

O Debian e a distribuicao Linux que mais avancou em builds reproduziveis. Desde 2016, o projeto Debian tem uma iniciativa dedicada para tornar todos os seus pacotes reproduziveis. Em 2024, mais de 95% dos pacotes do Debian sao reproduziveis.

### 12.2 Desafios do Debian

O Debian enfrenta desafios unicos:

- Mais de 60.000 pacotes
- Multiplos arquiteturas (amd64, arm64, i386, etc.)
- Compiladores diferentes para cada pacote
- Ferramentas de build variadas
- Historico de 30+ anos

### 12.3 Ferramentas do Debian

#### sbuild

O sbuild e a ferramenta oficial do Debian para construir pacotes em ambientes isolados:

```bash
# Configurar sbuild
sudo sbuild-createchroot bookworm /srv/chroot/bookworm

# Construir um pacote
sbuild --arch=amd64 --dist=bookworm meu-pacote_1.0-1.dsc
```

#### reprotest

O reprotest e uma ferramenta que verifica se um build e reproduzivel:

```bash
# Instalar
sudo apt-get install reprotest

# Verificar reproduzibilidade
reprotest --vary=-path,+time,+hostname,+user,+buildpath \
    -- null
```

### 12.4 Como o Debian garante reproduzibilidade

1. **Build path independence**: Os pacotes devem funcionar independentemente do caminho de build
2. **Timestamp removal**: Timestamps sao removidos de pacotes binarios
3. **File ordering**: A ordem de arquivos e controlada
4. **Hostname removal**: O hostname do build nao deve aparecer no pacote
5. **User removal**: O usuario do build nao deve aparecer

### 12.5 Exemplo de pacote Debian reproduzivel

```bash
# estrutura de um pacote reproduzivel
meu-pacote-1.0/
├── debian/
│   ├── control
│   ├── rules
│   ├── changelog
│   ├── copyright
│   └── source/
│       └── format
├── src/
│   └── main.c
└── CMakeLists.txt
```

```makefile
# debian/rules
#!/usr/bin/make -f

export DEB_BUILD_MAINT_OPTIONS = hardening=+all

%:
	dh $@

override_dh_auto_configure:
	dh_auto_configure -- \
		-DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_SOURCE_DATE_EPOCH=$(shell stat -c %Y debian/changelog) \
		-DCMAKE_INSTALL_PREFIX=/usr

override_dh_auto_install:
	dh_auto_install
	# Remover timestamps desnecessarios
	find debian/tmp -name '*.la' -delete
	find debian/tmp -name '*.a' -exec strip --strip-unneeded {} \;
```

### 12.6 Verificacao no Debian

```bash
# Verificar se um pacote do Debian e reproduzivel
# Usando o sistema de build do Debian

# 1. Obter o codigo-fonte
apt-get source meu-pacote

# 2. Construir
dpkg-buildpackage -us -uc

# 3. Baixar o pacote oficial
apt-get download meu-pacote

# 4. Comparar com diffoscope
diffoscope meu-pacote_1.0-1_amd64.deb ../meu-pacote_1.0-1_amd64.deb
```

### 12.7 Resultados e metricas

| Metrica | Valor |
|---------|-------|
| Total de pacotes | ~60.000 |
| Pacotes reproduziveis (2024) | ~95% |
| Iniciativa iniciada | 2016 |
| Meta | 100% ate 2025 |

---

## 13. Exemplo: CMakeLists.txt deterministico

### 13.1 Projeto exemplo completo

Vamos criar um projeto CMake completamente deterministico, aplicando todos os conceitos aprendidos.

```cmake
# CMakeLists.txt - Projeto com build 100% reproduzivel
# Aplica todos os conceitos de determinismo

cmake_minimum_required(VERSION 3.20)
project(ReproducibleApp
    VERSION 1.0.0
    LANGUAGES C CXX
    DESCRIPTION "Aplicacao com build deterministico"
)

# =============================================================================
# SECAO 1: Configuracao de Reproduzibilidade
# =============================================================================

# Fixar locale para determinismo
set(LANG "C")
set(LC_ALL "C")

# Obter timestamp do ultimo commit do Git
execute_process(
    COMMAND git log -1 --format=%ct
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_COMMIT_TIMESTAMP
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
    RESULT_VARIABLE GIT_RESULT
)

if(GIT_RESULT EQUAL 0 AND GIT_COMMIT_TIMESTAMP)
    set(CMAKE_SOURCE_DATE_EPOCH ${GIT_COMMIT_TIMESTAMP})
    message(STATUS "Reproducible build: SOURCE_DATE_EPOCH=${CMAKE_SOURCE_DATE_EPOCH}")
else()
    message(WARNING "Git not available, using fixed timestamp")
    set(CMAKE_SOURCE_DATE_EPOCH 1704067200)
endif()

# =============================================================================
# SECAO 2: Configuracao de Build
# =============================================================================

# Padroes de C/C++
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_EXTENSIONS OFF)

# Flags de compilacao
add_compile_options(
    -Wall
    -Wextra
    -Wpedantic
    -Werror
    -fstack-protector-strong
    -D_FORTIFY_SOURCE=2
    -fno-plt
)

# Flags de ligacao
add_link_options(
    -Wl,-z,relro,-z,now
    -Wl,-z,noexecstack
)

# =============================================================================
# SECAO 3: Targets
# =============================================================================

# Executavel principal
add_executable(reproducible_app
    src/main.c
    src/utils.c
)

# Configuracoes especificas do target
target_include_directories(reproducible_app PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Gerar build ID para verificacao
set_target_properties(reproducible_app PROPERTIES
    ENABLE_EXPORTS ON
    INSTALL_RPATH ""
    BUILD_RPATH ""
)

# =============================================================================
# SECAO 4: Verificacao Pos-Build
# =============================================================================

# Gerar hash apos build
add_custom_command(TARGET reproducible_app POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "=== Build Reproduzivel ==="
    COMMAND ${CMAKE_COMMAND} -E echo "Commit timestamp: ${CMAKE_SOURCE_DATE_EPOCH}"
    COMMAND ${CMAKE_COMMAND} -E sha256sum
        $<TARGET_FILE:reproducible_app>
        > ${CMAKE_BINARY_DIR}/reproducible_app-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}.sha256
    COMMAND cat ${CMAKE_BINARY_DIR}/reproducible_app-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}.sha256
    COMMENT "Generating reproducible build checksum"
)

# =============================================================================
# SECAO 5: Testes
# =============================================================================

enable_testing()

add_executable(reproducible_app_test
    tests/test_main.c
)
target_link_libraries(reproducible_app_test PRIVATE reproducible_app)
add_test(NAME reproducible_test COMMAND reproducible_app_test)
```

### 13.2 Codigo-fonte do projeto

```c
// include/utils.h
#ifndef UTILS_H
#define UTILS_H

int calculate_hash(const char *input, char *output, size_t output_size);
int verify_integrity(const char *filepath);

#endif // UTILS_H
```

```c
// src/utils.c
#include "utils.h"
#include <stdio.h>
#include <string.h>

int calculate_hash(const char *input, char *output, size_t output_size) {
    if (!input || !output || output_size < 65) {
        return -1;
    }

    // Implementacao simplificada para demonstracao
    // Em producao, usar OpenSSL ou similar
    snprintf(output, output_size, "hash_of_%s", input);
    return 0;
}

int verify_integrity(const char *filepath) {
    if (!filepath) {
        return -1;
    }

    FILE *file = fopen(filepath, "rb");
    if (!file) {
        return -1;
    }

    fclose(file);
    return 0;
}
```

```c
// src/main.c
#include <stdio.h>
#include "utils.h"

int main(void) {
    printf("ReproducibleApp v1.0.0\n");
    printf("Build timestamp: %d\n", __DATE__);

    char hash[65];
    if (calculate_hash("test", hash, sizeof(hash)) == 0) {
        printf("Hash: %s\n", hash);
    }

    return 0;
}
```

### 13.3 Script de verificacao

```bash
#!/bin/bash
# verify-build.sh - Verifica se o build e reproduzivel

set -e

echo "=== Verificacao de Build Reproduzivel ==="
echo ""

# Configuracoes
REPO_DIR=$(pwd)
BUILD_DIR_1="/tmp/build1"
BUILD_DIR_2="/tmp/build2"
COMMIT=$(git rev-parse HEAD)
EPOCH=$(git log -1 --format=%ct)

echo "Commit: $COMMIT"
echo "Epoch: $EPOCH"
echo ""

# Funcao para construir
build_project() {
    local build_dir=$1
    rm -rf "$build_dir"
    mkdir -p "$build_dir"

    cd "$build_dir"
    git clone "$REPO_DIR" .
    git checkout "$COMMIT"

    cmake -B _build \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_SOURCE_DATE_EPOCH=$EPOCH

    cmake --build _build -j$(nproc)

    sha256sum _build/reproducible_app > "$build_dir/checksum.sha256"
    cd "$REPO_DIR"
}

# Build 1
echo "Construindo build 1..."
build_project "$BUILD_DIR_1"

# Build 2
echo "Construindo build 2..."
build_project "$BUILD_DIR_2"

# Comparar
echo ""
echo "=== Resultado ==="

HASH1=$(cut -d' ' -f1 "$BUILD_DIR_1/checksum.sha256")
HASH2=$(cut -d' ' -f1 "$BUILD_DIR_2/checksum.sha256")

echo "Hash Build 1: $HASH1"
echo "Hash Build 2: $HASH2"

if [ "$HASH1" = "$HASH2" ]; then
    echo ""
    echo "SUCESSO: Build e reproduzivel!"
    echo "Hash: $HASH1"
    exit 0
else
    echo ""
    echo "FALHA: Build NAO e reproduzivel!"
    echo "Diferenca detectada entre os builds."
    exit 1
fi
```

### 13.4 Estrutura final do projeto

```
ReproducibleApp/
├── CMakeLists.txt
├── include/
│   └── utils.h
├── src/
│   ├── main.c
│   └── utils.c
├── tests/
│   └── test_main.c
├── cmake/
│   └── toolchains/
│       └── aarch64-linux-gnu.cmake
├── scripts/
│   └── verify-build.sh
├── .github/
│   └── workflows/
│       └── reproducible-build.yml
└── README.md
```

### 13.5 Toolchain para cross-compilation

```cmake
# cmake/toolchains/aarch64-linux-gnu.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)

set(CMAKE_FIND_ROOT_PATH /usr/aarch64-linux-gnu)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### 13.6 Workflow de build multiplataforma

```yaml
# .github/workflows/reproducible-build.yml
name: Reproducible Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        include:
          - target: x86_64-linux
            runner: ubuntu-latest
          - target: aarch64-linux
            runner: ubuntu-latest

    runs-on: ${{ matrix.runner }}

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y build-essential cmake
          if [ "${{ matrix.target }}" = "aarch64-linux" ]; then
            sudo apt-get install -y gcc-aarch64-linux-gnu
          fi

      - name: Build
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)
          if [ "${{ matrix.target }}" = "aarch64-linux" ]; then
            cmake -B build \
              -DCMAKE_BUILD_TYPE=Release \
              -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP \
              -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-gnu.cmake
          else
            cmake -B build \
              -DCMAKE_BUILD_TYPE=Release \
              -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
          fi
          cmake --build build -j$(nproc)

      - name: Generate hash
        run: |
          cd build
          sha256sum reproducible_app > reproducible_app-${{ matrix.target }}.sha256

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: reproducible_app-${{ matrix.target }}
          path: |
            build/reproducible_app
            build/reproducible_app-${{ matrix.target }}.sha256

  verify:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Download artifacts
        uses: actions/download-artifact@v4

      - name: Verify reproducibility
        run: |
          TIMESTAMP=$(git log -1 --format=%ct)

          for target in x86_64-linux aarch64-linux; do
            echo "=== Verifying $target ==="

            if [ "$target" = "aarch64-linux" ]; then
              sudo apt-get install -y gcc-aarch64-linux-gnu
              cmake -B build-verify \
                -DCMAKE_BUILD_TYPE=Release \
                -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP \
                -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/aarch64-linux-gnu.cmake
            else
              cmake -B build-verify \
                -DCMAKE_BUILD_TYPE=Release \
                -DCMAKE_SOURCE_DATE_EPOCH=$TIMESTAMP
            fi

            cmake --build build-verify -j$(nproc)

            HASH_ORIGINAL=$(cut -d' ' -f1 reproducible_app-${target}/reproducible_app-${target}.sha256)
            HASH_VERIFY=$(sha256sum build-verify/reproducible_app | cut -d' ' -f1)

            if [ "$HASH_ORIGINAL" = "$HASH_VERIFY" ]; then
              echo "$target: Build reproduzivel!"
            else
              echo "$target: Build NAO reproduzivel!"
              exit 1
            fi
          done
```

---

## 13.5 Estrategias avancadas de determinismo

### 13.5.1 Build path independence

Um dos maiores desafios para builds reproduziveis e garantir que o caminho de build nao afete o resultado. Muitas ferramentas incorporam o caminho absoluto de build nos binarios.

**Problema**: O GCC inclui o caminho absoluto no dwarf debug info:

```bash
$ readelf -p .debug_str meu_programa | grep "/home"
[ 23] /home/usuario/projetos/meu-projeto/src/main.c
# Este caminho aparece no binario
```

**Solucao com CMake**:

```cmake
# Usar caminho relativo para debug info
if(CMAKE_COMPILER_IS_GNUCXX)
    add_compile_options(-fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.)
    add_compile_options(-fdebug-prefix-map=${CMAKE_BINARY_DIR}=build)
endif()

# Para Clang, usar -fdebug-prefix-map tambem
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    add_compile_options(-fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.)
    add_compile_options(-fdebug-prefix-map=${CMAKE_BINARY_DIR}=build)
endif()
```

**Solucao com variavel de ambiente**:

```bash
# Antes de compilar
export BUILD_PREFIX_MAP="${CMAKE_CURRENT_SOURCE_DIR}=/src"
export BUILD_PREFIX_MAP="${BUILD_PREFIX_MAP} ${CMAKE_BINARY_DIR}=/build"

gcc -fdebug-prefix-map="${BUILD_PREFIX_MAP}" -c src/main.c
```

### 13.5.2 Determinismo em bibliotecas compartilhadas

Bibliotecas compartilhadas (`.so`) apresentam desafios unicos:

```cmake
# Configuracao deterministica para shared libraries
add_library(mylib SHARED
    src/lib.c
)

# Fixar SOVERSION para determinismo
set_target_properties(mylib PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Remover runpath absoluto
set_target_properties(mylib PROPERTIES
    INSTALL_RPATH ""
    BUILD_RPATH ""
    SKIP_BUILD_RPATH TRUE
)

# Gerar output com nome previsivel
set_target_properties(mylib PROPERTIES
    OUTPUT_NAME mylib
    PREFIX lib
)
```

### 13.5.3 Determinismo em arquivos de debug

Os arquivos de debug (`.debug`, `-debuginfo`) precisam ser reproduziveis tambem:

```cmake
# Gerar debug info reproduzivel
set(CMAKE_C_FLAGS_DEBUG "-g -fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.")
set(CMAKE_CXX_FLAGS_DEBUG "-g -fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=.")

# Separar debug info de forma deterministica
add_executable(myapp src/main.c)

# Usar objcopy para extrair debug info
add_custom_command(TARGET myapp POST_BUILD
    COMMAND objcopy --only-keep-debug
        $<TARGET_FILE:myapp>
        $<TARGET_FILE:myapp>.debug
    COMMAND objcopy --strip-debug
        $<TARGET_FILE:myapp>
    COMMENT "Extracting debug info"
)
```

### 13.5.4 Determinismo em packages gerados

Quando usando CPack para gerar pacotes, tambem precisamos de determinismo:

```cmake
# CPack configurado para determinismo
set(CPACK_PACKAGE_NAME ${PROJECT_NAME})
set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})

# Fixar timestamps nos pacotes
set(CPACK_DEBIAN_PACKAGE_BUILD_TIMESTAMP ${CMAKE_SOURCE_DATE_EPOCH})

# Usar compression deterministica
set(CPACK_DEBIAN_PACKAGE_COMPRESSIONTYPE "xz")
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)

# Gerar checksums reproduziveis
set(CPACK_DEBIAN_PACKAGE_CONTROL_STRICT_PERMISSION TRUE)

include(CPack)
```

### 13.5.5 Verificacao automatizada de determinismo

```cmake
# CMake module para verificacao de determinismo
# cmake/DeterminismCheck.cmake

function(check_build_determinism target)
    # Verificar se SOURCE_DATE_EPOCH esta definido
    if(NOT CMAKE_SOURCE_DATE_EPOCH)
        message(WARNING "CMAKE_SOURCE_DATE_EPOCH not set - build may not be deterministic")
        return()
    endif()

    # Verificar se locale esta fixado
    if(NOT "$ENV{LANG}" STREQUAL "C")
        message(WARNING "LANG is not C - locale may affect determinism")
    endif()

    # Verificar flags problematicas
    get_target_property(TARGET_COMPILE_OPTIONS ${target} COMPILE_OPTIONS)
    foreach(opt IN LISTS TARGET_COMPILE_OPTIONS)
        if(opt MATCHES "-O[0-3s]")
            message(STATUS "Optimization level detected: ${opt}")
            message(STATUS "  Note: Different optimization levels may affect determinism")
        endif()
    endforeach()

    # Verificar sources
    get_target_property(TARGET_SOURCES ${target} SOURCES)
    foreach(source IN LISTS TARGET_SOURCES)
        if(source MATCHES "\\$\\{.*\\}")
            message(WARNING "Generator expression in sources may affect determinism: ${source}")
        endif()
    endforeach()

    message(STATUS "Determinism check complete for ${target}")
endfunction()
```

---

## 14. Exercicios

### Exercicio 1: Identificacao de nao-determinismo (Basico)

Dado o seguinte CMakeLists.txt, identifique TODAS as fontes de nao-determinismo e proponha correcoes:

```cmake
cmake_minimum_required(VERSION 3.10)
project(MeuProjeto)

file(GLOB SOURCES "src/*.cpp")
add_executable(meuprog ${SOURCES})

target_compile_definitions(meuprog PRIVATE
    BUILD_DIR="${CMAKE_CURRENT_BINARY_DIR}"
    BUILD_TIME="__DATE__ __TIME__"
)
```

**Resolucao esperada**:

1. Falta `list(SORT SOURCES)` apos o `file(GLOB)`
2. `BUILD_DIR` usa caminho absoluto — usar caminho relativo ou remover
3. `BUILD_TIME` usa `__DATE__` e `__TIME__` — remover ou usar `SOURCE_DATE_EPOCH`
4. Falta `CMAKE_SOURCE_DATE_EPOCH`
5. `CMAKE_VERSION` mais antigo (3.10) — atualizar para 3.20+

### Exercicio 2: Configuracao Docker (Intermediario)

Crie um Dockerfile que garanta builds reproduziveis para um projeto CMake, incluindo:

- Imagem base com hash pinning
- Locale fixo
- Ferramentas com versoes documentadas
- Script de verificacao pos-build

**Resolucao esperada**: Dockerfile com FROM ubuntu:22.04@sha256:..., ENV LANG=C, apt-get install com versoes especificas, e comando de verificacao com sha256sum.

### Exercicio 3: Verificacao com Diffoscope (Intermediario)

Voce tem dois binarios `prog_v1` e `prog_v2`. Escreva um script bash que:

1. Execute diffoscope para comparar os dois binarios
2. Extraia as diferencas encontradas
3. Classifique cada diferenca (timestamp, path, build-id, etc.)
4. Gere um relatorio em formato Markdown

**Resolucao esperada**: Script que usa `diffoscope --text` para saida textual, grep para classificar diferencas, e formatacao para Markdown.

### Exercicio 4: Pipeline CI/CD (Avancado)

Projete um pipeline GitHub Actions que:

1. Compile o projeto em tres plataformas (Linux, Windows, macOS)
2. Gere hashes SHA-256 para cada plataforma
3. Verifique que cada build e reproduzivel (recompile e compare)
4. Publique os artifacts com hashes no GitHub Release

**Resolucao esperada**: Workflow com matrix strategy, steps de build/verify/release, e upload de artifacts.

### Exercicio 5: Nix para CMake (Avancado)

Crie um `default.nix` que:

1. Use Nix para construir um projeto CMake
2. Fixe todas as dependencias via Nix
3. Configure SOURCE_DATE_EPOCH
4. Verifique que o build e reproduzivel

**Resolucao esperada**: Arquivo Nix com `stdenv.mkDerivation`, `nativeBuildInputs`, `buildInputs`, `cmakeFlags`, e `postBuild` com verificacao de hash.

### Exercicio 6: Analise completa de determinismo (Avancado)

Dado um projeto CMake existente, execute uma analise completa de determinismo:

1. Documente todas as potenciais fontes de nao-determinismo
2. Implemente correcoes para cada uma
3. Crie um script de verificacao automatizado
4. Documente como outros desenvolvedores podem reproduzir o build

**Resolucao esperada**: Documento com lista de fontes, implementacao no CMakeLists.txt, script de verificacao, e README com instrucoes.

### Exercicio 7: Comparacao de abordagens (Exploratorio)

Compare tres abordagens para builds reproduziveis:

1. Docker + CMake
2. Nix + CMake
3. Guix + CMake

Para cada abordagem, documente:

- Facilidade de implementacao
- Grau de determinismo atingido
- Manutencao necessaria
- Casos de uso ideais

### Exercicio 8: Cross-compilation reproduzivel (Avancado)

Configure um projeto CMake para cross-compilation reproduzivel de x86_64 para ARM64:

1. Crie um toolchain file para aarch64-linux-gnu
2. Configure SOURCE_DATE_EPOCH no toolchain
3. Garanta que os paths de cross-compilation nao vazam para o binario
4. Gere um binario ARM64 reproduzivel e verifique com QEMU

```cmake
# Resolucao: cmake/toolchains/aarch64-linux-gnu.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_AR aarch64-linux-gnu-ar)
set(CMAKE_RANLIB aarch64-linux-gnu-ranlib)
set(CMAKE_STRIP aarch64-linux-gnu-strip)
set(CMAKE_OBJCOPY aarch64-linux-gnu-objcopy)

set(CMAKE_SYSROOT /usr/aarch64-linux-gnu)
set(CMAKE_FIND_ROOT_PATH /usr/aarch64-linux-gnu)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Garantir que paths nao vazem
set(CMAKE_C_FLAGS_INIT "-fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=/src")
set(CMAKE_CXX_FLAGS_INIT "-fdebug-prefix-map=${CMAKE_CURRENT_SOURCE_DIR}=/src")
```

### Exercicio 9: Verificacao de build com reprodutest (Intermediario)

Instale e configure o reprodutest para verificar a reproduzibilidade do seu projeto:

```bash
# Resolucao passo a passo

# 1. Instalar reprodutest
sudo apt-get install reprotest

# 2. Criar script de build
cat > build.sh << 'EOF'
#!/bin/bash
set -e
cmake -B build -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
cmake --build build -j$(nproc)
EOF
chmod +x build.sh

# 3. Executar verificacao
reprotest --vary=-path,+time,+hostname,+user \
    --null . ./build.sh

# 4. Analisar resultados
# O reprodutest compara builds com diferentes variacoes
# Se algum variacao causa diferencas, o build nao e reproduzivel
```

### Exercicio 10: Projeto completo com todas as tecnicas (Expert)

Crie um projeto CMake do zero que demonstre TODAS as tecnicas de builds reproduziveis:

**Requisitos**:

1. Projeto com multiplos targets (executavel, biblioteca estatica, biblioteca compartilhada)
2. SOURCE_DATE_EPOCH configurado com timestamp do Git
3. Locale fixado em C
4. File ordering deterministico
5. Paths absolutos eliminados
6. Docker multi-stage para build reproduzivel
7. Script de verificacao que compara dois builds
8. CI/CD com verificacao automatica
9. Hash verification de todos os artifacts
10. Documentacao completa no README

**Estrutura esperada**:

```
meu-projeto/
├── CMakeLists.txt
├── cmake/
│   ├── modules/
│   │   ├── DeterminismCheck.cmake
│   │   └── HashVerification.cmake
│   └── toolchains/
│       └── aarch64-linux-gnu.cmake
├── include/
│   ├── mylib/
│   │   └── mylib.h
│   └── myexe/
│       └── main.h
├── src/
│   ├── mylib.c
│   └── main.c
├── tests/
│   └── test_mylib.c
├── docker/
│   ├── Dockerfile.reproducible
│   └── docker-compose.reproducible.yml
├── scripts/
│   ├── verify-build.sh
│   └── generate-checksums.sh
├── .github/
│   └── workflows/
│       └── reproducible-build.yml
└── README.md
```

**CMakeLists.txt**:

```cmake
cmake_minimum_required(VERSION 3.20)
project(MeuProjeto VERSION 1.0.0 LANGUAGES C CXX)

# --- Determinismo ---
set(LANG "C")
set(LC_ALL "C")

execute_process(
    COMMAND git log -1 --format=%ct
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    OUTPUT_VARIABLE GIT_TIMESTAMP
    OUTPUT_STRIP_TRAILING_WHITESPACE
    ERROR_QUIET
)
if(GIT_TIMESTAMP)
    set(CMAKE_SOURCE_DATE_EPOCH ${GIT_TIMESTAMP})
endif()

# --- Modulos personalizados ---
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/modules")
include(DeterminismCheck)
include(HashVerification)

# --- Configuracao de build ---
set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 17)
add_compile_options(-Wall -Wextra -Wpedantic)

# --- Biblioteca estatica ---
add_library(mylib_static STATIC src/mylib.c)
target_include_directories(mylib_static PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
set_target_properties(mylib_static PROPERTIES
    OUTPUT_NAME mylib
    PREFIX lib
)

# --- Biblioteca compartilhada ---
add_library(mylib_shared SHARED src/mylib.c)
target_include_directories(mylib_shared PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
set_target_properties(mylib_shared PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    OUTPUT_NAME mylib
    PREFIX lib
    INSTALL_RPATH ""
    BUILD_RPATH ""
)

# --- Executavel ---
add_executable(myexe src/main.c)
target_link_libraries(myexe PRIVATE mylib_static)

# --- Verificacao de determinismo ---
check_build_determinism(myexe)
check_build_determinism(mylib_static)
check_build_determinism(mylib_shared)

# --- Gerar checksums ---
add_custom_target(checksums
    COMMAND ${CMAKE_COMMAND} -E sha256sum
        $<TARGET_FILE:myexe>
        $<TARGET_FILE:mylib_static>
        $<TARGET_FILE:mylib_shared>
        > ${CMAKE_BINARY_DIR}/checksums.sha256
    DEPENDS myexe mylib_static mylib_shared
    COMMENT "Generating checksums for all targets"
)
```

---

## 15. Referencias

### Organizacoes e Projetos

- Reproducible Builds: https://reproducible-builds.org/
- Debian Reproducible Builds: https://wiki.debian.org/ReproducibleBuilds
- Nix: https://nixos.org/
- GNU Guix: https://guix.gnu.org/

### Documentacao

- CMake Documentation - CMAKE_SOURCE_DATE_EPOCH: https://cmake.org/cmake/help/latest/variable/CMAKE_SOURCE_DATE_EPOCH.html
- SOURCE_DATE_EPOCH specification: https://reproducible-builds.org/specs/source-date-epoch/
- Diffoscope documentation: https://diffoscope.org/
- Docker documentation: https://docs.docker.com/

### Artigos e Papers

- "Reproducible Builds: What, Why, and How" - Reproducible Builds organization
- "Trusting Trust" - Ken Thompson, 1984
- "Bootstrappable Builds" - Jérémy Bobbio
- "Building Reproducible Packages with Guix" - Ludovic Courtès

### Ferramentas

- diffoscope: https://diffoscope.org/
- reprotest: https://salsa.debian.org/reproducible-builds/reprotest
- strip-nondeterminism: https://salsa.debian.org/reproducible-builds/strip-nondeterminism
- normalize-deb: https://salsa.debian.org/reproducible-builds/normalize-deb

### CVEs Relacionados

- CVE-2024-3094: XZ Utils backdoor (supply chain via build system)
- CVE-2020-1472: Zerologon (afeta ambientes de build que dependem de Active Directory)

### Normas e Padroes

- NIST SP 800-218: Secure Software Development Framework
- ISO 27001:2022 - Security controls for build systems
- SLSA Framework: Supply-chain Levels for Software Artifacts
- Sigstore: https://www.sigstore.dev/
- in-toto: https://in-toto.io/

### Comunidades e Grupos

- Reproducible Builds mailing list: https://lists.reproducible-builds.org/
- Debian Reproducible Builds team: https://reproducible-builds-team.debian.net/
- NixOS community: https://discourse.nixos.org/
- GNU Guix community: https://guix.gnu.org/en/community/

### Videos e Treinamentos

- "Reproducible Builds in Practice" - FOSDEM talks
- "Building Secure Software with Nix" - NixCon presentations
- "Supply Chain Security" - DEF CON talks

### Livros e Documentacao Longa

- "The Art of Build Systems" - capitulo sobre determinismo
- "Reproducible Builds: A Step-by-Step Guide" - Reproducible Builds organization
- "Nix Pills" - Ludovic Courtès (livro online sobre Nix)
- "Guix Reference Manual" - documentacao oficial do Guix
- "Secure Software Development Lifecycle" - NIST guidelines
- "Build Systems à la Carte" - Simon Peyton Jones (paper academico)

### Comunidades ativas

- Debian Reproducible Builds: https://lists.reproducible-builds.org/pipermail/rb-general/
- Nix discourse: https://discourse.nixos.org/
- Guix discuss: https://lists.gnu.org/mailman/listinfo/guix-devel
- Reproducible Builds IRC: #reproducible-builds on OFTC

### Empresas e projetos adotantes

- Debian: 95%+ dos pacotes reproduziveis
- Arch Linux: Iniciativa em progresso
- Fedora: Suporte crescente
- NixOS: Reproduzivel por construcao
- Qubes OS: Usa builds reproduziveis para compontes criticos

---

*[Proximo capitulo: 09 — Finding Packages Seguro](09-finding-packages.md)*
