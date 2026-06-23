---
layout: default
title: "07-caching-performance"
---

# Capitulo 7 — Caching e Performance

> *"Tempo de build e tempo de dinheiro. Otimize cada segundo."*

---

## Sumario

| Secao | Descricao |
|-------|-----------|
| 7.1 | actions/cache |
| 7.2 | Language-specific Caching |
| 7.3 | Docker Layer Caching |
| 7.4 | Dependabot |
| 7.5 | Security Updates |
| 7.6 | Workflow Optimization |
| 7.7 | Artifact Retention |
| 7.8 | Concurrency Groups |
| 7.9 | Cost Monitoring |

---

## Objetivos de Aprendizado

1. Configurar caching com actions/cache para diferentes tipos de dependencias
2. Implementar cache por linguagem (Node.js, Python, Go, Rust, Java)
3. Usar Docker layer caching para acelerar builds de containers
4. Configurar Dependabot para atualizacoes automaticas de dependencias
5. Implementar security updates para manter dependencias seguras
6. Otimizar workflows para performance e custo
7. Gerenciar retention de artifacts para economizar armazenamento
8. Configurar concurrency groups para evitar workflows duplicados
9. Monitorar custos de GitHub Actions
10. Implementar estrategias de otimizacao avancadas

---

## 7.1 actions/cache

O action actions/cache e o mecanismo fundamental de caching do GitHub Actions. Ele permite armazenar e recuperar dependencias entre execucoes de workflows.

### 7.1.1 Configuracao Basica

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      npm-
```

### 7.1.2 Key Strategy

A estrategia de chaves define como o cache e identificado e recuperado.

| Key | Quando Usar | Exemplo |
|-----|-------------|---------|
| `deps-${{ hashFiles('lock') }}` | Cache por hash do lockfile | npm, pip, composer |
| `os-deps-${{ hashFiles('lock') }}` | Por OS + lockfile | Projetos com diferencas por OS |
| `node${{ matrix.node }}-deps` | Por versao + lockfile | Matrix builds |
| `build-${{ github.sha }}` | Por commit especifico | Builds unicos |
| `cache-${{ runner.os }}-${{ hashFiles('lock') }}` | Por OS + hash | Cross-platform |

### 7.1.3 Restore Keys

Restore keys permitem recuperar caches parciais quando o cache exato nao existe.

```yaml
restore-keys: |
  npm-${{ hashFiles('package-lock.json') }}   # Exato
  npm-node20-                                   # Prefixo node 20
  npm-                                          # Qualquer cache npm
```

### 7.1.4 Cache Multi-Path

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      ~/.cache/node_modules
      node_modules/
    key: npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      npm-${{ runner.os }}-
```

### 7.1.5 Cache com Condicoes

```yaml
- uses: actions/cache@v4
  if: matrix.os == 'ubuntu-latest'
  with:
    path: ~/.npm
    key: npm-${{ hashFiles('package-lock.json') }}
```

### 7.1.6 Tabela de Estrategias de Cache

| Estrategia | Precisao | Hit Rate | Observacao |
|------------|----------|----------|------------|
| Hash do lockfile | Alta | Media | Padrao recomendada |
| Hash do lockfile + OS | Alta | Baixa | Cross-platform |
| Hash do lockfile + versao | Media | Alta | Matrix builds |
| Branch + hash | Media | Media | Branches diferentes |
| Commit hash | Baixa | Muito baixa | Builds unicos |

---

## 7.2 Language-specific Caching

Cada linguagem de programacao tem suas proprias estrategias de caching integradas nas setup actions.

### 7.2.1 Node.js (actions/setup-node)

O setup-node ja inclui caching integrado para npm, yarn e pnpm.

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'npm'
```

Cache para yarn:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'yarn'
```

Cache para pnpm:

```yaml
- uses: actions/setup-node@v4
  with:
    node-version: '20'
    cache: 'pnpm'
```

Cache manual para npm:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.npm
    key: npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      npm-${{ runner.os }}-
```

### 7.2.2 Python (actions/setup-python)

O setup-python suporta caching para pip, pipenv e poetry.

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'pip'
```

Cache para poetry:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'
    cache: 'poetry'
```

Cache manual para pip:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      pip-${{ runner.os }}-
```

Cache para virtualenv:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: pip-${{ runner.os }}-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      pip-${{ runner.os }}-

- run: pip install -r requirements.txt
```

### 7.2.3 Java (actions/setup-java)

O setup-java suporta caching para Maven e Gradle.

```yaml
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'temurin'
    cache: 'maven'
```

Cache para Gradle:

```yaml
- uses: actions/setup-java@v4
  with:
    java-version: '21'
    distribution: 'temurin'
    cache: 'gradle'
```

Cache manual para Maven:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.m2/repository
    key: maven-${{ runner.os }}-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      maven-${{ runner.os }}-
```

Cache manual para Gradle:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.gradle/caches
      ~/.gradle/wrapper
    key: gradle-${{ runner.os }}-${{ hashFiles('**/*.gradle*', '**/gradle-wrapper.properties') }}
    restore-keys: |
      gradle-${{ runner.os }}-
```

### 7.2.4 Go (actions/setup-go)

O setup-go ja inclui caching integrado para modulos e builds.

```yaml
- uses: actions/setup-go@v5
  with:
    go-version: '1.22'
    cache: true
```

Cache manual para Go:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/go/pkg/mod
      ~/.cache/go-build
    key: go-${{ runner.os }}-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      go-${{ runner.os }}-
```

### 7.2.5 Rust (Swatinem/rust-cache)

O Rust nao tem caching integrado, mas o Swatinem/rust-cache e a solucao padrao.

```yaml
- uses: Swatinem/rust-cache@v2
  with:
    cache-targets: true
    cache-on-failure: true
```

Cache manual para Rust:

```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.cargo/bin/
      ~/.cargo/registry/index/
      ~/.cargo/registry/cache/
      ~/.cargo/git/db/
      target/
    key: rust-${{ runner.os }}-${{ hashFiles('**/Cargo.lock') }}
    restore-keys: |
      rust-${{ runner.os }}-
```

### 7.2.6 .NET (actions/setup-dotnet)

```yaml
- uses: actions/setup-dotnet@v4
  with:
    dotnet-version: '8.0.x'
    cache: true
```

Cache manual para .NET:

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.nuget/packages
    key: nuget-${{ runner.os }}-${{ hashFiles('**/*.csproj') }}
    restore-keys: |
      nuget-${{ runner.os }}-
```

### 7.2.7 Ruby (ruby/setup-ruby)

```yaml
- uses: ruby/setup-ruby@v1
  with:
    ruby-version: '3.3'
    bundler-cache: true
```

### 7.2.8 PHP (shivammathur/setup-php)

```yaml
- uses: shivammathur/setup-php@v2
  with:
    php-version: '8.3'
    tools: composer:v2
    coverage: none
```

Cache manual para Composer:

```yaml
- uses: actions/cache@v4
  with:
    path: vendor
    key: composer-${{ hashFiles('**/composer.lock') }}
    restore-keys: |
      composer-
```

### 7.2.9 Tabela de Cache por Linguagem

| Linguagem | Action | Cache Built-in | Caminho do Cache | Chave Padrao |
|-----------|--------|----------------|------------------|--------------|
| Node.js | actions/setup-node@v4 | npm, yarn, pnpm | ~/.npm | package-lock.json hash |
| Python | actions/setup-python@v5 | pip, pipenv, poetry | ~/.cache/pip | requirements.txt hash |
| Java | actions/setup-java@v4 | maven, gradle | ~/.m2/repository | pom.xml hash |
| Go | actions/setup-go@v5 | modules, build | ~/go/pkg/mod | go.sum hash |
| Rust | Swatinem/rust-cache@v2 | targets | target/ | Cargo.lock hash |
| .NET | actions/setup-dotnet@v4 | NuGet | ~/.nuget/packages | *.csproj hash |
| Ruby | ruby/setup-ruby@v1 | Bundler | vendor/bundle | Gemfile.lock hash |
| PHP | shivammathur/setup-php@v2 | Composer | vendor/ | composer.lock hash |

---

## 7.3 Docker Layer Caching

Docker layer caching permite reutilizar camadas de imagens Docker entre builds, reduzindo significativamente o tempo de build.

### 7.3.1 GitHub Actions Cache (GHA)

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: myapp:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 7.3.2 Registry Caching

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: ghcr.io/myorg/myapp:latest
    cache-from: type=registry,ref=ghcr.io/myorg/myapp:cache
    cache-to: type=registry,ref=ghcr.io/myorg/myapp:cache,mode=max
```

### 7.3.3 Local Caching

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: myapp:latest
    cache-from: type=local,src=/tmp/.buildx-cache
    cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
```

### 7.3.4 Docker Layer Caching Completo

```yaml
name: Docker Build with Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha
            type=ref,event=branch

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

### 7.3.5 Docker com Multi-Stage Build

```dockerfile
# Dockerfile com multi-stage build
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### 7.3.6 Tabela de Docker Cache Types

| Tipo | Descricao | Vantagens | Desvantagens |
|------|-----------|-----------|--------------|
| GHA | GitHub Actions cache | Rapido, integrado | Limite de 10GB |
| Registry | Cache no registry | Compartilhavel | Mais lento |
| Local | Cache local | Simples | Nao compartilhavel |
| Inline | Embed na imagem | Simples | Aumenta tamanho |

---

## 7.4 Dependabot

Dependabot e um servico do GitHub que monitors dependencias e cria pull requests automaticos para atualizacoes.

### 7.4.1 Dependabot Config

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "team-security"
    labels:
      - "dependencies"
      - "automated"
    groups:
      dev-dependencies:
        dependency-type: "development"
      production-dependencies:
        dependency-type: "production"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      actions:
        patterns: ["*"]

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "composer"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 7.4.2 Dependabot Security Updates

Configurado automaticamente pelo GitHub para vulnerabilidades conhecidas.

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 5
    labels:
      - "security"
      - "dependencies"
```

### 7.4.3 Dependabot com Auto-merge

```yaml
name: Dependabot Auto-merge

on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Fetch Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge minor and patch updates
        if: steps.metadata.outputs.update-type == 'version-update:semver-minor' || steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 7.4.4 Dependabot com Notification

```yaml
name: Dependabot Notifications

on: pull_request

jobs:
  notify:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "New Dependabot PR: ${{ github.event.pull_request.title }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 7.5 Security Updates

Security updates sao atualizacoes automaticas para corrigir vulnerabilidades de seguranca.

### 7.5.1 GitHub Security Advisories

O GitHub monitora automaticamente dependencias e cria security updates quando vulnerabilidades sao descobertas.

### 7.5.2 Security Updates com Dependabot

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    labels:
      - "security"
    groups:
      security-updates:
        patterns: ["*"]
        update-types:
          - "security"
```

### 7.5.3 Security Scanning com CodeQL

```yaml
name: CodeQL Security Scanning

on: [push, pull_request, schedule]

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'python', 'java']
    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
```

### 7.5.4 Security Scanning com Trivy

```yaml
name: Trivy Security Scanning

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## 7.6 Workflow Optimization

Otimizacao de workflows envolve reduzir tempo de build, custo e complexidade.

### 7.6.1 Minimize Job Time

```yaml
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

      - name: Check if build needed
        id: check
        run: |
          if git diff --name-only HEAD~1 | grep -q "^src/"; then
            echo "changed=true" >> $GITHUB_OUTPUT
          else
            echo "changed=false" >> $GITHUB_OUTPUT
          fi

      - name: Build
        if: steps.check.outputs.changed == 'true'
        run: npm run build
```

### 7.6.2 Parallel Jobs

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

### 7.6.3 Path Filters

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

### 7.6.4 Conditional Steps

```yaml
steps:
  - name: Build
    run: npm run build
    if: success()

  - name: Test
    run: npm test
    if: success()

  - name: Deploy
    if: github.ref == 'refs/heads/main' && success()
    run: ./deploy.sh
```

### 7.6.5 Tabela de Otimizacao

| Estrategia | Impacto | Complexidade | Quando Usar |
|------------|---------|--------------|-------------|
| Caching | Alto | Baixo | Sempre |
| Path filters | Alto | Baixo | Sempre |
| Concurrency groups | Alto | Baixo | Sempre |
| Parallel jobs | Medio | Baixo | Jobs independentes |
| Conditional steps | Medio | Baixo | Quando necessario |
| Sharded tests | Alto | Medio | Testes longos |

---

## 7.7 Artifact Retention

Artifact retention define por quanto tempo artifacts sao mantidos antes de serem deletados automaticamente.

### 7.7.1 Retention Basico

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/
    retention-days: 30
```

### 7.7.2 Retention por Tipo

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: logs
    path: logs/
    retention-days: 1  # Manter apenas 1 dia

- uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/
    retention-days: 7  # Manter 1 semana

- uses: actions/upload-artifact@v4
  with:
    name: release
    path: dist/
    retention-days: 90  # Manter 3 meses
```

### 7.7.3 Delete Manual

```yaml
- name: Delete old artifacts
  uses: geekyeggo/delete-artifact@v5
  with:
    name: build-*
    retention-days: 7
```

### 7.7.4 Tabela de Retention

| Tipo de Artifact | Dias Recomendados | Observacao |
|------------------|-------------------|------------|
| Logs | 1-3 | Apenas para debug |
| Test results | 7 | Para analise pos-build |
| Build artifacts | 7-30 | Para deploy |
| Release artifacts | 30-90 | Para distribuicao |
| Coverage reports | 30 | Para historico |
| Security scans | 90 | Para compliance |

---

## 7.8 Concurrency Groups

Concurrency groups permitem controlar execucoes simultaneas de workflows.

### 7.8.1 Cancelar Workflows Anteriores

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### 7.8.2 Aguardar, Nao Cancelar

```yaml
concurrency:
  group: deploy-${{ github.event.inputs.environment }}
  cancel-in-progress: false
```

### 7.8.3 Concurrency por Branch

```yaml
concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

### 7.8.4 Concurrency por Environment

```yaml
concurrency:
  group: deploy-${{ github.event.inputs.environment }}
  cancel-in-progress: false
```

### 7.8.5 Tabela de Concurrency

| Cenario | cancel-in-progress | Observacao |
|---------|-------------------|------------|
| CI basico | true | Cancelar duplicates |
| Deploy | false | Aguardar fila |
| Nightly build | false | Manter todos |
| PR check | true | Rapido feedback |

---

## 7.9 Cost Monitoring

Monitoramento de custos e essencial para evitar surpresas na fatura do GitHub Actions.

### 7.9.1 GitHub Actions Billing API

```yaml
- name: Check minutes used
  run: |
    curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
      https://api.github.com/repos/${{ github.repository }}/actions/workflows \
      | jq '.total_count'
```

### 7.9.2 Cost Optimization Checklist

| Acao | Impacto | Reducao Estimada |
|------|---------|------------------|
| Cache de dependencias | Alto | -50% tempo |
| Concurrency groups | Alto | -30% duplicatas |
| Path filters | Alto | -40% builds desnecessarios |
| fail-fast: true | Medio | -10% tempo |
| max-parallel | Medio | -20% custo |
| Self-hosted runners | Alto | -80% custo para projetos grandes |
| Ubuntu vs macOS/Windows | Alto | -50-90% custo |

### 7.9.3 Monitor de Custo

```yaml
name: Cost Monitor

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Get billing info
        run: |
          echo "## GitHub Actions Billing" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Repository: ${{ github.repository }}" >> $GITHUB_STEP_SUMMARY
          echo "Date: $(date)" >> $GITHUB_STEP_SUMMARY

      - name: Notify if high usage
        if: steps.billing.outputs.minutes > 1000
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "High GitHub Actions usage: ${{ steps.billing.outputs.minutes }} minutes"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 7.9.4 Tabela de Custos por Runner

| Runner | Custo por Minuto | Custo por Hora | Observacao |
|--------|------------------|----------------|------------|
| ubuntu-latest | $0.008 | $0.48 | Mais barato |
| macos-13 | $0.08 | $4.80 | 10x ubuntu |
| macos-14 | $0.12 | $7.20 | Apple Silicon |
| windows-latest | $0.016 | $0.96 | 2x ubuntu |

### 7.9.5 Estrategias de Reducao de Custo

| Estrategia | Reducao | Implementacao |
|------------|---------|---------------|
| Usar ubuntu | 50-90% | Evitar macOS/Windows desnecessarios |
| Caching | 30-50% | Configurar cache por linguagem |
| Path filters | 40-60% | Evitar builds em mudancas de docs |
| Concurrency groups | 20-40% | Cancelar workflows anteriores |
| fail-fast | 10-30% | Cancelar rapido em falha |
| max-parallel | 20-40% | Limitar jobs simultaneos |
| Self-hosted runners | 50-80% | Para projetos grandes |

---

## 7.10 Exemplos de Casos Reais

### 7.10.1 Pipeline Otimizada Completa

```yaml
name: Optimized CI

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
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

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

  typecheck:
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

  test:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
          retention-days: 7

  build:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 15
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

### 7.10.2 Pipeline com Docker Cache

```yaml
name: Docker Optimized CI

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha
            type=ref,event=branch

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

---

## 7.11 Exemplos Avancados de Caching

### 7.11.1 Cache Compartilhado entre Workflows

```yaml
name: Shared Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/cache@v4
        id: cache-deps
        with:
          path: |
            ~/.npm
            node_modules/
          key: deps-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            deps-${{ runner.os }}-

      - name: Install dependencies
        if: steps.cache-deps.outputs.cache-hit != 'true'
        run: npm ci

      - run: npm run build
```

### 7.11.2 Cache com Invalidacao Manual

```yaml
name: Cache with Manual Invalidation

on:
  workflow_dispatch:
    inputs:
      invalidate_cache:
        description: 'Invalidate cache'
        required: false
        type: boolean
        default: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/cache@v4
        id: cache-deps
        with:
          path: ~/.npm
          key: npm-${{ hashFiles('package-lock.json') }}
          enableCrossOsArchive: true

      - name: Install dependencies
        if: steps.cache-deps.outputs.cache-hit != 'true' || inputs.invalidate_cache
        run: npm ci

      - run: npm run build
```

### 7.11.3 Cache Multi-Stage

```yaml
name: Multi-Stage Cache

on: [push, pull_request]

jobs:
  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/cache/save@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}

  build:
    needs: dependencies
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache/restore@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache/restore@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - run: npm test
```

### 7.11.4 Cache com Condicoes Complexas

```yaml
name: Conditional Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Cache npm
        uses: actions/cache@v4
        if: hashFiles('package-lock.json') != ''
        with:
          path: ~/.npm
          key: npm-${{ hashFiles('package-lock.json') }}
          restore-keys: |
            npm-

      - name: Cache pip
        uses: actions/cache@v4
        if: hashFiles('requirements.txt') != ''
        with:
          path: ~/.cache/pip
          key: pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            pip-

      - run: npm ci
```

---

## 7.12 Exemplos Avancados de Docker Layer Caching

### 7.12.1 Docker com Build Args e Cache

```yaml
name: Docker Advanced Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate cache key
        id: cache-key
        run: |
          echo "key=build-${{ runner.os }}-${{ hashFiles('Dockerfile', 'package-lock.json') }}" >> $GITHUB_OUTPUT

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha,scope=${{ steps.cache-key.outputs.key }}
          cache-to: type=gha,scope=${{ steps.cache-key.outputs.key }},mode=max
          build-args: |
            NODE_VERSION=20
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}
```

### 7.12.2 Docker com Multi-Registry Cache

```yaml
name: Docker Multi-Registry Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ${{ secrets.DOCKERHUB_USERNAME }}/myapp:${{ github.sha }}
          cache-from: |
            type=gha
            type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/myapp:cache
          cache-to: |
            type=gha,mode=max
            type=registry,ref=${{ secrets.DOCKERHUB_USERNAME }}/myapp:cache,mode=max
```

### 7.12.3 Docker com Cleanup de Cache

```yaml
name: Docker Cache Cleanup

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Cleanup old cache
        uses: actions/github-script@v7
        with:
          script: |
            const caches = await github.rest.actions.getActionsCacheList({
              owner: context.repo.owner,
              repo: context.repo.repo,
              key: 'buildx-',
              sort: 'last_accessed_at',
              direction: 'asc'
            });

            for (const cache of caches.data.actions_caches) {
              if (cache.last_accessed_at < new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)) {
                await github.rest.actions.deleteActionsCacheById({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  cache_id: cache.id
                });
              }
            }
```

---

## 7.13 Exemplos de Dependabot Avancado

### 7.13.1 Dependabot com Auto-merge para Updates Seguras

```yaml
name: Dependabot Auto-merge

on: pull_request

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    steps:
      - name: Fetch Dependabot metadata
        id: metadata
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge patch updates
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Approve minor updates
        if: steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr review --approve "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Notify for major updates
        if: steps.metadata.outputs.update-type == 'version-update:semver-major'
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Major update required: ${{ steps.metadata.outputs.dependency-name }} ${{ steps.metadata.outputs.previous-version }} -> ${{ steps.metadata.outputs.new-version }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 7.13.2 Dependabot com Grouping

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      typescript:
        patterns:
          - "typescript"
          - "@types/*"
      testing:
        patterns:
          - "jest"
          - "@jest/*"
          - "ts-jest"
          - "jest-*"
      linting:
        patterns:
          - "eslint"
          - "prettier"
          - "eslint-*"
          - "@typescript-eslint/*"
      react:
        patterns:
          - "react"
          - "react-dom"
          - "@types/react*"
      build:
        patterns:
          - "webpack"
          - "ts-loader"
          - "css-loader"
          - "style-loader"
```

### 7.13.3 Dependabot com Schedule Personalizado

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Sao_Paulo"
    open-pull-requests-limit: 10

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "friday"
      time: "17:00"
      timezone: "America/Sao_Paulo"
```

---

## 7.14 Exemplos de Security Updates

### 7.14.1 Security Scanning Completo

```yaml
name: Security Scanning

on: [push, pull_request, schedule]

jobs:
  codeql:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'python']
    steps:
      - uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"

  trivy:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy filesystem scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-fs-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy filesystem scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-fs-results.sarif'

  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: critical
```

### 7.14.2 Security Scanning com Container

```yaml
name: Container Security Scanning

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: myapp:test

      - name: Run Trivy container scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: myapp:test
          format: 'sarif'
          output: 'trivy-container-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload container scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-container-results.sarif'
          category: 'container-scan'
```

---

## 7.15 Exemplos de Workflow Optimization

### 7.15.1 Pipeline Otimizada Completa

```yaml
name: Fully Optimized CI

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
      - '.github/workflows/docs-*.yml'
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

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

  typecheck:
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

  test:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
          retention-days: 7

  build:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 15
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

  deploy-preview:
    needs: build
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Deploy preview
        run: |
          echo "Deploying preview for PR #${{ github.event.pull_request.number }}"

  deploy-production:
    needs: [build, coverage]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - name: Deploy to production
        run: |
          echo "Deploying to production"
```

---

## 7.16 Exemplos de Artifact Retention

### 7.16.1 Retention por Tipo de Artifact

```yaml
name: Artifact Retention

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: build-logs
          path: build-logs/
          retention-days: 1

      - uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: test-results/
          retention-days: 7

      - uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/
          retention-days: 30

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 90
```

### 7.16.2 Cleanup de Artifacts

```yaml
name: Cleanup Old Artifacts

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Delete old artifacts
        uses: actions/github-script@v7
        with:
          script: |
            const artifacts = await github.rest.actions.listWorkflowArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo
            });

            for (const artifact of artifacts.data.artifacts) {
              const daysSinceCreation = (Date.now() - new Date(artifact.created_at).getTime()) / (1000 * 60 * 60 * 24);

              if (daysSinceCreation > 30) {
                await github.rest.actions.deleteArtifact({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  artifact_id: artifact.id
                });
              }
            }
```

---

## 7.17 Exemplos de Concurrency Groups

### 7.17.1 Concurrency Basico

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### 7.17.2 Concurrency por Branch

```yaml
concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true
```

### 7.17.3 Concurrency por Environment

```yaml
concurrency:
  group: deploy-${{ github.event.inputs.environment }}
  cancel-in-progress: false
```

### 7.17.4 Concurrency com Multiple Groups

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

---

## 7.18 Exemplos de Cost Monitoring

### 7.18.1 Cost Monitor Basico

```yaml
name: Cost Monitor

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Get billing info
        run: |
          echo "## GitHub Actions Billing" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Repository: ${{ github.repository }}" >> $GITHUB_STEP_SUMMARY
          echo "Date: $(date)" >> $GITHUB_STEP_SUMMARY
```

### 7.18.2 Cost Report com Slack

```yaml
name: Cost Report

on:
  schedule:
    - cron: '0 0 * * 1'  # Toda segunda-feira

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - name: Generate report
        run: |
          echo "Weekly GitHub Actions Cost Report" > report.txt
          echo "Repository: ${{ github.repository }}" >> report.txt
          echo "Date: $(date)" >> report.txt

      - name: Send to Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Weekly GitHub Actions Cost Report for ${{ github.repository }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 7.19 Tabela Comparativa de Estrategias de Caching

| Estrategia | Precisao | Hit Rate | Complexidade | Uso Recomendado |
|------------|----------|----------|--------------|-----------------|
| Hash do lockfile | Alta | Media | Baixa | Projetos com gerenciador de pacotes |
| Hash do lockfile + OS | Alta | Baixa | Baixa | Cross-platform |
| Hash do lockfile + versao | Media | Alta | Media | Matrix builds |
| Branch + hash | Media | Media | Baixa | Branches diferentes |
| Commit hash | Baixa | Muito baixa | Baixa | Builds unicos |
| Docker GHA | Alta | Alta | Media | Docker builds |
| Docker Registry | Alta | Media | Media | Docker builds compartilhados |
| Docker Local | Media | Alta | Baixa | Builds locais |

---

## 7.20 Fluxo de Decisao de Caching

```
                    ┌─────────────┐
                    │   Precisa   │
                    │ de cache?   │
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
       │ Que tipo?   │          │ Sem cache    │
       └──────┬──────┘          └──────────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼───┐ ┌──▼──┐ ┌───▼───┐
│Depen- │ │Docker│ │Outro  │
│dencias│ │Layer │ │       │
│       │ │      │ │       │
│Setup  │ │Build │ │Custom │
│action │ │Push  │ │cache  │
└───────┘ └─────┘ └───────┘
```

---

## 7.21 Checklist de Performance

### 7.21.1 Checklist de Caching

| Item | Verificado |
|------|------------|
| Cache de dependencias configurado | [ ] |
| Docker layer caching ativo | [ ] |
| Cache key com hash do lockfile | [ ] |
| Restore keys configurados | [ ] |
| Cache compartilhado entre jobs | [ ] |
| Cache invalidado quando necessario | [ ] |
| Retention de artifacts definida | [ ] |
| Cleanup de cache antigo | [ ] |

### 7.21.2 Checklist de Otimizacao

| Item | Verificado |
|------|------------|
| Path filters ativos | [ ] |
| Concurrency groups configurados | [ ] |
| Timeout definido para jobs | [ ] |
| fail-fast configurado | [ ] |
| max-parallel definido | [ ] |
| Jobs paralelos quando possivel | [ ] |
| Conditional steps implementados | [ ] |
| Custo monitorado | [ ] |

---

## 7.22 Glossario de Caching e Performance

| Termo | Definicao |
|-------|-----------|
| Cache | Armazenamento temporario para reutilizacao |
| Cache hit | Quando o cache e encontrado |
| Cache miss | Quando o cache nao e encontrado |
| Cache key | Identificador unico do cache |
| Restore key | Chave alternativa para recuperar cache |
| Lockfile | Arquivo com versoes exatas de dependencias |
| Layer caching | Caching de camadas de imagem Docker |
| GHA cache | GitHub Actions cache (type=gha) |
| Registry cache | Cache em registry de containers |
| Concurrency group | Grupo para controlar execucoes simultaneas |
| Path filter | Filtro para evitar builds por arquivos |
| Artifact | Arquivo compartilhado entre jobs |
| Retention | Tempo de vida de um artifact |
| Cost monitoring | Monitoramento de custos de build |

---

## 7.23 Referencias

1. https://docs.github.com/en/actions/using-workflows/caching-dependencies-to-speed-up-workflows
2. https://github.com/actions/cache
3. https://github.com/dependabot/dependabot-core
4. https://github.com/docker/build-push-action#caching
5. https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions
6. https://github.com/Swatinem/rust-cache
7. https://github.com/codecov/codecov-action
8. https://github.com/github/codeql-action
9. https://github.com/aquasecurity/trivy-action
10. https://github.com/geekyeggo/delete-artifact
11. https://github.com/dependabot/fetch-metadata
12. https://github.com/actions/dependency-review-action
13. https://github.com/docker/metadata-action
14. https://github.com/docker/login-action
15. https://github.com/docker/setup-buildx-action

---

## 7.24 Exercicios

1. Configure cache para dependencias npm com key baseada em package-lock.json
2. Implemente Docker layer caching com GitHub Actions cache
3. Configure Dependabot para atualizar npm e GitHub Actions semanalmente
4. Adicione path filters para evitar builds em mudancas de docs
5. Implemente concurrency group que cancele workflows anteriores
6. Configure retention de artifacts para 1 dia para logs e 90 dias para releases
7. Implemente cost monitor para verificar uso de minutos
8. Configure security scanning com CodeQL
9. Implemente auto-merge para Dependabot PRs
10. Otimize pipeline com todas as estrategias de caching
11. Configure cache multi-stage para builds complexos
12. Implemente cache compartilhado entre workflows
13. Configure Docker multi-registry cache
14. Implemente cleanup automatico de cache antigo
15. Configure Dependabot com grouping para pacotes relacionados

---

## 7.25 Fluxo de Trabalho Recomendado

### 7.25.1 Para Projetos Novos

1. Comece com cache basico de dependencias
2. Adicione Docker layer caching
3. Configure Dependabot para atualizacoes
4. Implemente path filters
5. Configure concurrency groups

### 7.25.2 Para Projetos Existentes

1. Audite cache atual
2. Identifique oportunidades de otimizacao
3. Implemente caching por linguagem
4. Configure security scanning
5. Implemente cost monitoring

### 7.25.3 Para Monorepos

1. Configure cache compartilhado
2. Implemente path filters por pacote
3. Configure concurrency groups por servico
4. Implemente cleanup automatico
5. Monitore custos por pacote

---

## 7.26 Metricas de Performance

### 7.26.1 Metricas Importantes

| Metrica | Descricao | Meta |
|---------|-----------|------|
| Cache hit rate | Porcentagem de cache hits | > 80% |
| Tempo medio de build | Duracao media dos jobs | < 10 minutos |
| Custo por build | Minutos consumidos por build | < 50 minutos |
| Tempo de feedback | Tempo ate primeiro resultado | < 5 minutos |
| Taxa de atualizacao | Dependencias atualizadas | > 90% |
| Vulnerabilidades | Numero de vulnerabilidades | 0 criticas |

### 7.26.2 Dashboard de Performance

```yaml
name: Performance Dashboard

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  dashboard:
    runs-on: ubuntu-latest
    steps:
      - name: Generate dashboard
        run: |
          echo "## Performance Dashboard" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Cache Hit Rate | ${{ steps.cache.outputs.hit-rate }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Average Build Time | ${{ steps.build.outputs.avg-time }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Cost per Build | ${{ steps.cost.outputs.per-build }} |" >> $GITHUB_STEP_SUMMARY
```

---

## 7.27 Tabela de Decisao de Performance

| Cenario | Recomendacao | Prioridade |
|---------|--------------|------------|
| Builds lentos | Caching + parallel jobs | Alta |
| Custo alto | Path filters + concurrency groups | Alta |
| Dependencias desatualizadas | Dependabot | Media |
| Vulnerabilidades | Security scanning | Alta |
| Cache miss frequente | Melhorar cache key | Media |
| Docker builds lentos | Layer caching | Alta |
| Workflows duplicados | Concurrency groups | Media |
| Artifacts acumulando | Retention policies | Baixa |

---

## 7.28 Melhores Praticas

### 7.28.1 Regras de Ouro

| Regra | Descricao | Prioridade |
|-------|-----------|------------|
| Sempre usar caching | Caching reduz tempo significativamente | Alta |
| Usar path filters | Evitar builds desnecessarios | Alta |
| Configurar concurrency groups | Cancelar workflows anteriores | Alta |
| Monitorar custos | Evitar surpresas na fatura | Alta |
| Usar security scanning | Manter dependencias seguras | Alta |
| Configurar Dependabot | Atualizacoes automaticas | Media |
| Definir retention policies | Economizar armazenamento | Media |
| Usar timeout | Evitar jobs presos | Media |

### 7.28.2 Anti-Patterns

| Anti-Pattern | Problema | Solucao |
|--------------|----------|---------|
| Sem cache | Builds lentos | Configurar cache |
| Cache key muito generica | Cache invalido | Usar hash do lockfile |
| Sem path filters | Builds desnecessarios | Configurar path filters |
| Sem concurrency groups | Workflows duplicados | Configurar concurrency |
| Sem timeout | Jobs presos | Definir timeout |
| Sem security scanning | Vulnerabilidades | Configurar CodeQL/Trivy |
| Sem cost monitoring | Custos inesperados | Implementar monitoring |

---

## 7.29 Exemplos de Cenarios

### 7.29.1 Cenario: Startup com Poucos Recursos

```yaml
name: Startup CI

on: [push, pull_request]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

### 7.29.2 Cenario: Empresa Grande

```yaml
name: Enterprise CI

on: [push, pull_request]

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

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

  test:
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

  security:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
```

---

## 7.30 Resumo Final

Caching e performance sao aspectos criticos de pipelines de CI/CD. Use as estrategias deste capitulo para:

1. **Reduzir tempo de build**: Caching de dependencias e Docker layers
2. **Economizar custos**: Path filters e concurrency groups
3. **Manter seguranca**: Dependabot e security scanning
4. **Monitorar uso**: Cost monitoring e dashboards
5. **Limpar recursos**: Retention policies e cleanup automatico

Lembre-se: otimizacao e um processo continuo. Revise e ajuste regularmente suas estrategias de performance.

---

## 7.31 Exemplos de Casos Reais Detalhados

### 7.31.1 Pipeline Full Stack Otimizada

Pipeline completa para aplicacao full stack com todas as otimizacoes de performance.

```yaml
name: Full Stack Optimized CI

on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'package-lock.json'
      - 'Dockerfile'
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '.github/ISSUE_TEMPLATE/**'
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

env:
  NODE_VERSION: '20'
  DOCKER_BUILDKIT: 1

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run prettier:check

  typecheck:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run typecheck

  test-unit:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-coverage
          path: coverage/
          retention-days: 7

  test-integration:
    needs: [lint, typecheck]
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
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

  build:
    needs: [test-unit, test-integration]
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1

  docker:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha
            type=ref,event=branch

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  coverage:
    needs: [test-unit]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: unit-coverage
          path: coverage/
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage/lcov.info
          flags: unittests
          fail_ci_if_error: false

  security:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  deploy-preview:
    needs: [docker, coverage, security]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy preview
        run: |
          echo "Deploying preview for PR #${{ github.event.pull_request.number }}"

  deploy-production:
    needs: [docker, coverage, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: |
          echo "Deploying to production"
```

### 7.31.2 Pipeline Monorepo Otimizada

Pipeline para monorepo com cache compartilhado e otimizacoes especificas.

```yaml
name: Monorepo Optimized CI

on:
  push:
    paths:
      - 'packages/**'
      - 'package.json'
      - 'package-lock.json'
  pull_request:
    paths:
      - 'packages/**'

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

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

  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - uses: actions/cache/save@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}

  frontend:
    needs: [detect-changes, dependencies]
    if: needs.detect-changes.outputs.frontend == 'true' || needs.detect-changes.outputs.shared == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache/restore@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npm run test --workspace=packages/frontend
      - run: npm run build --workspace=packages/frontend

  backend:
    needs: [detect-changes, dependencies]
    if: needs.detect-changes.outputs.backend == 'true' || needs.detect-changes.outputs.shared == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache/restore@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npm run test --workspace=packages/backend
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/postgres
      - run: npm run build --workspace=packages/backend

  integration:
    needs: [frontend, backend]
    if: always() && !contains(needs.*.result, 'failure')
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/cache/restore@v4
        with:
          path: node_modules/
          key: node-modules-${{ runner.os }}-${{ hashFiles('package-lock.json') }}
      - run: npm run test:integration
```

### 7.31.3 Pipeline Rust Otimizada

Pipeline completa para projeto Rust com caching avancado.

```yaml
name: Rust Optimized CI

on: [push, pull_request]

concurrency:
  group: ci-${{ github.head_ref || github.ref }}
  cancel-in-progress: true

jobs:
  fmt:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt
      - run: cargo fmt --check

  clippy:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy
      - uses: Swatinem/rust-cache@v2
        with:
          cache-on-failure: true
      - run: cargo clippy -- -D warnings

  test:
    needs: [fmt, clippy]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: Swatinem/rust-cache@v2
        with:
          cache-on-failure: true
      - run: cargo test --verbose
      - run: cargo test --verbose --release

  build:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      matrix:
        target:
          - x86_64-unknown-linux-gnu
          - x86_64-unknown-linux-musl
          - aarch64-unknown-linux-gnu
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          targets: ${{ matrix.target }}
      - uses: Swatinem/rust-cache@v2
        with:
          key: ${{ matrix.target }}
      - run: cargo build --release --target ${{ matrix.target }}
      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.target }}
          path: target/${{ matrix.target }}/release/myapp
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

## 7.32 Tabela de Decisao Final

| Cenario | Estrategia Recomendada | Prioridade | Impacto |
|---------|------------------------|------------|---------|
| Startup com poucos recursos | Caching basico + concurrency | Alta | Alto |
| Empresa grande | Cache completo + security + monitoring | Alta | Muito alto |
| Monorepo | Cache compartilhado + path filters | Alta | Alto |
| Projeto Rust | Swatinem/rust-cache + targets | Media | Alto |
| Docker heavy | Layer caching + multi-stage | Alta | Muito alto |
| Multi-OS | Path filters + max-parallel | Media | Medio |
| Multi-language | Caching por linguagem + parallel | Alta | Alto |
| Projeto legado | Dependabot + security scanning | Media | Medio |

---

## 7.33 Fluxo de Otimizacao Continua

```
                    ┌─────────────┐
                    │  Medir      │
                    │ Performance │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Identificar│
                    │ Gargalos    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Implementar│
                    │ Otimizacao  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Validar    │
                    │ Resultado   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Documentar │
                    │ Aprendizado │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Repetir    │
                    │ Ciclo       │
                    └─────────────┘
```

---

## 7.34 Checklist Final de Performance

| Item | Verificado | Observacao |
|------|------------|------------|
| Cache de dependencias | [ ] | Configurar para todas as linguagens |
| Docker layer caching | [ ] | Usar GHA ou registry cache |
| Path filters | [ ] | Evitar builds em docs/md |
| Concurrency groups | [ ] | Cancelar workflows anteriores |
| Timeout definido | [ ] | Evitar jobs presos |
| fail-fast configurado | [ ] | Cancelar rapido em falha |
| max-parallel definido | [ ] | Limitar jobs simultaneos |
| Security scanning | [ ] | CodeQL ou Trivy |
| Dependabot | [ ] | Atualizacoes automaticas |
| Cost monitoring | [ ] | Monitorar uso de minutos |
| Retention policies | [ ] | Definir tempo de vida dos artifacts |
| Cleanup automatico | [ ] | Remover artifacts antigos |
| Dashboard de metrics | [ ] | Visualizar performance |
| Documentacao | [ ] | Registrar decisoes |

---

## 7.35 Resumo Completo

### 7.35.1 Pontos Principais

1. **Caching e fundamental**: Sempre configure cache para dependencias
2. **Docker layer caching reduz tempo**: Use GHA ou registry cache
3. **Dependabot mantem atualizado**: Configure para todas as linguagens
4. **Security scanning e obrigatorio**: Use CodeQL e Trivy
5. **Path filters economizam**: Evite builds desnecessarios
6. **Concurrency groups evitam duplicatas**: Cancel workflows anteriores
7. **Cost monitoring e essencial**: Monitore uso de minutos
8. **Retention policies economizam**: Defina tempo de vida dos artifacts

### 7.35.2 Proximos Passos

1. Implementar caching em todos os projetos
2. Configurar Dependabot
3. Implementar security scanning
4. Configurar cost monitoring
5. Documentar otimizacoes realizadas
6. Revisar e ajustar regularmente

### 7.35.3 Recursos Adicionais

| Recurso | URL | Descricao |
|---------|-----|-----------|
| GitHub Actions Docs | docs.github.com/actions | Documentacao oficial |
| Actions Marketplace | github.com/marketplace?type=actions | Actions populares |
| Dependabot Docs | docs.github.com/code-security/dependabot | Documentacao Dependabot |
| CodeQL Docs | docs.github.com/code-security/codeql | Documentacao CodeQL |
| Trivy Docs | trivy.dev | Documentacao Trivy |
---

*[Capítulo anterior: 06 — Matrix Builds](06-matrix-builds.md)*
*[Próximo capítulo: 08 — Artifacts Outputs](08-artifacts-outputs.md)*
