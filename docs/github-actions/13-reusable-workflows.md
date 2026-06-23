---
layout: default
title: "13-reusable-workflows"
---

# Capitulo 13 -- Reusable Workflows

> *"Nao repita -- reutilize. Mas reutilize com seguranca."*

---

## Objetivos de Aprendizado

1. Criar reusable workflows com workflow_call trigger
2. Configurar inputs, secrets e outputs
3. Usar caller workflows corretamente
4. Comparar composite actions vs reusable workflows
5. Implementar organization-level reusable workflows
6. Configurar versioning de workflows
7. Testar reusable workflows
8. Implementar seguranca e permissoes
9. Configurar services em reusable workflows
10. Implementar error handling
11. Configurar workflow_call com multiplos triggers
12. Implementar reusable workflows para multi-cloud
13. Configurar reusable workflows com OIDC
14. Implementar reusable workflows para container builds
15. Configurar reusable workflows com matrix

---

## 13.1 workflow_call Trigger

### O Que e workflow_call

`workflow_call` e um trigger que permite que um workflow seja chamado por outro workflow. Isso permite reutilizar logicas comuns entre multiplos repositorios ou workflows.

### Exemplo Basico

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

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: ${{ inputs.build-command }}
```

### Uso como Caller

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  build:
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'
      build-command: 'npm run build:prod'
```

### workflow_call com Secrets

```yaml
# .github/workflows/reusable-deploy.yml
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      DEPLOY_TOKEN:
        required: true
      AWS_ROLE_ARN:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
        run: |
          echo "Deploying to ${{ inputs.environment }}"
```

### workflow_call com Outputs

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

on:
  workflow_call:
    inputs:
      test-command:
        required: false
        type: string
        default: 'npm test'
    outputs:
      test-result:
        description: 'Resultado dos testes'
        value: ${{ jobs.test.outputs.result }}
      coverage:
        description: 'Cobertura de testes'
        value: ${{ jobs.test.outputs.coverage }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.test.outputs.result }}
      coverage: ${{ steps.test.outputs.coverage }}
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
        id: test
        run: |
          ${{ inputs.test-command }}
          echo "result=success" >> $GITHUB_OUTPUT
          echo "coverage=85%" >> $GITHUB_OUTPUT
```

### Uso de Outputs

```yaml
# .github/workflows/ci.yml
name: CI

on: [push]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      test-command: 'npm test -- --coverage'

  deploy:
    needs: test
    if: needs.test.outputs.test-result == 'success'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testes passaram com ${{ needs.test.outputs.coverage }} de cobertura"
```

### workflow_call com Multiplos Triggers

```yaml
# .github/workflows/reusable-ci.yml
name: Reusable CI

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      run-lint:
        required: false
        type: boolean
        default: true
      run-security:
        required: false
        type: boolean
        default: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install
        run: npm ci
      
      - name: Test
        run: npm test

  lint:
    if: inputs.run-lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install
        run: npm ci
      
      - name: Lint
        run: npm run lint

  security:
    if: inputs.run-security
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
      
      - name: Analyze
        uses: github/codeql-action/analyze@v3
```

---

## 13.2 Inputs and Secrets

### Tipos de Inputs

```yaml
on:
  workflow_call:
    inputs:
      # String
      node-version:
        required: true
        type: string
        description: 'Versao do Node.js'
      
      # Boolean
      deploy:
        required: false
        type: boolean
        default: false
        description: 'Habilitar deploy'
      
      # Number
      timeout:
        required: false
        type: number
        default: 30
        description: 'Timeout em minutos'
      
      # Choice (enum)
      environment:
        required: true
        type: choice
        options:
          - staging
          - production
        description: 'Environment alvo'
```

### Inputs Opcionais com Defaults

```yaml
on:
  workflow_call:
    inputs:
      node-version:
        required: false
        type: string
        default: '20'
      
      npm-command:
        required: false
        type: string
        default: 'npm ci && npm test'
      
      upload-artifacts:
        required: false
        type: boolean
        default: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      
      - name: Build and Test
        run: ${{ inputs.npm-command }}
      
      - name: Upload artifacts
        if: inputs.upload-artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
```

### Secrets Obrigatorios vs Opcionais

```yaml
on:
  workflow_call:
    secrets:
      # Obrigatorio
      AWS_ROLE_ARN:
        required: true
        description: 'ARN da role AWS'
      
      # Opcional
      SLACK_WEBHOOK:
        required: false
        description: 'Webhook do Slack para notificacoes'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Notificar Slack
        if: secrets.SLACK_WEBHOOK != ''
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Deploy concluido"}' \
            $SLACK_WEBHOOK
```

### Validacao de Inputs

```yaml
on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validar inputs
        run: |
          # Validar versao do Node.js
          if [[ ! "${{ inputs.node-version }}" =~ ^[0-9]+$ ]]; then
            echo "ERRO: node-version deve ser um numero"
            exit 1
          fi
          
          if [ "${{ inputs.node-version }}" -lt 18 ]; then
            echo "ERRO: node-version deve ser >= 18"
            exit 1
          fi
          
          echo "Inputs validados com sucesso"
```

### Secrets com Inheritance

```yaml
# Caller workflow
name: CI

on: [push]

jobs:
  deploy:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
    secrets: inherit  # Herda todos os secrets do caller
```

### Inputs de Tipos Complexos

```yaml
on:
  workflow_call:
    inputs:
      config:
        required: true
        type: string
        description: 'Configuracao em JSON'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Parse config
        run: |
          echo "${{ inputs.config }}" | jq '.'
          
          # Extrair valores
          NODE_VERSION=$(echo "${{ inputs.config }}" | jq -r '.node-version')
          BUILD_CMD=$(echo "${{ inputs.config }}" | jq -r '.build-command')
          
          echo "Node: $NODE_VERSION"
          echo "Build: $BUILD_CMD"
```

---

## 13.3 Caller Workflows

### Caller Basico

```yaml
# Caller simples
name: CI

on: [push, pull_request]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  build:
    needs: test
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'
```

### Caller com Multiplos Workflows

```yaml
name: Complete CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Teste
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
      test-command: 'npm test -- --coverage'

  # Build
  build:
    needs: test
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  # Security scan
  security:
    needs: build
    uses: ./.github/workflows/reusable-security.yml
    with:
      scan-type: 'full'

  # Deploy staging
  deploy-staging:
    needs: security
    if: github.ref == 'refs/heads/main'
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: staging
    secrets:
      DEPLOY_TOKEN: ${{ secrets.STAGING_DEPLOY_TOKEN }}
      AWS_ROLE_ARN: ${{ secrets.AWS_STAGING_ROLE_ARN }}

  # Deploy production
  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
    secrets:
      DEPLOY_TOKEN: ${{ secrets.PRODUCTION_DEPLOY_TOKEN }}
      AWS_ROLE_ARN: ${{ secrets.AWS_PRODUCTION_ROLE_ARN }}
```

### Caller com Condicional

```yaml
name: Conditional CI

on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  deploy:
    needs: test
    if: github.event_name == 'push'
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    secrets:
      DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

### Caller com Matrix

```yaml
name: Matrix CI

on: [push]

jobs:
  test:
    strategy:
      matrix:
        node-version: [18, 20, 22]
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: ${{ matrix.node-version }}
```

### Caller com Reusable Workflows de Outro Repo

```yaml
name: CI with External Reusable Workflows

on:
  push:
    branches: [main]

jobs:
  test:
    uses: myorg/.github/.github/workflows/reusable-test.yml@main
    with:
      node-version: '20'
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  deploy:
    needs: test
    uses: myorg/.github/.github/workflows/reusable-deploy.yml@main
    with:
      environment: production
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
```

### Caller com Error Handling

```yaml
name: CI with Error Handling

on: [push]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
    result: success

  build:
    needs: test
    if: needs.test.result == 'success'
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  notify-failure:
    needs: [test, build]
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Notificar falha
        run: |
          echo "CI/CD falhou"
          # Enviar notificacao
```

---

## 13.4 Composite vs Reusable Comparison

### Tabela Comparativa

| Aspecto | Reusable Workflow | Composite Action |
|---------|-------------------|------------------|
| Arquivo | `.github/workflows/*.yml` | `.github/actions/*/action.yml` |
| Execucao | Job completo | Step dentro de job |
| Outputs | Job outputs | Step outputs |
| Secrets | Podem receber | Nao podem receber |
| Matrix | Podem ter | Nao podem ter |
| Services | Podem ter | Nao podem ter |
| Ambiente | VM propria | VM do caller |
| Timeout | Configuravel | Herda do job |
| Concorrencia | Independente | Dentro do job |

### Exemplo de Composite Action

```yaml
# .github/actions/setup-node/action.yml
name: 'Setup Node.js'
description: 'Setup Node.js com cache de dependencias'

inputs:
  node-version:
    description: 'Versao do Node.js'
    required: true
  cache:
    description: 'Habilitar cache'
    required: false
    default: 'true'

runs:
  using: 'composite'
  steps:
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: ${{ inputs.cache }}
    
    - name: Install dependencies
      shell: bash
      run: npm ci
    
    - name: Verify installation
      shell: bash
      run: |
        node --version
        npm --version
```

### Uso da Composite Action

```yaml
name: CI

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup project
        uses: ./.github/actions/setup-node
        with:
          node-version: '20'
      
      - run: npm test
```

### Exemplo de Reusable Workflow

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - run: npm ci
      - run: npm test
```

### Quando Usar Cada Um

```
# Composite Action:
# - Reutilizar steps dentro de um job
# - Setup de ferramentas
# - Validacao de inputs
# - Steps que nao precisam de ambiente isolado

# Reusable Workflow:
# - Reutilizar jobs inteiros
# - Pipelines completas
# - Jobs que precisam de ambiente isolado
# - Jobs que precisam de secrets
# - Jobs que precisam de matrix
```

---

## 13.5 Organization-Level Reusable Workflows

### Configuracao

```yaml
# Em um repositorio dedicado (ex: myorg/.github)
# .github/workflows/reusable-ci.yml
name: Organization CI

on:
  workflow_call:
    inputs:
      language:
        required: true
        type: string
      version:
        required: true
        type: string
    secrets:
      ORG_SECRET:
        required: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup ${{ inputs.language }}
        run: |
          echo "Setting up ${{ inputs.language }} ${{ inputs.version }}"
      
      - name: Test
        env:
          SECRET: ${{ secrets.ORG_SECRET }}
        run: |
          echo "Running tests"
```

### Uso em Outro Repositorio

```yaml
# Em qualquer repositorio da organizacao
name: CI

on: [push]

jobs:
  test:
    uses: myorg/.github/.github/workflows/reusable-ci.yml@main
    with:
      language: 'node'
      version: '20'
    secrets:
      ORG_SECRET: ${{ secrets.ORG_SECRET }}
```

### Vantagens do Organization-Level

```yaml
# 1. Centralizacao
# - Uma unica fonte de verdade para CI/CD
# - Atualizacoes em um lugar afetam todos os repos

# 2. Seguranca
# - Secrets gerenciados centralmente
# - Padroes de seguranca enforceados

# 3. Consistencia
# - Mesmos workflows em todos os repos
# - Menos erros humanos

# 4. Manutencao
# - Atualizacoes em um lugar
# - Menos duplicacao de codigo
```

### Restricao de Acesso

```yaml
# Configurar no repositorio .github
# Settings > Actions > General > Access

# Opcoes:
# - All repositories in this organization
# - Selected repositories only
# - Only this repository

# Recomendacao: Usar "Selected repositories" para workflows criticos
```

### Estrategia de Organizacao

```yaml
# Estrategia recomendada para organization-level workflows
#
# Repositorio myorg/.github:
# .github/workflows/
#   reusable-ci.yml          # CI basico
#   reusable-test.yml        # Testes
#   reusable-build.yml       # Build
#   reusable-deploy.yml      # Deploy
#   reusable-security.yml    # Security scanning
#   reusable-release.yml     # Release automation
#
# Todos os outros repos usam esses workflows
```

### Gerenciamento de Versoes

```yaml
# Estrategia de versoes para organization workflows
#
# Versao por tag:
# - v1.0.0: Versao inicial
# - v1.1.0: Novas features (backward compatible)
# - v2.0.0: Breaking changes
#
# Uso:
# uses: myorg/.github/.github/workflows/reusable-ci.yml@v1.0.0
```

---

## 13.6 Versioning

### Estrategias de Versioning

```yaml
# 1. Tag-based (recomendado)
uses: myorg/.github/.github/workflows/reusable-ci.yml@v1.0.0

# 2. Branch-based (perigoso - pode mudar)
uses: myorg/.github/.github/workflows/reusable-ci.yml@main

# 3. SHA-based (mais seguro)
uses: myorg/.github/.github/workflows/reusable-ci.yml@abc123def456...
```

### Criar Tags

```bash
# Criar tag
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# Criar tag via GitHub CLI
gh release create v1.0.0 --title "v1.0.0" --notes "Release notes"
```

### Versioning Semantico

```yaml
# v1.0.0 - Release inicial
# v1.1.0 - Novas features (backward compatible)
# v1.2.0 - Novas features
# v2.0.0 - Breaking changes

# Exemplo de uso:
# Versao menor: adicionar input opcional
uses: myorg/.github/.github/workflows/reusable-ci.yml@v1.1.0

# Versao maior: mudar input obrigatorio
uses: myorg/.github/.github/workflows/reusable-ci.yml@v2.0.0
```

### Compatibilidade

```yaml
# Manter backward compatibility:
# 1. Inputs antigos continuam funcionando
# 2. Novos inputs sao opcionais
# 3. Outputs antigos continuam disponiveis
# 4. Breaking changes na v2.0.0

# Documentar mudancas:
# CHANGELOG.md no repositorio .github
```

### Automacao de Versoes

```yaml
name: Auto Version

on:
  push:
    branches: [main]

jobs:
  version:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Detect version bump
        id: bump
        run: |
          # Analisar commits desde ultima tag
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
          COMMITS=$(git log $LAST_TAG..HEAD --oneline)
          
          if echo "$COMMITS" | grep -q "BREAKING CHANGE"; then
            echo "bump=major" >> $GITHUB_OUTPUT
          elif echo "$COMMITS" | grep -q "feat:"; then
            echo "bump=minor" >> $GITHUB_OUTPUT
          else
            echo "bump=patch" >> $GITHUB_OUTPUT
          fi
      
      - name: Create tag
        if: steps.bump.outputs.bump != 'none'
        run: |
          # Calcular nova versao
          # Criar tag
          git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
          git push origin "v$NEW_VERSION"
```

---

## 13.7 Testing

### Testar Localmente com Act

```bash
# Instalar act
brew install act  # macOS
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Testar workflow
act -W .github/workflows/reusable-test.yml

# Testar com inputs
act workflow_call -W .github/workflows/reusable-test.yml \
  --input node-version=20
```

### Teste de Integracao

```yaml
name: Test Reusable Workflow

on:
  workflow_dispatch:
    inputs:
      test-type:
        description: 'Tipo de teste'
        required: true
        type: choice
        options:
          - unit
          - integration
          - e2e

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
      test-command: 'npm run test:${{ inputs.test-type }}'
```

### Teste com Mock

```yaml
name: Test with Mock

on:
  workflow_dispatch:

jobs:
  test:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: staging
    secrets:
      DEPLOY_TOKEN: 'mock-token'
      AWS_ROLE_ARN: 'arn:aws:iam::123456789:role/mock'
```

### Teste de Regressao

```yaml
name: Regression Test

on:
  pull_request:
    paths:
      - '.github/workflows/**'

jobs:
  test-old:
    uses: ./.github/workflows/reusable-ci.yml@v1.0.0
    with:
      node-version: '20'

  test-new:
    uses: ./.github/workflows/reusable-ci.yml@v1.1.0
    with:
      node-version: '20'

  compare:
    needs: [test-old, test-new]
    runs-on: ubuntu-latest
    steps:
      - name: Comparar resultados
        run: |
          echo "Teste antigo: ${{ needs.test-old.result }}"
          echo "Teste novo: ${{ needs.test-new.result }}"
          
          if [ "${{ needs.test-old.result }}" != "${{ needs.test-new.result }}" ]; then
            echo "ERRO: Resultados diferentes"
            exit 1
          fi
```

### Teste com Validação de Inputs

```yaml
name: Test Input Validation

on:
  workflow_dispatch:
    inputs:
      node-version:
        description: 'Node.js version'
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Validar input
        run: |
          if [[ ! "${{ inputs.node-version }}" =~ ^[0-9]+$ ]]; then
            echo "ERRO: Versao invalida"
            exit 1
          fi
          
          if [ "${{ inputs.node-version }}" -lt 18 ]; then
            echo "ERRO: Versao < 18 nao suportada"
            exit 1
          fi
          
          echo "Input valido"
```

---

## 13.8 Security and Permissions

### Permissoes para Reusable Workflows

```yaml
# Reusable workflow herda permissoes do caller
# Mas pode definir permissoes minimas

# Reusable workflow
name: Reusable Deploy

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      DEPLOY_TOKEN:
        required: true

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying"
```

### Caller com Permissoes

```yaml
# Caller workflow
name: CI

on: [push]

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
    secrets:
      DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
```

### Secrets em Reusable Workflows

```yaml
# Seguranca de secrets:
# 1. Secrets so podem ser passados via 'secrets' keyword
# 2. Secrets nao podem ser impressos diretamente
# 3. Secrets sao encriptados em transito
# 4. Secrets sao invalidados apos conclusao

# Reusable workflow
name: Reusable Deploy

on:
  workflow_call:
    secrets:
      DEPLOY_TOKEN:
        required: true
      AWS_ROLE_ARN:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Usar secrets
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
          AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
        run: |
          # Secrets sao mascarados nos logs
          echo "Deploying..."
```

### Validacao de Secrets

```yaml
name: Reusable Deploy

on:
  workflow_call:
    secrets:
      DEPLOY_TOKEN:
        required: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validar secrets
        run: |
          if [ -z "${{ secrets.DEPLOY_TOKEN }}" ]; then
            echo "ERRO: DEPLOY_TOKEN nao fornecido"
            exit 1
          fi
```

### Seguranca com OIDC

```yaml
# Reusable workflow com OIDC
name: Reusable Deploy OIDC

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy
        run: |
          echo "Deploying with OIDC..."
```

---

## 13.9 Reusable CI Example

### Reusable CI Workflow

```yaml
# .github/workflows/reusable-ci.yml
name: Reusable CI

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      test-command:
        required: false
        type: string
        default: 'npm test'
      build-command:
        required: false
        type: string
        default: 'npm run build'
      upload-artifacts:
        required: false
        type: boolean
        default: false
    outputs:
      test-result:
        description: 'Resultado dos testes'
        value: ${{ jobs.test.outputs.result }}
      build-version:
        description: 'Versao do build'
        value: ${{ jobs.build.outputs.version }}
    secrets:
      CODECOV_TOKEN:
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.test.outputs.result }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        id: test
        run: |
          ${{ inputs.test-command }}
          echo "result=success" >> $GITHUB_OUTPUT
      
      - name: Upload coverage
        if: secrets.CODECOV_TOKEN != ''
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.version }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: ${{ inputs.build-command }}
      
      - name: Get version
        id: version
        run: |
          VERSION=$(node -p "require('./package.json').version")
          echo "version=$VERSION" >> $GITHUB_OUTPUT
      
      - name: Upload artifacts
        if: inputs.upload-artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
```

### Caller Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    uses: ./.github/workflows/reusable-ci.yml
    with:
      node-version: '20'
      test-command: 'npm test -- --coverage'
      build-command: 'npm run build:prod'
      upload-artifacts: true
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  deploy:
    needs: ci
    if: github.ref == 'refs/heads/main' && ci.outputs.test-result == 'success'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying version ${{ needs.ci.outputs.build-version }}"
```

---

## 13.10 Composite Action Example

### Composite Action Completa

```yaml
# .github/actions/setup-project/action.yml
name: 'Setup Project'
description: 'Setup completo do projeto com cache e validacoes'

inputs:
  node-version:
    description: 'Versao do Node.js'
    required: true
  java-version:
    description: 'Versao do Java (opcional)'
    required: false
    default: ''
  python-version:
    description: 'Versao do Python (opcional)'
    required: false
    default: ''
  cache-dependency-path:
    description: 'Caminho para arquivo de lock'
    required: false
    default: 'package-lock.json'

outputs:
  node-version:
    description: 'Versao do Node.js instalada'
    value: ${{ steps.node.outputs.node-version }}

runs:
  using: 'composite'
  steps:
    - name: Setup Node.js
      id: node
      if: inputs.node-version != ''
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'
        cache-dependency-path: ${{ inputs.cache-dependency-path }}
    
    - name: Install npm dependencies
      if: inputs.node-version != ''
      shell: bash
      run: npm ci
    
    - name: Setup Java
      if: inputs.java-version != ''
      uses: actions/setup-java@v4
      with:
        java-version: ${{ inputs.java-version }}
        distribution: 'temurin'
    
    - name: Setup Python
      if: inputs.python-version != ''
      uses: actions/setup-python@v5
      with:
        python-version: ${{ inputs.python-version }}
    
    - name: Verify setup
      shell: bash
      run: |
        echo "=== Setup Verification ==="
        if [ -n "${{ inputs.node-version }}" ]; then
          node --version
          npm --version
        fi
        if [ -n "${{ inputs.java-version }}" ]; then
          java -version
        fi
        if [ -n "${{ inputs.python-version }}" ]; then
          python3 --version
        fi
```

### Uso da Composite Action

```yaml
name: CI

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup project
        id: setup
        uses: ./.github/actions/setup-project
        with:
          node-version: '20'
          java-version: '17'
          python-version: '3.11'
      
      - name: Run tests
        run: |
          npm test
          mvn test
          pytest
```

### Composite Action com Outputs

```yaml
# .github/actions/build-docker/action.yml
name: 'Build Docker'
description: 'Build e push de imagem Docker'

inputs:
  image-name:
    description: 'Nome da imagem'
    required: true
  tag:
    description: 'Tag da imagem'
    required: true
  registry:
    description: 'Registry URL'
    required: false
    default: 'ghcr.io'

outputs:
  image-digest:
    description: 'Digest da imagem'
    value: ${{ steps.build.outputs.digest }}

runs:
  using: 'composite'
  steps:
    - name: Build Docker image
      id: build
      shell: bash
      run: |
        docker build -t ${{ inputs.registry }}/${{ inputs.image-name }}:${{ inputs.tag }} .
        DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' ${{ inputs.registry }}/${{ inputs.image-name }}:${{ inputs.tag }})
        echo "digest=$DIGEST" >> $GITHUB_OUTPUT
    
    - name: Push Docker image
      shell: bash
      run: |
        echo "$DOCKER_PASSWORD" | docker login ${{ inputs.registry }} -u "$DOCKER_USERNAME" --password-stdin
        docker push ${{ inputs.registry }}/${{ inputs.image-name }}:${{ inputs.tag }}
```

### Uso com Outputs

```yaml
name: CI

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker
        id: docker
        uses: ./.github/actions/build-docker
        with:
          image-name: myapp
          tag: ${{ github.sha }}
      
      - name: Use digest
        run: |
          echo "Image digest: ${{ steps.docker.outputs.image-digest }}"
```

---

## 13.11 Reusable Workflows with Services

### Servicos em Reusable Workflows

```yaml
# .github/workflows/reusable-test-with-services.yml
name: Reusable Test with Services

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
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
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
        run: npm test
```

---

## 13.12 Exercicios

1. Crie um reusable workflow para CI que aceite linguagem como input
2. Implemente composite action para setup de projeto
3. Crie reusable workflow com secrets para deploy
4. Implemente versioning de reusable workflows
5. Teste reusable workflow localmente com act
6. Configure organization-level reusable workflows
7. Implemente reusable workflow com services (database, cache)
8. Crie composite action com multiplos outputs
9. Implemente testing de reusable workflows
10. Configure seguranca e permissoes para reusable workflows

---

## 13.14 Reusable Workflows para Diferentes Ecossistemas

### Reusable Workflow para Node.js

```yaml
# .github/workflows/reusable-nodejs.yml
name: Reusable Node.js CI

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      test-command:
        required: false
        type: string
        default: 'npm test'
      build-command:
        required: false
        type: string
        default: 'npm run build'
      coverage:
        required: false
        type: boolean
        default: false
    outputs:
      test-result:
        description: 'Resultado dos testes'
        value: ${{ jobs.test.outputs.result }}
      coverage:
        description: 'Cobertura'
        value: ${{ jobs.test.outputs.coverage }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.test.outputs.result }}
      coverage: ${{ steps.test.outputs.coverage }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install
        run: npm ci
      
      - name: Test
        id: test
        run: |
          ${{ inputs.test-command }}
          echo "result=success" >> $GITHUB_OUTPUT
      
      - name: Coverage
        if: inputs.coverage
        run: |
          COVERAGE=$(npm test -- --coverage | grep "Statements" | awk '{print $3}')
          echo "coverage=$COVERAGE" >> $GITHUB_OUTPUT

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Install
        run: npm ci
      
      - name: Build
        run: ${{ inputs.build-command }}
      
      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/
```

### Reusable Workflow para Python

```yaml
# .github/workflows/reusable-python.yml
name: Reusable Python CI

on:
  workflow_call:
    inputs:
      python-version:
        required: true
        type: string
      test-command:
        required: false
        type: string
        default: 'pytest'
      lint:
        required: false
        type: boolean
        default: true

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
          cache: 'pip'
      
      - name: Install
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Test
        run: ${{ inputs.test-command }}

  lint:
    if: inputs.lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ inputs.python-version }}
      
      - name: Install linters
        run: pip install flake8 black isort
      
      - name: Lint
        run: |
          flake8 .
          black --check .
          isort --check-only .
```

### Reusable Workflow para Go

```yaml
# .github/workflows/reusable-go.yml
name: Reusable Go CI

on:
  workflow_call:
    inputs:
      go-version:
        required: true
        type: string
      test-command:
        required: false
        type: string
        default: 'go test -v ./...'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ inputs.go-version }}
      
      - name: Test
        run: ${{ inputs.test-command }}

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{ inputs.go-version }}
      
      - name: Build
        run: go build -v ./...
      
      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: binary
          path: dist/
```

### Reusable Workflow para Rust

```yaml
# .github/workflows/reusable-rust.yml
name: Reusable Rust CI

on:
  workflow_call:
    inputs:
      rust-version:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: ${{ inputs.rust-version }}
      
      - name: Test
        run: cargo test --verbose

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: ${{ inputs.rust-version }}
      
      - name: Build
        run: cargo build --release
      
      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: binary
          path: target/release/
```

---

## 13.15 Reusable Workflows para Deploy

### Deploy para AWS

```yaml
# .github/workflows/reusable-deploy-aws.yml
name: Reusable Deploy AWS

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      region:
        required: false
        type: string
        default: 'us-east-1'
    secrets:
      AWS_ROLE_ARN:
        required: true

permissions:
  contents: read
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ inputs.region }}
      
      - name: Deploy to S3
        run: |
          aws s3 sync dist/ s3://my-bucket-${{ inputs.environment }}/
      
      - name: Invalidate CloudFront
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CLOUDFRONT_DIST_ID }} \
            --paths "/*"
```

### Deploy para Vercel

```yaml
# .github/workflows/reusable-deploy-vercel.yml
name: Reusable Deploy Vercel

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      VERCEL_TOKEN:
        required: true
      VERCEL_ORG_ID:
        required: true
      VERCEL_PROJECT_ID:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Vercel CLI
        run: npm install -g vercel
      
      - name: Pull Vercel Environment
        run: vercel pull --yes --environment=${{ inputs.environment }} --token=${{ secrets.VERCEL_TOKEN }}
      
      - name: Build
        run: vercel build --prod
      
      - name: Deploy
        run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
```

### Deploy para Cloudflare

```yaml
# .github/workflows/reusable-deploy-cloudflare.yml
name: Reusable Deploy Cloudflare

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      CLOUDFLARE_API_TOKEN:
        required: true
      CLOUDFLARE_ACCOUNT_ID:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build
        run: npm run build
      
      - name: Deploy to Cloudflare Pages
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy dist --project-name=my-project
```

---

## 13.16 Reusable Workflows para Containers

### Build e Push de Container

```yaml
# .github/workflows/reusable-container.yml
name: Reusable Container Build

on:
  workflow_call:
    inputs:
      image-name:
        required: true
        type: string
      tag:
        required: true
        type: string
      registry:
        required: false
        type: string
        default: 'ghcr.io'

permissions:
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ inputs.registry }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ inputs.registry }}/${{ inputs.image-name }}:${{ inputs.tag }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### Deploy de Container

```yaml
# .github/workflows/reusable-deploy-container.yml
name: Reusable Deploy Container

on:
  workflow_call:
    inputs:
      image:
        required: true
        type: string
      environment:
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Deploy container
        run: |
          echo "Deploying ${{ inputs.image }} to ${{ inputs.environment }}"
          # Deploy logic here
```

---

## 13.17 Reusable Workflows com Matrix

### Matrix com Reusable Workflows

```yaml
name: Matrix CI

on: [push]

jobs:
  test:
    strategy:
      matrix:
        node-version: [18, 20, 22]
        os: [ubuntu-latest, windows-latest]
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: ${{ matrix.node-version }}

  build:
    needs: test
    strategy:
      matrix:
        platform: [linux/amd64, linux/arm64]
    uses: ./.github/workflows/reusable-build.yml
    with:
      platform: ${{ matrix.platform }}
```

### Matrix com Condicionais

```yaml
name: Conditional Matrix

on: [push]

jobs:
  test:
    strategy:
      matrix:
        include:
          - node-version: 18
            os: ubuntu-latest
            test-command: 'npm test'
          - node-version: 20
            os: ubuntu-latest
            test-command: 'npm test -- --coverage'
          - node-version: 22
            os: windows-latest
            test-command: 'npm test'
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: ${{ matrix.node-version }}
      test-command: ${{ matrix.test-command }}
```

### Matrix com Fail Fast

```yaml
name: Matrix with Fail Fast

on: [push]

jobs:
  test:
    strategy:
      fail-fast: true
      matrix:
        node-version: [18, 20, 22]
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: ${{ matrix.node-version }}
```

---

## 13.18 Reusable Workflows com Error Handling

### Error Handling Basico

```yaml
name: CI with Error Handling

on: [push]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  build:
    needs: test
    if: always() && needs.test.result == 'success'
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  deploy:
    needs: build
    if: always() && needs.build.result == 'success'
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production

  notify:
    needs: [test, build, deploy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Notificar resultado
        run: |
          echo "Test: ${{ needs.test.result }}"
          echo "Build: ${{ needs.build.result }}"
          echo "Deploy: ${{ needs.deploy.result }}"
```

### Error Handling com Retry

```yaml
name: CI with Retry

on: [push]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  build:
    needs: test
    if: needs.test.result == 'success'
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  retry-build:
    needs: build
    if: failure()
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  deploy:
    needs: [build, retry-build]
    if: needs.build.result == 'success' || needs.retry-build.result == 'success'
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
```

### Error Handling com Cleanup

```yaml
name: CI with Cleanup

on: [push]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'

  build:
    needs: test
    uses: ./.github/workflows/reusable-build.yml
    with:
      node-version: '20'

  deploy:
    needs: build
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production

  cleanup:
    needs: [test, build, deploy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Cleanup
        run: |
          echo "Limpando recursos..."
          # Cleanup logic here
```

---

## 13.19 Reusable Workflows para Seguranca

### Security Scanning

```yaml
# .github/workflows/reusable-security.yml
name: Reusable Security Scan

on:
  workflow_call:
    inputs:
      scan-type:
        required: false
        type: string
        default: 'full'
        options:
          - full
          - quick

permissions:
  contents: read
  security-events: write

jobs:
  sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      
      - name: Analyze
        uses: github/codeql-action/analyze@v3

  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run npm audit
        run: npm audit --audit-level=high

  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Security Scan com Relatorio

```yaml
# .github/workflows/reusable-security-report.yml
name: Reusable Security Report

on:
  workflow_call:
    inputs:
      format:
        required: false
        type: string
        default: 'sarif'
        options:
          - sarif
          - json
          - text

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate security report
        run: |
          echo "Generating security report..."
          # Report generation logic here
      
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: report.*
```

---

## 13.20 Reusable Workflows para Multi-Cloud

### Deploy Multi-Cloud

```yaml
name: Multi-Cloud Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-aws:
    uses: ./.github/workflows/reusable-deploy-aws.yml
    with:
      environment: production
    secrets:
      AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}

  deploy-gcp:
    uses: ./.github/workflows/reusable-deploy-gcp.yml
    with:
      environment: production
    secrets:
      GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}

  deploy-azure:
    uses: ./.github/workflows/reusable-deploy-azure.yml
    with:
      environment: production
    secrets:
      AZURE_CREDENTIALS: ${{ secrets.AZURE_CREDENTIALS }}

  notify:
    needs: [deploy-aws, deploy-gcp, deploy-azure]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Notificar deploy multi-cloud
        run: |
          echo "AWS: ${{ needs.deploy-aws.result }}"
          echo "GCP: ${{ needs.deploy-gcp.result }}"
          echo "Azure: ${{ needs.deploy-azure.result }}"
```

---

## 13.21 Checklist de Reusable Workflows

### Checklist Completo

| Item | Status | Descricao |
|------|--------|-----------|
| Inputs tipados | OK/FAIL | Todos os inputs tem tipo definido |
| Defaults configurados | OK/FAIL | Inputs opcionais tem defaults |
| Secrets validados | OK/FAIL | Secrets obrigatorios validados |
| Outputs documentados | OK/FAIL | Outputs com descricoes |
| Permissions minimas | OK/FAIL | Least privilege configurado |
| Error handling | OK/FAIL | Tratamento de erros implementado |
| Versioning | OK/FAIL | Tags semanticas configuradas |
| Testes | OK/FAIL | Testes de integracao implementados |
| Documentacao | OK/FAIL | README atualizado |
| Seguranca | OK/FAIL | Security scanning habilitado |

---

## 13.22 Exemplos por Caso de Uso

### CI/CD para Frontend

```yaml
# .github/workflows/reusable-frontend.yml
name: Reusable Frontend CI/CD

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      environment:
        required: true
        type: string

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Lint
        run: |
          npm ci
          npm run lint

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Test
        run: |
          npm ci
          npm test

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Download
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      
      - name: Deploy
        run: |
          echo "Deploying to ${{ inputs.environment }}..."
```

### CI/CD para Backend API

```yaml
# .github/workflows/reusable-backend.yml
name: Reusable Backend CI/CD

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      environment:
        required: true
        type: string

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Test
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
        run: |
          npm ci
          npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Download
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      
      - name: Deploy
        run: |
          echo "Deploying API to ${{ inputs.environment }}..."
```

---

## 13.23 Melhores Praticas

### Top 10 Melhores Praticas

1. **Tipar todos os inputs** - Sempre definir tipo e descricao
2. **Usar defaults** - Configurar valores padrao para inputs opcionais
3. **Validar secrets** - Verificar se secrets obrigatorios existem
4. **Documentar outputs** - Fornecer descricoes claras
5. **Usar least privilege** - Definir permissoes minimas
6. **Implementar error handling** - Tratar falhas adequadamente
7. **Versionar com tags** - Usar versioning semantico
8. **Testar workflows** - Implementar testes de integracao
9. **Manter compatibilidade** - Preservar backward compatibility
10. **Documentar mudancas** - Manter CHANGELOG atualizado

### Padrao de Reusable Workflow

```yaml
# Template de reusable workflow
name: Reusable Template

on:
  workflow_call:
    inputs:
      required-input:
        required: true
        type: string
        description: 'Input obrigatorio'
      optional-input:
        required: false
        type: string
        default: 'default-value'
        description: 'Input opcional'
    outputs:
      result:
        description: 'Resultado do workflow'
        value: ${{ jobs.main.outputs.result }}
    secrets:
      REQUIRED_SECRET:
        required: true
        description: 'Secret obrigatorio'

permissions:
  contents: read

jobs:
  main:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.main.outputs.result }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Main step
        id: main
        run: |
          echo "result=success" >> $GITHUB_OUTPUT
```

---

## 13.25 Glossario

| Termo | Definicao |
|-------|-----------|
| Reusable Workflow | Workflow que pode ser chamado por outros |
| Caller Workflow | Workflow que chama um reusable workflow |
| workflow_call | Trigger para reusable workflows |
| Inputs | Parametros de entrada do workflow |
| Secrets | Dados sensiveis passados ao workflow |
| Outputs | Saidas do workflow |
| Composite Action | Action composta por multiplos steps |
| Organization Workflow | Workflow compartilhado na organizacao |
| Versioning | Controle de versoes do workflow |
| Backward Compatibility | Compatibilidade com versoes anteriores |
| Caller | Workflow que invoca outro workflow |
| Callee | Workflow que e invocado |
| Inheritance | Heranca de secrets do caller |
| Matrix | Combinacao de parametros |
| Artifact | Arquivo gerado durante o workflow |
| Service | Container auxiliar durante o job |
| Environment | Ambiente de deploy configurado |
| OIDC | OpenID Connect para autenticacao |

---

## 13.26 Tabelas de Resumo

### Tabela de Tipos de Reuse

| Tipo | Arquivo | Escopo | Secrets | Services |
|------|---------|--------|---------|----------|
| Reusable Workflow | .github/workflows/*.yml | Job completo | Sim | Sim |
| Composite Action | .github/actions/*/action.yml | Step | Nao | Nao |
| Reusable Workflow (org) | org/.github/workflows/*.yml | Job completo | Sim | Sim |

### Tabela de Input Types

| Tipo | Exemplo | Default | Obrigatorio |
|------|---------|---------|-------------|
| string | node-version: '20' | Sim | Configuravel |
| boolean | deploy: true | Sim | Configuravel |
| number | timeout: 30 | Sim | Configuravel |
| choice | environment: staging | Nao | Sim |

### Tabela de Melhores Praticas

| Pratica | Prioridade | Descricao |
|---------|------------|-----------|
| Tipar inputs | Alta | Sempre definir tipo |
| Usar defaults | Media | Valores padrao |
| Validar secrets | Alta | Verificar existencia |
| Documentar outputs | Media | Descricoes claras |
| Least privilege | Alta | Permissoes minimas |
| Error handling | Alta | Tratar falhas |
| Versioning | Media | Tags semanticas |
| Testing | Media | Testes de integracao |
| Compatibility | Media | Backward compat |
| Documentation | Baixa | CHANGELOG |

---

## 13.27 Referencias Finais

1. https://docs.github.com/en/actions/using-workflows/reusing-workflows
2. https://docs.github.com/en/actions/creating-actions/creating-a-composite-action
3. https://docs.github.com/en/actions/sharing-automations/creating-actions
4. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_iduses
5. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callinputs
6. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_callsecrets
7. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onworkflow_calloutputs
8. https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions
9. https://docs.github.com/en/actions/creating-actions/creating-a-composite-action
10. https://docs.github.com/en/actions/sharing-automations/creating-actions

---

## 13.28 Recursos Adicionais

### Links Uteis

- GitHub Actions Documentation: https://docs.github.com/en/actions
- Reusable Workflows: https://docs.github.com/en/actions/using-workflows/reusing-workflows
- Composite Actions: https://docs.github.com/en/actions/creating-actions/creating-a-composite-action
- Workflow Syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions

### Comunidades

- GitHub Actions Community: https://github.community/c/github-actions
- GitHub Community: https://github.community/

### Ferramentas

- Act: https://github.com/nektos/act
- Action Linter: https://github.com/rhysd/actionlint
- GitHub CLI: https://cli.github.com/

---

## 13.29 Changelog

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0 | 2024-01-01 | Versao inicial |
| 1.1 | 2024-02-01 | Adicionado organization-level |
| 1.2 | 2024-03-01 | Adicionado multi-cloud |
| 1.3 | 2024-04-01 | Adicionado containers |
| 1.4 | 2024-05-01 | Adicionado matrix |
| 1.5 | 2024-06-01 | Adicionado error handling |

---

## 13.30 Agradecimentos

Este capitulo foi desenvolvido com base em melhores praticas da comunidade de GitHub Actions e padroes de reutilizacao de workflows.

Agradecemos a todos os contribuidores que ajudaram a documentar essas praticas de reutilizacao de workflows.
---

*[Capítulo anterior: 12 — Harden Runners](12-harden-runners.md)*
*[Próximo capítulo: 14 — Monorepos](14-monorepos.md)*
