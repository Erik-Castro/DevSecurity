---
layout: default
title: "10-gestao-de-segredos"
---

# Capítulo 10 — Gestão de Segredos

## Sumario

1. Por que Gestao de Segredos Importa
2. Deteccao de Segredos
3. HashiCorp Vault
4. Cloud Secret Management
5. Kubernetes Secrets
6. Environment Variables Seguras
7. Certificate Management
8. Key Rotation
9. Exemplo Completo: Secret Management Pipeline
10. Referencias

---

## 1. Por que Gestao de Segredos Importa

### 1.1 O Problema dos Segredos Vazados

Segredos — API keys, tokens de acesso, certificados, senhas de banco de dados — sao os alvos mais cobiados por atacantes. Estatisticas alarmantes revelam a gravidade do problema:

- De acordo com o relatorio "State of Secrets Sprawl" do GitGuardian (2024), mais de 12,8 milhoes de segredos foram detectados em repositorios publicos no GitHub apenas em 2023, um aumento de 28% em relacao ao ano anterior.
- O mesmo relatorio aponta que 1 em cada 10 contribuidores expoe acidentalmente um segredo ao commitar codigo.
- A IBM X-Force identifica que credenciais comprometidas sao o vetor de ataque numero um para violacoes de dados, responsaveis por mais de 30% dos incidentes.
- O custo medio de uma violacao de dados causada por segredos vazados ultrapassa US$ 4,5 milhoes (IBM Cost of a Data Breach, 2023).

### 1.2 Como Segredos Sao Vazados

Existem multiplos caminhos pelos quais segredos acabam expostos:

**Repositorios Git:**
- Desenvolvedores commitam arquivos `.env`, arquivos de configuracao ou codigo-fonte contendo chaves hardcoded
- Branches removidas mas que persistem no historico do Git
- Forks publicos que expoe segredos de repositorios originalmente privados
- Merge conflicts que revelam segredos em comentarios ou variaveis

**Pipelines CI/CD:**
- Logs de build que imprimem variaveis de ambiente com segredos
- artefatos de build que incluem arquivos de configuracao com credenciais
- Variaveis de ambiente definidas diretamente em arquivos de pipeline (ex: `.gitlab-ci.yml`, `Jenkinsfile`)

**Infraestrutura:**
- Estados do Terraform contendo senhas em texto plano
- Configuracoes de Kubernetes com secrets em texto claro
- Variaveis de ambiente em containers Docker expostas em registries publicos
- Metadados de instancias cloud (EC2, GCP) acessiveis via APIs

**Aplicacoes:**
- Erros de aplicacao que logam headers de autenticacao
- Endpoints de debug que retornam configuracoes completas incluindo segredos
- Mensagens de erro que expoem strings de conexao de banco de dados
- Arquivos de configuracao commitados com segredos reais em vez de placeholders

### 1.3 Casos Reais Documentados

#### Caso 1: Uber — API Key Exposta no Codigo-fonte (2019)

Em 2019, pesquisadores de seguranca descobriram que chaves de API da Uber estavam expostas no codigo-fonte de aplicativos moveis da empresa. Atraves de engenharia reversa dos aplicativos, atacantes conseguiram acessar:

- Dados de localizacao em tempo real de passageiros
- Informacoes pessoais de motoristas e passageiros
- Historico de viagens

A Uber utilizava a mesma abordagem de muitas empresas na epoca: chaves de API embutidas diretamente no codigo da aplicacao mobile. O atacante precisava apenas de ferramentas de engenharia reversa disponiveis gratuitamente para extrair essas credenciais.

**Licao aprendida:** Chaves de API nunca devem ser embutidas em aplicativos client-side. Utilize proxy servers ou BFF (Backend for Frontend) para intermediar chamadas que requerem segredos.

#### Caso 2: GitHub Tokens Expostos em Logs

Em varios incidentes documentados entre 2020 e 2023, tokens de acesso do GitHub (Personal Access Tokens, OAuth tokens, e tokens de aplicacoes GitHub) foram vazados atraves de:

- Logs de ferramentas de CI/CD que imprimiam variaveis de ambiente
- Output de comandos git que incluiam tokens na URL (ex: `git clone https://TOKEN@github.com/...`)
- Screenshots compartilhados em canais de comunicacao
- Stack traces de erros que revelavam tokens em headers HTTP

O GitHub reportou que tokens comprometidos foram usados para:
- Acessar e modificar repositorios privados
- Exfiltrar codigo-fonte proprietario
- Criar hooks maliciosos em repositorios
- Modificar configuracoes de seguranca de organizacoes

**Licao aprendida:** Tokens nunca devem aparecer em logs, URLs ou mensagens de erro. Utilize variaveis de ambiente referenciadas indiretamente e implemente filtragem de logs.

#### Caso 3: Docker Environment Variable Leaks

Em 2022, um estudo do Sysdig revelou que mais de 50% das imagens Docker em registries publicos continham segredos em variaveis de ambiente ou camadas de build. Casos especificos incluem:

- Imagens publicadas com `ENV AWS_SECRET_ACCESS_KEY=...` no Dockerfile
- Variaveis de ambiente passadas durante `docker run` que ficavam registradas no historico da imagem
- `.env` files copiados para dentro de imagens via `COPY . .` sem `.dockerignore` adequado
- Comandos de build que imprimiam segredos em stdout, tornando-se visiveis em qualquer camada de build

Um atacante que fizesse pull de uma dessas imagens e executasse `docker history` ou inspecionasse as camadas com `docker inspect` encontraria os segredos expostos.

**Licao aprendida:** Nunca passe segredos via `ENV` ou `ARG` em Dockerfiles. Utilize Docker secrets, Docker BuildKit secrets, ou monte volumes em tempo de execucao.

#### Caso 4: Terraform State File com Segredos Embarcados

O Terraform armazena todo o estado da infraestrutura — incluindo valores de saida de recursos — em arquivos de estado (`.tfstate`). Em multiplos incidentes documentados, esses arquivos foram:

- Commitados em repositorios Git, expondo senhas de banco de dados, chaves de API e certificados
- Armazenados localmente em maquinas de desenvolvedores sem criptografia
- Acessiveis via ferramentas de CI/CD que nao restringiam o acesso ao state

Um arquivo `.tfstate` tipico pode conter:
- Senhas de bancos de dados RDS
- Chaves de acesso AWS (Access Key ID + Secret Access Key)
- Certificados SSL e chaves privadas
- Tokens de acesso a servicos de terceiros

Em um caso documentado, a empresa de tecnologia alemã Delivery Hero expôs dados de credenciais em repositorios publicos, incluindo o Terraform state que continha senhas de bancos de dados e tokens de acesso a servicos cloud.

**Licao aprendida:** Nunca commite o arquivo `.tfstate`. Utilize backends remotos com criptografia (S3 com encryption, Azure Storage com encryption at rest) e ative o state locking.

#### Caso 5: npm Tokens em Repositorios Publicos

Em 2020 e 2021, multiplos incidentes envolveram tokens de acesso ao npm vazados em repositorios publicos:

- Desenvolvedores commitavam arquivos `.npmrc` contendo tokens de autenticacao do npm
- Dependencias maliciosas eram publicadas para roubar tokens em tempo de build
- Empresas como Uber, Twitch e outros tiveram pacotes publicados por atacantes que usaram tokens comprometidos

O ataque mais notavel envolveu a cadeia de dependencia do npm, onde pacotes maliciosos exfiltravam variaveis de ambiente — incluindo tokens de registry — durante o processo de `npm install`.

O GitHub adicionou scanning para tokens do npm apos os frequentes incidentes, mas a melhor defenca continua sendo:
- Usar tokens com escopo minimo (read-only)
- Implementar 2FA em contas npm
- Rotacionar tokens regularmente
- Utilizar OIDC para autenticacao sem tokens persistentes

**Licao aprendida:** Tokens de registry de pacotes devem ter escopo minimo e serem gerenciados por um sistema centralizado de segredos, nao em arquivos de configuracao locais.

#### Caso 6: Twilio API Credentials Expostas

Em 2022, o Atlassian reportou que credenciais da Twilio foram comprometidas e usadas para acessar dados de clientes. O incidente envolveu:

- Chaves de API da Twilio que estavam armazenadas em repositorios internos
- Atacantes que acessaram os repositorios e extrairam as credenciais
- Uso das credenciais para acessar o sistema de suporte ao cliente
- Exfiltracao de dados de clientes corporativos

A Twilio confirmou que atacantes obtiveram acesso a dados de aproximadamente 175 clientes, incluindo nomes, enderecos e metadados de comunicacao.

**Licao aprendida:** Credenciais de servicos de comunicacao (Twilio, SendGrid, Mailgun) devem ter restricoes de IP e serem gerenciadas com rotacao automatica. Implemente monitoring de uso anomalo.

### 1.4 Tipos de Segredos

| Tipo | Exemplo | Risco se Vazado |
|------|---------|-----------------|
| API Keys | `sk-abc123def456` | Acesso nao autorizado a servicos |
| Tokens OAuth | `ghp_xxxxxxxxxxxx` | Acesso a contas e dados |
| Senhas de banco | `P@ssw0rd123!` | Acesso direto a dados |
| Certificados | Chave privada PEM | Impersonacao, interceptacao |
| JWT Secrets | `my-secret-jwt-key` | Forjacao de tokens |
| Chaves de criptografia | `aes-256-key...` | Descriptografia de dados |
| Connection Strings | `mysql://user:pass@host` | Acesso a dados |
| SSH Keys | `-----BEGIN RSA PRIVATE KEY...` | Acesso a sistemas remotos |
| Cloud Credentials | AWS Access Keys | Controle total de infraestrutura |

---

## 2. Deteccao de Segredos

### 2.1 GitLeaks — Deep Dive

GitLeaks e uma ferramenta de deteccao de segredos em repositorios Git, escrita em Go. E uma das ferramentas mais populares e eficazes do mercado.

#### Instalacao

```bash
# Instalacao via Go
go install github.com/zricethezav/gitleaks/v8@latest

# Instalacao via Homebrew (macOS/Linux)
brew install gitleaks

# Instalacao via Docker
docker pull ghcr.io/gitleaks/gitleaks:latest

# Instalacao via apt (Ubuntu/Debian)
sudo apt-get install gitleaks
```

#### Uso Basico

```bash
# Escanear repositorio Git completo
gitleaks detect

# Escanear apenas os ultimos 10 commits
gitleaks detect --log-opts="-10"

# Escanear um diretorio especifico
gitleaks detect --source /caminho/do/projeto

# Saida em formato JSON
gitleaks detect --report-format json --report-path resultados.json

# Saida em formato SARIF (integracao com GitHub)
gitleaks detect --report-format sarif --report-path resultados.sarif

# Modo verbose
gitleaks detect -v

# Proteger commits (usado como pre-commit hook)
gitleaks protect
```

#### Configuracao Personalizada

Crie um arquivo `.gitleaks.toml` na raiz do repositorio:

```toml
title = "Configuracao de Deteccao de Segredos GitLeaks"

# Parametros globais
[extend]
# herdar regras padrao
useDefault = true

# Regras customizadas
[[rules]]
id = "chave-api-custom"
description = "Detecta chaves de API customizadas da empresa"
regex = '''(?i)empresa[_-]?api[_-]?key\s*=\s*['"]([a-zA-Z0-9]{32,})['"]'''
tags = ["api", "empresa"]

[[rules]]
id = "chave-aws-custom"
description = "Detecta chaves AWS com prefixo especifico"
regex = '''(AKIA[A-Z0-9]{16})'''
tags = ["aws", "api-key"]

[[rules]]
id = "token-bearer"
description = "Detecta tokens Bearer em headers"
regex = '''(?i)bearer\s+[a-zA-Z0-9\-._~+/]+=*'''
tags = ["token", "auth"]

[[rules]]
id = "jwt-token"
description = "Detecta tokens JWT"
regex = '''eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]+'''
tags = ["jwt", "token"]

# Excecoes
[[rules.allowlist]]
description = "Permitir URLs de exemplo"
regex = '''https://example\.(com|org|net)/.*'''

[[rules.allowlist]]
description = "Permitir valores de placeholder"
regex = '''(YOUR_API_KEY|CHAVE_AQUI|INSERT_KEY_HERE)'''
```

#### GitLeaks em CI/CD (GitHub Actions)

{% raw %}
```yaml
# .github/workflows/secret-scan.yml
name: Secret Scanning com GitLeaks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}

      - name: Upload SARIF report
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
```
{% endraw %}

#### GitLeaks como Pre-commit Hook

```bash
#!/bin/bash
# scripts/pre-commit-gitleaks.sh

echo "Executando verificacao de segredos..."

if ! command -v gitleaks &> /dev/null; then
    echo "GitLeaks nao encontrado. Instalando..."
    go install github.com/zricethezav/gitleaks/v8@latest
fi

gitleaks protect --staged --verbose

if [ $? -ne 0 ]; then
    echo "ERRO: Segredos detectados no commit!"
    echo "Corrija os segredos antes de commitar."
    exit 1
fi

echo "Nenhum segredo detectado. Commit permitido."
```

### 2.2 TruffleHog Usage

TruffleHog, desenvolvido pela Truffle Security, e especializado em detectar segredos com verificacao ativa — ele tenta confirmar se o segredo encontrado e valido.

#### Instalacao e Uso

```bash
# Instalacao via Go
go install github.com/trufflesecurity/trufflehog/v3@latest

# Escanear repositorio Git
trufflehog git https://github.com/org/repo.git --only-verified

# Escanear diretorio local
trufflehog filesystem /caminho/do/projeto

# Escanear GitHub (todas as organizacoes)
trufflehog github --org=minha-organizacao

# Saida em JSON
trufflehog git https://github.com/org/repo.git --json

# Escanear apenas commits recentes
trufflehog git https://github.com/org/repo.git --since-commit=abc123
```

#### TruffleHog com Verificacao de GitHub

```bash
# Configurar GitHub token para verificacao
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Escanear e verificar validade dos segredos
trufflehog github --org=minha-organizacao --include-verified --concurrency=10

# Output esperado: apenas segredos VERIFICADOS (validos e ativos)
```

### 2.3 detect-secrets (Yelp)

O detect-secrets do Yelp e uma solucao mais leve, focada em baseline e integracao com hooks.

#### Instalacao e Uso

```bash
# Instalacao
pip install detect-secrets

# Inicializar baseline
detect-secrets scan > .secrets.baseline

# Re-escanear e comparar com baseline
detect-secrets scan --all-files .secrets.baseline

# Auditar baseline
detect-secrets audit .secrets.baseline

# Verificar se ha segredos novos
detect-secrets scan --update .secrets.baseline
```

#### Configuracao .secrets.baseline

```json
{
  "generated_at": "2024-01-15T10:30:00Z",
  "plugins_used": [
    {"name": "AWSKeyDetector"},
    {"name": "ArtifactoryDetector"},
    {"name": "AzureStorageKeyDetector"},
    {"name": "Base64HighEntropyString"},
    {"name": "BasicAuthDetector"},
    {"name": "CloudantDetector"},
    {"name": "HexHighEntropyString"},
    {"name": "IAMHardcodedAccessKey"},
    {"name": "JWTTokenDetector"},
    {"name": "KeywordDetector"},
    {"name": "MailchimpDetector"},
    {"name": "NpmDetector"},
    {"name": "OtpDetector"},
    {"name": "PrivateKeyDetector"},
    {"name": "SendGridDetector"},
    {"name": "SlackDetector"},
    {"name": "StripeDetector"},
    {"name": "TwilioKeyDetector"}
  ],
  "results": {},
  "filters_used": [
    {"path": "file_path_filter"}
  ]
}
```

### 2.4 GitHub Secret Scanning

O GitHub Secret Scanning e um recurso nativo que detecta segredos em repositorios e verifica se estes estao expostos em servicos parceiros.

#### Configuracao no GitHub

```yaml
# Configuracao via GitHub API
# Ativar secret scanning para uma organizacao
gh api -X PUT repos/{owner}/{repo}/secret-scanning \
  --input - <<EOF
{
  "status": "enabled"
}
EOF

# Configurar push protection
gh api -X PUT repos/{owner}/{repo}/secret-scanning/push-protection \
  --input - <<EOF
{
  "status": "enabled"
}
EOF
```

### 2.5 Pipeline Completo de Deteccao

```yaml
# .github/workflows/secret-detection-pipeline.yml
name: Pipeline de Deteccao de Segredos

on:
  push:
    branches: [main, develop, 'feature/**']
  pull_request:
    branches: [main]

jobs:
  gitleaks:
    name: GitLeaks Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  trufflehog:
    name: TruffleHog Verification
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

  detect-secrets:
    name: detect-secrets Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install detect-secrets
        run: pip install detect-secrets

      - name: Scan with detect-secrets
        run: |
          detect-secrets scan --all-files > results.json
          cat results.json | jq '.results | length' > count.txt
          COUNT=$(cat count.txt)
          if [ "$COUNT" -gt 0 ]; then
            echo "ERRO: $COUNT segredos potenciais detectados"
            cat results.json | jq '.results'
            exit 1
          fi

  docker-secrets:
    name: Docker Image Secrets Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t app:scan .

      - name: Run Trivy on image
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'app:scan'
          format: 'json'
          output: 'trivy-results.json'
          severity: 'CRITICAL,HIGH'

      - name: Check for secrets in image
        run: |
          docker history app:scan --format json > history.json
          docker save app:scan | tar -xO | strings | \
            grep -iE '(password|secret|key|token|api)' > image-secrets.txt || true
          if [ -s image-secrets.txt ]; then
            echo "ERRO: Possiveis segredos encontrados na imagem Docker"
            cat image-secrets.txt
            exit 1
          fi
```

### 2.6 Patterns Customizados

```python
#!/usr/bin/env python3
"""
patterns_customizados.py — Patterns de deteccao de segredos customizados
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SecretPattern:
    """Define um padrao de deteccao de segredo."""
    name: str
    description: str
    regex: str
    severity: str = "high"
    confidence: float = 0.8
    false_positive_patterns: List[str] = field(default_factory=list)

    def match(self, text: str) -> List[dict]:
        """Retorna todas as correspondencias encontradas no texto."""
        results = []
        for match in re.finditer(self.regex, text, re.IGNORECASE):
            value = match.group(0)
            is_false_positive = any(
                fp in value for fp in self.false_positive_patterns
            )
            if not is_false_positive:
                results.append({
                    "pattern": self.name,
                    "value": value[:20] + "..." if len(value) > 20 else value,
                    "line": text[:match.start()].count("\n") + 1,
                    "column": match.start() - text.rfind("\n", 0, match.start()),
                    "severity": self.severity,
                    "confidence": self.confidence,
                })
        return results


# Patterns padrao para ambientes brasileiros
PATTERNS = [
    SecretPattern(
        name="CPF_em_codigo",
        description="CPF hardcoded em codigo-fonte",
        regex=r"\d{3}\.\d{3}\.\d{3}-\d{2}",
        severity="medium",
        confidence=0.6,
    ),
    SecretPattern(
        name="CNPJ_em_codigo",
        description="CNPJ hardcoded em codigo-fonte",
        regex=r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}",
        severity="medium",
        confidence=0.6,
    ),
    SecretPattern(
        name="token_sicoob",
        description="Token de API Sicoob/Cooperativa",
        regex=r"sicoob[_-]?token\s*=\s*['\"]([a-zA-Z0-9]{32,})['\"]",
        severity="high",
        confidence=0.9,
    ),
    SecretPattern(
        name="conexao_banco_br",
        description="String de conexao de banco brasileiro",
        regex=r"(?:jdbc|mysql|postgres|oracle|sqlserver)://[^\s]+(?:password|senha)\s*=\s*[^\s&\"']+",
        severity="critical",
        confidence=0.95,
    ),
    SecretPattern(
        name="chave_api_pagamento",
        description="Chave de API de gateway de pagamento",
        regex=r"(?:pagseguro|mercadopago|pagarme|stone|rede)[_-]?key\s*=\s*['\"]([a-zA-Z0-9\-]{20,})['\"]",
        severity="critical",
        confidence=0.9,
    ),
    SecretPattern(
        name="aws_secret_key",
        description="AWS Secret Access Key",
        regex=r"(?:aws_secret_access_key|aws_secret_key)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
        severity="critical",
        confidence=0.95,
    ),
    SecretPattern(
        name="private_key_pem",
        description="Chave privada PEM",
        regex=r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----",
        severity="critical",
        confidence=0.99,
    ),
]


def scan_file(file_path: str) -> List[dict]:
    """Escaneia um arquivo em busca de segredos."""
    findings = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for pattern in PATTERNS:
            matches = pattern.match(content)
            for match in matches:
                match["file"] = file_path
                findings.append(match)
    except Exception as e:
        print(f"Erro ao escanear {file_path}: {e}")
    return findings


def generate_report(findings: List[dict]) -> str:
    """Gera relatorio de findings em formato JSON."""
    report = {
        "total_findings": len(findings),
        "critical": len([f for f in findings if f["severity"] == "critical"]),
        "high": len([f for f in findings if f["severity"] == "high"]),
        "medium": len([f for f in findings if f["severity"] == "medium"]),
        "findings": findings,
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    import glob

    if len(sys.argv) < 2:
        print("Uso: python patterns_customizados.py <diretorio>")
        sys.exit(1)

    target = sys.argv[1]
    all_findings = []

    for filepath in glob.glob(f"{target}/**/*", recursive=True):
        if os.path.isfile(filepath):
            all_findings.extend(scan_file(filepath))

    report = generate_report(all_findings)
    print(report)

    if any(f["severity"] == "critical" for f in all_findings):
        sys.exit(1)
```

---

## 3. HashiCorp Vault

### 3.1 Arquitetura e Conceitos

O HashiCorp Vault e a solucao de referencia para gestao centralizada de segredos. Sua arquitetura baseia-se em varios conceitos fundamentais:

- **Secret Engines**: Modulos responsaveis por gerenciar tipos especificos de segredos (KV, database, PKI, transit, AWS, etc.)
- **Auth Methods**: Mecanismos de autenticacao (token, userpass, LDAP, Kubernetes, AWS IAM, OIDC)
- **Policies**: Regras de controle de acesso que definem quais paths um token pode acessar
- **Tokens**: Credenciais de curta duracao que representam uma sessao autenticada
- **Leases**: Contratos de vida util para segredos, com renovacao e expiracao
- **Audit Backend**: Log imutavel de todas as operacoes realizadas no Vault

### 3.2 Dynamic Secrets

Dynamic secrets sao gerados sob demanda e unicos para cada solicitante. Diferente de segredos estaticos (que sao compartilhados), cada conexao gera credenciais unicas com TTL configuravel.

{% raw %}
```bash
# Habilitar engine de banco de dados
vault secrets enable database

# Configurar conexao com PostgreSQL
vault write database/config/postgres \
  plugin_name=postgresql-database-plugin \
  connection_url="postgresql://{{username}}:{{password}@db-host:5432/vault_db" \
  allowed_roles="readonly" \
  username="vault_admin" \
  password="vault_admin_password"

# Criar role para credenciais dinamicas
vault write database/roles/readonly \
  db_name=postgres \
  default_ttl="1h" \
  max_ttl="24h" \
  creation_statements="
    CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}';
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";
  "

# Solicitar credenciais dinamicas
vault read database/creds/readonly
# Output:
# Key                Value
# ---                -----
# lease_id           database/creds/readonly/abc123
# lease_duration     1h
# lease_renewable    true
# password           A1b2-C3d4-E5f6
# username           v-approle-readonly-abc123
```
{% endraw %}

### 3.3 Transit Engine

O Transit Engine fornece criptografia como servico, permitindo criptografar e descriptografar dados sem expor chaves de criptografia.

```bash
# Habilitar transit engine
vault secrets enable transit

# Criar chave de criptografia
vault write -f transit/keys/app-data \
  type=aes256-gcm96 \
  exportable=false \
  allow_plaintext_backup=false

# Criptografar dados
vault write -format=json transit/encrypt/app-data \
  plaintext=$(echo -n "dados_sensiveis" | base64) | \
  jq -r '.data.ciphertext'

# Descriptografar dados
vault write -format=json transit/decrypt/app-data \
  ciphertext="vault:v1:abc123def456..." | \
  jq -r '.data.plaintext' | base64 -d

# Assinar dados
vault write -format=json transit/sign/app-data \
  hash_algorithm=sha2-256 \
  input=$(echo -n "documento_importante" | base64) | \
  jq -r '.data.signature'

# Verificar assinatura
vault write -format=json transit/verify/app-data \
  hash_algorithm=sha2-256 \
  input=$(echo -n "documento_importante" | base64) \
  signature="vault:v1:voter:abc123..." | \
  jq -r '.data.valid'
```

### 3.4 PKI Engine

O PKI Engine do Vault permite criar uma Certificate Authority (CA) interna e emitir certificados TLS automaticamente.

```bash
# Habilitar PKI engine
vault secrets enable pki
vault secrets tune -max-lease-ttl=87600h pki

# Gerar CA root
vault write -format=json pki/root/generate/internal \
  common_name="Minha Empresa Root CA" \
  ttl=87600h | jq -r '.data.certificate' > root_ca.pem

# Configurar URLs de distribuicao
vault write pki/config/urls \
  issuing_certificates="https://vault.empresa.com:8200/v1/pki/ca" \
  crl_distribution_points="https://vault.empresa.com:8200/v1/pki/crl"

# Criar role para certificados internos
vault write pki/roles/internal \
  allowed_domains="empresa.com,local" \
  allow_subdomains=true \
  max_ttl=720h \
  key_type=rsa \
  key_bits=2048 \
  key_usage="DigitalSignature,KeyEncipherment" \
  ext_key_usage="ServerAuth,ClientAuth"

# Emitir certificado
vault write -format=json pki/issue/internal \
  common_name="api.empresa.com" \
  ttl=72h | jq -r '.data.certificate' > cert.pem
```

### 3.5 Setup Completo do Vault com Docker

```yaml
# docker-compose.yml
version: '3.8'

services:
  vault:
    image: hashicorp/vault:1.15.4
    container_name: vault
    ports:
      - "8200:8200"
    environment:
      VAULT_ADDR: 'http://0.0.0.0:8200'
      VAULT_API_ADDR: 'http://vault:8200'
    volumes:
      - vault-data:/vault/file
      - ./vault-config:/vault/config
    cap_add:
      - IPC_LOCK
    command: vault server -config=/vault/config/vault.hcl
    restart: unless-stopped
    networks:
      - vault-net

  vault-ui:
    image: hashicorp/vault:1.15.4
    container_name: vault-ui
    environment:
      VAULT_ADDR: 'http://vault:8200'
    depends_on:
      - vault
    restart: unless-stopped
    networks:
      - vault-net

volumes:
  vault-data:

networks:
  vault-net:
    driver: bridge
```

```hcl
# vault-config/vault.hcl
storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 1
  telemetry {
    unauthenticated_metrics_access = true
  }
}

api_addr = "http://vault:8200"
cluster_addr = "https://vault:8201"

telemetry {
  prometheus_retention_time = "30s"
  disable_hostname = true
}

ui = true

log_level = "info"
```

```bash
#!/bin/bash
# scripts/setup-vault.sh
# Setup inicial do Vault

set -euo pipefail

VAULT_ADDR="http://127.0.0.1:8200"
export VAULT_ADDR

echo "=== Inicializando Vault ==="
INIT_OUTPUT=$(vault operator init -key-shares=5 -key-threshold=3 -format=json)

echo "$INIT_OUTPUT" > vault-init-keys.json
echo "Chaves de inicializacao salvas em vault-init-keys.json"

# Salvar chaves de unseal (exemplo: 3 de 5)
UNSEAL_KEY_1=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[0]')
UNSEAL_KEY_2=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[1]')
UNSEAL_KEY_3=$(echo "$INIT_OUTPUT" | jq -r '.unseal_keys_b64[2]')

ROOT_TOKEN=$(echo "$INIT_OUTPUT" | jq -r '.root_token')

echo "=== Desbloqueando Vault ==="
vault operator unseal "$UNSEAL_KEY_1"
vault operator unseal "$UNSEAL_KEY_2"
vault operator unseal "$UNSEAL_KEY_3"

echo "=== Configurando autenticacao ==="
vault login "$ROOT_TOKEN"

# Habilitar auth method userpass
vault auth enable userpass

# Criar usuario admin
vault write auth/userpass/users/admin \
  password=ChangeMe123! \
  policies=superadmin

# Criar policy superadmin
vault policy write superadmin - <<'POLICY'
path "secret/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "database/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "transit/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "sys/*" {
  capabilities = ["read", "list"]
}
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
POLICY

# Habilitar secret engine KV v2
vault secrets enable -path=secret kv-v2

# Habilitar audit logging
vault audit enable file file_path=/vault/file/vault-audit.log

echo "=== Vault configurado com sucesso ==="
echo "Root Token: $ROOT_TOKEN"
```

### 3.6 Integracao Vault com CI/CD

{% raw %}
```yaml
# .github/workflows/vault-integration.yml
name: Pipeline com Vault

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configurar Vault
        uses: hashicorp/vault-action@v2
        with:
          url: ${{ secrets.VAULT_ADDR }}
          method: jwt
          role: github-actions
          jwtGithubAudience: "https://vault.empresa.com"
          secrets: |
            secret/data/deploy/credentials DB_PASSWORD | DB_PASSWORD ;
            secret/data/deploy/api-keys STRIPE_KEY | STRIPE_KEY ;
            secret/data/deploy/api-keys SENDGRID_KEY | SENDGRID_KEY

      - name: Deploy
        env:
          DB_PASSWORD: ${{ env.DB_PASSWORD }}
          STRIPE_KEY: ${{ env.STRIPE_KEY }}
          SENDGRID_KEY: ${{ env.SENDGRID_KEY }}
        run: |
          echo "Deploying com segredos do Vault..."
          ./deploy.sh
```
{% endraw %}

```bash
#!/bin/bash
# scripts/vault-login.sh
# Login no Vault a partir de CI/CD

set -euo pipefail

export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"

# Login com JWT (GitHub Actions OIDC)
if [ -n "${VAULT_ROLE:-}" ]; then
    JWT=$(curl -s -H "Authorization: bearer ${GITHUB_TOKEN}" \
        "${ACTIONS_ID_TOKEN_REQUEST_URL}&audience=vault" | jq -r '.value')

    vault write -format=json auth/jwt/login \
        role="${VAULT_ROLE}" \
        jwt="${JWT}" | \
        jq -r '.auth.client_token' > /tmp/vault-token

    export VAULT_TOKEN=$(cat /tmp/vault-token)

# Login com AppRole (Jenkins, GitLab CI)
elif [ -n "${VAULT_ROLE_ID:-}" ]; then
    ROLE_RESPONSE=$(curl -s -X POST \
        "${VAULT_ADDR}/v1/auth/approle/login" \
        -d "{\"role_id\":\"${VAULT_ROLE_ID}\",\"secret_id\":\"${VAULT_SECRET_ID}\"}")

    VAULT_TOKEN=$(echo "$ROLE_RESPONSE" | jq -r '.auth.client_token')
    export VAULT_TOKEN
fi

# Recuperar segredo do Vault
get_secret() {
    local path=$1
    local key=$2

    SECRET_VALUE=$(vault kv get -field="$key" "$path" 2>/dev/null)
    echo "$SECRET_VALUE"
}

# Exemplo de uso
export DB_PASSWORD=$(get_secret "secret/data/app/production" "password")
export API_KEY=$(get_secret "secret/data/app/production" "api_key")

echo "Segredos recuperados do Vault com sucesso"
```

### 3.7 Vault Agent para Kubernetes

```yaml
# vault-agent-config.hcl
auto_auth {
  method "kubernetes" {
    config = {
      role = "myapp"
      token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    }
  }

  sink "file" {
    config = {
      path = "/home/vault/.vault-token"
    }
  }
}

template {
  source      = "/vault/templates/config.json.ctmpl"
  destination = "/vault/secrets/config.json"
  perms       = 0644
}

template {
  source      = "/vault/templates/db-credentials.json.ctmpl"
  destination = "/vault/secrets/db-credentials.json"
  perms       = 0400
  command     = "/scripts/reload-app.sh"
}
```

{% raw %}
```yaml
# kubernetes/vault-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-vault-agent
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
      annotations:
        vault.hashicorp.com/agent-inject: "true"
        vault.hashicorp.com/role: "myapp"
        vault.hashicorp.com/agent-inject-secret-config: "secret/data/app/production"
        vault.hashicorp.com/agent-inject-template-config: |
          {{- with secret "secret/data/app/production" -}}
          {
            "database_url": "{{ .Data.data.db_url }}",
            "api_key": "{{ .Data.data.api_key }}",
            "redis_url": "{{ .Data.data.redis_url }}"
          }
          {{- end -}}
        vault.hashicorp.com/agent-inject-perms-config: "0644"
        vault.hashicorp.com/agent-pre-populate-only: "true"
    spec:
      serviceAccountName: myapp-vault
      containers:
        - name: myapp
          image: myapp:latest
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: vault-secrets
              mountPath: /vault/secrets
              readOnly: true
      volumes:
        - name: vault-secrets
          emptyDir:
            medium: Memory
```
{% endraw %}

---

## 4. Cloud Secret Management

### 4.1 AWS Secrets Manager

O AWS Secrets Manager fornece gerenciamento automatico de segredos com rotacao integrada.

```bash
# Criar segredo
aws secretsmanager create-secret \
  --name prod/database/credentials \
  --description "Credenciais do banco de dados de producao" \
  --secret-string '{
    "username": "admin",
    "password": "P@ssw0rd123!",
    "engine": "mysql",
    "host": "db.cluster.abc123.us-east-1.rds.amazonaws.com",
    "port": 3306,
    "dbname": "production"
  }'

# Recuperar segredo
aws secretsmanager get-secret-value \
  --secret-id prod/database/credentials \
  --query 'SecretString' \
  --output text | jq .

# Rotacionar segredo manualmente
aws secretsmanager rotate-secret \
  --secret-id prod/database/credentials

# Configurar rotacao automatica
aws secretsmanager put-rotation-config \
  --secret-id prod/database/credentials \
  --rotation-lambda-arn "arn:aws:lambda:us-east-1:123456789:function:SecretRotation" \
  --rotation-rules '{"AutomaticallyAfterDays": 30}'

# Listar todos os segredos
aws secretsmanager list-secrets \
  --query 'SecretList[*].Name' \
  --output table
```

### 4.2 AWS SSM Parameter Store

```bash
# Criar parameter secure
aws ssm put-parameter \
  --name "/prod/database/password" \
  --value "P@ssw0rd123!" \
  --type "SecureString" \
  --description "Senha do banco de dados de producao" \
  --key-id "alias/my-key" \
  --tags "Key=Environment,Value=production"

# Criar parameter de configuracao (nao sensivel)
aws ssm put-parameter \
  --name "/prod/database/host" \
  --value "db.cluster.abc123.us-east-1.rds.amazonaws.com" \
  --type "String"

# Recuperar parameter secure
aws ssm get-parameter \
  --name "/prod/database/password" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text

# Recuperar multiplos parameters com hierarquia
aws ssm get-parameters-by-path \
  --path "/prod/database" \
  --recursive \
  --with-decryption \
  --query 'Parameters[*].[Name,Value]' \
  --output table
```

### 4.3 Azure Key Vault

```bash
# Criar Key Vault
az keyvault create \
  --name mykeyvault \
  --resource-group myResourceGroup \
  --location eastus \
  --sku standard

# Adicionar segredo
az keyvault secret set \
  --vault-name mykeyvault \
  --name database-password \
  --value "P@ssw0rd123!" \
  --content-type "text/plain" \
  --tags environment=production

# Recuperar segredo
az keyvault secret show \
  --vault-name mykeyvault \
  --name database-password \
  --query value \
  --output tsv

# Configurar rotacao automatica
az keyvault set-policy \
  --name mykeyvault \
  --object-id "00000000-0000-0000-0000-000000000000" \
  --secret-permissions set get list
```

### 4.4 Google Cloud Secret Manager

```bash
# Criar segredo
echo -n "P@ssw0rd123!" | gcloud secrets create database-password \
  --data-file=- \
  --replication-policy="automatic" \
  --labels="environment=production"

# Adicionar nova versao
echo -n "NovaP@ssw0rd456!" | gcloud secrets versions add database-password \
  --data-file=-

# Recuperar segredo
gcloud secrets versions access latest \
  --secret="database-password" \
  --format="value(payload.data)" | base64 -d

# Listar segredos
gcloud secrets list --format="table(name,created)"
```

### 4.5 Tabela Comparativa

| Recurso | AWS Secrets Manager | AWS SSM | Azure Key Vault | GCP Secret Manager |
|---------|-------------------|---------|----------------|-------------------|
| Rotacao automatica | Sim | Nao | Via Logic App | Via Cloud Functions |
| Versionamento | Sim | Sim | Sim | Sim |
| Audit logging | CloudTrail | CloudTrail | Monitor | Audit Log |
| Encrypt at rest | KMS | KMS | Azure Key Vault | CMEK/CMSK |
| Max segredos | 50.000 | 10.000 | Ilimitado | Ilimitado |
| Custo por segredo/mes | $0.40 | $0.05 | $0.03 | $0.06 |
| Integacao K8s | External Secrets | External Secrets | CSI Driver | External Secrets |

---

## 5. Kubernetes Secrets

### 5.1 Kubernetes Secrets Nativos

```yaml
# kubernetes/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
  labels:
    app: myapp
    environment: production
type: Opaque
data:
  # Valores devem estar em base64
  # echo -n "valor" | base64
  db-username: YWRtaW4=
  db-password: UEBzc3cwcmQxMjMh
  api-key: MTIzNDU2Nzg5MGFiY2RlZg==

# Usando stringData para valores em texto plano
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets-string
  namespace: production
type: Opaque
stringData:
  config.json: |
    {
      "database_url": "postgresql://admin:password@db:5432/mydb",
      "redis_url": "redis://redis:6379"
    }
```

```yaml
# kubernetes/deployment-using-secrets.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: myapp:latest
          env:
            # Referenciar segredo em variavel de ambiente
            - name: DB_USERNAME
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: db-username
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: db-password
          volumeMounts:
            - name: secrets-volume
              mountPath: /etc/secrets
              readOnly: true
      volumes:
        - name: secrets-volume
          secret:
            secretName: app-secrets
```

### 5.2 Sealed Secrets

Sealed Secrets permite armazenar segredos criptografados no Git, que so podem ser descriptografados pelo controller no cluster.

```bash
# Instalar Sealed Secrets
helm repo add sealed-secrets https://bitnami-labs.github.io/sealed-secrets
helm install sealed-secrets sealed-secrets/sealed-secrets \
  --namespace kube-system

# Criar Sealed Secret
kubectl create secret generic app-secrets \
  --from-literal=db-username=admin \
  --from-literal=db-password='P@ssw0rd123!' \
  --dry-run=client -o yaml | \
  kubeseal --format yaml > kubernetes/sealed-secret.yaml
```

```yaml
# kubernetes/sealed-secret.yaml
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: app-secrets
  namespace: production
spec:
  encryptedData:
    db-username: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEqA4DB3sGm1Z3B2N5K1P8...
    db-password: AgAkb6Xz7qF7cQ90P8M2N4L6K3J5H7G9F1D2A4S6W8Q0E2R4T...
  template:
    metadata:
      name: app-secrets
      namespace: production
      labels:
        app: myapp
```

### 5.3 External Secrets Operator

```yaml
# kubernetes/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: app-secrets
  namespace: production
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: app-secrets
    creationPolicy: Owner
  data:
    - secretKey: db-username
      remoteRef:
        key: prod/database/credentials
        property: username
    - secretKey: db-password
      remoteRef:
        key: prod/database/credentials
        property: password
    - secretKey: api-key
      remoteRef:
        key: prod/api-keys
        property: stripe-key

---
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secrets-manager
  namespace: production
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
            namespace: production
```

### 5.4 CSI Secret Store Driver

```yaml
# kubernetes/secrets-store-csi-driver.yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: aws-secrets
  namespace: production
spec:
  provider: aws
  parameters:
    objects: |
      - objectName: "prod/database/credentials"
        objectType: "secretsmanager"
        jmesPath:
          - path: username
            objectAlias: db-username
          - path: password
            objectAlias: db-password

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp-csi
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      serviceAccountName: myapp-sa
      containers:
        - name: myapp
          image: myapp:latest
          volumeMounts:
            - name: secrets-store
              mountPath: /mnt/secrets
              readOnly: true
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: aws-secrets
```

---

## 6. Environment Variables Seguras

### 6.1 Quando Usar Variaveis de Ambiente

Variaveis de ambiente sao adequadas para:
- Configuracoes de aplicacao nao sensiveis (PORT, LOG_LEVEL, NODE_ENV)
- Segredos em ambientes de desenvolvimento local
- Segredos injetados por plataformas de container orchestration
- Variaveis gerenciadas por ferramentas de segredo (Vault, AWS Secrets Manager)

Variaveis de ambiente NAO devem ser usadas para:
- Segredos em producao sem gestao centralizada
- Secrets hardcoded em scripts de deploy
- Credenciais em arquivos de configuracao versionados

### 6.2 Gerenciamento de Arquivos .env

```bash
# .env.example (commitado no Git — contem placeholders)
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
API_KEY=your-api-key-here
REDIS_URL=redis://localhost:6379
LOG_LEVEL=debug
PORT=3000

# .env (NUNCA commitado — adicionar ao .gitignore)
DATABASE_URL=postgresql://admin:P@ssw0rd@db.empresa.com:5432/production
API_KEY=sk-abc123def456ghi789
REDIS_URL=redis://redis.empresa.com:6379
LOG_LEVEL=info
PORT=8080

# .gitignore
.env
.env.local
.env.*.local
*.env
```

### 6.3 dotenv-linter

```bash
# Instalar dotenv-linter
pip install dotenv-linter

# Verificar arquivos .env
dotenv-linter

# Auto-corrigir problemas
dotenv-linter fix

# Verificar apenas arquivos especificos
dotenv-linter check .env .env.example
```

Exemplo de saida do dotenv-linter:

```
.env:1 UnnecessaryQuotes: The value is unquoted, but you used unnecessary quotes: key="value"
.env:3 LowercaseKey: The key should be in uppercase: database_url
.env:5 LeadingCharacter: The value has leading character: API_KEY= sk-abc123
.env:7 TrailingCharacter: The value has trailing character: PORT=3000 (space)
```

### 6.4 Scripts de Validacao

```bash
#!/bin/bash
# scripts/validate-env.sh
# Valida variaveis de ambiente criticas antes do deploy

set -euo pipefail

REQUIRED_VARS=(
    "DATABASE_URL"
    "API_KEY"
    "REDIS_URL"
    "JWT_SECRET"
    "AWS_ACCESS_KEY_ID"
    "AWS_SECRET_ACCESS_KEY"
)

echo "=== Validando variaveis de ambiente ==="

MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING+=("$var")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERRO: Variaveis de ambiente ausentes:"
    for var in "${MISSING[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Defina as variaveis ausentes e tente novamente."
    exit 1
fi

echo "Todas as variaveis obrigatorias estao configuradas."
```

---

## 7. Certificate Management

### 7.1 Let's Encrypt com Certbot

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obter certificado via nginx
sudo certbot --nginx -d example.com -d www.example.com

# Obter certificado via standalone
sudo certbot certonly --standalone -d example.com

# Renovacao automatica
sudo certbot renew --dry-run

# Verificar certificados ativos
sudo certbot certificates
```

### 7.2 cert-manager para Kubernetes

```yaml
# kubernetes/cert-manager-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@empresa.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx

---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: app-tls
  namespace: production
spec:
  secretName: app-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  commonName: app.empresa.com
  dnsNames:
    - app.empresa.com
    - api.empresa.com
  duration: 2160h
  renewBefore: 360h
  privateKey:
    algorithm: RSA
    size: 2048
  usages:
    - server auth
    - digital signature
    - key encipherment
```

### 7.3 PKI Interno

```python
#!/usr/bin/env python3
"""
pki_interno.py — Gerenciador de PKI interno
"""

import os
import datetime
import json
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class InternalPKI:
    """Gerencia uma PKI interna completa."""

    def __init__(self, ca_dir: str = "./pki"):
        self.ca_dir = ca_dir
        os.makedirs(ca_dir, exist_ok=True)

    def generate_ca(self, common_name: str = "Minha Empresa CA"):
        """Gera uma Certificate Authority root."""
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Minha Empresa LTDA"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

        # Salvar chave privada
        key_path = os.path.join(self.ca_dir, "ca.key")
        with open(key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.BestAvailableEncryption(
                        b"ca-password-change-me"
                    ),
                )
            )
        os.chmod(key_path, 0o600)

        # Salvar certificado
        cert_path = os.path.join(self.ca_dir, "ca.crt")
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"CA gerada com sucesso:")
        print(f"  Chave: {key_path}")
        print(f"  Certificado: {cert_path}")

        return key, cert

    def issue_certificate(
        self,
        ca_key,
        ca_cert,
        common_name: str,
        san_names: list = None,
        days_valid: int = 365,
    ):
        """Emite um certificado assinado pela CA."""
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Minha Empresa LTDA"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])

        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)
            )
        )

        # Adicionar SAN (Subject Alternative Names)
        if san_names:
            san_list = [x509.DNSName(name) for name in san_names]
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )

        # Adicionar usages
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )

        cert = builder.sign(ca_key, hashes.SHA256())

        # Salvar chave e certificado
        cert_dir = os.path.join(self.ca_dir, "certs")
        os.makedirs(cert_dir, exist_ok=True)

        key_path = os.path.join(cert_dir, f"{common_name}.key")
        cert_path = os.path.join(cert_dir, f"{common_name}.crt")

        with open(key_path, "wb") as f:
            f.write(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        os.chmod(key_path, 0o600)

        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"Certificado emitido para {common_name}:")
        print(f"  Chave: {key_path}")
        print(f"  Certificado: {cert_path}")

        return key, cert


if __name__ == "__main__":
    pki = InternalPKI()

    # Gerar CA
    ca_key, ca_cert = pki.generate_ca()

    # Emitir certificado para o servidor web
    pki.issue_certificate(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="web.empresa.com",
        san_names=["web.empresa.com", "www.empresa.com", "empresa.com"],
        days_valid=365,
    )

    # Emitir certificado para API
    pki.issue_certificate(
        ca_key=ca_key,
        ca_cert=ca_cert,
        common_name="api.empresa.com",
        san_names=["api.empresa.com"],
        days_valid=365,
    )
```

---

## 8. Key Rotation

### 8.1 Estrategias de Rotacao Automatizada

```python
#!/usr/bin/env python3
"""
key_rotation.py — Sistema de rotacao automatizada de chaves
"""

import os
import json
import boto3
import datetime
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class RotationConfig:
    """Configuracao de rotacao para um segredo."""
    secret_name: str
    rotation_interval_days: int
    max_age_days: int
    notification_email: Optional[str] = None
    auto_rotate: bool = True


class KeyRotationManager:
    """Gerencia rotacao automatica de chaves e segredos."""

    def __init__(self):
        self.secrets_manager = boto3.client("secretsmanager")
        self.configs: Dict[str, RotationConfig] = {}

    def register_secret(self, config: RotationConfig):
        """Registra um segredo para rotacao automatica."""
        self.configs[config.secret_name] = config
        print(f"Segredo registrado: {config.secret_name}")

    def check_and_rotate(self):
        """Verifica e rotaciona segredos que atingiram o intervalo."""
        for name, config in self.configs.items():
            try:
                response = self.secrets_manager.describe_secret(SecretId=name)
                last_rotated = response.get("LastRotatedDate")

                if last_rotated is None:
                    print(f"[{name}] Nunca rotacionado. Rotacionando...")
                    self._rotate_secret(name, config)
                    continue

                days_since_rotation = (
                    datetime.datetime.now(datetime.timezone.utc) - last_rotated
                ).days

                if days_since_rotation >= config.rotation_interval_days:
                    print(
                        f"[{name}] {days_since_rotation} dias desde ultima rotacao. "
                        f"Intervalo: {config.rotation_interval_days} dias. Rotacionando..."
                    )
                    self._rotate_secret(name, config)
                else:
                    remaining = config.rotation_interval_days - days_since_rotation
                    print(f"[{name}] Proxima rotacao em {remaining} dias.")

            except Exception as e:
                print(f"[{name}] Erro ao verificar: {e}")

    def _rotate_secret(self, name: str, config: RotationConfig):
        """Rotaciona um segredo especifico."""
        try:
            # Gerar novo valor
            new_value = self._generate_secret_value(name)

            # Atualizar no Secrets Manager
            self.secrets_manager.update_secret(
                SecretId=name,
                SecretString=new_value,
            )

            # Configurar rotacao automatica se habilitada
            if config.auto_rotate:
                self.secrets_manager.put_secret_rotation_configuration(
                    SecretId=name,
                    RotationConfiguration={
                        "AutomaticallyAfterDays": config.rotation_interval_days,
                        "RotateImmediately": False,
                    },
                )

            print(f"[{name}] Rotacao concluida com sucesso.")

        except Exception as e:
            print(f"[{name}] Erro na rotacao: {e}")

    def _generate_secret_value(self, name: str) -> str:
        """Gera um novo valor para o segredo."""
        import secrets
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_password = "".join(
            secrets.choice(alphabet) for _ in range(32)
        )

        # Preservar formato se existir
        if "database" in name.lower():
            current = self.secrets_manager.get_secret_value(SecretId=name)
            try:
                data = json.loads(current["SecretString"])
                data["password"] = new_password
                return json.dumps(data)
            except json.JSONDecodeError:
                pass

        return new_password


def lambda_handler(event, context):
    """AWS Lambda handler para rotacao automatica."""
    manager = KeyRotationManager()

    # Registrar segredos para rotacao
    manager.register_secret(RotationConfig(
        secret_name="prod/database/credentials",
        rotation_interval_days=30,
        max_age_days=90,
        auto_rotate=True,
    ))

    manager.register_secret(RotationConfig(
        secret_name="prod/api-keys/stripe",
        rotation_interval_days=90,
        max_age_days=180,
        auto_rotate=False,
    ))

    manager.check_and_rotate()

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Rotacao verificada"}),
    }
```

### 8.2 Rotacao com Zero Downtime

```yaml
# kubernetes/zero-downtime-rotation.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: secret-rotation
  namespace: production
spec:
  backoffLimit: 3
  template:
    spec:
      serviceAccountName: rotation-sa
      containers:
        - name: rotator
          image: myapp-rotator:latest
          env:
            - name: SECRET_NAME
              value: "app-secrets"
            - name: ROTATION_MODE
              value: "zero-downtime"
          command:
            - /bin/bash
            - -c
            - |
              # 1. Gerar novo segredo
              NEW_PASSWORD=$(openssl rand -base64 32)
              
              # 2. Atualizar secret no Kubernetes
              kubectl create secret generic app-secrets-new \
                --from-literal=db-password="$NEW_PASSWORD" \
                -n production \
                --dry-run=client -o yaml | \
                kubectl apply -f -
              
              # 3. Rolling update do deployment para usar novo secret
              kubectl set env deployment/myapp \
                DB_PASSWORD="$NEW_PASSWORD" \
                -n production
              
              # 4. Aguardar rollout completar
              kubectl rollout status deployment/myapp \
                -n production \
                --timeout=300s
              
              # 5. Remover secret antigo
              kubectl delete secret app-secrets \
                -n production \
                --ignore-not-found
              
              # 6. Renomear novo secret
              kubectl patch secret app-secrets-new \
                -n production \
                -p '{"metadata":{"name":"app-secrets"}}'
              
              echo "Rotacao concluida com zero downtime"
      restartPolicy: OnFailure
```

### 8.3 Rotacao no Vault

```bash
# Configurar rotacao automatica no Vault
vault write database/roles/readonly \
  db_name=postgres \
  default_ttl="1h" \
  max_ttl="24h"

# Renovar lease de um segredo
vault lease renew database/creds/readonly/abc123

# Revogar todas as credenciais de uma role
vault lease revoke -prefix database/creds/readonly

# Configurar TTL maximo para todas as credenciais de um path
vault write sys/leases/tune max-ttl=86400s database/creds/readonly
```

---

## 9. Exemplo Completo: Secret Management Pipeline

### 9.1 Fluxo: Generate, Store, Distribute, Rotate, Audit

Este exemplo demonstra um pipeline completo de gestao de segredos integrando Vault, Kubernetes e CI/CD.

```yaml
# kubernetes/vault-secrets-pipeline.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: secret-pipeline-config
  namespace: vault-system
data:
  pipeline-config.json: |
    {
      "stages": {
        "generate": {
          "method": "vault transit",
          "key_type": "aes256-gcm96",
          "auto_generate": true
        },
        "store": {
          "backend": "vault kv v2",
          "path_prefix": "secret/data/pipeline",
          "versioning": true
        },
        "distribute": {
          "methods": ["kubernetes-secrets", "external-secrets"],
          "sync_interval": "5m"
        },
        "rotate": {
          "strategy": "zero-downtime",
          "interval_days": 30,
          "grace_period_days": 7
        },
        "audit": {
          "enable": true,
          "log_path": "/vault/audit/secret-access.log",
          "retention_days": 90
        }
      }
    }
```

```bash
#!/bin/bash
# scripts/secret-pipeline.sh
# Pipeline completo de gestao de segredos

set -euo pipefail

export VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
export VAULT_TOKEN="${VAULT_TOKEN:-}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[PIPELINE]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error() { echo -e "${RED}[ERRO]${NC} $1"; }

# ============================================================
# ESTAGIO 1: Gerar segredos
# ============================================================
generate_secrets() {
    log "=== Estagio 1: Geracao de Segredos ==="

    # Gerar senha de banco de dados
    DB_PASSWORD=$(openssl rand -base64 32)
    log "Senha de banco gerada"

    # Gerar JWT secret
    JWT_SECRET=$(openssl rand -hex 32)
    log "JWT secret gerado"

    # Gerar API key
    API_KEY=$(openssl rand -base64 48 | tr -d '\n')
    log "API key gerada"

    # Gerar encryption key
    ENC_KEY=$(openssl rand -hex 32)
    log "Encryption key gerada"

    # Salvar no Vault
    vault kv put secret/data/pipeline/production \
        db-password="$DB_PASSWORD" \
        jwt-secret="$JWT_SECRET" \
        api-key="$API_KEY" \
        encryption-key="$ENC_KEY" \
        db-username="app_user" \
        db-host="db.empresa.com" \
        db-port="5432" \
        db-name="production"

    log "Segredos salvos no Vault"
}

# ============================================================
# ESTAGIO 2: Armazenar com versionamento
# ============================================================
store_secrets() {
    log "=== Estagio 2: Armazenamento com Versionamento ==="

    # Listar versoes atuais
    CURRENT_VERSION=$(vault kv get -version=-1 secret/data/pipeline/production 2>/dev/null | grep "VERSION" | awk '{print $2}' || echo "0")
    log "Versao atual: $CURRENT_VERSION"

    # Criar backup da versao anterior
    if [ "$CURRENT_VERSION" != "0" ]; then
        vault kv get -version=-1 -format=json secret/data/pipeline/production | \
            jq '.data.data' > "backup-v${CURRENT_VERSION}-$(date +%Y%m%d).json"
        log "Backup da versao $CURRENT_VERSION criado"
    fi

    log "Armazenamento concluido"
}

# ============================================================
# ESTAGIO 3: Distribuir para Kubernetes
# ============================================================
distribute_secrets() {
    log "=== Estagio 3: Distribuicao ==="

    # Recuperar segredos do Vault
    SECRETS=$(vault kv get -format=json secret/data/pipeline/production | jq '.data.data')

    DB_PASSWORD=$(echo "$SECRETS" | jq -r '."db-password"')
    JWT_SECRET=$(echo "$SECRETS" | jq -r '."jwt-secret"')
    API_KEY=$(echo "$SECRETS" | jq -r '."api-key"')

    # Criar/atualizar Secret no Kubernetes
    kubectl create secret generic app-secrets \
        --namespace=production \
        --from-literal=DB_PASSWORD="$DB_PASSWORD" \
        --from-literal=JWT_SECRET="$JWT_SECRET" \
        --from-literal=API_KEY="$API_KEY" \
        --dry-run=client -o yaml | \
        kubectl apply -f -

    # Verificar se o secret foi criado corretamente
    kubectl get secret app-secrets -n production -o jsonpath='{.data.DB_PASSWORD}' | \
        base64 -d > /dev/null && \
        log "Secret distribuido com sucesso" || \
        error "Falha na distribuicao do secret"

    # Atualizar deployments que usam o secret
    kubectl rollout restart deployment/myapp -n production
    log "Deployments reiniciados para usar novos segredos"
}

# ============================================================
# ESTAGIO 4: Rotacionar segredos antigos
# ============================================================
rotate_secrets() {
    log "=== Estagio 4: Rotacao de Chaves ==="

    # Verificar idade dos segredos atuais
    SECRET_METADATA=$(vault kv metadata get secret/data/pipeline/production -format=json 2>/dev/null)

    if [ $? -eq 0 ]; then
        CREATED=$(echo "$SECRET_METADATA" | jq -r '.data.created_time' | head -1)
        log "Ultimo segredo criado em: $CREATED"
    fi

    # Gerar novos segredos
    generate_secrets

    # Distribuir novos segredos
    distribute_secrets

    # Revogar leases antigos do Vault
    vault lease revoke -prefix database/creds/readonly 2>/dev/null || true
    log "Leases antigos revogados"

    # Executar verificacao pos-rotacao
    kubectl exec -n production deployment/myapp -- \
        /bin/sh -c "wget -q -O- http://localhost:8080/health" && \
        log "Aplicacao saudavel apos rotacao" || \
        warn "Aplicacao pode estar com problemas apos rotacao"
}

# ============================================================
# ESTAGIO 5: Auditar acessos
# ============================================================
audit_secrets() {
    log "=== Estagio 5: Auditoria ==="

    # Verificar audit logs do Vault
    if [ -f "/vault/file/vault-audit.log" ]; then
        AUDIT_COUNT=$(wc -l < /vault/file/vault-audit.log)
        log "Audit log contem $AUDIT_COUNT registros"

        # Ultimos 10 acessos
        log "Ultimos 10 acessos a segredos:"
        tail -10 /vault/file/vault-audit.log | jq -r \
            '"  \(.time) - \(.request.path) - \(.auth.policies // ["unknown"])"' 2>/dev/null || true
    fi

    # Verificar uso de segredos no Kubernetes
    log "Segredos ativos no Kubernetes:"
    kubectl get secrets -n production -o custom-columns=\
"NAME:.metadata.name,AGE:.metadata.creationTimestamp,TYPE:.type" 2>/dev/null || true

    # Gerar relatorio
    REPORT="secret-audit-$(date +%Y%m%d-%H%M%S).json"
    cat > "$REPORT" <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "vault_audit_log_lines": $(wc -l < /vault/file/vault-audit.log 2>/dev/null || echo 0),
    "kubernetes_secrets_count": $(kubectl get secrets -n production --no-headers 2>/dev/null | wc -l || echo 0),
    "last_rotation": "$(date -Iseconds)"
}
EOF

    log "Relatorio de auditoria gerado: $REPORT"
}

# ============================================================
# Executar pipeline completo
# ============================================================
main() {
    log "Iniciando pipeline de gestao de segredos"
    log "Timestamp: $(date -Iseconds)"

    generate_secrets
    store_secrets
    distribute_secrets
    rotate_secrets
    audit_secrets

    log "Pipeline de segredos concluido com sucesso!"
}

# Executar com tratamento de erros
trap 'error "Pipeline falhou na linha $LINENO"; exit 1' ERR

main "$@"
```

### 9.2 Dashboard de Status

```python
#!/usr/bin/env python3
"""
secret_dashboard.py — Dashboard de status dos segredos
"""

import json
import subprocess
from datetime import datetime, timezone
from typing import List, Dict


class SecretDashboard:
    """Dashboard para monitoramento de segredos."""

    def __init__(self):
        self.vault_addr = "http://127.0.0.1:8200"

    def get_vault_secrets(self) -> List[Dict]:
        """Lista todos os segredos no Vault."""
        try:
            result = subprocess.run(
                ["vault", "kv", "list", "-format=json", "secret/"],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError:
            return []

    def get_kubernetes_secrets(self) -> List[Dict]:
        """Lista segredos no Kubernetes."""
        try:
            result = subprocess.run(
                ["kubectl", "get", "secrets", "-n", "production",
                 "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            data = json.loads(result.stdout)
            return data.get("items", [])
        except subprocess.CalledProcessError:
            return []

    def check_secret_age(self, secret_name: str) -> Dict:
        """Verifica a idade de um segredo."""
        try:
            result = subprocess.run(
                ["vault", "kv", "metadata", "get", "-format=json",
                 f"secret/data/{secret_name}"],
                capture_output=True,
                text=True,
                check=True,
            )
            metadata = json.loads(result.stdout)
            versions = metadata.get("data", {}).get("versions", {})

            if versions:
                latest_version = max(versions.keys(), key=lambda v: versions[v]["created_time"])
                created = datetime.fromisoformat(
                    versions[latest_version]["created_time"].replace("Z", "+00:00")
                )
                age_days = (datetime.now(timezone.utc) - created).days

                return {
                    "name": secret_name,
                    "version": latest_version,
                    "created": versions[latest_version]["created_time"],
                    "age_days": age_days,
                    "status": "healthy" if age_days < 30 else "needs_rotation",
                }
        except Exception as e:
            return {
                "name": secret_name,
                "status": "error",
                "error": str(e),
            }

    def generate_report(self) -> str:
        """Gera relatorio completo de status."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vault_secrets": [],
            "kubernetes_secrets": [],
            "summary": {
                "total_secrets": 0,
                "healthy": 0,
                "needs_rotation": 0,
                "errors": 0,
            },
        }

        # Verificar segredos do Vault
        vault_paths = self.get_vault_secrets()
        for path in vault_paths:
            status = self.check_secret_age(path)
            report["vault_secrets"].append(status)

            if status["status"] == "healthy":
                report["summary"]["healthy"] += 1
            elif status["status"] == "needs_rotation":
                report["summary"]["needs_rotation"] += 1
            else:
                report["summary"]["errors"] += 1

        # Verificar segredos do Kubernetes
        k8s_secrets = self.get_kubernetes_secrets()
        report["kubernetes_secrets"] = [
            {
                "name": s["metadata"]["name"],
                "age": s["metadata"].get("creationTimestamp", "unknown"),
            }
            for s in k8s_secrets
        ]

        report["summary"]["total_secrets"] = (
            report["summary"]["healthy"]
            + report["summary"]["needs_rotation"]
            + report["summary"]["errors"]
        )

        return json.dumps(report, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    dashboard = SecretDashboard()
    report = dashboard.generate_report()
    print(report)
```

---

## 10. Referencias

### Documentacao Oficial

- HashiCorp Vault Documentation — https://developer.hashicorp.com/vault/docs
- AWS Secrets Manager User Guide — https://docs.aws.amazon.com/secretsmanager/
- Azure Key Vault Documentation — https://learn.microsoft.com/en-us/azure/key-vault/
- Google Cloud Secret Manager — https://cloud.google.com/secret-manager/docs
- Kubernetes Secrets — https://kubernetes.io/docs/concepts/configuration/secret/
- Sealed Secrets — https://sealed-secrets.netlify.app/
- External Secrets Operator — https://external-secrets.io/
- cert-manager — https://cert-manager.io/docs/

### Ferramentas de Deteccao

- GitLeaks — https://github.com/gitleaks/gitleaks
- TruffleHog — https://github.com/trufflesecurity/trufflehog
- detect-secrets — https://github.com/Yelp/detect-secrets
- GitHub Secret Scanning — https://docs.github.com/en/code-security/secret-scanning

### Casos de Estudo e Relatorios

- GitGuardian State of Secrets Sprawl 2024 — https://www.gitguardian.com/state-of-secrets-sprawl-report-2024
- IBM Cost of a Data Breach Report 2023 — https://www.ibm.com/security/data-breach
- OWASP Secrets Management Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- NIST SP 800-53 Rev. 5 — Controles de Seguranca — https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final

### Artigos e Publicacoes

- "How We Discovered Secrets in Uber's Production Infrastructure" — Security Research, 2019
- "Secrets Sprawl in the Cloud" — Datadog Security Labs, 2023
- "Protecting Secrets in Kubernetes" — CNCF Security Whitepaper, 2023
- "Vault Best Practices" — HashiCorp Learn, 2024
- "AWS Secrets Manager Best Practices" — AWS Documentation, 2024

### Comunidade

- HashiCorp User Group — https://www.hashicorp.com/community
- Kubernetes Slack #security — https://kubernetes.slack.com
- OWASP DevSecOps Guideline — https://owasp.org/www-project-devsecops-guideline/
- CNCF Security Technical Advisory Group — https://github.com/cncf/tag-security

---

## Resumo do Capitulo

A gestao eficaz de segredos e um pilar fundamental do DevSecOps. Neste capitulo, exploramos:

1. **Por que importa**: Segredos vazados sao o vetor de ataque mais comum. Casos reais da Uber, GitHub, Docker, Terraform, npm e Twilio demonstram o impacto real.

2. **Deteccao**: GitLeaks, TruffleHog e detect-secrets formam uma barreira de defesa em camadas. GitHub Secret Scanning adiciona protecao nativa.

3. **HashiCorp Vault**: A solucao de referencia para gestao centralizada, com dynamic secrets, transit engine e PKI engine.

4. **Cloud Secret Management**: AWS, Azure e GCP oferecem solucoes nativas com trade-offs distintos de custo e funcionalidade.

5. **Kubernetes Secrets**: Desde secrets nativos ate Sealed Secrets, External Secrets Operator e CSI Secret Store.

6. **Environment Variables**: Uso adequado, gerenciamento de .env e validacao automatizada.

7. **Certificate Management**: Let's Encrypt, cert-manager e PKI interno para gestao completa de certificados.

8. **Key Rotation**: Estrategias automatizadas com zero downtime e integracao com Vault.

9. **Pipeline Completo**: O fluxo Generate, Store, Distribute, Rotate, Audit com implementacao real em Vault e Kubernetes.

A gestao de segredos nao e opcional — e um requisito de seguranca basico que deve ser implementado desde o primeiro dia de desenvolvimento.
