---
layout: default
title: "15-devsecops-web"
---

# Capítulo 15: DevSecOps para Aplicações Web

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

- Compreender os princípios fundamentais de DevSecOps aplicados ao desenvolvimento web moderno
- Implementar security gates eficazes em pipelines de CI/CD para aplicações web
- Configurar ferramentas de SAST (Static Application Security Testing) para JavaScript e TypeScript
- Utilizar ferramentas de DAST (Dynamic Application Security Testing) como OWASP ZAP e Nuclei
- Implementar análise de composição de software (SCA) para gerenciar vulnerabilidades em dependências
- Configurar detecção de secrets em repositórios usando gitleaks e truffleHog
- Aplicar varredura de segurança em infraestrutura como código (IaC)
- Implementar varredura de containers em pipelines de integração contínua
- Configurar monitoramento de segurança com WAF, RASP e detecção de bots
- Estabelecer processos de resposta a incidentes para aplicações web
- Construir pipelines completas de segurança usando GitHub Actions e GitLab CI

---

## 1. Security Gates in CI/CD for Web Apps

### 1.1 O Conceito de Security Gates

Security gates são pontos de verificação obrigatórios em uma pipeline de CI/CD que validam se o código atende a critérios mínimos de segurança antes de avançar para a próxima etapa. O objetivo é detectar vulnerabilidades precocemente no ciclo de desenvolvimento, quando o custo de correção é significativamente menor.

A filosofia DevSecOps transforma a segurança de uma atividade final (período) em uma responsabilidade contínua distribuída ao longo de todo o ciclo de vida do desenvolvimento. Em vez de realizar auditorias de segurança apenas antes do lançamento, as verificações são incorporadas diretamente nos processos de desenvolvimento.

### 1.2 Tipos de Security Gates

**Pre-commit hooks**: Executados antes que o código seja comprometido no repositório local. São a primeira linha de defesa e impedem que código vulnerável entre no fluxo de trabalho.

**Commit hooks**: Executados durante o processo de commit. Validam mensagens de commit, estrutura do código e verificam a presença de padrões inseguros.

**Pull request gates**: Executados quando um pull request é criado ou atualizado. Realizam análises mais completas, incluindo SAST, SCA e detecção de secrets.

**Merge gates**: Bloqueiam a fusão de branches se as verificações de segurança falharem. Garantem que apenas código que atende aos padrões de segurança seja integrado ao branch principal.

**Deploy gates**: Última verificação antes da implantação em produção. Validam configurações de segurança, certificados e variáveis de ambiente sensíveis.

### 1.3 Pipeline de Segurança em Camadas

Uma pipeline de segurança eficaz deve operar em múltiplas camadas:

**Camada 1 - Desenvolvimento Local**: Hooks pré-commit que executam linting de segurança, detecção de secrets básicos e formatação de código. Essa camada fornece feedback imediato ao desenvolvedor.

**Camada 2 - Build e Teste**: Análises SAST, verificação de dependências (SCA), testes de unidade com foco em segurança e detecção de secrets avançada. Essa camada é executada em cada push ou pull request.

**Camada 3 - Integração**: Análises DAST em ambientes de staging, varredura de containers, verificação de infraestrutura como código e testes de penetrção automatizados.

**Camada 4 - Pré-deploy**: Validação de configurações de segurança em produção, verificação de certificados TLS, validação de headers de segurança HTTP e auditoria final de permissões.

### 1.4 Métricas de Segurança

Para medir a eficácia dos security gates, é necessário acompanhar métricas relevantes:

**Mean Time to Detect (MTTD)**: Tempo médio entre a introdução de uma vulnerabilidade e sua detecção. Um MTTD baixo indica que os gates estão funcionando efetivamente.

**Mean Time to Remediate (MTTR)**: Tempo médio entre a detecção e a correção de uma vulnerabilidade. Métricas altas podem indicar processos ineficientes de correção.

**Security Debt**: Quantidade total de vulnerabilidades conhecidas que não foram corrigidas. Deve ser monitorada e reduzida continuamente.

**Coverage de Security Gates**: Porcentagem de repositórios e pipelines que possuem security gates implementados. Meta ideal: 100% dos repositórios ativos.

### 1.5 Práticas Recomendadas

**Fail Fast**: Configurar os gates mais rápidos (linting, detecção de secrets) para executarem primeiro. Se falharem, não há necessidade de executar análises mais custosas.

**Feedback Loop Curto**: Fornecer feedback de segurança claro e acionável aos desenvolvedores. Incluir links para documentação, exemplos de correção e contexto sobre por que a verificação falhou.

**Exceções Documentadas**: Quando uma exceção for necessária, documentar formalmente o motivo, o risco aceito e a data de revisão. Exceções não devem ser permanentes.

**Baseline de Segurança**: Manter uma linha de base de vulnerabilidades conhecidas. Novas vulnerabilidades devem ser tratadas como prioridade, enquanto existentes devem ter um plano de remediação.

---

## 2. SAST for JavaScript/TypeScript

### 2.1 ESLint Security Plugins

ESLint é a ferramenta de linting padrão para projetos JavaScript e TypeScript. Vários plugins adicionam verificações de segurança específicas.

**eslint-plugin-security**: Oferece regras para detectar padrões inseguros comuns em código JavaScript.

**eslint-plugin-no-unsanitized**: Detecta uso inseguro de innerHTML, outerHTML e outras propriedades que podem levar a XSS.

**eslint-plugin-react-security**: Foca em vulnerabilidades específicas de aplicações React.

**eslint-plugin-typescript-security**: Adapta regras de segurança para código TypeScript.

### 2.2 Configuração do eslint-plugin-security

```javascript
// .eslintrc.js
module.exports = {
  plugins: ['security'],
  extends: [
    'eslint:recommended',
    'plugin:security/recommended-legacy',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
  ],
  rules: {
    'security/detect-object-injection': 'error',
    'security/detect-non-literal-regexp': 'warn',
    'security/detect-unsafe-regex': 'error',
    'security/detect-buffer-noassert': 'error',
    'security/detect-eval-with-expression': 'error',
    'security/detect-no-csrf-before-method-override': 'error',
    'security/detect-possible-timing-attacks': 'warn',
    'security/detect-sql-injection': 'error',
    'security/detect-non-literal-fs-filename': 'warn',
    'security/detect-non-literal-http-callback': 'warn',
    'security/detect-unsafe-regexp': 'error',
    'security/detect-eval': 'error',
    'security/detect-immediately-invoked-function-expression': 'error',
    'security/detect-unclear-string-concatenation': 'warn',
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
    project: './tsconfig.json',
  },
  env: {
    node: true,
    es2021: true,
  },
};
```

### 2.3 Regras de Segurança Customizadas para ESLint

É possível criar regras customizadas para detectar padrões específicos do seu projeto:

```javascript
// eslint-rules/detect-hardcoded-secrets.js
module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Detect hardcoded API keys and secrets',
      category: 'Security',
      recommended: true,
    },
    schema: [],
  },
  create(context) {
    const secretPatterns = [
      { pattern: /api[_-]?key\s*[=:]\s*['"][A-Za-z0-9]{20,}['"]/i, name: 'API Key' },
      { pattern: /secret[_-]?key\s*[=:]\s*['"][A-Za-z0-9]{20,}['"]/i, name: 'Secret Key' },
      { pattern: /password\s*[=:]\s*['"][^'"]{8,}['"]/i, name: 'Password' },
      { pattern: /token\s*[=:]\s*['"][A-Za-z0-9\-._]{20,}['"]/i, name: 'Token' },
      { pattern: /aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*['"]AK[A-Z0-9]{16}['"]/i, name: 'AWS Access Key' },
      { pattern: /private[_-]?key\s*[=:]\s*['"]-----BEGIN/gi, name: 'Private Key' },
    ];

    return {
      Literal(node) {
        if (typeof node.value !== 'string') return;

        for (const { pattern, name } of secretPatterns) {
          const fullText = context.getSourceCode().getText(node.parent);
          if (pattern.test(fullText)) {
            context.report({
              node,
              message: `Potential hardcoded ${name} detected. Use environment variables or a secrets manager instead.`,
            });
            break;
          }
        }
      },
    };
  },
};
```

### 2.4 Semgrep para JavaScript/TypeScript

Semgrep é uma ferramenta de análise estática de código que suporta múltiplas linguagens e oferece regras de segurança específicas para JavaScript e TypeScript.

**Configuração básica do Semgrep:**

```yaml
# .semgrep.yml
rules:
  - id: react-dangerouslySetInnerHTML
    pattern: |
      <$EL dangerouslySetInnerHTML=... />
    message: |
      Using dangerouslySetInnerHTML can lead to XSS vulnerabilities.
      Use a sanitization library like DOMPurify instead.
    languages: [typescript, javascript]
    severity: ERROR
    metadata:
      category: security
      technology: [react]
      cwe: ['CWE-79: Improper Neutralization of Input During Web Page Generation']

  - id: nodejs-sql-injection
    patterns:
      - pattern: |
          $QUERY = "..." + $REQ.body.$FIELD + "..."
          $DB.query($QUERY, ...)
      - pattern: |
          $QUERY = `...${$REQ.body.$FIELD}...`
          $DB.query($QUERY, ...)
    message: |
      Possible SQL injection via string concatenation or template literals.
      Use parameterized queries or an ORM instead.
    languages: [typescript, javascript]
    severity: ERROR
    metadata:
      category: security
      cwe: ['CWE-89: Improper Neutralization of Special Elements used in an SQL Command']

  - id: nodejs-eval-usage
    pattern: eval(...)
    message: |
      Use of eval() is dangerous and can lead to code injection attacks.
      Avoid eval() entirely or use Function constructor with input validation.
    languages: [typescript, javascript]
    severity: ERROR
    metadata:
      category: security
      cwe: ['CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code']

  - id: typescript-unsafe-deserialization
    patterns:
      - pattern: JSON.parse($DATA)
      - pattern-not: |
          JSON.parse($DATA, ...)
    message: |
      Parsing untrusted JSON data can lead to prototype pollution attacks.
      Consider using a schema validation library like ajv or zod.
    languages: [typescript, javascript]
    severity: WARNING
    metadata:
      category: security
      cwe: ['CWE-1321: Improperly Controlled Modification of Object Prototype Attributes']

  - id: express-no-helmet
    patterns:
      - pattern: |
          const $APP = express();
          $APP.listen(...)
      - pattern-not-inside: |
          $APP.use(helmet(...));
          ...
          $APP.listen(...)
    message: |
      Express application without Helmet middleware for security headers.
      Add helmet() middleware to set secure HTTP headers.
    languages: [typescript, javascript]
    severity: WARNING
    metadata:
      category: security
      technology: [express]

  - id: unsafe-regex-pattern
    pattern: new RegExp(...)
    message: |
      Dynamic regex construction can lead to ReDoS (Regular Expression Denial of Service).
      Validate and test regex patterns for catastrophic backtracking.
    languages: [typescript, javascript]
    severity: WARNING
    metadata:
      category: security
      cwe: ['CWE-1333: Inefficient Regular Expression Complexity']

  - id: insecure-random-number
    patterns:
      - pattern: Math.random()
    message: |
      Math.random() is not cryptographically secure.
      Use crypto.randomBytes() or crypto.randomUUID() for security-sensitive randomness.
    languages: [typescript, javascript]
    severity: WARNING
    metadata:
      category: security
      cwe: ['CWE-330: Use of Insufficiently Random Values']

  - id: open-redirect-vulnerability
    patterns:
      - pattern: |
          res.redirect($REQ.query.$PARAM)
      - pattern: |
          res.redirect($REQ.body.$PARAM)
    message: |
      Unvalidated redirect based on user input can lead to open redirect attacks.
      Validate the redirect URL against a whitelist of allowed domains.
    languages: [typescript, javascript]
    severity: ERROR
    metadata:
      category: security
      cwe: ['CWE-601: URL Redirection to Untrusted Site']
```

### 2.5 Integração com VS Code

Para fornecer feedback em tempo real aos desenvolvedores, é possível integrar Semgrep diretamente no VS Code:

```json
// .vscode/settings.json
{
  "semgrep.path": "/usr/local/bin/semgrep",
  "semgrep.severity": ["ERROR", "WARNING"],
  "semgrep.autoEnable": true,
  "semgrep.rules": [
    "p/default",
    "p/javascript",
    "p/typescript",
    "p/nodejs",
    "p/express",
    "p/react",
    "p/owasp-top-ten"
  ],
  "editor.codeActionsOnSave": {
    "source.fixAll.semgrep": true
  }
}
```

### 2.6 Executando Semgrep em CI/CD

```yaml
# Exemplo de integração Semgrep no GitHub Actions
name: Semgrep SAST

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  semgrep:
    name: Security Analysis (Semgrep)
    runs-on: ubuntu-latest
    container:
      image: semgrep/semgrep

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Semgrep
        run: semgrep scan --config=auto --json --output=semgrep-results.json
        env:
          SEMGREP_RULES: >-
            p/default
            p/javascript
            p/typescript
            p/nodejs
            p/express
            p/owasp-top-ten

      - name: Upload Semgrep results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: semgrep-results
          path: semgrep-results.json

      - name: Check for critical findings
        run: |
          CRITICAL_COUNT=$(cat semgrep-results.json | jq '[.results[] | select(.extra.severity == "ERROR")] | length')
          if [ "$CRITICAL_COUNT" -gt 0 ]; then
            echo "Found $CRITICAL_COUNT critical security findings"
            cat semgrep-results.json | jq '.results[] | select(.extra.severity == "ERROR") | {rule_id, message, path, start_line}'
            exit 1
          fi
          echo "No critical security findings"
```

---

## 3. DAST for Web Apps

### 3.1 OWASP ZAP (Zed Attack Proxy)

OWASP ZAP é uma das ferramentas de DAST mais populares e completas para testes de segurança de aplicações web. Ela funciona como um proxy intermediário que intercepta e analisa o tráfego HTTP/HTTPS.

**Instalação e configuração:**

```bash
# Instalação do ZAP via Docker
docker pull ghcr.io/zaproxy/zaproxy:stable

# Executando o ZAP baseline scan
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py \
  -t https://your-application.com \
  -r zap-report.html \
  -J zap-report.json \
  -x zap-report.xml

# Executando o ZAP full scan
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-full-scan.py \
  -t https://your-application.com \
  -r zap-full-report.html \
  -J zap-full-report.json \
  -a

# Executando o ZAP API scan
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py \
  -t https://your-application.com/openapi.json \
  -f openapi \
  -r zap-api-report.html \
  -J zap-api-report.json
```

**Configuração do ZAP para CI/CD:**

```yaml
# .zap/rules.tsv - Personalização de regras
# Formato: Rule ID    Action    Strength    Threshold
# Rule IDs podem ser encontrados na documentação do ZAP
40012	IGNORE	High	Low	# Cross Site Scripting (Reflected)
40014	IGNORE	High	Low	# Cross Site Scripting (Persistent)
40016	IGNORE	High	Low	# Cross Site Scripting (DOM Based)
90033	IGNORE	High	Low	# Loosely Scoped Cookie
10054	IGNORE	High	Low	# Cookie Without SameSite Attribute
10055	IGNORE	High	Low	# CSP
```

**Script de automação ZAP:**

```python
#!/usr/bin/env python3
"""
ZAP Automated Scan Script
Executes ZAP scans with custom configurations for CI/CD integration.
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


class ZAPScanner:
    """Wrapper for OWASP ZAP scanner with CI/CD integration."""

    def __init__(self, target_url: str, config_path: Optional[str] = None):
        self.target_url = target_url
        self.config_path = config_path
        self.results_dir = Path("zap-results")
        self.results_dir.mkdir(exist_ok=True)

    def run_baseline_scan(self) -> Dict:
        """Run ZAP baseline scan (quick, passive only)."""
        output_file = self.results_dir / "baseline-report"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.results_dir.absolute()}:/zap/wrk/",
            "ghcr.io/zaproxy/zaproxy:stable",
            "zap-baseline.py",
            "-t", self.target_url,
            "-r", f"{output_file.name}.html",
            "-J", f"{output_file.name}.json",
            "-l", "WARN",
        ]

        if self.config_path:
            cmd.extend(["-c", self.config_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        return self._parse_results(output_file, result.returncode)

    def run_full_scan(self) -> Dict:
        """Run ZAP full scan (comprehensive, active and passive)."""
        output_file = self.results_dir / "full-report"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.results_dir.absolute()}:/zap/wrk/",
            "ghcr.io/zaproxy/zaproxy:stable",
            "zap-full-scan.py",
            "-t", self.target_url,
            "-r", f"{output_file.name}.html",
            "-J", f"{output_file.name}.json",
            "-a",
        ]

        if self.config_path:
            cmd.extend(["-c", self.config_path])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        return self._parse_results(output_file, result.returncode)

    def run_api_scan(self, spec_url: str, spec_format: str = "openapi") -> Dict:
        """Run ZAP API scan against an API specification."""
        output_file = self.results_dir / "api-report"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.results_dir.absolute()}:/zap/wrk/",
            "ghcr.io/zaproxy/zaproxy:stable",
            "zap-api-scan.py",
            "-t", spec_url,
            "-f", spec_format,
            "-r", f"{output_file.name}.html",
            "-J", f"{output_file.name}.json",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        return self._parse_results(output_file, result.returncode)

    def _parse_results(self, output_file: Path, return_code: int) -> Dict:
        """Parse ZAP scan results from JSON output."""
        json_file = output_file.with_suffix(".json")

        findings = {
            "target": self.target_url,
            "scan_type": "unknown",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "return_code": return_code,
            "summary": {
                "high": 0,
                "medium": 0,
                "low": 0,
                "informational": 0,
            },
            "alerts": [],
        }

        if json_file.exists():
            with open(json_file, "r") as f:
                raw_data = json.load(f)

            for site in raw_data.get("site", []):
                for alert in site.get("alerts", []):
                    risk = int(alert.get("riskdesc", "0")[0])
                    finding = {
                        "rule_id": alert.get("pluginId"),
                        "name": alert.get("name"),
                        "risk_level": self._risk_to_string(risk),
                        "description": alert.get("desc", ""),
                        "solution": alert.get("solution", ""),
                        "reference": alert.get("reference", ""),
                        "cwe_id": alert.get("cweid"),
                        "wasc_id": alert.get("wascid"),
                        "count": int(alert.get("count", 1)),
                    }
                    findings["alerts"].append(finding)

                    if risk >= 3:
                        findings["summary"]["high"] += 1
                    elif risk == 2:
                        findings["summary"]["medium"] += 1
                    elif risk == 1:
                        findings["summary"]["low"] += 1
                    else:
                        findings["summary"]["informational"] += 1

        return findings

    @staticmethod
    def _risk_to_string(risk: int) -> str:
        """Convert numeric risk level to string."""
        risk_map = {3: "High", 2: "Medium", 1: "Low", 0: "Informational"}
        return risk_map.get(risk, "Unknown")


def main():
    parser = argparse.ArgumentParser(description="ZAP Automated Scanner")
    parser.add_argument("-t", "--target", required=True, help="Target URL")
    parser.add_argument(
        "-s", "--scan-type",
        choices=["baseline", "full", "api"],
        default="baseline",
        help="Scan type",
    )
    parser.add_argument("-c", "--config", help="ZAP rules configuration file")
    parser.add_argument("--spec-url", help="API specification URL (for API scan)")
    parser.add_argument("--spec-format", default="openapi", help="API spec format")
    parser.add_argument(
        "--fail-on-high", action="store_true", help="Exit with error on high findings"
    )

    args = parser.parse_args()

    scanner = ZAPScanner(args.target, args.config)

    if args.scan_type == "baseline":
        results = scanner.run_baseline_scan()
    elif args.scan_type == "full":
        results = scanner.run_full_scan()
    elif args.scan_type == "api":
        results = scanner.run_api_scan(args.spec_url, args.spec_format)

    print(f"\nScan completed for {results['target']}")
    print(f"Summary: {json.dumps(results['summary'], indent=2)}")

    if args.fail_on_high and results["summary"]["high"] > 0:
        print(f"\nFailed: {results['summary']['high']} high-risk findings")
        sys.exit(1)

    print("\nNo high-risk findings or --fail-on-high not set")


if __name__ == "__main__":
    main()
```

### 3.2 Nikto

Nikto é uma ferramenta de varredura de servidor web que verifica mais de 6700 pontos potencialmente perigosos. Ele é ideal para identificar configurações inseguras, arquivos expostos e versões desatualizadas.

**Instalação e uso básico:**

```bash
# Instalação via Docker
docker pull secfigo/nikto

# Varredura básica
docker run --rm secfigo/nikto \
  -h https://your-application.com \
  -Format txt \
  -output nikto-report.txt

# Varredura completa com opções adicionais
docker run --rm secfigo/nikto \
  -h https://your-application.com \
  -p 443 \
  -ssl \
  -Tuning 123bde \
  -output nikto-report.html \
  -Format htm \
  -Plugins all

# Varredura de API específica
docker run --rm secfigo/nikto \
  -h https://your-application.com/api \
  -ssl \
  -Tuning 123 \
  -output nikto-api-report.txt
```

**Script de automação Nikto para CI/CD:**

```bash
#!/bin/bash
# nikto-scan.sh - Automated Nikto scan for CI/CD

set -euo pipefail

TARGET_URL="${1:?Target URL is required}"
OUTPUT_DIR="nikto-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${OUTPUT_DIR}/nikto-${TIMESTAMP}.json"

mkdir -p "${OUTPUT_DIR}"

echo "Starting Nikto scan against: ${TARGET_URL}"

# Run Nikto scan
docker run --rm \
  -v "$(pwd)/${OUTPUT_DIR}:/output" \
  secfigo/nikto \
  -h "${TARGET_URL}" \
  -ssl \
  -Format json \
  -output "/output/nikto-${TIMESTAMP}.json" \
  -Tuning 1234567890abcde 2>/dev/null || true

# Parse results
if [ -f "${REPORT_FILE}" ]; then
  echo "Scan completed. Results saved to: ${REPORT_FILE}"
  
  # Extract critical findings
  HIGH_RISK=$(cat "${REPORT_FILE}" | \
    python3 -c "
import json, sys
data = json.load(sys.stdin)
vulns = data.get('host', {}).get('vulnerabilities', [])
high_risk = [v for v in vulns if v.get('osvdbid', '0') not in ['0', '']]
print(len(high_risk))
" 2>/dev/null || echo "0")

  if [ "${HIGH_RISK}" -gt 0 ]; then
    echo "WARNING: ${HIGH_RISK} potentially serious findings detected"
    cat "${REPORT_FILE}" | \
      python3 -c "
import json, sys
data = json.load(sys.stdin)
vulns = data.get('host', {}).get('vulnerabilities', [])
for v in vulns:
    print(f\"  [{v.get('id', 'N/A')}] {v.get('msg', 'Unknown')}\")
" 2>/dev/null || true
  else
    echo "No critical findings detected"
  fi
else
  echo "ERROR: Report file not generated"
  exit 1
fi
```

### 3.3 Nuclei

Nuclei é uma ferramenta de varredura baseada em templates que permite verificar vulnerabilidades conhecidas em aplicações web. Seu ecossistema de templates é mantido pela comunidade e é continuamente atualizado.

**Instalação e uso:**

```bash
# Instalação via Go
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Instalação via Docker
docker pull projectdiscovery/nuclei

# Download dos templates atualizados
nuclei -update-templates

# Varredura básica
nuclei -u https://your-application.com -json -o nuclei-results.json

# Varredura com templates específicos
nuclei -u https://your-application.com \
  -t http/vulnerabilities/ \
  -t http/exposures/ \
  -t http/misconfiguration/ \
  -json -o nuclei-results.json

# Varredura de múltiplos alvos
nuclei -l urls.txt \
  -t http/ \
  -severity critical,high \
  -json -o nuclei-results.json

# Varredura com rate limiting
nuclei -u https://your-application.com \
  -t http/ \
  -rate-limit 10 \
  -concurrency 5 \
  -json -o nuclei-results.json
```

**Templates customizados para Nuclei:**

```yaml
# nuclei-templates/custom-api-scan.yaml
id: custom-api-scan

info:
  name: Custom API Security Scan
  author: security-team
  severity: high
  description: Custom security checks for our API endpoints
  tags: api, security, custom

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/v1/users"
      - "{{BaseURL}}/api/v1/admin"
      - "{{BaseURL}}/api/v1/config"

    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
          - 401

      - type: word
        words:
          - "password"
          - "secret"
          - "token"
        condition: or
        part: body

    extractors:
      - type: regex
        group: 1
        regex:
          - "\"token\":\s*\"([^\"]+)\""

---

id: api-rate-limit-test

info:
  name: API Rate Limiting Test
  author: security-team
  severity: medium
  description: Tests if API endpoints have proper rate limiting

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/v1/login"
      - "{{BaseURL}}/api/v1/register"

    attack: batteringram
    threads: 20
    race: true

    matchers:
      - type: status
        status:
          - 429

    extractors:
      - type: dsl
        dsl:
          - '"Rate limit: " + status_code'

---

id: sensitive-data-exposure

info:
  name: Sensitive Data Exposure Check
  author: security-team
  severity: high
  description: Checks for sensitive data exposure in API responses

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/v1/debug"
      - "{{BaseURL}}/api/v1/health"
      - "{{BaseURL}}/api/v1/status"
      - "{{BaseURL}}/.env"
      - "{{BaseURL}}/config.json"
      - "{{BaseURL}}/wp-config.php.bak"

    matchers-condition: or
    matchers:
      - type: word
        words:
          - "AWS_ACCESS_KEY"
          - "AWS_SECRET_KEY"
          - "DATABASE_URL"
          - "REDIS_URL"
          - "SECRET_KEY"
          - "API_KEY"
          - "PRIVATE_KEY"
        condition: or
        part: body

      - type: regex
        regex:
          - "(?i)password\\s*[:=]\\s*[\"'][^\"']+[\"']"
          - "(?i)secret\\s*[:=]\\s*[\"'][^\"']+[\"']"
          - "(?i)key\\s*[:=]\\s*[\"'][^\"']+[\"']"
        part: body
```

---

## 4. SCA for Web

### 4.1 npm audit

npm audit é a ferramenta nativa do npm para analisar vulnerabilidades em dependências do projeto.

**Uso básico:**

```bash
# Executar auditoria
npm audit

# Auditoria em formato JSON
npm audit --json

# Corrigir vulnerabilidades automaticamente
npm audit fix

# Correção forçada (pode incluir breaking changes)
npm audit fix --force

# Auditoria específica para produção
npm audit --omit=dev

# Ignorar vulnerabilidades específicas
# Adicionar no package.json:
```

```json
{
  "name": "my-web-app",
  "version": "1.0.0",
  "audit": {
    "ignore": [
      {
        "id": "GHSA-xxxx-xxxx-xxxx",
        "reason": "Vulnerability does not affect our usage pattern",
        "expires": "2025-12-31"
      }
    ]
  }
}
```

**Script de automação npm audit:**

```bash
#!/bin/bash
# npm-audit-ci.sh - npm audit for CI/CD pipelines

set -euo pipefail

AUDIT_LEVEL="${1:-moderate}"
OUTPUT_DIR="audit-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${OUTPUT_DIR}/npm-audit-${TIMESTAMP}.json"

mkdir -p "${OUTPUT_DIR}"

echo "Running npm audit at level: ${AUDIT_LEVEL}"

# Run npm audit
npm audit --json > "${REPORT_FILE}" 2>/dev/null || true

# Parse results
VULNS=$(cat "${REPORT_FILE}" | jq '.metadata.vulnerabilities')

HIGH_VULNS=$(echo "${VULNS}" | jq '.high // 0')
CRITICAL_VULNS=$(echo "${VULNS}" | jq '.critical // 0')
TOTAL_VULNS=$(echo "${VULNS}" | jq '.total // 0')

echo "Vulnerability Summary:"
echo "  Critical: ${CRITICAL_VULNS}"
echo "  High: ${HIGH_VULNS}"
echo "  Total: ${TOTAL_VULNS}"

# Determine exit code based on audit level
case "${AUDIT_LEVEL}" in
  critical)
    if [ "${CRITICAL_VULNS}" -gt 0 ]; then
      echo "FAILED: Critical vulnerabilities found"
      cat "${REPORT_FILE}" | jq '.vulnerabilities | to_entries[] | select(.value.severity == "critical") | {key, severity: .value.severity, title: .value.via[0].title}'
      exit 1
    fi
    ;;
  high)
    if [ "${HIGH_VULNS}" -gt 0 ] || [ "${CRITICAL_VULNS}" -gt 0 ]; then
      echo "FAILED: High or critical vulnerabilities found"
      exit 1
    fi
    ;;
  moderate)
    if [ "${TOTAL_VULNS}" -gt 0 ]; then
      echo "FAILED: Vulnerabilities found at moderate level"
      exit 1
    fi
    ;;
  low)
    # Just report, don't fail
    echo "INFO: Vulnerabilities detected (not failing build)"
    ;;
esac

echo "PASSED: No vulnerabilities above threshold"
```

### 4.2 Snyk

Snyk é uma ferramenta comercial de SCA que oferece análise mais detalhada e integração com múltiplas linguagens e ecossistemas.

**Instalação e uso:**

```bash
# Instalação via npm
npm install -g snyk

# Autenticação
snyk auth

# Testar projeto Node.js
snyk test

# Testar com monitoramento contínuo
snyk monitor

# Testar container image
snyk container test myapp:latest

# Testar infraestrutura como código
snyk iac test terraform/

# Gerar relatório em formato específico
snyk test --json-file-output=snyk-results.json
```

**Configuração do Snyk:**

```json
// .snyk
{
  "version": "1.25.0",
  "ignore": {
    "SNYK-JS-LODASH-567746": [
      {
        "reason": "Lodash is only used for deep cloning, not template evaluation",
        "expires": "2025-06-01T00:00:00.000Z",
        "package": "lodash",
        "paths": ["src/utils/deep-clone"]
      }
    ]
  },
  "patch": {
    "SNYK-JS-AXIOS-6144458": [
      {
        "upgrades": ["axios@0.21.1"],
        "patch": "diff --git a/node_modules/axios/lib/adapters/http.js b/node_modules/axios/lib/adapters/http.js\n--- a/node_modules/axios/lib/adapters/http.js\n+++ b/node_modules/axios/lib/adapters/http.js\n@@ -100,6 +100,8 @@\n     if (config.cancelToken) {\n       config.cancelToken.throwIfRequested();\n     }\n+    // Security: Validate URL to prevent SSRF\n+    validateUrl(config.url);\n "
      }
    ]
  }
}
```

**Integração com GitHub Actions:**

```yaml
name: Snyk Security Scan

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  schedule:
    - cron: '0 8 * * 1'  # Every Monday at 8 AM

jobs:
  snyk-test:
    name: Snyk Security Analysis
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --json-file-output=snyk-results.json

      - name: Upload Snyk results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: snyk-results
          path: snyk-results.json

  snyk-monitor:
    name: Snyk Monitor
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Monitor project with Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: monitor
          args: --org=my-org --project-name=my-web-app
```

### 4.3 Dependabot

Dependabot é uma ferramenta nativa do GitHub que monitora dependências automaticamente e cria pull requests para atualizá-las.

**Configuração do Dependabot:**

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Configuração para npm
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "daily"
      time: "09:00"
      timezone: "America/Sao_Paulo"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
    groups:
      production-dependencies:
        patterns:
          - "*"
        update-types:
          - "minor"
          - "patch"
      development-dependencies:
        dependency-type: "development"
        patterns:
          - "*"
    ignore:
      - dependency-name: "@types/node"
        update-types:
          - "version-update:semver-patch"
      - dependency-name: "eslint"
        update-types:
          - "version-update:semver-patch"

  # Configuração para GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "github-actions"
    groups:
      actions-dependencies:
        patterns:
          - "*"

  # Configuração para Docker
  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "docker"

  # Configuração para Terraform
  - package-ecosystem: "terraform"
    directory: "/infrastructure"
    schedule:
      interval: "monthly"
    labels:
      - "dependencies"
      - "infrastructure"
```

---

## 5. Secret Detection

### 5.1 gitleaks

gitleaks é uma ferramenta de detecção de secrets que verifica repositórios Git em busca de chaves de API, senhas, tokens e outros dados sensíveis.

**Instalação e uso:**

```bash
# Instalação via Go
go install github.com/gitleaks/gitleaks/v8@latest

# Instalação via brew (macOS)
brew install gitleaks

# Varredura de repositório local
gitleaks detect

# Varredura com relatório em JSON
gitleaks detect --report-format json --report-path gitleaks-report.json

# Varredura de commits específicos
gitleaks detect --log-opts="--since=2024-01-01"

# Proteger repositório (pre-commit)
gitleaks protect

# Proteger com baseline
gitleaks detect --report-format json --report-path gitleaks-baseline.json
gitleaks protect --baseline-path gitleaks-baseline.json
```

**Configuração personalizada do gitleaks:**

```toml
# .gitleaks.toml
title = "Gitleaks Configuration"

[allowlist]
  description = "Global allowlist"
  paths = [
    '''(?i)fixture[s]?''',
    '''(?i)test[s]?[/\\]mock''',
    '''(?i)example[s]?''',
    '''package-lock\.json$''',
    '''yarn\.lock$''',
  ]

[[rules]]
  id = "aws-access-key"
  description = "AWS Access Key"
  regex = '''(?:^|[^A-Z0-9])(?<![A-Z0-9]{16})(AKIA[0-9A-Z]{16})(?:[^A-Z0-9]|$)'''
  tags = ["key", "AWS"]

[[rules]]
  id = "aws-secret-key"
  description = "AWS Secret Access Key"
  regex = '''(?i)(?:aws_secret_access_key|aws_secret_key)['"]?\s*[:=]\s*['"]?([A-Za-z0-9/+=]{40})['"]?'''
  tags = ["key", "AWS"]

[[rules]]
  id = "github-token"
  description = "GitHub Token"
  regex = '''ghp_[A-Za-z0-9]{36}'''
  tags = ["key", "GitHub"]

[[rules]]
  id = "github-fine-grained-token"
  description = "GitHub Fine-grained Token"
  regex = '''github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59}'''
  tags = ["key", "GitHub"]

[[rules]]
  id = "gitlab-token"
  description = "GitLab Token"
  regex = '''glpat-[A-Za-z0-9\-_]{20,}'''
  tags = ["key", "GitLab"]

[[rules]]
  id = "slack-webhook"
  description = "Slack Webhook URL"
  regex = '''https://hooks\.slack\.com/services/T[A-Z0-9]{8}/B[A-Z0-9]{8}/[a-zA-Z0-9]{24}'''
  tags = ["key", "Slack"]

[[rules]]
  id = "slack-token"
  description = "Slack Token"
  regex = '''xox[baprs]-[0-9a-zA-Z\-]{10,}'''
  tags = ["key", "Slack"]

[[rules]]
  id = "stripe-api-key"
  description = "Stripe API Key"
  regex = '''(?:r|s)k_(?:live|test)_[0-9a-zA-Z]{24,}'''
  tags = ["key", "Stripe"]

[[rules]]
  id = "google-api-key"
  description = "Google API Key"
  regex = '''AIza[0-9A-Za-z\-_]{35}'''
  tags = ["key", "Google"]

[[rules]]
  id = "google-oauth"
  description = "Google OAuth ID"
  regex = '''[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com'''
  tags = ["key", "Google"]

[[rules]]
  id = "private-key"
  description = "Private Key"
  regex = '''-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----'''
  tags = ["key", "Private"]

[[rules]]
  id = "generic-api-key"
  description = "Generic API Key"
  regex = '''(?i)(?:api[_-]?key|apikey|api_key)['":\s]*(?:=|:)\s*['"]?([a-zA-Z0-9\-_]{20,})['"]?'''
  tags = ["key", "Generic"]
  [rules.allowlist]
    regex = '''(?:example|placeholder|test|dummy|fake)'''
    description = "Exclude example/placeholder values"

[[rules]]
  id = "generic-secret"
  description = "Generic Secret"
  regex = '''(?i)(?:secret|password|passwd|pwd)['":\s]*(?:=|:)\s*['"]?([^\s'"]{8,})['"]?'''
  tags = ["secret", "Generic"]
  [rules.allowlist]
    regex = '''(?:example|placeholder|test|dummy|fake|changeme|default)'''
    description = "Exclude example/placeholder values"

[[rules]]
  id = "npm-token"
  description = "npm Token"
  regex = '''npm_[A-Za-z0-9]{36}'''
  tags = ["key", "npm"]

[[rules]]
  id = "docker-password"
  description = "Docker Password"
  regex = '''(?i)(?:docker[_-]?password|docker[_-]?passwd)['":\s]*(?:=|:)\s*['"]?([^\s'"]{8,})['"]?'''
  tags = ["secret", "Docker"]
```

**Integração com pre-commit:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
        name: gitleaks
        entry: gitleaks protect --staged --redact
        language: golang
        pass_filenames: false
        always_run: true
```

### 5.2 truffleHog

truffleHog é outra ferramenta popular de detecção de secrets que oferece análise mais profunda, incluindo verificação de entropia e suporte a múltiplos provedores.

**Instalação e uso:**

```bash
# Instalação via Docker
docker pull trufflesecurity/trufflehog

# Varredura de repositório local
trufflehog git file://./ --json > trufflehog-results.json

# Varredura de repositório remoto
trufflehog git https://github.com/org/repo.git --json > trufflehog-results.json

# Varredura com verificação de GitHub
trufflehog github --org=my-org --json > trufflehog-results.json

# Varredura de S3 bucket
trufflehog s3 --bucket=my-bucket --json > trufflehog-results.json

# Varredura de filesystem
trufflehog filesystem /path/to/scan --json > trufflehog-results.json

# Apenas resultados recentes
trufflehog git file://./ --since-commit=HEAD~100 --json > trufflehog-results.json
```

**Script de automação truffleHog:**

```bash
#!/bin/bash
# trufflehog-scan.sh - Automated truffleHog scan for CI/CD

set -euo pipefail

REPO_URL="${1:-.}"
OUTPUT_DIR="trufflehog-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${OUTPUT_DIR}/trufflehog-${TIMESTAMP}.json"

mkdir -p "${OUTPUT_DIR}"

echo "Starting truffleHog scan against: ${REPO_URL}"

# Run truffleHog
if [ "${REPO_URL}" = "." ]; then
  trufflehog git file://. --json --only-verified > "${REPORT_FILE}" 2>/dev/null || true
else
  trufflehog git "${REPO_URL}" --json --only-verified > "${REPORT_FILE}" 2>/dev/null || true
fi

# Parse results
if [ -f "${REPORT_FILE}" ] && [ -s "${REPORT_FILE}" ]; then
  TOTAL_SECRETS=$(cat "${REPORT_FILE}" | jq -s 'length')
  echo "Found ${TOTAL_SECRETS} potential secrets"
  
  # Group by detector type
  echo "\nSecrets by type:"
  cat "${REPORT_FILE}" | jq -s 'group_by(.DetectorName) | map({type: .[0].DetectorName, count: length}) | sort_by(-.count)'
  
  # List verified secrets
  echo "\nVerified secrets:"
  cat "${REPORT_FILE}" | jq -s '.[] | select(.Verified == true) | {detector: .DetectorName, source: .SourceMetadata.Data.Git.commit}'
  
  # Exit with error if verified secrets found
  VERIFIED_COUNT=$(cat "${REPORT_FILE}" | jq -s '[.[] | select(.Verified == true)] | length')
  if [ "${VERIFIED_COUNT}" -gt 0 ]; then
    echo "FAILED: ${VERIFIED_COUNT} verified secrets found"
    exit 1
  fi
  
  echo "No verified secrets found (unverified results may be false positives)"
else
  echo "No secrets detected"
fi
```

**Configuração de entropia para truffleHog:**

```yaml
# trufflehog-config.yaml
# Configuração personalizada para truffleHog

detectors:
  # Ajustar sensibilidade de entropia
  entropy:
    enabled: true
    threshold: 4.5  # Valores maiores = mais seletivo

  # Excluir padrões específicos
  allowlist:
    patterns:
      - "example\\.com"
      - "placeholder"
      - "dummy"
      - "test"
      - "changeme"
      - "TODO"
      - "FIXME"
    
    paths:
      - "test/"
      - "__tests__/"
      - "spec/"
      - "fixture[s]?/"
      - "\\.min\\.js$"
      - "package-lock\\.json$"
      - "yarn\\.lock$"

# Provedores para verificação
github:
  enabled: true
  tokens:
    - "${GITHUB_TOKEN}"

gitlab:
  enabled: true
  tokens:
    - "${GITLAB_TOKEN}"
```

---

## 6. Infrastructure Scanning

### 6.1 Terraform Security

**Checkov**: Ferramenta de análise estática para infraestrutura como código que suporta Terraform, CloudFormation, Kubernetes e outros.

```bash
# Instalação
pip install checkov

# Varredura de diretório Terraform
checkov -d ./terraform/

# Varredura de arquivo específico
checkov -f ./terraform/main.tf

# Apenas verificações específicas
checkov -d ./terraform/ --check CKV_AWS_18,CKV_AWS_19

# Excluir verificações
checkov -d ./terraform/ --skip-check CKV_AWS_18

# Relatório em formato específico
checkov -d ./terraform/ -o json > checkov-results.json
checkov -d ./terraform/ -o junitxml > checkov-results.xml

# Varredura com custom policies
checkov -d ./terraform/ --external-checks-dir ./custom-policies/
```

**Políticas customizadas para Checkov:**

```python
# custom-policies/terraform/check_s3_bucket_policy.py
from checkov.common.models.enums import CheckCategories, CheckResultType
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck


class S3BucketPublicAccessCheck(BaseResourceCheck):
    def __init__(self):
        name = "Ensure S3 bucket is not publicly accessible"
        id = "CKV_CUSTOM_S3_001"
        supported_resources = ["aws_s3_bucket"]
        categories = [CheckCategories.GENERAL_SECURITY]
        super().__init__(name, id, categories)

    def scan_resource_conf(self, conf):
        """
        Looks for public access configuration:
        https://www.terraform.io/docs/providers/aws/r/s3_bucket.html
        """
        acl = conf.get("acl", ["private"])
        if acl and acl[0] == "public-read":
            return CheckResultType.FAILED

        block_public_acls = conf.get("block_public_acls", [True])
        block_public_policy = conf.get("block_public_policy", [True])
        ignore_public_acls = conf.get("ignore_public_acls", [True])
        restrict_public_buckets = conf.get("restrict_public_buckets", [True])

        if not all([block_public_acls[0], block_public_policy[0],
                   ignore_public_acls[0], restrict_public_buckets[0]]):
            return CheckResultType.FAILED

        return CheckResultType.PASSED


check = S3BucketPublicAccessCheck()
```

**Terraform Sentinel Policies:**

```hcl
# sentinel/policies/s3-encryption.sentinel
import "tfplan/v2" as tfplan
import "strings"

s3_buckets = filter tfplan.resource_changes as _, rc {
    rc.type is "aws_s3_bucket" and
    (rc.change.actions contains "create" or
     rc.change.actions contains "update")
}

main = rule {
    all s3_buckets as _, bucket {
        bucket.change.after.server_side_encryption_configuration is not null
    }
}

# Error message
policy_evaluation = rule when main is false {
    print("S3 bucket does not have server-side encryption enabled")
    false
}
```

### 6.2 Kubernetes Security

**kube-score**: Análise estática de manifests Kubernetes.

```bash
# Instalação
brew install kube-score

# Análise de manifests
kube-score score deployment/*.yaml

# Com verificação detalhada
kube-score score deployment/*.yaml --verbose
```

**Kubesec**: Análise de segurança para recursos Kubernetes.

```bash
# Instalação via Docker
docker run --rm -i kubesec/kubesec:v2 scan /dev/stdin < deployment.yaml

# Scan de múltiplos arquivos
find . -name "*.yaml" -exec docker run --rm -i kubesec/kubesec:v2 scan /dev/stdin < {} \;
```

**Polaris**: Auditoria e conformidade de Kubernetes.

```bash
# Instalação
brew install FairwindsOps/tap/polaris

# Auditoria
polaris audit --audit-path ./kubernetes/

# Dashboard
polaris dashboard
```

---

## 7. Container Scanning

### 7.1 Trivy

Trivy é uma ferramenta completa de varredura de vulnerabilidades que suporta containers, imagens Docker, repositórios Git e infraestrutura como código.

**Instalação e uso:**

```bash
# Instalação via brew
brew install trivy

# Varredura de imagem Docker
trivy image myapp:latest

# Varredura com relatório em JSON
trivy image --format json --output trivy-results.json myapp:latest

# Varredura apenas vulnerabilidades críticas
trivy image --severity CRITICAL,HIGH myapp:latest

# Varredura de repositório filesystem
trivy fs --scanners vuln,secret,misconfig .

# Varredura de configuração IaC
trivy config ./terraform/

# Varredura de SBOM
trivy image --format spdx-json --output sbom.json myapp:latest
```

**Dockerfile seguro com Trivy:**

```dockerfile
# Dockerfile otimizado para segurança

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency files first (layer caching)
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Run build if needed
RUN npm run build

# Stage 2: Production
FROM node:20-alpine AS production

# Security: Run as non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Security: Remove unnecessary packages
RUN apk --no-cache add dumb-init && \
    rm -rf /var/cache/apk/*

WORKDIR /app

# Copy only production dependencies
COPY --from=builder --chown=appuser:appgroup /app/node_modules ./node_modules
COPY --from=builder --chown=appuser:appgroup /app/dist ./dist
COPY --from=builder --chown=appuser:appgroup /app/package.json ./

# Security: Set non-root user
USER appuser

# Security: Expose only necessary port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node --check /app/dist/health.js || exit 1

# Use dumb-init to handle PID 1 properly
ENTRYPOINT ["dumb-init", "--"]

CMD ["node", "dist/server.js"]
```

### 7.2 Docker Scout

```bash
# Instalação
docker scout version

# Análise de vulnerabilidades
docker scout cves myapp:latest

# Comparação entre versões
docker scout compare myapp:latest --to myapp:previous

# Recomendações de base image
docker scout recommendations myapp:latest

# SBOM generation
docker scout sbom myapp:latest --format spdx-json
```

### 7.3 Integração de Container Scanning no CI/CD

```yaml
# GitHub Actions - Container Security
name: Container Security Scan

on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-scan:
    name: Build and Scan Container
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      security-events: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
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
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          ignore-unfixed: true

      - name: Upload Trivy scan results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Trivy for SBOM
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ steps.meta.outputs.version }}
          format: 'cyclonedx'
          output: 'sbom.cdx.json'

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sbom
          path: sbom.cdx.json
```

---

## 8. Dynamic Application Security Testing

### 8.1 Automação de DAST em CI/CD

**Configuração do OWASP ZAP no GitHub Actions:**

```yaml
name: DAST - OWASP ZAP

on:
  workflow_run:
    workflows: ["Deploy to Staging"]
    types: [completed]
    branches: [main]

jobs:
  zap-scan:
    name: OWASP ZAP Scan
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ vars.STAGING_URL }}
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j'
          allow_issue_writing: false

      - name: ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.10.0
        with:
          target: ${{ vars.STAGING_URL }}
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
          allow_issue_writing: true
        continue-on-error: true
```

**Integração de DAST com GitLab CI:**

```yaml
# .gitlab-ci.yml - DAST Stage
dast-zap:
  stage: security
  image: ghcr.io/zaproxy/zaproxy:stable
  script:
    - >
      zap-full-scan.py
      -t ${STAGING_URL}
      -r zap-report.html
      -J zap-report.json
      -l WARN
      -I
    - |
      HIGH_COUNT=$(cat zap-report.json | jq '[.site[].alerts[] | select(.riskcode == "3")] | length')
      if [ "$HIGH_COUNT" -gt 0 ]; then
        echo "CRITICAL: $HIGH_COUNT high-risk vulnerabilities found"
        exit 1
      fi
  artifacts:
    paths:
      - zap-report.html
      - zap-report.json
    reports:
      dast: zap-report.json
  only:
    - main
    - merge_requests
  allow_failure: false
```

### 8.2 Testes de Segurança Personalizados

**Script de testes de segurança para APIs:**

```typescript
// tests/security/api-security.test.ts
import request from 'supertest';
import { app } from '../../src/app';

describe('API Security Tests', () => {
  describe('SQL Injection Prevention', () => {
    const sqlPayloads = [
      "' OR '1'='1",
      "1; DROP TABLE users; --",
      "1' UNION SELECT * FROM users --",
      "admin'--",
      "1' OR 1=1#",
    ];

    it.each(sqlPayloads)('should prevent SQL injection with payload: %s', async (payload) => {
      const response = await request(app)
        .get(`/api/users/search?q=${encodeURIComponent(payload)}`)
        .expect(400);

      expect(response.body).not.toHaveProperty('users');
      expect(response.body.error).toBeDefined();
    });
  });

  describe('XSS Prevention', () => {
    const xssPayloads = [
      '<script>alert("xss")</script>',
      '<img src="x" onerror="alert(1)">',
      'javascript:alert(1)',
      '<svg onload="alert(1)">',
      '{{7*7}}',
    ];

    it.each(xssPayloads)('should prevent XSS with payload: %s', async (payload) => {
      const response = await request(app)
        .post('/api/comments')
        .send({ content: payload })
        .expect(201);

      expect(response.body.content).not.toContain('<script>');
      expect(response.body.content).not.toContain('onerror');
      expect(response.body.content).not.toContain('onload');
    });
  });

  describe('Authentication Bypass', () => {
    it('should reject requests without authentication token', async () => {
      await request(app)
        .get('/api/admin/users')
        .expect(401);
    });

    it('should reject invalid JWT tokens', async () => {
      await request(app)
        .get('/api/admin/users')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);
    });

    it('should reject expired JWT tokens', async () => {
      const expiredToken = generateExpiredToken();
      await request(app)
        .get('/api/admin/users')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);
    });

    it('should prevent JWT algorithm confusion', async () => {
      const noneToken = generateNoneAlgorithmToken();
      await request(app)
        .get('/api/admin/users')
        .set('Authorization', `Bearer ${noneToken}`)
        .expect(401);
    });
  });

  describe('Rate Limiting', () => {
    it('should enforce rate limiting on login endpoint', async () => {
      const requests = Array(100).fill(null).map(() =>
        request(app)
          .post('/api/auth/login')
          .send({ email: 'test@example.com', password: 'wrong' })
      );

      const responses = await Promise.all(requests);
      const rateLimited = responses.some(r => r.status === 429);

      expect(rateLimited).toBe(true);
    });
  });

  describe('CSRF Protection', () => {
    it('should require CSRF token for state-changing operations', async () => {
      await request(app)
        .post('/api/users/profile')
        .send({ name: 'Hacker' })
        .expect(403);
    });

    it('should reject CSRF tokens from different origins', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({ email: 'test@example.com', password: 'password' });

      const csrfToken = response.body.csrfToken;
      
      await request(app)
        .post('/api/users/profile')
        .set('X-CSRF-Token', csrfToken)
        .set('Origin', 'https://evil.com')
        .send({ name: 'Hacker' })
        .expect(403);
    });
  });

  describe('Security Headers', () => {
    it('should include security headers in response', async () => {
      const response = await request(app)
        .get('/')
        .expect(200);

      expect(response.headers['x-content-type-options']).toBe('nosniff');
      expect(response.headers['x-frame-options']).toBe('DENY');
      expect(response.headers['x-xss-protection']).toBe('0');
      expect(response.headers['strict-transport-security']).toBeDefined();
      expect(response.headers['content-security-policy']).toBeDefined();
    });

    it('should not expose server version', async () => {
      const response = await request(app)
        .get('/')
        .expect(200);

      expect(response.headers['server']).toBeUndefined();
      expect(response.headers['x-powered-by']).toBeUndefined();
    });
  });
});

// Helper functions
function generateExpiredToken(): string {
  // Generate a JWT token with exp in the past
  const header = Buffer.from(JSON.stringify({
    alg: 'HS256',
    typ: 'JWT'
  })).toString('base64url');

  const payload = Buffer.from(JSON.stringify({
    sub: 'user-123',
    iat: Math.floor(Date.now() / 1000) - 3600,
    exp: Math.floor(Date.now() / 1000) - 1,
  })).toString('base64url');

  return `${header}.${payload}.fake-signature`;
}

function generateNoneAlgorithmToken(): string {
  const header = Buffer.from(JSON.stringify({
    alg: 'none',
    typ: 'JWT'
  })).toString('base64url');

  const payload = Buffer.from(JSON.stringify({
    sub: 'admin',
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 3600,
  })).toString('base64url');

  return `${header}.${payload}.`;
}
```

---

## 9. Security Monitoring

### 9.1 Web Application Firewall (WAF)

**ModSecurity com OWASP Core Rule Set:**

```apache
# ModSecurity configuration for Apache/Nginx

# Load ModSecurity module
LoadModule security2_module modules/mod_security2.so

# ModSecurity configuration
<IfModule mod_security2.c>
    SecRuleEngine On
    
    # Request body handling
    SecRequestBodyAccess On
    SecRequestBodyLimit 13107200
    SecRequestBodyNoFilesLimit 131072
    SecRequestBodyLimitAction Reject
    
    # Response body handling
    SecResponseBodyAccess On
    SecResponseBodyMimeType text/plain text/html text/xml application/json
    SecResponseBodyLimit 524288
    SecResponseBodyLimitAction ProcessPartial
    
    # Temp files
    SecTmpDir /tmp/modsecurity/tmp
    SecDataDir /tmp/modsecurity/data
    
    # Audit log
    SecAuditEngine RelevantOnly
    SecAuditLogRelevantStatus "^(?:5|4(?!04))"
    SecAuditLogType Serial
    SecAuditLog /var/log/modsecurity/modsec_audit.log
    
    # Debug log (disabled in production)
    SecDebugLog /var/log/modsecurity/debug.log
    SecDebugLogLevel 0
    
    # Default action
    SecDefaultAction "phase:1,deny,log,status:403"
    
    # Include OWASP CRS
    Include /etc/modsecurity/owasp-crs/crs-setup.conf
    Include /etc/modsecurity/owasp-crs/rules/*.conf
    
    # Custom rules
    Include /etc/modsecurity/custom-rules/*.conf
</IfModule>
```

**Regras customizadas ModSecurity:**

```apache
# custom-rules/api-protection.conf

# Block common attack patterns
SecRule REQUEST_URI "@rx /api/" \
    "id:10001,\
    phase:1,\
    chain,\
    deny,\
    status:403,\
    log,\
    msg:'Potential API abuse detected',\
    tag:'custom/api-protection'"
    SecRule REQUEST_URI "@rx (?:exec|eval|system|passthru|shell_exec)\(" \
        "t:none,t:urlDecodeUni"

# Rate limiting for login attempts
SecRule REQUEST_URI "@rx /api/auth/login" \
    "id:10002,\
    phase:1,\
    chain,\
    pass,\
    nolog,\
    setvar:ip.login_attempts=+1,\
    expirevar:ip.login_attempts=60"
    SecRule REQUEST_METHOD "@rx POST" \
        "t:none"

SecRule IP:LOGIN_ATTEMPTS "@gt 5" \
    "id:10003,\
    phase:1,\
    deny,\
    status:429,\
    log,\
    msg:'Too many login attempts from IP',\
    tag:'custom/rate-limit'"

# Block suspicious user agents
SecRule REQUEST_HEADERS:User-Agent "@rx (?:nikto|sqlmap|nmap|masscan|zgrab|gobuster)" \
    "id:10004,\
    phase:1,\
    deny,\
    status:403,\
    log,\
    msg:'Suspicious user agent detected',\
    tag:'custom/user-agent'"

# Prevent JSON injection
SecRule REQUEST_CONTENT_TYPE "@rx application/json" \
    "id:10005,\
    phase:1,\
    chain,\
    pass,\
    nolog"
    SecRule REQUEST_BODY "@rx __proto__|constructor\[|prototype\[" \
        "t:none,t:urlDecodeUni,\
        deny,\
        status:400,\
        log,\
        msg:'Potential prototype pollution attempt',\
        tag:'custom/json-injection'"
```

**WAF com AWS WAF:**

```typescript
// lib/waf-stack.ts
import * as cdk from 'aws-cdk-lib';
import * as wafv2 from 'aws-cdk-lib/aws-wafv2';
import * as constructs from 'constructs';

export class WafStack extends cdk.Stack {
  constructor(scope: constructs.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create Web ACL
    const webAcl = new wafv2.CfnWebACL(this, 'WebACL', {
      scope: 'REGIONAL',
      defaultAction: { allow: {} },
      visibilityConfig: {
        sampledRequestsEnabled: true,
        cloudWatchMetricsEnabled: true,
        metricName: 'WebACLMetric',
      },
      rules: [
        // AWS Managed Rules - Common Rule Set
        {
          name: 'AWSManagedRulesCommonRuleSet',
          priority: 1,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesCommonRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'CommonRuleSetMetric',
          },
        },
        // AWS Managed Rules - Known Bad Inputs
        {
          name: 'AWSManagedRulesKnownBadInputsRuleSet',
          priority: 2,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesKnownBadInputsRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'KnownBadInputsMetric',
          },
        },
        // AWS Managed Rules - SQL Injection
        {
          name: 'AWSManagedRulesSQLiRuleSet',
          priority: 3,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesSQLiRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'SQLiRuleSetMetric',
          },
        },
        // AWS Managed Rules - Linux OS
        {
          name: 'AWSManagedRulesLinuxRuleSet',
          priority: 4,
          overrideAction: { none: {} },
          statement: {
            managedRuleGroupStatement: {
              vendorName: 'AWS',
              name: 'AWSManagedRulesLinuxRuleSet',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'LinuxRuleSetMetric',
          },
        },
        // Rate Limiting Rule
        {
          name: 'RateLimitRule',
          priority: 5,
          action: { block: {} },
          statement: {
            rateBasedStatement: {
              limit: 2000,
              aggregateKeyType: 'IP',
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'RateLimitMetric',
          },
        },
        // Block suspicious countries (example)
        {
          name: 'GeoBlockRule',
          priority: 6,
          action: { block: {} },
          statement: {
            geoMatchStatement: {
              countryCodes: ['XX', 'YY'], // Add specific country codes
            },
          },
          visibilityConfig: {
            sampledRequestsEnabled: true,
            cloudWatchMetricsEnabled: true,
            metricName: 'GeoBlockMetric',
          },
        },
      ],
    });
  }
}
```

### 9.2 Runtime Application Self-Protection (RASP)

**Configuração de RASP para Node.js:**

```typescript
// src/middleware/rasp.ts
import { Request, Response, NextFunction } from 'express';

interface RASPConfig {
  enableSqlInjectionDetection: boolean;
  enableXssDetection: boolean;
  enableCommandInjectionDetection: boolean;
  enablePathTraversalDetection: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  blockOnDetection: boolean;
}

const defaultConfig: RASPConfig = {
  enableSqlInjectionDetection: true,
  enableXssDetection: true,
  enableCommandInjectionDetection: true,
  enablePathTraversalDetection: true,
  logLevel: 'warn',
  blockOnDetection: true,
};

export class RASPMiddleware {
  private config: RASPConfig;

  constructor(config: Partial<RASPConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
  }

  middleware() {
    return (req: Request, res: Response, next: NextFunction) => {
      const threats: string[] = [];

      // Check for SQL injection
      if (this.config.enableSqlInjectionDetection) {
        if (this.detectSqlInjection(req)) {
          threats.push('SQL_INJECTION');
        }
      }

      // Check for XSS
      if (this.config.enableXssDetection) {
        if (this.detectXss(req)) {
          threats.push('XSS');
        }
      }

      // Check for command injection
      if (this.config.enableCommandInjectionDetection) {
        if (this.detectCommandInjection(req)) {
          threats.push('COMMAND_INJECTION');
        }
      }

      // Check for path traversal
      if (this.config.enablePathTraversalDetection) {
        if (this.detectPathTraversal(req)) {
          threats.push('PATH_TRAVERSAL');
        }
      }

      if (threats.length > 0) {
        this.logThreat(req, threats);

        if (this.config.blockOnDetection) {
          res.status(403).json({
            error: 'Request blocked by security policy',
            code: 'SECURITY_VIOLATION',
          });
          return;
        }
      }

      next();
    };
  }

  private detectSqlInjection(req: Request): boolean {
    const sqlPatterns = [
      /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)/i,
      /(\b(OR|AND)\b\s+\d+\s*=\s*\d+)/i,
      /(UNION\s+(ALL\s+)?SELECT)/i,
      /(--|#|\/\*|\*\/)/,
      /(';\s*(DROP|DELETE|INSERT|UPDATE))/i,
      /(CHAR\s*\(\d+\))/i,
      /(CONCAT\s*\()/i,
    ];

    const checkString = (str: string): boolean => {
      return sqlPatterns.some(pattern => pattern.test(str));
    };

    // Check URL parameters
    for (const value of Object.values(req.query)) {
      if (typeof value === 'string' && checkString(value)) {
        return true;
      }
    }

    // Check request body
    if (req.body && typeof req.body === 'object') {
      const bodyStr = JSON.stringify(req.body);
      if (checkString(bodyStr)) {
        return true;
      }
    }

    return false;
  }

  private detectXss(req: Request): boolean {
    const xssPatterns = [
      /<script\b[^>]*>/i,
      /javascript\s*:/i,
      /on\w+\s*=/i,
      /<iframe\b/i,
      /<object\b/i,
      /<embed\b/i,
      /eval\s*\(/i,
      /expression\s*\(/i,
    ];

    const checkString = (str: string): boolean => {
      return xssPatterns.some(pattern => pattern.test(str));
    };

    for (const value of Object.values(req.query)) {
      if (typeof value === 'string' && checkString(value)) {
        return true;
      }
    }

    if (req.body && typeof req.body === 'object') {
      for (const value of Object.values(req.body)) {
        if (typeof value === 'string' && checkString(value)) {
          return true;
        }
      }
    }

    return false;
  }

  private detectCommandInjection(req: Request): boolean {
    const commandPatterns = [
      /[;&|`$]/,
      /\b(cat|ls|pwd|id|whoami|uname|curl|wget|nc|netcat)\b/i,
      /\b(rm|mv|cp|chmod|chown)\b.*-[rf]/i,
      /\|\s*(bash|sh|cmd)/i,
      />\s*\/etc\//i,
    ];

    const checkString = (str: string): boolean => {
      return commandPatterns.some(pattern => pattern.test(str));
    };

    for (const value of Object.values(req.query)) {
      if (typeof value === 'string' && checkString(value)) {
        return true;
      }
    }

    return false;
  }

  private detectPathTraversal(req: Request): boolean {
    const traversalPatterns = [
      /\.\.\//,
      /\.\.\\/,
      /%2e%2e%2f/i,
      /%2e%2e\//i,
      /\.\.%2f/i,
      /etc\/passwd/i,
      /etc\/shadow/i,
      /proc\/self/i,
    ];

    const checkString = (str: string): boolean => {
      return traversalPatterns.some(pattern => pattern.test(str));
    };

    for (const value of Object.values(req.query)) {
      if (typeof value === 'string' && checkString(value)) {
        return true;
      }
    }

    if (req.path && checkString(req.path)) {
      return true;
    }

    return false;
  }

  private logThreat(req: Request, threats: string[]): void {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level: this.config.logLevel,
      threats,
      request: {
        method: req.method,
        path: req.path,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
      },
    };

    console.error(JSON.stringify(logEntry));
  }
}

// Usage
export const rasp = new RASPMiddleware({
  enableSqlInjectionDetection: true,
  enableXssDetection: true,
  enableCommandInjectionDetection: true,
  enablePathTraversalDetection: true,
  logLevel: 'warn',
  blockOnDetection: true,
});

// In app.ts
// app.use(rasp.middleware());
```

### 9.3 Bot Detection

```typescript
// src/middleware/bot-detection.ts
import { Request, Response, NextFunction } from 'express';

interface BotDetectionConfig {
  blockMaliciousBots: boolean;
  challengeSuspiciousBots: boolean;
  logBotActivity: boolean;
  whitelistedUserAgents: string[];
  blacklistedUserAgents: string[];
  rateLimitWindow: number;
  maxRequestsPerWindow: number;
}

const defaultConfig: BotDetectionConfig = {
  blockMaliciousBots: true,
  challengeSuspiciousBots: true,
  logBotActivity: true,
  whitelistedUserAgents: [
    'Googlebot',
    'Bingbot',
    'Slurp',  // Yahoo
    'DuckDuckBot',
  ],
  blacklistedUserAgents: [
    'SemrushBot',
    'AhrefsBot',
    'MJ12bot',
    'DotBot',
    'BLEXBot',
    'Sogou',
  ],
  rateLimitWindow: 60000,  // 1 minute
  maxRequestsPerWindow: 100,
};

export class BotDetectionMiddleware {
  private config: BotDetectionConfig;
  private requestCounts: Map<string, { count: number; resetTime: number }> = new Map();

  constructor(config: Partial<BotDetectionConfig> = {}) {
    this.config = { ...defaultConfig, ...config };
  }

  middleware() {
    return (req: Request, res: Response, next: NextFunction) => {
      const userAgent = req.get('User-Agent') || '';
      const clientIp = req.ip;

      // Check if bot is blacklisted
      if (this.isBlacklistedBot(userAgent)) {
        if (this.config.logBotActivity) {
          this.logBotActivity(req, 'BLOCKED', 'Blacklisted user agent');
        }

        if (this.config.blockMaliciousBots) {
          res.status(403).json({ error: 'Access denied' });
          return;
        }
      }

      // Check if bot is whitelisted
      if (this.isWhitelistedBot(userAgent)) {
        next();
        return;
      }

      // Rate limiting for unknown bots
      if (this.isBot(userAgent)) {
        const isRateLimited = this.checkRateLimit(clientIp);
        
        if (isRateLimited) {
          if (this.config.logBotActivity) {
            this.logBotActivity(req, 'RATE_LIMITED', 'Rate limit exceeded');
          }

          if (this.config.challengeSuspiciousBots) {
            res.status(429).json({
              error: 'Rate limit exceeded',
              retryAfter: Math.ceil(this.config.rateLimitWindow / 1000),
            });
            return;
          }
        }
      }

      // Detect bot-like behavior patterns
      if (this.detectSuspiciousBehavior(req)) {
        if (this.config.logBotActivity) {
          this.logBotActivity(req, 'SUSPICIOUS', 'Suspicious behavior pattern');
        }

        if (this.config.challengeSuspiciousBots) {
          res.status(403).json({
            error: 'Suspicious activity detected',
            code: 'BOT_DETECTED',
          });
          return;
        }
      }

      next();
    };
  }

  private isBot(userAgent: string): boolean {
    const botPatterns = [
      /bot/i,
      /crawler/i,
      /spider/i,
      /scraper/i,
      /curl/i,
      /wget/i,
      /python-requests/i,
      /go-http-client/i,
    ];

    return botPatterns.some(pattern => pattern.test(userAgent));
  }

  private isBlacklistedBot(userAgent: string): boolean {
    return this.config.blacklistedUserAgents.some(bot =>
      userAgent.toLowerCase().includes(bot.toLowerCase())
    );
  }

  private isWhitelistedBot(userAgent: string): boolean {
    return this.config.whitelistedUserAgents.some(bot =>
      userAgent.toLowerCase().includes(bot.toLowerCase())
    );
  }

  private checkRateLimit(clientIp: string): boolean {
    const now = Date.now();
    const clientData = this.requestCounts.get(clientIp);

    if (!clientData || now > clientData.resetTime) {
      this.requestCounts.set(clientIp, {
        count: 1,
        resetTime: now + this.config.rateLimitWindow,
      });
      return false;
    }

    clientData.count++;

    if (clientData.count > this.config.maxRequestsPerWindow) {
      return true;
    }

    return false;
  }

  private detectSuspiciousBehavior(req: Request): boolean {
    // Check for common bot patterns
    const suspiciousPatterns = [
      // Rapid sequential requests to different endpoints
      req.path.includes('..'),
      // Missing or unusual Accept headers
      !req.get('Accept'),
      // Multiple failed requests
      req.get('X-Forwarded-For')?.split(',').length > 5,
    ];

    return suspiciousPatterns.some(pattern => !!pattern);
  }

  private logBotActivity(req: Request, action: string, reason: string): void {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      action,
      reason,
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      path: req.path,
      method: req.method,
    }));
  }
}

// Usage
export const botDetection = new BotDetectionMiddleware();
```

---

## 10. Incident Response

### 10.1 Plano de Resposta a Incidentes para Web Apps

**Estrutura do plano:**

```markdown
# Plano de Resposta a Incidentes - Aplicações Web

## 1. Classificação de Incidentes

### Nível 1 - Crítico
- Comprometimento de dados sensíveis (PII, credenciais)
- Ransomware ou criptografia de dados
- Perda total de acesso ao sistema
- Vazamento de dados em produção

### Nível 2 - Alto
- Vulnerabilidade ativamente explorada
- Indício de acesso não autorizado
- Falha de segurança em componente crítico
- Indisponibilidade parcial do serviço

### Nível 3 - Médio
- Vulnerabilidade identificada mas não explorada
- Tentativa de ataque detectada e bloqueada
- Anomalia de comportamento suspeita
- Falha de configuração de segurança

### Nível 4 - Baixo
- Informação de segurança não crítica
- Melhoria de segurança solicitada
- Atualização de dependência pendente
- Auditoria de segurança programada

## 2. Fluxo de Notificação

### Horário Comercial (9h-18h)
1. Notificar líder de segurança imediatamente
2. Acionar equipe de resposta a incidentes
3. Escalar para CISO se nível 1 ou 2

### Fora do Horário Comercial
1. Usar sistema de alertas automatizado
2. Notificar plantonista de segurança
3. Acionar equipe de resposta se necessário

## 3. Contatos de Emergência

| Papel | Nome | Telefone | Email |
|-------|------|----------|-------|
| Líder de Segurança | [Nome] | [Telefone] | [Email] |
| CISO | [Nome] | [Telefone] | [Email] |
| Líder de Desenvolvimento | [Nome] | [Telefone] | [Email] |
| Gerente de Infraestrutura | [Nome] | [Telefone] | [Email] |
| Advogado Corporativo | [Nome] | [Telefone] | [Email] |
| Assessoria de Comunicação | [Nome] | [Telefone] | [Email] |

## 4. Playbooks de Resposta

### 4.1 Vazamento de Dados

**Fase 1: Contenção (0-1 horas)**
1. Isolar sistemas afetados
2. Revogar credenciais comprometidas
3. Ativar logs detalhados
4. Notificar equipe de segurança

**Fase 2: Avaliação (1-4 horas)**
1. Determinar escopo do vazamento
2. Identificar dados comprometidos
3. Avaliar impacto em usuários
4. Documentar evidências

**Fase 3: Erradicação (4-24 horas)**
1. Corrigir vulnerabilidade explorada
2. Remover malware ou acesso não autorizado
3. Atualizar credenciais e chaves
4. Implementar controles adicionais

**Fase 4: Recuperação (24-72 horas)**
1. Restaurar sistemas a estado seguro
2. Validar integridade dos dados
3. Monitorar comportamento anômalo
4. Testar funcionalidade

**Fase 5: Lições Aprendidas (1-2 semanas)**
1. Realizar análise pós-incidente
2. Documentar melhorias
3. Atualizar playbooks
4. Implementar correções

### 4.2 Ataque DDoS

**Detecção:**
- Monitore métricas de tráfego
- Configure alertas para spikes anormais
- Use WAF para detecção de padrões

**Resposta:**
1. Ativar proteção DDoS (CDN, rate limiting)
2. Notificar provedor de infraestrutura
3. Escalar recursos se necessário
4. Documentar padrões de ataque

### 4.3 Comprometimento de Conta

**Detecção:**
- Monitore logins incomuns
- Detecte mudanças de configuração
- Alert sobre atividades suspeitas

**Resposta:**
1. Forçar reset de senha
2. Revogar tokens de sessão
3. Verificar mudanças recentes
4. Notificar usuário afetado
5. Documentar e investigar

### 4.4 Injeção de Código

**Detecção:**
- Monitore logs de aplicação
- Detecte padrões de exploração
- Use RASP para detecção em runtime

**Resposta:**
1. Bloquear IP de origem
2. Isolar sistema afetado
3. Analisar logs detalhadamente
4. Corrigir vulnerabilidade
5. Validar correção

## 5. Comunicação

### Interna
- Use canais seguros para comunicação
- Documente todas as ações tomadas
- Mantenha stakeholders informados

### Externa
- Siga regulamentações de notificação (LGPD, GDPR)
- Prepare comunicado para usuários afetados
- Coordenar com assessoria de comunicação

## 6. Documentação

### Relatório de Incidente
1. Data e hora do incidente
2. Descrição do incidente
3. Sistemas afetados
4. Dados comprometidos
5. Ações tomadas
6. Impacto estimado
7. Recomendações

## 7. Recuperação

### Validação
1. Testes de segurança
2. Validação de integridade
3. Monitoramento reforçado
4. Auditoria de acessos

### Prevenção
1. Implementar controles adicionais
2. Atualizar políticas
3. Treinar equipe
4. Revisar arquitetura
```

### 10.2 Automação de Resposta a Incidentes

```typescript
// src/services/incident-response.ts
import { EventEmitter } from 'events';

export enum IncidentSeverity {
  CRITICAL = 1,
  HIGH = 2,
  MEDIUM = 3,
  LOW = 4,
}

export enum IncidentStatus {
  DETECTED = 'detected',
  INVESTIGATING = 'investigating',
  CONTAINED = 'contained',
  ERADICATED = 'eradicated',
  RECOVERING = 'recovering',
  RESOLVED = 'resolved',
  POST_MORTEM = 'post_mortem',
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  detectedAt: Date;
  updatedAt: Date;
  assignedTo?: string;
  affectedSystems: string[];
  actions: IncidentAction[];
  communications: Communication[];
}

export interface IncidentAction {
  timestamp: Date;
  action: string;
  performedBy: string;
  result: string;
}

export interface Communication {
  timestamp: Date;
  channel: 'slack' | 'email' | 'pagerduty' | 'phone';
  message: string;
  recipients: string[];
}

export class IncidentResponseService extends EventEmitter {
  private incidents: Map<string, Incident> = new Map();

  async detectIncident(data: {
    title: string;
    description: string;
    severity: IncidentSeverity;
    affectedSystems: string[];
  }): Promise<Incident> {
    const incident: Incident = {
      id: this.generateId(),
      title: data.title,
      description: data.description,
      severity: data.severity,
      status: IncidentStatus.DETECTED,
      detectedAt: new Date(),
      updatedAt: new Date(),
      affectedSystems: data.affectedSystems,
      actions: [],
      communications: [],
    };

    this.incidents.set(incident.id, incident);

    // Trigger automated response
    await this.automatedResponse(incident);

    // Notify team
    await this.notifyTeam(incident);

    this.emit('incident:detected', incident);

    return incident;
  }

  private async automatedResponse(incident: Incident): Promise<void> {
    switch (incident.severity) {
      case IncidentSeverity.CRITICAL:
        await this.handleCriticalIncident(incident);
        break;
      case IncidentSeverity.HIGH:
        await this.handleHighIncident(incident);
        break;
      case IncidentSeverity.MEDIUM:
        await this.handleMediumIncident(incident);
        break;
      case IncidentSeverity.LOW:
        await this.handleLowIncident(incident);
        break;
    }
  }

  private async handleCriticalIncident(incident: Incident): Promise<void> {
    // Immediate containment actions
    await this.addAction(incident, {
      action: 'Isolate affected systems',
      performedBy: 'automated',
      result: 'Systems isolated successfully',
    });

    // Revoke compromised credentials
    await this.addAction(incident, {
      action: 'Revoke compromised credentials',
      performedBy: 'automated',
      result: 'Credentials revoked',
    });

    // Enable enhanced logging
    await this.addAction(incident, {
      action: 'Enable enhanced logging',
      performedBy: 'automated',
      result: 'Enhanced logging activated',
    });

    // Page on-call team
    await this.pageOnCall(incident);
  }

  private async handleHighIncident(incident: Incident): Promise<void> {
    // Block suspicious IPs
    await this.addAction(incident, {
      action: 'Block suspicious IPs',
      performedBy: 'automated',
      result: 'IPs blocked',
    });

    // Enable rate limiting
    await this.addAction(incident, {
      action: 'Enable aggressive rate limiting',
      performedBy: 'automated',
      result: 'Rate limiting enabled',
    });
  }

  private async handleMediumIncident(incident: Incident): Promise<void> {
    // Log for investigation
    await this.addAction(incident, {
      action: 'Log incident for investigation',
      performedBy: 'automated',
      result: 'Incident logged',
    });

    // Schedule review
    await this.addAction(incident, {
      action: 'Schedule security review',
      performedBy: 'automated',
      result: 'Review scheduled',
    });
  }

  private async handleLowIncident(incident: Incident): Promise<void> {
    // Log for awareness
    await this.addAction(incident, {
      action: 'Log for security awareness',
      performedBy: 'automated',
      result: 'Incident logged',
    });
  }

  private async addAction(incident: Incident, action: IncidentAction): Promise<void> {
    incident.actions.push({
      ...action,
      timestamp: new Date(),
    });
    incident.updatedAt = new Date();
  }

  private async notifyTeam(incident: Incident): Promise<void> {
    const notification = {
      timestamp: new Date(),
      channel: this.getNotificationChannel(incident.severity),
      message: this.formatNotification(incident),
      recipients: this.getRecipients(incident.severity),
    };

    incident.communications.push(notification);

    // Send notification via appropriate channel
    await this.sendNotification(notification);
  }

  private async pageOnCall(incident: Incident): Promise<void> {
    // Integrate with PagerDuty or similar
    console.log(`Paging on-call for incident ${incident.id}`);
  }

  private getNotificationChannel(severity: IncidentSeverity): Communication['channel'] {
    switch (severity) {
      case IncidentSeverity.CRITICAL:
        return 'pagerduty';
      case IncidentSeverity.HIGH:
        return 'slack';
      case IncidentSeverity.MEDIUM:
        return 'email';
      case IncidentSeverity.LOW:
        return 'slack';
    }
  }

  private getRecipients(severity: IncidentSeverity): string[] {
    switch (severity) {
      case IncidentSeverity.CRITICAL:
        return ['security-team', 'engineering-leads', 'ciso'];
      case IncidentSeverity.HIGH:
        return ['security-team', 'engineering-leads'];
      case IncidentSeverity.MEDIUM:
        return ['security-team'];
      case IncidentSeverity.LOW:
        return ['security-team'];
    }
  }

  private formatNotification(incident: Incident): string {
    return [
      `[${IncidentSeverity[incident.severity]}] ${incident.title}`,
      `ID: ${incident.id}`,
      `Status: ${incident.status}`,
      `Affected: ${incident.affectedSystems.join(', ')}`,
      `Detected: ${incident.detectedAt.toISOString()}`,
    ].join('\n');
  }

  private async sendNotification(notification: Communication): Promise<void> {
    // Implement actual notification logic
    console.log('Sending notification:', notification);
  }

  private generateId(): string {
    return `INC-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Usage example
const incidentService = new IncidentResponseService();

incidentService.on('incident:detected', (incident: Incident) => {
  console.log('Incident detected:', incident.id);
});
```

---

## 11. Complete GitHub Actions Security Pipeline

### 11.1 Pipeline Completa

{% raw %}
```yaml
# .github/workflows/security-pipeline.yml
name: Complete Security Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 8 * * 1'  # Weekly scan

permissions:
  contents: read
  security-events: write
  actions: read
  id-token: write

env:
  NODE_VERSION: '20'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ==========================================
  # Stage 1: Code Quality & Security Linting
  # ==========================================
  code-quality:
    name: Code Quality & Security Linting
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint with security rules
        run: |
          npx eslint . \
            --ext .js,.jsx,.ts,.tsx \
            --format json \
            --output-file eslint-results.json \
            || true
          
          # Check for security-critical errors
          SECURITY_ERRORS=$(cat eslint-results.json | \
            jq '[.messages[] | select(.ruleId | startswith("security/"))] | length')
          
          if [ "$SECURITY_ERRORS" -gt 0 ]; then
            echo "Security lint errors found"
            cat eslint-results.json | \
              jq '.messages[] | select(.ruleId | startswith("security/")) | {rule, message, line}'
            exit 1
          fi

      - name: Upload ESLint results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: eslint-results
          path: eslint-results.json

  # ==========================================
  # Stage 2: Secret Detection
  # ==========================================
  secret-detection:
    name: Secret Detection
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Run truffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

  # ==========================================
  # Stage 3: SAST (Static Application Security Testing)
  # ==========================================
  sast:
    name: SAST Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Semgrep
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/default
            p/javascript
            p/typescript
            p/nodejs
            p/express
            p/owasp-top-ten
          generateSarif: true

      - name: Upload SARIF to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: semgrep.sarif

      - name: Run SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@master
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
        with:
          args: >
            -Dsonar.projectKey=${{ github.repository_owner }}_${{ github.event.repository.name }}
            -Dsonar.sources=src
            -Dsonar.exclusions=**/node_modules/**,**/test/**
            -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info

  # ==========================================
  # Stage 4: SCA (Software Composition Analysis)
  # ==========================================
  sca:
    name: Software Composition Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run npm audit
        run: |
          npm audit --json > npm-audit.json || true
          
          CRITICAL=$(cat npm-audit.json | jq '.metadata.vulnerabilities.critical // 0')
          HIGH=$(cat npm-audit.json | jq '.metadata.vulnerabilities.high // 0')
          
          echo "Critical: $CRITICAL"
          echo "High: $HIGH"
          
          if [ "$CRITICAL" -gt 0 ]; then
            echo "Critical vulnerabilities found"
            exit 1
          fi

      - name: Run Snyk
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --json-file-output=snyk-results.json

      - name: Upload SCA results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: sca-results
          path: |
            npm-audit.json
            snyk-results.json

  # ==========================================
  # Stage 5: Container Security
  # ==========================================
  container-security:
    name: Container Security
    runs-on: ubuntu-latest
    needs: [code-quality, secret-detection, sast, sca]
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          load: true
          tags: ${{ env.IMAGE_NAME }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.IMAGE_NAME }}:scan
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
          ignore-unfixed: true

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

      - name: Run Docker Scout
        uses: docker/scout-action@v1
        with:
          command: cves
          image: ${{ env.IMAGE_NAME }}:scan
          only-severities: critical,high
          exit-code: true

  # ==========================================
  # Stage 6: Infrastructure Security
  # ==========================================
  infrastructure-security:
    name: Infrastructure Security
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Run Checkov
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: terraform/
          framework: terraform
          output_format: json
          output_file_path: checkov-results.json
          soft_fail: false

      - name: Upload Checkov results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: checkov-results
          path: checkov-results.json

  # ==========================================
  # Stage 7: DAST (Dynamic Application Security Testing)
  # ==========================================
  dast:
    name: DAST - OWASP ZAP
    runs-on: ubuntu-latest
    needs: [container-security]
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.12.0
        with:
          target: ${{ vars.STAGING_URL }}
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a -j'
          allow_issue_writing: false

      - name: ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.10.0
        with:
          target: ${{ vars.STAGING_URL }}
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'
          allow_issue_writing: true
        continue-on-error: true

  # ==========================================
  # Stage 8: Security Report
  # ==========================================
  security-report:
    name: Security Report
    runs-on: ubuntu-latest
    needs: [code-quality, secret-detection, sast, sca, container-security, infrastructure-security, dast]
    if: always()
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts

      - name: Generate security summary
        run: |
          echo "# Security Pipeline Report" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "## Scan Results" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          
          for artifact in artifacts/*/; do
            name=$(basename "$artifact")
            echo "### $name" >> $GITHUB_STEP_SUMMARY
            ls -la "$artifact" >> $GITHUB_STEP_SUMMARY
            echo "" >> $GITHUB_STEP_SUMMARY
          done

      - name: Upload combined report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: security-report
          path: artifacts/
```
{% endraw %}

---

## 12. Complete GitLab CI Security Pipeline

### 12.1 Pipeline Completa no GitLab

```yaml
# .gitlab-ci.yml - Complete Security Pipeline

stages:
  - build
  - test
  - security
  - deploy
  - monitor

variables:
  DOCKER_IMAGE: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  NODE_IMAGE: node:20-alpine

# ==========================================
# Stage 1: Build
# ==========================================
build:
  stage: build
  image: $NODE_IMAGE
  script:
    - npm ci --cache .npm --prefer-offline
    - npm run build
  artifacts:
    paths:
      - dist/
      - node_modules/
    expire_in: 1 hour
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .npm/
      - node_modules/

# ==========================================
# Stage 2: Tests & Quality
# ==========================================
unit-tests:
  stage: test
  image: $NODE_IMAGE
  script:
    - npm ci
    - npm run test:coverage
  coverage: '/Lines\s*:\s*(\d+\.?\d*)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
    paths:
      - coverage/
    expire_in: 1 week

# ==========================================
# Stage 3: Security Analysis
# ==========================================

# Secret Detection
secret-detection:
  stage: security
  image: zricethezav/gitleaks:latest
  script:
    - gitleaks detect
      --source="."
      --report-format=json
      --report-path=gitleaks-report.json
      --verbose
  artifacts:
    paths:
      - gitleaks-report.json
    reports:
      secret_detection: gitleaks-report.json
  allow_failure: false

# SAST - Static Application Security Testing
sast:
  stage: security
  image: semgrep/semgrep:latest
  script:
    - semgrep scan
      --config=auto
      --json
      --output=semgrep-results.json
      --sarif
      --output=semgrep-results.sarif
  artifacts:
    paths:
      - semgrep-results.json
      - semgrep-results.sarif
    reports:
      sast: gl-sast-report.json
  allow_failure: false

# SCA - Software Composition Analysis
dependency-scanning:
  stage: security
  image: $NODE_IMAGE
  script:
    - npm ci
    - npm audit --json > npm-audit.json || true
    - |
      CRITICAL=$(cat npm-audit.json | jq '.metadata.vulnerabilities.critical // 0')
      HIGH=$(cat npm-audit.json | jq '.metadata.vulnerabilities.high // 0')
      
      if [ "$CRITICAL" -gt 0 ]; then
        echo "Critical vulnerabilities found"
        exit 1
      fi
      
      if [ "$HIGH" -gt 0 ]; then
        echo "High vulnerabilities found"
        exit 1
      fi
  artifacts:
    paths:
      - npm-audit.json
    reports:
      dependency_scanning: gl-dependency-scanning-report.json

# Container Scanning
container-scanning:
  stage: security
  image:
    name: aquasec/trivy:latest
    entrypoint: [""]
  services:
    - docker:24-dind
  variables:
    DOCKER_TLS_CERTDIR: "/certs"
  before_script:
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker build -t $DOCKER_IMAGE .
  script:
    - trivy image
      --format json
      --output trivy-results.json
      --severity CRITICAL,HIGH
      $DOCKER_IMAGE
    - trivy image
      --format sarif
      --output trivy-results.sarif
      --severity CRITICAL,HIGH
      $DOCKER_IMAGE
  artifacts:
    paths:
      - trivy-results.json
      - trivy-results.sarif
    reports:
      container_scanning: gl-container-scanning-report.json
  allow_failure: false

# Infrastructure as Code Security
iac-security:
  stage: security
  image:
    name: bridgecrew/checkov:latest
    entrypoint: [""]
  script:
    - checkov
      --directory .
      --framework terraform
      --output json
      --output-file checkov-results.json
      --soft-fail-on CRITICAL
  artifacts:
    paths:
      - checkov-results.json
    reports:
      sast: checkov-results.json

# DAST - Dynamic Application Security Testing
dast:
  stage: security
  image: ghcr.io/zaproxy/zaproxy:stable
  script:
    - >
      zap-full-scan.py
      -t $STAGING_URL
      -r zap-report.html
      -J zap-report.json
      -l WARN
      -I
  artifacts:
    paths:
      - zap-report.html
      - zap-report.json
    reports:
      dast: zap-report.json
  only:
    - main
    - merge_requests
  allow_failure: true

# Security Scan Summary
security-summary:
  stage: security
  image: alpine:latest
  dependencies:
    - secret-detection
    - sast
    - dependency-scanning
    - container-scanning
    - iac-security
    - dast
  script:
    - |
      echo "# Security Scan Summary"
      echo ""
      echo "## Results"
      echo ""
      
      # Check gitleaks
      if [ -f gitleaks-report.json ]; then
        SECRETS=$(cat gitleaks-report.json | jq 'length')
        echo "- **Secret Detection**: $SECRETS findings"
      else
        echo "- **Secret Detection**: No findings"
      fi
      
      # Check semgrep
      if [ -f semgrep-results.json ]; then
        SAST_ISSUES=$(cat semgrep-results.json | jq '.results | length')
        echo "- **SAST**: $SAST_ISSUES issues"
      else
        echo "- **SAST**: No issues"
      fi
      
      # Check npm audit
      if [ -f npm-audit.json ]; then
        VULNS=$(cat npm-audit.json | jq '.metadata.vulnerabilities.total // 0')
        echo "- **Dependency Scanning**: $VULNS vulnerabilities"
      else
        echo "- **Dependency Scanning**: No vulnerabilities"
      fi
      
      # Check trivy
      if [ -f trivy-results.json ]; then
        CONTAINER_VULNS=$(cat trivy-results.json | jq '.Results[0].Vulnerabilities | length // 0')
        echo "- **Container Scanning**: $CONTAINER_VULNS vulnerabilities"
      else
        echo "- **Container Scanning**: No vulnerabilities"
      fi
  artifacts:
    paths:
      - SECURITY.md
  only:
    - main

# ==========================================
# Stage 4: Deploy
# ==========================================
deploy-staging:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl -X POST "$DEPLOY_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d '{"environment": "staging", "version": "'$CI_COMMIT_SHA'"}'
  environment:
    name: staging
    url: $STAGING_URL
  only:
    - main
  when: manual

deploy-production:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache curl
  script:
    - |
      curl -X POST "$DEPLOY_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d '{"environment": "production", "version": "'$CI_COMMIT_SHA'"}'
  environment:
    name: production
    url: $PRODUCTION_URL
  only:
    - main
  when: manual
  needs:
    - deploy-staging
    - security-summary

# ==========================================
# Stage 5: Post-Deploy Monitoring
# ==========================================
post-deploy-security:
  stage: monitor
  image: $NODE_IMAGE
  script:
    - npm ci
    - npm run test:security
  only:
    - main
  when: on_success
```

---

## 13. Exercícios

### Exercício 1: Configuração de Security Gates

**Objetivo**: Configurar security gates em uma pipeline de CI/CD para um projeto Node.js.

**Instruções**:

1. Crie um novo projeto Node.js ou use um existente
2. Configure ESLint com plugins de segurança
3. Adicione hooks pré-commit usando husky e lint-staged
4. Configure gitleaks para detecção de secrets
5. Crie uma pipeline GitHub Actions que execute todas as verificações

**Entregáveis**:
- Arquivo `.eslintrc.js` com regras de segurança
- Arquivo `.pre-commit-config.yaml` configurado
- Arquivo `.gitleaks.toml` com regras personalizadas
- Arquivo `.github/workflows/security.yml` com a pipeline completa

**Critérios de Avaliação**:
- Pipeline deve falhar se encontrar vulnerabilidades críticas
- Hooks devem impedir commits com código inseguro
- Devem existir pelo menos 10 regras de segurança configuradas

### Exercício 2: Implementação de SAST com Semgrep

**Objetivo**: Criar regras customizadas de Semgrep para detectar vulnerabilidades específicas do seu projeto.

**Instruções**:

1. Analise seu código em busca de padrões inseguros comuns
2. Crie pelo menos 5 regras Semgrep customizadas
3. Teste as regras localmente
4. Integre com CI/CD
5. Documente cada regra encontrada

**Entregáveis**:
- Arquivo `.semgrep.yml` com regras customizadas
- Documentação explicando cada regra
- Relatório de findings encontrados
- Pipeline atualizada com Semgrep

**Critérios de Avaliação**:
- Regras devem detectar vulnerabilidades reais
- Falsos positivos devem ser minimizados
- Documentação deve ser clara e útil

### Exercício 3: DAST com OWASP ZAP

**Objetivo**: Configurar e executar testes DAST usando OWASP ZAP.

**Instruções**:

1. Suba uma aplicação web em ambiente de staging
2. Configure o ZAP para varredura automatizada
3. Crie um script de automação que execute o ZAP regularmente
4. Analise os resultados e crie um plano de correção
5. Implemente as correções para vulnerabilidades encontradas

**Entregáveis**:
- Script de automação ZAP
- Relatório de varredura
- Plano de remediação
- Evidências das correções implementadas

**Critérios de Avaliação**:
- ZAP deve ser executado automaticamente
- Vulnerabilidades críticas devem ser corrigidas
- Relatório deve ser claro e acionável

### Exercício 4: Container Security

**Objetivo**: Implementar varredura de segurança completa para containers Docker.

**Instruções**:

1. Crie um Dockerfile seguro seguindo best practices
2. Configure Trivy para varredura de imagens
3. Implemente Docker Scout para recomendações
4. Configure pipeline para varredura automática
5. Documente todas as vulnerabilidades encontradas

**Entregáveis**:
- Dockerfile otimizado para segurança
- Configuração Trivy
- Pipeline de varredura de containers
- Relatório de vulnerabilidades

**Critérios de Avaliação**:
- Container não deve executar como root
- Imagem deve usar base mínima
- Vulnerabilidades críticas devem ser corrigidas
- SBOM deve ser gerado

### Exercício 5: Incident Response Playbook

**Objetivo**: Criar um playbook de resposta a incidentes para uma aplicação web.

**Instruções**:

1. Identifique os principais riscos da sua aplicação
2. Crie playbooks para cada tipo de incidente
3. Configure alertas automatizados
4. Implemente scripts de contenção
5. Realize um tabletop exercise

**Entregáveis**:
- Documento de playbooks de incident response
- Scripts de automação de contenção
- Configuração de alertas
- Relatório do tabletop exercise

**Critérios de Avaliação**:
- Playbooks devem cobrir os principais cenários
- Scripts devem ser testados e funcionais
- Alertas devem ser configurados corretamente
- Tabletop exercise deve ser documentado

### Exercício 6: Monitoramento de Segurança

**Objetivo**: Configurar monitoramento de segurança abrangente para uma aplicação web.

**Instruções**:

1. Configure WAF com regras personalizadas
2. Implemente RASP para detecção em runtime
3. Configure bot detection
4. Implemente logging de segurança centralizado
5. Configure dashboards de monitoramento

**Entregáveis**:
- Configuração WAF
- Implementação RASP
- Configuração de bot detection
- Pipeline de logs de segurança
- Dashboard de monitoramento

**Critérios de Avaliação**:
- WAF deve bloquear ataques conhecidos
- RASP deve detectar ameaças em runtime
- Bot detection deve identificar bots maliciosos
- Logs devem ser centralizados e pesquisáveis
- Dashboard deve mostrar métricas de segurança em tempo real

---

## 14. Referências

### OWASP (Open Worldwide Application Security Project)

1. OWASP Top Ten - https://owasp.org/Top10/
2. OWASP Application Security Verification Standard (ASVS) - https://owasp.org/www-project-application-security-verification-standard/
3. OWASP DevSecOps Guideline - https://owasp.org/www-project-devsecops-guideline/
4. OWASP ZAP - https://www.zaproxy.org/
5. OWASP Dependency-Check - https://owasp.org/www-project-dependency-check/
6. OWASP Code Review Guide - https://owasp.org/www-project-code-review-guide/
7. OWASP Testing Guide - https://owasp.org/www-project-web-security-testing-guide/

### Ferramentas de Segurança

8. Semgrep - https://semgrep.dev/
9. SonarQube - https://www.sonarsource.com/products/sonarqube/
10. Trivy - https://trivy.dev/
11. Snyk - https://snyk.io/
12. gitleaks - https://github.com/gitleaks/gitleaks
13. truffleHog - https://github.com/trufflesecurity/trufflehog
14. Checkov - https://www.checkov.io/
15. Docker Scout - https://docs.docker.com/scout/
16. Nuclei - https://nuclei.projectdiscovery.io/
17. Nikto - https://cirt.net/Nikto2

### CI/CD e DevSecOps

18. GitHub Actions Security - https://docs.github.com/en/actions/security
19. GitLab CI Security - https://docs.gitlab.com/ee/ci/
20. Jenkins Security - https://www.jenkins.io/doc/book/security/
21. Pipeline Security Best Practices - https://www.cisa.gov/news-events/cybersecurity-advisories/aa20-304a
22. SLSA Framework - https://slsa.dev/
23. In-Toto - https://in-toto.io/

### Infraestrutura como Código

24. Terraform Security - https://developer.hashicorp.com/terraform/cloud-docs/security
25. Kubernetes Security - https://kubernetes.io/docs/concepts/security/
26. AWS Security Best Practices - https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html
27. Cloud Security Posture Management - https://www.nist.gov/cyberframework

### Padrões e Frameworks

28. NIST Cybersecurity Framework - https://www.nist.gov/cyberframework
29. ISO 27001 - https://www.iso.org/iso-27001-information-security.html
30. SOC 2 - https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report
31. PCI DSS - https://www.pcisecuritystandards.org/
32. LGPD (Lei Geral de Protecao de Dados) - https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm

### Livros e Artigos

33. "DevSecOps: How to Seamlessly Integrate Security into DevOps" - Eyal Estrin
34. "Continuous Security: A Practical Guide to Securing Software" - Various Authors
35. "The DevSecOps Playbook" - Various Authors
36. "Web Application Security: Exploitation and Countermeasures for Modern Web Applications" - Andrew Hoffman
37. "Securing DevOps: How to Make Security Work" - Julien Vehent
38. "Application Security in the ISO 27001 Environment" - Various Authors

### Comunidades e Recursos

39. DevSecOps Community - https://www.devsecops.org/
40. Cloud Security Alliance - https://cloudsecurityalliance.org/
41. SANS Institute - https://www.sans.org/
42. National Cyber Security Centre - https://www.ncsc.gov.uk/
43. CERT/CC - https://www.sei.cmu.edu/about/divisions/cert/

---

## Resumo

Neste capítulo, exploramos os princípios e práticas de DevSecOps aplicados ao desenvolvimento web moderno. Cobrimos desde a configuração de security gates em pipelines de CI/CD até a implementação de ferramentas de monitoramento e resposta a incidentes.

Os pontos-chave abordados incluem:

- **Security Gates**: Implementação de verificações de segurança em múltiplas camadas do ciclo de desenvolvimento
- **SAST**: Uso de ESLint com plugins de segurança e Semgrep para análise estática de código
- **DAST**: Configuração do OWASP ZAP, Nikto e Nuclei para testes dinâmicos de segurança
- **SCA**: Gerenciamento de vulnerabilidades em dependências usando npm audit, Snyk e Dependabot
- **Secret Detection**: Detecção de dados sensíveis usando gitleaks e truffleHog
- **Infrastructure Scanning**: Análise de segurança de infraestrutura como código com Checkov
- **Container Scanning**: Varredura de imagens Docker usando Trivy e Docker Scout
- **Security Monitoring**: Implementação de WAF, RASP e bot detection
- **Incident Response**: Criação de playbooks e automação de resposta a incidentes
- **Pipeline Completa**: Exemplos práticos de pipelines de segurança no GitHub Actions e GitLab CI

A adoção de DevSecOps não é apenas uma questão de ferramentas, mas uma mudança cultural que coloca a segurança no centro do processo de desenvolvimento. Ao integrar segurança desde o início do ciclo de vida do desenvolvimento, é possível reduzir significativamente riscos, diminuir custos de correção e entregar software mais seguro e confiável.

---

*Fim do Capítulo 15 - DevSecOps para Aplicações Web*
---

*[Capítulo anterior: 14 — Seguranca Container](14-seguranca-container.md)*
*[Próximo capítulo: 16 — Pentesting Web](16-pentesting-web.md)*
