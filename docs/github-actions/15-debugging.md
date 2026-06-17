---
layout: default
title: "15-debugging"
---

# Capitulo 15 -- Debugging e Troubleshooting

> *"O debug comeca com logs. Logs comecam com visibilidade."*

---

## Objetivos de Aprendizado

1. Navegar e interpretar logs do GitHub Actions
2. Habilitar ACTIONS_STEP_DEBUG para logging detalhado
3. Usar Act para testar workflows localmente
4. Aplicar estrategias de rerun eficientes
5. Diagnosticar e resolver erros de timeout
6. Resolver erros comuns de YAML
7. Diagnosticar action not found
8. Resolver permission denied
9. Implementar debug passo a passo
10. Montar um checklist de debugging
11. Usar shell step debug com set -x
12. Configurar log groups
13. Usar GITHUB_STEP_SUMMARY para visibilidade
14. Debugar secrets e variaveis
15. Diagnosticar problemas de rede em runners

---

## 15.1 Reading Logs

### Acessar Logs

Os logs do GitHub Actions estao disponiveis na aba Actions do repositorio. Cada workflow run gera um registro completo de todos os jobs e steps executados.

```
1. Navegue ate a aba Actions do repositorio
2. Clique no workflow run que deseja inspecionar
3. Expanda o job desejado na barra lateral esquerda
4. Clique no step especifico para ver seus logs
```

### Estrutura dos Logs

```
Run actions/checkout@v4
Syncing repository: owner/repo
Getting Git metadata
Warning: Third party action has requested write permission
Setting up auth
  Setting up auth for owner/repo
  Persisting credentials to disk
  SUCCESS
  Cleaning up old auth tokens
Getting Git metadata
  git version 2.43.0
  git config --global --add safe.directory /home/runner/work/repo/repo
  git init /home/runner/work/repo/repo
  Initialized empty Git repository
  Entering 'repo'
  Fetching resolved ref
  git remote add origin https://github.com/owner/repo.git
  git config --global --add safe.directory /home/runner/work/repo/repo
  git fetch --force --tags --prune --prune-tags --progress --no-recurse-submodules origin +refs/heads/*:refs/remotes/origin/*
  remote: Enumerating objects: 1234, done.
  remote: Counting objects: 100% (1234/1234), done.
  remote: Compressing objects: 100% (567/567), done.
  Receiving objects: 100% (1234/1234), 123.45 KiB | 12.34 MiB/s, done.
  Resolving deltas: 100% (890/890), done.
  From https://github.com/owner/repo
   * [new branch]      main       -> origin/main
  git checkout --progress --force -B main refs/remotes/origin/main
  Switched to a new branch 'main'
```

### Niveis de Log

| Nivel | Cor | Visivel por Padrao | Conteudo |
|-------|-----|---------------------|----------|
| Debug | Cinza | Somente com ACTIONS_STEP_DEBUG | Variaveis internas, HTTP requests |
| Notice | Verde | Sim | Informativo, nao e erro |
| Warning | Amarelo | Sim | Alertas que nao impedem execucao |
| Error | Vermelho | Sim | Erros que falham o step |
| Fatal | Vermelho escuro | Sim | Erros que abortam o workflow |

### Log Groups

Log groups permitem organizar a saida em secoes colapsaveis. Sao uteis para output verbose que pode poluir os logs.

```yaml
steps:
  - name: Build with organized logs
    run: |
      echo "::group::Installing dependencies"
      npm ci
      echo "::endgroup::"

      echo "::group::Running tests"
      npm test
      echo "::endgroup::"

      echo "::group::Building project"
      npm run build
      echo "::endgroup::"
```

### Log Group com Titulo Dinamico

```yaml
steps:
  - name: Test matrix package
    run: |
      echo "::group::Testing ${{ matrix.package }}"
      cd packages/${{ matrix.package }}
      npm ci
      npm test
      echo "::endgroup::"
```

### Log Group Aninhado

```yaml
steps:
  - name: Nested log groups
    run: |
      echo "::group::Level 1"
      echo "  ::group::Level 2"
      echo "    content"
      echo "  ::endgroup::"
      echo "::endgroup::"
```

### Ocultar Saida

```yaml
steps:
  - name: Run with hidden output
    run: |
      echo "::echo::on"
      echo "This will be echoed to logs"
      echo "::echo::off"
      echo "This will NOT appear in logs"
```

### Masks de Saida

```yaml
steps:
  - name: Mask sensitive output
    run: |
      echo "::add-mask::sensitive-value-123"
      echo "The value sensitive-value-123 is now masked"
      # Output: The value *** is now masked
```

### Arquivos de Log

Cada workflow run gera arquivos de log que podem ser baixados:

```
1. Va ate a aba Actions
2. Selecione o workflow run
3. Clique em "..." no canto superior direito
4. Selecione "Download log archive"
```

O archive contem um arquivo `.txt` para cada job, organizados em pastas.

### Extraindo Informacoes dos Logs

```yaml
steps:
  - name: Build with log capture
    id: build
    run: |
      npm run build 2>&1 | tee build.log
      BUILD_EXIT=$?
      echo "build_exit=$BUILD_EXIT" >> "$GITHUB_OUTPUT"

      if [ $BUILD_EXIT -ne 0 ]; then
        echo "::error::Build failed with exit code $BUILD_EXIT"
        tail -50 build.log
      fi

  - name: Upload build logs on failure
    if: failure()
    uses: actions/upload-artifact@v4
    with:
      name: build-logs
      path: build.log
      retention-days: 7
```

### Filtro de Logs com Grep

```yaml
steps:
  - name: Run tests and capture errors
    run: |
      npm test 2>&1 | tee test-output.log
      TEST_EXIT=${PIPESTATUS[0]}

      if [ $TEST_EXIT -ne 0 ]; then
        echo "::group::Failed tests"
        grep -E "(FAIL|✕|●)" test-output.log
        echo "::endgroup::"
      fi

      exit $TEST_EXIT
```

### Saida Estruturada

```yaml
steps:
  - name: Structured output
    run: |
      echo "::group::Build Configuration"
      echo "Node version: $(node --version)"
      echo "NPM version: $(npm --version)"
      echo "Platform: $(uname -a)"
      echo "Working directory: $(pwd)"
      echo "::endgroup::"

      echo "::group::Dependencies"
      npm ls --depth=0
      echo "::endgroup::"

      echo "::group::Environment Variables"
      env | sort | grep -v -E "(TOKEN|SECRET|KEY|PASSWORD)" || true
      echo "::endgroup::"
```

### Annotation de Erros

```yaml
steps:
  - name: Lint with annotations
    run: |
      npx eslint . --format compact 2>&1 | while IFS= read -r line; do
        if [[ "$line" == *":"* ]]; then
          FILE=$(echo "$line" | cut -d: -f1)
          LINE=$(echo "$line" | cut -d: -f2)
          COL=$(echo "$line" | cut -d: -f3)
          MSG=$(echo "$line" | cut -d: -f4-)
          echo "::error file=$FILE,line=$LINE,col=$COL::$MSG"
        fi
      done
```

---

## 15.2 ACTIONS_STEP_DEBUG

### Habilitar Debug Logging

Debug logging pode ser habilitado de duas formas:

**Metodo 1: Repository secret**

```
Settings > Secrets and variables > Actions > New repository secret
Nome: ACTIONS_STEP_DEBUG
Valor: true
```

**Metodo 2: variavel de ambiente do workflow**

```yaml
env:
  ACTIONS_STEP_DEBUG: true
```

### O Que o Debug Habilita

Quando `ACTIONS_STEP_DEBUG` esta habilitado:

1. O valor de `runner.debug` retorna `'1'`
2. Acoes que suportam debug mostram informacoes detalhadas
3. Requests HTTP sao logados
4. Variaveis internas sao expostas
5. Logs de networking sao detalhados

### Exemplo com Debug

```yaml
steps:
  - name: Check debug status
    run: |
      echo "Runner debug: ${{ runner.debug }}"
      echo "Debug mode: ${{ runner.debug == '1' }}"

  - name: Verbose checkout
    uses: actions/checkout@v4
    with:
      fetch-depth: 0
      debug: true
```

### Debug com set -x

```yaml
steps:
  - name: Shell debug with set -x
    run: |
      set -x  # Habilita debug do shell
      echo "Starting build"
      npm ci
      echo "Dependencies installed"
      npm run build
      echo "Build complete"
      set +x  # Desabilita debug
```

### Debug de Variaveis de Ambiente

```yaml
steps:
  - name: Debug environment variables
    run: |
      echo "::group::Runner Variables"
      echo "runner.os = ${{ runner.os }}"
      echo "runner.arch = ${{ runner.arch }}"
      echo "runner.name = ${{ runner.name }}"
      echo "runner.debug = ${{ runner.debug }}"
      echo "runner.temp = ${{ runner.temp }}"
      echo "runner.tool_cache = ${{ runner.tool_cache }}"
      echo "::endgroup::"

      echo "::group::GitHub Context"
      echo "github.event_name = ${{ github.event_name }}"
      echo "github.ref = ${{ github.ref }}"
      echo "github.sha = ${{ github.sha }}"
      echo "github.repository = ${{ github.repository }}"
      echo "github.workspace = ${{ github.workspace }}"
      echo "::endgroup::"

      echo "::group::All Environment Variables"
      env | sort
      echo "::endgroup::"
```

### Debug de Outputs

```yaml
steps:
  - name: Step 1
    id: step1
    run: |
      echo "result=hello-world" >> "$GITHUB_OUTPUT"
      echo "debug-result" >> "$GITHUB_STEP_OUTPUT"

  - name: Debug outputs
    run: |
      echo "::group::Step Outputs"
      echo "step1.result = ${{ steps.step1.outputs.result }}"
      echo "::endgroup::"
```

### Debug de Secrets (Seguro)

```yaml
steps:
  - name: Debug secrets (safe)
    run: |
      # NUNCA faca echo de secrets diretamente
      # Use mask para proteger valores
      echo "::group::Secrets Status"
      echo "SECRET_A definido: ${{ secrets.SECRET_A != '' }}"
      echo "SECRET_B definido: ${{ secrets.SECRET_B != '' }}"
      echo "SECRET_C definido: ${{ secrets.SECRET_C != '' }}"
      echo "::endgroup::"

      # Verificar se secrets estao vazios
      if [ -z "${{ secrets.SECRET_A }}" ]; then
        echo "::error::SECRET_A is empty or not set"
        exit 1
      fi
```

### Debug de Caches

```yaml
steps:
  - name: Debug cache status
    run: |
      echo "::group::Cache Debug"
      echo "Cache key: ${{ steps.cache.outputs.cache-hit }}"
      echo "Cache hit: ${{ steps.cache.outputs.cache-hit == 'true' }}"
      echo "::endgroup::"
    id: cache-debug

  - name: Setup Node with cache debug
    uses: actions/setup-node@v4
    with:
      node-version: '20'
      cache: 'npm'

  - name: Show cache info
    run: |
      echo "::group::NPM Cache"
      npm cache ls 2>/dev/null | head -20
      echo "Cache location: $(npm config get cache)"
      echo "::endgroup::"
```

### Debug com ACTIONS_STEP_DEBUG em Condicoes

```yaml
steps:
  - name: Conditional debug
    run: |
      if [ "${{ runner.debug }}" == "1" ]; then
        echo "::group::Verbose Debug Mode"
        echo "All env vars:"
        env | sort
        echo ""
        echo "Disk usage:"
        df -h
        echo ""
        echo "Memory usage:"
        free -h
        echo "::endgroup::"
      else
        echo "Debug mode is off. Set ACTIONS_STEP_DEBUG=true for verbose output."
      fi
```

---

## 15.3 Act: Testar Localmente

### Instalacao

```bash
# macOS com Homebrew
brew install act

# Linux com script de instalacao
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows com Chocolatey
choco install act

# Go install
go install github.com/nektos/act@latest
```

### Comandos Basicos

```bash
# Listar workflows detectados
act -l

# Listar eventos disponiveis
act -l --list

# Rodar o workflow de push padrao
act push

# Rodar o workflow de pull_request
act pull_request

# Rodar com evento especifico
act -e event.json

# Rodar job especifico
act -j build

# Rodar job especifico com push
act push -j build
```

### Configuracao do Act

```yaml
# .actrc
--container-architecture linux/amd64
--platform ubuntu-latest=catthehacker/ubuntu:act-latest
--platform ubuntu-22.04=catthehacker/ubuntu:act-22.04
--platform macos-latest=catthehacker/macos:act-latest
--platform windows-latest=catthehacker/windows:act-latest
```

### Act com Secrets

```bash
# Usar arquivo de secrets
act push --secret-file .secrets

# Passar secret individual
act push -s MY_SECRET=value

# Usar .env como variaveis de ambiente
act push --env-file .env
```

### Arquivo .secrets

```
MY_SECRET=my-secret-value
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJalr...
DATABASE_URL=postgresql://localhost:5432/test
```

### Act com Docker

```bash
# Rodar com Docker (padrao)
act push

# Rodar sem Docker (usa container de imagem leve)
act push --container-architecture linux/amd64

# Rodar com bind mounts
act push --bind

# Rodar com rm (remover container apos execucao)
act push --rm
```

### Act com Multiplos Jobs

```bash
# Rodar todos os jobs
act push

# Rodar job especifico
act push -j lint
act push -j test
act push -j build

# Rodar job e seus dependentes
act push -j test --jobgraph
```

### Act com Platform Mapping

```bash
# Mapear runners para imagens Docker
act push \
  --platform ubuntu-latest=catthehacker/ubuntu:act-latest \
  --platform ubuntu-22.04=catthehacker/ubuntu:act-22.04 \
  --platform macos-latest=catthehacker/macos:act-latest
```

### Act com Artefatos

```bash
# Rodar com artefatos
act push --artifact-server-path /tmp/act-artifacts

# Rodar e acessar artefatos
act push --artifact-server-path ./act-artifacts
```

### Act com Eventos Customizados

```bash
# Criar arquivo de evento
cat > custom-event.json << 'EOF'
{
  "action": "completed",
  "workflow_run": {
    "id": 12345,
    "name": "CI",
    "conclusion": "success"
  }
}
EOF

# Rodar com evento customizado
act workflow_run -e custom-event.json
```

### Act com workflow_dispatch

```bash
# Criar arquivo de inputs
cat > dispatch-inputs.json << 'EOF'
{
  "inputs": {
    "environment": "staging",
    "skip_tests": "false",
    "notify": "true"
  }
}
EOF

# Rodar com inputs
act workflow_dispatch -e dispatch-inputs.json
```

### Act com Containers de Servico

```yaml
# Act suporta services containers como no GitHub Actions
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
```

### Act com Outputs

```bash
# Rodar e capturar outputs
act push --output event.json

# Ver outputs
cat event.json | jq '.outputs'
```

### Act com Repositorios de Dependencia

```bash
# Act resolve actions de repositorios
# Para actions locais, use bind mount
act push --bind

# Para actions de repositorios privados, configure GITHUB_TOKEN
act push -s GITHUB_TOKEN=ghp_...
```

### Act com Network

```bash
# Rodar com rede Docker personalizada
act push --network host

# Rodar com DNS personalizado
act push --dns 8.8.8.8
```

### Act com Workflows Aninhados

```bash
# Act suporta workflow_call
# Se seu workflow chama outro, act resolve automaticamente

# Para forcar resolucao local
act push --use-new-action-cache
```

### Comparacao: Act vs GitHub Actions

| Aspecto | Act | GitHub Actions |
|---------|-----|----------------|
| Velocidade | Instantaneo (local) | 30-60s cold start |
| Recursos | Seu hardware | GitHub-hosted runners |
| Network | Local | GitHub network |
| Services | Docker local | Docker na cloud |
| Secrets | Arquivo .secrets | Repository secrets |
| Artefatos | Local | GitHub storage |
| Permissions | Sua maquina | GitHub permissions |
| Debugging | Controle total | ACTIONS_STEP_DEBUG |

### Act com Matrix

```bash
# Act suporta matrix builds
act push -j test

# O act respeita a configuracao de matrix do workflow
# e executa cada combinacao localmente
```

### Act com Artifacts

```yaml
# Para testar artifacts localmente
steps:
  - uses: actions/upload-artifact@v4
    with:
      name: my-artifact
      path: dist/
```

```bash
# Act salva artifacts localmente
act push --artifact-server-path ./artifacts
ls -la ./artifacts/
```

### Act com Caches

```bash
# Act suporta caches
# O cache e mantido entre execucoes locais

# Limpar cache
rm -rf /tmp/act/cache

# Ver cache
ls -la /tmp/act/cache/
```

### Act com Reusable Workflows

```bash
# Act resolve workflow_call
# O workflow chamado deve estar no mesmo repositorio ou acessivel

act push
# O act detecta automaticamente workflows reutilizaveis
```

---

## 15.4 Rerun Strategies

### Opcoes de Rerun

| Opcao | Descricao | Quando Usar |
|-------|-----------|-------------|
| Re-run all jobs | Re-executa todos os jobs do workflow | Falha geral ou problema transitorio |
| Re-run failed jobs | Re-executa apenas jobs que falharam | Falha em jobs especificos |
| Re-run from failed | Re-executa do job que falhou em diante | Jobs dependentes podem ter falhado |

### Rerun com a API

```bash
# Rerun todos os jobs
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/rerun"

# Rerun apenas jobs que falharam
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/rerun-failed-jobs"

# Rerun job especifico
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/jobs/JOB_ID/rerun"
```

### Rerun com gh CLI

```bash
# Rerun todos os jobs
gh run rerun RUN_ID

# Rerun jobs que falharam
gh run rerun RUN_ID --failed

# Rerun job especifico
gh run rerun RUN_ID --job JOB_ID
```

### Rerun Automatico com Retry

```yaml
name: Retry Workflow

on:
  workflow_dispatch:
    inputs:
      max_retries:
        description: "Numero maximo de tentativas"
        required: false
        default: '3'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy with retry
        id: deploy
        run: |
          MAX_RETRIES=${{ inputs.max_retries || 3 }}
          RETRY_COUNT=0

          while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            echo "Attempt $((RETRY_COUNT + 1)) of $MAX_RETRIES"

            if deploy-command; then
              echo "Deploy succeeded on attempt $((RETRY_COUNT + 1))"
              echo "status=success" >> "$GITHUB_OUTPUT"
              exit 0
            fi

            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
              echo "Waiting 30s before retry..."
              sleep 30
            fi
          done

          echo "Deploy failed after $MAX_RETRIES attempts"
          echo "status=failure" >> "$GITHUB_OUTPUT"
          exit 1
```

### Rerun Condicional

```yaml
name: Conditional Rerun

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  notify-rerun:
    needs: test
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Check if should auto-retry
        run: |
          RUN_COUNT=$(gh run list --workflow=ci.yml --limit=1 --json databaseId | jq '.[0].databaseId')
          echo "Current run: $RUN_COUNT"

          # Verificar se ja tentamos 2 vezes
          PREVIOUS_RUNS=$(gh run list --workflow=ci.yml --limit=5 --json conclusion | jq '[.[] | select(.conclusion == "failure")] | length')
          echo "Previous failures: $PREVIOUS_RUNS"

          if [ "$PREVIOUS_RUNS" -lt 2 ]; then
            echo "Auto-retrying..."
            gh run rerun ${{ github.run_id }} --failed
          else
            echo "Too many failures, not retrying"
          fi
```

### Rerun com Exclusao de Cache

```yaml
name: Rerun Without Cache

on:
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Force fresh install
        if: github.event.inputs.force_fresh == 'true'
        run: |
          rm -rf node_modules
          npm cache clean --force

      - run: npm ci
      - run: npm test
```

---

## 15.5 Timeouts

### Tipos de Timeout

| Tipo | Padrao | Maximo | Configuracao |
|------|--------|--------|--------------|
| Job timeout | 360 min (6h) | 6h | `timeout-minutes` no job |
| Step timeout | Sem limite | Sem limite | `timeout-minutes` no step |
| Workflow timeout | Sem limite | Sem limite | `timeout-minutes` no workflow |

### Configuracao de Timeout

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        timeout-minutes: 5
        run: npm ci

      - name: Build
        timeout-minutes: 10
        run: npm run build

      - name: Test
        timeout-minutes: 15
        run: npm test
```

### Erro de Timeout

```
Error: The job running on runner [runner-name] has exceeded the maximum execution time of 360 minutes.
```

### Diagnosticar Timeout

```yaml
steps:
  - name: Monitor execution time
    run: |
      START_TIME=$(date +%s)
      echo "Start time: $(date)"

      # Simular trabalho
      sleep 60

      END_TIME=$(date +%s)
      DURATION=$((END_TIME - START_TIME))
      echo "Duration: ${DURATION}s"
      echo "Duration minutes: $((DURATION / 60))"
```

### Timeout com Notificacao

```yaml
name: Timeout Monitor

on:
  push:
    branches: [main]

jobs:
  long-running:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    steps:
      - uses: actions/checkout@v4

      - name: Long running task
        id: longtask
        run: |
          echo "Starting long task..."
          for i in $(seq 1 60); do
            echo "Progress: $i%"
            sleep 60
          done
          echo "Task complete"

      - name: Notify on timeout
        if: failure() && steps.longtask.outcome == 'failure'
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {"text": "Job timed out after ${{ job.timeout-minutes }} minutes"}
```

### Timeout por Step

```yaml
steps:
  - name: Fast step
    timeout-minutes: 2
    run: npm run lint

  - name: Medium step
    timeout-minutes: 10
    run: npm run test

  - name: Slow step
    timeout-minutes: 30
    run: npm run build
```

### Evitar Timeouts

```yaml
steps:
  - name: Build with progress
    run: |
      echo "Step 1/5: Installing..."
      npm ci
      echo "Step 2/5: Linting..."
      npm run lint
      echo "Step 3/5: Type checking..."
      npm run typecheck
      echo "Step 4/5: Testing..."
      npm test
      echo "Step 5/5: Building..."
      npm run build
      echo "Done!"
```

---

## 15.6 Common Errors

### Erro: YAML Syntax Error

```
Error: Invalid workflow file at .github/workflows/ci.yml
```

**Causas comuns:**

1. Indentacao incorreta (usar 2 espacos)
2. Caracteres especiais em strings
3. Aspas nao balanceadas
4. Dois-pontos extras ou faltando

**Solucao:**

```yaml
# ERRADO - indentacao incorreta
jobs:
build:   # deve ter 2 espacos de indentacao
  runs-on: ubuntu-latest

# CORRETO
jobs:
  build:
    runs-on: ubuntu-latest
```

```yaml
# ERRADO - string com dois-pontos sem aspas
env:
  DATABASE_URL: postgresql://user:pass@host:5432/db

# CORRETO
env:
  DATABASE_URL: "postgresql://user:pass@host:5432/db"
```

### Erro: Action Not Found

```
Error: Unable to resolve action `owner/action@v1`
```

**Causas:**

1. Nome da action incorreto
2. Tag ou branch inexistente
3. Repositorio privado sem acesso
4. Typo no nome

**Solucao:**

```yaml
# ERRADO
- uses: actions/checkout@v2

# CORRETO - usar versao atual
- uses: actions/checkout@v4

# OU usar SHA para maior seguranca
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

### Erro: Permission Denied

```
Error: HttpError: Resource not accessible by integration
```

**Causas:**

1. Token sem permissao necessaria
2. Permissao insuficiente para o contexto
3. Branch protection bloqueando

**Solucao:**

```yaml
name: CI

permissions:
  contents: read
  packages: write
  pull-requests: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm publish
```

### Erro: Runner Offline

```
Error: The runner has received a shutdown signal.
```

**Causas:**

1. Runner self-hosted desligado
2. Problema de rede
3. GitHub-hosted runner em manutencao

**Solucao:**

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    # Adicionar retry para runners instaveis
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - run: npm ci && npm test
```

### Erro: Cache Miss

```
Warning: Failed to restore cache
```

**Solucao:**

```yaml
steps:
  - name: Cache with restore keys
    uses: actions/cache@v4
    with:
      path: node_modules
      key: ${{ runner.os }}-modules-${{ hashFiles('**/package-lock.json') }}
      restore-keys: |
        ${{ runner.os }}-modules-
        ${{ runner.os }}-
```

### Erro: Disk Space

```
Error: No space left on device
```

**Solucao:**

```yaml
steps:
  - name: Free disk space
    run: |
      sudo rm -rf /usr/share/dotnet
      sudo rm -rf /opt/ghc
      sudo rm -rf "/usr/local/share/boost"
      sudo rm -rf /opt/hostedtoolcache
      df -h

  - uses: actions/checkout@v4
  - run: npm ci && npm test
```

### Erro: Network Timeout

```
Error: timeout of 30000ms exceeded
```

**Solucao:**

```yaml
steps:
  - name: Install with retry
    run: |
      for i in 1 2 3; do
        npm ci && break
        echo "Attempt $i failed, retrying in 30s..."
        sleep 30
      done
```

---

## 15.7 YAML Errors

### Erros Comuns de YAML

| Erro | Exemplo | Correcao |
|------|---------|----------|
| Indentacao | 4 espacos onde 2 sao esperados | Usar 2 espacos |
| String com : | `url: http://x:1` | Usar aspas: `"url"` |
| Caracter especial | `key: value{test}` | Usar aspas |
| Lista vazia | `- ` (com trailing space) | Remover trailing space |
| Booleano | `yes` / `no` | Usar `true` / `false` |

### YAML Linter

```yaml
# Adicionar step para validar YAML
steps:
  - name: Validate YAML
    run: |
      npm install -g yaml-lint
      yamllint -c .yamllint.yml .github/workflows/
```

### Arquivo .yamllint.yml

```yaml
---
extends: default

rules:
  line-length:
    max: 200
    allow-non-breakable-words: true
    allow-non-breakable-inline-mappings: true
  truthy:
    check-keys: false
  comments:
    min-spaces-from-content: 1
  document-start: disable
```

### Validacao com actionlint

```bash
# Instalar actionlint
go install github.com/rhysd/actionlint/cmd/actionlint@latest

# Rodar actionlint
actionlint

# Rodar com output detalhado
actionlint -verbose
```

### YAML Multi-line

```yaml
# Usar | para multi-line literal
steps:
  - name: Multi-line script
    run: |
      echo "Line 1"
      echo "Line 2"
      echo "Line 3"

# Usar > para multi-line folded
steps:
  - name: Folded string
    run: >
      echo "This is a very long command
      that spans multiple lines
      but is treated as one line"
```

### YAML com Template Literals

```yaml
steps:
  - name: Template in YAML
    run: |
      echo "Hello ${{ github.actor }}"
      echo "Branch: ${{ github.ref_name }}"
      echo "SHA: ${{ github.sha }}"
```

---

## 15.8 Action Not Found

### Diagnosticar

```yaml
steps:
  - name: Debug action resolution
    run: |
      echo "Checking action availability..."
      echo "GITHUB_WORKSPACE: ${{ github.workspace }}"
      echo "GITHUB_ACTION_PATH: ${{ github.action_path }}"
```

### Causas e Solucoes

1. **Nome incorreto**: Verifique o nome completo `owner/repo@ref`
2. **Tag inexistente**: Verifique as tags disponiveis no repositorio da action
3. **Repositorio privado**: Configure `GITHUB_TOKEN` para acesso
4. **Fork**: Use `owner/repo@SHA` ao inves de tags

### Usar SHA em vez de Tags

```yaml
# Mais seguro - pin por SHA
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
  with:
    repository: owner/repo
    ref: main

# Menos seguro - pin por tag
- uses: actions/checkout@v4
```

### Actions de Repositorios Privados

```yaml
steps:
  - name: Use private action
    uses: my-org/private-action@v1
    env:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Composite Actions Locais

```yaml
steps:
  - name: Use local composite action
    uses: ./.github/actions/my-action
    with:
      input1: value1
```

---

## 15.9 Permission Denied

### Diagnosticar

```yaml
steps:
  - name: Check permissions
    run: |
      echo "Token permissions:"
      curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
        "https://api.github.com/repos/${{ github.repository }}/permissions" | jq .
```

### Erros Comuns e Solucoes

**Erro: Resource not accessible by integration**

```yaml
# SOLUCAO 1: Adicionar permissions no workflow
name: CI
permissions:
  contents: read
  issues: write
  pull-requests: write

# SOLUCAO 2: Permissao especifica no job
jobs:
  comment:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Test comment'
            })
```

**Erro: Permission to write to repository denied**

```yaml
# SOLUCAO: Usar GITHUB_TOKEN com permissao correta
jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - name: Create release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

**Erro: Protected branch**

```yaml
# SOLUCAO: Configurar branch protection rules
# Settings > Branches > Add rule
# ou usar GitHub API
```

### Permissoes por Contexto

| Contexto | Permissao Necessaria | Exemplo |
|----------|---------------------|---------|
| Repositorio | contents: write | Push, criar releases |
| Issues | issues: write | Criar/comentar issues |
| PR | pull-requests: write | Criar/comentar PRs |
| Packages | packages: write | Push de imagens |
| Actions | actions: write | Dispatch de workflows |
| Deployments | deployments: write | Criar deployments |

---

## 15.10 Step-by-Step Debugging

### Workflow de Debug Completo

```yaml
name: Debug Workflow

on:
  push:
    branches: [main]

jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      # ============================================================
      # STEP 1: Informacoes do ambiente
      # ============================================================
      - name: Environment info
        run: |
          echo "::group::System Information"
          echo "OS: $(uname -a)"
          echo "Hostname: $(hostname)"
          echo "User: $(whoami)"
          echo "PWD: $(pwd)"
          echo "Disk space:"
          df -h /
          echo "Memory:"
          free -h
          echo "::endgroup::"

      # ============================================================
      # STEP 2: Informacoes do Git
      # ============================================================
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Git info
        run: |
          echo "::group::Git Information"
          echo "Git version: $(git --version)"
          echo "Current branch: $(git branch --show-current)"
          echo "Current SHA: $(git rev-parse HEAD)"
          echo "Remote branches:"
          git branch -r
          echo "Last 5 commits:"
          git log --oneline -5
          echo "::endgroup::"

      # ============================================================
      # STEP 3: Informacoes do Node
      # ============================================================
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Node info
        run: |
          echo "::group::Node.js Information"
          echo "Node version: $(node --version)"
          echo "NPM version: $(npm --version)"
          echo "NPM config:"
          npm config list
          echo "NPM cache:"
          npm cache ls 2>/dev/null | wc -l
          echo "::endgroup::"

      # ============================================================
      # STEP 4: Informacoes do GitHub
      # ============================================================
      - name: GitHub context
        run: |
          echo "::group::GitHub Context"
          echo "Event: ${{ github.event_name }}"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Repository: ${{ github.repository }}"
          echo "Actor: ${{ github.actor }}"
          echo "Workflow: ${{ github.workflow }}"
          echo "Run ID: ${{ github.run_id }}"
          echo "Run number: ${{ github.run_number }}"
          echo "Action: ${{ github.action }}"
          echo "::endgroup::"

      # ============================================================
      # STEP 5: Debug de secrets
      # ============================================================
      - name: Secrets status
        run: |
          echo "::group::Secrets Status"
          echo "SECRET_A definido: ${{ secrets.SECRET_A != '' }}"
          echo "SECRET_B definido: ${{ secrets.SECRET_B != '' }}"
          echo "SECRET_C definido: ${{ secrets.SECRET_C != '' }}"
          echo "::endgroup::"

      # ============================================================
      # STEP 6: Debug de variaveis
      # ============================================================
      - name: Variables debug
        run: |
          echo "::group::Environment Variables"
          env | sort | grep -v -E "(TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL)" || true
          echo "::endgroup::"

      # ============================================================
      # STEP 7: Build com logs
      # ============================================================
      - name: Build
        id: build
        run: |
          echo "::group::Build Output"
          npm ci 2>&1 | tee build.log
          BUILD_EXIT=${PIPESTATUS[0]}
          echo "::endgroup::"

          if [ $BUILD_EXIT -ne 0 ]; then
            echo "::error::npm ci failed with exit code $BUILD_EXIT"
            echo "::group::Error details"
            tail -50 build.log
            echo "::endgroup::"
          fi

          echo "build_exit=$BUILD_EXIT" >> "$GITHUB_OUTPUT"

      # ============================================================
      # STEP 8: Upload logs on failure
      # ============================================================
      - name: Upload debug logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: debug-logs-${{ github.run_id }}
          path: |
            build.log
            *.log
          retention-days: 7
```

### Debug de Performance

```yaml
name: Performance Debug

on:
  push:
    branches: [main]

jobs:
  perf-debug:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Measure step times
        run: |
          START_TOTAL=$(date +%s%N)

          START=$(date +%s%N)
          npm ci
          END=$(date +%s%N)
          echo "npm ci: $(( (END - START) / 1000000 ))ms"

          START=$(date +%s%N)
          npm run build
          END=$(date +%s%N)
          echo "npm run build: $(( (END - START) / 1000000 ))ms"

          START=$(date +%s%N)
          npm test
          END=$(date +%s%N)
          echo "npm test: $(( (END - START) / 1000000 ))ms"

          END_TOTAL=$(date +%s%N)
          echo "Total: $(( (END_TOTAL - START_TOTAL) / 1000000 ))ms"
```

### Debug de Concorrencia

```yaml
name: Concurrency Debug

on:
  push:
    branches: [main]

concurrency:
  group: debug-${{ github.ref }}
  cancel-in-progress: true

jobs:
  check-concurrency:
    runs-on: ubuntu-latest
    steps:
      - name: Concurrency info
        run: |
          echo "::group::Concurrency Information"
          echo "Workflow: ${{ github.workflow }}"
          echo "Ref: ${{ github.ref }}"
          echo "Run ID: ${{ github.run_id }}"
          echo "Run number: ${{ github.run_number }}"
          echo "Concurrency group: debug-${{ github.ref }}"
          echo "::endgroup::"
```

---

## 15.11 Debugging Checklist

### Checklist Pre-Commit

```markdown
## Antes de Commitar

- [ ] YAML valido (actionlint ou yamllint)
- [ ] Indentacao correta (2 espacos)
- [ ] Strings com caracteres especiais entre aspas
- [ ] Actions pinadas por SHA ou tag estavel
- [ ] Secrets nao hardcoded
- [ ] Permissoes explicitas
- [ ] Timeout configurado
- [ ] Concurrency groups configurados
- [ ] Cache configurado
- [ ] Path filters configurados (se monorepo)
```

### Checklist Pre-Merge

```markdown
## Antes de Merge

- [ ] Workflow roda sem erros no PR
- [ ] Todos os jobs passam
- [ ] Logs revisados para warnings
- [ ] Secrets e variaveis configurados no repo destino
- [ ] Branch protection rules ativas
- [ ] Required reviews configurados
- [ ] Status checks obrigatorios definidos
- [ ] Deploy rules configuradas
```

### Checklist de Debug

```markdown
## Quando o Workflow Falha

- [ ] Verificar logs do job que falhou
- [ ] Verificar se e erro de sintaxe YAML
- [ ] Verificar se actions existem e estao acessiveis
- [ ] Verificar permissoes do token
- [ ] Verificar se secrets estao definidos
- [ ] Verificar timeouts
- [ ] Verificar espaco em disco
- [ ] Verificar conectividade de rede
- [ ] Testar localmente com Act
- [ ] Habilitar ACTIONS_STEP_DEBUG para detalhes
```

### Template de Bug Report

```markdown
## Workflow Falhou

### Workflow
- Nome: [nome do workflow]
- Run ID: [run id]
- Branch: [branch]
- Commit: [sha]

### Erro
```
[cole o erro completo aqui]
```

### Contexto
- O que foi alterado: [descricao da mudanca]
- Que jobs falharam: [lista de jobs]
- Historico: [era a primeira vez ou ja falhou antes?]

### Tentativas
- [ ] Re-run all jobs
- [ ] Re-run failed jobs
- [ ] Testar com Act localmente
- [ ] Habilitar ACTIONS_STEP_DEBUG
```

---

## 15.12 Debug de Network em Runners

### Diagnosticar Problemas de Rede

```yaml
steps:
  - name: Network diagnostics
    run: |
      echo "::group::DNS Resolution"
      nslookup github.com
      nslookup registry.npmjs.org
      echo "::endgroup::"

      echo "::group::Connectivity"
      curl -I https://github.com
      curl -I https://registry.npmjs.org
      echo "::endgroup::"

      echo "::group::Proxy Settings"
      echo "HTTP_PROXY: $HTTP_PROXY"
      echo "HTTPS_PROXY: $HTTPS_PROXY"
      echo "NO_PROXY: $NO_PROXY"
      echo "::endgroup::"

      echo "::group::Firewall"
      sudo iptables -L -n 2>/dev/null || echo "Cannot check iptables"
      echo "::endgroup::"
```

### Proxy em Runners

```yaml
env:
  HTTP_PROXY: "http://proxy.example.com:8080"
  HTTPS_PROXY: "http://proxy.example.com:8080"
  NO_PROXY: "localhost,127.0.0.1,.example.com"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
```

### Timeout de Rede

```yaml
steps:
  - name: Install with network retry
    run: |
      npm config set fetch-retries 5
      npm config set fetch-retry-mintimeout 60000
      npm config set fetch-retry-maxtimeout 120000
      npm ci
```

### GitHub-hosted Runner Network

```yaml
steps:
  - name: Check runner network
    run: |
      echo "::group::Runner Network Info"
      echo "Public IP:"
      curl -s https://api.ipify.org
      echo ""
      echo "Internal IP:"
      hostname -I
      echo ""
      echo "DNS servers:"
      cat /etc/resolv.conf
      echo "::endgroup::"
```

---

## 15.13 GITHUB_STEP_SUMMARY

### Usar Summary para Visibilidade

```yaml
steps:
  - name: Run tests
    id: tests
    run: |
      npm test 2>&1 | tee test-output.txt
      TEST_EXIT=${PIPESTATUS[0]}
      echo "exit_code=$TEST_EXIT" >> "$GITHUB_OUTPUT"

      # Extrair metricas
      TOTAL=$(grep -c "PASS\|FAIL" test-output.txt || echo "0")
      PASSED=$(grep -c "PASS" test-output.txt || echo "0")
      FAILED=$(grep -c "FAIL" test-output.txt || echo "0")

      echo "total=$TOTAL" >> "$GITHUB_OUTPUT"
      echo "passed=$PASSED" >> "$GITHUB_OUTPUT"
      echo "failed=$FAILED" >> "$GITHUB_OUTPUT"

  - name: Generate summary
    if: always()
    run: |
      echo "## Test Results" >> "$GITHUB_STEP_SUMMARY"
      echo "" >> "$GITHUB_STEP_SUMMARY"
      echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
      echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
      echo "| Total | ${{ steps.tests.outputs.total }} |" >> "$GITHUB_STEP_SUMMARY"
      echo "| Passed | ${{ steps.tests.outputs.passed }} |" >> "$GITHUB_STEP_SUMMARY"
      echo "| Failed | ${{ steps.tests.outputs.failed }} |" >> "$GITHUB_STEP_SUMMARY"
      echo "" >> "$GITHUB_STEP_SUMMARY"

      if [ "${{ steps.tests.outputs.exit_code }}" == "0" ]; then
        echo "> **Status: PASS**" >> "$GITHUB_STEP_SUMMARY"
      else
        echo "> **Status: FAIL**" >> "$GITHUB_STEP_SUMMARY"
      fi
```

### Summary com Tabela de Build

```yaml
steps:
  - name: Build matrix summary
    run: |
      echo "## Build Matrix" >> "$GITHUB_STEP_SUMMARY"
      echo "" >> "$GITHUB_STEP_SUMMARY"
      echo "| Package | OS | Node | Status |" >> "$GITHUB_STEP_SUMMARY"
      echo "|---------|-----|------|--------|" >> "$GITHUB_STEP_SUMMARY"
      echo "| core | ubuntu | 20 | pass |" >> "$GITHUB_STEP_SUMMARY"
      echo "| api | ubuntu | 20 | pass |" >> "$GITHUB_STEP_SUMMARY"
      echo "| web | ubuntu | 20 | fail |" >> "$GITHUB_STEP_SUMMARY"
```

---

## 15.14 Debug de Services Containers

### Diagnosticar Services

```yaml
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
      - name: Check postgres health
        run: |
          echo "Waiting for postgres..."
          for i in $(seq 1 30); do
            if pg_isready -h localhost -p 5432 -U postgres; then
              echo "Postgres is ready"
              break
            fi
            echo "Attempt $i: Postgres not ready yet"
            sleep 2
          done

      - name: Test database connection
        run: |
          PGPASSWORD=test psql -h localhost -p 5432 -U postgres -d testdb -c "SELECT 1;"
```

### Debug de Redis

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

steps:
  - name: Debug Redis
    run: |
      echo "Testing Redis connection..."
      redis-cli -h localhost -p 6379 ping
      redis-cli -h localhost -p 6379 info server | head -20
```

### Debug de MySQL

```yaml
services:
  mysql:
    image: mysql:8.0
    env:
      MYSQL_ROOT_PASSWORD: test
      MYSQL_DATABASE: testdb
    ports:
      - 3306:3306
    options: >-
      --health-cmd="mysqladmin ping -h localhost"
      --health-interval=10s
      --health-timeout=5s
      --health-retries=5

steps:
  - name: Debug MySQL
    run: |
      echo "Testing MySQL connection..."
      mysql -h localhost -P 3306 -u root -ptest -e "SELECT 1;"
      mysql -h localhost -P 3306 -u root -ptest -e "SHOW DATABASES;"
```

### Debug de MongoDB

```yaml
services:
  mongodb:
    image: mongo:7
    ports:
      - 27017:27017
    options: >-
      --health-cmd="mongosh --eval 'db.runCommand(\"ping\").ok'"
      --health-interval=10s
      --health-timeout=5s
      --health-retries=5

steps:
  - name: Debug MongoDB
    run: |
      echo "Testing MongoDB connection..."
      mongosh --host localhost --port 27017 --eval "db.runCommand('ping')"
```

### Debug de Docker Compose

```yaml
steps:
  - name: Debug Docker Compose
    run: |
      echo "::group::Docker Compose Status"
      docker compose ps
      docker compose logs
      echo "::endgroup::"

      echo "::group::Docker Containers"
      docker ps -a
      echo "::endgroup::"

      echo "::group::Docker Networks"
      docker network ls
      docker network inspect bridge
      echo "::endgroup::"
```

### Debug de Docker Build

```yaml
steps:
  - name: Build Docker image with debug
    run: |
      docker build \
        --progress=plain \
        --no-cache \
        -t myapp:test \
        . 2>&1 | tee docker-build.log

  - name: Upload build logs on failure
    if: failure()
    uses: actions/upload-artifact@v4
    with:
      name: docker-build-logs
      path: docker-build.log
```

---

## 15.15 Debug de Matrix Builds

### Identificar Falha em Matrix

```yaml
name: Matrix Debug

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
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js ${{ matrix.node }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: System info
        run: |
          echo "OS: ${{ matrix.os }}"
          echo "Node: $(node --version)"
          echo "NPM: $(npm --version)"
          echo "Architecture: $(uname -m)"

      - name: Install and test
        run: |
          npm ci
          npm test
```

### Matrix com Debug Detalhado

```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        node: [18, 20]
        include:
          - os: ubuntu-latest
            node: 20
            experimental: true
      fail-fast: false
    continue-on-error: ${{ matrix.experimental || false }}
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}

      - name: Matrix debug info
        run: |
          echo "## Matrix Configuration" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "- OS: \`${{ matrix.os }}\`" >> "$GITHUB_STEP_SUMMARY"
          echo "- Node: \`${{ matrix.node }}\`" >> "$GITHUB_STEP_SUMMARY"
          echo "- Experimental: \`${{ matrix.experimental || false }}\`" >> "$GITHUB_STEP_SUMMARY"
          echo "- Runner: \`${{ runner.os }}\` / \`${{ runner.arch }}\`" >> "$GITHUB_STEP_SUMMARY"
```

---

## 15.16 Debug de Reusable Workflows

### Debug de Caller Workflow

```yaml
# .github/workflows/caller.yml
name: Caller Debug

on:
  push:
    branches: [main]

jobs:
  call-reusable:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '20'
      test-command: 'npm test -- --verbose'
    secrets: inherit
    # Debug: log inputs e secrets
```

### Debug no Reusable Workflow

```yaml
# .github/workflows/reusable-test.yml
name: Reusable Test

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
    secrets:
      DATABASE_URL:
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Debug inputs
        run: |
          echo "::group::Workflow Inputs"
          echo "node-version: ${{ inputs.node-version }}"
          echo "test-command: ${{ inputs.test-command }}"
          echo "::endgroup::"

      - name: Debug secrets
        run: |
          echo "::group::Secrets Status"
          echo "DATABASE_URL definido: ${{ secrets.DATABASE_URL != '' }}"
          echo "::endgroup::"

      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
          cache: 'npm'

      - run: npm ci
      - run: ${{ inputs.test-command }}
```

---

## 15.17 Debug de Artifacts

### Diagnosticar Artifacts

```yaml
steps:
  - name: Create test artifact
    run: |
      mkdir -p dist
      echo "test content" > dist/test.txt
      ls -la dist/

  - name: Upload artifact
    id: upload
    uses: actions/upload-artifact@v4
    with:
      name: test-artifact
      path: dist/
      retention-days: 1

  - name: Debug artifact
    run: |
      echo "Artifact name: test-artifact"
      echo "Artifact path: dist/"
      ls -la dist/
```

### Debug de Artifact Download

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "build output" > dist.txt
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist.txt

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: downloaded/

      - name: Verify download
        run: |
          echo "::group::Downloaded Artifacts"
          find downloaded/ -type f
          cat downloaded/dist.txt
          echo "::endgroup::"
```

---

## 15.18 Debug de Caches

### Diagnosticar Cache

```yaml
steps:
  - name: Cache debug
    id: cache
    uses: actions/cache@v4
    with:
      path: node_modules
      key: ${{ runner.os }}-modules-${{ hashFiles('**/package-lock.json') }}
      restore-keys: |
        ${{ runner.os }}-modules-

  - name: Cache info
    run: |
      echo "::group::Cache Status"
      echo "Cache hit: ${{ steps.cache.outputs.cache-hit }}"
      echo "Cache key: ${{ runner.os }}-modules-${{ hashFiles('**/package-lock.json') }}"
      echo "Node modules exists: $([ -d node_modules ] && echo yes || echo no)"
      echo "Node modules size: $(du -sh node_modules 2>/dev/null || echo 'N/A')"
      echo "::endgroup::"
```

### Cache com Debug Verboso

```yaml
steps:
  - name: Restore cache
    id: cache
    uses: actions/cache@v4
    with:
      path: |
        node_modules
        ~/.npm
      key: ${{ runner.os }}-npm-${{ hashFiles('**/package-lock.json') }}
      restore-keys: |
        ${{ runner.os }}-npm-

  - name: Debug cache restore
    run: |
      echo "::group::Cache Debug"
      if [ "${{ steps.cache.outputs.cache-hit }}" == "true" ]; then
        echo "Cache HIT - using cached dependencies"
        echo "Cached node_modules:"
        ls node_modules/ | head -20
      else
        echo "Cache MISS - will install fresh"
      fi
      echo "NPM cache size: $(du -sh ~/.npm 2>/dev/null || echo 'N/A')"
      echo "::endgroup::"
```

---

## 15.19 Debug de Deployments

### Debug de Deploy

```yaml
name: Deploy Debug

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Deploy debug
        run: |
          echo "::group::Deployment Information"
          echo "Environment: production"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Actor: ${{ github.actor }}"
          echo "Event: ${{ github.event_name }}"
          echo "::endgroup::"

      - name: Pre-deploy check
        run: |
          echo "Checking deployment prerequisites..."
          echo "1. Code is on main branch: $([[ ${{ github.ref }} == 'refs/heads/main' ]] && echo yes || echo no)"
          echo "2. All tests passed: (check previous jobs)"
          echo "3. Secrets are configured: ${{ secrets.DEPLOY_TOKEN != '' }}"
```

### Debug de Environment Protection

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Environment info
        run: |
          echo "::group::Environment Protection"
          echo "Environment: production"
          echo "URL: https://example.com"
          echo "Protection rules: (configured in GitHub Settings)"
          echo "::endgroup::"
```

---

## 15.20 Debug de OIDC

### Debug de OIDC Token

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Debug OIDC
        run: |
          echo "::group::OIDC Token"
          echo "Requesting OIDC token..."
          OIDC_TOKEN=$(curl -s -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://api.example.com" | jq -r '.value')
          echo "Token length: ${#OIDC_TOKEN}"
          echo "Token audience: https://api.example.com"
          echo "::endgroup::"

      - name: Configure AWS with OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions
          aws-region: us-east-1
```

---

## 15.21 Debug de Composite Actions

### Debug de Composite Action

```yaml
# .github/actions/setup/action.yml
name: Setup
description: Debug composite action

inputs:
  node-version:
    required: false
    default: '20'

runs:
  using: composite
  steps:
    - name: Debug inputs
      shell: bash
      run: |
        echo "::group::Composite Action Inputs"
        echo "node-version: ${{ inputs.node-version }}"
        echo "::endgroup::"

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ inputs.node-version }}
        cache: 'npm'
      shell: bash

    - name: Debug setup result
      shell: bash
      run: |
        echo "::group::Setup Result"
        echo "Node: $(node --version)"
        echo "NPM: $(npm --version)"
        echo "::endgroup::"
```

---

## 15.22 Debug de Workflow Dispatch

### Debug de Inputs

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
      skip_tests:
        description: 'Skip tests'
        required: false
        type: boolean
        default: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Debug inputs
        run: |
          echo "::group::Workflow Dispatch Inputs"
          echo "environment: ${{ inputs.environment }}"
          echo "skip_tests: ${{ inputs.skip_tests }}"
          echo "::endgroup::"

      - name: Validate inputs
        run: |
          if [ -z "${{ inputs.environment }}" ]; then
            echo "::error::Environment is required"
            exit 1
          fi

          if [[ ! "${{ inputs.environment }}" =~ ^(staging|production)$ ]]; then
            echo "::error::Invalid environment: ${{ inputs.environment }}"
            exit 1
          fi
```

### Debug de Evento

```yaml
steps:
  - name: Debug event
    run: |
      echo "::group::Event Payload"
      echo "Event name: ${{ github.event_name }}"
      echo "Action: ${{ github.event.action }}"
      echo "Sender: ${{ github.event.sender.login }}"
      echo "::endgroup::"
```

---

## 15.23 Debug de Repository Variables

### Debug de vars Context

```yaml
steps:
  - name: Debug repository variables
    run: |
      echo "::group::Repository Variables"
      echo "APP_NAME: ${{ vars.APP_NAME }}"
      echo "NODE_VERSION: ${{ vars.NODE_VERSION }}"
      echo "DEPLOY_TARGET: ${{ vars.DPLOY_TARGET }}"
      echo "::endgroup::"
```

### Debug de Environment Variables

```yaml
steps:
  - name: Debug environment variables
    run: |
      echo "::group::Environment Variables"
      echo "MY_VAR: ${{ vars.MY_VAR }}"
      echo "APP_URL: ${{ vars.APP_URL }}"
      echo "::endgroup::"
```

---

## 15.24 Debug de Job Dependencies

### Debug de Needs

```yaml
jobs:
  job-a:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.step1.outputs.value }}
    steps:
      - id: step1
        run: echo "value=success" >> "$GITHUB_OUTPUT"

  job-b:
    needs: job-a
    runs-on: ubuntu-latest
    steps:
      - name: Debug dependency
        run: |
          echo "Job A result: ${{ needs.job-a.result }}"
          echo "Job A output: ${{ needs.job-a.outputs.result }}"

  job-c:
    needs: [job-a, job-b]
    runs-on: ubuntu-latest
    steps:
      - name: Debug all dependencies
        run: |
          echo "Job A: ${{ needs.job-a.result }}"
          echo "Job B: ${{ needs.job-b.result }}"
          echo "Job A output: ${{ needs.job-a.outputs.result }}"
```

### Debug de Conditional Jobs

```yaml
jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      should-deploy: ${{ steps.check.outputs.deploy }}
    steps:
      - id: check
        run: echo "deploy=true" >> "$GITHUB_OUTPUT"

  deploy:
    needs: detect
    if: needs.detect.outputs.should-deploy == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Debug condition
        run: |
          echo "Should deploy: ${{ needs.detect.outputs.should-deploy }}"
          echo "Condition result: true"
```

---

## 15.25 Debug de Workflow Run Previous

### Usando workflow_run para Debug

```yaml
name: Debug Previous Run

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  debug-previous:
    runs-on: ubuntu-latest
    steps:
      - name: Debug previous run
        run: |
          echo "::group::Previous Run Information"
          echo "Workflow: ${{ github.event.workflow_run.name }}"
          echo "Conclusion: ${{ github.event.workflow_run.conclusion }}"
          echo "Run ID: ${{ github.event.workflow_run.id }}"
          echo "Run number: ${{ github.event.workflow_run.run_number }}"
          echo "Head branch: ${{ github.event.workflow_run.head_branch }}"
          echo "Head SHA: ${{ github.event.workflow_run.head_sha }}"
          echo "::endgroup::"
```

---

## 15.26 Debug de Secrets Encryption

### Verificar Secrets

```yaml
steps:
  - name: Verify secrets
    run: |
      echo "::group::Secrets Verification"
      echo "SECRET_A is set: ${{ secrets.SECRET_A != '' }}"
      echo "SECRET_B is set: ${{ secrets.SECRET_B != '' }}"
      echo "SECRET_C is set: ${{ secrets.SECRET_C != '' }}"
      echo "SECRET_D is set: ${{ secrets.SECRET_D != '' }}"
      echo ""

      # Verificar se todos os secrets necessarios estao definidos
      REQUIRED_SECRETS=("SECRET_A" "SECRET_B")
      for SECRET in "${REQUIRED_SECRETS[@]}"; do
        if [ -z "${!SECRET}" ]; then
          echo "::warning::Required secret $SECRET is not set"
        else
          echo "OK: $SECRET is configured"
        fi
      done
      echo "::endgroup::"
```

---

## 15.27 Debug de Self-Hosted Runners

### Debug de Runner Status

```yaml
jobs:
  debug-runner:
    runs-on: self-hosted
    steps:
      - name: Runner info
        run: |
          echo "::group::Runner Information"
          echo "Name: ${{ runner.name }}"
          echo "OS: ${{ runner.os }}"
          echo "Arch: ${{ runner.arch }}"
          echo "Temp: ${{ runner.temp }}"
          echo "Tool cache: ${{ runner.tool_cache }}"
          echo "Debug: ${{ runner.debug }}"
          echo ""

          echo "System:"
          uname -a
          echo ""

          echo "Disk:"
          df -h /
          echo ""

          echo "Memory:"
          free -h
          echo ""

          echo "CPU:"
          nproc
          echo ""

          echo "Docker:"
          docker --version 2>/dev/null || echo "Docker not available"
          echo "::endgroup::"
```

### Debug de Runner Labels

```yaml
jobs:
  debug-labels:
    runs-on: [self-hosted, linux, x64, gpu]
    steps:
      - name: Show runner labels
        run: |
          echo "Runner labels:"
          echo "  - self-hosted"
          echo "  - linux"
          echo "  - x64"
          echo "  - gpu"
```

---

## 15.28 Debug de Actions Kit

### Usando @actions/core para Debug

```typescript
import * as core from '@actions/core';

// Debug logging (so aparece com ACTIONS_STEP_DEBUG=true)
core.debug('This is debug output');

// Info
core.info('This is info output');

// Warning
core.warning('This is a warning');

// Error
core.error('This is an error');

// Set output
core.setOutput('myOutput', 'value');

// Set failed
core.setFailed('Action failed');

// Group
core.startGroup('My group');
console.log('Grouped output');
core.endGroup();

// Export variable
core.exportVariable('MY_VAR', 'value');

// Add path
core.addPath('/usr/local/bin');

// Set secret (mask)
core.setSecret('my-secret-value');
```

### Debug de Inputs e Outputs

```typescript
// Ler inputs
const nodeVersion = core.getInput('node-version', { required: true });
const environment = core.getInput('environment', { required: false });

// Debug inputs
core.debug(`Node version: ${nodeVersion}`);
core.debug(`Environment: ${environment}`);

// Definir outputs
core.setOutput('build-result', 'success');
core.setOutput('deploy-url', 'https://example.com');

// Group outputs
core.startGroup('Outputs');
console.log(`build-result: success`);
console.log(`deploy-url: https://example.com`);
core.endGroup();
```

---

## 15.29 Debug de Security

### Debug de Supply Chain

```yaml
steps:
  - name: Verify action integrity
    run: |
      echo "::group::Action Verification"
      echo "Checking pinned actions..."
      echo ""
      echo "Expected SHAs:"
      echo "  actions/checkout: b4ffde65f46336ab88eb53be808477a3936bae11"
      echo "  actions/setup-node: 60edb5dd545a775178f525247833660a0683627d"
      echo ""

      # Verificar se actions estao pinadas
      grep -r "uses:" .github/workflows/ | while IFS= read -r line; do
        if echo "$line" | grep -qE "@v[0-9]+"; then
          echo "WARNING: $line (uses tag, not SHA)"
        elif echo "$line" | grep -qE "@[a-f0-9]{40}"; then
          echo "OK: $line (pinned by SHA)"
        fi
      done
      echo "::endgroup::"
```

### Debug de Permissions

```yaml
steps:
  - name: Check token permissions
    run: |
      echo "::group::Token Permissions"
      curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
        "https://api.github.com/repos/${{ github.repository }}/permissions" | \
        jq '.'
      echo "::endgroup::"
```

---

## 15.30 Checklist de Debug Final

### Script de Debug Completo

```yaml
name: Complete Debug

on:
  workflow_dispatch:
    inputs:
      debug_level:
        description: 'Debug level'
        required: false
        default: 'verbose'
        type: choice
        options:
          - minimal
          - verbose
          - comprehensive

jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: System info
        run: |
          echo "::group::System"
          echo "OS: $(uname -a)"
          echo "Hostname: $(hostname)"
          echo "User: $(whoami)"
          echo "PWD: $(pwd)"
          echo "::endgroup::"

      - name: Git info
        run: |
          echo "::group::Git"
          echo "Version: $(git --version)"
          echo "Branch: $(git branch --show-current)"
          echo "SHA: $(git rev-parse HEAD)"
          echo "Remote: $(git remote -v)"
          echo "::endgroup::"

      - name: Runtime info
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Node info
        run: |
          echo "::group::Node.js"
          echo "Node: $(node --version)"
          echo "NPM: $(npm --version)"
          echo "Yarn: $(yarn --version 2>/dev/null || echo 'not installed')"
          echo "PNPM: $(pnpm --version 2>/dev/null || echo 'not installed')"
          echo "::endgroup::"

      - name: GitHub context
        run: |
          echo "::group::GitHub"
          echo "Event: ${{ github.event_name }}"
          echo "Ref: ${{ github.ref }}"
          echo "SHA: ${{ github.sha }}"
          echo "Repository: ${{ github.repository }}"
          echo "Actor: ${{ github.actor }}"
          echo "Workflow: ${{ github.workflow }}"
          echo "Run ID: ${{ github.run_id }}"
          echo "Run number: ${{ github.run_number }}"
          echo "Action: ${{ github.action }}"
          echo "Server URL: ${{ github.server_url }}"
          echo "API URL: ${{ github.api_url }}"
          echo "::endgroup::"

      - name: Secrets status
        if: inputs.debug_level != 'minimal'
        run: |
          echo "::group::Secrets"
          echo "GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN != '' }}"
          echo "DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN != '' }}"
          echo "NPM_TOKEN: ${{ secrets.NPM_TOKEN != '' }}"
          echo "::endgroup::"

      - name: Cache status
        id: cache
        uses: actions/cache@v4
        with:
          path: node_modules
          key: debug-${{ hashFiles('**/package-lock.json') }}

      - name: Cache debug
        if: inputs.debug_level != 'minimal'
        run: |
          echo "::group::Cache"
          echo "Hit: ${{ steps.cache.outputs.cache-hit }}"
          echo "Key: debug-${{ hashFiles('**/package-lock.json') }}"
          echo "::endgroup::"

      - name: Dependencies debug
        if: inputs.debug_level == 'comprehensive'
        run: |
          echo "::group::Dependencies"
          npm ls --depth=0 2>/dev/null || true
          echo "::endgroup::"

      - name: Build test
        run: |
          echo "::group::Build"
          npm ci 2>&1 | tail -20
          echo "::endgroup::"

      - name: Summary
        run: |
          echo "## Debug Summary" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Item | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| OS | ${{ runner.os }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Node | $(node --version) |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Event | ${{ github.event_name }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Ref | ${{ github.ref_name }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Cache | ${{ steps.cache.outputs.cache-hit }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Debug Level | ${{ inputs.debug_level }} |" >> "$GITHUB_STEP_SUMMARY"
```

---

## 15.31 Referencias

1. https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows
2. https://docs.github.com/en/actions/learn-github-actions/variables
3. https://github.com/nektos/act
4. https://github.com/rhysd/actionlint
5. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
6. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
7. https://github.com/actions/toolkit/tree/main/packages/core
8. https://docs.github.com/en/actions/learn-github-actions/expressions
9. https://github.com/sdras/awesome-actions
10. https://docs.github.com/en/actions/hosting-your-own-runners
11. https://github.com/nektos/act/blob/master/docs/README.md
12. https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
