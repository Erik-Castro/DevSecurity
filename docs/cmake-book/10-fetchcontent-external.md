---
layout: default
title: "10-fetchcontent-external"
---

# Capitulo 10: FetchContent e ExternalProject

> *"Dependencias baixadas em tempo de build sao a fronteira mais fraca da supply chain."*

---

## 10.1 Objetivos de Aprendizado

Apos completar este capitulo, voce sera capaz de:

- Usar `FetchContent` para baixar e integrar dependencias no build
- Configurar `ExternalProject_Add` para builds externos isolados
- Distinguir quando usar FetchContent versus ExternalProject
- Implementar pinning robusto com `GIT_TAG`, URLs e verificacao de hash
- Configurar `CMAKE_TLS_VERIFY` para downloads seguros
- Gerenciar `DOWNLOAD_EXTRACT_TIMESTAMP` para builds reproduziveis
- Usar content-hash para locking de dependencias
- Comparar submodules com FetchContent em cenarios de seguranca
- Analisar o CVE-2024-3094 (XZ Utils) e extrair licoes para build systems
- Implementar FetchContent seguro com verificao de hash completo

---

## 10.2 FetchContent: download, populate, add_subdirectory

### 10.2.1 O que e FetchContent

FetchContent e um modulo do CMake que permite baixar fontes de dependencias externas durante a configuracao do build, populando-as localmente e integrando-as ao build via `add_subdirectory`. Diferente do `find_package`, que espera que a biblioteca ja esteja instalada no sistema, FetchContent resolve o problema de "onde encontrar esta dependencia" baixando-a diretamente de repositories ou URLs.

O FetchContent foi introduzido no CMake 3.11 e amadureceu significativamente no CMake 3.14, tornando-se a abordagem recomendada para integrar dependencias que nao estao disponiveis via pacotes do sistema ou gerenciadores de pacotes.

### 10.2.2 Ciclo de Vida do FetchContent

O FetchContent opera em tres estagios claros:

**Estagio 1: Download (FetchContent_Declare)**
O comando `FetchContent_Declare` registra de onde a dependencia deve ser baixada. Neste ponto, nenhum download acontece — apenas a declaracao e armazenada internamente pelo CMake.

```cmake
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
)
```

**Estagio 2: Populate (FetchContent_MakeAvailable ou FetchContent_Populate)**
O comando `FetchContent_MakeAvailable` executa o download e extracao. Apos este passo, a variavel `fmt_SOURCE_DIR` estara disponivel apontando para o diretorio local das fontes.

**Estagio 3: Integrate (add_subdirectory implicito)**
`FetchContent_MakeAvailable` automaticamente chama `add_subdirectory` nas fontes baixadas, tornando os targets disponiveis para o seu projeto.

### 10.2.3 Exemplo Basico

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
)

FetchContent_MakeAvailable(fmt)

add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE fmt::fmt)
```

### 10.2.4 Controle Granular com FetchContent_Populate

Para controle mais fino, voce pode usar `FetchContent_Populate` em vez de `FetchContent_MakeAvailable`:

```cmake
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
)

FetchContent_GetProperties(googletest)
if(NOT googletest_POPULATED)
    FetchContent_Populate(googletest)
    add_subdirectory(
        ${googletest_SOURCE_DIR}
        ${googletest_BINARY_DIR}
        EXCLUDE_FROM_ALL
    )
endif()
```

A opcao `EXCLUDE_FROM_ALL` e importante: ela impede que targets da dependencia aparecam como targets padrao do build, evitando que `make` compile tudo implicitamente.

### 10.2.5 Variaveis Geradas pelo FetchContent

Apos o populate, o CMake define varias variaveis:

| Variavel | Descricao |
|----------|-----------|
| `<name>_SOURCE_DIR` | Caminho absoluto para o diretorio de fontes |
| `<name>_BINARY_DIR` | Caminho absoluto para o diretorio de build |
| `<name>_POPULATED` | TRUE se o populate ja foi executado |

### 10.2.6 FetchContent com URL Local

Voce pode usar URLs locais para testing ou ambientes sem acesso a rede:

```cmake
FetchContent_Declare(
    mylib
    URL      file:///opt/deps/mylib-1.0.tar.gz
    URL_HASH SHA256=abc123def456...
)
```

### 10.2.7 O Problema do Download Requerido

Por padrao, `FetchContent_Declare` com `GIT_REPOSITORY` ou `URL` obriga o download durante a configuracao. Isso pode ser problematico em ambientes com restricoes de rede. Use `DOWNLOAD_ONLY` quando quiser adiar:

```cmake
FetchContent_Declare(
    external_data
    URL      https://example.com/data.tar.gz
    URL_HASH SHA256=...
    DOWNLOAD_ONLY YES
)
```

### 10.2.8 Estrategia de Cachear FetchContent

Em CI/CD, baixar dependencias repetidamente e desperdicio. O CMake suporta caching via `FETCHCONTENT_UPDATES_DISCONNECTED`:

```cmake
# Em CMakeLists.txt principal
option(FETCHCONTENT_UPDATES_DISCONNECTED
    "Disable update check for FetchContent" ON)
```

Ou via linha de comando:

```bash
cmake -B build -DFETCHCONTENT_UPDATES_DISCONNECTED=ON
```

Quando habilitado, o CMake nao verifica por atualizacoes de repositorios Git ja baixados. Isso acelera builds incrementais e melhora a reprodutibilidade.

---

## 10.3 ExternalProject_Add: build separado

### 10.3.1 A Diferenca Fundamental

Enquanto `FetchContent` integra a dependencia diretamente ao seu build (mesmo CMakeLists.txt, mesmas flags, mesmas configuracoes), `ExternalProject_Add` cria um build completamente separado. A dependencia e configurada, compilada e instalada em seu proprio sandbox.

Isso e util quando:

- A dependencia requer flags de compilacao incompativeis com as do seu projeto
- A dependencia usa um build system diferente (Meson, Autotools, Makefile puro)
- Voce quer isolar erros de build da dependencia
- A dependencia precisa ser instalada antes de ser usada pelo seu projeto

### 10.3.2 Exemplo Basico

```cmake
cmake_minimum_required(VERSION 3.20)
project(MyProject LANGUAGES C CXX)

include(ExternalProject)

ExternalProject_Add(
    zlib_external
    URL               https://zlib.net/zlib-1.3.1.tar.gz
    URL_HASH          SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
    CMAKE_ARGS
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DBUILD_SHARED_LIBS=OFF
    BUILD_COMMAND
        ${CMAKE_COMMAND} --build <BINARY_DIR> --config $<CONFIG>
    INSTALL_COMMAND
        ${CMAKE_COMMAND} --install <BINARY_DIR> --config $<CONFIG>
)

# Criar target para expressar a dependencia
ExternalProject_Get_Property(zlib_external INSTALL_DIR)
add_library(zlib IMPORTED STATIC)
set_target_properties(zlib PROPERTIES
    IMPORTED_LOCATION ${INSTALL_DIR}/lib/libz.a
    INTERFACE_INCLUDE_DIRECTORIES ${INSTALL_DIR}/include
)
add_dependencies(zlib zlib_external)
```

### 10.3.3 Variaveis Internas do ExternalProject

O ExternalProject usa variaveis internas que sao substituidas durante o build:

| Variavel | Substituicao |
|----------|--------------|
| `<SOURCE_DIR>` | Diretorio de fontes extraidas |
| `<BINARY_DIR>` | Diretorio de build |
| `<INSTALL_DIR>` | Diretorio de instalacao |
| `<TMP_DIR>` | Diretorio temporario |
| `<STAMP_DIR>` | Diretorio de stamps (controle de estado) |

### 10.3.4 ExternalProject com Build System Diferente

```cmake
ExternalProject_Add(
    autotools_lib
    URL               https://example.com/lib-2.0.tar.gz
    URL_HASH          SHA256=...
    CONFIGURE_COMMAND
        <SOURCE_DIR>/configure
            --prefix=<INSTALL_DIR>
            --enable-static
            --disable-shared
    BUILD_COMMAND
        make -j${NPROC}
    INSTALL_COMMAND
        make install
)
```

### 10.3.5 ExternalProject com Patch

```cmake
ExternalProject_Add(
    patched_lib
    URL               https://example.com/lib-1.0.tar.gz
    URL_HASH          SHA256=...
    PATCH_COMMAND
        patch -p1 < ${CMAKE_CURRENT_SOURCE_DIR}/patches/fix-security.patch
    CMAKE_ARGS
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
)
```

### 10.3.6 Estampas e Re-build

ExternalProject usa "estampas" (arquivos selo) para rastrear o estado do build. Cada passo gera uma estampa:

- `configure` -> `<stamp_dir>/configure-done`
- `build` -> `<stamp_dir>/build-done`
- `install` -> `<stamp_dir>/install-done`

Se o build externo falhar, voce pode limpar as estampas para forcar re-build:

```bash
rm -rf build/patches/zlib_external-stamp/
```

### 10.3.7 ExternalProject como Dependencia de Build

Para expressar dependencias entre targets externos e o seu projeto:

```cmake
# Seu projeto depende do zlib externo
add_executable(myapp main.cpp)
add_dependencies(myapp zlib_external)
target_include_directories(myapp PRIVATE ${INSTALL_DIR}/include)
target_link_libraries(myapp PRIVATE ${INSTALL_DIR}/lib/libz.a)
```

Ou mais elegante, criando uma imported library:

```cmake
add_library(zlib_external_lib IMPORTED STATIC)
set_target_properties(zlib_external_lib PROPERTIES
    IMPORTED_LOCATION ${INSTALL_DIR}/lib/libz.a
    INTERFACE_INCLUDE_DIRECTORIES ${INSTALL_DIR}/include
)
add_dependencies(zlib_external_lib zlib_external)
target_link_libraries(myapp PRIVATE zlib_external_lib)
```

### 10.3.8 ExternalProject e o Problema de Rede

ExternalProject faz downloads em tempo de build, nao durante a configuracao. Isso significa que:

1. `cmake -B build` pode rodar sem rede (se o download anterior existir)
2. `cmake --build build` precisa de rede para baixar dependencias
3. Build failures de rede sao mais dificeis de debugar

Para mitigar isso, voce pode pré-baixar as fontes:

```cmake
ExternalProject_Add(
    mylib
    URL               ${PRE_DOWNLOADED_URL}
    URL_HASH          SHA256=...
    # ...
)
```

---

## 10.4 Diferencas: quando usar cada um

### 10.4.1 Tabela Comparativa

| Aspecto | FetchContent | ExternalProject |
|---------|-------------|-----------------|
| Integracao ao build | Mesmo CMakeLists.txt | Build separado |
| Acesso a targets | Direto | Via imported targets |
| Flags de compilacao | Herdadas do projeto | Configuradas separadamente |
| Build system da dependencia | CMake | Qualquer um |
| Tempo de download | Configuracao | Build |
| Controle de isolamento | Baixo | Alto |
| Facilidade de uso | Alta | Media |
| Reprodutibilidade | Depende da config | Mais isolada |

### 10.4.2 Cenarios de Uso

**Use FetchContent quando:**

- A dependencia e um projeto CMake moderno
- Voce quer acesso direto aos targets
- As flags de compilacao sao compativeis
- A dependencia e relativamente simples
- Voce quer que a dependencia seja tratada como parte do seu projeto

**Use ExternalProject quando:**

- A dependencia usa um build system nao-CMake (Autotools, Meson, Makefile)
- Voce precisa de isolamento total entre builds
- As flags de compilacao sao incompativeis
- A dependencia e complexa e pode causar conflitos
- Voce quer controle total sobre o processo de build

### 10.4.3 Exemplo de Decisao

**Cenario: Sua biblioteca de rede precisa de OpenSSL, mas OpenSSL usa Autotools.**

```cmake
# NAO usar FetchContent — OpenSSL nao e CMake-native
# Usar ExternalProject para isolar o build

include(ExternalProject)

ExternalProject_Add(
    openssl_external
    URL               https://www.openssl.org/source/openssl-3.2.1.tar.gz
    URL_HASH          SHA256=840af5366ab9b522ea3b6d7d3c57151c8e571e0453282b7a...
    CONFIGURE_COMMAND
        <SOURCE_DIR>/Configure
            --prefix=<INSTALL_DIR>
            --openssldir=<INSTALL_DIR>/ssl
            no-shared
            no-tests
    BUILD_COMMAND
        make -j$(nproc)
    INSTALL_COMMAND
        make install_sw
)
```

**Cenario: Sua aplicacao precisa da biblioteca de formato de texto `fmt`.**

```cmake
# Usar FetchContent — fmt e CMake-native e se integra perfeitamente

include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
    GIT_SHALLOW    TRUE
)

FetchContent_MakeAvailable(fmt)
```

### 10.4.4 Hibrindo: FetchContent com Controle

Voce pode combinar abordagens. Por exemplo, usar FetchContent para baixar, mas controlar a integracao:

```cmake
FetchContent_Declare(
    glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG        3.3.9
)

# Nao usar MakeAvailable — controle manual
FetchContent_GetProperties(glfw)
if(NOT glfw_POPULATED)
    FetchContent_Populate(glfw)

    # Configuracoes especificas antes do add_subdirectory
    set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
    set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
    set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)

    add_subdirectory(
        ${glfw_SOURCE_DIR}
        ${glfw_BINARY_DIR}
        EXCLUDE_FROM_ALL
    )
endif()
```

### 10.4.5 Impacto na Seguranca

A escolha entre FetchContent e ExternalProject tem implicacoes de seguranca:

- **FetchContent** herda as flags de seguranca do seu projeto. Se voce habilita `-fstack-protector-strong` e `-D_FORTIFY_SOURCE=2`, a dependencia tambem sera compilada com essas flags. Isso e desejavel para dependencias CMake que voce controla.

- **ExternalProject** isola as flags. A dependencia e compilada com suas proprias configuracoes. Isso pode ser necessario (OpenSSL tem suas proprias flags de hardening), mas tambem significa que voce precisa configurar explicitamente as flags de seguranca para cada dependencia externa.

- **Risco de FetchContent**: se a dependencia tem bugs de build que interagem com suas flags, o build pode falhar ou gerar binarios inseguros.

- **Risco de ExternalProject**: se voce esquece de configurar flags de seguranca, a dependencia pode ser compilada sem protections.

---

## 10.5 Pinning: GIT_TAG, URL, hash verification

### 10.5.1 O Problema de Pinning

Sem pinning, uma dependencia pode mudar entre builds. O que funcionava ontem pode quebrar hoje. Isso e especialmente perigoso em:

- Build servers que executam periodicamente
- Desenvolvedores que configuram o ambiente pela primeira vez
- CI/CD que re-executa builds antigos

Pinning e o ato de fixar uma dependencia em uma versao ou revisao especifica.

### 10.5.2 GIT_TAG: Tipos de Referencia

O `GIT_TAG` aceita varios formatos:

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY https://github.com/user/mylib.git
    GIT_TAG        v1.2.3              # Tag do git
)
```

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY https://github.com/user/mylib.git
    GIT_TAG        abc123def456        # SHA-1 completo ou prefixo
)
```

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY https://github.com/user/mylib.git
    GIT_TAG        main                # Branch (NAO recomendado)
)
```

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY https://github.com/user/mylib.git
    GIT_TAG        HEAD                # Ultimo commit (PERIGOSO)
)
```

**Recomendacao de seguranca**: SEMPRE use tags ou SHAs. NUNCA use branches ou HEAD em ambientes de producao.

### 10.5.3 URL com Hash

Para downloads via URL, a verificacao de hash e mandatoria para seguranca:

```cmake
FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.0.tar.gz
    URL_HASH          SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
)
```

O CMake suporta multiplos algoritmos de hash:

| Algoritmo | Forca | Recomendado |
|-----------|-------|-------------|
| MD5 | Fraca | Nao |
| SHA1 | Media | Nao |
| SHA256 | Forte | Sim |
| SHA512 | Muito Forte | Sim |
| SHA3_256 | Muito Forte | Sim |

### 10.5.4 Obtendo Hashes

```bash
# SHA256
sha256sum mylib-1.0.0.tar.gz

# SHA512
sha512sum mylib-1.0.0.tar.gz

# SHA3-256 (se disponivel)
openssl dgst -sha3-256 mylib-1.0.0.tar.gz
```

### 10.5.5 Multiplas URLs com Fallback

FetchContent suporta multiplas URLs como fallback:

```cmake
FetchContent_Declare(
    mylib
    URL               https://github.com/user/mylib/archive/refs/tags/v1.0.0.tar.gz
    URL_HASH          SHA256=abc123...
    # Fallback mirrors
    URL               https://mirror1.example.com/mylib-1.0.0.tar.gz
    URL               https://mirror2.example.com/mylib-1.0.0.tar.gz
)
```

O CMake tenta cada URL na ordem, parando no primeiro sucesso.

### 10.5.6 Pinning de Versoes com Range

Para projetos que usam versionamento semver, voce pode querer aceitar atualizacoes menores:

```cmake
# Fixar exatamente na versao 10.2.1
GIT_TAG 10.2.1

# Aceitar patches (10.2.x) — NAO recomendado para seguranca
# GIT_TAG 10.2    # Isto pega a tag mais recente 10.2.x
```

**Recomendacao de seguranca**: sempre fixe a versao completa. Atualizacoes devem ser feitas deliberadamente, nao automaticamente.

### 10.5.7 Pinning com Git Submodules Interno

Quando uma dependencia tem subproprios submodules, voce pode controlar o shallow clone:

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY    https://github.com/user/mylib.git
    GIT_TAG           v2.0.0
    GIT_SHALLOW       TRUE
    GIT_PROGRESS      TRUE
    GIT_SUBMODULES    ""           # Nao baixar submodules
    GIT_SUBMODULES_RECURSE FALSE
)
```

Ou especificar submodules especificos:

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY    https://github.com/user/mylib.git
    GIT_TAG           v2.0.0
    GIT_SUBMODULES    "third_party/dep1"
    GIT_SUBMODULES_RECURSE TRUE
)
```

### 10.5.8 Problemas de Pinning

**Tags movidas**: Algumas pessoas fazem force-push em tags. Isso viola a expectativa de que uma tag aponta para um commit fixo.

**Tags apontando para commits diferentes**: `v1.0.0` em um repo pode significar coisas diferentes dependendo de quando voce baixou.

**Solucao**: sempre verifique o hash do commit, nao apenas a tag:

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY    https://github.com/user/mylib.git
    GIT_TAG           v1.0.0
    GIT_SHALLOW       TRUE
)

# Apos populate, verifique o commit
FetchContent_MakeAvailable(mylib)
execute_process(
    COMMAND git -C ${mylib_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE GIT_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
message(STATUS "mylib commit: ${GIT_COMMIT}")
```

---

## 10.6 Security: DOWNLOAD_NO_EXTRACT, TLS verification

### 10.6.1 DOWNLOAD_NO_EXTRACT

Quando voce ja tem o arquivo baixado ou quer controlar a extracao manualmente:

```cmake
FetchContent_Declare(
    mylib
    URL               file:///opt/deps/mylib-1.0.tar.gz
    URL_HASH          SHA256=...
    DOWNLOAD_NO_EXTRACT TRUE
)

FetchContent_MakeAvailable(mylib)

# Extracao manual apos o populate
execute_process(
    COMMAND ${CMAKE_COMMAND} -E tar xzf
        ${mylib_SOURCE_DIR}/../mylib-1.0.tar.gz
    WORKING_DIRECTORY ${mylib_SOURCE_DIR}
)
```

### 10.6.2 DOWNLOAD_NO_EXTRACT e Seguranca

`DOWNLOAD_NO_EXTRACT` e util quando:

1. Voce quer verificar o conteudo antes de extrair
2. O arquivo ja passou por verificacao externa
3. Voce quer extrair em um diretorio com permissoes restritas
4. O conteudo precisa de tratamento especial (descompressao com filters)

### 10.6.3 TLS Verification

O CMake 3.19+ suporta verificacao TLS para downloads via URL. Habilitando `CMAKE_TLS_VERIFY`, voce garante que:

- O certificado SSL e valido
- O nome do hostname corresponde ao certificado
- A cadeia de certificados e completa

```cmake
# Na linha de comando
cmake -B build -DCMAKE_TLS_VERIFY=ON

# Ou no CMakeLists.txt
set(CMAKE_TLS_VERIFY ON)
```

### 10.6.4 Por que TLS Verification Importa

Sem verificacao TLS, um atacante pode:

1. **Man-in-the-middle**: interceptar o download e substituir o conteudo
2. **DNS poisoning**: redirecionar o download para um servidor malicioso
3. **Certificado forjado**: usar um certificado falso para se passar pelo servidor legitimo

Em ambientes corporativos, voce pode precisar de um CA customizado:

```cmake
set(CMAKE_TLS_CAINFO "/path/to/corporate-ca-bundle.crt")
set(CMAKE_TLS_VERIFY ON)
```

### 10.6.5 DOWNLOAD_NO_PROGRESS

Para ambientes onde a saida de progresso e indesejada (logs de CI/CD limpos):

```cmake
FetchContent_Declare(
    mylib
    URL               https://example.com/mylib.tar.gz
    URL_HASH          SHA256=...
    DOWNLOAD_NO_PROGRESS TRUE
)
```

### 10.6.6 Permissoes de Diretorio

Em ambientes com permissoes restritas, voce pode controlar onde os downloads sao armazenados:

```cmake
# Usar um diretorio de cache compartilhado
set(FETCHCONTENT_BASE_DIR "${CMAKE_BINARY_DIR}/_deps" CACHE PATH
    "Base directory for FetchContent downloads")
```

### 10.6.7 DOWNLOAD_EXTRACT_TIMESTAMP

O CMake 3.24 adicionou `DOWNLOAD_EXTRACT_TIMESTAMP` para evitar problemas com timestamps:

```cmake
# Comportamento padrao (pre-3.24): timestamp do arquivo extraido
# Comportamento em 3.24+: warning se nao configurado

set(FETCHCONTENT_TRY_FIND_PACKAGE_MODE ALWAYS)

FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.tar.gz
    URL_HASH          SHA256=...
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
```

Quando `DOWNLOAD_EXTRACT_TIMESTAMP` e TRUE, o CMake usa o timestamp do arquivo original. Quando FALSE (ou padrao em versoes anteriores), usa a data/hora atual, o que pode causar recompilacoes desnecessarias.

### 10.6.8 Ambiente Proxy

Para downloads atras de proxy corporativo:

```bash
# Variaveis de ambiente padrao
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8443
export NO_PROXY=localhost,127.0.0.1,.company.com

# Ou via CMake
cmake -B build \
    -DHTTP_PROXY=http://proxy.company.com:8080 \
    -DHTTPS_PROXY=http://proxy.company.com:8443
```

### 10.6.9 DNS e Seguranca

Em ambientes com DNS customizado, voce pode precisar configurar resolucao:

```cmake
# Forcar resolucao via IPv4 (evita problemas com DNS over IPv6)
set(FETCHCONTENT_UPDATES_DISCONNECTED ON)
```

---

## 10.7 CMAKE_TLS_VERIFY

### 10.7.1 Configuracao Completa

`CMAKE_TLS_VERIFY` controla a verificacao de certificados TLS para todos os downloads do CMake:

```cmake
# Habilitar verificacao TLS
set(CMAKE_TLS_VERIFY ON)

# Configurar CA bundle personalizado
set(CMAKE_TLS_CAINFO "/etc/ssl/certs/ca-certificates.crt")

# Para testes com certificados auto-assinados (NAO em producao)
set(CMAKE_TLS_VERIFY OFF)
set(CMAKE_TLS_CAINFO "")
```

### 10.7.2 Variaveis de Ambiente

```bash
# Variaveis padrao de OpenSSL que o CMake respeita
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export SSL_CERT_DIR=/etc/ssl/certs

# Para certificados customizados
export CURL_CA_BUNDLE=/path/to/ca-bundle.crt
```

### 10.7.3 Verificacao em CI/CD

Em CI/CD, a verificacao TLS deve ser habilitada sempre:

```yaml
# GitHub Actions
- name: Configure CMake
  run: |
    cmake -B build \
      -DCMAKE_TLS_VERIFY=ON \
      -DCMAKE_BUILD_TYPE=Release

# GitLab CI
build:
  script:
    - cmake -B build -DCMAKE_TLS_VERIFY=ON
```

### 10.7.4 Erros Comuns

**Erro: "SSL certificate problem: unable to get local issuer certificate"**

```bash
# Atualizar CA certificates
sudo update-ca-certificates

# Ou especificar o bundle
cmake -B build -DCMAKE_TLS_CAINFO=/etc/ssl/certs/ca-certificates.crt
```

**Erro: "certificate verify failed"**

Pode ser causado por:
1. Certificado expirado
2. Hostname mismatch
3. CA nao reconhecida
4. Proxy interceptando TLS (MITM)

### 10.7.5 Verificacao em Redes Corporativas

Corporacoes frequentemente usam proxies de inspecao TLS que substituem certificados:

```cmake
# Usar o CA bundle da corporacao
set(CMAKE_TLS_CAINFO "/etc/ssl/certs/corporate-ca-bundle.crt")
set(CMAKE_TLS_VERIFY ON)
```

### 10.7.6 FetchContent e TLS

Todo download via `FetchContent_Declare` com `URL` passa pelo `CMAKE_TLS_VERIFY`:

```cmake
set(CMAKE_TLS_VERIFY ON)

FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.tar.gz
    URL_HASH          SHA256=abc123...
    # TLS verification e automatica quando CMAKE_TLS_VERIFY=ON
)
```

Para repositorios Git (via `GIT_REPOSITORY`), a verificacao TLS e controlada pelo proprio Git:

```bash
# Configurar Git para sempre verificar TLS
git config --global http.sslVerify true

# Para repositorios especificos
git config http.sslVerify true
```

### 10.7.7 Debug de Conexoes TLS

Para diagnosticar problemas de TLS:

```bash
# Verificar certificado de um servidor
openssl s_client -connect example.com:443 -showcerts

# Verificar cadeia de certificados
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt server.crt

# Testar download com verbose
curl -v https://example.com/mylib.tar.gz -o /dev/null
```

---

## 10.8 DOWNLOAD_EXTRACT_TIMESTAMP

### 10.8.1 O Problema

Quando voce extrai um arquivo tar, cada arquivo recebe o timestamp de extracao, nao o timestamp original. Isso causa problemas de reprodutibilidade porque:

1. Dois builds identicos podem ter timestamps diferentes
2. Make usa timestamps para determinar se um arquivo precisa ser recompilado
3. Binarios podem diferir apenas por timestamps incorporados

### 10.8.2 Configuracao

```cmake
# CMake 3.24+
FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.tar.gz
    URL_HASH          SHA256=...
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)
```

Quando habilitado, o CMake preserva os timestamps originais dos arquivos dentro do tar.

### 10.8.3 Impacto na Reprodutibilidade

Com `DOWNLOAD_EXTRACT_TIMESTAMP TRUE`:

```bash
# Primeiro build
cmake -B build1
# Timestamps dos arquivos extraidos: 2024-01-15 10:00:00 (originais)

# Segundo build (mesma maquina, hora diferente)
cmake -B build2
# Timestamps dos arquivos extraidos: 2024-01-15 10:00:00 (originais)
# RESULTADO: identico ao build1
```

Sem a configuracao:

```bash
# Primeiro build
cmake -B build1
# Timestamps dos arquivos extraidos: 2024-06-15 14:30:00 (agora)

# Segundo build (meia hora depois)
cmake -B build2
# Timestamps dos arquivos extraidos: 2024-06-15 15:00:00 (agora)
# RESULTADO: timestamps diferentes, possivelmente binarios diferentes
```

### 10.8.4 Compatibilidade

| Versao CMake | Comportamento |
|--------------|---------------|
| < 3.24 | Sem `DOWNLOAD_EXTRACT_TIMESTAMP` |
| 3.24+ | Warning se nao configurado |
| 3.28+ | Pode se tornar padrao TRUE |

### 10.8.5 Migracao

Se voce esta usando CMake anterior a 3.24, implemente manualmente:

```cmake
# Para CMake < 3.24
FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.tar.gz
    URL_HASH          SHA256=...
    # DOWNLOAD_EXTRACT_TIMESTAMP nao existe nesta versao
)

# Apos extrair, ajustar timestamps manualmente
FetchContent_MakeAvailable(mylib)
```

### 10.8.6 Impacto em Build Systems

**Make**: O Make usa timestamps para determinar targets sujos. Com timestamps inconsistentes, o Make pode:
- Pular recompilacoes necessarias
- Realizar recompilacoes desnecessarias

**Ninja**: Ninja usa um modelo mais robusto de verificacao de dependencias, mas timestamps ainda importam para arquivos de sistema.

**MSBuild**: O MSBuild usa um modelo diferente de verificacao, menos sensivel a timestamps.

### 10.8.7 Melhores Praticas

```cmake
# Habilitar sempre em projetos que visam reprodutibilidade
set(FETCHCONTENT_TRY_FIND_PACKAGE_MODE ALWAYS)

cmake_minimum_required(VERSION 3.24)
project(MyProject LANGUAGES CXX)

# Garantir que todos os FetchContent usam DOWNLOAD_EXTRACT_TIMESTAMP
include(FetchContent)

macro(SafeFetchContent name)
    cmake_parse_arguments(ARG "" "URL;URL_HASH;GIT_REPOSITORY;GIT_TAG" "" ${ARGN})

    if(DEFINED ARG_URL)
        FetchContent_Declare(
            ${name}
            URL ${ARG_URL}
            URL_HASH ${ARG_URL_HASH}
            DOWNLOAD_EXTRACT_TIMESTAMP TRUE
        )
    elseif(DEFINED ARG_GIT_REPOSITORY)
        FetchContent_Declare(
            ${name}
            GIT_REPOSITORY ${ARG_GIT_REPOSITORY}
            GIT_TAG ${ARG_GIT_TAG}
        )
    endif()
endmacro()
```

---

## 10.9 Content Locking: content-hash

### 10.9.1 O Conceito

Content-locking vai alem do pinning de versao. Em vez de fixar "qual versao usar", fixa "qual conteudo exato usar". Isso e importante porque:

1. Tags podem ser movidas (force-push)
2. Repositorios podem ser comprometidos
3. Arquivos podem ser re-uploadados com conteudo diferente

### 10.9.2 Implementacao com Hash do Conteudo

```cmake
FetchContent_Declare(
    mylib
    URL               https://example.com/mylib-1.0.0.tar.gz
    URL_HASH          SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
)

# O hash garante que o conteudo e EXATAMENTE o esperado
# Qualquer alteracao, mesmo um bit, causa falha na verificacao
```

### 10.9.3 Lockfiles

Algumas ferramentas gerenciam content-locking automaticamente:

**CMake Presets com hash:**
```json
{
  "configurePresets": [
    {
      "name": "secure",
      "binaryDir": "${sourceDir}/build",
      "cacheVariables": {
        "FETCHCONTENT_FULLY_DISCONNECTED": "ON"
      }
    }
  ]
}
```

**Gerenciamento manual com lockfile:**
```cmake
# Arquivo: cmake/deps-lock.cmake
# Gerado automaticamente — nao editar manualmente

set(MYLIB_VERSION "1.0.0")
set(MYLIB_HASH "SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23")

set(FMT_VERSION "10.2.1")
set(FMT_HASH "SHA256=1234567890abcdef...")

set(GTEST_VERSION "1.14.0")
set(GTEST_HASH "SHA256=abcdef1234567890...")
```

### 10.9.4 Content-Hash vs Version-Hash

| Tipo | O que fixa | Seguranca |
|------|-----------|-----------|
| Version-hash | Versao (tag, branch) | Media — tags podem mudar |
| Content-hash | Conteudo exato do arquivo | Alta — qualquer mudanca e detectada |

### 10.9.5 Atualizacao Controlada

Para atualizar uma dependencia:

1. Baixe a nova versao
2. Calcule o hash
3. Atualize o hash no lockfile
4. Teste o build
5. Commit o lockfile junto com o codigo

```bash
# Baixar e calcular hash
wget https://example.com/mylib-1.1.0.tar.gz
sha256sum mylib-1.1.0.tar.gz
# Output: abc123def456... mylib-1.1.0.tar.gz

# Atualizar cmake/deps-lock.cmake
# set(MYLIB_HASH "SHA256=abc123def456...")
```

### 10.9.6 Verificacao em CI

```yaml
# GitHub Actions
- name: Verify dependency hashes
  run: |
    # Verificar que o lockfile nao foi modificado sem atualizacao de hash
    if git diff --name-only | grep -q "deps-lock.cmake"; then
      echo "Lockfile changed — verifying hashes..."
      cmake -P cmake/verify-hashes.cmake
    fi
```

### 10.9.7 Content-Hash para Git

Para repositorios Git, o equivalente e fixar o SHA do commit:

```cmake
FetchContent_Declare(
    mylib
    GIT_REPOSITORY https://github.com/user/mylib.git
    GIT_TAG        abc123def456789  # SHA completo do commit
)

# Verificar apos populate
FetchContent_MakeAvailable(mylib)
execute_process(
    COMMAND git -C ${mylib_SOURCE_DIR} rev-parse HEAD
    OUTPUT_VARIABLE ACTUAL_COMMIT
    OUTPUT_STRIP_TRAILING_WHITESPACE
)
if(NOT ACTUAL_COMMIT STREQUAL "abc123def456789")
    message(FATAL_ERROR
        "Commit mismatch! Expected abc123def456789, got ${ACTUAL_COMMIT}")
endif()
```

### 10.9.8 Integração com Ferramentas Externas

**Dependabot**: Nao suporta CMake FetchContent nativamente. Voce precisaria de um script customizado.

**Renovate**: Suporta CMakeLists.txt via regex customizada:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["cmake/deps-lock\\.cmake$"],
      "matchStrings": ["set\\((?<depName>\\w+)_VERSION \"(?<currentValue>\\d+\\.\\d+\\.\\d+)\"\\)"],
      "datasourceTemplate": "github-tags"
    }
  ]
}
```

### 10.9.9 Content-Hash e Supply Chain

Content-locking e uma defesa critica contra ataques de supply chain:

1. **Comprometimento de tag**: atacante move tag para commit malicioso. Hash nao muda (se voce fixou o SHA do commit).

2. **Comprometimento de URL**: atacante substitui arquivo no servidor. Hash nao muda.

3. **Comprometimento de mirror**: atacante injeta conteudo diferente em mirror. Hash nao muda.

4. **Comprometimento de desenvolvedor**: atacante injeta backdoor em codigo fonte. Hash muda (se voce usa content-hash e revisa mudancas).

A unica defesa que content-locking NAO oferece e contra comprometimento do proprio repositorio (onde o atacante injeta codigo antes de voce calcular o hash). Para isso, voce precisa de:

- Assinatura de artefatos (Sigstore, GPG)
- Audit log de builds (SLSA)
- Verificacao de proveniencia

---

## 10.10 Submodules vs FetchContent

### 10.10.1 O que sao Git Submodules

Git Submodules permitem que um repositorio Git inclua outro repositorio Git como subdiretorio. Cada submodulo aponta para um commit especifico:

```bash
# Adicionar submodulo
git submodule add https://github.com/user/mylib.git third_party/mylib

# Inicializar submodulos
git submodule update --init --recursive
```

### 10.10.2 Comparacao Detalhada

| Aspecto | Git Submodules | FetchContent |
|---------|---------------|--------------|
| Armazenamento | No repo Git | Download em build time |
| Tamanho do repo | Inclui hash do submodulo | Leve |
| Atualizacao | `git submodule update` | `FetchContent_Populate` |
| Build integration | Manual | Automatica |
| CI/CD | Precisa de `--recursive` | Automatica |
| Seguranca | Hash do commit | Hash do conteudo |
| Controle de versao | Commit SHA | Tag, SHA, ou URL hash |

### 10.10.3 Seguranca dos Submodules

Submodules tem problemas de seguranca conhecidos:

```bash
# Um atacante pode fazer force-push em um submodulo
# O repositorio pai continua apontando para o SHA antigo
# Mas se o SHA foi gerado por hash collision...

# Verificar integridade de submodulos
git submodule foreach 'git verify-commit HEAD'
```

### 10.10.4 Quando Usar Submodules

- Quando voce quer que as dependencias sejam versionadas junto com o codigo
- Quando a rede nao e disponivel em tempo de build
- Quando voce quer revisao explicita de atualizacoes de dependencias
- Quando a equipe ja esta familiarizada com submodules

### 10.10.5 Quando Usar FetchContent

- Quando voce quer integração transparente ao build
- Quando a dependencia e um projeto CMake
- Quando voce quer isolar o build da dependencia
- Quando voce quer usar gerenciadores de pacotes externos

### 10.10.6 Hibrindo: Submodules + FetchContent

Alguns projetos usam submodules para armazenar as fontes e FetchContent para integra-las ao build:

```cmake
# As fontes estao no submodule em third_party/mylib
# Mas a integracao ao build e feita via FetchContent

include(FetchContent)

# Se o submodulo ja existe, usar localmente
if(EXISTS "${CMAKE_SOURCE_DIR}/third_party/mylib/CMakeLists.txt")
    add_subdirectory(
        ${CMAKE_SOURCE_DIR}/third_party/mylib
        ${CMAKE_BINARY_DIR}/third_party/mylib
        EXCLUDE_FROM_ALL
    )
else()
    # Caso contrario, baixar via FetchContent
    FetchContent_Declare(
        mylib
        GIT_REPOSITORY https://github.com/user/mylib.git
        GIT_TAG        v1.0.0
    )
    FetchContent_MakeAvailable(mylib)
endif()
```

### 10.10.7 Migração de Submodules para FetchContent

```bash
# 1. Remover o submodule
git submodule deinit -f third_party/mylib
git rm -f third_party/mylib
rm -rf .git/modules/third_party/mylib

# 2. Adicionar ao CMakeLists.txt via FetchContent
# 3. Atualizar .gitignore para ignorar _deps/
# 4. Atualizar CI/CD para nao precisar de --recursive
```

### 10.10.8 Performance

| Aspecto | Submodules | FetchContent |
|---------|-----------|--------------|
| Clone inicial | Lento (histrico completo) | Lento (primeira vez) |
| Updates | `git submodule update` (lento) | `FETCHCONTENT_UPDATES_DISCONNECTED` |
| Disk usage | Compartilhado com .git | Separado em _deps/ |
| Parallelismo | Limitado | Melhor (build paralelo) |

---

## 10.11 CVE-2024-3094: XZ Utils via build system

### 10.11.1 Resumo do CVE

CVE-2024-3094 e uma das vulnerabilidades de supply chain mais significativas da historia do software. Um backdoor foi inserido nas versoes 5.6.0 e 5.6.1 do XZ Utils, uma biblioteca de compressao amplamente usada em sistemas Linux.

### 10.11.2 Timeline do Ataque

**Fevereiro 2024**: Atacador ("Jia Tan") comeca a contribuir para o projeto XZ Utils, ganhando confianca do mantenedor.

**Marco 2024**: Atacador injeta codigo malicioso nos scripts de build do XZ Utils. O backdoor e sutil — modifica arquivos m4 que controlam o build do liblzma.

**29 Marco 2024**: Versoes 5.6.0 e 5.6.1 sao lancadas com o backdoor.

**Abril 2024**: Andres Freund (Microsoft/PostgreSQL) descobre o backdoor apos notar lentidao inexplacavel no SSH.

### 10.11.3 Como o Backdoor Funcionava

O backdoor nao estava no codigo C do XZ Utils. Estava nos **scripts de build**:

1. Um script m4 (`build-to-host.m4`) verificava se o build estava sendo feito em um sistema Debian/Ubuntu
2. Se sim, modificava o build do liblzma para incluir o backdoor
3. O backdoor hookava o OpenSSH via libsystemd (que dependia do liblzma)
4. Isso permitia autenticacao remota no SSH com uma chave secreta do atacador

### 10.11.4 Implicacoes para Build Systems

O CVE-2024-3094 demonstra que:

1. **Scripts de build sao codigo**: m4, CMakeLists.txt, Makefiles — todos podem conter backdoors
2. **Compilacao e executacao**: o build system executa codigo, entao confiar em scripts de build e tao perigoso quanto confiar em codigo executavel
3. **Ataques de supply chain podem ser sofisticados**: o atacador passou meses ganhando confianca antes de injetar o backdoor
4. **Detecção e dificil**: o backdoor era sutil e so era ativado em ambientes especificos

### 10.11.5 Analise da Vulnerabilidade em CMake

Se o XZ Utils usasse CMake em vez de Autotools, o ataque poderia ter sido diferente:

```cmake
# CENARIO HIPOTETICO: backdoor em CMakeLists.txt
cmake_minimum_required(VERSION 3.20)

# Codigo aparentemente normal
add_library(lzma src/lzma_decoder.c src/lzma_encoder.c)

# Backdoor sutil: modifica comportamento em versoes especificas
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/.attacker_key")
    target_compile_definitions(lzma PRIVATE
        BACKDOOR_ENABLED=1
        BACKDOOR_KEY_FILE="${CMAKE_CURRENT_SOURCE_DIR}/.attacker_key"
    )
endif()
```

### 10.11.6 Defesas em Build Systems

**Verificacao de hash**: Se voce verificasse o hash do XZ Utils 5.6.0, detectaria a mudanca no script de build:

```cmake
FetchContent_Declare(
    xz_utils
    URL               https://tukaani.org/xz/xz-5.6.0.tar.gz
    URL_HASH          SHA256=...
    # O hash do 5.6.0 E diferente do 5.5.0
    # Mas se voce so olhou o hash do 5.5.0 e assumiu que o 5.6.0 era igual...
)
```

**Pinning de versao**: Se voce fixou no 5.5.0 e nao atualizou para 5.6.0, nao foi afetado.

**Auditoria de scripts de build**: Revisar mudancas em scripts de build (m4, CMakeLists.txt) e tao importante quanto revisar codigo-fonte.

### 10.11.7 Defesas Especificas para FetchContent

```cmake
include(FetchContent)

# 1. SEMPRE usar hash de conteudo
FetchContent_Declare(
    xz_utils
    URL               https://tukaani.org/xz/xz-5.5.2.tar.gz
    URL_HASH          SHA256=976688c256e03a03b28689b27ad537d0ea6d21876fb...
    # Use 5.5.2, NAO 5.6.0 ou 5.6.1
)

# 2. Verificar hash apos download
FetchContent_MakeAvailable(xz_utils)

# 3. Auditar scripts de build (para m4/Autotools)
# Verificar se ha mudancas suspeitas nos scripts de build
execute_process(
    COMMAND grep -r "backdoor\|exec\|system\|eval" 
        ${xz_utils_SOURCE_DIR}/m4/
    OUTPUT_VARIABLE SUSPICIOUS_CONTENT
)
if(SUSPICIOUS_CONTENT)
    message(WARNING "Suspicious content in build scripts: ${SUSPICIOUS_CONTENT}")
endif()
```

### 10.11.8 Monitoramento Continuo

```yaml
# GitHub Actions: monitorar atualizacoes de dependencias criticas
- name: Check for security advisories
  uses: actions/dependency-review-action@v3
  with:
    fail-on-severity: critical
```

```cmake
# Script de verificacao de seguranca
function(verify_dependency_security name hash)
    # Verificar se o hash esta na lista de hashes conhecidos
    file(READ "${CMAKE_SOURCE_DIR}/cmake/known-hashes.txt" KNOWN_HASHES)
    string(FIND "${KNOWN_HASHES}" "${hash}" HASH_FOUND)
    if(HASH_FOUND EQUAL -1)
        message(FATAL_ERROR
            "Unknown hash for ${name}: ${hash}. "
            "This dependency may have been tampered with.")
    endif()
endfunction()
```

### 10.11.9 Licoes Aprendidas

1. **Nunca confie em scripts de build de terceiros** sem auditoria
2. **Use hash de conteudo**, nao apenas versao
3. **Monitore atualizacoes** de dependencias criticas
4. **Isole builds** de dependencias nao-confiaveis
5. **Assine artefatos** quando possivel (Sigstore, GPG)
6. **Implemente SLSA** para rastreabilidade de build

### 10.11.10 Respostas da Comunidade

Apos o CVE-2024-3094, varias iniciativas surgiram:

- **SLSA (Supply chain Levels for Software Artifacts)**: framework para garantir integridade de artefatos
- **Sigstore**: assinatura e verificacao de artefatos de software
- **in-toto**: framework de seguranca de supply chain
- **Guac**: grafo de dependencias de software
- **Dependency-Graph**: analise automatizada de dependencias

---

## 10.12 Exemplo: FetchContent seguro com hash

### 10.12.1 Estrutura do Projeto

```
myproject/
  CMakeLists.txt
  cmake/
    deps-lock.cmake
    verify-hashes.cmake
    SecureFetchContent.cmake
  src/
    main.cpp
  tests/
    CMakeLists.txt
```

### 10.12.2 Arquivo de Lock

```cmake
# cmake/deps-lock.cmake
# Gerado em 2024-06-15 — NAO EDITAR MANUALMENTE
# Atualizar via: cmake -P cmake/update-hash.cmake <dependency> <url>

set(DEPS_LOCK_VERSION "1")

# fmt 10.2.1
set(FMT_VERSION "10.2.1")
set(FMT_HASH_TYPE "SHA256")
set(FMT_HASH "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
set(FMT_URL "https://github.com/fmtlib/fmt/archive/refs/tags/10.2.1.tar.gz")

# googletest 1.14.0
set(GTEST_VERSION "1.14.0")
set(GTEST_HASH_TYPE "SHA256")
set(GTEST_HASH "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
set(GTEST_URL "https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz")

# nlohmann_json 3.11.3
set(JSON_VERSION "3.11.3")
set(JSON_HASH_TYPE "SHA256")
set(JSON_HASH "0d8ef5af7f9794e3263480193c491549b2ba6cc74bb018906202ada498a79406")
set(JSON_URL "https://github.com/nlohmann/json/archive/refs/tags/v3.11.3.tar.gz")
```

### 10.12.3 Modulo de FetchContent Seguro

```cmake
# cmake/SecureFetchContent.cmake
include(FetchContent)
include(CMakeParseArguments)

# Incluir lockfile
include(${CMAKE_CURRENT_SOURCE_DIR}/cmake/deps-lock.cmake)

# Macro para fetch seguro com verificacao de hash
macro(SecureFetchContent)
    cmake_parse_arguments(ARG "" "NAME;EXCLUDE_FROM_ALL" "ADDITIONAL_OPTIONS" ${ARGN})

    # Construir argumentos do FetchContent_Declare
    set(DECLARE_ARGS
        ${ARG_NAME}
        URL ${${UPPER_ARG_NAME}_URL}
        URL_HASH ${${UPPER_ARG_NAME}_HASH_TYPE}=${${UPPER_ARG_NAME}_HASH}
    )

    # Adicionar opcoes adicionais
    list(APPEND DECLARE_ARGS ${ARG_ADDITIONAL_OPTIONS})

    # Declarar
    FetchContent_Declare(${DECLARE_ARGS})

    # Popular
    FetchContent_MakeAvailable(${ARG_NAME})
endmacro()

# Funcao para verificar hash apos download
function(VerifyDependencyHash name expected_hash)
    FetchContent_GetProperties(${name})
    if(NOT ${name}_SOURCE_DIR)
        message(FATAL_ERROR "Dependency ${name} not populated")
    endif()

    # Calcular hash do diretorio de fontes
    file(GLOB_RECURSE SOURCE_FILES "${${name}_SOURCE_DIR}/*")
    foreach(file ${SOURCE_FILES})
        file(SHA256 "${file}" FILE_HASH)
        string(APPEND combined_hash "${FILE_HASH}")
    endforeach()
    file(SHA256_STRING "${combined_hash}" DIRECTORY_HASH)

    # Verificar (hash do diretorio, nao do tarball)
    # O hash do tarball e verificado pelo FetchContent automaticamente
    message(STATUS "${name}: source directory hash = ${DIRECTORY_HASH}")
endfunction()

# Funcao para listar todas as dependencias
function(ListDependencies)
    message(STATUS "=== Locked Dependencies ===")
    message(STATUS "Lock version: ${DEPS_LOCK_VERSION}")
    message(STATUS "fmt: ${FMT_VERSION}")
    message(STATUS "googletest: ${GTEST_VERSION}")
    message(STATUS "nlohmann_json: ${JSON_VERSION}")
endfunction()
```

### 10.12.4 CMakeLists.txt Principal

```cmake
cmake_minimum_required(VERSION 3.24)
project(MyProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Seguranca: habilitar verificacao TLS
set(CMAKE_TLS_VERIFY ON)

# Habilitar DOWNLOAD_EXTRACT_TIMESTAMP para reprodutibilidade
set(DOWNLOAD_EXTRACT_TIMESTAMP TRUE)

# Incluir modulo seguro
include(cmake/SecureFetchContent.cmake)

# Listar dependencias bloqueadas
ListDependencies()

# Buscar dependencias
SecureFetchContent(NAME fmt)
SecureFetchContent(NAME googletest)
SecureFetchContent(NAME nlohmann_json)

# Verificar hashes
VerifyDependencyHash(fmt "${FMT_HASH}")
VerifyDependencyHash(googletest "${GTEST_HASH}")
VerifyDependencyHash(nlohmann_json "${JSON_HASH}")

# Configuracoes do projeto
add_executable(myapp
    src/main.cpp
)

target_link_libraries(myapp PRIVATE
    fmt::fmt
    nlohmann_json::nlohmann_json
)

# Testes
enable_testing()
add_executable(myapp_tests tests/test_main.cpp)
target_link_libraries(myapp_tests PRIVATE
    GTest::gtest_main
    fmt::fmt
    nlohmann_json::nlohmann_json
)
add_test(NAME MyTests COMMAND myapp_tests)
```

### 10.12.5 Script de Verificacao

```cmake
# cmake/verify-hashes.cmake
# Executar: cmake -P cmake/verify-hashes.cmake

include(cmake/deps-lock.cmake)

function(verify_hash name url hash_type expected_hash)
    message(STATUS "Verifying ${name}...")
    
    # Baixar arquivo temporario
    set(temp_file "${CMAKE_CURRENT_BINARY_DIR}/temp_${name}.tar.gz")
    file(DOWNLOAD
        "${url}"
        "${temp_file}"
        EXPECTED_HASH ${hash_type}=${expected_hash}
        STATUS download_status
    )
    
    list(GET download_status 0 status_code)
    if(NOT status_code EQUAL 0)
        list(GET download_status 1 error_message)
        message(FATAL_ERROR "Failed to download ${name}: ${error_message}")
    endif()
    
    message(STATUS "  ${name}: hash verified OK")
    file(REMOVE "${temp_file}")
endfunction()

# Verificar todas as dependencias
verify_hash("fmt" "${FMT_URL}" "${FMT_HASH_TYPE}" "${FMT_HASH}")
verify_hash("googletest" "${GTEST_URL}" "${GTEST_HASH_TYPE}" "${GTEST_HASH}")
verify_hash("nlohmann_json" "${JSON_URL}" "${JSON_HASH_TYPE}" "${JSON_HASH}")

message(STATUS "All dependency hashes verified successfully!")
```

### 10.12.6 Script de Atualizacao

```bash
#!/bin/bash
# cmake/update-hash.sh
# Uso: ./cmake/update-hash.sh <dependency> <url>

set -e

DEP_NAME=$1
DEP_URL=$2

if [ -z "$DEP_NAME" ] || [ -z "$DEP_URL" ]; then
    echo "Uso: $0 <dependency> <url>"
    exit 1
fi

echo "Downloading $DEP_NAME from $DEP_URL..."

# Baixar
TEMP_FILE=$(mktemp)
curl -L -o "$TEMP_FILE" "$DEP_URL"

# Calcular hash
HASH=$(sha256sum "$TEMP_FILE" | awk '{print $1}')

echo "Hash: $HASH"
echo "Por favor, atualize manualmente em cmake/deps-lock.cmake"

# Limpar
rm "$TEMP_FILE"
```

### 10.12.7 Pipeline CI/CD

```yaml
# .github/workflows/secure-build.yml
name: Secure Build

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify dependency hashes
        run: cmake -P cmake/verify-hashes.cmake
      
      - name: Configure
        run: |
          cmake -B build \
            -DCMAKE_TLS_VERIFY=ON \
            -DCMAKE_BUILD_TYPE=Release \
            -DFETCHCONTENT_FULLY_DISCONNECTED=OFF
        
      - name: Build
        run: cmake --build build --config Release
      
      - name: Test
        run: ctest --test-dir build --output-on-failure
```

---

## 10.13 Exercicios

### Exercicio 10.1: FetchContent Basico

**Objetivo**: Integrar uma dependencia via FetchContent.

**Instrucoes**:
1. Crie um projeto CMake que use FetchContent para baixar a biblioteca `fmt`
2. Fixe a versao 10.2.1
3. Use a biblioteca em um programa simples que imprima "Hello, World!"
4. Verifique que o build funciona

**Criterio de aceite**:
- FetchContent_Declare configurado corretamente
- Programa compila e executa
- Usando `FetchContent_MakeAvailable`

### Exercicio 10.2: Pinning com Hash

**Objetivo**: Implementar verificacao de hash para downloads.

**Instrucoes**:
1. Modifique o exercicio anterior para usar URL em vez de GIT_REPOSITORY
2. Calcule o hash SHA256 do tarball
3. Configure `URL_HASH` no FetchContent_Declare
4. Teste que o build funciona
5. Teste que mudar o hash causa erro

**Criterio de aceite**:
- Hash SHA256 configurado corretamente
- Build funciona com hash correto
- Build falha com hash incorreto

### Exercicio 10.3: ExternalProject

**Objetivo**: Configurar um build externo isolado.

**Instrucoes**:
1. Use `ExternalProject_Add` para baixar e compilar a biblioteca `zlib`
2. Crie uma imported library para usar o zlib
3. Compile um programa que use zlib
4. Verifique que o build do zlib e isolado do seu projeto

**Criterio de aceite**:
- ExternalProject_Add configurado corretamente
- Imported library criada
- Programa compila e linka com zlib
- Build do zlib e visivelmente separado

### Exercicio 10.4: Controle Granular

**Objetivo**: Usar FetchContent_Populate com controle manual.

**Instrucoes**:
1. Baixe o GoogleTest via FetchContent
2. Use `FetchContent_Populate` em vez de `FetchContent_MakeAvailable`
3. Configure `EXCLUDE_FROM_ALL`
4. Desabilite testos e exemplos do GoogleTest
5. Crie testes que usam o GoogleTest

**Criterio de aceite**:
- FetchContent_Populate usado corretamente
- EXCLUDE_FROM_ALL configurado
- Testes do GoogleTest desabilitados
- Seus testes funcionam

### Exercicio 10.5: TLS Verification

**Objetivo**: Configurar verificacao TLS para downloads.

**Instrucoes**:
1. Habilite `CMAKE_TLS_VERIFY` no seu projeto
2. Configure `CMAKE_TLS_CAINFO` para o CA bundle do sistema
3. Teste que downloads funcionam
4. Documente o que acontece quando TLS verification e desabilitado

**Criterio de aceite**:
- CMAKE_TLS_VERIFY=ON configurado
- Downloads funcionam
- Documentacao do comportamento

### Exercicio 10.6: Content Locking

**Objetivo**: Implementar sistema de content-locking.

**Instrucoes**:
1. Crie um arquivo `cmake/deps-lock.cmake` com 3 dependencias
2. Implemente uma macro `SecureFetchContent` que use o lockfile
3. Implemente verificacao de hash apos download
4. Crie um script de verificacao (cmake -P)
5. Integre ao CI/CD

**Criterio de aceite**:
- Lockfile criado com 3 dependencias
- Macro SecureFetchContent funcional
- Script de verificacao funcional
- CI/CD integra verificacao

### Exercicio 10.7: Submodules vs FetchContent

**Objetivo**: Comparar abordagens de gerenciamento de dependencias.

**Instrucoes**:
1. Crie um projeto que use submodules para uma dependencia
2. Migre para FetchContent
3. Documente as diferencas encontradas
4. Analise implicacoes de seguranca

**Criterio de aceite**:
- Projeto com submodules funcional
- Projeto com FetchContent funcional
- Documentacao comparativa
- Analise de seguranca

### Exercicio 10.8: CVE Analysis

**Objetivo**: Analisar o CVE-2024-3094 e implementar defesas.

**Instrucoes**:
1. Pesquise o CVE-2024-3094 (XZ Utils backdoor)
2. Documente como o ataque funcionava
3. Implemente defesas no seu projeto usando FetchContent
4. Crie um script de auditoria de dependencias
5. Teste que o script detectaria o tipo de ataque

**Criterio de aceite**:
- Documentacao do CVE
- Defesas implementadas
- Script de auditoria funcional
- Teste de deteccao

---

## 10.14 Referencias

### Documentacao Oficial do CMake

1. **FetchContent**: https://cmake.org/cmake/help/latest/module/FetchContent.html
2. **ExternalProject**: https://cmake.org/cmake/help/latest/module/ExternalProject.html
3. **CMAKE_TLS_VERIFY**: https://cmake.org/cmake/help/latest/variable/CMAKE_TLS_VERIFY.html
4. **DOWNLOAD_EXTRACT_TIMESTAMP**: https://cmake.org/cmake/help/latest/module/ExternalProject.html
5. **FetchContent_MakeAvailable**: https://cmake.org/cmake/help/latest/module/FetchContent.html#fetchcontent-makeavailable
6. **FetchContent_Populate**: https://cmake.org/cmake/help/latest/module/FetchContent.html#fetchcontent-populate

### Artigos e Publicacoes

7. "Secure CMake: Best Practices for Build Security" - Kitware Blog
8. "Supply Chain Security for C/C++ Projects" - ACCU Conference
9. "Building Secure C++ Applications with CMake" - Meeting C++
10. "Reproducible Builds with CMake" - FOSDEM

### CVEs e Seguranca

11. **CVE-2024-3094**: https://nvd.nist.gov/vuln/detail/CVE-2024-3094
12. **CVE-2023-44487**: https://nvd.nist.gov/vuln/detail/CVE-2023-44487
13. **XZ Utils Backdoor Analysis**: https://research.swtch.com/xz-timeline
14. **SLSA Framework**: https://slsa.dev/
15. **Sigstore**: https://www.sigstore.dev/

### Ferramentas

16. **CMake Presets**: https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html
17. **vcpkg**: https://vcpkg.io/
18. **Conan**: https://conan.io/
19. **Dependabot**: https://github.com/dependabot
20. **Renovate**: https://www.mend.io/renovate/

### Comunidade

21. **CMake Discourse**: https://discourse.cmake.org/
22. **CMake Reddit**: https://www.reddit.com/r/cmake/
23. **CMake Slack**: https://cmake-slack.herokuapp.com/

---

*[Proximo capitulo: 11 — vcpkg e Conan](11-vcpkg-conan.md)*

---

## 10.15 Aprofundamento: Padrões Avançados de FetchContent

### 10.15.1 FetchContent com Variante de Build

Quando sua dependência suporta múltiplas variantes (static, shared, debug, release), você pode controlar isso via FetchContent:

```cmake
# Variável global que controla o tipo de biblioteca
option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

# Buscar fmt
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.2.1
)

# Antes de MakeAvailable, definir opções da dependência
set(FMT_INSTALL ON CACHE BOOL "" FORCE)
set(FMT_TEST OFF CACHE BOOL "" FORCE)
set(FMT_DOC OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(fmt)
```

### 10.15.2 FetchContent com Opções Condicionalmente

```cmake
FetchContent_Declare(
    glfw
    GIT_REPOSITORY https://github.com/glfw/glfw.git
    GIT_TAG        3.3.9
    GIT_SHALLOW    TRUE
)

# Configurações antes do MakeAvailable
set(GLFW_BUILD_DOCS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(GLFW_BUILD_INSTALL OFF CACHE BOOL "" FORCE)

# Se Vulkan não estiver disponível, desabilitar
if(NOT Vulkan_FOUND)
    set(GLFW_VULKAN_STATIC OFF CACHE BOOL "" FORCE)
endif()

FetchContent_MakeAvailable(glfw)
```

### 10.15.3 Padrão de Versão Flexível

Crie um módulo que suporte versões flexíveis com fallback:

```cmake
# cmake/FlexibleFetchContent.cmake

# Lista de versões suportadas (mais recente primeiro)
set(FMT_SUPPORTED_VERSIONS "10.2.1" "10.1.1" "10.0.0" "9.1.0")

# Versão desejada
set(FMT_DESIRED_VERSION "10.2.1" CACHE STRING "Desired fmt version")

# Encontrar a versão mais recente disponível
set(FMT_SELECTED_VERSION "")
foreach(version ${FMT_SUPPORTED_VERSIONS})
    if("${version}" VERSION_GREATER_OR_EQUAL "${FMT_DESIRED_VERSION}")
        set(FMT_SELECTED_VERSION "${version}")
        break()
    endif()
endforeach()

# Fallback para a versão mais antiga suportada
if(NOT FMT_SELECTED_VERSION)
    list(GET FMT_SUPPORTED_VERSIONS -1 FMT_SELECTED_VERSION)
endif()

message(STATUS "Using fmt version: ${FMT_SELECTED_VERSION}")

# Calcular hash (você pode ter um mapa de versão->hash)
set(FMT_HASH_MAP
    "10.2.1:SHA256=abc123..."
    "10.1.1:SHA256=def456..."
    "10.0.0:SHA256=ghi789..."
    "9.1.0:SHA256=jkl012..."
)

# Buscar hash correspondente
set(FMT_HASH_ENTRY "")
foreach(entry ${FMT_HASH_MAP})
    string(REPLACE ":" ";" parts "${entry}")
    list(GET parts 0 hash_version)
    list(GET parts 1 hash_value)
    if("${hash_version}" STREQUAL "${FMT_SELECTED_VERSION}")
        set(FMT_HASH_ENTRY "${hash_value}")
        break()
    endif()
endforeach()

# Declarar com hash
FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        ${FMT_SELECTED_VERSION}
    # Se tiver URL direta, usar:
    # URL https://github.com/fmtlib/fmt/archive/refs/tags/${FMT_SELECTED_VERSION}.tar.gz
    # URL_HASH ${FMT_HASH_ENTRY}
)

FetchContent_MakeAvailable(fmt)
```

### 10.15.4 FetchContent com Cache Compartilhado

Em ambientes com múltiplos projetos, compartilhe o cache de downloads:

```cmake
# Todos os projetos usam o mesmo diretório de cache
set(FETCHCONTENT_BASE_DIR "${HOME}/.cache/cmake-fetchcontent" CACHE PATH
    "Base directory for all FetchContent downloads")

# Ou por projeto (compartilhando entre builds)
set(FETCHCONTENT_BASE_DIR "${CMAKE_SOURCE_DIR}/.cmake-cache" CACHE PATH
    "Base directory for FetchContent downloads")
```

### 10.15.5 FetchContent com DOWNLOAD_EXTRACT_TIMESTAMP em Versões Anteriores

Para CMake anterior a 3.24, implemente manualmente:

```cmake
# Função helper para CMake < 3.24
function(SafeFetchContentDeclare name)
    cmake_parse_arguments(ARG "" "URL;URL_HASH;GIT_REPOSITORY;GIT_TAG;DOWNLOAD_EXTRACT_TIMESTAMP" "" ${ARGN})

    set(DECLARE_ARGS "${name}")

    if(DEFINED ARG_URL)
        list(APPEND DECLARE_ARGS URL "${ARG_URL}")
        if(DEFINED ARG_URL_HASH)
            list(APPEND DECLARE_ARGS URL_HASH "${ARG_URL_HASH}")
        endif()
    elseif(DEFINED ARG_GIT_REPOSITORY)
        list(APPEND DECLARE_ARGS GIT_REPOSITORY "${ARG_GIT_REPOSITORY}")
        if(DEFINED ARG_GIT_TAG)
            list(APPEND DECLARE_ARGS GIT_TAG "${ARG_GIT_TAG}")
        endif()
    endif()

    # DOWNLOAD_EXTRACT_TIMESTAMP só existe no CMake 3.24+
    if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.24")
        if(DEFINED ARG_DOWNLOAD_EXTRACT_TIMESTAMP)
            list(APPEND DECLARE_ARGS DOWNLOAD_EXTRACT_TIMESTAMP "${ARG_DOWNLOAD_EXTRACT_TIMESTAMP}")
        endif()
    endif()

    # Chamar FetchContent_Declare com argumentos construídos
    FetchContent_Declare(${DECLARE_ARGS})
endfunction()
```

### 10.15.6 FetchContent com Symlinks

Em sistemas que precisam de symlinks para paths específicos:

```cmake
FetchContent_Declare(
    llvm
    GIT_REPOSITORY https://github.com/llvm/llvm-project.git
    GIT_TAG        llvmorg-17.0.6
    GIT_SHALLOW    TRUE
    GIT_SUBMODULES ""  # Não baixar submodules (economiza tempo)
)

FetchContent_MakeAvailable(llvm)

# Criar symlinks para headers específicos
set(LLVM_INCLUDE_DIR "${llvm_SOURCE_DIR}/llvm/include")
set(LLVM_BUILD_INCLUDE_DIR "${llvm_BINARY_DIR}/include")

# Symlink para headers gerados
file(CREATE_LINK
    "${LLVM_BUILD_INCLUDE_DIR}"
    "${LLVM_INCLUDE_DIR}/llvm/Config"
    SYMBOLIC
)
```

### 10.15.7 FetchContent com Custom Download Command

Para downloads que precisam de autenticação ou configuração especial:

```cmake
include(ExternalProject)

# Para downloads complexos, use ExternalProject com custom download
ExternalProject_Add(
    authenticated_lib
    URL               https://private.example.com/lib-1.0.tar.gz
    URL_HASH          SHA256=...
    HTTP_HEADER       "Authorization: Bearer ${AUTH_TOKEN}"
    HTTP_HEADER       "Accept: application/octet-stream"
    TLS_VERIFY        ON
    # ...
)

# OU use file(DOWNLOAD) + FetchContent
file(DOWNLOAD
    "https://private.example.com/lib-1.0.tar.gz"
    "${CMAKE_CURRENT_BINARY_DIR}/lib-1.0.tar.gz"
    HTTPHEADER "Authorization: Bearer ${AUTH_TOKEN}"
    EXPECTED_HASH SHA256=...
    TLS_VERIFY ON
)

FetchContent_Declare(
    authenticated_lib
    URL               "${CMAKE_CURRENT_BINARY_DIR}/lib-1.0.tar.gz"
    URL_HASH          SHA256=...
    DOWNLOAD_NO_EXTRACT TRUE
)

FetchContent_MakeAvailable(authenticated_lib)
```

---

## 10.16 Padrões de Arquitetura para Gerenciamento de Dependências

### 10.16.1 Camada de Dependências

Separe gerenciamento de dependências em um módulo dedicado:

```cmake
# cmake/Dependencies.cmake

# Este arquivo é incluído no CMakeLists.txt principal
# e gerencia TODAS as dependências externas

include(FetchContent)
include(cmake/SecureFetchContent.cmake)

# Grupo 1: Dependências obrigatórias
# Sempre presentes, essenciais para o projeto
set(DEPENDENCIES_MANDATORY
    fmt
    nlohmann_json
)

# Grupo 2: Dependências de desenvolvimento
# Apenas em modo desenvolvimento/testes
set(DEPENDENCIES_DEV
    googletest
    benchmark
)

# Grupo 3: Dependências opcionais
# Dependem de features habilitadas
set(DEPENDENCIES_OPTIONAL "")

if(ENABLE_NETWORKING)
    list(APPEND DEPENDENCIES_OPTIONAL curl)
endif()

if(ENABLE_DATABASE)
    list(APPEND DEPENDENCIES_OPTIONAL sqlite3)
endif()

# Função para buscar dependências
function(FetchDependencies)
    foreach(dep ${DEPENDENCIES_MANDATORY})
        message(STATUS "Fetching mandatory dependency: ${dep}")
        SecureFetchContent(NAME ${dep})
    endforeach()

    if(CMAKE_BUILD_TYPE STREQUAL "Debug" OR ENABLE_TESTING)
        foreach(dep ${DEPENDENCIES_DEV})
            message(STATUS "Fetching dev dependency: ${dep}")
            SecureFetchContent(NAME ${dep})
        endforeach()
    endif()

    foreach(dep ${DEPENDENCIES_OPTIONAL})
        message(STATUS "Fetching optional dependency: ${dep}")
        SecureFetchContent(NAME ${dep})
    endforeach()
endfunction()

# Função para listar dependências
function(ListDependencies)
    message(STATUS "=== Dependency Summary ===")
    message(STATUS "Mandatory: ${DEPENDENCIES_MANDATORY}")
    message(STATUS "Dev: ${DEPENDENCIES_DEV}")
    message(STATUS "Optional: ${DEPENDENCIES_OPTIONAL}")
endfunction()
```

### 10.16.2 Padrão de Wrapper Target

Crie targets wrapper para isolar dependências:

```cmake
# cmake/DependencyWrappers.cmake

# Wrapper para fmt
add_library(dep_fmt INTERFACE)
target_link_libraries(dep_fmt INTERFACE fmt::fmt)
target_compile_features(dep_fmt INTERFACE cxx_std_17)

# Wrapper para nlohmann_json
add_library(dep_json INTERFACE)
target_link_libraries(dep_json INTERFACE nlohmann_json::nlohmann_json)

# Wrapper para GoogleTest (apenas em debug/test)
if(CMAKE_BUILD_TYPE STREQUAL "Debug" OR ENABLE_TESTING)
    add_library(dep_gtest INTERFACE)
    target_link_libraries(dep_gtest INTERFACE GTest::gtest_main)
endif()

# Interface library que encapsula todas as dependências
add_library(project_dependencies INTERFACE)
target_link_libraries(project_dependencies INTERFACE
    dep_fmt
    dep_json
)

if(TARGET dep_gtest)
    target_link_libraries(project_dependencies INTERFACE dep_gtest)
endif()
```

### 10.16.3 Padrão de Política de Dependências

```cmake
# cmake/DependencyPolicy.cmake

# Política: todas as dependências devem ter hash verificado
option(DEPENDENCY_REQUIRE_HASH "Require hash for all dependencies" ON)

# Política: não usar HEAD ou branches como versão
option(DEPENDENCY_FORBID_HEAD "Forbid HEAD as dependency version" ON)

# Política: máximo de dependências (evita dependência excessiva)
set(DEPENDENCY_MAX_COUNT 10 CACHE STRING "Maximum number of dependencies")

# Verificar políticas
function(CheckDependencyPolicy name)
    if(DEPENDENCY_FORBID_HEAD)
        if("${${name}_VERSION}" STREQUAL "HEAD" OR
           "${${name}_GIT_TAG}" STREQUAL "HEAD")
            message(FATAL_ERROR
                "Policy violation: ${name} uses HEAD as version. "
                "Use a specific tag or commit SHA.")
        endif()
    endif()
endfunction()

# Contar dependências
macro(CountDependencies)
    math(EXPR DEP_COUNT "${DEPENDENCIES_MANDATORY_COUNT} + ${DEPENDENCIES_DEV_COUNT} + ${DEPENDENCIES_OPTIONAL_COUNT}")
    if(DEP_COUNT GREATER DEPENDENCY_MAX_COUNT)
        message(WARNING
            "Too many dependencies: ${DEP_COUNT} > ${DEPENDENCY_MAX_COUNT}. "
            "Consider reducing external dependencies.")
    endif()
endmacro()
```

---

## 10.17 Cenarios Reais e Soluções

### 10.17.1 Cenário: Projeto que Precisa de OpenSSL

```cmake
# Problema: OpenSSL não é CMake-native, precisa de ExternalProject

include(ExternalProject)

# Detectar plataforma
if(APPLE)
    set(OPENSSL_PLATFORM "darwin64-x86_64-cc")
elseif(UNIX)
    set(OPENSSL_PLATFORM "linux-x86_64")
else()
    message(FATAL_ERROR "Unsupported platform for OpenSSL build")
endif()

ExternalProject_Add(
    openssl_external
    URL               https://www.openssl.org/source/openssl-3.2.1.tar.gz
    URL_HASH          SHA256=840af5366ab9b522ea3b6d7d3c57151c8e571e0453282b7a...
    CONFIGURE_COMMAND
        <SOURCE_DIR>/Configure
            ${OPENSSL_PLATFORM}
            --prefix=<INSTALL_DIR>
            --openssldir=<INSTALL_DIR>/ssl
            no-shared
            no-tests
            no-comp
            no-ssl3
            no-weak-ssl-ciphers
    BUILD_COMMAND
        make -j${NPROC}
    INSTALL_COMMAND
        make install_sw
    BUILD_IN_SOURCE 0
)

# Criar imported targets
ExternalProject_Get_Property(openssl_external INSTALL_DIR)

add_library(OpenSSL::SSL IMPORTED STATIC)
set_target_properties(OpenSSL::SSL PROPERTIES
    IMPORTED_LOCATION ${INSTALL_DIR}/libssl.a
    INTERFACE_INCLUDE_DIRECTORIES ${INSTALL_DIR}/include
)

add_library(OpenSSL::Crypto IMPORTED STATIC)
set_target_properties(OpenSSL::Crypto PROPERTIES
    IMPORTED_LOCATION ${INSTALL_DIR}/libcrypto.a
    INTERFACE_INCLUDE_DIRECTORIES ${INSTALL_DIR}/include
)

add_dependencies(OpenSSL::SSL openssl_external)
add_dependencies(OpenSSL::Crypto openssl_external)
```

### 10.17.2 Cenário: Dependência com Script de Build Customizado

```cmake
# Problema: dependência que requer passos de build específicos

include(ExternalProject)

ExternalProject_Add(
    custom_lib
    GIT_REPOSITORY    https://github.com/user/custom_lib.git
    GIT_TAG           v2.1.0
    GIT_SHALLOW       TRUE

    # Passo 1: Configuração customizada
    CONFIGURE_COMMAND
        ${CMAKE_COMMAND}
            -E env CFLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2"
            <SOURCE_DIR>/configure
                --prefix=<INSTALL_DIR>
                --enable-static
                --disable-shared
                --disable-dependency-tracking

    # Passo 2: Build com flags de segurança
    BUILD_COMMAND
        ${CMAKE_COMMAND}
            -E env CFLAGS="-fstack-protector-strong"
            make -j${NPROC}

    # Passo 3: Verificação pós-build
    POST_BUILD_COMMAND
        sh -c "cd <INSTALL_DIR>/lib && \
               for lib in *.a; do \
                   echo 'Checking $lib...'; \
                   nm $lib | grep -v ' U ' | wc -l; \
               done"

    # Passo 4: Instalação
    INSTALL_COMMAND
        make install
)
```

### 10.17.3 Cenário: Múltiplas Versões da Mesma Dependência

```cmake
# Problema: projeto precisa de duas versões diferentes da mesma lib

# Versão antiga para compatibilidade
FetchContent_Declare(
    old_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.1.0  # Versão antiga
    SOURCE_SUBDIR  json    # Diretório fonte específico
)

# Versão nova para features recentes
FetchContent_Declare(
    new_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG        v3.11.3  # Versão nova
    SOURCE_SUBDIR  json
)

FetchContent_MakeAvailable(old_json new_json)

# Usar versões diferentes em targets diferentes
add_executable(legacy_tool legacy_tool.cpp)
target_link_libraries(legacy_tool PRIVATE nlohmann_json::nlohmann_json)

# Para a versão nova, criar um alias
add_library(new_json ALIAS nlohmann_json::nlohmann_json)
```

### 10.17.4 Cenário: Dependência com Submodules

```cmake
# Problema: dependência usa submodules, mas FetchContent não baixa

FetchContent_Declare(
    complex_lib
    GIT_REPOSITORY https://github.com/user/complex_lib.git
    GIT_TAG        v3.0.0
    GIT_SHALLOW    TRUE
    GIT_SUBMODULES "third_party/dep1;third_party/dep2"
    GIT_SUBMODULES_RECURSE TRUE
    GIT_PROGRESS TRUE
)

FetchContent_MakeAvailable(complex_lib)
```

### 10.17.5 Cenário: Dependência que Precisa de Generator Expressions

```cmake
FetchContent_Declare(
    my_lib
    GIT_REPOSITORY https://github.com/user/my_lib.git
    GIT_TAG        v1.0.0
)

FetchContent_MakeAvailable(my_lib)

# Usar generator expressions para configurações específicas
target_compile_definitions(my_lib PRIVATE
    $<$<CONFIG:Debug>:MY_LIB_DEBUG>
    $<$<CONFIG:Release>:MY_LIB_RELEASE>
    $<$<BOOL:${ENABLE_FEATURE_X}>:FEATURE_X_ENABLED>
)

target_compile_options(my_lib PRIVATE
    $<$<CXX_COMPILER_ID:GNU>:-Wall -Wextra>
    $<$<CXX_COMPILER_ID:Clang>:-Weverything>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)
```

---

## 10.18 Troubleshooting

### 10.18.1 Erros Comuns e Soluções

**Erro: "Could not find a package configuration file"**

```cmake
# Causa: dependência não instalou targets corretamente
# Solução: verificar INSTALA_DIR

FetchContent_GetProperties(mylib)
message(STATUS "mylib source dir: ${mylib_SOURCE_DIR}")
message(STATUS "mylib binary dir: ${mylib_BINARY_DIR}")

# Verificar se o targets file existe
file(GLOB TARGETS_FILES "${mylib_BINARY_DIR}/*Config.cmake")
message(STATUS "Config files: ${TARGETS_FILES}")
```

**Erro: "No rule to target"**

```cmake
# Causa: target não existe ou não foi criado
# Solução: verificar nomes dos targets

# Listar todos os targets disponíveis
get_property(ALL_TARGETS DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)
message(STATUS "Available targets: ${ALL_TARGETS}")
```

**Erro: "Circular dependency"**

```cmake
# Causa: dependências que dependem umas das outras
# Solução: usar Imported Targets em vez de link direto

# Em vez de:
# add_dependencies(myapp dep1 dep2)
# target_link_libraries(myapp dep1 dep2)

# Use:
add_library(dep1 IMPORTED STATIC)
set_target_properties(dep1 PROPERTIES
    IMPORTED_LOCATION /path/to/dep1.a
)
add_dependencies(dep1 dep1_external)

# Assim o CMake resolve a ordem corretamente
```

### 10.18.2 Debug de FetchContent

```cmake
# Habilitar verbose do FetchContent
set(FETCHCONTENT_QUIET OFF)

# Mostrar mensagens de progresso
set(FETCHCONTENT_UPDATES_DISCONNECTED OFF)

# Verificar variáveis após populate
FetchContent_MakeAvailable(mylib)
message(STATUS "mylib_SOURCE_DIR = ${mylib_SOURCE_DIR}")
message(STATUS "mylib_BINARY_DIR = ${mylib_BINARY_DIR}")

# Verificar se targets foram criados
if(TARGET mylib::mylib)
    message(STATUS "Target mylib::mylib found")
else()
    message(WARNING "Target mylib::mylib NOT found")
endif()
```

### 10.18.3 Problemas de Performance

```cmake
# Problema: FetchContent é lento em builds grandes
# Solução 1: Usar FETCHCONTENT_FULLY_DISCONNECTED em CI

# GitHub Actions
# -DFETCHCONTENT_FULLY_DISCONNECTED=ON

# Solução 2: Usar cache de download
set(FETCHCONTENT_BASE_DIR "${HOME}/.cache/cmake" CACHE PATH "")

# Solução 3: Usar shallow clone
FetchContent_Declare(
    large_repo
    GIT_REPOSITORY https://github.com/large/repo.git
    GIT_TAG        v1.0.0
    GIT_SHALLOW    TRUE
    GIT_PROGRESS   TRUE
)

# Solução 4: Usar DOWNLOAD_ONLY para pré-baixar
FetchContent_Declare(
    large_repo
    GIT_REPOSITORY https://github.com/large/repo.git
    GIT_TAG        v1.0.0
    DOWNLOAD_ONLY  TRUE
)
```

### 10.18.4 Problemas de Cross-Compilation

```cmake
# Problema: FetchContent baixa para plataforma errada
# Solução: usar toolchain file

# No CMakeLists.txt
if(CMAKE_CROSSCOMPILING)
    message(STATUS "Cross-compiling for: ${CMAKE_SYSTEM_NAME}")
    # Forçar download para plataforma alvo
    set(FETCHCONTENT_FULLY_DISCONNECTED OFF)
endif()

# Na linha de comando
# cmake -B build -DCMAKE_TOOLCHAIN_FILE=toolchain.cmake
```

---

## 10.19 Checklists de Segurança

### 10.19.1 Checklist para FetchContent

- [ ] Todas as dependências têm hash SHA256/SHA512 configurado
- [ ] Nenhuma dependência usa `GIT_TAG main` ou `HEAD`
- [ ] `CMAKE_TLS_VERIFY` está habilitado
- [ ] `DOWNLOAD_EXTRACT_TIMESTAMP` está configurado (CMake 3.24+)
- [ ] `FETCHCONTENT_UPDATES_DISCONNECTED` está ON em CI/CD
- [ ] Scripts de build de dependências são auditados
- [ ] Lockfile de dependências está versionado
- [ ] Atualizações de dependências passam por code review

### 10.19.2 Checklist para ExternalProject

- [ ] Hash de download é verificado (URL_HASH)
- [ ] TLS verification está habilitado
- [ ] Flags de segurança são passadas para o build externo
- [ ] Post-build steps verificam integridade
- [ ] Imported targets são criados corretamente
- [ ] Build externo é isolado (BUILD_IN_SOURCE 0)
- [ ] Estampas são limpas em builds limpos

### 10.19.3 Checklist para Supply Chain

- [ ] SBOM é gerado para o projeto
- [ ] Dependências são monitoradas para CVEs
- [ ] Atualizações são feitas deliberadamente
- [ ] Assinatura de artefatos é verificada (quando disponível)
- [ ] Build é reproduzível (mesmo hash produce mesmo binário)
- [ ] CI/CD verifica hashes antes de build
- [ ] Auditoria de dependências é feita periodicamente

---

## 10.20 Resumo

### 10.20.1 Conceitos-Chave

1. **FetchContent**: integra dependências CMake diretamente ao build
2. **ExternalProject**: cria builds isolados para dependências não-CMake
3. **Pinning**: fixa versão exata de dependências (tag ou SHA)
4. **Hash verification**: garante integridade do conteúdo baixado
5. **TLS verification**: protege contra ataques MITM
6. **DOWNLOAD_EXTRACT_TIMESTAMP**: melhora reprodutibilidade
7. **Content-locking**: fixa conteúdo exato, não apenas versão
8. **Submodules vs FetchContent**: trade-offs entre abordagens

### 10.20.2 Decisões de Design

| Situação | Recomendação |
|----------|-------------|
| Dependência CMake nativa | FetchContent |
| Dependência não-CMake | ExternalProject |
| Precisa de isolamento total | ExternalProject |
| Precisa de integração transparente | FetchContent |
| Ambiente sem rede | Submodules ou cache |
| Alta segurança necessária | Hash + TLS + lockfile |

### 10.20.23 Próximos Passos

1. **Capítulo 11**: vcpkg e Conan — gerenciadores de pacotes para C++
2. **Capítulo 12**: SBOM e Supply Chain — rastreabilidade completa
3. **Capítulo 16**: CI/CD Seguro — integração com pipelines

---

*[Voltar ao índice](INDICE.md) | [Próximo: vcpkg e Conan](11-vcpkg-conan.md)*

---

## 10.21 Referências Avançadas e Recursos

### 10.21.1 Livros e Publicações

**"CMake Best Practices"** — Dominik Berner, Kyle E. Laskowski
Publicação abrangente sobre padrões avançados de CMake, incluindo gerenciamento de dependências com FetchContent e ExternalProject.

**"Professional CMake: A Practical Guide"** — Craig Scott
Guia detalhado das melhores práticas de CMake, com capítulos dedicados a FetchContent, ExternalProject e segurança de build.

**"Large-Scale C++ Software Design"** — John Lakos
Embora focado em C++, aborda princípios de gerenciamento de dependências em projetos grandes.

### 10.21.2 Artigos Técnicos

**"Secure Supply Chain for C/C++ Projects"**
Artigo detalhando práticas de segurança para gerenciamento de dependências em projetos C/C++, incluindo uso de FetchContent com hash verification.

**"Reproducible Builds with CMake"**
Guia prático para implementar builds reproduzíveis usando CMake, abordando DOWNLOAD_EXTRACT_TIMESTAMP e content-locking.

**"Defending Against Supply Chain Attacks"**
Análise de vetores de ataque de supply chain e como Build Systems podem ser usados como defesa.

### 10.21.3 Repositórios de Referência

**CMake FetchContent Examples**
Repositório oficial com exemplos de uso de FetchContent em diferentes cenários.

**Awesome CMake**
Lista curada de módulos CMake, incluindo FetchContent, ExternalProject e ferramentas relacionadas.

**CMake Security Best Practices**
Repositório com checklists e templates para implementação de segurança em CMake.

### 10.21.4 Comunidade e Discussão

**CMake Discourse**
Fórum oficial da comunidade CMake para discussão de melhores práticas e problemas.

**CMake Reddit**
Comunidade informal para discussão de CMake e build systems.

**CMake Slack**
Canal de comunicação em tempo real para discussão de CMake.

### 10.21.5 Ferramentas Complementares

**vcpkg**
Gerenciador de pacotes para C++ com suporte a FetchContent e integração com CMake.

**Conan**
Gerenciador de pacotes multiplataforma com suporte a CMake e ExternalProject.

**CMake Presets**
Mecanismo para compartilhar configurações de build, incluindo configurações de FetchContent.

---

## 10.22 Glossário

**BUILD_IN_SOURCE**: Opção do ExternalProject que controla se o build ocorre no mesmo diretório das fontes.

**CMAKE_TLS_VERIFY**: Variável do CMake que habilita verificação de certificados TLS para downloads.

**content-hash**: Hash calculado sobre o conteúdo de um arquivo, garantindo que o conteúdo é exatamente o esperado.

**DOWNLOAD_EXTRACT_TIMESTAMP**: Opção do CMake que preserva timestamps originais de arquivos extraídos.

**DOWNLOAD_NO_EXTRACT**: Opção do FetchContent que baixa o arquivo sem extrair automaticamente.

**ExternalProject**: Módulo do CMake para gerenciar builds externos isolados.

**FetchContent**: Módulo do CMake para integrar dependências no build atual.

**GIT_SHALLOW**: Opção do FetchContent que faz clone superficial de repositórios Git.

**GIT_TAG**: Referência específica de um commit, tag ou branch no Git.

**HTTPS_PROXY**: Variável de ambiente para configurar proxy HTTPS.

**IMPORTED_TARGET**: Target definido externamente ao build atual.

**lockfile**: Arquivo que fixa versões exatas de dependências para reprodutibilidade.

**MITM (Man-in-the-Middle)**: Ataque onde um atacante intercepta comunicação entre duas partes.

**PINNING**: Prática de fixar uma dependência em uma versão ou commit específico.

**POST_BUILD_COMMAND**: Comando executado após o build de um ExternalProject.

**SLSA (Supply chain Levels for Software Artifacts)**: Framework para garantir integridade de artefatos de software.

**SOURCE_DIR**: Diretório que contém as fontes de uma dependência.

**Symlink**: Link simbólico que aponta para outro arquivo ou diretório.

**URL_HASH**: Hash verificado para arquivos baixados via URL.

**version-hash**: Hash que identifica uma versão específica (tag ou commit).

---

## 10.23 Exercícios Avançados

### Exercício 10.9: Sistema Completo de Gerenciamento de Dependências

**Objetivo**: Implementar um sistema completo de gerenciamento de dependências.

**Instruções**:
1. Crie um módulo `cmake/DependencyManager.cmake` que:
   - Suporte FetchContent e ExternalProject
   - Implemente verificação de hash obrigatória
   - Suporte lockfile para reprodutibilidade
   - Gere SBOM (Software Bill of Materials)
2. Implemente um script `cmake/update-dependencies.sh` que:
   - Baixe dependências e calcule hashes
   - Atualize o lockfile
   - Gere relatório de atualização
3. Integre com CI/CD para verificação automática
4. Documente o sistema

**Critério de aceite**:
- Módulo funcional com exemplos
- Script de atualização funcional
- Integração CI/CD
- Documentação completa

### Exercício 10.10: Análise de Vulnerabilidades em Dependências

**Objetivo**: Implementar verificação de vulnerabilidades em dependências.

**Instruções**:
1. Crie um script que:
   - Liste todas as dependências do projeto
   - Verifique CVEs conhecidos
   - Gere relatório de vulnerabilidades
2. Integre com o build para:
   - Bloquear dependências com vulnerabilidades críticas
   - Alertar sobre vulnerabilidades de alta severidade
   - Gerar SBOM para auditoria
3. Documente o processo

**Critério de aceite**:
- Script funcional
- Integração com build
- Relatórios gerados
- Documentação

### Exercício 10.11: Build Reproduzível Completo

**Objetivo**: Implementar build 100% reproduzível.

**Instruções**:
1. Configure o projeto para:
   - Usar DOWNLOAD_EXTRACT_TIMESTAMP
   - Fixar todas as versões de dependências
   - Usar hash de conteúdo
   - Configurar SOURCE_DATE_EPOCH
2. Implemente verificação de reprodutibilidade
3. Documente o processo

**Critério de aceite**:
- Configuração correta
- Verificação funcional
- Documentação

### Exercício 10.12: Análise de Performance de FetchContent

**Objetivo**: Otimizar performance de FetchContent.

**Instruções**:
1. Implemente benchmark de FetchContent com:
   - Diferentes estratégias de caching
   - FETCHCONTENT_UPDATES_DISCONNECTED
   - FETCHCONTENT_FULLY_DISCONNECTED
   - DOWNLOAD_ONLY
2. Meça e documente resultados
3. Implemente otimizações baseadas nos resultados

**Critério de aceite**:
- Benchmark implementado
- Resultados documentados
- Otimizações implementadas

### Exercício 10.13: Segurança em Cross-Compilation

**Objetivo**: Implementar FetchContent seguro em cross-compilation.

**Instruções**:
1. Configure projeto para cross-compilation com:
   - FetchContent para dependências
   - Verificação de hash para plataforma alvo
   - TLS verification
   - DOWNLOAD_EXTRACT_TIMESTAMP
2. Implemente testes de integração
3. Documente o processo

**Critério de aceite**:
- Configuração funcional
- Testes passando
- Documentação

---

## 10.24 Padrões de Código para FetchContent

### 10.24.1 Template de Projeto com FetchContent

```cmake
# cmake_template/CMakeLists.txt
cmake_minimum_required(VERSION 3.24)
project(MyProject VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Configurações de segurança
set(CMAKE_TLS_VERIFY ON)
set(DOWNLOAD_EXTRACT_TIMESTAMP TRUE)

# Habilitar warnings
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
elseif(MSVC)
    add_compile_options(/W4)
endif()

# Buscar dependências
include(FetchContent)

# Helper macro para fetch seguro
macro(SafeFetch name repo tag)
    FetchContent_Declare(
        ${name}
        GIT_REPOSITORY ${repo}
        GIT_TAG        ${tag}
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(${name})
endmacro()

# Dependências
SafeFetch(fmt "https://github.com/fmtlib/fmt.git" "10.2.1")
SafeFetch(json "https://github.com/nlohmann/json.git" "v3.11.3")

# Targets do projeto
add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE fmt::fmt nlohmann_json::nlohmann_json)

# Testes
option(BUILD_TESTING "Build tests" ON)
if(BUILD_TESTING)
    enable_testing()
    SafeFetch(googletest "https://github.com/google/googletest.git" "v1.14.0")
    
    add_executable(tests tests/test_main.cpp)
    target_link_libraries(tests PRIVATE GTest::gtest_main fmt::fmt nlohmann_json::nlohmann_json)
    add_test(NAME MyTests COMMAND tests)
endif()
```

### 10.24.2 Template de ExternalProject

```cmake
# external_template/CMakeLists.txt
cmake_minimum_required(VERSION 3.20)
project(ExternalBuild LANGUAGES C CXX)

include(ExternalProject)

# Configurações de segurança
set(CMAKE_TLS_VERIFY ON)

# Função para criar target imported
function(CreateImportedTarget name install_dir lib_path include_dir)
    add_library(${name} IMPORTED STATIC)
    set_target_properties(${name} PROPERTIES
        IMPORTED_LOCATION "${install_dir}/${lib_path}"
        INTERFACE_INCLUDE_DIRECTORIES "${install_dir}/${include_dir}"
    )
endfunction()

# Build externo
ExternalProject_Add(
    external_lib
    URL               https://example.com/lib-1.0.tar.gz
    URL_HASH          SHA256=...
    CMAKE_ARGS
        -DCMAKE_BUILD_TYPE=${CMAKE_BUILD_TYPE}
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    BUILD_COMMAND
        ${CMAKE_COMMAND} --build <BINARY_DIR> --config $<CONFIG>
    INSTALL_COMMAND
        ${CMAKE_COMMAND} --install <BINARY_DIR> --config $<CONFIG>
)

# Criar target imported
ExternalProject_Get_Property(external_lib INSTALL_DIR)
CreateImportedTarget(external_lib_target
    "${INSTALL_DIR}"
    "lib/libexternal.a"
    "include"
)
add_dependencies(external_lib_target external_lib)

# Usar no projeto
add_executable(myapp main.cpp)
target_link_libraries(myapp PRIVATE external_lib_target)
```

---

## 10.25 Métricas e Monitoramento

### 10.25.1 Métricas de Dependências

```cmake
# cmake/DependencyMetrics.cmake

# Contar dependências
function(DependencyMetrics)
    set(metrics_file "${CMAKE_BINARY_DIR}/dependency-metrics.txt")
    file(WRITE ${metrics_file} "=== Dependency Metrics ===\n")
    
    # Contar FetchContent
    list(LENGTH FETCHCONTENT_TRY_FIND_PACKAGE_MODE fetchcontent_count)
    file(APPEND ${metrics_file} "FetchContent dependencies: ${fetchcontent_count}\n")
    
    # Contar ExternalProject
    # ExternalProject não mantém lista, mas podemos rastrear
    
    # Listar targets
    get_property(all_targets DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)
    list(LENGTH all_targets target_count)
    file(APPEND ${metrics_file} "Total targets: ${target_count}\n")
    
    # Listar dependências de cada target
    foreach(target ${all_targets})
        get_property(link_libs TARGET ${target} PROPERTY LINK_LIBRARIES)
        if(link_libs)
            file(APPEND ${metrics_file} "${target} links: ${link_libs}\n")
        endif()
    endforeach()
    
    message(STATUS "Dependency metrics written to ${metrics_file}")
endfunction()
```

### 10.25.2 Relatório de Dependências

```cmake
# cmake/DependencyReport.cmake

function(GenerateDependencyReport)
    set(report_file "${CMAKE_BINARY_DIR}/dependency-report.md")
    
    file(WRITE ${report_file} "# Dependency Report\n\n")
    file(APPEND ${report_file} "Generated: ${CMAKE_CURRENT_TIMESTAMP}\n\n")
    
    # Informações do projeto
    file(APPEND ${report_file} "## Project\n")
    file(APPEND ${report_file} "- Name: ${PROJECT_NAME}\n")
    file(APPEND ${report_file} "- Version: ${PROJECT_VERSION}\n")
    file(APPEND ${report_file} "- CMake: ${CMAKE_VERSION}\n\n")
    
    # Dependências
    file(APPEND ${report_file} "## Dependencies\n\n")
    
    # Buscar todas as dependências FetchContent
    foreach(dep ${DEPENDENCIES_MANDATORY} ${DEPENDENCIES_DEV} ${DEPENDENCIES_OPTIONAL})
        FetchContent_GetProperties(${dep})
        if(${dep}_POPULATED)
            file(APPEND ${report_file} "### ${dep}\n")
            file(APPEND ${report_file} "- Source: ${${dep}_SOURCE_DIR}\n")
            file(APPEND ${report_file} "- Binary: ${${dep}_BINARY_DIR}\n\n")
        endif()
    endforeach()
    
    # Targets
    file(APPEND ${report_file} "## Targets\n\n")
    get_property(all_targets DIRECTORY PROPERTY BUILDSYSTEM_TARGETS)
    foreach(target ${all_targets})
        get_target_property(target_type ${target} TYPE)
        file(APPEND ${report_file} "- ${target} (${target_type})\n")
    endforeach()
    
    message(STATUS "Dependency report written to ${report_file}")
endfunction()
```

---

*[Voltar ao índice](INDICE.md) | [Próximo: vcpkg e Conan](11-vcpkg-conan.md)*
