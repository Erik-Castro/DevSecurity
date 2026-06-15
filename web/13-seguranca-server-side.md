# Capítulo 13: Segurança Server-Side

> *"O servidor é a primeira linha de defesa — e a última se falhar."*

---

## Objetivos de Aprendizado

1. Configurar headers de segurança em Express.js, Django, Flask e Go
2. Prevenir Server-Side Template Injection (SSTI) em cada framework
3. Implementar padrões de middleware seguros para autenticação e autorização
4. Proteger contra Server-Side Request Forgery (SSRF)
5. Configurar logging seguro sem expor dados sensíveis

---

## 13.1 Node.js / Express.js Security

### 13.1.1 Helmet.js

```javascript
const helmet = require('helmet');
const express = require('express');
const app = express();

app.use(helmet());

// Configuração granular
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", "'nonce-abc123'"],
            styleSrc: ["'self'", "'unsafe-inline'"],
            imgSrc: ["'self'", "data:", "https:"],
            connectSrc: ["'self'", "https://api.exemplo.com"],
            fontSrc: ["'self'"],
            objectSrc: ["'none'"],
            frameAncestors: ["'none'"],
            baseUri: ["'self'"],
            formAction: ["'self'"]
        }
    },
    hsts: { maxAge: 31536000, includeSubDomains: true, preload: true },
    referrerPolicy: { policy: 'strict-origin-when-cross-origin' }
}));
```

### 13.1.2 Express Rate Limiting

```javascript
const rateLimit = require('express-rate-limit');

// Geral
const generalLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Rate limit exceeded' }
});

// Login — mais restritivo
const loginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 5,
    skipSuccessfulRequests: true,
    message: { error: 'Too many login attempts' }
});

app.use('/api/', generalLimiter);
app.use('/auth/login', loginLimiter);
```

### 13.1.3 CORS Configuration

```javascript
const cors = require('cors');

app.use(cors({
    origin: (origin, callback) => {
        const allowedOrigins = ['https://app.exemplo.com', 'https://admin.exemplo.com'];
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('CORS not allowed'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    maxAge: 86400
}));
```

---

## 13.2 Django Security

### 13.2.1 Settings.py Seguro

```python
# settings.py — Configuração de segurança
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'nonce-{nonce}'")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_CONNECT_SRC = ("'self'",)
CSP_FONT_SRC = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_FRAME_ANCESTORS = ("'none'",)
```

### 13.2.2 Django ORM — SQL Injection Prevention

```python
# SEGURO — Django ORM previne SQL injection
from django.db.models import Q

def search_users(query):
    # ORM: parameterized automaticamente
    return User.objects.filter(
        Q(name__icontains=query) | Q(email__icontains=query)
    )

# PERIGOSO — raw SQL sem parameterização
def search_users_raw(query):
    # NUNCA faça isso:
    return User.objects.raw(f"SELECT * FROM users WHERE name LIKE '%{query}%'")

# SEGURO — raw SQL com parameterização
def search_users_safe(query):
    return User.objects.raw(
        "SELECT * FROM users WHERE name LIKE %s",
        [f"%{query}%"]
    )
```

---

## 13.3 Flask Security

### 13.3.1 Flask-Talisman

```python
from flask_talisman import Talisman

app = Flask(__name__)

csp = {
    'default-src': "'self'",
    'script-src': ["'self'"],
    'style-src': ["'self'", "'unsafe-inline'"],
    'img-src': ["'self'", "data:", "https:"],
    'connect-src': ["'self'"],
    'font-src': ["'self'"],
    'object-src': ["'none'"],
    'frame-ancestors': ["'none'"],
    'base-uri': ["'self'"],
    'form-action': ["'self'"]
}

Talisman(app,
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    content_security_policy=csp,
    referrer_policy='strict-origin-when-cross-origin'
)
```

---

## 13.4 Go Security

```go
package main

import (
    "net/http"
    "time"
    
    "github.com/rs/cors"
)

func secureMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        // Security headers
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("X-XSS-Protection", "0") // Deprecated, mas browsers antigos
        w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'")
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        
        // Request timeout
        r.Context() // Use context with timeout for downstream calls
        
        next.ServeHTTP(w, r)
    })
}
```

---

## 13.5 Server-Side Template Injection (SSTI)

### 13.5.1 Jinja2 (Python/Flask)

```python
# VULNERÁVEL — SSTI via template string
from jinja2 import Template

@app.route('/greet')
def greet():
    name = request.args.get('name', 'World')
    # NUNCA faça isso:
    template = Template(f'Olá, {name}!')
    return template.render()

# O atacante pode enviar: {{7*7}} → retorna 49
# Ou: {{config.items()}} → vaza configurações
# Ou: {{''.__class__.__mro__[1].__subclasses__()}} → RCE completo

# SEGURO — usar template files com autoescape
@app.route('/greet')
def greet():
    name = request.args.get('name', 'World')
    return render_template('greet.html', name=name)

# greet.html:
# <h1>Olá, {{ name }}</h1>  ← autoescaped por padrão
```

### 13.5.2 EJS (Node.js)

```javascript
// VULNERÁVEL — SSTI via options
const ejs = require('ejs');

app.get('/page', (req, res) => {
    const options = { filename: 'page.ejs' };
    // Se o template vem do user input:
    const template = req.query.template;
    res.send(ejs.render(template));  // SSTI!

// SEGURO — templates fixos
app.get('/page', (req, res) => {
    res.render('page', { name: req.query.name });  // Template fixo
});
```

---

## 13.6 Server-Side Request Forgery (SSRF)

### 13.6.1 Prevenção

```javascript
const { URL } = require('url');
const dns = require('dns').promises;
const ipaddr = require('ipaddr.js');

async function isSafeURL(urlString) {
    try {
        const url = new URL(urlString);
        
        // Protocolo
        if (!['http:', 'https:'].includes(url.protocol)) return false;
        
        // Resolver DNS
        const addresses = await dns.resolve4(url.hostname);
        
        for (const addr of addresses) {
            const ip = ipaddr.parse(addr);
            const range = ip.range();
            
            if (['private', 'loopback', 'linkLocal', 'uniqueLocal', 'multicast'].includes(range)) {
                return false;
            }
        }
        
        // Portas perigosas
        const dangerousPorts = ['22', '23', '25', '53', '110', '143', '445', '3389'];
        if (dangerousPorts.includes(url.port)) return false;
        
        return true;
    } catch {
        return false;
    }
}

// SSRF-safe fetch
async function safeFetch(urlString) {
    if (!await isSafeURL(urlString)) {
        throw new Error('URL blocked by SSRF protection');
    }
    return fetch(urlString);
}
```

---

## 13.7 Error Handling Sem Informação

```javascript
// VULNERÁVEL — expõe stack trace
app.use((err, req, res, next) => {
    res.status(500).json({
        error: err.message,
        stack: err.stack  // NUNCA em produção!
    });
});

// SEGURO — log interno, resposta genérica
app.use((err, req, res, next) => {
    logger.error('Unhandled error', {
        error: err.message,
        stack: err.stack,
        url: req.url,
        method: req.method,
        userId: req.user?.id
    });
    
    res.status(500).json({
        error: 'Internal server error',
        requestId: req.id  // Para correlação
    });
});
```

---

## 13.8 Logging Seguro

```javascript
// NUNCA logue:
// - Senhas ou tokens
// - Dados de cartão de crédito
// - CPF, RG, ou outros PII
// - Headers de autorização
// - Conteúdo de request bodies sensíveis

// SEGURO — sanitize antes de logar
function sanitizeLog(data) {
    const sensitive = ['password', 'token', 'secret', 'creditCard', 'ssn', 'cpf'];
    const sanitized = { ...data };
    
    for (const key of Object.keys(sanitized)) {
        if (sensitive.some(s => key.toLowerCase().includes(s))) {
            sanitized[key] = '***REDACTED***';
        }
    }
    
    return sanitized;
}

app.use((req, res, next) => {
    logger.info({
        method: req.method,
        url: req.url,
        userId: req.user?.id,
        body: sanitizeLog(req.body),
        ip: req.ip
    });
    next();
});
```

---

## 13.9 Referências

1. OWASP Node.js Security: https://cheatsheetseries.owasp.org/cheatsheets/Node_js_Security_Cheat_Sheet.html
2. OWASP Django Security: https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html
3. Helmet.js: https://helmetjs.github.io/
4. Flask-Talisman: https://github.com/GoogleCloudPlatform/flask-talisman
5. OWASP SSTI Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Template_Injection_Prevention_Cheat_Sheet.html
6. OWASP SSRF Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
7. Django Security Middleware: https://docs.djangoproject.com/en/stable/ref/middleware/#module-django.middleware.security
8. Express Security Best Practices: https://expressjs.com/en/advanced/best-practice-security.html
9. Go Secure Coding: https://owasp.org/www-project-go-secure-coding-practices-guide/

---

*[Capítulo anterior: 12 — JavaScript Seguro](12-javascript-seguro.md)*
*[Próximo capítulo: 14 — Containers e Deployment](14-seguranca-container.md)*

---

## 13.10 Secure Session Configuration

### 13.10.1 Express.js Session Security

```javascript
const session = require('express-session');
const RedisStore = require('connect-redis').default;
const { createClient } = require('redis');

const redisClient = createClient({ url: 'redis://localhost:6379' });
redisClient.connect();

app.use(session({
    store: new RedisStore({ client: redisClient }),
    name: '__Host-sessionId', // Cookie prefix para indicar Secure + HostOnly
    secret: process.env.SESSION_SECRET,
    resave: false,
    saveUninitialized: false,
    cookie: {
        secure: true,        // Apenas HTTPS
        httpOnly: true,      // Sem acesso via JavaScript
        sameSite: 'lax',     // CSRF protection
        domain: '.exemplo.com',
        path: '/',
        maxAge: 3600000      // 1 hora
    }
}));

// Regenerar ID de sessão após login
app.post('/auth/login', async (req, res) => {
    const user = await authenticate(req.body.email, req.body.password);
    if (user) {
        req.session.regenerate((err) => {
            req.session.userId = user.id;
            req.session.role = user.role;
            res.json({ success: true });
        });
    }
});

// Destruir sessão no logout
app.post('/auth/logout', (req, res) => {
    req.session.destroy((err) => {
        res.clearCookie('__Host-sessionId');
        res.json({ success: true });
    });
});
```

### 13.10.2 Django Session Security

```python
# settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600  # 1 hora
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_NAME = '__Host-sessionid'

# CSRF
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

### 13.10.3 Flask Session Security

```python
from flask import session
from datetime import timedelta

app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_KEY_PREFIX'] = 'session:'
```

---

## 13.11 Security Headers Completo

```javascript
// Middleware de headers de segurança completo
function securityHeaders(req, res, next) {
    // HSTS — Force HTTPS
    res.setHeader('Strict-Transport-Security', 
        'max-age=31536000; includeSubDomains; preload');
    
    // CSP — Content Security Policy
    res.setHeader('Content-Security-Policy',
        "default-src 'self'; " +
        "script-src 'self' 'nonce-{random}'; " +
        "style-src 'self' 'unsafe-inline'; " +
        "img-src 'self' data: https:; " +
        "font-src 'self'; " +
        "connect-src 'self'; " +
        "frame-ancestors 'none'; " +
        "base-uri 'self'; " +
        "form-action 'self'; " +
        "object-src 'none'"
    );
    
    // Previne MIME sniffing
    res.setHeader('X-Content-Type-Options', 'nosniff');
    
    // Previne clickjacking
    res.setHeader('X-Frame-Options', 'DENY');
    
    // XSS Protection (deprecated, mas browsers antigos)
    res.setHeader('X-XSS-Protection', '0');
    
    // Referrer Policy
    res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    
    // Permissions Policy
    res.setHeader('Permissions-Policy',
        'camera=(), microphone=(), geolocation=(), payment=()');
    
    // Cache control para páginas sensíveis
    if (req.path.startsWith('/api/') || req.path.includes('dashboard')) {
        res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
        res.setHeader('Pragma', 'no-cache');
        res.setHeader('Expires', '0');
        res.setHeader('Surrogate-Control', 'no-store');
    }
    
    next();
}
```

---

## 13.12 Path Traversal Prevention

```javascript
const path = require('path');

// VULNERÁVEL — path traversal
app.get('/files/:filename', (req, res) => {
    const filePath = path.join('/uploads', req.params.filename);
    // Atacante: GET /files/../../../etc/passwd
    res.sendFile(filePath);
});

// SEGURO — validação de path
app.get('/files/:filename', (req, res) => {
    const filename = path.basename(req.params.filename); // Remove path components
    const filePath = path.join('/uploads', filename);
    
    // Verificar que o resolved path está dentro do diretório permitido
    const resolved = path.resolve(filePath);
    const uploadsDir = path.resolve('/uploads');
    
    if (!resolved.startsWith(uploadsDir + path.sep) && resolved !== uploadsDir) {
        return res.status(403).json({ error: 'Acesso negado' });
    }
    
    res.sendFile(resolved);
});

// Middleware reutilizável
function securePath(baseDir) {
    return (req, res, next) => {
        const userPath = req.params.path || req.query.file;
        if (!userPath) return next();
        
        const resolved = path.resolve(path.join(baseDir, userPath));
        const base = path.resolve(baseDir);
        
        if (!resolved.startsWith(base + path.sep) && resolved !== base) {
            return res.status(403).json({ error: 'Path traversal detected' });
        }
        
        req.securePath = resolved;
        next();
    };
}
```

---

## 13.13 Rate Limiting Avançado

```javascript
const rateLimit = require('express-rate-limit');
const RedisStore = require('rate-limit-redis');
const { createClient } = require('redis');

const redisClient = createClient({ url: 'redis://localhost:6379' });

// Rate limiter distribuído
const apiLimiter = rateLimit({
    store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 100, // máximo 100 requests por IP
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Muitas requisições. Tente novamente mais tarde.' },
    keyGenerator: (req) => {
        return req.headers['x-forwarded-for'] || req.ip;
    }
});

// Login — mais restritivo
const loginLimiter = rateLimit({
    store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
    windowMs: 15 * 60 * 1000,
    max: 5, // máximo 5 tentativas de login
    skipSuccessfulRequests: true,
    message: { error: 'Muitas tentativas de login. Conta bloqueada temporariamente.' }
});

// API pública — mais permissivo
const publicApiLimiter = rateLimit({
    store: new RedisStore({ sendCommand: (...args) => redisClient.sendCommand(args) }),
    windowMs: 60 * 1000, // 1 minuto
    max: 60, // 60 requests por minuto
    standardHeaders: true
});

app.use('/api/', apiLimiter);
app.use('/auth/login', loginLimiter);
app.use('/api/public/', publicApiLimiter);
```

---

## 13.14 Secret Management em Server-Side

```javascript
// NUNCA use variáveis de ambiente hardcoded no código
// NUNCA commite .env no git

// .gitignore
// .env
// .env.local
// .env.production

// Carregar variáveis de ambiente de forma segura
const dotenv = require('dotenv');
dotenv.config();

// Validar que todas as variáveis necessárias existem
const requiredEnvVars = [
    'DATABASE_URL',
    'SESSION_SECRET',
    'JWT_SECRET',
    'SMTP_PASSWORD'
];

for (const envVar of requiredEnvVars) {
    if (!process.env[envVar]) {
        console.error(`Missing required environment variable: ${envVar}`);
        process.exit(1);
    }
}

// Em produção, usar secret management (Vault, AWS Secrets Manager, etc.)
const vault = require('node-vault')({
    apiVersion: 'v1',
    endpoint: process.env.VAULT_ADDR,
    token: process.env.VAULT_TOKEN
});

async function getSecret(path) {
    const { data } = await vault.read(path);
    return data.data;
}

// Uso
const dbPassword = await getSecret('secret/data/database');
```

---

## 13.15 Referências Adicionais

10. Express Security Best Practices: https://expressjs.com/en/advanced/best-practice-security.html
11. Django Security Checklist: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
12. Flask Security: https://flask.palletsprojects.com/en/3.0.x/security/
13. OWASP Session Management: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
14. OWASP HTTP Headers: https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html
15. Mozilla Observatory: https://observatory.mozilla.org/
16. SecurityHeaders.com: https://securityheaders.com/
17. OWASP Path Traversal: https://cheatsheetseries.owasp.org/cheatsheets/Path_Traversal_Cheat_Sheet.html
18. Rate Limiting Best Practices: https://www.cloudflare.com/learning/bots/what-is-rate-limiting/
19. HashiCorp Vault: https://www.vaultproject.io/
20. OWASP Secret Management: https://cheatsheetseries.owasp.org/cheatsheets/Vault_Cheat_Sheet.html

---

## 13.16 Secure Cookie Configuration

### 13.16.1 Comparação de Configurações

| Attribute | Valor Recomendado | Propósito |
|-----------|-------------------|-----------|
| `Secure` | `true` | Apenas via HTTPS |
| `HttpOnly` | `true` | Sem acesso via JavaScript |
| `SameSite` | `Lax` ou `Strict` | Proteção contra CSRF |
| `Path` | `/` ou rota específica | Escopo do cookie |
| `Domain` | `.exemplo.com` | Domínio do cookie |
| `Max-Age` | `3600` (1h) | Tempo de vida |
| `Partitioned` | `true` (Chrome) | Particionamento de cookies |

### 13.16.2 Cookie Prefixes

```javascript
// __Host- prefix força: Secure + Path=/ + SameSite=Lax
// __Secure- prefix força: Secure

// Configuração segura de cookie
res.cookie('sessionId', value, {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 3600000,
    // Chrome 117+: Cookie partitioning para third-party
    // partitioned: true  // Para cookies de terceiros (CROSS-SITE)
});

// Cookie para CSRF token
res.cookie('csrf-token', token, {
    httpOnly: false, // Precisa ser acessível via JS (para header)
    secure: true,
    sameSite: 'strict',
    path: '/',
    maxAge: 3600000
});
```

---

## 13.17 Command Injection Prevention

```javascript
const { execFile } = require('child_process');

// VULNERÁVEL — command injection
app.get('/ping', (req, res) => {
    const host = req.query.host;
    // Atacante: /ping?host=127.0.0.1;cat /etc/passwd
    exec(`ping -c 4 ${host}`, (err, stdout) => {
        res.send(stdout);
    });
});

// SEGURO — usar argumentos separados
app.get('/ping', (req, res) => {
    const host = req.query.host;
    
    // Validar input
    if (!/^[\w\.\-]+$/.test(host)) {
        return res.status(400).json({ error: 'Host inválido' });
    }
    
    execFile('ping', ['-c', '4', host], (err, stdout) => {
        if (err) return res.status(500).json({ error: 'Erro ao executar ping' });
        res.send(stdout);
    });
});

// Python equivalente
// PERIGOSO:
// os.system(f"ping -c 4 {host}")
// SEGURO:
// subprocess.run(["ping", "-c", "4", host], capture_output=True)
```

---

## 13.18 LDAP Injection Prevention

```javascript
// VULNERÁVEL — LDAP injection
const ldap = require('ldapjs');

app.post('/auth/ldap', (req, res) => {
    const { username, password } = req.body;
    // Atacante: username = "*)(&(objectClass=*)"
    const filter = `(uid=${username})`;
    // O filtro se torna: (uid=*)(&(objectClass=*))
    
    client.search('dc=exemplo,dc=com', { filter }, (err, result) => {
        // ...
    });
});

// SEGURO — escape de caracteres LDAP
function escapeLDAP(str) {
    return str
        .replace(/\\/g, '\\5c')
        .replace(/\*/g, '\\2a')
        .replace(/\(/g, '\\28')
        .replace(/\)/g, '\\29')
        .replace(/\0/g, '\\00');
}

app.post('/auth/ldap', (req, res) => {
    const username = escapeLDAP(req.body.username);
    const filter = `(uid=${username})`;
    // ...
});
```

---

## 13.19 Information Disclosure Prevention

```javascript
// VULNERÁVEL — expõe versão do framework
app.use((req, res, next) => {
    res.setHeader('X-Powered-By', 'Express 4.18.2'); // NUNCA!
    next();
});

// SEGURO — remover headers de identificação
app.disable('x-powered-by');

// VULNERÁVEL — error pages com detalhes
app.use((err, req, res, next) => {
    res.status(500).send(`
        <h1>Erro 500</h1>
        <pre>${err.stack}</pre>
        <p>Node.js ${process.version}</p>
        <p>Express ${require('express/package.json').version}</p>
    `);
});

// SEGURO — página de erro genérica
app.use((err, req, res, next) => {
    logger.error({ error: err.message, stack: err.stack, url: req.url });
    
    if (process.env.NODE_ENV === 'production') {
        res.status(500).send('Erro interno do servidor');
    } else {
        res.status(500).json({ error: err.message });
    }
});

// Custom error pages
app.use((req, res) => {
    res.status(404).send('Página não encontrada');
});
```

---

## 13.20 Server Hardening Checklist

| Item | Check | Prioridade |
|------|-------|-----------|
| TLS 1.3 configurado | cipher suites seguros | Crítico |
| HSTS habilitado | max-age >= 1 ano | Crítico |
| CSP configurado | default-src 'self' | Crítico |
| X-Content-Type-Options | nosniff | Alto |
| X-Frame-Options | DENY | Alto |
| Server tokens removidos | X-Powered-By removido | Alto |
| CORS configurado | origin allowlist | Alto |
| Rate limiting habilitado | por IP e endpoint | Alto |
| Error pages genéricas | sem stack traces | Alto |
| Logging sanitizado | sem PII/sensitive data | Alto |
| Session cookies seguros | Secure+HttpOnly+SameSite | Crítico |
| File upload validado | magic bytes + size limit | Alto |
| SQL queries parameterized | sem string concatenation | Crítico |
| Template injection prevenido | sem eval/render string | Crítico |
| SSRF prevenido | IP validation | Alto |

---

## 13.21 Referências Finais

21. OWASP Node.js Security: https://cheatsheetseries.owasp.org/cheatsheets/Node_js_Security_Cheat_Sheet.html
22. Express.js Security: https://expressjs.com/en/advanced/best-practice-security.html
23. Django Security: https://docs.djangoproject.com/en/stable/topics/security/
24. Flask Security: https://flask.palletsprojects.com/en/3.0.x/security/
25. OWASP Cheat Sheet Series: https://cheatsheetseries.owasp.org/
26. Mozilla Web Security Guidelines: https://infosec.mozilla.org/guidelines/web_security
27. Node.js Security Best Practices: https://nodejs.org/en/docs/guides/security/
28. OWASP Command Injection: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html
29. OWASP LDAP Injection: https://cheatsheetseries.owasp.org/cheatsheets/LDAP_Injection_Prevention_Cheat_Sheet.html
30. OWASP Server Side Request Forgery: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
