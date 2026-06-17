---
layout: default
title: "17-boas-praticas"
---

# Capitulo 17 -- Boas Praticas e Checklist

> *"Checklists previnem erros. Anti-patterns causam erros."*

---

## Objetivos de Aprendizado

1. Identificar e evitar 20+ anti-patterns comuns
2. Aplicar checklist de seguranca completa
3. Usar decision trees para decisoes de CI/CD
4. Criar templates padrao para CI e CD
5. Configurar Dependabot para atualizacoes automaticas
6. Conhecer as actions mais populares e seus usos
7. Dominar contexts e expressions do GitHub Actions
8. Implementar padroes de workflow robustos
9. Configurar branch protection rules
10. Aplicar least-privilege em permissoes
11. Implementar versionamento de workflows
12. Configurar environments com protection rules
13. Aplicar padroes de naming convention
14. Implementar reusable workflows eficientes
15. Configurar monitoring e alerting

---

## 17.1 Anti-Patterns

### Tabela Completa de Anti-Patterns

| # | Anti-Pattern | Problema | Solucao |
|---|-------------|----------|---------|
| 1 | Sem permissions explicitas | Token com permissao excessiva | Definir permissions por workflow/job |
| 2 | Secrets em logs | Vazamento de dados | Usar env vars, nunca echo secrets |
| 3 | Sem pin de actions | Supply chain attack | Pin por SHA, nao por tag |
| 4 | Sem timeout | Jobs pendentes infinitamente | Configurar timeout-minutes |
| 5 | Sem cache | Builds lentos e caros | Usar actions/cache |
| 6 | Sem concurrency | Workflows duplicados | Configurar concurrency groups |
| 7 | Sem path filters | Builds desnecessarios | Usar paths filter |
| 8 | Matrix enorme | Custo alto | Usar max-parallel e exclude |
| 9 | Sem test reporting | Falta de visibilidade | Usar test reporter actions |
| 10 | Branch protection off | Merge sem review | Configurar branch protection rules |
| 11 | Secrets hardcoded | Vazamento de credenciais | Usar GitHub Secrets |
| 12 | Sem dependabot | Actions desatualizadas | Configurar Dependabot |
| 13 | Logs sem agrupamento | Dificuldade de debug | Usar ::group:: |
| 14 | Sem retry | Falhas transitorias | Implementar retry logica |
| 15 | Deploy sem approval | Deploy sem validacao | Configurar environment protection |
| 16 | Sem rollback plan | Sem recuperacao | Implementar rollback automatico |
| 17 | Monorepo sem filters | Builds completos sempre | Configurar path filters |
| 18 | Sem status checks | Merge com falhas | Configurar required status checks |
| 19 | Runner sem hardening | Vunerabilidades | Usar hardening patterns |
| 20 | Sem audit trail | Falta de rastreabilidade | Configurar audit logging |
| 21 | Secrets compartilhados | Acesso excessivo | Usar environment secrets |
| 22 | Workflow gigante | Dificuldade de manutencao | Decompor em reusable workflows |
| 23 | Sem retry em rede | Falhas transitorias | Implementar backoff exponencial |
| 24 | Sem versionamento | Breaking changes | Versionar workflows com tags |
| 25 | Sem artifact cleanup | Consumo de armazenamento | Configurar retention-days |

### Anti-Pattern 1: Sem Permissions

```yaml
# ERRADO - permissao padrao e muito ampla
name: Bad CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

# CORRETO - permissions minimas
name: Good CI
on: [push]
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
```

### Anti-Pattern 2: Secrets em Logs

```yaml
# ERRADO - expose secret
steps:
  - run: echo "Token: ${{ secrets.MY_SECRET }}"

# CORRETO - usar env var
steps:
  - run: echo "Token is set: ${{ secrets.MY_SECRET != '' }}"
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}
```

### Anti-Pattern 3: Sem Pin de Actions

```yaml
# ERRADO - tag movel
- uses: actions/checkout@v4

# CORRETO - SHA fixo
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
  with:
    ref: v4.1.1
```

### Anti-Pattern 4: Sem Timeout

```yaml
# ERRADO - sem timeout
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: long-running-command

# CORRETO - timeout configurado
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - run: long-running-command
```

### Anti-Pattern 5: Sem Cache

```yaml
# ERRADO - reinstala tudo
steps:
  - uses: actions/setup-node@v4
    with:
      node-version: '20'
  - run: npm ci

# CORRETO - com cache
steps:
  - uses: actions/setup-node@v4
    with:
      node-version: '20'
      cache: 'npm'
  - run: npm ci
```

### Anti-Pattern 6: Sem Concurrency

```yaml
# ERRADO - execucoes duplicadas
on: push

# CORRETO - concurrency group
on: push
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Anti-Pattern 7: Sem Path Filters

```yaml
# ERRADO - roda para qualquer mudanca
on:
  push:
    branches: [main]

# CORRETO - filtra por paths
on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'package.json'
      - 'tsconfig.json'
    paths-ignore:
      - 'docs/**'
      - '**.md'
```

### Anti-Pattern 8: Matrix Enorme

```yaml
# ERRADO - matrix gigante
strategy:
  matrix:
    os: [ubuntu-latest, ubuntu-22.04, ubuntu-20.04, windows-latest, macos-latest]
    node: [14, 16, 18, 20, 22]
    # = 15 combinacoes!

# CORRETO - matrix otimizada
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node: [18, 20]
  fail-fast: true
  max-parallel: 3
```

### Anti-Pattern 9: Sem Test Reporting

```yaml
# ERRADO - sem visibilidade de testes
steps:
  - run: npm test

# CORRETO - com test reporting
steps:
  - run: npm test -- --reporter=junit --output-file=test-results.xml
  - uses: dorny/test-reporter@v1
    if: always()
    with:
      name: Test Results
      path: test-results.xml
      reporter: java-junit
```

### Anti-Pattern 10: Branch Protection Off

```yaml
# Configuracao recomendada via GitHub Settings:
# Settings > Branches > Add rule
#
# Branch name pattern: main
# [x] Require pull request reviews before merging
#     Required approving reviews: 1
# [x] Require status checks to pass before merging
#     Required: build, test
# [x] Require branches to be up to date before merging
# [x] Require conversation resolution before merging
# [x] Require linear history
# [ ] Include administrators (recomendado: ativar)
```

---

## 17.2 Checklist de Seguranca

### Checklist Completo

```markdown
## Seguranca de GitHub Actions

### Token e Permissoes
- [ ] Permissions configuradas (least-privilege)
- [ ] GITHUB_TOKEN com permissao minima necessaria
- [ ] Secrets usando env vars, nao inline
- [ ] Secrets nao hardcoded no workflow
- [ ] Environment secrets para deploys
- [ ] OIDC para cloud deploy (sem long-lived secrets)
- [ ] Audit log monitorado

### Actions e Dependencias
- [ ] Actions pinadas por SHA
- [ ] Dependabot para actions updates
- [ ] Dependabot para dependencias de codigo
- [ ] Renovate configurado (alternativa ao Dependabot)
- [ ] Supply chain attack mitigado

### Branch Protection
- [ ] Branch protection rules ativas
- [ ] Required reviews configurados
- [ ] Status checks obrigatorios definidos
- [ ] Conversations resolution obrigatorio
- [ ] Linear history obrigatorio

### Runners
- [ ] Self-hosted runners ephemeral
- [ ] Runners hardening aplicado
- [ ] Docker-in-Docker seguro
- [ ] Runner labels restritivos

### Workflow
- [ ] Concurrency groups habilitados
- [ ] Timeout configurado em todos os jobs
- [ ] Cache configurado corretamente
- [ ] Path filters para monorepos
- [ ] Environment protection rules
- [ ] Rollback plan documentado

### Monitoring
- [ ] Notificacoes configuradas
- [ ] Status badges atualizados
- [ ] Alertas de falha ativos
- [ ] SLA monitoring configurado
```

### Security Scanning

```yaml
name: Security Scan

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  codeql:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3

  dependency-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
```

---

## 17.3 Decision Trees

### Qual Trigger Usar?

```
Push para branch? --> push
PR aberto? --> pull_request
Manual? --> workflow_dispatch
Agendado? --> schedule
Outro workflow completou? --> workflow_run
Release criado? --> release
Issue criado/comentado? --> issues
PR comentado? --> pull_request_review
Discussion criada? --> discussion
Package publicado? --> registry_package
Git tag criado? --> push (com tags filter)
```

### Self-Hosted vs GitHub-Hosted?

```
Projeto pequeno? --> GitHub-hosted
Precisa de hardware especial? --> Self-hosted
Custo e prioridade? --> Self-hosted
Seguranca e prioridade? --> GitHub-hosted
Precisa de OS especifico? --> Self-hosted
Ambiente controlado necessario? --> Self-hosted
Pipeline simples? --> GitHub-hosted
```

### Cache Strategy?

```
Node.js? --> actions/setup-node com cache
Python? --> actions/setup-python com cache
Go? --> actions/setup-go com cache
Docker? --> docker/build-push-action com cache
Custom? --> actions/cache com key especifica
Monorepo? --> actions/cache com key por package
```

### Deploy Strategy?

```
Simples? --> deploy direto com actions
Multi-ambiente? --> environment protection rules
Blue-green? --> deploy com traffic shift
Canary? --> deploy com percentage
Rolling? --> matrix com max-parallel: 1
```

### Notification Strategy?

```
Simples? --> email built-in
Time usa Slack? --> slack-github-action
Time usa Discord? --> action-discord
Multi-canal? --> multi-step notification
Escalacao? --> PagerDuty/OpsGenie integration
```

### Testing Strategy?

```
Unit tests? --> npm test / pytest / go test
Integration tests? --> services containers
E2E tests? --> playwright / cypress
Load tests? --> k6 / artillery
Security tests? --> codeql / snyk
```

---

## 17.4 Templates

### CI Template - Node.js

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
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
      - run: npm run typecheck

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
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v4
        if: always()
        with:
          files: ./coverage/lcov.info

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
          retention-days: 7
```

### CI Template - Python

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  test:
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.12'
```

### CD Template

```yaml
name: Deploy

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: deploy-${{ inputs.environment || github.event.release.tag_name }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment || 'production' }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist/

  publish:
    needs: deploy
    runs-on: ubuntu-latest
    environment:
      name: production
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### Release Template

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
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
      - run: npm run build
      - run: npm test

      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: dist/*
```

---

## 17.5 Dependabot Configuration

### Dependabot para GitHub Actions

```yaml
# .github/dependabot.yml
version: 2
updates:
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Sao_Paulo"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "ci"
    reviewers:
      - "myorg/team-devops"
    groups:
      actions:
        patterns:
          - "actions/*"
          - "github/*"
```

### Dependabot para npm

```yaml
# .github/dependabot.yml
version: 2
updates:
  # npm dependencies
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "npm"
    commit-message:
      prefix: "deps"
    open-pull-requests-limit: 10
    reviewers:
      - "myorg/team-backend"
    groups:
      dev-dependencies:
        dependency-type: "development"
        patterns:
          - "*"
      production-dependencies:
        dependency-type: "production"
        patterns:
          - "*"
    ignore:
      - dependency-name: "@types/*"
        update-types: ["version-update:semver-patch"]
```

### Dependabot para Docker

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"
```

### Dependabot para pip

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "python"
```

### Dependabot com Security Alerts

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    # Dependabot tambem cria PRs para security updates automaticamente
    # Configurar em: Settings > Code security and analysis
```

### Auto-Merge para Dependabot

```yaml
name: Dependabot Auto-Merge

on:
  pull_request:

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

---

## 17.6 Popular Actions Reference

### Tabela de Actions Populares

| Action | Uso | Versao Recomendada |
|--------|-----|-------------------|
| actions/checkout | Clone do repositorio | v4 |
| actions/setup-node | Setup Node.js | v4 |
| actions/setup-python | Setup Python | v5 |
| actions/setup-java | Setup Java | v4 |
| actions/setup-go | Setup Go | v5 |
| actions/setup-dotnet | Setup .NET | v4 |
| actions/cache | Cache de dependencias | v4 |
| actions/upload-artifact | Upload de artifacts | v4 |
| actions/download-artifact | Download de artifacts | v4 |
| actions/upload-pages-artifact | Upload para GitHub Pages | v3 |
| actions/deploy-pages | Deploy para GitHub Pages | v4 |
| docker/build-push-action | Build e push de Docker | v5 |
| docker/setup-buildx-action | Setup Docker Buildx | v3 |
| codecov/codecov-action | Code coverage upload | v4 |
| softprops/action-gh-release | Criar releases | v2 |
| slackapi/slack-github-action | Notificacoes Slack | v1 |
| github/codeql-action | Security analysis | v3 |
| dependabot/fetch-metadata | Dependabot metadata | v2 |
| dorny/paths-filter | Changed files detection | v3 |
| dorny/test-reporter | Test report generation | v1 |
| tj-actions/changed-files | List changed files | v45 |
| aws-actions/configure-aws-credentials | AWS OIDC | v4 |
| aws-actions/amazon-ecr-login | ECR login | v2 |
| google-github-actions/auth | GCP auth | v2 |
| google-github-actions/deploy-cloudrun | Cloud Run deploy | v2 |
| azure/login | Azure login | v2 |
| azure/webapps-deploy | Azure Web App deploy | v3 |
| hashicorp/setup-terraform | Setup Terraform | v3 |
| actions/github-script | GitHub API via script | v7 |
| peter-evans/create-pull-request | Create PR programmatically | v6 |

### Exemplos de Uso

```yaml
# actions/checkout
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
  with:
    fetch-depth: 0  # Full clone
    token: ${{ secrets.GITHUB_TOKEN }}

# actions/setup-node
- uses: actions/setup-node@60edb5dd545a775178f525247833660a0683627d
  with:
    node-version: '20'
    cache: 'npm'
    registry-url: 'https://registry.npmjs.org'

# actions/cache
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      node_modules
    key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-npm-

# docker/build-push-action
- uses: docker/build-push-action@v5
  with:
    context: .
    push: true
    tags: user/app:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max

# actions/upload-artifact
- uses: actions/upload-artifact@v4
  with:
    name: my-artifact
    path: dist/
    retention-days: 7
    compression-level: 6

# actions/github-script
- uses: actions/github-script@v7
  with:
    script: |
      const { data: issue } = await github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'Automated Issue',
        body: 'Created by GitHub Actions'
      });
      console.log(`Created issue: ${issue.html_url}`);
```

---

## 17.7 Contexts Reference

### Tabela de Contexts

| Context | Descricao | Exemplo |
|---------|-----------|---------|
| github | Evento e dados do repositorio | github.event_name, github.ref |
| env | Variaveis de ambiente | env.NODE_VERSION |
| vars | Variaveis do repositorio | vars.APP_NAME |
| secrets | Secrets | secrets.AWS_KEY |
| needs | Outputs de jobs | needs.build.outputs.version |
| matrix | Valor da matrix | matrix.os |
| inputs | Inputs do workflow_dispatch | inputs.environment |
| runner | Dados do runner | runner.os, runner.name |
| strategy | Dados da strategy | strategy.fail-fast |
| job | Dados do job | job.status |
| steps | Outputs dos steps | steps.build.outputs.result |
| hashFiles | Hash de arquivos | hashFiles('**/package-lock.json') |

### github Context Completo

```yaml
steps:
  - name: GitHub context
    run: |
      echo "github.action = ${{ github.action }}"
      echo "github.action_path = ${{ github.action_path }}"
      echo "github.action_ref = ${{ github.action_ref }}"
      echo "github.action_repository = ${{ github.action_repository }}"
      echo "github.actor = ${{ github.actor }}"
      echo "github.actor_id = ${{ github.actor_id }}"
      echo "github.api_url = ${{ github.api_url }}"
      echo "github.base_ref = ${{ github.base_ref }}"
      echo "github.event = ${{ github.event }}"
      echo "github.event_name = ${{ github.event_name }}"
      echo "github.event_path = ${{ github.event_path }}"
      echo "github.head_ref = ${{ github.head_ref }}"
      echo "github.job = ${{ github.job }}"
      echo "github.ref = ${{ github.ref }}"
      echo "github.ref_name = ${{ github.ref_name }}"
      echo "github.ref_protected = ${{ github.ref_protected }}"
      echo "github.ref_type = ${{ github.ref_type }}"
      echo "github.repository = ${{ github.repository }}"
      echo "github.repository_owner = ${{ github.repository_owner }}"
      echo "github.run_id = ${{ github.run_id }}"
      echo "github.run_number = ${{ github.run_number }}"
      echo "github.server_url = ${{ github.server_url }}"
      echo "github.sha = ${{ github.sha }}"
      echo "github.token = ${{ github.token }}"
      echo "github.workspace = ${{ github.workspace }}"
```

### runner Context

```yaml
steps:
  - name: Runner context
    run: |
      echo "runner.arch = ${{ runner.arch }}"
      echo "runner.debug = ${{ runner.debug }}"
      echo "runner.name = ${{ runner.name }}"
      echo "runner.os = ${{ runner.os }}"
      echo "runner.temp = ${{ runner.temp }}"
      echo "runner.tool_cache = ${{ runner.tool_cache }}"
```

### needs Context

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
    steps:
      - id: version
        run: echo "value=1.0.0" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Build result: ${{ needs.build.result }}"
          echo "Build version: ${{ needs.build.outputs.version }}"
```

---

## 17.8 Expressions Reference

### Comparacao

```yaml
if: github.event_name == 'push'
if: github.ref != 'refs/heads/main'
if: runner.os == 'Linux'
if: matrix.node-version == '20'
```

### Logica

```yaml
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
if: github.event_name == 'pull_request' || github.event_name == 'push'
if: !(github.event_name == 'schedule')
if: github.ref == 'refs/heads/main' && !cancelled()
```

### Funcoes

```yaml
# contains
if: contains(github.event.pull_request.title, '[deploy]')

# startsWith
if: startsWith(github.ref, 'refs/tags/v')

# endsWith
if: endsWith(github.event.pull_request.head.ref, '-staging')

# format
run: echo "${{ format('Hello {0}', github.actor) }}"

# join
run: echo "${{ join(matrix.os, ', ') }}"

# toJSON / fromJSON
run: echo "${{ fromJSON('{\"key\": \"value\"}').key }}"

# hashFiles
key: ${{ hashFiles('**/package-lock.json') }}

# success / failure / always / cancelled
if: success()
if: failure()
if: always()
if: cancelled()

# needs
if: needs.build.result == 'success'
```

### Operadores

```yaml
# Igualdade
==

# Desigualdade
!=

# Maior/Menor
>
<
>=
<=

# And
&&

# Or
||

# Not
!

# In
in
contains('hello world', 'hello')
```

---

## 17.9 Naming Conventions

### Workflow Names

```yaml
# Padrao recomendado: [Area]: [Descricao]
name: CI: Build and Test
name: CD: Deploy to Production
name: Security: CodeQL Analysis
name: Release: Publish to npm
name: Ops: Scheduled Cleanup
```

### Job Names

```yaml
# Padrao recomendado: [acao]-[target]
jobs:
  lint-typescript:
    runs-on: ubuntu-latest

  test-unit:
    runs-on: ubuntu-latest

  build-docker:
    runs-on: ubuntu-latest

  deploy-staging:
    runs-on: ubuntu-latest

  notify-slack:
    runs-on: ubuntu-latest
```

### Step Names

```yaml
steps:
  - name: Checkout repository
    uses: actions/checkout@v4

  - name: Setup Node.js 20
    uses: actions/setup-node@v4
    with:
      node-version: '20'

  - name: Install dependencies
    run: npm ci

  - name: Run linter
    run: npm run lint

  - name: Run unit tests
    run: npm test

  - name: Build application
    run: npm run build

  - name: Upload build artifacts
    uses: actions/upload-artifact@v4
```

### File Naming

```
.github/workflows/
  ci.yml                    # CI principal
  cd.yml                    # CD principal
  release.yml               # Release automation
  security.yml              # Security scanning
  docs.yml                  # Documentacao
  scheduled.yml             # Tarefas agendadas
  reusable-ci.yml           # Reusable workflow de CI
  reusable-deploy.yml       # Reusable workflow de deploy
```

---

## 17.10 Environment Configuration

### Environment Protection Rules

```yaml
# Configuracao via GitHub Settings:
# Settings > Environments > New environment
#
# Environment: production
# [x] Required reviewers
#     - myorg/team-leads
# [x] Wait timer
#     - 5 minutes
# [x] Deployment branches
#     - Selected branches: main
# [x] Environment secrets
#     - DEPLOY_TOKEN: ****
# [x] Environment variables
#     - APP_URL: https://app.example.com
```

### Environment com OIDC

```yaml
name: Deploy with OIDC

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1

      - name: Deploy
        run: aws s3 sync dist/ s3://my-bucket/
```

---

## 17.11 Reusable Workflow Patterns

### Base Reusable Workflow

```yaml
# .github/workflows/reusable-base.yml
name: Reusable Base

on:
  workflow_call:
    inputs:
      node-version:
        required: false
        type: string
        default: '20'
      working-directory:
        required: false
        type: string
        default: '.'
    outputs:
      test-result:
        description: "Resultado dos testes"
        value: ${{ jobs.test.outputs.result }}
    secrets:
      CODECOV_TOKEN:
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ${{ inputs.working-directory }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'
          cache-dependency-path: ${{ inputs.working-directory }}/package-lock.json
      - run: npm ci
      - run: npm test
```

### Caller Pattern

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  core:
    uses: ./.github/workflows/reusable-base.yml
    with:
      node-version: '20'
      working-directory: packages/core
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}

  api:
    uses: ./.github/workflows/reusable-base.yml
    with:
      node-version: '20'
      working-directory: packages/api
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

---

## 17.12 Branch Protection Rules

### Configuracao Recomendada

```yaml
# Settings > Branches > Add rule
#
# Branch name pattern: main
#
# === Protect matching branches ===
# [x] Require a pull request before merging
#     [x] Require approvals: 1
#     [x] Dismiss stale pull request approvals when new commits are pushed
#     [x] Require review from Code Owners
#
# [x] Require status checks to pass before merging
#     [x] Require branches to be up to date before merging
#     Required status checks:
#       - lint
#       - test
#       - build
#
# [x] Require conversation resolution before merging
# [x] Require linear history
#
# === Restrict who can push to matching branches ===
# [ ] Restrict pushes that create matching branches
# [ ] Require a pull request before merging (for admin)
#
# [x] Include administrators
# [x] Allow force pushes (optional)
# [x] Allow deletions (optional)
```

### Status Checks via API

```bash
# Listar status checks disponiveis
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/branches/main/protection"

# Configurar status checks obrigatorios
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/branches/main/protection" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["lint", "test", "build"]
    },
    "enforce_admins": true,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews": true
    },
    "restrictions": null
  }'
```

---

## 17.13 Workflow Versioning

### Versionamento com Tags

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'workflow-v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
```

### Uso de Workflows Versionados

```yaml
# Chamar workflow versionado
jobs:
  ci:
    uses: myorg/shared-workflows/.github/workflows/ci.yml@workflow-v1
    with:
      node-version: '20'
```

### Breaking Changes Policy

```markdown
## Workflow Versioning Policy

### Semver para Workflows
- **Major (v1 -> v2)**: Breaking changes (inputs removidos, outputs alterados)
- **Minor (v1.0 -> v1.1)**: Novos inputs opcionais, novas features
- **Patch (v1.0.0 -> v1.0.1)**: Bug fixes, correcoes internas

### Deprecation Policy
1. Nova versao disponibilizada com novo input de compatibilidade
2. Versao antiga continua funcionando por 3 meses
3. Aviso de deprecation no release notes
4. Apos 3 meses, versao antiga e removida
```

---

## 17.14 Workflow Organization

### Estrutura de Diretorios

```
.github/
  workflows/
    # Workflows principais
    ci.yml
    cd.yml
    release.yml

    # Workflows reutilizaveis
    reusable/
      ci-base.yml
      deploy.yml
      notify.yml

    # Workflows agendados
    scheduled/
      cleanup.yml
      dependency-review.yml

    # Composite actions locais
  actions/
    setup-project/
      action.yml
    deploy-app/
      action.yml

  # Dependabot
  dependabot.yml

  # CODEOWNERS
  CODEOWNERS
```

### CODEOWNERS

```
# .github/CODEOWNERS

# Global
* @myorg/team-leads

# Frontend
/packages/web/ @myorg/team-frontend
*.tsx @myorg/team-frontend
*.css @myorg/team-frontend

# Backend
/packages/api/ @myorg/team-backend
*.go @myorg/team-backend

# Infrastructure
/.github/ @myorg/team-devops
/Dockerfile @myorg/team-devops
/docker-compose*.yml @myorg/team-devops
```

---

## 17.15 Checklist Pre-Deploy

### Checklist Completo

```markdown
## Pre-Deploy Checklist

### Codigo
- [ ] Todos os testes passando
- [ ] Lint sem erros
- [ ] Type check sem erros
- [ ] Coverage minimo atingido
- [ ] Security scan sem alertas criticos
- [ ] Code review aprovado

### Configuracao
- [ ] Environment secrets configurados
- [ ] Environment variables configuradas
- [ ] Feature flags configuradas
- [ ] Rate limiting configurado
- [ ] CORS configurado

### Infraestrutura
- [ ] Database migrations testadas
- [ ] Cache invalidation planejada
- [ ] CDN configurado
- [ ] SSL certificates validos
- [ ] DNS configurado

### Monitoring
- [ ] Logging configurado
- [ ] Metrics configuradas
- [ ] Alerts configurados
- [ ] Dashboards atualizados
- [ ] Runbooks atualizados

### Rollback
- [ ] Rollback plan documentado
- [ ] Rollback testado
- [ ] Database rollback scripts prontos
- [ ] Feature flags para rollback
- [ ] Communication plan pronto
```

---

## 17.16 Workflows Avancados

### Matrix com Condicoes

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
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [18, 20, 22]
        include:
          - os: ubuntu-latest
            node: 20
            experimental: true
        exclude:
          - os: windows-latest
            node: 18
      fail-fast: false
      max-parallel: 4
    continue-on-error: ${{ matrix.experimental || false }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci && npm test
```

### Conditional Jobs

```yaml
name: Conditional Jobs

on:
  push:
    branches: [main]

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      frontend: ${{ steps.changes.outputs.frontend }}
      backend: ${{ steps.changes.outputs.backend }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            frontend:
              - 'packages/web/**'
            backend:
              - 'packages/api/**'

  test-frontend:
    needs: detect
    if: needs.detect.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/web && npm ci && npm test

  test-backend:
    needs: detect
    if: needs.detect.outputs.backend == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/api && npm ci && npm test
```

### Job Outputs

```yaml
name: Job Outputs

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
      artifact-url: ${{ steps.upload.outputs.artifact-url }}
    steps:
      - id: version
        run: echo "value=$(jq -r .version package.json)" >> "$GITHUB_OUTPUT"
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - id: upload
        uses: actions/upload-artifact@v4
        with:
          name: dist-${{ steps.version.outputs.value }}
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying version ${{ needs.build.outputs.version }}"
```

### Workflow Dispatch com Inputs

```yaml
name: Workflow Dispatch

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Version to deploy'
        required: true
        type: string
      dry-run:
        description: 'Dry run'
        required: false
        type: boolean
        default: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      - run: |
          echo "Environment: ${{ inputs.environment }}"
          echo "Version: ${{ inputs.version }}"
          echo "Dry run: ${{ inputs.dry-run }}"
```

### Reusable Workflow com Outputs

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

on:
  workflow_call:
    inputs:
      package:
        required: true
        type: string
    outputs:
      test-result:
        description: "Test result"
        value: ${{ jobs.test.outputs.result }}
      coverage:
        description: "Coverage percentage"
        value: ${{ jobs.test.outputs.coverage }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.test.outputs.result }}
      coverage: ${{ steps.test.outputs.coverage }}
    steps:
      - uses: actions/checkout@v4
      - run: cd packages/${{ inputs.package }} && npm ci && npm test
      - id: test
        run: echo "result=success" >> "$GITHUB_OUTPUT"
```

### Composite Action com Multiplos Steps

```yaml
# .github/actions/setup-project/action.yml
name: Setup Project
description: Setup completo do projeto

inputs:
  node-version:
    description: "Node.js version"
    required: false
    default: '20'
  install-deps:
    description: "Install dependencies"
    required: false
    default: 'true'

runs:
  using: composite
  steps:
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'

    - name: Install dependencies
      if: inputs.install-deps == 'true'
      shell: bash
      run: npm ci

    - name: Verify installation
      shell: bash
      run: |
        echo "Node: $(node --version)"
        echo "NPM: $(npm --version)"
        echo "Dependencies installed: $([ -d node_modules ] && echo yes || echo no)"
```

---

## 17.17 Error Handling Patterns

### Retry with Backoff

```yaml
name: Retry Pattern

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy with retry
        run: |
          MAX_RETRIES=3
          RETRY_DELAY=30

          for i in $(seq 1 $MAX_RETRIES); do
            echo "Attempt $i of $MAX_RETRIES"

            if deploy-command; then
              echo "Deploy succeeded"
              exit 0
            fi

            if [ $i -lt $MAX_RETRIES ]; then
              DELAY=$((RETRY_DELAY * i))
              echo "Waiting ${DELAY}s before retry..."
              sleep $DELAY
            fi
          done

          echo "Deploy failed after $MAX_RETRIES attempts"
          exit 1
```

### Circuit Breaker

```yaml
name: Circuit Breaker

on:
  schedule:
    - cron: '*/5 * * * *'

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check service health
        id: health
        run: |
          HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.example.com/health)
          echo "http_code=$HTTP_CODE" >> "$GITHUB_OUTPUT"

          if [ "$HTTP_CODE" != "200" ]; then
            echo "Service unhealthy (HTTP $HTTP_CODE)"
            echo "unhealthy=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Alert on circuit open
        if: steps.health.outputs.unhealthy == 'true'
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Circuit breaker OPEN: service is unhealthy"}
```

### Graceful Degradation

```yaml
name: Graceful Degradation

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy with fallback
        run: |
          # Tentar deploy primario
          if deploy-primary; then
            echo "Primary deploy succeeded"
            exit 0
          fi

          echo "Primary deploy failed, trying fallback..."

          # Fallback secundario
          if deploy-secondary; then
            echo "Secondary deploy succeeded"
            exit 0
          fi

          echo "Both deploys failed"
          exit 1
```

---

## 17.18 Performance Optimization

### Parallel Jobs

```yaml
name: Parallel Execution

on:
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run lint

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test -- --grep "unit"

  test-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test -- --grep "integration"

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --audit-level=high
```

### Dependency Graph Optimization

```yaml
name: Optimized Pipeline

on:
  push:
    branches: [main]

jobs:
  # Phase 1: Fast checks (parallel)
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run lint

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run typecheck

  # Phase 2: Tests (after fast checks)
  test:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  # Phase 3: Build (after tests)
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

### Cache Strategy

```yaml
name: Optimized Cache

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Cache de nivel 1: npm cache
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      # Cache de nivel 2: build artifacts
      - name: Cache build
        uses: actions/cache@v4
        with:
          path: |
            dist/
            .next/
            .turbo/
          key: build-${{ runner.os }}-${{ github.sha }}
          restore-keys: |
            build-${{ runner.os }}-

      - run: npm ci
      - run: npm run build
```

### Artifact Optimization

```yaml
name: Artifact Optimization

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      # Upload apenas arquivos necessarios
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: |
            dist/**/*.js
            dist/**/*.css
            dist/**/*.html
            !dist/**/*.map
            !dist/**/*.test.*
          retention-days: 1
          compression-level: 9
```

---

## 17.19 Security Hardening

### Token Permissions

```yaml
name: Secure Workflow

on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - name: Deploy with OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/deploy
          aws-region: us-east-1
```

### Secret Management

```yaml
name: Secure Secrets

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      # Usar secrets via env, nunca inline
      - name: Deploy
        run: |
          echo "Deploying..."
          # NUNCA faca: echo ${{ secrets.MY_SECRET }}
          # CORRETO: usar via env
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      # NUNCA faca isso:
      # - run: echo "Token: ${{ secrets.MY_SECRET }}"
```

### Action Pinning

```yaml
name: Pinned Actions

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      # CORRETO: pin por SHA
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - uses: actions/setup-node@60edb5dd545a775178f525247833660a0683627d

      # Ainda aceitavel: pin por tag major
      # - uses: actions/checkout@v4

      # ERRADO: branch movel
      # - uses: actions/checkout@main
```

### Input Validation

```yaml
name: Input Validation

on:
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        required: true
        type: string

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Validate inputs
        run: |
          # Validar environment
          if [[ ! "${{ inputs.environment }}" =~ ^(staging|production)$ ]]; then
            echo "::error::Invalid environment: ${{ inputs.environment }}"
            exit 1
          fi

          # Validar version format
          if [[ ! "${{ inputs.version }}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "::error::Invalid version format: ${{ inputs.version }}"
            exit 1
          fi

          echo "Inputs validated successfully"
```

---

## 17.20 Monitoring and Observability

### Structured Logging

```yaml
name: Structured Logging

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build with structured logs
        run: |
          echo "::group::Build Configuration"
          echo "node_version=20"
          echo "npm_version=$(npm --version)"
          echo "platform=$(uname -s)"
          echo "::endgroup::"

          echo "::group::Build Steps"
          START=$(date +%s%N)
          npm ci
          END=$(date +%s%N)
          echo "npm_ci_ms=$(( (END - START) / 1000000 ))"

          START=$(date +%s%N)
          npm run build
          END=$(date +%s%N)
          echo "build_ms=$(( (END - START) / 1000000 ))"
          echo "::endgroup::"

      - name: Build summary
        run: |
          echo "## Build Summary" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Step | Duration |" >> "$GITHUB_STEP_SUMMARY"
          echo "|------|----------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Install | ~30s |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Build | ~45s |" >> "$GITHUB_STEP_SUMMARY"
```

### Metrics Collection

```yaml
name: Metrics Collection

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Collect metrics
        run: |
          METRICS="github_actions_runs_total{workflow=\"${{ github.event.workflow_run.name }}\",conclusion=\"${{ github.event.workflow_run.conclusion }}\"} 1"
          echo "$METRICS"

          # Push to Prometheus Pushgateway
          # curl -X POST --data-binary @- http://pushgateway:9091/metrics/job/ci
```

### Alerting Rules

```yaml
name: Alerting

on:
  workflow_run:
    workflows: ["CI", "CD"]
    types: [completed]

jobs:
  alert:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      - name: Determine alert severity
        id: severity
        run: |
          WORKFLOW="${{ github.event.workflow_run.name }}"

          if [[ "$WORKFLOW" == *"deploy"* ]] || [[ "$WORKFLOW" == *"production"* ]]; then
            echo "level=critical" >> "$GITHUB_OUTPUT"
          elif [[ "$WORKFLOW" == *"release"* ]]; then
            echo "level=warning" >> "$GITHUB_OUTPUT"
          else
            echo "level=info" >> "$GITHUB_OUTPUT"
          fi

      - name: Send alert
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "${{ steps.severity.outputs.level == 'critical' && ':rotating_light:' || ':warning:' }} Workflow failed: ${{ github.event.workflow_run.name }}"
            }
```

---

## 17.21 Multi-Cloud Deploy Patterns

### AWS Deploy

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1

      - name: Deploy to S3
        run: aws s3 sync dist/ s3://my-bucket/ --delete

      - name: Invalidate CloudFront
        run: aws cloudfront create-invalidation --distribution-id E1234567890 --paths "/*"
```

### GCP Deploy

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Auth GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
          service_account: github-actions@my-project.iam.gserviceaccount.com

      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: my-service
          region: us-central1
          image: gcr.io/my-project/my-app:latest
```

### Azure Deploy

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: my-app
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
          package: dist/
```

---

## 17.22 Disaster Recovery

### Backup Workflow

```yaml
name: Backup

on:
  schedule:
    - cron: '0 2 * * *'  # Diario as 2h

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Backup repository
        run: |
          curl -L -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/tarball" \
            -o backup-$(date +%Y-%m-%d).tar.gz

      - name: Upload backup
        uses: actions/upload-artifact@v4
        with:
          name: backup-${{ github.sha }}
          path: backup-*.tar.gz
          retention-days: 30
```

### Rollback Workflow

```yaml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to rollback to'
        required: true
        type: string

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}

      - run: npm ci && npm run build

      - name: Deploy rollback
        run: |
          echo "Rolling back to version ${{ inputs.version }}"
          # Deploy logic here

      - name: Notify
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Rollback to ${{ inputs.version }} completed"}
```

---

## 17.23 Compliance and Audit

### Audit Trail

```yaml
name: Audit Trail

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Log audit event
        run: |
          echo "## Audit Event" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Field | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|-------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Event | ${{ github.event_name }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Actor | ${{ github.actor }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Ref | ${{ github.ref }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| SHA | ${{ github.sha }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Time | $(date -u +%Y-%m-%dT%H:%M:%SZ) |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Run | ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }} |" >> "$GITHUB_STEP_SUMMARY"
```

### Compliance Check

```yaml
name: Compliance Check

on:
  pull_request:
    branches: [main]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check compliance
        run: |
          echo "## Compliance Check" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"

          # Check for secrets in code
          if grep -r "password\|secret\|token\|key" --include="*.ts" --include="*.js" src/ | grep -v "test\|mock\|example"; then
            echo "::warning::Potential secrets found in code"
            echo "| Check | Status |" >> "$GITHUB_STEP_SUMMARY"
            echo "|-------|--------|" >> "$GITHUB_STEP_SUMMARY"
            echo "| Secrets in code | WARNING |" >> "$GITHUB_STEP_SUMMARY"
          else
            echo "| Check | Status |" >> "$GITHUB_STEP_SUMMARY"
            echo "|-------|--------|" >> "$GITHUB_STEP_SUMMARY"
            echo "| Secrets in code | PASS |" >> "$GITHUB_STEP_SUMMARY"
          fi

          # Check for TODO/FIXME
          TODO_COUNT=$(grep -r "TODO\|FIXME" --include="*.ts" --include="*.js" src/ | wc -l)
          echo "| TODOs/FIXMEs | $TODO_COUNT |" >> "$GITHUB_STEP_SUMMARY"
```

---

## 17.24 Documentation as Code

### Auto-generated Docs

```yaml
name: Auto Documentation

on:
  push:
    branches: [main]
    paths:
      - 'src/**'

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate API docs
        run: |
          npm ci
          npx typedoc --out docs/api src/

      - name: Deploy docs
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/api
```

### Changelog Generation

```yaml
name: Changelog

on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate changelog
        run: |
          PREV_TAG=$(git describe --tags --abbrev=0 HEAD^)
          git log ${PREV_TAG}..HEAD --pretty=format:"- %s (%h)" --no-merges > CHANGELOG.md

      - name: Update release
        uses: softprops/action-gh-release@v2
        with:
          body_path: CHANGELOG.md
```

---

## 17.25 Exercicios

1. Implemente um workflow completo usando o template CI
2. Configure dependabot para npm e github-actions
3. Implemente notification Slack para builds que falharam
4. Crie checklist de seguranca para o seu projeto
5. Implemente reusable workflow de CI para reutilizar em multiplos repos
6. Configure branch protection rules com status checks
7. Implemente auto-merge para Dependabot PRs
8. Crie composite action para setup do projeto
9. Configure environment protection rules para production
10. Implemente security scanning com CodeQL
11. Implemente retry pattern com backoff exponencial
12. Configure circuit breaker para health checks
13. Implemente parallel jobs para otimizar tempo de build
14. Crie audit trail para compliance
15. Implemente disaster recovery com backup automatizado
16. Configure multi-cloud deploy (AWS/GCP/Azure)
17. Implemente structured logging com GITHUB_STEP_SUMMARY
18. Crie compliance check para pull requests
19. Implemente auto-generated documentation
20. Configure changelog generation automatizado

---

## 17.26 Migration Patterns

### Migrando de Travis CI

```yaml
# Travis CI (.travis.yml)
language: node_js
node_js:
  - "18"
script:
  - npm test
after_success:
  - npm run coveralls

# GitHub Actions equivalente
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
      - run: npm ci
      - run: npm test
      - uses: codecov/codecov-action@v4
        if: success()
```

### Migrando de CircleCI

```yaml
# CircleCI (.circleci/config.yml)
version: 2.1
jobs:
  build:
    docker:
      - image: cimg/node:18.0
    steps:
      - checkout
      - run: npm ci
      - run: npm test

# GitHub Actions equivalente
name: CI

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: node:18
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
```

### Migrando de Jenkins

```yaml
# Jenkinsfile
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'npm ci'
                sh 'npm run build'
            }
        }
        stage('Test') {
            steps {
                sh 'npm test'
            }
        }
    }
}

# GitHub Actions equivalente
name: CI

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
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - run: npm test
```

---

## 17.27 Checklist de Code Review

### Review de Workflow Files

```markdown
## Workflow Code Review Checklist

### Seguranca
- [ ] Permissions minimas configuradas
- [ ] Secrets nao hardcoded
- [ ] Actions pinadas por SHA
- [ ] Input validation implementada
- [ ] OIDC usado para cloud auth (não long-lived secrets)

### Funcionalidade
- [ ] Triggers corretos configurados
- [ ] Path filters adequados
- [ ] Concurrency groups configurados
- [ ] Timeouts apropriados
- [ ] Error handling implementado

### Performance
- [ ] Cache configurado
- [ ] Jobs paralelizados quando possivel
- [ ] Matrix otimizada
- [ ] Artifacts com retention adequada

### Manutencao
- [ ] Workflow names descritivos
- [ ] Step names claros
- [ ] Comments onde necessario
- [ ] Reusable workflows quando aplicavel
- [ ] Versionamento de workflows

### Testing
- [ ] Test reporting configurado
- [ ] Coverage upload ativo
- [ ] Test artifacts salvos
```

---

## 17.28 Troubleshooting Guide

### Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| `actions/checkout` falha | Branch/tag inexistente | Verificar ref, usar fetch-depth: 0 |
| Cache miss sempre | Key incorreta | Verificar hashFiles, usar restore-keys |
| Permission denied | Token sem permissao | Adicionar permissions no workflow |
| Timeout | Job demorando muito | Aumentar timeout-minutes ou otimizar |
| Action not found | Tag/SHA incorreta | Verificar versao da action |
| Secret undefined | Secret nao configurado | Configurar em Settings > Secrets |
| YAML parse error | Indentacao incorreta | Usar 2 espacos, validar com actionlint |
| Docker pull fail | Registry inacessivel | Verificar rede, usar mirror |
| Matrix empty | fromJSON retornando [] | Verificar outputs do job anterior |
| Workflow not trigger | paths filter muito restritivo | Verificar patterns de paths |

### Debug Commands

```bash
# Validar YAML
actionlint .github/workflows/*.yml

# Listar workflows
act -l

# Rodar com debug
ACTIONS_STEP_DEBUG=true act push

# Verificar permissoes
gh api repos/OWNER/REPO/permissions

# Listar secrets (nao valores)
gh secret list
```

---

## 17.29 Performance Benchmarks

### Metricas de Referencia

| Metrica | Bom | Medio | Ruim |
|---------|-----|-------|------|
| CI time (PR) | < 5 min | 5-15 min | > 15 min |
| CD time | < 3 min | 3-10 min | > 10 min |
| Cache hit rate | > 80% | 50-80% | < 50% |
| Success rate | > 95% | 85-95% | < 85% |
| MTTR | < 15 min | 15-60 min | > 60 min |

### Otimizacao de Performance

```yaml
name: Performance Optimized

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci --prefer-offline
      - run: npm run lint

  test:
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci --prefer-offline
      - run: npm test -- --forceExit --detectOpenHandles

  build:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci --prefer-offline
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1
          compression-level: 9
```

---

## 17.30 Referencias

1. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
2. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
3. https://github.com/topics/github-actions
4. https://docs.github.com/en/actions/learn-github-actions
5. https://docs.github.com/en/actions/using-workflows/reusing-workflows
6. https://docs.github.com/en/code-security/dependabot
7. https://github.com/sdras/awesome-actions
8. https://docs.github.com/en/actions/learn-github-actions/contexts
9. https://docs.github.com/en/actions/learn-github-actions/expressions
10. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
11. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/displaying-a-snapshot-of-differences-between-two-branches-or-commits
12. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-third-party-actions
13. https://docs.github.com/en/actions/learn-github-actions/variables#using-the-vars-context-to-access-variables
14. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency
15. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idtimeout-minutes
16. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstrategyfail-fast
17. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstrategymatrix
18. https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
19. https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows
20. https://docs.github.com/en/actions/hosting-your-own-runners
