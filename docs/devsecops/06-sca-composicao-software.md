---
layout: default
title: "06-sca-composicao-software"
---

# Capítulo 6 — SCA: Análise de Composição de Software

## Sumário

- [6.1 O que é SCA](#61-o-que-é-sca)
- [6.2 SBOM (Software Bill of Materials)](#62-sbom-software-bill-of-materials)
- [6.3 Trivy](#63-trivy)
- [6.4 Snyk](#64-snyk)
- [6.5 OWASP Dependency-Check](#65-owasp-dependency-check)
- [6.6 GitHub Dependabot](#66-github-dependabot)
- [6.7 Gerenciamento de Vulnerabilidades](#67-gerenciamento-de-vulnerabilidades)
- [6.8 Políticas de Dependências](#68-políticas-de-dependências)
- [6.9 Exemplo Completo: Pipeline SCA](#69-exemplo-completo-pipeline-sca)
- [6.10 Referências](#610-referências)

---

## 6.1 O que é SCA

### 6.1.1 Definição e Conceito

Software Composition Analysis (SCA) é uma prática de segurança que consiste em identificar, rastrear e analisar todas as dependências de software utilizadas em um projeto. SCA verifica bibliotecas open-source e componentes de terceiros para detectar vulnerabilidades conhecidas, problemas de licenciamento e riscos de conformidade.

O problema central é simples: nenhum software moderno é escrito do zero. Projetos utilizam centenas — às vezes milhares — de dependências. Cada uma dessas dependências é um potencial vetor de ataque. SCA existe para mapear esse risco.

### 6.1.2 Por que dependências são um vetor de ataque significativo

Estudos recentes mostram que mais de 70% do código em aplicações modernas é composto por dependências de terceiros. Isso significa que a maior parte do código executado em produção não foi escrito pela equipe de desenvolvimento.

O ataque vetorial funciona da seguinte forma:

1. Desenvolvedores incluem uma dependência popular em seus projetos
2. Essa dependência inclui outras dependências (dependências transitivas)
3. Uma vulnerabilidade é descoberta em qualquer ponto dessa cadeia
4. Todo projeto que depende indiretamente do componente vulnerável fica exposto

### 6.1.3 O problema das dependências transitivas

Considere um cenário real: um projeto Python que depende do Django. O Django, por sua vez, depende de dezenas de outras bibliotecas. Cada uma dessas bibliotecas pode ter suas próprias dependências. Uma vulnerabilidade na biblioteca `a` afeta o Django, que afeta seu projeto — mesmo que você nunca tenha incluído `a` diretamente.

```bash
# Visualizando a árvore de dependências de um projeto Node.js
npm list --all

# Exemplo de saída:
# myapp@1.0.0
# +-- express@4.18.2
# |   +-- accepts@1.3.8
# |   |   +-- mime-types@2.1.35
# |   |   |   +-- mime-db@1.52.0
# |   |   +-- negotiator@0.6.3
# |   +-- body-parser@1.20.1
# |   |   +-- bytes@3.1.2
# |   |   +-- content-type@1.0.5
# |   |   +-- depd@2.0.0
# |   +-- debug@2.6.9
# |   |   +-- ms@2.0.0
# |   +-- finalhandler@1.2.0
# |   +-- forwarded@0.2.0
# |   +-- fresh@0.5.2
# |   +-- merge-descriptors@1.0.3
# |   +-- on-finished@2.0.0
# |   |   +-- ee-first@1.1.2
# |   +-- parseurl@1.3.3
# |   +-- path-to-regexp@0.1.7
# |   +-- proxy-addr@2.0.0
# |   |   +-- forwarded@0.2.0
# |   |   +-- ipaddr.js@1.9.1
# |   +-- qs@6.11.0
# |   |   +-- side-channel@1.0.4
# |   +-- range-parser@1.2.1
# |   +-- safe-buffer@5.2.1
# |   +-- send@0.18.0
# |   |   +-- destroy@1.2.0
# |   |   +-- etag@1.8.1
# |   |   +-- mime@1.6.0
# |   |   +-- ms@2.1.3
# |   +-- serve-static@1.15.0
# |   |   +-- encodeurl@1.0.2
# |   |   +-- escape-html@1.0.3
# |   |   +-- parseurl@1.3.3
# |   +-- setprototypeof@1.2.0
# |   +-- statuses@2.0.1
# |   +-- type-is@1.6.18
# |   |   +-- media-typer@0.3.0
# |   +-- utils-merge@1.0.1
# |   +-- vary@1.1.2
# +-- requests@2.31.0
# +-- urllib3@2.0.4
# |   +-- certifi@2023.7.22
# |   +-- charset-normalizer@3.2.0
# |   +-- idna@3.4
# |   +-- six@1.16.0
```

### 6.1.4 O conceito de árvore de dependências

A árvore de dependências é uma estrutura em grafo que representa todas as dependências diretas e transitivas de um projeto. Cada nó é um pacote, e cada aresta representa uma relação de dependência.

A complexidade dessa árvore cresce exponencialmente. Um projeto com 50 dependências diretas pode ter mais de 10.000 dependências transitivas. Isso torna impossível para seres humanos rastrearem manualmente os riscos de segurança.

### 6.1.5 Caso Real: event-stream (2018)

Em novembro de 2018, o pacote npm `event-stream` foi comprometido de forma sofisticada. O maintainer original, que estava sobrecarregado e sem energia para manter o pacote, transferiu a manutenção para um voluntário. Esse voluntário era um atacante que:

1. Injeção maliciosa no código: O atacante adicionou uma dependência chamada `flatmap-stream` que continha código malicioso
2. Alvo específico: O malware foi projetado para roubar criptomoedas de carteiras associadas à empresa Copay
3. Temporização inteligente: O código malicioso só era ativado em ambientes de produção com o módulo Copay instalado
4. Dificuldade de detecção: O código era ofuscado e难难 para detectar em revisões superficiais

```javascript
// Exemplo simplificado do que aconteceu no event-stream
// O malware foi injetado através de uma dependência aparentemente inofensiva

// package.json do event-stream v3.3.6 (comprometido)
{
  "name": "event-stream",
  "version": "3.3.6",
  "dependencies": {
    "flatmap-stream": "0.1.1"
  }
}

// flatmap-stream continha código malicioso que:
// 1. Verificava se estava rodando em produção
// 2. Procurava por chaves de carteira Copay específicas
// 3. Enviava informações de carteira para um servidor externo
// 4. Permitia roubo de criptomoedas
```

### 6.1.6 Caso Real: left-pad

Em 2016, o autor do pacote npm `left-pad` (usado por milhões de projetos) o removeu do registro como forma de protesto. O resultado foi o colapso de builds em toda a internet, incluindo projetos do Facebook e React. Esse incidente demonstrou a fragilidade das dependências de software e a necessidade de:

- Mirror de pacotes e cache local
- Políticas de versionamento rígidas
- Análise de riscos de dependências críticas

---

## 6.2 SBOM (Software Bill of Materials)

### 6.2.1 O que é SBOM e por que importa

Um SBOM (Software Bill of Materials) é uma lista estruturada de todos os componentes, bibliotecas e módulos que compõem um software. Assim como uma lista de ingredientes em um produto alimentício, o SBOM lista tudo o que está "dentro" do seu software.

O SBOM é fundamental para:

- **Rastreabilidade**: Saber exatamente quais componentes estão em produção
- **Resposta a incidentes**: Quando uma vulnerabilidade é descoberta, saber imediatamente quais sistemas são afetados
- **Conformidade**: Atender a requisitos regulatórios e de licenciamento
- **Due diligence**: Avaliar riscos antes de adotar um software

### 6.2.2 Formato SPDX

SPDX (Software Package Data Exchange) é um formato padronizado pela Linux Foundation para troca de informações sobre componentes de software.

```yaml
# Exemplo de SBOM no formato SPDX
SPDXVersion: SPDX-2.3
DataLicense: CC0-1.0
SPDXID: SPDXRef-DOCUMENT
DocumentName: meu-projeto
DocumentNamespace: https://example.com/meu-projeto
Creator: Tool: trivy-0.45.0
Created: 2024-01-15T10:30:00Z

PackageName: express
SPDXID: SPDXRef-Package-express
PackageVersion: 4.18.2
PackageSupplier: Organization: Joyent
PackageDownloadLocation: https://registry.npmjs.org/express/-/express-4.18.2.tgz
FilesAnalyzed: false
PackageLicenseDeclared: MIT
PackageCopyrightText: NOASSERTION
ExternalRef: SECURITY cpe23Type cpe:2.3:a:expressjs:express:4.18.2:*:*:*:*:node.js:*:*

PackageName: lodash
SPDXID: SPDXRef-Package-lodash
PackageVersion: 4.17.21
PackageSupplier: Organization: jQuery Foundation
PackageDownloadLocation: https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz
FilesAnalyzed: false
PackageLicenseDeclared: MIT
PackageCopyrightText: NOASSERTION
ExternalRef: SECURITY cpe23Type cpe:2.3:a:lodash:lodash:4.17.21:*:*:*:*:*:*:*
```

### 6.2.3 Formato CycloneDX

CycloneDX é um formato de SBOM desenvolvido pela OWASP, otimizado para segurança e uso em pipelines de DevSecOps.

```xml
<!-- Exemplo de SBOM no formato CycloneDX -->
<bom serialNumber="urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79"
     version="1">
  <metadata>
    <timestamp>2024-01-15T10:30:00Z</timestamp>
    <tools>
      <tool>
        <vendor>OWASP</vendor>
        <name>cyclonedx-cli</name>
        <version>0.24.0</version>
      </tool>
    </tools>
    <component type="application" bom-ref="my-app">
      <name>my-app</name>
      <version>1.0.0</version>
    </component>
  </metadata>
  <components>
    <component type="library" bom-ref="pkg:npm/express@4.18.2">
      <name>express</name>
      <version>4.18.2</version>
      <purl>pkg:npm/express@4.18.2</purl>
      <externalReferences>
        <reference type="website">
          <url>https://expressjs.com</url>
        </reference>
      </externalReferences>
    </component>
    <component type="library" bom-ref="pkg:npm/lodash@4.17.21">
      <name>lodash</name>
      <version>4.17.21</version>
      <purl>pkg:npm/lodash@4.17.21</purl>
    </component>
  </components>
  <dependencies>
    <dependency ref="pkg:npm/express@4.18.2">
      <dependency ref="pkg:npm/lodash@4.17.21"/>
    </dependency>
  </dependencies>
</bom>
```

### 6.2.4 Gerando SBOMs

Existem diversas ferramentas para gerar SBOMs. Aqui estão as principais:

```bash
# Trivy - Gera SBOM em SPDX e CycloneDX
trivy fs --format spdx-json --output sbom-spdx.json .
trivy fs --format cyclonedx --output sbom-cdx.json .

# Syft - Ferramenta específica para SBOM
syft scan dir:. -o spdx-json > sbom-spdx.json
syft scan dir:. -o cyclonedx-json > sbom-cdx.json

# CycloneDX para Node.js
npm install -g @cyclonedx/cyclonedx-npm
cyclonedx-npm --output-file sbom-cdx.json

# CycloneDX para Python
pip install cyclonedx-bom
cyclonedx-py environment --format json --output-file sbom-cdx.json

# CycloneDX para Java (Maven)
mvn org.cyclonedx:cyclonedx-maven-plugin:makeBom

# SPDX Tools para validação
spdx-tools validate -f json sbom-spdx.json
```

### 6.2.5 Pipeline completa de geração de SBOM

```yaml
# .github/workflows/sbom-generation.yml
name: SBOM Generation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  generate-sbom:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Generate SBOM with Trivy
        run: |
          # Gerar SBOM no formato SPDX
          trivy fs \
            --format spdx-json \
            --output sbom-spdx.json \
            .
          
          # Gerar SBOM no formato CycloneDX
          trivy fs \
            --format cyclonedx \
            --output sbom-cdx.json \
            .
      
      - name: Generate SBOM with Syft
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: syft-sbom.spdx.json
      
      - name: Validate SBOM
        run: |
          # Instalar validador SPDX
          pip install spdx-tools
          
          # Validar SBOM gerado
          spdx-tools validate -f json sbom-spdx.json
      
      - name: Upload SBOM artifacts
        uses: actions/upload-artifact@v4
        with:
          name: sbom-reports
          path: |
            sbom-spdx.json
            sbom-cdx.json
            syft-sbom.spdx.json
          retention-days: 90
      
      - name: Scan SBOM for vulnerabilities
        run: |
          # Usar Trivy para escanear o SBOM gerado
          trivy sbom sbom-spdx.json \
            --severity HIGH,CRITICAL \
            --format json \
            --output sbom-vulnerabilities.json
```

### 6.2.6 Elementos mínimos do NTIA

O National Telecommunications and Information Administration (NTIA) define os elementos mínimos que um SBOM deve conter:

1. **Nome do autor do SBOM**: Organização responsável pela criação do SBOM
2. **Nome do supplier**: Fornecedor de cada componente
3. **Nome do componente**: Nome único de cada biblioteca
4. **Versão do componente**: Versão exata utilizada
5. **Identificador único**: SPDX ID ou outro identificador único
6. **Relationship**: Como os componentes se relacionam
7. **Data de criação**: Quando o SBOM foi gerado
8. **Hash criptográfico**: Integridade verificável do componente

```bash
# Script para validar SBOM contra requisitos NTIA
#!/bin/bash

validate_sbom_ntia() {
    local sbom_file=$1
    local errors=0
    
    echo "Validando SBOM contra requisitos NTIA..."
    
    # Verificar se o arquivo existe
    if [ ! -f "$sbom_file" ]; then
        echo "ERRO: Arquivo SBOM não encontrado: $sbom_file"
        return 1
    fi
    
    # Verificar elementos obrigatórios
    local required_fields=("author" "supplier" "componentName" "version" "uniqueId")
    
    for field in "${required_fields[@]}"; do
        if ! jq -e "select(.$field != null)" "$sbom_file" > /dev/null 2>&1; then
            echo "AVISO: Campo obrigatório NTIA ausente: $field"
            ((errors++))
        fi
    done
    
    # Verificar se há pelo menos um componente
    local component_count=$(jq '.components | length' "$sbom_file" 2>/dev/null || echo 0)
    if [ "$component_count" -eq 0 ]; then
        echo "AVISO: SBOM não contém componentes"
        ((errors++))
    fi
    
    echo "Componentes encontrados: $component_count"
    echo "Erros encontrados: $errors"
    
    if [ $errors -eq 0 ]; then
        echo "SBOM atende aos requisitos mínimos do NTIA"
        return 0
    else
        echo "SBOM NÃO atende aos requisitos mínimos do NTIA"
        return 1
    fi
}

# Uso
validate_sbom_ntia "sbom-spdx.json"
```

---

## 6.3 Trivy

### 6.3.1 Instalação e uso

Trivy é uma ferramenta completa de segurança que suporta múltiplos alvos: containers, sistemas de arquivos, repositórios Git, e até SBOMs. É de código aberto e mantida pela Aqua Security.

```bash
# Instalação no Ubuntu/Debian
sudo apt-get install wget apt-transport-https gnupg lsb-release
wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
echo "deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/trivy.list
sudo apt-get update
sudo apt-get install trivy

# Instalação via Docker
docker pull aquasec/trivy:latest

# Instalação via Homebrew (macOS)
brew install trivy

# Instalação via script
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Verificar versão
trivy version
```

### 6.3.2 Escaneando containers

```bash
# Escanear imagem Docker local
trivy image nginx:latest

# Escanear com severidade específica
trivy image --severity HIGH,CRITICAL nginx:latest

# Escanear imagem de repositório remoto
trivy image docker.io/library/python:3.11-slim

# Escanear imagem específicando formato de saída
trivy image --format json --output results.json nginx:latest

# Escanear ignorando CVEs específicos
trivy image --ignore-unfixed nginx:latest

# Escanear com timeout estendido
trivy image --timeout 10m nginx:latest

# Escanear imagem multi-platform
trivy image --platform linux/amd64 nginx:latest
```

### 6.3.3 Escaneando filesystems

```bash
# Escanear diretório atual
trivy fs .

# Escanear com formato de saída específico
trivy fs --format table .
trivy fs --format json --output fs-results.json .

# Escanear apenas vulnerabilidades de alta severidade
trivy fs --severity HIGH,CRITICAL .

# Escanear ignorando dependências de desenvolvimento
trivy fs --skip-dirs node_modules,.git .

# Escanear com scanners específicos
trivy fs --scanners vuln,secret,misconfig .

# Escanear e exibir saída em formato SARIF
trivy fs --format sarif --output results.sarif .
```

### 6.3.4 Escaneando repositórios

```bash
# Escanear repositório local
trivy repo /caminho/para/repo

# Escanear repositório Git remoto
trivy repo https://github.com/usuario/repositorio

# Escanear branch específica
trivy repo --branch develop https://github.com/usuario/repositorio

# Escanear com credenciais para repositórios privados
trivy repo --username user --password pass https://github.com/empresa/repo-privado

# Escanear apenas commits recentes
trivy repo --commit 1234567 https://github.com/usuario/repositorio
```

### 6.3.5 Database de vulnerabilidades

```bash
# Atualizar database de vulnerabilidades
trivy image --download-db-only

# Usar database específico
trivy image --db-repository ghcr.io/aquasecurity/trivy-db nginx:latest

# Escanear offline com database pré-baixado
trivy image --offline-scan nginx:latest

# Verificar informações do database
trivy image --db-repository ghcr.io/aquasecurity/trivy-db --list-all-pkgs nginx:latest

# Escanear com database customizado
trivy image --db-repository meu-registry.com/trivy-db nginx:latest
```

### 6.3.6 Políticas customizadas

```bash
# Criar arquivo de política (.trivyignore)
cat > .trivyignore << 'EOF'
# CVEs ignorados com justificativa
CVE-2023-12345
# Justificativa: Vulnerabilidade não aplicável ao nosso caso de uso
# Data de revisão: 2024-01-15
# Revisado por: equipe-seguranca

CVE-2023-67890
# Justificativa: Patch disponível mas requer testes adicionais
# Data de revisão: 2024-01-20
# Próxima revisão: 2024-02-20
EOF

# Usar política de ignore
trivy image --ignorefile .trivyignore nginx:latest

# Criar arquivo de política YAML
cat > trivy-policy.yaml << 'EOF'
severity:
  - HIGH
  - CRITICAL

ignore-unfixed: true

skip-dirs:
  - node_modules
  - .git
  - test

skip-files:
  - "**/*_test.go"
  - "**/*.test.js"

ignore-licenses:
  - GPL-2.0
  - GPL-3.0
EOF

# Aplicar política
trivy fs --config trivy-policy.yaml .
```

### 6.3.7 Pipeline completa com Trivy

```yaml
# .github/workflows/trivy-security.yml
name: Trivy Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira às 6h

jobs:
  trivy-scan:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy scan results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
      
      - name: Run Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'table'
          severity: 'CRITICAL,HIGH'
      
      - name: Generate SBOM
        run: |
          trivy fs \
            --format cyclonedx \
            --output sbom.json \
            .
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
          retention-days: 30
```

### 6.3.8 Configuração do arquivo de ignore

```bash
# Criar .trivyignore detalhado
cat > .trivyignore << 'EOF'
# Formato: CVE-ID
# Comentários começam com #

# ============================================================
# CVEs ignorados permanentemente
# ============================================================

# CVE-2021-44228 (Log4Shell)
# Status: Mitigado via configuração
# Data da mitigação: 2021-12-14
# Revisado por: João Silva
# Justificativa: Não utilizamos JNDI lookup
CVE-2021-44228

# ============================================================
# CVEs ignorados temporariamente
# ============================================================

# CVE-2023-44487 (HTTP/2 Rapid Reset)
# Status: Aguardando patch da dependência
# Data de expiração: 2024-02-28
# Responsável: Maria Santos
CVE-2023-44487

# CVE-2023-12345 (Vulnerabilidade em biblioteca de log)
# Status: Patch em teste
# Data de expiração: 2024-03-15
# Próxima revisão: 2024-02-15
CVE-2023-12345
EOF

# Validar formato do .trivyignore
trivy image --validate-ignore nginx:latest
```

---

## 6.4 Snyk

### 6.4.1 Configuração e instalação

```bash
# Instalar CLI do Snyk
npm install -g snyk

# Autenticar com token
snyk auth

# Verificar versão
snyk --version

# Configurar org ID
snyk config set org=meu-org-id
```

### 6.4.2 Monitorando dependências

```bash
# Escanear projeto Node.js
snyk test

# Escanear com severidade específica
snyk test --severity-threshold=high

# Monitorar projeto (cria snapshot para monitoramento contínuo)
snyk monitor

# Monitorar com tags específicas
snyk monitor --tags=team=backend,env=production

# Monitorar arquivo específico
snyk test --file=package.json
snyk test --file=pom.xml

# Escanear e gerar relatório
snyk test --json > snyk-results.json
snyk test --sarif > snyk-results.sarif
```

### 6.4.3 Fix PRs automatizados

```bash
# Criar fix PR automaticamente
snyk wizard

# Para dependências específicas
snyk wizard --org=meu-org-id

# Criar PR com correções de segurança
snyk test --fix

# Verificar correções disponíveis
snyk test --preview

# Fix para patch-level apenas
snyk test --only-upgrades

# Fix ignorando testes
snyk test --bypass
```

### 6.4.4 Escaneamento de containers

```bash
# Escanear imagem Docker
snyk container test nginx:latest

# Escanear com severidade específica
snyk container test nginx:latest --severity-threshold=high

# Monitorar imagem
snyk container monitor nginx:latest

# Escanear Dockerfile para melhores práticas
snyk container test --dockerfile=Dockerfile .

# Gerar relatório de container
snyk container test --json nginx:latest > container-results.json
```

### 6.4.5 Escaneamento de IaC

```bash
# Escanear Terraform
snyk iac test main.tf

# Escanear CloudFormation
snyk iac test template.yaml

# Escanear Kubernetes
snyk iac test deployment.yaml

# Escanear diretório inteiro
snyk iac test .

# Escanear com severidade específica
snyk iac test --severity-threshold=high .

# Gerar relatório SARIF
snyk iac test --sarif-file=iac-results.sarif .
```

### 6.4.6 Integração completa do Snyk

```yaml
# .github/workflows/snyk-security.yml
name: Snyk Security

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  snyk-test:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
      
      - name: Run Snyk Open Source
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --all-projects
      
      - name: Run Snyk Code
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: code test
          args: --all-projects
      
      - name: Monitor project
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: monitor
          args: --all-projects
      
      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .
      
      - name: Run Snyk Container
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: myapp:${{ github.sha }}
          args: --severity-threshold=high
```

---

## 6.5 OWASP Dependency-Check

### 6.5.1 Configuração com Maven/Gradle

```xml
<!-- pom.xml - Configuração para Maven -->
<project>
    <build>
        <plugins>
            <plugin>
                <groupId>org.owasp</groupId>
                <artifactId>dependency-check-maven</artifactId>
                <version>9.0.7</version>
                <configuration>
                    <failBuildOnCVSS>7</failBuildOnCVSS>
                    <suppressionFiles>
                        <suppressionFile>dependency-check-suppressions.xml</suppressionFile>
                    </suppressionFiles>
                    <formats>
                        <format>HTML</format>
                        <format>JSON</format>
                        <format>SARIF</format>
                    </formats>
                </configuration>
                <executions>
                    <execution>
                        <goals>
                            <goal>check</goal>
                        </goals>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
```

```groovy
// build.gradle - Configuração para Gradle
plugins {
    id 'org.owasp.dependencycheck' version '9.0.7'
}

dependencyCheck {
    failBuildOnCVSS = 7
    suppressionFiles = ['dependency-check-suppressions.xml']
    formats = ['HTML', 'JSON', 'SARIF']
    analyzers {
        nodeEnabled = true
        pythonEnabled = true
    }
}

tasks.named("check").configure {
    dependsOn "dependencyCheckAnalyze"
}
```

### 6.5.2 Uso standalone

```bash
# Download do OWASP Dependency-Check
wget https://github.com/jeremylong/DependencyCheck/releases/download/v9.0.7/dependency-check-9.0.7-release.zip
unzip dependency-check-9.0.7-release.zip

# Escanear projeto
./dependency-check/bin/dependency-check.sh --project "Meu Projeto" --scan ./src

# Escanear com formato específico
./dependency-check/bin/dependency-check.sh \
  --project "Meu Projeto" \
  --scan ./src \
  --format HTML \
  --format JSON

# Escanear ignorando CVEs específicos
./dependency-check/bin/dependency-check.sh \
  --project "Meu Projeto" \
  --scan ./src \
  --suppression dependency-check-suppressions.xml

# Escanear com CVSS mínimo
./dependency-check/bin/dependency-check.sh \
  --project "Meu Projeto" \
  --scan ./src \
  --failOnCVSS 7
```

### 6.5.3 Gerenciamento do database CVE

```bash
# Atualizar database
./dependency-check/bin/dependency-check.sh --updateonly

# Download inicial do database
./dependency-check/bin/dependency-check.sh --downloadOnly

# Usar mirror local
./dependency-check/bin/dependency-check.sh \
  --project "Meu Projeto" \
  --scan ./src \
  --data /caminho/para/database

# Configurar proxy
export http_proxy=http://proxy.empresa.com:8080
export https_proxy=http://proxy.empresa.com:8080
./dependency-check/bin/dependency-check.sh --updateonly

# Verificar status do database
./dependency-check/bin/dependency-check.sh --checkVersion
```

### 6.5.4 Integração CI/CD

```yaml
# .github/workflows/dependency-check.yml
name: OWASP Dependency Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  dependency-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          java-version: '17'
          distribution: 'temurin'
      
      - name: Run OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'Meu Projeto'
          path: '.'
          format: 'HTML'
          format: 'JSON'
      
      - name: Upload Dependency Check Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dependency-check-report
          path: reports/
```

### 6.5.5 Arquivo de supressão

```xml
<!-- dependency-check-suppressions.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<suppressions xmlns="https://jeremylong.github.io/DependencyCheck/dependency-suppression.1.3.xsd">
    <!-- Supressão global para CVE específico -->
    <suppress>
        <notes>CVE não aplicável - vulnerabilidade em componente não utilizado</notes>
        <packageUrl regex="true">pkg:maven/com\.fasterxml\.jackson/core/jackson-databind@2\.13\..*</packageUrl>
        <cve>CVE-2020-36518</cve>
        <justification>Não utilizamos a funcionalidade afetada</justification>
        <vulnerabilityName>Jackson Databind DoS vulnerability</vulnerabilityName>
        <source>Manual review - 2024-01-15</source>
    </suppress>
    
    <!-- Supressão por SHA1 -->
    <suppress>
        <notes>Vulnerabilidade não aplicável ao nosso caso de uso</notes>
        <sha1>abc123def456789...</sha1>
        <cve>CVE-2021-44228</cve>
        <justification>Mitigado via configuração - desabilitado JNDI lookup</justification>
        <source>Segurança da informação - 2021-12-14</source>
    </suppress>
    
    <!-- Supressão por padrão de URL -->
    <suppress>
        <notes>Dependência de teste - não afeta produção</notes>
        <packageUrl regex="true">pkg:npm/mock.*@.*</packageUrl>
        <cve>CVE-.*</cve>
        <justification>Pacotes mock não são usados em produção</justification>
        <source>Equipe de segurança - 2024-02-01</source>
    </suppress>
</suppressions>
```

---

## 6.6 GitHub Dependabot

### 6.6.1 Configuração

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Dependências npm
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Sao_Paulo"
    open-pull-requests-limit: 10
    reviewers:
      - "usuario1"
      - "usuario2"
    assignees:
      - "usuario1"
    labels:
      - "dependencies"
      - "security"
    groups:
      production-dependencies:
        dependency-type: "production"
        update-types:
          - "major"
          - "minor"
      development-dependencies:
        dependency-type: "development"
        update-types:
          - "patch"
    ignore:
      - dependency-name: "lodash"
        update-types:
          - "version-update:semver-major"
    versioning-strategy: increase
  
  # Dependências pip (Python)
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels:
      - "dependencies"
      - "python"
  
  # Dependências Maven (Java)
  - package-ecosystem: "maven"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "tuesday"
    labels:
      - "dependencies"
      - "java"
  
  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "wednesday"
    labels:
      - "dependencies"
      - "ci"
  
  # Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "thursday"
    labels:
      - "dependencies"
      - "docker"
  
  # Terraform
  - package-ecosystem: "terraform"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "friday"
    labels:
      - "dependencies"
      - "infrastructure"
```

### 6.6.2 Security Alerts

```bash
# Configurar security alerts via GitHub CLI
gh api repos/{owner}/{repo}/vulnerability-alerts -X PUT

# Habilitar automerge para dependências seguras
gh api repos/{owner}/{repo}/automerge -X PUT

# Verificar alertas de segurança
gh api repos/{owner}/{repo}/dependabot/alerts

# Verificar PRs de segurança
gh api repos/{owner}/{repo}/dependabot/prs
```

### 6.6.3 PRs automatizados

O Dependabot cria PRs automaticamente quando:

1. Uma nova versão está disponível para uma dependência
2. Uma vulnerabilidade é descoberta em uma dependência atual
3. Uma atualização de licença é detectada

```yaml
# Configuração avançada de PRs
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
    groups:
      all-dependencies:
        patterns:
          - "*"
    open-pull-requests-limit: 50
    reviewers:
      - "equipe-seguranca"
    labels:
      - "automated"
      - "dependencies"
    commit-message:
      prefix: "deps"
      include: "scope"
```

### 6.6.4 Estratégias de atualização de versão

```yaml
# Estratégia para pacotes críticos
- package-ecosystem: "npm"
  directory: "/"
  schedule:
    interval: "daily"
  allow:
    - dependency-type: "production"
  update-types:
    - "version-update:semver-patch"
    - "version-update:semver-minor"
  ignore:
    - dependency-name: "*"
      update-types:
        - "version-update:semver-major"

# Estratégia para pacotes de desenvolvimento
- package-ecosystem: "npm"
  directory: "/"
  schedule:
    interval: "weekly"
  allow:
    - dependency-type: "development"
  update-types:
    - "version-update:semver-patch"

# Estratégia para pacotes de segurança (urgente)
- package-ecosystem: "npm"
  directory: "/"
  schedule:
    interval: "daily"
  allow:
    - dependency-type: "production"
  labels:
    - "security"
    - "urgent"
```

---

## 6.7 Gerenciamento de Vulnerabilidades

### 6.7.1 Processo de triagem

O processo de triagem de vulnerabilidades segue estas etapas:

1. **Identificação**: Ferramentas SCA detectam vulnerabilidades
2. **Classificação**: CVSS score e severidade
3. **Análise de impacto**: Afeta nosso caso de uso?
4. **Decisão**: Corrigir, mitigar ou aceitar risco
5. **Acompanhamento**: Verificar se a correção foi aplicada

```python
# Script de triagem automatizada
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class VulnerabilityTriage:
    def __init__(self, severity_threshold: str = "HIGH"):
        self.severity_threshold = severity_threshold
        self.severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    
    def run_trivy_scan(self, target: str) -> Dict:
        """Executa scan Trivy e retorna resultados."""
        cmd = [
            "trivy", "fs",
            "--format", "json",
            "--severity", f"{self.severity_threshold},CRITICAL",
            target
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Trivy scan failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def parse_vulnerabilities(self, scan_results: Dict) -> List[Dict]:
        """Extrai vulnerabilidades dos resultados."""
        vulnerabilities = []
        
        for result in scan_results.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                vulnerabilities.append({
                    "id": vuln.get("VulnerabilityID"),
                    "severity": vuln.get("Severity"),
                    "title": vuln.get("Title"),
                    "package": vuln.get("PkgName"),
                    "installed_version": vuln.get("InstalledVersion"),
                    "fixed_version": vuln.get("FixedVersion"),
                    "cvss_score": vuln.get("CVSS", {}).get("score", 0),
                    "references": vuln.get("References", [])
                })
        
        return vulnerabilities
    
    def triage_vulnerability(self, vuln: Dict) -> Tuple[str, str]:
        """Determina ação para uma vulnerabilidade."""
        severity = vuln["severity"]
        fixed_version = vuln.get("fixed_version")
        
        # Regras de triagem
        if severity == "CRITICAL":
            if fixed_version:
                return "FIX_NOW", "Correção urgente disponível"
            else:
                return "MITIGATE", "Sem correção - aplicar mitigação"
        
        elif severity == "HIGH":
            if fixed_version:
                return "FIX_SCHEDULED", "Agendar correção para próximo sprint"
            else:
                return "MONITOR", "Monitorar para disponibilidade de patch"
        
        elif severity == "MEDIUM":
            if fixed_version:
                return "BACKLOG", "Adicionar ao backlog"
            else:
                return "ACCEPT", "Aceitar risco - baixo impacto"
        
        else:  # LOW
            return "ACCEPT", "Aceitar risco - severidade baixa"
    
    def generate_triage_report(self, vulnerabilities: List[Dict]) -> Dict:
        """Gera relatório de triagem."""
        triage_results = {
            "timestamp": datetime.now().isoformat(),
            "total_vulnerabilities": len(vulnerabilities),
            "by_severity": {},
            "by_action": {},
            "vulnerabilities": []
        }
        
        for vuln in vulnerabilities:
            action, justification = self.triage_vulnerability(vuln)
            
            vuln_triage = {
                **vuln,
                "action": action,
                "justification": justification,
                "triaged_at": datetime.now().isoformat()
            }
            
            triage_results["vulnerabilities"].append(vuln_triage)
            
            # Estatísticas
            severity = vuln["severity"]
            triage_results["by_severity"][severity] = \
                triage_results["by_severity"].get(severity, 0) + 1
            
            triage_results["by_action"][action] = \
                triage_results["by_action"].get(action, 0) + 1
        
        return triage_results
    
    def save_report(self, report: Dict, output_file: str):
        """Salva relatório em JSON."""
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Relatório salvo em: {output_file}")

# Uso do script
if __name__ == "__main__":
    triage = VulnerabilityTriage(severity_threshold="HIGH")
    
    # Executar scan
    scan_results = triage.run_trivy_scan(".")
    
    # Parsear vulnerabilidades
    vulnerabilities = triage.parse_vulnerabilities(scan_results)
    
    # Gerar relatório de triagem
    report = triage.generate_triage_report(vulnerabilities)
    
    # Salvar relatório
    triage.save_report(report, "triage-report.json")
    
    # Resumo
    print(f"\nTotal de vulnerabilidades: {report['total_vulnerabilities']}")
    print(f"Por severidade: {report['by_severity']}")
    print(f"Por ação: {report['by_action']}")
```

### 6.7.2 Avaliação de risco para dependências

```python
# Modelo de avaliação de risco de dependências
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime, timedelta

class RiskLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class DependencyRisk:
    name: str
    version: str
    severity: str
    cvss_score: float
    has_fix: bool
    days_since_disclosure: int
    exploit_available: bool
    business_criticality: str
    
    def calculate_risk_score(self) -> float:
        """Calcula score de risco (0-100)."""
        # Base score from CVSS
        base_score = self.cvss_score * 10
        
        # Adjustments
        adjustments = 0
        
        # Severity multiplier
        severity_multiplier = {
            "LOW": 1.0,
            "MEDIUM": 1.5,
            "HIGH": 2.0,
            "CRITICAL": 3.0
        }
        base_score *= severity_multiplier.get(self.severity, 1.0)
        
        # No fix available increases risk
        if not self.has_fix:
            adjustments += 15
        
        # Exploit available increases risk significantly
        if self.exploit_available:
            adjustments += 25
        
        # Old vulnerabilities are less risky (already known)
        if self.days_since_disclosure > 180:
            adjustments -= 10
        
        # Business criticality multiplier
        criticality_multiplier = {
            "low": 0.8,
            "medium": 1.0,
            "high": 1.3,
            "critical": 1.5
        }
        base_score *= criticality_multiplier.get(self.business_criticality, 1.0)
        
        return min(100, max(0, base_score + adjustments))
    
    def get_risk_level(self) -> RiskLevel:
        """Retorna nível de risco baseado no score."""
        score = self.calculate_risk_score()
        
        if score >= 80:
            return RiskLevel.CRITICAL
        elif score >= 60:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

def assess_dependency_risks(vulnerabilities: List[Dict]) -> List[DependencyRisk]:
    """Avalia riscos de um lista de vulnerabilidades."""
    risks = []
    
    for vuln in vulnerabilities:
        risk = DependencyRisk(
            name=vuln["package"],
            version=vuln["installed_version"],
            severity=vuln["severity"],
            cvss_score=vuln.get("cvss_score", 0),
            has_fix=bool(vuln.get("fixed_version")),
            days_since_disclosure=vuln.get("days_since_disclosure", 0),
            exploit_available=vuln.get("exploit_available", False),
            business_criticality=vuln.get("business_criticality", "medium")
        )
        risks.append(risk)
    
    return sorted(risks, key=lambda x: x.calculate_risk_score(), reverse=True)
```

### 6.7.3 Quando corrigir vs contornar

| Cenário | Ação Recomendada | Prazo |
|---------|------------------|-------|
| CVE CRITICAL com fix disponível | Correção imediata | 24-48 horas |
| CVE HIGH com fix disponível | Agendar correção | Próximo sprint |
| CVE CRITICAL sem fix | Mitigar + monitorar | 1 semana |
| CVE HIGH sem fix | Mitigar + documentar | 2 semanas |
| CVE MEDIUM com fix | Backlog | Próximo ciclo |
| CVE LOW | Aceitar risco | Não priorizar |

### 6.7.4 Priorização de CVEs

```python
# Script de priorização de CVEs
from datetime import datetime, timedelta
from typing import List, Dict

class CVEPrioritizer:
    def __init__(self, current_date: datetime = None):
        self.current_date = current_date or datetime.now()
    
    def calculate_priority_score(self, cve: Dict) -> int:
        """
        Calcula score de priorização (0-100).
        Maior score = maior prioridade.
        """
        score = 0
        
        # Fator 1: Severidade CVSS (0-40 pontos)
        cvss = cve.get("cvss_score", 0)
        score += cvss * 4
        
        # Fator 2: Existência de exploit (0-25 pontos)
        if cve.get("exploit_available", False):
            score += 25
        
        # Fator 3: Disponibilidade de fix (0-20 pontos)
        if cve.get("has_fix", False):
            score += 20
        else:
            # Sem fix = menor prioridade imediata
            score -= 10
        
        # Fator 4: Idade da vulnerabilidade (0-15 pontos)
        disclosure_date = cve.get("disclosure_date")
        if disclosure_date:
            days_old = (self.current_date - disclosure_date).days
            if days_old <= 7:
                score += 15  # Muito novo - alta prioridade
            elif days_old <= 30:
                score += 10
            elif days_old <= 90:
                score += 5
            # Mais de 90 dias = sem bônus
        
        # Fator 5: Impacto no negócio (0-10 pontos)
        business_impact = cve.get("business_impact", "low")
        impact_scores = {
            "critical": 10,
            "high": 8,
            "medium": 5,
            "low": 2
        }
        score += impact_scores.get(business_impact, 2)
        
        return min(100, max(0, score))
    
    def prioritize_cves(self, cves: List[Dict]) -> List[Dict]:
        """Prioriza lista de CVEs por score."""
        prioritized = []
        
        for cve in cves:
            priority_score = self.calculate_priority_score(cve)
            prioritized.append({
                **cve,
                "priority_score": priority_score,
                "priority_level": self._get_priority_level(priority_score)
            })
        
        # Ordenar por score (maior primeiro)
        return sorted(prioritized, key=lambda x: x["priority_score"], reverse=True)
    
    def _get_priority_level(self, score: int) -> str:
        """Retorna nível de prioridade."""
        if score >= 80:
            return "P0 - IMEDIATO"
        elif score >= 60:
            return "P1 - URGENTE"
        elif score >= 40:
            return "P2 - ALTO"
        elif score >= 20:
            return "P3 - MÉDIO"
        else:
            return "P4 - BAIXO"
```

---

## 6.8 Políticas de Dependências

### 6.8.1 Estratégias de versionamento

```yaml
# Exemplo: .npmrc para npm
# Usar versão exata (recomendado para produção)
save-exact=true

# Prevenir instalação de dependências não listadas
package-lock=true

# Verificar integridade dos pacotes
ignore-scripts=false
```

```toml
# Exemplo: pyproject.toml para Python
[tool.poetry.dependencies]
python = "^3.11"
django = "4.2.7"  # Versão exata
requests = ">=2.31.0,<3.0.0"  # Range permitido

[tool.pip]
require-hashes = true
```

### 6.8.2 Licenças permitidas/bloqueadas

```yaml
# .github/dependency-review-config.yml
dependency-review-config:
  # Licenças permitidas
  allowed-licenses:
    - MIT
    - Apache-2.0
    - BSD-2-Clause
    - BSD-3-Clause
    - ISC
    - MPL-2.0
  
  # Licenças bloqueadas
  blocked-licenses:
    - GPL-2.0
    - GPL-3.0
    - AGPL-3.0
    - SSPL-1.0
  
  # Severidade mínima para bloquear
  min-severity: high
  
  # Bloquear vulnerabilidades conhecidas
  fail-on-severity: high
  
  # Ignorar dependências de desenvolvimento
  ignore-dev-dependencies: true
```

```python
# Script de verificação de licenças
import json
import subprocess
from typing import List, Dict, Tuple

class LicenseChecker:
    ALLOWED_LICENSES = {
        "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
        "ISC", "MPL-2.0", "Unlicense", "0BSD"
    }
    
    BLOCKED_LICENSES = {
        "GPL-2.0", "GPL-2.0-only", "GPL-2.0-or-later",
        "GPL-3.0", "GPL-3.0-only", "GPL-3.0-or-later",
        "AGPL-3.0", "AGPL-3.0-only", "AGPL-3.0-or-later",
        "SSPL-1.0", "EUPL-1.1"
    }
    
    def check_license(self, package: Dict) -> Tuple[bool, str]:
        """Verifica se a licença de um pacote é permitida."""
        license_id = package.get("license", "UNKNOWN")
        
        if license_id in self.BLOCKED_LICENSES:
            return False, f"Licença bloqueada: {license_id}"
        
        if license_id in self.ALLOWED_LICENSES:
            return True, f"Licença permitida: {license_id}"
        
        return False, f"Licença desconhecida: {license_id}"
    
    def scan_project(self, project_path: str) -> List[Dict]:
        """Escaneia projeto e retorna licenças."""
        cmd = [
            "syft", "scan", "dir:.",
            "-o", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)
        
        if result.returncode != 0:
            raise Exception(f"Syft scan failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def generate_report(self, packages: List[Dict]) -> Dict:
        """Gera relatório de licenças."""
        report = {
            "total_packages": len(packages),
            "allowed": [],
            "blocked": [],
            "unknown": [],
            "compliant": True
        }
        
        for pkg in packages:
            is_allowed, message = self.check_license(pkg)
            
            if is_allowed:
                report["allowed"].append({
                    "name": pkg.get("name"),
                    "version": pkg.get("version"),
                    "license": pkg.get("license")
                })
            elif "bloqueada" in message:
                report["blocked"].append({
                    "name": pkg.get("name"),
                    "version": pkg.get("version"),
                    "license": pkg.get("license"),
                    "message": message
                })
                report["compliant"] = False
            else:
                report["unknown"].append({
                    "name": pkg.get("name"),
                    "version": pkg.get("version"),
                    "license": pkg.get("license"),
                    "message": message
                })
        
        return report
```

### 6.8.3 Severidade máxima de vulnerabilidade

```yaml
# Configuração de threshold de severidade
# .trivy-policy.yaml
severity:
  - CRITICAL
  - HIGH

# Configuração para fail no CI
fail-on-severity: HIGH

# Configuração de tolerância zero
zero-tolerance:
  severity:
    - CRITICAL
  exploit-available: true
  age-days: 30  # CVEs com mais de 30 dias sem fix
```

### 6.8.4 Configuração completa de política de dependências

```yaml
# .github/dependency-policy.yml
version: 1
policy:
  # Configurações gerais
  general:
    fail-on-vulnerability: true
    minimum-severity: HIGH
    max-age-days: 90
  
  # Licenças
  licenses:
    allowed:
      - MIT
      - Apache-2.0
      - BSD-2-Clause
      - BSD-3-Clause
      - ISC
      - MPL-2.0
    blocked:
      - GPL-2.0
      - GPL-3.0
      - AGPL-3.0
      - SSPL-1.0
    require-approval:
      - LGPL-2.1
      - LGPL-3.0
  
  # Dependências
  dependencies:
    # Exigir hash em production
    require-hash: true
    
    # Versões mínimas
    minimum-versions:
      node: "18.0.0"
      python: "3.10.0"
      java: "17.0.0"
    
    # Pacotes bloqueados
    blocked-packages:
      - name: "left-pad"
        reason: "Pacote desnecessário"
      - name: "event-stream"
        reason: "Histórico de comprometimento"
  
  # Vulnerabilidades
  vulnerabilities:
    # Ações por severidade
    actions:
      CRITICAL: "block"
      HIGH: "block"
      MEDIUM: "warn"
      LOW: "ignore"
    
    # Revisão manual necessária
    manual-review:
      severity: "CRITICAL"
      exploit-available: true
    
    # Auto-fix
    auto-fix:
      enabled: true
      min-severity: "HIGH"
      max-version-bump: "minor"
  
  # Exceções
  exceptions:
    - package: "express"
      cve: "CVE-2024-12345"
      reason: "Mitigado via configuração"
      expires: "2024-06-30"
      approved-by: "equipe-seguranca"
```

---

## 6.9 Exemplo Completo: Pipeline SCA

### 6.9.1 Pipeline multi-ferramenta

```yaml
# .github/workflows/complete-sca-pipeline.yml
name: Complete SCA Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Toda segunda-feira às 6h

jobs:
  # Job 1: Geração de SBOM
  generate-sbom:
    runs-on: ubuntu-latest
    outputs:
      sbom-artifact: ${{ steps.generate.outputs.artifact-name }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Generate SBOM with Trivy
        id: generate
        run: |
          # Gerar SBOM SPDX
          trivy fs \
            --format spdx-json \
            --output sbom-spdx.json \
            .
          
          # Gerar SBOM CycloneDX
          trivy fs \
            --format cyclonedx \
            --output sbom-cdx.json \
            .
          
          echo "artifact-name=sbom-${{ github.sha }}" >> $GITHUB_OUTPUT
      
      - name: Validate SBOM
        run: |
          # Validar formato SPDX
          python -m pip install spdx-tools
          spdx-tools validate -f json sbom-spdx.json
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: ${{ steps.generate.outputs.artifact-name }}
          path: |
            sbom-spdx.json
            sbom-cdx.json
          retention-days: 90

  # Job 2: Vulnerability Scan com múltiplas ferramentas
  vulnerability-scan:
    runs-on: ubuntu-latest
    needs: generate-sbom
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'json'
          output: 'trivy-fs-results.json'
          severity: 'CRITICAL,HIGH'
      
      - name: Trivy dependency scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'json'
          output: 'trivy-dep-results.json'
          severity: 'CRITICAL,HIGH,MEDIUM'
      
      - name: OWASP Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'DevSecOps Pipeline'
          path: '.'
          format: 'JSON'
      
      - name: License check with Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          syft scan dir:. -o json > syft-results.json
      
      - name: Merge scan results
        run: |
          python << 'EOF'
          import json
          
          # Carregar resultados Trivy
          with open('trivy-fs-results.json') as f:
              trivy_results = json.load(f)
          
          # Carregar resultados OWASP
          try:
              with open('dependency-check-report.json') as f:
                  owasp_results = json.load(f)
          except FileNotFoundError:
              owasp_results = {"dependencies": []}
          
          # Carregar resultados Syft
          with open('syft-results.json') as f:
              syft_results = json.load(f)
          
          # Consolidar resultados
          consolidated = {
              "trivy": trivy_results,
              "owasp": owasp_results,
              "syft": syft_results
          }
          
          with open('consolidated-results.json', 'w') as f:
              json.dump(consolidated, f, indent=2)
          
          print("Resultados consolidados salvos")
          EOF
      
      - name: Upload scan results
        uses: actions/upload-artifact@v4
        with:
          name: vulnerability-scan-results
          path: |
            trivy-fs-results.json
            trivy-dep-results.json
            dependency-check-report.json
            syft-results.json
            consolidated-results.json
          retention-days: 90

  # Job 3: Build e scan de imagem
  container-scan:
    runs-on: ubuntu-latest
    needs: vulnerability-scan
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.sha }} .
          docker tag myapp:${{ github.sha }} myapp:latest
      
      - name: Trivy image scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'json'
          output: 'trivy-image-results.json'
          severity: 'CRITICAL,HIGH'
      
      - name: Snyk container scan
        uses: snyk/actions/docker@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          image: 'myapp:${{ github.sha }}'
          args: '--severity-threshold=high --json-file-output=snyk-container.json'
      
      - name: Docker Scout
        uses: docker/scout-action@v1
        with:
          command: cves
          image: myapp:${{ github.sha }}
          only-severities: critical,high
          output-file: scout-results.json
      
      - name: Generate SBOM for container
        run: |
          trivy image \
            --format cyclonedx \
            --output container-sbom.json \
            myapp:${{ github.sha }}
      
      - name: Upload container scan results
        uses: actions/upload-artifact@v4
        with:
          name: container-scan-results
          path: |
            trivy-image-results.json
            snyk-container.json
            scout-results.json
            container-sbom.json

  # Job 4: Análise e aprovação
  security-review:
    runs-on: ubuntu-latest
    needs: [generate-sbom, vulnerability-scan, container-scan]
    
    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/
      
      - name: Generate security report
        run: |
          python << 'EOF'
          import json
          import os
          from datetime import datetime
          
          # Carregar todos os resultados
          results = {
              "timestamp": datetime.now().isoformat(),
              "commit": "${{ github.sha }}",
              "scan_results": {}
          }
          
          # Processar cada tipo de scan
          for scan_type in ["trivy-fs", "trivy-dep", "trivy-image", "owasp", "snyk", "scout"]:
              result_file = f"artifacts/{scan_type}-results.json"
              if os.path.exists(result_file):
                  with open(result_file) as f:
                      results["scan_results"][scan_type] = json.load(f)
          
          # Salvar relatório consolidado
          with open('security-report.json', 'w') as f:
              json.dump(results, f, indent=2)
          
          # Gerar relatório Markdown
          with open('security-report.md', 'w') as f:
              f.write("# Relatório de Segurança - SCA\n\n")
              f.write(f"**Data:** {results['timestamp']}\n")
              f.write(f"**Commit:** {results['commit']}\n\n")
              f.write("## Resumo\n\n")
              f.write("| Ferramenta | Vulnerabilidades | Críticas | Altas |\n")
              f.write("|------------|------------------|----------|-------|\n")
              f.write("| Trivy FS | 12 | 2 | 10 |\n")
              f.write("| Trivy Image | 8 | 1 | 7 |\n")
              f.write("| OWASP | 5 | 0 | 5 |\n")
              f.write("| Snyk | 10 | 3 | 7 |\n")
              f.write("| Docker Scout | 6 | 1 | 5 |\n")
          
          print("Relatório gerado com sucesso")
          EOF
      
      - name: Upload security report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: |
            security-report.json
            security-report.md

  # Job 5: Auto-fix (apenas no develop)
  auto-fix:
    runs-on: ubuntu-latest
    needs: security-review
    if: github.ref == 'refs/heads/develop'
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Create fix branch
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git checkout -b fix/security-updates-${{ github.run_id }}
      
      - name: Apply automatic fixes
        run: |
          # Atualizar dependências com patches de segurança
          npm audit fix
          
          # Atualizar dependências menores
          npm update --save
      
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "fix: security dependency updates"
          title: "fix: Security dependency updates"
          body: |
            Automated security dependency updates
            
            ## Changes
            - Updated dependencies with security patches
            - Fixed ${{ needs.vulnerability-scan.outputs.critical-count }} critical vulnerabilities
            - Fixed ${{ needs.vulnerability-scan.outputs.high-count }} high vulnerabilities
            
            ## Generated by
            SCA Pipeline - Auto-fix job
          branch: fix/security-updates-${{ github.run_id }}
          labels: |
            security
            dependencies
            automated
```

### 6.9.2 Script de orquestração local

```bash
#!/bin/bash
# run-sca-pipeline.sh - Pipeline SCA completa para execução local

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Funções auxiliares
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar dependências
check_dependencies() {
    log_info "Verificando dependências..."
    
    local deps=("trivy" "syft" "docker" "jq")
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "$dep não encontrado. Por favor, instale-o primeiro."
            exit 1
        fi
    done
    
    log_info "Todas as dependências verificadas"
}

# Criar diretório de resultados
setup_results_dir() {
    local results_dir="sca-results-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$results_dir"
    echo "$results_dir"
}

# Gerar SBOM
generate_sbom() {
    local results_dir=$1
    
    log_info "Gerando SBOM..."
    
    # SBOM com Trivy (SPDX)
    trivy fs \
        --format spdx-json \
        --output "$results_dir/sbom-spdx.json" \
        .
    
    # SBOM com Trivy (CycloneDX)
    trivy fs \
        --format cyclonedx \
        --output "$results_dir/sbom-cdx.json" \
        .
    
    # SBOM com Syft
    syft scan dir:. -o json > "$results_dir/sbom-syft.json"
    
    log_info "SBOMs gerados em $results_dir"
}

# Scan de vulnerabilidades
scan_vulnerabilities() {
    local results_dir=$1
    
    log_info "Escaneando vulnerabilidades..."
    
    # Trivy filesystem scan
    trivy fs \
        --format json \
        --output "$results_dir/trivy-fs.json" \
        --severity HIGH,CRITICAL \
        .
    
    # Trivy ignorando fix available
    trivy fs \
        --format json \
        --output "$results_dir/trivy-unfixed.json" \
        --ignore-unfixed \
        .
    
    log_info "Scan de vulnerabilidades concluído"
}

# Scan de licenças
scan_licenses() {
    local results_dir=$1
    
    log_info "Verificando licenças..."
    
    # Usar Syft para análise de licenças
    syft scan dir:. -o json > "$results_dir/licenses.json"
    
    # Extrair e verificar licenças
    jq -r '.artifacts[] | "\(.name)@\(.version): \(.licenses[0].value // "UNKNOWN")"' \
        "$results_dir/licenses.json" > "$results_dir/licenses-list.txt"
    
    log_info "Análise de licenças concluída"
}

# Verificar políticas
check_policies() {
    local results_dir=$1
    
    log_info "Verificando políticas..."
    
    # Verificar se há vulnerabilidades CRITICAL
    local critical_count=$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL") | .VulnerabilityID' \
        "$results_dir/trivy-fs.json" | wc -l)
    
    if [ "$critical_count" -gt 0 ]; then
        log_error "Encontradas $critical_count vulnerabilidades CRÍTICAS"
        return 1
    fi
    
    # Verificar licenças bloqueadas
    local blocked_licenses=$(grep -E "GPL|AGPL|SSPL" "$results_dir/licenses-list.txt" | wc -l)
    
    if [ "$blocked_licenses" -gt 0 ]; then
        log_warn "Encontradas $blocked_licenses dependências com licenças potencialmente problemáticas"
    fi
    
    log_info "Verificação de políticas concluída"
}

# Gerar relatório
generate_report() {
    local results_dir=$1
    
    log_info "Gerando relatório..."
    
    cat > "$results_dir/REPORT.md" << EOF
# Relatório de Segurança - SCA

**Data:** $(date)
**Diretório:** $(pwd)
**Commit:** $(git rev-parse HEAD 2>/dev/null || echo "N/A")

## Resumo

### Vulnerabilidades

| Severidade | Quantidade |
|------------|------------|
| CRITICAL | $(jq -r '[.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL")] | length' "$results_dir/trivy-fs.json") |
| HIGH | $(jq -r '[.Results[]?.Vulnerabilities[]? | select(.Severity == "HIGH")] | length' "$results_dir/trivy-fs.json") |

### Licenças

$(head -20 "$results_dir/licenses-list.txt")

## Detalhes

### Top 10 Vulnerabilidades

\`\`\`
$(jq -r '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL" or .Severity == "HIGH") | "\(.VulnerabilityID) [\(.Severity)] - \(.PkgName)@\(.InstalledVersion)"' "$results_dir/trivy-fs.json" | head -10)
\`\`\`

## Recomendações

1. Atualizar vulnerabilidades CRITICAL imediatamente
2. Revisar vulnerabilidades HIGH no próximo sprint
3. Verificar licenças bloqueadas
EOF
    
    log_info "Relatório gerado em $results_dir/REPORT.md"
}

# Função principal
main() {
    log_info "Iniciando pipeline SCA completa..."
    
    # Verificar dependências
    check_dependencies
    
    # Criar diretório de resultados
    local results_dir
    results_dir=$(setup_results_dir)
    
    # Executar etapas
    generate_sbom "$results_dir"
    scan_vulnerabilities "$results_dir"
    scan_licenses "$results_dir"
    
    # Verificar políticas
    if ! check_policies "$results_dir"; then
        log_error "Pipeline falhou na verificação de políticas"
        exit 1
    fi
    
    # Gerar relatório
    generate_report "$results_dir"
    
    log_info "Pipeline SCA concluída com sucesso!"
    log_info "Resultados salvos em: $results_dir"
}

# Executar
main "$@"
```

---

## 6.10 Referências

### 6.10.1 Casos reais de segurança

1. **Log4Shell (CVE-2021-44228)**
   - Vulnerabilidade no Apache Log4j que permitia Remote Code Execution
   - CVSS: 10.0 (máximo)
   - Impacto: Milhões de aplicações Java afetadas mundialmente
   - Lição: Dependências de logging precisam de atenção especial

2. **event-stream (2018)**
   - Comprometimento do pacote npm para roubo de criptomoedas
   - Atacante assumiu manutenção do pacote
   - Malware era difícil de detectar
   - Lição: Transferência de manutenção de pacotes é risco

3. **ua-parser-js (2021)**
   - Pacote npm popular comprometido com malware
   - Afetou mais de 8 milhões de downloads semanais
   - Continha cryptominer e roubo de credenciais
   - Lição: Pacotes populares são alvos atraentes

4. **colors.js sabotage (2022)**
   - Mantenedor destruiu intencionalmente seu próprio pacote
   - Injetou loop infinito que imprimia caracteres unicode
   - Afetou milhares de projetos
   - Lição: Dependências de unmaintained packages são risco

5. **SolarWinds (2020)**
   - Comprometimento da cadeia de suprimentos
   - Backdoor inserido durante processo de build
   - Afetou milhares de organizações, incluindo agências governamentais
   - Lição: SBOMs são essenciais para rastreabilidade

6. **left-pad (2016)**
   - Autor removeu pacote do npm como protesto
   - Quebrou builds em toda a internet
   - Demonstou fragilidade das dependências
   - Lição: Mirror e cache de pacotes são importantes

### 6.10.2 Padrões e documentação

- [NTIA SBOM Guidelines](https://www.ntia.doc.gov/files/ntia/publications/ntia_sbom_minimum_elements_report.pdf)
- [OWASP Software Component Verification Standard](https://owasp.org/www-project-software-component-verification-standard/)
- [CycloneDX Specification](https://cyclonedx.org/specification/overview/)
- [SPDX Specification](https://spdx.org/spdx-specification/)
- [NIST Secure Software Development Framework](https://csrc.nist.gov/publications/detail/ssdf/rev-1/final)

### 6.10.3 Ferramentas mencionadas

- [Trivy](https://trivy.dev/) - Scanner de segurança completo
- [Syft](https://github.com/anchore/syft) - Geração de SBOM
- [Snyk](https://snyk.io/) - Plataforma de segurança de desenvolvimento
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/) - Scanner de dependências
- [GitHub Dependabot](https://github.com/features/dependabot) - Atualização automática de dependências
- [CycloneDX](https://cyclonedx.org/) - Formato de SBOM da OWASP
- [SPDX](https://spdx.org/) - Formato de SBOM da Linux Foundation

### 6.10.4 Livros e artigos

- "Software Supply Chain Security" - Dan Lorenc
- "DevSecOps: Design, Operationalize, and Scale" - Shrish Bykolla
- "The DevOps Handbook" - Gene Kim, Jez Humble, Patrick Debois, John Willis
- "Building Secure and Reliable Systems" - Google SRE Team
- "Secure by Design" - Dan Bergh Johnsson, Daniel Deogun, Dan Sawano

---

## Resumo do Capítulo

Neste capítulo, exploramos a Análise de Composição de Software (SCA) como prática essencial de DevSecOps. Aprendemos:

1. **O que é SCA** e por que dependências são vetores de ataque significativos
2. **SBOMs** são fundamentais para rastreabilidade e conformidade
3. **Trivy** é uma ferramenta completa para múltiplos alvos
4. **Snyk** oferece integração profunda com ecossistemas de desenvolvimento
5. **OWASP Dependency-Check** é uma opção robusta para projetos Java
6. **Dependabot** automatiza atualizações de segurança no GitHub
7. **Processos de triagem** são essenciais para gerenciar vulnerabilidades
8. **Políticas de dependências** definem regras claras para o time
9. **Pipelines completas** orquestram múltiplas ferramentas

A chave para um programa SCA eficaz é combinar automação com processos claros de triagem e remediação. Nenhuma ferramenta sozinha resolve o problema - é necessário um ecossistema integrado de ferramentas, políticas e pessoas.
---

*[Capítulo anterior: 05 — Dast Analise Dinamica](05-dast-analise-dinamica.md)*
*[Próximo capítulo: 07 — Seguranca De Containers](07-seguranca-de-containers.md)*
