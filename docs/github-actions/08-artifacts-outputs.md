---
layout: default
title: "08-artifacts-outputs"
---

# Capitulo 8 — Artifacts e Outputs

> *"Artifacts sao a ponte entre jobs. Outputs sao a ponte entre steps."*

---

## Sumario

| Secao | Descricao |
|-------|-----------|
| 8.1 | upload-artifact |
| 8.2 | download-artifact |
| 8.3 | Retention policies |
| 8.4 | Size limits |
| 8.5 | Job outputs |
| 8.6 | Step outputs |
| 8.7 | Matrix output aggregation |
| 8.8 | Build artifacts |
| 8.9 | SBOM generation |

---

## Objetivos de Aprendizado

1. Usar upload-artifact e download-artifact para compartilhar dados entre jobs
2. Configurar retention policies para gerenciar armazenamento
3. Entender e respeitar size limits de artifacts
4. Implementar job outputs para comunicacao entre jobs
5. Usar step outputs para comunicacao entre steps
6. Agregar outputs de matrix builds
7. Gerenciar build artifacts para releases
8. Gerar e armazenar SBOMs (Software Bill of Materials)
9. Otimizar uso de artifacts para reduzir custos
10. Implementar patterns avancados de artifacts

---

## 8.1 Upload de Artifacts

Upload de artifacts e o mecanismo para armazenar arquivos gerados durante a execucao de um workflow, tornando-os disponiveis para outros jobs ou para download manual.

### 8.1.1 Upload Basico

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/
    retention-days: 30
```

### 8.1.2 Multiplos Paths

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: build-artifacts
    path: |
      dist/
      build/
      *.log
    retention-days: 7
```

### 8.1.3 Compression

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: compressed-output
    path: dist/
    compression-level: 9  # 0-9, default 6
```

### 8.1.4 Upload com Condicoes

```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: test-results
    path: test-results/
    retention-days: 7
```

### 8.1.5 Upload de Multiplos Artifacts

```yaml
steps:
  - name: Build frontend
    run: npm run build:frontend

  - name: Build backend
    run: npm run build:backend

  - uses: actions/upload-artifact@v4
    with:
      name: frontend-dist
      path: packages/frontend/dist/
      retention-days: 1

  - uses: actions/upload-artifact@v4
    with:
      name: backend-dist
      path: packages/backend/dist/
      retention-days: 1

  - uses: actions/upload-artifact@v4
    with:
      name: build-logs
      path: logs/
      retention-days: 7
```

### 8.1.6 Upload com Nome Dinamico

```yaml
steps:
  - name: Set artifact name
    id: artifact
    run: |
      echo "name=build-${{ github.sha }}" >> $GITHUB_OUTPUT

  - uses: actions/upload-artifact@v4
    with:
      name: ${{ steps.artifact.outputs.name }}
      path: dist/
      retention-days: 30
```

### 8.1.7 Tabela de Opcoes de Upload

| Opcao | Tipo | Descricao | Default |
|-------|------|-----------|---------|
| name | string | Nome do artifact | Obrigatorio |
| path | string | Caminho dos arquivos | Obrigatorio |
| retention-days | number | Dias de retencao | 90 |
| compression-level | number | Nivel de compressao (0-9) | 6 |
| if-no-files-found | string | Comportamento se nao encontrar arquivos | warn |

---

## 8.2 Download de Artifacts

Download de artifacts e o mecanismo para recuperar arquivos armazenados por upload-artifact.

### 8.2.1 Download Basico

```yaml
- uses: actions/download-artifact@v4
  with:
    name: build-output
    path: ./dist
```

### 8.2.2 Download de Todos os Artifacts

```yaml
- uses: actions/download-artifact@v4
  with:
    path: ./artifacts
    merge-multiple: true
```

### 8.2.3 Download com Pattern

```yaml
- uses: actions/download-artifact@v4
  with:
    pattern: build-*
    path: ./artifacts
    merge-multiple: true
```

### 8.2.4 Download de Artifact Especifico

```yaml
- uses: actions/download-artifact@v4
  with:
    name: frontend-dist
    path: ./dist/frontend

- uses: actions/download-artifact@v4
  with:
    name: backend-dist
    path: ./dist/backend
```

### 8.2.5 Download com Merge

```yaml
- uses: actions/download-artifact@v4
  with:
    path: ./all-artifacts
    merge-multiple: true
```

### 8.2.6 Tabela de Opcoes de Download

| Opcao | Tipo | Descricao | Default |
|-------|------|-----------|---------|
| name | string | Nome do artifact | Obrigatorio (ou pattern) |
| pattern | string | Pattern para filtrar artifacts | - |
| path | string | Caminho de destino | . |
| merge-multiple | boolean | Merge multiplos artifacts | false |

---

## 8.3 Retention Policies

Retention policies definem por quanto tempo artifacts sao mantidos antes de serem deletados automaticamente.

### 8.3.1 Retention Basico

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: logs
    path: logs/
    retention-days: 1  # Manter apenas 1 dia
```

### 8.3.2 Retention por Tipo

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: logs
    path: logs/
    retention-days: 1  # Logs: 1 dia

- uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: test-results/
    retention-days: 7  # Testes: 1 semana

- uses: actions/upload-artifact@v4
  with:
    name: coverage
    path: coverage/
    retention-days: 30  # Coverage: 1 mes

- uses: actions/upload-artifact@v4
  with:
    name: release
    path: dist/
    retention-days: 90  # Release: 3 meses
```

### 8.3.3 Retention por Branch

```yaml
steps:
  - name: Set retention
    id: retention
    run: |
      if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
        echo "days=90" >> $GITHUB_OUTPUT
      elif [[ "${{ github.ref }}" == refs/pull/* ]]; then
        echo "days=7" >> $GITHUB_OUTPUT
      else
        echo "days=1" >> $GITHUB_OUTPUT
      fi

  - uses: actions/upload-artifact@v4
    with:
      name: build
      path: dist/
      retention-days: ${{ steps.retention.outputs.days }}
```

### 8.3.4 Delete Manual de Artifacts

```yaml
- name: Delete old artifacts
  uses: geekyeggo/delete-artifact@v5
  with:
    name: build-*
    retention-days: 7
```

### 8.3.5 Cleanup Automatico

```yaml
name: Cleanup Old Artifacts

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Delete old artifacts
        uses: actions/github-script@v7
        with:
          script: |
            const artifacts = await github.rest.actions.listWorkflowArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo
            });

            for (const artifact of artifacts.data.artifacts) {
              const daysSinceCreation = (Date.now() - new Date(artifact.created_at).getTime()) / (1000 * 60 * 60 * 24);

              if (daysSinceCreation > 30) {
                await github.rest.actions.deleteArtifact({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  artifact_id: artifact.id
                });
              }
            }
```

### 8.3.6 Tabela de Retention Recomendada

| Tipo de Artifact | Dias Recomendados | Observacao |
|------------------|-------------------|------------|
| Logs de build | 1-3 | Apenas para debug |
| Test results | 7 | Para analise pos-build |
| Coverage reports | 30 | Para historico |
| Build artifacts | 7-30 | Para deploy |
| Release artifacts | 30-90 | Para distribuicao |
| Security scans | 90 | Para compliance |
| Database backups | 30 | Para recovery |

---

## 8.4 Size Limits

GitHub Actions tem limites de tamanho para artifacts que devem ser respeitados.

### 8.4.1 Limites por Artefact

| Limite | Valor | Observacao |
|--------|-------|------------|
| Tamanho maximo por artifact | 500 MB | Upload unico |
| Tamanho total por workflow | 10 GB | Soma de todos os artifacts |
| Numero de artifacts | 500 por workflow run | Limite por execucao |

### 8.4.2 Gerenciamento de Tamanho

```yaml
steps:
  - name: Check artifact size
    run: |
      du -sh dist/
      if [ $(du -sb dist/ | cut -f1) -gt 500000000 ]; then
        echo "Artifact too large (>500MB)"
        exit 1
      fi

  - uses: actions/upload-artifact@v4
    with:
      name: dist
      path: dist/
```

### 8.4.3 Compressao para Reduzir Tamanho

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: compressed-dist
    path: dist/
    compression-level: 9  # Maxima compressao
```

### 8.4.4 Upload Seletivo

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: |
      dist/**/*.js
      dist/**/*.css
      dist/**/*.html
    retention-days: 7
```

### 8.4.5 Tabela de Tamanhos por Tipo

| Tipo | Tamanho Tipico | Estrategia |
|------|----------------|------------|
| Source code | 1-10 MB | Upload direto |
| Build output | 10-100 MB | Compressao |
| node_modules | 100-500 MB | Evitar upload |
| Docker image | 100 MB-1 GB | Usar registry |
| Logs | 1-50 MB | Retention curta |
| Test results | 1-10 MB | Retention media |

---

## 8.5 Job Outputs

Job outputs permitem compartilhar dados entre jobs dentro de um workflow.

### 8.5.1 Job Outputs Basico

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.value }}
      commit-sha: ${{ steps.commit.outputs.sha }}
    steps:
      - id: version
        run: echo "value=1.2.3" >> $GITHUB_OUTPUT
      - id: commit
        run: echo "sha=${{ github.sha }}" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Version: ${{ needs.build.outputs.version }}"
          echo "SHA: ${{ needs.build.outputs.commit-sha }}"
```

### 8.5.2 Job Outputs com Condicoes

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      should-deploy: ${{ steps.check.outputs.deploy }}
    steps:
      - id: check
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "deploy=true" >> $GITHUB_OUTPUT
          else
            echo "deploy=false" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: build
    if: needs.build.outputs.should-deploy == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying..."
```

### 8.5.3 Job Outputs com JSON

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: |
          echo 'matrix={"os":["ubuntu-latest","macos-latest"],"node":["18","20","22"]}' >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ${{ matrix.os }}
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - run: echo "Testing on ${{ matrix.os }} with Node ${{ matrix.node }}"
```

### 8.5.4 Job Outputs com Multiple Values

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
      sha: ${{ steps.sha.outputs.s }}
      branch: ${{ steps.branch.outputs.b }}
    steps:
      - id: version
        run: echo "v=$(node -p 'require(\"./package.json\").version')" >> $GITHUB_OUTPUT
      - id: sha
        run: echo "s=${{ github.sha }}" >> $GITHUB_OUTPUT
      - id: branch
        run: echo "b=${{ github.ref_name }}" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Version: ${{ needs.build.outputs.version }}"
          echo "SHA: ${{ needs.build.outputs.sha }}"
          echo "Branch: ${{ needs.build.outputs.branch }}"
```

---

## 8.6 Step Outputs

Step outputs permitem compartilhar dados entre steps dentro de um job.

### 8.6.1 Step Outputs Basico

```yaml
steps:
  - id: lint
    run: |
      if npm run lint 2>&1 | grep -q "error"; then
        echo "has_errors=true" >> $GITHUB_OUTPUT
      else
        echo "has_errors=false" >> $GITHUB_OUTPUT
      fi

  - if: steps.lint.outputs.has_errors == 'true'
    run: echo "Lint errors found"
```

### 8.6.2 Step Outputs com Variaveis

```yaml
steps:
  - id: vars
    run: |
      echo "node_version=$(node -v)" >> $GITHUB_OUTPUT
      echo "npm_version=$(npm -v)" >> $GITHUB_OUTPUT
      echo "os=$(uname -s)" >> $GITHUB_OUTPUT

  - run: |
      echo "Node: ${{ steps.vars.outputs.node_version }}"
      echo "NPM: ${{ steps.vars.outputs.npm_version }}"
      echo "OS: ${{ steps.vars.outputs.os }}"
```

### 8.6.3 Step Outputs com JSON

```yaml
steps:
  - id: packages
    run: |
      PACKAGES=$(find packages -name "package.json" -not -path "*/node_modules/*" | \
        xargs -I {} dirname {} | \
        xargs -I {} basename {} | \
        jq -R -s -c 'split("\n") | map(select(length > 0))')
      echo "list=$PACKAGES" >> $GITHUB_OUTPUT

  - run: |
      echo "Packages: ${{ steps.packages.outputs.list }}"
```

### 8.6.4 Step Outputs com Multi-line

```yaml
steps:
  - id: changes
    run: |
      CHANGES=$(git diff --name-only HEAD~1)
      EOF=$(dd if=/dev/urandom bs=15 count=1 status=none | base64)
      echo "list<<$EOF" >> $GITHUB_OUTPUT
      echo "$CHANGES" >> $GITHUB_OUTPUT
      echo "$EOF" >> $GITHUB_OUTPUT

  - run: |
      echo "Changed files:"
      echo "${{ steps.changes.outputs.list }}"
```

---

## 8.7 Matrix Output Aggregation

Matrix output aggregation e o processo de coletar e combinar resultados de multiplos jobs de matrix.

### 8.7.1 Aggregation Basico

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    outputs:
      results: ${{ steps.check.outputs.results }}
    steps:
      - id: check
        run: |
          echo "${{ matrix.package }}=success" >> $GITHUB_OUTPUT

  report:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: echo "All builds: ${{ needs.build.outputs.results }}"
```

### 8.7.2 Aggregation com Artifacts

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci

      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - run: |
          for dir in artifacts/*/; do
            package=$(basename "$dir")
            echo "Testing $package"
            npm run test --workspace=packages/$package
          done
```

### 8.7.3 Aggregation com Status

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    outputs:
      status: ${{ steps.status.outputs.result }}
    steps:
      - id: status
        run: |
          if [ "${{ matrix.package }}" = "core" ]; then
            echo "result=success" >> $GITHUB_OUTPUT
          fi

  report:
    needs: build
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Generate report
        run: |
          echo "## Build Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Package | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|---------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| core | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| utils | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| api | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
```

### 8.7.4 Aggregation com Merge

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  merge:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: dist-*
          path: merged-dist
          merge-multiple: true

      - run: ls -la merged-dist/
```

---

## 8.8 Build Artifacts

Build artifacts sao arquivos gerados durante o processo de build que podem ser distribuidos ou usados em etapas posteriores.

### 8.8.1 Build Artifact Basico

```yaml
name: Build with Artifacts

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - id: version
        run: echo "v=$(node -p 'require(\"./package.json\").version')" >> $GITHUB_OUTPUT

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
          retention-days: 30

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - run: node dist/index.js --test

  release:
    needs: [build, test]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - name: Create release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/*
```

### 8.8.2 Build Artifact para Multi-Platform

```yaml
name: Multi-Platform Build Artifacts

on: [push, pull_request]

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
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'
          cache: true

      - name: Build
        run: |
          SUFFIX=""
          if [ "${{ runner.os }}" = "Windows" ]; then
            SUFFIX=".exe"
          fi
          go build -o bin/myapp${SUFFIX} ./cmd/myapp

      - uses: actions/upload-artifact@v4
        with:
          name: myapp-${{ matrix.artifact }}
          path: bin/
          retention-days: 7

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            artifacts/myapp-linux-amd64/*
            artifacts/myapp-darwin-arm64/*
            artifacts/myapp-windows-amd64/*
```

### 8.8.3 Build Artifact com Versionamento

```yaml
name: Versioned Build Artifacts

on:
  push:
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - id: version
        run: echo "v=${GITHUB_REF#refs/tags/}" >> $GITHUB_OUTPUT

      - uses: actions/upload-artifact@v4
        with:
          name: release-${{ steps.version.outputs.v }}
          path: dist/
          retention-days: 90

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: release-${{ needs.build.outputs.version }}
          path: dist/
      - run: node dist/index.js --test

  release:
    needs: [build, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: release-${{ needs.build.outputs.version }}
          path: dist/
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ needs.build.outputs.version }}
          generate_release_notes: true
          files: dist/*
```

---

## 8.9 SBOM Generation

SBOM (Software Bill of Materials) e um documento que lista todos os componentes, bibliotecas e dependencias de um software.

### 8.9.1 SBOM Basico

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    path: ./dist
    format: spdx-json
    output-file: sbom.json

- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

### 8.9.2 SBOM com Syft

```yaml
- name: Install Syft
  uses: anchore/sbom-action/download-syft@v0

- name: Generate SBOM
  run: |
    syft dir:. -o spdx-json=sbom.spdx.json
    syft dir:. -o cyclonedx-json=sbom.cyclonedx.json

- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: |
      sbom.spdx.json
      sbom.cyclonedx.json
```

### 8.9.3 SBOM com Trivy

```yaml
- name: Generate SBOM with Trivy
  uses: aquasecurity/trivy-action@0.28.0
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'cyclonedx'
    output: 'sbom.json'

- uses: actions/upload-artifact@v4
  with:
    name: sbom
    path: sbom.json
```

### 8.9.4 SBOM para Docker

```yaml
- name: Build Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    load: true
    tags: myapp:test

- name: Generate SBOM for Docker image
  uses: anchore/sbom-action@v0
  with:
    image: myapp:test
    format: spdx-json
    output-file: sbom-docker.json

- uses: actions/upload-artifact@v4
  with:
    name: sbom-docker
    path: sbom-docker.json
```

### 8.9.5 SBOM com Scan

```yaml
- name: Generate and scan SBOM
  uses: anchore/sbom-action@v0
  with:
    path: ./dist
    format: spdx-json
    output-file: sbom.json

- name: Scan SBOM for vulnerabilities
  uses: aquasecurity/trivy-action@0.28.0
  with:
    scan-type: 'sbom'
    sbom: sbom.json
    format: 'sarif'
    output: 'vulnerabilities.sarif'
    severity: 'CRITICAL,HIGH'

- name: Upload vulnerability scan
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: 'vulnerabilities.sarif'
```

### 8.9.6 Tabela de Formatos SBOM

| Formato | Descricao | Uso Recomendado |
|---------|-----------|-----------------|
| SPDX JSON | Padrao SPDX | Compliance, auditoria |
| CycloneDX JSON | OWASP standard | Seguranca, vulnerabilidades |
| SPDX Tag-Value | Formato texto | Ferramentas legadas |
| CycloneDX XML | Formato XML | Integracao com ferramentas |

---

## 8.10 Exemplos de Casos Reais

### 8.10.1 Pipeline Completa com Artifacts

```yaml
name: Complete Pipeline with Artifacts

on: [push, pull_request]

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

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/
          retention-days: 7

  build:
    needs: test
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

      - id: version
        run: echo "v=$(node -p 'require(\"./package.json\").version')" >> $GITHUB_OUTPUT

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
          retention-days: 30

  sbom:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: ./dist
          format: spdx-json
          output-file: sbom.json

      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
          retention-days: 90

  coverage:
    needs: test
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: coverage
          path: coverage/
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage/lcov.info
          flags: unittests
          fail_ci_if_error: false

  deploy-preview:
    needs: [build, sbom]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - name: Deploy preview
        run: |
          echo "Deploying preview for PR #${{ github.event.pull_request.number }}"

  deploy-production:
    needs: [build, sbom, coverage]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - uses: actions/download-artifact@v4
        with:
          name: sbom
          path: .
      - name: Deploy to production
        run: |
          echo "Deploying version ${{ needs.build.outputs.version }}"
          echo "SBOM: $(ls -la sbom.json)"
          ./deploy.sh

  release:
    needs: [deploy-production]
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - uses: actions/download-artifact@v4
        with:
          name: sbom
          path: .
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*
            sbom.json
```

### 8.10.2 Pipeline Monorepo com Artifacts

```yaml
name: Monorepo with Artifacts

on: [push, pull_request]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.changes.outputs.packages }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            packages:
              - 'packages/**'

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages == 'true'
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect packages
        id: set-matrix
        run: |
          PACKAGES=$(find packages -name "package.json" -not -path "*/node_modules/*" | \
            xargs -I {} dirname {} | \
            xargs -I {} basename {} | \
            jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "matrix={\"package\":$PACKAGES}" >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test --workspace=packages/${{ matrix.package }}

  build-packages:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}
      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  publish:
    needs: build-packages
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          registry-url: 'https://registry.npmjs.org'
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
      - name: Publish
        run: |
          cd packages/${{ matrix.package }}
          npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 8.11 Exercicios

1. Crie um pipeline que upload artifacts de build e download em job de deploy
2. Implemente outputs de job que compartilhem versao e commit SHA
3. Configure retention de artifacts para 1 dia para logs e 90 dias para releases
4. Implemente matrix output aggregation para reportar status de todos os packages
5. Gere SBOM com anchore/sbom-action e upload como artifact
6. Configure size limits e compressao para artifacts grandes
7. Implemente cleanup automatico de artifacts antigos
8. Crie pipeline com versionamento de artifacts
9. Implemente SBOM com scan de vulnerabilidades
10. Configure job outputs para comunicacao entre jobs

---

## 8.12 Referencias

1. https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts
2. https://github.com/actions/upload-artifact
3. https://github.com/actions/download-artifact
4. https://docs.github.com/en/actions/using-jobs/defining-outputs-for-jobs
5. https://github.com/anchore/sbom-action
6. https://github.com/aquasecurity/trivy-action
7. https://github.com/geekyeggo/delete-artifact
8. https://docs.github.com/en/actions/learn-github-actions/contexts#steps-context
9. https://docs.github.com/en/actions/learn-github-actions/contexts#jobs-context
10. https://spdx.org/specifications
11. https://cyclonedx.org/specifications/overview/
12. https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idoutputs

---

## 8.13 Exemplos Avancados de Artifacts

### 8.13.1 Artifacts com Cache Compartilhado

```yaml
name: Shared Artifact Cache

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/cache@v4
        id: cache-deps
        with:
          path: |
            ~/.npm
            node_modules/
          key: deps-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            deps-${{ runner.os }}-

      - name: Install dependencies
        if: steps.cache-deps.outputs.cache-hit != 'true'
        run: npm ci

      - run: npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
          retention-days: 7

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/cache@v4
        with:
          path: |
            ~/.npm
            node_modules/
          key: deps-${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}
          restore-keys: |
            deps-${{ runner.os }}-

      - uses: actions/download-artifact@v4
        with:
          name: build-output
          path: dist/

      - run: npm test
```

### 8.13.2 Artifacts com Multi-Stage Pipeline

```yaml
name: Multi-Stage Pipeline

on: [push, pull_request]

jobs:
  stage-1:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck

  stage-2:
    needs: stage-1
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1

  stage-3:
    needs: stage-2
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - run: npm test

  stage-4:
    needs: stage-3
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - run: npm run deploy
```

### 8.13.3 Artifacts com Conditional Upload

```yaml
name: Conditional Artifacts

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      should-upload: ${{ steps.check.outputs.upload }}
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build

      - id: check
        run: |
          if [ -d "dist" ]; then
            echo "upload=true" >> $GITHUB_OUTPUT
          else
            echo "upload=false" >> $GITHUB_OUTPUT
          fi

      - uses: actions/upload-artifact@v4
        if: steps.check.outputs.upload == 'true'
        with:
          name: dist
          path: dist/
          retention-days: 7

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - uses: actions/download-artifact@v4
        if: needs.build.outputs.should-upload == 'true'
        with:
          name: dist
          path: dist/
      - run: npm test
```

---

## 8.14 Exemplos Avancados de Outputs

### 8.14.1 Outputs com Multiplos Steps

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
      sha: ${{ steps.sha.outputs.s }}
      branch: ${{ steps.branch.outputs.b }}
      timestamp: ${{ steps.timestamp.outputs.t }}
    steps:
      - id: version
        run: echo "v=$(node -p 'require(\"./package.json\").version')" >> $GITHUB_OUTPUT

      - id: sha
        run: echo "s=${{ github.sha }}" >> $GITHUB_OUTPUT

      - id: branch
        run: echo "b=${{ github.ref_name }}" >> $GITHUB_OUTPUT

      - id: timestamp
        run: echo "t=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Version: ${{ needs.build.outputs.version }}"
          echo "SHA: ${{ needs.build.outputs.sha }}"
          echo "Branch: ${{ needs.build.outputs.branch }}"
          echo "Timestamp: ${{ needs.build.outputs.timestamp }}"
```

### 8.14.2 Outputs com JSON Complexo

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.packages.outputs.list }}
      metadata: ${{ steps.metadata.outputs.json }}
    steps:
      - id: packages
        run: |
          PACKAGES=$(find packages -name "package.json" -not -path "*/node_modules/*" | \
            xargs -I {} dirname {} | \
            xargs -I {} basename {} | \
            jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "list=$PACKAGES" >> $GITHUB_OUTPUT

      - id: metadata
        run: |
          METADATA=$(jq -n \
            --arg version "$(node -p 'require(\"./package.json\").version')" \
            --arg sha "${{ github.sha }}" \
            --arg branch "${{ github.ref_name }}" \
            --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            '{version: $version, sha: $sha, branch: $branch, date: $date}')
          echo "json=$METADATA" >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.packages) }}
    steps:
      - run: echo "Testing package: ${{ matrix.package }}"
```

### 8.14.3 Outputs com Validacao

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.version.outputs.v }}
    steps:
      - id: version
        run: |
          VERSION=$(node -p 'require(\"./package.json\").version')
          if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "Invalid version: $VERSION"
            exit 1
          fi
          echo "v=$VERSION" >> $GITHUB_OUTPUT

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: |
          if [ -z "${{ needs.build.outputs.version }}" ]; then
            echo "Version not set"
            exit 1
          fi
          echo "Deploying version ${{ needs.build.outputs.version }}"
```

---

## 8.15 Exemplos de Matrix Output Aggregation

### 8.15.1 Aggregation com Status Detalhado

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api, web]
    outputs:
      results: ${{ steps.results.outputs.json }}
    steps:
      - id: results
        run: |
          if [ "${{ matrix.package }}" = "core" ]; then
            echo '{"core":"success","utils":"pending","api":"pending","web":"pending"}' >> $GITHUB_OUTPUT
          fi

  report:
    needs: build
    runs-on: ubuntu-latest
    if: always()
    steps:
      - name: Generate report
        run: |
          echo "## Build Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Package | Status |" >> $GITHUB_STEP_SUMMARY
          echo "|---------|--------|" >> $GITHUB_STEP_SUMMARY
          echo "| core | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| utils | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| api | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
          echo "| web | ${{ needs.build.result }} |" >> $GITHUB_STEP_SUMMARY
```

### 8.15.2 Aggregation com Artifacts Merge

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  merge:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: dist-*
          path: merged-dist
          merge-multiple: true

      - run: |
          echo "Merged artifacts:"
          find merged-dist -type f | head -20

      - uses: actions/upload-artifact@v4
        with:
          name: merged-dist
          path: merged-dist/
          retention-days: 7
```

### 8.15.3 Aggregation com Notification

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        package: [core, utils, api]
    outputs:
      status: ${{ steps.status.outputs.result }}
    steps:
      - id: status
        run: |
          if [ "${{ matrix.package }}" = "core" ]; then
            echo "result=success" >> $GITHUB_OUTPUT
          fi

  notify:
    needs: build
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Build status: ${{ needs.build.result }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 8.16 Exemplos de SBOM Avancados

### 8.16.1 SBOM Completo com Scan

```yaml
name: Complete SBOM Pipeline

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build

      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1

  sbom:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/

      - name: Generate SBOM (SPDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./dist
          format: spdx-json
          output-file: sbom-spdx.json

      - name: Generate SBOM (CycloneDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./dist
          format: cyclonedx-json
          output-file: sbom-cyclonedx.json

      - name: Scan SBOM for vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'sbom'
          sbom: sbom-spdx.json
          format: 'sarif'
          output: 'vulnerabilities.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload vulnerability scan
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'vulnerabilities.sarif'

      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom-spdx.json
            sbom-cyclonedx.json
            vulnerabilities.sarif
          retention-days: 90
```

### 8.16.2 SBOM para Docker Image

```yaml
name: Docker SBOM

on: [push, pull_request]

jobs:
  build:
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

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: myapp:test
          format: spdx-json
          output-file: sbom.json

      - name: Scan SBOM
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'sbom'
          sbom: sbom.json
          format: 'sarif'
          output: 'vulnerabilities.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'vulnerabilities.sarif'

      - uses: actions/upload-artifact@v4
        with:
          name: sbom-docker
          path: |
            sbom.json
            vulnerabilities.sarif
          retention-days: 90
```

### 8.16.3 SBOM com Compliance

```yaml
name: SBOM Compliance

on: [push, pull_request]

jobs:
  sbom:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: sbom.json

      - name: Validate SBOM
        run: |
          if [ ! -f sbom.json ]; then
            echo "SBOM not generated"
            exit 1
          fi

          # Validate SPDX format
          if ! jq -e '.spdxVersion' sbom.json > /dev/null 2>&1; then
            echo "Invalid SPDX format"
            exit 1
          fi

      - name: Check for critical vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'sbom'
          sbom: sbom.json
          format: 'json'
          output: 'vulnerabilities.json'
          severity: 'CRITICAL'

      - name: Fail if critical vulnerabilities
        run: |
          if jq -e '.Results[].Vulnerabilities | length > 0' vulnerabilities.json > /dev/null 2>&1; then
            echo "Critical vulnerabilities found"
            exit 1
          fi

      - uses: actions/upload-artifact@v4
        with:
          name: sbom-compliance
          path: |
            sbom.json
            vulnerabilities.json
          retention-days: 90
```

---

## 8.17 Tabela Comparativa de Artifacts

| Caracteristica | upload-artifact v4 | upload-artifact v3 | Observacao |
|----------------|-------------------|-------------------|------------|
| Tamanho maximo | 500 MB | 500 MB | Por artifact |
| Total por workflow | 10 GB | 10 GB | Soma de todos |
| Numero de artifacts | 500 | 500 | Por workflow run |
| Compressao | Sim | Sim | Nivel 0-9 |
| Merge | Sim | Nao | Novidade v4 |
| Pattern download | Sim | Nao | Novidade v4 |

---

## 8.18 Fluxo de Decisao de Artifacts

```
                    ┌─────────────┐
                    │   Precisa   │
                    │ artifact?   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Sim/Nao    │
                    └──────┬──────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼──────┐
       │    Sim      │          │     Nao      │
       │             │          │              │
       │ Que tipo?   │          │ Usar outputs │
       └──────┬──────┘          └──────────────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼───┐ ┌──▼──┐ ┌───▼───┐
│ Build │ │Test │ │SBOM   │
│output │ │result│ │       │
│       │ │     │ │       │
│dist/  │ │*.xml│ │sbom.* │
└───────┘ └─────┘ └───────┘
```

---

## 8.19 Checklist de Artifacts

| Item | Verificado |
|------|------------|
| Retention policies configuradas | [ ] |
| Size limits respeitados | [ ] |
| Compressao ativa quando necessario | [ ] |
| Cleanup automatico configurado | [ ] |
| Job outputs definidos | [ ] |
| Step outputs implementados | [ ] |
| Matrix outputs agregados | [ ] |
| SBOM gerado | [ ] |
| SBOM escaneado | [ ] |
| Artifacts versionados | [ ] |

---

## 8.20 Glossario de Artifacts e Outputs

| Termo | Definicao |
|-------|-----------|
| Artifact | Arquivo armazenado por upload-artifact |
| Job output | Dado compartilhado entre jobs |
| Step output | Dado compartilhado entre steps |
| Retention | Tempo de vida de um artifact |
| SBOM | Software Bill of Materials |
| SPDX | Software Package Data Exchange |
| CycloneDX | Padrao SBOM do OWASP |
| Merge | Combinar multiplos artifacts |
| Pattern | Filtro para download de artifacts |
| Compression | Reducao de tamanho de artifacts |

---

## 8.21 Metricas de Artifacts

### 8.21.1 Metricas Importantes

| Metrica | Descricao | Meta |
|---------|-----------|------|
| Tamanho medio | Tamanho medio dos artifacts | < 100 MB |
| Retention media | Tempo medio de retencao | < 30 dias |
| Upload sucesso | Taxa de sucesso de uploads | > 99% |
| Download sucesso | Taxa de sucesso de downloads | > 99% |
| SBOM gerado | Percentage de builds com SBOM | 100% |
| Vulnerabilidades | Numero de vulnerabilidades criticas | 0 |

### 8.21.2 Dashboard de Artifacts

```yaml
name: Artifact Dashboard

on:
  schedule:
    - cron: '0 0 * * 0'  # Toda semana

jobs:
  dashboard:
    runs-on: ubuntu-latest
    steps:
      - name: Generate dashboard
        run: |
          echo "## Artifact Dashboard" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "| Metric | Value |" >> $GITHUB_STEP_SUMMARY
          echo "|--------|-------|" >> $GITHUB_STEP_SUMMARY
          echo "| Total Artifacts | ${{ steps.artifacts.outputs.total }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Total Size | ${{ steps.artifacts.outputs.size }} |" >> $GITHUB_STEP_SUMMARY
          echo "| Average Retention | ${{ steps.artifacts.outputs.retention }} |" >> $GITHUB_STEP_SUMMARY
```

---

## 8.22 Melhores Praticas

### 8.22.1 Regras de Ouro

| Regra | Descricao | Prioridade |
|-------|-----------|------------|
| Usar retention policies | Definir tempo de vida dos artifacts | Alta |
| Comprimir artifacts grandes | Reduzir tamanho para upload/download | Alta |
| Versionar artifacts | Facilitar rastreabilidade | Media |
| Gerar SBOM | Compliance e seguranca | Alta |
| Limpar artifacts antigos | Economizar armazenamento | Media |
| Usar outputs | Comunicacao entre jobs/steps | Alta |
| Validar artifacts | Garantir integridade | Media |
| Documentar artifacts | Facilitar manutencao | Baixa |

### 8.22.2 Anti-Patterns

| Anti-Pattern | Problema | Solucao |
|--------------|----------|---------|
| Sem retention | Acumulo de artifacts | Configurar retention |
| Artifacts muito grandes | Lentidao | Comprimir ou dividir |
| Sem versionamento | Dificuldade de rastreio | Versionar artifacts |
| Sem SBOM | Falta de compliance | Gerar SBOM |
| Sem cleanup | Custo elevado | Configurar cleanup |
| Sem outputs | Comunicacao ruim | Usar job/step outputs |
| Sem validacao | Integridade duvidosa | Validar artifacts |

---

## 8.23 Resumo Final

### 8.23.1 Pontos Principais

1. **Artifacts sao essenciais**: Compartilham dados entre jobs
2. **Retention policies economizam**: Defina tempo de vida adequado
3. **Size limits importam**: Comprima e selecione arquivos
4. **Outputs comunicam**: Use job e step outputs
5. **Matrix outputs agregam**: Colete resultados de matrix builds
6. **SBOM e obrigatorio**: Para compliance e seguranca
7. **Cleanup automático**: Remova artifacts antigos
8. **Versionamento facilita**: Rastreie artifacts por versao

### 8.23.2 Proximos Passos

1. Implementar retention policies em todos os projetos
2. Configurar SBOM generation
3. Implementar job outputs para comunicacao
4. Configurar cleanup automatico
5. Documentar artifacts e outputs
6. Revisar e ajustar regularmente

### 8.23.3 Recursos Adicionais

| Recurso | URL | Descricao |
|---------|-----|-----------|
| GitHub Actions Docs | docs.github.com/actions | Documentacao oficial |
| upload-artifact | github.com/actions/upload-artifact | Action de upload |
| download-artifact | github.com/actions/download-artifact | Action de download |
| anchore/sbom-action | github.com/anchore/sbom-action | Geracao de SBOM |
| SPDX | spdx.org | Padrao SPDX |
| CycloneDX | cyclonedx.org | Padrao CycloneDX |

---

## 8.24 Exercicios Adicionais

11. Implemente pipeline com artifacts versionados por tag
12. Configure SBOM com scan de vulnerabilidades e falha se encontrar criticas
13. Implemente matrix output aggregation com notification Slack
14. Crie pipeline com multi-stage artifacts e cache compartilhado
15. Implemente cleanup automatico de artifacts baseado em idade

---

## 8.25 Versao deste Documento

| Campo | Valor |
|-------|-------|
| Versao | 1.0 |
| Data | 2024 |
| Autor | Equipe DevSecurity |
| Licenca | MIT |
| Status | Producao |

---

## 8.26 Exemplos de Casos Reais Detalhados

### 8.26.1 Pipeline Full Stack com Artifacts Completos

Pipeline completa para aplicacao full stack com artifacts, outputs, SBOM e cleanup.

```yaml
name: Full Stack Complete Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

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
      - run: npm run prettier:check

  typecheck:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run typecheck

  test-unit:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:unit -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: unit-coverage
          path: coverage/
          retention-days: 7

  test-integration:
    needs: [lint, typecheck]
    runs-on: ubuntu-latest
    timeout-minutes: 30
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
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run test:integration
        env:
          DATABASE_URL: postgres://postgres:test@localhost:5432/testdb

  build:
    needs: [test-unit, test-integration]
    runs-on: ubuntu-latest
    timeout-minutes: 15
    outputs:
      version: ${{ steps.version.outputs.v }}
      sha: ${{ steps.sha.outputs.s }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build

      - id: version
        run: echo "v=$(node -p 'require(\"./package.json\").version')" >> $GITHUB_OUTPUT

      - id: sha
        run: echo "s=${{ github.sha }}" >> $GITHUB_OUTPUT

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
          retention-days: 30

  sbom:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/

      - name: Generate SBOM (SPDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./dist
          format: spdx-json
          output-file: sbom-spdx.json

      - name: Generate SBOM (CycloneDX)
        uses: anchore/sbom-action@v0
        with:
          path: ./dist
          format: cyclonedx-json
          output-file: sbom-cyclonedx.json

      - name: Scan SBOM for vulnerabilities
        uses: aquasecurity/trivy-action@0.28.0
        with:
          scan-type: 'sbom'
          sbom: sbom-spdx.json
          format: 'sarif'
          output: 'vulnerabilities.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload vulnerability scan
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'vulnerabilities.sarif'

      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom-spdx.json
            sbom-cyclonedx.json
            vulnerabilities.sarif
          retention-days: 90

  coverage:
    needs: test-unit
    if: always()
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: unit-coverage
          path: coverage/
      - uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: coverage/lcov.info
          flags: unittests
          fail_ci_if_error: false

  docker:
    needs: build
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha
            type=ref,event=branch
            type=semver,pattern={{version}}

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

  deploy-preview:
    needs: [build, sbom, docker]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - uses: actions/download-artifact@v4
        with:
          name: sbom
          path: .
      - name: Deploy preview
        run: |
          echo "Deploying preview for PR #${{ github.event.pull_request.number }}"
          echo "Version: ${{ needs.build.outputs.version }}"
          echo "SBOM: $(ls -la sbom-*.json)"

  deploy-staging:
    needs: [build, sbom, docker]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - name: Deploy to staging
        run: |
          echo "Deploying to staging"
          echo "Version: ${{ needs.build.outputs.version }}"

  deploy-production:
    needs: [deploy-staging, coverage]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - uses: actions/download-artifact@v4
        with:
          name: sbom
          path: .
      - name: Deploy to production
        run: |
          echo "Deploying to production"
          echo "Version: ${{ needs.build.outputs.version }}"
          echo "SBOM: $(ls -la sbom-*.json)"
          ./deploy.sh

  release:
    needs: [deploy-production, sbom]
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ github.sha }}
          path: dist/
      - uses: actions/download-artifact@v4
        with:
          name: sbom
          path: .
      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            dist/*
            sbom-spdx.json
            sbom-cyclonedx.json

  cleanup:
    needs: [release]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Delete old artifacts
        uses: actions/github-script@v7
        with:
          script: |
            const artifacts = await github.rest.actions.listWorkflowArtifacts({
              owner: context.repo.owner,
              repo: context.repo.repo
            });

            for (const artifact of artifacts.data.artifacts) {
              const daysSinceCreation = (Date.now() - new Date(artifact.created_at).getTime()) / (1000 * 60 * 60 * 24);

              if (daysSinceCreation > 30) {
                await github.rest.actions.deleteArtifact({
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  artifact_id: artifact.id
                });
              }
            }
```

### 8.26.2 Pipeline Monorepo com Artifacts

Pipeline completa para monorepo com artifacts por pacote.

```yaml
name: Monorepo Artifacts Pipeline

on: [push, pull_request]

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      packages: ${{ steps.changes.outputs.packages }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            packages:
              - 'packages/**'

  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.packages == 'true'
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - uses: actions/checkout@v4

      - name: Detect packages
        id: set-matrix
        run: |
          PACKAGES=$(find packages -name "package.json" -not -path "*/node_modules/*" | \
            xargs -I {} dirname {} | \
            xargs -I {} basename {} | \
            jq -R -s -c 'split("\n") | map(select(length > 0))')
          echo "matrix={\"package\":$PACKAGES}" >> $GITHUB_OUTPUT

  test:
    needs: build
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test --workspace=packages/${{ matrix.package }}

  build-packages:
    needs: test
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build --workspace=packages/${{ matrix.package }}

      - uses: actions/upload-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
          retention-days: 1

  sbom:
    needs: build-packages
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: sbom.json

      - uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
          retention-days: 90

  merge:
    needs: build-packages
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: dist-*
          path: merged-dist
          merge-multiple: true

      - run: |
          echo "Merged artifacts:"
          find merged-dist -type f | head -20

      - uses: actions/upload-artifact@v4
        with:
          name: merged-dist
          path: merged-dist/
          retention-days: 7

  publish:
    needs: [merge, sbom]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.build.outputs.matrix) }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          registry-url: 'https://registry.npmjs.org'
      - uses: actions/download-artifact@v4
        with:
          name: dist-${{ matrix.package }}
          path: packages/${{ matrix.package }}/dist/
      - name: Publish
        run: |
          cd packages/${{ matrix.package }}
          npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## 8.27 Tabela de Decisao Final

| Cenario | Estrategia Recomendada | Prioridade | Impacto |
|---------|------------------------|------------|---------|
| Projeto simples | Artifacts basicos + outputs | Media | Medio |
| Full stack | Artifacts + SBOM + cleanup | Alta | Alto |
| Monorepo | Artifacts por pacote + merge | Alta | Alto |
| Multi-platform | Artifacts por plataforma | Media | Medio |
| Enterprise | Artifacts + SBOM + compliance | Alta | Muito alto |
| Open source | Artifacts basicos + SBOM | Media | Medio |

---

## 8.28 Fluxo de Trabalho Recomendado

### 8.28.1 Para Projetos Novos

1. Configure artifacts basicos para build output
2. Implemente job outputs para comunicacao
3. Configure retention policies
4. Adicione SBOM generation
5. Implemente cleanup automatico

### 8.28.2 Para Projetos Existentes

1. Audite artifacts atuais
2. Otimize retention policies
3. Implemente SBOM se nao existir
4. Configure cleanup automatico
5. Documentar artifacts e outputs

### 8.28.3 Para Monorepos

1. Configure artifacts por pacote
2. Implemente merge de artifacts
3. Configure SBOM para todos os pacotes
4. Implemente cleanup por pacote
5. Monitore custos por pacote

---

## 8.29 Checklist Final

| Item | Verificado | Observacao |
|------|------------|------------|
| Artifacts configurados | [ ] | Para todos os jobs necessarios |
| Retention policies | [ ] | Definidas por tipo de artifact |
| Size limits | [ ] | Respeitados e monitorados |
| Job outputs | [ ] | Definidos para comunicacao |
| Step outputs | [ ] | Implementados quando necessario |
| Matrix outputs | [ ] | Agregados corretamente |
| SBOM gerado | [ ] | Em formato SPDX ou CycloneDX |
| SBOM escaneado | [ ] | Vulnerabilidades verificadas |
| Cleanup configurado | [ ] | Automatico e regular |
| Versionamento | [ ] | Artifacts versionados |
| Documentacao | [ ] | Artifacts e outputs documentados |
| Monitoring | [ ] | Custos e uso monitorados |

---

## 8.30 Resumo Completo

### 8.30.1 Pontos Principais

1. **Artifacts sao a ponte**: Compartilham dados entre jobs
2. **Outputs comunicam**: Entre jobs e steps
3. **Retention economiza**: Defina tempo de vida adequado
4. **SBOM e obrigatorio**: Para compliance e seguranca
5. **Cleanup limpa**: Remova artifacts antigos
6. **Versionamento rastreia**: Facilite debugging
7. **Matrix outputs agregam**: Colete resultados
8. **Compression reduz**: Otimize upload/download

### 8.30.2 Proximos Passos

1. Implementar artifacts em todos os projetos
2. Configurar SBOM generation
3. Implementar job e step outputs
4. Configure cleanup automatico
5. Documentar artifacts e outputs
6. Revisar e ajustar regularmente
7. Monitorar custos
8. Compartilhar aprendizados com a equipe

---

## 8.31 Agradecimentos

Este capitulo foi elaborado com base nas melhores praticas da comunidade de GitHub Actions. Agradecemos a todos os contribuidores que compartilham conhecimento e experiencia no desenvolvimento de pipelines de CI/CD eficientes e confiaveis.

---

## 8.32 Glossario Completo

| Termo | Definicao | Exemplo de Uso |
|-------|-----------|----------------|
| Artifact | Arquivo armazenado por upload-artifact | dist/, coverage/ |
| Job output | Dado compartilhado entre jobs | needs.build.outputs.version |
| Step output | Dado compartilhado entre steps | steps.check.outputs.result |
| Retention | Tempo de vida de um artifact | retention-days: 30 |
| SBOM | Software Bill of Materials | sbom.json |
| SPDX | Software Package Data Exchange | sbom-spdx.json |
| CycloneDX | Padrao SBOM do OWASP | sbom-cyclonedx.json |
| Merge | Combinar multiplos artifacts | merge-multiple: true |
| Pattern | Filtro para download de artifacts | pattern: dist-* |
| Compression | Reducao de tamanho de artifacts | compression-level: 9 |
| Matrix output | Output agregado de matrix build | needs.build.outputs.results |
| Cleanup | Remocao automatica de artifacts | delete-artifact |
| Versioning | Controle de versao de artifacts | dist-${{ github.sha }} |
| Compliance | Conformidade com normas | SBOM obrigatorio |

---

## 8.33 Tabela de Referencia Rapida

### 8.33.1 Upload Artifact

| Opcao | Tipo | Descricao | Default |
|-------|------|-----------|---------|
| name | string | Nome do artifact | Obrigatorio |
| path | string | Caminho dos arquivos | Obrigatorio |
| retention-days | number | Dias de retencao | 90 |
| compression-level | number | Nivel de compressao (0-9) | 6 |
| if-no-files-found | string | Comportamento se nao encontrar | warn |

### 8.33.2 Download Artifact

| Opcao | Tipo | Descricao | Default |
|-------|------|-----------|---------|
| name | string | Nome do artifact | Obrigatorio (ou pattern) |
| pattern | string | Pattern para filtrar | - |
| path | string | Caminho de destino | . |
| merge-multiple | boolean | Merge multiplos artifacts | false |

### 8.33.3 Job Outputs

| Opcao | Tipo | Descricao | Default |
|-------|------|-----------|---------|
| outputs | map | Mapa de outputs | - |

### 8.33.4 Step Outputs

| Formato | Exemplo |
|---------|---------|
| Simples | echo "key=value" >> $GITHUB_OUTPUT |
| Multi-line | echo "key<<EOF" >> $GITHUB_OUTPUT |
| JSON | echo "key={}" >> $GITHUB_OUTPUT |

---

## 8.34 Fluxo de Decisao Completo

```
                    ┌─────────────┐
                    │  Workflow   │
                    │   Trigger   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Build      │
                    │  Job        │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │   Upload    │ │Output│ │    SBOM     │
       │  Artifact   │ │      │ │  Generation │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │   Test      │
                    │   Job       │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Download   │
                    │  Artifact   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Deploy    │
                    │   Job       │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Cleanup   │
                    │   Old       │
                    │  Artifacts  │
                    └─────────────┘
```

---

## 8.35 Versao Final deste Documento

| Campo | Valor |
|-------|-------|
| Versao | 1.0 |
| Data | 2024 |
| Autor | Equipe DevSecurity |
| Licenca | MIT |
| Status | Producao |
| Total de Secoes | 35 |
| Total de Exemplos | 50+ |
| Total de Tabelas | 20+ |

---

## 8.36 Recursos Finais

### 8.36.1 Links Uteis

| Recurso | URL | Descricao |
|---------|-----|-----------|
| GitHub Actions Docs | docs.github.com/actions | Documentacao oficial |
| upload-artifact | github.com/actions/upload-artifact | Action de upload |
| download-artifact | github.com/actions/download-artifact | Action de download |
| anchore/sbom-action | github.com/anchore/sbom-action | Geracao de SBOM |
| SPDX | spdx.org | Padrao SPDX |
| CycloneDX | cyclonedx.org | Padrao CycloneDX |
| CodeQL | github.com/github/codeql-action | Security scanning |
| Trivy | trivy.dev | Vulnerability scanning |
| Codecov | codecov.io | Code coverage |

### 8.36.2 Comunidade

| Recurso | URL | Descricao |
|---------|-----|-----------|
| GitHub Community | github.community | Forum da comunidade |
| GitHub Actions Market | github.com/marketplace?type=actions | Actions populares |
| GitHub Learning Lab | lab.github.com | Cursos interativos |
| GitHub Status | www.githubstatus.com | Status dos servicos |

---

## 8.37 Notas Finais

Este capitulo cobriu todos os aspectos de artifacts e outputs no GitHub Actions, desde o basico ate exemplos avancados de casos reais. Lembre-se de:

1. **Planejar antes de implementar**: Defina quais artifacts sao necessarios
2. **Otimizar continuamente**: Revise retention policies e cleanup
3. **Documentar decisoes**: Registre por que certos artifacts existem
4. **Monitorar custos**: Artifacts consomem armazenamento
5. **Compartilhar conhecimento**: Ensine a equipe sobre melhores praticas

O uso correto de artifacts e outputs e fundamental para pipelines de CI/CD eficientes e confiaveis. Use as estrategias deste capitulo como base para seus proprios projetos.

---

## 8.38 Agradecimentos Finais

Agradecemos a todos que contribuiram para a criacao deste material. O conhecimento compartilhado fortalece a comunidade de desenvolvimento de software.

---

## 8.39 Contato e Suporte

Para duvidas ou sugestoes, abra uma issue no repositorio ou entre em contato com a equipe de DevSecurity.
---

*[Capítulo anterior: 07 — Caching Performance](07-caching-performance.md)*
*[Próximo capítulo: 09 — Secrets Variaveis](09-secrets-variaveis.md)*
