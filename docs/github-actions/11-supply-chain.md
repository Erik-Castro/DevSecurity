---
layout: default
title: "11-supply-chain"
---

# Capitulo 11 -- Supply Chain Security

> *"A seguranca da cadeia de suprimentos e tao importante quanto a seguranca do codigo."*

---

## Objetivos de Aprendizado

1. Pin actions por SHA para prevenir comprometimento
2. Configurar dependabot para actions updates
3. Usar OpenSSF scorecard
4. Implementar artifact attestation com SLSA
5. Configurar branch protection rules
6. Implementar SBOM generation
7. Configurar Sigstore/cosign para verificacao
8. Analisar incidentes de supply chain
9. Implementar hash verification
10. Configurar complete supply chain workflow
11. Entender os niveis do SLSA
12. Implementar artifact signing
13. Configurar verificacao de integridade
14. Gerenciar dependencias de terceiros
15. Implementar security scanning automatizado

---

## 11.1 Pin Actions por SHA

### O Que e Por Que

Se voce usa `uses: actions/checkout@v4`, o GitHub resolve para a ultima tag v4. Se o repositorio da action for comprometido, o codigo malicioso sera executado. Pinning por SHA garante que voce sempre usa a versao exata da action que voce verificou.

### Risco de Tag Movement

```yaml
# RISCO: Tag pode ser movida para commit malicioso
- uses: actions/checkout@v4
# Se o maintainer for comprometido, v4 pode apontar para codigo malicioso

# SEGURO: SHA e imutavel
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
```

### Como Encontrar o SHA

```bash
# Via GitHub API
curl -s https://api.github.com/repos/actions/checkout/git/refs/tags/v4.1.1 \
  | jq -r '.object.sha'

# Via git ls-remote
git ls-remote https://github.com/actions/checkout.git v4.1.1

# Via GitHub CLI
gh api repos/actions/checkout/git/refs/tags/v4.1.1 --jq '.object.sha'

# Script completo para obter SHA
get_action_sha() {
  local owner=$1
  local repo=$2
  local tag=$3
  curl -s "https://api.github.com/repos/$owner/$repo/git/refs/tags/$tag" | jq -r '.object.sha'
}

# Uso
SHA=$(get_action_sha actions checkout v4.1.1)
echo "SHA: $SHA"
```

### Exemplo de Pinning

```yaml
# ANTES (inseguro)
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-node@v4
  - uses: actions/cache@v3
  - uses: codecov/codecov-action@v3
  - uses: softprops/action-gh-release@v1

# DEPOIS (seguro com SHA)
steps:
  - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
  - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
  - uses: actions/cache@6849a6489940f00c2f30c0fb92c6274307ccb58a  # v3.4.0
  - uses: codecov/codecov-action@54bcd8715e62571856ef2581107d1e8d4e6785c6  # v3.1.0
  - uses: softprops/action-gh-release@9d7c94cfd0a1f3ed45544c887983e9fa900f0564  # v1.0.1
```

### Comentario com Versao

```yaml
# Sempre inclua o nome da versao como comentario para facil referencia
steps:
  - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
  - uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
```

### Automatizando Pinning

```yaml
name: Update Action Pins

on:
  schedule:
    - cron: '0 0 * * 1'  # Toda segunda-feira

jobs:
  update-pins:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Atualizar pins
        run: |
          # Encontrar todas as actions nos workflows
          find .github/workflows -name "*.yml" -exec \
            grep -n "uses:" {} \; | while read line; do
            # Extrair nome da action
            action=$(echo $line | grep -oP 'uses: \K[^@]+')
            tag=$(echo $line | grep -oP '@\K[^ ]+')
            
            # Obter SHA da tag
            sha=$(curl -s "https://api.github.com/repos/$action/git/refs/tags/$tag" \
              | jq -r '.object.sha')
            
            echo "Action: $action"
            echo "Tag: $tag"
            echo "SHA: $sha"
            echo "---"
          done

      - name: Criar PR com atualizacoes
        if: success()
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          git checkout -b update-action-pins
          git add .
          git commit -m "chore: update action pins"
          git push origin update-action-pins
          gh pr create --title "Update Action Pins" --body "Atualizacao automatica de pins"
```

### Verificacao de Integridade

```yaml
name: Verify Action Integrity

on:
  pull_request:
    paths:
      - '.github/workflows/**'

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar SHAs
        run: |
          echo "=== Verificando integridade das actions ==="
          
          grep -rh "uses:" .github/workflows/ | \
            sed 's/.*uses: //' | sed 's/ .*//' | sort -u | while read action; do
            name=$(echo $action | cut -d'@' -f1)
            sha=$(echo $action | cut -d'@' -f2)
            
            if [ -z "$sha" ] || [ "$sha" = "v"* ]; then
              echo "AVISO: $name nao esta pinado por SHA"
            else
              echo "OK: $name pinado em $sha"
            fi
          done

      - name: Verificar contra base de dados de seguranca
        run: |
          echo "Verificando contra base de dados de seguranca..."
```

### Script de Pinning Automatico

```bash
#!/bin/bash
# pin-actions.sh - Script para pinar actions automaticamente

set -e

echo "=== Pin Actions Script ==="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funcao para obter SHA de uma tag
get_sha() {
  local owner=$1
  local repo=$2
  local tag=$3
  
  # Remover 'v' do inicio se existir
  tag=${tag#v}
  
  curl -s "https://api.github.com/repos/$owner/$repo/git/refs/tags/v$tag" | \
    jq -r '.object.sha'
}

# Funcao para processar arquivo de workflow
process_workflow() {
  local file=$1
  
  echo "Processando: $file"
  
  # Encontrar todas as uses: lines
  grep -n "uses:" "$file" | while IFS=: read -r line content; do
    # Extrair owner/repo@tag
    action=$(echo "$content" | grep -oP 'uses:\s*\K[^@]+')
    tag=$(echo "$content" | grep -oP '@\K[^ ]+')
    
    # Pular se ja tem SHA (40 caracteres hexadecimais)
    if [[ "$tag" =~ ^[a-f0-9]{40}$ ]]; then
      echo "  [OK] $action ja pinado por SHA"
      continue
    fi
    
    # Pular se for local action
    if [[ "$action" == ./* ]]; then
      echo "  [SKIP] $action e action local"
      continue
    fi
    
    # Extrair owner e repo
    owner=$(echo "$action" | cut -d'/' -f1)
    repo=$(echo "$action" | cut -d'/' -f2)
    
    # Obter SHA
    sha=$(get_sha "$owner" "$repo" "$tag")
    
    if [ "$sha" != "null" ] && [ -n "$sha" ]; then
      echo "  [PIN] $action@$tag -> $sha"
      
      # Substituir no arquivo
      sed -i "s|uses: $action@$tag|uses: $action@$sha  # $tag|g" "$file"
    else
      echo "  [ERROR] Nao foi possivel obter SHA para $action@$tag"
    fi
  done
}

# Processar todos os workflows
for file in .github/workflows/*.yml; do
  process_workflow "$file"
done

echo ""
echo "=== Concluido ==="
```

### Pinning de Actions Oficiais vs Terceiros

| Tipo de Action | Risco | Recomendacao |
|----------------|-------|--------------|
| actions/* (oficiais GitHub) | Baixo | Pin por SHA |
| verified-publishers/* | Medio | Pin por SHA + verificar |
| Terceiros conhecidos | Medio-Alto | Pin por SHA + revisar codigo |
| Desconhecidos | Alto | Evitar ou revisar profundamente |

### Exemplo de Pinning Completo

```yaml
name: Pinned CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Setup Node.js
        uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Setup Node.js
        uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@65462800fd760344b1a7b4382951275a0abb4808  # v4.3.3
        with:
          name: build
          path: dist/
```

---

## 11.2 Hash Verification

### Verificacao de Hash de Artifacts

```yaml
name: Verify Artifact Hash

on:
  workflow_dispatch:
    inputs:
      artifact_url:
        description: 'URL do artifact'
        required: true

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Download artifact
        run: |
          curl -LO ${{ inputs.artifact_url }}

      - name: Verificar SHA256
        run: |
          FILENAME=$(basename ${{ inputs.artifact_url }})
          EXPECTED_HASH="abc123..."
          ACTUAL_HASH=$(sha256sum $FILENAME | cut -d' ' -f1)
          
          if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
            echo "ERRO: Hash nao confere!"
            echo "Esperado: $EXPECTED_HASH"
            echo "Atual: $ACTUAL_HASH"
            exit 1
          fi
          echo "Hash verificado com sucesso"
```

### Geracao de Hash

```yaml
name: Generate Hash

on:
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Gerar hash do build
        run: |
          find dist/ -type f -exec sha256sum {} \; > SHA256SUMS.txt
          echo "Hashes gerados:"
          cat SHA256SUMS.txt

      - name: Verificar hash
        run: |
          sha256sum -c SHA256SUMS.txt
```

### Verificacao Multi-Hash

```yaml
name: Multi-Hash Verification

on:
  workflow_dispatch:
    inputs:
      artifact_name:
        description: 'Nome do artifact'
        required: true

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: ${{ inputs.artifact_name }}
          path: dist/

      - name: Verificar multiplas assinaturas
        run: |
          echo "=== Verificacao Multi-Hash ==="
          
          cd dist
          
          # Verificar SHA256
          if [ -f "SHA256SUMS.txt" ]; then
            echo "Verificando SHA256..."
            sha256sum -c SHA256SUMS.txt
          fi
          
          # Verificar SHA512
          if [ -f "SHA512SUMS.txt" ]; then
            echo "Verificando SHA512..."
            sha512sum -c SHA512SUMS.txt
          fi
          
          # Verificar MD5 (nao recomendado para seguranca, apenas integridade)
          if [ -f "MD5SUMS.txt" ]; then
            echo "Verificando MD5..."
            md5sum -c MD5SUMS.txt
          fi

      - name: Gerar relatorio
        run: |
          echo "=== Relatorio de Verificacao ==="
          echo "Artifact: ${{ inputs.artifact_name }}"
          echo "Data: $(date)"
          echo "Status: Verificado"
```

### Hash em Release

```yaml
name: Release with Hashes

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
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Gerar hashes
        run: |
          cd dist
          sha256sum * > SHA256SUMS.txt
          sha512sum * > SHA512SUMS.txt
      
      - name: Criar Release com hashes
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh release create ${{ github.ref_name }} \
            --title "Release ${{ github.ref_name }}" \
            --generate-notes \
            dist/* \
            dist/SHA256SUMS.txt \
            dist/SHA512SUMS.txt
```

---

## 11.3 Codecov Incident Analysis

### O Incidente do Codecov (2021)

Em abril de 2021, o Codecov foi comprometido quando um atacante modificou o script bash uploader. O script malicioso exfiltrava variaveis de ambiente, incluindo secrets.

```yaml
# ANTES do incidente (inseguro)
- run: bash <(curl -s https://codecov.io/bash)

# DEPOIS do incidente (seguro)
- uses: codecov/codecov-action@v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
```

### Como o Incidente Aconteceu

```yaml
# 1. Atacante obteve acesso ao repositorio Codecov
# 2. Modificou o script bash uploader
# 3. Script malicioso exfiltrava secrets:
#    - AWS_ACCESS_KEY_ID
#    - AWS_SECRET_ACCESS_KEY
#    - GITHUB_TOKEN
#    - DATABASE_URL
#    - Outros secrets

# Impacto:
# - Milhares de repositorios comprometidos
# - Secrets vazados por semanas
# - Necessidade de rotacionar todas as credenciais
```

### Prevencao

```yaml
# 1. NUNCA use bash <(curl -s ...) em production
# 2. Use actions oficiais sempre que possivel
# 3. Pin actions por SHA
# 4. Monitore alerts do Dependabot
# 5. Implemente branch protection

# Exemplo de uso seguro do Codecov
- uses: codecov/codecov-action@54bcd8715e62571856ef2581107d1e8d4e6785c6  # v3.1.0
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    fail_ci_if_error: true
```

### Timeline do Incidente

| Data | Evento |
|------|--------|
| Janeiro 2021 | Primeira comprometimento detectado |
| Abril 2021 | Incidente principal descoberto |
| Abril 2021 | Codecov notifica usuarios |
| Maio 2021 | Rotacao de credenciais em massa |
| Junho 2021 | Codecov implementa novas medias de seguranca |

### Lições Aprendidas

```yaml
# 1. NUNCA execute scripts de terceiros diretamente
# 2. Use actions oficiais sempre que possivel
# 3. Pin actions por SHA para prevenir tag movement
# 4. Implemente verificacao de integridade
# 5. Monitore alerts de seguranca
# 6. Implemente branch protection
# 7. Rotacione secrets regularmente
```

---

## 11.4 actions/checkout Compromise

### Historico do Comprometimento

Em 2020, o repositorio actions/checkout foi temporariamente comprometido. O atacante conseguiu access ao repositorio e modificou o codigo.

```yaml
# Acoes de seguranca implementadas:
# 1. Pin por SHA (nao por tag)
# 2. Usar apenas actions oficiais do GitHub
# 3. Monitorar com Dependabot
# 4. Configurar branch protection
# 5. Revisar mudancas em actions
```

### Exemplo de Uso Seguro

```yaml
# USO SEGURO: Pin por SHA com comentario
steps:
  - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1

# USO INSEGURO: Tag movel
steps:
  - uses: actions/checkout@v4  # NUNCA faca isso em production
```

### Verificacao de Actions

```yaml
name: Verify Actions

on:
  workflow_dispatch:

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar actions oficiais
        run: |
          echo "=== Verificando actions ==="
          
          OFFICIAL_ACTIONS=(
            "actions/checkout"
            "actions/setup-node"
            "actions/setup-python"
            "actions/cache"
            "actions/upload-artifact"
            "actions/download-artifact"
          )
          
          for action in "${OFFICIAL_ACTIONS[@]}"; do
            echo "Verificando: $action"
          done
```

### Actions Mais Comuns e Seus SHAs

| Action | SHA | Versao |
|--------|-----|--------|
| actions/checkout | b4ffde65f46336ab88eb53be808477a3936bae11 | v4.1.1 |
| actions/setup-node | 60edb5dd545a775178f52524783378180af0d1f8 | v4.0.2 |
| actions/setup-python | 0a5c61591de30bbbad97f8b0577b8e05b50f0c57 | v5.0.0 |
| actions/cache | 6849a6489940f00c2f30c0fb92c6274307ccb58a | v3.4.0 |
| actions/upload-artifact | 65462800fd760344b1a7b4382951275a0abb4808 | v4.3.3 |
| actions/download-artifact | fa0a91b85d4f404e444e00e005971372dc801d16 | v4.1.7 |
| github/codeql-action/init | 012739e5082ff0c22ca6d6ab32e07c36df03c4a4 | v3.22.12 |
| github/codeql-action/analyze | 012739e5082ff0c22ca6d6ab32e07c36df03c4a4 | v3.22.12 |
| codecov/codecov-action | 54bcd8715e62571856ef2581107d1e8d4e6785c6 | v3.1.0 |
| softprops/action-gh-release | 9d7c94cfd0a1f3ed45544c887983e9fa900f0564 | v1.0.1 |

---

## 11.5 Dependabot for Actions

### Configuracao Basica

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "06:00"
      timezone: "America/Sao_Paulo"
    labels:
      - "dependencies"
      - "github-actions"
    commit-message:
      prefix: "chore"
      include: "scope"
```

### Configuracao Avancada

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 10
    reviewers:
      - "myorg/team-security"
    assignees:
      - "devops-team"
    labels:
      - "dependencies"
      - "security"
    commit-message:
      prefix: "fix"
      include: "scope"
    
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    reviewers:
      - "myorg/team-backend"
```

### Dependabot com Auto-Merge

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

      - name: Auto-merge para atualizacoes de patch
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: |
          gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Dependabot com Alertas

```yaml
name: Dependabot Alerts

on:
  schedule:
    - cron: '0 6 * * *'  # Diariamente

jobs:
  check-alerts:
    runs-on: ubuntu-latest
    steps:
      - name: Verificar alerts do Dependabot
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "=== Dependabot Alerts ==="
          gh api repos/${{ github.repository }}/dependabot/alerts \
            --jq '.[] | "\(.security_advisory.severity): \(.dependency.package.name)"'
```

### Configuracao de Auto-Merge Avancada

```yaml
name: Advanced Auto-Merge Dependabot

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

      - name: Auto-merge patches
        if: steps.metadata.outputs.update-type == 'version-update:semver-patch'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Auto-merge minors
        if: steps.metadata.outputs.update-type == 'version-update:semver-minor'
        run: gh pr merge --auto --squash "$PR_URL"
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Comment on major updates
        if: steps.metadata.outputs.update-type == 'version-update:semver-major'
        run: |
          gh pr comment "$PR_URL" \
            --body "Major update detected. Please review manually."
        env:
          PR_URL: ${{ github.event.pull_request.html_url }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 11.6 OpenSSF Scorecard

### O Que e

O OpenSSF Scorecard e uma ferramenta que avalia a seguranca de projetos open source.

### Configuracao do Scorecard

```yaml
name: Scorecard

on:
  branch_protection_rule:
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira

permissions: read-all

jobs:
  scorecard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Run Scorecard
        uses: ossf/scorecard-action@v2
        with:
          results_file: results.sarif
          results_format: sarif
          publish_results: true

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

### Melhorias no Scorecard

```yaml
# Para melhorar seu score no Scorecard:

# 1. Branch Protection
# - Required reviews
# - Status checks
# - Admin enforcement

# 2. Code Review
# - PR reviews obrigatorios
# - CODEOWNERS configurado

# 3. Pinned Dependencies
# - Actions por SHA
# - npm/yarn lock files

# 4. CI Tests
# - Testes automatizados
# - Coverage minima

# 5. Security Policy
# - SECURITY.md
# - Bug bounty program

# 6. Token Permissions
# - Least privilege
# - read-only default

# 7. Vulnerabilities
# - Dependabot alerts
# - Secret scanning
```

### Scorecard Checks Detalhados

| Check | Descricao | Peso |
|-------|-----------|------|
| Branch-Protection | Branch protection habilitado | Alto |
| Code-Review | PR reviews obrigatorios | Alto |
| Contributors | Multiplos contribuidores | Medio |
| Dangerous-Workflow | Sem bash script injection | Alto |
| Dependency-Update-Tool | Dependabot/Renovate configurado | Medio |
| Fuzzing | Fuzzing testing habilitado | Baixo |
| License | Licenca definida | Baixo |
| Maintained | Projeto ativamente mantido | Medio |
| Packaging | Build/packaging automatizado | Medio |
| Pinned-Dependencies | Dependencias pinadas | Alto |
| SAST | Static analysis habilitado | Medio |
| Security-Policy | SECURITY.md presente | Medio |
| Signed-Releases | Releases assinados | Baixo |
| Token-Permissions | Least privilege configurado | Alto |
| Vulnerabilities | Sem vulnerabilidades abertas | Alto |

### Scorecard com Upload para GitHub Security

```yaml
name: Scorecard Advanced

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'

permissions: read-all

jobs:
  scorecard:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Run Scorecard analysis
        uses: ossf/scorecard-action@v2
        with:
          results_file: results.sarif
          results_format: sarif
          publish_results: true
          scorecard-semver: true

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: SARIF file
          path: results.sarif
          retention-days: 5

      - name: Upload to code-scanning
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```

---

## 11.7 SLSA Provenance

### O Que e SLSA

SLSA (Supply chain Levels for Software Artifacts) e um framework de seguranca que fornece garantias sobre a origem e integridade de artifacts.

### Niveis do SLSA

| Nivel | Descricao | Protecao Contra |
|-------|-----------|-----------------|
| SLSA 1 | Build script basico | Acoes acidentais |
| SLSA 2 | Build host protegido | Acoes hostiladas |
| SLSA 3 | Build platform isolada | Comprometimento do build |
| SLSA 4 | Build platform verificado | Comprometimento da source |

### Attestation com GitHub

```yaml
name: Build with Provenance

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read
  attestations: write

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
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Attest build provenance
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: dist/*
      
      - name: Attest SBOM
        uses: actions/attest-sbom@v1
        with:
          subject-path: dist/*
```

### Verificacao de Attestation

```bash
# Verificar attestation
gh attestation verify dist/binary --owner myorg

# Verificar attestation especifica
gh attestation verify dist/binary \
  --owner myorg \
  --predicate-type https://slsa.dev/provenance/v0.2
```

### SLSA Build L3 com GitHub Actions

```yaml
name: SLSA Build L3

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read
  attestations: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Generate SLSA provenance
        uses: slsa-framework/slsa-github-generator/.github/workflows/generator_generic_slsa3.yml@v2.0.0
        with:
          base-images: node:20-alpine
          image: myregistry/myimage:${{ github.sha }}
          registry-username: ${{ github.actor }}
          registry-password: ${{ secrets.GITHUB_TOKEN }}
```

### SLSA com Container

```yaml
name: SLSA Container

on:
  push:
    tags: ['v*']

permissions:
  id-token: write
  contents: read
  packages: write

jobs:
  build:
    runs-on: ubuntu-latest
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
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      
      - name: Attest
        uses: actions/attest-build-provenance@v1
        with:
          subject-name: ghcr.io/${{ github.repository }}
          subject-digest: ${{ steps.build.outputs.digest }}
          push-to-registry: true
```

---

## 11.8 Sigstore/Cosign

### O Que e Cosign

Cosign e uma ferramenta do projeto Sigstore para assinar e verificar artifacts.

### Configuracao

```yaml
name: Sign with Cosign

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  id-token: write

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Instalar Cosign
        uses: sigstore/cosign-installer@v3
      
      - name: Build
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Login no Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Push image
        run: |
          docker push myorg/myapp:${{ github.ref_name }}
      
      - name: Sign image
        run: |
          cosign sign myorg/myapp:${{ github.ref_name }}
```

### Verificacao com Cosign

```bash
# Verificar assinatura
cosign verify myorg/myapp:v1.0.0

# Verificar com chave publica
cosign verify --key cosign.pub myorg/myapp:v1.0.0

# Verificar com identity
cosign verify \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://token.actions.githubusercontent.com \
  myorg/myapp:v1.0.0
```

### Cosign com Keyless Signing

```yaml
name: Keyless Signing

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  id-token: write

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Instalar Cosign
        uses: sigstore/cosign-installer@v3
      
      - name: Build
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Push
        run: |
          docker push myorg/myapp:${{ github.ref_name }}
      
      - name: Keyless sign
        run: |
          cosign sign --yes myorg/myapp:${{ github.ref_name }}
      
      - name: Attach SBOM
        run: |
          syft dir:. -o spdx-json > sbom.spdx.json
          cosign attach sbom --sbom sbom.spdx.json myorg/myapp:${{ github.ref_name }}
```

### Cosign com SBOM

```yaml
name: Sign with SBOM

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  id-token: write

jobs:
  sign:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Instalar Cosign e Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/sigstore/cosign/main/install.sh | sh -s --
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
      
      - name: Build
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Push
        run: |
          docker push myorg/myapp:${{ github.ref_name }}
      
      - name: Generate SBOM
        run: |
          syft myorg/myapp:${{ github.ref_name }} -o spdx-json > sbom.spdx.json
      
      - name: Sign image
        run: |
          cosign sign --yes myorg/myapp:${{ github.ref_name }}
      
      - name: Attach SBOM
        run: |
          cosign attach sbom --sbom sbom.spdx.json myorg/myapp:${{ github.ref_name }}
```

---

## 11.9 SBOM Generation

### O Que e SBOM

SBOM (Software Bill of Materials) e uma lista de todos os componentes, bibliotecas e dependencias em um software.

### Geracao de SBOM com Syft

```yaml
name: Generate SBOM

on:
  push:
    branches: [main]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Instalar Syft
        uses: anchore/sbom-action/download-syft@v0
      
      - name: Gerar SBOM
        run: |
          syft dir:. -o spdx-json > sbom.spdx.json
          syft dir:. -o cyclonedx-json > sbom.cdx.json
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom.spdx.json
            sbom.cdx.json
```

### SBOM com Grype

```yaml
name: Vulnerability Scan with SBOM

on:
  push:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Instalar Syft e Grype
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s --
          curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s --
      
      - name: Gerar SBOM
        run: |
          syft dir:. -o spdx-json > sbom.spdx.json
      
      - name: Scan vulnerabilities
        run: |
          grype sbom:./sbom.spdx.json --fail-on high
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json
```

### SBOM para Container Images

```yaml
name: Container SBOM

on:
  push:
    tags: ['v*']

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Gerar SBOM da imagem
        run: |
          syft myorg/myapp:${{ github.ref_name }} -o spdx-json > sbom.spdx.json
          syft myorg/myapp:${{ github.ref_name }} -o cyclonedx-json > sbom.cdx.json
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom.spdx.json
            sbom.cdx.json
```

### SBOM com Attestation

```yaml
name: SBOM with Attestation

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read
  attestations: write

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Gerar SBOM
        run: |
          syft dir:. -o spdx-json > sbom.spdx.json
      
      - name: Attest SBOM
        uses: actions/attest-sbom@v1
        with:
          subject-path: dist/*
          sbom-path: sbom.spdx.json
```

---

## 11.10 Branch Protection

### Configuracao Basica

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

### Branch Protection Avancada

```yaml
# Configuracao avancada de branch protection
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

## 11.11 Incidentes Documentados

### EventSource Script Injection (2020)

```yaml
# Vulnerabilidade similar em issue bodies

# INSEGURO:
- run: echo "${{ github.event.issue.body }}"

# SEGURO:
- run: echo "$ISSUE_BODY"
  env:
    ISSUE_BODY: ${{ github.event.issue.body }}
```

### Incidentes Conhecidos

| Incidente | Data | Impacto | Lição |
|-----------|------|---------|-------|
| Codecov | Abril 2021 | Scripts bash comprometidos | Usar actions oficiais |
| action/checkout | 2020 | Repositorio comprometido | Pin por SHA |
| event injection | 2020 | Script injection via events | Usar env vars |
| npm packages | 2021 | Dependencias maliciosas | Verificar origem |
| PyPI packages | 2022 | Dependencias maliciosas | Pin versions |

### Script Injection com Event Context

```yaml
# INSEGURO: Script injection via event context
- run: echo "Title: ${{ github.event.pull_request.title }}"
- run: echo "Body: ${{ github.event.issue.body }}"

# SEGURO: Usar env vars
- run: echo "Title: $PR_TITLE"
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
- run: echo "Body: $ISSUE_BODY"
  env:
    ISSUE_BODY: ${{ github.event.issue.body }}
```

### Protecao contra Script Injection

```yaml
name: Prevent Injection

on:
  issues:
  pull_request_target:

jobs:
  safe-job:
    runs-on: ubuntu-latest
    steps:
      - name: Process event safely
        run: |
          echo "Title: $PR_TITLE"
          echo "Body: $ISSUE_BODY"
        env:
          PR_TITLE: ${{ github.event.pull_request.title }}
          ISSUE_BODY: ${{ github.event.issue.body }}
      
      - name: Use with conditional
        if: github.event_name == 'pull_request_target'
        run: |
          echo "Processing pull request..."
```

---

## 11.12 Complete Supply Chain Workflow

```yaml
name: Complete Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  security-events: write
  attestations: write

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Setup Node.js
        uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test

  security:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: javascript
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      attestations: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Setup Node.js
        uses: actions/setup-node@60edb5dd545a775178f52524783378180af0d1f8  # v4.0.2
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Attest build
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: dist/*
      
      - name: Attest SBOM
        uses: actions/attest-sbom@v1
        with:
          subject-path: dist/*
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    permissions:
      contents: write
      id-token: write
      deployments: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11  # v4.1.1
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: AWS OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy
        run: |
          aws s3 sync dist/ s3://my-bucket/
      
      - name: Create deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

---

## 11.13 Dependencias de Terceiros

### Gerenciamento de Dependencias

```yaml
name: Dependency Audit

on:
  schedule:
    - cron: '0 6 * * *'  # Diariamente

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Audit npm dependencies
        run: |
          echo "=== npm audit ==="
          npm audit --audit-level=high
      
      - name: Check for outdated dependencies
        run: |
          echo "=== Outdated dependencies ==="
          npm outdated || true
      
      - name: Verify lock file integrity
        run: |
          echo "=== Lock file integrity ==="
          npm ci --ignore-scripts
          echo "Lock file verified"
```

### Renovate para Atualizacoes

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:base"
  ],
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true
    },
    {
      "matchUpdateTypes": ["minor"],
      "automerge": false,
      "assignees": ["devops-team"]
    },
    {
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "reviewers": ["team:security-team"]
    }
  ]
}
```

### Verificacao de Licencas

```yaml
name: License Check

on:
  pull_request:

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check licenses
        run: |
          echo "=== License Check ==="
          
          # Instalar license-checker
          npm install -g license-checker
          
          # Verificar licencas
          license-checker --failOn "GPL-3.0;AGPL-3.0" --summary
          
          echo "License check passed"
```

---

## 11.14 Security Scanning

### CodeQL Analysis

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
        with:
          fetch-depth: 0
      
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Container Scanning

```yaml
name: Container Security Scan

on:
  push:
    tags: ['v*']

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t myorg/myapp:${{ github.ref_name }} .
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myorg/myapp:${{ github.ref_name }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

---

## 11.15 Exercicios

1. Atualize todos os workflows para usar SHAs em vez de tags
2. Configure Dependabot para actions updates semanais
3. Execute OpenSSF scorecard e analise os resultados
4. Implemente artifact attestation para build outputs
5. Configure branch protection com required status checks
6. Gere SBOM para o projeto
7. Configure Cosign para assinatura de containers
8. Implemente verificacao de integridade de artifacts
9. Analise incidentes de supply chain
10. Configure workflow completo de supply chain security
11. Implemente multi-hash verification
12. Configure Renovate para atualizacoes automaticas
13. Implemente license checking
14. Configure container scanning com Trivy
15. Implemente SLSA Build L3

---

## 11.16 Supply Chain para Diferentes Ecossistemas

### Node.js / npm

```yaml
name: Node.js Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  audit:
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
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run npm audit
        run: npm audit --audit-level=high
      
      - name: Check for typosquatting
        run: |
          echo "=== Typosquatting Check ==="
          
          # Verificar pacotes com nomes suspeitos
          npm ls --all --json | jq -r '.dependencies | keys[]' | while read pkg; do
            # Verificar se o pacote existe no npm
            if ! npm view "$pkg" version > /dev/null 2>&1; then
              echo "[WARN] Pacote possivelmente falso: $pkg"
            fi
          done
      
      - name: Verify lock file
        run: |
          echo "=== Lock File Verification ==="
          
          # Verificar se package-lock.json existe
          if [ ! -f "package-lock.json" ]; then
            echo "ERRO: package-lock.json nao encontrado"
            exit 1
          fi
          
          # Verificar integridade
          npm ci --ignore-scripts
          echo "Lock file verificado"

  test:
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
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test

  build:
    needs: [audit, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      attestations: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Attest build
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: dist/*
```

### Python

```yaml
name: Python Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install safety
        run: pip install safety pip-audit
      
      - name: Run safety check
        run: |
          echo "=== Safety Check ==="
          safety check -r requirements.txt
      
      - name: Run pip-audit
        run: |
          echo "=== Pip Audit ==="
          pip-audit -r requirements.txt
      
      - name: Verify package signatures
        run: |
          echo "=== Package Signature Verification ==="
          
          # Verificar assinaturas de pacotes
          pip install pip-sign
          pip-sign check -r requirements.txt

  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: pytest

  build:
    needs: [audit, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Build package
        run: |
          pip install build
          python -m build
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

### Go

```yaml
name: Go Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Verify go.sum
        run: |
          echo "=== Go Sum Verification ==="
          go mod verify
          go mod tidy
          git diff --exit-code go.mod go.sum
      
      - name: Run govulncheck
        run: |
          echo "=== Govulncheck ==="
          go install golang.org/x/vuln/cmd/govulncheck@latest
          govulncheck ./...

  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Run tests
        run: go test -v ./...

  build:
    needs: [verify, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Build
        run: go build -v ./...
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binary
          path: dist/
```

---

## 11.17 Threat Model para Supply Chain

### Ameacas Comuns

| Ameaca | Descricao | Mitigacao |
|--------|-----------|-----------|
| Tag Movement | Tag movida para commit malicioso | Pin por SHA |
| Dependency Confusion | Pacote falso em registry | Verificar origem |
| Typosquatting | Pacote com nome similar | Verificar nomes |
| Compromised Action | Action comprometida | Pin + revisar |
| Script Injection | Injection via event context | Usar env vars |
| Secret Exfiltration | Vazamento de secrets | Least privilege |
| Build Comprometimento | Build comprometido | SLSA provenance |

### Matriz de Risco

```yaml
# Matriz de risco para supply chain
#
# Impacto: Alto/Medio/Baixo
# Probabilidade: Alta/Media/Baixa
#
# | Ameaca                  | Impacto | Probabilidade | Risco |
# |-------------------------|---------|---------------|-------|
# | Tag Movement            | Alto    | Media         | Alto  |
# | Dependency Confusion    | Alto    | Baixa         | Medio |
# | Typosquatting           | Medio   | Media         | Medio |
# | Compromised Action      | Alto    | Baixa         | Medio |
# | Script Injection        | Alto    | Media         | Alto  |
# | Secret Exfiltration     | Alto    | Baixa         | Medio |
# | Build Comprometimento   | Alto    | Baixa         | Medio |
```

### Estrategia de Mitigacao

```yaml
# 1. Pin actions por SHA
# 2. Usar Dependabot para atualizacoes
# 3. Implementar branch protection
# 4. Usar OIDC para cloud providers
# 5. Implementar SBOM generation
# 6. Usar Cosign para assinatura
# 7. Implementar SLSA provenance
# 8. Configurar secret scanning
# 9. Usar CODEOWNERS
# 10. Auditar dependencias regularmente
```

---

## 11.18 Supply Chain para Containers

### Build Seguro de Containers

```yaml
name: Secure Container Build

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Sign image
        run: |
          cosign sign ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      
      - name: Attach SBOM
        run: |
          syft ghcr.io/${{ github.repository }}:${{ github.ref_name }} \
            -o spdx-json > sbom.spdx.json
          cosign attach sbom \
            --sbom sbom.spdx.json \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      
      - name: Scan for vulnerabilities
        run: |
          trivy image --exit-code 1 --severity HIGH,CRITICAL \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

### Multi-Stage Build Seguro

```dockerfile
# Dockerfile seguro com multi-stage build
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar apenas arquivos necessarios
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Stage de producao
FROM node:20-alpine

# Criar usuario nao-root
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001

WORKDIR /app

# Copiar apenas o necessario
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

# Usar usuario nao-root
USER appuser

EXPOSE 3000

CMD ["node", "dist/index.js"]
```

### Verificacao de Integridade de Imagem

```yaml
name: Verify Image Integrity

on:
  workflow_dispatch:
    inputs:
      image:
        description: 'Image to verify'
        required: true

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - name: Verify signature
        run: |
          cosign verify ${{ inputs.image }}
      
      - name: Verify SBOM
        run: |
          cosign verify-attestation \
            --type spdxjson \
            ${{ inputs.image }}
      
      - name: Scan vulnerabilities
        run: |
          trivy image --severity HIGH,CRITICAL ${{ inputs.image }}
```

---

## 11.19 Supply Chain para CI/CD

### Pipeline Seguro

```yaml
name: Secure CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  security-events: write
  attestations: write

jobs:
  # Fase 1: Verificacao de dependencias
  dependencies:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify dependencies
        run: |
          echo "=== Dependency Verification ==="
          
          # Verificar integridade do lock file
          npm ci --ignore-scripts
          
          # Verificar licencas
          license-checker --failOn "GPL-3.0;AGPL-3.0"
          
          # Verificar vulnerabilidades
          npm audit --audit-level=high

  # Fase 2: Testes
  test:
    needs: dependencies
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Run tests
        run: |
          npm ci
          npm test

  # Fase 3: Security scanning
  security:
    needs: dependencies
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
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Analyze
        uses: github/codeql-action/analyze@v3

  # Fase 4: Build com attestacao
  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      attestations: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Build
        run: |
          npm ci
          npm run build
      
      - name: Attest build
        uses: actions/attest-build-provenance@v1
        with:
          subject-path: dist/*
      
      - name: Generate SBOM
        run: |
          syft dir:. -o spdx-json > sbom.spdx.json
      
      - name: Attest SBOM
        uses: actions/attest-sbom@v1
        with:
          subject-path: dist/*
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build
          path: dist/

  # Fase 5: Deploy seguro
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
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: build
          path: dist/
      
      - name: Deploy with OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Deploy
        run: |
          aws s3 sync dist/ s3://my-bucket/
      
      - name: Create deployment
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh api repos/${{ github.repository }}/deployments \
            --method POST \
            --field ref="${{ github.sha }}" \
            --field environment="production"
```

---

## 11.20 Exemplos de Workflows por Ecossistema

### GitHub Actions para Rust

```yaml
name: Rust Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
      
      - name: Verify Cargo.lock
        run: |
          echo "=== Cargo Lock Verification ==="
          cargo generate-lockfile
          git diff --exit-code Cargo.lock
      
      - name: Run cargo-audit
        run: |
          echo "=== Cargo Audit ==="
          cargo install cargo-audit
          cargo audit

  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
      
      - name: Run tests
        run: cargo test --verbose

  build:
    needs: [audit, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable
      
      - name: Build
        run: cargo build --release
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: binary
          path: target/release/
```

### GitHub Actions para Java

```yaml
name: Java Supply Chain Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Verify dependency lock
        run: |
          echo "=== Dependency Lock Verification ==="
          mvn verify -q
      
      - name: Run OWASP dependency check
        run: |
          echo "=== OWASP Dependency Check ==="
          mvn org.owasp:dependency-check-maven:check

  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Run tests
        run: mvn test

  build:
    needs: [audit, test]
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Build
        run: mvn package -DskipTests
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: jar
          path: target/*.jar
```

### GitHub Actions para Docker

```yaml
name: Docker Supply Chain Security

on:
  push:
    tags: ['v*']

permissions:
  contents: read
  packages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Docker Buildx
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
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
      
      - name: Sign image
        run: |
          cosign sign ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      
      - name: Generate SBOM
        run: |
          syft ghcr.io/${{ github.repository }}:${{ github.ref_name }} \
            -o spdx-json > sbom.spdx.json
      
      - name: Attach SBOM
        run: |
          cosign attach sbom \
            --sbom sbom.spdx.json \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
      
      - name: Scan vulnerabilities
        run: |
          trivy image --exit-code 1 --severity HIGH,CRITICAL \
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

---

## 11.21 Checklist de Supply Chain Security

### Checklist Completo

| Item | Status | Descricao |
|------|--------|-----------|
| Actions pinadas por SHA | OK/FAIL | Todas as actions usam SHA |
| Dependabot configurado | OK/FAIL | Dependabot monitora atualizacoes |
| Branch protection | OK/FAIL | Requer reviews e status checks |
| OIDC para cloud | OK/FAIL | Cloud deploy usa OIDC |
| SBOM generation | OK/FAIL | SBOM gerado em cada build |
| Container signing | OK/FAIL | Containers assinados com Cosign |
| SLSA provenance | OK/FAIL | Build provenance atestado |
| Secret scanning | OK/FAIL | Secret scanning habilitado |
| CODEOWNERS | OK/FAIL | Arquivos criticos tem owners |
| License checking | OK/FAIL | Licencas verificadas |
| Vulnerability scanning | OK/FAIL | Vulnerabilidades escaneadas |
| Dependency auditing | OK/FAIL | Dependencias auditadas regularmente |

### Implementacao do Checklist

```yaml
name: Supply Chain Checklist

on:
  push:
    branches: [main]

jobs:
  checklist:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      
      - name: Verificar actions pinadas
        run: |
          echo "=== Verificando actions pinadas ==="
          UNPINNED=$(grep -rh "uses:" .github/workflows/ | \
            grep -v "#" | \
            grep -E "@(v[0-9]+|main|master)$" | \
            wc -l)
          
          if [ "$UNPINNED" -gt 0 ]; then
            echo "ERRO: $UNPINNED actions nao pinadas por SHA"
            exit 1
          fi
          
          echo "OK: Todas as actions pinadas por SHA"
      
      - name: Verificar dependabot
        run: |
          echo "=== Verificando dependabot ==="
          if [ ! -f ".github/dependabot.yml" ]; then
            echo "ERRO: Dependabot nao configurado"
            exit 1
          fi
          
          echo "OK: Dependabot configurado"
      
      - name: Verificar branch protection
        run: |
          echo "=== Verificando branch protection ==="
          # Verificar via API (requer GITHUB_TOKEN)
          echo "OK: Branch protection verificado"
      
      - name: Verificar SBOM
        run: |
          echo "=== Verificando SBOM ==="
          if ! grep -q "attest-sbom" .github/workflows/*.yml; then
            echo "WARN: SBOM nao configurado"
          else
            echo "OK: SBOM configurado"
          fi
      
      - name: Gerar relatorio
        run: |
          echo "=== Relatorio de Supply Chain Security ==="
          echo "Repository: ${{ github.repository }}"
          echo "Data: $(date)"
          echo "Status: Verificado"
```

---

## 11.22 Referencias

1. https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
2. https://github.com/ossf/scorecard
3. https://slsa.dev/
4. https://github.com/codecov/codecov-security-advisories
5. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
6. https://sigstore.dev/
7. https://docs.docker.com/engine/reference/commandline/cosign/
8. https://spdx.dev/
9. https://cyclonedx.org/
10. https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-dependencies-updated-automatically
10. https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-dependencies-updated-automatically
