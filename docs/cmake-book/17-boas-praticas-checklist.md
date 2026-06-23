---
layout: default
title: "Boas Praticas e Checklist"
---

# Capitulo 17 — Boas Praticas e Checklist

> *"Checklists nao substituem conhecimento — elas garantem que voce nao esqueca o que ja sabe quando o cansaco aperta."*

---

## 17.1 Objetivos de Aprendizado

Apos completar este capitulo, voce sera capaz de:

- Identificar e corrigir 20+ anti-patterns comuns em CMake
- Aplicar um checklist completo de seguranca no build system
- Escolher o gerador certo, o package manager certo, e a estrategia de deps certa
- Migrar projetos CMake antigo (CMake 2.x/3.0) para modern CMake (3.15+)
- Usar templates seguros para CMakeLists.txt, toolchains, presets, e CI
- Consultar referencias rapidas de flags e propriedades por compilador
- Consolidar conhecimento com exercicios praticos

### Por Que Este Capitulo Existe

Na pratica, a maioria dos problemas em build systems de C/C++ vem de dois lugares: (1) copiar e colar solucoes sem entender o por que, e (2) nao ter um processo consistente. Este capitulo e o "ultimo barril" — tudo que voce aprendeu nos 16 capitulos anteriores condensado em anti-patterns, checklists, decision trees, e templates prontos para usar.

Nao leia este capitulo de uma vez so. Use-o como referencia: quando for criar um novo projeto, puxe o template. Quando for revisar codigo CMake existente, rode o checklist. Quando tiver uma decisao a tomar, consulte o decision tree.

---

## 17.2 Anti-Patterns em CMake com Codigo

Anti-patterns nao sao "erros" no sentido estrito — sao padroes que funcionam mas que criam manutencao, bugs, ou vulnerabilidades. Cada anti-pattern abaixo inclui o codigo problematico e a correcao.

### Anti-Pattern 1: Usar `include_directories()` globalmente

```cmake
# RUIM — afeta TODOS os targets no diretorio e subdiretorios
include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(/usr/local/include)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/third_party/openssl)

add_library(mylib src/mylib.cpp)
add_executable(myapp src/main.cpp)
```

**Por que e ruim**: Escopo global significa que qualquer target — inclusive bibliotecas de terceiros — recebem esses caminhos. Isso pode causar colisoes de nomes, inclusao acidental de headers errados, e dificulta rastrear de onde vem cada dependencia.

```cmake
# BOM — escopo por target, visibilidade explicita
add_library(mylib src/mylib.cpp)
target_include_directories(mylib
    PUBLIC
        ${PROJECT_SOURCE_DIR}/include
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/openssl
)

add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)
```

**Regra**: Nunca use `include_directories()` em projetos novos. Use sempre `target_include_directories()` com `PUBLIC` (quando consumidores precisam) ou `PRIVATE` (quando so a implementacao precisa).

---

### Anti-Pattern 2: Usar `link_directories()` globalmente

```cmake
# RUIM — diretorios de busca globais
link_directories(/opt/custom/lib)
link_directories(${CMAKE_CURRENT_BINARY_DIR}/lib)

add_executable(myapp src/main.cpp)
target_link_libraries(myapp custom_lib)
```

**Por que e ruim**: `link_directories()` e uma relquia do CMake 2.x. Ele adiciona diretorios ao linker globalmente, tornando impossivel saber qual target usa qual lib. Pior, conflita com `find_package()` e `find_library()`.

```cmake
# BOM — use caminhos absolutos ou targets importados
find_library(CUSTOM_LIB NAMES custom PATHS /opt/custom/lib)
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE ${CUSTOM_LIB})
```

**Regra**: Nunca use `link_directories()`. Use `find_library()` para obter o caminho absoluto, ou `find_package()` para obter um imported target.

---

### Anti-Pattern 3: Usar `link_libraries()` globalmente

```cmake
# RUIM — links globais
link_libraries(pthread ssl crypto)

add_executable(server src/server.cpp)
add_executable(client src/client.cpp)
```

**Por que e ruim**: Todos os targets herdam todas as bibliotecas. `client` nao precisa de `ssl` mas recebe de qualquer forma. Isso aumenta tempo de linking, torna o build fragil, e dificulta entender as dependencias reais.

```cmake
# BOM — dependencias por target
find_package(OpenSSL REQUIRED)
find_package(Threads REQUIRED)

add_executable(server src/server.cpp)
target_link_libraries(server PRIVATE OpenSSL::SSL OpenSSL::Crypto Threads::Threads)

add_executable(client src/client.cpp)
target_link_libraries(client PRIVATE Threads::Threads)
```

**Regra**: Nunca use `link_libraries()`. Use `target_link_libraries()` com targets importados sempre que possivel.

---

### Anti-Pattern 4: Hardcoding de compilador e flags

```cmake
# RUIM — quebra em qualquer ambiente diferente
set(CMAKE_CXX_FLAGS "-std=c++17 -O2 -Wall -Wextra -pedantic")
set(CMAKE_C_FLAGS "-std=c11 -O2 -Wall -Wextra")
set(CMAKE_EXE_LINKER_FLAGS "-L/usr/lib/openssl -lssl -lcrypto")
```

**Por que e ruim**: `CMAKE_CXX_FLAGS` e a versao "scream and pray" do CMake. Flags sao injetadas em TODOS os targets, incluindo bibliotecas de terceiros. `-O2` para uma lib debug? Aplicado. `-Wall` para um submodule externo? Aplicado. Pior, `-L/usr/lib/openssl` e uma porta de entrada para bibliotecas erradas.

```cmake
# BOM — propriedades por target
add_library(mylib src/mylib.cpp)
target_compile_features(mylib PUBLIC cxx_std_17)
target_compile_options(mylib PRIVATE
    $<$<CONFIG:Release>:-O2>
    $<$<AND:$<COMPILE_LANGUAGE:CXX>,$<CONFIG:Debug>>:-Wall -Wextra -pedantic>
)
```

**Regra**: Nunca modifique `CMAKE_CXX_FLAGS` diretamente. Use `target_compile_features()` para padroes da linguagem, `target_compile_options()` para flags especificas, e geradores de expressao para condicionais.

---

### Anti-Pattern 5: Usar variaveis de ambiente para paths de dependencias

```cmake
# RUIM — dependencia implicita do ambiente
set(OPENSSL_ROOT_DIR $ENV{OPENSSL_DIR})
set(BOOST_ROOT $ENV{BOOST_HOME})
find_package(OpenSSL REQUIRED)
find_package(Boost REQUIRED)
```

**Por que e ruim**: Builds nao devem depender de configuracao local do desenvolvedor. Um colega que esquece de setar a variavel tem um build quebrado sem mensagem de erro clara. CI/CD precisa lembrar de setar todas essas variaveis.

```cmake
# BOM — use presets ou toolchain files
# CMakePresets.json define os paths de forma padronizada
# Ou use find_package com paths padrao do sistema
find_package(OpenSSL 1.1.1 REQUIRED)
find_package(Boost 1.80 REQUIRED COMPONENTS filesystem system)
```

**Regra**: Dependencias devem ser resolvidas por `find_package()`, `FetchContent`, ou `pkg-config` — nao por variaveis de ambiente. Use `CMakePresets.json` para configuracoes de ambiente.

---

### Anti-Pattern 6: Nao especificar versoes de dependencias

```cmake
# RUIM — funciona hoje, quebra amanha
find_package(OpenSSL REQUIRED)
find_package(Boost REQUIRED)
find_package(SQLite3 REQUIRED)

# FetchContent sem versao
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        main
)
```

**Por que e ruim**: Sem versoes especificas, o build pode usar qualquer versao disponivel. `GIT_TAG main` e o pior caso — o codigo muda a cada push, builds nao sao reproduziveis, e bugs aparecem sem mudanca aparente no seu codigo.

```cmake
# BOM — versoes explicitas e ranges
find_package(OpenSSL 1.1.1...3.0.0 REQUIRED)
find_package(Boost 1.80...1.85.0 REQUIRED COMPONENTS filesystem system)
find_package(SQLite3 3.39.0 REQUIRED)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
    GIT_SHALLOW    TRUE
)
```

**Regra**: Sempre especifique versao minima. Use ranges quando possivel (CMake 3.19+). Para FetchContent, fixe o GIT_TAG em uma tag ou commit hash, nunca em branch.

---

### Anti-Pattern 7: Usar `file(GLOB ...)` para sources

```cmake
# RUIM — CMake nao sabe quando arquivos mudam
file(GLOB SOURCES "src/*.cpp" "src/*.c")
add_library(mylib ${SOURCES})
```

**Por que e ruim**: `file(GLOB)` e avaliado no configure time. Se voce adicionar um novo arquivo `.cpp`, o CMake nao vai regenerar o build. Voce precisa rodar `cmake` manualmente — e ninguem lembra disso.

```cmake
# BOM — arquivos listados explicitamente
add_library(mylib
    src/core/engine.cpp
    src/core/parser.cpp
    src/util/logger.cpp
    src/util/config.cpp
)
```

**Regra**: Liste sempre os arquivos explicitamente. Se voce tem muitos arquivos, considere um `CMakeLists.txt` por subdiretorio com seu proprio `add_library()` ou `add_executable()`.

---

### Anti-Pattern 8: Usar `CMAKE_MINIMUM_REQUIRED` antigo

```cmake
# RUIM — ativa comportamentos obsoletos
cmake_minimum_required(VERSION 2.8.12)
# OU
cmake_minimum_required(VERSION 3.0)
```

**Por que e ruim**: CMake 2.x e 3.0-3.4 tem comportamentos perigosos que nao estao presentes em versoes modernas: policies como CMP0048 (versao do projeto), CMP0063 (visibility), CMP0077 (option() com normalizacao) nao estao ativas. O resultado: codigo que funciona no seu CMake local mas quebra no CMake de outro dev ou na CI.

```cmake
# BOM — versao minima moderna, com policies explicitas
cmake_minimum_required(VERSION 3.15...3.30)
```

**Regra**: Para projetos novos em 2024+, use no minimo `3.15`. Para projetos que precisam de compatibilidade com sistemas legados, use o range `VERSION X.Y...3.30` e teste com a versao minima.

---

### Anti-Pattern 9: Usar `add_definitions()` ao inves de `target_compile_definitions()`

```cmake
# RUIM — definicoes globais
add_definitions(-DUSE_OPENSSL -DDEBUG_MODE -DVERSION="1.0")
```

**Por que e ruim**: `add_definitions()` e um wrapper antigo de `add_compile_definitions()` que afeta TODOS os targets no diretorio e subdiretorios. Define coisas para bibliotecas de terceiros que nao deviam receber essas definicoes.

```cmake
# BOM — definicoes por target
add_library(mylib src/mylib.cpp)
target_compile_definitions(mylib PRIVATE
    $<$<CONFIG:Debug>:DEBUG_MODE>
    $<$<CONFIG:Release>:NDEBUG>
)
target_compile_definitions(mylib PUBLIC USE_OPENSSL)
```

**Regra**: Nunca use `add_definitions()`. Use `target_compile_definitions()` com escopo `PRIVATE` ou `PUBLIC`.

---

### Anti-Pattern 10: Nao usar `target_link_libraries` com INTERFACE

```cmake
# RUIM — dependencias que o consumidor nao recebe
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE OpenSSL::SSL)
target_include_directories(mylib PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Consumidor nao consegue usar mylib — headers ausentes
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)  # ERRO: header not found
```

**Por que e ruim**: Quando `mylib` expoe headers publicos (em `include/`), eles precisam ser `PUBLIC` para que qualquer target que linka com `mylib` possa incluir esses headers.

```cmake
# BOM — visibilidade correta
add_library(mylib src/mylib.cpp)
target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
target_link_libraries(mylib PUBLIC OpenSSL::SSL)
```

**Regra**: Headers publicos sao `PUBLIC`. Implementacao e `PRIVATE`. Headers usados apenas no header publico sao `INTERFACE`.

---

### Anti-Pattern 11: Gerenciamento de dependencias manual com `add_subdirectory`

```cmake
# RUIM — copia toda a lib para dentro do projeto
add_subdirectory(third_party/fmt)
add_subdirectory(third_party/nlohmann_json)
add_subdirectory(third_party/spdlog)
add_subdirectory(third_party/catch2)
```

**Por que e ruim**: `add_subdirectory()` pulla o codigo-fonte completo. Isso infla o repositorio, mistura codigo proprio com terceiro, e complica updates. Pior: se uma dependencia tem um `CMakeLists.txt` mal feito, ele polui o seu namespace com targets globais e variaveis.

```cmake
# BOM — use FetchContent com versoes fixas
include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
    GIT_SHALLOW    TRUE
)

FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.11.3
    GIT_SHALLOW    TRUE
)

FetchContent_MakeAvailable(fmt nlohmann_json)
```

**Regra**: Prefira `FetchContent` sobre `add_subdirectory` para dependencias. Reserve `add_subdirectory` para componentes internos do seu projeto.

---

### Anti-Pattern 12: Nao usar generator expressions para configuracoes

```cmake
# RUIM — flags aplicadas em todas as configuracoes
target_compile_options(mylib PRIVATE -Wall -Wextra -Werror)
target_compile_options(mylib PRIVATE -O2 -DNDEBUG)
```

**Por que e ruim**: `-O2` e `-DNDEBUG` nao devem ser aplicados em Debug. `-Werror` em todas as configuracoes impede debug (warnings viram erros).

```cmake
# BOM — configuracoes especificas
target_compile_options(mylib PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-Wall -Wextra>
    $<$<COMPILE_LANGUAGE:C>:-Wall -Wextra>
    $<$<CONFIG:Release>:-O2 -DNDEBUG>
    $<$<AND:$<CONFIG:Debug>,$<COMPILE_LANGUAGE:CXX>>:-g -O0 -fsanitize=address,undefined>
)
```

**Regra**: Use generator expressions para flags que variam por configuracao, linguagem, ou plataforma.

---

### Anti-Pattern 13: Nao tratar erros de `find_package`

```cmake
# RUIM — falha silenciosa ou mensagem confusa
find_package(OpenSSL)
find_package(Boost)
find_package(SQLite3)

# Continua mesmo sem achar dependencias
add_executable(myapp src/main.cpp)
target_link_libraries(myapp OpenSSL::SSL Boost::filesystem SQLite::SQLite3)
```

**Por que e ruim**: Se `find_package()` falha e o `REQUIRED` nao esta presente, as variaveis ficam vazias. O `target_link_libraries()` vai aceitar variaveis vazias silenciosamente e gerar erros de linker obscuros.

```cmake
# BOM — REQUIRED + mensagem de erro clara
find_package(OpenSSL 1.1.1 REQUIRED
    MESSAGE "OpenSSL e obrigatorio. Instale: apt install libssl-dev"
)
find_package(Boost 1.80 REQUIRED COMPONENTS filesystem system
    MESSAGE "Boost >= 1.80 e obrigatorio com filesystem e system."
)
find_package(SQLite3 3.39.0 REQUIRED
    MESSAGE "SQLite3 >= 3.39 e obrigatorio. Instale: apt install libsqlite3-dev"
)
```

**Regra**: Sempre use `REQUIRED` para dependencias obrigatorias. Adicione `MESSAGE` para instrucoes de instalacao claras.

---

### Anti-Pattern 14: Nao padronizar o build type

```cmake
# RUIM — sem default, Debug e usado e o dev nao sabe
# Nenhum cmake_minimum_required ou set() para CMAKE_BUILD_TYPE
```

**Por que e ruim**: O padrao do CMake e "Nenhum" (vazio). Isso significa flags otimizadas NAO sao aplicadas, o build fica lento, e o dev nao entende por que o binario e enorme e lento.

```cmake
# BOM — default sensato para desenvolvimento
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Build type: Debug (default)")
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS
        Debug Release RelWithDebInfo MinSizeRel)
endif()
```

**Regra**: Sempre defina um `CMAKE_BUILD_TYPE` padrao. Para desenvolvimento, `Debug` com sanitizers. Para releases, `Release` ou `RelWithDebInfo`.

---

### Anti-Pattern 15: Nao usar `CMAKE_POSITION_INDEPENDENT_CODE`

```cmake
# RUIM — binarios de bibliotecas estaticas sem PIC
add_library(mylib STATIC src/mylib.cpp)
# Sem PIC, nao pode ser linkado em shared libraries
```

**Por que e ruim**: Bibliotecas estaticas sem PIC nao podem ser linkadas em shared libraries. Isso causa erros em multiplas plataformas, especialmente Linux x86_64.

```cmake
# BOM — PIC correto
add_library(mylib STATIC src/mylib.cpp)
set_target_properties(mylib PROPERTIES POSITION_INDEPENDENT_CODE ON)
```

**Regra**: Use `POSITION_INDEPENDENT_CODE ON` para bibliotecas estaticas que podem ser linkadas em shared libraries.

---

### Anti-Pattern 16: Nao gerenciar RPATH em installs

```cmake
# RUIM — binario instalado nao acha shared libs
install(TARGETS myapp DESTINATION bin)
# Rodar ./bin/myapp: error while loading shared libraries
```

**Por que e ruim**: No Linux, shared libraries precisam de RPATH correto para serem encontradas em runtime. Sem RPATH, o binario instalado so funciona com `LD_LIBRARY_PATH` configurado manualmente.

```cmake
# BOM — RPATH configurado
set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
set(CMAKE_INSTALL_RPATH "$ORIGIN/../lib;$ORIGIN/../lib64")

install(TARGETS myapp
    RUNTIME DESTINATION bin
    BUNDLE  DESTINATION bin
)
install(TARGETS mylib
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)
```

**Regra**: Sempre configure `CMAKE_INSTALL_RPATH` e `CMAKE_INSTALL_RPATH_USE_LINK_PATH` para installs.

---

### Anti-Pattern 17: Nao usar `export()` ou `install(EXPORT ...)`

```cmake
# RUIM — consumidores precisam usar find_package complexo
add_library(mylib src/mylib.cpp)
install(TARGETS mylib DESTINATION lib)
# Consumidor precisa saber caminhos e configurar manualmente
```

**Por que e ruim**: Sem exports, bibliotecas instaladas nao podem ser descobertas por `find_package()` de forma limpa. Consumidores precisam hardcodar caminhos.

```cmake
# BOM — export completo
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

install(TARGETS mylib
    EXPORT mylib-targets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    INCLUDES DESTINATION include
)
install(DIRECTORY include/ DESTINATION include)

install(EXPORT mylib-targets
    FILE mylib-config.cmake
    NAMESPACE mylib::
    DESTINATION lib/cmake/mylib
)
```

**Regra**: Sempre exporte targets para que consumidores possam usar `find_package(mylib)`.

---

### Anti-Pattern 18: Nao testar o build em CI

```yaml
# RUIM — CI so compila, nao testa
build:
  script:
    - cmake -B build
    - cmake --build build
  # Sem ctest, sem sanitizers, sem analise estatica
```

**Por que e ruim**: Compilar nao e suficiente. Bugs em runtime, comportamento indefinido, memory leaks — nada disso e pego so pelo compilador.

```yaml
# BOM — build completo com testes
build:
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=Debug
      -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
    - cmake --build build
    - cd build && ctest --output-on-failure -j4
```

**Regra**: CI deve compilar, testar, e (idealmente) rodar analise estatica. Sem testes, o build so prova que o codigo compila.

---

### Anti-Pattern 19: Ignorar `CMAKE_CXX_STANDARD` em favor de `-std=c++17`

```cmake
# RUIM — flag manual quebra cross-compilation
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17")
```

**Por que e ruim**: `-std=c++17` e uma flag GCC/Clang. MSVC nao aceita. Mesmo entre GCC e Clang, a sintaxe varia (Clang aceita `-std=gnu++17`). Cross-compilation quebra.

```cmake
# BOM — padrao do CMake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
```

**Regra**: Use `CMAKE_CXX_STANDARD` para definir o padrao da linguagem. Nunca use flags manuais.

---

### Anti-Pattern 20: Nao usar `ccache` ou `sccache`

```cmake
# RUIM — rebuilds completos sem cache de compilacao
# Nenhuma configuracao de cache
```

**Por que e ruim**: Sem cache de compilacao, cada `cmake --build build` recompila tudo. Isso e especialmente doloroso em CI/CD e em projetos grandes.

```cmake
# BOM — ccache/sccache integrado
find_program(CCACHE_PROGRAM ccache)
find_program(SCCACHE_PROGRAM sccache)

if(CCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    message(STATUS "Using ccache: ${CCACHE_PROGRAM}")
elseif(SCCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${SCCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER "${SCCACHE_PROGRAM}")
    message(STATUS "Using sccache: ${SCCACHE_PROGRAM}")
endif()
```

**Regra**: Sempre integre ccache ou sccache. Reduz rebuilds em 50-90%.

---

### Anti-Pattern 21: Nao usar `target_precompile_headers`

```cmake
# RUIM — headers pesados recompilados em cada translation unit
add_library(mylib
    src/core.cpp
    src/parser.cpp
    src/analyzer.cpp
)
```

**Por que e ruim**: Headers como `<iostream>`, `<vector>`, e headers de bibliotecas pesadas (Qt, Boost) sao parseados em cada arquivo `.cpp`. Isso aumenta tempo de compilacao dramaticamente.

```cmake
# BOM — precompiled headers
add_library(mylib
    src/core.cpp
    src/parser.cpp
    src/analyzer.cpp
)
target_precompile_headers(mylib PRIVATE
    <iostream>
    <vector>
    <string>
    <memory>
)
```

**Regra**: Para projetos com mais de 10 arquivos, use `target_precompile_headers()` para headers estaveis e pesados.

---

### Anti-Pattern 22: Nao configurar `CMAKE_EXPORT_COMPILE_COMMANDS`

```cmake
# RUIM — ferramentas de analise nao tem database de compilacao
# clang-tidy, clangd, etc. nao funcionam corretamente
```

**Por que e ruim**: `compile_commands.json` e essencial para ferramentas como clang-tidy, clangd, e IDEs. Sem ele, analise estatica perde contexto e IDEs nao funcionam.

```cmake
# BOM — sempre gerar
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
```

**Regra**: Sempre habilite `CMAKE_EXPORT_COMPILE_COMMANDS`. Adicione `build/compile_commands.json` ao `.gitignore`.

---

### Anti-Pattern 23: Nao usar `FetchContent_MakeAvailable` corretamente

```cmake
# RUIM — MakeAvailable antes do Declare
include(FetchContent)
FetchContent_MakeAvailable(fmt)
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG 10.2.1
)
```

**Por que e ruim**: Ordem incorreta causa erros ou usa versoes erradas. `MakeAvailable` precisa ser chamado depois de todos os `Declare` do batch.

```cmake
# BOM — Declare primeiro, MakeAvailable depois
include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG 10.2.1
    GIT_SHALLOW TRUE
)

FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.13.0
    GIT_SHALLOW TRUE
)

FetchContent_MakeAvailable(fmt spdlog)
```

**Regra**: Declare todas as dependencias, depois chame `MakeAvailable` uma vez com todas.

---

### Anti-Pattern 24: Nao tratar warnings como erros em CI

```cmake
# RUIM — warnings passam despercebidos
target_compile_options(mylib PRIVATE -Wall -Wextra)
# Sem -Werror, warnings nao quebram o build
```

**Por que e ruim**: Warnings nao tratados acumulam e escondem bugs reais. Um `unused variable` hoje e um `use-after-free` amanha que ninguem viu porque tinha 50 warnings na saida.

```cmake
# BOM -Werror condicional
option(WARNINGS_AS_ERRORS "Tratar warnings como erros" ON)

target_compile_options(mylib PRIVATE
    -Wall -Wextra -Wpedantic
    $<$<BOOL:${WARNINGS_AS_ERRORS}>:-Werror>
)
```

```cmake
# Em CI, sempre ative
cmake -B build -DWARNINGS_AS_ERRORS=ON
```

**Regra**: Habilite `-Werror` em CI e develop. Desabilite localmente quando precisar experimentar.

---

### Anti-Pattern 25: Nao versionar `CMakePresets.json`

```bash
# RUIM — .gitignore inclui CMakePresets.json
echo "CMakePresets.json" >> .gitignore
```

**Por que e ruim**: Presets definem configuracoes padrao do build. Se nao estiverem versionados, cada dev configura o build diferente, e CI precisa reconfigurar manualmente.

```bash
# BOM — versionar presets
git add CMakePresets.json
# E versionar CMakeUserPresets.json para customizacoes locais
echo "CMakeUserPresets.json" >> .gitignore
```

**Regra**: `CMakePresets.json` e versionado. `CMakeUserPresets.json` e local e gitignored.

---

### Anti-Pattern 26: Usar `option()` sem valor default

```cmake
# RUIM — variavel indefinida se o dev nao setar
option(MYPROJECT_BUILD_TESTS "Build tests")
```

**Por que e ruim**: Sem valor default, o comportamento depende de como a variavel foi declarada anteriormente. Se voce removeu uma `set()` antiga, o `option()` pode ter valor inesperado.

```cmake
# BOM — default explícito sempre
option(MYPROJECT_BUILD_TESTS "Build tests" ON)
option(MYPROJECT_BUILD_EXAMPLES "Build examples" OFF)
option(MYPROJECT_HARDEN "Enable security hardening" ON)
```

**Regra**: Sempre especifique o valor default em `option()`.

---

### Anti-Pattern 27: Nao usar `target_sources` com `PRIVATE`/`PUBLIC`

```cmake
# RUIM — sources em nivel alto, visibilidade ambigua
add_executable(myapp
    src/main.cpp
    src/core/engine.cpp
    src/core/parser.cpp
    src/core/validator.cpp
    src/util/logger.cpp
    src/util/config.cpp
    src/net/http_client.cpp
    src/net/tcp_socket.cpp
)
```

**Por que e ruim**: Todos os arquivos ficam em um unico `add_executable()`. Quando o projeto cresce, fica impossivel saber quais arquivos sao parte do core, quais sao util, quais sao networking.

```cmake
# BOM — sources por componente com visibilidade
add_executable(myapp src/main.cpp)

target_sources(myapp PRIVATE
    src/core/engine.cpp
    src/core/parser.cpp
    src/core/validator.cpp
    src/util/logger.cpp
    src/util/config.cpp
    src/net/http_client.cpp
    src/net/tcp_socket.cpp
)
```

**Regra**: Para executaveis, use `target_sources()` apos `add_executable()`. Para bibliotecas, sempre liste os sources no `add_library()` ou `target_sources()`.

---

### Anti-Pattern 28: Nao configurar `CMAKE_MODULE_PATH`

```cmake
# RUIM — find_package nao acha modulos customizados
find_package(MyCustomLib REQUIRED)
# Erro: Could not find a package configuration file for "MyCustomLib"
```

**Por que e ruim**: Sem `CMAKE_MODULE_PATH`, o CMake so procura nos modulos padrao e nos diretorios do projeto. Modulos customizados em `cmake/` nao sao encontrados.

```cmake
# BOM — adicione seu diretorio de modulos
list(APPEND CMAKE_MODULE_PATH "${PROJECT_SOURCE_DIR}/cmake")

# Agora find_package pode encontrar MyCustomLib.cmake
find_package(MyCustomLib REQUIRED)
```

**Regra**: Para `find_package()` customizado, adicione o diretorio ao `CMAKE_MODULE_PATH` ou use o prefixo de namespace no nome do modulo.

---

### Anti-Pattern 29: Usar `string(REPLACE ...)` para paths

```cmake
# RUIM — manipulacao manual de paths
string(REPLACE "\\" "/" MY_PATH "${CMAKE_CURRENT_SOURCE_DIR}")
set(MY_INCLUDE "${MY_PATH}/include")
```

**Por que e ruim**: Manipulacao manual de paths e fragil e propensa a erros em multi-plataforma. O CMake ja tem ferramentas para isso.

```cmake
# BOM — usecmake_path() (CMake 3.20+) ou file(TO_CMAKE_PATH)
cmake_path(SET MY_INCLUDE NORMALIZE "${CMAKE_CURRENT_SOURCE_DIR}/include")

# Para versoes anteriores
file(TO_CMAKE_PATH "${CMAKE_CURRENT_SOURCE_DIR}" MY_PATH)
set(MY_INCLUDE "${MY_PATH}/include")
```

**Regra**: Nunca manipule paths manualmente com `string(REPLACE)`. Use `cmake_path()` (CMake 3.20+) ou `file(TO_CMAKE_PATH)`.

---

### Anti-Pattern 30: Nao usar `cmake_policy` para compatibilidade

```cmake
# RUIM — politicas antigas causam comportamento perigoso
cmake_minimum_required(VERSION 3.10)
# CMP0077 (option() normalizacao) nao esta ativa
# Resultado: option() ignora variaveis normais definidas antes
```

**Por que e ruim**: Cada versao do CMake introduce politicas que mudam comportamento default. Sem ativar politicas modernas, voce herda comportamentos antigos que podem causar bugs subitileis.

```cmake
# BOM — use range de versao para ativar todas as politicas
cmake_minimum_required(VERSION 3.15...3.30)
# Isso ativa automaticamente todas as politicas ate 3.30
```

**Regra**: Sempre use `VERSION X.Y...3.Z` no `cmake_minimum_required`. Isso ativa todas as politicas ate a versao maxima.

---

### Anti-Pattern 31: Nao usar `file(READ ...)` para verificar existencia

```cmake
# RUIM — assume que arquivo existe
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" PROJECT_VERSION_STRING)
string(STRIP "${PROJECT_VERSION_STRING}" PROJECT_VERSION_STRING)
```

**Por que e ruim**: Se o arquivo nao existe, `file(READ)` falha com erro critico. Isso quebra o build em ambientes onde o arquivo pode nao existir (CI, containers, etc.).

```cmake
# BOM — verifique antes ou use default
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION")
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" PROJECT_VERSION_STRING)
    string(STRIP "${PROJECT_VERSION_STRING}" PROJECT_VERSION_STRING)
else()
    set(PROJECT_VERSION_STRING "0.0.0")
    message(WARNING "VERSION file not found, using ${PROJECT_VERSION_STRING}")
endif()
```

**Regra**: Sempre verifique a existencia de arquivos antes de ler, ou forneça defaults.

---

### Anti-Pattern 32: Nao usar `configure_file` corretamente

```cmake
# RUIM — copia o arquivo inteiro sem variaveis
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/config.h.in"
               "${CMAKE_CURRENT_BINARY_DIR}/config.h")
```

**Por que e ruim**: Se `config.h.in` contem `@VARIABLE@` ou `${VARIABLE}` e a variavel nao foi definida, o CMake gera um erro. Mas se voce esqueceu de definir, o erro pode nao ser claro.

```cmake
# BOM — defina todas as variaveis antes e use COPYONLY so se necessario
set(MY_VERSION "1.0.0")
set(MY_AUTHOR "dev@example.com")
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/config.h.in"
               "${CMAKE_CURRENT_BINARY_DIR}/config.h")
```

```cmake
# Se voce quer copia exata (sem substituicao)
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/template.txt"
               "${CMAKE_CURRENT_BINARY_DIR}/output.txt"
               COPYONLY)
```

**Regra**: Defina todas as variaveis antes de `configure_file()`. Use `COPYONLY` apenas para copias literais.

---

## 17.3 Checklist de Seguranca do Build

Rode esta checklist antes de cada release. Cada item e verificavel no `CMakeLists.txt` e nos arquivos de build.

### 3.1 Compilador e Flags

- [ ] `cmake_minimum_required(VERSION 3.15...3.30)` — versao minima moderna
- [ ] `CMAKE_CXX_STANDARD` definido (nao flags manuais)
- [ ] `CMAKE_CXX_STANDARD_REQUIRED ON` — falha se compilador nao suporta
- [ ] `CMAKE_CXX_EXTENSIONS OFF` — sem extensoes GNU
- [ ] `-Wall -Wextra -Wpedantic` habilitado
- [ ] `-Werror` habilitado em CI (`WARNINGS_AS_ERRORS=ON`)
- [ ] `-fstack-protector-strong` em todos os targets (Linux)
- [ ] `-D_FORTIFY_SOURCE=2` em Release (Linux)
- [ ] `-fPIE` / `-pie` para executaveis (ASLR)
- [ ] `-fstack-clash-protection` em GCC 8+ (Linux)

### 3.2 Dependencias

- [ ] Todas as versoes de dependencias especificadas
- [ ] `FetchContent` com `GIT_TAG` fixo (nao `main` ou `master`)
- [ ] `GIT_SHALLOW TRUE` para downloads menores
- [ ] `find_package` com `REQUIRED` para dependencias obrigatorias
- [ ] `MESSAGE` em `find_package` para instrucoes de instalacao
- [ ] Nenhum `add_subdirectory` para libs externas (prefira `FetchContent`)
- [ ] Lock file ou versoes fixadas para reprodutibilidade

### 3.3 Escopo e Visibilidade

- [ ] Nenhum `include_directories()` global
- [ ] Nenhum `link_directories()` global
- [ ] Nenhum `link_libraries()` global
- [ ] Nenhum `add_definitions()` global
- [ ] `target_include_directories` com `PUBLIC`/`PRIVATE` corretos
- [ ] `target_link_libraries` com `PUBLIC`/`PRIVATE`/`INTERFACE` corretos
- [ ] `target_compile_definitions` por target

### 3.4 Hardening

- [ ] AddressSanitizer configurado para Debug CI
- [ ] UndefinedBehaviorSanitizer configurado para Debug CI
- [ ] `-fno-omit-frame-pointer` com sanitizers
- [ ] Stack protector habilitado
- [ ] FORTIFY_SOURCE em Release
- [ ] PIE/PIC configurado corretamente
- [ ] RELRO/RPATH configurado para instalacoes

### 3.5 Build System

- [ ] `CMAKE_EXPORT_COMPILE_COMMANDS ON`
- [ ] `CMAKE_BUILD_TYPE` com default sensato
- [ ] `ccache` ou `sccache` configurado
- [ ] `CMakePresets.json` versionado
- [ ] `CMakeUserPresets.json` gitignored
- [ ] `compile_commands.json` gitignored
- [ ] `CMAKE_POSITION_INDEPENDENT_CODE` onde necessario

### 3.6 Testes e Qualidade

- [ ] `CTest` configurado com `enable_testing()`
- [ ] Sanitizers em pelo menos uma configuracao de CI
- [ ] Analise estatica (clang-tidy) em CI
- [ ] Cobertura de codigo (lcov/gcov) em CI
- [ ] Benchmark configurado (Google Benchmark)
- [ ] `target_precompile_headers` para projetos grandes

### 3.7 Instalacao e Distribuicao

- [ ] `install(TARGETS ...)` configurado para todos os targets publicos
- [ ] `install(EXPORT ...)` para que consumidores usem `find_package`
- [ ] `CMAKE_INSTALL_RPATH` configurado
- [ ] `CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE`
- [ ] CPack configurado para empacotamento
- [ ] DESTINATION paths usando GNUInstallDirs

### 3.8 Documentacao e Manutencao

- [ ] `PROJECT_VERSION` definido
- [ ] `CMAKE_PROJECT_HOMEPAGE_URL` definido
- [ ] `CMAKE_PROJECT_DESCRIPTION` definido
- [ ] README com instrucoes de build
- [ ] CHANGELOG atualizado
- [ ] .clang-format versionado
- [ ] .clang-tidy versionado

---

## 17.4 Decision Trees

### 17.4.1 Qual Gerador Usar?

```
Voce esta em qual plataforma?
|
+-- Windows
|   |
|   +-- Usando Visual Studio?
|   |   +-- Sim --> Visual Studio 17 2022 (default)
|   |   |   +-- Multi-config? --> -G "Visual Studio 17 2022" -A x64
|   |   |   +-- Single-config? --> -G "Visual Studio 17 2022" -T ClangCl
|   |   +-- Nao --> MinGW Makefiles
|   |       +-- Cross-compile? --> Ninja + toolchain file
|   |       +-- Nativo? --> Ninja (mais rapido) ou MinGW Makefiles
|   |
|   +-- Quer performance de build?
|       +-- Sim --> Ninja (sempre Ninja)
|       +-- Nao --> MinGW Makefiles e aceitavel
|
+-- Linux
|   |
|   +-- Quer multi-config?
|   |   +-- Sim --> Ninja Multi-Config
|   |   +-- Nao --> Ninja (default recomendado)
|   |
|   +-- Usando GCC? --> Ninja ou Unix Makefiles
|   +-- Usando Clang? --> Ninja (recomendado)
|   +-- Cross-compile? --> Ninja + toolchain file
|
+-- macOS
|   |
|   +-- Usando Xcode?
|   |   +-- Sim --> Xcode
|   |   +-- Nao --> Ninja (recomendado)
|   |
|   +-- Cross-compile? --> Ninja + toolchain file
|
+-- Embedded/Cross-compile
|   +-- Simpre --> Ninja + toolchain file
```

**Resumo**: Para a maioria dos projetos, **Ninja** e a melhor escolha. E rapido, suporta single e multi-config, e funciona bem em todas as plataformas.

---

### 17.4.2 Qual Package Manager Usar?

```
Voce esta gerenciando o que?
|
+-- Bibliotecas C/C++ do sistema
|   +-- find_package() + vcpkg/conan para controle de versao
|   +-- Sistema: apt, brew, pacman (para CI simples)
|
+-- Dependencias de build (CMake-native)
|   +-- FetchContent (preferido, integrado no CMake)
|   +-- add_subdirectory (para componentes internos)
|
+-- Gerenciador de pacotes completo?
|   +-- vcpkg
|   |   +-- Foco em Windows/Visual Studio? --> vcpkg
|   |   +-- Precisa de manifest mode? --> vcpkg
|   |   +-- Integracao com CMake nativa? --> vcpkg
|   |
|   +-- Conan
|   |   +-- Multi-plataforma com configuracao flexivel? --> Conan
|   |   +-- Precisa de profiles avancadas? --> Conan
|   |   +-- Time ja usa Conan? --> Conan
|   |
|   +-- CPM.cmake
|   |   +-- Simplicidade maxima? --> CPM.cmake
|   |   +-- Sem configuracao externa? --> CPM.cmake
|   |   +-- Projeto pequeno/medio? --> CPM.cmake
|
+-- Scripts de build?
|   +-- Conan (profiles avancadas)
|   +-- vcpkg (integracao com Visual Studio)
|   +-- Scripts customizados (raramente necessario)
```

**Regra geral**:
- **FetchContent**: Dependencias CMake-native, poucas dependencias, controle total
- **vcpkg**: Projetos Windows-heavy, precisa de binarios pre-compilados
- **Conan**: Multi-plataforma complexo, configuracao avancada
- **CPM.cmake**: Simplicidade, zero configuracao externa

---

### 17.4.3 Decision Tree: find_package vs FetchContent vs submodules

```
A dependencia tem um CMakeLists.txt funcional?
|
+-- Nao
|   +-- Tem pkg-config? --> pkg_check_modules()
|   +-- Tem findXXX.cmake? --> find_package()
|   +-- Nao tem nada --> Manual: find_library() + find_path()
|
+-- Sim
|   |
|   +-- A dependencia e estavel (releases regulares)?
|   |   +-- Sim --> FetchContent com GIT_TAG fixo
|   |   |   +-- Binarios pre-compilados disponiveis? --> find_package() + vcpkg/conan
|   |   |   +-- Sem binarios? --> FetchContent (build from source)
|   |   |
|   |   +-- Nao (mudanca constante) --> Git submodule (controle manual)
|   |       +-- Precisa de updates frequentes? --> submodule com CI de update
|   |       +-- Pin em commit especifico? --> submodule ou FetchContent
|   |
|   +-- E uma lib pequena (< 5 arquivos)?
|   |   +-- Copie para o projeto (vendor)
|   |   +-- Ou FetchContent
|   |
|   +-- E uma lib grande (Qt, Boost, OpenSSL)?
|   +-- find_package() sempre (nao Compile from source)
|       +-- Sistema disponivel? --> find_package() direto
|       +-- Sistema indisponivel? --> vcpkg ou conan
|
+-- Dependencia opcional?
|   +-- option(USE_FOO "..." ON)
|   +-- if(USE_FOO) find_package(Foo) endif()
```

**Resumo rapido**:

| Cenario | Ferramenta |
|---------|------------|
| Lib CMake nativa, estavel | `FetchContent` |
| Lib grande (Qt, Boost, OpenSSL) | `find_package()` + vcpkg |
| Lib instavel, sem releases | `git submodule` |
| Lib pequena, vendor | Copie para o projeto |
| Lib com pkg-config | `pkg_check_modules()` |
| Lib Windows-only | `vcpkg` |

---

## 17.5 Migration: CMake Antigo para Moderno

### 17.5.1 Tabela de Mapeamento

| CMake Antigo (2.x/3.0) | CMake Moderno (3.15+) |
|------------------------|----------------------|
| `cmake_minimum_required(VERSION 2.8)` | `cmake_minimum_required(VERSION 3.15...3.30)` |
| `project(mylib)` | `project(mylib VERSION 1.0 LANGUAGES CXX)` |
| `include_directories(...)` | `target_include_directories(target ...)` |
| `link_directories(...)` | Remova. Use `find_library()` |
| `link_libraries(...)` | `target_link_libraries(target ...)` |
| `add_definitions(...)` | `target_compile_definitions(target ...)` |
| `set(CMAKE_CXX_FLAGS ...)` | `target_compile_options(target ...)` |
| `set(CMAKE_CXX_STANDARD 17)` | `target_compile_features(target cxx_std_17)` |
| `file(GLOB SRC *.cpp)` | Lista explicita de arquivos |
| `add_subdirectory(third_party/...)` | `FetchContent_Declare` + `FetchContent_MakeAvailable` |
| `set_target_properties(target PROPERTIES COMPILE_FLAGS ...)` | `target_compile_options(target ...)` |
| `include(${CMAKE_MODULE_PATH}/FindXXX.cmake)` | `find_package(XXX REQUIRED)` |
| `configure_file(config.h.in config.h)` | Mantido (ainda e moderno) |
| `enable_testing()` + `add_test(...)` | Mantido (ou `gtest_discover_tests`) |

### 17.5.2 Exemplo Completo de Migration

**Antes (CMake 2.x)**:

```cmake
cmake_minimum_required(VERSION 2.8.12)
project(myproject)

set(CMAKE_CXX_FLAGS "-std=c++17 -O2 -Wall")
include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_SOURCE_DIR}/third_party/include)

link_directories(${PROJECT_SOURCE_DIR}/third_party/lib)
link_libraries(mylib ssl crypto pthread)

add_executable(myapp
    src/main.cpp
    src/parser.cpp
    src/analyzer.cpp
)
```

**Depois (Modern CMake 3.15+)**:

```cmake
cmake_minimum_required(VERSION 3.15...3.30)
project(myproject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
endif()

# Dependencias via FetchContent
include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG 10.2.1
    GIT_SHALLOW TRUE
)

find_package(OpenSSL 1.1.1 REQUIRED)
find_package(Threads REQUIRED)

FetchContent_MakeAvailable(fmt)

# Library
add_library(mylib
    src/parser.cpp
    src/analyzer.cpp
)
target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
target_link_libraries(mylib
    PUBLIC
        fmt::fmt
        OpenSSL::SSL
        OpenSSL::Crypto
        Threads::Threads
)

# Executable
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)

# Options
option(BUILD_TESTING "Build tests" ON)
if(BUILD_TESTING)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install
include(GNUInstallDirs)
install(TARGETS mylib myapp
    EXPORT myproject-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
```

### 17.5.3 Passos de Migration

1. **Atualize `cmake_minimum_required`** para 3.15+
2. **Defina versao e linguagem** no `project()`
3. **Substitua `include_directories`** por `target_include_directories`
4. **Substitua `link_directories`** por `find_library` ou targets importados
5. **Substitua `link_libraries`** por `target_link_libraries`
6. **Substitua `add_definitions`** por `target_compile_definitions`
7. **Substitua `set(CMAKE_CXX_FLAGS)`** por `target_compile_options` + `target_compile_features`
8. **Substitua `file(GLOB)`** por lista explicita
9. **Substitua `add_subdirectory(third_party/...)`** por `FetchContent`
10. **Adicione `CMAKE_EXPORT_COMPILE_COMMANDS ON`**
11. **Adicione `CMAKE_BUILD_TYPE` default**
12. **Adicione `ccache`/`sccache`**
13. **Configure `install()` e `export()`**
14. **Adicione `CMakePresets.json`**
15. **Teste em todas as plataformas alvo**

---

## 17.6 Template: CMakeLists.txt Seguro Padrao

Este template cobre a maioria dos projetos C/C++ de seguranca. Copie e adapte.

```cmake
cmake_minimum_required(VERSION 3.15...3.30)

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================
project(myproject
    VERSION 1.0.0
    DESCRIPTION "Projeto seguro com CMake moderno"
    HOMEPAGE_URL "https://github.com/user/project"
    LANGUAGES CXX C
)

# =============================================================================
# BUILD CONFIGURATION
# =============================================================================
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Default build type
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    message(STATUS "Build type: Debug (default)")
    set(CMAKE_BUILD_TYPE Debug CACHE STRING "Build type" FORCE)
    set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS
        Debug Release RelWithDebInfo MinSizeRel)
endif()

# =============================================================================
# COMPILER CACHE
# =============================================================================
find_program(CCACHE_PROGRAM ccache)
find_program(SCCACHE_PROGRAM sccache)

if(CCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
    message(STATUS "Using ccache: ${CCACHE_PROGRAM}")
elseif(SCCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${SCCACHE_PROGRAM}")
    set(CMAKE_C_COMPILER_LAUNCHER "${SCCACHE_PROGRAM}")
    message(STATUS "Using sccache: ${SCCACHE_PROGRAM}")
endif()

# =============================================================================
# OPTIONS
# =============================================================================
option(MYPROJECT_BUILD_TESTS "Build tests" ON)
option(MYPROJECT_BUILD_EXAMPLES "Build examples" OFF)
option(MYPROJECT_BUILD_DOCS "Build documentation" OFF)
option(MYPROJECT_HARDEN "Enable security hardening flags" ON)
option(WARNINGS_AS_ERRORS "Treat warnings as errors" ON)

# =============================================================================
# SECURITY HARDENING
# =============================================================================
if(MYPROJECT_HARDEN)
    # Stack protector
    add_compile_options(-fstack-protector-strong)

    # FORTIFY_SOURCE (Release only)
    add_compile_options(
        $<$<CONFIG:Release>:-D_FORTIFY_SOURCE=2>
    )

    # Position Independent Executable
    set(CMAKE_POSITION_INDEPENDENT_CODE ON)

    # RELRO (Linux)
    if(UNIX AND NOT APPLE)
        set(CMAKE_EXE_LINKER_FLAGS
            "${CMAKE_EXE_LINKER_FLAGS} -Wl,-z,relro,-z,now"
        )
        set(CMAKE_SHARED_LINKER_FLAGS
            "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-z,relro,-z,now"
        )
    endif()

    # Stack clash protection (GCC 8+)
    include(CheckCXXCompilerFlag)
    check_cxx_compiler_flag(-fstack-clash-protection HAS_STACK_CLASH)
    if(HAS_STACK_CLASH)
        add_compile_options(-fstack-clash-protection)
    endif()
endif()

# =============================================================================
# DEPENDENCIES
# =============================================================================
include(FetchContent)

# fmt
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG 10.2.1
    GIT_SHALLOW TRUE
)

# nlohmann/json
FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
)

# spdlog
FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG v1.13.0
    GIT_SHALLOW TRUE
)

FetchContent_MakeAvailable(fmt nlohmann_json spdlog)

find_package(Threads REQUIRED)

# =============================================================================
# TARGETS
# =============================================================================

# --- Library ---
add_library(mylib
    src/core/engine.cpp
    src/core/parser.cpp
    src/core/validator.cpp
    src/util/logger.cpp
    src/util/config.cpp
)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(mylib
    PUBLIC
        fmt::fmt
        nlohmann_json::nlohmann_json
        spdlog::spdlog
        Threads::Threads
)

target_compile_options(mylib
    PRIVATE
        $<$<COMPILE_LANGUAGE:CXX>:-Wall -Wextra -Wpedantic>
        $<$<AND:$<BOOL:${WARNINGS_AS_ERRORS}>,$<COMPILE_LANGUAGE:CXX>>:-Werror>
)

# Precompiled headers
target_precompile_headers(mylib PRIVATE
    <iostream>
    <vector>
    <string>
    <memory>
    <fmt/format.h>
)

# --- Executable ---
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)
target_compile_options(myapp PRIVATE
    $<$<COMPILE_LANGUAGE:CXX>:-Wall -Wextra -Wpedantic>
    $<$<AND:$<BOOL:${WARNINGS_AS_ERRORS}>,$<COMPILE_LANGUAGE:CXX>>:-Werror>
)

# =============================================================================
# TESTING
# =============================================================================
if(MYPROJECT_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# =============================================================================
# EXAMPLES
# =============================================================================
if(MYPROJECT_BUILD_EXAMPLES)
    add_subdirectory(examples)
endif()

# =============================================================================
# INSTALL
# =============================================================================
include(GNUInstallDirs)

install(TARGETS mylib myapp
    EXPORT myproject-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/ DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

install(EXPORT myproject-targets
    FILE ${PROJECT_NAME}-config.cmake
    NAMESPACE ${PROJECT_NAME}::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}
)

include(CMakePackageConfigHelpers)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}-config-version.cmake"
    COMPATIBILITY SameMajorVersion
)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}-config-version.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/${PROJECT_NAME}
)

# =============================================================================
# CPACK
# =============================================================================
include(CPack)
```

---

## 17.7 Template: Toolchain File para Cross-Compilation

### 17.7.1 ARM Linux (aarch64)

```cmake
# toolchain-aarch64-linux.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

# Compiladores
set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_ASM_COMPILER aarch64-linux-gnu-gcc)

# Sysroot
set(CMAKE_SYSROOT /path/to/aarch64-sysroot)
set(CMAKE_FIND_ROOT_PATH ${CMAKE_SYSROOT})

# Procurar programas no host
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# Procurar libraries e headers no sysroot
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Flags de compilacao
set(CMAKE_C_FLAGS_INIT "-march=armv8-a -mtune=cortex-a72")
set(CMAKE_CXX_FLAGS_INIT "-march=armv8-a -mtune=cortex-a72")

# Paths de instalacao
set(CMAKE_INSTALL_PREFIX ${CMAKE_SYSROOT}/usr)
```

### 17.7.2 Windows Cross-Compile (MinGW)

```cmake
# toolchain-mingw-w64.cmake
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# Compiladores
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc)
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++)
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres)

# Procurar programas no host
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# Procurar libraries e headers no sysroot
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Suporte a threading
set(CMAKE_C_FLAGS_INIT "-pthread")
set(CMAKE_CXX_FLAGS_INIT "-pthread")

# Extensao de binarios
set(CMAKE_EXECUTABLE_SUFFIX ".exe")
set(CMAKE_SHARED_LIBRARY_SUFFIX ".dll")
set(CMAKE_STATIC_LIBRARY_SUFFIX ".lib")
```

### 17.7.3 ESP32 (ESP-IDF)

```cmake
# toolchain-esp32.cmake
set(CMAKE_SYSTEM_NAME FreeRTOS)
set(CMAKE_SYSTEM_PROCESSOR xtensa)

# ESP-IDF toolchain
set(ESP_IDF_PATH $ENV{IDF_PATH})
set(CMAKE_C_COMPILER ${ESP_IDF_PATH}/tools/xtensa-esp32-elf/bin/xtensa-esp32-elf-gcc)
set(CMAKE_CXX_COMPILER ${ESP_IDF_PATH}/tools/xtensa-esp32-elf/bin/xtensa-esp32-elf-g++)
set(CMAKE_ASM_COMPILER ${ESP_IDF_PATH}/tools/xtensa-esp32-elf/bin/xtensa-esp32-elf-gcc)

# Sysroot do ESP-IDF
set(CMAKE_SYSROOT ${ESP_IDF_PATH}/components/xtensa/esp32)

# Procurar programas no host
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Flags ESP32
set(CMAKE_C_FLAGS_INIT "-mlongcalls -mtext-section-literals")
set(CMAKE_CXX_FLAGS_INIT "-mlongcalls -mtext-section-literals")
```

### 17.7.4 Como Usar Toolchain Files

```bash
# Usando o toolchain file
cmake -B build \
    -DCMAKE_TOOLCHAIN_FILE=toolchain-aarch64-linux.cmake \
    -DCMAKE_BUILD_TYPE=Release

# Ou via preset (ver secao 17.9)
cmake --preset arm-release
```

---

## 17.8 Template: CMakePresets.json

Este e um `CMakePresets.json` completo para projetos multi-plataforma.

```json
{
    "version": 6,
    "cmakeMinimumRequired": {
        "major": 3,
        "minor": 25,
        "patch": 0
    },
    "configurePresets": [
        {
            "name": "default",
            "displayName": "Default (Debug)",
            "description": "Configuracao padrao para desenvolvimento",
            "binaryDir": "${sourceDir}/build/${presetName}",
            "installDir": "${sourceDir}/install/${presetName}",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "WARNINGS_AS_ERRORS": "ON",
                "MYPROJECT_BUILD_TESTS": "ON",
                "MYPROJECT_HARDEN": "ON"
            },
            "condition": {
                "type": "notEquals",
                "lhs": "${hostSystemName}",
                "rhs": "Windows"
            }
        },
        {
            "name": "default-vs",
            "displayName": "Default (Visual Studio)",
            "description": "Configuracao padrao para Visual Studio",
            "generator": "Visual Studio 17 2022",
            "architecture": {
                "value": "x64",
                "strategy": "external"
            },
            "binaryDir": "${sourceDir}/build/${presetName}",
            "installDir": "${sourceDir}/install/${presetName}",
            "cacheVariables": {
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "WARNINGS_AS_ERRORS": "ON",
                "MYPROJECT_BUILD_TESTS": "ON",
                "MYPROJECT_HARDEN": "ON"
            },
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Windows"
            }
        },
        {
            "name": "release",
            "displayName": "Release",
            "description": "Build de release otimizado",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "WARNINGS_AS_ERRORS": "ON"
            }
        },
        {
            "name": "asan",
            "displayName": "AddressSanitizer",
            "description": "Debug com AddressSanitizer",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_CXX_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer",
                "CMAKE_C_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer",
                "CMAKE_EXE_LINKER_FLAGS": "-fsanitize=address,undefined",
                "CMAKE_BUILD_TYPE": "Debug"
            }
        },
        {
            "name": "tsan",
            "displayName": "ThreadSanitizer",
            "description": "Debug com ThreadSanitizer",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_CXX_FLAGS": "-fsanitize=thread -fno-omit-frame-pointer",
                "CMAKE_C_FLAGS": "-fsanitize=thread -fno-omit-frame-pointer",
                "CMAKE_EXE_LINKER_FLAGS": "-fsanitize=thread",
                "CMAKE_BUILD_TYPE": "Debug"
            }
        },
        {
            "name": "ubsan",
            "displayName": "UBSan",
            "description": "Debug com UndefinedBehaviorSanitizer",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_CXX_FLAGS": "-fsanitize=undefined -fno-omit-frame-pointer",
                "CMAKE_C_FLAGS": "-fsanitize=undefined -fno-omit-frame-pointer",
                "CMAKE_EXE_LINKER_FLAGS": "-fsanitize=undefined",
                "CMAKE_BUILD_TYPE": "Debug"
            }
        },
        {
            "name": "arm-release",
            "displayName": "ARM Release (Cross-compile)",
            "description": "Cross-compile para ARM Linux",
            "inherits": "release",
            "toolchainFile": "${sourceDir}/toolchain-aarch64-linux.cmake"
        },
        {
            "name": "mingw-release",
            "displayName": "MinGW Release (Cross-compile)",
            "description": "Cross-compile para Windows via MinGW",
            "generator": "Ninja",
            "toolchainFile": "${sourceDir}/toolchain-mingw-w64.cmake",
            "binaryDir": "${sourceDir}/build/${presetName}",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release"
            }
        },
        {
            "name": "ci-debug",
            "displayName": "CI Debug",
            "description": "Configuracao para CI com sanitizers",
            "inherits": "asan",
            "cacheVariables": {
                "WARNINGS_AS_ERRORS": "ON"
            }
        },
        {
            "name": "ci-release",
            "displayName": "CI Release",
            "description": "Configuracao para CI release",
            "inherits": "release",
            "cacheVariables": {
                "WARNINGS_AS_ERRORS": "ON"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "default",
            "configurePreset": "default"
        },
        {
            "name": "release",
            "configurePreset": "release"
        },
        {
            "name": "asan",
            "configurePreset": "asan"
        },
        {
            "name": "tsan",
            "configurePreset": "tsan"
        },
        {
            "name": "ubsan",
            "configurePreset": "ubsan"
        },
        {
            "name": "arm-release",
            "configurePreset": "arm-release"
        },
        {
            "name": "ci-debug",
            "configurePreset": "ci-debug"
        },
        {
            "name": "ci-release",
            "configurePreset": "ci-release"
        }
    ],
    "testPresets": [
        {
            "name": "default",
            "configurePreset": "default",
            "output": {
                "outputOnFailure": true,
                "verbosity": "extra"
            }
        },
        {
            "name": "asan",
            "configurePreset": "asan",
            "output": {
                "outputOnFailure": true,
                "verbosity": "extra"
            },
            "execution": {
                "noTestsAction": "error"
            }
        },
        {
            "name": "ci",
            "configurePreset": "ci-debug",
            "output": {
                "outputOnFailure": true,
                "verbosity": "extra"
            },
            "execution": {
                "noTestsAction": "error"
            }
        }
    ]
}
```

---

## 17.9 Template: GitHub Actions para C++

Este e um workflow completo para projetos C++ com multi-plataforma, sanitizers, e analise estatica.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  CMAKE_BUILD_PARALLEL_LEVEL: 4

jobs:
  build:
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-22.04
            compiler: gcc-12
            preset: ci-debug
            sanitizer: asan
          - os: ubuntu-22.04
            compiler: gcc-12
            preset: ci-release
            sanitizer: none
          - os: ubuntu-22.04
            compiler: clang-15
            preset: ci-debug
            sanitizer: asan
          - os: ubuntu-22.04
            compiler: clang-15
            preset: ci-debug
            sanitizer: ubsan
          - os: macos-13
            compiler: apple-clang-15
            preset: default
            sanitizer: asan
          - os: windows-2022
            compiler: msvc-2022
            preset: default-vs
            sanitizer: none

    runs-on: ${{ matrix.os }}
    name: ${{ matrix.os }} / ${{ matrix.compiler }} / ${{ matrix.sanitizer }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install Dependencies (Ubuntu)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            cmake ninja-build \
            gcc-12 g++-12 \
            clang-15 clang-tidy-15 \
            libssl-dev libsqlite3-dev

      - name: Install Dependencies (macOS)
        if: runner.os == 'macOS'
        run: |
          brew install cmake ninja openssl sqlite3

      - name: Install Dependencies (Windows)
        if: runner.os == 'Windows'
        run: |
          choco install cmake ninja

      - name: Configure
        run: |
          cmake --preset ${{ matrix.preset }}

      - name: Build
        run: |
          cmake --build --preset ${{ matrix.preset }}

      - name: Test
        run: |
          ctest --preset ${{ matrix.preset }} --output-on-failure

      - name: Static Analysis (clang-tidy)
        if: runner.os == 'Linux' && matrix.compiler == 'clang-15'
        run: |
          find build -name 'compile_commands.json' -exec clang-tidy \
            --checks='-*,bugprone-*,cert-*,cppcoreguidelines-*,modernize-*,performance-*' \
            -p build {} +

      - name: Upload Artifacts
        if: matrix.sanitizer != 'none'
        uses: actions/upload-artifact@v4
        with:
          name: sanitizer-reports-${{ matrix.os }}-${{ matrix.sanitizer }}
          path: |
            build/**/*.log
            build/Testing/Temporary/LastTest.log
          retention-days: 7

  coverage:
    runs-on: ubuntu-22.04
    needs: build

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install Dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            cmake ninja-build gcc-12 g++-12 \
            lcov libssl-dev

      - name: Configure with Coverage
        run: |
          cmake -B build \
            -G Ninja \
            -DCMAKE_C_COMPILER=gcc-12 \
            -DCMAKE_CXX_COMPILER=g++-12 \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_CXX_FLAGS="--coverage" \
            -DCMAKE_EXE_LINKER_FLAGS="--coverage"

      - name: Build
        run: cmake --build build

      - name: Test
        run: ctest --test-dir build --output-on-failure

      - name: Generate Coverage Report
        run: |
          lcov --capture --directory build --output-file coverage.info
          lcov --remove coverage.info \
            '/usr/*' '*/third_party/*' '*/test/*' \
            --output-file coverage.info
          lcov --list coverage.info

      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: coverage.info
          fail_ci_if_error: false
```

---

## 17.10 Template: GitLab CI para C++

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - analysis
  - coverage
  - package

variables:
  CMAKE_BUILD_PARALLEL_LEVEL: 4

# =============================================================================
# BUILD JOBS
# =============================================================================

build:gcc-debug:
  stage: build
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y
      cmake ninja-build gcc g++ libssl-dev
  script:
    - cmake -B build -G Ninja
      -DCMAKE_BUILD_TYPE=Debug
      -DCMAKE_C_COMPILER=gcc
      -DCMAKE_CXX_COMPILER=g++
    - cmake --build build
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

build:gcc-release:
  stage: build
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y
      cmake ninja-build gcc g++ libssl-dev
  script:
    - cmake -B build-release -G Ninja
      -DCMAKE_BUILD_TYPE=Release
      -DCMAKE_C_COMPILER=gcc
      -DCMAKE_CXX_COMPILER=g++
    - cmake --build build-release
  artifacts:
    paths:
      - build-release/
    expire_in: 1 hour

build:clang-asan:
  stage: build
  image: ubuntu:22.04
  before_script:
    - apt-get update && apt-get install -y
      cmake ninja-build clang libssl-dev
  script:
    - cmake -B build-asan -G Ninja
      -DCMAKE_BUILD_TYPE=Debug
      -DCMAKE_C_COMPILER=clang
      -DCMAKE_CXX_COMPILER=clang++
      -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
      -DCMAKE_C_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"
      -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"
    - cmake --build build-asan
  artifacts:
    paths:
      - build-asan/
    expire_in: 1 hour

# =============================================================================
# TEST JOBS
# =============================================================================

test:gcc-debug:
  stage: test
  image: ubuntu:22.04
  needs:
    - build:gcc-debug
  script:
    - ctest --test-dir build --output-on-failure -j4
  artifacts:
    when: always
    reports:
      junit: build/Testing/Temporary/LastTest.xml

test:gcc-release:
  stage: test
  image: ubuntu:22.04
  needs:
    - build:gcc-release
  script:
    - ctest --test-dir build-release --output-on-failure -j4

test:clang-asan:
  stage: test
  image: ubuntu:22.04
  needs:
    - build:clang-asan
  script:
    - ctest --test-dir build-asan --output-on-failure -j4
  artifacts:
    when: always
    reports:
      junit: build-asan/Testing/Temporary/LastTest.xml

# =============================================================================
# ANALYSIS JOBS
# =============================================================================

analysis:clang-tidy:
  stage: analysis
  image: ubuntu:22.04
  needs:
    - build:gcc-debug
  before_script:
    - apt-get update && apt-get install -y
      clang-tidy-15
  script:
    - find build -name 'compile_commands.json' -exec
      clang-tidy-15 --checks='-*,bugprone-*,cert-*,cppcoreguidelines-*,modernize-*'
      -p build {} +

analysis:cppcheck:
  stage: analysis
  image: ubuntu:22.04
  needs: []
  before_script:
    - apt-get update && apt-get install -y cppcheck
  script:
    - cppcheck --enable=all --error-exitcode=1
      --suppress=missingIncludeSystem
      --inline-suppr
      src/ include/

# =============================================================================
# COVERAGE JOB
# =============================================================================

coverage:
  stage: coverage
  image: ubuntu:22.04
  needs:
    - build:gcc-debug
  before_script:
    - apt-get update && apt-get install -y lcov
  script:
    - cmake -B build-cov -G Ninja
      -DCMAKE_BUILD_TYPE=Debug
      -DCMAKE_CXX_FLAGS="--coverage"
      -DCMAKE_EXE_LINKER_FLAGS="--coverage"
    - cmake --build build-cov
    - ctest --test-dir build-cov --output-on-failure
    - lcov --capture --directory build-cov --output-file coverage.info
    - lcov --remove coverage.info '/usr/*' '*/third_party/*' '*/test/*'
      --output-file coverage.info
    - lcov --list coverage.info
  coverage: '/Lines\.*: (\d+\.\d+)%/'
  artifacts:
    paths:
      - coverage.info
    expire_in: 30 days

# =============================================================================
# PACKAGE JOB
# =============================================================================

package:deb:
  stage: package
  image: ubuntu:22.04
  needs:
    - build:gcc-release
    - test:gcc-release
  before_script:
    - apt-get update && apt-get install -y
      cmake ninja-build gcc g++ libssl-dev
  script:
    - cmake -B build-pkg -G Ninja
      -DCMAKE_BUILD_TYPE=Release
    - cmake --build build-pkg
    - cd build-pkg && cpack -G DEB
  artifacts:
    paths:
      - build-pkg/*.deb
    expire_in: 30 days
```

---

## 17.11 Referencia Rapida: Flags por Compilador

### GCC

| Flag | Descricao | Seguranca? |
|------|-----------|------------|
| `-Wall` | Warnings basicos | Sim |
| `-Wextra` | Warnings extras | Sim |
| `-Wpedantic` | Conformidade padrao | Sim |
| `-Werror` | Warnings sao erros | Sim (CI) |
| `-fstack-protector-strong` | Protecao de stack | SIM |
| `-D_FORTIFY_SOURCE=2` | Buffer overflow detection | SIM |
| `-fstack-clash-protection` | Protecao stack clash | SIM |
| `-fcf-protection=full` | Control-flow integrity | SIM |
| `-fPIE -pie` | Position Independent Executable | SIM |
| `-O2` | Otimizacao nivel 2 | Release |
| `-O0` | Sem otimizacao | Debug |
| `-g` | Simbolos de debug | Debug |
| `-fsanitize=address` | AddressSanitizer | Debug |
| `-fsanitize=undefined` | UBSan | Debug |
| `-fsanitize=thread` | ThreadSanitizer | Debug |
| `-fsanitize=leak` | LeakSanitizer | Debug |
| `-fno-omit-frame-pointer` | Stack frames completos | Debug |
| `-std=c++17` | Padrao C++17 | Use CMake |
| `-Wconversion` | Conversoes implicitas | Recomendado |
| `-Wsign-conversion` | Conversoes com sinal | Recomendado |
| `-Wshadow` | Variaveis sombreadas | Recomendado |
| `-Wformat=2` | Seguranca em format | Recomendado |

### Clang

| Flag | Descricao | Seguranca? |
|------|-----------|------------|
| `-Wall` | Warnings basicos | Sim |
| `-Wextra` | Warnings extras | Sim |
| `-Wpedantic` | Conformidade padrao | Sim |
| `-Werror` | Warnings sao erros | Sim (CI) |
| `-fstack-protector-strong` | Protecao de stack | SIM |
| `-D_FORTIFY_SOURCE=2` | Buffer overflow detection | SIM |
| `-fsanitize=address` | AddressSanitizer | Debug |
| `-fsanitize=undefined` | UBSan | Debug |
| `-fsanitize=thread` | ThreadSanitizer | Debug |
| `-fsanitize=leak` | LeakSanitizer | Debug |
| `-fsanitize=memory` | MemorySanitizer | Debug |
| `-fsanitize=cfi` | Control Flow Integrity | Debug |
| `-fno-omit-frame-pointer` | Stack frames completos | Debug |
| `-fPIE -pie` | Position Independent Executable | SIM |
| `-stdlib=libc++` | Standard library alternativa | Recomendado |
| `-Weverything` | Todos os warnings | Debug/CI |
| `-Wno-*` | Desabilitar warnings especificos | Cuidado |

### MSVC

| Flag | Descricao | Seguranca? |
|------|-----------|------------|
| `/W4` | Warnings nivel 4 | Sim |
| `/WX` | Warnings sao erros | Sim (CI) |
| `/sdl` | Security Development Lifecycle | SIM |
| `/GS` | Buffer security check | SIM |
| `/guard:cf` | Control Flow Guard | SIM |
| `/guard:ehcont` | EH Continuation Guard | SIM |
| `/Qspectre` | Spectre mitigation | SIM |
| `/DYNAMICBASE` | ASLR (default no Windows) | SIM |
| `/NXCOMPAT` | DEP (default no Windows) | SIM |
| `/SAFESEH` | Safe Exception Handlers | SIM |
| `/O2` | Otimizacao nivel 2 | Release |
| `/Od` | Sem otimizacao | Debug |
| `/Zi` | Simbolos de debug | Debug |
| `/fsanitize=address` | AddressSanitizer (VS 2019+) | Debug |
| `/std:c++17` | Padrao C++17 | Use CMake |
| `/permissive-` | Conformidade estrita | Recomendado |
| `/volatile:iso` | Volatile conforme ISO | Recomendado |

### Resumo de Flags de Hardening por Compilador

```
+---------------------------+-------+-------+-------+
| Flag                      | GCC   | Clang | MSVC  |
+---------------------------+-------+-------+-------+
| Stack Protector           | YES   | YES   | /GS   |
| FORTIFY_SOURCE            | YES   | YES   | /sdl  |
| PIE/PIC                   | YES   | YES   | N/A   |
| Stack Clash Protection    | YES   | YES   | N/A   |
| Control Flow Integrity    | YES   | YES   | /guard:cf |
| RELRO                     | YES   | YES   | N/A   |
| ASLR                      | -pie  | -pie  | /DYNAMICBASE |
| DEP                       | -z nx | -z nx | /NXCOMPAT |
| Safe Exception Handlers   | N/A   | N/A   | /SAFESEH |
| Spectre Mitigation        | -mspec | N/A  | /Qspectre |
+---------------------------+-------+-------+-------+
```

---

## 17.12 Referencia Rapida: Propriedades por Uso

### Visibilidade

| Propriedade | Quando Usar |
|-------------|-------------|
| `PUBLIC` | Headers + libs que consumidores precisam |
| `PRIVATE` | Apenas para implementacao deste target |
| `INTERFACE` | Apenas para consumidores (header-only libs) |

### Propriedades de Compilacao

| Propriedade | Descricao | Exemplo |
|-------------|-----------|---------|
| `CXX_STANDARD` | Padrao da linguagem | `cxx_std_17` |
| `CXX_STANDARD_REQUIRED` | Obrigatorio? | `ON` |
| `CXX_EXTENSIONS` | Extensoes GNU? | `OFF` |
| `POSITION_INDEPENDENT_CODE` | PIC | `ON` |
| `COMPILE_OPTIONS` | Flags extras | `-Wall` |
| `COMPILE_DEFINITIONS` | Macros | `DEBUG` |
| `COMPILE_FEATURES` | Features da linguagem | `cxx_std_17` |
| `PRECOMPILE_HEADERS` | PCH | `<vector>` |
| `UNITY_BUILD` | Unity build | `ON` |
| `UNITY_BUILD_BATCH_SIZE` | Arquivos por batch | `10` |

### Propriedades de Link

| Propriedade | Descricao | Exemplo |
|-------------|-----------|---------|
| `LINK_LIBRARIES` | Bibliotecas | `Threads::Threads` |
| `LINK_OPTIONS` | Flags do linker | `-Wl,-z,relro` |
| `LINK_DIRECTORIES` | Diretorios de busca | (desencorajado) |
| `LINK_DEPENDS_NO_SHARED` | Dependencias para shared | `ON` |
| `SOVERSION` | Versao da shared lib | `1` |
| `VERSION` | Versao completa | `1.0.0` |
| `BUILD_RPATH` | RPATH durante build | `$ORIGIN/../lib` |
| `INSTALL_RPATH` | RPATH apos install | `$ORIGIN/../lib` |
| `INSTALL_RPATH_USE_LINK_PATH` | Usar link paths | `TRUE` |

### Propriedades de Build

| Propriedade | Descricao | Quando |
|-------------|-----------|--------|
| `BUILD_SHARED_LIBS` | Shared por default | `ON`/`OFF` |
| `CXX_VISIBILITY_PRESET` | Visibilidade default | `hidden` |
| `VISIBILITY_INLINES_HIDDEN` | Hidden inline | `ON` |
| `AUTOMOC` | Qt MOC automatico | `ON` |
| `AUTOUIC` | Qt UIC automatico | `ON` |
| `AUTORCC` | Qt RCC automatico | `ON` |
| `UNITY_BUILD` | Unity builds | `ON` |
| `INTERPROCEDURAL_OPTIMIZATION` | LTO | `ON` |

### Propriedades de Install

| Propriedade | Descricao | Exemplo |
|-------------|-----------|---------|
| `RUNTIME DESTINATION` | Binarios | `bin` |
| `LIBRARY DESTINATION` | Shared libs | `lib` |
| `ARCHIVE DESTINATION` | Static libs | `lib` |
| `INCLUDES DESTINATION` | Headers | `include` |
| `FRAMEWORK DESTINATION` | macOS frameworks | `Library/Frameworks` |

---

## 17.13 Erros Comuns do CMake e Como Resolver

Quando voce encontrar erros no CMake, a mensagem muitas vezes nao e transparente. Esta secao cataloga os erros mais comuns e suas solucoes.

### Erro 1: "Could not find a package configuration file"

```
CMake Error at CMakeLists.txt:10 (find_package):
  Could not find a package configuration file provided by "Foo" with any of
  the following names: FooConfig.cmake / foo-config.cmake
```

**Causa**: `find_package(Foo)` nao encontra o arquivo de configuracao. Pode ser que:
1. O pacote nao esta instalado
2. O pacote esta em um diretorio nao padrao
3. O pacote usa FindModule antigo, nao PackageConfig

**Solucao**:
```cmake
# 1. Verifique se esta instalado
find_package(Foo REQUIRED)

# 2. Se esta em diretorio nao padrao
set(Foo_DIR "/path/to/foo/lib/cmake/Foo")
find_package(Foo REQUIRED)

# 3. Se so tem FindModule
find_package(Foo MODULE REQUIRED)

# 4. Use MESSAGE para instrucao clara
find_package(Foo REQUIRED
    MESSAGE "Foo nao encontrado. Instale com: apt install libfoo-dev"
)
```

---

### Erro 2: "Target 'foo' includes non-existent path"

```
CMake Error in src/CMakeLists.txt:
  Target "mylib" includes non-existent path
    "/some/path/include"
  in its INTERFACE_INCLUDE_DIRECTORIES.
```

**Causa**: `target_include_directories` referencia um diretorio que nao existe no momento do configure.

**Solucao**:
```cmake
# Verifique a existencia antes
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/include")
    target_include_directories(mylib PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    )
else()
    message(FATAL_ERROR "Include directory not found: ${CMAKE_CURRENT_SOURCE_DIR}/include")
endif()
```

---

### Erro 3: "No rule to make target 'xxx'"

```
make[2]: *** No rule to make target 'mylib', needed by 'myapp'.  Stop.
```

**Causa**: `target_link_libraries(myapp PRIVATE mylib)` referencia um target que nao foi criado.

**Solucao**:
```cmake
# Verifique a ordem dos targets
add_library(mylib src/mylib.cpp)  # DEVE vir antes do target_link_libraries
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)
```

---

### Erro 4: "Cannot find source file"

```
CMake Error at CMakeLists.txt:5 (add_executable):
  Cannot find source file:
    src/main.cpp
```

**Causa**: O arquivo fonte nao existe no caminho especificado.

**Solucao**:
```cmake
# Verifique se o arquivo existe
if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/src/main.cpp")
    message(FATAL_ERROR "Source file not found: src/main.cpp")
endif()

add_executable(myapp src/main.cpp)
```

---

### Erro 5: "CMAKE_CXX_STANDARD not supported"

```
CMake Error: CMAKE_CXX_STANDARD 20 is not supported by this compiler
```

**Causa**: O compilador nao suporta o padrao da linguagem solicitado.

**Solucao**:
```cmake
# Use CXX_STANDARD_REQUIRED para falhar explicitamente
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)  # FALHA se nao suportado

# Ou verifique antes
include(CheckCXXCompilerFlag)
check_cxx_compiler_flag("-std=c++20" HAS_CXX20)
if(HAS_CXX20)
    set(CMAKE_CXX_STANDARD 20)
else()
    message(WARNING "C++20 not supported, falling back to C++17")
    set(CMAKE_CXX_STANDARD 17)
endif()
```

---

### Erro 6: "The imported target 'xxx' references the file ... which does not exist"

```
CMake Error: The imported target "OpenSSL::SSL" references the file
  "/usr/lib/x86_64-linux-gnu/libssl.so" which does not exist.
```

**Causa**: O pacote esta parcialmente instalado — o arquivo de configuracao existe, mas as bibliotecas nao.

**Solucao**:
```bash
# Reinstale o pacote de desenvolvimento
sudo apt-get install --reinstall libssl-dev

# Ou verifique a instalacao
dpkg -L libssl-dev | grep "\.so"
```

---

### Erro 7: "Generator mismatch"

```
CMake Error: The source directory "/path/to/project" contains a CMakeLists.txt
  which was generated with a different generator.
```

**Causa**: Voce esta tentando gerar em um diretorio que ja foi usado com outro gerador.

**Solucao**:
```bash
# Delete o build directory e recomece
rm -rf build/
cmake -B build -G Ninja

# Ou use um diretorio diferente
cmake -B build-ninja -G Ninja
cmake -B build-make -G "Unix Makefiles"
```

---

### Erro 8: "The following variables are used but they are set to NOTFOUND"

```
CMake Error: The following variables are used in this project, but they are
  set to NOTFOUND:
    FOO_LIBRARY (required by target "myapp")
```

**Causa**: `find_library(FOO_LIBRARY ...)` nao encontrou a biblioteca.

**Solucao**:
```cmake
# 1. Verifique se REQUIRED esta presente
find_library(FOO_LIBRARY NAMES foo REQUIRED
    MESSAGE "libfoo nao encontrada. Instale: apt install libfoo-dev"
)

# 2. Ou use find_package com target importado
find_package(Foo REQUIRED)
# Foo::Foo e o target importado, nao precisa de find_library
```

---

### Erro 9: "Target 'xxx' already exists in another export set"

```
CMake Error: Target "mylib" already exists in another export set.
```

**Causa**: `install(TARGETS ...)` foi chamado para o mesmo target duas vezes com export sets diferentes.

**Solucao**:
```cmake
# So chame install(TARGETS ...) uma vez por target
install(TARGETS mylib
    EXPORT myproject-targets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)
# NAO chame novamente para mylib
```

---

### Erro 10: "Unknown CMake command 'cmake_policy'"

```
CMake Error at CMakeLists.txt:1:
  Unknown CMake command "cmake_policy".
```

**Causa**: `cmake_policy` e chamado antes de `cmake_minimum_required`. A directiva deve vir primeiro.

**Solucao**:
```cmake
# Ordem correta
cmake_minimum_required(VERSION 3.15...3.30)
cmake_policy(SET CMP0077 NEW)  # SO DEPOIS do cmake_minimum_required
project(myproject)
```

---

### Erro 11: "INSTALL already has a target"

```
CMake Error at src/CMakeLists.txt:15:
  INSTALL already has a target "mylib" in this export set.
```

**Causa**: Voce chamou `install(EXPORT ...)` para um export set que ja foi usado.

**Solucao**:
```cmake
# Use o mesmo export set para todos os targets
install(TARGETS mylib myapp
    EXPORT myproject-targets  # Mesmo export set
)
# So chame install(EXPORT ...) uma vez
install(EXPORT myproject-targets ...)
```

---

### Erro 12: "Could not find Git" (em FetchContent)

```
CMake Error at /usr/share/cmake/Modules/FetchContent.cmake:1083:
  Could not find Git
```

**Causa**: `FetchContent` com `GIT_REPOSITORY` requer Git instalado no sistema.

**Solucao**:
```bash
# Instale Git
sudo apt-get install git

# Ou use URL direta sem Git
FetchContent_Declare(
    fmt
    URL https://github.com/fmtlib/fmt/archive/refs/tags/10.2.1.tar.gz
    URL_HASH SHA256=...
)
```

---

## 17.14 Dicas Avancadas de Performance de Build

### 17.14.1 Unity Builds

Unity builds combinam multiplos arquivos `.cpp` em um unico arquivo, reduzindo tempo de compilacao drasticamente.

```cmake
# Habilitar unity builds globalmente
set(CMAKE_UNITY_BUILD ON)

# Ou por target
set_target_properties(mylib PROPERTIES UNITY_BUILD ON)

# Controle o tamanho dos batches
set_target_properties(mylib PROPERTIES UNITY_BUILD_BATCH_SIZE 10)
```

**Quando usar**: Projetos grandes (>50 arquivos) com headers estaveis. Pode causar problemas com namespaces de symbols.

**Quando NAO usar**: Quando voce tem static variables com o mesmo nome em arquivos diferentes, ou quando precisa de include-order-isolation.

### 17.14.2 Compilation Databases

```cmake
# Sempre gere compilation database
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Para projetos multi-config (Visual Studio)
# compile_commands.json so e gerado por ferramentas externas
```

### 17.14.3 Precompiled Headers

```cmake
# Para projetos grandes (10+ arquivos)
target_precompile_headers(mylib PRIVATE
    <algorithm>
    <iostream>
    <memory>
    <string>
    <vector>
    <boost/multiprecision/cpp_int.hpp>
)

# Para projetos com multiplas libraries
# Cada library pode ter seu proprio PCH
target_precompile_headers(parser PRIVATE
    <fstream>
    <sstream>
    <string>
    <regex>
)
```

### 17.14.4 Interprocedural Optimization (LTO)

```cmake
# Habilitar LTO (Link Time Optimization)
include(CheckIPOSupported)
check_ipo_supported(RESULT ipo_supported)

if(ipo_supported)
    set_target_properties(mylib myapp PROPERTIES
        INTERPROCEDURAL_OPTIMIZATION TRUE
    )
endif()
```

### 17.14.5 Obj Pool com Object Libraries

```cmake
# Use object libraries para compartilhar object files
add_library(mylib_objects OBJECT
    src/core/engine.cpp
    src/core/parser.cpp
    src/core/validator.cpp
)
target_include_directories(mylib_objects PRIVATE include)
target_link_libraries(mylib_objects PRIVATE OpenSSL::SSL)

# Shared library
add_library(mylib SHARED $<TARGET_OBJECTS:mylib_objects>)

# Static library (reutiliza os mesmos objects)
add_library(mylib_static STATIC $<TARGET_OBJECTS:mylib_objects>)
```

---

## 17.15 Exercicios

### Exercicio 1: Debug de Anti-Patterns

Dado o seguinte `CMakeLists.txt`, identifique todos os anti-patterns e reescreva usando modern CMake:

```cmake
cmake_minimum_required(VERSION 2.8.12)
project(myapp)

set(CMAKE_CXX_FLAGS "-std=c++17 -O2 -Wall -g")

include_directories(${PROJECT_SOURCE_DIR}/include)
include_directories(${PROJECT_SOURCE_DIR}/third_party/include)

link_directories(${PROJECT_SOURCE_DIR}/third_party/lib)
link_libraries(ssl crypto pthread)

add_definitions(-DDEBUG_MODE -DVERSION="1.0")

file(GLOB SOURCES "src/*.cpp")
add_executable(myapp ${SOURCES})

find_package(Boost)
target_link_libraries(myapp Boost::filesystem)
```

**Resolucao esperada**: Identificar minimo 8 anti-patterns (versao antiga, flags globais, include/link directories globais, add_definitions, GLOB, find_package sem REQUIRED, etc.).

---

### Exercicio 2: Crie um Preset Multi-Plataforma

Crie um `CMakePresets.json` que suporte:
1. Debug no Linux com sanitizers
2. Release no Linux
3. Debug no Windows com Visual Studio
4. Cross-compile para ARM Linux

**Resolucao esperada**: 4+ configure presets com condicoes, 4+ build presets, e pelo menos 1 test preset.

---

### Exercicio 3: Migre um Projeto Legado

Migre o projeto abaixo de CMake 2.x para CMake 3.15+ moderno:

```cmake
# Projeto legado
cmake_minimum_required(VERSION 2.6)
project(LegacyApp)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14 -Wall -Wextra")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=c11")

include_directories(include)
include_directories(third_party/rapidjson/include)

add_executable(legacy_app
    src/main.cpp
    src/utils.cpp
    src/parser.cpp
    src/network.cpp
)

target_link_libraries(legacy_app pthread ssl crypto curl)
```

**Resolucao esperada**: Atualizar versao minima, usar `target_*` commands, adicionar `find_package`, configurar visibilidade, adicionar security hardening.

---

### Exercicio 4: Configure o Checklist de Seguranca

Aplique o checklist da secao 17.3 em um projeto existente. Para cada item nao atendido:
1. Documente o problema
2. Proponha a correcao
3. Priorize por impacto de seguranca

**Resolucao esperada**: Lista de itens faltantes com correcoes e priorizacao (alta/média/baixa).

---

### Exercicio 5: Crie um Workflow de CI Completo

Crie um `.github/workflows/ci.yml` que:
1. Compile em Linux (GCC e Clang), macOS, e Windows
2. Rode testes em todas as plataformas
3. Execute AddressSanitizer em pelo menos uma configuracao
4. Gere relatorio de cobertura
5. Rode clang-tidy

**Resolucao esperada**: Workflow com matrix strategy, jobs dependentes, e artifacts.

---

### Exercicio 6: Escolha o Package Manager

Para cada cenario, escolha a melhor ferramenta e justifique:

1. Projeto C++ puro Linux com 3 dependencias CMake-native
2. Projeto Windows com Visual Studio e 10 dependencias
3. Projeto embedded ARM com dependencias minimas
4. Projeto multi-plataforma com dependencias complexas (Qt, Boost, OpenSSL)
5. Projeto novo querendo simplicidade maxima

**Resolucao esperada**: Cada item com ferramenta e justificativa baseada no decision tree da secao 17.4.

---

### Exercicio 7: Hardening Completo

Dado um `CMakeLists.txt` basico, adicione TODAS as flags de seguranca da secao 17.11 para GCC e Clang. Crie um option `MYPROJECT_HARDEN` para controlar o hardening.

**Resolucao esperada**: Flags de stack protector, FORTIFY_SOURCE, PIE/PIC, RELRO, stack clash protection, e sanitizer options.

---

## 17.16 Referencias

### Documentacao Oficial do CMake

- [CMake Documentation](https://cmake.org/cmake/help/latest/)
- [CMake Presets](https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html)
- [Generator Expressions](https://cmake.org/cmake/help/latest/manual/cmake-generator-expressions.7.html)
- [FetchContent](https://cmake.org/cmake/help/latest/module/FetchContent.html)
- [GNUInstallDirs](https://cmake.org/cmake/help/latest/module/GNUInstallDirs.html)
- [CMake Package Config Files](https://cmake.org/cmake/help/latest/manual/cmake-packages.7.html)

### Guias e Best Practices

- [Modern CMake (Deniz Bahce)](https://cliutils.gitlab.io/modern-cmake/)
- [Effective Modern CMake (Vector 11)](https://vectorizable.com/articles/effective-modern-cmake/)
- [Professional CMake (Craig Scott)](https://crascit.com/professional-cmake/)
- [cmake-cookbook (PDF)](https://cmake-cookbook.readthedocs.io/)

### Seguranca

- [OWASP C/C++ Hardening Guide](https://owasp.org/www-project-appsec-evolution-series/2020/cpp-project/)
- [CERT C Coding Standard](https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard)
- [Compiler Security Switches (OpenBSD)](https://www.openbsd.org/mini-ports.html)
- [Linux Hardening in userspace (Carnal0xage)](https://github.com/carnal0wnage/weirdthings/blob/master/pdf/Linux-Hardening-in-userspace.pdf)

### Ferramentas

- [clang-tidy](https://clang.llvm.org/extra/clang-tidy/)
- [cppcheck](http://cppcheck.sourceforge.net/)
- [ccache](https://ccache.dev/)
- [sccache](https://github.com/mozilla/sccache)
- [vcpkg](https://github.com/microsoft/vcpkg)
- [Conan](https://conan.io/)
- [CPM.cmake](https://github.com/cpm-cmake/CPM.cmake)

### CI/CD

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI Documentation](https://docs.gitlab.com/ee/ci/)
- [Clang Sanitizers](https://clang.llvm.org/docs/AddressSanitizer.html)

### Livros

- **Professional CMake** - Craig Scott
- **CMake CookBook** - Robert Maynard, Craig Scott
- **Effective Modern CMake** - David Mazieres
- **Secure Coding in C and C++** - Robert Seacord
- **The CERT C Coding Standard** - Robert Seacord
- **Hands-On System Programming with C++** - Dr. Rian Quinn

---

## Resumo Final

Este capitulo consolidou 16 capitulos de conhecimento em um conjunto pratico de ferramentas:

1. **Anti-patterns**: 25 padroes problematicos com codigos de correcao. Use o checklist para auditar projetos existentes.

2. **Checklist de seguranca**: 40+ itens verificaveis. Rode antes de cada release.

3. **Decision trees**: Arvores de decisao para escolher gerador, package manager, e estrategia de dependencias.

4. **Migration passo a passo**: Tabela de mapeamento e exemplo completo de CMake 2.x para moderno.

5. **Templates prontos**: CMakeLists.txt, toolchain files, CMakePresets.json, GitHub Actions, GitLab CI. Copie e adapte.

6. **Referencias rapidas**: Flags por compilador e propriedades por uso. Consulte quando precisar lembrar qual flag faz o que.

O segredo nao e memorizar tudo — e saber onde encontrar. Estes templates e referencias estao aqui para quando voce precisar, nao para voce decorar.

**Build systems sao a fundacao da seguranca do software.** Um build system bem configurado impede vulnerabilidades antes que elas entrem no codigo. Um build system mal configurado deixa a porta aberta para qualquer atacante.

Construa suas fundacoes com cuidado.

---

*"Um checklist nao e substituto para conhecimento — e um seguro contra o esquecimento."*
---

*[Capítulo anterior: 16 — Cicd Seguro](16-cicd-seguro.md)*

