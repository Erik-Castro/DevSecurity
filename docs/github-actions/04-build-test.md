---
layout: default
title: "04-build-test"
---

# Capitulo 4 — Build e Test Automatizados

> *"Se nao esta testado, nao esta pronto."*

---

## Sumario

| Secao | Descricao |
|-------|-----------|
| 4.1 | Pipeline Basico |
| 4.2 | Setup Languages |
| 4.3 | Build Steps |
| 4.4 | Test Frameworks |
| 4.5 | Test Reporting (JUnit) |
| 4.6 | Code Coverage (Codecov/Coveralls) |
| 4.7 | Fail-fast |
| 4.8 | Conditional Steps |
| 4.9 | Multi-Language Builds |
| 4.10 | CMake Workflow |
| 4.11 | Performance Optimization |

---

## Objetivos de Aprendizado

1. Configurar pipelines de build completos e robustos
2. Usar setup actions para multiplas linguagens de programacao
3. Definir build steps eficientes e reutilizaveis
4. Integrar test frameworks populares como Jest, pytest, JUnit, e Go test
5. Configurar test reporting com formato JUnit XML
6. Implementar code coverage com Codecov e Coveralls
7. Utilizar fail-fast para cancelar workflows rapido em caso de falha
8. Criar conditional steps baseados em contexto e expresoes
9. Configurar multi-language builds para monolitos e monorepos
10. Implementar workflows completos de build para CMake
11. Otimizar performance de pipelines com caching e paralelismo

---

## 4.1 Pipeline Basico

Um pipeline basico de build e test e o fundamento de qualquer projeto com GitHub Actions. Este pipeline deve executar as operacoes fundamentais: checkout do codigo, setup do ambiente, instalacao de dependencias, build e execucao de testes.

### 4.1.1 Estrutura Fundamental

Toda pipeline de CI comeca com a declaracao de nome, triggers e jobs. O nome identifica o workflow na interface do GitHub. Os triggers definem quando o workflow e executado. Os jobs contem os steps que realizam o trabalho real.

```yaml
name: CI

on: [push, pull_request]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install
        run: npm ci

      - name: Build
        run: npm run build

      - name: Test
        run: npm test
```

### 4.1.2 Pipeline com Multiple Stages

Em projetos maiores, e comum dividir o pipeline em multiples jobs que rodam sequencialmente ou em paralelo. Cada job representa uma fase do processo de build.

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

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

  build:
    needs: [lint, type-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  integration-test:
    needs: build
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
      - run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
```

### 4.1.3 Pipeline com Matrix Basico

Matrix builds permitem executar o mesmo pipeline em multiplos ambientes simultaneamente.

```yaml
name: CI Matrix

on: [push, pull_request]

jobs:
  build-and-test:
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
      - run: npm run build
      - run: npm test
```

### 4.1.4 Pipeline com Services

Muitos projetos precisam de servicos como bancos de dados, caches ou filas de mensagens durante os testes.

```yaml
name: CI with Services

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      mongodb:
        image: mongo:7
        ports:
          - 27017:27017
        options: >-
          --health-cmd "mongosh --eval 'db.adminCommand({ping:1})'"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      rabbitmq:
        image: rabbitmq:3-management
        ports:
          - 5672:5672
          - 15672:15672
        env:
          RABBITMQ_DEFAULT_USER: guest
          RABBITMQ_DEFAULT_PASS: guest
        options: >-
          --health-cmd "rabbitmq-diagnostics -q ping"
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
      - run: npm run test:integration
        env:
          REDIS_URL: redis://localhost:6379
          MONGODB_URL: mongodb://localhost:27017
          RABBITMQ_URL: amqp://guest:guest@localhost:5672
```

### 4.1.5 Pipeline com Timeout

Definir timeouts e uma boa pratica para evitar jobs que travam indefinidamente e consomem minutos preciosos do plano gratuito.

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - run: npm test

  slow-test:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run test:slow
```

### 4.1.6 Pipeline com Environment Variables

Variaveis de ambiente sao uteis para configurar o comportamento do pipeline sem modificar o codigo fonte.

```yaml
name: CI with Environment

on: [push, pull_request]

env:
  NODE_ENV: test
  CI: true
  FORCE_COLOR: 1

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      DEBUG: 'app:*'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
        env:
          NODE_ENV: production
      - run: npm test
        env:
          NODE_OPTIONS: '--max-old-space-size=4096'
```

### 4.1.7 Pipeline com Permissions

Definir permissoes explicitamente e uma boa pratica de seguranca para minimizar o escopo do GITHUB_TOKEN.

```yaml
name: CI with Permissions

on: [push, pull_request]

permissions:
  contents: read
  checks: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: npm test
```

---

## 4.2 Setup Languages

A configuracao do ambiente de build e uma etapa critica. Cada linguagem de programacao tem sua propria action de setup que configura o interpretador ou compilador, caches de dependencias e registos de pacotes.

### 4.2.1 Node.js

O setup-node e uma das actions mais usadas. Ele configura o Node.js, configura o cache do gerenciador de pacotes e pode configurar registos privados.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| node-version | string | Versao do Node.js | - |
| cache | string | Gerenciador de pacotes para cache | - |
| registry-url | string | URL do registro npm | - |
| always-auth | boolean | Sempre autenticar no registro | false |
| scope | string | Escopo do registro | - |

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
    registry-url: 'https://registry.npmjs.org'
```

Configuracao com multiplos registos e scopes:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
    registry-url: 'https://npm.pkg.github.com'
    scope: '@myorg'
```

### 4.2.2 Python

O setup-python suporta multiplos gerenciadores de pacotes (pip, pipenv, poetry) e caches automaticos.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| python-version | string | Versao do Python | - |
| cache | string | Gerenciador de pacotes para cache | - |
| architecture | string | Arquitetura (x64, x86) | x64 |
| check-latest | boolean | Verificar versao mais recente | false |

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

Configuracao com Poetry:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'poetry'

- run: poetry install
```

Configuracao com multiplos arquitetonicos:

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12']
    architecture: [x64, x86]
steps:
  - uses: actions/setup-python@v5
    with:
      python-version: ${{ matrix.python-version }}
      architecture: ${{ matrix.architecture }}
      cache: 'pip'
```

### 4.2.3 Java

O setup-java suporta multiplos distribuicoes JDK (Temurin, Zulu, GraalVM, etc.) e gerenciadores de build (Maven, Gradle).

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| java-version | string | Versao do JDK | - |
| distribution | string | Distribuicao do JDK | temurin |
| cache | string | Gerenciador de build para cache | - |
| java-package | string | Tipo de pacote (jdk, jre, jdk+ndk) | jdk |

```yaml
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'temurin'
    cache: 'maven'
```

Configuracao com Gradle:

```yaml
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'graalvm'
    cache: 'gradle'
```

### 4.2.4 Go

O setup-go configura o Go e ativa o cache automatico de modulo e build.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| go-version | string | Versao do Go | - |
| cache | boolean | Ativar cache | true |
| check-latest | boolean | Verificar versao mais recente | false |

```yaml
- uses: actions/setup-go@v5
  with:
    go-version: '1.22'
    cache: true
```

### 4.2.5 Rust

O setup do Rust e feito via dtolnay/rust-toolchain, que configura o compilador, componentes e targets.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| toolchain | string | Toolchain do Rust | stable |
| components | string | Componentes adicionais | - |
| targets | string | Targets de compilacao | - |

```yaml
- uses: dtolnay/rust-toolchain@stable
  with:
    components: rustfmt, clippy
    targets: x86_64-unknown-linux-gnu
```

### 4.2.6 .NET

O setup-dotnet configura o SDK do .NET e caches de NuGet.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| dotnet-version | string | Versao do .NET SDK | - |
| cache | boolean | Ativar cache NuGet | false |

```yaml
- uses: actions/setup-dotnet@v4
  with:
    dotnet-version: '8.0.x'
    cache: true
```

### 4.2.7 Ruby

O setup-ruby configura o Ruby e bundler com caches.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| ruby-version | string | Versao do Ruby | - |
| bundler-cache | boolean | Cache do Bundler | false |

```yaml
- uses: ruby/setup-ruby@v1
  with:
    ruby-version: '3.3'
    bundler-cache: true
```

### 4.2.8 PHP

O setup-php configura o PHP com extensoes e caches do Composer.

| Parametro | Tipo | Descricao | Default |
|-----------|------|-----------|---------|
| php-version | string | Versao do PHP | - |
| tools | string | Ferramentas adicionais | - |
| coverage | string | Driver de coverage | xdebug |

```yaml
- uses: shivammathur/setup-php@v2
  with:
    php-version: '8.3'
    tools: composer:v2
    coverage: xdebug
```

### 4.2.9 Tabela Resumo de Setup Actions

| Linguagem | Action | Cache Built-in | Registry Config |
|-----------|--------|----------------|-----------------|
| Node.js | actions/setup-node@v4 | npm, yarn, pnpm | Sim |
| Python | actions/setup-python@v5 | pip, pipenv, poetry | Nao |
| Java | actions/setup-java@v4 | maven, gradle | Nao |
| Go | actions/setup-go@v5 | modules, build | Nao |
| Rust | dtolnay/rust-toolchain@stable | Nao (usar Swatinem/rust-cache) | Nao |
| .NET | actions/setup-dotnet@v4 | NuGet | Nao |
| Ruby | ruby/setup-ruby@v1 | Bundler | Nao |
| PHP | shivammathur/setup-php@v2 | Composer | Nao |

---

## 4.3 Build Steps

Build steps sao os comandos executados para compilar, empacotar ou transformar o codigo fonte em artefatos prontos para uso. A definicao correta dos build steps e essencial para garantir reprodutibilidade e eficiencia.

### 4.3.1 Build Node.js

O build de um projeto Node.js tipicamente envolve instalacao de dependencias, transpilacao de TypeScript, bundle com bundler e copia de assets estaticos.

```yaml
- name: Install dependencies
  run: npm ci

- name: Build TypeScript
  run: npm run build

- name: Bundle application
  run: npx webpack --mode production

- name: Copy static assets
  run: cp -r public/ dist/public/
```

Build com Next.js:

```yaml
- name: Build Next.js
  run: npm run build
  env:
    NEXT_TELEMETRY_DISABLED: 1
    NODE_ENV: production
```

Build com Vite:

```yaml
- name: Build Vite
  run: npm run build
  env:
    NODE_ENV: production
```

### 4.3.2 Build Python

Builds Python normalmente envolvem criacao de pacotes wheel, validacao de metadados e empacotamento de distribuicoes.

```yaml
- name: Install build tools
  run: pip install build twine

- name: Build package
  run: python -m build

- name: Check package
  run: twine check dist/*

- name: Upload to PyPI
  run: twine upload dist/*
  if: startsWith(github.ref, 'refs/tags/')
  env:
    TWINE_USERNAME: __token__
    TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
```

Build com Poetry:

```yaml
- name: Install Poetry
  run: pip install poetry

- name: Build package
  run: poetry build

- name: Publish to PyPI
  run: poetry publish
  if: startsWith(github.ref, 'refs/tags/')
  env:
    POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_TOKEN }}
```

### 4.3.3 Build Java

Builds Java tipicamente usam Maven ou Gradle com profiles especificos para CI.

```yaml
# Maven
- name: Build with Maven
  run: mvn -B package -DskipTests

# Maven com profile de CI
- name: Build with Maven (CI profile)
  run: mvn -B package -P ci -DskipTests

# Gradle
- name: Build with Gradle
  run: ./gradlew build -x test

# Gradle com task especifica
- name: Build JAR
  run: ./gradlew bootJar -x test
```

### 4.3.4 Build Go

Builds Go sao simples e eficientes, com cross-compilacao facil usando variaveis de ambiente.

```yaml
- name: Build
  run: go build -o bin/app ./cmd/app

# Cross-compilacao
- name: Build for Linux
  env:
    GOOS: linux
    GOARCH: amd64
  run: go build -o bin/app-linux-amd64 ./cmd/app

- name: Build for macOS
  env:
    GOOS: darwin
    GOARCH: arm64
  run: go build -o bin/app-darwin-arm64 ./cmd/app

# Com flags de versionamento
- name: Build with ldflags
  run: |
    go build -ldflags "-X main.version=${{ github.sha }} -X main.buildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)" -o bin/app ./cmd/app
```

### 4.3.5 Build Rust

Builds Rust envolvem compilacao com cargo, otimizacoes e geracao de binarios.

```yaml
- name: Build
  run: cargo build --release

# Cross-compilacao
- name: Build for target
  run: cargo build --release --target x86_64-unknown-linux-musl

# Com features especificas
- name: Build with features
  run: cargo build --release --features "full"
```

### 4.3.6 Build C/C++ com CMake

Builds C/C++ normalmente usam CMake para gerar arquivos de build e depois compilam com make ou ninja.

```yaml
- name: Configure CMake
  run: cmake -B build -DCMAKE_BUILD_TYPE=Release

- name: Build
  run: cmake --build build --parallel $(nproc 2>/dev/null || echo 4)

- name: Run tests
  run: ctest --test-dir build --output-on-failure
```

### 4.3.7 Build Docker

Builds Docker criam imagens containerizadas que podem ser distribuidas e executadas em qualquer ambiente.

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    push: false
    tags: myapp:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 4.3.8 Build com Scripts Customizados

Muitos projetos tem scripts de build customizados que precisam ser executados em sequencia.

```yaml
- name: Setup environment
  run: |
    echo "Building for ${{ github.ref_name }}"
    export BUILD_ENV=${{ github.ref_name == 'main' && 'production' || 'staging' }}
    echo "BUILD_ENV=$BUILD_ENV" >> $GITHUB_ENV

- name: Run build script
  run: |
    chmod +x scripts/build.sh
    ./scripts/build.sh

- name: Verify build output
  run: |
    if [ ! -d "dist" ]; then
      echo "Build output directory not found"
      exit 1
    fi
    ls -la dist/
```

### 4.3.9 Tabela de Build Commands por Linguagem

| Linguagem | Command de Build | Comando Alternativo | Observacao |
|-----------|------------------|---------------------|------------|
| Node.js | `npm run build` | `yarn build`, `pnpm build` | Depende do script no package.json |
| Python | `python -m build` | `poetry build` | Requer ferramentas de build |
| Java | `mvn package` | `gradle build` | Depende do gerenciador de build |
| Go | `go build` | `make build` | Cross-compilacao com GOOS/GOARCH |
| Rust | `cargo build` | `cargo build --release` | Optimizations com --release |
| C/C++ | `cmake --build build` | `make -j4` | Requer CMake ou Makefile |
| Ruby | `bundle exec rake build` | `gem build` | Depende do gerenciador de pacotes |
| PHP | `composer build` | `vendor/bin/phpunit` | Depende do composer.json |

---

## 4.4 Test Frameworks

A integracao correta de test frameworks e essencial para garantir qualidade de codigo. Cada linguagem tem seus proprios frameworks e padroes de configuracao.

### 4.4.1 Jest (Node.js)

Jest e o framework de teste mais popular para Node.js, suportando unit tests, integration tests e snapshot tests.

```yaml
- name: Run Jest tests
  run: npx jest --coverage --reporters=default --reporters=jest-junit
  env:
    JEST_JUNIT_OUTPUT_DIR: ./test-results
    JEST_JUNIT_OUTPUT_NAME: results.xml
```

Configuracao com reporters personalizados:

```yaml
- name: Run tests with reporters
  run: |
    npx jest \
      --coverage \
      --coverageDirectory=coverage \
      --ci \
      --reporters=default \
      --reporters=jest-junit
  env:
    JEST_JUNIT_OUTPUT_DIR: ./test-results
```

### 4.4.2 Vitest (Node.js)

Vitest e um framework de teste moderno e rapido para projetos Vite.

```yaml
- name: Run Vitest
  run: npx vitest run --reporter=junit --outputFile=test-results/junit.xml

- name: Run Vitest with coverage
  run: npx vitest run --coverage
```

### 4.4.3 Mocha (Node.js)

Mocha e um framework de teste flexivel que suporta multiplos reporters.

```yaml
- name: Run Mocha tests
  run: npx mocha --reporter mocha-junit-reporter --reporter-options mochaFile=./test-results/junit.xml
```

### 4.4.4 pytest (Python)

pytest e o framework de teste padrao para Python, com suporte a fixtures, parametrizacao e plugins.

```yaml
- name: Install test dependencies
  run: pip install pytest pytest-cov pytest-xdist

- name: Run tests
  run: pytest --junitxml=test-results/junit.xml --cov=src --cov-report=xml

- name: Run tests in parallel
  run: pytest -n auto --junitxml=test-results/junit.xml
```

### 4.4.5 JUnit (Java)

JUnit e o framework de teste padrao para Java, tipicamente usado com Maven ou Gradle.

```yaml
# Maven
- name: Run JUnit tests
  run: mvn test

# Gradle
- name: Run JUnit tests
  run: ./gradlew test

# Com relatorios
- name: Run tests with reports
  run: mvn test -Dsurefire.reportFormat=xml
```

### 4.4.6 Go test

Go tem um framework de teste integrado na linguagem.

```yaml
- name: Run Go tests
  run: go test -v -race -coverprofile=coverage.out ./...

- name: Generate coverage report
  run: go tool cover -html=coverage.out -o coverage.html
```

### 4.4.7 cargo test (Rust)

Rust usa cargo test que e integrado ao gerenciador de pacotes.

```yaml
- name: Run Rust tests
  run: cargo test --verbose

- name: Run tests with coverage
  run: cargo tarpaulin --out xml
```

### 4.4.8 Tabela de Test Frameworks

| Linguagem | Framework | Comando Basico | Com Coverage | Output XML |
|-----------|-----------|----------------|--------------|------------|
| Node.js | Jest | `jest` | `jest --coverage` | `--reporters=jest-junit` |
| Node.js | Vitest | `vitest run` | `vitest run --coverage` | `--reporter=junit` |
| Node.js | Mocha | `mocha` | `nyc mocha` | `--reporter mocha-junit-reporter` |
| Python | pytest | `pytest` | `pytest --cov=src` | `--junitxml=junit.xml` |
| Java | JUnit | `mvn test` | `mvn test jacoco:report` | `maven-surefire-plugin` |
| Go | go test | `go test ./...` | `go test -cover` | `go test -json` |
| Rust | cargo test | `cargo test` | `cargo tarpaulin` | `--format junit` |

---

## 4.5 Test Reporting (JUnit)

Test reporting e essencial para visualizar resultados de testes na interface do GitHub. O formato JUnit XML e o padrao para relatorios de testes.

### 4.5.1 dorny/test-reporter

O dorny/test-reporter e a action mais popular para publicar resultados de testes no GitHub.

```yaml
- name: Run tests
  run: npm test -- --reporter=junit

- name: Publish test results
  uses: dorny/test-reporter@v1
  if: always()
  with:
    name: Test Results
    path: test-results/*.xml
    reporter: java-junit
    fail-on-error: true
    path-replace-map: '"/github/workspace/" = ""'
    flaky-test-threshold: 3
    fail-on-flaky-test: false
```

### 4.5.2 mikepenz/action-junit-report

Esta action oferece mais opcoes de configuracao e suporta multiplos formatos.

```yaml
- name: Test Summary
  uses: mikepenz/action-junit-report@v4
  if: always()
  with:
    report_paths: 'test-results/*.xml'
    fail_on_failure: true
    require_tests: false
    include_passed: false
    detail_level: 'failures'
    job_name: 'Test Results'
```

### 4.5.3 GitHub Test Reporter

O GitHub tem seu proprio reporter de testes que pode ser usado diretamente.

```yaml
- name: Run tests with GitHub reporter
  run: npm test -- --reporter=@github/test-reporter
  env:
    TEST_REPORTER_PATH: test-results/junit.xml

- name: Publish Test Results
  uses: mikepenz/action-junit-report@v4
  if: always()
  with:
    report_paths: test-results/junit.xml
```

### 4.5.4 Report Customizado

Para necessidades especificas, voce pode criar um reporter customizado.

```yaml
- name: Run tests
  id: tests
  run: |
    npm test -- --reporter=json > test-results/results.json
    if [ $? -eq 0 ]; then
      echo "status=success" >> $GITHUB_OUTPUT
    else
      echo "status=failure" >> $GITHUB_OUTPUT
    fi

- name: Generate test report
  run: |
    node scripts/generate-report.js \
      --input test-results/results.json \
      --output test-results/report.md

- name: Comment PR with test results
  if: github.event_name == 'pull_request'
  uses: marocchino/sticky-pull-request-comment@v2
  with:
    path: test-results/report.md
```

### 4.5.5 Comparacao de Reporters

| Reporter | Suporte | Formatos | Comentarios |
|----------|---------|----------|-------------|
| dorny/test-reporter | Excelente | JUnit, .NET, Mocha | Mais popular, configuravel |
| mikepenz/action-junit-report | Muito bom | JUnit, .NET | Mais recente, ativamente mantido |
| EnricoMi/publish-unit-result | Bom | JUnit | Opcao leve |
| zentered/check-run-reporter | Medio | JSON | Personalizavel |

### 4.5.6 Configuracao Avancada de Reporters

```yaml
- name: Run tests with coverage
  run: |
    npm test -- \
      --reporter=junit \
      --coverage \
      --coverageReporters=lcov \
      --coverageReporters=text-summary
  env:
    JEST_JUNIT_OUTPUT_DIR: ./test-results

- name: Publish test results
  uses: dorny/test-reporter@v1
  if: always()
  with:
    name: Test Results (${{ matrix.node-version }})
    path: test-results/*.xml
    reporter: java-junit
    fail-on-error: true
    flatten: true

- name: Publish coverage
  uses: codecov/codecov-action@v4
  if: always()
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    flags: node${{ matrix.node-version }}
    files: ./coverage/lcov.info
    fail_ci_if_error: false
```

---

## 4.6 Code Coverage (Codecov/Coveralls)

Code coverage mede a porcao de codigo que e exercitada pelos testes. E uma metrica importante para avaliar a completitude dos testes.

### 4.6.1 Codecov

Codecov e o servico de code coverage mais popular para GitHub, com integracao nativa e dashboard detalhado.

Configuracao basica:

```yaml
- name: Run tests with coverage
  run: npm test -- --coverage

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage/lcov.info
    flags: unittests
    name: codecov-umbrella
    fail_ci_if_error: false
    verbose: false
```

Configuracao com matrix:

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage/lcov.info
    flags: node${{ matrix.node-version }}
    name: codecov-${{ matrix.node-version }}
    fail_ci_if_error: false
```

Configuracao com comparacao de branches:

```yaml
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    flags: unittests
    fail_ci_if_error: false
    override_branch: ${{ github.head_ref || github.ref_name }}
    override_commit: ${{ github.sha }}
    override_pr: ${{ github.event.pull_request.number }}
```

### 4.6.2 Coveralls

Coveralls e outra opcao popular com suporte a multiplos idiomas e formatos.

```yaml
- name: Run tests with coverage
  run: npm test -- --coverage

- name: Upload coverage to Coveralls
  uses: coverallsapp/github-action@v2
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    file: coverage/lcov.info
    flag-name: node-${{ matrix.node-version }}
    parallel: true
```

Coveralls com matrix e paralelismo:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage

      - name: Upload coverage
        uses: coverallsapp/github-action@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          flag-name: node-${{ matrix.node-version }}
          parallel: true

  coveralls-finish:
    needs: test
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      - name: Coveralls Finished
        uses: coverallsapp/github-action@v2
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          parallel-finished: true
```

### 4.6.3 Codecov vs Coveralls

| Caracteristica | Codecov | Coveralls |
|----------------|---------|-----------|
| Planos gratuitos | Sim (public repos) | Sim (public repos) |
| Suporte a idiomas | Todos | Todos |
| Integracao GitHub | Excelente | Boa |
| Dashboard | Detalhado | Simples |
| Comentarios em PR | Sim | Sim |
| Comparacao de branches | Sim | Sim |
| Badge | Sim | Sim |
| API | Sim | Sim |
| Configuracao | codecov.yml | .coveralls.yml |

### 4.6.4 Configuracao de Coverage Thresholds

Codecov permite configurar thresholds minimos de coverage que devem ser alcancados.

```yaml
# codecov.yml
coverage:
  status:
    project:
      default:
        target: 80%
        threshold: 1%
    patch:
      default:
        target: 90%
        threshold: 5%

parsers:
  gcov:
    branch_detection:
      conditional: yes
      loop: yes
      method: no
      macro: no

comment:
  layout: "reach,diff,flags,files"
  behavior: default
  require_changes: false
  require_base: false
  require_head: true

ignore:
  - "dist/**"
  - "node_modules/**"
  - "**/*.test.js"
  - "**/*.spec.js"
```

### 4.6.5 Coverage para Multiplos Pacotes

```yaml
jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci

      - name: Test packages/core
        run: |
          cd packages/core
          npm test -- --coverage
          mv coverage/lcov.info ../../coverage-core.lcov

      - name: Test packages/utils
        run: |
          cd packages/utils
          npm test -- --coverage
          mv coverage/lcov.info ../../coverage-utils.lcov

      - name: Merge coverage
        run: |
          npx lcov-merger coverage-core.lcov coverage-utils.lcov > coverage.lcov

      - name: Upload to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.lcov
```

---

## 4.7 Fail-fast

Fail-fast e uma estrategia que cancela todos os jobs em execucao assim que um deles falha. Isso economiza tempo e recursos ao evitar que trabalhos desnecessarios continuem rodando.

### 4.7.1 Fail-fast em Matrix Strategy

```yaml
strategy:
  fail-fast: true  # Default: true
```

Quando fail-fast esta ativo e um job do matrix falha, todos os outros jobs sao cancelados imediatamente. Isso e util quando uma falha em uma plataforma indica um problema que afeta todas as plataformas.

### 4.7.2 Fail-fast Desabilitado

```yaml
strategy:
  fail-fast: false
```

Quando fail-fast esta desabilitado, todos os jobs continuam rodando mesmo que um deles falhe. Isso e util quando voce quer ver todos os resultados, mesmo que alguns tenham falhado.

### 4.7.3 Exemplo Completo com Fail-fast

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

### 4.7.4 Fail-fast com Conditional Jobs

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      fail-fast: true
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test -- --shard=${{ matrix.shard }}/4

  report:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Check test results
        run: |
          if [ "${{ needs.test.result }}" = "failure" ]; then
            echo "One or more test shards failed"
            exit 1
          fi
```

### 4.7.5 Fail-fast com Continue-on-error

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

      # Lint e opcional - nao cancela o job se falhar
      - name: Lint
        continue-on-error: true
        run: npm run lint

      # Test e obrigatorio - cancela o job se falhar
      - name: Test
        run: npm test
```

### 4.7.6 Tabela de Decisao Fail-fast

| Cenario | Fail-fast | Comportamento |
|---------|-----------|---------------|
| Testes unitarios em matrix | true | Cancela todos se um falhar |
| Testes de plataforma | false | Continua para ver quais plataformas falharam |
| Deploy pipeline | true | Cancela tudo se build falhar |
| Nightly build | false | Coleta todos os resultados |
| Pull request CI | true | Rapido feedback ao autor |

---

## 4.8 Conditional Steps

Conditional steps sao steps que so sao executados quando uma determinada condicao e atendida. Eles permitem criar pipelines flexiveis que se adaptam a diferentes situacoes.

### 4.8.1 Condicoes Basicas

```yaml
steps:
  - name: Build
    run: npm run build
    if: success()

  - name: Deploy on success
    run: ./deploy.sh
    if: success()

  - name: Notify on failure
    if: failure()
    run: echo "Build failed!"

  - name: Always run
    if: always()
    run: echo "Cleanup regardless of status"

  - name: If previous step failed
    if: steps.build.outcome == 'failure'
    run: echo "Build failed, running fallback"
```

### 4.8.2 Condicoes Baseadas em Contexto

```yaml
steps:
  - name: Run only on main
    if: github.ref == 'refs/heads/main'
    run: echo "Running on main branch"

  - name: Run only on PR
    if: github.event_name == 'pull_request'
    run: echo "Running on pull request"

  - name: Run only on tag
    if: startsWith(github.ref, 'refs/tags/')
    run: echo "Running on tag"

  - name: Run only on push to main
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    run: echo "Push to main"
```

### 4.8.3 Condicoes Baseadas em Matrix

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, macos-latest, windows-latest]
    node-version: [18, 20, 22]
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

### 4.8.4 Condicoes Baseadas em Secrets

```yaml
steps:
  - name: Run with secret
    if: env.HAVE_SECRET == 'true'
    run: echo "Running with secret"
    env:
      HAVE_SECRET: ${{ secrets.MY_SECRET != '' && 'true' || 'false' }}

  - name: Deploy only if deploy key exists
    if: ${{ env.DEPLOY_KEY != '' }}
    env:
      DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
    run: echo "Deploy key available"
```

### 4.8.5 Condicoes Complexas com Operadores Logicos

```yaml
steps:
  - name: Complex condition
    if: >-
      (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/')) &&
      github.event_name == 'push'
    run: echo "Running on main or tag push"

  - name: Negate condition
    if: "!startsWith(github.ref, 'refs/heads/dependabot/')"
    run: echo "Not a dependabot branch"

  - name: Multiple conditions
    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      !contains(github.event.head_commit.message, '[skip ci]')
    run: echo "Full CI on main push"
```

### 4.8.6 Tabela de Condicoes

| Condicao | Descricao | Exemplo |
|----------|-----------|---------|
| `success()` | Todos os steps anteriores tiveram sucesso | `if: success()` |
| `failure()` | Pelo menos um step anterior falhou | `if: failure()` |
| `always()` | Sempre executa | `if: always()` |
| `cancelled()` | Workflow foi cancelado | `if: cancelled()` |
| `steps.id.outcome` | Resultado de um step especifico | `if: steps.build.outcome == 'success'` |
| `github.ref` | Branch ou tag atual | `if: github.ref == 'refs/heads/main'` |
| `github.event_name` | Tipo de evento | `if: github.event_name == 'push'` |
| `matrix.*` | Valor da matrix atual | `if: matrix.os == 'ubuntu-latest'` |

---

## 4.9 Multi-Language Builds

Multi-language builds sao pipelines que constroem e testam projetos que usam mais de uma linguagem de programacao. Isso e comum em monolitos, monorepos e microsservicos.

### 4.9.1 Pipeline Multi-Linguagem Basico

```yaml
name: Multi-Language CI

on: [push, pull_request]

jobs:
  node:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest

  go:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - run: go test ./...

  rust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
      - run: cargo test
```

### 4.9.2 Monorepo com Multi-Linguagens

```yaml
name: Monorepo CI

on: [push, pull_request]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.changes.outputs.frontend }}
      backend: ${{ steps.changes.outputs.backend }}
      shared: ${{ steps.changes.outputs.shared }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            frontend:
              - 'packages/frontend/**'
            backend:
              - 'packages/backend/**'
            shared:
              - 'packages/shared/**'

  frontend:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true' || needs.detect-changes.outputs.shared == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test --workspace=packages/frontend
      - run: npm run build --workspace=packages/frontend

  backend:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true' || needs.detect-changes.outputs.shared == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r packages/backend/requirements.txt
      - run: pytest packages/backend/tests/
```

### 4.9.3 Full Stack com Multi-Linguagens

```yaml
name: Full Stack CI

on: [push, pull_request]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: npm test
      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: dist/
          retention-days: 1

  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/postgres

  integration:
    needs: [frontend, backend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: dist/
      - run: docker-compose up -d
      - run: npm run test:integration
```

### 4.9.4 Tabela de Configuracao Multi-Language

| Combinacao | Actions Necessarias | Services | Observacao |
|------------|---------------------|----------|------------|
| Node.js + Python | setup-node, setup-python | Nenhum | Comum em ML pipelines |
| Node.js + Go | setup-node, setup-go | Nenhum | Comum em APIs |
| Java + Node.js | setup-java, setup-node | Nenhum | Comum em enterprise |
| Rust + Node.js | rust-toolchain, setup-node | Nenhum | Comum em WASM |
| Python + Java | setup-python, setup-java | PostgreSQL | Comum em data pipelines |

---

## 4.10 CMake Workflow

CMake e um sistema de build multiplataforma amplamente utilizado para projetos C e C++. Um workflow completo de CMake inclui configuracao, compilacao, testes e empacotamento.

### 4.10.1 CMake Basico

```yaml
name: C++ CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ libssl-dev

      - name: Configure
        run: cmake -B build -DCMAKE_BUILD_TYPE=Release

      - name: Build
        run: cmake --build build --parallel $(nproc 2>/dev/null || echo 4)

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 4.10.2 CMake Multi-Platform

```yaml
name: C++ Cross-Platform CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        build_type: [Debug, Release]

    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ libssl-dev

      - name: Install dependencies (macOS)
        if: runner.os == 'macOS'
        run: brew install cmake openssl

      - name: Install dependencies (Windows)
        if: runner.os == 'Windows'
        run: choco install cmake

      - name: Configure
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
            -DCMAKE_CXX_STANDARD=17

      - name: Build
        run: cmake --build build --config ${{ matrix.build_type }}

      - name: Test
        run: ctest --test-dir build --config ${{ matrix.build_type }} --output-on-failure
```

### 4.10.3 CMake com Multi-Compiler

```yaml
name: C++ Multi-Compiler

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        compiler:
          - { cc: gcc-12, cxx: g++-12 }
          - { cc: gcc-13, cxx: g++-13 }
          - { cc: clang-15, cxx: clang++-15 }
          - { cc: clang-16, cxx: clang++-16 }

    steps:
      - uses: actions/checkout@v4

      - name: Install compiler
        run: |
          sudo apt-get update
          sudo apt-get install -y ${{ matrix.compiler.cc }}

      - name: Configure
        env:
          CC: ${{ matrix.compiler.cc }}
          CXX: ${{ matrix.compiler.cxx }}
        run: cmake -B build -DCMAKE_BUILD_TYPE=Release

      - name: Build
        run: cmake --build build --parallel $(nproc)

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 4.10.4 CMake com Coverage

```yaml
name: C++ Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake g++ gcovr

      - name: Configure with coverage
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Debug \
            -DCMAKE_CXX_FLAGS="--coverage -fprofile-arcs -ftest-coverage"

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

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.xml
          fail_ci_if_error: false
```

### 4.10.5 CMake com Conan

```yaml
name: C++ with Conan

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Conan
        run: |
          pip install conan
          conan profile detect --force

      - name: Install dependencies
        run: conan install . --build=missing -of build

      - name: Configure
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake

      - name: Build
        run: cmake --build build --parallel $(nproc)

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 4.10.6 CMake com vcpkg

```yaml
name: C++ with vcpkg

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      VCPKG_ROOT: ${{ github.workspace }}/vcpkg
    steps:
      - uses: actions/checkout@v4

      - name: Setup vcpkg
        run: |
          git clone https://github.com/microsoft/vcpkg.git
          ./vcpkg/bootstrap-vcpkg.sh

      - name: Install dependencies
        run: |
          ./vcpkg/vcpkg install

      - name: Configure
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_TOOLCHAIN_FILE=${{ env.VCPKG_ROOT }}/scripts/buildsystems/vcpkg.cmake

      - name: Build
        run: cmake --build build --parallel $(nproc)

      - name: Test
        run: ctest --test-dir build --output-on-failure
```

### 4.10.7 Tabela de CMake Options

| Option | Tipo | Descricao | Default |
|--------|------|-----------|---------|
| CMAKE_BUILD_TYPE | STRING | Tipo de build | Debug |
| CMAKE_CXX_STANDARD | STRING | Padrao C++ | 17 |
| CMAKE_CXX_FLAGS | STRING | Flags do compilador | - |
| BUILD_TESTING | BOOL | Construir testes | ON |
| CMAKE_INSTALL_PREFIX | PATH | Prefixo de instalacao | /usr/local |

---

## 4.11 Performance Optimization

A otimizacao de performance de pipelines e essencial para reduzir tempo de espera e custos. Existem varias estrategias que podem ser aplicadas.

### 4.11.1 Caching de Dependencias

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      npm-
```

### 4.11.2 Paralelismo de Jobs

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm run typecheck
```

### 4.11.3 Path Filters

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'package-lock.json'
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '.github/ISSUE_TEMPLATE/**'
```

### 4.11.4 Concurrency Groups

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### 4.11.5 Conditional Builds

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check if build needed
        id: check
        run: |
          if git diff --name-only HEAD~1 | grep -q "^src/"; then
            echo "needed=true" >> $GITHUB_OUTPUT
          else
            echo "needed=false" >> $GITHUB_OUTPUT
          fi

      - name: Build
        if: steps.check.outputs.needed == 'true'
        run: npm run build

      - name: Test
        if: steps.check.outputs.needed == 'true'
        run: npm test
```

### 4.11.6 Sharded Tests

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npx jest --shard=${{ matrix.shard }}/4
```

### 4.11.7 Reusable Workflows

```yaml
# .github/workflows/reusable-build.yml
name: Reusable Build

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      build-command:
        required: false
        type: string
        default: 'npm run build'
    secrets:
      npm-token:
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: ${{ inputs.build-command }}
```

### 4.11.8 Tabela de Otimizacao

| Estrategia | Impacto | Complexidade | Quando Usar |
|------------|---------|--------------|-------------|
| Caching | Alto | Baixo | Sempre |
| Path filters | Alto | Baixo | Sempre |
| Concurrency groups | Alto | Baixo | Sempre |
| Paralelismo | Medio | Baixo | Jobs independentes |
| Sharded tests | Alto | Medio | Testes longos |
| Conditional builds | Medio | Baixo | Projetos grandes |
| Reusable workflows | Medio | Medio | Multi-repo |

---

## 4.12 Exemplos de Casos Reais

### 4.12.1 Pipeline para Projeto Full Stack

Este e um exemplo completo de pipeline para um projeto full stack com frontend React, backend Node.js e banco de dados PostgreSQL.

```yaml
name: Full Stack CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  NODE_ENV: test
  CI: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
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
    timeout-minutes: 10
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
    timeout-minutes: 15
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
    timeout-minutes: 15
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
    runs-on: ubuntu-latest
    timeout-minutes: 20
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
      - run: npm run test:frontend -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: frontend-coverage
          path: packages/frontend/coverage/
          retention-days: 7

  test-backend:
    needs: build-backend
    runs-on: ubuntu-latest
    timeout-minutes: 20
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
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
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
      - run: npm run test:backend -- --coverage
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-coverage
          path: packages/backend/coverage/
          retention-days: 7

  test-integration:
    needs: [build-frontend, build-backend]
    runs-on: ubuntu-latest
    timeout-minutes: 30
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
    runs-on: ubuntu-latest
    timeout-minutes: 45
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
          name: e2e-logs
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
          # Deploy logic here
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
```

### 4.12.2 Pipeline para Biblioteca npm

Pipeline completo para publicar uma biblioteca npm com testes em multiplos ambientes.

```yaml
name: npm Library CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

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

  test:
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
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: matrix.os == 'ubuntu-latest' && matrix.node-version == 20
        with:
          name: coverage
          path: coverage/
          retention-days: 7

  build:
    needs: [lint, test]
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
          retention-days: 7

  typecheck:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - run: npm run typecheck

  publish:
    needs: [build, typecheck]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Publish to npm
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  coverage:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: coverage
          path: coverage/
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage/lcov.info
          flags: unittests
          fail_ci_if_error: false
```

### 4.12.3 Pipeline para CLI Tool

Pipeline para ferramenta de linha de comando com cross-compilacao e testes.

```yaml
name: CLI Tool CI

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
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - run: go test -v -race -coverprofile=coverage.out ./...
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage.out
          fail_ci_if_error: false

  build:
    needs: [lint, test]
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            goos: linux
            goarch: amd64
            suffix: ''
          - os: ubuntu-latest
            goos: linux
            goarch: arm64
            suffix: ''
          - os: macos-latest
            goos: darwin
            goarch: arm64
            suffix: ''
          - os: windows-latest
            goos: windows
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
            artifacts/myapp-linux-amd64/myapp-linux-amd64
            artifacts/myapp-linux-arm64/myapp-linux-arm64
            artifacts/myapp-darwin-arm64/myapp-darwin-arm64
            artifacts/myapp-windows-amd64/myapp-windows-amd64.exe
```

### 4.12.4 Pipeline para Python Package

Pipeline completa para pacote Python com testes em multiplos Python versions.

```yaml
name: Python Package CI

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
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']
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
    needs: [lint, test]
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

### 4.12.5 Pipeline para Microservicos

Pipeline para arquitetura de microservicos com build e deploy independente.

```yaml
name: Microservices CI

on: [push, pull_request]

jobs:
  detect-services:
    runs-on: ubuntu-latest
    outputs:
      api-gateway: ${{ steps.changes.outputs.api-gateway }}
      user-service: ${{ steps.changes.outputs.user-service }}
      order-service: ${{ steps.changes.outputs.order-service }}
      notification-service: ${{ steps.changes.outputs.notification-service }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            api-gateway:
              - 'services/api-gateway/**'
            user-service:
              - 'services/user-service/**'
            order-service:
              - 'services/order-service/**'
            notification-service:
              - 'services/notification-service/**'

  api-gateway:
    needs: detect-services
    if: needs.detect-services.outputs.api-gateway == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
        working-directory: services/api-gateway
      - run: npm test
        working-directory: services/api-gateway
      - run: npm run build
        working-directory: services/api-gateway
      - uses: actions/upload-artifact@v4
        with:
          name: api-gateway-dist
          path: services/api-gateway/dist/
          retention-days: 1

  user-service:
    needs: detect-services
    if: needs.detect-services.outputs.user-service == 'true'
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r services/user-service/requirements.txt
      - run: pytest services/user-service/tests/
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/postgres

  order-service:
    needs: detect-services
    if: needs.detect-services.outputs.order-service == 'true'
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true
      - run: go test ./...
        working-directory: services/order-service
      - run: go build -o bin/order-service ./cmd/order-service
        working-directory: services/order-service

  notification-service:
    needs: detect-services
    if: needs.detect-services.outputs.notification-service == 'true'
    runs-on: ubuntu-latest
    services:
      rabbitmq:
        image: rabbitmq:3
        ports:
          - 5672:5672
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'
      - run: mvn test
        working-directory: services/notification-service
      - run: mvn package -DskipTests
        working-directory: services/notification-service

  integration-test:
    needs: [api-gateway, user-service, order-service, notification-service]
    if: always() && !contains(needs.*.result, 'failure')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build all services
        run: |
          docker-compose build
      - name: Start all services
        run: |
          docker-compose up -d
          sleep 60
      - name: Run integration tests
        run: |
          npm run test:integration
      - name: Collect logs
        if: failure()
        run: |
          docker-compose logs > integration-logs.txt
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: integration-logs
          path: integration-logs.txt
          retention-days: 7
      - name: Stop services
        if: always()
        run: docker-compose down
```

---

## 4.13 Exercicios

1. Crie um pipeline CI que teste em Node.js 18, 20 e 22 com matrix build
2. Configure code coverage com Codecov e publique resultados em PRs
3. Implemente conditional deploy que so rode em pushes para main
4. Crie um matrix build multi-OS com continue-on-error no Windows
5. Configure test reporting com dorny/test-reporter
6. Implemente fail-fast em matrix build para cancelar jobs rapido
7. Configure conditional steps baseados em contexto de evento
8. Crie um pipeline multi-language com Node.js e Python
9. Implemente CMake workflow para projeto C++ multi-plataforma
10. Otimize pipeline com caching, path filters e concurrency groups

---

## 4.13 Referencias

1. https://docs.github.com/en/actions/automating-builds-and-tests
2. https://docs.github.com/en/actions/learn-github-actions/expressions#success
3. https://github.com/codecov/codecov-action
4. https://github.com/dorny/test-reporter
5. https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
6. https://github.com/mikepenz/action-junit-report
7. https://github.com/coverallsapp/github-action
8. https://cmake.org/cmake/help/latest/guide/tutorial/
9. https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
10. https://docs.github.com/en/actions/learn-github-actions/expressions
