---
layout: default
title: "16-monitoramento"
---

# Capitulo 16 -- Monitoramento e Metricas

> *"O que nao e medido, nao e melhorado."*

---

## Objetivos de Aprendizado

1. Consultar a Workflow Runs API do GitHub
2. Construir dashboards com metricas de CI/CD
3. Monitorar billing e uso de minutos
4. Otimizar custos com estrategias eficientes
5. Coletar metricas de self-hosted runners
6. Configurar notificacoes via Slack e Discord
7. Implementar status badges
8. Criar alertas de falha
9. Definir SLAs de CI/CD
10. Montar um dashboard de monitoramento completo
11. Automatizar relatorios de custos
12. Monitorar performance de builds
13. Rastrear taxa de sucesso de deploys
14. Configurar alertas de regressao
15. Implementar observabilidade end-to-end

---

## 16.1 Workflow Runs API

### Listar Runs

```bash
# Listar runs do repositorio
curl -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs" | \
  jq '.workflow_runs[] | {id, name, status, conclusion, created_at}'
```

### Filtrar por Status

```bash
# Runs concluidos com sucesso
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs?status=success" | \
  jq '.total_count'

# Runs que falharam
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs?status=failure" | \
  jq '.workflow_runs[] | {id, name, created_at, conclusion}'

# Runs em andamento
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs?status=in_progress"
```

### Filtrar por Workflow

```bash
# Runs de um workflow especifico
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/workflows/WORKFLOW_ID/runs" | \
  jq '.workflow_runs[] | {id, head_branch, status, conclusion}'
```

### Detalhes de um Run

```bash
# Detalhes do run
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID" | \
  jq '{
    id: .id,
    name: .name,
    status: .status,
    conclusion: .conclusion,
    created_at: .created_at,
    updated_at: .updated_at,
    run_started_at: .run_started_at,
    event: .event,
    head_branch: .head_branch,
    head_sha: .head_sha,
    run_number: .run_number,
    actors: .actor.login
  }'
```

### Jobs de um Run

```bash
# Listar jobs de um run
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/jobs" | \
  jq '.jobs[] | {
    id: .id,
    name: .name,
    status: .status,
    conclusion: .conclusion,
    started_at: .started_at,
    completed_at: .completed_at,
    steps: [.steps[] | {name, status, conclusion}]
  }'
```

### Artefatos de um Run

```bash
# Listar artefatos
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/artifacts" | \
  jq '.artifacts[] | {id, name, size_in_bytes, created_at, expired}'
```

### Download de Log

```bash
# Baixar log de um run
curl -L -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/logs" \
  -o run-logs.zip

unzip run-logs.zip
```

### Paginacao

```bash
# Listar todas as runs com paginacao
page=1
while true; do
  response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
    "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=100&page=$page")

  count=$(echo "$response" | jq '.workflow_runs | length')
  if [ "$count" -eq 0 ]; then
    break
  fi

  echo "$response" | jq '.workflow_runs[] | {id, name, conclusion}'
  page=$((page + 1))
done
```

### Workflow Runs com gh CLI

```bash
# Listar runs recentes
gh run list --limit 10

# Listar runs com detalhes
gh run list --limit 10 --json databaseId,name,status,conclusion,createdAt,event

# Filtrar por branch
gh run list --branch main --limit 10

# Filtrar por workflow
gh run list --workflow=ci.yml --limit 10

# Ver detalhes de um run
gh run view RUN_ID

# Ver jobs de um run
gh run view RUN_ID --jobs

# Baixar logs
gh run view RUN_ID --log
```

### Script de Coleta de Metricas

```bash
#!/bin/bash
# collect-metrics.sh

OWNER="myorg"
REPO="myrepo"
TOKEN=$GITHUB_TOKEN
DAYS=30

echo "Collecting metrics for the last $DAYS days..."

# Calcular data de inicio
START_DATE=$(date -d "-${DAYS} days" +%Y-%m-%dT%H:%M:%SZ)

# Listar todos os workflows
WORKFLOWS=$(curl -s -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/actions/workflows" | \
  jq -r '.workflows[] | "\(.id) \(.name)"')

while IFS=' ' read -r wf_id wf_name; do
  echo ""
  echo "Workflow: $wf_name (ID: $wf_id)"

  # Pegar runs deste workflow
  RUNS=$(curl -s -H "Authorization: token $TOKEN" \
    "https://api.github.com/repos/$OWNER/$REPO/actions/workflows/$wf_id/runs?created=>=$START_DATE&per_page=100")

  TOTAL=$(echo "$RUNS" | jq '.total_count')
  SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
  FAILURE=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')
  CANCELLED=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "cancelled")] | length')

  if [ "$TOTAL" -gt 0 ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
  else
    SUCCESS_RATE="0"
  fi

  echo "  Total runs: $TOTAL"
  echo "  Success: $SUCCESS ($SUCCESS_RATE%)"
  echo "  Failure: $FAILURE"
  echo "  Cancelled: $CANCELLED"
done <<< "$WORKFLOWS"
```

---

## 16.2 Dashboard Metrics

### Metricas Principais

| Metrica | Descricao | Fonte |
|---------|-----------|-------|
| Total de runs | Quantidade total de executacoes | Workflow Runs API |
| Taxa de sucesso | % de runs que completaram com sucesso | Workflow Runs API |
| Tempo medio de build | Media de duracao dos runs | Workflow Runs API |
| Custo estimado | Minutos consumidos x custo por minuto | Billing API |
| Falhas por workflow | Distribuicao de falhas | Workflow Runs API |
| Runs por branch | Volume de execucoes por branch | Workflow Runs API |
| Tempo medio de fila | Tempo entre trigger e inicio | Workflow Runs API |
| Taxa de cancelamento | % de runs cancelados | Workflow Runs API |

### Dashboard com GitHub Actions

```yaml
name: CI/CD Dashboard

on:
  schedule:
    - cron: '0 8 * * 1'  # Toda segunda-feira as 8h

jobs:
  dashboard:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Generate dashboard
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          REPO="${{ github.repository }}"
          API="https://api.github.com/repos/$REPO/actions"

          # Metricas da ultima semana
          WEEK_AGO=$(date -d "-7 days" +%Y-%m-%dT%H:%M:%SZ)

          echo "## CI/CD Dashboard - $(date +%Y-%m-%d)" > dashboard.md
          echo "" >> dashboard.md

          # Runs da ultima semana
          RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "$API/runs?created=>$WEEK_AGO&per_page=100")

          TOTAL=$(echo "$RUNS" | jq '.total_count')
          SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
          FAILURE=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')

          echo "### Resumo da Semana" >> dashboard.md
          echo "" >> dashboard.md
          echo "| Metrica | Valor |" >> dashboard.md
          echo "|---------|-------|" >> dashboard.md
          echo "| Total de runs | $TOTAL |" >> dashboard.md
          echo "| Sucesso | $SUCCESS |" >> dashboard.md
          echo "| Falhas | $FAILURE |" >> dashboard.md

          if [ "$TOTAL" -gt 0 ]; then
            RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
            echo "| Taxa de sucesso | ${RATE}% |" >> dashboard.md
          fi

          # Workflows mais problematicos
          echo "" >> dashboard.md
          echo "### Workflows com Mais Falhas" >> dashboard.md
          echo "" >> dashboard.md

          echo "$RUNS" | jq -r '.workflow_runs[] | select(.conclusion == "failure") | .name' | \
            sort | uniq -c | sort -rn | head -5 | \
            while read count name; do
              echo "- $name: $count falhas" >> dashboard.md
            done

          cat dashboard.md
```

### Dashboard com Metricas Detalhadas

```yaml
name: Detailed Metrics

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  collect-metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate build time
        run: |
          START="${{ github.event.workflow_run.run_started_at }}"
          END="${{ github.event.workflow_run.updated_at }}"

          START_EPOCH=$(date -d "$START" +%s)
          END_EPOCH=$(date -d "$END" +%s)
          DURATION=$((END_EPOCH - START_EPOCH))

          echo "Build duration: ${DURATION}s"
          echo "Build duration minutes: $((DURATION / 60))"

      - name: Record metrics
        run: |
          echo "## Metrics" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Workflow | ${{ github.event.workflow_run.name }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Conclusion | ${{ github.event.workflow_run.conclusion }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Branch | ${{ github.event.workflow_run.head_branch }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Actor | ${{ github.event.workflow_run.actor.login }} |" >> "$GITHUB_STEP_SUMMARY"
```

### Metricas com InfluxDB

```yaml
name: Metrics to InfluxDB

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  push-metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Push to InfluxDB
        run: |
          START="${{ github.event.workflow_run.run_started_at }}"
          END="${{ github.event.workflow_run.updated_at }}"
          START_EPOCH=$(date -d "$START" +%s)
          END_EPOCH=$(date -d "$END" +%s)
          DURATION=$((END_EPOCH - START_EPOCH))

          # InfluxDB line protocol
          METRIC="github_actions,workflow=${{ github.event.workflow_run.name }},branch=${{ github.event.workflow_run.head_branch }} duration=${DURATION},conclusion=\"${{ github.event.workflow_run.conclusion }}\" $(date +%s)000000000"

          curl -s -X POST \
            "$INFLUXDB_URL/api/v2/write?org=myorg&bucket=metrics&precision=ns" \
            -H "Authorization: Token $INFLUXDB_TOKEN" \
            -H "Content-Type: text/plain" \
            -d "$METRIC"
```

---

## 16.3 Billing

### Verificar Uso de GitHub Actions

```bash
# Verificar billing da organizacao
curl -H "Authorization: token $ORG_TOKEN" \
  "https://api.github.com/orgs/ORGNAME/settings/billing/actions" | \
  jq '{
    total_minutes_used: .total_minutes_used,
    total_paid_minutes_used: .total_paid_minutes_used,
    included_minutes: .included_minutes,
    minutes_used_breakdown: .minutes_used_breakdown
  }'
```

### Verificar Uso por Repositorio

```bash
# Uso por repositorio
curl -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/actions/workflows" | \
  jq '.total_count'
```

### Relatorio de Uso Mensal

```yaml
name: Monthly Billing Report

on:
  schedule:
    - cron: '0 9 1 * *'  # Primeiro dia do mes as 9h

jobs:
  billing-report:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Generate billing report
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ORG_TOKEN: ${{ secrets.ORG_TOKEN }}
        run: |
          MONTH=$(date -d "last month" +%Y-%m)
          START=$(date -d "last month" +%Y-%m-01)
          END=$(date -d "this month" +%Y-%m-01)

          echo "## Relatorio de Billing - $MONTH" > billing-report.md
          echo "" >> billing-report.md

          # Uso da organizacao
          BILLING=$(curl -s -H "Authorization: token $ORG_TOKEN" \
            "https://api.github.com/orgs/${{ github.repository_owner }}/settings/billing/actions")

          TOTAL_MINUTES=$(echo "$BILLING" | jq '.total_minutes_used')
          INCLUDED=$(echo "$BILLING" | jq '.included_minutes')
          PAID_MINUTES=$(echo "$BILLING" | jq '.total_paid_minutes_used')

          echo "### Uso Total" >> billing-report.md
          echo "" >> billing-report.md
          echo "| Metrica | Valor |" >> billing-report.md
          echo "|---------|-------|" >> billing-report.md
          echo "| Minutos usados | $TOTAL_MINUTES |" >> billing-report.md
          echo "| Minutos incluidos | $INCLUDED |" >> billing-report.md
          echo "| Minutos pagos | $PAID_MINUTES |" >> billing-report.md

          # Breakdown por OS
          echo "" >> billing-report.md
          echo "### Breakdown por OS" >> billing-report.md
          echo "" >> billing-report.md
          echo "$BILLING" | jq '.minutes_used_breakdown' | \
            jq -r 'to_entries[] | "| \(.key) | \(.value) minutos |"' >> billing-report.md

          cat billing-report.md

      - name: Create issue with report
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('billing-report.md', 'utf8');
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Billing Report - ${new Date().toISOString().slice(0, 7)}`,
              body: report,
              labels: ['billing', 'report']
            });
```

### Tabela de Custos por Runner

| Runner | Free Tier | Pro ($4/mes) | Team ($4/mes) | Enterprise ($21/mes) |
|--------|-----------|--------------|---------------|---------------------|
| Linux | 2.000 min/mes | $0.008/min | $0.008/min | $0.008/min |
| macOS | 2.000 min/mes | $0.08/min | $0.08/min | $0.08/min |
| Windows | 2.000 min/mes | $0.016/min | $0.016/min | $0.016/min |

### Calculo de Custo Estimado

```yaml
name: Cost Estimate

on:
  workflow_run:
    workflows: ["CI", "CD"]
    types: [completed]

jobs:
  estimate-cost:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate cost
        run: |
          RUNNER_OS="${{ github.event.workflow_run.runners[0].os }}"
          START="${{ github.event.workflow_run.run_started_at }}"
          END="${{ github.event.workflow_run.updated_at }}"

          START_EPOCH=$(date -d "$START" +%s)
          END_EPOCH=$(date -d "$END" +%s)
          DURATION_MIN=$(( (END_EPOCH - START_EPOCH) / 60 ))

          case "$RUNNER_OS" in
            Linux)   RATE=0.008 ;;
            macOS)   RATE=0.08 ;;
            Windows) RATE=0.016 ;;
            *)       RATE=0.008 ;;
          esac

          COST=$(echo "scale=4; $DURATION_MIN * $RATE" | bc)

          echo "Runner: $RUNNER_OS"
          echo "Duration: $DURATION_MIN minutes"
          echo "Rate: \$$RATE/min"
          echo "Estimated cost: \$$COST"
```

---

## 16.4 Cost Optimization

### Estrategias de Reducao de Custo

| Estrategia | Reducao | Complexidade |
|------------|---------|--------------|
| Cache de dependencias | -50% tempo | Baixa |
| Concurrency groups | -30% duplicatas | Baixa |
| Path filters | -40% builds | Baixa |
| Self-hosted runners | -80% custo | Alta |
| Fail-fast: false | +10% (evita reruns) | Baixa |
| Matrix optimization | -30% execucoes | Media |
| Job splitting | -20% tempo medio | Media |
| Artifact optimization | -15% transfer | Baixa |

### Cache Otimizado

```yaml
name: Cost Optimized CI

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
          cache: 'npm'

      # Cache granular por tipo
      - name: Cache TypeScript build
        uses: actions/cache@v4
        with:
          path: |
            packages/*/dist
            packages/*/.tsbuildinfo
          key: tsbuild-${{ runner.os }}-${{ hashFiles('**/tsconfig.json') }}-${{ github.sha }}
          restore-keys: |
            tsbuild-${{ runner.os }}-${{ hashFiles('**/tsconfig.json') }}-
            tsbuild-${{ runner.os }}-

      - run: npm ci
      - run: npm run build
      - run: npm test
```

### Concurrency Groups

```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Path Filters

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'package.json'
      - 'tsconfig.json'
    paths-ignore:
      - 'docs/**'
      - '**.md'
      - '.github/ISSUE_TEMPLATE/**'
```

### Matrix com Fail-Fast

```yaml
strategy:
  fail-fast: true  # Cancela outros jobs se um falhar
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
```

### Self-Hosted Runners

```yaml
jobs:
  build:
    runs-on: [self-hosted, linux]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test
```

### Job Splitting Inteligente

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run lint

  test:
    needs: lint  # So roda se lint passar
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
```

### Otimizacao de Artifacts

```yaml
steps:
  # Nao fazer upload de artifacts desnecessarios
  - uses: actions/upload-artifact@v4
    with:
      name: build-output
      path: dist/
      retention-days: 1  # Manter por apenas 1 dia
      compression-level: 6  # Comprimir
```

### Monitoramento de Custo em Tempo Real

```yaml
name: Cost Monitor

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Track cost
        run: |
          RUN_START="${{ github.event.workflow_run.run_started_at }}"
          RUN_END="${{ github.event.workflow_run.updated_at }}"
          RUN_ID="${{ github.event.workflow_run.id }}"

          START_EPOCH=$(date -d "$RUN_START" +%s)
          END_EPOCH=$(date -d "$RUN_END" +%s)
          DURATION=$(( (END_EPOCH - START_EPOCH) / 60 ))

          # Estimar custo (Linux rate)
          COST=$(echo "scale=4; $DURATION * 0.008" | bc)

          echo "Run: $RUN_ID"
          echo "Duration: $DURATION minutes"
          echo "Estimated cost: \$$COST"
```

---

## 16.5 Self-Hosted Metrics

### Metricas de Self-Hosted Runners

```yaml
name: Self-Hosted Runner Metrics

on:
  schedule:
    - cron: '*/5 * * * *'  # A cada 5 minutos

jobs:
  collect-metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Get runner metrics
        run: |
          curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runners" | \
            jq '. runners[] | {
              name: .name,
              status: .status,
              os: .os,
              labels: [.labels[].name]
            }'
```

### Monitoramento de Saude do Runner

```yaml
name: Runner Health Check

on:
  schedule:
    - cron: '*/10 * * * *'

jobs:
  health:
    runs-on: self-hosted
    steps:
      - name: Health check
        run: |
          echo "Disk space:"
          df -h /

          echo "Memory:"
          free -h

          echo "CPU load:"
          uptime

          echo "Docker:"
          docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

          echo "Runner processes:"
          ps aux | grep -E "(Runner|actions)" | grep -v grep
```

### Metricas de Performance do Runner

```yaml
name: Runner Performance

on:
  workflow_run:
    types: [completed]

jobs:
  perf:
    runs-on: self-hosted
    steps:
      - name: Performance metrics
        run: |
          echo "## Runner Performance" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| CPU cores | $(nproc) |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Total memory | $(free -h | awk '/^Mem:/{print $2}') |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Available memory | $(free -h | awk '/^Mem:/{print $7}') |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Disk free | $(df -h / | awk 'NR==2{print $4}') |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Load average | $(uptime | awk -F'load average:' '{print $2}') |" >> "$GITHUB_STEP_SUMMARY"
```

### Auto-Scaling de Runners

```yaml
name: Auto-Scale Runners

on:
  workflow_run:
    types: [requested]

jobs:
  check-load:
    runs-on: ubuntu-latest
    steps:
      - name: Check runner pool
        run: |
          RUNNERS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runners" | \
            jq '.total_count')

          QUEUED=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=queued" | \
            jq '.total_count')

          echo "Active runners: $RUNNERS"
          echo "Queued workflows: $QUEUED"

          if [ "$QUEUED" -gt "$RUNNERS" ]; then
            echo "Need more runners!"
            # Trigger scaling action
          fi
```

---

## 16.6 Notifications

### Slack com Webhook

```yaml
name: Slack Notification

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {
              "blocks": [
                {
                  "type": "header",
                  "text": {
                    "type": "plain_text",
                    "text": "CI/CD ${{ github.event.workflow_run.conclusion == 'success' && 'Passed' || 'Failed' }}"
                  }
                },
                {
                  "type": "section",
                  "fields": [
                    {
                      "type": "mrkdwn",
                      "text": "*Workflow:*\n${{ github.event.workflow_run.name }}"
                    },
                    {
                      "type": "mrkdwn",
                      "text": "*Branch:*\n${{ github.event.workflow_run.head_branch }}"
                    },
                    {
                      "type": "mrkdwn",
                      "text": "*Actor:*\n${{ github.event.workflow_run.actor.login }}"
                    },
                    {
                      "type": "mrkdwn",
                      "text": "*Run:*\n<${{ github.event.workflow_run.html_url }}|View>"
                    }
                  ]
                }
              ]
            }
```

### Slack com Rich Message

```yaml
- name: Rich Slack notification
  uses: slackapi/slack-github-action@v1
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK }}
    webhook-type: incoming-webhook
    payload: |
      {
        "attachments": [
          {
            "color": "${{ github.event.workflow_run.conclusion == 'success' && '#36a64f' || '#ff0000' }}",
            "blocks": [
              {
                "type": "section",
                "text": {
                  "type": "mrkdwn",
                  "text": "*${{ github.event.workflow_run.conclusion == 'success' && 'Build Passed' || 'Build Failed' }}*\nWorkflow: ${{ github.event.workflow_run.name }}\nBranch: ${{ github.event.workflow_run.head_branch }}"
                }
              },
              {
                "type": "actions",
                "elements": [
                  {
                    "type": "button",
                    "text": {
                      "type": "plain_text",
                      "text": "View Run"
                    },
                    "url": "${{ github.event.workflow_run.html_url }}"
                  }
                ]
              }
            ]
          }
        ]
      }
```

### Discord com Webhook

```yaml
- name: Discord notification
  if: always()
  uses: Ilshidur/action-discord@0.3.2
  env:
    DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
  with:
    args: |
      **${{ github.event.workflow_run.conclusion == 'success' && 'Build Passed' || 'Build Failed' }}**
      Workflow: ${{ github.event.workflow_run.name }}
      Branch: ${{ github.event.workflow_run.head_branch }}
      <${{ github.event.workflow_run.html_url }}>
```

### Discord com Embed

```yaml
- name: Discord embed notification
  run: |
    COLOR=$( [ "${{ github.event.workflow_run.conclusion }}" = "success" ] && echo "3066993" || echo "15158332" )
    TITLE=$( [ "${{ github.event.workflow_run.conclusion }}" = "success" ] && echo "Build Passed" || echo "Build Failed" )

    curl -s -H "Content-Type: application/json" \
      -d "{
        \"embeds\": [{
          \"title\": \"$TITLE\",
          \"description\": \"Workflow: ${{ github.event.workflow_run.name }}\",
          \"color\": $COLOR,
          \"fields\": [
            {\"name\": \"Branch\", \"value\": \"${{ github.event.workflow_run.head_branch }}\", \"inline\": true},
            {\"name\": \"Actor\", \"value\": \"${{ github.event.workflow_run.actor.login }}\", \"inline\": true},
            {\"name\": \"Run\", \"value\": \"[View](${{ github.event.workflow_run.html_url }})\"}
          ]
        }]
      }" \
      "${{ secrets.DISCORD_WEBHOOK }}"
```

### Email (Built-in)

Configurado em Settings > Notifications > Actions.

### Notificacao Condicional

```yaml
jobs:
  notify:
    needs: [build, test, deploy]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Determine notification type
        id: notify
        run: |
          if [ "${{ needs.deploy.result }}" == "success" ]; then
            echo "type=success" >> "$GITHUB_OUTPUT"
            echo "message=Deploy completed successfully" >> "$GITHUB_OUTPUT"
          elif [ "${{ needs.test.result }}" == "failure" ]; then
            echo "type=failure" >> "$GITHUB_OUTPUT"
            echo "message=Tests failed" >> "$GITHUB_OUTPUT"
          elif [ "${{ needs.build.result }}" == "failure" ]; then
            echo "type=failure" >> "$GITHUB_OUTPUT"
            echo "message=Build failed" >> "$GITHUB_OUTPUT"
          else
            echo "type=warning" >> "$GITHUB_OUTPUT"
            echo "message=Workflow completed with issues" >> "$GITHUB_OUTPUT"
          fi

      - name: Send notification
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": "${{ steps.notify.outputs.message }}",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "${{ steps.notify.outputs.type == 'success' && ':white_check_mark:' || ':x:' }} ${{ steps.notify.outputs.message }}\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View Run>"
                  }
                }
              ]
            }
```

### Notificacao por Canal Diferente

```yaml
jobs:
  notify-slack:
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_ALERTS_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Build failed: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}

  notify-email:
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "Build Failed: ${{ github.repository }}"
          body: "Build failed. View: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          to: team@example.com
          from: ci@example.com
```

---

## 16.7 Status Badges

### Badge Basico

```markdown
![Build](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
```

### Badge com Link

```markdown
[![Build](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
```

### Badge por Branch

```markdown
![Build](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg?branch=main)
```

### Badge Customizado com Shields.io

```markdown
![Build Status](https://img.shields.io/github/actions/workflow/status/OWNER/REPO/ci.yml?branch=main&label=build)
![Coverage](https://img.shields.io/codecov/c/github/OWNER/REPO)
![License](https://img.shields.io/github/license/OWNER/REPO)
```

### Badge com Status Dinamico

```yaml
name: Update Badge

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  update-badge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Update badge
        run: |
          STATUS="${{ github.event.workflow_run.conclusion }}"
          COLOR=$( [ "$STATUS" = "success" ] && echo "brightgreen" || echo "red" )

          # Atualizar badge no README
          sed -i "s/build-passing/build-${STATUS}/g" README.md
          sed -i "s/color-brightgreen/color-${COLOR}/g" README.md
```

### Badge com Evento

```yaml
name: Badge Update

on:
  push:
    branches: [main]

jobs:
  badge:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Update badge
        run: |
          STATUS="passing"
          BADGE="[![CI](https://img.shields.io/badge/CI-${STATUS}-brightgreen)](${{ github.server_url }}/${{ github.repository }}/actions)"

          # Atualizar README
          sed -i "s|\[![CI\](.*)\](.*)|${BADGE}|" README.md

          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add README.md
          git diff --staged --quiet || git commit -m "ci: update badge"
          git push
```

### Badge com gh API

```bash
# Criar badge customizado
curl -s "https://img.shields.io/badge/build-passing-brightgreen" > badge.svg
```

---

## 16.8 Failure Alerts

### Alerta em Tempo Real

```yaml
name: Failure Alert

on:
  workflow_run:
    workflows: ["CI", "CD"]
    types: [completed]

jobs:
  alert:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Send alert
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_ALERTS_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {
              "text": ":rotating_light: ALERT: Build Failed",
              "blocks": [
                {
                  "type": "header",
                  "text": {
                    "type": "plain_text",
                    "text": "Build Failed Alert"
                  }
                },
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Workflow:* ${{ github.event.workflow_run.name }}\n*Branch:* ${{ github.event.workflow_run.head_branch }}\n*Actor:* ${{ github.event.workflow_run.actor.login }}\n*Run:* <${{ github.event.workflow_run.html_url }}|View Details>"
                  }
                },
                {
                  "type": "context",
                  "elements": [
                    {
                      "type": "mrkdwn",
                      "text": "Failed at ${{ github.event.workflow_run.updated_at }}"
                    }
                  ]
                }
              ]
            }
```

### Alerta com Retry Automatico

```yaml
name: Auto-Retry Alert

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  check-and-retry:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Check retry count
        id: retry
        run: |
          RUN_ID="${{ github.event.workflow_run.id }}"
          RETRY_KEY="retry-$RUN_ID"

          # Verificar se ja tentamos retry
          PREVIOUS=$(gh run list --workflow=ci.yml --limit=5 --json databaseId,conclusion | \
            jq '[.[] | select(.conclusion == "failure")] | length')

          echo "Previous failures: $PREVIOUS"
          echo "should_retry=$( [ "$PREVIOUS" -lt 2 ] && echo true || echo false )" >> "$GITHUB_OUTPUT"

      - name: Retry if needed
        if: steps.retry.outputs.should_retry == 'true'
        run: |
          echo "Auto-retrying workflow..."
          gh run rerun ${{ github.event.workflow_run.id }} --failed
```

### Alerta com Escalacao

```yaml
name: Escalation Alert

on:
  workflow_run:
    workflows: ["Production Deploy"]
    types: [completed]

jobs:
  alert:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Immediate alert
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_ONCALL_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": ":rotating_light: PRODUCTION DEPLOY FAILED"}

      - name: Page on-call after 5 minutes
        if: always()
        run: |
          sleep 300
          # Integracao com PagerDuty/OpsGenie
          curl -s -X POST \
            -H "Authorization: Token ${{ secrets.PAGERDUTY_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{
              "incident": {
                "type": "incident",
                "title": "Production deploy failed",
                "service": {"id": "SERVICE_ID"},
                "urgency": "high"
              }
            }' \
            "https://api.pagerduty.com/incidents"
```

---

## 16.9 CI/CD SLA

### Definicao de SLA

| Metrica | Meta | Alerta |
|---------|------|--------|
| Build time | < 10 min | > 15 min |
| Deploy time | < 5 min | > 10 min |
| Success rate | > 95% | < 90% |
| MTTR | < 30 min | > 60 min |
| Pipeline frequency | > 10/dia | < 5/dia |

### Monitoramento de SLA

```yaml
name: SLA Monitor

on:
  schedule:
    - cron: '0 * * * *'  # A cada hora

jobs:
  check-sla:
    runs-on: ubuntu-latest
    steps:
      - name: Check build SLA
        run: |
          # Pegar ultimas 100 runs
          RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?per_page=100")

          TOTAL=$(echo "$RUNS" | jq '.total_count')
          SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')

          if [ "$TOTAL" -gt 0 ]; then
            SUCCESS_RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
          else
            SUCCESS_RATE="0"
          fi

          echo "Success rate: $SUCCESS_RATE%"

          # Verificar SLA
          if (( $(echo "$SUCCESS_RATE < 95" | bc -l) )); then
            echo "::error::SLA breach: success rate is $SUCCESS_RATE% (target: >95%)"
            # Enviar alerta
          fi

      - name: Check build time SLA
        run: |
          RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?per_page=10")

          # Calcular tempo medio
          echo "$RUNS" | jq -r '.workflow_runs[] | select(.conclusion == "success") | {
            start: .run_started_at,
            end: .updated_at
          }' | \
          while read -r line; do
            START=$(echo "$line" | jq -r '.start')
            END=$(echo "$line" | jq -r '.end')
            # Processar tempo medio
          done
```

### Dashboard de SLA

```yaml
name: SLA Dashboard

on:
  schedule:
    - cron: '0 9 * * 1'  # Toda segunda-feira

jobs:
  sla-report:
    runs-on: ubuntu-latest
    steps:
      - name: Generate SLA report
        run: |
          echo "## SLA Report - $(date +%Y-%m-%d)" > sla-report.md
          echo "" >> sla-report.md

          echo "### Build SLA" >> sla-report.md
          echo "| Metrica | Actual | Target | Status |" >> sla-report.md
          echo "|---------|--------|--------|--------|" >> sla-report.md
          echo "| Success rate | 97.5% | >95% | PASS |" >> sla-report.md
          echo "| Avg build time | 8.2 min | <10 min | PASS |" >> sla-report.md
          echo "| P95 build time | 12.1 min | <15 min | PASS |" >> sla-report.md

          echo "" >> sla-report.md
          echo "### Deploy SLA" >> sla-report.md
          echo "| Metrica | Actual | Target | Status |" >> sla-report.md
          echo "|---------|--------|--------|--------|" >> sla-report.md
          echo "| Deploy success | 99.1% | >99% | PASS |" >> sla-report.md
          echo "| Avg deploy time | 3.4 min | <5 min | PASS |" >> sla-report.md
          echo "| Rollback rate | 0.9% | <1% | PASS |" >> sla-report.md

          cat sla-report.md
```

---

## 16.10 Monitoring Dashboard

### Dashboard Completo com YAML

```yaml
name: Monitoring Dashboard

on:
  schedule:
    - cron: '0 */6 * * *'  # A cada 6 horas
  workflow_dispatch:

jobs:
  dashboard:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4

      - name: Generate dashboard
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          API="https://api.github.com/repos/${{ github.repository }}"
          NOW=$(date +%Y-%m-%dT%H:%M:%SZ)
          WEEK_AGO=$(date -d "-7 days" +%Y-%m-%dT%H:%M:%SZ)

          echo "# CI/CD Monitoring Dashboard" > dashboard.md
          echo "" >> dashboard.md
          echo "Generated at: $NOW" >> dashboard.md
          echo "" >> dashboard.md

          # === WORKFLOW RUNS ===
          echo "## Workflow Runs (Last 7 Days)" >> dashboard.md
          echo "" >> dashboard.md

          RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "$API/actions/runs?created=>$WEEK_AGO&per_page=100")

          TOTAL=$(echo "$RUNS" | jq '.total_count')
          SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
          FAILURE=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')
          CANCELLED=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "cancelled")] | length')

          if [ "$TOTAL" -gt 0 ]; then
            RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
          else
            RATE="0"
          fi

          echo "| Metric | Value |" >> dashboard.md
          echo "|--------|-------|" >> dashboard.md
          echo "| Total runs | $TOTAL |" >> dashboard.md
          echo "| Successful | $SUCCESS |" >> dashboard.md
          echo "| Failed | $FAILURE |" >> dashboard.md
          echo "| Cancelled | $CANCELLED |" >> dashboard.md
          echo "| Success rate | ${RATE}% |" >> dashboard.md

          # === WORKFLOW BREAKDOWN ===
          echo "" >> dashboard.md
          echo "## Runs by Workflow" >> dashboard.md
          echo "" >> dashboard.md
          echo "| Workflow | Total | Success | Failed |" >> dashboard.md
          echo "|----------|-------|---------|--------|" >> dashboard.md

          echo "$RUNS" | jq -r '.workflow_runs[].name' | sort | uniq -c | sort -rn | while read count name; do
            WF_SUCCESS=$(echo "$RUNS" | jq "[.workflow_runs[] | select(.name == \"$name\" and .conclusion == \"success\")] | length")
            WF_FAILURE=$(echo "$RUNS" | jq "[.workflow_runs[] | select(.name == \"$name\" and .conclusion == \"failure\")] | length")
            echo "| $name | $count | $WF_SUCCESS | $WF_FAILURE |" >> dashboard.md
          done

          # === RECENT FAILURES ===
          echo "" >> dashboard.md
          echo "## Recent Failures" >> dashboard.md
          echo "" >> dashboard.md

          echo "$RUNS" | jq -r '.workflow_runs[] | select(.conclusion == "failure") | "| [\(.name)](\(.html_url)) | \(.head_branch) | \(.actor.login) | \(.created_at) |"' | head -10 >> dashboard.md

          cat dashboard.md

      - name: Commit dashboard
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add dashboard.md
          git diff --staged --quiet || git commit -m "ci: update monitoring dashboard"
          git push
```

### Dashboard com Status Page

```yaml
name: Status Page

on:
  schedule:
    - cron: '*/30 * * * *'

jobs:
  status:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate status
        run: |
          echo "# System Status" > STATUS.md
          echo "" >> STATUS.md
          echo "Last updated: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> STATUS.md
          echo "" >> STATUS.md

          echo "## Services" >> STATUS.md
          echo "" >> STATUS.md
          echo "| Service | Status | Last Check |" >> STATUS.md
          echo "|---------|--------|------------|" >> STATUS.md

          # Verificar cada servico
          SERVICES=("api" "web" "worker")
          for SVC in "${SERVICES[@]}"; do
            # Health check
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$SVC.example.com/health" || echo "000")
            if [ "$HTTP_CODE" = "200" ]; then
              STATUS="Operational"
            else
              STATUS="Degraded"
            fi
            echo "| $SVC | $STATUS | $(date -u +%H:%M:%SZ) |" >> STATUS.md
          done

          cat STATUS.md
```

---

## 16.11 Relatorios Automaticos

### Relatorio Semanal

```yaml
name: Weekly Report

on:
  schedule:
    - cron: '0 9 * * 1'  # Toda segunda-feira

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - name: Generate weekly report
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          WEEK_AGO=$(date -d "-7 days" +%Y-%m-%dT%H:%M:%SZ)
          API="https://api.github.com/repos/${{ github.repository }}"

          echo "# Weekly CI/CD Report" > report.md
          echo "Week of $(date -d '7 days ago' +%Y-%m-%d) to $(date +%Y-%m-%d)" >> report.md
          echo "" >> report.md

          RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "$API/actions/runs?created=>$WEEK_AGO&per_page=100")

          TOTAL=$(echo "$RUNS" | jq '.total_count')
          SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')
          FAILURE=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "failure")] | length')

          echo "## Summary" >> report.md
          echo "- Total runs: $TOTAL" >> report.md
          echo "- Success: $SUCCESS" >> report.md
          echo "- Failures: $FAILURE" >> report.md

          if [ "$TOTAL" -gt 0 ]; then
            RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
            echo "- Success rate: ${RATE}%" >> report.md
          fi

          cat report.md

      - name: Create GitHub issue
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('report.md', 'utf8');
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Weekly CI/CD Report - ${new Date().toISOString().slice(0, 10)}`,
              body: report,
              labels: ['report', 'ci-cd']
            });
```

### Relatorio de Performance

```yaml
name: Performance Report

on:
  schedule:
    - cron: '0 10 1 * *'  # Primeiro dia do mes

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
      - name: Monthly performance report
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          MONTH_START=$(date -d "last month" +%Y-%m-01)
          MONTH_END=$(date -d "this month" +%Y-%m-01)

          echo "# Monthly Performance Report" > perf-report.md
          echo "Month: $(date -d 'last month' +%Y-%m)" >> perf-report.md
          echo "" >> perf-report.md

          RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>=$MONTH_START&created=<=$MONTH_END&per_page=100")

          TOTAL=$(echo "$RUNS" | jq '.total_count')
          SUCCESS=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion == "success")] | length')

          echo "## Metrics" >> perf-report.md
          echo "- Total runs: $TOTAL" >> perf-report.md
          echo "- Success rate: $(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)%" >> perf-report.md

          cat perf-report.md
```

---

## 16.12 Observabilidade End-to-End

### Trace de Deploy

```yaml
name: Deploy Trace

on:
  push:
    branches: [main]

jobs:
  trace:
    runs-on: ubuntu-latest
    outputs:
      trace-id: ${{ steps.trace.outputs.trace-id }}
    steps:
      - name: Start trace
        id: trace
        run: |
          TRACE_ID="trace-$(date +%s)-${{ github.run_id }}"
          echo "trace-id=$TRACE_ID" >> "$GITHUB_OUTPUT"
          echo "## Deploy Trace" >> "$GITHUB_STEP_SUMMARY"
          echo "Trace ID: \`$TRACE_ID\`" >> "$GITHUB_STEP_SUMMARY"

      - uses: actions/checkout@v4

      - name: Build
        id: build
        run: |
          START=$(date +%s%N)
          npm ci && npm run build
          END=$(date +%s%N)
          DURATION=$(( (END - START) / 1000000 ))
          echo "build_duration=$DURATION" >> "$GITHUB_OUTPUT"
          echo "- Build: ${DURATION}ms" >> "$GITHUB_STEP_SUMMARY"

      - name: Test
        id: test
        run: |
          START=$(date +%s%N)
          npm test
          END=$(date +%s%N)
          DURATION=$(( (END - START) / 1000000 ))
          echo "test_duration=$DURATION" >> "$GITHUB_OUTPUT"
          echo "- Test: ${DURATION}ms" >> "$GITHUB_STEP_SUMMARY"

      - name: Deploy
        id: deploy
        run: |
          START=$(date +%s%N)
          echo "Deploying..."
          sleep 5
          END=$(date +%s%N)
          DURATION=$(( (END - START) / 1000000 ))
          echo "deploy_duration=$DURATION" >> "$GITHUB_OUTPUT"
          echo "- Deploy: ${DURATION}ms" >> "$GITHUB_STEP_SUMMARY"

      - name: Total trace
        run: |
          TOTAL=$(( ${{ steps.build.outputs.build_duration }} + ${{ steps.test.outputs.test_duration }} + ${{ steps.deploy.outputs.deploy_duration }} ))
          echo "- **Total: ${TOTAL}ms**" >> "$GITHUB_STEP_SUMMARY"
```

### Health Check End-to-End

```yaml
name: E2E Health Check

on:
  schedule:
    - cron: '*/5 * * * *'

jobs:
  health:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api, web, worker]
    steps:
      - name: Health check ${{ matrix.service }}
        run: |
          HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            "https://${{ matrix.service }}.example.com/health")

          if [ "$HTTP_CODE" = "200" ]; then
            echo "## ${{ matrix.service }}: HEALTHY" >> "$GITHUB_STEP_SUMMARY"
          else
            echo "## ${{ matrix.service }}: UNHEALTHY (HTTP $HTTP_CODE)" >> "$GITHUB_STEP_SUMMARY"
            exit 1
          fi
```

### Metricas de Latencia

```yaml
name: Latency Monitor

on:
  schedule:
    - cron: '*/10 * * * *'

jobs:
  latency:
    runs-on: ubuntu-latest
    steps:
      - name: Measure API latency
        run: |
          echo "## API Latency" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Endpoint | Latency | Status |" >> "$GITHUB_STEP_SUMMARY"
          echo "|----------|---------|--------|" >> "$GITHUB_STEP_SUMMARY"

          ENDPOINTS=("/health" "/api/v1/users" "/api/v1/products")
          for EP in "${ENDPOINTS[@]}"; do
            START=$(date +%s%N)
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://api.example.com$EP")
            END=$(date +%s%N)
            LATENCY=$(( (END - START) / 1000000 ))

            echo "| $EP | ${LATENCY}ms | $HTTP_CODE |" >> "$GITHUB_STEP_SUMMARY"
          done
```

---

## 16.13 Exercicios

1. Implemente notification via Slack para builds que falharam
2. Crie um script que calcule custos mensais de GitHub Actions
3. Configure status badge no README do repositorio
4. Implemente alertas para builds que excedem timeout
5. Crie dashboard com metricas de build time
6. Implemente monitoring de self-hosted runners
7. Configure relatorio semanal automatico
8. Implemente SLA monitoring com alertas
9. Crie health check end-to-end para todos os servicos
10. Implemente trace de deploy com metricas de latencia

---

## 16.14 Monitoramento de Seguranca

### Security Scan Metrics

```yaml
name: Security Scan Metrics

on:
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira

jobs:
  security-metrics:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Dependabot alerts
        run: |
          ALERTS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/vulnerability-alerts" | \
            jq '.total_count' 2>/dev/null || echo "0")

          echo "## Security Metrics" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Dependabot alerts | $ALERTS |" >> "$GITHUB_STEP_SUMMARY"

      - name: Code scanning alerts
        run: |
          ALERTS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/code-scanning/alerts" | \
            jq '.total_count' 2>/dev/null || echo "0")

          echo "| Code scanning alerts | $ALERTS |" >> "$GITHUB_STEP_SUMMARY"

      - name: Secret scanning alerts
        run: |
          ALERTS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/secret-scanning/alerts" | \
            jq '.total_count' 2>/dev/null || echo "0")

          echo "| Secret scanning alerts | $ALERTS |" >> "$GITHUB_STEP_SUMMARY"
```

### Supply Chain Monitoring

```yaml
name: Supply Chain Monitor

on:
  schedule:
    - cron: '0 7 * * *'  # Diario

jobs:
  check-actions:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Audit action versions
        run: |
          echo "## Action Version Audit" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Action | Version | Pinned |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|---------|--------|" >> "$GITHUB_STEP_SUMMARY"

          grep -r "uses:" .github/workflows/ | \
            sed 's/.*uses: //' | sort -u | while read action; do
              if echo "$action" | grep -qE "@[a-f0-9]{40}"; then
                echo "| $action | SHA | YES |" >> "$GITHUB_STEP_SUMMARY"
              elif echo "$action" | grep -qE "@v[0-9]"; then
                echo "| $action | Tag | NO |" >> "$GITHUB_STEP_SUMMARY"
              else
                echo "| $action | Branch | NO |" >> "$GITHUB_STEP_SUMMARY"
              fi
            done
```

### License Compliance

```yaml
name: License Compliance

on:
  pull_request:
    branches: [main]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check licenses
        run: |
          npm install -g license-checker
          license-checker --production --json > licenses.json

          # Verificar licencas proibidas
          PROHIBITED=("GPL-3.0" "AGPL-3.0" "SSPL-1.0")

          echo "## License Check" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"

          for lic in "${PROHIBITED[@]}"; do
            COUNT=$(jq -r "to_entries[] | select(.value.licenses == \"$lic\") | .key" licenses.json | wc -l)
            if [ "$COUNT" -gt 0 ]; then
              echo "::warning::Found $COUNT packages with prohibited license: $lic"
              echo "| $lic | $COUNT packages |" >> "$GITHUB_STEP_SUMMARY"
            fi
          done
```

---

## 16.15 Monitoramento de Performance de Builds

### Build Time Tracking

```yaml
name: Build Time Tracker

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  track:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate build time
        run: |
          START="${{ github.event.workflow_run.run_started_at }}"
          END="${{ github.event.workflow_run.updated_at }}"

          START_EPOCH=$(date -d "$START" +%s)
          END_EPOCH=$(date -d "$END" +%s)
          DURATION=$((END_EPOCH - START_EPOCH))

          MINUTES=$((DURATION / 60))
          SECONDS=$((DURATION % 60))

          echo "Build time: ${MINUTES}m ${SECONDS}s"
          echo "Build time seconds: $DURATION"

          # Alertar se build demorou mais que 10 minutos
          if [ "$DURATION" -gt 600 ]; then
            echo "::warning::Build took longer than 10 minutes ($DURATION seconds)"
          fi
```

### Build Time Trend

```yaml
name: Build Time Trend

on:
  schedule:
    - cron: '0 9 * * 1'

jobs:
  trend:
    runs-on: ubuntu-latest
    steps:
      - name: Analyze build times
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "## Build Time Trend (Last 30 Days)" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Date | Avg Build Time | Runs |" >> "$GITHUB_STEP_SUMMARY"
          echo "|------|----------------|------|" >> "$GITHUB_STEP_SUMMARY"

          for i in $(seq 0 29); do
            DATE=$(date -d "-$i days" +%Y-%m-%d)
            NEXT_DATE=$(date -d "-$((i-1)) days" +%Y-%m-%d)

            RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
              "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>$DATE&created<$NEXT_DATE&per_page=100" | \
              jq '.total_count')

            if [ "$RUNS" -gt 0 ]; then
              echo "| $DATE | - | $RUNS |" >> "$GITHUB_STEP_SUMMARY"
            fi
          done
```

### Performance Regression Detection

```yaml
name: Performance Regression

on:
  pull_request:
    branches: [main]

jobs:
  perf-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Measure PR build time
        id: pr
        run: |
          START=$(date +%s%N)
          npm ci && npm run build
          END=$(date +%s%N)
          DURATION=$(( (END - START) / 1000000 ))
          echo "duration=$DURATION" >> "$GITHUB_OUTPUT"

      - name: Get main build time
        id: main
        run: |
          # Pegar tempo medio dos ultimos 5 builds do main
          RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?branch=main&status=success&per_page=5")

          echo "Main average: (simulated)"
          echo "duration=30000" >> "$GITHUB_OUTPUT"

      - name: Compare
        run: |
          PR_TIME=${{ steps.pr.outputs.duration }}
          MAIN_TIME=${{ steps.main.outputs.duration }}

          DIFF=$(( (PR_TIME - MAIN_TIME) * 100 / MAIN_TIME ))

          echo "PR build time: ${PR_TIME}ms"
          echo "Main avg build time: ${MAIN_TIME}ms"
          echo "Difference: ${DIFF}%"

          if [ "$DIFF" -gt 20 ]; then
            echo "::warning::Build time regression detected: ${DIFF}% slower"
          fi
```

---

## 16.16 Taxa de Sucesso de Deploys

### Deploy Success Rate

```yaml
name: Deploy Success Rate

on:
  workflow_run:
    workflows: ["Deploy"]
    types: [completed]

jobs:
  track:
    runs-on: ubuntu-latest
    steps:
      - name: Record deploy result
        run: |
          CONCLUSION="${{ github.event.workflow_run.conclusion }}"
          BRANCH="${{ github.event.workflow_run.head_branch }}"
          RUN_ID="${{ github.event.workflow_run.id }}"

          echo "Deploy result: $CONCLUSION"
          echo "Branch: $BRANCH"
          echo "Run: $RUN_ID"

          # Alertar se deploy falhou
          if [ "$CONCLUSION" = "failure" ]; then
            echo "::error::Deploy failed on branch $BRANCH"
          fi
```

### Deploy Frequency

```yaml
name: Deploy Frequency

on:
  schedule:
    - cron: '0 9 * * 1'

jobs:
  frequency:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate deploy frequency
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          WEEK_AGO=$(date -d "-7 days" +%Y-%m-%dT%H:%M:%SZ)

          DEPLOYS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>$WEEK_AGO&per_page=100" | \
            jq '[.workflow_runs[] | select(.name | test("deploy"; "i"))] | length')

          echo "## Deploy Frequency" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "Deploys this week: $DEPLOYS" >> "$GITHUB_STEP_SUMMARY"
          echo "Average per day: $(echo "scale=1; $DEPLOYS / 7" | bc)" >> "$GITHUB_STEP_SUMMARY"
```

### Rollback Rate

```yaml
name: Rollback Monitoring

on:
  workflow_run:
    workflows: ["Rollback"]
    types: [completed]

jobs:
  track:
    runs-on: ubuntu-latest
    steps:
      - name: Record rollback
        run: |
          echo "## Rollback Event" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Field | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|-------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Workflow | ${{ github.event.workflow_run.name }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Conclusion | ${{ github.event.workflow_run.conclusion }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Branch | ${{ github.event.workflow_run.head_branch }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Actor | ${{ github.event.workflow_run.actor.login }} |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Time | ${{ github.event.workflow_run.updated_at }} |" >> "$GITHUB_STEP_SUMMARY"

      - name: Alert
        if: github.event.workflow_run.conclusion == 'failure'
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_ALERTS_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Rollback failed! Immediate attention required."}
```

---

## 16.17 Alertas de Regressao

### Code Regression Alert

```yaml
name: Regression Alert

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  check-regression:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Check if regression
        run: |
          # Verificar se o workflow anterior passou
          PREV_RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=success&per_page=1")

          PREV_CONCLUSION=$(echo "$PREV_RUNS" | jq -r '.workflow_runs[0].conclusion')

          if [ "$PREV_CONCLUSION" = "success" ]; then
            echo "::error::Regression detected! Previous run passed, current run failed."
            echo "This is likely a regression introduced by recent changes."
          fi
```

### Test Regression Alert

```yaml
name: Test Regression

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  test-regression:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Compare test results
        run: |
          echo "## Test Regression Analysis" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "Current run failed. Comparing with previous successful run..." >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"

          # Baixar logs do run atual
          curl -L -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs/${{ github.run_id }}/logs" \
            -o current-logs.zip

          # Analisar falhas
          echo "### Failed Tests" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "Check the workflow logs for detailed failure information." >> "$GITHUB_STEP_SUMMARY"
```

### Performance Regression Alert

```yaml
name: Performance Regression Alert

on:
  schedule:
    - cron: '0 * * * *'  # A cada hora

jobs:
  perf-regression:
    runs-on: ubuntu-latest
    steps:
      - name: Check performance
        run: |
          # Pegar ultimas 10 builds de sucesso
          RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=success&per_page=10")

          # Calcular tempo medio
          echo "Analyzing build performance..."

          # Se build medio > 15 minutos, alertar
          echo "Average build time: (check logs)"
          echo "Performance threshold: 15 minutes"
```

---

## 16.18 Monitoramento de Infraestrutura

### Runner Infrastructure Metrics

```yaml
name: Infrastructure Metrics

on:
  schedule:
    - cron: '*/15 * * * *'  # A cada 15 minutos

jobs:
  metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Collect infrastructure metrics
        run: |
          echo "## Infrastructure Metrics" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"

          # GitHub-hosted runners
          echo "| GitHub-hosted runners | Available |" >> "$GITHUB_STEP_SUMMARY"

          # Self-hosted runners
          RUNNERS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runners" | \
            jq '.total_count')
          echo "| Self-hosted runners | $RUNNERS |" >> "$GITHUB_STEP_SUMMARY"

          # Queued workflows
          QUEUED=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=queued" | \
            jq '.total_count')
          echo "| Queued workflows | $QUEUED |" >> "$GITHUB_STEP_SUMMARY"

          # Active workflows
          ACTIVE=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=in_progress" | \
            jq '.total_count')
          echo "| Active workflows | $ACTIVE |" >> "$GITHUB_STEP_SUMMARY"
```

### Docker Registry Metrics

```yaml
name: Docker Registry Metrics

on:
  schedule:
    - cron: '0 */6 * * *'

jobs:
  registry:
    runs-on: ubuntu-latest
    steps:
      - name: Check Docker registry
        run: |
          echo "## Docker Registry Metrics" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"

          # Listar imagens
          echo "### Recent Images" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Image | Tag | Size | Pushed |" >> "$GITHUB_STEP_SUMMARY"
          echo "|-------|-----|------|--------|" >> "$GITHUB_STEP_SUMMARY"

          # Consultar API do GitHub Container Registry
          PACKAGES=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/orgs/${{ github.repository_owner }}/packages?package_type=container&per_page=10")

          echo "$PACKAGES" | jq -r '.[] | "| \(.name) | latest | - | - |"' >> "$GITHUB_STEP_SUMMARY" 2>/dev/null || echo "| No packages found | - | - | - |" >> "$GITHUB_STEP_SUMMARY"
```

### Cache Metrics

```yaml
name: Cache Metrics

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  cache-stats:
    runs-on: ubuntu-latest
    steps:
      - name: Cache hit rate
        run: |
          echo "## Cache Statistics" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "Workflow: ${{ github.event.workflow_run.name }}" >> "$GITHUB_STEP_SUMMARY"
          echo "Run: ${{ github.event.workflow_run.html_url }}" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "Cache performance is tracked per-workflow." >> "$GITHUB_STEP_SUMMARY"
          echo "Check individual step logs for cache-hit status." >> "$GITHUB_STEP_SUMMARY"
```

---

## 16.19 Alertas e Notificacoes Avancadas

### Multi-Channel Notification

```yaml
name: Multi-Channel Alert

on:
  workflow_run:
    workflows: ["Production Deploy"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      # Slack
      - name: Slack alert
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Production deploy failed!"}

      # Discord
      - name: Discord alert
        uses: Ilshidur/action-discord@0.3.2
        env:
          DISCORD_WEBHOOK: ${{ secrets.DISCORD_WEBHOOK }}
        with:
          args: "Production deploy failed!"

      # Email
      - name: Email alert
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "ALERT: Production Deploy Failed"
          body: "Production deploy has failed. Immediate action required."
          to: oncall@example.com
          from: ci@example.com

      # GitHub Issue
      - name: Create incident issue
        uses: actions/github-script@v7
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `Incident: Production deploy failed - ${new Date().toISOString()}`,
              body: `## Incident Report\n\n**Workflow:** ${{ github.event.workflow_run.name }}\n**Run:** ${{ github.event.workflow_run.html_url }}\n**Branch:** ${{ github.event.workflow_run.head_branch }}\n\nImmediate attention required.`,
              labels: ['incident', 'production', 'urgent']
            });
```

### Notification Throttling

```yaml
name: Throttled Notifications

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  notify:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      - name: Check notification cooldown
        id: cooldown
        run: |
          # Verificar ultima notificacao
          LAST_NOTIFICATION=$(cat last-notification.txt 2>/dev/null || echo "0")
          CURRENT_TIME=$(date +%s)
          COOLDOWN=300  # 5 minutos

          if [ $((CURRENT_TIME - LAST_NOTIFICATION)) -gt $COOLDOWN ]; then
            echo "should_notify=true" >> "$GITHUB_OUTPUT"
            echo "$CURRENT_TIME" > last-notification.txt
          else
            echo "should_notify=false" >> "$GITHUB_OUTPUT"
          fi

      - name: Send notification
        if: steps.cooldown.outputs.should_notify == 'true'
        uses: slackapi/slack-github-action@v1
        with:
          webhook: ${{ secrets.SLACK_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": "Build failed (notification throttled to every 5 min)"}
```

---

## 16.20 Dashboard com Grafana/Prometheus

### Export Metrics to Prometheus

```yaml
name: Prometheus Export

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]

jobs:
  export:
    runs-on: ubuntu-latest
    steps:
      - name: Push metrics
        run: |
          START="${{ github.event.workflow_run.run_started_at }}"
          END="${{ github.event.workflow_run.updated_at }}"
          START_EPOCH=$(date -d "$START" +%s)
          END_EPOCH=$(date -d "$END" +%s)
          DURATION=$((END_EPOCH - START_EPOCH))

          CONCLUSION="${{ github.event.workflow_run.conclusion }}"
          if [ "$CONCLUSION" = "success" ]; then
            SUCCESS=1
          else
            SUCCESS=0
          fi

          # Push to Pushgateway
          cat <<EOF | curl -s --data-binary @- \
            "http://pushgateway:9091/metrics/job/github_actions/workflow/${{ github.event.workflow_run.name }}"
          # HELP github_actions_workflow_duration_seconds Duration of workflow runs
          # TYPE github_actions_workflow_duration_seconds gauge
          github_actions_workflow_duration_seconds{workflow="${{ github.event.workflow_run.name }}",branch="${{ github.event.workflow_run.head_branch }}"} $DURATION
          # HELP github_actions_workflow_success Whether the workflow succeeded
          # TYPE github_actions_workflow_success gauge
          github_actions_workflow_success{workflow="${{ github.event.workflow_run.name }}",branch="${{ github.event.workflow_run.head_branch }}"} $SUCCESS
          EOF
```

### Grafana Dashboard JSON

```json
{
  "dashboard": {
    "title": "GitHub Actions CI/CD",
    "panels": [
      {
        "title": "Build Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(github_actions_workflow_success) / count(github_actions_workflow_success) * 100"
          }
        ]
      },
      {
        "title": "Build Duration",
        "type": "graph",
        "targets": [
          {
            "expr": "github_actions_workflow_duration_seconds"
          }
        ]
      },
      {
        "title": "Failed Builds",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(github_actions_workflow_success == 0)"
          }
        ]
      }
    ]
  }
}
```

---

## 16.21 Exercicios

1. Implemente notification via Slack para builds que falharam
2. Crie um script que calcule custos mensais de GitHub Actions
3. Configure status badge no README do repositorio
4. Implemente alertas para builds que excedem timeout
5. Crie dashboard com metricas de build time
6. Implemente monitoring de self-hosted runners
7. Configure relatorio semanal automatico
8. Implemente SLA monitoring com alertas
9. Crie health check end-to-end para todos os servicos
10. Implemente trace de deploy com metricas de latencia
11. Configure multi-channel notifications (Slack + Discord + Email)
12. Implemente notification throttling para evitar spam
13. Crie export de metricas para Prometheus
14. Implemente regression alerting
15. Configure supply chain monitoring

---

## 16.22 Cost Allocation por Team

### Atribuicao de Custo por Time

```yaml
name: Cost Allocation

on:
  schedule:
    - cron: '0 9 1 * *'  # Primeiro dia do mes

jobs:
  allocate:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate team costs
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "## Monthly Cost Allocation" > cost-report.md
          echo "Month: $(date -d 'last month' +%Y-%m)" >> cost-report.md
          echo "" >> cost-report.md

          echo "### Cost by Workflow" >> cost-report.md
          echo "" >> cost-report.md
          echo "| Workflow | Runs | Est. Minutes | Est. Cost |" >> cost-report.md
          echo "|----------|------|--------------|-----------|" >> cost-report.md

          # Pegar runs do mes anterior
          MONTH_START=$(date -d "last month" +%Y-%m-01 +%Y-%m-%dT%H:%M:%SZ)

          WORKFLOWS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/${{ github.repository }}/actions/workflows" | \
            jq -r '.workflows[] | "\(.id) \(.name)"')

          TOTAL_COST=0

          while IFS=' ' read -r wf_id wf_name; do
            RUNS=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
              "https://api.github.com/repos/${{ github.repository }}/actions/workflows/$wf_id/runs?created=>$MONTH_START&per_page=100")

            COUNT=$(echo "$RUNS" | jq '.total_count')

            if [ "$COUNT" -gt 0 ]; then
              # Estimar minutos baseado na duracao media
              AVG_DURATION=$(echo "$RUNS" | jq '[.workflow_runs[] | select(.conclusion)] | map(
                (if .updated_at and .run_started_at then
                  (.updated_at | sub("\\.[0-9]+Z$";"Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime) -
                  (.run_started_at | sub("\\.[0-9]+Z$";"Z") | strptime("%Y-%m-%dT%H:%M:%SZ") | mktime)
                else 0 end)
              ) | if length > 0 then add / length else 0 end')

              TOTAL_MINUTES=$(echo "$COUNT * $AVG_DURATION / 60" | bc)
              COST=$(echo "scale=2; $TOTAL_MINUTES * 0.008" | bc)
              TOTAL_COST=$(echo "scale=2; $TOTAL_COST + $COST" | bc)

              echo "| $wf_name | $COUNT | $TOTAL_MINUTES | \$$COST |" >> cost-report.md
            fi
          done <<< "$WORKFLOWS"

          echo "" >> cost-report.md
          echo "**Total Estimated Cost: \$$TOTAL_COST**" >> cost-report.md

          cat cost-report.md
```

### Cost per Branch

```yaml
name: Cost per Branch

on:
  schedule:
    - cron: '0 10 1 * *'

jobs:
  branch-cost:
    runs-on: ubuntu-latest
    steps:
      - name: Branch cost breakdown
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "## Cost by Branch" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Branch | Runs | Est. Cost |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|------|-----------|" >> "$GITHUB_STEP_SUMMARY"

          MONTH_START=$(date -d "last month" +%Y-%m-01 +%Y-%m-%dT%H:%M:%SZ)

          BRANCHES=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>$MONTH_START&per_page=100" | \
            jq -r '.workflow_runs[].head_branch' | sort -u)

          for BRANCH in $BRANCHES; do
            COUNT=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
              "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>$MONTH_START&branch=$BRANCH&per_page=100" | \
              jq '.total_count')

            COST=$(echo "scale=2; $COUNT * 5 * 0.008" | bc)
            echo "| $BRANCH | $COUNT | \$$COST |" >> "$GITHUB_STEP_SUMMARY"
          done
```

### Cost Alert Threshold

```yaml
name: Cost Alert

on:
  workflow_run:
    workflows: ["CI", "CD"]
    types: [completed]

jobs:
  cost-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check daily cost
        run: |
          TODAY=$(date +%Y-%m-%d)

          RUNS=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?created=>$TODAY&per_page=100")

          COUNT=$(echo "$RUNS" | jq '.total_count')
          ESTIMATED_MINUTES=$((COUNT * 5))
          ESTIMATED_COST=$(echo "scale=2; $ESTIMATED_MINUTES * 0.008" | bc)

          echo "Today's runs: $COUNT"
          echo "Estimated minutes: $ESTIMATED_MINUTES"
          echo "Estimated cost: \$$ESTIMATED_COST"

          # Alertar se custo diario > $50
          if (( $(echo "$ESTIMATED_COST > 50" | bc -l) )); then
            echo "::warning::Daily cost estimate exceeds \$50: \$$ESTIMATED_COST"
          fi
```

---

## 16.23 Alertas de Disponibilidade

### Uptime Monitor

```yaml
name: Uptime Monitor

on:
  schedule:
    - cron: '* * * * *'  # A cada minuto

jobs:
  uptime:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        url:
          - https://api.example.com/health
          - https://web.example.com/health
          - https://worker.example.com/health
    steps:
      - name: Check ${{ matrix.url }}
        run: |
          HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${{ matrix.url }}")

          if [ "$HTTP_CODE" != "200" ]; then
            echo "::error::Service unavailable: ${{ matrix.url }} (HTTP $HTTP_CODE)"
            exit 1
          fi

          echo "Service healthy: ${{ matrix.url }} (HTTP $HTTP_CODE)"
```

### SLA Calculator

```yaml
name: SLA Calculator

on:
  schedule:
    - cron: '0 0 1 * *'  # Primeiro dia do mes

jobs:
  sla:
    runs-on: ubuntu-latest
    steps:
      - name: Calculate monthly SLA
        run: |
          DAYS_IN_MONTH=$(date -d "last month" +%d)
          TOTAL_MINUTES=$((DAYS_IN_MONTH * 24 * 60))

          #假定 99.9% SLA
          SLA_TARGET=99.9
          ALLOWED_DOWNTIME=$(echo "scale=0; $TOTAL_MINUTES * (100 - $SLA_TARGET) / 100" | bc)

          echo "## Monthly SLA Report" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Days in month | $DAYS_IN_MONTH |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Total minutes | $TOTAL_MINUTES |" >> "$GITHUB_STEP_SUMMARY"
          echo "| SLA target | ${SLA_TARGET}% |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Allowed downtime | ${ALLOWED_DOWNTIME} minutes |" >> "$GITHUB_STEP_SUMMARY"
```

### Error Budget

```yaml
name: Error Budget

on:
  schedule:
    - cron: '0 8 * * *'  # Diario

jobs:
  error-budget:
    runs-on: ubuntu-latest
    steps:
      - name: Check error budget
        run: |
          #假定 99.9% SLA = 0.1% error budget = ~43 minutes/month
          MONTH_DAYS=$(date +%d)
          TOTAL_MINUTES=$((MONTH_DAYS * 24 * 60))
          ERROR_BUDGET_MINUTES=$(echo "scale=0; $TOTAL_MINUTES * 0.001" | bc)

          FAILURES=$(curl -s -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs?status=failure&created=>=$(date +%Y-%m-01)&per_page=100" | \
            jq '.total_count')

          echo "## Error Budget Status" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Month day | $MONTH_DAYS |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Error budget (minutes) | $ERROR_BUDGET_MINUTES |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Failures this month | $FAILURES |" >> "$GITHUB_STEP_SUMMARY"
```

---

## 16.24 Monitoring com Sentry

### Sentry Release Tracking

```yaml
name: Sentry Release

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create Sentry release
        uses: getsentry/action-release@v1
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: my-org
          SENTRY_PROJECT: my-project
        with:
          environment: production
          version: ${{ github.sha }}
          deployArgc: true
```

### Sentry Alert on Failure

```yaml
name: Sentry Alert

on:
  workflow_run:
    workflows: ["Deploy"]
    types: [completed]

jobs:
  alert:
    runs-on: ubuntu-latest
    if: failure()
    steps:
      - name: Notify Sentry
        run: |
          curl -s -X POST \
            -H "Authorization: Bearer ${{ secrets.SENTRY_AUTH_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d '{
              "message": "Deploy failed",
              "level": "error",
              "platform": "javascript"
            }' \
            "https://sentry.io/api/0/organizations/my-org/events/"
```

---

## 16.25 Monitoramento de Logs Centralizado

### Ship Logs to External Service

```yaml
name: Log Shipping

on:
  workflow_run:
    types: [completed]

jobs:
  ship-logs:
    runs-on: ubuntu-latest
    steps:
      - name: Download logs
        run: |
          curl -L -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
            "https://api.github.com/repos/${{ github.repository }}/actions/runs/${{ github.run_id }}/logs" \
            -o logs.zip
          unzip logs.zip

      - name: Ship to Elasticsearch
        run: |
          for log_file in *.txt; do
            curl -s -X POST \
              -H "Content-Type: application/json" \
              -d "{\"workflow\": \"${{ github.event.workflow_run.name }}\", \"log\": \"$(cat $log_file | head -100)\"}" \
              "http://elasticsearch:9200/github-actions/_doc"
          done
```

---

## 16.26 Dashboard de Qualidade

### Code Quality Metrics

```yaml
name: Quality Dashboard

on:
  schedule:
    - cron: '0 9 * * 1'

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Quality metrics
        run: |
          echo "## Code Quality Dashboard" >> "$GITHUB_STEP_SUMMARY"
          echo "" >> "$GITHUB_STEP_SUMMARY"
          echo "| Metric | Value | Trend |" >> "$GITHUB_STEP_SUMMARY"
          echo "|--------|-------|-------|" >> "$GITHUB_STEP_SUMMARY"
          echo "| Test coverage | 85% | stable |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Lint errors | 0 | improved |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Type errors | 2 | regressed |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Security vulns | 0 | stable |" >> "$GITHUB_STEP_SUMMARY"
          echo "| Bundle size | 125KB | improved |" >> "$GITHUB_STEP_SUMMARY"
```

---

## 16.27 Referencias

1. https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/understanding-the-billing-for-github-actions
2. https://github.com/slackapi/slack-github-action
3. https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/viewing-workflow-run-history
4. https://docs.github.com/en/rest/actions/workflows
5. https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-the-health-of-your-self-hosted-runners
6. https://github.com/Ilshidur/action-discord
7. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency
8. https://docs.github.com/en/actions/learn-github-actions/contexts
9. https://docs.github.com/en/actions/learn-github-actions/expressions
10. https://github.com/dawidd6/action-send-mail
11. https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows
12. https://github.com/actions/github-script
---

*[Capítulo anterior: 15 — Debugging](15-debugging.md)*
*[Próximo capítulo: 17 — Boas Praticas](17-boas-praticas.md)*
