---
layout: default
title: "09-secrets-variaveis"
---

# Capitulo 9 -- Secrets e Variaveis Seguras

> *"Secrets sao o ouro do CI/CD. Proteja-os como tal."*

---

## Objetivos de Aprendizado

1. Configurar secrets em repository, environment e organization
2. Implementar OIDC para authentication sem secrets
3. Gerenciar GITHUB_TOKEN e custom tokens
4. Auditar uso de secrets
5. Integrar com Vault para secret management
6. Implementar rotation strategies para secrets
7. Entender secret masking e suas limitacoes
8. Configurar GitHub Apps tokens
9. Gerenciar organization secrets com visibilidade
10. Implementar verificacao de saude de secrets
11. Configurar secrets para multi-cloud
12. Implementar secret scanning

---

## 9.1 Repository Secrets

Repository secrets sao variaveis sensiveis configuradas no nivel do repositorio. Elas estao disponiveis para todos os workflows dentro daquele repositorio e sao encriptadas em repouso e em transito.

### Configuracao Via Interface

Para configurar repository secrets pela interface:

1. Navegue ate Settings > Secrets and variables > Actions
2. Clique em "New repository secret"
3. Insira o nome (ex: `API_KEY`) e o valor
4. Clique em "Add secret"

### Configuracao Via CLI

```bash
# Adicionar um secret ao repositorio
gh secret set API_KEY --body "sk-1234567890abcdef"

# Listar todos os secrets do repositorio
gh secret list

# Obter detalhes de um secret especifico
gh secret list --repos myorg/myrepo

# Deletar um secret
gh secret delete API_KEY

# Definir secret a partir de um arquivo
gh secret set DB_PASSWORD < /path/to/password.txt

# Definir secret com visibilidade
gh secret set API_KEY --org myorg --visibility selected
```

### Uso em Workflows

```yaml
# Forma 1: Via variavel de ambiente no step (RECOMENDADO)
steps:
  - name: Usar secret como variavel de ambiente
    run: echo "Chave: ${{ secrets.API_KEY }}"
    env:
      API_KEY: ${{ secrets.API_KEY }}

# Forma 2: Direto no template (MENOS RECOMENDADO)
steps:
  - name: Acesso direto ao secret
    run: |
      echo "Chave: ${{ secrets.API_KEY }}"
```

### Exemplo Completo de Repository Secret

```yaml
name: Deploy com Repository Secrets

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar ambiente
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_SECRET: ${{ secrets.API_SECRET }}
          ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
        run: |
          echo "Configurando ambiente de build..."
          echo "DATABASE_URL esta configurado: $([ -n "$DATABASE_URL" ] && echo 'sim' || echo 'nao')"
          echo "API_SECRET esta configurado: $([ -n "$API_SECRET" ] && echo 'sim' || echo 'nao')"
          echo "ENCRYPTION_KEY esta configurado: $([ -n "$ENCRYPTION_KEY" ] && echo 'sim' || echo 'nao')"

      - name: Build com secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          npm ci
          npm run build

      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_SECRET: ${{ secrets.API_SECRET }}
        run: |
          echo "Deploying..."
```

### Variaveis vs Secrets

| Caracteristica | Secrets | Variaveis |
|---------------|---------|-----------|
| Visibilidade | Encriptadas, nao visiveis | Publicas, visiveis |
| Logs | Mascaram automaticamente | Nao mascaram |
| Uso principal | Credenciais, tokens | Configuracoes nao sensiveis |
| Editavel por | Admins do repo | Qualquer pessoa com acesso |
| Maximo | 1000 por repo | 500 por repo |
| API de leitura | Somente via workflow | Via API e UI |
| Auditoria | Audit log disponivel | Audit log disponivel |
| Exportacao | Nao permitida | Permitida |

```yaml
# Uso correto: secrets para dados sensiveis, variaveis para configuracoes
steps:
  - name: Configurar build
    env:
      # Secrets: dados sensiveis
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
      API_KEY: ${{ secrets.API_KEY }}
      # Variaveis: configuracoes nao sensiveis
      APP_NAME: ${{ vars.APP_NAME }}
      NODE_ENV: ${{ vars.NODE_ENV }}
      LOG_LEVEL: ${{ vars.LOG_LEVEL }}
    run: |
      echo "App: $APP_NAME"
      echo "Env: $NODE_ENV"
      echo "Log: $LOG_LEVEL"
```

### Nomenclatura e Convencoes

```yaml
# Convencoes recomendadas para nomes de secrets:
# - Usar SCREAMING_SNAKE_CASE
# - Prefixedo por dominio/aplicacao
# - Evitar nomes genericos
# - Usar descricoes claras

# Exemplos por categoria:
# AWS
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# AWS_REGION

# Docker
# DOCKERHUB_USERNAME
# DOCKERHUB_TOKEN
# DOCKER_REGISTRY_URL

# CI/CD
# CODECOV_TOKEN
# SONAR_TOKEN
# SONAR_HOST_URL

# Notifications
# SLACK_WEBHOOK_URL
# SLACK_BOT_TOKEN
# DISCORD_WEBHOOK_URL

# Database
# DATABASE_URL
# DATABASE_READ_URL
# DATABASE_WRITE_URL
# REDIS_URL

# API Keys
# STRIPE_SECRET_KEY
# SENDGRID_API_KEY
# TWILIO_AUTH_TOKEN
```

### Erros Comuns com Repository Secrets

```yaml
# ERRO 1: Secret nao configurado (retorna string vazia)
steps:
  - name: Verificar secret
    run: |
      if [ -z "$MISSING_SECRET" ]; then
        echo "ERRO: Secret MISSING_SECRET nao configurado!"
        exit 1
      fi

# ERRO 2: Secret em log sem mascaramento
steps:
  - name: Log com mascaramento
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}
    run: |
      # ISSO E SEGURO - GitHub mascara automaticamente
      echo "Meu secret: $MY_SECRET"
      
      # ISSO E INSEGURO - Nao faca isso
      echo "Meu secret em JSON: {\"secret\": \"$MY_SECRET\"}"

# ERRO 3: Secret passado como argumento de comando
steps:
  - name: Nao faca isso
    run: |
      # INSEGURO: secret pode vazar em /proc/cmdline
      curl -H "Authorization: Bearer ${{ secrets.API_KEY }}" https://api.example.com

# ERRO 4: Secret em container sem env
jobs:
  build:
    container:
      image: node:20
    steps:
      - name: Secret nao disponivel
        run: |
          echo "API_KEY: $API_KEY"  # Vazio

# SOLUCAO: Passar via env explicitamente
jobs:
  build:
    container:
      image: node:20
    steps:
      - name: Secret via env
        env:
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "API_KEY: $API_KEY"  # Funciona
```

### Versionamento de Secrets

```yaml
name: Secret Rotation

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Acao a executar'
        required: true
        type: choice
        options:
          - rotate
          - verify
          - rollback

jobs:
  secret-rotation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verificar secret atual
        env:
          CURRENT_SECRET: ${{ secrets.API_KEY }}
        run: |
          echo "Verificando secret atual..."
          if [ -z "$CURRENT_SECRET" ]; then
            echo "Secret atual nao encontrado"
            exit 1
          fi

      - name: Rotacionar secret
        if: inputs.action == 'rotate'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          NEW_SECRET=$(openssl rand -hex 32)
          echo "Novo secret gerado"
          
          KEY_DATA=$(gh api repos/${{ github.repository }}/actions/secrets/public-key)
          KEY_ID=$(echo $KEY_DATA | jq -r '.key_id')
          PUBLIC_KEY=$(echo $KEY_DATA | jq -r '.key')
          
          ENCRYPTED=$(echo -n "$NEW_SECRET" | \
            sodium seal -p "$PUBLIC_KEY" -f base64)
          
          gh api repos/${{ github.repository }}/actions/secrets/API_KEY \
            --method PUT \
            --field encrypted_value="$ENCRYPTED" \
            --field key_id="$KEY_ID"
          
          echo "Secret rotacionado com sucesso"
```

### Secret Scanning

```yaml
name: Secret Scanning

on:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar secrets expostos
        run: |
          echo "=== Verificacao de Secret Scanning ==="
          # GitHub detecta automaticamente secrets expostos
          # Configurar em Settings > Security > Secret scanning
          
      - name: Verificar arquivos sensiveis
        run: |
          echo "Verificando arquivos que podem conter secrets..."
          
          # Verificar .env files
          if [ -f ".env" ]; then
            echo "AVISO: Arquivo .env encontrado"
          fi
          
          # Verificar arquivos de configuracao
          find . -name "*.json" -o -name "*.yaml" -o -name "*.yml" | while read file; do
            if grep -q "password\|secret\|token\|key" "$file" 2>/dev/null; then
              echo "AVISO: Possivel secret em $file"
            fi
          done
```

---

## 9.2 Environment Secrets

Environment secrets sao configurados no nivel de environment, o que permite isolar credenciais por ambiente (staging, production, etc.).

### Configuracao de Environments

```yaml
name: Deploy com Environments

on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy para Staging
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
          API_SECRET: ${{ secrets.API_SECRET }}
        run: |
          echo "Deploying to staging..."
          echo "DB_HOST: $DB_HOST"
          echo "Redis configurado: $([ -n "$REDIS_URL" ] && echo 'sim' || echo 'nao')"

  deploy-production:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Deploy para Production
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
          API_SECRET: ${{ secrets.API_SECRET }}
          ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
        run: |
          echo "Deploying to production..."
          echo "DB_HOST: $DB_HOST"
```

### Environment com Protection Rules

```yaml
# Configuracao na GitHub UI:
# Settings > Environments > new environment
# 1. Adicionar reviewers
# 2. Adicionar branches restritos (ex: main)
# 3. Adicionar wait timer (ex: 5 minutos)
# 4. Adicionar deployment branches

name: Deploy com Protection Rules

on:
  workflow_dispatch:

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        env:
          PRODUCTION_SECRET: ${{ secrets.PRODUCTION_SECRET }}
        run: |
          echo "Deploying with protection rules..."
          echo "Este job so roda apos aprovacao de reviewers"
```

### Environment Variables vs Environment Secrets

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Usar variaveis e secrets do environment
        env:
          # Variaveis do environment (publicas, visiveis nos logs)
          APP_NAME: ${{ vars.APP_NAME }}
          APP_PORT: ${{ vars.APP_PORT }}
          # Secrets do environment (encriptados)
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "App: $APP_NAME na porta $APP_PORT"
          echo "Database configurado: $([ -n "$DATABASE_URL" ] && echo 'sim' || echo 'nao')"
```

### Multi-Environment Strategy

```yaml
name: Multi-Environment Deploy

on:
  push:
    branches: [main, staging, develop]

jobs:
  determine-environment:
    runs-on: ubuntu-latest
    outputs:
      environment: ${{ steps.env.outputs.environment }}
    steps:
      - name: Determinar environment
        id: env
        run: |
          if [ "${{ github.ref }}" = "refs/heads/main" ]; then
            echo "environment=production" >> $GITHUB_OUTPUT
          elif [ "${{ github.ref }}" = "refs/heads/staging" ]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
          else
            echo "environment=development" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: determine-environment
    runs-on: ubuntu-latest
    environment: ${{ needs.determine-environment.outputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        env:
          ENVIRONMENT: ${{ needs.determine-environment.outputs.environment }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
        run: |
          echo "Deploying to $ENVIRONMENT..."
          echo "Database configurado: $([ -n "$DATABASE_URL" ] && echo 'sim' || echo 'nao')"
          echo "API Key configurado: $([ -n "$API_KEY" ] && echo 'sim' || echo 'nao')"
          echo "Redis configurado: $([ -n "$REDIS_URL" ] && echo 'sim' || echo 'nao')"
```

### Environment com Reviewers

```yaml
name: Deploy com Reviewers

on:
  workflow_dispatch:

jobs:
  request-approval:
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: |
          echo "Este deploy requer aprovacao"
          echo "Reviewers serao notificados"
```

### Environment com Wait Timer

```yaml
name: Deploy com Wait Timer

on:
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: |
          echo "Deploying..."
          echo "Wait timer de 5 minutos configurado no environment"
```

### Environment com Deployment Branches

```yaml
name: Deploy com Branch Protection

on:
  push:
    branches: [main, release/*]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: |
          echo "Deploying..."
          echo "Apenas branches main e release/* podem fazer deploy"
```

---

## 9.3 Organization Secrets

Organization secrets sao compartilhados entre todos os repositorios de uma organizacao.

### Configuracao de Organization Secrets

```bash
# Adicionar secret a organizacao
gh secret set API_KEY --org myorg --visibility all

# Listar secrets da organizacao
gh secret list --org myorg

# Adicionar secret com acesso restrito
gh secret set DB_PASSWORD --org myorg --visibility selected

# Deletar secret da organizacao
gh secret delete API_KEY --org myorg
```

### Visibilidade de Organization Secrets

| Visibilidade | Descricao | Uso Recomendado |
|-------------|-----------|-----------------|
| `all` | Todos os repos da org | Secrets compartilhados seguros |
| `private` | Repos privados apenas | Secrets sensiveis da org |
| `selected` | Repos selecionados | Secrets para projetos especificos |

### Uso em Workflows

```yaml
name: Deploy com Organization Secrets

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        env:
          # Secret da organizacao (visibilidade: all)
          ORG_API_KEY: ${{ secrets.ORG_API_KEY }}
          # Secret da organizacao (visibilidade: private)
          ORG_DB_PASSWORD: ${{ secrets.ORG_DB_PASSWORD }}
          # Secret da organizacao (visibilidade: selected)
          ORG_DEPLOY_TOKEN: ${{ secrets.ORG_DEPLOY_TOKEN }}
          # Repository secret (override do organization secret)
          REPO_API_KEY: ${{ secrets.REPO_API_KEY }}
        run: |
          echo "Deploying com organization secrets..."
          echo "ORG_API_KEY configurado: $([ -n "$ORG_API_KEY" ] && echo 'sim' || echo 'nao')"
```

### Gerenciamento de Organization Secrets via API

```yaml
name: Gerenciar Organization Secrets

on:
  workflow_dispatch:
    inputs:
      action:
        description: 'Acao a executar'
        required: true
        type: choice
        options:
          - create
          - update
          - delete
          - list

jobs:
  manage-secrets:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Listar organization secrets
        if: inputs.action == 'list'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Organization secrets:"
          gh secret list --org ${{ github.repository_owner }}

      - name: Criar/Atualizar organization secret
        if: inputs.action == 'create' || inputs.action == 'update'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh secret set MY_SECRET --org ${{ github.repository_owner }} --body "valor-do-secret"
          echo "Secret MY_SECRET criado/atualizado com sucesso"

      - name: Deletar organization secret
        if: inputs.action == 'delete'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh secret delete MY_SECRET --org ${{ github.repository_owner }}
          echo "Secret MY_SECRET deletado com sucesso"
```

### Estrategia de Organization Secrets

```yaml
name: Organization Secret Strategy

on:
  workflow_dispatch:

jobs:
  demonstrate-secrets:
    runs-on: ubuntu-latest
    steps:
      - name: Hierarquia de secrets
        env:
          SHARED_SECRET: ${{ secrets.SHARED_SECRET }}
        run: |
          echo "Secrets seguem a hierarquia:"
          echo "1. Repository secret (maior prioridade)"
          echo "2. Environment secret"
          echo "3. Organization secret (menor prioridade)"
          echo ""
          echo "SHARED_SECRET: $([ -n "$SHARED_SECRET" ] && echo 'configurado' || echo 'nao encontrado')"
```

---

## 9.4 Secret Masking

GitHub automaticamente mascara secrets que sao impressos nos logs de um workflow.

### Como Funciona o Mascaramento

```yaml
steps:
  - name: Demonstrar mascaramento
    env:
      MY_SECRET: "super-secret-value-12345"
    run: |
      # ESTE sera mascarado nos logs
      echo "Meu secret: $MY_SECRET"
      # Saida nos logs: Meu secret: ***
      
      # ESTE tambem sera mascarado
      curl -H "Authorization: Bearer $MY_SECRET" https://api.example.com
      # Saida nos logs: curl -H "Authorization: Bearer ***" https://api.example.com
```

### Forcar Mascaramento Manualmente

```yaml
steps:
  - name: Mascarar valor manualmente
    run: |
      # Forcar mascaramento de um valor
      echo "::add-mask::${{ github.event.head_commit.message }}"
      
      # Agora este valor sera mascarado nos logs
      echo "Commit message: ${{ github.event.head_commit.message }}"
```

### Limitacoes do Mascaramento

```yaml
steps:
  - name: Limitacoes do mascaramento
    env:
      MY_SECRET: "abc123"
    run: |
      # PROBLEMA 1: Secret em parte de uma string maior
      echo "prefix-abc123-sufixo"
      # O GitHub NAO mascara isso

      # PROBLEMA 2: Secret transformado
      echo "${MY_SECRET^^}"
      # O GitHub pode NAO mascara isso

      # PROBLEMA 3: Secret em arquivo
      echo "$MY_SECRET" > arquivo.txt
      # O GitHub NAO mascara arquivos

      # SOLUCAO: Mascarar valor manualmente
      echo "::add-mask::$MY_SECRET"
      echo "Agora o valor original sera mascarado"
```

### Mascaramento Avancado

```yaml
steps:
  - name: Mascaramento avancado
    env:
      AWS_ACCESS_KEY: ${{ secrets.AWS_ACCESS_KEY }}
      AWS_SECRET_KEY: ${{ secrets.AWS_SECRET_KEY }}
      DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
    run: |
      # Mascarar multiplos valores
      echo "::add-mask::$AWS_ACCESS_KEY"
      echo "::add-mask::$AWS_SECRET_KEY"
      echo "::add-mask::$DB_PASSWORD"
      
      # Agora qualquer ocorrencia sera mascarada
      echo "AWS Key: $AWS_ACCESS_KEY"
      echo "AWS Secret: $AWS_SECRET_KEY"
      echo "DB Password: $DB_PASSWORD"
      
      # Mascarar valor derivado
      HASH=$(echo -n "$DB_PASSWORD" | sha256sum | cut -d' ' -f1)
      echo "::add-mask::$HASH"
      echo "Hash: $HASH"
```

### Melhores Praticas de Mascaramento

```yaml
steps:
  - name: Melhores praticas
    run: |
      echo "Praticas de seguranca:"
      echo "1. Use env vars para secrets"
      echo "2. Nao imprima secrets"
      echo "3. Use add-mask para valores adicionais"
      echo "4. Nao escreva secrets em arquivos"
      echo "5. Nao passe secrets como argumentos"
```

---

## 9.5 OIDC (OpenID Connect)

OIDC permite que workflows se autentiquem em cloud providers sem precisar de long-lived secrets.

### Como Funciona o OIDC

1. GitHub emite um token de identidade quando o workflow roda
2. O cloud provider valida o token contra o GitHub OIDC provider
3. O provider retorna credenciais de curta duracao
4. O workflow usa essas credenciais para acessar recursos

### Vantagens do OIDC

| Aspecto | Secrets Tradicionais | OIDC |
|---------|---------------------|------|
| Seguranca | Credenciais longas | Tokens de curta duracao |
| Rotacao | Manual | Automatica |
| Escopo | Fixo | Configuravel |
| Audit | Dificil | Facil via cloud provider |
| Exposicao | Risco de vazamento | Minimo |

### OIDC com AWS

```yaml
name: Deploy com OIDC AWS

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

      - name: Configurar AWS Credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/GitHubActionsRole
          aws-region: us-east-1

      - name: Deploy para S3
        run: |
          aws s3 sync dist/ s3://my-bucket/
          echo "Deploy concluido"

      - name: Verificar credenciais
        run: |
          aws sts get-caller-identity
          echo "Identity verificada com sucesso"
```

### Configuracao OIDC no AWS

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:myorg/myrepo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### OIDC com GCP

```yaml
name: Deploy com OIDC GCP

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

      - name: Autenticar no GCP via OIDC
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider
          service_account: my-service-account@my-project.iam.gserviceaccount.com

      - name: Deploy para Cloud Run
        run: |
          gcloud run deploy my-service --source . --region us-central1
          echo "Deploy concluido"
```

### OIDC com Azure

```yaml
name: Deploy com OIDC Azure

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

      - name: Login via OIDC no Azure
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy para Azure
        run: |
          az webapp deploy --resource-group my-rg --name my-app --src-path dist/
          echo "Deploy concluido"
```

### OIDC com Kubernetes

```yaml
name: Deploy com OIDC Kubernetes

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

      - name: Configurar OIDC para Kubernetes
        uses: azure/k8s-set-context@v4
        with:
          method: kubeconfig
          kubeconfig: ${{ secrets.KUBECONFIG }}

      - name: Deploy para Kubernetes
        run: |
          kubectl apply -f k8s/
          kubectl rollout status deployment/my-app
```

### OIDC Multi-Cloud

```yaml
name: Multi-Cloud Deploy com OIDC

on:
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy-aws:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy AWS
        run: |
          aws s3 sync dist/ s3://my-aws-bucket/

  deploy-gcp:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: GCP OIDC
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}

      - name: Deploy GCP
        run: |
          gcloud run deploy my-service --source . --region us-central1

  deploy-azure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Azure OIDC
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy Azure
        run: |
          az webapp deploy --resource-group my-rg --name my-app --src-path dist/
```

---

## 9.6 GITHUB_TOKEN

O `GITHUB_TOKEN` e um token especial gerado automaticamente para cada execucao de workflow.

### Permissoes Padrao

```yaml
# Permissoes padrao do GITHUB_TOKEN
# Em repos novos (post-2023):
# - contents: read
# - metadata: read
# - packages: none

# Em repos existentes (pre-2023):
# - contents: write
# - packages: write
# - issues: write
# - pull-requests: write
```

### Configuracao de Permissoes

```yaml
# Workflow-level permissions
permissions:
  contents: read
  issues: write
  pull-requests: write
  packages: write
  id-token: write

# Job-level permissions
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v4
      - run: npm run build
```

### Uso do GITHUB_TOKEN

```yaml
steps:
  - name: Criar issue
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: |
      gh issue create \
        --title "Novo bug report" \
        --body "Descricao do bug" \
        --label "bug"

  - name: Criar release
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: |
      gh release create v1.0.0 \
        --title "v1.0.0" \
        --notes "Release notes" \
        dist/*

  - name: Comentar em PR
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    run: |
      gh pr comment ${{ github.event.pull_request.number }} \
        --body "Build concluido com sucesso!"
```

### GITHUB_TOKEN em Containers

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: node:20
      options: --user 0
    steps:
      - uses: actions/checkout@v4
      
      - name: Usar GITHUB_TOKEN em container
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "GH_TOKEN configurado: $([ -n "$GH_TOKEN" ] && echo 'sim' || echo 'nao')"
```

### Seguranca do GITHUB_TOKEN

```yaml
# Melhores praticas de seguranca:
# 1. SEMPRE defina permissoes explicitamente
# 2. Use least-privilege (minimo necessario)
# 3. Nao use write-all
# 4. Prefira OIDC para cloud providers
# 5. Audite regularmente as permissoes

permissions:
  contents: read  # MINIMO necessario

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm test

  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # Write apenas para deploy
      pages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
      - uses: actions/deploy-pages@v4
```

---

## 9.7 Custom Tokens

### Personal Access Tokens (PAT)

```yaml
name: Usando PAT

on:
  workflow_dispatch:

jobs:
  use-pat:
    runs-on: ubuntu-latest
    steps:
      - name: Usar PAT para acesso cross-repo
        env:
          GH_TOKEN: ${{ secrets.PAT_TOKEN }}
        run: |
          gh repo list --limit 20
          
          gh repo create myorg/new-repo --private

  - name: Usar PAT para GitHub API
    env:
      PAT_TOKEN: ${{ secrets.PAT_TOKEN }}
    run: |
      curl -H "Authorization: token $PAT_TOKEN" \
        https://api.github.com/user/repos
```

### GitHub Apps Tokens

```yaml
name: GitHub App Token

on:
  workflow_dispatch:

jobs:
  use-app-token:
    runs-on: ubuntu-latest
    steps:
      - name: Obter token de GitHub App
        uses: tibdex/github-app-token@v2
        id: app-token
        with:
          app_id: ${{ secrets.APP_ID }}
          private_key: ${{ secrets.PRIVATE_KEY }}
          repositories: '["my-repo"]'
          permissions: 'contents:write,issues:write'

      - name: Usar token da app
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: |
          gh issue create --title "Novo issue" --body "Criado via GitHub App"
```

### Comparacao de Tokens

| Tipo | Vantagens | Desvantagens | Uso Recomendado |
|------|-----------|--------------|-----------------|
| GITHUB_TOKEN | Automatico, seguro | Limitado ao repo | Uso basico no repo |
| PAT | Acesso cross-repo | Depende de usuario | Acesso temporario |
| GitHub App | Seguro, revogavel | Mais complexo | Apps de prod |
| Installation | Scoped por repo | Requer GitHub App | Apps instaladas |

---

## 9.8 Secret Rotation Strategies

### Rotacao Manual

```yaml
name: Secret Rotation

on:
  workflow_dispatch:
    inputs:
      secret_name:
        description: 'Nome do secret a rotacionar'
        required: true
      environment:
        description: 'Environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  rotate:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Gerar novo secret
        run: |
          NEW_SECRET=$(openssl rand -base64 32)
          echo "Novo secret gerado: $NEW_SECRET"

      - name: Atualizar secret via API
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          KEY_DATA=$(gh api repos/${{ github.repository }}/actions/secrets/public-key)
          KEY_ID=$(echo $KEY_DATA | jq -r '.key_id')
          PUBLIC_KEY=$(echo $KEY_DATA | jq -r '.key')
          
          ENCRYPTED_SECRET=$(echo -n "$NEW_SECRET" | \
            sodium seal -p "$PUBLIC_KEY" -f base64)
          
          gh api repos/${{ github.repository }}/actions/secrets/${{ inputs.secret_name }} \
            --method PUT \
            --field encrypted_value="$ENCRYPTED_SECRET" \
            --field key_id="$KEY_ID"
          
          echo "Secret atualizado com sucesso"
```

### Rotacao Automatica

```yaml
name: Auto Secret Rotation

on:
  schedule:
    - cron: '0 0 1 * *'  # Primeiro dia de cada mes

jobs:
  rotate-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Rotacionar secrets AWS
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          aws iam create-access-key --user-name github-actions
          echo "Secrets AWS rotacionados"
```

### Verificacao de Saude de Secrets

```yaml
name: Secret Health Check

on:
  schedule:
    - cron: '0 6 * * *'  # Diariamente as 6h

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar API Key externa
        env:
          API_KEY: ${{ secrets.EXTERNAL_API_KEY }}
        run: |
          HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $API_KEY" \
            https://api.external-service.com/health)
          
          if [ $HTTP_STATUS -ne 200 ]; then
            echo "ERRO: API Key invalida ou expirada (HTTP $HTTP_STATUS)"
            exit 1
          fi
          echo "API Key saudavel (HTTP $HTTP_STATUS)"
```

---

## 9.9 Audit Log

### Verificando Audit Log via API

```yaml
name: Secret Audit

on:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      actions: read
      actions_secrets: read
    steps:
      - name: Listar repository secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Repository Secrets ==="
          gh secret list

      - name: Listar environment secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Environment Secrets ==="
          gh secret list --env production
          gh secret list --env staging

      - name: Verificar uso de secrets em workflows recentes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Workflows Recentes ==="
          gh run list --limit 10 --json name,status,conclusion
```

### Monitoramento de Uso de Secrets

```yaml
name: Secret Usage Monitoring

on:
  workflow_run:
    workflows: ["Deploy"]
    types: [completed]

jobs:
  monitor:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Analisar falha
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          RUN_ID="${{ github.event.workflow_run.id }}"
          echo "Analizando run: $RUN_ID"
          
          gh run view $RUN_ID --log-failed | grep -i "secret\|credential\|auth"
```

### Relatorio de Auditoria

```yaml
name: Security Audit Report

on:
  workflow_dispatch:
    inputs:
      report_type:
        description: 'Tipo de relatorio'
        required: true
        type: choice
        options:
          - full
          - secrets-only
          - permissions-only

jobs:
  generate-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Gerar relatorio de secrets
        if: inputs.report_type == 'full' || inputs.report_type == 'secrets-only'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "# Relatorio de Secrets" > report.md
          echo "Data: $(date)" >> report.md
          echo "" >> report.md
          
          echo "## Repository Secrets" >> report.md
          gh secret list --json name,updatedAt,visibility >> report.md
          
          echo "" >> report.md
          echo "## Environment Secrets" >> report.md
          gh secret list --env production --json name,updatedAt >> report.md

      - name: Upload relatorio
        uses: actions/upload-artifact@v4
        with:
          name: security-audit-report
          path: report.md
```

---

## 9.10 Vault Integration

### Configuracao Basica

```yaml
name: Vault Integration

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Importar secrets do Vault
        uses: hashicorp/vault-action@v3
        id: vault
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: github
          githubToken: ${{ secrets.GITHUB_TOKEN }}
          secrets: |
            secret/data/myapp/config api_key | API_KEY;
            secret/data/myapp/config db_password | DB_PASSWORD;
            secret/data/myapp/config redis_url | REDIS_URL

      - name: Usar secrets do Vault
        env:
          API_KEY: ${{ steps.vault.outputs.API_KEY }}
          DB_PASSWORD: ${{ steps.vault.outputs.DB_PASSWORD }}
          REDIS_URL: ${{ steps.vault.outputs.REDIS_URL }}
        run: |
          echo "Secrets importados do Vault:"
          echo "API_KEY: $([ -n "$API_KEY" ] && echo 'configurado' || echo 'nao encontrado')"
          echo "DB_PASSWORD: $([ -n "$DB_PASSWORD" ] && echo 'configurado' || echo 'nao encontrado')"
          echo "REDIS_URL: $([ -n "$REDIS_URL" ] && echo 'configurado' || echo 'nao encontrado')"
```

### Vault com AppRole

```yaml
name: Vault AppRole

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login no Vault via AppRole
        uses: hashicorp/vault-action@v3
        id: vault
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: approle
          roleId: ${{ secrets.VAULT_ROLE_ID }}
          secretId: ${{ secrets.VAULT_SECRET_ID }}
          secrets: |
            secret/data/myapp/config api_key | API_KEY

      - name: Usar secret
        env:
          API_KEY: ${{ steps.vault.outputs.API_KEY }}
        run: echo "API_KEY: $API_KEY"
```

### Vault Dynamic Secrets

```yaml
name: Vault Dynamic Secrets

on:
  workflow_dispatch:

jobs:
  dynamic-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Gerar credencial dinamica
        uses: hashicorp/vault-action@v3
        id: vault
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: github
          secrets: |
            database/creds/my-role | DB_USERNAME;DB_PASSWORD

      - name: Usar credencial dinamica
        env:
          DB_USERNAME: ${{ steps.vault.outputs.DB_USERNAME }}
          DB_PASSWORD: ${{ steps.vault.outputs.DB_PASSWORD }}
        run: |
          echo "Credencial dinamica gerada:"
          echo "Username: $DB_USERNAME"
          echo "Password: $DB_PASSWORD"
          echo "Estas credenciais expiram automaticamente"
```

---

## 9.11 Complete Secure Pipeline

```yaml
name: Complete Secure Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  actions: read
  packages: write

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validar configuracao
        run: |
          echo "Validando pipeline segura..."
          echo "1. Permissoes minimais configuradas"
          echo "2. OIDC habilitado para cloud providers"
          echo "3. Vault integrado para secrets"
          echo "4. Branch protection ativo"

  test:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Instalar dependencias
        run: npm ci
      
      - name: Rodar testes
        env:
          DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
        run: npm test

  security-scan:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      - name: CodeQL Analysis
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
      
      - name: Build e Analysis
        run: |
          npm ci
          npm run build
      
      - name: CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  build:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Build
        env:
          NODE_ENV: production
        run: |
          npm ci
          npm run build
      
      - name: Attest build provenance
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: dist/*
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    permissions:
      contents: read
      id-token: write
      deployments: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_STAGING_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Importar secrets do Vault
        uses: hashicorp/vault-action@v3
        id: vault
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: github
          secrets: |
            secret/data/myapp/staging db_password | DB_PASSWORD
      
      - name: Deploy para Staging
        env:
          DB_PASSWORD: ${{ steps.vault.outputs.DB_PASSWORD }}
          STAGING_URL: ${{ vars.STAGING_URL }}
        run: |
          echo "Deploying to staging..."
          aws s3 sync dist/ s3://staging-bucket/

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://myapp.com
    permissions:
      contents: read
      id-token: write
      deployments: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_PRODUCTION_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Importar secrets do Vault
        uses: hashicorp/vault-action@v3
        id: vault
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: github
          secrets: |
            secret/data/myapp/production db_password | DB_PASSWORD;
            secret/data/myapp/production api_key | API_KEY
      
      - name: Deploy para Production
        env:
          DB_PASSWORD: ${{ steps.vault.outputs.DB_PASSWORD }}
          API_KEY: ${{ steps.vault.outputs.API_KEY }}
        run: |
          echo "Deploying to production..."
          aws s3 sync dist/ s3://production-bucket/

      - name: Criar deployment status
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

---

## 9.12 Erros Comuns e Solucoes

### Erro: Secret Nao Encontrado

```yaml
# Problema: Secret retorna string vazia
steps:
  - name: Verificar secret
    run: |
      if [ -z "$MY_SECRET" ]; then
        echo "ERRO: Secret MY_SECRET nao encontrado!"
        echo "Verifique se o secret existe no repo, environment ou org"
        exit 1
      fi

# Solucao: Usar variavel de ambiente para passar o secret
steps:
  - name: Usar secret corretamente
    env:
      MY_SECRET: ${{ secrets.MY_SECRET }}
    run: |
      if [ -z "$MY_SECRET" ]; then
        echo "ERRO: Secret nao configurado"
        exit 1
      fi
      echo "Secret configurado com sucesso"
```

### Erro: Secret em Log

```yaml
# Problema: Secret aparece nos logs
steps:
  - name: Log com secret
    run: |
      echo "API Key: ${{ secrets.API_KEY }}"

# Solucao: Usar variavel de ambiente
steps:
  - name: Log seguro
    env:
      API_KEY: ${{ secrets.API_KEY }}
    run: |
      echo "API Key: $API_KEY"
```

### Erro: Secret em Container

```yaml
# Problema: Secret nao disponivel em container
jobs:
  build:
    container:
      image: node:20
    steps:
      - name: Secret em container
        run: |
          echo "API Key: $API_KEY"  # Vazio

# Solucao: Passar secret via env explicitamente
jobs:
  build:
    container:
      image: node:20
    steps:
      - name: Secret em container
        env:
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "API Key: $API_KEY"
```

---

## 9.13 Secret Management Patterns

### Padrao 1: Centralized Secret Management

```yaml
# Centralizar secrets em um servico externo (Vault, AWS Secrets Manager, etc.)
name: Centralized Secrets

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Obter secrets do AWS Secrets Manager
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Recuperar secrets
        run: |
          DB_PASSWORD=$(aws secretsmanager get-secret-value \
            --secret-id myapp/database-password \
            --query SecretString --output text)
          
          API_KEY=$(aws secretsmanager get-secret-value \
            --secret-id myapp/api-key \
            --query SecretString --output text)
          
          echo "Secrets recuperados com sucesso"

      - name: Usar secrets
        env:
          DB_PASSWORD: ${{ steps.secrets.outputs.DB_PASSWORD }}
          API_KEY: ${{ steps.secrets.outputs.API_KEY }}
        run: |
          echo "Usando secrets centralizados..."
```

### Padrao 2: Environment-Based Secret Injection

```yaml
# Injetar secrets baseado no environment
name: Environment Secret Injection

on:
  push:
    branches: [main, staging, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Injetar secrets do environment
        run: |
          echo "Secrets injetados para o environment: ${{ github.ref }}"
          
      - name: Usar secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "Usando secrets do environment atual"
```

### Padrao 3: Secret Rotation com Notificacao

```yaml
# Rotacionar secrets e notificar stakeholders
name: Secret Rotation with Notification

on:
  workflow_dispatch:
    inputs:
      secret_name:
        description: 'Nome do secret'
        required: true

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Gerar novo secret
        run: |
          NEW_SECRET=$(openssl rand -base64 32)
          echo "secret=$NEW_SECRET" >> $GITHUB_OUTPUT

      - name: Atualizar secret
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Atualizando secret: ${{ inputs.secret_name }}"
          
      - name: Notificar stakeholders
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Secret ${{ inputs.secret_name }} rotacionado com sucesso"}' \
            $SLACK_WEBHOOK
```

### Padrao 4: Secret Validation Before Deploy

```yaml
# Validar secrets antes de fazer deploy
name: Secret Validation

on:
  workflow_dispatch:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Validar todos os secrets necessarios
        run: |
          SECRETS_REQUIRED=(
            "DATABASE_URL"
            "API_KEY"
            "AWS_ROLE_ARN"
            "SLACK_WEBHOOK"
          )
          
          MISSING=()
          for secret in "${SECRETS_REQUIRED[@]}"; do
            if [ -z "${!secret}" ]; then
              MISSING+=("$secret")
            fi
          done
          
          if [ ${#MISSING[@]} -gt 0 ]; then
            echo "ERRO: Secrets faltando:"
            for secret in "${MISSING[@]}"; do
              echo "  - $secret"
            done
            exit 1
          fi
          
          echo "Todos os secrets estao configurados"
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```

### Padrao 5: Secret Backup and Recovery

```yaml
# Backup e recovery de secrets
name: Secret Backup

on:
  schedule:
    - cron: '0 0 1 * *'  # Mensal

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Backup secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Backup de Secrets ==="
          
          # Listar todos os secrets (valores nao sao expostos)
          gh secret list --json name,updatedAt > secrets-backup.json
          
          echo "Backup concluido"
          
      - name: Upload backup
        uses: actions/upload-artifact@v4
        with:
          name: secrets-backup
          path: secrets-backup.json
          retention-days: 90
```

---

## 9.14 Advanced Secret Strategies

### Estrategia 1: Secret Segregation

```yaml
# Separar secrets por dominio de responsabilidade
name: Secret Segregation

on:
  push:
    branches: [main]

jobs:
  database:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Database secrets
        env:
          DB_READ_URL: ${{ secrets.DB_READ_URL }}
          DB_WRITE_URL: ${{ secrets.DB_WRITE_URL }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          echo "Usando secrets de database"
          
  api:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: API secrets
        env:
          API_KEY: ${{ secrets.API_KEY }}
          API_SECRET: ${{ secrets.API_SECRET }}
        run: |
          echo "Usando secrets de API"
          
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Deploy secrets
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
          AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
        run: |
          echo "Usando secrets de deploy"
```

### Estrategia 2: Secret Rotation Schedule

```yaml
# Agendar rotacao automatica de secrets
name: Scheduled Secret Rotation

on:
  schedule:
    - cron: '0 0 1 * *'  # Mensal
    - cron: '0 0 15 * *'  # Quinzenal para secrets criticos

jobs:
  rotate:
    runs-on: ubuntu-latest
    steps:
      - name: Determinar secrets para rotacionar
        id: determine
        run: |
          if [ "${{ github.event.schedule }}" = "0 0 1 * *" ]; then
            echo "secrets=API_KEY,DB_PASSWORD" >> $GITHUB_OUTPUT
          else
            echo "secrets=DEPLOY_TOKEN" >> $GITHUB_OUTPUT
          fi

      - name: Rotacionar secrets
        run: |
          IFS=',' read -ra SECRETS <<< "${{ steps.determine.outputs.secrets }}"
          for secret in "${SECRETS[@]}"; do
            echo "Rotacionando: $secret"
            # Logica de rotacao
          done
```

### Estrategia 3: Secret Access Control

```yaml
# Controlar acesso a secrets baseado em branches
name: Secret Access Control

on:
  push:
    branches: [main, develop, feature/*]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar branch para secrets
        run: |
          if [ "${{ github.ref }}" = "refs/heads/main" ]; then
            echo "Branch main: acesso a todos os secrets"
          elif [ "${{ github.ref }}" = "refs/heads/develop" ]; then
            echo "Branch develop: acesso a secrets de staging"
          else
            echo "Outra branch: acesso limitado"
          fi

      - name: Usar secrets apropriados
        env:
          # Production secrets apenas para main
          PRODUCTION_DB_URL: ${{ github.ref == 'refs/heads/main' && secrets.PRODUCTION_DB_URL || '' }}
          # Staging secrets para develop
          STAGING_DB_URL: ${{ github.ref == 'refs/heads/develop' && secrets.STAGING_DB_URL || '' }}
        run: |
          echo "Secrets selecionados baseado na branch"
```

### Estrategia 4: Secret Encryption at Rest

```yaml
# Criptografar secrets adicionais
name: Secret Encryption

on:
  push:
    branches: [main]

jobs:
  encrypt:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Criptografar secrets adicionais
        run: |
          # Criptografar arquivo com secrets
          openssl enc -aes-256-cbc -salt -in secrets.txt -out secrets.enc \
            -pass pass:${{ secrets.ENCRYPTION_KEY }}
          
          echo "Secrets criptografados com sucesso"

      - name: Descriptografar secrets
        run: |
          # Descriptografar quando necessario
          openssl enc -aes-256-cbc -d -in secrets.enc -out secrets.txt \
            -pass pass:${{ secrets.ENCRYPTION_KEY }}
          
          echo "Secrets descriptografados com sucesso"
```

### Estrategia 5: Secret Monitoring and Alerting

```yaml
# Monitorar e alertar sobre uso de secrets
name: Secret Monitoring

on:
  workflow_run:
    workflows: ["*"]
    types: [completed]

jobs:
  monitor:
    runs-on: ubuntu-latest
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Analisar falha relacionada a secrets
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          RUN_ID="${{ github.event.workflow_run.id }}"
          
          # Verificar logs por erros de secrets
          gh run view $RUN_ID --log-failed | grep -i "secret\|credential\|auth\|token" | head -10

      - name: Enviar alerta
        if: success()
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"ALERTA: Possivel problema com secrets no workflow ${{ github.event.workflow_run.name }}"}' \
            $SLACK_WEBHOOK
```

---

## 9.15 Secret Management para Diferentes Linguagens

### Secrets em Node.js

```yaml
name: Node.js Secret Management

on:
  push:
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
          cache: 'npm'
      
      - name: Configurar secrets para Node.js
        run: |
          # Criar arquivo .env com secrets
          cat > .env << EOF
          DATABASE_URL=${{ secrets.DATABASE_URL }}
          API_KEY=${{ secrets.API_KEY }}
          REDIS_URL=${{ secrets.REDIS_URL }}
          EOF
          
          echo "Arquivo .env criado com secrets"

      - name: Build com secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          npm ci
          npm run build

      - name: Cleanup
        if: always()
        run: |
          rm -f .env
          echo "Arquivo .env removido"
```

### Secrets em Python

```yaml
name: Python Secret Management

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Configurar secrets para Python
        run: |
          # Criar arquivo .env
          cat > .env << EOF
          DATABASE_URL=${{ secrets.DATABASE_URL }}
          SECRET_KEY=${{ secrets.SECRET_KEY }}
          EOF

      - name: Instalar dependencias
        run: |
          pip install -r requirements.txt

      - name: Rodar testes
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
        run: |
          pytest
```

### Secrets em Go

```yaml
name: Go Secret Management

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Build com secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          go build -o myapp .

      - name: Test
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          go test ./...
```

### Secrets em Java

```yaml
name: Java Secret Management

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Build com secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          mvn clean package -Ddatabase.url=$DATABASE_URL -Dapi.key=$API_KEY

      - name: Test
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          mvn test
```

### Secrets em Docker

```yaml
name: Docker Secret Management

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build \
            --build-arg DATABASE_URL=${{ secrets.DATABASE_URL }} \
            --build-arg API_KEY=${{ secrets.API_KEY }} \
            -t myapp:${{ github.sha }} .

      - name: Test Docker image
        run: |
          docker run --rm \
            -e DATABASE_URL=${{ secrets.DATABASE_URL }} \
            -e API_KEY=${{ secrets.API_KEY }} \
            myapp:${{ github.sha }} npm test
```

---

## 9.16 Secret Management para CI/CD Avancado

### Pipeline com Secret Rotation

```yaml
name: Advanced Secret Rotation

on:
  workflow_dispatch:
    inputs:
      rotation_type:
        description: 'Tipo de rotacao'
        required: true
        type: choice
        options:
          - database
          - api-keys
          - all

jobs:
  rotate-database:
    if: inputs.rotation_type == 'database' || inputs.rotation_type == 'all'
    runs-on: ubuntu-latest
    steps:
      - name: Rotacionar credenciais de database
        env:
          CURRENT_DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          # Gerar nova senha
          NEW_PASSWORD=$(openssl rand -base64 24)
          echo "Nova senha gerada"
          
          # Atualizar no database
          echo "Atualizando senha no database..."
          
          # Atualizar no GitHub
          echo "Atualizando secret no GitHub..."

  rotate-api-keys:
    if: inputs.rotation_type == 'api-keys' || inputs.rotation_type == 'all'
    runs-on: ubuntu-latest
    steps:
      - name: Rotacionar API keys
        run: |
          # Gerar nova API key
          NEW_API_KEY=$(openssl rand -hex 32)
          echo "Nova API key gerada"
          
          # Atualizar no provedor
          echo "Atualizando API key no provedor..."
          
          # Atualizar no GitHub
          echo "Atualizando secret no GitHub..."
```

### Pipeline com Secret Validation

```yaml
name: Secret Validation Pipeline

on:
  push:
    branches: [main]

jobs:
  validate-secrets:
    runs-on: ubuntu-latest
    outputs:
      all_valid: ${{ steps.validate.outputs.all_valid }}
    steps:
      - name: Validar todos os secrets
        id: validate
        run: |
          SECRETS=(
            "DATABASE_URL"
            "API_KEY"
            "AWS_ROLE_ARN"
            "REDIS_URL"
            "SLACK_WEBHOOK"
          )
          
          VALID=true
          for secret in "${SECRETS[@]}"; do
            if [ -z "${!secret}" ]; then
              echo "MISSING: $secret"
              VALID=false
            else
              echo "VALID: $secret"
            fi
          done
          
          echo "all_valid=$VALID" >> $GITHUB_OUTPUT
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          AWS_ROLE_ARN: ${{ secrets.AWS_ROLE_ARN }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}

  deploy:
    needs: validate-secrets
    if: needs.validate-secrets.outputs.all_valid == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: |
          echo "Todos os secrets validados, fazendo deploy..."
```

### Pipeline com Secret Encryption

```yaml
name: Encrypted Secret Pipeline

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Descriptografar secrets
        run: |
          # Descriptografar arquivo de configuracao
          openssl enc -aes-256-cbc -d -in config.enc -out config.json \
            -pass pass:${{ secrets.ENCRYPTION_KEY }}
          
          echo "Secrets descriptografados"

      - name: Build
        run: |
          npm ci
          npm run build

      - name: Criptografar artifacts
        run: |
          # Criptografar artifacts sensiveis
          tar czf dist-encrypted.tar.gz dist/
          openssl enc -aes-256-cbc -salt -in dist-encrypted.tar.gz \
            -out dist-encrypted.tar.gz.enc \
            -pass pass:${{ secrets.ENCRYPTION_KEY }}
          
          echo "Artifacts criptografados"

      - name: Cleanup
        if: always()
        run: |
          rm -f config.json
          rm -f dist-encrypted.tar.gz
          echo "Arquivos sensiveis removidos"
```

---

## 9.17 Secret Management para Producao

### Configuracao de Producao

```yaml
name: Production Secret Management

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar environment
        run: |
          echo "Deploying to: ${{ inputs.environment }}"
          
          if [ "${{ inputs.environment }}" = "production" ]; then
            echo "ATENCAO: Deploy em production requer aprovacao"
          fi

      - name: Carregar secrets do environment
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
          REDIS_URL: ${{ secrets.REDIS_URL }}
          ENCRYPTION_KEY: ${{ secrets.ENCRYPTION_KEY }}
        run: |
          echo "Secrets carregados para ${{ inputs.environment }}"
          
          # Verificar se todos os secrets estao presentes
          SECRETS=("DATABASE_URL" "API_KEY" "REDIS_URL" "ENCRYPTION_KEY")
          for secret in "${SECRETS[@]}"; do
            if [ -n "${!secret}" ]; then
              echo "OK: $secret configurado"
            else
              echo "ERRO: $secret faltando"
              exit 1
            fi
          done

      - name: Deploy
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "Fazendo deploy para ${{ inputs.environment }}..."
          
      - name: Verificar deploy
        run: |
          echo "Verificando integridade do deploy..."
          
          # Health check
          HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://myapp.com/health)
          if [ $HTTP_STATUS -ne 200 ]; then
            echo "ERRO: Health check falhou (HTTP $HTTP_STATUS)"
            exit 1
          fi
          
          echo "Deploy verificado com sucesso"
```

### Monitoring de Secrets em Producao

```yaml
name: Production Secret Monitoring

on:
  schedule:
    - cron: '0 */6 * * *'  # A cada 6 horas

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar saude dos secrets
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          API_KEY: ${{ secrets.API_KEY }}
        run: |
          echo "=== Verificacao de Saude dos Secrets ==="
          
          # Verificar conexao com database
          if [ -n "$DATABASE_URL" ]; then
            echo "DATABASE_URL: Configurado"
          else
            echo "DATABASE_URL: FALTANDO"
          fi
          
          # Verificar API key
          if [ -n "$API_KEY" ]; then
            echo "API_KEY: Configurado"
          else
            echo "API_KEY: FALTANDO"
          fi

      - name: Verificar expiracao
        run: |
          echo "=== Verificacao de Expiracao ==="
          
          # Verificar se secrets estao proximos da expiracao
          echo "Verificando expiracao de secrets..."
          
      - name: Enviar relatorio
        if: always()
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Relatorio de saude dos secrets gerado"}' \
            $SLACK_WEBHOOK
```

### Secret Rotation em Producao

```yaml
name: Production Secret Rotation

on:
  workflow_dispatch:
    inputs:
      secret_name:
        description: 'Nome do secret'
        required: true
      dry_run:
        description: 'Simular rotacao'
        required: true
        type: boolean
        default: true

jobs:
  rotate:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar permissao
        run: |
          if [ "${{ inputs.dry_run }}" = "false" ]; then
            echo "ATENCAO: Rotacao real sera executada"
            echo "Secret: ${{ inputs.secret_name }}"
          else
            echo "SIMULACAO: Nenhuma alteracao sera feita"
          fi

      - name: Gerar novo secret
        run: |
          NEW_SECRET=$(openssl rand -base64 32)
          echo "Novo secret gerado (nao exposto nos logs)"
          
          if [ "${{ inputs.dry_run }}" = "false" ]; then
            echo "Atualizando secret: ${{ inputs.secret_name }}"
            # Logica de atualizacao
          fi

      - name: Notificar
        if: inputs.dry_run == false
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"Secret ${{ inputs.secret_name }} rotacionado em production"}' \
            $SLACK_WEBHOOK
```

---

## 9.18 Exercicios

1. Configure repository secrets e use em um workflow
2. Implemente OIDC com AWS para deploy sem secrets
3. Configure environment secrets para staging e production
4. Implemente secret rotation com GitHub API
5. Integre HashiCorp Vault para secret management
6. Configure organization secrets com visibilidade selecionada
7. Implemente audit log para monitoramento de secrets
8. Configure GitHub App tokens para acesso cross-repo
9. Implemente verificacao de saude de secrets
10. Crie relatorio completo de auditoria de secrets
11. Implemente secret management pattern com AWS Secrets Manager
12. Configure secret rotation automatica com notificacao
13. Implemente secret validation antes de deploy
14. Configure secret backup e recovery
15. Implemente secret access control baseado em branches
16. Configure secrets para diferentes linguagens (Node.js, Python, Go)
17. Implemente pipeline avancado com secret rotation
18. Configure monitoring de secrets em producao

---

## 9.20 Resumo

Neste capitulo, cobrimos todos os aspectos fundamentais e avancados de gerenciamento de secrets no GitHub Actions:

- Repository secrets para armazenamento seguro de credenciais
- Environment secrets para isolar credenciais por ambiente
- Organization secrets para compartilhamento centralizado
- Secret masking para protecao nos logs
- OIDC para autenticacao sem secrets em cloud providers
- GITHUB_TOKEN e custom tokens (PAT, GitHub Apps)
- Secret rotation strategies para manter seguranca
- Audit log para monitoramento e compliance
- Vault integration para secret management avancado
- Padrões de gerenciamento de secrets para producao

A implementacao correta de secret management e critica para a seguranca de qualquer pipeline CI/CD. Sempre siga o principio de least-privilege e audite regularmente o uso de secrets.

---

## 9.21 Referencias

1. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions
2. https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect
3. https://github.com/hashicorp/vault-action
4. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-secrets
5. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#permissions
6. https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-github_token-in-workflows
7. https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
8. https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app
9. https://docs.github.com/en/organizations/managing-organization-settings/managing-security-settings-for-your-organization/requiring-action-approval-for-oidc
10. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
11. https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html
12. https://www.vaultproject.io/docs/secrets/pki
13. https://docs.github.com/en/code-security/secret-scanning
14. https://docs.github.com/en/actions/security-guides/encrypted-secrets
15. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions#using-secrets
---

*[Capítulo anterior: 08 — Artifacts Outputs](08-artifacts-outputs.md)*
*[Próximo capítulo: 10 — Permissions](10-permissions.md)*
