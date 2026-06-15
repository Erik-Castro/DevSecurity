---
layout: default
title: "09-finding-packages"
---

# Capitulo 9 — Finding Packages Seguro

> *"A confianca em um pacote externo e uma decisao de seguranca, nao uma questao de conveniencia."*

---

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

- Entender os dois modos de `find_package()`: Basic e Config
- Diferenciar find modules de config files e seus impactos de seguranca
- Configurar `CMAKE_PREFIX_PATH` de forma segura
- Usar IMPORTED targets e propagar dependencias corretamente
- Utilizar funcoes auxiliares como `find_library`, `find_path` e `find_program`
- Integrar pkg-config com `CMakePkgConfig` de forma segura
- Aplicar restricoes de versao em `find_package()`
- Gerenciar componentes com `COMPONENTS`
- Configurar `CMAKE_FIND_PACKAGE_PREFER_CONFIG`
- Identificar e mitigar riscos de seguranca como path injection e typosquatting
- Validar packages encontrados antes de usa-los
- Implementar um `find_package(OpenSSL)` seguro e auditavel

---

## 9.1 find_package(): Modos Basic e Config

O `find_package()` e a funcao principal do CMake para localizar dependencias externas. Entender seus dois modos de operacao e fundamental para configuracoes seguras.

### 9.1.1 Modo Basic

O modo Basic e o modo padrao quando nenhuma opcao e especificada. O CMake busca por **find modules** em diretorios padrao do sistema.

```cmake
find_package(ZLIB)
```

Quando voce chama `find_package(ZLIB)` sem opcoes adicionais, o CMake:

1. Procura por `FindZLIB.cmake` em diretorios de modulo
2. Se nao encontrar, tenta o modo Config
3. Define variaveis como `ZLIB_FOUND`, `ZLIB_VERSION_STRING`, etc.

```cmake
# Exemplo basico de uso
find_package(ZLIB REQUIRED)

if(ZLIB_FOUND)
    message(STATUS "ZLIB version: ${ZLIB_VERSION_STRING}")
    target_link_libraries(myapp PRIVATE ZLIB::ZLIB)
endif()
```

**Fluxo de busca do modo Basic:**

1. `<PackageName>_ROOT` (CMake 3.12+)
2. `CMAKE_PREFIX_PATH`
3. `CMAKE_FRAMEWORK_PATH` e `CMAKE_APPBUNDLE_PATH`
4. `PATH` do sistema
5. Diretorios padrao do CMake

### 9.1.2 Modo Config

O modo Config e ativado explicitamente ou quando o CMake encontra um arquivo de configuração.

```cmake
find_package(ZLIB CONFIG)
# ou
find_package(ZLIB CONFIG REQUIRED)
```

No modo Config, o CMake procura por:

- `<PackageName>Config.cmake`
- `<lowercase-package-name>-config.cmake`
- `<PackageName>ConfigVersion.cmake`

```cmake
# Exemplo com CONFIG explícito
find_package(fmt CONFIG REQUIRED)

if(fmt_FOUND)
    target_link_libraries(myapp PRIVATE fmt::fmt)
endif()
```

**Diferencas Basic vs Config:**

| Aspecto | Basic | Config |
|---------|-------|--------|
| Procura por | Find modules | Config files |
| Localizacao | Module path | Prefix directories |
| Versao | Opcional | Comum |
| Flexibilidade | Limitada ao modulo | Completa |
| Seguranca | Depende do modulo | Depende do config file |

### 9.1.3 Modo Exato

O modo exato e uma restricao que so aceita Config files.

```cmake
find_package(ZLIB EXACT CONFIG 1.2.13)
```

Esta forma e a mais restritiva e segura:

- `EXACT`: A versao deve ser exatamente a especificada
- `CONFIG`: Forca o modo Config
- Versao especificada explicitamente

### 9.1.4 Controle de Obrigatoriedade

O `REQUIRED` faz o CMake falhar se o pacote nao for encontrado.

```cmake
# Faz o build falhar se OpenSSL nao estiver disponivel
find_package(OpenSSL REQUIRED)

# Permite construcao parcial se OpenSSL nao for encontrado
find_package(OpenSSL QUIET)

# Combinacao de opcoes
find_package(OpenSSL 3.0.0 REQUIRED)
```

**Melhor pratica de seguranca:** Sempre use `REQUIRED` para dependencias criticas de seguranca. Um pacote ausente que deveria ser obrigatorio pode levar a build incompleta com funcoes de seguranca desabilitadas.

### 9.1.5 Modo MODULE

O modo MODULE forca a busca apenas por find modules.

```cmake
find_package(ZLIB MODULE)
```

Isso garante que apenas `FindZLIB.cmake` seja usado, ignorando qualquer config file.

---

## 9.2 Find Modules vs Config Files

A distincao entre find modules e config files e critica para seguranca.

### 9.2.1 Find Modules

Find modules (`Find<Package>.cmake`) sao scripts写rios escritos pela comunidade ou pelo CMake. Eles contem logica para localizar bibliotecas e headers.

```cmake
# Estrutura tipica de um Find module
# FindZLIB.cmake

find_path(ZLIB_INCLUDE_DIR
    NAMES zlib.h
    PATHS
        /usr/include
        /usr/local/include
        /opt/zlib/include
)

find_library(ZLIB_LIBRARY
    NAMES z zlib
    PATHS
        /usr/lib
        /usr/local/lib
        /opt/zlib/lib
)

# Definir target IMPORTED
if(ZLIB_FOUND AND NOT TARGET ZLIB::ZLIB)
    add_library(ZLIB::ZLIB UNKNOWN IMPORTED)
    set_target_properties(ZLIB::ZLIB PROPERTIES
        IMPORTED_LOCATION "${ZLIB_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${ZLIB_INCLUDE_DIR}"
    )
endif()
```

**Riscos de Find Modules:**

1. **Caminhos fixos**: Podem ser manipulados por atacantes
2. **Scripts nao verificados**: Pode conter codigo malicioso
3. **Versoes nao controladas**: Podem encontrar versoes antigas/vulneraveis
4. **Falta de validacao**: Nao verificam integridade

### 9.2.2 Config Files

Config files sao gerados pelo proprio pacote (ou pelo gerenciador de pacotes) durante a instalacao.

```cmake
# Exemplo de config file gerado por uma library
# zlib-config.cmake

@PACKAGE_INIT@

include(CMakeFindDependencyMacro)

# Definir targets IMPORTED
add_library(ZLIB::ZLIB SHARED IMPORTED)

set_target_properties(ZLIB::ZLIB PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "${PACKAGE_PREFIX_DIR}/include"
    IMPORTED_LOCATION "${PACKAGE_PREFIX_DIR}/lib/libz.so"
    VERSION "1.2.13"
)
```

**Vantagens de Config Files:**

1. **Gerados pelo pacote**: Mais confiaveis que find modules genericos
2. **Contem metadados completos**: Versao, dependencias, opcoes de compilacao
3. **Suporte a versoes**: ConfigVersion.cmake valida compatibilidade
4. **IMPORTED targets**: Targets bem definidos com todas as propriedades

### 9.2.3 Comparacao de Seguranca

| Aspecto | Find Modules | Config Files |
|---------|--------------|--------------|
| Origem | Comunidade/CMake | Proprio pacote |
| Verificacao | Manual | ConfigVersion automatica |
| Metadados | Parcial | Completo |
| Targets | Opcional (IMPORTED) | Obrigatorio |
| Risco | Alto (caminhos fixos) | Baixo (controlado pelo pacote) |
| Recomendacao | Ultimo recurso | Preferido |

---

## 9.3 CMAKE_PREFIX_PATH e Seguranca

O `CMAKE_PREFIX_PATH` e um dos vetores de ataque mais comuns em build systems.

### 9.3.1 Como Funciona

```cmake
# Definir prefixo de busca
list(APPEND CMAKE_PREFIX_PATH "/opt/mylibs")
find_package(MyLib)
```

O CMake procura por:
- `/opt/mylibs/lib/cmake/MyLib/MyLibConfig.cmake`
- `/opt/mylibs/lib64/cmake/MyLib/MyLibConfig.cmake`

### 9.3.2 Vetores de Ataque

**Ataque por Path Injection:**

```bash
# Atacante adiciona diretorio malicioso
export CMAKE_PREFIX_PATH="/malicious/path:$CMAKE_PREFIX_PATH"

# CMake encontra pacote falso
cmake ..  # Usa pacote malicioso em vez do legitimo
```

**Ataque por Sobrescrita:**

```bash
# Atacante cria diretorio com nome de pacote
mkdir -p /tmp/fake_zlib/lib/cmake/ZLIB/
cat > /tmp/fake_zlib/lib/cmake/ZLIB/ZLIBConfig.cmake << 'EOF'
# Config file malicioso
add_library(ZLIB::ZLIB SHARED IMPORTED)
set_target_properties(ZLIB::ZLIB PROPERTIES
    IMPORTED_LOCATION "/tmp/fake_zlib/lib/libz.so"
)
EOF

# Se CMAKE_PREFIX_PATH inclui /tmp, o pacote falso sera encontrado
```

### 9.3.3 Mitigacoes

**1. Restringir CMAKE_PREFIX_PATH:**

```cmake
# Nao adicionar diretorios nao confiaveis
# RUIM:
list(APPEND CMAKE_PREFIX_PATH "$ENV{HOME}/.local")

# MELHOR: Usar caminho absoluto e verificado
set(MY_LIB_PATH "/opt/trusted/lib")
if(EXISTS "${MY_LIB_PATH}")
    list(APPEND CMAKE_PREFIX_PATH "${MY_LIB_PATH}")
endif()
```

**2. Usar <PackageName>_ROOT:**

```cmake
# CMake 3.12+: usar <PackageName>_ROOT para isolamento
set(ZLIB_ROOT "/opt/zlib-1.2.13")
find_package(ZLIB)
```

**3. Desabilitar busca em diretorios perigosos:**

```cmake
# Nao usar diretorios do usuario em builds de producao
if(NOT DEFINED CMAKE_PREFIX_PATH)
    # Usar caminho padrao do sistema
    set(CMAKE_PREFIX_PATH "/usr;/usr/local")
endif()
```

**4. Verificar CMAKE_PREFIX_PATH em CI/CD:**

```yaml
# GitHub Actions
- name: Configure
  run: |
    # Limpar CMAKE_PREFIX_PATH de ambientes nao confiaveis
    unset CMAKE_PREFIX_PATH
    cmake -B build -DCMAKE_PREFIX_PATH=/usr
```

### 9.3.4 Validação de Prefixos

```cmake
# Funcao para validar prefixos antes de usar
function(validate_prefix prefix)
    # Verificar se o prefixo existe
    if(NOT EXISTS "${prefix}")
        message(WARNING "Prefixo nao existe: ${prefix}")
        return()
    endif()

    # Verificar se o diretorio e legivel
    if(NOT IS_READABLE "${prefix}")
        message(WARNING "Prefixo nao e legivel: ${prefix}")
        return()
    endif()

    # Verificar se nao e um symlink para local inesperado
    get_filename_component(real_path "${prefix}" REALPATH)
    if(NOT "${real_path}" STREQUAL "${prefix}")
        message(WARNING "Prefixo e symlink: ${prefix} -> ${real_path}")
    endif()
endfunction()

# Uso
validate_prefix("/opt/mylib")
```

---

## 9.4 IMPORTED Targets e Propagate

IMPORTED targets sao a forma moderna e segura de usar dependencias externas.

### 9.4.1 O que sao IMPORTED Targets

```cmake
# IMPORTED targets sao targets que representam bibliotecas externas
add_library(MyLib::MyLib IMPORTED)

set_target_properties(MyLib::MyLib PROPERTIES
    IMPORTED_LOCATION "/usr/lib/libmylib.so"
    INTERFACE_INCLUDE_DIRECTORIES "/usr/include/mylib"
    INTERFACE_COMPILE_DEFINITIONS "USE_MYLIB"
    INTERFACE_LINK_LIBRARIES "Threads::Threads"
)
```

### 9.4.2 Propagacao de Dependencias

Uma das vantagens dos IMPORTED targets e a propagacao automatica de dependencias.

```cmake
# MyLib depende de OpenSSL
add_library(MyLib::MyLib IMPORTED)

set_target_properties(MyLib::MyLib PROPERTIES
    IMPORTED_LOCATION "/usr/lib/libmylib.so"
    INTERFACE_LINK_LIBRARIES "OpenSSL::SSL;OpenSSL::Crypto"
)

# Quando meu app linka com MyLib, OpenSSL e automaticamente incluido
target_link_libraries(myapp PRIVATE MyLib::MyLib)
# Isso equivale a:
# target_link_libraries(myapp PRIVATE MyLib::MyLib OpenSSL::SSL OpenSSL::Crypto)
```

### 9.4.3 Seguranca na Propagacao

A propagacao automatica pode esconder dependencias inseguras.

```cmake
# Cuidado: dependencias transmistas podem nao ser verificadas
find_package(BoringLib REQUIRED)
target_link_libraries(myapp PRIVATE BoringLib::BoringLib)

# BoringLib pode ter dependencias perigosas que voce nao ver
# Verificar sempre:
get_target_property(deps BoringLib::BoringLib INTERFACE_LINK_LIBRARIES)
message(STATUS "Dependencias de BoringLib: ${deps}")
```

### 9.4.4 Boas Praticas para IMPORTED Targets

**1. Sempre usar alvos namespace:**

```cmake
# BOM: Namespace claro
target_link_libraries(myapp PRIVATE ZLIB::ZLIB)
target_link_libraries(myapp PRIVATE OpenSSL::SSL)

# RUIM: Sem namespace
target_link_libraries(myapp PRIVATE z)
target_link_libraries(myapp PRIVATE ssl)
```

**2. Verificar propriedades antes de usar:**

```cmake
# Verificar se o target existe antes de usar
if(TARGET ZLIB::ZLIB)
    target_link_libraries(myapp PRIVATE ZLIB::ZLIB)
else()
    message(FATAL_ERROR "Target ZLIB::ZLIB nao encontrado")
endif()
```

**3. Usar propriedades INTERFACE:**

```cmake
# IMPORTED targets devem definir INTERFACE properties
set_target_properties(MyLib::MyLib PROPERTIES
    INTERFACE_INCLUDE_DIRECTORIES "/usr/include/mylib"
    INTERFACE_COMPILE_DEFINITIONS "USE_MYLIB=1"
    INTERFACE_LINK_LIBRARIES "Threads::Threads"
)
```

### 9.4.5 Criando IMPORTED Targets Seguros

```cmake
# Funcao para criar IMPORTED target com validacao
function(create_safe_imported_target name)
    set(options "")
    set(oneValueArgs LOCATION INCLUDE_DIR)
    set(multiValueArgs DEPENDENCIES DEFINITIONS)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # Validar localizacao
    if(NOT EXISTS "${ARG_LOCATION}")
        message(FATAL_ERROR "Localizacao invalida: ${ARG_LOCATION}")
    endif()

    # Verificar se nao e um symlink para local inesperado
    get_filename_component(real_location "${ARG_LOCATION}" REALPATH)
    if(NOT "${real_location}" STREQUAL "${ARG_LOCATION}")
        message(WARNING "Localizacao e symlink: ${ARG_LOCATION}")
    endif()

    # Criar target
    add_library(${name} IMPORTED UNKNOWN)

    set_target_properties(${name} PROPERTIES
        IMPORTED_LOCATION "${ARG_LOCATION}"
    )

    # Adicionar include dir se fornecido
    if(ARG_INCLUDE_DIR)
        if(EXISTS "${ARG_INCLUDE_DIR}")
            set_target_properties(${name} PROPERTIES
                INTERFACE_INCLUDE_DIRECTORIES "${ARG_INCLUDE_DIR}"
            )
        endif()
    endif()

    # Adicionar definicoes
    if(ARG_DEFINITIONS)
        set_target_properties(${name} PROPERTIES
            INTERFACE_COMPILE_DEFINITIONS "${ARG_DEFINITIONS}"
        )
    endif()

    # Adicionar dependencias
    if(ARG_DEPENDENCIES)
        set_target_properties(${name} PROPERTIES
            INTERFACE_LINK_LIBRARIES "${ARG_DEPENDENCIES}"
        )
    endif()
endfunction()

# Uso
create_safe_imported_target(MyLib::MyLib
    LOCATION "/usr/lib/libmylib.so"
    INCLUDE_DIR "/usr/include/mylib"
    DEPENDENCIES "Threads::Threads;ZLIB::ZLIB"
    DEFINITIONS "USE_MYLIB=1"
)
```

---

## 9.5 find_library, find_path, find_program

Estas funcoes sao os blocos de construcao dos find modules e permitem controle fino da busca.

### 9.5.1 find_library

```cmake
# Buscar uma biblioteca
find_library(ZLIB_LIBRARY
    NAMES z zlib zlib1
    PATHS
        /usr/lib
        /usr/lib64
        /usr/local/lib
        /opt/zlib/lib
    PATH_SUFFIXES
        lib
        lib64
)

if(ZLIB_LIBRARY)
    message(STATUS "ZLIB library found: ${ZLIB_LIBRARY}")
else()
    message(FATAL_ERROR "ZLIB library not found")
endif()
```

**Seguranca em find_library:**

```cmake
# RUIM: Buscar em diretorios nao confiaveis
find_library(MYLIB
    NAMES mylib
    PATHS
        /tmp
        /var/tmp
        $ENV{HOME}/.local
)

# MELHOR: Apenas diretorios do sistema
find_library(MYLIB
    NAMES mylib
    PATHS
        /usr/lib
        /usr/lib64
        /usr/local/lib
    NO_DEFAULT_PATH
)
```

### 9.5.2 find_path

```cmake
# Buscar um header
find_path(ZLIB_INCLUDE_DIR
    NAMES zlib.h
    PATHS
        /usr/include
        /usr/local/include
        /opt/zlib/include
    PATH_SUFFIXES
        include
        include/zlib
)

if(ZLIB_INCLUDE_DIR)
    message(STATUS "ZLIB include found: ${ZLIB_INCLUDE_DIR}")
endif()
```

**Validacao de include path:**

```cmake
# Verificar se o header existe e e valido
find_path(ZLIB_INCLUDE_DIR NAMES zlib.h)

if(ZLIB_INCLUDE_DIR)
    # Verificar se o arquivo realmente existe
    if(NOT EXISTS "${ZLIB_INCLUDE_DIR}/zlib.h")
        message(WARNING "Header nao existe: ${ZLIB_INCLUDE_DIR}/zlib.h")
        unset(ZLIB_INCLUDE_DIR)
    endif()

    # Verificar se e um arquivo regular (nao symlink para local inesperado)
    get_filename_component(real_path "${ZLIB_INCLUDE_DIR}/zlib.h" REALPATH)
    if(NOT "${real_path}" MATCHES "^${ZLIB_INCLUDE_DIR}/")
        message(WARNING "Header e symlink: ${ZLIB_INCLUDE_DIR}/zlib.h -> ${real_path}")
    endif()
endif()
```

### 9.5.3 find_program

```cmake
# Buscar um programa
find_program(GIT_EXECUTABLE
    NAMES git
    PATHS
        /usr/bin
        /usr/local/bin
        /opt/git/bin
)

if(GIT_EXECUTABLE)
    message(STATUS "Git found: ${GIT_EXECUTABLE}")

    # Verificar se e executavel
    if(NOT IS_EXECUTABLE "${GIT_EXECUTABLE}")
        message(FATAL_ERROR "Git nao e executavel: ${GIT_EXECUTABLE}")
    endif()
endif()
```

**Seguranca em find_program:**

```cmake
# RUIM: Buscar em diretorios do usuario
find_program(NODE_EXECUTABLE
    NAMES node
    PATHS
        $ENV{HOME}/.nvm/versions/node
        /usr/local/bin
)

# MELHOR: Apenas diretorios do sistema
find_program(NODE_EXECUTABLE
    NAMES node
    PATHS
        /usr/bin
        /usr/local/bin
    NO_DEFAULT_PATH
)
```

### 9.5.4 Restringir Busca

```cmake
# Usar NO_DEFAULT_PATH para evitar busca em diretorios padrao
find_library(MYLIB
    NAMES mylib
    PATHS /opt/mylib/lib
    NO_DEFAULT_PATH
)

# Usar NO_CMAKE_FIND_ROOT_PATH para cross-compilation
find_library(MYLIB
    NAMES mylib
    PATHS /opt/mylib/lib
    NO_CMAKE_FIND_ROOT_PATH
)

# Usar CMAKE_FIND_ROOT_PATH_MODE_LIBRARY para controlar busca
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
# Agora find_library so busca dentro de CMAKE_FIND_ROOT_PATH
```

### 9.5.5 Funcao Auxiliar Segura

```cmake
# Funcao wrapper segura para find_library
function(safe_find_library var_name)
    set(options REQUIRED QUIET)
    set(oneValueArgs "")
    set(multiValueArgs NAMES PATHS)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # Validar nomes
    foreach(name IN LISTS ARG_NAMES)
        if(name MATCHES "[^a-zA-Z0-9_]")
            message(FATAL_ERROR "Nome de biblioteca invalido: ${name}")
        endif()
    endforeach()

    # Validar caminhos
    foreach(path IN LISTS ARG_PATHS)
        if(NOT EXISTS "${path}")
            message(WARNING "Caminho nao existe: ${path}")
        endif()
    endforeach()

    # Executar find_library com restricoes
    find_library(${var_name}
        NAMES ${ARG_NAMES}
        PATHS ${ARG_PATHS}
        NO_DEFAULT_PATH
    )

    # Verificar resultado
    if(NOT ${var_name})
        if(ARG_REQUIRED)
            message(FATAL_ERROR "Biblioteca nao encontrada: ${ARG_NAMES}")
        elseif(NOT ARG_QUIET)
            message(WARNING "Biblioteca nao encontrada: ${ARG_NAMES}")
        endif()
    else()
        # Validar caminho encontrado
        get_filename_component(real_path "${${var_name}}" REALPATH)
        if(NOT "${real_path}" MATCHES "^/(usr|opt)/")
            message(WARNING "Biblioteca em localizacao suspeita: ${${var_name}}")
        endif()
    endif()
endfunction()
```

---

## 9.6 pkg-config: CMakePkgConfig

O pkg-config e uma ferramenta padrao para gerenciar dependencias em sistemas Unix-like.

### 9.6.1 Integracao com CMake

```cmake
# Usar find_package para pkg-config
find_package(PkgConfig REQUIRED)

# Buscar pacote via pkg-config
pkg_check_modules(ZLIB REQUIRED IMPORTED_TARGET zlib)

# Usar target gerado
target_link_libraries(myapp PRIVATE PkgConfig::ZLIB)
```

### 9.6.2 Seguranca com pkg-config

**Riscos do pkg-config:**

```bash
# Atacante pode sobrescrever .pc files
export PKG_CONFIG_PATH="/malicious/path:$PKG_CONFIG_PATH"

# CMake pode encontrar pacotes falsos
```

**Mitigacoes:**

```cmake
# 1. Restringir PKG_CONFIG_PATH
set(ENV{PKG_CONFIG_PATH} "/usr/lib/pkgconfig:/usr/local/lib/pkgconfig")

# 2. Usar caminho especifico
pkg_check_modules(ZLIB
    IMPORTED_TARGET
    PATHS /usr/lib/pkgconfig /usr/local/lib/pkgconfig
    NO_DEFAULT_PATH
)

# 3. Validar versao
pkg_check_modules(ZLIB
    IMPORTED_TARGET
    "zlib>=1.2.13"
)
```

### 9.6.3 CMakePkgConfig vs find_package

| Aspecto | pkg-config | find_package |
|---------|------------|--------------|
| Config file | .pc files | Config.cmake |
| Versao | Sim | Sim |
| Targets | PkgConfig::X | X::X (customizado) |
| Seguranca | Depende do .pc | Depende do config |
| Recomendacao | Sistemas Unix | Qualquer sistema |

### 9.6.4 Configuracao Segura

```cmake
# Configuracao padrao segura para pkg-config
find_package(PkgConfig REQUIRED)

# Desabilitar busca em diretorios nao confiaveis
set(ENV{PKG_CONFIG_PATH} "")

# Definir caminhos explicitos
set(PKG_CONFIG_ARGN "--define-variable=prefix=/usr")

# Usar apenas diretorios conhecidos
pkg_check_modules(ZLIB
    IMPORTED_TARGET
    PATHS
        /usr/lib/x86_64-linux-gnu/pkgconfig
        /usr/lib64/pkgconfig
        /usr/local/lib/pkgconfig
    NO_DEFAULT_PATH
)
```

### 9.6.5 Verificacao de Integridade

```cmake
# Verificar integridade do pkg-config
function(verify_pkg_config_integrity module)
    # Verificar se o modulo existe
    if(NOT PKG_CONFIG_FOUND)
        message(FATAL_ERROR "pkg-config nao encontrado")
    endif()

    # Verificar versao do pkg-config
    if(PKG_CONFIG_VERSION_STRING VERSION_LESS "0.29")
        message(WARNING "pkg-config antigo, possivelmente vulneravel")
    endif()

    # Verificar se o modulo e confiavel
    execute_process(
        COMMAND ${PKG_CONFIG_EXECUTABLE} --variable=pcfiledir ${module}
        OUTPUT_VARIABLE pcfiledir
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )

    if(pcfiledir)
        # Verificar se o diretorio e confiavel
        if(NOT pcfiledir MATCHES "^/(usr|opt)/")
            message(WARNING "pcfile em localizacao suspeita: ${pcfiledir}")
        endif()
    endif()
endfunction()
```

---

## 9.7 Version Requirements: find_package(X 3.0 REQUIRED)

Restricoes de versao sao essenciais para seguranca e compatibilidade.

### 9.7.1 Sintaxe Basica

```cmake
# Versao minima
find_package(ZLIB 1.2.13 REQUIRED)

# Versao minima e maxima
find_package(Boost 1.70.0...1.80.0 REQUIRED)

# Versao exata
find_package(ZLIB 1.2.13 EXACT REQUIRED)
```

### 9.7.2 ConfigVersion.cmake

O arquivo `ConfigVersion.cmake` e responsavel por validar versoes.

```cmake
# Exemplo de ConfigVersion.cmake
set(PACKAGE_VERSION "1.2.13")

if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)
    set(PACKAGE_VERSION_COMPATIBLE FALSE)
else()
    set(PACKAGE_VERSION_COMPATIBLE TRUE)
    if(PACKAGE_VERSION VERSION_EQUAL PACKAGE_FIND_VERSION)
        set(PACKAGE_VERSION_EXACT TRUE)
    endif()
endif()
```

### 9.7.3 Controle de Compatibilidade

```cmake
# Configurar como CMake determina compatibilidade
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# Usar version range (CMake 3.19+)
find_package(Boost 1.70.0...<1.81.0 REQUIRED COMPONENTS system filesystem)

# Versao exata
find_package(ZLIB 1.2.13 EXACT REQUIRED)
```

### 9.7.4 Seguranca de Versao

**Por que restricoes de versao sao importantes:**

1. **Vulnerabilidades conhecidas**: Versoes antigas podem ter CVEs
2. **Mudancas de API**: Versoes diferentes podem ter comportamento diferente
3. **Reprodutibilidade**: Versoes fixas garantem builds reproduziveis

```cmake
# RUIM: Sem restricao de versao
find_package(OpenSSL)
# Pode encontrar qualquer versao, incluindo vulneravel

# MELHOR: Com restricao de versao
find_package(OpenSSL 3.0.0 REQUIRED)
# Garante versao minima segura

# MELHOR AINDA: Range de versoes
find_package(OpenSSL 3.0.0...<3.2.0 REQUIRED)
# Aceita apenas versoes suportadas
```

### 9.7.5 Verificacao de Versao

```cmake
# Verificar versao encontrada
find_package(ZLIB 1.2.13 REQUIRED)

if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL "1.2.13")
    message(FATAL_ERROR "ZLIB版本太旧: ${ZLIB_VERSION_STRING}")
endif()

# Verificar se a versao e conhecida
set(KNOWN_SAFE_VERSIONS "1.2.13" "1.2.14" "1.3.0")
if(NOT ZLIB_VERSION_STRING IN_LIST KNOWN_SAFE_VERSIONS)
    message(WARNING "ZLIB版本未知: ${ZLIB_VERSION_STRING}")
endif()
```

---

## 9.8 Component Support: find_package(X COMPONENTS a b)

Componentes permitem buscar partes especificas de um pacote.

### 9.8.1 Sintaxe Basica

```cmake
# Buscar componentes especificos
find_package(Boost REQUIRED COMPONENTS system filesystem)

# Componentes opcionais
find_package(Boost REQUIRED COMPONENTS system)
find_package(Boost OPTIONAL_COMPONENTS filesystem regex)
```

### 9.8.2 Seguranca com Componentes

```cmake
# Cuidado: componentes podem ter dependencias diferentes
find_package(Qt6 REQUIRED COMPONENTS Core Widgets)

# Verificar se todos os componentes foram encontrados
foreach(comp IN ITEMS Core Widgets)
    if(NOT Qt6${comp}_FOUND)
        message(FATAL_ERROR "Qt6 componente nao encontrado: ${comp}")
    endif()
endforeach()
```

### 9.8.3 Controle de Componentes

```cmake
# Definir quais componentes sao obrigatorios
set(REQUIRED_COMPONENTS system filesystem)
set(OPTIONAL_COMPONENTS regex timer)

# Buscar componentes obrigatorios
find_package(Boost REQUIRED COMPONENTS ${REQUIRED_COMPONENTS})

# Buscar componentes opcionais
find_package(Boost OPTIONAL_COMPONENTS ${OPTIONAL_COMPONENTS})

# Usar apenas componentes encontrados
set(BOOST_COMPONENTS ${REQUIRED_COMPONENTS})
foreach(comp IN LISTS OPTIONAL_COMPONENTS)
    if(Boost${comp}_FOUND)
        list(APPEND BOOST_COMPONENTS ${comp})
    endif()
endforeach()
```

### 9.8.4 Componentes e IMPORTED Targets

```cmake
# Componentes geram targets separados
find_package(Boost REQUIRED COMPONENTS system filesystem)

# Usar targets
target_link_libraries(myapp PRIVATE Boost::system Boost::filesystem)

# Verificar targets antes de usar
if(TARGET Boost::system)
    target_link_libraries(myapp PRIVATE Boost::system)
endif()
```

### 9.8.5 Validacao de Componentes

```cmake
# Funcao para validar componentes encontrados
function(validate_components package_name)
    set(options REQUIRED)
    set(oneValueArgs "")
    set(multiValueArgs COMPONENTS)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    foreach(comp IN LISTS ARG_COMPONENTS)
        # Verificar se o componente foi encontrado
        if(NOT ${package_name}${comp}_FOUND)
            if(ARG_REQUIRED)
                message(FATAL_ERROR "Componente obrigatorio nao encontrado: ${package_name}${comp}")
            else()
                message(WARNING "Componente opcional nao encontrado: ${package_name}${comp}")
            endif()
        endif()

        # Verificar se o target existe
        if(NOT TARGET ${package_name}::${comp})
            message(WARNING "Target nao encontrado: ${package_name}::${comp}")
        endif()
    endforeach()
endfunction()

# Uso
find_package(Boost REQUIRED COMPONENTS system filesystem)
validate_components(Boost
    REQUIRED
    COMPONENTS system filesystem
)
```

---

## 9.9 CMAKE_FIND_PACKAGE_PREFER_CONFIG

Esta variavel controla a preferencia entre Basic e Config modes.

### 9.9.1 Configuracao

```cmake
# Preferir Config files sobre find modules
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# Preferir find modules sobre Config files
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF)
```

### 9.9.2 Seguranca

```cmake
# Configuracao segura
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# Isso garante que:
# 1. Config files do proprio pacote sejam usados
# 2. Find modules genericos sejam evitados
# 3. Versoes e dependencias sejam melhor controladas
```

### 9.9.3 Controle por Pacote

```cmake
# Para pacotes especificos, forcar CONFIG
find_package(OpenSSL CONFIG REQUIRED)

# Para outros, usar preferencia global
find_package(ZLIB)
```

### 9.9.4 Comportamento por Padrao

```cmake
# Comportamento padrao do CMake:
# 1. Procura por Find<PackageName>.cmake
# 2. Se nao encontrar, procura por <PackageName>Config.cmake
# 3. A menos que CMAKE_FIND_PACKAGE_PREFER_CONFIG seja ON

# Configuracao recomendada para seguranca:
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)
find_package(OpenSSL 3.0.0 REQUIRED)
```

### 9.9.5 Heranca de Configuracao

```cmake
# CMAKE_FIND_PACKAGE_PREFER_CONFIG pode ser herdado
# de CMakeLists.txt pai

# Para subprojetos:
add_subdirectory(extern/mylib)

# mylib pode ter sua propria configuracao
```

---

## 9.10 Security Risks: Path Injection, Typosquatting

### 9.10.1 Path Injection

**Definicao:** Um atacante manipula caminhos de busca para que o CMake encontre pacotes maliciosos.

**Exemplo de Ataque:**

```bash
# 1. Criar pacote malicioso
mkdir -p /tmp/fake_openssl/lib/cmake/openssl/
cat > /tmp/fake_openssl/lib/cmake/openssl/openssl-config.cmake << 'EOF'
# Config file malicioso
add_library(OpenSSL::SSL SHARED IMPORTED)
set_target_properties(OpenSSL::SSL PROPERTIES
    IMPORTED_LOCATION "/tmp/fake_openssl/lib/libssl.so"
)
# Codigo malicioso executado durante build
execute_process(COMMAND ${CMAKE_COMMAND} -E env
    "LD_PRELOAD=/tmp/fake_openssl/lib/malicious.so"
    "true"
)
EOF

# 2. Injetar caminho
export CMAKE_PREFIX_PATH="/tmp/fake_openssl:$CMAKE_PREFIX_PATH"

# 3. Build normalmente
cmake ..  # Usa pacote malicioso
```

**Mitigacoes:**

```cmake
# 1. Validar CMAKE_PREFIX_PATH
if(DEFINED CMAKE_PREFIX_PATH)
    foreach(path IN LISTS CMAKE_PREFIX_PATH)
        if(NOT path MATCHES "^/(usr|opt)/")
            message(FATAL_ERROR "Caminho nao confiavel em CMAKE_PREFIX_PATH: ${path}")
        endif()
    endforeach()
endif()

# 2. Usar caminhos absolutos e verificados
set(OPENSSL_ROOT_DIR "/opt/openssl-3.0.0")
find_package(OpenSSL 3.0.0 REQUIRED)

# 3. Verificar integridade do pacote encontrado
if(EXISTS "${OPENSSL_SSL_LIBRARY}")
    # Verificar assinatura ou hash
    file(READ "${OPENSSL_SSL_LIBRARY}" content HEX LIMIT 16)
    if(NOT content STREQUAL "7f454c4602010103")
        message(FATAL_ERROR "Biblioteca OpenSSL corrompida ou adulterada")
    endif()
endif()
```

### 9.10.2 Typosquatting

**Definicao:** Um atacante cria pacotes com nomes similares a pacotes populares.

**Exemplo:**

```bash
# Pacote legitimo: OpenSSL
# Pacote malicioso: openSLL (com L maiusculo)
# Pacote malicioso: openssl2
# Pacote malicioso: openssl_
```

**Mitigacoes:**

```cmake
# 1. Usar nomes exatos
find_package(OpenSSL REQUIRED)
# Nao: find_package(openssl) ou find_package(OpenSSL2)

# 2. Verificar versao e origem
find_package(OpenSSL 3.0.0 REQUIRED)
if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL "3.0.0")
    message(FATAL_ERROR "Versao OpenSSL invalida")
endif()

# 3. Verificar caminho
if(NOT OPENSSL_SSL_LIBRARY MATCHES "^/(usr|opt)/")
    message(FATAL_ERROR "OpenSSL em localizacao suspeita")
endif()
```

### 9.10.3 Confusao de Nomes

```cmake
# Cuidado com nomes similares
find_package(CURL REQUIRED)   # libcurl
find_package(Curl REQUIRED)   # Pode ser diferente

# Verificar se e o pacote esperado
find_package(CURL REQUIRED)
if(NOT CURL_VERSION_STRING MATCHES "curl")
    message(FATAL_ERROR "Pacote CURL inesperado encontrado")
endif()
```

### 9.10.4 Ataque de Symlink

```bash
# Atacante cria symlink para pacote malicioso
ln -s /tmp/fake_openssl /usr/lib/openssl

# CMake pode seguir o symlink
find_package(OpenSSL)  # Encontra via symlink
```

**Mitigacao:**

```cmake
# Verificar se o caminho e um symlink
get_filename_component(real_path "${OPENSSL_SSL_LIBRARY}" REALPATH)
if(NOT "${real_path}" STREQUAL "${OPENSSL_SSL_LIBRARY}")
    message(WARNING "OpenSSL e um symlink: ${OPENSSL_SSL_LIBRARY}")
endif()
```

### 9.10.5 Resumo de Riscos

| Risco | Vetor de Ataque | Mitigacao |
|-------|-----------------|-----------|
| Path Injection | CMAKE_PREFIX_PATH | Validar caminhos |
| Typosquatting | Nomes similares | Usar nomes exatos |
| Confusao de Nomes | Nomes alternativos | Verificar versao |
| Symlink Attack | Symlinks | Verificar REALPATH |
| Version Confusion | Versoes antigas | Restricoes de versao |

---

## 9.11 Validacao de Packages Encontrados

Apos encontrar um pacote, e essencial valida-lo antes de usar.

### 9.11.1 Validacao Basica

```cmake
# Validar se o pacote foi encontrado
find_package(ZLIB REQUIRED)

if(NOT ZLIB_FOUND)
    message(FATAL_ERROR "ZLIB nao encontrado")
endif()

# Validar versao
if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL "1.2.13")
    message(FATAL_ERROR "ZLIB versao antiga: ${ZLIB_VERSION_STRING}")
endif()

# Validar caminhos
if(NOT EXISTS "${ZLIB_LIBRARY}")
    message(FATAL_ERROR "Biblioteca ZLIB nao existe: ${ZLIB_LIBRARY}")
endif()
```

### 9.11.2 Funcao de Validacao Completa

```cmake
# Funcao para validar pacote completo
function(validate_package package_name)
    set(options REQUIRED)
    set(oneValueArgs MIN_VERSION)
    set(multiValueArgs COMPONENTS)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # Verificar se o pacote foi encontrado
    if(NOT ${package_name}_FOUND)
        if(ARG_REQUIRED)
            message(FATAL_ERROR "Pacote obrigatorio nao encontrado: ${package_name}")
        else()
            message(WARNING "Pacote nao encontrado: ${package_name}")
            return()
        endif()
    endif()

    # Verificar versao minima
    if(ARG_MIN_VERSION)
        if(DEFINED ${package_name}_VERSION)
            if(${${package_name}_VERSION} VERSION_LESS ${ARG_MIN_VERSION})
                message(FATAL_ERROR
                    "Versao do ${package_name} muito antiga: "
                    "${${package_name}_VERSION} < ${ARG_MIN_VERSION}"
                )
            endif()
        endif()
    endif()

    # Verificar componentes
    foreach(comp IN LISTS ARG_COMPONENTS)
        if(NOT ${package_name}${comp}_FOUND)
            message(FATAL_ERROR "Componente nao encontrado: ${package_name}${comp}")
        endif()
    endforeach()

    # Verificar caminhos
    if(DEFINED ${package_name}_LIBRARY)
        if(NOT EXISTS "${${package_name}_LIBRARY}")
            message(FATAL_ERROR "Biblioteca nao existe: ${${package_name}_LIBRARY}")
        endif()
    endif()

    if(DEFINED ${package_name}_INCLUDE_DIR)
        if(NOT EXISTS "${${package_name}_INCLUDE_DIR}")
            message(FATAL_ERROR "Include dir nao existe: ${${package_name}_INCLUDE_DIR}")
        endif()
    endif()

    message(STATUS "Pacote ${package_name} validado com sucesso")
endfunction()

# Uso
find_package(ZLIB REQUIRED)
validate_package(ZLIB
    REQUIRED
    MIN_VERSION "1.2.13"
)
```

### 9.11.3 Verificacao de Integridade

```cmake
# Verificar integridade de uma biblioteca
function(verify_library_integrity library_path expected_hash)
    if(NOT EXISTS "${library_path}")
        message(FATAL_ERROR "Biblioteca nao existe: ${library_path}")
    endif()

    file(SHA256 "${library_path}" actual_hash)

    if(NOT "${actual_hash}" STREQUAL "${expected_hash}")
        message(FATAL_ERROR
            "Integridade da biblioteca verificada:\n"
            "  Arquivo: ${library_path}\n"
            "  Hash esperado: ${expected_hash}\n"
            "  Hash atual: ${actual_hash}"
        )
    endif()

    message(STATUS "Integridade verificada: ${library_path}")
endfunction()

# Uso
find_package(OpenSSL REQUIRED)
verify_library_integrity(
    "${OPENSSL_SSL_LIBRARY}"
    "abc123..."  # Hash SHA256 esperado
)
```

### 9.11.4 Verificacao de Permissoes

```cmake
# Verificar permissoes de arquivos
function(check_file_permissions file_path)
    if(NOT EXISTS "${file_path}")
        message(FATAL_ERROR "Arquivo nao existe: ${file_path}")
    endif()

    # Verificar se e executavel
    if(IS_EXECUTABLE "${file_path}")
        message(WARNING "Arquivo executavel encontrado: ${file_path}")
    endif()

    # Verificar se e world-writable
    file(READ "${file_path}" content LIMIT 1)
    # Nota: Verificacao de permissoes depende do sistema operacional
endfunction()
```

### 9.11.5 Checklist de Validacao

```cmake
# Checklist completo de validacao de pacote
macro(validate_package_checklist package_name)
    # 1. Pacote encontrado
    if(NOT ${package_name}_FOUND)
        message(FATAL_ERROR "Pacote nao encontrado: ${package_name}")
    endif()

    # 2. Versao definida
    if(NOT DEFINED ${package_name}_VERSION)
        message(WARNING "Versao nao definida para: ${package_name}")
    endif()

    # 3. Variaveis principais definidas
    foreach(var IN ITEMS LIBRARY INCLUDE_DIR)
        if(DEFINED ${package_name}_${var})
            if(NOT EXISTS "${${package_name}_${var}}")
                message(FATAL_ERROR "${var} nao existe: ${${package_name}_${var}}")
            endif()
        endif()
    endforeach()

    # 4. Targets definidos
    foreach(target IN ITEMS ${package_name}::${package_name})
        if(NOT TARGET ${target})
            message(WARNING "Target nao definido: ${target}")
        endif()
    endforeach()

    message(STATUS "Checklist de validacao completo para ${package_name}")
endmacro()
```

---

## 9.12 Exemplo: find_package OpenSSL Seguro

OpenSSL e uma das dependencias mais criticas e comuns em projetos C/C++.

### 9.12.1 Configuracao Basica

```cmake
# find_package OpenSSL basico
find_package(OpenSSL REQUIRED)

if(OPENSSL_FOUND)
    message(STATUS "OpenSSL version: ${OPENSSL_VERSION}")
    message(STATUS "OpenSSL include: ${OPENSSL_INCLUDE_DIR}")
    message(STATUS "OpenSSL libraries: ${OPENSSL_LIBRARIES}")

    target_link_libraries(myapp PRIVATE OpenSSL::SSL OpenSSL::Crypto)
endif()
```

### 9.12.2 Configuracao Segura Completa

```cmake
# Configuracao OpenSSL segura

# 1. Definir versao minima segura
# OpenSSL 1.1.1 EOL em 2023-09-11
# OpenSSL 3.0.x suportado ate 2026-09-07
set(OPENSSL_MIN_VERSION "3.0.0")

# 2. Buscar com restricoes
find_package(OpenSSL ${OPENSSL_MIN_VERSION} REQUIRED)

# 3. Validar versao encontrada
if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL ${OPENSSL_MIN_VERSION})
    message(FATAL_ERROR
        "OpenSSL versao insegura: ${OPENSSL_VERSION}\n"
        "Minimo exigido: ${OPENSSL_MIN_VERSION}\n"
        "Atualize o OpenSSL para uma versao suportada."
    )
endif()

# 4. Verificar caminhos
foreach(lib IN ITEMS SSL Crypto)
    if(DEFINED OPENSSL_${lib}_LIBRARY)
        if(NOT EXISTS "${OPENSSL_${lib}_LIBRARY}")
            message(FATAL_ERROR "Biblioteca OpenSSL nao existe: ${OPENSSL_${lib}_LIBRARY}")
        endif()

        # Verificar se e symlink
        get_filename_component(real_path "${OPENSSL_${lib}_LIBRARY}" REALPATH)
        if(NOT "${real_path}" STREQUAL "${OPENSSL_${lib}_LIBRARY}")
            message(WARNING "OpenSSL ${lib} e symlink: ${OPENSSL_${lib}_LIBRARY}")
        endif()

        # Verificar localizacao
        if(NOT "${real_path}" MATCHES "^/(usr|opt)/")
            message(WARNING "OpenSSL ${lib} em localizacao suspeita: ${real_path}")
        endif()
    endif()
endforeach()

# 5. Verificar include dir
if(DEFINED OPENSSL_INCLUDE_DIR)
    if(NOT EXISTS "${OPENSSL_INCLUDE_DIR}")
        message(FATAL_ERROR "OpenSSL include dir nao existe: ${OPENSSL_INCLUDE_DIR}")
    endif()

    # Verificar se opensslv.h existe e contem informacao de versao
    if(NOT EXISTS "${OPENSSL_INCLUDE_DIR}/openssl/opensslv.h")
        message(FATAL_ERROR "opensslv.h nao encontrado")
    endif()
endif()

# 6. Verificar compatibilidade de API
# OpenSSL 3.0+ usa APIs diferentes de 1.1.1
if(OPENSSL_VERSION VERSION_GREATER_EQUAL "3.0.0")
    message(STATUS "Usando OpenSSL 3.0+ API")
else()
    message(WARNING "Usando API antiga do OpenSSL")
endif()

# 7. Configurar target seguro
target_link_libraries(myapp PRIVATE OpenSSL::SSL OpenSSL::Crypto)

# 8. Adicionar definicoes de seguranca
target_compile_definitions(myapp PRIVATE
    OPENSSL_API_COMPAT=0x10100000L  # Compatibilidade
    OPENSSL_NO_COMP                  # Desabilitar compressao
)
```

### 9.12.3 Funcao de Configuracao OpenSSL

```cmake
# Funcao reutilizavel para configuracao OpenSSL segura
function(configure_openssl_secure target_name)
    set(options REQUIRED)
    set(oneValueArgs MIN_VERSION)
    set(multiValueArgs "")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # Versao padrao
    if(NOT ARG_MIN_VERSION)
        set(ARG_MIN_VERSION "3.0.0")
    endif()

    # Buscar OpenSSL
    find_package(OpenSSL ${ARG_MIN_VERSION}
        ${ARG_REQUIRED}
    )

    if(NOT OPENSSL_FOUND)
        if(ARG_REQUIRED)
            message(FATAL_ERROR "OpenSSL obrigatorio nao encontrado")
        else()
            message(WARNING "OpenSSL nao encontrado")
            return()
        endif()
    endif()

    # Validar versao
    if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL ${ARG_MIN_VERSION})
        message(FATAL_ERROR
            "OpenSSL versao antiga: ${OPENSSL_VERSION} < ${ARG_MIN_VERSION}"
        )
    endif()

    # Validar caminhos
    foreach(lib IN ITEMS SSL Crypto)
        if(DEFINED OPENSSL_${lib}_LIBRARY)
            if(NOT EXISTS "${OPENSSL_${lib}_LIBRARY}")
                message(FATAL_ERROR "Biblioteca OpenSSL nao existe")
            endif()
        endif()
    endforeach()

    # Configurar target
    target_link_libraries(${target_name} PRIVATE OpenSSL::SSL OpenSSL::Crypto)

    # Adicionar include dir
    target_include_directories(${target_name} PRIVATE ${OPENSSL_INCLUDE_DIR})

    message(STATUS "OpenSSL configurado para ${target_name}")
    message(STATUS "  Versao: ${OPENSSL_VERSION}")
    message(STATUS "  SSL Library: ${OPENSSL_SSL_LIBRARY}")
    message(STATUS "  Crypto Library: ${OPENSSL_CRYPTO_LIBRARY}")
endfunction()

# Uso
add_executable(myapp main.cpp)
configure_openssl_secure(myapp
    REQUIRED
    MIN_VERSION "3.0.0"
)
```

### 9.12.4 Open SSL e FIPS

```cmake
# OpenSSL FIPS mode
find_package(OpenSSL 3.0.0 REQUIRED)

# Verificar se FIPS esta disponivel
if(OPENSSL_VERSION VERSION_GREATER_EQUAL "3.0.0")
    # OpenSSL 3.0+ tem suporte FIPS built-in
    target_compile_definitions(myapp PRIVATE OPENSSL_FIPS)

    # Verificar se o provider FIPS esta disponivel
    execute_process(
        COMMAND ${OPENSSL_EXECUTABLE} list -providers
        OUTPUT_VARIABLE providers
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )

    if(providers MATCHES "fips")
        message(STATUS "OpenSSL FIPS provider disponivel")
    else()
        message(WARNING "OpenSSL FIPS provider nao encontrado")
    endif()
endif()
```

---

## 9.13 Exercicios

### Exercicio 1: find_package Basico

Escreva um `CMakeLists.txt` que:

1. Busque OpenSSL 3.0.0+ com REQUIRED
2. Verifique se a versao encontrada e >= 3.0.0
3. Verifique se as bibliotecas existem
4. Link seu alvo com OpenSSL

```cmake
# Solucao
cmake_minimum_required(VERSION 3.20)
project(ex1_openssl)

find_package(OpenSSL 3.0.0 REQUIRED)

if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL "3.0.0")
    message(FATAL_ERROR "OpenSSL muito antigo")
endif()

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE OpenSSL::SSL OpenSSL::Crypto)
```

### Exercicio 2: Validacao de Path

Escreva uma funcao `validate_cmake_prefix_path()` que:

1. Receba CMAKE_PREFIX_PATH como argumento
2. Verifique se cada caminho comeca com `/usr/` ou `/opt/`
3. Emita erro se encontrar caminhos suspeitos

```cmake
# Solucao
function(validate_cmake_prefix_path)
    foreach(path IN LISTS CMAKE_PREFIX_PATH)
        if(NOT path MATCHES "^/(usr|opt)/")
            message(FATAL_ERROR "Caminho suspeito: ${path}")
        endif()
    endforeach()
    message(STATUS "Todos os prefixos validados")
endfunction()

# Uso
validate_cmake_prefix_path()
```

### Exercicio 3: find_library Seguro

Crie uma funcao `safe_find_library()` que:

1. Receba nome da biblioteca e lista de caminhos permitidos
2. Busque a biblioteca apenas nos caminhos permitidos
3. Verifique se o resultado e um symlink
4. Retorne o resultado ou erro

```cmake
# Solucao
function(safe_find_library var_name)
    set(options REQUIRED)
    set(oneValueArgs "")
    set(multiValueArgs NAMES PATHS)
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # Buscar apenas nos caminhos especificados
    find_library(${var_name}
        NAMES ${ARG_NAMES}
        PATHS ${ARG_PATHS}
        NO_DEFAULT_PATH
    )

    # Verificar resultado
    if(NOT ${var_name})
        if(ARG_REQUIRED)
            message(FATAL_ERROR "Biblioteca nao encontrada: ${ARG_NAMES}")
        endif()
        return()
    endif()

    # Verificar symlink
    get_filename_component(real_path "${${var_name}}" REALPATH)
    if(NOT "${real_path}" STREQUAL "${${var_name}}")
        message(WARNING "Biblioteca e symlink: ${${var_name}}")
    endif()
endfunction()

# Uso
safe_find_library(MYLIB
    NAMES mylib
    PATHS /usr/lib /usr/local/lib
    REQUIRED
)
```

### Exercicio 4: Configuracao de Componentes

Escreva um `CMakeLists.txt` que:

1. Busque Boost com system, filesystem e regex
2. Verifique se todos os componentes foram encontrados
3. Use cada componente apenas se encontrado

```cmake
# Solucao
cmake_minimum_required(VERSION 3.20)
project(ex4_boost)

find_package(Boost REQUIRED COMPONENTS system filesystem)
find_package(Boost OPTIONAL_COMPONENTS regex)

# Verificar componentes obrigatorios
foreach(comp IN ITEMS system filesystem)
    if(NOT Boost${comp}_FOUND)
        message(FATAL_ERROR "Componente obrigatorio nao encontrado: ${comp}")
    endif()
endforeach()

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE Boost::system Boost::filesystem)

# Adicionar regex apenas se encontrado
if(Boostregex_FOUND)
    target_link_libraries(myapp PRIVATE Boost::regex)
endif()
```

### Exercicio 5: Seguranca com pkg-config

Crie uma configuracao que:

1. Use pkg-config para encontrar zlib
2. Restinja busca a /usr/lib e /usr/local/lib
3. Verifique a versao encontrada
4. Valide o caminho do pcfile

```cmake
# Solucao
find_package(PkgConfig REQUIRED)

# Definir caminhos permitidos
set(ENV{PKG_CONFIG_PATH} "/usr/lib/pkgconfig:/usr/local/lib/pkgconfig")

pkg_check_modules(ZLIB IMPORTED_TARGET "zlib>=1.2.13")

if(NOT ZLIB_FOUND)
    message(FATAL_ERROR "zlib nao encontrado via pkg-config")
endif()

# Verificar versao
if(NOT ZLIB_VERSION VERSION_GREATER_EQUAL "1.2.13")
    message(FATAL_ERROR "zlib muito antigo: ${ZLIB_VERSION}")
endif()

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE PkgConfig::ZLIB)
```

### Exercicio 6: Funcao de Validacao Completa

Implemente uma funcao `validate_package_complete()` que:

1. Verifique se o pacote foi encontrado
2. Valide a versao minima
3. Verifique se todas as bibliotecas existem
4. Verifique se os include dirs existem
5. Verifique se nao sao symlinks
6. Valide os targets IMPORTED

```cmake
# Solucao
function(validate_package_complete package_name)
    set(options REQUIRED)
    set(oneValueArgs MIN_VERSION)
    set(multiValueArgs "")
    cmake_parse_arguments(ARG "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    # 1. Pacote encontrado
    if(NOT ${package_name}_FOUND)
        if(ARG_REQUIRED)
            message(FATAL_ERROR "Pacote nao encontrado: ${package_name}")
        endif()
        return()
    endif()

    # 2. Versao minima
    if(ARG_MIN_VERSION AND DEFINED ${package_name}_VERSION)
        if(${${package_name}_VERSION} VERSION_LESS ${ARG_MIN_VERSION})
            message(FATAL_ERROR "Versao muito antiga: ${${package_name}_VERSION}")
        endif()
    endif()

    # 3. Bibliotecas
    foreach(lib_var IN ITEMS LIBRARY)
        if(DEFINED ${package_name}_${lib_var})
            if(NOT EXISTS "${${package_name}_${lib_var}}")
                message(FATAL_ERROR "Biblioteca nao existe: ${${package_name}_${lib_var}}")
            endif()
        endif()
    endforeach()

    # 4. Include dirs
    if(DEFINED ${package_name}_INCLUDE_DIR)
        if(NOT EXISTS "${${package_name}_INCLUDE_DIR}")
            message(FATAL_ERROR "Include dir nao existe: ${${package_name}_INCLUDE_DIR}")
        endif()
    endif()

    # 5. Symlinks
    foreach(lib_var IN ITEMS LIBRARY)
        if(DEFINED ${package_name}_${lib_var})
            get_filename_component(real_path "${${package_name}_${lib_var}}" REALPATH)
            if(NOT "${real_path}" STREQUAL "${${package_name}_${lib_var}}")
                message(WARNING "Symlink detectado: ${${package_name}_${lib_var}}")
            endif()
        endif()
    endforeach()

    # 6. Targets
    if(TARGET ${package_name}::${package_name})
        message(STATUS "Target ${package_name}::${package_name} encontrado")
    endif()

    message(STATUS "Validacao completa: ${package_name}")
endfunction()
```

### Exercicio 7: Exercicio Integrado

Crie um `CMakeLists.txt` completo que:

1. Valide CMAKE_PREFIX_PATH
2. Busque OpenSSL 3.0.0+ com validacao
3. Busque zlib 1.2.13+ com validacao
4. Use pkg-config para uma dependencia opcional
5. Valide todos os pacotes encontrados
6. Gere um relatorio de seguranca

```cmake
# Solucao
cmake_minimum_required(VERSION 3.20)
project(ex7_integrado)

# 1. Validar CMAKE_PREFIX_PATH
foreach(path IN LISTS CMAKE_PREFIX_PATH)
    if(NOT path MATCHES "^/(usr|opt)/")
        message(FATAL_ERROR "Caminho suspeito: ${path}")
    endif()
endforeach()

# 2. OpenSSL
find_package(OpenSSL 3.0.0 REQUIRED)
if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL "3.0.0")
    message(FATAL_ERROR "OpenSSL muito antigo")
endif()

# 3. zlib
find_package(ZLIB 1.2.13 REQUIRED)
if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL "1.2.13")
    message(FATAL_ERROR "zlib muito antigo")
endif()

# 4. pkg-config opcional
find_package(PkgConfig QUIET)
if(PKG_CONFIG_FOUND)
    pkg_check_modules(JSON IMPORTED_TARGET json-c)
endif()

# 5. Validar pacotes
foreach(pkg IN ITEMS OpenSSL ZLIB)
    if(DEFINED ${pkg}_LIBRARY)
        if(NOT EXISTS "${${pkg}_LIBRARY}")
            message(FATAL_ERROR "Biblioteca nao existe: ${${pkg}_LIBRARY}")
        endif()
    endif()
endforeach()

# 6. Relatorio
message(STATUS "=== Relatorio de Seguranca ===")
message(STATUS "OpenSSL: ${OPENSSL_VERSION}")
message(STATUS "zlib: ${ZLIB_VERSION_STRING}")
if(DEFINED JSON_VERSION)
    message(STATUS "json-c: ${JSON_VERSION}")
endif()

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE OpenSSL::SSL OpenSSL::Crypto ZLIB::ZLIB)
if(TARGET PkgConfig::JSON)
    target_link_libraries(myapp PRIVATE PkgConfig::JSON)
endif()
```

---

## 9.14 Referencias

### Documentacao Oficial

- [CMake find_package()](https://cmake.org/cmake/help/latest/command/find_package.html)
- [CMake find_library()](https://cmake.org/cmake/help/latest/command/find_library.html)
- [CMake find_path()](https://cmake.org/cmake/help/latest/command/find_path.html)
- [CMake find_program()](https://cmake.org/cmake/help/latest/command/find_program.html)
- [CMake IMPORTED Targets](https://cmake.org/cmake/help/latest/prop_tgt/IMPORTED.html)
- [CMake Variables](https://cmake.org/cmake/help/latest/variable/CMAKE_FIND_PACKAGE_PREFER_CONFIG.html)

### Artigos e Blogs

- [Modern CMake: find_package](https://cliutils.gitlab.io/modern-cmake/chapters/find-package.html)
- [CMake find_package Security](https://cmake.org/cmake/help/latest/manual/cmake-packages.7.html)
- [pkg-config Integration](https://cmake.org/cmake/help/latest/module/FindPkgConfig.html)

### CVEs Relacionadas

- **CVE-2024-3094**: XZ Utils backdoor (supply chain via build system)
- **CVE-2023-44487**: HTTP/2 Rapid Reset (dependencias de rede)
- **CVE-2021-44228**: Log4Shell (dependency injection)

### Ferramentas

- [Conan Package Manager](https://conan.io/)
- [vcpkg Package Manager](https://vcpkg.io/)
- [pkg-config](https://www.freedesktop.org/wiki/Software/pkg-config/)

### Livros

- "Professional CMake" by Craig Scott
- "CMake Best Practices" by Dominik Berner
- "Mastering CMake" by Kitware

---

## Proximo Capitulo

*[Proximo capitulo: 10 — FetchContent e ExternalProject](10-fetchcontent-external.md)*

---

*Este capitulo faz parte do livro "CMake Seguro e Build Systems" do projeto DevSecurity.*

---

## 9.15 Estudo de Caso: Projeto Real com Multiplas Dependencias

Nesta secao, vamos analisar um projeto real que precisa de multiplas dependencias externas e como configurar cada uma de forma segura.

### 9.15.1 Cenario do Projeto

Imagine um servidor HTTP que depende de:

- OpenSSL (criptografia)
- zlib (compressao)
- libevent (async I/O)
- json-c (parsing JSON)
- pthreads (threading)

### 9.15.2 CMakeLists.txt Completo

```cmake
cmake_minimum_required(VERSION 3.20)
project(secure_server VERSION 1.0.0 LANGUAGES C CXX)

# Configuracoes globais de seguranca
set(CMAKE_C_STANDARD 17)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Preferir Config files sobre find modules
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

# ============================================================================
# Validacao de CMAKE_PREFIX_PATH
# ============================================================================

# Funcao para validar prefixos
function(validate_prefix_paths)
    foreach(path IN LISTS CMAKE_PREFIX_PATH)
        # Ignorar caminhos vazios
        if("${path}" STREQUAL "")
            continue()
        endif()

        # Verificar se comeca com /usr ou /opt
        if(NOT path MATCHES "^/(usr|opt)/")
            message(FATAL_ERROR
                "Caminho nao confiavel em CMAKE_PREFIX_PATH:\n"
                "  Caminho: ${path}\n"
                "  Motivo: Nao esta em /usr ou /opt\n"
                "  Solucao: Remova este caminho ou use -DCMAKE_PREFIX_PATH"
            )
        endif()

        # Verificar se o diretorio existe
        if(NOT EXISTS "${path}")
            message(WARNING
                "Caminho em CMAKE_PREFIX_PATH nao existe:\n"
                "  Caminho: ${path}"
            )
        endif()
    endforeach()

    message(STATUS "CMAKE_PREFIX_PATH validado com sucesso")
endfunction()

validate_prefix_paths()

# ============================================================================
# OpenSSL (Critico para seguranca)
# ============================================================================

# OpenSSL 1.1.1 EOL em 2023-09-11
# OpenSSL 3.0.x suportado ate 2026-09-07
# OpenSSL 3.1.x suportado ate 2025-03-14
set(OPENSSL_MIN_VERSION "3.0.0")

find_package(OpenSSL ${OPENSSL_MIN_VERSION} REQUIRED)

# Validacao completa de OpenSSL
function(validate_openssl)
    # 1. Pacote encontrado
    if(NOT OpenSSL_FOUND)
        message(FATAL_ERROR "OpenSSL nao encontrado")
    endif()

    # 2. Versao minima
    if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL ${OPENSSL_MIN_VERSION})
        message(FATAL_ERROR
            "OpenSSL versao insegura:\n"
            "  Atual: ${OPENSSL_VERSION}\n"
            "  Minimo: ${OPENSSL_MIN_VERSION}\n"
            "  Acao: Atualize o OpenSSL"
        )
    endif()

    # 3. Bibliotecas existem
    foreach(lib IN ITEMS SSL Crypto)
        set(lib_var "OPENSSL_${lib}_LIBRARY")
        if(DEFINED ${lib_var})
            if(NOT EXISTS "${${lib_var}}")
                message(FATAL_ERROR "Biblioteca OpenSSL nao existe: ${${lib_var}}")
            endif()

            # Verificar symlink
            get_filename_component(real_path "${${lib_var}}" REALPATH)
            if(NOT "${real_path}" STREQUAL "${${lib_var}}")
                message(WARNING "OpenSSL ${lib} e symlink: ${${lib_var}}")
            endif()

            # Verificar localizacao
            if(NOT "${real_path}" MATCHES "^/(usr|opt)/")
                message(FATAL_ERROR "OpenSSL ${lib} em localizacao suspeita: ${real_path}")
            endif()
        endif()
    endforeach()

    # 4. Include dir
    if(NOT EXISTS "${OPENSSL_INCLUDE_DIR}")
        message(FATAL_ERROR "OpenSSL include dir nao existe: ${OPENSSL_INCLUDE_DIR}")
    endif()

    # 5. opensslv.h existe
    if(NOT EXISTS "${OPENSSL_INCLUDE_DIR}/openssl/opensslv.h")
        message(FATAL_ERROR "opensslv.h nao encontrado")
    endif()

    message(STATUS "OpenSSL validado: ${OPENSSL_VERSION}")
endfunction()

validate_openssl()

# ============================================================================
# zlib
# ============================================================================

set(ZLIB_MIN_VERSION "1.2.13")

find_package(ZLIB ${ZLIB_MIN_VERSION} REQUIRED)

# Validacao de zlib
function(validate_zlib)
    if(NOT ZLIB_FOUND)
        message(FATAL_ERROR "zlib nao encontrado")
    endif()

    if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL ${ZLIB_MIN_VERSION})
        message(FATAL_ERROR "zlib muito antigo: ${ZLIB_VERSION_STRING}")
    endif()

    if(NOT EXISTS "${ZLIB_LIBRARY}")
        message(FATAL_ERROR "Biblioteca zlib nao existe: ${ZLIB_LIBRARY}")
    endif()

    get_filename_component(real_path "${ZLIB_LIBRARY}" REALPATH)
    if(NOT "${real_path}" MATCHES "^/(usr|opt)/")
        message(FATAL_ERROR "zlib em localizacao suspeita: ${real_path}")
    endif()

    message(STATUS "zlib validado: ${ZLIB_VERSION_STRING}")
endfunction()

validate_zlib()

# ============================================================================
# libevent
# ============================================================================

find_package(libevent 2.1.0 REQUIRED)

# Validacao de libevent
function(validate_libevent)
    if(NOT libevent_FOUND)
        message(FATAL_ERROR "libevent nao encontrado")
    endif()

    if(DEFINED libevent_INCLUDE_DIR)
        if(NOT EXISTS "${libevent_INCLUDE_DIR}")
            message(FATAL_ERROR "libevent include dir nao existe")
        endif()
    endif()

    if(DEFINED libevent_LIBRARIES)
        foreach(lib IN LISTS libevent_LIBRARIES)
            if(EXISTS "${lib}")
                get_filename_component(real_path "${lib}" REALPATH)
                if(NOT "${real_path}" MATCHES "^/(usr|opt)/")
                    message(WARNING "libevent em localizacao suspeita: ${real_path}")
                endif()
            endif()
        endforeach()
    endif()

    message(STATUS "libevent validado")
endfunction()

validate_libevent()

# ============================================================================
# json-c
# ============================================================================

find_package(PkgConfig REQUIRED)
pkg_check_modules(JSONC IMPORTED_TARGET json-c)

if(NOT JSONC_FOUND)
    message(FATAL_ERROR "json-c nao encontrado via pkg-config")
endif()

# Validacao de json-c
if(DEFINED JSONC_VERSION)
    if(JSONC_VERSION VERSION_LESS "0.13")
        message(WARNING "json-c versao antiga: ${JSONC_VERSION}")
    endif()
endif()

# ============================================================================
# Threads
# ============================================================================

find_package(Threads REQUIRED)

if(NOT Threads_FOUND)
    message(FATAL_ERROR "Threads nao encontrado")
endif()

# ============================================================================
# Relatorio de Seguranca
# ============================================================================

message(STATUS "")
message(STATUS "========================================")
message(STATUS "  RELATORIO DE SEGURANCA - DEPENDENCIAS")
message(STATUS "========================================")
message(STATUS "OpenSSL:   ${OPENSSL_VERSION}")
message(STATUS "zlib:      ${ZLIB_VERSION_STRING}")
message(STATUS "libevent:  ${libevent_VERSION}")
message(STATUS "json-c:    ${JSONC_VERSION}")
message(STATUS "Threads:   ${Threads_FOUND}")
message(STATUS "========================================")
message(STATUS "")

# ============================================================================
# Target Principal
# ============================================================================

add_executable(secure_server
    src/main.cpp
    src/server.cpp
    src/crypto.cpp
    src/compress.cpp
)

target_link_libraries(secure_server PRIVATE
    OpenSSL::SSL
    OpenSSL::Crypto
    ZLIB::ZLIB
    ${libevent_LIBRARIES}
    PkgConfig::JSONC
    Threads::Threads
)

target_include_directories(secure_server PRIVATE
    ${OPENSSL_INCLUDE_DIR}
    ${ZLIB_INCLUDE_DIR}
    ${libevent_INCLUDE_DIR}
    ${JSONC_INCLUDE_DIRS}
)

# ============================================================================
# Flags de Seguranca
# ============================================================================

target_compile_options(secure_server PRIVATE
    -Wall
    -Wextra
    -Werror
    -fstack-protector-strong
    -D_FORTIFY_SOURCE=2
    -fPIE
)

target_link_options(secure_server PRIVATE
    -Wl,-z,relro,-z,now
    -pie
)
```

### 9.15.3 Analise de Seguranca do Projeto

| Dependencia | Versao Minima | Risco | Mitigacao |
|-------------|---------------|-------|-----------|
| OpenSSL | 3.0.0 | Alto | Versao EOL, CVEs |
| zlib | 1.2.13 | Medio | Buffer overflow historico |
| libevent | 2.1.0 | Medio | Vulnerabilidades de parsing |
| json-c | 0.13 | Baixo | Parsing vulnerabilities |
| pthreads | N/A | Baixo | Parte do sistema |

---

## 9.16 Padroes Avancados de find_package

### 9.16.1 Modo QUIET

O modo QUIET impede mensagens de erro quando o pacote nao e encontrado.

```cmake
# QUIET: Nao emitir erro se nao encontrar
find_package(MyLib QUIET)

if(MyLib_FOUND)
    target_link_libraries(myapp PRIVATE MyLib::MyLib)
else()
    # Usar fallback
    message(STATUS "MyLib nao encontrado, usando implementacao propria")
endif()
```

### 9.16.2 Modo REQUIRED com QUIET

```cmake
# REQUIRED + QUIET: Erro silencioso
find_package(MyLib REQUIRED QUIET)
# O erro sera emitido apenas uma vez, nao varias vezes
```

### 9.16.3 Variaveis de Controle

```cmake
# Desabilitar busca em diretorios padrao
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# Forcar busca em diretorios especificos
set(CMAKE_FIND_ROOT_PATH /opt/sysroot)

# Usar caminhos absolutos
find_package(OpenSSL
    PATHS /opt/openssl/lib/cmake/openssl
    NO_DEFAULT_PATH
)
```

### 9.16.4 Customizacao por Pacote

```cmake
# Customizar comportamento de find_package por pacote
set(ZLIB_ROOT "/opt/zlib-1.2.13")
set(OPENSSL_ROOT_DIR "/opt/openssl-3.0.0")

find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)
```

### 9.16.5 Cache e Reexecucao

```cmake
# CMake cacheia resultados de find_package
# Para forcar reexecucao:
# rm -rf build/
# cmake -B build

# Ou desabilitar cache
set(CMAKE_FIND_PACKAGE_NO_PACKAGE_CACHE ON)

# Ou limpar cache especifico
unset(ZLIB_LIBRARY CACHE)
unset(ZLIB_INCLUDE_DIR CACHE)
find_package(ZLIB REQUIRED)
```

---

## 9.17 Trabalhando com Pacotes Nao Padronizados

Nem todos os pacotes fornecem Config files ou Find modules.

### 9.17.1 Criando um Find Module

```cmake
# FindMyLib.cmake
#
# Modulo para encontrar MyLib
#

# Buscar include dir
find_path(MYLIB_INCLUDE_DIR
    NAMES mylib.h
    PATHS
        /usr/include
        /usr/local/include
        /opt/mylib/include
    PATH_SUFFIXES mylib
)

# Buscar biblioteca
find_library(MYLIB_LIBRARY
    NAMES mylib
    PATHS
        /usr/lib
        /usr/lib64
        /usr/local/lib
        /opt/mylib/lib
)

# Determinar versao
if(MYLIB_INCLUDE_DIR AND EXISTS "${MYLIB_INCLUDE_DIR}/mylib_version.h")
    file(STRINGS "${MYLIB_INCLUDE_DIR}/mylib_version.h" version_line
        REGEX "^#define MYLIB_VERSION_[A-Z]+ [0-9]+")
    string(REGEX REPLACE "^#define MYLIB_VERSION_MAJOR ([0-9]+)$" "\\1"
        MYLIB_VERSION_MAJOR "${version_line}")
    string(REGEX REPLACE "^#define MYLIB_VERSION_MINOR ([0-9]+)$" "\\1"
        MYLIB_VERSION_MINOR "${version_line}")
    set(MYLIB_VERSION "${MYLIB_VERSION_MAJOR}.${MYLIB_VERSION_MINOR}")
endif()

# Validacao
include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(MyLib
    REQUIRED_VARS MYLIB_LIBRARY MYLIB_INCLUDE_DIR
    VERSION_VAR MYLIB_VERSION
)

# Criar target IMPORTED
if(MYLIB_FOUND AND NOT TARGET MyLib::MyLib)
    add_library(MyLib::MyLib UNKNOWN IMPORTED)
    set_target_properties(MyLib::MyLib PROPERTIES
        IMPORTED_LOCATION "${MYLIB_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${MYLIB_INCLUDE_DIR}"
    )
endif()

mark_as_advanced(MYLIB_INCLUDE_DIR MYLIB_LIBRARY)
```

### 9.17.2 Criando um Config File

```cmake
# MyLibConfig.cmake.in (template)
@PACKAGE_INIT@

include(CMakeFindDependencyMacro)

# Encontrar dependencias
find_dependencyThreads)

# Definir targets
add_library(MyLib::MyLib UNKNOWN IMPORTED)
set_target_properties(MyLib::MyLib PROPERTIES
    IMPORTED_LOCATION "@PACKAGE_MYLIB_LIBDIR@/libmylib.so"
    INTERFACE_INCLUDE_DIRECTORIES "@PACKAGE_MYLIB_INCLUDEDIR@"
)

# Configuracao de versao
include("${CMAKE_CURRENT_LIST_DIR}/MyLibConfigVersion.cmake")
```

### 9.17.3 Gerando Config Files

```cmake
# No CMakeLists.txt da MyLib
include(CMakePackageConfigHelpers)

configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/MyLibConfig.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfig.cmake"
    INSTALL_DESTINATION lib/cmake/MyLib
)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

# Instalar config files
install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/MyLibConfigVersion.cmake"
    DESTINATION lib/cmake/MyLib
)
```

---

## 9.18 Debugging de find_package

### 9.18.1 Mensagens de Debug

```cmake
# Habilitar mensagens de debug
set(CMAKE_FIND_DEBUG_MODE TRUE)

find_package(ZLIB)
# Agora o CMake mostra todos os caminhos pesquisados
```

### 9.18.2 Variaveis de Debug

```cmake
# Mostrar variaveis encontradas
message(STATUS "ZLIB_FOUND: ${ZLIB_FOUND}")
message(STATUS "ZLIB_VERSION: ${ZLIB_VERSION}")
message(STATUS "ZLIB_INCLUDE_DIR: ${ZLIB_INCLUDE_DIR}")
message(STATUS "ZLIB_LIBRARY: ${ZLIB_LIBRARY}")

# Mostrar todos os caminhos pesquisados
message(STATUS "CMAKE_PREFIX_PATH: ${CMAKE_PREFIX_PATH}")
message(STATUS "CMAKE_FRAMEWORK_PATH: ${CMAKE_FRAMEWORK_PATH}")
```

### 9.18.3 Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| "Could not find ZLIB" | Biblioteca nao instalada | Instalar zlib-dev |
| "Could not find a package configuration file" | Falta Config.cmake | Instalar pacote de desenvolvimento |
| "Version mismatch" | Versao incompativel | Atualizar ou desabilitar verificacao |
| "Target not found" | Config file incompleto | Verificar instalacao |

### 9.18.4 Ferramentas de Diagnostico

```bash
# Listar todos os pacotes CMake disponiveis
cmake --find-package -DNAME=ZLIB -DLANGUAGE=CXX -DCOMPILER_ID=GNU -DMODE=EXIST

# Verificar versao do CMake
cmake --version

# Listar modulos disponiveis
ls /usr/share/cmake-*/Modules/Find*.cmake

# Verificar variaveis de ambiente
echo $CMAKE_PREFIX_PATH
echo $PKG_CONFIG_PATH
```

---

## 9.19 Integracao com Sistemas de Build

### 9.19.1 Integracao com vcpkg

```cmake
# vcpkg automaticamente fornece Config files
# Nao e necessario find_package com opcoes extras

find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)

# vcpkg garante que as versoes sao consistentes
```

### 9.19.2 Integracao com Conan

```cmake
# Conan gera Config files automaticamente
# Usar find_package normalmente

find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)

# Conan gerencia versoes e dependencias
```

### 9.19.3 Integracao com Spack

```cmake
# Spack fornece modulos de ambiente
# Usar find_package com caminhos especificos

find_package(ZLIB
    PATHS $ENV{ZLIB_ROOT}/lib/cmake/zlib
    NO_DEFAULT_PATH
)
```

### 9.19.4 Integracao com Sistemas Operacionais

```cmake
# Linux: usar diretorios padrao do sistema
find_package(ZLIB
    PATHS
        /usr/lib/x86_64-linux-gnu
        /usr/lib64
    PATH_SUFFIXES cmake/zlib
)

# macOS: usar Homebrew ou MacPorts
find_package(OpenSSL
    PATHS
        /opt/homebrew
        /usr/local
    PATH_SUFFIXES lib/cmake/openssl
)

# Windows: usar vcpkg ou instalacao manual
find_package(OpenSSL
    PATHS
        C:/Program Files/OpenSSL
        C:/vcpkg/installed/x64-windows
)
```

---

## 9.20 Resumo e Melhores Praticas

### 9.20.1 Regras de Ouro

1. **Sempre usar REQUIRED** para dependencias criticas
2. **Restringir CMAKE_PREFIX_PATH** a diretorios confiaveis
3. **Validar versoes** com restricoes de versao
4. **Verificar caminhos** apos find_package
5. **Usar IMPORTED targets** em vez de variaveis
6. **Preferir Config files** sobre find modules
7. **Documentar dependencias** e suas versoes

### 9.20.2 Checklist de Seguranca

- [ ] CMAKE_PREFIX_PATH validado
- [ ] Todas as dependencias tem restricao de versao
- [ ] Caminhos de bibliotecas verificados
- [ ] Symlinks detectados e investigados
- [ ] IMPORTED targets usados corretamente
- [ ] Config files preferidos sobre find modules
- [ ] Relatorio de dependencias gerado
- [ ] Builds reproduziveis verificados

### 9.20.3 Anti-Patterns

```cmake
# RUIM: Sem restricao de versao
find_package(OpenSSL)

# RUIM: Caminhos nao confiaveis
list(APPEND CMAKE_PREFIX_PATH "/tmp")

# RUIM: Usando variaveis em vez de targets
include_directories(${ZLIB_INCLUDE_DIR})
link_directories(${ZLIB_LIBRARY_DIR})

# RUIM: Sem validacao
find_package(MyLib REQUIRED)
target_link_libraries(myapp PRIVATE MyLib::MyLib)
```

### 9.20.4 Padroes Recomendados

```cmake
# BOM: Com restricao de versao
find_package(OpenSSL 3.0.0 REQUIRED)

# BOM: Caminhos validados
set(CMAKE_PREFIX_PATH "/usr;/usr/local")

# BOM: Usando targets
target_link_libraries(myapp PRIVATE OpenSSL::SSL)

# BOM: Com validacao
find_package(ZLIB REQUIRED)
if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL "1.2.13")
    message(FATAL_ERROR "zlib muito antigo")
endif()
```

---

## 9.21 Exercicios Adicionais

### Exercicio 8: Debug de find_package

Crie um script que:

1. Habilite CMAKE_FIND_DEBUG_MODE
2. Execute cmake com --trace-source
3. Analise a saida para encontrar problemas

```bash
#!/bin/bash
# Script de debug
mkdir -p build-debug
cd build-debug

cmake .. \
    --trace-source="FindOpenSSL.cmake" \
    --trace-expand \
    -DCMAKE_FIND_DEBUG_MODE=TRUE \
    2>&1 | tee cmake-debug.log

# Analisar log
grep -i "error\|warning\|found" cmake-debug.log
```

### Exercicio 9: Criacao de Find Module

Crie um Find module completo para uma biblioteca ficticia que:

1. Busque headers e bibliotecas
2. Determine a versao
3. Crie um target IMPORTED
4. Valide o resultado

### Exercicio 10: Integracao com CI/CD

Crie um workflow de CI que:

1. Valide todas as dependencias
2. Gere um relatorio de seguranca
3. Falhe se encontrar versoes inseguras
4. Armazene o relatorio como artefato

```yaml
# .github/workflows/dependency-check.yml
name: Dependency Security Check

on: [push, pull_request]

jobs:
  check-deps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            libssl-dev \
            zlib1g-dev \
            libevent-dev \
            libjson-c-dev

      - name: Configure CMake
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DENABLE_SECURITY_CHECK=ON

      - name: Build
        run: cmake --build build

      - name: Upload security report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: build/security-report.json
```

### Exercicio 11: Funcao de Auditoria

Crie uma funcao `audit_dependencies()` que:

1. Liste todas as dependencias encontradas
2. Verifique versoes contra base de dados de CVEs
3. Gere relatorio em JSON
4. Retorne status de seguranca

### Exercicio 12: Pacote com Multiplas Versoes

Crie um cenario onde:

1. O sistema tem multiplas versoes de OpenSSL instaladas
2. O CMakeLists.txt deve escolher a versao correta
3. Implemente logica de selecao baseada em seguranca

---

## 9.22 Glossario

| Termo | Definicao |
|-------|-----------|
| **find_package** | Funcao CMake para localizar dependencias externas |
| **Find Module** | Script CMake que busca por um pacote especifico |
| **Config File** | Arquivo gerado pelo pacote para configuracao |
| **IMPORTED Target** | Target CMake que representa uma biblioteca externa |
| **CMAKE_PREFIX_PATH** | Lista de diretorios para buscar pacotes |
| **pkg-config** | Ferramenta para gerenciar dependencias em Unix |
| **FIPS** | Federal Information Processing Standards |
| **CVE** | Common Vulnerabilities and Exposures |
| **EOL** | End of Life |
| **Symlink** | Link simbolico para outro arquivo |

---

## 9.23 Perguntas Frequentes

### P: Quando usar Basic vs Config mode?

**R:** Prefira Config mode quando disponivel. Ele e mais seguro porque e gerado pelo proprio pacote e inclui validacao de versao. Use Basic mode apenas quando o pacote nao fornece Config files.

### P: Como saber se um pacote fornece Config files?

**R:** Verifique se existe `<PackageName>Config.cmake` ou `<lowercase-package-name>-config.cmake` no diretorio de instalacao do pacote.

### P: E seguro usar CMAKE_PREFIX_PATH?

**R:** Sim, desde que voce valide os caminhos. Nunca adicione diretorios nao confiaveis (como /tmp ou diretorios do usuario) ao CMAKE_PREFIX_PATH em builds de producao.

### P: Como verificar se um pacote e confiavel?

**R:** Verifique: (1) versao e se e suportada, (2) caminho de instalacao, (3) integridade do binario (hash ou assinatura), (4) origem (repositorio oficial vs terceiros).

### P: O que fazer se um pacote nao fornecem Config files?

**R:** Crie um Find module ou contacte os mantenedores do pacote para adicionar suporte a CMake. Como alternativa, use pkg-config.

---

## 9.24 Exemplo Pratico: Projeto de Producao

### 9.24.1 Estrutura do Projeto

```
myproject/
├── CMakeLists.txt
├── cmake/
│   ├── FindOpenSSL.cmake
│   └── FindZLIB.cmake
├── src/
│   ├── main.cpp
│   ├── server.cpp
│   └── crypto.cpp
├── config/
│   └── dependencies.cmake
└── scripts/
    └── validate-deps.sh
```

### 9.24.2 Arquivo de Configuracao de Dependencias

```cmake
# config/dependencies.cmake

# Versoes minimas seguras
set(DEPS_OPENSSL_MIN "3.0.0")
set(DEPS_ZLIB_MIN "1.2.13")
set(DEPS_LIBEVENT_MIN "2.1.0")

# Funcao para validar todas as dependencias
function(validate_all_dependencies)
    # OpenSSL
    find_package(OpenSSL ${DEPS_OPENSSL_MIN} REQUIRED)
    if(NOT OPENSSL_VERSION VERSION_GREATER_EQUAL ${DEPS_OPENSSL_MIN})
        message(FATAL_ERROR "OpenSSL inseguro")
    endif()

    # zlib
    find_package(ZLIB ${DEPS_ZLIB_MIN} REQUIRED)
    if(NOT ZLIB_VERSION_STRING VERSION_GREATER_EQUAL ${DEPS_ZLIB_MIN})
        message(FATAL_ERROR "zlib inseguro")
    endif()

    # libevent
    find_package(libevent ${DEPS_LIBEVENT_MIN} REQUIRED)

    message(STATUS "Todas as dependencias validadas")
endfunction()
```

### 9.24.3 Script de Validacao

```bash
#!/bin/bash
# scripts/validate-deps.sh

set -e

echo "=== Validacao de Dependencias ==="

# Verificar se as dependencias estao instaladas
check_package() {
    local name=$1
    local min_version=$2

    if ! pkg-config --exists "$name"; then
        echo "ERRO: $name nao encontrado"
        exit 1
    fi

    local version=$(pkg-config --modversion "$name")
    if [ "$(printf '%s\n' "$min_version" "$version" | sort -V | head -n1)" != "$min_version" ]; then
        echo "ERRO: $name versao $version < $min_version"
        exit 1
    fi

    echo "OK: $name $version"
}

check_package "openssl" "3.0.0"
check_package "zlib" "1.2.13"
check_package "libevent" "2.1.0"

echo "=== Todas as dependencias validadas ==="
```

---

## 9.25 Casos de Estudo Reais

### 9.25.1 Caso: Equifax Breach (2017)

Embora nao seja diretamente sobre CMake, a Equifax breach ilustra a importancia de gerenciar dependencias:

- Apache Struts com CVE-2017-5638
- Falta de gerenciamento de versoes
- Falta de atualizacoes de seguranca

**Lições para CMake:**
- Sempre usar restricoes de versao
- Manter um inventario de dependencias
- Atualizar regularmente

### 9.25.2 Caso: SolarWinds (2020)

O ataque ao SolarWinds compromiseou o build system:

- Malicious code injetado durante build
- Dependencias de supply chain comprometidas

**Lições para CMake:**
- Validar integridade de dependencias
- Usar builds reproduziveis
- Auditar CMAKE_PREFIX_PATH

### 9.25.3 Caso: Log4Shell (2021)

CVE-2021-44228 afetou Log4j:

- Dependencia transitiva mal gerenciada
- Versoes antigas em producao

**Lições para CMake:**
- Verificar dependencias transitivas
- Usar IMPORTED targets para visibilidade
- Gerar relatorios de dependencias

---

## 9.26 Proximos Passos

Neste capitulo, voce aprendeu a:

- Usar find_package() de forma segura
- Validar pacotes encontrados
- Mitigar riscos de path injection e typosquatting
- Integrar pkg-config com seguranca

No proximo capitulo, vamos explorar:

- [FetchContent e ExternalProject](10-fetchcontent-external.md)
- Como buscar e construir dependencias de forma segura
- Pinning e hash verification
- Supply chain security

---

*Fim do Capitulo 9 — Finding Packages Seguro*
