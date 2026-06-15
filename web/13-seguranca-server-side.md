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
