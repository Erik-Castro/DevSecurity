# Capitulo 02 -- Protocolo HTTP Seguro

> **Livro 6: Desenvolvimento Seguro na Web**
> **Projeto: DevSecurity**

---

## Sumario

1. Objetivos de Aprendizado
2. HTTP/1.1 vs HTTP/2 vs HTTP/3: Implicacoes de Seguranca
3. Headers de Seguranca HTTP Completos
4. TLS 1.3 para Web: Cipher Suites e Certificate Pinning
5. CORS: Preflight, Credentials e Origins
6. Cookies Seguros: Atributos e Configuracao
7. HTTP Request Smuggling
8. HTTP Desync Attacks
9. Server Configuration Hardening: nginx, Apache, Caddy
10. CDN Security
11. HSTS Preload List
12. Mixed Content Prevention
13. Cache Poisoning Attacks
14. Configuracao Completa de Seguranca nginx
15. Exercicios
16. Referencias

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

1. **Distinguir** as diferencas de seguranca entre HTTP/1.1, HTTP/2 e HTTP/3, incluindo vetores de ataque especificos de cada versao e como as mitigacoes evoluiram ao longo do tempo.

2. **Implementar** todos os headers de seguranca HTTP recomendados pelo OWASP, Mozilla e CIS Benchmarks, incluindo Content-Security-Policy com politicas completas e funcionais para aplicacoes do mundo real.

3. **Configurar** TLS 1.3 com cipher suites seguros, implementar certificate pinning e evitar downgrade attacks que exploram negociacao de protocolo.

4. **Projetar e validar** politicas CORS que previnam ataques de origem cruzada sem comprometer funcionalidades legitimas, incluindo tratamento correto de credenciais e preflight requests.

5. **Detectar e mitigar** ataques de HTTP request smuggling e HTTP desync, incluindo tecnicas de testing e configuracao de servidores front-end e back-end.

6. **Harden** configuracoes de servidores web (nginx, Apache, Caddy) seguindo benchmarks de seguranca reconhecidos pela industria.

7. **Prevenir** cache poisoning, mixed content e outros vetores de ataque que exploram o transporte e cache HTTP.

---

## 2. HTTP/1.1 vs HTTP/2 vs HTTP/3: Implicacoes de Seguranca

### 2.1 Visao Geral das Versoes

O protocolo HTTP evoluiu significativamente ao longo de tres decadas. Cada versao traz ganhos de performance, mas tambem introduz novas superficies de ataque que os desenvolvedores precisam entender.

#### HTTP/1.1 (RFC 9110, 1997/2022)

HTTP/1.1 e o protocolo base que dominou a web por mais de 20 anos. Suas caracteristicas principais de seguranca incluem:

- **Texto claro** na camada de aplicacao (nao confundir com transporte criptografado)
- **Conexoes persistentes** por padrao (keep-alive)
- **Head-of-line blocking** a nivel de aplicacao
- **Pipelining** opcional e problemático

A natureza textual do HTTP/1.1 e a raiz de muitas vulnerabilidades:

```
GET /admin/config HTTP/1.1
Host: example.com
Cookie: session=abc123def456
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
X-Forwarded-For: 192.168.1.100
```

Cada cabecalho e transmitido como texto legivel. Mesmo com TLS, a camada de aplicacao continua text-based, o que cria oportunidades para ataques de parsing.

#### HTTP/2 (RFC 9113, 2015/2022)

HTTP/2 introduz multiplexing binario, o que elimina head-of-line blocking a nivel de aplicacao mas cria novos vetores de ataque:

- **Frame splitting**: Um frame de cabecalho pode ser dividido entre multiplos frames
- **HPACK compression**: Compressao de cabecalhos pode ser explorada para inferir dados sensiveis (CRIME/BREACH-like attacks)
- **Stream priority**: Pode ser manipulado para causar negacao de servico
- **Server push**: Pode ser abusado para injetar recursos nao solicitados

O formato binario do HTTP/2 torna certos tipos de request smuggling mais dificeis, mas nao impossiveis:

```
+-----------------------------------------------+
|                 Length (24)                    |
+---------------+---------------+---------------+
|   Type (8)    |   Flags (8)   |
+-+-------------+---------------+------...-----+
|R|         Stream Identifier (31)             |
+-+-------------+---------------------------...-+
|           Frame Payload (0...)               |
+-----------------------------------------------+
```

#### HTTP/3 (RFC 9114, 2022)

HTTP/3 roda sobre QUIC (RFC 9000) em vez de TCP, eliminando TCP-level head-of-line blocking:

- **QUIC sobre UDP**: Transporte base completamente reescrito
- **Criptografia obrigatoria**: TLS 1.3 e integrado ao protocolo, nao e opcional
- **Connection migration**: Conexoes sobrevivem a mudancas de rede (WiFi para celular)
- **0-RTT**: Possibilidade de enviar dados antes da completacao do handshake (risky)

O 0-RTT do QUIC e particularmente perigoso para seguranca porque permite replay de requests:

```
// Atacante pode capturar e reenviar esta request em 0-RTT
POST /api/transfer HTTP/3
Host: bank.example.com
Content-Type: application/json

{"to":"attacker-account","amount":10000}
```

Para mitigar, servidores devem aceitar 0-RTT apenas para requests idempotentes, ou implementar anti-replay mechanisms como o anti-replay design do QUIC.

### 2.2 Tabela Comparativa de Seguranca

| Aspecto | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---------|----------|--------|--------|
| Transporte | TCP | TCP | QUIC (UDP) |
| Criptografia | Opcional (TLS) | Opcional (TLS) | Obrigatoria (TLS 1.3) |
| Head-of-Line Blocking | Sim (aplicacao) | Sim (TCP) | Nao |
| Multiplexing | Nao | Sim (binario) | Sim (binario) |
| Request Smuggling | Alta risco | Risco reduzido | Risco minimo |
| Server Push | Nao | Sim (abusive) | Sim (limitado) |
| 0-RTT Replay | N/A | N/A | Risco presente |
| Header Compression | Nao | HPACK | QPACK |

### 2.3 CVE-2023-44487: HTTP/2 Rapid Reset Attack

Esta CVE revelou uma vulnerabilidade fundamental no design do HTTP/2. O ataque explora o fato de que o protocolo permite criar e cancelar rapidamente multiplos streams, causando exhaustao de recursos no servidor.

**Vetor do ataque:**

```
// O atacante envia multiplos HEADERS frames com END_STREAM
// seguidos imediatamente por RST_STREAM frames
[HEADERS] stream_id=1, END_STREAM
[RST_STREAM] stream_id=1, CANCEL
[HEADERS] stream_id=3, END_STREAM
[RST_STREAM] stream_id=3, CANCEL
[HEADERS] stream_id=5, END_STREAM
[RST_STREAM] stream_id=5, CANCEL
// ... repetido milhares de vezes por segundo
```

**Impacto:** O servidor gasta mais recursos processando e rejeitando os frames do que o atacante gasta enviando-os. Taxas de amplificacao de 2x a 30x foram documentadas.

**Servidores afetados:**
- Nginx (CVE-2023-44487)
- Apache HTTP Server (CVE-2023-44487)
- Golang net/http (CVE-2023-44487)
- Envoy Proxy (CVE-2023-44487)

**Mitigacao:**

```nginx
# nginx 1.25.3+
http2_max_concurrent_streams 128;
http2_max_concurrent_pushes 0;
limit_req_zone $binary_remote_addr zone=http2:10m rate=100r/s;

server {
    listen 443 ssl http2;

    limit_req zone=http2 burst=50 nodelay;

    location / {
        proxy_pass http://backend;
    }
}
```

### 2.4 CVE-2019-9514, CVE-2019-9515: HTTP/2 Resource Exhaustion

O HTTP/2 Data Flood Vulnerability (CVE-2019-9514) permitia que atacantes enviassem frames com payload valido mas inutil, forçando o servidor a consumir memoria e CPU.

**Vulneravel:**

```
// Multiplos DATA frames com dados validos mas inuteis
[DATA] stream_id=1, length=16384, payload=<random_data>
[DATA] stream_id=1, length=16384, payload=<random_data>
[DATA] stream_id=1, length=16384, payload=<random_data>
// O servidor continua aceitando e armazenando em buffers
```

**Mitigacao:**

```apache
# Apache 2.4.41+
# Configurar limites de frames e streams
Http2MaxSessionStreams 100
Http2MaxFrameSize 16384
Http2MaxHeaderBlockSize 16384
```

### 2.5 HPACK Bomb (CVE-2020-11651-like)

A compressao HPACK do HTTP/2 pode ser explorada para criar "bombs" de dados compactados que expandem massivamente:

```
// Um cabecalho de poucos bytes pode expandir para megabytes
// Se o servidor nao limitar a descompressao
Header: cookie = AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA...
// Com HPACK, 1 byte de indice pode referenciar strings longas
// Multiplos indices podem causar explosao de memoria
```

**Mitigacao em nginx:**

```nginx
# Limitar o tamanho total de cabecalhos
large_client_header_buffers 4 8k;

# Limitar o tamanho de cabecalho individual
client_header_buffer_size 1k;

# Definir limite de corpos de request
client_max_body_size 10m;
```

---

## 3. Headers de Seguranca HTTP Completos

### 3.1 Strict-Transport-Security (HSTS)

O header HSTS instrui o navegador a acessar o dominio apenas via HTTPS, eliminando a possibilidade de downgrade attacks durante a navegacao normal.

#### Mecanismo

Quando o navegador recebe este header, ele:
1. Registra o dominio na HSTS includeList
2. Redireciona automaticamente qualquer HTTP para HTTPS
3. Bloqueia certificados invalidos (nao permite bypass)
4. Aplica para todas as subdomains quando inclui subdomains

#### Configuracao Correta

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

**Parametros:**

| Parametro | Descricao | Valor Recomendado |
|-----------|-----------|-------------------|
| max-age | Tempo em segundos que o navegador deve forcar HTTPS | 31536000 (1 ano) no minimo; 63072000 (2 anos) para preload |
| includeSubDomains | Aplica a todas as subdomains | Sempre incluir |
| preload | Permite inclusao na HSTS preload list | Incluir para dominios publicos |

#### Exemplo Completo com nginx

```nginx
# Configuracao HSTS para nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # HSTS header - so adiciona quando ja esta em HTTPS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Configuracao TLS basica
    ssl_certificate /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # TLS minimo 1.2 (1.3 preferido)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
}

# Redirecionamento HTTP -> HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

#### Erros Comuns

**Erro 1: HSTS sem redirect HTTP para HTTPS**

O HSTS so funciona apos a primeira visita via HTTPS. Se o servidor nao redireciona HTTP para HTTPS, a primeira visita e vulneravel a downgrade:

```
# ERRADO: HSTS configurado mas sem redirect HTTP->HTTPS
# O atacante pode interceptar a primeira visita HTTP

# CORRETO: Sempre configurar redirect
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

**Erro 2: max-age muito curto**

```
# ERRADO: max-age muito curto
Strict-Transport-Security: max-age=300

# CORRETO: minimo 1 ano, idealmente 2 anos para preload
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

**Erro 3: HSTS em subdomains sem controlar HTTPS**

Se incluiSubDomains esta definido, TODOS os subdevem ter HTTPS configurado. Caso contrario, o navegador bloqueara acesso a subdomains que so funcionam em HTTP.

### 3.2 Content-Security-Policy (CSP)

O CSP e o header de seguranca mais complexo e mais poderoso do HTTP. Ele define quais recursos o navegador pode carregar e de quais origens.

#### Diretivas Principais

| Diretiva | Descricao |
|----------|-----------|
| default-src | Fallback para todas as diretrizes de busca de recursos |
| script-src | Permite carregar scripts JavaScript |
| style-src | Permite carregar CSS |
| img-src | Permite carregar imagens |
| font-src | Permite carregar fontes |
| connect-src | Permite conexoes (fetch, XHR, WebSocket) |
| frame-src | Permite iframes |
| object-src | Permite plugins (object, embed, applet) |
| media-src | Permite audio e video |
| frame-ancestors | Permite que paginas sejam embutidas |
| form-action | Permite submissoes de formulario |
| base-uri | Permite o elemento base |
| report-uri | URL para receber relatorios de violacao |
| report-to | Endpoint para Reporting API |
| upgrade-insecure-requests | Forca HTTPS para todos os recursos |
| require-trusted-types-for | Forca Trusted Types para DOM manipulation |

#### Exemplo 1: CSP Basico para Aplicacao Web

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.example.com;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self' https://fonts.gstatic.com;
  connect-src 'self' https://api.example.com;
  frame-src 'none';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  upgrade-insecure-requests;
```

#### Exemplo 2: CSP Avancada com Nonce e Reporting

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self' 'nonce-{RANDOM_BASE64}' 'strict-dynamic';
  style-src 'self' 'nonce-{RANDOM_BASE64}';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://api.example.com wss://ws.example.com;
  frame-src https://www.youtube.com https://player.vimeo.com;
  media-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self' https://checkout.example.com;
  frame-ancestors 'self';
  upgrade-insecure-requests;
  report-uri /csp-report;
  report-to csp-endpoint;
```

**Geracao de nonce em Node.js:**

```javascript
// Geracao segura de nonce para CSP
const crypto = require('crypto');

function generateCSPNonce() {
  return crypto.randomBytes(16).toString('baseix');
}

// Exemplo com Express
const express = require('express');
const app = express();

app.use((req, res, next) => {
  const nonce = generateCSPNonce();
  res.locals.cspNonce = nonce;

  const csp = [
    "default-src 'none'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    `style-src 'self' 'nonce-${nonce}'`,
    "img-src 'self' data: https:",
    "font-src 'self'",
    "connect-src 'self' https://api.example.com",
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "upgrade-insecure-requests"
  ].join('; ');

  res.setHeader('Content-Security-Policy', csp);
  next();
});

// Template com nonce injetado
app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <script nonce="${res.locals.cspNonce}">
        // Script inline permitido por causa do nonce
        console.log('CSP nonce working');
      </script>
    </head>
    <body>
      <h1>Pagina com CSP</h1>
    </body>
    </html>
  `);
});
```

**Geracao de nonce em Python (Flask):**

```python
import secrets
from flask import Flask, Response

app = Flask(__name__)

@app.after_request
def add_csp_header(response: Response) -> Response:
    nonce = secrets.token_urlsafe(16)
    csp_policy = (
        f"default-src 'none'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"img-src 'self' data: https:; "
        f"font-src 'self'; "
        f"connect-src 'self' https://api.example.com; "
        f"frame-src 'none'; "
        f"object-src 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self'; "
        f"upgrade-insecure-requests"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    return response
```

#### Exemplo 3: CSP para SPA (Single Page Application)

SPAs sao desafiadoras para CSP porque geralmente usam eval(), inline scripts, e dynamic imports:

```
Content-Security-Policy:
  default-src 'none';
  script-src 'self' 'wasm-unsafe-eval';
  style-src 'self';
  img-src 'self' data: blob: https:;
  font-src 'self' data:;
  connect-src 'self' https://api.example.com wss://ws.example.com;
  worker-src 'self' blob:;
  manifest-src 'self';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
  report-uri /csp-violation;
```

#### CSP Reporting

```
// Endpoint de recebimento de violacoes CSP
// Node.js com Express

app.post('/csp-report', express.json({ type: 'application/csp-report' }), (req, res) => {
  const report = req.body;
  const violation = report['csp-report'];

  console.error('CSP Violation:', {
    documentUri: violation['document-uri'],
    violatedDirective: violation['violated-directive'],
    blockedUri: violation['blocked-uri'],
    sourceFile: violation['source-file'],
    lineNumber: violation['line-number'],
    columnNumber: violation['column-number'],
    statusCode: violation['status-code'],
    effectiveDirective: violation['effective-directive'],
    sample: violation['sample']
  });

  // Enviar para sistema de monitoramento
  metrics.increment('csp.violation', {
    directive: violation['violated-directive'],
    blocked_type: violation['blocked-uri']
  });

  res.status(204).end();
});
```

### 3.3 X-Content-Type-Options

Este header previne que o navegador faça MIME sniffing, forçando-o a seguir o Content-Type declarado pelo servidor.

```
X-Content-Type-Options: nosniff
```

**Por que e critico:**

Se um servidor retorna um arquivo JPEG com Content-Type: text/html e X-Content-Type-Options ausente, o navegador pode interpretar o JPEG como HTML, permitindo XSS stored:

```
# VULNERAVEL: MIME sniffing sem protecao
HTTP/1.1 200 OK
Content-Type: image/jpeg
Content-Length: 45678

<script>alert('XSS')</script>
...dados binarios do JPEG...
```

Com `nosniff`, o navegador respeita o Content-Type declarado e nao executa o "script" como JavaScript.

**Configuracao em servidores:**

```nginx
# nginx
add_header X-Content-Type-Options "nosniff" always;
```

```apache
# Apache
Header always set X-Content-Type-Options "nosniff"
```

```python
# Django
# settings.py
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### 3.4 X-Frame-Options

Previne que a pagina seja carregada em iframes, prevenindo clickjacking.

```
X-Frame-Options: DENY
```

**Valores:**

| Valor | Descricao |
|-------|-----------|
| DENY | Nao permite iframe de nenhuma origem |
| SAMEORIGIN | Permite iframe apenas do mesmo dominio |
| ALLOW-FROM https://example.com | Permite iframe apenas da origem especificada (deprecated) |

**Preferencia moderna:** Use `frame-ancestors` do CSP em vez de X-Frame-Options, pois e mais flexivel. Porem, X-Frame-Options continua necessario para navegadores antigos.

```
# Ambos devem estar presentes para compatibilidade
Content-Security-Policy: frame-ancestors 'self';
X-Frame-Options: DENY
```

### 3.5 Referrer-Policy

Controla quanta informacao da URL de origem e transmitida no cabecalho Referer.

```
Referrer-Policy: strict-origin-when-cross-origin
```

**Valores importantes:**

| Valor | Descricao | Uso Recomendado |
|-------|-----------|-----------------|
| no-referrer | Nao envia Referer nunca | APIs sensiveis |
| no-referrer-when-downgrade | Nao envia em downgrade HTTP | Nao recomendado |
| origin | Envia apenas a origem | Formularios sensiveis |
| origin-when-cross-origin | Origem completa para same-origin, apenas origem para cross-origin | Boa opcao geral |
| strict-origin | Envia origem apenas quando ambos sao HTTPS | Seguro |
| strict-origin-when-cross-origin | Igual acima mas envia URL completa para same-origin | **Recomendado** |
| same-origin | Envia para same-origin, nada para cross-origin | Opcao restritiva |

**Exemplo com nginx:**

```nginx
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 3.6 Permissions-Policy

Substitui Feature-Policy e controla quais funcionalidades do navegador a pagina pode usar.

```
Permissions-Policy:
  camera=(),
  microphone=(),
  geolocation=(self),
  payment=(self),
  usb=(),
  magnetometer=(),
  gyroscope=(),
  accelerometer=(),
  ambient-light-sensor=(),
  autoplay=(self),
  battery=(),
  display-capture=(),
  document-domain=(),
  encrypted-media=(),
  execution-while-not-rendered=(),
  execution-while-out-of-viewport=(),
  fullscreen=(self),
  gamepad=(),
  web-share=(self)
```

**Configuracao com nginx:**

```nginx
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(self), payment=(self), usb=()" always;
```

### 3.7 X-XSS-Protection (DEPRECATED)

Este header era usado para ativar o XSS Auditor do navegador. Porem:

1. O XSS Auditor era facilmente bypassado
2. O XSS Auditor introduziu novas vulnerabilidades (information leakage)
3. Todos os navegadores modernos o removeram
4. O OWASP recomenda **desabilita-lo explicitamente**

```
X-XSS-Protection: 0
```

**Por que 0 e nao remover completamente:**

Alguns navegadores antigos interpretam a ausencia do header como "ativar protecao padrao", o que pode causar comportamentos inesperados. Definir `0` explicitamente desabilita o auditor em todos os navegadores.

```nginx
# nginx - desabilitar XSS Auditor
add_header X-XSS-Protection "0" always;
```

### 3.8 Headers Completos de Seguranca

**Conjunto completo recomendado:**

```nginx
# Headers de seguranca completos para nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'none'; script-src 'self' 'nonce-${csp_nonce}'; style-src 'self' 'nonce-${csp_nonce}'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests; report-uri /csp-report" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
add_header X-XSS-Protection "0" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
add_header Cross-Origin-Embedder-Policy "require-corp" always;
add_header Cross-Origin-Resource-Policy "same-origin" always;
```

### 3.9 COOP, COEP e CORP

Estes headers sao novos e implementam o modelo de isolamento de sitio (Site Isolation) no navegador:

**Cross-Origin-Opener-Policy (COOP):**

```
Cross-Origin-Opener-Policy: same-origin
```

Garante que o top-level document nao tenha referencia a outros top-level documents de origem cruzada. Essencial para prevenir Spectre-like attacks.

**Cross-Origin-Embedder-Policy (COEP):**

```
Cross-Origin-Embedder-Policy: require-corp
```

Garante que todos os recursos carregados tenham permissao explicita para serem embutidos em origens cruzadas.

**Cross-Origin-Resource-Policy (CORP):**

```
Cross-Origin-Resource-Policy: same-origin
```

Indica que o recurso so deve ser carregado na mesma origem.

---

## 4. TLS 1.3 para Web: Cipher Suites e Certificate Pinning

### 4.1 TLS 1.3: O Novo Padrao

TLS 1.3 (RFC 8446) e o protocolo de seguranca para transporte de dados na web. Ele elimina vulnerabilidades do TLS 1.2 e simplifica o handshake.

**Mudancas criticas em relacao ao TLS 1.2:**

1. Removeu RSA key exchange (forward secrecy obrigatorio)
2. Removeu CBC mode ciphers
3. Removeu RC4
4. Removeu DES/3DES
5. Removeu MD5 e SHA-1 para handshake
6. Removeu compression (CRIME attack)
7. Reduziu handshake de 2-RTT para 1-RTT
8. Adicionou 0-RTT resumption

**Cipher suites TLS 1.3 (todos com forward secrecy):**

| Cipher Suite | Chave | Autenticacao | Handshake | Tamanho |
|-------------|-------|--------------|-----------|---------|
| TLS_AES_256_GCM_SHA384 | AES-256-GCM | N/A (via handshake) | SHA-384 | 256 |
| TLS_AES_128_GCM_SHA256 | AES-128-GCM | N/A | SHA-256 | 128 |
| TLS_CHACHA20_POLY1305_SHA256 | ChaCha20 | N/A | SHA-256 | 256 |

### 4.2 Configuracao TLS em nginx

```nginx
# Configuracao TLS 1.3 para nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    # Certificados
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;

    # Protocolos - apenas TLS 1.2 e 1.3
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites - apenas as mais seguras
    ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # Elliptic curves
    ssl_ecdh_curve X25519:P-256:P-384;

    # Session tickets - desabilitar para forward secrecy
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;
    resolver 1.1.1.1 8.8.8.8 valid=300s;
    resolver_timeout 5s;

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # DH parameters para TLS 1.2
    ssl_dhparam /etc/ssl/dhparam.pem;
}
```

**Gerar DH parameters seguros:**

```bash
# Gerar DH parameters com 4096 bits (pode levar minutos)
openssl dhparam -out /etc/ssl/dhparam.pem 4096

# Ou usar 2048 bits (aceitavel para a maioria)
openssl dhparam -out /etc/ssl/dhparam.pem 2048
```

### 4.3 Certificate Pinning

Certificate Pinning (ou public key pinning) e uma tecnica que impede que o navegador aceite certificados emitidos por CAs comprometidas. O navegador "grava" (pina) o certificado ou chave publica de um dominio e so aceita conexoes com certificados correspondentes.

**Formas de implementacao:**

**1. Public-Key-Pins-Report-Only (HTTP Header - deprecated):**

```
Public-Key-Pins-Report-Only:
  pin-sha256="base64+primary==";
  pin-sha256="base64+backup==";
  max-age=5184000;
  includeSubDomains;
  report-uri="https://example.com/pkp-report"
```

**2. HPKP via Expect-CT + Certificate Transparency:**

O HPKP foi deprecated devido a risco de bricking. A abordagem moderna e Certificate Transparency (CT).

**3. Implementacao em codigo (Tokio/Rust):**

```rust
use rustls::ClientConfig;
use std::sync::Arc;

fn configure_tls_with_pinning() -> ClientConfig {
    let mut root_store = rustls::RootCertStore::empty();
    root_store.add_trust_anchors(webpki_roots::TLS_SERVER_ROOTS.iter().cloned());

    let mut config = ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();

    // Pinning de chave publica via custom verifier
    let pinning_verifier = PinnedCertificateVerifier {
        expected_pins: vec![
            "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",  // Pin primario
            "sha256/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",  // Pin backup
        ],
        intermediate_pins: vec![
            "sha256/CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC=",
        ],
    };

    config.dangerous()
        .with_custom_certificate_verifier(Arc::new(pinning_verifier));

    config
}

struct PinnedCertificateVerifier {
    expected_pins: Vec<String>,
    intermediate_pins: Vec<String>,
}

impl rustls::client::danger::ServerCertVerifier for PinnedCertificateVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &rustls::pki_types::CertificateDer<'static>,
        intermediates: &[rustls::pki_types::CertificateDer<'static>],
        server_name: &rustls::pki_types::ServerName<'static>,
        ocsp_response: &[u8],
        now: rustls::pki_types::UnixTime,
    ) -> Result<rustls::client::danger::ServerCertVerified, rustls::Error> {
        // Verificar pin do certificado final
        let end_pin = compute_pin(end_entity);
        if !self.expected_pins.contains(&end_pin) {
            return Err(rustls::Error::General(
                "Certificate pin mismatch for end entity".into()
            ));
        }

        // Verificar pins dos intermediarios
        for intermediate in intermediates {
            let inter_pin = compute_pin(intermediate);
            if self.intermediate_pins.contains(&inter_pin) {
                return Ok(rustls::client::danger::ServerCertVerified::assertion());
            }
        }

        Err(rustls::Error::General(
            "No intermediate certificate matched pin".into()
        ))
    }

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &rustls::pki_types::CertificateDer<'static>,
        dss_sig: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls12_signature(
            message,
            cert,
            dss_sig,
            &rustls::crypto::ring::default_provider().signature_verification_algorithms,
        )
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &rustls::pki_types::CertificateDer<'static>,
        dss_sig: &rustls::DigitallySignedStruct,
    ) -> Result<rustls::client::danger::HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls13_signature(
            message,
            cert,
            dss_sig,
            &rustls::crypto::ring::default_provider().signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<rustls::SignatureScheme> {
        rustls::crypto::ring::default_provider()
            .signature_verification_algorithms
            .supported_schemes()
    }
}

fn compute_pin(cert: &rustls::pki_types::CertificateDer<'static>) -> String {
    use sha2::{Sha256, Digest};
    use base64::Engine;

    let mut hasher = Sha256::new();
    hasher.update(cert.as_ref());
    let hash = hasher.finalize();

    let mut result = String::from("sha256/");
    result.push_str(&base64::engine::general_purpose::STANDARD.encode(hash));
    result
}
```

**4. Certificate Transparency (abordagem moderna):**

```python
# Verificacao de CT em Python com cryptography
from cryptography import x509
from cryptography.hazmat.primitives import hashes

def verify_ct_extension(cert_pem: bytes) -> bool:
    """Verifica se o certificado tem SCTs (Signed Certificate Timestamps)"""
    cert = x509.load_pem_x509_certificate(cert_pem)

    try:
        # Procurar SCT List extension (OID 1.3.6.1.4.1.11129.2.4.5)
        sct_extension = cert.extensions.get_extension_for_oid(
            x509.ObjectIdentifier("1.3.6.1.4.1.11129.2.4.5")
        )
        return sct_extension is not None
    except x509.ExtensionNotFound:
        return False
```

### 4.4 CVE-2014-0160: Heartbleed - Deep Dive

Heartbleed e uma das vulnerabilidades mais devastadoras da historia da internet. Expôs chaves privadas de servidores, dados de usuarios, e tokens de autenticacao de milhoes de sites.

**Mecanismo:**

O heartbeat do TLS permite que um peer envie um payload e receba o mesmo payload de volta. O bug estava no processamento do campo `payload_length`:

```c
// CODIGO VULNERAVEL (simplificado) - OpenSSL 1.0.1 ate 1.0.1f
int dtls1_process_heartbeat(SSL *s) {
    unsigned char *p = &s->s3->rrec.data[0], *pl;
    unsigned short hbtype;
    unsigned int payload;

    // Ler tipo do heartbeat
    hbtype = *p++;

    // Ler tamanho do payload - SEM VALIDACAO!
    n2s(p, payload);

    // Apontar para o payload
    pl = p;

    // Responder com O MESMO tamanho declarado
    // MAS o payload real pode ser menor!
    if (hbtype == TLS1_HB_REQUEST) {
        unsigned char *buffer, *bp;

        // Aloca memoria baseado no payload_length DECLARADO
        buffer = OPENSSL_malloc(1 + 2 + payload + 16);
        bp = buffer;

        *bp++ = TLS1_HB_RESPONSE;
        s2n(payload, bp);

        // COPIA payload bytes da memoria do servidor
        // MAS O PAYLOAD REAL PODE TER APENAS 1 BYTE!
        // Os restantes bytes vem da memoria adjacent do servidor
        memcpy(bp, pl, payload);
        bp += payload;

        // Envia de volta para o atacante
        dtls1_write_heartbeat(s, buffer, 3 + payload + 16);
    }
}
```

**O ataque:**

```
// Atacante envia heartbeat request com payload_length = 65535
// mas com payload real de apenas 1 byte
HeartbeatRequest:
  type: 1 (REQUEST)
  payload_length: 65535
  payload: "A" (1 byte)

// Servidor responde com 65535 bytes
// Os primeiros 1 byte sao o "A"
// Os proximos 65534 bytes sao MEMORIA ADJACENTE do processo
// Isso pode conter:
//   - Chaves privadas TLS
//   - Senhas de usuarios
//   - Tokens de sessao
//   - Dados de outros clientes
```

**Impacto:**
- 17% de todos os certificados SSL confiaveis da web afetados
- Chaves privadas expostas em massa
- Dados sensiveis de usuarios expostos
- Necessidade de reissue massiva de certificados

**Mitigacao:**
- Atualizar OpenSSL para 1.0.1g ou superior
- Revogar e reemitir todos os certificados
- Resetar todas as senhas de usuarios
- Invalidar todos os tokens de sessao
- Monitorar para uso indevido de chaves expostas

### 4.5 CVE-2022-3602 e CVE-2022-3786: Buffer Overflow no OpenSSL

Estas vulnerabilidades do OpenSSL 3.0.x causaram buffer overflows no processamento de certificados X.509 com nomes Unicode excessivamente longos:

```c
// Simplificacao do bug
int do_x509_check(X509 *x, const char *chk, size_t chklen,
                  unsigned int flags, char **peername) {
    GENERAL_NAMES *gens = NULL;
    X509_NAME *name = NULL;
    int cnid = NID_undef;
    int alt_type = GEN_DNS;

    // Buffer fixo para o nome Common Name
    char peername_buffer[256];  // TAMANHO FIXO - VULNERAVEL

    // Se o CN for maior que 256 bytes, overflow occurs
    X509_NAME_oneline(X509_get_subject_name(x),
                      peername_buffer,  // SEM VERIFICACAO DE TAMANHO
                      sizeof(peername_buffer));
}
```

**Mitigacao:**
- Atualizar OpenSSL para 3.0.7+ ou 3.1.1+
- Verificar versao do OpenSSL no deploy

```bash
# Verificar versao do OpenSSL
openssl version

# Output esperado: OpenSSL 3.0.7 ou superior
```

---

## 5. CORS: Preflight, Credentials e Origins

### 5.1 Mecanismo Completo do CORS

CORS (Cross-Origin Resource Sharing) e o mecanismo que o navegador usa para controlar quando uma requisicao de origem cruzada e permitida. Ele protege usuarios contra ataques onde sites maliciosos fazem requests em seu nome.

**Requisicoes Simples (Simple Requests):**

Uma requisicao e considerada "simples" quando:
1. Metodo e GET, HEAD ou POST
2. Headers sao apenas Accept, Accept-Language, Content-Language, Content-Type (com tipos limitados)
3. Nao ha campos de entrada do usuario em Content-Type (exceto application/x-www-form-urlencoded, multipart/form-data, text/plain)

```
// Request simples - sem preflight
GET /api/data HTTP/1.1
Origin: https://other-site.com
Accept: application/json
```

**Requisicoes Nao-Simples (Non-Simple Requests):**

Qualquer requisicao que nao atenda aos criterios acima gera um preflight:

```
// Request que gera preflight
POST /api/data HTTP/1.1
Origin: https://other-site.com
Content-Type: application/json    // Content-Type nao e simples
Authorization: Bearer token       // Header customizado
X-Custom-Header: value           // Header customizado
```

### 5.2 Preflight Request

O preflight e um OPTIONS request que o navegador envia antes da requisicao real:

```
// 1. Preflight (enviado pelo navegador automaticamente)
OPTIONS /api/data HTTP/1.1
Origin: https://other-site.com
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type, authorization
Access-Control-Max-Age: 86400

// 2. Resposta do servidor
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://other-site.com
Access-Control-Allow-Methods: GET, POST, PUT, DELETE
Access-Control-Allow-Headers: content-type, authorization
Access-Control-Max-Age: 86400
Access-Control-Allow-Credentials: true

// 3. Request real (enviada apenas se preflight for aceito)
POST /api/data HTTP/1.1
Origin: https://other-site.com
Content-Type: application/json
Authorization: Bearer token
```

### 5.3 Configuracao CORS Segura

**Exemplo com Express.js:**

```javascript
const express = require('express');
const cors = require('cors');

const app = express();

// Configuracao CORS completa
const corsOptions = {
  origin: function (origin, callback) {
    // Lista de origens permitidas
    const allowedOrigins = [
      'https://app.example.com',
      'https://admin.example.com',
      'https://staging.example.com'
    ];

    // Permite requests sem origin (mobile apps, curl, postman)
    if (!origin) {
      return callback(null, true);
    }

    if (allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      callback(new Error('Origin not allowed by CORS'));
    }
  },

  // Metodos permitidos
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],

  // Headers permitidos
  allowedHeaders: [
    'Content-Type',
    'Authorization',
    'X-Requested-With',
    'X-Request-ID'
  ],

  // Headers expostos ao navegador
  exposedHeaders: [
    'X-Request-ID',
    'X-Total-Count',
    'X-Rate-Limit-Remaining'
  ],

  // Credenciais (cookies, authorization headers)
  credentials: true,

  // Cache do preflight (24 horas)
  maxAge: 86400,

  // Sucesso para status codes 204 e 204
  optionsSuccessStatus: 204
};

app.use(cors(corsOptions));

// Alternativa: configuracao manual sem biblioteca
app.use((req, res, next) => {
  const origin = req.headers.origin;

  if (origin && isAllowedOrigin(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Access-Control-Allow-Credentials', 'true');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Expose-Headers', 'X-Request-ID');
    res.setHeader('Access-Control-Max-Age', '86400');
  }

  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }

  next();
});

function isAllowedOrigin(origin) {
  const allowedOrigins = [
    'https://app.example.com',
    'https://admin.example.com'
  ];
  return allowedOrigins.includes(origin);
}
```

### 5.4 Erros Criticos de CORS

**Erro 1: Origin reflect (O PIOR erro possivel):**

```python
# VULNERAVEL: Refletir qualquer Origin
@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers['Access-Control-Allow-Origin'] = origin  # NUNCA FACO ISSO
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
```

Isso permite que qualquer site acesse a API com credenciais do usuario.

**Erro 2: Wildcard com credenciais:**

```python
# VULNERAVEL: Wildcard com credenciais - navegador rejeita, mas revela informacao
response.headers['Access-Control-Allow-Origin'] = '*'
response.headers['Access-Control-Allow-Credentials'] = 'true'
```

Navegadores rejeitam essa combinacao, mas o simples fato de tentar revela ao atacante que o servidor suporta credenciais.

**Erro 3: Null origin:**

```python
# VULNERAVEL: Permitir null origin (sandbox iframes, data: URIs)
response.headers['Access-Control-Allow-Origin'] = 'null'
```

Isso permite que iframes com src="data:text/html,..." ou sandboxed iframes acessem a API.

### 5.5 CVE-2018-0069: CORS Misconfiguration

Embora a referencia original seja especifica de um vendor, o padrao de CORS misconfiguration e universalmente documentado:

```javascript
// VULNERAVEL: CORS que aceita qualquer subdominio
const corsOptions = {
  origin: function(origin, callback) {
    // Qualquer subdominio de example.com e aceito
    const domain = new URL(origin).hostname;
    if (domain.endsWith('.example.com')) {
      callback(null, true);  // VULNERAVEL: *.example.com e ampla demais
    }
  }
};
```

Um atacante poderia registrar `attacker-example.com` (contem `.example.com`) e explorar isso.

**Correcao - whitelist exata:**

```javascript
const ALLOWED_ORIGINS = new Set([
  'https://app.example.com',
  'https://admin.example.com',
  'https://api.example.com',
  'https://staging.example.com'
]);

function isOriginAllowed(origin) {
  try {
    const url = new URL(origin);
    return url.protocol === 'https:' && ALLOWED_ORIGINS.has(origin);
  } catch {
    return false;
  }
}
```

### 5.6 CORS com Django

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    'https://app.example.com',
    'https://admin.example.com',
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_EXPOSE_HEADERS = [
    'content-length',
    'x-request-id',
]

CORS_PREFLIGHT_MAX_AGE = 86400

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
```

### 5.7 CORS com Go

```go
package main

import (
    "net/http"
    "strings"
)

func corsMiddleware(next http.Handler) http.Handler {
    allowedOrigins := map[string]bool{
        "https://app.example.com":      true,
        "https://admin.example.com":    true,
        "https://staging.example.com":  true,
    }

    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        origin := r.Header.Get("Origin")

        if origin != "" && allowedOrigins[origin] {
            w.Header().Set("Access-Control-Allow-Origin", origin)
            w.Header().Set("Access-Control-Allow-Credentials", "true")
            w.Header().Set("Access-Control-Allow-Methods",
                "GET, POST, PUT, DELETE, PATCH, OPTIONS")
            w.Header().Set("Access-Control-Allow-Headers",
                "Content-Type, Authorization, X-Request-ID")
            w.Header().Set("Access-Control-Expose-Headers",
                "X-Request-ID, X-Total-Count")
            w.Header().Set("Access-Control-Max-Age", "86400")
        }

        if r.Method == "OPTIONS" && origin != "" {
            w.WriteHeader(http.StatusNoContent)
            return
        }

        next.ServeHTTP(w, r)
    })
}
```

---

## 6. Cookies Seguros: Atributos e Configuracao

### 6.1 Atributos de Seguranca

Cada cookie deve ser configurado com os atributos de seguranca apropriados. Cookies sem essas atributos estao sujeitos a roubo, interceptacao e manipulacao.

#### Atributos Completos

```
Set-Cookie: session_id=abc123def456;
  Path=/;
  Domain=.example.com;
  Secure;
  HttpOnly;
  SameSite=Lax;
  Max-Age=3600;
  Expires=Wed, 15 Jun 2026 12:00:00 GMT;
```

#### Descricao de Cada Atributo

| Atributo | Descricao | Seguranca |
|----------|-----------|-----------|
| Secure | Cookie so e enviado via HTTPS | Previne interceptacao em HTTP |
| HttpOnly | Cookie nao e acessivel via JavaScript | Previne roubo via XSS |
| SameSite | Controla envio em requests cross-site | Previne CSRF |
| Path | Escopo do cookie no servidor | Limita onde o cookie e enviado |
| Domain | Dominio para o qual o cookie e valido | Pode ser exploitado se muito amplo |
| Max-Age | Tempo de vida em segundos | Controla duracao |
| Expires | Data de expiracao | Alternativa ao Max-Age |
| Priority | Prioridade do cookie (deprecated) | Nao mais relevante |
| SameParty | Para first-party isolation | Experimental |

### 6.2 SameSite: A Profundidade Completa

SameSite e o atributo mais importante e mais mal comprendido dos cookies.

**Valores:**

| Valor | Comportamento | Protecao CSRF |
|-------|---------------|---------------|
| Strict | Cookie nunca e enviado em cross-site requests | Maxima |
| Lax | Cookie e enviado em top-level navigations (GET) | Boa (padrao moderno) |
| None | Cookie e enviado em todos os cross-site requests | Nenhuma |
| (ausente) | Comportamento varia por navegador | Imprevisivel |

**Quando usar cada valor:**

```
# Sessao de aplicacao - SameSite=Lax (padrao seguro)
Set-Cookie: session_id=abc123; Secure; HttpOnly; SameSite=Lax; Path=/

# Cookie de autenticacao - SameSite=Strict (maxima seguranca)
Set-Cookie: auth_token=xyz789; Secure; HttpOnly; SameSite=Strict; Path=/

# Cookie de terceiros (analytics, embeds) - SameSite=None (obrigatorio)
Set-Cookie: analytics_id=tracker123; Secure; SameSite=None; Path=/
```

**Diferenca critica entre Lax e Strict:**

```
# Cenario: Usuario esta logado em example.com e clica em link para example.com

# Com SameSite=Lax:
# O cookie e ENVIADO na navegacao GET para example.com
# Mas NAO e enviado para POST, PUT, DELETE ou requests de imagem/script

# Com SameSite=Strict:
# O cookie NUNCA e enviado em requests cross-site
# Mesmo navegacao GET nao envia o cookie
# Usuario precisa logar novamente ao clicar link externo
```

### 6.3 Configuracao Segura por Linguagem

**Node.js/Express:**

```javascript
const express = require('express');
const session = require('express-session');

const app = express();

// Configuracao de sessao segura
app.use(session({
  name: '__Host-sessionId',  // Prefixo __Host- forcece Secure, Path=/, Domain ausente
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: true,          // HTTPS obrigatorio
    httpOnly: true,        // Sem acesso JavaScript
    sameSite: 'lax',       // CSRF protection
    maxAge: 3600000,       // 1 hora em milissegundos
    path: '/',             // Escopo raiz
    // NAO definir Domain - impede fixation em subdomains
  }
}));

// Funcao helper para setar cookies seguros
function setSecureCookie(res, name, value, options = {}) {
  const defaults = {
    secure: true,
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 3600,
  };

  const cookieOptions = { ...defaults, ...options };

  // Usar prefixo quando apropriado
  if (cookieOptions.sameSite === 'none') {
    name = name.startsWith('__Secure-') ? name : `__Secure-${name}`;
    cookieOptions.secure = true;  // __Secure- REQUER Secure
  }

  res.cookie(name, value, cookieOptions);
}

// Exemplo de uso
app.post('/login', (req, res) => {
  // ... autenticacao ...
  setSecureCookie(res, 'sessionId', generateSessionId(), {
    maxAge: 86400  // 24 horas
  });

  // Cookie de refresh token com duracao maior
  setSecureCookie(res, 'refreshToken', generateRefreshToken(), {
    maxAge: 604800,  // 7 dias
    httpOnly: true,
    sameSite: 'strict'
  });

  res.json({ success: true });
});
```

**Python/Django:**

```python
# settings.py

# Configuracao de sessao segura
SESSION_COOKIE_SECURE = True           # HTTPS obrigatorio
SESSION_COOKIE_HTTPONLY = True          # Sem acesso JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'        # CSRF protection
SESSION_COOKIE_AGE = 3600              # 1 hora
SESSION_COOKIE_PATH = '/'              # Escopo raiz
SESSION_COOKIE_NAME = '__Host-sessionid'  # Prefixo __Host-

# CSRF cookie
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = '__Host-csrftoken'

# Nao definir SESSION_COOKIE_DOMAIN - previne cookie fixation

# Configuracao de autenticacao
AUTH_COOKIE_SECURE = True
AUTH_COOKIE_HTTPONLY = True
AUTH_COOKIE_SAMESITE = 'Lax'
```

**Go:**

```go
package main

import (
    "net/http"
    "time"
)

func setSecureCookie(w http.ResponseWriter, name, value string) {
    cookie := &http.Cookie{
        Name:     "__Host-" + name,
        Value:    value,
        Path:     "/",
        Secure:   true,
        HttpOnly: true,
        SameSite: http.SameSiteLaxMode,
        MaxAge:   3600,
    }
    http.SetCookie(w, cookie)
}

func setCrossSiteCookie(w http.ResponseWriter, name, value string) {
    cookie := &http.Cookie{
        Name:     name,
        Value:    value,
        Path:     "/",
        Secure:   true,
        HttpOnly: false,  // Necessario para analytics
        SameSite: http.SameSiteNoneMode,
        MaxAge:   86400,
    }
    http.SetCookie(w, cookie)
}

func main() {
    mux := http.NewServeMux()

    mux.HandleFunc("/login", func(w http.ResponseWriter, r *http.Request) {
        // ... autenticacao ...
        setSecureCookie(w, "sessionId", generateSessionID())
        setSecureCookie(w, "refreshToken", generateRefreshToken())

        w.Header().Set("Content-Type", "application/json")
        w.Write([]byte(`{"success": true}`))
    })

    // Middleware para invalidar cookies em logout
    mux.HandleFunc("/logout", func(w http.ResponseWriter, r *http.Request) {
        http.SetCookie(w, &http.Cookie{
            Name:     "__Host-sessionId",
            Value:    "",
            Path:     "/",
            MaxAge:   -1,
            Secure:   true,
            HttpOnly: true,
            SameSite: http.SameSiteLaxMode,
        })

        w.WriteHeader(http.StatusNoContent)
    })

    http.ListenAndServeTLS(":443", "cert.pem", "key.pem", mux)
}
```

### 6.4 CVE-2018-1000120: Cookie Manipulation

Em versoes anteriores a certos frameworks, cookies podiam ser manipulados de formas que bypassavam seguranca:

```javascript
// VULNERAVEL: Cookie sem validacao de Path
// Atacante pode definir cookies que afetam outros paths

// Atacante envia:
Set-Cookie: session=attacker_controlled; Path=/admin

// Se o servidor nao valida o Path, o cookie do atacante
// sobrescreve o cookie legitimo do usuario em /admin
```

**Mitigacao:**

```javascript
// Validacao rigorosa de cookies
function parseCookies(cookieHeader) {
  const cookies = {};
  const pairs = cookieHeader.split(';');

  for (const pair of pairs) {
    const [name, ...rest] = pair.trim().split('=');
    const value = rest.join('=');

    // Validar nome do cookie
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
      continue;  // Rejeitar nomes invalidos
    }

    // Validar tamanho
    if (name.length > 256 || value.length > 4096) {
      continue;  // Rejeitar cookies grandes
    }

    cookies[name] = decodeURIComponent(value);
  }

  return cookies;
}
```

---

## 7. HTTP Request Smuggling

### 7.1 O que e HTTP Request Smuggling

HTTP Request Smuggling e um ataque que explora ambiguidades na interpretacao de boundaries entre multiplos servidores HTTP. O atacante envia um request malicioso que e interpretado de forma diferente pelo servidor front-end e pelo servidor back-end, resultando em "smuggling" (contrabando) de um request dentro de outro.

### 7.2 Variantes do Ataque

#### CL.TE (Content-Length vs Transfer-Encoding)

```
# Front-end usa Content-Length, back-end usa Transfer-Encoding

# REQUEST DO ATACANTE:
POST / HTTP/1.1
Host: vulnerable.example.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 6
Transfer-Encoding: chunked

0

G
```

**Interpretacao do front-end (Content-Length):**

O front-end ve `Content-Length: 6` e envia apenas os primeiros 6 bytes do body:
```
0\r\n\r\nG
```

**Interpretacao do back-end (Transfer-Encoding):**

O back-end ve `Transfer-Encoding: chunked` e processa:
```
0\r\n\r\n
```

O chunk `0` indica fim da mensagem. O restante `G` fica no buffer e e prependado ao proximo request.

**Resultado:** O proximo request legitimo do usuario comeca com `G`, transformando-se em:

```
GPOST / HTTP/1.1
Host: vulnerable.example.com
```

#### TE.CL (Transfer-Encoding vs Content-Length)

```
# Front-end usa Transfer-Encoding, back-end usa Content-Length

POST / HTTP/1.1
Host: vulnerable.example.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 4
Transfer-Encoding: chunked

5c
GPOST / HTTP/1.1
Host: vulnerable.example.com
Content-Type: application/x-www-form-urlencoded

0


```

O back-end ve `Content-Length: 4` e processa apenas `5c\r\n`, interpretando o proximo bloco como request legitimo.

#### TE.TE (Transfer-Encoding obfuscation)

Ambos os servidores usam Transfer-Encoding, mas o front-end aceita uma versao ofuscada que o back-end rejeita:

```
POST / HTTP/1.1
Host: vulnerable.example.com
Transfer-Encoding: chunked
Transfer-Encoding: x

0

GPOST / HTTP/1.1
...
```

O front-end pode aceitar `Transfer-Encoding: x` como invalido e usar um outro header, enquanto o back-end aceita `Transfer-Encoding: chunked`.

### 7.3 CVE-2024-27316: Apache HTTP Server Request Smuggling

O Apache HTTP Server antes da versao 2.4.59 era vulneravel a request smuggling devido a tratamento incorreto de multiplos headers Transfer-Encoding:

```
# REQUEST MALICIOSO
POST / HTTP/1.1
Host: vulnerable.example.com
Transfer-Encoding: chunked
Transfer-Encoding: identity

1c
GET /admin HTTP/1.1
Host: vulnerable.example.com
0


```

O Apache processava o ultimo Transfer-Encoding (identity), enquanto outros servidores podiam usar o primeiro (chunked), criando ambiguidade.

### 7.4 CVE-2023-46805/2024-21887: Ivanti Connect Secure

Embora nao seja request smuggling no sentido classico, este incidente demonstra como ambiguidade na interpretacao de HTTP pode ser devastadora:

```
# Bypass de autenticacao via path traversal no HTTP request
GET /api/v1/totp/user-backup-code/../../system/system-information HTTP/1.1
Host: vpn.example.com

# O parser de URL do servidor interpreta differently o path
# Resultando em acesso sem autenticacao a endpoints protegidos
```

### 7.5 Prevencao

**Regra fundamental:** NUNCA usar multiplos servidores HTTP com parse diferente no mesmo path de request.

**Configuracao segura em nginx (como proxy reverso):**

```nginx
# Configuracao anti-smuggling no nginx
http {
    # Desabilitar Transfer-Encoding no back-end
    proxy_set_header Transfer-Encoding "";

    # Forcar Content-Length em todos os requests
    proxy_http_version 1.1;
    proxy_set_header Connection "";

    # Configuracao de buffer para prevenir buffering issues
    proxy_buffering on;
    proxy_buffer_size 8k;
    proxy_buffers 8 8k;

    # Timeouts para prevenir slow loris
    proxy_connect_timeout 10s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;

    upstream backend {
        server 127.0.0.1:8080;
        # Usar o mesmo software HTTP em todos os backends
    }

    server {
        listen 80;
        server_name example.com;

        location / {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Remover Transfer-Encoding do proxied request
            proxy_set_header Transfer-Encoding "";
        }
    }
}
```

**Configuracao segura em Apache (como proxy):**

```apache
# Desabilitar proxy de Transfer-Encoding
ProxyRequests Off
ProxyPreserveHost On

# Forcar HTTP/1.1 no proxy
ProxyPass / http://127.0.0.1:8080/
ProxyPassReverse / http://127.0.0.1:8080/

# Headers de seguranca
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "DENY"

# Desabilitar TRACE e TRACK
TraceEnable Off
```

---

## 8. HTTP Desync Attacks

### 8.1 Diferenca entre Smuggling e Desync

Enquanto request smuggling e sobre ambiguidade entre servidores, desync attacks exploram a forma como um servidor individual processa requests que nao estao corretamente delimitados.

### 8.2 Request Splitting

O atacante injeta um delimiter de request no body, fazendo com que o servidor interprete metade do body como um novo request:

```
# Request normal
POST /api/upload HTTP/1.1
Host: example.com
Content-Type: text/plain
Content-Length: 35

Hello, this is the first request
POST /api/admin HTTP/1.1
Host: example.com
Content-Type: text/plain
Content-Length: 0

```

O servidor processa apenas os primeiros 35 bytes como body do primeiro request e interpreta o restante como um novo request.

### 8.3 HTTP/2 Desync

Com HTTP/2, os ataques de desync podem usar HPACK para ofuscar headers:

```
# Enviar HEADERS frame com Transfer-Encoding ofuscado via HPACK
# Se o servidor descomprime incorretamente, pode aceitar o header
# enquanto o parser original rejeitaria
```

### 8.4 CVE-2023-35001: HTTP Request Smuggling via Nginx

O nginx antes da versao 1.24.0 era vulneravel devido a tratamento incorreto de chunked encoding em situações especificas:

```nginx
# Configuracao vulnerable
location / {
    proxy_pass http://backend;
    # A ausencia de proxy_http_version 1.1 pode causar issues
    # O nginx por padrao usa HTTP/1.0 para o backend
}
```

**Correcao:**

```nginx
location / {
    proxy_pass http://backend;
    proxy_http_version 1.1;  # SEMPRE especificar HTTP/1.1
    proxy_set_header Connection "";
}
```

### 8.5 Payload Splitting

```python
# Exemplo de payload splitting em Python
# Um atacante pode injetar quebras de linha em campos de formulario

import requests

# Request com payload splitting
payload = (
    "username=admin\r\n"
    "password=anything\r\n"
    "\r\n"
    "POST /api/admin/delete HTTP/1.1\r\n"
    "Host: example.com\r\n"
    "Content-Type: application/x-www-form-urlencoded\r\n"
    "Content-Length: 30\r\n"
    "\r\n"
    "target=attacker_controlled_account"
)

# Se o servidor nao sanitiza \r\n no body, pode interpretar
# o segundo POST como um request separado
response = requests.post(
    'https://example.com/api/login',
    data=payload,
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)
```

### 8.6 Mitigacoes Completas

**1. Usar HTTP/2 end-to-end:**

O HTTP/2 tem frames binarios que eliminam muitas ambiguidades do HTTP/1.1.

**2. Nunca mixar servidores HTTP diferentes:**

```nginx
# ERRADO: nginx proxy para Apache com configs diferentes
# nginx e Apache tem parsers diferentes de HTTP

# CORRETO: Usar o mesmo software em toda a cadeia
# ou usar um proxy que normaliza completamente
```

**3. Normalizar todos os requests antes de processar:**

```python
# Middleware de normalizacao
class NormalizeRequestMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Normalizar line endings
        body = environ.get('wsgi.input')
        if body:
            content = body.read()
            # Remover null bytes
            content = content.replace(b'\x00', b'')
            # Normalizar line endings
            content = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')

            # Verificar por delimitadores suspeitos
            if b'\n\n' in content:
                # Body contem possivel request splitting
                # Logar e rejeitar
                logger.warning("Potential request splitting detected")
                environ['wsgi.input'] = io.BytesIO(b'')
                environ['CONTENT_LENGTH'] = '0'
            else:
                environ['wsgi.input'] = io.BytesIO(content)
                environ['CONTENT_LENGTH'] = str(len(content))

        return self.app(environ, start_response)
```

**4. Implementar rate limiting:**

```nginx
# nginx - rate limiting por IP
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
    }

    location /api/login {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://backend;
    }
}
```

---

## 9. Server Configuration Hardening

### 9.1 nginx Hardening

```nginx
# /etc/nginx/nginx.conf - Configuracao completa de seguranca

# Nivel de worker processes
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # Esconder versao do nginx
    server_tokens off;

    # Desabilitar metodos inuteis
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        # Bloquear todos os metodos exceto GET e POST
        if ($request_method !~ ^(GET|HEAD|POST|PUT|PATCH|DELETE)$) {
            return 405;
        }

        # Desabilitar TRACE e TRACK
        if ($request_method ~* ^(TRACE|TRACK)$) {
            return 405;
        }

        # Redirecionar HTTP para HTTPS
        return 301 https://$host$request_uri;
    }

    # Configuracao HTTPS principal
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name example.com;

        # Certificados SSL
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;

        # TLS configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers on;

        # Session configuration
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;
        ssl_session_timeout 1d;

        # OCSP Stapling
        ssl_stapling on;
        ssl_stapling_verify on;
        ssl_trusted_certificate /etc/nginx/ssl/chain.pem;
        resolver 1.1.1.1 8.8.8.8 valid=300s;
        resolver_timeout 5s;

        # DH parameters
        ssl_dhparam /etc/nginx/ssl/dhparam.pem;

        # Seguranca de requests
        client_body_timeout 10s;
        client_header_timeout 10s;
        client_max_body_size 10m;
        keepalive_timeout 30s;
        send_timeout 10s;

        # Buffers
        client_body_buffer_size 16k;
        client_header_buffer_size 1k;
        large_client_header_buffers 4 8k;

        # Rate limiting
        limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
        limit_conn_zone $binary_remote_addr zone=addr:10m;

        # Headers de seguranca
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-Frame-Options "DENY" always;
        add_header X-XSS-Protection "0" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;
        add_header Cross-Origin-Opener-Policy "same-origin" always;
        add_header Cross-Origin-Embedder-Policy "require-corp" always;

        # Content-Security-Policy
        add_header Content-Security-Policy "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests; report-uri /csp-report" always;

        # Desabilitar listing de diretorios
        autoindex off;

        # Desabilitar Server-Info
        location ~ ^/(?:server-info|server-status)$ {
            deny all;
            return 404;
        }

        # Bloquear arquivos ocultos
        location ~ /\. {
            deny all;
            return 404;
        }

        # Bloquear arquivos de backup
        location ~* \.(bak|old|orig|save|swp|sql|db)$ {
            deny all;
            return 404;
        }

        # Rate limiting e connection limiting
        location / {
            limit_req zone=general burst=20 nodelay;
            limit_conn addr 10;

            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Login com rate limiting mais restritivo
        location /api/login {
            limit_req zone=general burst=5 nodelay;

            proxy_pass http://127.0.0.1:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Health check (sem rate limiting)
        location /health {
            access_log off;
            return 200 "OK\n";
        }
    }
}
```

### 9.2 Apache Hardening

```apache
# /etc/apache2/conf-available/security.conf

# Esconder versao do Apache
ServerTokens Prod
ServerSignature Off

# Desabilitar TRACE e TRACK
TraceEnable Off

# Desabilitar indexacao de diretorios
Options -Indexes -FollowSymLinks -Includes

# Bloquear acesso a arquivos ocultos
<DirectoryMatch "^\.|\/\.">
    Require all denied
</DirectoryMatch>

# Headers de seguranca
Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "DENY"
Header always set X-XSS-Protection "0"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
Header always set Cross-Origin-Opener-Policy "same-origin"
Header always set Cross-Origin-Embedder-Policy "require-corp"

# Remover headers perigosos
Header always unset X-Powered-By
Header always unset Server

# Seguranca de uploads
<Directory /var/www/html/uploads>
    # Desabilitar executacao de scripts
    Options -ExecCGI -Indexes
    AddHandler cgi-script .cgi .pl .py

    # Limitar tipos de arquivo
    <FilesMatch "\.(php|phtml|php3|php4|php5|php7|php8|pl|py|cgi|sh|asp|aspx|jsp)$">
        Require all denied
    </FilesMatch>
</Directory>

# Seguranca de configuracao
<Directory /var/www/html>
    AllowOverride None
    Require all granted

    # PHP security
    <IfModule mod_php.c>
        php_flag display_errors off
        php_flag expose_php off
        php_flag allow_url_fopen off
        php_flag allow_url_include off
        php_flag disable_functions exec,passthru,shell_exec,system,proc_open,popen,show_source
    </IfModule>
</Directory>

# Limitar tamanho de requests
LimitRequestBody 10485760

# Timeout settings
Timeout 30
KeepAliveTimeout 5
MaxKeepAliveRequests 100
```

### 9.3 Caddy Hardening

Caddy e um servidor web moderno com HTTPS automatico:

```caddy
# Caddyfile - Configuracao de seguranca
{
    # Esconder versao
    servers {
        protocol {
            experimental_http3
        }
    }

    # OCSP stapling e automatico no Caddy
    ocsp_stapling on
}

example.com {
    # Headers de seguranca
    header {
        Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "0"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "camera=(), microphone=(), geolocation=()"
        Content-Security-Policy "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests"
        -Server
    }

    # Compressao
    encode gzip zstd

    # Logging
    log {
        output file /var/log/caddy/access.log
        format json
    }

    # Timeouts
    timeouts {
        read_body 10s
        read_header 10s
        write 30s
        idle 120s
    }

    # Limits
    request_body {
        max_size 10MB
    }

    # Proxy reverso com seguranca
    reverse_proxy 127.0.0.1:8080 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}

        transport http {
            read_buffer 16384
            write_buffer 16384
        }

        # Health check
        health_uri /health
        health_interval 30s
        health_timeout 5s
    }

    # Bloquear acesso a arquivos ocultos
    @hidden path */.* *.bak *.old *.orig *.save
    respond @hidden 404

    # Bloquear acesso a diretorios
    @directory path */
    respond @directory 404
}
```

### 9.4 Benchmark CIS

Para validar a configuracao, use ferramentas automatizadas:

```bash
# nginx - test with Mozilla Observatory
curl -s "https://http-observatory.security.mozilla.org/api/v1/analyze?host=example.com" | jq .

# SSL Labs test
curl -s "https://api.ssllabs.com/api/v3/analyze?host=example.com&publish=off&all=done" | jq .

# Testar headers de seguranca
curl -sI https://example.com | grep -iE "(strict-transport|content-security|x-content-type|x-frame|referrer-policy|permissions-policy)"

# Testar com testssl.sh
testssl.sh https://example.com
```

---

## 10. CDN Security

### 10.1 Consideracoes de Seguranca com CDN

CDNs introduzem uma camada intermediaria entre o usuario e o servidor. Isso cria novas superficies de ataque que precisam ser endereçadas.

#### Arquitetura de Seguranca com CDN

```
Usuario -> CDN (Cloudflare, Akamai, AWS CloudFront)
  -> Origin Server (seu servidor)

Pontos criticos:
1. Configuracao do CDN vs Origin
2. Cache de conteudo sensiveis
3. Certificados TLS no CDN
4. Headers de seguranca propagados
5. Rate limiting no CDN
6. DDoS protection
```

### 10.2 Cloudflare Security Headers

```nginx
# Configuracao Cloudflare para protecao de headers
# Via Cloudflare Dashboard ou API

# Configuracao de TLS no Cloudflare
# TLS 1.3 habilitado por padrao

# Configuracao de seguranca do Cloudflare
# Via Page Rules ou Transform Rules

# Regra: Forcar HTTPS em todo o dominio
# Match: *example.com/*
# Setting: Always Use HTTPS = On

# Regra: Security Level para API endpoints
# Match: example.com/api/*
# Setting: Security Level = High
# Setting: Browser Integrity Check = On

# Regra: Bypass cache para endpoints sensiveis
# Match: example.com/api/*
# Setting: Cache Level = Bypass
# Setting: Disable Security = Off
```

### 10.3 AWS CloudFront

```python
# Configuracao de CloudFront com seguranca
import boto3

cloudfront = boto3.client('cloudfront')

# Criar distribuicao com headers de seguranca
distribution_config = {
    'CallerReference': 'example-dist',
    'Origins': {
        'Quantity': 1,
        'Items': [
            {
                'Id': 'origin-example',
                'DomainName': 'example.com',
                'CustomOriginConfig': {
                    'HTTPPort': 80,
                    'HTTPSPort': 443,
                    'OriginProtocolPolicy': 'https-only',
                    'OriginSslProtocols': {
                        'Quantity': 1,
                        'Items': ['TLSv1.2']
                    },
                    'OriginReadTimeout': 30,
                    'OriginKeepaliveTimeout': 5
                }
            }
        ]
    },
    'DefaultCacheBehavior': {
        'TargetOriginId': 'origin-example',
        'ViewerProtocolPolicy': 'redirect-to-https',
        'AllowedMethods': {
            'Quantity': 2,
            'Items': ['GET', 'HEAD']
        },
        'CachePolicyId': 'optimized',
        'Compress': True,
        'ResponseHeadersPolicyId': 'security-headers-policy'
    },
    'CustomErrorResponses': {
        'Quantity': 0
    },
    'Comment': 'Secure distribution',
    'Enabled': True,
    'HttpVersion': 'http2and3',
    'IsIPV6Enabled': True,
    'Logging': {
        'Enabled': True,
        'Bucket': 'logs.example.com.s3.amazonaws.com',
        'Prefix': 'cloudfront/'
    },
    'WebACLId': 'arn:aws:wafv2:us-east-1:123456789012:global/webacl/example/abc123'
}

# Response Headers Policy para seguranca
response_headers_policy = {
    'Name': 'SecurityHeadersPolicy',
    'Comment': 'Security headers for all responses',
    'SecurityHeadersConfig': {
        'StrictTransportSecurity': {
            'Override': True,
            'AccessControlMaxAgeSec': 63072000,
            'IncludeSubdomains': True,
            'Preload': True
        },
        'ContentTypeOptions': {
            'Override': True
        },
        'FrameOptions': {
            'Override': True,
            'FrameOption': 'DENY'
        },
        'XSSProtection': {
            'Override': True,
            'Protection': False
        },
        'ReferrerPolicy': {
            'Override': True,
            'ReferrerPolicy': 'strict-origin-when-cross-origin'
        },
        'ContentSecurityPolicy': {
            "Override": True,
            "ContentSecurityPolicy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'"
        }
    }
}
```

### 10.4 CDN Cache Poisoning Prevention

```nginx
# Prevencao de cache poisoning em CDN
# Configuracao no origin server

# Adicionar headers que o CDN deve respeitar
add_header Cache-Control "private, no-cache, no-store, must-revalidate" always;
add_header Vary "Accept-Encoding, Authorization" always;
add_header X-Cache-Status "MISS" always;

# NUNCA cachear respostas com cookies sensiveis
location /api/ {
    proxy_pass http://backend;
    add_header Cache-Control "private, no-cache, no-store" always;
    add_header Set-Cookie "";  # Propagar para o proximo nivel
}
```

### 10.5 CDN Token Authentication

```python
# CloudFront Signed URLs (previne acesso direto ao origin)
import boto3
import time
import json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
import base64

def create_signed_url(resource_path, key_pair_id, private_key):
    """Criar CloudFront Signed URL"""
    cloudfront = boto3.client('cloudfront')

    # Policy
    policy = {
        "Statement": [{
            "Resource": resource_path,
            "Condition": {
                "DateLessThan": {
                    "AWS:EpochTime": int(time.time()) + 3600  # 1 hora
                }
            }
        }]
    }

    # Assinar
    signer = cloudfront.signer.sign(
        key_pair_id=key_pair_id,
        private_key=private_key,
        resource=resource_path,
        policy=json.dumps(policy)
    )

    return f"https://d1234.cloudfront.net{resource_path}?Signature={signer}&Key-Pair-Id={key_pair_id}"
```

---

## 11. HSTS Preload List

### 11.1 O que e a HSTS Preload List

A HSTS Preload List e uma lista compilada por navegadores (Chrome, Firefox, Safari, Edge) de dominios que devem ser forçados a usar HTTPS mesmo na primeira visita. Essa lista e distribuida com o navegador, entao mesmo que o usuario nunca tenha visitado o dominio, o navegador ja sabe que deve usar HTTPS.

### 11.2 Requisitos para Preload

Para ser incluido na HSTS Preload List, seu dominio deve:

1. Servir HTTPS em todas as subdomains (ou redirecionar HTTP para HTTPS)
2. Servir HTTPS em todas as subdomains
3. Servir um certificado TLS valido (nao auto-assinado)
4. Redirecionar HTTP para HTTPS no host
5. Redirecionar HTTP para HTTPS em todas as subdomains
6. Serve o header HSTS na response HTTPS com:
   - `max-age` de no minimo 31536000 (1 ano)
   - `includeSubDomains` directive
   - `preload` directive

### 11.3 Configuracao Completa para Preload

```nginx
# Configuracao nginx completa para HSTS Preload

# Bloco HTTP para redirecionar tudo para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name example.com *.example.com;

    # Redirecionar todos os requests para HTTPS
    return 301 https://$host$request_uri;
}

# Bloco HTTPS com HSTS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com;

    # HSTS com preload
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # ... resto da configuracao ...
}

# Subdomains precisam de configs similares
# Cada subdominio que serve HTTPS deve ter o HSTS header
```

### 11.4 Testes para Preload

```bash
# Verificar se o dominio atende aos requisitos de preload
# Usar o site oficial: https://hstspreload.org/

# Verificar manualmente
curl -sI https://example.com | grep -i strict-transport

# Output esperado:
# strict-transport-security: max-age=63072000; includeSubDomains; preload

# Verificar subdomains
for sub in www api admin app; do
  echo "=== $sub.example.com ==="
  curl -sI https://$sub.example.com | grep -i strict-transport
done

# Verificar redirect HTTP->HTTPS
curl -sI http://example.com | head -1
# Output esperado: HTTP/1.1 301 Moved Permanently
# ou: HTTP/1.1 308 Permanent Redirect
```

### 11.5 Riscos do Preload

```
# RISCO CRITICO: Uma vez na preload list, remover e LENTO
# O processo de remocao pode levar meses

# ANTES de submeter para preload, VERIFIQUE:
# 1. Todas as subdomains tem HTTPS funcionando
# 2. Nenhum subdomain depende de HTTP
# 3. O redirect HTTP->HTTPS funciona em todos os subdomains
# 4. O certificado e valido para todas as subdomains

# Teste extensivamente antes de submeter
```

### 11.6 Submissao para Preload

```
# Passos para submeter:
# 1. Acesse https://hstspreload.org/
# 2. Insira seu dominio
# 3. Verifique se atende a todos os requisitos
# 4. Submeta

# Apos submissao:
# - Pode levar dias para ser processado
# - Inclusao no Chromium (Chrome, Edge, Opera)
# - Inclusao no Firefox (ate 2 semanas apos Chromium)
# - Inclusao no Safari (processo separado)

# Para remover:
# 1. Remova o header HSTS
# 2. Redirecione HTTPS para HTTP (se necessario)
# 3. Submeta remocao no site
# 4. Aguarde ate 6 meses para remocao completa
```

---

## 12. Mixed Content Prevention

### 12.1 Tipos de Mixed Content

Mixed content occurs when uma pagina HTTPS carrega recursos via HTTP:

**Mixed Content de Audio/Video (Menos perigoso):**
```
<video src="http://example.com/video.mp4"></video>
<audio src="http://example.com/audio.mp3"></audio>
```

**Mixed Content de Imagem (Moderadamente perigoso):**
```
<img src="http://example.com/image.png">
```

**Mixed Content de Script (CATASTROFICO):**
```
<script src="http://example.com/script.js"></script>
<link rel="stylesheet" href="http://example.com/style.css">
<iframe src="http://example.com/frame.html"></iframe>
```

### 12.2 Como o Navegador Trata Mixed Content

```
# Navegador moderno (Chrome 79+, Firefox 59+, Safari 13+):

# Mixed Content de Audio/Video: bloqueado por padrao
# Mixed Content de Imagem: bloqueado em contextos seguros
# Mixed Content de Script: SEMPRE bloqueado
# Mixed Content de Iframe: SEMPRE bloqueado

# Mixed Content em HTTP (nao HTTPS): sem protecao
```

### 12.3 Prevencao com upgrade-insecure-requests

```
Content-Security-Policy: upgrade-insecure-requests
```

Este diretoiva do CSP diz ao navegador para:
1. Transformar todos os HTTP para HTTPS automaticamente
2. Bloquear requests HTTP que nao podem ser convertidos para HTTPS

**Exemplo em nginx:**

```nginx
# Configuracao nginx para prevenir mixed content
add_header Content-Security-Policy "upgrade-insecure-requests; default-src 'self' https:; script-src 'self' https:; style-src 'self' https:; img-src 'self' https: data:; font-src 'self' https:;" always;
```

### 12.4 Content-Security-Policy para HTTP Only

Para proteger contra mixed content em todos os niveis:

```nginx
# CSP que requer HTTPS para todos os recursos
add_header Content-Security-Policy "default-src https:; script-src https:; style-src https:; img-src https: data:; font-src https:; connect-src https: wss:; frame-src https:; media-src https:; object-src 'none'; base-uri 'https:; form-action 'https:'" always;
```

### 12.5 Mixed Content em APIs

```javascript
// Verificar mixed content no frontend
function checkMixedContent() {
  const resources = document.querySelectorAll('img, script, link, iframe, audio, video, source');

  const mixedContent = [];
  resources.forEach(resource => {
    const src = resource.src || resource.href;
    if (src && src.startsWith('http:') && !src.includes('localhost')) {
      mixedContent.push({
        element: resource.tagName,
        source: src,
        severity: getMixedContentSeverity(resource.tagName)
      });
    }
  });

  if (mixedContent.length > 0) {
    console.error('Mixed content detected:', mixedContent);
    return false;
  }
  return true;
}

function getMixedContentSeverity(tagName) {
  const blockable = ['SCRIPT', 'IFRAME', 'OBJECT', 'EMBED'];
  const optInBlockable = ['IMG', 'AUDIO', 'VIDEO', 'SOURCE'];
  const shouldBlock = ['LINK'];

  if (blockable.includes(tagName)) return 'critical';
  if (optInBlockable.includes(tagName)) return 'moderate';
  if (shouldBlock.includes(tagName)) return 'low';
  return 'unknown';
}
```

---

## 13. Cache Poisoning Attacks

### 13.1 Web Cache Poisoning

Web cache poisoning e um ataque onde o atacante injeta headers ou conteudo malicioso no cache de um servidor intermediario (CDN, proxy, load balancer), fazendo com que usuarios legitimos recebam conteudo envenenado.

### 13.2 Cache Poisoning via Unkeyed Headers

```
# Request do atacante com header nao-keyed
GET /page HTTP/1.1
Host: example.com
X-Forwarded-Host: evil.com
X-Original-URL: /admin

# Se o servidor:
# 1. Cacheia a resposta baseada no URL (/page)
# 2. Usa X-Forwarded-Host para gerar links no HTML
# 3. Aceita X-Original-URL para roteamento

# Resultado: A resposta cacheada contem links para evil.com
# Todos os usuarios que acessarem /page receberao o HTML envenenado
```

**Vulneravel:**

```javascript
// Codigo vulneravel no servidor
app.get('/page', (req, res) => {
  const host = req.headers['x-forwarded-host'] || req.hostname;

  // Gera links baseados no header manipulavel
  const html = `
    <a href="https://${host}/other-page">Link</a>
    <img src="https://${host}/image.png">
  `;

  res.send(html);
  // NAO valida se X-Forwarded-Host e legítimo
});
```

**Correcao:**

```javascript
// CORRETO: Validar e sanitizar headers
const TRUSTED_HOSTS = ['example.com', 'www.example.com', 'cdn.example.com'];

app.get('/page', (req, res) => {
  // Ignorar X-Forwarded-Host completamente
  // ou validar contra whitelist
  const host = req.hostname;

  if (!TRUSTED_HOSTS.includes(host)) {
    return res.status(400).send('Invalid host');
  }

  const html = `
    <a href="https://${host}/other-page">Link</a>
    <img src="https://${host}/image.png">
  `;

  res.send(html);
});
```

### 13.3 Cache Poisoning via Vary Header

```
# Request do atacante
GET /page HTTP/1.1
Host: example.com
User-Agent: MaliciousAgent

# Se o servidor:
# 1. Cacheia por URL
# 2. Gera resposta diferente baseado no User-Agent
# 3. NAO inclui header Vary apropriado

# Resultado: A resposta cacheada pode ser servida
# para usuarios com diferentes User-Agents
```

**Prevencao:**

```nginx
# nginx - configurar Vary corretamente
location /page {
    # Vary em headers que afetam a resposta
    add_header Vary "Accept-Encoding, Authorization" always;

    # Nao cachear respostas que variam por cookies
    proxy_cache_bypass $cookie_session_id;

    # Ou nunca cachear para endpoints sensiveis
    add_header Cache-Control "private, no-cache" always;
}
```

### 13.4 CVE-2017-3165: Apache HTTP Cache Poisoning

O Apache HTTP Server antes da versao 2.4.25 permitia cache poisoning via URL encoding:

```
# Request com encoding manipulado
GET /page%2f../admin HTTP/1.1
Host: example.com

# O Apache decodifica e redireciona para /admin
# Mas o cache pode armazenar a resposta como se fosse /page
# Resultado: /admin retorna conteudo cacheado de /page
```

### 13.5 Cache Poisoning via Cache Deception

Cache deception e um ataque onde o atacante engana o servidor para que ele cacheie conteudo sensiveis:

```
# Request do atacante
GET /profile.js HTTP/1.1
Host: example.com
Accept: */*

# Se o servidor:
# 1. Processa /profile como endpoint legitimo (perfil do usuario)
# 2. Ignora a extensao .js (trata como /profile)
# 3. O CDN/cache cacheia a resposta por /profile.js

# Resultado: O cache contem dados sensiveis do usuario
# Se outro usuario acessar /profile.js (que normalmente seria
# um arquivo JavaScript estatico), recebera o perfil do usuario
```

**Prevencao:**

```nginx
# Prevencao de cache deception
location / {
    # Explicitamente definir quais paths sao estaticos
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Nao cachear endpoints dinamicos
    location /api/ {
        add_header Cache-Control "private, no-store" always;
        proxy_pass http://backend;
    }

    # Nao cachear paginas com dados sensiveis
    location /profile {
        add_header Cache-Control "private, no-cache, must-revalidate" always;
        proxy_pass http://backend;
    }

    # Default: nao cachear
    location / {
        add_header Cache-Control "private, no-store" always;
        proxy_pass http://backend;
    }
}
```

### 13.6 CVE-2017-7881: Cache Poisoning via X-Forwarded-Host

Esta CVE documenta um caso real de cache poisoning via header X-Forwarded-Host em multiplos CDNs:

```
# O atacante envia:
GET / HTTP/1.1
Host: target.com
X-Forwarded-Host: evil.com

# O servidor gera HTML contendo:
# <script src="https://evil.com/malicious.js"></script>

# O CDN cacheia esta resposta e servindo para todos os usuarios
```

**Mitigacao completa:**

```javascript
// Middleware de validacao de host
const ALLOWED_HOSTS = new Set([
  'example.com',
  'www.example.com',
  'cdn.example.com'
]);

function validateHost(req, res, next) {
  const host = req.headers.host;

  if (!host || !ALLOWED_HOSTS.has(host.split(':')[0])) {
    return res.status(400).json({ error: 'Invalid host header' });
  }

  // NUNCA confiar em X-Forwarded-Host sem validacao
  // e sempre usar o Host header como fonte de verdade

  next();
}

// Aplicar em todos os endpoints
app.use(validateHost);

// Para endpoints estaticos, adicionar cache-control
app.use('/static', express.static('public', {
  setHeaders: (res) => {
    res.setHeader('Cache-Control', 'public, max-age=31536000, immutable');
    res.setHeader('Vary', 'Accept-Encoding');
  }
}));
```

---

## 14. Configuracao Completa de Seguranca nginx

### 14.1 nginx.conf Completo

```nginx
# /etc/nginx/nginx.conf
# Configuracao de seguranca completa para nginx

# Auto-detect numero de CPUs
worker_processes auto;

# Nivel maximo de arquivos abertos
worker_rlimit_nofile 65535;

# Carregar modulo para limitar conexoes
load_module modules/ngx_http_limit_conn_module.so;

events {
    worker_connections 4096;
    multi_accept on;
    use epoll;
}

http {
    # === IDENTIFICACAO ===
    server_tokens off;
    more_clear_headers Server;

    # === LOGS ===
    log_format main '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main buffer=16k flush=5s;
    error_log /var/log/nginx/error.log warn;

    # === PERFORMANCE ===
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
    types_hash_max_size 2048;
    server_names_hash_bucket_size 64;
    client_body_buffer_size 16k;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;

    # === MIME TYPES ===
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # === GZIP (com restricoes) ===
    gzip on;
    gzip_vary on;
    gzip_min_length 256;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # === LIMITACOES ===
    # Limitar taxa de requests por IP
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    limit_req_zone $binary_remote_addr zone=api:10m rate=20r/s;

    # Limitar numero de conexoes por IP
    limit_conn_zone $binary_remote_addr zone=addr:10m;

    # === PROXY ===
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering on;
    proxy_buffer_size 16k;
    proxy_buffers 4 32k;
    proxy_busy_buffers_size 64k;
    proxy_temp_file_write_size 64k;

    # === RATE LIMITING RESPOSTA ===
    limit_req_status 429;
    limit_conn_status 429;

    # === INCLUDE ===
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

### 14.2 Site Config Completo

```nginx
# /etc/nginx/sites-available/example.com

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name example.com *.example.com;

    # ACME challenge para Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect everything else
    location / {
        return 301 https://$host$request_uri;
    }
}

# Redirect non-www to www
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    return 301 https://www.example.com$request_uri;
}

# Main server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.example.com;

    # === TLS ===
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    ssl_ecdh_curve X25519:P-256:P-384;

    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
    resolver 1.1.1.1 8.8.8.8 valid=300s;
    resolver_timeout 5s;

    ssl_dhparam /etc/nginx/ssl/dhparam.pem;

    # === HEADERS DE SEGURANCA ===
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'nonce-{random}'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://api.example.com wss://ws.example.com; frame-src https://www.youtube.com https://player.vimeo.com; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests; report-uri /csp-report" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "0" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Embedder-Policy "require-corp" always;

    # === LOGGING ===
    access_log /var/log/nginx/example.com.access.log main;
    error_log /var/log/nginx/example.com.error.log warn;

    # === LIMITS ===
    client_body_timeout 10s;
    client_header_timeout 10s;
    client_max_body_size 10m;
    send_timeout 10s;
    keepalive_timeout 30s;

    # === RATE LIMITING ===
    location / {
        limit_req zone=general burst=20 nodelay;
        limit_conn addr 10;

        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;
    }

    # Login endpoint
    location /api/login {
        limit_req zone=login burst=3 nodelay;

        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API endpoints
    location /api/ {
        limit_req zone=api burst=50 nodelay;

        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Vary "Accept-Encoding";

        alias /var/www/example.com/static/;
    }

    # Block hidden files
    location ~ /\. {
        deny all;
        return 404;
    }

    # Block backup files
    location ~* \.(bak|old|orig|save|swp|sql|db)$ {
        deny all;
        return 404;
    }

    # Health check
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # CSP report endpoint
    location /csp-report {
        # Only accept POST
        limit_req zone=api burst=10;

        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Content-Type "application/csp-report";
    }
}
```

---

## 15. Exercicios

### Exercicio 1: Headers de Seguranca (Nivel Basico)

**Objetivo:** Implementar todos os headers de seguranca em uma aplicacao web.

**Enunciado:** Dada a seguinte aplicacao Express.js, adicione todos os headers de seguranca necessarios:

```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.send('<html><body><h1>Hello World</h1></body></html>');
});

app.listen(3000);
```

**Requisitos:**
1. HSTS com 2 anos e preload
2. CSP com nonce para scripts inline
3. X-Content-Type-Options nosniff
4. X-Frame-Options DENY
5. Referrer-Policy strict-origin-when-cross-origin
6. Permissions-Policy bloqueando camera e microphone
7. X-XSS-Protection desabilitado

**Solucao esperada:**
- Middleware que gera nonce por request
- Headers configurados corretamente
- Teste com curl verificando todos os headers

### Exercicio 2: CORS Seguro (Nivel Intermediario)

**Objetivo:** Implementar uma politica CORS segura para uma API multi-tenant.

**Enunciado:** Voce tem uma API que serve para tres tenants diferentes:
- app.client-a.com
- app.client-b.com
- admin.client-a.com

Implemente CORS que:
1. Permita requests de cada tenant apenas para seu dominio
2. Permita credenciais (cookies)
3. Restringa metodos para GET, POST, PUT, DELETE
4. Limite headers a Content-Type e Authorization
5. Previna que o admin namespace seja acessado por requests do client-a

**Solucao esperada:**
- Whitelist dinamica baseada no tenant
- Validacao de origin contra dominios conhecidos
- Headers CORS configurados corretamente
- Testes que verificam que cross-tenant access e bloqueado

### Exercicio 3: Request Smuggling Detection (Nivel Avancado)

**Objetivo:** Implementar um detector de request smuggling em Python.

**Enunciado:** Crie um middleware Python que detecta e previne HTTP request smuggling:

```python
# Implemente o seguinte middleware
class AntiSmugglingMiddleware:
    """
    Detecta e previne HTTP request smuggling

    Requisitos:
    1. Detectar multiplos headers Transfer-Encoding
    2. Detectar Content-Length e Transfer-Encoding simultaneos
    3. Validar chunked encoding
    4. Rejeitar requests com null bytes no body
    5. Logar tentativas de smuggling
    """
    pass
```

**Casos de teste:**
```python
# Teste 1: Multiplos Transfer-Encoding
test_smuggling_cl_te()
test_smuggling_te_cl()
test_smuggling_te_te()
test_null_byte_injection()
test_invalid_chunk_size()
```

### Exercicio 4: Cache Poisoning Prevention (Nivel Avancado)

**Objetivo:** Configurar nginx para prevenir cache poisoning.

**Enunciado:** Configure nginx como proxy reverso para um backend. A configuracao deve:
1. Validar todos os headers de proxy (X-Forwarded-Host, X-Original-URL)
2. Configurar Cache-Control corretamente
3. Implementar Vary apropriado
4. Prevenir cache deception para endpoints sensiveis
5. Configurar CSP que prevenha carregamento de scripts de origens nao confiaveis

**Entregaveis:**
- nginx.conf completo
- Testes que verificam que cache poisoning nao e possivel
- Documentacao das decisoes de seguranca

### Exercicio 5: HSTS e Certificate Pinning (Nivel Intermediario)

**Objetivo:** Configurar HSTS e testar certificate transparency.

**Enunciado:**
1. Configurar nginx para servir HTTPS com HSTS configurado corretamente
2. Verificar se o servidor atende aos requisitos de HSTS preload
3. Implementar verificacao de Certificate Transparency em Python
4. Testar com testssl.sh e reportar resultados

**Entregaveis:**
- nginx.conf com HSTS
- Script Python de verificacao de CT
- Relatorio testssl.sh
- Checklist de pre-submissao para HSTS preload

### Exercicio 6: CVE Analysis (Nivel Expert)

**Objetivo:** Analisar uma CVE real de HTTP security e implementar protecao.

**Enunciado:** Escolha UMA das CVEs documentadas neste capitulo:
- CVE-2023-44487 (HTTP/2 Rapid Reset)
- CVE-2014-0160 (Heartbleed)
- CVE-2023-46805/2024-21887 (Ivanti Connect Secure)

E implemente:
1. Reproducao controlada da vulnerabilidade em ambiente de teste
2. Script de deteccao
3. Mitigacao completa
4. Relatorio tecnico documentando raiz causal e impacto

---

## 16. Referencias

### RFCs e Documentacao Oficial

1. RFC 9110 - HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110
2. RFC 9111 - HTTP Caching: https://www.rfc-editor.org/rfc/rfc9111
3. RFC 9112 - HTTP/1.1: https://www.rfc-editor.org/rfc/rfc9112
4. RFC 9113 - HTTP/2: https://www.rfc-editor.org/rfc/rfc9113
5. RFC 9114 - HTTP/3: https://www.rfc-editor.org/rfc/rfc9114
6. RFC 9000 - QUIC: https://www.rfc-editor.org/rfc/rfc9000
7. RFC 8446 - TLS 1.3: https://www.rfc-editor.org/rfc/rfc8446
8. RFC 8615 - HTTP Header Field Registrations: https://www.rfc-editor.org/rfc/rfc8615
9. RFC 6454 - The Web Origin Concept: https://www.rfc-editor.org/rfc/rfc6454
10. RFC 6265 - HTTP State Management Mechanism (Cookies): https://www.rfc-editor.org/rfc/rfc6265

### OWASP Resources

11. OWASP HTTP Security Response Headers: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
12. OWASP Content Security Policy Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
13. OWASP Cross-Origin Resource Sharing: https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny
14. OWASP Cookie Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cookie_Security_Cheat_Sheet.html
15. OWASP HTTP Request Smuggling: https://owasp.org/www-community/attacks/HTTP_Request_Smuggling

### Mozilla Resources

16. Mozilla Web Security Guidelines: https://infosec.mozilla.org/guidelines/web_security
17. Mozilla Observatory: https://observatory.mozilla.org/
18. Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
19. HSTS Preload List: https://hstspreload.org/
20. Content Security Policy Reference: https://content-security-policy.com/

### CVEs e Incidentes

21. CVE-2023-44487 - HTTP/2 Rapid Reset: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-44487
22. CVE-2019-9514 - HTTP/2 Resource Exhaustion: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-9514
23. CVE-2019-9515 - HTTP/2 Data Flood: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-9515
24. CVE-2014-0160 - Heartbleed: https://heartbleed.com/
25. CVE-2022-3602 - OpenSSL Buffer Overflow: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2022-3602
26. CVE-2023-35001 - Nginx Request Smuggling: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-35001
27. CVE-2023-46805 - Ivanti Connect Secure: https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2023-46805

### Ferramentas de Teste

28. testssl.sh: https://testssl.sh/
29. SSL Labs: https://www.ssllabs.com/ssltest/
30. Security Headers: https://securityheaders.com/
31. Mozilla Observatory: https://observatory.mozilla.org/
32. Burp Suite: https://portswigger.net/burp
33. OWASP ZAP: https://www.zaproxy.org/

### Configuracao de Servidores

34. nginx Documentation: https://nginx.org/en/docs/
35. Apache HTTP Server Documentation: https://httpd.apache.org/docs/2.4/
36. Caddy Documentation: https://caddyserver.com/docs/
37. CIS Benchmarks: https://www.cisecurity.org/cis-benchmarks

---

**[Fim do Capitulo 02 -- Protocolo HTTP Seguro]**

*[Capítulo 03 — OWASP Top 10: Guia Completo](03-owasp-top-10.md)*
