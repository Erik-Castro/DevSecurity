---
layout: default
title: "01-introducao-ao-devsecops"
---

# Capítulo 1 — Introdução ao DevSecOps

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Definir e contextualizar DevSecOps** em relação a DevOps e SecOps, compreendendo a evolução histórica que levou à integração de segurança no ciclo de vida do desenvolvimento de software.
2. **Identificar as causas raiz da falha de segurança em ambientes ágeis**, incluindo gargalos tradicionais, fricção entre equipes e a ausência de automação de segurança em pipelines CI/CD.
3. **Aplicar os princípios fundamentais do DevSecOps** — shift-left, verificação contínua, defesa em profundidade, menor privilégio e infraestrutura imutável — com exemplos práticos de implementação.
4. **Avaliar a maturidade DevSecOps de uma organização** usando o modelo de níveis 0 a 5, com checklist de avaliação e roadmap de evolução.
5. **Mapear o ecossistema de ferramentas DevSecOps** e integrar ferramentas de SAST, DAST, SCA, scanning de segredos, containers e IaC em pipelines CI/CD reais.

---

## 1. O que é DevSecOps

### 1.1 Definição e Evolução a partir do DevOps

DevSecOps é a prática de incorporar segurança de forma automática, contínua e compartilhada em todas as fases do ciclo de vida do desenvolvimento de software — desde o planejamento até a operação e monitoramento. O termo surgiu como uma evolução natural do DevOps, que por sua vez nasceu da necessidade de colmatar o abismo entre equipes de desenvolvimento e operações.

A evolução pode ser compreendida em três grandes marcos:

**Fase 1: Waterfall e Segurança Isolada (até 2008)**

O modelo tradicional em cascata tratava segurança como uma fase final — um checkpoint antes da liberação. Vulnerabilidades descobertas nessa fase exigiam retrabalho massivo, gerando custos exponenciais.

```text
Planejamento -> Desenvolvimento -> Testes -> Segurança -> Deploy
                                                   ^
                                                   |
                                            Gargalo crítico
                                            (fim do ciclo)
```

**Fase 2: DevOps e Agilidade (2009-2015)**

O DevOps eliminou o muro entre Dev e Ops, promovendo integração contínua (CI) e entrega contínua (CD). Entretanto, segurança continuou sendo frequentemente negligenciada ou tratada como obstáculo à velocidade.

```text
Planejamento <-> Desenvolvimento <-> Testes <-> Deploy <-> Monitoramento
     |                                                         |
     +------------- Feedback contínuo ------------------------+
                   (sem segurança integrada)
```

**Fase 3: DevSecOps (2015-atual)**

DevSecOps integra segurança como responsabilidade compartilhada em todas as fases, automatizando verificações de segurança e eliminando o trade-off entre velocidade e segurança.

```text
Planejamento <-> Desenvolvimento <-> Testes <-> Deploy <-> Monitoramento
     |    |            |    |            |    |           |       |
     S    S            S    S            S    S           S       S
     |    |            |    |            |    |           |       |
     Segurança como pilar transversal em todo o ciclo
```

### 1.2 Os Três Pilares: Dev + Sec + Ops

DevSecOps é composto por três pilares interdependentes. A remoção de qualquer um deles degrada o modelo para uma versão inferior do anterior.

| Pilar | Responsabilidade | Prática Principal | Resultado Esperado |
|-------|-------------------|-------------------|---------------------|
| **Dev** (Desenvolvimento) | Escrever código seguro, revisar código, testes unitários de segurança | SAST, code review automatizado, testes de composição | Código com menos vulnerabilidades na origem |
| **Sec** (Segurança) | Definir políticas, conduzir testes, responder incidentes | DAST, pen testing, monitoramento de ameaças | Cobertura de segurança verificável e auditoria |
| **Ops** (Operações) | Manter infraestrutura segura, monitorar, responder | Hardening, patches, response automatizado | Ambiente resiliente e compliance contínuo |

A interação entre os pilares cria um ciclo de feedback onde cada área contribui e se beneficia das outras:

```text
        +-----------+
        |    Sec    |
        | Políticas |
        | Testes    |
        +-----+-----+
              |
    +---------+---------+
    |                   |
+---+---+         +-----+-----+
|  Dev  |         |    Ops    |
| Código|         | Infra     |
| Tests |         | Monitor   |
+---+---+         +-----+-----+
    |                   |
    +--------+----------+
             |
      Feedback contínuo
```

### 1.3 DevSecOps vs DevOps vs SecOps

A tabela a seguir diferencia os três modelos de forma clara:

| Aspecto | DevOps | SecOps | DevSecOps |
|---------|--------|--------|-----------|
| **Foco principal** | Velocidade e colaboração | Controle e conformidade | Velocidade + Segurança |
| **Segurança** | Responsabilidade secundária | Responsabilidade primária | Responsabilidade compartilhada |
| **Velocidade de entrega** | Alta | Baixa | Alta |
| **Automação de segurança** | Mínima | Manual/escaneamento periódico | Integrada e contínua |
| **Feedback de segurança** | Tardio (produção) | Periódico (auditorias) | Imediato (cada commit) |
| **Custo de correção** | Alto (produção) | Variável | Baixo (desenvolvimento) |
| **Cultura** | Colaboração Dev-Ops | Segurança isolada | Segurança é responsabilidade de todos |
| **Métricas principais** | Lead time, deploy frequency | Número de vulnerabilidades, compliance | MTTR, vuln detection time, fix rate |

### 1.4 O Manifesto DevSecOps

Assim como o Manifesto Ágil transformou o desenvolvimento de software, o Manifesto DevSecOps estabelece princípios fundamentais para a segurança contínua:

```text
Estamos descobrindo maneiras melhores de desenvolver software,
mantendo a segurança como parte intrínseca do processo, e ajudando
outras organizações a fazerem o mesmo.

Por meio do nosso trabalho, passamos a valorizar:

Automatizar o mais possível                        > Processos manuais de segurança
Verificar segurança contínuamente                   > Testar apenas no final
Responsabilidade compartilhada                      > Segurança como silo
Segurança como facilitadora                         > Segurança como obstáculo
Infraestrutura como código, incluindo política      > Configuração manual

Assim como no Manifesto Ágil, valorizamos os itens da direita,
mas valorizamos MAIS os itens da esquerda.
```

### 1.5 Modelo de Maturidade para Adoção de DevSecOps

A adoção de DevSecOps não acontece da noite para o dia. É um processo gradual que segue níveis de maturidade. O modelo a seguir, inspirado noCapability Maturity Model Integration (CMMI), define seis níveis (0 a 5) que uma organização pode percorrer.

**Nível 0 — Ausente**
- Não existe prática formal de segurança no ciclo de desenvolvimento
- Vulnerabilidades são descobertas apenas em produção ou por terceiros
- Não há ferramentas automatizadas de segurança

**Nível 1 — Inicial/Reativo**
- Segurança é tratada de forma ad hoc, apenas quando necessária
- Testes de segurança são manuais e inconsistentes
- Não há padrões definidos para código seguro

**Nível 2 — Repetível/Consciente**
- Algumas práticas de segurança são repetidas em projetos
- Ferramentas básicas de SAST ou DAST são usadas esporadicamente
- Equipe reconhece a importância da segurança

**Nível 3 — Definido/Proativo**
- Políticas de segurança são documentadas e padronizadas
- Ferramentas de segurança são integradas ao CI/CD
- Treinamento de segurança para desenvolvedores é formal
- Code review com checklist de segurança é obrigatório

**Nível 4 — Gerenciado/Mensurado**
- Métricas de segurança são coletadas e analisadas
- Vulnerabilidades têm SLA de correção definido
- Segurança é medível e auditável
- Dashboards de segurança em tempo real

**Nível 5 — Otimizado/Adaptativo**
- Segurança é completamente automatizada e contínua
- Machine learning é aplicado a detecção de anomalias
- Organização contribui para segurança do ecossistema (open source)
- Segurança é vantagem competitiva, não custo

---

## 2. Por que Segurança Falha em Ambientes Ágeis

### 2.1 Segurança Tradicional como Gargalo

O modelo tradicional de segurança tratava o escaneamento como uma fase final do ciclo de vida. Isso criava um gargalo natural:

```text
Ciclo Tradicional (Waterfall com Segurança):
+-----------+     +-----------+     +-----------+     +-----------+
| Planejamento| -> | Desenvolvimento| -> | Testes  | -> | SEGURANÇA |
+-----------+     +-----------+     +-----------+     +-----------+
                                                       Duração: 2-4 semanas
                                                       Custo: $50.000-$500.000
                                                       Descobertas: 150+ vulns
                                                       Retrabalho: 60-80% do código
```

Quando vulnerabilidades são descobertas no final, o custo de correção é exponencialmente maior:

| Fase de Descoberta | Custo Relativo de Correção |
|---------------------|---------------------------|
| Planejamento (requisitos) | 1x |
| Desenvolvimento | 5x |
| Testes | 10x |
| Staging/Pre-produção | 30x |
| Produção | 100x |

### 2.2 O Problema do "Throw it Over the Wall"

O termo "jogar por cima do muro" descreve a prática de desenvolvimento entregar código para segurança testar, sem colaboração prévia. Este padrão é extremamente prejudicial:

```text
Equipe de Desenvolvimento                 Equipe de Segurança
+------------------+                      +------------------+
|                  |                      |                  |
| Escreve código   | --- "Joga por       | Encontra 200     |
| Sem verificações |     cima do muro"    | vulnerabilidades |
| de segurança     | -------------------> | Pede retrabalho  |
|                  |                      |                  |
+------------------+                      +------------------+
                                              |
                                              v
                                        +-----------+
                                        | Atraso:   |
                                        | 3-6 meses |
                                        | Custo:    |
                                        | alto      |
                                        +-----------+
```

### 2.3 Fricção entre Equipes de Segurança e Desenvolvimento

A fricção entre equipes é um dos maiores obstáculos para a adoção de DevSecOps. As causas incluem:

**Linguagens diferentes:**
- Desenvolvedores falam em features, velocity, sprint
- Segurança fala em vulnerabilidades, CVE, CVSS, compliance
- Ops fala em uptime, SLA, MTTR

**Prioridades conflitantes:**
- Dev quer entregar features rapidamente
- Segurança quer pausar para correções
- Ops quer estabilidade

**Falta de contexto compartilhado:**
- Desenvolvedores não entendem por que certas vulnerabilidades são críticas
- Segurança não entende o contexto de negócio do código
- Ambos operam em silos com ferramentas diferentes

A solução é DevSecOps: compartilhar responsabilidade, ferramentas e linguagem.

### 2.4 Estatísticas sobre Segurança em CI/CD

Dados recentes demonstram a urgência da adoção de DevSecOps:

- **83%** dos desenvolvedores fazem push de código com alguma vulnerabilidade conhecida (Sonatype, 2023)
- **76%** dos incidentes de segurança envolvem credenciais ou segredos expostos no código (GitGuardian, 2023)
- **60%** das empresas não automatizam testes de segurança em pipelines CI/CD (DORA, 2023)
- **Apenas 13%** das organizações atingem o nível 4 ou 5 de maturidade DevSecOps (Gartner, 2023)
- **45%** dos desenvolvedores não recebem treinamento regular de segurança (Snyk, 2023)
- **O custo médio de uma brecha de segurança** atingiu US$ 4,45 milhões em 2023 (IBM, 2023)
- **68%** das brechas envolvem componente humano ( Verizon DBIR, 2023)

### 2.5 Estudo de Caso: Equifax — O que Testes Automatizados Teriam Capturado

Em 17 de setembro de 2017, a Equifax — uma das três maiores bureaus de crédito dos EUA — anunciou que dados pessoais de 147 milhões de pessoas foram comprometidos. A brecha ocorreu entre maio e julho de 2017, mas o ataque começou em março de 2017.

**O que aconteceu:**

A Equifax usava o Apache Struts, um framework web Java. Uma vulnerabilidade crítica (CVE-2017-5638) foi divulgada em 7 de março de 2017. A Equifax não aplicou a correção. Atacantes exploraram essa vulnerabilidade em 10 de maio de 2017, obtendo acesso não autorizado a bancos de dados sensíveis.

**Falhas que testes automatizados teriam capturado:**

```text
Vulnerabilidade CVE-2017-5638 (Apache Struts):
  Tipo: Remote Code Execution (RCE)
  Severidade: CRÍTICA (CVSS 10.0)
  Data da advisory: 7 de março de 2017
  Patch disponível: Sim, desde o dia da advisory
  Status na Equifax: NÃO APLICADO
```

| Ferramenta | O que teria detectado | Quando detectaria |
|------------|----------------------|-------------------|
| **SCA (Software Composition Analysis)** | Versão vulnerável do Apache Struts na composição de dependências | No build — antes do deploy |
| **SAST (Static Application Testing)** | Chamadas HTTP não sanitizadas que alimentam o Struts | No commit/push |
| **DAST (Dynamic Application Testing)** | A exploração do CVE-2017-5638 contra a aplicação em staging | No pipeline de staging |
| **IaC Scanning** | Configurações de container ou servidor desatualizadas | Na construção da infraestrutura |
| **Dependency-Check** | Bibliotecas com CVEs conhecidas no classpath | No build CI |

**Implementação de SCA que teria prevenido a brecha:**

```yaml
# .github/workflows/security-sca.yml
name: Software Composition Analysis

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

      - name: Set up JDK
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Run OWASP Dependency-Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          path: '.'
          format: 'HTML'
          fail_on_cvss: 7

      - name: Check for known CVEs
        run: |
          # Verifica se há dependências com CVEs de severidade >= 7
          python3 scripts/check_cve_threshold.py \
            --report reports/dependency-check-report.html \
            --threshold 7 \
            --fail-on-match

      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dependency-check-report
          path: reports/
```

**Script de verificação de CVEs:**

```python
#!/usr/bin/env python3
"""
Verifica o relatório do OWASP Dependency-Check e falha se
CVEs acima do threshold forem encontrados.
"""
import argparse
import re
import sys
from pathlib import Path


def parse_dependency_check_report(report_path: str) -> list[dict]:
    """Extrai vulnerabilidades do relatório HTML do Dependency-Check."""
    vulnerabilities = []
    content = Path(report_path).read_text(encoding="utf-8")

    # Padrão para extrair CVEs do relatório HTML
    cve_pattern = re.compile(
        r'<td>(CVE-\d{4}-\d+)</td>.*?<td>([\d.]+)</td>',
        re.DOTALL
    )

    for match in cve_pattern.finditer(content):
        cve_id, cvss_score = match.groups()
        vulnerabilities.append({
            "cve": cve_id,
            "cvss": float(cvss_score)
        })

    return vulnerabilities


def check_threshold(vulns: list[dict], threshold: int) -> list[dict]:
    """Retorna vulnerabilidades acima do threshold de CVSS."""
    return [v for v in vulns if v["cvss"] >= threshold]


def main():
    parser = argparse.ArgumentParser(
        description="Verifica CVEs no relatório de Dependency-Check"
    )
    parser.add_argument("--report", required=True, help="Caminho do relatório HTML")
    parser.add_argument("--threshold", type=int, default=7,
                        help="Threshold de CVSS (default: 7)")
    parser.add_argument("--fail-on-match", action="store_true",
                        help="Falhar se vulnerabilidades forem encontradas")

    args = parser.parse_args()

    vulns = parse_dependency_check_report(args.report)
    critical_vulns = check_threshold(vulns, args.threshold)

    if critical_vulns:
        print(f"\n[FAIL] {len(critical_vulns)} vulnerabilidade(s) "
              f"com CVSS >= {args.threshold} encontrada(s):\n")
        for v in critical_vulns:
            print(f"  - {v['cve']} (CVSS: {v['cvss']})")
        print()

        if args.fail_on_match:
            sys.exit(1)
    else:
        print(f"\n[PASS] Nenhuma vulnerabilidade com CVSS >= {args.threshold}")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Impacto da Equifax:**

- **147 milhões** de pessoas afetadas
- **US$ 1,4 bilhão** em custos relacionados à brecha
- **US$ 700 milhões** de acordo com a FTC
- **CEO, CIO e CISO** demitidos
- **30+ processos judiciais** movidos

Se a Equifax tivesse um pipeline CI/CD com SCA automatizado, a vulnerabilidade teria sido detectada no dia em que a dependência foi introduzida (ou no build seguinte após a divulgação da CVE), e o patch teria sido aplicado antes do ataque.

---

## 3. Princípios Fundamentais do DevSecOps

### 3.1 Automação em Primeiro Lugar

O princípio mais fundamental do DevSecOps é: se pode ser automatizado, DEVE ser automatizado. A automação elimina erros humanos, garante consistência e permite que verificações de segurança rodem em cada build sem exceção.

```yaml
# Exemplo: Pipeline com automação completa de segurança
name: DevSecOps Automated Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  security-automated:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: SAST - Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/owasp-top-ten
            p/python
            p/security-audit
          generateSarif: true

      - name: Secret Scanning - GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: SCA - Snyk
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

      - name: Container Scanning - Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: IaC Scanning - Checkov
        uses: bridgecrewio/checkov-action@master
        with:
          directory: .
          framework: terraform,dockerfile
          soft_fail: false
```

### 3.2 Shift-Left Security (Segurança à Esquerda)

Shift-left significa mover a verificação de segurança para o estágio mais inicial possível do ciclo de vida. Quanto mais cedo uma vulnerabilidade é detectada, menor o custo de correção.

```text
SHIFT-LEFT: Onde encontrar vulnerabilidades

Traditional:                                              Shift-Left:
[Plan] [Code] [Build] [Test] [Deploy] [Monitor]          [Plan] [Code] [Build] [Test] [Deploy] [Monitor]
                                          ^                    ^     ^     ^
                                          |                    |     |     |
                                     Segurança aqui      Segurança    |     |
                                          |               aqui        |     |
                                     Custo: 100x              |      |     |
                                                              |      |     |
                                                         Custo  |   Custo  Custo
                                                         5x     |   10x    30x
                                                                |
                                                           Ideia aqui
                                                           Custo 1x
```

**Implementação do shift-left com pre-commit hooks:**

```bash
#!/bin/bash
# install-hooks.sh — Instala hooks de segurança no repositório

set -euo pipefail

echo "=== Instalando hooks de pré-commit de segurança ==="

# Instala pre-commit se não estiver instalado
if ! command -v pre-commit &> /dev/null; then
    pip install pre-commit
fi

# Cria o .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: Secret Scanning

  - repo: https://github.com/semgrep/semgrep
    rev: v1.50.0
    hooks:
      - id: semgrep
        name: SAST - Semgrep
        args: ['--config', 'p/owasp-top-ten', '--error']

  - repo: https://github.com/bridgecrewio/checkov
    rev: 3.1.44
    hooks:
      - id: checkov
        name: IaC Scanning
        args: ['--directory', '.', '--soft-fail']

  - repo: local
    hooks:
      - id: no-secrets-in-code
        name: Verificar segredos em código
        entry: bash -c 'grep -rn "password\|secret\|api_key\|token" --include="*.py" --include="*.js" . && exit 1 || exit 0'
        language: system
        types: [python, javascript]
EOF

# Instala os hooks
pre-commit install

echo "=== Hooks instalados com sucesso ==="
```

**Exemplo de .pre-commit-config.yaml com múltiplas ferramentas de segurança:**

```yaml
# .pre-commit-config.yaml
repos:
  # --- Secret Scanning ---
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  # --- SAST com Semgrep ---
  - repo: https://github.com/semgrep/semgrep
    rev: v1.50.0
    hooks:
      - id: semgrep
        args: ['--config', 'auto', '--error']

  # --- IaC Scanning ---
  - repo: https://github.com/bridgecrewio/checkov
    rev: 3.1.44
    hooks:
      - id: checkov
        args: ['--directory', '.', '--framework', 'dockerfile,terraform']

  # --- Python linting de segurança ---
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.6
    hooks:
      - id: bandit
        args: ['-r', '.', '-ll']

  # --- Commit message com conventional commits ---
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.1.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

### 3.3 Verificação Contínua

Segurança não é um evento — é um processo contínuo. A verificação contínua garante que cada mudança no código, na infraestrutura ou nas dependências seja automaticamente avaliada quanto a riscos.

```yaml
# Verificação contínua com cron para detectar novas vulnerabilidades
name: Continuous Security Monitoring

on:
  schedule:
    - cron: '0 6 * * *'  # Roda todo dia às 6h UTC
  workflow_dispatch:

jobs:
  continuous-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: SCA - Verificar novas CVEs em dependências
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --all-projects --severity-threshold=medium

      - name: Container Re-scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myregistry/myapp:latest'
          severity: 'CRITICAL,HIGH'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: License Compliance Check
        run: |
          pip install pip-licenses
          pip-licenses --format=json --output-file=licenses.json
          python3 scripts/check_licenses.py \
            --input licenses.json \
            --policy policies/allowed-licenses.json

      - name: Secret Rotation Check
        run: |
          python3 scripts/check_secret_rotation.py \
            --max-age-days 90 \
            --services aws,gcp,github
```

### 3.4 Defesa em Profundidade nos Pipelines

Defesa em profundidade significa aplicar múltiplas camadas de segurança. Se uma falhar, outra está lá para capturar a ameaça.

```text
Camadas de Defesa em Profundidade no Pipeline:

Camada 1: Desenvolvedor (local)
  └─ Pre-commit hooks (secret scanning, linting)
  └─ IDE plugins (SAST em tempo real)

Camada 2: Pull Request
  └─ Code review automatizado (dependabot, renovate)
  └─ SAST no diff
  └─ Secret scanning no diff

Camada 3: Build/CI
  └─ SAST completo
  └─ SCA (análise de composição)
  └─ Unit tests de segurança
  └─ DAST em ambiente isolado

Camada 4: Staging
  └─ DAST completo (OWASP ZAP)
  └─ Pen testing automatizado
  └─ Container scanning
  └─ IaC scanning

Camada 5: Deploy/Produção
  └─ Verificação de integridade (image signing)
  └─ Runtime protection (WAF, RASP)
  └─ Monitoramento contínuo
  └─ Response automatizado
```

```yaml
# Exemplo de pipeline com defesa em profundidade
name: Defense in Depth Pipeline

on: [push, pull_request]

jobs:
  # Camada 1: Análise estática no código
  layer-1-sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/owasp-top-ten
            p/python
            p/secrets

  # Camada 2: Análise de composição
  layer-2-sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  # Camada 3: Container scanning
  layer-3-container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -t app:${{ github.sha }} .
      - uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'app:${{ github.sha }}'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

  # Camada 4: IaC scanning
  layer-4-iac:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bridgecrewio/checkov-action@master
        with:
          directory: terraform/
          framework: terraform
```

### 3.5 Menor Privilégio para Agents de Pipeline

Agentes de CI/CD devem operar com o mínimo de permissões necessário. Princípio fundamental de segurança que se aplica diretamente aos pipelines.

```yaml
# Exemplo: Pipeline com menor privilégio
name: Least Privilege Pipeline

on:
  push:
    branches: [main]

permissions:
  contents: read        # Apenas leitura do código
  security-events: write # Para enviar resultados de segurança

jobs:
  security-scan:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4

      - name: SAST Scan
        uses: semgrep/semgrep-action@v1
        with:
          config: p/owasp-top-ten
          generateSarif: true

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: semgrep.sarif

  # Deploy só roda APÓS todas as verificações passarem
  deploy:
    needs: [security-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # OIDC para cloud (sem secrets hardcoded)
    steps:
      - uses: actions/checkout@v4
      - name: Deploy via OIDC
        run: |
          # Usa OIDC em vez de long-lived credentials
          aws configure set role_arn ${{ secrets.AWS_ROLE_ARN }}
          aws sts get-caller-identity
```

### 3.6 Infraestrutura Imutável

Infraestrutura imutável significa que containers e servidores são criados, nunca modificados. Se uma correção de segurança é necessária, um novo container é criado — nunca se aplica patch em um container em execução.

```dockerfile
# Dockerfile multi-stage para infraestrutura imutável
# Cada build gera um artifact novo, nunca se modifica o existente

# Stage 1: Build com verificação de segurança
FROM python:3.12-slim AS builder

# Instala ferramentas de verificação
RUN pip install --no-cache-dir pip-audit safety

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verifica dependências durante o build
RUN pip-audit -r requirements.txt --output /audit-results.txt

# Stage 2: Runtime (imutável)
FROM python:3.12-slim AS runtime

# Usa usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copia apenas o necessário
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser . .

# Muda para usuário não-root
USER appuser

# Verificação final durante o build
RUN python -c "import ast; ast.parse(open('main.py').read())"

EXPOSE 8000

# Health check embutido
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "main.py"]
```

---

## 4. O Maturidade DevSecOps

### 4.1 Níveis 0 a 5 de Maturidade DevSecOps

O modelo de maturidade DevSecOps avaliá cinco dimensões em cada nível:

```text
Dimensões Avaliadas:
1. Pessoas e Cultura
2. Processos e Práticas
3. Ferramentas e Automação
4. Métricas e Observabilidade
5. Governança e Compliance
```

**Nível 0 — Ausente**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | Sem treinamento de segurança |
| Processos | Nenhum processo formal |
| Ferramentas | Nenhuma ferramenta de segurança automatizada |
| Métricas | Sem métricas de segurança |
| Governança | Sem políticas documentadas |

```bash
# Sinal de Nível 0: Nenhuma verificação de segurança no pipeline
$ cat .github/workflows/ci.yml
# (apenas build e deploy, sem steps de segurança)
```

**Nível 1 — Inicial/Reativo**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | Treinamento ad hoc |
| Processos | Revisão manual de segurança |
| Ferramentas | Ferramentas instaladas, mas não integradas ao CI |
| Métricas | Contagem manual de vulnerabilidades |
| Governança | Políticas verbais |

```yaml
# Sinal de Nível 1: Ferramenta configurada, mas rodando manualmente
- name: Security Scan (manual)
  run: |
    echo "Execute manualmente: semgrep --config auto ."
    echo "Resultados devem ser revisados pelo time de segurança"
  # NÃO roda automaticamente no pipeline
```

**Nível 2 — Repetível/Consciente**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | Treinamento regular, awareness |
| Processos | SAST e DAST integrados em alguns projetos |
| Ferramentas | Algumas ferramentas automatizadas no CI |
| Métricas | Relatórios periódicos (mensais) |
| Governança | Políticas documentadas |

```yaml
# Sinal de Nível 2: SAST integrado em pipelines, mas sem enforcement
- name: SAST
  uses: semgrep/semgrep-action@v1
  continue-on-error: true  # NÃO falha o build
```

**Nível 3 — Definido/Proativo**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | Treinamento obrigatório, champion de segurança |
| Processos | Pipeline de segurança padronizado, security gates |
| Ferramentas | SAST, SCA, secret scanning, IaC scanning |
| Métricas | KPIs definidos, dashboards |
| Governança | Compliance automatizado |

```yaml
# Sinal de Nível 3: Security gate que falha o build
- name: SAST
  uses: semgrep/semgrep-action@v1
  with:
    config: p/owasp-top-ten
    # Falha o build se encontrar vulnerabilidades

- name: Secret Scanning
  uses: gitleaks/gitleaks-action@v2
  # Falha o build se encontrar segredos
```

**Nível 4 — Gerenciado/Mensurado**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | DevSecOps como prática diária |
| Processos | Security champions, threat modeling |
| Ferramentas | Todas as categorias integradas |
| Métricas | MTTR < 24h, detection time < 1h |
| Governança | Compliance contínuo, auditoria automatizada |

```yaml
# Sinal de Nível 4: Métricas, SLA e enforcement completo
- name: Security Gate Enforcement
  run: |
    python3 scripts/security_gate.py \
      --max-critical 0 \
      --max-high 0 \
      --max-medium 5 \
      --mttr-sla 24 \
      --enforce
```

**Nível 5 — Otimizado/Adaptativo**

| Dimensão | Característica |
|----------|----------------|
| Pessoas | Segurança como vantagem competitiva |
| Processos | ML para detecção, auto-remediation |
| Ferramentas | Plataforma unificada com feedback loop |
| Métricas | Análise preditiva, benchmarking |
| Governança | Contribui para ecossistema (open source, CVEs) |

### 4.2 Checklist de Avaliação de Maturidade

```markdown
## Checklist de Avaliação de Maturidade DevSecOps

### 1. Pessoas e Cultura (peso: 25%)
- [ ] Nível 0: Sem treinamento de segurança para devs
- [ ] Nível 1: Treinamento anual opcional
- [ ] Nível 2: Treinamento regular, awareness
- [ ] Nível 3: Treinamento obrigatório, security champions
- [ ] Nível 4: DevSecOps como prática diária
- [ ] Nível 5: Segurança como vantagem competitiva

### 2. Processos e Práticas (peso: 25%)
- [ ] Nível 0: Sem processos formais
- [ ] Nível 1: Revisão manual ad hoc
- [ ] Nível 2: SAST/DAST em alguns projetos
- [ ] Nível 3: Pipeline padronizado com security gates
- [ ] Nível 4: Threat modeling, security champions
- [ ] Nível 5: ML para detecção, auto-remediation

### 3. Ferramentas e Automação (peso: 25%)
- [ ] Nível 0: Nenhuma ferramenta
- [ ] Nível 1: Ferramentas instaladas, não integradas
- [ ] Nível 2: Algumas integradas no CI
- [ ] Nível 3: SAST, SCA, secrets, IaC no pipeline
- [ ] Nível 4: Todas as categorias, plataforma unificada
- [ ] Nível 5: Feedback loop com ML

### 4. Métricas e Observabilidade (peso: 15%)
- [ ] Nível 0: Sem métricas
- [ ] Nível 1: Contagem manual
- [ ] Nível 2: Relatórios periódicos
- [ ] Nível 3: KPIs definidos, dashboards
- [ ] Nível 4: MTTR < 24h, detection < 1h
- [ ] Nível 5: Análise preditiva, benchmarking

### 5. Governança e Compliance (peso: 10%)
- [ ] Nível 0: Sem políticas
- [ ] Nível 1: Políticas verbais
- [ ] Nível 2: Políticas documentadas
- [ ] Nível 3: Compliance automatizado
- [ ] Nível 4: Auditoria contínua
- [ ] Nível 5: Contribuição para ecossistema
```

### 4.3 Roadmap de Evolução

```text
Roadmap de Adoção DevSecOps (12-18 meses):

Mês 1-3: Fundação (Nível 0 -> 1)
  ├── Instalar SAST (Semgrep) no CI
  ├── Configurar Secret Scanning (GitLeaks)
  ├── Treinamento básico para devs
  └── Criar .pre-commit-config.yaml

Mês 4-6: Expansão (Nível 1 -> 2)
  ├── Adicionar SCA (Snyk/Trivy)
  ├── Adicionar IaC Scanning (Checkov)
  ├── Definir security gates básicos
  └── Primeiro relatório de métricas

Mês 7-9: Consolidação (Nível 2 -> 3)
  ├── Padronizar pipeline de segurança
  ├── Implementar DAST (OWASP ZAP)
  ├── Security champions program
  ├── Dashboards de métricas
  └── SLA de correção definido

Mês 10-12: Excelência (Nível 3 -> 4)
  ├── Platform engineering de segurança
  ├── Automatizar compliance
  ├── MTTR < 24h como meta
  └── Auditoria contínua

Mês 13-18: Liderança (Nível 4 -> 5)
  ├── ML para detecção de anomalias
  ├── Auto-remediation para vulnerabilidades comuns
  ├── Contribuição para open source security
  └── Benchmarking com indústria
```

### 4.4 Template Completo de Avaliação de Maturidade

```python
#!/usr/bin/env python3
"""
Template de avaliação de maturidade DevSecOps.
Gera um relatório baseado em questionário estruturado.
"""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class MaturityLevel(IntEnum):
    ABSENT = 0
    INITIAL = 1
    REPEATABLE = 2
    DEFINED = 3
    MANAGED = 4
    OPTIMIZED = 5


class Dimension:
    PESSOAS = "Pessoas e Cultura"
    PROCESSOS = "Processos e Praticas"
    FERRAMENTAS = "Ferramentas e Automacao"
    METRICAS = "Metricas e Observabilidade"
    GOVERNANCA = "Governanca e Compliance"


DIMENSION_WEIGHTS = {
    Dimension.PESSOAS: 0.25,
    Dimension.PROCESSOS: 0.25,
    Dimension.FERRAMENTAS: 0.25,
    Dimension.METRICAS: 0.15,
    Dimension.GOVERNANCA: 0.10,
}


@dataclass
class AssessmentResult:
    dimension: str
    level: MaturityLevel
    score: float
    recommendations: list[str] = field(default_factory=list)


def assess_dimension(dimension: str, level: int) -> AssessmentResult:
    """Avalia uma dimensão e retorna resultado com recomendações."""
    ml = MaturityLevel(min(max(level, 0), 5))
    weight = DIMENSION_WEIGHTS[dimension]
    score = ml.value / 5.0 * 100 * weight

    recommendations = {
        MaturityLevel.ABSENT: [
            "Instalar pelo menos uma ferramenta SAST no CI",
            "Configurar secret scanning em todos os repositorios",
            "Realizar treinamento basico de seguranca para devs",
        ],
        MaturityLevel.INITIAL: [
            "Integrar SAST e SCA no pipeline CI/CD",
            "Definir security gates que falhem o build",
            "Implementar code review com checklist de seguranca",
        ],
        MaturityLevel.REPEATABLE: [
            "Adicionar DAST ao pipeline",
            "Implementar IaC scanning",
            "Definir KPIs de seguranca e SLAs",
        ],
        MaturityLevel.DEFINED: [
            "Implementar security champions program",
            "Automatizar compliance checking",
            "Criar dashboards em tempo real",
        ],
        MaturityLevel.MANAGED: [
            "Explorar ML para deteccao de anomalias",
            "Implementar auto-remediation",
            "Contribuir para seguranca do ecossistema",
        ],
        MaturityLevel.OPTIMIZED: [
            "Mantenha a excelencia e mentorou outras organizacoes",
        ],
    }

    return AssessmentResult(
        dimension=dimension,
        level=ml,
        score=score,
        recommendations=recommendations.get(ml, []),
    )


def generate_report(assessments: list[AssessmentResult]) -> str:
    """Gera relatorio completo de maturidade."""
    total_score = sum(a.score for a in assessments)
    overall_level = total_score / (100 * sum(DIMENSION_WEIGHTS.values())) * 5

    report = [
        "=" * 60,
        "  RELATORIO DE MATURIDADE DEVSECOPS",
        "=" * 60,
        "",
        f"  Pontuacao Total: {total_score:.1f}/100",
        f"  Nivel Geral: {overall_level:.1f}/5",
        "",
    ]

    level_names = {
        0: "Ausente",
        1: "Inicial/Reativo",
        2: "Repetivel/Consciente",
        3: "Definido/Proativo",
        4: "Gerenciado/Mensurado",
        5: "Otimizado/Adaptativo",
    }

    for a in assessments:
        report.append(f"  {a.dimension}")
        report.append(f"    Nivel: {a.level.value} - {level_names.get(a.level.value, '?')}")
        report.append(f"    Pontuacao: {a.score:.1f}")
        if a.recommendations:
            report.append("    Proximos passos:")
            for r in a.recommendations:
                report.append(f"      - {r}")
        report.append("")

    report.append("=" * 60)
    return "\n".join(report)


def main():
    print("Avaliacao de Maturidade DevSecOps")
    print("-" * 40)

    assessments = []
    for dimension, weight in DIMENSION_WEIGHTS.items():
        level = int(input(f"Nivel para '{dimension}' (0-5): "))
        assessments.append(assess_dimension(dimension, level))

    report = generate_report(assessments)
    print(report)


if __name__ == "__main__":
    main()
```

---

## 5. Ferramentas do Ecossistema DevSecOps

### 5.1 Mapa Completo de Ferramentas por Categoria

O ecossistema DevSecOps é vasto. A tabela a seguir organiza as principais ferramentas por categoria, incluindo suas características e casos de uso.

#### SAST (Static Application Security Testing)

| Ferramenta | Linguagens Suportadas | Licença | Integração CI/CD | Destaque |
|------------|----------------------|---------|-------------------|----------|
| **Semgrep** | 30+ (Python, JS, Go, Java, etc.) | OSS / Comercial | GitHub Actions, GitLab, Jenkins | Regras customizáveis, alto desempenho |
| **SonarQube** | 25+ | Community (OSS) / Enterprise | Jenkins, GitHub, GitLab | Quality gate integrado, dashboard completo |
| **CodeQL** | Java, C/C++, C#, JavaScript, Python, Go, Ruby | OSS | GitHub Actions nativo | Análise semântica profunda |
| **Bandit** | Python | OSS | Qualquer CI | Leve, focado em Python |
| **Brakeman** | Ruby on Rails | OSS | Qualquer CI | Especializado em Rails |
| **SpotBugs** | Java | OSS | Maven, Gradle, Jenkins | Sucessor do FindBugs |
| **Checkmarx** | 25+ | Comercial | Integrado com múltiplos CI | Enterprise, scans profundas |

**Exemplo: Semgrep com regras customizadas**

```yaml
# .semgrep.yml
rules:
  - id: hardcoded-password
    pattern: |
      $VAR = "..."
      ...
      $CONN = $VAR
    message: >
      Possivel senha hardcoded em codigo.
      Use variaveis de ambiente ou gerenciamento de segredos.
    languages: [python]
    severity: ERROR
    metadata:
      category: security
      cwe: "CWE-798"

  - id: sql-injection
    patterns:
      - pattern: |
          cursor.execute("..." + $VAR)
      - pattern: |
          cursor.execute(f"...{$VAR}")
    message: >
      Possivel SQL injection. Use parametros prepared.
    languages: [python]
    severity: ERROR

  - id: insecure-deserialization
    pattern: pickle.loads(...)
    message: >
      pickle.loads e inseguro. Use json ou msgpack.
    languages: [python]
    severity: WARNING
```

#### DAST (Dynamic Application Security Testing)

| Ferramenta | Tipo | Licença | Destaque |
|------------|------|---------|----------|
| **OWASP ZAP** | Scanner automatizado | OSS | Framework completo, API extensível |
| **Nikto** | Scanner web server | OSS | Testes de configuração de servidor |
| **Burp Suite** | Scanner + Proxy | Community (OSS) / Pro (Comercial) | Padrão da indústria para pentest |
| **Nuclei** | Scanner baseado em templates | OSS | 6000+ templates de vulnerabilidades |

**Exemplo: OWASP ZAP em pipeline CI/CD**

```yaml
# .github/workflows/dast-zap.yml
name: DAST with OWASP ZAP

on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]

jobs:
  dast-scan:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.10.0
        with:
          target: ${{ secrets.STAGING_URL }}
          rules_file_name: 'zap-rules.tsv'
          cmd_options: >-
            -a
            -j
            -l WARN
            -z "-config api.disablekey=true"

      - name: ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.8.0
        with:
          target: ${{ secrets.STAGING_URL }}
          cmd_options: >-
            -a
            -j
            -l WARN
            -t ${{ secrets.STAGING_URL }}
```

#### SCA (Software Composition Analysis)

| Ferramenta | Ecossistemas | Licença | Destaque |
|------------|-------------|---------|----------|
| **Snyk** | npm, pip, Maven, Go, NuGet, etc. | Free tier / Comercial | Database de vulnerabilidades proprietário |
| **Trivy** | Containers, filesystem, repos | OSS | Multi-target, rápido |
| **OWASP Dependency-Check** | Java, .NET, Ruby, Python, Node.js | OSS | Integração com NVD |
| **Dependabot** | GitHub ecosystem | OSS (GitHub) | Auto-PRs para updates |
| **Renovate** | Multi-ecosistema | OSS | Configurável, cross-platform |
| **osv-scanner** | Multi-ecosistema (Google OSV) | OSS | Database OSV, rápido |

**Exemplo: Snyk em pipeline**

{% raw %}
```yaml
# .github/workflows/sca-snyk.yml
name: SCA - Snyk

on: [push, pull_request]

jobs:
  snyk-sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Snyk Security Test
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: >-
            --all-projects
            --severity-threshold=high
            --sarif-file-output=snyk.sarif

      - name: Upload Snyk results to GitHub
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: snyk.sarif
```
{% endraw %}

**Exemplo: Trivy para SCA em filesystem**

```yaml
# .github/workflows/sca-trivy.yml
name: SCA - Trivy Filesystem

on: [push, pull_request]

jobs:
  trivy-sca:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Trivy filesystem scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'table'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          ignore-unfixed: true

      - name: Trivy SBOM generation
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'cyclonedx'
          output: 'sbom.json'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json
```

#### Secret Scanning

| Ferramenta | Método | Licença | Destaque |
|------------|--------|---------|----------|
| **GitLeaks** | Regex + Entropy | OSS | Rápido, integrável com pre-commit e CI |
| **TruffleHog** | Regex + Verified Scanning | OSS | Verificação ativa contra APIs |
| **GitHub Secret Scanning** | Patterns proprietários | Grátis (GitHub) | Integrado ao GitHub |
| **detect-secrets** (Yelp) | Regex + Entropy + Heurísticas | OSS | Plugin para pre-commit |

**Exemplo: GitLeaks com configuração avançada**

```toml
# gitleaks.toml
title = "Gitleaks Config"

[allowlist]
  description = "Global allowlist"
  paths = [
    '''vendor/''',
    '''node_modules/''',
    '''\.lock$''',
    '''go\.sum$''',
  ]
  regexes = [
    '''1234567890abcdefghijklmnopqrstuvwxyz''',
  ]

[[rules]]
  id = "aws-access-key"
  description = "AWS Access Key"
  regex = '''(?i)aws[_\s]*[_\s]*(?:ACCESS_KEY|AKIA)[\s:=]?[A-Z0-9]{16,20}'''
  tags = ["key", "AWS"]

[[rules]]
  id = "private-key"
  description = "Private Key"
  regex = '''-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'''
  tags = ["key", "Private"]

[[rules]]
  id = "generic-api-key"
  description = "Generic API Key"
  regex = '''(?i)(?:api[_\s]*key|apikey|api[_\s]*secret)[\s:=]?[A-Za-z0-9\-_]{20,50}'''
  tags = ["key", "Generic"]

[[rules]]
  id = "connection-string"
  description = "Database Connection String"
  regex = '''(?i)(?:mysql|postgres|mongodb|redis|amqp)://[^\s]+'''
  tags = ["database", "connection"]
```

**Exemplo: TruffleHog com verified scanning**

{% raw %}
```yaml
# .github/workflows/secret-scanning.yml
name: Secret Scanning

on: [push, pull_request]

jobs:
  trufflehog:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Histórico completo para scanning

      - name: TruffleHog Scan
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified
          path: ./
          base: ${{ github.event.repository.default_branch }}
```
{% endraw %}

#### Container Scanning

| Ferramenta | Alvo | Licença | Destaque |
|------------|------|---------|----------|
| **Trivy** | Imagens, filesystem, repos | OSS | Multi-target, SBOM integrado |
| **Grype** | Imagens container | OSS | Indexação rápida |
| **Snyk Container** | Imagens, IaC | Free tier / Comercial | Recomendações de fix |
| **Docker Scout** | Imagens Docker | Free tier / Comercial | Integrado ao Docker CLI |

**Exemplo: Trivy para scanning de imagem**

```yaml
# .github/workflows/container-scan.yml
name: Container Security Scan

on:
  push:
    branches: [main]
    paths:
      - 'Dockerfile'
      - 'docker-compose*.yml'

jobs:
  container-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
```

#### IaC (Infrastructure as Code) Scanning

| Ferramenta | IaC Suportado | Licença | Destaque |
|------------|--------------|---------|----------|
| **Checkov** | Terraform, CloudFormation, K8s, Dockerfile, etc. | OSS | 1000+ políticas |
| **tfsec** | Terraform | OSS (Checkov) | Focado em Terraform |
| **KICS** | Terraform, Ansible, Docker, K8s, etc. | OSS (Checkmarx) | Multi-IaC |
| **cfn-lint** | CloudFormation | OSS | Validação de templates AWS |
| **Prowler** | AWS, Azure, GCP | OSS | Auditoria de cloud |

**Exemplo: Checkov com políticas customizadas**

```yaml
# .github/workflows/iac-scan.yml
name: IaC Security Scan

on: [push, pull_request]

jobs:
  checkov:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Checkov Terraform Scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: terraform/
          framework: terraform
          output_format: cli,sarif
          output_file_path: console,checkov-results.sarif
          soft_fail: false
          skip_check: CKV_AWS_18  # Exemplo de skip específico

      - name: Checkov Dockerfile Scan
        uses: bridgecrewio/checkov-action@master
        with:
          file: Dockerfile
          framework: dockerfile

      - name: Checkov Kubernetes Scan
        uses: bridgecrewio/checkov-action@master
        with:
          directory: k8s/
          framework: kubernetes
```

#### License Scanning

| Ferramenta | Ecossistemas | Licença | Destaque |
|------------|-------------|---------|----------|
| **FOSSA** | Multi-ecosistema | Comercial / Free tier | Compliance automatizado |
| **pip-licenses** | Python | OSS | Simples e direto |
| **license-checker** | Node.js | OSS | Integração npm |
| **ScanCode** | Multi-ecosistema | OSS | Scan profundo de licenças |

### 5.2 Tabela Comparativa Geral

| Categoria | Ferramenta Principal | Open Source | Facilidade de Integração | Cobertura | Custo |
|-----------|---------------------|-------------|-------------------------|-----------|-------|
| SAST | Semgrep | Sim | Alta | Alta | Grátis |
| SAST | SonarQube Community | Sim | Média | Média-Alta | Grátis |
| SAST | CodeQL | Sim | Alta (GitHub) | Alta | Grátis (GitHub) |
| SCA | Snyk | Parcial | Alta | Alta | Freemium |
| SCA | Trivy | Sim | Alta | Média-Alta | Grátis |
| DAST | OWASP ZAP | Sim | Média | Alta | Grátis |
| Secrets | GitLeaks | Sim | Alta | Média | Grátis |
| Secrets | TruffleHog | Sim | Média | Alta | Grátis |
| Container | Trivy | Sim | Alta | Alta | Grátis |
| IaC | Checkov | Sim | Alta | Alta | Grátis |
| License | FOSSA | Parcial | Alta | Alta | Freemium |

### 5.3 Pontos de Integração no CI/CD

```text
Fluxo de Ferramentas DevSecOps no Pipeline:

  Developer Machine               CI/CD Pipeline                    Staging/Production
  +------------------+            +---------------------+           +------------------+
  |                  |            |                     |           |                  |
  | Pre-commit hooks | ---------> | Build               | ------->  | DAST (ZAP)       |
  | - GitLeaks       |            | - SAST (Semgrep)    |           | - Runtime scan   |
  | - Semgrep        |            | - SCA (Snyk/Trivy)  |           |                  |
  | - Bandit         |            | - Secret scanning   |           | Container scan   |
  | - Checkov        |            | - Unit tests sec    |           | - Trivy          |
  |                  |            |                     |           |                  |
  +------------------+            | Security Gate       |           | IaC scan         |
                                  | (fail if vulns)     |           | - Checkov        |
                                  +---------------------+           |                  |
                                                                    | Compliance scan  |
                                                                    +------------------+
```

---

## 6. Estudo de Caso: DevSecOps na Prática

### 6.1 Cenário ANTES: Pipeline Tradicional Inseguro

Vamos analisar um pipeline típico de uma empresa que usa DevOps mas não tem segurança integrada:

```yaml
# pipeline-before.yml — Pipeline INSEGURO (ANTES do DevSecOps)
name: CI/CD Pipeline (Inseguro)

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/

      - name: Build Docker image
        run: docker build -t myapp:${{ github.sha }} .

      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker tag myapp:${{ github.sha }} myregistry.com/myapp:${{ github.sha }}
          docker push myregistry.com/myapp:${{ github.sha }}

      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp myapp=myregistry.com/myapp:${{ github.sha }}
```

**Problemas identificados neste pipeline:**

1. **Sem SAST**: Não verifica vulnerabilidades no código
2. **Sem SCA**: Não verifica CVEs em dependências
3. **Sem Secret Scanning**: Segredos podem ser commitados
4. **Sem Container Scanning**: Imagem pode ter vulnerabilidades
5. **Sem IaC Scanning**: Configurações Kubernetes inseguras
6. **Sem DAST**: Não testa a aplicação em runtime
7. **Sem Security Gate**: Nenhuma verificação bloqueia o deploy
8. **Docker login hardcoded**: Senha pode vazar nos logs

### 6.2 Cenário DEPOIS: Pipeline DevSecOps com Security Gates

```yaml
# pipeline-after.yml — Pipeline SEGURO (DEPOIS do DevSecOps)
name: DevSecOps Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  # ============================================
  # CAMADA 1: Análise Estática (SAST)
  # ============================================
  sast:
    name: "SAST - Analise Estatica"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Semgrep SAST
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/owasp-top-ten
            p/python
            p/secrets
            p/security-audit
          generateSarif: true
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: semgrep.sarif

  # ============================================
  # CAMADA 2: Secret Scanning
  # ============================================
  secrets:
    name: "Secrets - Deteccao de Segredos"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  # ============================================
  # CAMADA 3: Análise de Composição (SCA)
  # ============================================
  sca:
    name: "SCA - Analise de Composicao"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: OWASP Dependency-Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          path: '.'
          format: 'HTML'
          fail_on_cvss: 7

      - name: Snyk SCA
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --sarif-file-output=snyk.sarif

      - name: Upload Snyk SARIF
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: snyk.sarif

  # ============================================
  # CAMADA 4: IaC Scanning
  # ============================================
  iac:
    name: "IaC - Infraestrutura como Codigo"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Checkov Terraform
        uses: bridgecrewio/checkov-action@master
        with:
          directory: terraform/
          framework: terraform
          soft_fail: false

      - name: Checkov Dockerfile
        uses: bridgecrewio/checkov-action@master
        with:
          file: Dockerfile
          framework: dockerfile

      - name: Checkov Kubernetes
        uses: bridgecrewio/checkov-action@master
        with:
          directory: k8s/
          framework: kubernetes

  # ============================================
  # CAMADA 5: Testes e Build
  # ============================================
  build:
    name: "Build e Testes"
    runs-on: ubuntu-latest
    needs: [sast, secrets, sca, iac]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Run unit tests
        run: pytest tests/ --cov=src --cov-report=xml

      - name: Security unit tests
        run: pytest tests/security/ -v

      - name: Build Docker image
        run: |
          docker build \
            --label "git.commit=${{ github.sha }}" \
            --label "git.branch=${{ github.ref_name }}" \
            -t myapp:${{ github.sha }} .

  # ============================================
  # CAMADA 6: Container Scanning
  # ============================================
  container-scan:
    name: "Container - Escaneamento de Imagem"
    runs-on: ubuntu-latest
    needs: [build]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build image for scanning
        run: docker build -t myapp:${{ github.sha }} .

      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'

      - name: Trivy SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'myapp:${{ github.sha }}'
          format: 'cyclonedx'
          output: 'sbom.json'

      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.json

  # ============================================
  # CAMADA 7: Deploy (com todas as verificações)
  # ============================================
  deploy-staging:
    name: "Deploy - Staging"
    runs-on: ubuntu-latest
    needs: [sast, secrets, sca, iac, build, container-scan]
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy to staging
        run: |
          kubectl set image deployment/myapp \
            myapp=myregistry.com/myapp:${{ github.sha }} \
            --namespace=staging

  # ============================================
  # CAMADA 8: DAST (após deploy em staging)
  # ============================================
  dast:
    name: "DAST - Teste Dinamico"
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    steps:
      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.10.0
        with:
          target: ${{ secrets.STAGING_URL }}
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a -j'

  # ============================================
  # CAMADA 9: Deploy em Produção (após DAST)
  # ============================================
  deploy-production:
    name: "Deploy - Producao"
    runs-on: ubuntu-latest
    needs: [dast]
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp \
            myapp=myregistry.com/myapp:${{ github.sha }} \
            --namespace=production
```

### 6.3 Análise: O que Cada Ferramenta Captura

```text
Comparação de cobertura: ANTES vs DEPOIS

Categoria          | ANTES (Pipeline Inseguro) | DEPOIS (DevSecOps)
-------------------|---------------------------|-------------------
SAST               | Nenhuma verificacao       | Semgrep (OWASP Top 10)
Secret Scanning    | Nenhuma verificacao       | GitLeaks + Semgrep
SCA                | Nenhuma verificacao       | Snyk + OWASP Dep-Check
Container Scanning | Nenhuma verificacao       | Trivy (vuln + SBOM)
IaC Scanning       | Nenhuma verificacao       | Checkov (Terraform, K8s, Docker)
DAST               | Nenhuma verificacao       | OWASP ZAP
Unit Tests Sec     | Nenhuma verificacao       | pytest security tests
Security Gate      | Nao existe                | Bloqueia se vulns encontradas
SBOM               | Nao existe                | Gerado em cada build
Compliance         | Manual                    | Automatizado
Deploy Seguro      | Direto para producao      | Staging -> DAST -> Producao
```

**Vulnerabilidades que cada ferramenta teria capturado:**

| Vulnerabilidade | SAST | SCA | Secrets | Container | IaC | DAST |
|----------------|------|-----|---------|-----------|-----|------|
| SQL Injection | X | - | - | - | - | X |
| XSS Reflected | X | - | - | - | - | X |
| CVE em dependência | - | X | - | - | - | - |
| API key hardcoded | - | - | X | - | - | - |
| Container sem non-root | - | - | - | X | - | - |
| Terraform com S3 público | - | - | - | - | X | - |
| SQL Injection em runtime | - | - | - | - | - | X |
| Deserialization RCE | X | - | - | - | - | X |
| Biblioteca com CVE | - | X | - | - | - | - |
| K8s com hostNetwork | - | - | - | - | X | - |

---

## 7. Métricas de DevSecOps

### 7.1 Métricas Principais

DevSecOps exige métricas para medir eficácia. As principais métricas são:

**MTTR (Mean Time to Remediate)**

Tempo médio desde a detecção de uma vulnerabilidade até sua correção completa.

```python
#!/usr/bin/env python3
"""Calcula MTTR de vulnerabilidades."""
from datetime import datetime


def calculate_mttr(vulnerabilities: list[dict]) -> float:
    """
    Calcula o tempo medio de remediacao.

    Cada vulnerabilidade deve ter:
    - detected_at: datetime da deteccao
    - remediated_at: datetime da correcao (ou None se aberta)
    """
    remediation_times = []

    for vuln in vulnerabilities:
        if vuln["remediated_at"] is not None:
            delta = vuln["remediated_at"] - vuln["detected_at"]
            remediation_times.append(delta.total_seconds() / 3600)  # horas

    if not remediation_times:
        return float("inf")

    return sum(remediation_times) / len(remediation_times)


# Exemplo de uso
vulns = [
    {
        "cve": "CVE-2024-0001",
        "detected_at": datetime(2024, 1, 15, 10, 0),
        "remediated_at": datetime(2024, 1, 16, 14, 0),  # 28 horas
    },
    {
        "cve": "CVE-2024-0002",
        "detected_at": datetime(2024, 1, 16, 8, 0),
        "remediated_at": datetime(2024, 1, 16, 12, 0),  # 4 horas
    },
    {
        "cve": "CVE-2024-0003",
        "detected_at": datetime(2024, 1, 17, 9, 0),
        "remediated_at": datetime(2024, 1, 20, 10, 0),  # 73 horas
    },
]

mttr = calculate_mttr(vulns)
print(f"MTTR: {mttr:.1f} horas")
# MTTR: 35.0 horas
```

**Vulnerability Detection Time (VDT)**

Tempo desde a introdução de uma vulnerabilidade até sua detecção.

```python
def calculate_vdt(introduced_at: datetime, detected_at: datetime) -> float:
    """Tempo de deteccao em horas."""
    delta = detected_at - introduced_at
    return delta.total_seconds() / 3600
```

**Vulnerability Fix Rate (VFR)**

Porcentagem de vulnerabilidades corrigidas dentro do SLA.

```python
def calculate_vfr(vulnerabilities: list[dict], sla_hours: int = 24) -> float:
    """
    Taxa de correcao dentro do SLA.
    100% = todas as vulnerabilidades corrigidas dentro do SLA.
    """
    fixed_within_sla = 0
    total = len(vulnerabilities)

    for vuln in vulnerabilities:
        if vuln["remediated_at"] is not None:
            delta = vuln["remediated_at"] - vuln["detected_at"]
            if delta.total_seconds() / 3600 <= sla_hours:
                fixed_within_sla += 1

    return (fixed_within_sla / total * 100) if total > 0 else 0
```

**Outras métricas importantes:**

| Métrica | Fórmula | Meta Recomendada |
|---------|---------|-----------------|
| **MTTR** | Tempo médio de remediacao | < 24h (Critical), < 72h (High) |
| **VDT** | Tempo medio de deteccao | < 1 commit (shift-left) |
| **VFR** | % corrigidas dentro do SLA | > 95% |
| **Security Coverage** | % de repos com SAST+SCA | > 95% |
| **False Positive Rate** | FPs / Total findings | < 10% |
| **Security Debt** | Total de vulns nao corrigidas | Tendencia decrescente |
| **Pipeline Security Time** | Tempo total de scans no CI | < 10 min |
| **Deployment Frequency** | Deploys por dia (com seguranca) | > 1 por dia |

### 7.2 Dashboard de Métricas

```python
#!/usr/bin/env python3
"""
Gera dashboard de metricas DevSecOps em formato Markdown.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class SecurityMetrics:
    total_vulnerabilities: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    remediated_within_sla: int = 0
    total_remediated: int = 0
    mttr_hours: float = 0.0
    repos_with_security: int = 0
    total_repos: int = 0
    scans_today: int = 0
    deploys_today: int = 0
    blocked_deploys: int = 0


def generate_dashboard(metrics: SecurityMetrics) -> str:
    """Gera dashboard completo em Markdown."""
    sla_rate = (
        (metrics.remediated_within_sla / metrics.total_remediated * 100)
        if metrics.total_remediated > 0
        else 0
    )
    coverage = (
        (metrics.repos_with_security / metrics.total_repos * 100)
        if metrics.total_repos > 0
        else 0
    )
    block_rate = (
        (metrics.blocked_deploys / metrics.deploys_today * 100)
        if metrics.deploys_today > 0
        else 0
    )

    dashboard = f"""
# Dashboard DevSecOps
**Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Resumo de Vulnerabilidades

| Severidade | Quantidade | Status |
|-----------|-----------|--------|
| Critica   | {metrics.critical}  | {'ALERTA' if metrics.critical > 0 else 'OK'} |
| Alta      | {metrics.high}      | {'ALERTA' if metrics.high > 0 else 'OK'} |
| Media     | {metrics.medium}    | {'ATENCAO' if metrics.medium > 10 else 'OK'} |
| Baixa     | {metrics.low}       | OK |
| **Total** | **{metrics.total_vulnerabilities}** | |

## Metricas de Eficacia

| Metrica | Valor | Meta | Status |
|---------|-------|------|--------|
| MTTR (Critical) | {metrics.mttr_hours:.1f}h | < 24h | {'OK' if metrics.mttr_hours < 24 else 'FALHA'} |
| Taxa de SLA | {sla_rate:.1f}% | > 95% | {'OK' if sla_rate > 95 else 'FALHA'} |
| Cobertura Security | {coverage:.1f}% | > 95% | {'OK' if coverage > 95 else 'FALHA'} |
| Deploys Bloqueados | {metrics.blocked_deploys} ({block_rate:.1f}%) | Monitorar | INFO |
| Scans Hoje | {metrics.scans_today} | - | INFO |

## Status de Cobertura

```
Repositorios com DevSecOps: {metrics.repos_with_security}/{metrics.total_repos}
[{'#' * int(coverage // 5)}{'.' * (20 - int(coverage // 5))}] {coverage:.1f}%
```

## Acoes Recomendadas

{'- [ ] URGENTE: Corrigir vulnerabilidades criticas pendentes' if metrics.critical > 0 else ''}
{'- [ ] Corrigir vulnerabilidades altas pendentes' if metrics.high > 0 else ''}
{'- [ ] Aumentar cobertura de security scanning' if coverage < 95 else ''}
{'- [ ] Reduzir MTTR abaixo de 24h' if metrics.mttr_hours >= 24 else ''}
"""
    return dashboard


# Exemplo de uso
metrics = SecurityMetrics(
    total_vulnerabilities=47,
    critical=2,
    high=8,
    medium=15,
    low=22,
    remediated_within_sla=40,
    total_remediated=42,
    mttr_hours=18.5,
    repos_with_security=18,
    total_repos=20,
    scans_today=156,
    deploys_today=23,
    blocked_deploys=3,
)

print(generate_dashboard(metrics))
```

### 7.3 KPIs para Segurança em Pipelines

```text
Framework de KPIs DevSecOps:

NIVEL 1 (Operacional):
  - Numero de scans executados por dia
  - Tempo medio de scan por ferramenta
  - Taxa de sucesso dos scans
  - Numero de falsos positivos

NIVEL 2 (Tatico):
  - MTTR por severidade
  - Taxa de correcao dentro do SLA
  - Numero de vulnerabilidades por build
  - Cobertura de repos com security scanning

NIVEL 3 (Estrategico):
  - Custo por vulnerabilidade corrigida
  - ROI de DevSecOps
  - Reducao de incidentes de seguranca
  - Tempo medio de deteccao (VDT)
  - Compliance score automatizado
```

```yaml
# Exemplo: Workflow que coleta métricas automaticamente
name: Security Metrics Collection

on:
  schedule:
    - cron: '0 0 * * *'  # Diário à meia-noite
  workflow_dispatch:

jobs:
  collect-metrics:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Collect security metrics
        run: |
          python3 scripts/collect_metrics.py \
            --output metrics.json

      - name: Generate dashboard
        run: |
          python3 scripts/generate_dashboard.py \
            --input metrics.json \
            --output dashboard.md

      - name: Upload metrics to monitoring
        run: |
          curl -X POST "${{ secrets.METRICS_ENDPOINT }}" \
            -H "Authorization: Bearer ${{ secrets.METRICS_TOKEN }}" \
            -H "Content-Type: application/json" \
            -d @metrics.json

      - name: Create GitHub Pages dashboard
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs
```

---

## 8. Referências

### 8.1 Livros e Publicações

1. **"DevSecOps: A Practical Guide"** — Birgitta Böckeler,Thoughtworks. Guia prático de implementação de DevSecOps em organizações reais.

2. **"The Phoenix Project"** — Gene Kim, Kevin Behr, George Spafford. O livro que popularizou DevOps e que toda equipe deve ler.

3. **"Accelerate: The Science of Lean Software and DevOps"** — Nicole Forsgren, Jez Humble, Gene Kim. Dados sobre como práticas de DevOps (incluindo segurança) impactam performance organizacional.

4. **"OWASP DevSecOps Guideline"** — OWASP Foundation. Guia abrangente de práticas de segurança em DevSecOps. Disponível em: https://owasp.org/www-project-devsecops-guideline/

5. **"NIST SP 800-204C"** — Security Strategies for Microservices. Framework do governo dos EUA para segurança em arquiteturas modernas.

6. **"DORA State of DevOps Report"** — Google Cloud / DORA. Relatório anual que mede o impacto de DevOps e segurança na performance.

### 8.2 Ferramentas e Frameworks

| Recurso | URL |
|---------|-----|
| Semgrep | https://semgrep.dev |
| SonarQube | https://www.sonarqube.org |
| CodeQL | https://codeql.github.com |
| OWASP ZAP | https://www.zaproxy.org |
| Snyk | https://snyk.io |
| Trivy | https://trivy.dev |
| GitLeaks | https://gitleaks.io |
| TruffleHog | https://github.com/trufflesecurity/trufflehog |
| Checkov | https://www.checkov.io |
| OWASP Dependency-Check | https://owasp.org/www-project-dependency-check/ |
| FOSSA | https://fossa.com |
| OSV Scanner | https://osv.dev |

### 8.3 Padrões e Normas

- **OWASP Top 10** (2021) — Lista das 10 vulnerabilidades web mais críticas.
- **OWASP ASVS** (Application Security Verification Standard) — Padrão para verificação de segurança de aplicações.
- **CIS Benchmarks** — Benchmarks de configuração segura para sistemas e cloud.
- **NIST Cybersecurity Framework** — Framework de segurança cibernética do governo dos EUA.
- **ISO 27001/27002** — Padrões internacionais de gestão de segurança da informação.
- **SLSA Framework** (Supply-chain Levels for Software Artifacts) — Framework de segurança da cadeia de suprimentos de software.

### 8.4 Comunidades e Eventos

- **OWASP (Open Worldwide Application Security Project)** — Organização líder em segurança de aplicações open source.
- **DevSecCon** — Conferência global dedicada a DevSecOps.
- **Black Hat / DEF CON** — Eventos de segurança com tracks específicos para DevSecOps.
- **KubeCon + CloudNativeCon** — Evento de cloud native com forte presença de segurança.

### 8.5 Próximos Capítulos

No próximo capítulo, abordaremos **Fundamentos de Segurança no Código**, incluindo:
- OWASP Top 10 na prática
- Vulnerabilidades mais comuns em aplicações web
- Padrões de código seguro em Python, JavaScript e Go
- Exercícios práticos com vulnerabilidades intencionais (DVWA, WebGoat)

---

*Fim do Capítulo 1 — Introdução ao DevSecOps*
---

*[Capítulo anterior: 00 — Prefacio](00-prefacio.md)*
*[Próximo capítulo: 02 — Fundamentos Devops E Seguranca](02-fundamentos-devops-e-seguranca.md)*
