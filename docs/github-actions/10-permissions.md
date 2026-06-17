---
layout: default
title: "10-permissions"
---

# Capitulo 10 -- Permissions e Least-Privilege

> *"O minimo necessario e o maximo seguro."*

---

## Objetivos de Aprendizado

1. Configurar permissions por workflow e job
2. Usar least-privilege para GITHUB_TOKEN
3. Implementar conditional permissions
4. Auditar permissoes atuais
5. Entender security best practices
6. Implementar scripts de auditoria
7. Configurar permissoes para OIDC
8. Gerenciar permissoes em organization-level
9. Implementar permissions para GitHub Apps
10. Configurar branch protection com permissions
11. Entender a hierarquia completa de scopes
12. Implementar audit logs automatizados
13. Configurar permissao para reusable workflows
14. Gerenciar permissoes cross-repository
15. Implementar permission drift detection

---

## 10.1 Default Permissions

Por padrao, o GITHUB_TOKEN tem permissoes limitadas. Em repos novos (post-2023), as permissoes padrao sao:

| Scope | Default | Descricao |
|-------|---------|-----------|
| contents | read | Leitura do repositorio |
| metadata | read | Metadados do repositorio |
| packages | none | Sem acesso a pacotes |
| actions | none | Sem acesso a workflows |
| issues | none | Sem acesso a issues |
| pull-requests | none | Sem acesso a PRs |
| deployments | none | Sem acesso a deployments |
| id-token | none | Sem acesso a OIDC |
| pages | none | Sem acesso a GitHub Pages |
| security-events | none | Sem acesso a code scanning |
| repository-projects | none | Sem acesso a projetos |
| discussions | none | Sem acesso a discussoes |
| checks | none | Sem acesso a checks |
| statuses | none | Sem acesso a commit statuses |
| environments | none | Sem acesso a environments |

### Repos Existentes (Pre-2023)

```yaml
# Repos existentes podem ter permissoes mais amplas:
# contents: write
# packages: write
# issues: write
# pull-requests: write
# deployments: write
# actions: write
# ... (todas as permissoes de escrita)

# Recomendacao: Alterar para read-only em Settings > Actions > General
```

### Verificar Permissoes Atuais

```yaml
name: Verificar Permissoes

on:
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Mostrar permissoes
        run: |
          echo "=== Permissoes do GITHUB_TOKEN ==="
          echo "Contents: ${{ permissions.contents }}"
          echo "Actions: ${{ permissions.actions }}"
          echo "Issues: ${{ permissions.issues }}"
          echo "Pull-requests: ${{ permissions.pull-requests }}"
          echo "Packages: ${{ permissions.packages }}"
          echo "Deployments: ${{ permissions.deployments }}"
          echo "Id-token: ${{ permissions.id-token }}"
          echo "Pages: ${{ permissions.pages }}"
          echo "Security-events: ${{ permissions.security-events }}"
          echo "Metadata: ${{ permissions.metadata }}"
```

### Alterar Permissoes Padrao

```yaml
# Em Settings > Actions > General > Workflow permissions
# Opcoes:
# 1. Read and write permissions (MENOS SEGURO)
# 2. Read repository contents and packages permissions (RECOMENDADO)

# Recomendacao: SEMPRE usar opcao 2 (read-only)
# E configurar permissoes explicitamente em cada workflow
```

### Impacto das Permissoes Padrao

```yaml
# Com read-only (recomendado):
# - Workflows precisam declarar permissoes explicitamente
# - Menor superficie de ataque
# - Mais previsivel

# Com read-write (nao recomendado):
# - Workflows herdam permissoes amplas
# - Maior risco de uso indevido
# - Mais dificil de auditar
```

### Diferencas entre Repos Novos e Antigos

| Caracteristica | Repos Novo (Post-2023) | Repos Antigo (Pre-2023) |
|----------------|------------------------|-------------------------|
| Default contents | read | write |
| Default actions | none | write |
| Default issues | none | write |
| Default packages | none | write |
| Seguranca | Mais seguro | Menos seguro |
| Necessidade de config | Opcional | Recomendado |

### Configuracao Organizacional

```yaml
# Settings > Actions > General > Organization permissions
# Opcoes para a organizacao inteira:
#
# 1. Allow all actions and reusable workflows
# 2. Allow select actions and reusable workflows
# 3. Disable actions
#
# Recomendacao: Usar opcao 2 para controlar quais actions sao permitidas
```

### Estrategia de Migracao de Permissoes

```yaml
# Passo 1: Auditar workflows existentes
name: Audit Permissions

on:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - name: Listar todos os workflows
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Listando workflows ==="
          gh api repos/${{ github.repository }}/actions/workflows \
            --jq '.workflows[] | "\(.name) - \(.path) - \(.state)"'
      
      - name: Analisar permissoes de cada workflow
        run: |
          echo "=== Analise de permissoes ==="
          for file in .github/workflows/*.yml; do
            echo "Arquivo: $file"
            if grep -q "permissions:" "$file"; then
              echo "  Tem bloco permissions"
            else
              echo "  SEM bloco permissions - HERDA DEFAULT"
            fi
          done

# Passo 2: Adicionar permissions: read em todos os workflows
# Passo 3: Adicionar permissions especificas nos jobs que precisam de write
# Passo 4: Alterar default para read-only no repo settings
```

---

## 10.2 Permissions Block

O bloco `permissions` define as permissoes do GITHUB_TOKEN para o workflow ou job especifico.

### Workflow Level

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Herda permissoes do workflow"
      # contents: read, issues: write, pull-requests: write
```

### Job Level

```yaml
permissions:
  contents: read  # Permissao padrao do workflow

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read  # Sobrescreve para read-only
    steps:
      - run: echo "Apenas leitura"

  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pages: write
      id-token: write
    steps:
      - run: echo "Pode escrever"
```

### Hierarquia de Permissions

```yaml
# 1. Workflow-level: define permissoes base
# 2. Job-level: sobrescreve workflow-level
# 3. Step-level: NAO suportado (apenas workflow e job)

# Exemplo de hierarquia:
permissions:
  contents: read  # Workflow-level: read

jobs:
  build:
    permissions:
      contents: read  # Job-level: mantem read
    steps:
      - run: echo "contents: read"

  deploy:
    permissions:
      contents: write  # Job-level: sobrescreve para write
    steps:
      - run: echo "contents: write"
```

### Permissions com Variaveis

```yaml
# Permissions NAO aceitam variaveis
# ISSO NAO FUNCIONA:
# permissions:
#   contents: ${{ vars.DEFAULT_PERMISSION }}

# Solucao: Usar condicionais
jobs:
  test:
    permissions:
      contents: read
    steps:
      - run: echo "Sempre read"

  deploy:
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: write
    steps:
      - run: echo "Write apenas para main"
```

### Permissions Herdados

```yaml
# Quando um job nao declara permissions, ele herda do workflow
# Se o workflow nao declara permissions, usa as permissoes padrao

# Exemplo:
# Workflow: permissions: contents: read
# Job 1: (sem permissions) -> herda contents: read
# Job 2: permissions: contents: write -> sobrescreve para write
# Job 3: permissions: issues: write -> herda contents: read + issues: write
```

### Permissions para Reusable Workflows

```yaml
# Reusable workflow herda permissoes do caller
# Mas pode definir permissoes minimas internamente

# Reusable workflow (.github/workflows/reusable-deploy.yml)
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
      - run: echo "Deploying to ${{ inputs.environment }}"

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

### Permissions com GITHUB_TOKEN Explicito

```yaml
# O GITHUB_TOKEN e automaticamente disponibilizado
# Nao e necessario passar como secret

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - name: Usar GITHUB_TOKEN
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/releases \
            --method POST \
            --field tag_name="v1.0.0" \
            --field name="Release v1.0.0"
```

---

## 10.3 All Scopes Explicados

### contents

Controle acesso ao repositorio, releases e branches.

```yaml
permissions:
  contents: read  # Leitura de codigo, branches, tags
  # contents: write  # Criar branches, tags, releases, push code
  # contents: admin  # Gerenciar branch protection, visibility

jobs:
  read-only:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: echo "Apenas leitura do codigo"

  write:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - run: git push origin main

  admin:
    runs-on: ubuntu-latest
    permissions:
      contents: admin
    steps:
      - uses: actions/checkout@v4
      - run: |
          # Gerenciar branch protection
          echo "Gerenciando branch protection"
```

### issues

Controle acesso a issues e comentarios.

```yaml
permissions:
  issues: read  # Ler issues
  # issues: write  # Criar, atualizar, comentar em issues
  # issues: admin  # Gerenciar labels, milestones

jobs:
  create-issue:
    runs-on: ubuntu-latest
    permissions:
      issues: write
    steps:
      - name: Criar issue
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh issue create \
            --title "Bug report" \
            --body "Descricao do bug" \
            --label "bug"

  manage-milestones:
    runs-on: ubuntu-latest
    permissions:
      issues: admin
    steps:
      - name: Gerenciar milestone
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/milestones \
            --method POST \
            --field title="v2.0" \
            --field due_on="2024-12-31T00:00:00Z"
```

### pull-requests

Controle acesso a pull requests e reviews.

```yaml
permissions:
  pull-requests: read  # Ler PRs
  # pull-requests: write  # Criar, atualizar, comentar em PRs
  # pull-requests: admin  # Gerenciar reviews

jobs:
  comment-pr:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - name: Comentar em PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr comment ${{ github.event.pull_request.number }} \
            --body "Build concluido com sucesso!"

  auto-approve:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: admin
    steps:
      - name: Auto-approve PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr review ${{ github.event.pull_request.number }} --approve
```

### packages

Controle acesso a GitHub Packages.

```yaml
permissions:
  packages: read  # Ler pacotes
  # packages: write  # Criar, atualizar pacotes
  # packages: admin  # Gerenciar pacotes

jobs:
  publish:
    runs-on: ubuntu-latest
    permissions:
      packages: write
    steps:
      - name: Publicar pacote
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          npm publish

  delete-package:
    runs-on: ubuntu-latest
    permissions:
      packages: admin
    steps:
      - name: Deletar pacote
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/packages/maven/my-package/versions/1.0.0 \
            --method DELETE
```

### actions

Controle acesso a workflows e runs.

```yaml
permissions:
  actions: read  # Ler workflows e runs
  # actions: write  # Criar, cancelar workflows
  # actions: admin  # Gerenciar workflows

jobs:
  trigger-workflow:
    runs-on: ubuntu-latest
    permissions:
      actions: write
    steps:
      - name: Disparar workflow
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh workflow run deploy.yml -f environment=production

  cancel-run:
    runs-on: ubuntu-latest
    permissions:
      actions: write
    steps:
      - name: Cancelar run
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh run cancel ${{ github.run_id }}
```

### deployments

Controle acesso a deployments.

```yaml
permissions:
  deployments: read  # Ler deployments
  # deployments: write  # Criar, atualizar deployments
  # deployments: admin  # Gerenciar deployments

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      deployments: write
    steps:
      - name: Criar deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

### id-token

Controle acesso a OIDC token.

```yaml
permissions:
  id-token: write  # Necessario para OIDC
  # id-token: read  # Ler OIDC token
  # id-token: none  # Sem acesso

jobs:
  oidc:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Configurar AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/GitHubActions
          aws-region: us-east-1
```

### pages

Controle acesso a GitHub Pages.

```yaml
permissions:
  pages: read  # Ler Pages
  # pages: write  # Criar, atualizar Pages
  # pages: admin  # Gerenciar Pages

jobs:
  deploy-pages:
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    steps:
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
      - uses: actions/deploy-pages@v4
```

### security-events

Controle acesso a code scanning e secret scanning.

```yaml
permissions:
  security-events: read  # Ler security events
  # security-events: write  # Criar, atualizar security events
  # security-events: admin  # Gerenciar security events

jobs:
  codeql:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - uses: github/codeql-action/analyze@v3
```

### repository-projects

Controle acesso a GitHub Projects.

```yaml
permissions:
  repository-projects: read  # Ler projetos
  # repository-projects: write  # Criar, atualizar projetos
  # repository-projects: admin  # Gerenciar projetos

jobs:
  update-project:
    runs-on: ubuntu-latest
    permissions:
      repository-projects: write
    steps:
      - name: Atualizar projeto
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Projeto atualizado"
```

### discussions

Controle acesso a GitHub Discussions.

```yaml
permissions:
  discussions: read  # Ler discussoes
  # discussions: write  # Criar, atualizar discussoes
  # discussions: admin  # Gerenciar discussoes

jobs:
  create-discussion:
    runs-on: ubuntu-latest
    permissions:
      discussions: write
    steps:
      - name: Criar discussao
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Discussao criada"
```

### checks

Controle acesso a GitHub Checks.

```yaml
permissions:
  checks: read  # Ler checks
  # checks: write  # Criar, atualizar checks
  # checks: admin  # Gerenciar checks

jobs:
  create-check:
    runs-on: ubuntu-latest
    permissions:
      checks: write
    steps:
      - name: Criar check
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Check criado"
```

### statuses

Controle acesso a commit statuses.

```yaml
permissions:
  statuses: read  # Ler statuses
  # statuses: write  # Criar, atualizar statuses
  # statuses: admin  # Gerenciar statuses

jobs:
  create-status:
    runs-on: ubuntu-latest
    permissions:
      statuses: write
    steps:
      - name: Criar status
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          curl -X POST \
            -H "Authorization: token $GH_TOKEN" \
            https://api.github.com/repos/${{ github.repository }}/statuses/${{ github.sha }} \
            -d '{"state": "success", "description": "Build passed"}'
```

### metadata

Controle acesso a metadados do repositorio.

```yaml
permissions:
  metadata: read  # Ler metadados (sempre disponivel)
  # metadata: write  # Gerenciar metadados

jobs:
  read-metadata:
    runs-on: ubuntu-latest
    steps:
      - name: Ler metadados
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }} | jq '.description'
```

### environments

Controle acesso a environments.

```yaml
permissions:
  environments: read  # Ler environments
  # environments: write  # Criar, atualizar environments
  # environments: admin  # Gerenciar environments

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      environments: write
    environment: production
    steps:
      - name: Deploy
        run: echo "Deploying"
```

### Tabela Completa de Scopes

| Scope | Read | Write | Admin | Descricao |
|-------|------|-------|-------|-----------|
| contents | Ler codigo, branches, tags | Criar branches, tags, releases | Gerenciar branch protection | Acesso ao repositorio |
| metadata | Ler metadados | Gerenciar metadados | N/A | Metadados do repo |
| actions | Ler workflows e runs | Criar, cancelar workflows | Gerenciar workflows | Acesso a GitHub Actions |
| issues | Ler issues | Criar, atualizar, comentar | Gerenciar labels, milestones | Acesso a issues |
| pull-requests | Ler PRs | Criar, atualizar, comentar | Gerenciar reviews | Acesso a PRs |
| packages | Ler pacotes | Criar, atualizar pacotes | Gerenciar pacotes | Acesso a GitHub Packages |
| deployments | Ler deployments | Criar, atualizar deployments | Gerenciar deployments | Acesso a deployments |
| id-token | Ler OIDC token | Gerar OIDC token | N/A | Acesso a OIDC |
| pages | Ler Pages | Criar, atualizar Pages | Gerenciar Pages | Acesso a GitHub Pages |
| security-events | Ler security events | Criar security events | Gerenciar security events | Acesso a code scanning |
| repository-projects | Ler projetos | Criar, atualizar projetos | Gerenciar projetos | Acesso a GitHub Projects |
| discussions | Ler discussoes | Criar, atualizar discussoes | Gerenciar discussoes | Acesso a discussions |
| checks | Ler checks | Criar, atualizar checks | Gerenciar checks | Acesso a GitHub Checks |
| statuses | Ler statuses | Criar, atualizar statuses | Gerenciar statuses | Acesso a commit statuses |
| environments | Ler environments | Criar, atualizar environments | Gerenciar environments | Acesso a environments |

---

## 10.4 OIDC Permissions

OIDC requer permissoes especificas para funcionar corretamente.

### Configuracao Basica OIDC

```yaml
permissions:
  id-token: write  # OBRIGATORIO para OIDC
  contents: read   # Necessario para checkout

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configurar AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789:role/GitHubActions
          aws-region: us-east-1
```

### OIDC com Multi-Cloud

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy-aws:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

  deploy-gcp:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF }}
          service_account: ${{ secrets.GCP_SA }}

  deploy-azure:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

### OIDC com AWS STS Assume Role

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Assume Role com External ID
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
          role-session-name: GitHubActions-${{ github.run_id }}
      
      - name: Verificar credenciais
        run: |
          aws sts get-caller-identity
      
      - name: Deploy com S3
        run: |
          aws s3 sync dist/ s3://my-bucket/
```

### OIDC com GCP Workload Identity Federation

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Autenticar com GCP
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF }}
          service_account: ${{ secrets.GCP_SA }}
          token_format: 'access_token'
      
      - name: Deploy com gcloud
        run: |
          gcloud run deploy my-service \
            --image gcr.io/my-project/my-image:${{ github.sha }} \
            --region us-central1
```

### OIDC com Azure

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Login com OIDC
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Deploy Azure Web App
        uses: azure/webapps-deploy@v3
        with:
          app-name: 'my-webapp'
          package: './dist'
```

### OIDC com Terraform Cloud

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.6.0'
      
      - name: Terraform Init
        run: terraform init
        env:
          TF_CLOUD_ORGANIZATION: ${{ vars.TFC_ORG }}
      
      - name: Terraform Plan
        run: terraform plan
        env:
          TF_CLOUD_ORGANIZATION: ${{ vars.TFC_ORG }}
```

### OIDC com HashiCorp Vault

```yaml
permissions:
  id-token: write
  contents: read

jobs:
  vault-secrets:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Login no Vault com OIDC
        uses: hashicorp/vault-action@v2
        with:
          url: https://vault.company.com
          method: jwt
          role: github-actions
          jwtGithubAudience: https://vault.company.com
        env:
          VAULT_ROLE: github-actions
      
      - name: Usar secrets do Vault
        uses: hashicorp/vault-action@v2
        with:
          url: https://vault.company.com
          secrets: |
            secret/data/myapp config | CONFIG ;
            secret/data/myapp api_key | API_KEY
        env:
          VAULT_ROLE: github-actions
      
      - name: Deploy
        env:
          CONFIG: ${{ env.CONFIG }}
          API_KEY: ${{ env.API_KEY }}
        run: |
          echo "Deploying with Vault secrets"
```

---

## 10.5 Conditional Permissions

Permissions podem ser condicionais baseado no tipo de evento ou outras condicoes.

### Permissions por Evento

```yaml
jobs:
  on-push:
    if: github.event_name == 'push'
    permissions:
      contents: write
    steps:
      - run: echo "Push event - pode escrever"

  on-pr:
    if: github.event_name == 'pull_request'
    permissions:
      contents: read
      pull-requests: write
    steps:
      - run: echo "PR event - leitura + comentarios"

  on-schedule:
    if: github.event_name == 'schedule'
    permissions:
      contents: read
    steps:
      - run: echo "Schedule event - apenas leitura"
```

### Permissions por Branch

```yaml
jobs:
  on-main:
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: write
      deployments: write
    steps:
      - run: echo "Main branch - deploy completo"

  on-develop:
    if: github.ref == 'refs/heads/develop'
    permissions:
      contents: read
    steps:
      - run: echo "Develop branch - apenas leitura"

  on-feature:
    if: startsWith(github.ref, 'refs/heads/feature/')
    permissions:
      contents: read
      pull-requests: write
    steps:
      - run: echo "Feature branch - leitura + PR"
```

### Permissions por Actor

```yaml
jobs:
  bot:
    if: github.actor == 'dependabot[bot]'
    permissions:
      contents: write
      pull-requests: write
    steps:
      - run: echo "Dependabot - pode escrever"

  maintainer:
    if: contains(github.event.pull_request.labels.*.name, 'priority')
    permissions:
      contents: write
      pull-requests: write
    steps:
      - run: echo "Prioridade alta - acesso total"

  regular:
    if: "!contains(github.event.pull_request.labels.*.name, 'priority')"
    permissions:
      contents: read
      pull-requests: read
    steps:
      - run: echo "Regular - acesso limitado"
```

### Permissions com Multiplas Condicoes

```yaml
jobs:
  complex:
    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main' &&
      github.actor != 'dependabot[bot]'
    permissions:
      contents: write
      deployments: write
      packages: write
    steps:
      - run: echo "Condicoes complexas atendidas"
```

### Permissions para Dependabot

```yaml
name: Auto-Merge Dependabot

on:
  pull_request:

jobs:
  auto-merge:
    runs-on: ubuntu-latest
    if: github.actor == 'dependabot[bot]'
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Verificar tipo de atualizacao
        id: metadata
        uses: dependabot/fetch-metadata@v2
        with:
          github-token: "${{ secrets.GITHUB_TOKEN }}"

      - name: Auto-merge para patches
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Auto-merge para minors
        if: steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Permissions para Release Automation

```yaml
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Criar Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create ${{ github.ref_name }} \
            --title "Release ${{ github.ref_name }}" \
            --generate-notes
      
      - name: Upload artifacts
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release upload ${{ github.ref_name }} \
            dist/*
```

### Permissions para Code Scanning

```yaml
name: CodeQL

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
          queries: security-and-quality
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:javascript"
```

---

## 10.6 Security Best Practices

### Regras de Ouro

```yaml
# REGRA 1: SEMPRE defina permissions explicitamente
permissions:
  contents: read

# REGRA 2: Use read por default, write apenas quando necessario
permissions:
  contents: read  # Base read

jobs:
  build:
    permissions:
      contents: read  # Apenas leitura

  deploy:
    permissions:
      contents: write  # Escrita necessaria

# REGRA 3: Nao use `permissions: write-all`
# NUNCA faca isso:
# permissions: write-all

# REGRA 4: Prefira OIDC sobre secrets para cloud providers
permissions:
  id-token: write
  contents: read

# REGRA 5: Audite regularmente as permissoes
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Auditar permissoes
        run: |
          echo "Permissoes atuais:"
          echo "contents: ${{ permissions.contents }}"
          echo "actions: ${{ permissions.actions }}"
          echo "issues: ${{ permissions.issues }}"
```

### Exemplo Seguro

```yaml
permissions:
  contents: read  # So leitura do codigo

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  lint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm run lint

  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm run build

  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
      - uses: actions/deploy-pages@v4
```

### Anti-Patterns

```yaml
# ANTI-PATTERN 1: Permissoes muito amplas
permissions:
  contents: write  # Necessario apenas para deploy
  issues: write    # Nao necessario
  packages: write  # Nao necessario

# SOLUCAO: Permissoes minimas
permissions:
  contents: read

jobs:
  test:
    permissions:
      contents: read

  deploy:
    permissions:
      contents: write
      pages: write
      id-token: write

# ANTI-PATTERN 2: Permissoes em todos os jobs
jobs:
  job1:
    permissions:
      contents: write
  job2:
    permissions:
      contents: write
  job3:
    permissions:
      contents: write

# SOLUCAO: Permissoes no workflow, override nos jobs
permissions:
  contents: read

jobs:
  job1:
    permissions:
      contents: read

  job2:
    permissions:
      contents: read

  job3:
    permissions:
      contents: write  # Apenas este precisa de write
```

### Checklist de Seguranca

| Item | Status | Descricao |
|------|--------|-----------|
| Default permissions read-only | OK/FAIL | Configurado em Settings |
| Bloco permissions em todos os workflows | OK/FAIL | Cada workflow tem permissions explicito |
| OIDC em vez de long-lived secrets | OK/FAIL | Cloud deploy usa id-token |
| least-privilege em cada job | OK/FAIL | Cada job so tem o que precisa |
| Sem write-all | OK/FAIL | Nenhum workflow usa write-all |
| Auditoria periodica | OK/FAIL | Audit workflow configurado |
| Branch protection | OK/FAIL | Requer reviews e status checks |
| CODEOWNERS | OK/DIRTY | Arquivos criticos tem owners |

### Padrao de Workflow Seguro

```yaml
# Template de workflow seguro
name: Secure Template

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - run: npm ci
      - uses: github/codeql-action/analyze@v3

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    permissions:
      contents: write
      id-token: write
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - run: aws s3 sync dist/ s3://my-bucket/
```

---

## 10.7 Audit Scripts

### Script de Auditoria de Permissoes

```yaml
name: Permission Audit

on:
  workflow_dispatch:
    inputs:
      report_format:
        description: 'Formato do relatorio'
        required: true
        type: choice
        options:
          - text
          - json
          - sarif

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - name: Listar workflows
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Auditoria de Permissoes ==="
          echo "Repository: ${{ github.repository }}"
          echo "Data: $(date)"
          echo ""
          
          echo "Workflows:"
          gh api repos/${{ github.repository }}/actions/workflows \
            --jq '.workflows[] | "\(.name) - \(.path)"'

      - name: Analisar permissoes
        run: |
          echo "=== Permissoes do Token Atual ==="
          echo "Contents: ${{ permissions.contents }}"
          echo "Actions: ${{ permissions.actions }}"
          echo "Issues: ${{ permissions.issues }}"
          echo "Pull-requests: ${{ permissions.pull-requests }}"
          echo "Packages: ${{ permissions.packages }}"
          echo "Deployments: ${{ permissions.deployments }}"
          echo "Id-token: ${{ permissions.id-token }}"
          echo "Pages: ${{ permissions.pages }}"
          echo "Security-events: ${{ permissions.security-events }}"

      - name: Verificar permissoes perigosas
        run: |
          echo "=== Verificacao de Seguranca ==="
          
          if [ "${{ permissions.contents }}" = "write" ]; then
            echo "AVISO: contents: write configurado"
          fi
          
          if [ "${{ permissions.actions }}" = "write" ]; then
            echo "AVISO: actions: write configurado"
          fi
          
          if [ "${{ permissions.packages }}" = "write" ]; then
            echo "AVISO: packages: write configurado"
          fi
```

### Script de Auditoria de Secrets

```yaml
name: Secret Audit

on:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - name: Listar repository secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Repository Secrets ==="
          gh secret list --json name,updatedAt,visibility
          
          echo ""
          echo "=== Environment Secrets ==="
          gh secret list --env production --json name,updatedAt
          gh secret list --env staging --json name,updatedAt

      - name: Verificar idade dos secrets
        run: |
          echo "=== Verificacao de Idade ==="
          echo "Verificando secrets nao atualizados nos ultimos 90 dias..."
```

### Script de Auditoria Completa

```yaml
name: Full Security Audit

on:
  workflow_dispatch:
    inputs:
      scope:
        description: 'Escopo da auditoria'
        required: true
        type: choice
        options:
          - repository
          - organization
          - full

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
      security-events: read
    steps:
      - name: Auditoria de repository
        if: inputs.scope == 'repository' || inputs.scope == 'full'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Auditoria de Repository ==="
          
          echo "Branch Protection:"
          gh api repos/${{ github.repository }}/branches/main/protection \
            --jq '.required_pull_request_reviews.required_approving_review_count'
          
          echo "Dependabot Alerts:"
          gh api repos/${{ github.repository }}/vulnerability-alerts \
            --jq '.enabled'

      - name: Auditoria de organization
        if: inputs.scope == 'organization' || inputs.scope == 'full'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Auditoria de Organization ==="
          
          echo "Organization Secrets:"
          gh secret list --org ${{ github.repository_owner }} --json name,visibility
          
          echo "Organization Members:"
          gh api orgs/${{ github.repository_owner }}/members \
            --jq '.[].login' | head -20

      - name: Gerar relatorio
        run: |
          echo "=== Relatorio de Auditoria ==="
          echo "Repository: ${{ github.repository }}"
          echo "Data: $(date)"
          echo "Escopo: ${{ inputs.scope }}"
          echo "Status: Concluido"
```

### Auditoria de Workflow Permissions

```yaml
name: Workflow Permission Analysis

on:
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@v4

      - name: Analisar permissoes de cada workflow
        run: |
          echo "=== Analise de Permissions ==="
          echo ""
          
          for file in .github/workflows/*.yml; do
            echo "Arquivo: $file"
            echo "---"
            
            # Verificar se tem bloco permissions
            if grep -q "^permissions:" "$file"; then
              echo "  [OK] Tem bloco permissions"
              
              # Extrair permissoes
              sed -n '/^permissions:/,/^[a-z]/p' "$file" | head -10
            else
              echo "  [WARN] SEM bloco permissions - usa default"
            fi
            
            # Verificar per job
            echo "  Jobs:"
            grep -n "permissions:" "$file" | grep -v "^.*:.*#"
            
            echo ""
          done

      - name: Verificar write-all
        run: |
          echo "=== Verificacao de write-all ==="
          
          if grep -r "write-all" .github/workflows/; then
            echo "ERRO: write-all encontrado!"
            exit 1
          else
            echo "OK: Nenhum write-all encontrado"
          fi
```

### Auditoria de OIDC Usage

```yaml
name: OIDC Audit

on:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar uso de OIDC
        run: |
          echo "=== Auditoria de OIDC ==="
          echo ""
          
          echo "Workflows com id-token: write:"
          grep -rl "id-token: write" .github/workflows/ || echo "Nenhum"
          
          echo ""
          echo "Workflows com AWS credentials:"
          grep -rl "aws-actions/configure-aws-credentials" .github/workflows/ || echo "Nenhum"
          
          echo ""
          echo "Workflows com long-lived secrets:"
          grep -rl "AWS_ACCESS_KEY_ID" .github/workflows/ || echo "Nenhum"
          grep -rl "AWS_SECRET_ACCESS_KEY" .github/workflows/ || echo "Nenhum"

      - name: Recomendacoes
        run: |
          echo "=== Recomendacoes ==="
          echo ""
          echo "1. Use OIDC em vez de long-lived secrets para cloud providers"
          echo "2. Configure least-privilege para cada role"
          echo "3. Use External ID para prevenir confused deputy"
          echo 4. Rotate secrets regularmente"
          echo "5. Audite acessos periodicamente"
```

---

## 10.8 Organization-Level Permissions

### Configuracao de Organization

```yaml
# Settings > Actions > General > Organization permissions
# 
# 1. Allow all actions and reusable workflows
#    - Todos os repos podem usar todas as actions
#    - MENOS SEGURO
#
# 2. Allow select actions and reusable workflows
#    - Apenas actions aprovadas podem ser usadas
#    - RECOMENDADO
#
# 3. Disable actions
#    - Nenhuma action pode ser usada
#    - Mais restritivo

# Recomendacao: Usar opcao 2 com allow list
```

### Allow List de Actions

```yaml
# Configurar allow list em Settings > Actions > General
# 
# Permitir:
# - actions/* (todas as actions oficiais do GitHub)
# - myorg/* (actions da organizacao)
# - verified-publishers/* (publishers verificados)
#
# Bloquear:
# - Todas as outras actions
# - Actions de terceiros nao verificadas
```

### Organization Secrets

```yaml
# Organization secrets sao compartilhados entre repos
# Configurar em Settings > Secrets > Actions

# Tipos de access:
# - All repositories (todos os repos)
# - Selected repositories (repos selecionados)
# - Private repositories (apenas repos privados)

# Exemplo de uso:
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Usar organization secret
        env:
          ORG_SECRET: ${{ secrets.ORG_SECRET }}
        run: |
          echo "Usando secret da organizacao"
```

### Organization Variables

```yaml
# Organization variables sao compartilhadas entre repos
# Configurar em Settings > Variables > Actions

# Tipos:
# - Environment variables (variaveis de ambiente)
# - Dependabot variables (variaveis do Dependabot)

# Exemplo de uso:
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Usar organization variable
        env:
          ORG_VAR: ${{ vars.ORG_VARIABLE }}
        run: |
          echo "Usando variavel da organizacao: $ORG_VAR"
```

### Restricao de Acesso por Repo

```yaml
# Configurar permissao por repo
# Settings > Actions > General > Access

# Opcoes:
# - All repositories in this organization
# - Selected repositories only
# - Only this repository

# Recomendacao: Usar "Selected repositories" para workflows criticos
```

---

## 10.9 GitHub Apps Permissions

### Criar GitHub App com Permissoes Minimas

```yaml
# GitHub Apps permitem autenticacao mais granular que PATs
# Configurar em Settings > Developer settings > GitHub Apps

# Permissoes minimais para CI/CD:
# Repository permissions:
#   - Contents: Read
#   - Deployments: Read and write
#   - Issues: Read and write
#   - Pull requests: Read and write
#   - Statuses: Read and write
#
# Organization permissions:
#   - Members: Read
#
# Account permissions:
#   - Email addresses: Read
```

### Uso de GitHub App Token

```yaml
name: Use GitHub App

on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
    steps:
      - name: Generate App Token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ vars.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}
      
      - name: Usar token do App
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

### GitHub App vs PAT vs GITHUB_TOKEN

| Caracteristica | GITHUB_TOKEN | PAT | GitHub App |
|----------------|--------------|-----|------------|
| Escopo | Repository | User/Repo | Repository/Org |
| Expiracao | 1 hora | Nunca | 1 hora |
| Auditavel | Sim | Parcial | Sim |
| Multi-repo | Nao | Sim | Sim |
| Permissoes | Limitadas | Amplas | Granulares |
| Seguranca | Alta | Media | Alta |

### Configuracao de GitHub App para CI/CD

```yaml
# Passo 1: Criar GitHub App
# Settings > Developer settings > GitHub Apps > New GitHub App
#
# Passo 2: Configurar permissoes
# Repository permissions:
#   - Contents: Read
#   - Deployments: Read and write
#   - Packages: Read and write
#
# Passo 3: Instalar no repositorio
# Settings > Installations > Install
#
# Passo 4: Configurar secrets
# APP_ID: ID do App
# APP_PRIVATE_KEY: Chave privada do App
#
# Passo 5: Usar no workflow
```

---

## 10.10 Branch Protection com Permissions

### Configuracao de Branch Protection

```yaml
# Configurado via API
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["test", "lint", "security-scan"]
    },
    "required_pull_request_reviews": {
      "required_approving_review_count": 2,
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": true
    },
    "enforce_admins": true,
    "restrictions": null
  }'
```

### Branch Protection com CODEOWNERS

```
# .github/CODEOWNERS
# Codigo requer revisao do time especifico

# Frontend
/src/frontend/ @myorg/frontend-team

# Backend
/src/backend/ @myorg/backend-team

# Infrastructure
/terraform/ @myorg/devops-team
/.github/ @myorg/devops-team

# Security
/src/auth/ @myorg/security-team
```

### Branch Protection Rules

| Regra | Descricao | Recomendacao |
|-------|-----------|--------------|
| Required reviews | Numero de reviews necessarios | 2 reviewers |
| Dismiss stale reviews | Desabilitar reviews antigos | Sim |
| Require code owners | Requer review do owner | Sim |
| Require status checks | Status checks obrigatorios | test, lint, security |
| Require branches up to date | Branch deve estar atualizada | Sim |
| Require signed commits | Commits devem ser assinados | Sim |
| Require linear history | Historio linear | Sim |
| Include administrators | Administradores tambem seguem | Sim |
| Restrict force pushes | Bloquear force push | Sim |
| Restrict deletions | Bloquear delete | Sim |

### Configuracao Avancada de Branch Protection

```yaml
# Branch protection com required reviews e status checks
curl -X PUT \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/OWNER/REPO/branches/main/protection \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": [
        "test",
        "lint",
        "security-scan",
        "build"
      ]
    },
    "required_pull_request_reviews": {
      "required_approving_review_count": 2,
      "dismiss_stale_reviews": true,
      "require_code_owner_reviews": true,
      "dismissal_restrictions": {
        "users": ["admin-user"],
        "teams": ["admin-team"]
      }
    },
    "enforce_admins": true,
    "restrictions": {
      "users": [],
      "teams": ["core-team"],
      "apps": []
    },
    "required_linear_history": true,
    "allow_force_pushes": false,
    "allow_deletions": false,
    "block_creations": true,
    "required_conversation_resolution": true
  }'
```

---

## 10.11 Permission Drift Detection

### Detectar Mudancas de Permissoes

```yaml
name: Permission Drift Detection

on:
  schedule:
    - cron: '0 6 * * *'  # Diariamente

jobs:
  detect-drift:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Capturar estado atual
        run: |
          echo "=== Capturando estado de permissions ==="
          
          # Listar workflows e seus statuses
          gh api repos/${{ github.repository }}/actions/workflows \
            --jq '.workflows[] | {name: .name, path: .path, state: .state}' \
            > current-state.json
          
          echo "Estado capturado"
          cat current-state.json

      - name: Comparar com estado anterior
        run: |
          echo "=== Comparando com estado anterior ==="
          
          if [ -f previous-state.json ]; then
            diff previous-state.json current-state.json || echo "Mudancas detectadas!"
          else
            echo "Primeira execucao - salvando estado"
            cp current-state.json previous-state.json
          fi

      - name: Alertar sobre mudancas
        if: failure()
        run: |
          echo "=== ALERTA: Mudancas de permissao detectadas ==="
          echo "Verificar mudancas nos workflows"
```

### Monitorar Mudancas em Settings

```yaml
name: Monitor Settings Changes

on:
  repository_dispatch:
    types: [settings_change]

jobs:
  notify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Notificar sobre mudanca
        run: |
          echo "=== Configuracoes do repositorio alteradas ==="
          echo "Evento: ${{ github.event.action }}"
          echo "Actor: ${{ github.actor }}"
          echo "Data: $(date)"
```

---

## 10.12 Exemplo Completo

```yaml
name: Secure CI/CD

permissions:
  contents: read  # Default: read only

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  lint:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint

  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - run: npm ci
      - uses: github/codeql-action/analyze@v3

  build:
    needs: [test, lint, security-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
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
          name: build
          path: dist/

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - name: Deploy para Staging
        env:
          STAGING_URL: ${{ vars.STAGING_URL }}
        run: |
          echo "Deploying to staging..."

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    permissions:
      contents: write
      deployments: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - name: Deploy para Production
        run: |
          echo "Deploying to production..."
      - name: Criar Deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

---

## 10.13 Exercicios

1. Configure um workflow com permissions minimas (apenas read)
2. Implemente conditional permissions baseado no tipo de evento
3. Crie um audit script que liste permissoes de todos os workflows
4. Configure OIDC para AWS com permissions minimas
5. Compare permissoes entre workflow-level e job-level
6. Implemente permissions condicionais baseado em labels
7. Crie relatorio completo de auditoria de seguranca
8. Configure permissions para multi-cloud deploy
9. Implemente verificacao automatica de permissoes perigosas
10. Configure permissions para GitHub Apps tokens
11. Implemente permission drift detection
12. Configure organization-level permissions
13. Crie checklist de seguranca para permissions
14. Implemente auditoria de OIDC usage
15. Configure branch protection com permissions

---

## 10.14 Permission Patterns por Tipo de Projeto

### Projeto Frontend

```yaml
name: Frontend CI/CD

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage

  visual-tests:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:visual

  lighthouse:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - name: Lighthouse CI
        uses: treosh/lighthouse-ci-action@v10
        with:
          urls: |
            http://localhost:3000
          configPath: ./lighthouserc.json

  deploy-preview:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  deploy-production:
    needs: [test, visual-tests, lighthouse]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

### Projeto Backend API

```yaml
name: Backend API CI/CD

permissions:
  contents: read

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
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports:
          - 6379:6379
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
        run: npm test

  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: javascript
      - run: npm ci
      - uses: github/codeql-action/analyze@v3

  build:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - name: Deploy to staging
        run: |
          echo "Deploying to staging..."
          # Deploy to staging environment

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://api.myapp.com
    permissions:
      contents: read
      deployments: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # Deploy to production environment
```

### Projeto Infrastructure (Terraform)

```yaml
name: Infrastructure CI/CD

permissions:
  contents: read

jobs:
  plan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.6.0'
      - name: Terraform Init
        run: terraform init
      - name: Terraform Plan
        id: plan
        run: terraform plan -no-color
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const plan = `${{ steps.plan.outputs.stdout }}`;
            const body = `### Terraform Plan\n\`\`\`\n${plan}\n\`\`\``;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            })

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: '1.6.0'
      - name: Terraform Init
        run: terraform init
      - name: Terraform Apply
        run: terraform apply -auto-approve
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### Projeto Multi-Service

```yaml
name: Multi-Service CI/CD

permissions:
  contents: read

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      frontend: ${{ steps.filter.outputs.frontend }}
      backend: ${{ steps.filter.outputs.backend }}
      infra: ${{ steps.filter.outputs.infra }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v2
        id: filter
        with:
          filters: |
            frontend:
              - 'src/frontend/**'
            backend:
              - 'src/backend/**'
            infra:
              - 'terraform/**'

  test-frontend:
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: cd src/frontend && npm ci && npm test

  test-backend:
    needs: detect-changes
    if: needs.detect-changes.outputs.backend == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: cd src/backend && npm ci && npm test

  deploy-frontend:
    needs: [detect-changes, test-frontend]
    if: needs.detect-changes.outputs.frontend == 'true' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying frontend..."

  deploy-backend:
    needs: [detect-changes, test-backend]
    if: needs.detect-changes.outputs.backend == 'true' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      deployments: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - run: echo "Deploying backend..."
```

---

## 10.15 Troubleshooting de Permissions

### Erros Comuns e Solucoes

| Erro | Causa | Solucao |
|------|-------|---------|
| Resource not accessible by integration | Permissao insuficiente | Adicionar scope necessario no permissions |
| Not found | Acesso negado | Verificar permissions do workflow |
| Bad credentials | Token invalido | Verificar se GITHUB_TOKEN esta disponivel |
| Forbidden | Permissao negada | Adicionar permissao necessaria |
| Validation Failed | Parametro invalido | Verificar formato do request |

### Debug de Permissions

```yaml
name: Debug Permissions

on:
  workflow_dispatch:

jobs:
  debug:
    runs-on: ubuntu-latest
    steps:
      - name: Mostrar todas as permissoes
        run: |
          echo "=== Debug de Permissoes ==="
          echo ""
          echo "GITHUB_TOKEN permissions:"
          echo "  contents: ${{ permissions.contents }}"
          echo "  actions: ${{ permissions.actions }}"
          echo "  issues: ${{ permissions.issues }}"
          echo "  pull-requests: ${{ permissions.pull-requests }}"
          echo "  packages: ${{ permissions.packages }}"
          echo "  deployments: ${{ permissions.deployments }}"
          echo "  id-token: ${{ permissions.id-token }}"
          echo "  pages: ${{ permissions.pages }}"
          echo "  security-events: ${{ permissions.security-events }}"
          echo "  metadata: ${{ permissions.metadata }}"
          echo "  repository-projects: ${{ permissions.repository-projects }}"
          echo "  discussions: ${{ permissions.discussions }}"
          echo "  checks: ${{ permissions.checks }}"
          echo "  statuses: ${{ permissions.statuses }}"
          echo "  environments: ${{ permissions.environments }}"
          echo ""
          echo "Contexto do evento:"
          echo "  event_name: ${{ github.event_name }}"
          echo "  ref: ${{ github.ref }}"
          echo "  actor: ${{ github.actor }}"
          echo "  repository: ${{ github.repository }}"

      - name: Testar cada permissao
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Teste de Permissoes ==="
          
          # Testar contents
          echo "Testando contents..."
          gh api repos/${{ github.repository }} > /dev/null 2>&1 && echo "  [OK] contents" || echo "  [FAIL] contents"
          
          # Testar actions
          echo "Testando actions..."
          gh api repos/${{ github.repository }}/actions/workflows > /dev/null 2>&1 && echo "  [OK] actions" || echo "  [FAIL] actions"
          
          # Testar issues
          echo "Testando issues..."
          gh api repos/${{ github.repository }}/issues > /dev/null 2>&1 && echo "  [OK] issues" || echo "  [FAIL] issues"
          
          # Testar pull-requests
          echo "Testando pull-requests..."
          gh api repos/${{ github.repository }}/pulls > /dev/null 2>&1 && echo "  [OK] pull-requests" || echo "  [FAIL] pull-requests"
```

### Validacao de Permissions em CI

```yaml
name: Validate Permissions

on:
  pull_request:
    paths:
      - '.github/workflows/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Validar permissoes
        run: |
          echo "=== Validacao de Permissoes ==="
          
          ERROR=0
          
          for file in .github/workflows/*.yml; do
            echo "Analisando: $file"
            
            # Verificar se tem bloco permissions
            if ! grep -q "^permissions:" "$file"; then
              echo "  [WARN] Sem bloco permissions"
              ERROR=1
            fi
            
            # Verificar write-all
            if grep -q "write-all" "$file"; then
              echo "  [ERROR] write-all encontrado"
              ERROR=1
            fi
            
            # Verificar secrets em logs
            if grep -q "echo.*secrets\." "$file"; then
              echo "  [WARN] Secrets podem ser impressos em logs"
            fi
          done
          
          if [ $ERROR -eq 1 ]; then
            echo "Validacao falhou"
            exit 1
          fi
          
          echo "Validacao passou"
```

### Logging de Permissoes

```yaml
name: Permission Logging

on:
  push:
  pull_request:

jobs:
  log-permissions:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Log permissoes
        run: |
          echo "=== Permission Log ===" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Scope | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|-------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| contents | ${{ permissions.contents }} |" >> $GITHUB_STEP_SUMMARY
          echo "| actions | ${{ permissions.actions }} |" >> $GITHUB_STEP_SUMMARY
          echo "| issues | ${{ permissions.issues }} |" >> $GITHUB_STEP_SUMMARY
          echo "| pull-requests | ${{ permissions.pull-requests }} |" >> $GITHUB_STEP_SUMMARY
          echo "| packages | ${{ permissions.packages }} |" >> $GITHUB_STEP_SUMMARY
          echo "| deployments | ${{ permissions.deployments }} |" >> $GITHUB_STEP_SUMMARY
          echo "| id-token | ${{ permissions.id-token }} |" >> $GITHUB_STEP_SUMMARY
          echo "| pages | ${{ permissions.pages }} |" >> $GITHUB_STEP_SUMMARY
          echo "| security-events | ${{ permissions.security-events }} |" >> $GITHUB_STEP_SUMMARY
          echo "| metadata | ${{ permissions.metadata }} |" >> $GITHUB_STEP_SUMMARY
          echo "| repository-projects | ${{ permissions.repository-projects }} |" >> $GITHUB_STEP_SUMMARY
          echo "| discussions | ${{ permissions.discussions }} |" >> $GITHUB_STEP_SUMMARY
          echo "| checks | ${{ permissions.checks }} |" >> $GITHUB_STEP_SUMMARY
          echo "| statuses | ${{ permissions.statuses }} |" >> $GITHUB_STEP_SUMMARY
          echo "| environments | ${{ permissions.environments }} |" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "Event: ${{ github.event_name }}" >> $GITHUB_STEP_SUMMARY
          echo "Actor: ${{ github.actor }}" >> $GITHUB_STEP_SUMMARY
          echo "Ref: ${{ github.ref }}" >> $GITHUB_STEP_SUMMARY
```

---

## 10.16 Referencias

1. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#permissions
2. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#granting-additional-permissions
3. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-github_token-in-workflows
4. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
5. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
6. https://docs.github.com/en/actions/using-workflows/roles-for-continuous-integration
7. https://docs.github.com/en/actions/security-guides/automatic-token-authentication
8. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
9. https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
10. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-secrets
2. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#granting-additional-permissions
3. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-github_token-in-workflows
4. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
5. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
6. https://docs.github.com/en/actions/using-workflows/roles-for-continuous-integration
7. https://docs.github.com/en/actions/security-guides/automatic-token-authentication
8. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
9. https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
10. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-secrets
