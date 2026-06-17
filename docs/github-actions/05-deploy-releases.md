---
layout: default
title: "05-deploy-releases"
---

# Capitulo 5 — Deploy e Releases

> *"O deploy nao e o fim — e o comeco da confiabilidade."*

---

## Sumario

| Secao | Descricao |
|-------|-----------|
| 5.1 | GitHub Pages |
| 5.2 | Docker Build/Push |
| 5.3 | GitHub Container Registry (GHCR) |
| 5.4 | Cloud Deploy (AWS/Azure/GCP) |
| 5.5 | semantic-release |
| 5.6 | GitHub Releases |
| 5.7 | Environment Protection |
| 5.8 | Deployment Branches |
| 5.9 | Rollback Strategies |
| 5.10 | Blue-Green Deploys |
| 5.11 | Canary Deploys |

---

## Objetivos de Aprendizado

1. Configurar deploy para GitHub Pages com Jekyll e outros geradores
2. Construir e publicar imagens Docker no GHCR e outros registries
3. Implementar deploy para cloud providers (AWS, Azure, GCP)
4. Automatizar releases com semantic-release
5. Criar e gerenciar GitHub Releases com artefatos
6. Configurar environment protection rules com reviewers e wait timers
7. Definir deployment branches para restringir deploys
8. Implementar rollback strategies eficientes
9. Configurar blue-green deploys com health checks
10. Implementar canary deploys com metricas de erro

---

## 5.1 GitHub Pages

GitHub Pages e uma forma simples e gratuita de hospedar sites estaticos diretamente do repositorio. O deploy pode ser automatizado com GitHub Actions.

### 5.1.1 Deploy Basico com Jekyll

```yaml
name: Deploy Pages

on:
  push:
    branches: [main]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/jekyll-build-pages@v1
        with:
          source: ./
          destination: ./_site
      - uses: actions/upload-pages-artifact@v3

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.1.2 Deploy com Next.js

```yaml
name: Deploy Next.js to Pages

on:
  push:
    branches: [main]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

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
      - uses: actions/upload-pages-artifact@v3
        with:
          path: .next

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.1.3 Deploy com Vite

```yaml
name: Deploy Vite to Pages

on:
  push:
    branches: [main]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

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
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.1.4 Deploy com Hugo

```yaml
name: Deploy Hugo to Pages

on:
  push:
    branches: [main]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
          fetch-depth: 0
      - name: Setup Hugo
        uses: peaceiris/actions-hugo@v2
        with:
          hugo-version: 'latest'
          extended: true
      - name: Build
        run: hugo --minify
      - uses: actions/upload-pages-artifact@v3
        with:
          path: public

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.1.5 Deploy com Multiplos Ambientes

```yaml
name: Deploy Pages Multi-Environment

on:
  push:
    branches: [main, staging]

permissions:
  pages: write
  id-token: write

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: false

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

      - name: Set environment
        id: env
        run: |
          if [ "${{ github.ref }}" = "refs/heads/main" ]; then
            echo "environment=production" >> $GITHUB_OUTPUT
          else
            echo "environment=staging" >> $GITHUB_OUTPUT
          fi

      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_ENV: ${{ steps.env.outputs.environment }}

      - uses: actions/upload-pages-artifact@v3
        with:
          path: .next

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages-${{ steps.env.outputs.environment }}
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

### 5.1.6 Tabela de Geradores Estaticos

| Gerador | Linguagem | Comando de Build | Observacao |
|---------|-----------|------------------|------------|
| Jekyll | Ruby | `jekyll build` | Padrao do GitHub |
| Hugo | Go | `hugo --minify` | Muito rapido |
| Next.js | Node.js | `next build` | Suporte SSR/SSG |
| Vite | Node.js | `vite build` | Rapido e moderno |
| Astro | Node.js | `astro build` | Performance otima |
| Gatsby | Node.js | `gatsby build` | Muitos plugins |
| Eleventy | Node.js | `eleventy` | Simples e flexivel |
| Docusaurus | Node.js | `npm run build` | Documentacao |

---

## 5.2 Docker Build/Push

Docker permite empacotar aplicacoes em containers portaveis. O build e push de imagens Docker e uma parte essencial de pipelines de deploy.

### 5.2.1 Dockerfile Basico

```dockerfile
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

### 5.2.2 Docker Build com Buildx

```yaml
name: Docker Build and Push

on:
  push:
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

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

### 5.2.3 Docker Build Multi-Platform

```yaml
name: Docker Multi-Platform Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: myorg/myapp
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: linux/amd64,linux/arm64,linux/arm/v7
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 5.2.4 Docker com Testes

```yaml
name: Docker Build and Test

on: [push, pull_request]

jobs:
  build-and-test:
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
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run tests in container
        run: |
          docker run --rm myapp:test npm test

      - name: Run health check
        run: |
          docker run -d --name test-container -p 3000:3000 myapp:test
          sleep 10
          curl -f http://localhost:3000/health || exit 1
          docker stop test-container
```

### 5.2.5 Docker com Build Args

```yaml
name: Docker with Build Args

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build with args
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: myapp:test
          build-args: |
            NODE_VERSION=20
            BUILD_DATE=${{ github.event.head_commit.timestamp }}
            VCS_REF=${{ github.sha }}
            VERSION=${{ github.ref_name }}
```

### 5.2.6 Docker com Secrets

```yaml
name: Docker with Secrets

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build with secrets
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: myapp:test
          secrets: |
            "npm_token=${{ secrets.NPM_TOKEN }}"
```

### 5.2.7 Tabela de Docker Actions

| Action | Descricao | Versao |
|--------|-----------|--------|
| docker/setup-buildx-action | Configura Docker Buildx | v3 |
| docker/setup-qemu-action | Configura QEMU para multi-platform | v3 |
| docker/login-action | Login em registries | v3 |
| docker/metadata-action | Extrai metadata de tags | v5 |
| docker/build-push-action | Build e push de imagens | v5 |
| docker/build-push-action | Build e push de imagens | v5 |
| docker/actions/docker-compose | Executa docker-compose | - |

---

## 5.3 GitHub Container Registry (GHCR)

GHCR e o registry de containers do GitHub, integrado nativamente com o GitHub Actions e GitHub Packages.

### 5.3.1 GHCR Basico

```yaml
name: Publish to GHCR

on:
  push:
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 5.3.2 GHCR com Package Permissions

```yaml
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4

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
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Sign image
        uses: sigstore/cosign-installer@v3
      - run: cosign sign ghcr.io/${{ github.repository }}:${{ github.ref_name }}
        env:
          COSIGN_EXPERIMENTAL: 1
```

### 5.3.3 GHCR com Multi-Tag

```yaml
name: GHCR Multi-Tag

on:
  push:
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=ref,event=branch
            type=sha,prefix=sha-

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 5.3.4 GHCR com Vulnerability Scanning

```yaml
name: GHCR with Security Scanning

on:
  push:
    tags: ['v*']

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      security-events: write
    steps:
      - uses: actions/checkout@v4

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
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## 5.4 Cloud Deploy (AWS/Azure/GCP)

Deploy para cloud providers e uma parte essencial de pipelines de CI/CD. Cada provider tem suas proprias actions e configuracoes.

### 5.4.1 AWS S3 Deploy

```yaml
deploy-s3:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci && npm run build

    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Deploy to S3
      run: |
        aws s3 sync dist/ s3://my-bucket/ \
          --delete \
          --cache-control "max-age=31536000"
```

### 5.4.2 AWS CloudFront Invalidation

```yaml
deploy-s3:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci && npm run build

    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Deploy to S3
      run: aws s3 sync dist/ s3://my-bucket/ --delete

    - name: Invalidate CloudFront
      run: |
        aws cloudfront create-invalidation \
          --distribution-id ${{ secrets.CLOUDFRONT_DISTRIBUTION_ID }} \
          --paths "/*"
```

### 5.4.3 AWS ECS Deploy

```yaml
deploy-ecs:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Login to ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v2

    - name: Build and push to ECR
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: my-app
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG

    - name: Deploy to ECS
      uses: aws-actions/amazon-ecs-deploy-task-definition@v2
      with:
        task-definition: ecs-task-definition.json
        service: my-service
        cluster: my-cluster
        wait-for-service-stability: true
```

### 5.4.4 Azure Static Web Apps

```yaml
deploy-azure:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build and Deploy
      uses: Azure/static-web-apps-deploy@v1
      with:
        azure_static_web_apps_api_token: ${{ secrets.AZURE_TOKEN }}
        repo_token: ${{ secrets.GITHUB_TOKEN }}
        app_location: "/"
        output_location: "dist"
```

### 5.4.5 Azure App Service

```yaml
deploy-azure-app:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci && npm run build

    - name: Login to Azure
      uses: azure/login@v2
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}

    - name: Deploy to Azure Web App
      uses: azure/webapps-deploy@v3
      with:
        app-name: 'my-app'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        package: dist/
```

### 5.4.6 GCP Cloud Run

```yaml
deploy-gcp:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Login to GCP
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_CREDENTIALS }}

    - name: Setup GCP SDK
      uses: google-github-actions/setup-gcloud@v2
      with:
        project_id: ${{ secrets.GCP_PROJECT }}

    - name: Build and push to GCR
      run: |
        gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT }}/my-app

    - name: Deploy to Cloud Run
      run: |
        gcloud run deploy my-app \
          --image gcr.io/${{ secrets.GCP_PROJECT }}/my-app \
          --platform managed \
          --region us-central1 \
          --allow-unauthenticated
```

### 5.4.7 GCP Cloud Storage

```yaml
deploy-gcs:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: npm ci && npm run build

    - name: Login to GCP
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_CREDENTIALS }}

    - name: Deploy to GCS
      run: |
        gsutil -m rsync -r -d dist/ gs://my-bucket/
```

### 5.4.8 Tabela de Cloud Providers

| Provider | Service | Action | Observacao |
|----------|---------|--------|------------|
| AWS | S3 | aws-actions/configure-aws-credentials | Static hosting |
| AWS | CloudFront | aws cloudfront create-invalidation | CDN invalidation |
| AWS | ECS | aws-actions/amazon-ecs-deploy-task-definition | Container deploy |
| AWS | Lambda | aws-actions/configure-aws-credentials | Serverless |
| Azure | Static Web Apps | Azure/static-web-apps-deploy | Static hosting |
| Azure | App Service | azure/webapps-deploy | Web apps |
| Azure | Container Instances | azure/aci-deploy | Containers |
| GCP | Cloud Run | google-github-actions/deploy-cloudrun | Containers |
| GCP | Cloud Storage | gsutil rsync | Static hosting |
| GCP | App Engine | google-github-actions/deploy-appengine | Web apps |

---

## 5.5 semantic-release

semantic-release automatiza a criacao de versoes e releases baseado em commits convencionais.

### 5.5.1 Configuracao Basica

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

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

      - name: Semantic Release
        uses: cycjimmy/semantic-release-action@v4
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### 5.5.2 Configuracao Avancada

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test

  release:
    needs: test
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

      - name: Semantic Release
        uses: cycjimmy/semantic-release-action@v4
        with:
          branches: |
            [
              'main',
              {name: 'beta', prerelease: true},
              {name: 'alpha', prerelease: true}
            ]
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

### 5.5.3 .releaserc.json

```json
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github",
    [
      "@semantic-release/git",
      {
        "assets": ["package.json", "CHANGELOG.md"],
        "message": "chore(release): ${nextRelease.version}\n\n${nextRelease.notes}"
      }
    ]
  ]
}
```

### 5.5.4 semantic-release com Changelog

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Semantic Release
        uses: cycjimmy/semantic-release-action@v4
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}

      - name: Update Changelog
        run: |
          npx conventional-changelog-cli -p angular -i CHANGELOG.md -s
```

### 5.5.5 semantic-release Multi-Package

```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  issues: write
  pull-requests: write

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

      - name: Release packages
        run: npx lerna version --conventional-commits --yes
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Publish packages
        run: npx lerna publish from-package --yes
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 5.6 GitHub Releases

GitHub Releases permitem criar releases oficiais com notes, artefatos e download links.

### 5.6.1 Release Automatica

```yaml
name: Release

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*
```

### 5.6.2 Release Manual

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag'
        required: true
      prerelease:
        description: 'Is prerelease'
        required: false
        type: boolean
        default: false

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ inputs.version }}
          name: ${{ inputs.version }}
          generate_release_notes: true
          prerelease: ${{ inputs.prerelease }}
          files: dist/*
```

### 5.6.3 Release com Changelog

```yaml
name: Release

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate Changelog
        id: changelog
        run: |
          CHANGELOG=$(git log --pretty=format:"- %s" $(git describe --tags --abbrev=0 HEAD^)..HEAD)
          echo "changelog<<EOF" >> $GITHUB_OUTPUT
          echo "$CHANGELOG" >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          body: |
            ## Changes
            ${{ steps.changelog.outputs.changelog }}
          files: dist/*
```

### 5.6.4 Release com Artefatos Assinados

```yaml
name: Release with Signing

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - name: Import GPG key
        uses: crazy-max/ghaction-import-gpg@v6
        with:
          gpg_private_key: ${{ secrets.GPG_PRIVATE_KEY }}
          passphrase: ${{ secrets.GPG_PASSPHRASE }}

      - name: Sign artifacts
        run: |
          for file in dist/*; do
            gpg --batch --yes --detach-sign "$file"
          done

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*
            dist/*.sig
```

### 5.6.5 Release com Multi-Plataforma

```yaml
name: Release Multi-Platform

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact: linux-amd64
          - os: macos-latest
            artifact: darwin-arm64
          - os: windows-latest
            artifact: windows-amd64
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - name: Create artifact
        run: |
          if [ "${{ matrix.os }}" = "windows-latest" ]; then
            7z a myapp-${{ matrix.artifact }}.zip dist/
          else
            tar -czf myapp-${{ matrix.artifact }}.tar.gz dist/
          fi

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.artifact }}
          path: myapp-${{ matrix.artifact }}.*

  release:
    needs: build
    runs-on: ubuntu-latest
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

## 5.7 Environment Protection

Environment protection rules permitem adicionar camadas de seguranca e aprovacao antes de deploys.

### 5.7.1 Environment Protection Basico

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

### 5.7.2 Environment com Required Reviewers

```yaml
jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

Configuracao no GitHub:
- Settings > Environments > production
- Required reviewers: adicione 1-2 reviewers
- Wait timer: 5-30 minutos de espera
- Deployment branches: restrinja a `main`

### 5.7.3 Environment com Variables

```yaml
jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
        env:
          API_URL: ${{ vars.API_URL }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### 5.7.4 Environment com Wait Timer

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - run: echo "Deploying to staging"

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Waiting 10 minutes before production deploy"
      - name: Wait for approval
        run: sleep 600
      - run: echo "Deploying to production"
```

### 5.7.5 Environment com Deployment Branches

```yaml
jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

Configuracao no GitHub:
- Settings > Environments > production
- Deployment branches: Selected branches
- Branch patterns: `main`, `release/*`

### 5.7.6 Environment com Protection Rules

```yaml
jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - run: echo "Deploying to production"
```

Configuracao no GitHub:
- Settings > Environments > production
- Deployment branches: Selected branches
- Branch patterns: `main`
- Required reviewers: 2 reviewers
- Wait timer: 15 minutes
- Prevent self-review: Yes

---

## 5.8 Deployment Branches

Deployment branches restringem quais branches podem fazer deploy para ambientes especificos.

### 5.8.1 Branch Protection Basico

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - run: echo "Deploying from main"
```

### 5.8.2 Branch Protection com Patterns

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: |
      github.ref == 'refs/heads/main' ||
      startsWith(github.ref, 'refs/heads/release/')
    steps:
      - run: echo "Deploying from main or release branch"
```

### 5.8.3 Branch Protection com Environment

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    if: github.ref == 'refs/heads/develop'
    steps:
      - run: echo "Deploying to staging from develop"

  deploy-production:
    runs-on: ubuntu-latest
    environment: production
    if: github.ref == 'refs/heads/main'
    steps:
      - run: echo "Deploying to production from main"
```

### 5.8.4 Branch Protection com Tag

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/v')
    steps:
      - run: echo "Deploying from tag"
```

### 5.8.5 Branch Protection com Matrix

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - branch: main
            environment: production
          - branch: develop
            environment: staging
          - branch: release/*
            environment: pre-production
    steps:
      - run: echo "Deploying to ${{ matrix.environment }}"
```

---

## 5.9 Rollback Strategies

Rollback strategies sao planos de contingencia para reverter deploys problematicos.

### 5.9.1 Git Revert + Redeploy

```yaml
jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.inputs.previous_version }}
      - run: npm ci && npm run build
      - name: Deploy previous version
        run: ./deploy.sh
```

### 5.9.2 Rollback com Tag

```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to rollback to'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}
      - run: npm ci && npm run build
      - name: Deploy rollback
        run: ./deploy.sh
```

### 5.9.3 Rollback com Image

```yaml
on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker image tag to rollback to'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy previous image
        run: |
          kubectl set image deployment/myapp \
            myapp=ghcr.io/myorg/myapp:${{ inputs.image_tag }}
```

### 5.9.4 Automatic Rollback

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - name: Deploy
        id: deploy
        run: ./deploy.sh

      - name: Health check
        id: health
        run: |
          sleep 30
          if ! curl -f https://example.com/health; then
            echo "Health check failed"
            echo "rollback=true" >> $GITHUB_OUTPUT
          fi

      - name: Rollback
        if: steps.health.outputs.rollback == 'true'
        run: ./rollback.sh
```

### 5.9.5 Rollback com Notification

```yaml
jobs:
  rollback:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.version }}

      - name: Deploy previous version
        run: ./deploy.sh

      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Rollback executed to version ${{ inputs.version }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 5.10 Blue-Green Deploys

Blue-green deploys mantem duas copias da aplicacao e alternam o trafego entre elas.

### 5.10.1 Blue-Green Basico

```yaml
jobs:
  blue-green:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to green
        run: ./deploy-to-green.sh

      - name: Health check
        run: ./health-check.sh green

      - name: Switch traffic
        run: ./switch-traffic.sh green

      - name: Keep blue as fallback
        run: echo "Blue available for rollback"
```

### 5.10.2 Blue-Green com Health Checks

```yaml
jobs:
  blue-green:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to green
        run: ./deploy-to-green.sh

      - name: Wait for startup
        run: sleep 30

      - name: Health check
        id: health
        run: |
          for i in {1..10}; do
            if curl -f http://green.example.com/health; then
              echo "healthy=true" >> $GITHUB_OUTPUT
              exit 0
            fi
            sleep 5
          done
          echo "healthy=false" >> $GITHUB_OUTPUT

      - name: Switch traffic
        if: steps.health.outputs.healthy == 'true'
        run: ./switch-traffic.sh green

      - name: Rollback
        if: steps.health.outputs.healthy == 'false'
        run: |
          ./cleanup-green.sh
          echo "Rollback to blue"
```

### 5.10.3 Blue-Green com Traffic Switch

```yaml
jobs:
  blue-green:
    runs-on: ubuntu-latest
    steps:
      - name: Determine active slot
        id: slot
        run: |
          ACTIVE=$(curl -s https://example.com/api/active-slot)
          if [ "$ACTIVE" = "blue" ]; then
            echo "deploy_to=green" >> $GITHUB_OUTPUT
            echo "switch_to=green" >> $GITHUB_OUTPUT
          else
            echo "deploy_to=blue" >> $GITHUB_OUTPUT
            echo "switch_to=blue" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to ${{ steps.slot.outputs.deploy_to }}
        run: ./deploy.sh ${{ steps.slot.outputs.deploy_to }}

      - name: Health check
        run: |
          curl -f http://${{ steps.slot.outputs.deploy_to }}.example.com/health

      - name: Switch traffic
        run: |
          curl -X POST https://example.com/api/switch-slot \
            -d '{"slot": "${{ steps.slot.outputs.switch_to }}"}'
```

### 5.10.4 Blue-Green com Database Migration

```yaml
jobs:
  blue-green:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to green
        run: ./deploy-to-green.sh

      - name: Run database migrations
        run: ./migrate-database.sh

      - name: Health check
        run: ./health-check.sh green

      - name: Switch traffic
        run: ./switch-traffic.sh green

      - name: Verify deployment
        run: ./verify-deployment.sh

      - name: Cleanup old version
        run: ./cleanup-old-version.sh
```

---

## 5.11 Canary Deploys

Canary deploys liberam mudancas gradualmente para uma pequena porcao dos usuarios antes de disponibilizar para todos.

### 5.11.1 Canary Basico

```yaml
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary (10%)
        run: ./deploy-canary.sh 10

      - name: Monitor canary
        run: |
          sleep 300
          ./monitor-canary.sh

      - name: Promote to full
        run: ./promote-canary.sh
```

### 5.11.2 Canary com Metricas

```yaml
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary (10%)
        run: ./deploy-canary.sh 10

      - name: Wait for metrics
        run: sleep 600

      - name: Check error rate
        id: metrics
        run: |
          ERROR_RATE=$(curl -s https://metrics.example.com/error-rate)
          if (( $(echo "$ERROR_RATE > 5.0" | bc -l) )); then
            echo "rollback=true" >> $GITHUB_OUTPUT
          else
            echo "rollback=false" >> $GITHUB_OUTPUT
          fi

      - name: Rollback canary
        if: steps.metrics.outputs.rollback == 'true'
        run: ./rollback-canary.sh

      - name: Promote canary
        if: steps.metrics.outputs.rollback == 'false'
        run: ./promote-canary.sh
```

### 5.11.3 Canary com Gradual Rollout

```yaml
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary (5%)
        run: ./deploy-canary.sh 5
        id: deploy

      - name: Monitor 5%
        run: sleep 300

      - name: Increase to 25%
        run: ./update-canary.sh 25

      - name: Monitor 25%
        run: sleep 300

      - name: Increase to 50%
        run: ./update-canary.sh 50

      - name: Monitor 50%
        run: sleep 300

      - name: Increase to 100%
        run: ./promote-canary.sh
```

### 5.11.4 Canary com Alertas

```yaml
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary
        run: ./deploy-canary.sh 10

      - name: Monitor and alert
        run: |
          for i in {1..6}; do
            sleep 60
            ERROR_RATE=$(curl -s https://metrics.example.com/error-rate)
            if (( $(echo "$ERROR_RATE > 5.0" | bc -l) )); then
              echo "High error rate detected: $ERROR_RATE%"
              ./send-alert.sh "Canary deployment error rate: $ERROR_RATE%"
              ./rollback-canary.sh
              exit 1
            fi
          done

      - name: Promote canary
        run: ./promote-canary.sh
```

### 5.11.5 Canary com Service Mesh

```yaml
jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy canary version
        run: |
          kubectl apply -f canary-deployment.yaml

      - name: Configure traffic split
        run: |
          kubectl apply -f virtual-service.yaml

      - name: Monitor canary
        run: sleep 600

      - name: Check metrics
        id: check
        run: |
          if ./check-canary-metrics.sh; then
            echo "success=true" >> $GITHUB_OUTPUT
          else
            echo "success=false" >> $GITHUB_OUTPUT
          fi

      - name: Promote to stable
        if: steps.check.outputs.success == 'true'
        run: |
          kubectl apply -f stable-deployment.yaml
          kubectl delete -f canary-deployment.yaml

      - name: Rollback
        if: steps.check.outputs.success == 'false'
        run: |
          kubectl delete -f canary-deployment.yaml
          kubectl delete -f virtual-service.yaml
```

### 5.11.6 Tabela de Deploy Strategies

| Estrategia | Risco | Downtime | Rollback | Complexidade |
|------------|-------|----------|----------|--------------|
| Recreate | Alto | Sim | Rapido | Baixa |
| Rolling | Baixo | Nao | Medio | Media |
| Blue-Green | Baixo | Nao | Rapido | Media |
| Canary | Muito Baixo | Nao | Rapido | Alta |
| A/B Testing | Baixo | Nao | Rapido | Alta |

---

## 5.12 Exemplos de Casos Reais

### 5.12.1 Pipeline Completa de Deploy Full Stack

Pipeline completa para deploy de aplicacao full stack com frontend, backend e infraestrutura.

```yaml
name: Full Stack Deploy

on:
  push:
    tags: ['v*']

permissions:
  contents: write
  packages: write
  id-token: write

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:ci

  build-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:frontend
      - uses: actions/upload-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
          retention-days: 1

  build-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build:backend
      - uses: actions/upload-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/
          retention-days: 1

  build-docker:
    needs: [build-frontend, build-backend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: frontend-dist
          path: packages/frontend/dist/
      - uses: actions/download-artifact@v4
        with:
          name: backend-dist
          path: packages/backend/dist/

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: build-docker
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          kubectl set image deployment/myapp \
            myapp=ghcr.io/${{ env.IMAGE_NAME }}:${{ github.ref_name }} \
            --namespace=staging

      - name: Verify staging
        run: |
          sleep 60
          curl -f https://staging.example.com/health

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp \
            myapp=ghcr.io/${{ env.IMAGE_NAME }}:${{ github.ref_name }} \
            --namespace=production

      - name: Verify production
        run: |
          sleep 60
          curl -f https://example.com/health

      - name: Notify success
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Production deploy successful: ${{ github.ref_name }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

  rollback:
    needs: deploy-production
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Rollback production
        run: |
          kubectl rollout undo deployment/myapp --namespace=production

      - name: Notify rollback
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Production rollback executed for ${{ github.ref_name }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### 5.12.2 Pipeline de Deploy para Monorepo

Pipeline completa para deploy de monorepo com multiplos servicos.

```yaml
name: Monorepo Deploy

on:
  push:
    tags: ['v*']

permissions:
  contents: write
  packages: write

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.changes.outputs.api }}
      web: ${{ steps.changes.outputs.web }}
      worker: ${{ steps.changes.outputs.worker }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            api:
              - 'services/api/**'
            web:
              - 'services/web/**'
            worker:
              - 'services/worker/**'

  build-api:
    needs: detect-changes
    if: needs.detect-changes.outputs.api == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
        working-directory: services/api
      - run: npm run build
        working-directory: services/api

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push API
        uses: docker/build-push-action@v5
        with:
          context: services/api
          push: true
          tags: ghcr.io/${{ github.repository }}/api:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-web:
    needs: detect-changes
    if: needs.detect-changes.outputs.web == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
        working-directory: services/web
      - run: npm run build
        working-directory: services/web

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Web
        uses: docker/build-push-action@v5
        with:
          context: services/web
          push: true
          tags: ghcr.io/${{ github.repository }}/web:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-worker:
    needs: detect-changes
    if: needs.detect-changes.outputs.worker == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r services/worker/requirements.txt

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Worker
        uses: docker/build-push-action@v5
        with:
          context: services/worker
          push: true
          tags: ghcr.io/${{ github.repository }}/worker:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: [build-api, build-web, build-worker]
    if: always() && !contains(needs.*.result, 'failure')
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Deploy API
        if: needs.build-api.result == 'success'
        run: |
          kubectl set image deployment/api \
            api=ghcr.io/${{ github.repository }}/api:${{ github.ref_name }}

      - name: Deploy Web
        if: needs.build-web.result == 'success'
        run: |
          kubectl set image deployment/web \
            web=ghcr.io/${{ github.repository }}/web:${{ github.ref_name }}

      - name: Deploy Worker
        if: needs.build-worker.result == 'success'
        run: |
          kubectl set image deployment/worker \
            worker=ghcr.io/${{ github.repository }}/worker:${{ github.ref_name }}

      - name: Verify deployment
        run: |
          sleep 60
          curl -f https://example.com/health
```

### 5.12.3 Pipeline de Deploy com Database Migration

Pipeline completa para deploy com migracao de banco de dados.

```yaml
name: Deploy with DB Migration

on:
  push:
    tags: ['v*']

permissions:
  contents: write
  packages: write

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
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  backup-database:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Backup database
        run: |
          pg_dump $DATABASE_URL > backup-${{ github.ref_name }}.sql
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

      - uses: actions/upload-artifact@v4
        with:
          name: db-backup
          path: backup-*.sql
          retention-days: 30

  run-migrations:
    needs: backup-database
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Run migrations
        run: |
          docker run --rm \
            -e DATABASE_URL=$DATABASE_URL \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }} \
            npm run migrate
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  deploy:
    needs: run-migrations
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy new version
        run: |
          kubectl set image deployment/myapp \
            myapp=ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Verify deployment
        run: |
          sleep 60
          curl -f https://example.com/health

  rollback:
    needs: deploy
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - name: Rollback deployment
        run: |
          kubectl rollout undo deployment/myapp

      - name: Rollback database
        run: |
          psql $DATABASE_URL < backup-${{ github.ref_name }}.sql
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### 5.12.4 Pipeline de Deploy com Feature Flags

Pipeline completa para deploy com feature flags.

```yaml
name: Deploy with Feature Flags

on:
  push:
    tags: ['v*']

permissions:
  contents: write
  packages: write

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
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-canary:
    needs: build
    runs-on: ubuntu-latest
    environment: canary
    steps:
      - uses: actions/checkout@v4

      - name: Deploy canary
        run: |
          kubectl set image deployment/myapp-canary \
            myapp=ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Enable canary feature flags
        run: |
          curl -X POST https://flags.example.com/api/enable \
            -H "Authorization: Bearer ${{ secrets.FLAGS_TOKEN }}" \
            -d '{"flag": "new_feature", "percentage": 10}'

  monitor-canary:
    needs: deploy-canary
    runs-on: ubuntu-latest
    steps:
      - name: Wait for metrics
        run: sleep 300

      - name: Check error rate
        id: metrics
        run: |
          ERROR_RATE=$(curl -s https://metrics.example.com/error-rate)
          if (( $(echo "$ERROR_RATE > 5.0" | bc -l) )); then
            echo "rollback=true" >> $GITHUB_OUTPUT
          else
            echo "rollback=false" >> $GITHUB_OUTPUT
          fi

      - name: Rollback canary
        if: steps.metrics.outputs.rollback == 'true'
        run: |
          kubectl delete deployment myapp-canary
          curl -X POST https://flags.example.com/api/disable \
            -H "Authorization: Bearer ${{ secrets.FLAGS_TOKEN }}" \
            -d '{"flag": "new_feature"}'

  deploy-production:
    needs: monitor-canary
    if: steps.metrics.outputs.rollback == 'false'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Deploy production
        run: |
          kubectl set image deployment/myapp \
            myapp=ghcr.io/${{ github.repository }}:${{ github.ref_name }}

      - name: Enable feature flags
        run: |
          curl -X POST https://flags.example.com/api/enable \
            -H "Authorization: Bearer ${{ secrets.FLAGS_TOKEN }}" \
            -d '{"flag": "new_feature", "percentage": 100}'

      - name: Verify deployment
        run: |
          sleep 60
          curl -f https://example.com/health
```

### 5.12.5 Pipeline de Deploy com Terraform

Pipeline completa para deploy com Terraform Infrastructure as Code.

```yaml
name: Deploy with Terraform

on:
  push:
    tags: ['v*']

permissions:
  contents: write
  packages: write
  id-token: write

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
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  plan-infrastructure:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Terraform Init
        run: terraform init
        working-directory: infrastructure

      - name: Terraform Plan
        run: |
          terraform plan \
            -var="image_tag=${{ github.ref_name }}" \
            -out=tfplan
        working-directory: infrastructure

      - uses: actions/upload-artifact@v4
        with:
          name: tfplan
          path: infrastructure/tfplan
          retention-days: 1

  deploy-infrastructure:
    needs: plan-infrastructure
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Terraform Init
        run: terraform init
        working-directory: infrastructure

      - uses: actions/download-artifact@v4
        with:
          name: tfplan
          path: infrastructure/

      - name: Terraform Apply
        run: terraform apply -auto-approve tfplan
        working-directory: infrastructure

      - name: Verify deployment
        run: |
          sleep 60
          curl -f https://example.com/health

  rollback:
    needs: deploy-infrastructure
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "1.7.0"

      - name: Terraform Init
        run: terraform init
        working-directory: infrastructure

      - name: Terraform Apply Previous
        run: |
          terraform apply -auto-approve \
            -var="image_tag=${{ github.event.inputs.previous_version }}"
        working-directory: infrastructure
```

---

## 5.14 Comparacao Detalhada de Estrategias de Deploy

### 5.14.1 Tabela de Comparacao

| Caracteristica | Recreate | Rolling Update | Blue-Green | Canary | A/B Testing |
|----------------|----------|----------------|------------|--------|-------------|
| Downtime | Sim | Nao | Nao | Nao | Nao |
| Risco | Alto | Baixo | Baixo | Muito Baixo | Baixo |
| Velocidade | Rapida | Media | Media | Lenta | Lenta |
| Rollback | Rapido | Medio | Rapido | Rapido | Rapido |
| Custo | Baixo | Baixo | Alto (2x infra) | Medio | Alto |
| Complexidade | Baixa | Media | Media | Alta | Alta |
| Uso ideal | Dev/Test | Producao | Producao critica | Producao critica | Feature testing |

### 5.14.2 Quando Usar Cada Estrategia

**Recreate**: Quando a aplicacao nao pode rodar em versoes diferentes simultaneamente. Comum em aplicacoes legadas com dependencias de banco de dados.

**Rolling Update**: Para a maioria dos casos de uso. Equilibrio entre velocidade e seguranca. O Kubernetes usa esta estrategia por padrao.

**Blue-Green**: Para aplicacoes criticas que precisam de rollback instantaneo. Quando voce tem infraestrutura suficiente para manter duas copias.

**Canary**: Para mudancas de alto risco onde voce quer validar com trafego real antes de liberar para todos. Comum em servicos de alto volume.

**A/B Testing**: Quando voce quer testar funcionalidades especificas com segmentos de usuarios antes de liberar para todos.

### 5.14.3 Decisoes de Arquitetura

| Decisao | Recomendacao |
|---------|--------------|
| Infraestrutura limitada | Rolling Update |
| Deploy critico | Blue-Green ou Canary |
| Feature testing | A/B Testing |
| Validacao gradual | Canary |
| Rollback rapido | Blue-Green |
| Custo controlado | Rolling Update |
| Alto trafego | Canary |

---

## 5.15 Exercicios

1. Configure deploy para GitHub Pages com Jekyll
2. Crie um pipeline Docker build + push para GHCR com versionamento semver
3. Implemente release automation com semantic-release
4. Configure environment protection com required reviewers
5. Implemente blue-green deploy com health checks
6. Configure canary deploy com metricas de erro
7. Implemente rollback automatico baseado em health checks
8. Configure deploy multi-platform com Docker Buildx
9. Implemente deploy para AWS S3 com CloudFront invalidation
10. Configure deployment branches para restringir deploys
11. Implemente pipeline completa de deploy full stack com testes
12. Configure deploy com database migration e backup
13. Implemente deploy com feature flags e canary
14. Configure deploy com Terraform Infrastructure as Code
15. Implemente rollback automatico com notificacao Slack

---

## 5.16 Checklist de Deploy

Antes de qualquer deploy em producao, verifique os seguintes pontos:

| Item | Verificado |
|------|------------|
| Testes unitarios passando | [ ] |
| Testes de integracao passando | [ ] |
| Testes E2E passando | [ ] |
| Code coverage >= 80% | [ ] |
| Lint sem erros | [ ] |
| Type check sem erros | [ ] |
| Build completo | [ ] |
| Security scan sem criticos | [ ] |
| Database backup realizado | [ ] |
| Rollback testado | [ ] |
| Health check configurado | [ ] |
| Monitoring configurado | [ ] |
| Alerts configurados | [ ] |
| Documentation atualizada | [ ] |
| Changelog atualizado | [ ] |

---

## 5.17 Fluxo de Deploy Completo

```
                    ┌─────────────┐
                    │   Push/Tag   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Build     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    Tests     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Security   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Package   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │   Staging    │ │ Docker│ │  Artifact   │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  Approval   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Deploy     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Verify     │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Monitor    │
                    └─────────────┘
```

---

## 5.18 Referencias

1. https://docs.github.com/en/pages
2. https://github.com/docker/build-push-action
3. https://github.com/softprops/action-gh-release
4. https://github.com/cycjimmy/semantic-release-action
5. https://docs.github.com/en/actions/deployment/targeting-different-environments
6. https://docs.github.com/en/actions/deployment/using-environments-for-deployment
7. https://github.com/aws-actions/configure-aws-credentials
8. https://github.com/Azure/static-web-apps-deploy
9. https://github.com/google-github-actions/deploy-cloudrun
10. https://docs.github.com/en/actions/publishing-packages/publishing-docker-images
11. https://github.com/docker/metadata-action
12. https://github.com/softprops/action-gh-release
13. https://github.com/sigstore/cosign-installer
14. https://github.com/aquasecurity/trivy-action
15. https://github.com/hashicorp/setup-terraform

---

## 5.19 Glossario de Deploy

| Termo | Definicao |
|-------|-----------|
| Artifact | Arquivo gerado durante o build que sera distribuido |
| Canary | Deploy gradual para uma pequena porcao de usuarios |
| CD (Continuous Delivery) | Entrega continua de software |
| CI (Continuous Integration) | Integracao continua de codigo |
| Container | Empacotamento padronizado de aplicacao |
| Deployment | Processo de colocar software em producao |
| Environment | Ambiente de execucao (dev, staging, production) |
| GitOps | Gerenciamento de infraestrutura via Git |
| Health Check | Verificacao de saude da aplicacao |
| Image | Template para criacao de containers |
| Manifest | Arquivo de configuracao de deploy (Kubernetes, etc.) |
| Migration | Mudanca estrutural no banco de dados |
| Namespace | Isolamento logico de recursos no Kubernetes |
| Registry | Repositorio de imagens Docker |
| Replica | Copia de um container em execucao |
| Rollback | Reversao para versao anterior |
| Scaling | Aumento ou diminuicao de replicas |
| Service Mesh | Camada de comunicacao entre servicos |
| Tag | Versao ou rotulo de uma imagem Docker |
| Traffic Split | Divisao de trafego entre versoes |
| Virtual Service | Configuracao de roteamento no Istio |
| Volume | Armazenamento persistente para containers |
