---
layout: default
title: "14-monorepos"
---

# Capitulo 14 -- Monorepos com GitHub Actions

> *"Um repositorio, multiplos projetos, um pipeline otimizado."*

---

## Objetivos de Aprendizado

1. Entender os desafios especificos de monorepos no GitHub Actions
2. Configurar path filters para triggers seletivos
3. Implementar changed files detection com dorny/paths-filter
4. Integrar Turborepo com GitHub Actions
5. Integrar Nx com GitHub Actions
6. Implementar deploys independentes por package
7. Criar shared workflows para packages comuns
8. Configurar shared cache entre packages
9. Implementar matrix builds por package
10. Montar um exemplo completo de monorepo CI/CD
11. Aplicar boas praticas para monorepos em producao
12. Gerenciar dependencias entre packages
13. Configurar versionamento semver para monorepos
14. Implementar mudanca seletiva com base em diffs
15. Otimizar custos com builds condicionais

---

## 14.1 Desafios de Monorepos

### O Que e um Monorepo

Um monorepo e uma estrutura de repositorio onde multiplos projetos, pacotes ou servicos vivem juntos no mesmo repositorio Git. Ao contrario do polyrepo (onde cada projeto tem seu proprio repositorio), o monorepo centraliza tudo.

### Estrutura Tipica

```
my-monorepo/
  packages/
    core/
      src/
      package.json
      tsconfig.json
    api/
      src/
      package.json
      tsconfig.json
    web/
      src/
      package.json
      tsconfig.json
    shared/
      src/
      package.json
      tsconfig.json
  tools/
    scripts/
    configs/
  docs/
  package.json
  turbo.json
  .github/
    workflows/
```

### Principais Desafios

1. **Builds seletivos**: Nao faz sentido rebuildar todos os packages quando apenas um muda
2. **Cache compartilhado**: Packages compartilham dependencias e devem compartilhar caches
3. **Deploys independentes**: Cada package pode ter seu ciclo de deploy proprio
4. **Dependencias complexas**: Packages podem depender uns dos outros em grafo aciclico direcionado (DAG)
5. **Matrix de testes**: Cada package pode ter requisitos de teste diferentes
6. **Versionamento**: Estrategia de versionamento pode ser unificada ou independente
7. **Notifications**: Alertas devem ser direcionados ao time responsavel pelo package afetado
8. **Linting e formatacao**: Regras podem variar entre packages

### Impacto no CI/CD

Sem otimizacao, um monorepo pode gerar centenas de workflows desnecessarios a cada push. Um repositorio com 50 packages pode acionar 50 builds mesmo que apenas um arquivo de documentacao tenha mudado. Isso consome minutos de runner, aumenta custos e devolve feedback mais lento.

```yaml
# EXEMPLO: Pior caso - build completo sem otimizacao
# Esse workflow roda TODOS os jobs SEMPRE, mesmo para mudancas em docs

name: Bad Monorepo CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-core:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/core && npm ci && npm run build

  build-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/api && npm ci && npm run build

  build-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/web && npm ci && npm run build

  build-shared:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/shared && npm ci && npm run build

  build-tools:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd tools && npm ci && npm run build

# RESULTADO: 5 jobs rodam SEMPRE, mesmo para mudancas em docs/
# Custo estimado: ~5 minutos de runner por push
```

### Abordagens de Solucao

| Abordagem | Ferramenta | Complexidade | Beneficio |
|-----------|------------|--------------|-----------|
| Path filters nativos | on.push.paths | Baixa | Evita triggers em paths irrelevantes |
| Changed files detection | dorny/paths-filter | Media | Detecta exatamente o que mudou |
| Build orchestration | Turborepo / Nx | Alta | Build seletivo com cache inteligente |
| Reusable workflows | workflow_call | Media | Jobs compartilhados entre packages |
| Matrix dinamica | fromJSON + outputs | Media | Testa apenas packages afetados |

---

## 14.2 Path Filters

### Como Funcionam

Path filters sao uma feature nativa do GitHub Actions que permite definir quais paths devem acionar um workflow. Se nenhuma mudanca foi feita nos paths especificados, o workflow nao executa.

### Sintaxe Basica

```yaml
name: Path Filtered CI

on:
  push:
    branches: [main]
    paths:
      - 'packages/core/**'
      - 'packages/api/**'
      - 'package.json'
      - 'turbo.json'
  pull_request:
    branches: [main]
    paths:
      - 'packages/core/**'
      - 'packages/api/**'
```

### paths vs paths-ignore

```yaml
# USANDO paths - workflow roda APENAS quando esses paths mudam
on:
  push:
    paths:
      - 'packages/core/**'
      - 'packages/api/**'
      - 'packages/shared/**'
      - 'package.json'
      - 'turbo.json'
      - 'pnpm-lock.yaml'

# USANDO paths-ignore - workflow roda EXCETO quando esses paths mudam
on:
  push:
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '.github/ISSUE_TEMPLATE/**'
      - 'LICENSE'
      - '.gitignore'
```

### Padroes Glob

```yaml
on:
  push:
    paths:
      # Todos os arquivos .ts em packages/core
      - 'packages/core/**/*.ts'

      # Todos os arquivos em packages/api exceto testes
      - 'packages/api/src/**'
      - '!packages/api/src/**/*.test.ts'
      - '!packages/api/src/**/*.spec.ts'

      # Arquivos de configuracao raiz
      - 'package.json'
      - 'tsconfig.json'
      - 'turbo.json'

      # Lock files
      - 'pnpm-lock.yaml'
      - 'package-lock.json'
      - 'yarn.lock'
```

### Multi-Path com OR Logico

```yaml
# Workflow roda se QUALQUER um dos paths mudar
on:
  push:
    paths:
      - 'packages/**'
      - 'tools/**'
      - 'package.json'
      - 'turbo.json'
```

### Limitacoes dos Path Filters

1. Path filters so funcionam com `push` e `pull_request` (e `pull_request_target`)
2. Nao funcionam com `workflow_dispatch`, `schedule`, `release`
3. Path filters avaliam a DIFF entre o commit anterior e o atual
4. Para PRs, compara com a branch base
5. Para pushes, compara com o commit anterior

### Exemplo com Multiplos Workflows

```yaml
# .github/workflows/ci-core.yml
name: CI Core

on:
  push:
    paths:
      - 'packages/core/**'
      - 'packages/shared/**'
      - 'package.json'
      - 'turbo.json'
  pull_request:
    paths:
      - 'packages/core/**'
      - 'packages/shared/**'

concurrency:
  group: ci-core-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/core test
      - run: pnpm --filter @myorg/core build
```

```yaml
# .github/workflows/ci-api.yml
name: CI API

on:
  push:
    paths:
      - 'packages/api/**'
      - 'packages/shared/**'
      - 'package.json'
      - 'turbo.json'
  pull_request:
    paths:
      - 'packages/api/**'
      - 'packages/shared/**'

concurrency:
  group: ci-api-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
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
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/api test
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/testdb
      - run: pnpm --filter @myorg/api build
```

---

## 14.3 Changed Files Detection

### dorny/paths-filter

A action `dorny/paths-filter` oferece deteccao avancada de arquivos alterados. Diferente dos path filters nativos, ela permite usar os resultados como outputs para decisoes condicionais em jobs posteriores.

### Configuracao Basica

```yaml
name: Changed Files Detection

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      core: ${{ steps.filter.outputs.core }}
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      shared: ${{ steps.filter.outputs.shared }}
      tools: ${{ steps.filter.outputs.tools }}
      docs: ${{ steps.filter.outputs.docs }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect changed files
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'
            shared:
              - 'packages/shared/**'
            tools:
              - 'tools/**'
            docs:
              - 'docs/**'
              - '**.md'
```

### Outputs Condicionais

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      core: ${{ steps.filter.outputs.core }}
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
    steps:
      - uses: actions/checkout@v4
      - name: Detect changes
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

  test-core:
    needs: detect-changes
    if: needs.detect-changes.outputs.core == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/core && npm ci && npm test

  test-api:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/api && npm ci && npm test

  test-web:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/web && npm ci && npm test
```

### Filtros com Exclusao

```yaml
- name: Detect changes
  uses: dorny/paths-filter@v3
  id: filter
  with:
    filters: |
      core:
        - 'packages/core/src/**'
        - 'packages/core/package.json'
        - 'packages/shared/src/**'
        - '!packages/core/src/**/*.test.ts'
        - '!packages/core/src/**/*.spec.ts'
      api:
        - 'packages/api/src/**'
        - 'packages/api/package.json'
        - 'packages/shared/src/**'
        - '!packages/api/src/**/*.test.ts'
```

### change-files como Outputs JSON

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.changes.outputs.changes }}
    steps:
      - uses: actions/checkout@v4

      - name: Get changed files
        id: changed-files
        uses: tj-actions/changed-files@v45

      - name: Determine changed packages
        id: changes
        run: |
          CHANGED_FILES="${{ steps.changed-files.outputs.all_changed_files }}"
          PACKAGES="[]"

          if echo "$CHANGED_FILES" | grep -q "^packages/core/"; then
            PACKAGES=$(echo "$PACKAGES" | jq -c '. + ["core"]')
          fi
          if echo "$CHANGED_FILES" | grep -q "^packages/api/"; then
            PACKAGES=$(echo "$PACKAGES" | jq -c '. + ["api"]')
          fi
          if echo "$CHANGED_FILES" | grep -q "^packages/web/"; then
            PACKAGES=$(echo "$PACKAGES" | jq -c '. + ["web"]')
          fi

          echo "changes=$PACKAGES" >> "$GITHUB_OUTPUT"
          echo "Changed packages: $PACKAGES"

  test:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJSON(needs.detect-changes.outputs.packages) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/${{ matrix.package }} && npm ci && npm test
```

### Monodir (Alternativa Leve)

```yaml
jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      core: ${{ steps.check.outputs.core }}
      api: ${{ steps.check.outputs.api }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check changes using git diff
        id: check
        run: |
          BASE_SHA=${{ github.event.pull_request.base.sha || github.event.before }}
          CURRENT_SHA=${{ github.sha }}

          # Verificar se packages/core foi alterado
          if git diff --name-only "$BASE_SHA" "$CURRENT_SHA" | grep -q "^packages/core/"; then
            echo "core=true" >> "$GITHUB_OUTPUT"
          else
            echo "core=false" >> "$GITHUB_OUTPUT"
          fi

          # Verificar se packages/api foi alterado
          if git diff --name-only "$BASE_SHA" "$CURRENT_SHA" | grep -q "^packages/api/"; then
            echo "api=true" >> "$GITHUB_OUTPUT"
          else
            echo "api=false" >> "$GITHUB_OUTPUT"
          fi
```

### Comparacao de Abordagens

| Ferramenta | Vantagens | Desvantagens |
|------------|-----------|--------------|
| on.push.paths | Nativo, simples | So filtra triggers, nao retorna outputs |
| dorny/paths-filter | Outputs por package, suporte a glob | Dependencia externa |
| tj-actions/changed-files | Lista todos os arquivos | Mais verboso |
| git diff manual | Sem dependencia | Mais codigo, propenso a erros |

---

## 14.4 Turborepo Integration

### O Que e Turborepo

Turborepo e um sistema de build que otimiza monorepos com cache inteligente e execucao paralela. Ele entende o grafo de dependencias entre packages e so rebuilda o que realmente mudou.

### Configuracao Basica

```json
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": []
    },
    "lint": {
      "outputs": []
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "typecheck": {
      "dependsOn": ["^build"],
      "outputs": []
    }
  }
}
```

### GitHub Actions com Turborepo - Basico

```yaml
name: Turborepo CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm turbo build

      - name: Test
        run: pnpm turbo test
```

### Turborepo com Cache Remoto

```yaml
name: Turborepo CI with Remote Cache

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
  TURBO_TEAM: ${{ secrets.TURBO_TEAM }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build with remote cache
        run: pnpm turbo build --remote-only

      - name: Test
        run: pnpm turbo test
```

### Turborepo com Filter

```yaml
name: Turborepo Selective Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect changes
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJSON(needs.detect-changes.outputs.packages) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build package and dependencies
        run: pnpm turbo build --filter=@myorg/${{ matrix.package }}...

      - name: Test package
        run: pnpm turbo test --filter=@myorg/${{ matrix.package }}
```

### Turborepo com Outputs de Cache

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      turbo-hash: ${{ steps.turborepo.outputs.turbo-hash }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build with Turborepo
        id: turborepo
        run: |
          pnpm turbo build --dry-run --json | jq -r '.[0].hash' > turbo-hash.txt
          echo "turbo-hash=$(cat turbo-hash.txt)" >> "$GITHUB_OUTPUT"

      - name: Cache Turbo outputs
        uses: actions/cache@v4
        with:
          path: |
            packages/*/dist
            node_modules/.cache/turbo
          key: turbo-${{ runner.os }}-${{ steps.turborepo.outputs.turbo-hash }}
          restore-keys: |
            turbo-${{ runner.os }}-
```

### Turborepo com Summary

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build and generate summary
        run: |
          pnpm turbo build --summarize > turbo-summary.txt
          echo "## Turborepo Build Summary" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          cat turbo-summary.txt >> "$GITHUB_STEP_SUMMARY"
```

---

## 14.5 Nx Integration

### O Que e Nx

Nx e uma ferramenta de build para monorepos que fornece cache inteligente, execucao paralela, e analise de dependencias. Ele suporta multiplos frameworks (React, Angular, Node, etc.) e linguagens.

### Configuracao Basica

```json
// nx.json
{
  "$schema": "./node_modules/nx/schemas/nx-schema.json",
  "targetDefaults": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["production", "^production"]
    },
    "test": {
      "inputs": ["default", "^production"]
    },
    "lint": {
      "inputs": ["default", "{workspaceRoot}/.eslintrc.json"]
    }
  },
  "namedInputs": {
    "default": ["{projectRoot}/**/*", "sharedGlobals"],
    "sharedGlobals": [],
    "production": [
      "default",
      "!{projectRoot}/**/?(*.)+(spec|test).[jt]s?(x)?(.snap)",
      "!{projectRoot}/tsconfig.spec.json",
      "!{projectRoot}/.eslintrc.json"
    ]
  },
  "tasksRunnerOptions": {
    "default": {
      "runner": "nx-cloud",
      "options": {
        "cacheableOperations": ["build", "test", "lint"],
        "accessToken": "${NX_CLOUD_ACCESS_TOKEN}"
      }
    }
  }
}
```

### GitHub Actions com Nx - Basico

```yaml
name: Nx CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  NX_CLOUD_ACCESS_TOKEN: ${{ secrets.NX_CLOUD_ACCESS_TOKEN }}

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Affected build
        run: npx nx affected --target=build --parallel=3

      - name: Affected test
        run: npx nx affected --target=test --parallel=3 --configuration=ci
```

### Nx com Deteccao de Projetos Afetados

```yaml
name: Nx Affected Projects

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  affected:
    runs-on: ubuntu-latest
    outputs:
      projects: ${{ steps.affected.outputs.projects }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Get affected projects
        id: affected
        run: |
          PROJECTS=$(npx nx print-affected --target=build --type=app | jq -c '.projects')
          echo "projects=$PROJECTS" >> "$GITHUB_OUTPUT"

  build:
    needs: affected
    if: needs.affected.outputs.projects != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: ${{ fromJSON(needs.affected.outputs.projects) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build project
        run: npx nx build ${{ matrix.project }}

      - name: Test project
        run: npx nx test ${{ matrix.project }}
```

### Nx com Cloud

```yaml
name: Nx Cloud CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  NX_CLOUD_DISTRIBUTED_EXECUTION: true
  NX_CLOUD_DISTRIBUTED_EXECUTION_AGENT_COUNT: 3
  NX_CLOUD_ACCESS_TOKEN: ${{ secrets.NX_CLOUD_ACCESS_TOKEN }}

jobs:
  main:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Run affected commands
        run: |
          npx nx affected --target=lint --parallel=3
          npx nx affected --target=test --parallel=3 --configuration=ci
          npx nx affected --target=build --parallel=3

      - name: Stop Nx Cloud agents
        if: always()
        run: npx nx cloud stop-all-agents
```

### Nx com Matrix por Projeto

```yaml
name: Nx Matrix Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  list-projects:
    runs-on: ubuntu-latest
    outputs:
      apps: ${{ steps.list.outputs.apps }}
      libs: ${{ steps.list.outputs.libs }}
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: List affected apps
        id: list
        run: |
          APPS=$(npx nx show projects --type=app | jq -R -s -c 'split("\n") | map(select(length > 0))')
          LIBS=$(npx nx show projects --type=lib | jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "apps=$APPS" >> "$GITHUB_OUTPUT"
          echo "libs=$LIBS" >> "$GITHUB_OUTPUT"

  test-apps:
    needs: list-projects
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: ${{ fromJSON(needs.list-projects.outputs.apps) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Build and test
        run: |
          npx nx build ${{ matrix.project }}
          npx nx test ${{ matrix.project }}

  test-libs:
    needs: list-projects
    runs-on: ubuntu-latest
    strategy:
      matrix:
        project: ${{ fromJSON(needs.list-projects.outputs.libs) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Test library
        run: npx nx test ${{ matrix.project }}
```

---

## 14.6 Deploys Independentes

### Conceito

Deploys independentes significam que cada package do monorepo pode ser implantado sem afetar os outros. Isso e util quando packages tem ciclos de vida diferentes (ex: uma lib core que muda raramente vs uma API que muda frequentemente).

### Deploy por Package com Conditions

```yaml
name: Independent Deploys

on:
  push:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      worker: ${{ steps.filter.outputs.worker }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'
            worker:
              - 'packages/worker/**'

  deploy-api:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    environment: production-api
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/api && npm ci && npm run build
      - name: Deploy API
        run: |
          echo "Deploying API to production"
          # aws s3 sync packages/api/dist s3://api-bucket
          # or: vercel deploy --prod packages/api

  deploy-web:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    environment: production-web
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/web && npm ci && npm run build
      - name: Deploy Web
        run: |
          echo "Deploying Web to production"
          # netlify deploy --dir=packages/web/dist --prod

  deploy-worker:
    needs: detect-changes
    if: needs.detect-changes.outputs.worker == 'true'
    runs-on: ubuntu-latest
    environment: production-worker
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/worker && npm ci && npm run build
      - name: Deploy Worker
        run: |
          echo "Deploying Worker to production"
          # wrangler deploy packages/worker/src/index.ts
```

### Deploy com Matrix Dinamica

```yaml
name: Matrix Deploy

on:
  push:
    branches: [main]

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      deployables: ${{ steps.filter.outputs.deployables }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect deployable packages
        id: filter
        uses: dorny/paths-filter@v3
        with:
          list-files: json
          filters: |
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

      - name: Build deployable list
        run: |
          DEPLOYABLES="[]"
          if [ "${{ steps.filter.outputs.api }}" == "true" ]; then
            DEPLOYABLES=$(echo "$DEPLOYABLES" | jq -c '. + ["api"]')
          fi
          if [ "${{ steps.filter.outputs.web }}" == "true" ]; then
            DEPLOYABLES=$(echo "$DEPLOYABLES" | jq -c '. + ["web"]')
          fi
          echo "deployables=$DEPLOYABLES" >> "$GITHUB_OUTPUT"

  deploy:
    needs: detect
    if: needs.detect.outputs.deployables != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJSON(needs.detect.outputs.deployables) }}
      max-parallel: 1
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Deploy package
        run: |
          echo "Deploying ${{ matrix.package }}"
          cd packages/${{ matrix.package }}
          npm ci
          npm run build
          echo "Deploy complete for ${{ matrix.package }}"
```

### Deploy com Environment Protection Rules

```yaml
name: Deploy with Protection

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [api, web, worker]
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/${{ matrix.package }} && npm ci && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    strategy:
      matrix:
        package: [api, web, worker]
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-${{ matrix.package }}
          path: dist

      - name: Deploy to staging
        run: |
          echo "Deploying ${{ matrix.package }} to staging"
          ls -la dist/

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    strategy:
      matrix:
        package: [api, web, worker]
      max-parallel: 1
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-${{ matrix.package }}
          path: dist

      - name: Deploy to production
        run: |
          echo "Deploying ${{ matrix.package }} to production"
          ls -la dist/
```

### Deploy com Rollback

```yaml
name: Deploy with Rollback

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      - name: Get version
        id: version
        run: echo "version=$(jq -r .version package.json)" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [api, web]
    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: cd packages/${{ matrix.package }} && npm ci && npm run build

      - name: Deploy
        id: deploy
        run: |
          echo "Deploying ${{ matrix.package }} v${{ needs.build.outputs.version }}"
          echo "deploy_id=deploy-$(date +%s)" >> "$GITHUB_OUTPUT"

      - name: Health check
        id: healthcheck
        run: |
          echo "Running health check for ${{ matrix.package }}"
          sleep 5
          echo "healthy=true" >> "$GITHUB_OUTPUT"

      - name: Rollback on failure
        if: failure() && steps.deploy.outputs.deploy_id
        run: |
          echo "Rolling back ${{ matrix.package }} deployment"
          echo "Rolling back deploy: ${{ steps.deploy.outputs.deploy_id }}"
```

---

## 14.7 Shared Workflows

### Conceito

Shared workflows no contexto de monorepos sao workflows reutilizaveis que podem ser chamados por multiplos packages. Isso evita duplicacao de configuracao e facilita manutencao.

### Reusable Test Workflow

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

on:
  workflow_call:
    inputs:
      package:
        required: true
        type: string
      node-version:
        required: false
        type: string
        default: '20'
      test-command:
        required: false
        type: string
        default: 'npm test'
      needs-database:
        required: false
        type: boolean
        default: false
    secrets:
      DATABASE_URL:
        required: false

jobs:
  test:
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
        if: ${{ inputs.needs-database }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: cd packages/${{ inputs.package }} && npm ci

      - name: Run tests
        run: cd packages/${{ inputs.package }} && ${{ inputs.test-command }}
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL || 'postgresql://postgres:test@localhost:5432/testdb' }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ inputs.package }}
          path: packages/${{ inputs.package }}/coverage/
          retention-days: 7
```

### Reusable Build Workflow

```yaml
# .github/workflows/reusable-build.yml
name: Reusable Build

on:
  workflow_call:
    inputs:
      package:
        required: true
        type: string
      node-version:
        required: false
        type: string
        default: '20'
      build-command:
        required: false
        type: string
        default: 'npm run build'
      upload-artifact:
        required: false
        type: boolean
        default: false
    outputs:
      dist-path:
        description: "Caminho do output do build"
        value: ${{ jobs.build.outputs.dist-path }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      dist-path: ${{ steps.build.outputs.dist-path }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: cd packages/${{ inputs.package }} && npm ci

      - name: Build
        id: build
        run: |
          cd packages/${{ inputs.package }}
          ${{ inputs.build-command }}
          echo "dist-path=packages/${{ inputs.package }}/dist" >> "$GITHUB_OUTPUT"

      - name: Upload artifact
        if: inputs.upload-artifact
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ inputs.package }}
          path: packages/${{ inputs.package }}/dist
          retention-days: 7
```

### Reusable Deploy Workflow

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      package:
        required: true
        type: string
      environment:
        required: true
        type: string
      artifact-name:
        required: false
        type: string
        default: ''
    secrets:
      DEPLOY_TOKEN:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Download artifact
        if: inputs.artifact-name != ''
        uses: actions/download-artifact@v4
        with:
          name: ${{ inputs.artifact-name }}
          path: dist

      - name: Deploy
        run: |
          echo "Deploying ${{ inputs.package }} to ${{ inputs.environment }}"
          echo "Token provided: ${{ secrets.DEPLOY_TOKEN != '' }}"
```

### Caller Workflows

```yaml
# .github/workflows/ci-api.yml
name: CI API

on:
  push:
    paths:
      - 'packages/api/**'
  pull_request:
    paths:
      - 'packages/api/**'

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      package: api
      needs-database: true
    secrets:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}

  build:
    needs: test
    uses: ./.github/workflows/reusable-build.yml
    with:
      package: api
      upload-artifact: true
```

```yaml
# .github/workflows/ci-web.yml
name: CI Web

on:
  push:
    paths:
      - 'packages/web/**'
  pull_request:
    paths:
      - 'packages/web/**'

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      package: web

  build:
    needs: test
    uses: ./.github/workflows/reusable-build.yml
    with:
      package: web
      upload-artifact: true
```

```yaml
# .github/workflows/deploy-production.yml
name: Deploy Production

on:
  push:
    branches: [main]
    paths:
      - 'packages/api/**'
      - 'packages/web/**'

jobs:
  deploy-api:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      package: api
      environment: production
      artifact-name: build-api
    secrets:
      DEPLOY_TOKEN: ${{ secrets.API_DEPLOY_TOKEN }}

  deploy-web:
    needs: deploy-api
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      package: web
      environment: production
      artifact-name: build-web
    secrets:
      DEPLOY_TOKEN: ${{ secrets.WEB_DEPLOY_TOKEN }}
```

### Reusable Workflow com Multiplos Secrets

```yaml
# .github/workflows/reusable-multi-secret.yml
name: Reusable Multi-Secret

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      AWS_ACCESS_KEY_ID:
        required: true
      AWS_SECRET_ACCESS_KEY:
        required: true
      AWS_REGION:
        required: false
      SLACK_WEBHOOK:
        required: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_REGION || 'us-east-1' }}

      - name: Notify
        if: secrets.SLACK_WEBHOOK != ''
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Deployed to ${{ inputs.environment }}"}
```

---

## 14.8 Shared Cache

### Cache Entre Packages

Em monorepos, packages frequentemente compartilham dependencias. Um cache compartilhado evita downloads repetidos e acelera builds significativamente.

### Cache Basico com actions/cache

```yaml
name: Shared Cache Monorepo

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  install:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Cache node_modules
        uses: actions/cache@v4
        with:
          path: |
            node_modules
            packages/*/node_modules
          key: ${{ runner.os }}-modules-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            ${{ runner.os }}-modules-

      - name: Install all dependencies
        run: npm ci

  test-core:
    needs: install
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Restore cache
        uses: actions/cache@v4
        with:
          path: |
            node_modules
            packages/*/node_modules
          key: ${{ runner.os }}-modules-${{ hashFiles('**/package-lock.json') }}

      - name: Test core
        run: cd packages/core && npm test
```

### Cache com Turbo

```yaml
name: Turbo Shared Cache

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

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Cache Turborepo
        uses: actions/cache@v4
        with:
          path: .turbo/cache
          key: turbo-${{ runner.os }}-${{ hashFiles('**/turbo.json') }}-${{ github.sha }}
          restore-keys: |
            turbo-${{ runner.os }}-${{ hashFiles('**/turbo.json') }}-
            turbo-${{ runner.os }}-

      - name: Build
        run: pnpm turbo build

      - name: Test
        run: pnpm turbo test
```

### Cache por Package com Hash

```yaml
name: Per-Package Cache

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web, shared]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Cache package build
        uses: actions/cache@v4
        with:
          path: packages/${{ matrix.package }}/dist
          key: build-${{ matrix.package }}-${{ hashFiles(format('packages/{0}/src/**', matrix.package)) }}
          restore-keys: |
            build-${{ matrix.package }}-

      - name: Install and build
        run: |
          cd packages/${{ matrix.package }}
          npm ci
          npm run build
```

### Cache com Restore Keys Progressivos

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Cache npm dependencies
        uses: actions/cache@v4
        with:
          path: ~/.npm
          key: npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            npm-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
            npm-${{ runner.os }}-
            npm-

      - name: Cache node_modules
        uses: actions/cache@v4
        with:
          path: |
            node_modules
            packages/*/node_modules
          key: modules-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            modules-${{ runner.os }}-

      - name: Cache build artifacts
        uses: actions/cache@v4
        with:
          path: |
            packages/*/dist
            packages/*/.next
          key: builds-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            builds-${{ runner.os }}-

      - name: Install
        run: npm ci

      - name: Build all
        run: npm run build:all
```

### Cache com Dependencias Cross-Package

```yaml
name: Cross-Package Cache

on:
  push:
    branches: [main]

jobs:
  build-dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install all
        run: pnpm install --frozen-lockfile

      - name: Build shared first
        run: pnpm --filter @myorg/shared build

      - name: Cache shared build
        uses: actions/cache/save@v4
        with:
          path: packages/shared/dist
          key: shared-build-${{ github.sha }}

  build-packages:
    needs: build-dependencies
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install all
        run: pnpm install --frozen-lockfile

      - name: Restore shared build
        uses: actions/cache/restore@v4
        with:
          path: packages/shared/dist
          key: shared-build-${{ github.sha }}

      - name: Build
        run: pnpm --filter @myorg/${{ matrix.package }} build
```

---

## 14.9 Matrix por Package

### Matrix Dinamica com Changed Files

```yaml
name: Matrix by Package

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect changes
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

      - name: Build matrix
        run: |
          CHANGES=""
          if [ "${{ steps.filter.outputs.core }}" == "true" ]; then
            CHANGES="${CHANGES}core,"
          fi
          if [ "${{ steps.filter.outputs.api }}" == "true" ]; then
            CHANGES="${CHANGES}api,"
          fi
          if [ "${{ steps.filter.outputs.web }}" == "true" ]; then
            CHANGES="${CHANGES}web,"
          fi
          # Remove trailing comma and format as JSON array
          CHANGES=$(echo "$CHANGES" | sed 's/,$//' | jq -R -c 'split(",") | map(select(length > 0))')
          echo "changes=$CHANGES" >> "$GITHUB_OUTPUT"

  test:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages != '[]'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: ${{ fromJSON(needs.detect-changes.outputs.packages) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: cd packages/${{ matrix.package }} && npm ci

      - name: Lint
        run: cd packages/${{ matrix.package }} && npm run lint

      - name: Type check
        run: cd packages/${{ matrix.package }} && npm run typecheck

      - name: Test
        run: cd packages/${{ matrix.package }} && npm test

      - name: Build
        run: cd packages/${{ matrix.package }} && npm run build
```

### Matrix com Multiplos OS

```yaml
name: Cross-Platform Matrix

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.filter.outputs.changes }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'

  test:
    needs: detect
    if: needs.detect.outputs.packages != '[]'
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        package: ${{ fromJSON(needs.detect.outputs.packages) }}
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install
        run: cd packages/${{ matrix.package }} && npm ci

      - name: Test
        run: cd packages/${{ matrix.package }} && npm test
```

### Matrix com Include e Exclude

```yaml
name: Advanced Matrix

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest]
        package: [core, api]
        include:
          - node-version: 20
            os: windows-latest
            package: core
          - node-version: 20
            os: macos-latest
            package: core
        exclude:
          - node-version: 18
            package: api
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install
        run: cd packages/${{ matrix.package }} && npm ci

      - name: Test
        run: cd packages/${{ matrix.package }} && npm test
```

### Matrix com Max-Parallel

```yaml
name: Controlled Parallel Matrix

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      max-parallel: 2
      matrix:
        package: [core, api, web, shared, worker, cli]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/${{ matrix.package }} && npm ci && npm test
```

### Matrix com Continue-on-error

```yaml
name: Resilient Matrix

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web, shared]
      fail-fast: false
    continue-on-error: ${{ matrix.package == 'web' }}
    steps:
      - uses: actions/checkout@v4

      - name: Test
        run: cd packages/${{ matrix.package }} && npm ci && npm test
```

---

## 14.10 Exemplo Completo

### Monorepo CI/CD Completo

```yaml
name: Monorepo Full CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  packages: write
  pull-requests: write

jobs:
  # ============================================================
  # JOB 1: Detectar packages afetados
  # ============================================================
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      core: ${{ steps.filter.outputs.core }}
      api: ${{ steps.filter.outputs.api }}
      web: ${{ steps.filter.outputs.web }}
      shared: ${{ steps.filter.outputs.shared }}
      any-code: ${{ steps.filter.outputs.any-code }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect changed files
        uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            core:
              - 'packages/core/**'
              - 'packages/shared/**'
              - 'package.json'
              - 'turbo.json'
            api:
              - 'packages/api/**'
              - 'packages/shared/**'
              - 'package.json'
              - 'turbo.json'
            web:
              - 'packages/web/**'
              - 'packages/shared/**'
              - 'package.json'
              - 'turbo.json'
            shared:
              - 'packages/shared/**'
            any-code:
              - 'packages/**'
              - 'tools/**'
              - 'package.json'
              - 'turbo.json'
              - 'tsconfig.json'

  # ============================================================
  # JOB 2: Lint global
  # ============================================================
  lint:
    needs: detect-changes
    if: needs.detect-changes.outputs.any-code == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Lint all packages
        run: pnpm turbo lint

      - name: Type check all packages
        run: pnpm turbo typecheck

  # ============================================================
  # JOB 3: Testar core
  # ============================================================
  test-core:
    needs: [detect-changes, lint]
    if: needs.detect-changes.outputs.core == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Test core
        run: pnpm --filter @myorg/core test -- --coverage

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-core
          path: packages/core/coverage/
          retention-days: 7

  # ============================================================
  # JOB 4: Testar shared
  # ============================================================
  test-shared:
    needs: [detect-changes, lint]
    if: needs.detect-changes.outputs.shared == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Test shared
        run: pnpm --filter @myorg/shared test -- --coverage

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-shared
          path: packages/shared/coverage/
          retention-days: 7

  # ============================================================
  # JOB 5: Testar API
  # ============================================================
  test-api:
    needs: [detect-changes, lint, test-shared]
    if: needs.detect-changes.outputs.api == 'true'
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

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Test API
        run: pnpm --filter @myorg/api test -- --coverage
        env:
          DATABASE_URL: postgresql://postgres:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-api
          path: packages/api/coverage/
          retention-days: 7

  # ============================================================
  # JOB 6: Testar Web
  # ============================================================
  test-web:
    needs: [detect-changes, lint, test-shared]
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Test Web
        run: pnpm --filter @myorg/web test -- --coverage

      - name: Build Web
        run: pnpm --filter @myorg/web build

      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-web
          path: packages/web/coverage/
          retention-days: 7

  # ============================================================
  # JOB 7: Build para staging
  # ============================================================
  build-staging:
    needs: [test-core, test-api, test-web, test-shared]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm --filter @myorg/${{ matrix.package }} build

      - name: Upload build
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.package }}-staging
          path: packages/${{ matrix.package }}/dist/
          retention-days: 3

  # ============================================================
  # JOB 8: Deploy staging
  # ============================================================
  deploy-staging:
    needs: build-staging
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    strategy:
      matrix:
        package: [api, web]
      max-parallel: 1
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-${{ matrix.package }}-staging
          path: dist

      - name: Deploy to staging
        run: |
          echo "Deploying ${{ matrix.package }} to staging"
          ls -la dist/

  # ============================================================
  # JOB 9: Build para production
  # ============================================================
  build-production:
    needs: [test-core, test-api, test-web, test-shared]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - name: Install pnpm
        run: corepack enable && corepack prepare pnpm@latest --activate

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Build
        run: pnpm --filter @myorg/${{ matrix.package }} build

      - name: Upload build
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ matrix.package }}-production
          path: packages/${{ matrix.package }}/dist/
          retention-days: 3

  # ============================================================
  # JOB 10: Deploy production
  # ============================================================
  deploy-production:
    needs: build-production
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    strategy:
      matrix:
        package: [api, web]
      max-parallel: 1
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-${{ matrix.package }}-production
          path: dist

      - name: Deploy to production
        run: |
          echo "Deploying ${{ matrix.package }} to production"
          ls -la dist/

      - name: Health check
        run: |
          echo "Running health check for ${{ matrix.package }}"
          sleep 10
          echo "Health check passed"

  # ============================================================
  # JOB 11: Notificacao
  # ============================================================
  notify:
    needs: [deploy-staging, deploy-production]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Determine status
        id: status
        run: |
          if [ "${{ needs.deploy-staging.result }}" == "success" ] || [ "${{ needs.deploy-production.result }}" == "success" ]; then
            echo "status=success" >> "$GITHUB_OUTPUT"
          else
            echo "status=failure" >> "$GITHUB_OUTPUT"
          fi

      - name: Notify Slack
        if: steps.status.outputs.status == 'failure'
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Monorepo CI/CD failed",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Monorepo CI/CD Failed*\n*Repo:* ${{ github.repository }}\n*Branch:* ${{ github.ref_name }}\n*Run:* ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                  }
                }
              ]
            }
```

---

## 14.11 Boas Praticas

### Regras Fundamentais

1. **Sempre usar path filters**: Evite builds desnecessarios filtrando por paths afetados
2. **Detectar mudancas antes de buildar**: Use dorny/paths-filter ou equivalente
3. **Cache compartilhado e obrigatorio**: Configure caches que persistem entre jobs e workflows
4. **Deploys independentes**: Cada package deve poder ser implantado separadamente
5. **Reusable workflows**: Extrair logica comum para workflows reutilizaveis
6. **Fail-fast: false**: Em monorepos, um package nao deve impedir testes de outros
7. **Max-parallel**: Controle paralelismo para evitar sobrecarga de recursos
8. **Concurrency groups**: Previna execucoes duplicadas do mesmo workflow
9. **Matrix dinamica**: Gere a matrix baseada nos packages afetados
10. **Testes de integracao**: Testar packages em conjunto alem de isoladamente

### Anti-Patterns

| Anti-Pattern | Problema | Solucao |
|--------------|----------|---------|
| Build completo sempre | Consumo desnecessario de minutos | Path filters + changed detection |
| Sem cache compartilhado | Downloads repetidos | actions/cache com keys por package |
| Deploy acoplado | Todos os packages implantados juntos | Deploys independentes com conditions |
| Matrix estatica fixa | Testa packages que nao mudaram | Matrix dinamica com fromJSON |
| Sem concurrency group | Workflows duplicados | concurrency com cancel-in-progress |
| Sem fail-fast: false | Um package falha todos | Configurar fail-fast: false |
| Sem max-parallel | Sobra de recursos | Definir max-parallel adequado |
| Sem reusabilidade | Duplicacao de workflows | Reusable workflows com workflow_call |
| Sem branch strategy | Deploys em todas as branches | Condicionais por branch |
| Sem environment protection | Deploy direto para producao | Environment protection rules |

### Organizacao de Diretorios

```
monorepo/
  .github/
    workflows/
      ci.yml                    # Workflow principal de CI
      cd-staging.yml            # Deploy para staging
      cd-production.yml         # Deploy para producao
      reusable-test.yml         # Workflow reutilizavel de teste
      reusable-build.yml        # Workflow reutilizavel de build
      reusable-deploy.yml       # Workflow reutilizavel de deploy
    actions/
      setup-monorepo/           # Composite action para setup
        action.yml
        scripts/
  packages/
    core/
      src/
      package.json
      tsconfig.json
    api/
      src/
      package.json
      tsconfig.json
    web/
      src/
      package.json
      tsconfig.json
    shared/
      src/
      package.json
      tsconfig.json
  tools/
    scripts/
      detect-changes.sh
  turbo.json
  package.json
  pnpm-workspace.yaml
  tsconfig.json
```

### Composite Action para Setup

```yaml
# .github/actions/setup-monorepo/action.yml
name: Setup Monorepo
description: Setup completo para monorepo com cache

inputs:
  node-version:
    description: "Versao do Node.js"
    required: false
    default: '20'

runs:
  using: composite
  steps:
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'pnpm'

    - name: Install pnpm
      shell: bash
      run: corepack enable && corepack prepare pnpm@latest --activate

    - name: Cache pnpm store
      uses: actions/cache@v4
      with:
        path: ~/.pnpm-store
        key: pnpm-${{ runner.os }}-${{ hashFiles('**/pnpm-lock.yaml') }}
        restore-keys: |
          pnpm-${{ runner.os }}-

    - name: Install dependencies
      shell: bash
      run: pnpm install --frozen-lockfile

    - name: Cache Turborepo
      uses: actions/cache@v4
      with:
        path: .turbo/cache
        key: turbo-${{ runner.os }}-${{ hashFiles('**/turbo.json') }}-${{ github.sha }}
        restore-keys: |
          turbo-${{ runner.os }}-${{ hashFiles('**/turbo.json') }}-
          turbo-${{ runner.os }}-
```

---

## 14.12 Gerenciamento de Dependencias

### Grafo de Dependencias

Em monorepos, packages podem depender uns dos outros. Gerenciar essas dependencias corretamente e crucial para builds eficientes.

```json
// packages/api/package.json
{
  "name": "@myorg/api",
  "dependencies": {
    "@myorg/core": "workspace:*",
    "@myorg/shared": "workspace:*"
  }
}
```

### Build Ordem Correta

```yaml
name: Dependency-Aware Build

on:
  push:
    branches: [main]

jobs:
  build-shared:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: corepack enable && corepack prepare pnpm@latest --activate
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/shared build
      - uses: actions/upload-artifact@v4
        with:
          name: shared-dist
          path: packages/shared/dist/

  build-core:
    needs: build-shared
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: shared-dist
          path: packages/shared/dist/
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: corepack enable && corepack prepare pnpm@latest --activate
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/core build
      - uses: actions/upload-artifact@v4
        with:
          name: core-dist
          path: packages/core/dist/

  build-api:
    needs: [build-shared, build-core]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: shared-dist
          path: packages/shared/dist/
      - uses: actions/download-artifact@v4
        with:
          name: core-dist
          path: packages/core/dist/
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: corepack enable && corepack prepare pnpm@latest --activate
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/api build
      - uses: actions/upload-artifact@v4
        with:
          name: api-dist
          path: packages/api/dist/

  build-web:
    needs: [build-shared, build-core]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: shared-dist
          path: packages/shared/dist/
      - uses: actions/download-artifact@v4
        with:
          name: core-dist
          path: packages/core/dist/
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: corepack enable && corepack prepare pnpm@latest --activate
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter @myorg/web build
      - uses: actions/upload-artifact@v4
        with:
          name: web-dist
          path: packages/web/dist/
```

### Turbo Resolva Dependencias Automaticamente

```yaml
# Com Turborepo, a ordem de build e resolvida automaticamente
name: Turbo Dependency Resolution

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'
      - run: corepack enable && corepack prepare pnpm@latest --activate
      - run: pnpm install --frozen-lockfile
      # Turbo constroi o grafo automaticamente e respeita dependsOn
      - run: pnpm turbo build
```

---

## 14.13 Versionamento Semver

### Versionamento com Changesets

```yaml
name: Version and Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'pnpm'

      - run: corepack enable && corepack prepare pnpm@latest --activate

      - run: pnpm install --frozen-lockfile

      - name: Create release
        id: changesets
        uses: changesets/action@v1
        with:
          version: pnpm changeset version
          publish: pnpm changeset publish
          title: 'chore: version packages'
          commit: 'chore: version packages'
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### Versionamento com Conventional Commits

```yaml
name: Semantic Release

on:
  push:
    branches: [main]

jobs:
  release:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, api, web]
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: cd packages/${{ matrix.package }} && npm ci

      - name: Semantic Release
        run: |
          cd packages/${{ matrix.package }}
          npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 14.14 Mudanca Seletiva com Diffs

### Usando git diff para Deteccao

```yaml
name: Selective Change Detection

on:
  push:
    branches: [main]

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.detect.outputs.packages }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect changed packages
        id: detect
        run: |
          BASE=${{ github.event.before }}
          HEAD=${{ github.sha }}

          CHANGED_DIRS=$(git diff --name-only "$BASE" "$HEAD" | \
            awk -F/ '{print $1"/"$2}' | sort -u)

          PACKAGES="[]"
          for DIR in $CHANGED_DIRS; do
            if [ -d "$DIR" ] && [ -f "$DIR/package.json" ]; then
              PKG_NAME=$(jq -r '.name' "$DIR/package.json" | sed 's/@myorg\///')
              PACKAGES=$(echo "$PACKAGES" | jq -c ". + [\"$PKG_NAME\"]")
            fi
          done

          echo "packages=$PACKAGES" >> "$GITHUB_OUTPUT"
          echo "Detected packages: $PACKAGES"
```

### Filtrar por Tipo de Mudanca

```yaml
name: Change Type Detection

on:
  push:
    branches: [main]

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      source-changes: ${{ steps.types.outputs.source }}
      config-changes: ${{ steps.types.outputs.config }}
      test-changes: ${{ steps.types.outputs.test }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Detect change types
        id: types
        run: |
          BASE=${{ github.event.before }}
          HEAD=${{ github.sha }}

          SOURCE=$(git diff --name-only "$BASE" "$HEAD" | grep -E '\.(ts|js|tsx|jsx)$' | grep -v '\.test\.' | grep -v '\.spec\.' | wc -l)
          CONFIG=$(git diff --name-only "$BASE" "$HEAD" | grep -E '(package\.json|tsconfig\.json|turbo\.json)$' | wc -l)
          TEST=$(git diff --name-only "$BASE" "$HEAD" | grep -E '\.(test|spec)\.(ts|js|tsx|jsx)$' | wc -l)

          [ "$SOURCE" -gt 0 ] && echo "source=true" >> "$GITHUB_OUTPUT" || echo "source=false" >> "$GITHUB_OUTPUT"
          [ "$CONFIG" -gt 0 ] && echo "config=true" >> "$GITHUB_OUTPUT" || echo "config=false" >> "$GITHUB_OUTPUT"
          [ "$TEST" -gt 0 ] && echo "test=true" >> "$GITHUB_OUTPUT" || echo "test=false" >> "$GITHUB_OUTPUT"
```

---

## 14.15 Otimizacao de Custos

### Estrategias de Reducao

```yaml
name: Cost-Optimized CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.filter.outputs.changes }}
      has-changes: ${{ steps.filter.outputs.has-changes }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect changes
        id: filter
        uses: dorny/paths-filter@v3
        with:
          filters: |
            core:
              - 'packages/core/**'
            api:
              - 'packages/api/**'
            web:
              - 'packages/web/**'

      - name: Check if any changes
        run: |
          if [ "${{ steps.filter.outputs.core }}" == "true" ] || \
             [ "${{ steps.filter.outputs.api }}" == "true" ] || \
             [ "${{ steps.filter.outputs.web }}" == "true" ]; then
            echo "has-changes=true" >> "$GITHUB_OUTPUT"
          else
            echo "has-changes=false" >> "$GITHUB_OUTPUT"
          fi

  test:
    needs: detect
    if: needs.detect.outputs.has-changes == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    strategy:
      matrix:
        package: ${{ fromJSON(needs.detect.outputs.packages) }}
      fail-fast: false
      max-parallel: 3
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install
        run: cd packages/${{ matrix.package }} && npm ci

      - name: Test
        run: cd packages/${{ matrix.package }} && npm test
        timeout-minutes: 10

      - name: Build
        run: cd packages/${{ matrix.package }} && npm run build
        timeout-minutes: 5
```

### Monitoring de Custos

```yaml
name: Cost Tracking

on:
  workflow_run:
    workflows: ["Monorepo Full CI/CD"]
    types: [completed]

jobs:
  track-costs:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate cost
        run: |
          RUN_DURATION=${{ github.event.workflow_run.updated_at }}
          RUN_ID=${{ github.event.workflow_run.id }}

          echo "Workflow run: $RUN_ID"
          echo "Completed at: $RUN_DURATION"

          # GitHub API para detalhes do run
          curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs/$RUN_ID/jobs" \
            | jq '.jobs[] | {name: .name, started_at: .started_at, completed_at: .completed_at, conclusion: .conclusion}'
```

---

## 14.16 Exercicios

1. Implemente path filters para 3 packages em um monorepo
2. Configure deploys independentes por package com environment protection rules
3. Implemente cache compartilhado entre packages com restore-keys progressivos
4. Crie matrix build por package com changes detection e fail-fast: false
5. Integre Turborepo com GitHub Actions usando cache remoto
6. Implemente Nx com affected projects detection
7. Crie reusable workflows para test, build e deploy
8. Implemente versionamento semver com Changesets
9. Configure monitoring de custos com workflow_run
10. Implemente composite action para setup de monorepo

---

## 14.17 Referencias

1. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_targetpathspaths-ignore
2. https://github.com/dorny/paths-filter
3. https://github.com/tj-actions/changed-files
4. https://turbo.build/repo/docs
5. https://nx.dev/getting-started/intro
6. https://github.com/changesets/changesets
7. https://docs.github.com/en/actions/using-workflows/reusing-workflows
8. https://github.com/actions/cache
9. https://turbo.build/repo/docs/core-concepts/remote-caching
10. https://nx.dev/concepts/more-concepts/how-caching-works
11. https://pnpm.io/workspaces
12. https://docs.github.com/en/actions/learn-github-actions/contexts
13. https://docs.github.com/en/actions/learn-github-actions/expressions
14. https://github.com/actions/runner/blob/main/docs/hosted-details.md
15. https://docs.github.com/en/actions/using-workflows/monitoring-and-troubleshooting-workflows
