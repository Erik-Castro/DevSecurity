---
layout: default
title: "Capitulo 16 — CI/CD Seguro com CMake"
---

# Capitulo 16 — CI/CD Seguro com CMake

> *"A pipeline de CI/CD nao e apenas automacao — e a barreira entre codigo vulneravel e software produzido."*

---

## Sumario

- [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
- [GitHub Actions para C++: setup-cmake](#2-github-actions-para-c-c-setup-cmake)
- [GitLab CI para C++: .gitlab-ci.yml](#3-gitlab-ci-para-c-gitlab-ciyml)
- [Security gates: SAST, DAST, dependency scan](#4-security-gates-sast-dast-dependency-scan)
- [Build matrix: multi-platform, multi-compiler](#5-build-matrix-multi-platform-multi-compiler)
- [Caching: ccache, sccache, build cache](#6-caching-ccache-sccache-build-cache)
- [Artifact management: upload/download](#7-artifact-management-uploaddownload)
- [Code signing in CI](#8-code-signing-in-ci)
- [SBOM generation in pipeline](#9-sbom-generation-in-pipeline)
- [Secret management: OIDC, vault integration](#10-secret-management-oidc-vault-integration)
- [Branch protection: required reviews, status checks](#11-branch-protection-required-reviews-status-checks)
- [Exemplo: GitHub Actions pipeline completa](#12-exemplo-github-actions-pipeline-completa)
- [Exemplo: GitLab CI pipeline completa](#13-exemplo-gitlab-ci-pipeline-completa)
- [Exercicios](#14-exercicios)
- [Referencias](#15-referencias)

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. Configurar um pipeline de GitHub Actions para projetos C++ com CMake, incluindo configuracao, build e teste.
2. Escrever um `.gitlab-ci.yml` completo para projetos C++ multiplataforma.
3. Implementar security gates (SAST, DAST, dependency scanning) em pipelines de CI/CD.
4. Configurar build matrix para testar compilacao em multiplos sistemas operacionais e compiladores.
5. Otimizar builds com ccache, sccache e caches do proprio provedor de CI.
6. Gerenciar artefatos de build com upload, download e retencao adequada.
7. Integrar code signing em pipelines para autenticar binarios produzidos.
8. Gerar SBOM (Software Bill of Materials) automaticamente em cada build.
9. Gerenciar segredos de forma segura usando OIDC e integracao com vaults.
10. Configurar branch protection rules com required reviews e status checks.
11. Montar pipelines completas e seguras em GitHub Actions e GitLab CI.

### Por que CI/CD e criticalo para seguranca

Uma pipeline de CI/CD e o ponto de confianca mais importante em qualquer projeto de software. E nela que:

- O codigo fonte e transformado em binarios distribuidos
- Dependencias sao resolvidas e integradas
- Testes de seguranca sao executados (ou ignorados)
- Artefatos sao assinados e publicados
- Segredos sao acessados e utilizados

Se a pipeline e comprometida, o software final e comprometido. Historias como o ataque SolarWinds (2020) demonstram que adversarios miram diretamente em pipelines de build para injetar codigo malicioso. O comprometimento do build server permite que o atacante injete backdoors no binario final sem que nenhum commit suspeito apareca no historico do git.

Um pipeline inseguro pode:

- Executar dependencias nao verificadas de registries publicas
- Usar credenciais estaticas que vazam para logs publicos
- Publicar artefatos sem assinatura, permitindo substituicao
- Pular etapas de verificacao por pressao de tempo
- Rodar em ambientes com permissoes excessivas

Este capitulo transforma CI/CD de "automacao de build" em uma defesa de seguranca ativa.

---

## 2. GitHub Actions para C++: setup-cmake

### 2.1 Fundamentos do GitHub Actions para C++

GitHub Actions e a plataforma de CI/CD nativa do GitHub, baseada em eventos (event-driven). Para projetos C++ com CMake, o ciclo basico envolve:

1. Trigger do workflow (push, pull request, tag)
2. Setup do ambiente (compilador, CMake, ferramentas)
3. Configuracao do CMake
4. Build do projeto
5. Execucao de testes
6. Publicacao de artefatos

O action `lukka/get-cmake` e a forma recomendada de instalar CMake em workflows do GitHub Actions:

```yaml
name: Build and Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Get CMake and Ninja
        uses: lukka/get-cmake@latest

      - name: Configure
        run: cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release

      - name: Build
        run: cmake --build build --parallel $(nproc)

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 2.2 Configuracao avancada com toolchain

Para projetos que exigem configuracao especifica, voce pode usar toolchain files:

```yaml
      - name: Configure with security hardening
        run: |
          cmake -B build \
            -G Ninja \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_TOOLCHAIN_FILE=${{ github.workspace }}/cmake/toolchains/hardened-linux.cmake \
            -DENABLE_SECURITY_FLAGS=ON \
            -DENABLE_SANITIZERS=OFF \
            -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON

      - name: Build
        run: cmake --build build --parallel $(nproc)

      - name: Run security tests
        run: |
          cd build
          ctest --output-on-failure -L security
```

### 2.3 Actions especializadas para C++

O ecossistema GitHub Actions possui varias actions especificas para C++ e CMake:

**`lukka/run-cmake`**: Executa comandos CMake com cache integrado:

```yaml
      - name: Run CMake configure
        uses: lukka/run-cmake@v11
        with:
          configurePreset: release-ninja

      - name: Run CMake build
        uses: lukka/run-cmake@v11
        with:
          buildPreset: release-ninja
```

**`actions/cache`**: Cache generico para diretorios:

```yaml
      - name: Cache CMake build
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/ccache
            build/CMakeFiles
          key: cmake-${{ runner.os }}-${{ hashFiles('CMakeLists.txt', 'cmake/**') }}
          restore-keys: |
            cmake-${{ runner.os }}-
```

**`actions/upload-artifact`**: Upload de binarios e relatorios:

```yaml
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binaries-linux-x64
          path: |
            build/bin/
            build/lib/
          retention-days: 30
          if-no-files-found: error
```

### 2.4 Permissoes minimas

Um erro comum em GitHub Actions e conceder permissoes excessivas ao workflow. A definicao de permissoes deve ser o mais restritiva possivel:

```yaml
name: Secure Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
      actions: read
```

O campo `permissions` no nivel do workflow define o token `GITHUB_TOKEN` para todas as jobs. Cada job pode sobrescrever com permissões proprias, mas nunca deve exceder as do workflow. Regra de ouro: `contents: read` por padrao, `write` apenas quando necessario.

### 2.5 Security hardening do proprio workflow

O proprio workflow do GitHub Actions precisa ser protegido. Medidas essenciais:

**Pin de actions por SHA em vez de tags**:

```yaml
      # INSEGURO - tag pode ser movida para commit malicioso
      - uses: actions/checkout@v4

      # SEGURO - commit SHA e imutavel
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

**Limitacao de pull_request_target**:

```yaml
# NUNCA faca isto em workflows com pull_request_target
name: Unsafe
on:
  pull_request_target:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      # Este passo roda o CODIGO DO PR, nao do branch main
      # Um atacante pode injetar codigo via PR
      - uses: actions/checkout@v4
      - run: ./build.sh  # EXECUTA CODIGO DO ATACANTE
```

O evento `pull_request_target` executa o workflow do branch base (main), mas tem acesso a secrets e permissões elevadas. Se o checkout usar o codigo do PR, um atacante pode injetar comandos arbitrarios. A unica forma segura de usar `pull_request_target` e explicitly checkout do branch base:

```yaml
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.sha }}
```

### 2.6 Hardening do runner

Cada job roda em um runner (VM). O hardening do runner envolve:

1. Usar self-hosted runners apenas em ambientes controlados
2. Nunca rodar workflow em forks sem verificacao
3. Limitar o tempo de execucao
4. Usar containers Docker para isolamento

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    container:
      image: gcc:13
      options: --user 1001
```

### 2.7 Reusable workflows

Para padronizar configuracao de seguranca em multiplos repositorios, crie reusable workflows:

```yaml
# .github/workflows/reusable-secure-build.yml
name: Reusable Secure Build

on:
  workflow_call:
    inputs:
      cmake-version:
        required: false
        type: string
        default: '3.30'
      build-type:
        required: true
        type: string
    secrets:
      CODE_SIGNING_KEY:
        required: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - uses: lukka/get-cmake@latest
      - name: Configure
        run: cmake -B build -DCMAKE_BUILD_TYPE=${{ inputs.build-type }}
      - name: Build
        run: cmake --build build --parallel
```

O uso de `workflow_call` permite que outros repositorios invoquem este workflow como um action. Assim, todas as politicas de seguranca ficam centralizadas em um unico lugar.

---

## 3. GitLab CI para C++: .gitlab-ci.yml

### 3.1 Fundamentos do GitLab CI

GitLab CI usa um arquivo `.gitlab-ci.yml` na raiz do repositorio. O modelo e baseado em stages, jobs e artifacts:

```yaml
stages:
  - configure
  - build
  - test
  - security
  - deploy

variables:
  CMAKE_BUILD_PARALLEL_LEVEL: "4"

configure:
  stage: configure
  image: gcc:13
  script:
    - apt-get update && apt-get install -y cmake ninja-build
    - cmake -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
  artifacts:
    paths:
      - build/CMakeCache.txt
      - build/CMakeFiles/
    expire_in: 1 hour

build:
  stage: build
  image: gcc:13
  script:
    - cmake --build build --parallel
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 7 days
  dependencies:
    - configure

test:
  stage: test
  image: gcc:13
  script:
    - cd build && ctest --output-on-failure
  artifacts:
    when: always
    paths:
      - build/Testing/
    reports:
      junit: build/test-results.xml
  dependencies:
    - build
```

### 3.2 Variaveis predefinidas do GitLab CI

O GitLab CI fornece variaveis automaticas que facilitam a configuracao:

| Variavel | Descricao | Exemplo |
|----------|-----------|---------|
| `CI_COMMIT_BRANCH` | Nome do branch atual | `main` |
| `CI_COMMIT_SHA` | Hash do commit | `abc123...` |
| `CI_PIPELINE_SOURCE` | Origem do pipeline | `push`, `web`, `schedule` |
| `CI_JOB_TOKEN` | Token de autenticacao do job | Token automatico |
| `CI_REGISTRY_IMAGE` | Endereco do registry | `registry.gitlab.com/group/project` |
| `CI_MERGE_REQUEST_IID` | Numero do MR | `42` |
| `CI_PROJECT_DIR` | Diretorio do projeto | `/builds/group/project` |
| `CI_SERVER_VERSION` | Versao do GitLab | `16.8.0` |

### 3.3 Regras e condicoes

O GitLab CI suporta regras flexiveis para controlar quando jobs executam:

```yaml
security-scan:
  stage: security
  image: securecoderssast:latest
  script:
    - run-sast --format sarif --output results.sarif
  artifacts:
    reports:
      sast: results.sarif
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
    - if: $CI_COMMIT_TAG
```

As regras `if` usam expressoes de logica. `$CI_DEFAULT_BRANCH` e o branch padrao do repositorio (geralmente `main` ou `master`).

### 3.4 Incluindo arquivos externos

GitLab CI suporta `include` para modularizar configuracao:

```yaml
include:
  - local: '.gitlab/ci/security.yml'
  - remote: 'https://example.com/ci-templates/cpp-build.yml'
  - project: 'devops/ci-templates'
    file: '/templates/cmake-build.yml'
    ref: v2.1

stages:
  - configure
  - build
  - test
  - security
  - deploy
```

### 3.5 Services e Docker

Para jobs que precisam de servicos auxiliares (banco de dados, cache, etc):

```yaml
integration-test:
  stage: test
  image: gcc:13
  services:
    - name: redis:7
      alias: cache
    - name: postgres:15
      alias: database
  variables:
    DATABASE_URL: "postgresql://database:5432/test"
    REDIS_URL: "redis://cache:6379"
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=Debug -DENABLE_INTEGRATION_TESTS=ON
    - cmake --build build
    - cd build && ctest -L integration --output-on-failure
```

### 3.6 Cache no GitLab CI

```yaml
build:
  stage: build
  script:
    - cmake --build build --parallel
  cache:
    key:
      files:
        - CMakeLists.txt
        - cmake/**/*.cmake
    paths:
      - .ccache/
      - build/CMakeFiles/
    policy: push-pull
```

A propriedade `key.files` permite cache invalidation automatica baseada em mudancas nos arquivos de configuracao. `policy: push-pull` permite ler e escrever no cache (padrao).

### 3.7 Multi-project pipelines

GitLab CI permite acionar pipelines em outros projetos:

```yaml
deploy-dependencies:
  stage: deploy
  trigger:
    project: mygroup/dependency-project
    branch: main
    strategy: depend
```

`strategy: depend` faz o pipeline atual aguardar o pipeline acionado terminar antes de prosseguir.

### 3.8 Seguranca do GitLab CI

**Protecao de variaveis sensiveis**:

```yaml
deploy:
  stage: deploy
  script:
    - deploy-to-production
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  environment:
    name: production
    url: https://example.com
```

Variaveis marcadas como `masked` no GitLab nao aparecem nos logs. Variaveis protegidas so estao disponiveis em branches protegidos.

**Escopo de artefatos**:

```yaml
test:
  stage: test
  artifacts:
    paths:
      - build/test-results/
    expire_in: 1 week
    access: developer
```

O `access: developer` limita quem pode baixar os artefatos.

---

## 4. Security gates: SAST, DAST, dependency scan

### 4.1 O conceito de security gate

Um security gate e um ponto de verificacao na pipeline que bloqueia a progressao se criterios de seguranca nao forem atendidos. A ideia e simples: nenhum codigo deve avancar para proxima etapa sem passar por todas as verificacoes de seguranca aplicaveis.

```
Codigo -> [SAST] -> [Dependency Scan] -> [Build] -> [DAST] -> [Sign] -> Deploy
            |              |                            |
            v              v                            v
         FAIL = STOP    FAIL = STOP                 FAIL = STOP
```

### 4.2 SAST (Static Application Security Testing)

SAST analisa o codigo fonte em busca de padroes vulneraveis sem executar o programa. Para C++ e CMake, as principais ferramentas sao:

**clang-tidy** como SAST:

```yaml
  sast-clang-tidy:
    stage: security
    script:
      - cmake -B build-sast -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
      - cmake --build build-sast
      - run-clang-tidy -p build-sast -checks='bugprone-*,security-*,-modernize-*'
    artifacts:
      paths:
        - clang-tidy-results.txt
```

**cppcheck** como SAST:

```yaml
  sast-cppcheck:
    stage: security
    script:
      - cppcheck --enable=all --suppress=missingIncludeSystem
        --output-file=cppcheck-results.xml --xml
        --xml-version=2 src/ include/
    artifacts:
      reports:
        sast: cppcheck-results.xml
```

**CodeQL** (GitHub):

```yaml
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: cpp

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:cpp"
```

**Semgrep** como SAST multi-linguagem:

```yaml
  sast-semgrep:
    stage: security
    image: semgrep/semgrep
    script:
      - semgrep --config auto --sarif --output semgrep.sarif src/
    artifacts:
      reports:
        dependency_scanning: semgrep.sarif
```

### 4.3 DAST (Dynamic Application Security Testing)

DAST testa o software em execucao, enviando inputs maliciosos e verificando o comportamento. Para binarios C++, DAST envolve geralmente fuzzing:

**AFL++ em pipeline**:

```yaml
  dast-aflplusplus:
    stage: security
    image: aflplusplus/aflplusplus
    script:
      - cmake -B build-fuzz -DCMAKE_BUILD_TYPE=Debug
        -DENABLE_FUZZING=ON -DFUZZING_ENGINE=aflplusplus
      - cmake --build build-fuzz
      - timeout 300 afl-fuzz -i testcases/ -o findings/
        build-fuzz/bin/fuzz_target
    artifacts:
      paths:
        - findings/
      expire_in: 7 days
    allow_failure: true
```

**OSS-Fuzz integration**:

```yaml
  dast-ossfuzz:
    stage: security
    image: gcr.io/oss-fuzz-base/base-builder
    script:
      - compile
      - run_fuzzer target_dict corpus/
    artifacts:
      paths:
        - out/
      expire_in: 30 days
```

### 4.4 Dependency scanning

Verificacao de dependencias e uma das etapas mais criticas. Vulnerabilidades em dependencias sao responsaveis por 70% dos incidentes de seguranca em software.

**Dependabot** (GitHub) via workflow:

```yaml
      - name: Run dependency review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0
```

**Trivy** para scan de dependencias:

```yaml
  dependency-scan:
    stage: security
    image: aquasec/trivy
    script:
      - trivy fs --format sarif --output trivy-fs.sarif .
      - trivy fs --severity HIGH,CRITICAL --exit-code 1 .
    artifacts:
      reports:
        dependency_scanning: trivy-fs.sarif
```

**OWASP Dependency-Check**:

```yaml
  dependency-check:
    stage: security
    image: owasp/dependency-check
    script:
      - dependency-check.sh
        --project "MyProject"
        --scan src/
        --format SARIF
        --format HTML
        --out dependency-check-report/
        --nvdApiKey $NVD_API_KEY
    artifacts:
      paths:
        - dependency-check-report/
      reports:
        dependency_scanning: dependency-check-report/dependency-check-report.sarif
```

### 4.5 Integracao com GitHub Security

GitHub fornece painel unificado para todos os resultados de seguranca:

```yaml
      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
          category: sast-results
```

### 4.6 Configuracao de fail-on

A decisao de bloquear ou apenas alertar e crucial:

```yaml
  security-gate:
    stage: security
    script:
      - trivy fs --severity CRITICAL --exit-code 1 .
    rules:
      - if: $CI_PIPELINE_SOURCE == "merge_request_event"
        when: on_success
      - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
        when: always
```

`--exit-code 1` faz o job falhar se vulnerabilidades forem encontradas. `allow_failure: true` permite que o pipeline prossiga mesmo com falha no security gate (nao recomendado para producao).

### 4.7 Formato SARIF

SARIF (Static Analysis Results Interchange Format) e o formato padrao para resultados de analise estatica. Todos os principais tools de SAST sao capazes de gerar SARIF:

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [
    {
      "tool": {
        "driver": {
          "name": "cppcheck",
          "version": "2.12.0",
          "rules": [...]
        }
      },
      "results": [...]
    }
  ]
}
```

---

## 5. Build matrix: multi-platform, multi-compiler

### 5.1 Por que build matrix importa

A compilation matrix testa o codigo em todas as combinacoes relevantes de plataforma, compilador e configuracao. Isso e essencial para:

- Detectar bugs que so aparecem em compiladores especificos
- Verificar portabilidade entre sistemas operacionais
- Testar differentes padroes de seguranca por plataforma
- Validar compatibilidade com versoes anteriores de compiladores

### 5.2 GitHub Actions build matrix

```yaml
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-22.04, ubuntu-24.04, macos-14, windows-2022]
        compiler:
          - { cc: gcc-13, cxx: g++-13 }
          - { cc: clang-17, cxx: clang++-17 }
        build-type: [Release, Debug]
        exclude:
          - os: windows-2022
            compiler: { cc: gcc-13, cxx: g++-13 }
        include:
          - os: ubuntu-24.04
            compiler: { cc: gcc-14, cxx: g++-14 }
            build-type: Release
            experimental: true

    continue-on-error: ${{ matrix.experimental || false }}

    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Install compiler (Ubuntu)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y ${{ matrix.compiler.cc }}

      - name: Install compiler (macOS)
        if: runner.os == 'macOS'
        run: brew install gcc@13

      - name: Configure
        env:
          CC: ${{ matrix.compiler.cc }}
          CXX: ${{ matrix.compiler.cxx }}
        run: cmake -B build -DCMAKE_BUILD_TYPE=${{ matrix.build-type }}

      - name: Build
        run: cmake --build build --parallel

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 5.3 GitLab CI build matrix

```yaml
.build-template:
  stage: build
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=$BUILD_TYPE
    - cmake --build build --parallel
    - ctest --test-dir build --output-on-failure

build-gcc-13:
  extends: .build-template
  image: gcc:13
  variables:
    BUILD_TYPE: Release

build-gcc-14:
  extends: .build-template
  image: gcc:14
  variables:
    BUILD_TYPE: Release

build-clang-17:
  extends: .build-template
  image: silkeh/clang:17
  variables:
    BUILD_TYPE: Release

build-windows:
  extends: .build-template
  tags:
    - windows
  variables:
    BUILD_TYPE: Release
```

### 5.4 Variaveis de ambiente por plataforma

Cada plataforma tem particularidades que afetam o build:

| Plataforma | Compilador Padrao | CMake Generator | Particularidade |
|------------|-------------------|-----------------|-----------------|
| Ubuntu | GCC | Makefiles/Ninja | apt-get para deps |
| macOS | Clang (Apple) | Xcode/Ninja | Homebrew para deps |
| Windows | MSVC | Visual Studio | vcpkg para deps |
| FreeBSD | Clang | Makefiles/Ninja | pkg para deps |

### 5.5 Cross-compilation na matrix

Para testar compilacao cruzada:

```yaml
    strategy:
      matrix:
        include:
          - target: linux-x64
            triplet: x64-linux
            cmake-toolchain: cmake/toolchains/x64-linux.cmake
          - target: linux-arm64
            triplet: arm64-linux
            cmake-toolchain: cmake/toolchains/arm64-linux.cmake
          - target: linux-armhf
            triplet: arm-linux-gnueabihf
            cmake-toolchain: cmake/toolchains/arm-linux-gnueabihf.cmake
          - target: wasm
            triplet: wasm32-emscripten
            cmake-toolchain: cmake/toolchains/wasm.cmake
```

### 5.6 Fail-fast vs tolerancia a falhas

`fail-fast: true` (padrao) cancela todos os jobs restantes quando um falha. `fail-fast: false` permite que todos os jobs terminem. Para build matrix de seguranca, `fail-fast: false` e preferivel porque:

1. Permite ver todas as falhas de uma vez
2. Nao perde informacao de diagnosticos de plataformas que funcionam
3. Cada plataforma e independente em termos de seguranca

---

## 6. Caching: ccache, sccache, build cache

### 6.1 Por que caching importa

Builds C++ sao notoriamente lentos. Um projeto medio pode levar 10-30 minutos para compilar do zero. Caching reduz isso dramaticamente para builds incrementais de 1-3 minutos. Mas caching tambem e uma questao de seguranca:

- Cache compartilhado entre branches pode ser poisoning
- Cache de artefatos de compilacao pode conter informacoes sensiveis
- Cache de dependencias pode mascarar vulnerabilidades

### 6.2 ccache

ccache e um cache de compilacao que armazena resultados de compilacao e os reutiliza quando as mesmas entradas sao fornecidas:

```yaml
      - name: Setup ccache
        run: |
          sudo apt-get install ccache
          ccache --max-size=500M
          ccache --zero-stats

      - name: Cache ccache
        uses: actions/cache@v4
        with:
          path: ~/.cache/ccache
          key: ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ github.sha }}
          restore-keys: |
            ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-
            ccache-${{ runner.os }}-

      - name: Configure
        env:
          CC: ${{ matrix.compiler.cc }}
          CXX: ${{ matrix.compiler.cxx }}
        run: |
          cmake -B build -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_C_COMPILER_LAUNCHER=ccache \
            -DCMAKE_CXX_COMPILER_LAUNCHER=ccache

      - name: Build
        run: cmake --build build --parallel

      - name: Show ccache stats
        run: ccache --show-stats
```

### 6.3 sccache

sccache e uma alternativa ao ccache desenvolvida pela Mozilla. A diferencca principal e suporte a cache remoto (S3, Azure Blob):

```yaml
      - name: Setup sccache
        uses: mozilla-actions/sccache-action@v0.0.6

      - name: Configure
        env:
          SCCACHE_GHA_ENABLED: "true"
          RUSTC_WRAPPER: "sccache"
        run: |
          cmake -B build -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_C_COMPILER_LAUNCHER=sccache \
            -DCMAKE_CXX_COMPILER_LAUNCHER=sccache
```

sccache se integra nativamente com GitHub Actions cache, eliminando a necessidade de configuracao manual de cache.

### 6.4 Build cache do CMake

CMake 3.18+ possui build cache proprio que salva e restaura estado de build:

```yaml
      - name: Cache CMake build
        uses: actions/cache@v4
        with:
          path: |
            build/CMakeCache.txt
            build/CMakeFiles/
            build/_deps/
          key: cmake-build-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ hashFiles('CMakeLists.txt', 'cmake/**') }}
          restore-keys: |
            cmake-build-${{ runner.os }}-${{ matrix.compiler.cc }}-
```

### 6.5 Cache seguro

Regras para caching seguro:

**Nunca cachear**:
- Arquivos de configuracao com credenciais
- Keys de assinatura
- Certificados privados
- Tokens de acesso

**Sempre invalidate quando**:
- `CMakeLists.txt` muda
- Arquivos em `cmake/` mudam
- Compilador ou versao muda
- `vcpkg.json` ou `conanfile.py` muda

**Chaves de cache devem ser**:
- Especificas por OS, compilador e hash dos arquivos de build
- Nunca compartilhadas entre branches publicos e privados
- Invalidadas quando vulnerabilidades sao detectadas em dependencias

```yaml
      - name: Cache key with invalidation
        uses: actions/cache@v4
        with:
          path: build/
          key: build-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ hashFiles('CMakeLists.txt', 'cmake/**', 'vcpkg.json') }}-${{ github.sha }}
          restore-keys: |
            build-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ hashFiles('CMakeLists.txt', 'cmake/**', 'vcpkg.json') }}-
            build-${{ runner.os }}-${{ matrix.compiler.cc }}-
```

### 6.6 Cache poisoning

Cache poisoning e uma tecnica onde o atacante injeta dados maliciosos no cache. Em GitHub Actions, o cache e compartilhado entre workflows do mesmo repositorio. Um workflow em um branch pode escrever no cache e outro workflow pode ler:

```yaml
# Atacante injeta cache malicioso via PR
# O cache e salvo porque o workflow tem permissao de write
# O workflow do main le o cache comprometido
```

Mitigacoes:

1. **Chaves de cache especificas**: Use `github.sha` ou hash de arquivos criticos na chave
2. **Nao confie em cache de PRs**: Use `restore-keys` apenas com prefixos controlados
3. **Segure o cache remoto**: Se usar cache remoto, autentique e autorize

---

## 7. Artifact management: upload/download

### 7.1 Artefatos em GitHub Actions

GitHub Actions fornece `actions/upload-artifact` e `actions/download-artifact`:

```yaml
      - name: Upload test results
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.os }}-${{ matrix.compiler.cc }}
          path: |
            build/Testing/
            build/test-results.xml
          retention-days: 90
          compression-level: 6
          if-no-files-found: warn
```

### 7.2 Artefatos em GitLab CI

```yaml
  build:
    stage: build
    script:
      - cmake --build build --parallel
    artifacts:
      name: "binary-${CI_COMMIT_SHORT_SHA}-${CI_JOB_ID}"
      paths:
        - build/bin/
        - build/lib/
        - build/*.so
      exclude:
        - build/CMakeFiles/
        - build/cmake_install.cmake
      expire_in: 30 days
      when: on_success
```

### 7.3 Seguranca de artefatos

Artefatos de build podem conter informacoes sensiveis:

**Nunca incluir em artefatos**:
- Arquivos de configuracao com tokens
- Chaves de debug
- Informacoes de conexao a bancos de dados
- Logs que contenham variaveis de ambiente

**Sempre incluir**:
- Binarios compilados (para release)
- SBOM
- Relatorios de seguranca
- Provas de build (hashes, logs de configuracao)

### 7.4 Retencao adequada

```yaml
      - name: Upload release artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-${{ github.ref_name }}
          path: build/release/*
          retention-days: 90

      - name: Upload security reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports-${{ github.sha }}
          path: |
            sarif-results.sarif
            trivy-results.sarif
            dependency-check-report/
          retention-days: 365
```

### 7.5 Sbom como artefato

O SBOM deve ser tratado como artefato de alto valor:

```yaml
      - name: Generate SBOM
        run: |
          syft scan dir:. -o spdx-json=sbom.spdx.json
          syft scan dir:. -o cyclonedx-json=sbom.cdx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom-${{ github.ref_name }}-${{ github.sha }}
          path: |
            sbom.spdx.json
            sbom.cdx.json
          retention-days: 2555
```

---

## 8. Code signing in CI

### 8.1 Por que code signing importa

Code signing e o processo de anexar uma assinatura digital a binarios. Isso permite que usuarios finais verifiquem:

1. O binario foi realmente construido por voce
2. O binario nao foi alterado apos a assinatura
3. A origem do binario e confiavel

Sem code signing, qualquer pessoa pode distribuir binarios em seu nome.

### 8.2 GPG signing em CI

GPG e o metodo mais comum para assinar artefatos open-source:

```yaml
      - name: Import GPG key
        uses: crazy-max/ghaction-import-gpg@v6
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}

      - name: Sign release artifacts
        run: |
          for file in build/release/*; do
            gpg --batch --yes --armor --detach-sign "$file"
          done

      - name: Verify signatures
        run: |
          for file in build/release/*.asc; do
            gpg --verify "$file" "${file%.asc}"
          done
```

### 8.3 Sigstore/cosign

Sigstore e a abordagem moderna para assinatura de artefatos. cosign e a ferramenta principal:

```yaml
      - name: Install cosign
        if: github.event_name != 'pull_request'
        uses: sigstore/cosign-installer@v3

      - name: Log in to GHCR
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push image
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Sign container image
        if: github.event_name != 'pull_request'
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          cosign sign ghcr.io/${{ github.repository }}@${DIGEST}

      - name: Verify signature
        run: |
          cosign verify ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### 8.4 SLSA provenance

SLSA (Supply-chain Levels for Software Artifacts) fornece framework para attestacao de origem de artefatos:

```yaml
      - name: Generate provenance
        if: github.event_name != 'pull_request'
        uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.1.0
        with:
          base64-subjects: "${{ steps.hash.outputs.digests }}"
          upload-assets: true
          compile-generator: true
```

### 8.5 Code signing para Windows (Authenticode)

Para binarios Windows, Authenticode e o padrao:

```yaml
  sign-windows:
    runs-on: windows-latest
    steps:
      - name: Import code signing certificate
        uses: windows-actions/import-certificate@v1
        with:
          pfx-base64: ${{ secrets.WINDOWS_CERT_PFX }}
          pfx-password: ${{ secrets.WINDOWS_CERT_PASSWORD }}

      - name: Sign executables
        run: |
          $cert = Get-ChildItem -Path Cert:\CurrentUser\My -CodeSigningCert
          Get-ChildItem build/release/*.exe | ForEach-Object {
            Set-AuthenticodeSignature -FilePath $_.FullName -Certificate $cert
          }
```

### 8.6 Code signing para macOS (Apple notarization)

```yaml
  sign-macos:
    runs-on: macos-latest
    steps:
      - name: Import signing certificate
        uses: apple-actions/import-codesign-certs@v3
        with:
          p12-file-base64: ${{ secrets.MACOS_CERT_P12 }}
          p12-password: ${{ secrets.MACOS_CERT_PASSWORD }}

      - name: Sign binary
        run: |
          codesign --force --options runtime --timestamp \
            --sign "Developer ID Application" build/release/myapp

      - name: Notarize
        run: |
          xcrun notarytool submit build/release/myapp.zip \
            --apple-id ${{ secrets.APPLE_ID }} \
            --team-id ${{ secrets.APPLE_TEAM_ID }} \
            --password ${{ secrets.APPLE_APP_PASSWORD }} \
            --wait
```

### 8.7 Verificacao pos-build

A verificacao de assinatura deve ser parte do pipeline de release:

```yaml
  verify-signatures:
    needs: [build, sign]
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: release-signed
          path: release/

      - name: Verify GPG signatures
        run: |
          for file in release/*.asc; do
            if ! gpg --verify "$file" "${file%.asc}"; then
              echo "FAIL: Signature verification failed for ${file%.asc}"
              exit 1
            fi
          done

      - name: Verify checksums
        run: |
          cd release
          sha256sum -c SHA256SUMS
```

---

## 9. SBOM generation in pipeline

### 9.1 O que e SBOM e por que importa

SBOM (Software Bill of Materials) e uma lista estruturada de todos os componentes, bibliotecas e dependencias que compoem um software. E o equivalente a uma lista de ingredientes na area de seguranca de software.

A Executive Order 14028 (EUA, 2021) exige SBOM para software vendido ao governo federal. A EU Cyber Resilience Act (2024) exige SBOM para produtos com componentes digitais.

### 9.2 Formatos de SBOM

| Formato | Organizacao | Formato | Uso Principal |
|---------|-------------|---------|---------------|
| SPDX | Linux Foundation | JSON/XML | Compliance, legal |
| CycloneDX | OWASP | JSON/XML | Vulnerability management |
| SWID | ISO | XML | Enterprise asset management |

### 9.3 Geracao de SBOM com Syft

Syft e uma ferramenta open-source da Anchore para gerar SBOM:

```yaml
      - name: Install Syft
        uses: anchore/sbom-action/download-syft@v0

      - name: Generate SPDX SBOM
        run: |
          syft scan dir:. \
            --output spdx-json=sbom.spdx.json \
            --output spdx-tag-value=sbom.spdx

      - name: Generate CycloneDX SBOM
        run: |
          syft scan dir:. \
            --output cyclonedx-json=sbom.cdx.json
```

### 9.4 Geracao de SBOM com cdxgen

cdxgen e uma ferramenta da CycloneDX para gerar SBOM especifico para C++:

```yaml
      - name: Install cdxgen
        run: npm install -g @cyclonedx/cdxgen

      - name: Generate SBOM
        run: |
          cdxgen -o sbom.cdx.json \
            --spec-version 1_5 \
            --profile moderate \
            --export-provenance
```

### 9.5 Geracao de SBOM com CLIF

CLIF (CycloneDX CLI) permite converter e validar SBOM:

```yaml
      - name: Validate SBOM
        run: |
          cdxgen -o sbom.cdx.json .
          cdx validate sbom.cdx.json
          cdx convert sbom.cdx.json -o sbom.spdx.json -t spdx
```

### 9.6 SBOM em CMake

CMake pode gerar SBOM durante o build usando `CPack`:

```cmake
# CMakeLists.txt
include(CPackComponent)

set(CPACK_GENERATOR "DEB;RPM;TGZ")
set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS ON)

set(CPACK_INCLUDE_TOPLEVEL_DIRECTORY ON)
set(CPACK_STRIP_FILES ON)

# SBOM via CPack
set(CPACK_RPM_PACKAGE_LICENSE "MIT")
set(CPACK_RPM_PACKAGE_GROUP "Development/Libraries")

include(CPack)
```

### 9.7 Assinatura de SBOM

O SBOM deve ser assinado para garantir integridade:

```yaml
      - name: Sign SBOM
        run: |
          cosign sign-blob \
            --yes \
            --output-signature sbom.cdx.json.sig \
            sbom.cdx.json

      - name: Attach SBOM to release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            sbom.spdx.json
            sbom.cdx.json
            sbom.cdx.json.sig
```

### 9.8 Vulnerability scanning do SBOM

Apos gerar o SBOM, ele pode ser escaneado contra bases de vulnerabilidade:

```yaml
      - name: Scan SBOM for vulnerabilities
        run: |
          grype sbom:sbom.cdx.json \
            --output sarif --file grype-results.sarif
          grype sbom:sbom.cdx.json \
            --fail-on critical
```

### 9.9 SBOM em releases

```yaml
  release:
    needs: [build, sign, sbom]
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - name: Create release with SBOM
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            build/release/*
            sbom.spdx.json
            sbom.cdx.json
            SBOM.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 10. Secret management: OIDC, vault integration

### 10.1 Por que secrets importam em CI/CD

CI/CD pipelines precisam acessar segredos para:
- Assinar binarios (chaves GPG, certificados)
- Publicar pacotes (tokens de registry)
- Acessar servicos (tokens de API, credenciais de banco)
- Deploy em ambientes de producao

Se um segredo vaza, o atacante pode:
- Assinar binarios maliciosos em seu nome
- Publicar versoes comprometidas
- Acessar dados sensiveis
- Comprometer ambientes de producao

### 10.2 GitHub Actions secrets

```yaml
      - name: Use secret
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
        run: |
          curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com
```

**Protecao de secrets**:
- Secrets nao aparecem em logs (automatico)
- Secrets sao disponiveis apenas em branches protegidos (configuravel)
- Secrets nao sao disponiveis em workflows de pull_request de forks

```yaml
on:
  pull_request_target:
    # NUNCA faca checkout do PR aqui
    # Apenas use secrets para workflow do branch base
```

### 10.3 OIDC (OpenID Connect)

OIDC e a forma mais segura de autenticar em CI/CD. Elimina a necessidade de secrets estaticos:

```yaml
      - name: Configure OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/ci-deploy
          aws-region: us-east-1
          oidc-role-session: deploy-session
```

OIDC funciona com:

| Provedor | Configuracao | Uso |
|----------|--------------|-----|
| AWS | `role-to-assume` | Deploy, S3, ECR |
| GCP | `workload_identity_provider` | Deploy, GCS, GCR |
| Azure | `federated-token` | Deploy, Blob, ACR |
| HashiCorp Vault | `vault-role` | Secrets, PKI |

### 10.4 HashiCorp Vault integration

Vault e um gerenciador de segredos corporativo:

```yaml
      - name: Vault login
        uses: hashicorp/vault-action@v3
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: jwt
          role: ci-role
          secrets: |
            secret/data/ci deploy_token | DEPLOY_TOKEN ;
            secret/data/ci api_key | API_KEY ;
            secret/data/ci db_password | DB_PASSWORD
        env:
          DEPLOY_TOKEN: ${{ steps.vault.outputs.deploy_token }}
```

### 10.5 Vault com AppRole

Para ambientes sem OIDC:

```yaml
      - name: Vault AppRole
        run: |
          VAULT_TOKEN=$(vault write -field=token auth/approle/login \
            role_id=${{ secrets.VAULT_ROLE_ID }} \
            secret_id=${{ secrets.VAULT_SECRET_ID }})
          echo "::add-mask::$VAULT_TOKEN"
          
          DB_PASSWORD=$(vault kv get -field=password secret/ci/db)
          echo "::add-mask::$DB_PASSWORD"
```

### 10.6 Rotation de secrets

Secrets devem ser rotacionados regularmente:

```yaml
      - name: Rotate secrets (scheduled)
        if: github.event_name == 'schedule'
        run: |
          NEW_KEY=$(openssl rand -base64 32)
          gh secret set API_TOKEN --body "$NEW_KEY"
          echo "Secret rotated. Previous value invalidated."
```

### 10.7 Secret scanning no repositorio

GitHub detecta secrets commitados acidentalmente:

```yaml
      - name: Check for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified
```

### 10.8 Encriptacao de secrets em artefatos

Nunca inclua secrets em artefatos. Se precisar de secrets em artefatos temporarios, encripte:

```yaml
      - name: Encrypt artifacts
        run: |
          gpg --batch --yes --symmetric --cipher-algo AES256 \
            -o artifacts.enc artifacts.tar
        env:
          GPG_BATCH_PASSPHRASE: ${{ secrets.ARTIFACT_PASSPHRASE }}

      - name: Decrypt artifacts
        run: |
          gpg --batch --yes --decrypt \
            -o artifacts.tar artifacts.enc
        env:
          GPG_BATCH_PASSPHRASE: ${{ secrets.ARTIFACT_PASSPHRASE }}
```

### 10.9 Environment secrets

GitHub Actions suporta secrets por ambiente (production, staging):

```yaml
  deploy-production:
    needs: build
    environment: production
    runs-on: ubuntu-latest
    steps:
      - name: Deploy
        env:
          PROD_TOKEN: ${{ secrets.PROD_DEPLOY_TOKEN }}
        run: ./deploy.sh
```

Ambientes podem ter protecao adicional como:
- Required reviewers
- Wait timer
- Deployment branches

### 10.10 Gerenciamento de segredos em GitLab CI

GitLab CI fornece variaveis protegidas e mascaradas:

```yaml
  deploy:
    stage: deploy
    script:
      - echo "Deploying with token..."
    variables:
      TOKEN: $PROTECTED_TOKEN
    rules:
      - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
        when: on_success
```

Configuracao no GitLab UI:
- **Protected**: Disponivel apenas em branches protegidos
- **Masked**: Nao aparece nos logs
- **File type**: Conteudo e tratado como arquivo

---

## 11. Branch protection: required reviews, status checks

### 11.1 Por que branch protection importa

Branch protection previne que codigo nao revisado ou nao verificado seja integrado ao branch principal. E a ultima barreira antes que codigo comprometido atinja producao.

### 11.2 GitHub branch protection rules

```yaml
# Configuracao via API (exemplo com gh CLI)
# gh api repos/{owner}/{repo}/branches/main/protection \
#   -X PUT -f 'required_status_checks={"strict":true,"contexts":["build","security-scan"]}' \
#   -f 'enforce_admins=true' \
#   -f 'required_pull_request_reviews={"required_approving_review_count":2,"dismiss_stale_reviews":true}' \
#   -f 'restrictions=null'
```

Via GitHub UI ou API, configure:

1. **Require pull request reviews**: Exige pelo menos 2 approvals
2. **Dismiss stale reviews**: Revoga approvals quando novos commits sao feitos
3. **Require status checks**: Exige que jobs especificos passem
4. **Require branches to be up to date**: Branch deve estar atualizado antes do merge
5. **Require signed commits**: Exige commits GPG assinados
6. **Require linear history**: Exige squash merge ou rebase
7. **Require conversation resolution**: Exige que threads sejam resolvidas
8. **Require code owners**: Exige aprovacao de code owners
9. **Restrict pushes**: Limita quem pode push direto

### 11.3 Status checks obrigatorios

```yaml
# Workflow que gera status check
name: Security Checks

on:
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cmake -B build && cmake --build build

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: trivy fs --exit-code 1 .

  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cppcheck --error-exitcode=1 src/
```

### 11.4 CODEOWNERS

O arquivo `CODEOWNERS` define quem deve revisar cada area do codigo:

```
# CODEOWNERS
*.cpp @team-core
*.h @team-core
CMakeLists.txt @team-build
cmake/ @team-build
.github/ @team-devops
.gitlab-ci.yml @team-devops
*security* @team-security
```

### 11.5 GitLab merge request approvals

```yaml
# Configuracao no .gitlab/approval-rules.yml
approvers:
  - name: Security Team
    approvals_required: 2
    users:
      - security-lead
      - security-engineer

approver_rules:
  - name: Critical Files
    approvals_required: 2
    applies_to:
      - CMakeLists.txt
      - cmake/**/*.cmake
      - .gitlab-ci.yml
```

### 11.6 Required reviews para areas criticas

Para arquivos de seguranca (CMakeLists.txt, toolchain files, CI configs):

```yaml
# GitHub: CODEOWNERS
CMakeLists.txt @org/security-team
cmake/toolchains/ @org/security-team
.github/workflows/ @org/devops-team
.github/workflows/*security* @org/security-team
```

### 11.7 Signed commits enforcement

```yaml
# GitHub: branch protection rule
# "Require signed commits" - todos os commits devem ser GPG/SSH/S/MIME signed

# GitLab: merge request approval
# Settings > Repository > Protected Branches > "Require signed commits"
```

### 11.8 Status check no CI

```yaml
      - name: Require all security checks passed
        if: always()
        run: |
          echo "Security gate results:"
          echo "  SAST: ${{ needs.sast.result }}"
          echo "  Dependency scan: ${{ needs.dependency-scan.result }}"
          echo "  Build: ${{ needs.build.result }}"
          echo "  Tests: ${{ needs.test.result }}"
          
          if [ "${{ needs.sast.result }}" != "success" ] || \
             [ "${{ needs.dependency-scan.result }}" != "success" ]; then
            echo "FAIL: Security checks did not pass"
            exit 1
          fi
```

---

## 12. Exemplo: GitHub Actions pipeline completa

Este e um exemplo completo de pipeline GitHub Actions para um projeto C++ com CMake, incluindo todas as praticas de seguranca discutidas:

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  release:
    types: [published]
  schedule:
    - cron: '0 6 * * 1'

permissions:
  contents: read
  security-events: write
  actions: read
  id-token: write

env:
  CMAKE_BUILD_PARALLEL_LEVEL: "4"

jobs:
  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Get CMake
        uses: lukka/get-cmake@latest

      - name: Configure for compile_commands.json
        run: |
          cmake -B build-scan \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_EXPORT_COMPILE_COMMANDS=ON

      - name: Run clang-tidy
        run: |
          run-clang-tidy -p build-scan \
            -checks='-*,bugprone-*,performance-*,security-*,-modernize-*' \
            2>&1 | tee clang-tidy-results.txt
          if grep -q "warning:" clang-tidy-results.txt; then
            echo "clang-tidy found issues"
            exit 1
          fi

      - name: Run cppcheck
        run: |
          cppcheck \
            --enable=all \
            --suppress=missingIncludeSystem \
            --error-exitcode=1 \
            --inline-suppr \
            -I include/ \
            src/

  sast:
    name: SAST Analysis
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: cpp
          queries: security-extended

      - name: Build for CodeQL
        run: |
          cmake -B build -DCMAKE_BUILD_TYPE=Debug
          cmake --build build

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:cpp"

  dependency-scan:
    name: Dependency Security
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Run Trivy filesystem scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: fs
          scan-ref: .
          format: sarif
          output: trivy-fs.sarif
          severity: HIGH,CRITICAL

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-fs.sarif
          category: dependency-scan

      - name: Fail on critical vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: fs
          scan-ref: .
          severity: CRITICAL
          exit-code: 1

  build:
    name: Build (${{ matrix.os }}, ${{ matrix.compiler.cc }})
    needs: [lint, sast, dependency-scan]
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-22.04, ubuntu-24.04, macos-14, windows-2022]
        compiler:
          - { cc: gcc-13, cxx: g++-13 }
          - { cc: clang-17, cxx: clang++-17 }
        build-type: [Release, Debug]
        include:
          - os: ubuntu-24.04
            compiler: { cc: gcc-14, cxx: g++-14 }
            build-type: Release
            experimental: true
        exclude:
          - os: macos-14
            compiler: { cc: gcc-13, cxx: g++-13 }
          - os: windows-2022
            compiler: { cc: gcc-13, cxx: g++-13 }
    continue-on-error: ${{ matrix.experimental || false }}

    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Install compiler (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y ${{ matrix.compiler.cc }} cmake ninja-build ccache

      - name: Install compiler (macOS)
        if: runner.os == 'macOS'
        run: |
          brew install gcc@14 ninja ccache

      - name: Setup ccache
        uses: actions/cache@v4
        with:
          path: ~/.cache/ccache
          key: ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ matrix.build-type }}-${{ github.sha }}
          restore-keys: |
            ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ matrix.build-type }}-
            ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-
            ccache-${{ runner.os }}-

      - name: Configure
        env:
          CC: ${{ matrix.compiler.cc }}
          CXX: ${{ matrix.compiler.cxx }}
        run: |
          cmake -B build \
            -G Ninja \
            -DCMAKE_BUILD_TYPE=${{ matrix.build-type }} \
            -DCMAKE_C_COMPILER_LAUNCHER=ccache \
            -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
            -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=${{ matrix.build-type == 'Release' && 'ON' || 'OFF' }} \
            -DENABLE_SECURITY_FLAGS=ON \
            -DENABLE_SANITIZERS=${{ matrix.build-type == 'Debug' && 'ON' || 'OFF' }}

      - name: Build
        run: cmake --build build --parallel

      - name: Test
        run: ctest --test-dir build --output-on-failure --output-junit test-results.xml

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.os }}-${{ matrix.compiler.cc }}-${{ matrix.build-type }}
          path: build/test-results.xml
          retention-days: 30

      - name: Upload build artifacts
        if: matrix.build-type == 'Release' && !matrix.experimental
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.os }}-${{ matrix.compiler.cc }}
          path: |
            build/bin/
            build/lib/
          retention-days: 30

  sbom:
    name: Generate SBOM
    needs: [build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Install Syft
        uses: anchore/sbom-action/download-syft@v0

      - name: Generate SPDX SBOM
        run: |
          syft scan dir:. \
            --output spdx-json=sbom.spdx.json \
            --source-name "myproject" \
            --source-version "${{ github.sha }}"

      - name: Generate CycloneDX SBOM
        run: |
          syft scan dir:. \
            --output cyclonedx-json=sbom.cdx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom-${{ github.sha }}
          path: |
            sbom.spdx.json
            sbom.cdx.json
          retention-days: 2555

  sign:
    name: Sign Artifacts
    needs: [build, sbom]
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    steps:
      - name: Install cosign
        uses: sigstore/cosign-installer@v3

      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Sign artifacts
        run: |
          for artifact in artifacts/*/; do
            find "$artifact" -type f ! -name "*.sig" | while read file; do
              cosign sign-blob --yes --output-signature "${file}.sig" "$file"
            done
          done

      - name: Verify signatures
        run: |
          for sigfile in $(find artifacts/ -name "*.sig"); do
            original="${sigfile%.sig}"
            if ! cosign verify-blob --signature "$sigfile" "$original"; then
              echo "FAIL: Signature verification failed for $original"
              exit 1
            fi
          done

      - name: Upload signed artifacts
        uses: actions/upload-artifact@v4
        with:
          name: signed-artifacts
          path: artifacts/

  release:
    name: Publish Release
    needs: [build, sbom, sign]
    if: github.event_name == 'release'
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: release/

      - name: Generate checksums
        run: |
          cd release
          find . -type f ! -name "*.sig" ! -name "SHA256SUMS" -exec sha256sum {} \; > SHA256SUMS

      - name: Sign checksums
        uses: crazy-max/ghaction-import-gpg@v6
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}

      - name: Sign SHA256SUMS
        run: |
          gpg --armor --detach-sign release/SHA256SUMS

      - name: Upload release assets
        uses: softprops/action-gh-release@v2
        with:
          files: |
            release/**/*
          generate_release_notes: true
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 13. Exemplo: GitLab CI pipeline completa

Este e um exemplo completo de pipeline GitLab CI para o mesmo projeto:

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - security
  - build
  - test
  - package
  - sign
  - deploy

variables:
  CMAKE_BUILD_PARALLEL_LEVEL: "4"
  GIT_DEPTH: 100

# ============================================================
# TEMPLATES
# ============================================================

.cmake-base:
  before_script:
    - apt-get update && apt-get install -y cmake ninja-build ccache
    - ccache --max-size=500M

.build-template:
  extends: .cmake-base
  script:
    - cmake -B build -G Ninja
      -DCMAKE_BUILD_TYPE=${BUILD_TYPE}
      -DCMAKE_C_COMPILER_LAUNCHER=ccache
      -DCMAKE_CXX_COMPILER_LAUNCHER=ccache
    - cmake --build build --parallel
  cache:
    key:
      files:
        - CMakeLists.txt
        - cmake/**/*.cmake
    paths:
      - .ccache/
    policy: push-pull

# ============================================================
# LINT STAGE
# ============================================================

clang-tidy:
  stage: lint
  image: silkeh/clang:17
  extends: .cmake-base
  script:
    - apt-get install -y clang-tools-17
    - cmake -B build-scan -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    - run-clang-tidy-17 -p build-scan
      '-checks=-*,bugprone-*,performance-*,security-*'
  allow_failure: true

cppcheck:
  stage: lint
  image: ubuntu:24.04
  extends: .cmake-base
  script:
    - apt-get install -y cppcheck
    - cppcheck --enable=all
      --suppress=missingIncludeSystem
      --error-exitcode=1
      --inline-suppr
      -I include/
      src/
  allow_failure: true

# ============================================================
# SECURITY STAGE
# ============================================================

sast-clang:
  stage: security
  image: silkeh/clang:17
  extends: .cmake-base
  script:
    - apt-get install -y clang-tools-17
    - cmake -B build-sast -DCMAKE_BUILD_TYPE=Debug -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
    - cmake --build build-sast
    - clang-tidy-17 -p build-sast
      '-checks=-*,clang-analyzer-*,cppcoreguidelines-*,bugprone-*,security-*'
      2>&1 | tee sast-results.txt
  artifacts:
    paths:
      - sast-results.txt
    when: always

dependency-scan:
  stage: security
  image: aquasec/trivy:latest
  script:
    - trivy fs --format sarif --output trivy-fs.sarif .
    - trivy fs --severity HIGH,CRITICAL --exit-code 1 .
  artifacts:
    reports:
      dependency_scanning: trivy-fs.sarif
    when: always
    paths:
      - trivy-fs.sarif

secret-scan:
  stage: security
  image: trufflesecurity/trufflehog:latest
  script:
    - trufflehog git file://. --only-verified --json > secret-scan.json
  artifacts:
    when: always
    paths:
      - secret-scan.json

# ============================================================
# BUILD STAGE
# ============================================================

build-gcc-13-release:
  extends: .build-template
  stage: build
  image: gcc:13
  variables:
    BUILD_TYPE: Release
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 30 days

build-gcc-13-debug:
  extends: .build-template
  stage: build
  image: gcc:13
  variables:
    BUILD_TYPE: Debug
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 7 days

build-gcc-14-release:
  extends: .build-template
  stage: build
  image: gcc:14
  variables:
    BUILD_TYPE: Release
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 30 days

build-clang-17-release:
  extends: .build-template
  stage: build
  image: silkeh/clang:17
  variables:
    BUILD_TYPE: Release
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 30 days

build-clang-17-debug:
  extends: .build-template
  stage: build
  image: silkeh/clang:17
  variables:
    BUILD_TYPE: Debug
  artifacts:
    paths:
      - build/bin/
      - build/lib/
    expire_in: 7 days

# ============================================================
# TEST STAGE
# ============================================================

test-unit:
  stage: test
  image: gcc:13
  extends: .cmake-base
  needs:
    - build-gcc-13-release
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=Release
    - cmake --build build --parallel
    - cd build && ctest --output-on-failure --output-junit test-results.xml
  artifacts:
    when: always
    reports:
      junit: build/test-results.xml
    paths:
      - build/test-results.xml

test-security:
  stage: test
  image: gcc:13
  extends: .cmake-base
  needs:
    - build-gcc-13-debug
  script:
    - cmake -B build-debug
      -DCMAKE_BUILD_TYPE=Debug
      -DENABLE_SANITIZERS=ON
    - cmake --build build-debug --parallel
    - cd build-debug && ctest -L security --output-on-failure
  allow_failure: true

test-integration:
  stage: test
  image: gcc:13
  extends: .cmake-base
  services:
    - name: redis:7
      alias: cache
  needs:
    - build-gcc-13-release
  script:
    - cmake -B build
      -DCMAKE_BUILD_TYPE=Release
      -DENABLE_INTEGRATION_TESTS=ON
    - cmake --build build --parallel
    - cd build && ctest -L integration --output-on-failure
  allow_failure: true

# ============================================================
# PACKAGE STAGE
# ============================================================

generate-sbom:
  stage: package
  image: anchore/syft:latest
  needs:
    - build-gcc-13-release
  script:
    - syft scan dir:. -o spdx-json=sbom.spdx.json
    - syft scan dir:. -o cyclonedx-json=sbom.cdx.json
  artifacts:
    paths:
      - sbom.spdx.json
      - sbom.cdx.json
    expire_in: 7 years

generate-checksums:
  stage: package
  needs:
    - build-gcc-13-release
    - build-clang-17-release
  script:
    - mkdir -p checksums
    - find build*/bin build*/lib -type f -exec sha256sum {} \; > checksums/SHA256SUMS
  artifacts:
    paths:
      - checksums/SHA256SUMS

# ============================================================
# SIGN STAGE
# ============================================================

sign-artifacts:
  stage: sign
  image: alpine:3.20
  needs:
    - generate-sbom
    - generate-checksums
  before_script:
    - apk add --no-cache gnupg cosign
  script:
    - echo "$GPG_PRIVATE_KEY" | gpg --batch --import
    - for file in sbom.spdx.json sbom.cdx.json checksums/SHA256SUMS; do
        gpg --batch --yes --armor --detach-sign "$file";
      done
    - cosign sign-blob --yes --output-signature sbom.cdx.json.sig sbom.cdx.json
  artifacts:
    paths:
      - sbom.spdx.json
      - sbom.spdx.json.asc
      - sbom.cdx.json
      - sbom.cdx.json.asc
      - sbom.cdx.json.sig
      - checksums/
    expire_in: 7 years
  rules:
    - if: $CI_COMMIT_TAG
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# ============================================================
# DEPLOY STAGE
# ============================================================

deploy-staging:
  stage: deploy
  image: alpine:3.20
  needs:
    - sign-artifacts
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl -X POST "$STAGING_DEPLOY_URL" \
        -H "Authorization: Bearer $STAGING_TOKEN" \
        -F "binary=@build-gcc-13-release/bin/myapp" \
        -F "sbom=@sbom.spdx.json" \
        -F "checksum=@checksums/SHA256SUMS"
  environment:
    name: staging
    url: https://staging.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy-production:
  stage: deploy
  image: alpine:3.20
  needs:
    - sign-artifacts
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl -X POST "$PRODUCTION_DEPLOY_URL" \
        -H "Authorization: Bearer $PRODUCTION_TOKEN" \
        -F "binary=@build-gcc-13-release/bin/myapp" \
        -F "sbom=@sbom.spdx.json" \
        -F "checksum=@checksums/SHA256SUMS"
  environment:
    name: production
    url: https://example.com
  rules:
    - if: $CI_COMMIT_TAG
      when: manual
  allow_failure: false
```

---

## 14. Exercicios

### Exercicio 1: Pipeline basica

Crie um GitHub Actions workflow que:
- Execute em Ubuntu e macOS
- Use GCC e Clang
- Configure, build e teste um projeto CMake basico
- Cache os resultados de compilacao

### Exercicio 2: Security gate

Adicione ao exercicio anterior:
- Um job de SAST usando cppcheck
- Um job de dependency scan usando Trivy
- Um job que verifique se nenhum secret foi commitado
- Todos os jobs de seguranca devem rodar ANTES do build

### Exercicio 3: Build matrix completa

Crie uma build matrix que teste:
- 3 sistemas operacionais (Ubuntu, macOS, Windows)
- 2 compiladores por OS
- 2 build types (Release, Debug)
- Total esperado: 12 combinacoes
- Inclua pelo menos 1 combinacao experimental com `continue-on-error`

### Exercicio 4: SBOM e signing

Estenda a pipeline para:
- Gerar SBOM em formato SPDX e CycloneDX
- Assinar o SBOM com cosign
- Gerar checksums SHA256 de todos os artefatos
- Upload de todos os artefatos com retencao de 7 anos

### Exercicio 5: GitLab CI migration

Migre a pipeline do Exercicio 1 para GitLab CI:
- Use templates YAML para reutilizacao
- Implemente stages: lint, security, build, test, deploy
- Configure cache com invalidation baseada em CMakeLists.txt
- Adicione regras para executar security scan apenas em MRs e no branch principal

### Exercicio 6: OIDC deployment

Configure deploy usando OIDC:
- Para AWS (role-to-assume)
- Elimine secrets estaticos
- Adicione environment protection com required reviewers
- Configure wait timer de 5 minutos para producao

### Exercicio 7: Branch protection

Configure branch protection rules:
- Exija 2 approvals
- Exija status checks (build, sast, dependency-scan)
- Exija signed commits
- Configure CODEOWNERS para arquivos criticos
- Documente o fluxo de merge resultante

---

## 15. Referencias

### Documentacao oficial

1. GitHub Actions Documentation. https://docs.github.com/en/actions
2. GitLab CI/CD Documentation. https://docs.gitlab.com/ee/ci/
3. CMake Documentation. https://cmake.org/cmake/help/latest/
4. OSSF Scorecard. https://github.com/ossf/scorecard
5. SLSA Framework. https://slsa.dev/

### Ferramentas

6. ccache - Compiler Cache. https://ccache.dev/
7. sccache - Shared Compilation Cache. https://github.com/mozilla/sccache
8. Trivy - Security Scanner. https://trivy.dev/
9. Syft - SBOM Generator. https://github.com/anchore/syft
10. cosign - Container Signing. https://github.com/sigstore/cosign
11. CodeQL - Semantic Analysis. https://codeql.github.com/
12. Semgrep - Static Analysis. https://semgrep.dev/
13. OWASP Dependency-Check. https://owasp.org/www-project-dependency-check/
14. TruffleHog - Secret Scanner. https://trufflesecurity.com/trufflehog

### Artigos e papers

15. SLSA: Supply-chain Levels for Software Artifacts. https://slsa.dev/spec/v1.0/
16. NTIA SBOM Minimum Elements. https://www.ntia.doc.gov/files/ntia/publications/sbom_minimum_elements_report_20211012.pdf
17. EU Cyber Resilience Act. https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act
18. NIST SP 800-218 - SSDF. https://csrc.nist.gov/publications/detail/sp/800-218/final
19. Executive Order 14028 - Improving the Nation's Cybersecurity. https://www.whitehouse.gov/briefing-room/presidential-actions/2021/05/12/executive-order-on-improving-the-nations-cybersecurity/

### Seguranca de CI/CD

20. OWASP Top 10 CI/CD Security Risks. https://owasp.org/www-project-top-10-ci-cd-security-risks/
21. GitHub Actions Security Hardening. https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
22. GitLab CI/CD Security. https://docs.gitlab.com/ee/ci/yaml/#keywords
23. SolarWinds Attack Analysis. https://www.crowdstrike.com/blog/sunspot-malware-technical-analysis/
24. Codecov Breach Analysis. https://about.codecov.io/security-update/

### CVEs relevantes

25. CVE-2020-1472 - Zerologon. Comprometimento de Active Directory via autenticacao de build servers.
26. CVE-2021-44228 - Log4Shell. Exploracao de dependencias via logging em pipelines.
27. CVE-2024-3094 - XZ Utils backdoor. Backdoor injetada via comprometimento de maintainer.
28. CVE-2023-44487 - HTTP/2 Rapid Reset. DoS via dependencias de rede em build servers.

---

*"A pipeline de CI/CD segura nao e um luxo — e a base de qualquer projeto que leva seguranca a serio."*

---

**Fim do Capitulo 16**

---

## Apendice A: Padrões de Pipeline para Diferentes Tamanhos de Projeto

### A.1 Projeto individual (1 pessoa)

Para projetos pessoais ou prototipos, a pipeline deve ser minima mas segura:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: lukka/get-cmake@latest
      - run: cmake -B build -DCMAKE_BUILD_TYPE=Release
      - run: cmake --build build --parallel
      - run: ctest --test-dir build --output-on-failure
```

Neste nivel, voce prescinde de:
- Build matrix (testar em 1 OS e 1 compilador e suficiente)
- Security gates complexos (use apenas Dependabot alerts)
- Code signing (nao e critico para uso pessoal)
- SBOM (nao obrigatorio para projetos nao distribuidos)

### A.2 Projeto pequeno (2-5 pessoas)

Para equipes pequenas, adicione:
- Build matrix com 2-3 combinacoes
- SAST basico (cppcheck ou clang-tidy)
- Dependabot para dependencias
- Branch protection com 1 approval

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          sudo apt-get update && sudo apt-get install -y cppcheck
          cppcheck --enable=all --error-exitcode=1 src/ include/

  build:
    needs: lint
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-22.04, macos-14]
    steps:
      - uses: actions/checkout@v4
      - uses: lukka/get-cmake@latest
      - run: cmake -B build && cmake --build build --parallel
      - run: ctest --test-dir build --output-on-failure
```

### A.3 Projeto mediano (5-20 pessoas)

Para equipes medias, adicione:
- Build matrix completa (3+ OS, 2+ compiladores)
- SAST com CodeQL
- Dependency scanning com Trivy
- SBOM generation
- Branch protection com 2 approvals
- CODEOWNERS

### A.4 Projeto grande (20+ pessoas)

Para projetos enterprise, adicione todas as praticas deste capitulo:
- OIDC para deploy
- Vault para secrets
- SBOM assinado com cosign
- SLSA provenance
- Code signing para todas as plataformas
- Self-hosted runners com hardening
- Reusable workflows para padronizacao
- Multi-repository pipelines

---

## Apendice B: Troubleshooting Comum

### B.1 CMake nao encontrado na pipeline

**Sintoma**: `cmake: command not found`

**Causa**: O runner nao possui CMake instalado.

**Solucao**:
```yaml
      - name: Install CMake
        uses: lukka/get-cmake@latest
        # ou
        run: sudo apt-get update && sudo apt-get install -y cmake
```

### B.2 Build falha com erro de permissao

**Sintoma**: `Permission denied` ao executar binarios ou acessar diretorios.

**Causa**: O runner roda como usuario nao-privilegiado, ou permissoes de arquivo estao incorretas.

**Solucao**:
```yaml
      - name: Fix permissions
        run: chmod +x build/bin/*
        # ou
        run: sudo chown -R $USER:$USER build/
```

### B.3 Cache nao e restaurado

**Sintoma**: Build sempre compila do zero apesar de cache configurado.

**Causas possiveis**:
1. Chave de cache muito especifica (muda a cada commit)
2. Arquivos de cache estao em localizacao incorreta
3. Cache expirou (retencao do provedor)

**Solucao**:
```yaml
      - name: Cache with proper keys
        uses: actions/cache@v4
        with:
          path: ~/.cache/ccache
          key: ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-${{ hashFiles('CMakeLists.txt') }}
          restore-keys: |
            ccache-${{ runner.os }}-${{ matrix.compiler.cc }}-
```

### B.4 Secrets nao disponiveis em pull requests

**Sintoma**: Workflow falha em pull requests com `Error: secret not found`.

**Causa**: GitHub Actions nao disponibiliza secrets para workflows acionados por `pull_request` de forks.

**Solucao**: Use `pull_request_target` com checkout do branch base, ou use OIDC:
```yaml
on:
  pull_request_target:
    branches: [main]

jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.sha }}
```

### B.5 Status check nao aparece no PR

**Sintoma**: Workflow roda mas o status check nao aparece como obrigatorio no PR.

**Causa**: O nome do job no workflow nao corresponde ao nome configurado nas branch protection rules.

**Solucao**: Verifique o nome exato do job em Settings > Branches > Branch protection rules > Required status checks.

### B.6 SBOM incompleto ou vazio

**Sintoma**: SBOM gerado nao lista todas as dependencias.

**Causa**: Syft ou cdxgen nao conseguem detectar todas as dependencias de C++ (especialmente header-only libraries).

**Solucao**:
1. Use `--catalogers` para habilitar catalogadores especificos
2. Forneça `--source` para Syft indicar onde buscar
3. Complemente com analise manual de CMakeLists.txt

### B.7 Timeout em pipelines longas

**Sintoma**: Job excede o timeout padrao de 6 horas (GitHub) ou 1 hora (GitLab).

**Causa**: Build C++ complexo ou testes lentos.

**Solucao**:
```yaml
jobs:
  build:
    timeout-minutes: 30
    steps:
      - name: Build with timeout
        run: |
          timeout 1200 cmake --build build --parallel || {
            echo "Build timed out after 20 minutes"
            exit 1
          }
```

### B.8 Runner com espaco insuficiente

**Sintoma**: `No space left on device` durante build.

**Causa**: GitHub Actions runners tem 14GB de disco. Build grandes podem exceder isso.

**Solucao**:
```yaml
      - name: Free disk space
        run: |
          sudo rm -rf /usr/share/dotnet
          sudo rm -rf /opt/ghc
          sudo rm -rf /usr/local/lib/android
          docker image prune -af
```

---

## Apendice C: Metricas de Pipeline

### C.1 Metricas importantes

| Metrica | Meta | Descricao |
|---------|------|-----------|
| Build time | < 10 min | Tempo total de compilacao |
| Test time | < 5 min | Tempo total de testes |
| Security scan time | < 10 min | Tempo total de analises de seguranca |
| Pipeline time | < 30 min | Tempo total do pipeline |
| Success rate | > 95% | Percentual de pipelines bem-sucedidas |
| MTTR | < 30 min | Tempo medio para recuperar de falha |

### C.2 Coleta de metricas

```yaml
      - name: Collect pipeline metrics
        if: always()
        run: |
          echo "Pipeline Duration: ${{ github.event.workflow_run.duration_ms }}ms"
          echo "Job Duration: ${{ steps.timer.outputs.duration }}s"
          echo "Build Size: $(du -sh build/ | cut -f1)"
          echo "Binary Size: $(find build/bin -type f -exec du -sh {} \; | sort -rh | head -5)"
```

### C.3 Alertas

Configure alertas para metricas criticas:
- Build time aumentou > 50%
- Taxa de falha > 5%
- Security scan encontrou vulnerabilidades CRITICAL
- SBOM nao foi gerado

---

## Apendice D: Padrao de Nomenclatura para Workflows

### D.1 Convencoes de nome

| Workflow | Trigger | Descricao |
|----------|---------|-----------|
| `ci.yml` | push, pull_request | Build e teste basico |
| `security.yml` | push, pull_request | Analises de seguranca |
| `release.yml` | release, tag | Build, sign, publish |
| `scheduled.yml` | schedule | Scan periodico de dependencias |
| `deploy.yml` | workflow_dispatch | Deploy manual |

### D.2 Naming de jobs

```yaml
jobs:
  lint-cpp:
    # Lint especifico para C++
  
  lint-cmake:
    # Lint especifico para CMakeLists.txt
  
  build-linux:
    # Build especifico para Linux
  
  build-macos:
    # Build especifico para macOS
  
  build-windows:
    # Build especifico para Windows
  
  test-unit:
    # Testes unitarios
  
  test-integration:
    # Testes de integracao
  
  security-sast:
    # Static Application Security Testing
  
  security-dependency:
    # Dependency scanning
  
  security-secret:
    # Secret scanning
```

---

## Apendice E: Checklists de Seguranca

### E.1 Checklist antes de adicionar CI/CD

- [ ] Repositorio tem branch protection configurado
- [ ] CODEOWNERS definido para areas criticas
- [ ] Secrets nao estao commitados no historico do git
- [ ] Dependabot ou Renovate configurado para dependencias
- [ ] Pelo menos 1 pessoa da equipe entende o pipeline
- [ ] Documentacao do processo de build existe
- [ ] Procedimento de rollback documentado

### E.1 Checklist do pipeline

- [ ] Actions pinadas por SHA, nao por tag
- [ ] Permissois minimas definidas
- [ ] Secrets mascarados em logs
- [ ] Cache invalidado corretamente
- [ ] Artefatos com retencao adequada
- [ ] Security gates bloqueiam merge em falhas
- [ ] SBOM gerado em cada release
- [ ] Code signing configurado para releases
- [ ] Branch protection exige 2+ approvals
- [ ] Status checks obrigatórios definidos

### E.3 Checklist de deploy

- [ ] Deploy requer approval manual para producao
- [ ] OIDC ou vault para credenciais de deploy
- [ ] Rollback documentado e testado
- [ ] Monitoring apos deploy configurado
- [ ] Alertas para falhas de deploy
- [ ] Logs de deploy preservados
- [ ] Artefatos de deploy assinados

---

**Fim do Capitulo 16 — CI/CD Seguro com CMake**
