---
layout: default
title: "03-expressoes-funcoes"
---

# Capitulo 03 — Expressoes e Funcoes do CMake

> *"Quem controla o build, controla o que entra no binario."*

---

## Sumario

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Generator Expressions: Sintaxe e Uso](#2-generator-expressions-sintaxe-e-uso)
3. [Condicionais: if(), elseif(), else()](#3-condicionais-if-elseif-else)
4. [Loops: foreach(), while()](#4-loops-foreach-while)
5. [Funcoes: function(), macro() — Diferencas Criticas](#5-functions-macro-diferencas-criticas)
6. [Scope: Parent Scope, PARENT_SCOPE](#6-scope-parent-scope-parent_scope)
7. [Argument Parsing: cmake_parse_arguments()](#7-argument-parsing-cmake_parse_arguments)
8. [Listas e Strings: Operacoes Comuns](#8-listas-e-strings-operacoes-comuns)
9. [Math Expressions: math(EXPR)](#9-math-expressions-math-expr)
10. [File Operations: file(READ), file(WRITE), file(GLOB)](#10-file-operations-fileread-filewrite-fileglob)
11. [Custom Commands: add_custom_command()](#11-custom-commands-add_custom_command)
12. [Configure File: configure_file()](#12-configure-file-configure_file)
13. [Exemplo: Funcao Reutilizavel para Hardening](#13-exemplo-funcao-reutilizavel-para-hardening)
14. [Exercicios](#14-exercicios)
15. [Anti-Padroes e Cuidados Comuns](#15-anti-padroes-e-cuidados-comuns)
16. [Referencias](#16-referencias)

---

## 1. Objetivos de Aprendizado

Apos completar este capitulo, o leitor sera capaz de:

- Diferenciar generator expressions de expressoes de tempo de configuracao
- Usar condicionais `if()`, `elseif()`, `else()` de forma segura e correta
- Iterar sobre listas com `foreach()` e `while()`
- Criar funcoes e macros CMake, entendendo as diferencas criticas de escopo
- Gerenciar escopo de variaveis com `PARENT_SCOPE`
- Parsear argumentos de funcoes com `cmake_parse_arguments()`
- Manipular listas e strings com operacoes nativas do CMake
- Expressar operacoes aritmeticas com `math(EXPR)`
- Realizar operacoes de arquivo com `file()`
- Definir custom commands para geracao de codigo e pre-processamento
- Usar `configure_file()` para gerar headers de configuracao
- Construir uma funcao reutilizavel de hardening de compilador

### Por que este capitulo importa para seguranca

Expressoes e funcoes sao o "tejido conjuntivo" de qualquer CMakeLists.txt nao trivial. Decoes aqui tem impacto direto na seguranca:

- Um `if()` com variavel nao-quoteada pode ser explorado via injection de caminho
- Uma `function()` que nao valida argumentos pode aceitar valores perigosos
- Um `file(GLOB)` sem restricao pode incluir arquivos sensiveis no build
- Um `configure_file()` pode vazar informacoes de ambiente em headers publicos
- Um `add_custom_command()` mal configurado pode executar codigo arbitrario

Entender profundamente estas construcoes e o primeiro passo para escrever CMake que protege, nao expoe.

---

## 2. Generator Expressions: Sintaxe e Uso

### 2.1 O que sao generator expressions

Generator expressions (genexps) sao expressoes avaliadas pelo gerador de build (Make, Ninja, Visual Studio, Xcode) durante a geracao — nao durante a execucao do CMake. Isso e fundamental porque o CMake executa duas fases:

1. **Fase de configuracao**: o CMakeLists.txt e avaliado, variaveis e propriedades sao definidas
2. **Fase de geracao**: o build system e realmente produzido (Makefiles, build.ninja, etc.)

Genexps so existem na segunda fase. Isso permite que uma unica CMakeLists.txt gere configs diferentes para Debug, Release, multi-config generators, e ate mesmo para targets diferentes dentro do mesmo projeto.

### 2.2 Sintaxe basica

Genexps sempre comecam com `$<` e terminam com `>`. O conteudo entre os delimitadores define o tipo de expressao:

```cmake
$<expression>
```

### 2.3 Tipos de generator expressions

#### Expressoes booleanas

```cmake
# Expressao de condicao: $<condition:true_string>
$<1:hello>       # Sempre produz "hello" (1 = true)
$<0:hello>       # Sempre produz nada (0 = false)

# Combinacao: $<condition:output>
target_compile_definitions(mylib PRIVATE
    $<$<BOOL:${ENABLE_FEATURE_X}>:FEATURE_X_ENABLED>
)

# Variacao: expressoes compostas
target_compile_options(mylib PRIVATE
    $<$<AND:$<BOOL:${ENABLE_DEBUG}>,$<NOT:$<PLATFORM_ID:Windows>>>:-g3>
)
```

#### $<0:...> e $<1:...>

Sao os interruptores binarios mais basicos:

```cmake
# Sempre inclui o conteudo (true)
$<1:DEBUG_MODE>

# Nunca inclui o conteudo (false)
$<0:SECRET_VALUE>
```

#### $<BOOL:...>

Avalia uma string como condicao booleana. Sera falso para: `0`, `OFF`, `NO`, `FALSE`, `N`, `IGNORE`, `NOTFOUND`, string vazia, ou string terminada em `-NOTFOUND`.

```cmake
target_compile_definitions(mylib PRIVATE
    $<$<BOOL:${CMAKE_BUILD_TYPE}>:BUILD_TYPE_DEFINED>
)

# Exemplo pratico: so incluir hardening em builds de release
target_compile_options(mylib PRIVATE
    $<$<BOOL:${CMAKE_BUILD_TYPE}>:
        $<$<NOT:$<CONFIG:Debug>>:-D_FORTIFY_SOURCE=2>
    >
)
```

#### $<CONFIG:...>

Testa a configuracao atual (Debug, Release, RelWithDebInfo, MinSizeRel):

```cmake
target_compile_options(myapp PRIVATE
    $<$<CONFIG:Debug>:-O0 -g3 -fsanitize=address,undefined>
    $<$<CONFIG:Release>:-O2 -DNDEBUG>
    $<$<CONFIG:RelWithDebInfo>:-O2 -g -DNDEBUG>
    $<$<CONFIG:MinSizeRel>:-Os -DNDEBUG>
)
```

Para multi-config generators (Visual Studio, Xcode), essa expressao e avaliada por target, nao por build. O CMake gera configuracoes para todas as configs possiveis.

#### $<PLATFORM_ID:...>

Testa o ID da plataforma (Linux, Windows, Darwin):

```cmake
target_compile_definitions(mylib PRIVATE
    $<$<PLATFORM_ID:Linux>:PLATFORM_LINUX>
    $<$<PLATFORM_ID:Windows>:PLATFORM_WINDOWS>
    $<$<PLATFORM_ID:DARWIN>:PLATFORM_MACOS>
)
```

#### $<CXX_COMPILER_ID:...> e $<C_COMPILER_ID:...>

Testa o compilador:

```cmake
target_compile_options(mylib PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:Clang>:-Weverything -Wno-c++98-compat>
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)
```

#### $<TARGET_OBJECTS:tgt>

Inclui todos os object files de um object library:

```cmake
add_library(objects OBJECT lib1.cpp lib2.cpp)
add_library(mylib PRIVATE $<TARGET_OBJECTS:objects>)
```

#### $<TARGET_FILE:tgt> e $<TARGET_FILE_NAME:tgt>

Referencia o arquivo de saida de um target:

```cmake
add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_STRIP} $<TARGET_FILE:myapp>
    COMMENT "Stripping symbols from myapp"
)
```

#### $<TARGET_PROPERTY:tgt,prop>

Acessa uma propriedade de um target:

```cmake
target_include_directories(mylib PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Em outro target, pode acessar a propriedade do mylib
target_include_directories(myapp PRIVATE
    $<TARGET_PROPERTY:mylib,INTERFACE_INCLUDE_DIRECTORIES>
)
```

#### $<INSTALL_PREFIX:...>

Produz caminhos relativos ao prefixo de instalacao:

```cmake
install(FILES config.json DESTINATION ${CMAKE_INSTALL_PREFIX}/etc/myapp)
```

#### $<LIST:...>

Agrega multiplos items em uma unica expressao:

```cmake
target_compile_options(mylib PRIVATE
    $<LIST:,-Wall,-Wextra,-Wpedantic>
)
```

### 2.4 Operadores logicos

Genexps suportam operadores booleanos:

```cmake
# AND: $<AND:expr1;expr2;...>
$<$<AND:$<CONFIG:Debug>,$<CXX_COMPILER_ID:GNU>>:-O0 -g3>

# OR: $<OR:expr1;expr2;...>
$<$<OR:$<PLATFORM_ID:Linux>,$<PLATFORM_ID:DARWIN>>:-fPIC>

# NOT: $<NOT:expr>
$<$<NOT:$<CONFIG:Debug>>:-O2>
```

### 2.5 Multi-config generators

Multi-config generators (Visual Studio, Xcode, Ninja Multi-Config) sao uma area onde genexps brilham. Com single-config generators (Makefiles, Ninja), `CMAKE_BUILD_TYPE` e definido no momento da configuracao. Com multi-config, a configuracao e escolhida no momento da build:

```cmake
# Isso NAO funciona com multi-config generators:
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2")  # ERRADO

# Isso funciona com ambos:
target_compile_options(mylib PRIVATE
    $<$<CONFIG:Release>:-O2>
    $<$<CONFIG:Debug>:-O0 -g3>
)
```

### 2.6 Seguranca: genexps e injection

Generator expressions sao avaliadas pelo gerador de build, nao pelo shell. Isso significa que, por padrao, elas nao sofrem shell injection. Porem, se o valor de uma variavel CMake contiver caracteres perigosos e for usado em genexps que terminam em comandos de shell, o resultado pode ser inseguro:

```cmake
# PERIGOSO: variavel de usuario sem validacao
set(USER_INPUT "$ENV{USER_INPUT}")
target_compile_options(mylib PRIVATE
    $<$<BOOL:${USER_INPUT}>:${USER_INPUT}>  # Pode injetar flags
)

# SEGURO: validar antes de usar
if(NOT USER_INPUT MATCHES "^[a-zA-Z0-9_]+$")
    message(FATAL_ERROR "Invalid USER_INPUT")
endif()
target_compile_options(mylib PRIVATE
    $<$<BOOL:${USER_INPUT}>:-DUSER_DEFINED=${USER_INPUT}>
)
```

### 2.7 Limitacoes de genexps

Genexps NAO podem ser usadas em todos os contextos. Elas so funcionam em propriedades de target e comandos que aceitam genexps explicitamente:

```cmake
# Genexp funciona: target_compile_options aceita genexps
target_compile_options(mylib PRIVATE $<$<CONFIG:Debug>:-g>)

# Genexp NAO funciona: if() nao aceita genexps
if($<CONFIG:Debug>)  # ERRO em tempo de configuracao
    message("Debug mode")
endif()

# Genexp NAO funciona: message() nao aceita genexps
message($<$<CONFIG:Debug>:Debug mode>)  # ERRO

# Genexp NAO funciona: variaveis sao avaliadas em tempo de configuracao
set(MY_FLAG $<$<CONFIG:Debug>:-g>)  # Armazena a string literal, nao avalia
```

### 2.8 Tabela de referencia rapida

| Expressao | Descricao | Exemplo |
|-----------|-----------|---------|
| `$<0:s>` | Sempre vazio | `$<0:secret>` -> `` |
| `$<1:s>` | Sempre `s` | `$<1:hello>` -> `hello` |
| `$<BOOL:v>` | Booleano | `$<BOOL:OFF>` -> `0` |
| `$<CONFIG:c>` | Config igual a `c` | `$<CONFIG:Debug>` |
| `$<PLATFORM_ID:p>` | Plataforma | `$<PLATFORM_ID:Linux>` |
| `$<CXX_COMPILER_ID:c>` | Compilador | `$<CXX_COMPILER_ID:GNU>` |
| `$<AND:e;e;...>` | AND logico | `$<AND:1;1>` -> `1` |
| `$<OR:e;e;...>` | OR logico | `$<OR:0;1>` -> `1` |
| `$<NOT:e>` | NOT logico | `$<NOT:0>` -> `1` |
| `$<TARGET_PROPERTY:t,p>` | Propriedade | `$<TARGET_PROPERTY:lib,SOVERSION>` |
| `$<TARGET_FILE:t>` | Arquivo de saida | `$<TARGET_FILE:myapp>` |

---

## 3. Condicionais: if(), elseif(), else()

### 3.1 Sintaxe basica

O `if()` do CMake e uma das construcoes mais usadas — e mais mal compreendidas:

```cmake
if(condition)
    # bloco verdadero
elseif(another_condition)
    # segundo bloco
else()
    # bloco padrao
endif()
```

### 3.2 Regras de avaliacao do if()

O `if()` do CMake tem regras de avaliacao contraintuitivas. Entender essas regras e CRITICO para seguranca:

**Regra 1**: Se o argumento e uma variavel definida, o `if()` avaliara o CONTEUDO da variavel, nao a existencia dela:

```cmake
set(myvar "TRUE")
if(myvar)           # Avalia "TRUE" -> true
    message("OK")
endif()

# Para testar se uma variavel EXISTE:
if(DEFINED myvar)   # true: myvar esta definida
    message("Variable exists")
endif()
```

**Regra 2**: Strings que nao parecem booleanas sao avaliadas como variaveis ou constantes numericas:

```cmake
set(myvar "hello")
if(myvar)  # Avalia "hello" -> tenta como variavel -> "hello" como constante -> ERRO ou resultado inesperado
endif()
```

**Regra 3**: O CMake tenta fazer "match" do valor em varias categorias:

1. Bool constante conhecida: `TRUE`, `1`, `ON`, `YES`, `Y` (e mais)
2. Bool constante falsa: `0`, `OFF`, `NO`, `N`, `IGNORE`, `NOTFOUND`, string vazia, string terminada em `-NOTFOUND`
3. Constante numerica: `+123`, `-123`
4. Variavel definida: se `DEFINED`
5. Target: se `TARGET`
6. String de caminho: se `IS_ABSOLUTE` ou `EXISTS`
7. Expressao de teste: se comeca com `EXISTS`, `COMMAND`, `DEFINED`, `IN_LIST`, etc.
8. Par de strings: `str1 OP str2`

### 3.3 Operadores de comparacao

```cmake
# Igualdade
if(var STREQUAL "value")     # Comparacao de string
if(var EQUAL 42)             # Comparacao numerica

# Desigualdade
if(var STRLESS "value")      # Lexicografica menor
if(var LESS 42)              # Numerica menor
if(var GREATER 42)           # Numerica maior

# Match de expressao regular
if(var MATCHES "^[0-9]+$")  # Regex match
```

### 3.4 Testes unarios

```cmake
if(EXISTS "/path/to/file")    # Arquivo ou diretorio existe
if(IS_DIRECTORY "/path")      # E um diretorio
if(IS_ABSOLUTE "/absolute")   # Caminho e absoluto
if(DEFINED var)               # Variavel esta definida
if(TARGET mylib)              # Target foi criado com add_library ou add_executable
if(var IN_LIST mylist)        # var esta na lista mylist (CMake 3.6+)
if(COMMAND function_name)     # Funcao/macro/comando existe
```

### 3.5 Operadores logicos

```cmake
# NOT
if(NOT condition)

# AND
if(cond1 AND cond2)

# OR
if(cond1 OR cond2)

# Parenteses (ajudam legibilidade)
if((cond1 AND cond2) OR cond3)
```

### 3.6 Seguranca: quoting de variaveis

O ERRO MAIS COMUM e esquecer de colocar variaveis entre aspas. Isso pode causar problemas serios:

```cmake
set(USER_PATH "/home/user")

# PERIGOSO: sem aspas - caminhos com espacos quebram
if(EXISTS ${USER_PATH}/file.txt)    # Pode quebrar

# SEGURO: com aspas
if(EXISTS "${USER_PATH}/file.txt")  # Funciona sempre

# PERIGOSO: variavel nao definida se torna string vazia
if(${UNDEFINED_VAR} STREQUAL "hello")  # Avalia "" STREQUAL "hello"
# Deveria ser:
if("${UNDEFINED_VAR}" STREQUAL "hello")
```

### 3.7 Seguranca: validacao de inputs

Em build systems de seguranca, validar inputs antes de usar em condicionais e essencial:

```cmake
# NUNCA aceitar path de usuario direto em condicionais
set(USER_DIR "$ENV{USER_DIR}")

# Validar que nao e vazio, nao contem traversal, e e absoluto
if("${USER_DIR}" STREQUAL "")
    message(FATAL_ERROR "USER_DIR must not be empty")
endif()

if(NOT IS_ABSOLUTE "${USER_DIR}")
    message(FATAL_ERROR "USER_DIR must be absolute path")
endif()

if("${USER_DIR}" MATCHES "\\.\\.")
    message(FATAL_ERROR "USER_DIR must not contain ..")
endif()

if(NOT IS_DIRECTORY "${USER_DIR}")
    message(FATAL_ERROR "USER_DIR must be an existing directory")
endif()
```

### 3.8 Seguranca: padroes perigosos com if()

Padroes que devem ser EVITADO em build systems seguros:

```cmake
# 1. NAO usar variavel de ambiente diretamente em if()
# PERIGOSO:
if($ENV{DEBUG_MODE})  # Qualquer valor nao-falso ativa

# SEGURO:
set(debug_mode "$ENV{DEBUG_MODE}")
if("${debug_mode}" STREQUAL "1")
    # debug mode
endif()

# 2. NAO usar if() para testar existencia sem DEFINED
# PERIGOSO:
if(${MY_VAR})  # Se MY_VAR nao existe, avaliacao indefinida

# SEGURO:
if(DEFINED MY_VAR AND NOT "${MY_VAR}" STREQUAL "")
    # MY_VAR existe e nao e vazio
endif()

# 3. NAO confundir NOT com negacao
# PERIGOSO:
if(NOT "yes" STREQUAL "no")  # Avalia como: NOT ("yes" STREQUAL "no") -> NOT FALSE -> TRUE
# Mas se quiser:
if(NOT ("yes" STREQUAL "no"))  # O mesmo, mas parenteses tornam explicito
```

### 3.9 Padroes de seguranca com if()

```cmake
# Padrao: verificacao em cascata de inputs de usuario
macro(validate_build_option option_name value)
    if("${value}" STREQUAL "")
        message(FATAL_ERROR "${option_name} must not be empty")
    endif()
    if("${value}" MATCHES "[;&|`$]")
        message(FATAL_ERROR "${option_name} contains dangerous characters")
    endif()
endmacro()

validate_build_option("MY_OPTION" "${MY_OPTION}")

# Padrao: deteccao segura de plataforma
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(PLATFORM_LINUX TRUE)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(PLATFORM_WINDOWS TRUE)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(PLATFORM_MACOS TRUE)
else()
    message(WARNING "Unsupported platform: ${CMAKE_SYSTEM_NAME}")
endif()

# Padrao: deteccao segura de compilador
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set(COMPILER_GCC TRUE)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    set(COMPILER_CLANG TRUE)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    set(COMPILER_MSVC TRUE)
else()
    message(WARNING "Unknown compiler: ${CMAKE_CXX_COMPILER_ID}")
endif()
```

---

## 4. Loops: foreach(), while()

### 4.1 foreach() basico

O `foreach()` itera sobre uma lista de valores:

```cmake
foreach(item RANGE 0 9)
    message("Item: ${item}")
endforeach()

foreach(color IN LISTS my_colors)
    message("Color: ${color}")
endforeach()

foreach(file IN ITEMS lib1.cpp lib2.cpp lib3.cpp)
    message("File: ${file}")
endforeach()
```

### 4.2 Formas de foreach()

#### Range

```cmake
foreach(i RANGE 0 10)       # 0, 1, 2, ..., 10
    message("${i}")
endforeach()

foreach(i RANGE 0 10 2)    # 0, 2, 4, 6, 8, 10 (step 2)
    message("${i}")
endforeach()

foreach(i RANGE 10 0 -1)   # 10, 9, 8, ..., 0 (decrescente)
    message("${i}")
endforeach()
```

#### LISTS

```cmake
set(my_list "a" "b" "c")
foreach(item IN LISTS my_list)
    message("${item}")
endforeach()
```

#### ITEMS

```cmake
foreach(item IN ITEMS "hello world" "foo bar")
    # Cada item e tratado como uma unidade, mesmo com espacos
    message("${item}")
endforeach()
```

#### ZIP

Disponivel desde CMake 3.17:

```cmake
set(keys "A" "B" "C")
set(values 1 2 3)

foreach(key value IN ZIP_LISTS keys values)
    message("${key} = ${value}")
endforeach()
# Output:
# A = 1
# B = 2
# C = 3
```

### 4.3 foreach() e seguranca

Loops em CMakeLists.txt sao frequentemente usados para iterar sobre listas de arquivos, dependencias ou opcoes. Cada caso tem implicacoes de seguranca:

```cmake
# PERIGOSO: file(GLOB) em loop sem validacao
file(GLOB user_files "$ENV{USER_UPLOAD_DIR}/*")
foreach(file IN LISTS user_files)
    configure_file(${file} ${CMAKE_BINARY_DIR}/generated/)  # Pode incluir arquivos perigosos
endforeach()

# SEGURO: filtrar antes de iterar
file(GLOB user_files "$ENV{USER_UPLOAD_DIR}/*.cpp")
foreach(file IN LISTS user_files)
    # Validar que o arquivo esta dentro do diretorio esperado
    get_filename_component(real_file "${file}" REALPATH)
    if(real_file MATCHES "^${CMAKE_CURRENT_SOURCE_DIR}/src/")
        configure_file(${file} ${CMAKE_BINARY_DIR}/generated/)
    endif()
endforeach()

# PERIGOSO: iterar sobre lista de comandos
set(dangerous_commands "rm -rf /" "dd if=/dev/zero of=/dev/sda")
foreach(cmd IN LISTS dangerous_commands)
    execute_process(COMMAND sh -c "${cmd}")  # EXECUTA O COMANDO
endforeach()

# SEGURO: lista de comandos deve ser controlada pelo build system
set(allowed_commands "cmake --version" "gcc --version")
foreach(cmd IN LISTS allowed_commands)
    # Comando validado, executar com controle
    execute_process(COMMAND ${cmd} OUTPUT_VARIABLE output)
endforeach()
```

### 4.4 while()

O `while()` continua enquanto a condicao for verdadeira:

```cmake
set(counter 0)
while(counter LESS 10)
    message("Counter: ${counter}")
    math(EXPR counter "${counter} + 1")
endforeach()
```

### 4.5 Seguranca: loops infinitos

Loops infinitos em CMakeLists.txt podem travar o build inteiro. Sempre inclua uma condicao de saida:

```cmake
# PERIGOSO: sem limite de iteracao
set(value "")
while(NOT value)
    # Se value nunca mudar, loop infinito
    set(value "${SOME_CONDITION}")
endforeach()

# SEGURO: com limite de seguranca
set(iterations 0)
set(max_iterations 1000)
while(NOT value AND iterations LESS max_iterations)
    set(value "${SOME_CONDITION}")
    math(EXPR iterations "${iterations} + 1")
endforeach()
if(iterations GREATER_EQUAL max_iterations)
    message(FATAL_ERROR "Loop exceeded maximum iterations - possible infinite loop")
endif()
```

### 4.6 break() e continue()

```cmake
foreach(file IN LISTS all_files)
    # Pular arquivos que nao sao .cpp
    get_filename_component(ext "${file}" EXT)
    if(NOT "${ext}" STREQUAL ".cpp")
        continue()
    endif()

    # Processar ate encontrar um arquivo especifico
    if("${file}" MATCHES "special\\.cpp")
        message("Found special file: ${file}")
        break()
    endif()

    message("Processing: ${file}")
endforeach()
```

### 4.7 Padroes comuns de loops em build systems seguros

```cmake
# Padrao: iterar sobre targets com validacao
set(my_targets "lib1" "lib2" "lib3")
foreach(target_name IN LISTS my_targets)
    if(TARGET "${target_name}")
        target_compile_options("${target_name}" PRIVATE
            $<$<CXX_COMPILER_ID:GNU>:-Werror>
        )
    else()
        message(WARNING "Target ${target_name} not found")
    endif()
endforeach()

# Padrao: iterar sobre diretorios de inclusao com sanitizacao
set(include_dirs "/usr/include" "/usr/local/include" "$ENV{CUSTOM_INCLUDE}")
foreach(dir IN LISTS include_dirs)
    if(IS_ABSOLUTE "${dir}" AND IS_DIRECTORY "${dir}")
        include_directories("${dir}")
    endif()
endforeach()

# Padrao: processar arquivos de configuracao em lote
set(config_files "config_debug.json" "config_release.json" "config_test.json")
foreach(config IN LISTS config_files)
    if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${config}")
        configure_file(
            "${CMAKE_CURRENT_SOURCE_DIR}/${config}"
            "${CMAKE_CURRENT_BINARY_DIR}/${config}"
            COPYONLY
        )
    endif()
endforeach()
```

---

## 5. Funcoes: function(), macro() — Diferencas Criticas

### 5.1 function() — escopo novo

Funcoes CMO criam um novo escopo de variaveis. Variaveis locais nao afetam o escopo do chamador:

```cmake
function(my_function arg1 arg2)
    set(local_var "hello")  # Local a funcao
    message("${arg1} and ${arg2}")
endfunction()

# Uso:
my_function("foo" "bar")
# local_var nao existe aqui fora
```

### 5.2 macro() — substituicao textual

Macros NAO criam escopo novo. Elas sao expandidas textualmente no escopo do chamador:

```cmake
macro(my_macro arg1 arg2)
    set(local_var "hello")  # Afeta o escopo do chamador!
endmacro()

# Uso:
my_macro("foo" "bar")
message("${local_var}")  # "hello" — a macro modificou o escopo do chamador
```

### 5.3 Tabela comparativa

| Caracteristica | function() | macro() |
|---------------|------------|---------|
| Escopo de variaveis | Novo escopo | Escopo do chamador |
| `ARGV0`, `ARGV1`, ... | Disponiveis | Disponiveis |
| `ARGN` | Argumentos extras | Argumentos extras |
| `ARGC` | Contagem de argumentos | Contagem de argumentos |
| `return()` | Volta da funcao | Volta do escopo onde foi chamada |
| Performance | Levemente mais lenta | Mais rapida (sem escopo) |
| Argumentos sao... | Avaliados antes da chamada | Avaliados como parte da expansao |
| `cmake_policy` | Herda politicas do chamador | Nao herda politicas |

### 5.4 Diferenca critica: avaliacao de argumentos

Esta e a diferencas mais subestimada:

```cmake
# Em uma function(), os argumentos ja estao avaliados:
function(my_func val)
    message("Value: ${val}")
endfunction()

set(mylist "a" "b" "c")
my_func(${mylist})  # val = "a" — so o primeiro elemento!

# Para passar a lista inteira, use aspas:
my_func("${mylist}")  # val = "a;b;c"

# Em uma macro, a avaliacao e diferente:
macro(my_macro)
    # ARGV0 aqui sera avaliado como "a" se chamado com my_macro(${mylist})
    message("First: ${ARGV0}")
endmacro()
```

### 5.5 Quando usar function() vs macro()

**Use function() quando:**
- Precisa de escopo isolado (nao quer "vazamento" de variaveis)
- Argumentos podem conter listas ou valores complexos
- Funcao e chamada muitas vezes (performance menor e aceitavel)
- Precisa de `return()` para sair da funcao

**Use macro() quando:**
- Precisa modificar o escopo do chamador intencionalmente
- Performance e critica (evitar overhead de chamada)
- Implementacao e curta e simples
- Precisa de `cmake_parse_arguments()` com argumentos posicionais

```cmake
# BOA PRATICA: function() para a maioria dos casos
function(add_secure_compile_options target)
    if(NOT TARGET "${target}")
        message(FATAL_ERROR "Target ${target} does not exist")
    endif()
    target_compile_options("${target}" PRIVATE
        $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Werror -Wpedantic>
        $<$<CXX_COMPILER_ID:Clang>:-Wall -Wextra -Werror>
    )
endfunction()

# BOA PRATICA: macro() para helpers simples que precisam de escopo do chamador
macro(set_if_not_defined var value)
    if(NOT DEFINED ${var})
        set(${var} "${value}")
    endif()
endmacro()

set_if_not_defined(MY_OPTION "default_value")
message("${MY_OPTION}")  # "default_value" — a macro setou no escopo do chamador
```

### 5.6 Seguranca: funcoes e validacao

Funcoes devem validar seus argumentos antes de usa-los:

```cmake
function(add_secure_library)
    cmake_parse_arguments(
        PARSE_ARGV 0
        PARSED                     # prefix
        "STATIC;SHARED"            # options
        "NAME;SOURCES"             # one-value keywords
        "INCLUDES;LINK_LIBRARIES"  # multi-value keywords
    )

    # Validacao obrigatoria
    if("${PARSED_NAME}" STREQUAL "")
        message(FATAL_ERROR "NAME is required for add_secure_library")
    endif()

    if("${PARSED_SOURCES}" STREQUAL "")
        message(FATAL_ERROR "SOURCES is required for add_secure_library")
    endif()

    # Validacao de nomes de targets (nao pode conter caracteres perigosos)
    if("${PARSED_NAME}" MATCHES "[;&|`$\\\"]")
        message(FATAL_ERROR "Target name contains invalid characters: ${PARSED_NAME}")
    endif()

    # Criar a library
    if(PARSED_STATIC)
        add_library("${PARSED_NAME}" STATIC ${PARSED_SOURCES})
    elseif(PARSED_SHARED)
        add_library("${PARSED_NAME}" SHARED ${PARSED_SOURCES})
    else()
        add_library("${PARSED_NAME}" STATIC ${PARSED_SOURCES})
    endif()

    # Adicionar include directories com validacao
    foreach(dir IN LISTS PARSED_INCLUDES)
        if(IS_ABSOLUTE "${dir}" AND IS_DIRECTORY "${dir}")
            target_include_directories("${PARSED_NAME}" PRIVATE "${dir}")
        else()
            message(WARNING "Invalid include directory: ${dir}")
        endif()
    endforeach()
endfunction()
```

### 5.7 ARGV, ARGC, ARGN, ARGV0, ARGV1, ...

Estas variaveis especiais sao disponiveis dentro de functions e macros:

```cmake
function(print_all_args)
    message("Total args: ${ARGC}")
    message("All args (semicolon separated): ${ARGV}")
    message("Args beyond named: ${ARGN}")

    # Acessar argumentos individuais
    set(i 0)
    while(i LESS ARGC)
        message("ARGV${i} = ${ARGV${i}}")
        math(EXPR i "${i} + 1")
    endwhile()
endfunction()

print_all_args("hello" "world" "extra1" "extra2")
# Total args: 4
# All args: hello;world;extra1;extra2
# Args beyond named: extra1;extra2
# ARGV0 = hello
# ARGV1 = world
# ARGV2 = extra1
# ARGV3 = extra2
```

---

## 6. Scope: Parent Scope, PARENT_SCOPE

### 6.1 O problema do escopo

Cada `function()` e `macro()` cria (ou nao) um escopo. Variaveis definidas dentro de uma function NAO sao visiveis fora dela:

```cmake
function(my_func)
    set(internal_var "value")
endfunction()

my_func()
message("${internal_var}")  # Variavel vazia! internal_var nao existe aqui
```

### 6.2 PARENT_SCOPE

Para comunicar valores de volta ao chamador, use `PARENT_SCOPE`:

```cmake
function(get_value output_var)
    set(${output_var} "computed_value" PARENT_SCOPE)
endfunction()

get_value(my_result)
message("${my_result}")  # "computed_value"
```

### 6.3 Regras do PARENT_SCOPE

1. `PARENT_SCOPE` modifica a variavel no escopo PAI do chamador imediato
2. Se houver encadeamento de funcoes, `PARENT_SCOPE` vai subindo um nivel por vez
3. Modificacoes nao afetam o escopo local da funcao que fez o `set()`
4. Variavel deve ser passada como referencia (nome da variavel, nao valor)

```cmake
function(outer_func)
    inner_func()
    message("${result}")  # "inner_value" — inner_func setou via PARENT_SCOPE
endfunction()

function(inner_func)
    set(result "inner_value" PARENT_SCOPE)
    message("${result}")  # VAZIO aqui dentro! PARENT_SCOPE nao modifica escopo local
endfunction()

outer_func()
```

### 6.4 Seguranca: PARENT_SCOPE e vazamento de dados

`PARENT_SCOPE` pode causar vazamento nao intencional de variaveis sensiveis:

```cmake
# PERIGOSO: vazamento de dados sensiveis
function(process_secrets)
    set(SECRET_KEY "$ENV{SECRET_KEY}")
    # Qualquer chamada dentro pode acidentalmente usar ou propagar SECRET_KEY
    # via PARENT_SCOPE ou modificacao de variavel global

    # Se SECRET_KEY for modificado acidentalmente em um loop:
    foreach(item IN LISTS items)
        set(SECRET_KEY "${item}")  # Modificou a variavel local, mas se for global...
    endforeach()
endfunction()

# SEGURO: isolar dados sensiveis
function(process_data data)
    # Usar prefixo exclusivo para variaveis locais
    set(_process_data_internal "")
    foreach(item IN LISTS data)
        list(APPEND _process_data_internal "${item}_processed")
    endforeach()
    set(result "${_process_data_internal}" PARENT_SCOPE)
    # _process_data_internal morre com o escopo da funcao
endfunction()
```

### 6.5 Variaveis de cache vs variaveis normais

Variaveis de cache sao globais e persistem entre chamadas ao CMake. Variaveis normais sao locais ao escopo:

```cmake
# Variavel de cache (persiste, e global)
set(MY_OPTION "value" CACHE STRING "My option")

# Variavel normal (local ao escopo)
set(my_local "value")

# Para sobrescrever cache com variavel local:
set(MY_OPTION "new_value" CACHE STRING "My option" FORCE)
```

### 6.6 Seguranca: cache e FORCE

O operador `FORCE` sobrescreve variaveis de cache, mesmo que o usuario tenha definido:

```cmake
# NUNCA usar FORCE em opcoes que o usuario pode querer controlar
set(SECURE_BUILD ON CACHE BOOL "Enable secure build options")
# Se usar FORCE:
set(SECURE_BUILD ON CACHE BOOL "Enable secure build options" FORCE)  # Sobrescreve escolha do usuario

# BOA PRATICA: so usar FORCE para valores internos controlados pelo build system
set(_INTERNAL_VERSION "1.2.3" CACHE STRING "Internal version" FORCE)
```

### 6.7 Variaveis de ambiente e seguranca

Variaveis de ambiente (`$ENV{...}`) sao controladas pelo usuario do sistema e NUNCA devem ser confiadas sem validacao:

```cmake
# NUNCA fazer:
set(build_flags "$ENV{CXXFLAGS}")  # Usuario pode ter colocado algo perigoso
add_compile_options("${build_flags}")

# SEGURO: parsear e validar
set(user_flags "$ENV{CXXFLAGS}")
if(NOT "${user_flags}" STREQUAL "")
    # Separar por espacos e validar cada flag
    separate_arguments(user_flags_list UNIX_COMMAND "${user_flags}")
    foreach(flag IN LISTS user_flags_list)
        # Whitelist de flags permitidas
        if(flag MATCHES "^-O[0-3s]$"
           OR flag MATCHES "^-g$"
           OR flag MATCHES "^-Wall$"
           OR flag MATCHES "^-Wextra$")
            list(APPEND safe_flags "${flag}")
        else()
            message(WARNING "Ignoring potentially unsafe CXXFLAGS: ${flag}")
        endif()
    endforeach()
    add_compile_options(${safe_flags})
endif()
```

---

## 7. Argument Parsing: cmake_parse_arguments()

### 7.1 Sintaxe basica

`cmake_parse_arguments()` e a forma padrao do CMake de parsear argumentos nomeados:

```cmake
cmake_parse_arguments(
    <prefix>                        # Prefixo para as variaveis de resultado
    <options>                       # Argumentos booleanos (sem valor)
    <one_value_keywords>            # Argumentos que aceitam um valor
    <multi_value_keywords>          # Argumentos que aceitam uma lista
    ${ARGN}                         # Argumentos a serem parseados
)
```

### 7.2 Opcoes (booleanos)

```cmake
function(my_lib)
    cmake_parse_arguments(
        PARSED              # prefix
        "STATIC;SHARED"     # options
        "NAME"              # one-value keywords
        "SOURCES"           # multi-value keywords
        ${ARGN}
    )

    # PARSED_STATIC sera TRUE ou FALSE
    # PARSED_SHARED sera TRUE ou FALSE
    # PARSED_NAME tera o valor
    # PARSED_SOURCES tera a lista
endfunction()

my_lib(NAME mylib STATIC SOURCES a.cpp b.cpp)
# PARSED_STATIC = TRUE
# PARSED_NAME = "mylib"
# PARSED_SOURCES = "a.cpp;b.cpp"
```

### 7.3 Um valor (one-value keywords)

```cmake
function(set_target_version)
    cmake_parse_arguments(
        PARSED
        ""                    # options
        "NAME;VERSION"        # one-value keywords
        ""                    # multi-value keywords
        ${ARGN}
    )

    if(NOT DEFINED PARSED_VERSION)
        message(FATAL_ERROR "VERSION is required")
    endif()

    set_target_properties(${PARSED_NAME} PROPERTIES
        VERSION "${PARSED_VERSION}"
    )
endfunction()

set_target_version(NAME mylib VERSION 1.2.3)
```

### 7.4 Multi-valor

```cmake
function(add_test_suite)
    cmake_parse_arguments(
        PARSED
        ""
        "NAME;SUITE"
        "SOURCES;DEPENDENCIES"
        ${ARGN}
    )

    add_executable(${PARSED_NAME} ${PARSED_SOURCES})
    target_link_libraries(${PARSED_NAME} PRIVATE ${PARSED_DEPENDENCIES})
    add_test(NAME ${PARSED_SUITE}/${PARSED_NAME} COMMAND ${PARSED_NAME})
endfunction()

add_test_suite(
    NAME unit_tests
    SUITE core
    SOURCES test1.cpp test2.cpp
    DEPENDENCIES gtest gtest_main mylib
)
```

### 7.5 PARSE_ARGV (CMake 3.7+)

Desde CMake 3.7, `cmake_parse_arguments` aceita `PARSE_ARGV` para parsear argumentos diretamente da variavel `ARGV`:

```cmake
function(my_func)
    cmake_parse_arguments(
        PARSE_ARGV 0     # Comecar do indice 0
        PARSED
        "VERBOSE"
        "NAME"
        "SOURCES"
    )
    # Mesma funcionalidade, mas mais seguro para listas
endfunction()
```

A diferenca critica: com `PARSE_ARGV`, argumentos com espacos sao tratados corretamente como um unico argumento, nao como multiplos.

### 7.6 Seguranca: parseamento de argumentos

Argument parsing e um ponto critico de seguranca. Argumentos mal parseados podem levar a:

- Inclusao de arquivos nao intencionais
- Execucao de comandos nao autorizados
- Vazamento de informacoes

```cmake
function(secure_add_executable)
    cmake_parse_arguments(
        PARSE_ARGV 0
        PARSED
        "STATIC;SHARED;ENABLE_HARDENING"
        "NAME;OUTPUT_DIR;CXX_STANDARD"
        "SOURCES;INCLUDES;DEFINES;COMPILE_OPTIONS"
    )

    # Validacao obrigatoria
    if("${PARSED_NAME}" STREQUAL "")
        message(FATAL_ERROR "NAME is required")
    endif()

    if(NOT "${PARSED_NAME}" MATCHES "^[a-zA-Z][a-zA-Z0-9_-]*$")
        message(FATAL_ERROR "NAME must be a valid CMake target name")
    endif()

    if("${PARSED_SOURCES}" STREQUAL "")
        message(FATAL_ERROR "SOURCES is required")
    endif()

    # Validar que todas as fontes existem
    foreach(src IN LISTS PARSED_SOURCES)
        if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${src}")
            message(FATAL_ERROR "Source file does not exist: ${src}")
        endif()
    endforeach()

    # Validar OUTPUT_DIR se fornecido
    if(NOT "${PARSED_OUTPUT_DIR}" STREQUAL "")
        if(NOT IS_ABSOLUTE "${PARSED_OUTPUT_DIR}")
            set(PARSED_OUTPUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/${PARSED_OUTPUT_DIR}")
        endif()
        file(MAKE_DIRECTORY "${PARSED_OUTPUT_DIR}")
    endif()

    # Validar CXX_STANDARD
    if(NOT "${PARSED_CXX_STANDARD}" STREQUAL "")
        if(NOT PARSED_CXX_STANDARD MATCHES "^(14|17|20|23)$")
            message(FATAL_ERROR "CXX_STANDARD must be 14, 17, 20, or 23")
        endif()
    endif()

    # Criar target
    add_executable("${PARSED_NAME}" ${PARSED_SOURCES})

    # Aplicar configuracoes
    if(NOT "${PARSED_CXX_STANDARD}" STREQUAL "")
        set_target_properties("${PARSED_NAME}" PROPERTIES
            CXX_STANDARD "${PARSED_CXX_STANDARD}"
            CXX_STANDARD_REQUIRED ON
        )
    endif()

    # Hardening
    if(PARSED_ENABLE_HARDENING)
        target_compile_options("${PARSED_NAME}" PRIVATE
            $<$<CXX_COMPILER_ID:GNU>:
                -fstack-protector-strong
                -D_FORTIFY_SOURCE=2
                -Wformat -Wformat-security
            >
        )
        target_link_options("${PARSED_NAME}" PRIVATE
            $<$<PLATFORM_ID:Linux>:-Wl,-z,relro,-z,now>
        )
    endif()
endfunction()
```

### 7.7 Argumentos posicionais (nargs)

Para aceitar argumentos posicionais alem dos nomeados, voce precisa tratar manualmente:

```cmake
function(positional_args_func)
    # Os primeiros N argumentos sao posicionais
    set(positional_args "")
    set(named_args "")
    set(is_named FALSE)

    foreach(arg IN LISTS ARGN)
        if(arg MATCHES "^[A-Z_]+$" AND NOT arg STREQUAL "SOURCES")
            set(is_named TRUE)
        endif()

        if(is_named)
            list(APPEND named_args "${arg}")
        else()
            list(APPEND positional_args "${arg}")
        endif()
    endforeach()

    # Agora parsear os argumentos nomeados
    cmake_parse_arguments(
        PARSED ""
        "NAME"
        "SOURCES"
        ${named_args}
    )

    message("Positional: ${positional_args}")
    message("Name: ${PARSED_NAME}")
    message("Sources: ${PARSED_SOURCES}")
endfunction()
```

---

## 8. Listas e Strings: Operacoes Comuns

### 8.1 Listas no CMake

Listas no CMake sao strings separadas por ponto e virgula (`;`). Nao ha tipo "lista" separado:

```cmake
set(mylist "a" "b" "c")      # mylist = "a;b;c"
set(same_list "a;b;c")        # Mesmo resultado
```

### 8.2 Operacoes comuns com listas

#### list(LENGTH)

```cmake
set(mylist "a" "b" "c")
list(LENGTH mylist count)
message("Count: ${count}")  # 3
```

#### list(APPEND)

```cmake
set(mylist "")
list(APPEND mylist "a")
list(APPEND mylist "b" "c")
# mylist = "a;b;c"
```

#### list(PREPEND)

```cmake
set(mylist "c")
list(PREPEND mylist "a" "b")
# mylist = "a;b;c"
```

#### list(INSERT)

```cmake
set(mylist "a" "c")
list(INSERT mylist 1 "b")
# mylist = "a;b;c"
``()

#### list(REMOVE_ITEM)

```cmake
set(mylist "a" "b" "c" "b")
list(REMOVE_ITEM mylist "b")
# mylist = "a;c" — remove TODAS as ocorrencias
```

#### list(REMOVE_AT)

```cmake
set(mylist "a" "b" "c")
list(REMOVE_AT mylist 1)
# mylist = "a;c"
``()

#### list(GET)

```cmake
set(mylist "a" "b" "c")
list(GET mylist 0 first)
list(GET mylist -1 last)
# first = "a", last = "c"
```

#### list(FIND)

```cmake
set(mylist "a" "b" "c")
list(FIND mylist "b" index)
# index = 1
# Se nao encontrar: index = -1
```

#### list(SORT)

```cmake
set(mylist "c" "a" "b")
list(SORT mylist)
# mylist = "a;b;c"
```

#### list(JOIN)

```cmake
set(mylist "a" "b" "c")
list(JOIN mylist ", " result)
# result = "a, b, c"
```

#### list(TRANSFORM)

```cmake
set(mylist "a" "b" "c")
list(TRANSFORM mylist TOUPPER)
# mylist = "A;B;C"

list(TRANSFORM mylist APPEND ".cpp")
# mylist = "A.cpp;B.cpp;C.cpp"

list(TRANSFORM mylist REPLACE "^A" "X")
# mylist = "X.cpp;B.cpp;C.cpp"
```

### 8.3 Operacoes com strings

#### string()

```cmake
# Concatenacao
string(CONCAT result "Hello" " " "World")
# result = "Hello World"

# Comprimento
string(LENGTH "hello" len)
# len = 5

# Substring
string(SUBSTRING "hello world" 0 5 sub)
# sub = "hello"

# Replace
string(REPLACE "old" "new" result "old text old text")
# result = "new text new text"

# Regex match
string(REGEX MATCH "^[0-9]+" matched "123abc")
# matched = "123"

# Regex replace
string(REGEX REPLACE "([0-9]+)" "[\\1]" result "abc123def456")
# result = "abc[123]def[456]"

# Upper/Lower case
string(TOUPPER "hello" upper)
string(TOLOWER "HELLO" lower)

# Strip whitespace
string(STRIP "  hello  " stripped)
# stripped = "hello"

# Find
string(FIND "hello world" "world" pos)
# pos = 6
# If not found: pos = -1

# Hex
string(HEX "hello" hex)
# hex = "68656c6c6f"

# ASCII
string(ASCII 72 101 108 108 111 ascii)
# ascii = "Hello"
```

### 8.4 Seguranca: manipulacao de listas e strings

```cmake
# PERIGOSO: unquoting em foreach pode causar word splitting
set(user_input "file1.cpp;file2.cpp;file3.cpp")
foreach(file IN LISTS user_input)
    # Se user_input vier de input externo e conter espacos:
    # file1 with space.cpp sera dividido em "file1" e "with" e "space.cpp"
endforeach()

# SEGURO: sempre tratar como lista ou como string unica, nunca ambos
# Como lista (semicolon separated):
set(file_list "file1.cpp" "file2.cpp" "file3.cpp")
foreach(file IN LISTS file_list)
    # file e tratado como um item unico
endforeach()

# Como string unica (com espacos):
set(file_string "file with spaces.cpp")
# NAO usar foreach com LISTS nesse caso

# PERIGOSO: string(REGEX) com input de usuario pode causar ReDoS
set(user_pattern "$ENV{USER_REGEX}")
string(REGEX MATCH "${user_pattern}" matched "${input}")
# Se user_pattern for uma regex catastrófica (ex: "(a+)+$"), pode travar

# SEGURO: validar regex antes de usar
if(user_pattern MATCHES "[|*+?{]${2,}")
    message(FATAL_ERROR "Regex pattern too complex")
endif()

# PERIGOSO: string(REPLACE) com inputs que contem caracteres especiais
set(path "$ENV{USER_PATH}")
string(REPLACE "/" "\\\\" windows_path "${path}")
# Se path contiver \, resultado sera imprevisivel

# SEGURO: usar cmake_path (CMake 3.20+)
cmake_path(NATIVE_PATH "${path}" native_path)
```

### 8.5 Padroes uteis de manipulacao

```cmake
# Extrair extensao de arquivo
function(get_file_extension filename output_var)
    get_filename_component(ext "${filename}" EXT)
    set(${output_var} "${ext}" PARENT_SCOPE)
endfunction()

# Normalizar caminho
function(normalize_path path output_var)
    cmake_path(ABSOLUTE_PATH path NORMALIZE OUTPUT_VARIABLE normalized)
    set(${output_var} "${normalized}" PARENT_SCOPE)
endfunction()

# Validar que um path e relativo (para instalacao)
function(validate_relative_path path)
    if(IS_ABSOLUTE "${path}")
        message(FATAL_ERROR "Path must be relative: ${path}")
    endif()
    if("${path}" MATCHES "\\.\\.")
        message(FATAL_ERROR "Path must not contain ..: ${path}")
    endif()
endfunction()

# Converter lista para argumentos de shell
function(list_to_shell_args input_list output_var)
    set(result "")
    foreach(item IN LISTS input_list)
        string(APPEND result " \"${item}\"")
    endforeach()
    set(${output_var} "${result}" PARENT_SCOPE)
endfunction()
```

---

## 9. Math Expressions: math(EXPR)

### 9.1 Sintaxe

`math(EXPR)` executa expressoes aritmeticas inteiras:

```cmake
math(EXPR result "2 + 2")
# result = 4

math(EXPR result "10 * 5 + 3")
# result = 53

math(EXPR result "2 ** 8")
# result = 256

math(EXPR result "10 % 3")
# result = 1

math(EXPR result "-5 + 3")
# result = -2
```

### 9.2 Operadores suportados

| Operador | Descricao | Exemplo |
|----------|-----------|---------|
| `+` | Soma | `2 + 3` = 5 |
| `-` | Subtracao | `5 - 3` = 2 |
| `*` | Multiplicacao | `2 * 3` = 6 |
| `/` | Divisao inteira | `7 / 2` = 3 |
| `%` | Modulo | `7 % 2` = 1 |
| `**` | Potencia | `2 ** 8` = 256 |

### 9.3 Uso pratico

```cmake
# Contador de iteracao
set(i 0)
while(i LESS 10)
    math(EXPR i "${i} + 1")
    message("Iteration ${i}")
endforeach()

# Calcular tamanho de array
set(my_array "a" "b" "c" "d")
list(LENGTH my_array array_size)
math(EXPR last_index "${array_size} - 1")
message("Last index: ${last_index}")  # 3

# Operacoes com propriedades
set(major 1)
set(minor 2)
set(patch 3)
math(EXPR next_patch "${patch} + 1")
set(VERSION "${major}.${minor}.${next_patch}")

# Calcular offset em arquivo
set(header_size 16)
set(data_size 1024)
math(EXPR total_size "${header_size} + ${data_size}")
```

### 9.4 Limitacoes

`math(EXPR)` so trabalha com inteiros. Nao suporta ponto flutuante:

```cmake
math(EXPR result "3.14 * 2")  # ERRO: syntax error

# Para floats, use string operations ou mensagens com formatacao
set(pi "3.14")
set(diameter "10")
# Sem suporte nativo a float, precisa de workaround
```

### 9.5 Seguranca: math(EXPR)

```cmake
# PERIGOSO: expressao vinda de input externo
set(user_expr "$ENV{USER_EXPR}")
math(EXPR result "${user_expr}")  # Pode causar erro ou resultado inesperado

# SEGURO: validar antes de calcular
set(user_expr "$ENV{USER_EXPR}")
if(user_expr MATCHES "^[0-9+\\-*/%() ]+$")
    math(EXPR result "${user_expr}")
else()
    message(FATAL_ERROR "Invalid mathematical expression: ${user_expr}")
endif()

# PERIGOSO: overflow silencioso
set(a "2147483647")  # MAX_INT32
set(b "1")
math(EXPR result "${a} + ${b}")  # Resultado indefinido em alguns compiladores

# SEGURO: checar limites antes
set(a "2147483647")
set(b "1")
math(EXPR sum "${a} + ${b}")
if(sum LESS 0)
    message(FATAL_ERROR "Integer overflow detected")
endif()
```

---

## 10. File Operations: file(READ), file(WRITE), file(GLOB)

### 10.1 file(READ)

Le o conteudo de um arquivo para uma variavel:

```cmake
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/config.json" config_content)
message("${config_content}")
```

#### Offset e limit

```cmake
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/big_file.txt" first_100_bytes
     OFFSET 0 LIMIT 100)
```

### 10.2 file(WRITE)

Escreve conteudo em um arquivo (sobrescreve se existir):

```cmake
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp"
"// Auto-generated — do not edit
#include \"config.h\"
const char* VERSION = \"${PROJECT_VERSION}\";
"
)
```

### 10.3 file(APPEND)

Adiciona conteudo ao final de um arquivo:

```cmake
file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/log.txt"
    "Build started at ${CMAKE_CURRENT_LIST_FILE}:${CMAKE_CURRENT_LIST_LINE}\n"
)
```

### 10.4 file(GLOB) e file(GLOB_RECURSE)

Encontram arquivos usando padroes:

```cmake
# GLOB simples
file(GLOB sources "*.cpp" "*.c")
add_library(mylib ${sources})

# GLOB recursivo
file(GLOB_RECURSE all_headers "*.h" "*.hpp")

# GLOB com CONFIGURE_DEPENDS (CMake 3.12+)
file(GLOB sources CONFIGURE_DEPENDS "*.cpp")
# Gera aviso se novos arquivos aparecerem apos configuracao
```

### 10.5 file(DOWNLOAD)

Baixa arquivos:

```cmake
file(DOWNLOAD
    "https://example.com/data.json"
    "${CMAKE_CURRENT_BINARY_DIR}/data.json"
    EXPECTED_HASH SHA256=abc123...
    STATUS download_status
)
list(GET download_status 0 status_code)
if(NOT status_code EQUAL 0)
    message(FATAL_ERROR "Download failed")
endif()
```

### 10.6 file(MAKE_DIRECTORY)

Cria diretorios:

```cmake
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/generated")
```

### 10.7 file(RENAME)

Move ou renomeia arquivos:

```cmake
file(RENAME
    "${CMAKE_CURRENT_BINARY_DIR}/temp.cpp"
    "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp"
)
```

### 10.8 file(COPY)

Copia arquivos e diretorios:

```cmake
file(COPY "${CMAKE_CURRENT_SOURCE_DIR}/resources"
     DESTINATION "${CMAKE_CURRENT_BINARY_DIR}"
)
```

### 10.9 file(REMOVE) e file(REMOVE_RECURSE)

Remove arquivos ou diretorios:

```cmake
file(REMOVE "${CMAKE_CURRENT_BINARY_DIR}/temp.txt")
file(REMOVE_RECURSE "${CMAKE_CURRENT_BINARY_DIR}/generated")
```

### 10.10 Seguranca: operacoes de arquivo

Operacoes de arquivo sao os vetores de ataque mais criticos em build systems:

#### file(GLOB) e seguranca

```cmake
# PERIGOSO: GLOB sem restricao pode incluir arquivos sensiveis
file(GLOB everything "*")
# Pode incluir .env, .git/, secrets/, etc.

# PERIGOSO: GLOB_RECURSE em diretorio de upload
file(GLOB_RECURSE user_files "$ENV{UPLOAD_DIR}/*")
# Pode incluir qualquer coisa que o usuario tenha uploadado

# SEGURO: GLOB com filtros especificos
file(GLOB sources "*.cpp" "*.c")
file(GLOB headers "*.h" "*.hpp")
file(GLOB config_files "config_*.json")

# SEGURO: GLOB com CONFIGURE_DEPENDS para detectar mudancas
file(GLOB_RECURSE sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
)
```

#### file(DOWNLOAD) e seguranca

```cmake
# PERIGOSO: download sem verificacao de hash
file(DOWNLOAD
    "https://example.com/tool.tar.gz"
    "${CMAKE_CURRENT_BINARY_DIR}/tool.tar.gz"
)

# SEGURO: sempre verificar hash
file(DOWNLOAD
    "https://example.com/tool.tar.gz"
    "${CMAKE_CURRENT_BINARY_DIR}/tool.tar.gz"
    EXPECTED_HASH SHA256=abc123def456...
    TLS_VERIFY ON
    STATUS download_status
)

# SEGURO: usar FetchContent ao inves de file(DOWNLOAD) quando possivel
include(FetchContent)
FetchContent_Declare(
    my_dep
    URL "https://example.com/dep-1.0.tar.gz"
    URL_HASH SHA256=abc123def456...
)
FetchContent_MakeAvailable(my_dep)
```

#### file(WRITE) e seguranca

```cmake
# PERIGOSO: escrever dados sensiveis em arquivo
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/secrets.h"
    "#define API_KEY \"$ENV{API_KEY}\""
)
# API_KEY ficara no arquivo e pode ser commitado ou logado

# SEGURO: usar configure_file() que NAO vaza dados em tempo de build
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/secrets.h.in"
               "${CMAKE_CURRENT_BINARY_DIR}/secrets.h")
# secrets.h.in deve conter @API_KEY@ que sera substituido apenas no configure
# e o valor NAO aparece no log do build

# SEGURO: nao escrever caminhos absolutos em arquivos gerados
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/paths.txt"
    "SOURCE_DIR=${CMAKE_CURRENT_SOURCE_DIR}\n"
)
# Isso pode vazar informacoes sobre a estrutura do build
# Em vez disso, usar caminhos relativos ou $<TARGET_FILE:...>
```

#### file(READ) e seguranca

```cmake
# PERIGOSO: ler arquivo sem verificar existencia
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/config.json" config)
# Se config.json nao existir, erro nao tratado

# SEGURO: verificar antes
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/config.json")
    file(READ "${CMAKE_CURRENT_SOURCE_DIR}/config.json" config)
else()
    message(FATAL_ERROR "Required config file not found: config.json")
endif()

# PERIGOSO: ler arquivo arbitrario de path de usuario
set(user_file "$ENV{USER_FILE}")
file(READ "${user_file}" content)  # Pode ler qualquer arquivo no sistema

# SEGURO: restringir a diretorio seguro
cmake_path(IS_PREFIX "${CMAKE_CURRENT_SOURCE_DIR}" "${user_file}" is_safe)
if(NOT is_safe)
    message(FATAL_ERROR "File must be within project directory")
endif()
```

---

## 11. Custom Commands: add_custom_command()

### 11.1 Sintaxe

`add_custom_command()` define comandos executados durante a build:

```cmake
# Forma 1: associado a um target
add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Build complete"
    COMMENT "Post-build step"
)

# Forma 2: gerando um arquivo
add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp"
    COMMAND ${CMAKE_COMMAND} -E echo "Generating..."
    COMMAND python3 "${CMAKE_CURRENT_SOURCE_DIR}/generate.py"
        --output "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/generate.py"
    COMMENT "Generating code from Python script"
)
```

### 11.2 POST_BUILD e PRE_BUILD

```cmake
# POST_BUILD: executar apos a build do target
add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_STRIP} $<TARGET_FILE:myapp>
    COMMENT "Stripping debug symbols"
)

# PRE_BUILD: executar antes da build (so MSVC no Windows)
add_custom_command(TARGET myapp PRE_BUILD
    COMMAND ${CMAKE_COMMAND} -E echo "Pre-build step"
)

# PRE_LINK: executar antes do link
add_custom_command(TARGET myapp PRE_LINK
    COMMAND ${CMAKE_COMMAND} -E echo "Pre-link step"
)
```

### 11.3 Geracao de codigo

```cmake
# Gerar header a partir de template
add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/version.h"
    COMMAND python3 "${CMAKE_CURRENT_SOURCE_DIR}/generate_version.py"
        --major "${PROJECT_VERSION_MAJOR}"
        --minor "${PROJECT_VERSION_MINOR}"
        --patch "${PROJECT_VERSION_PATCH}"
        --output "${CMAKE_CURRENT_BINARY_DIR}/version.h"
    DEPENDS
        "${CMAKE_CURRENT_SOURCE_DIR}/generate_version.py"
        "${CMAKE_CURRENT_SOURCE_DIR}/version_template.h"
    COMMENT "Generating version.h"
)

# Incluir o arquivo gerado no target
add_executable(myapp main.cpp "${CMAKE_CURRENT_BINARY_DIR}/version.h")
```

### 11.4 Seguranca: custom commands

Custom commands sao o vetor de ataque mais perigoso em CMake. Elas executam comandos arbitrarios durante a build:

```cmake
# PERIGOSO: executar comando de usuario
set(user_command "$ENV{BUILD_HOOK}")
add_custom_command(TARGET myapp POST_BUILD
    COMMAND sh -c "${user_command}"  # EXECUTA O QUE O USUARIO QUISER
)

# SEGURO: comandos devem ser hardcoded no CMakeLists.txt
add_custom_command(TARGET myapp POST_BUILD
    COMMAND ${CMAKE_STRIP} $<TARGET_FILE:myapp>
    COMMENT "Stripping symbols"
)

# PERIGOSO: executar script sem verificacao
add_custom_command(
    OUTPUT "generated.cpp"
    COMMAND python3 "${CMAKE_CURRENT_SOURCE_DIR}/script.py"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/script.py"
)
# Se script.py for comprometido via supply chain, executa codigo malicioso

# SEGURO: verificar hash do script
file(HASH "${CMAKE_CURRENT_SOURCE_DIR}/script.py" script_hash)
if(NOT "${script_hash}" STREQUAL "expected_hash_here")
    message(FATAL_ERROR "Script hash mismatch — possible tampering")
endif()

# SEGURO: usar generator expressions para comandos condicionais
add_custom_command(TARGET myapp POST_BUILD
    COMMAND $<$<CONFIG:Release>:${CMAKE_STRIP}>
            $<$<CONFIG:Release>:$<TARGET_FILE:myapp>>
    COMMENT $<$<CONFIG:Release>:Stripping symbols>
)
```

### 11.5 BYPRODUCTS e ORDER_DEPENDS

```cmake
# BYPRODUCTS: arquivos que o comando gera (para o gerador saber)
add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp"
    BYPRODUCTS "${CMAKE_CURRENT_BINARY_DIR}/generated.h"
    COMMAND python3 generate.py
    DEPENDS generate.py
)

# Deps entre custom commands
add_custom_command(
    OUTPUT step1.cpp
    COMMAND python3 step1.py
    DEPENDS step1.py
)

add_custom_command(
    OUTPUT step2.cpp
    COMMAND python3 step2.py
    DEPENDS step1.cpp
    # step1.cpp deve ser gerado antes de step2.cpp
)
```

### 11.6 add_custom_target()

Diferente de `add_custom_command()`, `add_custom_target()` cria um target que sempre executa:

```cmake
add_custom_target(generate_docs
    COMMAND doxygen "${CMAKE_CURRENT_SOURCE_DIR}/Doxyfile"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    COMMENT "Generating documentation"
)

# Para sempre executar (nao tem OUTPUT):
add_custom_target(always_run ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Always running"
)
```

### 11.7 Seguranca: comandos vs targets

```cmake
# add_custom_command: executado apenas quando necessario (depende de OUTPUT)
# add_custom_target: executado toda vez que o target e buildado

# PERIGOSO: custom target com comandos de usuario
add_custom_target(run_tests
    COMMAND $ENV{TEST_COMMAND}  # Usuario controla o que roda
)

# SEGURO: comandos fixos
add_custom_target(run_tests
    COMMAND ${CMAKE_CTEST_COMMAND} --test-dir ${CMAKE_BINARY_DIR}
    COMMENT "Running test suite"
)
```

---

## 12. Configure File: configure_file()

### 12.1 Sintaxe

`configure_file()` copia um arquivo substituindo variaveis CMake por seus valores:

```cmake
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/config.h"
)
```

### 12.2 Variaveis substituidas

```cmake
# config.h.in:
#define VERSION "@PROJECT_VERSION@"
#define BUILD_TYPE "@CMAKE_BUILD_TYPE@"
#define PLATFORM "@CMAKE_SYSTEM_NAME@"
#cmakedefine ENABLE_DEBUG
#cmakedefine ENABLE_HARDENING 1
```

#### @VAR@ e ${VAR}

Ambos sao substituidos:

```cmake
set(MY_VAR "hello")

# config.h.in:
#define MY_VAR "@MY_VAR@"       # Substituido por "hello"
#define MY_VAR2 "${MY_VAR}"     # Substituido por "hello"
```

#### #cmakedefine

```cmake
# Se ENABLE_DEBUG for definido como TRUE, ON, 1, etc:
#cmakedefine ENABLE_DEBUG
# Gera: #define ENABLE_DEBUG

# Se ENABLE_DEBUG for definido como FALSE, OFF, 0, ou nao definido:
# Gera: /* #undef ENABLE_DEBUG */

# cmakedefine com valor:
#cmakedefine ENABLE_DEBUG 1
# Se definido: #define ENABLE_DEBUG 1
# Se nao: /* #undef ENABLE_DEBUG 1 */
```

#### #cmakedefine01

```cmake
# Gera sempre #define, com 0 ou 1:
#cmakedefine01 ENABLE_DEBUG
# Se definido: #define ENABLE_DEBUG 1
# Se nao: #define ENABLE_DEBUG 0
```

### 12.3 Modo COPYONLY

```cmake
# Copia sem substituicao
configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/template.h"
    "${CMAKE_CURRENT_BINARY_DIR}/template.h"
    COPYONLY
)
```

### 12.4 Seguranca: configure_file()

`configure_file()` e uma ferramenta poderosa mas perigosa se usada incorretamente:

#### Vazamento de dados

```cmake
# PERIGOSO: incluir variaveis sensiveis em headers publicos
set(API_KEY "$ENV{API_KEY}")
set(SECRET_TOKEN "$ENV{SECRET_TOKEN}")

configure_file("secrets.h.in" "secrets.h")
# secrets.h.in:
# #define API_KEY "@API_KEY@"
# #define SECRET_TOKEN "@SECRET_TOKEN@"
# O resultado contera as chaves em texto plano!

# SEGURO: dados sensiveis NUNCA em headers
# Em vez disso, usar variaveis de build ou runtime configuration
configure_file("config.h.in" "config.h")
# config.h.in:
# #define API_KEY_FILE "@CMAKE_CURRENT_BINARY_DIR@/api_key.txt"
# O binario le a chave do arquivo em runtime
```

#### Caminhos absolutos

```cmake
# PERIGOSO: incluir caminhos absolutos em headers
configure_file("paths.h.in" "paths.h")
# paths.h.in:
# #define SOURCE_DIR "@CMAKE_CURRENT_SOURCE_DIR@"
# #define BUILD_DIR "@CMAKE_CURRENT_BINARY_DIR@"
# Isso vaza a estrutura do filesystem do build

# SEGURO: usar caminhos relativos ou targets
configure_file("paths.h.in" "paths.h")
# paths.h.in:
# #define RESOURCE_DIR "resources"
```

#### Variaveis de ambiente

```cmake
# PERIGOSO: vazar variaveis de ambiente
set(HOME_DIR "$ENV{HOME}")
set(USER_NAME "$ENV{USER}")
configure_file("env.h.in" "env.h")

# SEGURO: so incluir variaveis de build
configure_file("config.h.in" "config.h")
# config.h.in deve conter apenas:
# #define VERSION "@PROJECT_VERSION@"
# #define BUILD_TYPE "@CMAKE_BUILD_TYPE@"
```

### 12.5 Padrao seguro de configure_file()

```cmake
# Arquivo de configuracao seguro
# config.h.in:
# #pragma once
# #define APP_VERSION "@PROJECT_VERSION@"
# #define APP_VERSION_MAJOR @PROJECT_VERSION_MAJOR@
# #define APP_VERSION_MINOR @PROJECT_VERSION_MINOR@
# #define APP_VERSION_PATCH @PROJECT_VERSION_PATCH@
# #cmakedefine ENABLE_HARDENING
# #cmakedefine ENABLE_SANITIZERS
# #cmakedefine01 BUILD_IS_RELEASE
# /* Do NOT put secrets or absolute paths in this file */

# CMakeLists.txt:
set(BUILD_IS_RELEASE FALSE)
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(BUILD_IS_RELEASE TRUE)
endif()

configure_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/config.h.in"
    "${CMAKE_CURRENT_BINARY_DIR}/config.h"
)
```

---

## 13. Exemplo: Funcao Reutilizavel para Hardening

Este e o exemplo integrador do capitulo. Vamos construir uma funcao CMake completa que aplica hardening de seguranca a qualquer target, usando todos os conceitos aprendidos.

### 13.1 Especificacao

A funcao `secure_target_hardening()` deve:

1. Aceitar um nome de target como argumento obrigatorio
2. Aceitar opcoes para habilitar/desabilitar features de hardening
3. Funcionar com GCC, Clang e MSVC
4. Funcionar em Linux, macOS e Windows
5. Validar todos os argumentos
6. Reportar o que foi aplicado

### 13.2 Implementacao completa

```cmake
# secure_hardening.cmake — Include este arquivo no seu CMakeLists.txt

#[=======================================================================[.rst:
secure_target_hardening
-----------------------

Applies compiler and linker hardening options to a target.

Usage::

  secure_target_hardening(
    my_target
    [STACK_PROTECTION ON|OFF]
    [FORTIFY_SOURCE ON|OFF]
    [FORMAT_SECURITY ON|OFF]
    [RELRO ON|OFF]
    [NOW ON|OFF]
    [ASLR ON|OFF]
    [STRIP ON|OFF]
    [FORTIFY_SOURCE_LEVEL 1|2]
  )

Example::

  secure_target_hardening(myapp
    STACK_PROTECTION ON
    FORTIFY_SOURCE ON
    FORTIFY_SOURCE_LEVEL 2
    RELRO ON
    NOW ON
  )

#]=======================================================================]

function(secure_target_hardening target_name)
    cmake_parse_arguments(
        PARSE_ARGV 1
        PARSED
        "STACK_PROTECTION;FORTIFY_SOURCE;FORMAT_SECURITY;RELRO;NOW;ASLR;STRIP"
        "FORTIFY_SOURCE_LEVEL"
    )

    # Validacao obrigatoria
    if("${target_name}" STREQUAL "")
        message(FATAL_ERROR "secure_target_hardening: target name is required")
    endif()

    if(NOT TARGET "${target_name}")
        message(FATAL_ERROR "secure_target_hardening: target '${target_name}' does not exist")
    endif()

    # Validar nome do target
    if("${target_name}" MATCHES "[;&|`$\\\"]")
        message(FATAL_ERROR "secure_target_hardening: invalid target name")
    endif()

    # Defaults
    if(NOT DEFINED PARSED_STACK_PROTECTION)
        set(PARSED_STACK_PROTECTION ON)
    endif()
    if(NOT DEFINED PARSED_FORTIFY_SOURCE)
        set(PARSED_FORTIFY_SOURCE ON)
    endif()
    if(NOT DEFINED PARSED_FORMAT_SECURITY)
        set(PARSED_FORMAT_SECURITY ON)
    endif()
    if(NOT DEFINED PARSED_RELRO)
        set(PARSED_RELRO ON)
    endif()
    if(NOT DEFINED PARSED_NOW)
        set(PARSED_NOW ON)
    endif()
    if(NOT DEFINED PARSED_FORTIFY_SOURCE_LEVEL)
        set(PARSED_FORTIFY_SOURCE_LEVEL 2)
    endif()

    # Validar FORTIFY_SOURCE_LEVEL
    if(NOT PARSED_FORTIFY_SOURCE_LEVEL MATCHES "^[12]$")
        message(FATAL_ERROR
            "secure_target_hardening: FORTIFY_SOURCE_LEVEL must be 1 or 2"
        )
    endif()

    set(_hardening_flags "")
    set(_hardening_definitions "")
    set(_link_options "")

    # --- GCC ---
    if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
        # Stack protection
        if(PARSED_STACK_PROTECTION)
            list(APPEND _hardening_flags -fstack-protector-strong)
        endif()

        # FORTIFY_SOURCE
        if(PARSED_FORTIFY_SOURCE)
            list(APPEND _hardening_definitions
                _FORTIFY_SOURCE=${PARSED_FORTIFY_SOURCE_LEVEL}
            )
        endif()

        # Format security
        if(PARSED_FORMAT_SECURITY)
            list(APPEND _hardening_flags -Wformat -Wformat-security)
            list(APPEND _hardening_definitions
                -Werror=format-security
            )
        endif()

        # ASLR (PIE)
        if(PARSED_ASLR)
            list(APPEND _hardening_flags -fPIE)
            list(APPEND _link_options -pie)
        endif()

        # RELRO
        if(PARSED_RELRO)
            if(PARSED_NOW)
                list(APPEND _link_options -Wl,-z,relro,-z,now)
            else()
                list(APPEND _link_options -Wl,-z,relro)
            endif()
        endif()

        # Strip
        if(PARSED_STRIP)
            list(APPEND _link_options -s)
        endif()

    # --- Clang ---
    elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        # Stack protection
        if(PARSED_STACK_PROTECTION)
            list(APPEND _hardening_flags -fstack-protector-strong)
        endif()

        # FORTIFY_SOURCE
        if(PARSED_FORTIFY_SOURCE)
            list(APPEND _hardening_definitions
                _FORTIFY_SOURCE=${PARSED_FORTIFY_SOURCE_LEVEL}
            )
        endif()

        # Format security
        if(PARSED_FORMAT_SECURITY)
            list(APPEND _hardening_flags -Wformat -Wformat-security)
            list(APPEND _hardening_definitions
                -Werror=format-security
            )
        endif()

        # ASLR
        if(PARSED_ASLR)
            list(APPEND _hardening_flags -fPIE)
            list(APPEND _link_options -pie)
        endif()

        # RELRO
        if(PARSED_RELRO)
            if(PARSED_NOW)
                list(APPEND _link_options -Wl,-z,relro,-z,now)
            else()
                list(APPEND _link_options -Wl,-z,relro)
            endif()
        endif()

        # Strip
        if(PARSED_STRIP)
            list(APPEND _link_options -s)
        endif()

    # --- MSVC ---
    elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
        # Stack protection (GS e default no MSVC, mas podemos forcar)
        if(PARSED_STACK_PROTECTION)
            list(APPEND _hardening_flags /GS)
        endif()

        # FORTIFY_SOURCE (SDS no MSVC)
        if(PARSED_FORTIFY_SOURCE)
            list(APPEND _hardening_flags /sdl)
        endif()

        # Format security
        if(PARSED_FORMAT_SECURITY)
            list(APPEND _hardening_flags /W4 /WX)
        endif()

        # ASLR (DYNAMICBASE e default no MSVC, mas podemos forcar)
        if(PARSED_ASLR)
            list(APPEND _link_options /DYNAMICBASE)
        endif()

        # NX (DEP)
        list(APPEND _link_options /NXCOMPAT)

        # Strip (DEBUG info removida em Release)
        if(PARSED_STRIP)
            list(APPEND _link_options /DEBUG:NONE)
        endif()

    else()
        message(WARNING
            "secure_target_hardening: unknown compiler '${CMAKE_CXX_COMPILER_ID}'"
        )
    endif()

    # Aplicar flags ao target
    if(NOT "${_hardening_flags}" STREQUAL "")
        target_compile_options("${target_name}" PRIVATE ${_hardening_flags})
    endif()

    if(NOT "${_hardening_definitions}" STREQUAL "")
        target_compile_definitions("${target_name}" PRIVATE ${_hardening_definitions})
    endif()

    if(NOT "${_link_options}" STREQUAL "")
        target_link_options("${target_name}" PRIVATE ${_link_options})
    endif()

    # Log do que foi aplicado
    message(STATUS "Hardening applied to '${target_name}':")
    if(PARSED_STACK_PROTECTION)
        message(STATUS "  - Stack protection: ON")
    endif()
    if(PARSED_FORTIFY_SOURCE)
        message(STATUS "  - FORTIFY_SOURCE level ${PARSED_FORTIFY_SOURCE_LEVEL}")
    endif()
    if(PARSED_FORMAT_SECURITY)
        message(STATUS "  - Format security: ON")
    endif()
    if(PARSED_RELRO)
        message(STATUS "  - RELRO: ON (NOW=${PARSED_NOW})")
    endif()
    if(PARSED_ASLR)
        message(STATUS "  - ASLR/PIE: ON")
    endif()
    if(PARSED_STRIP)
        message(STATUS "  - Strip: ON")
    endif()
endfunction()
```

### 13.3 Uso

```cmake
# CMakeLists.txt principal
cmake_minimum_required(VERSION 3.20)
project(MySecureApp VERSION 1.0.0 LANGUAGES CXX)

# Incluir o modulo de hardening
include(cmake/secure_hardening.cmake)

# Criar o executavel
add_executable(myapp
    src/main.cpp
    src/utils.cpp
)

# Aplicar hardening
secure_target_hardening(myapp
    STACK_PROTECTION ON
    FORTIFY_SOURCE ON
    FORTIFY_SOURCE_LEVEL 2
    FORMAT_SECURITY ON
    RELRO ON
    NOW ON
    ASLR ON
    STRIP $<$<CONFIG:Release>:ON>
)
```

### 13.4 Analise da funcao

Esta funcao demonstra todos os conceitos do capitulo:

- **cmake_parse_arguments()**: para parsear argumentos nomeados
- **function()**: para criar escopo isolado
- **if() / elseif()**: para deteccao de compilador e plataforma
- **Validacao**: todas as entradas sao verificadas antes de usar
- **Generator expressions**: para flags condicionais por configuracao
- **Loop com foreach()**: embora nao usado explicitamente aqui, poderia ser usado para iterar sobre listas de flags
- **Seguranca**: validacao de nomes, whitelisting de valores, sem inputs de usuario

---

## 14. Exercicios

### Exercicio 1: Generator Expressions

Crie uma `target_compile_options()` que:

- Em Debug: adicione `-O0 -g3`
- Em Release: adicione `-O2 -DNDEBUG`
- Apenas em Linux: adicione `-fPIC`
- Apenas com GCC: adicione `-Wall -Wextra`

**Dica**: Use genexps encadeados com `$<AND:...>` e `$<OR:...>`.

<details>
<summary>Solucao</summary>

```cmake
target_compile_options(mylib PRIVATE
    $<$<CONFIG:Debug>:-O0 -g3>
    $<$<CONFIG:Release>:-O2 -DNDEBUG>
    $<$<PLATFORM_ID:Linux>:-fPIC>
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra>
)
```

</details>

### Exercicio 2: Funcao de Validacao

Crie uma funcao `validate_cmake_options()` que:

- Aceite um prefixo e uma lista de opcoes obrigatorias
- Verifique se cada opcao esta definida e nao e vazia
- Emita `FATAL_ERROR` se alguma opcao estiver faltando

**Dica**: Use `cmake_parse_arguments()` e loop com `foreach()`.

<details>
<summary>Solucao</summary>

```cmake
function(validate_cmake_options prefix)
    set(required_options ${ARGN})
    foreach(opt IN LISTS required_options)
        set(full_name "${prefix}_${opt}")
        if(NOT DEFINED ${full_name})
            message(FATAL_ERROR "Required option ${full_name} is not defined")
        endif()
        if("${${full_name}}" STREQUAL "")
            message(FATAL_ERROR "Required option ${full_name} is empty")
        endif()
    endforeach()
endfunction()

# Uso:
set(MYAPP_NAME "MyApp")
set(MYAPP_VERSION "1.0")
validate_cmake_options(MYAPP NAME VERSION)
```

</details>

### Exercicio 3: File Operations

Crie um script CMake que:

- Leia um arquivo `versions.txt` contendo versoes (uma por linha)
- Para cada versao, gere um arquivo `version_<N>.h` com `#define VERSION "<version>"`
- Valide que cada linha nao contem caracteres perigosos

**Dica**: Use `file(READ)`, `string(REPLACE)`, `foreach()`, e `file(WRITE)`.

<details>
<summary>Solucao</summary>

```cmake
file(READ "${CMAKE_CURRENT_SOURCE_DIR}/versions.txt" versions_content)
string(REPLACE "\n" ";" versions_list "${versions_content}")

set(index 0)
foreach(version IN LISTS versions_list)
    # Validar
    if(version MATCHES "[;&|`\$\"]")
        message(FATAL_ERROR "Invalid characters in version: ${version}")
    endif()

    # Gerar header
    math(EXPR index "${index} + 1")
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/version_${index}.h"
"#pragma once
#define VERSION \"${version}\"
#define VERSION_MAJOR ${version}
"
    )
endforeach()
```

</details>

### Exercicio 4: PARENT_SCOPE

Crie uma funcao `detect_secure_compiler()` que:

- Detecte se o compilador suporta `-fstack-protector-strong`
- Retorne o resultado via `PARENT_SCOPE`
- Nao modifique nenhuma variavel no escopo local

**Dica**: Use `check_cxx_compiler_flag()` ou `try_compile()`.

<details>
<summary>Solucao</summary>

```cmake
include(CheckCXXCompilerFlag)

function(detect_secure_compiler output_var)
    check_cxx_compiler_flag("-fstack-protector-strong" HAS_STACK_PROTECTOR)
    set(${output_var} ${HAS_STACK_PROTECTOR} PARENT_SCOPE)
endfunction()

detect_secure_compiler(HAS_STACK_PROTECTOR)
if(HAS_STACK_PROTECTOR)
    message(STATUS "Stack protector supported")
endif()
```

</details>

### Exercicio 5: Custom Commands com Seguranca

Crie um `add_custom_command()` que:

- Execute um script Python para gerar codigo
- Verifique o hash do script antes de executar
- Valide que o output existe apos a execucao
- Use `DEPENDS` para rastreabilidade

**Dica**: Use `file(HASH)`, `add_custom_command(OUTPUT ...)`, e `add_custom_command(COMMAND ...)`.

<details>
<summary>Solucao</summary>

```cmake
# Verificar hash do script
set(SCRIPT_PATH "${CMAKE_CURRENT_SOURCE_DIR}/generate.py")
set(EXPECTED_HASH "abc123def456...")

file(HASH "${SCRIPT_PATH}" ACTUAL_HASH)
if(NOT "${ACTUAL_HASH}" STREQUAL "${EXPECTED_HASH}")
    message(FATAL_ERROR "Script hash mismatch: expected ${EXPECTED_HASH}, got ${ACTUAL_HASH}")
endif()

# Custom command
set(GENERATED_FILE "${CMAKE_CURRENT_BINARY_DIR}/generated.cpp")

add_custom_command(
    OUTPUT "${GENERATED_FILE}"
    COMMAND python3 "${SCRIPT_PATH}"
        --output "${GENERATED_FILE}"
    DEPENDS "${SCRIPT_PATH}"
    COMMAND ${CMAKE_COMMAND} -E echo "Verifying output..."
    COMMAND ${CMAKE_COMMAND} -E test -f "${GENERATED_FILE}"
    COMMENT "Generating code from verified script"
)

# Adicionar ao target
add_executable(myapp main.cpp "${GENERATED_FILE}")
```

</details>

### Exercicio 6: while() e math()

Crie um script CMake que:

- Gere uma tabela de multiplicacao de 1 a 10
- Salve o resultado em `multiplication_table.txt`
- Use `while()` e `math(EXPR)`

**Dica**: Aninhamento de loops com `while()`.

<details>
<summary>Solucao</summary>

```cmake
set(output "")
set(i 1)
while(i LESS_EQUAL 10)
    set(j 1)
    while(j LESS_EQUAL 10)
        math(EXPR result "${i} * ${j}")
        string(APPEND output "${i} x ${j} = ${result}\t")
        math(EXPR j "${j} + 1")
    endwhile()
    string(APPEND output "\n")
    math(EXPR i "${i} + 1")
endwhile()

file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/multiplication_table.txt" "${output}")
```

</details>

### Exercicio 7: configure_file() Seguro

Crie um sistema de configuracao que:

- Gere `config.h` a partir de `config.h.in`
- Nao inclua dados sensiveis ou caminhos absolutos
- Use `#cmakedefine` para features habilitadas
- Valide que `config.h.in` existe antes de chamar `configure_file()`

**Dica**: Use `if(EXISTS ...)` e `configure_file()`.

<details>
<summary>Solucao</summary>

```cmake
# config.h.in:
# #pragma once
# #define APP_VERSION "@PROJECT_VERSION@"
# #cmakedefine ENABLE_HARDENING
# #cmakedefine ENABLE_SANITIZERS
# #cmakedefine01 BUILD_IS_RELEASE

# CMakeLists.txt:
set(BUILD_IS_RELEASE FALSE)
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    set(BUILD_IS_RELEASE TRUE)
endif()

set(CONFIG_TEMPLATE "${CMAKE_CURRENT_SOURCE_DIR}/config.h.in")
if(NOT EXISTS "${CONFIG_TEMPLATE}")
    message(FATAL_ERROR "Config template not found: ${CONFIG_TEMPLATE}")
endif()

configure_file("${CONFIG_TEMPLATE}" "${CMAKE_CURRENT_BINARY_DIR}/config.h")
```

</details>

---

## 15. Anti-Padroes e Cuidados Comuns

### 15.1 Anti-padroes de genexps

```cmake
# ANTI-PADRAO: genexp em contexts que nao aceitam
# Nao funciona — message() nao avalia genexps
message($<$<CONFIG:Debug>:Debug mode>)

# ANTI-PADRAO: genexp em variavel
set(my_flag $<$<CONFIG:Debug>:-g>)
# my_flag armazena a string literal "$<CONFIG:Debug>:-g", nao o resultado

# ANTI-PADRAO: genexp complexo demais
target_compile_options(mylib PRIVATE
    $<$<AND:$<BOOL:${A}>,$<OR:$<BOOL:${B}>,$<BOOL:${C}>},
        $<NOT:$<PLATFORM_ID:Windows>>>:-Werror>
)
# Torna o CMakeLists.txt ilegivel — prefira if() para logica complexa

# CORRETO: usar if() para logica complexa, genexp para flags simples
if(A AND (B OR C) AND NOT CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_compile_options(mylib PRIVATE -Werror)
endif()
```

### 15.2 Anti-padroes de function/macro

```cmake
# ANTI-PADRAO: macro que modifica escopo do chamador sem intencao
macro(add_flag flag)
    set(current_flags "${current_flags} ${flag}")
endmacro()

# O chamador nao espera que current_flags seja modificada
# Isso causa efeitos colaterais dificeis de debugar

# CORRETO: usar function() com return via PARENT_SCOPE
function(add_flag target flag)
    target_compile_options("${target}" PRIVATE "${flag}")
endfunction()

# ANTI-PADRAO: function() sem validacao de argumentos
function(dangerous_function)
    # Assume que o primeiro argumento e um target
    # Se nao for, comportamento indefinido
    target_compile_options(${ARGV0} PRIVATE -Wall)
endfunction()

# CORRETO: sempre validar
function(safe_function target)
    if(NOT TARGET "${target}")
        message(FATAL_ERROR "Not a valid target: ${target}")
    endif()
    target_compile_options("${target}" PRIVATE -Wall)
endfunction()
```

### 15.3 Anti-padroes de file(GLOB)

```cmake
# ANTI-PADRAO: GLOB seguido de commit
file(GLOB sources "*.cpp")
# Se voce fizer git add e commit, o CMake NAO atualiza a lista
# quando novos arquivos sao adicionados

# CORRETO: usar CONFIGURE_DEPENDS (CMake 3.12+)
file(GLOB sources CONFIGURE_DEPENDS "*.cpp")

# OU melhor: listar arquivos explicitamente
add_library(mylib
    src/main.cpp
    src/utils.cpp
    src/parser.cpp
)
# Isso e explicito, previsivel, e funciona sempre

# ANTI-PADRAO: GLOB sem filtro de diretorio
file(GLOB_RECURSE all_files "*")
# Inclui TUDO — .git, build/, .env, secrets/, etc.

# CORRETO: filtro especifico
file(GLOB_RECURSE sources CONFIGURE_DEPENDS
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp"
    "${CMAKE_CURRENT_SOURCE_DIR}/src/*.c"
)
```

### 15.4 Anti-padroes de if()

```cmake
# ANTI-PADRAO: variavel nao-quotada em if()
set(myvar "some value with spaces")
if(${myvar} STREQUAL "target")
# Quebra se myvar contiver espacos

# CORRETO: sempre quotar
if("${myvar}" STREQUAL "target")

# ANTI-PADRAO: testar variavel com if() sem DEFINED
if(${MY_OPTION})
# Se MY_OPTION nao existe, comportamento indefinido

# CORRETO: testar existencia primeiro
if(DEFINED MY_OPTION AND NOT "${MY_OPTION}" STREQUAL "")

# ANTI-PADRAO: confundir string com bool
set(mystring "NOTFOUND")
if(${mystring})
# "NOTFOUND" e falsa no CMake — mas o usuario nao espera isso

# CORRETO: ser explicito
if("${mystring}" STREQUAL "NOTFOUND")
    message("String is NOTFOUND")
endif()
```

### 15.5 Anti-padroes de configure_file()

```cmake
# ANTI-PADRAO: usar configure_file() como copia
configure_file(src.cpp.in dest.cpp)
# Se src.cpp.in nao tiver variaveis, use file(COPY ...) instead

# ANTI-PADRAO: esquecer que configure_file() NAO valida variaveis
set(UNDEFINED_VAR "")  # Nao definido!
configure_file(config.h.in config.h)
# config.h.in com @UNDEFINED_VAR@ sera substituido por string vazia

# CORRETO: sempre definir variaveis antes de configure_file()
if(NOT DEFINED UNDEFINED_VAR)
    set(UNDEFINED_VAR "default_value")
endif()
configure_file(config.h.in config.h)

# ANTI-PADRAO: incluir dados sensiveis
set(API_KEY "$ENV{API_KEY}")
configure_file("secret.h.in" "secret.h")
# API_KEY ficara em texto plano no header

# CORRETO: nunca incluir segredos em headers
# Ler de arquivo ou variavel de ambiente em runtime
```

### 15.6 Anti-padroes de loop

```cmake
# ANTI-PADRAO: foreach sem verificacao de existencia
file(GLOB sources "*.cpp")
# sources pode estar vazio se nao houver .cpp
foreach(src IN LISTS sources)
    # Se sources estiver vazio, o loop nao executa — mas o CMake
    # pode nao avisar, e o build falha misteriosamente depois
endforeach()

# CORRETO: verificar antes
if(sources)
    foreach(src IN LISTS sources)
        # Processar
    endforeach()
else()
    message(FATAL_ERROR "No source files found")
endif()

# ANTI-PADRAO: while sem limite
set(i 0)
while(i LESS 100)
    # Se i nunca aumentar, loop infinito
endforeach()

# CORRETO: sempre ter um limite de seguranca
set(max_iterations 1000)
set(i 0)
while(i LESS 100 AND i LESS max_iterations)
    math(EXPR i "${i} + 1")
endforeach()
if(i GREATER_EQUAL max_iterations)
    message(FATAL_ERROR "Loop exceeded safety limit")
endif()
```

---

## 16. Referencias

### Documentacao Oficial

- [CMake Language Reference](https://cmake.org/cmake/help/latest/manual/cmake-language.7.html)
- [Generator Expressions](https://cmake.org/cmake/help/latest/manual/cmake-generator-expressions.7.html)
- [if() Command](https://cmake.org/cmake/help/latest/command/if.html)
- [foreach() Command](https://cmake.org/cmake/help/latest/command/foreach.html)
- [function() Command](https://cmake.org/cmake/help/latest/command/function.html)
- [macro() Command](https://cmake.org/cmake/help/latest/command/macro.html)
- [cmake_parse_arguments()](https://cmake.org/cmake/help/latest/command/cmake_parse_arguments.html)
- [file() Command](https://cmake.org/cmake/help/latest/command/file.html)
- [configure_file()](https://cmake.org/cmake/help/latest/command/configure_file.html)
- [add_custom_command()](https://cmake.org/cmake/help/latest/command/add_custom_command.html)

### Livros e Artigos

- "Mastering CMake" — Kitware (autor oficial do CMake)
- "Professional CMake: A Practical Guide" — Craig Scott
- "Modern CMake" — Jason Turner
- "CMake Best Practices" — Dominik Berner, Betty Kitchen

### CVEs Relacionados

| CVE | Relevancia |
|-----|-----------|
| CVE-2024-3094 | XZ Utils backdoor — supply chain via build system |
| CVE-2023-44487 | HTTP/2 Rapid Reset — builds com dependencias de rede |
| CVE-2021-44228 | Log4Shell — dependencias em build systems |

### Ferramentas

| Ferramenta | Uso |
|-----------|-----|
| CMake 3.20+ | Build system |
| Ninja | Gerador de build rapido |
| clang-tidy | Analise estatica |
| cppcheck | Analise estatica |
| CMake Utils | Modulos utilitarios |

---

*[Capitulo anterior: 02 — Target Model e Properties](02-target-model-properties.md) | [Capítulo 4 — Flags de Segurança do Compilador](04-flags-seguranca-compilador.md)*
