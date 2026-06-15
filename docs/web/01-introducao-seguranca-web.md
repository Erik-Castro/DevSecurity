# Capítulo 01 — Introdução à Segurança Web

> *"Não existe sistema seguro — existe sistema que ainda não foi comprometido."*

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

1. Compreender a evolução histórica da segurança web e como as vulnerabilidades modernas surgiram a partir de decisões arquiteturais passadas.
2. Aplicar modelos de ameaça estruturados (STRIDE, PASTA) para identificar riscos em aplicações web.
3. Descrever a arquitetura típica de uma aplicação web moderna e mapear superfícies de ataque em cada camada.
4. Implementar headers de segurança HTTP corretamente, incluindo CSP, HSTS, X-Content-Type-Options e X-Frame-Options.
5. Configurar Same-Origin Policy e CORS de forma segura, evitando os erros mais comuns.
6. Definir cookies com atributos Secure, HttpOnly e SameSite apropriados para cada cenário.
7. Diferenciar sessões baseadas em cookies de tokens (JWT, OAuth 2.0, OpenID Connect) e escolher o modelo correto para cada caso de uso.
8. Entender o handshake TLS/SSL, cipher suites e como o HSTS protege contra downgrade attacks.
9. Compreender DNSSEC, DoH e DoT como camadas de segurança adicionais.
10. Configurar um laboratório local com OWASP Juice Shop, DVWA e WebGoat para prática hands-on.

---

## 2. História da Segurança Web: de CGI Bins a SPAs Modernas

### 2.1 A Era CGI (1993–1998)

A web começou como um sistema estático de distribuição de documentos. Em 1993, o Common Gateway Interface (CGI) transformou a web de um sistema passivo em uma plataforma interativa. Programadores escreviam scripts em Perl, C ou shell que rodavam no servidor e geravam HTML dinamicamente.

```bash
#!/bin/bash
# CGI bin típico dos anos 90 — sem sanitização de input
QUERY_STRING="$QUERY_STRING"
echo "Content-Type: text/html"
echo ""
echo "<html><body>"
echo "<h1>Busca: $QUERY_STRING</h1>"
# Vulnerabilidade: command injection via QUERY_STRING
echo "</body></html>"
```

Nessa era, o conceito de "segurança web" praticamente não existia. Os scripts CGI:

- Rodavam com permissões do servidor web (frequentemente root ou www-data).
- Não tinham sanitização de entrada — o input do usuário era passado diretamente para comandos do sistema operacional.
- Não havia distinção entre dados e código — um parâmetro de URL podia injetar comandos arbitrários.
- Não existiam frameworks de segurança — cada programador reinventava a roda (ou simplesmente ignorava o problema).

O primeiro ataque amplamente documentado contra uma aplicação CGI foi o **remote code execution** via variáveis de ambiente em 1995, quando o PHF CGI do NCSA HTTPd permitia execução remota de comandos através de newlines injetados no parâmetro `q`.

```
# O clássico PHF exploit
http://vulnerable-server/cgi-bin/phf?Qalias=x%0a/bin/cat%20/etc/passwd
```

### 2.2 A Era das CGI e Scripting (1995–2000)

Com a chegada do PHP (1995), Perl CGI, ASP (1996) e JSP (1997), a web dinâmica se popularizou. Mas a segurança continuou sendo uma questão secundária.

```php
// PHP típico de 1997 — SQL injection trivial
$result = mysql_query("SELECT * FROM users WHERE id = '$_GET[id]'");
```

Nessa época surgiram as primeiras categorias de vulnerabilidades web que ainda existem hoje:

- **SQL Injection**: O primeiro artigo acadêmico sobre SQL injection foi publicado por Jeff Forristal em 1998, mas o conceito era praticamente desconhecido fora de círculos de segurança.
- **Cross-Site Scripting (XSS)**: Marc Slemko documentou o primeiro caso de XSS em 1998 em um newsgroup do Apache.
- **Session Hijacking**: Cookies de sessão eram frequentemente transmitidos sem criptografia, facilitando roubo de sessões.

### 2.3 A Era Web 2.0 (2004–2010)

O termo "Web 2.0" marcou a transição de páginas estáticas para aplicações ricas baseadas em AJAX, RSS, e conteúdo gerado pelo usuário. Essa transição multiplicou superfícies de ataque:

```javascript
// AJAX típico de Web 2.0 — sem validação de origin
var xhr = new XMLHttpRequest();
xhr.open('GET', '/api/userdata?token=' + stolenToken, true);
xhr.send();
```

Foi nessa era que surgiram:

- **CSRF (Cross-Site Request Forgery)**: Aplicações confiavam em cookies automaticamente, permitindo que sites maliciosos executassem ações em nome do usuário autenticado.
- **XSS Persistente (Stored XSS)**: Fóruns, wikis e redes sociais permitiam que atacantes injetassem scripts que afetavam outros usuários.
- **Subversions of Trust**: O modelo de same-origin era flexível o suficiente para permitir ataques sophisticated.
- **OWASP Top 10 (2004)**: A primeira versão do OWASP Top 10 foi publicada em 2004, estabelecendo um padrão para categorização de riscos.

### 2.4 A Era Moderna: SPAs, APIs e Cloud (2010–Presente)

A ascensão de single-page applications (SPAs), microservices e cloud computing transformou radicalmente a superfície de ataque:

```
Timeline da Segurança Web:

1993 ── CGI Bins ──────────────── Sem sanitização, execução direta
1995 ── PHP/ASP/JSP ───────────── SQL injection, XSS nascem
1998 ── Primeiros papers ──────── Jeff Forristal documenta SQLi
2004 ── OWASP Top 10 v1 ──────── Primeira categorização formal
2005 ── CSRF awareness ────────── CSRF entra no radar mainstream
2010 ── SPAs + AJAX ───────────── CORS, CSP, novos headers
2013 ── OAuth 2.0 RFC 6749 ────── Padrão de autorização para APIs
2015 ── HSTS preload ──────────── Browsers comecam aforcar HTTPS
2017 ── Equifax breach ────────── 147M registros expostos
2020 ── SolarWinds ────────────── Supply chain attack
2021 ── Log4Shell ─────────────── JNDI injection em escala global
2023 ── MOVEit/3CX ────────────── SQLi e supply chain
2024 ── xz-utils backdoor ─────── Comprometimento de build system
```

### 2.5 Lições da História

A história da segurança web revela padrões que se repetem:

| Padrão | Exemplo Histórico | Lição |
|--------|-------------------|-------|
| Input confiável | CGI bins, PHP `$_GET` | Nunca confie em input do cliente |
| Defaults perigosos | CORS `*`, cookies sem HttpOnly | Defaults devem ser seguros |
| Complexidade crescente | OAuth 2.0 flows, CSP directives | Mais features = mais superfície de ataque |
| Confiança cega | Cookies cross-site, same-origin flexível | Confiança deve ser verificada |
| Retrocompatibilidade | TLS 1.0, SSL 3.0 | Legacy é a maior ameaça à segurança |
| Supply chain | SolarWinds, xz-utils, Log4Shell | Confie, mas verifique |

---

## 3. Modelo de Ameaça para Aplicações Web

### 3.1 Por Que Threat Modeling?

Antes de codificar uma única linha, é necessário entender **quem** pode atacar, **como** pode atacar e **o que** está em risco. Threat modeling é o processo estruturado de identificar esses fatores.

Sem threat modeling, desenvolvedores focam em vulnerabilidades conhecidas e ignoram vetores de ataque específicos do contexto da aplicação. É a diferença entre proteger contra uma lista genérica de ataques e proteger contra ataques reais contra **seu** sistema.

### 3.2 STRIDE

STRIDE é um modelo de ameaça desenvolvido pela Microsoft em 1999, amplamente utilizado até hoje. Cada letra representa uma categoria de ameaça:

| Categoria | Descrição | Exemplo Web | Mitigation |
|-----------|-----------|-------------|------------|
| **S**poofing | Assumir identidade falsa | Cookie theft, session hijacking | MFA, tokens assinados |
| **T**ampering | Modificar dados não autorizadamente | SQL injection, parameter tampering | Input validation, signatures |
| **R**epudiation | Negação de ações realizadas | Usuário nega ter feito transação | Audit logs, non-repudiation |
| **I**nformation Disclosure | Exposição de dados sensíveis | Path traversal, verbose errors | Encryption, least privilege |
| **D**enial of Service | Tornar serviço indisponível | DDoS, ReDoS, slow loris | Rate limiting, WAF, CDNs |
| **E**levation of Privilege | Ganhar acesso não autorizado | IDOR, privilege escalation | Authorization checks, RBAC |

#### Aplicando STRIDE em uma aplicação web

Considere uma aplicação de e-commerce com as seguintes funcionalidades:

```
┌─────────────────────────────────────────────────┐
│              E-COMMERCE APPLICATION              │
├─────────────────────────────────────────────────┤
│                                                  │
│  [User] ──login──> [Auth Service]                │
│     │                   │                        │
│     │              [Session Store]               │
│     │                                            │
│     ├──browse──> [Product Catalog]               │
│     │                   │                        │
│     ├──search──> [Search Engine]                 │
│     │                                            │
│     ├──cart───> [Cart Service]                   │
│     │                   │                        │
│     ├──order──> [Payment Gateway]                │
│     │                   │                        │
│     ├──review─> [Review System]                  │
│     │                                            │
│     └──profile> [User Data Store]                │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Análise STRIDE por componente:**

**Spoofing — Login/Auth Service:**
- Ameaça: Atacante rouba sessão de usuário para acessar contas.
- Vetor: XSS para extrair cookies de sessão.
- Mitigation: HttpOnly cookies, MFA, tokens de curta duração.

**Tampering — Product Catalog:**
- Ameaça: Atacante modifica preços de produtos via parâmetros de request.
- Vetor: Manipulação de parâmetros no checkout (`price=0.01`).
- Mitigation: Validação server-side, nunca confiar em preço do cliente.

**Repudiation — Review System:**
- Ameaça: Usuário publica review ofensiva e depois nega.
- Vetor: Falta de audit log.
- Mitigation: Logs imutáveis com timestamp, IP e hash de integridade.

**Information Disclosure — User Data Store:**
- Ameaça: Vazamento de dados pessoais de usuários.
- Vetor: IDOR (`/api/users/123` → `/api/users/456`).
- Mitigation: Authorization checks, dados encriptados at rest.

**Denial of Service — Search Engine:**
- Ameaça: Queries complexas que consomem recursos do servidor.
- Vetor: ReDoS em regex de busca.
- Mitigation: Rate limiting, queries com timeout, regex seguras.

**Elevation of Privilege — Cart Service:**
- Ameaça: Usuário comum acessa endpoints de admin.
- Vetor: Falta de verificação de role no backend.
- Mitigation: RBAC, authorization middleware em cada endpoint.

### 3.3 PASTA (Penetration Attack Simulated Threat Analysis)

PASTA é um modelo de ameaça de 7 estágios que combina análise de negócios com técnicas de segurança ofensiva:

```
Estágio 1: Definir objetivos de segurança
    │
    v
Estágio 2: Definir escopo técnico
    │
    v
Estágio 3: Aplicar modelo de decomposição de aplicação
    │
    v
Estágio 4: Análise de ameaças
    │
    v
Estágio 5: Vulnerabilidade e fraqueza analysis
    │
    v
Estágio 6: Análise de exploit e ataque
    │
    v
Estágio 7: Impacto e risco quantificado
```

#### Estágio 1: Objetivos de Segurança

```
business_goals:
  - proteger_dados_clientes: CRITICO
  - disponibilidade_99.9: ALTO
  - compliance_pci_dss: OBRIGATORIO
  - protecao_reputacao: ALTO

security_requirements:
  - autenticacao_mfa: OBRIGATORIO
  - criptografia_em_transito: OBRIGATORIO
  - criptografia_em_reposicao: OBRIGATORIO
  - logging_auditoria: OBRIGATORIO
  - rate_limiting: ALTO
```

#### Estágio 2: Escopo Técnico

```
technology_stack:
  frontend:
    - React 18 (SPA)
    - TypeScript
    - Webpack
  backend:
    - Node.js 20 LTS
    - Express.js
    - TypeScript
  database:
    - PostgreSQL 16
    - Redis 7
  infrastructure:
    - AWS ECS Fargate
    - CloudFront CDN
    - Route 53 DNS
    - ALB (Application Load Balancer)
```

#### Estágio 3: Decomposição da Aplicação

```yaml
data_flows:
  user_to_alb:
    protocol: HTTPS (TLS 1.3)
    port: 443
    authentication: TLS client cert (optional)
    encryption: AES-256-GCM

  alb_to_ecs:
    protocol: HTTP (internal VPC)
    port: 3000
    trust_boundary: VPC

  ecs_to_rds:
    protocol: PostgreSQL TLS
    port: 5432
    authentication: IAM authentication
    encryption: AES-256

  ecs_to_redis:
    protocol: Redis TLS
    port: 6379
    authentication: AUTH token
    encryption: TLS 1.2+

trust_boundaries:
  - internet_to_vpc: ALB (WAF enabled)
  - vpc_to_rds: Security groups
  - ecs_to_external: NAT gateway (restricted)
```

#### Estágio 4: Análise de Ameaças

```
threats:
  - id: T001
    name: SQL Injection via search
    stride: Tampering
    component: Search Engine
    likelihood: ALTA
    impact: CRITICO

  - id: T002
    name: Session hijacking via XSS
    stride: Spoofing
    component: Frontend
    likelihood: MEDIA
    impact: ALTO

  - id: T003
    name: IDOR em user profile
    stride: Information Disclosure
    component: User Data Store
    likelihood: ALTA
    impact: ALTO

  - id: T004
    name: ReDoS em search queries
    stride: Denial of Service
    component: Search Engine
    likelihood: MEDIA
    impact: MEDIO

  - id: T005
    name: Privilege escalation via API
    stride: Elevation of Privilege
    component: Auth Service
    likelihood: BAIXA
    impact: CRITICO
```

#### Estágio 5: Vulnerabilidades

```
vulnerabilities:
  - threat: T001
    vulns:
      - CWE-89: SQL Injection
      - CWE-116: Improper encoding
    mitigations:
      - Parameterized queries
      - Input validation (whitelist)
      - ORM with safe query building

  - threat: T002
    vulns:
      - CWE-79: Cross-Site Scripting
      - CWE-614: Sensitive cookie without Secure flag
    mitigations:
      - Content Security Policy
      - Output encoding
      - HttpOnly + Secure cookies
```

#### Estágio 6: Análise de Exploit

```
attack_chains:
  - chain_id: AC001
    name: "XSS → Session Theft → Account Takeover"
    steps:
      - attacker_submits_comment_with_xss_payload
      - victim_views_comment_page
      - xss_executes_and_exfiltrates_session_cookie
      - attacker_uses_stolen_session
    tools:
      - Burp Suite
      - Custom XSS payloads
    difficulty: MEDIA

  - chain_id: AC002
    name: "IDOR → PII Exposure → Data Breach"
    steps:
      - attacker_enumerates_user_ids
      - attacker_modifies_id_in_api_request
      - api_returns_other_users_data
      - attacker_mass_extracts_data
    tools:
      - Burp Suite Intruder
      - Python scripts
    difficulty: BAIXA
```

#### Estágio 7: Impacto e Risco

```
risk_matrix:
  - threat: T001 (SQLi)
    likelihood: 4 (Alta)
    impact: 5 (Critico)
    risk_score: 20
    risk_level: CRITICO
    business_impact: "Exposição de dados de pagamento, multa PCI DSS"

  - threat: T002 (XSS)
    likelihood: 3 (Media)
    impact: 4 (Alto)
    risk_score: 12
    risk_level: ALTO
    business_impact: "Account takeover em massa, perda de confiança"
```

### 3.4 Comparação: STRIDE vs PASTA

| Aspecto | STRIDE | PASTA |
|---------|--------|-------|
| Origem | Microsoft (1999) | OWASP (2012) |
| Foco | Categorias de ameaça | Processo de análise |
| Abordagem | Asset-centric | Attack-centric |
| Complexidade | Simples | Completo |
| Melhor para | Quick assessments | Deep security analysis |
| Output | Lista de ameaças | Risk quantified report |
| Requer expertise | Baixa | Alta |

### 3.5 Outros Modelos de Ameaça

#### LINDDUN (Privacy Threat Modeling)

Especializado em privacidade de dados — complementar ao STRIDE para aplicações que tratam PII:

| Categoria | Foco | Exemplo |
|-----------|------|---------|
| Linking | Conectar identidades | Cross-device tracking |
| Identifying | Identificar indivíduos | Nome real em logs |
| Non-repudiation | Impedir denegação | Logs imutáveis demais |
| Detecting | Detectar atividade | Side-channel leaks |
| Unawareness | Usuário não sabe | Dark patterns |
| Non-compliance | Viola regulations | GDPR, LGPD |
| Exposing | Revelar dados | Data breaches |

#### Attack Trees

```
                    [Comprometer conta de usuário]
                           /              \
                          /                \
                [Roubear sessão]      [Quebrar senha]
                /          \                |
               /            \               |
     [XSS cookie theft]  [Session fixation] [Brute force]
           |                    |                |
           |                    |                |
    [Stored XSS]          [Lack of token    [No rate limit]
           |               rotation]        [No lockout]
           |                    |                |
    [Comment injection]   [Config error]   [Weak password
     in forum                               policy]
```

### 3.6 Threat Modeling na Prática

#### Passo 1: Desenhe Data Flow Diagrams (DFD)

```javascript
// DFD para uma aplicação de mensagens
const dfd = {
  externalEntities: [
    { id: 'user', name: 'User (Browser)', trust: 'untrusted' },
    { id: 'email', name: 'Email Provider', trust: 'external' }
  ],
  processes: [
    { id: 'auth', name: 'Authentication', trust: 'trusted' },
    { id: 'messaging', name: 'Messaging Service', trust: 'trusted' },
    { id: 'notifications', name: 'Notification Service', trust: 'trusted' }
  ],
  stores: [
    { id: 'users_db', name: 'Users DB', trust: 'internal' },
    { id: 'messages_db', name: 'Messages DB', trust: 'internal' },
    { id: 'session_store', name: 'Session Store (Redis)', trust: 'internal' }
  ],
  dataFlows: [
    { from: 'user', to: 'auth', data: 'credentials', protocol: 'HTTPS' },
    { from: 'auth', to: 'session_store', data: 'session_token', protocol: 'TCP' },
    { from: 'auth', to: 'users_db', data: 'user_lookup', protocol: 'TCP' },
    { from: 'user', to: 'messaging', data: 'message_content', protocol: 'HTTPS' },
    { from: 'messaging', to: 'messages_db', data: 'persist_message', protocol: 'TCP' },
    { from: 'messaging', to: 'notifications', data: 'new_message_event', protocol: 'TCP' },
    { from: 'notifications', to: 'email', data: 'email_notification', protocol: 'SMTP/TLS' }
  ],
  trustBoundaries: [
    { id: 'tb1', name: 'Internet → VPC', crosses: ['user → auth', 'user → messaging'] },
    { id: 'tb2', name: 'VPC → Database', crosses: ['auth → users_db', 'messaging → messages_db'] }
  ]
};
```

#### Passo 2: Identifique Ameaças por Data Flow

Para cada fluxo de dados que cruza uma trust boundary, pergunte:

1. O dado pode ser interceptado? (Information Disclosure)
2. O dado pode ser modificado? (Tampering)
3. O ator pode ser falsificado? (Spoofing)
4. O serviço pode ser indisponibilizado? (DoS)
5. O ator pode escalar privilégios? (Elevation)
6. As ações podem ser negadas? (Repudiation)

#### Passo 3: Priorize com Risk Rating

```python
# Cálculo de risco simplificado (CVSS-like)
import math

def calculate_risk(likelihood: int, impact: int) -> dict:
    """
    Calculate risk score based on likelihood and impact.
    
    Args:
        likelihood: 1-5 scale (1=rare, 5=almost certain)
        impact: 1-5 scale (1=negligible, 5=catastrophic)
    
    Returns:
        Dictionary with risk score and level
    """
    risk_score = likelihood * impact
    
    if risk_score >= 20:
        risk_level = "CRITICAL"
    elif risk_score >= 12:
        risk_level = "HIGH"
    elif risk_score >= 6:
        risk_level = "MEDIUM"
    elif risk_score >= 2:
        risk_level = "LOW"
    else:
        risk_level = "INFO"
    
    return {
        "score": risk_score,
        "level": risk_level,
        "likelihood": likelihood,
        "impact": impact,
        "formula": f"{likelihood} x {impact} = {risk_score}"
    }

# Exemplo de uso
risks = [
    calculate_risk(4, 5),  # SQLi em dados de pagamento
    calculate_risk(3, 4),  # XSS que rouba sessões
    calculate_risk(2, 2),  # Info leak em error messages
    calculate_risk(5, 3),  # DDoS em endpoint público
]

for risk in risks:
    print(f"Score: {risk['score']} | Level: {risk['level']} | "
          f"Formula: {risk['formula']}")
```

Saída:
```
Score: 20 | Level: CRITICAL | Formula: 4 x 5 = 20
Score: 12 | Level: HIGH     | Formula: 3 x 4 = 12
Score: 4  | Level: LOW      | Formula: 2 x 2 = 4
Score: 15 | Level: HIGH     | Formula: 5 x 3 = 15
```

#### Passo 4: Documente e Acompanhe

```yaml
# threat-model.yaml
metadata:
  project: "e-commerce-api"
  version: "1.0"
  date: "2024-01-15"
  author: "Security Team"

threats:
  - id: "T-001"
    title: "SQL Injection via product search"
    component: "Product API"
    data_flow: "user → messaging"
    stride: "Tampering"
    cvss: 9.8
    risk: "CRITICAL"
    status: "mitigated"
    mitigations:
      - "Parameterized queries via ORM"
      - "Input validation whitelist"
      - "WAF SQL injection rules"
    verification:
      - "Automated SAST scan (Semgrep)"
      - "Manual pentest (quarterly)"
      - "Bug bounty program"

  - id: "T-002"
    title: "Stored XSS in product reviews"
    component: "Review Service"
    data_flow: "user → messaging"
    stride: "Tampering"
    cvss: 8.1
    risk: "HIGH"
    status: "in_progress"
    mitigations:
      - "DOMPurify for HTML sanitization"
      - "CSP header with strict-dynamic"
      - "Output encoding on server side"
    verification:
      - "Manual testing"
      - "Automated XSS scanner"
```

---

## 4. Arquitetura de uma Aplicação Web: Client, Server, Database, CDN, Cache

### 4.1 Visão Geral da Arquitetura

Uma aplicação web moderna típica envolve múltiplas camadas, cada uma com seu próprio conjunto de riscos de segurança:

```
┌──────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
│                                                              │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐                 │
│  │ Browser │    │ Mobile  │    │ API      │                 │
│  │ (SPA)   │    │ Client  │    │ Client   │                 │
│  └────┬────┘    └────┬────┘    └────┬─────┘                 │
│       │              │              │                        │
└───────┼──────────────┼──────────────┼────────────────────────┘
        │              │              │
   ┌────▼──────────────▼──────────────▼────┐
   │           CDN (CloudFront)            │  ← Cache poisoning
   │      Static assets, Edge Rules        │    DDoS protection
   └────────────────┬──────────────────────┘
                    │
   ┌────────────────▼──────────────────────┐
   │     WAF (Web Application Firewall)    │  ← Injection filtering
   │         Rate Limiting, Bot Detection  │    Bot detection
   └────────────────┬──────────────────────┘
                    │
   ┌────────────────▼──────────────────────┐
   │    Load Balancer (ALB / Nginx)        │  ← TLS termination
   │         SSL/TLS, Routing              │    Request validation
   └────────────────┬──────────────────────┘
                    │
   ┌────────────────▼──────────────────────┐
   │         API Gateway / Reverse Proxy   │  ← Authentication
   │    Rate Limiting, Request Validation  │    Authorization
   └────────────────┬──────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
   ┌────▼───┐  ┌───▼────┐  ┌──▼───────┐
   │ Auth   │  │ Core   │  │ Notif.   │
   │Service │  │Service │  │ Service  │
   │        │  │        │  │          │
   └───┬────┘  └───┬────┘  └──┬───────┘
       │           │           │
   ┌───▼────┐  ┌───▼────┐  ┌──▼───────┐
   │Postgres│  │Postgres│  │  Redis   │
   │  (user)│  │ (data) │  │ (queue)  │
   └────────┘  └────────┘  └──────────┘
```

### 4.2 Camada 1: Client (Browser/App)

O cliente é a primeira linha de defesa e a primeira superfície de ataque.

**Responsabilidades de segurança do cliente:**
- Sanitização de output (encoding)
- Enforce CSP (Content Security Policy)
- Gerenciamento seguro de tokens (não em localStorage para tokens sensíveis)
- Detecção de mixed content

**Riscos do cliente:**
- XSS (Cross-Site Scripting)
- CSRF (Cross-Site Request Forgery)
- Client-side storage inseguro
- Dependências de terceiros comprometidas

```typescript
// Exemplo: gerenciamento seguro de tokens no cliente
class SecureTokenManager {
    private accessToken: string | null = null;
    private refreshTimer: ReturnType<typeof setTimeout> | null = null;

    constructor(private authService: AuthService) {}

    async login(username: string, password: string): Promise<void> {
        const response = await this.authService.login({ username, password });

        // Armazenar access token em memória (não em localStorage)
        this.accessToken = response.accessToken;

        // Refresh automático antes de expirar
        this.scheduleRefresh(response.expiresIn);
    }

    private scheduleRefresh(expiresIn: number): void {
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }

        // Renovar 60 segundos antes de expirar
        const refreshIn = Math.max((expiresIn - 60) * 1000, 0);
        this.refreshTimer = setTimeout(async () => {
            try {
                const response = await this.authService.refresh();
                this.accessToken = response.accessToken;
                this.scheduleRefresh(response.expiresIn);
            } catch {
                this.logout();
            }
        }, refreshIn);
    }

    getToken(): string | null {
        return this.accessToken;
    }

    logout(): void {
        this.accessToken = null;
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }
    }
}
```

**NUNCA faça isso:**
```typescript
// VULNERAVEL: armazenar token em localStorage
localStorage.setItem('auth_token', token); // ✗ XSS pode ler

// VULNERAVEL: usar innerHTML sem sanitização
element.innerHTML = userInput; // ✗ Stored XSS

// VULNERAVEL: eval() com input do usuário
eval(userInput); // ✗ Remote Code Execution
```

### 4.3 Camada 2: CDN (Content Delivery Network)

CDNs como CloudFront, Cloudflare e Akamai adicionam camadas de segurança:

**Proteções:**
- DDoS mitigation na borda
- WAF (Web Application Firewall)
- TLS termination
- Rate limiting
- Bot detection

**Riscos:**
- Cache poisoning via headers
- Cache deception attacks
- Origin IP exposure
- Misconfigured cache rules

```nginx
# Configuração segura de CDN no Nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    # TLS Configuration
    ssl_certificate /etc/ssl/certs/app.example.com.pem;
    ssl_certificate_key /etc/ssl/private/app.example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "0" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Não cachear conteúdo sensível
    location /api/ {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
        add_header Pragma "no-cache";
        proxy_pass http://backend;
    }

    # Cachear assets estáticos com versão
    location /static/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        alias /var/www/static/;
    }
}
```

### 4.4 Camada 3: Server (API/Application)

O servidor é o coração da segurança — todas as decisões de autorização e validação devem ocorrer aqui.

**Princípios:**
- Nunca confie no client para validação
- Valide tudo no server-side
- Use frameworks de segurança (Helmet.js, Django middleware)
- Implemente logging e monitoring

```go
// Go: Middleware de segurança para API
package middleware

import (
    "net/http"
    "time"
    "sync"
)

type SecurityMiddleware struct {
    rateLimiter *RateLimiter
}

type RateLimiter struct {
    mu       sync.RWMutex
    visitors map[string]*Visitor
    rate     int
    burst    int
}

type Visitor struct {
    count    int
    lastSeen time.Time
}

func NewSecurityMiddleware(rate int, burst int) *SecurityMiddleware {
    return &SecurityMiddleware{
        rateLimiter: &RateLimiter{
            visitors: make(map[string]*Visitor),
            rate:     rate,
            burst:    burst,
        },
    }
}

func (sm *SecurityMiddleware) Apply(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Rate limiting
        ip := extractIP(r)
        if !sm.rateLimiter.Allow(ip) {
            http.Error(w, "Too Many Requests", http.StatusTooManyRequests)
            return
        }

        // Security headers
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("X-XSS-Protection", "0")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        w.Header().Set("Content-Security-Policy", "default-src 'self'")

        // CORS validation
        origin := r.Header.Get("Origin")
        if !isAllowedOrigin(origin) {
            http.Error(w, "Forbidden", http.StatusForbidden)
            return
        }

        next.ServeHTTP(w, r)
    })
}

func (rl *RateLimiter) Allow(ip string) bool {
    rl.mu.Lock()
    defer rl.mu.Unlock()

    visitor, exists := rl.visitors[ip]
    if !exists {
        rl.visitors[ip] = &Visitor{count: 1, lastSeen: time.Now()}
        return true
    }

    if time.Since(visitor.lastSeen) > time.Second {
        visitor.count = 1
        visitor.lastSeen = time.Now()
        return true
    }

    visitor.count++
    visitor.lastSeen = time.Now()
    return visitor.count <= rl.burst
}

func extractIP(r *http.Request) string {
    if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
        return xff
    }
    return r.RemoteAddr
}

func isAllowedOrigin(origin string) bool {
    allowed := []string{
        "https://app.example.com",
        "https://admin.example.com",
    }
    for _, a := range allowed {
        if origin == a {
            return true
        }
    }
    return false
}
```

### 4.5 Camada 4: Database

O banco de dados é o último recurso — se o atacante chegar até aqui, todas as defesas anteriores falharam.

**Princípios:**
- Princípio do menor privilégio
- Criptografia em repouso
- Prepared statements / parameterized queries
- Audit logging
- Backup encriptado

```python
# Python: Configuração segura de banco de dados
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet

class SecureDatabaseConfig:
    """Configuração de banco de dados seguindo princípios de segurança."""

    def __init__(self):
        self.db_url = os.environ["DATABASE_URL"]
        self.encryption_key = os.environ["DB_ENCRYPTION_KEY"]
        self.fernet = Fernet(self.encryption_key.encode())

    def create_engine(self):
        engine = create_engine(
            self.db_url,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            # Forçar SSL
            connect_args={
                "sslmode": "verify-full",
                "sslrootcert": "/etc/ssl/certs/ca-certificates.crt",
            }
        )

        # Log queries em modo debug (remover em produção)
        @event.listens_for(engine, "before_cursor_execute")
        def log_query(conn, cursor, statement, parameters, context, executemany):
            if os.environ.get("SQL_LOGGING") == "true":
                print(f"SQL: {statement} | Params: {parameters}")

        return engine

    def encrypt_sensitive(self, data: str) -> bytes:
        """Encriptar dados sensíveis antes de armazenar."""
        return self.fernet.encrypt(data.encode())

    def decrypt_sensitive(self, encrypted_data: bytes) -> str:
        """Decriptar dados sensíveis após leitura."""
        return self.fernet.decrypt(encrypted_data).decode()


def create_secure_session():
    """Criar sessão com verificações de segurança."""
    config = SecureDatabaseConfig()
    engine = config.create_engine()

    Session = sessionmaker(bind=engine)
    session = Session()

    # Verificar conexão SSL
    result = session.execute(text("SHOW ssl_status"))
    ssl_info = result.fetchone()
    print(f"SSL Status: {ssl_info}")

    return session


@contextmanager
def secure_transaction(session):
    """Context manager para transações com rollback seguro."""
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Transaction rolled back: {e}")
        raise
    finally:
        session.close()
```

```python
# Nunca faça isso — SQL injection clássica
def get_user_vulnerable(user_id: str):
    """VULNERAVEL: String interpolation em query SQL."""
    query = f"SELECT * FROM users WHERE id = '{user_id}'"
    return db.execute(query)  # ✗ SQL Injection!

# Sempre faça isso — parameterized query
def get_user_secure(user_id: str):
    """SEGURO: Parameterized query."""
    query = text("SELECT * FROM users WHERE id = :user_id")
    return db.execute(query, {"user_id": user_id})  # ✓ Safe
```

### 4.6 Mapa de Superfícies de Ataque

| Camada | Componente | Superfície de Ataque | Severidade |
|--------|------------|---------------------|------------|
| Client | Browser | XSS, CSRF, clickjacking | ALTA |
| Client | localStorage | Token theft | MEDIA |
| Client | Service Worker | Cache poisoning | BAIXA |
| CDN | Cache | Cache poisoning, cache deception | ALTA |
| CDN | Edge rules | Request smuggling | MEDIA |
| WAF | Rule set | Rule bypass, false negatives | ALTA |
| Load Balancer | TLS config | Downgrade attacks | ALTA |
| API Gateway | Auth middleware | Bypass, misconfiguration | CRITICA |
| Server | Business logic | IDOR, business logic flaws | ALTA |
| Server | File upload | Webshell, malware upload | CRITICA |
| Database | SQL interface | SQL injection | CRITICA |
| Database | Stored procedures | Privilege escalation | ALTA |

---

## 5. HTTP/HTTPS: Headers de Segurança, Status Codes, Methods

### 5.1 Headers de Segurança HTTP

Os headers de segurança são a primeira linha de defesa no protocolo HTTP. Um header mal configurado pode expor a aplicação a ataques que, de outra forma, seriam bloqueados pelo browser.

#### Tabela Comparativa de Headers de Segurança

| Header | Valor Recomendado | Protege Contra | Compatibilidade |
|--------|-------------------|----------------|-----------------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Protocol downgrade, cookie hijacking | Todos browsers modernos |
| `Content-Security-Policy` | `default-src 'self'` (personalizar) | XSS, data injection | Todos browsers modernos |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing attacks | Todos browsers modernos |
| `X-Frame-Options` | `DENY` ou `SAMEORIGIN` | Clickjacking | Todos browsers (legado) |
| `X-XSS-Protection` | `0` | **DEPRECATED** — pode causar XSS | Legado |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | URL leak em referrer | Todos browsers modernos |
| `Permissions-Policy` | `camera=(), microphone=()` | Feature abuse | Chrome/Edge (parcial Firefox) |
| `Cross-Origin-Opener-Policy` | `same-origin` | Spectre-type attacks | Todos browsers modernos |
| `Cross-Origin-Resource-Policy` | `same-origin` | Cross-origin reads | Chrome, Firefox |
| `Cross-Origin-Embedder-Policy` | `require-corp` | Cross-origin isolation | Chrome, Firefox |

#### Configuração em Diferentes Stacks

**Node.js (Express + Helmet):**

```typescript
import express from 'express';
import helmet from 'helmet';

const app = express();

// Helmet configura automaticamente:
// - Content-Security-Policy
// - X-Content-Type-Options
// - X-Frame-Options
// - Strict-Transport-Security (em produção)
// - etc.
app.use(helmet());

// Configuração customizada para cada header
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", "'strict-dynamic'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", "data:", "https:"],
            fontSrc: ["'self'", "https://fonts.googleapis.com"],
            connectSrc: ["'self'", "https://api.example.com"],
            frameSrc: ["'none'"],
            objectSrc: ["'none'"],
            baseUri: ["'self'"],
            formAction: ["'self'"],
            frameAncestors: ["'none'"],
            upgradeInsecureRequests: [],
        }
    },
    hsts: {
        maxAge: 63072000, // 2 anos
        includeSubDomains: true,
        preload: true,
    },
    referrerPolicy: {
        policy: "strict-origin-when-cross-origin",
    },
    crossOriginEmbedderPolicy: true,
    crossOriginOpenerPolicy: true,
    crossOriginResourcePolicy: { policy: "same-origin" },
}));

app.listen(3000);
```

**Python (Django):**

```python
# settings.py — Django Security Settings

SECURE_HSTS_SECONDS = 63072000  # 2 years
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = False  # Deprecated, desativar
SECURE_FRAME_DENY = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSP Middleware (django-csp)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'strict-dynamic'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_CONNECT_SRC = ("'self'", "https://api.example.com")
CSP_FRAME_SRC = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_UPGRADE_INSECURE_REQUESTS = True

# Permissions Policy
PERMISSIONS_POLICY = {
    'camera': [],
    'microphone': [],
    'geolocation': [],
    'payment': ['self'],
}
```

**Go (net/http com middleware customizado):**

```go
package middleware

import "net/http"

func SecurityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // HSTS — force HTTPS for 2 years
        w.Header().Set("Strict-Transport-Security",
            "max-age=63072000; includeSubDomains; preload")

        // Prevent MIME sniffing
        w.Header().Set("X-Content-Type-Options", "nosniff")

        // Prevent framing (clickjacking)
        w.Header().Set("X-Frame-Options", "DENY")

        // Disable legacy XSS filter (can introduce vulnerabilities)
        w.Header().Set("X-XSS-Protection", "0")

        // Referrer policy
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

        // Content Security Policy
        w.Header().Set("Content-Security-Policy",
            "default-src 'self'; "+
            "script-src 'self' 'strict-dynamic'; "+
            "style-src 'self' 'unsafe-inline'; "+
            "img-src 'self' data: https:; "+
            "font-src 'self' https://fonts.gstatic.com; "+
            "connect-src 'self' https://api.example.com; "+
            "frame-src 'none'; "+
            "object-src 'none'; "+
            "base-uri 'self'; "+
            "form-action 'self'; "+
            "frame-ancestors 'none'; "+
            "upgrade-insecure-requests")

        // Permissions Policy
        w.Header().Set("Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(self)")

        // Cross-Origin Policies
        w.Header().Set("Cross-Origin-Opener-Policy", "same-origin")
        w.Header().Set("Cross-Origin-Resource-Policy", "same-origin")
        w.Header().Set("Cross-Origin-Embedder-Policy", "require-corp")

        next.ServeHTTP(w, r)
    })
}
```

### 5.2 HTTP Methods e Segurança

| Method | Seguro? | Uso | Riscos |
|--------|---------|-----|--------|
| GET | Read-only | Leitura de recursos | Não deve ter efeitos colaterais |
| POST | Criação | Criação de recursos | CSRF, mass assignment |
| PUT | Substituição total | Update completo | CSRF, data tampering |
| PATCH | Atualização parcial | Update parcial | CSRF, path traversal |
| DELETE | Remoção | Deleção de recursos | CSRF, IDOR |
| OPTIONS | Pré-requisição | CORS preflight | Information disclosure |
| HEAD | Metadados | Verificar existência | Information disclosure |
| TRACE | Debug | Echo request | **DEPRECATED** — XST attacks |

```python
# Python (Flask): Validação de HTTP methods
from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)

def require_methods(*methods):
    """Decorator para restringir HTTP methods."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method not in methods:
                return jsonify({
                    "error": "Method Not Allowed",
                    "allowed": list(methods)
                }), 405
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route("/api/users/<int:user_id>", methods=["GET", "PUT", "DELETE"])
@require_methods("GET", "PUT", "DELETE")
def user_resource(user_id):
    if request.method == "GET":
        return jsonify(get_user(user_id))
    elif request.method == "PUT":
        data = request.get_json()
        return jsonify(update_user(user_id, data))
    elif request.method == "DELETE":
        delete_user(user_id)
        return "", 204
```

### 5.3 HTTP Status Codes e Segurança

Status codes podem vajar informações sobre a aplicação se não forem controlados:

```typescript
// TypeScript: Uso correto de status codes
import express, { Request, Response } from 'express';

const router = express.Router();

// CORRETO: 401 para não autenticado
router.get('/api/profile', (req: Request, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: 'Authentication required' });
    }
    // ...
});

// CORRETO: 403 para autenticado mas sem permissão
router.delete('/api/users/:id', (req: Request, res: Response) => {
    if (!req.user) {
        return res.status(401).json({ error: 'Authentication required' });
    }
    if (req.user.role !== 'admin') {
        return res.status(403).json({ error: 'Insufficient permissions' });
    }
    // ...
});

// CORRETO: 404 genérico (não vajar existência)
router.get('/api/users/:id', (req: Request, res: Response) => {
    const user = findUser(req.params.id);
    if (!user) {
        // NÃO retornar "User not found for ID X"
        // Isso permite enumeration de IDs
        return res.status(404).json({ error: 'Resource not found' });
    }
    // ...
});

// INCORRETO: Mensagem de erro detalhada
router.post('/api/login', async (req: Request, res: Response) => {
    const user = await findUserByEmail(req.body.email);

    if (!user) {
        // VULNERAVEL: revela que o email não existe
        return res.status(401).json({ error: 'Email not found' }); // ✗
    }

    if (!await verifyPassword(user, req.body.password)) {
        // VULNERAVEL: revela que a senha está errada
        return res.status(401).json({ error: 'Invalid password' }); // ✗
    }

    // SEGURO: Mensagem genérica
    return res.status(401).json({ error: 'Invalid credentials' }); // ✓
});
```

### 5.4 HSTS (HTTP Strict Transport Security)

HSTS força o browser a usar HTTPS sempre que acessar o domínio, prevenindo downgrade attacks:

```nginx
# Nginx: HSTS Configuration
server {
    listen 443 ssl http2;

    # Forçar HTTPS por 2 anos
    add_header Strict-Transport-Security
        "max-age=63072000; includeSubDomains; preload" always;

    # Redirect HTTP para HTTPS
}

server {
    listen 80;
    server_name example.com;

    # Redirect permanente para HTTPS
    return 301 https://$host$request_uri;
}
```

**Configuração HSTS:**

| Directive | Valor | Descrição |
|-----------|-------|-----------|
| `max-age` | `63072000` (2 anos) | Tempo em segundos que o browser deve lembrar de usar HTTPS |
| `includeSubDomains` | `true` | Aplica a todos os subdomínios |
| `preload` | `true` | Permite incluir na HSTS preload list dos browsers |

**HSTS Preload List:** Após configurar HSTS com `preload`, submeta o domínio em https://hstspreload.org. Uma vez incluído, browsers hard-coded forçam HTTPS antes mesmo da primeira visita.

---

## 6. Same-Origin Policy e CORS (Cross-Origin Resource Sharing)

### 6.1 Same-Origin Policy (SOP)

A Same-Origin Policy é o pilar fundamental de segurança dos browsers. Ela restringe como um documento ou script carregado de uma **origin** pode interagir com recursos de outra **origin**.

**Origin** é definida pela combinação de:
- **Scheme** (protocolo): `http` ou `https`
- **Host**: `example.com`
- **Port**: `80`, `443`, etc.

```
Origens idênticas (SOP permite acesso total):
  https://app.example.com:443  ===  https://app.example.com:443

Origens diferentes (SOP bloqueia acesso):
  https://app.example.com      !==  http://app.example.com      (scheme diferente)
  https://app.example.com      !==  https://api.example.com     (host diferente)
  https://app.example.com:443  !==  https://app.example.com:8080 (port diferente)
  https://app.example.com      !==  https://app.example.com/api  (path NÃO conta)
```

#### O que SOP controla:

| Recurso | Mesma Origin | Cross-Origin |
|---------|-------------|--------------|
| JavaScript (AJAX/fetch) | Acesso total | Bloqueado (a menos que CORS) |
| DOM (iframe) | Acesso total | Bloqueado (cross-origin frames) |
| Cookies | Enviados automaticamente | Enviados se same-site |
| Storage (localStorage) | Acesso total | Bloqueado |
| Fonts | Acesso total | Restrito (CORS) |
| Images | Acesso total | Acesso para display, bloqueado para leitura |
| CSS | Acesso total | Acesso para display |
| WebSockets | Acesso total | Handshake cross-origin permitido |

```javascript
// Exemplo: SOP na prática
// Página em https://app.example.com

// MESMA ORIGIN — funciona
fetch('https://app.example.com/api/data')
    .then(res => res.json())
    .then(data => console.log(data)); // ✓ Sucesso

// CROSS-ORIGIN — bloqueado pelo SOP
fetch('https://api.other.com/data')
    .then(res => res.json())
    .then(data => console.log(data)); // ✗ Blocked by CORS policy

// CROSS-ORIGIN com CORS habilitado no servidor
fetch('https://api.example.com/data', {
    credentials: 'include'  // Enviar cookies
})
    .then(res => res.json())
    .then(data => console.log(data)); // ✓ Sucesso se CORS permitir
```

### 6.2 CORS (Cross-Origin Resource Sharing)

CORS é o mecanismo que permite ao browser relaxar a Same-Origin Policy de forma controlada. O servidor explicitamente declara quais origins podem acessar seus recursos.

#### Como CORS funciona:

```
┌──────────┐                              ┌──────────┐
│ Browser  │                              │  Server  │
│ (Origin) │                              │ (API)    │
└────┬─────┘                              └────┬─────┘
     │                                         │
     │  1. Request com Origin header           │
     │────────────────────────────────────────>│
     │     Origin: https://app.example.com     │
     │     Access-Control-Request-Method: POST │
     │                                         │
     │  2. Server verifica origin              │
     │                                         │
     │  3. Resposta com headers CORS           │
     │<────────────────────────────────────────│
     │     Access-Control-Allow-Origin:        │
     │       https://app.example.com           │
     │     Access-Control-Allow-Methods:       │
     │       GET, POST, PUT                    │
     │     Access-Control-Allow-Headers:       │
     │       Content-Type, Authorization       │
     │     Access-Control-Max-Age: 86400       │
     │                                         │
     │  4. Browser permite acesso              │
     │     (apenas para esta origin)           │
```

#### Headers CORS:

| Header | Direção | Descrição |
|--------|---------|-----------|
| `Access-Control-Allow-Origin` | Resposta | Origins permitidas |
| `Access-Control-Allow-Methods` | Resposta | Methods HTTP permitidos |
| `Access-Control-Allow-Headers` | Resposta | Headers permitidos no request |
| `Access-Control-Allow-Credentials` | Resposta | Se cookies/auth podem ser enviados |
| `Access-Control-Expose-Headers` | Resposta | Headers expostos ao JavaScript |
| `Access-Control-Max-Age` | Resposta | Cache do preflight em segundos |
| `Origin` | Request | Origin que fez a requisição |
| `Access-Control-Request-Method` | Request | Method que o browser quer usar |
| `Access-Control-Request-Headers` | Request | Headers que o browser quer enviar |

#### Configuração CORS em Diferentes Stacks:

```typescript
// TypeScript (Express): Configuração CORS segura
import express from 'express';
import cors from 'cors';

const app = express();

// Whitelist de origins permitidas
const ALLOWED_ORIGINS = [
    'https://app.example.com',
    'https://admin.example.com',
    'https://staging.example.com',
];

// Configuração CORS
const corsOptions: cors.CorsOptions = {
    origin: function (origin, callback) {
        // Permitir requests sem origin (server-to-server, Postman)
        if (!origin) {
            return callback(null, true);
        }

        if (ALLOWED_ORIGINS.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error(`Origin ${origin} not allowed by CORS`));
        }
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID'],
    exposedHeaders: ['X-Total-Count', 'X-Page-Count'],
    credentials: true,
    maxAge: 86400, // 24 hours preflight cache
};

app.use(cors(corsOptions));

// Rotas específicas com CORS diferente
app.get('/api/public/data', cors({
    origin: '*',  // Público — qualquer origin
}), (req, res) => {
    res.json({ data: 'public data' });
});

app.get('/api/sensitive/data', cors({
    origin: ALLOWED_ORIGINS,
    credentials: true,
}), (req, res) => {
    res.json({ data: 'sensitive data' });
});
```

```python
# Python (Flask): Configuração CORS segura
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)

# Whitelist de origins
ALLOWED_ORIGINS = [
    "https://app.example.com",
    "https://admin.example.com",
    "https://staging.example.com",
]

# Configuração CORS global
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["X-Total-Count"],
        "supports_credentials": True,
        "max_age": 86400,
    }
})

@app.route("/api/public/data")
def public_data():
    return jsonify({"data": "public data"})

@app.route("/api/sensitive/data")
def sensitive_data():
    return jsonify({"data": "sensitive data"})
```

```go
// Go: Middleware CORS customizado
package middleware

import (
    "net/http"
    "strings"
)

var allowedOrigins = map[string]bool{
    "https://app.example.com":     true,
    "https://admin.example.com":   true,
    "https://staging.example.com": true,
}

func CORS(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        origin := r.Header.Get("Origin")

        // Pre-flight request (OPTIONS)
        if r.Method == "OPTIONS" {
            if allowedOrigins[origin] {
                w.Header().Set("Access-Control-Allow-Origin", origin)
                w.Header().Set("Access-Control-Allow-Methods",
                    "GET, POST, PUT, DELETE, PATCH, OPTIONS")
                w.Header().Set("Access-Control-Allow-Headers",
                    "Content-Type, Authorization, X-Request-ID")
                w.Header().Set("Access-Control-Allow-Credentials", "true")
                w.Header().Set("Access-Control-Max-Age", "86400")
                w.WriteHeader(http.StatusNoContent)
                return
            }
            w.WriteHeader(http.StatusForbidden)
            return
        }

        // Normal request
        if allowedOrigins[origin] {
            w.Header().Set("Access-Control-Allow-Origin", origin)
            w.Header().Set("Access-Control-Allow-Credentials", "true")
            w.Header().Set("Access-Control-Expose-Headers", "X-Total-Count")
        }

        next.ServeHTTP(w, r)
    })
}
```

### 6.3 Erros Comuns de CORS

```typescript
// ERRO 1: CORS wildcard com credenciais
// NUNCA faça isso — browsers bloqueiam automaticamente
app.use(cors({
    origin: '*',                    // ✗ Qualquer origin
    credentials: true,              // ✗ Combinado com wildcard = BLOQUEADO
}));

// ERRO 2: Refletir Origin sem validação
app.use((req, res, next) => {
    // VULNERAVEL: reflete qualquer origin
    res.setHeader('Access-Control-Allow-Origin', req.headers.origin); // ✗
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    next();
});

// ERRO 3: Não validar subdomínios
const ALLOWED = ['example.com'];
// "evil-example.com" contém "example.com" — precisa de validação estrita

// ERRO 4: CORS no frontend (impossível)
// CORS é CONTROLADO PELO SERVIDOR, não pelo client
// Não existe bypass de CORS no browser
```

### 6.4 Preflight Requests

Requests que atendem a qualquer uma dessas condições disparam um preflight (OPTIONS request):

- Method diferente de GET, POST ou HEAD
- Content-Type diferente de `application/x-www-form-urlencoded`, `multipart/form-data` ou `text/plain`
- Headers customizados (ex: `Authorization`)
- Request com credenciais

```typescript
// Preflight automático pelo browser
// Quando o JavaScript faz:
fetch('https://api.example.com/data', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token123',
    },
    body: JSON.stringify({ name: 'test' }),
    credentials: 'include',
});

// O browser PRIMEIRO envia:
// OPTIONS /data HTTP/1.1
// Origin: https://app.example.com
// Access-Control-Request-Method: POST
// Access-Control-Request-Headers: Content-Type, Authorization

// E SÓ DEPOIS envia o request real se o servidor responder com CORS adequado
```

---

## 7. Content Security Policy (CSP) — Configuração Completa

### 7.1 O que é CSP?

Content Security Policy é um mecanismo de defesa em profundidade que protege contra XSS, data injection e outros ataques de execução de código não autorizado. CSP define quais fontes de conteúdo são permitidas em uma página.

```
CSP funciona como uma whitelist de fontes de conteúdo:

Sem CSP:
  <script src="https://app.com/app.js"></script>     ✓ permitido
  <script src="https://evil.com/steal.js"></script>   ✓ também permitido (XSS!)

Com CSP (default-src 'self'):
  <script src="https://app.com/app.js"></script>     ✓ permitido
  <script src="https://evil.com/steal.js"></script>   ✗ bloqueado pelo CSP
```

### 7.2 Diretivas CSP

| Diretiva | Controle | Exemplo de Ataque Prevenido |
|----------|----------|----------------------------|
| `default-src` | Fallback para todas as fontes | Baseline de segurança |
| `script-src` | Scripts JavaScript executados | XSS via `<script>` |
| `style-src` | Folhas de estilo | CSS injection, data exfiltration |
| `img-src` | Imagens | Image-based data exfiltration |
| `font-src` | Fontes | Font-based data exfiltration |
| `connect-src` | Conexões (AJAX, WebSocket, EventSource) | Data exfiltration via fetch |
| `frame-src` | Iframes | Clickjacking, frame injection |
| `object-src` | Plugins (Flash, Java) | Plugin-based attacks |
| `media-src` | Áudio e vídeo | Media-based attacks |
| `worker-src` | Web Workers e Service Workers | Worker-based attacks |
| `base-uri` | Elemento `<base>` | Base tag hijacking |
| `form-action` | Destino de formulários | Form hijacking |
| `frame-ancestors` | Quem pode embedar a página | Clickjacking |
| `upgrade-insecure-requests` | Forçar HTTPS | Protocol downgrade |

### 7.3 Valores das Diretivas

| Valor | Significação | Segurança |
|-------|-------------|-----------|
| `'none'` | Nada permitido | Mais restritivo |
| `'self'` | Mesma origin | Seguro |
| `'unsafe-inline'` | Scripts inline, event handlers | **Inseguro** — enfraquece CSP |
| `'unsafe-eval'` | eval(), new Function() | **Muito inseguro** |
| `'strict-dynamic'` | Scripts carregados por scripts confiáveis | Recomendado para SPAs |
| `'nonce-{random}'` | Script com nonce específico | Seguro com nonce único |
| `'sha256-{hash}'` | Script com hash específico | Seguro mas imutável |
| `https:` | Qualquer HTTPS | Seguro |
| `data:` | URLs data: (base64) | Potencialmente inseguro |
| `blob:` | Blob URLs | Potencialmente inseguro |

### 7.4 Exemplos de CSP por Cenário

#### Cenário 1: Site Estático (blog, landing page)

```nginx
# CSP para site estático — restrição máxima
Content-Security-Policy:
    default-src 'none';
    script-src 'self' 'sha256-abc123...';
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self' https://fonts.gstatic.com;
    connect-src 'none';
    frame-src 'none';
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    upgrade-insecure-requests
```

#### Cenário 2: SPA com API

```typescript
// CSP para SPA (React/Vue/Angular) — nonce-based
const generateNonce = (): string => {
    const buffer = new Uint8Array(16);
    crypto.getRandomValues(buffer);
    return btoa(String.fromCharCode(...buffer));
};

// Middleware que gera nonce único por request
function cspMiddleware(req, res, next) {
    const nonce = generateNonce();
    res.locals.cspNonce = nonce;

    const csp = [
        "default-src 'self'",
        `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
        `style-src 'self' 'nonce-${nonce}'`,
        "img-src 'self' data: https: blob:",
        "font-src 'self' https://fonts.gstatic.com",
        "connect-src 'self' https://api.example.com wss://ws.example.com",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ].join('; ');

    res.setHeader('Content-Security-Policy', csp);
    next();
}

// Uso no template: <script nonce="<%= cspNonce %>" src="/app.js"></script>
```

#### Cenário 3: Aplicação com Inline Scripts (legado)

```python
# CSP para aplicação legada — report-only primeiro
CSP_REPORT_ONLY = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",  # Necessário para legado
    "style-src": "'self' 'unsafe-inline'",
    "img-src": "'self' data: https:",
    "report-uri": "/csp-report",
}

# Gradualmente migrar para:
CSP_STRICT = {
    "default-src": "'self'",
    "script-src": "'self' 'strict-dynamic' 'nonce-{random}'",
    "style-src": "'self' 'nonce-{random}'",
    "img-src": "'self' data: https:",
    "report-uri": "/csp-report",
}
```

#### Cenário 4: API Pública

```go
// CSP mínimo para API (não serve HTML)
func APICSP(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // APIs que só servem JSON não precisam de CSP complexo
        // Mas se servirem erro pages HTML, CSP é necessário
        w.Header().Set("Content-Security-Policy",
            "default-src 'none'; "+
            "frame-ancestors 'none'")
        next.ServeHTTP(w, r)
    })
}
```

### 7.5 CSP Report-Only e Violation Reports

Antes de bloquear com CSP, use `Content-Security-Policy-Report-Only` para testar:

```
# Fase 1: Report-only (não bloqueia, apenas reporta)
Content-Security-Policy-Report-Only:
    default-src 'self';
    script-src 'self' 'strict-dynamic' 'nonce-{random}';
    report-uri /csp-violations;
    report-to csp-endpoint

# Fase 2: Após revisar violações, ativar CSP real
Content-Security-Policy:
    default-src 'self';
    script-src 'self' 'strict-dynamic' 'nonce-{random}';
```

```typescript
// Endpoint para receber relatórios de violação CSP
app.post('/csp-violations', express.json({ type: 'application/csp-report' }), (req, res) => {
    const report = req.body['csp-report'];

    // Log da violação
    logger.warn('CSP Violation', {
        documentUri: report['document-uri'],
        violatedDirective: report['violated-directive'],
        effectiveDirective: report['effective-directive'],
        blockedUri: report['blocked-uri'],
        sourceFile: report['source-file'],
        lineNumber: report['line-number'],
        originalPolicy: report['original-policy'],
        userAgent: req.headers['user-agent'],
        ip: req.ip,
    });

    // Alertar se violações críticas
    if (report['violated-directive']?.startsWith('script-src')) {
        alertSecurity('CSP script-src violation', report);
    }

    res.status(204).end();
});
```

### 7.6 Erros Comuns de CSP

| Erro | Por que é perigoso | Alternativa |
|------|--------------------|-------------|
| `'unsafe-inline'` em script-src | Permite qualquer script inline — XSS funciona | Usar nonces ou hashes |
| `'unsafe-eval'` em script-src | Permite eval() — RCE direto | Evitar eval; usar JSON.parse |
| `*` como fonte | Equivale a não ter CSP | Whitelist específica |
| `data:` em script-src | Permite scripts via data: URLs | Nunca usar em script-src |
| CSP muito permissivo | Ofusca o problema sem resolver | Testar com report-only primeiro |
| Não usar `frame-ancestors` | Clickjacking via iframes externos | Definir frame-ancestors |

---

## 8. Cookies: Secure, HttpOnly, SameSite, Path

### 8.1 Atributos de Cookie e Segurança

Cookies são o mecanismo mais antigo e mais perigoso de estado na web. Cada atributo de cookie impacta diretamente a segurança da aplicação.

#### Tabela Completa de Atributos de Cookie

| Atributo | Valor | Descrição | Segurança |
|----------|-------|-----------|-----------|
| `Secure` | (flag) | Cookie enviado apenas via HTTPS | Previne interceptação em HTTP |
| `HttpOnly` | (flag) | Cookie inacessível via JavaScript | Previne XSS para roubo de cookie |
| `SameSite` | `Strict` | Cookie não enviado em requests cross-site | Previne CSRF |
| `SameSite` | `Lax` | Cookie enviado apenas em top-level navigation | Equilíbrio entre segurança e usabilidade |
| `SameSite` | `None` | Cookie enviado em qualquer context | Requer `Secure` — vulnerável se não HTTPS |
| `Path` | `/api` | Cookie restrito a path específico | Limita superfície de exposição |
| `Domain` | `.example.com` | Cookie disponível em subdomínios | Evitar em domínios compartilhados |
| `Max-Age` | `3600` | Tempo de vida em segundos | Cookies curtos = menor janela de ataque |
| `Expires` | data GMT | Data de expiração | Preferir Max-Age sobre Expires |
| `Priority` | `High` | Prioridade de envio | Controle de envio |

### 8.2 Configuração Segura de Cookies

```typescript
// TypeScript (Express): Configuração segura de cookies
import express from 'express';
import cookieParser from 'cookie-parser';

const app = express();
app.use(cookieParser());

// Configuração base para cookies de sessão
const SESSION_COOKIE_OPTIONS: cookie.CookieOptions = {
    httpOnly: true,     // Inacessível via JavaScript
    secure: true,       // Apenas via HTTPS
    sameSite: 'lax',    // Proteção CSRF básica
    path: '/',          // Disponível em todas as rotas
    maxAge: 3600000,    // 1 hora
    signed: true,       // Assinado para detectar tampering
};

// Configuração para cookies de autenticação
const AUTH_COOKIE_OPTIONS: cookie.CookieOptions = {
    httpOnly: true,
    secure: true,
    sameSite: 'strict', // Proteção CSRF máxima
    path: '/api/auth',  // Restrito ao path de autenticação
    maxAge: 900000,     // 15 minutos (curto para segurança)
    signed: true,
};

// Configuração para CSRF token
const CSRF_COOKIE_OPTIONS: cookie.CookieOptions = {
    httpOnly: false,    // Precisa ser lido pelo JavaScript
    secure: true,
    sameSite: 'strict',
    path: '/',
    maxAge: 3600000,
};

// Middleware para definir cookies seguros
function setSecureCookies(req, res, next) {
    const sessionId = generateSecureSessionId();

    res.cookie('session_id', sessionId, SESSION_COOKIE_OPTIONS);

    // Nunca definir cookies sensíveis sem esses atributos:
    // ✗ res.cookie('token', token);  // Falta HttpOnly, Secure
    // ✓ res.cookie('token', token, AUTH_COOKIE_OPTIONS);

    next();
}
```

```python
# Python (Flask): Configuração segura de cookies
from flask import Flask, make_response, request

app = Flask(__name__)

# Configuração global de cookies da sessão
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = '__Host-session_id'  # Prefixo seguro
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

@app.route('/login', methods=['POST'])
def login():
    user = authenticate(request.json['email'], request.json['password'])

    if not user:
        return {'error': 'Invalid credentials'}, 401

    session_token = create_session(user.id)

    response = make_response({'status': 'ok'})
    response.set_cookie(
        'session_id',
        session_token,
        httponly=True,
        secure=True,
        samesite='Lax',
        path='/',
        max_age=3600,
        # Prefixo __Host- força HTTPS e path /
    )

    return response


@app.route('/logout', methods=['POST'])
def logout():
    response = make_response({'status': 'ok'})

    # Deletar cookie corretamente
    response.delete_cookie(
        'session_id',
        path='/',
        secure=True,
        httponly=True,
        samesite='Lax',
    )

    return response
```

```go
// Go: Configuração segura de cookies
package handlers

import (
    "crypto/rand"
    "encoding/hex"
    "net/http"
    "time"
)

func SetSecureCookie(w http.ResponseWriter, name, value string, maxAge int) {
    cookie := &http.Cookie{
        Name:     name,
        Value:    value,
        Path:     "/",
        MaxAge:   maxAge,
        HttpOnly: true,
        Secure:   true,
        SameSite: http.SameSiteLaxMode,
    }
    http.SetCookie(w, cookie)
}

func SetSessionCookie(w http.ResponseWriter, userID string) error {
    // Gerar token de sessão criptograficamente seguro
    token, err := generateSecureToken(32)
    if err != nil {
        return err
    }

    // Armazenar sessão no servidor (Redis/DB)
    if err := storeSession(token, userID, 30*time.Minute); err != nil {
        return err
    }

    // Definir cookie com prefixo __Host-
    cookie := &http.Cookie{
        Name:     "__Host-session_id",
        Value:    token,
        Path:     "/",
        MaxAge:   1800, // 30 minutos
        HttpOnly: true,
        Secure:   true,
        SameSite: http.SameSiteLaxMode,
    }

    http.SetCookie(w, cookie)
    return nil
}

func generateSecureToken(n int) (string, error) {
    bytes := make([]byte, n)
    if _, err := rand.Read(bytes); err != nil {
        return "", err
    }
    return hex.EncodeToString(bytes), nil
}
```

### 8.3 Cookie Prefixes

Browsers reconhecem prefixos especiais em nomes de cookie que forçam comportamentos seguros:

| Prefixo | Comportamento Forçado |
|---------|----------------------|
| `__Host-` | `Secure`, `Path=/`, sem `Domain` |
| `__Secure-` | `Secure` obrigatório |

```
# Correto — prefixo __Host- força HTTPS e path /
Set-Cookie: __Host-session_id=abc123; HttpOnly; SameSite=Lax

# Inseguro — sem prefixo, pode ser definido via HTTP
Set-Cookie: session_id=abc123

# Inválido — __Host- exige Secure e Path=/
Set-Cookie: __Host-session_id=abc123; Path=/api  # ✗ Inválido!
```

### 8.4 Cookie Security Matrix

| Cookie Type | HttpOnly | Secure | SameSite | Path | Max-Age | Exemplo |
|-------------|----------|--------|----------|------|---------|---------|
| Session ID | OBRIGATORIO | OBRIGATORIO | Lax/Strict | / | 30min-1h | `__Host-sid` |
| Auth Token | OBRIGATORIO | OBRIGATORIO | Strict | /api/auth | 15min | `__Secure-auth` |
| CSRF Token | Opcional | OBRIGATORIO | Strict | / | 1h | `csrf_token` |
| Refresh Token | OBRIGATORIO | OBRIGATORIO | Strict | /api/auth/refresh | 7-30d | `__Secure-refresh` |
| Preference | false | true | Lax | / | 1y | `theme` |
| Analytics | false | true | None | / | 2y | `_ga` |

### 8.5 Ataques Relacionados a Cookies

```typescript
// ATAQUE 1: Cookie fixation
// O atacante define um session ID conhecido na vítima

// VULNERAVEL: não regenerar session ID após login
app.post('/login', async (req, res) => {
    const user = await authenticate(req.body.email, req.body.password);
    if (user) {
        // ✗ Mesmo session ID do antes do login
        res.cookie('session_id', req.session.id, COOKIE_OPTIONS);
        res.json({ success: true });
    }
});

// SEGURO: regenerar session ID após login
app.post('/login', async (req, res) => {
    const user = await authenticate(req.body.email, req.body.password);
    if (user) {
        // ✓ Novo session ID — o antigo é invalidado
        req.session.regenerate((err) => {
            req.session.userId = user.id;
            res.cookie('session_id', req.session.id, COOKIE_OPTIONS);
            res.json({ success: true });
        });
    }
});

// ATAQUE 2: Cookie tossing via subdomain
// Um atacante controla sub.example.com e define um cookie
// que afeta app.example.com

// VULNERAVEL: cookie sem Domain específico
res.cookie('session_id', evilValue, {
    domain: '.example.com', // Afeta TODOS subdomínios
});

// SEGURO: cookie restrito ao domínio exato
res.cookie('session_id', sessionValue, {
    // Sem Domain — restrito ao domínio exato
    secure: true,
    httpOnly: true,
});
```

---

## 9. Sessions vs Tokens: JWT, OAuth 2.0, OpenID Connect

### 9.1 Sessions Baseadas em Cookie

O modelo tradicional de sessão usa cookies para identificar o usuário e armazena o estado no servidor.

```
Fluxo de sessão baseada em cookie:

[Browser]                          [Server]
    │                                │
    │  1. POST /login                │
    │     email + password           │
    │───────────────────────────────>│
    │                                │  2. Validar credenciais
    │                                │  3. Criar sessão no servidor
    │                                │     (Redis: session_id → user_data)
    │  4. Set-Cookie:                │
    │     session_id=abc123          │
    │<───────────────────────────────│
    │                                │
    │  5. GET /api/profile           │
    │     Cookie: session_id=abc123  │
    │───────────────────────────────>│
    │                                │  6. Buscar sessão no Redis
    │                                │  7. Retornar dados do usuário
    │  8. Response: { user data }    │
    │<───────────────────────────────│
```

**Vantagens:**
- Estado no servidor — controle total sobre expiração e invalidação
- Cookie é automaticamente gerenciado pelo browser
- Menor superfície de ataque no client
- Revogação imediata (deletar do Redis)

**Desvantagens:**
- Stateful — dificulta horizontal scaling
- CSRF risk (mitigado com SameSite)
- Cookie não funciona bem entre domínios diferentes
- Não funciona bem com APIs mobile

```python
# Python (Flask): Sessão segura com Redis
from flask import Flask, session, request, jsonify
import redis
import secrets
from datetime import timedelta

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Configuração de sessão segura
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.Redis(
    host='localhost',
    port=6379,
    ssl=True,
    ssl_certfile='/etc/ssl/redis.pem',
    ssl_keyfile='/etc/ssl/redis.key',
)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

@app.route('/login', methods=['POST'])
def login():
    email = request.json.get('email')
    password = request.json.get('password')

    user = authenticate_user(email, password)
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Regenerar sessão para prevenir fixation
    session.clear()
    session['user_id'] = user.id
    session['role'] = user.role
    session['login_time'] = datetime.utcnow().isoformat()

    return jsonify({'status': 'ok', 'user': user.to_dict()})


@app.route('/api/profile')
def get_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    user = get_user_by_id(user_id)
    return jsonify(user.to_dict())


@app.route('/logout', methods=['POST'])
def logout():
    # Invalidar sessão no servidor
    session.clear()
    return jsonify({'status': 'ok'})
```

### 9.2 JWT (JSON Web Tokens)

JWT é um padrão de token stateless que contém os dados do usuário diretamente no token.

```
Estrutura de um JWT:

eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9        ← Header
.
eyJ1c2VyX2lkIjoiMTIzNDUifQ                     ← Payload
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c   ← Signature
```

```
Header (algoritmo e tipo):
{
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-id-2024"
}

Payload (dados do usuário — NÃO encriptado):
{
    "sub": "user123",
    "email": "user@example.com",
    "role": "admin",
    "iat": 1700000000,
    "exp": 1700003600,
    "iss": "https://auth.example.com",
    "aud": "https://api.example.com"
}

Signature (integridade — garante que o token não foi alterado):
RS256(base64(header) + "." + base64(payload), privateKey)
```

```typescript
// TypeScript: Implementação segura de JWT
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';

// Chaves RSA para RS256 (nunca HS256 em produção)
const PRIVATE_KEY = fs.readFileSync('/etc/keys/private.pem');
const PUBLIC_KEY = fs.readFileSync('/etc/keys/public.pem');

interface TokenPayload {
    sub: string;
    email: string;
    role: string;
    iat: number;
    exp: number;
    iss: string;
    aud: string;
    jti: string;  // JWT ID — para revogação
}

class JWTService {
    private readonly ISSUER = 'https://auth.example.com';
    private readonly AUDIENCE = 'https://api.example.com';
    private readonly ACCESS_TOKEN_TTL = 900;       // 15 minutos
    private readonly REFRESH_TOKEN_TTL = 604800;    // 7 dias

    generateTokenPair(user: { id: string; email: string; role: string }) {
        const accessToken = this.generateAccessToken(user);
        const refreshToken = this.generateRefreshToken(user);

        return { accessToken, refreshToken };
    }

    private generateAccessToken(user: { id: string; email: string; role: string }): string {
        const payload: Partial<TokenPayload> = {
            sub: user.id,
            email: user.email,
            role: user.role,
            iss: this.ISSUER,
            aud: this.AUDIENCE,
            jti: uuidv4(),
        };

        return jwt.sign(payload, PRIVATE_KEY, {
            algorithm: 'RS256',
            expiresIn: this.ACCESS_TOKEN_TTL,
        });
    }

    private generateRefreshToken(user: { id: string }): string {
        return jwt.sign(
            { sub: user.id, type: 'refresh', jti: uuidv4() },
            PRIVATE_KEY,
            {
                algorithm: 'RS256',
                expiresIn: this.REFRESH_TOKEN_TTL,
            }
        );
    }

    verifyAccessToken(token: string): TokenPayload {
        return jwt.verify(token, PUBLIC_KEY, {
            algorithms: ['RS256'],
            issuer: this.ISSUER,
            audience: this.AUDIENCE,
        }) as TokenPayload;
    }

    verifyRefreshToken(token: string): { sub: string; jti: string } {
        return jwt.verify(token, PUBLIC_KEY, {
            algorithms: ['RS256'],
            issuer: this.ISSUER,
        }) as { sub: string; jti: string };
    }
}
```

```python
# Python: Implementação segura de JWT
import jwt
import time
import uuid
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class JWTService:
    def __init__(self, private_key_path: str, public_key_path: str):
        with open(private_key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None
            )
        with open(public_key_path, 'rb') as f:
            self.public_key = serialization.load_pem_public_key(f.read())

        self.issuer = "https://auth.example.com"
        self.audience = "https://api.example.com"
        self.access_ttl = 900    # 15 minutos
        self.refresh_ttl = 604800  # 7 dias

    def generate_tokens(self, user: dict) -> dict:
        now = datetime.utcnow()

        access_payload = {
            "sub": user["id"],
            "email": user["email"],
            "role": user["role"],
            "iat": now,
            "exp": now + timedelta(seconds=self.access_ttl),
            "iss": self.issuer,
            "aud": self.audience,
            "jti": str(uuid.uuid4()),
        }

        refresh_payload = {
            "sub": user["id"],
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_ttl),
            "iss": self.issuer,
            "jti": str(uuid.uuid4()),
        }

        access_token = jwt.encode(
            access_payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "key-2024"}
        )

        refresh_token = jwt.encode(
            refresh_payload,
            self.private_key,
            algorithm="RS256",
            headers={"kid": "key-2024"}
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": self.access_ttl,
            "token_type": "Bearer",
        }

    def verify_token(self, token: str, token_type: str = "access") -> dict:
        return jwt.decode(
            token,
            self.public_key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience if token_type == "access" else None,
        )
```

```go
// Go: Implementação segura de JWT
package auth

import (
    "crypto/rsa"
    "crypto/x509"
    "encoding/pem"
    "os"
    "time"

    "github.com/golang-jwt/jwt/v5"
    "github.com/google/uuid"
)

type JWTService struct {
    privateKey  *rsa.PrivateKey
    publicKey   *rsa.PublicKey
    issuer      string
    audience    string
    accessTTL   time.Duration
    refreshTTL  time.Duration
}

type Claims struct {
    jwt.RegisteredClaims
    Email string `json:"email"`
    Role  string `json:"role"`
}

func NewJWTService(privateKeyPath, publicKeyPath string) (*JWTService, error) {
    privateKey, err := loadPrivateKey(privateKeyPath)
    if err != nil {
        return nil, err
    }

    publicKey, err := loadPublicKey(publicKeyPath)
    if err != nil {
        return nil, err
    }

    return &JWTService{
        privateKey: privateKey,
        publicKey:  publicKey,
        issuer:     "https://auth.example.com",
        audience:   "https://api.example.com",
        accessTTL:  15 * time.Minute,
        refreshTTL: 7 * 24 * time.Hour,
    }, nil
}

func (s *JWTService) GenerateAccessToken(userID, email, role string) (string, error) {
    claims := &Claims{
        RegisteredClaims: jwt.RegisteredClaims{
            Subject:   userID,
            Issuer:    s.issuer,
            Audience:  jwt.ClaimStrings{s.audience},
            IssuedAt:  jwt.NewNumericDate(time.Now()),
            ExpiresAt: jwt.NewNumericDate(time.Now().Add(s.accessTTL)),
            ID:        uuid.New().String(),
        },
        Email: email,
        Role:  role,
    }

    token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
    return token.SignedString(s.privateKey)
}

func (s *JWTService) VerifyAccessToken(tokenString string) (*Claims, error) {
    token, err := jwt.ParseWithClaims(tokenString, &Claims{},
        func(token *jwt.Token) (interface{}, error) {
            if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
                return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
            }
            return s.publicKey, nil
        },
        jwt.WithIssuer(s.issuer),
        jwt.WithAudience(s.audience),
    )
    if err != nil {
        return nil, err
    }

    claims, ok := token.Claims.(*Claims)
    if !ok || !token.Valid {
        return nil, fmt.Errorf("invalid token")
    }

    return claims, nil
}

func loadPrivateKey(path string) (*rsa.PrivateKey, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }
    block, _ := pem.Decode(data)
    return x509.ParsePKCS1PrivateKey(block.Bytes)
}

func loadPublicKey(path string) (*rsa.PublicKey, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, err
    }
    block, _ := pem.Decode(data)
    return x509.ParsePKCS1PublicKey(block.Bytes)
}
```

### 9.3 Erros Comundos com JWT

| Erro | Consequência | Mitigation |
|------|-------------|------------|
| Usar HS256 com secret fraco | Token forjado | Usar RS256/ES256 com chaves RSA/ECDSA |
| Não validar `iss` e `aud` | Token de outro serviço aceito | Validar todos os campos |
| Armazenar dados sensíveis no payload | Dados expostos (payload é decodificável) | Dados não sensíveis apenas |
| Não implementar revogação | Token roubado continua válido | Blocklist de tokens revogados |
| TTL muito longo | Janela de ataque maior | Access token: 15min, Refresh: 7d |
| Não usar `kid` (key ID) | Rotação de chaves difícil | Sempre incluir kid no header |

### 9.4 OAuth 2.0

OAuth 2.0 é um framework de autorização que permite ao usuário autorizar uma aplicação terceira a acessar seus dados sem compartilhar credenciais.

#### Grant Types e Segurança

| Grant Type | Uso | Segurança |
|------------|-----|-----------|
| Authorization Code + PKCE | SPAs, mobile apps | Recomendado — usa code verifier |
| Authorization Code | Server-side apps | Seguro com PKCE |
| Client Credentials | Machine-to-machine | Seguro para backend |
| Implicit | **DEPRECATED** | Inseguro — access token na URL |
| Password | **DEPRECATED** | Inseguro — credenciais no client |
| Device Code | Smart TV, CLI | Seguro para input limitado |

```
Fluxo Authorization Code + PKCE:

[Client SPA]              [Auth Server]              [Resource Server]
    │                          │                          │
    │ 1. Gerar code_verifier  │                          │
    │    e code_challenge      │                          │
    │                          │                          │
    │ 2. GET /authorize        │                          │
    │    ?response_type=code   │                          │
    │    &client_id=app123     │                          │
    │    &redirect_uri=https://                          │
    │      app.example.com/   │                          │
    │      callback           │                          │
    │    &scope=openid profile│                          │
    │    &state=xyz           │                          │
    │    &code_challenge=abc  │                          │
    │    &code_challenge_     │                          │
    │      method=S256        │                          │
    │─────────────────────────>│                          │
    │                          │                          │
    │ 3. User autentica       │                          │
    │    e autoriza            │                          │
    │                          │                          │
    │ 4. Redirect com code    │                          │
    │<─────────────────────────│                          │
    │                          │                          │
    │ 5. POST /token           │                          │
    │    grant_type=           │                          │
    │      authorization_code  │                          │
    │    &code=xyz123          │                          │
    │    &code_verifier=def   │                          │
    │─────────────────────────>│                          │
    │                          │                          │
    │ 6. Valida code_verifier  │                          │
    │    contra code_challenge │                          │
    │                          │                          │
    │ 7. Access token +        │                          │
    │    Refresh token         │                          │
    │<─────────────────────────│                          │
    │                          │                          │
    │ 8. GET /api/data         │                          │
    │    Authorization: Bearer │                          │
    │      access_token        │                          │
    │─────────────────────────────────────────────────────>│
    │                          │                          │
    │ 9. Resource              │                          │
    │<─────────────────────────────────────────────────────│
```

```typescript
// TypeScript: OAuth 2.0 Authorization Code + PKCE
import crypto from 'crypto';

class OAuthClient {
    private codeVerifier: string = '';
    private codeChallenge: string = '';

    async initiateLogin(): Promise<string> {
        // Gerar code_verifier (43-128 caracteres)
        this.codeVerifier = crypto.randomBytes(32)
            .toString('base64url')
            .substring(0, 128);

        // Gerar code_challenge (SHA-256 do code_verifier)
        this.codeChallenge = crypto.createHash('sha256')
            .update(this.codeVerifier)
            .digest('base64url');

        // Gerar state para prevenir CSRF
        const state = crypto.randomBytes(32).toString('hex');

        // Armazenar state e code_verifier temporariamente
        await this.storePKCEParams(state, this.codeVerifier);

        // Construir URL de autorização
        const params = new URLSearchParams({
            response_type: 'code',
            client_id: 'app123',
            redirect_uri: 'https://app.example.com/callback',
            scope: 'openid profile email',
            state: state,
            code_challenge: this.codeChallenge,
            code_challenge_method: 'S256',
        });

        return `https://auth.example.com/authorize?${params.toString()}`;
    }

    async handleCallback(code: string, state: string): Promise<TokenPair> {
        // Validar state
        const storedParams = await this.getPKCEParams(state);
        if (!storedParams) {
            throw new Error('Invalid state parameter');
        }

        // Trocar code por tokens
        const response = await fetch('https://auth.example.com/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                grant_type: 'authorization_code',
                code: code,
                redirect_uri: 'https://app.example.com/callback',
                client_id: 'app123',
                code_verifier: storedParams.codeVerifier,
            }),
        });

        if (!response.ok) {
            throw new Error('Token exchange failed');
        }

        return response.json();
    }
}
```

### 9.5 OpenID Connect (OIDC)

OIDC é uma camada de identidade sobre OAuth 2.0 que adiciona autenticação ao framework de autorização:

| Conceito | OAuth 2.0 | OIDC |
|----------|-----------|------|
| Foco | Autorização | Autenticação + Autorização |
| Token principal | Access Token | ID Token (JWT) |
| UserInfo endpoint | Não | Sim |
| Scopes padrão | custom | `openid`, `profile`, `email` |
| Discovery | Não | `.well-known/openid-configuration` |

```typescript
// OIDC: Validação de ID Token
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

class OIDCValidator {
    private client: jwksClient.JWKSClient;

    constructor(issuer: string) {
        this.client = jwksClient({
            jwksUri: `${issuer}/.well-known/jwks.json`,
            cache: true,
            rateLimit: true,
        });
    }

    async validateIDToken(idToken: string, expectedNonce: string): Promise<any> {
        // Decodificar header para obter kid
        const header = jwt.decode(idToken, { complete: true })?.header;
        if (!header) throw new Error('Invalid ID token');

        // Buscar chave pública por kid
        const key = await this.client.getSigningKey(header.kid);
        const publicKey = key.getPublicKey();

        // Validar token
        const payload = jwt.verify(idToken, publicKey, {
            algorithms: ['RS256', 'ES256'],
            issuer: 'https://accounts.google.com',
            audience: 'app123-client-id',
        }) as any;

        // Validar nonce
        if (payload.nonce !== expectedNonce) {
            throw new Error('Nonce mismatch');
        }

        // Validar tempo
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp < now) throw new Error('Token expired');
        if (payload.iat > now + 300) throw new Error('Token issued in future');

        return payload;
    }
}
```

### 9.6 Comparativo: Sessions vs JWT vs OAuth

| Aspecto | Sessions (Cookie) | JWT | OAuth 2.0 |
|---------|-------------------|-----|-----------|
| Estado | Server-side | Stateless | Stateless |
| Scaling | Difícil (sticky sessions ou shared store) | Fácil | Fácil |
| Revogação | Imediata (delete session) | Difícil (precisa blocklist) | Depende do provider |
| Cross-domain | Limitado (cookies) | Funciona | Projetado para isso |
| Mobile support | Limitado | Excelente | Excelente |
| Complexidade | Baixa | Média | Alta |
| Segurança padrão | CSRF risk (mitigável) | Nenhum (precisa configurar) | Vários flows |
| Token size | 32-64 bytes (session ID) | 500-1000+ bytes | Variável |
| Uso recomendado | Apps monolíticas | APIs modernas | SSO, integrações |


---

## 10. Modelos de Autenticação: Cookie-based, Bearer Token, API Key

### 10.1 Cookie-based Authentication

Autenticação baseada em cookies é o modelo mais antigo e ainda o mais usado em aplicações web tradicionais.

```
Fluxo de Cookie-based Authentication:

[Browser]                          [Server]
    │                                │
    │  1. POST /login                │
    │     {email, password}          │
    │───────────────────────────────>│
    │                                │  2. Verificar credenciais
    │                                │  3. Criar sessão
    │  4. Set-Cookie:                │
    │     session_id=abc123;         │
    │     HttpOnly; Secure;          │
    │     SameSite=Lax; Path=/      │
    │<───────────────────────────────│
    │                                │
    │  5. GET /api/profile           │
    │     Cookie: session_id=abc123  │
    │     (browser envia automatico) │
    │───────────────────────────────>│
    │                                │  6. Validar sessão
    │  7. {user data}                │
    │<───────────────────────────────│
```

```typescript
// TypeScript (Express): Cookie-based Authentication completa
import express from 'express';
import session from 'express-session';
import RedisStore from 'connect-redis';
import { createClient } from 'redis';

const app = express();

// Redis client para sessões
const redisClient = createClient({
    url: process.env.REDIS_URL,
    socket: { tls: true }
});
redisClient.connect();

// Configuração de sessão
app.use(session({
    store: new RedisStore({ client: redisClient }),
    name: '__Host-session_id',
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: process.env.NODE_ENV === 'production',
        httpOnly: true,
        maxAge: 30 * 60 * 1000, // 30 minutos
        sameSite: 'lax',
        path: '/',
    },
}));

// Login
app.post('/api/login', async (req, res) => {
    const { email, password } = req.body;

    const user = await authenticateUser(email, password);
    if (!user) {
        return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Regenerar sessão (previne fixation)
    req.session.regenerate((err) => {
        if (err) {
            return res.status(500).json({ error: 'Session error' });
        }

        req.session.userId = user.id;
        req.session.role = user.role;

        res.json({
            user: { id: user.id, email: user.email, name: user.name }
        });
    });
});

// Middleware de autenticação
function requireAuth(req, res, next) {
    if (!req.session.userId) {
        return res.status(401).json({ error: 'Authentication required' });
    }
    next();
}

// Rotas protegidas
app.get('/api/profile', requireAuth, async (req, res) => {
    const user = await getUserById(req.session.userId);
    res.json(user);
});

// Logout
app.post('/api/logout', (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            return res.status(500).json({ error: 'Logout error' });
        }
        res.clearCookie('__Host-session_id', {
            path: '/',
            secure: true,
            httpOnly: true,
            sameSite: 'lax',
        });
        res.json({ status: 'ok' });
    });
});
```

### 10.2 Bearer Token Authentication

Bearer tokens são usados em APIs modernas, particularmente com OAuth 2.0 e JWT.

```
Fluxo de Bearer Token:

[Client]                          [Auth Server]
    │                                │
    │  1. POST /oauth/token          │
    │     {grant_type, credentials}  │
    │───────────────────────────────>│
    │                                │  2. Validar credenciais
    │  3. {access_token,             │
    │      token_type: "Bearer",     │
    │      expires_in: 900}          │
    │<───────────────────────────────│
    │                                │
    │  4. GET /api/data              │
    │     Authorization:             │
    │       Bearer eyJhbG...         │
    │───────────────────────────────>│
    │                                │  5. Verificar token
    │  6. {data}                     │
    │<───────────────────────────────│
```

```python
# Python (FastAPI): Bearer Token Authentication
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

app = FastAPI()
security = HTTPBearer()

# Configuração JWT
ALGORITHM = "RS256"
PUBLIC_KEY = open("public.pem").read()
ISSUER = "https://auth.example.com"

class TokenData(BaseModel):
    sub: str
    email: str
    role: str

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Verificar e decodificar Bearer token."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
        )
        return TokenData(
            sub=payload["sub"],
            email=payload["email"],
            role=payload["role"],
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Rota pública
@app.get("/api/public")
async def public_endpoint():
    return {"message": "This is public"}

# Rota protegida
@app.get("/api/profile")
async def get_profile(current_user: TokenData = Depends(verify_token)):
    user = await get_user_by_id(current_user.sub)
    return user

# Rota admin
@app.get("/api/admin/users")
async def admin_users(current_user: TokenData = Depends(verify_token)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    users = await get_all_users()
    return users
```

```go
// Go: Bearer Token Authentication Middleware
package middleware

import (
    "context"
    "net/http"
    "strings"

    "github.com/golang-jwt/jwt/v5"
)

type contextKey string

const UserContextKey contextKey = "user"

type Claims struct {
    jwt.RegisteredClaims
    Email string `json:"email"`
    Role  string `json:"role"`
}

func BearerAuth(publicKey interface{}) func(http.Handler) http.Handler {
    return func(next http.Handler) http.Handler {
        return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
            authHeader := r.Header.Get("Authorization")
            if authHeader == "" {
                http.Error(w, "Authorization header required", http.StatusUnauthorized)
                return
            }

            parts := strings.SplitN(authHeader, " ", 2)
            if len(parts) != 2 || parts[0] != "Bearer" {
                http.Error(w, "Invalid authorization format", http.StatusUnauthorized)
                return
            }

            tokenString := parts[1]

            claims := &Claims{}
            token, err := jwt.ParseWithClaims(tokenString, claims,
                func(token *jwt.Token) (interface{}, error) {
                    if _, ok := token.Method.(*jwt.SigningMethodRSA); !ok {
                        return nil, fmt.Errorf("unexpected signing method")
                    }
                    return publicKey, nil
                },
                jwt.WithIssuer("https://auth.example.com"),
                jwt.WithAudience("https://api.example.com"),
            )

            if err != nil || !token.Valid {
                http.Error(w, "Invalid token", http.StatusUnauthorized)
                return
            }

            ctx := context.WithValue(r.Context(), UserContextKey, claims)
            next.ServeHTTP(w, r.WithContext(ctx))
        })
    }
}
```

### 10.3 API Key Authentication

API keys são usadas para autenticação machine-to-machine e em APIs públicas.

```
Fluxo de API Key:

[Client]                          [API Gateway]
    │                                │
    │  1. GET /api/data              │
    │     X-API-Key: ak_live_123...  │
    │───────────────────────────────>│
    │                                │  2. Verificar API key
    │                                │  3. Rate limit por key
    │  4. {data}                     │
    │<───────────────────────────────│
```

```python
# Python (FastAPI): API Key Authentication
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import hashlib
import secrets

app = FastAPI()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Banco de API keys (em produção: hash armazenado)
API_KEYS_DB = {
    hashlib.sha256(key.encode()).hexdigest(): {
        "name": "Partner App",
        "rate_limit": 1000,  # requests per hour
        "scopes": ["read", "write"],
    }
}

async def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> dict:
    """Verificar API key."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_info = API_KEYS_DB.get(key_hash)

    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return key_info

@app.get("/api/data")
async def get_data(key_info: dict = Depends(verify_api_key)):
    if "read" not in key_info["scopes"]:
        raise HTTPException(status_code=403, detail="Insufficient scopes")

    return {"data": "value"}
```

### 10.4 Comparativo de Modelos de Autenticação

| Aspecto | Cookie-based | Bearer Token | API Key |
|---------|-------------|--------------|---------|
| Uso principal | Web apps (browser) | APIs modernas | Machine-to-machine |
| Armazenamento | Cookie HttpOnly | Memory/localStorage | Header ou query |
| Proteção CSRF | Sim (SameSite) | Não vulnerável | Não vulnerável |
| Proteção XSS | HttpOnly impede | Nenhuma (token no JS) | Nenhuma |
| Revogação | Imediata (server-side) | Difícil (stateless) | Simples (delete key) |
| Escopo | Sessão completa | Por request | Por request |
| Granularidade | Usuário | Usuário + scopes | Aplicação + scopes |
| Exemplo de uso | Login em site | API REST moderna | API pública |

### 10.5 Multi-factor Authentication (MFA)

MFA adiciona uma camada extra de segurança além de senha + token:

```typescript
// TypeScript: Implementação de TOTP (Time-based One-Time Password)
import { authenticator } from 'otplib';
import QRCode from 'qrcode';

class MFAService {
    async setupTOTP(userId: string): Promise<{ secret: string; qrCode: string }> {
        const secret = authenticator.generateSecret();

        // Gerar URI para QR Code
        const otpauth = authenticator.keyuri(
            userId,
            'MyApp',
            secret
        );

        // Gerar QR Code como data URL
        const qrCode = await QRCode.toDataURL(otpauth);

        // Armazenar secret (encriptado)
        await storeMFASecret(userId, secret);

        return { secret, qrCode };
    }

    async verifyTOTP(userId: string, token: string): Promise<boolean> {
        const secret = await getMFASecret(userId);
        return authenticator.verify({ token, secret });
    }
}

// Middleware de MFA check
function requireMFA(req, res, next) {
    if (!req.session.mfaVerified) {
        return res.status(403).json({
            error: 'MFA required',
            redirect: '/mfa/verify'
        });
    }
    next();
}
```

---

## 11. TLS/SSL: Certificados, Handshake, Cipher Suites, HSTS

### 11.1 O Handshake TLS

O TLS handshake é o processo pelo qual cliente e servidor estabelecem uma conexão segura:

```
TLS 1.3 Handshake (simplificado):

[Client]                                    [Server]
    │                                          │
    │  1. ClientHello                          │
    │     - TLS 1.3                            │
    │     - Cipher suites suportados           │
    │     - Key share (ECDHE)                  │
    │─────────────────────────────────────────>│
    │                                          │
    │  2. ServerHello                          │
    │     - TLS 1.3 (aceito)                   │
    │     - Cipher suite selecionado           │
    │     - Key share (ECDHE)                  │
    │     - Certificate                        │
    │     - CertificateVerify                  │
    │     - Finished                           │
    │<─────────────────────────────────────────│
    │                                          │
    │  3. Finished                             │
    │     (verificação de integridade)         │
    │─────────────────────────────────────────>│
    │                                          │
    │  4. Comunicação encriptada               │
    │<─────────────────────────────────────────>│
```

### 11.2 Cipher Suites

Cipher suites definem os algoritmos usados para cada etapa da comunicação TLS:

| Componente | Algoritmo | Função |
|-----------|-----------|--------|
| Key Exchange | ECDHE | Troca de chaves segura (Forward Secrecy) |
| Authentication | RSA/ECDSA | Autenticação do servidor |
| Encryption | AES-128-GCM/AES-256-GCM | Encriptação dos dados |
| Hash | SHA-256/SHA-384 | Integridade dos dados |

```nginx
# Nginx: Configuração de cipher suites segura
server {
    listen 443 ssl http2;

    # TLS 1.2 e 1.3 apenas
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites seguras (TLS 1.2)
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    # TLS 1.3 cipher suites (configurados automaticamente)
    # TLS_AES_256_GCM_SHA384
    # TLS_CHACHA20_POLY1305_SHA256
    # TLS_AES_128_GCM_SHA256

    ssl_prefer_server_ciphers off;

    # Session tickets para performance
    ssl_session_tickets on;
    ssl_session_ticket_key /etc/ssl/ticket.key;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
}
```

### 11.3 Certificados TLS

```bash
# Gerar certificado autoassinado para desenvolvimento
openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout server.key \
    -out server.crt \
    -subj "/CN=localhost"

# Gerar CSR (Certificate Signing Request) para produção
openssl req -new -newkey rsa:4096 \
    -nodes -keyout server.key \
    -out server.csr \
    -subj "/C=BR/ST=Sao Paulo/L=Sao Paulo/O=MyCompany/CN=app.example.com"

# Verificar certificado
openssl x509 -in server.crt -text -noout

# Verificar cadeia de certificados
openssl verify -CAfile ca-bundle.crt server.crt

# Testar configuração TLS
openssl s_client -connect app.example.com:443 -tls1_2
openssl s_client -connect app.example.com:443 -tls1_3
```

### 11.4 HSTS e Prevenção de Downgrade

```
Cadeia de proteção HTTPS:

1. HSTS (HTTP Strict Transport Security)
   → Browser remembers: "nunca usar HTTP neste domínio"
   → Prevenção de SSL stripping

2. HSTS Preload
   → Hard-coded nos browsers
   → Proteção na primeira visita

3. Certificate Transparency
   → Logs públicos de todos os certificados emitidos
   → Detecção de certificados fraudulentos

4. OCSP Stapling
   → Server fornece status do certificado
   → Previne revocation check delays

5. CAA Records
   → DNS record que define quem pode emitir certificados
   → Ex: example.com CAA 0 issue "letsencrypt.org"
```

### 11.5 Configuração TLS em Go

```go
// Go: Configuração TLS segura
package main

import (
    "crypto/tls"
    "log"
    "net/http"
)

func main() {
    tlsConfig := &tls.Config{
        MinVersion: tls.VersionTLS12,
        MaxVersion: tls.VersionTLS13,

        // Cipher suites seguras (TLS 1.2)
        CipherSuites: []uint16{
            tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
            tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
            tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,
            tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
        },

        // Prefer server cipher order
        PreferServerCipherSuites: true,

        // Session tickets
        SessionTicketsDisabled: false,

        // Curve preferences
        CurvePreferences: []tls.CurveID{
            tls.X25519,
            tls.CurveP256,
        },
    }

    server := &http.Server{
        Addr:      ":443",
        TLSConfig: tlsConfig,
    }

    // Forçar HTTPS
    go func() {
        httpServer := &http.Server{
            Addr: ":80",
            Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
                target := "https://" + r.Host + r.URL.RequestURI()
                http.Redirect(w, r, target, http.StatusMovedPermanently)
            }),
        }
        log.Fatal(httpServer.ListenAndServe())
    }()

    log.Fatal(server.ListenAndServeTLS("server.crt", "server.key"))
}
```

---

## 12. DNS Security: DNSSEC, DoH, DoT

### 12.1 Por Que DNS Security?

DNS é frequentemente chamado de "protocolo cego da internet" — não possui autenticação nativa, tornando-o vulnerável a:

- **DNS Spoofing/Poisoning**: Atacante injeta respostas DNS falsas
- **Man-in-the-Middle**: Interceptação de queries DNS
- **DNS Hijacking**: Redirecionamento de tráfego para servidores maliciosos
- **Monitoring**: Vigilância de quais domínios o usuário acessa

### 12.2 DNSSEC (DNS Security Extensions)

DNSSEC adiciona autenticação e integridade às respostas DNS usando criptografia de chaves públicas:

```
Chain of Trust DNSSEC:

Root Zone (.)
    │
    ├── KSK (Key Signing Key) → assina ZSK
    ├── ZSK (Zone Signing Key) → assina registros DNS
    │
    v
.com Zone
    │
    ├── KSK → assina ZSK
    ├── ZSK → assina registros
    │
    v
example.com Zone
    │
    ├── KSK → assina ZSK
    ├── ZSK → assina registros:
    │   ├── A: 93.184.216.34 (assinado com RRSIG)
    │   ├── AAAA: 2606:2800:220:1:248:1893:25c8:1946 (assinado com RRSIG)
    │   └── MX: mail.example.com (assinado com RRSIG)
```

```bash
# Verificar DNSSEC para um domínio
dig example.com +dnssec
drill -TD example.com

# Configurar DNSSEC no BIND
# named.conf
zone "example.com" {
    type master;
    file "example.com.zone";
    key-directory "/etc/bind/keys";
    dnssec-policy "default";
    inline-signing yes;
};
```

### 12.3 DNS over HTTPS (DoH)

DoH encripta queries DNS usando HTTPS, prevenindo espionagem e manipulação:

```typescript
// TypeScript: Cliente DoH
class DNSOverHTTPS {
    private dohEndpoint = 'https://cloudflare-dns.com/dns-query';

    async resolve(domain: string, type: string = 'A'): Promise<any> {
        const response = await fetch(this.dohEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/dns-message',
                'Accept': 'application/dns-message',
            },
            body: this.encodeDNSQuery(domain, type),
        });

        if (!response.ok) {
            throw new Error(`DoH request failed: ${response.status}`);
        }

        return this.decodeDNSResponse(await response.arrayBuffer());
    }

    private encodeDNSQuery(domain: string, type: string): ArrayBuffer {
        // Implementação simplificada — usar lib em produção
        const encoder = new TextEncoder();
        const query = {
            status: 0,
            type: 'query',
            id: Math.floor(Math.random() * 65535),
            flags: 0x0100, // Standard query
            questions: [{
                name: domain,
                type: type === 'A' ? 1 : type === 'AAAA' ? 28 : 1,
                class: 1, // IN
            }],
        };
        // Serialização DNS wire format
        return this.serializeDNSQuery(query);
    }
}

// Uso
const dns = new DNSOverHTTPS();
const result = await dns.resolve('example.com', 'A');
console.log(result.answers);
```

### 12.4 DNS over TLS (DoT)

DoT usa TLS na porta 853 para encriptar queries DNS:

```python
# Python: Cliente DoT
import ssl
import socket
import struct

class DNSOverTLS:
    def __init__(self, server: str = '1.1.1.1', port: int = 853):
        self.server = server
        self.port = port

    def resolve(self, domain: str) -> bytes:
        context = ssl.create_default_context()

        with socket.create_connection((self.server, self.port)) as sock:
            with context.wrap_socket(sock, server_hostname=self.server) as ssock:
                # Construir query DNS
                query = self._build_dns_query(domain)

                # Enviar com prefixo de comprimento (TLS)
                ssock.send(struct.pack('!H', len(query)) + query)

                # Receber resposta
                length_bytes = ssock.recv(2)
                response_length = struct.unpack('!H', length_bytes)[0]
                response = ssock.recv(response_length)

                return response

    def _build_dns_query(self, domain: str) -> bytes:
        # Implementação simplificada de DNS query
        header = struct.pack('!HHHHHH',
            0x1234,  # Transaction ID
            0x0100,  # Flags: Standard query
            1,       # Questions
            0,       # Answers
            0,       # Authority
            0,       # Additional
        )

        question = b''
        for part in domain.split('.'):
            question += bytes([len(part)]) + part.encode()
        question += b'\x00'
        question += struct.pack('!HH', 1, 1)  # Type A, Class IN

        return header + question
```

### 12.5 Configuração DNS Segura

```bash
# /etc/resolv.conf — usar DNS público seguro
# Cloudflare
nameserver 1.1.1.1
nameserver 1.0.0.1

# Google
nameserver 8.8.8.8
nameserver 8.8.4.4

# Quad9 (bloqueia domínios maliciosos)
nameserver 9.9.9.9
nameserver 149.112.112.112

# Configurar DoH no Firefox (about:config)
# network.trr.mode = 3 (TRR only)
# network.trr.uri = https://cloudflare-dns.com/dns-query
```

---

## 13. Browser Security: Sandbox, CORS Preflight, Mixed Content

### 13.1 Browser Sandbox

Browsers executam código em sandboxes restritivos para limitar o impacto de vulnerabilidades:

```
Arquitetura de Sandbox do Browser:

┌─────────────────────────────────────────────┐
│                  Browser                     │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │         Processo Principal              │ │
│  │         (UI, Network, Storage)          │ │
│  └──────────────┬─────────────────────────┘ │
│                 │                            │
│  ┌──────────────▼─────────────────────────┐ │
│  │      Renderer Process (per-tab)        │ │
│  │      ┌─────────────────────────────┐   │ │
│  │      │    JavaScript Engine        │   │ │
│  │      │    (V8/SpiderMonkey)        │   │ │
│  │      └─────────────────────────────┘   │ │
│  │      ┌─────────────────────────────┐   │ │
│  │      │    DOM Rendering Engine     │   │ │
│  │      └─────────────────────────────┘   │ │
│  │      ┌─────────────────────────────┐   │ │
│  │      │    WebGL/WebAudio          │   │ │
│  │      └─────────────────────────────┘   │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │      GPU Process                       │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  ┌────────────────────────────────────────┐ │
│  │      Network Process                   │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### 13.2 Mixed Content

Mixed content ocorre quando uma página HTTPS carrega recursos via HTTP:

```typescript
// Tipos de mixed content
const mixedContentTypes = {
    // Blocking (o browser bloqueia)
    blocking: [
        'script',      // JavaScript
        'iframe',      // Iframes
        'websocket',   // WebSocket connections
        'stylesheet',  // CSS (em novos browsers)
    ],

    // Warning (o browser avisa mas permite)
    warning: [
        'image',       // Imagens
        'media',       // Áudio e vídeo
        'font',        // Fontes
        'object',      // Plugins
        'fetch',       // AJAX/fetch requests
    ],
};

// CSP para prevenir mixed content
const mixedContentCSP = {
    // Forçar todos os recursos via HTTPS
    upgradeInsecureRequests: true,

    // Ou especificar esquemas permitidos
    defaultSrc: ["'self'", 'https:'],
    scriptSrc: ["'self'", 'https:'],
    styleSrc: ["'self'", 'https:'],
    imgSrc: ["'self'", 'https:', 'data:'],
    fontSrc: ["'self'", 'https:'],
};
```

### 13.3 Clickjacking Prevention

```typescript
// Proteção contra clickjacking com X-Frame-Options e CSP
// Express.js middleware

function clickjackingProtection(req, res, next) {
    // X-Frame-Options (legado)
    res.setHeader('X-Frame-Options', 'DENY');

    // CSP frame-ancestors (moderno)
    res.setHeader('Content-Security-Policy',
        "frame-ancestors 'none'");

    // Para frames específicos (ex: embed em parceiros)
    // const allowedOrigins = ['https://partner.com'];
    // const origin = req.headers.origin;
    // if (allowedOrigins.includes(origin)) {
    //     res.setHeader('X-Frame-Options', `ALLOW-FROM ${origin}`);
    //     res.setHeader('Content-Security-Policy',
    //         `frame-ancestors ${origin}`);
    // }

    next();
}

// Verificação server-side adicional
function verifyFrameAncestors(req, res, next) {
    // Alguns browsers não suportam CSP frame-ancestors
    const referer = req.headers.referer;
    if (referer) {
        const refererUrl = new URL(referer);
        if (refererUrl.hostname !== req.hostname) {
            return res.status(403).json({
                error: 'Frame embedding not allowed'
            });
        }
    }
    next();
}
```

### 13.4 Subresource Integrity (SRI)

```html
<!-- SRI garante que o conteúdo de CDN não foi modificado -->
<script
    src="https://cdn.example.com/library.js"
    integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"
    crossorigin="anonymous">
</script>

<link
    rel="stylesheet"
    href="https://cdn.example.com/styles.css"
    integrity="sha384-abc123..."
    crossorigin="anonymous">
```

```python
# Python: Gerar hashes SRI para assets
import hashlib
import base64

def generate_sri_hash(file_path: str, algorithm: str = 'sha384') -> str:
    """Gerar Subresource Integrity hash para um arquivo."""
    hash_func = hashlib.new(algorithm)

    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)

    digest = base64.b64encode(hash_func.digest()).decode('ascii')
    return f"{algorithm}-{digest}"

# Uso
sri_hash = generate_sri_hash('dist/bundle.js')
print(f'integrity="{sri_hash}"')
```

---

## 14. Common Misconceptions About Web Security

### 14.1 Mito: "HTTPS resolve todos os problemas de segurança"

**Realidade:** HTTPS protege a transmissão em trânsito, mas não resolve:

- XSS (Cross-Site Scripting)
- SQL Injection
- CSRF (Cross-Site Request Forgery)
- Vulnerabilidades de lógica de negócio
- Autenticação fraca
- Autorização incorreta

HTTPS é **necessário mas não suficiente**. É uma camada — não a solução completa.

### 14.2 Mito: "Meu site não tem dados sensíveis, não precisa de segurança"

**Realidade:** Todo site pode ser usado como:

- **Pivô**: Site comprometido serve como base para atacar outros sistemas
- **C2 Server**: Código malicioso pode usar seu domínio para comunicação
- **SEO Spam**: Injeção de conteúdo para redirecionar usuários
- **Cryptomining**: Uso de CPU do visitante para mineração
- **Phishing**: Clonagem do site para roubar credenciais

### 14.3 Mito: "Firewall e WAF protegem minha aplicação"

**Realidade:** WAFs e firewalls são camadas adicionais, não substitutos:

- Bypass de WAF é relativamente simples para atacantes experientes
- WAF não protege contra vulnerabilidades de lógica de negócio
- WAF não substitui validação de input no código
- WAF pode ter falsos negativos e falsos positivos

### 14.4 Mito: "JavaScript no browser é seguro porque roda em sandbox"

**Realidade:** O sandbox do browser tem limitações:

- XSS bypassa o sandbox (executa código no contexto do usuário)
- Side-channel attacks (Spectre, Meltdown) exploram hardware
- Extension permissions podem ser excessivas
- Storage compartilhado pode vazar dados

### 14.5 Mito: "Autenticação complexa = mais segura"

**Realidade:** Segurança vem de boas práticas, não de complexidade:

```
# Mito: "Vou inventar minha própria criptografia"
# Realidade: use padrões estabelecidos

# ERRADO — criptografia caseira
def encrypt_password(password):
    return password[::-1]  # ✗ Inversão não é criptografia

# CORRETO — usar bcrypt
import bcrypt
def hash_password(password):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt)
```

### 14.6 Mito: "Se o código é open source, é automaticamente seguro"

**Realidade:** Visibilidade não garante segurança:

- Log4Shell existiu em código open source por anos
- xz-utils backdoor passou por review sem ser detectada
- Muitas dependências transitivas são ignoradas
- Auditoria de código requer expertise específica em segurança

### 14.7 Mito: "Penetration testing anual é suficiente"

**Realidade:** O estado da aplicação muda constantemente:

- Novas dependências introduzem vulnerabilidades
- Features novas podem criar novas superfícies de ataque
- CVEs descobertas em componentes existentes
- Configurações mudam durante deployments

Segurança é um **processo contínuo**, não um checkpoint.

### 14.8 Tabela: Mito vs Realidade

| Mito | Realidade |
|------|-----------|
| "HTTPS = seguro" | HTTPS é necessário mas não suficiente |
| "Nossos dados não são valiosos" | Todo site é pivô potencial |
| "WAF nos protege" | WAF é camada adicional, não solução |
| "Sandbox do browser é perfeito" | XSS e side-channels existem |
| "Complexidade = segurança" | Simplicidade = menos superfície de ataque |
| "Open source = seguro" | Visibilidade não garante auditoria |
| "Pen test anual basta" | Segurança é processo contínuo |
| "Não fomos atacados = somos seguros" | Pode ser que não sabemos que fomos atacados |
| "DevOps acelera = menos seguro" | DevSecOps acelera E protege |
| "Segurança é custo" | Segurança é investimento |

---

## 15. Lab Setup: OWASP Juice Shop, DVWA, WebGoat

### 15.1 OWASP Juice Shop

Juice Shop é um playground moderno com centenas de vulnerabilidades realistas em uma aplicação Node.js.

```bash
# Instalar Docker (se ainda não tiver)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Executar OWASP Juice Shop
docker run -d \
    --name juice-shop \
    -p 3000:3000 \
    bkimminich/juice-shop

# Acessar: http://localhost:3000

# Modo de desenvolvimento (com fontes)
git clone https://github.com/juice-shop/juice-shop.git
cd juice-shop
npm install
npm run start

# Resolver desafios (sólucions em diferentes níveis)
# Nível: Pega-me se puder (Tutorial)
# Nível: Fácil
# Nível: Médio
# Nível: Difícil
# Nível: Insuperável
```

```typescript
// Exemplo: encontrar e explorar vulnerabilidade no Juice Shop
// SQL Injection no search

// Requisição original
// GET /rest/products/search?q=pen

// Payload de SQL injection
// GET /rest/products/search?q=pen%27%20OR%201%3D1%20--

// Em JavaScript para automação
async function exploitSQLi() {
    const payload = "' OR 1=1 --";
    const url = `http://localhost:3000/rest/products/search?q=${encodeURIComponent(payload)}`;

    const response = await fetch(url);
    const data = await response.json();

    console.log('Produtos encontrados:', data.data.length);
    return data;
}
```

### 15.2 DVWA (Damn Vulnerable Web Application)

DVWA é uma aplicação PHP com vulnerabilidades configuráveis em diferentes níveis de dificuldade.

```bash
# Executar DVWA com Docker
docker run -d \
    --name dvwa \
    -p 8080:80 \
    vulnerables/web-dvwa

# Configuração inicial
# 1. Acessar http://localhost:8080
# 2. Login: admin / password
# 3. Criar banco de dados (botão "Create / Reset Database")
# 4. Configurar nível de dificuldade em DVWA Security
```

```python
# Python: Explorar XSS refletido no DVWA
import requests
from bs4 import BeautifulSoup

class DVWAExploiter:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username: str = 'admin', password: str = 'password'):
        """Login no DVWA."""
        login_page = self.session.get(f'{self.base_url}/login.php')
        soup = BeautifulSoup(login_page.text, 'html.parser')
        token = soup.find('input', {'name': 'user_token'})['value']

        response = self.session.post(f'{self.base_url}/login.php', data={
            'username': username,
            'password': password,
            'user_token': token,
        })

        return 'Login failed' not in response.text

    def test_xss_reflected(self, payload: str):
        """Testar XSS refletido."""
        response = self.session.get(
            f'{self.base_url}/vulnerabilities/xss_r/',
            params={'name': payload}
        )
        return payload in response.text

    def test_sqli(self, payload: str):
        """Testar SQL injection."""
        response = self.session.get(
            f'{self.base_url}/vulnerabilities/sqli/',
            params={'id': payload, 'Submit': 'Submit'}
        )
        return response.text

# Uso
dvwa = DVWAExploiter('http://localhost:8080')
dvwa.login()

# XSS refletido
xss_payload = '<script>alert("XSS")</script>'
print(f"XSS funciona: {dvwa.test_xss_reflected(xss_payload)}")

# SQL injection
sqli_payload = "1' OR '1'='1"
print(f"SQLi resposta: {dvwa.test_sqli(sqli_payload)}")
```

### 15.3 WebGoat

WebGoat é uma plataforma de ensino da OWASP com lições estruturadas sobre segurança.

```bash
# Executar WebGoat com Docker
docker run -d \
    --name webgoat \
    -p 8081:8080 \
    -p 9090:9090 \
    webgoat/webgoat

# Acessar: http://localhost:8081/WebGoat
# WebWolf (para exercícios avançados): http://localhost:9090/WebWolf
```

### 15.4 Cenário de Laboratório Completo

```yaml
# docker-compose.yml — Laboratório completo de segurança
version: '3.8'

services:
  juice-shop:
    image: bkimminich/juice-shop
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
    volumes:
      - juice-shop-data:/app/data

  dvwa:
    image: vulnerables/web-dvwa
    ports:
      - "8080:80"
    environment:
      - MYSQL_ROOT_PASSWORD=dvwa

  webgoat:
    image: webgoat/webgoat
    ports:
      - "8081:8080"
      - "9090:9090"
    environment:
      - WEBGOAT_PORT=8080

  burpsuite:
    image: vulnerabilityassessmentscanner/burpsuite
    ports:
      - "8082:8080"
      - "1337:1337"
    volumes:
      - burp-data:/home/burp/data

  nginx-proxy:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx-proxy.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - juice-shop
      - dvwa
      - webgoat

volumes:
  juice-shop-data:
  burp-data:
```

```nginx
# nginx-proxy.conf — Reverse proxy para o laboratório
server {
    listen 80;
    server_name localhost;

    # OWASP Juice Shop
    location /juice-shop/ {
        proxy_pass http://juice-shop:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # DVWA
    location /dvwa/ {
        proxy_pass http://dvwa:80/;
        proxy_set_header Host $host;
    }

    # WebGoat
    location /webgoat/ {
        proxy_pass http://webgoat:8080/WebGoat/;
        proxy_set_header Host $host;
    }
}
```

### 15.5 Scripts de Automação para Laboratório

```python
# Python: Scanner automático de vulnerabilidades
import asyncio
import aiohttp
from dataclasses import dataclass

@dataclass
class VulnerabilityResult:
    name: str
    severity: str
    url: str
    payload: str
    vulnerable: bool

class VulnerabilityScanner:
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.results: list[VulnerabilityResult] = []

    async def scan_xss(self, session: aiohttp.ClientSession):
        """Scan for reflected XSS."""
        payloads = [
            '<script>alert("XSS")</script>',
            '<img src=x onerror=alert("XSS")>',
            '"><script>alert("XSS")</script>',
        ]

        for payload in payloads:
            url = f"{self.target_url}/search?q={payload}"
            async with session.get(url) as resp:
                text = await resp.text()
                self.results.append(VulnerabilityResult(
                    name="Reflected XSS",
                    severity="HIGH",
                    url=url,
                    payload=payload,
                    vulnerable=payload in text,
                ))

    async def scan_sqli(self, session: aiohttp.ClientSession):
        """Scan for SQL injection."""
        payloads = [
            "' OR '1'='1",
            "1' UNION SELECT NULL--",
            "1; DROP TABLE users--",
        ]

        for payload in payloads:
            url = f"{self.target_url}/users?id={payload}"
            async with session.get(url) as resp:
                text = await resp.text()
                # Verificar se retornou dados inesperados
                has_sqli = any(indicator in text.lower() for indicator in [
                    'sql', 'mysql', 'sqlite', 'error in your sql'
                ])
                self.results.append(VulnerabilityResult(
                    name="SQL Injection",
                    severity="CRITICAL",
                    url=url,
                    payload=payload,
                    vulnerable=has_sqli,
                ))

    async def run(self):
        """Executar todas as verificações."""
        async with aiohttp.ClientSession() as session:
            await asyncio.gather(
                self.scan_xss(session),
                self.scan_sqli(session),
            )

        return self.results

# Executar scan
scanner = VulnerabilityScanner('http://localhost:3000')
results = asyncio.run(scanner.run())

for result in results:
    status = "VULNERAVEL" if result.vulnerable else "SEGURO"
    print(f"[{result.severity}] {result.name}: {status}")
```

---

## 16. Referências

### 16.1 Padrões e Especificações

| Referência | URL | Descrição |
|-----------|-----|-----------|
| OWASP Top 10 (2021) | https://owasp.org/www-project-top-ten/ | Top 10 vulnerabilidades web |
| OWASP ASVS v4.0 | https://owasp.org/www-project-application-security-verification-standard/ | Application Security Verification Standard |
| RFC 7230-7235 (HTTP/1.1) | https://tools.ietf.org/html/rfc7230 | Especificação HTTP/1.1 |
| RFC 8446 (TLS 1.3) | https://tools.ietf.org/html/rfc8446 | Especificação TLS 1.3 |
| RFC 6749 (OAuth 2.0) | https://tools.ietf.org/html/rfc6749 | Framework OAuth 2.0 |
| RFC 7519 (JWT) | https://tools.ietf.org/html/rfc7519 | JSON Web Token |
| RFC 6797 (HSTS) | https://tools.ietf.org/html/rfc6797 | HTTP Strict Transport Security |
| RFC 6454 (SOP) | https://tools.ietf.org/html/rfc6454 | Same-Origin Policy |
| RFC 6455 (WebSocket) | https://tools.ietf.org/html/rfc6455 | WebSocket Protocol |

### 16.2 Ferramentas

| Ferramenta | Uso | URL |
|-----------|-----|-----|
| Burp Suite | Proxy de interceptação e scanner | https://portswigger.net/burp |
| OWASP ZAP | Scanner de vulnerabilidades | https://www.zaproxy.org |
| Nmap | Port scanning e service detection | https://nmap.org |
| SQLMap | SQL injection automation | https://sqlmap.org |
| Nikto | Web server scanner | https://cirt.net/Nikto2 |
| Semgrep | SAST (static analysis) | https://semgrep.dev |
| Snyk | Dependency scanning | https://snyk.io |
| SonarQube | Code quality + security | https://www.sonarqube.org |

### 16.3 Laboratórios e Prática

| Laboratório | Tecnologia | URL |
|------------|------------|-----|
| OWASP Juice Shop | Node.js | https://github.com/juice-shop/juice-shop |
| DVWA | PHP | https://github.com/digininja/DVWA |
| WebGoat | Java | https://github.com/WebGoat/WebGoat |
| HackTheBox | Múltipla | https://www.hackthebox.com |
| TryHackMe | Múltipla | https://tryhackme.com |
| PortSwigger Web Security Academy | Múltipla | https://portswigger.net/web-security |

### 16.4 Livros e Papers

| Título | Autor | Ano |
|--------|-------|-----|
| The Web Application Hacker's Handbook | Stuttard, Pinto | 2011 |
| HTTP: The Definitive Guide | Gourley, Totty | 2002 |
| Bulletproof SSL and TLS | Ivan Ristic | 2016 |
| Tangled Web | Michal Zalewski | 2011 |
| The Tangled Web (2nd ed) | Michal Zalewski | 2013 |
| Web Application Security | Andrew Hoffman | 2019 |
| Real-World Bug Hunting | Peter Yaworski | 2018 |

### 16.5 Referências de Header Configuration

| Header | Mozilla Observatory | SecurityHeaders.com | Qualys SSL Labs |
|--------|--------------------|--------------------|-----------------|
| HSTS | Teste de configuração | Score impact | N/A |
| CSP | Teste de política | Score impact | N/A |
| X-Content-Type-Options | Verificação | Score impact | N/A |
| X-Frame-Options | Verificação | Score impact | N/A |
| TLS Config | N/A | N/A | Grade A+ objetivo |

---

*[Voltar ao Prefácio](00-prefacio.md)*

*[Próximo capítulo: 02 — Protocolo HTTP Seguro](02-protocolo-http-seguro.md)*
