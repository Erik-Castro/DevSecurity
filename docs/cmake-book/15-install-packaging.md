---
layout: default
title: "15-install-packaging"
---

# Capítulo 15: Install e Packaging

## Sumário

- [15.1 Objetivos de Aprendizado](#151-objetivos-de-aprendizado)
- [15.2 install(): TARGETS, DIRECTORY, FILES](#152-install-targets-directory-files)
- [15.3 CMAKE_INSTALL_PREFIX vs DESTDIR](#153-cmake_install_prefix-vs-destdir)
- [15.4 GNUInstallDirs: Padrão de Instalação](#154-gnuinstalldirs-padrão-de-instalação)
- [15.5 Component-based Installation](#155-component-based-installation)
- [15.6 RPATH: Configuração e Segurança](#156-rpath-configuração-e-segurança)
- [15.7 CPack: Geradores (DEB, RPM, NSIS, TGZ)](#157-cpack-geradores-deb-rpm-nsis-tgz)
- [15.8 CPack Variables: CPACK_PACKAGE_*, CPACK_GENERATOR](#158-cpack-variables-cpack_package_-cpack_generator)
- [15.9 CPack Component Groups](#159-cpack-component-groups)
- [15.10 Packaging Seguro: Signing, Hash Verification](#1510-packaging-seguro-signing-hash-verification)
- [15.11 Debian Packaging: debian/control, rules](#1511-debian-packaging-debiancontrol-rules)
- [15.12 RPM Packaging: Spec Files](#1512-rpm-packaging-spec-files)
- [15.13 Exemplo: Install + CPack Completo](#1513-exemplo-install--cpack-completo)
- [15.14 Exercícios](#1514-exercícios)
- [15.15 Referências](#1515-referências)

---

## 15.1 Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Utilizar `install()` de forma segura e eficiente para alvos, diretórios e arquivos
2. Diferenciar `CMAKE_INSTALL_PREFIX` de `DESTDIR` e aplicar corretamente em cada cenário
3. Adotar `GNUInstallDirs` para conformidade com padrões de instalação em Linux
4. Implementar componentes de instalação para controle granular do que é instalado
5. Configurar RPATH de forma segura, evitando vulnerabilidades de loading dinâmico
6. Utilizar CPack para gerar pacotes DEB, RPM, NSIS e TGZ
7. Configurar variáveis do CPack para metadados de pacote completos
8. Organizar componentes em grupos para instalação modular
9. Implementar signing e verificação de hash em pacotes gerados
10. Entender a estrutura de `debian/control` e `rules` para pacotes Debian
11. Criar spec files RPM para distribuições Red Hat
12. Construir um pipeline completo de install + CPack com segurança integrada

### Pré-requisitos

- Conhecimento de CMake básico até intermediário (Capítulos 01-03)
- Familiaridade com build systems e geradores (Make, Ninja)
- Ter lido o Capítulo 14 sobre Testing no CMake
- Noções básicas de gerenciamento de pacotes em Linux

### Ferramentas Necessárias

- CMake 3.20 ou superior
- Compilador C/C++ funcional
- dpkg-dev (para pacotes Debian)
- rpm-build (para pacotes RPM)
- GPG (para signing de pacotes)

---

## 15.2 install(): TARGETS, DIRECTORY, FILES

### O Problema: Distribuição Insegura

A instalação de software é frequentemente tratada como um passo trivial após o build. No entanto, erros na instalação podem criar vulnerabilidades críticas:

- Arquivos instalados com permissões incorretas (executável world-writable)
- Headers instalados em diretórios acessíveis por outros usuários
- Bibliotecas instaladas em paths que permitem library path injection
- Arquivos de configuração instalados com dados sensíveis hardcoded
- Binários instalados sem strip, expondo informações de debug

O comando `install()` do CMake é a primeira linha de defesa contra esses problemas. Vamos analisar cada variante em profundidade.

### install(TARGETS): Instalando Binários e Bibliotecas

A variante `install(TARGETS)` é usada para instalar alvos que foram criados com `add_executable()` ou `add_library()`. Esta é a forma mais segura e recomendada de instalar artefatos compilados.

#### Sintaxe Básica

```cmake
install(
    TARGETS <target> [<target> ...]
    [EXPORT <export-name>]
    [RUNTIME DESTINATION <dir>]
    [LIBRARY DESTINATION <dir>]
    [ARCHIVE DESTINATION <dir>]
    [INCLUDES DESTINATION <dir>]
    [FRAMEWORK DESTINATION <dir>]
    [CXX_MODULES_BMI_DESTINATION <dir>]
    [OBJECTS DESTINATION <dir>]
    [PRIVATE_HEADER DESTINATION <dir>]
    [PUBLIC_HEADER DESTINATION <dir>]
    [RESOURCE DESTINATION <dir>]
)
```

#### Exemplo Básico com Segurança

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureInstaller C CXX)

# Criar alvos
add_executable(myapp main.cpp)
add_library(mylib SHARED lib.cpp)

# Configurar propriedades de seguranca nos alvos
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH_USE_LINK_PATH TRUE
    INSTALL_RPATH "$ORIGIN/../lib"
)

# Instalar com destinos corretos
install(
    TARGETS myapp mylib
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib/static
    INCLUDES DESTINATION include
)
```

#### Entendendo os Destinos

Cada tipo de artefato de build tem um destino apropriado:

| Tipo de Artefato | Propriedade | Destino Padrão | Descrição |
|-----------------|-------------|-----------------|-----------|
| Executável (não- framework) | RUNTIME | `${CMAKE_INSTALL_BINDIR}` | Binários executáveis |
| Biblioteca compartilhada (não-framework) | LIBRARY | `${CMAKE_INSTALL_LIBDIR}` | .so, .dylib |
| Biblioteca estática | ARCHIVE | `${CMAKE_INSTALL_LIBDIR}` | .a, .lib |
| Header público | PUBLIC_HEADER | `${CMAKE_INSTALL_INCLUDEDIR}` | .h, .hpp |
| Arquivo de objeto | OBJECTS | `${CMAKE_INSTALL_LIBDIR}` | .o |
| Framework (Apple) | FRAMEWORK | `${CMAKE_INSTALL_FRAMEWORK_DIR}` | .framework |
| Módulo C++ (BMI) | CXX_MODULES_BMI_DESTINATION | `${CMAKE_INSTALL_LIBDIR}/cxx_modules/` | .pcm |
| Recurso | RESOURCE | `${CMAKE_INSTALL_DATAROOTDIR}` | .plist, .xib |

#### Cenário: Biblioteca com Headers e Export

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureLib VERSION 1.0.0 LANGUAGES C CXX)

# Criar biblioteca compartilhada
add_library(securelib SHARED
    src/securelib.cpp
    src/crypto_utils.cpp
    src/hash_utils.cpp
)

# Configurar versionamento da biblioteca
set_target_properties(securelib PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "include/securelib.h;include/crypto_utils.h;include/hash_utils.h"
    INSTALL_RPATH "$ORIGIN"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# Configurar include directories para consumers
target_include_directories(securelib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

# Gerar arquivo de export para downstream usage
include(GNUInstallDirs)
install(
    TARGETS securelib
    EXPORT securelib-targets
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/securelib
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

# Instalar arquivo de export
install(
    EXPORT securelib-targets
    FILE securelib-targets.cmake
    NAMESPACE SecureLib::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/securelib
)
```

### install(DIRECTORY): Instalando Árvores de Diretórios

A variante `install(DIRECTORY)` permite instalar árvores inteiras de diretórios, com controle fino sobre quais arquivos são incluídos.

#### Sintaxe Completa

```cmake
install(
    DIRECTORY <dir>...
    [TYPE <type> | DESTINATION <dir>]
    [FILE_PERMISSIONS <permissions>...]
    [DIRECTORY_PERMISSIONS <permissions>...]
    [USE_SOURCE_PERMISSIONS]
    [FILES_MATCHING]
    [PATTERN <glob-pattern> ...]
    [REGEX <regex-pattern> ...]
    [EXCLUDE <regex-pattern> ...]
    [OPTIONAL]
    [CONFIGURATIONS [Debug|Release|...]]
    [COMPONENT <component>]
    [NAMELINK_COMPONENT <component>]
    [NAMELINK_SKIP|NAMELINK_ONLY]
)
```

#### Exemplo: Instalando Diretórios de Configuração

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureApp C CXX)

# Instalar diretório de configuração com permissões seguras
install(
    DIRECTORY config/
    DESTINATION etc/myapp
    USE_SOURCE_PERMISSIONS
    PATTERN "*.conf"
    PATTERN "*.template"
    PATTERN "*.example" EXCLUDE
)

# Instalar recursos (templates, assets)
install(
    DIRECTORY resources/
    DESTINATION share/myapp/resources
    FILES_MATCHING
    PATTERN "*.png"
    PATTERN "*.svg"
    PATTERN "*.css"
    PATTERN "*.js"
)

# Instalar scripts com permissão executável restrita
install(
    DIRECTORY scripts/
    DESTINATION libexec/myapp
    DIRECTORY_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                         GROUP_READ GROUP_EXECUTE
    FILE_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                     GROUP_READ GROUP_EXECUTE
    PATTERN "*.sh"
    PATTERN "*.py"
)

# Instalar documentação
install(
    DIRECTORY docs/
    DESTINATION share/doc/myapp
    PATTERN "*.md"
    PATTERN "*.txt"
    PATTERN "html" EXCLUDE
)
```

#### Padrões de Inclusão e Exclusão

O uso correto de `PATTERN` e `REGEX` é essencial para evitar a instalação de arquivos sensíveis:

```cmake
# CORRETO: Usar FILES_MATCHING para filtrar apenas tipos específicos
install(
    DIRECTORY config/
    DESTINATION etc/myapp
    FILES_MATCHING
    PATTERN "*.conf"
    PATTERN "*.json"
)

# INCORRETO: Instalar tudo e confiar que não há arquivos sensíveis
install(
    DIRECTORY config/
    DESTINATION etc/myapp
)

# CORRETO: Excluir arquivos sensíveis explicitamente
install(
    DIRECTORY config/
    DESTINATION etc/myapp
    EXCLUDE "\\.env$"
    EXCLUDE "\\.key$"
    EXCLUDE "\\.pem$"
    EXCLUDE "\\.secret$"
)
```

### install(FILES): Instalando Arquivos Individuais

A variante `install(FILES)` é usada para instalar arquivos específicos, quando você precisa de controle granular.

#### Sintaxe

```cmake
install(
    FILES <file>...
    [TYPE <type> | DESTINATION <dir>]
    [PERMISSIONS <permissions>...]
    [CONFIGURATIONS [Debug|Release|...]]
    [COMPONENT <component>]
    [EXCLUDE_FROM_ALL]
    [RENAME <new-name>]
    [OPTIONAL]
)
```

#### Exemplo: Instalando Arquivos de Configuração Sensíveis

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureConfig C CXX)

# Gerar arquivo de configuração a partir de template
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/config/app.conf.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated/app.conf
    @ONLY
)

# Instalar configuração gerada com permissões restritas
install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/generated/app.conf
    DESTINATION etc/myapp
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ
    COMPONENT config
)

# Instalar certificados com permissões extremamente restritas
install(
    FILES
        certs/ca-bundle.crt
        certs/server.crt
    DESTINATION share/myapp/certs
    PERMISSIONS OWNER_READ GROUP_READ
    COMPONENT certificates
)

# Instalar chave privada com permissões máxima restrita
install(
    FILES certs/server.key
    DESTINATION share/myapp/certs
    PERMISSIONS OWNER_READ OWNER_WRITE
    COMPONENT private-keys
)

# Instalar README e LICENSE
install(
    FILES README.md LICENSE COPYING
    DESTINATION share/doc/myapp
    PERMISSIONS OWNER_READ GROUP_READ WORLD_READ
    COMPONENT documentation
)

# Instalar arquivo de configuração de systemd
install(
    FILES systemd/myapp.service
    DESTINATION ${CMAKE_INSTALL_PREFIX}/lib/systemd/system
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ
    COMPONENT service
)
```

### Dicas de Segurança para install()

#### Regra 1: Sempre Especifique DESTINATION

```cmake
# INSEGURO: Sem DESTINATION, depende do path do arquivo
install(FILES myconfig.conf)

# SEGURO: Sempre especifique DESTINATION explícito
install(FILES myconfig.conf DESTINATION etc/myapp)
```

#### Regra 2: Use COMPONENTS para Controle Granular

```cmake
# SEGURO: Componentes permite instalar apenas o necessário
install(TARGETS myapp
    RUNTIME DESTINATION bin
    COMPONENT runtime
)
install(FILES config/app.conf
    DESTINATION etc/myapp
    COMPONENT config
)
```

#### Regra 3: Nunca Use `install(CODE)` sem Necessidade

```cmake
# PERIGOSO: install(CODE) pode executar comandos arbitrários
install(CODE "execute_process(COMMAND curl https://example.com/config)")
```

#### Regra 4: Valide Permissões

```cmake
# Use permissões mínimas necessárias
install(
    FILES secrets.key
    DESTINATION etc/myapp
    PERMISSIONS OWNER_READ OWNER_WRITE
    # NÃO: WORLD_READ, WORLD_WRITE, WORLD_EXECUTE
)
```

#### Regra 5: Evite Path Traversal em install()

```cmake
# PERIGOSO: path relativo pode causar traversal
install(FILES config.conf DESTINATION "../../etc")

# SEGURO: sempre caminho absoluto ou relativo simples
install(FILES config.conf DESTINATION etc/myapp)
```

### install(TARGETS) com NAMELINK

Em sistemas Unix, `NAMELINK` controla a criação de symlinks para bibliotecas:

```cmake
# Criar biblioteca com versionamento
add_library(mylib SHARED lib.cpp)
set_target_properties(mylib PROPERTIES
    VERSION 1.2.3
    SOVERSION 1
)

# Instalar com namelinks
install(
    TARGETS mylib
    LIBRARY DESTINATION lib
    NAMELINK_COMPONENT mylib-namelink
)

# Resultado em /usr/local/lib:
# libmylib.so -> libmylib.so.1
# libmylib.so.1 -> libmylib.so.1.2.3
# libmylib.so.1.2.3
```

### install(TARGETS) com EXPORT

O sistema de export do CMake permite que outras instalações do CMake encontrem sua biblioteca:

```cmake
# Criar target e export
install(
    TARGETS mylib
    EXPORT mylib-export
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib/static
    INCLUDES DESTINATION include
)

# Gerar arquivo de export
install(
    EXPORT mylib-export
    FILE mylib-config.cmake
    NAMESPACE MyLib::
    DESTINATION lib/cmake/mylib
)

# Gerar arquivo de versão
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/mylib-config-version.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
install(
    FILES "${CMAKE_CURRENT_BINARY_DIR}/mylib-config-version.cmake"
    DESTINATION lib/cmake/mylib
)
```

### Validação Pós-Instalação

CMake pode executar scripts de validação após a instalação:

```cmake
# Script de validação
file(WRITE ${CMAKE_CURRENT_BINARY_DIR}/validate_install.cmake
[=[
    # Verificar se arquivos foram instalados
    if(NOT EXISTS "${CMAKE_INSTALL_PREFIX}/bin/myapp")
        message(FATAL_ERROR "myapp não foi instalado corretamente")
    endif()

    # Verificar permissões do binário
    file(READ "${CMAKE_INSTALL_PREFIX}/bin/myapp" content)
    if(NOT content)
        message(FATAL_ERROR "myapp está vazio ou inacessível")
    endif()

    message(STATUS "Instalação validada com sucesso")
]=])

install(SCRIPT ${CMAKE_CURRENT_BINARY_DIR}/validate_install.cmake)
```

---

## 15.3 CMAKE_INSTALL_PREFIX vs DESTDIR

### Entendendo os Dois Conceitos

A confusão entre `CMAKE_INSTALL_PREFIX` e `DESTDIR` é uma das fontes mais comuns de erros em instalações de software. Vamos esclarecer cada um.

#### CMAKE_INSTALL_PREFIX

`CMAKE_INSTALL_PREFIX` é o caminho base onde o software será instalado. Ele é embutido no build durante a configuração e afeta caminhos relativos nos arquivos gerados.

```cmake
# Configurar prefixo durante a configuração
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..

# Usar na instalação
cmake --install . --prefix /opt/myapp
```

**Valores padrão:**
- Linux: `/usr/local`
- Windows: `C:/Program Files/${PROJECT_NAME}`
- macOS: `/usr/local` ou `/Library/Frameworks`

**Importante:** O `CMAKE_INSTALL_PREFIX` afeta diretamente os binários instalados, especialmente:
- RPATH de binários (embedded RPATH)
- Caminhos hardcoded em scripts de shell
- Localização de arquivos de configuração

#### DESTDIR

`DESTDIR` é um prefixo temporário usado para instalação staging. Ele NÃO é embutido nos binários — é uma camada de abstração para instalação em diretórios temporários.

```bash
# Instalar em staging directory (DESTDIR)
DESTDIR=/tmp/staging cmake --install .

# Resultado: arquivos em /tmp/staging/usr/local/bin/
```

**Diferença Fundamental:**

```cmake
# COM CMAKE_INSTALL_PREFIX=/usr/local
# O binário terá RPATH: /usr/local/lib

# COM DESTDIR=/tmp/staging E CMAKE_INSTALL_PREFIX=/usr/local
# O binário terá RPATH: /usr/local/lib (NÃO /tmp/staging/usr/local/lib)
# Mas os arquivos serão escritos em /tmp/staging/usr/local/bin/
```

### Cenário 1: Instalação Local (Desenvolvimento)

```bash
# Configurar com prefixo local
cmake -B build -DCMAKE_INSTALL_PREFIX=$HOME/.local ..

# Build
cmake --build build

# Instalar
cmake --install build

# Resultado:
# ~/.local/bin/myapp
# ~/.local/lib/libmylib.so
# ~/.local/include/mylib/
```

### Cenário 2: Instalação com DESTDIR (Pacotes)

```bash
# Configurar com prefixo do sistema
cmake -B build -DCMAKE_INSTALL_PREFIX=/usr ..

# Build
cmake --build build

# Instalar em staging para pacote
DESTDIR=/tmp/myapp-1.0.0 cmake --install build

# Resultado:
# /tmp/myapp-1.0.0/usr/bin/myapp
# /tmp/myapp-1.0.0/usr/lib/libmylib.so
# /tmp/myapp-1.0.0/usr/include/mylib/
```

### Cenário 3: Instalação Cross-Compilation

```bash
# Para cross-compilation, DESTDIR é essencial
# O prefixo é para o target, DESTDIR é para o host

# Configurar
cmake -B build \
    -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake \
    -DCMAKE_INSTALL_PREFIX=/usr \
    ..

# Build
cmake --build build

# Instalar em staging
DESTDIR=/tmp/target-root cmake --install build
```

### Proteção contra Path Injection

Um erro comum é usar `DESTDIR` de forma insegura, permitindo path injection:

```cmake
# INSEGURO: Usar DESTDIR diretamente em paths
set(MY_INSTALL_DIR "${DESTDIR}${CMAKE_INSTALL_PREFIX}")

# SEGURO: Deixar o CMake gerenciar os paths
install(TARGETS myapp RUNTIME DESTINATION bin)
# O CMake automaticamente prefixa com DESTDIR quando definido
```

### Validação de Paths de Instalação

```cmake
# Script de validação para garantir paths seguros
function(validate_install_paths)
    # Verificar que o prefixo não é vazio
    if("${CMAKE_INSTALL_PREFIX}" STREQUAL "")
        message(FATAL_ERROR "CMAKE_INSTALL_PREFIX não pode ser vazio")
    endif()

    # Verificar que o prefixo é um caminho absoluto
    if(NOT IS_ABSOLUTE "${CMAKE_INSTALL_PREFIX}")
        message(FATAL_ERROR "CMAKE_INSTALL_PREFIX deve ser caminho absoluto")
    endif()

    # Verificar que não há path traversal
    string(FIND "${CMAKE_INSTALL_PREFIX}" ".." _found)
    if(NOT _found EQUAL -1)
        message(FATAL_ERROR "CMAKE_INSTALL_PREFIX contém path traversal")
    endif()

    message(STATUS "CMAKE_INSTALL_PREFIX: ${CMAKE_INSTALL_PREFIX}")
endfunction()

validate_install_paths()
```

### CMAKE_INSTALL_PREFIX vs Prefix Fixo

Em alguns cenários, você pode querer forçar um prefixo específico:

```cmake
# Opção 1: Usar CMAKE_INSTALL_PREFIX com valor padrão
if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set(CMAKE_INSTALL_PREFIX "/usr/local" CACHE PATH "Install prefix" FORCE)
endif()

# Opção 2: Usar prefixo fixo para conformidade
set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "Install prefix" FORCE)

# Opção 3: Permitir override apenas em builds de desenvolvimento
option(ENABLE_DEVELOPER_INSTALL "Use developer install prefix" OFF)
if(ENABLE_DEVELOPER_INSTALL)
    set(CMAKE_INSTALL_PREFIX "$ENV{HOME}/.local" CACHE PATH "Install prefix" FORCE)
else()
    set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "Install prefix" FORCE)
endif()
```

### Variáveis Derivadas de CMAKE_INSTALL_PREFIX

O CMake usa `CMAKE_INSTALL_PREFIX` para calcular outros caminhos importantes:

```cmake
# CMAKE_INSTALL_PREFIX afeta:
# - CMAKE_INSTALL_BINDIR
# - CMAKE_INSTALL_LIBDIR
# - CMAKE_INSTALL_INCLUDEDIR
# - CMAKE_INSTALL_DATAROOTDIR
# E muitos outros via GNUInstallDirs

# Verificar caminhos resultantes
message(STATUS "BIN: ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_BINDIR}")
message(STATUS "LIB: ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}")
message(STATUS "INCLUDE: ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_INCLUDEDIR}")
```

---

## 15.4 GNUInstallDirs: Padrão de Instalação

### Por que GNUInstallDirs?

O módulo `GNUInstallDirs` define padrões de instalação que seguem as convenções do sistema de arquivos do Linux (Filesystem Hierarchy Standard - FHS). Usar esses padrões é essencial para:

- Conformidade com pacotes do sistema
- Compatibilidade com ferramentas de gerenciamento de pacotes
- Integração com scripts de instalação automáticos
- Prevenção de conflitos com outros pacotes

### Ativação e Uso

```cmake
# Incluir módulo (após project())
include(GNUInstallDirs)

# Os seguintes diretórios estão disponíveis:
# CMAKE_INSTALL_BINDIR     - binários executáveis (bin)
# CMAKE_INSTALL_SBINDIR    - binários do sistema (sbin)
# CMAKE_INSTALL_LIBEXECDIR - executáveis de suporte (libexec)
# CMAKE_INSTALL_LIBDIR     - bibliotecas (lib, lib64)
# CMAKE_INSTALL_INCLUDEDIR - headers (include)
# CMAKE_INSTALL_DATAROOTDIR - dados compartilhados (share)
# CMAKE_INSTALL_DATADIR    - dados do pacote
# CMAKE_INSTALL_MANDIR     - manual pages
# CMAKE_INSTALL_INFODIR    - documentação info
# CMAKE_INSTALL_LOCALEDIR  - arquivos de locale
# CMAKE_INSTALL_DOCDIR     - documentação
# CMAKE_INSTALL_SYSTEMDSDIR - arquivos systemd
```

### Exemplo Completo com GNUInstallDirs

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyApp VERSION 2.1.0 LANGUAGES C CXX)

include(GNUInstallDirs)

# Criar executável
add_executable(myapp
    src/main.cpp
    src/config.cpp
    src/network.cpp
)

# Configurar propriedades
set_target_properties(myapp PROPERTIES
    VERSION ${PROJECT_VERSION}
    INSTALL_RPATH "$ORIGIN/../lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# Instalar executável
install(TARGETS myapp RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})

# Instalar headers
install(
    FILES
        include/myapp/config.h
        include/myapp/network.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/myapp
)

# Instalar configuração
install(
    FILES config/myapp.conf
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}
)

# Instalar documentação
install(
    FILES README.md
    DESTINATION ${CMAKE_INSTALL_DOCDIR}
)

# Instalar man page
install(
    FILES doc/myapp.1
    DESTINATION ${CMAKE_INSTALL_MANDIR}/man1
)

# Instalar desktop file (Linux)
install(
    FILES desktop/myapp.desktop
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/applications
)

# Instalar icons
install(
    FILES icons/myapp.png
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/icons/hicolor/256x256/apps
)
```

### Personalização de GNUInstallDirs

```cmake
include(GNUInstallDirs)

# Personalizar diretórios para conformidade específica
set(CMAKE_INSTALL_LIBDIR "lib/myapp-${PROJECT_VERSION}" CACHE PATH
    "Library installation directory" FORCE)

# Usar arquitetura específica
set(CMAKE_INSTALL_LIBDIR "lib/${CMAKE_LIBRARY_ARCHITECTURE}" CACHE PATH
    "Library directory with multiarch suffix" FORCE)

# Para sistemas que usam lib64
if(CMAKE_SIZEOF_VOID_P EQUAL 8 AND NOT DEFINED CMAKE_INSTALL_LIBDIR)
    set(CMAKE_INSTALL_LIBDIR "lib64")
endif()
```

### Caminhos Absolutos vs Relativos

```cmake
include(GNUInstallDirs)

# CMAKE_INSTALL_BINDIR pode ser relativo ou absoluto
# Para instalação no sistema, geralmente é relativo a CMAKE_INSTALL_PREFIX

# Verificar se é relativo
if(NOT IS_ABSOLUTE "${CMAKE_INSTALL_BINDIR}")
    message(STATUS "BINDIR é relativo: ${CMAKE_INSTALL_BINDIR}")
    message(STATUS "Caminho completo: ${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_BINDIR}")
endif()

# Para cross-compilation, pode ser necessário forçar caminhos absolutos
if(CMAKE_CROSSCOMPILING)
    set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "Target install prefix" FORCE)
endif()
```

### Integração com Outros Módulos

```cmake
# GNUInstallDirs pode ser combinado com outros módulos

# Com CMakePackageConfigHelpers
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

# Gerar arquivo de versão
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/mylib-config-version.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

# Instalar em caminho padrão
install(
    FILES "${CMAKE_INSTALL_PREFIX}/${CMAKE_INSTALL_LIBDIR}/cmake/mylib/mylib-config-version.cmake"
    DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/mylib"
)
```

---

## 15.5 Component-based Installation

### O Conceito de Componentes

Componentes permitem dividir a instalação em partes modulares, cada uma podendo ser instalada ou desinstalada independentemente. Isso é essencial para:

- Pacotes de distribuição (pacotes -dev, -doc, -dbg)
- Instalação parcial em ambientes restritos
- Controle granular de permissões por componente
- Build systems de integração contínua

### Definindo Componentes

```cmake
# Componentes são definidos com a propriedade COMPONENT
install(
    TARGETS mylib
    LIBRARY DESTINATION lib
    COMPONENT runtime
)

install(
    FILES include/mylib.h
    DESTINATION include
    COMPONENT dev
)

install(
    FILES doc/mylib.1
    DESTINATION share/man/man1
    COMPONENT doc
)

install(
    FILES examples/basic.cpp
    DESTINATION share/mylib/examples
    COMPONENT examples
)
```

### Instalação por Componente

```bash
# Listar componentes disponíveis
cmake --install build --component help

# Instalar apenas um componente específico
cmake --install build --component runtime
cmake --install build --component dev
cmake --install build --component doc

# Instalar tudo (comportamento padrão)
cmake --install build
```

### Componentes com DESTDIR

```bash
# Instalar componentes específicos em staging
DESTDIR=/tmp/staging cmake --install build --component runtime
DESTDIR=/tmp/staging cmake --install build --component dev

# Criar pacote apenas com runtime
cd /tmp/staging && tar czf myapp-runtime.tar.gz .
```

### Componentes e Permissões

Componentes permitem diferentes permissões para diferentes partes:

```cmake
# Binários - permissões normais
install(
    TARGETS myapp
    RUNTIME DESTINATION bin
    PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE
                GROUP_READ GROUP_EXECUTE
    COMPONENT runtime
)

# Configuração - permissões restritas
install(
    FILES config/app.conf
    DESTINATION etc/myapp
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ
    COMPONENT config
)

# Documentação - permissões públicas
install(
    FILES README.md
    DESTINATION share/doc/myapp
    PERMISSIONS OWNER_READ GROUP_READ WORLD_READ
    COMPONENT documentation
)
```

### Componentes e CPack

Componentes se integram perfeitamente com CPack para criação de pacotes:

```cmake
# Configurar CPack com componentes
set(CPACK_GENERATOR "DEB;RPM;TGZ")

# Componentes do CPack
set(CPACK_DEB_COMPONENT_INSTALL ON)
set(CPACK_RPM_COMPONENT_INSTALL ON)

# Componente runtime
set(CPACK_DEBIAN_RUNTIME_PACKAGE_NAME "myapp")
set(CPACK_DEBIAN_RUNTIME_PACKAGE_DEPENDS "libc6 (>= 2.17)")

# Componente dev
set(CPACK_DEBIAN_DEV_PACKAGE_NAME "myapp-dev")
set(CPACK_DEBIAN_DEV_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")

include(CPack)
```

### Validação de Componentes

```cmake
# Script para validar que componentes essenciais existem
function(validate_components)
    set(_required_components runtime config)

    foreach(_comp ${_required_components})
        # Verificar se há arquivos para este componente
        string(TOUPPER "${_comp}" _comp_upper)
        set(_component_files "_CPACK_INSTALL_COMPONENTS_${_comp_upper}")

        if(NOT ${_component_files})
            message(WARNING "Componente '${_comp}' não tem arquivos instalados")
        endif()
    endforeach()
endfunction()

validate_components()
```

---

## 15.6 RPATH: Configuração e Segurança

### O Que é RPATH?

RPATH (Runtime Path) é uma lista de diretórios embutida no executável que o sistema operacional usa para encontrar bibliotecas compartilhadas durante a execução. A configuração incorreta de RPATH pode criar vulnerabilidades sérias.

### Tipos de Path de Biblioteca

O Linux busca bibliotecas nesta ordem:

1. **LD_LIBRARY_PATH** - Variável de ambiente (perigosa se configurada incorretamente)
2. **RUNPATH** - Embutido no ELF, por biblioteca (não herdado)
3. **RPATH** - Embutido no ELF, herdado por dependências
4. **/etc/ld.so.cache** - Cache do ldconfig
5. **/lib, /usr/lib** - Diretórios padrão

### Configurando RPATH no CMake

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureRPATH C CXX)

add_executable(myapp main.cpp)
add_library(mylib SHARED lib.cpp)

# Configurar RPATH para instalação
set_target_properties(mylib PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
    INSTALL_RPATH "$ORIGIN/../lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)
```

### Opções de RPATH

```cmake
# INSTALL_RPATH - RPATH para build tree
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib;/opt/myapp/lib"
)

# INSTALL_RPATH_USE_LINK_PATH - Adicionar diretórios de link ao RPATH
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# BUILD_RPATH - RPATH para build tree
set_target_properties(myapp PROPERTIES
    BUILD_RPATH "${CMAKE_BINARY_DIR}/lib"
)

# SKIP_BUILD_RPATH - Não gerar RPATH no build
set_target_properties(myapp PROPERTIES
    SKIP_BUILD_RPATH TRUE
)

# CMAKE_SKIP_RPATH - Pular RPATH globalmente
set(CMAKE_SKIP_RPATH TRUE)

# CMAKE_SKIP_INSTALL_RPATH - Pular RPATH na instalação
set(CMAKE_SKIP_INSTALL_RPATH TRUE)
```

### Vulnerabilidades de RPATH

#### Vulnerabilidade 1: Library Path Injection

```cmake
# PERIGOSO: RPATH com path relativo sem $ORIGIN
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "/tmp/fake"  # Atacante pode criar /tmp/fake com library maliciosa
)
```

#### Vulnerabilidade 2: world-writable RPATH

```cmake
# PERIGOSO: Diretório world-writable no RPATH
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "/tmp/shared"  # /tmp/shared pode ser world-writable
)
```

#### Vulnerabilidade 3: RPATH com LD_LIBRARY_PATH

```cmake
# PERIGOSO: Depender de LD_LIBRARY_PATH
# O atacante pode definir LD_LIBRARY_PATH para carregar libraries maliciosas
```

### Boas Práticas de RPATH

```cmake
# SEGURO: Usar $ORIGIN para paths relativos
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
)

# SEGURO: Usar path absoluto para instalação no sistema
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "${CMAKE_INSTALL_PREFIX}/lib"
)

# SEGURO: Combinar $ORIGIN com path absoluto
set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib;${CMAKE_INSTALL_PREFIX}/lib"
)

# Verificar RPATH após instalação
add_custom_target(verify_rpath
    COMMAND readelf -d $<TARGET_FILE:myapp> | grep RPATH
    COMMENT "Verificando RPATH do binário"
)
```

### RPATH para Cross-Compilation

```cmake
# Para cross-compilation, RPATH deve ser configurado para o target
if(CMAKE_CROSSCOMPILING)
    set(CMAKE_INSTALL_RPATH "/usr/lib/${CMAKE_LIBRARY_ARCHITECTURE}")
else()
    set(CMAKE_INSTALL_RPATH "$ORIGIN/../lib")
endif()

set(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)
```

### Validação de RPATH

```cmake
# Script para validar RPATH
function(validate_rpath target)
    add_custom_command(TARGET ${target} POST_BUILD
        COMMAND readelf -d $<TARGET_FILE:${target}>
        COMMAND grep -q "RPATH"
        COMMENT "Validando RPATH de ${target}"
    )
endfunction()

validate_rpath(myapp)
```

---

## 15.7 CPack: Geradores (DEB, RPM, NSIS, TGZ)

### Introdução ao CPack

CPack é o gerador de pacotes do CMake, capaz de criar pacotes para múltiplas distribuições e sistemas operacionais a partir da mesma configuração de build. É a ferramenta ideal para distribuição segura de software.

### Configuração Básica do CPack

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyApp VERSION 1.0.0 LANGUAGES C CXX)

# ... configuração do projeto ...

# Habilitar CPack
include(CPack)

# Configurações básicas
set(CPACK_PACKAGE_NAME "myapp")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Meu aplicativo seguro")
set(CPACK_PACKAGE_VENDOR "Minha Empresa")
set(CPACK_PACKAGE_CONTACT "admin@minhaempresa.com")
set(CPACK_PACKAGE_HOMEPAGE_URL "https://myapp.example.com")
```

### Gerador DEB (Debian/Ubuntu)

```cmake
# Configuração para pacotes Debian
set(CPACK_GENERATOR "DEB")

set(CPACK_DEBIAN_PACKAGE_NAME "myapp")
set(CPACK_DEBIAN_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_DEBIAN_PACKAGE_SECTION "utils")
set(CPACK_DEBIAN_PACKAGE_PRIORITY "optional")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libc6 (>= 2.17), libstdc++6 (>= 11)")
set(CPACK_DEBIAN_PACKAGE_RECOMMENDS "myapp-doc")
set(CPACK_DEBIAN_PACKAGE_SUGGESTS "myapp-dev")

# Controle de qualidade
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)
set(CPACK_DEBIAN_PACKAGE_DEBUG ON)

# Arquitetura
set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "amd64")

# Assinatura
set(CPACK_DEBIAN_PACKAGE_DISTRIBUTION "jammy")
```

### Gerador RPM (Red Hat/CentOS/Fedora)

```cmake
# Configuração para pacotes RPM
set(CPACK_GENERATOR "RPM")

set(CPACK_RPM_PACKAGE_NAME "myapp")
set(CPACK_RPM_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_RPM_PACKAGE_RELEASE "1")
set(CPACK_RPM_PACKAGE_LICENSE "MIT")
set(CPACK_RPM_PACKAGE_GROUP "Applications/System")
set(CPACK_RPM_PACKAGE_URL "https://myapp.example.com")
set(CPACK_RPM_PACKAGE_DESCRIPTION "Meu aplicativo seguro")

# Dependências
set(CPACK_RPM_PACKAGE_REQUIRES "glibc >= 2.17, libstdc++ >= 11")

# Auto-dependências
set(CPACK_RPM_PACKAGE_AUTOREQ ON)
set(CPACK_RPM_PACKAGE_AUTOPROV ON)

# Controle de qualidade
set(CPACK_RPM_PACKAGE_DEBUG ON)

# Arquitetura
set(CPACK_RPM_PACKAGE_ARCHITECTURE "x86_64")
```

### Gerador TGZ (Tarball)

```cmake
# Configuração para tarball
set(CPACK_GENERATOR "TGZ")

set(CPACK_ARCHIVE_COMPONENT_INSTALL ON)
set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY ON)
set(CPACK_STRIP_FILES OFF)  # Manter symbols para debug
```

### Gerador NSIS (Windows)

```cmake
# Configuração para NSIS (Windows Installer)
set(CPACK_GENERATOR "NSIS")

set(CPACK_NSIS_PACKAGE_NAME "MyApp")
set(CPACK_NSIS_DISPLAY_NAME "MyApp ${PROJECT_VERSION}")
set(CPACK_NSIS_PUBLISHER "Minha Empresa")
set(CPACK_NSIS_URL_INFO_ABOUT "https://myapp.example.com")
set(CPACK_NSIS_HELP_LINK "https://myapp.example.com/support")
set(CPACK_NSIS_CONTACT "support@minhaempresa.com")

# Ícone
set(CPACK_NSIS_ICON "${CMAKE_SOURCE_DIR}/icons/myapp.ico")

# Diretório de instalação
set(CPACK_NSIS_INSTALL_ROOT "$PROGRAMFILES")

# Comandos pós-instalação
set(CPACK_NSIS_EXECUTABLES_DIRECTORY "bin")
set(CPACK_NSIS_ICONS_EXTRA "Desktop;StartMenu")
```

### Gerador WIX (Windows MSI)

```cmake
# Configuração para WIX (Windows MSI)
set(CPACK_GENERATOR "WIX")

set(CPACK_WIX_PRODUCT_GUID "YOUR-GUID-HERE")
set(CPACK_WIX_UPGRADE_GUID "YOUR-UPGRADE-GUID")
set(CPACK_WIX_PRODUCT_NAME "MyApp")
set(CPACK_WIX_MANUFACTURER "Minha Empresa")
set(CPACK_WIX_PROGRAM_LIST_FOLDER "MyFolder")

# Ícone
set(CPACK_WIX_PRODUCT_ICON "${CMAKE_SOURCE_DIR}/icons/myapp.ico")
```

### Gerando Pacotes

```bash
# Gerar pacote para o gerador padrão
cpack

# Gerar pacote específico
cpack -G DEB

# Gerar pacote com diretório de saída específico
cpack -G DEB -B ${CMAKE_BINARY_DIR}/packages

# Gerar pacote com verbose
cpack -G DEB --verbose

# Gerar pacote a partir de build directory
cd build && cpack -G DEB
```

### Múltiplos Geradores

```cmake
# Habilitar múltiplos geradores
set(CPACK_GENERATOR "DEB;RPM;TGZ")

# Gerar todos os pacotes
# cpkgerará myapp-1.0.0-Linux.deb, myapp-1.0.0-Linux.rpm, myapp-1.0.0-Linux.tar.gz
```

---

## 15.8 CPack Variables: CPACK_PACKAGE_*, CPACK_GENERATOR

### Variáveis Essenciais do CPack

#### Metadados do Pacote

```cmake
# Nome do pacote (obrigatório)
set(CPACK_PACKAGE_NAME "myapp")

# Versão do pacote
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")

# Build number (para.rpm)
set(CPACK_PACKAGE_VERSION_MAJOR "1")
set(CPACK_PACKAGE_VERSION_MINOR "0")
set(CPACK_PACKAGE_VERSION_PATCH "0")

# Descrição resumida
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Meu aplicativo seguro e eficiente")

# Descrição completa
set(CPACK_PACKAGE_DESCRIPTION
    "MyApp é um aplicativo que fornece funcionalidades seguras
     de processamento de dados com suporte a múltiplos formatos.")

# Licença
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_SOURCE_DIR}/LICENSE")

# Vendendor
set(CPACK_PACKAGE_VENDOR "Minha Empresa Ltda")

# Contato
set(CPACK_PACKAGE_CONTACT "admin@minhaempresa.com")

# Homepage
set(CPACK_PACKAGE_HOMEPAGE_URL "https://myapp.example.com")

# Grupo (para RPM)
set(CPACK_RPM_PACKAGE_GROUP "Applications/System")

# Seção (para DEB)
set(CPACK_DEBIAN_PACKAGE_SECTION "utils")
```

#### Informações de Arquitetura

```cmake
# Arquitetura do pacote
# Opções: amd64, i386, arm64, armhf, all, any
set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "${CMAKE_SYSTEM_PROCESSOR}")
set(CPACK_RPM_PACKAGE_ARCHITECTURE "${CMAKE_SYSTEM_PROCESSOR}")

# Para pacotes multi-arquitetura
if(CMAKE_SIZEOF_VOID_P EQUAL 8)
    set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "amd64")
    set(CPACK_RPM_PACKAGE_ARCHITECTURE "x86_64")
else()
    set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "i386")
    set(CPACK_RPM_PACKAGE_ARCHITECTURE "i686")
endif()
```

#### Dependências

```cmake
# Dependências Debian
set(CPACK_DEBIAN_PACKAGE_DEPENDS
    "libc6 (>= 2.17),
     libstdc++6 (>= 11),
     libssl3 (>= 3.0.0)")

# Dependências RPM
set(CPACK_RPM_PACKAGE_REQUIRES
    "glibc >= 2.17,
     libstdc++ >= 11,
     openssl >= 3.0.0")

# Recomendados (DEB)
set(CPACK_DEBIAN_PACKAGE_RECOMMENDS "myapp-doc, myapp-dev")

# Sugestões (DEB)
set(CPACK_DEBIAN_PACKAGE_SUGGESTS "myapp-extras")

# Conflitos (RPM)
set(CPACK_RPM_PACKAGE_CONFLICTS "myapp-legacy")

# Provides (RPM)
set(CPACK_RPM_PACKAGE_PROVIDES "myapp-api = ${PROJECT_VERSION}")
```

#### Diretórios de Instalação

```cmake
# Prefixo de instalação
set(CPACK_PACKAGING_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Usar GNUInstallDirs para consistência
include(GNUInstallDirs)
set(CPACK_PACKAGING_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")
```

#### Comportamento do Pacote

```cmake
# Strip binaries
set(CPACK_STRIP_FILES ON)

# Manter debug info em pacote separado
set(CPACK_STRIP_FILES OFF)

# Gerar package debug
set(CPACK_DEBIAN_DEBUG_PACKAGE_NAME "myapp-dbg")
set(CPACK_RPM_DEBUGINFO_PACKAGE ON)

# Arquitetura do pacote (para cross-compilation)
set(CPACK_PACKAGE_FILE_NAME
    "${CPACK_PACKAGE_NAME}-${CPACK_PACKAGE_VERSION}-${CMAKE_SYSTEM_NAME}-${CMAKE_SYSTEM_PROCESSOR}")
```

#### Controle de Versão

```cmake
# Gerar package version file
include(CMakePackageConfigHelpers)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/myapp-config-version.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)
```

### Variáveis Específicas por Gerador

#### DEB Específicas

```cmake
set(CPACK_DEBIAN_PACKAGE_NAME "myapp")
set(CPACK_DEBIAN_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_DEBIAN_PACKAGE_RELEASE "1")
set(CPACK_DEBIAN_PACKAGE_DISTRIBUTION "jammy")
set(CPACK_DEBIAN_PACKAGE_SECTION "utils")
set(CPACK_DEBIAN_PACKAGE_PRIORITY "optional")
set(CPACK_DEBIAN_PACKAGE_MAINTAINER "Minha Empresa <admin@minhaempresa.com>")
set(CPACK_DEBIAN_PACKAGE_DESCRIPTION "MyApp - Aplicativo seguro")
set(CPACK_DEBIAN_PACKAGE_HOMEPAGE "https://myapp.example.com")
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)
set(CPACK_DEBIAN_PACKAGE_PREDEPENDS "debconf (>= 0.5) | debconf-2.0")
set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA
    "${CMAKE_SOURCE_DIR}/debian/postinst;${CMAKE_SOURCE_DIR}/debian/postrm")
```

#### RPM Específicas

```cmake
set(CPACK_RPM_PACKAGE_NAME "myapp")
set(CPACK_RPM_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_RPM_PACKAGE_RELEASE "1")
set(CPACK_RPM_PACKAGE_LICENSE "MIT")
set(CPACK_RPM_PACKAGE_GROUP "Applications/System")
set(CPACK_RPM_PACKAGE_URL "https://myapp.example.com")
set(CPACK_RPM_PACKAGE_DESCRIPTION "Meu aplicativo seguro")
set(CPACK_RPM_PACKAGE_REQUIRES "glibc >= 2.17")
set(CPACK_RPM_PACKAGE_SUGGESTS "myapp-doc")
set(CPACK_RPM_PACKAGE_CONFLICTS "myapp-legacy")
set(CPACK_RPM_PACKAGE_AUTOREQ ON)
set(CPACK_RPM_PACKAGE_AUTOPROV ON)
set(CPACK_RPM_PACKAGE_DEBUGINFO_PACKAGE ON)
set(CPACK_RPM_PACKAGE_POST_INSTALL_SCRIPT_FILE
    "${CMAKE_SOURCE_DIR}/rpm/postinst.sh")
set(CPACK_RPM_PACKAGE_PRE_UNINSTALL_SCRIPT_FILE
    "${CMAKE_SOURCE_DIR}/rpm/preuninstall.sh")
```

#### NSIS Específicas

```cmake
set(CPACK_NSIS_PACKAGE_NAME "MyApp")
set(CPACK_NSIS_DISPLAY_NAME "MyApp ${PROJECT_VERSION}")
set(CPACK_NSIS_PUBLISHER "Minha Empresa")
set(CPACK_NSIS_URL_INFO_ABOUT "https://myapp.example.com")
set(CPACK_NSIS_HELP_LINK "https://myapp.example.com/support")
set(CPACK_NSIS_CONTACT "support@minhaempresa.com")
set(CPACK_NSIS_INSTALL_ROOT "$PROGRAMFILES")
set(CPACK_NSIS_EXECUTABLES_DIRECTORY "bin")
set(CPACK_NSIS_ICONS_EXTRA "Desktop;StartMenu")
```

---

## 15.9 CPack Component Groups

### Conceito de Component Groups

Component groups permitem organizar componentes em categorias lógicas, facilitando a criação de pacotes modulares. Cada grupo pode ser instalado como um pacote separado.

### Definindo Componentes e Grupos

```cmake
cmake_minimum_required(VERSION 3.20)
project(ModularApp VERSION 1.0.0 LANGUAGES C CXX)

# Criar alvos
add_executable(myapp src/main.cpp)
add_library(mylib SHARED src/lib.cpp)

# Componente: runtime (binários e bibliotecas)
install(TARGETS myapp RUNTIME DESTINATION bin COMPONENT runtime)
install(TARGETS mylib LIBRARY DESTINATION lib COMPONENT runtime)

# Componente: dev (headers e arquivos de desenvolvimento)
install(FILES include/mylib.h DESTINATION include COMPONENT dev)
install(TARGETS mylib ARCHIVE DESTINATION lib COMPONENT dev)

# Componente: doc (documentação)
install(FILES README.md DESTINATION share/doc/myapp COMPONENT doc)
install(FILES doc/myapp.1 DESTINATION share/man/man1 COMPONENT doc)

# Componente: config (configuração)
install(FILES config/myapp.conf DESTINATION etc/myapp COMPONENT config)

# Componente: examples
install(FILES examples/basic.cpp DESTINATION share/myapp/examples COMPONENT examples)
```

### Definindo Grupos

```cmake
# Definir component groups
set(CPACK_COMPONENT_RUNTIME_GROUP "applications")
set(CPACK_COMPONENT_DEV_GROUP "development")
set(CPACK_COMPONENT_DOC_GROUP "documentation")
set(CPACK_COMPONENT_CONFIG_GROUP "configuration")
set(CPACK_COMPONENT_EXAMPLES_GROUP "examples")

# Configurar descrições dos grupos
set(CPACK_COMPONENT_APPLICATIONS_DESCRIPTION
    "Aplicativo principal e bibliotecas runtime")
set(CPACK_COMPONENT_DEVELOPMENT_DESCRIPTION
    "Headers e arquivos para desenvolvimento")
set(CPACK_COMPONENT_DOCUMENTATION_DESCRIPTION
    "Documentação do aplicativo")
set(CPACK_COMPONENT_CONFIGURATION_DESCRIPTION
    "Arquivos de configuração")
set(CPACK_COMPONENT_EXAMPLES_DESCRIPTION
    "Exemplos de uso")
```

### CPack com Component Groups

```cmake
# Habilitar instalação por componente
set(CPACK_DEB_COMPONENT_INSTALL ON)
set(CPACK_RPM_COMPONENT_INSTALL ON)

# Configurar pacotes Debian por componente
set(CPACK_DEBIAN_APPLICATIONS_PACKAGE_NAME "myapp")
set(CPACK_DEBIAN_APPLICATIONS_PACKAGE_DEPENDS "libc6 (>= 2.17)")

set(CPACK_DEBIAN_DEV_PACKAGE_NAME "myapp-dev")
set(CPACK_DEBIAN_DEV_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")

set(CPACK_DEBIAN_DOC_PACKAGE_NAME "myapp-doc")
set(CPACK_DEBIAN_DOC_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")

# Configurar pacotes RPM por componente
set(CPACK_RPM_APPLICATIONS_PACKAGE_NAME "myapp")
set(CPACK_RPM_APPLICATIONS_PACKAGE_REQUIRES "glibc >= 2.17")

set(CPACK_RPM_DEV_PACKAGE_NAME "myapp-devel")
set(CPACK_RPM_DEV_PACKAGE_REQUIRES "myapp = ${PROJECT_VERSION}")

set(CPACK_RPM_DOC_PACKAGE_NAME "myapp-doc")
set(CPACK_RPM_DOC_PACKAGE_REQUIRES "myapp = ${PROJECT_VERSION}")
```

### Gerando Pacotes com Component Groups

```bash
# Gerar pacote com todos os componentes
cpack -G DEB

# Gerar pacote específico de um grupo
cpack -G DEB -D CPACK_DEB_COMPONENTS=applications
cpack -G DEB -D CPACK_DEB_COMPONENTS=development

# Gerar pacote de todos os componentes de um grupo
cpack -G DEB --component runtime
```

### Validação de Component Groups

```cmake
# Script para validar component groups
function(validate_component_groups)
    set(_valid_groups applications development documentation configuration examples)

    foreach(_group ${_valid_groups})
        string(TOUPPER "${_group}" _group_upper)
        set(_group_var "CPACK_COMPONENT_${_group_upper}_GROUP")

        if(NOT DEFINED ${_group_var})
            message(WARNING "Grupo '${_group}' não definido")
        endif()
    endforeach()
endfunction()

validate_component_groups()
```

---

## 15.10 Packaging Seguro: Signing, Hash Verification

### Por que Assinar Pacotes?

A assinatura digital de pacotes é essencial para:

- **Integridade**: Garantir que o pacote não foi modificado após a criação
- **Autenticidade**: Confirmar que o pacote veio do desenvolvedor legítimo
- **Não-repúdio**: Provar quem criou o pacote
- **Conformidade**: Muitas distribuições exigem pacotes assinados

### Configuração de GPG para Assinatura

```cmake
# Script para assinatura de pacotes
function(sign_package package_file gpg_key)
    # Verificar se GPG está disponível
    find_program(GPG_EXECUTABLE gpg)
    if(NOT GPG_EXECUTABLE)
        message(WARNING "GPG não encontrado. Pacote não será assinado.")
        return()
    endif()

    # Assinar pacote
    execute_process(
        COMMAND ${GPG_EXECUTABLE} --armor --detach-sign
            --local-user ${gpg_key}
            ${package_file}
        RESULT_VARIABLE GPG_RESULT
    )

    if(NOT GPG_RESULT EQUAL 0)
        message(FATAL_ERROR "Falha ao assinar pacote: ${package_file}")
    endif()

    message(STATUS "Pacote assinado: ${package_file}.asc")
endfunction()
```

### Verificação de Hash

```cmake
# Script para gerar e verificar hashes
function(generate_package_hash package_file hash_file)
    # Gerar hash SHA256
    file(SHA256 ${package_file} _hash)

    # Escrever arquivo de hash
    file(WRITE "${hash_file}" "${_hash}  ${package_file}\n")

    message(STATUS "Hash gerado: ${_hash}")
endfunction()

function(verify_package_hash package_file hash_file)
    # Ler hash esperado
    file(READ "${hash_file}" _expected_hash)
    string(STRIP "${_expected_hash}" _expected_hash)

    # Calcular hash atual
    file(SHA256 ${package_file} _actual_hash)

    # Comparar
    if("${_expected_hash}" STREQUAL "${_actual_hash}")
        message(STATUS "Hash verificado com sucesso: ${package_file}")
        return(TRUE)
    else()
        message(FATAL_ERROR
            "Falha na verificação de hash para ${package_file}\n"
            "Esperado: ${_expected_hash}\n"
            "Atual: ${_actual_hash}")
    endif()
endfunction()
```

### Assinatura com SignPackage

```cmake
# Configurar assinatura de pacotes
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)

# Script pós-geração para assinatura
set(CPACK_POST_BUILD_SCRIPT "${CMAKE_SOURCE_DIR}/cmake/sign_package.cmake")

# sign_package.cmake
file(WRITE ${CMAKE_SOURCE_DIR}/cmake/sign_package.cmake
[=[
    # Assinar pacote gerado
    foreach(_package ${CPACK_GENERATED_PACKAGES})
        # Gerar hash
        file(SHA256 "${_package}" _hash)
        file(WRITE "${_package}.sha256" "${_hash}  ${_package}\n")

        # Assinar com GPG
        if(DEFINED ENV{GPG_KEY})
            execute_process(
                COMMAND gpg --armor --detach-sign
                    --local-user $ENV{GPG_KEY}
                    ${_package}
                RESULT_VARIABLE _result
            )

            if(_result EQUAL 0)
                message(STATUS "Pacote assinado: ${_package}.asc")
            else()
                message(WARNING "Falha ao assinar: ${_package}")
            endif()
        endif()
    endforeach()
]=])
```

### Verificação de Integridade em Scripts de Instalação

```cmake
# Script de verificação para scripts de instalação
function(verify_package_integrity package_file expected_hash)
    # Calcular hash do pacote
    file(SHA256 ${package_file} actual_hash)

    # Comparar com hash esperado
    if(NOT "${actual_hash}" STREQUAL "${expected_hash}")
        message(FATAL_ERROR
            "INTEGRIDADE COMPROMETIDA!\n"
            "Pacote: ${package_file}\n"
            "Hash esperado: ${expected_hash}\n"
            "Hash atual: ${actual_hash}")
    endif()

    message(STATUS "Integridade verificada: ${package_file}")
endfunction()

# Uso
verify_package_integrity(
    "myapp-1.0.0-Linux.deb"
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
```

### Assinatura com SignPackage e VerifyPackage

```cmake
# Configurar assinatura de pacotes
set(CPACK_DEB_SIGN_PACKAGE ON)
set(CPACK_DEB_SIGN_KEY_ID "YOUR_KEY_ID")

# Script para assinar pacotes Debian
set(CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA
    "${CMAKE_SOURCE_DIR}/debian/sign_package.sh")

# debian/sign_package.sh
file(WRITE ${CMAKE_SOURCE_DIR}/debian/sign_package.sh
[=[
    #!/bin/bash
    set -e

    PACKAGE_FILE=$1
    GPG_KEY=$2

    # Assinar pacote
    gpg --armor --detach-sign --local-user "$GPG_KEY" "$PACKAGE_FILE"

    # Gerar hash
    sha256sum "$PACKAGE_FILE" > "${PACKAGE_FILE}.sha256"

    echo "Pacote assinado: ${PACKAGE_FILE}.asc"
    echo "Hash gerado: ${PACKAGE_FILE}.sha256"
]=])
```

### Verificação de Assinatura em Distribuições

```cmake
# Script para verificar assinatura em distribuições
function(verify_package_signature package_file signature_file)
    # Verificar se GPG está disponível
    find_program(GPG_EXECUTABLE gpg)
    if(NOT GPG_EXECUTABLE)
        message(FATAL_ERROR "GPG não encontrado para verificação")
    endif()

    # Verificar assinatura
    execute_process(
        COMMAND ${GPG_EXECUTABLE} --verify ${signature_file} ${package_file}
        RESULT_VARIABLE _result
    )

    if(NOT _result EQUAL 0)
        message(FATAL_ERROR "Assinatura inválida para: ${package_file}")
    endif()

    message(STATUS "Assinatura verificada: ${package_file}")
endfunction()
```

---

## 15.11 Debian Packaging: debian/control, rules

### Estrutura de um Pacote Debian

Um pacote Debian típico requer uma estrutura específica de diretórios:

```
myapp/
├── debian/
│   ├── control
│   ├── rules
│   ├── changelog
│   ├── copyright
│   ├── compat
│   ├── install
│   ├── postinst
│   ├── prerm
│   ├── postrm
│   └── manpages
├── src/
│   └── main.cpp
├── CMakeLists.txt
└── README.md
```

### debian/control

O arquivo `control` define os metadados do pacote:

```
Source: myapp
Section: utils
Priority: optional
Maintainer: Minha Empresa <admin@minhaempresa.com>
Build-Depends: debhelper-compat (= 13),
               cmake (>= 3.20),
               g++ (>= 11),
               libssl-dev (>= 3.0.0),
               pkg-config
Standards-Version: 4.6.0
Homepage: https://myapp.example.com
Vcs-Git: https://github.com/minhaempresa/myapp.git
Vcs-Browser: https://github.com/minhaempresa/myapp

Package: myapp
Architecture: any
Depends: ${shlibs:Depends}, ${misc:Depends}
Recommends: myapp-doc
Description: Aplicativo seguro de processamento de dados
 MyApp é um aplicativo que fornece funcionalidades seguras
 de processamento de dados com suporte a múltiplos formatos.
 .
 Principais características:
 - Processamento seguro de dados
 - Suporte a múltiplos formatos
 - Interface de linha de comando
 - Alta performance

Package: myapp-dev
Architecture: any
Depends: myapp (= ${binary:Version}), ${shlibs:Depends}, ${misc:Depends}
Description: Headers e arquivos de desenvolvimento do MyApp
 Pacote de desenvolvimento contendo headers e arquivos
 estáticos para compilar programas que usam MyApp.

Package: myapp-doc
Architecture: all
Depends: ${misc:Depends}
Description: Documentação do MyApp
 Documentação completa do MyApp em formato HTML e man pages.
```

### debian/rules

O arquivo `rules` é o Makefile que controla a compilação do pacote:

```makefile
#!/usr/bin/make -f

export DH_VERBOSE = 1

%:
	dh $@

override_dh_auto_configure:
	dh_auto_configure -- \
		-DCMAKE_INSTALL_PREFIX=/usr \
		-DCMAKE_BUILD_TYPE=Release \
		-DBUILD_TESTING=OFF \
		-DCMAKE_SKIP_RPATH=OFF \
		-DCMAKE_INSTALL_RPATH=/usr/lib

override_dh_auto_build:
	dh_auto_build --parallel

override_dh_auto_install:
	dh_auto_install

override_dh_auto_test:
	# Tests disabled during package build
	# dh_auto_test

override_dh_shlibdeps:
	dh_shlibdeps -l/usr/lib

override_dh_strip:
	dh_strip --no-automatic-dbgsym

override_dh_installdocs:
	dh_installdocs README.md CHANGES

override_dh_installman:
	dh_installman doc/myapp.1

override_dh_installchangelogs:
	dh_installchangelogs CHANGES
```

### debian/changelog

O arquivo `changelog` mantém o histórico de versões:

```
myapp (1.0.0-1) unstable; urgency=medium

  * Initial release
  * Added secure data processing
  * Added support for multiple formats
  * Added man pages

 -- Minha Empresa <admin@minhaempresa.com>  Mon, 15 Jun 2026 12:00:00 +0000

myapp (0.9.0-1) unstable; urgency=low

  * Beta release
  * Bug fixes

 -- Minha Empresa <admin@minhaempresa.com>  Mon, 01 Jun 2026 12:00:00 +0000
```

### debian/install

O arquivo `install` lista arquivos para instalação:

```
# Arquivos para instalação
src/myapp usr/bin
lib/libmylib.so.* usr/lib
include/mylib.h usr/include
config/myapp.conf etc/myapp
doc/myapp.1 usr/share/man/man1
```

### Scripts de Maintainer

#### debian/postinst

```bash
#!/bin/bash
set -e

case "$1" in
    configure)
        # Configurar diretórios
        mkdir -p /etc/myapp
        chown root:root /etc/myapp
        chmod 755 /etc/myapp

        # Atualizar ldconfig
        ldconfig

        # Habilitar serviço
        if [ -d /run/systemd/system ]; then
            systemctl daemon-reload
            systemctl enable myapp.service
        fi
        ;;
esac

#DEBHELPER#
```

#### debian/prerm

```bash
#!/bin/bash
set -e

case "$1" in
    remove|upgrade|deconfigure)
        # Parar serviço
        if [ -d /run/systemd/system ]; then
            systemctl stop myapp.service || true
        fi
        ;;
esac

#DEBHELPER#
```

#### debian/postrm

```bash
#!/bin/bash
set -e

case "$1" in
    purge)
        # Limpar configuração
        rm -rf /etc/myapp

        # Limpar logs
        rm -rf /var/log/myapp
        ;;
esac

#DEBHELPER#
```

### Construindo o Pacote Debian

```bash
# Instalar dependências de build
sudo apt-get install build-essential devscripts debhelper cmake libssl-dev

# Construir pacote
dpkg-buildpackage -us -uc -b

# Ou usar debuild
debuild -us -uc

# Ou usar pbuilder para ambiente limpo
sudo pbuilder build myapp_1.0.0-1.dsc
```

### Verificação de Qualidade Debian

```bash
# Verificar pacote
lintian myapp_1.0.0-1_amd64.deb

# Verificar dependências
dpkg-deb -I myapp_1.0.0-1_amd64.deb

# Verificar conteúdo
dpkg-deb -c myapp_1.0.0-1_amd64.deb

# Testar instalação
sudo dpkg -i myapp_1.0.0-1_amd64.deb
```

---

## 15.12 RPM Packaging: Spec Files

### Estrutura de um Spec File

O spec file RPM define como o pacote é construído e instalado:

```spec
Name:           myapp
Version:        1.0.0
Release:        1%{?dist}
Summary:        Aplicativo seguro de processamento de dados

License:        MIT
URL:            https://myapp.example.com
Source0:        %{name}-%{version}.tar.gz

BuildRequires:  cmake >= 3.20
BuildRequires:  gcc >= 11
BuildRequires:  gcc-c++ >= 11
BuildRequires:  openssl-devel >= 3.0.0
BuildRequires:  pkgconfig

%description
MyApp é um aplicativo que fornece funcionalidades seguras
de processamento de dados com suporte a múltiplos formatos.

Principais características:
- Processamento seguro de dados
- Suporte a múltiplos formatos
- Interface de linha de comando
- Alta performance

%package doc
Summary:        Documentação do MyApp
Requires:       %{name} = %{version}-%{release}

%description doc
Documentação completa do MyApp em formato HTML e man pages.

%package devel
Summary:        Headers e arquivos de desenvolvimento do MyApp
Requires:       %{name} = %{version}-%{release}

%description devel
Pacote de desenvolvimento contendo headers e arquivos
estáticos para compilar programas que usam MyApp.

%prep
%setup -q

%build
%cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF \
    -DCMAKE_SKIP_RPATH=OFF \
    -DCMAKE_INSTALL_RPATH=%{_libdir}
%cmake_build

%install
%cmake_install

%check
# Tests disabled during package build
# %cmake_build --target test

%post
/sbin/ldconfig

%postun
/sbin/ldconfig

%files
%license LICENSE
%doc README.md CHANGES
%{_bindir}/myapp
%{_libdir}/libmylib.so.*

%files doc
%doc %{_docdir}/%{name}/html
%{_mandir}/man1/myapp.1*

%files devel
%{_includedir}/mylib.h
%{_libdir}/libmylib.so
%{_libdir}/pkgconfig/mylib.pc

%changelog
* Mon Jun 15 2026 Minha Empresa <admin@minhaempresa.com> - 1.0.0-1
- Initial release
- Added secure data processing
- Added support for multiple formats
- Added man pages
```

### Macros RPM

```spec
# Macros úteis
%{_bindir}        # /usr/bin
%{_sbindir}       # /usr/sbin
%{_libdir}        # /usr/lib64 ou /usr/lib
%{_includedir}    # /usr/include
%{_datadir}       # /usr/share
%{_mandir}        # /usr/share/man
%{_docdir}        # /usr/share/doc
%{_sysconfdir}    # /etc
%{_localstatedir} # /var

# Macros do CMake
%cmake            # Configuração CMake
%cmake_build      # Build
%cmake_install    # Instalação
%cmake_check      # Testes
```

### Construindo o Pacote RPM

```bash
# Instalar dependências de build
sudo dnf install rpm-build cmake gcc gcc-c++ openssl-devel

# Estrutura de diretórios
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Copiar spec file
cp myapp.spec ~/rpmbuild/SPECS/

# Copiar fonte
cp myapp-1.0.0.tar.gz ~/rpmbuild/SOURCES/

# Construir pacote
rpmbuild -ba ~/rpmbuild/SPECS/myapp.spec

# Ou apenas pacote binário
rpmbuild -bb ~/rpmbuild/SPECS/myapp.spec
```

### Verificação de Qualidade RPM

```bash
# Verificar pacote
rpm -qpi myapp-1.0.0-1.fc39.x86_64.rpm

# Verificar conteúdo
rpm -qpl myapp-1.0.0-1.fc39.x86_64.rpm

# Verificar dependências
rpm -qpR myapp-1.0.0-1.fc39.x86_64.rpm

# Testar instalação
sudo rpm -ivh myapp-1.0.0-1.fc39.x86_64.rpm
```

---

## 15.13 Exemplo: Install + CPack Completo

### Estrutura do Projeto

```
myapp/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   ├── config.cpp
│   └── network.cpp
├── include/
│   ├── myapp/
│   │   ├── config.h
│   │   └── network.h
│   └── mylib/
│       └── mylib.h
├── lib/
│   └── mylib.cpp
├── config/
│   ├── myapp.conf
│   └── myapp.conf.in
├── doc/
│   ├── myapp.1
│   └── README.md
├── examples/
│   └── basic.cpp
├── tests/
│   └── test_myapp.cpp
├── cmake/
│   ├── FindMyLib.cmake
│   └── SignPackage.cmake
├── debian/
│   ├── control
│   ├── rules
│   └── changelog
├── rpm/
│   └── myapp.spec
└── LICENSE
```

### CMakeLists.txt Completo

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyApp VERSION 2.1.0 LANGUAGES C CXX)

# ============================================================================
# Configuração do Projeto
# ============================================================================

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Habilitar export de compile_commands.json
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# ============================================================================
# Incluir Módulos
# ============================================================================

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(CPack)

# ============================================================================
# Criar Biblioteca
# ============================================================================

add_library(mylib SHARED
    lib/mylib.cpp
)

set_target_properties(mylib PROPERTIES
    VERSION ${PROJECT_VERSION}
    SOVERSION ${PROJECT_VERSION_MAJOR}
    PUBLIC_HEADER "include/mylib/mylib.h"
    INSTALL_RPATH "$ORIGIN"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)

# ============================================================================
# Criar Executável
# ============================================================================

add_executable(myapp
    src/main.cpp
    src/config.cpp
    src/network.cpp
)

target_link_libraries(myapp PRIVATE mylib)

set_target_properties(myapp PROPERTIES
    INSTALL_RPATH "$ORIGIN/../lib"
    INSTALL_RPATH_USE_LINK_PATH TRUE
)

# ============================================================================
# Configurar Testes
# ============================================================================

enable_testing()
find_package(GTest QUIET)
if(GTest)
    add_executable(test_myapp tests/test_myapp.cpp)
    target_link_libraries(test_myapp PRIVATE mylib GTest::gtest_main)
    add_test(NAME test_myapp COMMAND test_myapp)
endif()

# ============================================================================
# Instalação
# ============================================================================

# Instalar biblioteca
install(
    TARGETS mylib
    EXPORT myapp-targets
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    PUBLIC_HEADER DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/mylib
    COMPONENT runtime
)

# Instalar executável
install(
    TARGETS myapp
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    COMPONENT runtime
)

# Instalar headers
install(
    FILES
        include/myapp/config.h
        include/myapp/network.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/myapp
    COMPONENT dev
)

# Instalar configuração
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/config/myapp.conf.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated/myapp.conf
    @ONLY
)

install(
    FILES ${CMAKE_CURRENT_BINARY_DIR}/generated/myapp.conf
    DESTINATION ${CMAKE_INSTALL_SYSCONFDIR}/myapp
    PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ
    COMPONENT config
)

# Instalar documentação
install(
    FILES
        README.md
        LICENSE
    DESTINATION ${CMAKE_INSTALL_DOCDIR}
    COMPONENT doc
)

install(
    FILES doc/myapp.1
    DESTINATION ${CMAKE_INSTALL_MANDIR}/man1
    COMPONENT doc
)

# Instalar exemplos
install(
    FILES examples/basic.cpp
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/myapp/examples
    COMPONENT examples
)

# Instalar desktop file
install(
    FILES desktop/myapp.desktop
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/applications
    COMPONENT desktop
)

# Instalar icons
install(
    FILES icons/myapp.png
    DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/icons/hicolor/256x256/apps
    COMPONENT desktop
)

# ============================================================================
# Export de CMake
# ============================================================================

# Criar export targets
install(
    EXPORT myapp-targets
    FILE myapp-targets.cmake
    NAMESPACE MyApp::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/myapp
    COMPONENT dev
)

# Gerar arquivo de configuração
configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/cmake/myapp-config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/myapp-config.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/myapp
)

# Gerar arquivo de versão
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/myapp-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(
    FILES
        ${CMAKE_CURRENT_BINARY_DIR}/myapp-config.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/myapp-config-version.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/myapp
    COMPONENT dev
)

# ============================================================================
# CPack Configuration
# ============================================================================

# Metadados do pacote
set(CPACK_PACKAGE_NAME "myapp")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Meu aplicativo seguro e eficiente")
set(CPACK_PACKAGE_VENDOR "Minha Empresa Ltda")
set(CPACK_PACKAGE_CONTACT "admin@minhaempresa.com")
set(CPACK_PACKAGE_HOMEPAGE_URL "https://myapp.example.com")
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_SOURCE_DIR}/LICENSE")

# Diretórios
set(CPACK_PACKAGING_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Habilitar instalação por componente
set(CPACK_DEB_COMPONENT_INSTALL ON)
set(CPACK_RPM_COMPONENT_INSTALL ON)

# ============================================================================
# Configuração DEB
# ============================================================================

# Componente runtime
set(CPACK_DEBIAN_RUNTIME_PACKAGE_NAME "myapp")
set(CPACK_DEBIAN_RUNTIME_PACKAGE_SECTION "utils")
set(CPACK_DEBIAN_RUNTIME_PACKAGE_PRIORITY "optional")
set(CPACK_DEBIAN_RUNTIME_PACKAGE_DEPENDS
    "libc6 (>= 2.17), libstdc++6 (>= 11), libssl3 (>= 3.0.0)")
set(CPACK_DEBIAN_RUNTIME_PACKAGE_DESCRIPTION
    "MyApp - Aplicativo seguro de processamento de dados")

# Componente dev
set(CPACK_DEBIAN_DEV_PACKAGE_NAME "myapp-dev")
set(CPACK_DEBIAN_DEV_PACKAGE_DEPENDS
    "myapp (= ${PROJECT_VERSION}), libssl-dev (>= 3.0.0)")
set(CPACK_DEBIAN_DEV_PACKAGE_DESCRIPTION
    "MyApp - Headers e arquivos de desenvolvimento")

# Componente doc
set(CPACK_DEBIAN_DOC_PACKAGE_NAME "myapp-doc")
set(CPACK_DEBIAN_DOC_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")
set(CPACK_DEBIAN_DOC_PACKAGE_DESCRIPTION
    "MyApp - Documentação")

# Componente config
set(CPACK_DEBIAN_CONFIG_PACKAGE_NAME "myapp-config")
set(CPACK_DEBIAN_CONFIG_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")
set(CPACK_DEBIAN_CONFIG_PACKAGE_DESCRIPTION
    "MyApp - Arquivos de configuração")

# Componente examples
set(CPACK_DEBIAN_EXAMPLES_PACKAGE_NAME "myapp-examples")
set(CPACK_DEBIAN_EXAMPLES_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")
set(CPACK_DEBIAN_EXAMPLES_PACKAGE_DESCRIPTION
    "MyApp - Exemplos de uso")

# Componente desktop
set(CPACK_DEBIAN_DESKTOP_PACKAGE_NAME "myapp-desktop")
set(CPACK_DEBIAN_DESKTOP_PACKAGE_DEPENDS "myapp (= ${PROJECT_VERSION})")
set(CPACK_DEBIAN_DESKTOP_PACKAGE_DESCRIPTION
    "MyApp - Arquivos desktop e ícones")

# Auto-dependências
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)

# ============================================================================
# Configuração RPM
# ============================================================================

# Componente runtime
set(CPACK_RPM_RUNTIME_PACKAGE_NAME "myapp")
set(CPACK_RPM_RUNTIME_PACKAGE_LICENSE "MIT")
set(CPACK_RPM_RUNTIME_PACKAGE_GROUP "Applications/System")
set(CPACK_RPM_RUNTIME_PACKAGE_REQUIRES
    "glibc >= 2.17, libstdc++ >= 11, openssl >= 3.0.0")
set(CPACK_RPM_RUNTIME_PACKAGE_DESCRIPTION
    "MyApp - Aplicativo seguro de processamento de dados")

# Componente devel
set(CPACK_RPM_DEVEL_PACKAGE_NAME "myapp-devel")
set(CPACK_RPM_DEVEL_PACKAGE_REQUIRES
    "myapp = ${PROJECT_VERSION}, openssl-devel >= 3.0.0")
set(CPACK_RPM_DEVEL_PACKAGE_DESCRIPTION
    "MyApp - Headers e arquivos de desenvolvimento")

# Componente doc
set(CPACK_RPM_DOC_PACKAGE_NAME "myapp-doc")
set(CPACK_RPM_DOC_PACKAGE_REQUIRES "myapp = ${PROJECT_VERSION}")
set(CPACK_RPM_DOC_PACKAGE_DESCRIPTION
    "MyApp - Documentação")

# Componente config
set(CPACK_RPM_CONFIG_PACKAGE_NAME "myapp-config")
set(CPACK_RPM_CONFIG_PACKAGE_REQUIRES "myapp = ${PROJECT_VERSION}")
set(CPACK_RPM_CONFIG_PACKAGE_DESCRIPTION
    "MyApp - Arquivos de configuração")

# Componente examples
set(CPACK_RPM_EXAMPLES_PACKAGE_NAME "myapp-examples")
set(CPACK_RPM_EXAMPLES_PACKAGE_REQUIRES "myapp = ${PROJECT_VERSION}")
set(CPACK_RPM_EXAMPLES_PACKAGE_DESCRIPTION
    "MyApp - Exemplos de uso")

# Auto-dependências
set(CPACK_RPM_PACKAGE_AUTOREQ ON)
set(CPACK_RPM_PACKAGE_AUTOPROV ON)

# Debug info
set(CPACK_RPM_DEBUGINFO_PACKAGE ON)

# ============================================================================
# Configuração TGZ
# ============================================================================

set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY ON)
set(CPACK_STRIP_FILES OFF)

# ============================================================================
# Configuração NSIS (Windows)
# ============================================================================

set(CPACK_NSIS_PACKAGE_NAME "MyApp")
set(CPACK_NSIS_DISPLAY_NAME "MyApp ${PROJECT_VERSION}")
set(CPACK_NSIS_PUBLISHER "Minha Empresa")
set(CPACK_NSIS_URL_INFO_ABOUT "https://myapp.example.com")
set(CPACK_NSIS_HELP_LINK "https://myapp.example.com/support")
set(CPACK_NSIS_CONTACT "support@minhaempresa.com")
set(CPACK_NSIS_INSTALL_ROOT "$PROGRAMFILES")
set(CPACK_NSIS_EXECUTABLES_DIRECTORY "bin")
set(CPACK_NSIS_ICONS_EXTRA "Desktop;StartMenu")

# ============================================================================
# Configuração de Assinatura
# ============================================================================

# Script pós-geração para assinatura
set(CPACK_POST_BUILD_SCRIPT "${CMAKE_SOURCE_DIR}/cmake/SignPackage.cmake")

# ============================================================================
# Geradores Padrão
# ============================================================================

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CPACK_GENERATOR "DEB;RPM;TGZ")
elseif(CMAKE_SYSTEM_NAME STREQUAL "Windows")
    set(CPACK_GENERATOR "NSIS;WIX;TGZ")
elseif(CMAKE_SYSTEM_NAME STREQUAL "Darwin")
    set(CPACK_GENERATOR "DragNDrop;TGZ")
else()
    set(CPACK_GENERATOR "TGZ")
endif()
```

### cmake/myapp-config.cmake.in

```cmake
@PACKAGE_INIT@

include(CMakeFindDependencyMacro)

find_dependency(Threads)

include("${CMAKE_CURRENT_LIST_DIR}/myapp-targets.cmake")

check_required_components(myapp)
```

### cmake/SignPackage.cmake

```cmake
# Script para assinar pacotes gerados

find_program(GPG_EXECUTABLE gpg)
find_program(SHA256SUM_EXECUTABLE sha256sum)

# Função para gerar hash
function(generate_hash package_file)
    if(SHA256SUM_EXECUTABLE)
        execute_process(
            COMMAND ${SHA256SUM_EXECUTABLE} ${package_file}
            OUTPUT_VARIABLE _hash_output
            OUTPUT_STRIP_TRAILING_WHITESPACE
        )
        file(WRITE "${package_file}.sha256" "${_hash_output}\n")
        message(STATUS "Hash gerado: ${_hash_output}")
    endif()
endfunction()

# Função para assinar pacote
function(sign_package package_file key_id)
    if(GPG_EXECUTABLE AND DEFINED ENV{GPG_KEY})
        execute_process(
            COMMAND ${GPG_EXECUTABLE} --armor --detach-sign
                --local-user $ENV{GPG_KEY}
                ${package_file}
            RESULT_VARIABLE _result
        )

        if(_result EQUAL 0)
            message(STATUS "Pacote assinado: ${package_file}.asc")
        else()
            message(WARNING "Falha ao assinar: ${package_file}")
        endif()
    endif()
endfunction()

# Processar pacotes gerados
if(CPACK_GENERATED_PACKAGES)
    foreach(_package ${CPACK_GENERATED_PACKAGES})
        generate_hash("${_package}")
        sign_package("${_package}" "$ENV{GPG_KEY}")
    endforeach()
endif()
```

### Construindo e Instalando

```bash
# Configurar
cmake -B build \
    -DCMAKE_INSTALL_PREFIX=/usr \
    -DCMAKE_BUILD_TYPE=Release \
    ..

# Build
cmake --build build -j$(nproc)

# Testar
cmake --build build --target test

# Instalar localmente (para teste)
DESTDIR=/tmp/staging cmake --install build

# Gerar pacotes
cd build && cpack

# Gerar pacote específico
cd build && cpack -G DEB
cd build && cpack -G RPM
cd build && cpack -G TGZ
```

### Verificando os Pacotes Gerados

```bash
# Verificar pacote Debian
dpkg-deb -I myapp-2.1.0-Linux.deb
dpkg-deb -c myapp-2.1.0-Linux.deb

# Verificar pacote RPM
rpm -qpi myapp-2.1.0-Linux.rpm
rpm -qpl myapp-2.1.0-Linux.rpm

# Verificar tarball
tar -tzf myapp-2.1.0-Linux.tar.gz

# Verificar assinatura
gpg --verify myapp-2.1.0-Linux.deb.asc

# Verificar hash
sha256sum -c myapp-2.1.0-Linux.deb.sha256
```

---

## 15.14 Exercícios

### Exercício 1: Instalação Segura Básica

Crie um CMakeLists.txt que instale um executável e uma biblioteca compartilhada com as seguintes exigências:

1. O executável deve ter RPATH configurado com `$ORIGIN/../lib`
2. A biblioteca deve ter versionamento (SOVERSION)
3. Headers devem ser instalados em `${CMAKE_INSTALL_INCLUDEDIR}/mylib`
4. Configuração deve ter permissões OWNER_READ OWNER_WRITE GROUP_READ
5. Documentação deve ser instalada em `${CMAKE_INSTALL_DOCDIR}`

### Exercício 2: Component-based Installation

Implemente um projeto com os seguintes componentes:

1. `runtime` - Binários e bibliotecas
2. `dev` - Headers e arquivos de desenvolvimento
3. `doc` - Documentação
4. `config` - Arquivos de configuração

Demonstre como instalar apenas o componente `runtime` usando `cmake --install --component`.

### Exercício 3: CPack Multi-Plataforma

Configure CPack para gerar pacotes para:

1. DEB (Debian/Ubuntu)
2. RPM (Red Hat/Fedora)
3. TGZ (Qualquer plataforma)

Inclua metadados completos, dependências e descrições.

### Exercício 4: Debian Packaging

Crie uma estrutura completa de pacote Debian incluindo:

1. `debian/control` com múltiplos binários
2. `debian/rules` com build customizado
3. `debian/changelog` com histórico de versões
4. Scripts `postinst`, `prerm`, `postrm`

### Exercício 5: Signing e Verificação

Implemente um sistema de assinatura de pacotes:

1. Gere hashes SHA256 dos pacotes
2. Assine pacotes com GPG
3. Crie scripts de verificação de integridade
4. Documente o processo de verificação

### Exercício 6: RPATH Security

Analise e corrija os seguintes problemas de RPATH:

1. RPATH com path world-writable
2. Dependência de LD_LIBRARY_PATH
3. Falta de `$ORIGIN` em paths relativos
4. RPATH incorreto em cross-compilation

### Exercício 7: GNUInstallDirs

Refatore um projeto existente para usar `GNUInstallDirs`:

1. Substitua paths hardcoded por variáveis do GNUInstallDirs
2. Configure instalação para conformidade FHS
3. Documente os caminhos resultantes

---

## 15.15 Referências

### Documentação Oficial

- [CMake install() Command](https://cmake.org/cmake/help/latest/command/install.html)
- [CMake GNUInstallDirs Module](https://cmake.org/cmake/help/latest/module/GNUInstallDirs.html)
- [CMake CPack Module](https://cmake.org/cmake/help/latest/module/CPack.html)
- [CMake CPack DEB Generator](https://cmake.org/cmake/help/latest/module/CPackDeb.html)
- [CMake CPack RPM Generator](https://cmake.org/cmake/help/latest/module/CPackRPM.html)

### Livros e Artigos

- "Mastering CMake" - Kitware
- "CMake: A Cross-Platform Build System" - Craig Scott
- [Debian New Maintainer's Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [RPM Guide](https://docs.fedoraproject.org/en-US/Fedora/33/Community_Documentation)

### Segurança

- [OWASP Supply Chain Security](https://owasp.org/www-project-supply-chain-security/)
- [SLSA Framework](https://slsa.dev/)
- [Sigstore](https://www.sigstore.dev/)
- [CIS Benchmarks for Linux](https://www.cisecurity.org/cis-benchmarks)

### Ferramentas

- [debhelper](https://manpages.debian.org/bookworm/debhelper/debhelper.1.en.html)
- [rpmbuild](https://man7.org/linux/man-pages/man8/rpmbuild.8.html)
- [lintian](https://manpages.debian.org/bookworm/lintian/lintian.1.en.html)
- [GnuPG](https://gnupg.org/)

---

*[Capítulo anterior: 14 — Testing no CMake](14-testing-cmake.md)* | *[Próximo capítulo: 16 — CI/CD Seguro com CMake](16-cicd-seguro.md)*
