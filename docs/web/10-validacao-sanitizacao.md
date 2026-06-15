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

*[Capítulo anterior: 09 — Criptografia na Web](09-criptografia-na-web.md)*
*[Próximo capítulo: 11 — Segurança de APIs](11-seguranca-api.md)*

---

## 10.10 Rich Text Editor Validation

### 10.10.1 Procedural Validation Pipeline

```javascript
// Pipeline completo de validação para inputs de usuário
class InputValidator {
    constructor() {
        this.rules = new Map();
    }
    
    addRule(field, validator) {
        if (!this.rules.has(field)) this.rules.set(field, []);
        this.rules.get(field).push(validator);
        return this;
    }
    
    validate(data) {
        const errors = [];
        
        for (const [field, validators] of this.rules) {
            const value = data[field];
            
            for (const validator of validators) {
                const result = validator(value, data);
                if (result !== true) {
                    errors.push({ field, message: result });
                }
            }
        }
        
        return { valid: errors.length === 0, errors };
    }
}

// Regras de validação reutilizáveis
const rules = {
    required: (msg = 'Campo obrigatório') => (value) => {
        if (value === undefined || value === null || value === '') return msg;
        return true;
    },
    
    maxLength: (max, msg) => (value) => {
        if (typeof value === 'string' && value.length > max) return msg || `Máximo ${max} caracteres`;
        return true;
    },
    
    minLength: (min, msg) => (value) => {
        if (typeof value === 'string' && value.length < min) return msg || `Mínimo ${min} caracteres`;
        return true;
    },
    
    pattern: (regex, msg) => (value) => {
        if (typeof value === 'string' && !regex.test(value)) return msg;
        return true;
    },
    
    noHTML: (msg = 'Tags HTML não são permitidas') => (value) => {
        if (typeof value === 'string' && /<[^>]*>/.test(value)) return msg;
        return true;
    },
    
    noScript: (msg = 'Scripts não são permitidos') => (value) => {
        if (typeof value === 'string' && /<script/i.test(value)) return msg;
        return true;
    },
    
    noSQL: (msg = 'Caracteres SQL inválidos') => (value) => {
        if (typeof value === 'string' && /['";\\]/.test(value)) return msg;
        return true;
    }
};

// Uso
const validator = new InputValidator();
validator
    .addRule('name', rules.required())
    .addRule('name', rules.minLength(2))
    .addRule('name', rules.maxLength(100))
    .addRule('name', rules.pattern(/^[a-zA-ZÀ-ÿ\s]+$/, 'Apenas letras'))
    .addRule('email', rules.required())
    .addRule('email', rules.pattern(/^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Email inválido'))
    .addRule('bio', rules.maxLength(500))
    .addRule('bio', rules.noHTML());

const result = validator.validate(req.body);
if (!result.valid) {
    return res.status(400).json({ errors: result.errors });
}
```

---

## 10.11 File Upload — Validação Completa

### 10.11.1 Validação Multi-Camada

```javascript
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const fileType = require('file-type');

// Storage com nome seguro
const storage = multer.diskStorage({
    destination: '/uploads/temp/',
    filename: (req, file, cb) => {
        const randomName = require('crypto').randomBytes(16).toString('hex');
        const ext = path.extname(file.originalname).toLowerCase();
        cb(null, `${randomName}${ext}`);
    }
});

// Filtro de upload
const fileFilter = async (req, file, cb) => {
    // 1. Verificar MIME type do request
    const allowedMimes = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf'];
    if (!allowedMimes.includes(file.mimetype)) {
        return cb(new Error('Tipo MIME não permitido'), false);
    }
    
    // 2. Verificar extensão
    const allowedExts = ['.jpg', '.jpeg', '.png', '.gif', '.pdf'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (!allowedExts.includes(ext)) {
        return cb(new Error('Extensão não permitida'), false);
    }
    
    // 3. Verificar magic bytes (após upload temporário)
    cb(null, true);
};

const upload = multer({
    storage,
    limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
    fileFilter
});

// Middleware pós-upload: validar magic bytes
async function validateMagicBytes(filePath) {
    const buffer = Buffer.alloc(8);
    const fd = fs.openSync(filePath, 'r');
    fs.readSync(fd, buffer, 0, 8, 0);
    fs.closeSync(fd);
    
    const signatures = {
        'ffd8ff': 'image/jpeg',
        '89504e47': 'image/png',
        '47494638': 'image/gif',
        '25504446': 'application/pdf'
    };
    
    const header = buffer.toString('hex');
    for (const [sig, expectedMime] of Object.entries(signatures)) {
        if (header.startsWith(sig)) return expectedMime;
    }
    
    // Magic bytes não reconhecidos — arquivo potencialmente malicioso
    fs.unlinkSync(filePath); // Deletar arquivo
    throw new Error('Tipo de arquivo não reconhecido');
}

// Validação final do arquivo
async function validateUploadedFile(filePath, originalMimetype) {
    // 1. Magic bytes
    const detectedMime = await validateMagicBytes(filePath);
    if (detectedMime !== originalMimetype) {
        fs.unlinkSync(filePath);
        throw new Error('MIME type não corresponde ao conteúdo');
    }
    
    // 2. Tamanho
    const stats = fs.statSync(filePath);
    if (stats.size > 5 * 1024 * 1024) {
        fs.unlinkSync(filePath);
        throw new Error('Arquivo excede tamanho máximo');
    }
    
    // 3. Para imagens: verificar dimensões
    if (detectedMime.startsWith('image/')) {
        const imageInfo = require('imageinfo')(fs.readFileSync(filePath));
        if (!imageInfo || !imageInfo.width || !imageInfo.height) {
            fs.unlinkSync(filePath);
            throw new Error('Não foi possível ler informações da imagem');
        }
        
        if (imageInfo.width > 4096 || imageInfo.height > 4096) {
            fs.unlinkSync(filePath);
            throw new Error('Dimensões da imagem excedem máximo permitido');
        }
    }
    
    return { path: filePath, mime: detectedMime, size: stats.size };
}
```

### 10.11.2 Validação de Upload em Python (Flask)

```python
from flask import Flask, request
from werkzeug.utils import secure_filename
import os
import magic

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
ALLOWED_MIMES = {'image/png', 'image/jpeg', 'image/gif', 'application/pdf'}
MAX_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_upload(file):
    # 1. Nome seguro
    filename = secure_filename(file.filename)
    if not filename or not allowed_file(filename):
        return False, "Tipo de arquivo não permitido"
    
    # 2. Ler conteúdo
    content = file.read()
    
    # 3. Tamanho
    if len(content) > MAX_SIZE:
        return False, "Arquivo excede tamanho máximo"
    
    # 4. Magic bytes
    detected_mime = magic.from_buffer(content, mime=True)
    if detected_mime not in ALLOWED_MIMES:
        return False, f"Tipo de conteúdo não permitido: {detected_mime}"
    
    # 5. Nome aleatório para armazenamento
    import uuid
    ext = filename.rsplit('.', 1)[1].lower()
    safe_filename = f"{uuid.uuid4().hex}.{ext}"
    
    return True, {"filename": safe_filename, "mime": detected_mime, "size": len(content)}
```

---

## 10.12 CORS Validation

### 10.12.1 Origin Validation

```javascript
// Validação de Origin em requests
function validateOrigin(req) {
    const origin = req.headers.origin;
    
    // Requests sem Origin (same-origin, POST direto, etc.)
    if (!origin) return true;
    
    const allowedOrigins = [
        'https://app.exemplo.com',
        'https://admin.exemplo.com',
        'https://api.exemplo.com'
    ];
    
    // Parse da origin
    try {
        const parsed = new URL(origin);
        
        // Verificar se é HTTPS em produção
        if (process.env.NODE_ENV === 'production' && parsed.protocol !== 'https:') {
            return false;
        }
        
        // Verificar se está na allowlist
        return allowedOrigins.includes(origin);
    } catch {
        return false;
    }
}

// Middleware
function originMiddleware(req, res, next) {
    if (!validateOrigin(req)) {
        return res.status(403).json({ error: 'Origin not allowed' });
    }
    next();
}
```

---

## 10.13 Validation Middleware Completo

```javascript
// middleware/validation.js — Express.js
const { z } = require('zod');

// Schema para criação de usuário
const CreateUserSchema = z.object({
    name: z.string()
        .min(1, 'Nome é obrigatório')
        .max(100, 'Nome muito longo')
        .regex(/^[a-zA-ZÀ-ÿ\s]+$/, 'Nome contém caracteres inválidos'),
    
    email: z.string()
        .email('Email inválido')
        .max(254, 'Email muito longo')
        .toLowerCase(),
    
    password: z.string()
        .min(8, 'Senha deve ter pelo menos 8 caracteres')
        .max(128, 'Senha muito longa')
        .regex(/[A-Z]/, 'Senha precisa de letra maiúscula')
        .regex(/[a-z]/, 'Senha precisa de letra minúscula')
        .regex(/[0-9]/, 'Senha precisa de número')
        .regex(/[^a-zA-Z0-9]/, 'Senha precisa de símbolo'),
    
    age: z.number()
        .int()
        .min(0, 'Idade inválida')
        .max(150, 'Idade inválida')
        .optional(),
    
    role: z.enum(['user', 'admin', 'moderator']).default('user')
});

// Schema para login
const LoginSchema = z.object({
    email: z.string().email('Email inválido'),
    password: z.string().min(1, 'Senha é obrigatória')
});

// Middleware de validação
function validate(schema) {
    return (req, res, next) => {
        const result = schema.safeParse(req.body);
        
        if (!result.success) {
            const errors = result.error.issues.map(issue => ({
                field: issue.path.join('.'),
                message: issue.message,
                code: issue.code
            }));
            
            return res.status(400).json({
                error: 'Validation failed',
                errors
            });
        }
        
        // Dados validados e sanitizados
        req.validatedBody = result.data;
        next();
    };
}

// Uso nas rotas
app.post('/api/users', validate(CreateUserSchema), async (req, res) => {
    // req.validatedBody contém dados validados e com tipos corretos
    const user = await createUser(req.validatedBody);
    res.status(201).json(user);
});

app.post('/api/auth/login', validate(LoginSchema), async (req, res) => {
    const { email, password } = req.validatedBody;
    const token = await authenticate(email, password);
    res.json({ token });
});
```

---

## 10.14 Referências Adicionais

9. OWASP ASVS v4.0 — Input Validation: https://asvs.owasp.org/
10. Zod Documentation: https://zod.dev/
11. Joi Documentation: https://joi.dev/
12. Pydantic Documentation: https://docs.pydantic.dev/
13. go-playground/validator: https://github.com/go-playground/validator
14. OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
15. OWASP Query Parameterization: https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
16. DOMPurify Configuration: https://github.com/cure53/DOMPurify#configuration
17. sanitize-html Documentation: https://github.com/apostrophecms/sanitize-html#readme

---

## 10.15 Phone Number Validation

### 10.15.1 Validação Internacional

```javascript
// Usando libphonenumber-js
import { isValidPhoneNumber, parsePhoneNumber } from 'libphonenumber-js';

function validatePhone(phone, country = 'BR') {
    // Validar formato
    if (!isValidPhoneNumber(phone, country)) {
        return { valid: false, error: 'Número de telefone inválido' };
    }
    
    const parsed = parsePhoneNumber(phone, country);
    
    return {
        valid: true,
        formatted: parsed.formatInternational(),
        country: parsed.country,
        type: parsed.getType(), // MOBILE, FIXED_LINE, etc.
        national: parsed.formatNational()
    };
}

// Uso
const result = validatePhone('+55 11 99999-8888', 'BR');
// { valid: true, formatted: '+55 11 99999-8888', country: 'BR', type: 'MOBILE' }
```

```python
# Python — phonenumbers
import phonenumbers

def validate_phone(phone_str, country='BR'):
    try:
        parsed = phonenumbers.parse(phone_str, country)
        if not phonenumbers.is_valid_number(parsed):
            return {'valid': False, 'error': 'Número inválido'}
        
        return {
            'valid': True,
            'formatted': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            'country': phonenumbers.region_code_for_number(parsed),
            'type': phonenumbers.number_type(parsed)
        }
    except phonenumbers.NumberParseException:
        return {'valid': False, 'error': 'Formato inválido'}
```

---

## 10.16 Numeric Validation

### 10.16.1 Prevenção de Integer Overflow e Type Confusion

```javascript
// Validação de números — previne overflow e type confusion
function validateInteger(value, options = {}) {
    const { min = Number.MIN_SAFE_INTEGER, max = Number.MAX_SAFE_INTEGER } = options;
    
    // Converter para número
    const num = Number(value);
    
    // Verificar se é finite
    if (!Number.isFinite(num)) {
        return { valid: false, error: 'Valor não é um número válido' };
    }
    
    // Verificar se é integer
    if (!Number.isInteger(num)) {
        return { valid: false, error: 'Valor deve ser um número inteiro' };
    }
    
    // Verificar range
    if (num < min || num > max) {
        return { valid: false, error: `Valor deve estar entre ${min} e ${max}` };
    }
    
    return { valid: true, value: num };
}

// Validação de Decimal
function validateDecimal(value, options = {}) {
    const { min = -Infinity, max = Infinity, decimals = 2 } = options;
    
    const num = parseFloat(value);
    
    if (!Number.isFinite(num)) {
        return { valid: false, error: 'Valor não é um número decimal válido' };
    }
    
    if (num < min || num > max) {
        return { valid: false, error: `Valor deve estar entre ${min} e ${max}` };
    }
    
    // Verificar casas decimais
    const parts = String(value).split('.');
    if (parts.length > 1 && parts[1].length > decimals) {
        return { valid: false, error: `Máximo ${decimals} casas decimais` };
    }
    
    return { valid: true, value: Math.round(num * Math.pow(10, decimals)) / Math.pow(10, decimals) };
}

// Validação de CEP (Brasil)
function validateCEP(cep) {
    const cleaned = cep.replace(/\D/g, '');
    if (cleaned.length !== 8) return { valid: false, error: 'CEP deve ter 8 dígitos' };
    const formatted = `${cleaned.slice(0, 5)}-${cleaned.slice(5)}`;
    return { valid: true, value: formatted };
}

// Validação de CPF (Brasil)
function validateCPF(cpf) {
    const cleaned = cpf.replace(/\D/g, '');
    if (cleaned.length !== 11) return { valid: false, error: 'CPF deve ter 11 dígitos' };
    if (/^(\d)\1{10}$/.test(cleaned)) return { valid: false, error: 'CPF inválido' };
    
    // Validação de dígitos verificadores
    let sum = 0;
    for (let i = 0; i < 9; i++) sum += parseInt(cleaned[i]) * (10 - i);
    let remainder = (sum * 10) % 11;
    if (remainder === 10) remainder = 0;
    if (remainder !== parseInt(cleaned[9])) return { valid: false, error: 'CPF inválido' };
    
    sum = 0;
    for (let i = 0; i < 10; i++) sum += parseInt(cleaned[i]) * (11 - i);
    remainder = (sum * 10) % 11;
    if (remainder === 10) remainder = 0;
    if (remainder !== parseInt(cleaned[10])) return { valid: false, error: 'CPF inválido' };
    
    return { valid: true, value: cleaned };
}
```

---

## 10.17 Date Validation

```javascript
// Validação segura de datas
function validateDate(dateString, options = {}) {
    const { minDate, maxDate, format = 'YYYY-MM-DD' } = options;
    
    // Parse manual para evitar Date.parse pitfalls
    const match = dateString.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return { valid: false, error: 'Formato de data inválido (use YYYY-MM-DD)' };
    
    const [, year, month, day] = match.map(Number);
    
    // Verificar ranges
    if (month < 1 || month > 12) return { valid: false, error: 'Mês inválido' };
    if (day < 1 || day > 31) return { valid: false, error: 'Dia inválido' };
    
    // Verificar dias por mês
    const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
    const maxDay = isLeap && month === 2 ? 29 : daysInMonth[month - 1];
    
    if (day > maxDay) return { valid: false, error: `Dia inválido para o mês ${month}` };
    
    const date = new Date(year, month - 1, day);
    
    if (minDate && date < new Date(minDate)) {
        return { valid: false, error: `Data deve ser posterior a ${minDate}` };
    }
    if (maxDate && date > new Date(maxDate)) {
        return { valid: false, error: `Data deve ser anterior a ${maxDate}` };
    }
    
    return { valid: true, value: date };
}
```

---

## 10.18 Referências Finais

21. libphonenumber-js: https://github.com/catamphetamine/libphonenumbers-js
22. OWASP ASVS v4.0 — Input Validation: https://asvs.owasp.org/
23. CWE-20: Improper Input Validation: https://cwe.mitre.org/data/definitions/20.html
24. CWE-434: Unrestricted Upload of File with Dangerous Type: https://cwe.mitre.org/data/definitions/434.html
25. CWE-918: Server-Side Request Forgery: https://cwe.mitre.org/data/definitions/918.html
