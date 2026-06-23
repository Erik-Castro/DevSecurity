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

*[Capítulo anterior: 09 — Finding Packages](09-finding-packages.md)*
*[Próximo capítulo: 11 — Vcpkg Conan](11-vcpkg-conan.md)*
