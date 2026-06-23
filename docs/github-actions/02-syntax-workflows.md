---
layout: default
title: "02-syntax-workflows"
---

# Capitulo 2 — Syntax e Estrutura de Workflows

> *"O YAML e a lingua franca dos pipelines modernos."*

---

## Objetivos de Aprendizado

1. Dominar a estrutura YAML de workflows, incluindo todas as propriedades disponiveis
2. Configurar triggers detalhados com branches, paths, types e filters
3. Implementar jobs completos com dependencias, condicoes e outputs
4. Usar steps avancados com id, if, continue-on-error, shell e working-directory
5. Dominar expressions e contexts para logica condicional avancada
6. Implementar matrix strategies completas com include, exclude e max-parallel
7. Configurar concurrency groups para controle de execucoes simultaneas
8. Utilizar services detalhados com health checks e multiplas versoes
9. Configurar defaults para otimizar workflows repetitivos
10. Criar workflows completos seguindo boas praticas de estrutura

---

## 2.1 YAML Basico

### Estrutura Fundamental

Todo workflow GitHub Actions e um arquivo YAML com a seguinte estrutura basica:

```yaml
name: Nome do Workflow

on:
  push:
    branches: [main]

env:
  NODE_VERSION: '20'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "Hello"
```

### Regras de Sintaxe YAML

O GitHub Actions usa YAML 1.2 com algumas restricoes especificas:

| Regra | Descricao | Exemplo |
|-------|-----------|---------|
| Indentacao | 2 espacos (obrigatorio, sem tabs) | `jobs:\n  build:` |
| Strings | Aspas opcionais, mas recomendadas para valores problematicos | `node-version: '20'` |
| Booleanos | `true`/`false` (minusculo, sem aspas) | `continue-on-error: true` |
| Null | `null` ou omitir o valor | `env:` (vazio = null) |
| Sequencias | Hifen + espaco | `- item1\n- item2` |
| Mappings | Chave: valor | `key: value` |
| Multi-line literal | Pipe `|` (preserva quebras) | `run: |\n  echo "a"\n  echo "b"` |
| Multi-line folded | Seta `>` (quebras viram espacos) | `run: >\n  echo "a"\n  echo "b"` |
| Comentarios | Hash `#` | `# Isto e um comentario` |
| Anchors | `&` e `*` para reutilizar | `&defaults` / `*defaults` |
| Merge keys | `<<:` para combinar | `<<: *defaults` |

### Tipos de Dados

```yaml
# String
name: "Meu Workflow"
node-version: '20'

# Number
timeout-minutes: 30
max-parallel: 5

# Boolean
continue-on-error: true
fail-fast: false

# Null
env:  # Vazio, valor null

# Array (sequence)
branches: [main, develop]
options:
  - option1
  - option2

# Object (mapping)
env:
  KEY1: value1
  KEY2: value2
```

### Anchors e Merge Keys

YAML suporta anchors para reutilizar blocos de configuracao:

```yaml
# Definir defaults com anchor
_build_defaults: &build_defaults
  runs-on: ubuntu-latest
  timeout-minutes: 15
  env:
    NODE_VERSION: '20'

jobs:
  # Usar anchor com merge key
  build:
    <<: *build_defaults
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

  test:
    <<: *build_defaults
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  lint:
    <<: *build_defaults
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run lint
```

**Nota**: Anchors funcionam apenas dentro do mesmo arquivo YAML. Para reutilizar configuracoes entre arquivos, use reusable workflows ou composite actions.

### Erros Comuns de Sintaxe

```yaml
# ERRADO: Tab ao inves de espaco
jobs:
	build:  # Tab = ERRO
	  runs-on: ubuntu-latest

# ERRADO: Indentacao incorreta
jobs:
  build:
   runs-on: ubuntu-latest  # 1 espaco = ERRO
    steps:                  # 4 espacos = ERRO
      - run: echo "hello"

# ERRADO: String sem aspas onde e necessario
on:
  push:
    branches: [main]  # OK
    paths: ['src/**'] # OK com aspas

# ERRADO: Boolean com aspas
continue-on-error: 'true'  # String, nao boolean

# ERRADO: Valor nulo incorreto
env: ~  # Usar ~ e invalido em GitHub Actions
env:    # Deixe vazio ou use null
```

### YAML Folded vs Literal

```yaml
# Literal (|) - preserva quebras de linha
run: |
  echo "Linha 1"
  echo "Linha 2"
  echo "Linha 3"
# Resultado:
# echo "Linha 1"
# echo "Linha 2"
# echo "Linha 3"

# Folded (>) - converte quebras em espacos
run: >
  echo "Linha 1"
  echo "Linha 2"
  echo "Linha 3"
# Resultado:
# echo "Linha 1" echo "Linha 2" echo "Linha 3"

# Folded com strip (-) - remove newline final
run: >-
  echo "Linha 1"
  echo "Linha 2"
# Resultado:
# echo "Linha 1" echo "Linha 2" (sem newline final)

# Literal com keep (+) - preserva newlines vazios
run: |+
  echo "Linha 1"

  echo "Linha 3"
# Resultado:
# echo "Linha 1"
# (linha vazia preservada)
# echo "Linha 3"
```

---

## 2.2 Triggers Detalhados

### Visao Geral dos Triggers

O GitHub Actions suporta diversos tipos de triggers:

| Trigger | Descricao | Exemplo de uso |
|---------|-----------|----------------|
| `push` | Quando codigo e enviado | CI automatico |
| `pull_request` | Quando PR e criado/atualizado | Review checks |
| `pull_request_target` | PR no contexto do branch base | Forks seguros |
| `workflow_dispatch` | Manual via UI/API | Deploy manual |
| `workflow_call` | Chamado por outro workflow | Reusable workflows |
| `workflow_run` | Apos outro workflow completar | Pipelines encadeadas |
| `schedule` | Cron-based | Tarefas agendadas |
| `repository_dispatch` | Via API | Integracao externa |
| `release` | Quando release e criado | Deploy apos release |
| `deployment` | Quando deployment e criado | Deploy status |
| `issues` | Quando issue e criada/atualizada | Auto-labeling |
| `issue_comment` | Quando comentario e feito | Bot commands |
| `pull_request_review` | Quando review e submetido | Approval checks |
| `pull_request_review_comment` | Quando comentario em review | Feedback |
| `create` | Quando branch/tag e criada | Auto-tag |
| `delete` | Quando branch/tag e deletada | Cleanup |
| `fork` | Quando repo e forked | CI para forks |
| `gollum` | Quando wiki e atualizada | Wiki CI |
| `membership` | Quando membro e adicionado/removido | Team management |
| `page_build` | Quando GitHub Pages e construido | Pages CI |
| `project` | Quando project board e atualizado | Project automation |
| `project_card` | Quando card e movido | Notifications |
| `project_column` | Quando coluna e atualizada | Automation |
| `public` | Quando repo se torna publico | Security check |
| `registry_packages` | Quando package e publicado | Post-publish |
| `watch` | Quando repo recebe star | Thank you bot |

### push

O trigger `push` dispara quando codigo e enviado para branches ou tags:

```yaml
on:
  push:
    branches: [main, develop]
    branches-ignore: ['feature/*', 'experimental/*']
    paths: ['src/**', 'package.json', 'package-lock.json']
    paths-ignore: ['docs/**', '*.md', '.vscode/**', 'LICENSE']
    tags: ['v*']
    tags-ignore: ['v0.*']
```

**Filtros detalhados do push**:

| Filtro | Descricao | Exemplo |
|--------|-----------|---------|
| `branches` | Branches que disparam | `[main, 'release/*']` |
| `branches-ignore` | Branches que NAO disparam | `['feature/*']` |
| `paths` | Arquivos que disparam | `['src/**']` |
| `paths-ignore` | Arquivos que NAO disparam | `['docs/**']` |
| `tags` | Tags que disparam | `['v*']` |
| `tags-ignore` | Tags que NAO disparam | `['v0.*']` |

**Padroes de glob suportados**:

```yaml
branches:
  - main                    # Exato
  - 'release/*'             # Qualquer coisa apos release/
  - 'release/**'            # Qualquer coisa apos release/ (inclui subdirs)
  - 'v[0-9]+.[0-9]+'        # Regex-like patterns
  - 'feature/{bugfix,hotfix}/*'  # Brace expansion
  - '!main'                 # Negacao

paths:
  - 'src/**'                # Qualquer arquivo em src/
  - '*.js'                  # Arquivos .js na raiz
  - '**/*.test.js'          # Arquivos de teste
  - 'package.json'          # Arquivo especifico
  - '!docs/**'              # Negacao
```

### pull_request

O trigger `pull_request` dispara em various eventos de PR:

```yaml
on:
  pull_request:
    branches: [main]
    branches-ignore: [develop]
    types: [opened, synchronize, reopened, edited, assigned, labeled, ready_for_review]
    paths: ['src/**']
    paths-ignore: ['docs/**']
```

**Tipos de eventos do pull_request**:

| Tipo | Descricao | Quando usar |
|------|-----------|-------------|
| `opened` | PR criado | CI imediato |
| `synchronize` | Novo commit no PR | Re-run CI |
| `reopened` | PR reaberto | Re-run CI |
| `edited` | Titulo/body editado | Atualizar checks |
| `assigned` | PR atribuido a alguem | Notificacoes |
| `labeled` | Label adicionada | Conditional jobs |
| `unlabeled` | Label removida | Cleanup |
| `ready_for_review` | PR marcado como ready | Deploy preview |
| `review_requested` | Review requisitado | Notificacoes |
| `auto_merge_enabled` | Auto-merge habilitado | Validation |
| `auto_merge_disabled` | Auto-merge desabilitado | Logging |

**Exemplo de PR com multiplos filtros**:

```yaml
on:
  pull_request:
    branches:
      - main
      - 'release/*'
    types: [opened, synchronize, reopened]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
    paths-ignore:
      - 'src/**/*.test.js'  # Ignora testes unitarios
      - '*.md'
```

### pull_request_target

**ATENCAO**: `pull_request_target` roda no contexto do branch BASE, nao do PR. Isto e perigoso se voce fizer checkout do branch do PR.

```yaml
# USO SEGURO: So para workflows que NAO precisam do codigo do PR
on:
  pull_request_target:
    types: [opened, reopened, synchronize]

jobs:
  check-pr:
    runs-on: ubuntu-latest
    steps:
      - name: Check PR title
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
        run: |
          if [[ ! "$PR_TITLE" =~ ^feat:|^fix:|^docs: ]]; then
            echo "PR title must follow conventional commits!"
            exit 1
          fi

# USO PERIGOSO: NAO faca isso!
on:
  pull_request_target:
    types: [opened]
jobs:
  dangerous:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4  # PERIGO: checkout do branch base
      # Mas o PR pode ter modificado o workflow!
```

### workflow_dispatch

O trigger `workflow_dispatch` permite disparar workflows manualmente:

```yaml
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
        required: false
        type: string
        default: 'latest'
      dry_run:
        description: 'Dry run?'
        type: boolean
        default: false
      notify:
        description: 'Send notification'
        type: boolean
        default: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Deploy
        run: |
          echo "Environment: ${{ inputs.environment }}"
          echo "Version: ${{ inputs.version }}"
          echo "Dry run: ${{ inputs.dry_run }}"
          if [ "${{ inputs.dry_run }}" == "true" ]; then
            echo "This is a dry run - no changes will be made"
          else
            deploy.sh ${{ inputs.version }} ${{ inputs.environment }}
          fi
```

**Tipos de input disponiveis**:

| Tipo | Descricao | Exemplo |
|------|-----------|---------|
| `string` | Texto livre | `version: '1.0.0'` |
| `boolean` | Verdadeiro/falso | `dry_run: true` |
| `choice` | Lista de opcoes | `environment: staging` |

**API para disparar workflow_dispatch**:

```bash
# Via GitHub CLI
gh workflow run deploy.yml \
  -f environment=production \
  -f version=1.2.3 \
  -f dry_run=false

# Via API REST
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/deploy.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "environment": "production",
      "version": "1.2.3",
      "dry_run": "false"
    }
  }'
```

### workflow_call

O trigger `workflow_call` permite que um workflow seja chamado por outro:

```yaml
# Workflow reutilizavel (.github/workflows/reusable-test.yml)
name: Reusable Test

on:
  workflow_call:
    inputs:
      node-version:
        required: true
        type: string
      os:
        required: false
        type: string
        default: 'ubuntu-latest'
    secrets:
      CODECOV_TOKEN:
        required: true
    outputs:
      test-result:
        description: 'Test result'
        value: ${{ jobs.test.outputs.result }}

jobs:
  test:
    runs-on: ${{ inputs.os }}
    outputs:
      result: ${{ steps.test.outputs.result }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci && npm test
      - id: test
        run: echo "result=success" >> $GITHUB_OUTPUT
```

```yaml
# Workflow que chama o reutilizavel
name: Main CI

on:
  push:
    branches: [main]

jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
      os: 'ubuntu-latest'
    secrets:
      CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

### workflow_run

O trigger `workflow_run` dispara apos outro workflow completar:

```yaml
# Workflow A (chamado)
name: Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
    steps:
      - id: version
        run: echo "value=1.0.0" >> $GITHUB_OUTPUT
      - run: npm run build
```

```yaml
# Workflow B (dispara apos Build)
name: Deploy after Build

on:
  workflow_run:
    workflows: ["Build"]  # Nome exato do workflow
    types:
      - completed
    branches:
      - main

jobs:
  deploy:
    # So roda se o workflow anterior foi bem-sucedido
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - name: Download artifacts
        uses: dawidd6/action-download-artifact@v3
        with:
          workflow: build
          workflow_conclusion: success
      - run: echo "Deploying..."
```

### schedule

O trigger `schedule` usa sintaxe cron para agendar execucoes:

```yaml
on:
  schedule:
    - cron: '0 2 * * 1'      # Toda segunda-feira as 02:00 UTC
    - cron: '0 12 * * 1-5'   # Seg-Sex as 12:00 UTC
    - cron: '0 0 1 * *'      # Dia 1 de cada mes as 00:00 UTC
    - cron: '*/15 * * * *'   # A cada 15 minutos
    - cron: '0 */6 * * *'    # A cada 6 horas
```

**Sintaxe cron do GitHub Actions**:

```
┌───────────── minuto (0 - 59)
│ ┌───────────── hora (0 - 23)
│ │ ┌───────────── dia do mes (1 - 31)
│ │ │ ┌───────────── mes (1 - 12)
│ │ │ │ ┌───────────── dia da semana (0 - 6, domingo = 0)
│ │ │ │ │
* * * * *
```

**Exemplos de cron**:

| Cron | Descricao |
|------|-----------|
| `* * * * *` | A cada minuto |
| `0 * * * *` | A cada hora (minuto 0) |
| `0 0 * * *` | Todo dia as 00:00 UTC |
| `0 2 * * 1` | Toda segunda as 02:00 UTC |
| `0 0 1 * *` | Primeiro dia do mes |
| `30 4 * * 1-5` | Seg-Sex as 04:30 UTC |
| `0 0 * * 0` | Todo domingo |
| `0 12 1,15 * *` | Dia 1 e 15 do mes |
| `*/5 * * * *` | A cada 5 minutos |
| `0 0/6 * * *` | A cada 6 horas |

**Nota importante**: Schedules rodam na branch padrao do repositorio (geralmente `main`). Schedules podem ter atraso de ate 60 minutos.

### repository_dispatch

O trigger `repository_dispatch` permite disparar workflows via API:

```yaml
on:
  repository_dispatch:
    types: [deploy, build, notify]

jobs:
  handle:
    runs-on: ubuntu-latest
    steps:
      - name: Handle dispatch
        env:
          DISPATCH_TYPE: ${{ github.event.client_payload.type }}
          DISPATCH_DATA: ${{ github.event.client_payload.data }}
        run: |
          echo "Type: $DISPATCH_TYPE"
          echo "Data: $DISPATCH_DATA"
```

**API para disparar**:

```bash
# Via GitHub CLI
gh api repos/OWNER/REPO/dispatches \
  -f event_type=deploy \
  -f client_payload='{"environment":"production","version":"1.0.0"}'

# Via API REST
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{
    "event_type": "deploy",
    "client_payload": {
      "environment": "production",
      "version": "1.0.0"
    }
  }'
```

### release

O trigger `release` dispara em eventos de release:

```yaml
on:
  release:
    types: [published, unpublished, created, edited, deleted, prereleased, released]

jobs:
  release:
    runs-on: ubuntu-latest
    if: github.event.action == 'published'
    steps:
      - name: Get release info
        env:
          TAG: ${{ github.event.release.tag_name }}
          NAME: ${{ github.event.release.name }}
          BODY: ${{ github.event.release.body }}
        run: |
          echo "Release: $NAME ($TAG)"
          echo "Body: $BODY"

      - name: Deploy
        run: deploy.sh ${{ github.event.release.tag_name }}
```

### Trigger Combinado

Voce pode combinar multiplos triggers em um unico workflow:

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'
  workflow_dispatch:
    inputs:
      force:
        type: boolean
        default: false

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Determine context
        run: |
          if [ "${{ github.event_name }}" == "push" ]; then
            echo "Running on push to ${{ github.ref_name }}"
          elif [ "${{ github.event_name }}" == "pull_request" ]; then
            echo "Running on PR #${{ github.event.pull_request.number }}"
          elif [ "${{ github.event_name }}" == "schedule" ]; then
            echo "Running on schedule"
          elif [ "${{ github.event_name }}" == "workflow_dispatch" ]; then
            echo "Running manually (force=${{ inputs.force }})"
          fi
```

---

## 2.3 Jobs Completos

### Estrutura de um Job

```yaml
jobs:
  job-name:
    name: 'Display Name'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
    env:
      JOB_VAR: value
    outputs:
      result: ${{ steps.step-id.outputs.value }}
    needs: [other-job]
    if: success()
    concurrency:
      group: job-group
      cancel-in-progress: true
    services:
      service-name:
        image: redis:7
    container:
      image: node:20
    runs-on: [self-hosted, gpu]
    steps:
      # Steps aqui
```

### Propriedades Detalhadas de Job

| Propriedade | Tipo | Descricao | Default |
|-------------|------|-----------|---------|
| `runs-on` | string/array | Runner selector | Obrigatorio |
| `name` | string | Nome exibido na UI | job-key |
| `needs` | string/array | Jobs dependentes | Nenhum |
| `if` | string | Condicao para executar | `true` |
| `outputs` | map | Saidas compartilhadas | Nenhum |
| `env` | map | Variaveis de ambiente | Nenhum |
| `timeout-minutes` | number | Timeout em minutos | 360 |
| `concurrency` | object/group | Controle de concorrencia | Nenhum |
| `services` | map | Containers auxiliares | Nenhum |
| `container` | object/string | Container para o job | Nenhum |
| `defaults` | object | Defaults do job | Nenhum |
| `strategy` | object | Configuracao de matrix | Nenhum |
| `environment` | string/object | Environment de deploy | Nenhum |

### Dependencias entre Jobs

```yaml
jobs:
  # Job sem dependencias
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Linting"

  # Job que depende de um unico job
  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - run: echo "Testing"

  # Job que depende de multiplos jobs
  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building"

  # Job que so roda se anteriores falharam
  notify-failure:
    needs: [lint, test, build]
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - run: echo "Algo falhou!"

  # Job que roda independente do resultado
  cleanup:
    needs: [lint, test, build]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: echo "Limpando..."
```

### Condicoes em Jobs

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    # So roda se for push para develop
    if: github.event_name == 'push' && github.ref == 'refs/heads/develop'
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    runs-on: ubuntu-latest
    # So roda se for PR merged para main
    if: >
      github.event_name == 'pull_request' &&
      github.event.pull_request.merged == true &&
      github.ref == 'refs/heads/main'
    steps:
      - run: echo "Deploying to production"

  deploy-manual:
    runs-on: ubuntu-latest
    # So roda via workflow_dispatch
    if: github.event_name == 'workflow_dispatch'
    environment: production
    steps:
      - run: echo "Manual deploy"

  deploy-tag:
    runs-on: ubuntu-latest
    # So roda quando tag e criada
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - run: echo "Deploying version ${{ github.ref_name }}"
```

### Outputs de Jobs

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
      image-tag: ${{ steps.docker.outputs.tag }}
      should-deploy: ${{ steps.check.outputs.deploy }}
    steps:
      - id: version
        run: echo "value=$(cat VERSION)" >> $GITHUB_OUTPUT

      - id: docker
        run: echo "tag=ghcr.io/app:$(cat VERSION)" >> $GITHUB_OUTPUT

      - id: check
        run: |
          if [ "${{ github.ref }}" == "refs/heads/main" ]; then
            echo "deploy=true" >> $GITHUB_OUTPUT
          else
            echo "deploy=false" >> $GITHUB_OUTPUT
          fi

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "Version: ${{ needs.build.outputs.version }}"
      - run: echo "Image: ${{ needs.build.outputs.image-tag }}"

  deploy:
    needs: [build, test]
    if: needs.build.outputs.should-deploy == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying ${{ needs.build.outputs.image-tag }}"
```

### Job Timeout

```yaml
jobs:
  quick-test:
    runs-on: ubuntu-latest
    timeout-minutes: 10  # Timeout especifico para este job
    steps:
      - run: echo "Rapido"

  long-build:
    runs-on: ubuntu-latest
    timeout-minutes: 120  # Build que pode demorar
    steps:
      - run: make build

  very-long:
    runs-on: ubuntu-latest
    timeout-minutes: 360  # Maximo permitido (6 horas)
    steps:
      - run: make very-large-build
```

### Job com Environment

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    steps:
      - run: echo "Deploying to production"
      # Environment protection rules sao aplicados automaticamente:
      # - Required reviewers
      # - Wait timer
      # - Deployment branches
```

---

## 2.4 Steps Avancados

### Estrutura Completa de um Step

```yaml
steps:
  - name: Step name
    id: step-id
    uses: actions/checkout@v4
    with:
      param1: value1
    env:
      VAR: value
    shell: bash
    working-directory: ./subdir
    continue-on-error: true
    timeout-minutes: 10
    if: success()
```

### Propriedades Detalhadas de Step

| Propriedade | Tipo | Descricao |
|-------------|------|-----------|
| `name` | string | Nome exibido na UI |
| `id` | string | Identificador para referenciar |
| `uses` | string | Action a ser usada |
| `run` | string | Comando shell |
| `shell` | string | Shell para o comando |
| `with` | map | Parametros da action |
| `env` | map | Variaveis de ambiente |
| `working-directory` | string | Diretorio de trabalho |
| `continue-on-error` | boolean | Nao falhar o job se step falhar |
| `timeout-minutes` | number | Timeout individual do step |

### Tipos de Steps

**Step com run (comando shell)**:

```yaml
steps:
  - name: Simple command
    run: echo "Hello"

  - name: Multi-line command
    run: |
      echo "Linha 1"
      echo "Linha 2"
      if [ -f package.json ]; then
        npm ci
      fi

  - name: PowerShell (Windows)
    run: |
      Write-Host "Hello from PowerShell"
      Get-Date
    shell: pwsh

  - name: Python script
    run: |
      import sys
      print(f"Python {sys.version}")
    shell: python

  - name: Custom shell
    run: echo $1 $2
    shell: bash --noprofile --norc -e -o pipefail {0}
```

**Step com uses (action)**:

```yaml
steps:
  - name: Checkout
    uses: actions/checkout@v4

  - name: Setup Node.js
    uses: actions/setup-node@v4
    with:
      node-version: '20'
      cache: 'npm'

  - name: Composite action local
    uses: ./.github/actions/setup

  - name: Docker action
    uses: docker://alpine:3.18
    with:
      args: echo "Running in Docker"
```

### Shell Options

```yaml
steps:
  # Bash (padrao no Linux/macOS)
  - run: echo "Hello"
    shell: bash

  # Bash com opcoes especificas
  - run: |
      set -e  # Sair em erro
      set -o pipefail  # Falha em pipes
      echo "Safe bash"
    shell: bash --noprofile --norc -e -o pipefail {0}

  # Sh (minimalista)
  - run: echo "Hello"
    shell: sh

  # PowerShell Core (cross-platform)
  - run: Write-Host "Hello"
    shell: pwsh

  # PowerShell Desktop (Windows only)
  - run: Write-Host "Hello"
    shell: powershell

  # Python
  - run: |
      import os
      print(os.environ.get('MY_VAR', 'default'))
    shell: python

  # Node.js
  - run: |
      console.log('Hello from Node');
      console.log(process.env.MY_VAR);
    shell: node --experimental-default-type=module {0}
```

**Shell padrao por SO**:

| SO | Shell padrao |
|----|-------------|
| Linux (Ubuntu) | `bash --noprofile --norc -e -o pipefail {0}` |
| macOS | `bash --noprofile --norc -e -o pipefail {0}` |
| Windows | `pwsh` |

### Working Directory

```yaml
steps:
  - name: Run from root
    run: echo "Running from root"

  - name: Run from subdir
    run: echo "Running from subdir"
    working-directory: ./src

  - name: Run from nested dir
    run: echo "Running from nested"
    working-directory: ./src/components

  - name: Multiple commands in different dirs
    run: |
      cd frontend && npm install
      cd ../backend && mvn install
    working-directory: .  # Comando unico, CD manual
```

### Steps Condicionais

```yaml
steps:
  - name: Always run
    run: echo "Always"

  - name: Only on push
    if: github.event_name == 'push'
    run: echo "Push event"

  - name: Only on PR
    if: github.event_name == 'pull_request'
    run: echo "PR event"

  - name: Only on main
    if: github.ref == 'refs/heads/main'
    run: echo "Main branch"

  - name: If previous step failed
    if: failure()
    run: echo "Previous step failed"

  - name: If always (even if cancelled)
    if: always()
    run: echo "Always, even cancelled"

  - name: Complex condition
    if: >
      (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
      (github.event_name == 'pull_request' && contains(github.event.pull_request.title, '[deploy]'))
    run: echo "Deploy triggered"

  - name: Step outcome check
    id: step1
    run: echo "result=success" >> $GITHUB_OUTPUT

  - name: Check previous step
    if: steps.step1.outcome == 'success'
    run: echo "Step 1 succeeded"

  - name: Check step failure
    if: steps.step1.outcome == 'failure'
    run: echo "Step 1 failed"
```

### Continue on Error

```yaml
steps:
  - name: Critical step
    run: echo "Must succeed"

  - name: Optional step
    continue-on-error: true
    run: |
      # Este step pode falhar sem quebrar o job
      optional-command || echo "Failed but continuing"

  - name: Check optional result
    if: steps.optional.outcome == 'failure'
    run: echo "Optional step failed, but job continues"

  - name: Lint with warning
    continue-on-error: true
    run: npm run lint
```

### Timeout por Step

```yaml
steps:
  - name: Quick step
    timeout-minutes: 1
    run: echo "Must be fast"

  - name: Long running step
    timeout-minutes: 60
    run: |
      for i in {1..3600}; do
        echo "Processing $i"
        sleep 1
      done

  - name: Docker build
    timeout-minutes: 30
    run: docker build -t myapp .
```

### Steps com ID e Referenciamento

```yaml
steps:
  - id: checkout
    uses: actions/checkout@v4

  - id: setup
    uses: actions/setup-node@v4
    with:
      node-version: '20'

  - id: build
    run: |
      npm ci
      npm run build
      echo "build-dir=dist" >> $GITHUB_OUTPUT
      echo "size=$(du -sh dist | cut -f1)" >> $GITHUB_OUTPUT

  - id: test
    run: npm test
    if: steps.build.outcome == 'success'

  - name: Use outputs
    run: |
      echo "Build directory: ${{ steps.build.outputs.build-dir }}"
      echo "Build size: ${{ steps.build.outputs.size }}"
      echo "Test result: ${{ steps.test.outcome }}"
```

### Upload e Download de Artifacts

```yaml
steps:
  - name: Build
    run: npm run build

  - name: Upload dist folder
    uses: actions/upload-artifact@v4
    with:
      name: build-output
      path: dist/
      retention-days: 7
      compression-level: 6

  - name: Upload multiple items
    uses: actions/upload-artifact@v4
    with:
      name: multi-output
      path: |
        dist/
        coverage/
        reports/
      retention-days: 30

  - name: Upload with glob
    uses: actions/upload-artifact@v4
    with:
      name: binaries
      path: |
        build/*.exe
        build/*.dmg
        build/*.tar.gz
      if-no-files-found: warn

  # Download em outro job
  - name: Download artifacts
    uses: actions/download-artifact@v4
    with:
      name: build-output
      path: dist/

  - name: Download all artifacts
    uses: actions/download-artifact@v4
    with:
      path: all-artifacts
      merge-multiple: true
```

---

## 2.5 Expressoes e Contexts

### Contexts Disponiveis

| Context | Descricao | Propriedades Principais |
|---------|-----------|------------------------|
| `github` | Dados do evento e repositorio | `actor`, `event_name`, `ref`, `sha`, `repository` |
| `env` | Variaveis de ambiente do workflow | Chaves definidas em `env:` |
| `vars` | Variaveis do repositorio/organizacao | Chaves em Settings > Variables |
| `secrets` | Secrets do repositorio/organizacao | Chaves em Settings > Secrets |
| `needs` | Outputs de jobs anteriores | `needs.job.outputs.key` |
| `strategy` | Dados da matrix | `strategy.job-index`, `strategy.fail-fast` |
| `matrix` | Valor atual da matrix | `matrix.key` |
| `inputs` | Inputs do workflow_dispatch | `inputs.key` |
| `runner` | Dados do runner | `runner.os`, `runner.arch`, `runner.name` |
| `job` | Dados do job | `job.status`, `job.container` |
| `steps` | Resultados de steps anteriores | `steps.id.outcome`, `steps.id.outputs.key` |
| `gate` | Dados do deployment protection rule | `gate.reviewers` |

### github Context Detalhado

```yaml
# Propriedades do github context
${{ github.token }}                    # Token de autenticacao
${{ github.workflow }}                 # Nome do workflow
${{ github.workspace }}                # Diretorio de trabalho
${{ github.action }}                   # ID do step atual
${{ github.action_path }}              # Path da action atual
${{ github.action_repository }}        # Repositorio da action
${{ github.actor }}                    # Quem disparou
${{ github.api_url }}                  # URL da API
${{ github.base_ref }}                 # Branch base do PR
${{ github.env }}                      # Path do arquivo de env
${{ github.event }}                    # Objeto completo do evento
${{ github.event_name }}               # Nome do evento
${{ github.event_path }}               # Path do JSON do evento
${{ github.graphql_url }}              # URL do GraphQL
${{ github.head_ref }}                 # Branch head do PR
${{ github.job }}                      # ID do job
${{ github.ref }}                      # Ref completa
${{ github.ref_name }}                 # Nome da ref
${{ github.ref_protected }}            # Se branch e protegida
${{ github.ref_type }}                 # Tipo da ref (branch/tag)
${{ github.repository }}               # owner/repo
${{ github.repository_id }}            # ID numerico
${{ github.repository_owner }}         # Owner do repo
${{ github.repository_visibility }}    # public/private/internal
${{ github.retention_days }}           # Dias de retencao
${{ github.run_id }}                   # ID da execucao
${{ github.run_number }}               # Numero sequencial
${{ github.server_url }}               # https://github.com
${{ github.sha }}                      # Commit SHA
${{ github.triggering_actor }}         # Quem realmente disparou

# Propriedades especificas do evento
# Para push:
${{ github.event.before }}             # SHA anterior
${{ github.event.head_commit.message }}
${{ github.event.head_commit.author.name }}
${{ github.event.head_commit.author.email }}
${{ github.event.commits }}            # Array de commits
${{ github.event.forced }}             # Se foi force push

# Para pull_request:
${{ github.event.pull_request.number }}
${{ github.event.pull_request.title }}
${{ github.event.pull_request.body }}
${{ github.event.pull_request.state }}
${{ github.event.pull_request.merged }}
${{ github.event.pull_request.head.ref }}
${{ github.event.pull_request.head.sha }}
${{ github.event.pull_request.base.ref }}
${{ github.event.pull_request.base.sha }}
${{ github.event.pull_request.changed_files }}
${{ github.event.pull_request.additions }}
${{ github.event.pull_request.deletions }}
${{ github.event.pull_request.user.login }}
${{ github.event.pull_request.labels.*.name }}

# Para release:
${{ github.event.release.tag_name }}
${{ github.event.release.name }}
${{ github.event.release.body }}
${{ github.event.release.upload_url }}
${{ github.event.release.zipball_url }}
${{ github.event.release.tarball_url }}
${{ github.event.release.target_commitish }}
${{ github.event.release.prerelease }}
${{ github.event.release.draft }}
```

### steps Context

```yaml
steps:
  - id: build
    run: |
      echo "version=1.0.0" >> $GITHUB_OUTPUT
      echo "dir=dist" >> $GITHUB_OUTPUT

  - id: test
    run: npm test
    continue-on-error: true

  - name: Check results
    run: |
      # Outcome do step anterior
      echo "Build outcome: ${{ steps.build.outcome }}"
      echo "Test outcome: ${{ steps.test.outcome }}"

      # Outputs do step build
      echo "Version: ${{ steps.build.outputs.version }}"
      echo "Dir: ${{ steps.build.outputs.dir }}"

      # Verificar se build foi sucesso
      if [ "${{ steps.build.outcome }}" == "success" ]; then
        echo "Build succeeded!"
      fi
```

### needs Context

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    outputs:
      lint-result: ${{ steps.lint.outputs.result }}
    steps:
      - id: lint
        run: echo "result=pass" >> $GITHUB_OUTPUT

  test:
    needs: lint
    runs-on: ubuntu-latest
    outputs:
      test-result: ${{ steps.test.outputs.result }}
    steps:
      - id: test
        run: echo "result=pass" >> $GITHUB_OUTPUT

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - name: Check dependencies
        run: |
          echo "Lint: ${{ needs.lint.result }}"
          echo "Lint output: ${{ needs.lint.outputs.lint-result }}"
          echo "Test: ${{ needs.test.result }}"
          echo "Test output: ${{ needs.test.outputs.test-result }}"

          if [ "${{ needs.lint.result }}" != "success" ] || [ "${{ needs.test.result }}" != "success" ]; then
            echo "Dependencies failed!"
            exit 1
          fi
```

### Operadores de Expressao

```yaml
# Comparacao
if: github.event_name == 'push'
if: github.ref != 'refs/heads/main'
if: github.event.pull_request.merged == true
if: github.run_number > 100

# Logico
if: github.event_name == 'push' && github.ref == 'refs/heads/main'
if: github.event_name == 'push' || github.event_name == 'pull_request'
if: !(github.event_name == 'schedule')
if: github.event_name == 'push' && !cancelled()

# Containment
if: contains(github.event.pull_request.title, '[deploy]')
if: contains(github.event.pull_request.labels.*.name, 'deploy')
if: !contains(github.event.pull_request.title, '[skip ci]')

# Prefix/Suffix
if: startsWith(github.ref, 'refs/tags/v')
if: endsWith(github.event.pull_request.head.ref, '-fix')

# Format
run: echo "${{ format('Deploying {0} to {1}', github.sha, inputs.environment) }}"

# Join
run: echo "${{ join(github.event.pull_request.labels.*.name, ', ') }}"

# Split
env:
  TAGS: ${{ join(github.event.release.tag_name, '-') }}

# Length
if: length(github.event.pull_request.body) > 0
if: length(github.event.commits) > 5

# Hash
run: echo "${{ hashFiles('**/package-lock.json') }}"
run: echo "${{ hashFiles('requirements.txt', 'Pipfile.lock') }}"

# JSON
run: echo "${{ toJSON(github.event) }}"
env:
  CONFIG: ${{ fromJSON(vars.BUILD_CONFIG) }}

# Ternario
env:
  NODE_VERSION: ${{ github.ref == 'refs/heads/main' && '20' || '18' }}
  IS_MAIN: ${{ github.ref == 'refs/heads/main' && 'true' || 'false' }}
```

### Funcoes de Status

```yaml
# Sempre verdadeiro (ignora resultados anteriores)
if: always()

# Verdadeiro se todos anteriores foram sucesso
if: success()

# Verdadeiro se algum anterior falhou
if: failure()

# Verdadeiro se workflow foi cancelado
if: cancelled()

# Verdadeiro se todos anteriores foram skipped
if: skipped()

# Combinacoes
if: success() && github.ref == 'refs/heads/main'
if: failure() || cancelled()
if: !success()  # Equivalente a failure() || cancelled() || skipped()
```

### Formatacao de Strings

```yaml
# Formato basico
run: echo "${{ format('Hello {0}!', github.actor) }}"

# Multiplos placeholders
run: echo "${{ format('Deploying {0} to {1} at {2}', github.sha, inputs.env, github.run_number) }}"

# Em env vars
env:
  MESSAGE: "${{ format('Build {0} on {1}', github.run_number, runner.os) }}"
  URL: "${{ format('{0}/{1}/actions/runs/{2}', github.server_url, github.repository, github.run_id) }}"
```

### Hash de Arquivos

```yaml
# Hash unico de um arquivo
run: echo "${{ hashFiles('package-lock.json') }}"

# Hash de multiplos arquivos
run: echo "${{ hashFiles('package.json', 'package-lock.json') }}"

# Hash de padrao glob
run: echo "${{ hashFiles('**/package-lock.json') }}"

# Usar em cache keys
- uses: actions/cache@v4
  with:
    path: node_modules
    key: deps-${{ hashFiles('**/package-lock.json') }}

# Usar em condicoes
- name: Install only if lock file changed
  if: hashFiles('package-lock.json') != steps.cache.outputs.cache-primary-key-hash
  run: npm ci
```

---

## 2.6 Matrix Strategy Completa

### Estrutura Basica

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
      - run: npm ci && npm test
```

### Combinacoes Geradas

A matrix acima gera 9 combinacoes:

| # | OS | Node |
|---|-----|------|
| 1 | ubuntu-latest | 18 |
| 2 | ubuntu-latest | 20 |
| 3 | ubuntu-latest | 22 |
| 4 | macos-latest | 18 |
| 5 | macos-latest | 20 |
| 6 | macos-latest | 22 |
| 7 | windows-latest | 18 |
| 8 | windows-latest | 20 |
| 9 | windows-latest | 22 |

### Include e Exclude

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
        # Include: adiciona combinacoes extras
        include:
          - os: ubuntu-latest
            node-version: 20
            experimental: true
            coverage: true
          - os: ubuntu-latest
            node-version: 22
            experimental: true
        # Exclude: remove combinacoes
        exclude:
          - os: windows-latest
            node-version: 18
          - os: macos-latest
            node-version: 18
      fail-fast: false
```

**Resultado**:

| # | OS | Node | Experimental | Coverage |
|---|-----|------|-------------|----------|
| 1 | ubuntu-latest | 18 | - | - |
| 2 | ubuntu-latest | 20 | true | true |
| 3 | ubuntu-latest | 22 | true | - |
| 4 | macos-latest | 20 | - | - |
| 5 | macos-latest | 22 | - | - |
| 6 | windows-latest | 20 | - | - |
| 7 | windows-latest | 22 | - | - |

### Matrix com Propriedades Avancadas

```yaml
jobs:
  build:
    runs-on: ${{ matrix.runner }}
    strategy:
      matrix:
        include:
          # Configuracao 1: Linux basico
          - runner: ubuntu-latest
            os: linux
            arch: x64
            build-cmd: 'make build-linux'
            artifact: 'linux-x64'

          # Configuracao 2: Linux ARM
          - runner: ubuntu-latest
            os: linux
            arch: arm64
            build-cmd: 'make build-linux-arm'
            artifact: 'linux-arm64'

          # Configuracao 3: macOS
          - runner: macos-latest
            os: darwin
            arch: arm64
            build-cmd: 'make build-mac'
            artifact: 'macos-arm64'

          # Configuracao 4: Windows
          - runner: windows-latest
            os: windows
            arch: x64
            build-cmd: 'make build-windows'
            artifact: 'windows-x64'

          # Configuracao 5: Windows com GPU
          - runner: [self-hosted, windows, gpu]
            os: windows
            arch: x64
            build-cmd: 'make build-windows-gpu'
            artifact: 'windows-x64-gpu'
      fail-fast: false
      max-parallel: 2

    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: ${{ matrix.build-cmd }}

      - name: Upload
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.artifact }}
          path: build/${{ matrix.artifact }}/
```

### fail-fast

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]
      # fail-fast: true (padrao) - cancela outros jobs se um falhar
      # fail-fast: false - todos os jobs rodam independente de falhas
      fail-fast: false
    steps:
      - run: echo "Running on ${{ matrix.os }} with Node ${{ matrix.node }}"
```

### max-parallel

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]
      max-parallel: 3  # So 3 jobs rodam simultaneamente
      fail-fast: false
    steps:
      - run: echo "Running"
```

### Matrix Dinamica

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          # Gerar matrix dinamicamente
          MATRIX='{"include":[{"os":"ubuntu-latest","node":"20"},{"os":"macos-latest","node":"20"}]}'
          echo "matrix=$MATRIX" >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ${{ matrix.os }}
    strategy:
      matrix: ${{ fromJSON(needs.build.outputs.matrix) }}
    steps:
      - run: echo "Testing on ${{ matrix.os }} with Node ${{ matrix.node }}"
```

### Usando Variaveis de Environment na Matrix

```yaml
env:
  LINUX_VERSIONS: '["ubuntu-22.04", "ubuntu-24.04"]'
  MACOS_VERSIONS: '["macos-13", "macos-14"]'

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: ${{ fromJSON(env.LINUX_VERSIONS) }}
    steps:
      - run: echo "Testing on ${{ matrix.os }}"
```

### Condicoes Baseadas em Matrix

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node: [18, 20, 22]
        include:
          - os: ubuntu-latest
            node: 20
            primary: true
    steps:
      - uses: actions/checkout@v4

      - name: Setup
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: Test
        run: npm test

      # So upload coverage no primary
      - name: Upload coverage
        if: matrix.primary
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}

      # So deploy no primary
      - name: Deploy
        if: matrix.primary && github.ref == 'refs/heads/main'
        run: echo "Deploying..."
```

---

## 2.7 Concurrency Groups

### Conceito

Concurrency groups controlam quantas execucoes de um workflow podem rodar simultaneamente. Isto e util para:
- Evitar deploys simultaneos
- Cancelar execucoes obsoletas
- Economizar minutos de runner

### Sintaxe Basica

```yaml
concurrency:
  group: unique-group-name
  cancel-in-progress: false
```

### Padroes de Concurrency Groups

```yaml
# Padrao 1: Por workflow + branch
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

# Padrao 2: Por workflow + evento
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}
  cancel-in-progress: false

# Padrao 3: Por job especifico
jobs:
  deploy:
    concurrency:
      group: deploy-${{ inputs.environment }}
      cancel-in-progress: false

# Padrao 4: Por repository
concurrency:
  group: ${{ github.repository }}-${{ github.workflow }}
  cancel-in-progress: true

# Padrao 5: Por actor
concurrency:
  group: ${{ github.workflow }}-${{ github.actor }}
  cancel-in-progress: true
```

### Exemplos Praticos

**CI - Cancelar execucoes obsoletas**:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true  # Cancela CI anterior para este branch

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
```

**Deploy - Evitar deploys simultaneos**:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    concurrency:
      group: deploy-production  # So um deploy por vez
      cancel-in-progress: false  # Nao cancela deploys em andamento
    environment: production
    steps:
      - run: echo "Deploying..."
```

**Deploy por Environment**:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    concurrency:
      group: deploy-${{ inputs.environment }}  # Um por ambiente
      cancel-in-progress: false
    environment: ${{ inputs.environment }}
    steps:
      - run: echo "Deploying to ${{ inputs.environment }}"
```

### cancel-in-progress Detalhado

```yaml
# cancel-in-progress: true
# - Se uma nova execucao inicia, cancela as anteriores no mesmo group
# - Util para CI onde execucoes anteriores sao obsoletas

# cancel-in-progress: false (padrao)
# - Novas execucoes ficam na fila ate anteriores completarem
# - Util para deploys onde cada execucao e importante

# Exemplo: CI com cancel, Deploy sem cancel
name: CI/CD

on:
  push:
    branches: [main]

jobs:
  ci:
    concurrency:
      group: ci-${{ github.ref }}
      cancel-in-progress: true
    runs-on: ubuntu-latest
    steps:
      - run: npm test

  deploy:
    needs: ci
    concurrency:
      group: deploy-production
      cancel-in-progress: false
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying"
```

### Concurrency em Workflow vs Job

```yaml
# Workflow-level (afeta todos os jobs)
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  job1:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Job 1"

  job2:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Job 2"
```

```yaml
# Job-level (afeta apenas o job especifico)
jobs:
  job1:
    concurrency:
      group: job1-${{ github.ref }}
      cancel-in-progress: true
    runs-on: ubuntu-latest
    steps:
      - run: echo "Job 1"

  job2:
    concurrency:
      group: job2-${{ github.ref }}
      cancel-in-progress: false
    runs-on: ubuntu-latest
    steps:
      - run: echo "Job 2"
```

---

## 2.8 Services Detalhado

### Conceito

Services sao containers Docker que rodam ao lado do job e sao uteis para:
- Bancos de dados (PostgreSQL, MySQL, MongoDB)
- Cache (Redis, Memcached)
- Message queues (RabbitMQ, Kafka)
- Ferramentas de teste (Selenium, MailHog)

### Sintaxe Completa

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      service-name:
        image: image:tag
        env:
          KEY: value
        ports:
          - host-port:container-port
        volumes:
          - /host/path:/container/path
        options: >-
          --health-cmd "command"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
          --health-start-period 30s
        credentials:
          username: ${{ secrets.REGISTRY_USER }}
          password: ${{ secrets.REGISTRY_PASS }}
```

### PostgreSQL

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
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
          --health-start-period 10s
        volumes:
          - postgres-data:/var/lib/postgresql/data

    steps:
      - uses: actions/checkout@v4

      - name: Wait for PostgreSQL
        run: |
          until pg_isready -h localhost -p 5432; do
            echo "Waiting for PostgreSQL..."
            sleep 1
          done

      - name: Run migrations
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
        run: npm run db:migrate

      - name: Run tests
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
        run: npm test

volumes:
  postgres-data:
```

### MySQL

```yaml
services:
  mysql:
    image: mysql:8.0
    env:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: testdb
      MYSQL_USER: testuser
      MYSQL_PASSWORD: testpass
    ports:
      - 3306:3306
    options: >-
      --health-cmd "mysqladmin ping -h localhost"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### Redis

```yaml
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
```

### MongoDB

```yaml
services:
  mongodb:
    image: mongo:7
    ports:
      - 27017:27017
    env:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: password
      MONGO_INITDB_DATABASE: testdb
    options: >-
      --health-cmd "mongosh --eval 'db.adminCommand({ping:1})'"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

### RabbitMQ

```yaml
services:
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
```

### Elasticsearch

```yaml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    ports:
      - 9200:9200
    env:
      discovery.type: single-node
      xpack.security.enabled: "false"
      ES_JAVA_OPTS: "-Xms512m -Xmx512m"
    options: >-
      --health-cmd "curl -f http://localhost:9200/_cluster/health || exit 1"
      --health-interval 15s
      --health-timeout 10s
      --health-retries 10
      --health-start-period 30s
```

### Multiplos Services

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        ports: ['6379:6379']
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      rabbitmq:
        image: rabbitmq:3
        ports: ['5672:5672']
        options: >-
          --health-cmd "rabbitmq-diagnostics -q ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Test all services
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
          RABBITMQ_URL: amqp://localhost:5672
        run: |
          npm run test:integration
          npm run test:e2e
```

### Services com Network Customizada

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      app:
        image: myapp:latest
        ports: ['8080:8080']
        networks:
          - test-network

      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        networks:
          - test-network

    networks:
      test-network:
        driver: bridge

    steps:
      - run: curl http://app:8080/health
```

---

## 2.9 Defaults

### Conceito

O `defaults` permite definir valores padrao que sao aplicados a todos os steps de um job ou workflow, reduzindo repeticao.

### Workflow-level Defaults

```yaml
name: CI

defaults:
  run:
    shell: bash
    working-directory: ./src

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - run: npm run lint
        # Usa shell: bash e working-directory: ./src automaticamente

  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
        # Usa shell: bash e working-directory: ./src automaticamente
```

### Job-level Defaults

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        shell: bash
        working-directory: ./frontend
    steps:
      - run: npm ci
        # working-directory: ./frontend

      - run: npm run build
        # working-directory: ./frontend

  test-backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        shell: bash
        working-directory: ./backend
    steps:
      - run: mvn test
        # working-directory: ./backend
```

### Sobrescrevendo Defaults

```yaml
defaults:
  run:
    shell: bash
    working-directory: ./src

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Usa default (./src)"

      - run: echo "Sobrescreve working-directory"
        working-directory: ./tests

      - run: echo "Sobrescreve shell"
        shell: pwsh
```

### Defaults para Actions

```yaml
defaults:
  run:
    shell: bash
    working-directory: ./src

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        # working-directory nao se aplica a actions, so a run

      - run: npm ci
        # working-directory: ./src (aplicado)
```

---

## 2.10 Exemplo Workflow Completo

### Pipeline Full-Stack com Todos os Recursos

Este workflow demonstra praticamente todos os conceitos discutidos neste capitulo:

```yaml
# .github/workflows/full-pipeline.yml
name: Full Pipeline

# ============================================
# TRIGGERS
# ============================================
on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'package-lock.json'
      - 'Dockerfile'
      - '.github/workflows/**'
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.vscode/**'
      - 'LICENSE'

  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]
    paths:
      - 'src/**'
      - 'tests/**'

  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production
      skip_tests:
        description: 'Skip tests (emergency deploy)'
        type: boolean
        default: false
      debug:
        description: 'Enable debug logging'
        type: boolean
        default: false

  release:
    types: [published]

# ============================================
# WORKFLOW-LEVEL CONFIG
# ============================================
env:
  NODE_VERSION: '20'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

# Concurrency group
concurrency:
  group: pipeline-${{ github.ref }}
  cancel-in-progress: true

# Default permissions
permissions:
  contents: read

# ============================================
# JOBS
# ============================================
jobs:
  # ========================================
  # LINT JOB
  # ========================================
  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint -- --format=json -o eslint-report.json
        continue-on-error: false

      - name: Run Prettier
        run: npm run format:check

      - name: Run TypeScript
        run: npm run typecheck

      - name: Upload lint report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: lint-report
          path: eslint-report.json
          retention-days: 7

  # ========================================
  # TEST JOB (Matrix)
  # ========================================
  test:
    name: Test (${{ matrix.os }}, Node ${{ matrix.node-version }})
    needs: lint
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20

    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18, 20, 22]
        include:
          - os: ubuntu-latest
            node-version: 20
            primary: true
        exclude:
          - os: windows-latest
            node-version: 18
          - os: macos-latest
            node-version: 18
      fail-fast: false

    services:
      postgres:
        image: postgres:16
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
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        if: ${{ !inputs.skip_tests }}
        run: npm run test:unit -- --coverage
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
          NODE_ENV: test

      - name: Run integration tests
        if: ${{ !inputs.skip_tests && matrix.primary }}
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
          NODE_ENV: test

      - name: Upload coverage
        if: matrix.primary && always()
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage/lcov.info
          flags: ${{ matrix.os }}-node${{ matrix.node-version }}
          fail_ci_if_error: false

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results-${{ matrix.os }}-node${{ matrix.node-version }}
          path: |
            coverage/
            test-results/
          retention-days: 7

  # ========================================
  # SECURITY SCAN
  # ========================================
  security:
    name: Security Scan
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      security-events: write
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Trivy (filesystem)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-fs.sarif'
          severity: 'CRITICAL,HIGH'
          skip-dirs: 'node_modules,coverage,dist'

      - name: Run Trivy (config)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-config.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_files: 'trivy-*.sarif'

      - name: Run npm audit
        if: always()
        run: |
          npm audit --audit-level=high --json > audit-report.json || true
          if [ "$(cat audit-report.json | jq '.metadata.vulnerabilities.high + .metadata.vulnerabilities.critical')" -gt 0 ]; then
            echo "::warning::Found high/critical vulnerabilities"
          fi

      - name: Upload audit report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            trivy-*.sarif
            audit-report.json
          retention-days: 30

  # ========================================
  # BUILD JOB
  # ========================================
  build:
    name: Build
    needs: [test, security]
    if: |
      inputs.skip_tests ||
      (needs.test.result == 'success' && needs.security.result == 'success')
    runs-on: ubuntu-latest
    timeout-minutes: 15

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build-push.outputs.digest }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-${{ github.sha }}
          path: dist/
          retention-days: 7

      - name: Docker meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        id: build-push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

  # ========================================
  # DEPLOY STAGING
  # ========================================
  deploy-staging:
    name: Deploy to Staging
    needs: build
    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      (inputs.environment == 'staging' || inputs.environment == '')
    runs-on: ubuntu-latest
    timeout-minutes: 15
    environment:
      name: staging
      url: https://staging.myapp.com

    concurrency:
      group: deploy-staging
      cancel-in-progress: false

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_STAGING }}
          aws-region: us-east-1

      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster staging \
            --service myapp-staging \
            --force-new-deployment

      - name: Wait for stability
        run: |
          aws ecs wait services-stable \
            --cluster staging \
            --services myapp-staging

      - name: Health check
        run: |
          for i in {1..30}; do
            if curl -sf https://staging.myapp.com/health; then
              echo "Health check passed!"
              exit 0
            fi
            echo "Attempt $i/30..."
            sleep 10
          done
          exit 1

  # ========================================
  # DEPLOY PRODUCTION
  # ========================================
  deploy-production:
    name: Deploy to Production
    needs: build
    if: |
      (github.event_name == 'release' && github.event.action == 'published') ||
      (github.event_name == 'workflow_dispatch' && inputs.environment == 'production')
    runs-on: ubuntu-latest
    timeout-minutes: 20
    environment:
      name: production
      url: https://myapp.com

    concurrency:
      group: deploy-production
      cancel-in-progress: false

    permissions:
      contents: read
      deployments: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN_PRODUCTION }}
          aws-region: us-east-1

      - name: Create deployment
        run: |
          aws ecs update-service \
            --cluster production \
            --service myapp-production \
            --force-new-deployment

      - name: Wait for stability
        run: |
          aws ecs wait services-stable \
            --cluster production \
            --services myapp-production

      - name: Health check
        run: |
          for i in {1..60}; do
            if curl -sf https://myapp.com/health; then
              echo "Health check passed!"
              exit 0
            fi
            echo "Attempt $i/60..."
            sleep 10
          done
          exit 1

  # ========================================
  # NOTIFY
  # ========================================
  notify:
    name: Notify
    needs: [build, deploy-staging, deploy-production]
    if: always()
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Determine status
        id: status
        run: |
          if [ "${{ needs.deploy-production.result }}" == "success" ]; then
            echo "result=deployed to production" >> $GITHUB_OUTPUT
            echo "color=good" >> $GITHUB_OUTPUT
          elif [ "${{ needs.deploy-staging.result }}" == "success" ]; then
            echo "result=deployed to staging" >> $GITHUB_OUTPUT
            echo "color=warning" >> $GITHUB_OUTPUT
          elif [ "${{ needs.build.result }}" == "success" ]; then
            echo "result=built successfully" >> $GITHUB_OUTPUT
            echo "color=good" >> $GITHUB_OUTPUT
          else
            echo "result=failed" >> $GITHUB_OUTPUT
            echo "color=danger" >> $GITHUB_OUTPUT
          fi

      - name: Send Slack notification
        if: vars.ENABLE_SLACK == 'true'
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: 'C0123456789'
          slack-message: |
            *${{ steps.status.outputs.result }}*
            Repo: ${{ github.repository }}
            Commit: ${{ github.sha }}
            Actor: ${{ github.actor }}
            Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        env:
          SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
```

---

## 2.11 Referencias

### Documentacao Oficial

1. Workflow syntax: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
2. Expressions: https://docs.github.com/en/actions/learn-github-actions/expressions
3. Contexts: https://docs.github.com/en/actions/learn-github-actions/contexts
4. Matrix builds: https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs
5. Containerized services: https://docs.github.com/en/actions/using-containerized-services
6. Workflow dispatch: https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#workflow_dispatch
7. Reusable workflows: https://docs.github.com/en/actions/using-workflows/reusing-workflows
8. Concurrency groups: https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency

### Recursos Adicionais

9. GitHub Actions YAML validator: https://github.com/actions/workflow-parser
10. GitHub Actions linting: https://github.com/rhysd/actionlint
11. GitHub Actions best practices: https://docs.github.com/en/actions/learn-github-actions/best-practices-for-github-actions
12. GitHub Actions security hardening: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions

### Exemplos

13. GitHub Actions workflow examples: https://github.com/actions/starter-workflows
14. Awesome GitHub Actions: https://github.com/sdras/awesome-actions
15. GitHub Actions by example: https://www.actionsbyexample.com/

---

## 2.12 Exercicios

### Exercicio 1: YAML Basico

Crie um workflow basico com:
- Nome "My First Workflow"
- Trigger push para main
- Um job que rode em ubuntu-latest
- Um step que use actions/checkout e outro que execute echo

### Exercicio 2: Triggers Detalhados

Crie um workflow com:
- Trigger push para branches main e develop
- Trigger pull_request para main com types [opened, synchronize]
- Filtro paths para src/** e package.json
- Filtro paths-ignore para docs/** e *.md

### Exercicio 3: Jobs com Dependencias

Crie um workflow com 4 jobs:
1. lint (sem dependencia)
2. test (depende de lint)
3. build (depende de test)
4. deploy (depende de build, so roda na main)

Use condicoes `if` apropriadas e `needs`.

### Exercicio 4: Matrix Strategy

Crie um workflow de teste com matrix:
- OS: ubuntu-latest, macos-latest, windows-latest
- Node: 18, 20, 22
- Exclude: windows + Node 18
- Include: ubuntu + Node 20 com extra=true
- fail-fast: false

### Exercicio 5: Services

Crie um workflow com:
- PostgreSQL service com health check
- Redis service com health check
- Steps que verifiquem a conexao com ambos

### Exercicio 6: Concurrency

Crie um workflow com:
- Concurrency group baseado em workflow + ref
- cancel-in-progress: true para CI
- cancel-in-progress: false para deploy

### Exercicio 7: Expressions

Crie um workflow que use:
- Pelo menos 5 contexts diferentes
- Funcoes: contains, startsWith, format, hashFiles
- Condicoes: if, failure(), always()
- Ternario operator

### Exercicio 8: Defaults

Crie um workflow com:
- Defaults de shell bash
- Defaults de working-directory
- Um step que sobrescreva o working-directory

### Exercicio 9: Workflow Completo

Crie um workflow full-stack com:
- Todos os triggers: push, PR, schedule, workflow_dispatch
- Jobs: lint, test (matrix), security, build, deploy
- Services: PostgreSQL, Redis
- Concurrency groups
- Artifacts upload/download
- Notifications

### Exercicio 10: Reusable Workflow

Crie:
1. Um workflow reutilizavel que aceite inputs (node-version, os) e secrets
2. Um workflow principal que chame o reutilizavel
---

*[Capítulo anterior: 01 — Introducao Github Actions](01-introducao-github-actions.md)*
*[Próximo capítulo: 03 — Triggers Eventos](03-triggers-eventos.md)*
