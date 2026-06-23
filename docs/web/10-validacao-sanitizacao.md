# Capítulo 10: Input Validation e Sanitization

> *"Nunca confie em input do usuário — nem do cliente, nem do servidor, nem de ninguém."*

---

## Objetivos de Aprendizado

1. Implementar validação de input com allowlists em múltiplos contextos
2. Usar bibliotecas de validação (Zod, Joi, Pydantic, validator.go)
3. Aplicar sanitização de HTML com DOMPurify e sanitize-html
4. Proteger contra file upload attacks, SSRF e email injection
5. Configurar validação de schemas para APIs REST e GraphQL

---

## 10.1 Princípios Fundamentais

### Allowlist vs Blocklist

```
ALWAYS: Allowlist (whitelist) — aceitar APENAS o formato conhecido
NEVER: Blocklist (blacklist) — bloquear conhecidos maliciosos
```

**Por que blocklists falham:**

| Ataque | Blocklist | Allowlist |
|--------|-----------|-----------|
| `<script>` | Bloqueado | Aceito: `<b>`, `<i>` apenas |
| `javascript:` | Bloqueado | Aceito: `https://` apenas |
| SQL: `' OR 1=1` | Bloqueado | Aceito: números positivos apenas |

### Validação em Camadas

```
Client-side (conveniência) → Server-side (obrigatório) → Database (constraint)
```

NUNCA dependa apenas da validação client-side — ela pode ser bypassada com curl, Burp ou JavaScript desabilitado.

---

## 10.2 Validação de Email

```javascript
// JavaScript — Validação robusta
function isValidEmail(email) {
    // RFC 5322 simplificado
    const regex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
    if (!regex.test(email)) return false;
    
    // Verificar MX record (opcional, async)
    const parts = email.split('@');
    if (parts.length !== 2) return false;
    const domain = parts[1];
    
    // Block domains known for disposable email
    const disposableDomains = ['guerrillamail.com', 'tempmail.com', 'throwaway.email'];
    if (disposableDomains.includes(domain.toLowerCase())) return false;
    
    return true;
}
```

```python
# Python — usando email-validator
from email_validator import validate_email, EmailNotValidError

def is_valid_email(email):
    try:
        result = validate_email(email, check_deliverability=True)
        return True
    except EmailNotValidError:
        return False
```

```go
// Go — validação com regex
import "regexp"

var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

func IsValidEmail(email string) bool {
    return emailRegex.MatchString(email) && len(email) <= 254
}
```

---

## 10.3 Validação de URL

```javascript
// Validação segura de URL — previne SSRF
function isValidURL(url) {
    try {
        const parsed = new URL(url);
        
        // Allowlist de protocolos
        if (!['http:', 'https:'].includes(parsed.protocol)) {
            return false;
        }
        
        // Block localhost e private IPs (previne SSRF)
        const hostname = parsed.hostname;
        if (hostname === 'localhost' || 
            hostname === '127.0.0.1' ||
            hostname === '0.0.0.0' ||
            hostname.startsWith('192.168.') ||
            hostname.startsWith('10.') ||
            hostname.startsWith('172.') ||
            /^172\.(1[6-9]|2\d|3[01])\./.test(hostname)) {
            return false;
        }
        
        // Tamanho máximo
        if (url.length > 2048) return false;
        
        return true;
    } catch {
        return false;
    }
}
```

---

## 10.4 JSON Schema Validation

```javascript
// Usando Zod (TypeScript)
import { z } from 'zod';

const UserSchema = z.object({
    name: z.string().min(1).max(100).regex(/^[a-zA-ZÀ-ÿ\s]+$/),
    email: z.string().email().max(254),
    age: z.number().int().min(0).max(150),
    password: z.string().min(8).max(128)
        .regex(/[A-Z]/, 'Precisa de maiúscula')
        .regex(/[a-z]/, 'Precisa de minúscula')
        .regex(/[0-9]/, 'Precisa de número')
        .regex(/[^a-zA-Z0-9]/, 'Precisa de símbolo'),
    url: z.string().url().optional(),
    role: z.enum(['user', 'admin', 'moderator'])
});

// Middleware de validação
function validate(schema) {
    return (req, res, next) => {
        const result = schema.safeParse(req.body);
        if (!result.success) {
            return res.status(400).json({ 
                errors: result.error.issues.map(i => ({
                    field: i.path.join('.'),
                    message: i.message
                }))
            });
        }
        req.validatedBody = result.data;
        next();
    };
}

// Uso
app.post('/users', validate(UserSchema), createUser);
```

```python
# Python — Pydantic
from pydantic import BaseModel, EmailStr, Field, validator
import re

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(..., ge=0, le=150)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', v):
            raise ValueError('Nome contém caracteres inválidos')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha precisa de maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha precisa de minúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('Senha precisa de número')
        return v
```

```go
// Go — go-playground/validator
import "github.com/go-playground/validator/v10"

type UserCreate struct {
    Name     string `validate:"required,min=1,max=100,alpha"`
    Email    string `validate:"required,email,max=254"`
    Age      int    `validate:"required,gte=0,lte=150"`
    Password string `validate:"required,min=8,max=128"`
}

var validate = validator.New()

func ValidateUser(u UserCreate) error {
    return validate.Struct(u)
}
```

---

## 10.5 File Upload Security

```javascript
// Express.js — Upload seguro com multer
const multer = require('multer');
const path = require('path');
const crypto = require('crypto');

const ALLOWED_TYPES = {
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'application/pdf': ['.pdf']
};

const MAX_SIZE = 5 * 1024 * 1024; // 5MB

const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, '/uploads/'),
    filename: (req, file, cb) => {
        const randomName = crypto.randomBytes(16).toString('hex');
        const ext = path.extname(file.originalname).toLowerCase();
        cb(null, `${randomName}${ext}`);
    }
});

const upload = multer({
    storage,
    limits: { fileSize: MAX_SIZE },
    fileFilter: (req, file, cb) => {
        // Verificar MIME type
        if (!ALLOWED_TYPES[file.mimetype]) {
            return cb(new Error('Tipo de arquivo não permitido'));
        }
        
        // Verificar extensão
        const ext = path.extname(file.originalname).toLowerCase();
        if (!ALLOWED_TYPES[file.mimetype].includes(ext)) {
            return cb(new Error('Extensão não corresponde ao tipo'));
        }
        
        // Verificar magic bytes (primeiros 8 bytes)
        cb(null, true);
    }
});

// Validação de magic bytes
function validateMagicBytes(buffer) {
    const signatures = {
        'ffd8ff': 'image/jpeg',
        '89504e47': 'image/png',
        '47494638': 'image/gif',
        '25504446': 'application/pdf'
    };
    
    const header = buffer.slice(0, 8).toString('hex');
    for (const [sig, mime] of Object.entries(signatures)) {
        if (header.startsWith(sig)) return mime;
    }
    return null;
}
```

---

## 10.6 HTML Sanitization

```javascript
import DOMPurify from 'dompurify';
import createDOMPurify from 'dompurify';
import { JSDOM } from 'jsdom';

const window = new JSDOM('').window;
const DOMPurifyServer = createDOMPurify(window);

// Server-side sanitization
function sanitizeHTML(dirty) {
    return DOMPurifyServer.sanitize(dirty, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote', 'code', 'pre', 'img'],
        ALLOWED_ATTR: ['href', 'title', 'alt', 'src', 'width', 'height'],
        ALLOW_DATA_ATTR: false,
        ALLOW_UNKNOWN_PROTOCOLS: false
    });
}
```

---

## 10.7 Request Size Limits

```javascript
// Express.js — Limitar tamanho de request
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ limit: '1mb', extended: true }));

// Express rate limiting
const rateLimit = require('express-rate-limit');

const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutos
    max: 100, // máximo 100 requests por window
    message: { error: 'Muitas requisições. Tente novamente mais tarde.' },
    standardHeaders: true,
    legacyHeaders: false
});

app.use('/api/', apiLimiter);
```

---

## 10.8 SSRF Prevention

```javascript
// Previnição de SSRF via validação de URL
const dns = require('dns').promises;
const ipaddr = require('ipaddr.js');

async function isSafeURL(url) {
    const parsed = new URL(url);
    
    // Protocolo
    if (!['http:', 'https:'].includes(parsed.protocol)) return false;
    
    // Resolver DNS e verificar IP
    const addresses = await dns.resolve4(parsed.hostname);
    for (const addr of addresses) {
        const ip = ipaddr.parse(addr);
        const range = ip.range();
        
        // Block private/loopback ranges
        if (['private', 'loopback', 'linkLocal', 'uniqueLocal'].includes(range)) {
            return false;
        }
    }
    
    return true;
}
```

---

## 10.9 Referências

1. OWASP Input Validation: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
2. OWASP File Upload: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
3. OWASP SSRF Prevention: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
4. Zod: https://zod.dev/
5. Pydantic: https://docs.pydantic.dev/
6. DOMPurify: https://github.com/cure53/DOMPurify
7. sanitize-html: https://github.com/apostrophecms/sanitize-html
8. OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
---

*[Capítulo anterior: 09 — Criptografia Na Web](09-criptografia-na-web.md)*
*[Próximo capítulo: 11 — Seguranca Api](11-seguranca-api.md)*
