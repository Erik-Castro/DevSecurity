# Capítulo 09 — Criptografia na Web

> *"A criptografia não é uma feature — é a camada fundamental que torna qualquer outra segurança possível."*

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. Configurar e gerenciar certificados TLS/SSL para servidores web, incluindo Let's Encrypt e OCSP Stapling
2. Implementar HTTPS everywhere com estratégias de redirect e HSTS robustas
3. Utilizar a Web Crypto API completa: encrypt/decrypt, sign/verify, key generation
4. Projetar criptografia ponta-a-ponta (E2E) em aplicações web
5. Implementar operações com SubtleCrypto: AES-GCM, RSA-OAEP, ECDSA e ECDH
6. Comparar e aplicar hashing de senhas com bcrypt e Argon2 em web apps
7. Gerar números aleatórios seguros em navegadores modernos
8. Implementar Certificate Transparency e compreender seu papel na segurança
9. Configurar DANE e DNSSEC para validação de certificados
10. Habilitar forward secrecy em servidores web
11. Configurar TLS termination em load balancers
12. Implementar criptografia de conteúdo em armazenamento em nuvem
13. Conduzir exercícios práticos de criptografia web

---

## 9.1 TLS para Web: Certificate Management, Let's Encrypt, OCSP

### 9.1.1 Fundamentos do TLS

O Transport Layer Security (TLS) é o protocolo que garante confidencialidade, integridade e autenticação em comunicações web. Desde sua última iteração estável (TLS 1.3, definido no RFC 8446), o protocolo eliminou muitas das fragilidades das versões anteriores, como o suporte a cifras de modo CBC e a renegociação insegura.

A arquitetura TLS opera em duas camadas principais:

1. **Handshake Protocol**: Negociação de algoritmos, troca de chaves e autenticação mútua
2. **Record Protocol**: Criptografia e integridade dos dados transmitidos

O handshake TLS 1.3 simplificou drasticamente o processo, reduzindo o número de round-trips de dois para apenas um (com suporte a 0-RTT para conexões repetidas):

```
Client                          Server
  |                                |
  |--- ClientHello --------------->|
  |    (supported_versions,        |
  |     key_share, signature_algs) |
  |                                |
  |<--- ServerHello ---------------|
  |    (key_share, cipher_suite)   |
  |<--- {EncryptedExtensions} -----|
  |<--- {Certificate} -------------|
  |<--- {CertificateVerify} -------|
  |<--- {Finished} ----------------|
  |                                |
  |--- {Finished} ---------------->|
  |                                |
  |<==== Application Data =========>
```

### 9.1.2 Certificate Management

A gestão de certificados TLS é um dos pilares da segurança web. Um certificado X.509 estabelece a confiança entre o cliente e o servidor, atestando que o domínio consultado é realmente administrado pelo titular do certificado.

Estrutura de um certificado X.509 v3:

```
Certificate ::= SEQUENCE {
    tbsCertificate       TBSCertificate,       -- Dados a serem assinados
    signatureAlgorithm   AlgorithmIdentifier,  -- Algoritmo usado na assinatura
    signatureValue       BIT STRING             -- Assinatura digital do CA
}

TBSCertificate ::= SEQUENCE {
    version         [0]  INTEGER DEFAULT v1,
    serialNumber         INTEGER,
    signature            AlgorithmIdentifier,
    issuer               Name,
    validity             Validity,
    subject              Name,
    subjectPublicKeyInfo SubjectPublicKeyInfo,
    issuerUniqueID  [1]  IMPLICIT UniqueIdentifier OPTIONAL,
    subjectUniqueID [2]  IMPLICIT UniqueIdentifier OPTIONAL,
    extensions      [3]  Extensions OPTIONAL
}
```

As extensões mais importantes para uso web são:

| Extensão | Finalidade |
|----------|-----------|
| `subjectAltName` (SAN) | Lista de domínios/IPs cobertos pelo certificado |
| `keyUsage` | Restringe usos da chave (digitalSignature, keyEncipherment) |
| `extendedKeyUsage` | Especifica purpose (serverAuth, clientAuth) |
| `basicConstraints` | Indica se é CA (pathLen) ou certificado final |
| `crlDistributionPoints` | URL para lista de certificados revogados |
| `authorityInfoAccess` | URLs para OCSP e issuers |
| `certificatePolicies` | Políticas de certificação aplicáveis |

### 9.1.3 Let's Encrypt

O Let's Encrypt é uma Autoridade Certificadora (CA) gratuita e automatizada que utiliza o protocolo ACME (Automatic Certificate Management Environment, RFC 8555) para emissão e renovação de certificados.

O protocolo ACME opera através dos seguintes desafios:

**HTTP-01 Challenge**:
O servidor CA solicita que um arquivo específico seja servido em `http://<domain>/.well-known/acme-challenge/<token>`. Isso valida que o solicitante controla o servidor web do domínio.

```
GET /.well-known/acme-challenge/xyz123 HTTP/1.1
Host: example.com

HTTP/1.1 200 OK
Content-Type: application/octet-stream

xyz123.abc456def789...token-signature
```

**DNS-01 Challenge**:
O servidor CA solicita a criação de um registro TXT específico no DNS do domínio. Este desafio é necessário para wildcard certificates.

```
_acme-challenge.example.com. 300 IN TXT "dGhpcyBpcyBhIHRva2Vu"
```

**TLS-ALPN-01 Challenge**:
Utiliza uma extensão TLS-specific durante o handshake TLS. O servidor CA se conecta via TLS e verifica a presença de um certificado auto-assinado com uma extensão específica no campo Subject Alternative Name.

Configuração com Certbot:

```bash
# Instalação no Ubuntu/Debian
sudo apt update && sudo apt install certbot python3-certbot-nginx

# Certificado básico com auto-configuração do nginx
sudo certbot --nginx -d example.com -d www.example.com

# Certificado wildcard (requer DNS-01)
sudo certbot certonly --manual --preferred-challenges dns \
    -d "*.example.com" -d example.com

# Configuração para DNS via Cloudflare API
sudo certbot certonly --dns-cloudflare \
    --dns-cloudflare-credentials ~/.secrets/cloudflare.ini \
    -d "*.example.com" -d example.com

# Verificação do certificado
sudo certbot certificates

# Renovação manual
sudo certbot renew --dry-run

# Cron job para renovação automática (já instalado pelo apt)
# /etc/cron.d/certbot
0 */12 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
```

Configuração avançada com o plugin nginx:

```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # Certificados Let's Encrypt
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Certificado de cadeia intermediária (trusted)
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;

    # Parâmetros TLS modernos
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Session tickets para performance
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # DH parameters personalizado
    ssl_dhparam /etc/nginx/ssl/dhparam.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9.1.4 OCSP (Online Certificate Status Protocol)

O OCSP (definido no RFC 6960) é um protocolo de validação de certificados em tempo real. Permite que clientes verifiquem se um certificado foi revogado antes de confiar nele.

**Problema do OCSP padrão**: Sem OCSP Stapling, o navegador precisa fazer uma conexão separada para o servidor OCSP da CA, o que:

1. Revela ao CA quais sites o usuário está visitando (problema de privacidade)
2. Adiciona latência ao handshake TLS
3. Se o servidor OCSP estiver indisponível, browsers podem falhar abertamente ou (mais comumente) ignorar a verificação — o chamado "soft-fail"

**OCSP Stapling** resolve esses problemas: o servidor web busca periodicamente o status OCSP e "encarta" (staple) a resposta junto com o certificado durante o handshake TLS.

```
Servidor web                  CA OCSP
    |                            |
    |--- OCSP Request ---------->|
    |    (cert serial + issuer)  |
    |                            |
    |<-- OCSP Response ----------|
    |    (status: good/revoked)  |
    |    (nextUpdate: timestamp) |
    |                            |
    | (armazena e usa no        |
    |  próximo TLS handshake)    |
```

Configuração do OCSP Stapling em nginx:

```nginx
# Habilita OCSP Stapling
ssl_stapling on;

# Habilita verificação da resposta OCSP
ssl_stapling_verify on;

# Define o chain de certificados para verificação
ssl_trusted_certificate /etc/nginx/ssl/chain.pem;

# Resolvers para buscar o endpoint OCSP da CA
resolver 1.1.1.1 8.8.8.8 valid=300s;
resolver_timeout 5s;

# Tamanho do cache OCSP
ssl_stapling_cache shared:OCSP:10m;
```

Verificação do OCSP Stapling em produção:

```bash
# Verificar OCSP Stapling via OpenSSL
openssl s_client -connect example.com:443 -status -servername example.com </dev/null 2>/dev/null | \
    grep -A 5 "OCSP response"

# Output esperado com OCSP funcionando:
# OCSP response:
# ============================================
# OCSP Response Data:
#     OCSP Response Status: successful (0x0)
#     Response Type: Basic OCSP Response
#     ...

# Teste automatizado com curl
curl -v --cert-status https://example.com 2>&1 | grep -i ocsp

# Script de monitoramento
#!/bin/bash
DOMAIN="example.com"
OCSP_STATUS=$(echo | openssl s_client -connect ${DOMAIN}:443 -status -servername ${DOMAIN} 2>/dev/null | \
    grep -o "OCSP Response Status: .*")

if [[ "$OCSP_STATUS" == *"successful"* ]]; then
    echo "OCSP Stapling OK: $OCSP_STATUS"
else
    echo "OCSP Stapling FAIL: $OCSP_STATUS"
    # Alerta aqui
fi
```

### 9.1.5 Gestão de Certificados em Escala

Em ambientes com múltiplos domínios e microserviços, a gestão de certificados requer ferramentas especializadas:

**cert-manager para Kubernetes**:

```yaml
# ClusterIssuer para Let's Encrypt
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
      - dns01:
          cloudflare:
            email: admin@example.com
            apiTokenSecretRef:
              name: cloudflare-api-token
              key: api-token

---
# Certificate para um domínio
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-com-cert
  namespace: production
spec:
  secretName: example-com-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - example.com
    - www.example.com
    - api.example.com
  duration: 2160h    # 90 dias
  renewBefore: 360h  # Renova 15 dias antes

---
# Ingress usando o certificado
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/hsts: "true"
    nginx.ingress.kubernetes.io/hsts-max-age: "63072000"
    nginx.ingress.kubernetes.io/hsts-include-subdomains: "true"
spec:
  tls:
    - hosts:
        - example.com
        - www.example.com
      secretName: example-com-tls
  rules:
    - host: example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-service
                port:
                  number: 80
```

**Vault como PKI interna**:

```hcl
# Vault PKI Secret Engine
path "pki/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

# Gerar root CA interna
vault secrets enable -path=pki pki
vault secrets tune -max-lease-ttl=87600h pki

vault write pki/root/generate/internal \
    common_name="Internal Root CA" \
    ttl=87600h \
    key_bits=4096

# Configurar URLs de distribuição
vault write pki/config/urls \
    issuing_certificates="https://vault.internal:8200/v1/pki/ca" \
    crl_distribution_points="https://vault.internal:8200/v1/pki/crl"

# Gerar emitente intermediário
vault secrets enable -path=pki_int pki
vault write pki_int/intermediate/generate/internal \
    common_name="Internal Intermediate CA" \
    key_bits=4096

# Assinar o emitente intermediário com a root CA
vault write -format=json pki/root/sign-intermediate \
    @pki_int/csr.pem \
    format=pem_bundle \
    ttl=43800h > /tmp/intermediate.pem

# Emitir certificado para servidor web
vault write pki_int/issue/web-server \
    common_name="api.internal.example.com" \
    alt_names="api.internal.example.com,localhost" \
    ip_sans="127.0.0.1,10.0.0.1" \
    ttl=720h \
    format=pem
```

**Exemplo com HashiCorp Vault e Node.js**:

```javascript
const https = require('https');
const fs = require('fs');

const VAULT_ADDR = 'https://vault.internal:8200';
const VAULT_TOKEN = process.env.VAULT_TOKEN;

// Obter certificado do Vault
async function getCertificate(serviceName) {
    const response = await fetch(`${VAULT_ADDR}/v1/pki_int/issue/${serviceName}`, {
        method: 'POST',
        headers: {
            'X-Vault-Token': VAULT_TOKEN,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            common_name: `${serviceName}.internal.example.com`,
            ttl: '720h',
        }),
    });

    const data = await response.json();
    return {
        cert: data.data.certificate,
        key: data.data.private_key,
        ca: data.data.issuing_ca,
        expiration: data.data.expiration,
    };
}

// Criar servidor HTTPS com certificado do Vault
async function createSecureServer(serviceName, port) {
    const { cert, key, ca } = await getCertificate(serviceName);

    const options = {
        key: key,
        cert: cert,
        ca: ca,
        // Força verificação mútua (mTLS)
        requestCert: true,
        rejectUnauthorized: true,
        // Protocolos permitidos
        minVersion: 'TLSv1.2',
        maxVersion: 'TLSv1.3',
    };

    const server = https.createServer(options, (req, res) => {
        // Verificar certificado do cliente
        const clientCert = req.socket.getPeerCertificate();
        console.log('Client CN:', clientCert.subject?.CN);

        res.writeHead(200, { 'Content-Type': 'text/plain' });
        res.end('Hello from secure server!');
    });

    server.listen(port, () => {
        console.log(`Secure server running on port ${port}`);
    });

    return server;
}

createSecureServer('api-gateway', 8443);
```

---

## 9.2 HTTPS Everywhere: Redirect Strategies, HSTS

### 9.2.1 Estratégias de Redirect HTTP para HTTPS

A transição completa para HTTPS requer que todas as requisições HTTP sejam redirecionadas para HTTPS de forma segura e eficiente.

**Redirect na camada de rede (iptables/nftables)**:

```bash
#!/bin/bash
# Redirect HTTP (port 80) para HTTPS (port 443) via iptables
# Apenas para tráfego destinado ao próprio servidor

# Habilitar IP forwarding
sysctl -w net.ipv4.ip_forward=1

# Redirect para IP específico do servidor
SERVER_IP="10.0.0.1"

iptables -t nat -A PREROUTING -i eth0 -p tcp -s ! $SERVER_IP \
    --dport 80 -j REDIRECT --to-port 443

iptables -t nat -A PREROUTING -i eth0 -p tcp -s $SERVER_IP \
    --dport 80 -j REDIRECT --to-port 443

# Persistir regras
iptables-save > /etc/iptables/rules.v4
```

**Redirect em Nginx (configuração recomendada)**:

```nginx
# Bloco HTTP — redireciona TUDO para HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com *.example.com;

    # Let's Encrypt ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }

    # Redirecionamento 301 (permanente) para HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# Bloco HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # ... (restante da configuração TLS)
}
```

**Redirect em Apache**:

```apache
# Mod_rewrite para redirect 301
<VirtualHost *:80>
    ServerName example.com
    ServerAlias www.example.com

    # ACME challenge para Let's Encrypt
    Alias /.well-known/acme-challenge/ /var/www/certbot/.well-known/acme-challenge/
    <Directory /var/www/certbot/.well-known/acme-challenge/>
        Options None
        AllowOverride None
        Require all granted
    </Directory>

    # Redirect para HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

# Bloco HTTPS com OCSP Stapling
<VirtualHost *:443>
    ServerName example.com
    ServerAlias www.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/example.com/privkey.pem

    SSLUseStapling on
    SSLStaplingCache "shmcb:logs/stapling-cache(150000)"
    SSLStaplingResponseMaxAge 900

    # Headers de segurança
    Header always set Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "DENY"
</VirtualHost>
```

**Redirect em HAProxy (load balancer)**:

```
frontend http_front
    bind *:80
    # Let's Encrypt ACME
    acl is_acme path_beg /.well-known/acme-challenge/
    use_backend certbot_back if is_acme

    # Redirect para HTTPS
    http-request redirect scheme https unless { ssl_fc }

frontend https_front
    bind *:443 ssl crt /etc/ssl/certs/example.pem
    default_backend web_servers

backend certbot_back
    server certbot 127.0.0.1:8888

backend web_servers
    balance roundrobin
    server web1 10.0.0.10:8080 check
    server web2 10.0.0.11:8080 check
```

**Redirect com PHP (quando não há controle do servidor web)**:

```php
<?php
// Redirecionamento HTTPS via PHP
// Usar apenas quando não for possível configurar no servidor web

$isHttps = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off')
    || (!empty($_SERVER['SERVER_PORT']) && $_SERVER['SERVER_PORT'] == 443)
    || (!empty($_SERVER['HTTP_X_FORWARDED_PROTO']) && $_SERVER['HTTP_X_FORWARDED_PROTO'] === 'https');

if (!$isHttps) {
    $redirectUrl = 'https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI'];
    header('HTTP/1.1 301 Moved Permanently');
    header('Location: ' . $redirectUrl);
    exit();
}
```

### 9.2.2 HSTS (HTTP Strict Transport Security)

O HSTS (RFC 6797) é um mecanismo que instrui os navegadores a acessar o site APENAS via HTTPS, eliminando a primeira conexão insegura e protegando contra downgrade attacks e cookie hijacking.

**Cabeçalho HSTS**:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

| Diretiva | Descrição | Recomendação |
|----------|-----------|-------------|
| `max-age` | Tempo (segundos) que o navegador deve forçar HTTPS | Mínimo 31536000 (1 ano) para produção |
| `includeSubDomains` | Aplica a todos os subdomínios | Sempre incluir |
| `preload` | Permite inclusão na lista de preload dos navegadores | Necessário para proteção inicial |

**Lista de preload**:

Os navegadores (Chrome, Firefox, Safari, Edge) mantêm uma lista de domínios que devem ser acessados APENAS via HTTPS, mesmo na primeira visita. Para inclusão:

1. O site deve servir HTTPS em todas as páginas
2. Redirecionar HTTP para HTTPS com 301/302
3. Usar HSTS com `max-age` mínimo de 31536000 segundos
4. Incluir `includeSubDomains`
5. Permitir `preload`
6. Submeter em https://hstspreload.org

**HSTS e Single Sign-On (SSO)**:

```javascript
// Middleware Node.js com HSTS configurável
function hstsMiddleware(options = {}) {
    const defaults = {
        maxAge: 31536000,           // 1 ano
        includeSubDomains: true,
        preload: true,
    };

    const config = { ...defaults, ...options };

    return (req, res, next) => {
        // Apenas para conexões HTTPS
        if (req.secure || req.headers['x-forwarded-proto'] === 'https') {
            let header = `max-age=${config.maxAge}`;
            if (config.includeSubDomains) header += '; includeSubDomains';
            if (config.preload) header += '; preload';

            res.setHeader('Strict-Transport-Security', header);
        }

        // Redirect HTTP para HTTPS se não estiver em HTTPS
        if (!req.secure && req.headers['x-forwarded-proto'] !== 'https') {
            const httpsUrl = `https://${req.headers.host}${req.url}`;
            return res.redirect(301, httpsUrl);
        }

        next();
    };
}

// Uso com Express
const express = require('express');
const app = express();

// HSTS para ambiente de produção
if (process.env.NODE_ENV === 'production') {
    app.use(hstsMiddleware({
        maxAge: 63072000,  // 2 anos (para preload)
        includeSubDomains: true,
        preload: true,
    }));
}

// HSTS para desenvolvimento (max-age menor)
if (process.env.NODE_ENV === 'development') {
    app.use(hstsMiddleware({
        maxAge: 0,
        includeSubDomains: false,
        preload: false,
    }));
}
```

**Cuidados com HSTS**:

1. **Max-age muito alto**: Se o site precisar voltar para HTTP (migração), usuários que já visitaram ficarão presos em HTTPS. Comece com `max-age=300` (5 minutos) e aumente gradualmente.

2. **IncludeSubDomains**: Certe-se de que TODOS os subdomínios suportam HTTPS. Um subdomínio sem HTTPS ficará inacessível.

3. **Preload é permanente**: Remover um domínio da lista de preload pode levar meses. Não ative `preload` até ter certeza absoluta.

4. **HSTS + HTTP**: O header HSTS só é processado quando entregue via HTTPS. Nunca envie o header em respostas HTTP.

```python
# Python/Django: Middleware HSTS
class HSTSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.is_secure():
            max_age = 63072000 if not request.META.get('DEBUG') else 300
            header = f'max-age={max_age}; includeSubDomains; preload'
            response['Strict-Transport-Security'] = header

        return response
```

### 9.2.3 Double Submit Cookie Pattern com HTTPS

O Double Submit Cookie é uma defesa CSRF que se beneficia de HTTPS — o cookie não pode ser lido por JavaScript (HttpOnly) mas está disponível no servidor para comparação:

```javascript
// Express.js: Double Submit Cookie com HTTPS
const crypto = require('crypto');
const express = require('express');
const cookieParser = require('cookie-parser');
const helmet = require('helmet');

const app = express();

app.use(cookieParser());
app.use(helmet());

// Gerar token CSRF e definir em cookie + metadado
function generateCsrfProtection(req, res, next) {
    if (req.method === 'GET') {
        const token = crypto.randomBytes(32).toString('hex');
        res.cookie('XSRF-TOKEN', token, {
            httpOnly: false,     // Precisa ser acessível por JS no double-submit
            secure: true,        // HTTPS only
            sameSite: 'strict',
            path: '/',
        });
        res.locals.csrfToken = token;
    }
    next();
}

// Verificar token CSRF em requisições mutáveis
function verifyCsrfToken(req, res, next) {
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) {
        const cookieToken = req.cookies['XSRF-TOKEN'];
        const headerToken = req.headers['x-xsrf-token'];

        if (!cookieToken || !headerToken) {
            return res.status(403).json({ error: 'CSRF token missing' });
        }

        if (!crypto.timingSafeEqual(
            Buffer.from(cookieToken, 'hex'),
            Buffer.from(headerToken, 'hex')
        )) {
            return res.status(403).json({ error: 'CSRF token mismatch' });
        }
    }
    next();
}

app.use(generateCsrfProtection);
app.use(verifyCsrfToken);
```

---

## 9.3 Web Crypto API: Encrypt/Decrypt, Sign/Verify, Key Generation

### 9.3.1 Visão Geral da Web Crypto API

A Web Crypto API (W3C Recommendation) fornece criptografia segura diretamente no navegador, sem necessidade de bibliotecas externas. Diferente do descontinuado `window.crypto`, a Web Crypto API oferece operações criptográficas padronizadas e otimizadas.

**Interface principal**:

```typescript
// Tipos TypeScript para a Web Crypto API
interface Crypto {
    readonly subtle: SubtleCrypto;
    getRandomValues(array: ArrayBufferView): ArrayBufferView;
    randomUUID(): string;
}

interface SubtleCrypto {
    // Criptografia simétrica
    encrypt(algorithm: AlgorithmIdentifier | RsaOaepParams | AesCtrParams | AesCbcParams | AesGcmParams,
            key: CryptoKey,
            data: BufferSource): Promise<ArrayBuffer>;

    decrypt(algorithm: AlgorithmIdentifier | RsaOaepParams | AesCtrParams | AesCbcParams | AesGcmParams,
            key: CryptoKey,
            data: BufferSource): Promise<ArrayBuffer>;

    // Assinatura digital
    sign(algorithm: AlgorithmIdentifier | RsaPssParams | EcdsaParams,
         key: CryptoKey,
         data: BufferSource): Promise<ArrayBuffer>;

    verify(algorithm: AlgorithmIdentifier | RsaPssParams | EcdsaParams,
           key: CryptoKey,
           signature: BufferSource,
           data: BufferSource): Promise<boolean>;

    // Derivação e importação de chaves
    generateKey(algorithm: AlgorithmIdentifier | RsaKeyGenParams | EcKeyGenParams | AesKeyGenParams,
                extractable: boolean,
                keyUsages: KeyUsage[]): Promise<CryptoKey | CryptoKeyPair>;

    deriveKey(algorithm: AlgorithmIdentifier | EcdhKeyDeriveParams,
              baseKey: CryptoKey,
              derivedKeyType: AlgorithmIdentifier | AesKeyGenParams,
              extractable: boolean,
              keyUsages: KeyUsage[]): Promise<CryptoKey>;

    deriveBits(algorithm: AlgorithmIdentifier | EcdhKeyDeriveParams,
               baseKey: CryptoKey,
               length: number): Promise<ArrayBuffer>;

    // Importação e exportação
    importKey(format: KeyFormat,
              keyData: BufferSource | JsonWebKey,
              algorithm: AlgorithmIdentifier | RsaKeyGenParams | EcKeyGenParams | AesKeyGenParams,
              extractable: boolean,
              keyUsages: KeyUsage[]): Promise<CryptoKey>;

    exportKey(format: 'raw' | 'spki' | 'pkcs8' | 'jwk',
              key: CryptoKey): Promise<ArrayBuffer | JsonWebKey>;

    // Hash
    digest(algorithm: AlgorithmIdentifier,
           data: BufferSource): Promise<ArrayBuffer>;

    // Wrap/unwrap
    wrapKey(format: KeyFormat,
            key: CryptoKey,
            wrappingKey: CryptoKey,
            wrapAlgorithm: AlgorithmIdentifier): Promise<ArrayBuffer>;

    unwrapKey(format: KeyFormat,
              wrappedKey: BufferSource,
              unwrappingKey: CryptoKey,
              unwrapAlgorithm: AlgorithmIdentifier,
              unwrappedKeyType: AlgorithmIdentifier | RsaKeyGenParams | EcKeyGenParams | AesKeyGenParams,
              extractable: boolean,
              keyUsages: KeyUsage[]): Promise<CryptoKey>;
}
```

### 9.3.2 Gerenciamento de Chaves

```javascript
// Geração de chaves para diferentes algoritmos

// 1. Chave AES-GCM (simétrica, 256 bits)
async function generateAESKey() {
    const key = await window.crypto.subtle.generateKey(
        {
            name: 'AES-GCM',
            length: 256,  // 128, 192 ou 256
        },
        true,   // extractable
        ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
    );
    return key;
}

// 2. Par de chaves RSA-OAEP
async function generateRSAKeyPair() {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: 'RSA-OAEP',
            modulusLength: 2048,
            publicExponent: new Uint8Array([1, 0, 1]),  // 65537
            hash: 'SHA-256',
        },
        true,   // extractable
        ['encrypt', 'decrypt']  // keyUsages
    );
    return keyPair;  // { publicKey, privateKey }
}

// 3. Par de chaves ECDSA (assinatura)
async function generateECDSAKeyPair() {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: 'ECDSA',
            namedCurve: 'P-256',  // P-256, P-384, P-521
        },
        true,   // extractable
        ['sign', 'verify']
    );
    return keyPair;
}

// 4. Par de chaves ECDH (troca de chaves)
async function generateECDHKeyPair() {
    const keyPair = await window.crypto.subtle.generateKey(
        {
            name: 'ECDH',
            namedCurve: 'P-256',
        },
        true,   // extractable
        ['deriveKey', 'deriveBits']
    );
    return keyPair;
}

// 5. Chave HMAC (assinatura com segredo compartilhado)
async function generateHMACKey() {
    const key = await window.crypto.subtle.generateKey(
        {
            name: 'HMAC',
            hash: 'SHA-256',
        },
        true,   // extractable
        ['sign', 'verify']
    );
    return key;
}
```

### 9.3.3 Exportação e Importação de Chaves

```javascript
// Formatos de exportação: raw, spki, pkcs8, jwk

// Exportar chave AES (formato raw)
async function exportAESKey(key) {
    const raw = await window.crypto.subtle.exportKey('raw', key);
    return new Uint8Array(raw);
}

// Exportar chave pública RSA (formato SPKI)
async function exportPublicKey(key) {
    const spki = await window.crypto.subtle.exportKey('spki', key);
    return new Uint8Array(spki);
}

// Exportar chave privada (formato PKCS8)
async function exportPrivateKey(key) {
    const pkcs8 = await window.crypto.subtle.exportKey('pkcs8', key);
    return new Uint8Array(pkcs8);
}

// Exportar em formato JWK (JSON Web Key)
async function exportJWK(key) {
    const jwk = await window.crypto.subtle.exportKey('jwk', key);
    return jwk;
}

// Importar chave AES a partir de bytes brutos
async function importAESKey(rawBytes) {
    return window.crypto.subtle.importKey(
        'raw',
        rawBytes,
        { name: 'AES-GCM', length: 256 },
        true,
        ['encrypt', 'decrypt']
    );
}

// Importar chave a partir de JWK
async function importJWK(jwk) {
    return window.crypto.subtle.importKey(
        'jwk',
        jwk,
        { name: jwk.alg === 'A256GCM' ? 'AES-GCM' : 'RSA-OAEP' },
        false,
        ['encrypt', 'decrypt']
    );
}

// Importar chave pública de PEM (SPKI)
async function importPublicKeyPEM(pemString) {
    // Remover headers PEM e decodificar base64
    const pemBody = pemString
        .replace(/-----BEGIN PUBLIC KEY-----/, '')
        .replace(/-----END PUBLIC KEY-----/, '')
        .replace(/\s+/g, '');

    const binaryDer = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));

    return window.crypto.subtle.importKey(
        'spki',
        binaryDer,
        {
            name: 'RSA-OAEP',
            hash: 'SHA-256',
        },
        false,
        ['encrypt', 'verify']
    );
}

// Importar chave privada de PEM (PKCS8)
async function importPrivateKeyPEM(pemString) {
    const pemBody = pemString
        .replace(/-----BEGIN PRIVATE KEY-----/, '')
        .replace(/-----END PRIVATE KEY-----/, '')
        .replace(/\s+/g, '');

    const binaryDer = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));

    return window.crypto.subtle.importKey(
        'pkcs8',
        binaryDer,
        {
            name: 'RSA-OAEP',
            hash: 'SHA-256',
        },
        true,
        ['decrypt', 'sign']
    );
}
```

### 9.3.4 Operações de Criptografia Simétrica (AES)

```javascript
// AES-GCM: Autenticated Encryption with Associated Data (AEAD)

// Criptografar com AES-GCM
async function encryptAESGCM(key, plaintext, associatedData) {
    // IV (Initialization Vector) deve ser único para cada operação
    const iv = window.crypto.getRandomValues(new Uint8Array(12));  // 96 bits para GCM

    // Dados associados (não criptografados mas autenticados)
    const aad = associatedData
        ? new TextEncoder().encode(associatedData)
        : new Uint8Array(0);

    const ciphertext = await window.crypto.subtle.encrypt(
        {
            name: 'AES-GCM',
            iv: iv,
            additionalData: aad,
            tagLength: 128,  // 128 bits para o tag de autenticação
        },
        key,
        new TextEncoder().encode(plaintext)
    );

    return {
        iv: iv,
        ciphertext: new Uint8Array(ciphertext),
    };
}

// Descriptografar com AES-GCM
async function decryptAESGCM(key, encryptedData, associatedData) {
    const aad = associatedData
        ? new TextEncoder().encode(associatedData)
        : new Uint8Array(0);

    const decrypted = await window.crypto.subtle.decrypt(
        {
            name: 'AES-GCM',
            iv: encryptedData.iv,
            additionalData: aad,
            tagLength: 128,
        },
        key,
        encryptedData.ciphertext
    );

    return new TextDecoder().decode(decrypted);
}

// Exemplo completo: Criptografia de dados no navegador
async function demoAESGCM() {
    // Gerar chave
    const key = await window.crypto.subtle.generateKey(
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );

    // Dados para criptografar
    const dadosSensiveis = {
        nome: "João Silva",
        cpf: "123.456.789-00",
        email: "joao@example.com",
        saldo: 50000.00,
    };

    const plaintext = JSON.stringify(dadosSensiveis);

    // Criptografar
    const encrypted = await encryptAESGCM(key, plaintext, "user-session-123");

    console.log("IV:", Array.from(encrypted.iv).map(b => b.toString(16).padStart(2, '0')).join(''));
    console.log("Ciphertext (base64):", btoa(String.fromCharCode(...encrypted.ciphertext)));

    // Descriptografar
    const decrypted = await decryptAESGCM(key, encrypted, "user-session-123");
    const dadosRecuperados = JSON.parse(decrypted);

    console.log("Dados originais:", dadosRecuperados);
}

// AES-CBC (para compatibilidade, não recomendado para novos projetos)
async function encryptAESCBC(key, plaintext) {
    const iv = window.crypto.getRandomValues(new Uint8Array(16));  // 128 bits para CBC

    // Padding PKCS7 via SubtleCrypto
    const ciphertext = await window.crypto.subtle.encrypt(
        {
            name: 'AES-CBC',
            iv: iv,
        },
        key,
        new TextEncoder().encode(plaintext)
    );

    return {
        iv: iv,
        ciphertext: new Uint8Array(ciphertext),
    };
}

// AES-CTR (Counter mode, útil para streaming)
async function encryptAESCTR(key, plaintext, counter) {
    const nonce = window.crypto.getRandomValues(new Uint8Array(16));

    const ciphertext = await window.crypto.subtle.encrypt(
        {
            name: 'AES-CTR',
            counter: counter || nonce,
            length: 64,  // Tamanho do counter em bits
        },
        key,
        new TextEncoder().encode(plaintext)
    );

    return {
        counter: counter || nonce,
        ciphertext: new Uint8Array(ciphertext),
    };
}
```

### 9.3.5 Operações de Assinatura Digital

```javascript
// RSA-PSS: Recomendado para assinatura de documentos

// Assinar dados com RSA-PSS
async function signWithRSAPSS(privateKey, data) {
    const encodedData = new TextEncoder().encode(data);

    const signature = await window.crypto.subtle.sign(
        {
            name: 'RSA-PSS',
            saltLength: 32,  // Tamanho do salt em bytes (recomendado: 32)
        },
        privateKey,
        encodedData
    );

    return new Uint8Array(signature);
}

// Verificar assinatura RSA-PSS
async function verifyRSAPSS(publicKey, signature, data) {
    const encodedData = new TextEncoder().encode(data);

    const isValid = await window.crypto.subtle.verify(
        {
            name: 'RSA-PSS',
            saltLength: 32,
        },
        publicKey,
        signature,
        encodedData
    );

    return isValid;
}

// ECDSA: Mais eficiente, recomendado para novos sistemas

// Assinar dados com ECDSA
async function signWithECDSA(privateKey, data) {
    const encodedData = new TextEncoder().encode(data);

    const signature = await window.crypto.subtle.sign(
        {
            name: 'ECDSA',
            hash: 'SHA-256',  // Algoritmo de hash a ser aplicado
        },
        privateKey,
        encodedData
    );

    // Convertendo para formato DER (para interoperabilidade)
    return derEncodeSignature(new Uint8Array(signature));
}

// Verificar assinatura ECDSA
async function verifyECDSA(publicKey, signature, data) {
    const encodedData = new TextEncoder().encode(data);

    // Decodificar de DER se necessário
    const rawSignature = derDecodeSignature(signature);

    const isValid = await window.crypto.subtle.verify(
        {
            name: 'ECDSA',
            hash: 'SHA-256',
        },
        publicKey,
        rawSignature,
        encodedData
    );

    return isValid;
}

// Funções auxiliares para DER encoding (necessário para JWS/JWT)
function derEncodeSignature(signature) {
    // Assinatura ECDSA é (r, s), cada um de 32 bytes para P-256
    const r = signature.slice(0, 32);
    const s = signature.slice(32, 64);

    function encodeLength(len) {
        if (len < 128) return [len];
        const bytes = [];
        let temp = len;
        while (temp > 0) {
            bytes.unshift(temp & 0xff);
            temp >>= 8;
        }
        return [0x80 | bytes.length, ...bytes];
    }

    function encodeInteger(int) {
        // Remover zeros à esquerda, mas manter pelo menos um byte
        let start = 0;
        while (start < int.length - 1 && int[start] === 0) start++;
        const trimmed = int.slice(start);
        // Se o bit mais significativo está setado, adicionar zero padding
        if (trimmed[0] & 0x80) {
            return [0x02, trimmed.length + 1, 0x00, ...trimmed];
        }
        return [0x02, trimmed.length, ...trimmed];
    }

    const encodedR = encodeInteger(r);
    const encodedS = encodeInteger(s);
    const content = [...encodedR, ...encodedS];

    return new Uint8Array([
        0x30,
        ...encodeLength(content.length),
        ...content,
    ]);
}

function derDecodeSignature(der) {
    let offset = 0;

    if (der[offset++] !== 0x30) throw new Error('Invalid DER signature');
    offset++; // Skip sequence length

    // Read r
    if (der[offset++] !== 0x02) throw new Error('Invalid DER integer');
    const rLen = der[offset++];
    const r = der.slice(offset, offset + rLen);
    offset += rLen;

    // Read s
    if (der[offset++] !== 0x02) throw new Error('Invalid DER integer');
    const sLen = der[offset++];
    const s = der.slice(offset, offset + sLen);

    return new Uint8Array([...r, ...s]);
}

// HMAC: Autenticação com chave secreta
async function signHMAC(key, data) {
    const encodedData = new TextEncoder().encode(data);

    const signature = await window.crypto.subtle.sign(
        'HMAC',
        key,
        encodedData
    );

    return new Uint8Array(signature);
}

async function verifyHMAC(key, signature, data) {
    const encodedData = new TextEncoder().encode(data);

    return window.crypto.subtle.verify(
        'HMAC',
        key,
        signature,
        encodedData
    );
}
```

---

## 9.4 Client-Side Encryption: End-to-End Encryption in Web Apps

### 9.4.1 Princípios da Criptografia Ponta-a-Ponta (E2E)

A criptografia ponta-a-ponta garante que apenas o remetente e o destinatário possam ler as mensagens. Nem o servidor, nem intermediários, nem provedores de infraestrutura podem acessar o conteúdo em texto plano.

**Modelo de segurança E2E para web**:

```
Remetente                    Servidor                    Destinatário
    |                            |                            |
    | 1. Gerar chave simétrica   |                            |
    |    (mensagem)              |                            |
    |                            |                            |
    | 2. Criptografar mensagem   |                            |
    |    com chave simétrica     |                            |
    |                            |                            |
    | 3. Criptografar chave      |                            |
    |    com chave pública       |                            |
    |    do destinatário         |                            |
    |                            |                            |
    | 4. Enviar:                 |                            |
    |    {mensagem_cifrada}      |                            |
    |    {chave_cifrada}         |                            |
    |---------------------------->|                            |
    |                            | 5. Armazenar              |
    |                            |    (não pode ler)          |
    |                            |---------------------------->|
    |                            |                            | 6. Descifrar chave
    |                            |                            |    com chave privada
    |                            |                            |
    |                            |                            | 7. Descifrar mensagem
    |                            |                            |    com chave simétrica
```

### 9.4.2 Implementação Completa de E2E Messaging

```javascript
// Sistema completo de mensagens com criptografia E2E
class E2EEncryptedMessaging {
    constructor() {
        this.keyPairs = new Map();  // userId -> { publicKey, privateKey }
    }

    // Gerar par de chaves para um usuário
    async generateUserKeys(userId) {
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: 'RSA-OAEP',
                modulusLength: 2048,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash: 'SHA-256',
            },
            true,  // extractable (para persistir)
            ['encrypt', 'decrypt']
        );

        this.keyPairs.set(userId, keyPair);

        // Exportar chave pública para distribuição
        const publicKeyJwk = await window.crypto.subtle.exportKey('jwk', keyPair.publicKey);

        return {
            userId: userId,
            publicKey: publicKeyJwk,
            // Chave privada NUNCA sai do dispositivo
        };
    }

    // Obter chave pública de outro usuário (simula busca no servidor)
    async getPublicKey(userId) {
        // Em produção: buscar do servidor de chaves
        // const response = await fetch(`/api/keys/${userId}`);
        // return await response.json();
        return this.keyPairs.get(userId)?.publicKey;
    }

    // Enviar mensagem criptografada
    async encryptMessage(senderId, recipientId, message) {
        // 1. Buscar chave pública do destinatário
        const recipientPublicKeyJwk = await this.getPublicKey(recipientId);
        if (!recipientPublicKeyJwk) {
            throw new Error(`Public key not found for user ${recipientId}`);
        }

        // Importar chave pública
        const recipientPublicKey = await window.crypto.subtle.importKey(
            'jwk',
            recipientPublicKeyJwk,
            { name: 'RSA-OAEP', hash: 'SHA-256' },
            false,
            ['encrypt']
        );

        // 2. Gerar chave simétrica para esta mensagem
        const messageKey = await window.crypto.subtle.generateKey(
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );

        // 3. Criptografar mensagem com chave simétrica
        const iv = window.crypto.getRandomValues(new Uint8Array(12));
        const encodedMessage = new TextEncoder().encode(message);

        const encryptedMessage = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            messageKey,
            encodedMessage
        );

        // 4. Exportar e criptografar a chave simétrica
        const rawMessageKey = await window.crypto.subtle.exportKey('raw', messageKey);

        const encryptedMessageKey = await window.crypto.subtle.encrypt(
            { name: 'RSA-OAEP' },
            recipientPublicKey,
            rawMessageKey
        );

        // 5. Montar pacote criptografado
        return {
            senderId: senderId,
            recipientId: recipientId,
            timestamp: Date.now(),
            encryptedMessage: this.arrayBufferToBase64(encryptedMessage),
            encryptedMessageKey: this.arrayBufferToBase64(encryptedMessageKey),
            iv: this.arrayBufferToBase64(iv),
        };
    }

    // Receber e descriptografar mensagem
    async decryptMessage(recipientId, encryptedPackage) {
        const privateKeyPair = this.keyPairs.get(recipientId);
        if (!privateKeyPair) {
            throw new Error(`Private key not found for user ${recipientId}`);
        }

        // 1. Descriptografar a chave simétrica com chave privada RSA
        const encryptedMessageKey = this.base64ToArrayBuffer(encryptedPackage.encryptedMessageKey);

        const rawMessageKey = await window.crypto.subtle.decrypt(
            { name: 'RSA-OAEP' },
            privateKeyPair.privateKey,
            encryptedMessageKey
        );

        // 2. Importar chave simétrica
        const messageKey = await window.crypto.subtle.importKey(
            'raw',
            rawMessageKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['decrypt']
        );

        // 3. Descriptografar a mensagem
        const iv = this.base64ToArrayBuffer(encryptedPackage.iv);
        const encryptedMessage = this.base64ToArrayBuffer(encryptedPackage.encryptedMessage);

        const decryptedMessage = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            messageKey,
            encryptedMessage
        );

        return {
            senderId: encryptedPackage.senderId,
            message: new TextDecoder().decode(decryptedMessage),
            timestamp: encryptedPackage.timestamp,
        };
    }

    // Utilitários de conversão
    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    base64ToArrayBuffer(base64) {
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
        }
        return bytes.buffer;
    }
}

// Exemplo de uso
async function demoE2E() {
    const messaging = new E2EEncryptedMessaging();

    // Alice e Bob geram suas chaves
    await messaging.generateUserKeys('alice');
    await messaging.generateUserKeys('bob');

    // Alice envia mensagem criptografada para Bob
    const encryptedPkg = await messaging.encryptMessage(
        'alice',
        'bob',
        'Olá Bob! Esta mensagem é confidencial.'
    );

    console.log('Mensagem criptografada:', encryptedPkg);

    // Bob recebe e descriptografa
    const decrypted = await messaging.decryptMessage('bob', encryptedPkg);
    console.log('Mensagem descriptografada:', decrypted.message);
}
```

### 9.4.3 Key Exchange Protocol (X3DH)

O protocolo X3DH (Extended Triple Diffie-Hellman), usado pelo Signal Protocol, permite建立 um canal seguro mesmo entre usuários que nunca se comunicaram:

```javascript
// Implementação simplificada do X3DH para web
class X3DHKeyExchange {
    // Gerar chave de identidade (long-term)
    async generateIdentityKey() {
        return window.crypto.subtle.generateKey(
            { name: 'ECDH', namedCurve: 'P-256' },
            true,
            ['deriveKey', 'deriveBits']
        );
    }

    // Gerar chave de assinatura (long-term)
    async generateSigningKey() {
        return window.crypto.subtle.generateKey(
            { name: 'ECDSA', namedCurve: 'P-256' },
            true,
            ['sign', 'verify']
        );
    }

    // Gerar chave de pré-assinatura (one-time)
    async generatePreKey() {
        return window.crypto.subtle.generateKey(
            { name: 'ECDH', namedCurve: 'P-256' },
            true,
            ['deriveKey', 'deriveBits']
        );
    }

    // Gerar chave de sessão (efêmera)
    async generateSignedPreKey(signingKey) {
        const preKey = await window.crypto.subtle.generateKey(
            { name: 'ECDH', namedCurve: 'P-256' },
            true,
            ['deriveKey', 'deriveBits']
        );

        // Exportar chave pública para assinar
        const publicKeyData = await window.crypto.subtle.exportKey('raw', preKey.publicKey);

        // Assinar a chave pública
        const signature = await window.crypto.subtle.sign(
            { name: 'ECDSA', hash: 'SHA-256' },
            signingKey.privateKey,
            publicKeyData
        );

        return {
            keyPair: preKey,
            signature: new Uint8Array(signature),
        };
    }

    // Derivar chave compartilhada via ECDH
    async deriveSharedKey(privateKey, publicKey) {
        return window.crypto.subtle.deriveKey(
            {
                name: 'ECDH',
                public: publicKey,
            },
            privateKey,
            { name: 'AES-GCM', length: 256 },
            false,
            ['encrypt', 'decrypt']
        );
    }

    // Derivar chave de sessão via X3DH (simplificado)
    async computeX3DHSharedSecret(
        aliceIdentityKey,   // Par de chaves de identidade de Alice
        bobIdentityKey,     // Chave pública de identidade de Bob
        bobSignedPreKey,    // Chave pública de pré-assinatura de Bob
        aliceEphemeralKey   // Chave efêmera de Alice
    ) {
        // DH1 = DH(Alice_Identity, Bob_Signed_PreKey)
        const dh1 = await window.crypto.subtle.deriveBits(
            { name: 'ECDH', public: bobSignedPreKey },
            aliceIdentityKey.privateKey,
            256
        );

        // DH2 = DH(Alice_Ephemeral, Bob_Identity)
        const dh2 = await window.crypto.subtle.deriveBits(
            { name: 'ECDH', public: bobIdentityKey },
            aliceEphemeralKey.privateKey,
            256
        );

        // DH3 = DH(Alice_Ephemeral, Bob_Signed_PreKey)
        const dh3 = await window.crypto.subtle.deriveBits(
            { name: 'ECDH', public: bobSignedPreKey },
            aliceEphemeralKey.privateKey,
            256
        );

        // KDF: Concatenar DH1 || DH2 || DH3 e derivar chave final
        const combinedSecret = new Uint8Array(96);  // 3 * 32 bytes
        combinedSecret.set(new Uint8Array(dh1), 0);
        combinedSecret.set(new Uint8Array(dh2), 32);
        combinedSecret.set(new Uint8Array(dh3), 64);

        // Usar HKDF para derivar chave final
        const derivedKey = await this.hkdfExpand(combinedSecret, 'X3DH-Symmetric', 32);

        return derivedKey;
    }

    // HKDF (HMAC-based Key Derivation Function)
    async hkdfExpand(inputKeyMaterial, info, length) {
        const encoder = new TextEncoder();
        const infoBytes = encoder.encode(info);

        // Importar IKM como chave HMAC
        const baseKey = await window.crypto.subtle.importKey(
            'raw',
            inputKeyMaterial,
            { name: 'HMAC', hash: 'SHA-256' },
            false,
            ['sign']
        );

        // HKDF-Expand
        const n = Math.ceil(length / 32);
        let previousBlock = new Uint8Array(32);
        const outputBlocks = [];

        for (let i = 1; i <= n; i++) {
            const hmacInput = new Uint8Array(32 + infoBytes.length + 1);
            hmacInput.set(previousBlock, 0);
            hmacInput.set(infoBytes, 32);
            hmacInput[32 + infoBytes.length] = i;

            const hmacResult = await window.crypto.subtle.sign('HMAC', baseKey, hmacInput);
            previousBlock = new Uint8Array(hmacResult);
            outputBlocks.push(previousBlock);
        }

        // Concatenar e truncar para o tamanho desejado
        const result = new Uint8Array(length);
        let offset = 0;
        for (const block of outputBlocks) {
            result.set(block.slice(0, length - offset), offset);
            offset += block.length;
        }

        return result;
    }
}
```

---

## 9.5 SubtleCrypto: AES-GCM, RSA-OAEP, ECDSA, ECDH

### 9.5.1 AES-GCM em Detalhes

O AES-GCM (Galois/Counter Mode) é o modo de operação recomendado para criptografia autenticada. Ele fornece tanto confidencialidade quanto integridade (via tag de autenticação).

**Parâmetros críticos**:

| Parâmetro | Tamanho | Notas |
|-----------|---------|-------|
| Chave | 128, 192 ou 256 bits | 256 recomendado |
| IV/Nonce | 96 bits (12 bytes) | NUNCA reutilizar com a mesma chave |
| Tag | 128 bits (padrão) | Tags menores reduzem segurança |
| AAD | Variável | Dados autenticados mas não cifrados |

```javascript
// AES-GCM: Implementação completa com validação de segurança

class SecureAESGCM {
    static MAX_IV_REUSE = 2 ** 32;  // Limite de operações antes de rekey

    constructor(key) {
        this.key = key;
        this.usageCounter = 0;
        this.usedNonces = new Set();
    }

    // Gerar chave AES-GCM segura
    static async generateKey(length = 256) {
        if (![128, 192, 256].includes(length)) {
            throw new Error(`Invalid AES key length: ${length}`);
        }

        return window.crypto.subtle.generateKey(
            { name: 'AES-GCM', length },
            true,
            ['encrypt', 'decrypt']
        );
    }

    // Criptografar com validação de nonce
    async encrypt(plaintext, associatedData = null) {
        this.usageCounter++;

        // Verificar necessidade de rekey
        if (this.usageCounter > SecureAESGCM.MAX_IV_REUSE) {
            throw new Error('Key usage limit reached. Generate new key.');
        }

        // Gerar nonce único de 12 bytes
        const nonce = window.crypto.getRandomValues(new Uint8Array(12));

        // Verificar que o nonce não foi usado antes (defesa contra reutilização)
        const nonceHex = Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join('');
        if (this.usedNonces.has(nonceHex)) {
            // Em produção: erro fatal — nonce reutilizado indica falha grave
            throw new Error('CRITICAL: Nonce collision detected!');
        }
        this.usedNonces.add(nonceHex);

        const encodedPlaintext = new TextEncoder().encode(plaintext);

        const ciphertext = await window.crypto.subtle.encrypt(
            {
                name: 'AES-GCM',
                iv: nonce,
                additionalData: associatedData
                    ? new TextEncoder().encode(associatedData)
                    : new Uint8Array(0),
                tagLength: 128,
            },
            this.key,
            encodedPlaintext
        );

        // Separar ciphertext do tag (últimos 16 bytes)
        const ciphertextArray = new Uint8Array(ciphertext);
        const tag = ciphertextArray.slice(-16);
        const ciphertextOnly = ciphertextArray.slice(0, -16);

        return {
            nonce: nonce,
            ciphertext: ciphertextOnly,
            tag: tag,
            usageCounter: this.usageCounter,
        };
    }

    // Descriptografar com verificação de autenticidade
    async decrypt(encryptedData, associatedData = null) {
        // Reconstruir ciphertext com tag
        const ciphertextWithTag = new Uint8Array(
            encryptedData.ciphertext.length + encryptedData.tag.length
        );
        ciphertextWithTag.set(encryptedData.ciphertext, 0);
        ciphertextWithTag.set(encryptedData.tag, encryptedData.ciphertext.length);

        try {
            const decrypted = await window.crypto.subtle.decrypt(
                {
                    name: 'AES-GCM',
                    iv: encryptedData.nonce,
                    additionalData: associatedData
                        ? new TextEncoder().encode(associatedData)
                        : new Uint8Array(0),
                    tagLength: 128,
                },
                this.key,
                ciphertextWithTag
            );

            return new TextDecoder().decode(decrypted);
        } catch (error) {
            // GCM falha em qualquer violação de integridade
            // Não detalhar a causa para evitar oracle attacks
            throw new Error('Decryption failed: integrity check failed');
        }
    }

    // Exportar chave
    async exportKey() {
        return window.crypto.subtle.exportKey('jwk', this.key);
    }

    // Importar chave
    static async importKey(jwk) {
        const key = await window.crypto.subtle.importKey(
            'jwk',
            jwk,
            { name: 'AES-GCM' },
            false,
            ['encrypt', 'decrypt']
        );
        return new SecureAESGCM(key);
    }
}

// Uso
async function demoSecureAES() {
    const key = await SecureAESGCM.generateKey(256);
    const cipher = new SecureAESGCM(key);

    const dados = JSON.stringify({
        transacao: "PIX-2024-001",
        valor: 1500.00,
        destino: "123456789-0",
    });

    const encrypted = await cipher.encrypt(dados, "transacao-id-001");
    console.log("Encrypted:", encrypted);

    const decrypted = await cipher.decrypt(encrypted, "transacao-id-001");
    console.log("Decrypted:", JSON.parse(decrypted));
}
```

### 9.5.2 RSA-OAEP em Detalhes

RSA-OAEP (Optimal Asymmetric Encryption Padding) é um esquema de criptografia assimétrica probabilístico. É recomendado para criptografia de pequenos volumes de dados (chaves simétricas, tokens).

**Parâmetros**:

| Parâmetro | Tamanho Recomendado | Notas |
|-----------|-------------------|-------|
| modulusLength | 2048 bits (mínimo) | 4096 bits para dados de alto valor |
| publicExponent | 65537 (0x010001) | Padrão da indústria |
| hash | SHA-256 ou SHA-384 | SHA-1 NÃO recomendado |

```javascript
// RSA-OAEP: Implementação completa com OAEP padding

class RSAOAEP {
    static async generateKeyPair(modulusLength = 2048, hash = 'SHA-256') {
        const keyPair = await window.crypto.subtle.generateKey(
            {
                name: 'RSA-OAEP',
                modulusLength,
                publicExponent: new Uint8Array([1, 0, 1]),
                hash,
            },
            true,
            ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
        );

        return keyPair;
    }

    // Criptografar com chave pública
    static async encrypt(publicKey, plaintext) {
        const encodedData = new TextEncoder().encode(plaintext);

        // RSA-OAEP pode criptografar no máximo:
        // key_size - 2 * hash_size - 2 bytes
        // Para 2048-bit key com SHA-256: 256 - 64 - 2 = 190 bytes
        const maxBytes = 190;  // Para RSA-2048 com SHA-256

        if (encodedData.length > maxBytes) {
            throw new Error(
                `Data too large for RSA-OAEP: ${encodedData.length} bytes (max: ${maxBytes})`
            );
        }

        const ciphertext = await window.crypto.subtle.encrypt(
            { name: 'RSA-OAEP' },
            publicKey,
            encodedData
        );

        return new Uint8Array(ciphertext);
    }

    // Descriptografar com chave privada
    static async decrypt(privateKey, ciphertext) {
        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'RSA-OAEP' },
            privateKey,
            ciphertext
        );

        return new TextDecoder().decode(decrypted);
    }

    // Assinar com RSA-PSS (mais seguro que PKCS#1 v1.5 para assinatura)
    static async sign(privateKey, data, saltLength = 32) {
        const encodedData = new TextEncoder().encode(data);

        const signature = await window.crypto.subtle.sign(
            { name: 'RSA-PSS', saltLength },
            privateKey,
            encodedData
        );

        return new Uint8Array(signature);
    }

    // Verificar assinatura
    static async verify(publicKey, signature, data, saltLength = 32) {
        const encodedData = new TextEncoder().encode(data);

        return window.crypto.subtle.verify(
            { name: 'RSA-PSS', saltLength },
            publicKey,
            signature,
            encodedData
        );
    }

    // Wrap/Unwrap de chaves simétricas
    static async wrapKey(wrappingKey, keyToWrap) {
        const wrapped = await window.crypto.subtle.wrapKey(
            'raw',
            keyToWrap,
            wrappingKey,
            { name: 'RSA-OAEP' }
        );

        return new Uint8Array(wrapped);
    }

    static async unwrapKey(unwrappingKey, wrappedKey, algorithm, extractable, keyUsages) {
        return window.crypto.subtle.unwrapKey(
            'raw',
            wrappedKey,
            unwrappingKey,
            { name: 'RSA-OAEP' },
            algorithm,
            extractable,
            keyUsages
        );
    }
}
```

### 9.5.3 ECDSA em Detalhes

ECDSA (Elliptic Curve Digital Signature Algorithm) oferece segurança equivalente a RSA com chaves muito menores:

| Curva | Tamanho Chave | Segurança Equivalente RSA |
|-------|--------------|-------------------------|
| P-256 | 256 bits | RSA-3072 |
| P-384 | 384 bits | RSA-7680 |
| P-521 | 521 bits | RSA-15360 |

```javascript
// ECDSA: Implementação completa

class ECDSASignature {
    // Curvas suportadas com seus tamanhos de assinatura
    static CURVES = {
        'P-256': { signatureLength: 64, keyUsages: ['sign', 'verify'] },
        'P-384': { signatureLength: 96, keyUsages: ['sign', 'verify'] },
        'P-521': { signatureLength: 132, keyUsages: ['sign', 'verify'] },
    };

    static async generateKeyPair(curve = 'P-256') {
        if (!ECDSASignature.CURVES[curve]) {
            throw new Error(`Unsupported curve: ${curve}`);
        }

        return window.crypto.subtle.generateKey(
            { name: 'ECDSA', namedCurve: curve },
            true,
            ECDSASignature.CURVES[curve].keyUsages
        );
    }

    // Assinar dados
    static async sign(privateKey, data, algorithm = { name: 'ECDSA', hash: 'SHA-256' }) {
        const encodedData = new TextEncoder().encode(data);

        const signature = await window.crypto.subtle.sign(
            algorithm,
            privateKey,
            encodedData
        );

        return {
            signature: new Uint8Array(signature),
            algorithm: algorithm,
            timestamp: Date.now(),
        };
    }

    // Verificar assinatura
    static async verify(publicKey, signedData) {
        const encodedData = new TextEncoder().encode(signedData.data);

        return window.crypto.subtle.verify(
            signedData.algorithm,
            publicKey,
            signedData.signature,
            encodedData
        );
    }

    // Assinar dados JSON
    static async signJSON(privateKey, jsonData) {
        // Canonicalizar JSON (ordenar chaves)
        const canonical = JSON.stringify(jsonData, Object.keys(jsonData).sort());
        return ECDSASignature.sign(privateKey, canonical);
    }

    // Verificar assinatura JSON
    static async verifyJSON(publicKey, jsonData, signedData) {
        const canonical = JSON.stringify(jsonData, Object.keys(jsonData).sort());
        return ECDSASignature.verify(publicKey, {
            ...signedData,
            data: canonical,
        });
    }
}

// Exemplo: Assinatura de documento
async function signDocument() {
    const keyPair = await ECDSASignature.generateKeyPair('P-256');

    const documento = {
        tipo: "contrato",
        partes: ["Alice Corp", "Bob Ltd"],
        valor: 50000,
        data: "2024-01-15",
    };

    // Assinar
    const signed = await ECDSASignature.signJSON(keyPair.privateKey, documento);
    console.log("Assinatura:", Array.from(signed.signature).map(b => b.toString(16).padStart(2, '0')).join(''));

    // Verificar
    const isValid = await ECDSASignature.verifyJSON(keyPair.publicKey, documento, signed);
    console.log("Válida:", isValid);  // true
}
```

### 9.5.4 ECDH em Detalhes

ECDH (Elliptic Curve Diffie-Hellman) permite que duas partes estabeleçam um segredo compartilhado sobre um canal inseguro.

```javascript
// ECDH: Troca de chaves Diffie-Hellman sobre curvas elípticas

class ECDHKeyExchange {
    static async generateKeyPair(curve = 'P-256') {
        return window.crypto.subtle.generateKey(
            { name: 'ECDH', namedCurve: curve },
            true,
            ['deriveKey', 'deriveBits']
        );
    }

    // Derivar segredo compartilhado
    static async deriveSharedSecret(privateKey, publicKey, algorithm = 'AES-GCM', keyLength = 256) {
        return window.crypto.subtle.deriveKey(
            {
                name: 'ECDH',
                public: publicKey,
            },
            privateKey,
            { name: algorithm, length: keyLength },
            false,
            ['encrypt', 'decrypt']
        );
    }

    // Derivar bits brutos (para KDF customizado)
    static async deriveBits(privateKey, publicKey, length = 256) {
        return window.crypto.subtle.deriveBits(
            {
                name: 'ECDH',
                public: publicKey,
            },
            privateKey,
            length
        );
    }

    // Protocolo completo: Troca segura entre Alice e Bob
    static async performKeyExchange() {
        // Alice gera suas chaves
        const aliceKeyPair = await ECDHKeyExchange.generateKeyPair('P-256');

        // Bob gera suas chaves
        const bobKeyPair = await ECDHKeyExchange.generateKeyPair('P-256');

        // Alice exporta chave pública para enviar a Bob
        const alicePublicKeyData = await window.crypto.subtle.exportKey(
            'raw',
            aliceKeyPair.publicKey
        );

        // Bob exporta chave pública para enviar a Alice
        const bobPublicKeyData = await window.crypto.subtle.exportKey(
            'raw',
            bobKeyPair.publicKey
        );

        // Alice importa chave pública de Bob e deriva segredo
        const bobPublicKeyImported = await window.crypto.subtle.importKey(
            'raw',
            bobPublicKeyData,
            { name: 'ECDH', namedCurve: 'P-256' },
            false,
            []
        );

        const sharedSecretAlice = await ECDHKeyExchange.deriveSharedSecret(
            aliceKeyPair.privateKey,
            bobPublicKeyImported
        );

        // Bob importa chave pública de Alice e deriva segredo
        const alicePublicKeyImported = await window.crypto.subtle.importKey(
            'raw',
            alicePublicKeyData,
            { name: 'ECDH', namedCurve: 'P-256' },
            false,
            []
        );

        const sharedSecretBob = await ECDHKeyExchange.deriveSharedSecret(
            bobKeyPair.privateKey,
            alicePublicKeyImported
        );

        // Ambos devem ter a mesma chave (verificação)
        const aliceKeyRaw = await window.crypto.subtle.exportKey('raw', sharedSecretAlice);
        const bobKeyRaw = await window.crypto.subtle.exportKey('raw', sharedSecretBob);

        const match = Array.from(new Uint8Array(aliceKeyRaw))
            .every((byte, i) => byte === new Uint8Array(bobKeyRaw)[i]);

        console.log('Chaves coincidem:', match);

        return { sharedSecretAlice, sharedSecretBob };
    }
}

// ECDH com Key Derivation Function (HKDF)
async function ecdhWithHKDF() {
    const alice = await ECDHKeyExchange.generateKeyPair();
    const bob = await ECDHKeyExchange.generateKeyPair();

    // Derivar bits brutos
    const rawSecret = await ECDHKeyExchange.deriveBits(
        alice.privateKey,
        bob.publicKey,
        256
    );

    // Importar HKDF key
    const hkdfKey = await window.crypto.subtle.importKey(
        'raw',
        rawSecret,
        { name: 'HKDF' },
        false,
        ['deriveKey']
    );

    // Derivar chave de encriptação via HKDF
    const encryptionKey = await window.crypto.subtle.deriveKey(
        {
            name: 'HKDF',
            hash: 'SHA-256',
            salt: window.crypto.getRandomValues(new Uint8Array(32)),
            info: new TextEncoder().encode('E2E-Encryption-Key'),
        },
        hkdfKey,
        { name: 'AES-GCM', length: 256 },
        false,
        ['encrypt', 'decrypt']
    );

    return encryptionKey;
}
```

---

## 9.6 Password Hashing in Web Apps: bcrypt/Argon2 Comparison

### 9.6.1 Por que Não Usar Hash Simples?

Hash functions como SHA-256 ou MD5 NÃO devem ser usadas para hashing de senhas porque são rápidas demais. Um atacante pode testar bilhões de senhas por segundo com GPUs modernas.

**Velocidade de hash (bcrypt, 10 rounds)**:

| Hardware | Senhas/segundo |
|----------|---------------|
| CPU Moderna | ~30.000 |
| GPU RTX 3080 | ~184.000 |
| GPU RTX 4090 | ~350.000 |
| Botnet 1000 GPUs | ~350.000.000 |

Com SHA-256 (sem salt), a mesma GPU pode testar bilhões por segundo.

### 9.6.2 bcrypt

O bcrypt é um adaptador do Blowfish com uma "cost factor" ajustável que aumenta exponencialmente o tempo de computação.

**Parâmetros**:

| Parâmetro | Descrição | Recomendação |
|-----------|-----------|-------------|
| cost | Número de rounds (2^cost) | 12-14 (2024+) |
| salt | Automatically generated (128 bits) | Gerenciado internamente |
| plaintext limit | 72 bytes | Truncar ou usar pré-hash |

```javascript
// bcrypt: Implementação no servidor (Node.js)
const bcrypt = require('bcrypt');

const BCRYPT_ROUNDS = 12;  // Recomendado para 2024

// Hash de senha
async function hashPassword(password) {
    // Validação de entrada
    if (!password || typeof password !== 'string') {
        throw new Error('Password must be a non-empty string');
    }

    if (password.length > 72) {
        // bcrypt truncata em 72 bytes — pré-hash para preservar entropia
        const preHashed = require('crypto')
            .createHash('sha256')
            .update(password)
            .digest('hex');
        return bcrypt.hash(preHashed, BCRYPT_ROUNDS);
    }

    return bcrypt.hash(password, BCRYPT_ROUNDS);
}

// Verificação de senha
async function verifyPassword(password, storedHash) {
    if (!password || !storedHash) {
        return false;
    }

    // Se a senha foi pré-hash (hash de 64 hex chars = 32 bytes SHA-256)
    if (storedHash.length === 60 && /^[0-9a-f]{60}$/.test(storedHash)) {
        // bcrypt hash
        return bcrypt.compare(password, storedHash);
    }

    // Se a senha original foi pré-hash
    const preHashed = require('crypto')
        .createHash('sha256')
        .update(password)
        .digest('hex');

    return bcrypt.compare(preHashed, storedHash);
}

// Formato do hash bcrypt: $2b$12$KfONfFhS1E4q0H5l3m6n7e.R4d4g5h6j7k8l9m0n1o2p3q4r5s6t
//     |    |  |                              |
//     |    |  |                              +-- 31 chars de salt + hash
//     |    |  +-- rounds (12)
//     |    +-- versão (b)
//     +-- identificador ($)
```

### 9.6.3 Argon2

O Argon2 é o vencedor do Password Hashing Competition (2015) e é atualmente o algoritmo recomendado para hashing de senhas. Existem três variantes:

| Variante | Uso Recomendado |
|----------|----------------|
| Argon2id | Híbrido (recomendado para maioria dos casos) |
| Argon2i | Resistente a side-channel attacks |
| Argon2d | Resistente a GPU cracking attacks |

**Parâmetros do Argon2**:

| Parâmetro | Descrição | Recomendação |
|-----------|-----------|-------------|
| type | id, i, ou d | id (recomendado) |
| memoryCost | Memória em KB | 65536-262144 (64-256 MB) |
| timeCost | Iterações | 3-5 |
| parallelism | Threads | 4 (ajustar ao hardware) |
| hashLength | Tamanho do hash | 32 bytes (256 bits) |
| saltLength | Tamanho do salt | 16 bytes (128 bits) |

```javascript
// Argon2: Implementação no servidor (Node.js)
const argon2 = require('argon2');

const ARGON2_OPTIONS = {
    type: argon2.argon2id,     // Variante híbrida
    memoryCost: 65536,         // 64 MB
    timeCost: 3,               // 3 iterações
    parallelism: 4,            // 4 threads
    hashLength: 32,            // 256 bits
    saltLength: 16,            // 128 bits
};

// Hash de senha
async function hashPasswordArgon2(password) {
    if (!password || typeof password !== 'string') {
        throw new Error('Password must be a non-empty string');
    }

    const hash = await argon2.hash(password, ARGON2_OPTIONS);

    // Formato do hash Argon2:
    // $argon2id$v=19$m=65536,t=3,p=4$c29tZXNhbHQ$RdescudvJCsgt3ub+b+dHRWwl3ZvNmS4L4S
    //     |       | |       |       |              |
    //     |       | |       |       |              +-- Hash (base64)
    //     |       | |       |       +-- Salt (base64)
    //     |       | |       +-- parallelism
    //     |       | +-- time cost
    //     |       +-- memory cost (KB)
    //     +-- variant (id, i, d)

    return hash;
}

// Verificação de senha
async function verifyPasswordArgon2(password, storedHash) {
    if (!password || !storedHash) {
        return false;
    }

    try {
        return await argon2.verify(storedHash, password);
    } catch (error) {
        // Erro de formato ou hash inválido
        return false;
    }
}

// Verificar se o hash precisa de rehash (parâmetros mudaram)
async function needsRehash(storedHash) {
    return argon2.needsRehash(storedHash, ARGON2_OPTIONS);
}

// Middleware de rehash automático (para quando os parâmetros mudam)
async function rehashMiddleware(req, res, next) {
    if (req.user && req.user.passwordHash) {
        if (await needsRehash(req.user.passwordHash)) {
            // Rehash com novos parâmetros
            // Nota: req.user.password já deve estar disponível
            // (via sessão ou outro mecanismo)
            const newHash = await hashPasswordArgon2(req.user.password);
            await updateUserPasswordHash(req.user.id, newHash);
        }
    }
    next();
}
```

### 9.6.4 Comparação bcrypt vs Argon2

```javascript
// Benchmark comparativo: bcrypt vs Argon2

const { PerformanceObserver, performance } = require('perf_hooks');
const bcrypt = require('bcrypt');
const argon2 = require('argon2');

async function benchmark() {
    const password = 'MyS3cur3P@ssw0rd!';
    const iterations = 100;

    console.log('=== Benchmark: Hash Generation ===\n');

    // bcrypt com diferentes cost factors
    for (const cost of [10, 12, 14]) {
        const start = performance.now();
        for (let i = 0; i < iterations; i++) {
            await bcrypt.hash(password, cost);
        }
        const elapsed = performance.now() - start;
        console.log(`bcrypt (cost=${cost}): ${(elapsed / iterations).toFixed(2)} ms/hash`);
    }

    console.log('');

    // Argon2 com diferentes configurações
    const argonConfigs = [
        { type: argon2.argon2id, memoryCost: 65536, timeCost: 3, parallelism: 4 },
        { type: argon2.argon2id, memoryCost: 131072, timeCost: 4, parallelism: 4 },
        { type: argon2.argon2id, memoryCost: 262144, timeCost: 5, parallelism: 4 },
    ];

    for (const config of argonConfigs) {
        const start = performance.now();
        for (let i = 0; i < iterations; i++) {
            await argon2.hash(password, config);
        }
        const elapsed = performance.now() - start;
        console.log(
            `Argon2id (m=${config.memoryCost}, t=${config.timeCost}): ` +
            `${(elapsed / iterations).toFixed(2)} ms/hash`
        );
    }

    console.log('\n=== Benchmark: Verification ===\n');

    // bcrypt verify
    const bcryptHash = await bcrypt.hash(password, 12);
    const bcryptStart = performance.now();
    for (let i = 0; i < iterations; i++) {
        await bcrypt.compare(password, bcryptHash);
    }
    const bcryptElapsed = performance.now() - bcryptStart;
    console.log(`bcrypt verify: ${(bcryptElapsed / iterations).toFixed(2)} ms/op`);

    // Argon2 verify
    const argonHash = await argon2.hash(password, argonConfigs[0]);
    const argonStart = performance.now();
    for (let i = 0; i < iterations; i++) {
        await argon2.verify(argonHash, password);
    }
    const argonElapsed = performance.now() - argonStart;
    console.log(`Argon2 verify: ${(argonElapsed / iterations).toFixed(2)} ms/op`);
}

// Resultados típicos (RTX 3080):
// bcrypt (cost=10): 105.23 ms/hash
// bcrypt (cost=12): 420.87 ms/hash
// bcrypt (cost=14): 1683.45 ms/hash
// Argon2id (m=65536, t=3): 312.54 ms/hash
// Argon2id (m=131072, t=4): 625.08 ms/hash
// Argon2id (m=262144, t=5): 1250.16 ms/hash
```

### 9.6.5 Implementação de Proteção contra Timing Attacks

```javascript
// Comparação segura contra timing attacks

const crypto = require('crypto');

// Função de comparação em tempo constante
function timingSafeEqual(a, b) {
    if (typeof a !== 'string' || typeof b !== 'string') {
        return false;
    }

    if (a.length !== b.length) {
        // Ainda executar comparação para não vazar informação de tamanho
        crypto.timingSafeEqual(
            Buffer.from(a.padEnd(64, '\0')),
            Buffer.from(b.padEnd(64, '\0'))
        );
        return false;
    }

    return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

// Sistema completo de autenticação resistente a timing attacks
class SecureAuth {
    constructor() {
        this.BCRYPT_ROUNDS = 12;
        this.MAX_LOGIN_ATTEMPTS = 5;
        this.LOCKOUT_DURATION = 15 * 60 * 1000;  // 15 minutos
        this.attempts = new Map();  // userId -> { count, lockoutUntil }
    }

    async hashPassword(password) {
        return bcrypt.hash(password, this.BCRYPT_ROUNDS);
    }

    async verifyPassword(password, storedHash) {
        return bcrypt.compare(password, storedHash);
    }

    // Verificar tentativas de login
    checkRateLimit(userId) {
        const record = this.attempts.get(userId);
        if (!record) return { allowed: true, attempts: 0 };

        if (record.lockoutUntil > Date.now()) {
            const remainingMs = record.lockoutUntil - Date.now();
            return {
                allowed: false,
                attempts: record.count,
                retryAfter: Math.ceil(remainingMs / 1000),
            };
        }

        return { allowed: true, attempts: record.count };
    }

    recordFailedAttempt(userId) {
        const record = this.attempts.get(userId) || { count: 0 };
        record.count++;

        if (record.count >= this.MAX_LOGIN_ATTEMPTS) {
            record.lockoutUntil = Date.now() + this.LOCKOUT_DURATION;
        }

        this.attempts.set(userId, record);
    }

    clearAttempts(userId) {
        this.attempts.delete(userId);
    }

    // Login completo com proteções
    async login(userId, password) {
        // Verificar rate limit
        const rateLimit = this.checkRateLimit(userId);
        if (!rateLimit.allowed) {
            // Mensagem genérica — não revelar se o usuário existe
            return {
                success: false,
                error: 'Account temporarily locked. Please try again later.',
                retryAfter: rateLimit.retryAfter,
            };
        }

        // Buscar hash do usuário
        const storedHash = await this.getPasswordHash(userId);
        if (!storedHash) {
            // Executar hash mesmo com hash inexistente para evitar timing leak
            await bcrypt.hash(password, this.BCRYPT_ROUNDS);
            return {
                success: false,
                error: 'Invalid credentials.',
            };
        }

        // Verificar senha
        const isValid = await this.verifyPassword(password, storedHash);

        if (!isValid) {
            this.recordFailedAttempt(userId);
            return {
                success: false,
                error: 'Invalid credentials.',
            };
        }

        // Login bem-sucedido
        this.clearAttempts(userId);

        // Verificar se precisa de rehash
        if (await bcrypt.compare(password, storedHash)) {
            // Verificar se o hash precisa de rehash (custo do bcrypt mudou)
            const currentCost = parseInt(storedHash.split('$')[2]);
            if (currentCost < this.BCRYPT_ROUNDS) {
                const newHash = await this.hashPassword(password);
                await this.updatePasswordHash(userId, newHash);
            }
        }

        return {
            success: true,
            userId: userId,
        };
    }

    // Métodos stub (implementar conforme ORM/banco de dados)
    async getPasswordHash(userId) { /* ... */ }
    async updatePasswordHash(userId, hash) { /* ... */ }
}
```

---

## 9.7 Secure Random Number Generation in Browsers

### 9.7.1 A Importância de RNG Criptograficamente Seguro

Números aleatórios são a base de toda criptografia. Um RNG (Random Number Generator) com falhas compromete todo o sistema.

**Fontes de aleatoriedade no navegador**:

| API | Entropia | Recomendação |
|-----|----------|-------------|
| `crypto.getRandomValues()` | Alta (hardware RNG) | SEMPRE usar para criptografia |
| `Math.random()` | Baixa (PRNG) | NUNCA usar para criptografia |
| `crypto.randomUUID()` | Alta | Usar para UUIDs v4 |

### 9.7.2 Implementação de RNG Seguro

```javascript
// RNG criptograficamente seguro para navegador

class SecureRandom {
    // Gerar bytes aleatórios
    static getBytes(length) {
        return window.crypto.getRandomValues(new Uint8Array(length));
    }

    // Gerar inteiro aleatório em intervalo [min, max]
    // Distribuição uniforme (sem bias)
    static getRange(min, max) {
        const range = max - min + 1;
        const bits = Math.ceil(Math.log2(range));
        const bytesNeeded = Math.ceil(bits / 8);
        const mask = (1 << bits) - 1;

        let randomValue;
        do {
            const randomBytes = window.crypto.getRandomValues(new Uint8Array(bytesNeeded));
            randomValue = 0;
            for (let i = 0; i < bytesNeeded; i++) {
                randomValue = (randomValue << 8) | randomBytes[i];
            }
            randomValue &= mask;
        } while (randomValue >= range);  // Rejection sampling para eliminação de bias

        return min + randomValue;
    }

    // Gerar string aleatória de caracteres específicos
    static getString(length, charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789') {
        let result = '';
        const charsetLength = charset.length;

        // Rejection sampling para distribuição uniforme
        const bitsPerChar = Math.ceil(Math.log2(charsetLength));
        const maxValid = Math.floor(256 / charsetLength) * charsetLength;

        while (result.length < length) {
            const randomByte = window.crypto.getRandomValues(new Uint8Array(1))[0];
            if (randomByte < maxValid) {
                result += charset[randomByte % charsetLength];
            }
        }

        return result;
    }

    // Gerar token URL-safe (base64url)
    static getToken(lengthInBytes = 32) {
        const bytes = this.getBytes(lengthInBytes);
        return this.arrayBufferToBase64Url(bytes);
    }

    // Gerar senha segura
    static generatePassword(length = 16) {
        const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const lowercase = 'abcdefghijklmnopqrstuvwxyz';
        const digits = '0123456789';
        const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?';

        const allChars = uppercase + lowercase + digits + symbols;

        // Garantir pelo menos um de cada tipo
        let password = '';
        password += uppercase[this.getRange(0, uppercase.length - 1)];
        password += lowercase[this.getRange(0, lowercase.length - 1)];
        password += digits[this.getRange(0, digits.length - 1)];
        password += symbols[this.getRange(0, symbols.length - 1)];

        // Preencher o resto
        for (let i = password.length; i < length; i++) {
            password += allChars[this.getRange(0, allChars.length - 1)];
        }

        // Embaralhar (Fisher-Yates com RNG seguro)
        const array = password.split('');
        for (let i = array.length - 1; i > 0; i--) {
            const j = this.getRange(0, i);
            [array[i], array[j]] = [array[j], array[i]];
        }

        return array.join('');
    }

    // Gerar TOTP secret (para autenticação 2FA)
    static generateTOTPSecret(length = 20) {
        const bytes = this.getBytes(length);
        return this.arrayBufferToBase32(bytes);
    }

    // Utilitários
    static arrayBufferToBase64Url(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary)
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=+$/, '');
    }

    static arrayBufferToBase32(buffer) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
        const bytes = new Uint8Array(buffer);
        let bits = '';
        for (const byte of bytes) {
            bits += byte.toString(2).padStart(8, '0');
        }
        let result = '';
        for (let i = 0; i < bits.length; i += 5) {
            const chunk = bits.substr(i, 5).padEnd(5, '0');
            result += chars[parseInt(chunk, 2)];
        }
        return result;
    }
}

// Exemplo de uso
function demoSecureRandom() {
    console.log('Bytes aleatórios:', Array.from(SecureRandom.getBytes(16)));
    console.log('Número aleatório [1, 100]:', SecureRandom.getRange(1, 100));
    console.log('String aleatória:', SecureRandom.getString(32));
    console.log('Token URL-safe:', SecureRandom.getToken(32));
    console.log('Senha segura:', SecureRandom.generatePassword(20));
    console.log('TOTP Secret:', SecureRandom.generateTOTPSecret());
    console.log('UUID v4:', crypto.randomUUID());
}
```

### 9.7.3 Geração de Números Aleatórios no Servidor (Node.js)

```javascript
// Node.js: RNG criptograficamente seguro

const crypto = require('crypto');

// 1. crypto.randomBytes
function getRandomBytes(length) {
    return new Promise((resolve, reject) => {
        crypto.randomBytes(length, (err, buffer) => {
            if (err) reject(err);
            else resolve(buffer);
        });
    });
}

// 2. crypto.randomInt (Node.js 14.10+)
function getRandomInt(min, max) {
    return crypto.randomInt(min, max + 1);
}

// 3. crypto.randomUUID (Node.js 14.17+)
function getUUID() {
    return crypto.randomUUID();
}

// 4. crypto.generateKeyPairSync para chaves
function generateRSAKeyPair() {
    return crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: { type: 'spki', format: 'pem' },
        privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    });
}

// 5. crypto.createCipheriv para criptografia simétrica
function encryptAES256GCM(key, plaintext, aad) {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

    if (aad) cipher.setAAD(aad);

    let encrypted = cipher.update(plaintext, 'utf8');
    encrypted = Buffer.concat([encrypted, cipher.final()]);

    const tag = cipher.getAuthTag();

    return { iv, encrypted, tag };
}

// 6. Estimativa de entropia (para debug)
function estimateEntropy(bytes) {
    // Shannon entropy para verificar uniformidade
    const freq = new Array(256).fill(0);
    for (const byte of bytes) {
        freq[byte]++;
    }

    let entropy = 0;
    const len = bytes.length;
    for (const f of freq) {
        if (f > 0) {
            const p = f / len;
            entropy -= p * Math.log2(p);
        }
    }

    return entropy;  // Deve ser próximo de 8 para bytes uniformes
}

// Teste de entropia
async function testEntropy() {
    const bytes = await getRandomBytes(10000);
    const entropy = estimateEntropy(bytes);
    console.log(`Entropia: ${entropy.toFixed(4)} bits/byte (ideal: 8.0000)`);
}
```

---

## 9.8 Certificate Transparency

### 9.8.1 O Problema da Confiança Cega em CAs

O sistema tradicional de certificados TLS confia em centenas de Autoridades Certificadoras (CAs). Qualquer uma delas pode emitir um certificado para qualquer domínio, e os navegadores aceitarão. Isso criou ataques como o da DigiNotar (2011), onde um certificado fraudulento para *.google.com foi emitido.

**Certificate Transparency (CT)** é um sistema de log público que registra todos os certificados emitidos, tornando impossível emitir certificados sem ser detectado.

### 9.8.2 Arquitetura do CT

```
Emissor do Certificado           CT Log Server           Monitor
    |                                |                      |
    | 1. Submeter certificado       |                      |
    |    (SCT - Signed Certificate  |                      |
    |     Timestamp)                |                      |
    |------------------------------->|                      |
    |                                |                      |
    | 2. Resposta: SCT              |                      |
    |<-------------------------------|                      |
    |                                |                      |
    | 3. Incluir SCT no certificado |                      |
    |    (via TLS extension ou       |                      |
    |     OCSP extension)           |                      |
    |                                |                      |
    |                                | 4. Log público      |
    |                                |    (append-only)    |
    |                                |<---------------------|
    |                                |                      |
    |                                | 5. Verificar se      |
    |                                |    certificado       |
    |                                |    esperado está     |
    |                                |    no log            |
```

### 9.8.3 Verificação de CT no Navegador

```javascript
// Verificar SCTs em um certificado via TLS

// No navegador: via JavaScript (limitado)
// CT verification é feita pelo próprio navegador na maioria dos casos

// Exemplo de verificação manual via OpenSSL
// openssl s_client -connect example.com:443 -ct </dev/null 2>/dev/null | \
//     grep -A 2 "SCT"

// Verificação de CT via API pública (Google CT)
async function verifyCertificateTransparency(domain) {
    try {
        const response = await fetch(
            `https://crt.sh/?q=${domain}&output=json`
        );

        const certificates = await response.json();

        // Filtrar certificados válidos
        const validCerts = certificates.filter(cert =>
            new Date(cert.not_after) > new Date() &&
            new Date(cert.not_before) < new Date()
        );

        console.log(`Certificados CT encontrados para ${domain}:`, validCerts.length);

        for (const cert of validCerts.slice(0, 5)) {
            console.log(`  - ID: ${cert.id}`);
            console.log(`    Emitido: ${cert.not_before}`);
            console.log(`    Expira: ${cert.not_after}`);
            console.log(`    CA: ${cert.issuer_name}`);
        }

        return validCerts;
    } catch (error) {
        console.error('Erro ao verificar CT:', error);
        return [];
    }
}

// Verificação de SCTs via API do Google
async function checkGoogleSCT(domain) {
    try {
        const response = await fetch(
            `https://crt.sh/?q=${domain}&output=json`
        );

        const certs = await response.json();
        const scts = certs.flatMap(cert => cert.sct_list || []);

        return {
            domain,
            totalCerts: certs.length,
            sctCount: scts.length,
            hasValidSCT: scts.some(sct =>
                new Date(sct.timestamp) > new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
            ),
        };
    } catch (error) {
        return { domain, error: error.message };
    }
}
```

### 9.8.4 Google CT Policy

O Google Chrome exige que certificados tenham SCTs de pelo menos dois logs CT diferentes. A política é:

1. **Domínios públicos**: Mínimo de 2 SCTs de logs CT diferentes
2. **Domínios privados (internal names)**: Mínimo de 2 SCTs
3. **Certificados com validity > 180 dias**: Mínimo de 3 SCTs

```bash
# Verificar CT policy compliance
# Usando certlint ou certspotter

# Instalar certspotter
pip install certspotter

# Verificar um domínio
certspotter check example.com

# Output esperado:
# Domain: example.com
# CT Logs found: 3
# SCTs embedded: 3
# Status: COMPLIANT
```

---

## 9.9 DANE and DNSSEC for TLS

### 9.9.1 DNSSEC: Segurança no DNS

O DNSSEC (DNS Security Extensions) adiciona autenticação e integridade às respostas DNS, prevenindo ataques de spoofing e cache poisoning.

**Hierarquia de assinaturas DNSSEC**:

```
Root Zone (.)
    |
    |--- .com (DS record)
    |       |
    |       |--- example.com (DS record)
    |               |
    |               |--- www.example.com (A record + RRSIG)
    |               |--- mail.example.com (A record + RRSIG)
    |
    |--- .org (DS record)
            |
            |--- ...
```

**Registros DNSSEC**:

| Registro | Função |
|----------|--------|
| `DNSKEY` | Chave pública para verificar assinaturas |
| `DS` | Delegation Signer — hash da chave do filho |
| `RRSIG` | Assinatura de um conjunto de registros |
| `NSEC` | Prova de inexistência (NXDOMAIN) |
| `NSEC3` | Versão hasheada do NSEC (proteção contra zone walking) |

### 9.9.2 DANE (DNS-based Authentication of Named Entities)

DANE (RFC 6698) usa registros TLSA no DNS para associar certificados TLS a domínios, eliminando a dependência de centenas de CAs.

**Registro TLSA**:

```
_443._tcp.example.com. IN TLSA (
    3       -- Certificate Usage
    1       -- Selector
    1       -- Matching Type
    SHA256_hash_do_certificado
)

Certificate Usage:
  0 = PKIX-TA (CA constraint)
  1 = PKIX-EE (EE constraint)
  2 = DANE-TA (Trust Anchor)
  3 = DANE-EE (End Entity) -- MAIS USADO

Selector:
  0 = Full certificate
  1 = SubjectPublicKeyInfo (recomendado)

Matching Type:
  0 = Exact match
  1 = SHA-256 hash (recomendado)
  2 = SHA-512 hash
```

### 9.9.3 Configuração de DNSSEC com Bind9

```bash
# Instalação do Bind9 com DNSSEC
sudo apt install bind9 bind9utils dnsutils

# Gerar chave ZSK (Zone Signing Key)
dnssec-keygen -a ECDSAP256SHA256 -n ZONE example.com

# Gerar chave KSK (Key Signing Key)
dnssec-keygen -a ECDSAP256SHA256 -n ZONE -f KSK example.com

# Arquivo de zona com DNSSEC
cat > /etc/bind/zones/db.example.com << 'EOF'
$TTL 3600
@   IN  SOA ns1.example.com. admin.example.com. (
        2024011501  ; Serial
        3600        ; Refresh
        900         ; Retry
        604800      ; Expire
        86400       ; Minimum TTL
    )

    IN  NS  ns1.example.com.
    IN  NS  ns2.example.com.

    ; DS record (do pai)
    IN  DS  12345 13 2 ABCDEF1234567890...

ns1 IN  A   10.0.0.1
ns2 IN  A   10.0.0.2

www IN  A   10.0.0.10
www IN  TLSA 3 1 1 <SHA256_hash_do_certificado>

mail IN  A   10.0.0.20
mail IN  TLSA 3 1 1 <SHA256_hash_do_certificado>
EOF

# Assinar a zona
dnssec-signzone -A -3 $(head -c 1000 /dev/urandom | sha1sum | cut -b 1-16) \
    -N INCREMENT \
    -o example.com \
    -t /etc/bind/zones/db.example.com

# Verificar assinatura
dnssec-verify -D /etc/bind/zones/ /etc/bind/zones/db.example.com.signed
```

### 9.9.4 Verificação de DANE

```javascript
// Verificação DANE via DNS over HTTPS (DoH)

async function verifyDANE(domain, port = 443) {
    const dohEndpoint = 'https://dns.google/resolve';

    try {
        const tlsaRecord = `${port}._tcp.${domain}`;
        const response = await fetch(
            `${dohEndpoint}?name=${tlsaRecord}&type=TLSA`
        );

        const data = await response.json();

        if (data.Answer) {
            const tlsa = data.Answer.find(r => r.type === 52);  // TLSA = type 52
            if (tlsa) {
                const parts = tlsa.data.split(' ');
                return {
                    domain,
                    port,
                    certificateUsage: parseInt(parts[0]),
                    selector: parseInt(parts[1]),
                    matchingType: parseInt(parts[2]),
                    certData: parts[3],
                    hasDANE: true,
                };
            }
        }

        return { domain, hasDANE: false };
    } catch (error) {
        return { domain, hasDANE: false, error: error.message };
    }
}

// Verificar se o certificado do servidor corresponde ao registro DANE
async function verifyDANECompliance(domain) {
    const dane = await verifyDANE(domain);
    if (!dane.hasDANE) {
        return { domain, compliant: false, reason: 'No TLSA record' };
    }

    // Em produção: buscar certificado do servidor e comparar com TLSA
    // const serverCert = await getServerCertificate(domain, dane.port);
    // const match = compareCertificateWithTLSA(serverCert, dane);

    return {
        domain,
        compliant: true,  // Simplificado para exemplo
        dane: dane,
    };
}
```

---

## 9.10 Forward Secrecy in Web Servers

### 9.10.1 O Que é Forward Secrecy?

Forward Secrecy (ou Perfect Forward Secrecy — PFS) garante que, mesmo que a chave privada do servidor seja comprometida no futuro, as sessões anteriores continuem seguras. Cada sessão usa uma chave efêmera única.

**Sem Forward Secrecy**:

```
Sessão 1: [Mensagem1] ---> Criptografada com chave_estatica
Sessão 2: [Mensagem2] ---> Criptografada com chave_estatica
...
Se a chave_estatica for comprometida, TODAS as sessões são expostas.
```

**Com Forward Secrecy (ECDHE)**:

```
Sessão 1: [Mensagem1] ---> Criptografada com chave_efemera_1
Sessão 2: [Mensagem2] ---> Criptografada com chave_efemera_2
...
Se a chave_estatica for comprometida, apenas o handshake é exposto.
As sessões anteriores permanecem seguras.
```

### 9.10.2 Configuração de Forward Secrecy em Nginx

```nginx
# Configuração TLS com Forward Secrecy no Nginx

server {
    listen 443 ssl http2;
    server_name example.com;

    # Certificado
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Protocolos — apenas TLS 1.2 e 1.3
    ssl_protocols TLSv1.2 TLSv1.3;

    # Cipher suites com ECDHE para forward secrecy
    # TLS 1.3 (configurado via ssl_conf_command ou automático)
    ssl_conf_command Ciphersuites TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256;

    # TLS 1.2 cipher suites
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;

    # Não forçar preferência de cipher (TLS 1.3 não suporta)
    ssl_prefer_server_ciphers off;

    # DH parameters para DHE (fallback)
    ssl_dhparam /etc/nginx/ssl/dhparam.pem;

    # ECDH curve
    ssl_ecdh_curve X25519:P-256:P-384;

    # Session tickets (se usando, precisa de renovação regular)
    ssl_session_tickets on;
    ssl_session_ticket_key /etc/nginx/ssl/current.key;
    ssl_session_ticket_key /etc/nginx/ssl/previous.key;

    # Session cache
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/example.com/chain.pem;
    resolver 8.8.8.8 1.1.1.1 valid=300s;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
}

# Redirect HTTP -> HTTPS
server {
    listen 80;
    server_name example.com www.example.com;
    return 301 https://$host$request_uri;
}
```

### 9.10.3 Geração de Parâmetros DH e ECDH

```bash
# Gerar parâmetros DH (2048+ bits)
openssl dhparam -out /etc/nginx/ssl/dhparam.pem 4096

# Gerar curve ECDH (X25519 é recomendado)
openssl ecparam -genkey -name X25519 -out /etc/nginx/ssl/x25519.pem

# Verificar configuração TLS
openssl s_client -connect example.com:443 -servername example.com </dev/null 2>/dev/null | \
    grep -E "(Protocol|Cipher|Server public key)"

# Output esperado com forward secrecy:
# Protocol  : TLSv1.3
# Cipher    : TLS_AES_256_GCM_SHA384
# Server public key: 256 bit (ECDSA)
```

### 9.10.4 Verificação de Forward Secrecy

```javascript
// Verificar forward secrecy de um servidor

async function checkForwardSecrecy(domain) {
    try {
        // Usar API de testes TLS (exemplo com SSL Labs API)
        const response = await fetch(
            `https://api.ssllabs.com/api/v3/analyze?host=${domain}&startNew=on&all=done`
        );

        const data = await response.json();
        const endpoints = data.endpoints || [];

        const results = endpoints.map(endpoint => ({
            ip: endpoint.ipAddress,
            grade: endpoint.grade,
            forwardSecrecy: endpoint.forwardSecrecy,
            protocols: endpoint.protocols?.map(p => `${p.name} ${p.version}`),
            cipherSuites: endpoint.details?.cipherSuites?.filter(c =>
                c.name?.includes('ECDHE') || c.name?.includes('DHE')
            ).map(c => c.name),
        }));

        return {
            domain,
            hasForwardSecrecy: results.every(r => r.forwardSecrecy),
            details: results,
        };
    } catch (error) {
        return { domain, error: error.message };
    }
}

// Verificação rápida via OpenSSL
async function quickFSCheck(domain) {
    const { execSync } = require('child_process');

    try {
        const output = execSync(
            `echo | openssl s_client -connect ${domain}:443 -servername ${domain} 2>/dev/null | grep "Server public key"`,
            { encoding: 'utf-8' }
        );

        const hasECDHE = output.includes('EC') || output.includes('X25519');
        const hasDHE = !hasECDHE;  // Simplificado

        return {
            domain,
            forwardSecrecy: hasECDHE || hasDHE,
            keyType: hasECDHE ? 'EC' : hasDHE ? 'DH' : 'RSA',
        };
    } catch (error) {
        return { domain, error: error.message };
    }
}
```

---

## 9.11 TLS Termination at Load Balancers

### 9.11.1 Arquiteturas de TLS Termination

Existem três padrões principais para TLS em ambientes com load balancers:

**Padrão 1: TLS Termination no Load Balancer**

```
Cliente ----[HTTPS]----> Load Balancer ----[HTTP]----> Backend Server
                              |
                         TLS Decrypt
                         (termina TLS aqui)
```

**Padrão 2: TLS Passthrough**

```
Cliente ----[HTTPS]----> Load Balancer ----[HTTPS]----> Backend Server
                              |
                         Sem decrypt
                         (apenas roteamento)
```

**Padrão 3: TLS Re-encrypt (Double TLS)**

```
Cliente ----[HTTPS]----> Load Balancer ----[HTTPS]----> Backend Server
                              |                              |
                         TLS Decrypt                   TLS Decrypt
                         TLS Re-encrypt
```

### 9.11.2 TLS Termination com Nginx como Load Balancer

```nginx
# Nginx como load balancer com TLS termination

upstream backend_servers {
    least_conn;
    server 10.0.0.10:8080 weight=3;
    server 10.0.0.11:8080 weight=2;
    server 10.0.0.12:8080 weight=1 backup;

    # Health checks (comercial)
    # health_check interval=10 fails=3 passes=2;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # TLS Configuration
    ssl_certificate /etc/ssl/certs/api.example.com.pem;
    ssl_certificate_key /etc/ssl/private/api.example.com.key;

    # TLS 1.3 + 1.2 com forward secrecy
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/ssl/certs/ca-chain.pem;
    resolver 8.8.8.8 1.1.1.1 valid=300s;

    # Session tickets com renovação automática
    ssl_session_tickets on;

    # Proxy para backends
    location / {
        proxy_pass http://backend_servers;

        # Headers de proxy
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # WebSocket
    location /ws {
        proxy_pass http://backend_servers;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 9.11.3 TLS Re-encrypt com mTLS

```nginx
# TLS Re-encrypt: Load Balancer decripta e re-cripta para backends

# Backend servers com mTLS
upstream backend_mtls {
    server 10.0.0.10:8443;
    server 10.0.0.11:8443;
}

server {
    listen 443 ssl http2;
    server_name internal.example.com;

    # Certificado público
    ssl_certificate /etc/ssl/certs/internal.example.com.pem;
    ssl_certificate_key /etc/ssl/private/internal.example.com.key;

    # TLS padrão
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass https://backend_mtls;

        # mTLS com backends
        proxy_ssl_certificate /etc/ssl/certs/backend-client.pem;
        proxy_ssl_certificate_key /etc/ssl/private/backend-client.key;
        proxy_ssl_trusted_certificate /etc/ssl/certs/backend-ca.pem;
        proxy_ssl_verify on;
        proxy_ssl_verify_depth 2;
        proxy_ssl_server_name on;
        proxy_ssl_name backend.internal.example.com;

        # TLS 1.3 para backends
        proxy_ssl_protocols TLSv1.3;
        proxy_ssl_ciphers TLS_AES_256_GCM_SHA384;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 9.11.4 HAProxy com TLS Termination

```haproxy
# HAProxy: TLS Termination completa

global
    ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384
    ssl-default-bind-ciphersuites TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:TLS_AES_128_GCM_SHA256
    ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets
    tune.ssl.default-dh-param 2048

frontend https_front
    bind *:443 ssl crt /etc/ssl/certs/example.pem alpn h2,http/1.1
    mode http

    # OCSP Stapling
    ssl-stapling on
    ssl-stapling-verify on

    # HSTS
    http-response set-header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"

    # Redirect HTTP -> HTTPS
    http-request redirect scheme https unless { ssl_fc }

    # ACLs
    acl is_api path_beg /api/
    acl is_websocket hdr(Upgrade) -i websocket

    # Routing
    use_backend api_servers if is_api
    use_backend ws_servers if is_websocket
    default_backend web_servers

backend web_servers
    balance roundrobin
    option httpchk GET /health HTTP/1.1\r\nHost:\ example.com
    http-check expect status 200

    server web1 10.0.0.10:8080 check inter 5s fall 3 rise 2
    server web2 10.0.0.11:8080 check inter 5s fall 3 rise 2

backend api_servers
    balance leastconn
    option httpchk GET /api/health HTTP/1.1\r\nHost:\ api.example.com

    server api1 10.0.0.20:3000 check inter 5s
    server api2 10.0.0.21:3000 check inter 5s

backend ws_servers
    balance source
    option httpchk GET /ws/health HTTP/1.1\r\nHost:\ example.com
    timeout server 3600s
    timeout tunnel 3600s

    server ws1 10.0.0.30:8080 check inter 5s
    server ws2 10.0.0.31:8080 check inter 5s

# Redirect HTTP para HTTPS
frontend http_front
    bind *:80
    http-request redirect scheme https
```

---

## 9.12 Content Encryption in Cloud Storage

### 9.12.1 Criptografia de Conteúdo em S3

```javascript
// AWS S3: Client-side encryption com AES-GCM

const { S3Client, PutObjectCommand, GetObjectCommand } = require('@aws-sdk/client-s3');
const { KMSClient, GenerateDataKeyCommand, DecryptCommand } = require('@aws-sdk/client-kms');

class S3ContentEncryption {
    constructor(bucketName, region = 'us-east-1') {
        this.bucket = bucketName;
        this.s3 = new S3Client({ region });
        this.kms = new KMSClient({ region });
    }

    // Upload com criptografia client-side
    async uploadEncrypted(key, data, metadata = {}) {
        // Gerar data key via KMS
        const dataKeyResponse = await this.kms.send(new GenerateDataKeyCommand({
            KeyId: 'alias/my-key',
            KeySpec: 'AES_256',
        }));

        const plaintextKey = dataKeyResponse.Plaintext;
        const encryptedKey = dataKeyResponse.CiphertextBlob;

        // Criptografar dados com AES-256-GCM
        const crypto = require('crypto');
        const iv = crypto.randomBytes(12);
        const cipher = crypto.createCipheriv('aes-256-gcm', plaintextKey, iv);

        const encryptedData = Buffer.concat([
            cipher.update(typeof data === 'string' ? Buffer.from(data) : data),
            cipher.final(),
        ]);

        const authTag = cipher.getAuthTag();

        // Upload para S3 com metadados de criptografia
        await this.s3.send(new PutObjectCommand({
            Bucket: this.bucket,
            Key: key,
            Body: encryptedData,
            // Armazenar IV, authTag e encrypted key como metadados
            Metadata: {
                'x-amz-encryption-iv': iv.toString('base64'),
                'x-amz-encryption-tag': authTag.toString('base64'),
                'x-amz-encryption-key': encryptedKey.toString('base64'),
                ...metadata,
            },
            // Server-side encryption adicional
            ServerSideEncryption: 'aws:kms',
            SSEKMSKeyId: 'alias/my-key',
        }));

        return {
            key,
            encryptedKeySize: encryptedData.length,
            dataKeyId: dataKeyResponse.KeyId,
        };
    }

    // Download com descriptografia client-side
    async downloadEncrypted(key) {
        const response = await this.s3.send(new GetObjectCommand({
            Bucket: this.bucket,
            Key: key,
        }));

        const body = await response.Body.transformToByteArray();
        const metadata = response.Metadata;

        // Recuperar data key do KMS
        const encryptedKey = Buffer.from(metadata['x-amz-encryption-key'], 'base64');
        const decryptResponse = await this.kms.send(new DecryptCommand({
            CiphertextBlob: encryptedKey,
        }));

        const plaintextKey = decryptResponse.Plaintext;

        // Descriptografar dados
        const crypto = require('crypto');
        const iv = Buffer.from(metadata['x-amz-encryption-iv'], 'base64');
        const authTag = Buffer.from(metadata['x-amz-encryption-tag'], 'base64');

        const decipher = crypto.createDecipheriv('aes-256-gcm', plaintextKey, iv);
        decipher.setAuthTag(authTag);

        const decrypted = Buffer.concat([
            decipher.update(body),
            decipher.final(),
        ]);

        return decrypted.toString('utf-8');
    }
}

// Exemplo de uso
async function demoS3Encryption() {
    const s3enc = new S3ContentEncryption('my-secure-bucket', 'us-east-1');

    // Upload
    const dadosSensiveis = JSON.stringify({
        documento: "Contrato Confidencial",
        valor: 1000000,
        partes: ["Empresa A", "Empresa B"],
    });

    const uploadResult = await s3enc.uploadEncrypted(
        'contracts/2024/001.json',
        dadosSensiveis,
        { 'content-type': 'application/json' }
    );

    console.log('Upload result:', uploadResult);

    // Download
    const decrypted = await s3enc.downloadEncrypted('contracts/2024/001.json');
    console.log('Decrypted:', JSON.parse(decrypted));
}
```

### 9.12.2 Criptografia de Conteúdo em Google Cloud Storage

```javascript
// Google Cloud Storage: Client-side encryption

const { Storage } = require('@google-cloud/storage');
const crypto = require('crypto');

class GCSContentEncryption {
    constructor(bucketName) {
        this.storage = new Storage();
        this.bucket = this.storage.bucket(bucketName);
    }

    async uploadEncrypted(key, data, metadata = {}) {
        // Gerar chave de criptografia
        const encryptionKey = crypto.randomBytes(32);
        const iv = crypto.randomBytes(12);

        // Criptografar dados
        const cipher = crypto.createCipheriv('aes-256-gcm', encryptionKey, iv);
        const encryptedData = Buffer.concat([
            cipher.update(typeof data === 'string' ? Buffer.from(data) : data),
            cipher.final(),
        ]);
        const authTag = cipher.getAuthTag();

        // Upload com KMS key management
        const file = this.bucket.file(key);

        await file.save(encryptedData, {
            metadata: {
                metadata: {
                    'encryption-iv': iv.toString('base64'),
                    'encryption-tag': authTag.toString('base64'),
                    ...metadata,
                },
            },
            // Customer-supplied encryption key (CSEK)
            encryptionKey: encryptionKey,
        });

        return {
            key,
            size: encryptedData.length,
        };
    }

    async downloadEncrypted(key) {
        const file = this.bucket.file(key);

        // Download com descriptografia automática
        const [metadata] = await file.getMetadata();
        const encryptionKey = crypto.randomBytes(32);  // Em produção: buscar chave

        const [data] = await file.download({
            encryptionKey: encryptionKey,
        });

        const iv = Buffer.from(metadata.metadata['encryption-iv'], 'base64');
        const authTag = Buffer.from(metadata.metadata['encryption-tag'], 'base64');

        const decipher = crypto.createDecipheriv('aes-256-gcm', encryptionKey, iv);
        decipher.setAuthTag(authTag);

        const decrypted = Buffer.concat([
            decipher.update(data),
            decipher.final(),
        ]);

        return decrypted.toString('utf-8');
    }
}
```

### 9.12.3 Criptografia com Chave Gerenciada pelo Usuário (BYOK)

```javascript
// Bring Your Own Key (BYOK) para cloud storage

class BYOKManager {
    constructor() {
        this.keys = new Map();
    }

    // Gerar chave de criptografia
    async generateKey(keyId) {
        const key = await window.crypto.subtle.generateKey(
            { name: 'AES-GCM', length: 256 },
            true,
            ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
        );

        this.keys.set(keyId, key);
        return key;
    }

    // Importar chave de backup
    async importKey(keyId, jwk) {
        const key = await window.crypto.subtle.importKey(
            'jwk',
            jwk,
            { name: 'AES-GCM', length: 256 },
            true,
            ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
        );

        this.keys.set(keyId, key);
        return key;
    }

    // Exportar chave para backup
    async exportKey(keyId) {
        const key = this.keys.get(keyId);
        if (!key) throw new Error('Key not found');
        return window.crypto.subtle.exportKey('jwk', key);
    }

    // Criptografar chave com chave mestra (KMS)
    async wrapKey(keyId, masterKey) {
        const key = this.keys.get(keyId);
        if (!key) throw new Error('Key not found');

        const wrapped = await window.crypto.subtle.wrapKey(
            'raw',
            key,
            masterKey,
            { name: 'AES-KW' }
        );

        return new Uint8Array(wrapped);
    }

    // Descriptografar chave com chave mestra
    async unwrapKey(keyId, wrappedKey, masterKey) {
        const key = await window.crypto.subtle.unwrapKey(
            'raw',
            wrappedKey,
            masterKey,
            { name: 'AES-KW' },
            { name: 'AES-GCM', length: 256 },
            true,
            ['encrypt', 'decrypt']
        );

        this.keys.set(keyId, key);
        return key;
    }

    // Rotacionar chave
    async rotateKey(oldKeyId, newKeyId) {
        const oldKey = this.keys.get(oldKeyId);
        if (!oldKey) throw new Error('Old key not found');

        // Gerar nova chave
        const newKey = await this.generateKey(newKeyId);

        // Re-encrypt dados existentes (em produção: buscar do storage)
        // ...

        // Marcar chave antiga como inativa
        this.keys.set(oldKeyId, null);

        return { oldKeyId, newKeyId };
    }
}

// Exemplo de BYOK com AWS KMS
async function byokWithAWSKMS() {
    const { KMSClient, GenerateDataKeyCommand } = require('@aws-sdk/client-kms');

    const kms = new KMSClient({ region: 'us-east-1' });

    // Gerar data key via KMS
    const dataKeyResponse = await kms.send(new GenerateDataKeyCommand({
        KeyId: 'arn:aws:kms:us-east-1:123456789:key/my-key',
        KeySpec: 'AES_256',
    }));

    const dataKey = dataKeyResponse.Plaintext;
    const encryptedDataKey = dataKeyResponse.CiphertextBlob;

    // Usar dataKey para criptografar dados
    const cipher = require('crypto').createCipheriv(
        'aes-256-gcm',
        dataKey,
        require('crypto').randomBytes(12)
    );

    // ... encrypt data ...

    // Armazenar encryptedDataKey junto com os dados criptografados
    // Para descriptografar: decrypt encryptedDataKey via KMS -> dataKey -> decrypt data
}
```

---

## 9.13 Exercícios

### Exercício 1: Implementação de TLS em Servidor Web

**Objetivo**: Configurar um servidor web Node.js com TLS 1.3 e verificação de certificado.

**Requisitos**:
1. Criar um servidor HTTPS com certificado autoassinado
2. Configurar TLS 1.3 com cipher suites modernas
3. Implementar redirect de HTTP para HTTPS
4. Verificar o certificado do cliente (mTLS opcional)
5. Implementar logging de handshake failures

```javascript
// Estrutura do exercício
const https = require('https');
const http = require('http');
const fs = require('fs');
const tls = require('tls');

// 1. Gerar certificado autoassinado (para desenvolvimento)
// openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

// 2. Configurar servidor HTTPS
const options = {
    key: fs.readFileSync('key.pem'),
    cert: fs.readFileSync('cert.pem'),
    minVersion: 'TLSv1.3',
    maxVersion: 'TLSv1.3',
    ciphers: [
        'TLS_AES_256_GCM_SHA384',
        'TLS_CHACHA20_POLY1305_SHA256',
        'TLS_AES_128_GCM_SHA256',
    ].join(':'),
    honorCipherOrder: true,
};

// 3. Criar servidor HTTPS
const server = https.createServer(options, (req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Hello over TLS 1.3!');
});

// 4. Redirect HTTP -> HTTPS
const httpServer = http.createServer((req, res) => {
    const httpsUrl = `https://${req.headers.host}${req.url}`;
    res.writeHead(301, { 'Location': httpsUrl });
    res.end();
});

// 5. Logging de eventos TLS
server.on('tlsClientError', (err, socket) => {
    console.error('TLS Client Error:', err.message);
});

server.on('clientError', (err, socket) => {
    console.error('Client Error:', err.message);
    socket.destroy();
});

server.listen(443, () => {
    console.log('HTTPS server on port 443');
});

httpServer.listen(80, () => {
    console.log('HTTP redirect server on port 80');
});
```

**Testes**:
```bash
# Testar TLS 1.3
openssl s_client -connect localhost:443 -tls1_3

# Testar redirect
curl -v http://localhost:80

# Verificar cipher suite
openssl s_client -connect localhost:443 -cipher ECDHE-RSA-AES128-GCM-SHA256
```

### Exercício 2: Criptografia de Dados com Web Crypto API

**Objetivo**: Implementar criptografia ponta-a-ponta para mensagens de texto.

**Requisitos**:
1. Gerar par de chaves RSA-OAEP para cada usuário
2. Criptografar mensagens com AES-GCM
3. Criptografar a chave simétrica com a chave pública do destinatário
4. Implementar verificação de integridade
5. Criar interface de teste no console

```javascript
// Estrutura esperada
class MessageEncryption {
    // Gerar chaves de usuário
    async generateUserKeyPair(userId) { /* ... */ }

    // Criptografar mensagem
    async encryptMessage(senderId, recipientId, message) { /* ... */ }

    // Descriptografar mensagem
    async decryptMessage(userId, encryptedMessage) { /* ... */ }

    // Verificar integridade
    async verifyIntegrity(message) { /* ... */ }
}

// Testes
async function testEncryption() {
    const enc = new MessageEncryption();
    await enc.generateUserKeyPair('alice');
    await enc.generateUserKeyPair('bob');

    const encrypted = await enc.encryptMessage('alice', 'bob', 'Olá Bob!');
    console.log('Encrypted:', encrypted);

    const decrypted = await enc.decryptMessage('bob', encrypted);
    console.log('Decrypted:', decrypted);

    // Verificar que dados diferentes produzem ciphertexts diferentes
    const encrypted2 = await enc.encryptMessage('alice', 'bob', 'Olá Bob!');
    console.log('Nonce único:', encrypted.iv !== encrypted2.iv);
}
```

### Exercício 3: Implementação de HMAC com Web Crypto

**Objetivo**: Criar sistema de assinatura de requisições HTTP usando HMAC.

**Requisitos**:
1. Gerar chave HMAC compartilhada
2. Assinar requisições HTTP (método, path, timestamp, body)
3. Verificar assinatura no servidor
4. Proteger contra replay attacks com timestamp
5. Implementar tolerância de tempo configurável

```javascript
// Estrutura esperada
class RequestSigner {
    constructor(secretKey) { /* ... */ }

    // Assinar requisição
    sign(method, path, body = '', timestamp = Date.now()) { /* ... */ }

    // Verificar assinatura
    verify(method, path, body, signature, timestamp, toleranceMs = 300000) { /* ... */ }
}

// Testes
function testRequestSigner() {
    const signer = new RequestSigner('my-secret-key');

    // Assinar
    const sig = signer.sign('POST', '/api/data', '{"key":"value"}');
    console.log('Signature:', sig);

    // Verificar
    const valid = signer.verify('POST', '/api/data', '{"key":"value"}', sig.signature, sig.timestamp);
    console.log('Valid:', valid);

    // Verificar com timestamp antigo
    const expired = signer.verify('POST', '/api/data', '{"key":"value"}', sig.signature, sig.timestamp - 600000);
    console.log('Expired (should be false):', expired);
}
```

### Exercício 4: Password Hashing com Argon2

**Objetivo**: Implementar sistema completo de hashing de senhas com Argon2.

**Requisitos**:
1. Hash de senha com Argon2id (configuração segura)
2. Verificação de senha
3. Detecção de necessidade de rehash
4. Proteção contra timing attacks
5. Rate limiting de tentativas de login

```javascript
// Estrutura esperada
class PasswordManager {
    async hashPassword(password) { /* ... */ }
    async verifyPassword(password, hash) { /* ... */ }
    async needsRehash(hash) { /* ... */ }
}

class LoginProtector {
    constructor(passwordManager) { /* ... */ }
    async attemptLogin(userId, password) { /* ... */ }
    getRemainingAttempts(userId) { /* ... */ }
}

// Testes
async function testPasswordSystem() {
    const pm = new PasswordManager();
    const protector = new LoginProtector(pm);

    const hash = await pm.hashPassword('MyS3cur3P@ssw0rd!');
    console.log('Hash:', hash);

    const valid = await pm.verifyPassword('MyS3cur3P@ssw0rd!', hash);
    console.log('Valid:', valid);

    const invalid = await pm.verifyPassword('wrong', hash);
    console.log('Invalid (should be false):', invalid);

    const rehash = await pm.needsRehash(hash);
    console.log('Needs rehash:', rehash);
}
```

### Exercício 5: Secure Random Generation

**Objetivo**: Implementar gerador de números aleatórios seguros com estatísticas de qualidade.

**Requisitos**:
1. Implementar RNG criptograficamente seguro
2. Gerar tokens, senhas e UUIDs
3. Implementar teste de distribuição (chi-square)
4. Criar interface de teste
5. Documentar fontes de entropia

```javascript
// Estrutura esperada
class SecureRandomGenerator {
    getBytes(length) { /* ... */ }
    getRange(min, max) { /* ... */ }
    getString(length, charset) { /* ... */ }
    getToken(bytes) { /* ... */ }
    generatePassword(length) { /* ... */ }
    generateUUID() { /* ... */ }
}

// Testes estatísticos
function testRandomness(generator, samples = 10000) {
    // Chi-square test para uniformidade
    const frequencies = new Array(256).fill(0);
    for (let i = 0; i < samples; i++) {
        const byte = generator.getBytes(1)[0];
        frequencies[byte]++;
    }

    const expected = samples / 256;
    let chiSquare = 0;
    for (const freq of frequencies) {
        chiSquare += Math.pow(freq - expected, 2) / expected;
    }

    // Graus de liberdade: 255
    // Para p < 0.05: chiSquare > 293.25 (rejeitar uniformidade)
    console.log('Chi-square:', chiSquare);
    console.log('Uniform:', chiSquare < 293.25);
}
```

### Exercício 6: Certificate Transparency Monitor

**Objetivo**: Implementar monitor de Certificate Transparency para detectar certificados não autorizados.

**Requisitos**:
1. Consultar API do crt.sh para um domínio
2. Filtrar apenas certificados válidos
3. Detectar novos certificados emitidos
4. Enviar alerta quando detectar certificado suspeito
5. Manter histórico de certificados conhecidos

```javascript
// Estrutura esperada
class CTMonitor {
    async checkDomain(domain) { /* ... */ }
    async detectNewCertificates(domain, knownCertIds) { /* ... */ }
    async alertSuspicious(domain, cert) { /* ... */ }
}
```

### Exercício 7: TLS Configuration Auditor

**Objetivo**: Criar ferramenta que audita a configuração TLS de servidores web.

**Requisitos**:
1. Verificar versão TLS suportada
2. Listar cipher suites habilitadas
3. Verificar forward secrecy
4. Verificar OCSP Stapling
5. Gerar relatório de conformidade com recomendações

```javascript
// Estrutura esperada
class TLSAuditor {
    async audit(domain) {
        return {
            tlsVersion: /* ... */,
            cipherSuites: /* ... */,
            forwardSecrecy: /* ... */,
            ocspStapling: /* ... */,
            certificate: /* ... */,
            recommendations: /* ... */,
        };
    }
}
```

---

## 9.14 Referências

### Especificações e RFCs

- RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 8555: Automatic Certificate Management Environment (ACME)
- RFC 6960: X.509 Internet Public Key Infrastructure Online Certificate Status Protocol (OCSP)
- RFC 6797: HTTP Strict Transport Security (HSTS)
- RFC 7518: JSON Web Algorithms (JWA)
- RFC 7517: JSON Web Key (JWK)
- RFC 6962: Certificate Transparency
- RFC 6698: The DNS-Based Authentication of Named Entities (DANE) Transport Layer Security (TLS) Protocol
- RFC 4034: Resource Records for the DNS Security Extensions
- RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 5869: HMAC-based Extract-and-Expand Key Derivation Function (HKDF)
- RFC 9106: Argon2 Memory-Hard Function for Password Hashing and Key Derivation

### Documentação de APIs

- Web Crypto API (W3C): https://www.w3.org/TR/WebCryptoAPI/
- SubtleCrypto: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto
- Let's Encrypt: https://letsencrypt.org/docs/
- ACME Protocol: https://datatracker.ietf.org/doc/html/rfc8555
- Certificate Transparency: https://certificate.transparency.dev/
- crt.sh: https://crt.sh/

### Ferramentas

- OpenSSL: https://www.openssl.org/docs/
- Certbot: https://certbot.eff.org/
- CFSSL: https://github.com/cloudflare/cfssl
- Step CA: https://smallstep.com/docs/step-ca/
- Vault PKI: https://developer.hashicorp.com/vault/docs/secrets/pki

### Bibliotecas e Implementações

- Node.js crypto: https://nodejs.org/api/crypto.html
- WebCrypto polyfill: https://github.com/nicolo-ribaudo/nicolo-ribaudo.github.io/blob/main/webcrypto-shim.js
- bcrypt.js: https://www.npmjs.com/package/bcryptjs
- argon2: https://www.npmjs.com/package/argon2
- jose (JOSE/JWT): https://www.npmjs.com/package/jose

### Artigos e Guias

- Mozilla SSL Configuration Generator: https://ssl-config.mozilla.org/
- SSL Labs Best Practices: https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices
- OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
- Cloudflare Blog — TLS: https://blog.cloudflare.com/tag/tls/

### CVEs Relacionados

| CVE | Vulnerabilidade | Lição |
|-----|-----------------|-------|
| CVE-2014-0160 | Heartbleed (OpenSSL) | Memory disclosure via TLS |
| CVE-2015-0204 | FREAK (RSA Export) | downgrade attack |
| CVE-2016-0800 | DROWN (SSLv2) | Protocolo antigo compromete TLS moderno |
| CVE-2016-2183 | SWEET32 (64-bit block cipher) | Limites de bloco em CBC/3DES |
| CVE-2019-1547 | OpenSSL ECDSA nonce bias | Nonce reuse vulnerability |
| CVE-2021-3449 | OpenSSL NULL dereference | Renegotiation DoS |
| CVE-2023-0464 | OpenSSL X.509 Policy | Certificate policy bypass |
