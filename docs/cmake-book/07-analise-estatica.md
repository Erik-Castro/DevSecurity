---
layout: default
title: "Analise Estatica com CMake"
---

# Capítulo 07 — Analise Estatica com CMake

> *"Previna bugs antes que eles cheguem ao runtime. Analise estatica e o radar do seu build system."*

---

## 7.1 Objetivos de Aprendizado

Apos completar este capitulo, voce sera capaz de:

- Configurar e integrar clang-tidy em projetos CMake
- Usar cppcheck como ferramenta complementar de analise
- Integrar Facebook Infer para analise profunda de ponteiros e recursos
- Criar targets customizados para executar analises estaticas
- Gerar saidas SARIF para integracao com GitHub Code Scanning
- Configurar warnings como erros para catches precoces
- Entender compliance MISRA C/C++ e como verificar com ferramentas open-source
- Aplicar regras CERT C/C++ e mapear findings para CWE
- Construir pipelines completas de analise estatica

### Por Que Analise Estatica Importa

Analise estatica examina o codigo sem executa-lo. Enquanto testes unitarios e sanitizers capturam bugs em runtime, analise estatica encontra:

- **Vulnerabilidades de seguranca**: buffer overflows, use-after-free, SQL injection
- **Bugs logicos**: dead code, uninitialize variables, null pointer dereferences
- **Code smells**: complexidade ciclomatica, duplicacao, violacoes de padrao
- **Violacoes de padrao**: naming conventions, formatting, architecture rules

Para projetos de seguranca, analise estatica e **obrigatoria**, nao opcional. OWASP, CERT, e MISRA todos exigem ou recomendam fortemente ferramentas de analise estatica como parte do ciclo de vida de desenvolvimento seguro.

### Ferramentas Discutidas

| Ferramenta | Tipo | Linguagens | Custo |
|------------|------|------------|-------|
| clang-tidy | Analise + fixes automaticos | C/C++ | Gratuito (LLVM) |
| cppcheck | Analise estatica | C/C++ | Gratuito (open-source) |
| Facebook Infer | Analise profunda | C/C++/Java/OCaml | Gratuito (open-source) |
| clang-tidy com checks MISRA | Compliance | C/C++ | Gratuito (via plugins) |
| clang-tidy com checks CERT | Compliance | C/C++ | Gratuito (built-in) |

---

## 7.2 clang-tidy: Configuracao, Checks e Fixes

clang-tidy e a ferramenta de analise estatica mais popular no ecossistema C/C++. Faz parte do projeto LLVM e oferece centenas de checks organizados em modulos.

### 7.2.1 Instalacao

```bash
# Ubuntu/Debian
sudo apt-get install clang-tidy

# macOS com Homebrew
brew install llvm

# Verificar versao
clang-tidy --version
```

### 7.2.2 Configuracao Basica

clang-tidy usa um arquivo `.clang-tidy` na raiz do projeto:

```yaml
---
Checks: >
  -*,
  bugprone-*,
  cert-*,
  clang-analyzer-*,
  concurrency-*,
  cppcoreguidelines-*,
  misc-*,
  modernize-*,
  performance-*,
  portability-*,
  readability-*,
  -bugprone-easily-swappable-parameters,
  -readability-magic-numbers

WarningsAsErrors: >
  bugprone-dangling-handle,
  bugprone-use-after-move,
  cert-err33-c,
  cppcoreguidelines-init-variables,
  cppcoreguidelines-pro-type-member-init

HeaderFilterRegex: 'src/.*'

FormatStyle: none
```

### 7.2.3 Categorias de Checks

#### Bugprone Checks

Estes checks detectam bugs comuns que frequentemente levam a comportamento indefinido:

```yaml
# Checks criticos para seguranca
bugprone-dangling-handle
bugprone-implicit-widening-of-multiplication-result
bugprone-infinite-loop
bugprone-narrowing-conversions
bugprone-not-null-terminated-result
bugprone-sizeof-expression
bugprone-suspicious-string-compare
bugprone-uninitialized-foreground
bugprone-use-after-move
```

Exemplo de bug detectado por `bugprone-use-after-move`:

```cpp
#include <string>
#include <vector>
#include <utility>

void process_data(std::vector<std::string>& items) {
    std::string temp = std::move(items[0]);
    
    // BUG: usando items[0] apos move
    if (items[0] == "special") {
        do_something(temp);
    }
    
    // clang-tidy detecta: use after move of 'items[0]'
}
```

#### CERT C/C++ Checks

Checks que implementam regras do CERT C Coding Standard:

```yaml
cert-dcl50-cpp    # variadic function declarations
cert-err33-c      # check return value
cert-err34-c      # check return value of strtol
cert-err58-cpp    # static storage duration initialization
cert-err59-cpp    # avoid exceptions with noexcept
cert-flp30-c      # floating point conversion
cert-msc24-c      # do not use deprecated functions
cert-msc30-c      # do not use rand()
```

#### CppCoreGuidelines

Implementacao do C++ Core Guidelines:

```yaml
cppcoreguidelines-init-variables          # inicilizar variaveis
cppcoreguidelines-interfaces-global-init  # init de interfaces
cppcoreguidelines-narrowing-conversions   # narrowing
cppcoreguidelines-no-malloc              # malloc em C++
cppcoreguidelines-pro-bounds-array-to-pointer-decay  # decay
cppcoreguidelines-pro-type-member-init   # membros nao-init
cppcoreguidelines-pro-type-reinterpret-cast  # reinterpret_cast
cppcoreguidelines-slicing                 # object slicing
```

#### Modernize Checks

Checks que sugerem atualizacoes para padroes modernos de C++:

```yaml
modernize-avoid-bind          # usar lambda em vez de bind
modernize-concat-nested-namespaces  # C++17 namespaces
modernize-make-unique         # make_unique em vez de new
modernize-use-auto            # usar auto
modernize-use-emplace         # emplace em vez de push_back
modernize-use-nullptr         # nullptr em vez de NULL
modernize-use-override        # override em metodos virtuais
```

### 7.2.4 Execucao Manual

```bash
# Analise basica
clang-tidy src/*.cpp -- -std=c++17 -Iinclude

# Com export de saida
clang-tidy src/*.cpp --export-fixes=fixes.yaml -- -std=c++17 -Iinclude

# Apenas checks especificos
clang-tidy src/main.cpp --checks='bugprone-*,cert-*' -- -std=c++17

# Executar fixes automaticos
clang-tidy src/*.cpp --fix -- -std=c++17 -Iinclude

# Verificar apenas header files
clang-tidy src/*.cpp --header-filter='include/.*' -- -std=c++17 -Iinclude
```

### 7.2.5 Fixes Automaticos

clang-tidy pode corrigir automaticamente muitos problemas:

```bash
# Corrigir e salvar
clang-tidy src/*.cpp --fix --fix-errors -- -std=c++17 -Iinclude

# Corrigir apenas checks especificos
clang-tidy src/*.cpp --fix --checks='modernize-use-nullptr' -- -std=c++17

# Exportar fixes para revisao
clang-tidy src/*.cpp --export-fixes=fixes.yaml --fix -- -std=c++17
```

### 7.2.6 Configuracao por Diretorio

clang-tidy pode ter configuracoes diferentes por diretorio:

```
project/
├── .clang-tidy                    # Configuracao global
├── src/
│   ├── .clang-tidy               # Configuracao para src/
│   └── security/
│       └── .clang-tidy           # Checks mais rigorosos
├── tests/
│   └── .clang-tidy               # Checks menos restritivos
└── vendor/
    └── .clang-tidy               # Desabilitar checks
```

Exemplo de `.clang-tidy` para diretorio de seguranca:

```yaml
---
Checks: >
  -*,
  bugprone-*,
  cert-*,
  clang-analyzer-*,
  cppcoreguidelines-*,
  security-*

WarningsAsErrors: '*'

HeaderFilterRegex: 'src/security/.*'
```

---

## 7.3 cppcheck: Uso e Integracao

cppcheck e uma ferramenta de analise estatica open-source focada em detectar bugs que outros compiladores nao detectam. Diferente do clang-tidy, cppcheck faz analise mais profunda sem necessidade de compilar o codigo.

### 7.3.1 Instalacao

```bash
# Ubuntu/Debian
sudo apt-get install cppcheck

# macOS
brew install cppcheck

# Verificar versao
cppcheck --version
```

### 7.3.2 Uso Basico

```bash
# Analise basica
cppcheck src/

# Analise detalhada (mais lenta, mais profunda)
cppcheck --enable=all --std=c++17 src/

# Verificar apenas arquivos especificos
cppcheck src/main.cpp src/parser.cpp

# Analise com informacao de incluso
cppcheck -I include/ src/

# Saida em formato XML
cppcheck --xml --xml-version=2 src/ 2> results.xml
```

### 7.3.3 Configuracao Avancada

#### Suppressao de Warnings

```cpp
// Suprimir warning em uma linha especifica
int* p = nullptr;
// cppcheck-suppress nullPointer
*p = 5;

// Suprimir por categoria
// cppcheck-suppress memleak
void leaked_memory() {
    int* arr = new int[100];
    // funcao que "usa" arr de forma que cppcheck nao entende
}

// Suprimir por id
// cppcheck-suppress [uninitvar,uninitMemberVar]
class MyClass {
    int member;
public:
    MyClass() {} // nao inicia member
};
```

#### Supressao por Arquivo

```xml
<?xml version="1.0" encoding="UTF-8"?>
<suppressions>
  <!-- Suprimir todos os warnings em vendor/ -->
  <suppress>
    <fileName>vendor/*</fileName>
  </suppress>
  
  <!-- Suprimir warning especifico em arquivo -->
  <suppress>
    <fileName>src/parser.cpp</fileName>
    <id>uninitvar</id>
  </suppress>
  
  <!-- Suprimir por funcao -->
  <suppress>
    <functionName>legacy_function</functionName>
    <id>unusedFunction</id>
  </suppress>
</suppressions>
```

#### Supressao por Projeto

Criar arquivo `cppcheck-suppressions.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<suppressions>
  <suppress>
    <fileName>src/legacy/*</fileName>
    <id>uninitvar</id>
  </suppress>
  <suppress>
    <fileName>tests/*</fileName>
    <id>unusedFunction</id>
  </suppress>
</suppressions>
```

Uso:

```bash
cppcheck --suppressions-list=cppcheck-suppressions.xml --enable=all src/
```

### 7.3.4 Integracao com Build System

#### Usando compile_commands.json

```bash
# Gerar compile_commands.json com CMake
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Usar com cppcheck
cppcheck --project=build/compile_commands.json --enable=all
```

#### Verificacao Contra Definicoes

```bash
# Definicoes de ambiente
cppcheck -D__linux__ -D__x86_64__ -DCMAKE_SYSTEM_NAME=Linux src/

# Definicoes via arquivo
cppcheck --project=build/compile_commands.json \
         --enable=all \
         --suppress=missingIncludeSystem
```

### 7.3.5 Saida e Relatorios

#### Saida XML

```bash
cppcheck --xml --xml-version=2 --enable=all src/ 2> report.xml
```

Formato do XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<results>
  <cppcheck version="2.13"/>
  <errors>
    <error id="uninitvar" severity="error" msg="Uninitialized variable" 
           verbose="Uninitialized variable: p" cwe="457">
      <location file="src/main.cpp" line="42" info="Expression: p"/>
    </error>
  </errors>
</results>
```

#### Saida JSON

```bash
cppcheck --json --enable=all src/ 2> report.json
```

#### Saida CSV

```bash
cppcheck --template='{file},{line},{column},{severity},{id},{message}' \
         --enable=all src/ 2> report.csv
```

### 7.3.6 Diferenças entre cppcheck e clang-tidy

| Aspecto | cppcheck | clang-tidy |
|---------|----------|------------|
| Analise | Sem compilar (parsing proprio) | Usa AST do Clang |
| Velocidade | Mais rapido | Mais lento |
| Precisao | Mais false positives | Mais preciso |
| Fixes | Nao | Sim (muitos automaticos) |
| Checks | ~600 | ~1000+ |
| C/C++ | Ambos | Principalmente C++ |
| Integracao | Standalone | Parte do LLVM |
| Regras CERT/MISRA | Limitado | Excelente |

---

## 7.4 Facebook Infer: Analise Profunda

Facebook Infer e uma ferramenta de analise estatica que usa logica de inferencia de tipos para encontrar bugs de memoria e recursos. Diferente de cppcheck e clang-tidy, Infer faz analise inter-procedural e consegue rastrear dados entre funcoes.

### 7.4.1 Instalacao

```bash
# Ubuntu/Debian
sudo apt-get install infer

# macOS
brew install infer

# Via opam
opam install infer

# Verificar versao
infer --version
```

### 7.4.2 Tipos de Analises

#### Analise de Memoria

```bash
# Analise basica de memoria
infer -- make

# Analise detalhada
infer --bufferoverrun --make

# Todos os analisadores
infer --analysis-path ./inference -- make
```

Bugs detectados:

- **Use-after-free**: Acessar memoria apos liberacao
- **Double-free**: Liberar memoria duas vezes
- **Memory leak**: Alocacao sem liberacao correspondente
- **Buffer overflow**: Acesso fora dos limites do buffer
- **Null dereference**: Desreferenciar ponteiro nulo

#### Analise de Concorrencia

```bash
# Detectar race conditions
infer --racerun --make
```

#### Analise de GVK (Global Variable Key)

```bash
# Detectar uso incorreto de globals
infer --goblin --make
```

### 7.4.3 Exemplos de Bugs Detectados

#### Use-After-Free

```cpp
#include <cstdlib>

void vulnerable_function() {
    int* data = (int*)malloc(sizeof(int) * 100);
    
    if (data == nullptr) {
        return;
    }
    
    free(data);
    
    // BUG: use-after-free
    data[0] = 42;  // Infer detecta: USE_AFTER_FREE
}
```

#### Memory Leak

```cpp
#include <cstdlib>
#include <cstdio>

void leaky_function() {
    int* buffer = (int*)malloc(1024);
    
    if (buffer == nullptr) {
        return;
    }
    
    // BUG: memory leak - buffer nunca e liberado
    // Infer detecta: MEMORY_LEAK
    
    FILE* f = fopen("output.txt", "w");
    if (f) {
        fprintf(f, "buffer: %p\n", buffer);
        fclose(f);
    }
}
```

#### Null Dereference

```cpp
#include <cstdlib>
#include <cstring>

void process_input(const char* input) {
    char* buffer = (char*)malloc(strlen(input) + 1);
    
    // BUG: se malloc retornar NULL, strcpy desreferencia NULL
    // Infer detecta: NULL_RETURNS
    
    strcpy(buffer, input);
    
    free(buffer);
}
```

### 7.4.4 Configuracao do Infer

Criar arquivo `infer.ini`:

```ini
[default]
# Analisadores habilitados
--bufferoverrun
--cyclomatic
--eradicate
--lab
--linters
--quandary
--racerun
--siof
--starvation
--xss

# Profundidade da analise
--pulse-max-bucket-size 5000
--pulse-max-callbacks 50000
--pulse-max-fold 30000

# Filtros
--report-force-deadcode true
--filter-blacklist-path=vendor/
```

### 7.4.5 Integracao com CI/CD

```yaml
# GitHub Actions
- name: Run Facebook Infer
  run: |
    infer -- make -j$(nproc) 2>&1 | tee infer-output.txt
    
    # Verificar se ha findings
    if grep -q "error:" infer-output.txt; then
      echo "Infer found issues!"
      exit 1
    fi
```

### 7.4.6 Interpretacao de Resultados

```bash
# Listar todos os findings
infer report

# Filtrar por tipo
infer report --issues "USE_AFTER_FREE"

# Saida detalhada
infer report --issues "MEMORY_LEAK" --print-eradicate
```

---

## 7.5 CMake Integration: CMAKE_CXX_CLANG_TIDY

CMake oferece suporte nativo a clang-tidy atraves da variavel `CMAKE_CXX_CLANG_TIDY`. Esta e a forma mais simples e recomendada de integrar clang-tidy.

### 7.5.1 Configuracao Basica

#### No CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

# Configurar clang-tidy globalmente
set(CMAKE_CXX_CLANG_TIDY 
    clang-tidy
    --warnings-as-errors=*
    --extra-arg=-std=c++17
)

# Targets
add_executable(myapp src/main.cpp src/parser.cpp)
target_link_libraries(myapp PRIVATE mylib)
```

#### Via Linha de Comando

```bash
# Habilitar clang-tidy durante o build
cmake -B build -DCMAKE_CXX_CLANG_TIDY="clang-tidy;-warnings-as-errors=*" .

# Compilar
cmake --build build
```

### 7.5.2 Configuracao por Target

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

add_library(mylib src/mylib.cpp)

# Configuracao especifica para mylib
set_target_properties(mylib PROPERTIES
    CXX_CLANG_TIDY
    "clang-tidy;--checks=-*,bugprone-*,cert-*;--warnings-as-errors=*"
)

# Configuracao diferente para testes
add_executable(mytests tests/test_main.cpp)
set_target_properties(mytests PROPERTIES
    CXX_CLANG_TIDY
    "clang-tidy;--checks=-*,modernize-*;--warnings-as-errors=-*"
)
```

### 7.5.3 CMAKE_CXX_CPPCHECK

Similar ao clang-tidy, CMake tem suporte nativo a cppcheck:

```cmake
# Habilitar cppcheck
set(CMAKE_CXX_CPPCHECK 
    cppcheck
    --enable=all
    --std=c++17
    --suppress=missingIncludeSystem
)
```

### 7.5.4 Usando compile_commands.json

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

# Gerar compile_commands.json
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# clang-tidy usara automaticamente compile_commands.json
set(CMAKE_CXX_CLANG_TIDY clang-tidy)
```

### 7.5.5 Configuracao Condicional

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

option(ENABLE_CLANG_TIDY "Enable clang-tidy analysis" OFF)
option(ENABLE_CPPCHECK "Enable cppcheck analysis" OFF)

# clang-tidy apenas em modo debug ou CI
if(ENABLE_CLANG_TIDY OR CMAKE_BUILD_TYPE STREQUAL "Debug")
    find_program(CLANG_TIDY_EXE clang-tidy)
    if(CLANG_TIDY_EXE)
        set(CMAKE_CXX_CLANG_TIDY 
            ${CLANG_TIDY_EXE}
            --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
            --warnings-as-errors=*
        )
        message(STATUS "clang-tidy enabled: ${CLANG_TIDY_EXE}")
    else()
        message(WARNING "clang-tidy not found, analysis disabled")
    endif()
endif()

# cppcheck em todas as configuracoes
if(ENABLE_CPPCHECK)
    find_program(CPPCHECK_EXE cppcheck)
    if(CPPCHECK_EXE)
        set(CMAKE_CXX_CPPCHECK
            ${CPPCHECK_EXE}
            --enable=all
            --std=c++17
            --suppress=missingIncludeSystem
            --inline-suppr
        )
        message(STATUS "cppcheck enabled: ${CPPCHECK_EXE}")
    else()
        message(WARNING "cppcheck not found, analysis disabled")
    endif()
endif()

add_executable(myapp src/main.cpp)
```

### 7.5.6 Propriedade CXX_CLANG_TIDY e CMAKE_CXX_CLANG_TIDY

```cmake
# Variavel global - aplica a todos os targets CXX
set(CMAKE_CXX_CLANG_TIDY "clang-tidy;--fix")

# Propriedade de target - sobrescreve a global
set_target_properties(myapp PROPERTIES
    CXX_CLANG_TIDY "clang-tidy;--checks=-*,modernize-*"
)

# Para C
set(CMAKE_C_CLANG_TIDY "clang-tidy;--checks=-*,bugprone-*")
set(CMAKE_C_CPPCHECK "cppcheck;--enable=all")
```

---

## 7.6 Custom Targets para Analise

Targets customizados permitem executar analises como parte do build, mas sem bloquear o desenvolvimento diario.

### 7.6.1 Target de Analise Estatica

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

# Targets do projeto
add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)
target_compile_features(mylib PUBLIC cxx_std_17)

add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE mylib)

# ============================================================
# Custom targets para analise estatica
# ============================================================

# Target para clang-tidy
find_program(CLANG_TIDY_EXE clang-tidy)
if(CLANG_TIDY_EXE)
    add_custom_target(clang-tidy
        COMMAND ${CLANG_TIDY_EXE}
            --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
            --export-fixes=${CMAKE_BINARY_DIR}/clang-tidy-fixes.yaml
            -p ${CMAKE_BINARY_DIR}
            ${CMAKE_SOURCE_DIR}/src/main.cpp
            ${CMAKE_SOURCE_DIR}/src/mylib.cpp
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running clang-tidy analysis"
        VERBATIM
    )
    add_dependencies(analysis clang-tidy)
endif()

# Target para cppcheck
find_program(CPPCHECK_EXE cppcheck)
if(CPPCHECK_EXE)
    add_custom_target(cppcheck
        COMMAND ${CPPCHECK_EXE}
            --enable=all
            --std=c++17
            --suppress=missingIncludeSystem
            --inline-suppr
            --project=${CMAKE_BINARY_DIR}/compile_commands.json
            --output-file=${CMAKE_BINARY_DIR}/cppcheck-report.txt
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running cppcheck analysis"
        VERBATIM
    )
    add_dependencies(analysis cppcheck)
endif()

# Meta-target que executa todas as analises
add_custom_target(analysis
    COMMENT "Running all static analyses"
)
```

### 7.6.2 Target com Verificacao de Erros

```cmake
# Analise que falha o build se encontrar problemas
add_custom_target(static-analysis-check
    COMMAND ${CMAKE_COMMAND} -E echo "=== Running clang-tidy ==="
    COMMAND ${CLANG_TIDY_EXE}
        --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
        --warnings-as-errors=*
        -p ${CMAKE_BINARY_DIR}
        $<TARGET_PROPERTY:mylib,SOURCES>
    COMMAND ${CMAKE_COMMAND} -E echo "=== Running cppcheck ==="
    COMMAND ${CPPCHECK_EXE}
        --enable=all
        --error-exitcode=1
        --std=c++17
        --project=${CMAKE_BINARY_DIR}/compile_commands.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Static analysis (will fail on errors)"
    VERBATIM
)

# Executar antes de testes
add_custom_target(pre-test-analysis
    DEPENDS static-analysis-check
)
add_dependencies(check pre-test-analysis)
```

### 7.6.3 Analise Incremental

```cmake
# Analisar apenas arquivos modificados
add_custom_target(tidy-incremental
    COMMAND ${CMAKE_COMMAND} 
        -DCLANG_TIDY=${CLANG_TIDY_EXE}
        -DBUILD_DIR=${CMAKE_BINARY_DIR}
        -DSOURCE_DIR=${CMAKE_SOURCE_DIR}
        -P ${CMAKE_SOURCE_DIR}/scripts/run-tidy-incremental.cmake
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Running incremental clang-tidy"
    VERBATIM
)
```

Script `scripts/run-tidy-incremental.cmake`:

```cmake
# run-tidy-incremental.cmake
execute_process(
    COMMAND git diff --name-only --diff-filter=ACMR HEAD
    OUTPUT_VARIABLE MODIFIED_FILES
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

string(REPLACE "\n" ";" FILE_LIST "${MODIFIED_FILES}")

set(CPP_FILES "")
foreach(FILE ${FILE_LIST})
    if(FILE MATCHES "\\.(cpp|cxx|cc|c|h|hpp)$")
        list(APPEND CPP_FILES "${SOURCE_DIR}/${FILE}")
    endif()
endforeach()

if(CPP_FILES)
    message(STATUS "Analyzing ${CMAKE_CURRENT_LIST_FILE} files:")
    foreach(F ${CPP_FILES})
        message(STATUS "  ${F}")
    endforeach()
    
    execute_process(
        COMMAND ${CLANG_TIDY} --config-file=${SOURCE_DIR}/.clang-tidy
                --export-fixes=${BUILD_DIR}/tidy-fixes.yaml
                --p ${BUILD_DIR}
                ${CPP_FILES}
        RESULT_VARIABLE RESULT
    )
    
    if(NOT RESULT EQUAL 0)
        message(FATAL_ERROR "clang-tidy found issues!")
    endif()
else()
    message(STATUS "No C++ files to analyze")
endif()
```

### 7.6.4 Relatorio HTML de Analise

```cmake
# Gerar relatorio HTML com clang-tidy
add_custom_target(tidy-report
    COMMAND ${CLANG_TIDY_EXE}
        --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
        --format=html
        --output=${CMAKE_BINARY_DIR}/tidy-report.html
        -p ${CMAKE_BINARY_DIR}
        $<TARGET_PROPERTY:mylib,SOURCES>
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating clang-tidy HTML report"
    VERBATIM
)

# Gerar relatorio com cppcheck
add_custom_target(cppcheck-report
    COMMAND ${CMAKE_BINARY_DIR}/scripts/generate-cppcheck-html.sh
        --input=${CMAKE_BINARY_DIR}/cppcheck-report.txt
        --output=${CMAKE_BINARY_DIR}/cppcheck-report.html
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating cppcheck HTML report"
    VERBATIM
)
```

Script `scripts/generate-cppcheck-html.sh`:

```bash
#!/bin/bash
set -euo pipefail

INPUT=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --input) INPUT="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

cat > "$OUTPUT" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>cppcheck Report</title>
    <style>
        body { font-family: monospace; margin: 20px; }
        .error { color: red; }
        .warning { color: orange; }
        .style { color: blue; }
        table { border-collapse: collapse; width: 100%; }
        td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
<h1>cppcheck Analysis Report</h1>
<table>
<tr><th>File</th><th>Line</th><th>Severity</th><th>ID</th><th>Message</th></tr>
HTMLHEAD

while IFS= read -r line; do
    if [[ $line == *": error:"* ]]; then
        CLASS="error"
    elif [[ $line == *": warning:"* ]]; then
        CLASS="warning"
    elif [[ $line == *": style:"* ]]; then
        CLASS="style"
    else
        CLASS=""
    fi
    
    if [[ $line =~ ^(.+):([0-9]+):\[(.*)\]\ (.+)$ ]]; then
        FILE="${BASH_REMATCH[1]}"
        LINE="${BASH_REMATCH[2]}"
        SEVERITY="${BASH_REMATCH[3]}"
        MSG="${BASH_REMATCH[4]}"
        echo "<tr class=\"$CLASS\"><td>$FILE</td><td>$LINE</td><td>$SEVERITY</td><td></td><td>$MSG</td></tr>" >> "$OUTPUT"
    fi
done < "$INPUT"

cat >> "$OUTPUT" << 'HTMLFOOT'
</table>
</body>
</html>
HTMLFOOT

echo "Report generated: $OUTPUT"
```

---

## 7.7 SARIF Output para GitHub

SARIF (Static Analysis Results Interchange Format) e o formato padrao para integrar resultados de analise estatica com GitHub Code Scanning.

### 7.7.1 O que e SARIF

SARIF e um formato JSON padronizado pela OASIS que permite:

- Compartilhar resultados entre ferramentas
- Integrar com GitHub, Azure DevOps, etc.
- Correlacionar findings entre ferramentas
- Gerar metricas de qualidade

### 7.7.2 Formato SARIF

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "clang-tidy",
          "semanticVersion": "16.0.0",
          "rules": [
            {
              "id": "bugprone-use-after-move",
              "name": "bugprone-use-after-move",
              "shortDescription": {
                "text": "Use after move"
              },
              "fullDescription": {
                "text": "A variable is used after it has been moved"
              },
              "defaultConfiguration": {
                "level": "error"
              },
              "properties": {
                "tags": [
                  "bugprone",
                  "memory"
                ]
              }
            }
          ]
        }
      },
      "results": [
        {
          "ruleId": "bugprone-use-after-move",
          "level": "error",
          "message": {
            "text": "use after move of 'temp'"
          },
          "locations": [
            {
              "physicalLocation": {
                "artifactLocation": {
                  "uri": "src/main.cpp",
                  "uriBaseId": "%SRCROOT%"
                },
                "region": {
                  "startLine": 42,
                  "startColumn": 5,
                  "endLine": 42,
                  "endColumn": 10
                }
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### 7.7.3 Gerando SARIF com clang-tidy

```bash
# clang-tidy pode gerar SARIF diretamente
clang-tidy --format=sarif --output=sarif.json \
    src/*.cpp -- -std=c++17

# Usando clang-tidy para gerar SARIF
clang-tidy --export-fixes=fixes.yaml \
    --format=sarif \
    --output=results.sarif \
    src/*.cpp -- -std=c++17
```

### 7.7.4 Gerando SARIF com cppcheck

cppcheck nao gera SARIF nativamente, mas podemos converter:

Script `scripts/convert-cppcheck-to-sarif.sh`:

```bash
#!/bin/bash
set -euo pipefail

INPUT=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --input) INPUT="$2"; shift 2 ;;
        --output) OUTPUT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

python3 << PYTHON
import json
import sys
import xml.etree.ElementTree as ET

# Parse cppcheck XML
tree = ET.parse("$INPUT")
root = tree.getroot()

results = []
rules = {}

for error in root.findall('.//error'):
    rule_id = error.get('id')
    severity = error.get('severity')
    msg = error.get('msg')
    verbose = error.get('verbose', msg)
    
    # Adicionar regra se nao existe
    if rule_id not in rules:
        rules[rule_id] = {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": msg},
            "fullDescription": {"text": verbose},
            "defaultConfiguration": {
                "level": "error" if severity == "error" else 
                         "warning" if severity == "warning" else "note"
            }
        }
    
    # Extrair localizacao
    locations = []
    for location in error.findall('.//location'):
        file = location.get('file')
        line = int(location.get('line', 0))
        column = int(location.get('column', 0))
        
        loc = {
            "physicalLocation": {
                "artifactLocation": {
                    "uri": file,
                    "uriBaseId": "%SRCROOT%"
                },
                "region": {
                    "startLine": line,
                    "startColumn": column if column > 0 else 1
                }
            }
        }
        locations.append(loc)
    
    results.append({
        "ruleId": rule_id,
        "level": "error" if severity == "error" else 
                 "warning" if severity == "warning" else "note",
        "message": {"text": verbose},
        "locations": locations
    })

sarif = {
    "version": "2.1.0",
    "runs": [{
        "tool": {
            "driver": {
                "name": "cppcheck",
                "semanticVersion": "2.13",
                "rules": list(rules.values())
            }
        },
        "results": results
    }]
}

with open("$OUTPUT", 'w') as f:
    json.dump(sarif, f, indent=2)

print(f"Converted {len(results)} results to SARIF")
PYTHON

echo "SARIF output: $OUTPUT"
```

### 7.7.5 Merge de SARIFs

```bash
# Instalar sarif-multitool
dotnet tool install -g sarif.multitool

# Merge multiplos SARIFs
sarif merge results1.sarif results2.sarif \
    --output=combined.sarif \
    --merge-runs
```

Script Python para merge simples:

```python
#!/usr/bin/env python3
"""Merge multiple SARIF files into one."""
import json
import sys
from typing import List, Dict

def merge_sarifs(sarif_files: List[str]) -> Dict:
    """Merge multiple SARIF files."""
    merged = {
        "version": "2.1.0",
        "runs": []
    }
    
    for sarif_file in sarif_files:
        with open(sarif_file, 'r') as f:
            sarif = json.load(f)
        
        for run in sarif.get("runs", []):
            merged["runs"].append(run)
    
    return merged

def main():
    if len(sys.argv) < 3:
        print("Usage: merge-sarif.py output.sarif input1.sarif input2.sarif ...")
        sys.exit(1)
    
    output_file = sys.argv[1]
    input_files = sys.argv[2:]
    
    merged = merge_sarifs(input_files)
    
    with open(output_file, 'w') as f:
        json.dump(merged, f, indent=2)
    
    total_results = sum(
        len(run.get("results", []))
        for run in merged["runs"]
    )
    
    print(f"Merged {len(input_files)} SARIF files")
    print(f"Total results: {total_results}")
    print(f"Output: {output_file}")

if __name__ == "__main__":
    main()
```

### 7.7.6 Integracao com GitHub Actions

```yaml
name: Static Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  static-analysis:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y clang-tidy cppcheck
      
      - name: Configure CMake
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
      
      - name: Run clang-tidy
        run: |
          clang-tidy --format=sarif --output=clang-tidy.sarif \
            $(find src -name '*.cpp') \
            -- -std=c++17 -Iinclude \
               -I${{ github.workspace }}/build
      
      - name: Run cppcheck
        run: |
          cppcheck --xml --xml-version=2 \
            --enable=all --std=c++17 \
            --project=build/compile_commands.json \
            2> cppcheck.xml
      
      - name: Convert cppcheck to SARIF
        run: |
          python3 scripts/convert-cppcheck-to-sarif.sh \
            --input=cppcheck.xml \
            --output=cppcheck.sarif
      
      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: |
            clang-tidy.sarif
            cppcheck.sarif
          category: static-analysis
```

---

## 7.8 Compile Warnings como Erros

Configurar warnings como erros e essencial para qualidade. Em seguranca, isso e **obrigatorio**.

### 7.8.1 Flags de Warning do GCC

```cmake
# Warnings basicos
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")

# Warnings especificos para seguranca
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    -Wformat=2 \
    -Wformat-security \
    -Wformat-nonliteral \
    -Wconversion \
    -Wsign-conversion \
    -Wnull-dereference \
    -Wimplicit-fallthrough \
    -Wdouble-promotion \
    -Wshadow \
    -Wold-style-cast \
    -Woverloaded-virtual \
    -Wnon-virtual-dtor \
    -Wunused"
)

# Tratar warnings como erros
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror")
```

### 7.8.2 Flags de Warning do Clang

```cmake
# Flags Clang para seguranca
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
    -Weverything \
    -Wno-c++98-compat \
    -Wno-c++98-compat-pedantic \
    -Wno-padded \
    -Wno-exit-time-destructors \
    -Wno-global-constructors"
)

# Tratar warnings como erros
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror")
```

### 7.8.3 Configuracao por Target

```cmake
add_library(mylib src/mylib.cpp)

# Bibliotecas: warnings nao devem ser erros (so no build final)
target_compile_options(mylib PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:Clang>:-Weverything -Wno-c++98-compat>
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)

# Executavel: warnings SAO erros
add_executable(myapp src/main.cpp)
target_compile_options(myapp PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra -Wpedantic -Werror>
    $<$<CXX_COMPILER_ID:Clang>:-Weverything -Wno-c++98-compat -Werror>
    $<$<CXX_COMPILER_ID:MSVC>:/W4 /WX>
)
```

### 7.8.4 Desabilitar Warnings Especificos

```cmake
# Para vendored code (nao controlamos)
set_source_files_properties(
    vendor/third_party.cpp
    PROPERTIES COMPILE_FLAGS "-w"
)

# Ou usando isystem (trata como sistema)
target_include_directories(mylib SYSTEM PRIVATE
    ${CMAKE_SOURCE_DIR}/vendor/include
)

# Desabilitar warnings especificos
target_compile_options(mylib PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wno-unused-parameter>
    $<$<CXX_COMPILER_ID:Clang>:-Wno-padded>
)
```

### 7.8.5 Propriedade COMPILE_WARNING_AS_ERROR

CMake 3.26+ oferece propriedade nativa:

```cmake
cmake_minimum_required(VERSION 3.26)
project(MyProject LANGUAGES CXX)

add_executable(myapp src/main.cpp)

# Ativar warnings como erros
set_target_properties(myapp PROPERTIES
    COMPILE_WARNING_AS_ERROR ON
)
```

### 7.8.6 Diferentes Niveis de Rigor

```cmake
# Opcao para controlar rigor
option(STRICT_WARNINGS "Enable strict warning mode" OFF)
option(SECURITY_WARNINGS "Enable security-focused warnings" OFF)

# Warnings basicos sempre ativos
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra")

if(STRICT_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wpedantic -Werror")
endif()

if(SECURITY_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
        -Wformat=2 \
        -Wformat-security \
        -Wformat-nonliteral \
        -Wnull-dereference \
        -Wimplicit-fallthrough"
    )
    
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
            -Wimplicit-fallthrough \
            -Wcomma"
        )
    endif()
endif()
```

---

## 7.9 MISRA C/C++ Compliance

MISRA (Motor Industry Software Reliability Association) define padroes de codificacao para software de sistemas criticos. Embora originalmente para automotive, e amplamente adotado em aerospace, medical, e finance.

### 7.9.1 O que e MISRA

MISRA C:2012 e MISRA C++:2023 definem regras de codificacao que:

- Previnem comportamento indefinido
- Tornam o codigo portavel e auditavel
- Facilitam verificacao automatica
- Reduzem riscos em sistemas criticos

### 7.9.2 Regras MISRA C:2012

```
Mandatory Rules (100% compliance obrigatorio):
- Rule 1.1: O programa nao deve conter construtos que nao estejam no Standard C
- Rule 1.2: Linguagem extensions devem ser documentadas
- Rule 1.3: Nao deve haver converte de tipo inseguro

Required Rules (compliance esperado):
- Rule 2.1: Nao deve haver codigo inalcancavel
- Rule 2.2: Nao deve haver codigo morto
- Rule 3.1: // nao deve ser usado para comentar multi-line
- Rule 3.2: // nao deve terminar com \
- Rule 8.13: Um ponteiro para const deve ser usado quando o objeto nao e modificado
- Rule 10.1: Operando de um operador ternario deve ser logico
- Rule 11.3: Nao deve haver cast entre ponteiro para objeto e tipo inteiro

Advisory Rules (recomendado):
- Rule 2.7: Nao deve haver codigo nao utilizado
- Rule 8.7: Funcoes e objects devem ter linkage limitado
```

### 7.9.3 Regras MISRA C++:2023

```
Mandatory Rules:
- Rule 0.1.1: O programa nao deve conter construtos que nao estejam no Standard C++
- Rule 0.1.2: O programa nao deve depender de comportamento indefinido
- Rule 1.1.1: O programa nao deve conter construtos que nao estejam no Standard C++
- Rule 1.2.1: O programa nao deve depender de comportamento indefinido

Required Rules:
- Rule 2.1.1: Nao deve haver conversoes implicitas que alterem o valor
- Rule 2.1.2: Nao deve haver conversoes entre ponteiros para objetos e ponteiros para inteiros
- Rule 2.1.3: Nao deve haver conversoes de ponteiro para tipo incompativel
- Rule 3.1.1: O nome de um object nao deve ser escondido em escopo aninhado
```

### 7.9.4 Verificacao MISRA com clang-tidy

clang-tidy tem suporte limitado a regras MISRA via plugins:

```bash
# Usar clang-tidy com checks MISRA
clang-tidy src/*.cpp \
    --checks='-*,cert-*,cppcoreguidelines-*' \
    -- -std=c++17
```

### 7.9.5 Ferramentas Open-Source para MISRA

#### cppcheck com MISRA addon

```bash
# Gerar addon MISRA
cppcheck --addon=misc --enable=all src/

# Criar arquivo de addon
cat > cppcheck_addons/misra.json << 'EOF'
{
  "script": "addons/misra.py",
  "args": ["--rule-texts=true"]
}
EOF

# Executar
cppcheck --addon=cppcheck_addons/misra.json src/
```

#### Polyspace Bug Finder (comercial)

Polyspace e a ferramenta comercial mais usada para MISRA, mas para projetos open-source:

### 7.9.6 Configuracao CMake para MISRA

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

option(ENABLE_MISRA_CHECK "Enable MISRA compliance checks" OFF)

if(ENABLE_MISRA_CHECK)
    # cppcheck com addon MISRA
    find_program(CPPCHECK_EXE cppcheck)
    if(CPPCHECK_EXE)
        add_custom_target(misra-check
            COMMAND ${CPPCHECK_EXE}
                --addon=${CMAKE_SOURCE_DIR}/cppcheck_addons/misra.json
                --enable=all
                --std=c11
                --project=${CMAKE_BINARY_DIR}/compile_commands.json
            WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
            COMMENT "Running MISRA compliance check"
            VERBATIM
        )
    endif()
endif()
```

---

## 7.10 CERT C/C++ Rules

CERT (Computer Emergency Response Team) define regras de codificacao segura para prevenir vulnerabilidades.

### 7.10.1 CERT C Rules

#### Fatos e Linguagem (F)

```
FIO30-C: Use.Restrict pointers for file access
FIO32-C: Do not open more files than implementation supports
FIO33-C: Check for end-of-file condition
FIO34-C: Write to read-only files only when appropriate
FIO38-C: Do not copy FILE values
FIO39-C: Do not open a file that is already open
```

#### Inteiros (INT)

```
INT30-C: Ensure that unsigned integer operations do not result in wraparound
INT31-C: Ensure that integer conversions do not result in loss of data
INT32-C: Ensure that operations on signed integers do not result in overflow
INT33-C: Ensure that division and modulo operations do not result in divide-by-zero
INT34-C: Do not shift left by a negative number or by greater than or equal to bit width
INT35-C: Use prefix notation for the increment/decrement operator on iterators
```

#### Memoria (MEM)

```
MEM30-C: Allocate and release memory properly
MEM31-C: Free dynamically allocated memory when no longer needed
MEM32-C: Detect and handle memory allocation errors
MEM33-C: Allocate and copy structures containing flexible arrays
MEM34-C: Allocate sufficient memory for an object
MEM35-C: Allocate enough memory for flexible array members
```

#### Seguranca (SEC)

```
SEC30-C: Use cryptographically strong random number generators
SEC31-C: Ensure that cryptographic random number generators generate unpredictable values
SEC32-C: Limit the amount of data passed to untrusted code
SEC33-C: Generate strong random numbers for security-critical applications
SEC34-C: Use cryptographically strong pseudo-random number generators
```

### 7.10.2 CERT C++ Rules

```
ENV31-CPP: Do not rely on an undefined behavior
ERR33-CPP: Detect and handle standard library errors
CON31-CPP: Ensure mutexes are unlocked before releasing
CON32-CPP: Ensure locks are acquired in consistent order
CON33-CPP: Avoid deadlocks by using a consistent lock order
CON34-CPP: Properly sequence signaling and waiting on condition variables
```

### 7.10.3 Verificacao com clang-tidy

clang-tidy tem suporte a CERT via built-in checks:

```yaml
# .clang-tidy
---
Checks: >
  cert-*,
  cert-dcl50-cpp,
  cert-dcl54-cpp,
  cert-err33-c,
  cert-err34-c,
  cert-err52-cpp,
  cert-err58-cpp,
  cert-err59-cpp,
  cert-err60-cpp,
  cert-err61-cpp,
  cert-err69-cpp,
  cert-flp30-c,
  cert-msc24-c,
  cert-msc30-c,
  cert-msc32-c,
  cert-msc37-c,
  cert-msc50-cpp,
  cert-msc51-cpp

WarningsAsErrors: >
  cert-err33-c,
  cert-err34-c,
  cert-err52-cpp,
  cert-err58-cpp,
  cert-err59-cpp,
  cert-err60-cpp,
  cert-err61-cpp
```

### 7.10.4 Configuracao CMake para CERT

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

option(ENABLE_CERT_CHECK "Enable CERT compliance checks" OFF)

if(ENABLE_CERT_CHECK)
    # clang-tidy com checks CERT
    find_program(CLANG_TIDY_EXE clang-tidy)
    if(CLANG_TIDY_EXE)
        set(CMAKE_CXX_CLANG_TIDY
            ${CLANG_TIDY_EXE}
            --checks=cert-*
            --warnings-as-errors=cert-*
            --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy-cert
        )
    endif()
endif()
```

---

## 7.11 CWE Mapping para Findings

CWE (Common Weakness Enumeration) e uma lista padrao de vulnerabilidades de seguranca. Mapear findings para CWE permite correlacionar com CVEs e ferramentas de gestao de vulnerabilidades.

### 7.11.1 CWEs Comuns em C/C++

```
CWE-120: Buffer Copy without Checking Size of Input ('Classic Buffer Overflow')
CWE-125: Out-of-bounds Read
CWE-131: Incorrect Calculation of Buffer Size
CWE-190: Integer Overflow or Wraparound
CWE-191: Integer Underflow
CWE-193: Off-by-one Error
CWE-195: Signed to Unsigned Conversion Error
CWE-197: Numeric Truncation Error
CWE-200: Exposure of Sensitive Information
CWE-242: Use of Inherently Dangerous Function
CWE-319: Cleartext Transmission of Sensitive Information
CWE-327: Use of a Broken or Risky Cryptographic Algorithm
CWE-362: Concurrent Execution Using Shared Resource with Improper Synchronization ('Race Condition')
CWE-367: TOCTOU Race Condition
CWE-401: Missing Release of Memory after Effective Lifetime ('Memory Leak')
CWE-404: Improper Resource Shutdown or Release
CWE-415: Double Free
CWE-416: Use After Free
CWE-421: Race Condition During Access to Alternate Channel
CWE-457: Use of Uninitialized Variable
CWE-458: Missing Initialization for Critical Variable
CWE-476: NULL Pointer Dereference
CWE-562: Return of Stack Variable Address
CWE-570: Expression is Always False
CWE-587: Assignment of Fixed Address to a Pointer
CWE-665: Improper Initialization
CWE-674: Uncontrolled Recursion
CWE-681: Incorrect Conversion between Numeric Types
CWE-704: Incorrect Type Conversion or Cast
CWE-758: Reliance on Undefined Behavior
CWE-761: Free of Pointer not at Start of Buffer
CWE-762: Mismatched Memory Management Routines
CWE-763: Use-after-free
CWE-764: Multiple Locks of a Critical Resource
CWE-765: Multiple Unlocks of a Critical Resource
CWE-783: Operator Precedence Logic Error
CWE-788: Access of Memory Location After End of Buffer
CWE-789: Memory Allocation with Excessive Size Value
CWE-806: Buffer Access Using Size of Source Buffer
CWE-823: Use of Out-of-range Pointer Offset
CWE-824: Access of Uninitialized Pointer
CWE-825: Expired Pointer Dereference
CWE-835: Loop with Unreachable Exit Condition ('Infinite Loop')
CWE-843: Type Confusion
```

### 7.11.2 Mapeamento clang-tidy para CWE

clang-tidy pode adicionar tags CWE aos resultados:

```bash
# clang-tidy com informacao CWE
clang-tidy --format=json --output=results.json \
    src/*.cpp -- -std=c++17

# Saida incluindo CWE
# CWE-457: Use of Uninitialized Variable
# CWE-416: Use After Free
# CWE-476: NULL Pointer Dereference
```

### 7.11.3 Mapeamento cppcheck para CWE

cppcheck adiciona tags CWE ao formato XML:

```xml
<error id="uninitvar" severity="error" 
       msg="Uninitialized variable" 
       cwe="457"/>
<error id="memleak" severity="error"
       msg="Possible memory leak"
       cwe="401"/>
<error id="nullPointer" severity="error"
       msg="Possible null pointer dereference"
       cwe="476"/>
```

### 7.11.4 Script de Mapeamento

Script `scripts/map-cwe.py`:

```python
#!/usr/bin/env python3
"""Map static analysis findings to CWE IDs."""
import json
import xml.etree.ElementTree as ET
from typing import List, Dict

# Mapeamento de check IDs para CWE
CHECK_TO_CWE = {
    # clang-tidy checks
    "bugprone-dangling-handle": "CWE-416",
    "bugprone-use-after-move": "CWE-416",
    "cert-err33-c": "CWE-252",
    "cert-err34-c": "CWE-190",
    "cppcoreguidelines-init-variables": "CWE-457",
    "cppcoreguidelines-pro-type-member-init": "CWE-665",
    "cppcoreguidelines-slicing": "CWE-843",
    
    # cppcheck IDs
    "uninitvar": "CWE-457",
    "memleak": "CWE-401",
    "nullPointer": "CWE-476",
    "resourceLeak": "CWE-404",
    "doubleFree": "CWE-415",
    "bufferAccessOutOfBounds": "CWE-787",
    "arrayIndexOutOfBounds": "CWE-125",
    "integerOverflow": "CWE-190",
    "negativeIndex": "CWE-125",
    "sizeofwithNoArrayArgument": "CWE-131",
}

def parse_cppcheck_xml(xml_file: str) -> List[Dict]:
    """Parse cppcheck XML output and map to CWE."""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    findings = []
    for error in root.findall('.//error'):
        check_id = error.get('id')
        severity = error.get('severity')
        msg = error.get('msg')
        cwe_id = CHECK_TO_CWE.get(check_id, "CWE-Unknown")
        
        findings.append({
            "tool": "cppcheck",
            "check_id": check_id,
            "severity": severity,
            "message": msg,
            "cwe": cwe_id,
        })
    
    return findings

def parse_sarif(sarif_file: str) -> List[Dict]:
    """Parse SARIF file and map to CWE."""
    with open(sarif_file, 'r') as f:
        sarif = json.load(f)
    
    findings = []
    for run in sarif.get("runs", []):
        tool_name = run.get("tool", {}).get("driver", {}).get("name", "unknown")
        
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "unknown")
            level = result.get("level", "note")
            message = result.get("message", {}).get("text", "")
            cwe_id = CHECK_TO_CWE.get(rule_id, "CWE-Unknown")
            
            findings.append({
                "tool": tool_name,
                "check_id": rule_id,
                "severity": level,
                "message": message,
                "cwe": cwe_id,
            })
    
    return findings

def generate_cwe_report(findings: List[Dict]) -> Dict:
    """Generate CWE-based summary."""
    cwe_counts = {}
    for finding in findings:
        cwe = finding["cwe"]
        if cwe not in cwe_counts:
            cwe_counts[cwe] = 0
        cwe_counts[cwe] += 1
    
    # Ordenar por contagem
    sorted_cwes = sorted(cwe_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_findings": len(findings),
        "cwe_summary": dict(sorted_cwes),
        "by_tool": {
            tool: len([f for f in findings if f["tool"] == tool])
            for tool in set(f["tool"] for f in findings)
        }
    }

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: map-cwe.py <cppcheck.xml|sarif.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if input_file.endswith('.xml'):
        findings = parse_cppcheck_xml(input_file)
    elif input_file.endswith('.json') or input_file.endswith('.sarif'):
        findings = parse_sarif(input_file)
    else:
        print(f"Unsupported file format: {input_file}")
        sys.exit(1)
    
    report = generate_cwe_report(findings)
    
    print(f"\nCWE Mapping Report")
    print(f"=" * 50)
    print(f"Total findings: {report['total_findings']}")
    print(f"\nFindings by tool:")
    for tool, count in report["by_tool"].items():
        print(f"  {tool}: {count}")
    print(f"\nFindings by CWE:")
    for cwe, count in report["cwe_summary"].items():
        print(f"  {cwe}: {count}")

if __name__ == "__main__":
    main()
```

---

## 7.12 Exemplo: Pipeline Completa de Analise

Este exemplo demonstra uma pipeline completa de analise estatica integrada com CMake.

### 7.12.1 Estrutura do Projeto

```
secure-project/
├── CMakeLists.txt
├── .clang-tidy
├── cppcheck-suppressions.xml
├── include/
│   └── secure_project/
│       ├── crypto.h
│       └── parser.h
├── src/
│   ├── main.cpp
│   ├── crypto.cpp
│   └── parser.cpp
├── tests/
│   ├── test_crypto.cpp
│   └── test_parser.cpp
├── scripts/
│   ├── run-static-analysis.sh
│   └── generate-reports.sh
└── .github/
    └── workflows/
        └── static-analysis.yml
```

### 7.12.2 CMakeLists.txt Principal

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureProject 
    VERSION 1.0.0
    LANGUAGES CXX
    DESCRIPTION "Secure project with static analysis"
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================
# Opcoes de Analise
# ============================================================

option(ENABLE_STATIC_ANALYSIS "Enable all static analysis tools" OFF)
option(ENABLE_CLANG_TIDY "Enable clang-tidy" OFF)
option(ENABLE_CPPCHECK "Enable cppcheck" OFF)
option(ENABLE_MISRA_CHECK "Enable MISRA compliance" OFF)
option(ENABLE_CERT_CHECK "Enable CERT compliance" OFF)
option(ENABLE_SECURITY_WARNINGS "Enable security-focused warnings" OFF)

# ============================================================
# Configuracao de Warnings
# ============================================================

# Warnings basicos
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Wpedantic")

if(ENABLE_SECURITY_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
        -Wformat=2 \
        -Wformat-security \
        -Wformat-nonliteral \
        -Wconversion \
        -Wsign-conversion \
        -Wnull-dereference \
        -Wimplicit-fallthrough \
        -Wdouble-promotion \
        -Wshadow \
        -Wold-style-cast \
        -Woverloaded-virtual \
        -Wnon-virtual-dtor \
        -Wunused"
    )
    
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Weverything -Wno-c++98-compat -Wno-padded")
    endif()
    
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Werror")
    endif()
endif()

# ============================================================
# Configuracao clang-tidy
# ============================================================

if(ENABLE_CLANG_TIDY OR ENABLE_STATIC_ANALYSIS)
    find_program(CLANG_TIDY_EXE clang-tidy)
    if(CLANG_TIDY_EXE)
        message(STATUS "clang-tidy found: ${CLANG_TIDY_EXE}")
        
        set(CLANG_TIDY_CHECKS "bugprone-*,cert-*,cppcoreguidelines-*")
        
        if(ENABLE_MISRA_CHECK)
            set(CLANG_TIDY_CHECKS "${CLANG_TIDY_CHECKS},misc-*")
        endif()
        
        if(ENABLE_CERT_CHECK)
            set(CLANG_TIDY_CHECKS "${CLANG_TIDY_CHECKS},cert-*")
        endif()
        
        set(CMAKE_CXX_CLANG_TIDY
            ${CLANG_TIDY_EXE}
            --checks=${CLANG_TIDY_CHECKS}
            --warnings-as-errors=*
            --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
            --export-fixes=${CMAKE_BINARY_DIR}/clang-tidy-fixes.yaml
        )
    else()
        message(WARNING "clang-tidy not found")
    endif()
endif()

# ============================================================
# Configuracao cppcheck
# ============================================================

if(ENABLE_CPPCHECK OR ENABLE_STATIC_ANALYSIS)
    find_program(CPPCHECK_EXE cppcheck)
    if(CPPCHECK_EXE)
        message(STATUS "cppcheck found: ${CPPCHECK_EXE}")
        
        set(CMAKE_CXX_CPPCHECK
            ${CPPCHECK_EXE}
            --enable=all
            --std=c++17
            --suppress=missingIncludeSystem
            --inline-suppr
            --project=${CMAKE_BINARY_DIR}/compile_commands.json
            --output-file=${CMAKE_BINARY_DIR}/cppcheck-report.txt
            --xml
        )
    else()
        message(WARNING "cppcheck not found")
    endif()
endif()

# ============================================================
# Targets do Projeto
# ============================================================

# Biblioteca principal
add_library(secure_lib STATIC
    src/crypto.cpp
    src/parser.cpp
)

target_include_directories(secure_lib PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

target_compile_features(secure_lib PUBLIC cxx_std_17)

# Executavel principal
add_executable(secure_app
    src/main.cpp
)

target_link_libraries(secure_app PRIVATE secure_lib)

# ============================================================
# Targets de Analise Estatica
# ============================================================

# Meta-target para todas as analises
add_custom_target(static-analysis
    COMMENT "Running all static analyses"
)

# clang-tidy
if(CLANG_TIDY_EXE)
    add_custom_target(clang-tidy
        COMMAND ${CLANG_TIDY_EXE}
            --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
            --export-fixes=${CMAKE_BINARY_DIR}/clang-tidy-fixes.yaml
            -p ${CMAKE_BINARY_DIR}
            $<TARGET_PROPERTY:secure_lib,SOURCES>
            $<TARGET_PROPERTY:secure_app,SOURCES>
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running clang-tidy"
        VERBATIM
    )
    add_dependencies(static-analysis clang-tidy)
endif()

# cppcheck
if(CPPCHECK_EXE)
    add_custom_target(cppcheck
        COMMAND ${CPPCHECK_EXE}
            --enable=all
            --std=c++17
            --suppress=missingIncludeSystem
            --inline-suppr
            --project=${CMAKE_BINARY_DIR}/compile_commands.json
            --output-file=${CMAKE_BINARY_DIR}/cppcheck-report.txt
        WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
        COMMENT "Running cppcheck"
        VERBATIM
    )
    add_dependencies(static-analysis cppcheck)
endif()

# Relatorios SARIF
add_custom_target(generate-sarif
    COMMAND ${CMAKE_SOURCE_DIR}/scripts/generate-sarif.sh
        --clang-tidy=${CMAKE_BINARY_DIR}/clang-tidy-fixes.yaml
        --cppcheck=${CMAKE_BINARY_DIR}/cppcheck-report.txt
        --output=${CMAKE_BINARY_DIR}/combined.sarif
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating SARIF reports"
    VERBATIM
)

# Meta-target para analise + relatorios
add_custom_target(full-analysis
    DEPENDS static-analysis generate-sarif
)

# ============================================================
# Testes
# ============================================================

enable_testing()
find_package(GTest QUIET)

if(GTest_FOUND)
    add_executable(test_crypto tests/test_crypto.cpp)
    target_link_libraries(test_crypto PRIVATE secure_lib GTest::gtest_main)
    add_test(NAME test_crypto COMMAND test_crypto)
    
    add_executable(test_parser tests/test_parser.cpp)
    target_link_libraries(test_parser PRIVATE secure_lib GTest::gtest_main)
    add_test(NAME test_parser COMMAND test_parser)
endif()
```

### 7.12.3 Script de Analise Completa

Script `scripts/run-static-analysis.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Configuracoes
BUILD_DIR="build-analysis"
SOURCE_DIR="$(pwd)"
OUTPUT_DIR="analysis-results"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funcoes auxiliares
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Criar diretorio de saida
mkdir -p "${OUTPUT_DIR}"

# ============================================================
# Passo 1: Configurar CMake com analises habilitadas
# ============================================================
log_info "Configurando CMake com analises habilitadas..."
cmake -B "${BUILD_DIR}" \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_STATIC_ANALYSIS=ON \
    -DENABLE_SECURITY_WARNINGS=ON \
    -DENABLE_MISRA_CHECK=ON \
    -DENABLE_CERT_CHECK=ON \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    "${SOURCE_DIR}"

# ============================================================
# Passo 2: Compilar projeto (clang-tidy roda durante build)
# ============================================================
log_info "Compilando projeto com clang-tidy..."
cmake --build "${BUILD_DIR}" \
    --target secure_lib \
    2>&1 | tee "${OUTPUT_DIR}/clang-tidy-output.txt" || true

# ============================================================
# Passo 3: Executar cppcheck separadamente
# ============================================================
log_info "Executando cppcheck..."
cppcheck --enable=all \
    --std=c++17 \
    --suppress=missingIncludeSystem \
    --inline-suppr \
    --project="${BUILD_DIR}/compile_commands.json" \
    --output-file="${OUTPUT_DIR}/cppcheck-report.txt" \
    --xml 2> "${OUTPUT_DIR}/cppcheck-report.xml" || true

# ============================================================
# Passo 4: Gerar relatorios SARIF
# ============================================================
log_info "Gerando relatorios SARIF..."
if [ -f "${BUILD_DIR}/clang-tidy-fixes.yaml" ]; then
    "${SOURCE_DIR}/scripts/generate-sarif.sh" \
        --clang-tidy="${BUILD_DIR}/clang-tidy-fixes.yaml" \
        --cppcheck="${OUTPUT_DIR}/cppcheck-report.xml" \
        --output="${OUTPUT_DIR}/combined.sarif" || true
fi

# ============================================================
# Passo 5: Verificar se ha erros
# ============================================================
log_info "Verificando resultados..."

ERRORS_FOUND=0

# Verificar clang-tidy
if [ -f "${BUILD_DIR}/clang-tidy-fixes.yaml" ]; then
    if grep -q "Fixes applied:" "${BUILD_DIR}/clang-tidy-fixes.yaml"; then
        log_warn "clang-tidy encontrou problemas"
        ERRORS_FOUND=1
    fi
fi

# Verificar cppcheck
if [ -f "${OUTPUT_DIR}/cppcheck-report.xml" ]; then
    if grep -q 'severity="error"' "${OUTPUT_DIR}/cppcheck-report.xml"; then
        log_warn "cppcheck encontrou erros"
        ERRORS_FOUND=1
    fi
fi

# ============================================================
# Passo 6: Gerar relatorio HTML
# ============================================================
log_info "Gerando relatorio HTML..."
"${SOURCE_DIR}/scripts/generate-reports.sh" \
    --input-dir="${OUTPUT_DIR}" \
    --output-dir="${OUTPUT_DIR}/html"

# ============================================================
# Resumo
# ============================================================
echo ""
echo "================================================"
echo "  ANALISE ESTATICA COMPLETA"
echo "================================================"
echo ""
echo "  Relatorios gerados em: ${OUTPUT_DIR}/"
echo ""
echo "  Arquivos:"
if [ -f "${OUTPUT_DIR}/combined.sarif" ]; then
    echo "    - combined.sarif (para GitHub)"
fi
if [ -f "${OUTPUT_DIR}/html/report.html" ]; then
    echo "    - html/report.html (relatorio visual)"
fi
echo ""

if [ ${ERRORS_FOUND} -eq 0 ]; then
    log_info "Nenhum erro critico encontrado!"
    exit 0
else
    log_error "Foram encontrados problemas. Verifique os relatorios."
    exit 1
fi
```

### 7.12.4 Script de Geracao de Relatorios

Script `scripts/generate-reports.sh`:

```bash
#!/bin/bash
set -euo pipefail

INPUT_DIR=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir) INPUT_DIR="$2"; shift 2 ;;
        --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
        *) shift ;;
    esac
done

mkdir -p "${OUTPUT_DIR}"

# Gerar relatorio HTML basico
cat > "${OUTPUT_DIR}/report.html" << 'HTMLHEAD'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Relatorio de Analise Estatica</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 { color: #2c3e50; }
        h2 { color: #34495e; border-bottom: 2px solid #3498db; }
        .summary { background: #ecf0f1; padding: 15px; border-radius: 5px; }
        .error { color: #e74c3c; font-weight: bold; }
        .warning { color: #f39c12; }
        .info { color: #3498db; }
        table { border-collapse: collapse; width: 100%; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #3498db; color: white; }
        tr:nth-child(even) { background: #f2f2f2; }
        .pass { background: #2ecc71; color: white; padding: 2px 8px; border-radius: 3px; }
        .fail { background: #e74c3c; color: white; padding: 2px 8px; border-radius: 3px; }
    </style>
</head>
<body>
<h1>Relatorio de Analise Estatica</h1>
HTMLHEAD

# Resumo
ERRORS=0
WARNINGS=0

if [ -f "${INPUT_DIR}/cppcheck-report.xml" ]; then
    ERRORS=$(grep -c 'severity="error"' "${INPUT_DIR}/cppcheck-report.xml" || true)
    WARNINGS=$(grep -c 'severity="warning"' "${INPUT_DIR}/cppcheck-report.xml" || true)
fi

cat >> "${OUTPUT_DIR}/report.html" << SUMMARY
<div class="summary">
    <h2>Resumo</h2>
    <p><strong>Erros:</strong> <span class="error">${ERRORS}</span></p>
    <p><strong>Avisos:</strong> <span class="warning">${WARNINGS}</span></p>
</div>
SUMMARY

# clang-tidy
cat >> "${OUTPUT_DIR}/report.html" << 'SECTION1'
<h2>clang-tidy</h2>
<table>
<tr><th>Arquivo</th><th>Linha</th><th>Check</th><th>Mensagem</th></tr>
SECTION1

if [ -f "${INPUT_DIR}/clang-tidy-output.txt" ]; then
    # Extrair linhas com problemas
    grep -E "(warning|error):" "${INPUT_DIR}/clang-tidy-output.txt" | \
    while IFS= read -r line; do
        if [[ $line =~ ^([^:]+):([0-9]+):[0-9]+:\ *(warning|error):\ (.+)\[([^]]+)\]$ ]]; then
            FILE="${BASH_REMATCH[1]}"
            LINE="${BASH_REMATCH[2]}"
            SEVERITY="${BASH_REMATCH[3]}"
            MSG="${BASH_REMATCH[4]}"
            CHECK="${BASH_REMATCH[5]}"
            CLASS="info"
            if [ "${SEVERITY}" = "error" ]; then
                CLASS="error"
            fi
            echo "<tr><td>${FILE}</td><td>${LINE}</td><td class=\"${CLASS}\">${CHECK}</td><td>${MSG}</td></tr>" >> "${OUTPUT_DIR}/report.html"
        fi
    done
else
    echo "<tr><td colspan='4'>Nenhum resultado encontrado</td></tr>" >> "${OUTPUT_DIR}/report.html"
fi

echo "</table>" >> "${OUTPUT_DIR}/report.html"

# cppcheck
cat >> "${OUTPUT_DIR}/report.html" << 'SECTION2'
<h2>cppcheck</h2>
<table>
<tr><th>Arquivo</th><th>Linha</th><th>Gravidade</th><th>ID</th><th>Mensagem</th></tr>
SECTION2

if [ -f "${INPUT_DIR}/cppcheck-report.txt" ]; then
    while IFS= read -r line; do
        if [[ $line =~ ^([^:]+):([0-9]+):\[(.*)\]\ (.+)$ ]]; then
            FILE="${BASH_REMATCH[1]}"
            LINE="${BASH_REMATCH[2]}"
            ID="${BASH_REMATCH[3]}"
            MSG="${BASH_REMATCH[4]}"
            SEVERITY="info"
            if [[ "${ID}" == *"error"* ]]; then
                SEVERITY="error"
            elif [[ "${ID}" == *"warning"* ]]; then
                SEVERITY="warning"
            fi
            echo "<tr><td>${FILE}</td><td>${LINE}</td><td class=\"${SEVERITY}\">${SEVERITY}</td><td>${ID}</td><td>${MSG}</td></tr>" >> "${OUTPUT_DIR}/report.html"
        fi
    done < "${INPUT_DIR}/cppcheck-report.txt"
else
    echo "<tr><td colspan='5'>Nenhum resultado encontrado</td></tr>" >> "${OUTPUT_DIR}/report.html"
fi

echo "</table>" >> "${OUTPUT_DIR}/report.html"

# Fechar HTML
cat >> "${OUTPUT_DIR}/report.html" << 'HTMLFOOT'
</body>
</html>
HTMLFOOT

echo "Relatorio gerado: ${OUTPUT_DIR}/report.html"
```

### 7.12.5 Workflow GitHub Actions

Workflow `.github/workflows/static-analysis.yml`:

```yaml
name: Static Analysis

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  static-analysis:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            clang-tidy \
            cppcheck \
            cmake \
            ninja-build
      
      - name: Configure CMake
        run: |
          cmake -B build \
            -G Ninja \
            -DCMAKE_BUILD_TYPE=Release \
            -DENABLE_STATIC_ANALYSIS=ON \
            -DENABLE_SECURITY_WARNINGS=ON \
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
      
      - name: Run clang-tidy
        run: |
          clang-tidy --format=sarif --output=clang-tidy.sarif \
            $(find src -name '*.cpp') \
            -- -std=c++17 -Iinclude \
               -I${{ github.workspace }}/build
      
      - name: Run cppcheck
        run: |
          cppcheck --xml --xml-version=2 \
            --enable=all --std=c++17 \
            --project=build/compile_commands.json \
            2> cppcheck.xml
      
      - name: Convert cppcheck to SARIF
        run: |
          python3 scripts/convert-cppcheck-to-sarif.sh \
            --input=cppcheck.xml \
            --output=cppcheck.sarif
      
      - name: Upload SARIF to GitHub
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: |
            clang-tidy.sarif
            cppcheck.sarif
          category: static-analysis
      
      - name: Upload analysis reports
        uses: actions/upload-artifact@v4
        with:
          name: static-analysis-reports
          path: |
            clang-tidy.sarif
            cppcheck.xml
            cppcheck.sarif
          retention-days: 30
```

---

## 7.13 Exercicios

### Exercicio 1: Configuracao clang-tidy

**Objetivo**: Configurar clang-tidy para um projeto existente.

**Instrucoes**:
1. Criar um arquivo `.clang-tidy` na raiz do projeto
2. Habilitar checks de bugprone, cert, e cppcoreguidelines
3. Configurar warnings-as-errors para checks criticos
4. Testar com um arquivo de exemplo que contenha bugs comuns

**Arquivo de teste** `src/test-bugs.cpp`:

```cpp
#include <iostream>
#include <memory>
#include <vector>

// Bug 1: null pointer dereference
void null_deref() {
    int* p = nullptr;
    std::cout << *p << std::endl;
}

// Bug 2: use after move
void use_after_move() {
    std::vector<int> v = {1, 2, 3};
    auto v2 = std::move(v);
    std::cout << v.size() << std::endl;
}

// Bug 3: uninitialized variable
void uninit_var() {
    int x;
    std::cout << x << std::endl;
}

int main() {
    null_deref();
    use_after_move();
    uninit_var();
    return 0;
}
```

**CMakeLists.txt**:

```cmake
cmake_minimum_required(VERSION 3.20)
project(Exercise1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(CMAKE_CXX_CLANG_TIDY
    clang-tidy
    --checks=-*,bugprone-*,cert-*,cppcoreguidelines-*
    --warnings-as-errors=*
)

add_executable(test-bugs src/test-bugs.cpp)
```

### Exercicio 2: Integracao cppcheck

**Objetivo**: Configurar cppcheck com supressoes customizadas.

**Instrucoes**:
1. Criar arquivo de supressoes para cppcheck
2. Configurar CMake para usar cppcheck
3. Criar target customizado para executar cppcheck
4. Gerar relatorio em XML

**Dica**: Use `CMAKE_CXX_CPPCHECK` ou crie um custom target.

### Exercicio 3: Pipeline SARIF

**Objetivo**: Configurar pipeline completa que gera SARIF para GitHub.

**Instrucoes**:
1. Configurar clang-tidy para gerar saida SARIF
2. Configurar cppcheck para gerar XML
3. Criar script para converter cppcheck XML para SARIF
4. Configurar GitHub Actions para upload de SARIF
5. Verificar que os findings aparecem em GitHub Code Scanning

### Exercicio 4: MISRA Compliance

**Objetivo**: Verificar compliance com regras MISRA C.

**Instrucoes**:
1. Instalar cppcheck com addon MISRA
2. Criar CMake option para habilitar verificacao MISRA
3. Criar target `misra-check` que executa a verificacao
4. Criar relatorio de compliance

**Dica**: Use o addon `cppcheck_addons/misra.json`.

### Exercicio 5: CWE Mapping

**Objetivo**: Criar script que mapeia findings para CWE.

**Instrucoes**:
1. Criar script Python que parseia saida do clang-tidy
2. Mapear check IDs para CWEs usando o dicionario fornecido
3. Gerar relatorio com contagem por CWE
4. Integrar com pipeline existente

### Exercicio 6: Fix Automaticos

**Objetivo**: Configurar clang-tidy para corrigir bugs automaticamente.

**Instrucoes**:
1. Criar arquivo com bugs comuns (use o do Exercicio 1)
2. Configurar CMake para rodar clang-tidy com `--fix`
3. Criar target que aplica fixes e gera diff
4. Criar target que reverte fixes (usando git)

### Exercicio 7: Analise Incremental

**Objetivo**: Criar sistema de analise que roda apenas em arquivos modificados.

**Instrucoes**:
1. Criar script que identifica arquivos modificados desde o ultimo commit
2. Rodar clang-tidy apenas nesses arquivos
3. Integrar com Git hooks (pre-commit)
4. Criar target CMake que executa a analise incremental

---

## 7.14 Referencias

### Documentacao Oficial

- [clang-tidy Documentation](https://clang.llvm.org/extra/clang-tidy/)
- [cppcheck Manual](http://cppcheck.net/manual.html)
- [Facebook Infer Documentation](https://infer.linux.do/)
- [CMake Documentation - CMAKE_CXX_CLANG_TIDY](https://cmake.org/cmake/help/latest/variable/CMAKE_CXX_CLANG_TIDY.html)
- [SARIF Specification](https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html)

### Padroes e Certificacoes

- [MISRA C:2012 Guidelines](https://www.misra.org.uk/)
- [MISRA C++:2023 Guidelines](https://www.misra.org.uk/)
- [CERT C Coding Standard](https://wiki.sei.cmu.edu/confluence/display/c)
- [CERT C++ Coding Standard](https://wiki.sei.cmu.edu/confluence/pages/viewpage.action?pageId=88046716)
- [CWE List](https://cwe.mitre.org/)

### Artigos e Livros

- [Static Analysis for C/C++ Developers](https://clang.llvm.org/docs/ClangStaticAnalysis.html)
- [Secure Coding in C and C++](https://www.owasp.org/index.php/Secure_Coding_Cheat_Sheet)
- [The CERT C Coding Standard, 2nd Edition](https://www.amazon.com/CERT-Coding-Standard-2nd-Edition/dp/0321985090)
- [Defensive Coding Guidelines for C](https://www.securecoding.cert.org/confluence/pages/viewpage.action?pageId=625)

### Ferramentas Adicionais

- [Clang Static Analyzer](https://clang-analyzer.llvm.org/)
- [PVS-Studio](https://pvs-studio.com/) (comercial)
- [Coverity](https://scan.coverity.com/) (gratuito para open-source)
- [SonarQube](https://www.sonarsource.com/) (versao comunitaria gratuita)
- [PC-lint](https://gimpel.com/) (comercial)

### Repositorios de Exemplo

- [llvm/llvm-project](https://github.com/llvm/llvm-project) - Exemplo de uso de clang-tidy
- [danmar/cppcheck](https://github.com/danmar/cppcheck) - Codigo-fonte do cppcheck
- [facebook/infer](https://github.com/facebook/infer) - Codigo-fonte do Infer

---

*[Proximo capitulo: 08 — Builds Reproduziveis](08-builds-reproduziveis.md)*

---

## 7.15 Exemplos Avancados

### 7.15.1 clang-tidy com Configuracoes Personalizadas por Diretorio

Em projetos grandes, e comum ter configuracoes diferentes para cada modulo:

```cmake
cmake_minimum_required(VERSION 3.20)
project(BigProject LANGUAGES CXX)

# Configuracao global padrao
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Bibliotecas core - rigor total
add_library(core STATIC src/core/core.cpp)
set_target_properties(core PROPERTIES
    CXX_CLANG_TIDY "clang-tidy;--checks=-*,cert-*,cppcoreguidelines-*;--warnings-as-errors=*"
)

# Modulo de seguranca - checks extras
add_library(security STATIC src/security/crypto.cpp)
target_include_directories(security PUBLIC include)
set_target_properties(security PROPERTIES
    CXX_CLANG_TIDY "clang-tidy;--checks=-*,bugprone-*,cert-*,security-*;--warnings-as-errors=*"
)

# Modulo legado - menos restritivo
add_library(legacy STATIC src/legacy/compat.cpp)
set_target_properties(legacy PROPERTIES
    CXX_CLANG_TIDY "clang-tidy;--checks=-*,modernize-*;--warnings-as-errors=-*"
)

# Testes - sem erros, apenas avisos
add_executable(tests tests/main.cpp)
target_link_libraries(tests PRIVATE core security)
set_target_properties(tests PROPERTIES
    CXX_CLANG_TIDY "clang-tidy;--checks=-*,bugprone-*,cert-*;--warnings-as-errors=-*"
)
```

### 7.15.2 cppcheck com Supressoes de Projeto

Para projetos com codigo legado ou dependencias de terceiros:

```cmake
cmake_minimum_required(VERSION 3.20)
project(LegacyProject LANGUAGES CXX)

# Configuracao cppcheck com supressoes
find_program(CPPCHECK_EXE cppcheck)
if(CPPCHECK_EXE)
    set(CMAKE_CXX_CPPCHECK
        ${CPPCHECK_EXE}
        --enable=all
        --std=c++17
        --suppress=missingIncludeSystem
        --suppress=unusedFunction
        --suppress=uninitvar
        --inline-suppr
        --project=${CMAKE_BINARY_DIR}/compile_commands.json
    )
endif()

# Biblioteca principal
add_library(mylib src/mylib.cpp)

# Codigo legado - supressoes adicionais
add_library(legacy STATIC src/legacy/old_code.cpp)
set_source_files_properties(src/legacy/old_code.cpp
    PROPERTIES
    COMPILE_FLAGS "-w"
)

# Vendor code - desabilitar completamente
add_library(vendor STATIC vendor/third_party/vendor.cpp)
set_source_files_properties(vendor/third_party/vendor.cpp
    PROPERTIES
    COMPILE_FLAGS "-w"
)
```

### 7.15.3 Analise com Diferentes Niveis de Severidade

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecurityProject LANGUAGES CXX)

# Nivel 1: Apenas erros criticos (default)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Werror")

# Nivel 2: Warnings adicionais
option(LEVEL2_WARNINGS "Enable level 2 warnings" OFF)
if(LEVEL2_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wextra -Wpedantic")
endif()

# Nivel 3: Warnings de seguranca
option(LEVEL3_WARNINGS "Enable security warnings" OFF)
if(LEVEL3_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
        -Wformat=2 \
        -Wformat-security \
        -Wformat-nonliteral \
        -Wconversion \
        -Wsign-conversion \
        -Wnull-dereference"
    )
endif()

# Nivel 4: Todos os warnings (para CI)
option(LEVEL4_WARNINGS "Enable all warnings" OFF)
if(LEVEL4_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} \
        -Weverything \
        -Wno-c++98-compat \
        -Wno-c++98-compat-pedantic \
        -Wno-padded"
    )
endif()

add_executable(myapp src/main.cpp)
```

### 7.15.4 Integracao com Build System Existente

Para projetos que nao usam CMake, podemos usar compile_commands.json:

```bash
# Gerar compile_commands.json com outro build system
# Para Makefile:
bear -- make

# Para Ninja:
ninja -t compdb > compile_commands.json

# Para Meson:
ninja -t compdb > compile_commands.json

# Usar com clang-tidy
clang-tidy --p=build/ src/*.cpp

# Usar com cppcheck
cppcheck --project=compile_commands.json --enable=all
```

### 7.15.5 Relatorios de Tendencia

Script para monitorar qualidade ao longo do tempo:

```bash
#!/bin/bash
set -euo pipefail

# Historico de findings
HISTORY_FILE="analysis-history.csv"

# Executar analise
cppcheck --enable=all --std=c++17 --xml \
    src/ 2> current-analysis.xml

# Contar findings por severidade
ERRORS=$(grep -c 'severity="error"' current-analysis.xml || true)
WARNINGS=$(grep -c 'severity="warning"' current-analysis.xml || true)
STYLE=$(grep -c 'severity="style"' current-analysis.xml || true)

# Adicionar ao historico
echo "$(date -Iseconds),${ERRORS},${WARNINGS},${STYLE}" >> ${HISTORY_FILE}

# Verificar regressao
if [ -f "${HISTORY_FILE}" ]; then
    PREV_ERRORS=$(tail -1 ${HISTORY_FILE} | cut -d',' -f2 || echo 0)
    
    if [ ${ERRORS} -gt ${PREV_ERRORS} ]; then
        echo "ALERTA: Aumento de erros (${PREV_ERRORS} -> ${ERRORS})"
        exit 1
    fi
fi

echo "Analise concluida: ${ERRORS} erros, ${WARNINGS} avisos, ${STYLE} estilo"
```

### 7.15.6 clang-tidy com Export de Correcoes

```cmake
cmake_minimum_required(VERSION 3.20)
project(AutoFixProject LANGUAGES CXX)

# Configurar para gerar correcoes
set(CMAKE_CXX_CLANG_TIDY
    clang-tidy
    --fix
    --fix-errors
    --config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
    --export-fixes=${CMAKE_BINARY_DIR}/fixes.yaml
)

add_executable(myapp src/main.cpp)
```

Para aplicar as correcoes:

```bash
# Build normal (clang-tidy roda e gera fixes)
cmake --build build

# Reverter mudancas indesejadas
git checkout -- src/

# Aplicar apenas fixes aprovados
clang-apply-replacements --style=file build/

# Ou usar yaml para revisar manualmente
cat build/fixes.yaml
```

### 7.15.7 Analise de Dependencias

clang-tidy pode analisar headers incluidos:

```cmake
cmake_minimum_required(VERSION 3.20)
project(WithDependencies LANGUAGES CXX)

# Configurar header filter para analisar apenas headers do projeto
set(CMAKE_CXX_CLANG_TIDY
    clang-tidy
    --header-filter='^${CMAKE_SOURCE_DIR}/include/.*'
    --checks=-*,bugprone-*
)

add_library(mylib src/mylib.cpp)
target_include_directories(mylib PUBLIC include)
```

### 7.15.8 clang-tidy com Formatacao

Integracao com clang-format para manter consistencia:

```yaml
# .clang-tidy
---
Checks: >
  -*,
  bugprone-*,
  cert-*,
  modernize-*,
  readability-*

FormatStyle: file  # Usa .clang-format

# .clang-format
---
BasedOnStyle: Google
IndentWidth: 4
ColumnLimit: 100
```

```bash
# Verificar formatacao
clang-format --dry-run --Werror src/*.cpp

# Aplicar formatacao
clang-format -i src/*.cpp
```

### 7.15.9 Multi-Plataforma

```cmake
cmake_minimum_required(VERSION 3.20)
project(MultiPlatform LANGUAGES CXX)

# Configuracao especifica por compilador
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -Werror")
elseif(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Weverything -Wno-c++98-compat -Werror")
elseif(CMAKE_CXX_COMPILER_ID MATCHES "MSVC")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4 /WX")
endif()

# clang-tidy funciona em todas as plataformas
find_program(CLANG_TIDY_EXE clang-tidy)
if(CLANG_TIDY_EXE)
    set(CMAKE_CXX_CLANG_TIDY
        ${CLANG_TIDY_EXE}
        --checks=-*,bugprone-*,cert-*
        --warnings-as-errors=*
    )
endif()

# cppcheck funciona em todas as plataformas
find_program(CPPCHECK_EXE cppcheck)
if(CPPCHECK_EXE)
    set(CMAKE_CXX_CPPCHECK
        ${CPPCHECK_EXE}
        --enable=all
        --std=c++17
        --suppress=missingIncludeSystem
    )
endif()

add_executable(myapp src/main.cpp)
```

---

## 7.16 Anti-Patterns Comuns

### 7.16.1 Desabilitar Todos os Warnings

**Errado**:
```cmake
# NUNCA faca isso!
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -w")
```

**Certo**:
```cmake
# Desabilitar apenas para vendored code
set_source_files_properties(vendor/*.cpp PROPERTIES COMPILE_FLAGS "-w")

# Ou usar isystem para includes
target_include_directories(mylib SYSTEM PRIVATE vendor/include)
```

### 7.16.2 Ignorar Erros de Analise

**Errado**:
```bash
# NUNCA faca isso em producao!
clang-tidy src/*.cpp || true
cppcheck src/ || true
```

**Certo**:
```bash
# Capturar e tratar erros adequadamente
if ! clang-tidy src/*.cpp; then
    echo "clang-tidy encontrou problemas"
    exit 1
fi
```

### 7.16.3 Nao Usar compile_commands.json

**Errado**:
```bash
# Analise imprecisa sem informacao de compilacao
clang-tidy src/main.cpp
cppcheck src/
```

**Certo**:
```bash
# Gerar compile_commands.json
cmake -B build -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

# Usar com -p para precisao
clang-tidy --p=build/ src/*.cpp
cppcheck --project=build/compile_commands.json
```

### 7.16.4 Analise Apenas em CI

**Errado**:
```yaml
# Analise apenas no CI causa feedback lento
- name: Analyze
  run: cmake --build build --target static-analysis
```

**Certo**:
```yaml
# Analise local e no CI
steps:
  - name: Local analysis
    run: cmake --build build --target static-analysis
  
  - name: CI analysis
    run: cmake --build build --target full-analysis
```

### 7.16.5 Nao Revisar Fixes Automaticos

**Errado**:
```bash
# Aplicar fixes sem revisao
clang-tidy src/*.cpp --fix
git add -A
git commit -m "auto-fix"
```

**Certo**:
```bash
# Gerar fixes para revisao
clang-tidy src/*.cpp --export-fixes=fixes.yaml

# Revisar antes de aplicar
cat fixes.yaml

# Aplicar se aprovado
clang-apply-replacements --style=file build/
```

---

## 7.17 Metricas de Qualidade

### 7.17.1 Metricas de Analise Estatica

```python
#!/usr/bin/env python3
"""Calcular metricas de analise estatica."""
import json
import xml.etree.ElementTree as ET
from typing import Dict, List

def calculate_metrics(sarif_file: str) -> Dict:
    """Calcular metricas de um arquivo SARIF."""
    with open(sarif_file, 'r') as f:
        sarif = json.load(f)
    
    metrics = {
        "total_findings": 0,
        "by_severity": {"error": 0, "warning": 0, "note": 0},
        "by_cwe": {},
        "by_tool": {},
    }
    
    for run in sarif.get("runs", []):
        tool_name = run.get("tool", {}).get("driver", {}).get("name", "unknown")
        
        if tool_name not in metrics["by_tool"]:
            metrics["by_tool"][tool_name] = 0
        
        for result in run.get("results", []):
            metrics["total_findings"] += 1
            metrics["by_tool"][tool_name] += 1
            
            level = result.get("level", "note")
            metrics["by_severity"][level] += 1
            
            rule_id = result.get("ruleId", "unknown")
            if rule_id not in metrics["by_cwe"]:
                metrics["by_cwe"][rule_id] = 0
            metrics["by_cwe"][rule_id] += 1
    
    return metrics

def calculate_quality_score(metrics: Dict) -> float:
    """Calcular score de qualidade (0-100)."""
    if metrics["total_findings"] == 0:
        return 100.0
    
    # Penalidade por severidade
    error_penalty = metrics["by_severity"]["error"] * 10
    warning_penalty = metrics["by_severity"]["warning"] * 2
    note_penalty = metrics["by_severity"]["note"] * 0.5
    
    total_penalty = error_penalty + warning_penalty + note_penalty
    
    # Score baseado em penalidade
    score = max(0, 100 - total_penalty)
    
    return round(score, 2)

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: quality-metrics.py <sarif-file>")
        sys.exit(1)
    
    sarif_file = sys.argv[1]
    metrics = calculate_metrics(sarif_file)
    score = calculate_quality_score(metrics)
    
    print(f"\nMetricas de Qualidade")
    print("=" * 50)
    print(f"Score: {score}/100")
    print(f"\nTotal de findings: {metrics['total_findings']}")
    print(f"\nPor severidade:")
    for sev, count in metrics["by_severity"].items():
        print(f"  {sev}: {count}")
    print(f"\nPor ferramenta:")
    for tool, count in metrics["by_tool"].items():
        print(f"  {tool}: {count}")

if __name__ == "__main__":
    main()
```

### 7.17.2 Dashboard de Qualidade

```cmake
cmake_minimum_required(VERSION 3.20)
project(QualityDashboard LANGUAGES CXX)

# Target para metricas
add_custom_target(quality-metrics
    COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/quality-metrics.py
        --input=${CMAKE_BINARY_DIR}/combined.sarif
        --output=${CMAKE_BINARY_DIR}/quality-report.json
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Calculating quality metrics"
    VERBATIM
)

# Target para dashboard HTML
add_custom_target(quality-dashboard
    COMMAND python3 ${CMAKE_SOURCE_DIR}/scripts/generate-dashboard.py
        --metrics=${CMAKE_BINARY_DIR}/quality-report.json
        --output=${CMAKE_BINARY_DIR}/dashboard.html
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
    COMMENT "Generating quality dashboard"
    VERBATIM
    DEPENDS quality-metrics
)
```

Script `scripts/generate-dashboard.py`:

```python
#!/usr/bin/env python3
"""Gerar dashboard HTML de metricas de qualidade."""
import json
import sys

def generate_dashboard(metrics_file: str, output_file: str):
    """Gerar dashboard HTML."""
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Dashboard de Qualidade</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric {{
            display: inline-block;
            text-align: center;
            padding: 20px;
            margin: 10px;
            min-width: 150px;
        }}
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            color: #333;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .error {{ color: #e74c3c; }}
        .warning {{ color: #f39c12; }}
        .info {{ color: #3498db; }}
        .success {{ color: #2ecc71; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f2f2f2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Dashboard de Qualidade - Analise Estatica</h1>
        
        <div class="card">
            <h2>Resumo</h2>
            <div class="metric">
                <div class="metric-value">{metrics.get('score', 0)}</div>
                <div class="metric-label">Score de Qualidade</div>
            </div>
            <div class="metric">
                <div class="metric-value">{metrics.get('total_findings', 0)}</div>
                <div class="metric-label">Total de Findings</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Por Severidade</h2>
            <table>
                <tr><th>Severidade</th><th>Quantidade</th></tr>
"""
    
    for severity, count in metrics.get('by_severity', {}).items():
        html += f'                <tr><td class="{severity}">{severity}</td><td>{count}</td></tr>\n'
    
    html += """            </table>
        </div>
        
        <div class="card">
            <h2>Por Ferramenta</h2>
            <table>
                <tr><th>Ferramenta</th><th>Findings</th></tr>
"""
    
    for tool, count in metrics.get('by_tool', {}).items():
        html += f'                <tr><td>{tool}</td><td>{count}</td></tr>\n'
    
    html += """            </table>
        </div>
    </div>
</body>
</html>"""
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Dashboard gerado: {output_file}")

def main():
    if len(sys.argv) < 3:
        print("Usage: generate-dashboard.py <metrics.json> <output.html>")
        sys.exit(1)
    
    metrics_file = sys.argv[1]
    output_file = sys.argv[2]
    
    generate_dashboard(metrics_file, output_file)

if __name__ == "__main__":
    main()
```

---

## 7.18 Checklist de Implementacao

Use este checklist ao implementar analise estatica no seu projeto:

### Configuracao Basica

- [ ] clang-tidy configurado com `.clang-tidy`
- [ ] cppcheck configurado com supressoes
- [ ] compile_commands.json gerado automaticamente
- [ ] Warnings habilitados (-Wall -Wextra -Wpedantic)

### Seguranca

- [ ] Checks de bugprone habilitados
- [ ] Checks de cert habilitados
- [ ] warnings-as-errors ativo para erros criticos
- [ ] Security warnings habilitados (-Wformat-security, etc.)

### CI/CD

- [ ] Analise roda em todo pull request
- [ ] SARIF gerado e upload para GitHub
- [ ] Fail build se houver erros
- [ ] Relatorios gerados como artifacts

### Manutencao

- [ ] Equipe treinada para interpretar resultados
- [ ] Processo para desabilitar warnings (com justificativa)
- [ ] Revisao periodica de supressoes
- [ ] Monitoramento de tendencia de qualidade

### Excecoes

- [ ] Codigo legado com supressoes documentadas
- [ ] Vendor code com analise desabilitada
- [ ] Testes com regras menos restritivas

---

## 7.19 Resumo do Capitulo

Este capitulo cobriu as principais ferramentas e tecnicas de analise estatica para projetos C/C++ usando CMake:

### Pontos-Chave

1. **clang-tidy** e a ferramenta principal para analise estatica em C++, com centenas de checks e suporte a fixes automaticos

2. **cppcheck** e uma alternativa leve que faz analise sem compilar o codigo, util para verificações rápidas

3. **Facebook Infer** oferece analise profunda inter-procedural, ideal para encontrar bugs complexos de memoria e concorrencia

4. **CMake** tem suporte nativo a clang-tidy e cppcheck via `CMAKE_CXX_CLANG_TIDY` e `CMAKE_CXX_CPPCHECK`

5. **Targets customizados** permitem flexibilidade na configuracao da analise

6. **SARIF** e o formato padrao para integrar com GitHub Code Scanning

7. **Warnings como erros** sao obrigatorios em projetos de seguranca

8. **MISRA** e **CERT** definem padroes de codificacao segura

9. **CWE mapping** permite correlacionar findings com vulnerabilidades conhecidas

### Proximo Passo

No proximo capitulo, veremos como construir **builds reproduziveis** - um requisito essencial para verificacao de integridade e auditoria de seguranca.

---

*[Proximo capitulo: 08 — Builds Reproduziveis](08-builds-reproduziveis.md)*
