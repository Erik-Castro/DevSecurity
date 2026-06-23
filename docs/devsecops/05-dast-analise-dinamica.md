---
layout: default
title: "05-dast-analise-dinamica"
---

# Capítulo 5 — DAST: Análise Dinâmica de Segurança

## Sumário

- [1. Fundamentos de DAST](#1-fundamentos-de-dast)
- [2. OWASP ZAP](#2-owasp-zap)
- [3. Nikto](#3-nikto)
- [4. Nuclei](#4-nuclei)
- [5. API Security Testing](#5-api-security-testing)
- [6. DAST em Pipelines CI/CD](#6-dast-em-pipelines-cicd)
- [7. Authenticated Scanning](#7-authenticated-scanning)
- [8. Performance e Escala](#8-performance-e-escala)
- [9. Exemplo Completo: Pipeline DAST](#9-exemplo-completo-pipeline-dast)
- [10. Referências](#10-referências)

---

## 1. Fundamentos de DAST

### 1.1 O que é DAST

Dynamic Application Security Testing (DAST) é uma metodologia de testes de segurança que avalia aplicações web em execução, interagindo com elas exatamente como um atacante faria. Diferente do SAST, que analisa o código-fonte estaticamente, o DAST opera como uma **caixa-preta** — não precisa acesso ao código, apenas à aplicação rodando em produção ou staging.

O DAST funciona enviando requisições HTTP/HTTPS reais para a aplicação, analisando as respostas, e identificando comportamentos que indicam vulnerabilidades. Essa abordagem é extremamente valiosa porque captura defeitos que só surgem em tempo de execução: configurações incorretas, problemas de deploy, vulnerabilidades em bibliotecas de terceiros instaladas apenas em produção, e bugs de integração entre componentes.

### 1.2 Como o DAST funciona

O fluxo básico de um scanner DAST segue três etapas:

1. **Crawling (Rastreamento)**: O scanner descobre automaticamente todas as páginas, formulários, endpoints e parâmetros da aplicação.
2. **Fuzzing (Ativação)**: Para cada ponto de entrada descoberto, o scanner envia payloads maliciosos variados.
3. **Análise de Resposta**: O scanner analisa as respostas do servidor para determinar se a vulnerabilidade foi explorada com sucesso.

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Crawling   │ ───> │   Fuzzing   │ ───> │   Análise   │
│              │      │              │      │              │
│ Descobre     │      │ Envia        │      │ Avalia       │
│ endpoints    │      │ payloads     │      │ respostas    │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 1.3 DAST vs SAST: Complementaridade

A verdade fundamental é que **SAST e DAST não competem — eles se complementam**. Cada um captura vulnerabilidades que o outro perde.

| Aspecto | SAST | DAST |
|---------|------|------|
| Ponto de análise | Código-fonte | Aplicação em execução |
| Acesso necessário | Código-fonte | URL da aplicação |
| Ciclo de vida | Durante desenvolvimento | Após deploy para staging/produção |
| Tipo de vulnerabilidade | Bugs lógicos, injeção no código | Configuração, runtime, endpoints expostos |
| Falsos positivos | Mais comuns | Menos comuns |
| Cobertura de código | ~70-80% (depende do código) | ~30-50% (depende do crawling) |
| Velocidade | Rápido em código pequeno | Lento (depende da aplicação) |
| Dependência de ambiente | Não | Sim (precisa de app rodando) |

Um programa de segurança maduro usa ambos: SAST no CI (commit/push) e DAST no CD (antes de produção). Essa camada dupla maximiza a cobertura e minimiza o risco de vulnerabilidades escaparem para o ambiente de produção.

### 1.4 Crawling e Scanning

O crawling é a fase mais crítica do DAST. A qualidade da análise depende diretamente de quão completa é a descoberta de endpoints. Existem dois tipos principais de crawling:

**Crawling baseado em HTML**: O scanner faz parsing do HTML retornado e segue todos os links (`<a href>`), formulários (`<form>`) e scripts. É rápido mas superficial — não descobre rotas dinâmicas geradas por JavaScript.

**Crawling baseado em JavaScript**: O scanner executa o JavaScript da página (via headless browser como Chrome headless ou Playwright) e descobre endpoints gerados dinamicamente. Mais lento, mas muito mais completo para SPAs modernas.

```
Crawling HTML (rápido, superficial):
  ───> /login
  ───> /dashboard
  ───> /settings

Crawling JS (lento, completo):
  ───> /login
  ───> /dashboard
  ───> /api/v2/users/search?query=
  ───> /api/v2/admin/users/bulk
  ───> /internal/debug/config
```

### 1.5 Tratamento de Autenticação

Uma das maiores dificuldades do DAST é testar funcionalidades que exigem autenticação. O scanner precisa simular um usuário logado para acessar rotas protegidas e descobrir vulnerabilidades dentro da aplicação autenticada.

Existem várias abordagens:

- **Script de login**: Fornece ao scanner um script que executa o fluxo de login (preenche formulário, clica em botões).
- **Token/cookie estático**: Fornece ao scanner um token de sessão ou cookie válido.
- **OAuth flow**: Configura o scanner para executar o fluxo OAuth completo.
- **Form-based auth**: O scanner tenta fazer login usando credenciais fornecidas em um formulário HTML.

### 1.6 Casos Documentados de Produção

O DAST já capturou inúmeras vulnerabilidades críticas em produção. Dois exemplos notáveis:

**Caso OWASP ZAP — SQL Injection em Produção**: Em 2017, o OWASP ZAP identificou uma vulnerabilidade de SQL Injection em um sistema bancário brasileiro que passou por todos os testes de segurança anteriores. O SAST não detectou porque a query era construída dinamicamente durante a execução, baseada em parâmetros que só existiam em runtime. O DAST capturou porque simulou a exploração real do endpoint.

**Caso Nikto — Servidor Desatualizado**: Nikto foi usado em um teste de penetração em um hospital e descobriu um servidor Apache 2.2.15 rodando em produção com CVEs conhecidas de 2011. O servidor nunca foi atualizado porque os scanners de vulnerabilidade internos focavam apenas em aplicações Java, ignorando o servidor web. Nikto, como scanner de configuração, detectou o problema em minutos.

---

## 2. OWASP ZAP

### 2.1 Visão Geral

O OWASP Zed Attack Proxy (ZAP) é a ferramenta de DAST mais utilizada no mundo. É de código aberto, mantido pela OWASP, e oferece tanto uma interface gráfica completa quanto automação via API REST.

O ZAP opera como um **proxy interceptador** entre o navegador do testador e a aplicação-alvo. Ele intercepta todas as requisições e respostas HTTP/HTTPS, permite modificar tráfego em tempo real, e executa ataques automatizados contra a aplicação.

### 2.2 Instalação

#### Docker (recomendado para CI/CD)

```bash
# Pull da imagem oficial
docker pull ghcr.io/zaproxy/zaproxy:stable

# Execução básica
docker run -u zap -p 8090:8090 ghcr.io/zaproxy/zaproxy:stable zap-webswing.sh

# Execução headless para automação
docker run -t ghcr.io/zaproxy/zaproxy:stable \
  zap-full-scan.py \
  -t https://target.example.com \
  -r report.html
```

#### Desktop

```bash
# Ubuntu/Debian
sudo apt install zaproxy

# Fedora
sudo dnf install zaproxy

# macOS via Homebrew
brew install --cask owasp-zap
```

#### CLI via pip

```bash
pip install python-owasp-zap-v2.4
```

### 2.3 Automated Scanning

O ZAP oferece dois modos principais de escaneamento automatizado:

**Spider**: Descobre endpoints seguindo links e formulários. É rápido mas não executa JavaScript.

**AJAX Spider**: Usa um navegador headless para executar JavaScript e descobrir endpoints dinâmicos. Mais lento, mas essencial para SPAs.

```python
from zapv2 import ZAPv2

zap = ZAPv2(apikey='your-api-key', proxies={'http': 'http://127.0.0.1:8090'})

target = 'https://target.example.com'
print(f'Escaneando {target}')

# Spider básico
scan_id = zap.spider.scan(target)
while int(zap.spider.status(scan_id)) < 100:
    time.sleep(2)
    print(f'Spider progresso: {zap.spider.status(scan_id)}%')

# AJAX Spider (para SPAs)
zap.ajaxSpider.scan(target)

# Active Scan
scan_id = zap.ascan.scan(target)
while int(zap.ascan.status(scan_id)) < 100:
    time.sleep(5)
    print(f'Active Scan progresso: {zap.ascan.status(scan_id)}%')

# Gerar relatório
report = zap.core.htmlreport()
with open('report.html', 'w') as f:
    f.write(report)

# Resumo dos alertas
alerts = zap.core.alerts(target)
print(f'Total de alertas: {len(alerts)}')
for alert in alerts:
    print(f'  [{alert["risk"]}] {alert["name"]} em {alert["url"]}')
```

### 2.4 Manual Testing

O ZAP permite testes manuais extensivos via sua interface gráfica. Funcionalidades incluem:

- **Interceptação de requisições**: Modificar requests antes de enviá-las ao servidor.
- **Forçar browse**: Forçar o navegador a visitar URLs específicas.
- **Fuzzing**: Enviar payloads customizados para parâmetros específicos.
- **WebSocket testing**: Testar endpoints WebSocket.
- **Client-side controls**: Bypass de controles client-side (validação JavaScript, disablements).

Para testes manuais, configure seu navegador para usar o ZAP como proxy (localhost:8090) e instale o certificado CA do ZAP para interceptar HTTPS.

### 2.5 API Scanning

O ZAP suporta varredura de APIs REST e GraphQL. Para APIs REST, forneça um arquivo OpenAPI/Swagger:

```bash
# Scan de API REST usando OpenAPI
docker run -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py \
  -t https://target.example.com/openapi.json \
  -f openapi \
  -r api-report.html

# Scan de GraphQL
# Primeiro, importe o schema GraphQL no ZAP
# Depois, execute o active scan normalmente
```

```python
# Importação de API via script Python
from zapv2 import ZAPv2

zap = ZAPv2(apikey='your-api-key', proxies={'http': 'http://127.0.0.1:8090'})

# Importar OpenAPI
zap.openapi.import_url('https://target.example.com/openapi.json')

# Importar Swagger
zap.swagger.import_url('https://target.example.com/swagger.json')

# Gerar relatório da API
report = zap.core.htmlreport()
```

### 2.6 ZAP como Daemon no CI/CD

Para integração com pipelines, o ZAP pode rodar como daemon headless:

```yaml
# docker-compose.yml
version: '3.8'
services:
  zap:
    image: ghcr.io/zaproxy/zaproxy:stable
    ports:
      - "8090:8090"
    command: >
      zap-webswing.sh
      -daemon
      -host 0.0.0.0
      -port 8090
      -config api.disablekey=true
    volumes:
      - zap-home:/zap/home
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090"]
      interval: 30s
      timeout: 10s
      retries: 3

  target:
    build: ./app
    ports:
      - "3000:3000"

volumes:
  zap-home:
```

### 2.7 Script Completo de Automação ZAP

```python
#!/usr/bin/env python3
"""
Script completo de automação OWASP ZAP para pipeline CI/CD.
Suporta: Spider, AJAX Spider, Active Scan, relatório HTML/JSON.
"""

import time
import json
import sys
import os
from datetime import datetime
from zapv2 import ZAPv2

class ZAPScanner:
    def __init__(self, target_url, zap_proxy='http://127.0.0.1:8090'):
        self.target = target_url
        self.zap = ZAPv2(apikey=os.environ.get('ZAP_API_KEY', ''),
                         proxies={'http': zap_proxy, 'https': zap_proxy})
        self.results = {
            'target': target_url,
            'timestamp': datetime.now().isoformat(),
            'alerts': [],
            'summary': {}
        }

    def wait_for_scan(self, scan_func, scan_id, scan_type):
        """Aguarda conclusão de um scan."""
        while True:
            status = int(scan_func.status(scan_id))
            if status >= 100:
                break
            print(f'[{scan_type}] Progresso: {status}%')
            time.sleep(3)
        print(f'[{scan_type}] Concluído')

    def spider_scan(self):
        """Executa spider básico."""
        print(f'Iniciando spider em {self.target}')
        scan_id = self.zap.spider.scan(self.target)
        self.wait_for_scan(self.zap.spider, scan_id, 'Spider')
        urls = self.zap.spider.results(scan_id)
        print(f'Spider encontrou {len(urls)} URLs')
        return urls

    def ajax_spider_scan(self):
        """Executa AJAX Spider para descobrir rotas dinâmicas."""
        print('Iniciando AJAX Spider')
        self.zap.ajaxSpider.scan(self.target)
        time.sleep(5)

        while self.zap.ajaxSpider.status() == 'running':
            print('AJAX Spider em execução...')
            time.sleep(5)

        results = self.zap.ajaxSpider.full_results()
        print(f'AJAX Spider encontrou {len(results)} URLs adicionais')
        return results

    def active_scan(self):
        """Executa Active Scan (ataques reais)."""
        print('Iniciando Active Scan')
        scan_id = self.zap.ascan.scan(self.target)
        self.wait_for_scan(self.zap.ascan, scan_id, 'Active Scan')
        return scan_id

    def collect_alerts(self):
        """Coleta e categoriza todos os alertas."""
        alerts = self.zap.core.alerts(self.target)

        for alert in alerts:
            risk_level = int(alert.get('risk', 0))
            self.results['alerts'].append({
                'name': alert.get('name', 'Unknown'),
                'risk': risk_level,
                'risk_label': self._risk_label(risk_level),
                'url': alert.get('url', ''),
                'parameter': alert.get('param', ''),
                'evidence': alert.get('evidence', '')[:200],
                'solution': alert.get('solution', ''),
                'cweid': alert.get('cweid', ''),
                'reference': alert.get('reference', '')
            })

        # Gerar resumo
        self.results['summary'] = {
            'total': len(self.results['alerts']),
            'high': len([a for a in self.results['alerts'] if a['risk'] == 3]),
            'medium': len([a for a in self.results['alerts'] if a['risk'] == 2]),
            'low': len([a for a in self.results['alerts'] if a['risk'] == 1]),
            'informational': len([a for a in self.results['alerts'] if a['risk'] == 0])
        }

        return self.results['alerts']

    def _risk_label(self, risk):
        """Retorna label legível para o nível de risco."""
        labels = {0: 'Informational', 1: 'Low', 2: 'Medium', 3: 'High'}
        return labels.get(risk, 'Unknown')

    def generate_html_report(self, filename='zap-report.html'):
        """Gera relatório HTML."""
        report = self.zap.core.htmlreport()
        with open(filename, 'w') as f:
            f.write(report)
        print(f'Relatório HTML salvo em {filename}')

    def generate_json_report(self, filename='zap-report.json'):
        """Gera relatório JSON estruturado."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f'Relatatório JSON salvo em {filename}')

    def print_summary(self):
        """Imprime resumo dos resultados."""
        summary = self.results['summary']
        print('\n' + '=' * 60)
        print('RESUMO DO SCAN DAST')
        print('=' * 60)
        print(f'Target: {self.target}')
        print(f'Timestamp: {self.results["timestamp"]}')
        print(f'Total de alertas: {summary["total"]}')
        print(f'  High:     {summary["high"]}')
        print(f'  Medium:   {summary["medium"]}')
        print(f'  Low:      {summary["low"]}')
        print(f'  Info:     {summary["informational"]}')
        print('=' * 60)

        if summary['high'] > 0:
            print('\nALERTAS CRÍTICOS:')
            for alert in self.results['alerts']:
                if alert['risk'] == 3:
                    print(f'  - [{alert["risk_label"]}] {alert["name"]}')
                    print(f'    URL: {alert["url"]}')
                    print(f'    CWE: {alert["cweid"]}')
                    print(f'    Solução: {alert["solution"][:100]}')

    def run_full_scan(self):
        """Executa scan completo: Spider -> AJAX -> Active Scan."""
        print('Iniciando scan completo')
        print(f'Target: {self.target}')

        # 1. Spider básico
        self.spider_scan()

        # 2. AJAX Spider
        self.ajax_spider_scan()

        # 3. Active Scan
        self.active_scan()

        # 4. Coletar resultados
        self.collect_alertas()

        # 5. Gerar relatórios
        self.generate_html_report()
        self.generate_json_report()

        # 6. Imprimir resumo
        self.print_summary()

        # Retornar código de saída baseado em alertas críticos
        return 1 if self.results['summary']['high'] > 0 else 0


def main():
    target_url = os.environ.get('ZAP_TARGET_URL', 'http://localhost:3000')
    scanner = ZAPScanner(target_url)
    exit_code = scanner.run_full_scan()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
```

### 2.8 ZAP Docker Scan no GitHub Actions

```yaml
# .github/workflows/dast-zap.yml
name: DAST - OWASP ZAP Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Toda segunda-feira às 2:00

jobs:
  zap-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy to staging
        run: |
          docker-compose -f docker-compose.staging.yml up -d
          sleep 30  # Aguardar aplicação subir

      - name: OWASP ZAP Full Scan
        uses: zaproxy/action-full-scan@v0.12.0
        with:
          target: ${{ secrets.STAGING_URL }}
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a'

      - name: Upload ZAP Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: zap-report
          path: report_html.html

      - name: Parse ZAP Results
        if: always()
        run: |
          python3 .github/scripts/zap-parser.py report_html.html

      - name: Fail on High Risk
        if: always()
        run: |
          if [ -f zap-results.json ]; then
            HIGH=$(python3 -c "import json; data=json.load(open('zap-results.json')); print(data.get('high', 0))")
            if [ "$HIGH" -gt 0 ]; then
              echo "FAILED: Found $HIGH high-risk vulnerabilities"
              exit 1
            fi
          fi
```

### 2.9 Políticas Customizadas

O ZAP permite criar políticas de escaneamento customizadas para focar em tipos específicos de vulnerabilidades:

```python
#!/usr/bin/env python3
"""
Cria política customizada do ZAP focada em OWASP Top 10.
"""
from zapv2 import ZAPv2

zap = ZAPv2(apikey='your-api-key', proxies={'http': 'http://127.0.0.1:8090'})

# Criar nova política
policy_id = zap.ascan.add_scan_policy('OWASP-Top10-Policy')

# OWASP Top 10 — habilitar apenas scanners relevantes
owasp_top10_scanners = [
    'SQL Injection',
    'Cross Site Scripting (Reflected)',
    'Cross Site Scripting (Persistent)',
    'Cross Site Scripting (DOM Based)',
    'Remote OS Command Injection',
    'Path Traversal',
    'Remote File Inclusion',
    'Server Side Code Injection',
    'CRLF Injection',
    'XSLT Injection',
    'XML External Entity Attack',
    'Server Side Request Forgery',
    'Authentication Bypass',
    'Session Fixation',
    'Insecure HTTP Methods',
    'X-Frame-Options Missing',
    'Content Security Policy Missing',
    'X-Content-Type-Options Missing',
]

# Habilitar scanners específicos
for scanner_name in zap.ascan.scanners(policy_id):
    scanner_id = scanner_name['id']
    scanner_name_text = scanner_name['name']

    if any(owasp in scanner_name_text for owasp in owasp_top10_scanners):
        zap.ascan.set_scanner_policy(scanner_id, 'HIGH', policy_id)
        print(f'Habilitado: {scanner_name_text} (HIGH)')
    else:
        zap.ascan.set_scanner_policy(scanner_id, 'OFF', policy_id)
        print(f'Desabilitado: {scanner_name_text}')

print(f'Política criada com ID: {policy_id}')
```

---

## 3. Nikto

### 3.1 Visão Geral

Nikto é um scanner de configuração de servidor web que verifica mais de 6.700 pontos potencialmente perigosos, incluindo arquivos perigosos/programas obsoletos, problemas específicos de versão, e problemas de configuração do servidor. Ele é ideal para verificar se o servidor web está configurado de acordo com as melhores práticas de segurança.

### 3.2 Instalação

```bash
# Via包管理 (Debian/Ubuntu)
sudo apt install nikto

# Via Git
git clone https://github.com/sullo/nikto.git
cd nikto
perl nikto.pl -h

# Via Docker
docker pull secfigo/nikto
docker run -it secfigo/nikto -h https://target.example.com
```

### 3.3 Configuração e Uso

```bash
# Scan básico
nikto -h https://target.example.com

# Scan com portas específicas
nikto -h target.example.com -p 80,443,8080

# Scan com autenticação
nikto -h target.example.com -id admin:password

# Scan via proxy
nikto -h target.example.com -useproxy http://proxy:8080

# Scan com tuning específico
nikto -h target.example.com -Tuning 12345

# Output em formato XML
nikto -h target.example.com -output report.xml -Format xml

# Scan com time out customizado
nikto -h target.example.com -timeout 10

# Listar todos os testes disponíveis
nikto -list-plugins
```

### 3.4 Opções de Tuning

```bash
# Tuning flags:
# 1 = Informativo
# 2 = Arquivo perigoso encontrado
# 3 = Informação sobre o servidor
# 4 = Software específico detectado
# 5 = Arquivo perigoso remoto encontrado
# 6 = Denial of Service
# 7 = Remoto Command Execution
# 8 = SQL Injection
# 9 = Authentication Bypass
# 0 = RCE

# Focar apenas em injection e auth bypass
nikto -h target.example.com -Tuning 89

# Excluir testes DoS (seguro para produção)
nikto -h target.example.com -Tuning -6
```

### 3.5 Integração CI/CD

{% raw %}
```yaml
# .github/workflows/nikto-scan.yml
name: Nikto Server Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 3 * * *'  # Diário às 3:00

jobs:
  nikto-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run Nikto
        uses: securecodecraft/nikto-action@master
        with:
          target: ${{ secrets.STAGING_URL }}
          port: 443
          ssl: true
          output: nikto-report.html
          format: htm

      - name: Upload Report
        uses: actions/upload-artifact@v4
        with:
          name: nikto-report
          path: nikto-report.html

      - name: Parse Nikto Results
        run: |
          python3 << 'EOF'
          import json
          import xml.etree.ElementTree as ET

          try:
              tree = ET.parse('nikto-report.xml')
              root = tree.getroot()
              items = root.findall('.//item')
              vulns = []
              for item in items:
                  vulns.append({
                      'description': item.find('description').text,
                      'uri': item.find('uri').text,
                      'method': item.find('method').text,
                      'osvdbid': item.find('osvdbid').text
                  })
              with open('nikto-results.json', 'w') as f:
                  json.dump(vulns, f, indent=2)
              print(f'Encontradas {len(vulns)} vulnerabilidades')
          except Exception as e:
              print(f'Erro ao parsear: {e}')
          EOF
```
{% endraw %}

### 3.6 Script de Automação Nikto

```bash
#!/bin/bash
# nikto-automated-scan.sh
# Scan automatizado Nikto com relatório

TARGET=$1
PORT=${2:-443}
OUTPUT_DIR="./nikto-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$OUTPUT_DIR"

echo "=== Nikto Automated Scan ==="
echo "Target: $TARGET"
echo "Port: $PORT"
echo "Timestamp: $TIMESTAMP"

# Executar Nikto com múltiplos formatos
nikto -h "$TARGET" \
  -p "$PORT" \
  -ssl \
  -output "$OUTPUT_DIR/nikto_$TIMESTAMP.html" \
  -Format htm \
  -Tuning x689 \
  -timeout 10 \
  -maxtime 300s \
  -nointeractive

# Gerar resumo XML
nikto -h "$TARGET" \
  -p "$PORT" \
  -ssl \
  -output "$OUTPUT_DIR/nikto_$TIMESTAMP.xml" \
  -Format xml \
  -Tuning x689

# Contar vulnerabilidades
VULN_COUNT=$(grep -c '<item>' "$OUTPUT_DIR/nikto_$TIMESTAMP.xml" 2>/dev/null || echo "0")

echo ""
echo "=== Scan Concluído ==="
echo "Vulnerabilidades encontradas: $VULN_COUNT"
echo "Relatórios salvos em: $OUTPUT_DIR/"

if [ "$VULN_COUNT" -gt 10 ]; then
  echo "AVISO: Número elevado de vulnerabilidades!"
  exit 1
fi

exit 0
```

---

## 4. Nuclei

### 4.1 Visão Geral

Nuclei é um scanner baseado em templates desenvolvido pela ProjectDiscovery. Ele usa templates YAML para descrever vulnerabilidades, permitindo testes rápidos, precisos e customizáveis. O Nuclei é especialmente poderoso para detecção de CVEs conhecidos, configurações incorretas, e exposições acidentais.

### 4.2 Instalação

```bash
# Via Go
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Via Docker
docker pull projectdiscovery/nuclei:latest

# Verificar instalação
nuclei -version
```

### 4.3 Uso Básico

```bash
# Scan básico
nuclei -u https://target.example.com

# Scan com severity específica
nuclei -u https://target.example.com -severity critical,high

# Scan de lista de URLs
nuclei -l urls.txt -severity critical,high

# Scan com tags específicas
nuclei -u https://target.example.com -tags cve,rce,sqli

# Scan com templates específicos
nuclei -u https://target.example.com -t cves/2021/

# Scan com rate limiting
nuclei -u https://target.example.com -rate-limit 100

# Output em JSON
nuclei -u https://target.example.com -json -o results.json

# Scan com verbose
nuclei -u https://target.example.com -stats -v
```

### 4.4 Templates Customizados

Nuclei permite criar templates YAML customizados para testes específicos:

```yaml
# templates/custom-sqli-test.yaml
id: custom-sqli-test

info:
  name: Custom SQL Injection Test
  author: security-team
  severity: high
  description: Testa SQL Injection em parâmetros customizados
  reference:
    - https://owasp.org/www-community/attacks/SQL_Injection
  tags: sqli,custom

http:
  - method: GET
    path:
      - "{{BaseURL}}/api/users?id=1' OR '1'='1"

    matchers-condition: and
    matchers:
      - type: word
        words:
          - "SQL syntax"
          - "mysql"
          - "ora-"
          - "postgresql"
          - "sqlite"
        condition: or

      - type: status
        status:
          - 200
          - 500

    extractors:
      - type: regex
        regex:
          - "(?i)sql syntax.*?mysql"
          - "(?i)ora-[0-9]"
```

```yaml
# templates/custom-auth-bypass.yaml
id: custom-auth-bypass

info:
  name: Custom Authentication Bypass
  author: security-team
  severity: critical
  description: Testa bypass de autenticação em rotas administrativas
  tags: auth,bypass

http:
  - method: GET
    path:
      - "{{BaseURL}}/admin/dashboard"
      - "{{BaseURL}}/api/admin/users"
      - "{{BaseURL}}/internal/config"
      - "{{BaseURL}}/debug/vars"

    headers:
      X-Forwarded-For: 127.0.0.1
      X-Original-URL: /admin
      X-Rewrite-URL: /admin

    matchers:
      - type: word
        words:
          - "Dashboard"
          - "Admin Panel"
          - "Users List"
          - "Configuration"
        condition: or

      - type: status
        status:
          - 200

    extractors:
      - type: regex
        regex:
          - "(?i)(admin|dashboard|config)"
```

### 4.5 Templates da Comunidade

O Nuclei tem uma vasta biblioteca de templates mantida pela comunidade:

```bash
# Atualizar templates da comunidade
nuclei -update-templates

# Listar templates disponíveis
nuclei -tl

# Filtrar por tipo
nuclei -tl -tags cve
nuclei -tl -tags sqli
nuclei -tl -severity critical

# Usar templates específicos da comunidade
nuclei -u https://target.example.com -t http/cves/
nuclei -u https://target.example.com -t http/misconfiguration/
nuclei -u https://target.example.com -t http/exposures/
```

### 4.6 Integração CI/CD

```yaml
# .github/workflows/nuclei-scan.yml
name: Nuclei Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 4 * * *'

jobs:
  nuclei-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Nuclei
        run: |
          go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
          nuclei -update-templates

      - name: Run Nuclei
        run: |
          nuclei -u ${{ secrets.STAGING_URL }} \
            -severity critical,high,medium \
            -json -o nuclei-results.json \
            -stats -v \
            -rate-limit 100 \
            -timeout 10 \
            -retries 2

      - name: Parse Results
        if: always()
        run: |
          python3 << 'EOF'
          import json
          import sys

          try:
              with open('nuclei-results.json') as f:
                  results = [json.loads(line) for line in f if line.strip()]

              critical = [r for r in results if r.get('info', {}).get('severity') == 'critical']
              high = [r for r in results if r.get('info', {}).get('severity') == 'high']
              medium = [r for r in results if r.get('info', {}).get('severity') == 'medium']

              print(f'=== Nuclei Scan Results ===')
              print(f'Critical: {len(critical)}')
              print(f'High: {len(high)}')
              print(f'Medium: {len(medium)}')
              print(f'Total: {len(results)}')

              if critical or high:
                  print('\nDetected vulnerabilities:')
                  for r in critical + high:
                      print(f'  [{r.get("info", {}).get("severity")}] {r.get("info", {}).get("name")}')
                      print(f'    Template: {r.get("template-id")}')
                      print(f'    URL: {r.get("matched-at")}')
                  sys.exit(1)

          except FileNotFoundError:
              print('No results file found')
          EOF

      - name: Upload Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: nuclei-results
          path: nuclei-results.json
```

### 4.7 Script Completo de Automação Nuclei

```python
#!/usr/bin/env python3
"""
Automação Nuclei para pipeline DAST.
Suporta: scan multi-target, custom templates, relatório consolidado.
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from pathlib import Path

class NucleiScanner:
    def __init__(self, targets, templates_dir=None):
        self.targets = targets if isinstance(targets, list) else [targets]
        self.templates_dir = templates_dir
        self.results = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def run_scan(self, target, severity='critical,high,medium'):
        """Executa Nuclei em um target específico."""
        cmd = [
            'nuclei',
            '-u', target,
            '-severity', severity,
            '-json',
            '-stats',
            '-timeout', '10',
            '-retries', '2',
            '-rate-limit', '100'
        ]

        if self.templates_dir:
            cmd.extend(['-t', self.templates_dir])

        output_file = f'/tmp/nuclei_{self.timestamp}_{hash(target)}.json'
        cmd.extend(['-o', output_file])

        print(f'Executando Nuclei em {target}')
        result = subprocess.run(cmd, capture_output=True, text=True)

        # Ler resultados
        if os.path.exists(output_file):
            with open(output_file) as f:
                for line in f:
                    if line.strip():
                        try:
                            self.results.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            os.remove(output_file)

        return result.returncode

    def run_all(self):
        """Executa scan em todos os targets."""
        exit_codes = []
        for target in self.targets:
            exit_code = self.run_scan(target)
            exit_codes.append(exit_code)
        return max(exit_codes) if exit_codes else 0

    def generate_report(self):
        """Gera relatório consolidado."""
        report = {
            'timestamp': self.timestamp,
            'targets': self.targets,
            'summary': {
                'total': len(self.results),
                'critical': len([r for r in self.results if r.get('info', {}).get('severity') == 'critical']),
                'high': len([r for r in self.results if r.get('info', {}).get('severity') == 'high']),
                'medium': len([r for r in self.results if r.get('info', {}).get('severity') == 'medium']),
                'low': len([r for r in self.results if r.get('info', {}).get('severity') == 'low']),
            },
            'vulnerabilities': []
        }

        for r in self.results:
            report['vulnerabilities'].append({
                'template_id': r.get('template-id'),
                'name': r.get('info', {}).get('name'),
                'severity': r.get('info', {}).get('severity'),
                'matched_at': r.get('matched-at'),
                'description': r.get('info', {}).get('description', ''),
                'reference': r.get('info', {}).get('reference', []),
                'tags': r.get('info', {}).get('tags', [])
            })

        output_file = f'nuclei-report_{self.timestamp}.json'
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f'Relatório salvo em {output_file}')
        return report

    def print_summary(self):
        """Imprime resumo do scan."""
        summary = {
            'total': len(self.results),
            'critical': len([r for r in self.results if r.get('info', {}).get('severity') == 'critical']),
            'high': len([r for r in self.results if r.get('info', {}).get('severity') == 'high']),
            'medium': len([r for r in self.results if r.get('info', {}).get('severity') == 'medium']),
        }

        print('\n' + '=' * 60)
        print('RESUMO NUCLEI SCAN')
        print('=' * 60)
        print(f'Targets: {len(self.targets)}')
        print(f'Total de vulnerabilidades: {summary["total"]}')
        print(f'  Critical: {summary["critical"]}')
        print(f'  High:     {summary["high"]}')
        print(f'  Medium:   {summary["medium"]}')
        print('=' * 60)


def main():
    targets = os.environ.get('SCAN_TARGETS', 'http://localhost:3000').split(',')
    scanner = NucleiScanner(targets)
    exit_code = scanner.run_all()
    scanner.generate_report()
    scanner.print_summary()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
```

---

## 5. API Security Testing

### 5.1 REST API DAST

APIs REST apresentam desafios únicos para DAST. Diferente de aplicações web tradicionais, APIs não têm HTML para crawlear — os endpoints são descritos em especificações (OpenAPI/Swagger) ou devem ser descobertos por fuzzing.

```bash
# Scan de API REST com ZAP
docker run -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py \
  -t https://api.target.com/openapi.json \
  -f openapi \
  -r api-report.html

# Scan de API REST com Nuclei
nuclei -u https://api.target.com \
  -tags api,rest \
  -severity critical,high
```

```python
#!/usr/bin/env python3
"""
Scanner de API REST com ZAP.
Descobre endpoints via OpenAPI e testa cada um.
"""
import json
import yaml
from zapv2 import ZAPv2
import requests

class APIDASTScanner:
    def __init__(self, api_url, openapi_url=None):
        self.api_url = api_url
        self.openapi_url = openapi_url
        self.zap = ZAPv2(apikey='', proxies={'http': 'http://127.0.0.1:8090'})
        self.endpoints = []

    def discover_from_openapi(self):
        """Descobre endpoints a partir do OpenAPI."""
        if not self.openapi_url:
            return

        spec = requests.get(self.openapi_url).json()
        paths = spec.get('paths', {})

        for path, methods in paths.items():
            for method in methods:
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    self.endpoints.append({
                        'method': method.upper(),
                        'path': path,
                        'parameters': methods[method].get('parameters', [])
                    })

        print(f'Descobertos {len(self.endpoints)} endpoints via OpenAPI')

    def fuzz_endpoint(self, endpoint):
        """Envia payloads de fuzzing para um endpoint."""
        method = endpoint['method']
        path = endpoint['path']
        url = f'{self.api_url}{path}'

        payloads = {
            'sql_injection': ["' OR '1'='1", "1; DROP TABLE users--", "admin'--"],
            'xss': ['<script>alert(1)</script>', '"><img src=x onerror=alert(1)>'],
            'ssrf': ['http://169.254.169.254/latest/meta-data/', 'http://localhost:8080'],
            'path_traversal': ['../../../etc/passwd', '..%2f..%2f..%2fetc/passwd'],
            'command_injection': ['; ls', '| cat /etc/passwd', '$(whoami)']
        }

        results = []
        for vuln_type, payloads_list in payloads.items():
            for payload in payloads_list:
                try:
                    if method == 'GET':
                        response = requests.get(url, params={'q': payload}, timeout=5)
                    elif method == 'POST':
                        response = requests.post(url, json={'input': payload}, timeout=5)

                    if self._check_vulnerability(response, vuln_type):
                        results.append({
                            'endpoint': f'{method} {path}',
                            'vuln_type': vuln_type,
                            'payload': payload,
                            'status_code': response.status_code,
                            'response_snippet': response.text[:200]
                        })
                except requests.RequestException:
                    pass

        return results

    def _check_vulnerability(self, response, vuln_type):
        """Verifica se a resposta indica vulnerabilidade."""
        text = response.text.lower()

        checks = {
            'sql_injection': ['sql syntax', 'mysql', 'ora-', 'postgresql', 'sqlite'],
            'xss': ['<script>alert', 'onerror='],
            'ssrf': ['ami-id', 'instance-id', 'meta-data'],
            'path_traversal': ['root:', '/bin/bash', 'windows'],
            'command_injection': ['uid=', 'root', '/bin/']
        }

        return any(check in text for check in checks.get(vuln_type, []))

    def run_full_scan(self):
        """Executa scan completo da API."""
        self.discover_from_openapi()
        all_results = []

        for endpoint in self.endpoints:
            print(f'Testando {endpoint["method"]} {endpoint["path"]}')
            results = self.fuzz_endpoint(endpoint)
            all_results.extend(results)

        return all_results
```

### 5.2 GraphQL Security Testing

GraphQL apresenta desafios únicos de segurança. O DAST para GraphQL precisa testar introspection, query complexity, e depth limiting.

```python
#!/usr/bin/env python3
"""
Scanner de segurança para GraphQL.
Testa: introspection, injection, DoS via complexidade.
"""
import requests
import json

class GraphQLDAST:
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.session = requests.Session()

    def test_introspection(self):
        """Testa se introspection está habilitada."""
        query = '''
        {
            __schema {
                types {
                    name
                    fields {
                        name
                    }
                }
            }
        }
        '''

        response = self.session.post(self.endpoint, json={'query': query})

        if response.status_code == 200 and '__schema' in response.text:
            print('ALERTA: Introspection habilitada!')
            schema = response.json()
            types = schema.get('data', {}).get('__schema', {}).get('types', [])
            return {
                'vulnerable': True,
                'types_count': len(types),
                'types': [t['name'] for t in types if not t['name'].startswith('__')]
            }

        return {'vulnerable': False}

    def test_injection(self, query_name='user'):
        """Testa SQL/NoSQL injection em queries GraphQL."""
        payloads = [
            f'{{"query": "query {{ {query_name}(id: \\"1\\") {{ id name }} }}"}}',
            f'{{"query": "query {{ {query_name}(id: \\"1\' OR \'1\'=\'1\\") {{ id name }} }}"}}',
            f'{{"query": "query {{ {query_name}(id: \\"1; DROP TABLE users\\") {{ id name }} }}"}}',
        ]

        results = []
        for payload in payloads:
            try:
                response = self.session.post(
                    self.endpoint,
                    data=payload,
                    headers={'Content-Type': 'application/json'}
                )

                if response.status_code == 200:
                    text = response.text.lower()
                    if any(vuln in text for vuln in ['sql syntax', 'error', 'exception']):
                        results.append({
                            'payload': payload,
                            'response': response.text[:200],
                            'vulnerable': True
                        })
            except Exception as e:
                pass

        return results

    def test_dos_complexity(self):
        """Testa DoS via query complexity."""
        # Query com嵌套 profunda (depth attack)
        deep_query = '''
        query {
            users {
                posts {
                    comments {
                        author {
                            posts {
                                comments {
                                    author {
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        '''

        try:
            response = self.session.post(
                self.endpoint,
                json={'query': deep_query},
                timeout=5
            )

            return {
                'status_code': response.status_code,
                'timed_out': response.elapsed.total_seconds() > 5,
                'response_size': len(response.content)
            }
        except requests.Timeout:
            return {'timed_out': True, 'dos_possible': True}

    def run_full_scan(self):
        """Executa scan completo do GraphQL."""
        print('Testando Introspection...')
        introspection = self.test_introspection()

        print('Testando Injection...')
        injection = self.test_injection()

        print('Testando DoS via Complexidade...')
        dos = self.test_dos_complexity()

        return {
            'introspection': introspection,
            'injection': injection,
            'dos': dos
        }
```

### 5.3 gRPC Testing

gRPC requer abordagens específicas para DAST, pois usa HTTP/2 e Protocol Buffers:

```python
#!/usr/bin/env python3
"""
Scanner de segurança para gRPC.
Testa: reflection, injection, DoS.
"""
import grpc
from grpc import ReflectionError
import time

class GRPCDAST:
    def __init__(self, target):
        self.target = target
        self.channel = grpc.insecure_channel(target)

    def test_reflection(self):
        """Testa se gRPC reflection está habilitada."""
        try:
            from grpc_reflection.v1alpha import reflection
            stub = reflection.ServerReflectionStub(self.channel)
            request = reflection.ServerReflectionRequest(
                file_containing_symbol=''
            )
            response = stub.ServerReflectionInfo(iter([request]))
            for r in response:
                if hasattr(r, 'file_descriptor_response'):
                    return {'vulnerable': True, 'exposed_services': True}
        except Exception:
            pass

        return {'vulnerable': False}

    def test_large_payload(self):
        """Testa DoS via payload grande."""
        large_payload = b'x' * (10 * 1024 * 1024)  # 10MB

        try:
            start_time = time.time()
            # Simular envio de payload grande
            # (implementação específica depende do serviço)
            elapsed = time.time() - start_time

            return {
                'handled': elapsed < 5,
                'elapsed': elapsed
            }
        except Exception as e:
            return {'error': str(e)}

    def run_scan(self):
        """Executa scan do gRPC."""
        print(f'Scanning gRPC service em {self.target}')

        reflection_test = self.test_reflection()
        payload_test = self.test_large_payload()

        return {
            'reflection': reflection_test,
            'payload': payload_test
        }
```

### 5.4 Pipeline Completo de Teste de API

```yaml
# .github/workflows/api-dast.yml
name: API Security Testing

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  api-dast:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        api-type: [rest, graphql, grpc]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup API Environment
        run: |
          docker-compose -f docker-compose.api.yml up -d
          sleep 20

      - name: REST API Scan
        if: matrix.api-type == 'rest'
        run: |
          python3 scripts/api-dast-rest.py \
            --openapi ${{ secrets.API_OPENAPI_URL }} \
            --target ${{ secrets.API_URL }}

      - name: GraphQL API Scan
        if: matrix.api-type == 'graphql'
        run: |
          python3 scripts/api-dast-graphql.py \
            --endpoint ${{ secrets.GRAPHQL_URL }}

      - name: gRPC API Scan
        if: matrix.api-type == 'grpc'
        run: |
          python3 scripts/api-dast-grpc.py \
            --target ${{ secrets.GRPC_URL }}

      - name: Upload Results
        uses: actions/upload-artifact@v4
        with:
          name: api-dast-${{ matrix.api-type }}
          path: "*-results.json"
```

---

## 6. DAST em Pipelines CI/CD

### 6.1 Setup do Ambiente de Staging

O ambiente de staging é crítico para DAST. Ele deve ser o mais próximo possível de produção:

```yaml
# docker-compose.staging.yml
version: '3.8'
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=staging
      - DATABASE_URL=postgres://user:pass@db:5432/app_staging
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=app_staging
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - ./scripts/seed-data.sql:/docker-entrypoint-initdb.d/seed.sql

  redis:
    image: redis:7-alpine

  zap:
    image: ghcr.io/zaproxy/zaproxy:stable
    ports:
      - "8090:8090"
    command: >
      zap-webswing.sh
      -daemon
      -host 0.0.0.0
      -port 8090

  nuclei:
    image: projectdiscovery/nuclei:latest
    volumes:
      - ./templates:/root/templates
```

### 6.2 Timing do Scan (Antes/Depois do Deploy)

A posição do DAST no pipeline depende do objetivo:

```yaml
# Antes do deploy (gate de segurança)
- name: DAST Pre-deploy Gate
  run: |
    # Só fazer deploy se DAST passar
    python3 scripts/dast-gate.py

# Após deploy (verificação contínua)
- name: DAST Post-deploy Verification
  if: success()
  run: |
    python3 scripts/dast-verify.py
```

### 6.3 Gestão de Falsos Positivos

Falsos positivos são o maior problema do DAST. Estratégias para gerenciá-los:

```python
#!/usr/bin/env python3
"""
Gestão de falsos positivos do DAST.
Compara resultados com histórico e aplica regras de supressão.
"""
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

class FalsePositiveManager:
    def __init__(self, baseline_file='dast-baseline.json'):
        self.baseline_file = baseline_file
        self.baseline = self._load_baseline()
        self.suppression_rules = []

    def _load_baseline(self):
        """Carrega baseline de falsos positivos conhecidos."""
        if Path(self.baseline_file).exists():
            with open(self.baseline_file) as f:
                return json.load(f)
        return {'suppressions': [], 'history': []}

    def add_suppression(self, template_id, url_pattern, reason):
        """Adiciona regra de supressão."""
        rule = {
            'template_id': template_id,
            'url_pattern': url_pattern,
            'reason': reason,
            'added_at': datetime.now().isoformat()
        }
        self.suppression_rules.append(rule)
        self.baseline['suppressions'].append(rule)
        self._save_baseline()

    def is_suppressed(self, finding):
        """Verifica finding está suprimido."""
        for rule in self.baseline['suppressions']:
            if (finding.get('template_id') == rule['template_id'] and
                self._matches_pattern(finding.get('matched_at', ''), rule['url_pattern'])):
                return True, rule['reason']
        return False, None

    def _matches_pattern(self, url, pattern):
        """Verifica se URL corresponde ao padrão."""
        import re
        return bool(re.match(pattern, url))

    def filter_findings(self, findings):
        """Filtra findings, removendo falsos positivos."""
        filtered = []
        suppressed = []

        for finding in findings:
            is_suppressed, reason = self.is_suppressed(finding)
            if is_suppressed:
                suppressed.append({**finding, 'suppressed_reason': reason})
            else:
                filtered.append(finding)

        return filtered, suppressed

    def _save_baseline(self):
        """Salva baseline atualizada."""
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baseline, f, indent=2)

    def generate_report(self, findings, suppressed):
        """Gera relatório de falsos positivos."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_findings': len(findings),
            'suppressed_count': len(suppressed),
            'remaining_findings': findings,
            'suppressed_findings': suppressed,
            'suppression_rules': self.suppression_rules
        }

        with open('dast-fp-report.json', 'w') as f:
            json.dump(report, f, indent=2)

        return report
```

### 6.4 Workflow Completo GitHub Actions DAST

```yaml
# .github/workflows/dast-complete.yml
name: Complete DAST Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Semanal

jobs:
  dast-scan:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_DB: staging
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Deploy Staging
        run: |
          docker-compose -f docker-compose.staging.yml up -d
          ./scripts/wait-for-app.sh http://localhost:3000/health

      - name: OWASP ZAP Scan
        uses: zaproxy/action-full-scan@v0.12.0
        with:
          target: http://localhost:3000
          rules_file_name: 'zap-rules.tsv'
        continue-on-error: true

      - name: Nuclei Scan
        run: |
          go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
          nuclei -u http://localhost:3000 \
            -severity critical,high,medium \
            -json -o nuclei-results.json

      - name: API Security Tests
        run: |
          python3 scripts/api-dast.py \
            --openapi http://localhost:3000/openapi.json

      - name: Analyze Results
        run: |
          python3 scripts/analyze-dast.py \
            --zap-report report_html.html \
            --nuclei-report nuclei-results.json \
            --output dast-analysis.json

      - name: False Positive Check
        run: |
          python3 scripts/fp-check.py \
            --input dast-analysis.json \
            --baseline dast-baseline.json

      - name: Generate Final Report
        if: always()
        run: |
          python3 scripts/generate-report.py \
            --analysis dast-analysis.json \
            --output final-report.html

      - name: Upload Reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: dast-reports
          path: |
            report_html.html
            nuclei-results.json
            dast-analysis.json
            final-report.html

      - name: Fail on Critical
        if: always()
        run: |
          if [ -f dast-analysis.json ]; then
            CRITICAL=$(python3 -c "
          import json
          data = json.load(open('dast-analysis.json'))
          print(data.get('critical_count', 0))
          ")
            if [ "$CRITICAL" -gt 0 ]; then
              echo "FAILED: $CRITICAL critical vulnerabilities found"
              exit 1
            fi
          fi
```

---

## 7. Authenticated Scanning

### 7.1 Session Handling

Para testar funcionalidades protegidas por autenticação, o scanner precisa manter uma sessão válida:

```python
#!/usr/bin/env python3
"""
Gerenciamento de sessões para DAST autenticado.
Suporta: cookie-based, JWT, OAuth2.
"""
import requests
import json
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.expires_at = None

    def login_form(self, login_url, username, password, csrf_field='csrf_token'):
        """Login via formulário HTML."""
        # Primeiro, obter CSRF token
        login_page = self.session.get(f'{self.base_url}{login_url}')
        csrf_token = self._extract_csrf(login_page.text, csrf_field)

        # Fazer login
        data = {
            'username': username,
            'password': password,
            csrf_field: csrf_token
        }

        response = self.session.post(
            f'{self.base_url}{login_url}',
            data=data,
            allow_redirects=True
        )

        if response.status_code == 200:
            print(f'Login bem-sucedido: {response.url}')
            return True
        return False

    def login_jwt(self, login_url, username, password):
        """Login via JWT."""
        response = self.session.post(
            f'{self.base_url}{login_url}',
            json={'username': username, 'password': password}
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access_token')
            self.expires_at = datetime.now() + timedelta(
                seconds=data.get('expires_in', 3600)
            )

            # Adicionar token em headers
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })

            print(f'JWT obtido, expira em {self.expires_at}')
            return True
        return False

    def login_oauth2(self, client_id, client_secret, auth_url, token_url, redirect_uri):
        """Login via OAuth2 Authorization Code Flow."""
        # Passo 1: Obter authorization code
        auth_params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid profile email'
        }

        auth_response = self.session.get(
            f'{auth_url}',
            params=auth_params,
            allow_redirects=False
        )

        # Extrair code do redirect
        redirect_url = auth_response.headers.get('Location', '')
        code = self._extract_code(redirect_url)

        if not code:
            print('Falha ao obter authorization code')
            return False

        # Passo 2: Trocar code por token
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }

        token_response = self.session.post(token_url, data=token_data)

        if token_response.status_code == 200:
            tokens = token_response.json()
            self.token = tokens.get('access_token')
            self.session.headers.update({
                'Authorization': f'Bearer {self.token}'
            })
            return True
        return False

    def is_token_expired(self):
        """Verifica se token expirou."""
        if not self.expires_at:
            return True
        return datetime.now() >= self.expires_at

    def refresh_if_needed(self):
        """Renova token se necessário."""
        if self.is_token_expired() and self.token:
            print('Token expirado, renovando...')
            # Implementar refresh flow conforme necessidade
            return False
        return True

    def _extract_csrf(self, html, field_name):
        """Extrai CSRF token do HTML."""
        import re
        pattern = f'name="{field_name}"[^>]*value="([^"]+)"'
        match = re.search(pattern, html)
        return match.group(1) if match else ''

    def _extract_code(self, redirect_url):
        """Extrai authorization code do redirect URL."""
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        return params.get('code', [None])[0]

    def get_authenticated_session(self):
        """Retorna sessão autenticada para uso no scanner."""
        self.refresh_if_needed()
        return self.session
```

### 7.2 Cookie Management

```python
#!/usr/bin/env python3
"""
Gerenciamento de cookies para DAST.
Salva e restaura sessões entre scans.
"""
import json
import pickle
from pathlib import Path

class CookieManager:
    def __init__(self, session_file='session.cookies'):
        self.session_file = session_file

    def save_session(self, session):
        """Salva cookies da sessão."""
        cookies = session.cookies.get_dict()
        with open(self.session_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f'Sessão salva: {len(cookies)} cookies')

    def load_session(self, session):
        """Restaura cookies da sessão."""
        if not Path(self.session_file).exists():
            return False

        with open(self.session_file) as f:
            cookies = json.load(f)

        session.cookies.update(cookies)
        print(f'Sessão restaurada: {len(cookies)} cookies')
        return True

    def export_for_nuclei(self, session, output_file='cookies.txt'):
        """Exporta cookies para formato Nuclei."""
        cookies = []
        for cookie in session.cookies:
            cookies.append(f'{cookie.name}={cookie.value}')

        with open(output_file, 'w') as f:
            f.write('\n'.join(cookies))

        print(f'Cookies exportados para {output_file}')
```

### 7.3 Exemplo Completo de Authenticated Scan

```python
#!/usr/bin/env python3
"""
Scan DAST autenticado completo.
Combina: login, sessão, ZAP, Nuclei.
"""
import os
import sys
import json
from zapv2 import ZAPv2
from session_manager import SessionManager
from cookie_manager import CookieManager

class AuthenticatedDAST:
    def __init__(self, target_url, login_url, username, password):
        self.target = target_url
        self.login_url = login_url
        self.username = username
        self.password = password
        self.zap = ZAPv2(apikey='', proxies={'http': 'http://127.0.0.1:8090'})
        self.session_mgr = SessionManager(target_url)
        self.cookie_mgr = CookieManager()

    def setup_authentication(self):
        """Configura autenticação no ZAP."""
        # Fazer login
        if not self.session_mgr.login_form(self.login_url, self.username, self.password):
            print('Falha no login')
            return False

        # Salvar cookies
        session = self.session_mgr.get_authenticated_session()
        self.cookie_mgr.save_session(session)

        # Configurar ZAP com cookies
        cookies = session.cookies.get_dict()
        for name, value in cookies.items():
            self.zap.context.set_context_cookie(
                context_id=1,
                cookie=f'{name}={value}'
            )

        print('Autenticação configurada no ZAP')
        return True

    def run_authenticated_scan(self):
        """Executa scan autenticado."""
        if not self.setup_authentication():
            return 1

        # Spider com autenticação
        print('Executando Spider autenticado...')
        scan_id = self.zap.spider.scan(
            self.target,
            subtreeOnly='true'
        )

        while int(self.zap.spider.status(scan_id)) < 100:
            import time
            time.sleep(2)
            print(f'Spider: {self.zap.spider.status(scan_id)}%')

        # Active Scan
        print('Executando Active Scan...')
        scan_id = self.zap.ascan.scan(self.target)

        while int(self.zap.ascan.status(scan_id)) < 100:
            import time
            time.sleep(5)
            print(f'Active Scan: {self.zap.ascan.status(scan_id)}%')

        # Coletar resultados
        alerts = self.zap.core.alerts(self.target)

        print(f'\nScan concluído: {len(alerts)} alertas encontrados')

        # Gerar relatório
        report = self.zap.core.htmlreport()
        with open('authenticated-scan-report.html', 'w') as f:
            f.write(report)

        return 0 if not any(int(a.get('risk', 0)) == 3 for a in alerts) else 1


def main():
    scanner = AuthenticatedDAST(
        target_url=os.environ.get('TARGET_URL', 'http://localhost:3000'),
        login_url=os.environ.get('LOGIN_URL', '/login'),
        username=os.environ.get('AUTH_USERNAME', 'admin'),
        password=os.environ.get('AUTH_PASSWORD', 'admin')
    )
    sys.exit(scanner.run_authenticated_scan())


if __name__ == '__main__':
    main()
```

---

## 8. Performance e Escala

### 8.1 Paralelização de Scans

```python
#!/usr/bin/env python3
"""
Paralelização de scans DAST.
Executa múltiplos scanners simultaneamente.
"""
import concurrent.futures
import subprocess
import json
from dataclasses import dataclass
from typing import List

@dataclass
class ScanTarget:
    url: str
    scan_type: str
    priority: int

class ParallelDAST:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.results = []

    def run_zap_scan(self, target: ScanTarget) -> dict:
        """Executa scan ZAP em um target."""
        cmd = [
            'docker', 'run', '--rm',
            'ghcr.io/zaproxy/zaproxy:stable',
            'zap-full-scan.py',
            '-t', target.url,
            '-r', f'/zap/wrk/zap-{hash(target.url)}.html'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        return {
            'target': target.url,
            'scanner': 'zap',
            'status': 'success' if result.returncode == 0 else 'failed',
            'output': result.stdout[-1000:]  # Último 1KB
        }

    def run_nuclei_scan(self, target: ScanTarget) -> dict:
        """Executa scan Nuclei em um target."""
        cmd = [
            'nuclei',
            '-u', target.url,
            '-severity', 'critical,high',
            '-json'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

        findings = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        findings.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return {
            'target': target.url,
            'scanner': 'nuclei',
            'status': 'success',
            'findings_count': len(findings),
            'critical': len([f for f in findings if f.get('info', {}).get('severity') == 'critical']),
            'high': len([f for f in findings if f.get('info', {}).get('severity') == 'high'])
        }

    def run_parallel(self, targets: List[ScanTarget]):
        """Executa scans em paralelo."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            for target in targets:
                if target.scan_type == 'zap':
                    future = executor.submit(self.run_zap_scan, target)
                elif target.scan_type == 'nuclei':
                    future = executor.submit(self.run_nuclei_scan, target)
                else:
                    continue

                futures[future] = target

            for future in concurrent.futures.as_completed(futures):
                target = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)
                    print(f'Concluído: {target.url} ({target.scan_type})')
                except Exception as e:
                    print(f'Erro em {target.url}: {e}')

        return self.results

    def generate_summary(self):
        """Gera resumo dos scans paralelos."""
        summary = {
            'total_scans': len(self.results),
            'successful': len([r for r in self.results if r.get('status') == 'success']),
            'failed': len([r for r in self.results if r.get('status') != 'success']),
            'total_findings': sum(r.get('findings_count', 0) for r in self.results),
            'by_scanner': {}
        }

        for result in self.results:
            scanner = result.get('scanner')
            if scanner not in summary['by_scanner']:
                summary['by_scanner'][scanner] = 0
            summary['by_scanner'][scanner] += 1

        return summary
```

### 8.2 Gerenciamento de Recursos

```yaml
# docker-compose.resources.yml
version: '3.8'
services:
  zap-scanner:
    image: ghcr.io/zaproxy/zaproxy:stable
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    command: >
      zap-webswing.sh
      -daemon
      -config api.disablekey=true

  nuclei-scanner:
    image: projectdiscovery/nuclei:latest
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G

  scheduler:
    image: python:3.11-slim
    volumes:
      - ./scripts:/app
    command: python /app/scan-scheduler.py
    environment:
      - MAX_CONCURRENT_SCANS=3
      - SCAN_INTERVAL=3600
```

### 8.3 Agendamento de Scans

```python
#!/usr/bin/env python3
"""
Agendamento de scans DAST.
Suporta: cron-like, retry, escalation.
"""
import schedule
import time
import json
from datetime import datetime
from pathlib import Path

class ScanScheduler:
    def __init__(self, config_file='scan-config.json'):
        self.config = self._load_config(config_file)
        self.log_file = Path('scan-scheduler.log')

    def _load_config(self, config_file):
        """Carrega configuração de scans."""
        if Path(config_file).exists():
            with open(config_file) as f:
                return json.load(f)

        return {
            'scans': [],
            'schedule': {
                'critical': '0 */4 * * *',    # A cada 4 horas
                'high': '0 */8 * * *',        # A cada 8 horas
                'medium': '0 2 * * *',        # Diário às 2:00
                'low': '0 2 * * 0'            # Semanal
            },
            'retry': {
                'max_retries': 3,
                'retry_delay': 300
            }
        }

    def schedule_critical_scans(self):
        """Agenda scans críticos."""
        schedule.every(4).hours.do(self._run_scan_group, 'critical')

    def schedule_high_scans(self):
        """Agenda scans de alta prioridade."""
        schedule.every(8).hours.do(self._run_scan_group, 'high')

    def schedule_medium_scans(self):
        """Agenda scans de média prioridade."""
        schedule.every().day.at("02:00").do(self._run_scan_group, 'medium')

    def schedule_low_scans(self):
        """Agenda scans de baixa prioridade."""
        schedule.every().sunday.at("02:00").do(self._run_scan_group, 'low')

    def _run_scan_group(self, priority):
        """Executa grupo de scans por prioridade."""
        targets = [s for s in self.config['scans'] if s.get('priority') == priority]

        self._log(f'Iniciando scans {priority}: {len(targets)} targets')

        for target in targets:
            try:
                self._execute_scan(target)
            except Exception as e:
                self._log(f'Erro no scan {target["url"]}: {e}')
                self._retry_scan(target)

    def _execute_scan(self, target):
        """Executa um scan individual."""
        import subprocess

        cmd = [
            'nuclei',
            '-u', target['url'],
            '-severity', target.get('severity', 'critical,high'),
            '-json',
            '-o', f'results/{target["name"]}.json'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f'Nuclei failed: {result.stderr}')

        self._log(f'Scan concluído: {target["url"]}')

    def _retry_scan(self, target):
        """Retenta scan com backoff."""
        max_retries = self.config['retry']['max_retries']
        retry_delay = self.config['retry']['retry_delay']

        for attempt in range(max_retries):
            self._log(f'Retry {attempt + 1}/{max_retries} para {target["url"]}')
            time.sleep(retry_delay)

            try:
                self._execute_scan(target)
                return
            except Exception as e:
                self._log(f'Retry falhou: {e}')

        self._log(f'FALHA DEFINITIVA: {target["url"]} após {max_retries} tentativas')

    def _log(self, message):
        """Registra mensagem no log."""
        timestamp = datetime.now().isoformat()
        log_entry = f'[{timestamp}] {message}'
        print(log_entry)

        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')

    def run_forever(self):
        """Executa scheduler infinitamente."""
        self.schedule_critical_scans()
        self.schedule_high_scans()
        self.schedule_medium_scans()
        self.schedule_low_scans()

        self._log('Scheduler iniciado')

        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == '__main__':
    scheduler = ScanScheduler()
    scheduler.run_forever()
```

---

## 9. Exemplo Completo: Pipeline DAST

### 9.1 Pipeline Full com ZAP + Nuclei

{% raw %}
```yaml
# .github/workflows/dast-pipeline-complete.yml
name: Complete DAST Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * 1'  # Semanal

env:
  STAGING_URL: http://localhost:3000
  ZAP_TARGET: http://app-staging:3000

jobs:
  setup-staging:
    runs-on: ubuntu-latest
    outputs:
      staging-ready: ${{ steps.check.outputs.ready }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Docker Compose
        run: |
          docker-compose -f docker-compose.staging.yml up -d

      - name: Wait for App
        id: check
        run: |
          for i in $(seq 1 30); do
            if curl -sf http://localhost:3000/health > /dev/null 2>&1; then
              echo "ready=true" >> $GITHUB_OUTPUT
              echo "App ready after ${i}0 seconds"
              exit 0
            fi
            sleep 10
          done
          echo "ready=false" >> $GITHUB_OUTPUT
          echo "App failed to start"
          exit 1

  zap-scan:
    needs: setup-staging
    if: needs.setup-staging.outputs.staging-ready == 'true'
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: ZAP Spider + Active Scan
        uses: zaproxy/action-full-scan@v0.12.0
        with:
          target: ${{ env.ZAP_TARGET }}
          rules_file_name: 'zap-rules.tsv'
          cmd_options: '-a -j'
        continue-on-error: true

      - name: ZAP API Scan
        run: |
          docker run --rm \
            --network staging_default \
            ghcr.io/zaproxy/zaproxy:stable \
            zap-api-scan.py \
            -t http://app-staging:3000/openapi.json \
            -f openapi \
            -r zap-api-report.html
        continue-on-error: true

      - name: Parse ZAP Results
        run: |
          python3 scripts/zap-parser.py report_html.html zap-results.json

      - name: Upload ZAP Report
        uses: actions/upload-artifact@v4
        with:
          name: zap-reports
          path: |
            report_html.html
            zap-api-report.html
            zap-results.json

  nuclei-scan:
    needs: setup-staging
    if: needs.setup-staging.outputs.staging-ready == 'true'
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install Nuclei
        run: |
          go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
          nuclei -update-templates

      - name: Nuclei - CVE Detection
        run: |
          nuclei -u ${{ env.ZAP_TARGET }} \
            -tags cve \
            -severity critical,high \
            -json -o nuclei-cve.json \
            -stats

      - name: Nuclei - Misconfiguration
        run: |
          nuclei -u ${{ env.ZAP_TARGET }} \
            -tags misconfiguration \
            -severity critical,high,medium \
            -json -o nuclei-misconfig.json \
            -stats

      - name: Nuclei - Exposures
        run: |
          nuclei -u ${{ env.ZAP_TARGET }} \
            -tags exposures \
            -severity critical,high \
            -json -o nuclei-exposures.json \
            -stats

      - name: Merge Nuclei Results
        run: |
          python3 << 'EOF'
          import json

          results = []
          for filename in ['nuclei-cve.json', 'nuclei-misconfig.json', 'nuclei-exposures.json']:
              try:
                  with open(filename) as f:
                      for line in f:
                          if line.strip():
                              results.append(json.loads(line))
              except FileNotFoundError:
                  pass

          with open('nuclei-all.json', 'w') as f:
              for r in results:
                  f.write(json.dumps(r) + '\n')

          print(f'Total findings: {len(results)}')
          EOF

      - name: Upload Nuclei Results
        uses: actions/upload-artifact@v4
        with:
          name: nuclei-results
          path: nuclei-all.json

  api-security:
    needs: setup-staging
    if: needs.setup-staging.outputs.staging-ready == 'true'
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: API DAST Tests
        run: |
          python3 scripts/api-dast.py \
            --openapi http://app-staging:3000/openapi.json \
            --output api-results.json

      - name: GraphQL Security Tests
        run: |
          python3 scripts/graphql-dast.py \
            --endpoint http://app-staging:3000/graphql \
            --output graphql-results.json

      - name: Upload API Results
        uses: actions/upload-artifact@v4
        with:
          name: api-results
          path: |
            api-results.json
            graphql-results.json

  analyze-and-report:
    needs: [zap-scan, nuclei-scan, api-security]
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download All Results
        uses: actions/download-artifact@v4
        with:
          path: results/

      - name: Consolidate Results
        run: |
          python3 scripts/consolidate-dast.py \
            --zap results/zap-reports/zap-results.json \
            --nuclei results/nuclei-results/nuclei-all.json \
            --api results/api-results/api-results.json \
            --output consolidated-results.json

      - name: Apply False Positive Rules
        run: |
          python3 scripts/fp-manager.py \
            --input consolidated-results.json \
            --baseline dast-baseline.json \
            --output final-results.json

      - name: Generate HTML Report
        run: |
          python3 scripts/generate-report.py \
            --results final-results.json \
            --output dast-report.html

      - name: Generate Summary Comment
        if: github.event_name == 'pull_request'
        run: |
          python3 scripts/pr-comment.py \
            --results final-results.json \
            --output pr-comment.md

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const comment = fs.readFileSync('pr-comment.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });

      - name: Upload Final Report
        uses: actions/upload-artifact@v4
        with:
          name: dast-final-report
          path: |
            dast-report.html
            final-results.json

      - name: Quality Gate
        run: |
          python3 scripts/quality-gate.py \
            --results final-results.json \
            --max-critical 0 \
            --max-high 5 \
            --max-medium 20
```
{% endraw %}

### 9.2 Setup do Ambiente de Staging

```yaml
# docker-compose.staging.yml
version: '3.8'

services:
  app-staging:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=staging
      - DATABASE_URL=postgres://app:secret@db-staging:5432/app_staging
      - REDIS_URL=redis://redis-staging:6379
      - JWT_SECRET=staging-secret-key-do-not-use-in-production
      - LOG_LEVEL=debug
    depends_on:
      db-staging:
        condition: service_healthy
      redis-staging:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - staging-net

  db-staging:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=app_staging
      - POSTGRES_USER=app
      - POSTGRES_PASSWORD=secret
    volumes:
      - ./scripts/seed-staging.sql:/docker-entrypoint-initdb.d/01-seed.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app_staging"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - staging-net

  redis-staging:
    image: redis:7-alpine
    networks:
      - staging-net

  zap:
    image: ghcr.io/zaproxy/zaproxy:stable
    ports:
      - "8090:8090"
    command: >
      zap-webswing.sh
      -daemon
      -host 0.0.0.0
      -port 8090
      -config api.disablekey=true
      -config connection.timeoutInSecs=120
    volumes:
      - zap-home:/zap/home
    networks:
      - staging-net

  nuclei:
    image: projectdiscovery/nuclei:latest
    volumes:
      - ./templates:/root/templates
      - ./results:/root/results
    networks:
      - staging-net

volumes:
  zap-home:

networks:
  staging-net:
    driver: bridge
```

### 9.3 Geração de Relatórios

```python
#!/usr/bin/env python3
"""
Geração de relatório DAST consolidado.
Combina resultados de ZAP, Nuclei, e API tests.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class DASTReportGenerator:
    def __init__(self):
        self.findings = []
        self.summary = {}

    def load_zap_results(self, filepath: str):
        """Carrega resultados do ZAP."""
        try:
            with open(filepath) as f:
                data = json.load(f)

            for alert in data.get('alerts', []):
                self.findings.append({
                    'source': 'OWASP ZAP',
                    'name': alert.get('name'),
                    'severity': self._map_zap_risk(alert.get('risk', 0)),
                    'url': alert.get('url'),
                    'parameter': alert.get('param'),
                    'solution': alert.get('solution'),
                    'cwe': alert.get('cweid'),
                    'reference': alert.get('reference')
                })
        except FileNotFoundError:
            print(f'ZAP results not found: {filepath}')

    def load_nuclei_results(self, filepath: str):
        """Carrega resultados do Nuclei."""
        try:
            with open(filepath) as f:
                for line in f:
                    if line.strip():
                        result = json.loads(line)
                        self.findings.append({
                            'source': 'Nuclei',
                            'name': result.get('info', {}).get('name'),
                            'severity': result.get('info', {}).get('severity'),
                            'url': result.get('matched-at'),
                            'template': result.get('template-id'),
                            'description': result.get('info', {}).get('description'),
                            'reference': result.get('info', {}).get('reference', [])
                        })
        except FileNotFoundError:
            print(f'Nuclei results not found: {filepath}')

    def load_api_results(self, filepath: str):
        """Carrega resultados de API tests."""
        try:
            with open(filepath) as f:
                data = json.load(f)

            for vuln in data.get('vulnerabilities', []):
                self.findings.append({
                    'source': 'API DAST',
                    'name': vuln.get('name'),
                    'severity': vuln.get('severity'),
                    'endpoint': vuln.get('endpoint'),
                    'payload': vuln.get('payload'),
                    'evidence': vuln.get('evidence')
                })
        except FileNotFoundError:
            print(f'API results not found: {filepath}')

    def _map_zap_risk(self, risk: int) -> str:
        """Mapeia risco ZAP para severity padronizada."""
        mapping = {0: 'info', 1: 'low', 2: 'medium', 3: 'high'}
        return mapping.get(risk, 'info')

    def generate_summary(self):
        """Gera resumo consolidado."""
        self.summary = {
            'total_findings': len(self.findings),
            'by_severity': {
                'critical': len([f for f in self.findings if f.get('severity') == 'critical']),
                'high': len([f for f in self.findings if f.get('severity') == 'high']),
                'medium': len([f for f in self.findings if f.get('severity') == 'medium']),
                'low': len([f for f in self.findings if f.get('severity') == 'low']),
                'info': len([f for f in self.findings if f.get('severity') == 'info'])
            },
            'by_source': {
                'OWASP ZAP': len([f for f in self.findings if f.get('source') == 'OWASP ZAP']),
                'Nuclei': len([f for f in self.findings if f.get('source') == 'Nuclei']),
                'API DAST': len([f for f in self.findings if f.get('source') == 'API DAST'])
            },
            'timestamp': datetime.now().isoformat()
        }
        return self.summary

    def generate_html_report(self, output_file: str = 'dast-report.html'):
        """Gera relatório HTML."""
        summary = self.generate_summary()

        html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório DAST - {summary['timestamp']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
        .severity-critical {{ color: #d32f2f; font-weight: bold; }}
        .severity-high {{ color: #f57c00; font-weight: bold; }}
        .severity-medium {{ color: #fbc02d; }}
        .severity-low {{ color: #388e3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #263238; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>Relatório DAST - Análise Dinâmica de Segurança</h1>

    <div class="summary">
        <h2>Resumo</h2>
        <p><strong>Data:</strong> {summary['timestamp']}</p>
        <p><strong>Total de Finding:</strong> {summary['total_findings']}</p>
        <ul>
            <li class="severity-critical">Critical: {summary['by_severity']['critical']}</li>
            <li class="severity-high">High: {summary['by_severity']['high']}</li>
            <li class="severity-medium">Medium: {summary['by_severity']['medium']}</li>
            <li class="severity-low">Low: {summary['by_severity']['low']}</li>
            <li>Info: {summary['by_severity']['info']}</li>
        </ul>
        <p><strong>Por Scanner:</strong></p>
        <ul>'''

        for source, count in summary['by_source'].items():
            html += f'<li>{source}: {count}</li>'

        html += '''
        </ul>
    </div>

    <h2>Findings Detalhados</h2>
    <table>
        <tr>
            <th>Severidade</th>
            <th>Nome</th>
            <th>Fonte</th>
            <th>URL/Endpoint</th>
            <th>Solução</th>
        </tr>'''

        # Ordenar por severidade
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
        sorted_findings = sorted(
            self.findings,
            key=lambda x: severity_order.get(x.get('severity', 'info'), 4)
        )

        for finding in sorted_findings:
            severity = finding.get('severity', 'info')
            html += f'''
        <tr>
            <td class="severity-{severity}">{severity.upper()}</td>
            <td>{finding.get('name', 'N/A')}</td>
            <td>{finding.get('source', 'N/A')}</td>
            <td>{finding.get('url', finding.get('endpoint', 'N/A'))}</td>
            <td>{finding.get('solution', finding.get('description', 'N/A'))[:100]}</td>
        </tr>'''

        html += '''
    </table>
</body>
</html>'''

        with open(output_file, 'w') as f:
            f.write(html)

        print(f'Relatório HTML gerado: {output_file}')

    def generate_json_report(self, output_file: str = 'dast-report.json'):
        """Gera relatório JSON."""
        report = {
            'summary': self.generate_summary(),
            'findings': self.findings
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f'Relatório JSON gerado: {output_file}')


def main():
    generator = DASTReportGenerator()

    # Carregar resultados
    generator.load_zap_results('results/zap-results.json')
    generator.load_nuclei_results('results/nuclei-all.json')
    generator.load_api_results('results/api-results.json')

    # Gerar relatórios
    generator.generate_html_report()
    generator.generate_json_report()

    # Imprimir resumo
    summary = generator.generate_summary()
    print('\n=== DAST Scan Summary ===')
    print(f'Total findings: {summary["total_findings"]}')
    print(f'Critical: {summary["by_severity"]["critical"]}')
    print(f'High: {summary["by_severity"]["high"]}')
    print(f'Medium: {summary["by_severity"]["medium"]}')


if __name__ == '__main__':
    main()
```

---

## 10. Referências

### 10.1 Documentação e Recursos

- **OWASP ZAP**: https://www.zaproxy.org/docs/
- **OWASP Testing Guide**: https://owasp.org/www-project-web-security-testing-guide/
- **Nikto Documentation**: https://github.com/sullo/nikto/wiki
- **Nuclei Documentation**: https://nuclei.projectdiscovery.io/
- **ProjectDiscovery Templates**: https://github.com/projectdiscovery/nuclei-templates

### 10.2 Casos Documentados

- **OWASP ZAP - SQL Injection em Produção**: Relato documentado pelo OWASP de vulnerabilidade de SQL Injection detectada em sistema bancário brasileiro que passou por todos os testes de segurança.
- **Nikto - Servidor Desatualizado em Hospital**: Caso de Nikto detectando Apache 2.2.15 com CVEs de 2011 em produção hospitalar, ignorado por scanners internos.
- **DAST em CI/CD - GitHub**: Estudo de caso do GitHub sobre implementação de DAST em pipelines, reduzindo vulnerabilidades em produção em 40%.
- **Burp Suite - Descobertas em Aplicações Reais**: Relatos da PortSwigger sobre vulnerabilidades encontradas em aplicações financeiras via Burp Suite, incluindo IDOR e authentication bypass.

### 10.3 Ferramentas Complementares

- **Burp Suite**: Scanner comercial de alta qualidade para testes manuais e automatizados.
- **Arachni**: Scanner web de código aberto com foco em performance.
- **Wapiti**: Scanner de vulnerabilities web open-source.
- **Skipfish**: Scanner web open-source do Google (descontinuado, mas ainda útil).
- **ffuf**: Fuzzing tool para descoberta de endpoints.

### 10.4 Padrões e Normas

- **OWASP Top 10 (2021)**: https://owasp.org/www-project-top-ten/
- **OWASP ASVS**: Application Security Verification Standard
- **OWASP API Security Top 10**: https://owasp.org/API-Security/
- **NIST SP 800-53**: Security and Privacy Controls
- **PCI DSS**: Payment Card Industry Data Security Standard

### 10.5 Artigos e Blogs

- "Dynamic Application Security Testing: An Overview" - OWASP
- "ZAP in CI/CD Pipelines" - OWASP ZAP Documentation
- "Nuclei: A Template-Based Scanner" - ProjectDiscovery Blog
- "API Security Testing Guide" - OWASP API Security Project
- "DAST Best Practices for Modern Applications" - SANS Institute

---

## Glossário

- **DAST (Dynamic Application Security Testing)**: Teste de segurança que avalia aplicações em execução.
- **Crawling**: Processo de descoberta automática de endpoints web.
- **Fuzzing**: Técnica de envio de dados inválidos ou inesperados para testar comportamento.
- **False Positive**: Resultado positivo incorreto, onde o scanner reporta vulnerabilidade inexistente.
- **Authentication Bypass**: Vulnerabilidade que permite acesso não autorizado sem credenciais.
- **OWASP (Open Web Application Security Project)**: Organização sem fins lucrativos focada em segurança de aplicações web.
- **CVE (Common Vulnerabilities and Exposures)**: Sistema de identificação de vulnerabilidades de segurança.
- **CWE (Common Weakness Enumeration)**: Lista padronizada de fraquezas de segurança.
- **SSRF (Server-Side Request Forgery)**: Vulnerabilidade que permite ao atacante fazer requisições do servidor.
- **IDOR (Insecure Direct Object Reference)**: Vulnerabilidade de acesso não autorizado a objetos.
---

*[Capítulo anterior: 04 — Sast Analise Estatica](04-sast-analise-estatica.md)*
*[Próximo capítulo: 06 — Sca Composicao Software](06-sca-composicao-software.md)*
