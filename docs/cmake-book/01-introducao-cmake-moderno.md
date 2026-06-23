---
layout: default
title: "Capitulo 01 — Introducao ao CMake Moderno"
---

# Capitulo 01 — Introducao ao CMake Moderno

> *"O build system nao e apenas uma ferramenta de compilacao — e a primeira camada de seguranca do seu software."*

---

## Sumario

- [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
- [Historia do CMake: de makefiles a generators modernos](#2-historia-do-cmake-de-makefiles-a-generators-modernos)
- [Por que CMake e o padrao da industria](#3-por-que-cmake-e-o-padrao-da-industria)
- [Instalacao e versionamento](#4-instalacao-e-versionamento)
- [Estrutura basica de um CMakeLists.txt](#5-estrutura-basica-de-um-cmakeliststxt)
- [Targets: executaveis, libraries, interface](#6-targets)
- [Generators: Make, Ninja, Visual Studio, Xcode](#7-generators)
- [Build types: Debug, Release, RelWithDebInfo, MinSizeRel](#8-build-types)
- [Variaveis, cache e environment](#9-variaveis-cache-e-environment)
- [Comandos fundamentais](#10-comandos-fundamentais)
- [Include directories, compile definitions e compile options](#11-include-directories-compile-definitions-e-compile-options)
- [Exemplo completo: projeto C++17 com CMake](#12-exemplo-completo)
- [Exercicios](#13-exercicios)
- [Anti-patterns comuns em CMake](#14-anti-patterns-comuns-em-cmake)
- [Referencias](#15-referencias)

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Explicar a evolucao do CMake desde sua criacao ate a versao moderna (3.20+).
2. Entender por que CMake se tornou o build system de facto para projetos C/C++.
3. Instalar e configurar CMake com versionamento adequado usando `cmake_minimum_required`.
4. Escrever um `CMakeLists.txt` correto e seguro para projetos de qualquer porte.
5. Diferenciar os tres tipos de targets: executaveis, bibliotecas compartilhadas e bibliotecas interface.
6. Escolher o generator adequado para cada plataforma e cenario.
7. Configurar build types que influenciam flags de compilacao e seguranca.
8. Dominar o sistema de variaveis, cache e ambiente do CMake.
9. Usar comandos fundamentais como `add_executable`, `add_library` e `target_link_libraries`.
10. Configurar include directories, compile definitions e compile options de forma moderna.
11. Montar um projeto completo em C++17 usando as praticas recomendadas.

### Por que estes objetivos importam para seguranca

Muitos engenheiros tratam o `CMakeLists.txt` como "codigo de configuracao" que pode ser copiado e colado de templates. Esta e uma das maiores fontes de vulnerabilidades em software C/C++. Um build system mal configurado pode:

- Gerar binarios sem protecao contra buffer overflows
- Desabilitar ASLR ou DEP sem que o desenvolvedor perceba
- Compilar com otimizacoes que eliminam verificacoes de seguranca
- Incluir dependencias nao auditadas do sistema operacional
- Produzir binarios nao-reproduziveis, impossibilitando verificacao forense

O dominio destes conceitos e o primeiro passo para construir pipelines de build seguros. Cada conceito abordado aqui sera aprofundado em capitulos posteriores com foco especifico em seguranca.

---

## 2. Historia do CMake: de makefiles a generators modernos

### 2.1 O problema original: portabilidade de Makefiles

Na decada de 1990, o Make era a ferramenta padrao para automacao de builds em sistemas UNIX. Cada projeto escrevia um `Makefile` manual ou usava ferramentas geradoras de Makefile como `autoconf`, `automake` e `libtool` — coletivamente conhecidos como GNU Autotools.

O problema fundamental era a portabilidade:

- Makefiles escritos para GCC nao funcionavam com Sun Studio
- Makefiles para Linux nao compilavam em Solaris ou HP-UX
- Makefiles para UNIX nao funcionavam no Windows
- Diferentes versoes de make tinham sintaxes incompativeis
- GNU Make e BSD Make tinham subconjuntos diferentes

Cada plataforma precisava de um Makefile diferente, ou de um `Makefile.in` processado por scripts que tentavam detectar automaticamente as capacidades do compilador. O resultado era fragil, dificil de manter e cheio de workarounds.

### 2.2 O nascimento do CMake (1999-2000)

CMake foi criado por Bill Hoffman e Eric Noulard no Research & Development Institute (RDI), uma subsidiaria da GE Healthcare. O objetivo era construir um sistema de build que:

1. Gerasse Makefiles nativos para cada plataforma
2. Fosse declarativo em vez de imperativo
3. Tivesse uma linguagem de scripting para operacoes complexas
4. Suportasse multiplos geradores de build
5. Fosse simples de aprender e usar

O nome "CMake" e uma abreviacao de "Cross-platform Make", refletindo sua missao original de unificar a geracao de Makefiles em plataformas diferentes.

### 2.3 Evolucao temporizada

| Ano | Versao | Marco Principal |
|-----|--------|-----------------|
| 1999 | CMake 1.0 | Primeira versao interna no RDI |
| 2000 | CMake 1.2 | Lancamento como open-source no SourceForge |
| 2001 | CMake 2.0 | Suporte a install targets, CPack |
| 2003 | CMake 2.2 | CTest introduzido para testes automatizados |
| 2005 | CMake 2.6 | Target model inicial, politicas |
| 2008 | CMake 2.8 | Estabilizacao da sintaxe, melhor suporte IDE |
| 2014 | CMake 3.0 | Modern target model, generator expressions |
| 2016 | CMake 3.5 | Filesets, melhorias em cross-compilation |
| 2018 | CMake 3.12 | Target-based include directories (final) |
| 2020 | CMake 3.17 | Presets, melhorias em FetchContent |
| 2021 | CMake 3.20 | TOOLCHAIN_FILE, presets v3, FindPython moderno |
| 2022 | CMake 3.24 | PACKAGE_CONFIG, subproject improvements |
| 2023 | CMake 3.27 | Block/Policies, FileSet de compilacao |
| 2024 | CMake 3.28 | Suporte a C++23, melhorias em FetchContent |
| 2025 | CMake 3.30 | Melhorias em presetering, novas propriedades |

### 2.4 O paradigma "gerador de build"

A grande inovacao do CMake nao foi criar uma nova linguagem de Makefile. Foi introduzir o conceito de **generator**: CMake nao compila codigo — ele gera arquivos de build para outra ferramenta.

O fluxo e:

```
CMakeLists.txt  -->  CMake (configure)  -->  Build System Files
                                                  |
                                                  v
                                         make / ninja / msbuild
                                                  |
                                                  v
                                              Binarios
```

Esta separacao e fundamental porque:

- O CMakeLists.txt descreve o que construir, nao como
- O "como" e delegado para o generator mais adequado
- O mesmo CMakeLists.txt pode gerar Makefiles, Ninja files, projetos VS ou Xcode
- As flags de compilacao sao resolvidas apenas no momento do build real

### 2.5 A revolucao moderna: target-based CMake

Ate CMake 2.8, a maioria dos projetos usava variaveis globais:

```cmake
# Estilo antigo (NAO recomendado)
include_directories(${CMAKE_SOURCE_DIR}/include
                    ${CMAKE_SOURCE_DIR}/third_party/abc)
link_directories(${CMAKE_SOURCE_DIR}/lib)
add_definitions(-DUSE_SSL=1 -Wall -Wextra)
add_executable(myapp main.cpp utils.cpp)
target_link_libraries(myapp ssl crypto pthread)
```

Este estilo tem problemas graves de seguranca e manutencao:

- `include_directories` afeta TODOS os targets no diretorio — incluindo bibliotecas de terceiros
- `link_directories` e universalmente considerado inseguro (podia linkar bibliotecas nao intencionais)
- `add_definitions` e global — voce nao consegue aplicar flags diferentes para targets diferentes
- `target_link_libraries` sem `PRIVATE`/`PUBLIC`/`INTERFACE` expoe dependencias desnecessarias

O target-based CMake, introduzido gradualmente desde CMake 2.8.12 e maduro desde CMake 3.12, resolve estes problemas:

```cmake
# Estilo moderno (recomendado)
add_executable(myapp main.cpp utils.cpp)

target_include_directories(myapp
    PRIVATE ${CMAKE_SOURCE_DIR}/include
)

target_compile_definitions(myapp
    PRIVATE USE_SSL=1
)

target_compile_options(myapp
    PRIVATE -Wall -Wextra -Werror
)

target_link_libraries(myapp
    PRIVATE
        ssl
        crypto
        Threads::Threads
)
```

As diferencas criticas:

1. Cada propriedade e aplicada a um target especifico
2. O escopo e explicito: `PRIVATE`, `PUBLIC` ou `INTERFACE`
3. `link_directories` e eliminado em favor de targets de biblioteca
4. A dependencia e rastreavel: voce sabe exatamente o que cada target precisa

### 2.6 CMake 3.20+: o que mudou significativamente

CMake 3.20 marcou um ponto de inflexao na maturidade do sistema:

**cmake_minimum_required(VERSION 3.20)**:

- Ativa todas as politicas modernas por padrao
- Descontinua suporte a sintaxes antigas perigosas
- Ativa o comportamento de error-on-deprecated
- Permite usar `cmake_policy` de forma mais granular

**Presets (v3)**:

- Formato padronizado para configuracoes de build
- Versionamento de presets (schema version 3)
- Suporte a presets de usuario e de projeto
- Integracao com CI/CD pipelines

**FindPython moderno**:

- `find_package(Python3)` como modulo padrao
- Suporte a componentes granulares (Interpreter, Development, NumPy)
- Melhor deteccao de ambientes virtuais

**FetchContent melhorias**:

- `FetchContent_Declare` com `DOWNLOAD_EXTRACT_TIMESTAMP`
- Melhor controle de cache e offline builds
- `OVERRIDE_FIND_PACKAGE` para substituir find_package

### 2.7 CMake e o futuro: direction de desenvolvimento

O time do CMake esta focado em areas estrategicas:

1. **Melhor suporte a package management**: integracao nativa com gerenciadores de pacotes
2. **Presets universais**: padronizacao de configuracoes para IDEs e CI/CD
3. **Build reproducibility**: suporte nativo a builds deterministas
4. **Toolchain files modernos**: simplificacao de cross-compilation
5. **Melhor desempenho**: cache distribuido, parallelism, incremental builds

---

## 3. Por que CMake e o padrao da industria

### 3.1 Adocao em projetos de referencia

CMake nao e apenas "mais uma opcao". Ele e o build system dominante em praticamente todos os ecossistemas C/C++ de producao:

**Compiladores e ferramentas de build**:

- **LLVM/Clang**: o maior projeto C++ do mundo usa CMake desde 2011
- **GCC**: usa CMake para componentes adicionais e para build em Windows
- **Ninja**: construido com CMake, e o generator recomendado para CMake

**Frameworks e bibliotecas**:

- **Qt**: migrou de qmake para CMake em 2020 (Qt 6)
- **OpenCV**: usa CMake exclusivamente desde a versao 3.0
- **Boost**: suporta CMake desde 1.70 como alternativa ao b2
- **TensorFlow**: usa CMake para builds nativos em Windows
- **spdlog**: projetado inteiramente para CMake com `FetchContent`

**Projetos de seguranca**:

- **OpenSSL**: suporte a CMake desde 3.0
- **Libsodium**: construido com CMake
- **BoringSSL**: Google usa CMake para seu fork do OpenSSL
- **cURL**: suporte a CMake como build alternativo

**Sistemas operacionais e embedded**:

- **Zephyr RTOS**: usa CMake como build system primario
- **ESP-IDF**: usa CMake (migrado do GNU Make)
- **Android NDK**: usa CMake para builds nativos
- **Windows SDK**: suporte a CMake desde Windows 10 SDK

### 3.2 Por que CMake venceu as alternativas

Comparado com as alternativas historicas e contemporaneas:

| Caracteristica | CMake | Autotools | Meson | Bazel | Premake |
|----------------|-------|-----------|-------|-------|---------|
| Portabilidade | Excelente | Limitada | Excelente | Excelente | Boa |
| Curva de aprendizado | Moderada | Alta | Baixa | Alta | Baixa |
| Comunidade | Massiva | Declinante | Crescendo | Grande | Pequena |
| IDE Support | Nativo | Nenhum | Parcial | Parcial | Parcial |
| Package management | Bom | Nenhum | Medio | Excelente | Nenhum |
| Flexibilidade | Alta | Alta | Moderada | Baixa | Moderada |
| Maturidade | 25+ anos | 30+ anos | 10+ anos | 8+ anos | 15+ anos |

CMake venceu porque equilibrou portabilidade, flexibilidade e adocao. Autotools e poderoso mas complexo e limitado a UNIX. Bazel e excelente para monorepos mas tem curva de aprendizado alta. Meson e moderno e rapido mas ainda nao tem a mesma base instalada.

### 3.3 O ecossistema CMake

CMake nao e isolado — ele se conecta com um ecossistema rico:

**Geradores de build suportados**:

- Unix Makefiles
- Ninja
- Visual Studio 17 2022 (e versoes anteriores)
- Xcode
- NMake Makefiles
- MinGW Makefiles
- Ninja Multi-Config

**Ferramentas integradas**:

- CTest: framework de testes
- CPack: framework de packaging
- CDash: dashboard de testes e builds
- CMake Presets: configuracoes padronizadas

**Gerenciadores de pacotes integrados**:

- `find_package()`: localizar pacotes do sistema
- `FetchContent`: baixar e construir dependencias durante o configure
- `ExternalProject`: gerenciar projetos externos complexos
- Integracao com vcpkg, Conan, Hunter

**IDEs com suporte nativo a CMake**:

- CLion (JetBrains): suporte completo
- Visual Studio: abertura e build diretos
- Visual Studio Code (via extensao CMake Tools)
- Qt Creator: integracao profunda
- Xcode (via gerador Xcode)

### 3.4 Implicacoes de seguranca na adocao

A adocao massiva de CMake tem implicacoes de seguranca que este livro explora:

1. **Padronizacao**: quando todos usam o mesmo build system, padroes de seguranca podem ser definidos uma vez e reutilizados
2. **Auditoria**: existem ferramentas que analisam CMakeLists.txt para encontrar problemas
3. **Reproduzibilidade**: CMake e fundamental para builds deterministas
4. **Dependencias**: o ecossistema de package management do CMake e o ponto de entrada para supply chain attacks
5. **Flags de seguranca**: CMake e o ponto onde flags como `-fstack-protector-strong` sao definidas

---

## 4. Instalacao e versionamento

### 4.1 Instalacao por plataforma

#### Linux (Debian/Ubuntu)

```bash
# Versao padrao do repositorio (geralmente antiga)
sudo apt update
sudo apt install cmake

# Versao atual via snap
sudo snap install cmake --classic

# Verificacao de versao
cmake --version
```

**Recomendacao de seguranca**: use sempre a versao mais recente do snap ou do repositorio oficial do Kitware. Versoes antigas do repositorio do Ubuntu podem ter problemas conhecidos e nao recebem patches de seguranca.

#### Linux (Fedora/RHEL)

```bash
# Versao padrao
sudo dnf install cmake

# Via snap
sudo snap install cmake --classic
```

#### macOS

```bash
# Via Homebrew (recomendado)
brew install cmake

# Verificacao
cmake --version
```

#### Windows

```bash
# Via chocolatey
choco install cmake --installargs '"ADD_CMAKE_TO_PATH=System"'

# Via winget
winget install Kitware.CMake

# Via instalador manual
# Download de https://cmake.org/download/
# Marcar "Add CMake to the system PATH"
```

#### Verificao de integridade

Para ambientes de producao, sempre verifique a integridade do instalador:

```bash
# Baixar o hash SHA-256 oficial
# Compare com o hash do arquivo baixado
sha256sum cmake-3.28.1-linux-x86_64.tar.gz

# Para pacotes gerenciados, verifique a assinatura GPG
# (procedimento varia por gerenciador de pacotes)
```

### 4.2 Versionamento: cmake_minimum_required

O comando `cmake_minimum_required` e o ponto de entrada de seguranca mais importante de qualquer `CMakeLists.txt`. Ele controla:

1. **Quais politicas sao ativadas**: cada versao do CMake introduz politicas que mudam comportamentos
2. **Quais features estao disponiveis**: comandos e propriedades sao disponibilizados por versao
3. **Comportamento de deprecacao**: versoes novas podem gerar erros ou warnings

```cmake
cmake_minimum_required(VERSION 3.20)
```

**Por que 3.20 e o minimo recomendado**:

- Todas as politicas modernas estao ativas por padrao
- Presets v3 estao disponiveis
- `target_sources` com `FILE_SET` esta disponivel
- `find_package(Python3)` e o modulo padrao
- FetchContent tem melhorias significativas
- O comportamento de erro em deprecated esta ativo

### 4.3 Politicas: cmake_policy

Cada versao do CMake pode mudar o comportamento padrao de comandos existentes. Estas mudancas sao controladas por politicas numeradas.

```cmake
cmake_minimum_required(VERSION 3.20)

# Ativar uma politica especifica
# CMP0077: option() nao sobrescreve variaveis normais (desde 3.13)
if(POLICY CMP0077)
    cmake_policy(SET CMP0077 NEW)
endif()

# Definir todas as politicas ate uma versao especifica
# NEW = comportamento moderno
# OLD = comportamento antigo (DEPRECATED)
cmake_policy(VERSION 3.20)
```

**Politicas criticas para seguranca**:

| Politica | Versao | Efeito |
|----------|--------|--------|
| CMP0063 | 3.3 | Visibility para todos os target types |
| CMP0065 | 3.4 | ENABLE_EXPORTS nao e mais padrao para executaveis |
| CMP0066 | 3.7 | Honra flags de compile em try_compile |
| CMP0067 | 3.8 | Honra padrao de linguagem em try_compile |
| CMP0069 | 3.9 | INTERPROCEDURAL_OPTIMIZATION e permitido |
| CMP0074 | 3.12 | find_package usa <Package>_ROOT |
| CMP0076 | 3.13 | target_sources converte paths relativos |
| CMP0077 | 3.13 | option() nao sobrescreve variaveis normais |
| CMP0079 | 3.13 | target_link_libraries permite targets de outros diretorios |
| CMP0128 | 3.22 | VISIBILITY_INLINES_HIDDEN e padrao para C e CXX |

### 4.4 Versoes minimas por contexto

| Contexto | Versao Minima | Justificativa |
|----------|---------------|---------------|
| Projeto novo em 2024+ | 3.20 | Todas as features modernas |
| Projeto com vcpkg | 3.21 | Preset integration |
| Projeto com FetchContent | 3.24 | Melhorias em download |
| Projeto com presets | 3.25 | Presets v4 |
| Projeto legado | 3.16 | Equilibrio entre moderno e compativel |
| Embedded/RTOS | 3.18 | Toolchain support maduro |

### 4.5 Deteccao de versao em tempo de execucao

```cmake
cmake_minimum_required(VERSION 3.20)

# Verificar se esta rodando no CMake esperado
if(CMAKE_VERSION VERSION_LESS "3.20")
    message(FATAL_ERROR
        "Este projeto requer CMake 3.20 ou superior. "
        "Versao atual: ${CMAKE_VERSION}"
    )
endif()

# Verificacao condicional de features
if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.24")
    message(STATUS "Usando CMake ${CMAKE_VERSION} — features avancadas disponiveis")
endif()
```

---

## 5. Estrutura basica de um CMakeLists.txt

### 5.1 Arquitetura de um CMakeLists.txt

Todo `CMakeLists.txt` segue uma estrutura hierarquica:

```
meu-projeto/
  CMakeLists.txt          # Arquivo raiz (project root)
  src/
    CMakeLists.txt        # Build para executavel principal
  lib/
    CMakeLists.txt        # Build para bibliotecas
  test/
    CMakeLists.txt        # Build para testes
  cmake/                  # Modulos de cmake customizados
    FindSomething.cmake
  include/                # Headers publicos
    meu-projeto/
      header.h
```

O `CMakeLists.txt` raiz e o ponto de entrada. Ele:

1. Declara o projeto com `project()`
2. Define a versao minima do CMake
3. Configura opcoes globais
4. Adiciona subdiretorios com `add_subdirectory()`

### 5.2 Um CMakeLists.txt minimo correto

```cmake
cmake_minimum_required(VERSION 3.20)

project(MeuProjeto
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Um projeto de exemplo"
)

add_executable(meuprodigo
    src/main.cpp
    src/utils.cpp
)
```

Este e o minimo absoluto para um projeto funcional. Porem, para seguranca, precisamos de mais.

### 5.3 Estrutura completa recomendada

```cmake
cmake_minimum_required(VERSION 3.20)

# ============================================================
# Projeto
# ============================================================
project(MeuProjeto
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Projeto com seguranca em mente"
)

# ============================================================
# Configuracoes globais
# ============================================================

# Nao permitir construicao na fonte (in-source build)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR
        "Construcao na fonte nao e permitida. "
        "Crie um diretorio de build separado: "
        "cmake -B build"
    )
endif()

# Default a build type (se nao especificado)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# Padroes de compilacao
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ============================================================
# Opcoes do projeto
# ============================================================
option(MEUPROJETO_BUILD_TESTS "Construir testes" ON)
option(MEUPROJETO_BUILD_EXAMPLES "Construir exemplos" ON)

# ============================================================
# Targets
# ============================================================
add_subdirectory(src)

# ============================================================
# Testes (condicional)
# ============================================================
if(MEUPROJETO_BUILD_TESTS)
    enable_testing()
    add_subdirectory(test)
endif()
```

### 5.4 Erros comuns em CMakeLists.txt

#### Erro 1: In-source build

```cmake
# ERRADO: nao verifica se o build e na fonte
cmake_minimum_required(VERSION 3.20)
project(MeuProjeto)
add_executable(meuprodigo main.cpp)
```

Se o usuario executar `cmake .` no diretorio raiz, os arquivos de build serao misturados com o codigo fonte. Isto pode causar:

- Poluicao do repositorio Git
- Conflitos entre arquivos gerados e fonte
- Dificuldade em limpar o build

#### Erro 2: Versao minima nao definida

```cmake
# ERRADO: nao especifica versao minima
project(MeuProjeto)
add_executable(meuprodigo main.cpp)
```

Sem `cmake_minimum_required`, o CMake usa comportamentos antigos que podem ser inseguros. Por exemplo, a politica CMP0063 (visibility) nao e ativada, e executaveis podem expor simbolos internos.

#### Erro 3: linguagem nao especificada

```cmake
# ERRADO: nao especifica linguagens
cmake_minimum_required(VERSION 3.20)
project(MeuProjeto)
add_executable(meuprodigo main.cpp)
```

Quando `project()` nao especifica `LANGUAGES`, o CMake tenta detectar automaticamente. Isto e lento e imprevisivel. Sempre especifique as linguagens explicitamente.

### 5.5 Organizacao de diretorios

#### Arquitetura por camada (recomendada para seguranca)

```
meu-projeto/
  CMakeLists.txt              # Root
  cmake/
    CompilerWarnings.cmake    # Flags de warning centralizadas
    Sanitizers.cmake          # Configuracao de sanitizers
    StaticAnalysis.cmake      # clang-tidy, cppcheck
  src/
    CMakeLists.txt            # Targets de producao
    core/
      CMakeLists.txt          # Biblioteca core
      core.cpp
      core.h
    app/
      CMakeLists.txt          # Executavel principal
      main.cpp
  include/
    meu-projeto/
      public_header.h         # Headers publicos da API
  test/
    CMakeLists.txt            # Configuracao de testes
    unit/
      CMakeLists.txt
      test_core.cpp
    integration/
      CMakeLists.txt
      test_integration.cpp
  docs/
    Doxyfile.in
  third_party/
    CMakeLists.txt            # Dependencias externas
```

Esta organizacao permite:

- Isolacao de responsabilidades em cada `CMakeLists.txt`
- Centrais de configuracao de seguranca (cmake/)
- Separação entre API publica e implementacao
- Testes organizados por tipo
- Dependencias gerenciadas isoladamente

---

## 6. Targets

### 6.1 O conceito de target

Um target e a unidade basica do build system do CMake. Cada target representa:

- Um executavel para ser gerado
- Uma biblioteca para ser construida
- Uma interface para propagar propriedades

Targets sao declarados com comandos especificos e possuem propriedades que controlam como sao construidos, como interagem com outros targets, e como sao instalados.

### 6.2 Executaveis: add_executable

```cmake
add_executable(meuprodigo
    src/main.cpp
    src/utils.cpp
    src/config.cpp
)
```

**Propriedades essenciais de executaveis**:

```cmake
add_executable(meuprodigo
    src/main.cpp
    src/utils.cpp
)

# Nome de saida (override do padrao)
set_target_properties(meuprodigo PROPERTIES
    OUTPUT_NAME "mp"
)

# Versao do binario
set_target_properties(meuprodigo PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)

# Sufixo customizado
set_target_properties(meuprodigo PROPERTIES
    DEBUG_POSTFIX "_d"
)

# Visibilidade de exportacao (IMPORTANTE para seguranca)
set_target_properties(meuprodigo PROPERTIES
    ENABLE_EXPORTS OFF
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)
```

**Executaveis IMPORTED** (para ferramentas pre-compiladas):

```cmake
add_executable(ninja IMPORTED)
set_target_properties(ninja PROPERTIES
    IMPORTED_LOCATION "/usr/bin/ninja"
)
```

### 6.3 Bibliotecas: add_library

CMake suporta multiplos tipos de bibliotecas:

#### Biblioteca estatica (STATIC)

```cmake
add_library(mylib STATIC
    src/core.cpp
    src/utils.cpp
)
```

Vantagens de seguranca:

- Todas as dependencias sao resolvidas no link-time
- Nao ha risco de DLL hijacking
- O binario final e auto-contido (mais facil de auditar)
- Simbolos podem ser otimizados (dead code elimination)

#### Biblioteca compartilhada (SHARED)

```cmake
add_library(mylib SHARED
    src/core.cpp
    src/utils.cpp
)

# Versao da biblioteca
set_target_properties(mylib PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
)
```

Implicacoes de seguranca:

- DLL search path pode ser explorado (DLL hijacking)
- Versoes anteriores podem ter vulnerabilidades (CVE em dependencias compartilhadas)
- ASLR e mais eficaz com bibliotecas compartilhadas
- `RPATH` pode expor caminhos internos

#### Biblioteca MODULE

```cmake
add_library(myplugin MODULE
    src/plugin.cpp
)
```

Modulos sao como compartilhadas mas nao sao linkados — sao carregados dinamicamente em runtime com `dlopen()`. Cuidado especialmente com a seguranca destes, pois sao frequentemente o vetor de ataque para exploits de plugin.

#### Biblioteca interface (INTERFACE)

```cmake
add_library(myheaders INTERFACE)

target_include_directories(myheaders
    INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(myheaders
    INTERFACE cxx_std_17
)
```

Bibliotecas interface nao compilam nada — elas propagam propriedades para quem as consome. Sao usadas para:

- Headers-only libraries
- Definicao de padroes de compilacao
- Configuracoes compartilhadas entre targets

#### Biblioteca ALIAS

```cmake
add_library(MyProject::Core ALIAS mycore)
```

Aliases criam nomes qualificados que simulam targets importados de um package. Sao fundamentais para padronizar nomes de targets em projetos grandes.

#### Biblioteca OBJECT

```cmake
add_library(myobj OBJECT
    src/core.cpp
    src/utils.cpp
)
```

Objetos compilam o codigo mas nao geram um arquivo de biblioteca. Sao uteis para:

- Compartilhar objetos entre executavel e testes
- Evitar recompilacao em multiplos targets
- Construcao modular

### 6.4 Propriedades de visibilidade (IMPORTANTE para seguranca)

```cmake
add_library(mylib SHARED src/core.cpp)

# Ocultar todos os simbolos por padrao
set_target_properties(mylib PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    C_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)
```

A visibilidade controla quais simbolos sao exportados da biblioteca:

- `hidden`: todos os simbolos sao internos (padrao recomendado)
- `default`: todos os simbolos sao exportados (padrao historico)
- `protected`: exportados mas nao sao sobrescritos por aliases

**Por que visibilidade importa**:

- Simbolos visiveis podem ser interceptados (function hooking)
- Simbolos expostos revelam a estrutura interna do binario
- Menos simbolos exportados = menor superficie de ataque
- Melhora o desempenho (o linker pode otimizar mais)

### 6.5 Configuracao de targets

```cmake
add_executable(meuprodigo
    src/main.cpp
    src/utils.cpp
)

# Propriedades de build
set_target_properties(meuprodigo PROPERTIES
    # Padrao de padrao C++
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF

    # Output
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib

    # Sufixo por build type
    DEBUG_POSTFIX "_d"
    RELEASE_POSTFIX ""

    # Seguranca
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON

    # Posicao independente (IMPORTANTE para ASLR)
    POSITION_INDEPENDENT_CODE ON

    # Interprocedural optimization (LTO)
    INTERPROCEDURAL_OPTIMIZATION_RELEASE ON
)
```

---

## 7. Generators

### 7.1 O que e um generator

O generator e a ferramenta que CMake usa para criar os arquivos de build. O CMakeLists.txt descreve o que construir; o generator决定 como isso sera compilado.

```
CMakeLists.txt --> CMake --> Build System Files --> Compiler
                               |
                          (generator)
```

### 7.2 Generators disponiveis

#### Unix Makefiles

```bash
cmake -G "Unix Makefiles" -B build
cmake --build build
```

- O generator mais maduro e amples
- Suporta parallel builds com `make -jN`
- IDE support limitado
- Ideal para servidores e CI/CD

#### Ninja

```bash
cmake -G Ninja -B build
cmake --build build
```

- Mais rapido que Make para builds incrementais
- Melhor gerenciamento de dependencias
- Output mais limpo e organizado
- Recomendado pelo proprio time do CMake
- Suporta parallel builds automaticamente

#### Ninja Multi-Config

```bash
cmake -G "Ninja Multi-Config" -B build
cmake --build build --config Release
```

- Permite multiplos build types em um so diretorio
- Ideal para desenvolvimento local (Debug + Release)
- Mais eficiente que multiplos diretorios de build

#### Visual Studio 17 2022

```bash
cmake -G "Visual Studio 17 2022" -B build
cmake --build build --config Release
```

- Gera um arquivo .sln e .vcxproj
- Integracao nativa com Visual Studio IDE
- Suporta multiplos build types
- Ideal para desenvolvimento Windows

#### Visual Studio 17 2022 - Arm64

```bash
cmake -G "Visual Studio 17 2022" -A ARM64 -B build
```

#### Xcode

```bash
cmake -G Xcode -B build
cmake --build build --config Release
```

- Gera um projeto .xcodeproj
- Integracao nativa com Xcode IDE
- Suporta debug com lldb
- Ideal para desenvolvimento macOS/iOS

### 7.3 Selecionando o generator

```bash
# Listar generators disponiveis
cmake --help

# Especificar generator na linha de comando
cmake -G Ninja -B build

# Ou via variavel de ambiente
export CMAKE_GENERATOR=Ninja
cmake -B build
```

### 7.4 Generators e seguranca

A escolha do generator influencia a seguranca:

| Generator | Paralelismo | Reprodutibilidade | Seguranca de flags |
|-----------|-------------|-------------------|-------------------|
| Unix Makefiles | make -jN | Depende | Flags via ENV sao inseguras |
| Ninja | Automatico | Excelente | Flags sao arquivos estaticos |
| Visual Studio | Automatico | Boa | Propriedades do .vcxproj |
| Xcode | Automatico | Boa | Build settings do .xcodeproj |

**Recomendacao**: para ambientes de CI/CD e producao, prefira Ninja. Ele e mais rapido, mais previsivel, e gera arquivos de build mais faceis de auditar.

### 7.5 Configuracao via presets

CMake Presets e a forma moderna de gerenciar configuracoes de build:

```json
{
    "version": 3,
    "configurePresets": [
        {
            "name": "default",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_CXX_STANDARD": "17",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
            }
        },
        {
            "name": "debug",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build-debug",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_CXX_STANDARD": "17"
            }
        },
        {
            "name": "secure",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build-secure",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "RelWithDebInfo",
                "CMAKE_CXX_STANDARD": "20",
                "MEUPROJETO_ENABLE_SANITIZERS": "ON",
                "MEUPROJETO_ENABLE_STATIC_ANALYSIS": "ON"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "default",
            "configurePreset": "default"
        }
    ]
}
```

---

## 8. Build types

### 8.1 O conceito de build type

Build types determinam como o compilador trata o codigo. Cada build type combina otimizacao, informacao de debug e verificacoes de seguranca.

### 8.2 Build types padrao

#### Debug

```cmake
set(CMAKE_BUILD_TYPE Debug)
```

Caracteristicas:
- `-O0` (sem otimizacao)
- `-g` (informacao de debug completa)
- Sem eliminacao de codigo morto
- Todos os asserts ativos
- Symoblos preservados

Flags tipicas (GCC/Clang):
```
-O0 -g -DDEBUG -D_DEBUG
```

Uso:
- Desenvolvimento local
- Debugging com gdb/lldb
- Analise de memory leaks com valgrind

#### Release

```cmake
set(CMAKE_BUILD_TYPE Release)
```

Caracteristicas:
- `-O3` ou `-O2` (otimizacao maxima)
- Sem informacao de debug
- Eliminacao de codigo morto
- Inlining agressivo
- Pode eliminar verificacoes de seguranca

Flags tipicas (GCC/Clang):
```
-O3 -DNDEBUG
```

Uso:
- Producao
- Benchmarks
- Distribuicao de binarios

**Alerta de seguranca**: `-O3` pode消除 verificacoes de bounds checking e alinhar codigo de forma que torne exploits mais faceis. Sempre combine com flags de hardening especificas (Capitulo 04).

#### RelWithDebInfo

```cmake
set(CMAKE_BUILD_TYPE RelWithDebInfo)
```

Caracteristicas:
- `-O2` (otimizacao moderada)
- `-g` (informacao de debug)
- DWARF debug info embutido
- Equilibrio entre desempenho e debuggabilidade

Flags tipicas (GCC/Clang):
```
-O2 -g -DNDEBUG -fno-omit-frame-pointer
```

Uso:
- Profiling em ambiente proximo de producao
- Debugging de problemas que so aparecem com otimizacao
- Crash analysis com core dumps

#### MinSizeRel

```cmake
set(CMAKE_BUILD_TYPE MinSizeRel)
```

Caracteristicas:
- `-Os` (otimizacao para tamanho)
- `-g` (informacao de debug leve)
- Menor binario possivel
- Pode perder desempenho em troca de tamanho

Flags tipicas (GCC/Clang):
```
-Os -g -DNDEBUG
```

Uso:
- Embedded systems
- Containers Docker com tamanho minimo
- Distribuicao onde tamanho importa

### 8.3 Build types customizados

```cmake
# Build type seguro (recomendado para producao)
set(CMAKE_CXX_FLAGS_SECURE "-O2 -g -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -pie -Wall -Wextra -Werror")

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Secure CACHE STRING "Build type" FORCE)
endif()

# Registrar o build type customizado
set_property(CACHE CMAKE_BUILD_TYPE PROPERTY
    STRINGS Debug Release RelWithDebInfo MinSizeRel Secure
)
```

### 8.4 Build type e flags de seguranca

| Build Type | Otimizacao | Debug | Flags de seguranca |
|------------|-----------|-------|-------------------|
| Debug | Nenhuma | Sim | Depende da config |
| Release | Maxima | Nao | Depende da config |
| RelWithDebInfo | Moderada | Sim | Depende da config |
| MinSizeRel | Tamanho | Sim | Depende da config |

**Ponto critico**: o build type por si so NAO garante seguranca. Um `Release` com `-O3` pode desabilitar verificacoes de bounds. A seguranca precisa ser adicionada explicitamente via flags adicionais (Capitulo 04).

### 8.5 Selecionando build type

```bash
# Na linha de comando
cmake -B build -DCMAKE_BUILD_TYPE=Release

# Com presets
cmake --preset default

# Via variavel de ambiente
export CMAKE_BUILD_TYPE=Debug
cmake -B build
```

---

## 9. Variaveis, cache e environment

### 9.1 O sistema de variaveis do CMake

CMake tem tres scopes de variaveis:

1. **Cache**: persiste entre executacoes do cmake (armazenadas em CMakeCache.txt)
2. **Normal**: existe apenas durante a executacao atual do cmake
3. **Environment**: variaveis do sistema operacional

### 9.2 Variaveis de cache

```cmake
# Definir uma variavel de cache (persiste entre runs)
set(MEUPROJETO_VERSION "1.0.0" CACHE STRING "Versao do projeto")

# Definir com valor padrao so se nao estiver no cache
set(MY_OPTION ON CACHE BOOL "Habilitar feature X")

# Forcar atualizacao do cache
set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Build type" FORCE)

# Mostrar todas as variaveis de cache
# (util para debugging)
get_cmake_property(_varNames VARIABLES)
foreach(_varName ${_varNames})
    message(STATUS "${_varName} = ${${_varName}}")
endforeach()
```

**Seguranca do cache**:

- Variaveis de cache sao escritas em `CMakeCache.txt`
- Este arquivo NUNCA deve ser committado no repositorio
- Adicione `CMakeCache.txt` ao `.gitignore`
- Variaveis de cache podem ser sobrescritas na linha de comando
- Em CI/CD, sempre defina variaveis explicitamente (nao dependa do cache)

### 9.3 Variaveis normais

```cmake
# Variavel normal (nao persiste)
set(MY_VAR "valor")
message(STATUS "MY_VAR = ${MY_VAR}")

# Escopo: variaveis normais sao herdadas por subdiretorios
# mas NAO sao transmitidas para o escopo pai
```

### 9.4 Variaveis de ambiente

```cmake
# Ler variavel de ambiente
message(STATUS "USER = $ENV{USER}")
message(STATUS "HOME = $ENV{HOME}")

# Definir variavel de ambiente para o build
set(ENV{CC} "/usr/bin/clang")

# Condicionais baseadas em ambiente
if(DEFINED ENV{CI})
    message(STATUS "Rodando em CI — habilitando features de CI")
endif()
```

### 9.5 Variaveis内置 do CMake

CMake define automaticamente varias variaveis uteis:

```cmake
# Informacoes do projeto
message(STATUS "Nome: ${PROJECT_NAME}")
message(STATUS "Versao: ${PROJECT_VERSION}")
message(STATUS "Source dir: ${CMAKE_SOURCE_DIR}")
message(STATUS "Binary dir: ${CMAKE_BINARY_DIR}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")

# Informacoes do compilador
message(STATUS "CXX compiler: ${CMAKE_CXX_COMPILER}")
message(STATUS "CXX compiler ID: ${CMAKE_CXX_COMPILER_ID}")
message(STATUS "CXX compiler version: ${CMAKE_CXX_COMPILER_VERSION}")

# Informacoes da plataforma
message(STATUS "Sistema: ${CMAKE_SYSTEM_NAME}")
message(STATUS "Processador: ${CMAKE_SYSTEM_PROCESSOR}")

# Informacoes de build
message(STATUS "Generator: ${CMAKE_GENERATOR}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
```

### 9.6 Propriedades vs Variaveis

CMake tem dois sistemas de armazenamento de dados: variaveis e propriedades. Entender a diferenca e critico:

**Variaveis**:
- Simples: `set(VAR "value")`
- Escopo: normal (local ao CMakeLists.txt atual e subdiretorios)
- Uso: configuracoes gerais, flags, caminhos

**Propriedades**:
- Complexas: `set_target_properties(target PROPERTIES PROP "value")`
- Escopo: especificas a um target, diretorio, ou global
- Uso: configuracoes de build, seguranca, instalacao

```cmake
# Variavel (simples, global)
set(MY_FLAGS "-Wall -Wextra")

# Propriedade (especifica do target)
set_target_properties(mylib PROPERTIES
    COMPILE_FLAGS "-Wall -Wextra"
)

# Propriedade moderna (target_compile_options)
target_compile_options(mylib PRIVATE -Wall -Wextra)
```

**Recomendacao de seguranca**: prefira propriedades de target sobre variaveis globais. Propriedades sao rastreaveis e afetam apenas o target especifico.

### 9.7 Cache e seguranca

O cache do CMake contem informacoes sensiveis:

```cmake
# NUNCA coloque chaves de API ou senhas no cache
# ERRADO
set(API_KEY "abc123" CACHE STRING "API key")

# CORRETO
set(API_KEY "" CACHE STRING "API key")
# Defina via variavel de ambiente em CI:
# export API_KEY=abc123
# cmake -B build -DAPI_KEY=$API_KEY
```

**Regras de seguranca para cache**:

1. Nunca commite `CMakeCache.txt` no repositorio
2. Nunca armazene credenciais no cache
3. Use variaveis de ambiente para dados sensiveis
4. Em CI/CD, sempre defina cache explicitamente
5. Use `FORCE` com cuidado — pode sobrescrever configuracoes do usuario

---

## 10. Comandos fundamentais

### 10.1 add_executable

O comando mais basico para criar um executavel:

```cmake
add_executable(meuprodigo
    src/main.cpp
    src/utils.cpp
    src/config.cpp
)
```

**Variantes**:

```cmake
# Executavel importado (pre-compilado)
add_executable(meuprodigo IMPORTED)
set_target_properties(meuprodigo PROPERTIES
    IMPORTED_LOCATION "/usr/bin/meuprodigo"
)

# Executavel ALIAS
add_executable(MyProject::App ALIAS meuprodigo)

# Executavel de teste (CTEST)
add_executable(teste_core
    test/teste_core.cpp
)
add_test(NAME teste_core COMMAND teste_core)
```

### 10.2 add_library

```cmake
# Biblioteca estatica
add_library(mylib STATIC
    src/core.cpp
    src/utils.cpp
)

# Biblioteca compartilhada
add_library(mylib SHARED
    src/core.cpp
    src/utils.cpp
)

# Biblioteca de modulos (plugins)
add_library(myplugin MODULE
    src/plugin.cpp
)

# Biblioteca interface (headers only)
add_library(myheaders INTERFACE)

# Biblioteca OBJECT
add_library(myobj OBJECT
    src/core.cpp
)
```

**Variante IMPORTED**:

```cmake
# Biblioteca de sistema
add_library(ZLIB::ZLIB IMPORTED)
set_target_properties(ZLIB::ZLIB PROPERTIES
    IMPORTED_LOCATION "/usr/lib/x86_64-linux-gnu/libz.so"
    INTERFACE_INCLUDE_DIRECTORIES "/usr/include"
)
```

**Variante ALIAS**:

```cmake
# Criar alias para padronizacao de nomes
add_library(MyProject::Core ALIAS mycore)
add_library(MyProject::Utils ALIAS myutils)
```

### 10.3 target_link_libraries

O comando mais importante para definir dependencias:

```cmake
# Sintaxe moderna (recomendada)
target_link_libraries(meuprodigo
    PRIVATE
        MyProject::Core
        MyProject::Utils
    PUBLIC
        MyProject::API
    INTERFACE
        MyProject::Headers
)
```

**Niveis de visibilidade**:

- `PRIVATE`: dependencia usada apenas na compilacao deste target
- `PUBLIC`: dependencia propagada para targets que consomem este target
- `INTERFACE`: dependencia propagada mas nao usada pelo proprio target

```cmake
# Exemplo pratico
add_library(mycore STATIC src/core.cpp)

target_link_libraries(mycore
    PRIVATE
        OpenSSL::SSL          # Usado apenas internamente
        Threads::Threads      # Usado apenas internamente
    PUBLIC
        MyProject::Headers   # Propagado para quem usar mycore
)

add_executable(meuprodigo src/main.cpp)

target_link_libraries(meuprodigo
    PRIVATE
        mycore               # Transitivamente recebe Headers
)
```

**Por que visibilidade importa para seguranca**:

- `PRIVATE` minimiza a superficie de ataque
- `PUBLIC` pode expor dependencias sensiveis para outros targets
- `INTERFACE` deve ser usado com cuidado — pode propagar configuracoes perigosas

### 10.4 target_include_directories

```cmake
# Inclusoes para o proprio target
target_include_directories(mylib
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Inclusoes publicas (propagadas)
target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Inclusoes do sistema (suprimem warnings)
target_include_directories(mylib
    SYSTEM
        PRIVATE
            /usr/include/openssl
)
```

**Generator expressions** (`$<...>`):

- `$<BUILD_INTERFACE:path>`: aplica apenas durante o build (nao no install)
- `$<INSTALL_INTERFACE:path>`: aplica apenas apos o install
- `SYSTEM`: marca o diretorio como de sistema (suprime warnings)

### 10.5 target_compile_options

```cmake
# Opcoes de compilacao
target_compile_options(meuprodigo
    PRIVATE
        -Wall
        -Wextra
        -Werror
        -Wpedantic
)

# Opcoes especificas por compilador
target_compile_options(meuprodigo
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wno-unused-parameter>
        $<$<CXX_COMPILER_ID:Clang>:-Wmost>
        $<$<CXX_COMPILER_ID:MSVC>:/W4>
)

# Opcoes por build type
target_compile_options(meuprodigo
    PRIVATE
        $<$<CONFIG:Debug>:-O0 -g>
        $<$<CONFIG:Release>:-O3>
)
```

### 10.6 target_compile_definitions

```cmake
# Definicoes de preprocessador
target_compile_definitions(mylib
    PRIVATE
        MYLIB_INTERNAL=1
        _USE_MATH_DEFINES
)

# Definicoes com valores
target_compile_definitions(mylib
    PRIVATE
        VERSION_MAJOR=${PROJECT_VERSION_MAJOR}
        VERSION_MINOR=${PROJECT_VERSION_MINOR}
        VERSION_PATCH=${PROJECT_VERSION_PATCH}
)

# Definicoes por plataforma
target_compile_definitions(mylib
    PRIVATE
        $<$<PLATFORM_ID:Linux>:PLATFORM_LINUX>
        $<$<PLATFORM_ID:Windows>:PLATFORM_WINDOWS>
        $<$<PLATFORM_ID:Darwin>:PLATFORM_MACOS>
)
```

### 10.7 target_compile_features

```cmake
# Requisitos de linguagem modernos
target_compile_features(mylib
    PUBLIC
        cxx_std_17
)

# Para C
target_compile_features(mylib
    PUBLIC
        c_std_11
)
```

`target_compile_features` e preferivel a `set(CMAKE_CXX_STANDARD ...)` porque:

- E propagado corretamente via PUBLIC/PRIVATE/INTERFACE
- Funciona com targets IMPORTED e ALIAS
- E mais granular que variaveis globais

### 10.8 set_target_properties

```cmake
set_target_properties(mylib PROPERTIES
    # Propriedades de build
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED ON
    CXX_EXTENSIONS OFF

    # Output
    OUTPUT_NAME "mylib"
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}

    # Visibilidade
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON

    # Posicao independente
    POSITION_INDEPENDENT_CODE ON

    # LTO
    INTERPROCEDURAL_OPTIMIZATION_RELEASE ON

    # Sufixo por build type
    DEBUG_POSTFIX "_d"

    # Build directory
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
    ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib
)
```

### 10.9 add_subdirectory

```cmake
# Incluir subdiretorio
add_subdirectory(src)

# Com condicao
if(MEUPROJETO_BUILD_TESTS)
    add_subdirectory(test)
endif()

# Com alias para o subdiretorio
add_subdirectory(third_party/googletest EXCLUDE_FROM_ALL)
```

`EXCLUDE_FROM_ALL` e importante porque:

- Impede que dependencias de terceiros sejam instaladas junto
- Evita conflitos com pacotes do sistema
- Reduz o tempo de build

### 10.10 include_directories (DEPRECATED)

```cmake
# NAO RECOMENDADO — afeta todos os targets no diretorio
include_directories(${CMAKE_SOURCE_DIR}/include)
```

Este comando e considerado deprecated para uso moderno. Use `target_include_directories` em seu lugar. A diferenca e que `include_directories` afeta TODOS os targets no diretorio, incluindo bibliotecas de terceiros.

---

## 11. Include directories, compile definitions e compile options

### 11.1 Gerenciamento de headers

#### Estrutura recomendada

```
meu-projeto/
  include/
    meu-projeto/
      module_a.h       # Header publico do modulo A
      module_b.h       # Header publico do modulo B
  src/
    module_a/
      module_a.cpp     # Implementacao do modulo A
      module_a_p.h     # Header privado do modulo A
    module_b/
      module_b.cpp
      module_b_p.h
```

**Regra**: headers publicos ficam em `include/`, headers privados ficam junto com a implementacao em `src/`.

#### Configuracao de include directories

```cmake
# Headers publicos (propagados)
target_include_directories(module_a
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Headers privados (nao propagados)
target_include_directories(module_a
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
)

# Headers de sistema (suprimem warnings)
target_include_directories(module_a
    SYSTEM
        PRIVATE
            ${OPENSSL_INCLUDE_DIR}
)
```

**Por que `$<BUILD_INTERFACE>` e `$<INSTALL_INTERFACE>` importam**:

Durante o build, os headers estao no diretorio fonte. Apos o install, estao no destino de instalacao. Sem estas expressoes, o build quebra apos o install porque os caminhos mudam.

### 11.2 Compile definitions

Definicoes de preprocessador controlam o comportamento do codigo em tempo de compilacao:

```cmake
# Definicoes basicas
target_compile_definitions(mylib
    PRIVATE
        MYLIB_BUILD=1
        NDEBUG=$<IF:$<CONFIG:Debug>,0,1>
)

# Definicoes de seguranca
target_compile_definitions(mylib
    PRIVATE
        _FORTIFY_SOURCE=2
        _GLIBCXX_ASSERTIONS
)

# Definicoes condicionais
option(USE_OPENSSL "Usar OpenSSL" ON)
if(USE_OPENSSL)
    target_compile_definitions(mylib
        PRIVATE
            MYLIB_USE_OPENSSL=1
    )
endif()

# Definicoes por plataforma
target_compile_definitions(mylib
    PRIVATE
        $<$<PLATFORM_ID:Windows>:_CRT_SECURE_NO_WARNINGS>
        $<$<PLATFORM_ID:Linux>:_POSIX_C_SOURCE=200809L>
)
```

**Implicacoes de seguranca**:

- `_FORTIFY_SOURCE=2`: ativa verificacoes de buffer overflow em funcoes de string
- `_GLIBCXX_ASSERTIONS`: habilita verificacoes extras no libstdc++
- `_CRT_SECURE_NO_WARNINGS`: desabilita warnings de seguranca no MSVC (use com cuidado)
- `NDEBUG`: desabilita asserts — pode esconder bugs em producao

### 11.3 Compile options

Opcoes de compilacao controlam o comportamento do compilador:

```cmake
# Warnings (recomendado para todos os projetos)
target_compile_options(mylib
    PRIVATE
        # GCC/Clang
        $<$<CXX_COMPILER_ID:GNU,Clang>:
            -Wall
            -Wextra
            -Wpedantic
            -Wshadow
            -Wconversion
            -Wsign-conversion
            -Wdouble-promotion
            -Wformat=2
            -Wformat-security
            -Wnull-dereference
            -Wimplicit-fallthrough
            -Wstack-protector
        >
        # Clang especifico
        $<$<CXX_COMPILER_ID:Clang>:
            -Wmost
            -Wno-c99-extensions
        >
        # MSVC
        $<$<CXX_COMPILER_ID:MSVC>:
            /W4
            /w14242
            /w14254
            /w14263
            /w14265
            /w14287
            /we4289
            /w14296
            /w14311
            /w14545
            /w14546
            /w14547
            /w14549
            /w14555
            /w14619
            /w14640
            /w14826
            /w14905
            /w14906
            /w14928
        >
)

# Opcoes de seguranca (serao detalhadas no Capitulo 04)
target_compile_options(mylib
    PRIVATE
        $<$<AND:$<CXX_COMPILER_ID:GNU,Clang>,$<NOT:$<STREQUAL:${CMAKE_SYSTEM_NAME},Windows>>:-fstack-protector-strong>
        -fstack-protector-strong
        $<$<CXX_COMPILER_ID:GNU,Clang>:-fPIE>
)
```

### 11.4 Target properties avancadas

```cmake
add_executable(meuprodigo src/main.cpp)

# Propriedades de output
set_target_properties(meuprodigo PROPERTIES
    OUTPUT_NAME "mp"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    RUNTIME_OUTPUT_DIRECTORY_DEBUG "${CMAKE_BINARY_DIR}/bin/Debug"
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_BINARY_DIR}/bin/Release"
)

# Propriedades de linking
set_target_properties(meuprodigo PROPERTIES
    LINK_FLAGS "-Wl,--no-undefined"
    LINK_SEARCH_DIRECTORIES_STATIC TRUE
)

# Propriedades de install
install(TARGETS meuprodigo
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

# Propriedades de export
install(TARGETS meuprodigo
    EXPORT MeuProjetoTargets
)
```

---

## 12. Exemplo completo

### 12.1 Estrutura do projeto

```
meu-servidor/
  CMakeLists.txt
  cmake/
    CompilerWarnings.cmake
  include/
    meu-servidor/
      server.h
      config.h
      logger.h
  src/
    main.cpp
    server.cpp
    config.cpp
    logger.cpp
  test/
    CMakeLists.txt
    test_config.cpp
    test_logger.cpp
  CMakePresets.json
  .gitignore
```

### 12.2 CMakeLists.txt raiz

```cmake
cmake_minimum_required(VERSION 3.20)

project(MeuServidor
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Servidor seguro com CMake moderno"
)

# ============================================================
# Prevencao de in-source build
# ============================================================
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR
        "Construcao na fonte nao e permitida. "
        "Crie um diretorio de build: cmake -B build"
    )
endif()

# ============================================================
# Configuracoes globais
# ============================================================
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Exportar compile_commands.json para ferramentas
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Default build type
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY
        STRINGS Debug Release RelWithDebInfo MinSizeRel
    )
endif()

# ============================================================
# Opcoes do projeto
# ============================================================
option(MEUSERVidor_BUILD_TESTS "Construir testes" ON)
option(MEUSERVidor_ENABLE_SANITIZERS "Habilitar sanitizers" OFF)
option(MEUSERVidor_ENABLE_WARNINGS "Habilitar warnings rigorosos" ON)

# ============================================================
# Warnings centrais
# ============================================================
include(cmake/CompilerWarnings.cmake)

# ============================================================
# Targets
# ============================================================
add_subdirectory(src)

# ============================================================
# Testes
# ============================================================
if(MEUSERVidor_BUILD_TESTS)
    enable_testing()
    add_subdirectory(test)
endif()
```

### 12.3 src/CMakeLists.txt

```cmake
# ============================================================
# Biblioteca core
# ============================================================
add_library(meuservidor_core STATIC
    server.cpp
    config.cpp
    logger.cpp
)

target_include_directories(meuservidor_core
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_features(meuservidor_core
    PUBLIC cxx_std_17
)

target_compile_definitions(meuservidor_core
    PRIVATE
        MEUSERVidor_BUILD=1
        _FORTIFY_SOURCE=2
)

# ============================================================
# Executavel principal
# ============================================================
add_executable(meuservidor
    main.cpp
)

target_link_libraries(meuservidor
    PRIVATE
        meuservidor_core
        Threads::Threads
)

# ============================================================
# Threads (necessario para servidor)
# ============================================================
find_package(Threads REQUIRED)
```

### 12.4 cmake/CompilerWarnings.cmake

```cmake
# ============================================================
# Compiler Warnings — configuracao centralizada
# ============================================================

if(NOT MEUSERVidor_ENABLE_WARNINGS)
    return()
endif()

# Funcao para adicionar warnings a um target
function(meuservidor_set_warnings target)
    target_compile_options(${target}
        PRIVATE
            $<$<CXX_COMPILER_ID:GNU,Clang>:
                -Wall
                -Wextra
                -Wpedantic
                -Wshadow
                -Wconversion
                -Wformat=2
                -Wformat-security
                -Wnull-dereference
                -Wimplicit-fallthrough
                -Wstack-protector
                -Wstrict-aliasing=2
                -Wold-style-cast
                -Woverloaded-virtual
                -Wnon-virtual-dtor
                -Wcast-align
                -Wuseless-cast
                -Wdouble-promotion
            >
            $<$<CXX_COMPILER_ID:Clang>:
                -Weverything
                -Wno-c++98-compat
                -Wno-c++98-compat-pedantic
                -Wno-padded
                -Wno-exit-time-destructors
                -Wno-global-constructors
            >
            $<$<CXX_COMPILER_ID:MSVC>:
                /W4
                /permissive-
                /w14242
                /w14254
                /w14263
                /w14265
                /w14287
                /we4289
                /w14296
                /w14311
                /w14545
                /w14546
                /w14547
                /w14549
                /w14555
                /w14619
                /w14640
                /w14826
                /w14905
                /w14906
                /w14928
            >
    )
endfunction()
```

### 12.5 test/CMakeLists.txt

```cmake
# ============================================================
# Google Test
# ============================================================
include(FetchContent)

FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)

FetchContent_MakeAvailable(googletest)

# ============================================================
# Funcao auxiliar para testes
# ============================================================
function(meuservidor_add_test name)
    add_executable(${name} ${name}.cpp)
    target_link_libraries(${name}
        PRIVATE
            meuservidor_core
            GTest::gtest_main
    )
    add_test(NAME ${name} COMMAND ${name})
endfunction()

# ============================================================
# Testes
# ============================================================
meuservidor_add_test(test_config)
meuservidor_add_test(test_logger)
```

### 12.6 CMakePresets.json

```json
{
    "version": 3,
    "cmakeMinimumRequired": {
        "major": 3,
        "minor": 20,
        "patch": 0
    },
    "configurePresets": [
        {
            "name": "default",
            "displayName": "Default (Ninja, Release)",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_CXX_STANDARD": "17",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "MEUSERVidor_BUILD_TESTS": "ON",
                "MEUSERVidor_ENABLE_WARNINGS": "ON"
            }
        },
        {
            "name": "debug",
            "displayName": "Debug (Ninja, Debug)",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build-debug",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_CXX_STANDARD": "17",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "MEUSERVidor_BUILD_TESTS": "ON",
                "MEUSERVidor_ENABLE_WARNINGS": "ON"
            }
        },
        {
            "name": "secure",
            "displayName": "Secure (Ninja, RelWithDebInfo + Sanitizers)",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build-secure",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "RelWithDebInfo",
                "CMAKE_CXX_STANDARD": "20",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "MEUSERVidor_BUILD_TESTS": "ON",
                "MEUSERVidor_ENABLE_WARNINGS": "ON",
                "MEUSERVidor_ENABLE_SANITIZERS": "ON"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "default",
            "configurePreset": "default"
        },
        {
            "name": "debug",
            "configurePreset": "debug"
        },
        {
            "name": "secure",
            "configurePreset": "secure"
        }
    ],
    "testPresets": [
        {
            "name": "default",
            "configurePreset": "default",
            "output": {
                "outputOnFailure": true
            }
        }
    ]
}
```

### 12.7 .gitignore

```gitignore
# Build directories
build/
build-*/
build_*/

# CMake generated files
CMakeCache.txt
CMakeFiles/
cmake_install.cmake
Makefile
compile_commands.json
CTestTestfile.cmake
Testing/
install_manifest.txt

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# Binarios
*.o
*.so
*.dylib
*.dll
*.a
*.lib
*.exe
```

### 12.8 Fontes completas do projeto

#### include/meu-servidor/server.h

```cpp
#ifndef MEU_SERVIDOR_SERVER_H
#define MEU_SERVIDOR_SERVER_H

#include <string>
#include <functional>
#include <memory>

namespace meu_servidor {

class Config;

class Server {
public:
    explicit Server(const Config& config);
    ~Server();

    Server(const Server&) = delete;
    Server& operator=(const Server&) = delete;

    bool start();
    void stop();
    bool is_running() const;

    void set_request_handler(std::function<void(const std::string&)> handler);

private:
    struct Impl;
    std::unique_ptr<Impl> pimpl_;
};

} // namespace meu_servidor

#endif // MEU_SERVIDOR_SERVER_H
```

#### include/meu-servidor/config.h

```cpp
#ifndef MEU_SERVIDOR_CONFIG_H
#define MEU_SERVIDOR_CONFIG_H

#include <string>
#include <cstdint>

namespace meu_servidor {

struct Config {
    std::string host = "0.0.0.0";
    uint16_t port = 8080;
    int max_connections = 100;
    bool enable_logging = true;
    std::string log_level = "info";
};

Config load_config(const std::string& filepath);
Config default_config();

} // namespace meu_servidor

#endif // MEU_SERVIDOR_CONFIG_H
```

#### include/meu-servidor/logger.h

```cpp
#ifndef MEU_SERVIDOR_LOGGER_H
#define MEU_SERVIDOR_LOGGER_H

#include <string>
#include <fstream>
#include <mutex>

namespace meu_servidor {

enum class LogLevel {
    Debug,
    Info,
    Warning,
    Error
};

class Logger {
public:
    explicit Logger(LogLevel min_level = LogLevel::Info);
    ~Logger();

    void set_log_file(const std::string& filepath);

    void debug(const std::string& message);
    void info(const std::string& message);
    void warning(const std::string& message);
    void error(const std::string& message);

    static Logger& instance();
    static void initialize(LogLevel level);

private:
    void log(LogLevel level, const std::string& message);
    std::string level_to_string(LogLevel level) const;

    LogLevel min_level_;
    std::ofstream log_file_;
    std::mutex mutex_;
};

} // namespace meu_servidor

#endif // MEU_SERVIDOR_LOGGER_H
```

#### src/server.cpp

```cpp
#include "meu-servidor/server.h"
#include "meu-servidor/config.h"
#include "meu-servidor/logger.h"

#include <atomic>
#include <thread>
#include <vector>
#include <functional>

namespace meu_servidor {

struct Server::Impl {
    Config config;
    std::atomic<bool> running{false};
    std::vector<std::thread> workers;
    std::function<void(const std::string&)> request_handler;

    explicit Impl(const Config& cfg) : config(cfg) {}
};

Server::Server(const Config& config)
    : pimpl_(std::make_unique<Impl>(config)) {
    Logger::instance().info("Servidor criado em " + config.host +
                           ":" + std::to_string(config.port));
}

Server::~Server() {
    stop();
}

bool Server::start() {
    if (pimpl_->running.load()) {
        Logger::instance().warning("Servidor ja esta rodando");
        return false;
    }

    pimpl_->running.store(true);
    Logger::instance().info("Servidor iniciado na porta " +
                           std::to_string(pimpl_->config.port));
    return true;
}

void Server::stop() {
    if (!pimpl_->running.load()) {
        return;
    }

    pimpl_->running.store(false);

    for (auto& worker : pimpl_->workers) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    pimpl_->workers.clear();
    Logger::instance().info("Servidor parado");
}

bool Server::is_running() const {
    return pimpl_->running.load();
}

void Server::set_request_handler(
    std::function<void(const std::string&)> handler) {
    pimpl_->request_handler = std::move(handler);
}

} // namespace meu_servidor
```

#### src/config.cpp

```cpp
#include "meu-servidor/config.h"
#include "meu-servidor/logger.h"

#include <fstream>
#include <sstream>
#include <stdexcept>

namespace meu_servidor {

Config load_config(const std::string& filepath) {
    Config config;

    std::ifstream file(filepath);
    if (!file.is_open()) {
        Logger::instance().warning(
            "Arquivo de configuracao nao encontrado: " + filepath +
            " — usando configuracao padrao");
        return default_config();
    }

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') {
            continue;
        }

        auto pos = line.find('=');
        if (pos == std::string::npos) {
            continue;
        }

        std::string key = line.substr(0, pos);
        std::string value = line.substr(pos + 1);

        // Remover espacos
        key.erase(0, key.find_first_not_of(" \t"));
        key.erase(key.find_last_not_of(" \t") + 1);
        value.erase(0, value.find_first_not_of(" \t"));
        value.erase(value.find_last_not_of(" \t") + 1);

        if (key == "host") {
            config.host = value;
        } else if (key == "port") {
            config.port = static_cast<uint16_t>(std::stoi(value));
        } else if (key == "max_connections") {
            config.max_connections = std::stoi(value);
        } else if (key == "enable_logging") {
            config.enable_logging = (value == "true" || value == "1");
        } else if (key == "log_level") {
            config.log_level = value;
        }
    }

    return config;
}

Config default_config() {
    return Config{};
}

} // namespace meu_servidor
```

#### src/logger.cpp

```cpp
#include "meu-servidor/logger.h"

#include <iostream>
#include <chrono>
#include <iomanip>
#include <ctime>

namespace meu_servidor {

Logger::Logger(LogLevel min_level)
    : min_level_(min_level) {}

Logger::~Logger() {
    if (log_file_.is_open()) {
        log_file_.close();
    }
}

void Logger::set_log_file(const std::string& filepath) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (log_file_.is_open()) {
        log_file_.close();
    }
    log_file_.open(filepath, std::ios::app);
}

void Logger::debug(const std::string& message) {
    log(LogLevel::Debug, message);
}

void Logger::info(const std::string& message) {
    log(LogLevel::Info, message);
}

void Logger::warning(const std::string& message) {
    log(LogLevel::Warning, message);
}

void Logger::error(const std::string& message) {
    log(LogLevel::Error, message);
}

Logger& Logger::instance() {
    static Logger instance;
    return instance;
}

void Logger::initialize(LogLevel level) {
    instance().min_level_ = level;
}

void Logger::log(LogLevel level, const std::string& message) {
    if (level < min_level_) {
        return;
    }

    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);

    std::lock_guard<std::mutex> lock(mutex_);

    std::tm tm_buf{};
    localtime_r(&time, &tm_buf);

    std::ostringstream oss;
    oss << std::put_time(&tm_buf, "%Y-%m-%d %H:%M:%S")
        << " [" << level_to_string(level) << "] "
        << message;

    std::string formatted = oss.str();

    if (log_file_.is_open()) {
        log_file_ << formatted << "\n";
        log_file_.flush();
    }

    if (level >= LogLevel::Warning) {
        std::cerr << formatted << "\n";
    } else {
        std::clog << formatted << "\n";
    }
}

std::string Logger::level_to_string(LogLevel level) const {
    switch (level) {
        case LogLevel::Debug:   return "DEBUG";
        case LogLevel::Info:    return "INFO";
        case LogLevel::Warning: return "WARN";
        case LogLevel::Error:   return "ERROR";
    }
    return "UNKNOWN";
}

} // namespace meu_servidor
```

#### src/app/main.cpp

```cpp
#include "meu-servidor/server.h"
#include "meu-servidor/config.h"
#include "meu-servidor/logger.h"

#include <iostream>
#include <signal.h>
#include <atomic>

static std::atomic<bool> g_running{true};

void signal_handler(int /*signum*/) {
    g_running.store(false);
}

int main(int argc, char* argv[]) {
    std::string config_file = "servidor.conf";
    if (argc > 1) {
        config_file = argv[1];
    }

    auto config = meu_servidor::load_config(config_file);

    meu_servidor::Logger::initialize(
        config.enable_logging ? meu_servidor::LogLevel::Info
                             : meu_servidor::LogLevel::Error
    );

    meu_servidor::Server server(config);

    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);

    if (!server.start()) {
        std::cerr << "Falha ao iniciar servidor\n";
        return 1;
    }

    std::cout << "Servidor rodando. Pressione Ctrl+C para parar.\n";

    while (g_running.load()) {
        // Simulacao de loop principal do servidor
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    server.stop();
    return 0;
}
```

#### test/test_config.cpp

```cpp
#include <gtest/gtest.h>
#include "meu-servidor/config.h"

TEST(ConfigTest, DefaultConfig) {
    auto config = meu_servidor::default_config();
    EXPECT_EQ(config.host, "0.0.0.0");
    EXPECT_EQ(config.port, 8080);
    EXPECT_EQ(config.max_connections, 100);
    EXPECT_TRUE(config.enable_logging);
}

TEST(ConfigTest, MissingFileReturnsDefault) {
    auto config = meu_servidor::load_config("nonexistent.conf");
    EXPECT_EQ(config.port, 8080);
}

TEST(ConfigTest, CustomPort) {
    auto config = meu_servidor::default_config();
    config.port = 9090;
    EXPECT_EQ(config.port, 9090);
}
```

#### test/test_logger.cpp

```cpp
#include <gtest/gtest.h>
#include "meu-servidor/logger.h"

TEST(LoggerTest, SingletonInstance) {
    auto& logger1 = meu_servidor::Logger::instance();
    auto& logger2 = meu_servidor::Logger::instance();
    EXPECT_EQ(&logger1, &logger2);
}

TEST(LoggerTest, SetLogFile) {
    auto& logger = meu_servidor::Logger::instance();
    // Nao deve lancar excecao
    logger.set_log_file("/tmp/test_logger.log");
}
```

### 12.9 Instrucoes de uso

```bash
# Configurar (usando preset)
cmake --preset default

# Compilar
cmake --build --preset default

# Rodar testes
ctest --preset default

# Configuracao segura (com sanitizers)
cmake --preset secure
cmake --build --preset secure
ctest --preset secure

# Build manual (sem presets)
cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build

# Executar o servidor
./build/bin/meuservidor

# Executar com arquivo de configuracao
./build/bin/meuservidor /caminho/para/servidor.conf
```

---

## 13. Exercicios

### Exercicio 1: CMakeLists.txt basico (facil)

Crie um projeto com a seguinte estrutura:

```
exercicio1/
  CMakeLists.txt
  main.cpp
```

O `CMakeLists.txt` deve:

1. Exigir CMake 3.20+
2. Declarar o projeto com nome, versao e linguagem
3. Criar um executavel de `main.cpp`
4. Configurar `CMAKE_CXX_STANDARD` para C++17

```cpp
// main.cpp
#include <iostream>
#include <string>

int main() {
    std::string nome = "CMake Moderno";
    std::cout << "Bem-vindo ao " << nome << "!" << std::endl;
    return 0;
}
```

**Solucao esperada**:

```cmake
cmake_minimum_required(VERSION 3.20)

project(Exercicio1
    VERSION 1.0.0
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(exercicio1 main.cpp)
```

### Exercicio 2: Biblioteca e executavel (medio)

Crie um projeto com:

```
exercicio2/
  CMakeLists.txt
  src/
    CMakeLists.txt
    main.cpp
    mathutils.cpp
  include/
    exercicio2/
      mathutils.h
```

Requisitos:

1. `mathutils.h` declara funcoes `soma`, `subtrai`, `multiplica`
2. `mathutils.cpp` implementa as funcoes
3. A biblioteca deve ser `PUBLIC` em `target_include_directories`
4. O executavel linka contra a biblioteca

**Solucao esperada**:

```cmake
# exercicio2/CMakeLists.txt
cmake_minimum_required(VERSION 3.20)

project(Exercicio2 VERSION 1.0.0 LANGUAGES CXX)

add_subdirectory(src)
```

```cmake
# exercicio2/src/CMakeLists.txt
add_library(mathutils STATIC
    mathutils.cpp
)

target_include_directories(mathutils
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

add_executable(exercicio2 main.cpp)
target_link_libraries(exercicio2 PRIVATE mathutils)
```

### Exercicio 3: Build types e opcoes (medio)

Modifique o exercicio 2 para:

1. Adicionar uma opcao `ENABLE_TESTING`
2. Configurar build types com valores padrao
3. Adicionar warnings como `PRIVATE` do target
4. Criar um `CMakePresets.json` com presets para Debug, Release e Secure

### Exercicio 4: Variaveis e cache (dificil)

Crie um `CMakeLists.txt` que:

1. Defina uma variavel de cache `MY_APP_VERSION` com valor padrao "0.0.1"
2. Permita sobrescrever via linha de comando
3. Use a variavel como definicao de preprocessador
4. Imprima informacoes do compilador e plataforma
5. Condicione o comportamento baseado no build type

```cmake
cmake_minimum_required(VERSION 3.20)

project(Exercicio4 VERSION 1.0.0 LANGUAGES CXX)

# Variavel de cache
set(MY_APP_VERSION "0.0.1" CACHE STRING "Versao da aplicacao")

# Informacoes do compilador
message(STATUS "Compilador: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "Plataforma: ${CMAKE_SYSTEM_NAME}")
message(STATUS "Processador: ${CMAKE_SYSTEM_PROCESSOR}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
message(STATUS "Versao do app: ${MY_APP_VERSION}")

# Definicao de preprocessador
add_executable(exercicio4 main.cpp)
target_compile_definitions(exercicio4
    PRIVATE
        APP_VERSION="${MY_APP_VERSION}"
)
```

### Exercicio 5: Projeto completo (dificil)

Crie um projeto completo com:

```
exercicio5/
  CMakeLists.txt
  cmake/
    CompilerWarnings.cmake
  src/
    CMakeLists.txt
    core/
      CMakeLists.txt
      calculator.cpp
      calculator.h
    app/
      CMakeLists.txt
      main.cpp
  test/
    CMakeLists.txt
    test_calculator.cpp
```

Requisitos:

1. `calculator` e uma biblioteca STATIC
2. `exercicio5` e o executavel que usa a biblioteca
3. Warnings sao centralizados em `cmake/CompilerWarnings.cmake`
4. Testes usam GoogleTest via FetchContent
5. O `CMakeLists.txt` raiz previne in-source build
6. Build types Default e Debug estao configurados

### Exercicio 6: Visibilidade de simbolos (dificil)

Crie um projeto com uma biblioteca compartilhada que:

1. Tenha todos os simbolos ocultos por padrao
2. Exporte apenas funcoes marcadas com uma macro `EXPORT`

```cpp
// export.h
#ifdef _WIN32
    #ifdef MEUPROJETO_BUILD
        #define EXPORT __declspec(dllexport)
    #else
        #define EXPORT __declspec(dllimport)
    #endif
#else
    #define EXPORT __attribute__((visibility("default")))
#endif
```

```cmake
# Configuracao da biblioteca
add_library(mylib SHARED mylib.cpp)

target_compile_definitions(mylib PRIVATE MEUPROJETO_BUILD=1)

set_target_properties(mylib PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)
```

### Exercicio 7: Cross-compilation basico (dificil)

Crie um toolchain file para cross-compilation:

```cmake
# cmake/toolchain-arm64.cmake
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

Use com:

```bash
cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/toolchain-arm64.cmake
```

---

## 14. Anti-patterns comuns em CMake

### 14.1 In-source build

**Problema**: executar `cmake .` no diretorio raiz mistura arquivos gerados com codigo fonte.

```bash
# ERRADO
cd meu-projeto/
cmake .
make

# CORRETO
cd meu-projeto/
cmake -B build
cmake --build build
```

**Por que e perigoso**: arquivos de build podem conter informacoes sensiveis (paths, variaveis de ambiente). Se o diretorio de build e o mesmo da fonte, estes dados ficam expostos no repositorio.

### 14.2 Usar include_directories global

**Problema**: `include_directories()` afeta TODOS os targets no diretorio.

```cmake
# ERRADO — afeta ate bibliotecas de terceiros
include_directories(/usr/include)
include_directories(${CMAKE_SOURCE_DIR}/include)
```

**Solucao**: usar `target_include_directories()` com visibilidade explicita.

### 14.3 Link directories

**Problema**: `link_directories()` e universalmente considerado inseguro.

```cmake
# ERRADO — pode linkar bibliotecas nao intencionais
link_directories(/usr/lib)
target_link_libraries(myapp somelibrary)
```

**Solucao**: usar targets de biblioteca com `find_package()` ou `add_library()`.

### 14.4 Variaveis globais para configuracao

**Problema**: `set(CMAKE_CXX_FLAGS ...)` modifica flags para TODOS os targets.

```cmake
# ERRADO — todos os targets recebem as mesmas flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")
```

**Solucao**: usar `target_compile_options()` por target.

### 14.5 Ignorar in-source build check

```cmake
# ERRADO — nao verifica
cmake_minimum_required(VERSION 3.20)
project(MeuProjeto)
```

**Solucao**: sempre incluir a verificacao:

```cmake
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
    message(FATAL_ERROR "In-source build nao permitido")
endif()
```

### 14.6 Versao minima antiga

```cmake
# ERRADO — politicas antigas podem ser inseguras
cmake_minimum_required(VERSION 2.8)
```

**Solucao**: sempre usar 3.20+ para projetos novos.

### 14.7 Copiar flags de seguranca sem entender

```cmake
# ERRADO — flags copiadas sem contexto
target_compile_options(myapp PRIVATE -fstack-protector -fPIE)
```

**Solucao**: entender cada flag antes de usa-las (Capitulo 04 detalha cada uma).

### 14.8 Nao usar cmake_minimum_required

```cmake
# ERRADO — versao minima nao definida
project(MeuProjeto)
add_executable(meuprodigo main.cpp)
```

Sem `cmake_minimum_required`, o CMake usa comportamentos historicos que podem ser inseguros.

### 14.9 Resumo dos anti-patterns

| Anti-pattern | Problema | Solucao |
|--------------|----------|---------|
| In-source build | Poluicao, exposicao | `cmake -B build` |
| `include_directories` | Escopo global | `target_include_directories` |
| `link_directories` | Risco de linking incorreto | Targets de biblioteca |
| `set(CMAKE_CXX_FLAGS)` | Flags globais | `target_compile_options` |
| Sem version check | Comportamento antigo | `cmake_minimum_required(VERSION 3.20)` |
| Versao antiga | Politicas inseguras | Usar 3.20+ |
| Flags copiadas | Desconhecimento | Estudar cada flag |

---

## 15. Referencias

### Documentacao oficial

- **CMake Documentation**: https://cmake.org/cmake/help/latest/
- **CMake Tutorial**: https://cmake.org/cmake/help/latest/guide/tutorial/index.html
- **CMake Presets**: https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html
- **CMake Policy Reference**: https://cmake.org/cmake/help/latest/manual/cmake-policies.7.html
- **Generator Expressions**: https://cmake.org/cmake/help/latest/manual/cmake-generator-expressions.7.html

### Livros e artigos

- **"Mastering CMake"** — Kitware, Inc. (o referencia definitivo)
- **"Modern CMake"** by Jason Turner — https://gist.github.com/mbinna/c61dbb39bca0e4fb7d1f73b0d66a4fd1
- **"How to CMake Good"** — https://github.com/vectorclass/version-benchmark/blob/master/CMakeGood.md
- **"Effective Modern CMake"** — https://gist.github.com/mbinna/c61dbb39bca0e4fb7d1f73b0d66a4fd1
- **"An Introduction to Modern CMake"** by Henry Schreiner — https://cliutils.gitlab.io/modern-cmake/

### Projetos de referencia

- **LLVM/Clang**: https://github.com/llvm/llvm-project (CMake complexo e maduro)
- **Qt**: https://code.qt.io/cmake/qt-cmake-manual.html (migracao para CMake moderno)
- **OpenCV**: https://github.com/opencv/opencv (CMake para projetos grandes)
- **spdlog**: https://github.com/gabime/spdlog (exemplo de FetchContent)

### Ferramentas

- **cmake-lint**: https://github.com/cheshirekow/cmake-lint (linting de CMakeLists.txt)
- **cmake-format**: https://github.com/cheshirekow/cmake-format (formatacao)
- **cmake-init**: https://github.com/friendlyanon/cmake-init (scaffolding de projetos)
- **compiledb**: https://github.com/nicktimko/compiledb (geracao de compile_commands.json)

### Seguranca

- **OWASP Build Security**: https://owasp.org/www-project-dependency-check/
- **CWE-506**: Embedded Malicious Code
- **CWE-829**: Inclusion of Functionality from Untrusted Control Sphere
- **SLSA Framework**: https://slsa.dev/spec/v1.0/framework
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Target Model Properties](02-target-model-properties.md)*
