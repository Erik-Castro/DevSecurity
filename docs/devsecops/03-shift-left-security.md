---
layout: default
title: "03-shift-left-security"
---

# Capítulo 3 — Shift-Left Security

> "O custo de corrigir um bug em producao e 100 vezes maior do que corrigi-lo na fase de design."

---

## Sumario

1. [O que e Shift-Left Security](#1-o-que-e-shift-left-security)
2. [IDE Integration para Seguranca](#2-ide-integration-para-seguranca)
3. [Code Review Automatizado](#3-code-review-automatizado)
4. [Threat Modeling no Pipeline](#4-threat-modeling-no-pipeline)
5. [Secret Scanning](#5-secret-scanning)
6. [License Compliance](#6-license-compliance)
7. [Exemplo Completo: Pipeline Shift-Left](#7-exemplo-completo-pipeline-shift-left)
8. [Metricas de Shift-Left](#8-metricas-de-shift-left)
9. [Referencias](#9-referencias)

---

## 1. O que e Shift-Left Security

### 1.1 Definicao e Filosofia

Shift-Left Security e a pratica de incorporar verificacoes e validacoes de seguranca o mais cedo possivel no ciclo de vida do desenvolvimento de software. Em vez de tratar seguranca como uma etapa final — executada por uma equipe dedicada antes do release — o shift-left distribui essa responsabilidade ao longo de todo o pipeline, comecando pelo proprio editor de codigo do desenvolvedor.

O termo "shift-left" vem do modelo tradicional de waterfall, onde as fases eram organizadas da esquerda para a direita em um diagrama de timeline. A fase de seguranca ficava posicionada a direita, ou seja, no final do ciclo. Mover essa fase para a esquerda significa antecipa-la, integrando-a desde o primeiro commit.

A filosofia por tras do shift-left se baseia em tres pilares fundamentais:

- **Prevencao sobre correcao**: e mais barato e eficaz prevenir vulnerabilidades do que-las corrigir apos o deploy.
- **Automacao sobre intervencao manual**: ferramentas automatizadas podem analisar milhares de linhas de codigo em segundos, algo impossivel para revisores humanos.
- **Responsabilidade compartilhada**: seguranca nao e problema apenas da equipe de seguranca; e responsabilidade de todos que escrevem codigo.

### 1.2 Custo de Encontrar Bugs no Inicio vs. no Final

O famoso "Cost of Change Curve" do Software Engineering Institute demonstra de forma clara a economia gerada por shift-left. Os dados abaixo sao baseados em estudos publicados pelo IBM Systems Sciences Institute e pelo NIST (National Institute of Standards and Technology):

| Fase de Descoberta | Custo Relativo de Correcao |
|---------------------|---------------------------|
| Requirements/Design | 1x |
| Coding (IDE) | 5x |
| Code Review / PR | 10x |
| Unit Testing | 15x |
| Integration Testing | 30x |
| System Testing | 60x |
| Staging / Pre-Producao | 100x |
| Producao (post-deploy) | 300x a 1000x |

Isso significa que uma vulnerabilidade de SQL Injection descoberta durante o code review custa cerca de 10 vezes menos para corrigir do que a mesma vulnerabilidade descoberta em staging, e ate 1000 vezes menos do que descoberta em producao.

O relatorio "The Economic Impacts of Inadequate Infrastructure for Software Testing" do NIST (2002, atualizado em 2010) estimou que o custo anual de software defeituoso nos EUA era de aproximadamente USD 3.12 bilhoes. Estudos posteriores da Cisco e da IBM indicaram que:
- 85% das vulnerabilidades encontradas em producao poderiam ter sido detectadas durante o desenvolvimento.
- Organizacoes que adotam shift-left reduzem o tempo medio de remediacao de vulnerabilidades criticas de 120 dias para menos de 15 dias.
- O ROI medio de ferramentas de seguranca integradas ao IDE e de 300% no primeiro ano.

### 1.3 O Espectro do Shift-Left

O shift-left nao e binario — ele opera em um espectro de maturidade. Cada organizacao pode escolher onde posicionar-se:

**Nivel 1 — Revisao Manual:**
- Code review com checklist de seguranca
- Sem ferramentas automatizadas
- Baixa cobertura, alto custo humano

**Nivel 2 — Ferramentas Basicas:**
- Linters com regras de seguranca (Bandit para Python, ESLint-plugin-security para JavaScript)
- Pre-commit hooks para deteccao de secrets
- SAST basico no IDE

**Nivel 3 — Pipeline Integrado:**
- SAST, DAST, SCA e secret scanning no CI/CD
- Block merges quando vulnerabilidades criticas sao encontradas
- Dashboards de seguranca

**Nivel 4 — Shift-Left Avancado:**
- Threat modeling automatizado
- Infraestrutura como codigo analisada estaticamente
- Policy-as-code (OPA, Sentinel)
- SBOM automatico em cada build

**Nivel 5 — Seguranca como Codigo:**
- Regras de seguranca versionadas e testadas como codigo
- Compliance automatizado e auditar
- Feedback em tempo real ao desenvolvedor
- Seguranca integrada ao APM e observabilidade

### 1.4 Caso Publico: Microsoft Secure Future Initiative

Em 2023, a Microsoft lancou a "Secure Future Initiative" (SFI) apos uma serie de incidentes de seguranca de alto perfil. A SFI representou um shift-left massivo em toda a organizacao:

- **Antes**: Equipes de seguranca analisavam codigo manualmente antes de releases trimestrais.
- **Depois**: Cada pull request passa por analise automatizada com CodeQL e Secret Scanner. A media de tempo para detectar uma vulnerabilidade caiu de 90 dias para 3 dias.
- **Resultado**: Reducao de 74% em vulnerabilidades criticas encontradas em producao no primeiro ano de implementacao.

---

## 2. IDE Integration para Seguranca

### 2.1 VS Code Security Extensions

O Visual Studio Code, por ser o editor mais utilizado por desenvolvedores, dispoe de um ecossistema robusto de extensoes de seguranca. As principais sao:

**Snyk Security:**
- Escaneamento em tempo real de dependencias
- Deteccao de vulnerabilidades em tempo de digitacao
- Correcoes automaticas sugeridas

Para instalar via CLI:

```bash
code --install-extension snyk-security.snyk-vulnerability-scanner
```

**SonarLint:**
- Deteccao de bugs, code smells e vulnerabilidades de seguranca
- Explicacoes detalhadas de cada problema encontrado
- Integracao com SonarQube para sincronizacao de regras

```bash
code --install-extension sonarsource.sonarlint-vscode
```

**GitLens + Security:**
- Historico de seguranca por arquivo
- Identificacao de autores de linhas problematicas
- Integracao com advisories

```json
{
  "sonarlint.rules": {
    "typescript:S5144": {
      "level": "error",
      "message": "Server-Side Request Forgery detected"
    },
    "python:S5135": {
      "level": "error",
      "message": "Deserialized object from untrusted source"
    }
  }
}
```

### 2.2 JetBrains IDE Security Plugins

Os IDEs da JetBrains (IntelliJ IDEA, PyCharm, WebStorm) possuem plugins nativos e de terceiros para seguranca:

**JetBrains Security:**
- Analise estatica de codigo embutida no IDE
- Deteccao de padroes inseguros em Java, Kotlin, Python, JavaScript
- Integracao com OWASP Dependency Check

**SonarLint (disponivel tambem para JetBrains):**
- Mesmo conjunto de regras do VS Code
- Suporte a 29 linguagens
- Modo Connected para sincronizar com SonarQube/SonarCloud

Para configurar regras de seguranca especificas no JetBrains:

```xml
<!-- .idea/sonarlint.xml (commitado ou via .gitignore) -->
<component name="SonarLintProjectSettings">
  <option name="connectedModeServers">
    <list>
      <option>
        <option name="serverId" value="sonarcloud" />
        <option name="organizationKey" value="minha-org" />
      </option>
    </list>
  </option>
</component>
```

### 2.3 Pre-commit Hooks Deep Dive

Pre-commit hooks sao o primeiro barreira de defesa antes do codigo chegar ao repositorio. Executam localmente na maquina do desenvolvedor e podem detectar problemas antes mesmo do commit ser criado.

**O framework pre-commit** e o padrao da industria para gerenciar hooks em repositorios. Ele permite definir hooks declarativamente em um arquivo YAML e distribui-los para toda a equipe.

Instalacao:

```bash
pip install pre-commit
# ou
brew install pre-commit  # macOS
```

**Vantagens do pre-commit sobre hooks nativos do git:**
- Hooks sao versionados no repositorio (mesmo setup para todos)
- Hooks rodam em isolamento (virtualenvs separados)
- Facil adicionar, remover e atualizar hooks
- Hooks sao executados em arquivos modificados (efficiente)

### 2.4 Arquivo Completo .pre-commit-config.yaml com Hooks de Seguranca

```yaml
# .pre-commit-config.yaml
# Configuracao completa de pre-commit hooks para seguranca

repos:
  # ============================================
  # HOOK: Deteccao de Secrets
  # ============================================
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: Gitleaks - Deteccao de Secrets
        description: "Verifica se secrets foram adicionados ao repositorio"
        args: ["--verbose"]

  # ============================================
  # HOOK: Deteccao de Secrets (alternativa - detect-secrets)
  # ============================================
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
        name: Detect-secrets
        description: "Baseline de secrets para evitar falsos positivos"

  # ============================================
  # HOOK: Bandit (Python Security Linter)
  # ============================================
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        name: Bandit - Security Linter para Python
        description: "Analise de seguranca em codigo Python"
        args: ["-c", "pyproject.toml"]
        additional_dependencies: ["bandit[toml]"]

  # ============================================
  # HOOK: Safety (Dependencias Python)
  # ============================================
  - repo: https://github.com/Lucas-C/pre-commit-hooks-safety
    rev: v1.3.1
    hooks:
      - id: python-safety-dependencies-check
        name: Safety - Verificacao de Dependencias
        description: "Verifica dependencias Python com vulnerabilidades conhecidas"
        args: ["--file=requirements.txt"]

  # ============================================
  # HOOK: Bandit para Arquivos de Infraestrutura
  # ============================================
  - repo: https://github.com/bridgecrewio/checkov
    rev: v3.1.0
    hooks:
      - id: checkov
        name: Checkov - IaC Security Scanner
        description: "Verifica seguranca de Infrastructure as Code"
        args: ["--directory", ".", "--framework", "terraform"]

  # ============================================
  # HOOK: Dockerfile Linting
  # ============================================
  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-dockerfile
        name: Hadolint - Dockerfile Linter
        description: "Linting e verificacao de seguranca de Dockerfiles"

  # ============================================
  # HOOK: YAML Lint
  # ============================================
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
        name: Check YAML
        description: "Validacao de sintaxe YAML"
        args: ["--allow-multiple-documents"]
      - id: check-json
        name: Check JSON
        description: "Validacao de sintaxe JSON"
      - id: check-toml
        name: Check TOML
        description: "Validacao de sintaxe TOML"

  # ============================================
  # HOOK: Verificacao de Arquivos Sensíveis
  # ============================================
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-merge-conflict
        name: Check Merge Conflict
        description: "Verifica conflitos de merge nao resolvidos"
      - id: detect-private-key
        name: Detect Private Key
        description: "Detecta chaves privadas no codigo"
      - id: no-commit-to-branch
        name: No Direct Commits to Main
        description: "Impede commits diretos na branch main"
        args: ["--branch", "main"]

  # ============================================
  # HOOK: Gitleaks para Historico
  # ============================================
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: Gitleaks - Scan Completo
        description: "Verifica commits anteriores para secrets"

  # ============================================
  # HOOK: Semgrep (Multi-linguagem)
  # ============================================
  - repo: https://github.com/semgrep/semgrep
    rev: v1.56.0
    hooks:
      - id: semgrep
        name: Semgrep - SAST Multi-linguagem
        description: "Analise de seguranca baseada em regras"
        args: ["--config=auto", "--error"]

  # ============================================
  # HOOK: ShellCheck
  # ============================================
  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.9.0
    hooks:
      - id: shellcheck
        name: ShellCheck
        description: "Analise estatica de scripts shell"

  # ============================================
  # HOOK: Secrets em Arquivos de Configuracao
  # ============================================
  - repo: local
    hooks:
      - id: check-env-files
        name: Check .env Files
        description: "Impede commit de arquivos .env"
        entry: bash -c 'git diff --cached --name-only | grep -E "\.env$" && echo "ERRO: Arquivos .env nao podem ser commitados" && exit 1 || exit 0'
        language: system
        always_run: true
        pass_filenames: false
```

### 2.5 EditorConfig para Seguranca

O `.editorconfig` pode ser utilizado para garantir que arquivos sensiveis nao sejam alterados acidentalmente e para manter consistencia:

```ini
# .editorconfig
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

# Forcar LF em scripts (evita problemas com CRLF em shells)
[*.sh]
end_of_line = lf

# Nao alterar arquivos de chave publica
[*.pub]
insert_final_newline = false
trim_trailing_whitespace = false

# Configuracao especifica para Dockerfiles
[Dockerfile*]
indent_style = space
indent_size = 4

# Configuracao para arquivos de seguranca
[.secrets.baseline]
insert_final_newline = false
```

---

## 3. Code Review Automatizado

### 3.1 GitHub PR Security Checks

O GitHub oferece um conjunto nativo de verificacoes de seguranca para Pull Requests. A configuracao e feita no arquivo `.github/repository.yaml`:

```yaml
# .github/repository.yaml
private_vulnerability_reporting: true
security_advisories:
  enabled: true
```

Alem disso, as GitHub Actions podem ser configuradas para bloquear merges quando vulnerabilidades sao encontradas:

```yaml
# .github/workflows/security-gate.yml
name: Security Gate

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  pull-requests: read
  checks: read

jobs:
  security-gate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run CodeQL
        uses: github/codeql-action/analyze@v3
        with:
          languages: python, javascript
          category: "/language:python"

      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/python
            p/jwt
            p/secrets
            p/owasp-top-ten

      - name: Verificar Dependencias
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0
```

### 3.2 CodeQL Setup e Queries Customizadas

CodeQL e a ferramenta de analise semantica de codigo do GitHub. Diferente de ferramentas baseadas em regex, CodeQL transforma o codigo em um banco de dados consultavel, permitindo queries complexas que entendem o fluxo de dados.

**Configuracao completa para GitHub Actions:**

{% raw %}
```yaml
# .github/workflows/codeql-analysis.yml
name: "CodeQL Analysis"

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * 1'  # Segunda-feira as 6h

jobs:
  analyze:
    name: Analyze (${{ matrix.language }})
    runs-on: ubuntu-latest
    timeout-minutes: 360

    permissions:
      security-events: write
      packages: read
      actions: read
      contents: read

    strategy:
      fail-fast: false
      matrix:
        include:
          - language: python
            build-mode: none
          - language: javascript-typescript
            build-mode: none

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          build-mode: ${{ matrix.build-mode }}
          config: |
            security-extended
            security-and-quality

      - name: Autobuild
        if: matrix.build-mode == 'autobuild'
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
          upload: true
          output: sarif-results
```
{% endraw %}

**Query customizada para detectar SSRF em Python:**

```ql
// .github/codeql/queries/ssrf-detection.ql
/**
 * @name Server-Side Request Forgery (SSRF) em Python
 * @description Detecta solicitacoes HTTP onde a URL e controlada pelo usuario
 *              sem validacao adequada.
 * @kind path-problem
 * @problem.severity error
 * @security-severity 8.6
 * @precision high
 * @id python/ssrf-attacker-controlled-url
 * @tags security
 *       external/cwe/cwe-918
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.security.dataflow.ServerSideRequestForgeryQuery

from ServerSideRequestForgery::Configuration config,
     DataFlow::Node source, DataFlow::Node sink
where
  config.hasFlow(source, sink)
select sink.getNode(), source, sink,
  "Essa URL de requisicao HTTP $@ e controlada por um atacante.",
  source.getNode(), "valor de entrada"
```

**Query customizada para deteccao de deserializacao insegura:**

```ql
// .github/codeql/queries/insecure-deserialization.ql
/**
 * @name Deserializacao Insegura em Python
 * @description Detecta uso de pickle, yaml.load sem SafeLoader, ou
 *              marshallow sem validacao de tipos.
 * @kind path-problem
 * @problem.severity error
 * @security-severity 9.8
 * @precision high
 * @id python/insecure-deserialization
 * @tags security
 *       external/cwe/cwe-502
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.dataflow.new.RemoteFlowSources

module InsecureDeserializationConfig implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node source) {
    source instanceof RemoteFlowSource
  }

  predicate isSink(DataFlow::Node sink) {
    exists(DataFlow::CallNode call |
      // pickle.loads
      call.getFunction().(DataFlow::AttrRead).getAttributeName() = "loads" and
      call.getFunction().(DataFlow::AttrRead).getObject().(DataFlow::AttrRead)
        .getAttributeName() = "pickle" and
      sink = call.getArg(0)
    )
    or
    // yaml.load sem Loader=SafeLoader
    exists(DataFlow::CallNode call |
      call.getFunction().(DataFlow::AttrRead).getAttributeName() = "load" and
      call.getFunction().(DataFlow::AttrRead).getObject().(DataFlow::AttrRead)
        .getAttributeName() = "yaml" and
      not exists(DataFlow::Node loader |
        call.getArgByName("Loader") = loader and
        loader.toString().matches("%SafeLoader%")
      ) and
      sink = call.getArg(0)
    )
  }
}

from InsecureDeserializationConfig config,
     DataFlow::Node source, DataFlow::Node sink
where config.hasFlow(source, sink)
select sink, source, sink,
  "Objeto de entrada serializado $@ e desserializado de forma insegura.",
  source.getNode(), "origem"
```

### 3.3 Semgrep Rules e Custom Policies

Semgrep e uma ferramenta de analise estatica open-source que usa patterns de codigo para detectar vulnerabilidades. Sua sintaxe e proxima da linguagem-alvo, tornando as regras faceis de escrever e entender.

**Configuracao completa para Python:**

```yaml
# .semgrep.yml

rules:
  # ============================================
  # REGRA 1: Deteccao de SQL Injection
  # ============================================
  - id: python.sql-injection
    patterns:
      - pattern-either:
          - pattern: |
              $CURSOR.execute("..." + $INPUT)
          - pattern: |
              $CURSOR.execute(f"...{$INPUT}...")
          - pattern: |
              $CURSOR.execute("...%s..." % $INPUT)
          - pattern: |
              $CURSOR.execute("...{}".format($INPUT))
          - pattern: |
              $QUERY = "..." + $INPUT
              ...
              $CURSOR.execute($QUERY)
    message: |
      SQL Injection detectada. A variavel $INPUT esta sendo
      concatenada diretamente em uma query SQL.
      Use queries parametrizadas: cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    languages: [python]
    severity: ERROR
    metadata:
      cwe:
        - "CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')"
      owasp:
        - A03:2021 Injection
      confidence: HIGH
      impact: HIGH
      references:
        - https://owasp.org/Top10/A03_2021-Injection/

  # ============================================
  # REGRA 2: Deteccao de Command Injection
  # ============================================
  - id: python.command-injection
    patterns:
      - pattern-either:
          - pattern: os.system($CMD)
          - pattern: os.popen($CMD)
          - pattern: subprocess.call($CMD, shell=True)
          - pattern: subprocess.Popen($CMD, shell=True)
          - pattern: subprocess.run($CMD, shell=True)
    message: |
      Command Injection potencial. O argumento shell=True com
      variaveis do usuario permite execucao de comandos arbitrarios.
      Use subprocess.run() com shell=False e lista de argumentos.
    languages: [python]
    severity: ERROR
    metadata:
      cwe:
        - "CWE-78: Improper Neutralization of Special Elements used in an OS Command"
      owasp:
        - A03:2021 Injection

  # ============================================
  # REGRA 3: Deteccao de Hardcoded Secrets
  # ============================================
  - id: python.hardcoded-secret
    patterns:
      - pattern-either:
          - pattern: $VAR = "sk_live_..."
          - pattern: $VAR = "AKIA..."
          - pattern: $VAR = "ghp_..."
          - pattern: $VAR = "xox[bpoa]-..."
    message: |
      Secret hardcoded detectado. Nunca armazene chaves de API,
      tokens ou credenciais diretamente no codigo.
      Use variaveis de ambiente ou um vault de seguranca.
    languages: [python]
    severity: ERROR
    metadata:
      cwe:
        - "CWE-798: Use of Hard-coded Credentials"
      owasp:
        - A07:2021 Identification and Authentication Failures

  # ============================================
  # REGRA 4: Deteccao de YAML Unsafe Load
  # ============================================
  - id: python.yaml-unsafe-load
    pattern: yaml.load($DATA)
    message: |
      yaml.load() sem Loader explicito e inseguro.
      Use yaml.load(data, Loader=yaml.SafeLoader) para
      evitar desserializacao arbitraria de objetos Python.
    languages: [python]
    severity: WARNING
    metadata:
      cwe:
        - "CWE-502: Deserialization of Untrusted Data"

  # ============================================
  # REGRA 5: Deteccao de Eval/Exec
  # ============================================
  - id: python.dangerous-eval
    pattern-either:
      - pattern: eval($INPUT)
      - pattern: exec($INPUT)
    message: |
      Uso de eval() ou exec() com entrada nao confiavel.
      Isso permite execucao arbitraria de codigo Python.
    languages: [python]
    severity: ERROR
    metadata:
      cwe:
        - "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code"

  # ============================================
  # REGRA 6: Deteccao de Insecure Random
  # ============================================
  - id: python.insecure-random
    pattern: random.random()
    message: |
      Use de random.random() para fins de seguranca.
      Para tokens, senhas ou nonces, use secrets.token_bytes()
      ou secrets.token_hex().
    languages: [python]
    severity: WARNING
    metadata:
      cwe:
        - "CWE-330: Use of Insufficiently Random Values"

  # ============================================
  # REGRA 7: Deteccao de Debug Mode
  # ============================================
  - id: python.debug-enabled
    patterns:
      - pattern-either:
          - pattern: app.run(debug=True)
          - pattern: Flask(__name__, debug=True)
    message: |
      Flask com debug=True em producao expoe o debugger
      interativo, permitindo execucao remota de codigo.
      Desative debug em producao.
    languages: [python]
    severity: WARNING
    metadata:
      cwe:
        - "CWE-215: Insertion of Sensitive Information Into Debugging Code"

# Configuracao global do Semgrep
settings:
  # Ignorar testes
  paths:
    exclude:
      - "**/test_*.py"
      - "**/tests/**"
      - "**/*_test.py"
      - "**/migrations/**"
      - "**/node_modules/**"

  # Limites de performance
  max_targets_per_rule: 1000
  timeout: 30
```

**Configuracao de .semgrepignore:**

```
# .semgrepignore
# Ignorar arquivos de teste
tests/
test_*
*_test.py
conftest.py

# Ignorar migracoes
**/migrations/

# Ignorar dependencias vendored
vendor/
third_party/

# Ignorar geradores de codigo
*.pb2.py
*_pb2_grpc.py
```

### 3.4 Executando Semgrep Localmente

```bash
# Instalacao
pip install semgrep

# Executar todas as regras do repositorio
semgrep scan --config .semgrep.yml

# Executar apenas regras especificas
semgrep scan --config .semgrep.yml --include-rule python.sql-injection

# Executar com contexto (mostra linhas ao redor)
semgrep scan --config .semgrep.yml --verbose

# Gerar relatorio em formato SARIF (para GitHub)
semgrep scan --config .semgrep.yml --sarif --output results.sarif

# Executar com regras publicas do Semgrep
semgrep scan --config p/python --config p/owasp-top-ten

# Modo CI (fail se encontrar erros)
semgrep scan --config .semgrep.yml --error --sarif
```

---

## 4. Threat Modeling no Pipeline

### 4.1 Threat Modeling Automatizado com ThreatPlaybook

O Threat Modeling tradicional e um processo manual, demorado e dependente de especialistas. O ThreatPlaybook automatiza parte desse processo, integrando-o ao pipeline CI/CD.

**Conceitos basicos:**

O ThreatPlaybook utiliza a metodologia STRIDE para classificar ameacas:

- **S**poofing (Falsificacao): O atacante se faz passar por outro usuario ou sistema.
- **T**ampering (Alteracao): O atacante modifica dados ou codigo sem autorizacao.
- **R**epudiation (Repudio): O atacante realiza uma acao e depois nega ter sido ele.
- **I**nformation Disclosure (Divulgacao de Informacoes): O atacante acessa informacoes privilegiadas.
- **D**enial of Service (Negação de Servico): O atacante torna o sistema indisponivel.
- **E**levation of Privilege (Elevacao de Privilegio): O atacante obtendo permissoes que nao deveria ter.

**Integracao com GitHub Actions:**

```yaml
# .github/workflows/threat-model.yml
name: Threat Model Analysis

on:
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'api/**'
      - 'infrastructure/**'

jobs:
  threat-model:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar ThreatPlaybook
        run: |
          pip install threat-playbook

      - name: Executar Threat Model
        run: |
          threat-playbook analyze \
            --source src/ \
            --output threat-report.json \
            --format json \
            --rules rules/

      - name: Avaliar Riscos
        run: |
          python3 -c "
          import json
          with open('threat-report.json') as f:
              threats = json.load(f)

          critical = [t for t in threats if t['severity'] == 'critical']
          high = [t for t in threats if t['severity'] == 'high']

          if critical:
              print(f'ERRO: {len(critical)} ameacas criticas encontradas')
              for t in critical:
                  print(f'  - [{t[\"type\"]}] {t[\"description\"]}')
              exit(1)

          if high:
              print(f'AVISO: {len(high)} ameacas de alta severidade')
              for t in high:
                  print(f'  - [{t[\"type\"]}] {t[\"description\"]}')

          print('Analise de ameacas concluida.')
          "

      - name: Upload Threat Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: threat-model-report
          path: threat-report.json
```

### 4.2 STRIDE no CI/CD

Para integrar STRIDE ao pipeline de forma mais granular, podemos criar um script Python que analisa mudancas no codigo e verifica padroes conhecidos:

```python
#!/usr/bin/env python3
"""
stride_checker.py - Verificacao automatica de STRIDE em mudancas de codigo.
Integrado ao CI/CD, analisa diffs para detectar padrões de ameaca.
"""

import subprocess
import sys
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
from enum import Enum


class ThreatType(Enum):
    SPOOFING = "Spoofing"
    TAMPERING = "Tampering"
    REPUDIATION = "Repudiation"
    INFO_DISCLOSURE = "Information Disclosure"
    DENIAL_OF_SERVICE = "Denial of Service"
    ELEVATION_OF_PRIVILEGE = "Elevation of Privilege"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Threat:
    type: ThreatType
    severity: Severity
    description: str
    file: str
    line: Optional[int]
    recommendation: str


STRIDE_PATTERNS = [
    {
        "type": ThreatType.SPOOFING,
        "severity": Severity.HIGH,
        "pattern": r"(?:jwt|token)\.decode\([^)]*verify\s*=\s*False",
        "description": "Verificacao de JWT desabilitada - permite falsificacao de identidade",
        "recommendation": "Sempre verifique tokens JWT com verify=True e use algoritmo adequado",
        "cwe": "CWE-294",
    },
    {
        "type": ThreatType.TAMPERING,
        "severity": Severity.HIGH,
        "pattern": r"exec\(|eval\(|compile\(.*,\s*['\"]exec['\"]",
        "description": "Execucao dinamica de codigo - permite alteracao arbitraria de comportamento",
        "recommendation": "Evite eval/exec; use parseadores seguros ou whitelists de funcoes",
        "cwe": "CWE-95",
    },
    {
        "type": ThreatType.INFO_DISCLOSURE,
        "severity": Severity.CRITICAL,
        "pattern": r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
        "description": "Credencial hardcoded detectada - risco de divulgacao de informacoes",
        "recommendation": "Use variaveis de ambiente ou vault de seguranca",
        "cwe": "CWE-798",
    },
    {
        "type": ThreatType.REPUDIATION,
        "severity": Severity.MEDIUM,
        "pattern": r"logging\.(debug|info)\(['\"].*(?:password|token|secret|key)",
        "description": "Credenciais sendo logadas - permite rastreamento ou exposicao em logs",
        "recommendation": "Nunca logue dados sensiveis; mascare valores antes de registrar",
        "cwe": "CWE-532",
    },
    {
        "type": ThreatType.DENIAL_OF_SERVICE,
        "severity": Severity.MEDIUM,
        "pattern": r"time\.sleep\(|while\s+True(?!\s*:\s*pass)|\.read\(\)\s*$",
        "description": "Possivel loop infinito ou operacao bloqueante - risco de DoS",
        "recommendation": "Adicione timeouts e limites de iteracao em loops e operacoes de I/O",
        "cwe": "CWE-400",
    },
    {
        "type": ThreatType.ELEVATION_OF_PRIVILEGE,
        "severity": Severity.HIGH,
        "pattern": r"chmod\s+777|chmod\s+\+x|sudo|os\.system\(.*rm\s+-rf",
        "description": "Operacao com privilegios elevados ou deletacao perigosa",
        "recommendation": "Use permissoes minimas necessarias; evite rm -rf em scripts",
        "cwe": "CWE-250",
    },
    {
        "type": ThreatType.INFO_DISCLOSURE,
        "severity": Severity.HIGH,
        "pattern": r"SELECT\s+\*\s+FROM|\.raw\(|\.extra\(.*where\s",
        "description": "Consulta SQL potencialmente insegura - risco de SQL Injection",
        "recommendation": "Use queries parametrizadas e ORM sempre que possivel",
        "cwe": "CWE-89",
    },
]


def get_changed_files() -> List[str]:
    """Obtem lista de arquivos alterados no commit atual."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD~1..HEAD"],
        capture_output=True,
        text=True,
    )
    return [
        f.strip()
        for f in result.stdout.strip().split("\n")
        if f.strip() and f.endswith(".py")
    ]


def scan_file(filepath: str) -> List[Threat]:
    """Escaneia um arquivo em busca de padroes STRIDE."""
    threats = []
    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except (IOError, UnicodeDecodeError):
        return threats

    for line_num, line in enumerate(lines, 1):
        for pattern_config in STRIDE_PATTERNS:
            if re.search(pattern_config["pattern"], line, re.IGNORECASE):
                threats.append(
                    Threat(
                        type=pattern_config["type"],
                        severity=pattern_config["severity"],
                        description=pattern_config["description"],
                        file=filepath,
                        line=line_num,
                        recommendation=pattern_config["recommendation"],
                    )
                )
    return threats


def main() -> int:
    """Funcao principal do STRIDE checker."""
    files = get_changed_files()

    if not files:
        print("Nenhum arquivo Python alterado.")
        return 0

    print(f"Analisando {len(files)} arquivos alterados...\n")

    all_threats: List[Threat] = []
    for filepath in files:
        threats = scan_file(filepath)
        all_threats.extend(threats)

    if not all_threats:
        print("Nenhuma ameaca STRIDE detectada nas alteracoes.")
        return 0

    critical = [t for t in all_threats if t.severity == Severity.CRITICAL]
    high = [t for t in all_threats if t.severity == Severity.HIGH]
    medium = [t for t in all_threats if t.severity == Severity.MEDIUM]
    low = [t for t in all_threats if t.severity == Severity.LOW]

    print(f"Resumo: {len(critical)} critica(s), {len(high)} alta(s), "
          f"{len(medium)} media(s), {len(low)} baixa(s)\n")

    for threat in all_threats:
        severity_icon = {
            Severity.CRITICAL: "CRITICO",
            Severity.HIGH: "ALTO",
            Severity.MEDIUM: "MEDIO",
            Severity.LOW: "BAIXO",
        }
        print(f"[{severity_icon[threat.severity]}] {threat.type.value}")
        print(f"  Arquivo: {threat.file}:{threat.line}")
        print(f"  Problema: {threat.description}")
        print(f"  Recomendacao: {threat.recommendation}")
        print()

    if critical:
        print("ERRO: Ameacas criticas bloqueiam o merge.")
        return 1

    if high:
        print("AVISO: Ameacas de alta severidade devem ser avaliadas.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 4.3 Integracao com Ferramentas de Planejamento

O threat modeling integrado ao pipeline pode ser conectado a ferramentas de planejamento para criar automaticamente tickets de seguranca:

```yaml
# .github/workflows/threat-to-jira.yml
name: Create Security Tickets

on:
  workflow_run:
    workflows: ["Threat Model Analysis"]
    types: [completed]

jobs:
  create-tickets:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Baixar Relatorio de Ameacas
        uses: actions/download-artifact@v4
        with:
          name: threat-model-report

      - name: Criar Tickets no Jira
        env:
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
        run: |
          python3 << 'EOF'
          import json
          import requests
          import os

          with open('threat-report.json') as f:
              threats = json.load(f)

          base_url = os.environ['JIRA_BASE_URL']
          token = os.environ['JIRA_API_TOKEN']

          for threat in threats:
              if threat['severity'] in ('critical', 'high'):
                  payload = {
                      "fields": {
                          "project": {"key": "SEC"},
                          "summary": f"[SEG] {threat['type']}: {threat['description'][:80]}",
                          "description": {
                              "type": "doc",
                              "version": 1,
                              "content": [{
                                  "type": "paragraph",
                                  "content": [{
                                      "text": f"Ameaca: {threat['description']}\n"
                                              f"Recomendacao: {threat['recommendation']}\n"
                                              f"Arquivo: {threat['file']}:{threat['line']}"
                                  }]
                              }]
                          },
                          "issuetype": {"name": "Bug"},
                          "priority": {
                              "name": "Critical" if threat['severity'] == 'critical' else "High"
                          },
                          "labels": ["security", "auto-detected", threat['type'].lower().replace(' ', '-')]
                      }
                  }

                  response = requests.post(
                      f"{base_url}/rest/api/3/issue",
                      json=payload,
                      headers={"Authorization": f"Bearer {token}"},
                  )
                  print(f"Ticket criado: {response.status_code} - {threat['type']}")
          EOF
```

---

## 5. Secret Scanning

### 5.1 GitLeaks Deep Dive

GitLeaks e a ferramenta mais popular para deteccao de secrets em repositorios Git. Ele suporta multiplos provedores e formatos de secret.

**Instalacao:**

```bash
# Via Go
go install github.com/gitleaks/gitleaks/v8@latest

# Via Homebrew
brew install gitleaks

# Via Docker
docker pull ghcr.io/gitleaks/gitleaks:latest
```

**Uso basico:**

```bash
# Escanear o repositorio inteiro
gitleaks detect

# Escanear especifico um commit
gitleaks protect --staged

# Escanear com verbosidade
gitleaks detect --verbose

# Output em formato JSON
gitleaks detect --report-format json --report-path gitleaks-report.json

# Output em formato SARIF (GitHub)
gitleaks detect --report-format sarif --report-path results.sarif

# Usar config customizada
gitleaks detect --config .gitleaks.toml

# Proteger contra commits com secrets (pre-commit)
gitleaks protect --staged --verbose
```

### 5.2 Configuracao Completa .gitleaks.toml

```toml
# .gitleaks.toml
# Configuracao completa do GitLeaks

title = "Regras de Secret Scanning do Projeto"

# Acao ao encontrar um secret: "none" (apenas reportar) ou "block" (bloquear)
# Em pre-commit, sempre use "block"
# Em CI, use "block" para branches protegidas

# ============================================
# REGRAS PADRAO (extendidas)
# ============================================

[[rules]]
id = "aws-access-key-id"
description = "AWS Access Key ID"
regex = '''(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'''
tags = ["key", "AWS"]

[[rules]]
id = "aws-secret-access-key"
description = "AWS Secret Access Key"
regex = '''(?i)aws(.{0,20})[\'\"][0-9a-zA-Z\/+]{40}'''
tags = ["key", "AWS"]

[[rules]]
id = "github-pat"
description = "GitHub Personal Access Token"
regex = '''ghp_[0-9a-zA-Z]{36}'''
tags = ["key", "GitHub"]

[[rules]]
id = "github-oauth"
description = "GitHub OAuth Access Token"
regex = '''gho_[0-9a-zA-Z]{36}'''
tags = ["key", "GitHub"]

[[rules]]
id = "github-app-token"
description = "GitHub App Token"
regex = '''(ghu|ghs)_[0-9a-zA-Z]{36}'''
tags = ["key", "GitHub"]

[[rules]]
id = "gitlab-pat"
description = "GitLab Personal Access Token"
regex = '''glpat-[0-9a-zA-Z\-_]{20,}'''
tags = ["key", "GitLab"]

[[rules]]
id = "slack-webhook"
description = "Slack Webhook URL"
regex = '''https://hooks\.slack\.com/services/T[a-zA-Z0-9]{8}/B[a-zA-Z0-9]{8}/[a-zA-Z0-9]{24}'''
tags = ["key", "Slack"]

[[rules]]
id = "slack-token"
description = "Slack Token"
regex = '''xox[baprs]-[0-9a-zA-Z\-]{10,}'''
tags = ["key", "Slack"]

[[rules]]
id = "stripe-secret-key"
description = "Stripe Secret Key"
regex = '''sk_live_[0-9a-zA-Z]{24,}'''
tags = ["key", "Stripe"]

[[rules]]
id = "stripe-publishable-key"
description = "Stripe Publishable Key"
regex = '''pk_live_[0-9a-zA-Z]{24,}'''
tags = ["key", "Stripe"]

[[rules]]
id = "google-api-key"
description = "Google API Key"
regex = '''AIza[0-9A-Za-z\-_]{35}'''
tags = ["key", "Google"]

[[rules]]
id = "google-oauth-id"
description = "Google OAuth ID"
regex = '''[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com'''
tags = ["key", "Google"]

[[rules]]
id = "heroku-api-key"
description = "Heroku API Key"
regex = '''(?i)heroku(.{0,20})[\'\"][0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'''
tags = ["key", "Heroku"]

[[rules]]
id = "private-key"
description = "Generic Private Key"
regex = '''-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'''
tags = ["key", "Private"]

[[rules]]
id = "jwt-token"
description = "JSON Web Token"
regex = '''eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.+/=]{10,}'''
tags = ["key", "JWT"]

[[rules]]
id = "npm-token"
description = "NPM Access Token"
regex = '''npm_[A-Za-z0-9]{36}'''
tags = ["key", "NPM"]

[[rules]]
id = "pypi-token"
description = "PyPI API Token"
regex = '''pypi-[A-Za-z0-9\-_]{50,}'''
tags = ["key", "PyPI"]

[[rules]]
id = "sendgrid-api-key"
description = "SendGrid API Key"
regex = '''SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}'''
tags = ["key", "SendGrid"]

[[rules]]
id = "twilio-api-key"
description = "Twilio API Key"
regex = '''SK[0-9a-fA-F]{32}'''
tags = ["key", "Twilio"]

# ============================================
# REGRAS CUSTOMIZADAS PARA O PROJETO
# ============================================

[[rules]]
id = "django-secret-key"
description = "Django Secret Key"
regex = '''SECRET_KEY\s*=\s*[\'\"](.{30,})[\'\"]'''
tags = ["key", "Django", "Python"]

[[rules]]
id = "database-url"
description = "Database Connection URL"
regex = '''(?i)(?:mysql|postgres|postgresql|mongodb|redis):\/\/[^\s\'\"]+'''
tags = ["key", "Database"]

[[rules]]
id = "internal-api-url"
description = "Internal API URL"
regex = '''https?:\/\/(?:10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.|192\.168\.)(?:[0-9]{1,3}\.){2}[0-9]{1,3}(?::\d+)?'''
tags = ["url", "Internal"]

# ============================================
# EXCECOES (allowlist)
# ============================================

[[rules.allowlists]]
description = "Exemplo de token em documentacao"
regexes = [
    '''example[_-]secret''',
    '''your[_-]api[_-]key[_-]here''',
    '''placeholder''',
    '''xxx''',
    '''changeme''',
]

# Ignorar arquivos de teste e documentacao
[[rules.allowlists]]
description = "Arquivos de teste e documentacao"
paths = [
    '''tests/.*\.py$''',
    '''docs/.*\.md$''',
    '''README\.md$''',
    '''CHANGELOG\.md$''',
    '''test_.*\.py$''',
    '''*_test\.py$''',
]

# Ignorar o proprio arquivo de config
[[rules.allowlists]]
description = "Proprio arquivo de configuracao"
paths = [
    '''.gitleaks\.toml$''',
]

# Ignorar fixtures e mocks
[[rules.allowlists]]
description = "Fixtures e mocks"
paths = [
    '''fixtures/.*''',
    '''mocks/.*''',
    '''__pycache__/.*''',
    '''\.pyc$''',
]
```

### 5.3 TruffleHog Usage

TruffleHog e uma alternativa ao GitLeaks com foco em deteccao mais profunda. Ele verifica nonces, validade de tokens e suporta mais de 600 formatos de secret.

**Instalacao:**

```bash
# Via Go
go install github.com/trufflesecurity/trufflehog/v3@latest

# Via Docker
docker pull trufflesecurity/trufflehog:latest
```

**Uso:**

```bash
# Escanear repositorio GitHub
trufflehog github --repo https://github.com/org/repo

# Escanear repositorio local
trufflehog filesystem /caminho/para/codigo

# Escanear com verificacao de veracidade
trufflehog github --repo https://github.com/org/repo --only-verified

# Output JSON
trufflehog github --repo https://github.com/org/repo --json > trufflehog-results.json

# Escanear org inteira
trufflehog github --org https://github.com/minha-org
```

**Diferencas entre GitLeaks e TruffleHog:**

| Caracteristica | GitLeaks | TruffleHog |
|----------------|----------|------------|
| Velocidade | Mais rapido | Mais lento (verificacao profunda) |
| Verificacao de veracidade | Nao | Sim (verifica se tokens sao validos) |
| Formatos suportados | ~100 | ~600+ |
| Historico Git | Sim | Sim |
| Escaneamento de imagem Docker | Nao | Sim |
| Escaneamento S3/GCS | Nao | Sim |

### 5.4 GitHub Secret Scanning

O GitHub Secret Scanning e um recurso nativo do GitHub Advanced Security. Ele verifica automaticamente os repositorios por secrets conhecidos de parceiros (AWS, Azure, Google, etc.).

**Ativando Secret Scanning:**

```bash
# Via GitHub CLI
gh api repos/{owner}/{repo}/secret-scanning --method PUT

# Configurar push protection
gh api repos/{owner}/{repo}/secret-scanning/push-protection --method PUT
```

**Configuracao de push protection:**

```yaml
# .github/repository.yml (para repositorios GitHub)
secret_scanning:
  enabled: true
secret_scanning_push_protection:
  enabled: true
```

### 5.5 Pipeline Completa de Secret Scanning

```yaml
# .github/workflows/secret-scanning.yml
name: Secret Scanning Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 8 * * 1-5'  # Segunda a Sexta as 8h

jobs:
  # ============================================
  # Job 1: Pre-commit Secrets Check
  # ============================================
  pre-commit-secrets:
    name: Pre-commit Secrets Check
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar pre-commit
        run: pip install pre-commit

      - name: Executar pre-commit hooks de seguranca
        run: |
          pre-commit run gitleaks --all-files
          pre-commit run detect-secrets --all-files
          pre-commit run detect-private-key --all-files

  # ============================================
  # Job 2: GitLeaks Scan Completo
  # ============================================
  gitleaks-full:
    name: GitLeaks Full Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Instalar GitLeaks
        run: |
          wget -qO- https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz | tar xz
          sudo mv gitleaks /usr/local/bin/

      - name: Executar GitLeaks
        run: |
          gitleaks detect \
            --config .gitleaks.toml \
            --report-format json \
            --report-path gitleaks-report.json \
            --verbose

      - name: Upload GitLeaks Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: gitleaks-report
          path: gitleaks-report.json

      - name: Publicar resultado no GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: gitleaks-report.sarif
          category: gitleaks

  # ============================================
  # Job 3: TruffleHog Scan
  # ============================================
  trufflehog-scan:
    name: TruffleHog Deep Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Executar TruffleHog
        run: |
          docker run --rm \
            -v "$(pwd):/repo" \
            trufflesecurity/trufflehog:latest \
            filesystem /repo \
            --json > trufflehog-results.json

      - name: Verificar Resultados
        run: |
          SECRETS_FOUND=$(cat trufflehog-results.json | wc -l)
          if [ "$SECRETS_FOUND" -gt 0 ]; then
            echo "ERRO: $SECRETS_FOUND secrets encontrados pelo TruffleHog"
            cat trufflehog-results.json | python3 -c "
          import sys, json
          for line in sys.stdin:
              try:
                  result = json.loads(line)
                  detector = result.get('DetectorName', 'Unknown')
                  verified = result.get('Verified', False)
                  source = result.get('SourceMetadata', {}).get('Data', {}).get('Filesystem', {}).get('file', 'N/A')
                  print(f'  [{detector}] Verificado: {verified} - {source}')
              except json.JSONDecodeError:
                  pass
          "
            exit 1
          else
            echo "Nenhum secret encontrado pelo TruffleHog."
          fi

      - name: Upload TruffleHog Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: trufflehog-report
          path: trufflehog-results.json

  # ============================================
  # Job 4: GitHub Secret Scanning
  # ============================================
  github-secret-scanning:
    name: GitHub Secret Scanning
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - name: Verificar Secret Scanning Status
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          STATUS=$(gh api repos/${{ github.repository }}/secret-scanning \
            --jq '.enabled' 2>/dev/null || echo "not_available")
          echo "Secret Scanning enabled: $STATUS"

          if [ "$STATUS" != "true" ]; then
            echo "AVISO: Secret Scanning nao esta habilitado para este repositorio"
            echo "Ative via: Settings > Security > Secret scanning"
          fi

  # ============================================
  # Job 5: Verificacao de Secrets em Historico
  # ============================================
  historical-scan:
    name: Historical Scan (Semana)
    runs-on: ubuntu-latest
    if: github.event.schedule
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Scan Historico Completo
        run: |
          echo "Executando scan historico agendado..."
          gitleaks detect \
            --config .gitleaks.toml \
            --report-format sarif \
            --report-path historical-scan.sarif \
            --verbose

      - name: Upload Historical Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: historical-scan-report
          path: historical-scan.sarif
```

### 5.6 Detectando Secrets em Historico

Detectar secrets que ja foram commitados e mais complexo do que detectar secrets em commits novos. A abordagem envolve escanear o historico completo do Git:

```bash
#!/usr/bin/env bash
# scan-history.sh - Escaneamento de historico Git para secrets

set -euo pipefail

REPO_PATH="${1:-.}"
REPORT_DIR="secret-scan-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/history-scan-${TIMESTAMP}"

mkdir -p "$REPORT_DIR"

echo "=== Escaneamento de Historico Git ==="
echo "Repositorio: $(cd "$REPO_PATH" && git rev-parse --show-toplevel)"
echo "Branch atual: $(cd "$REPO_PATH" && git branch --show-current)"
echo "Total de commits: $(cd "$REPO_PATH" && git rev-list --count HEAD)"
echo ""

# Contar commits por autor
echo "--- Top 10 Autores por Numero de Commits ---"
cd "$REPO_PATH" && git shortlog -sn --all | head -10
echo ""

# Escanear com GitLeaks
echo "--- Executando GitLeaks no Historico Completo ---"
gitleaks detect \
  --config .gitleaks.toml \
  --report-format json \
  --report-path "${REPORT_FILE}-gitleaks.json" \
  --log-level info \
  "$REPO_PATH" || true

GITLEAKS_COUNT=$(python3 -c "
import json
try:
    with open('${REPORT_FILE}-gitleaks.json') as f:
        data = json.load(f)
        print(len(data))
except:
    print(0)
" 2>/dev/null || echo "0")

echo "GitLeaks encontrou: $GITLEAKS_COUNT secrets"

# Escanear com TruffleHog (mais profundo)
echo ""
echo "--- Executando TruffleHog no Historico Completo ---"
trufflehog git "file://${REPO_PATH}" \
  --json \
  > "${REPORT_FILE}-trufflehog.json" 2>/dev/null || true

TRUFFLEHOG_COUNT=$(wc -l < "${REPORT_FILE}-trufflehog.json" 2>/dev/null || echo "0")
echo "TruffleHog encontrou: $TRUFFLEHOG_COUNT possiveis secrets"

# Gerar relatorio consolidado
echo ""
echo "--- Gerando Relatorio Consolidado ---"
python3 << PYEOF
import json
import os
from datetime import datetime

report_file = "${REPORT_FILE}-consolidated.md"

gitleaks_file = "${REPORT_FILE}-gitleaks.json"
trufflehog_file = "${REPORT_FILE}-trufflehog.json"

with open(report_file, "w") as f:
    f.write("# Relatorio de Secret Scanning - Historico\\n\\n")
    f.write(f"**Data:** {datetime.now().isoformat()}\\n")
    f.write(f"**Repositorio:** {os.getcwd()}\\n\\n")

    f.write("## Resumo\\n\\n")
    f.write(f"- GitLeaks: {${GITLEAKS_COUNT}} secrets encontrados\\n")
    f.write(f"- TruffleHog: {${TRUFFLEHOG_COUNT}} possiveis secrets\\n\\n")

    if int("${GITLEAKS_COUNT}") > 0:
        f.write("## Detalhes GitLeaks\\n\\n")
        try:
            with open(gitleaks_file) as gf:
                leaks = json.load(gf)
                for leak in leaks:
                    f.write(f"### {leak.get('RuleID', 'Unknown Rule')}\\n\\n")
                    f.write(f"- **Arquivo:** {leak.get('File', 'N/A')}\\n")
                    f.write(f"- **Linha:** {leak.get('StartLine', 'N/A')}\\n")
                    f.write(f"- **Commit:** {leak.get('Commit', 'N/A')}\\n")
                    f.write(f"- **Autor:** {leak.get('Author', 'N/A')}\\n")
                    f.write(f"- **Data:** {leak.get('Date', 'N/A')}\\n\\n")
        except Exception as e:
            f.write(f"Erro ao ler relatorio GitLeaks: {e}\\n")

print(f"Relatorio gerado: {report_file}")
PYEOF

echo ""
echo "=== Escaneamento Concluido ==="
echo "Relatorios salvos em: ${REPORT_DIR}/"
```

---

## 6. License Compliance

### 6.1 SPDX e CycloneDX

SPDX (Software Package Data Exchange) e CycloneDX sao os dois principais formatos de SBOM (Software Bill of Materials). Ambos sao padroes da industria e suportados por ferramentas de compliance.

**SPDX** e mantido pela Linux Foundation e foca em:
- Identificacao precisa de pacotes
- Metadados de licenciamento
- Relacoes entre pacotes (dependencias)

**CycloneDX** e mantido pela OWASP e foca em:
- Vunerabilidades associadas a pacotes
- Composicao de software (SBOM completo)
- Integracao com ferramentas de seguranca

### 6.2 Gerando SBOMs

```bash
# Gerar SBOM em formato SPDX com Syft
syft scan dir:. -o spdx-json > sbom-spdx.json

# Gerar SBOM em formato CycloneDX com Syft
syft scan dir:. -o cyclonedx-json > sbom-cyclonedx.json

# Gerar SBOM com CDXGen (foco em CycloneDX)
cdxgen -o sbom-cdxgen.json -t python

# Gerar SBOM de imagem Docker
syft scan docker:myapp:latest -o spdx-json > sbom-docker.json
```

### 6.3 FOSSA Integration

FOSSA e uma plataforma de compliance de licencas que integra ao pipeline CI/CD:

```yaml
# .github/workflows/license-compliance.yml
name: License Compliance

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  license-check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Instalar Ferramentas
        run: |
          pip install pip-licenses safety

      - name: Gerar Lista de Licencas
        run: |
          pip-licenses --format=json --output-file=licenses.json
          pip-licenses --format=markdown --with-urls > licenses.md

      - name: Verificar Licencas Proibidas
        run: |
          python3 << 'EOF'
          import json

          PROHIBITED = [
              "GPL-3.0",
              "AGPL-3.0",
              "SSPL-1.0",
              "EUPL-1.1",
              "CC-BY-NC-4.0",
          ]

          RESTRICTIVE = [
              "GPL-2.0",
              "LGPL-2.1",
              "MPL-2.0",
          ]

          with open("licenses.json") as f:
              licenses = json.load(f)

          violations = []
          warnings = []

          for pkg in licenses:
              lic = pkg.get("License", "Unknown")
              name = pkg.get("Name", "Unknown")

              for prohibited in PROHIBITED:
                  if prohibited.lower() in lic.lower():
                      violations.append(f"  {name}: {lic}")

              for restrictive in RESTRICTIVE:
                  if restrictive.lower() in lic.lower():
                      warnings.append(f"  {name}: {lic}")

          if violations:
              print("ERRO: Licencas proibidas encontradas:")
              for v in violations:
                  print(v)
              exit(1)

          if warnings:
              print("AVISO: Licencas restritivas encontradas:")
              for w in warnings:
                  print(w)

          print("Verificacao de licencas concluida.")
          EOF

      - name: Verificar Vulnerabilidades em Dependencias
        run: |
          safety check --json > safety-report.json || true
          python3 -c "
          import json
          with open('safety-report.json') as f:
              report = json.load(f)
          if report:
              print(f'Encontradas {len(report)} dependencias vulneraveis')
              for item in report:
                  print(f'  {item[\"package\"]}: {item[\"vulnerability\"]}')
          else:
              print('Nenhuma vulnerabilidade encontrada.')
          "

      - name: Upload License Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: license-report
          path: |
            licenses.json
            licenses.md
            safety-report.json
```

### 6.4 Configuracao de Politica de Licencas

```yaml
# .fossa.yml
# Configuracao FOSSA para compliance de licencas

version: 3

project:
  id: meu-projeto
  name: Meu Projeto
  team: minha-equipe
  branch: main

analyze:
  modules:
    - name: backend
      type: pip
      path: .
      target: requirements.txt
    - name: frontend
      type: npm
      path: frontend/
      target: package.json
    - name: infrastructure
      type: generic
      path: infrastructure/
      target: "*.tf"

policy:
  # Licencas permitidas
  allowed:
    - MIT
    - BSD-2-Clause
    - BSD-3-Clause
    - Apache-2.0
    - ISC
    - 0BSD
    - Unlicense

  # Licencas que precisam aprovacao manual
  restricted:
    - LGPL-2.1
    - LGPL-3.0
    - MPL-2.0
    - EPL-1.0
    - EPL-2.0

  # Licencas proibidas
  denied:
    - GPL-2.0
    - GPL-3.0
    - AGPL-3.0
    - SSPL-1.0
    - EUPL-1.1

  # Ignorar dependencias de teste
  ignore:
    - "*-dev"
    - "*-test"
    - pytest
    - coverage
    - mypy
```

---

## 7. Exemplo Completo: Pipeline Shift-Left

### 7.1 GitHub Actions Workflow Completo

{% raw %}
```yaml
# .github/workflows/shift-left-pipeline.yml
name: Shift-Left Security Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

permissions:
  contents: read
  security-events: write
  pull-requests: read
  checks: read
  actions: read
  packages: read
  id-token: write

env:
  PYTHON_VERSION: "3.12"

jobs:
  # ============================================
  # FASE 1: Pre-commit & Secrets (Instantaneo)
  # ============================================
  fase-1-secrets:
    name: "Fase 1: Secret Scanning"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Instalar pre-commit
        run: pip install pre-commit

      - name: Executar Secret Scanning
        run: |
          pre-commit run gitleaks --all-files
          pre-commit run detect-private-key --all-files
          pre-commit run check-env-files --all-files

      - name: GitLeaks Scan Detalhado
        run: |
          wget -qO- https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz | tar xz
          sudo mv gitleaks /usr/local/bin/
          gitleaks detect --config .gitleaks.toml --report-format json --report-path secret-scan.json || true

      - name: Upload Secret Scan Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: secret-scan-report
          path: secret-scan.json

  # ============================================
  # FASE 2: Analise Estatica (30-60s)
  # ============================================
  fase-2-sast:
    name: "Fase 2: SAST - Analise Estatica"
    runs-on: ubuntu-latest
    needs: fase-1-secrets
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Instalar Dependencias
        run: |
          pip install bandit semgrep safety pip-licenses

      - name: Bandit - Security Linter
        run: |
          bandit -r src/ -f json -o bandit-report.json \
            -ll --severity-level medium || true
          bandit -r src/ -f screen -ll

      - name: Semgrep - SAST Multi-linguagem
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            .semgrep.yml
            p/python
            p/owasp-top-ten
            p/secrets
        env:
          SEMGREP_SEND_METRICS: off

      - name: Upload SAST Reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sast-reports
          path: |
            bandit-report.json

  # ============================================
  # FASE 3: CodeQL (2-5min)
  # ============================================
  fase-3-codeql:
    name: "Fase 3: CodeQL - Analise Semantica"
    runs-on: ubuntu-latest
    needs: fase-1-secrets
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: python
          config: security-extended

      - name: Autobuild
        uses: github/codeql-action/autobuild@v3

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:python"

  # ============================================
  # FASE 4: Dependencias (30s)
  # ============================================
  fase-4-dependencias:
    name: "Fase 4: SCA - Analise de Dependencias"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Instalar Dependencias
        run: |
          pip install pip-audit pip-licenses safety

      - name: pip-audit - Vulnerabilidades
        run: |
          pip install -r requirements.txt 2>/dev/null || true
          pip-audit --format json --output pip-audit-report.json || true
          pip-audit --desc

      - name: Safety Check
        run: |
          safety check --json > safety-report.json || true

      - name: Verificar Licencas
        run: |
          pip-licenses --format=json --output-file=licenses.json
          python3 -c "
          import json
          PROHIBITED = ['GPL-3.0', 'AGPL-3.0', 'SSPL-1.0']
          with open('licenses.json') as f:
              licenses = json.load(f)
          violations = []
          for pkg in licenses:
              for p in PROHIBITED:
                  if p.lower() in pkg.get('License', '').lower():
                      violations.append(f'{pkg[\"Name\"]}: {pkg[\"License\"]}')
          if violations:
              print('ERRO: Licencas proibidas:')
              for v in violations:
                  print(f'  {v}')
              exit(1)
          print('Todas as licencas sao permitidas.')
          "

      - name: Dependency Review
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high

      - name: Upload Dependency Reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dependency-reports
          path: |
            pip-audit-report.json
            safety-report.json
            licenses.json

  # ============================================
  # FASE 5: IaC Security (30s)
  # ============================================
  fase-5-iac:
    name: "Fase 5: IaC Security"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Checkov - IaC Scanner
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: infrastructure/
          framework: terraform,cloudformation,dockerfile,kubernetes
          output_format: json
          output_file_path: checkov-results.json
          soft_fail: false

      - name: Hadolint - Dockerfile Linting
        run: |
          if [ -f Dockerfile ]; then
            docker run --rm -i hadolint/hadolint < Dockerfile
          fi

      - name: Kubesec - Kubernetes Security
        run: |
          if ls k8s/*.yaml 2>/dev/null; then
            for f in k8s/*.yaml; do
              echo "Verificando: $f"
              docker run --rm -i kubesec/kubesec:v2 scan /dev/stdin < "$f"
            done
          fi

      - name: Upload IaC Reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: iac-reports
          path: checkov-results.json

  # ============================================
  # FASE 6: SBOM (1min)
  # ============================================
  fase-6-sbom:
    name: "Fase 6: SBOM Generation"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Gerar SBOM com Syft
        run: |
          curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
          syft scan dir:. -o spdx-json > sbom-spdx.json
          syft scan dir:. -o cyclonedx-json > sbom-cyclonedx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom-spdx.json
            sbom-cyclonedx.json

  # ============================================
  # Security Gate - Decisao Final
  # ============================================
  security-gate:
    name: "Security Gate - Decisao Final"
    runs-on: ubuntu-latest
    needs: [fase-1-secrets, fase-2-sast, fase-3-codeql, fase-4-dependencias, fase-5-iac]
    if: always()
    steps:
      - name: Verificar Resultados
        run: |
          echo "=== Security Gate ==="

          # Verificar se algum job falhou
          FAILED=0

          if [ "${{ needs.fase-1-secrets.result }}" = "failure" ]; then
            echo "FALHA: Secret Scanning detectou secrets"
            FAILED=1
          fi

          if [ "${{ needs.fase-2-sast.result }}" = "failure" ]; then
            echo "FALHA: SAST encontrou vulnerabilidades criticas"
            FAILED=1
          fi

          if [ "${{ needs.fase-3-codeql.result }}" = "failure" ]; then
            echo "FALHA: CodeQL encontrou vulnerabilidades criticas"
            FAILED=1
          fi

          if [ "${{ needs.fase-4-dependencias.result }}" = "failure" ]; then
            echo "FALHA: Dependencias com vulnerabilidades criticas"
            FAILED=1
          fi

          if [ "${{ needs.fase-5-iac.result }}" = "failure" ]; then
            echo "FALHA: IaC com configuracoes inseguras"
            FAILED=1
          fi

          if [ "$FAILED" -eq 1 ]; then
            echo ""
            echo "O pipeline de seguranca BLOQUEOU o merge/deploy."
            echo "Corrija os problemas antes de prosseguir."
            exit 1
          fi

          echo "Todos os checks de seguranca PASSARAM."
```
{% endraw %}

---

## 8. Metricas de Shift-Left

### 8.1 Medindo Eficacia

Para saber se o shift-left esta funcionando, e preciso medir. As principais metricas sao:

**MTTR (Mean Time to Remediate):**
Tempo medio entre a deteccao de uma vulnerabilidade e sua correcao. Em pipelines shift-left, o MTTR ideal e menor que 24 horas para vulnerabilidades criticas e menor que 7 dias para high.

**Densidade de Vulnerabilidades por Commit:**
Numero medio de vulnerabilidades encontradas por commit. Uma tendencia de queda indica que os desenvolvedores estao aprendendo a escrever codigo mais seguro.

**Cobertura de Ferramentas:**
Porcentagem de repositorios com pelo menos um check de seguranca no CI/CD. O ideal e 100%.

**Tempo Medio de Build de Seguranca:**
Tempo total que todas as ferramentas de seguranca levam para executar. Deve ser menor que 10 minutos para nao impactar a produtividade.

**Taxa de Falsos Positivos:**
Numero de falsos positivos reportados pelas ferramentas. Uma taxa alta (>30%) indica necessidade de ajuste nas configuracoes.

### 8.2 KPIs e Dashboards

```python
#!/usr/bin/env python3
"""
shift_left_metrics.py - Calculo de metricas de Shift-Left Security.
Gera um dashboard simples com os KPIs principais.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class SecurityMetric:
    name: str
    value: float
    unit: str
    target: float
    status: str  # "green", "yellow", "red"


class ShiftLeftDashboard:
    def __init__(self):
        self.metrics: List[SecurityMetric] = []

    def add_metric(
        self,
        name: str,
        value: float,
        unit: str,
        target: float,
        comparison: str = "less_is_better",
    ):
        if comparison == "less_is_better":
            if value <= target:
                status = "green"
            elif value <= target * 1.5:
                status = "yellow"
            else:
                status = "red"
        else:
            if value >= target:
                status = "green"
            elif value >= target * 0.7:
                status = "yellow"
            else:
                status = "red"

        self.metrics.append(
            SecurityMetric(
                name=name,
                value=value,
                unit=unit,
                target=target,
                status=status,
            )
        )

    def calculate_mttr(self, vulnerabilities: List[Dict[str, Any]]) -> float:
        """Calcula o tempo medio de remediacao em horas."""
        remediation_times = []
        for vuln in vulnerabilities:
            if vuln.get("remediated_at") and vuln.get("detected_at"):
                detected = datetime.fromisoformat(vuln["detected_at"])
                remediated = datetime.fromisoformat(vuln["remediated_at"])
                hours = (remediated - detected).total_seconds() / 3600
                remediation_times.append(hours)

        if not remediation_times:
            return 0.0
        return sum(remediation_times) / len(remediation_times)

    def calculate_vulnerability_density(
        self,
        total_vulnerabilities: int,
        total_commits: int,
    ) -> float:
        """Calcula a densidade de vulnerabilidades por commit."""
        if total_commits == 0:
            return 0.0
        return total_vulnerabilities / total_commits

    def calculate_coverage(
        self,
        repos_with_security: int,
        total_repos: int,
    ) -> float:
        """Calcula a cobertura de ferramentas de seguranca."""
        if total_repos == 0:
            return 0.0
        return (repos_with_security / total_repos) * 100

    def calculate_false_positive_rate(
        self,
        false_positives: int,
        total_findings: int,
    ) -> float:
        """Calcula a taxa de falsos positivos."""
        if total_findings == 0:
            return 0.0
        return (false_positives / total_findings) * 100

    def generate_report(self) -> str:
        """Gera o relatorio do dashboard."""
        status_icons = {
            "green": "[OK]",
            "yellow": "[!]",
            "red": "[X]",
        }

        report = []
        report.append("=" * 60)
        report.append("  DASHBOARD - SHIFT-LEFT SECURITY METRICS")
        report.append(f"  Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        report.append("")

        for metric in self.metrics:
            icon = status_icons[metric.status]
            report.append(f"  {icon} {metric.name}")
            report.append(f"     Valor: {metric.value:.2f} {metric.unit}")
            report.append(f"     Meta:  {metric.target:.2f} {metric.unit}")
            report.append("")

        report.append("=" * 60)

        green_count = sum(1 for m in self.metrics if m.status == "green")
        total = len(self.metrics)

        report.append(f"  Resumo: {green_count}/{total} metricas dentro da meta")
        report.append("=" * 60)

        return "\n".join(report)


def main():
    dashboard = ShiftLeftDashboard()

    # MTTR: Tempo medio de remediacao
    vulnerabilities = [
        {
            "detected_at": "2025-01-15T10:00:00",
            "remediated_at": "2025-01-16T14:00:00",
        },
        {
            "detected_at": "2025-01-17T09:00:00",
            "remediated_at": "2025-01-18T11:00:00",
        },
        {
            "detected_at": "2025-01-20T08:00:00",
            "remediated_at": "2025-01-20T16:00:00",
        },
    ]

    mttr = dashboard.calculate_mttr(vulnerabilities)
    dashboard.add_metric(
        name="MTTR - Tempo Medio de Remediacao (horas)",
        value=mttr,
        unit="horas",
        target=24.0,
        comparison="less_is_better",
    )

    # Densidade de vulnerabilidades
    density = dashboard.calculate_vulnerability_density(
        total_vulnerabilities=15,
        total_commits=500,
    )
    dashboard.add_metric(
        name="Densidade de Vulnerabilidades por Commit",
        value=density,
        unit="vulns/commit",
        target=0.05,
        comparison="less_is_better",
    )

    # Cobertura de ferramentas
    coverage = dashboard.calculate_coverage(
        repos_with_security=28,
        total_repos=30,
    )
    dashboard.add_metric(
        name="Cobertura de Ferramentas de Seguranca (%)",
        value=coverage,
        unit="%",
        target=100.0,
        comparison="more_is_better",
    )

    # Taxa de falsos positivos
    fp_rate = dashboard.calculate_false_positive_rate(
        false_positives=12,
        total_findings=85,
    )
    dashboard.add_metric(
        name="Taxa de Falsos Positivos (%)",
        value=fp_rate,
        unit="%",
        target=20.0,
        comparison="less_is_better",
    )

    # Tempo de build de seguranca
    dashboard.add_metric(
        name="Tempo Total de Build de Seguranca (minutos)",
        value=8.5,
        unit="minutos",
        target=10.0,
        comparison="less_is_better",
    )

    # Repositorios com security gate
    security_gate_coverage = dashboard.calculate_coverage(
        repos_with_security=26,
        total_repos=30,
    )
    dashboard.add_metric(
        name="Repositorios com Security Gate (%)",
        value=security_gate_coverage,
        unit="%",
        target=100.0,
        comparison="more_is_better",
    )

    print(dashboard.generate_report())


if __name__ == "__main__":
    main()
```

---

## 9. Referencias

1. **OWASP Top 10 (2021)** - https://owasp.org/Top10/
2. **NIST SP 800-218 - Secure Software Development Framework** - https://csrc.nist.gov/publications/detail/ssdf/1.1/final
3. **Microsoft Secure Future Initiative** - https://query.prod.cms.rt.microsoft.com/cms/api/am/binary/RE5VJyb
4. **Google BeyondCorp** - https://beyondcorp.corp.google.com/
5. **SonarSource - DevSecOps Best Practices** - https://www.sonarsource.com/solutions/devsecops/
6. **Snyk - State of Open Source Security Report** - https://snyk.io/report/open-source-security/
7. **Semgrep Documentation** - https://semgrep.dev/docs/
8. **CodeQL Documentation** - https://codeql.github.com/docs/
9. **GitLeaks Documentation** - https://github.com/gitleaks/gitleaks
10. **TruffleHog Documentation** - https://trufflesecurity.com/trufflehog
11. **Checkov Documentation** - https://www.checkov.io/
12. **OWASP CycloneDX** - https://cyclonedx.org/
13. **SPDX Specification** - https://spdx.dev/
14. **FOSSA Documentation** - https://docs.fossa.com/
15. **Syft Documentation** - https://github.com/anchore/syft

### Estudos de Caso Publicos

16. **GitHub: How We Built CodeQL** - https://github.blog/2019-02-14-how-we-built-codeql-github/
17. **Google: Fuzzing at Scale** - https://research.google/pubs/pub48149/
18. **Mozilla: Static Analysis at Scale** - https://wiki.mozilla.org/Static_Analysis
19. **Netflix: Security Monkey to Metaflow** - https://netflix.github.io/
20. **Capital One: DevSecOps Transformation** - https://www.capitalone.com/tech/engineering/devsecops/

---

> **Proximo Capitulo:** Capitulo 4 — Controle de Acesso e Identidade (IAM) no DevSecOps
