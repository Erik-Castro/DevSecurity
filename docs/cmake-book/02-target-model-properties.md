---
layout: default
title: "02-target-model-properties"
---

# Capítulo 02: Target Model e Properties

## Sumário

- [2.1 Objetivos de Aprendizado](#21-objetivos-de-aprendizado)
- [2.2 Target-based Design: Por que Targets São Melhores que Variáveis Globais](#22-target-based-design-por-que-targets-são-melhores-que-variáveis-globais)
- [2.3 Propriedades Públicas vs Privadas vs Interface](#23-propriedades-públicas-vs-privadas-vs-interface)
- [2.4 INTERFACE Libraries: Padrão para Header-Only](#24-interface-libraries-padrão-para-header-only)
- [2.5 Compile Features: cxx_std_17, cxx_std_20](#25-compile-features-cxx_std_17-cxx_std_20)
- [2.6 Target Properties: INCLUDE_DIRECTORIES, COMPILE_DEFINITIONS](#26-target-properties-include_directories-compile_definitions)
- [2.7 Propagate vs Set: Como as Propriedades Fluem](#27-propagate-vs-set-como-as-propriedades-fluem)
- [2.8 Aliases: add_library(alias ALIAS target)](#28-aliases-add_libraryalias-alias-target)
- [2.9 Object Libraries: Reutilização de Object Files](#29-object-libraries-reutilização-de-object-files)
- [2.10 IMPORTED Targets: Integração com find_package](#210-imported-targets-integração-com-find_package)
- [2.11 Custom Targets: add_custom_target, add_custom_command](#211-custom-targets-add_custom_target-add_custom_command)
- [2.12 Generator Expressions: $<TARGET_PROPERTY:...>](#212-generator-expressions-target_property)
- [2.13 Exemplo Completo: Biblioteca Modular com Targets](#213-exemplo-completo-biblioteca-modular-com-targets)
- [2.14 Exercícios](#214-exercícios)
- [2.15 Referências](#215-referências)

---

## 2.1 Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Compreender por que o modelo de targets do CMake é superior ao uso de variáveis globais
2. Diferenciar propriedades públicas, privadas e de interface e quando usar cada uma
3. Criar e utilizar INTERFACE libraries para projetos header-only
4. Aplicar compile features como cxx_std_17 e cxx_std_20 de forma moderna
5. Gerenciar INCLUDE_DIRECTORIES e COMPILE_DEFINITIONS por target
6. Entender como as propriedades fluem entre targets (propagate vs set)
7. Utilizar aliases para tornar builds mais robustas
8. Trabalhar com Object libraries para reutilização de object files
9. Integrar dependências externas via IMPORTED targets
10. Criar custom targets e custom commands para processos avançados
11. Empregar generator expressions para comportamento condicional em tempo de configuração

### Pré-requisitos

- Conhecimento básico de CMake (CMakeLists.txt, add_library, add_executable)
- Familiaridade com o conceito de compilação e linkage
- Ter lido o Capítulo 01 desta série

### Ferramentas Necessárias

- CMake 3.16 ou superior
- Compilador C++ com suporte a C++17 ou superior
- Editor de código com suporte a CMake

---

## 2.2 Target-based Design: Por que Targets São Melhores que Variáveis Globais

### O Problema com Variáveis Globais

Antes da introdução do modelo de targets, os projetos CMake dependiam fortemente de variáveis globais para configurar compilação. Veja um exemplo típico de código legado:

```cmake
# ABORDAGEM LEGADA - NÃO RECOMENDADA
cmake_minimum_required(VERSION 3.10)
project(MeuProjeto CXX)

# Variáveis globais para diretórios
set(MEUPROJETO_INCLUDE_DIR ${CMAKE_SOURCE_DIR}/include)
set(MEUPROJETO_SRC_DIR ${CMAKE_SOURCE_DIR}/src)
set(MEUPROJETO_LIB_DIR ${CMAKE_SOURCE_DIR}/lib)

# Variáveis globais para flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")
set(CMAKE_CXX_FLAGS_DEBUG "-g -DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -DNDEBUG")

# Variáveis globais para definições
add_definitions(-DMEUPROJETO_USE_SIMD=1)
add_definitions(-DMEUPROJETO_DEBUG_MODE=0)

# Compilação do projeto
include_directories(${MEUPROJETO_INCLUDE_DIR})
add_library(meuprojeto ${MEUPROJETO_SRC_DIR}/core.cpp
                       ${MEUPROJETO_SRC_DIR}/utils.cpp)
target_link_libraries(meuprojeto PUBLIC ${MEUPROJETO_LIB_DIR}/libexternal.a)
```

### Por que Isso é Problemático?

Variáveis globais apresentam vários problemas sérios:

1. **Efeitos colaterais invisíveis**: Quando você modifica `CMAKE_CXX_FLAGS`, isso afeta TODOS os targets no projeto, incluindo bibliotecas externas que você não controla.

2. **Falta de encapsulamento**: Não há forma de dizer "esta flag se aplica apenas a este target". Tudo é global.

3. **Dificuldade de reutilização**: Bibliotecas não podem ser reutilizadas em outros projetos porque dependem de variáveis globais que podem não existir.

4. **Conflitos de namespace**: Variáveis como `CMAKE_CXX_FLAGS` são compartilhadas entre todos os projetos, causando conflitos.

5. **Impossibilidade de dependências granulares**: Não é possível dizer "este target precisa destas definições, mas aquele não".

### A Solução: Modelo de Targets

O modelo de targets do CMake resolve todos esses problemas associando propriedades diretamente a targets específicos:

```cmake
# ABORDAGEM MODERNA - RECOMENDADA
cmake_minimum_required(VERSION 3.16)
project(MeuProjeto LANGUAGES CXX)

# Criar biblioteca com propriedades associadas ao target
add_library(meuprojeto
    src/core.cpp
    src/utils.cpp
)

# Propriedades associadas ao target, não ao projeto
target_include_directories(meuprojeto
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_options(meuprojeto
    PRIVATE
        -Wall
        -Wextra
    PUBLIC
        -O2
)

target_compile_definitions(meuprojeto
    PRIVATE
        MEUPROJETO_USE_SIMD=1
    PUBLIC
        MEUPROJETO_DEBUG_MODE=0
)

# Dependência externa é uma interface limpa
find_package(ExternalLib REQUIRED)
target_link_libraries(meuprojeto PUBLIC ExternalLib::ExternalLib)
```

### Vantagens do Modelo de Targets

1. **Encapsulamento**: Cada target tem suas próprias propriedades. Modificar uma não afeta outras.

2. **Reutilizabilidade**: Bibliotecas podem ser reutilizadas porque suas propriedades viajam com elas.

3. **Granularidade**: Você pode especificar diferentes flags para diferentes partes do projeto.

4. **Dependências explícitas**: O sistema de linkage do CMake gerencia automaticamente a propagação de propriedades.

5. **Suporte a ferramentas externas**: find_package retorna targets com propriedades pré-configuradas.

6. **Escopo correto**: Propriedades PRIVATE não vazam para quem consome o target.

### Exemplo Prático: Comparação de Abordagens

Considere um projeto com duas bibliotecas, `libA` e `libB`, onde `libB` depende de `libA`.

**Abordagem com variáveis globais (legada):**

```cmake
# PROBLEMA: libB não pode ser usada sem libA
# porque libA depende de variáveis globais

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -pthread")
include_directories(${CMAKE_SOURCE_DIR}/libA/include)
include_directories(${CMAKE_SOURCE_DIR}/libB/include)

add_library(libA src/a1.cpp src/a2.cpp)
add_library(libB src/b1.cpp src/b2.cpp)

target_link_libraries(libB libA)
```

**Abordagem com targets (moderna):**

```cmake
# SOLUÇÃO: libA e libB são autocontidas
# libB pode ser usada em qualquer projeto

add_library(libA
    src/a1.cpp
    src/a2.cpp
)

target_include_directories(libA
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_options(libA
    PUBLIC
        -pthread
)

add_library(libB
    src/b1.cpp
    src/b2.cpp
)

target_include_directories(libB
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_link_libraries(libB PUBLIC libA)
```

### A Regra de Ouro

**Nunca use variáveis globais no CMake moderno.** Cada propriedade deve ser associada a um target específico usando comandos como `target_compile_options`, `target_include_directories`, `target_compile_definitions`, e `target_link_libraries`.

---

## 2.3 Propriedades Públicas vs Privadas vs Interface

O CMake classifica propriedades em três categorias fundamentais que determinam como elas se propagam entre targets:

### Propriedades PRIVATE

Propriedades que se aplicam apenas ao target atual e NÃO são propagadas para alvos que dependem dele.

```cmake
add_library(meulib src/meulib.cpp)

# Flags de compilação PRIVADAS
target_compile_options(meulib
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -O2
)

# Definições PRIVADAS
target_compile_definitions(meulib
    PRIVATE
        MEULIB_INTERNAL_DEBUG=1
        MEULIB_USE_SSE42=1
)

# Include directories PRIVADAS
target_include_directories(meulib
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/internal
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/private
)

# Estas propriedades NÃO são visíveis para quem faz link com meulib
```

**Quando usar PRIVATE:**
- Flags de otimização que não afetam a API pública
- Definições internas de debug
- Diretórios de headers internos
- Flags específicas do compilador para otimização

### Propriedades PUBLIC

Propriedades que se aplicam ao target atual E são propagadas para alvos que dependem dele.

```cmake
add_library(meulib src/meulib.cpp)

# Flags de compilação PÚBLICAS
target_compile_options(meulib
    PUBLIC
        -pthread
        -fPIC
)

# Definições PÚBLICAS
target_compile_definitions(meulib
    PUBLIC
        MEULIB_USE_EXCEPTIONS=1
        MEULIB_API_VERSION=2
)

# Include directories PÚBLICAS
target_include_directories(meulib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Qualquer target que faça link com meulib receberá estas propriedades
```

**Quando usar PUBLIC:**
- Flags que afetam a API pública do target
- Definições necessárias para consumir a biblioteca
- Diretórios de headers públicos
- Flags que devem ser herdadas por dependentes

### Propriedades INTERFACE

Propriedades que NÃO se aplicam ao target atual, mas SÃO propagadas para alvos que dependem dele.

```cmake
# INTERFACE library (header-only)
add_library(meulib INTERFACE)

# Flags de compilação INTERFACE
target_compile_options(meulib
    INTERFACE
        -Wall
        -Wextra
)

# Definições INTERFACE
target_compile_definitions(meulib
    INTERFACE
        MEULIB_USE_EXCEPTIONS=1
)

# Include directories INTERFACE
target_include_directories(meulib
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Estas propriedades NÃO são aplicadas ao meulib (não tem sources)
# mas SÃO aplicadas a targets que dependem de meulib
```

**Quando usar INTERFACE:**
- Bibliotecas header-only
- pacotes de configuração (targets exportados)
- Propriedades que não se aplicam ao target atual

### Tabela Comparativa

| Propriedade | Aplica ao target | Propaga para dependentes |
|-------------|------------------|--------------------------|
| PRIVATE     | Sim              | Não                      |
| PUBLIC      | Sim              | Sim                      |
| INTERFACE   | Não              | Sim                      |

### Exemplo Prático: Múltiplos Escopos

Considere uma biblioteca que tem headers públicos e internos:

```cmake
add_library(meulib
    src/core.cpp
    src/internal_helper.cpp
    src/platform_specific.cpp
)

target_include_directories(meulib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
        ${CMAKE_CURRENT_SOURCE_DIR}/src/platform
)

target_compile_options(meulib
    PUBLIC
        -pthread
    PRIVATE
        -Wall
        -Wextra
        $<$<CXX_COMPILER_ID:GNU>:-Wno-unused-parameter>
        $<$<CXX_COMPILER_ID:Clang>:-Wno-missing-field-initializers>
)

target_compile_definitions(meulib
    PUBLIC
        MEULIB_API_VERSION=2
    PRIVATE
        MEULIB_BUILDING=1
        $<$<CONFIG:Debug>:MEULIB_DEBUG_MODE=1>
)
```

### Cuidados Comuns

1. **Não misture PUBLIC e PRIVATE sem necessidade**: Se uma propriedade só é usada no target atual, use PRIVATE.

2. **Headers públicos em PRIVATE**: Um erro comum é colocar diretórios de headers públicos em PRIVATE, tornando impossível incluir a biblioteca.

3. **INTERFACE sem target**: Nem todo target pode ter INTERFACE. Apenas targets criados com `add_library(... INTERFACE)` ou IMPORTED.

4. **Propriedades herdadas**: Quando você faz `target_link_libraries(A PUBLIC B)`, as propriedades PUBLIC e INTERFACE de B são herdadas por A como propriedades PUBLIC.

---

## 2.4 INTERFACE Libraries: Padrão para Header-Only

### Conceito

INTERFACE libraries são targets que não possuem fontes compiladas. Elas existem apenas para transmitir propriedades (includes, definições, compile features) para targets que dependem delas.

### Quando Usar

1. **Bibliotecas header-only**: Bibliotecas que não precisam de compilação, apenas de inclusão de headers.
2. **Pacotes de configuração**: Targets exportados que transmitem configurações.
3. **Agregação de propriedades**: Grupo de configurações que podem ser aplicadas juntas.

### Exemplo Básico

```cmake
# Criar uma INTERFACE library para headers comuns
add_library(common_headers INTERFACE)

target_include_directories(common_headers
    INTERFACE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_features(common_headers
    INTERFACE
        cxx_std_17
)

target_compile_definitions(common_headers
    INTERFACE
        USE_MODERN_CXX=1
)

# Usar em outro target
add_library(meuapp src/main.cpp)
target_link_libraries(meuapp PUBLIC common_headers)
```

### Exemplo: Biblioteca Header-Only Completa

```cmake
# Estrutura do projeto:
# myheaderlib/
#   CMakeLists.txt
#   include/
#     myheaderlib/
#       algorithm.hpp
#       container.hpp
#       utility.hpp
#   tests/
#     test_algorithm.cpp
#     test_container.cpp

cmake_minimum_required(VERSION 3.16)
project(MyHeaderLib LANGUAGES CXX)

# INTERFACE library
add_library(myheaderlib INTERFACE)

# Configurar include directories
target_include_directories(myheaderlib
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Compile features necessários
target_compile_features(myheaderlib
    INTERFACE
        cxx_std_17
)

# Definições necessárias para usar a biblioteca
target_compile_definitions(myheaderlib
    INTERFACE
        MYHEADERLIB_USE_EXCEPTIONS=1
)

# Dependências externas (se houver)
find_package(Threads REQUIRED)
target_link_libraries(myheaderlib INTERFACE Threads::Threads)

# Testes (opcional)
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()
    add_executable(test_algorithm tests/test_algorithm.cpp)
    target_link_libraries(test_algorithm PRIVATE myheaderlib)
    add_test(NAME test_algorithm COMMAND test_algorithm)

    add_executable(test_container tests/test_container.cpp)
    target_link_libraries(test_container PRIVATE myheaderlib)
    add_test(NAME test_container COMMAND test_container)
endif()
```

### INTERFACE Libraries para Configurações

Você pode criar múltiplas INTERFACE libraries para diferentes configurações:

```cmake
# Configuração para debug
add_library(config_debug INTERFACE)
target_compile_definitions(config_debug
    INTERFACE
        DEBUG=1
        _DEBUG=1
        $<$<CXX_COMPILER_ID:GNU>:_GLIBCXX_DEBUG=1>
)
target_compile_options(config_debug
    INTERFACE
        -g
        -O0
)

# Configuração para release
add_library(config_release INTERFACE)
target_compile_definitions(config_release
    INTERFACE
        NDEBUG=1
)
target_compile_options(config_release
    INTERFACE
        -O3
        -DNDEBUG
)

# Usar condicionalmente
if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    target_link_libraries(meuapp PRIVATE config_debug)
else()
    target_link_libraries(meuapp PRIVATE config_release)
endif()
```

### INTERFACE Libraries para Plataformas

```cmake
# Configuração específica por plataforma
if(WIN32)
    add_library(platform_config INTERFACE)
    target_compile_definitions(platform_config
        INTERFACE
            PLATFORM_WINDOWS=1
            WIN32_LEAN_AND_MEAN=1
            NOMINMAX=1
    )
    target_link_libraries(platform_config INTERFACE ws2_32 winmm)
elseif(APPLE)
    add_library(platform_config INTERFACE)
    target_compile_definitions(platform_config
        INTERFACE
            PLATFORM_MACOS=1
    )
    target_link_libraries(platform_config INTERFACE "-framework CoreFoundation")
elseif(UNIX)
    add_library(platform_config INTERFACE)
    target_compile_definitions(platform_config
        INTERFACE
            PLATFORM_LINUX=1
    )
    target_link_libraries(platform_config INTERFACE pthread dl)
endif()

# Aplicar a configuração da plataforma
target_link_libraries(meuapp PRIVATE platform_config)
```

### INTERFACE Libraries para Sanitizers

```cmake
# Configuração para sanitizers
add_library(sanitizer_asan INTERFACE)
target_compile_options(sanitizer_asan
    INTERFACE
        -fsanitize=address
        -fno-omit-frame-pointer
)
target_link_options(sanitizer_asan
    INTERFACE
        -fsanitize=address
)

add_library(sanitizer_ubsan INTERFACE)
target_compile_options(sanitizer_ubsan
    INTERFACE
        -fsanitize=undefined
)
target_link_options(sanitizer_ubsan
    INTERFACE
        -fsanitize=undefined
)

add_library(sanitizer_tsan INTERFACE)
target_compile_options(sanitizer_tsan
    INTERFACE
        -fsanitize=thread
)
target_link_options(sanitizer_tsan
    INTERFACE
        -fsanitize=thread
)

# Opções de build
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
option(ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)
option(ENABLE_TSAN "Enable ThreadSanitizer" OFF)

if(ENABLE_ASAN)
    target_link_libraries(meuapp PRIVATE sanitizer_asan)
endif()
if(ENABLE_UBSAN)
    target_link_libraries(meuapp PRIVATE sanitizer_ubsan)
endif()
if(ENABLE_TSAN)
    target_link_libraries(meuapp PRIVATE sanitizer_tsan)
endif()
```

### INTERFACE Libraries para Warnings

```cmake
# Conjunto padrao de warnings
add_library(warnings_strict INTERFACE)
target_compile_options(warnings_strict
    INTERFACE
        -Wall
        -Wextra
        -Wpedantic
        -Wshadow
        -Wnon-virtual-dtor
        -Wold-style-cast
        -Wcast-align
        -Wunused
        -Woverloaded-virtual
        -Wconversion
        -Wsign-conversion
        -Wmisleading-indentation
        -Wduplicated-cond
        -Wduplicated-branches
        -Wlogical-op
        -Wnull-dereference
        -Wuseless-cast
        -Wdouble-promotion
        -Wformat=2
)

# Warnings como erros (opcional)
option(WARNINGS_AS_ERRORS "Treat warnings as errors" OFF)
if(WARNINGS_AS_ERRORS)
    target_compile_options(warnings_strict INTERFACE -Werror)
endif()

# Aplicar a todos os targets
target_link_libraries(meuapp PRIVATE warnings_strict)
target_link_libraries(meulib PRIVATE warnings_strict)
```

### INTERFACE Libraries para Padrões de Código

```cmake
# Configuração de código para o projeto
add_library(code_standards INTERFACE)

target_compile_features(code_standards
    INTERFACE
        cxx_std_17
)

target_compile_options(code_standards
    INTERFACE
        $<$<CXX_COMPILER_ID:GNU>:-fconcepts-diagnostics-depth=2>
        $<$<CXX_COMPILER_ID:Clang>:-fconcepts>  # Para clang antigo
)

target_compile_definitions(code_standards
    INTERFACE
        $<$<CXX_COMPILER_ID:MSVC>:_CRT_SECURE_NO_WARNINGS>
        $<$<CXX_COMPILER_ID:MSVC>:NOMINMAX>
)

target_link_libraries(meuapp PRIVATE code_standards)
target_link_libraries(meulib PRIVATE code_standards)
```

### INTERFACE Libraries para Testes

```cmake
# Configuração comum para testes
add_library(test_config INTERFACE)

target_compile_features(test_config
    INTERFACE
        cxx_std_17
)

target_compile_definitions(test_config
    INTERFACE
        TEST_BUILD=1
        $<$<CONFIG:Debug>:TEST_DEBUG=1>
)

target_link_libraries(test_config INTERFACE
    GTest::gtest
    GTest::gmock
)

# Usar em testes
add_executable(test_meuapp tests/test_main.cpp tests/test_utils.cpp)
target_link_libraries(test_meuapp PRIVATE test_config meuapp)
```

### INTERFACE Libraries para Dependências Externas

```cmake
# Wrapper para dependências externas
find_package(Boost REQUIRED COMPONENTS filesystem system)
add_library(boost_config INTERFACE)
target_link_libraries(boost_config INTERFACE
    Boost::filesystem
    Boost::system
)
target_compile_definitions(boost_config INTERFACE
    BOOST_FILESYSTEM_NO_DEPRECATED=1
)

find_package(OpenSSL REQUIRED)
add_library(openssl_config INTERFACE)
target_link_libraries(openssl_config INTERFACE
    OpenSSL::SSL
    OpenSSL::Crypto
)

# Usar no projeto
target_link_libraries(meuapp PRIVATE boost_config openssl_config)
```

### INTERFACE Libraries para Opções de Build

```cmake
# Opções de build configuráveis
option(ENABLE_LOGGING "Enable logging" ON)
option(ENABLE_METRICS "Enable metrics" ON)
option(ENABLE_TRACING "Enable tracing" OFF)

add_library(build_options INTERFACE)

if(ENABLE_LOGGING)
    target_compile_definitions(build_options INTERFACE ENABLE_LOGGING=1)
endif()

if(ENABLE_METRICS)
    target_compile_definitions(build_options INTERFACE ENABLE_METRICS=1)
endif()

if(ENABLE_TRACING)
    target_compile_definitions(build_options INTERFACE ENABLE_TRACING=1)
endif()

target_link_libraries(meuapp PRIVATE build_options)
```

---

## 2.5 Compile Features: cxx_std_17, cxx_std_20

### Conceito

Compile features são uma forma portável de especificar requisitos de compilação. Em vez de usar flags específicas do compilador, você especifica o padrão C++ necessário.

### Por que Usar Compile Features?

1. **Portabilidade**: Funciona com qualquer compilador suportado pelo CMake.
2. **Clareza**: Expressa claramente a intenção do projeto.
3. **Automático**: O CMake escolhe a flag correta para cada compilador.
4. **Verificação**: O CMake verifica se o compilador suporta o padrão solicitado.

### Exemplo Básico

```cmake
add_library(meulib src/meulib.cpp)

# Requerer C++17
target_compile_features(meulib PUBLIC cxx_std_17)
```

Isso é equivalente a:

```cmake
# GCC/Clang
target_compile_options(meulib PUBLIC -std=c++17)

# MSVC
target_compile_options(meulib PUBLIC /std:c++17)
```

Mas a forma com compile features é portável e verificada pelo CMake.

### Padrões Disponíveis

| Feature         | Padrão C++ | Ano  |
|-----------------|------------|------|
| cxx_std_98      | C++98      | 1998 |
| cxx_std_11      | C++11      | 2011 |
| cxx_std_14      | C++14      | 2014 |
| cxx_std_17      | C++17      | 2017 |
| cxx_std_20      | C++20      | 2020 |
| cxx_std_23      | C++23      | 2023 |

### Exemplo: Projeto com C++17

```cmake
cmake_minimum_required(VERSION 3.16)
project(MeuProjeto LANGUAGES CXX)

# INTERFACE library para configuração padrão
add_library(project_defaults INTERFACE)

# Requerer C++17
target_compile_features(project_defaults INTERFACE cxx_std_17)

# Outras configurações
target_compile_options(project_defaults INTERFACE
    -Wall
    -Wextra
    -Wpedantic
)

# Biblioteca principal
add_library(meulib
    src/core.cpp
    src/utils.cpp
)

target_link_libraries(meulib PUBLIC project_defaults)

# Executável
add_executable(meuapp src/main.cpp)
target_link_libraries(meuapp PRIVATE meulib)
```

### Exemplo: Projeto com C++20

```cmake
cmake_minimum_required(VERSION 3.16)
project(MeuProjeto20 LANGUAGES CXX)

# Requerer C++20
add_library(project_defaults INTERFACE)
target_compile_features(project_defaults INTERFACE cxx_std_20)

# Biblioteca que usa features C++20
add_library(meulib20
    src/concepts.cpp
    src/ranges.cpp
    src/coroutines.cpp
)

target_link_libraries(meulib20 PUBLIC project_defaults)
```

### Verificação de Suporte

O CMake verifica automaticamente se o compilador suporta o padrão solicitado:

```cmake
# Se o compilador não suportar C++20, o CMake emitirá um erro
cmake_minimum_required(VERSION 3.16)
project(MeuProjeto LANGUAGES CXX)

# Isso causará erro se o compilador não suportar C++20
add_library(meulib src/meulib.cpp)
target_compile_features(meulib PUBLIC cxx_std_20)
```

### Fallback para Padrões Mais Antigos

Você pode usar um fallback para padrões mais antigos:

```cmake
# Tentar C++20, se não, usar C++17
include(CheckCXXCompilerFlag)

check_cxx_compiler_flag("-std=c++20" COMPILER_SUPPORTS_CXX20)
check_cxx_compiler_flag("-std=c++17" COMPILER_SUPPORTS_CXX17)

if(COMPILER_SUPPORTS_CXX20)
    set(CMAKE_CXX_STANDARD 20)
elseif(COMPILER_SUPPORTS_CXX17)
    set(CMAKE_CXX_STANDARD 17)
else()
    message(FATAL_ERROR "C++17 or later is required")
endif()

set(CMAKE_CXX_STANDARD_REQUIRED ON)
```

### Compile Features Específicos

Além do padrão, você pode requisitar features específicas:

```cmake
add_library(meulib src/meulib.cpp)

# Requerer features específicas
target_compile_features(meulib
    PUBLIC
        cxx_std_17
        cxx_constexpr
        cxx_lambda_capture_default_this
        cxx_std_optional
        cxx_std_variant
        cxx_std_string_view
)
```

### Exemplo Prático: Projeto Moderno

```cmake
cmake_minimum_required(VERSION 3.20)
project(ModernProject LANGUAGES CXX)

# Configuração padrão moderna
add_library(modern_config INTERFACE)

# C++20 como padrão mínimo
target_compile_features(modern_config INTERFACE cxx_std_20)

# Warnings estritos
target_compile_options(modern_config INTERFACE
    -Wall
    -Wextra
    -Wpedantic
    -Wshadow
    -Wnon-virtual-dtor
    -Wold-style-cast
    -Wcast-align
    -Wunused
    -Woverloaded-virtual
    -Wconversion
    -Wsign-conversion
    -Wmisleading-indentation
    -Wduplicated-cond
    -Wduplicated-branches
    -Wlogical-op
    -Wnull-dereference
    -Wuseless-cast
    -Wdouble-promotion
    -Wformat=2
    -Wimplicit-fallthrough
)

# Definições de build
target_compile_definitions(modern_config INTERFACE
    $<$<CONFIG:Debug>:DEBUG=1>
    $<$<CONFIG:Release>:NDEBUG=1>
    $<$<CXX_COMPILER_ID:MSVC>:_CRT_SECURE_NO_WARNINGS>
    $<$<CXX_COMPILER_ID:MSVC>:NOMINMAX>
)

# Biblioteca do projeto
add_library(mylib
    src/core.cpp
    src/utils.cpp
    src/platform.cpp
)

target_link_libraries(mylib PUBLIC modern_config)

# Executável principal
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)

# Testes
option(BUILD_TESTS "Build tests" ON)
if(BUILD_TESTS)
    enable_testing()

    find_package(GTest REQUIRED)

    add_executable(test_core tests/test_core.cpp)
    target_link_libraries(test_core PRIVATE mylib GTest::gtest_main)
    add_test(NAME test_core COMMAND test_core)

    add_executable(test_utils tests/test_utils.cpp)
    target_link_libraries(test_utils PRIVATE mylib GTest::gtest_main)
    add_test(NAME test_utils COMMAND test_utils)
endif()
```

### Cuidados Comuns

1. **Não misturar CMAKE_CXX_STANDARD com compile features**: Use um ou outro, não ambos. Compile features são mais granulares.

2. **Verificar suporte**: Sempre verifique se o compilador suporta o padrão desejado antes de usá-lo.

3. **Usar PRIVATE para implementação**: Se a feature só é usada na implementação, use PRIVATE.

4. **Documentar requisitos**: Deixe claro nos comentários por que uma feature específica é necessária.

---

## 2.6 Target Properties: INCLUDE_DIRECTORIES, COMPILE_DEFINITIONS

### INCLUDE_DIRECTORIES

#### Sintaxe

```cmake
target_include_directories(<target>
    [SYSTEM] [AFTER | BEFORE]
    <INTERFACE | PUBLIC | PRIVATE>
    [items1...]
    [<INTERFACE | PUBLIC | PRIVATE>
    [items2...] ...]
)
```

#### Exemplo Básico

```cmake
add_library(meulib src/meulib.cpp)

target_include_directories(meulib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)
```

#### Generator Expressions

```cmake
# BUILD_INTERFACE: usado durante a build local
# INSTALL_INTERFACE: usado após instalação
target_include_directories(meulib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
```

#### SYSTEM Includes

```cmake
# Includes de sistema (tratados como <header> em vez de "header")
target_include_directories(meulib
    SYSTEM PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/third_party/include
)
```

#### BEFORE/AFTER

```cmake
# BEFORE: adiciona antes dos outros includes
# AFTER: adiciona depois (padrão)
target_include_directories(meulib
    PUBLIC
        AFTER
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
```

#### Exemplo Prático

```cmake
# Estrutura do projeto:
# mylib/
#   CMakeLists.txt
#   include/
#     mylib/
#       public_api.hpp
#   src/
#     internal/
#       helper.hpp
#     mylib.cpp

cmake_minimum_required(VERSION 3.16)
project(MyLib LANGUAGES CXX)

add_library(mylib
    src/mylib.cpp
)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)
```

### COMPILE_DEFINITIONS

#### Sintaxe

```cmake
target_compile_definitions(<target>
    <INTERFACE | PUBLIC | PRIVATE>
    [items1...]
    [<INTERFACE | PUBLIC | PRIVATE>
    [items2...] ...]
)
```

#### Exemplo Básico

```cmake
add_library(meulib src/meulib.cpp)

target_compile_definitions(meulib
    PUBLIC
        MYLIB_API_VERSION=2
    PRIVATE
        MYLIB_BUILDING=1
        $<$<CONFIG:Debug>:MYLIB_DEBUG=1>
)
```

#### Definições por Compilador

```cmake
target_compile_definitions(meulib
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:GNU_COMPILER=1>
        $<$<CXX_COMPILER_ID:Clang>:CLANG_COMPILER=1>
        $<$<CXX_COMPILER_ID:MSVC>:MSVC_COMPILER=1>
)
```

#### Definições por Plataforma

```cmake
target_compile_definitions(meulib
    PRIVATE
        $<$<PLATFORM_ID:Windows>:PLATFORM_WINDOWS=1>
        $<$<PLATFORM_ID:Linux>:PLATFORM_LINUX=1>
        $<$<PLATFORM_ID:Darwin>:PLATFORM_MACOS=1>
)
```

#### Definições por Build Type

```cmake
target_compile_definitions(meulib
    PRIVATE
        $<$<CONFIG:Debug>:DEBUG=1>
        $<$<CONFIG:Release>:NDEBUG=1>
        $<$<CONFIG:RelWithDebInfo>:NDEBUG=1>
        $<$<CONFIG:MinSizeRel>:NDEBUG=1>
)
```

#### Exemplo Prático: Definições de Segurança

```cmake
add_library(security_lib src/security.cpp)

target_compile_definitions(security_lib
    PUBLIC
        SECURITY_API_VERSION=1
        SECURITY_USE_EXCEPTIONS=1
    PRIVATE
        SECURITY_BUILDING=1
        $<$<CONFIG:Debug>:SECURITY_DEBUG=1>
        $<$<CONFIG:Release>:SECURITY_OPTIMIZED=1>
        $<$<CXX_COMPILER_ID:GNU>:_FORTIFY_SOURCE=2>
        $<$<CXX_COMPILER_ID:GNU>:_GLIBCXX_ASSERTIONS=1>
        $<$<CXX_COMPILER_ID:GNU>:_GLIBCXX_DEBUG=1>
        $<$<CXX_COMPILER_ID:GNU>:_GLIBCXX_DEBUG_PEDANTIC=1>
)
```

### COMPILE_OPTIONS

#### Sintaxe

```cmake
target_compile_options(<target>
    [BEFORE] [SYSTEM]
    <INTERFACE | PUBLIC | PRIVATE>
    [items1...]
    [<INTERFACE | PUBLIC | PRIVATE>
    [items2...] ...]
)
```

#### Exemplo Básico

```cmake
add_library(meulib src/meulib.cpp)

target_compile_options(meulib
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
    PUBLIC
        -pthread
)
```

#### Flags por Compilador

```cmake
target_compile_options(meulib
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Wpedantic>
        $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)
```

#### Flags por Build Type

```cmake
target_compile_options(meulib
    PRIVATE
        $<$<CONFIG:Debug>:-g -O0>
        $<$<CONFIG:Release>:-O3 -DNDEBUG>
        $<$<CONFIG:RelWithDebInfo>:-g -O2 -DNDEBUG>
        $<$<CONFIG:MinSizeRel>:-Os -DNDEBUG>
)
```

#### Exemplo Prático: Flags de Segurança

```cmake
add_library(secure_lib src/secure.cpp)

target_compile_options(secure_lib
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
        $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)

target_compile_options(secure_lib
    PRIVATE
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Debug>>:-g -O0 -fsanitize=address -fno-omit-frame-pointer>
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Release>>:-O3 -DNDEBUG -fstack-protector-strong>
)
```

### LINK_OPTIONS

#### Sintaxe

```cmake
target_link_options(<target>
    [BEFORE]
    <INTERFACE | PUBLIC | PRIVATE>
    [items1...]
    [<INTERFACE | PUBLIC | PRIVATE>
    [items2...] ...]
)
```

#### Exemplo Básico

```cmake
add_library(meulib src/meulib.cpp)

target_link_options(meulib
    PRIVATE
        -pthread
)
```

#### Flags por Plataforma

```cmake
target_link_options(meulib
    PRIVATE
        $<$<PLATFORM_ID:Windows>:/INCREMENTAL:NO>
        $<$<PLATFORM_ID:Linux>:-Wl,--no-undefined>
        $<$<PLATFORM_ID:Darwin>:-Wl,-dead_strip>
)
```

#### Flags de Segurança

```cmake
add_library(secure_lib src/secure.cpp)

target_link_options(secure_lib
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wl,-z,relro,-z,now>
        $<$<CXX_COMPILER_ID:GNU>:-Wl,-z,noexecstack>
        $<$<CXX_COMPILER_ID:GNU>:-pie>
)
```

### Exemplo Completo: Propriedades de Target

```cmake
cmake_minimum_required(VERSION 3.16)
project(SecureProject LANGUAGES CXX)

# INTERFACE library para configuração padrão
add_library(project_config INTERFACE)

target_compile_features(project_config INTERFACE cxx_std_17)

target_compile_options(project_config
    INTERFACE
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
        $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)

target_compile_definitions(project_config
    INTERFACE
        $<$<CONFIG:Debug>:DEBUG=1>
        $<$<CONFIG:Release>:NDEBUG=1>
        $<$<CXX_COMPILER_ID:MSVC>:_CRT_SECURE_NO_WARNINGS>
        $<$<CXX_COMPILER_ID:MSVC>:NOMINMAX>
)

# Biblioteca principal
add_library(mylib
    src/core.cpp
    src/utils.cpp
)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)

target_compile_definitions(mylib
    PUBLIC
        MYLIB_API_VERSION=1
    PRIVATE
        MYLIB_BUILDING=1
        $<$<CONFIG:Debug>:MYLIB_DEBUG=1>
)

target_compile_options(mylib
    PRIVATE
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Debug>>:-g -O0 -fsanitize=address -fno-omit-frame-pointer>
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Release>>:-O3 -fstack-protector-strong>
)

target_link_options(mylib
    PRIVATE
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Debug>>:-fsanitize=address>
        $<$<CXX_COMPILER_ID:GNU>:-Wl,-z,relro,-z,now>
)

target_link_libraries(mylib PUBLIC project_config)

# Executável principal
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)
```

---

## 2.7 Propagate vs Set: Como as Propriedades Fluem

### Conceito de Propagação

Quando você usa `target_link_libraries(A PUBLIC B)`, as propriedades PUBLIC e INTERFACE de B são herdadas por A. Isso é chamado de "propagação".

### Regras de Propagação

1. **PUBLIC**: Propriedades são herdadas por dependentes E aplicadas ao target atual.
2. **PRIVATE**: Propriedades são aplicadas apenas ao target atual.
3. **INTERFACE**: Propriedades são herdadas por dependentes, mas NÃO aplicadas ao target atual.

### Exemplo: Propagação em Cadeia

```cmake
# Cenário: A -> B -> C
# onde "->" significa "depende de"

add_library(c src/c.cpp)
target_compile_definitions(c PUBLIC C_DEFINITIONS=1)
target_compile_options(c PUBLIC -pthread)

add_library(b src/b.cpp)
target_link_libraries(b PUBLIC c)  # B herda de C

add_library(a src/a.cpp)
target_link_libraries(a PUBLIC b)  # A herda de B e C

# Resultado:
# A herda: C_DEFINITIONS=1, -pthread (de C via B)
# B herda: C_DEFINITIONS=1, -pthread (de C)
# C tem: C_DEFINITIONS=1, -pthread
```

### Exemplo: Propagação Parcial

```cmake
# Cenário: A -> B -> C
# onde "->" significa "depende de"

add_library(c src/c.cpp)
target_compile_definitions(c PUBLIC C_PUBLIC=1)
target_compile_definitions(c PRIVATE C_PRIVATE=1)
target_compile_definitions(c INTERFACE C_INTERFACE=1)

add_library(b src/b.cpp)
target_link_libraries(b PUBLIC c)

add_library(a src/a.cpp)
target_link_libraries(a PUBLIC b)

# Resultado:
# A herda: C_PUBLIC=1, C_INTERFACE=1 (de C via B)
# A NÃO herda: C_PRIVATE=1 (PRIVATE não propaga)

# B herda: C_PUBLIC=1, C_INTERFACE=1 (de C)
# B NÃO herda: C_PRIVATE=1 (PRIVATE não propaga)

# C tem: C_PUBLIC=1, C_PRIVATE=1, C_INTERFACE=1
```

### Exemplo: Propriedades Acumuladas

```cmake
# Propriedades são acumuladas, não substituídas

add_library(c src/c.cpp)
target_compile_definitions(c PUBLIC C_DEFINITIONS=1)

add_library(b src/b.cpp)
target_compile_definitions(b PUBLIC B_DEFINITIONS=1)
target_link_libraries(b PUBLIC c)

add_library(a src/a.cpp)
target_compile_definitions(a PUBLIC A_DEFINITIONS=1)
target_link_libraries(a PUBLIC b)

# Resultado:
# A herda: A_DEFINITIONS=1, B_DEFINITIONS=1, C_DEFINITIONS=1
# B herda: B_DEFINITIONS=1, C_DEFINITIONS=1
# C tem: C_DEFINITIONS=1
```

### Exemplo: PRIVATE vs PUBLIC

```cmake
# Demonstração da diferença entre PRIVATE e PUBLIC

add_library(c src/c.cpp)
target_compile_definitions(c PUBLIC C_PUBLIC=1)
target_compile_definitions(c PRIVATE C_PRIVATE=1)

add_library(b src/b.cpp)
target_link_libraries(b PUBLIC c)
target_compile_definitions(b PUBLIC B_PUBLIC=1)
target_compile_definitions(b PRIVATE B_PRIVATE=1)

add_library(a src/a.cpp)
target_link_libraries(a PUBLIC b)
target_compile_definitions(a PUBLIC A_PUBLIC=1)
target_compile_definitions(a PRIVATE A_PRIVATE=1)

# Resultado para compilação de a.cpp:
# Definições: A_PUBLIC=1, A_PRIVATE=1, B_PUBLIC=1, C_PUBLIC=1
# (A herda PUBLIC de B e C, mas PRIVATE de B e C não propagam)

# Resultado para compilação de b.cpp:
# Definições: B_PUBLIC=1, B_PRIVATE=1, C_PUBLIC=1
# (B herda PUBLIC de C, mas PRIVATE de C não propaga)

# Resultado para compilação de c.cpp:
# Definições: C_PUBLIC=1, C_PRIVATE=1
```

### Exemplo: INTERFACE Libraries

```cmake
# INTERFACE libraries transmitem propriedades sem serem compiladas

add_library(config INTERFACE)
target_compile_definitions(config INTERFACE CONFIG_DEFINITIONS=1)
target_compile_options(config INTERFACE -pthread)
target_compile_features(config INTERFACE cxx_std_17)

add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PUBLIC config)

# Resultado:
# mylib herda: CONFIG_DEFINITIONS=1, -pthread, cxx_std_17
# config não é compilado (INTERFACE)
```

### Exemplo: Múltiplos Dependentes

```cmake
# Biblioteca base
add_library(base src/base.cpp)
target_compile_definitions(base PUBLIC BASE_DEFINITIONS=1)
target_compile_options(base PUBLIC -pthread)

# Bibliotecas que dependem de base
add_library(libA src/libA.cpp)
target_link_libraries(libA PUBLIC base)

add_library(libB src/libB.cpp)
target_link_libraries(libB PUBLIC base)

# Executável que depende de libA e libB
add_executable(app src/app.cpp)
target_link_libraries(app PRIVATE libA libB)

# Resultado:
# app herda: BASE_DEFINITIONS=1, -pthread (de libA e libB)
# libA herda: BASE_DEFINITIONS=1, -pthread
# libB herda: BASE_DEFINITIONS=1, -pthread
# base tem: BASE_DEFINITIONS=1, -pthread
```

### Exemplo: Conflitos de Propriedades

```cmake
# Quando múltiplos targets definem a mesma propriedade

add_library(libA src/libA.cpp)
target_compile_definitions(libA PUBLIC FEATURE=1)

add_library(libB src/libB.cpp)
target_compile_definitions(libB PUBLIC FEATURE=2)

add_executable(app src/app.cpp)
target_link_libraries(app PRIVATE libA libB)

# Resultado:
# app herda: FEATURE=1 (de libA) e FEATURE=2 (de libB)
# O valor final depende da ordem de processamento do CMake
# Isso pode causar comportamento indefinido!
```

### Boas Práticas de Propagação

```cmake
# BOA PRÁTICA: Usar PRIVATE para implementação

add_library(mylib
    src/core.cpp
    src/utils.cpp
)

# Headers públicos: PUBLIC
target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Headers internos: PRIVATE
target_include_directories(mylib
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)

# Flags de warning: PRIVATE (não afeta quem consome)
target_compile_options(mylib
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

# Definições internas: PRIVATE
target_compile_definitions(mylib
    PRIVATE
        MYLIB_BUILDING=1
        $<$<CONFIG:Debug>:MYLIB_DEBUG=1>
)

# Definições públicas: PUBLIC
target_compile_definitions(mylib
    PUBLIC
        MYLIB_API_VERSION=1
)

# Flags públicas (ex: pthread): PUBLIC
target_compile_options(mylib
    PUBLIC
        -pthread
)
```

### Casos de Uso Comuns

#### Caso 1: Biblioteca Header-Only

```cmake
# INTERFACE library: todas as propriedades são INTERFACE
add_library(headerlib INTERFACE)

target_include_directories(headerlib
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_features(headerlib
    INTERFACE
        cxx_std_17
)
```

#### Caso 2: Biblioteca Estática

```cmake
# Biblioteca estática: mistura de PUBLIC, PRIVATE, INTERFACE
add_library(staticlib STATIC
    src/staticlib.cpp
)

target_include_directories(staticlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)

target_compile_features(staticlib
    PUBLIC
        cxx_std_17
)

target_compile_options(staticlib
    PRIVATE
        -Wall
        -Wextra
)
```

#### Caso 3: Biblioteca Compartilhada

```cmake
# Biblioteca compartilhada: atenção para -fPIC
add_library(sharedlib SHARED
    src/sharedlib.cpp
)

target_include_directories(sharedlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_options(sharedlib
    PUBLIC
        -fPIC
    PRIVATE
        -Wall
        -Wextra
)

target_compile_definitions(sharedlib
    PRIVATE
        SHARED_BUILDING=1
    PUBLIC
        SHARED_API=1
)
```

#### Caso 4: Executável

```cmake
# Executável: geralmente PRIVATE para tudo
add_executable(myapp
    src/main.cpp
    src/utils.cpp
)

target_include_directories(myapp
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_options(myapp
    PRIVATE
        -Wall
        -Wextra
        -Wpedantic
)

target_compile_definitions(myapp
    PRIVATE
        APP_VERSION=1
)
```

---

## 2.8 Aliases: add_library(alias ALIAS target)

### Conceito

Aliases são nomes alternativos para targets existentes. Eles são particularmente úteis para bibliotecas EXPORTED e para manter consistência entre builds locais e instaladas.

### Por que Usar Aliases?

1. **Consistência**: Mesmo nome para targets locais e instalados.
2. **Segurança**: Evita acidentalmente linkar com targets errados.
3. **Clareza**: Nomes qualificados como `Namespace::Target` são mais expressivos.
4. **Compatibilidade**: Facilita a migração de find_package para subdirectories.

### Exemplo Básico

```cmake
add_library(mylib src/mylib.cpp)

# Criar alias
add_library(MyProject::mylib ALIAS mylib)

# Usar alias
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE MyProject::mylib)
```

### Exemplo: Namespace

```cmake
# Projeto com namespace
add_library(core src/core.cpp)
add_library(utils src/utils.cpp)
add_library(io src/io.cpp)

# Criar aliases com namespace
add_library(MyProject::core ALIAS core)
add_library(MyProject::utils ALIAS utils)
add_library(MyProject::io ALIAS io)

# Usar aliases
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE
    MyProject::core
    MyProject::utils
    MyProject::io
)
```

### Exemplo: Biblioteca Exportada

```cmake
# Biblioteca que pode ser instalada e exportada
add_library(mylib src/mylib.cpp)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Criar alias
add_library(MyProject::mylib ALIAS mylib)

# Configurar instalação
install(TARGETS mylib
    EXPORT MyProjectTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    INCLUDES DESTINATION include
)

install(DIRECTORY include/ DESTINATION include)

# Exportar targets
install(EXPORT MyProjectTargets
    FILE MyProjectTargets.cmake
    NAMESPACE MyProject::
    DESTINATION lib/cmake/MyProject
)
```

### Exemplo: find_package vs Alias

```cmake
# Comportamento idêntico:

# Opção 1: Usando find_package (após instalação)
find_package(MyProject REQUIRED)
target_link_libraries(app PRIVATE MyProject::mylib)

# Opção 2: Usando add_subdirectory (durante desenvolvimento)
add_subdirectory(path/to/myproject)
target_link_libraries(app PRIVATE MyProject::mylib)

# Em ambos os casos, o target é MyProject::mylib
```

### Exemplo: Condições de Build

```cmake
# Criar alias baseado na configuração
add_library(mylib src/mylib.cpp)

if(CMAKE_BUILD_TYPE STREQUAL "Debug")
    add_library(MyProject::mylib_debug ALIAS mylib)
else()
    add_library(MyProject::mylib_release ALIAS mylib)
endif()
```

### Exemplo: Bibliotecas Opcionais

```cmake
# Biblioteca principal
add_library(core src/core.cpp)
add_library(MyProject::core ALIAS core)

# Biblioteca opcional
option(ENABLE_IO "Enable I/O library" ON)
if(ENABLE_IO)
    add_library(io src/io.cpp)
    add_library(MyProject::io ALIAS io)
endif()

# Executável que usa dependências
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE MyProject::core)

if(ENABLE_IO)
    target_link_libraries(myapp PRIVATE MyProject::io)
endif()
```

### Exemplo: Testes

```cmake
# Biblioteca do projeto
add_library(mylib src/mylib.cpp)
add_library(MyProject::mylib ALIAS mylib)

# Testes que usam o mesmo target
enable_testing()

add_executable(test_mylib tests/test_mylib.cpp)
target_link_libraries(test_mylib PRIVATE MyProject::mylib)
add_test(NAME test_mylib COMMAND test_mylib)

# Se mylib mudar, test_mylib é recompilado automaticamente
```

### Exemplo: Múltiplos Projetos

```cmake
# Estrutura:
# project/
#   CMakeLists.txt
#   libs/
#     core/CMakeLists.txt
#     utils/CMakeLists.txt
#   app/CMakeLists.txt

# project/CMakeLists.txt
cmake_minimum_required(VERSION 3.16)
project(MyProject LANGUAGES CXX)

add_subdirectory(libs/core)
add_subdirectory(libs/utils)
add_subdirectory(app)

# libs/core/CMakeLists.txt
add_library(core src/core.cpp)
add_library(MyProject::core ALIAS core)
target_include_directories(core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# libs/utils/CMakeLists.txt
add_library(utils src/utils.cpp)
add_library(MyProject::utils ALIAS utils)
target_include_directories(utils PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_link_libraries(utils PUBLIC MyProject::core)

# app/CMakeLists.txt
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE
    MyProject::core
    MyProject::utils
)
```

### Cuidados Comuns

1. **Aliases não são targets reais**: Você não pode modificar propriedades de um alias.

2. **Aliases são case-sensitive**: `MyProject::mylib` e `myproject::mylib` são diferentes.

3. **Aliases e GLOBAL**: Use `add_library(... ALIAS ... GLOBAL)` se precisar que o alias seja visível em subdiretórios.

4. **Aliases e IMPORTED**: Você pode criar aliases para targets IMPORTED.

---

## 2.9 Object Libraries: Reutilização de Object Files

### Conceito

Object libraries são bibliotecas que compilam fontes em object files, mas não os linkam em uma biblioteca final. Os object files podem ser reutilizados por múltiplos targets.

### Quando Usar

1. **Reutilização de object files**: Mesmos object files usados por múltiplos targets.
2. **Evitar recompilação**: Compilar uma vez, usar em vários lugares.
3. **Flexibilidade**: Combinar object files de diferentes maneiras.
4. **Testes**: Criar bibliotecas de teste que usam os mesmos object files.

### Exemplo Básico

```cmake
# Object library
add_library(myobjlib OBJECT
    src/core.cpp
    src/utils.cpp
)

target_include_directories(myobjlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

target_compile_features(myobjlib PUBLIC cxx_std_17)

# Usar em múltiplos targets
add_library(staticlib STATIC $<TARGET_OBJECTS:myobjlib>)
add_library(sharedlib SHARED $<TARGET_OBJECTS:myobjlib>)
add_executable(myapp src/main.cpp $<TARGET_OBJECTS:myobjlib>)
```

### Exemplo: Biblioteca Estática e Compartilhada

```cmake
# Object library para código comum
add_library(common OBJECT
    src/common1.cpp
    src/common2.cpp
    src/common3.cpp
)

target_include_directories(common
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_options(common
    PRIVATE
        -Wall
        -Wextra
)

# Biblioteca estática
add_library(staticlib STATIC $<TARGET_OBJECTS:common>)
set_target_properties(staticlib PROPERTIES
    OUTPUT_NAME "mylib"
    ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
)

# Biblioteca compartilhada
add_library(sharedlib SHARED $<TARGET_OBJECTS:common>)
set_target_properties(sharedlib PROPERTIES
    OUTPUT_NAME "mylib"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib"
    VERSION 1.0.0
    SOVERSION 1
)

# Executável
add_executable(myapp src/main.cpp $<TARGET_OBJECTS:common>)
target_link_libraries(myapp PRIVATE sharedlib)
```

### Exemplo: Testes

```cmake
# Object library para código de teste
add_library(test_objects OBJECT
    tests/mock_core.cpp
    tests/mock_utils.cpp
    tests/test_helpers.cpp
)

target_include_directories(test_objects
    PRIVATE
        ${CMAKE_SOURCE_DIR}/include
        ${CMAKE_SOURCE_DIR}/tests
)

target_compile_features(test_objects PRIVATE cxx_std_17)

# Múltiplos executáveis de teste
add_executable(test_core
    tests/test_core.cpp
    $<TARGET_OBJECTS:test_objects>
)
target_link_libraries(test_core PRIVATE GTest::gtest_main)

add_executable(test_utils
    tests/test_utils.cpp
    $<TARGET_OBJECTS:test_objects>
)
target_link_libraries(test_utils PRIVATE GTest::gtest_main)

add_executable(test_integration
    tests/test_integration.cpp
    $<TARGET_OBJECTS:test_objects>
)
target_link_libraries(test_integration PRIVATE GTest::gtest_main)
```

### Exemplo: Plataformas Diferentes

```cmake
# Object library para código comum
add_library(common OBJECT
    src/common.cpp
    src/utils.cpp
)

# Código específico por plataforma
if(WIN32)
    add_library(platform OBJECT
        src/windows/platform.cpp
        src/windows/registry.cpp
    )
elseif(APPLE)
    add_library(platform OBJECT
        src/macos/platform.cpp
        src/macos/foundation.cpp
    )
elseif(UNIX)
    add_library(platform OBJECT
        src/linux/platform.cpp
        src/linux/proc.cpp
    )
endif()

# Biblioteca final combina comum + plataforma
add_library(mylib STATIC
    $<TARGET_OBJECTS:common>
    $<TARGET_OBJECTS:platform>
)

# Ou executável
add_executable(myapp
    src/main.cpp
    $<TARGET_OBJECTS:common>
    $<TARGET_OBJECTS:platform>
)
target_link_libraries(myapp PRIVATE mylib)
```

### Exemplo: Object Libraries com Propriedades

```cmake
# Object library com propriedades específicas
add_library(myobjlib OBJECT
    src/core.cpp
    src/utils.cpp
)

target_include_directories(myobjlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src/internal
)

target_compile_options(myobjlib
    PRIVATE
        -Wall
        -Wextra
)

target_compile_definitions(myobjlib
    PRIVATE
        MYOBJLIB_BUILDING=1
    PUBLIC
        MYOBJLIB_API_VERSION=1
)

# Usar em staticlib
add_library(staticlib STATIC $<TARGET_OBJECTS:myobjlib>)
target_link_libraries(staticlib PUBLIC myobjlib)

# Usar em sharedlib
add_library(sharedlib SHARED $<TARGET_OBJECTS:myobjlib>)
target_link_libraries(sharedlib PUBLIC myobjlib)
```

### Exemplo: Object Libraries com Generator Expressions

```cmake
# Object library com comportamento condicional
add_library(myobjlib OBJECT
    src/core.cpp
    src/utils.cpp
)

target_compile_definitions(myobjlib
    PRIVATE
        $<$<CONFIG:Debug>:DEBUG=1>
        $<$<CONFIG:Release>:NDEBUG=1>
)

target_compile_options(myobjlib
    PRIVATE
        $<$<CONFIG:Debug>:-g -O0>
        $<$<CONFIG:Release>:-O3>
)

# Usar em múltiplos targets
add_library(staticlib STATIC $<TARGET_OBJECTS:myobjlib>)
add_library(sharedlib SHARED $<TARGET_OBJECTS:myobjlib>)
add_executable(myapp src/main.cpp $<TARGET_OBJECTS:myobjlib>)
```

### Exemplo: Object Libraries para Headers

```cmake
# Object library que também fornece headers
add_library(myobjlib OBJECT
    src/core.cpp
    src/utils.cpp
)

target_include_directories(myobjlib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# Interface library para headers apenas
add_library(myheaders INTERFACE)
target_include_directories(myheaders
    INTERFACE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)

# Usar headers em outros targets
add_executable(otherapp src/other.cpp)
target_link_libraries(otherapp PRIVATE myheaders)
```

### Cuidados Comuns

1. **Object libraries não são linkadas**: Você precisa usar `$<TARGET_OBJECTS:...>` para incluir os object files.

2. **Propriedades não propagam automaticamente**: Use `target_link_libraries(target PUBLIC objectlib)` para propagar propriedades.

3. **Object libraries e instalação**: Object libraries não são instaladas por padrão.

4. **Object libraries e IDEs**: Algumas IDEs não mostram Object libraries na árvore de projetos.

---

## 2.10 IMPORTED Targets: Integração com find_package

### Conceito

IMPORTED targets são targets que representam bibliotecas ou executáveis pré-compilados, geralmente encontrados por `find_package` ou `find_library`.

### Por que Usar IMPORTED Targets?

1. **Integração limpa**: Bibliotecas externas são tratadas como targets normais.
2. **Propriedades automáticas**: Include directories, libraries, e defines são configurados automaticamente.
3. **Namespace**: Targets IMPORTED geralmente usam namespaces (ex: `Boost::filesystem`).
4. **Propagação**: Propriedades são propagadas corretamente.

### Exemplo Básico

```cmake
# Encontrar biblioteca externa
find_package(Threads REQUIRED)

# Usar IMPORTED target
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE Threads::Threads)
```

### Exemplo: Múltiplas Bibliotecas

```cmake
# Encontrar múltiplas bibliotecas
find_package(Threads REQUIRED)
find_package(Boost REQUIRED COMPONENTS filesystem system)
find_package(OpenSSL REQUIRED)

# Usar IMPORTED targets
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE
    Threads::Threads
    Boost::filesystem
    Boost::system
    OpenSSL::SSL
    OpenSSL::Crypto
)
```

### Exemplo: Bibliotecas com Configurações

```cmake
# Encontrar biblioteca com configurações específicas
find_package(Boost REQUIRED COMPONENTS filesystem system)

# IMPORTED target já tem configurações corretas
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE Boost::filesystem Boost::system)

# Não precisa configurar include directories manualmente
# O IMPORTED target já tem isso configurado
```

### Exemplo: Bibliotecas Opcionais

```cmake
# Encontrar bibliotecas opcionais
find_package(Boost OPTIONAL_COMPONENTS filesystem system)

# Verificar se foram encontrados
if(Boost_FILESYSTEM_FOUND)
    add_library(mylib src/mylib.cpp)
    target_link_libraries(mylib PRIVATE Boost::filesystem)
endif()
```

### Exemplo: IMPORTED Targets Manuais

```cmake
# Criar IMPORTED target manualmente
add_library(external_lib IMPORTED STATIC)

set_target_properties(external_lib PROPERTIES
    IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/libexternal.a"
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
)

# Usar IMPORTED target
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE external_lib)
```

### Exemplo: IMPORTED Targets Globais

```cmake
# IMPORTED target global (visível em subdiretórios)
add_library(external_lib IMPORTED GLOBAL STATIC)

set_target_properties(external_lib PROPERTIES
    IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/libexternal.a"
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
)

# Usar em subdiretórios
add_subdirectory(subdir)
```

### Exemplo: IMPORTED Targets com Propriedades

```cmake
# IMPORTED target com propriedades complexas
add_library(external_lib IMPORTED STATIC)

set_target_properties(external_lib PROPERTIES
    IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/libexternal.a"
    INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
    INTERFACE_COMPILE_DEFINITIONS "EXTERNAL_USE_SSE42=1"
    INTERFACE_COMPILE_OPTIONS "-msse4.2"
    INTERFACE_LINK_LIBRARIES "Threads::Threads"
)

# Usar IMPORTED target
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE external_lib)
```

### Exemplo: IMPORTED Targets por Plataforma

```cmake
# IMPORTED target diferente por plataforma
if(WIN32)
    add_library(external_lib IMPORTED STATIC)
    set_target_properties(external_lib PROPERTIES
        IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/win/libexternal.lib"
        INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
    )
elseif(APPLE)
    add_library(external_lib IMPORTED STATIC)
    set_target_properties(external_lib PROPERTIES
        IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/macos/libexternal.a"
        INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
    )
elseif(UNIX)
    add_library(external_lib IMPORTED STATIC)
    set_target_properties(external_lib PROPERTIES
        IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/lib/linux/libexternal.a"
        INTERFACE_INCLUDE_DIRECTORIES "${CMAKE_SOURCE_DIR}/include"
    )
endif()
```

### Exemplo: IMPORTED Targets para Executáveis

```cmake
# IMPORTED executable
add_executable(external_tool IMPORTED)

set_target_properties(external_tool PROPERTIES
    IMPORTED_LOCATION "${CMAKE_SOURCE_DIR}/bin/external_tool"
)

# Usar em custom command
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/output.txt
    COMMAND external_tool --input input.txt --output output.txt
    DEPENDS input.txt
)
```

### Exemplo: IMPORTED Targets com Versões

```cmake
# IMPORTED target com versão
find_package(Boost 1.70.0 REQUIRED COMPONENTS filesystem)

# IMPORTED target já tem versão configurada
add_library(mylib src/mylib.cpp)
target_link_libraries(mylib PRIVATE Boost::filesystem)
```

### Cuidados Comuns

1. **IMPORTED targets não são instalados**: Eles representam bibliotecas pré-existentes.

2. **IMPORTED targets e Aliases**: Você pode criar aliases para IMPORTED targets.

3. **IMPORTED targets e propagate**: IMPORTED targets propagam suas propriedades INTERFACE.

4. **IMPORTED targets e find_package**: `find_package` geralmente cria IMPORTED targets automaticamente.

---

## 2.11 Custom Targets: add_custom_target, add_custom_command

### Conceito

Custom targets e custom commands permitem executar comandos arbitrários durante a build. Eles são úteis para geração de código, processamento de arquivos, e outras tarefas.

### add_custom_target

```cmake
add_custom_target(mytarget
    COMMAND ${CMAKE_COMMAND} -E echo "Hello from custom target"
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Executing my custom target"
    VERBATIM
)
```

### add_custom_command

```cmake
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/output.txt
    COMMAND ${CMAKE_COMMAND} -E echo "Generating output"
    COMMAND ${CMAKE_COMMAND} -E copy input.txt output.txt
    DEPENDS input.txt
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Generating output file"
    VERBATIM
)
```

### Exemplo: Geração de Código

```cmake
# Gerar código a partir de um template
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/generated.cpp
    COMMAND ${CMAKE_COMMAND} -E env
        PYTHONPATH=${CMAKE_SOURCE_DIR}/tools
        python3 ${CMAKE_SOURCE_DIR}/tools/code_generator.py
            --input ${CMAKE_SOURCE_DIR}/templates/template.cpp
            --output ${CMAKE_CURRENT_BINARY_DIR}/generated.cpp
    DEPENDS
        ${CMAKE_SOURCE_DIR}/tools/code_generator.py
        ${CMAKE_SOURCE_DIR}/templates/template.cpp
    COMMENT "Generating code from template"
    VERBATIM
)

# Usar arquivo gerado
add_library(mylib
    src/core.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/generated.cpp
)
```

### Exemplo: Processamento de Arquivos

```cmake
# Processar múltiplos arquivos
file(GLOB_RECURSE INPUT_FILES "${CMAKE_SOURCE_DIR}/data/*.txt")

foreach(INPUT_FILE ${INPUT_FILES})
    get_filename_component(BASENAME ${INPUT_FILE} NAME)
    set(OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/processed/${BASENAME}.bin)

    add_custom_command(
        OUTPUT ${OUTPUT_FILE}
        COMMAND ${CMAKE_COMMAND} -E env
            python3 ${CMAKE_SOURCE_DIR}/tools/processor.py
                --input ${INPUT_FILE}
                --output ${OUTPUT_FILE}
        DEPENDS ${INPUT_FILE}
        COMMENT "Processing ${BASENAME}"
        VERBATIM
    )

    list(APPEND OUTPUT_FILES ${OUTPUT_FILE})
endforeach()

# Custom target para processar todos
add_custom_target(process_data ALL
    DEPENDS ${OUTPUT_FILES}
)
```

### Exemplo: Geração de Documentação

```cmake
# Gerar documentação com Doxygen
find_package(Doxygen REQUIRED)

set(DOXYGEN_INPUT_DIR ${CMAKE_SOURCE_DIR}/include)
set(DOXYGEN_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/docs)
set(DOXYGEN_INDEX_FILE ${DOXYGEN_OUTPUT_DIR}/html/index.html)

file(GLOB_RECURSE DOXYGEN_INPUT_FILES
    "${DOXYGEN_INPUT_DIR}/*.hpp"
    "${DOXYGEN_INPUT_DIR}/*.cpp"
)

add_custom_command(
    OUTPUT ${DOXYGEN_INDEX_FILE}
    COMMAND ${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    DEPENDS ${DOXYGEN_INPUT_FILES}
    COMMENT "Generating documentation with Doxygen"
    VERBATIM
)

add_custom_target(docs ALL
    DEPENDS ${DOXYGEN_INDEX_FILE}
)
```

### Exemplo: Geração de Recursos

```cmake
# Gerar recursos binários
set(RESOURCE_FILES
    ${CMAKE_SOURCE_DIR}/resources/icon.png
    ${CMAKE_SOURCE_DIR}/resources/splash.png
    ${CMAKE_SOURCE_DIR}/resources/background.png
)

set(OUTPUT_FILES "")
foreach(RESOURCE ${RESOURCE_FILES})
    get_filename_component(BASENAME ${RESOURCE} NAME)
    set(OUTPUT_FILE ${CMAKE_CURRENT_BINARY_DIR}/resources/${BASENAME}.h)

    add_custom_command(
        OUTPUT ${OUTPUT_FILE}
        COMMAND ${CMAKE_COMMAND} -E env
            python3 ${CMAKE_SOURCE_DIR}/tools/resource_compiler.py
                --input ${RESOURCE}
                --output ${OUTPUT_FILE}
                --name ${BASENAME}
        DEPENDS ${RESOURCE}
        COMMENT "Compiling resource ${BASENAME}"
        VERBATIM
    )

    list(APPEND OUTPUT_FILES ${OUTPUT_FILE})
endforeach()

# Custom target para compilar todos os recursos
add_custom_target(compile_resources ALL
    DEPENDS ${OUTPUT_FILES}
)

# Biblioteca que depende dos recursos
add_library(mylib src/mylib.cpp)
add_dependencies(mylib compile_resources)
```

### Exemplo: Custom Target com Dependências

```cmake
# Custom target com dependências complexas
add_custom_target(run_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    DEPENDS test_core test_utils test_integration
    COMMENT "Running all tests"
    VERBATIM
)

# Custom target para limpeza
add_custom_target(clean_all
    COMMAND ${CMAKE_COMMAND} -E remove_directory ${CMAKE_CURRENT_BINARY_DIR}
    COMMENT "Cleaning all build files"
    VERBATIM
)
```

### Exemplo: Custom Command para Build

```cmake
# Custom command que gera arquivo para build
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/version.h
    COMMAND ${CMAKE_COMMAND} -E env
        python3 ${CMAKE_SOURCE_DIR}/tools/version_generator.py
            --output ${CMAKE_CURRENT_BINARY_DIR}/version.h
            --git-dir ${CMAKE_SOURCE_DIR}
    DEPENDS ${CMAKE_SOURCE_DIR}/tools/version_generator.py
    COMMENT "Generating version header"
    VERBATIM
)

# Usar arquivo gerado
add_library(mylib
    src/core.cpp
    ${CMAKE_CURRENT_BINARY_DIR}/version.h
)

target_include_directories(mylib
    PRIVATE
        ${CMAKE_CURRENT_BINARY_DIR}
)
```

### Exemplo: Custom Target para Instalação

```cmake
# Custom target para instalação personalizada
add_custom_target(install_custom
    COMMAND ${CMAKE_COMMAND} -E echo "Installing custom files"
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_SOURCE_DIR}/custom_files
        ${CMAKE_INSTALL_PREFIX}/custom
    COMMENT "Installing custom files"
    VERBATIM
)
```

### Cuidados Comuns

1. **VERBATIM**: Sempre use VERBATIM para evitar problemas com espaços em argumentos.

2. **DEPENDS**: Especifique todas as dependências para que o CMake saiba quando re-executar.

3. **WORKING_DIRECTORY**: Especifique o diretório de trabalho correto.

4. **COMMENT**: Adicione comentários para facilitar o debug.

---

## 2.12 Generator Expressions: $<TARGET_PROPERTY:...>

### Conceito

Generator expressions são expressões avaliadas em tempo de geração (durante a build), não em tempo de configuração (durante cmake). Elas são particularmente úteis para comportamento condicional.

### Sintaxe Básica

```cmake
# Sintaxe geral
$<expression>

# Exemplos
$<CONFIG:Debug>
$<CXX_COMPILER_ID:GNU>
$<PLATFORM_ID:Linux>
$<TARGET_PROPERTY:property_name>
```

### Tipos de Generator Expressions

#### Expressões Condicionais

```cmake
# Condição simples
$<CONFIG:Debug>  # Verdadeiro se config for Debug

# Condição composta
$<$<CONFIG:Debug>:DEBUG=1>  # Define DEBUG=1 se config for Debug

# AND
$<$<AND:$<CONFIG:Debug>,$<CXX_COMPILER_ID:GNU>>:DEBUG_GCC=1>

# OR
$<$<OR:$<CONFIG:Debug>,$<CONFIG:RelWithDebInfo>>:DEBUG_INFO=1>

# NOT
$<$<NOT:$<CONFIG:Release>>:DEBUG_MODE=1>
```

#### Expressões de Propriedade

```cmake
# Propriedade de target
$<TARGET_PROPERTY:property_name>

# Propriedade de target com default
$<TARGET_PROPERTY:property_name,DEFAULT_VALUE>

# Propriedade de diretório
$<TARGET_PROPERTY:property_name,DIRECTORY>
```

#### Expressões de Compilador

```cmake
# ID do compilador
$<CXX_COMPILER_ID:GNU>  # Verdadeiro se GCC
$<CXX_COMPILER_ID:Clang>  # Verdadeiro se Clang
$<CXX_COMPILER_ID:MSVC>  # Verdadeiro se MSVC

# Versão do compilador
$<CXX_COMPILER_VERSION:8.0>
```

#### Expressões de Plataforma

```cmake
# Plataforma
$<PLATFORM_ID:Windows>
$<PLATFORM_ID:Linux>
$<PLATFORM_ID:Darwin>
```

#### Expressões de Build

```cmake
# Tipo de build
$<CONFIG:Debug>
$<CONFIG:Release>
$<CONFIG:RelWithDebInfo>
$<CONFIG:MinSizeRel>
```

### Exemplo Básico

```cmake
add_library(mylib src/mylib.cpp)

target_compile_definitions(mylib
    PRIVATE
        $<$<CONFIG:Debug>:DEBUG=1>
        $<$<CONFIG:Release>:NDEBUG=1>
)

target_compile_options(mylib
    PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra>
        $<$<CXX_COMPILER_ID:MSVC>:/W4>
)
```

### Exemplo: Propriedades de Target

```cmake
# Usar propriedades de target em generator expressions
add_library(mylib src/mylib.cpp)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

target_compile_definitions(mylib
    PUBLIC
        $<TARGET_PROPERTY:INTERFACE_COMPILE_DEFINITIONS>
)
```

### Exemplo: Comportamento Condicional

```cmake
# Flags diferentes por compilador e configuração
add_library(mylib src/mylib.cpp)

target_compile_options(mylib
    PRIVATE
        # GCC Debug
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Debug>>:-g -O0 -fsanitize=address>

        # GCC Release
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Release>>:-O3 -DNDEBUG>

        # Clang Debug
        $<$<AND:$<CXX_COMPILER_ID:Clang>,$<CONFIG:Debug>>:-g -O0 -fsanitize=address>

        # Clang Release
        $<$<AND:$<CXX_COMPILER_ID:Clang>,$<CONFIG:Release>>:-O3 -DNDEBUG>

        # MSVC
        $<$<CXX_COMPILER_ID:MSVC>:/W4 /O2>
)
```

### Exemplo: Definições por Plataforma

```cmake
add_library(mylib src/mylib.cpp)

target_compile_definitions(mylib
    PRIVATE
        # Windows
        $<$<PLATFORM_ID:Windows>:PLATFORM_WINDOWS=1>
        $<$<PLATFORM_ID:Windows>:WIN32_LEAN_AND_MEAN=1>
        $<$<PLATFORM_ID:Windows>:NOMINMAX=1>

        # Linux
        $<$<PLATFORM_ID:Linux>:PLATFORM_LINUX=1>

        # macOS
        $<$<PLATFORM_ID:Darwin>:PLATFORM_MACOS=1>
)
```

### Exemplo: Include Directories Condicionais

```cmake
add_library(mylib src/mylib.cpp)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        $<$<PLATFORM_ID:Windows>:${CMAKE_CURRENT_SOURCE_DIR}/platform/windows>
        $<$<PLATFORM_ID:Linux>:${CMAKE_CURRENT_SOURCE_DIR}/platform/linux>
        $<$<PLATFORM_ID:Darwin>:${CMAKE_CURRENT_SOURCE_DIR}/platform/macos>
)
```

### Exemplo: Link Libraries Condicionais

```cmake
add_library(mylib src/mylib.cpp)

target_link_libraries(mylib
    PRIVATE
        $<$<PLATFORM_ID:Windows>:ws2_32>
        $<$<PLATFORM_ID:Linux>:pthread>
        $<$<PLATFORM_ID:Darwin>:-framework CoreFoundation>
)
```

### Exemplo: Install Paths

```cmake
# Configurar paths de instalação
install(TARGETS mylib
    LIBRARY DESTINATION
        $<IF:$<PLATFORM_ID:Windows>,bin,lib>
    ARCHIVE DESTINATION
        $<IF:$<PLATFORM_ID:Windows>,lib,lib>
    RUNTIME DESTINATION
        $<IF:$<PLATFORM_ID:Windows>,bin,bin>
)
```

### Exemplo: Custom Commands

```cmake
# Usar generator expressions em custom commands
add_custom_command(
    OUTPUT output.txt
    COMMAND
        $<$<PLATFORM_ID:Windows>:cmd /c>
        $<$<NOT:$<PLATFORM_ID:Windows>>:${CMAKE_COMMAND} -E>
        echo "Hello from $<PLATFORM_ID:Windows>"
    VERBATIM
)
```

### Exemplo: Propriedades Complexas

```cmake
# Propriedades complexas com generator expressions
add_library(mylib src/mylib.cpp)

target_compile_options(mylib
    PRIVATE
        # Warnings diferentes por compilador
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Wpedantic>
        $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>

        # Otimização por configuração
        $<$<CONFIG:Debug>:-g -O0>
        $<$<CONFIG:Release>:-O3 -DNDEBUG>
        $<$<CONFIG:RelWithDebInfo>:-g -O2 -DNDEBUG>

        # Flags específicas por compilador e configuração
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Debug>>:-fsanitize=address>
        $<$<AND:$<CXX_COMPILER_ID:GNU>,$<CONFIG:Release>>:-fstack-protector-strong>
)
```

### Cuidados Comuns

1. **Não confunda com variáveis**: Generator expressions são avaliadas em tempo de geração, não em tempo de configuração.

2. **Escopo correto**: Generator expressions só funcionam em contextos suportados pelo CMake.

3. **Performance**: Evite generator expressions complexas em loops grandes.

4. **Debug**: Use `message(STATUS "...")` para debugar generator expressions.

---

## 2.13 Exemplo Completo: Biblioteca Modular com Targets

### Estrutura do Projeto

```
modular_project/
├── CMakeLists.txt
├── libs/
│   ├── core/
│   │   ├── CMakeLists.txt
│   │   ├── include/
│   │   │   └── core/
│   │   │       ├── core.hpp
│   │   │       └── types.hpp
│   │   └── src/
│   │       └── core.cpp
│   ├── utils/
│   │   ├── CMakeLists.txt
│   │   ├── include/
│   │   │   └── utils/
│   │   │       ├── string_utils.hpp
│   │   │       └── file_utils.hpp
│   │   └── src/
│   │       ├── string_utils.cpp
│   │       └── file_utils.cpp
│   └── io/
│       ├── CMakeLists.txt
│       ├── include/
│       │   └── io/
│       │       ├── reader.hpp
│       │       └── writer.hpp
│       └── src/
│           ├── reader.cpp
│           └── writer.cpp
├── app/
│   ├── CMakeLists.txt
│   └── src/
│       └── main.cpp
├── tests/
│   ├── CMakeLists.txt
│   └── test_core.cpp
└── config/
    ├── compiler_config.cmake
    └── platform_config.cmake
```

### Arquivo Raiz: CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(ModularProject
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Projeto modular com targets"
)

# Configuração padrão
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Opções de build
option(BUILD_TESTS "Build tests" ON)
option(BUILD_SHARED_LIBS "Build shared libraries" ON)
option(ENABLE_WARNINGS "Enable strict warnings" ON)

# Adicionar configurações
include(config/compiler_config.cmake)
include(config/platform_config.cmake)

# Adicionar bibliotecas
add_subdirectory(libs/core)
add_subdirectory(libs/utils)
add_subdirectory(libs/io)

# Adicionar aplicação
add_subdirectory(app)

# Adicionar testes
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Configurar instalação
install(EXPORT ModularProjectTargets
    FILE ModularProjectTargets.cmake
    NAMESPACE ModularProject::
    DESTINATION lib/cmake/ModularProject
)
```

### Configuração do Compilador: config/compiler_config.cmake

```cmake
# Configuração do compilador
add_library(compiler_config INTERFACE)

target_compile_features(compiler_config INTERFACE cxx_std_17)

if(ENABLE_WARNINGS)
    target_compile_options(compiler_config
        INTERFACE
            $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
            $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Wpedantic -Wshadow -Wformat=2>
            $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
    )
endif()

target_compile_definitions(compiler_config
    INTERFACE
        $<$<CONFIG:Debug>:DEBUG=1>
        $<$<CONFIG:Release>:NDEBUG=1>
        $<$<CXX_COMPILER_ID:MSVC>:_CRT_SECURE_NO_WARNINGS>
        $<$<CXX_COMPILER_ID:MSVC>:NOMINMAX>
)
```

### Configuração da Plataforma: config/platform_config.cmake

```cmake
# Configuração da plataforma
add_library(platform_config INTERFACE)

target_compile_definitions(platform_config
    INTERFACE
        $<$<PLATFORM_ID:Windows>:PLATFORM_WINDOWS=1>
        $<$<PLATFORM_ID:Linux>:PLATFORM_LINUX=1>
        $<$<PLATFORM_ID:Darwin>:PLATFORM_MACOS=1>
)

if(WIN32)
    target_link_libraries(platform_config INTERFACE ws2_32 winmm)
elseif(APPLE)
    target_link_libraries(platform_config INTERFACE "-framework CoreFoundation")
elseif(UNIX)
    target_link_libraries(platform_config INTERFACE pthread dl)
endif()
```

### Biblioteca Core: libs/core/CMakeLists.txt

```cmake
# Biblioteca core
add_library(core
    src/core.cpp
)

# Configurar include directories
target_include_directories(core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Configurar dependências
target_link_libraries(core
    PUBLIC
        compiler_config
        platform_config
)

# Configurar propriedades
set_target_properties(core PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "include/core/core.hpp;include/core/types.hpp"
)

# Criar alias
add_library(ModularProject::core ALIAS core)

# Configurar instalação
install(TARGETS core
    EXPORT ModularProjectTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    PUBLIC_HEADER DESTINATION include/core
)
```

### Biblioteca Utils: libs/utils/CMakeLists.txt

```cmake
# Biblioteca utils
add_library(utils
    src/string_utils.cpp
    src/file_utils.cpp
)

# Configurar include directories
target_include_directories(utils
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Configurar dependências
target_link_libraries(utils
    PUBLIC
        ModularProject::core
        compiler_config
        platform_config
)

# Configurar propriedades
set_target_properties(utils PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "include/utils/string_utils.hpp;include/utils/file_utils.hpp"
)

# Criar alias
add_library(ModularProject::utils ALIAS utils)

# Configurar instalação
install(TARGETS utils
    EXPORT ModularProjectTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    PUBLIC_HEADER DESTINATION include/utils
)
```

### Biblioteca IO: libs/io/CMakeLists.txt

```cmake
# Biblioteca io
add_library(io
    src/reader.cpp
    src/writer.cpp
)

# Configurar include directories
target_include_directories(io
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)

# Configurar dependências
target_link_libraries(io
    PUBLIC
        ModularProject::core
        ModularProject::utils
        compiler_config
        platform_config
)

# Configurar propriedades
set_target_properties(io PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "include/io/reader.hpp;include/io/writer.hpp"
)

# Criar alias
add_library(ModularProject::io ALIAS io)

# Configurar instalação
install(TARGETS io
    EXPORT ModularProjectTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    PUBLIC_HEADER DESTINATION include/io
)
```

### Aplicação: app/CMakeLists.txt

```cmake
# Aplicação principal
add_executable(myapp
    src/main.cpp
)

# Configurar dependências
target_link_libraries(myapp
    PRIVATE
        ModularProject::core
        ModularProject::utils
        ModularProject::io
        compiler_config
        platform_config
)

# Configurar propriedades
set_target_properties(myapp PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Configurar instalação
install(TARGETS myapp
    RUNTIME DESTINATION bin
)
```

### Testes: tests/CMakeLists.txt

```cmake
# Encontrar framework de teste
find_package(GTest REQUIRED)

# Teste core
add_executable(test_core
    test_core.cpp
)

target_link_libraries(test_core
    PRIVATE
        ModularProject::core
        GTest::gtest_main
)

add_test(NAME test_core COMMAND test_core)

# Teste utils
add_executable(test_utils
    test_utils.cpp
)

target_link_libraries(test_utils
    PRIVATE
        ModularProject::utils
        GTest::gtest_main
)

add_test(NAME test_utils COMMAND test_utils)

# Teste io
add_executable(test_io
    test_io.cpp
)

target_link_libraries(test_io
    PRIVATE
        ModularProject::io
        GTest::gtest_main
)

add_test(NAME test_io COMMAND test_io)
```

### Executando o Projeto

```bash
# Criar diretório de build
mkdir build && cd build

# Configurar
cmake .. -DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTS=ON

# Compilar
cmake --build .

# Rodar testes
ctest --output-on-failure

# Instalar
cmake --install . --prefix /usr/local
```

---

## 2.14 Exercícios

### Exercício 1: INTERFACE Library para Configuração

Crie uma INTERFACE library chamada `project_config` que:
- Requer C++17
- Adiciona warnings estritos para GCC e Clang
- Define `_CRT_SECURE_NO_WARNINGS` para MSVC
- Configura `DEBUG=1` para builds Debug

**Dica**: Use `target_compile_features`, `target_compile_options`, e `target_compile_definitions`.

### Exercício 2: Biblioteca com Propriedades Múltiplas

Crie uma biblioteca `mylib` com:
- Headers públicos em `include/`
- Headers privados em `src/internal/`
- Definição pública `MYLIB_API_VERSION=1`
- Definição privada `MYLIB_BUILDING=1`
- Flags de warning apenas para implementação
- Propagação de `-pthread` para dependentes

**Dica**: Use `target_include_directories` com `PUBLIC` e `PRIVATE`, e `target_compile_definitions` com `PUBLIC` e `PRIVATE`.

### Exercício 3: Object Library para Testes

Crie uma Object library `test_helpers` que:
- Compile arquivos de teste comuns
- Tenha include directories para testes
- Seja usada por múltiplos executáveis de teste
- Propague dependências necessárias

**Dica**: Use `add_library(... OBJECT)` e `$<TARGET_OBJECTS:...>`.

### Exercício 4: IMPORTED Target Manual

Crie um IMPORTED target para uma biblioteca externa:
- Defina `IMPORTED_LOCATION` para um arquivo `.a` ou `.lib`
- Configure `INTERFACE_INCLUDE_DIRECTORIES`
- Adicione `INTERFACE_COMPILE_DEFINITIONS`
- Use o target em uma biblioteca do projeto

**Dica**: Use `add_library(... IMPORTED)` e `set_target_properties`.

### Exercício 5: Custom Target para Geração de Código

Crie um custom target que:
- Execute um script Python para gerar código
- Gere um arquivo `generated.hpp`
- Seja dependência de uma biblioteca
- Execute apenas quando os inputs mudarem

**Dica**: Use `add_custom_command` com `OUTPUT` e `DEPENDS`, e `add_custom_target` com `ALL`.

### Exercício 6: Generator Expressions Complexas

Crie configurações de compilação usando generator expressions que:
- Apliquem flags diferentes para GCC, Clang e MSVC
- Configure otimizações por tipo de build (Debug/Release)
- Adicionem defines específicos por plataforma
- Use AND/OR para condições compostas

**Dica**: Use `$<$<AND:...>:...>`, `$<$<OR:...>:...>`, e combinações de `$<CXX_COMPILER_ID:...>`, `$<CONFIG:...>`, `$<PLATFORM_ID:...>`.

### Exercício 7: Projeto Completo com Aliases

Crie um projeto completo que:
- Tenha 3 bibliotecas com aliases `Project::name`
- Use `find_package` para dependências externas
- Configure instalação com exports
- Permita uso via `add_subdirectory` e `find_package`

**Dica**: Use `add_library(... ALIAS ...)` e `install(EXPORT ...)`.

---

## 2.15 Referências

### Documentação Oficial

- [CMake Target Properties](https://cmake.org/cmake/help/latest/manual/cmake-properties.7.html)
- [target_compile_features](https://cmake.org/cmake/help/latest/command/target_compile_features.html)
- [target_include_directories](https://cmake.org/cmake/help/latest/command/target_include_directories.html)
- [target_compile_definitions](https://cmake.org/cmake/help/latest/command/target_compile_definitions.html)
- [target_compile_options](https://cmake.org/cmake/help/latest/command/target_compile_options.html)
- [target_link_libraries](https://cmake.org/cmake/help/latest/command/target_link_libraries.html)
- [Generator Expressions](https://cmake.org/cmake/help/latest/manual/cmake-generator-expressions.7.html)
- [IMPORTED Targets](https://cmake.org/cmake/help/latest/manual/cmake-buildsystem.7.html#imported-targets)
- [Object Libraries](https://cmake.org/cmake/help/latest/command/add_library.html#object-libraries)

### Livros e Artigos

- "Mastering CMake" - Kitware
- "CMake Best Practices" - Dominik Berner, Agustín K. Ballone
- "Effective CMake" - Daniel Pfeifer (apresentação)
- "Modern CMake" - Jason Turner

### Projetos de Referência

- [CMake Cookbook](https://github.com/dev-cafe/cmake-cookbook)
- [Modern CMake Examples](https://github.com/vectorclass/version-benchmark)
- [CMake Examples](https://github.com/AcademySoftwareFoundation/cmake-example)

### Comunidades

- [CMake Discourse](https://discourse.cmake.org/)
- [Stack Overflow - CMake Tag](https://stackoverflow.com/questions/tagged/cmake)
- [CMake Mailing Lists](https://cmake.org/mailing-lists/)

---

**Fim do Capítulo 02: Target Model e Properties**

No próximo capítulo, exploraremos [Gerenciamento de Dependências](03-expressoes-funcoes.md), incluindo find_package, FetchContent, e gerenciamento de pacotes externos.
