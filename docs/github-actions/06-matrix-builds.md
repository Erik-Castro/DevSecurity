---
layout: default
title: "06-matrix-builds"
---

# Capitulo 6 — Matrix Builds e Multi-Plataforma

> *"Teste em todas as plataformas antes de entregar em qualquer uma."*

---

## Sumario

| Secao | Descricao |
|-------|-----------|
| 6.1 | Matrix Strategy |
| 6.2 | Multi-OS |
| 6.3 | Multi-compiler |
| 6.4 | Multi-version |
| 6.5 | Fail-fast |
| 6.6 | Matrix Outputs |
| 6.7 | Cross-compilation |
| 6.8 | Performance Optimization |
| 6.9 | Conditional Matrix |
| 6.10 | Cost Optimization |

---

## Objetivos de Aprendizado

1. Configurar matrix strategies completas e flexiveis
2. Testar em multiplos sistemas operacionais (Linux, macOS, Windows)
3. Testar com multiplos compiladores (gcc, clang, msvc)
4. Testar com multiplos versoes de linguagens
5. Usar fail-fast para cancelar jobs rapido em caso de falha
6. Gerenciar outputs de matrix builds
7. Implementar cross-compilation para multiplas arquiteturas
8. Otimizar performance de matrix builds
9. Criar conditional matrices baseadas em contexto
10. Otimizar custos de matrix builds

---

## 6.1 Matrix Strategy

Matrix strategy e o mecanismo do GitHub Actions para executar o mesmo job em multiplos ambientes simultaneamente. Cada combinacao de valores da matrix cria um job separado.

### 6.1.1 Matrix Strategy Basico

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

**Resultado**: 9 jobs (3 OS x 3 versoes)

### 6.1.2 Matrix com Multiplos Parametros

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
    build-type: [Debug, Release]
```

**Resultado**: 18 jobs (3 OS x 3 versoes x 2 build types)

### 6.1.3 Matrix com Include

Include permite adicionar combinacoes especificas a matrix.

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
    include:
      - os: ubuntu-latest
        node-version: 22
        experimental: true
      - os: macos-latest
        node-version: 22
        experimental: false
```

### 6.1.4 Matrix com Exclude

Exclude permite remover combinacoes especificas da matrix.

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
    exclude:
      - os: macos-latest
        node-version: 18
      - os: windows-latest
        node-version: 18
      - os: windows-latest
        node-version: 20
```

### 6.1.5 Matrix com Include e Exclude

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
    build-type: [Debug, Release]
    include:
      - os: ubuntu-latest
        node-version: 22
        build-type: Coverage
    exclude:
      - os: macos-latest
        node-version: 18
        build-type: Debug
      - os: windows-latest
        node-version: 18
        build-type: Debug
      - os: windows-latest
        node-version: 18
        build-type: Release
```

### 6.1.6 Tabela de Matrix Combinacoes

| OS | Node Version | Build Type | Incluido | Observacao |
|----|--------------|------------|----------|------------|
| ubuntu-latest | 18 | Debug | Sim | Basico |
| ubuntu-latest | 18 | Release | Sim | Basico |
| ubuntu-latest | 20 | Debug | Sim | Basico |
| ubuntu-latest | 20 | Release | Sim | Basico |
| ubuntu-latest | 22 | Debug | Sim | Basico |
| ubuntu-latest | 22 | Release | Sim | Basico |
| ubuntu-latest | 22 | Coverage | Sim | Incluido manualmente |
| macos-latest | 18 | Debug | Nao | Excluido |
| macos-latest | 18 | Release | Sim | Basico |
| macos-latest | 20 | Debug | Sim | Basico |
| macos-latest | 20 | Release | Sim | Basico |
| macos-latest | 22 | Debug | Sim | Basico |
| macos-latest | 22 | Release | Sim | Basico |
| windows-latest | 18 | Debug | Nao | Excluido |
| windows-latest | 18 | Release | Nao | Excluido |
| windows-latest | 20 | Debug | Sim | Basico |
| windows-latest | 20 | Release | Sim | Basico |
| windows-latest | 22 | Debug | Sim | Basico |
| windows-latest | 22 | Release | Sim | Basico |

---

## 6.2 Multi-OS

Testar em multiplos sistemas operacionais e essencial para garantir compatibilidade cross-platform.

### 6.2.1 Tabela de Runners

| Runner | Sistema | Pacotes | Observacao |
|--------|---------|---------|------------|
| ubuntu-latest | Ubuntu 22.04 LTS | apt | Mais rapido e barato |
| macos-13 | macOS 13 Ventura | brew | x86_64 |
| macos-14 | macOS 14 Sonoma | brew | ARM64 (Apple Silicon) |
| macos-latest | macOS 14 Sonoma | brew | ARM64 (padrao) |
| windows-latest | Windows Server 2022 | choco | Mais lento |

### 6.2.2 Steps por OS

```yaml
steps:
  - name: Install dependencies (Linux)
    if: runner.os == 'Linux'
    run: sudo apt-get update && sudo apt-get install -y libssl-dev

  - name: Install dependencies (macOS)
    if: runner.os == 'macOS'
    run: brew install openssl

  - name: Install dependencies (Windows)
    if: runner.os == 'Windows'
    run: choco install openssl
```

### 6.2.3 Multi-OS com Matrix

```yaml
name: Multi-OS CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Upload results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.os }}
          path: test-results/
          retention-days: 7
```

### 6.2.4 Multi-OS com Scripts por OS

```yaml
jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Build (Linux)
        if: runner.os == 'Linux'
        run: |
          make build
          make test

      - name: Build (macOS)
        if: runner.os == 'macOS'
        run: |
          brew install make
          gmake build
          gmake test

      - name: Build (Windows)
        if: runner.os == 'Windows'
        run: |
          choco install make
          make build
          make test
```

---

## 6.3 Multi-Compiler

Testar com multiplos compiladores e essencial para garantir portabilidade em projetos C e C++.

### 6.3.1 Multi-Compiler Basico

```yaml
strategy:
  matrix:
    compiler: [gcc, clang, msvc]
    include:
      - compiler: gcc
        cc: gcc-12
        cxx: g++-12
      - compiler: clang
        cc: clang-16
        cxx: clang++-16
      - compiler: msvc
        cc: cl.exe
        cxx: cl.exe

steps:
  - name: Configure
    env:
      CC: ${{ matrix.cc }}
      CXX: ${{ matrix.cxx }}
    run: cmake -B build -DCMAKE_BUILD_TYPE=Release
```

### 6.3.2 Multi-Compiler com Versoes

```yaml
strategy:
  matrix:
    compiler:
      - { name: gcc-11, cc: gcc-11, cxx: g++-11, os: ubuntu-latest }
      - { name: gcc-12, cc: gcc-12, cxx: g++-12, os: ubuntu-latest }
      - { name: gcc-13, cc: gcc-13, cxx: g++-13, os: ubuntu-latest }
      - { name: clang-14, cc: clang-14, cxx: clang++-14, os: ubuntu-latest }
      - { name: clang-15, cc: clang-15, cxx: clang++-15, os: ubuntu-latest }
      - { name: clang-16, cc: clang-16, cxx: clang++-16, os: ubuntu-latest }
      - { name: msvc, cc: cl.exe, cxx: cl.exe, os: windows-latest }

runs-on: ${{ matrix.compiler.os }}

steps:
  - uses: actions/checkout@v4

  - name: Install compiler (Linux)
    if: runner.os == 'Linux'
    run: |
      sudo apt-get update
      sudo apt-get install -y ${{ matrix.compiler.cc }}

  - name: Configure
    env:
      CC: ${{ matrix.compiler.cc }}
      CXX: ${{ matrix.compiler.cxx }}
    run: cmake -B build -DCMAKE_BUILD_TYPE=Release

  - name: Build
    run: cmake --build build --parallel $(nproc 2>/dev/null || echo 4)

  - name: Test
    run: ctest --test-dir build --output-on-failure
```

### 6.3.3 Multi-Compiler com Multi-OS

```yaml
strategy:
  matrix:
    include:
      - os: ubuntu-latest
        compiler: gcc
        cc: gcc-12
        cxx: g++-12
      - os: ubuntu-latest
        compiler: clang
        cc: clang-16
        cxx: clang++-16
      - os: macos-latest
        compiler: clang
        cc: clang
        cxx: clang++
      - os: windows-latest
        compiler: msvc
        cc: cl.exe
        cxx: cl.exe

runs-on: ${{ matrix.os }}

steps:
  - uses: actions/checkout@v4

  - name: Install dependencies (Linux)
    if: runner.os == 'Linux'
    run: |
      sudo apt-get update
      sudo apt-get install -y cmake ${{ matrix.compiler }}

  - name: Install dependencies (macOS)
    if: runner.os == 'macOS'
    run: brew install cmake

  - name: Install dependencies (Windows)
    if: runner.os == 'Windows'
    run: choco install cmake

  - name: Configure
    env:
      CC: ${{ matrix.cc }}
      CXX: ${{ matrix.cxx }}
    run: cmake -B build -DCMAKE_BUILD_TYPE=Release

  - name: Build
    run: cmake --build build --config Release

  - name: Test
    run: ctest --test-dir build --output-on-failure
```

### 6.3.4 Tabela de Compiladores

| Compilador | Versoes Suportadas | OS | Observacao |
|------------|-------------------|-----|------------|
| GCC | 9, 10, 11, 12, 13, 14 | Linux | Padrao Linux |
| Clang | 14, 15, 16, 17, 18 | Linux, macOS | Multi-plataforma |
| MSVC | 2019, 2022 | Windows | Padrao Windows |
| Apple Clang | 14, 15 | macOS | Especifico Apple |
| Intel ICC | 2021 | Linux | Otimizado Intel |
| Cranelift | - | Multi | Alternativa LLVM |

---

## 6.4 Multi-Version

Testar com multiplos versoes de linguagens garante compatibilidade retroativa e identifica problemas de deprecacao.

### 6.4.1 Node.js Multi-Version

```yaml
strategy:
  matrix:
    node-version: [18, 20, 22]

steps:
  - uses: actions/setup-node@v4
    with:
      node-version: ${{ matrix.node-version }}
      cache: 'npm'
  - run: npm ci
  - run: npm test
```

### 6.4.2 Python Multi-Version

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']

steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
      cache: 'pip'
  - run: pip install -r requirements.txt
  - run: pytest
```

### 6.4.3 Java Multi-Version

```yaml
strategy:
  matrix:
    java-version: ['17', '21']

steps:
  - uses: actions/setup-java@v4
    with:
      java-version: ${{ matrix.java-version }}
      distribution: 'temurin'
      cache: 'maven'
  - run: mvn test
```

### 6.4.4 Go Multi-Version

```yaml
strategy:
  matrix:
    go-version: ['1.21', '1.22', '1.23']

steps:
  - uses: actions/setup-go@v5
    with:
      go-version: ${{ matrix.go-version }}
      cache: true
  - run: go test ./...
```

### 6.4.5 Rust Multi-Version

```yaml
strategy:
  matrix:
    rust-version: ['stable', 'beta', 'nightly']

steps:
  - uses: dtolnay/rust-toolchain@master
    with:
      toolchain: ${{ matrix.rust-version }}
      components: rustfmt, clippy
  - run: cargo test
```

### 6.4.6 PHP Multi-Version

```yaml
strategy:
  matrix:
    php-version: ['8.1', '8.2', '8.3']

steps:
  - uses: shivammathur/setup-php@v2
    with:
      php-version: ${{ matrix.php-version }}
      coverage: xdebug
  - run: composer install
  - run: vendor/bin/phpunit
```

### 6.4.7 Tabela de Versoes por Linguagem

| Linguagem | Versoes Recomendadas | LTS | Observacao |
|-----------|---------------------|-----|------------|
| Node.js | 18, 20, 22 | 18, 20 | LTS a cada 2 versoes |
| Python | 3.10, 3.11, 3.12, 3.13 | 3.10, 3.12 | Suporte ~5 anos |
| Java | 17, 21 | 17, 21 | LTS a cada 2 versoes |
| Go | 1.21, 1.22, 1.23 | N/A | Suporte 2 versoes |
| Rust | stable, beta, nightly | N/A | Rolling release |
| PHP | 8.1, 8.2, 8.3 | 8.1 | Suporte ~3 anos |
| Ruby | 3.1, 3.2, 3.3 | 3.2 | Suporte ~3 anos |

---

## 6.5 Fail-fast

Fail-fast e uma estrategia que cancela todos os jobs em execucao assim que um deles falha.

### 6.5.1 Fail-fast Habilitado

```yaml
strategy:
  fail-fast: true  # Default: true
```

### 6.5.2 Fail-fast Desabilitado

```yaml
strategy:
  fail-fast: false
```

### 6.5.3 Fail-fast com Matrix Completa

```yaml
name: CI with Fail-fast

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: true
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying..."
```

### 6.5.4 Fail-fast com Continue-on-error

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: true
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci

      # Lint e opcional
      - name: Lint
        continue-on-error: true
        run: npm run lint

      # Test e obrigatorio
      - name: Test
        run: npm test
```

### 6.5.5 Tabela de Decisao Fail-fast

| Cenario | Fail-fast | Comportamento |
|---------|-----------|---------------|
| Testes unitarios | true | Cancela todos se um falhar |
| Testes de plataforma | false | Continua para ver quais falharam |
| Deploy pipeline | true | Cancela tudo se build falhar |
| Nightly build | false | Coleta todos os resultados |
| Pull request CI | true | Rapido feedback |

---

## 6.6 Matrix Outputs

Matrix outputs permitem coletar e compartilhar resultados entre jobs.

### 6.6.1 Matrix Outputs Basico

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      matrix-result: ${{ steps.check.outputs.result }}
    steps:
      - id: check
        run: echo "result=success" >> $GITHUB_OUTPUT
```

### 6.6.2 Matrix Outputs com Agregacao

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    outputs:
      results: ${{ steps.check.outputs.results }}
    steps:
      - id: check
        run: |
          echo "${{ matrix.package }}=success" >> $GITHUB_OUTPUT

  report:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "All builds: ${{ needs.build.outputs.results }}"
```

### 6.6.3 Matrix Outputs com Artifacts

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci

      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - run: |
          for dir in artifacts/*/; do
            package=$(basename "$dir")
            echo "Testing $package"
            npm run test --workspace=packages/$package
          done
```

---

## 6.7 Cross-compilation

Cross-compilation permite compilar codigo para arquiteturas diferentes daquela onde o build esta sendo executado.

### 6.7.1 Go Cross-compilation

```yaml
strategy:
  matrix:
    include:
      - goos: linux
        goarch: amd64
      - goos: linux
        goarch: arm64
      - goos: darwin
        goarch: arm64
      - goos: windows
        goarch: amd64

runs-on: ubuntu-latest

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-go@v5
    with:
      go-version: '1.22'
      cache: true

  - name: Build
    env:
      GOOS: ${{ matrix.goos }}
      GOARCH: ${{ matrix.goarch }}
    run: |
      SUFFIX=""
      if [ "${{ matrix.goos }}" = "windows" ]; then
        SUFFIX=".exe"
      fi
      go build -o bin/myapp-${{ matrix.goos }}-${{ matrix.goarch }}${SUFFIX} ./cmd/myapp

  - uses: actions/upload-artifact@v4
    with:
      name: myapp-${{ matrix.goos }}-${{ matrix.goarch }}
      path: bin/
```

### 6.7.2 Rust Cross-compilation

```yaml
strategy:
  matrix:
    target:
      - x86_64-unknown-linux-gnu
      - x86_64-unknown-linux-musl
      - aarch64-unknown-linux-gnu
      - x86_64-apple-darwin
      - aarch64-apple-darwin
      - x86_64-pc-windows-msvc

runs-on: ubuntu-latest

steps:
  - uses: actions/checkout@v4

  - uses: dtolnay/rust-toolchain@stable
    with:
      targets: ${{ matrix.target }}

  - name: Build
    run: cargo build --release --target ${{ matrix.target }}

  - uses: actions/upload-artifact@v4
    with:
      name: myapp-${{ matrix.target }}
      path: target/${{ matrix.target }}/release/
```

### 6.7.3 C++ Cross-compilation com Docker

```yaml
strategy:
  matrix:
    platform:
      - { arch: amd64, docker_arch: linux/amd64 }
      - { arch: arm64, docker_arch: linux/arm64 }

runs-on: ubuntu-latest

steps:
  - uses: actions/checkout@v4

  - name: Set up QEMU
    uses: docker/setup-qemu-action@v3

  - name: Set up Docker Buildx
    uses: docker/setup-buildx-action@v3

  - name: Build
    uses: docker/build-push-action@v5
    with:
      context: .
      platforms: ${{ matrix.platform.docker_arch }}
      load: true
      tags: myapp:${{ matrix.platform.arch }}

  - name: Extract binary
    run: |
      docker run --rm myapp:${{ matrix.platform.arch }} cat /app/bin/myapp > myapp-${{ matrix.platform.arch }}
      chmod +x myapp-${{ matrix.platform.arch }}

  - uses: actions/upload-artifact@v4
    with:
      name: myapp-${{ matrix.platform.arch }}
      path: myapp-${{ matrix.platform.arch }}
```

### 6.7.4 Tabela de Cross-compilation Targets

| Linguagem | Target | OS | Arquitetura |
|-----------|--------|-----|-------------|
| Go | linux/amd64 | Linux | x86_64 |
| Go | linux/arm64 | Linux | ARM64 |
| Go | darwin/arm64 | macOS | Apple Silicon |
| Go | windows/amd64 | Windows | x86_64 |
| Rust | x86_64-unknown-linux-gnu | Linux | x86_64 |
| Rust | aarch64-apple-darwin | macOS | Apple Silicon |
| Rust | x86_64-pc-windows-msvc | Windows | x86_64 |
| C++ | linux/amd64 | Linux | x86_64 |
| C++ | linux/arm64 | Linux | ARM64 |

---

## 6.8 Performance Optimization

Matrix builds podem ser lentos e caros. Existem varias estrategias para otimizar performance.

### 6.8.1 Max-parallel

```yaml
strategy:
  max-parallel: 3  # Maximo 3 jobs simultaneos
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
```

### 6.8.2 Concurrency Groups

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
```

### 6.8.3 Caching por Matrix

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

### 6.8.4 Path Filters

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
    paths-ignore:
      - 'docs/**'
      - '**.md'
```

### 6.8.5 Tabela de Otimizacao

| Estrategia | Impacto | Complexidade | Quando Usar |
|------------|---------|--------------|-------------|
| max-parallel | Alto | Baixo | Sempre |
| Concurrency groups | Alto | Baixo | Sempre |
| Caching | Alto | Baixo | Sempre |
| Path filters | Alto | Baixo | Sempre |
| fail-fast | Medio | Baixo | Quando aprovado |
| Sharded tests | Alto | Medio | Testes longos |

---

## 6.9 Conditional Matrix

Conditional matrix permite criar combinacoes dinamicas baseadas em contexto.

### 6.9.1 Conditional Matrix Basico

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    include:
      - os: ubuntu-latest
        full_test: true
      - os: macos-latest
        full_test: false
      - os: windows-latest
        full_test: false

steps:
  - name: Full test suite
    if: matrix.full_test
    run: npm test -- --full

  - name: Quick test
    if: "!matrix.full_test"
    run: npm test -- --quick
```

### 6.9.2 Conditional Matrix com Variavel

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
    experimental: [false]
    include:
      - os: ubuntu-latest
        node-version: 22
        experimental: true

steps:
  - name: Run tests
    run: npm test
    continue-on-error: ${{ matrix.experimental }}
```

### 6.9.3 Conditional Matrix com Evento

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    include:
      - os: ubuntu-latest
        deploy: true
      - os: macos-latest
        deploy: false
      - os: windows-latest
        deploy: false

steps:
  - name: Build
    run: npm run build

  - name: Deploy
    if: matrix.deploy && github.ref == 'refs/heads/main'
    run: ./deploy.sh
```

### 6.9.4 Conditional Matrix com Secret

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    include:
      - os: ubuntu-latest
        has_secret: true
      - os: macos-latest
        has_secret: false
      - os: windows-latest
        has_secret: false

steps:
  - name: Run with secret
    if: matrix.has_secret
    run: echo "Running with secret"
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}

  - name: Run without secret
    if: "!matrix.has_secret"
    run: echo "Running without secret"
```

---

## 6.10 Cost Optimization

Matrix builds podem consumir muitos minutos de build. A otimizacao de custos e essencial.

### 6.10.1 Tabela de Custos por Runner

| Runner | Custo por Minuto | Observacao |
|--------|------------------|------------|
| ubuntu-latest | $0.008 | Mais barato |
| macos-13 | $0.08 | 10x ubuntu |
| macos-14 | $0.12 | Apple Silicon |
| windows-latest | $0.016 | 2x ubuntu |

### 6.10.2 Estrategias de Reducao de Custo

| Estrategia | Reducao | Implementacao |
|------------|---------|---------------|
| Usar ubuntu quando possivel | 50-80% | Evitar macOS/Windows desnecessarios |
| max-parallel | 30-50% | Limitar jobs simultaneos |
| Concurrency groups | 20-40% | Cancelar workflows anteriores |
| Path filters | 40-60% | Evitar builds desnecessarios |
| fail-fast | 10-30% | Cancelar rapido em falha |
| Caching | 30-50% | Evitar rebuilds |

### 6.10.3 Exemplo de Matrix Otimizada

```yaml
name: Cost-Optimized CI

on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: true
      max-parallel: 2
      matrix:
        os: [ubuntu-latest]
        node-version: [20]
        include:
          - os: macos-latest
            node-version: 20
          - os: windows-latest
            node-version: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

### 6.10.4 Tabela de Decisao de Custo

| Cenario | Recomendacao | Custo Estimado |
|---------|--------------|----------------|
| PR baseline | ubuntu apenas | $0.08 |
| PR completo | ubuntu + macos + windows | $0.22 |
| Nightly | ubuntu apenas | $0.08 |
| Release | Todos os OS | $0.22 |
| Hotfix | ubuntu apenas | $0.08 |

---

## 6.11 Exemplos de Casos Reais

### 6.11.1 Pipeline Completa Multi-Plataforma

```yaml
name: Multi-Platform CI/CD

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  test:
    needs: lint
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results-${{ matrix.os }}-${{ matrix.node-version }}
          path: test-results/
          retention-days: 7

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1

  report:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/
      - name: Generate report
        run: |
          echo "# Test Results" > report.md
          echo "" >> report.md
          for dir in artifacts/test-results-*/; do
            os=$(echo "$dir" | grep -oP 'test-results-\K[^-]+')
            node=$(echo "$dir" | grep -oP 'test-results-[^-]+-\K\d+')
            echo "- OS: $os, Node: $node" >> report.md
          done
```

### 6.11.2 Pipeline C++ Multi-Compiler

```yaml
name: C++ Multi-Compiler CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            compiler: gcc-12
            cc: gcc-12
            cxx: g++-12
          - os: ubuntu-latest
            compiler: gcc-13
            cc: gcc-13
            cxx: g++-13
          - os: ubuntu-latest
            compiler: clang-15
            cc: clang-15
            cxx: clang++-15
          - os: ubuntu-latest
            compiler: clang-16
            cc: clang-16
            cxx: clang++-16
          - os: macos-latest
            compiler: apple-clang
            cc: clang
            cxx: clang++
          - os: windows-latest
            compiler: msvc
            cc: cl.exe
            cxx: cl.exe

    steps:
      - uses: actions/checkout@v4

      - name: Install compiler (Ubuntu)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake ${{ matrix.compiler }}

      - name: Install compiler (macOS)
        if: runner.os == 'macOS'
        run: brew install cmake

      - name: Install compiler (Windows)
        if: runner.os == 'Windows'
        run: choco install cmake

      - name: Configure
        env:
          CC: ${{ matrix.cc }}
          CXX: ${{ matrix.cxx }}
        run: cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD=17

      - name: Build
        run: cmake --build build --parallel $(nproc 2>/dev/null || echo 4)

      - name: Test
        run: ctest --test-dir build --output-on-failure

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: matrix.compiler == 'gcc-12'
        with:
          name: build-${{ matrix.compiler }}
          path: build/
          retention-days: 7
```

### 6.11.3 Pipeline Rust Cross-compilation

```yaml
name: Rust Cross-Platform CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        rust-version: [stable, beta, nightly]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ matrix.rust-version }}
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
      - run: cargo fmt --check
      - run: cargo clippy -- -D warnings
      - run: cargo test

  build:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-gnu
          - x86_64-unknown-linux-musl
          - aarch64-unknown-linux-gnu
          - x86_64-apple-darwin
          - aarch64-apple-darwin
          - x86_64-pc-windows-msvc
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}
      - uses: Swatinem/rust-cache@v2
        with:
          key: ${{ matrix.target }}

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Create archive
        run: |
          cd target/${{ matrix.target }}/release
          if [[ "${{ matrix.target }}" == *"windows"* ]]; then
            7z a ../../../myapp-${{ matrix.target }}.zip myapp.exe
          else
            tar -czf ../../../myapp-${{ matrix.target }}.tar.gz myapp
          fi

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.target }}
          path: myapp-${{ matrix.target }}.*
          retention-days: 7

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: artifacts/**/*
```

---

## 6.12 Exemplos Avancados

### 6.12.1 Pipeline Monorepo com Matrix

Pipeline completa para monorepo com multiplos pacotes e testes em paralelo.

```yaml
name: Monorepo Matrix CI

on: [push, pull_request]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.changes.outputs.packages }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            packages:
              - 'packages/**'

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages == 'true'
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect packages
        id: set-matrix
        run: |
          PACKAGES=$(find packages -name "package.json" -not -path "*/node_modules/*" | \
            xargs -I {} dirname {} | \
            xargs -I {} basename {} | \
            jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "matrix={\"package\":$PACKAGES}" >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test --workspace=packages/${{ matrix.package }}
      - run: npm run lint --workspace=packages/${{ matrix.package }}

  test-cross-platform:
    needs: build
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        package: ${{ fromJson(needs.build.outputs.matrix).package }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test --workspace=packages/${{ matrix.package }}

  build-packages:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJson(needs.build.outputs.matrix).package }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}
      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  publish:
    needs: build-packages
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJson(needs.build.outputs.matrix).package }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          registry-url: 'https://registry.npmjs.org'
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
      - name: Publish
        run: |
          cd packages/${{ matrix.package }}
          npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### 6.12.2 Pipeline com Matrix Dinamico

```yaml
name: Dynamic Matrix CI

on: [push, pull_request]

jobs:
  generate-matrix:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4

      - name: Generate matrix
        id: set-matrix
        run: |
          # Read matrix from config file
          if [ -f ".github/matrix.json" ]; then
            MATRIX=$(cat .github/matrix.json)
          else
            # Default matrix
            MATRIX='{"os":["ubuntu-latest"],"node-version":["20"]}'
          fi
          echo "matrix=$MATRIX" >> $GITHUB_OUTPUT

  test:
    needs: generate-matrix
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix: ${{ fromJson(needs.generate-matrix.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

### 6.12.3 Pipeline com Matrix e Artifacts

```yaml
name: Matrix with Artifacts

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        include:
          - os: ubuntu-latest
            artifact: linux-amd64
          - os: macos-latest
            artifact: darwin-arm64
          - os: windows-latest
            artifact: windows-amd64
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true

      - name: Build
        run: |
          SUFFIX=""
          if [ "${{ runner.os }}" = "Windows" ]; then
            SUFFIX=".exe"
          fi
          go build -o bin/myapp${SUFFIX} ./cmd/myapp

      - name: Create archive
        run: |
          if [ "${{ runner.os }}" = "Windows" ]; then
            7z a myapp-${{ matrix.artifact }}.zip bin/myapp.exe
          else
            tar -czf myapp-${{ matrix.artifact }}.tar.gz bin/myapp
          fi

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.artifact }}
          path: myapp-${{ matrix.artifact }}.*
          retention-days: 7

  test:
    needs: build
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        include:
          - os: ubuntu-latest
            artifact: linux-amd64
          - os: macos-latest
            artifact: darwin-arm64
          - os: windows-latest
            artifact: windows-amd64
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: myapp-${{ matrix.artifact }}
          path: bin/

      - name: Run tests
        run: |
          if [ "${{ runner.os }}" = "Windows" ]; then
            ./bin/myapp.exe --test
          else
            chmod +x ./bin/myapp
            ./bin/myapp --test
          fi

  release:
    needs: test
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: artifacts/**/*
```

### 6.12.4 Pipeline com Matrix e Database

```yaml
name: Matrix with Database

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        database: [postgres, mysql, sqlite]
        include:
          - database: postgres
            image: postgres:16
            port: 5432
            url: postgres://postgres:test@localhost:5432/testdb
          - database: mysql
            image: mysql:8
            port: 3306
            url: mysql://root:test@localhost:3306/testdb
          - database: sqlite
            image: ''
            port: ''
            url: sqlite::memory:
    services:
      database:
        image: ${{ matrix.image }}
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
          MYSQL_ROOT_PASSWORD: test
          MYSQL_DATABASE: testdb
        ports:
          - ${{ matrix.port }}:${{ matrix.port }}
        options: >-
          --health-cmd "pg_isready || mysqladmin ping || true"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        if: ${{ matrix.image != '' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test
        env:
          DATABASE_URL: ${{ matrix.url }}
          DATABASE_TYPE: ${{ matrix.database }}
```

---

## 6.13 Tabela Comparativa de Matrix Strategies

| Estrategia | Vantagens | Desvantagens | Uso Recomendado |
|------------|-----------|--------------|-----------------|
| Matrix simples | Facil configuracao | Limitada | Projetos pequenos |
| Include/Exclude | Flexivel | Complexa | Combinacoes especificas |
| Matrix dinamico | Automatico | Complexo | Monorepos |
| Matrix com outputs | Coleta dados | Mais passos | Reports |
| Matrix condicional | Otimizada | Complexa | Cenarios variados |

---

## 6.14 Fluxo de Matrix Build

```
                    ┌─────────────┐
                    │  Workflow    │
                    │   Trigger    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Matrix    │
                    │  Expansion  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │   Job 1     │ │ Job 2│ │   Job 3     │
       │  (OS A)     │ │(OS B)│ │  (OS C)     │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │   Results   │
                    │ Aggregation │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Deploy    │
                    │  (se todos  │
                    │  passaram)  │
                    └─────────────┘
```

---

## 6.15 Checklist de Matrix Build

Antes de configurar um matrix build, verifique:

| Item | Verificado |
|------|------------|
| Matrix nao e desnecessariamente grande | [ ] |
| fail-fast configurado corretamente | [ ] |
| max-parallel definido | [ ] |
| Concurrency groups ativos | [ ] |
| Caching configurado | [ ] |
| Path filters ativos | [ ] |
| Outputs definidos se necessario | [ ] |
| Artifacts com retencao adequada | [ ] |
| Custos estimados | [ ] |
| Rollback testado | [ ] |

---

## 6.16 Glossario de Matrix Builds

| Termo | Definicao |
|-------|-----------|
| Matrix | Combinacao de valores para executar multiplos jobs |
| Include | Adicionar combinacoes especificas a matrix |
| Exclude | Remover combinacoes especificas da matrix |
| Fail-fast | Cancelar todos os jobs quando um falha |
| Max-parallel | Limite de jobs executados simultaneamente |
| Concurrency group | Grupo para cancelar workflows anteriores |
| Cross-compilation | Compilar para arquitetura diferente |
| Path filter | Evitar builds baseado em arquivos modificados |
| Sharded test | Dividir testes em multiplos jobs |
| Artifact | Arquivo compartilhado entre jobs |

---

## 6.17 Exercicios

1. Crie um matrix build que teste Node.js 18/20/22 em 3 OS
2. Configure exclude para nao testar gcc no Windows
3. Implemente conditional matrix que rode testes completos apenas no Linux
4. Crie matrix build para compiladores gcc/clang/msvc em C++
5. Configure max-parallel para limitar jobs simultaneos
6. Implemente cross-compilation para Go com 4 targets
7. Configure cost-optimized matrix com path filters
8. Implemente matrix outputs para reportar status de todos os builds
9. Crie conditional matrix baseado em variavel de ambiente
10. Implemente matrix com continue-on-error para builds experimentais
11. Crie matrix build para Rust com stable/beta/nightly
12. Configure matrix com database para testes de integracao
13. Implemente matrix dinamico baseado em arquivos modificados
14. Crie matrix build com artifacts para releases multi-plataforma
15. Configure matrix com concurrency groups para evitar duplicatas

---

## 6.18 Exemplos de Casos Reais Detalhados

### 6.18.1 Pipeline Full Stack Multi-Plataforma

Pipeline completa para aplicacao full stack com frontend, backend e testes em todas as plataformas.

```yaml
name: Full Stack Multi-Platform CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run prettier:check

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run typecheck

  build-frontend:
    needs: [lint, type-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:frontend
      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
          retention-days: 1

  build-backend:
    needs: [lint, type-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:backend
      - uses: actions/upload-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/
          retention-days: 1

  test-frontend:
    needs: build-frontend
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
      - run: npm run test:frontend
      - uses: actions/upload-artifact@v4
        if: matrix.os == 'ubuntu-latest'
        with:
          name: frontend-coverage
          path: packages/frontend/coverage/
          retention-days: 7

  test-backend:
    needs: build-backend
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/
      - run: npm run test:backend
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
      - uses: actions/upload-artifact@v4
        with:
          name: backend-coverage
          path: packages/backend/coverage/
          retention-days: 7

  test-integration:
    needs: [build-frontend, build-backend]
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
      - uses: actions/download-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/
      - run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

  e2e:
    needs: [test-frontend, test-backend, test-integration]
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
      - uses: actions/download-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/
      - name: Start application
        run: |
          docker-compose up -d
          sleep 30
      - name: Run E2E tests
        run: npm run test:e2e
      - name: Collect logs
        if: failure()
        run: docker-compose logs > docker-logs.txt
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: e2e-logs-${{ matrix.os }}
          path: docker-logs.txt
          retention-days: 7
      - name: Stop application
        if: always()
        run: docker-compose down

  coverage-report:
    needs: [test-frontend, test-backend]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: frontend-coverage
          path: frontend-coverage/
      - uses: actions/download-artifact@v4
        with:
          name: backend-coverage
          path: backend-coverage/
      - name: Merge coverage
        run: |
          npx lcov-merger \
            frontend-coverage/lcov.info \
            backend-coverage/lcov.info \
            > combined-coverage.lcov
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: combined-coverage.lcov
          flags: fullstack
          fail_ci_if_error: false

  deploy-preview:
    needs: [e2e]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:frontend
      - run: npm run build:backend
      - name: Deploy preview
        run: |
          echo "Deploying preview for PR #${{ github.event.pull_request.number }}"
      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Preview deployment ready!'
            })

  deploy-production:
    needs: [e2e]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:frontend
      - run: npm run build:backend
      - name: Deploy to production
        run: |
          echo "Deploying to production"
          ./deploy.sh
```

### 6.18.2 Pipeline Rust Multi-Target

Pipeline completa para projeto Rust com multi-target e releases.

```yaml
name: Rust Multi-Target CI

on: [push, pull_request]

jobs:
  fmt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt
      - run: cargo fmt --check

  clippy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy
      - uses: Swatinem/rust-cache@v2
      - run: cargo clippy -- -D warnings

  test:
    needs: [fmt, clippy]
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        rust-version: [stable, beta]
        include:
          - os: ubuntu-latest
            rust-version: nightly
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ matrix.rust-version }}
      - uses: Swatinem/rust-cache@v2
        with:
          key: ${{ matrix.os }}-${{ matrix.rust-version }}
      - run: cargo test --verbose
      - run: cargo test --verbose --release

  build:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-gnu
          - x86_64-unknown-linux-musl
          - aarch64-unknown-linux-gnu
          - x86_64-apple-darwin
          - aarch64-apple-darwin
          - x86_64-pc-windows-msvc
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}
      - uses: Swatinem/rust-cache@v2
        with:
          key: build-${{ matrix.target }}

      - name: Install cross-compilation tools
        if: contains(matrix.target, 'aarch64-unknown-linux')
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-aarch64-linux-gnu

      - name: Build
        run: cargo build --release --target ${{ matrix.target }}

      - name: Create archive
        run: |
          cd target/${{ matrix.target }}/release
          if [[ "${{ matrix.target }}" == *"windows"* ]]; then
            7z a ../../../myapp-${{ matrix.target }}.zip myapp.exe
          elif [[ "${{ matrix.target }}" == *"apple"* ]]; then
            tar -czf ../../../myapp-${{ matrix.target }}.tar.gz myapp
          else
            tar -czf ../../../myapp-${{ matrix.target }}.tar.gz myapp
          fi

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.target }}
          path: myapp-${{ matrix.target }}.*
          retention-days: 7

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: artifacts/**/*
```

### 6.18.3 Pipeline C++ com CMake e Conan

Pipeline completa para projeto C++ com CMake, Conan e multi-compiler.

```yaml
name: C++ CI with Conan

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        include:
          - os: ubuntu-latest
            compiler: gcc-12
            cc: gcc-12
            cxx: g++-12
            build_type: Release
          - os: ubuntu-latest
            compiler: gcc-13
            cc: gcc-13
            cxx: g++-13
            build_type: Release
          - os: ubuntu-latest
            compiler: clang-15
            cc: clang-15
            cxx: clang++-15
            build_type: Release
          - os: ubuntu-latest
            compiler: clang-16
            cc: clang-16
            cxx: clang++-16
            build_type: Release
          - os: macos-latest
            compiler: apple-clang
            cc: clang
            cxx: clang++
            build_type: Release
          - os: windows-latest
            compiler: msvc
            cc: cl.exe
            cxx: cl.exe
            build_type: Release
          - os: ubuntu-latest
            compiler: gcc-12
            cc: gcc-12
            cxx: g++-12
            build_type: Debug
    steps:
      - uses: actions/checkout@v4

      - name: Install Conan
        run: pip install conan

      - name: Detect Conan profile
        run: conan profile detect --force

      - name: Install dependencies
        run: conan install . --build=missing -of build

      - name: Install compiler (Ubuntu)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake ${{ matrix.compiler }}

      - name: Install compiler (macOS)
        if: runner.os == 'macOS'
        run: brew install cmake

      - name: Install compiler (Windows)
        if: runner.os == 'Windows'
        run: choco install cmake

      - name: Configure
        env:
          CC: ${{ matrix.cc }}
          CXX: ${{ matrix.cxx }}
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
            -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
            -DCMAKE_CXX_STANDARD=17

      - name: Build
        run: cmake --build build --config ${{ matrix.build_type }} --parallel $(nproc 2>/dev/null || echo 4)

      - name: Test
        run: ctest --test-dir build --config ${{ matrix.build_type }} --output-on-failure

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        if: matrix.compiler == 'gcc-12' && matrix.build_type == 'Release'
        with:
          name: build-${{ matrix.compiler }}-${{ matrix.build_type }}
          path: build/
          retention-days: 7

  coverage:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ gcovr conan

      - name: Detect Conan profile
        run: conan profile detect --force

      - name: Install Conan packages
        run: conan install . --build=missing -of build

      - name: Configure with coverage
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_CXX_FLAGS="--coverage -fprofile-arcs -ftest-coverage" \
            -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake

      - name: Build
        run: cmake --build build

      - name: Test
        run: ctest --test-dir build --output-on-failure

      - name: Generate coverage report
        run: |
          gcovr --root . \
            --filter src/ \
            --exclude tests/ \
            --xml-pretty \
            -o coverage.xml

      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.xml
          fail_ci_if_error: false
```

### 6.18.4 Pipeline Python Multi-Version com Matrix

Pipeline completa para pacote Python com multi-version e matrix.

```yaml
name: Python Multi-Version CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install ruff
      - run: ruff check src/
      - run: ruff format --check src/

  test:
    needs: lint
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']
        exclude:
          - os: macos-latest
            python-version: '3.10'
          - os: windows-latest
            python-version: '3.10'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: pip install -e ".[test]"
      - run: pytest --junitxml=test-results/junit.xml --cov=src --cov-report=xml
      - uses: actions/upload-artifact@v4
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
        with:
          name: coverage
          path: coverage.xml
          retention-days: 7

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install build twine
      - run: python -m build
      - run: twine check dist/*
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 30

  publish-pypi:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_TOKEN }}

  publish-testpypi:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          repository-url: https://test.pypi.org/legacy/
          password: ${{ secrets.TEST_PYPI_TOKEN }}

  coverage:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: coverage
          path: coverage.xml
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.xml/coverage.xml
          flags: unittests
          fail_ci_if_error: false
```

### 6.18.5 Pipeline Go Multi-Version com Matrix

Pipeline completa para projeto Go com multi-version e cross-compilation.

```yaml
name: Go Multi-Version CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - run: go vet ./...
      - name: Run golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        go-version: ['1.21', '1.22', '1.23']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: ${{ matrix.go-version }}
          cache: true
      - run: go test -v -race -coverprofile=coverage.out ./...
      - uses: codecov/codecov-action@v4
        if: matrix.go-version == '1.22'
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.out
          fail_ci_if_error: false

  build:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - goos: linux
            goarch: amd64
            suffix: ''
          - goos: linux
            goarch: arm64
            suffix: ''
          - goos: darwin
            goarch: arm64
            suffix: ''
          - goos: windows
            goarch: amd64
            suffix: '.exe'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true

      - name: Build
        env:
          GOOS: ${{ matrix.goos }}
          GOARCH: ${{ matrix.goarch }}
        run: |
          go build -ldflags "-X main.version=${{ github.sha }}" \
            -o bin/myapp-${{ matrix.goos }}-${{ matrix.goarch }}${{ matrix.suffix }} \
            ./cmd/myapp

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.goos }}-${{ matrix.goarch }}
          path: bin/
          retention-days: 7

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            artifacts/myapp-linux-amd64/*
            artifacts/myapp-linux-arm64/*
            artifacts/myapp-darwin-arm64/*
            artifacts/myapp-windows-amd64/*
```

---

## 6.19 Troubleshooting de Matrix Builds

### 6.19.1 Problemas Comuns e Solucoes

| Problema | Causa | Solucao |
|----------|-------|---------|
| Jobs nao executam | Matrix vazio | Verificar sintaxe da matrix |
| Jobs cancelados | fail-fast: true | Desabilitar ou corrigir job falho |
| Custo alto | Muitas combinacoes | Reduzir matrix ou usar max-parallel |
| Lentidao | Muitos jobs | Usar caching e path filters |
| Falha em um OS | Incompatibilidade | Usar exclude ou continue-on-error |
| Outputs nao funcionam | Sintaxe incorreta | Verificar GITHUB_OUTPUT |

### 6.19.2 Debug de Matrix Builds

```yaml
jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - name: Debug matrix
        run: |
          echo "OS: ${{ matrix.os }}"
          echo "Node Version: ${{ matrix.node-version }}"
          echo "Build Type: ${{ matrix.build-type }}"
          echo "All matrix values:"
          echo '${{ toJSON(matrix) }}' | jq .
```

### 6.19.3 Logs de Matrix Builds

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/checkout@v4

      - name: Log matrix context
        run: |
          echo "Matrix OS: ${{ matrix.os }}"
          echo "Runner OS: ${{ runner.os }}"
          echo "Runner Arch: ${{ runner.arch }}"
          echo "GitHub Ref: ${{ github.ref }}"
          echo "GitHub SHA: ${{ github.sha }}"

      - name: Run tests
        run: npm test
```

---

## 6.20 Melhores Praticas

### 6.20.1 Regras de Ouro

| Regra | Descricao | Prioridade |
|-------|-----------|------------|
| Usar fail-fast | Cancelar rapido em falha | Alta |
| Definir max-parallel | Limitar jobs simultaneos | Alta |
| Usar caching | Evitar rebuilds | Alta |
| Definir timeouts | Evitar jobs presos | Alta |
| Usar path filters | Evitar builds desnecessarios | Media |
| Definir retention | Economizar armazenamento | Media |
| Usar concurrency groups | Cancelar workflows anteriores | Media |
| Monitorar custos | Evitar surpresas na fatura | Alta |

### 6.20.2 Checklist de Revisao

| Item | Verificado |
|------|------------|
| Matrix nao e desnecessariamente grande | [ ] |
| fail-fast configurado corretamente | [ ] |
| max-parallel definido | [ ] |
| Timeouts configurados | [ ] |
| Caching ativo | [ ] |
| Path filters ativos | [ ] |
| Concurrency groups ativos | [ ] |
| Outputs definidos se necessario | [ ] |
| Artifacts com retencao adequada | [ ] |
| Custos estimados | [ ] |
| Rollback testado | [ ] |
| Logs configurados | [ ] |

---

## 6.21 Fluxo de Decisao de Matrix

```
                    ┌─────────────┐
                    │   Precisa   │
                    │ de matrix?  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Sim/Nao    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼──────┐
       │    Sim      │          │     Nao      │
       │             │          │              │
       │ Quantos     │          │ Usar job     │
       │ parametros? │          │ unico        │
       └──────┬──────┘          └──────────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼───┐ ┌──▼──┐ ┌───▼───┐
│  2    │ │  3  │ │  4+   │
│       │ │     │ │       │
│Matrix │ │Max  │ │Dividir│
│simples│ │para-│ │em     │
│       │ │llel │ │jobs   │
└───────┘ └─────┘ └───────┘
```

---

## 6.22 Referencias

1. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
2. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#expanding-or-adding-matrix-configurations
3. https://docs.github.com/en/actions/learn-github-actions/contexts#matrix-context
4. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-for-your-jobs
5. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-strategy
6. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#defining-matrix-strategies
7. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#expanding-or-adding-matrix-configurations
8. https://docs.github.com/en/actions/learn-github-actions/expressions
9. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-for-your-jobs
10. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#using-a-matrix-strategy
11. https://docs.github.com/en/actions/learn-github-actions/contexts#matrix-context
12. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs#expanding-or-adding-matrix-configurations

---

## 6.23 Glossario Completo

| Termo | Definicao | Exemplo de Uso |
|-------|-----------|----------------|
| Matrix | Combinacao de valores para jobs | os: [ubuntu, macos, windows] |
| Include | Adicionar combinacoes especificas | include: [{os: ubuntu, extra: true}] |
| Exclude | Remover combinacoes especificas | exclude: [{os: windows, node: 18}] |
| Fail-fast | Cancelar jobs quando um falha | fail-fast: true |
| Max-parallel | Limite de jobs simultaneos | max-parallel: 3 |
| Concurrency group | Grupo para cancelar workflows | group: ci-${{ github.ref }} |
| Cross-compilation | Compilar para outra arquitetura | GOOS=linux GOARCH=arm64 |
| Path filter | Evitar builds por arquivos | paths: ['src/**'] |
| Sharded test | Dividir testes em partes | --shard=1/4 |
| Artifact | Arquivo compartilhado entre jobs | upload-artifact/download-artifact |
| Runner | Maquina de execucao | ubuntu-latest, macos-latest |
| Job | Unidade de trabalho | test, build, deploy |
| Step | Acao dentro de um job | uses: actions/checkout@v4 |
| Workflow | Arquivo de pipeline | .github/workflows/ci.yml |
| Trigger | Evento que inicia workflow | push, pull_request |
| Expression | Avaliacao dinamica | ${{ matrix.os }} |
| Context | Objeto com dados do evento | github, matrix, runner |
| Service | Container auxiliar para testes | postgres, redis |
| Environment | Ambiente de deploy | staging, production |
| Secret | Dado sensivel criptografado | secrets.GITHUB_TOKEN |
| Variable | Variavel de ambiente | vars.APP_NAME |

---

## 6.24 Tabela de Compatibilidade

### 6.24.1 Compatibilidade de Runners

| Runner | Linux | macOS | Windows | ARM64 | Observacao |
|--------|-------|-------|---------|-------|------------|
| ubuntu-latest | Sim | Nao | Nao | Nao | Mais rapido |
| macos-13 | Nao | Sim | Nao | Nao | x86_64 |
| macos-14 | Nao | Sim | Nao | Sim | Apple Silicon |
| macos-latest | Nao | Sim | Nao | Sim | Padrao |
| windows-latest | Nao | Nao | Sim | Nao | Mais lento |

### 6.24.2 Compatibilidade de Linguagens

| Linguagem | Linux | macOS | Windows | Observacao |
|-----------|-------|-------|---------|------------|
| Node.js | Sim | Sim | Sim | Multi-plataforma |
| Python | Sim | Sim | Sim | Multi-plataforma |
| Java | Sim | Sim | Sim | Multi-plataforma |
| Go | Sim | Sim | Sim | Multi-plataforma |
| Rust | Sim | Sim | Sim | Multi-plataforma |
| C/C++ | Sim | Sim | Sim | Requer compilador |
| Ruby | Sim | Sim | Sim | Multi-plataforma |
| PHP | Sim | Sim | Sim | Multi-plataforma |

---

## 6.25 Metricas de Matrix Builds

### 6.25.1 Metricas Importantes

| Metrica | Descricao | Meta |
|---------|-----------|------|
| Tempo medio de build | Duracao media dos jobs | < 10 minutos |
| Taxa de sucesso | Jobs que terminam com sucesso | > 95% |
| Custo por build | Minutos consumidos por build | < 100 minutos |
| Tempo de feedback | Tempo ate primeiro resultado | < 5 minutos |
| Cobertura de plataforma | OS testados / OS suportados | 100% |
| Cobertura de versao | Versoes testadas / Versoes suportadas | 100% |

### 6.25.2 Dashboard de Monitoramento

```yaml
jobs:
  metrics:
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Collect metrics
        run: |
          echo "## Build Metrics" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Trigger | ${{ github.event_name }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Ref | ${{ github.ref }} |" >> $GITHUB_STEP_SUMMARY
          echo "| SHA | ${{ github.sha }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Actor | ${{ github.actor }} |" >> $GITHUB_STEP_SUMMARY
```

---

## 6.26 Resumo Final

Matrix builds sao uma ferramenta poderosa para garantir qualidade e compatibilidade em projetos de software. Use-as sabiamente:

1. **Comece simples**: Comece com matrix basico e adicione complexidade conforme necessario
2. **Otimize sempre**: Use caching, path filters e concurrency groups
3. **Monitore custos**: Matrix builds podem consumir muitos minutos
4. **Use fail-fast**: Cancelar rapido em falha economiza tempo e dinheiro
5. **Teste em todas as plataformas**: Garanta compatibilidade cross-platform
6. **Documente decisoes**: Registre por que certas combinacoes foram incluidas ou excluidas
7. **Revise regularmente**: Matrix builds podem ficar desatualizadas com o tempo

---

## 6.27 Fluxo de Trabalho Recomendado

### 6.27.1 Para Projetos Novos

1. Comece com matrix simples (1 OS, 1 versao)
2. Adicione testes cross-platform quando necessario
3. Configure caching e path filters
4. Adicione matrix de versoes para compatibilidade
5. Configure monitoring de custos

### 6.27.2 Para Projetos Existentes

1. Audite matrix atual
2. Identifique combinacoes desnecessarias
3. Otimize com exclude e max-parallel
4. Configure concurrency groups
5. Implemente monitoring de custos

### 6.27.3 Para Monorepos

1. Detecte mudancas com path filters
2. Use matrix dinamico para pacotes
3. Teste cada pacote independentemente
4. Agregue resultados para deploy
5. Otimize com caching compartilhado

---

## 6.28 Recursos Adicionais

| Recurso | URL | Descricao |
|---------|-----|-----------|
| GitHub Actions Docs | docs.github.com/actions | Documentacao oficial |
| Actions Marketplace | github.com/marketplace?type=actions | Actions populares |
| GitHub Actions Learning Lab | lab.github.com | Cursos interativos |
| GitHub Actions Community | github.community | Forum da comunidade |
| GitHub Actions Status | www.githubstatus.com | Status dos servicos |

---

## 6.29 Agradecimentos

Este capitulo foi elaborado com base nas melhores praticas da comunidade de GitHub Actions. Agradecemos a todos os contribuidores que compartilham conhecimento e experiencia no desenvolvimento de pipelines de CI/CD eficientes e confiaveis.

---

## 6.30 Versao deste Documento

| Campo | Valor |
|-------|-------|
| Versao | 1.0 |
| Data | 2024 |
| Autor | Equipe DevSecurity |
| Licenca | MIT |
| Status | Producao |